"""keypoints → 관절각(도) → 특징벡터 F = [Θ, α·Θ̇, β·Θ̈].

ml_CLAUDE.md: 좌표만 비교하면 속도 오류 → 각도+각속도+각가속도 다중 모달 필수.
순수 numpy. 단위는 도(°) — issue 문구("20° 부족")와 일관.
"""

from __future__ import annotations

import numpy as np

from .skeleton import JOINT_ANGLES, JOINT_KEYS, kp_index

# Θ̇·Θ̈ 스케일(ml_CLAUDE.md α·β). 각도 대비 변화량이 작아 가중치로 균형.
DEFAULT_ALPHA = 0.10
DEFAULT_BETA = 0.02
DEFAULT_MIN_CONF = 0.3


def _angle_deg(a, b, c):
    """vertex b 에서 (a-b),(c-b) 사이 각(도). 결측/퇴화 시 nan."""
    if np.any(np.isnan(a)) or np.any(np.isnan(b)) or np.any(np.isnan(c)):
        return np.nan
    ba = a - b
    bc = c - b
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba == 0 or nbc == 0:
        return np.nan
    cosang = np.clip(np.dot(ba, bc) / (nba * nbc), -1.0, 1.0)
    return float(np.degrees(np.arccos(cosang)))


def compute_joint_angles(keypoints, min_conf: float = DEFAULT_MIN_CONF):
    """keypoints (T,17,2) 또는 (T,17,3=x,y,conf) → 각도 (T, NUM_JOINTS) 도.

    conf 가 있으면 min_conf 미만 점은 결측(nan) 처리.
    """
    kp = np.asarray(keypoints, dtype=float)
    if kp.ndim != 3 or kp.shape[1] < 17 or kp.shape[2] < 2:
        raise ValueError("keypoints 형상은 (T,17,2|3) 이어야 합니다.")
    T = kp.shape[0]
    xy = kp[:, :, :2].copy()
    if kp.shape[2] >= 3:
        low = kp[:, :, 2] < min_conf
        xy[low] = np.nan

    out = np.full((T, len(JOINT_KEYS)), np.nan, dtype=float)
    for j, key in enumerate(JOINT_KEYS):
        an, bn, cn = JOINT_ANGLES[key]
        ia, ib, ic = kp_index(an), kp_index(bn), kp_index(cn)
        for t in range(T):
            out[t, j] = _angle_deg(xy[t, ia], xy[t, ib], xy[t, ic])
    return out


def fill_gaps(angles):
    """관절별 시간축 결측을 선형보간 + 양끝 보충. 전체 결측 열은 0."""
    a = np.array(angles, dtype=float, copy=True)
    T = a.shape[0]
    idx = np.arange(T)
    for j in range(a.shape[1]):
        col = a[:, j]
        good = ~np.isnan(col)
        if good.sum() == 0:
            a[:, j] = 0.0
        elif good.sum() < T:
            a[:, j] = np.interp(idx, idx[good], col[good])
    return a


def feature_vector(
    angles, alpha: float = DEFAULT_ALPHA, beta: float = DEFAULT_BETA
):
    """각도(T,J) → F (T, 3J) = [Θ, α·Θ̇, β·Θ̈]. (결측은 미리 fill_gaps 권장)"""
    a = np.asarray(angles, dtype=float)
    if a.ndim != 2:
        raise ValueError("angles 는 (T,J) 2차원이어야 합니다.")
    if a.shape[0] < 2:
        vel = np.zeros_like(a)
        acc = np.zeros_like(a)
    else:
        vel = np.gradient(a, axis=0)
        acc = np.gradient(vel, axis=0)
    return np.concatenate([a, alpha * vel, beta * acc], axis=1)
