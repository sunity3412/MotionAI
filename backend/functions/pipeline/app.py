"""분석 파이프라인 — S3 업로드 이벤트 → SQS → 이 함수 (비동기).

알고리즘 코어(features/motiondtw/kismam/selfmotion/assemble)는 모델 무관·
유닛 검증됨. 무거운 모델/ffmpeg/Cerebras 는 interfaces 어댑터로 분리:
현재 stub → AWS 컨테이너·가중치·Cerebras 키 준비 후 교체(#7-follow).

오케스트레이션 정직성:
  - 모델 미구현(NotImplementedError)은 가짜 상태로 덮지 않고 그대로 올림
    → SQS 재시도→DLQ 로 가시화(dev). 운영 전 정책 재검토.
  - 인체 미감지(NoHumanError) → contract no_human 으로 실패 기록.
  - 그 외 런타임 오류 → server_error 로 실패 기록(사용자 노출 문구).

상태/오류/경로는 docs/contract.md, 단계는 models.PIPELINE_SEQUENCE.
"""

from __future__ import annotations

import logging
import os
import tempfile

import boto3  # Lambda 런타임 제공
import numpy as np

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import assemble, kismam, selfmotion
from sunity_shared.analysis.features import (
    compute_joint_angles,
    feature_vector,
    fill_gaps,
)
from sunity_shared.analysis.interfaces import (
    FallbackCoachWriter,
    NoHumanError,
    NotImplementedFrameExtractor,
    NotImplementedPoseEstimator,
)
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
from sunity_shared.events import iter_s3_keys_from_sqs
from sunity_shared.s3keys import parse_upload_key

log = logging.getLogger()
log.setLevel(logging.INFO)

_s3 = boto3.client("s3")
_PLAYBACK_EXPIRES = 3600  # 결과 화면 영상 재생 서명 URL 만료(초)

# #7-follow 에서 실제 어댑터로 교체할 지점 (여기만 바꾸면 코어는 그대로)
_FRAME_EXTRACTOR = NotImplementedFrameExtractor()
_POSE_ESTIMATOR = NotImplementedPoseEstimator()
_COACH_WRITER = FallbackCoachWriter()


def _signed_get(bucket: str, key: str) -> str:
    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=_PLAYBACK_EXPIRES,
    )


def _angles_from_video(bucket: str, key: str) -> np.ndarray:
    """S3 영상 → 프레임 → keypoints → 관절각(T,J), 결측 보간."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        _s3.download_file(bucket, key, tmp.name)
        frames = _FRAME_EXTRACTOR.extract(tmp.name)
    keypoints = _POSE_ESTIMATOR.estimate(frames)  # 미감지 시 NoHumanError
    return fill_gaps(compute_joint_angles(keypoints))


def _process(bucket: str, key: str, uid: str, analysis_id: str) -> None:
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
        a_ref = np.asarray(ref["angles"], dtype=float)
        match = motion_dtw(feature_vector(angles), feature_vector(a_ref))
        deviation = per_joint_deviation(
            match.path, angles[match.start : match.end], a_ref
        )
        assessments = kismam.assess(deviation)
        similarity = kismam.overall_score(assessments)
        comparison = assemble.build_mode1(ref, similarity)
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
        {"mode": mode, "top": [a.key for a in kismam.top_issues(assessments)]}
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
    processed = 0
    for bucket, key in iter_s3_keys_from_sqs(event):
        parsed = parse_upload_key(key)
        if parsed is None:
            log.warning("스킵: 인식 불가 S3 키 %s", key)
            continue
        uid, analysis_id = parsed.uid, parsed.analysis_id
        try:
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
        except NotImplementedError:
            # #7-follow 미구현 — 가짜 상태로 덮지 않고 가시화(DLQ)
            log.exception("파이프라인 미구현 단계 analysis_id=%s", analysis_id)
            raise
        except Exception:  # noqa: BLE001
            log.exception("분석 실패 analysis_id=%s", analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_SERVER_ERROR,
                models.ERROR_MESSAGE[models.ERR_SERVER_ERROR],
            )
    return {"processed": processed}
