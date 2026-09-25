"""벌림 규칙 — 기준 실행 창 **마지막 1/3 구간**의 두 허벅지 사이각 중앙값, 정은지 상대 (quick-260925-nnt).

왜 있나
───────
belle 2026-09-25 (power-spin 실수, 봉인 정답): *"다리 벌림이 다르다 = 다리가 1자로 쫙 벌려졌는가, 조금만 벌려졌는가"*.
기존 split 기하 경로는 **클립 최대값**(peak)을 썼는데 2D 사이각은 다리를 접은 순간(tuck)에도 두 허벅지가
반평행이면 180° 로 포화한다(기준 power-spin r43 180.0, kip-up 기준 180.0) — 그래서 게이트를 죽여 두었다.
동작이 **끝나는 구간**(스플릿을 완성하는 마지막 1/3)의 **중앙값**은 그 포화를 피한다: 09-24 저장 doc 실측
실수 39° · 정타 140° · 기준 138°(회전 중 두 허벅지가 화면과 나란해지는 0~4° 프레임이 끼어 있어 최소/최대가
아니라 중앙값이어야 한다).

어떻게 재나 (ig3 유지 구간 상수와 같은 규율)
──────────────────────────────────────────
- 기준 국면 = 기준 실행 창 (r0, r1) 의 마지막 1/3 [r_a, r1). 학생 국면 = 운영 DTW path 로 그 구간에 짝지어진
  학생 프레임의 [최소, 최대+1). 짝은 **가장자리에만** 쓴다 — 구간 안에서는 짝 없이 각자 중앙값(정체 짝이
  낮은 표본을 공급하는 c3m 함정 회피). path 가 없으면 학생 창의 마지막 1/3 로 대체.
- 사이각 = features.split_angle_series (IPSF split 정의, 두 허벅지 hip→knee 방향벡터 사이각, 2D).
- 부족분 = 기준 중앙값 − 학생 중앙값 (양수 = 학생이 덜 벌렸다). 소비 = 기존 `split_angle` criterion
  (reference_relative, tol 20, 관절 캡 −20) — 새 문턱 0.
- 순간 = 학생 국면에서 학생 중앙값에 가장 가까운 프레임(동률 = 앞) → 영상 멈춤·카드가 물려받는다.

fail-closed (None): 창·path 형상 이상 · 국면이 MIN_PHASE_FRAMES 미만 · 유한 표본 부족 · 사이각 비유한.
★ 이 규칙은 **어느 동작이 스플릿 요소인가**를 모른다 — 그 판단은 technique.SPLIT_LINE_ELEMENTS(호출측 게이트).
"""

from __future__ import annotations

import math

import numpy as np

from . import features

FINAL_PHASE_FRACTION = 1.0 / 3.0
MIN_PHASE_FRAMES = 5


def final_phase_split(student_kp, reference_kp, r_win, path_pairs, *, u_win=None) -> dict | None:
    """학생·기준 17점 keypoints (T,17,3+) + 기준 창 + 운영 DTW 절대 짝 → 마지막 국면 사이각 요약 | None."""
    try:
        r0, r1 = int(r_win[0]), int(r_win[1])
    except (TypeError, ValueError, IndexError):
        return None
    if r1 - r0 < MIN_PHASE_FRAMES:
        return None
    r_a = r0 + int(math.floor((r1 - r0) * (1.0 - FINAL_PHASE_FRACTION)))
    if r1 - r_a < MIN_PHASE_FRAMES:
        r_a = max(r0, r1 - MIN_PHASE_FRAMES)
    try:
        S = np.asarray(student_kp, dtype=float)
        R = np.asarray(reference_kp, dtype=float)
        if S.ndim != 3 or R.ndim != 3 or S.shape[1] != 17 or R.shape[1] != 17 or S.shape[2] < 2 or R.shape[2] < 2:
            return None
        s_series = features.split_angle_series(S[:, :, :3] if S.shape[2] >= 3 else np.pad(S, ((0, 0), (0, 0), (0, 1))))
        r_series = features.split_angle_series(R[:, :, :3] if R.shape[2] >= 3 else np.pad(R, ((0, 0), (0, 0), (0, 1))))
    except Exception:  # noqa: BLE001 — 형상·계산 실패는 미채점
        return None
    if r1 > len(r_series):
        return None
    # 학생 국면 — 짝은 가장자리에만
    us: list[int] = []
    try:
        for u, r in path_pairs or ():
            if r_a <= int(r) < r1:
                us.append(int(u))
    except (TypeError, ValueError):
        us = []
    if us:
        u_a, u_b = min(us), max(us) + 1
    elif u_win is not None:
        try:
            u0, u1 = int(u_win[0]), int(u_win[1])
        except (TypeError, ValueError, IndexError):
            return None
        u_a = u0 + int(math.floor((u1 - u0) * (1.0 - FINAL_PHASE_FRACTION)))
        u_b = u1
    else:
        return None
    u_a, u_b = max(0, u_a), min(len(s_series), u_b)
    if u_b - u_a < MIN_PHASE_FRAMES:
        return None
    s_seg = s_series[u_a:u_b]
    r_seg = r_series[r_a:r1]
    s_ok = np.isfinite(s_seg)
    r_ok = np.isfinite(r_seg)
    if s_ok.sum() < MIN_PHASE_FRAMES or r_ok.sum() < MIN_PHASE_FRAMES:
        return None
    s_med = float(np.median(s_seg[s_ok]))
    r_med = float(np.median(r_seg[r_ok]))
    if not (math.isfinite(s_med) and math.isfinite(r_med)):
        return None
    dist = np.where(s_ok, np.abs(s_seg - s_med), np.inf)
    s_frame = int(u_a + int(np.argmin(dist)))
    return {
        "studentDeg": s_med,
        "referenceDeg": r_med,
        "deficitDeg": r_med - s_med,
        "studentFrame": s_frame,
        "studentPhase": (int(u_a), int(u_b)),
        "referencePhase": (int(r_a), int(r1)),
        "nStudent": int(s_ok.sum()),
        "nReference": int(r_ok.sum()),
    }
