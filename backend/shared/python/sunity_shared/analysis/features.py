"""3D keypoints → 관절각(도) → 특징벡터 F = [Θ, α·Θ̇, β·Θ̈].

ml_CLAUDE.md: 좌표만 비교하면 속도 오류 → 각도+각속도+각가속도 다중 모달 필수.
순수 numpy. 단위는 도(°) — issue 문구("20° 부족")와 일관.

입력은 NLF 3D keypoints (T,17,3=xyz 또는 T,17,4=xyz+불확실도). 관절각은
3D 벡터 사이 각이라 카메라 투영 왜곡(2D 단축)에서 자유롭다. 불확실도 기반
신뢰도 판정은 시간축 보간(temporal)이 joint_uncertainty 출력으로 담당한다.
"""

from __future__ import annotations

import numpy as np

from .skeleton import JOINT_ANGLES, JOINT_KEYS, kp_index

# Θ̇·Θ̈ 스케일(ml_CLAUDE.md α·β). 각도 대비 변화량이 작아 가중치로 균형.
DEFAULT_ALPHA = 0.10
DEFAULT_BETA = 0.02


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


def compute_joint_angles(keypoints):
    """3D keypoints (T,17,3=xyz) 또는 (T,17,4=xyz+불확실도) → 각도 (T,NUM_JOINTS) 도.

    NLF 3D 좌표에서 관절각을 계산한다. 4채널이면 4번째(불확실도)는 무시하고
    좌표만 쓴다 — 불확실도 신뢰도 판정은 시간축 보간(temporal)이 담당한다.
    NLF 가 NaN 을 낸 점이 끼면 해당 관절각도 NaN — temporal 이 보간한다.
    """
    kp = np.asarray(keypoints, dtype=float)
    if kp.ndim != 3 or kp.shape[1] < 17 or kp.shape[2] < 3:
        raise ValueError("keypoints 형상은 (T,17,3|4=xyz[,불확실도]) 이어야 합니다.")
    xyz = kp[:, :, :3]
    T = kp.shape[0]

    out = np.full((T, len(JOINT_KEYS)), np.nan, dtype=float)
    for j, key in enumerate(JOINT_KEYS):
        an, bn, cn = JOINT_ANGLES[key]
        ia, ib, ic = kp_index(an), kp_index(bn), kp_index(cn)
        for t in range(T):
            out[t, j] = _angle_deg(xyz[t, ia], xyz[t, ib], xyz[t, ic])
    return out


def joint_uncertainty(keypoints):
    """3D keypoints (T,17,4=xyz+불확실도) → 관절각별 불확실도 (T,NUM_JOINTS).

    한 관절각은 정의 keypoint 3개로 계산되므로, 그 3점 불확실도의 최댓값을
    관절각 불확실도로 본다(가장 불신하는 점이 각도를 지배). 4채널이 아니면
    (불확실도 정보 없음) 0 — temporal 이 균일 신뢰로 처리한다. NLF 가 NaN/inf
    를 낸 점은 불확실도도 그대로 전파돼 temporal 에서 폐색으로 잡힌다.
    """
    kp = np.asarray(keypoints, dtype=float)
    if kp.ndim != 3 or kp.shape[1] < 17:
        raise ValueError("keypoints 형상은 (T,17,3|4) 이어야 합니다.")
    T = kp.shape[0]
    if kp.shape[2] < 4:
        return np.zeros((T, len(JOINT_KEYS)), dtype=float)

    unc = kp[:, :, 3]
    out = np.zeros((T, len(JOINT_KEYS)), dtype=float)
    for j, key in enumerate(JOINT_KEYS):
        an, bn, cn = JOINT_ANGLES[key]
        idx = [kp_index(an), kp_index(bn), kp_index(cn)]
        out[:, j] = np.max(unc[:, idx], axis=1)  # NaN/inf 전파
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
