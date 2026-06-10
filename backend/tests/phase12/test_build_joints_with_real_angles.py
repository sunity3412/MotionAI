"""Phase 12 Wave 0B (Plan 12-01) — assemble.build_joints 의 실 각도 채움 검증.

assemble.build_joints(assessments) 가 모든 8 joint 의 currentAngle + targetAngle
채움 (mock JointAssessment 입력). 4 joint 만 채움 케이스에서 4 joint 만 박제 +
나머지 currentAngle/targetAngle key 누락 (Phase 12 Wave 0A 회귀 0 검증).
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis import assemble, kismam
from sunity_shared.analysis.skeleton import JOINT_KEYS


def test_build_joints_all_eight_filled() -> None:
    """모든 8 joint 에 user_angles + reference_angles 박제 시 currentAngle/targetAngle 채움."""
    n = len(JOINT_KEYS)
    deviation = np.zeros(n, dtype=float)
    user_means = {key: 150.0 for key in JOINT_KEYS}
    ref_means = {key: 170.0 for key in JOINT_KEYS}
    assessments = kismam.assess(
        deviation,
        user_angles=user_means,
        reference_angles=ref_means,
        target_source="reference_motion",
    )
    joints = assemble.build_joints(assessments)
    assert len(joints) == 8
    for j in joints:
        assert "currentAngle" in j, (
            f"joint {j['key']} 누락 currentAngle (Phase 12 R4 회귀)"
        )
        assert "targetAngle" in j, (
            f"joint {j['key']} 누락 targetAngle (Phase 12 R4 회귀)"
        )
        # 150 vs 170 → delta = -20 (extend 방향).
        assert j["currentAngle"] == 150.0
        assert j["targetAngle"] == 170.0
        assert j["deltaDeg"] == -20.0
        assert j.get("targetSource") == "reference_motion"


def test_build_joints_partial_extension_targets() -> None:
    """4 joint 만 reference_angles 박제 (mode3 first extension_requirement) →
    그 4 만 currentAngle/targetAngle 박제 + 나머지 4 는 키 누락.
    """
    n = len(JOINT_KEYS)
    deviation = np.zeros(n, dtype=float)
    user_means = {key: 150.0 for key in JOINT_KEYS}
    # 4 joint 만 IPSF 180° target 박제.
    ext_targets = {
        "left_elbow": 180.0,
        "right_elbow": 180.0,
        "left_knee": 180.0,
        "right_knee": 180.0,
    }
    assessments = kismam.assess(
        deviation,
        user_angles=user_means,
        reference_angles=ext_targets,
        target_source="extension_requirement",
    )
    joints = assemble.build_joints(assessments)

    extension_keys = set(ext_targets.keys())
    for j in joints:
        if j["key"] in extension_keys:
            assert "currentAngle" in j
            assert "targetAngle" in j
            assert j["targetAngle"] == 180.0
            assert j.get("targetSource") == "extension_requirement"
        else:
            # non-extension joint → currentAngle/targetAngle key 누락.
            assert "currentAngle" not in j, (
                f"non-extension joint {j['key']} 에 currentAngle 박제 — 회귀"
            )
            assert "targetAngle" not in j, (
                f"non-extension joint {j['key']} 에 targetAngle 박제 — 회귀"
            )
            # target_source 만 'unavailable' 박제.
            assert j.get("targetSource") == "unavailable"


def test_build_joints_no_user_no_reference_keeps_legacy() -> None:
    """legacy caller (user_angles/reference_angles 둘 다 None) → currentAngle 키 누락 (이전 동작 유지)."""
    n = len(JOINT_KEYS)
    deviation = np.zeros(n, dtype=float)
    assessments = kismam.assess(deviation)  # legacy — kwarg 없음
    joints = assemble.build_joints(assessments)
    for j in joints:
        assert "currentAngle" not in j
        assert "targetAngle" not in j
        # target_source 도 None (kismam.assess legacy).
        assert "targetSource" not in j


def test_build_joints_returns_eight_joints() -> None:
    """build_joints 반환은 항상 8 joint (JOINT_KEYS = COCO body 8)."""
    n = len(JOINT_KEYS)
    deviation = np.zeros(n, dtype=float)
    assessments = kismam.assess(deviation)
    joints = assemble.build_joints(assessments)
    assert len(joints) == 8
    keys = [j["key"] for j in joints]
    assert set(keys) == set(JOINT_KEYS)
