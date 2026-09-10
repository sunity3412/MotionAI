"""map_exercises 순수 매핑 함수 단위 테스트 (Plan 13-A Task 2 / criteria 2,3).

<behavior> 6 항목 미러:
  1. late_contact finding + painArea ["wrist"] → grip_weak 운동 + wrist painArea 운동 포함.
  2. 출력 길이는 상한 cap 이하, 중복(name) 제거. **하한 없음** (quick-260910-pbs).
  3. painArea avoid 안전 라인 우선 정렬.
  4. force_pattern_inference=None + pain_areas=[] → 빈 list (크래시 X).
  5. motion_id=None → generic 결함 운동만 (graceful).
  6. 반환 dict 항목 = plain camelCase scalar (name/setsReps/purpose/sourceRef).
"""

from __future__ import annotations

from sunity_shared import models
from sunity_shared.analysis import exercise_map
from sunity_shared.analysis.exercise_map import _MAX_EXERCISES, map_exercises

from .conftest import load_phase13_fixture

_SCALAR_FIELDS = {"name", "setsReps", "purpose", "sourceRef"}


def _sample_inference() -> dict:
    return load_phase13_fixture("sample_force_pattern_inference.json")


def test_late_contact_plus_wrist_includes_grip_and_wrist_exercises() -> None:
    # sample fixture 에는 late_contact (grip_weak) + axis_tilt (core_weak) finding.
    result = map_exercises(_sample_inference(), pain_areas=["wrist"], motion_id=None)
    names = {ex["name"] for ex in result}
    # grip_weak 운동 (파머스 워크 등) 또는 wrist painArea 운동이 포함.
    assert any(n in names for n in {"파머스 워크", "악력기 운동", "데드리프트"})


def test_output_capped_and_deduped() -> None:
    # 모든 신호 + 모든 painArea → union 폭발 → 상한 cap + dedup.
    big_inference = {
        "findings": [
            {"sourceSignal": "late_contact", "jointHint": "손목"},
            {"sourceSignal": "axis_tilt", "jointHint": "코어"},
            {"sourceSignal": "high_jitter", "jointHint": "어깨"},
        ]
    }
    result = map_exercises(
        big_inference, pain_areas=["wrist", "shoulder", "lower_back"], motion_id=None
    )
    assert 0 < len(result) <= _MAX_EXERCISES
    names = [ex["name"] for ex in result]
    assert len(names) == len(set(names)), "중복 name 미제거"


def test_pain_area_avoid_exercise_prioritized() -> None:
    # painArea 가 있으면 안전(painArea) 운동이 앞쪽에 정렬됨.
    result = map_exercises(
        _sample_inference(), pain_areas=["wrist"], motion_id=None
    )
    assert len(result) >= 1
    # 첫 항목이 wrist painArea 운동 (파머스 워크 / 악력기 운동).
    assert result[0]["name"] in {"파머스 워크", "악력기 운동"}


def test_none_inference_and_empty_pain_areas_returns_empty() -> None:
    assert map_exercises(None, pain_areas=[], motion_id=None) == []


def test_motion_id_none_is_graceful() -> None:
    result = map_exercises(_sample_inference(), pain_areas=[], motion_id=None)
    assert isinstance(result, list)
    assert 0 <= len(result) <= _MAX_EXERCISES


def test_returned_items_are_plain_camel_case_scalar_dicts() -> None:
    result = map_exercises(_sample_inference(), pain_areas=["wrist"], motion_id=None)
    assert len(result) >= 1
    for ex in result:
        assert isinstance(ex, dict)
        assert _SCALAR_FIELDS <= set(ex.keys())
        for v in ex.values():
            assert isinstance(v, (str, type(None))), "scalar only (no nested)"


# ── quick-260704-fwb — vision veto 결함 부위(fault_keypoint_sets) 매칭 ──────────

# fixture lockstep: corrective_exercises.json defect별 운동 이름 (grep 게이트 아님 —
# 순서 검증용 소속 판정에만 사용).
_GRIP_EXERCISES = {"파머스 워크", "악력기 운동", "밴드 턱걸이", "철봉 매달리기", "데드리프트"}
_LEG_HIP_SHOULDER_EXERCISES = {
    # hip_hamstring_tight
    "허벅지 뒤 스트레칭", "골반 앞 스트레칭", "허벅지 앞 스트레칭", "앞뒤로 다리 흔들기", "파트너 스트레칭",
    # legs_not_extended
    "스쿼트", "런지", "까치발 들기", "다리 차올리기", "옆으로 다리 들기",
    # shoulder_unstable
    "팔굽혀펴기", "어깨 위로 밀기", "매달려 어깨 내리기", "팔 돌리기", "어깨 뒤 스트레칭",
}


def _grip_trigger_inference() -> dict:
    """late_contact → grip_weak 트리거 findings (kip-up 미스매치 재현 입력)."""
    return {"findings": [{"sourceSignal": "late_contact", "jointHint": "손목"}]}


