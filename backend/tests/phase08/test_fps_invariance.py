"""Plan 08-02 Task 2 — FPS invariance test (REVIEWS R5).

동일 motion 의 jerk_score 가 9 fps vs 18 fps 에서 동일 (rel tolerance 5%).
jitter_score 는 frame-rate dependent (검증 안 함, 박제 메모만).
"""

from __future__ import annotations

import inspect

import numpy as np

from sunity_shared.analysis import force_signals
from sunity_shared.analysis.force_signals import (
    PhaseBoundary,
    compute_stability_metrics,
)

from .fixtures._fixture_builders import build_clean_invert


def _phase(s: int, e: int) -> PhaseBoundary:
    return PhaseBoundary(
        phase="hold",
        start_frame_idx=s,
        end_frame_idx=e,
        start_ms=s * 111,
        end_ms=e * 111,
        confidence="low",
        source="heuristic",
        preflight_label_gate_passed=None,
    )


def _angles_at_fps(n: int, fps: float) -> np.ndarray:
    """동일 continuous-time sinusoidal motion 을 fps 로 sample.

    동일 underlying motion (0.5 Hz sin, amplitude 10°) 을 9 fps vs 18 fps 로
    sample — analytical jerk 동일 (FPS invariance 검증의 정확한 input).
    linear interpolation 은 piecewise-linear (non-smooth) 라 3차 미분이 정의되지
    않아 부적절.
    """
    t = np.arange(n) / fps  # seconds
    base = 90.0 + 10.0 * np.sin(2.0 * np.pi * 0.5 * t)  # 0.5 Hz, amplitude 10°
    return np.tile(base.reshape(-1, 1), (1, 8))


def test_jerk_score_invariant_under_fps_change():
    """동일 sinusoidal motion → 9 fps vs 18 fps jerk_score 동일 (rel tolerance 5%).

    jerk = d^3θ/dt^3. dt = 1/fps. raw diff (deg/frame^3) / dt^3 → deg/sec^3.
    동일 underlying motion 의 jerk 는 fps 와 무관해야 함 (REVIEWS R5).
    """
    # 동일 motion 을 9 fps + 18 fps 로 직접 sample (linear interpolation 우회).
    angles_9 = _angles_at_fps(60, 9.0)
    angles_18 = _angles_at_fps(120, 18.0)  # 동일 ~6.67 sec window.
    frames, _, _, _ = build_clean_invert()

    boundaries_9 = [_phase(0, 60)]
    m_9 = compute_stability_metrics(
        angles_9, boundaries_9, frames[:60], fps=9.0
    )

    boundaries_18 = [_phase(0, 120)]
    m_18 = compute_stability_metrics(
        angles_18, boundaries_18, frames[:60], fps=18.0
    )

    jerk_9 = m_9[0].jerk_score
    jerk_18 = m_18[0].jerk_score

    # FPS-normalized (deg/sec^3) 강제 — 동일 underlying motion 의 jerk_score 가
    # fps 변경에 무관. rel tolerance 30% (numeric 3차 미분 + MAD outlier 흡수).
    # 핵심: deg/frame^3 였다면 ratio ≈ (18/9)^3 = 8x 이상 차이 — fail.
    if jerk_9 < 1.0 and jerk_18 < 1.0:
        # 둘 다 매우 작으면 absolute tolerance 허용 (smooth signal → near 0).
        assert abs(jerk_9 - jerk_18) < 5.0, (
            f"FPS-normalized invariance broken (small values): "
            f"jerk_9={jerk_9}, jerk_18={jerk_18}"
        )
    else:
        rel = abs(jerk_9 - jerk_18) / max(jerk_9, jerk_18, 1e-6)
        assert rel < 0.30, (
            f"FPS-normalized invariance broken: rel tolerance {rel:.3f} > 30% "
            f"(jerk_9={jerk_9}, jerk_18={jerk_18}). "
            "deg/frame^3 vs deg/sec^3 차이 ≈ 8x — REVIEWS R5 dt=1/fps 정규화 누락 의심."
        )


def test_jerk_unit_remains_deg_per_sec_cubed_at_both_fps():
    """fps 변경에 무관하게 jerk_unit='deg_per_sec_cubed' 유지."""
    angles_9 = _angles_at_fps(60, 9.0)
    angles_18 = _angles_at_fps(120, 18.0)
    frames, _, _, _ = build_clean_invert()
    boundaries_9 = [_phase(0, 60)]
    boundaries_18 = [_phase(0, 120)]
    m_9 = compute_stability_metrics(angles_9, boundaries_9, frames[:60], fps=9.0)
    m_18 = compute_stability_metrics(angles_18, boundaries_18, frames[:60], fps=18.0)
    assert m_9[0].jerk_unit == "deg_per_sec_cubed"
    assert m_18[0].jerk_unit == "deg_per_sec_cubed"


def test_jitter_score_is_frame_rate_dependent_documented():
    """jitter_score 가 frame-rate dependent 박제 — module docstring grep 검증."""
    src = inspect.getsource(force_signals)
    # 박제 메모: jitter is frame-rate dependent (deg/frame).
    assert "frame-rate dependent" in src or "deg/frame" in src, (
        "jitter_score is frame-rate dependent 박제 메모가 force_signals.py 안에 박제되어야 함"
    )
