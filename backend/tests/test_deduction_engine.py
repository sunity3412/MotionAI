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

import json
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


def _assert_record_keys(rec_dict):
    """record to_dict() 키 형상 가드 (quick-260705-k8h cap-인지 공용 helper).

    필수 키(DEDUCTION_RECORD_KEYS) 전부 존재 + 초과 키는 OPTIONAL 만 허용 +
    rawPoints/capApplied 는 반드시 쌍(둘 다 있거나 둘 다 없음 — 투명 내역 불변식)."""
    keys = set(rec_dict)
    required = set(models.DEDUCTION_RECORD_KEYS)
    optional = set(models.DEDUCTION_RECORD_OPTIONAL_KEYS)
    assert required <= keys, f"필수 키 누락 {required - keys}"
    assert keys - required <= optional, f"미계약 초과 키 {keys - required - optional}"
    assert ("rawPoints" in keys) == ("capApplied" in keys), \
        "rawPoints/capApplied 는 쌍으로만 존재해야 함"


# ── contract lockstep ─────────────────────────────────────────────────────


def test_contract_lockstep():
    # DEDUCTION_RECORD_KEYS member 이름 == TS DeductionRecord 필드 (set 동등).
    ts = (pathlib.Path(__file__).resolve().parents[1].parent
          / "app" / "src" / "types" / "analysis.ts").read_text(encoding="utf-8")
    m = re.search(r"export interface DeductionRecord \{(.*?)\}", ts, re.S)
    assert m, "DeductionRecord interface 부재"
    ts_fields = set(re.findall(r"(\w+)\??:", m.group(1)))
    # quick-260705-k8h: TS regex 는 optional 필드(rawPoints?/capApplied?)도 잡으므로
    # 필수 ∪ optional == TS 필드 set 으로 lockstep 단언 + 두 집합 disjoint 가드.
    assert (set(models.DEDUCTION_RECORD_KEYS)
            | set(models.DEDUCTION_RECORD_OPTIONAL_KEYS)) == ts_fields
    assert not set(models.DEDUCTION_RECORD_KEYS) & set(models.DEDUCTION_RECORD_OPTIONAL_KEYS)
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
    # leg=40 → raw 24 > 상한 20 → cap 적용 record (quick-260705-k8h) — 키 형상은
    # 필수 ⊆ 키 ⊆ 필수 ∪ optional 로 단언 (helper 재사용).
    _assert_record_keys(recs[0].to_dict())


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


# ── fault_category 고정 enum 라우팅 (25-05, SCHEMA v8.1) ─────────────────────


def _v11_kipup_split_diff(**extra):
    """v11 kip-up 실측 형상 — split 관측이 '벌림'+extension_or_alignment 로 drift 해
    leg_extension 으로 새던 supported_difference (25-SWEEP-EVIDENCE 실측 재현)."""
    d = _diff("양다리", "양다리 벌림 각도가 기준에 비해 현저히 좁음")
    d.update(extra)
    return d


def test_criteria_for_fault_category_enum_first_split():
    """v11 실측 형상이 fault_category=split_angle 로 오면 어휘/fault_kind 와 무관하게
    무조건 split 분기 (enum 1순위 소비)."""
    d = _v11_kipup_split_diff(fault_category="split_angle")
    fk = vision_veto.fault_key_from_difference(d)
    # v11 drift 형상 그대로 — fault_kind 는 extension 계열로 정규화되지만 라우팅은 enum.
    assert fk.fault_kind == "extension_or_alignment"
    out = ipsf_criteria.criteria_for_fault(fk, d, _measured(leg=40.0, split=40.0))
    assert out == ("split_angle",)


def test_criteria_for_fault_category_split_wins_without_split_vocab():
    """enum split_angle 은 스플릿 어휘가 전혀 없어도 split — 키워드 파싱이 라우팅
    근거에서 소멸했음을 증명 (두더지잡기 종결)."""
    d = _diff("오른쪽 다리", "각도가 기준보다 부족함")
    d["fault_category"] = "split_angle"
    fk = vision_veto.fault_key_from_difference(d)
    assert ipsf_criteria.criteria_for_fault(fk, d, _measured()) == ("split_angle",)


