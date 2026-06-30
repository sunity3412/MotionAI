"""Phase 10 Wave 3 — D-06 레벨 대비 무리 firing-rule (Mode 1 전용).

10-04 flip: positive cases now fire the real `_level_mismatch_flag`. No-flag
invariants (Mode-3, level-without-control, spoof-omit) stay GREEN. Severity scales
with BOTH rank-gap AND instability so a gap of exactly 1 does not over-warn.

per Plan 10-04 Task 2 + CONTEXT D-06/D-02.
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis.safety_flags import compute_safety_flags

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


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


def test_spoofed_experience_no_flag(high_control_loss_report, hold_profile) -> None:
    """위조/비-enum experience → enum guard → level flag omit (fail-safe, T-10-02)."""
    assert _call(
        mode="mode1",
        report=high_control_loss_report,
        experience="grandmaster",  # 비-enum 위조 값
        reference_level="advanced",
        profile=hold_profile,
    ) == []


def test_none_experience_no_flag(high_control_loss_report, hold_profile) -> None:
    """experience=None → level flag omit (fail-safe)."""
    assert _call(
        mode="mode1",
        report=high_control_loss_report,
        experience=None,
        reference_level="advanced",
        profile=hold_profile,
    ) == []


def test_equal_level_no_flag(high_control_loss_report, hold_profile) -> None:
    """gap=0 (advanced × advanced) → posture 미충족 → no-flag."""
    assert _call(
        mode="mode1",
        report=high_control_loss_report,
        experience="advanced",
        reference_level="advanced",
        profile=hold_profile,
    ) == []


# ── 10-04 positive (real implementation) ─────────────────────────────────────


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


def test_level_severity_scales_with_gap(
    medium_control_loss_report, high_control_loss_report, hold_profile
) -> None:
    """severity 가 rank-gap×instability 로 스케일 — gap=1+medium 은 gap=2+high 보다 낮다
    (gap=1 over-warn 방지)."""
    gap1 = _call(
        mode="mode1",
        report=medium_control_loss_report,
        experience="intermediate",
        reference_level="advanced",
        profile=hold_profile,
    )
    gap2 = _call(
        mode="mode1",
        report=high_control_loss_report,
        experience="beginner",
        reference_level="advanced",
        profile=hold_profile,
    )
    g1 = next(f for f in gap1 if f.flag_type == "level_mismatch")
    g2 = next(f for f in gap2 if f.flag_type == "level_mismatch")
    assert _SEVERITY_RANK[g1.severity] < _SEVERITY_RANK[g2.severity]
