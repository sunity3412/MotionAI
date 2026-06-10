"""Phase 9 Wave 1 T1 — force_pattern_copy.py AST 금지 표현 grep gate.

D-09-D3 / RESEARCH Pitfall 7 — 8 substring + 2 regex forbidden 검출 0 회.

AST 룰: `_FORCE_PATTERN_COPY_DATA` + `_MODE_PREFIX` + `_FALLBACK_BODY` 의 string
constant 만 iterate. FORBIDDEN tuple / 모듈 docstring / lookup helper docstring
은 검사 scope 밖 (Phase 7 패턴 정합).

`_FORCE_PATTERN_COPY` 자체는 `MappingProxyType(_FORCE_PATTERN_COPY_DATA)` 호출
결과라 AST literal 0 개 — extractor target 은 `_DATA` 변수 (R3 정합).

박제 메모리 정합:
  - [[no-baekje-filler]]: '박제' 단어는 본 게이트 직접 차단하진 않지만, belle
    검수 단계에서 확인.
  - [[mode3-progress-not-similarity]]: `\\d+%\\s*감점` regex 가 수치 단독
    감점 노출 차단.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from sunity_shared.analysis.force_pattern_copy import (
    FORBIDDEN_PHRASES_PHASE9_REGEX,
    FORBIDDEN_PHRASES_RESEARCH,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = (
    _REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "force_pattern_copy.py"
)

_TARGET_NAMES = frozenset(
    {"_FORCE_PATTERN_COPY_DATA", "_MODE_PREFIX", "_FALLBACK_BODY"}
)


def _extract_force_pattern_copy_strings() -> tuple[
    list[tuple[str, int]], dict[str, int]
]:
    """AST 추출 — Assign + AnnAssign 둘 다 검사 (현 모듈은 type annotation 사용 —
    AnnAssign).

    Returns:
      (strings_with_lineno, per_target_count) — strings_with_lineno 는 (text,
      lineno) tuple list, per_target_count 는 target_id → string count.
    """
    src = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    strings: list[tuple[str, int]] = []
    per_target: dict[str, int] = {name: 0 for name in _TARGET_NAMES}
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
        if target_id in _TARGET_NAMES:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    strings.append((sub.value, sub.lineno))
                    per_target[target_id] += 1
    return strings, per_target


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES_RESEARCH)
def test_no_forbidden_substring(phrase: str) -> None:
    """8 substring 금지 표현 미발견 — research §10.2 6 + Phase 9 신규 2."""
    strings, _ = _extract_force_pattern_copy_strings()
    violations = [(s, ln) for s, ln in strings if phrase in s]
    assert not violations, (
        f"금지 substring {phrase!r} 발견: {violations}"
    )


@pytest.mark.parametrize("pattern", FORBIDDEN_PHRASES_PHASE9_REGEX)
def test_no_forbidden_regex(pattern: str) -> None:
    """2 regex 금지 표현 미발견.

    Positive-control 예시 (절대 commit X):
      '근육 힘 방향이 확정됩니다' → `근육 힘 방향.*확정` regex match (조사 변형 catch).
      '30% 감점입니다' → `\\d+%\\s*감점` regex match (수치 감점 catch).
    """
    strings, _ = _extract_force_pattern_copy_strings()
    compiled = re.compile(pattern)
    violations = [(s, ln) for s, ln in strings if compiled.search(s)]
    assert not violations, (
        f"금지 regex {pattern!r} 발견: {violations}"
    )


def test_ast_gate_extracts_strings() -> None:
    """sanity — AST 추출이 충분한 string 발견 + per-target floor.

    R3 정합 — `_FORCE_PATTERN_COPY_DATA >= 18` 명시 assert (extractor target 이
    `_DATA` 변수로 박제됨을 회귀 차단; MappingProxyType wrap 이 원인이었음).
    """
    strings, per_target = _extract_force_pattern_copy_strings()
    # 18 canned + 3 mode prefix + 1 fallback = 최소 22 string (tuple key
    # constant 는 string 아니므로 제외).
    assert len(strings) >= 22, (
        f"AST 추출이 22 string 미만 — got {len(strings)}, per_target={per_target}"
    )
    assert per_target["_FORCE_PATTERN_COPY_DATA"] >= 18, (
        f"_FORCE_PATTERN_COPY_DATA 가 18 string 미만 — "
        f"got {per_target['_FORCE_PATTERN_COPY_DATA']}"
    )
    assert per_target["_MODE_PREFIX"] >= 3, (
        f"_MODE_PREFIX 가 3 string 미만 — got {per_target['_MODE_PREFIX']}"
    )
    assert per_target["_FALLBACK_BODY"] >= 1, (
        f"_FALLBACK_BODY 가 1 string 미만 — got {per_target['_FALLBACK_BODY']}"
    )