def test_criteria_for_fault_category_absent_beollim_keyword_fallback():
    """enum 부재(구 캐시 하위호환) — 같은 v11 형상이 신규 '벌림' 키워드 폴백으로 split
    라우팅 (기존엔 어느 마커에도 안 걸려 rule 8 → leg_extension 으로 새며 감점 유실)."""
    d = _v11_kipup_split_diff()  # fault_category 없음
    fk = vision_veto.fault_key_from_difference(d)
    assert ipsf_criteria.criteria_for_fault(fk, d, _measured(leg=40.0)) == ("split_angle",)


def test_criteria_for_fault_category_alignment_and_grip_decisive():
    """단독-결정 enum: alignment→line, grip→coverage gap — 키워드로는 도달 못 하는
    body_part 어휘에서도 enum 이 라우팅을 결정한다."""
    d_align = _diff("몸 전체", "자세 축이 흐트러짐")  # 키워드로는 torso gap 행
    d_align["fault_category"] = "alignment"
    fk_a = vision_veto.fault_key_from_difference(d_align)
    assert ipsf_criteria.criteria_for_fault(fk_a, d_align, _measured(line=40.0)) == ("line",)

    d_grip = _diff("오른손", "폴을 잡는 방식이 기준과 다름")
    d_grip["fault_category"] = "grip"
    fk_g = vision_veto.fault_key_from_difference(d_grip)
    out = ipsf_criteria.criteria_for_fault(fk_g, d_grip, _measured())
    assert isinstance(out, ipsf_criteria.CoverageGap)
    assert out.keypoint_set == "grip"


def test_criteria_for_fault_category_nondecisive_falls_through_keywords():
    """limb_extension/pole_gap/other 는 부위(leg vs arm) 정보가 없어 기존 키워드 체인
    유지 (하위호환) — 무릎 굽음→leg_extension, 팔꿈치 굽음→arm_extension 불변."""
    for cat in ("limb_extension", "other"):
        d_knee = _diff("무릎", "굽음")
        d_knee["fault_category"] = cat
        fk = vision_veto.fault_key_from_difference(d_knee)
        assert ipsf_criteria.criteria_for_fault(fk, d_knee, _measured(leg=40.0)) == (
            "leg_extension",
        ), cat
    d_elbow = _diff("팔꿈치", "굽음")
    d_elbow["fault_category"] = "pole_gap"
    fk_e = vision_veto.fault_key_from_difference(d_elbow)
    assert ipsf_criteria.criteria_for_fault(fk_e, d_elbow, _measured(arm=40.0)) == (
        "arm_extension",
    )


def test_criteria_for_fault_category_split_keyword_guards_enum_misclass():
    """split 어휘 방어는 비-split enum 오분류보다 우선 — 반복 재발 축이 'split 감점
    유실'이므로, category=alignment 로 잘못 와도 텍스트에 스플릿/벌림이 있으면 split."""
    d = _v11_kipup_split_diff(fault_category="alignment")
    fk = vision_veto.fault_key_from_difference(d)
    assert ipsf_criteria.criteria_for_fault(fk, d, _measured()) == ("split_angle",)


def test_criteria_for_fault_category_severity_invariant():
    """ND-02 불변: enum 라우팅도 severity 를 읽지 않는다."""
    d_minor = _v11_kipup_split_diff(fault_category="split_angle", severity="minor")
    d_major = _v11_kipup_split_diff(fault_category="split_angle", severity="major")
    fk_minor = vision_veto.fault_key_from_difference(d_minor)
    fk_major = vision_veto.fault_key_from_difference(d_major)
    assert (ipsf_criteria.criteria_for_fault(fk_minor, d_minor, _measured())
            == ipsf_criteria.criteria_for_fault(fk_major, d_major, _measured()))


