#!/usr/bin/env python3
"""Phase 24 투명 감점-합산 채점 ND-07 게이트 (pod-free, exit 0 = PASS).

박제 정신 (ND-07 — "정은지 95~100 은 RESULT, not a target"):
  · Phase 18 의 case-by-case 밴드 매니페스트(verdict-consistency / discriminate-margin)
    는 curve-fit 유발 매니페스트라 RETIRE 했다(phase18/assert_baseline.py). 대신 합성
    fixture 위에서 tally 가 추적가능/단조/결정적임을 Pod 없이 증명한다.
  · 객관성(D-06, [[analysis-objectivity-no-human-scores]]): 게이트는 사람 점수 라벨을
    절대 쓰지 않는다. 감점은 명명 편차 + 명명 규칙에서만 나온다. 합성 fixture 는
    엔지니어링 기하(합성 각/notch)일 뿐 보유 영상에 curve-fit 한 타깃이 아니다.

게이트 (importable 함수 — Plan 03 Task 2 가 직접 unit-test):
  1. check_traceability(breakdowns)        — 모든 −point 역산가능, final == max(0, round(100+Σpoints)).
  2. check_monotonicity()                   — 합성 편차 sweep → final 비증가(zero inversion),
                                              ACTIVATED CRITERION SET 고정.
  3. check_determinism()                    — MATH-determinism(같은 입력 → byte-identical breakdown),
                                              verdict cache(frame-pair hash) 조건부. Gemini 샘플링
                                              결정성 주장 아님.
  4. check_criterion_selection_determinism() — criterion SELECTION 이 supported_differences 의 순수
                                              함수(severity/telemetry 등 무관 필드 무시).
  5. check_generalization(pairs, breakdowns) — ARTIFACT-GATED(HIGH-4) + STRUCTURAL(MEDIUM-1).
                                              실 Pod-생성 phase24_breakdowns.json 이 있을 때만 실행,
                                              없으면 SKIPPED(실패 아님). 수치 ≥95 밴드 미적용.
  6. check_clean_residual(breakdowns)        — ABSOLUTE 잔차(ARTIFACT-GATED, HIGH-4). 정타(correct)
                                              멤버의 모든 measured-angle record 가 raw 편차
                                              ≤ 그 criterion 의 IPSF tolerance 로 역산돼야 한다.
                                              generalization 의 RELATIVE 속성(fault > success)이
                                              못 잡는 오염 정타(tolerance 초과 잔차)를 ABSOLUTE 로
                                              차단. artifact 없으면 SKIPPED(실패 아님).
  7. check_sensitivity()                     — above-cutoff metric-validity(합성, 항상 실행). elite-low
                                              만으로 metric validity 미증명 — 명백히 above-tolerance 인
                                              편차는 감점을 내고, deadzone(tolerance 미만) 편차는 안
                                              낸다(양방). 임계/margin 은 CRITERION_GROUPS tolerance
                                              에서만 파생(curve-fit 금지), 점수 밴드 미단언.

determinism scope 정직성:
  실제 Phase-18 drift 는 tally 수학이 아니라 Gemini 샘플링(다른 fault set → 다른 criterion
  selection)이었다. 그래서 (3)은 verdict cache 조건부 MATH-determinism, (4)는 criterion-
  SELECTION-determinism 으로 명시 분리한다.

monotonicity scope:
  단조성은 ACTIVATED CRITERION SET 이 고정일 때만 주장한다(criteria 선택은 sweep 동안
  불변). per-criterion min(raw, ipsf_cap)-before-sum 이 고정 set 의 global monotonicity 를
  보존(review-confirmed).

generalization scope (HIGH-4 + MEDIUM-1):
  phase18 6-페어 일반화는 실 Pod sweep 이 생성·커밋한 phase24_breakdowns.json 에만 돈다.
  STRUCTURAL: success 멤버는 records 부재 OR within-tolerance(추적가능 이유)면 PASS;
  fault 멤버는 같은 named criterion 에서 success 보다 strictly 큰 shortfall 이면 PASS.
  수치 ≥95 bound 는 순수 게이트에 절대 적용 안 함(curve-fit 유발 — slope/cap/tolerance 가
  [ASSUMED]). 수치 high-score 관측은 Task 3 Pod 체크포인트의 OBSERVATIONAL report;
  unseen+above-cutoff sensitivity set 이 생긴 뒤에만 hard gate 승격 가능. sensitivity set
  은 Pod-serial deferred.

exit 0 = PASS, non-zero = FAIL.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np  # NaN/Inf 가드 + finite 검사 (엔진과 동일 substrate)

_HERE = pathlib.Path(__file__).resolve().parent
# Lambda Layer(/opt/python) 미존재 로컬에서 sunity_shared import 경로 주입.
_LAYER = _HERE.parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

from sunity_shared.analysis import deduction_engine, ipsf_criteria, vision_veto  # noqa: E402

# phase18 fault-label 페어(일반화 게이트 입력 — 재사용, silent 밴드 금지).
_PHASE18 = _HERE.parents[0] / "phase18"
_PAIRS = _PHASE18 / "dataset" / "pairs.yaml"
# 실 Pod sweep 이 생성·커밋하는 일반화 artifact(HIGH-4 — 없으면 SKIPPED).
_BREAKDOWN_ARTIFACT = _HERE / "baseline" / "phase24_breakdowns.json"

_TOLERANCE_DEG = ipsf_criteria._ANGLE_TOLERANCE_DEG
_DEVIATION_SOURCES = {"ipsf_absolute", "reference_relative", "dimension_overall"}


# ── 합성 fixture 빌더 (보유 영상 무관 — 엔지니어링 기하) ────────────────────


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


def _notch_quant(reference_notches, student_notches, baseline_kind="hip_line",
                 keypoint="left_hand"):
    return vision_veto.VisionQuantificationResult(
        quantificationStatus="available",
        bodyRelativeNotches=[{
            "keypoint": keypoint,
            "student_notches": student_notches,
            "reference_notches": reference_notches,
            "delta_notches": round(student_notches - reference_notches, 4),
            "baseline_kind": baseline_kind,
            "source": "geometry",
        }],
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


def _synthetic_breakdowns():
    """추적성/직렬화 게이트가 도는 합성 breakdown set.

    엔진을 합성 측정 substrate 위에 돌려 실제 DeductionBreakdown 들을 만든다(엔진의
    역산 형식 그대로). 보유 영상 입력은 전혀 없다(HIGH-4 — phase18 tally 입력은 Pod
    artifact 이전엔 존재하지 않음). 명시적으로 fallback-path breakdown 도 포함해 그것이
    추적성을 PASS 하는지(100+Σpoints==final, MEDIUM-1) 검증한다.
    """
    out = []
    # leg bend (one criterion)
    out.append(_tally({"leg_extension": 40.0}, _ctx([_diff("무릎", "굽음")])))
    # multi-criterion
    out.append(_tally({"leg_extension": 50.0, "arm_extension": 30.0,
                       "split_angle": 45.0}, _ctx([_diff("무릎", "굽음")])))
    # huge deviation → final clamps to 0 (only clamp is max(0,…))
    out.append(_tally({"leg_extension": 500.0, "arm_extension": 500.0,
                       "split_angle": 500.0}, _ctx([_diff("무릎", "굽음")])))
    # within-tolerance → no records (honest 0)
    out.append(_tally({"leg_extension": 5.0}, _ctx([_diff("무릎", "굽음")])))
    # insufficient-reach (reference_relative)
    q = _notch_quant(reference_notches=3.0, student_notches=2.0)
    out.append(deduction_engine.tally(
        q, _ctx([_diff("손", "거리 부족")]), dimension_overall=80,
        measured_deviations={"body_relative_notches": q.bodyRelativeNotches},
        dimension_scores=None, baseline_kind="hip_line"))
    # UNAVAILABLE FALLBACK path (MEDIUM-1) — must PASS traceability, NOT be skipped.
    out.append(_tally({"leg_extension": 40.0}, _ctx([_diff("무릎", "굽음")]),
                      dimension_overall=62, quantification=_unavailable_quant()))
    return out


# ── (1) traceability ────────────────────────────────────────────────────────


def check_traceability(breakdowns) -> list[str]:
    """모든 record 역산가능 + final == max(0, round(100 + Σ records.points)).

    points 는 SIGNED NEGATIVE(HIGH-2 통합식). 각 record 는 non-null ruleId/criterion,
    finite measuredValue/deviation, 수치 baselineValue, deviationSource ∈ 허용집합,
    ipsfAnchor(CoP citation OR engineering_interpretation) 를 가진다. quantification_
    unavailable fallback record(criterion='dimension_overall_fallback', unit='score_delta',
    deviationSource='dimension_overall', baselineValue=100, MEDIUM-1)도 이 게이트를
    construction 으로 PASS — 예외가 아니라 100+Σpoints==final 이 fallback 경로에서도 성립.
    """
    failures: list[str] = []
    for i, b in enumerate(breakdowns):
        d = b.to_dict() if hasattr(b, "to_dict") else b
        records = d["records"]
        # 통합 signed-negative 합산식 — fallback 경로 포함.
        expected = max(0, round(100 + sum(r["points"] for r in records)))
        if d["final"] != expected:
            failures.append(
                f"[traceability] breakdown[{i}] final={d['final']} != "
                f"max(0, round(100 + Σpoints))={expected}"
            )
        for j, r in enumerate(records):
            tag = f"breakdown[{i}].records[{j}] ({r.get('criterion')})"
            if not r.get("ruleId"):
                failures.append(f"[traceability] {tag}: null/empty ruleId")
            if not r.get("criterion"):
                failures.append(f"[traceability] {tag}: null/empty criterion")
            mv = r.get("measuredValue")
            dv = r.get("deviation")
            if mv is None or not np.isfinite(float(mv)):
                failures.append(f"[traceability] {tag}: measuredValue not finite ({mv})")
            if dv is None or not np.isfinite(float(dv)):
                failures.append(f"[traceability] {tag}: deviation not finite ({dv})")
            bv = r.get("baselineValue")
            if bv is None or not np.isfinite(float(bv)):
                failures.append(f"[traceability] {tag}: baselineValue not numeric ({bv})")
            ds = r.get("deviationSource")
            if ds not in _DEVIATION_SOURCES:
                failures.append(
                    f"[traceability] {tag}: deviationSource={ds} not in {_DEVIATION_SOURCES}"
                )
            if not r.get("ipsfAnchor"):
                failures.append(f"[traceability] {tag}: missing ipsfAnchor")
            # coverage-gap 은 0-deduction 이어야 한다 — points<0 인데 ruleId=None 금지.
            if r.get("points", 0) < 0 and not r.get("ruleId"):
                failures.append(f"[traceability] {tag}: points<0 with null ruleId (band leak)")
    return failures


# ── (2) monotonicity (fixed activated criterion set) ──────────────────────────


def check_monotonicity() -> list[str]:
    """criterion 별 독립 sweep — 편차↑ → final 비증가(zero inversion).

    ACTIVATED CRITERION SET 고정(같은 fault_context / supported_differences 를 sweep 내내
    유지 → criteria_for_fault 선택 불변). per-criterion min(raw, ipsf_cap)-before-sum 이
    고정 set 의 global monotonicity 를 보존(review-confirmed). Pure, Pod 없음.
    """
    failures: list[str] = []
    sweeps = {
        "leg_extension": (lambda dev: ({"leg_extension": dev}, _ctx([_diff("무릎", "굽음")]))),
        "arm_extension": (lambda dev: ({"arm_extension": dev}, _ctx([_diff("팔꿈치", "굽음")]))),
        "split_angle": (lambda dev: ({"split_angle": dev}, _ctx([_diff("스플릿", "벌어짐 부족")]))),
    }
    deviations = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]
    for cid, build in sweeps.items():
        finals = []
        for dev in deviations:
            measured, ctx = build(dev)
            finals.append(_tally(measured, ctx).final)
        for k in range(1, len(finals)):
            if finals[k] > finals[k - 1]:
                failures.append(
                    f"[monotonicity] {cid}: inversion at dev={deviations[k]}° "
                    f"(final {finals[k - 1]} → {finals[k]} increased)"
                )
    # reach (insufficient-reach): student notches 줄일수록(=shortfall↑) final 비증가.
    reach_finals = []
    reach_devs = []
    for student in (3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0):
        q = _notch_quant(reference_notches=3.0, student_notches=student)
        b = deduction_engine.tally(
            q, _ctx([_diff("손", "거리 부족")]), dimension_overall=80,
            measured_deviations={"body_relative_notches": q.bodyRelativeNotches},
            dimension_scores=None, baseline_kind="hip_line")
        reach_finals.append(b.final)
        reach_devs.append(student)
    for k in range(1, len(reach_finals)):
        if reach_finals[k] > reach_finals[k - 1]:
            failures.append(
                f"[monotonicity] body_relative_reach: inversion at student={reach_devs[k]} "
                f"(final {reach_finals[k - 1]} → {reach_finals[k]} increased)"
            )
    return failures


# ── (3a) MATH-determinism (conditional on verdict cache) ──────────────────────


def check_determinism() -> list[str]:
    """MATH-determinism — 같은 stored 합성 quantification + 같은 supported_differences 를
    tally() 에 두 번 통과 → byte-identical breakdown(to_dict 직렬화 비교).

    이 게이트는 frame-pair hash 로 키된 verdict cache 조건부다 — Gemini 샘플링이
    결정적이라는 주장이 아니다(determinism scope 정직성). 같은 입력에 대해 엔진 수학이
    결정적임만 증명한다.
    """
    failures: list[str] = []
    cases = [
        ({"leg_extension": 40.0, "arm_extension": 30.0},
         _ctx([_diff("무릎", "굽음"), _diff("팔꿈치", "굽음")])),
        ({"split_angle": 45.0}, _ctx([_diff("스플릿", "벌어짐 부족")])),
    ]
    for idx, (measured, ctx) in enumerate(cases):
        first = json.dumps(_tally(measured, ctx).to_dict(), sort_keys=True)
        second = json.dumps(_tally(measured, ctx).to_dict(), sort_keys=True)
        if first != second:
            failures.append(
                f"[determinism] case[{idx}]: breakdown not byte-identical across two runs"
            )
    # reach 경로도 결정적.
    q = _notch_quant(reference_notches=3.0, student_notches=2.0)

    def _reach():
        return deduction_engine.tally(
            q, _ctx([_diff("손", "거리 부족")]), dimension_overall=80,
            measured_deviations={"body_relative_notches": q.bodyRelativeNotches},
            dimension_scores=None, baseline_kind="hip_line").to_dict()
    if json.dumps(_reach(), sort_keys=True) != json.dumps(_reach(), sort_keys=True):
        failures.append("[determinism] reach path: breakdown not byte-identical")
    return failures


# ── (3b) criterion-SELECTION-determinism ──────────────────────────────────────


def _activated_selection(differences, measured):
    """엔진의 criterion SELECTION(활성화 criterion id 집합)을 supported_differences +
    measured substrate 의 순수 함수로 재현 — seed ∪ router(severity 미사용).
    """
    seeded = set(ipsf_criteria.criteria_from_measured_deviations(measured))
    pointed: set[str] = set()
    for diff in differences:
        try:
            from sunity_shared.analysis.vision_veto import fault_key_from_difference
            fk = fault_key_from_difference(diff)
        except Exception:  # noqa: BLE001
            fk = None
        res = ipsf_criteria.criteria_for_fault(fk, diff, measured)
        if isinstance(res, ipsf_criteria.CoverageGap):
            continue
        pointed.update(res)
    activated = seeded | pointed
    if activated & {"leg_extension", "arm_extension"} and "line" in activated:
        activated.discard("line")
    return frozenset(activated)


def check_criterion_selection_determinism() -> list[str]:
    """criterion SELECTION 이 supported_differences 의 순수 함수임을 증명(실 Phase-18 drift
    방어 게이트). 무관 필드(severity / telemetry)만 바꾼 동일 supported_differences →
    동일 활성 criterion set. severity 가 selection 을 바꾸면 FAIL.
    """
    failures: list[str] = []
    measured = {"leg_extension": 40.0}
    base = [_diff("무릎", "굽음", severity="moderate")]
    # severity 변주
    var_sev = [_diff("무릎", "굽음", severity="major")]
    # telemetry-류 무관 필드 변주(approx_angle_deviation_deg 는 selection 에 안 들어감)
    var_tel = [_diff("무릎", "굽음", severity="minor", approx_angle_deviation_deg=999)]
    sel_base = _activated_selection(base, measured)
    sel_sev = _activated_selection(var_sev, measured)
    sel_tel = _activated_selection(var_tel, measured)
    if sel_base != sel_sev:
        failures.append(
            f"[selection] severity changed selection: {sorted(sel_base)} != {sorted(sel_sev)}"
        )
    if sel_base != sel_tel:
        failures.append(
            f"[selection] irrelevant telemetry changed selection: "
            f"{sorted(sel_base)} != {sorted(sel_tel)}"
        )
    # 같은 입력 두 번 → 동일(순수성).
    if _activated_selection(base, measured) != _activated_selection(base, measured):
        failures.append("[selection] non-deterministic across identical inputs")
    return failures


# ── (4) generalization (ARTIFACT-GATED + STRUCTURAL) ──────────────────────────

# RESULT not target — curve-fit ban. 수치 ≥95 bound 는 순수 게이트에 절대 미적용(MEDIUM-1).
# success 멤버: records 부재 OR within-tolerance(추적가능). fault 멤버: 같은 named
# criterion 에서 success 보다 strictly 큰 shortfall(structural relative, false-negative 방향).


def _records_of(member):
    """artifact 멤버에서 records list 추출(deductionBreakdown OBJECT 또는 records list)."""
    if member is None:
        return None
    if isinstance(member, dict):
        if "records" in member:
            return member["records"]
        bd = member.get("deductionBreakdown")
        if isinstance(bd, dict):
            return bd.get("records", [])
    return None


def check_generalization(pairs=None, breakdowns=None) -> list[str]:
    """phase18 6-페어 STRUCTURAL 일반화 — 실 Pod-생성 artifact 에만 돈다(HIGH-4).

    artifact(phase24_breakdowns.json) ABSENT 면 단일 SKIPPED marker 반환(실패 아님).
    입력을 절대 fabricate 하지 않는다(옛 eval18 overall 을 tally 결과로 읽지 않고,
    breakdown 을 합성하지도 않음). artifact PRESENT 면 STRUCTURAL(MEDIUM-1):
      · success/elite 멤버: records 부재 OR 모든 record 의 deviation ≤ 그 criterion tolerance.
      · fault 멤버: 같은 named criterion 에서 success 보다 strictly 큰 shortfall(deviation).
    """
    if breakdowns is None:
        if not _BREAKDOWN_ARTIFACT.exists():
            return ["SKIPPED (phase24 breakdown fixture absent)"]
        breakdowns = json.loads(_BREAKDOWN_ARTIFACT.read_text(encoding="utf-8"))
    if not breakdowns:
        return ["SKIPPED (phase24 breakdown fixture absent)"]

    failures: list[str] = []
    by_id = breakdowns if isinstance(breakdowns, dict) else {
        p.get("motion_id"): p for p in breakdowns
    }
    tol_by_crit = {c["id"]: c["tolerance"] for c in ipsf_criteria.CRITERION_GROUPS}

    for motion_id, entry in by_id.items():
        success_recs = _records_of(entry.get("correct") if isinstance(entry, dict) else None)
        fault_recs = _records_of(entry.get("fault") if isinstance(entry, dict) else None)
        # success: within-tolerance 추적가능(또는 records 부재).
        if success_recs:
            for r in success_recs:
                crit = r.get("criterion")
                tol = tol_by_crit.get(crit)
                dev = r.get("deviation")
                if tol is not None and dev is not None and dev > tol:
                    failures.append(
                        f"[generalization] {motion_id}: success member has criterion={crit} "
                        f"deviation={dev} > tolerance={tol} (not traceable-within-tolerance)"
                    )
        # fault: 같은 named criterion 에서 success 보다 strictly 큰 shortfall.
        if fault_recs is None:
            continue
        success_dev = {r.get("criterion"): r.get("deviation") for r in (success_recs or [])}
        larger_in_named = False
        for r in fault_recs:
            crit = r.get("criterion")
            fdev = r.get("deviation")
            sdev = success_dev.get(crit, 0.0) or 0.0
            if fdev is not None and fdev > sdev:
                larger_in_named = True
                break
        if not larger_in_named:
            failures.append(
                f"[generalization] {motion_id}: fault member shows no strictly larger "
                f"shortfall in any named criterion than its success pair "
                f"(structural false-negative)"
            )
    # unseen sensitivity set 은 Pod-serial deferred(정직한 SKIPPED — 실패 아님).
    failures.append("SKIPPED (sensitivity set deferred — Pod-serial, see Task 3 checkpoint)")
    return failures


# ── (6) clean-residual (ABSOLUTE, ARTIFACT-GATED) ─────────────────────────────

# generalization 은 fault shortfall > success shortfall 의 RELATIVE 속성만 본다 — 오염된
# 정타(correct)가 tolerance 초과 잔차를 들고도 상대적으로 PASS 할 수 있다. clean-residual 은
# ABSOLUTE 속성을 단언: correct 멤버의 모든 measured-angle record 가 raw 편차 ≤ criterion
# tolerance 로 역산돼야 한다. raw = abs(baselineValue − measuredValue) — deviation_source 무관
# (ipsf_absolute 180−d / reference_relative 0−d / reach ref−stu 모두 동일 tolerance-anchored 량).


def _finite_num(x):
    """None/non-finite → None, else float. clean-residual finite-guard(traceability 가 별도로 잡음)."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def check_clean_residual(breakdowns=None) -> list[str]:
    """정타(correct) 멤버 ABSOLUTE 잔차 게이트 — 실 Pod-생성 artifact 에만 돈다(HIGH-4).

    artifact(phase24_breakdowns.json) ABSENT/empty → 단일 SKIPPED marker(실패 아님). PRESENT 면
    각 motion 의 correct 멤버 record 를 _records_of 로 추출하고, criterion 이 tol_by_crit
    (CRITERION_GROUPS tolerance)에 있을 때 raw = abs(baselineValue − measuredValue) 를 역산해
    raw > tolerance 면 FAIL. tol_by_crit 에 없는 criterion(dimension_overall_fallback)은 anchor
    tolerance 부재 → out-of-scope skip(실패 아님). baselineValue/measuredValue 가 non-finite 면
    skip(traceability 게이트가 따로 잡음).

    24-07 후 granular reference_relative pod artifact 가 오염 정타 잔차를 실으면 이 게이트는 FAIL
    하도록 설계됐다 — 그 red 가 P1 objective-IPSF 채점이 green 으로 돌려야 할 신호다(EXPECTED red).
    """
    if breakdowns is None:
        if not _BREAKDOWN_ARTIFACT.exists():
            return ["SKIPPED (phase24 breakdown fixture absent for clean-residual)"]
        breakdowns = json.loads(_BREAKDOWN_ARTIFACT.read_text(encoding="utf-8"))
    if not breakdowns:
        return ["SKIPPED (phase24 breakdown fixture absent for clean-residual)"]

    failures: list[str] = []
    by_id = breakdowns if isinstance(breakdowns, dict) else {
        p.get("motion_id"): p for p in breakdowns
    }
    tol_by_crit = {c["id"]: c["tolerance"] for c in ipsf_criteria.CRITERION_GROUPS}

    for motion_id, entry in by_id.items():
        correct_recs = _records_of(entry.get("correct") if isinstance(entry, dict) else None)
        if not correct_recs:
            continue
        for r in correct_recs:
            crit = r.get("criterion")
            tol = tol_by_crit.get(crit)
            if tol is None:
                continue  # anchor tolerance 부재(fallback/unknown) — out of scope, 실패 아님
            bv = _finite_num(r.get("baselineValue"))
            mv = _finite_num(r.get("measuredValue"))
            if bv is None or mv is None:
                continue  # finite-guard — traceability 게이트가 별도로 잡음
            raw = abs(bv - mv)
            if raw > tol:
                failures.append(
                    f"[clean-residual] {motion_id}: correct member residual above tolerance "
                    f"— criterion={crit} raw={round(raw, 2)} > tolerance={tol}"
                )
    return failures


