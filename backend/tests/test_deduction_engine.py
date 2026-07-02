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
from sunity_shared.analysis.skeleton import JOINT_KEYS


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
    # source 값 집합 lockstep (quick-260702-q8q) — 엔진이 vision-측정 split 경로에서
    # source='vision' 을 방출(belle 2026-06-29 결정 A)하므로 TS union 도 실방출 값
    # 집합 {geometry, vision} 과 일치해야 한다 (계약 drift 재발 가드).
    assert "'geometry' | 'vision'" in m.group(1)


def test_vision_measured_split_emits_source_vision():
    """vision-측정 split 경로 lockstep 가드 (quick-260702-q8q).

    md 에 split_angle substrate 부재(geometric 측정 confounded) + Gemini split diff 가
    approx_angle_deviation_deg(vision-측정 reference-상대 편차)를 보유 → 엔진이 md 에
    주입하고 record.source == 'vision' 으로 provenance 를 투명 표기한다.
    """
    d = _diff("스플릿", "벌어짐 부족")
    d["approx_angle_deviation_deg"] = 30.0
    b = _tally(_measured(), _ctx([d]))
    split_recs = [r for r in b.records if r.criterion == "split_angle"]
    assert len(split_recs) == 1
    rec = split_recs[0]
    assert rec.source == "vision"
    assert rec.deviation_source == "reference_relative"
    # to_dict() 키가 계약 tuple 과 정확히 일치 + 전 record 값 집합 가드.
    assert set(rec.to_dict()) == set(models.DEDUCTION_RECORD_KEYS)
    assert all(r.source in {"geometry", "vision"} for r in b.records)


def test_geometry_path_source_geometry():
    """geometry 경로 회귀 0 — 측정 seed 기반 record 는 여전히 source='geometry'."""
    b = _tally(_measured(leg=40.0), _ctx([_diff("무릎", "굽음")]))
    recs = [r for r in b.records if r.criterion == "leg_extension"]
    assert recs
    assert all(r.source == "geometry" for r in recs)
    assert set(recs[0].to_dict()) == set(models.DEDUCTION_RECORD_KEYS)


# ── criterion table ────────────────────────────────────────────────────────


def test_criterion_groups_core_plus_reference_relative():
    # 24-07: 5 core criteria 보존 + JOINT_KEYS 별 reference_relative 각도 criterion 추가.
    by_id = {c["id"]: c for c in ipsf_criteria.CRITERION_GROUPS}
    ids = set(by_id)
    assert {"leg_extension", "arm_extension", "split_angle", "line",
            "body_relative_reach"} <= ids
    # deviation_source + direction tags present + correct (core).
    # leg/arm/line = ipsf_absolute(180° 신전). split_angle = reference_relative(정은지 대비
    # split 부족분 — 객관 180° 강요 금지, 15-SPLIT-MEASUREMENT-DESIGN §3 / RESUME 2026-06-29).
    for cid in ("leg_extension", "arm_extension", "line"):
        assert by_id[cid]["deviation_source"] == "ipsf_absolute"
        assert by_id[cid]["direction"] == "over_target"
    assert by_id["split_angle"]["deviation_source"] == "reference_relative"
    assert by_id["split_angle"]["direction"] == "over_target"
    assert by_id["body_relative_reach"]["deviation_source"] == "reference_relative"
    assert by_id["body_relative_reach"]["direction"] == "insufficient_reach"
    # 24-07 — per-joint reference_relative 각도 criterion(JOINT_KEYS 1개씩, granular wish).
    ref_rel = [c for c in ipsf_criteria.CRITERION_GROUPS
               if c["id"].startswith("angle_vs_reference__")]
    assert len(ref_rel) == len(JOINT_KEYS)
    assert {c["id"] for c in ref_rel} == {f"angle_vs_reference__{jk}" for jk in JOINT_KEYS}
    for c in ref_rel:
        assert c["deviation_source"] == "reference_relative"
        assert c["direction"] == "over_target"
        assert c["joint_keys"] and len(c["joint_keys"]) == 1
        assert c["tolerance"] == ipsf_criteria._ANGLE_TOLERANCE_DEG  # kismam 재사용
        assert c["ipsf_cap"] == ipsf_criteria._ANGLE_CAP
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
    assert leg.deviation_source == "ipsf_absolute"
    d = _diff("손", "거리 부족")
    reach = deduction_engine.tally(
        _notch_quant(3.0, 2.0), _ctx([d]), dimension_overall=80,
        measured_deviations={"body_relative_notches": _notch_quant(3.0, 2.0).bodyRelativeNotches},
        dimension_scores=None, baseline_kind="hip_line")
    rr = [r for r in reach.records if r.criterion == "body_relative_reach"][0]
    assert rr.deviation_source == "reference_relative"


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
        out[bk] = (rr[0].points if rr else 0.0, rr[0].baseline_kind if rr else None)
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
    # 폴백 조건 = quant 불가 AND 측정/지목 substrate 전무(빈 seed + Gemini 무지목). 24-05 후
    # 비-빈 각도 seed 는 granular 경로로 가므로 폴백 계약은 빈-seed 로 정확히 검증.
    b = _tally(_measured(), _ctx([]),
               dimension_overall=62, quantification=_unavailable_quant())
    assert b.final == 62
    assert b.fallback == "quantification_unavailable"
    assert b.final != 100


