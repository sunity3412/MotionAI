"""Plan 08.1-02 Wave 2 — pipeline _process mock E2E (synthetic pose_frames).

compute_force_signals 우산 안 axisMetrics 6 필드 정합 + distance kwarg 부재 +
tilt-only path 산출 검증.

3 test:
  - test_pipeline_axis_metrics_have_six_fields: 5 distance 필드 부재 + 6 필드 존재
  - test_pipeline_axis_metrics_no_distance_fields: compute_axis_deviation 의
    distance kwarg/positional 사용 시 TypeError
  - test_pipeline_axis_tilt_only_path: pole_aligned 입력 → shoulder/hip tilt
    산출 + severity 'low' + warnings 청결 (tilt_unavailable / transitional /
    fallback 부재)

mock-based — 실 S3 / 실 Firestore / 실 RTMW / 실 Gemini 호출 0.

per Plan 08.1-02 must_haves artifacts[2].
"""

from __future__ import annotations

import dataclasses
import inspect

import numpy as np
import pytest

from sunity_shared.analysis.force_signals import (
    BodyLineTiltMetric,
    compute_axis_deviation,
    compute_force_signals,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS

from tests.phase08_1.fixtures._factory import (
    make_phase_boundary,
    make_pole_axis_measurement_vertical_fallback,
    make_pose_frame_with_pole_aligned,
)


# ── Helper: synthetic angles + body profile ──────────────────────────────


def _angles_8j(rows: int = 60) -> np.ndarray:
    """compute_force_signals 가 받는 angles (T, J) 합성."""
    rng = np.random.default_rng(0)
    base = 90.0 + 5.0 * np.sin(np.arange(rows) / 5.0)
    out = np.tile(base.reshape(-1, 1), (1, len(JOINT_KEYS)))
    out += rng.normal(0.0, 0.5, size=(rows, len(JOINT_KEYS)))
    return out


def _mock_body_profile():
    """compute_force_signals body_profile 박제 — Phase 8 fixture 와 동일 패턴."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    return BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.9,
        warnings=[],
    )


# ── Test 1: 6 필드 정합 (Wave 0 schema 보존) ─────────────────────────────


def test_pipeline_axis_metrics_have_six_fields() -> None:
    """compute_force_signals → forceSignalsReport.axisMetrics 의 각 metric 가
    BodyLineTiltMetric 의 6 필드만 보유 — distance/scale_denominator/
    coordinate_space/deviation_direction 5 필드 부재.
    """
    pose_frames = [
        make_pose_frame_with_pole_aligned(
            frame_index=i, shoulder_tilt_deg=15.0, hip_tilt_deg=10.0
        )
        for i in range(60)
    ]
    measurement = make_pole_axis_measurement_vertical_fallback()
    angles = _angles_8j(rows=60)
    body_profile = _mock_body_profile()

    report = compute_force_signals(
        pose_frames,
        measurement,
        body_profile,
        angles=angles,
        fps=9.0,
    )

    assert report.axis_metrics, "expected at least one BodyLineTiltMetric"
    expected_fields = {
        "phase",
        "shoulder_tilt",
        "hip_tilt",
        "severity",
        "confidence",
        "warnings",
    }
    schema_fields = {f.name for f in dataclasses.fields(BodyLineTiltMetric)}
    assert schema_fields == expected_fields

    # distance 필드 직접 access 시 AttributeError — 5 distance 필드 부재.
    sample = report.axis_metrics[0]
    for forbidden in (
        "pelvis_distance_from_pole_axis",
        "chest_distance_from_pole_axis",
        "scale_denominator",
        "coordinate_space",
        "deviation_direction",
    ):
        with pytest.raises(AttributeError):
            getattr(sample, forbidden)


# ── Test 2: distance kwarg 부재 — TypeError ──────────────────────────────


def test_pipeline_axis_metrics_no_distance_fields() -> None:
    """compute_axis_deviation 시그너처 박제 — distance/scale/coordinate 관련
    kwarg 전무. distance kwarg 호출 시 TypeError.

    Wave 1 의 시그너처: (pose_frames, phase_boundaries, pole_axis_measurement,
    *, fps=9.0). distance 관련 kwarg 자체 부재.
    """
    sig = inspect.signature(compute_axis_deviation)
    params = set(sig.parameters)
    for forbidden in (
        "distance",
        "scale_denominator",
        "coordinate_space",
        "deviation_direction",
        "pelvis_distance",
        "chest_distance",
    ):
        assert forbidden not in params, (
            f"compute_axis_deviation must not have {forbidden} parameter "
            f"(Wave 0 D-01 distance hard break). got: {params}"
        )

    # actual call with forbidden kwarg → TypeError
    pose_frames = [
        make_pose_frame_with_pole_aligned(
            frame_index=i, shoulder_tilt_deg=10.0, hip_tilt_deg=5.0
        )
        for i in range(10)
    ]
    phases = [make_phase_boundary("hold", 0, 10)]
    measurement = make_pole_axis_measurement_vertical_fallback()

    with pytest.raises(TypeError):
        compute_axis_deviation(  # type: ignore[call-arg]
            pose_frames, phases, measurement, distance="anything"
        )


# ── Test 3: tilt-only path 산출 ───────────────────────────────────────────


def test_pipeline_axis_tilt_only_path() -> None:
    """pole_aligned 합성 입력 (shoulder=15°, hip=10°) → tilt 산출 +
    severity='low' + warnings 청결 (tilt_unavailable / transitional /
    tilt_thresholds_fallback 부재).

    8조건 measured-low gate 의 mock E2E 검증 — Wave 2 production sweep 의
    핵심 invariant 를 unit test 차원 에서 박제.
    """
    pose_frames = [
        make_pose_frame_with_pole_aligned(
            frame_index=i, shoulder_tilt_deg=15.0, hip_tilt_deg=10.0
        )
        for i in range(60)
    ]
    measurement = make_pole_axis_measurement_vertical_fallback()
    angles = _angles_8j(rows=60)
    body_profile = _mock_body_profile()

    report = compute_force_signals(
        pose_frames,
        measurement,
        body_profile,
        angles=angles,
        fps=9.0,
    )

    assert report.axis_metrics, "expected axisMetrics 산출"
    for m in report.axis_metrics:
        # tilt 값 산출 (None 아님).
        assert m.shoulder_tilt is not None, f"phase={m.phase} shoulder_tilt is None"
        assert m.hip_tilt is not None, f"phase={m.phase} hip_tilt is None"
        # 입력 의도 값 근접 (np.median tolerance 2°).
        assert abs(m.shoulder_tilt - 15.0) < 2.0
        assert abs(m.hip_tilt - 10.0) < 2.0
        # 15° / 10° 모두 yaml shoulder_cutoff=63.28° / hip_cutoff=54.62° 미만 → 'low'.
        assert m.severity == "low", f"phase={m.phase} severity={m.severity}"
        # warnings 청결 — production sweep 의 8조건 acceptance 정합.
        for forbidden in (
            "tilt_unavailable",
            "phase_8_1_wave_0_transitional",
            "tilt_thresholds_fallback",
        ):
            assert forbidden not in m.warnings, (
                f"phase={m.phase} warnings={m.warnings} contains {forbidden}"
            )

    # top-level warnings 청결 — axis_metric_transitional 부재.
    assert "axis_metric_transitional" not in report.warnings
