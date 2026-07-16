"""Phase 29 (29-02) — Mode3 점수 내역 seam 테스트 (D-01/D-02/D-03 매트릭스).

박제 정신 (29-CONTEXT D-01~D-03, 24-04 Option A 이식):
  · D-01: mode3 등록 동작에서 md(ipsf_absolute measured seed)가 비어있지 않으면
    deduction_engine.tally 가 실행되고 deductionBreakdown 이 방출된다 — Gemini 추가 호출 0,
    visionVeto.status 는 'mode3_held' 유지(비전 미실행 진실 신호, 'applied' 재사용 금지 —
    result.tsx vetoApplied 파생 의미 오염 방지, RESEARCH Pattern 1 옵션 a).
  · D-02: 방출 doc 의 overallScore == deductionBreakdown.final — 100−Σ감점 항등식
    (엔진 to_dict 산술 그대로, 재계산 조작 금지). 성장 델타 소스는 저장 overallScore 단일 —
    pre-tally 점수를 나르는 별도 점수 필드 방출 0 (sub-clause). legacy prev doc(구점수) vs
    신규 doc(tally) 혼재 델타는 코드 방어 대상 아님 — D-04 재분석 배너가 완충.
  · D-03: md 빈 dict(미등록 동작 + 빈 criteria 4동작)는 breakdown 미방출 + overallScore
    byte-불변 — 기준 없는 감점 0=100 위양성 차단.
  · mode1 TALLY-ELIGIBLE 3-status(candidate_verdict/no_fault/low_alignment_confidence)
    로직 불변 — 형제 비측정 status 는 여전히 score-free passthrough.

전부 mock-based — 실 Gemini / 실 Pod / 실 S3 / 실 Firestore 호출 0. PYTHONPATH=shared/python.
# 수치 타깃 아님 — 방향/구조 단언만 (curve-fit 금지). 100/0 은 항등식 상수로만 사용.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# pipeline/app.py + shared layer path 주입 (test_pipeline_deduction_seam.py 관례 승계).
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared.analysis import gemini_vision_scorer, vision_veto  # noqa: E402


# ── helpers (test_pipeline_deduction_seam.py 패턴 승계) ───────────────────────


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


def _score(overall=88):
    """mode3 doc 형상 — 절대 차원(line/stability)만 (mode3-overall-exclude-angle invariant)."""
    return {"overallScore": overall, "dimensionScores": {"line": overall, "stability": 90}}


def _enable(monkeypatch):
    monkeypatch.setattr(app, "_gemini_vision_veto_enabled", lambda: True)


def _run_mode3(md, *, overall=88):
    """mode3_held ctx + md 로 from_context seam 직접 호출 (quantification 없음 — mode3 실형상)."""
    return app._apply_vision_veto_from_context(
        _score(overall), _ctx("mode3_held"), None,
        measured_deviations=md, baseline_kind="hip_line",
    )


# ── D-01 — md 보유 시 tally 방출, mode3_held 불변 ─────────────────────────────


def test_d01_mode3_md_present_emits_measured_breakdown(monkeypatch):
    """D-01: mode3_held + measured seed(leg 편차 > tol) → deductionBreakdown 방출.
    records 는 measured seed 파생(deviationSource=ipsf_absolute), status 는 'mode3_held'
    유지 — 'applied' 아님 (RESEARCH Pattern 1 옵션 a)."""
    _enable(monkeypatch)
    out = _run_mode3({"leg_extension": 45.0})
    bd = out["deductionBreakdown"]
    crits = {r["criterion"] for r in bd["records"]}
    assert "leg_extension" in crits
    # measured seed 파생만 — Gemini-located criterion 0 (supported_differences 부재).
    sources = {r["deviationSource"] for r in bd["records"]}
    assert sources == {"ipsf_absolute"}
    assert out["visionVeto"]["status"] == "mode3_held"
    assert out["visionVeto"]["status"] != "applied"


# ── D-02 — overallScore == breakdown.final 항등 ──────────────────────────────


def test_d02_overall_equals_tally_final_identity(monkeypatch):
    """D-02: 방출 doc 의 overallScore == breakdown.final AND final == 엔진 산술
    max(0, round(100 + Σ points)) — 재계산 조작 금지 (points 는 signed-negative)."""
    _enable(monkeypatch)
    out = _run_mode3({"leg_extension": 45.0})
    bd = out["deductionBreakdown"]
    assert out["overallScore"] == bd["final"]
    pts = sum(r["points"] for r in bd["records"])
    assert bd["final"] == max(0, round(100 + pts))
    assert out["overallScore"] < 100  # 편차 > tol → 실제 감점 발생 (방향 단언)


# ── D-03 — md 빈 dict → 미방출 + byte-불변 ───────────────────────────────────


def test_d03_empty_md_passthrough_score_byte_invariant(monkeypatch):
    """D-03: mode3_held + md == {} (미등록 동작 + 빈 criteria 4동작 자연 방어) →
    breakdown 미방출 + overallScore/dimensionScores byte-불변 + status mode3_held.
    기준 없는 감점 0=100 위양성 차단 — criteria 복원/신설 금지 (RESEARCH Pitfall 1)."""
    _enable(monkeypatch)
    score_in = _score(88)
    out = app._apply_vision_veto_from_context(
        score_in, _ctx("mode3_held"), None,
        measured_deviations={}, baseline_kind="hip_line",
    )
    assert "deductionBreakdown" not in out
    assert out["overallScore"] == 88
    assert out == {**score_in, "visionVeto": {"status": "mode3_held"}}


# ── clean tally — 편차 tolerance 이내 → records 0, final 100 ─────────────────


def test_clean_md_within_tolerance_emits_final_100(monkeypatch):
    """mode3_held + md 보유 + 전 편차 tolerance 이내 → breakdown 방출 + records 0 +
    final == 100 (감점 0 = 100, 260630-l4e mode1 clean 선례와 동일 원리 —
    투명 tally 가 authoritative, 레거시 dimension passthrough 아님)."""
    _enable(monkeypatch)
    out = _run_mode3({"leg_extension": 5.0}, overall=88)  # 5° < tol(20°)
    bd = out["deductionBreakdown"]
    assert bd["records"] == []
    assert bd["final"] == 100
    assert out["overallScore"] == 100
    assert out["visionVeto"]["status"] == "mode3_held"


# ── Gemini 무호출 — mode3 경로 vision 판정 함수 sentinel ─────────────────────


def test_mode3_path_never_calls_vision_assessment(monkeypatch):
    """mode3 seam 은 Gemini 추가 호출 0 — assess 계열이 호출되면 raise 하는 sentinel
    설치 후 정상 통과 확인 (비용/시간 증가 0, D-01)."""
    _enable(monkeypatch)

    def _boom(*_a, **_k):  # pragma: no cover - 호출되면 즉시 실패
        raise AssertionError("mode3 경로에서 vision 판정 함수 호출 금지 (D-01)")

    monkeypatch.setattr(gemini_vision_scorer, "assess_fault_severity", _boom)
    monkeypatch.setattr(app, "_collect_vision_fault_context", _boom)
    out = _run_mode3({"leg_extension": 45.0})
    assert out["visionVeto"]["status"] == "mode3_held"


# ── mode1 무회귀 — 형제 비측정 status 는 여전히 passthrough ──────────────────


def test_sibling_non_measured_statuses_still_passthrough(monkeypatch):
    """passthrough_map 의 나머지 status 는 md 가 있어도 여전히 미방출 + 점수 불변 —
    mode3_held 만 tally-eligible 로 이동 (mode1 TALLY-ELIGIBLE 3-status 불변)."""
    _enable(monkeypatch)
    for status in (
        "resource_limited", "disabled", "missing_reference",
        "missing_current_video", "skipped_error",
    ):
        out = app._apply_vision_veto_from_context(
            _score(91), _ctx(status), None,
            measured_deviations={"leg_extension": 50.0}, baseline_kind="hip_line",
        )
        assert out["overallScore"] == 91, f"{status} score 불변"
        assert "deductionBreakdown" not in out, f"{status} tally 미실행"


# ── D-02 sub-clause — 성장 델타 소스 = 저장 overallScore 단일 ─────────────────


def test_d02_delta_source_single_overall_score_in_place(monkeypatch):
    """D-02 sub-clause (성장 델타도 tally 점수 기준으로 일관): 방출 dict 의 점수 필드는
    overallScore in-place 교체 단일 — pre-tally 점수(dimension overall 원본 등)를 나르는
    신규 점수 키 방출 0. 성장 델타는 앱(GrowthChart.tsx / 결과화면)이 doc.overallScore 로
    산출하므로 이 단언이 델타의 tally 일관을 고정한다. legacy prev doc(구점수) vs 신규
    doc(tally) 혼재 델타는 코드 방어 대상 아님 — D-04 재분석 배너가 완충."""
    _enable(monkeypatch)
    score_in = _score(88)
    out = app._apply_vision_veto_from_context(
        score_in, _ctx("mode3_held"), None,
        measured_deviations={"leg_extension": 45.0}, baseline_kind="hip_line",
    )
    # 신규 키는 deductionBreakdown + visionVeto 뿐 — 별도 점수 필드 0.
    assert set(out.keys()) == set(score_in.keys()) | {"deductionBreakdown", "visionVeto"}
    # overallScore 는 in-place 교체(tally final) — 입력 원점수는 어디에도 실려가지 않는다.
    assert out["overallScore"] == out["deductionBreakdown"]["final"]
    assert out["overallScore"] != 88
    assert 88 not in (
        out["visionVeto"].get("tallyFinal"),
        out.get("preTallyScore"),
    )
    # dimensionScores 는 차원 표시용 그대로 (점수 필드 신설 아님 — 기존 계약 필드).
    assert out["dimensionScores"] == score_in["dimensionScores"]
