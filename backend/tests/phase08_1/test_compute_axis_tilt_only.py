"""Plan 08.1-01 Wave 1 — compute_axis_deviation 실 tilt-only body 검증.

3 branch:
  - pole_aligned 3D path (정은지 영상 — RTMW path)
  - image_2d fallback path (legacy or non-RTMW)
  - 둘 다 미가용 path → severity='low' + warnings 'tilt_unavailable'

invariants:
  - 6 필드 AxisDeviationMetric 정합 (Wave 0 schema 보존)
  - tilt 값 ∈ [0, 90] (unsigned) 또는 None
  - FPS-invariance — 9 fps vs 18 fps (2x resample) 동일 tilt

per Plan 08.1-01 must_haves Step 3 RED.
"""

from __future__ import annotations

import dataclasses

import pytest

from sunity_shared.analysis.force_signals import (
    AxisDeviationMetric,
    _severity_from_tilt,
    compute_axis_deviation,
)
from tests.phase08_1.fixtures._factory import (
    make_phase_boundary,
    make_pole_axis_measurement_vertical_fallback,
    make_pole_axis_measurement_with_line,
    make_pole_line_vertical,
    make_pose_frame_neither_path,
    make_pose_frame_with_image_2d_only,
    make_pose_frame_with_pole_aligned,
)


# ── pole_aligned path ────────────────────────────────────────────────────


def test_compute_axis_pole_aligned_path() -> None:
    """pole_aligned 3D path — shoulder_tilt=15°, hip_tilt=10° → severity='low'."""
    pose_frames = [
        make_pose_frame_with_pole_aligned(
            frame_index=i, shoulder_tilt_deg=15.0, hip_tilt_deg=10.0
        )
        for i in range(10)
    ]
    phases = [make_phase_boundary("hold", 0, 10)]
    measurement = make_pole_axis_measurement_vertical_fallback()

    metrics = compute_axis_deviation(pose_frames, phases, measurement, fps=9.0)

    assert len(metrics) == 1
    m = metrics[0]
    assert m.phase == "hold"
    assert m.shoulder_tilt is not None
    assert abs(m.shoulder_tilt - 15.0) < 2.0
    assert m.hip_tilt is not None
    assert abs(m.hip_tilt - 10.0) < 2.0
    # 15° < fallback 25° → 'low'.
    assert m.severity == "low"
    assert "tilt_unavailable" not in m.warnings


# ── image_2d fallback path ───────────────────────────────────────────────


def test_compute_axis_image_2d_path_fallback() -> None:
    """keypoints_2d only + pole_line vertical → shoulder_tilt=12°, hip_tilt=8°."""
    line = make_pole_line_vertical()
    pose_frames = [
        make_pose_frame_with_image_2d_only(
            frame_index=i,
            shoulder_tilt_deg=12.0,
            hip_tilt_deg=8.0,
            pole_line=line,
        )
        for i in range(10)
    ]
    phases = [make_phase_boundary("hold", 0, 10)]
    measurement = make_pole_axis_measurement_with_line(line)

    metrics = compute_axis_deviation(pose_frames, phases, measurement, fps=9.0)

    assert len(metrics) == 1
    m = metrics[0]
    assert m.shoulder_tilt is not None
    assert abs(m.shoulder_tilt - 12.0) < 2.0, f"got {m.shoulder_tilt}"
    assert m.hip_tilt is not None
    assert abs(m.hip_tilt - 8.0) < 2.0, f"got {m.hip_tilt}"
    assert m.severity == "low"


# ── neither path → 'tilt_unavailable' ────────────────────────────────────


def test_compute_axis_neither_path_unavailable() -> None:
    """keypoints_3d_pole_aligned 빈 dict + keypoints_2d=None → 'tilt_unavailable'."""
    pose_frames = [make_pose_frame_neither_path(frame_index=i) for i in range(10)]
    phases = [make_phase_boundary("hold", 0, 10)]
    measurement = make_pole_axis_measurement_vertical_fallback()

    metrics = compute_axis_deviation(pose_frames, phases, measurement, fps=9.0)

    assert len(metrics) == 1
    m = metrics[0]
    assert m.shoulder_tilt is None
    assert m.hip_tilt is None
    assert m.severity == "low"
    assert m.confidence == "low"
    assert "tilt_unavailable" in m.warnings


# ── _severity_from_tilt boundary semantics ──────────────────────────────


def test_severity_from_tilt_low_medium_high() -> None:
    thresholds = (25.0, 37.5)
    assert _severity_from_tilt(15.0, thresholds) == "low"
    assert _severity_from_tilt(30.0, thresholds) == "medium"
    assert _severity_from_tilt(40.0, thresholds) == "high"
    assert _severity_from_tilt(None, thresholds) == "low"


# ── FPS-invariance ──────────────────────────────────────────────────────


def test_fps_invariance_tilt_metric() -> None:
    """9 fps (N frames) vs 18 fps (2N frames, identical tilt per frame) → 동일 tilt."""
    frames_9 = [
        make_pose_frame_with_pole_aligned(
            frame_index=i, shoulder_tilt_deg=20.0, hip_tilt_deg=15.0
        )
        for i in range(10)
    ]
    frames_18 = [
        make_pose_frame_with_pole_aligned(
            frame_index=i, shoulder_tilt_deg=20.0, hip_tilt_deg=15.0
        )
        for i in range(20)
    ]
    measurement = make_pole_axis_measurement_vertical_fallback()

    m9 = compute_axis_deviation(
        frames_9, [make_phase_boundary("hold", 0, 10)], measurement, fps=9.0
    )[0]
    m18 = compute_axis_deviation(
        frames_18, [make_phase_boundary("hold", 0, 20)], measurement, fps=18.0
    )[0]

    assert m9.shoulder_tilt is not None and m18.shoulder_tilt is not None
    assert abs(m9.shoulder_tilt - m18.shoulder_tilt) < 0.01
    assert m9.hip_tilt is not None and m18.hip_tilt is not None
    assert abs(m9.hip_tilt - m18.hip_tilt) < 0.01


# ── 6 필드 정합 ──────────────────────────────────────────────────────────


def test_axis_metric_has_only_six_fields() -> None:
    """Wave 0 schema 보존 — 6 필드 (phase / shoulder_tilt / hip_tilt / severity /
    confidence / warnings) 만 정합."""
    field_names = {f.name for f in dataclasses.fields(AxisDeviationMetric)}
    assert field_names == {
        "phase",
        "shoulder_tilt",
        "hip_tilt",
        "severity",
        "confidence",
        "warnings",
    }
