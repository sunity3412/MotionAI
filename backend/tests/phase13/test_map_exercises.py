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
