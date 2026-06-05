"""IPSF 실행 심사기준 기반 점수 차원 (docs/research/폴스포츠-지식.md 보고서 5·6).

신체 부위(상체/코어/하체)가 아니라 심판이 실제로 보는 실행 차원으로 채점한다:

  - angle      각도 정확도  : 관절각 vs 기준(reference) 편차. reference 필요.
                             (mode1=정은지, mode3=이전 영상). kismam.overall_score 사용.
  - line       라인·확장    : '펴야 하는' 사지의 신전 완성도. **기술 조건부** — 어떤
                             관절이 펴져야 하는지는 TechniqueProfile 이 정한다.
  - stability  안정성·홀딩  : 피크/홀딩 구간의 시간축 떨림(분산). 절대 지표.

2026-05-29 재교정: '균형(좌우 대칭)' 차원 제거. IPSF 기술감점 프로토콜(보고서 6 §4)에
좌우 신체 대칭 항목이 없고, 폴 동작 상당수가 의도적 비대칭이라 대칭 페널티가 정상
동작(세계챔피언 포함)을 깎는 위양성이었다. line 도 무조건 180° 가 아니라 기술이 신전을
요구하는 관절(profile.expects_extension)에만 적용 — '의도된 굽힘'을 결함으로 깎지 않는다.

점수 스케일은 kismam.score_from_deviation(가우시안 z=편차/허용오차)을 공유한다.
허용오차(tol)는 IPSF 기준(각도 허용오차 20°)에서 출발한 휴리스틱 — belle 시연
데이터로 튜닝 예정.
"""

from __future__ import annotations

import numpy as np

from . import kismam
from .skeleton import JOINT_KEYS
from .technique import TechniqueProfile

# 차원 키 (contract / app dimensionScores 키와 동일 문자열).
DIM_ANGLE = "angle"
DIM_LINE = "line"
DIM_STABILITY = "stability"
# 기준 영상 없이 산출 가능한 절대 지표 — mode3 첫 분석부터 사용.
ABSOLUTE_DIMENSIONS = (DIM_LINE, DIM_STABILITY)

# 허용오차(도). z=dev/tol 가우시안 → tol 만큼 벗어나면 점수 ~61.
_LINE_TOL_DEG = 20.0      # 완전 신전(180°) 대비 부족분. IPSF 각도 허용오차 20° 기준.
_STABILITY_TOL_DEG = 15.0  # Path T1 (2026-06-05): inter-frame diff median 기준. 정은지 reference 5영상 wobble 측정 6~16° 박제 → 사용자 영상 정상 wobble 범위 박제 정신 정합 (RTMW noise + 자세 미세 변화 흡수). 진짜 떨림 (20°+) 만 FAIL.

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


def stability_score(angles, profile: "TechniqueProfile | None" = None) -> int:
    """홀딩 구간 관절각 안정도 → 가우시안. 낮은 떨림 = 통제된 정지.

    Path R (2026-06-05): inter-frame difference median 알고리즘 — 박제 정신 정합.
    Path H production (2026-06-05): profile.hold_window 우선 사용 (Gemini KeyMoments 박제),
    없으면 자동 추출 fallback (FallbackRecognizer path 회귀 0).
    """
    a = _as_tj(angles)
    if a.shape[0] <= 1:
        return 100  # 프레임이 1개뿐이면 떨림 측정 불가 — 감점 근거 없음
    if profile is not None and profile.hold_window is not None:
        s, e = profile.hold_window
        s = max(0, min(s, a.shape[0]))
        e = max(s, min(e, a.shape[0]))
    else:
        s, e = hold_window(a)
    sliced = a[s:e]
    if sliced.shape[0] < 2:
        return 100
    # 인접 frame 간 angle 차이 (jerk) — outlier robust median 사용
    inter_frame_diff = np.abs(np.diff(sliced, axis=0))  # (T-1, J)
    median_jerk = np.nanmedian(inter_frame_diff, axis=0)  # (J,)
    wobble = float(np.nanmean(median_jerk))
    return kismam.score_from_deviation(wobble, _STABILITY_TOL_DEG)


def line_score(angles, profile: TechniqueProfile) -> int | None:
    """라인·확장 점수. 홀딩 구간 대표 포즈에서, profile 이 신전(EXTEND)을 요구한
    관절만 180° 대비 부족분으로 채점한다. 신전 요구 관절이 하나도 없으면(전부 의도적
    굽힘) 라인 평가 대상이 아니므로 None → 해당 차원 생략(가짜 점수 안 만듦).

    Path H production (2026-06-05): profile.hold_window 우선 사용.
    """
    a = _as_tj(angles)
    if profile.hold_window is not None:
        s, e = profile.hold_window
        s = max(0, min(s, a.shape[0]))
        e = max(s, min(e, a.shape[0]))
    else:
        s, e = hold_window(a)
    rep = np.mean(a[s:e], axis=0)
    deficits = [
        max(0.0, _FULL_EXTENSION_DEG - float(rep[JOINT_KEYS.index(k)]))
        for k in JOINT_KEYS
        if profile.expects_extension(k)
    ]
    if not deficits:
        return None
    return kismam.score_from_deviation(float(np.mean(deficits)), _LINE_TOL_DEG)


def extension_deviation(angles, profile: TechniqueProfile) -> np.ndarray:
    """관절별 신전 부족분(도) 벡터 (J,) — 코칭 tips 용. EXTEND 관절만 (180-각),
    그 외는 0. mode3 첫 분석에서 '더 펴주세요' 코칭의 IPSF 라인 근거."""
    a = _as_tj(angles)
    s, e = hold_window(a)
    rep = np.mean(a[s:e], axis=0)
    dev = np.zeros(len(JOINT_KEYS), dtype=float)
    for i, k in enumerate(JOINT_KEYS):
        if profile.expects_extension(k):
            dev[i] = max(0.0, _FULL_EXTENSION_DEG - float(rep[i]))
    return dev


def absolute_dimension_scores(angles, profile: TechniqueProfile) -> dict[str, int]:
    """기준 영상 없이 산출하는 절대 차원 점수. 항상 stability, 신전 관절이 있으면 line.
    mode3 첫 분석 + 모든 분석의 절대 지표 부분."""
    out: dict[str, int] = {}
    ls = line_score(angles, profile)
    if ls is not None:
        out[DIM_LINE] = ls
    out[DIM_STABILITY] = stability_score(angles, profile)
    return out


def overall_from_dimensions(dimension_scores: dict[str, int]) -> int:
    """차원 점수 평균 = 종합 점수. 빈 dict 면 0."""
    vals = list(dimension_scores.values())
    return int(round(sum(vals) / len(vals))) if vals else 0
