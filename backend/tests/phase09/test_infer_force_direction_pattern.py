"""Phase 9 Wave 1 T2 — infer_force_direction_pattern 6 signal detection tests.

per Plan 09-02 Task T2 / D-09-A1~A5 / Open Q 1~3 / Pitfall 1~5.

Coverage:
  - 6 signal detection (axis_tilt / pelvis_drop / late_contact / high_jitter /
    high_jerk / abnormal_release)
  - axis warning ignore (3 per-metric + 1 report-tier — R4 iter-3)
  - phase 미인식 fallback (phase_unavailable_for_inference)
  - 0-finding fallback (no_significant_force_pattern_signal)
  - Confidence 산식 (low/low / high/high / min)
  - rotate pattern 미산출 (Open Q 1)
  - boundary cases (IPSF tolerance 20° strict / jitter 8.0 strict / jerk 5000 strict)
  - pelvis_drop None guard (R4 iter-3)
  - contact-only finding cf=0.3 capped when axis missing (R11 conservative v1)
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.force_pattern import (
    _AXIS_IGNORE_WARNINGS_PER_METRIC,
    _AXIS_IGNORE_WARNINGS_REPORT,
    _CONFIDENCE_TO_FACTOR,
    _IPSF_TOLERANCE_DEG,
    ForcePatternFinding,
    ForcePatternInference,
    _detect_pelvis_drop,
    fallback_body,
    infer_force_direction_pattern,
)

from .conftest import (
    _make_axis_metric,
    _make_contact_metric,
    _make_force_signals_report,
    _make_phase_boundary,
    _make_stability_metric,
)


# ── 6 signal detection — ON 조건만 만족 / 다른 5 OFF ──────────────────────


def _baseline_axis(phase: str = "lock") -> object:
    """axis raw tilt 0 (안전한 baseline)."""
    return _make_axis_metric(
        phase=phase, shoulder_tilt=0.0, hip_tilt=0.0, confidence="high"
    )


def _baseline_stab(phase: str = "lock") -> object:
    return _make_stability_metric(
        phase=phase, jitter_score=0.0, jerk_score=0.0, confidence="high"
    )


def _baseline_contact(phase: str = "lock") -> object:
    return _make_contact_metric(
        phase=phase, estimated_stable=True, near_pole_ratio=1.0, confidence="high"
    )


def test_axis_tilt_signal_emits_release_finding() -> None:
    """axis_tilt ON @ lock — shoulder=30 > 20°."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(
            _make_axis_metric(
                phase="lock", shoulder_tilt=30.0, hip_tilt=10.0, confidence="high"
            ),
        ),
        stability_metrics=(_baseline_stab("lock"),),
        contact_metrics=(_baseline_contact("lock"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    assert len(result.findings) >= 1
    axis_finding = next(
        (f for f in result.findings if f.source_signal == "axis_tilt"), None
    )
    assert axis_finding is not None
    assert axis_finding.pattern == "release"
    assert axis_finding.joint_hint == "몸 중심"


def test_pelvis_drop_signal_emits_release_finding() -> None:
    """pelvis_drop ON @ entry — hip=22, shoulder=5 → hip > 20 AND (22-5)=17 > 10.

    NOTE: shoulder/hip < IPSF_TOL=20 으로 axis_tilt 가 함께 발화하지 않게 fixture
    박제 (axis_tilt 와 pelvis_drop 모두 pattern='release' + phase 동일 → dedup
    되므로 pelvis 단독 발화로 단위 검증). hip=22 → axis_tilt 의 max(5,22)=22 >
    20 도 통과 — 양쪽 signal 모두 발화. dedup 후 score tie-break (axis_tilt vs
    pelvis_drop 둘 다 base 0.72 × cf 동일) → axis_tilt 가 candidates list 안 더
    먼저 들어가서 sort stable 로 win. pelvis 단독 검증을 위해 hip 만 임계 통과
    + shoulder 도 임계 통과 안 시키는 axis_tilt OFF 박제 필요.

    실제 fixture: hip=22, shoulder=0 → axis_tilt: max(0,22)=22 > 20 → ON.
    pelvis_drop: 22 > 20 AND (22-0)=22 > 10 → ON. 둘 다 same (release, entry) →
    dedup. axis_tilt 가 list 첫 번째 detector 라서 결과 candidates[0]. 그래서
    pelvis 검증 X.

    해결: axis_tilt 가 발화하지 않도록 fixture 박제 — hip/shoulder 양쪽 다 ≤
    20°. 그런데 pelvis 룰은 hip > 20° 강제. 이 모순 = D-09-A1 룰 정합: pelvis
    가 발화하는 모든 시나리오에서 axis_tilt 도 발화한다. dedup 결과는 의도된
    동작. 본 test 는 finding 결과 안 'release@entry' 가 존재하면 PASS (pelvis
    가 axis_tilt 에 dedup 우선순위에 잠겨도 detection 룰 자체는 검증됨).

    단독 pelvis_drop detection 단위 검증은 _detect_pelvis_drop 직접 호출 test
    로 처리.
    """
    # _detect_pelvis_drop 직접 호출 — 단독 detection 룰 검증.
    from sunity_shared.analysis.force_pattern import _detect_pelvis_drop

    axis = _make_axis_metric(
        phase="entry", shoulder_tilt=10.0, hip_tilt=30.0, confidence="high"
    )
    findings = _detect_pelvis_drop(axis, "entry", cf=1.0, mode_context="mode1")
    assert len(findings) == 1
    assert findings[0].pattern == "release"
    assert findings[0].source_signal == "pelvis_drop"
    assert findings[0].joint_hint == "엉덩이 관절"


def test_late_contact_signal_emits_brace_finding() -> None:
    """late_contact ON @ lock — estimated_stable=False."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(_baseline_axis("lock"),),
        stability_metrics=(_baseline_stab("lock"),),
        contact_metrics=(
            _make_contact_metric(
                phase="lock", estimated_stable=False, confidence="high"
            ),
        ),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    late_finding = next(
        (f for f in result.findings if f.source_signal == "late_contact"), None
    )
    assert late_finding is not None
    assert late_finding.pattern == "brace"
    assert late_finding.joint_hint == "허벅지 안쪽"


def test_high_jitter_signal_emits_unknown_finding() -> None:
    """high_jitter ON @ hold — jitter_score=10.0 > 8.0."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="hold"),),
        axis_metrics=(_baseline_axis("hold"),),
        stability_metrics=(
            _make_stability_metric(
                phase="hold", jitter_score=10.0, jerk_score=0.0, confidence="high"
            ),
        ),
        contact_metrics=(_baseline_contact("hold"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    jitter_finding = next(
        (f for f in result.findings if f.source_signal == "high_jitter"), None
    )
    assert jitter_finding is not None
    assert jitter_finding.pattern == "unknown"
    assert jitter_finding.joint_hint is None


def test_high_jerk_signal_emits_unknown_finding() -> None:
    """high_jerk ON @ transition — jerk_score=6000 > 5000."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="transition"),),
        axis_metrics=(_baseline_axis("transition"),),
        stability_metrics=(
            _make_stability_metric(
                phase="transition",
                jitter_score=0.0,
                jerk_score=6000.0,
                confidence="high",
            ),
        ),
        contact_metrics=(_baseline_contact("transition"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    jerk_finding = next(
        (f for f in result.findings if f.source_signal == "high_jerk"), None
    )
    assert jerk_finding is not None
    assert jerk_finding.pattern == "unknown"
    assert jerk_finding.joint_hint is None


def test_abnormal_release_signal_emits_release_finding() -> None:
    """abnormal_release ON @ hold — warning 'abnormal_release_during_hold'."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="hold"),),
        axis_metrics=(_baseline_axis("hold"),),
        stability_metrics=(_baseline_stab("hold"),),
        contact_metrics=(
            _make_contact_metric(
                phase="hold",
                estimated_stable=True,
                warnings=("abnormal_release_during_hold",),
                confidence="high",
            ),
        ),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    rel_finding = next(
        (f for f in result.findings if f.source_signal == "abnormal_release"), None
    )
    assert rel_finding is not None
    assert rel_finding.pattern == "release"
    assert rel_finding.joint_hint == "등 근육"


# ── Axis warning ignore (R4 per-metric tier) ─────────────────────────────


@pytest.mark.parametrize(
    "warning",
    sorted(_AXIS_IGNORE_WARNINGS_PER_METRIC),
)
def test_axis_warning_ignore_rule_blocks_axis_tilt(warning: str) -> None:
    """per-axisMetric warnings ∈ {phase_8_1_wave_0_transitional, tilt_unavailable,
    tilt_thresholds_fallback} 시 axis 계열 finding 미emit + umbrella warning
    'axis_signal_unavailable' 추가.
    """
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(
            _make_axis_metric(
                phase="lock",
                shoulder_tilt=30.0,
                hip_tilt=10.0,
                warnings=(warning,),
                confidence="high",
            ),
        ),
        stability_metrics=(_baseline_stab("lock"),),
        contact_metrics=(_baseline_contact("lock"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    axis_findings = [
        f
        for f in result.findings
        if f.source_signal in ("axis_tilt", "pelvis_drop")
    ]
    assert axis_findings == []
    assert "axis_signal_unavailable" in result.warnings


def test_axis_report_warning_blocks_all_phases() -> None:
    """top-level 'axis_metric_transitional' → 모든 phase axis 계열 finding
    0회 + umbrella warning emit.
    """
    report = _make_force_signals_report(
        warnings=("axis_metric_transitional",),
        phase_boundaries=(
            _make_phase_boundary(phase="lock"),
            _make_phase_boundary(phase="hold"),
        ),
        axis_metrics=(
            _make_axis_metric(
                phase="lock", shoulder_tilt=30.0, hip_tilt=10.0, confidence="high"
            ),
            _make_axis_metric(
                phase="hold", shoulder_tilt=10.0, hip_tilt=30.0, confidence="high"
            ),
        ),
        stability_metrics=(_baseline_stab("lock"), _baseline_stab("hold")),
        contact_metrics=(_baseline_contact("lock"), _baseline_contact("hold")),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    axis_findings = [
        f
        for f in result.findings
        if f.source_signal in ("axis_tilt", "pelvis_drop")
    ]
    assert axis_findings == []
    assert "axis_signal_unavailable" in result.warnings


def test_axis_blocked_blocks_pelvis_drop_too() -> None:
    """axis warning 시 pelvis_drop 도 함께 차단 (axis 계열 일괄 skip)."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="entry"),),
        axis_metrics=(
            _make_axis_metric(
                phase="entry",
                shoulder_tilt=10.0,
                hip_tilt=30.0,
                warnings=("tilt_unavailable",),
                confidence="high",
            ),
        ),
        stability_metrics=(_baseline_stab("entry"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    pelvis = [f for f in result.findings if f.source_signal == "pelvis_drop"]
    assert pelvis == []


def test_axis_blocked_does_not_block_stability_or_contact() -> None:
    """axis warning 시 stability/contact detector 는 정상 동작."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="transition"),),
        axis_metrics=(
            _make_axis_metric(
                phase="transition",
                shoulder_tilt=30.0,
                hip_tilt=10.0,
                warnings=("tilt_unavailable",),
                confidence="high",
            ),
        ),
        stability_metrics=(
            _make_stability_metric(
                phase="transition",
                jitter_score=0.0,
                jerk_score=6000.0,
                confidence="high",
            ),
        ),
        contact_metrics=(_baseline_contact("transition"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    axis = [
        f
        for f in result.findings
        if f.source_signal in ("axis_tilt", "pelvis_drop")
    ]
    assert axis == []
    jerk = [f for f in result.findings if f.source_signal == "high_jerk"]
    assert len(jerk) == 1


# ── Phase 미인식 fallback (D-09-A4) ──────────────────────────────────────


def test_phase_unavailable_fallback() -> None:
    """phase_boundaries=(lock,) 1 phase 만 박제 → 4 phase missing → umbrella
    warning 'phase_unavailable_for_inference' 단일 emit. lock signal 모두 OFF →
    findings 0 + 'no_significant_force_pattern_signal' 도 함께 emit.
    """
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(_baseline_axis("lock"),),
        stability_metrics=(_baseline_stab("lock"),),
        contact_metrics=(_baseline_contact("lock"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    assert result.findings == []
    assert "phase_unavailable_for_inference" in result.warnings
    # 중복 제거 확인 — 4 phase missing 이어도 1 회만 emit.
    count = result.warnings.count("phase_unavailable_for_inference")
    assert count == 1
    assert "no_significant_force_pattern_signal" in result.warnings


# ── 0-finding fallback (D-09-B4 / Open Q 3) ─────────────────────────────


def test_no_signal_emits_fallback() -> None:
    """모든 phase 박제 + 모든 metric 임계 미만 → 0 finding + 'low' + fallback."""
    phases = ("entry", "lock", "transition", "final_shape", "hold")
    report = _make_force_signals_report(
        phase_boundaries=tuple(_make_phase_boundary(phase=p) for p in phases),
        axis_metrics=tuple(_baseline_axis(p) for p in phases),
        stability_metrics=tuple(_baseline_stab(p) for p in phases),
        contact_metrics=tuple(_baseline_contact(p) for p in phases),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    assert result.findings == []
    assert result.overall_confidence == "low"
    assert "no_significant_force_pattern_signal" in result.warnings
    # fallback body helper 가 정상 반환 (interpretation 본문은 frontend 책임).
    assert isinstance(fallback_body(), str)
    assert "강사와 함께 확인" in fallback_body()


# ── Confidence 산식 (D-09-A5) ────────────────────────────────────────────


def test_confidence_formula_low_low() -> None:
    """base axis_tilt 0.72 × cf=min(low=0.3, low=0.3)=0.3 → 0.216."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(
            _make_axis_metric(
                phase="lock", shoulder_tilt=30.0, hip_tilt=10.0, confidence="low"
            ),
        ),
        stability_metrics=(
            _make_stability_metric(
                phase="lock", jitter_score=0.0, jerk_score=0.0, confidence="low"
            ),
        ),
        contact_metrics=(_baseline_contact("lock"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    axis = next(f for f in result.findings if f.source_signal == "axis_tilt")
    assert axis.confidence == pytest.approx(0.216, abs=1e-6)


def test_confidence_formula_high_high() -> None:
    """base 0.72 × cf=1.0 → 0.72."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(
            _make_axis_metric(
                phase="lock", shoulder_tilt=30.0, hip_tilt=10.0, confidence="high"
            ),
        ),
        stability_metrics=(
            _make_stability_metric(
                phase="lock", jitter_score=0.0, jerk_score=0.0, confidence="high"
            ),
        ),
        contact_metrics=(_baseline_contact("lock"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    axis = next(f for f in result.findings if f.source_signal == "axis_tilt")
    assert axis.confidence == pytest.approx(0.72, abs=1e-6)


def test_confidence_formula_takes_min() -> None:
    """axisMetric high + stabilityMetric low → cf=0.3 (min). high_jitter base 0.63
    × 0.3 = 0.189.
    """
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="hold"),),
        axis_metrics=(
            _make_axis_metric(
                phase="hold", shoulder_tilt=0.0, hip_tilt=0.0, confidence="high"
            ),
        ),
        stability_metrics=(
            _make_stability_metric(
                phase="hold", jitter_score=10.0, jerk_score=0.0, confidence="low"
            ),
        ),
        contact_metrics=(_baseline_contact("hold"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    jitter = next(f for f in result.findings if f.source_signal == "high_jitter")
    assert jitter.confidence == pytest.approx(0.189, abs=1e-6)


# ── Open Q 1 — rotate pattern 미산출 회귀 가드 ────────────────────────────


def test_no_rotate_pattern_emitted() -> None:
    """6 signal 모두 ON 시에도 findings 안 pattern='rotate' 0 회."""
    phases = ("entry", "lock", "transition", "final_shape", "hold")
    report = _make_force_signals_report(
        phase_boundaries=tuple(_make_phase_boundary(phase=p) for p in phases),
        axis_metrics=tuple(
            _make_axis_metric(
                phase=p, shoulder_tilt=30.0, hip_tilt=30.0, confidence="high"
            )
            for p in phases
        ),
        stability_metrics=tuple(
            _make_stability_metric(
                phase=p, jitter_score=10.0, jerk_score=6000.0, confidence="high"
            )
            for p in phases
        ),
        contact_metrics=tuple(
            _make_contact_metric(
                phase=p,
                estimated_stable=False,
                warnings=("abnormal_release_during_hold",),
                confidence="high",
            )
            for p in phases
        ),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    for f in result.findings:
        assert f.pattern != "rotate", (
            f"Open Q 1 회귀 — rotate pattern 검출됨: {f}"
        )


# ── Boundary 검증 (strict 부등호) ─────────────────────────────────────────


def test_axis_tilt_boundary_at_ipsf_tolerance() -> None:
    """shoulder_tilt = 20.0 (=tol) → 미emit. = 20.1 → emit."""
    base = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(
            _make_axis_metric(
                phase="lock",
                shoulder_tilt=_IPSF_TOLERANCE_DEG,
                hip_tilt=0.0,
                confidence="high",
            ),
        ),
        stability_metrics=(_baseline_stab("lock"),),
    )
    result_eq = infer_force_direction_pattern(base, motion_id=None, mode_context="mode1")
    assert [f for f in result_eq.findings if f.source_signal == "axis_tilt"] == []

    over = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(
            _make_axis_metric(
                phase="lock",
                shoulder_tilt=20.1,
                hip_tilt=0.0,
                confidence="high",
            ),
        ),
        stability_metrics=(_baseline_stab("lock"),),
    )
    result_over = infer_force_direction_pattern(over, motion_id=None, mode_context="mode1")
    assert any(f.source_signal == "axis_tilt" for f in result_over.findings)


def test_pelvis_drop_requires_both_conditions() -> None:
    """(hip=25, sh=20): diff=5 not > 10 → 미emit.
    (hip=21, sh=10): hip > 20 + diff=11 > 10 → emit.
    (hip=18, sh=5): hip not > 20 → 미emit.

    _detect_pelvis_drop 직접 호출 — pipeline dedup (axis_tilt vs pelvis_drop
    동일 (release, phase)) 와 분리해 룰 자체만 검증.
    """
    cases = [
        (25.0, 20.0, False),
        (21.0, 10.0, True),
        (18.0, 5.0, False),
    ]
    for hip, shoulder, expect_emit in cases:
        axis = _make_axis_metric(
            phase="entry",
            shoulder_tilt=shoulder,
            hip_tilt=hip,
            confidence="high",
        )
        findings = _detect_pelvis_drop(
            axis, "entry", cf=1.0, mode_context="mode1"
        )
        if expect_emit:
            assert len(findings) == 1, (
                f"(hip={hip}, sh={shoulder}) emit 기대했으나 0 finding"
            )
            assert findings[0].pattern == "release"
            assert findings[0].source_signal == "pelvis_drop"
        else:
            assert findings == [], (
                f"(hip={hip}, sh={shoulder}) 미emit 기대했으나 finding 발생: {findings}"
            )


def test_pelvis_drop_skips_when_tilt_none() -> None:
    """R4 iter-3 회귀 — axis.shoulder_tilt / hip_tilt is None → []. TypeError X."""
    axis = _make_axis_metric(
        phase="entry",
        shoulder_tilt=None,
        hip_tilt=None,
        confidence="low",
        warnings=(),
    )
    # _detect_pelvis_drop 직접 호출 — TypeError raise 차단 검증.
    findings = _detect_pelvis_drop(axis, "entry", cf=1.0, mode_context="mode1")
    assert findings == []

    # 동일 fixture 가 infer_force_direction_pattern 통과 시에도 crash X.
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="entry"),),
        axis_metrics=(axis,),
        stability_metrics=(_baseline_stab("entry"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    pelvis = [f for f in result.findings if f.source_signal == "pelvis_drop"]
    assert pelvis == []


def test_late_contact_only_in_lock_phase() -> None:
    """late_contact 는 phase='lock' 만 emit. entry 에서는 미emit."""
    report_entry = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="entry"),),
        axis_metrics=(_baseline_axis("entry"),),
        stability_metrics=(_baseline_stab("entry"),),
        contact_metrics=(
            _make_contact_metric(
                phase="entry", estimated_stable=False, confidence="high"
            ),
        ),
    )
    result_entry = infer_force_direction_pattern(
        report_entry, motion_id=None, mode_context="mode1"
    )
    late_entry = [
        f for f in result_entry.findings if f.source_signal == "late_contact"
    ]
    assert late_entry == []

    report_lock = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(_baseline_axis("lock"),),
        stability_metrics=(_baseline_stab("lock"),),
        contact_metrics=(
            _make_contact_metric(
                phase="lock", estimated_stable=False, confidence="high"
            ),
        ),
    )
    result_lock = infer_force_direction_pattern(
        report_lock, motion_id=None, mode_context="mode1"
    )
    late_lock = [
        f for f in result_lock.findings if f.source_signal == "late_contact"
    ]
    assert len(late_lock) == 1


def test_high_jitter_threshold_exact_boundary() -> None:
    """jitter_score = 8.0 → 미emit (strict `>`). 8.1 → emit."""
    eq = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="hold"),),
        axis_metrics=(_baseline_axis("hold"),),
        stability_metrics=(
            _make_stability_metric(
                phase="hold", jitter_score=8.0, jerk_score=0.0, confidence="high"
            ),
        ),
    )
    result_eq = infer_force_direction_pattern(eq, motion_id=None, mode_context="mode1")
    assert [f for f in result_eq.findings if f.source_signal == "high_jitter"] == []

    over = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="hold"),),
        axis_metrics=(_baseline_axis("hold"),),
        stability_metrics=(
            _make_stability_metric(
                phase="hold", jitter_score=8.1, jerk_score=0.0, confidence="high"
            ),
        ),
    )
    result_over = infer_force_direction_pattern(over, motion_id=None, mode_context="mode1")
    assert any(f.source_signal == "high_jitter" for f in result_over.findings)


def test_high_jerk_threshold_exact_boundary() -> None:
    """jerk_score = 5000.0 → 미emit. 5001 → emit."""
    eq = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="transition"),),
        axis_metrics=(_baseline_axis("transition"),),
        stability_metrics=(
            _make_stability_metric(
                phase="transition",
                jitter_score=0.0,
                jerk_score=5000.0,
                confidence="high",
            ),
        ),
    )
    result_eq = infer_force_direction_pattern(eq, motion_id=None, mode_context="mode1")
    assert [f for f in result_eq.findings if f.source_signal == "high_jerk"] == []

    over = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="transition"),),
        axis_metrics=(_baseline_axis("transition"),),
        stability_metrics=(
            _make_stability_metric(
                phase="transition",
                jitter_score=0.0,
                jerk_score=5001.0,
                confidence="high",
            ),
        ),
    )
    result_over = infer_force_direction_pattern(
        over, motion_id=None, mode_context="mode1"
    )
    assert any(f.source_signal == "high_jerk" for f in result_over.findings)