def test_unavailable_emits_traceable_record():
    # 빈 seed(_measured()) + Gemini 무지목(_ctx([])) → dimension_overall_fallback record(추적성).
    b = _tally(_measured(), _ctx([]),
               dimension_overall=62, quantification=_unavailable_quant())
    fb = [r for r in b.records if r.criterion == "dimension_overall_fallback"]
    assert len(fb) == 1
    rec = fb[0]
    assert rec.rule_id == "quantification_unavailable_dimension_overall"
    assert rec.unit == "score_delta"
    assert rec.deviation_source == "dimension_overall"
    assert rec.baseline_value == 100
    assert rec.points < 0
    assert 100 + sum(r.points for r in b.records) == b.final


# ── 24-05: measured-seed 가 quant unavailable 에서도 소비됨 (ND-01/05/06/07) ───
# 24-04 가 apply seam 에서 low_alignment 를 tally-eligible 로 만들었으나, 엔진 폴백 게이트가
# measured seed 를 문 앞에서 폐기했다. 폴백을 criterion 선택 뒤로 옮긴 fix 의 회귀 가드.


def test_unavailable_with_angle_seed_emits_granular():
    # CORE 회귀 가드(ND-01): quant 불가 + 측정 각도 seed(leg=30) → leg_extension granular record,
    # dimension_overall_fallback 아님, final<100.
    b = _tally(_measured(leg=30.0), _ctx([]),
               dimension_overall=80, quantification=_unavailable_quant())
    assert any(r.criterion == "leg_extension" for r in b.records)
    assert b.fallback != "quantification_unavailable"
    assert not any(r.criterion == "dimension_overall_fallback" for r in b.records)
    assert b.final < 100


def test_unavailable_empty_seed_preserves_fallback():
    # 폴백 보존: quant 불가 + 측정 seed 전무(md={}) → dimension_overall_fallback 1개 유지.
    b = _tally(_measured(), _ctx([]),
               dimension_overall=70, quantification=_unavailable_quant())
    fb = [r for r in b.records if r.criterion == "dimension_overall_fallback"]
    assert len(fb) == 1
    assert b.fallback == "quantification_unavailable"


def test_legacy_none_quant_none_md_preserves_fallback():
    # legacy 단일영상(quantification=None, measured_deviations=None) → 폴백 보존(회귀 0).
    b = deduction_engine.tally(
        None, _ctx([]), dimension_overall=75,
        measured_deviations=None, dimension_scores=None, baseline_kind="hip_line")
    fb = [r for r in b.records if r.criterion == "dimension_overall_fallback"]
    assert len(fb) == 1
    assert b.fallback == "quantification_unavailable"


def test_unavailable_seed_monotonic_deduction():
    # 단조성(ND-07): 측정 편차 클수록 총 감점(Σ|points|) 증가. 둘 다 unavailable quant.
    small = _tally(_measured(leg=20.0), _ctx([]),
                   dimension_overall=80, quantification=_unavailable_quant())
    large = _tally(_measured(leg=40.0), _ctx([]),
                   dimension_overall=80, quantification=_unavailable_quant())
    ded_small = sum(abs(r.points) for r in small.records)
    ded_large = sum(abs(r.points) for r in large.records)
    assert ded_small < ded_large


def test_unavailable_seed_emits_reach_coverage_gap():
    # 추적성(ND-06/07): quant 불가 + 각도 seed → reach 칸 측정 불가가 coverage_gaps 에 노출.
    b = _tally(_measured(leg=30.0), _ctx([]),
               dimension_overall=80, quantification=_unavailable_quant())
    rule_ids = {g.get("ruleId") for g in b.coverage_gaps}
    assert "reach_substrate_unavailable_low_alignment" in rule_ids


