"""Plan 08-02 Task 3 — compute_force_signals umbrella 통합 test.

REVIEWS R5 핵심: temporal_fill 중복 호출 영구 차단 — angles 인자 = caller
(pipeline._process) 가 이미 temporal_fill 1회 적용 후 전달. umbrella 본체는
temporal_fill 호출 영구 금지 (double smoothing 차단).

mocked test: unittest.mock.patch 로 temporal.temporal_fill mock + call_count==0 검증.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from sunity_shared.analysis.force_signals import (
    ForceSignalsReport,
    compute_force_signals,
)

from .fixtures._fixture_builders import (
    build_clean_invert,
    build_occluded_lock,
)


def _angles(n: int, seed: int = 0) -> np.ndarray:
    """non-trivial smooth signal — 4 metric 모두 산출 가능."""
    rng = np.random.default_rng(seed)
    base = 90.0 + 5.0 * np.sin(np.arange(n) / 5.0)
    out = np.tile(base.reshape(-1, 1), (1, 8))
    out += rng.normal(0.0, 0.5, size=(n, 8))
    return out


def test_compute_force_signals_e2e_clean_invert():
    """build_clean_invert E2E — 5 phase + 4 metric list non-empty."""
    frames, pole, profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    report = compute_force_signals(
        frames,
        pole,
        profile,
        angles=angles,
        fps=expected["fps"],
        motion_id=expected["motion_id"],
        preflight_label_gate_passed=True,
    )
    assert isinstance(report, ForceSignalsReport)
    assert len(report.phase_boundaries) == 5
    assert len(report.axis_metrics) > 0
    assert len(report.stability_metrics) > 0
    assert len(report.contact_metrics) > 0


def test_compute_force_signals_does_not_call_temporal_fill():
    """REVIEWS R5 정합 — umbrella 본체 안에서 temporal_fill 영구 호출 차단.

    unittest.mock.patch 로 temporal.temporal_fill mock + call_count==0 검증.
    """
    frames, pole, profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    with patch(
        "sunity_shared.analysis.temporal.temporal_fill"
    ) as mock_fill:
        compute_force_signals(
            frames,
            pole,
            profile,
            angles=angles,
            fps=expected["fps"],
            motion_id=expected["motion_id"],
        )
        assert mock_fill.call_count == 0


def test_compute_force_signals_requires_angles_not_none():
    """angles=None 호출 시 ValueError raise (REVIEWS R5 — caller responsibility 강제)."""
    frames, pole, profile, _ = build_clean_invert()
    with pytest.raises(ValueError, match=r"angles"):
        compute_force_signals(
            frames,
            pole,
            profile,
            angles=None,  # type: ignore[arg-type]
            fps=9.0,
        )


def test_confidence_weighting_emits_warning_on_high_low_reliability():
    """phase 의 LOW_RELIABILITY_PHASE_THRESHOLD (0.4) 초과 → 'occlusion_high_in_phase' 박제.

    build_occluded_lock 자체는 6/60 low-frame (10%) — Layer 1 heuristic 균등
    분할 시 single phase 내 비율이 LOW_RELIABILITY_PHASE_THRESHOLD 미달.
    본 test 는 동일 fixture frame 위에 추가 low frame 을 박제해 한 phase 의
    low 비율 > 0.4 강제 — warning emission mechanism 검증.
    """
    from .fixtures._factory import make_pose_frame
    from .fixtures._fixture_builders import _make_frame_basic, _line_available_measurement

    # 60 frame — 처음 5 frame 이 모두 reliability='low' → entry phase (0-12) 의
    # 5/12 = 0.42 > LOW_RELIABILITY_PHASE_THRESHOLD (0.4).
    frames = []
    for i in range(60):
        rel = "low" if i < 5 else "high"
        frames.append(_make_frame_basic(i, reliability=rel))
    pole = _line_available_measurement()
    angles = _angles(len(frames))
    report = compute_force_signals(
        frames,
        pole,
        None,
        angles=angles,
        fps=9.0,
        motion_id="ref-foxtop",
    )
    # entry phase metric 의 warnings 에 'occlusion_high_in_phase' 박제.
    all_metric_warnings = []
    for m in report.stability_metrics:
        all_metric_warnings.extend(m.warnings)
    assert "occlusion_high_in_phase" in all_metric_warnings


def test_overall_confidence_min_propagation():
    """1 metric confidence='low' → overall_confidence='low' (min propagation)."""
    frames, pole, profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    # preflight gate=None → phase_boundaries confidence='low' → overall='low'.
    report = compute_force_signals(
        frames,
        pole,
        profile,
        angles=angles,
        fps=expected["fps"],
        motion_id=expected["motion_id"],
        preflight_label_gate_passed=None,
    )
    assert report.overall_confidence == "low"


def test_motion_unrecognized_emits_warning():
    """motion_id=None → top-level warnings contains 'motion_unrecognized_layer1_only'."""
    frames, pole, profile, _ = build_clean_invert()
    angles = _angles(len(frames))
    report = compute_force_signals(
        frames,
        pole,
        profile,
        angles=angles,
        fps=9.0,
        motion_id=None,
    )
    assert "motion_unrecognized_layer1_only" in report.warnings


def test_layer2_unavailable_emits_warning():
    """gemini_extractor=None → warnings contains 'layer2_unavailable'."""
    frames, pole, profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    report = compute_force_signals(
        frames,
        pole,
        profile,
        angles=angles,
        fps=expected["fps"],
        motion_id=expected["motion_id"],
        gemini_extractor=None,
    )
    assert "layer2_unavailable" in report.warnings


def test_warning_fps_normalization_applied_emitted():
    """fps 정상 호출 시 warnings contains 'fps_normalization_applied' (REVIEWS R5 박제 메모)."""
    frames, pole, profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    report = compute_force_signals(
        frames,
        pole,
        profile,
        angles=angles,
        fps=expected["fps"],
        motion_id=expected["motion_id"],
    )
    assert "fps_normalization_applied" in report.warnings
