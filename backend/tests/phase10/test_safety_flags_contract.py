"""Phase 10 Wave 0 — SafetyFlag Firestore contract guard (scalar-only).

`_validate_safety_flags` 는 10-02 에서 firestore_admin.py 에 추가된다. 본 파일은
지금 COLLECT 되어야 하므로 validator import 는 테스트 함수 안에서 lazy 로 한다
(module-top import 금지 — 아직 없음). 검증 동작 테스트는 xfail(strict=True) —
not-yet-existing 함수의 positive 동작이라 stub 상태에서 실패 → 10-02 에서 flip.

per Plan 10-01 Task 3 (T-10-01 nested-array 방어).
"""

from __future__ import annotations

import pytest


def _load_validator():
    """10-02 에서 추가될 firestore_admin._validate_safety_flags 를 lazy 로 로드."""
    from sunity_shared import firestore_admin

    return firestore_admin._validate_safety_flags  # type: ignore[attr-defined]


def _scalar_flag_dict() -> dict:
    return {
        "flagType": "trunk_hyperextension",
        "bodyRegion": "허리",
        "severity": "medium",
        "confidence": "low",
        "modeScope": "both",
        "postureCondition": "trunk reverse-bend in hold",
        "controlLossSignal": "left_hip instability medium",
    }


def test_validator_accepts_scalar_only_flag() -> None:
    validate = _load_validator()
    # scalar-only flag dict 는 통과해야 한다 (예외 없음).
    validate([_scalar_flag_dict()])


def test_validator_rejects_nested_list_flag() -> None:
    validate = _load_validator()
    bad = _scalar_flag_dict()
    bad["causes"] = ["a", "b"]  # nested array — Firestore 금지
    with pytest.raises(Exception):
        validate([bad])
