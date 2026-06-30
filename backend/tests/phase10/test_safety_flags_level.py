"""Phase 10 Wave 0 — D-06 레벨 대비 무리 firing-rule (Mode 1 전용).

GREEN = 정답이 [] (stub). xfail(strict) = 플래그 SHOULD fire (10-04 flip).

per Plan 10-01 Task 3 + CONTEXT D-06.
"""

from __future__ import annotations

import numpy as np
import pytest

from sunity_shared.analysis.safety_flags import compute_safety_flags


def _call(*, mode, report, experience, reference_level, profile=None, dimension_scores=None):
    a = np.full((40, 8), 150.0, dtype=float)
    return compute_safety_flags(
        angles=a,
        keypoints_4ch=None,
        force_signals_report=report,
        dimension_scores=dimension_scores or {},
        reference_angles=None,
        experience=experience,
        reference_level=reference_level,
        mode=mode,
        profile=profile,
    )


# ── GREEN: no-flag 불변식 ────────────────────────────────────────────────────


def test_mode3_level_no_flag(high_control_loss_report, hold_profile) -> None:
    """Mode 3 는 move 난이도 미상 → D-06 미적용 → advanced-ref × beginner 라도 no-flag."""
    assert _call(
        mode="mode3",
        report=high_control_loss_report,
        experience="beginner",
        reference_level="advanced",
        profile=hold_profile,
    ) == []


def test_level_without_control_loss_no_flag(low_control_loss_report, hold_profile) -> None:
    """레벨 mismatch 라도 통제 상실 없으면 no-flag (D-02 조합)."""
    assert _call(
        mode="mode1",
        report=low_control_loss_report,
        experience="beginner",
        reference_level="advanced",
        profile=hold_profile,
    ) == []


# ── xfail-strict: positive (10-04 에서 flip) ────────────────────────────────


@pytest.mark.xfail(strict=True, reason="D-06 level-mismatch firing rule lands in 10-04")
def test_mode1_level_mismatch_with_control_loss_flags(high_control_loss_report, hold_profile) -> None:
    """Mode 1 + advanced reference × beginner experience + 통제 상실 → 플래그 발화."""
    flags = _call(
        mode="mode1",
        report=high_control_loss_report,
        experience="beginner",
        reference_level="advanced",
        profile=hold_profile,
    )
    assert any(f.flag_type == "level_mismatch" for f in flags)
