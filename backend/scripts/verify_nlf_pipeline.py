"""NLF 하이브리드 파이프라인 end-to-end 검증 (#7-follow).

영상 1개에 새 3D 파이프라인 전체를 돌려 단계별 출력을 점검한다:
  ffmpeg 프레임 → NLF 3D keypoints(+불확실도) → 3D 관절각 → 시간축 폐색
  보간 → 특징벡터.
각 단계의 형상·통계·폐색 판정 프레임 수를 찍는다. 가장 접힌 인버트 콤보
(ref-invert-butterfly-combo·ref-gemini-to-ayesha-combo)에서 폐색 프레임이
잡혀 보간되는지가 핵심 확인점.

NLF 는 GPU 전제 — RunPod 등 CUDA 환경에서 돌려야 수치가 유효하다(CPU 는
좌표가 NaN 으로 발산). pose_estimator.NlfPoseEstimator 가 device 를 자동
선택한다.

사용:
  cd backend
  python scripts/verify_nlf_pipeline.py "../정은지님 영상/ref-plank-spin.mp4"
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

from sunity_shared.analysis import skeleton  # noqa: E402
from sunity_shared.analysis.features import (  # noqa: E402
    compute_joint_angles,
    feature_vector,
    joint_uncertainty,
)
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402
from sunity_shared.analysis.pose_estimator import NlfPoseEstimator  # noqa: E402
from sunity_shared.analysis.temporal import occluded_mask, temporal_fill  # noqa: E402


def _stat(name: str, arr: np.ndarray) -> None:
    finite = arr[np.isfinite(arr)]
    n_nan = int(np.isnan(arr).sum())
    n_inf = int(np.isinf(arr).sum())
    if finite.size:
        print(
            f"  {name}: shape={arr.shape} "
            f"min={finite.min():.2f} median={np.median(finite):.2f} "
            f"max={finite.max():.2f}  NaN={n_nan} inf={n_inf}"
        )
    else:
        print(f"  {name}: shape={arr.shape}  유효값 0 (전부 NaN/inf)")


def main(video_path: str) -> None:
    print(f"영상: {video_path}\n")

    print("[1] 프레임 추출 (ffmpeg)")
    t0 = time.time()
    frames = FfmpegFrameExtractor().extract(video_path)
    print(f"  frames={frames.shape}  {time.time() - t0:.1f}s\n")

    print("[2] NLF 3D keypoints (YOLO 박스 → estimate_poses_batched)")
    t0 = time.time()
    estimator = NlfPoseEstimator()
    print(f"  device={estimator._device}")
    keypoints = estimator.estimate(frames)  # (T,17,4)
    print(f"  추정 {time.time() - t0:.1f}s")
    _stat("keypoints xyz", keypoints[:, :, :3])
    _stat("keypoints uncertainty", keypoints[:, :, 3])
    print()

    print("[3] 3D 관절각 (compute_joint_angles)")
    angles = compute_joint_angles(keypoints)
    unc = joint_uncertainty(keypoints)
    _stat("angles(deg)", angles)
    _stat("joint uncertainty", unc)
    print()

    print("[4] 시간축 폐색 판정 + 보간 (temporal_fill)")
    mask = occluded_mask(angles, unc)
    T = len(angles)
    for j, key in enumerate(skeleton.JOINT_KEYS):
        n_bad = int(mask[:, j].sum())
        if n_bad:
            print(f"  {key}: 폐색 판정 {n_bad}/{T} 프레임 → 보간")
    if not mask.any():
        print(f"  폐색 판정 프레임 0 — 전 구간 NLF 신뢰 (T={T})")
    filled = temporal_fill(angles, unc)
    moved = np.abs(filled - np.nan_to_num(angles))
    print(f"  보간·스무딩 후 각도 평균 변화 {np.nanmean(moved):.2f}도")
    _stat("filled angles(deg)", filled)
    print()

    print("[5] 특징벡터 (feature_vector)")
    feats = feature_vector(filled)
    print(f"  F shape={feats.shape} = (T, 3·{skeleton.NUM_JOINTS})")
    print("\n파이프라인 end-to-end 통과. 폐색 콤보 영상에서 [4] 보간 프레임 수 확인.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용: python scripts/verify_nlf_pipeline.py "<영상경로>"')
        sys.exit(1)
    main(sys.argv[1])