# ── (7) sensitivity (above-cutoff metric-validity, 합성·항상 실행) ─────────────

# elite-low(clean stays clean)만으로는 metric validity 미증명 — 명백히 above-tolerance 인 편차가
# 실제 감점을 내는지, deadzone(tolerance 미만) 편차가 spurious 감점을 안 내는지 양방 증명. 모든
# 임계/margin 은 CRITERION_GROUPS tolerance 에서만 파생(리터럴 magic number 금지, curve-fit 금지).
# 점수 밴드 절대 미단언 — 방향성(final<baseline penalized / final==baseline+empty clean)만.


def check_sensitivity() -> list[str]:
    """above-cutoff/deadzone 양방 sensitivity 게이트 — 합성, 항상 실행(artifact 무관).

    leg_extension / arm_extension 각각:
      · above = 2×tolerance(명백히 above-cutoff) → tally.final 이 baseline 미만이고 record 중
        points<0 가 있어야 한다(없으면 metric 이 tolerance 위에서 무감각 = FAIL).
      · deadzone = tolerance/2(NONZERO, strictly below tolerance) → tally.final==baseline 이고
        record 가 비어야 한다(positive 입력으로 over<=0 dead-zone branch 를 실제로 태운다 —
        legitimate 소편차를 over-penalize 하는 엔진 = 위양성 = FAIL).
    임계/margin 은 CRITERION_GROUPS tolerance 에서만 파생. 점수 밴드 미단언.
    """
    failures: list[str] = []
    tol_by_crit = {c["id"]: c["tolerance"] for c in ipsf_criteria.CRITERION_GROUPS}
    probes = {
        "leg_extension": _diff("무릎", "굽음"),
        "arm_extension": _diff("팔꿈치", "굽음"),
    }
    baseline = deduction_engine._BASELINE
    for cid, diff in probes.items():
        tol = tol_by_crit[cid]
        above = 2.0 * tol         # 명백히 above-cutoff(load-bearing)
        deadzone = tol / 2.0      # NONZERO, strictly below tolerance(dead-zone branch)
        ctx = _ctx([diff])
        # above-cutoff → 반드시 비-자명 감점.
        b_above = _tally({cid: above}, ctx)
        if b_above.final >= baseline or not any(r.points < 0 for r in b_above.records):
            failures.append(
                f"[sensitivity] {cid}: above-cutoff deviation (2×tol={above}) produced no "
                f"penalty (final={b_above.final}) — metric insensitive above tolerance"
            )
        # deadzone(<tol) → 감점 0(spurious penalty 금지).
        b_dead = _tally({cid: deadzone}, ctx)
        if b_dead.final < baseline or b_dead.records:
            failures.append(
                f"[sensitivity] {cid}: within-tolerance deviation (tol/2={deadzone}) was "
                f"spuriously penalized (final={b_dead.final}, records={len(b_dead.records)})"
            )
    return failures


