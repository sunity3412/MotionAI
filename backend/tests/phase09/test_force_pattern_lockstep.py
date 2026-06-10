"""Plan 09-01 Wave 0 — 3-way schema lockstep (D-09-U1 / D-09-D1).

TS Literal union (analysis.ts) ↔ Python frozenset (force_pattern.py) ↔
docs/contract.md §9.11 필드 표 3 축 lockstep grep 검증.

per Plan 09-01 must_haves + RESEARCH §"Pattern 1" + §"Phase Requirements".
"""

from __future__ import annotations

import re
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TS_PATH = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_CONTRACT_PATH = _REPO_ROOT / "docs" / "contract.md"


# ── (a) Python _FORCE_PATTERNS frozenset ─────────────────────────────────


def test_force_patterns_frozenset_in_python() -> None:
    """D-09-D1 — Python frozenset 박제 6 값 정합."""
    from sunity_shared.analysis.force_pattern import _FORCE_PATTERNS

    expected = {"pull", "push", "brace", "rotate", "release", "unknown"}
    assert _FORCE_PATTERNS == expected, (
        f"_FORCE_PATTERNS 정합 위반:\n  expected: {expected}\n  actual: {_FORCE_PATTERNS}"
    )


def test_force_source_signals_frozenset_in_python() -> None:
    """D-09-D1 — Python frozenset 박제 6 신호 정합."""
    from sunity_shared.analysis.force_pattern import _FORCE_SOURCE_SIGNALS

    expected = {
        "axis_tilt",
        "pelvis_drop",
        "late_contact",
        "high_jitter",
        "high_jerk",
        "abnormal_release",
    }
    assert _FORCE_SOURCE_SIGNALS == expected, (
        f"_FORCE_SOURCE_SIGNALS 정합 위반:\n"
        f"  expected: {expected}\n  actual: {_FORCE_SOURCE_SIGNALS}"
    )


def test_mode_contexts_frozenset_in_python() -> None:
    """D-09-D1 — Python frozenset 박제 3 mode context 정합."""
    from sunity_shared.analysis.force_pattern import _MODE_CONTEXTS

    expected = {"mode1", "mode3_first", "mode3_progress"}
    assert _MODE_CONTEXTS == expected, (
        f"_MODE_CONTEXTS 정합 위반:\n"
        f"  expected: {expected}\n  actual: {_MODE_CONTEXTS}"
    )


# ── (b) TS Literal union — analysis.ts ────────────────────────────────────


def test_force_pattern_literals_in_ts() -> None:
    """D-09-U1 — analysis.ts 안에 6 ForceDirectionPattern + 6 ForceSourceSignal +
    3 ModeContext Literal token 모두 박제 (verbatim 정합).
    """
    text = _TS_PATH.read_text(encoding="utf-8")

    pattern_tokens = ["pull", "push", "brace", "rotate", "release", "unknown"]
    signal_tokens = [
        "axis_tilt",
        "pelvis_drop",
        "late_contact",
        "high_jitter",
        "high_jerk",
        "abnormal_release",
    ]
    mode_tokens = ["mode1", "mode3_first", "mode3_progress"]

    for tok in pattern_tokens + signal_tokens + mode_tokens:
        # Quoted literal — TS Literal union 박제.
        m = re.search(rf"['\"]{re.escape(tok)}['\"]", text)
        assert m is not None, (
            f"TS analysis.ts 안에 Literal token {tok!r} 박제 부재 (D-09-D1 lockstep 위반)"
        )


def test_force_pattern_interfaces_in_ts() -> None:
    """D-09-D1 — analysis.ts 안에 ForcePatternFinding / ForcePatternInference interface
    헤더 박제."""
    text = _TS_PATH.read_text(encoding="utf-8")
    assert "ForcePatternFinding" in text, "TS interface ForcePatternFinding 부재"
    assert "ForcePatternInference" in text, "TS interface ForcePatternInference 부재"
    assert "forcePatternInference" in text, (
        "AnalysisResult.forcePatternInference 필드 부재 (D-09-U1)"
    )


# ── (c) docs/contract.md §9.11 ────────────────────────────────────────────


def test_contract_section_9_11_present() -> None:
    """D-09-U1 — docs/contract.md §9.11 ForcePatternInference 섹션 박제."""
    text = _CONTRACT_PATH.read_text(encoding="utf-8")
    assert "§9.11" in text, "docs/contract.md 안 §9.11 헤딩 부재"
    assert "ForcePatternInference" in text, (
        "docs/contract.md 안 ForcePatternInference 표 부재"
    )


def test_contract_section_9_11_has_finding_fields() -> None:
    """D-09-D1 — §9.11 표가 8 ForcePatternFinding 필드 + 5 ForcePatternInference 필드
    박제 (camelCase 행으로)."""
    text = _CONTRACT_PATH.read_text(encoding="utf-8")

    # 8 ForcePatternFinding 필드.
    finding_fields = [
        "pattern",
        "phase",
        "sourceSignal",
        "reason",
        "interpretation",
        "confidence",
        "jointHint",
        "warnings",
    ]
    for f in finding_fields:
        assert f in text, f"docs §9.11 안 ForcePatternFinding 필드 {f!r} 박제 부재"

    # 5 ForcePatternInference 필드.
    inference_fields = [
        "version",
        "findings",
        "overallConfidence",
        "modeContext",
        "warnings",
    ]
    for f in inference_fields:
        assert f in text, f"docs §9.11 안 ForcePatternInference 필드 {f!r} 박제 부재"


def test_contract_section_9_11_has_warning_codes() -> None:
    """§9.11.6 — 3 warning code 박제."""
    text = _CONTRACT_PATH.read_text(encoding="utf-8")
    for code in (
        "phase_unavailable_for_inference",
        "axis_signal_unavailable",
        "no_significant_force_pattern_signal",
    ):
        assert code in text, f"docs §9.11 안 warning code {code!r} 박제 부재"


# ── alias group for T3 quick gate (`-k "ts or analysis_ts"`) ─────────────


def test_force_pattern_literals_in_analysis_ts() -> None:
    """T3 quick gate (-k 'ts or analysis_ts') 박제 alias — analysis.ts Literal
    token 박제 (test_force_pattern_literals_in_ts 와 동일 검증).
    """
    test_force_pattern_literals_in_ts()
