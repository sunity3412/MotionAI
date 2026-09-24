"""유지 구간 몸 높이 — 기준 clipRange 창 안에서 학생·정은지의 엉덩이·낮은발·그립 손 높이 (quick-260924-vj1).

왜 있나
───────
belle 2026-09-24 kip-up 실수 판독: *"k24 부터 다리 뜨임의 틀림 … 발의 높이 … 끝까지 연속"*. 8관절 각도에는
"몸이 바닥에서 얼마나 떠 있나"가 없다 — 그 실수는 겨드랑이 각도(+33.9)로 **번져서만** 잡혔고, 카드는
"어깨 각도가 차이가 있어요"라고만 말했다(uff §1). 이 모듈은 그 높이를 저장 2D 키포인트에서 직접 잰다.

어떻게 재나 (ig3 유지 구간 상수와 같은 규율)
──────────────────────────────────────────
- 창 = 호출측이 넘긴 학생 (u0, u1) · 기준 (r0, r1) — 운영 `_reference_exec_window` + `_student_window_from_match`
  (DTW 는 창 가장자리에만 쓴다). 창 안에서는 **짝 없이** 중앙값.
- 단위 = 서 있을 때 몸길이(어깨~발목 세로 거리), 바닥 = 발목 y — 둘 다 각 영상 **창 이전 프레임**의 중앙값.
  각자 자기 좌표에서 정규화하므로 촬영 거리·해상도 차가 상쇄된다(uff 실측: 같은 스튜디오 바닥 0.811/0.814,
  몸길이 0.282/0.280 프레임 비).
- 높이(양수 = 바닥 위): 엉덩이(좌우 평균) · 낮은발(두 발목 중 낮은 쪽) · 그립 손(두 손 중 높은 쪽).
  손 기준(음수 = 손보다 아래): 엉덩이 − 그립 손 · 낮은발 − 그립 손.
- 앞/중/뒤 1/3: 각 영상 자기 창을 셋으로 나눈 구간의 중앙값 — "끝날 때까지"라고 말할 자격.

fail-closed (None)
──────────────────
보고서 형상 이상 · 창 이전 프레임 부족 · 창이 짧음 · 서 있는 자세로 볼 수 없음(몸길이 ≤ 0) ·
신뢰도 하한 미만 관절만 남음. None 이면 호출측은 아무 문장도 만들지 않는다(지금 문구 byte-동일).

채점 무접촉: 산출은 카드 문장 선택(`body_low_arm_open`)과 로그에만 쓰인다. 감점 md·record 값·순간에 닿지 않는다.
"""

from __future__ import annotations

import math
import warnings
from typing import Mapping

import numpy as np

# 좌표 신뢰 하한 — card_gates.HOLD_CONF_MIN(0.35, "각도 측정 좌표 신뢰 하한")과 같은 층.
# 값만 같게 두는 이유: card_gates 는 Gemini 설정·렌더러를 끌어와 순수 모듈이 import 하면 무거워진다.
# 두 값이 갈라지지 않게 test_hold_height.py 가 대조한다(신규 튜닝 상수 0).
MIN_CONF = 0.35

# 창 최소 프레임 — pipeline app._CONSTANT_WINDOW_MIN_FRAMES(5)와 같은 값(같은 창을 쓰므로).
MIN_WINDOW_FRAMES = 5
# 창 이전(서 있는) 프레임 최소 수 — 바닥·몸길이를 한 장으로 정하지 않기 위한 최소 표본.
MIN_STAND_FRAMES = 3

# 잡음 폭(몸길이 비). 근거 = 같은 영상의 판 간 차(09-22 vs 09-23, 다른 GPU): 높이 상수 |차| ≤ 0.5 프레임%
# (i38) ≈ 0.018 몸길이(몸길이 ≈ 0.28 프레임), 정타−정은지 ≤ 0.01(uff). 0.05 는 판 간 잡음의 약 2.8배다.
# ★판정은 이 값에 둔감하다 — uff 실측(kip-up 실수·정타)으로 0.03~0.12 어디서든 같은 결론이
# 나는 것을 test_hold_height.py 가 잠근다. 영상에 맞춰 이 값을 옮기지 말 것("조절" 금지).
# ★모르는 것: **다른 테이크**의 정타 변동. kip-up 정타는 기준과 같은 테이크라 0 이 당연하고, 유일한 다른 테이크
# 정타(power-spin, vj1 게이트)는 한 축에서 0.088(낮은발, 위쪽 방향)·그립 −0.075 까지 났다 — 네 조건을 동시에
# 만족한 정타는 없었다. 새 테이크(정은지 추가 촬영)가 오면 이 폭부터 다시 본다(봉인 시험지).
NOISE_BODY_LENGTH = 0.05

_NEEDED = (
    "left_shoulder", "right_shoulder", "left_hip", "right_hip",
    "left_ankle", "right_ankle", "left_hand", "right_hand",
)


def _arrays(report: Mapping | None):
    """keypointReport(dict) → (X (T,J,2), C (T,J), 이름→열) | None. 형상이 어긋나면 None."""
    if not isinstance(report, Mapping):
        return None
    try:
        joints = list(report.get("joints") or [])
        T = int(report.get("frames") or 0)
        J = len(joints)
        data = np.asarray(report.get("data") or [], dtype=float)
        conf = np.asarray(report.get("confidence") or [], dtype=float)
    except (TypeError, ValueError):
        return None
    if T <= 0 or J == 0 or data.size != T * J * 2 or conf.size != T * J:
        return None
    idx = {name: i for i, name in enumerate(joints)}
    if any(n not in idx for n in _NEEDED):
        return None
    return data.reshape(T, J, 2), conf.reshape(T, J), idx


