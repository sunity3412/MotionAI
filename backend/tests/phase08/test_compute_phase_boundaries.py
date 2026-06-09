"""Plan 08-02 Task 2 — Layer 1 휴리스틱 + preflight gate confidence 단위 test.

REVIEWS R4 정합:
  - Layer 1 default confidence = 'low' (preflight gate 검증 전)
  - preflight_label_gate_passed=True  → 'medium' 승급
  - preflight_label_gate_passed=False → 'low' + 'preflight_label_gate_failed'
  - preflight_label_gate_passed=None  → 'low' + 'preflight_gate_pending'

REVIEWS Cycle 2 NEW HIGH #2 정합:
  _layer1_confidence_from_preflight helper 3-state 검증.
"""

from __future__ import annotations

import numpy as np
import pytest

from sunity_shared.analysis.force_signals import (
    _layer1_confidence_from_preflight,
    compute_phase_boundaries,
)

from .fixtures._fixture_builders import build_clean_invert


def _build_angles(num_frames: int, num_joints: int = 8) -> np.ndarray:
    """Layer 1 휴리스틱 입력용 합성 각도 (T, J) — NaN 없음, low velocity."""
    return np.full((num_frames, num_joints), 90.0, dtype=float)


def test_layer1_only_with_clean_invert():
    """build_clean_invert 입력 → 5 phase boundary 반환 (or single hold fallback)."""
    frames, pole, profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=None,
    )
    assert isinstance(boundaries, list)
    assert len(boundaries) >= 1
    # 모든 phase 가 PhaseBoundary 객체.
    for b in boundaries:
        assert b.start_frame_idx <= b.end_frame_idx
        assert b.source in ("heuristic", "gemini_assisted", "heuristic_fallback")


def test_layer1_default_confidence_low_without_preflight_gate():
    """preflight_label_gate_passed=None (default) → confidence='low' 강제."""
    frames, pole, profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        # preflight_label_gate_passed=None (default)
    )
    for b in boundaries:
        assert b.confidence == "low"
        assert b.preflight_label_gate_passed is None


def test_layer1_warning_preflight_gate_pending_when_none():
    """preflight_label_gate_passed=None → helper 가 'preflight_gate_pending' warning 반환."""
    confidence, warnings = _layer1_confidence_from_preflight(None)
    assert confidence == "low"
    assert "preflight_gate_pending" in warnings


def test_layer1_confidence_medium_when_preflight_gate_passed_true():
    """preflight_label_gate_passed=True → 'medium' 승급."""
    frames, pole, profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=True,
    )
    for b in boundaries:
        assert b.confidence == "medium"
        assert b.preflight_label_gate_passed is True


def test_layer1_warning_preflight_label_gate_failed_when_false():
    """preflight_label_gate_passed=False → 'low' + 'preflight_label_gate_failed' warning."""
    confidence, warnings = _layer1_confidence_from_preflight(False)
    assert confidence == "low"
    assert "preflight_label_gate_failed" in warnings


def test_layer1_confidence_from_preflight_helper_three_state():
    """3-state matrix — True/False/None."""
    assert _layer1_confidence_from_preflight(True) == ("medium", [])
    assert _layer1_confidence_from_preflight(False) == (
        "low",
        ["preflight_label_gate_failed"],
    )
    assert _layer1_confidence_from_preflight(None) == (
        "low",
        ["preflight_gate_pending"],
    )


def test_video_too_short_falls_back_to_single_hold():
    """T < 10 frames → single 'hold' phase + warning source."""
    frames, pole, profile, _ = build_clean_invert()
    short_frames = frames[:5]
    angles = _build_angles(len(short_frames))
    boundaries = compute_phase_boundaries(
        short_frames,
        pole,
        profile,
        angles,
        motion_id="ref-invert",
        fps=9.0,
    )
    assert len(boundaries) == 1
    assert boundaries[0].phase == "hold"


def test_heavy_occlusion_returns_low_confidence():
    """all-NaN angles → single 'hold' + low confidence."""
    frames, pole, profile, _ = build_clean_invert()
    angles = np.full((len(frames), 8), np.nan, dtype=float)
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        profile,
        angles,
        motion_id="ref-invert",
        fps=9.0,
    )
    assert len(boundaries) >= 1
    for b in boundaries:
        assert b.confidence == "low"


def test_layer2_hook_not_invoked_when_gemini_extractor_none():
    """gemini_extractor=None → Layer 1 단독 (heuristic source).

    Plan 08-03 가 Layer 2 활성화. 본 plan 의 본체는 Layer 1 only.
    """
    frames, pole, profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        gemini_extractor=None,  # Plan 08-03 활성화 전 None.
    )
    for b in boundaries:
        # heuristic or heuristic_fallback (motion_id 미인식 시) — gemini_assisted 영구 X (본 plan).
        assert b.source in ("heuristic", "heuristic_fallback")