def test_unavailable_seed_deterministic():
    # 결정성(ND-07): 동일 입력 2회 호출 → to_dict() 동일(records/coverageGaps/final 일치).
    q = _unavailable_quant()
    b1 = _tally(_measured(leg=30.0), _ctx([]),
                dimension_overall=80, quantification=q)
    b2 = _tally(_measured(leg=30.0), _ctx([]),
                dimension_overall=80, quantification=q)
    assert b1.to_dict() == b2.to_dict()


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
    assert all(not (r.points < 0 and r.rule_id is None) for r in b.records)


# ── 24-07: reference_relative per-joint 각도 seed (미등록 동작 granular 실현) ──────
# 미등록 동작(expects_extension 전부 False)에서 ipsf_absolute seed 가 빌 때, 정은지(reference)
# 대비 per-joint 각도 편차를 granular DeductionRecord 로 방출한다(dimension_overall_fallback 아님).
# calibration = kismam 재사용(tol 20° + _SLOPE), 새 임계 0. 방향/구조 단언만(curve-fit 금지).


def _ref_rel(**joint_devs):
    """reference_relative md (angle_vs_reference__{joint} → reference 대비 deg 편차)."""
    return {f"angle_vs_reference__{jk}": float(v) for jk, v in joint_devs.items()}


def test_reference_relative_seeds_granular_per_joint():
    # 미등록 동작: 무릎 편차 35°(>tol 20°) → per-joint reference_relative record 1개 방출,
    # dimension_overall_fallback 아님 (quant unavailable 이어도 각도 seed 살아 granular, 24-05).
    b = _tally(_ref_rel(left_knee=35.0), _ctx([]), quantification=_unavailable_quant())
    recs = [r for r in b.records if r.criterion == "angle_vs_reference__left_knee"]
    assert len(recs) == 1
    assert recs[0].deviation_source == "reference_relative"
    assert recs[0].unit == "deg"
    assert recs[0].points < 0
    assert recs[0].baseline_value == 0.0  # 목표 = reference 대비 0° 편차
    assert not any(r.criterion == "dimension_overall_fallback" for r in b.records)
    assert b.final < 100


def test_reference_relative_deadzone():
    # 12° < tol 20° → seed 안 됨 → reference_relative record 0 (dead-zone).
    b = _tally(_ref_rel(left_knee=12.0), _ctx([]), quantification=_available_quant())
    assert not any(r.criterion == "angle_vs_reference__left_knee" for r in b.records)


def test_reference_relative_self_compare_zero():
    # self-compare: 모든 angle_vs_reference__* = 0 → record 0, final=100 (위양성 0).
    md = {f"angle_vs_reference__{jk}": 0.0 for jk in JOINT_KEYS}
    b = _tally(md, _ctx([]), dimension_overall=100, quantification=_available_quant())
    assert all(not r.criterion.startswith("angle_vs_reference__") for r in b.records)
    assert b.final == 100


def test_reference_relative_double_count_blocked():
    # leg_extension(무릎 ipsf_absolute) seed + 같은 무릎 reference_relative → leg_extension 만,
    # 무릎 reference_relative 2개는 cross-exclusion 으로 discard (knee double-count 0).
    md = {**_measured(leg=30.0), **_ref_rel(left_knee=35.0, right_knee=33.0)}
    b = _tally(md, _ctx([]), quantification=_available_quant())
    crits = {r.criterion for r in b.records}
    assert "leg_extension" in crits
    assert "angle_vs_reference__left_knee" not in crits
    assert "angle_vs_reference__right_knee" not in crits


def test_reference_relative_complement_preserved():
    # leg_extension(무릎) + 어깨 reference_relative → 둘 다 방출 (어깨는 어떤 ipsf_absolute 도
    # claim 안 함 = 순수 보완 seed).
    md = {**_measured(leg=30.0), **_ref_rel(left_shoulder=40.0)}
    b = _tally(md, _ctx([]), quantification=_available_quant())
    crits = {r.criterion for r in b.records}
    assert "leg_extension" in crits
    assert "angle_vs_reference__left_shoulder" in crits


def test_reference_relative_deterministic():
    # 결정성: 동일 md 2회 호출 → records/final 동일 순서·값.
    md = _ref_rel(left_knee=35.0, right_elbow=28.0)
    q = _available_quant()
    b1 = _tally(md, _ctx([]), quantification=q)
    b2 = _tally(md, _ctx([]), quantification=q)
    assert b1.to_dict() == b2.to_dict()


