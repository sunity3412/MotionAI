"""붕괴 프레임 판정 — conf 게이트가 못 잡는 축 (quick-260810-e4v U5).

왜 새 판정이 필요한가 (2026-08-10 실측, belle 카드 판정에서 나옴):
`right_elbow` 카드는 팔꿈치 conf **0.57** 로 표시 게이트(0.5)를 통과했는데, 그 프레임은
12관절 중 **10개가 폴 위 한 세로선**에 뭉쳐 있었고 `right_shoulder` 와 `right_hand` 가
**완전히 같은 좌표**(0.532, 0.462)였다. 그래서 사이각이 **0도**가 되고 링이 팔꿈치가
아니라 골반에 찍힌 채 **−11.6점 카드**가 나갔다.

붕괴 프레임에서는 모델이 오히려 확신하므로(08-09 실측) **confidence 로는 원리적으로
못 걸러진다.** 그래서 "좌표가 서로 뭉쳤는가"를 따로 본다.

08-09 에 표시 창을 넓힐 수 없었던 이유도 이것이다 — 선택 기준이 `confidence 최대`라
넓힐수록 붕괴를 끌어당겼다. 붕괴를 **명시 배제**하면 넓히는 것이 안전해진다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import pose_collapse as pc  # noqa: E402

# 2026-08-10 실측 프레임 (belle 반려 영상 재분석 p34fresh1786338601)
COLLAPSED_RIGHT_ELBOW = [          # 나 frame 118 — 12관절 중 10개가 x=0.532
    (0.532, 0.462), (0.532, 0.462), (0.532, 0.462), (0.532, 0.601),
    (0.532, 0.629), (0.524, 0.556), (0.532, 0.470), (0.532, 0.510),
    (0.532, 0.545), (0.532, 0.580), (0.524, 0.500), (0.601, 0.700),
]
CLEAN_LEFT_HIP = [                 # 나 frame 96 — 저신뢰 0, 좌표 분산 정상
    (0.41, 0.22), (0.55, 0.24), (0.44, 0.47), (0.52, 0.48),
    (0.43, 0.66), (0.51, 0.67), (0.39, 0.35), (0.58, 0.36),
    (0.42, 0.83), (0.50, 0.84), (0.40, 0.29), (0.57, 0.30),
]


def test_identical_points_are_collapse_by_definition() -> None:
    """서로 다른 관절이 **같은 좌표**에 있는 것은 임계 문제가 아니라 불가능한 예측이다."""
    pts = [(0.5, 0.5), (0.5, 0.5), (0.1, 0.2), (0.3, 0.4)]
    assert pc.is_collapsed(pts) is True
    d = pc.diagnostics(pts)
    assert d["same_point"] == 2


def test_measured_collapsed_frame_is_caught() -> None:
    assert pc.is_collapsed(COLLAPSED_RIGHT_ELBOW) is True
    d = pc.diagnostics(COLLAPSED_RIGHT_ELBOW)
    assert d["max_same_x"] >= 8, d


def test_measured_clean_frame_passes() -> None:
    assert pc.is_collapsed(CLEAN_LEFT_HIP) is False
    d = pc.diagnostics(CLEAN_LEFT_HIP)
    assert d["same_point"] == 0
    assert d["max_same_x"] <= 2, d


def test_pole_line_without_identical_points_is_caught() -> None:
    """좌표가 겹치지 않아도 한 세로선에 몰리면 붕괴 — 폴 위 한 줄 패턴."""
    pts = [(0.5, 0.10 + 0.03 * i) for i in range(6)] + [(0.2, 0.9), (0.8, 0.9)]
    assert pc.is_collapsed(pts) is True


def test_none_and_missing_points_are_ignored_not_counted() -> None:
    """결측은 붕괴 증거가 아니다 — 세지 않는다(다른 게이트의 몫)."""
    pts = [None, None, (0.1, 0.2), (0.3, 0.4), (0.5, 0.6), (0.7, 0.8)]
    assert pc.is_collapsed(pts) is False
    assert pc.diagnostics(pts)["n"] == 4


def test_too_few_points_is_unknown_not_collapsed() -> None:
    """표본이 너무 적으면 판정 불가 — 붕괴로 단정하지 않는다(fail-open).

    붕괴로 단정하면 결측 많은 프레임이 전부 카드에서 빠져 표시가 사라진다.
    """
    assert pc.is_collapsed([(0.1, 0.2), (0.3, 0.4)]) is False
    assert pc.diagnostics([(0.1, 0.2)])["decidable"] is False


def test_thresholds_sit_in_the_observed_empty_band() -> None:
    """임계 근거를 테스트로 박제 — 실측 깨끗 1~3 / 붕괴 5~10 사이의 빈 구간.

    `SAME_POINT_MIN` 은 튜닝값이 아니다(중복 자체가 불가능한 예측이라 2).
    `SAME_X_MIN` 은 실측 10프레임에서 갈린 구간 안이다 — **표본이 작다**는 것도 함께 박제.
    """
    assert pc.SAME_POINT_MIN == 2
    assert 3 < pc.SAME_X_MIN < 5
    assert pc.CALIBRATION_SAMPLE_FRAMES == 10


@pytest.mark.parametrize("scale", [1.0, 640.0, 2160.0])
def test_scale_invariant(scale) -> None:
    """정규화 좌표든 px 든 같은 판정 — 호출측 좌표계에 안 걸린다."""
    pts = [(x * scale, y * scale) for x, y in CLEAN_LEFT_HIP]
    assert pc.is_collapsed(pts) is False
    bad = [(x * scale, y * scale) for x, y in COLLAPSED_RIGHT_ELBOW]
    assert pc.is_collapsed(bad) is True
