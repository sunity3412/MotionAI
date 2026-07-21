"""동작×결함 고정 문구집 조립 layer (Phase 32 Plan 32-05 / D-08·D-11·D-13·D-14).

감점 카드 3단(상태→왜→행동)+코치 질문+운동 연결의 **골격**을 backend/data/
phrasebook.json fixture 에서 조립한다. LLM(coach_writer)은 가변부(상황 수치·조사
연결·응원 톤)만 소유하고, 골격은 이 fixture 가 소유해 "무릎을 더 펴세요" 수준의
일반론 생성 경로를 차단한다 (D-11). 32-09 방출·32-10 렌더의 데이터 원천.

순수성 (Layer 2 boto3 영구 차단 — exercise_map.py / copy_templates.py 패턴 정합):
  - numpy/AWS-free, network-free. 단위 test 로 전부 검증.
  - 입력은 str|None, 출력은 plain camelCase scalar dict (dataclass 아님 —
    Firestore 가 그대로 저장, nested array/dict 0 [[firestore-nested-array-flat]]).

3-way / lockstep 정합:
  - phrasebook.json entry 키 = ipsf_criteria.CRITERION_GROUPS 실존 criterion +
    deduction_engine dimension_overall_fallback + safety_flags._FLAG_TYPES.
  - terminology_map.json 은 app/src/lib/terminologyMap.ts 의 단일 출처 —
    test_terminology_lockstep.py 가 양방향 텍스트 대조로 drift 차단 (D-12).

fail-closed 원칙 (D-11 일반론 금지의 폴백): 미지원 조합/저정보 criterion
(dimension_overall_fallback)은 cueLine/exerciseId 를 **생성하지 않는다** — whyLine 은
안전한 사실만, coachQuestion 으로 강사 확인을 유도한다 (조언 fabrication 0).
"""

from __future__ import annotations

import json
from pathlib import Path

# ── fixture 경로 (exercise_map._CORRECTIVE_EXERCISES_PATH 패턴 정합:
#    analysis → sunity_shared → python → shared → backend / "data") ──────────────
_PHRASEBOOK_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "data" / "phrasebook.json"
)
_TERMINOLOGY_MAP_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "data" / "terminology_map.json"
)
_PHRASEBOOK_CACHE: dict | None = None
_TERMINOLOGY_CACHE: dict | None = None

# ── entry 슬롯 키 (정상 히트) / fail-closed 슬롯 키 / safety 슬롯 키 ────────────
_ENTRY_SLOTS = (
    "statusLine",
    "whyLine",
    "cueLine",
    "coachQuestion",
    "exerciseId",
    "exerciseReason",
)
_SAFETY_SLOTS = ("statusLine", "whyLine", "coachQuestion")
# fail-closed 는 cueLine/exerciseId/exerciseReason 를 **생략** (일반론 조언 생성 차단).
_FAIL_CLOSED_SLOTS = ("statusLine", "whyLine", "coachQuestion")

_COMMON_PREFIX = "__common__"

# ── 금지어 게이트 (D-09/D-11) — copy_templates.FORBIDDEN_PHRASES_SUNITY 확장 ──
# 렌더 카피에서 0회여야 하는 리터럴. 본 tuple 자체는 게이트 scope 밖(렌더 카피 아님).
FORBIDDEN_PHRASES_PHRASEBOOK: tuple[str, ...] = (
    "%일치",  # [[mode3-progress-not-similarity]]
    "유사도",  # 동일 — 수치 유사도 헤드라인 금지
    "박제",  # [[no-baekje-filler]]
)
# D-09 위반 정규식 — % 환산 + 'N도만큼' 수치-지시 일반론.
FORBIDDEN_REGEX_PHRASEBOOK: tuple[str, ...] = (
    r"\d+\s*%",
    r"\d+(?:\.\d+)?\s*(?:도|°)\s*만큼",
)

# 미등재 safety 유형 폴백 — 조언 생성 0, 강사 확인 유도만 (D-14).
_GENERIC_SAFETY = {
    "statusLine": "안전과 관련해 살펴볼 부분이 있어요",
    "whyLine": "무리한 자세는 부상으로 이어질 수 있어요",
    "coachQuestion": "이 부분이 안전한지 강사님과 이 화면을 함께 확인해보고 싶어요",
}


def _load_phrasebook() -> dict:
    """phrasebook.json lazy load + 모듈 캐시."""
    global _PHRASEBOOK_CACHE
    if _PHRASEBOOK_CACHE is None:
        _PHRASEBOOK_CACHE = json.loads(
            _PHRASEBOOK_PATH.read_text(encoding="utf-8")
        )
    return _PHRASEBOOK_CACHE


