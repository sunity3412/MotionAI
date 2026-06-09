"""Plan 08-02 Task 2 — compute_axis_deviation 단위 test (REVIEWS R1/R2).

R1: point_to_pole_line_distance_2d 사용 강제 (Plan 08-00 contract)
R2: median_torso_length denominator + BodyNormalizationProfile import 영구 차단
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis.force_signals import (
    AxisDeviationMetric,
    PhaseBoundary,
    compute_axis_deviation,
    compute_phase_boundaries,
)

from .fixtures._factory import make_pole_axis_measurement
from .fixtures._fixture_builders import build_clean_invert, build_pelvis_drop


def _angles(n: int) -> np.ndarray:
    return np.full((n, 8), 90.0, dtype=float)


def _hold_boundary(start: int, end: int) -> PhaseBoundary:
    """단일 hold phase 박제 — axis test 의 minimal 입력."""
    return PhaseBoundary(
        phase="hold",
        start_frame_idx=start,
        end_frame_idx=end,
        start_ms=start * 111,
        end_ms=end * 111,
        confidence="low",
        source="heuristic",
        preflight_label_gate_passed=None,
    )


def test_pelvis_distance_uses_observed_torso_length_denominator():
    """pelvis distance = raw_distance / median_torso_length(image_2d).

    build_clean_invert: shoulder y=0.30, hip y=0.60 → torso_length ≈ 0.30.
    pelvis (hip midpoint x=0.5, y=0.6) → pole (x=0.5 vertical) 거리 = 0.0.
    """
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_hold_boundary(0, 60)]
    metrics = compute_axis_deviation(frames, boundaries, pole)
    assert len(metrics) == 1
    m = metrics[0]
    assert m.pelvis_distance_from_pole_axis is not None
    # pelvis ≈ on the pole → distance ≈ 0 / 0.30 ≈ 0.0.
    assert m.pelvis_distance_from_pole_axis < 0.02
    assert m.scale_denominator == "observed_torso_length"
    assert m.coordinate_space == "image_2d"


def test_chest_distance_uses_observed_torso_length_denominator():
    """chest distance = shoulder midpoint → pole line."""
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_hold_boundary(0, 60)]
    metrics = compute_axis_deviation(frames, boundaries, pole)
    m = metrics[0]
    assert m.chest_distance_from_pole_axis is not None
    assert m.chest_distance_from_pole_axis < 0.02


def test_line_missing_returns_null_distance_with_warning():
    """pole_axis_measurement.line=None → distance None + warning 'pole_line_missing'."""
    frames, _, _, _ = build_clean_invert()
    pole_no_line = make_pole_axis_measurement(line=None)
    boundaries = [_hold_boundary(0, 60)]
    metrics = compute_axis_deviation(frames, boundaries, pole_no_line)
    m = metrics[0]
    assert m.pelvis_distance_from_pole_axis is None
    assert m.chest_distance_from_pole_axis is None
    assert m.coordinate_space == "unavailable"
    assert m.scale_denominator == "unavailable"
    assert "pole_line_missing" in m.warnings


def test_scale_unavailable_returns_null_distance_with_warning():
    """valid frame < 5 → median_torso_length None → scale_denominator='unavailable'."""
    frames, pole, _, _ = build_clean_invert()
    # 5 frame 미만 → median_torso_length 가 None 반환.
    short_frames = frames[:3]
    boundaries = [_hold_boundary(0, 3)]
    metrics = compute_axis_deviation(short_frames, boundaries, pole)
    m = metrics[0]
    assert m.scale_denominator == "unavailable"
    assert "scale_unavailable" in m.warnings


def test_coordinate_space_image_2d_when_line_present():
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_hold_boundary(0, 60)]
    metrics = compute_axis_deviation(frames, boundaries, pole)
    assert metrics[0].coordinate_space == "image_2d"


def test_coordinate_space_unavailable_when_line_none():
    frames, _, _, _ = build_clean_invert()
    pole_no_line = make_pole_axis_measurement(line=None)
    boundaries = [_hold_boundary(0, 60)]
    metrics = compute_axis_deviation(frames, boundaries, pole_no_line)
    assert metrics[0].coordinate_space == "unavailable"


def test_torso_scale_not_used_as_denominator():
    """REVIEWS R2 drift defense — compute_axis_deviation source 안에서
    BodyNormalizationProfile.torso_scale 사용 영구 금지.
    """
    import inspect

    from sunity_shared.analysis import force_signals

    src = inspect.getsource(force_signals)
    # 본 module 안에서 BodyNormalizationProfile 사용 금지.
    assert "BodyNormalizationProfile" not in src
    # torso_scale literal 사용 금지 (median_torso_length 만 사용).
    # body_normalization 의 torso_scale 필드 attribute access 검색 — 'profile.torso_scale' 등 영구 차단.
    assert ".torso_scale" not in src


def test_pelvis_drop_fixture_emits_high_severity_outward():
    """build_pelvis_drop: hold 구간 pelvis +0.35 outward → severity='high'."""
    frames, pole, _, expected = build_pelvis_drop()
    # hold = frame 30~50 (pelvis drop 구간).
    boundaries = [_hold_boundary(30, 50)]
    metrics = compute_axis_deviation(frames, boundaries, pole)
    m = metrics[0]
    # raw distance ≈ 0.35, normalized by torso (0.30) → 1.17. > 0.30 = high.
    assert m.severity == "high"
    assert m.deviation_direction in ("outward", "left", "right")


def test_shoulder_tilt_signed_degrees():
    """shoulder_tilt 가 float (signed degrees) 반환."""
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_hold_boundary(0, 60)]
    metrics = compute_axis_deviation(frames, boundaries, pole)
    m = metrics[0]
    assert m.shoulder_tilt is not None
    assert isinstance(m.shoulder_tilt, float)


def test_hip_tilt_signed_degrees():
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_hold_boundary(0, 60)]
    metrics = compute_axis_deviation(frames, boundaries, pole)
    m = metrics[0]
    assert m.hip_tilt is not None
    assert isinstance(m.hip_tilt, float)


def test_deviation_direction_outward():
    """pelvis +0.35 outward drift → deviation_direction != 'unknown'."""
    frames, pole, _, _ = build_pelvis_drop()
    boundaries = [_hold_boundary(30, 50)]
    metrics = compute_axis_deviation(frames, boundaries, pole)
    m = metrics[0]
    assert m.deviation_direction != "unknown"
