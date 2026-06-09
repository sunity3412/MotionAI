"""Plan 08.1-00 Wave 0 Task 1 — AxisDeviationMetric 3-way lockstep grep 검증.

D-01 (Distance Hard Break) 정합 — TS interface + Python dataclass + docs §9.3
모두 AxisDeviationMetric 박제 6 필드 (phase / shoulder_tilt / hip_tilt / severity /
confidence / warnings) 만 존재 + 제거된 5 필드 (pelvis_distance_from_pole_axis /
chest_distance_from_pole_axis / scale_denominator / coordinate_space /
deviation_direction) 부재.

per Plan 08.1-00 must_haves + RESEARCH §4 α-4 + IPSF NotebookLM citation 9.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest  # noqa: F401


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TS_PATH = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_CONTRACT_PATH = _REPO_ROOT / "docs" / "contract.md"


# 6 필드 박제 (남기는 set).
_TS_KEEP_FIELDS = {"phase", "shoulderTilt", "hipTilt", "severity", "confidence", "warnings"}
_PY_KEEP_FIELDS = {
    "phase",
    "shoulder_tilt",
    "hip_tilt",
    "severity",
    "confidence",
    "warnings",
}

# 5 필드 박제 (제거 set).
_TS_REMOVED_FIELDS = {
    "pelvisDistanceFromPoleAxis",
    "chestDistanceFromPoleAxis",
    "scaleDenominator",
    "coordinateSpace",
    "deviationDirection",
}
_PY_REMOVED_FIELDS = {
    "pelvis_distance_from_pole_axis",
    "chest_distance_from_pole_axis",
    "scale_denominator",
    "coordinate_space",
    "deviation_direction",
}


def _extract_ts_interface_block() -> str:
    """app/src/types/analysis.ts 의 `export interface AxisDeviationMetric { ... }` block 추출."""
    src = _TS_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"export interface AxisDeviationMetric \{[\s\S]*?\n\}",
        src,
    )
    assert m is not None, "TS interface AxisDeviationMetric block 부재"
    return m.group(0)


def _extract_contract_93_block() -> str:
    """docs/contract.md §9.3 block 추출 (§9.3 ~ 다음 §9.[4-9])."""
    src = _CONTRACT_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"### §9\.3 AxisDeviationMetric[\s\S]*?(?=### §9\.[4-9])",
        src,
    )
    assert m is not None, "docs §9.3 block 부재"
    return m.group(0)


# ── 6 필드 존재 검증 ──────────────────────────────────────────────────────


def test_axis_six_fields_present_in_ts() -> None:
    """TS interface AxisDeviationMetric block 박제 6 필드 모두 존재."""
    block = _extract_ts_interface_block()
    missing = [f for f in _TS_KEEP_FIELDS if f not in block]
    assert not missing, f"TS interface 박제 6 필드 누락: {missing}"


def test_axis_six_fields_present_in_python() -> None:
    """Python dataclass AxisDeviationMetric 박제 fields() 가 정확히 6 필드 set."""
    from sunity_shared.analysis.force_signals import AxisDeviationMetric

    names = {f.name for f in dataclasses.fields(AxisDeviationMetric)}
    assert names == _PY_KEEP_FIELDS, (
        f"Python dataclass 6 필드 정합 위반:\n"
        f"  expected: {_PY_KEEP_FIELDS}\n"
        f"  actual:   {names}"
    )


def test_axis_six_fields_present_in_docs() -> None:
    """docs §9.3 block 박제 6 필드 (camelCase + snake_case) 모두 행 존재."""
    block = _extract_contract_93_block()
    missing_camel = [f for f in _TS_KEEP_FIELDS if f not in block]
    missing_snake = [f for f in _PY_KEEP_FIELDS if f not in block]
    assert not missing_camel, f"docs §9.3 박제 camelCase 누락: {missing_camel}"
    assert not missing_snake, f"docs §9.3 박제 snake_case 누락: {missing_snake}"


# ── 5 필드 부재 검증 ──────────────────────────────────────────────────────


def test_distance_fields_removed_from_ts() -> None:
    """TS interface block 박제 5 필드 부재 (D-01 hard break).

    scope = `export interface AxisDeviationMetric { ... }` block 내부만.
    CoordinateSpace type alias 등 다른 위치 박제 허용.
    """
    block = _extract_ts_interface_block()
    present = [f for f in _TS_REMOVED_FIELDS if f in block]
    assert not present, (
        f"TS interface 박제 5 필드 잔존 — D-01 hard break 위반: {present}"
    )


def test_distance_fields_removed_from_python() -> None:
    """Python dataclass fields() 박제 5 필드 부재."""
    from sunity_shared.analysis.force_signals import AxisDeviationMetric

    names = {f.name for f in dataclasses.fields(AxisDeviationMetric)}
    present = _PY_REMOVED_FIELDS & names
    assert not present, (
        f"Python dataclass 5 필드 잔존 — D-01 hard break 위반: {present}"
    )


def test_distance_fields_removed_from_docs() -> None:
    """docs §9.3 block 박제 5 필드 부재 (camelCase 행 + snake_case 행 모두)."""
    block = _extract_contract_93_block()
    present_camel = [f for f in _TS_REMOVED_FIELDS if f in block]
    present_snake = [f for f in _PY_REMOVED_FIELDS if f in block]
    assert not present_camel, (
        f"docs §9.3 박제 camelCase 5 필드 잔존: {present_camel}"
    )
    assert not present_snake, (
        f"docs §9.3 박제 snake_case 5 필드 잔존: {present_snake}"
    )
