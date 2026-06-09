"""Plan 08.1-01 Wave 1 — `_get_tilt_thresholds()` lazy load + cache + fallback.

W10 정합 — fallback 신호 는 cache tuple 의 3rd element (list) 단일 source.
module-global mutable boolean flag 부재.

per Plan 08.1-01 must_haves Step 3 RED (loader 5 tests).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import yaml


# ── helpers ──────────────────────────────────────────────────────────────


def _write_valid_yaml(tmp_path):
    """schema_v2 compliant tilt_thresholds.yaml 합성 (loader 의 schema 검증 통과)."""
    yaml_data = {
        "schema_version": 2,
        "calibration_method": "elite_p100_plus_margin",
        "calibration_version": "1.1",
        "calibrated_at": "2026-06-09T00:00:00+00:00",
        "source": {
            "sweep_uid": "test_sweep",
            "sample_size": 25,
            "source_doc_ids": ["doc1", "doc2", "doc3", "doc4", "doc5"],
            "null_tilt_verified": True,
            "margin_deg": 5.0,
        },
        "shoulder_tilt": {
            "distribution": {"p25": 1.0, "p50": 2.0, "p75": 3.0, "p90": 4.0, "p100": 5.0},
            "operational_cutoff": {
                "medium_cutoff_deg": 20.0,
                "high_cutoff_deg": 40.0,
            },
        },
        "hip_tilt": {
            "distribution": {"p25": 0.5, "p50": 1.0, "p75": 1.5, "p90": 2.0, "p100": 2.5},
            "operational_cutoff": {
                "medium_cutoff_deg": 22.0,
                "high_cutoff_deg": 45.0,
            },
        },
        "ipsf_tolerance": {
            "source_ref": "test ref",
            "tolerance_deg": 20.0,
            "major_fault_deg": 40.0,
        },
    }
    path = tmp_path / "tilt_thresholds.yaml"
    with open(path, "w") as f:
        yaml.safe_dump(yaml_data, f, sort_keys=False)
    return path


# ── loader tests ─────────────────────────────────────────────────────────


def test_loader_reads_yaml_when_present(tmp_path, monkeypatch) -> None:
    """schema_v2 yaml 가용 → loader 가 operational_cutoff 정합 반환."""
    from sunity_shared.analysis import force_signals as fs

    yaml_path = _write_valid_yaml(tmp_path)
    monkeypatch.setattr(fs, "_TILT_THRESHOLDS_PATH", yaml_path)
    fs._TILT_THRESHOLDS_CACHE = None

    shoulder, hip, base_warnings = fs._get_tilt_thresholds()

    assert shoulder == (20.0, 40.0)
    assert hip == (22.0, 45.0)
    assert base_warnings == []


def test_loader_falls_back_when_yaml_missing(tmp_path, monkeypatch) -> None:
    """yaml 부재 → fallback (25.0, 37.5) + base_warnings = ['tilt_thresholds_fallback']."""
    from sunity_shared.analysis import force_signals as fs

    missing = tmp_path / "nonexistent.yaml"
    monkeypatch.setattr(fs, "_TILT_THRESHOLDS_PATH", missing)
    fs._TILT_THRESHOLDS_CACHE = None

    shoulder, hip, base_warnings = fs._get_tilt_thresholds()

    assert shoulder == fs.AXIS_TILT_THRESHOLDS_DEG
    assert hip == fs.AXIS_TILT_THRESHOLDS_DEG
    assert "tilt_thresholds_fallback" in base_warnings


def test_loader_caches_result(tmp_path, monkeypatch) -> None:
    """yaml.safe_load 가 한 번만 호출 (cache 정합)."""
    from sunity_shared.analysis import force_signals as fs

    yaml_path = _write_valid_yaml(tmp_path)
    monkeypatch.setattr(fs, "_TILT_THRESHOLDS_PATH", yaml_path)
    fs._TILT_THRESHOLDS_CACHE = None

    real_safe_load = yaml.safe_load
    with patch("yaml.safe_load", wraps=real_safe_load) as mock_load:
        fs._get_tilt_thresholds()
        fs._get_tilt_thresholds()
        fs._get_tilt_thresholds()
        assert mock_load.call_count == 1


def test_loader_returns_shoulder_and_hip_thresholds(tmp_path, monkeypatch) -> None:
    """shoulder + hip 각각 distinct tuple 반환."""
    from sunity_shared.analysis import force_signals as fs

    yaml_path = _write_valid_yaml(tmp_path)
    monkeypatch.setattr(fs, "_TILT_THRESHOLDS_PATH", yaml_path)
    fs._TILT_THRESHOLDS_CACHE = None

    shoulder, hip, _ = fs._get_tilt_thresholds()
    assert shoulder != hip  # _write_valid_yaml 가 distinct values 박제


def test_loader_fallback_warnings_in_cache_tuple_not_global(
    tmp_path, monkeypatch
) -> None:
    """W10 정합 — fallback 신호 는 cache tuple 의 3rd element. module-global flag 부재."""
    from sunity_shared.analysis import force_signals as fs

    missing = tmp_path / "absent.yaml"
    monkeypatch.setattr(fs, "_TILT_THRESHOLDS_PATH", missing)
    fs._TILT_THRESHOLDS_CACHE = None

    # 신규 module-level boolean flag 도입 금지 — 명시 검증.
    forbidden_flag_names = (
        "_TILT_THRESHOLDS_FALLBACK_FLAG",
        "_TILT_THRESHOLDS_FELL_BACK",
        "_tilt_thresholds_fallback",
        "_TILT_FALLBACK_SIGNAL",
    )
    for name in forbidden_flag_names:
        assert not hasattr(fs, name), f"module-global flag {name!r} 가 존재 — W10 위반"

    shoulder, hip, base_warnings = fs._get_tilt_thresholds()

    # fallback 신호 는 cache tuple 의 3rd element 단일 source.
    assert "tilt_thresholds_fallback" in base_warnings
    assert isinstance(fs._TILT_THRESHOLDS_CACHE, tuple)
    assert len(fs._TILT_THRESHOLDS_CACHE) == 3
    assert fs._TILT_THRESHOLDS_CACHE[2] == base_warnings
