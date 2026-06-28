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


def split_angle_series(keypoints):
    """3D keypoints (T,17,3=xyz | T,17,4=xyz+불확실도) → 프레임별 inter-thigh split(도).

    IPSF split 정의(Code of Points, NotebookLM 2026-06-27): split 은 "the lines the
    inner thighs form in alignment with hips to knees" — 즉 두 허벅지 라인(각 다리
    hip→knee) 사이각이다. 본 함수는 좌 허벅지 방향벡터(left_hip→left_knee)와 우
    허벅지 방향벡터(right_hip→right_knee) 사이각을 잰다. 다리를 모으면(두 허벅지
    평행) ≈0°, 직교(한 다리 수평·한 다리 수직)면 ≈90°, 다리가 완전한 일직선
    (full split)이면 ≈180°. 더 벌릴수록 단조 증가한다.

    주의: hip-center 를 vertex 로 좌우 무릎의 subtended 각을 재면 안 된다 — 골반
    너비 때문에 다리가 평행해도(모음) 0°가 아닌 값이 나온다. 변별 대상은 두
    허벅지 라인 자체의 사이각이므로 방향벡터 각으로 측정한다.

    좌표는 :3 만 사용(4채널이면 불확실도 무시, compute_joint_angles 와 동일).
    정의 keypoint(좌우 hip/knee) 중 하나라도 NaN 인 프레임은 split NaN
    (_angle_deg 가 전파) — temporal/호출자가 폐색으로 처리한다.

    엔진/AWS/네트워크 의존 0, 순수 numpy. 두 허벅지 방향벡터 사이각은 원점을
    vertex 로 둔 _angle_deg 재사용으로 계산한다(중복 구현 금지).
    """
    kp = np.asarray(keypoints, dtype=float)
    if kp.ndim != 3 or kp.shape[1] < 17 or kp.shape[2] < 3:
        raise ValueError("keypoints 형상은 (T,17,3|4=xyz[,불확실도]) 이어야 합니다.")
    xyz = kp[:, :, :3]
    T = kp.shape[0]

    il, ir = kp_index("left_hip"), kp_index("right_hip")
    ilk, irk = kp_index("left_knee"), kp_index("right_knee")
    zero = np.zeros(3, dtype=float)

    out = np.full((T,), np.nan, dtype=float)
    for t in range(T):
        left_thigh = xyz[t, ilk] - xyz[t, il]
        right_thigh = xyz[t, irk] - xyz[t, ir]
        # vertex=원점에서 두 허벅지 방향벡터 사이각 = inter-thigh split.
        out[t] = _angle_deg(left_thigh, zero, right_thigh)
    return out


def max_split(split_series):
    """split 시계열 (T,) → (최대 split(도), 프레임 인덱스). 유한값 없으면 (nan, -1).

    안정 hold-window 가 아니라 **peak** 를 고른다 — dynamic 동작(kip-up 등)의
    변별 순간은 다리를 최대로 벌린 순간이다(belle 교훈: 안정 윈도우는 dynamic
    peak 를 평균으로 씻어내 변별을 잃는다). NaN 프레임은 무시한다.
    """
    s = np.asarray(split_series, dtype=float).ravel()
    finite = np.isfinite(s)
    if not finite.any():
        return (float("nan"), -1)
    idx = int(np.argmax(np.where(finite, s, -np.inf)))
    return (float(s[idx]), idx)


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


# ---------------------------------------------------------------------------
# 표시용 frame-specific per-joint 각도 (23-02 Task 1, D-02 각도 + D-10 HIGH-3).
#
# "무릎 145° vs 정은지 178°, 33° 더 굽음" 같은 결함 출력 표시 문장의 **단일 진실**.
# 반드시 verdict 를 낸 그 still 프레임 쌍(user_frame_idx/ref_frame_idx)의 행 값에서만
# 계산한다 — DTW window median(motiondtw.per_joint_deviation, scoring 경로)으로 계산하면
# 안 된다(D-10 HIGH-3). median 을 still 프레임의 "정확 각도"로 표기하면 정확해 보이는데
# 실은 윈도우 평균인 모호성이 생긴다. robustness 목적의 window median 이 필요하면 아래
# window_median_angle_deltas 로 **별도 명명**해 sourceFrameIndices/windowPolicy 를 동반한다.
#
# 출력은 각도(도)만 — 절대 cm/px 거리 0(D-02: 단일 카메라 스케일 모호), percent/% 0
# (D-08: gemini_vision_scorer._SCORE_PATTERN 누수로 정상 verdict 폐기 위험). 8개
# skeleton.JOINT_ANGLES 관절만 다룬다 — 머리/그립은 vision-only(Gemini differences 담당).
# 순수 numpy(어댑터/네트워크 무관).
# ---------------------------------------------------------------------------

# delta<0 = 학생 각이 작음 = 더 굽음(작은 각 = 굽음). delta>0 = 더 펴짐.
_DIR_MORE_BENT = "더 굽음"
_DIR_MORE_EXTENDED = "더 펴짐"


