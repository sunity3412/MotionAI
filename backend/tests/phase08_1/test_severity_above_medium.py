"""Plan 08.1-01 Wave 1 — `_severity_from_tilt` above medium → 'medium'."""

from __future__ import annotations

from sunity_shared.analysis.force_signals import _severity_from_tilt


def test_severity_one_degree_above_medium_cutoff_is_medium() -> None:
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(26.0, thresholds) == "medium"


def test_severity_just_below_high_cutoff_is_medium() -> None:
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(37.5 - 0.001, thresholds) == "medium"


def test_severity_25_001_is_medium() -> None:
    """epsilon-aware: tilt = 25.001 → above medium_cutoff + 1e-9 → 'medium'."""
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(25.001, thresholds) == "medium"