# ── split_angle reference_relative (15-SPLIT-MEASUREMENT-DESIGN §3) ──────────


def test_split_reference_relative_scored_and_monotonic():
    # split_angle = reference_relative: md[split_angle]=max(0, 정은지 max-split − 학생) deg.
    # tol(20°) 초과 → record(baseline 0) 방출, 부족분↑ → 감점↑(단조). seed 만으로 활성(_ctx []).
    over = _tally(_measured(split=40.0), _ctx([]))
    rec = [r for r in over.records if r.criterion == "split_angle"]
    assert len(rec) == 1
    assert rec[0].deviation_source == "reference_relative"
    assert rec[0].unit == "deg"
    assert rec[0].baseline_value == 0.0  # 목표 = reference 대비 0° 부족
    assert rec[0].points < 0
    finals = [_tally(_measured(split=d), _ctx([])).final for d in (0.0, 30.0, 60.0, 90.0)]
    assert finals[0] >= finals[1] > finals[2] > finals[3]


def test_split_reference_relative_deadzone():
    # 학생 split 이 정은지와 tol(20°) 이내(부족분 12°) → dead-zone, 감점 0 (correct 위양성 0).
    b = _tally(_measured(split=12.0), _ctx([]))
    assert not any(r.criterion == "split_angle" for r in b.records)


def test_split_not_absolute_180_fail():
    # 객관 180° 강요 금지 회귀 가드(belle over-EXTEND): 부족분 40° 가 절대-split 140°<160°
    # 0-fail(cap 폭주)로 처리되면 안 됨 — reference_relative 선형(over=40−20=20)이어야 한다.
    rec = [r for r in _tally(_measured(split=40.0), _ctx([])).records
           if r.criterion == "split_angle"][0]
    assert rec.deviation == 20.0  # max(0, 40−tol 20) — 절대-fail cap(84) 아님
    assert rec.deviation_source == "reference_relative"


def test_split_claims_hips_blocks_reference_relative_double_count():
    # split_angle(양 hip claim) 활성 + 같은 hip reference_relative → split 만, hip ref_rel discard.
    md = {**_measured(split=40.0), **_ref_rel(left_hip=35.0, right_hip=33.0)}
    crits = {r.criterion for r in _tally(md, _ctx([])).records}
    assert "split_angle" in crits
    assert "angle_vs_reference__left_hip" not in crits
    assert "angle_vs_reference__right_hip" not in crits


def test_split_vision_measured_deviation_scores():
    # geometric split md 없음 + vision 이 split 30° 짚음 → split_angle 이 vision 측정값으로
    # 감점, source='vision' provenance (belle 2026-06-29 A — geometric 불가 결함의 vision 점수화).
    diff = {"body_part": "스플릿", "fault_state": "벌어짐 부족", "severity": "moderate",
            "approx_angle_deviation_deg": 30}
    b = _tally({}, _ctx([diff]))  # md 비어있음(geometric split 측정 없음)
    rec = [r for r in b.records if r.criterion == "split_angle"]
    assert len(rec) == 1
    assert rec[0].source == "vision"          # provenance 노출
    assert rec[0].deviation_source == "reference_relative"
    assert rec[0].deviation == 10.0           # over = max(0, 30 − tol 20)
    assert rec[0].points < 0


def test_split_geometric_md_precedence_over_vision():
    # geometric md["split_angle"] 존재(진짜 split-요구 동작) → vision 편차로 덮어쓰지 않음.
    diff = {"body_part": "스플릿", "fault_state": "벌어짐 부족", "severity": "moderate",
            "approx_angle_deviation_deg": 99}
    rec = [r for r in _tally(_measured(split=25.0), _ctx([diff])).records
           if r.criterion == "split_angle"][0]
    assert rec.source == "geometry"           # geometric 우선
    assert rec.deviation == 5.0               # 25 − 20 (geometric), 99 아님


def test_split_no_vision_deviation_no_score():
    # vision 이 split 을 짚어도 측정 편차(approx_angle_deviation_deg) 부재면 감점 0(honest).
    diff = {"body_part": "스플릿", "fault_state": "벌어짐 부족", "severity": "moderate"}
    b = _tally({}, _ctx([diff]))
    assert not any(r.criterion == "split_angle" for r in b.records)


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
