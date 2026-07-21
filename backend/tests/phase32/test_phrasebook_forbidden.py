"""Plan 32-05 Task 2 — 금지어 grep 게이트 (D-09/D-11).

phrasebook.json + terminology_map.json 의 **렌더 카피** string 전수 순회에서
D-09 위반 패턴(%환산·수치 헤드라인)과 일반론 문구(%일치/유사도/박제)가 0회임을
강제한다. sanity 테스트(추출 0건 = 게이트 무의미)를 동반한다.

스코프 근거 (copy_templates AST 게이트 선례 정합): 게이트는 화면에 렌더되는 카피
(entries 슬롯 + safetyEntries + failClosed + terminology terms)만 검사한다. _meta
provenance 는 검사 밖 — IPSF 근거 수치(20° 허용오차 등)·코드경로·메모리 태그를
정직하게 인용하는 문서이지 사용자 카피가 아니다 (copy_templates 가 docstring/
FORBIDDEN tuple 을 scope 밖으로 두는 것과 동일 원칙).
"""

from __future__ import annotations

import re

import pytest

from sunity_shared.analysis.phrasebook import (
    FORBIDDEN_PHRASES_PHRASEBOOK,
    FORBIDDEN_REGEX_PHRASEBOOK,
    rendered_copy_strings,
)


def _strings() -> list[str]:
    return rendered_copy_strings()


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES_PHRASEBOOK)
def test_no_forbidden_literal(phrase: str) -> None:
    """%일치 / 유사도 / 박제 리터럴 0회 (memory 박제 정합)."""
    viol = [s for s in _strings() if phrase in s]
    assert not viol, f"금지 리터럴 {phrase!r} 발견: {viol}"


@pytest.mark.parametrize("pattern", FORBIDDEN_REGEX_PHRASEBOOK)
def test_no_forbidden_regex(pattern: str) -> None:
    """D-09 위반 정규식(수치 % 환산 / 'N도만큼' 수치-지시 일반론) 0회."""
    rx = re.compile(pattern)
    viol = [s for s in _strings() if rx.search(s)]
    assert not viol, f"금지 패턴 {pattern!r} 발견: {viol}"


def test_no_percent_headline() -> None:
    """D-09 — 렌더 카피에 % 문자 자체가 없다 (% 환산 금지)."""
    viol = [s for s in _strings() if "%" in s]
    assert not viol, f"% 문자 발견 (D-09 % 환산 금지): {viol}"


def test_no_bare_digits_in_rendered_copy() -> None:
    """D-09 — 렌더 카피 슬롯 텍스트에 수치 없음 (수치는 렌더 시 소형 신뢰 배지 담당)."""
    viol = [s for s in _strings() if re.search(r"[0-9]", s)]
    assert not viol, f"렌더 카피에 수치 발견 (D-09 위반): {viol}"


def test_sanity_extraction_nonzero() -> None:
    """sanity — 추출 string 수 ≥ 50 (0-string 게이트 무의미 회귀 차단)."""
    strings = _strings()
    assert len(strings) >= 50, (
        f"렌더 카피 추출이 {len(strings)} 개 — 게이트 무의미 의심 (경로/스키마 확인)"
    )
