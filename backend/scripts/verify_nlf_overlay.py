"""NLF(3D HMR) 점군 overlay 검증 (#7-follow Phase 2 — 3D 전환 검증).

ViTPose(2D)는 폴 폐색·접힌 인버트 자세에서 keypoint 가 엉킨다. 대안으로
NLF(Neural Localizer Fields, NeurIPS'24)는 인체 표면 867점을 3D 로 복원한다.
인체 모델 prior 가 있어 가려진 자세도 해부학적으로 일관된 결과를 낸다.

NLF multi 모델의 내장 YOLO 탐지기는 CUDA 가 하드코딩돼 CPU 에서 실패하므로,
estimate_poses_batched(images, boxes, weights) 로 박스를 직접 주입한다:
  - 박스: 우리가 쓰는 YOLO11. 접힌 프레임에서 YOLO 가 실패하면 인접 성공
    프레임의 박스로 폴백한다(시간적 보완 — research §D 의 발상).
  - weights: 모델 내장 canonical 867점(crop_model.canonical_locs_init)을
    get_weights_for_canonical_points 로 변환 → SMPL 피팅(CPU SVD 크래시) 우회.

균등 간격 6프레임을 추정해 2D 투영점을 프레임에 그린다. 점 색은 불확실도:
신뢰(낮음)=시안 → 불확실(높음)=빨강. 가려진 자세에서도 점군이 일관된
인체 형태를 그리는지 육안 확인용.

사용:
  cd backend
  python scripts/verify_nlf_overlay.py "../정은지님 영상/ref-plank-spin.mp4"

결과: backend/scripts/overlay_out/ 에 6프레임 overlay PNG.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
import torchvision  # noqa: F401 — TorchScript 모델의 torchvision 연산 등록에 필요
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402

_MODEL = Path(__file__).resolve().parent / "nlf_l_multi.torchscript"


def _yolo_boxes(yolo, frames: np.ndarray) -> list[np.ndarray | None]:
    """각 프레임의 인체 박스(LTWH). 미감지 프레임은 None."""
    out: list[np.ndarray | None] = []
    for f in frames:
        det = yolo.predict(
            Image.fromarray(f), classes=[0], conf=0.3, verbose=False
        )
        bx = det[0].boxes.xyxy.cpu().numpy()
        if len(bx) == 0:
            out.append(None)
        else:
            x1, y1, x2, y2 = bx[0]
            out.append(np.array([x1, y1, x2 - x1, y2 - y1], dtype=np.float32))
    return out


def _fill_missing(boxes: list[np.ndarray | None]) -> list[np.ndarray]:
    """미감지(None) 박스를 가장 가까운 성공 프레임 박스로 채운다(시간적 보완)."""
    known = [(i, b) for i, b in enumerate(boxes) if b is not None]
    if not known:
        raise RuntimeError("영상 전체에서 YOLO 인체 박스 0개")
    filled: list[np.ndarray] = []
    for i, b in enumerate(boxes):
        if b is not None:
            filled.append(b)
        else:
            nearest = min(known, key=lambda kb: abs(kb[0] - i))[1]
            filled.append(nearest)
    return filled


def main(video_path: str) -> None:
    from ultralytics import YOLO

    out_dir = Path(__file__).resolve().parent / "overlay_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}")
    model = torch.jit.load(str(_MODEL), map_location=device).eval()
    canon = model.crop_model.canonical_locs_init  # (867,3) — model device
    yolo = YOLO("yolo11n.pt")

    frames = FfmpegFrameExtractor().extract(video_path)
    sample_idx = np.linspace(0, len(frames) - 1, 6, dtype=int)
    sampled = frames[sample_idx]
    print(f"프레임 {len(frames)}장 → 6프레임 추정")

    raw_boxes = _yolo_boxes(yolo, sampled)
    n_missed = sum(b is None for b in raw_boxes)
    if n_missed:
        print(f"YOLO 미감지 {n_missed}/6 — 인접 프레임 박스로 폴백")
    boxes = _fill_missing(raw_boxes)

    with torch.inference_mode():
        weights = model.get_weights_for_canonical_points(canon)
        for n, (src_i, box) in enumerate(zip(sample_idx, boxes)):
            frame = frames[src_i]
            images = (
                torch.from_numpy(frame)
                .permute(2, 0, 1)
                .contiguous()
                .unsqueeze(0)
                .to(device)
            )
            box_t = torch.from_numpy(box).unsqueeze(0).to(device)
            pred = model.estimate_poses_batched(images, [box_t], weights)
            pts = pred["poses2d"][0][0].cpu().numpy()  # (867,2)
            unc = pred["uncertainties"][0][0].cpu().numpy()  # (867,)

            # 유효(투영 가능) 점만 — 극단 자세에선 일부 점이 카메라 뒤로
            # 가 NaN/inf 로 투영된다. 유효 점 비율 자체가 진단 정보.
            valid = np.isfinite(pts).all(axis=1) & np.isfinite(unc)
            # 불확실도 정규화 → 색 (낮음=시안 신뢰, 높음=빨강).
            uv = unc[valid]
            lo, hi = np.percentile(uv, 5), np.percentile(uv, 95)

            img = Image.fromarray(frame).convert("RGB")
            draw = ImageDraw.Draw(img)
            for (x, y), u in zip(pts[valid], uv):
                t = float(np.clip((u - lo) / max(hi - lo, 1e-6), 0, 1))
                color = (int(60 + 195 * t), int(200 * (1 - t)), int(200 * (1 - t)))
                draw.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=color)
            path = out_dir / f"overlay_{n}_frame{int(src_i)}.png"
            img.save(path)
            print(
                f"저장: {path.name}  유효점 {int(valid.sum())}/867  "
                f"불확실도 중앙값={np.median(uv):.3f}"
            )

    print("\n점군이 가려진 자세에서도 일관된 인체 형태를 그리는지 육안 확인.")
    print("시안=신뢰 / 빨강=불확실(가림 추정).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용: python scripts/verify_nlf_overlay.py "<영상경로>"')
        sys.exit(1)
    main(sys.argv[1])
