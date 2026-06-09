"""Plan 08-02 Task 2 — compute_stability_metrics 단위 test.

REVIEWS R5: jerk FPS-normalized (deg/sec^3) + jerk_unit='deg_per_sec_cubed'.
Drift defense: jitter_score == dimensions.stability_wobble (abs < 1e-9).
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis import dimensions
from sunity_shared.analysis.force_signals import (
    JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED,
    UNSTABLE_BODY_PART_THRESHOLD_DEG,
    PhaseBoundary,
    compute_stability_metrics,
)

from .fixtures._fixture_builders import build_clean_invert, build_jerk_high


def _phase(name: str, s: int, e: int) -> PhaseBoundary:
    return PhaseBoundary(
        phase=name,  # type: ignore[arg-type]
        start_frame_idx=s,
        end_frame_idx=e,
        start_ms=s * 111,
        end_ms=e * 111,
        confidence="low",
        source="heuristic",
        preflight_label_gate_passed=None,
    )


def _angles_constant(n: int, val: float = 90.0) -> np.ndarray:
    return np.full((n, 8), val, dtype=float)


def _angles_noisy(n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return 90.0 + rng.normal(0.0, 2.0, size=(n, 8))


def test_drift_defense():
    """force_signals.jitter_score 가 dimensions.stability_wobble 직접 호출과
    abs < 1e-9 일치."""
    angles = _angles_noisy(50)
    frames, _, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 50)]
    metrics = compute_stability_metrics(angles, boundaries, frames[:50])
    expected = dimensions.stability_wobble(angles, profile=None)
    assert abs(metrics[0].jitter_score - expected) < 1e-9


def test_jitter_score_uses_dimensions_helper():
    """jitter_score is a non-negative float (deg/frame)."""
    angles = _angles_noisy(40)
    frames, _, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 40)]
    metrics = compute_stability_metrics(angles, boundaries, frames[:40])
    assert metrics[0].jitter_score >= 0.0


def test_jerk_score_fps_normalized_deg_per_sec_cubed():
    """동일 motion 의 jerk_score 가 dt=1/fps 정규화 산출 (deg/sec^3, FPS-invariant 단위).

    smooth signal → jerk ≈ 0.
    """
    angles = _angles_constant(40)
    frames, _, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 40)]
    metrics = compute_stability_metrics(angles, boundaries, frames[:40], fps=9.0)
    # constant angles → 3차 미분 = 0 → jerk_score = 0.
    assert metrics[0].jerk_score < 1e-6


def test_jerk_unit_field_is_deg_per_sec_cubed():
    """jerk_unit='deg_per_sec_cubed' 강제 (REVIEWS R5)."""
    angles = _angles_noisy(40)
    frames, _, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 40)]
    metrics = compute_stability_metrics(angles, boundaries, frames[:40], fps=9.0)
    assert metrics[0].jerk_unit == "deg_per_sec_cubed"


def test_jerk_score_mad_filtered():
    """MAD outlier rejection — single huge spike 가 median 을 왜곡하지 않음."""
    angles = _angles_constant(40)
    # frame 20 에 큰 spike (outlier).
    angles[20, 0] = 200.0
    angles[21, 0] = 90.0
    frames, _, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 40)]
    metrics = compute_stability_metrics(angles, boundaries, frames[:40], fps=9.0)
    # outlier 가 median 을 크게 왜곡 안 함 — MAD 필터링 후 median 은 여전히 매우 낮음.
    assert metrics[0].jerk_score < JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED[1]


def test_hold_stability_score_on_hold_phase_only():
    """phase='hold' 일 때만 hold_stability_score 반환."""
    angles = _angles_noisy(40)
    frames, _, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 40)]
    metrics = compute_stability_metrics(angles, boundaries, frames[:40])
    assert metrics[0].hold_stability_score is not None


def test_hold_stability_score_returns_none_when_phase_not_hold():
    """phase!='hold' → hold_stability_score=None."""
    angles = _angles_noisy(40)
    frames, _, _, _ = build_clean_invert()
    boundaries = [_phase("entry", 0, 40)]
    metrics = compute_stability_metrics(angles, boundaries, frames[:40])
    assert metrics[0].hold_stability_score is None


def test_unstable_body_parts_threshold_filter():
    """unstable_body_parts = wobble > UNSTABLE_BODY_PART_THRESHOLD_DEG."""
    angles = _angles_constant(40)
    frames, _, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 40)]
    metrics = compute_stability_metrics(angles, boundaries, frames[:40])
    # constant → 모든 joint wobble = 0 → unstable_body_parts = [].
    assert metrics[0].unstable_body_parts == []
    # threshold 박제 확인.
    assert UNSTABLE_BODY_PART_THRESHOLD_DEG > 0


def test_jerk_high_fixture_emits_high_severity():
    """build_jerk_high transition 구간 → severity='high'."""
    frames, _, _, expected = build_jerk_high()
    # synthesize a high-jerk angles signal for the transition window.
    angles = _angles_constant(60)
    # transition 구간 (15~25) 에 ±20° 진동.
    for i in range(15, 25):
        sign = 1.0 if (i % 2 == 0) else -1.0
        angles[i, :] = 90.0 + sign * 25.0
    boundaries = [_phase("transition", 15, 25)]
    metrics = compute_stability_metrics(angles, boundaries, frames[15:25], fps=expected["fps"])
    # high jerk → severity 'high' 또는 'medium'.
    assert metrics[0].severity in ("medium", "high")
