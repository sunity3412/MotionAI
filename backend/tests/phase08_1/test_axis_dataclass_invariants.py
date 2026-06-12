"""Plan 08.1-00 Wave 0 Task 1 — BodyLineTiltMetric 6 필드 dataclass invariant test.

D-01 정합 — 6 필드 인스턴스화 PASS + invalid severity/confidence/phase ValueError +
제거된 5 필드 kwarg TypeError.

per Plan 08.1-00 must_haves.
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.force_signals import BodyLineTiltMetric


# ── 6 필드 인스턴스화 PASS ────────────────────────────────────────────────


def test_axis_dataclass_six_fields_instantiation() -> None:
    """6 필드 인스턴스화 PASS — phase='hold' / shoulder_tilt=12.5 / hip_tilt=8.3."""
    m = BodyLineTiltMetric(
        phase="hold",
        shoulder_tilt=12.5,
        hip_tilt=8.3,
        severity="low",
        confidence="medium",
        warnings=[],
    )
    assert m.phase == "hold"
    assert m.shoulder_tilt == 12.5
    assert m.hip_tilt == 8.3
    assert m.severity == "low"
    assert m.confidence == "medium"
    assert m.warnings == []


def test_axis_dataclass_nullable_tilts() -> None:
    """shoulder_tilt=None + hip_tilt=None 박제 PASS (Wave 0 stub default)."""
    m = BodyLineTiltMetric(
        phase="entry",
        shoulder_tilt=None,
        hip_tilt=None,
        severity="low",
        confidence="low",
        warnings=["phase_8_1_wave_0_transitional"],
    )
    assert m.shoulder_tilt is None
    assert m.hip_tilt is None


# ── invalid 검증 ──────────────────────────────────────────────────────────


def test_axis_dataclass_invalid_severity_raises() -> None:
    with pytest.raises(ValueError, match="severity"):
        BodyLineTiltMetric(
            phase="hold",
            shoulder_tilt=None,
            hip_tilt=None,
            severity="invalid",  # type: ignore[arg-type]
            confidence="low",
            warnings=[],
        )


def test_axis_dataclass_invalid_confidence_raises() -> None:
    with pytest.raises(ValueError, match="confidence"):
        BodyLineTiltMetric(
            phase="hold",
            shoulder_tilt=None,
            hip_tilt=None,
            severity="low",
            confidence="invalid",  # type: ignore[arg-type]
            warnings=[],
        )


def test_axis_dataclass_invalid_phase_raises() -> None:
    with pytest.raises(ValueError, match="phase"):
        BodyLineTiltMetric(
            phase="invalid",  # type: ignore[arg-type]
            shoulder_tilt=None,
            hip_tilt=None,
            severity="low",
            confidence="low",
            warnings=[],
        )


# ── 제거된 5 필드 kwarg TypeError (D-01 hard break) ──────────────────────


def test_axis_dataclass_distance_kwarg_raises_typeerror() -> None:
    """제거된 5 필드 (pelvis_distance_from_pole_axis 등) kwarg 박제 TypeError raise.

    dataclass __init__ 이 unexpected keyword argument 박제 TypeError 자동 raise —
    D-01 hard break 검증.
    """
    with pytest.raises(TypeError, match="pelvis_distance_from_pole_axis|unexpected keyword"):
        BodyLineTiltMetric(
            phase="hold",
            shoulder_tilt=None,
            hip_tilt=None,
            severity="low",
            confidence="low",
            warnings=[],
            pelvis_distance_from_pole_axis=1.0,  # type: ignore[call-arg]
        )
