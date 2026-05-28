"""IPSF 실행 심사기준 기반 점수 차원 (docs/research/폴스포츠-지식.md 보고서 4·5·6).

신체 부위(상체/코어/하체)가 아니라 심판이 실제로 보는 실행 차원으로 채점한다:

  - angle      각도 정확도  : 관절각 vs 기준(reference) 편차. reference 필요.
                             (mode1=정은지, mode3=이전 영상). kismam.overall_score 사용.
  - line       라인·확장    : 펴야 할 사지(팔꿈치·무릎)의 신전 완성도. 절대 지표.
  - balance    균형·정렬    : 좌우 대칭. selfmotion.symmetry_deviation. 절대 지표.
  - stability  안정성·홀딩  : 피크/홀딩 구간의 시간축 떨림(분산). 절대 지표.

line/balance/stability 는 기준 영상이 필요 없는 '절대 지표'다 — mode3(자기 성장)에서
영상 1개만으로 절대 점수가 나오고, 세션 간 델타가 같은 척도라 진짜 발전을 측정한다.

점수 스케일은 kismam.score_from_deviation(가우시안 z=편차/허용오차)을 공유한다.
허용오차(tol)는 IPSF 기준에서 출발한 휴리스틱 — belle 시연 데이터로 튜닝 예정.
"""

from __future__ import annotations

import numpy as np

from . import kismam, selfmotion
from .skeleton import JOINT_KEYS

# 차원 키 (contract / app dimensionScores 키와 동일 문자열).
DIM_ANGLE = "angle"
DIM_LINE = "line"
DIM_BALANCE = "balance"
DIM_STABILITY = "stability"
# 기준 영상 없이 산출 가능한 절대 지표 — mode3 첫 분석부터 사용.
ABSOLUTE_DIMENSIONS = (DIM_LINE, DIM_BALANCE, DIM_STABILITY)

# 허용오차(도). z=dev/tol 가우시안 → tol 만큼 벗어나면 점수 ~61.
_BALANCE_TOL_DEG = 15.0   # 좌우 비대칭
_LINE_TOL_DEG = 15.0      # 완전 신전(180°) 대비 부족분
_STABILITY_TOL_DEG = 8.0  # 홀딩 구간 관절각 표준편차

# 신전(폄)을 평가하는 사지 관절 — 180°가 완전 신전. 어깨/고관절은 '폄' 의미가
# 달라 제외. 이 관절이 신전 영역(>= _EXTENSION_ZONE_DEG)에 있을 때만 라인 결함으로 봄
# (의도적으로 깊게 굽힌 자세는 라인 감점 대상이 아님 — IPSF 라인 정의).
_EXTENSION_JOINTS = ("left_elbow", "right_elbow", "left_knee", "right_knee")
_EXTENSION_ZONE_DEG = 150.0
_FULL_EXTENSION_DEG = 180.0


def _as_tj(angles) -> np.ndarray:
    a = np.asarray(angles, dtype=float)
    if a.ndim != 2 or a.shape[1] != len(JOINT_KEYS):
        raise ValueError(f"angles 형상은 (T,{len(JOINT_KEYS)}) 이어야 합니다.")
    return a


def hold_window(angles) -> tuple[int, int]:
    """가장 안정적인(분산 최소) 구간 (start, end). 홀딩=동작이 완성돼 정지한 지점.
    stability(그 구간의 떨림)와 line(그 구간의 대표 포즈) 둘 다 이 구간을 쓴다."""
    a = _as_tj(angles)
    t = a.shape[0]
    if t <= 1:
        return 0, t
    w = max(2, min(t, t // 4))
    best_s, best_v = 0, float("inf")
    for s in range(0, t - w + 1):
        v = float(np.mean(np.std(a[s : s + w], axis=0)))
        if v < best_v:
            best_v, best_s = v, s
    return best_s, best_s + w


def balance_score(angles) -> int:
    """좌우 대칭 점수. 대칭 편차(도) 평균 → 가우시안."""
    dev = selfmotion.symmetry_deviation(angles)  # (J,) 좌우 쌍 편차
    return kismam.score_from_deviation(float(np.mean(dev)), _BALANCE_TOL_DEG)


def stability_score(angles) -> int:
    """홀딩 구간 관절각 표준편차(떨림) → 가우시안. 낮은 떨림 = 통제된 정지."""
    a = _as_tj(angles)
    if a.shape[0] <= 1:
        return 100  # 프레임이 1개뿐이면 떨림 측정 불가 — 감점 근거 없음
    s, e = hold_window(a)
    wobble = float(np.mean(np.std(a[s:e], axis=0)))
    return kismam.score_from_deviation(wobble, _STABILITY_TOL_DEG)


def line_score(angles) -> int:
    """라인·확장 점수. 홀딩 구간 대표 포즈에서 사지 신전 완성도(180° 대비 부족분).

    신전 영역(>=150°)에 있는 팔꿈치/무릎만 라인 결함으로 본다. 의도적으로 굽힌
    자세(Chair/Tuck 등)는 제외. 신전 관절이 하나도 없으면 가장 펴진 관절의 부족분으로
    대체(폄을 유도) — 항상 값이 나오게 해 차원 누락을 막는다."""
    a = _as_tj(angles)
    s, e = hold_window(a)
    rep = np.mean(a[s:e], axis=0)  # 대표 포즈 (J,)
    deficits = []
    for key in _EXTENSION_JOINTS:
        ang = float(rep[JOINT_KEYS.index(key)])
        if ang >= _EXTENSION_ZONE_DEG:
            deficits.append(_FULL_EXTENSION_DEG - ang)
    if not deficits:
        # 신전 영역에 든 사지가 없음 → 가장 펴진 사지의 부족분으로 대체.
        max_ext = max(float(rep[JOINT_KEYS.index(k)]) for k in _EXTENSION_JOINTS)
        deficits.append(_FULL_EXTENSION_DEG - max_ext)
    return kismam.score_from_deviation(float(np.mean(deficits)), _LINE_TOL_DEG)


def absolute_dimension_scores(angles) -> dict[str, int]:
    """기준 영상 없이 산출하는 절대 차원 점수 (line/balance/stability).
    mode3 첫 분석 + 모든 분석의 절대 지표 부분."""
    return {
        DIM_LINE: line_score(angles),
        DIM_BALANCE: balance_score(angles),
        DIM_STABILITY: stability_score(angles),
    }


def overall_from_dimensions(dimension_scores: dict[str, int]) -> int:
    """차원 점수 평균 = 종합 점수. 빈 dict 면 0."""
    vals = list(dimension_scores.values())
    return int(round(sum(vals) / len(vals))) if vals else 0