# ── compose ───────────────────────────────────────────────────────────────────


def _split_skips(results):
    """SKIPPED marker 와 실제 failure 를 분리(SKIPPED 는 실패로 카운트 안 함)."""
    skips = [r for r in results if r.startswith("SKIPPED")]
    fails = [r for r in results if not r.startswith("SKIPPED")]
    return fails, skips


def main() -> int:
    breakdowns = _synthetic_breakdowns()
    failures: list[str] = []
    skipped: list[str] = []

    for label, result in (
        ("traceability", check_traceability(breakdowns)),
        ("monotonicity", check_monotonicity()),
        ("determinism", check_determinism()),
        ("criterion_selection", check_criterion_selection_determinism()),
        ("generalization", check_generalization()),
        ("clean_residual", check_clean_residual()),
        ("sensitivity", check_sensitivity()),
    ):
        fails, skips = _split_skips(result)
        failures.extend(fails)
        skipped.extend(skips)

    if failures:
        print("Phase 24 gates FAIL:")
        for f in failures:
            print("  -", f)
        for s in skipped:
            print("  ·", s)
        return 1

    print(f"Phase 24 gates PASS — {len(breakdowns)} synthetic breakdowns; "
          "traceability / monotonicity[fixed-set] / determinism[math+selection] green.")
    for s in skipped:
        print("  ·", s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