def load_terminology_map() -> dict:
    """terminology_map.json lazy load + 모듈 캐시.

    whyLine 심사 용어·앱 terminologyMap.ts 미러의 단일 출처. `{_meta, terms}` 형상.
    """
    global _TERMINOLOGY_CACHE
    if _TERMINOLOGY_CACHE is None:
        _TERMINOLOGY_CACHE = json.loads(
            _TERMINOLOGY_MAP_PATH.read_text(encoding="utf-8")
        )
    return _TERMINOLOGY_CACHE


def _entry_slots(entry: dict) -> dict:
    """정상 히트 entry → 6 슬롯 flat scalar dict (fabrication 0 — 있는 값만)."""
    return {slot: entry.get(slot) for slot in _ENTRY_SLOTS}


def _fail_closed_slots() -> dict:
    """fail-closed 폴백 — cueLine/exerciseId 생략 + failClosed 마커 (D-11).

    미지원 조합은 조언을 만들지 않는다: 행동 큐/운동 연결 없음, whyLine 은 안전한
    사실만, coachQuestion 으로 강사 확인 유도. 렌더(32-10)는 failClosed=True 를
    보고 행동문·운동 카드를 생략한다.
    """
    fc = _load_phrasebook().get("failClosed", {})
    out = {slot: fc.get(slot) for slot in _FAIL_CLOSED_SLOTS}
    out["failClosed"] = True
    return out


def assemble_phrases(
    motion_key: str | None,
    criterion: str,
    rule_id: str | None = None,
) -> dict:
    """동작 × criterion → 감점 카드 슬롯 dict (매칭 우선순위 + fail-closed).

    Args:
        motion_key: 인식된 동작 id (REGISTERED_MOTIONS) 또는 raw_name/None
            (미등재/인식 실패). 공통 entry 는 동작 독립이라 미등재도 phrasing 이
            비지 않는다.
        criterion: DeductionRecord.criterion (ipsf_criteria 실존 방출값 +
            dimension_overall_fallback).
        rule_id: DeductionRecord.ruleId — 현재 매칭 미사용(criterion 이 라우팅
            키). 향후 rule 별 세분화 hook 으로 시그니처에 보존.

    매칭 우선순위: {motion_key}.{criterion} (동작 전용 override) →
        {__common__}.{criterion} (criterion 공통) → fail-closed.

    Returns:
        정상 히트: {statusLine, whyLine, cueLine, coachQuestion, exerciseId,
            exerciseReason} flat scalar dict.
        fail-closed: {statusLine, whyLine, coachQuestion, failClosed:True} —
            cueLine/exerciseId 없음 (일반론 조언 생성 차단). 크래시 0 (graceful).
    """
    entries = _load_phrasebook().get("entries", {})
    if motion_key:
        specific = entries.get(f"{motion_key}.{criterion}")
        if isinstance(specific, dict):
            return _entry_slots(specific)
    common = entries.get(f"{_COMMON_PREFIX}.{criterion}")
    if isinstance(common, dict):
        return _entry_slots(common)
    return _fail_closed_slots()


def assemble_safety_phrases(flag_type: str) -> dict:
    """safetyFlags 유형 → 안전 슬롯 dict (D-14 차분한 안전 톤, 게임 요소 0).

    Returns:
        {statusLine, whyLine, coachQuestion} — cueLine·미션·게이지 키 없음.
        미등재 유형은 generic 안전 유도문 (조언 생성 0). 32-09 안전 질문 조립의
        매핑 원천. 크래시 0 (graceful).
    """
    safety = _load_phrasebook().get("safetyEntries", {})
    entry = safety.get(flag_type)
    if isinstance(entry, dict):
        return {slot: entry.get(slot) for slot in _SAFETY_SLOTS}
    return dict(_GENERIC_SAFETY)


def rendered_copy_strings() -> list[str]:
    """금지어 게이트용 — 화면에 렌더되는 카피 string 만 수집 (_meta provenance 제외).

    스코프: phrasebook entries 슬롯 + safetyEntries + failClosed + terminology
    terms 값. _meta(근거 수치·코드경로·메모리 태그 인용)는 사용자 카피가 아니므로
    제외한다 (copy_templates AST 게이트가 docstring/FORBIDDEN tuple 을 scope 밖으로
    두는 것과 동일 원칙 — test_phrasebook_forbidden.py 스코프 근거).
    """
    pb = _load_phrasebook()
    out: list[str] = []

    def _collect(obj) -> None:
        if isinstance(obj, str):
            out.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _collect(v)
        elif isinstance(obj, list):
            for v in obj:
                _collect(v)

    _collect(pb.get("entries", {}))
    _collect(pb.get("safetyEntries", {}))
    _collect(pb.get("failClosed", {}))
    _collect(load_terminology_map().get("terms", {}))
    return out
