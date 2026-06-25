"""Phase 24 ND-07 게이트 단위 테스트 — 게이트가 planted violation 을 잡고 valid breakdown
(unavailable fallback record 포함)을 PASS 하는지 결정적 검증. AWS 불필요.

test_kismam.py header/AWS-free convention 박제. assert_gates 의 importable 게이트 함수
(check_traceability / check_monotonicity / check_determinism /
check_criterion_selection_determinism / check_generalization)를 직접 호출 — 전체 CLI 안 돌림.

모든 단언은 방향/구조 — 보유 sweep 수치 타깃 아님(curve-fit 금지,
[[scoring-redesign-must-generalize-no-overfit]]). 특히 generalization 은 수치 ≥95 bound 가
없음을 명시 단언(MEDIUM-1) + artifact 부재 시 SKIPPED(HIGH-4).
"""

import importlib.util
import pathlib

import pytest

from sunity_shared.analysis import deduction_engine, ipsf_criteria, vision_veto


# ── assert_gates 를 파일 경로로 로드(evals/ 는 패키지 아님) ────────────────────


def _load_gates():
    path = (pathlib.Path(__file__).resolve().parents[1]
            / "evals" / "phase24" / "assert_gates.py")
    spec = importlib.util.spec_from_file_location("phase24_assert_gates", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gates = _load_gates()


# ── fixtures (test_deduction_engine.py 형상 박제) ────────────────────────────


def _ctx(differences):
    return {"supported_differences": list(differences)}


def _diff(body_part, fault_state, severity="moderate", **extra):
    d = {
        "body_part": body_part,
        "correct_state": "",
        "fault_state": fault_state,
        "severity": severity,
        "approx_angle_deviation_deg": 0,
    }
    d.update(extra)
    return d


def _available_quant():
    return vision_veto.VisionQuantificationResult(quantificationStatus="available")


def _unavailable_quant():
    return vision_veto.VisionQuantificationResult(
        quantificationStatus="unavailable", warnings=("inputs_missing",)
    )


def _tally(measured, ctx, *, dimension_overall=80, baseline_kind="hip_line",
           quantification=None):
    if quantification is None:
        quantification = _available_quant()
    return deduction_engine.tally(
        quantification, ctx,
        dimension_overall=dimension_overall,
        measured_deviations=measured,
        dimension_scores=None,
        baseline_kind=baseline_kind,
    )


def _valid_breakdown():
    return _tally({"leg_extension": 40.0}, _ctx([_diff("무릎", "굽음")]))


def _fallback_breakdown():
    # quantification_unavailable → single fallback record (MEDIUM-1).
    return _tally({"leg_extension": 40.0}, _ctx([_diff("무릎", "굽음")]),
                  dimension_overall=62, quantification=_unavailable_quant())


# ── traceability ─────────────────────────────────────────────────────────────


def test_traceability_gate_catches_mismatch():
    # valid → no failure.
    assert gates.check_traceability([_valid_breakdown()]) == []
    # planted: final ≠ max(0, round(100 + Σ points)).
    bad = _valid_breakdown().to_dict()
    bad["final"] = bad["final"] + 7  # tamper
    fails = gates.check_traceability([bad])
    assert any("final" in f for f in fails)


def test_traceability_gate_passes_fallback_record():
    # MEDIUM-1: quantification_unavailable fallback PASSES traceability (not an exception).
    b = _fallback_breakdown()
    fb = [r for r in b.records if r.criterion == "dimension_overall_fallback"]
    assert len(fb) == 1
    assert b.fallback == "quantification_unavailable"
    # 100 + Σ points == final holds on the fallback path too.
    assert 100 + sum(r.points for r in b.records) == b.final
    assert gates.check_traceability([b]) == []


def test_traceability_gate_catches_null_rule():
    # coverage-gap must be 0-deduction, NOT a null-rule penalty: ruleId=None with points<0.
    b = _valid_breakdown().to_dict()
    assert b["records"], "expected at least one record"
    b["records"][0]["ruleId"] = None
    b["records"][0]["points"] = -5.0
    fails = gates.check_traceability([b])
    assert any("ruleId" in f for f in fails)


def test_traceability_gate_catches_nonnumeric_baseline():
    b = _valid_breakdown().to_dict()
    b["records"][0]["baselineValue"] = None
    fails = gates.check_traceability([b])
    assert any("baselineValue" in f for f in fails)


# ── monotonicity ─────────────────────────────────────────────────────────────


def test_monotonicity_gate_passes_real_engine():
    # 실 엔진(고정 criterion set sweep) → 단조(inversion 0).
    assert gates.check_monotonicity() == []


def test_monotonicity_gate_catches_inversion(monkeypatch):
    # 비단조 sweep 을 만들기 위해 tally 를 deviation↑ → final↑ 로 뒤집는 stub 으로 교체.
    real_breakdown_cls = deduction_engine.DeductionBreakdown

    call = {"n": 0}

    def _bad_tally(quant, ctx, **kw):
        # 호출마다 final 을 증가시켜 단조성을 깬다(criterion set 은 고정으로 가정).
        call["n"] += 1
        return real_breakdown_cls(
            baseline=100, records=(), final=call["n"], coverage_gaps=(), fallback=None,
        )

    monkeypatch.setattr(gates.deduction_engine, "tally", _bad_tally)
    fails = gates.check_monotonicity()
    assert any("inversion" in f for f in fails)


# ── determinism (math) ───────────────────────────────────────────────────────


def test_determinism_gate_passes_real_engine():
    assert gates.check_determinism() == []


def test_determinism_gate_catches_drift(monkeypatch):
    # 같은 입력에 매 호출 다른 breakdown 을 내는 stub → drift 검출.
    real_breakdown_cls = deduction_engine.DeductionBreakdown
    call = {"n": 0}

    def _drifting_tally(quant, ctx, **kw):
        call["n"] += 1
        return real_breakdown_cls(
            baseline=100, records=(), final=100 - call["n"],
            coverage_gaps=(), fallback=None,
        )

    monkeypatch.setattr(gates.deduction_engine, "tally", _drifting_tally)
    fails = gates.check_determinism()
    assert any("byte-identical" in f for f in fails)


# ── criterion-selection determinism ──────────────────────────────────────────


def test_criterion_selection_determinism_passes():
    # severity/telemetry 무관 필드 변주 → 동일 selection.
    assert gates.check_criterion_selection_determinism() == []


def test_criterion_selection_determinism_catches_severity_drift(monkeypatch):
    # router 가 severity 를 읽게 만드는 stub → selection 이 severity 에 의존 → FAIL.
    real_router = ipsf_criteria.criteria_for_fault

    def _severity_sensitive_router(fault_key, supported_difference, measured_deviations):
        diff = supported_difference or {}
        if str(diff.get("severity")) == "major":
            return ("leg_extension", "arm_extension")  # major 면 다른 set
        return real_router(fault_key, supported_difference, measured_deviations)

    monkeypatch.setattr(gates.ipsf_criteria, "criteria_for_fault",
                        _severity_sensitive_router)
    fails = gates.check_criterion_selection_determinism()
    assert any("selection" in f for f in fails)


# ── generalization (structural + artifact-gated) ─────────────────────────────


def _artifact_pair(*, fault_dev, success_dev, criterion="leg_extension"):
    """phase24_breakdowns.json 멤버 형상 — correct/fault 각각 deductionBreakdown records."""
    def _member(dev):
        if dev is None:
            return {"records": []}
        return {"records": [{
            "criterion": criterion,
            "measuredValue": 180.0 - dev,
            "baselineValue": 180.0,
            "deviation": dev,
            "ruleId": "leg_extension_over_tol_linear",
            "points": -round(dev, 1),
            "unit": "deg",
            "ipsfAnchor": "19-IPSF",
            "source": "geometry",
            "deviationSource": "ipsf_absolute",
        }]}
    return {"correct": _member(success_dev), "fault": _member(fault_dev)}


def test_generalization_structural_directional():
    # fault shortfall > success shortfall in same named criterion → PASS (no real failure).
    arti = {"pdshape": _artifact_pair(fault_dev=45.0, success_dev=None)}
    res = gates.check_generalization(breakdowns=arti)
    real_fails = [r for r in res if not r.startswith("SKIPPED")]
    assert real_fails == []
    # 명시: 수치 ≥95 bound 가 아니라 same-criterion structural shortfall 비교 — fault_dev 가
    # success 대비 더 크면 통과(점수 무관).

    # inverted: fault shortfall ≤ success shortfall → structural false-negative FAIL.
    inverted = {"pdshape": _artifact_pair(fault_dev=10.0, success_dev=40.0)}
    res2 = gates.check_generalization(breakdowns=inverted)
    real_fails2 = [r for r in res2 if not r.startswith("SKIPPED")]
    assert any("false-negative" in f or "larger shortfall" in f for f in real_fails2)


def test_generalization_no_numeric_95_bound():
    # 게이트 소스에 수치 ≥95 bound 가 없어야 한다(MEDIUM-1 — curve-fit 금지).
    src = pathlib.Path(gates.__file__).read_text(encoding="utf-8")
    import re
    assert not re.search(r">=\s*~?95|>= ?95", src), "numeric >=95 bound leaked into pure gate"


def test_generalization_skipped_when_artifact_absent():
    # HIGH-4: artifact 부재 → SKIPPED marker(실패 아님). 존재하지 않는 경로로 강제.
    res = gates.check_generalization(breakdowns=None)
    # _BREAKDOWN_ARTIFACT 가 실제로 없으면 SKIPPED.
    if not gates._BREAKDOWN_ARTIFACT.exists():
        assert res == ["SKIPPED (phase24 breakdown fixture absent)"]
    # 빈 breakdowns 도 SKIPPED.
    assert gates.check_generalization(breakdowns={}) == [
        "SKIPPED (phase24 breakdown fixture absent)"
    ]


def test_full_gate_run_exits_zero_when_artifact_absent():
    # 전체 main() — artifact 부재 시에도 합성 게이트 PASS → exit 0.
    if not gates._BREAKDOWN_ARTIFACT.exists():
        assert gates.main() == 0
