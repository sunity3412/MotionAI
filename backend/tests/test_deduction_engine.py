"""투명 감점-합산 엔진(Phase 24 ND-01~07) 단위 게이트 — 결정적 검증. AWS 불필요.

test_kismam.py 구조 박제(monotonicity/dead-zone/single-fault-dominance) + Phase 24
신규 게이트: no-final-band / criterion 묶음 no-runaway / severity 독립 / criteria_for_fault
라우팅 정확도(split≠leg) + severity 불변 / line·leg cross double-count 금지(HIGH-5) /
insufficient-reach 방향(HIGH-2) / gemini-silent≠100(measured seed) / unavailable fallback
(+traceable record, MEDIUM-1) / full FaultKey coverage(+partition) / deviation source /
body_relative_reach baseline-driven(ND-05) / empty-expectations line 0(ND-06 honest 0) /
flat OBJECT serialization(baselineValue/baselineKind).

모든 단언은 방향/구조 — 보유 sweep 수치 타깃 아님(curve-fit 금지,
[[scoring-redesign-must-generalize-no-overfit]]).
"""

import pathlib
import re

import numpy as np
import pytest

from sunity_shared import models
from sunity_shared.analysis import deduction_engine, ipsf_criteria, vision_veto
from sunity_shared.analysis import technique


# ── fixtures ────────────────────────────────────────────────────────────────


def _measured(leg=None, arm=None, split=None, line=None):
    """ipsf_absolute 측정 편차 substrate (criterion id → student-vs-target deg).

    None = 그 criterion 의 측정 substrate 부재(profile-gated/미산출) → 0 기여(honest 0).
    """
    out: dict[str, float | None] = {}
    if leg is not None:
        out["leg_extension"] = leg
    if arm is not None:
        out["arm_extension"] = arm
    if split is not None:
        out["split_angle"] = split
    if line is not None:
        out["line"] = line
    return out


def _notch_quant(reference_notches, student_notches, baseline_kind="hip_line",
                 keypoint="left_hand"):
    """vision_veto.body_relative_notches 출력 형상의 합성 quantification (available)."""
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


def _available_quant():
    return vision_veto.VisionQuantificationResult(quantificationStatus="available")


def _unavailable_quant():
    return vision_veto.VisionQuantificationResult(
        quantificationStatus="unavailable", warnings=("inputs_missing",)
    )


def _diff(body_part, fault_state, severity="moderate"):
    """gemini_vision_scorer differences[] 항목 형상(router 입력)."""
    return {
        "body_part": body_part,
        "correct_state": "",
        "fault_state": fault_state,
        "severity": severity,
        "approx_angle_deviation_deg": 0,
    }


def _ctx(differences):
    """fault_context — supported_differences 보유 단순 컨테이너(엔진이 읽는 최소 형상)."""
    return {"supported_differences": list(differences)}


# ── contract lockstep ─────────────────────────────────────────────────────


def test_contract_lockstep():
    # DEDUCTION_RECORD_KEYS member 이름 == TS DeductionRecord 필드 (set 동등).
    ts = (pathlib.Path(__file__).resolve().parents[1].parent
          / "app" / "src" / "types" / "analysis.ts").read_text(encoding="utf-8")
    m = re.search(r"export interface DeductionRecord \{(.*?)\}", ts, re.S)
    assert m, "DeductionRecord interface 부재"
    ts_fields = set(re.findall(r"(\w+)\??:", m.group(1)))
    assert set(models.DEDUCTION_RECORD_KEYS) == ts_fields
    assert "baselineValue" in models.DEDUCTION_RECORD_KEYS
    assert "baselineKind" in models.DEDUCTION_RECORD_KEYS
    assert "fallback" in models.DEDUCTION_BREAKDOWN_KEYS
    assert "coverageGaps" in models.DEDUCTION_BREAKDOWN_KEYS


# ── criterion table ────────────────────────────────────────────────────────


