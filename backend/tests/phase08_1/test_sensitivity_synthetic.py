"""Plan 08.1-02 Task 2.5 — synthetic sensitivity unit test.

3 case (C-M3 정합):
  - above medium → 'medium'
  - above high → 'high'
  - perfect vertical (shoulder=0, hip=0) → 'low'

source-of-truth = synthetic_sensitivity_check.py 의 path 와 동일 (_severity_from_tilt +
_max_severity). yaml load 통해 실제 cutoff 적용.

per Plan 08.1-02 Task 2.5 acceptance.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from sunity_shared.analysis.force_signals import (
    _max_severity,
    _severity_from_tilt,
)


def _load_cutoffs() -> tuple[tuple[float, float], tuple[float, float]]:
    yaml_path = (
        Path(__file__).resolve().parents[2]
        / "judging_data" / "tilt_thresholds.yaml"
    )
    data = yaml.safe_load(yaml_path.read_text())
    s = data["shoulder_tilt"]["operational_cutoff"]
    h = data["hip_tilt"]["operational_cutoff"]
    return (
        (float(s["medium_cutoff_deg"]), float(s["high_cutoff_deg"])),
        (float(h["medium_cutoff_deg"]), float(h["high_cutoff_deg"])),
    )


def _eval(sh_deg: float, hp_deg: float) -> str:
    sh, hp = _load_cutoffs()
    return _max_severity(
        _severity_from_tilt(sh_deg, sh),
        _severity_from_tilt(hp_deg, hp),
    )


def test_above_medium_yields_medium() -> None:
    sh, _ = _load_cutoffs()
    medium_cutoff = sh[0]
    assert _eval(medium_cutoff + 1.0, 0.0) == "medium"


def test_above_high_yields_high() -> None:
    sh, _ = _load_cutoffs()
    high_cutoff = sh[1]
    assert _eval(high_cutoff + 1.0, 0.0) == "high"


def test_perfect_vertical_yields_low() -> None:
    """shoulder=0, hip=0 → 'low' (정은지 baseline invariant)."""
    assert _eval(0.0, 0.0) == "low"