def test_abnormal_release_detected_from_contact_warnings() -> None:
    """contactMetric.warnings = ['abnormal_release_during_hold'] → 1 finding."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="hold"),),
        axis_metrics=(_baseline_axis("hold"),),
        stability_metrics=(_baseline_stab("hold"),),
        contact_metrics=(
            _make_contact_metric(
                phase="hold",
                estimated_stable=True,
                warnings=("abnormal_release_during_hold",),
                confidence="high",
            ),
        ),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    rel = [f for f in result.findings if f.source_signal == "abnormal_release"]
    assert len(rel) == 1
    assert rel[0].pattern == "release"
    assert rel[0].joint_hint == "등 근육"


# ── overall_confidence 단순 매핑 ─────────────────────────────────────────


def test_overall_confidence_thresholds() -> None:
    """top confidence ≥ 0.7 → 'high'; ≥ 0.4 → 'medium'; else 'low'.

    direct construct ForcePatternInference 대신 _overall_confidence_from_findings
    경계를 infer_force_direction_pattern 의 산출 confidence 로 검증한다.
    """
    from sunity_shared.analysis.force_pattern import (
        _overall_confidence_from_findings,
    )

    high_finding = ForcePatternFinding(
        pattern="release",
        phase="lock",
        source_signal="axis_tilt",
        reason="x",
        interpretation="정은지 선수 기준 패턴과 비교했을 때, x",
        confidence=0.8,
        joint_hint="몸 중심",
        warnings=[],
    )
    medium_finding = ForcePatternFinding(
        pattern="release",
        phase="lock",
        source_signal="axis_tilt",
        reason="x",
        interpretation="정은지 선수 기준 패턴과 비교했을 때, x",
        confidence=0.5,
        joint_hint="몸 중심",
        warnings=[],
    )
    low_finding = ForcePatternFinding(
        pattern="release",
        phase="lock",
        source_signal="axis_tilt",
        reason="x",
        interpretation="정은지 선수 기준 패턴과 비교했을 때, x",
        confidence=0.2,
        joint_hint="몸 중심",
        warnings=[],
    )
    assert _overall_confidence_from_findings([high_finding]) == "high"
    assert _overall_confidence_from_findings([medium_finding]) == "medium"
    assert _overall_confidence_from_findings([low_finding]) == "low"
    assert _overall_confidence_from_findings([]) == "low"


# ── R11 conservative v1 — contact-only finding cf=0.3 capped when axis missing


def test_contact_only_confidence_capped_when_axis_missing() -> None:
    """phase='lock', axis_metric is None, stab high, abnormal_release warning ON.

    cf = min(_CONFIDENCE_TO_FACTOR[None→'low']=0.3, stability=1.0) = 0.3.
    abnormal_release base=0.75 → confidence = 0.75 * 0.3 = 0.225.
    "axis 가 없으면 contact-only finding 도 cf=0.3 로 capped — Phase 9 v1
    conservative strategy (R11)."
    """
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        # axis_metrics 비움 — axis is None.
        axis_metrics=(),
        stability_metrics=(
            _make_stability_metric(
                phase="lock", jitter_score=0.0, jerk_score=0.0, confidence="high"
            ),
        ),
        contact_metrics=(
            _make_contact_metric(
                phase="lock",
                estimated_stable=True,
                warnings=("abnormal_release_during_hold",),
                confidence="high",
            ),
        ),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    rel = next(f for f in result.findings if f.source_signal == "abnormal_release")
    expected = 0.75 * _CONFIDENCE_TO_FACTOR["low"]  # 0.225
    assert rel.confidence == pytest.approx(expected, abs=1e-6)


# ── ForcePatternInference 산출 형식 확인 ─────────────────────────────────


def test_result_is_force_pattern_inference_instance() -> None:
    """infer_force_direction_pattern 반환 = ForcePatternInference dataclass."""
    report = _make_force_signals_report(
        phase_boundaries=(_make_phase_boundary(phase="lock"),),
        axis_metrics=(_baseline_axis("lock"),),
        stability_metrics=(_baseline_stab("lock"),),
        contact_metrics=(_baseline_contact("lock"),),
    )
    result = infer_force_direction_pattern(report, motion_id=None, mode_context="mode1")
    assert isinstance(result, ForcePatternInference)
    assert result.version == "1.0"
    assert result.mode_context == "mode1"
