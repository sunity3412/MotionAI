"""Plan 08.1-01 Wave 1 — `_severity_from_tilt` above high → 'high'."""

from __future__ import annotations

from sunity_shared.analysis.force_signals import _severity_from_tilt


def test_severity_one_degree_above_high_cutoff_is_high() -> None:
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(38.5, thresholds) == "high"


def test_severity_far_above_high_cutoff_is_high() -> None:
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(70.0, thresholds) == "high"


def test_severity_just_above_high_epsilon_is_high() -> None:
    """epsilon-aware: tilt = 37.501 → above high_cutoff + 1e-9 → 'high'."""
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(37.501, thresholds) == "high"
