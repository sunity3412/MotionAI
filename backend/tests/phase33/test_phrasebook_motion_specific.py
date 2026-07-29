"""Plan 33-09 Task 1 — 동작 전용(motion-specific) phrasebook override 검증 (D-02/D-14).

phase32 선례(test_phrasebook_assembly.py 우선순위 + test_phrasebook_forbidden.py
D-09 게이트)를 계승하고, phase33 신규 사실을 박제한다: 등록 동작 x 방출 criterion
조합이 `{motion_key}.{criterion}` 전용 entry 로 `__common__` **보다 먼저** 해소된다
— power-spin 다리 큐가 공통 leg_extension 의 "천장" 큐로 떨어지지 않는다 (D-14).

데이터 무결성 게이트 (D-18 — 틀리면 걸리는 장치):
  · override 미작성 → test_motion_specific_overrides_common RED.
  · 새 카피에 수치/% 유입 → 금지어 게이트 RED (phase32 게이트 verbatim 재사용).
  · 전용 키가 미등재 동작/유령 criterion/유령 exerciseId 참조 → 유효성 테스트 RED.
  · _meta.coverageMatrix 와 entries 불일치 → lockstep 테스트 RED.

순수 함수/데이터만 — boto3/네트워크 무접촉 (conftest sys.path 주입).
phrasebook.py 는 무변경 (33-09 code-change-0) — 데이터가 lookup 을 채운다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from sunity_shared.analysis import phrasebook
from sunity_shared.analysis.gemini_motion_classifier import REGISTERED_MOTIONS
from sunity_shared.analysis.phrasebook import (
    FORBIDDEN_PHRASES_PHRASEBOOK,
    FORBIDDEN_REGEX_PHRASEBOOK,
    rendered_copy_strings,
)

_BACKEND = Path(__file__).resolve().parents[2]
_PHRASEBOOK_PATH = _BACKEND / "data" / "phrasebook.json"
_EXERCISES_PATH = _BACKEND / "data" / "corrective_exercises.json"

_COMMON_PREFIX = "__common__"


def _is_flat_scalar_dict(d: dict) -> bool:
    """반환 dict 가 flat scalar 인지 (nested list/dict 0 — Firestore flat 저장 가능)."""
    if not isinstance(d, dict):
        return False
    return all(v is None or isinstance(v, (str, int, float, bool)) for v in d.values())


def _load_fixture() -> dict:
    return json.loads(_PHRASEBOOK_PATH.read_text(encoding="utf-8"))


def _motion_specific_keys(entries: dict) -> list[str]:
    """`{motion_key}.{criterion}` 전용 키만 (— __common__ 제외)."""
    return [k for k in entries if not k.startswith(f"{_COMMON_PREFIX}.")]


# ── Test 1 — 동작 전용 override 가 __common__ 보다 먼저 해소 (D-14 핵심) ──────────
def test_motion_specific_overrides_common() -> None:
    """등록 동작 x 방출 criterion → 전용 cueLine (미등재 동작의 공통 cueLine 과 다름)."""
    specific = phrasebook.assemble_phrases("ref-power-spin", "leg_extension")
    common = phrasebook.assemble_phrases("어떤_미등재_동작", "leg_extension")
    assert specific.get("cueLine") and specific["cueLine"] != common["cueLine"], (
        "동작 전용 cueLine 이 __common__ 과 동일 (override 미작동 또는 데이터 미작성)"
    )
    assert _is_flat_scalar_dict(specific), f"nested 값 발견: {specific}"


def test_power_spin_leg_cue_not_ceiling() -> None:
    """D-14 헤드라인 케이스 — power-spin 은 폴 축 상하 수직 스플릿 (33-A1 실측 f71~f92).

    공통 leg_extension 의 '천장' 큐로 떨어지면 위·아래 두 다리 중 아래 다리에
    오답 지시가 된다. 전용 entry 의 cueLine 은 '천장' 을 말하지 않는다.
    """
    slots = phrasebook.assemble_phrases("ref-power-spin", "leg_extension")
    assert slots.get("cueLine"), "power-spin leg_extension 전용 cueLine 부재"
    assert "천장" not in slots["cueLine"], (
        f"power-spin 다리 큐가 여전히 천장을 말함 (D-14 위반): {slots['cueLine']!r}"
    )


def test_unregistered_motion_still_falls_to_common() -> None:
    """전용 entry 추가 후에도 미등재 동작(ref-combo 포함)은 공통 경로 유지 (회귀 방지)."""
    slots = phrasebook.assemble_phrases("ref-combo", "leg_extension")
    fixture = _load_fixture()
    assert slots["cueLine"] == fixture["entries"]["__common__.leg_extension"]["cueLine"]
    assert not slots.get("failClosed")


# ── Test 2 — 전용 키 유효성 (fabrication 0: 등록 동작 x 실존 criterion x 실존 운동) ──
def test_motion_specific_keys_are_valid() -> None:
    """전용 키의 motion = REGISTERED_MOTIONS 실존, criterion = __common__ 실존 criterion,
    exerciseId = corrective_exercises.json defects 실존 키. override 0 이면 RED (미작성)."""
    fixture = _load_fixture()
    entries = fixture["entries"]
    specific_keys = _motion_specific_keys(entries)
    assert specific_keys, "동작 전용 entry 가 0개 — 33-09 데이터 미작성 (D-14)"

    common_criteria = {
        k.split(".", 1)[1] for k in entries if k.startswith(f"{_COMMON_PREFIX}.")
    }
    defects = set(
        json.loads(_EXERCISES_PATH.read_text(encoding="utf-8"))["defects"].keys()
    )
    for key in specific_keys:
        motion, _, criterion = key.partition(".")
        assert motion in REGISTERED_MOTIONS, f"{key}: 미등재 동작 키 (fabrication)"
        assert criterion in common_criteria, f"{key}: 유령 criterion (방출 불가 조합)"
        entry = entries[key]
        # 필수 3 슬롯 (fail-closed 조합도 이 3 슬롯은 보유).
        for slot in ("statusLine", "whyLine", "coachQuestion"):
            assert isinstance(entry.get(slot), str) and entry[slot], (
                f"{key}: 필수 슬롯 {slot} 누락/빈 문자열"
            )
        # cueLine 보유 시 운동 연결 완결 (D-13) + exerciseId 실존.
        if "cueLine" in entry:
            assert isinstance(entry["cueLine"], str) and entry["cueLine"]
            assert entry.get("exerciseId") in defects, (
                f"{key}: exerciseId {entry.get('exerciseId')!r} 가 defects 에 없음"
            )
            assert isinstance(entry.get("exerciseReason"), str) and entry["exerciseReason"]


def test_coverage_matrix_lockstep() -> None:
    """_meta.coverageMatrix.motionOverrides 가 실제 entries 와 lockstep (drift 차단)."""
    fixture = _load_fixture()
    overrides_meta = fixture["_meta"]["coverageMatrix"].get("motionOverrides", {})
    declared = {
        f"{motion}.{criterion}"
        for motion, criteria in overrides_meta.items()
        for criterion in criteria
    }
    actual = set(_motion_specific_keys(fixture["entries"]))
    assert declared == actual, (
        f"coverageMatrix.motionOverrides 와 entries 불일치 — "
        f"meta에만: {sorted(declared - actual)} / entries에만: {sorted(actual - declared)}"
    )


# ── Test 3 — 금지어 게이트 (phase32 test_phrasebook_forbidden.py verbatim 재사용) ──
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
    """D-09 — 렌더 카피 슬롯 텍스트에 수치 없음 (신규 전용 entry 포함 전수)."""
    viol = [s for s in _strings() if re.search(r"[0-9]", s)]
    assert not viol, f"렌더 카피에 수치 발견 (D-09 위반): {viol}"


def test_sanity_extraction_nonzero() -> None:
    """sanity — 추출 string 수 ≥ 50 (0-string 게이트 무의미 회귀 차단)."""
    strings = _strings()
    assert len(strings) >= 50, (
        f"렌더 카피 추출이 {len(strings)} 개 — 게이트 무의미 의심 (경로/스키마 확인)"
    )


# ── Test 4 — 33-13 (A-6, belle 확인 ① 7R/4R 규칙) 화면 어휘 게이트 + 목표-선행 ──
def _fixture_copy_strings(fixture: dict) -> list[tuple[str, str]]:
    """phrasebook.json 안의 화면 렌더 카피 (path, text) 전수 — entries + safetyEntries
    + failClosed. _meta 는 provenance 문서라 스코프 밖 (phase32 forbidden 게이트와
    동일 원칙). terminology_map 은 용어 사전(내부 용어를 번역하는 것이 존재 이유)
    이라 이 게이트의 대상이 아니다."""
    out: list[tuple[str, str]] = []

    def walk(obj: object, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")
        elif isinstance(obj, str):
            out.append((path, obj))

    walk(fixture.get("entries", {}), "entries")
    walk(fixture.get("safetyEntries", {}), "safetyEntries")
    walk(fixture.get("failClosed", {}), "failClosed")
    return out


def test_screen_vocabulary_gate() -> None:
    """33-13 (A-6) — 채점 내부 용어(국면·신전·재신전·완성도)는 화면 문장 금지.

    belle 확인 ① 7R 규칙 (b): 내부 용어는 내부 기록 전용, 화면은 수강생·강사
    실사용 어휘. 어휘 목록은 데이터(_meta.screenVocabularyGate.words)로 운용 —
    동작·항목 무관 공통 (동작명 하드코딩 0)."""
    fixture = _load_fixture()
    words = fixture["_meta"]["screenVocabularyGate"]["words"]
    assert words, "_meta.screenVocabularyGate.words 부재 — 어휘 게이트 데이터 소실"
    viol = [
        (path, w)
        for path, text in _fixture_copy_strings(fixture)
        for w in words
        if w in text
    ]
    assert not viol, f"화면 어휘 게이트 위반 (채점 내부 용어 화면 노출): {viol}"


def test_motion_specific_cueline_goal_first() -> None:
    """33-13 (A-6) — 동작 전용 cueLine 은 목표-선행 문형 (belle 4R 승인:
    '목표는 …이에요. <행동 큐>'). 목표 문장 = 33-A1 완성 기준의 검증 claim 만 —
    동작별 데이터(cueLine 선두)로 운용, __common__ 은 동작 미상이라 대상 밖
    (일반론 목표 fabrication 금지)."""
    fixture = _load_fixture()
    entries = fixture["entries"]
    viol = [
        k
        for k in _motion_specific_keys(entries)
        if isinstance(entries[k].get("cueLine"), str)
        and not entries[k]["cueLine"].startswith("목표는 ")
    ]
    assert not viol, f"목표-선행 미적용 동작 전용 cueLine: {viol}"
