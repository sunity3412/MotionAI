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
import threading
import urllib.error
import urllib.request
from pathlib import Path

import boto3  # Lambda 런타임 제공
import numpy as np

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import (
    assemble,
    dimensions,
    kismam,
    segments,
    skeleton,
    technique,
)
from sunity_shared.analysis.features import (
    compute_joint_angles,
    feature_vector,
    joint_uncertainty,
)
from sunity_shared.analysis.interfaces import NoHumanError, NotPoleMotionError  # 가벼움 — 예외만
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
# 결과 화면 영상 재생 서명 URL 만료(초). 7일 = sigv4 + 영구 IAM 키의 최대값.
# 3600s 였을 때 belle 가 시연 후 다시 결과 화면을 열면 URL 이 만료돼 본인 영상이
# 비어 보였다(P0 #6). 운영 경로(RunPod)는 sunity-motion 영구 키로 서명하므로
# 7일 풀로 사용 가능. Lambda 폴백 경로의 임시 자격증명은 세션 길이로 자동 캡됨.
_PLAYBACK_EXPIRES = 7 * 24 * 60 * 60

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

# 기술 인식 어댑터 — swappable (technique.TechniqueRecognizer 프로토콜).
# Plan 5-03 박제 — 즉시 생성 박제 X → `_ensure_recognizer()` lazy creation 분기.
#
# 박제 정신 (D-12 / D-16 / Plan 5-03):
#   · D-12: RunPod server.py 무수정 1pass — pipeline 모듈 1점 swap 박제로 자동 작동.
#   · D-16: lazy import — pipeline 모듈 로드 시 google.genai / firebase_admin / boto3
#     (Lambda 런타임 제외) 0 import. Gemini 모드 진입 시점에만 lazy import.
#   · default = FallbackRecognizer (env 미설정 시) — 회귀 위험 최소 + A/B 비교 가능.
#
# env switch 박제 (둘 중 하나):
#   · GEMINI_RECOGNIZER_ENABLED=1|true|on|yes  (case-insensitive)
#   · RECOGNIZER_BACKEND=gemini                 (case-insensitive)
# 그 외 (미설정 / 다른 값) = FallbackRecognizer 박제 보존.
_RECOGNIZER: technique.TechniqueRecognizer | None = None
_RECOGNIZER_LOCK = threading.Lock()

# env switch 박제 값 (case-insensitive lower).
_GEMINI_ENV_TRUTHY = frozenset({"1", "true", "on", "yes", "gemini"})


def _gemini_enabled() -> bool:
    """env 기반 Gemini 어댑터 활성 여부 박제.

    두 env var 박제 (호환 alias):
      · GEMINI_RECOGNIZER_ENABLED — Plan 5-03 신설 박제
      · RECOGNIZER_BACKEND        — 기존 RunPod env 박제 패턴 정합

    case-insensitive. 박제 truthy 값 = {"1", "true", "on", "yes", "gemini"}.
    그 외 또는 미설정 = False (FallbackRecognizer 박제 보존).
    """
    for env_var in ("GEMINI_RECOGNIZER_ENABLED", "RECOGNIZER_BACKEND"):
        val = os.environ.get(env_var, "").strip().lower()
        if val in _GEMINI_ENV_TRUTHY:
            return True
    return False


