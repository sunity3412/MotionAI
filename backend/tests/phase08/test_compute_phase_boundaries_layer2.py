"""Plan 08-03 Task 1 — Layer 2 wiring + Cycle 2 NEW HIGH #2 차단 test.

신설 8 test:
  1. test_layer2_uses_technique_profile_key_moments
  2. test_force_signals_layer2_enabled_env_required (REVIEWS R7 — Phase 5 와 분리)
  3. test_layer1_layer2_agreement_high_confidence
  4. test_layer1_layer2_disagreement_major_falls_back_to_layer1
  5. test_layer2_runtime_error_falls_back_to_layer1
  6. test_layer2_no_duplicate_gemini_call (REVIEWS R6)
  7. test_layer2_failure_does_not_exceed_preflight_ceiling (REVIEWS Cycle 2 NEW HIGH #2)
  8. test_layer2_success_capped_by_preflight_ceiling (REVIEWS Cycle 2 NEW HIGH #2)
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import numpy as np
import pytest

from sunity_shared.analysis.force_signals import compute_phase_boundaries

from .fixtures._fixture_builders import build_clean_invert


def _build_angles(num_frames: int, num_joints: int = 8) -> np.ndarray:
    return np.full((num_frames, num_joints), 90.0, dtype=float)


@dataclass(frozen=True)
class _FakeKeyMoment:
    """test 박제 fake KeyMoment — real KeyMoment dataclass 의 frame_index 박제 mirror."""
    moment_key: str
    timestamp_seconds: float
    frame_index: int
    confidence: float = 0.9


@dataclass
class _FakeTechniqueProfile:
    """force_signals 가 key_moments attribute 만 박제 사용 → dict-like fake OK."""
    key_moments: tuple


def _moments_close_to_layer1(num_frames: int) -> tuple:
    """5 phase 박제 균등 분할 박제 Layer 1 boundary 박제 매우 가까운 moments — agreement 'high' 박제.

    Layer 1 박제 균등 분할:
      entry [0, T/5), lock [T/5, 2T/5), transition [2T/5, 3T/5),
      final_shape [3T/5, 4T/5), hold [4T/5, T).

    setup → entry 끝점 / lock 시작 (~T/5)
    hold → final_shape 끝점 / hold 시작 (~4T/5)
    release → hold 끝점 (~T)
    """
    e1 = num_frames // 5  # ~12 for T=60
    e4 = 4 * num_frames // 5  # ~48 for T=60
    return (
        _FakeKeyMoment("setup", e1 / 9.0, e1),
        _FakeKeyMoment("hold", e4 / 9.0, e4),
        _FakeKeyMoment("release", (num_frames - 1) / 9.0, num_frames - 1),
    )


def _moments_disagree_major(num_frames: int) -> tuple:
    """Layer 1 박제 boundary 박제 매우 멀리 떨어진 moments — disagreement major (>5 frame).

    setup → e1 + 10 frame shift → max_diff > 5.
    """
    e1 = num_frames // 5
    e4 = 4 * num_frames // 5
    return (
        _FakeKeyMoment("setup", (e1 + 10) / 9.0, e1 + 10),  # disagreement major
        _FakeKeyMoment("hold", e4 / 9.0, e4),
        _FakeKeyMoment("release", (num_frames - 1) / 9.0, num_frames - 1),
    )


# ── 1. Layer 2 활성 — technique_profile.key_moments 박제 reuse ──────────────


def test_layer2_uses_technique_profile_key_moments(monkeypatch):
    """FORCE_SIGNALS_LAYER2_ENABLED=1 + technique_profile.key_moments != None
    → Layer 2 활성 + source='gemini_assisted'.
    """
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    moments = _moments_close_to_layer1(len(frames))
    tp = _FakeTechniqueProfile(key_moments=moments)
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        body_profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=True,
        technique_profile=tp,
    )
    assert any(b.source == "gemini_assisted" for b in boundaries), (
        f"Layer 2 활성 박제 실패 — sources={[b.source for b in boundaries]}"
    )


# ── 2. FORCE_SIGNALS_LAYER2_ENABLED env required (REVIEWS R7) ──────────────


def test_force_signals_layer2_enabled_env_required(monkeypatch):
    """FORCE_SIGNALS_LAYER2_ENABLED unset → Layer 2 비활성 (key_moments 있어도)."""
    monkeypatch.delenv("FORCE_SIGNALS_LAYER2_ENABLED", raising=False)
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    moments = _moments_close_to_layer1(len(frames))
    tp = _FakeTechniqueProfile(key_moments=moments)
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        body_profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=True,
        technique_profile=tp,
    )
    # env unset → Layer 2 비활성 → source 'gemini_assisted' 박제 0.
    assert all(b.source != "gemini_assisted" for b in boundaries), (
        f"env unset 박제 Layer 2 활성 X 박제 강제 — sources={[b.source for b in boundaries]}"
    )


# ── 3. Layer 1 / 2 agreement — high confidence ─────────────────────────────


def test_layer1_layer2_agreement_high_confidence(monkeypatch):
    """boundary 차이 <=2 frame + preflight_label_gate_passed=True → 'high' + gemini_assisted."""
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    moments = _moments_close_to_layer1(len(frames))
    tp = _FakeTechniqueProfile(key_moments=moments)
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        body_profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=True,  # ceiling='medium'
        technique_profile=tp,
    )
    # agreement 'high' 박제이지만 ceiling 'medium' 박제 → effective='medium'.
    # (next test 박제 preflight=True 박제 검증, 본 test 는 source 박제만 검증.)
    assert any(b.source == "gemini_assisted" for b in boundaries)


# ── 4. Disagreement major → Layer 1 fallback ───────────────────────────────


def test_layer1_layer2_disagreement_major_falls_back_to_layer1(monkeypatch):
    """boundary 차이 >5 frame → effective 'low' → Layer 1 fallback + source='heuristic'."""
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    moments = _moments_disagree_major(len(frames))
    tp = _FakeTechniqueProfile(key_moments=moments)
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        body_profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=True,
        technique_profile=tp,
    )
    # disagreement_major → effective_confidence='low' → Layer 1 박제 + source='heuristic'.
    assert all(b.source != "gemini_assisted" for b in boundaries), (
        f"disagreement major 박제 Layer 1 fallback 박제 강제 — "
        f"sources={[b.source for b in boundaries]}"
    )


# ── 5. Layer 2 runtime error → Layer 1 fallback ────────────────────────────


def test_layer2_runtime_error_falls_back_to_layer1(monkeypatch):
    """key_moments 박제 monotonic 위반 (5 phase 박제 start_ms 순서 위반) → ValueError
    raise → except 분기 → Layer 1 + ceiling confidence + source='heuristic'.

    setup → e1+10 = 22, but Layer 1 박제 transition_start = 24 (2*60//5). e1 (entry
    끝) 박제 22 = lock_start, transition_start 박제 24 박제 — lock 박제 [22, 24) (2 frame OK).
    여기서 hold 박제 시 final_shape 끝 박제 박제 박제 36 (3*60//5), 박제 hold_start 박제
    moments_by_key["hold"] 박제 = 8 → hold_start=8, 박제 final_shape 박제 [36, 8) 박제
    monotonic 위반 (start=36 >= end=8) → ValueError raise.
    """
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    # hold 박제 frame_index 박제 final_shape Layer 1 start 보다 작은 값 → final_shape
    # 박제 boundary start >= end 위반 → ValueError raise.
    bad_moments = (
        _FakeKeyMoment("setup", 1.0, 12),  # lock_start = 12
        _FakeKeyMoment("hold", 0.8, 8),    # hold_start = 8 < final_shape_start (36) → 박제 final_shape [36, 8) 박제 위반
        _FakeKeyMoment("release", 6.0, 55),
    )
    tp = _FakeTechniqueProfile(key_moments=bad_moments)
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        body_profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=True,
        technique_profile=tp,
    )
    # except 분기 박제 fallback → Layer 1 박제 source='heuristic' (NOT gemini_assisted).
    assert all(b.source != "gemini_assisted" for b in boundaries), (
        f"Layer 2 ValueError 박제 except 박제 Layer 1 fallback 박제 강제 — "
        f"sources={[b.source for b in boundaries]}"
    )


# ── 6. Layer 2 — recognizer 중복 호출 영구 차단 (REVIEWS R6) ───────────────


def test_layer2_no_duplicate_gemini_call(monkeypatch):
    """force_signals 가 GeminiTechniqueRecognizer.recognize 박제 호출 X — 신규
    GeminiMomentExtractor singleton 영구 차단 박제 (REVIEWS R6).

    technique_profile.key_moments 박제 reuse — recognizer.recognize 박제 신규 호출 0.
    """
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    moments = _moments_close_to_layer1(len(frames))
    tp = _FakeTechniqueProfile(key_moments=moments)

    # mock recognizer 박제 — force_signals 가 본 mock 박제 호출 X 강제.
    fake_recognizer = MagicMock()
    fake_recognizer.recognize = MagicMock()

    compute_phase_boundaries(
        frames,
        pole,
        body_profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=True,
        technique_profile=tp,
    )
    assert fake_recognizer.recognize.call_count == 0, (
        f"force_signals 박제 recognizer.recognize 박제 신규 호출 영구 차단 위반 — "
        f"call_count={fake_recognizer.recognize.call_count}"
    )


# ── 7. Layer 2 except 박제 preflight ceiling 위로 promote 영구 차단 (Cycle 2 #2) ──


def test_layer2_failure_does_not_exceed_preflight_ceiling(monkeypatch):
    """REVIEWS Cycle 2 NEW HIGH #2 차단 — Layer 2 except 분기는 preflight gate
    ceiling 박제 그대로 박제 (Cycle 1 박제 hardcoded 'medium' 박제 영구 제거).

    preflight_label_gate_passed=None (default) + Layer 2 except → confidence='low'
    (NOT 'medium').
    """
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    bad_moments = (
        _FakeKeyMoment("setup", 1.0, 12),
        _FakeKeyMoment("hold", 5.0, 48),
        _FakeKeyMoment("release", 4.0, 30),  # monotonic 위반
    )
    tp = _FakeTechniqueProfile(key_moments=bad_moments)
    boundaries = compute_phase_boundaries(
        frames,
        pole,
        body_profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=None,  # ceiling='low'
        technique_profile=tp,
    )
    # Cycle 2 NEW HIGH #2 차단 검증 — except 분기 박제 ceiling ('low') 박제 유지 강제.
    for b in boundaries:
        assert b.confidence == "low", (
            f"REVIEWS Cycle 2 NEW HIGH #2 위반 — Layer 2 except 박제 preflight "
            f"ceiling 위로 promote 박제 영구 차단. confidence={b.confidence!r}"
        )


# ── 8. Layer 2 success — preflight ceiling 위로 promote 영구 차단 ──────────


def test_layer2_success_capped_by_preflight_ceiling(monkeypatch):
    """REVIEWS Cycle 2 NEW HIGH #2 차단 — Layer 2 success 분기도 _min_confidence
    박제 ceiling 박제 적용.

    case 1: preflight=None + Layer 2 agreement='high' → effective='low' (ceiling 박제).
    case 2: preflight=True + Layer 2 agreement='high' → effective='high' (ceiling 박제 해제).
    """
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    frames, pole, body_profile, expected = build_clean_invert()
    angles = _build_angles(len(frames))
    moments = _moments_close_to_layer1(len(frames))  # agreement 'high' 박제
    tp = _FakeTechniqueProfile(key_moments=moments)

    # case 1: preflight=None → ceiling='low' → effective='low' → Layer 1 fallback.
    boundaries_none = compute_phase_boundaries(
        frames,
        pole,
        body_profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=None,
        technique_profile=tp,
    )
    for b in boundaries_none:
        assert b.confidence == "low", (
            f"ceiling='low' 박제 위로 Layer 2 agreement 'high' 박제 promote 박제 영구 "
            f"차단. confidence={b.confidence!r}"
        )
    # effective='low' 시 Layer 1 박제 fallback 박제 source='heuristic' 강제.
    assert all(b.source != "gemini_assisted" for b in boundaries_none)

    # case 2: preflight=True → ceiling='medium' → effective=min('high', 'medium')='medium'.
    boundaries_true = compute_phase_boundaries(
        frames,
        pole,
        body_profile,
        angles,
        motion_id=expected["motion_id"],
        fps=expected["fps"],
        preflight_label_gate_passed=True,
        technique_profile=tp,
    )
    # ceiling='medium' 박제 → effective='medium' (NOT 'high' promote).
    # source='gemini_assisted' 박제 (effective != 'low').
    assert any(b.source == "gemini_assisted" for b in boundaries_true)
    for b in boundaries_true:
        # ceiling 박제 medium 위로 promote 영구 차단 — 'medium' 박제 강제 (NOT 'high').
        assert b.confidence == "medium", (
            f"ceiling='medium' 박제 위로 promote 박제 영구 차단. "
            f"confidence={b.confidence!r}"
        )
