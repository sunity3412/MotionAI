"""분석 파이프라인 — S3 업로드 이벤트 → SQS → 이 함수 (비동기).

두 가지 처리 경로:
  1. RunPod 위임 (운영) — RUNPOD_ANALYZE_URL + RUNPOD_AUTH_TOKEN 환경변수가
     set 이면 HTTP POST 로 위임. Lambda 는 즉시 끝. RunPod 서버가 S3 다운로드 →
     NLF GPU 추출 → reference 비교 → Firestore Admin 갱신 일체 처리.
     backend/runpod_inference/server.py 참조.
  2. 직접 처리 (폴백, 개발용) — RunPod 환경변수 미설정 시 이 Lambda 가 직접
     NLF 추론까지. Lambda 가 GPU 없는 환경이라 실제로는 NaN — #7-follow
     운영 GPU 인프라 켜지기 전 흐름 검증용.

알고리즘 코어(features/temporal/motiondtw/kismam/selfmotion/assemble)는 모델
무관·유닛 검증됨. 무거운 모델/ffmpeg/Cerebras 는 interfaces 어댑터로 분리 —
3D 포즈는 NLF(pose_estimator), 영상은 ffmpeg(frame_extractor), 코칭은
Cerebras(coach_writer). NLF 추론은 GPU 필요(plan.md #7-follow).

오케스트레이션 정직성:
  - 인체 미감지(NoHumanError) → contract no_human 으로 실패 기록.
  - 그 외 런타임 오류 → server_error 로 실패 기록(사용자 노출 문구).

상태/오류/경로는 docs/contract.md, 단계는 models.PIPELINE_SEQUENCE.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import urllib.error
import urllib.request

import boto3  # Lambda 런타임 제공
import numpy as np

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import assemble, kismam, segments, selfmotion, skeleton
from sunity_shared.analysis.features import (
    compute_joint_angles,
    feature_vector,
    joint_uncertainty,
)
from sunity_shared.analysis.interfaces import NoHumanError  # 가벼움 — 예외만
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
from sunity_shared.analysis.temporal import temporal_fill
from sunity_shared.events import iter_s3_keys_from_sqs
from sunity_shared.s3keys import parse_upload_key

# FfmpegFrameExtractor / NlfPoseEstimator / CerebrasCoachWriter 는 imageio·torch·
# requests 같은 무거운 의존성을 끌어옴. RunPod 위임 모드에선 사용하지 않으므로
# _ensure_adapters() 안에서 lazy import — Lambda 콜드스타트 절감 + 테스트가
# 어댑터 의존성 없이도 lambda_handler 디스패치를 검증할 수 있게 한다.

log = logging.getLogger()
log.setLevel(logging.INFO)

_s3 = boto3.client("s3")
_PLAYBACK_EXPIRES = 3600  # 결과 화면 영상 재생 서명 URL 만료(초)

# RunPod 위임 환경 — 운영에서만 set. 미설정 시 폴백(_process) 이라 개발은 그대로.
_RUNPOD_URL = os.environ.get("RUNPOD_ANALYZE_URL", "").strip()
_RUNPOD_TOKEN = os.environ.get("RUNPOD_AUTH_TOKEN", "").strip()
_RUNPOD_TIMEOUT_S = 10  # HTTP 위임 응답 대기 (Pod 은 202 즉시 반환 — 늦으면 장애)


def _runpod_enabled() -> bool:
    return bool(_RUNPOD_URL and _RUNPOD_TOKEN)


def _delegate_to_runpod(bucket: str, key: str) -> None:
    """RunPod /analyze 로 위임. 202/200 외 응답은 예외 → Lambda 가 fail_analysis 매핑.
    urllib 표준 라이브러리만 사용(requests 의존성 X — Layer 추가 부담 없음).

    RunPod proxy(*.proxy.runpod.net) 는 Cloudflare 뒤에 있다. urllib 의 기본
    User-Agent("Python-urllib/3.x") 가 Cloudflare 의 봇 차단(에러 1010) 에 걸려
    403 이 떨어진다. 일반적인 UA 와 Accept 헤더를 박아 통과시킨다."""
    payload = json.dumps({"bucket": bucket, "key": key}).encode("utf-8")
    req = urllib.request.Request(
        _RUNPOD_URL,
        method="POST",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "sunity-motion-pilot/1.0 (+aws-lambda)",
            "X-RunPod-Token": _RUNPOD_TOKEN,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_RUNPOD_TIMEOUT_S) as resp:
            if resp.status not in (200, 202):
                body = resp.read()[:512]
                raise RuntimeError(f"runpod {resp.status}: {body!r}")
    except urllib.error.HTTPError as e:
        body = e.read()[:512] if hasattr(e, "read") else b""
        raise RuntimeError(f"runpod HTTPError {e.code}: {body!r}") from e


# ML 어댑터 (폴백 경로 전용). RunPod 위임 사용 시 이 어댑터는 호출되지 않으므로
# Lambda 콜드스타트 비용도 절감 — 모듈 로드 시 즉시 생성하던 동작을 지연 생성으로
# 바꿔 RunPod 모드에서 NLF/ffmpeg/torch import 비용을 회피한다.
_FRAME_EXTRACTOR = None  # type: ignore[var-annotated]
_POSE_ESTIMATOR = None  # type: ignore[var-annotated]
_COACH_WRITER = None  # type: ignore[var-annotated]


def _ensure_adapters() -> None:
    """폴백 처리(_process) 진입 시 1회 어댑터 생성 + lazy import.
    RunPod 모드에선 이 함수가 호출되지 않아 imageio·torch 도 import 안 됨."""
    global _FRAME_EXTRACTOR, _POSE_ESTIMATOR, _COACH_WRITER
    if _FRAME_EXTRACTOR is None:
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        _FRAME_EXTRACTOR = FfmpegFrameExtractor()
    if _POSE_ESTIMATOR is None:
        from sunity_shared.analysis.pose_estimator import NlfPoseEstimator
        _POSE_ESTIMATOR = NlfPoseEstimator()
    if _COACH_WRITER is None:
        from sunity_shared.analysis.coach_writer import CerebrasCoachWriter
        _COACH_WRITER = CerebrasCoachWriter()


def _signed_get(bucket: str, key: str) -> str:
    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=_PLAYBACK_EXPIRES,
    )


def _angles_from_video(bucket: str, key: str) -> np.ndarray:
    """S3 영상 → 프레임 → NLF 3D keypoints → 관절각(T,J), 시간축 폐색 보간."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        _s3.download_file(bucket, key, tmp.name)
        frames = _FRAME_EXTRACTOR.extract(tmp.name)
    keypoints = _POSE_ESTIMATOR.estimate(frames)  # (T,17,4) — 미감지 시 NoHumanError
    angles = compute_joint_angles(keypoints)
    return temporal_fill(angles, joint_uncertainty(keypoints))