def _ensure_recognizer() -> technique.TechniqueRecognizer:
    """lazy creation + env switch 박제 (Plan 5-03).

    double-checked locking 박제로 thread 안전 — Pod uvicorn 은 `--workers 1` 박제
    기본이지만 BackgroundTasks 가 다중 분석 동시 진입 가능 (다중 SQS 메시지).

    분기:
      · env switch ON  → GeminiTechniqueRecognizer + TechniqueCache + record_unregistered_keyword hook 합성
      · env switch OFF → FallbackRecognizer 박제 (회귀 0)

    return: technique.TechniqueRecognizer 인스턴스 (멱등 — 2회 호출 = 같은 instance).
    """
    global _RECOGNIZER
    if _RECOGNIZER is not None:
        return _RECOGNIZER
    with _RECOGNIZER_LOCK:
        if _RECOGNIZER is not None:
            return _RECOGNIZER
        if _gemini_enabled():
            # D-16 lazy import — Gemini 모드 진입 시점에만 import.
            from sunity_shared.analysis.gemini_technique_recognizer import (
                GeminiTechniqueRecognizer,
            )
            from sunity_shared.analysis.technique_cache import TechniqueCache

            cache = TechniqueCache()
            # D-09 case 3 박제 — Phase 16 TERM-DATA-01 분기 3 자동 수집 hook.
            # uid = "anonymous-pipeline" 박제 (Pod 가 호출 시점 uid 정보 없음 — _process
            # caller 시점에서 알지만 cache 생성 시점엔 미상). 향후 hook 시그너처에
            # uid 주입 path 별 plan 책임.
            def _record_unregistered(keyword: str, video_hash: str) -> None:
                firestore_admin.record_unregistered_keyword(
                    keyword, uid="anonymous-pipeline", video_hash=video_hash
                )

            _RECOGNIZER = GeminiTechniqueRecognizer(
                cache=cache,
                unregistered_hook=_record_unregistered,
            )
            log.info("Recognizer = GeminiTechniqueRecognizer (env switch ON)")
        else:
            _RECOGNIZER = technique.FallbackRecognizer()
            log.info("Recognizer = Fallback (env switch OFF — default)")
        return _RECOGNIZER


class _RTMWNlfCompat:
    """Plan 25 atomic swap (2026-06-05): RTMW → NLF interface 호환 어댑터.

    pipeline/_process 의 `_POSE_ESTIMATOR.estimate(frames) → np.ndarray (T,17,4)` 호출
    유지. 내부에서 RTMWPoseEngine + vertical pole_axis fallback + to_coco17_array 변환.

    박제 정신 [[rtmw-free-stack-pivot]] 정합 — NLF/ultralytics 의존 제거.
    """

    def __init__(self) -> None:
        from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
        from sunity_shared.analysis.pose_frame import PoleAxis
        self._engine = RTMWPoseEngine()
        self._default_pole = PoleAxis(
            axis_vector=(0.0, 1.0, 0.0),
            confidence_level="low",
            source="vertical_fallback",
            frame_index=None,
        )

    def estimate(self, frames):
        """RTMW pose estimation → COCO-17 array (T,17,4) — NLF 호환 interface."""
        from sunity_shared.analysis.pose_frame import to_coco17_array
        pose_frames = self._engine.estimate(frames, self._default_pole)
        return to_coco17_array(pose_frames)


