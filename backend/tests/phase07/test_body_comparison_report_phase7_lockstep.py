"""Plan 07-01 Task 3: 3-way contract lockstep — TS + Python + docs/contract.md
§8 + §8.3 drift defense.

CLAUDE.md Cross-cutting 룰: BodyComparisonFinding / BodyComparisonReport 변경 시
세 곳 동시 갱신 — 본 테스트가 drift 를 방어.

Phase 6 박제 패턴 (test_body_comparison_report_lockstep.py) 미러.

iteration 2 (2026-06-08) cross-AI review fix 박제:
  - CR-01: render_finding_copy(used_reference_fallback) — interpretation nullable.
  - CR-02: 33 canned (12 global 추가) — docs §8.3 표 박제.
  - WR-01: 6 BodyComparisonFinding emit 위치 category="uncertain" placeholder.
  - WR-03: recommended_focus_fallback 신규 필드.
  - WR-04: resolver coverage test (별 파일).

per Plan 07-01 Task 3 + 07-PATTERNS.md §"test_body_comparison_report_phase7_lockstep.py".
"""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TS_PATH = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_PY_BODY_NORMALIZER_PATH = (
    _REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "body_normalizer.py"
)
_CONTRACT_PATH = _REPO_ROOT / "docs" / "contract.md"


# ── Phase 7 신설 필드 매핑 — TS camelCase ↔ Python snake_case ──────────

# BodyComparisonFinding 4 신설 필드 (D-07-A1 + D-07-C1).
_FINDING_FIELD_MAP: dict[str, str] = {
    "category": "category",
    "phase": "phase",
    "bodyTypeInterpretation": "body_type_interpretation",
    "recommendation": "recommendation",
}

# BodyComparisonReport 2+1 신설 필드 (D-07-B3 + WR-03 fix).
_REPORT_FIELD_MAP: dict[str, str] = {
    "doNotOverCorrect": "do_not_over_correct",
    "recommendedFocus": "recommended_focus",
    "recommendedFocusFallback": "recommended_focus_fallback",  # WR-03 fix
}

# 합쳐 7 신설 필드.
_FIELD_MAP: dict[str, str] = {**_FINDING_FIELD_MAP, **_REPORT_FIELD_MAP}


# ── Test 1: TS interface 에 7 신설 필드 모두 존재 ──────────────────────


def test_ts_phase7_fields_present() -> None:
    src = _TS_PATH.read_text(encoding="utf-8")
    for camel in _FIELD_MAP:
        assert camel in src, f"TS analysis.ts 에 Phase 7 신설 필드 {camel!r} 누락"


# ── Test 2: Python dataclass 에 7 신설 필드 모두 존재 ─────────────────


def test_python_phase7_fields_present() -> None:
    src = _PY_BODY_NORMALIZER_PATH.read_text(encoding="utf-8")
    for snake in _FIELD_MAP.values():
        assert snake in src, (
            f"Python body_normalizer.py 에 Phase 7 신설 필드 {snake!r} 누락"
        )


# ── Test 3: docs/contract.md §8.3 신규 서브섹션 + 7 필드 박제 ─────────


def test_docs_contract_md_section_8_3() -> None:
    src = _CONTRACT_PATH.read_text(encoding="utf-8")
    # §8.3 서브섹션 존재
    assert "§8.3" in src, "docs/contract.md §8.3 신규 서브섹션 누락"
    # Phase 7 신설 7 필드 (camelCase) 모두 존재
    for camel in _FIELD_MAP:
        assert camel in src, f"docs/contract.md 에 Phase 7 신설 필드 {camel!r} 누락"


# ── Test 4: 양방향 camelCase ↔ snake_case lockstep ───────────────────


def test_camelcase_snake_case_lockstep() -> None:
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    py_src = _PY_BODY_NORMALIZER_PATH.read_text(encoding="utf-8")
    for camel, snake in _FIELD_MAP.items():
        assert camel in ts_src, f"TS 에 {camel!r} 누락"
        assert snake in py_src, f"Python 에 {snake!r} 누락"


# ── Test 5: category Literal enum 박제 (D-07-A1) ─────────────────────


def test_category_literal_enum_in_python_and_ts() -> None:
    py_src = _PY_BODY_NORMALIZER_PATH.read_text(encoding="utf-8")
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    # Python: Literal[...] 3 enum 박제
    for enum_val in ("body_type_allowed", "needs_adjustment", "uncertain"):
        assert enum_val in py_src, (
            f"Python body_normalizer.py 에 category enum {enum_val!r} 누락"
        )
        assert enum_val in ts_src, (
            f"TS analysis.ts 에 category enum {enum_val!r} 누락"
        )


# ── Test 6: module constants CATEGORY_GATE + CATEGORY_CONF_GATE 박제 ──


def test_module_constants_present() -> None:
    py_src = _PY_BODY_NORMALIZER_PATH.read_text(encoding="utf-8")
    assert "CATEGORY_GATE = 0.2" in py_src or "CATEGORY_GATE: float = 0.2" in py_src, (
        "CATEGORY_GATE 상수 박제 누락 (D-07-A1)"
    )
    assert (
        "CATEGORY_CONF_GATE = 0.5" in py_src
        or "CATEGORY_CONF_GATE: float = 0.5" in py_src
    ), "CATEGORY_CONF_GATE 상수 박제 누락 (D-07-A2)"


# ── Test 7: WR-01 fail-safe placeholder 6 위치 검증 ──────────────────


def test_wr01_placeholder_six_emit_positions() -> None:
    """WR-01 fix — measure_ipsf_absolute_deficits 의 6 BodyComparisonFinding 호출
    위치에 category="uncertain" placeholder 박제. Plan 02 classify_findings 재할당."""
    py_src = _PY_BODY_NORMALIZER_PATH.read_text(encoding="utf-8")
    # 주석 라인 제외하고 category="uncertain" 출현 횟수 >= 6
    non_comment_lines = [
        line for line in py_src.splitlines() if not line.lstrip().startswith("#")
    ]
    non_comment_src = "\n".join(non_comment_lines)
    count = non_comment_src.count('category="uncertain"')
    # 7 = 6 emit placeholders + 1 dataclass default (= "uncertain")
    # 6 이상이면 placeholder 박제 완료.
    assert count >= 6, (
        f"WR-01 fix — category=\"uncertain\" placeholder 6 위치 필요. got {count}"
    )
    # WR-01 verify: body_type_allowed placeholder 우회 검증.
    leaked = non_comment_src.count('category="body_type_allowed"')
    assert leaked == 0, (
        f"WR-01 verify — category=\"body_type_allowed\" placeholder 우연한 fail-open "
        f"semantics 발견 ({leaked}). placeholder 는 uncertain 으로 통일."
    )
