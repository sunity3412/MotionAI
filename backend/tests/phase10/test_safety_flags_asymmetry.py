"""Phase 10 Wave 3 — D-03 asymmetry firing-rule (DTW-aligned reference-anchored).

10-04 flip: positive cases now fire the real `_asymmetry_flag`. No-flag invariants
(equal asymmetry, no-reference, timing-shifted DTW cancellation, no-control-loss,
wrong-phase) stay GREEN per D-02 LOCAL+TEMPORAL AND-gate + reference-anchored excess.

per Plan 10-04 Task 1 + CONTEXT D-03/D-02/D-07.
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis.safety_flags import compute_safety_flags

# JOINT_KEYS = (le, re, ls, rs, lh, rh, lk, rk) → left_hip=4, left_knee=6.
JOINT_LEFT_HIP_IDX = 4
JOINT_LEFT_KNEE_IDX = 6


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


def test_student_more_asymmetric_without_control_loss_no_flag(low_control_loss_report, hold_profile) -> None:
    """D-02: student 가 더 비대칭이어도 통제 상실 없으면 no-flag (자세 단독 금지)."""
    a = np.full((40, 8), 150.0, dtype=float)
    a[:, JOINT_LEFT_KNEE_IDX] = 90.0
    ref = np.full((40, 8), 150.0, dtype=float)
    assert _call(angles=a, report=low_control_loss_report, reference_angles=ref, profile=hold_profile) == []


def test_student_more_asymmetric_wrong_phase_no_flag(wrong_phase_knee_control_loss_report, hold_profile) -> None:
    """phase-co-location: 무릎 통제 상실이 hold 가 아닌 entry phase 에만 → no-flag
    (asymmetry hold window 의 phase 와 미겹침, _phase_for_window 게이트)."""
    a = np.full((40, 8), 150.0, dtype=float)
    a[:, JOINT_LEFT_KNEE_IDX] = 90.0
    ref = np.full((40, 8), 150.0, dtype=float)
    assert _call(angles=a, report=wrong_phase_knee_control_loss_report, reference_angles=ref, profile=hold_profile) == []


# ── 10-04 positive (real implementation) ─────────────────────────────────────


def test_student_more_asymmetric_with_control_loss_flags(high_control_loss_report, hold_profile) -> None:
    """student 가 reference 보다 유의하게 더 비대칭 + 통제 상실 → 플래그 발화."""
    a = np.full((40, 8), 150.0, dtype=float)
    a[:, JOINT_LEFT_KNEE_IDX] = 90.0  # 좌측 무릎만 크게 굽힘 → 좌우 편차 큼 (ref 대칭)
    ref = np.full((40, 8), 150.0, dtype=float)
    flags = _call(angles=a, report=high_control_loss_report, reference_angles=ref, profile=hold_profile)
    assert any(f.flag_type == "asymmetry" for f in flags)


def test_asymmetry_max_pair_drives_flag(high_control_loss_report, hold_profile) -> None:
    """MAX aggregation — 한 pair(좌우 고관절)만 심하게 비대칭이고 나머지 pair 는 대칭이어도
    그 worst pair 가 플래그를 발화시키고 audit 문자열이 책임 pair 를 명시한다."""
    a = np.full((40, 8), 150.0, dtype=float)
    a[:, JOINT_LEFT_HIP_IDX] = 95.0  # 좌측 고관절만 큰 편차 (다른 pair 대칭)
    ref = np.full((40, 8), 150.0, dtype=float)
    flags = _call(angles=a, report=high_control_loss_report, reference_angles=ref, profile=hold_profile)
    asym = [f for f in flags if f.flag_type == "asymmetry"]
    assert asym, "worst pair(고관절) 가 플래그를 발화시켜야 함"
    assert "고관절" in asym[0].posture_condition, "책임 pair 가 audit 문자열에 명시되어야 함"
