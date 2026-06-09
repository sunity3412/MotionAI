"""PoleLine2D + PoleAxisMeasurement contract test.

Task 1 (4 test): frozen 검증 + 점-직선 거리 analytical + coordinate_space invariant.
Task 2 (4 lockstep test 추가): TS interface + docs §9.0 + field camel/snake mirror.

per Plan 08-00 Task 1 + Task 2 <behavior>.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from sunity_shared.analysis.pole_geometry import (
    CoordinateSpace,  # noqa: F401 — Literal import 검증
    PoleAxisMeasurement,
    PoleLine2D,
    build_pole_axis_measurement,
    point_to_pole_line_distance_2d,
)

from .fixtures._factory import make_pole_axis, make_pole_line_2d


# ── Task 1: pole_geometry contract test ───────────────────────────────────

def test_pole_line_2d_frozen() -> None:
    """PoleLine2D 는 frozen — setattr 시 FrozenInstanceError."""
    line = make_pole_line_2d()
    with pytest.raises(FrozenInstanceError):
        line.confidence = 0.5  # type: ignore[misc]


def test_pole_axis_measurement_unavailable_returns_none_distance() -> None:
    """line=None 박제 시 coordinate_space='unavailable' 자동 강제.

    distance 산출 분기 = caller 책임 (PoleAxisMeasurement 자체는 distance 필드 없음).
    'unavailable' 시 caller 가 numeric 필드 None + warning 'pole_line_missing' 박제.
    """
    axis = make_pole_axis()
    measurement = build_pole_axis_measurement(axis_3d=axis, line=None)
    assert measurement.coordinate_space == "unavailable"
    assert measurement.line is None

    # invariant: line=None + coordinate_space != 'unavailable' → ValueError.
    with pytest.raises(ValueError):
        PoleAxisMeasurement(
            axis_3d=axis,
            line=None,
            coordinate_space="image_2d",
        )


def test_point_to_pole_line_distance_2d_analytical() -> None:
    """analytical sanity — horizontal/vertical line case."""
    # case 1: horizontal line at y=0, point=(0.5, 0.5) → distance = 0.5
    horizontal = PoleLine2D(
        point_image=(0.0, 0.0),
        direction_image=(1.0, 0.0),
        confidence=0.9,
        source="detected",
    )
    assert point_to_pole_line_distance_2d((0.5, 0.5), horizontal) == pytest.approx(
        0.5, abs=1e-6
    )

    # case 2: vertical line at x=0, point=(0.3, 0.5) → distance = 0.3
    vertical = PoleLine2D(
        point_image=(0.0, 0.0),
        direction_image=(0.0, 1.0),
        confidence=0.9,
        source="detected",
    )
    assert point_to_pole_line_distance_2d((0.3, 0.5), vertical) == pytest.approx(
        0.3, abs=1e-6
    )

    # case 3: point on the line → distance = 0
    assert point_to_pole_line_distance_2d((0.0, 0.5), vertical) == pytest.approx(
        0.0, abs=1e-6
    )


def test_build_pole_axis_measurement_image_line_present() -> None:
    """line 박제 시 coordinate_space='image_2d' 자동 박제."""
    axis = make_pole_axis()
    line = make_pole_line_2d()
    measurement = build_pole_axis_measurement(axis_3d=axis, line=line)
    assert measurement.coordinate_space == "image_2d"
    assert measurement.line is line
    assert measurement.axis_3d is axis