def _row_at(angle_matrix, idx: int):
    """(T, NUM_JOINTS) 각도 행렬에서 idx 행을 안전하게 꺼낸다 (범위 clamp 없음 — 정확 행)."""
    m = np.asarray(angle_matrix, dtype=float)
    if m.ndim != 2 or m.shape[1] != len(JOINT_KEYS):
        raise ValueError(
            f"angle_matrix 형상은 (T,{len(JOINT_KEYS)}) 이어야 합니다 — {m.shape}"
        )
    if idx < 0 or idx >= m.shape[0]:
        raise IndexError(f"frame_idx {idx} 가 (T={m.shape[0]}) 범위 밖")
    return m[idx]


def _delta_entry(joint: str, student_deg: float, reference_deg: float) -> dict:
    """관절 1개의 frame-specific delta dict (source='geometry')."""
    delta = float(student_deg) - float(reference_deg)
    direction = _DIR_MORE_BENT if delta < 0 else _DIR_MORE_EXTENDED
    return {
        "joint": joint,
        "student_deg": float(student_deg),
        "reference_deg": float(reference_deg),
        "delta_deg": delta,
        "direction": direction,
        "source": "geometry",
    }


def frame_pair_angle_deltas(
    student_angles,
    reference_angles,
    *,
    user_frame_idx: int,
    ref_frame_idx: int,
):
    """표시용 per-joint 각도 — verdict 프레임 쌍(user/ref_frame_idx)의 행 값에서만 (D-10 HIGH-3).

    학생 각도 행렬 (T_u, J) + 정은지 각도 행렬 (T_r, J) + **단일** user_frame_idx +
    **단일** ref_frame_idx 를 받아 관절별 {joint, student_deg, reference_deg, delta_deg,
    direction, source='geometry'} 를 그 **두 행의 값에서만** 계산한다. 예: user_frame_idx
    의 무릎 145 / ref_frame_idx 의 무릎 178 → delta -33, '더 굽음'.

    윈도우 median 아님 — 그 프레임 행 값(D-10 HIGH-3: median 을 still 프레임 정확
    각도로 표기 금지). NaN(선택 프레임 행 기준)인 관절은 결과에서 제외(np.isfinite).
    출력은 각도(도)만 — cm/px/percent 0.
    """
    s_row = _row_at(student_angles, int(user_frame_idx))
    r_row = _row_at(reference_angles, int(ref_frame_idx))
    out: list[dict] = []
    for j, joint in enumerate(JOINT_KEYS):
        sd = s_row[j]
        rd = r_row[j]
        if not (np.isfinite(sd) and np.isfinite(rd)):
            continue  # 선택 프레임 행에서 NaN/inf 인 관절 제외
        out.append(_delta_entry(joint, sd, rd))
    return out


def window_median_angle_deltas(
    student_angles,
    reference_angles,
    *,
    user_frame_idx: int,
    ref_frame_idx: int,
    window: int = 2,
):
    """robustness 용 window median 각도 델타 — **별도 명명**(D-10 HIGH-3).

    still 프레임의 "정확 각도"가 아니라 선택 프레임 ±window 의 robust median 임을
    sourceFrameIndices/windowPolicy 메타로 명시한다. RTMW jitter 흡수용. 호출자는 이
    값을 frame_pair_angle_deltas(표시 각도)와 **다른 키**(windowMedianAngleDeltas)에
    담아 still 프레임 정확 각도와 혼동하지 않게 해야 한다.

    반환: {deltas: [...], sourceFrameIndices: {...}, windowPolicy: str}. deltas 항목은
    frame_pair_angle_deltas 와 같은 형상이되 각도는 윈도우 median(NaN 무시). NaN 만
    있는 관절은 제외.
    """
    s = np.asarray(student_angles, dtype=float)
    r = np.asarray(reference_angles, dtype=float)
    if s.ndim != 2 or s.shape[1] != len(JOINT_KEYS):
        raise ValueError(f"student_angles 형상은 (T,{len(JOINT_KEYS)}) 이어야 합니다.")
    if r.ndim != 2 or r.shape[1] != len(JOINT_KEYS):
        raise ValueError(f"reference_angles 형상은 (T,{len(JOINT_KEYS)}) 이어야 합니다.")

    def _win_idx(matrix, center: int) -> list[int]:
        lo = max(0, center - int(window))
        hi = min(matrix.shape[0] - 1, center + int(window))
        return list(range(lo, hi + 1))

    s_idx = _win_idx(s, int(user_frame_idx))
    r_idx = _win_idx(r, int(ref_frame_idx))

    deltas: list[dict] = []
    for j, joint in enumerate(JOINT_KEYS):
        s_vals = s[s_idx, j]
        r_vals = r[r_idx, j]
        s_fin = s_vals[np.isfinite(s_vals)]
        r_fin = r_vals[np.isfinite(r_vals)]
        if s_fin.size == 0 or r_fin.size == 0:
            continue
        sd = float(np.median(s_fin))
        rd = float(np.median(r_fin))
        deltas.append(_delta_entry(joint, sd, rd))

    return {
        "deltas": deltas,
        "sourceFrameIndices": {"user": s_idx, "reference": r_idx},
        # worst-pose 중심 ±window 프레임의 robust median (still 정확 각도 아님).
        "windowPolicy": f"worst_pose_center_pm_{int(window)}_median",
    }


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
