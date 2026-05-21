"""reference 영상 keypoint overlay 검증 (#7-follow Phase 1).

정은지 영상에서 FrameExtractor + PoseEstimator 로 keypoint 를 추출하고
프레임에 골격을 그려 PNG 로 저장한다. 폴 폐색·인버트·고속 회전 구간에서
ViTPose 추출이 안정적인지, keypoint 순서가 COCO 17 과 맞는지 육안 확인용
(reference-motions.md §7 요구).

사용:
  cd backend
  python scripts/verify_pose_overlay.py "../정은지님 영상/ref-plank-spin.mp4"

결과: backend/scripts/overlay_out/ 에 균등 간격 6프레임 overlay PNG.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402
from sunity_shared.analysis.pose_estimator import YoloVitPoseEstimator  # noqa: E402
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES  # noqa: E402

# COCO 17 골격 연결 (육안 검증용)
BONES = [
    (5, 7), (7, 9), (6, 8), (8, 10),         # 양팔
    (5, 6), (5, 11), (6, 12), (11, 12),      # 몸통
    (11, 13), (13, 15), (12, 14), (14, 16),  # 양다리
    (0, 5), (0, 6),                          # 목
]
_MIN_CONF = 0.3


def main(video_path: str) -> None:
    out_dir = Path(__file__).resolve().parent / "overlay_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = FfmpegFrameExtractor().extract(video_path)
    print(f"프레임 {len(frames)}장 추출")
    kpts = YoloVitPoseEstimator().estimate(frames)  # (T, 17, 3)

    for n, i in enumerate(np.linspace(0, len(frames) - 1, 6, dtype=int)):
        img = Image.fromarray(frames[i]).convert("RGB")
        draw = ImageDraw.Draw(img)
        kp = kpts[i]
        for a, b in BONES:
            if kp[a, 2] > _MIN_CONF and kp[b, 2] > _MIN_CONF:
                draw.line(
                    [tuple(kp[a, :2]), tuple(kp[b, :2])],
                    fill=(0, 200, 255),
                    width=2,
                )
        for j in range(17):
            if kp[j, 2] > _MIN_CONF:
                x, y = kp[j, :2]
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 75, 51))
        path = out_dir / f"overlay_{n}_frame{int(i)}.png"
        img.save(path)
        print(f"저장: {path}")

    print("\nCOCO 17 순서:", KEYPOINT_NAMES)
    print("overlay PNG 에서 점이 실제 관절 위치와 맞는지 육안 확인하세요.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용: python scripts/verify_pose_overlay.py "<영상경로>"')
        sys.exit(1)
    main(sys.argv[1])
