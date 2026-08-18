"""기준 영상 t초 프레임 → RTMW 133 → 뼈대 PNG + 좌표 JSON (quick-260818-muy).

Pod 에서 실행한다 (RTMW 는 CUDA):
    cd /workspace/SunityMotion/backend
    PYTHONPATH=shared/python:. RTMW_ONNX_PATH=... YOLOX_ONNX_PATH=... RTMW_DEVICE=cuda \
      python3 ../.planning/quick/260818-muy-a-b-2/extract_skeleton.py \
        --video /workspace/_ill/ref-pdshape.mp4 --t 5.0 --crop 360 400 780 920 \
        --out /workspace/_ill/pdshape_leg

산출:
    {out}_frame.jpg      크롭 적용 원본 프레임 (현행 입력과 동일 구도)
    {out}_skel.png       같은 크롭의 뼈대 그림 — 검은 배경, 흰 뼈대, 관절 점
    {out}_kps.json       133 관절 픽셀 좌표(크롭 좌표계) + 신뢰도

왜 학습 캐시(phase22_coords_cache)를 안 쓰나: 53프레임 저fps·12관절이라 머리·목·발이 없고
t=5.0 에 정확히 맞는 프레임이 없다. 뼈대 입력은 그 프레임의 것이어야 한다.

동작명 분기 0 — 영상 경로·시각·크롭은 전부 인자.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

# COCO-WholeBody 133: 0-16 body(COCO17) / 17-22 feet / 23-90 face / 91-132 hands.
BODY_EDGES = [
    (5, 7), (7, 9), (6, 8), (8, 10),          # arms
    (11, 13), (13, 15), (12, 14), (14, 16),   # legs
    (5, 6), (11, 12), (5, 11), (6, 12),       # torso
    (0, 1), (0, 2), (1, 3), (2, 4),           # head
    (15, 17), (15, 18), (15, 19),             # left foot
    (16, 20), (16, 21), (16, 22),             # right foot
]
NECK_MID = ((5, 6), 0)  # 어깨 중점 → 코


def grab_frame(video: Path, t: float) -> np.ndarray:
    """ffmpeg 로 t초 프레임 1장을 RGB ndarray 로."""
    import imageio.v3 as iio
    tmp = video.with_suffix(f".t{t:.2f}.png")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(video),
         "-frames:v", "1", str(tmp)],
        check=True,
    )
    img = iio.imread(tmp)
    tmp.unlink(missing_ok=True)
    return np.asarray(img)[..., :3]


def draw_skeleton(kps: np.ndarray, scores: np.ndarray, size: tuple[int, int],
                  conf: float = 0.3) -> np.ndarray:
    """(133,2) 좌표 → 뼈대 이미지 (H,W,3) uint8. 흰 뼈, 관절 점, 검은 배경."""
    from PIL import Image, ImageDraw
    W, H = size
    im = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = max(3, int(min(W, H) * 0.012))
    r = max(4, int(min(W, H) * 0.016))

    def ok(i: int) -> bool:
        return scores[i] >= conf and 0 <= kps[i, 0] < W and 0 <= kps[i, 1] < H

    for a, b in BODY_EDGES:
        if ok(a) and ok(b):
            d.line([tuple(kps[a]), tuple(kps[b])], fill=(255, 255, 255), width=lw)
    (s1, s2), nose = NECK_MID
    if ok(s1) and ok(s2) and ok(nose):
        mid = ((kps[s1] + kps[s2]) / 2).tolist()
        d.line([tuple(mid), tuple(kps[nose])], fill=(255, 255, 255), width=lw)
    for i in range(23):  # body + feet joints only
        if ok(i):
            x, y = kps[i]
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 80, 60))
    return np.asarray(im)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--t", type=float, required=True)
    ap.add_argument("--crop", type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), default=None)
    ap.add_argument("--out", required=True, help="출력 접두 (확장자 없이)")
    args = ap.parse_args()

    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
    import imageio.v3 as iio

    frame = grab_frame(Path(args.video), args.t)
    H, W = frame.shape[:2]
    engine = RTMWPoseEngine()
    raw = engine._infer_raw(frame[None, ...])[0]
    if raw is None:
        raise SystemExit("RTMW 미감지 — 이 프레임에서 사람이 안 잡힌다")
    kps, scores = raw
    kps = np.asarray(kps, dtype=np.float32)[:, :2]
    scores = np.asarray(scores, dtype=np.float32)

    if args.crop:
        x0, y0, x1, y1 = args.crop
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x1), min(H, y1)
        frame = frame[y0:y1, x0:x1]
        kps = kps - np.array([x0, y0], dtype=np.float32)
        H, W = frame.shape[:2]

    skel = draw_skeleton(kps, scores, (W, H))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    iio.imwrite(f"{out}_frame.jpg", frame, quality=92)
    iio.imwrite(f"{out}_skel.png", skel)
    Path(f"{out}_kps.json").write_text(json.dumps({
        "video": args.video, "t": args.t, "crop": args.crop, "size": [W, H],
        "kps": kps.round(1).tolist(), "scores": scores.round(3).tolist(),
    }))
    vis = int((scores[:23] >= 0.3).sum())
    print(f"saved {out}_frame.jpg / _skel.png / _kps.json  size={W}x{H}  "
          f"body-joints-visible={vis}/23")


if __name__ == "__main__":
    main()
