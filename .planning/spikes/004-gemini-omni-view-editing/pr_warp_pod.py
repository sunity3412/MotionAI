"""Spike 006 — PersPose PR(Perspective Rotation) 수학 가상 카메라 기준선.

원리 (PersPose, NLM 폴스포츠 특화 소스 권고 1순위): 인체 bbox 중심 광선을
광학 중심 기준 회전(Rodrigues)으로 z축에 정렬 → H = K R K^-1 호모그래피 워프.
픽셀 생성 0 = 환각 원천 불가. 측정: 워프 영상 RTMW 재추론 기질(conf/boneCV/jerk)
이 원본 대비 개선되는가.

사용(Pod): python3 pr_warp_pod.py <gate_in> <kpts_dir> <out_videos_dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

BODY = slice(0, 17)


def per_frame_centers(kpts: np.ndarray, scores: np.ndarray, ts: np.ndarray, n_frames: int, fps: float) -> np.ndarray:
    """9fps 샘플 kpts 중심 → 원본 프레임 grid 로 보간 + 평활(창 9)."""
    conf = scores[:, BODY] > 0.3
    centers = np.full((len(kpts), 2), np.nan)
    for i in range(len(kpts)):
        pts = kpts[i, BODY][conf[i]]
        if len(pts) >= 5:
            centers[i] = pts.mean(0)
    valid = ~np.isnan(centers[:, 0])
    grid_ts = np.arange(n_frames) / fps
    cx = np.interp(grid_ts, ts[valid], centers[valid, 0])
    cy = np.interp(grid_ts, ts[valid], centers[valid, 1])
    k = 9
    ker = np.ones(k) / k
    cx = np.convolve(np.pad(cx, k // 2, mode="edge"), ker, mode="valid")
    cy = np.convolve(np.pad(cy, k // 2, mode="edge"), ker, mode="valid")
    return np.stack([cx, cy], -1)


def pr_homography(center: np.ndarray, w: int, h: int) -> np.ndarray:
    f = float(np.hypot(w, h))  # CLIFF 근사 focal
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])
    Kinv = np.linalg.inv(K)
    ray = Kinv @ np.array([center[0], center[1], 1.0])
    z = np.array([0.0, 0.0, 1.0])
    v = ray / np.linalg.norm(ray)
    axis = np.cross(v, z)
    s = np.linalg.norm(axis)
    if s < 1e-8:
        return np.eye(3)
    axis = axis / s
    phi = float(np.arccos(np.clip(np.dot(v, z), -1, 1)))
    R, _ = cv2.Rodrigues(axis * phi)
    return K @ R @ Kinv


def main() -> None:
    gate_in, kpts_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)
    for npz_path in sorted(kpts_dir.glob("*.npz")):
        name = npz_path.stem
        video = gate_in / f"{name}.mp4"
        if not video.exists():
            continue
        d = np.load(npz_path)
        cap = cv2.VideoCapture(str(video))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        centers = per_frame_centers(d["kpts"], d["scores"], d["ts"], n, fps)
        writer = cv2.VideoWriter(
            str(out_dir / f"{name}.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
        )
        i = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            H = pr_homography(centers[min(i, n - 1)], w, h)
            writer.write(cv2.warpPerspective(frame, H, (w, h)))
            i += 1
        cap.release()
        writer.release()
        print(f"{name}: warped {i} frames", flush=True)


if __name__ == "__main__":
    main()
