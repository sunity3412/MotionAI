"""Plan 08.1-00 Wave 0 — compute_axis_deviation transitional stub test (D-01).

Phase 8.1 박제 (2026-06-09): distance 차원 hard break — IPSF Code of Points 글로벌
distance 항목 부재. compute_axis_deviation 본체 = transitional stub. Wave 1 가
실 tilt 측정 알고리즘 배포 시 본 test 들이 RED → 새 본체 test 로 교체.

기존 distance 산출 기반 assertion (pelvis_distance / chest_distance /
scale_denominator / coordinate_space / deviation_direction) 박제 제거.
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
from .fixtures._fixture_builders import build_clean_invert


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


def _multi_phase_boundaries() -> list[PhaseBoundary]:
    """3 phase boundary 박제 — stub fan-out 검증."""
    return [
        PhaseBoundary(
            phase="entry",
            start_frame_idx=0,
            end_frame_idx=10,
            start_ms=0,
            end_ms=1111,
            confidence="low",
            source="heuristic",
            preflight_label_gate_passed=None,
        ),
        PhaseBoundary(
            phase="final_shape",
            start_frame_idx=10,
            end_frame_idx=30,
            start_ms=1111,
            end_ms=3333,
            confidence="low",
            source="heuristic",
            preflight_label_gate_passed=None,
        ),
        PhaseBoundary(
            phase="hold",
            start_frame_idx=30,
            end_frame_idx=60,
            start_ms=3333,
            end_ms=6666,
            confidence="low",
            source="heuristic",
            preflight_label_gate_passed=None,
        ),
    ]


# ── Wave 0 stub 동작 검증 ─────────────────────────────────────────────────


def test_compute_axis_returns_stub_for_all_phases() -> None:
    """3 phase boundary 입력 → 3 metric 반환 + 모두 stub default.

    severity='low' / confidence='low' / shoulder_tilt=None / hip_tilt=None /
    warnings 박제 'phase_8_1_wave_0_transitional' 포함.
    """
    frames, pole, _, _ = build_clean_invert()
    boundaries = _multi_phase_boundaries()
    metrics = compute_axis_deviation(frames, boundaries, pole)
    assert len(metrics) == 3
    expected_phases = ["entry", "final_shape", "hold"]
    for i, m in enumerate(metrics):
        assert m.phase == expected_phases[i]
        assert m.shoulder_tilt is None
        assert m.hip_tilt is None
        assert m.severity == "low"
        assert m.confidence == "low"
        assert "phase_8_1_wave_0_transitional" in m.warnings


def test_shoulder_tilt_stub_returns_none() -> None:
    """Wave 0 stub: shoulder_tilt=None 반환 + warning 'phase_8_1_wave_0_transitional'.

    Wave 1 가 실 tilt 측정 알고리즘 배포 시 본 test RED → 새 본체 test 로 교체.
    """
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_hold_boundary(0, 60)]
    metrics = compute_axis_deviation(frames, boundaries, pole)
    m = metrics[0]
    assert m.shoulder_tilt is None
    assert "phase_8_1_wave_0_transitional" in m.warnings


def test_hip_tilt_stub_returns_none() -> None:
    """Wave 0 stub: hip_tilt=None 반환 + warning 'phase_8_1_wave_0_transitional'."""
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_hold_boundary(0, 60)]
    metrics = compute_axis_deviation(frames, boundaries, pole)
    m = metrics[0]
    assert m.hip_tilt is None
    assert "phase_8_1_wave_0_transitional" in m.warnings


# ── R2 drift defense — 본 plan 박제 보존 (Wave 1 cleanup) ─────────────────


def test_torso_scale_not_used_as_denominator() -> None:
    """REVIEWS R2 drift defense — compute_axis_deviation source 안에서
    BodyNormalizationProfile.torso_scale 사용 영구 금지.

    본 plan (Wave 0) 의 stub body 자체는 torso 사용 X. 모듈 차원 invariant
    유지 (helper 함수들 Wave 1 cleanup 까지 보존).
    """
    import inspect

    from sunity_shared.analysis import force_signals

    src = inspect.getsource(force_signals)
    # 본 module 안에서 BodyNormalizationProfile 사용 금지.
    assert "BodyNormalizationProfile" not in src
    # torso_scale literal 사용 금지 (median_torso_length 만 사용).
    # body_normalization 의 torso_scale 필드 attribute access 검색 — 'profile.torso_scale' 등 영구 차단.
    assert ".torso_scale" not in src


# ── Wave 0 stub 의 pole_axis_measurement 의존성 부재 검증 ────────────────


def test_stub_ignores_pole_axis_measurement_line() -> None:
    """Wave 0 stub: pole_axis_measurement.line 가용성에 무관 동일 결과 반환.

    distance 산출 path 영구 제거 → line=None / line=PoleLine2D 두 입력 동일 결과.
    """
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_hold_boundary(0, 60)]

    metrics_with_line = compute_axis_deviation(frames, boundaries, pole)
    pole_no_line = make_pole_axis_measurement(line=None)
    metrics_no_line = compute_axis_deviation(frames, boundaries, pole_no_line)

    assert len(metrics_with_line) == len(metrics_no_line) == 1
    a, b = metrics_with_line[0], metrics_no_line[0]
    assert a.shoulder_tilt == b.shoulder_tilt is None
    assert a.hip_tilt == b.hip_tilt is None
    assert a.severity == b.severity == "low"
    assert a.warnings == b.warnings == ["phase_8_1_wave_0_transitional"]
