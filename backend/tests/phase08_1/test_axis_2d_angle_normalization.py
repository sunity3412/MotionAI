"""Plan 08.1-01 Wave 1 — `_normalize_angle_undirected` (C-M1).

modulo 180° + min(a, 180-a) → undirected line angle ∈ [0, 90].
keypoint ordering swap (left↔right) artifact 차단.

per Plan 08.1-01 must_haves Step 4 (C-M1).
"""

from __future__ import annotations

import math

import pytest

from sunity_shared.analysis.force_signals import _normalize_angle_undirected


def test_vertical_line_normalizes_to_90() -> None:
    """raw angle 90° (수직) → 90° (line tilt 의 worst case)."""
    assert math.isclose(_normalize_angle_undirected(90.0), 90.0, abs_tol=1e-9)


def test_horizontal_line_normalizes_to_0() -> None:
    """raw angle 0° (수평) → 0° (line tilt 의 best case)."""
    assert math.isclose(_normalize_angle_undirected(0.0), 0.0, abs_tol=1e-9)


def test_near_180_normalizes_to_small() -> None:
    """raw angle 175° → 5° (modulo 180 + min(a, 180-a))."""
    result = _normalize_angle_undirected(175.0)
    assert math.isclose(result, 5.0, abs_tol=1e-9)


def test_swapped_keypoints_same_tilt() -> None:
    """left↔right swap → raw 5° vs 185° → 둘 다 normalize 후 5° (동일)."""
    a = _normalize_angle_undirected(5.0)
    b = _normalize_angle_undirected(185.0)
    assert math.isclose(a, b, abs_tol=1e-9)
    assert math.isclose(a, 5.0, abs_tol=1e-9)


def test_negative_angle_normalizes_unsigned() -> None:
    """negative raw angle 도 [0, 90] 안 unsigned 정규화."""
    # -5° → 175° (modulo) → 5° (min(175, 5)=5).
    result = _normalize_angle_undirected(-5.0)
    assert math.isclose(result, 5.0, abs_tol=1e-9)


def test_above_90_below_180_reflects() -> None:
    """raw 120° → 60° (modulo 180=120, min(120, 60)=60)."""
    result = _normalize_angle_undirected(120.0)
    assert math.isclose(result, 60.0, abs_tol=1e-9)
