"""PoleLine2D + PoleAxisMeasurement contract test.

Task 1 (4 test): frozen 검증 + 점-직선 거리 analytical + coordinate_space invariant.
Task 2 (4 lockstep test 추가): TS interface + docs §9.0 + field camel/snake mirror.

per Plan 08-00 Task 1 + Task 2 <behavior>.
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from sunity_shared.analysis.pole_geometry import (
    CoordinateSpace,  # noqa: F401 — Literal import 검증
    PoleAxisMeasurement,
    PoleLine2D,
    build_pole_axis_measurement,
    point_to_pole_line_distance_2d,
)

from .fixtures._factory import make_pole_axis, make_pole_line_2d


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TS_ANALYSIS = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_CONTRACT_MD = _REPO_ROOT / "docs" / "contract.md"


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


# ── Task 2: 3-way contract lockstep test ──────────────────────────────────

def _read_ts() -> str:
    return _TS_ANALYSIS.read_text(encoding="utf-8")


def _read_contract() -> str:
    return _CONTRACT_MD.read_text(encoding="utf-8")


def test_ts_interface_has_coordinate_space_contract() -> None:
    """analysis.ts — CoordinateSpace + ContactPrimitiveKind + PoleLine2D + PoleAxisMeasurement 박제."""
    ts = _read_ts()
    assert "export type CoordinateSpace" in ts
    assert "export type ContactPrimitiveKind" in ts
    assert "export interface PoleLine2D" in ts
    assert "export interface PoleAxisMeasurement" in ts
    # CoordinateSpace 4 값 명시.
    assert "'image_2d'" in ts
    assert "'pole_aligned'" in ts
    assert "'world_3d'" in ts
    assert "'unavailable'" in ts
    # ContactPrimitiveKind 3 값 명시.
    assert "'keypoint'" in ts
    assert "'segment'" in ts
    assert "'region_proxy'" in ts


def test_contract_md_has_section_9_0() -> None:
    """docs/contract.md — §9.0 + 7 subsection (9.0.1~9.0.7)."""
    md = _read_contract()
    assert "## §9.0. Coordinate/Scale Contract" in md
    for sub in (
        "§9.0.1",
        "§9.0.2",
        "§9.0.3",
        "§9.0.4",
        "§9.0.5",
        "§9.0.6",
        "§9.0.7",
    ):
        assert sub in md, f"missing subsection {sub} in §9.0"
    # 핵심 keyword
    assert "PoleLine2D" in md
    assert "PoleAxisMeasurement" in md
    assert "median_torso_length" in md
    assert "preflight" in md.lower()


def test_contract_md_has_contact_primitive_classification_table() -> None:
    """docs §9.0.7 — 12 contact point × kind 분류 박제."""
    md = _read_contract()
    # 핵심 매핑 grep (segment / region_proxy / keypoint).
    assert re.search(r"left_inner_thigh.*segment", md), "left_inner_thigh=segment 박제 missing"
    assert re.search(r"hip.*region_proxy", md), "hip=region_proxy 박제 missing"
    assert re.search(r"left_hand.*keypoint", md), "left_hand=keypoint 박제 missing"


def test_ts_python_field_camel_snake_mirror() -> None:
    """3-way contract — TS camelCase ↔ Python snake_case 5 field mirror."""
    ts = _read_ts()
    py_src = (
        _REPO_ROOT
        / "backend"
        / "shared"
        / "python"
        / "sunity_shared"
        / "analysis"
        / "pole_geometry.py"
    ).read_text(encoding="utf-8")

    # 5 pair: pointImage ↔ point_image / directionImage ↔ direction_image /
    #         axis3d ↔ axis_3d / coordinateSpace ↔ coordinate_space /
    #         frameIndex ↔ frame_index
    pairs = [
        ("pointImage", "point_image"),
        ("directionImage", "direction_image"),
        ("axis3d", "axis_3d"),
        ("coordinateSpace", "coordinate_space"),
        ("frameIndex", "frame_index"),
    ]
    for camel, snake in pairs:
        assert camel in ts, f"TS missing camelCase field {camel}"
        assert snake in py_src, f"Python missing snake_case field {snake}"
