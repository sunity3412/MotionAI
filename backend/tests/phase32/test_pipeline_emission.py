"""Plan 32-09 — 파이프라인 번역 레이어·미션 루프 방출 통합 테스트 (D-08/D-11/D-19/D-26~D-29).

behavior 6건 (플랜 Task 2 스펙) + coach_writer 가변부 한정 게이트 2건:
  1. Cerebras 무키 환경에서 record 3단(statusLine/whyLine/cueLine)이 문구집 골격
     그대로 방출 (LLM 없이 3단 성립 — D-11).
  2. safetyFlags 입력 → mission.selectedBy=='safety' + isSafety + escalation 'none'
     + coachQuestions source='safety' (D-14 정합).
  3. prev chain — 동일 faultKey 잔존 시 streak 증가, 3회차 coach_card 승격 +
     coachQuestions source='mission_stuck' (recordId 조인). prev motionId 불일치 →
     streak 1 리셋.
  4. summaryPraise — outcome.improved → source 'mission_improved' + headline 수치
     부재(D-09) + evidenceValue 수치 분리.
  5. record 격리 — 한 record 조립 예외 주입에도 다른 record 문구·mission·praise 잔존.
  6. 방출 전체가 32-06 scoped validator 를 예외 없이 통과 (fake_firestore 경유
     complete_analysis 저장 성공).
  7-8. coach_writer — 시스템 프롬프트 슬롯 한정·일반론 금지 명문화 + LLM 출력
     런타임 금지어 필터 (FORBIDDEN_PHRASES_PHRASEBOOK 사후 필터, D-11).

LOCAL ONLY — 실 Firestore/AWS/Cerebras 무접촉. LLM 은 무키 환경 자연 no-op.
pipeline app.py 는 파일 경로 spec 로드(고유 모듈명) — tests/pipeline 의 'app'
모듈명 충돌 회피.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
import types
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2]
_PHASE31 = _BACKEND / "tests" / "phase31"

from sunity_shared import firestore_admin, models  # noqa: E402
from sunity_shared.analysis import phrasebook  # noqa: E402


# ─────────────────────── pipeline app 모듈 로드 (고유 이름) ───────────────────────


def _load_pipeline_app():
    name = "pipeline_app_phase32_emission"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, _BACKEND / "functions" / "pipeline" / "app.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def papp():
    return _load_pipeline_app()


@pytest.fixture(autouse=True)
def _no_cerebras_key(monkeypatch):
    """Cerebras 무키 환경 강제 — LLM 어댑터 자연 no-op (D-11 골격 성립 전제)."""
    monkeypatch.delenv("CEREBRAS_KEY_PARAM", raising=False)


# ─────────────────────── fixture: result/record/prev 빌더 ───────────────────────

_FAULT_KEY = "power-spin::leg_extension_over_tol_linear::leg_extension"


def _leg_record(points: float = -22.8) -> dict:
    return {
        "criterion": "leg_extension",
        "measuredValue": 141.0,
        "baselineValue": 180,
        "baselineKind": None,
        "deviation": 19.0,
        "ruleId": "leg_extension_over_tol_linear",
        "points": points,
        "unit": "deg",
        "ipsfAnchor": "19-IPSF §A 트랙2 (다리 신전 부족 누적 감점)",
        "source": "geometry",
        "deviationSource": "ipsf_absolute",
    }


def _shoulder_record() -> dict:
    return {
        "criterion": "angle_vs_reference__left_shoulder",
        "measuredValue": 100.0,
        "baselineValue": 130.0,
        "baselineKind": None,
        "deviation": 10.0,
        "ruleId": "angle_vs_reference_over_tol_linear",
        "points": -12.0,
        "unit": "deg",
        "ipsfAnchor": "expert_reference_deviation",
        "source": "geometry",
        "deviationSource": "reference_relative",
    }


def _result(records: list[dict], *, safety: list | None = None) -> dict:
    out = {
        "overallScore": 66,
        "dimensionScores": {"angle": 70, "line": 80, "stability": 100},
        "deductionBreakdown": {
            "baseline": 100,
            "records": records,
            "final": 66,
            "coverageGaps": [],
            "fallback": None,
        },
    }
    if safety is not None:
        out["safetyFlags"] = safety
    return out


def _prev_doc(streak: int, *, motion_id: str = "power-spin") -> dict:
    return {
        "result": {
            "mission": {
                "faultKey": _FAULT_KEY,
                "criterion": "leg_extension",
                "ruleId": "leg_extension_over_tol_linear",
                "recordId": "r00:leg_extension",
                "selectedBy": "repeat" if streak > 1 else "max_deduction",
                "streak": streak,
                "isSafety": False,
                "escalation": "none",
                "motionId": motion_id,
                "baselinePoints": 22.8,
                "baselineDeviation": 39.0,
                "targetValue": 180.0,
                "unit": "deg",
            }
        }
    }


def _emit(papp, result, *, mode="mode1", motion_id="power-spin", prev=None):
    papp._attach_translation_emission(
        result,
        mode=mode,
        motion_id=motion_id,
        prev_doc=prev,
        uid="u-test",
        analysis_id="a-test",
    )
    return result


# ─────────────────────── Test 1 — LLM 없이 3단 골격 성립 (D-11) ───────────────────────


def test_skeleton_without_llm_matches_phrasebook_verbatim(papp):
    """무키 환경 — record 3단이 phrasebook.json 골격 **그대로** (가공/생성 0)."""
    result = _emit(papp, _result([_leg_record()]))
    rec = result["deductionBreakdown"]["records"][0]

    fixture = json.loads((_BACKEND / "data" / "phrasebook.json").read_text("utf-8"))
    entry = fixture["entries"]["__common__.leg_extension"]
    assert rec["statusLine"] == entry["statusLine"]
    assert rec["whyLine"] == entry["whyLine"]
    assert rec["cueLine"] == entry["cueLine"]
    assert rec["coachQuestion"] == entry["coachQuestion"]
    assert rec["exerciseId"] == entry["exerciseId"]
    # recordId 각인 형식 + tolerance = 실존 규칙 상수 (ipsf 20°) — 자의 수치 0.
    assert rec["recordId"] == "r00:leg_extension"
    assert rec["tolerance"] == 20.0
    # 기존 키 무변경 (채점 무접촉).
    assert rec["points"] == -22.8
    assert rec["deviation"] == 19.0


def test_fail_closed_criterion_omits_cue_and_exercise(papp):
    """미등재 criterion — cueLine/exerciseId 생략 (fail-closed, 일반론 fabrication 0).
    failClosed 마커는 record 계약(§12.3) 밖이라 미방출."""
    fallback_rec = {
        "criterion": "dimension_overall_fallback",
        "measuredValue": 70.0,
        "baselineValue": 100,
        "baselineKind": None,
        "deviation": 30.0,
        "ruleId": "quantification_unavailable_dimension_overall",
        "points": -30.0,
        "unit": "score_delta",
        "ipsfAnchor": "engineering_interpretation",
        "source": "geometry",
        "deviationSource": "dimension_overall",
    }
    result = _result([fallback_rec])
    result["deductionBreakdown"]["fallback"] = "quantification_unavailable"
    _emit(papp, result)
    rec = result["deductionBreakdown"]["records"][0]
    assert isinstance(rec.get("statusLine"), str) and rec["statusLine"]
    assert "cueLine" not in rec
    assert "exerciseId" not in rec
    assert "failClosed" not in rec
    assert "tolerance" not in rec  # CRITERION_GROUPS 미등재 — 자의 수치 생성 금지


# ─────────────────────── Test 2 — 안전 미션 + safety 질문 (D-14) ───────────────────────


def test_safety_mission_and_safety_question(papp):
    result = _emit(
        papp,
        _result([_leg_record()], safety=[{"flagType": "asymmetry", "severity": "warn"}]),
    )
    mission = result["mission"]
    assert mission["selectedBy"] == "safety"
    assert mission["isSafety"] is True
    assert mission["escalation"] == "none"  # D-14 — 안전은 에스컬레이션 제외
    assert mission["streak"] == 1  # D-14 — 게임·streak 제외 (고정)

    questions = result["coachQuestions"]
    safety_qs = [q for q in questions if q["source"] == "safety"]
    assert safety_qs, f"safety 질문 부재: {questions}"
    expected = phrasebook.assemble_safety_phrases("asymmetry")["coachQuestion"]
    assert safety_qs[0]["text"] == expected


# ─────────────────────── Test 3 — prev chain streak/에스컬레이션/리셋 ───────────────────────


def test_prev_chain_streak_increments_and_third_strike_escalates(papp):
    # 2회차 — streak 1 → 2, exercise_detour.
    r2 = _emit(papp, _result([_leg_record()]), mode="mode3", prev=_prev_doc(1))
    assert r2["mission"]["faultKey"] == _FAULT_KEY
    assert r2["mission"]["streak"] == 2
    assert r2["mission"]["escalation"] == "exercise_detour"
    assert not any(
        q["source"] == "mission_stuck" for q in r2.get("coachQuestions", [])
    )

    # 3회차 — streak 2 → 3, coach_card + mission_stuck 질문 (recordId 조인).
    r3 = _emit(papp, _result([_leg_record()]), mode="mode3", prev=_prev_doc(2))
    assert r3["mission"]["streak"] == 3
    assert r3["mission"]["escalation"] == "coach_card"
    stuck = [q for q in r3["coachQuestions"] if q["source"] == "mission_stuck"]
    assert stuck, f"mission_stuck 질문 부재: {r3['coachQuestions']}"
    assert stuck[0]["recordId"] == "r00:leg_extension"
    rec = r3["deductionBreakdown"]["records"][0]
    assert stuck[0]["text"] == rec["coachQuestion"]


def test_prev_chain_resets_on_motion_id_mismatch(papp):
    """prev.motionId 불일치 — 다른 동작 체인 오염 차단 (streak 1 리셋)."""
    result = _emit(
        papp,
        _result([_leg_record()]),
        mode="mode3",
        prev=_prev_doc(2, motion_id="climb"),
    )
    assert result["mission"]["streak"] == 1
    assert result["mission"]["selectedBy"] == "max_deduction"


# ─────────────────────── Test 4 — summaryPraise 수치 분리 (D-09/D-26) ───────────────────────


def test_summary_praise_mission_improved_headline_numberless(papp):
    """prev 미션 faultKey 소멸 → improved outcome → praise 헤드라인 무수치."""
    result = _emit(
        papp,
        _result([_shoulder_record()]),  # leg_extension 소멸 — 개선
        mode="mode3",
        prev=_prev_doc(1),
    )
    outcome = result["missionOutcome"]
    assert outcome["improved"] is True
    assert outcome["deltaPoints"] == pytest.approx(22.8)

    praise = result["summaryPraise"]
    assert praise["source"] == "mission_improved"
    assert not re.search(r"[0-9]", praise["headline"]), praise["headline"]
    assert "%" not in praise["headline"]
    assert praise["evidenceValue"] == pytest.approx(22.8)
    assert praise["evidenceUnit"] == "points"


def test_mission_outcome_omitted_for_mode1(papp):
    """missionOutcome 은 mode3 전용 — mode1 은 키 자체 생략."""
    result = _emit(papp, _result([_leg_record()]), mode="mode1", prev=_prev_doc(1))
    assert "missionOutcome" not in result


# ─────────────────────── Test 5 — record 단위 격리 (리뷰 반영) ───────────────────────


def test_single_record_assembly_failure_is_isolated(papp, monkeypatch):
    """한 record 조립 예외 — 그 record 만 문구 없이, 나머지·미션·praise 잔존."""
    real = phrasebook.assemble_phrases

    def _boom(motion_key, criterion, rule_id=None):
        if criterion == "leg_extension":
            raise RuntimeError("주입 예외 (테스트)")
        return real(motion_key, criterion, rule_id)

    monkeypatch.setattr(
        "sunity_shared.analysis.phrasebook.assemble_phrases", _boom
    )
    result = _emit(papp, _result([_leg_record(), _shoulder_record()]), mode="mode3")

    rec0, rec1 = result["deductionBreakdown"]["records"]
    assert "statusLine" not in rec0  # 실패 record — 문구 없이 통과
    assert rec0["recordId"] == "r00:leg_extension"  # 각인은 문구 실패와 독립
    assert isinstance(rec1.get("statusLine"), str) and rec1["statusLine"]  # 잔존
    assert result.get("mission") is not None  # 미션 잔존
    assert result.get("summaryPraise") is not None  # praise 잔존 (stability clean)


def test_total_emission_failure_keeps_result_intact(papp, monkeypatch):
    """방출 전체 실패(상위 try) — result 기존 키 원형 유지, 분석 완주 (SP-3)."""
    monkeypatch.setattr(
        "sunity_shared.analysis.mission.select_mission",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("주입 예외")),
    )
    result = _result([_leg_record()])
    before = copy.deepcopy(result["deductionBreakdown"]["records"][0])
    _emit(papp, result)  # raise 없이 반환해야 함
    assert "mission" not in result
    # 문구 병합은 미션 실패와 독립으로 성립 (항목 격리).
    assert result["deductionBreakdown"]["records"][0]["statusLine"]
    assert result["deductionBreakdown"]["records"][0]["points"] == before["points"]


# ─────────────────────── Test 6 — scoped validator + fake_firestore 저장 ───────────────────────


def _load_phase31_conftest():
    name = "phase31_conftest_for_emission"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _PHASE31 / "conftest.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_emission_passes_scoped_validators_and_persists(papp, monkeypatch):
    """complete_analysis (32-06 validator 4종 포함) 가 방출 전체를 예외 없이 저장."""
    fake_mod = _load_phase31_conftest()
    db = fake_mod.FakeFirestore()
    monkeypatch.setattr(firestore_admin, "_doc", db.doc, raising=True)

    result = _emit(
        papp,
        _result(
            [_leg_record(), _shoulder_record()],
            safety=[{"flagType": "trunk_hyperextension", "severity": "warn"}],
        ),
        mode="mode3",
        prev=_prev_doc(2),
    )
    firestore_admin.complete_analysis("u-test", "a-test", result)

    stored = db.store["users/u-test/analyses/a-test"]
    assert stored["status"] == models.STATUS_DONE
    saved = stored["result"]
    assert saved["mission"]["selectedBy"] == "safety"  # 안전 > repeat (D-19 ①)
    outcome = saved["missionOutcome"]
    assert outcome["faultKey"] == _FAULT_KEY
    assert outcome["improved"] is False  # leg 결함 잔존 — 개선 아님 (D-06 정직)
    assert outcome["deltaPoints"] == pytest.approx(0.0)
    # 개선 없음 → 폴백 = 감점 0 차원 (stability) 칭찬 (D-26 폴백 사다리).
    assert saved["summaryPraise"]["source"] == "clean_dimension"
    assert {q["source"] for q in saved["coachQuestions"]} >= {"safety"}
    records = saved["deductionBreakdown"]["records"]
    assert all(r.get("recordId") for r in records)
    assert all(isinstance(r.get("statusLine"), str) for r in records)


# ─────────────────────── coach_writer 가변부 한정 (Task 2 본체, D-11) ───────────────────────


def test_coach_writer_system_prompt_declares_slot_limit():
    """시스템 프롬프트에 가변부 슬롯 한정 + 일반론 생성 금지 명문화 (acceptance grep)."""
    from sunity_shared.analysis import coach_writer

    system = coach_writer._SYSTEM
    assert "가변부" in system, "슬롯 한정 조항 부재"
    assert "일반론" in system, "일반론 금지 조항 부재"
    assert "문구집" in system, "문구집 골격 소유 명시 부재"


def test_coach_writer_runtime_filter_references_forbidden_constants():
    """LLM 출력 런타임 금지어 필터 존재 — FORBIDDEN 상수 참조 (acceptance grep ≥ 1)."""
    from sunity_shared.analysis import coach_writer

    source = Path(coach_writer.__file__).read_text(encoding="utf-8")
    assert "FORBIDDEN_PHRASES_PHRASEBOOK" in source
    assert "FORBIDDEN_REGEX_PHRASEBOOK" in source


class _StubCerebrasClient:
    """chat.completions.create 스텁 — 주입 JSON 을 그대로 응답."""

    def __init__(self, payload: dict) -> None:
        message = types.SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))
        choice = types.SimpleNamespace(message=message)
        resp = types.SimpleNamespace(choices=[choice])
        completions = types.SimpleNamespace(create=lambda **kw: resp)
        self.chat = types.SimpleNamespace(completions=completions)


def test_coach_writer_discards_forbidden_output_entry():
    """금지어 포함 entry 폐기(→골격/수치 폴백), 정상 entry 는 통과 (사후 필터)."""
    from sunity_shared.analysis import coach_writer

    writer = coach_writer.CerebrasCoachWriter()
    writer._client = _StubCerebrasClient({
        "left_knee": {"detail": "기준과 90% 유사도로 거의 같아요"},  # 금지 (regex+리터럴)
        "right_knee": {"detail": "발끝으로 천장을 밀어내듯 뻗어보세요"},  # 정상
    })
    out = writer.write({"mode": "mode1", "joints": [
        {"key": "left_knee", "labelKo": "왼쪽 무릎", "deviation_deg": 30.0},
        {"key": "right_knee", "labelKo": "오른쪽 무릎", "deviation_deg": 25.0},
    ]})
    assert "left_knee" not in out, f"금지어 entry 미폐기: {out}"
    assert out.get("right_knee", {}).get("detail") == "발끝으로 천장을 밀어내듯 뻗어보세요"


def test_coach_writer_no_key_returns_empty_skeleton_survives():
    """무키 환경 — write() {} (골격은 phrasebook 소유라 3단 성립, D-11 graceful)."""
    from sunity_shared.analysis import coach_writer

    writer = coach_writer.CerebrasCoachWriter()
    assert writer._client is None
    assert writer.write({"joints": [{"key": "left_knee", "deviation_deg": 30.0}]}) == {}
