"""Plan 07-01 Task 2 — AST 기반 9 금지 표현 grep gate.

D-07-D2 박제 — research §10.3 금지 6종 + Sunity 추가 3종 (memory 박제 정합).

AST 룰: `_COPY_TEMPLATES` + `_MODE_PREFIX` 의 string constant 만 iterate.
FORBIDDEN tuple / `_EMPTY_FOCUS_FALLBACK` 상수 / 모듈 docstring / fallback 문장
자체는 검사 scope 밖.

NOTE — copy_templates.py 의 두 dict 는 type annotation 을 가지므로 ast.AnnAssign
노드로 파싱됨. 본 게이트는 ast.Assign 과 ast.AnnAssign 둘 다 검사 (Rule 1 fix —
plan 의 ast.Assign 단독 snippet 은 0 strings 반환 → 게이트 무의미).

per Plan 07-01 Task 2 + .planning/phases/07-difference-classification/07-PATTERNS.md
§"test_copy_templates_no_forbidden.py".

박제 메모리 정합:
  - [[no-baekje-filler]]: "박제" 단어 검출.
  - [[mode3-progress-not-similarity]]: "%일치"/"유사도" 검출.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from sunity_shared.analysis.copy_templates import (
    FORBIDDEN_PHRASES,
    FORBIDDEN_PHRASES_SUNITY,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = (
    _REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "copy_templates.py"
)


def _extract_template_strings() -> list[tuple[str, int]]:
    """copy_templates.py 안 `_COPY_TEMPLATES` + `_MODE_PREFIX` dict literal 의
    string constant 추출. (string, lineno) tuple list 반환.

    Assign + AnnAssign 둘 다 검사 (현 모듈은 type annotation 박제 — AnnAssign).
    """
    src = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    strings: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        target_id: str | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                target_id = target.id
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name):
                target_id = target.id
        if target_id in ("_COPY_TEMPLATES", "_MODE_PREFIX"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    strings.append((sub.value, sub.lineno))
    return strings


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES + FORBIDDEN_PHRASES_SUNITY)
def test_no_forbidden_phrase_in_copy_templates(phrase: str) -> None:
    """9 금지 표현 (6 research §10.3 + 3 Sunity 박제) 모두 _COPY_TEMPLATES +
    _MODE_PREFIX 안 string constant 에서 0회 출현."""
    strings = _extract_template_strings()
    violations = [(s, ln) for s, ln in strings if phrase in s]
    assert not violations, (
        f"금지 표현 {phrase!r} 발견: {violations}"
    )


def test_ast_gate_extracts_strings() -> None:
    """sanity: AST 추출이 string constant 를 실제로 발견하는지 (회귀 차단 —
    Assign vs AnnAssign 함정 #Rule 1 fix). 33 카피 × 2 (interp + recom) + 3
    mode prefix = 최소 69 string constant 예상 — 단, dict key tuple 안 string
    도 포함되므로 더 많을 수 있음."""
    strings = _extract_template_strings()
    assert len(strings) >= 66, (
        f"AST 추출이 0 string 반환 — Assign 노드 누락 의심. got len={len(strings)}"
    )
