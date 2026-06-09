"""Plan 08-03 Task 1 — compute_force_signals umbrella Layer 2 + Cycle 2 NEW HIGH #2 test.

신설 5 test:
  1. test_layer2_activates_with_technique_profile_moments
  2. test_layer2_agreement_high_confidence_propagates_to_overall
  3. test_layer2_failure_does_not_exceed_preflight_ceiling (REVIEWS Cycle 2 NEW HIGH #2)
  4. test_layer2_failure_with_preflight_none_stays_low
  5. test_layer2_failure_with_preflight_passed_stays_medium
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sunity_shared.analysis.force_signals import compute_force_signals

from .fixtures._fixture_builders import build_clean_invert


@dataclass(frozen=True)
class _FakeKeyMoment:
    moment_key: str
    timestamp_seconds: float
    frame_index: int
    confidence: float = 0.9


@dataclass
class _FakeTechniqueProfile:
    key_moments: tuple


def _angles(num_frames: int, num_joints: int = 8) -> np.ndarray:
    """non-trivial smooth signal — 4 metric 모두 산출 가능."""
    rng = np.random.default_rng(0)
    base = 90.0 + 5.0 * np.sin(np.arange(num_frames) / 5.0)
    out = np.tile(base.reshape(-1, 1), (1, num_joints))
    out += rng.normal(0.0, 0.5, size=(num_frames, num_joints))
    return out


def _moments_close_to_layer1(num_frames: int) -> tuple:
    """agreement 'high' 박제 moments."""
    e1 = num_frames // 5
    e4 = 4 * num_frames // 5
    return (
        _FakeKeyMoment("setup", e1 / 9.0, e1),
        _FakeKeyMoment("hold", e4 / 9.0, e4),
        _FakeKeyMoment("release", (num_frames - 1) / 9.0, num_frames - 1),
    )


def _moments_monotonic_violation() -> tuple:
    """ValueError raise 박제 moments."""
    return (
        _FakeKeyMoment("setup", 1.0, 12),
        _FakeKeyMoment("hold", 0.8, 8),  # final_shape 박제 [36, 8) 박제 위반
        _FakeKeyMoment("release", 6.0, 55),
    )


# ── 1. Layer 2 활성 — technique_profile.key_moments 박제 reuse ──────────────


def test_layer2_activates_with_technique_profile_moments(monkeypatch):
    """TechniqueProfile(key_moments=...) + FORCE_SIGNALS_LAYER2_ENABLED=1 → Layer 2
    활성 + phase_boundaries[*].source='gemini_assisted'.
    """
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    moments = _moments_close_to_layer1(len(frames))
    tp = _FakeTechniqueProfile(key_moments=moments)
    report = compute_force_signals(
        frames,
        pole,
        body_profile,
        angles=angles,
        fps=expected["fps"],
        motion_id=expected["motion_id"],
        preflight_label_gate_passed=True,
        technique_profile=tp,
    )
    assert any(
        b.source == "gemini_assisted" for b in report.phase_boundaries
    )
    # warning 'layer2_unavailable' 박제 미발생 (Layer 2 활성 박제).
    assert "layer2_unavailable" not in report.warnings


# ── 2. Layer 2 agreement 'high' + preflight=True → overall confidence 'high' 후보 ──


def test_layer2_agreement_high_confidence_propagates_to_overall(monkeypatch):
    """Layer 2 agreement 'high' + preflight_label_gate_passed=True →
    phase_boundaries 박제 confidence='medium' (ceiling 박제) 박제. overall_confidence
    박제 다른 metric 의 confidence 박제 영향 받음 (line/scale unavailable 박제 'low' 박제
    가능). 본 test 박제 phase_boundaries confidence 박제 'medium' 검증 핵심.
    """
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    moments = _moments_close_to_layer1(len(frames))
    tp = _FakeTechniqueProfile(key_moments=moments)
    report = compute_force_signals(
        frames,
        pole,
        body_profile,
        angles=angles,
        fps=expected["fps"],
        motion_id=expected["motion_id"],
        preflight_label_gate_passed=True,  # ceiling='medium'
        technique_profile=tp,
    )
    for b in report.phase_boundaries:
        # ceiling 박제 'medium' 박제 — Layer 2 agreement 'high' 박제 위로 promote 영구 X.
        assert b.confidence == "medium", (
            f"REVIEWS Cycle 2 NEW HIGH #2 ceiling 박제 위로 promote 영구 X — "
            f"confidence={b.confidence!r}"
        )


# ── 3. Layer 2 failure preflight ceiling 위로 promote 영구 X (Cycle 2 NEW HIGH #2) ──


def test_layer2_failure_does_not_exceed_preflight_ceiling(monkeypatch):
    """REVIEWS Cycle 2 NEW HIGH #2 차단 — Layer 2 except 박제 ceiling 박제 그대로 박제.

    preflight_label_gate_passed=None + Layer 2 raise → phase_boundaries[*].confidence='low'.
    """
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    tp = _FakeTechniqueProfile(key_moments=_moments_monotonic_violation())
    report = compute_force_signals(
        frames,
        pole,
        body_profile,
        angles=angles,
        fps=expected["fps"],
        motion_id=expected["motion_id"],
        preflight_label_gate_passed=None,  # ceiling='low'
        technique_profile=tp,
    )
    for b in report.phase_boundaries:
        assert b.confidence == "low", (
            f"REVIEWS Cycle 2 NEW HIGH #2 위반 — Layer 2 except 박제 ceiling 'low' "
            f"박제 유지 강제. confidence={b.confidence!r}"
        )


# ── 4. preflight=None + Layer 2 failure → 'low' 박제 유지 ──────────────────


def test_layer2_failure_with_preflight_none_stays_low(monkeypatch):
    """preflight=None + Layer 2 raise → confidence='low' 박제."""
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    tp = _FakeTechniqueProfile(key_moments=_moments_monotonic_violation())
    report = compute_force_signals(
        frames,
        pole,
        body_profile,
        angles=angles,
        fps=expected["fps"],
        motion_id=expected["motion_id"],
        preflight_label_gate_passed=None,
        technique_profile=tp,
    )
    for b in report.phase_boundaries:
        assert b.confidence == "low"


# ── 5. preflight=True + Layer 2 failure → 'medium' 박제 유지 (ceiling) ─────


def test_layer2_failure_with_preflight_passed_stays_medium(monkeypatch):
    """preflight=True + Layer 2 raise → confidence='medium' 박제 (preflight ceiling 박제
    그대로, NOT 'high' promote).
    """
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _angles(len(frames))
    tp = _FakeTechniqueProfile(key_moments=_moments_monotonic_violation())
    report = compute_force_signals(
        frames,
        pole,
        body_profile,
        angles=angles,
        fps=expected["fps"],
        motion_id=expected["motion_id"],
        preflight_label_gate_passed=True,
        technique_profile=tp,
    )
    for b in report.phase_boundaries:
        # ceiling 박제 'medium' 박제 유지 — except 분기 박제 promote X.
        assert b.confidence == "medium", (
            f"preflight=True + Layer 2 except → ceiling 'medium' 박제 유지 강제. "
            f"confidence={b.confidence!r}"
        )
