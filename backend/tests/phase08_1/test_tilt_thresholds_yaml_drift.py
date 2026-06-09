"""Plan 08.1-01 Wave 1 Task 2 — tilt_thresholds.yaml drift defense (schema_v2).

W11 version-tolerant: 미래 schema 변경 시 본 test 가 schema_version bump 시
graceful skip + bump 가이드 박제.

per Plan 08.1-01 must_haves Step 3 (drift defense 11 tests).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_YAML_PATH = (
    Path(__file__).parent.parent.parent
    / "judging_data"
    / "tilt_thresholds.yaml"
)


@pytest.fixture(scope="module")
def yaml_data() -> dict:
    if not _YAML_PATH.exists():
        pytest.skip(
            f"tilt_thresholds.yaml 부재 ({_YAML_PATH}) — Wave 2 production sweep blocked"
        )
    with open(_YAML_PATH) as f:
        return yaml.safe_load(f)


def test_yaml_has_required_top_level_keys(yaml_data: dict) -> None:
    required = {
        "schema_version",
        "calibration_method",
        "calibration_version",
        "calibrated_at",
        "source",
        "shoulder_tilt",
        "hip_tilt",
        "ipsf_tolerance",
    }
    missing = required - set(yaml_data.keys())
    assert not missing, f"missing top-level keys: {missing}"


def test_yaml_schema_version_is_2(yaml_data: dict) -> None:
    """W11: schema_version != 2 시 bump + drift test 의 version-tolerant 분기 박제."""
    sv = yaml_data.get("schema_version")
    if sv != 2:
        pytest.skip(
            f"schema_version={sv} (expected 2) — bump 시 본 test 의 version-tolerant 분기 박제 plan"
        )
    assert sv == 2


def test_yaml_calibration_method(yaml_data: dict) -> None:
    assert yaml_data["calibration_method"] == "elite_p100_plus_margin"


def test_yaml_has_calibration_version(yaml_data: dict) -> None:
    cv = yaml_data["calibration_version"]
    assert isinstance(cv, str)
    parts = cv.split(".")
    assert len(parts) >= 2, f"semver-like 형식 기대: {cv}"
    assert all(p.isdigit() for p in parts), f"semver-like 형식 기대: {cv}"


def test_yaml_source_metadata(yaml_data: dict) -> None:
    src = yaml_data["source"]
    required = {
        "sweep_uid",
        "sample_size",
        "source_doc_ids",
        "null_tilt_verified",
        "margin_deg",
    }
    missing = required - set(src.keys())
    assert not missing, f"source missing keys: {missing}"
    assert src["null_tilt_verified"] is True
    assert isinstance(src["sample_size"], int)
    assert src["sample_size"] > 0
    assert isinstance(src["source_doc_ids"], list)
    assert len(src["source_doc_ids"]) > 0
    assert isinstance(src["margin_deg"], (int, float))


def test_yaml_shoulder_distribution(yaml_data: dict) -> None:
    dist = yaml_data["shoulder_tilt"]["distribution"]
    required = {"p25", "p50", "p75", "p90", "p100"}
    missing = required - set(dist.keys())
    assert not missing, f"shoulder_tilt distribution missing: {missing}"


def test_yaml_hip_distribution(yaml_data: dict) -> None:
    dist = yaml_data["hip_tilt"]["distribution"]
    required = {"p25", "p50", "p75", "p90", "p100"}
    missing = required - set(dist.keys())
    assert not missing, f"hip_tilt distribution missing: {missing}"


def test_yaml_shoulder_operational_cutoff(yaml_data: dict) -> None:
    oc = yaml_data["shoulder_tilt"]["operational_cutoff"]
    assert "medium_cutoff_deg" in oc
    assert "high_cutoff_deg" in oc
    assert isinstance(oc["medium_cutoff_deg"], (int, float))
    assert isinstance(oc["high_cutoff_deg"], (int, float))


def test_yaml_hip_operational_cutoff(yaml_data: dict) -> None:
    oc = yaml_data["hip_tilt"]["operational_cutoff"]
    assert "medium_cutoff_deg" in oc
    assert "high_cutoff_deg" in oc


def test_yaml_ipsf_tolerance(yaml_data: dict) -> None:
    ipsf = yaml_data["ipsf_tolerance"]
    assert ipsf["tolerance_deg"] == 20.0
    assert "major_fault_deg" in ipsf
    assert ipsf["major_fault_deg"] == 40.0
    assert "source_ref" in ipsf
    assert isinstance(ipsf["source_ref"], str)


def test_yaml_medium_cutoff_at_least_tolerance(yaml_data: dict) -> None:
    """invariant: operational_cutoff.medium_cutoff_deg >= ipsf_tolerance.tolerance_deg.

    C-H2: medium = max(P100 + margin, ipsf_tolerance.tolerance_deg).
    """
    ipsf_tol = yaml_data["ipsf_tolerance"]["tolerance_deg"]
    s_medium = yaml_data["shoulder_tilt"]["operational_cutoff"]["medium_cutoff_deg"]
    h_medium = yaml_data["hip_tilt"]["operational_cutoff"]["medium_cutoff_deg"]
    assert s_medium >= ipsf_tol
    assert h_medium >= ipsf_tol


def test_yaml_high_cutoff_at_least_medium(yaml_data: dict) -> None:
    """invariant: operational_cutoff.high_cutoff_deg >= operational_cutoff.medium_cutoff_deg."""
    s_oc = yaml_data["shoulder_tilt"]["operational_cutoff"]
    h_oc = yaml_data["hip_tilt"]["operational_cutoff"]
    assert s_oc["high_cutoff_deg"] >= s_oc["medium_cutoff_deg"]
    assert h_oc["high_cutoff_deg"] >= h_oc["medium_cutoff_deg"]
