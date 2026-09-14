"""result.joints3d 로부터 붕괴 프레임 / 뼈위반 p90 재계산 — 로컬 CPU 실측과 같은 정의.

정의 출처 = .planning/quick/260913-udr-rot180-inversion-pass/evidence/decompose.py:71-83
  · torso   = ||mean(kp5,kp6) - mean(kp11,kp12)||
  · 붕괴    = 한 프레임 17개 키포인트를 0.1px 로 반올림했을 때 고유 좌표 <= 8
  · 뼈위반  = 8개 뼈의 (길이/torso) 가 클립 중앙값에서 벗어난 |log 비율| 의 p90, 그 평균

09-13 실측은 rtmlib 출력(2D 픽셀)에서 쟀다. result.joints3d 는 같은 RTMW 좌표를
flat (T*17*3) 로 저장한 것이고 z==0 이므로 xy 만 쓰면 같은 양이다.

입력 = pull 해 둔 분석 doc JSON (result.joints3d / joints3dFrames / joints3dKeys).
"""
from __future__ import annotations

import json
import sys

import numpy as np

# decompose.py:13 과 동일 (COCO-17 인덱스)
BONES = ((5, 7), (7, 9), (6, 8), (8, 10), (11, 13), (13, 15), (12, 14), (14, 16))


def _torso(a: np.ndarray) -> np.ndarray:
    sh = a[:, [5, 6], :].mean(1)
    hp = a[:, [11, 12], :].mean(1)
    return np.linalg.norm(sh - hp, axis=-1)


def load(path: str) -> np.ndarray:
    doc = json.load(open(path))
    res = doc.get("result") or doc
    flat = res.get("joints3d")
    if not flat:
        raise SystemExit(f"{path}: result.joints3d 없음")
    t = int(res["joints3dFrames"])
    j = len(res["joints3dKeys"])
    a = np.asarray(flat, dtype=float).reshape(t, j, 3)
    return a[:, :, :2]  # z 는 항상 0 — xy 만


def metrics(a: np.ndarray) -> dict:
    uniq = np.array([len(set(map(tuple, np.round(a[t], 1)))) for t in range(len(a))])
    tor = _torso(a)
    bv = []
    for i, j in BONES:
        length = np.linalg.norm(a[:, i, :] - a[:, j, :], axis=-1) / (tor + 1e-9)
        med = np.nanmedian(length) + 1e-9
        bv.append(np.nanpercentile(np.abs(np.log((length + 1e-9) / med)), 90))
    return {
        "frames": int(len(a)),
        "collapse": int((uniq <= 8).sum()),
        "bone_p90_mean": float(np.mean(bv)),
        "bone_p90_per_bone": [round(float(x), 3) for x in bv],
        "torso_median_px": float(np.nanmedian(tor)),
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: joints3d_metrics.py <doc.json> [<doc.json> ...]")
    for path in sys.argv[1:]:
        m = metrics(load(path))
        print(f"{path}")
        print(f"  frames={m['frames']}  붕괴={m['collapse']}  "
              f"뼈위반p90평균={m['bone_p90_mean']:.3f}  torso중앙={m['torso_median_px']:.1f}px")
        print(f"  per-bone p90 = {m['bone_p90_per_bone']}")


if __name__ == "__main__":
    main()