def _y(X, C, idx, name):
    """관절 y (아래로 커짐). 신뢰도 하한 미만은 NaN."""
    v = X[:, idx[name], 1].copy()
    v[C[:, idx[name]] < MIN_CONF] = np.nan
    return v


def _nanmedian(v) -> float:
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else math.nan


def _series(report, window):
    """한 영상 → 창 안 프레임별 높이 5종 + 창 이전 기준(바닥·몸길이). 못 재면 None."""
    arr = _arrays(report)
    if arr is None:
        return None
    X, C, idx = arr
    T = X.shape[0]
    try:
        w0, w1 = int(window[0]), int(window[1])
    except (TypeError, ValueError, IndexError):
        return None
    if w0 < MIN_STAND_FRAMES or w1 > T or w1 - w0 < MIN_WINDOW_FRAMES:
        return None
    ank = np.vstack([_y(X, C, idx, "left_ankle"), _y(X, C, idx, "right_ankle")]).T
    sho = np.vstack([_y(X, C, idx, "left_shoulder"), _y(X, C, idx, "right_shoulder")]).T
    hip = np.vstack([_y(X, C, idx, "left_hip"), _y(X, C, idx, "right_hip")]).T
    hand = np.vstack([_y(X, C, idx, "left_hand"), _y(X, C, idx, "right_hand")]).T
    # 한 프레임의 두 관절이 모두 신뢰도 미만이면 nanmean/nanmax 가 빈 조각 경고를 낸다 — 그 프레임은
    # NaN 으로 남아 중앙값에서 빠지는 것이 의도라 경고만 끈다.
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        ank_mean = np.nanmean(ank, axis=1)
        sho_mean = np.nanmean(sho, axis=1)
        floor = _nanmedian(ank_mean[:w0])
        body = _nanmedian((ank_mean - sho_mean)[:w0])
        if not (math.isfinite(floor) and math.isfinite(body)) or body <= 0.0:
            return None
        low_ank = np.nanmax(ank, axis=1)        # 낮은발 = y 가 큰 쪽
        hip_y = np.nanmean(hip, axis=1)
        grip_y = np.nanmin(hand, axis=1)        # 그립 손 = 높은 손(y 가 작은 쪽)
    sl = slice(w0, w1)
    return {
        "hip": (floor - hip_y[sl]) / body,
        "lowFoot": (floor - low_ank[sl]) / body,
        "grip": (floor - grip_y[sl]) / body,
        "hipBelowHand": (grip_y[sl] - hip_y[sl]) / body,
        "lowFootBelowHand": (grip_y[sl] - low_ank[sl]) / body,
    }


def _thirds(v) -> list[float]:
    n = len(v)
    return [_nanmedian(v[n * k // 3: n * (k + 1) // 3]) for k in range(3)]


def hold_window_heights(
    student_report: Mapping | None,
    reference_report: Mapping | None,
    u_win,
    r_win,
) -> dict | None:
    """학생·정은지 유지 구간 높이 → `{axis: {student, reference, diff, thirds}}` | None.

    `student_report`·`reference_report` 는 **각도 프레임과 1:1** 인 keypointReport dict
    (학생 = 파이프라인 `keypoint_report_raw` 9fps 판, 기준 = 기준 doc `referenceKeypointReport`).
    `thirds` = [[학생, 정은지], ×3] (각 영상 자기 창의 앞/중/뒤). 하나라도 못 재면 None.
    """
    s = _series(student_report, u_win)
    r = _series(reference_report, r_win)
    if s is None or r is None:
        return None
    out: dict = {}
    for axis in ("hip", "lowFoot", "grip", "hipBelowHand", "lowFootBelowHand"):
        sm, rm = _nanmedian(s[axis]), _nanmedian(r[axis])
        if not (math.isfinite(sm) and math.isfinite(rm)):
            return None
        out[axis] = {
            "student": sm,
            "reference": rm,
            "diff": sm - rm,
            "thirds": [[a, b] for a, b in zip(_thirds(s[axis]), _thirds(r[axis]))],
        }
    return out


def body_low_arm_open(
    heights: dict | None,
    arm_signed_deg: float | None,
    *,
    noise: float = NOISE_BODY_LENGTH,
) -> bool:
    """belle kip-up 실수 판독의 **측정판** — 네 조건이 모두 잰 값으로 성립할 때만 True.

    ① 창 앞·중·뒤 1/3 **모두** 엉덩이와 낮은발이 정은지보다 잡음 폭 넘게 낮다 → "끝날 때까지 낮게 떠 있어요"
    ② 그립 손 높이 차가 잡음 폭 안이다 → "손 높이는 같은데"
    ③ 손 기준 엉덩이가 잡음 폭 넘게 낮다 → "몸이 손 아래로 처졌고"
    ④ 그 record 관절의 창 상수 부호가 + (팔-몸통 각이 더 열림) → "몸통에서 더 벌어져"

    하나라도 못 재거나(NaN·None) 어긋나면 False — 호출측은 지금 문구를 그대로 둔다.
    """
    if not isinstance(heights, dict) or arm_signed_deg is None:
        return False
    try:
        arm = float(arm_signed_deg)
        if not (math.isfinite(arm) and arm > 0.0):
            return False
        for axis in ("hip", "lowFoot"):
            for s, r in heights[axis]["thirds"]:
                if not (math.isfinite(s) and math.isfinite(r)) or not (s - r < -noise):
                    return False
        grip = float(heights["grip"]["diff"])
        below = float(heights["hipBelowHand"]["diff"])
    except (KeyError, TypeError, ValueError):
        return False
    if not (math.isfinite(grip) and abs(grip) <= noise):
        return False
    return math.isfinite(below) and below < -noise
