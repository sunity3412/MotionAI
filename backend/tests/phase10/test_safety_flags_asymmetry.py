"""Phase 10 Wave 0 — D-03 asymmetry firing-rule (reference-anchored).

GREEN = 정답이 [] (stub). xfail(strict) = 플래그 SHOULD fire (10-04 flip).

per Plan 10-01 Task 3 + CONTEXT D-03.
"""

from __future__ import annotations

import numpy as np
import pytest

from sunity_shared.analysis.safety_flags import compute_safety_flags


def _call(*, angles, report, reference_angles, mode="mode1", profile=None, dimension_scores=None):
    return compute_safety_flags(
        angles=angles,
        keypoints_4ch=None,
        force_signals_report=report,
        dimension_scores=dimension_scores or {},
        reference_angles=reference_angles,
        experience=None,
        reference_level=None,
        mode=mode,
        profile=profile,
    )


# ── GREEN: no-flag 불변식 ────────────────────────────────────────────────────


def test_equal_asymmetry_no_flag(high_control_loss_report, hold_profile) -> None:
    """student 와 reference 의 좌우 비대칭이 동일 → reference-anchored excess 0 → no-flag."""
    a = np.full((40, 8), 150.0, dtype=float)
    ref = np.full((40, 8), 150.0, dtype=float)
    assert _call(angles=a, report=high_control_loss_report, reference_angles=ref, profile=hold_profile) == []


def test_no_reference_no_flag(high_control_loss_report, hold_profile) -> None:
    """reference_angles=None → 절대 좌우 비대칭은 v1 에서 플래그 안 함 (D-03) → no-flag."""
    a = np.full((40, 8), 150.0, dtype=float)
    assert _call(angles=a, report=high_control_loss_report, reference_angles=None, profile=hold_profile) == []


def test_timing_shifted_same_asymmetry_no_flag(timing_shifted_student_angles, timing_shifted_reference_angles, high_control_loss_report, hold_profile) -> None:
    """HIGH-A DTW-alignment negative — 같은 극단이 서로 다른 time offset 에 → DTW
    path-alignment 후 짝지어 excess 상쇄 → no-flag (raw same-index 비교가 아님)."""
    assert _call(
        angles=timing_shifted_student_angles,
        report=high_control_loss_report,
        reference_angles=timing_shifted_reference_angles,
        profile=hold_profile,
    ) == []


# ── xfail-strict: positive (10-04 에서 flip) ────────────────────────────────


@pytest.mark.xfail(strict=True, reason="D-03 asymmetry firing rule lands in 10-04")
def test_student_more_asymmetric_with_control_loss_flags(high_control_loss_report, hold_profile) -> None:
    """student 가 reference 보다 유의하게 더 비대칭 + 통제 상실 → 플래그 발화."""
    # 좌측 관절만 크게 굽힘 → 좌우 편차 큼 (reference 는 대칭).
    a = np.full((40, 8), 150.0, dtype=float)
    a[:, JOINT_LEFT_IDX] = 90.0
    ref = np.full((40, 8), 150.0, dtype=float)
    flags = _call(angles=a, report=high_control_loss_report, reference_angles=ref, profile=hold_profile)
    assert any(f.flag_type == "asymmetry" for f in flags)


# JOINT_KEYS index of a left-side joint (left_knee) for the asymmetry positive case.
JOINT_LEFT_IDX = 6  # JOINT_KEYS = (le, re, ls, rs, lh, rh, lk, rk) → left_knee = 6
