"""Phase 34 수술 ③ — 좌우 기능 짝맞춤 (quick-260808-r82). numpy-only 순수 모듈.

미러 수행(그립팔이 기준과 좌우 거울상) 시 right-vs-right 비교는 "그립팔 vs 자유팔"
비교가 된다 — 근거 실측(memory mirror-performance-side-matching-phase34): 엘보 미러
수행에서 user 오른손목-폴 x간격 0.20 vs ref 왼손목-폴 0.20 (거울상). 이 모듈은
(1) 그립측 판별(grip_side)과 (2) 팔 관절쌍 L/R 각도 열 스왑(swap_lr_arm_columns)을
제공한다. 판별 신뢰 미달 = None = 미발동 fail-closed — 채점 급변 금지(T-34-01).

**스크린 v0 실측과의 관계 (박제):** 자율 스크린 v0 은 전신 미러 스왑을 위치 특징
공간에서 시험했고 5동작 전부 미개선으로 기각됐다. 단 v0 은 **위치 공간의 전신**
스왑이었고, 이 스왑은 **각도 공간의 국소(팔) L/R 열 교환** — 다른 연산이다. 관절각은
좌표계 미러의 영향을 받지 않는 스칼라라, 기능 동등 관절(그립팔↔그립팔)끼리 짝만
바꾸면 된다. 다리(hip/knee) 무접촉이 기본 — 다리 확장은 하네스 --side 실측에서
발동 doc 의 다리 편차가 일관 개선될 때만(quick-260808-r82 PLAN Task 2).

네트워크/영상/모델 금지 — 입력은 이미 산출된 joints3d 배열과 각도 행렬뿐.
"""

from __future__ import annotations

import numpy as np

# 그립 판별 std 비 하한 — 구조 유도 (fixture curve-fit 아님):
# 그립 손목 = 폴 접점에 고정(잔여 이동 = 몸통 흔들림 스케일, cm대) vs 자유 손목 =
# 팔 길이 스케일 스윕(수십 cm대). 고정점 대 스윕 말단의 운동 스케일은 역학 구조상
# 한 자릿수 배수로 갈린다 — 2.0(분산 4배)은 그 갈림의 보수적 하한이다. 근거 관측은
# 하네스 --side 표(quick-260808-r82 data/side_report.md)가 증거 의무를 진다.
GRIP_STD_RATIO_MIN = 2.0

# 유효 프레임 게이트에 쓰는 keypoint 신뢰 임계 — fault-zoom 마커 게이트
# (fault_zoom._KP_CONF_MIN=0.5)와 동일 임계 재사용 (신규 튜닝 0).
_CONF_MIN = 0.5

# L/R 기능 짝 — skeleton.JOINT_KEYS 의 좌우 쌍. 팔 = elbow/shoulder (기본 스왑 대상),
# 다리 = hip/knee (기본 무접촉 — 하네스 실측 근거 없이는 확장 금지).
ARM_LR_PAIRS: tuple[tuple[str, str], ...] = (
    ("left_elbow", "right_elbow"),
    ("left_shoulder", "right_shoulder"),
)
LEG_LR_PAIRS: tuple[tuple[str, str], ...] = (
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
)


def _wrist_track(arr: np.ndarray, keys: list[str] | tuple[str, ...], name: str,
                 confidence=None) -> np.ndarray:
    """(T,K,3) → 해당 손목의 (T,3) 궤적. 무효 프레임은 NaN 행.

    무효 = 비유한 좌표 / **전-0 triple**(joints3d 저장 시 NaN→0.0 sentinel 변환 —
    pipeline app.py "joints3d flat 박제" 절. 0,0,0 을 실좌표로 읽으면 정지로 오인해
    그립을 위조한다) / confidence 주어지면 conf < 0.5 프레임.
    """
    if name not in keys:
        return np.full((len(arr), 3), np.nan)
    j = list(keys).index(name)
    track = np.asarray(arr[:, j, :3], dtype=float).copy()
    finite = np.isfinite(track).all(axis=1)
    zero_sentinel = np.all(track == 0.0, axis=1)
    invalid = ~finite | zero_sentinel
    if confidence is not None:
        conf = np.asarray(confidence, dtype=float)
        if conf.ndim == 2 and conf.shape[0] == len(arr) and j < conf.shape[1]:
            invalid |= ~(conf[:, j] >= _CONF_MIN)
    track[invalid] = np.nan
    return track


def _spatial_std(track: np.ndarray) -> tuple[float, int]:
    """(T,3) 궤적 → (공간 표준편차 스칼라, 유효 프레임 수). NaN-aware.

    스칼라 = sqrt(var_x+var_y+var_z) — 축별 nanstd 의 합성(전체 공간 분산의 제곱근).
    """
    valid = int(np.isfinite(track).all(axis=1).sum())
    if valid == 0:
        return float("nan"), 0
    with np.errstate(invalid="ignore"):
        stds = np.nanstd(track, axis=0)
    return float(np.sqrt(np.nansum(stds**2))), valid