def _ensure_adapters() -> None:
    """폴백 처리(_process) 진입 시 1회 어댑터 생성 + lazy import.
    RunPod 모드에선 이 함수가 호출되지 않아 imageio·torch 도 import 안 됨.

    Plan 25 atomic swap (2026-06-05): NlfPoseEstimator → _RTMWNlfCompat (RTMW 기반,
    NLF interface 호환). 박제 정신 [[rtmw-free-stack-pivot]] 정합.
    """
    global _FRAME_EXTRACTOR, _POSE_ESTIMATOR, _COACH_WRITER
    if _FRAME_EXTRACTOR is None:
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        _FRAME_EXTRACTOR = FfmpegFrameExtractor()
    if _POSE_ESTIMATOR is None:
        _POSE_ESTIMATOR = _RTMWNlfCompat()
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
    """S3 영상 → 프레임 → NLF 3D keypoints → 관절각(T,J), 시간축 폐색 보간.

    B8 fix (2026-06-04 revision) — 시그너처 무변경 유지 박제. RunPod server.py
    `_process` 호출이 본 함수 path 를 직접 사용 X (server.py 는 pipeline 모듈을
    import 만 함). 본 함수의 시그너처는 단위 테스트가 박제로 검증 — 변경 시
    test_pipeline_recognizer_switch.TestB8FixSignature 가 차단.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        _s3.download_file(bucket, key, tmp.name)
        frames = _FRAME_EXTRACTOR.extract(tmp.name)
    keypoints = _POSE_ESTIMATOR.estimate(frames)  # (T,17,4) — 미감지 시 NoHumanError
    angles = compute_joint_angles(keypoints)
    return temporal_fill(angles, joint_uncertainty(keypoints))


def _angles_and_video_path_from_video(
    bucket: str, key: str
) -> tuple[np.ndarray, str]:
    """B8 fix (2026-06-04 revision) — Gemini 어댑터 path 전용 helper 박제.

    `_angles_from_video` 의 변형 — frames 인자로 local video path 가 필요한
    GeminiTechniqueRecognizer.recognize 호출 path 만 사용. delete=False
    tempfile 박제 — caller (`_process` Gemini 분기) 가 finally 에서 unlink 책임.

    박제 사유 (B8 fix):
      · 기존 `_angles_from_video` 시그너처 무변경 — 회귀 위험 0
      · RunPod server.py D-12 무수정 박제 정합 (호출처 갱신 0)
      · 신설 함수 분리 — 호출처 명시적 분기 (Gemini path 만 사용)

    Returns:
      (angles_filled, local_video_path) — caller 가 video_path 를 Gemini File API
      에 전달 + 분석 끝나면 unlink 박제.

    Raises:
      예외 발생 시 임시 파일 즉시 unlink 박제 (디스크 누수 보호).
    """
    _ensure_adapters()
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        _s3.download_file(bucket, key, tmp_path)
        frames = _FRAME_EXTRACTOR.extract(tmp_path)
        keypoints = _POSE_ESTIMATOR.estimate(frames)
        angles = compute_joint_angles(keypoints)
        angles_filled = temporal_fill(angles, joint_uncertainty(keypoints))
        return angles_filled, tmp_path
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def _deviation_against(
    user_angles: np.ndarray, ref_angles_flat, num_joints: int
):
    """기준 시퀀스 대비 관절별 각도 편차(도) — mode1(정은지)·mode3 second+(이전 영상)
    공용 코어. flat 저장 angles 를 reshape → DTW 정렬 → per_joint_deviation.
    반환: (deviation(J,), match, user_seg, a_ref) — mode1 은 segment 점수에 match 사용."""
    a_ref = np.asarray(ref_angles_flat, dtype=float)
    if a_ref.ndim == 1:
        a_ref = a_ref.reshape(-1, num_joints)
    match = motion_dtw(feature_vector(user_angles), feature_vector(a_ref))
    user_seg = user_angles[match.start : match.end]
    deviation = per_joint_deviation(match.path, user_seg, a_ref)
    return deviation, match, user_seg, a_ref


def _mode3_comparison(
    angles: np.ndarray, prev: dict | None, profile: technique.TechniqueProfile
):
    """자기 성장(mode3) 분기 — 순수(어댑터/S3/Firestore 불필요, 테스트 가능).

    절대 차원(라인/안정성)은 기준 없이 산출 → 세션 간 같은 척도라 발전 측정 가능
    ([[mode3-progress-not-similarity]]). 각도 차원은 기준이 필요하므로 이전 분석이
    있을 때만(이전 영상 대비 일관성) 표시하고 overall/delta 에선 제외(척도 안정).

    반환: (assessments, dimension_scores, overall, comparison).
      - assessments: 관절각 기반(코칭 tips 용). 첫 분석은 신전 부족분(IPSF 라인),
        이후는 이전 영상 대비.
      - dimension_scores: 첫 분석=절대 차원, 이후=절대 + angle(일관성).
      - overall: 절대 차원 평균(첫 분석/이후 동일 척도)."""
    abs_dims = dimensions.absolute_dimension_scores(angles, profile)
    prev_angles = (prev or {}).get("angles")
    if not prev or not prev_angles:
        # 첫 분석(또는 이전 angles 미저장) — 비교 대상 없음. 코칭은 신전 부족분(IPSF 라인) 기준.
        overall = dimensions.overall_from_dimensions(abs_dims)
        assessments = kismam.assess(dimensions.extension_deviation(angles, profile))
        return assessments, abs_dims, overall, assemble.build_mode3(is_first=True)
    num_joints = len(prev.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    deviation, *_ = _deviation_against(angles, prev_angles, num_joints)
    assessments = kismam.assess(deviation)
    dim_scores = {dimensions.DIM_ANGLE: kismam.overall_score(assessments), **abs_dims}
    # 박제 (2026-06-06 belle): mode3 second+ overall = 모든 차원 평균.
    # 이전 박제 = abs_dims 만 평균 (박제 메모 [[mode3-progress-not-similarity]] 정신).
    # belle 의문: "각도 100, 안정성 93 인데 총점 93? 각도 점수 어디 가나" — 정합.
    # overall 박제 변경 = (angle + line + stability) 평균. delta 박제는 abs_dims 만
    # 유지 (절대 척도 안정 — 박제 메모 정신 유지).
    overall = dimensions.overall_from_dimensions(dim_scores)
    prev_dims = (prev.get("result") or {}).get("dimensionScores")
    comparison = assemble.build_mode3(
        is_first=False,
        previous_analysis_id=prev.get("analysisId"),
        prev_dimension_scores=prev_dims,
        cur_dimension_scores=abs_dims,  # 발전 델타는 절대 3차원만(같은 척도)
    )
    return assessments, dim_scores, overall, comparison


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

    # Plan 5-03 박제 — env switch ON 분기 시 video path 가 Gemini File API 입력으로
    # 필요. 박제 사유: Gemini 어댑터의 recognize(angles, frames=local_video_path) 호출
    # path. env 미설정 시 기존 path (회귀 0) 박제 보존.
    recognizer = _ensure_recognizer()
    local_video_path: str | None = None
    if _gemini_enabled():
        angles, local_video_path = _angles_and_video_path_from_video(bucket, key)
    else:
        angles = _angles_from_video(bucket, key)

    # Path A production 정합 (2026-06-05): mode=expert = motion known case
    # (사용자가 referenceMotionId 선택). recognizer.motion_query_hint 박제 →
    # Gemini extractor 가 알려진 motion 기준 key moment 추출 (default 'auto' 폴백 차단).
    # mode=self (mode3) = motion 미상 (본인 영상 비교) → hint 미박제 = 'auto' default.
    ref_motion_id = meta.get("referenceMotionId")
    if mode == models.MODE_EXPERT and ref_motion_id and hasattr(recognizer, "motion_query_hint"):
        recognizer.motion_query_hint = str(ref_motion_id)

    firestore_admin.update_analysis_status(
        uid, analysis_id, models.STATUS_COMPARISON
    )
    my_video_url = _signed_get(bucket, key)
    reference_video_url = None

    try:
        # 기술 인식(swappable) → 절대 차원(라인/안정성)은 기준 영상 없이 항상 산출.
        # Plan 5-03 박제 — recognize(angles, frames=local_video_path) 호출. Gemini
        # 어댑터는 frames 인자 (video path) 를 File API 입력으로 사용. Fallback 은
        # frames 인자 ignore (Protocol 정합 — TestProtocolCompat 박제 검증).
        profile = recognizer.recognize(angles, frames=local_video_path)
        abs_dims = dimensions.absolute_dimension_scores(angles, profile)

        if mode == models.MODE_EXPERT:
            ref = firestore_admin.get_reference_motion(meta.get("referenceMotionId"))
            if ref is None or "angles" not in ref:
                raise RuntimeError("기준 모션 또는 keyframe 데이터 없음")
            # seed 는 Firestore 의 nested-array 금지 회피로 angles 를 flat 저장.
            num_joints = len(ref.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
            deviation, match, user_seg, a_ref = _deviation_against(
                angles, ref["angles"], num_joints
            )
            assessments = kismam.assess(deviation)
            # 각도 정확도 차원 = 정은지 대비 관절각 일치도. 모드1 게이지/일치도이기도 함.
            angle_dim = kismam.overall_score(assessments)
            # 비폴 영상 차단 안전망(belle P1 #8). 기준 동작과 너무 동떨어진 자세는
            # 폴 영상이 아닐 가능성이 높아 의미 없는 점수를 결과 화면에 노출하지 않는다.
            if angle_dim < models.NOT_POLE_SIMILARITY_THRESHOLD:
                log.info(
                    "비폴 영상 추정 차단 angle=%d threshold=%d",
                    angle_dim,
                    models.NOT_POLE_SIMILARITY_THRESHOLD,
                )
                raise NotPoleMotionError(
                    f"angle {angle_dim} < {models.NOT_POLE_SIMILARITY_THRESHOLD}"
                )
            dimension_scores = {dimensions.DIM_ANGLE: angle_dim, **abs_dims}
            overall = dimensions.overall_from_dimensions(dimension_scores)  # 4차원 평균
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
            comparison = assemble.build_mode1(ref, angle_dim, seg_scores)
            if ref.get("videoS3Key"):
                reference_video_url = _signed_get(bucket, ref["videoS3Key"])
        else:  # MODE_SELF — 자기 성장. 절대 차원 + (이전 분석 있으면) 발전 델타.
            # 박제 (2026-06-07 belle): mode=MODE_SELF 박제 — mode1 (정은지) 분석을
            # prev 로 잡는 함정 fix. 같은 mode 안에서만 prev 검색.
            prev = firestore_admin.get_previous_analysis(
                uid, analysis_id, mode=models.MODE_SELF
            )
            assessments, dimension_scores, overall, comparison = _mode3_comparison(
                angles, prev, profile
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
            dimension_scores,
            overall,
            comparison,
            my_video_url,
            reference_video_url=reference_video_url,
            coach_details=coach_details,
            my_video_key=key,  # 박제 (2026-06-06): GET /playback-url 재발급용
            # Phase 12.5 (2026-06-07): dimensionExplanation source 박제 박제
            # — line/stability deficit 가 점수 산식 (line_score/stability_score) 과 동일
            # _select_window + dimensions helpers 사용 (Codex v3 HIGH-2 정합).
            joint_angles=angles,
            profile=profile,
        )
        # 추출 angles 를 flat 저장 — 다음 mode3 분석이 '이전 영상' 기준으로 DTW 비교.
        firestore_admin.complete_analysis(
            uid,
            analysis_id,
            result,
            angles=np.asarray(angles, dtype=float).reshape(-1).tolist(),
            angles_joint_keys=list(skeleton.JOINT_KEYS),
            angles_frames=int(np.asarray(angles).shape[0]),
        )
        log.info("분석 완료 uid=%s analysis_id=%s mode=%s", uid, analysis_id, mode)
    finally:
        # Plan 5-03 박제 — Gemini 어댑터 path 에서 신설한 임시 파일 정리.
        # delete=False NamedTemporaryFile 박제 정신 정합 — caller 책임 (B8 fix).
        # T-05-03-02 (DoS — 디스크 누수) 박제 — try/finally + missing_ok=True.
        if local_video_path is not None:
            Path(local_video_path).unlink(missing_ok=True)


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
        except NotPoleMotionError:
            log.info("비폴 영상 차단 uid=%s analysis_id=%s", uid, analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_NOT_POLE_MOTION,
                models.ERROR_MESSAGE[models.ERR_NOT_POLE_MOTION],
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
