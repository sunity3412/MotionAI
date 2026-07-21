"""Plan 32-05 Task 2 — phrasebook 조립 순수 함수 검증 (assembly).

assemble_phrases / assemble_safety_phrases 의 매칭 우선순위(동작×criterion →
criterion 공통 → fail-closed) + fail-closed 폴백(cueLine/exerciseId 생성 0) +
flat scalar(Firestore nested-array 금지) + graceful 를 박제한다.

순수 함수만 — boto3/네트워크 무접촉 (conftest sys.path 주입).
per 32-05-PLAN behavior Test 1~4.
"""

from __future__ import annotations

from sunity_shared.analysis import phrasebook


def _is_flat_scalar_dict(d: dict) -> bool:
    """반환 dict 가 flat scalar 인지 (nested list/dict 0 — Firestore flat 저장 가능)."""
    if not isinstance(d, dict):
        return False
    return all(v is None or isinstance(v, (str, int, float, bool)) for v in d.values())


# ── Test (assembly) 1 — 등록 동작 + 전용/공통 entry 존재 criterion → 슬롯 dict ──
def test_registered_motion_common_entry_returns_slot_dict() -> None:
    slots = phrasebook.assemble_phrases("ref-kip-up", "leg_extension", None)
    assert isinstance(slots, dict)
    # 전용 또는 공통 entry 히트 — 6 슬롯 전부 존재 + exerciseId 포함.
    for key in ("statusLine", "whyLine", "cueLine", "coachQuestion", "exerciseId", "exerciseReason"):
        assert key in slots, f"leg_extension 슬롯 {key} 누락"
        assert isinstance(slots[key], str) and slots[key], f"{key} 가 비었거나 문자열 아님"
    # exerciseId 는 corrective_exercises defect 키 (fabrication 0).
    assert slots["exerciseId"] == "legs_not_extended"
    # fail-closed 마커 없음 (정상 히트).
    assert not slots.get("failClosed")


def test_angle_vs_reference_per_joint_entry() -> None:
    """quick-260626-jwu per-joint reference_relative criterion 도 공통 entry 히트."""
    slots = phrasebook.assemble_phrases(None, "angle_vs_reference__right_knee")
    assert slots.get("statusLine") and slots.get("cueLine")
    assert slots["exerciseId"] == "legs_not_extended"
    assert not slots.get("failClosed")


# ── Test (assembly) 2 — 미등재 동작/criterion → fail-closed (cueLine 부재) ──
def test_unknown_criterion_fails_closed_no_cue() -> None:
    slots = phrasebook.assemble_phrases("ref-kip-up", "this_criterion_does_not_exist")
    assert isinstance(slots, dict)
    # fail-closed: cueLine/exerciseId/exerciseReason 생성 안 함 (일반론 조언 차단).
    assert "cueLine" not in slots, "fail-closed 인데 cueLine 생성됨 (일반론 유입)"
    assert "exerciseId" not in slots
    assert "exerciseReason" not in slots
    assert slots.get("failClosed") is True
    # coachQuestion 은 강사 확인 유도문.
    assert slots.get("coachQuestion") and "강사" in slots["coachQuestion"]
    assert slots.get("statusLine") and slots.get("whyLine")


def test_dimension_overall_fallback_is_fail_closed() -> None:
    """엔진 폴백 criterion(관절 국소화 실패)은 특정 행동 큐를 짓지 않는다."""
    slots = phrasebook.assemble_phrases("ref-power-spin", "dimension_overall_fallback")
    assert slots.get("failClosed") is True
    assert "cueLine" not in slots
    assert "exerciseId" not in slots


def test_unregistered_motion_still_gets_common_phrasing() -> None:
    """미등재 동작이라도 criterion 공통 entry 로 phrasing 이 비지 않는다."""
    slots = phrasebook.assemble_phrases("어떤_미등재_동작", "split_angle")
    assert not slots.get("failClosed")
    assert slots.get("cueLine") and slots.get("exerciseId") == "hip_hamstring_tight"


def test_none_motion_key_graceful() -> None:
    """motion_key=None (인식 실패) 도 크래시 없이 공통 경로."""
    slots = phrasebook.assemble_phrases(None, "line")
    assert slots.get("statusLine")
    assert not slots.get("failClosed")


# ── Test (assembly) 3 — 반환 dict flat scalar (nested array/dict 0) ──
def test_returned_dict_is_flat_scalar() -> None:
    hit = phrasebook.assemble_phrases("ref-kip-up", "arm_extension")
    fc = phrasebook.assemble_phrases("ref-kip-up", "nonexistent")
    safety = phrasebook.assemble_safety_phrases("asymmetry")
    for d in (hit, fc, safety):
        assert _is_flat_scalar_dict(d), f"nested 값 발견: {d}"


# ── Test (assembly) 4 — safetyEntries 조회 (cueLine·게임 키 없음, D-14) ──
def test_safety_phrases_no_cue_no_game() -> None:
    for flag in ("asymmetry", "trunk_hyperextension", "joint_hyperextension", "level_mismatch"):
        slots = phrasebook.assemble_safety_phrases(flag)
        assert isinstance(slots, dict)
        assert slots.get("statusLine") and slots.get("whyLine") and slots.get("coachQuestion")
        # D-14: cueLine·게임 요소 없음 (차분한 안전 톤).
        assert "cueLine" not in slots, f"{flag}: 안전 entry 에 행동 큐 생성됨 (D-14 위반)"
        assert "exerciseId" not in slots
        assert "mission" not in slots and "gauge" not in slots
        # 강사와 함께 확인 유도 (D-14).
        assert "강사" in slots["coachQuestion"]


def test_unknown_safety_flag_generic_no_advice() -> None:
    """미등재 safety 유형 → generic 안전 유도문 (조언 생성 0, 크래시 0)."""
    slots = phrasebook.assemble_safety_phrases("some_unknown_flag")
    assert isinstance(slots, dict)
    assert "cueLine" not in slots
    assert slots.get("coachQuestion") and "강사" in slots["coachQuestion"]


def test_load_terminology_map_helper() -> None:
    """phrasebook.py 가 용어 맵 로드 헬퍼를 제공 (whyLine 심사 용어 참조용)."""
    tmap = phrasebook.load_terminology_map()
    assert isinstance(tmap, dict)
    terms = tmap.get("terms", tmap)
    assert "stability" in terms and "angle" in terms and "line" in terms
