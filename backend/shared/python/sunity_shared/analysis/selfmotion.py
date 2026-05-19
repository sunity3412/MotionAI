"""Mode3(자기 성장) 자기-기준 메트릭 — 외부 기준 모션 불필요.

ml_CLAUDE.md Mode3: 관절 각도 절대값 + 좌우 대칭 + 밸런스. 첫 영상부터
절대값 측정 가능(의존성 없음), 두 번째부터 이전 대비 비교.

MVP 편차 = 좌우 대칭 편차(도): 같은 동작에서 좌/우 관절 각도가 얼마나
어긋나는지. 순수 함수 — 모델 없이 검증 가능.
"""

from __future__ import annotations

import numpy as np

from .skeleton import JOINT_KEYS, NUM_JOINTS

# 좌/우 대칭 쌍. 각 쌍 편차를 양쪽 관절에 동일 부여.
_SYMMETRY_PAIRS = (
    ("left_elbow", "right_elbow"),
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
)


def symmetry_deviation(angles) -> np.ndarray:
    """각도 (T,J) → 관절별 좌우 대칭 편차(도) 길이 NUM_JOINTS (JOINT_KEYS 순)."""
    a = np.asarray(angles, dtype=float)
    if a.ndim != 2 or a.shape[1] != NUM_JOINTS:
        raise ValueError(f"angles 형상은 (T,{NUM_JOINTS}) 이어야 합니다.")
    dev = np.zeros(NUM_JOINTS, dtype=float)
    for lkey, rkey in _SYMMETRY_PAIRS:
        li, ri = JOINT_KEYS.index(lkey), JOINT_KEYS.index(rkey)
        d = float(np.mean(np.abs(a[:, li] - a[:, ri])))
        dev[li] = d
        dev[ri] = d
    return dev
