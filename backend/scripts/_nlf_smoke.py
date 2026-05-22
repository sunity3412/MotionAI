"""NLF 출력 구조 확인용 1회성 스모크 (#7-follow Phase 2).

NLF multi 모델의 내장 YOLO 탐지기는 CUDA 가 하드코딩돼 CPU 에서 실패한다.
대신 estimate_smpl_batched(images, boxes) 로 박스를 직접 주입해 탐지기를
건너뛴다 — 박스는 우리가 이미 쓰는 YOLO11 로 구한다.

영상 중간 프레임 1장에 돌려 반환 dict 의 키·shape·dtype 을 출력한다.

사용: cd backend && python scripts/_nlf_smoke.py "<영상경로>"
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
import torchvision  # noqa: F401 — TorchScript 모델의 torchvision 연산 등록에 필요
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402

_MODEL = Path(__file__).resolve().parent / "nlf_l_multi.torchscript"


def _describe(name: str, value) -> None:
    if isinstance(value, list):
        head = value[0] if value else None
        print(
            f"  {name}: list(len={len(value)}) "
            f"elem0={type(head).__name__} "
            f"shape={getattr(head, 'shape', None)} "
            f"dtype={getattr(head, 'dtype', None)}"
        )
    elif isinstance(value, torch.Tensor):
        print(f"  {name}: Tensor shape={tuple(value.shape)} dtype={value.dtype}")
    else:
        print(f"  {name}: {type(value).__name__} = {value!r}")


def main(video_path: str) -> None:
    from ultralytics import YOLO

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}")
    model = torch.jit.load(str(_MODEL), map_location=device).eval()
    yolo = YOLO("yolo11n.pt")

    frames = FfmpegFrameExtractor().extract(video_path)
    mid = frames[0]  # (H,W,3) uint8 RGB — 직립 프레임 (탐지 안정)

    det = yolo.predict(Image.fromarray(mid), classes=[0], conf=0.3, verbose=False)
    boxes_xyxy = det[0].boxes.xyxy.cpu().numpy()
    print(f"YOLO 인체 박스 {len(boxes_xyxy)}개")
    if len(boxes_xyxy) == 0:
        print("사람 미감지 — 다른 프레임 필요")
        return
    x1, y1, x2, y2 = boxes_xyxy[0]
    box_ltwh = torch.tensor(
        [[x1, y1, x2 - x1, y2 - y1]], dtype=torch.float32, device=device
    )

    images = (
        torch.from_numpy(mid).permute(2, 0, 1).contiguous().unsqueeze(0).to(device)
    )
    print(f"입력 images: shape={tuple(images.shape)} dtype={images.dtype}")
    print(f"입력 boxes(LTWH): {box_ltwh.tolist()}")

    with torch.inference_mode():
        pred = model.estimate_smpl_batched(images, [box_ltwh])

    print(f"출력 type: {type(pred).__name__}")
    if isinstance(pred, dict):
        for k, v in pred.items():
            _describe(k, v)
            if isinstance(v, list) and v and isinstance(v[0], torch.Tensor):
                arr = v[0].cpu().numpy()
                if arr.size:
                    print(
                        f"      sample[0] min={np.nanmin(arr):.2f} "
                        f"max={np.nanmax(arr):.2f}"
                    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용: python scripts/_nlf_smoke.py "<영상경로>"')
        sys.exit(1)
    main(sys.argv[1])
