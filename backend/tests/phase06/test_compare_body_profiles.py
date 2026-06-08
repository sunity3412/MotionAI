"""Task 4 (Part 2): compare_body_profiles 본체 (W1 used_reference_fallback + R8 extra_warnings + R2 source_keypoints)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.body_normalizer import (
    BODY_COMPARISON_WARNING_CODES,
    BodyComparisonReport,
    BodyComparisonSourcePose,
    compare_body_profiles,
)

from tests.phase06.fixtures._factory import (
    load_paired_frames,
    load_single_frames,
)


def _make_profile(**kw) -> BodyNormalizationProfile:
    defaults = dict(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.9,
        warnings=[],
    )
    defaults.update(kw)
    return BodyNormalizationProfile(**defaults)


def _frame_to_dict(frame) -> dict:
    return {n: (kp.x, kp.y, kp.z) for n, kp in frame.keypoints_3d.items()}


# ── Test 4: mode1 + reference + 안정 → 전체 report ───────────────────


def test_compare_body_profiles_mode1_returns_full_report() -> None:
    """mode1 + reference_profile + 안정 fixture → scale_profile != None,
    findings non-empty? body_normalization_confidence >= 0.5,
    used_reference_fallback=False."""
    pro_frames, student_frames = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_kp = _frame_to_dict(pro_frames[0])
    student_profile = _make_profile(
        estimated_height_scale=0.875, arm_scale=0.875, leg_scale=0.875,
        confidence=0.85,
    )
    pro_profile = _make_profile()

    report = compare_body_profiles(
        pose_frames=student_frames,
        student_profile=student_profile,
        reference_profile=pro_profile,
        comparison_type="mode1",
        source_keypoints=pro_kp,
        angles=None,
        technique_profile=None,
        reference_motion_id="ref-test",
        reference_athlete_name="정은지",
        target_torso_px=200.0,
    )
    assert report.comparison_type == "mode1"
    assert report.scale_profile is not None
    assert report.body_normalization_confidence >= 0.5
    assert report.used_reference_fallback is False
    assert report.reference_motion_id == "ref-test"
    assert report.reference_athlete_name == "정은지"


# ── Test 5: 저신뢰 fallback (mode3_first + no reference) ─────────────


def test_compare_body_profiles_low_confidence_fallback() -> None:
    """mode3_first + reference_profile=None + 불안정 → scale_profile=None +
    warnings ⊃ ['low_confidence_normalization_off']."""
    frames = load_single_frames("fixture_unstable_arm_swing")
    student_profile = _make_profile(confidence=0.85)
    report = compare_body_profiles(
        pose_frames=frames,
        student_profile=student_profile,
        reference_profile=None,
        comparison_type="mode3_first",
        source_keypoints=None,
        angles=None,
        technique_profile=None,
    )
    assert report.comparison_type == "mode3_first"
    assert report.scale_profile is None
    assert "low_confidence_normalization_off" in report.warnings
    # mode3_first + reference_profile=None 시 reference_profile_missing 은 emit 안 됨 (의도된 fallback)
    assert "reference_profile_missing" not in report.warnings
    # source_keypoints=None → R2 fix warning
    assert "reference_source_pose_missing" in report.warnings
    assert report.used_reference_fallback is False


# ── Test 6 (W1): mode3_first + Gemini fallback + boolean=True ────────


def test_compare_body_profiles_mode3_first_with_gemini_fallback_sets_boolean() -> None:
    """mode3_first + reference_profile (caller 전달) + confidence >= 0.5 +
    used_reference_fallback=True → comparisonType='mode3_first' 유지 + boolean=True."""
    _, student_frames = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_frames, _ = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_kp = _frame_to_dict(pro_frames[0])
    student_profile = _make_profile(
        estimated_height_scale=0.875, arm_scale=0.875, leg_scale=0.875,
        confidence=0.85,
    )
    pro_profile = _make_profile()

    report = compare_body_profiles(
        pose_frames=student_frames,
        student_profile=student_profile,
        reference_profile=pro_profile,
        comparison_type="mode3_first",
        source_keypoints=pro_kp,
        angles=None,
        technique_profile=None,
        reference_motion_id="ref-auto-matched",
        used_reference_fallback=True,
        target_torso_px=200.0,
    )
    assert report.comparison_type == "mode3_first"  # 4번째 케이스 금지 (W1)
    assert report.used_reference_fallback is True
    assert report.scale_profile is not None  # confidence >= 0.5 → 정규화 ON


# ── Test 7: mode3_progress 는 previous_analysis_id 필수 ──────────────


def test_compare_body_profiles_mode3_progress_requires_previous_id() -> None:
    """mode3_progress + previous_analysis_id=None → ValueError."""
    student_profile = _make_profile(confidence=0.85)
    with pytest.raises(ValueError, match="previous_analysis_id"):
        compare_body_profiles(
            pose_frames=None,
            student_profile=student_profile,
            reference_profile=None,
            comparison_type="mode3_progress",
            previous_analysis_id=None,
        )


# ── Test 10 (R8 fix): extra_warnings merge + validation ──────────────


def test_compare_body_profiles_merges_extra_warnings_with_validation() -> None:
    """compare_body_profiles(..., extra_warnings=['fallback_reference_not_found'])
    → report.warnings 가 내부 산출 + extra merge."""
    student_profile = _make_profile(confidence=0.85)
    report = compare_body_profiles(
        pose_frames=None,
        student_profile=student_profile,
        reference_profile=None,
        comparison_type="mode3_first",
        extra_warnings=["fallback_reference_not_found"],
    )
    assert "fallback_reference_not_found" in report.warnings
    # 모든 warnings 가 BODY_COMPARISON_WARNING_CODES frozen set 내
    for w in report.warnings:
        assert w in BODY_COMPARISON_WARNING_CODES, (
            f"warning '{w}' not in BODY_COMPARISON_WARNING_CODES"
        )


# ── Test 11 (R8 fix): invalid extra_warning → ValueError ────────────


def test_compare_body_profiles_rejects_invalid_extra_warning() -> None:
    """extra_warnings 에 유효하지 않은 코드 → ValueError. validation 우회 차단."""
    student_profile = _make_profile(confidence=0.85)
    with pytest.raises(ValueError, match="invalid extra_warning"):
        compare_body_profiles(
            pose_frames=None,
            student_profile=student_profile,
            reference_profile=None,
            comparison_type="mode3_first",
            extra_warnings=["not_a_valid_code"],
        )


# ── Test 12 (R2 fix): source_keypoints from BodyComparisonSourcePose ─


def test_compare_body_profiles_source_keypoints_from_body_comparison_source_pose() -> None:
    """caller 가 BodyComparisonSourcePose → to_keypoints_array() (J, 4) ndarray
    → compare_body_profiles 의 source_keypoints 인자로 전달.
    내부에서 normalize_pose_by_segments 까지 흘러가는지 검증."""
    _, student_frames = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_frames, _ = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_kp = pro_frames[0].keypoints_3d
    # KEYPOINT_NAMES 순서로 17 keypoint × 4 채널 flat values 생성
    from sunity_shared.analysis.skeleton import KEYPOINT_NAMES

    values = []
    for name in KEYPOINT_NAMES:
        kp = pro_kp[name]
        values.extend([kp.x, kp.y, kp.z, kp.confidence])
    source_pose = BodyComparisonSourcePose(
        joint_keys=KEYPOINT_NAMES,
        values=tuple(values),
        frame_index=0,
        torso_px=200.0,
        confidence=0.9,
        measured_at=1700000000000,
    )
    arr = source_pose.to_keypoints_array()
    assert arr.shape == (17, 4)

    student_profile = _make_profile(
        estimated_height_scale=0.875, arm_scale=0.875, leg_scale=0.875,
        confidence=0.85,
    )
    pro_profile = _make_profile()

    report = compare_body_profiles(
        pose_frames=student_frames,
        student_profile=student_profile,
        reference_profile=pro_profile,
        comparison_type="mode1",
        source_keypoints=arr,  # ndarray (17, 4)
        angles=None,
        technique_profile=None,
        reference_motion_id="ref-test",
        target_torso_px=200.0,
    )
    assert report.scale_profile is not None
    assert report.comparison_type == "mode1"