def test_kipup_fault_sets_prioritize_defect_body_parts_over_grip() -> None:
    """kip-up 시나리오: leg+shoulder 결함 + grip 트리거 findings 동시 입력 →
    결함 부위(다리/고관절/어깨) 운동이 **목록 선두** (pod 검증 fix — defect 당
    _EXERCISES_PER_DEFECT 개), grip 운동은 결함 부위 운동보다 앞서지 않음."""
    result = map_exercises(
        _grip_trigger_inference(),
        pain_areas=[],
        motion_id=None,
        fault_keypoint_sets=["leg", "shoulder"],
    )
    names = [ex["name"] for ex in result]
    # 정확한 선두 순서 (quick-260910-vwh Task 3 — **부위 단위** 라운드로빈):
    #   1라운드 = 부위마다 대표 하나씩 → leg(허벅지 뒤 스트레칭) · shoulder(팔굽혀펴기)
    #   2라운드 = 남은 자리를 앞 부위부터 → leg 의 두 번째(스쿼트)
    # 종전엔 defect 단위라 leg 하나가 2연속(허벅지 뒤 스트레칭·스쿼트)으로 앞을 먹고
    # shoulder 대표가 3번째로 밀렸다. 결과 카드는 3행만 보이므로 그게 곧 부위 소실이다.
    # 마지막 파머스 워크 는 findings(late_contact→grip_weak) 유래 — 종전엔 cap 에
    # 밀려 사라졌으나 백필 폐지로 자리가 남아 살아남는다 (quick-260910-pbs).
    assert names == [
        "허벅지 뒤 스트레칭",
        "팔굽혀펴기",
        "스쿼트",
        "파머스 워크",
    ]
    # grip 운동이 결함 부위 운동보다 앞서지 않는다.
    first_defect_idx = min(
        i for i, n in enumerate(names) if n in _LEG_HIP_SHOULDER_EXERCISES
    )
    grip_indices = [i for i, n in enumerate(names) if n in _GRIP_EXERCISES]
    for gi in grip_indices:
        assert gi > first_defect_idx, f"grip 운동 {names[gi]} 이 결함 부위 운동보다 앞섬"


def test_pod_repro_pain_wrist_fault_leg_defect_leads_grip_rear() -> None:
    """pod 재분석 재현 (2026-07-04): painArea wrist(파머스 워크/악력기 운동) 안전
    운동이 fault 유래 스트레칭보다 선두라 '결함과 무관한 운동이 대표' 로 보였음 →
    fix 후 확정 결함(leg) 운동이 선두, grip 계열은 제거되지 않고 후순위 유지."""
    result = map_exercises(
        None,
        pain_areas=["wrist"],
        motion_id=None,
        fault_keypoint_sets=["leg"],
    )
    names = [ex["name"] for ex in result]
    assert names == [
        "허벅지 뒤 스트레칭",
        "스쿼트",
        "파머스 워크",
        "악력기 운동",
    ]


def test_fault_keypoint_sets_none_is_byte_identical() -> None:
    """fault_keypoint_sets=None (default) → 기존 결과와 동일 (회귀 가드)."""
    base = map_exercises(_sample_inference(), pain_areas=["wrist"], motion_id=None)
    explicit = map_exercises(
        _sample_inference(), pain_areas=["wrist"], motion_id=None,
        fault_keypoint_sets=None,
    )
    assert base == explicit


def test_pain_area_first_only_without_fault_keypoint_sets() -> None:
    """painArea 최우선은 fault 부재(None 경로)에서만 유지 — fault 있으면 확정 결함
    운동이 선두 (pod 검증 fix). painArea 운동은 제거되지 않고 후순위 잔존."""
    base = map_exercises(
        _grip_trigger_inference(), pain_areas=["wrist"], motion_id=None
    )
    assert base[0]["name"] in {"파머스 워크", "악력기 운동"}

    with_fault = map_exercises(
        _grip_trigger_inference(),
        pain_areas=["wrist"],
        motion_id=None,
        fault_keypoint_sets=["leg"],
    )
    names = [ex["name"] for ex in with_fault]
    assert names[0] in {"허벅지 뒤 스트레칭", "골반 앞 스트레칭"}
    # painArea(grip 계열) 운동 잔존 — 후순위 (제거 아님).
    assert any(n in {"파머스 워크", "악력기 운동"} for n in names)


def test_fault_keypoint_sets_dedup_and_cap() -> None:
    """중복 keypoint_set + findings 폭발 입력 → dedup + 상한 cap 불변."""
    result = map_exercises(
        {
            "findings": [
                {"sourceSignal": "late_contact", "jointHint": "손목"},
                {"sourceSignal": "axis_tilt", "jointHint": "코어"},
            ]
        },
        pain_areas=[],
        motion_id=None,
        fault_keypoint_sets=["leg", "leg", "hip", "shoulder", "torso"],
    )
    assert 0 < len(result) <= _MAX_EXERCISES
    names = [ex["name"] for ex in result]
    assert len(names) == len(set(names)), "중복 name 미제거"


