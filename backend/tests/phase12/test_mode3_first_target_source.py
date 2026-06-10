"""Phase 12 Wave 0A R4 (Codex 직접 리뷰 2026-06-10) — mode3 first targetSource 분리.

mode3 첫 분석 = `dimensions.extension_deviation(angles, profile)` 사용 path.
이 값은 "이전 영상/정은지 대비 편차" 아니라 IPSF 180° 신전 부족분.

  - extension-required joint (profile.expects_extension == True)
    → targetAngle = 180.0, targetSource = 'extension_requirement'
  - non-extension joint
    → targetAngle = None, targetSource = 'unavailable'

cite: 12-00-PLAN.md Task T3.
"""

from __future__ import annotations

from sunity_shared.analysis import dimensions
from sunity_shared.analysis.technique import (
    JOINT_BENT_OK,
    JOINT_EXTEND,
    TechniqueProfile,
)


def _make_profile(*, ext_joints: tuple[str, ...] = ("left_elbow", "right_knee")) -> TechniqueProfile:
    """profile.expects_extension 박제 fixture."""
    return TechniqueProfile(
        name="test",
        category="unknown",
        joint_expectations={
            "left_elbow": JOINT_EXTEND if "left_elbow" in ext_joints else JOINT_BENT_OK,
            "right_elbow": JOINT_EXTEND if "right_elbow" in ext_joints else JOINT_BENT_OK,
            "left_shoulder": JOINT_BENT_OK,
            "right_shoulder": JOINT_BENT_OK,
            "left_hip": JOINT_BENT_OK,
            "right_hip": JOINT_BENT_OK,
            "left_knee": JOINT_EXTEND if "left_knee" in ext_joints else JOINT_BENT_OK,
            "right_knee": JOINT_EXTEND if "right_knee" in ext_joints else JOINT_BENT_OK,
        },
    )


def test_extension_required_joint_target_180_extension_requirement():
    """expects_extension == True → (180.0, 'extension_requirement')."""
    profile = _make_profile(ext_joints=("left_elbow",))
    target, source = dimensions._target_source_for_extension("left_elbow", profile)
    assert target == 180.0
    assert source == "extension_requirement"


def test_non_extension_joint_target_none_unavailable():
    """expects_extension == False → (None, 'unavailable')."""
    profile = _make_profile(ext_joints=("left_elbow",))
    target, source = dimensions._target_source_for_extension("left_shoulder", profile)
    assert target is None
    assert source == "unavailable"


def test_right_knee_extension_required():
    """elbow 외 다른 신전 joint (knee) 도 동일 분기."""
    profile = _make_profile(ext_joints=("right_knee",))
    target, source = dimensions._target_source_for_extension("right_knee", profile)
    assert target == 180.0
    assert source == "extension_requirement"
    # 좌측 knee 는 ext 아님
    target_l, source_l = dimensions._target_source_for_extension("left_knee", profile)
    assert target_l is None
    assert source_l == "unavailable"
