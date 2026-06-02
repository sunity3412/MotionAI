"""RTMW weights manifest schema + license gate 강제 검증 (Plan 01-20 Task 1).

Plan path: .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-20-PLAN.md
Audit doc: docs/licenses/rtmw-weights-audit.md

본 테스트는 weights_manifest.json 의 schema 무결성과 license gate 의 hard
constraint 를 강제한다. 핵심:

- production_eligible=true 인 entry 는 license_status='commercial_ok' 필수
  (audit 우회 차단 — Plan 01-20 T-20-01 mitigation).
- 차단 목록 (memory license-blocklist-pose.md) 의 alphapose/nlf/smplx/videopose3d
  부분문자열은 weight name 에 0 건.
- license_status enum: commercial_ok / restricted / unknown.

belle 검토 (Task 2 checkpoint) 통과 전 모든 entry production_eligible=false 유지 —
plan 21 진입 차단.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "pose_engines"
    / "rtmw"
    / "weights_manifest.json"
)

ALLOWED_LICENSE_STATUSES = {"commercial_ok", "restricted", "unknown"}

REQUIRED_TOPLEVEL_KEYS = {"manifest_version", "audit_date", "weights"}
REQUIRED_WEIGHT_KEYS = {
    "name",
    "url",
    "sha256",
    "training_data",
    "license_status",
    "production_eligible",
    "source_audit_ref",
}

BLOCKLISTED_SUBSTRINGS = ("alphapose", "nlf", "smplx", "videopose3d")


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.exists(), (
        f"weights_manifest.json 없음: {MANIFEST_PATH}. Plan 01-20 Task 1 산출 누락."
    )
    with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_manifest_loads_as_valid_json(manifest: dict) -> None:
    """weights_manifest.json 가 valid JSON 으로 로드된다."""
    assert isinstance(manifest, dict)


def test_manifest_required_keys(manifest: dict) -> None:
    """최상위 schema = {manifest_version, audit_date, weights} 모두 존재."""
    missing = REQUIRED_TOPLEVEL_KEYS - set(manifest.keys())
    assert not missing, f"최상위 키 누락: {missing}"
    assert isinstance(manifest["weights"], list)


def test_each_weight_required_keys(manifest: dict) -> None:
    """각 weight entry 가 필수 schema 키 (name, url, sha256, training_data,
    license_status, production_eligible, source_audit_ref) 모두 보유."""
    for idx, entry in enumerate(manifest["weights"]):
        assert isinstance(entry, dict), f"entry[{idx}] dict 아님"
        missing = REQUIRED_WEIGHT_KEYS - set(entry.keys())
        assert not missing, (
            f"entry[{idx}] ({entry.get('name', '?')}) 필수 키 누락: {missing}"
        )


def test_license_status_enum(manifest: dict) -> None:
    """license_status ∈ {commercial_ok, restricted, unknown}."""
    for entry in manifest["weights"]:
        status = entry["license_status"]
        assert status in ALLOWED_LICENSE_STATUSES, (
            f"entry '{entry['name']}' license_status={status!r} 는 enum "
            f"({sorted(ALLOWED_LICENSE_STATUSES)}) 위반"
        )


def test_production_eligible_implies_commercial_ok(manifest: dict) -> None:
    """**hard gate**: production_eligible=true 인 entry 는 license_status='commercial_ok' 필수.

    belle 가 license_status='restricted' 또는 'unknown' 인 가중치를 production
    승급 시도 시 본 테스트가 실패해야 함. T-20-01 (audit 우회 tampering) 차단.
    """
    for entry in manifest["weights"]:
        if entry["production_eligible"] is True:
            assert entry["license_status"] == "commercial_ok", (
                f"entry '{entry['name']}' production_eligible=true 인데 "
                f"license_status={entry['license_status']!r}. "
                "production 승급 전 license_status='commercial_ok' 로 갱신 필요 "
                "(audit doc §4 박제 + belle 결정 commit 함께)."
            )


def test_at_least_one_candidate_weight(manifest: dict) -> None:
    """weights 배열 길이 ≥ 1. Plan 01-20 acceptance criteria ≥ 4 별도 확인."""
    assert len(manifest["weights"]) >= 1, "weights 배열이 비어있음"


def test_no_blocklisted_weights(manifest: dict) -> None:
    """memory license-blocklist-pose.md 차단 모델 (alphapose/nlf/smplx/videopose3d)
    부분문자열이 weight name 에 0 건."""
    violations = []
    for entry in manifest["weights"]:
        name_lower = entry["name"].lower()
        for blocked in BLOCKLISTED_SUBSTRINGS:
            if blocked in name_lower:
                violations.append((entry["name"], blocked))
    assert not violations, (
        f"차단 목록 위반: {violations}. memory license-blocklist-pose.md 참조."
    )