def test_fault_categories_locked_vocab():
    """FAULT_CATEGORIES = 기존 criterion/faultKey 체계와 1:1 대응 고정 어휘 —
    새 분류 발명 금지. 라우터 단독-결정 집합은 enum 의 부분집합."""
    assert vision_veto.FAULT_CATEGORIES == (
        "split_angle", "limb_extension", "pole_gap", "alignment", "grip", "other",
    )
    assert ipsf_criteria._CATEGORY_DECISIVE <= frozenset(vision_veto.FAULT_CATEGORIES)


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
    # 밴드-부재 의미 유지 (quick-260705-k8h 후): 50/75/90 floor 없음 — huge deviation
    # 3건이 각각 per-record 상한 -20 으로 클램프돼 final == 100 - round(3 × cap) == 40
    # (< 50, 상수 파생 구조 단언 — sweep 수치 타깃 아님). record 단위 cap 은 밴드가
    # 아니다(명시 규칙 클램프) — final 단위 floor/ceiling 은 여전히 없음.
    b = _tally(_measured(leg=500.0, arm=500.0, split=500.0),
               _ctx([_diff("무릎", "굽음")]))
    assert b.final == 100 - round(3 * deduction_engine.PER_RECORD_DEDUCTION_CAP) == 40
    assert b.final < 50  # 50-floor 밴드 부재 증거
    # source guard — no min-band near the return.
    src = (pathlib.Path(deduction_engine.__file__).read_text(encoding="utf-8"))
    assert "min(100" not in src
    assert "min(final" not in src


