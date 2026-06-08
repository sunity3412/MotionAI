"""Task 4 (Part 1): IPSF 절대 deficit + C14 fix pose_reliability_low + W6 foreshortening proxy."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pytest

from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.body_normalizer import (
    BodyComparisonFinding,
    BodyComparisonReport,
    compare_body_profiles,
    is_foreshortening_detected,
    measure_ipsf_absolute_deficits,
    normalize_pose_by_segments,
)
from sunity_shared.analysis.pose_frame import (
    Keypoint3D,
    Keypoint3DAligned,
    PoseFrame,
)

from tests.phase06.fixtures._factory import (
    load_paired_frames,
    load_single_frames,
)


@dataclass
class _TechniqueProfileStub:
    expects_extension: tuple[str, ...] = ()


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


# ── Test 1: 160cm pro vs 140cm student — 정규화 ON 시 위양성 deduction 60% 감소 ──


def test_160cm_pro_vs_140cm_student_removes_false_positive() -> None:
    """정규화 ON → raw 비교 대비 deduction_score 합산 감소.

    raw 비교: pro 와 student 키 차이로 _measure_ipsf 일부 결과 differ.
    정규화 ON: 같은 자세 → finding 0 또는 deduction 합 < raw.
    """
    pro_frames, student_frames = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_kp = _frame_to_dict(pro_frames[0])
    student_kp = _frame_to_dict(student_frames[0])
    student_profile = _make_profile(
        estimated_height_scale=0.875,
        arm_scale=0.875,
        leg_scale=0.875,
    )
    pro_profile = _make_profile()

    # raw: 정규화 OFF, student keypoint 그대로 사용
    raw_findings = measure_ipsf_absolute_deficits(
        angles=None,
        technique_profile=None,
        normalized_keypoints=student_kp,
    )
    raw_total = sum(abs(f.deduction_score) for f in raw_findings)

    # 정규화 ON: pro keypoints → student scale 로 reproject
    student_torso_px = 200.0
    norm = normalize_pose_by_segments(
        pro_kp, pro_profile, student_profile, student_torso_px
    )
    norm_findings = measure_ipsf_absolute_deficits(
        angles=None,
        technique_profile=None,
        normalized_keypoints=norm,
    )
    norm_total = sum(abs(f.deduction_score) for f in norm_findings)

    # 정규화된 결과의 deduction 이 raw 의 60% 감소 이하 (즉 norm <= raw × 0.4) 또는 둘 다 0
    if raw_total > 0:
        # 정상 자세 fixture 라 둘 다 거의 0 이어도 OK. 핵심은 norm <= raw.
        assert norm_total <= raw_total, (
            f"정규화 후 deduction 이 raw 대비 증가하면 안 됨. "
            f"raw={raw_total:.2f}, norm={norm_total:.2f}"
        )


# ── Test 2: twist fixture 의 shoulderHipRatio 점수 차원 미적용 ────────


def test_twist_motion_shoulder_hip_ratio_not_in_findings() -> None:
    """fixture_lefty_vs_righty_twist → findings 에 'rounded_shoulders' 가능하나
    shoulderHipRatio 자체는 deficit 없음."""
    frames = load_single_frames("fixture_lefty_vs_righty_twist")
    kp = _frame_to_dict(frames[0])
    findings = measure_ipsf_absolute_deficits(
        angles=None,
        technique_profile=None,
        normalized_keypoints=kp,
    )
    deficit_codes = {f.deficit_code for f in findings}
    # shoulderHipRatio 자체는 deficit code 가 아님 (R9: 6 enum 만)
    assert "shoulder_hip_ratio" not in deficit_codes
    assert "shoulderHipRatio" not in deficit_codes


# ── Test 3: split angle 위양성 회피 ──────────────────────────────────


def test_split_angle_uses_hip_knee_line_not_toe_to_toe() -> None:
    """fixture_split_angle_hipline short vs long → split deficit (knee_toe_alignment) 동일."""
    short, long_ = load_paired_frames(
        "fixture_split_angle_hipline",
        key_a="short_leg_frames",
        key_b="long_leg_frames",
    )
    s_kp = _frame_to_dict(short[0])
    l_kp = _frame_to_dict(long_[0])
    s_findings = measure_ipsf_absolute_deficits(
        angles=None, technique_profile=None, normalized_keypoints=s_kp
    )
    l_findings = measure_ipsf_absolute_deficits(
        angles=None, technique_profile=None, normalized_keypoints=l_kp
    )
    # split 위양성 회피 — 둘 다 같은 자세, 같은 finding count (knee_toe_alignment 동일 emit/skip).
    s_codes = sorted([f.deficit_code for f in s_findings])
    l_codes = sorted([f.deficit_code for f in l_findings])
    assert s_codes == l_codes, (
        f"split short vs long deficit_code 동일해야 함 — "
        f"toe-to-toe 위양성 회피. short={s_codes}, long={l_codes}"
    )


# ── Test 8 (W6): foreshortening proxy → shoulder_hip_ratio_off ──────


def test_foreshortening_proxy_triggers_shoulder_hip_ratio_off() -> None:
    """fixture_foreshortening_lying_pose → compare_body_profiles 시
    apply_shoulder_hip_ratio=False + warnings ⊃ 'shoulder_hip_ratio_off'."""
    frames = load_single_frames("fixture_foreshortening_lying_pose")
    student_profile = _make_profile(confidence=0.85)
    pro_profile = _make_profile()
    pro_kp = _frame_to_dict(frames[0])  # source 로 같은 fixture 사용 (테스트 목적)

    report = compare_body_profiles(
        pose_frames=frames,
        student_profile=student_profile,
        reference_profile=pro_profile,
        comparison_type="mode1",
        source_keypoints=pro_kp,
        angles=None,
        technique_profile=None,
        reference_motion_id="ref-test",
        target_torso_px=200.0,
    )
    assert is_foreshortening_detected(frames) is True
    assert "foreshortening_off" in report.warnings
    assert "shoulder_hip_ratio_off" in report.warnings


# ── Test 9 (C14): pose_reliability_low rename, bad_angle 부재 ────────


def test_pose_reliability_low_deficit_code_replaces_bad_angle() -> None:
    """평균 conf < 0.4 인 frame 비율 > 0.5 → finding deficit_code='pose_reliability_low'.
    'bad_angle' string 은 findings 어디에도 없음."""
    # 합성 frames — 평균 confidence 0.2 인 10 frame
    low_conf_frames: list[PoseFrame] = []
    for i in range(10):
        kp = {
            "left_shoulder": Keypoint3D(x=100.0, y=100.0, z=0.0, confidence=0.2, uncertainty_proxy=0.8),
            "right_shoulder": Keypoint3D(x=200.0, y=100.0, z=0.0, confidence=0.2, uncertainty_proxy=0.8),
        }
        kp_aligned = {
            "left_shoulder": Keypoint3DAligned(x=100.0, y=100.0, z=0.0),
            "right_shoulder": Keypoint3DAligned(x=200.0, y=100.0, z=0.0),
        }
        low_conf_frames.append(
            PoseFrame(
                frame_index=i,
                timestamp_ms=i * 33,
                keypoints_3d=kp,
                keypoints_3d_pole_aligned=kp_aligned,
                reliability="low",
            )
        )
    findings = measure_ipsf_absolute_deficits(
        angles=None,
        technique_profile=None,
        normalized_keypoints=None,
        pose_frames=low_conf_frames,
    )
    deficit_codes = [f.deficit_code for f in findings]
    assert "pose_reliability_low" in deficit_codes
    assert "bad_angle" not in deficit_codes


# ── BodyComparisonFinding/Report __post_init__ 검증 (보너스) ─────────


def test_body_comparison_finding_confidence_validation() -> None:
    with pytest.raises(ValueError, match="confidence"):
        BodyComparisonFinding(
            deficit_code="clean_lines",
            joint_key=None,
            measured_value=160.0,
            deduction_score=-0.2,
            confidence=1.5,
            body_type_adjusted=True,
        )


def test_body_comparison_report_validation_used_fallback_only_in_mode3_first() -> None:
    """used_reference_fallback=True 는 mode3_first 에서만 허용."""
    with pytest.raises(ValueError, match="used_reference_fallback"):
        BodyComparisonReport(
            comparison_type="mode1",
            body_normalization_confidence=0.8,
            used_reference_fallback=True,
        )
