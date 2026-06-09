"""Plan 08.1-01 Wave 1 Task 2 — calibration source preflight hard gate (C-H3).

3 case:
  (a) null shoulderTilt → RuntimeError
  (b) 'phase_8_1_wave_0_transitional' warning → RuntimeError
  (c) 25 non-null + warnings 청결 → PASS + null_tilt_verified=true 박제

per Plan 08.1-01 must_haves Step 3 (calibration preflight 3 tests).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_calibrate_module():
    """backend/scripts/calibrate_tilt_thresholds.py 를 직접 로드 (sys.path 미오염)."""
    script_path = (
        Path(__file__).parent.parent.parent
        / "scripts"
        / "calibrate_tilt_thresholds.py"
    )
    spec = importlib.util.spec_from_file_location(
        "calibrate_tilt_thresholds", script_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture(scope="module")
def calibrate_module():
    return _load_calibrate_module()


def _make_axis_metrics(
    *,
    shoulder_tilt: float | None = 15.0,
    hip_tilt: float | None = 10.0,
    warnings: list[str] | None = None,
) -> list[dict]:
    """5 phase axisMetrics 합성."""
    if warnings is None:
        warnings = []
    return [
        {
            "phase": phase,
            "shoulderTilt": shoulder_tilt,
            "hipTilt": hip_tilt,
            "severity": "low",
            "confidence": "medium",
            "warnings": warnings,
        }
        for phase in ("entry", "lock", "transition", "final_shape", "hold")
    ]


def _make_record(
    doc_id: str,
    *,
    shoulder_tilt: float | None = 15.0,
    hip_tilt: float | None = 10.0,
    warnings: list[str] | None = None,
) -> dict:
    return {
        "doc_id": doc_id,
        "data": {
            "result": {
                "forceSignalsReport": {
                    "axisMetrics": _make_axis_metrics(
                        shoulder_tilt=shoulder_tilt,
                        hip_tilt=hip_tilt,
                        warnings=warnings,
                    )
                }
            }
        },
    }


def _make_5_records(**kwargs) -> list[dict]:
    return [_make_record(f"doc_{i}", **kwargs) for i in range(5)]


# ── (a) null shoulderTilt → RuntimeError ────────────────────────────────


def test_preflight_rejects_null_shoulder_tilt(calibrate_module) -> None:
    records = _make_5_records(shoulder_tilt=None)
    with pytest.raises(RuntimeError, match="null shoulderTilt"):
        calibrate_module._preflight_calibration_source(records)


def test_preflight_rejects_null_hip_tilt(calibrate_module) -> None:
    records = _make_5_records(hip_tilt=None)
    with pytest.raises(RuntimeError, match="null hipTilt"):
        calibrate_module._preflight_calibration_source(records)


# ── (b) transitional warning → RuntimeError ────────────────────────────


def test_preflight_rejects_transitional_warning(calibrate_module) -> None:
    records = _make_5_records(warnings=["phase_8_1_wave_0_transitional"])
    with pytest.raises(RuntimeError, match="transitional"):
        calibrate_module._preflight_calibration_source(records)


def test_preflight_rejects_tilt_unavailable(calibrate_module) -> None:
    records = _make_5_records(warnings=["tilt_unavailable"])
    with pytest.raises(RuntimeError, match="tilt_unavailable"):
        calibrate_module._preflight_calibration_source(records)


# ── (c) clean records → PASS + null_tilt_verified=true ────────────────


def test_preflight_passes_with_clean_records(calibrate_module) -> None:
    records = _make_5_records(shoulder_tilt=15.0, hip_tilt=10.0, warnings=[])
    doc_ids = calibrate_module._preflight_calibration_source(records)
    assert len(doc_ids) == 5
    assert doc_ids == [f"doc_{i}" for i in range(5)]


# ── 5 doc 외 입력 reject ───────────────────────────────────────────────


def test_preflight_rejects_wrong_doc_count(calibrate_module) -> None:
    records = [_make_record(f"doc_{i}") for i in range(3)]  # 3 docs not 5
    with pytest.raises(RuntimeError, match="expected 5 docs"):
        calibrate_module._preflight_calibration_source(records)