def test_criterion_groups_five_criteria():
    ids = {c["id"] for c in ipsf_criteria.CRITERION_GROUPS}
    assert ids == {"leg_extension", "arm_extension", "split_angle", "line",
                   "body_relative_reach"}
    by_id = {c["id"]: c for c in ipsf_criteria.CRITERION_GROUPS}
    # deviation_source + direction tags present + correct.
    for cid in ("leg_extension", "arm_extension", "split_angle", "line"):
        assert by_id[cid]["deviation_source"] == "ipsf_absolute"
        assert by_id[cid]["direction"] == "over_target"
    assert by_id["body_relative_reach"]["deviation_source"] == "reference_relative"
    assert by_id["body_relative_reach"]["direction"] == "insufficient_reach"
    # every criterion carries the named config keys.
    for c in ipsf_criteria.CRITERION_GROUPS:
        for k in ("id", "tolerance", "slope", "ipsf_cap", "rule_id",
                  "ipsf_anchor", "deviation_source", "direction"):
            assert k in c, f"{c['id']} missing {k}"
    # single shared linear slope reused verbatim from kismam.
    from sunity_shared.analysis import kismam
    for c in ipsf_criteria.CRITERION_GROUPS:
        assert c["slope"] == kismam._PENALTY_PER_DEG


def test_coverage_gap_keypoint_sets():
    gaps = ipsf_criteria.COVERAGE_GAP_KEYPOINT_SETS
    assert set(gaps) == {"head_neck", "grip", "torso", "shoulder", "hip"}
    assert all(isinstance(v, str) and v for v in gaps.values())


# ── measured-deviation seed (HIGH-1) ───────────────────────────────────────


def test_criteria_from_measured_deviations_seeds_beyond_tol():
    # finite + beyond tolerance → seeded; None / within-tol → not seeded.
    seeded = ipsf_criteria.criteria_from_measured_deviations(_measured(leg=40.0))
    assert "leg_extension" in seeded
    assert ipsf_criteria.criteria_from_measured_deviations(_measured(leg=5.0)) == frozenset()
    assert ipsf_criteria.criteria_from_measured_deviations(_measured()) == frozenset()
    # body_relative_reach is NOT seeded (router-only).
    assert "body_relative_reach" not in ipsf_criteria.criteria_from_measured_deviations(
        _measured(leg=40.0)
    )


# ── public router (HIGH-1) ─────────────────────────────────────────────────


def test_criteria_for_fault_selects_split_not_leg():
    measured = _measured(leg=40.0, split=40.0)
    fk = vision_veto.fault_key_from_difference(_diff("스플릿", "벌어짐 부족"))
    out = ipsf_criteria.criteria_for_fault(fk, _diff("스플릿", "벌어짐 부족"), measured)
    assert out == ("split_angle",)
    # keypoint_set normalizes to leg, but router must NOT pick leg_extension.
    assert fk.keypoint_set == "leg"


def test_criteria_for_fault_knee_bend_to_leg():
    measured = _measured(leg=40.0)
    d = _diff("무릎", "굽음")
    fk = vision_veto.fault_key_from_difference(d)
    assert ipsf_criteria.criteria_for_fault(fk, d, measured) == ("leg_extension",)


def test_criteria_for_fault_hand_reach_to_body_relative():
    quant = _notch_quant(reference_notches=3.0, student_notches=2.0)
    measured = {"body_relative_notches": quant.bodyRelativeNotches}
    d = _diff("손", "거리 부족 / 멀어요")
    fk = vision_veto.fault_key_from_difference(d)
    assert ipsf_criteria.criteria_for_fault(fk, d, measured) == ("body_relative_reach",)


def test_criteria_for_fault_grip_is_coverage_gap():
    d = _diff("그립", "풀림")
    fk = vision_veto.fault_key_from_difference(d)
    out = ipsf_criteria.criteria_for_fault(fk, d, _measured())
    assert isinstance(out, ipsf_criteria.CoverageGap)
    assert out.keypoint_set == "grip"


def test_criteria_for_fault_severity_invariant():
    measured = _measured(leg=40.0)
    d_minor = _diff("무릎", "굽음", severity="minor")
    d_major = _diff("무릎", "굽음", severity="major")
    fk_minor = vision_veto.fault_key_from_difference(d_minor)
    fk_major = vision_veto.fault_key_from_difference(d_major)
    assert (ipsf_criteria.criteria_for_fault(fk_minor, d_minor, measured)
            == ipsf_criteria.criteria_for_fault(fk_major, d_major, measured))


def test_criterion_for_keypoint_set_total_over_vocab():
    mapped = set()
    gap = set()
    for ks in vision_veto.FAULT_KEYPOINT_SETS:
        res = ipsf_criteria._criterion_for_keypoint_set(ks)
        assert res is not None, f"silent None for {ks}"
        if res in ipsf_criteria.COVERAGE_GAP_KEYPOINT_SETS:
            gap.add(ks)
        else:
            mapped.add(ks)
    assert mapped == {"leg", "arm", "line"}
    assert gap == {"head_neck", "grip", "torso", "shoulder", "hip"}
    assert mapped | gap == set(vision_veto.FAULT_KEYPOINT_SETS)
    assert mapped & gap == set()


