"""map_exercises 순수 매핑 함수 단위 테스트 (Plan 13-A Task 2 / criteria 2,3).

<behavior> 6 항목 미러:
  1. late_contact finding + painArea ["wrist"] → grip_weak 운동 + wrist painArea 운동 포함.
  2. 출력 길이는 항상 3~5 cap, 중복(name) 제거.
  3. painArea avoid 안전 라인 우선 정렬.
  4. force_pattern_inference=None + pain_areas=[] → 빈 list (크래시 X).
  5. motion_id=None → generic 결함 운동만 (graceful).
  6. 반환 dict 항목 = plain camelCase scalar (name/setsReps/purpose/sourceRef).
"""

from __future__ import annotations

from sunity_shared.analysis.exercise_map import map_exercises

from .conftest import load_phase13_fixture

_SCALAR_FIELDS = {"name", "setsReps", "purpose", "sourceRef"}


def _sample_inference() -> dict:
    return load_phase13_fixture("sample_force_pattern_inference.json")


def test_late_contact_plus_wrist_includes_grip_and_wrist_exercises() -> None:
    # sample fixture 에는 late_contact (grip_weak) + axis_tilt (core_weak) finding.
    result = map_exercises(_sample_inference(), pain_areas=["wrist"], motion_id=None)
    names = {ex["name"] for ex in result}
    # grip_weak 운동 (Farmer's Walk 등) 또는 wrist painArea 운동이 포함.
    assert any(n in names for n in {"Farmer's Walk", "Hand Grippers", "Deadlift"})


def test_output_capped_3_to_5_and_deduped() -> None:
    # 모든 신호 + 모든 painArea → union 폭발 → 3~5 cap + dedup.
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
    assert 3 <= len(result) <= 5
    names = [ex["name"] for ex in result]
    assert len(names) == len(set(names)), "중복 name 미제거"


def test_pain_area_avoid_exercise_prioritized() -> None:
    # painArea 가 있으면 안전(painArea) 운동이 앞쪽에 정렬됨.
    result = map_exercises(
        _sample_inference(), pain_areas=["wrist"], motion_id=None
    )
    assert len(result) >= 1
    # 첫 항목이 wrist painArea 운동 (Farmer's Walk / Hand Grippers).
    assert result[0]["name"] in {"Farmer's Walk", "Hand Grippers"}


def test_none_inference_and_empty_pain_areas_returns_empty() -> None:
    assert map_exercises(None, pain_areas=[], motion_id=None) == []


def test_motion_id_none_is_graceful() -> None:
    result = map_exercises(_sample_inference(), pain_areas=[], motion_id=None)
    assert isinstance(result, list)
    assert 0 <= len(result) <= 5


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
_GRIP_EXERCISES = {"Farmer's Walk", "Hand Grippers", "Assisted Pull-ups", "Dead Hang", "Deadlift"}
_LEG_HIP_SHOULDER_EXERCISES = {
    # hip_hamstring_tight
    "Hamstring Stretch", "Hip Flexor Stretch", "Quad Stretch", "Dynamic Leg Swings", "PNF Stretch",
    # legs_not_extended
    "Squats", "Lunges", "Calf Raises", "High Kick", "Lateral Leg Raise",
    # shoulder_unstable
    "Push-ups", "Overhead Press", "Scapular Depression Drills", "Arm Circles", "Cross-Shoulder Stretch",
}


def _grip_trigger_inference() -> dict:
    """late_contact → grip_weak 트리거 findings (kip-up 미스매치 재현 입력)."""
    return {"findings": [{"sourceSignal": "late_contact", "jointHint": "손목"}]}


def test_kipup_fault_sets_prioritize_defect_body_parts_over_grip() -> None:
    """kip-up 시나리오: leg+shoulder 결함 + grip 트리거 findings 동시 입력 →
    결함 부위(다리/고관절/어깨) 운동이 앞순위, grip 운동이 결함 부위 운동보다 앞서지 않음."""
    result = map_exercises(
        _grip_trigger_inference(),
        pain_areas=[],
        motion_id=None,
        fault_keypoint_sets=["leg", "shoulder"],
    )
    assert len(result) >= 3
    names = [ex["name"] for ex in result]
    # 앞순위 = 결함 부위 운동 (hip_hamstring_tight 가 leg 1순위 — 스플릿=고관절 유연성).
    assert names[0] in _LEG_HIP_SHOULDER_EXERCISES
    # grip 운동이 결함 부위 운동보다 앞서지 않는다.
    first_defect_idx = min(
        i for i, n in enumerate(names) if n in _LEG_HIP_SHOULDER_EXERCISES
    )
    grip_indices = [i for i, n in enumerate(names) if n in _GRIP_EXERCISES]
    for gi in grip_indices:
        assert gi > first_defect_idx, f"grip 운동 {names[gi]} 이 결함 부위 운동보다 앞섬"


def test_fault_keypoint_sets_none_is_byte_identical() -> None:
    """fault_keypoint_sets=None (default) → 기존 결과와 동일 (회귀 가드)."""
    base = map_exercises(_sample_inference(), pain_areas=["wrist"], motion_id=None)
    explicit = map_exercises(
        _sample_inference(), pain_areas=["wrist"], motion_id=None,
        fault_keypoint_sets=None,
    )
    assert base == explicit


def test_pain_area_still_first_with_fault_keypoint_sets() -> None:
    """painArea 안전 운동은 fault 매핑보다 여전히 최우선."""
    result = map_exercises(
        _grip_trigger_inference(),
        pain_areas=["wrist"],
        motion_id=None,
        fault_keypoint_sets=["leg"],
    )
    assert result[0]["name"] in {"Farmer's Walk", "Hand Grippers"}


def test_fault_keypoint_sets_dedup_and_cap() -> None:
    """중복 keypoint_set + findings 폭발 입력 → dedup + cap(≤5) 불변."""
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
    assert 3 <= len(result) <= 5
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
        "Hamstring Stretch", "Hip Flexor Stretch", "Quad Stretch",
        "Dynamic Leg Swings", "PNF Stretch",
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
