"""Phase 10 — D-02 LOCAL+TEMPORAL AND-gate firing-rule contracts.

GREEN/xfail discipline: 정답이 [] 인 케이스는 stub 위에서 즉시 GREEN. 10-02 가
trunk(D-04) 규칙을 구현하면서 must-fire 케이스를 flip 한다.

per Plan 10-02 Task 1 + CONTEXT D-02/D-04.
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis.force_signals import (
    ForceSignalsReport,
    PhaseBoundary,
    StabilityMetric,
)
from sunity_shared.analysis.safety_flags import (
    _phase_for_window,
    compute_safety_flags,
)
from sunity_shared.analysis.skeleton import NUM_JOINTS


def _call(angles, report, *, mode="mode1", profile=None, dimension_scores=None, reference_angles=None):
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


def _moderate_reference(value: float = 120.0, t: int = 40) -> np.ndarray:
    """중립(과신전 아님) 기준 각도 — student 의 극단 신전이 이 기준 대비 초과로 발화."""
    return np.full((t, NUM_JOINTS), value, dtype=float)


# ── 인라인 force_signals 빌더 (conftest 미변경 — wrong-phase-hip 케이스용) ───


def _boundary(phase: str, s: int, e: int) -> PhaseBoundary:
    return PhaseBoundary(
        phase=phase,
        start_frame_idx=s,
        end_frame_idx=e,
        start_ms=s * 33,
        end_ms=e * 33,
        confidence="medium",
        source="heuristic",
    )


def _metric(phase: str, severity: str, parts: list[str]) -> StabilityMetric:
    return StabilityMetric(
        phase=phase,
        jitter_score=10.0,
        jerk_score=900.0,
        hold_stability_score=40.0,
        unstable_body_parts=list(parts),
        severity=severity,
        confidence="medium",
        warnings=[],
    )


def _make_report(boundaries, metrics) -> ForceSignalsReport:
    return ForceSignalsReport(
        version="1.0",
        overall_confidence="medium",
        warnings=[],
        phase_boundaries=list(boundaries),
        axis_metrics=[],
        stability_metrics=list(metrics),
        contact_metrics=[],
    )


# ── GREEN: 정답이 [] 인 no-flag 불변식 ──────────────────────────────────────


def test_elite_posture_alone_no_flag(elite_angles, low_control_loss_report, hold_profile) -> None:
    """극단 자세 + 통제 상실 없음 → 플래그 없음 (정은지 위양성 방어 — headline gate)."""
    assert _call(elite_angles, low_control_loss_report, profile=hold_profile) == []


def test_deterministic(elite_angles, high_control_loss_report, hold_profile) -> None:
    """동일 입력 → 동일 출력 (결정론, D-01) — reference 있는 positive 경로에서도."""
    ref = _moderate_reference()
    a = _call(elite_angles, high_control_loss_report, profile=hold_profile, reference_angles=ref)
    b = _call(elite_angles, high_control_loss_report, profile=hold_profile, reference_angles=ref)
    assert a == b
    assert len(a) >= 1


def test_posture_without_control_loss_no_flag(elite_angles, low_control_loss_report, hold_profile) -> None:
    """극단 자세 + reference 대비 초과지만 통제 상실 없음 → 플래그 없음 (D-02 AND-gate)."""
    assert _call(
        elite_angles, low_control_loss_report, profile=hold_profile,
        reference_angles=_moderate_reference(),
    ) == []


def test_and_gate_requires_temporal_colocation(elite_angles, window_disjoint_report, hold_profile) -> None:
    """HIGH-1: posture 는 hold window 에 있으나 불안정은 disjoint window(entry)+다른
    관절(right_knee)에만 → temporal+locality 미충족 → 플래그 없음 (D-02)."""
    assert _call(
        elite_angles, window_disjoint_report, profile=hold_profile,
        reference_angles=_moderate_reference(),
    ) == []


def test_trunk_timing_shifted_same_extension_no_flag(
    timing_shifted_student_angles, timing_shifted_reference_angles,
    high_control_loss_report, hold_profile,
) -> None:
    """HIGH-A: student 와 reference 가 SAME 극단 신전을 SHIFTED timing 으로 가질 때,
    DTW path-정렬이 두 극단을 짝지어 reference-anchored excess 를 상쇄 → 통제 상실이
    co-located 여도 플래그 없음 (raw same-index 라면 위양성)."""
    assert _call(
        timing_shifted_student_angles, high_control_loss_report, profile=hold_profile,
        reference_angles=timing_shifted_reference_angles,
    ) == []


def test_and_gate_wrong_phase_no_flag(elite_angles, hold_profile) -> None:
    """HIGH-1 phase-gate: posture 는 hold phase, hip-local 불안정은 entry phase 에만 →
    temporal co-location 미충족 → 플래그 없음."""
    report = _make_report(
        [_boundary("entry", 0, 10), _boundary("hold", 10, 40)],
        [_metric("entry", "high", ["left_hip"])],
    )
    assert _call(
        elite_angles, report, profile=hold_profile, reference_angles=_moderate_reference(),
    ) == []


# ── _phase_for_window 단위 검증 (MEDIUM-1) ──────────────────────────────────


def test_phase_for_window_overlap() -> None:
    """≥50% overlap boundary 의 phase 매핑 + <50%/빈 boundary 시 None no-op."""
    bounds = [_boundary("entry", 0, 10), _boundary("hold", 10, 40)]
    # window (10,40) 은 hold 와 100% overlap → 'hold'.
    assert _phase_for_window(bounds, 10, 40) == "hold"
    # window (0,20) vs hold(15,40): overlap 5 < 0.5*20=10 → None (phase 미확정 no-op).
    assert _phase_for_window([_boundary("hold", 15, 40)], 0, 20) is None
    # 빈 boundary → None.
    assert _phase_for_window([], 0, 20) is None


# ── must-fire (10-02 에서 flip) ─────────────────────────────────────────────


def test_posture_and_control_loss_emits_flag(elite_angles, high_control_loss_report, hold_profile) -> None:
    """극단 신전(reference 대비 초과) + SAME-phase hip-local 통제 상실 → trunk 플래그 발화."""
    flags = _call(
        elite_angles, high_control_loss_report, profile=hold_profile,
        reference_angles=_moderate_reference(),
    )
    assert len(flags) >= 1
    trunk = flags[0]
    assert trunk.flag_type == "trunk_hyperextension"
    assert trunk.body_region == "허리"
    assert trunk.mode_scope == "both"