# ── engine tally behavior ──────────────────────────────────────────────────


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


def test_no_final_band():
    # huge deviation → final == 0 (no floor at 50/75/90).
    b = _tally(_measured(leg=500.0, arm=500.0, split=500.0),
               _ctx([_diff("무릎", "굽음")]))
    assert b.final == 0
    # source guard — no min-band near the return.
    src = (pathlib.Path(deduction_engine.__file__).read_text(encoding="utf-8"))
    assert "min(100" not in src
    assert "min(final" not in src


def test_deadzone_and_slope():
    in_tol = _tally(_measured(leg=5.0), _ctx([_diff("무릎", "굽음")]))
    assert all(r.points == 0 for r in in_tol.records if r.criterion == "leg_extension") \
        or all(r.criterion != "leg_extension" for r in in_tol.records)
    finals = []
    for dev in (0.0, 30.0, 60.0, 90.0):
        b = _tally(_measured(leg=dev), _ctx([_diff("무릎", "굽음")]))
        finals.append(b.final)
    # 보유 sweep 수치 타깃 아님 — 방향(단조 감소)만 단언.
    assert finals[0] >= finals[1] > finals[2] > finals[3]


def test_criterion_grouping_no_runaway():
    # both legs aggregated to ONE leg deviation upstream → ONE leg_extension record.
    b = _tally(_measured(leg=30.0), _ctx([_diff("무릎", "굽음")]))
    leg_records = [r for r in b.records if r.criterion == "leg_extension"]
    assert len(leg_records) == 1
    non_fallback = [r for r in b.records if r.criterion != "dimension_overall_fallback"]
    activated = len({r.criterion for r in non_fallback})
    assert len(non_fallback) <= activated


def test_score_independent_of_severity_enum():
    measured = _measured(leg=40.0)
    b_minor = _tally(measured, _ctx([_diff("무릎", "굽음", severity="minor")]))
    b_major = _tally(measured, _ctx([_diff("무릎", "굽음", severity="major")]))
    assert b_minor.final == b_major.final
    assert ([r.points for r in b_minor.records]
            == [r.points for r in b_major.records])


def test_line_leg_no_cross_double_count():
    # single bent knee activating leg_extension must NOT also emit a line record.
    measured = _measured(leg=40.0, line=40.0)
    b = _tally(measured, _ctx([_diff("무릎", "굽음")]))
    crits = {r.criterion for r in b.records}
    assert "leg_extension" in crits
    assert "line" not in crits
    # a line-dominant fault with no leg/arm activation DOES emit a line record.
    measured2 = _measured(line=40.0)
    b2 = _tally(measured2, _ctx([_diff("라인", "정렬 흐트러짐")]))
    assert "line" in {r.criterion for r in b2.records}


def test_reach_insufficient_direction():
    d = _diff("손", "거리 부족")
    # short reach (ref 3 / student 2) → deduction.
    short = deduction_engine.tally(
        _notch_quant(reference_notches=3.0, student_notches=2.0), _ctx([d]),
        dimension_overall=80,
        measured_deviations={"body_relative_notches":
                             _notch_quant(3.0, 2.0).bodyRelativeNotches},
        dimension_scores=None, baseline_kind="hip_line")
    reach_short = [r for r in short.records if r.criterion == "body_relative_reach"]
    assert reach_short and reach_short[0].points < 0
    # over reach (ref 2 / student 3) → NO deduction (insufficient_reach only).
    over = deduction_engine.tally(
        _notch_quant(reference_notches=2.0, student_notches=3.0), _ctx([d]),
        dimension_overall=80,
        measured_deviations={"body_relative_notches":
                             _notch_quant(2.0, 3.0).bodyRelativeNotches},
        dimension_scores=None, baseline_kind="hip_line")
    assert all(r.criterion != "body_relative_reach" or r.points == 0
               for r in over.records)


def test_deviation_source_per_criterion():
    b = _tally(_measured(leg=40.0), _ctx([_diff("무릎", "굽음")]))
    leg = [r for r in b.records if r.criterion == "leg_extension"][0]
    assert leg.deviationSource == "ipsf_absolute"
    d = _diff("손", "거리 부족")
    reach = deduction_engine.tally(
        _notch_quant(3.0, 2.0), _ctx([d]), dimension_overall=80,
        measured_deviations={"body_relative_notches": _notch_quant(3.0, 2.0).bodyRelativeNotches},
        dimension_scores=None, baseline_kind="hip_line")
    rr = [r for r in reach.records if r.criterion == "body_relative_reach"][0]
    assert rr.deviationSource == "reference_relative"