def grip_side(joints3d, joint_keys, confidence=None, debug_out=None):
    """그립측 판별 — "left" | "right" | None(판별 불가 = 미발동 fail-closed).

    left_wrist/right_wrist 궤적의 공간 분산 비교: 그립 손목 = 폴을 잡아 정지(잔여
    이동 = 몸통 흔들림 스케일) vs 자유 손목 = 팔 길이 스케일 스윕. 판별식:
    std_min * GRIP_STD_RATIO_MIN <= std_max 일 때만 작은 쪽을 그립으로 반환.

    Args:
        joints3d: (T,K,3) 위치 배열 또는 flat 1차원(len(joint_keys)*3 배수 —
            Firestore flat 저장 호환 reshape).
        joint_keys: K개 keypoint 이름 (left_wrist/right_wrist 포함 필요 — 없으면 None).
        confidence: (T,K) 신뢰도 배열(선택). 주어지면 conf >= 0.5 프레임만 유효
            (fault-zoom 마커 게이트 _KP_CONF_MIN 과 동일 임계 재사용).
        debug_out: dict 전달 시 {std_left, std_right, std_ratio, valid_left,
            valid_right, min_valid} 관측치 기록 (하네스 --side 표 / log 용 —
            out-param 선례: seed_audit_out).

    None 조건 (전부 fail-closed):
        · 어느 손목이든 유효 프레임 < max(9, T//4) — 9프레임 = 9fps 1초. 1초 미만
          관측으로 그립 판정 금지(구조 유도 — 폴 그립은 초 단위로 유지되는 상태다).
        · std 비 < GRIP_STD_RATIO_MIN (비슷한 분산 = 양손 그립/전환/판별 불가).
        · 입력 형상 불량 / 손목 키 부재 / std 비유한.
    """
    arr = np.asarray(joints3d, dtype=float)
    keys = list(joint_keys or ())
    if not keys:
        return None
    if arr.ndim == 1:
        if len(keys) == 0 or arr.size % (len(keys) * 3) != 0:
            return None
        arr = arr.reshape(-1, len(keys), 3)
    if arr.ndim != 3 or arr.shape[0] == 0 or arr.shape[1] != len(keys):
        return None

    T = arr.shape[0]
    left = _wrist_track(arr, keys, "left_wrist", confidence)
    right = _wrist_track(arr, keys, "right_wrist", confidence)
    std_l, valid_l = _spatial_std(left)
    std_r, valid_r = _spatial_std(right)
    min_valid = max(9, T // 4)
    if isinstance(debug_out, dict):
        ratio = None
        if std_l == std_l and std_r == std_r:
            lo, hi = min(std_l, std_r), max(std_l, std_r)
            ratio = (hi / lo) if lo > 0 else float("inf")
        debug_out.update({
            "std_left": None if std_l != std_l else round(std_l, 4),
            "std_right": None if std_r != std_r else round(std_r, 4),
            "std_ratio": None if ratio is None else (
                round(ratio, 2) if np.isfinite(ratio) else float("inf")
            ),
            "valid_left": valid_l,
            "valid_right": valid_r,
            "min_valid": min_valid,
        })
    if valid_l < min_valid or valid_r < min_valid:
        return None
    if not (std_l == std_l and std_r == std_r):  # NaN 방어
        return None
    lo, hi = min(std_l, std_r), max(std_l, std_r)
    if lo * GRIP_STD_RATIO_MIN > hi:  # 분리 미달 = 판별 불가
        return None
    if lo == hi:  # 완전 동률(둘 다 0 포함) — 판별 불가
        return None
    return "left" if std_l < std_r else "right"


def _swap_columns(A, joint_keys, pairs) -> np.ndarray:
    """(T,J) 각도 행렬의 지정 L/R 짝 열만 교환한 **사본** 반환 (입력 무변경).

    pairs 의 두 이름이 모두 joint_keys 에 있을 때만 그 짝을 교환 — 부분 키 집합
    (mode3 축소 계약 등)에선 해당 짝만 조용히 생략(fail-closed)."""
    arr = np.asarray(A, dtype=float).copy()
    keys = list(joint_keys)
    for a, b in pairs:
        if a in keys and b in keys:
            ia, ib = keys.index(a), keys.index(b)
            arr[:, [ia, ib]] = arr[:, [ib, ia]]
    return arr


def swap_lr_arm_columns(A, joint_keys) -> np.ndarray:
    """(T,J) 각도 행렬의 팔 관절쌍(elbow/shoulder) L/R 열만 교환. 다리 무접촉.

    involution: swap(swap(A)) == A. 각도는 좌표계-미러 불변 스칼라라 열 교환만으로
    기능 동등 관절 비교가 성립한다 (모듈 docstring 의 v0 기각 근거와 구분 참조).
    """
    return _swap_columns(A, joint_keys, ARM_LR_PAIRS)
