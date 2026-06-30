"""정은지 reference → real (T,17,4) COCO-17 3D keypoints (.npz) — Phase 10 D-05.

POD GPU 전용 (RTMW 의존). D-05 real-elite 회귀 fixture 의 단일 유효 3D source.

이 스크립트는 **유일하게 허용되는** `(T,17,4)` 3D 추출 경로다:
  frames -> RTMWPoseEngine.estimate(frames) -> pose_frames
        -> to_coco17_array(pose_frames)  # pose_frame.py:325 → (x, y, z, uncertainty_proxy)
ch3 = uncertainty_proxy (1.0 = 미감지/최악, low ≈ good — pose_frame.py:326,335).
skeleton.KEYPOINT_NAMES 17 keypoint 순서. `referenceKeypointReport`(2D 8-keypoint
overlay, data=T*J*2)와 `reference-angles.json`(angle-only, 8 joint)은 (T,17,4) 3D
source 로 금지 — 둘 다 3D 좌표를 복원할 수 없어 D-05 cross-product 커버리지를 줄 수 없다.

PINNED SOURCE MOTION IDS (KNOWN-ANSWER 회귀, fit 대상 아님 — [[calibration-source-hard-gate]]):
  ref-sideway-spin  — spin-around-pole (회전 방위)
  ref-invert        — inverted / mirrored orientation
  ref-foxtop-split  — extreme split (좌·우 양 사지)

Usage (Pod):
  cd /workspace/SunityMotion/backend
  source pod.env
  export PYTHONPATH=$PWD:$PWD/shared/python
  python scripts/extract_reference_coco17_4ch.py \
      --motions ref-sideway-spin ref-invert ref-foxtop-split \
      --out tests/phase10/fixtures/real_elite_coco17_4ch.npz

Output: np.savez 로 {motion_id: (T,17,4) float32} — conftest.load_real_elite_clips 정합.
이 npz 가 repo 에 들어오면 phase10 의 4 real-elite 테스트 skipif 가 자동 해제된다.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

import boto3
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "shared" / "python"))

from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402
from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import (  # noqa: E402
    RTMWPoseEngine,
)
from sunity_shared.analysis.pose_frame import PoleAxis, to_coco17_array  # noqa: E402

# Firestore reference doc id 와 동기 (extract_reference_keypoint_reports.py mirror).
DEFAULT_MOTION_IDS = ["ref-sideway-spin", "ref-invert", "ref-foxtop-split"]

S3_BUCKET = "sunity-motion-pilot-videos"
S3_PREFIX = "reference"

_DEFAULT_POLE = PoleAxis(
    axis_vector=(0.0, 1.0, 0.0),
    confidence_level="low",
    source="vertical_fallback",
)


def _process_motion(
    motion_id: str,
    s3: "boto3.client",  # type: ignore[name-defined]
    extractor: FfmpegFrameExtractor,
    engine: RTMWPoseEngine,
    s3_prefix: str,
) -> np.ndarray:
    """1 motion → (T,17,4) float32 (x, y, z, uncertainty_proxy)."""
    key = f"{s3_prefix}/{motion_id}.mp4"
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        local_path = Path(tmp.name)
    try:
        print(f"  [{motion_id}] S3 download s3://{S3_BUCKET}/{key}", flush=True)
        s3.download_file(S3_BUCKET, key, str(local_path))

        frames = extractor.extract(str(local_path))
        print(f"  [{motion_id}] RTMW pose ({frames.shape[0]} frame)", flush=True)
        pose_frames = engine.estimate(frames, _DEFAULT_POLE)

        arr = to_coco17_array(pose_frames).astype(np.float32)
        if arr.ndim != 3 or arr.shape[1] != 17 or arr.shape[2] != 4:
            raise RuntimeError(f"to_coco17_array 형상 비정상 {arr.shape} — {motion_id}")
        return arr
    finally:
        try:
            local_path.unlink()
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "tests" / "phase10" / "fixtures" / "real_elite_coco17_4ch.npz",
        help="Output .npz path",
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=DEFAULT_MOTION_IDS,
        help="Pinned motion id list (default = ref-sideway-spin ref-invert ref-foxtop-split).",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=18.0,
        help="Target sampling fps (default 18.0 — backend pipeline 정합).",
    )
    parser.add_argument(
        "--s3-prefix",
        type=str,
        default=S3_PREFIX,
        help=f"S3 prefix (default '{S3_PREFIX}').",
    )
    args = parser.parse_args()

    s3 = boto3.client("s3")
    extractor = FfmpegFrameExtractor(target_fps=args.target_fps)
    print("RTMW 엔진 init (가중치 로드 ~30초)...", flush=True)
    engine = RTMWPoseEngine()
    print("RTMW init 완료", flush=True)

    clips: dict[str, np.ndarray] = {}
    t_start = time.time()
    for motion_id in args.motions:
        t0 = time.time()
        try:
            clips[motion_id] = _process_motion(
                motion_id, s3, extractor, engine, args.s3_prefix
            )
            print(f"  [{motion_id}] OK {clips[motion_id].shape} ({time.time() - t0:.1f}s)")
        except Exception as exc:  # noqa: BLE001
            print(f"  [{motion_id}] FAIL — {exc}", file=sys.stderr)
            continue

    if not clips:
        print("추출된 motion 없음 — npz 미생성", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.out, **clips)
    print(
        f"\n총 {len(clips)}/{len(args.motions)} motion → {args.out} "
        f"({time.time() - t_start:.1f}s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
