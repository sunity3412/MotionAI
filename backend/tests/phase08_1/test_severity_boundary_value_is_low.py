"""Plan 08.1-01 Wave 1 — `_severity_from_tilt` boundary value = 'low' (C-H2).

epsilon 1e-9 float-safety + boundary value (정확히 cutoff) = 'low' 유지.
정은지 baseline 이 25/25 'low' 유지 보장 (Codex iteration 2 HIGH 정합).
"""

from __future__ import annotations

from sunity_shared.analysis.force_signals import _severity_from_tilt


def test_boundary_medium_cutoff_is_low() -> None:
    """tilt == medium_cutoff → 'low' (epsilon 1e-9 안)."""
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(25.0, thresholds) == "low"


def test_boundary_high_cutoff_is_medium() -> None:
    """tilt == high_cutoff → 'medium' (medium_cutoff < tilt <= high_cutoff)."""
    thresholds = (25.0, 37.5)
    # tilt == 37.5, medium_cutoff=25.0 → tilt > 25.0+eps → 'medium'.
    # tilt == 37.5, high_cutoff=37.5 → tilt > 37.5+eps False → not 'high' → 'medium'.
    assert _severity_from_tilt(37.5, thresholds) == "medium"


def test_float_epsilon_safety_below_cutoff_is_low() -> None:
    """tilt == cutoff - 1e-12 → 'low' (epsilon 정합)."""
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(25.0 - 1e-12, thresholds) == "low"


def test_float_epsilon_safety_at_cutoff_is_low() -> None:
    """tilt == cutoff + 1e-12 → 'low' (epsilon 1e-9 안)."""
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(25.0 + 1e-12, thresholds) == "low"


def test_none_is_low() -> None:
    """tilt=None → 'low' (calibration source guard)."""
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(None, thresholds) == "low"
