"""Plan 32-06 Task 2 — 계약 3면 lockstep + scoped validator 검증 (D-08/D-28/D-29).

3중 대조 (계약 lockstep 텍스트 대조 선례 — test_terminology_lockstep 복제):
  1. models.py 상수(MISSION_KEYS 블록) ↔ app/src/types/analysis.ts 문자열 존재.
  2. docs/contract.md §12 절 존재 (recordId ≥1 + summaryPraise ≥1 — acceptance).
  3. 앱 normalize(userAnalyses.ts) 헬퍼 존재 (4면 대칭 — validator↔normalize).

validator 행동 (motionAlignment 선례 뼈대):
  - 화이트리스트/enum/finite/상한 (streak 1..99, headline·text ≤200, 문항 ≤10).
  - source='user' 백엔드 방출 거부 (클라이언트 로컬 전용 경계 — contract.md §12.5).
  - complete_analysis 시그니처 diff 0 (신규 kwarg 없음 — SP-1 "result 안으로
    흐른다") + result 경유 wiring 실증 (malformed → ValueError, Firestore 무접촉).
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path

import pytest

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import mission

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TS_ANALYSIS = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_TS_USER_ANALYSES = _REPO_ROOT / "app" / "src" / "lib" / "userAnalyses.ts"
_CONTRACT = _REPO_ROOT / "docs" / "contract.md"


def _ts_text() -> str:
    return _TS_ANALYSIS.read_text(encoding="utf-8")


# ── 1. models.py 상수 존재 + 형상 ───────────────────────────────────────────


def test_models_constants_exist_exact() -> None:
    assert models.MISSION_KEYS == (
        "faultKey", "criterion", "ruleId", "recordId", "selectedBy", "streak",
        "isSafety", "escalation", "motionId", "baselinePoints",
        "baselineDeviation", "targetValue", "unit",
    )
    assert models.MISSION_SELECTED_BY == ("safety", "repeat", "max_deduction")
    assert models.MISSION_ESCALATIONS == ("none", "exercise_detour", "coach_card")
    assert models.MISSION_OUTCOME_KEYS == (
        "improved", "faultKey", "criterion", "baselinePoints", "currentPoints",
        "deltaPoints", "baselineDeviation", "currentDeviation", "deltaDeviation",
    )
    assert models.DEDUCTION_PHRASE_KEYS == (
        "statusLine", "whyLine", "cueLine", "coachQuestion", "exerciseId",
        "exerciseReason",
    )
    # §12.3 additive optional 전체 집합 — 필수/optional 키와 disjoint.
    assert models.DEDUCTION_RECORD_EXTENSION_KEYS == (
        ("recordId",) + models.DEDUCTION_PHRASE_KEYS + ("tolerance",)
    )
    assert not set(models.DEDUCTION_RECORD_EXTENSION_KEYS) & (
        set(models.DEDUCTION_RECORD_KEYS)
        | set(models.DEDUCTION_RECORD_OPTIONAL_KEYS)
    )
    assert models.SUMMARY_PRAISE_KEYS == (
        "source", "headline", "evidenceValue", "evidenceUnit",
    )
    assert models.SUMMARY_PRAISE_SOURCES == (
        "mission_improved", "clean_dimension", "criteria_met",
    )
    assert models.COACH_QUESTION_SOURCES == (
        "safety", "mission_stuck", "unmeasured", "user",
    )
    assert models.MISSION_STREAK_MAX == 99


def test_phrase_keys_lockstep_with_phrasebook_slots() -> None:
    """DEDUCTION_PHRASE_KEYS == phrasebook._ENTRY_SLOTS (32-05 조립 슬롯 동형)."""
    from sunity_shared.analysis import phrasebook

    assert models.DEDUCTION_PHRASE_KEYS == phrasebook._ENTRY_SLOTS


# ── 2. models ↔ analysis.ts 텍스트 lockstep ────────────────────────────────


def test_mission_keys_present_in_ts() -> None:
    text = _ts_text()
    for key in (
        models.MISSION_KEYS
        + models.MISSION_OUTCOME_KEYS
        + models.SUMMARY_PRAISE_KEYS
        + models.DEDUCTION_PHRASE_KEYS
        + ("recordId", "tolerance", "coachQuestions")
    ):
        assert key in text, f"analysis.ts 에 계약 키 {key!r} 부재"


def test_enum_literals_present_in_ts() -> None:
    text = _ts_text()
    for value in (
        models.MISSION_SELECTED_BY
        + models.MISSION_ESCALATIONS
        + models.SUMMARY_PRAISE_SOURCES
        + models.COACH_QUESTION_SOURCES
    ):
        assert f"'{value}'" in text, f"analysis.ts 에 enum 리터럴 {value!r} 부재"


def test_interfaces_present_in_ts() -> None:
    text = _ts_text()
    for name in (
        "export interface Mission {",
        "export interface MissionOutcome {",
        "export interface SummaryPraise {",
        "export interface CoachQuestion {",
    ):
        assert name in text, f"analysis.ts 에 {name!r} 부재"
    # AnalysisResult 소비 필드 4종.
    for field in (
        "mission?: Mission",
        "missionOutcome?: MissionOutcome",
        "summaryPraise?: SummaryPraise",
        "coachQuestions?: CoachQuestion[]",
    ):
        assert field in text, f"analysis.ts AnalysisResult 에 {field!r} 부재"


def test_user_source_client_local_boundary_documented() -> None:
    """source='user' 클라이언트 로컬 전용 경계 — TS 주석 + contract 절 1줄씩."""
    assert "로컬 전용" in _ts_text()
    assert "로컬 전용" in _CONTRACT.read_text(encoding="utf-8")


# ── 3. contract.md §12 절 존재 (acceptance grep) ───────────────────────────


def test_contract_md_section_present() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert text.count("recordId") >= 1
    assert text.count("summaryPraise") >= 1
    assert "## §12." in text
    assert "faultKey" in text
    assert "coachQuestions" in text


# ── 4. 앱 normalize 대칭 (4면) ─────────────────────────────────────────────


def test_app_normalize_helpers_present() -> None:
    text = _TS_USER_ANALYSES.read_text(encoding="utf-8")
    for helper in (
        "function normalizeMission(",
        "function normalizeMissionOutcome(",
        "function normalizeSummaryPraise(",
        "function normalizeCoachQuestions(",
        "function normalizeRecordPhraseFields(",
    ):
        assert helper in text, f"userAnalyses.ts 에 {helper!r} 부재"


# ── 5. validator 행동 — _validate_mission ──────────────────────────────────


def _valid_mission() -> dict:
    """엔진 실산출물이 validator 를 통과하는지 — 엔진↔저장층 통합 대조."""
    rec = {
        "criterion": "angle_vs_reference__left_knee",
        "measuredValue": 141.0,
        "baselineValue": 180.0,
        "baselineKind": None,
        "deviation": 39.0,
        "ruleId": "angle_vs_reference_over_tol_linear",
        "points": -8.0,
        "unit": "deg",
        "ipsfAnchor": "IPSF CoP Page 9",
        "source": "geometry",
        "deviationSource": "ipsf_absolute",
    }
    m = mission.select_mission([rec], None, None, "kip-up")
    assert m is not None
    return m


def test_validate_mission_accepts_engine_output() -> None:
    firestore_admin._validate_mission(_valid_mission())  # no raise
    firestore_admin._validate_mission(None)  # None graceful


def test_validate_mission_accepts_safety_engine_output() -> None:
    flag = {"flagType": "trunk_hyperextension", "bodyRegion": "trunk"}
    m = mission.select_mission([], [flag], None, "kip-up")
    firestore_admin._validate_mission(m)  # no raise — D-14 형상도 통과


def test_validate_mission_rejects_extra_key() -> None:
    bad = {**_valid_mission(), "cueText": "무릎으로 가슴을"}
    with pytest.raises(ValueError, match="화이트리스트"):
        firestore_admin._validate_mission(bad)


def test_validate_mission_rejects_bad_enums() -> None:
    with pytest.raises(ValueError, match="selectedBy"):
        firestore_admin._validate_mission({**_valid_mission(), "selectedBy": "llm"})
    with pytest.raises(ValueError, match="escalation"):
        firestore_admin._validate_mission({**_valid_mission(), "escalation": "boss"})


def test_validate_mission_rejects_streak_out_of_range() -> None:
    for streak in (0, 100, -1):
        with pytest.raises(ValueError, match="streak"):
            firestore_admin._validate_mission({**_valid_mission(), "streak": streak})
    with pytest.raises(ValueError, match="streak"):
        firestore_admin._validate_mission({**_valid_mission(), "streak": True})


def test_validate_mission_rejects_bad_baseline() -> None:
    with pytest.raises(ValueError, match="baselinePoints"):
        firestore_admin._validate_mission(
            {**_valid_mission(), "baselinePoints": -1.0}
        )
    with pytest.raises(ValueError, match="baselinePoints"):
        firestore_admin._validate_mission(
            {**_valid_mission(), "baselinePoints": math.nan}
        )


def test_validate_mission_rejects_non_dict() -> None:
    with pytest.raises(ValueError, match="dict"):
        firestore_admin._validate_mission(["not", "a", "dict"])


# ── 6. validator 행동 — _validate_mission_outcome ──────────────────────────


def _valid_outcome() -> dict:
    prev = _valid_mission()
    out = mission.derive_mission_outcome(prev, [], models.MODE_SELF, "kip-up")
    assert out is not None
    return out


def test_validate_mission_outcome_accepts_engine_output() -> None:
    firestore_admin._validate_mission_outcome(_valid_outcome())  # no raise
    firestore_admin._validate_mission_outcome(None)  # None graceful


def test_validate_mission_outcome_rejects_extra_and_nan() -> None:
    with pytest.raises(ValueError, match="화이트리스트"):
        firestore_admin._validate_mission_outcome(
            {**_valid_outcome(), "deltaSummary": "지난번보다 좋아졌어요"}
        )
    with pytest.raises(ValueError, match="deltaPoints"):
        firestore_admin._validate_mission_outcome(
            {**_valid_outcome(), "deltaPoints": math.inf}
        )
    with pytest.raises(ValueError, match="improved"):
        firestore_admin._validate_mission_outcome(
            {**_valid_outcome(), "improved": "yes"}
        )


# ── 7. validator 행동 — _validate_summary_praise ───────────────────────────


def _valid_praise() -> dict:
    return {
        "source": "mission_improved",
        "headline": "무릎이 지난번보다 훨씬 더 접혔어요",
        "evidenceValue": 3.0,
        "evidenceUnit": "점",
    }


def test_validate_summary_praise_accepts_valid() -> None:
    firestore_admin._validate_summary_praise(_valid_praise())
    firestore_admin._validate_summary_praise(None)  # None graceful


def test_validate_summary_praise_rejects_bad_source_and_headline() -> None:
    with pytest.raises(ValueError, match="source"):
        firestore_admin._validate_summary_praise(
            {**_valid_praise(), "source": "vibes"}
        )
    with pytest.raises(ValueError, match="headline"):
        firestore_admin._validate_summary_praise({**_valid_praise(), "headline": " "})
    with pytest.raises(ValueError, match="headline"):
        firestore_admin._validate_summary_praise(
            {**_valid_praise(), "headline": "가" * 201}
        )
    with pytest.raises(ValueError, match="evidenceValue"):
        firestore_admin._validate_summary_praise(
            {**_valid_praise(), "evidenceValue": math.nan}
        )


# ── 8. validator 행동 — _validate_coach_questions ──────────────────────────


def _valid_question(source: str = "safety") -> dict:
    return {
        "text": "이 부분이 안전한지 강사님과 함께 확인해보고 싶어요",
        "source": source,
        "recordId": "r00:angle_vs_reference__left_knee",
    }


def test_validate_coach_questions_accepts_valid() -> None:
    firestore_admin._validate_coach_questions(
        [_valid_question("safety"), _valid_question("mission_stuck"),
         _valid_question("unmeasured")]
    )
    firestore_admin._validate_coach_questions(None)  # None graceful
    firestore_admin._validate_coach_questions([])  # 빈 목록 허용


def test_validate_coach_questions_rejects_user_source() -> None:
    # 'user' 는 클라이언트 로컬 전용 — 백엔드 방출에 나타나면 계약 위반.
    with pytest.raises(ValueError, match="user"):
        firestore_admin._validate_coach_questions([_valid_question("user")])


def test_validate_coach_questions_rejects_cap_and_text() -> None:
    with pytest.raises(ValueError, match="상한"):
        firestore_admin._validate_coach_questions([_valid_question()] * 11)
    with pytest.raises(ValueError, match="text"):
        firestore_admin._validate_coach_questions(
            [{**_valid_question(), "text": "가" * 201}]
        )
    with pytest.raises(ValueError, match="text"):
        firestore_admin._validate_coach_questions([{**_valid_question(), "text": ""}])


def test_validate_coach_questions_rejects_nested() -> None:
    with pytest.raises((TypeError, ValueError)):
        firestore_admin._validate_coach_questions(
            [{**_valid_question(), "meta": {"nested": True}}]
        )
    with pytest.raises(TypeError):
        firestore_admin._validate_coach_questions("not-a-list")


# ── 9. complete_analysis — 신규 kwarg 0 + result 경유 wiring ───────────────


def test_complete_analysis_signature_no_new_kwargs() -> None:
    """SP-1 — mission 계열은 result 안으로만 흐른다 (시그니처 diff 0)."""
    params = set(inspect.signature(firestore_admin.complete_analysis).parameters)
    forbidden = {
        "mission", "mission_outcome", "summary_praise", "coach_questions",
        "missionOutcome", "summaryPraise", "coachQuestions",
    }
    assert not (params & forbidden), f"신규 kwarg 유입: {params & forbidden}"


def test_complete_analysis_validates_mission_via_result() -> None:
    """malformed mission 이 result 로 흘러오면 Firestore 접촉 전에 ValueError."""
    with pytest.raises(ValueError, match="mission"):
        firestore_admin.complete_analysis(
            "u1", "a1", {"mission": {"faultKey": ""}}
        )
    with pytest.raises(ValueError, match="coachQuestions"):
        firestore_admin.complete_analysis(
            "u1", "a1", {"coachQuestions": [_valid_question("user")]}
        )
    with pytest.raises(ValueError, match="summaryPraise"):
        firestore_admin.complete_analysis(
            "u1", "a1", {"summaryPraise": {"source": "vibes", "headline": "x"}}
        )


def test_records_phrase_extension_passes_existing_validator() -> None:
    """record 확장 키(recordId/3단 문구/tolerance)는 flat scalar 라 기존
    _validate_deduction_breakdown 경로 자동 통과 (validator 본체 무변경 실증)."""
    breakdown = {
        "baseline": 100,
        "final": 92,
        "records": [
            {
                "criterion": "angle_vs_reference__left_knee",
                "points": -8.0,
                "recordId": "r00:angle_vs_reference__left_knee",
                "statusLine": "무릎이 기준보다 덜 접혔어요",
                "whyLine": "다리 라인이 흐트러져 심사에서 감점되는 부분이에요",
                "cueLine": "무릎으로 가슴을 끌어안듯 접어보세요",
                "coachQuestion": "무릎 접힘이 어디서 막히는지 봐주실 수 있나요",
                "exerciseId": "hip_hamstring_stretch",
                "exerciseReason": "고관절 유연성이 무릎 접힘을 만들어요",
                "tolerance": 10.0,
            }
        ],
    }
    firestore_admin._validate_deduction_breakdown(breakdown)  # no raise
