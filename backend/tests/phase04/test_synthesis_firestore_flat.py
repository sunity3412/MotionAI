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


# ── Plan 04-01 Wave 1 (R3 fix + BLOCKER-4) — joints3d 전용 validator 테스트 ──


def _load_joints3d_validator():
    """joints3d 전용 validator — Wave 1 (04-01 Task 2) 박제 위치 lazy import."""
    try:
        from sunity_shared.firestore_admin import _validate_joints3d_payload
    except ImportError:
        pytest.skip(
            "_validate_joints3d_payload — Wave 1 (04-01 Task 2) 미박제"
        )
    return _validate_joints3d_payload


def test_joints3d_flat_no_nested_array() -> None:
    """joints3d flat list[float] + frames + 17 keys + coord_dim=3 + valid space → 통과."""
    validator = _load_joints3d_validator()
    frames = 2
    keys = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle",
    ]
    coord_dim = 3
    joints3d = [0.0] * (frames * len(keys) * coord_dim)
    validator(joints3d, keys, frames, coord_dim, "pole_aligned")
    # raise 없이 완료하면 통과.


def test_joints3d_nested_rejected() -> None:
    """joints3d 가 nested list 이면 TypeError."""
    validator = _load_joints3d_validator()
    frames = 1
    keys = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle",
    ]
    # nested list — 첫 원소가 [0.0] 인 nested 형태.
    joints3d_bad: list = [[0.0]] * (frames * len(keys) * 3)
    with pytest.raises(TypeError, match=r"nested list"):
        validator(joints3d_bad, keys, frames, 3, "pole_aligned")


def test_joints3d_invalid_space_rejected() -> None:
    """space 가 허용 set 밖이면 ValueError."""
    validator = _load_joints3d_validator()
    keys = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle",
    ]
    joints3d = [0.0] * (1 * len(keys) * 3)
    with pytest.raises(ValueError, match=r"space"):
        validator(joints3d, keys, 1, 3, "image_2d")


def test_joints3d_length_mismatch_rejected() -> None:
    """flat length != frames * keys * coord_dim 이면 ValueError."""
    validator = _load_joints3d_validator()
    keys = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle",
    ]
    joints3d = [0.0, 0.0]  # 길이 2 (expected = 1*17*3=51)
    with pytest.raises(ValueError, match=r"length"):
        validator(joints3d, keys, 1, 3, "pole_aligned")
