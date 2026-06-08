"""Task 3: bodyNormalizationConfidence 산식 + foreshortening 검출 + temporal variance + spatial dispersion (R5 fix + R6 fix)."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.body_normalizer import (
    DISPERSION_BASELINE,
    DISPERSION_RANGE,
    _compute_spatial_dispersion,
    compute_body_normalization_confidence,
    is_foreshortening_detected,
)
from sunity_shared.analysis.pose_frame import (
    Keypoint3D,
    Keypoint3DAligned,
    PoseFrame,
    to_coco17_array,
)

from tests.phase06.fixtures._factory import (
    load_paired_frames,
    load_single_frames,
)


def _make_profile(
    *,
    confidence: float = 0.9,
    warnings: list | None = None,
) -> BodyNormalizationProfile:
    return BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=confidence,
        warnings=warnings if warnings is not None else [],
    )


# ── Test 1: foreshortening lying pose → True + warning ────────────────


def test_foreshortening_lying_pose_disables_width_correction() -> None:
    """fixture_foreshortening_lying_pose → is_foreshortening_detected=True."""
    frames = load_single_frames("fixture_foreshortening_lying_pose")
    assert is_foreshortening_detected(frames) is True


# ── Test 2: unstable arm swing → confidence < 0.5 ─────────────────────


def test_unstable_arm_swing_lowers_confidence_below_threshold() -> None:
    """fixture_unstable_arm_swing → temporal variance > 10% → confidence < 0.5."""
    frames = load_single_frames("fixture_unstable_arm_swing")
    student_profile = _make_profile(confidence=0.85)
    conf, warnings = compute_body_normalization_confidence(
        frames, student_profile, reference_profile=None, comparison_type="mode1"
    )
    # base 0.85 - 0.5*temporal_penalty(1.0) = 0.35 < 0.5
    assert conf < 0.5, f"unstable arm swing confidence {conf:.3f} < 0.5 필요"
    assert "temporal_variance_high" in warnings


# ── Test 3: stable pose → confidence >= 0.5 ───────────────────────────


def test_stable_pose_confidence_above_threshold() -> None:
    """fixture_160cm_pro_vs_140cm_student.student_frames (안정) → confidence >= 0.5."""
    _, student_frames = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    student_profile = _make_profile(confidence=0.85)
    # comparison_type=mode1 + reference_profile=None 시
    # reference_profile_missing warning 이 emit 되므로,
    # 본 test 는 mode3_first 로 호출 (warning 없는 fallback path).
    conf, warnings = compute_body_normalization_confidence(
        student_frames,
        student_profile,
        reference_profile=None,
        comparison_type="mode3_first",
    )
    assert conf >= 0.5, f"stable pose confidence {conf:.3f} >= 0.5 필요"
    assert "temporal_variance_high" not in warnings
    assert "spatial_dispersion_high" not in warnings


# ── Test 4: confidence clamp [0.0, 1.0] ────────────────────────────────


def test_confidence_clamped_to_unit_interval() -> None:
    """극단 입력 시 confidence ∈ [0.0, 1.0]."""
    profile_hi = _make_profile(confidence=1.0)
    ref_hi = _make_profile(confidence=1.0)
    conf, _ = compute_body_normalization_confidence(
        None, profile_hi, ref_hi, "mode1"
    )
    assert 0.0 <= conf <= 1.0

    profile_lo = _make_profile(confidence=0.0)
    conf, _ = compute_body_normalization_confidence(
        None, profile_lo, None, "mode3_first"
    )
    assert 0.0 <= conf <= 1.0


# ── Test 5: reference_profile_missing warning + 하향 ────────────────


def test_reference_profile_missing_emits_warning() -> None:
    """reference_profile=None + comparison_type != 'mode3_first' → warning."""
    profile = _make_profile(confidence=0.85)
    conf_with_ref, warnings_with_ref = compute_body_normalization_confidence(
        None, profile, _make_profile(confidence=0.9), "mode1"
    )
    conf_no_ref, warnings_no_ref = compute_body_normalization_confidence(
        None, profile, None, "mode1"
    )
    assert "reference_profile_missing" in warnings_no_ref
    assert "reference_profile_missing" not in warnings_with_ref
    # bonus 없음 → conf_no_ref < conf_with_ref
    assert conf_no_ref < conf_with_ref


# ── Test 6: pose_frames=None graceful ────────────────────────────────


def test_confidence_handles_none_pose_frames_gracefully() -> None:
    """pose_frames=None → temporal_penalty = spatial_dispersion_penalty = 0."""
    profile = _make_profile(confidence=0.7)
    conf, warnings = compute_body_normalization_confidence(
        None, profile, None, "mode3_first"
    )
    # base 0.7 + reference_match_bonus (0) - 0 - 0 = 0.7
    assert abs(conf - 0.7) < 1e-6, f"None pose_frames base 보존 — got {conf}"
    assert "temporal_variance_high" not in warnings
    assert "spatial_dispersion_high" not in warnings


# ── Test 7 (R5 fix): high dispersion → high penalty ──────────────────


def test_high_dispersion_arms_sprawled_increases_penalty() -> None:
    """fixture_high_dispersion_arms_sprawled → spatial_dispersion_penalty ~= 1.0."""
    frames = load_single_frames("fixture_high_dispersion_arms_sprawled")
    dispersion_ratio = _compute_spatial_dispersion(frames)
    expected_penalty = max(
        0.0,
        min(1.0, (dispersion_ratio - DISPERSION_BASELINE) / DISPERSION_RANGE),
    )
    assert expected_penalty >= 0.99, (
        f"high dispersion ratio = {dispersion_ratio:.2f} → penalty "
        f"{expected_penalty:.3f}, expected ~1.0"
    )

    student_profile = _make_profile(confidence=0.85)
    conf, warnings = compute_body_normalization_confidence(
        frames, student_profile, None, "mode3_first"
    )
    assert "spatial_dispersion_high" in warnings

    # confidence 가 stable pose 대비 명확히 낮음
    _, stable = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    stable_conf, _ = compute_body_normalization_confidence(
        stable, student_profile, None, "mode3_first"
    )
    assert conf < stable_conf, (
        f"high_dispersion conf {conf:.3f} < stable conf {stable_conf:.3f} 필요"
    )


# ── Test 8 (R6 fix): to_coco17_array 4채널 보존 ─────────────────────


def test_to_coco17_array_preserves_confidence_channel() -> None:
    """to_coco17_array 결과 (T,17,4) 의 [:,:,3] 가 입력 uncertainty_proxy 보존."""
    # 합성 PoseFrame 3 frame, uncertainty_proxy 변동 (0.2, 0.5, 0.8)
    frames: list[PoseFrame] = []
    for i, up in enumerate([0.2, 0.5, 0.8]):
        kp3d = {
            "nose": Keypoint3D(x=100.0, y=100.0, z=0.0, confidence=1.0 - up, uncertainty_proxy=up)
        }
        kp_aligned = {"nose": Keypoint3DAligned(x=100.0, y=100.0, z=0.0)}
        frames.append(
            PoseFrame(
                frame_index=i,
                timestamp_ms=i * 33,
                keypoints_3d=kp3d,
                keypoints_3d_pole_aligned=kp_aligned,
                reliability="high",
            )
        )
    arr = to_coco17_array(frames)
    assert arr.shape == (3, 17, 4)
    # nose 는 KEYPOINT_NAMES 의 0번 인덱스
    assert abs(arr[0, 0, 3] - 0.2) < 1e-4
    assert abs(arr[1, 0, 3] - 0.5) < 1e-4
    assert abs(arr[2, 0, 3] - 0.8) < 1e-4


# ── Test 9 (R6 fix): compute_body_normalization_confidence 가 to_coco17_array 사용 ──


def test_compute_body_normalization_confidence_uses_to_coco17_array() -> None:
    """to_coco17_array 가 confidence 산출 path 에서 호출되는지 monkeypatch 검증."""
    frames = load_single_frames("fixture_high_dispersion_arms_sprawled")
    profile = _make_profile(confidence=0.85)

    call_count = {"n": 0}
    orig = to_coco17_array

    def _spy(pose_frames):
        call_count["n"] += 1
        return orig(pose_frames)

    with patch(
        "sunity_shared.analysis.body_normalizer.to_coco17_array", side_effect=_spy
    ):
        compute_body_normalization_confidence(
            frames, profile, None, "mode3_first"
        )

    assert call_count["n"] >= 1, (
        f"to_coco17_array 가 confidence path 에서 호출되어야 함 "
        f"(R6 fix). 실제 call count = {call_count['n']}"
    )
