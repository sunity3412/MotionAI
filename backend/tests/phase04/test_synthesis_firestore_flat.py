"""Phase 4 Wave 0 — POSE-03-e: Firestore synthesis meta flat 저장 검증.

[[firestore-nested-array-flat]] 정합 — synthesizedJoints 는 (T, J, 3) 형상을
flat list[float] + Frames(int) + JointKeys(list[str]) 3-필드 분해로 저장.
nested list 가 들어오면 _validate_flat_dict_no_nested_array 가 TypeError.

이 테스트는 Wave 0 시점부터 GREEN — firestore_admin._validate_flat_dict_no_nested_array
함수는 W5 (2026-06-08, Plan 06-02) 시점에 이미 박제됨.
"""

from __future__ import annotations

import pytest

try:
    from sunity_shared.firestore_admin import _validate_flat_dict_no_nested_array
except ImportError:
    pytest.skip(
        "_validate_flat_dict_no_nested_array not available — sunity_shared layer 미주입",
        allow_module_level=True,
    )


def test_ai_synthesis_meta_no_nested_array() -> None:
    """synthesizedJoints flat list[float] + Frames(int) + JointKeys(list[str]) 통과."""
    payload = {
        "synthesizedJoints": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "synthesizedJointsFrames": 1,
        "synthesizedJointsJointKeys": ["lShoulder", "rShoulder"],
    }

    # nested array 없으면 None 반환 (raise 안 함).
    result = _validate_flat_dict_no_nested_array(payload)

    assert result is None


def test_ai_synthesis_meta_nested_array_rejected() -> None:
    """synthesizedJoints 가 list[list[float]] 이면 TypeError."""
    payload = {
        "synthesizedJoints": [[1.0], [2.0]],
    }

    with pytest.raises(TypeError, match=r"nested list"):
        _validate_flat_dict_no_nested_array(payload)