def test_body_relative_reach_uses_baseline():
    d = _diff("손", "거리 부족")
    out = {}
    for bk in ("floor", "hip_line"):
        # same raw reach values, but different quantize baseline → different notches.
        q = vision_veto.VisionQuantificationResult(
            quantificationStatus="available",
            bodyRelativeNotches=[{
                "keypoint": "left_hand",
                "student_notches": 2.0 if bk == "floor" else 1.0,
                "reference_notches": 3.0,
                "delta_notches": (2.0 if bk == "floor" else 1.0) - 3.0,
                "baseline_kind": bk,
                "source": "geometry",
            }],
        )
        b = deduction_engine.tally(
            q, _ctx([d]), dimension_overall=80,
            measured_deviations={"body_relative_notches": q.bodyRelativeNotches},
            dimension_scores=None, baseline_kind=bk)
        rr = [r for r in b.records if r.criterion == "body_relative_reach"]
        out[bk] = (rr[0].points if rr else 0.0, rr[0].baselineKind if rr else None)
    assert out["floor"][0] != out["hip_line"][0]
    assert out["floor"][1] == "floor"
    assert out["hip_line"][1] == "hip_line"


def test_gemini_silent_not_100():
    # Gemini silent (no supported_differences) BUT measured leg dev beyond tol →
    # measured seed activates leg_extension → final < 100, record present.
    b = _tally(_measured(leg=40.0), _ctx([]), dimension_overall=80)
    assert b.records != ()
    assert any(r.criterion == "leg_extension" for r in b.records)
    assert b.final < 100


def test_unavailable_falls_back_not_100():
    b = _tally(_measured(leg=40.0), _ctx([_diff("무릎", "굽음")]),
               dimension_overall=62, quantification=_unavailable_quant())
    assert b.final == 62
    assert b.fallback == "quantification_unavailable"
    assert b.final != 100


def test_unavailable_emits_traceable_record():
    b = _tally(_measured(leg=40.0), _ctx([]),
               dimension_overall=62, quantification=_unavailable_quant())
    fb = [r for r in b.records if r.criterion == "dimension_overall_fallback"]
    assert len(fb) == 1
    rec = fb[0]
    assert rec.ruleId == "quantification_unavailable_dimension_overall"
    assert rec.unit == "score_delta"
    assert rec.deviationSource == "dimension_overall"
    assert rec.baselineValue == 100
    assert rec.points < 0
    assert 100 + sum(r.points for r in b.records) == b.final


def test_line_criterion_empty_expectations_zero():
    # unregistered move: empty joint_expectations → line_score None → 0 line substrate.
    profile = technique.TechniqueProfile(
        name="미상", category="unknown", joint_expectations={},
    )
    assert all(not profile.expects_extension(k)
               for k in ("left_knee", "left_elbow"))
    # engine: line measured substrate absent (None) → no line record, no crash.
    b = _tally(_measured(line=None), _ctx([_diff("라인", "정렬")]))
    line_records = [r for r in b.records if r.criterion == "line"]
    assert all(r.points == 0 for r in line_records)


def test_coverage_gap_no_band():
    d = _diff("그립", "풀림")
    b = _tally(_measured(), _ctx([d]))
    assert b.coverage_gaps, "coverage gap entry 부재"
    gap = b.coverage_gaps[0]
    assert gap.get("faultType") or gap.get("keypointSet")
    assert gap.get("reason")
    # MEDIUM-3 provenance.
    assert gap.get("bodyPart") or gap.get("faultState")
    # never a points<0 ruleId=None record.
    assert all(not (r.points < 0 and r.ruleId is None) for r in b.records)


def test_breakdown_serializes_flat():
    b = _tally(_measured(leg=40.0), _ctx([_diff("무릎", "굽음")]))
    d = b.to_dict()
    assert set(d.keys()) == set(models.DEDUCTION_BREAKDOWN_KEYS)
    assert isinstance(d["records"], list)
    for rec in d["records"]:
        assert set(rec.keys()) == set(models.DEDUCTION_RECORD_KEYS)
        for v in rec.values():
            assert not isinstance(v, (list, dict)), "nested array/dict 금지(Firestore-flat)"
    assert d["final"] == max(0, round(100.0 + sum(r["points"] for r in d["records"])))
