"""Phase 17 e2e Issue #4 fix — 신규 6 motion 의 bodyComparisonSourcePose 백필.

박제 정신:
  · Issue #4 — 신규 6 motion (ref-kip-up/ref-peter-pan/ref-power-spin/
    ref-elbow-twist-sister/ref-pdshape/ref-combo) 박힘 `bodyComparisonSourcePose`
    필드 누락. extract_reference_angles.py 박힘 angles 만 추출 + auto-register Lambda
    박힘 body extraction step X.
  · 본 script 박힘 Pod (CUDA + RTMW model 박힘) 박힘 박힘 박힘 박힘:
      1. Firestore reference/{motionId} 박힘 videoS3Key 박힘
      2. S3 박힘 영상 download
      3. RTMW pose estimate → measure_body_profile (BodyNormalizationProfile)
      4. 대표 frame 선택 → BodyComparisonSourcePose dict 박힘
      5. update_reference_body_data(motion_id, profile, source_pose) 박힘 atomic merge
  · 기존 active 5 motion (ref-foxtop 등) 박힘 박힘 박힘 박힘 — `--motions` 박힘 박힘
    박힘.

사용 (Pod):
  cd /workspace/SunityMotion/backend
  export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
  export AWS_DEFAULT_REGION=ap-northeast-2
  export FIREBASE_SA_PATH=/workspace/firebase-sa.json
  python -m scripts.backfill_body_data_new6 [--dry-run] [--motions ref-kip-up ...]
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

from sunity_shared.analysis import skeleton  # noqa: E402
from sunity_shared.analysis.body_normalization_measurer import (  # noqa: E402
    measure_body_profile,
)
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402
from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import (  # noqa: E402
    RTMWPoseEngine,
)
from sunity_shared.analysis.pose_frame import PoleAxis, to_coco17_array  # noqa: E402
from sunity_shared import firestore_admin, models  # noqa: E402

S3_BUCKET = "sunity-motion-pilot-videos"
S3_PREFIX = "reference"

# Issue #4 박힘 — 신규 6 motion 박힘 (Plan 17-07 신설 박힘).
NEW6_MOTION_IDS = [
    "ref-kip-up",
    "ref-peter-pan",
    "ref-power-spin",
    "ref-elbow-twist-sister",
    "ref-pdshape",
    "ref-combo",
]

# RTMW vertical pole_axis fallback — reference 영상 박힘 박힘 박힘 박힘.
_VERTICAL_POLE_AXIS = PoleAxis(
    axis_vector=(0.0, 1.0, 0.0),
    confidence_level="low",
    source="vertical_fallback",
    frame_index=None,
)


def _download_video(s3_client, motion_id: str, target: Path) -> None:
    """Firestore reference/{id}.videoS3Key 박힘 박힘 박힘 박힘 — 박힘 박힘 박힘 단순화 박힘
    convention 박힘 (`reference/{motionId}.mp4`)."""
    key = f"{S3_PREFIX}/{motion_id}.mp4"
    print(f"  S3 download s3://{S3_BUCKET}/{key} → {target.name}")
    s3_client.download_file(S3_BUCKET, key, str(target))


def _select_representative_frame_index(
    coco17_array: np.ndarray,
) -> int:
    """(T, 17, 4) ndarray 박힘 박힘 박힘 박힘 박힘 박힘 박힘 frame index 박힘.

    array[..., 3] 박힘 uncertainty_proxy (D-05) → confidence = 1 - uncertainty.
    NaN 박힘 박힘 박힘 박힘 박힘 박힘 박힘 (np.nanmean) — 미감지 keypoint 박힘 박힘.
    """
    T = coco17_array.shape[0]
    if T == 0:
        raise ValueError("no frames in coco17 array")
    # confidence = 1 - uncertainty_proxy. NaN safe.
    uncertainty = coco17_array[..., 3]  # (T, 17)
    confidence = 1.0 - uncertainty
    # 좌표 NaN frame 박힘 박힘 (미감지) — confidence 박힘 박힘 박힘 X.
    coord_finite = np.isfinite(coco17_array[..., 0])  # (T, 17)
    confidence = np.where(coord_finite, confidence, np.nan)
    frame_conf = np.nanmean(confidence, axis=1)  # (T,)
    # NaN frame 박힘 → -inf 박힘 박힘 (skip)
    frame_conf = np.where(np.isfinite(frame_conf), frame_conf, -np.inf)
    return int(np.argmax(frame_conf))


def _build_source_pose_dict(
    coco17_array: np.ndarray,
    frame_index: int,
    body_profile,
) -> dict:
    """BodyComparisonSourcePose 6 필수 필드 박힘 박힘 박힘 dict (camelCase, flat values).

    firestore_admin.update_reference_body_data 박힘 validator 박힘 박힘:
      - jointKeys: list[str] — skeleton.JOINT_KEYS (8 박힘) X. body_normalizer 박힘
        COCO-17 박힘 박힘 — 박힘 박힘 박힘 17 키 박힘.
      - values: flat list[float] — 4 × len(jointKeys) (x, y, z, conf).
      - frameIndex: int — 대표 frame 박힘.
      - torsoPx: float > 0 — body_profile.torso_px 박힘 박힘.
      - confidence: float in [0, 1] — frame 박힘 박힘 confidence 평균.
      - measuredAt: int ms epoch.
    """
    kps = coco17_array[frame_index]  # (17, 4) — [x, y, z, uncertainty_proxy]
    if kps is None or kps.size == 0:
        raise ValueError(f"frame {frame_index} has empty keypoints")
    # COCO-17 박힘 — pose_frame.KEYPOINT_NAMES 박힘 박힘 박힘 (to_coco17_array 박힘 박힘).
    COCO17_JOINT_KEYS = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle",
    ]
    flat_values: list[float] = []
    for j in range(17):
        x = float(kps[j, 0]) if np.isfinite(kps[j, 0]) else 0.0
        y = float(kps[j, 1]) if np.isfinite(kps[j, 1]) else 0.0
        z = float(kps[j, 2]) if np.isfinite(kps[j, 2]) else 0.0
        uncertainty = float(kps[j, 3]) if np.isfinite(kps[j, 3]) else 1.0
        confidence = max(0.0, min(1.0, 1.0 - uncertainty))
        flat_values.extend([x, y, z, confidence])
    # torso px — body_profile 박힘 박힘 torso_px 필드 X (BodyNormalizationProfile 박힘
    # ratio 박힘 박힘). 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 좌측 어깨(5) ↔ 좌측 골반(11)
    # 거리 (px-space proxy — z 박힘 박힘 박힘 X).
    ls_xy = np.array([kps[5, 0], kps[5, 1]])
    lh_xy = np.array([kps[11, 0], kps[11, 1]])
    if np.isfinite(ls_xy).all() and np.isfinite(lh_xy).all():
        torso_px = float(np.linalg.norm(ls_xy - lh_xy))
    else:
        torso_px = 0.0
    if not np.isfinite(torso_px) or torso_px <= 0:
        torso_px = 1.0  # validator 박힘 > 0 강제
    # confidence — 박힘 frame 박힘 박힘 박힘 (1 - mean uncertainty).
    mean_uncertainty = float(np.nanmean(kps[:, 3]))
    mean_conf = max(0.0, min(1.0, 1.0 - mean_uncertainty))
    return {
        "jointKeys": COCO17_JOINT_KEYS,
        "values": flat_values,
        "frameIndex": int(frame_index),
        "torsoPx": torso_px,
        "confidence": mean_conf,
        "measuredAt": int(time.time() * 1000),
    }


def _build_body_profile_dict(profile) -> dict:
    """measure_body_profile 박힘 박힘 (BodyNormalizationProfile dataclass) → camelCase dict.

    firestore_admin._REF_BODY_PROFILE_REQUIRED 박힘 박힘 박힘 7 필드 박힘 박힘:
      estimatedHeightScale / armScale / legScale / torsoScale / shoulderHipRatio /
      confidence / warnings.
    """
    raw = dataclasses.asdict(profile)
    return {
        "estimatedHeightScale": float(raw["estimated_height_scale"]),
        "armScale": float(raw["arm_scale"]),
        "legScale": float(raw["leg_scale"]),
        "torsoScale": float(raw["torso_scale"]),
        "shoulderHipRatio": float(raw["shoulder_hip_ratio"]),
        "confidence": float(raw["confidence"]),
        "warnings": list(raw.get("warnings") or []),
    }


def _backfill_one(
    motion_id: str,
    video_path: Path,
    extractor: FfmpegFrameExtractor,
    engine: RTMWPoseEngine,
    dry_run: bool,
) -> None:
    t0 = time.time()
    frames = extractor.extract(str(video_path))
    pose_frames = engine.estimate(frames, _VERTICAL_POLE_AXIS)
    profile = measure_body_profile(pose_frames)
    # body_shape 박힘 박힘 박힘 박힘 — source_pose 박힘 박힘.
    pose_frames_with_shape = [
        dataclasses.replace(pf, body_shape=profile) for pf in pose_frames
    ]
    coco17_array = to_coco17_array(pose_frames_with_shape)  # (T, 17, 4)
    rep_idx = _select_representative_frame_index(coco17_array)
    body_profile_dict = _build_body_profile_dict(profile)
    source_pose_dict = _build_source_pose_dict(coco17_array, rep_idx, profile)
    elapsed = time.time() - t0
    print(
        f"  frames={len(frames)} repFrame={rep_idx} torsoPx={source_pose_dict['torsoPx']:.1f} "
        f"conf={source_pose_dict['confidence']:.3f} took={elapsed:.1f}s"
    )
    if dry_run:
        print(f"  [dry-run] skip Firestore write")
        return
    firestore_admin.update_reference_body_data(
        motion_id, body_profile_dict, source_pose=source_pose_dict
    )
    print(f"  Firestore reference/{motion_id} body data merge OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--motions",
        nargs="+",
        default=NEW6_MOTION_IDS,
        help="백필할 motionId 부분집합 (디버그용). 기본은 신규 6 motion.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Firestore 쓰기 X, RTMW 추출/검증 박힘 박힘.",
    )
    args = parser.parse_args()

    try:
        import boto3
    except ImportError:
        print("boto3 없음. pip install boto3 후 재시도.", file=sys.stderr)
        sys.exit(1)

    region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION")
    if not region:
        print("AWS_DEFAULT_REGION 환경변수 필요 (ap-northeast-2).", file=sys.stderr)
        sys.exit(1)

    s3 = boto3.client("s3", region_name=region)
    extractor = FfmpegFrameExtractor()
    engine = RTMWPoseEngine()

    failures: list[tuple[str, str]] = []
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for motion_id in args.motions:
            print(f"\n[{motion_id}]")
            try:
                video_path = td_path / f"{motion_id}.mp4"
                _download_video(s3, motion_id, video_path)
                _backfill_one(motion_id, video_path, extractor, engine, args.dry_run)
            except Exception as exc:  # noqa: BLE001 - graceful per-motion
                print(f"  FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
                failures.append((motion_id, f"{type(exc).__name__}: {exc}"))

    print(
        f"\n완료. motions={len(args.motions)} failures={len(failures)} "
        f"dry_run={args.dry_run}"
    )
    if failures:
        print("실패 motion:")
        for mid, reason in failures:
            print(f"  - {mid}: {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
