"""붕괴 프레임 판정 — keypoint 가 한 점/한 세로선으로 뭉친 프레임 (순수).

**왜 confidence 로는 안 되는가.** 붕괴 프레임에서는 모델이 오히려 확신한다(08-09 실측:
붕괴 프레임의 관절 conf 0.67 로 표시 게이트 통과). 2026-08-10 실측이 더 선명하다 —
`right_elbow` 카드의 프레임은 팔꿈치 conf **0.57** 로 게이트(0.5)를 통과했는데
12관절 중 **10개가 x=0.532 한 세로선**(폴)에 뭉쳤고 `right_shoulder` 와 `right_hand` 가
**같은 좌표**였다. 결과: 사이각 **0도**, 링이 팔꿈치 아닌 골반에, 그리고 **−11.6점 카드**.

그래서 신뢰도와 **직교하는 축**으로 본다: 좌표가 서로 뭉쳤는가.

**이 판정이 여는 것.** 08-09 에 표시 창을 넓힐 수 없었던 이유가 선택 기준이
`confidence 최대` 여서 넓힐수록 붕괴를 끌어당긴 것이었다. 붕괴를 명시 배제하면 넓히는
것이 안전해진다 — 실패 기전 자체가 사라진다.

채점 무접촉: 표시 프레임 선택에만 쓴다.
"""

from __future__ import annotations

import math
from collections import Counter

# 서로 다른 관절이 **같은 좌표**에 있는 것은 임계 문제가 아니라 불가능한 예측이다.
# 그래서 2 는 튜닝값이 아니라 정의값(중복이 하나라도 있으면 붕괴).
SAME_POINT_MIN = 2

# 한 세로선(폴)에 몰린 관절 수. 2026-08-10 실측 10프레임에서 깨끗 1~3 / 붕괴 5~10 으로
# 갈렸고 4 는 그 **빈 구간** 안이다(임계를 곡선맞춤한 것이 아니라 데이터가 비운 자리).
# ★표본이 10프레임이라 작다 — 확대 검증 대상으로 박제한다.
SAME_X_MIN = 4
CALIBRATION_SAMPLE_FRAMES = 10

# 좌표 동일 판정 해상도. 정규화(0~1)와 px(수천) 어느 쪽이든 같은 판정이 나오도록
# 절대값이 아니라 **좌표 범위에 비례**해 양자화한다(아래 `_quantize`).
_QUANT_STEPS = 10_000

# 이보다 적은 유효 관절로는 뭉침을 논할 수 없다 — 판정 불가(붕괴로 단정하지 않는다).
# 붕괴로 단정하면 결측 많은 프레임이 전부 표시에서 빠져 카드가 사라진다(fail-open).
MIN_POINTS = 4


def _finite_points(points):
    out = []
    for p in points or ():
        if p is None:
            continue
        try:
            x, y = float(p[0]), float(p[1])
        except (TypeError, ValueError, IndexError):
            continue
        if math.isfinite(x) and math.isfinite(y):
            out.append((x, y))
    return out


def _quantize(vals):
    """좌표 범위에 비례한 양자화 — 스케일 무관 동일 판정."""
    lo, hi = min(vals), max(vals)
    span = hi - lo
    if span <= 0:
        return [0] * len(vals)
    step = span / _QUANT_STEPS
    return [int(round((v - lo) / step)) for v in vals]


def diagnostics(points) -> dict:
    """붕괴 지표 (순수) — {n, decidable, same_point, max_same_x}."""
    pts = _finite_points(points)
    n = len(pts)
    if n < MIN_POINTS:
        return {"n": n, "decidable": False, "same_point": 0, "max_same_x": 0}
    qx = _quantize([p[0] for p in pts])
    qy = _quantize([p[1] for p in pts])
    dup = Counter(zip(qx, qy))
    same_point = sum(c for c in dup.values() if c > 1)
    xs = Counter(qx)
    return {"n": n, "decidable": True, "same_point": same_point,
            "max_same_x": max(xs.values())}


def is_collapsed(points, *, same_point_min: int = SAME_POINT_MIN,
                 same_x_min: int = SAME_X_MIN) -> bool:
    """이 프레임의 keypoint 가 뭉쳤는가 (순수). 판정 불가면 False(fail-open)."""
    d = diagnostics(points)
    if not d["decidable"]:
        return False
    return d["same_point"] >= same_point_min or d["max_same_x"] >= same_x_min
