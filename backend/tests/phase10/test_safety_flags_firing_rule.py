"""Phase 10 Wave 0 — D-02 AND-gate firing-rule contracts.

GREEN/xfail discipline: 정답이 [] 인 케이스는 stub 위에서 즉시 GREEN. 플래그가
SHOULD fire 인 케이스만 xfail(strict=True) — 해당 wave 에서 flip.

per Plan 10-01 Task 3 + CONTEXT D-02.
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.safety_flags import compute_safety_flags


def _call(angles, report, *, mode="mode1", profile=None, dimension_scores=None):
    return compute_safety_flags(
        angles=angles,
        keypoints_4ch=None,
        force_signals_report=report,
        dimension_scores=dimension_scores or {},
        reference_angles=None,
        experience=None,
        reference_level=None,
        mode=mode,
        profile=profile,
    )


# ── GREEN: 정답이 [] 인 no-flag 불변식 ──────────────────────────────────────


def test_elite_posture_alone_no_flag(elite_angles, low_control_loss_report, hold_profile) -> None:
    """극단 자세 + 통제 상실 없음 → 플래그 없음 (정은지 위양성 방어)."""
    assert _call(elite_angles, low_control_loss_report, profile=hold_profile) == []


def test_deterministic(elite_angles, low_control_loss_report, hold_profile) -> None:
    """동일 입력 → 동일 출력 (결정론, D-01)."""
    a = _call(elite_angles, low_control_loss_report, profile=hold_profile)
    b = _call(elite_angles, low_control_loss_report, profile=hold_profile)
    assert a == b == []


def test_posture_without_control_loss_no_flag(elite_angles, low_control_loss_report, hold_profile) -> None:
    assert _call(elite_angles, low_control_loss_report, profile=hold_profile) == []


def test_and_gate_requires_temporal_colocation(elite_angles, window_disjoint_report, hold_profile) -> None:
    """HIGH-1: posture 는 hold window 에 있으나 불안정은 disjoint window(entry)에만 →
    temporal-colocation 미충족 → 플래그 없음 (D-02 locality+temporal)."""
    assert _call(elite_angles, window_disjoint_report, profile=hold_profile) == []


# ── xfail-strict: 플래그가 SHOULD fire (10-02 에서 flip) ─────────────────────


@pytest.mark.xfail(strict=True, reason="trunk AND-gate firing rule lands in 10-02")
def test_posture_and_control_loss_emits_flag(elite_angles, high_control_loss_report, hold_profile) -> None:
    """극단 자세 + SAME-window 통제 상실 → 플래그 발화 (D-02 조합)."""
    flags = _call(elite_angles, high_control_loss_report, profile=hold_profile)
    assert len(flags) >= 1
