"""Phase 7 fixture factory helper.

본 fixture 는 합성 — Phase 6 의 BodyComparisonFinding emit 후 분류 단계 입력
시뮬레이션. 6 fixture 의 임계값 박제 근거:
  - Plan 07-01 RESEARCH.md §"Test Fixtures" + §"Test Specifications"
  - D-07-A1: body_type_adjusted + abs(deduction) 룰
  - D-07-A2: confidence < 0.5 OR body_normalization_confidence < 0.5 → uncertain
  - D-07-Discretion + CR-01 fix: mode3_first + used_reference_fallback → unprefixed 단일 카피

per Plan 07-01 Task 1 <behavior>.

CR-01 fix path 정합: fixture #6 의 expected.recommendation 은 unprefixed 단일 문장
exact 박제. Plan 02 Task 1 의 test_uncertain_when_mode3_first_fallback 가 본 문자열
exact match 로 검증.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_FIXTURE_DIR: Path = Path(__file__).resolve().parent


def load_fixture_raw(name: str) -> dict[str, Any]:
    """fixture JSON 을 dict 로 raw 로딩.

    Args:
        name: fixture 파일명 ("fixture_xxx.json" 확장자 없이 또는 포함 둘 다 허용).

    Returns:
        JSON 으로 파싱된 dict — {"finding": {...}, "context": {...}, "expected": {...}}.
    """
    if not name.endswith(".json"):
        name = f"{name}.json"
    path = _FIXTURE_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def load_finding_from_fixture(name: str) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """fixture JSON 의 "finding" 필드를 BodyComparisonFinding 으로 변환.

    Plan 07-01 Task 3 가 BodyComparisonFinding 에 4 필드 (category / phase /
    body_type_interpretation / recommendation) 추가. category 는 required, 나머지 3
    필드 default 존재. fixture JSON 의 finding dict 에 category 가 없으면
    placeholder "uncertain" 적용 (Plan 02 가 재할당).

    Args:
        name: fixture 파일명.

    Returns:
        (finding, context, expected) tuple — finding 은 BodyComparisonFinding 인스턴스,
        나머지는 원본 dict.
    """
    # Lazy import — Plan 07-01 Task 3 의 schema 확장 후 정상 동작.
    from sunity_shared.analysis.body_normalizer import BodyComparisonFinding

    raw = load_fixture_raw(name)
    finding_dict = dict(raw["finding"])
    # category 필드 미지정 시 fail-safe placeholder (WR-01 fix 정합).
    finding_dict.setdefault("category", "uncertain")
    finding = BodyComparisonFinding(**finding_dict)
    context = dict(raw.get("context", {}))
    expected = dict(raw.get("expected", {}))
    return finding, context, expected


__all__ = (
    "load_fixture_raw",
    "load_finding_from_fixture",
)