def test_unknown_keypoint_set_is_graceful() -> None:
    """미지 keypoint_set 값 → 조용히 skip (크래시 0, 유효분만 매칭)."""
    result = map_exercises(
        None,
        pain_areas=[],
        motion_id=None,
        fault_keypoint_sets=["wing", "", "leg"],
    )
    assert len(result) >= 1
    assert result[0]["name"] in {
        "허벅지 뒤 스트레칭", "골반 앞 스트레칭", "허벅지 앞 스트레칭",
        "앞뒤로 다리 흔들기", "파트너 스트레칭",
    }


def test_fault_keypoint_sets_output_shape_unchanged() -> None:
    """출력 형상 {name,setsReps,purpose,sourceRef} 불변 (recommendedExercises 계약 0 변경)."""
    result = map_exercises(
        None, pain_areas=[], motion_id=None, fault_keypoint_sets=["shoulder"]
    )
    assert len(result) >= 1
    for ex in result:
        assert _SCALAR_FIELDS <= set(ex.keys())
        for v in ex.values():
            assert isinstance(v, (str, type(None))), "scalar only (no nested)"


# ── quick-260910-pbs — 개수는 분석이 정한다 (백필 폐지 / 결함당 대표 1개) ─────────
#
# belle 2026-09-10: "1개 필요하면 진짜 1개만, 3개 필요하면 3개, 진짜로 분석별로".
# 착수 전 실측: 저장된 doc 4건(감점 1~6건)이 **전부 5개**였다 — 개수가 분석과 무관.


def test_single_defect_yields_single_exercise() -> None:
    """결함 1개 → 운동 1개. 종전엔 그 defect 의 fixture 5개가 상한을 채웠다."""
    result = map_exercises(
        None, pain_areas=[], motion_id=None, fault_keypoint_sets=["shoulder"]
    )
    assert [ex["name"] for ex in result] == ["팔굽혀펴기"]


def test_no_backfill_from_matched_defect_group() -> None:
    """매칭된 defect 그룹의 나머지 운동으로 빈자리를 채우지 않는다 (백필 폐지).

    shoulder_unstable fixture 는 5개지만 대표 1개만 나와야 한다.
    """
    result = map_exercises(
        None, pain_areas=[], motion_id=None, fault_keypoint_sets=["shoulder"]
    )
    names = {ex["name"] for ex in result}
    assert not (
        names
        & {"어깨 위로 밀기", "매달려 어깨 내리기", "팔 돌리기",
           "어깨 뒤 스트레칭"}
    ), "백필이 살아 있다 — 같은 defect 그룹의 후순위 운동이 유입됨"


def test_exercise_count_tracks_defect_count() -> None:
    """결함 부위가 늘면 운동도 늘고, 줄면 준다 — 개수가 분석을 따라간다."""
    one = map_exercises(
        None, pain_areas=[], motion_id=None, fault_keypoint_sets=["shoulder"]
    )
    two = map_exercises(
        None, pain_areas=[], motion_id=None, fault_keypoint_sets=["shoulder", "grip"]
    )
    assert len(one) == 1
    assert len(two) == 2
    assert len(one) < len(two)


def test_findings_defect_obeys_same_per_defect_cap() -> None:
    """(3) findings 유래 defect 도 fault 경로와 같은 상한을 받는다.

    종전엔 여기만 슬라이스가 없어 defect 하나가 fixture 5개를 통째로 넣었다 —
    대표 doc c64afae6(감점 6건)이 어깨 운동 5개만 받은 실제 경로.
    """
    # late_contact 는 grip_weak + legs_not_extended 두 defect 를 트리거한다 →
    # defect 당 1개씩 = 2개. 각 그룹의 나머지 4개는 들어오지 않는다.
    result = map_exercises(
        _grip_trigger_inference(), pain_areas=[], motion_id=None
    )
    assert [ex["name"] for ex in result] == ["파머스 워크", "스쿼트"]
    names = {ex["name"] for ex in result}
    assert not (names & {"악력기 운동", "밴드 턱걸이", "철봉 매달리기",
                         "데드리프트", "런지", "까치발 들기"})


def test_no_minimum_floor_constant() -> None:
    """죽은 하한 상수 _MIN_EXERCISES 재도입 차단 — 하한은 존재하지 않는다."""
    assert not hasattr(exercise_map, "_MIN_EXERCISES")


def test_generation_cap_locksteps_with_storage_cap() -> None:
    """생성 상한 == 저장 거부선. 셋 중 둘이 어긋나면 유효 운동이 조용히 잘린다."""
    assert _MAX_EXERCISES == models.MAX_RECOMMENDED_EXERCISES == 5