def _process(bucket: str, key: str, uid: str, analysis_id: str) -> None:
    _ensure_adapters()
    firestore_admin.update_analysis_status(uid, analysis_id, models.STATUS_QUEUED)

    meta = firestore_admin.get_analysis(uid, analysis_id)
    if meta is None:
        raise RuntimeError(f"분석 문서 없음 users/{uid}/analyses/{analysis_id}")
    mode = meta.get("mode")

    firestore_admin.update_analysis_status(
        uid, analysis_id, models.STATUS_FRAME_EXTRACTION
    )
    firestore_admin.update_analysis_status(
        uid, analysis_id, models.STATUS_POSE_ANALYSIS
    )
    angles = _angles_from_video(bucket, key)

    firestore_admin.update_analysis_status(
        uid, analysis_id, models.STATUS_COMPARISON
    )
    my_video_url = _signed_get(bucket, key)
    reference_video_url = None

    if mode == models.MODE_EXPERT:
        ref = firestore_admin.get_reference_motion(meta.get("referenceMotionId"))
        if ref is None or "angles" not in ref:
            raise RuntimeError("기준 모션 또는 keyframe 데이터 없음")
        # seed 는 Firestore 의 nested-array 금지 회피로 angles 를 flat 저장.
        # anglesJointKeys 길이로 (T, J) 복원.
        a_ref = np.asarray(ref["angles"], dtype=float)
        if a_ref.ndim == 1:
            num_joints = len(ref.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
            a_ref = a_ref.reshape(-1, num_joints)
        match = motion_dtw(feature_vector(angles), feature_vector(a_ref))
        user_seg = angles[match.start : match.end]
        deviation = per_joint_deviation(match.path, user_seg, a_ref)
        assessments = kismam.assess(deviation)
        similarity = kismam.overall_score(assessments)
        # 콤보 모션이면 베이스/확장 구간 부분 점수 (reference-motions.md §7).
        seg_scores = None
        if ref.get("sharedBaseMotionId"):
            base_ref = firestore_admin.get_reference_motion(
                ref["sharedBaseMotionId"]
            )
            seg_scores = segments.segment_scores(
                ref,
                (base_ref or {}).get("name", ""),
                match.path,
                user_seg,
                a_ref,
            )
        comparison = assemble.build_mode1(ref, similarity, seg_scores)
        if ref.get("videoS3Key"):
            reference_video_url = _signed_get(bucket, ref["videoS3Key"])
    else:  # MODE_SELF — 좌우 대칭 자기 기준
        assessments = kismam.assess(selfmotion.symmetry_deviation(angles))
        prev = firestore_admin.get_previous_analysis(uid, analysis_id)
        comparison = assemble.build_mode3(
            is_first=prev is None,
            previous_analysis_id=prev.get("analysisId") if prev else None,
            prev_part_scores=(prev or {}).get("result", {}).get("partScores"),
            cur_part_scores=kismam.part_scores(assessments),
        )

    coach_details = _COACH_WRITER.write(
        {
            "mode": mode,
            "joints": [
                {
                    "key": a.key,
                    "labelKo": a.label_ko,
                    "deviation_deg": a.deviation_deg,
                    "direction": a.direction,
                }
                for a in kismam.top_issues(assessments, n=3)
            ],
        }
    )
    result = assemble.build_result(
        assessments,
        comparison,
        my_video_url,
        reference_video_url=reference_video_url,
        coach_details=coach_details,
    )
    firestore_admin.complete_analysis(uid, analysis_id, result)
    log.info("분석 완료 uid=%s analysis_id=%s mode=%s", uid, analysis_id, mode)


def lambda_handler(event: dict, _context) -> dict:
    """SQS 이벤트 → 메시지마다 RunPod 위임 또는 직접 처리.

    RunPod 위임 분기: _runpod_enabled() True 시 status=queued 로 일단 표시하고
    HTTP POST. Pod 가 202 를 반환하면 그 이후 status 갱신은 RunPod 서버가 책임.
    위임 호출 자체가 실패하면(타임아웃·5xx) ERR_SERVER_ERROR 로 매핑.
    """
    processed = 0
    delegated = _runpod_enabled()
    if delegated:
        log.info("RunPod 위임 모드 ON url=%s", _RUNPOD_URL)
    for bucket, key in iter_s3_keys_from_sqs(event):
        parsed = parse_upload_key(key)
        if parsed is None:
            log.warning("스킵: 인식 불가 S3 키 %s", key)
            continue
        uid, analysis_id = parsed.uid, parsed.analysis_id
        try:
            if delegated:
                # 위임 시 Lambda 는 queued 까지만 갱신. 그 이후 단계는 RunPod 책임.
                firestore_admin.update_analysis_status(
                    uid, analysis_id, models.STATUS_QUEUED
                )
                _delegate_to_runpod(bucket, key)
            else:
                _process(bucket, key, uid, analysis_id)
            processed += 1
        except NoHumanError:
            log.info("인체 미감지 uid=%s analysis_id=%s", uid, analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_NO_HUMAN,
                models.ERROR_MESSAGE[models.ERR_NO_HUMAN],
            )
        except Exception:  # noqa: BLE001
            log.exception("분석 실패 analysis_id=%s", analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_SERVER_ERROR,
                models.ERROR_MESSAGE[models.ERR_SERVER_ERROR],
            )
    return {"processed": processed}
