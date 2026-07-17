"""Spike 004-iii-b — Pod 측 RTMW 키포인트 추출 (production 동일 스택).

사용: python3 extract_kpts_pod.py <videos_dir> <out_dir>
각 mp4 를 9fps 샘플링 → YOLOX det + RTMW wholebody → <name>.npz (kpts[T,133,2], scores[T,133], ts[T]).
가장 큰 bbox 인물 1명만 (production 관례).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np
from rtmlib import Wholebody

DET = "/workspace/yolox_weights/yolox_m.onnx"
POSE = "/workspace/rtmw_weights/rtmw-x-384.onnx"
TARGET_FPS = 9.0


def extract(video: Path, wb: Wholebody, out_dir: Path) -> None:
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps / TARGET_FPS))
    kpts_all, scores_all, ts_all = [], [], []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            keypoints, scores = wb(frame)
            if keypoints is not None and len(keypoints) > 0:
                # 최대 면적 인물 선택: bbox 근사 = keypoint 범위
                areas = [
                    (k[:, 0].max() - k[:, 0].min()) * (k[:, 1].max() - k[:, 1].min())
                    for k in keypoints
                ]
                j = int(np.argmax(areas))
                kpts_all.append(keypoints[j])
                scores_all.append(scores[j])
            else:
                kpts_all.append(np.full((133, 2), np.nan))
                scores_all.append(np.zeros(133))
            ts_all.append(i / fps)
        i += 1
    cap.release()
    out = out_dir / (video.stem + ".npz")
    np.savez(
        out,
        kpts=np.asarray(kpts_all, dtype=np.float32),
        scores=np.asarray(scores_all, dtype=np.float32),
        ts=np.asarray(ts_all, dtype=np.float32),
    )
    print(f"{video.name}: T={len(ts_all)} -> {out.name}", flush=True)


def main() -> None:
    videos_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    wb = Wholebody(
        det=DET,
        det_input_size=(640, 640),
        pose=POSE,
        to_openpose=False,
        backend="onnxruntime",
        device="cuda",
    )
    t0 = time.time()
    for v in sorted(videos_dir.glob("*.mp4")):
        if v.stem.startswith("raw_"):
            continue
        extract(v, wb, out_dir)
    print(f"total {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
