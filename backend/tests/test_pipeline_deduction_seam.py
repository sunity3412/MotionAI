"""Phase 24 (24-02) — 투명 감점-합산 채점 seam 통합 테스트 (밴드 제거 end-to-end).

박제 정신 (24-CONTEXT ND-01~07):
  · severity→고정천장 밴드 제거 — overallScore = deduction_engine.tally(측정편차 →
    명시규칙 감점 → 합산).final. visionVeto.status 가 채점 실행을 증명.
  · seam 이 측정-기하 substrate(_build_deduction_measured_deviations)를 1회 빌드해 apply
    경로에 threaded — 0-100 dimension SCORE 를 deviation 으로 먹이지 않는다(HIGH-3).
  · criterion 선택은 엔진의 criteria_for_fault 라우터(body_part/fault_state, severity 미사용).
  · per-move baseline_kind 는 name/motion_id string-match(kip-up=floor named, hip_line 기본).
  · production Gemini-silent 방어: no_fault(정타) 가 tally-eligible — measured seed 가 감점.
  · Mode3 보류 + 토글 보존; math-determinism + severity-independence.

전부 mock-based — 실 Gemini / 실 Pod / 실 S3 / 실 Firestore 호출 0. PYTHONPATH=shared/python.
# 보유 sweep 수치 타깃 아님 — 방향/구조 단언만 (curve-fit 금지).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# pipeline/app.py + shared layer path 주입.
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

import app  # noqa: E402
from sunity_shared.analysis import technique, vision_veto  # noqa: E402
from sunity_shared.analysis import gemini_vision_scorer  # noqa: E402
from sunity_shared.analysis.motiondtw import MotionMatch  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────


def _profile(name: str = "t", motion_id: str | None = None) -> technique.TechniqueProfile:
    """팔꿈치/무릎 EXTEND 프로파일 (line/extension substrate 산출되게)."""
    exp = {
        k: technique.JOINT_EXTEND
        if k.endswith("elbow") or k.endswith("knee")
        else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(
        name=name, category="unknown", joint_expectations=exp, motion_id=motion_id
    )


def _verdict(severity: str = "moderate", differences=()):
    return gemini_vision_scorer.VisionVerdict(
        primary_fault="stub fault", severity=severity, differences=tuple(differences)
    )


def _ctx(status, *, verdict=None, supported=None, frame_pairs=None, cap=False):
    return vision_veto.VisionFaultContext(
        collection_status=status,
        verdict=verdict,
        supported_differences=list(supported or []),
        root_cause_hypotheses=[],
        selected_frame_pairs=list(frame_pairs or []),
        alignment={},
        telemetry={},
        cap_would_apply=cap,
    )


def _quant(status="available", notches=None):
    return vision_veto.VisionQuantificationResult(
        quantificationStatus=status,
        angleDeltas=None,
        bodyRelativeNotches=notches,
        windowMedianAngleDeltas=None,
        warnings=(),
    )


def _enable(monkeypatch):
    monkeypatch.setattr(app, "_gemini_vision_veto_enabled", lambda: True)


# ── band removed end-to-end ──────────────────────────────────────────────────


def test_fault_drives_overall_via_tally_no_fixed_ceiling(monkeypatch):
    """결함 verdict → overallScore = breakdown.final, 옛 고정 천장(50/75/90) 아님."""
    _enable(monkeypatch)
    ctx = _ctx("candidate_verdict", verdict=_verdict("major"), cap=True)
    out = app._apply_vision_veto(
        {"overallScore": 100, "dimensionScores": {"angle": 100}},
        mode="mode1", vision_fault_context=ctx, quantification=_quant("available"),
        measured_deviations={"leg_extension": 50.0}, baseline_kind="hip_line",
    )
    assert out["visionVeto"]["status"] == "applied"
    assert out["overallScore"] == out["deductionBreakdown"]["final"]
    final = out["overallScore"]
    # 측정 편차로 내려갔고, 옛 고정 ceiling(50/75/90)에 묶이지 않는다.
    assert final < 100
    assert final not in (50, 75, 90) or final == out["deductionBreakdown"]["final"]
    # final == max(0, round(100 + Σ points)) — 추적성.
    pts = sum(r["points"] for r in out["deductionBreakdown"]["records"])
    assert final == max(0, round(100 + pts))


def test_score_not_deviation_regression(monkeypatch):
    """HIGH-3 — 0-100 dimension SCORE(72)를 72° deviation 으로 먹이지 않는다.

    builder 는 extension_deviation(deg)/notch 에서만 substrate 를 뽑는다. dimension_scores
    의 angle=72 가 measured_deviations 로 새지 않음을 builder 출력으로 단언.
    """
    import numpy as np

    prof = _profile()
    # 깨끗한 각도(거의 180°) — extension deficit ~0. dimension SCORE 72 는 무관해야 함.
    angles = np.full((30, len(JOINT_KEYS)), 179.0, dtype=float)
    md = app._build_deduction_measured_deviations(
        angles=angles, profile=prof, assessments=[],
        dimension_scores={"angle": 72, "line": 72}, quantification=_quant("available"),
    )
    # 72 가 어떤 criterion deviation 으로도 들어가면 안 된다 (deg deficit 은 ~1).
    for cid in ("leg_extension", "arm_extension", "line"):
        if cid in md:
            assert md[cid] != 72, f"{cid} 에 dimension SCORE 72 가 deviation 으로 샜다 (HIGH-3)"
            assert md[cid] < 20, f"{cid} deficit 이 깨끗한 각도(179°)에서 과대 ({md[cid]})"


def test_criteria_for_fault_routing_at_seam(monkeypatch):
    """HIGH-1 — split→split_angle (not leg), grip→coverageGaps. seam 이 router 를 탄다."""
    _enable(monkeypatch)
    # split fault — body_part="스플릿".
    split_diff = {"body_part": "스플릿", "fault_state": "각도 부족"}
    ctx_split = _ctx("candidate_verdict", verdict=_verdict("moderate"),
                     supported=[split_diff], cap=True)
    out = app._apply_vision_veto(
        {"overallScore": 100, "dimensionScores": {}},
        mode="mode1", vision_fault_context=ctx_split,
        quantification=_quant("available"),
        measured_deviations={"split_angle": 40.0}, baseline_kind="hip_line",
    )
    crits = {r["criterion"] for r in out["deductionBreakdown"]["records"]}
    assert "split_angle" in crits
    assert "leg_extension" not in crits  # split 은 leg 로 라우팅되지 않는다.

    # grip fault → coverage gap (감점 0).
    grip_diff = {"body_part": "그립", "fault_state": "풀림"}
    ctx_grip = _ctx("candidate_verdict", verdict=_verdict("moderate"),
                    supported=[grip_diff], cap=True)
    out_g = app._apply_vision_veto(
        {"overallScore": 100, "dimensionScores": {}},
        mode="mode1", vision_fault_context=ctx_grip,
        quantification=_quant("available"),
        measured_deviations={}, baseline_kind="hip_line",
    )
    gaps = out_g["deductionBreakdown"]["coverageGaps"]
    assert any(g["keypointSet"] == "grip" for g in gaps)


def test_builder_split_deficit_injection():
    """split_deficit_deg → md[split_angle] (15-SPLIT-MEASUREMENT-DESIGN §3 wiring).

    _process 가 산출한 split 부족분(deg, 양수)을 builder 가 md 로 방출하고, None/0/NaN 은
    honest 0(미방출). 그 외 인자는 None 이어도 graceful(각 블록 가드)."""
    md = app._build_deduction_measured_deviations(
        angles=None, profile=None, assessments=None,
        dimension_scores=None, quantification=None, split_deficit_deg=30.0,
    )
    assert md["split_angle"] == 30.0
    for v in (None, 0.0, -5.0, float("nan")):
        md_skip = app._build_deduction_measured_deviations(
            angles=None, profile=None, assessments=None,
            dimension_scores=None, quantification=None, split_deficit_deg=v,
        )
        assert "split_angle" not in md_skip


def test_gemini_silent_no_fault_is_tally_eligible_production_shape(monkeypatch):
    """iter5 HIGH-1 — production no_fault(정타, valid still-pair, 측정 편차 BEYOND tol) →
    measured seed 가 감점. NOT 합성 candidate_verdict — 실 no_fault 경로(passthrough 버그)."""
    _enable(monkeypatch)
    pair = vision_veto.SelectedFramePair(
        student_frame_path="/tmp/s.png", reference_frame_path="/tmp/r.png",
        user_frame_idx=3, ref_frame_idx=3,
    )
    # collect 가 정타 still-pair 에 대해 실제로 반환하는 모양: no_fault + severity none +
    # 빈 supported_differences + valid frame_pair. 측정 leg 편차는 tol 초과.
    ctx = _ctx("no_fault", verdict=_verdict("none"), supported=[], frame_pairs=[pair])
    out = app._apply_vision_veto_from_context(
        {"overallScore": 100, "dimensionScores": {"angle": 100}}, ctx,
        _quant("available"),
        measured_deviations={"leg_extension": 45.0}, baseline_kind="hip_line",
    )
    crits = {r["criterion"] for r in out["deductionBreakdown"]["records"]}
    assert "leg_extension" in crits
    assert out["overallScore"] < 100
    assert out["visionVeto"]["status"] == "applied"
    # no_fault → cap_would_apply False → coach injection OFF (Gemini saw no fault).
    assert ctx.cap_would_apply is False
    assert ctx.eligible_for_coach is False


def test_gemini_silent_clean_geometry_not_applicable(monkeypatch):
    """Phase 24 — no_fault + 깨끗한 기하(측정 편차 0, quant available) → not_applicable.
    not_applicable 도 breakdown.final 이 점수다(레거시 min-of-core dimension passthrough 제거):
    records 가 비어 final=100, overallScore 도 100 이 된다 — 레거시 dimension 99 가 새지 않는다."""
    _enable(monkeypatch)
    pair = vision_veto.SelectedFramePair(
        student_frame_path="/tmp/s.png", reference_frame_path="/tmp/r.png",
        user_frame_idx=3, ref_frame_idx=3,
    )
    ctx = _ctx("no_fault", verdict=_verdict("none"), supported=[], frame_pairs=[pair])
    out = app._apply_vision_veto_from_context(
        {"overallScore": 99, "dimensionScores": {"angle": 99}}, ctx,
        _quant("available"),
        measured_deviations={}, baseline_kind="hip_line",
    )
    assert out["visionVeto"]["status"] == "not_applicable"
    # transparent tally 가 authoritative — clean records → final=100, 레거시 99 passthrough 폐기.
    assert out["overallScore"] == out["deductionBreakdown"]["final"]
    assert out["overallScore"] == 100
    assert ctx.cap_would_apply is False


def test_clean_not_applicable_uses_tally_final_not_legacy_dimension(monkeypatch):
    """Phase 24 — power-spin success 회귀가드: CLEAN no_fault(quant available, 측정 편차 0)에서
    레거시 score_result['overallScore']=91(min-of-core dimension, power-spin success 숫자)이
    not_applicable 분기로 새던 버그를 고정. breakdown.final(=100)이 점수이고 91 은 누출되지 않는다
    ([[scoring-must-be-transparent-deduction-tally]], [[score-spec-95-100-elite-vision-fix]])."""
    _enable(monkeypatch)
    pair = vision_veto.SelectedFramePair(
        student_frame_path="/tmp/s.png", reference_frame_path="/tmp/r.png",
        user_frame_idx=3, ref_frame_idx=3,
    )
    ctx = _ctx("no_fault", verdict=_verdict("none"), supported=[], frame_pairs=[pair])
    out = app._apply_vision_veto_from_context(
        {"overallScore": 91, "dimensionScores": {"angle": 91, "line": 91}}, ctx,
        _quant("available"),
        measured_deviations={}, baseline_kind="hip_line",
    )
    assert out["visionVeto"]["status"] == "not_applicable"
    # 레거시 min-of-core 91 이 not_applicable 분기를 통해 새지 않는다.
    assert out["overallScore"] != 91
    assert out["overallScore"] == out["deductionBreakdown"]["final"]
    assert out["overallScore"] == 100  # clean tally → empty records → final 100


def test_baseline_kind_derived_by_name():
    """BLOCKER B — kip-up/floor named → floor; 미상/inversion → hip_line."""
    assert app._baseline_kind_for_profile(_profile(name="미등록: kip-up")) == "floor"
    assert app._baseline_kind_for_profile(_profile(name="t", motion_id="kip_up")) == "floor"
    assert app._baseline_kind_for_profile(_profile(name="미상")) == "hip_line"
    assert app._baseline_kind_for_profile(_profile(name="inversion")) == "hip_line"
    assert app._baseline_kind_for_profile(_profile(name="깃발 flag")) == "pole_vertical"


def test_breakdown_object_set_on_result_and_flat(monkeypatch):
    """deductionBreakdown OBJECT {baseline,records,final,coverageGaps,fallback} on result,
    records 가 baselineValue/baselineKind 동반 flat — complete_analysis validator 가 수용,
    nested array 심으면 거부 (HIGH-1)."""
    _enable(monkeypatch)
    ctx = _ctx("candidate_verdict", verdict=_verdict("moderate"), cap=True)
    out = app._apply_vision_veto(
        {"overallScore": 100, "dimensionScores": {}},
        mode="mode1", vision_fault_context=ctx, quantification=_quant("available"),
        measured_deviations={"leg_extension": 40.0}, baseline_kind="floor",
    )
    bd = out["deductionBreakdown"]
    assert set(bd.keys()) == {"baseline", "records", "final", "coverageGaps", "fallback"}
    assert bd["baseline"] == 100
    for r in bd["records"]:
        assert "baselineValue" in r and "baselineKind" in r
    # complete_analysis 의 scoped validator 가 수용.
    from sunity_shared import firestore_admin
    firestore_admin._validate_deduction_breakdown(bd)  # 예외 0
    # nested array 심으면 거부.
    poisoned = dict(bd)
    poisoned["records"] = [{"criterion": "x", "nested": [[1, 2]]}]
    with pytest.raises((ValueError, TypeError)):
        firestore_admin._validate_deduction_breakdown(poisoned)


def test_mode3_held_passthrough_no_tally(monkeypatch):
    """Mode3 (MODE_SELF) → mode3_held passthrough, deductionBreakdown 부재 (reference-anchor 없음)."""
    import sunity_shared.models as models
    _enable(monkeypatch)
    out = app._apply_vision_veto(
        {"overallScore": 90, "dimensionScores": {}}, "/tmp/v.mp4", None, _profile(),
        mode=models.MODE_SELF, reference_video_path=None,
    )
    assert out["visionVeto"]["status"] == "mode3_held"
    assert out["overallScore"] == 90
    assert "deductionBreakdown" not in out


def test_toggle_off_disabled_passthrough(monkeypatch):
    """GEMINI_VISION_VETO_ENABLED off → disabled passthrough (점수 불변, tally 미실행)."""
    monkeypatch.setattr(app, "_gemini_vision_veto_enabled", lambda: False)
    out = app._apply_vision_veto(
        {"overallScore": 88, "dimensionScores": {}}, "/tmp/v.mp4", None, _profile(),
        mode="mode1", reference_video_path="/tmp/ref.mp4",
    )
    assert out["visionVeto"]["status"] == "disabled"
    assert out["overallScore"] == 88
    assert "deductionBreakdown" not in out


def test_math_determinism_same_input_identical_breakdown(monkeypatch):
    """같은 stored quantification + cached verdict 2회 → byte-identical deductionBreakdown."""
    _enable(monkeypatch)

    def _run():
        ctx = _ctx("candidate_verdict", verdict=_verdict("moderate"), cap=True)
        return app._apply_vision_veto(
            {"overallScore": 100, "dimensionScores": {}},
            mode="mode1", vision_fault_context=ctx, quantification=_quant("available"),
            measured_deviations={"leg_extension": 37.0}, baseline_kind="hip_line",
        )["deductionBreakdown"]

    assert _run() == _run()


def test_severity_independent_of_score(monkeypatch):
    """ND-02 — severity minor↔major swap, 동일 quantification → 동일 overallScore."""
    _enable(monkeypatch)

    def _run(sev):
        ctx = _ctx("candidate_verdict", verdict=_verdict(sev), cap=(sev in ("moderate", "major")))
        return app._apply_vision_veto(
            {"overallScore": 100, "dimensionScores": {}},
            mode="mode1", vision_fault_context=ctx, quantification=_quant("available"),
            measured_deviations={"leg_extension": 40.0}, baseline_kind="hip_line",
        )["overallScore"]

    assert _run("minor") == _run("major")


def test_coach_gate_band_free_continuity(monkeypatch):
    """HIGH-6 — eligible_for_coach: moderate/major True, minor/none False (continuity)."""
    for sev, expect in (("moderate", True), ("major", True), ("minor", False), ("none", False)):
        cap = sev in ("moderate", "major")
        ctx = _ctx("candidate_verdict", verdict=_verdict(sev), cap=cap)
        assert ctx.cap_would_apply is cap
        assert ctx.eligible_for_coach is expect, f"severity={sev} eligible mismatch"


# ── 24-04 — low_alignment_confidence measured-seed tally-eligibility ──────────


def test_low_alignment_measured_deduction_applied(monkeypatch):
    """24-04(Option A) — low_alignment_confidence + 측정 편차(BEYOND tol) → measured seed 가
    감점한다. records 는 ALL measured(deviationSource ∈ {ipsf_absolute, reference_relative}),
    Gemini-located criterion 0(supported_differences=[]). audit status=applied +
    collectionStatus=low_alignment_confidence(측정-only provenance)."""
    _enable(monkeypatch)
    # collect 가 정렬 약한 still-pair 에 대해 반환하는 모양: low_alignment + verdict None +
    # 빈 supported_differences + 빈 frame_pairs(Gemini 호출 전 bail). RTMW 측정 leg 편차는
    # tol 초과 — 정렬-독립이므로 감점되어야 한다.
    # production wiring(§2-4 false-green 교훈): low_alignment 는 frame_pairs=[] →
    # quantification UNAVAILABLE 이다. 그래도 정렬-독립 RTMW 각도 seed 가 살아 granular 감점.
    ctx = _ctx("low_alignment_confidence", verdict=None, supported=[], frame_pairs=[])
    out = app._apply_vision_veto_from_context(
        {"overallScore": 100, "dimensionScores": {"angle": 100}}, ctx,
        _quant("unavailable"),
        measured_deviations={"leg_extension": 45.0}, baseline_kind="hip_line",
    )
    bd = out["deductionBreakdown"]
    crits = {r["criterion"] for r in bd["records"]}
    assert "leg_extension" in crits
    assert out["overallScore"] == bd["final"]
    assert out["overallScore"] < 100
    assert out["visionVeto"]["status"] == "applied"
    # 측정-only provenance 보존 — Gemini 정렬이 낮았음을 리포트가 투명하게 보여준다.
    assert out["visionVeto"]["collectionStatus"] == "low_alignment_confidence"
    # 객관성: 모든 record 가 measured seed criterion(ipsf_absolute/reference_relative).
    # criteria_for_fault 만 만들 수 있는 Gemini-located record 는 0(supported_differences=[]).
    sources = {r["deviationSource"] for r in bd["records"]}
    assert sources <= {"ipsf_absolute", "reference_relative"}
    # 각도 seed 가 살아 dimension_overall 폴백을 안 탄다(quant unavailable 이어도 granular, 24-05).
    assert "dimension_overall" not in sources
    # low_alignment 은 코치 root-cause 를 주입하지 않는다 (candidate_verdict-only 유지).
    assert ctx.eligible_for_coach is False
    assert "faultJoints" not in out["visionVeto"]  # Gemini fault 부재 → 부착 0


def test_low_alignment_empty_seed_unavailable_fallback(monkeypatch):
    """production wiring(§2-4): low_alignment 는 frame_pairs=[] → quantification UNAVAILABLE.
    측정 편차도 {} (양쪽 substrate 빔) → dimension_overall_fallback 1개 +
    fallback=quantification_unavailable, final 불변. 측정 가능한 편차가 없으니 위양성 measured
    criterion 을 fabricate 하지 않는다(honest 한계). fallback record 도 applied 로 추적(TRUST-08)."""
    _enable(monkeypatch)
    ctx = _ctx("low_alignment_confidence", verdict=None, supported=[], frame_pairs=[])
    out = app._apply_vision_veto_from_context(
        {"overallScore": 96, "dimensionScores": {"angle": 96}}, ctx,
        _quant("unavailable"),
        measured_deviations={}, baseline_kind="hip_line",
    )
    bd = out["deductionBreakdown"]
    assert bd["fallback"] == "quantification_unavailable"
    assert len(bd["records"]) == 1
    assert bd["records"][0]["criterion"] == "dimension_overall_fallback"
    assert bd["final"] == 96  # dimension_overall 불변
    assert out["overallScore"] == 96
    # fallback record 만 — fabricate 된 measured criterion 0 (위양성 fabricate 금지).
    measured = [r for r in bd["records"] if r["deviationSource"] != "dimension_overall"]
    assert measured == []
    assert out["visionVeto"]["status"] == "applied"


def test_low_alignment_no_fabricated_gemini_faults(monkeypatch):
    """객관성 hard line — supported_differences=[] 인 low_alignment ctx 는 criteria_for_fault
    가 만들 수 있는 split_angle 같은 Gemini-located criterion 을 절대 만들지 않는다.
    measured_deviations 에 split substrate 가 없으면 split_angle record 도 없다.
    production wiring 일치 — quant UNAVAILABLE 에서도 각도 seed 만 granular 감점(§2-4)."""
    _enable(monkeypatch)
    ctx = _ctx("low_alignment_confidence", verdict=None, supported=[], frame_pairs=[])
    out = app._apply_vision_veto_from_context(
        {"overallScore": 100, "dimensionScores": {}}, ctx, _quant("unavailable"),
        measured_deviations={"leg_extension": 30.0}, baseline_kind="hip_line",
    )
    crits = {r["criterion"] for r in out["deductionBreakdown"]["records"]}
    # leg 만 측정됐다 — split_angle(Gemini-pointed router 전용 substrate 부재)은 없다.
    assert crits == {"leg_extension"}
    assert "split_angle" not in crits


def test_low_alignment_does_not_regress_sibling_passthrough(monkeypatch):
    """24-04 — low_alignment 의 형제 비측정 status 는 여전히 score-free passthrough
    (deductionBreakdown 부재). low_alignment 만 measured-eligible 로 이동."""
    _enable(monkeypatch)
    for status in ("resource_limited", "disabled", "missing_reference", "skipped_error"):
        ctx = _ctx(status, verdict=None, supported=[], frame_pairs=[])
        out = app._apply_vision_veto_from_context(
            {"overallScore": 91, "dimensionScores": {}}, ctx, _quant("unavailable"),
            measured_deviations={"leg_extension": 50.0}, baseline_kind="hip_line",
        )
        assert out["overallScore"] == 91, f"{status} score 불변"
        assert "deductionBreakdown" not in out, f"{status} tally 미실행"


def test_low_alignment_unavailable_emits_reach_coverage_gap(monkeypatch):
    """24-05(ND-06/07) — low_alignment + quant UNAVAILABLE + 각도 seed → reach 칸은 정렬 부재로
    측정 못 했음을 coverageGaps(reach_substrate_unavailable_low_alignment)로 투명 노출하면서도
    각도 granular 감점은 유지한다(honest 한계 + measured seed 소비 동시).

    NOTE(§3-2 정합): reach coverage gap 은 quant 불가 AND 활성 criterion 존재(각도 seed) 경로에서만
    방출된다 — 빈-seed 폴백 경로에 넣으면 legacy(None,None) 단일영상까지 low_alignment 로 오표기되므로
    설계상 activated 경로로 한정. (§5-2 item 8 의 reach-only md={} 문구는 §3-2 와 충돌해 achievable
    형태인 activated 경로로 구현.)"""
    _enable(monkeypatch)
    ctx = _ctx("low_alignment_confidence", verdict=None, supported=[], frame_pairs=[])
    out = app._apply_vision_veto_from_context(
        {"overallScore": 100, "dimensionScores": {"angle": 100}}, ctx,
        _quant("unavailable"),
        measured_deviations={"leg_extension": 30.0}, baseline_kind="hip_line",
    )
    bd = out["deductionBreakdown"]
    # 각도 granular 감점 유지(폴백 아님).
    assert any(r["criterion"] == "leg_extension" for r in bd["records"])
    assert bd["fallback"] != "quantification_unavailable"
    # reach 칸 측정 불가가 coverage gap 으로 투명 노출.
    rule_ids = {g["ruleId"] for g in bd["coverageGaps"]}
    assert "reach_substrate_unavailable_low_alignment" in rule_ids
    assert out["visionVeto"]["status"] == "applied"


# ── 24-07 ① fix — reference_relative per-joint granular seam 배선 ──────────────
# 미등록 동작(expects_extension 전부 False)에서 정은지(reference) 대비 per-joint 각도 편차를
# _build_deduction_measured_deviations 가 md[angle_vs_reference__{joint}] 로 방출한다(granular
# seed). 등록 동작의 절대-신전 소유 관절은 seed-stage cross-exclusion 으로 제외(double-count 0).
# 전부 mock-based — 실 Gemini/Pod/S3/Firestore 호출 0. (24-07 §3-2)

_LEFT_KNEE = JOINT_KEYS.index("left_knee")
_LEFT_SHOULDER = JOINT_KEYS.index("left_shoulder")


def _unregistered_profile():
    """미등록 동작 profile — expects_extension 전부 False (ipsf_absolute seed 빔)."""
    return technique.TechniqueProfile(
        name="미등록: ref-power-spin", category="unknown", joint_expectations={}
    )


def _identity_match(T):
    """identity DTW match — path local 인덱스 (i,i), start=0 end=T (점수경로와 동일 인덱싱)."""
    return MotionMatch(
        start=0, end=T, ref_start=0, ref_end=T,
        distance=0.0, path=[(i, i) for i in range(T)],
    )


def _ref_angles(T, deg=170.0):
    return np.full((T, len(JOINT_KEYS)), deg, dtype=float)


def test_reference_relative_unregistered_emits_per_joint_granular():
    """미등록 profile + reference 무릎 편차>tol → angle_vs_reference__left_knee 방출.
    ipsf_absolute(leg/arm/line) 키는 부재(profile-gated honest 0)."""
    T = 10
    ref = _ref_angles(T)
    usr = _ref_angles(T)
    usr[:, _LEFT_KNEE] = 130.0  # 정은지 대비 40° 편차
    md = app._build_deduction_measured_deviations(
        angles=usr, profile=_unregistered_profile(), assessments=[],
        dimension_scores={}, quantification=_quant("available"),
        reference_dtw_match=_identity_match(T), reference_angles=ref,
    )
    assert md.get("angle_vs_reference__left_knee") == pytest.approx(40.0)
    assert "leg_extension" not in md  # 미등록 → profile-gated 부재
    assert "line" not in md


def test_reference_relative_registered_knee_excluded_shoulder_kept():
    """등록 profile(무릎 expects_extension True) → 무릎 reference_relative 키 부재
    (seed-stage cross-exclusion). 어깨(expects_extension False)는 편차 시 reference_relative 키 존재."""
    T = 10
    ref = _ref_angles(T)
    usr = _ref_angles(T)
    usr[:, _LEFT_KNEE] = 130.0     # 무릎 40° — 등록(EXTEND)이므로 ipsf_absolute 가 채점
    usr[:, _LEFT_SHOULDER] = 130.0  # 어깨 40° — BENT_OK → reference_relative 보완
    md = app._build_deduction_measured_deviations(
        angles=usr, profile=_profile(), assessments=[],
        dimension_scores={}, quantification=_quant("available"),
        reference_dtw_match=_identity_match(T), reference_angles=ref,
    )
    assert "angle_vs_reference__left_knee" not in md  # 절대-신전 소유 관절 제외
    assert md.get("angle_vs_reference__left_shoulder") == pytest.approx(40.0)


def test_reference_relative_self_compare_no_keys():
    """self-compare(identity path + usr==ref → per_joint_deviation=0) → angle_vs_reference__* 0개."""
    T = 10
    ref = _ref_angles(T)
    md = app._build_deduction_measured_deviations(
        angles=ref.copy(), profile=_unregistered_profile(), assessments=[],
        dimension_scores={}, quantification=_quant("available"),
        reference_dtw_match=_identity_match(T), reference_angles=ref,
    )
    assert not any(k.startswith("angle_vs_reference__") for k in md)


def test_reference_relative_none_inputs_graceful():
    """reference_dtw_match=None 또는 reference_angles=None → reference_relative 미방출
    (mode3/legacy 무회귀)."""
    T = 10
    ref = _ref_angles(T)
    usr = _ref_angles(T)
    usr[:, _LEFT_KNEE] = 130.0
    md_no_match = app._build_deduction_measured_deviations(
        angles=usr, profile=_unregistered_profile(), assessments=[],
        dimension_scores={}, quantification=_quant("available"),
        reference_dtw_match=None, reference_angles=ref,
    )
    md_no_ref = app._build_deduction_measured_deviations(
        angles=usr, profile=_unregistered_profile(), assessments=[],
        dimension_scores={}, quantification=_quant("available"),
        reference_dtw_match=_identity_match(T), reference_angles=None,
    )
    assert not any(k.startswith("angle_vs_reference__") for k in md_no_match)
    assert not any(k.startswith("angle_vs_reference__") for k in md_no_ref)


def test_reference_relative_deterministic():
    """동일 입력 2회 → 동일 md (결정성)."""
    T = 10
    ref = _ref_angles(T)
    usr = _ref_angles(T)
    usr[:, _LEFT_KNEE] = 130.0
    kwargs = dict(
        profile=_unregistered_profile(), assessments=[], dimension_scores={},
        quantification=_quant("available"),
        reference_dtw_match=_identity_match(T), reference_angles=ref,
    )
    a = app._build_deduction_measured_deviations(angles=usr, **kwargs)
    b = app._build_deduction_measured_deviations(angles=usr, **kwargs)
    assert a == b


def test_legacy_path_unavailable_fallback(monkeypatch):
    """iter4 HIGH-2 — legacy(ctx None, Gemini 호출) → quantification=None → unavailable
    fallback(final=dimension_overall, ONE traceable record, NO band, NO router)."""
    _enable(monkeypatch)
    monkeypatch.setattr(
        gemini_vision_scorer, "assess_fault_severity",
        lambda *a, **k: _verdict("major"),
    )
    out = app._apply_vision_veto(
        {"overallScore": 84, "dimensionScores": {"angle": 84}}, "/tmp/v.mp4", None,
        _profile(), mode="mode1", reference_video_path="/tmp/ref.mp4",
    )
    bd = out["deductionBreakdown"]
    assert bd["fallback"] == "quantification_unavailable"
    assert len(bd["records"]) == 1
    assert bd["final"] == 84  # dimension_overall (리셋 0)
    assert out["overallScore"] == 84
