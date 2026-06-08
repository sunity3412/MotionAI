"""Plan 07-02 Task 1 — classify_findings() 10 단위 test.

박제 정신 (Plan 07-02 must_haves §5 + RESEARCH.md §"Validation Architecture Test Specifications"):
  - D-07-A1: body_type_adjusted + |deduction_score| 게이트 (CATEGORY_GATE = 0.2)
  - D-07-A2: uncertain demotion 게이트 (CATEGORY_CONF_GATE = 0.5)
  - D-07-B3: 카피 분배 룰 — body_type_allowed → do_not_over_correct,
             needs_adjustment + uncertain → recommended_focus (Decision 1)
  - D-07-C1: phase = "hold" v1 단일
  - CR-01 fix: mode3_first + used_reference_fallback=True → render_finding_copy
             (used_reference_fallback=True) thread → unprefixed 단일 카피 +
             body_type_interpretation=None
  - WR-03 fix: 빈 recommended_focus[] → _EMPTY_FOCUS_FALLBACK fallback 카피

test 매핑 (10 test):
  1. test_allowed_when_adjusted_and_small_deduction (fixture #1)
  2. test_needs_adjustment_when_large_deduction (fixture #2)
  3. test_uncertain_when_raw_coords (fixture #3 — body_type_adjusted=False)
  4. test_uncertain_when_finding_low_confidence (fixture #4)
  5. test_uncertain_when_report_low_confidence (fixture #5)
  6. test_uncertain_when_mode3_first_fallback (fixture #6 — CR-01 exact match)
  7. test_phase_default_hold (4 finding aggregate)
  8. test_aggregate_lists_populated (allowed + needs + uncertain → 1 dnoc + 2 rec)
  9. test_classify_findings_uses_replace_pattern_zero (AST grep — secondary convention)
  10. test_recommended_focus_fallback_populated_when_empty (WR-03 fix)

박제 메모 정합:
  - [[analysis-objectivity-no-human-scores]]: 분류 룰이 belle/강사 점수 라벨 무관.
  - [[mode3-progress-not-similarity]]: mode3_progress prefix carry-over (test 7 안).
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from sunity_shared.analysis.body_normalizer import (
    BodyComparisonFinding,
    classify_findings,
)
from sunity_shared.analysis.copy_templates import _EMPTY_FOCUS_FALLBACK

from tests.phase07.fixtures._factory import load_finding_from_fixture


# ── Test 1: body_type_allowed 분류 (fixture #1) ──────────────────────────


def test_allowed_when_adjusted_and_small_deduction() -> None:
    """fixture_classification_allowed.json — body_type_adjusted=True +
    |deduction|=0.2 + confidence=0.85 + comparison_type=mode1 →
    category='body_type_allowed'.

    do_not_over_correct == 1, recommended_focus == 0 → WR-03 fix:
    recommended_focus_fallback == _EMPTY_FOCUS_FALLBACK (빈 list 케이스).
    """
    finding, ctx, expected = load_finding_from_fixture("fixture_classification_allowed")
    classified, dnoc, rec, fallback = classify_findings(
        [finding],
        body_normalization_confidence=ctx["body_normalization_confidence"],
        comparison_type=ctx["comparison_type"],
        used_reference_fallback=ctx["used_reference_fallback"],
    )
    assert len(classified) == 1
    assert classified[0].category == expected["category"] == "body_type_allowed"
    assert len(dnoc) == expected["do_not_over_correct_count"] == 1
    assert len(rec) == expected["recommended_focus_count"] == 0
    # WR-03 — 빈 recommended_focus[] → fallback 카피 populated
    assert fallback == _EMPTY_FOCUS_FALLBACK


# ── Test 2: needs_adjustment 분류 (fixture #2) ───────────────────────────


def test_needs_adjustment_when_large_deduction() -> None:
    """fixture_classification_needs.json — pose_reliability_low (deduction=-0.5,
    |deduction|=0.5 > CATEGORY_GATE=0.2) + body_type_adjusted=True →
    category='needs_adjustment'.
    """
    finding, ctx, expected = load_finding_from_fixture("fixture_classification_needs")
    classified, dnoc, rec, fallback = classify_findings(
        [finding],
        body_normalization_confidence=ctx["body_normalization_confidence"],
        comparison_type=ctx["comparison_type"],
        used_reference_fallback=ctx["used_reference_fallback"],
    )
    assert classified[0].category == expected["category"] == "needs_adjustment"
    assert len(rec) == 1
    assert len(dnoc) == 0
    assert fallback is None  # WR-03 — recommended_focus 채워짐 → fallback None


# ── Test 3: uncertain (raw 좌표 path — body_type_adjusted=False) ─────────


def test_uncertain_when_raw_coords() -> None:
    """fixture_classification_uncertain_raw.json — body_type_adjusted=False →
    category='uncertain'. recommendation 안에 '강사' 또는 '확인' 포함.
    """
    finding, ctx, expected = load_finding_from_fixture(
        "fixture_classification_uncertain_raw"
    )
    classified, dnoc, rec, fallback = classify_findings(
        [finding],
        body_normalization_confidence=ctx["body_normalization_confidence"],
        comparison_type=ctx["comparison_type"],
        used_reference_fallback=ctx["used_reference_fallback"],
    )
    assert classified[0].category == expected["category"] == "uncertain"
    assert classified[0].recommendation is not None
    assert ("강사" in classified[0].recommendation) or (
        "확인" in classified[0].recommendation
    )
    assert len(rec) == 1
    assert len(dnoc) == 0


# ── Test 4: uncertain (finding-level confidence < 0.5) ──────────────────


def test_uncertain_when_finding_low_confidence() -> None:
    """fixture_classification_uncertain_low_conf.json — finding.confidence=0.3 <
    CATEGORY_CONF_GATE=0.5 → category='uncertain'.
    """
    finding, ctx, expected = load_finding_from_fixture(
        "fixture_classification_uncertain_low_conf"
    )
    classified, dnoc, rec, fallback = classify_findings(
        [finding],
        body_normalization_confidence=ctx["body_normalization_confidence"],
        comparison_type=ctx["comparison_type"],
        used_reference_fallback=ctx["used_reference_fallback"],
    )
    assert classified[0].category == expected["category"] == "uncertain"


# ── Test 5: uncertain (report-level body_normalization_confidence < 0.5) ─


def test_uncertain_when_report_low_confidence() -> None:
    """fixture_classification_uncertain_global_low.json — body_normalization_confidence=0.3
    < CATEGORY_CONF_GATE=0.5 → 모든 finding category='uncertain' (D-07-A2 global demotion).
    """
    finding, ctx, expected = load_finding_from_fixture(
        "fixture_classification_uncertain_global_low"
    )
    classified, dnoc, rec, fallback = classify_findings(
        [finding],
        body_normalization_confidence=ctx["body_normalization_confidence"],
        comparison_type=ctx["comparison_type"],
        used_reference_fallback=ctx["used_reference_fallback"],
    )
    assert classified[0].category == expected["category"] == "uncertain"


# ── Test 6: CR-01 fix — mode3_first + used_reference_fallback exact match ─


def test_uncertain_when_mode3_first_fallback() -> None:
    """fixture_classification_mode3_first_fallback.json — mode3_first +
    used_reference_fallback=True → 모든 finding category='uncertain' (Decision 1).

    CR-01 fix: recommendation == "이 동작은 기준 영상이 없어, AI 가 IPSF 절대 기준만으로 분석했어요.
    강사와 함께 확인 권유드려요." (mode prefix 결합 X — unprefixed 단일 카피).
    body_type_interpretation == None.
    """
    finding, ctx, expected = load_finding_from_fixture(
        "fixture_classification_mode3_first_fallback"
    )
    classified, dnoc, rec, fallback = classify_findings(
        [finding],
        body_normalization_confidence=ctx["body_normalization_confidence"],
        comparison_type=ctx["comparison_type"],
        used_reference_fallback=ctx["used_reference_fallback"],
    )
    assert classified[0].category == "uncertain"
    # CR-01 fix — body_type_interpretation = None (fallback path 의 단일 카피만)
    assert classified[0].body_type_interpretation is None
    # CR-01 fix — recommendation exact match (mode prefix 결합 X)
    assert classified[0].recommendation == (
        "이 동작은 기준 영상이 없어, "
        "AI 가 IPSF 절대 기준만으로 분석했어요. "
        "강사와 함께 확인 권유드려요."
    )
    # fixture #6 박제 정합 — expected.recommendation
    assert classified[0].recommendation == expected["recommendation"]


# ── Test 7: phase default 'hold' (D-07-C1) ───────────────────────────────


def test_phase_default_hold() -> None:
    """4 finding 입력 (allowed + needs + uncertain) → 모든 classified finding
    의 phase == 'hold' (v1 단일 — D-07-C1).
    """
    findings = [
        BodyComparisonFinding(
            deficit_code="knee_toe_alignment",
            joint_key="left_knee",
            measured_value=165.0,
            deduction_score=-0.2,
            confidence=0.85,
            body_type_adjusted=True,
        ),
        BodyComparisonFinding(
            deficit_code="pose_reliability_low",
            joint_key=None,
            measured_value=0.7,
            deduction_score=-0.5,
            confidence=0.9,
            body_type_adjusted=True,
        ),
        BodyComparisonFinding(
            deficit_code="extension",
            joint_key=None,
            measured_value=145.0,
            deduction_score=-0.2,
            confidence=0.85,
            body_type_adjusted=False,
        ),
    ]
    classified, _, _, _ = classify_findings(
        findings,
        body_normalization_confidence=0.85,
        comparison_type="mode1",
    )
    for f in classified:
        assert f.phase == "hold"


# ── Test 8: aggregate lists — Decision 1 (uncertain → recommended_focus) ─


def test_aggregate_lists_populated() -> None:
    """3 finding 입력 (allowed + needs + uncertain) → do_not_over_correct 1 +
    recommended_focus 2 (uncertain 통합 per Decision 1).
    """
    allowed = BodyComparisonFinding(
        deficit_code="knee_toe_alignment",
        joint_key="left_knee",
        measured_value=165.0,
        deduction_score=-0.2,
        confidence=0.85,
        body_type_adjusted=True,
    )
    needs = BodyComparisonFinding(
        deficit_code="pose_reliability_low",
        joint_key=None,
        measured_value=0.7,
        deduction_score=-0.5,
        confidence=0.9,
        body_type_adjusted=True,
    )
    uncertain = BodyComparisonFinding(
        deficit_code="extension",
        joint_key=None,
        measured_value=145.0,
        deduction_score=-0.2,
        confidence=0.85,
        body_type_adjusted=False,  # → uncertain
    )
    classified, dnoc, rec, fallback = classify_findings(
        [allowed, needs, uncertain],
        body_normalization_confidence=0.85,
        comparison_type="mode1",
    )
    assert len(classified) == 3
    assert len(dnoc) == 1  # allowed
    assert len(rec) == 2  # needs + uncertain (Decision 1)
    assert fallback is None  # recommended_focus 채워짐


# ── Test 9: AST grep — dataclasses.replace 0회 (secondary convention) ────


def test_classify_findings_uses_replace_pattern_zero() -> None:
    """INF-01 secondary convention check — classify_findings 함수 본체에 'dataclasses.replace'
    substring 0회. (primary safety property 는 test_classify_findings_preserves_measurement_fields.py)

    Path resolution: import 결과 module 의 __file__ 사용 — cwd 무관 안전.

    Rule 1 fix (Plan 02 Task 1, 2026-06-08): docstring 안의 'dataclasses.replace 우회 X'
    주석 문구가 false positive. ast.get_docstring 으로 docstring 제거 + 실 본문 nodes 만
    unparse 해서 검사 (Plan 01 의 AST gate Assign+AnnAssign fix 패턴 정합).
    """
    import sunity_shared.analysis.body_normalizer as body_normalizer_module

    src_path = pathlib.Path(body_normalizer_module.__file__)
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "classify_findings"
    )
    # docstring 제거 (Expr(Constant(str)) 가 첫 노드면 그것). 실제 본문 statement
    # 들만 unparse — docstring 의 false positive 차단.
    body_nodes = fn.body
    if (
        body_nodes
        and isinstance(body_nodes[0], ast.Expr)
        and isinstance(body_nodes[0].value, ast.Constant)
        and isinstance(body_nodes[0].value.value, str)
    ):
        body_nodes = body_nodes[1:]
    body_src = "\n".join(ast.unparse(n) for n in body_nodes)
    assert "dataclasses.replace" not in body_src, body_src


# ── Test 10: WR-03 fix — recommended_focus_fallback ──────────────────────


def test_recommended_focus_fallback_populated_when_empty() -> None:
    """WR-03 fix — recommended_focus[] 빈 list 일 때 _EMPTY_FOCUS_FALLBACK 박제.
    채워졌을 때는 None.
    """
    # all findings → body_type_allowed (deduction=-0.2, body_type_adjusted=True, confidence=0.85)
    allowed = BodyComparisonFinding(
        deficit_code="knee_toe_alignment",
        joint_key="left_knee",
        measured_value=165.0,
        deduction_score=-0.2,
        confidence=0.85,
        body_type_adjusted=True,
    )
    classified, dnoc, rec, fallback = classify_findings(
        [allowed],
        body_normalization_confidence=0.85,
        comparison_type="mode1",
    )
    assert rec == []
    assert fallback == _EMPTY_FOCUS_FALLBACK

    # needs_adjustment finding 추가 → recommended_focus 채워짐 → fallback None
    needs = BodyComparisonFinding(
        deficit_code="pose_reliability_low",
        joint_key=None,
        measured_value=0.7,
        deduction_score=-0.5,
        confidence=0.9,
        body_type_adjusted=True,
    )
    classified2, dnoc2, rec2, fallback2 = classify_findings(
        [allowed, needs],
        body_normalization_confidence=0.85,
        comparison_type="mode1",
    )
    assert rec2 != []
    assert fallback2 is None


# ── Bonus: phase07 conftest 가 sys.path 박제. import gate ────────────────


def test_imports_resolve_correctly() -> None:
    """phase07 conftest 의 import gate 가 정상 동작. classify_findings 가
    sunity_shared 안에서 export 가능."""
    assert callable(classify_findings)