def test_deadzone_and_slope():
    in_tol = _tally(_measured(leg=5.0), _ctx([_diff("무릎", "굽음")]))
    assert all(r.points == 0 for r in in_tol.records if r.criterion == "leg_extension") \
        or all(r.criterion != "leg_extension" for r in in_tol.records)
    finals = []
    # sub-cap 영역 devs (over 5/10/15 → raw 6/12/18 < 상한 20) — strict 단조 단언 보존.
    # cap 초과 영역의 포화(동점)는 per-record cap 전용 테스트에서 단언 (quick-260705-k8h).
    for dev in (0.0, 25.0, 30.0, 35.0):
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
    # quick-260705-k8h: 구 fixture(leg 20 vs 40)는 fallback -20 vs cap-포화 -20 동점이
    # 되므로 sub-cap granular 영역(over 5/15 → raw 6/18 < 상한 20)으로 교체 —
    # strict 단조 단언 보존. cap 초과 포화(동점)는 cap 전용 테스트 소관.
    small = _tally(_measured(leg=25.0), _ctx([]),
                   dimension_overall=80, quantification=_unavailable_quant())
    large = _tally(_measured(leg=35.0), _ctx([]),
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
    # sub-cap devs (over 5/10/15 → raw < 상한 20) — strict 단조 보존, cap 포화(동점)는
    # per-record cap 전용 테스트 소관 (quick-260705-k8h).
    finals = [_tally(_measured(split=d), _ctx([])).final for d in (0.0, 25.0, 30.0, 35.0)]
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
        # leg=40 → capped record 포함 (quick-260705-k8h) — cap-인지 키 형상 helper.
        # rawPoints(float)/capApplied(bool)는 scalar 라 flat 루프 자동 통과.
        _assert_record_keys(rec)
        for v in rec.values():
            assert not isinstance(v, (list, dict)), "nested array/dict 금지(Firestore-flat)"
    assert d["final"] == max(0, round(100.0 + sum(r["points"] for r in d["records"])))


# ── 25-02 review CR-01 — fold 멤버 라우팅 보존 ────────────────────────────────


def test_folded_leg_group_preserves_split_routing_via_members():
    """'스플릿 부족'+'무릎 굽음' 동시 언급이 keypoint_set=leg 한 그룹으로 fold 돼도
    split_angle 라우팅 + vision-측정 주입(belle 결정 A)이 보존된다 (CR-01 회귀).

    fold 대표가 무릎(major)로 뽑혀도 라우팅은 _memberFaults 각각으로 수행 —
    split 경로가 대표-선정 복권으로 소실되면 kip-up fault 88→~99 FP 재복귀 경로.
    """
    from sunity_shared.analysis import gemini_vision_scorer as gvs

    def d(body_part, fault_state, severity, dev):
        return {
            "body_part": body_part, "correct_state": "",
            "fault_state": fault_state, "severity": severity,
            "approx_angle_deviation_deg": dev,
        }

    per_call = [
        [d("스플릿", "각도 부족", "moderate", 30.0), d("무릎", "굽음", "major", 0)],
        [d("스플릿", "각도 부족", "moderate", 30.0), d("무릎", "굽음", "major", 0)],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="lower_body", min_support_k=2,
    )
    assert len(supported) == 1, "스플릿+무릎 전부 keypoint_set=leg → 한 그룹 fold"
    assert "무릎" in str(supported[0].get("body_part")), "대표 = major 무릎 (split 은 대표 아님)"

    b = _tally(_measured(), _ctx(supported))
    split_recs = [r for r in b.records if r.criterion == "split_angle"]
    assert len(split_recs) == 1, "멤버 라우팅으로 split_angle 경로 보존 (CR-01)"
    assert split_recs[0].source == "vision"
    assert split_recs[0].deviation_source == "reference_relative"


def test_routing_members_fallback_without_member_meta():
    """_memberFaults 부재(구 캐시/직접 구성 diff) → diff 자신 1개로 라우팅 (하위호환)."""
    diff = _diff("무릎", "굽음")
    assert deduction_engine._routing_members(diff) == [diff]
    b = _tally(_measured(leg=40.0), _ctx([diff]))
    assert any(r.criterion == "leg_extension" for r in b.records)


# ── 25-02 pod sweep FAIL 재현 — 실제 형상(fold→rich 캐시 왕복→ctx→tally) ──────


def _kipup_like_supported_via_rich_roundtrip(split_dev, sibling_dev):
    """kip-up sweep 관측 재현 fixture — 합성 지름길 금지: 실제 프로덕션 형상 경유.

    fold(supportCount 3, 3 distinct call) → _rich_to_doc/_rich_from_doc(캐시 왕복) 를
    거친 supported 를 반환. 산출 faultKey 는 관측 JSON 과 동일:
    {keypoint_set: leg, part_scope: line, side: unknown, fault_kind: pole_gap_or_bent}.
    """
    from sunity_shared.analysis import gemini_vision_scorer as gvs

    def d(body_part, fault_state, dev):
        return {
            "body_part": body_part, "correct_state": "",
            "fault_state": fault_state, "severity": "moderate",
            "approx_angle_deviation_deg": dev,
        }

    per_call = [
        [d("양쪽 다리", "굽고 벌어짐 부족", sibling_dev)],   # 대표(최고 dev) 후보
        [d("다리 스플릿", "벌어짐 부족", split_dev)],          # split 멤버
        [d("다리", "굽음", 5.0)],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="line", min_support_k=2,
    )
    assert len(supported) == 1
    fk = supported[0]["_faultKey"]
    assert fk.to_dict() == {
        "part_scope": "line", "side": "unknown",
        "keypoint_set": "leg", "fault_kind": "pole_gap_or_bent",
    }, "관측 JSON 의 faultKey 형상과 일치해야 재현 fixture 성립"
    assert supported[0]["_supportCount"] == 3
    # 실제 프로덕션 rich 캐시 왕복 형상 경유 (cold store → warm hit 동일 경로).
    rich = {
        "status": "candidate_verdict", "verdict": None,
        "supported_differences": supported,
        "root_cause_hypotheses": [], "telemetry": {},
    }
    doc = gvs.VisionVetoCache._rich_to_doc(rich)
    return gvs.VisionVetoCache._rich_from_doc(doc)["supported_differences"]


def test_split_member_without_dev_inherits_parent_vision_deviation():
    """pod sweep FAIL(kip-up fault 100) 회귀: split 멤버가 측정 편차 payload 를 안 들고
    있어도 부모(fold 대표)의 vision 측정값을 승계해 split_angle 이 발화한다."""
    supported = _kipup_like_supported_via_rich_roundtrip(split_dev=None, sibling_dev=28.0)
    ctx = vision_veto.VisionFaultContext(
        collection_status="candidate_verdict", verdict=None,
        supported_differences=list(supported), root_cause_hypotheses=[],
        selected_frame_pairs=[], alignment={}, telemetry={}, cap_would_apply=True,
    )
    b = _tally({}, ctx)
    split_recs = [r for r in b.records if r.criterion == "split_angle"]
    assert len(split_recs) == 1, "승계 없으면 md 미주입 → 미발화 → 100 FP 재발"
    assert split_recs[0].source == "vision"
    # 부모 대표(dev 28)의 측정값이 쓰였는가 — over-tol = 28 − 20 = 8.
    assert split_recs[0].deviation == pytest.approx(8.0)


def test_split_member_own_dev_takes_priority_over_parent():
    """split 멤버 자신의 측정값이 있으면 그것이 우선 (부모 승계는 부재 시 폴백만)."""
    supported = _kipup_like_supported_via_rich_roundtrip(split_dev=30.0, sibling_dev=50.0)
    ctx = vision_veto.VisionFaultContext(
        collection_status="candidate_verdict", verdict=None,
        supported_differences=list(supported), root_cause_hypotheses=[],
        selected_frame_pairs=[], alignment={}, telemetry={}, cap_would_apply=True,
    )
    b = _tally({}, ctx)
    split_recs = [r for r in b.records if r.criterion == "split_angle"]
    assert len(split_recs) == 1
    # 멤버 자신의 30 사용 — over-tol = 10 (부모 50 이면 30 이어야 함).
    assert split_recs[0].deviation == pytest.approx(10.0)


# ── 25-04 #3(a) — 측정 rubric: 각도쌍 산술 편차 + 멤버 median 집계 ────────────


def test_split_vision_arithmetic_pair_preferred_over_approx():
    """명시 각도쌍(student/reference)이 있으면 산술 편차가 approx 추정을 대체한다.

    (a) 측정 강건화: Gemini 의 "편차 한 방 추정"(approx 99)이 아니라 각도쌍의 산술
    |180−150| = 30 이 감점 입력 — over = 30 − tol 20 = 10."""
    diff = {"body_part": "스플릿", "fault_state": "벌어짐 부족", "severity": "moderate",
            "approx_angle_deviation_deg": 99,
            "student_angle_deg": 150.0, "reference_angle_deg": 180.0}
    rec = [r for r in _tally({}, _ctx([diff])).records
           if r.criterion == "split_angle"][0]
    assert rec.source == "vision"
    assert rec.deviation == pytest.approx(10.0), "산술 30 사용 — approx 99 아님"


def test_split_vision_pair_zero_deviation_no_injection():
    """각도쌍이 동일(산술 편차 0)이면 approx 로 폴백하지 않는다 — '재봤더니 차이 없음'
    을 approx 추정으로 뒤집는 모순 주입 금지(honest, 위양성 방어)."""
    diff = {"body_part": "스플릿", "fault_state": "벌어짐 부족", "severity": "moderate",
            "approx_angle_deviation_deg": 30,
            "student_angle_deg": 175.0, "reference_angle_deg": 175.0}
    b = _tally({}, _ctx([diff]))
    assert not any(r.criterion == "split_angle" for r in b.records)


def test_split_vision_median_across_members():
    """split-라우팅 멤버의 측정 추정치가 여럿이면 median(lower-middle) 집계 주입 —
    first-wins 단일 추정이 tol 경계를 넘나드는 변동 완화 ((a) run3 20° vs prod 30°)."""
    def m(part, dev):
        return {"body_part": part, "fault_state": "스플릿 각도 부족",
                "severity": "moderate", "approx_angle_deviation_deg": dev}

    diff = {**m("양다리", 30.0),
            "_memberFaults": [m("양다리", 30.0), m("오른쪽 다리 스플릿", 20.0),
                              m("왼쪽 다리 스플릿", 26.0)]}
    # 비어있지 않은 md 를 전달해야 엔진이 같은 객체를 mutate (`measured or {}` 폴백 회피).
    md = {"angle_vs_reference__left_shoulder": 0.5}  # below-tol seed(dead-zone, 무감점)
    b = _tally(md, _ctx([diff]))
    assert md.get("split_angle") == pytest.approx(26.0), "median(20,26,30) = 26"
    rec = [r for r in b.records if r.criterion == "split_angle"][0]
    assert rec.deviation == pytest.approx(6.0)  # 26 − tol 20


def test_split_vision_median_even_count_lower_middle():
    """짝수 개수 추정치는 lower-middle(보수적 — 감점 비부풀림) 채택."""
    def m(part, dev):
        return {"body_part": part, "fault_state": "스플릿 부족",
                "severity": "moderate", "approx_angle_deviation_deg": dev}

    diff = {**m("양다리", 40.0), "_memberFaults": [m("양다리", 40.0), m("다리 스플릿", 28.0)]}
    md = {"angle_vs_reference__left_shoulder": 0.5}  # 비어있지 않은 md (mutate 관찰용)
    _tally(md, _ctx([diff]))
    assert md.get("split_angle") == pytest.approx(28.0), "짝수 → lower-middle(28), 평균/40 아님"


def test_split_vision_median_geometric_md_still_wins():
    """geometric md["split_angle"] 실재 시 median 집계 경로 자체 비활성 (기존 우선순위 불변)."""
    def m(part, dev):
        return {"body_part": part, "fault_state": "스플릿 부족",
                "severity": "moderate", "approx_angle_deviation_deg": dev}

    diff = {**m("양다리", 90.0), "_memberFaults": [m("양다리", 90.0), m("다리 스플릿", 80.0)]}
    rec = [r for r in _tally(_measured(split=25.0), _ctx([diff])).records
           if r.criterion == "split_angle"][0]
    assert rec.source == "geometry"
    assert rec.deviation == pytest.approx(5.0)


# ── 25-04 sweep FAIL #1 회귀 — 실아티팩트 verbatim fixture ────────────────────
#
# fixture = phase25 Run 2 (HEAD 87978fe, cold 1783154115) kip-up fault 가 hit 한
# Firestore gemini_cache doc 의 verbatim 복사본 (vision_veto:8c206887...:v10.1:v7.0:
# agg3:whole_fanout, 2026-07-04 덤프 — 손 재구성 아님). v10.1 실출력은 split 어휘가
# body_part 가 아니라 fault_state 에 있다(body_part="양다리"/"오른쪽 다리") — body_part
# 단독 라우팅(구 rule 1)이면 split_angle 미발화 → vision 측정편차 미주입 → 99/100.


_KIPUP_REAL_CACHE_DOC = (
    pathlib.Path(__file__).parent / "fixtures" / "gemini_responses"
    / "phase25_kipup_agg3_rich_cache_doc.json"
)


def _kipup_real_cache_ctx():
    """실캐시 doc → 실경로 그대로 _rich_from_doc(캐시 hit 경로) → VisionFaultContext."""
    from sunity_shared.analysis import gemini_vision_scorer as gvs

    doc = json.loads(_KIPUP_REAL_CACHE_DOC.read_text(encoding="utf-8"))
    rich = gvs.VisionVetoCache._rich_from_doc(doc)
    return vision_veto.VisionFaultContext(
        collection_status="candidate_verdict",
        verdict=rich["verdict"],
        supported_differences=list(rich["supported_differences"]),
        root_cause_hypotheses=list(rich["root_cause_hypotheses"]),
        selected_frame_pairs=[], alignment={}, telemetry=rich["telemetry"],
        cap_would_apply=True,
    )


def test_phase25_kipup_real_cache_doc_injects_split_deviation():
    """sweep FAIL #1 회귀 (kip-up fault 99, split 주입 유실): 실캐시 doc 그대로
    tally 하면 split 멤버(fault_state 에만 '스플릿')가 split_angle 로 라우팅되고
    vision 측정편차(대표 멤버 20°)가 md 에 주입되어야 한다.

    md seed 는 실아티팩트 cold record 재현(angle_vs_reference__left_shoulder 20.6 —
    deductionBreakdown.records[0].measuredValue). 주입된 20° 는 tol 20° 와 동치라
    over 0(dead-zone, record 미방출) — 이 캐시의 최종 99 유지는 측정값 소관
    (Gemini 비결정 트랙, sweep 근본원인 #2)이지 라우팅 유실이 아니다."""
    ctx = _kipup_real_cache_ctx()
    md = {"angle_vs_reference__left_shoulder": 20.6}  # 실아티팩트 cold seed 재현
    b = _tally(md, ctx)
    # 회귀 본체: pre-fix 는 split 미라우팅 → md 미주입 (belle 결정 A 경로 유실).
    assert md.get("split_angle") == pytest.approx(20.0), \
        "split 멤버(fault_state 스플릿) 라우팅 미발화 → vision 측정편차 미주입 재발"
    # 실아티팩트와 동일: dev 20 == tol 20 → dead-zone (split record 미방출, final 99).
    assert not [r for r in b.records if r.criterion == "split_angle"]
    assert [r.criterion for r in b.records] == ["angle_vs_reference__left_shoulder"]
    assert b.final == 99
    # split 결함이 coverage gap 으로 새지 않는다.
    assert not [g for g in b.coverage_gaps if g["keypointSet"] == "leg"]


def test_phase25_kipup_real_members_route_split_and_leg():
    """실아티팩트 멤버 단위 라우팅: '스플릿' fault_state 멤버 2건(양다리/오른쪽 다리)
    → split_angle, 무릎-굽음 멤버 3건 → leg_extension (라우터 불변 존중)."""
    ctx = _kipup_real_cache_ctx()
    diff = ctx.supported_differences[0]
    members = deduction_engine._routing_members(diff)
    assert len(members) == 5, "실캐시 _memberFaults 5건이 라우팅 대상"
    routed = [
        ipsf_criteria.criteria_for_fault(deduction_engine._fault_key_for(m), m, {})
        for m in members
    ]
    split_members = [m for m, r in zip(members, routed) if r == ("split_angle",)]
    leg_members = [m for m, r in zip(members, routed) if r == ("leg_extension",)]
    assert len(split_members) == 2
    assert all("스플릿" in str(m.get("fault_state")) for m in split_members)
    assert all("스플릿" not in str(m.get("body_part")) for m in split_members), \
        "v10.1 실출력: split 어휘는 body_part 에 없다 — combined 라우팅 필요 근거"
    assert len(leg_members) == 3


# ── 25-02 review WR-04 — 측정 substrate 실재 시 shoulder/hip gap 억제 ─────────


def test_shoulder_gap_suppressed_when_measured_substrate_exists():
    """WR-04: 같은 관절의 angle_vs_reference 측정이 md 에 실재하면 'substrate deferred'
    gap 대신 측정 criterion 반환 — '측정해 감점했는데 측정 못 했다' 자기모순 제거."""
    diff = _diff("왼쪽 어깨", "정렬 흐트러짐")
    md = {"angle_vs_reference__left_shoulder": 40.4}
    out = ipsf_criteria.criteria_for_fault(None, diff, md)
    assert not isinstance(out, ipsf_criteria.CoverageGap)
    assert out == ("angle_vs_reference__left_shoulder",)

    # 측정 부재면 기존 gap 유지 (deferred substrate 정직 노출 — 억제 아님).
    out2 = ipsf_criteria.criteria_for_fault(None, diff, {})
    assert isinstance(out2, ipsf_criteria.CoverageGap)
    assert out2.keypoint_set == "shoulder"

    # NaN substrate 는 실재 아님 → gap 유지.
    out3 = ipsf_criteria.criteria_for_fault(
        None, diff, {"angle_vs_reference__left_shoulder": float("nan")}
    )
    assert isinstance(out3, ipsf_criteria.CoverageGap)


def test_hip_gap_suppressed_only_for_measured_side():
    """hip gap 억제는 측정 실재 side 의 criterion 만 반환 (미측정 side 미활성)."""
    md = {"angle_vs_reference__right_hip": 25.0}
    out = ipsf_criteria.criteria_for_fault(None, _diff("골반", "처짐"), md)
    assert out == ("angle_vs_reference__right_hip",)


def test_tally_no_shoulder_gap_and_record_contradiction():
    """end-to-end: 어깨 측정+짚임 → 감점 record 방출 AND shoulder gap 미방출 (보고 모순 0)."""
    md = {"angle_vs_reference__left_shoulder": 40.4}
    b = _tally(md, _ctx([_diff("왼쪽 어깨", "정렬 흐트러짐")]))
    assert any(r.criterion == "angle_vs_reference__left_shoulder" for r in b.records)
    assert not any(
        g.get("keypointSet") == "shoulder" for g in b.coverage_gaps
    ), "같은 결함에 감점 record + substrate-deferred gap 동시 방출 금지 (WR-04)"


# ── per-record 감점 상한 -20 (quick-260705-k8h, belle 승인) ──────────────────
# belle 실기기 관측: kip-up 잘못된 시연이 단일 대형 결함 record 폭주 감점으로 26점.
# run6 실데이터 4-규칙 비교에서 체감가중/RSS 는 작은-결함-다수 동작을 역전시켜 탈락 —
# 관절당 상한 -20 채택(IPSF 결함 유형별 감점 상한 구조 정합). 투명성
# ([[scoring-must-be-transparent-deduction-tally]])은 rawPoints/capApplied 로 보존.
# 실영상 점수 리터럴 타깃 금지 — 전 단언은 상수(PER_RECORD_DEDUCTION_CAP) 파생 값만.


def test_per_record_cap_clamps_and_exposes_raw():
    # leg=60 → over 40 × slope 1.2 = raw 48 > 상한 20 → points 는 -20 클램프,
    # 원 감점(rawPoints)과 capApplied 마커로 투명 내역 유지.
    b = _tally(_measured(leg=60.0), _ctx([]))
    rec = [r for r in b.records if r.criterion == "leg_extension"][0]
    assert rec.points == -deduction_engine.PER_RECORD_DEDUCTION_CAP == -20.0
    d = rec.to_dict()
    assert d["rawPoints"] == -48.0
    assert d["capApplied"] is True
    assert b.final == 80


def test_per_record_cap_under_threshold_byte_compatible():
    # leg=30 → raw 12 < 상한 → 기존 11키 정확 동등 (rawPoints/capApplied 키 자체 부재
    # — 구 앱/legacy doc byte-호환 회귀 가드, 구현 전에도 GREEN 인 의도적 가드).
    b = _tally(_measured(leg=30.0), _ctx([]))
    rec = [r for r in b.records if r.criterion == "leg_extension"][0]
    assert set(rec.to_dict()) == set(models.DEDUCTION_RECORD_KEYS)


def test_per_record_cap_boundary_exact_cap_not_flagged(monkeypatch):
    # 경계 == 클램프 아님. slope 1.2 로는 raw 정확히 20.0 을 만드는 깔끔한 dev 가 없어
    # monkeypatch 가 결정적 경계 검증 수단 — 튜닝 상수 변경 아님, 메커니즘 검증.
    monkeypatch.setattr(deduction_engine, "PER_RECORD_DEDUCTION_CAP", 12.0)
    b = _tally(_measured(leg=30.0), _ctx([]))  # over 10 × slope 1.2 = raw 정확히 12.0
    rec = [r for r in b.records if r.criterion == "leg_extension"][0]
    assert rec.points == -12.0
    assert set(rec.to_dict()) == set(models.DEDUCTION_RECORD_KEYS), \
        "raw == cap 정확 경계는 상한 이하 취급 — rawPoints/capApplied 미방출"
    # 대비쌍: cap 11.9 로 재패치 → 같은 입력이 클램프됨.
    monkeypatch.setattr(deduction_engine, "PER_RECORD_DEDUCTION_CAP", 11.9)
    b2 = _tally(_measured(leg=30.0), _ctx([]))
    rec2 = [r for r in b2.records if r.criterion == "leg_extension"][0]
    d2 = rec2.to_dict()
    assert rec2.points == -11.9
    assert d2["capApplied"] is True
    assert d2["rawPoints"] == -12.0


def test_per_record_cap_final_sum_consistency():
    # 둘 다 capped → final 은 capped 값 Σ 기준: 100 - 20 - 20 = 60 (raw 합 -96 아님).
    b = _tally(_measured(leg=60.0, arm=60.0), _ctx([]))
    assert b.final == max(0, round(100 + sum(r.points for r in b.records))) == 60
    assert b.to_dict()["final"] == 60


def test_fallback_record_not_capped():
    # fallback record(whole-score 폴백)는 클램프 비대상 — final == dimension_overall
    # 불변식(contract.md §10.5) + 100+Σpoints==final 추적성 동시 보존.
    b = _tally(_measured(), _ctx([]), dimension_overall=62,
               quantification=_unavailable_quant())
    fb = [r for r in b.records if r.criterion == "dimension_overall_fallback"][0]
    assert fb.points == -38.0  # < -20 허용 (criterion 감점 record 전용 상한)
    assert set(fb.to_dict()) == set(models.DEDUCTION_RECORD_KEYS)
    assert b.final == 62


def test_per_record_cap_deterministic():
    # 결정성(ND-07): 동일 입력 2회 → to_dict() byte-identical (rawPoints/capApplied 포함).
    b1 = _tally(_measured(leg=60.0), _ctx([]))
    b2 = _tally(_measured(leg=60.0), _ctx([]))
    assert b1.to_dict() == b2.to_dict()
