"""정은지 reference 5개 영상의 두 필드 백필 데이터 측정. Pod GPU 직접 실행 (CPU NaN).

R2 fix (2026-06-08 round-2, Plan 06-03): bodyNormalizationProfile +
bodyComparisonSourcePose 두 필드를 함께 산출. 대표 frame 선정 = pose_frames 중
평균 keypoint confidence (= 1 - uncertainty_proxy) 가장 높은 frame (단순/robust).

산출 = JSON fixture (`reference-body-data.json`) — 로컬 다운로드 후
`node app/scripts/seed-reference-body-profile.mjs` 으로 Firestore atomic merge.

실행 (W3 — 직접 실행, `-m` 미사용):
  python backend/scripts/extract_reference_body_profiles.py \\
      --bucket sunity-motion-pilot-videos \\
      --output /workspace/reference-body-data.json

C5 fix: --dry-run 플래그 — Firestore write 없이 proposed JSON 만 stdout 출력
(blast radius 1차 검증). dry-run 시에도 S3 download + RTMW estimate + measure 모두
실행 (실 측정이 본질).

[per [[runpod-gpu-env]], [[gsd-pod-work-push-first]], R2 fix (2026-06-08 round-2),
 W3, C5 (--dry-run), Plan 06-03 Task 2]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# W3 — sys.path 주입 (in-script, `-m` 미사용).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

# R2 — BodyComparisonSourcePose 는 pure-numpy dependency 만 — top-level import OK.
from sunity_shared.analysis.body_normalizer import (  # noqa: E402
    BodyComparisonSourcePose,
)
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES  # noqa: E402

# 헤비 의존 (imageio / rtmlib / boto3) 는 main() 안에서 lazy import — `--help`
# 가 Mac 로컬 환경에서도 exit 0 가능 (의존성 부재 시 fail-fast 는 측정 실행 시).

# Logging — per-motion 진행 + body confidence + source_pose 존재 여부.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("extract_reference_body_profiles")


# Plan 06-03 기본 5개 motion (정은지 reference).
DEFAULT_MOTION_IDS: tuple[str, ...] = (
    "ref-climb",
    "ref-foxtop",
    "ref-foxtop-split",
    "ref-invert",
    "ref-sideway-spin",
)


def _bp_to_camel_dict(bp) -> dict:
    """BodyNormalizationProfile dataclass → Firestore camelCase dict (7 필드)."""
    return {
        "estimatedHeightScale": float(bp.estimated_height_scale),
        "armScale": float(bp.arm_scale),
        "legScale": float(bp.leg_scale),
        "torsoScale": float(bp.torso_scale),
        "shoulderHipRatio": float(bp.shoulder_hip_ratio),
        "confidence": float(bp.confidence),
        # warnings 는 list[str] — Firestore flat 허용 (W5 정합).
        "warnings": list(bp.warnings),
    }


def _sp_to_camel_dict(sp: BodyComparisonSourcePose) -> dict:
    """BodyComparisonSourcePose dataclass → Firestore camelCase dict (6 필드)."""
    return {
        "jointKeys": list(sp.joint_keys),
        # values 는 flat list[float] — Firestore nested-array 회피 핵심.
        "values": list(sp.values),
        "frameIndex": int(sp.frame_index),
        "torsoPx": float(sp.torso_px),
        "confidence": float(sp.confidence),
        "measuredAt": int(sp.measured_at),
    }


def _representative_frame_confidence(pose_frame) -> float:
    """frame 의 평균 keypoint confidence (= 1 - uncertainty_proxy).

    keypoints_3d 가 비어있으면 0.0 반환.
    """
    kp = getattr(pose_frame, "keypoints_3d", None) or {}
    if not kp:
        return 0.0
    confs: list[float] = []
    for name in KEYPOINT_NAMES:
        if name in kp:
            confs.append(float(getattr(kp[name], "confidence", 0.0)))
    if not confs:
        return 0.0
    return sum(confs) / len(confs)


def _frame_torso_px(pose_frame) -> float:
    """단일 frame 의 mid_shoulder ↔ mid_hip 거리 (3D Euclidean).

    keypoints_3d 좌표계는 RTMW path 에서 image 픽셀 (x/y) + z (depth) 기준.
    Plan 06-02 _extract_target_torso_px 와 동일 산식 (단일 frame 버전).

    WR-04 (2026-06-08 review): 3D Euclidean (x/y/z) 사용 — pipeline 의 target
    측정과 self-consistent. 2D 만으로는 lean/fold 자세에서 비현실적으로 작은
    anchor 산출 → reproject segment 비례 축소.

    Endpoint 미감지 시 0.0 반환.
    """
    kp = getattr(pose_frame, "keypoints_3d", None) or {}
    needed = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
    if not all(n in kp for n in needed):
        return 0.0
    ls, rs, lh, rh = (kp[n] for n in needed)
    ms_x = (ls.x + rs.x) / 2
    ms_y = (ls.y + rs.y) / 2
    ms_z = (ls.z + rs.z) / 2
    mh_x = (lh.x + rh.x) / 2
    mh_y = (lh.y + rh.y) / 2
    mh_z = (lh.z + rh.z) / 2
    dx = mh_x - ms_x
    dy = mh_y - ms_y
    dz = mh_z - ms_z
    d = (dx * dx + dy * dy + dz * dz) ** 0.5
    if not np.isfinite(d) or d <= 0:
        return 0.0
    return float(d)


def _build_source_pose(
    pose_frames: list,
) -> tuple[dict | None, int | None, float | None]:
    """대표 frame 선정 + BodyComparisonSourcePose 산출.

    선정 = 평균 keypoint confidence 가장 높은 frame (단순/robust).
    Hold-window 메타가 미존재 (Plan 06-03 fallback default).

    Returns:
        (source_pose_dict | None, representative_frame_idx | None, mean_conf | None).
        실패 (모든 frame conf=0 또는 torso_px=0 또는 validator 위반) 시 (None, None, None).
    """
    if not pose_frames:
        return None, None, None

    # 평균 confidence 최대 frame.
    confs = [_representative_frame_confidence(f) for f in pose_frames]
    if not confs or max(confs) <= 0.0:
        log.warning("source_pose 산출 실패 — 모든 frame keypoint confidence 0")
        return None, None, None

    rep_idx = int(np.argmax(confs))
    rep_frame = pose_frames[rep_idx]
    rep_conf = float(confs[rep_idx])

    torso_px = _frame_torso_px(rep_frame)
    if torso_px <= 0:
        log.warning(
            "source_pose 산출 실패 — 대표 frame %d 의 torso_px <= 0", rep_idx
        )
        return None, None, None

    # 17 keypoint × 4채널 flat values 산출 — to_coco17_array 의 단일 frame 슬라이스.
    from sunity_shared.analysis.pose_frame import to_coco17_array

    single = to_coco17_array([rep_frame])  # (1, 17, 4)
    flat = np.asarray(single).reshape(-1)  # length = 68

    # NaN 검사 — 미감지 keypoint 가 있으면 BodyComparisonSourcePose validator 가
    # ValueError. dryrun/realrun 모두 동일하게 fallback (None) 처리.
    if not np.isfinite(flat).all():
        nan_count = int((~np.isfinite(flat)).sum())
        log.warning(
            "source_pose 산출 실패 — 대표 frame %d 의 values 에 NaN %d 개",
            rep_idx,
            nan_count,
        )
        return None, None, None

    try:
        sp = BodyComparisonSourcePose(
            joint_keys=tuple(KEYPOINT_NAMES),
            values=tuple(float(v) for v in flat.tolist()),
            frame_index=int(rep_idx),
            torso_px=float(torso_px),
            confidence=float(min(max(rep_conf, 0.0), 1.0)),
            measured_at=int(time.time() * 1000),
        )
    except ValueError as e:
        log.warning("BodyComparisonSourcePose validation 실패: %s", e)
        return None, None, None

    return _sp_to_camel_dict(sp), rep_idx, rep_conf


def _download_video(s3_client, bucket: str, motion_id: str, target: Path) -> None:
    key = f"reference/{motion_id}.mp4"
    log.info("S3 download s3://%s/%s → %s", bucket, key, target.name)
    s3_client.download_file(bucket, key, str(target))


def _measure_one(
    motion_id: str,
    video_path: Path,
    extractor,
    rtmw_engine,
) -> dict:
    """단일 motion → {"bodyNormalizationProfile": dict, "bodyComparisonSourcePose": dict | None}."""
    # lazy import — Mac 로컬 (--help) 에서도 import 가능하도록.
    from sunity_shared.analysis.body_normalization_measurer import (
        measure_body_profile,
    )
    from sunity_shared.analysis.pose_frame import PoleAxis

    t0 = time.time()
    frames = extractor.extract(str(video_path))
    # RTMW 운영 path 의 기본 pole_axis — 수직 폴백.
    default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )
    pose_frames = rtmw_engine.estimate(frames, default_pole)
    if not pose_frames:
        raise RuntimeError(f"pose_frames empty for {motion_id}")

    body_profile = measure_body_profile(pose_frames)
    body_profile_dict = _bp_to_camel_dict(body_profile)

    # R2 — 대표 frame + BodyComparisonSourcePose.
    source_pose_dict, rep_idx, rep_conf = _build_source_pose(pose_frames)

    elapsed = time.time() - t0
    log.info(
        "[%s] frames=%d body_conf=%.3f source_pose_present=%s "
        "(rep_idx=%s rep_conf=%s) %.1fs",
        motion_id,
        len(pose_frames),
        body_profile.confidence,
        source_pose_dict is not None,
        rep_idx,
        f"{rep_conf:.3f}" if rep_conf is not None else None,
        elapsed,
    )

    return {
        "bodyNormalizationProfile": body_profile_dict,
        "bodyComparisonSourcePose": source_pose_dict,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "정은지 reference 5개 영상의 두 필드 (bodyNormalizationProfile + "
            "bodyComparisonSourcePose) 백필 데이터 측정. Pod GPU 직접 실행 (CPU NaN). "
            "C5 fix: --dry-run."
        )
    )
    parser.add_argument(
        "--bucket",
        required=True,
        help="S3 bucket (예: sunity-motion-pilot-videos)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="결과 JSON 출력 경로 (예: /workspace/reference-body-data.json)",
    )
    parser.add_argument(
        "--motion-ids",
        default=",".join(DEFAULT_MOTION_IDS),
        help=(
            "쉼표 분리 motion id list. 기본은 정은지 reference 5개. "
            "디버그 용도로 일부만 측정 가능."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "C5 fix — Firestore write 없이 proposed JSON 만 stdout 출력. "
            "파일 미생성. 실 측정 + 산출은 동일 (blast radius 1차 검증)."
        ),
    )
    args = parser.parse_args()

    motion_ids = [m.strip() for m in args.motion_ids.split(",") if m.strip()]
    if not motion_ids:
        print("--motion-ids 가 비어있음", file=sys.stderr)
        sys.exit(1)

    # boto3 — Lambda 런타임엔 항상, RunPod 베이스 이미지엔 별도 install 필요.
    try:
        import boto3
    except ImportError:
        print("boto3 없음. pip install boto3 후 재시도.", file=sys.stderr)
        sys.exit(1)

    region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION")
    if not region:
        print(
            "AWS_DEFAULT_REGION 환경변수 필요 (예: ap-northeast-2).",
            file=sys.stderr,
        )
        sys.exit(1)

    s3 = boto3.client("s3", region_name=region)

    # imageio (FfmpegFrameExtractor 의존) — Pod 에서만 install.
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    extractor = FfmpegFrameExtractor()

    # RTMW engine — rtmlib 의존, Pod GPU 전용. import 단계에서 fail-fast.
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import (
        RTMWPoseEngine,
    )

    rtmw_engine = RTMWPoseEngine()

    log.info(
        "extract_reference_body_profiles start motions=%d mode=%s",
        len(motion_ids),
        "dry-run" if args.dry_run else "real-run",
    )

    motions_out: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for motion_id in motion_ids:
            log.info("--- %s ---", motion_id)
            try:
                video_path = td_path / f"{motion_id}.mp4"
                _download_video(s3, args.bucket, motion_id, video_path)
                motions_out[motion_id] = _measure_one(
                    motion_id, video_path, extractor, rtmw_engine
                )
            except Exception:
                log.error(
                    "[%s] FAIL — %s",
                    motion_id,
                    traceback.format_exc(),
                )

    payload = {
        "motions": motions_out,
        "measuredAt": datetime.now(timezone.utc).isoformat(),
        "rtmwOnnxPath": os.environ.get("RTMW_ONNX_PATH"),
    }

    if args.dry_run:
        # C5 fix — dry-run path: stdout 만, 파일 미생성.
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        log.info(
            "dry-run 완료 — %d/%d motion 측정. 파일 미생성.",
            len(motions_out),
            len(motion_ids),
        )
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    size_kb = args.output.stat().st_size / 1024
    log.info(
        "real-run 완료 — %d/%d motion 측정. → %s (%.1f KB)",
        len(motions_out),
        len(motion_ids),
        args.output,
        size_kb,
    )
    log.info(
        "belle: 이 파일을 로컬로 받아 다음 단계 실행:\n"
        "  scp <pod>:%s ./reference-body-data.json\n"
        "  cd app && npm run seed:body-profile -- --profiles ../reference-body-data.json --dry-run\n"
        "  (검증 후) cd app && npm run seed:body-profile -- --profiles ../reference-body-data.json",
        args.output,
    )


if __name__ == "__main__":
    main()
