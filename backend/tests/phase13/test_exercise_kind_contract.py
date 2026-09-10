"""quick-260910-vwh Task 2 — 운동 성격(kind) 계약.

belle 2026-09-10: "스트레칭 뿐만 아니라 근력을 키우는 헬스도 있을거고 다양하게
구성하여 분석에 따라 배전해주면 좋을거 같은데?"

여기서 지키는 것 셋:
  1. fixture 43행 전부 kind 를 갖고, 값은 models.EXERCISE_KINDS 안이다.
  2. 같은 운동(이름)은 어느 그룹에 있든 같은 kind 다 — 다르면 화면에서 같은 운동이
     그룹마다 다른 성격으로 보인다.
  3. map_exercises 산출 dict 키가 계약(RECOMMENDED_EXERCISE_KEYS)과 정확히 같다.

그리고 **하지 않는 것**도 박제한다 (belle 이 명시적으로 기각한 설계):
  "균형 잡히게 섞는거 물론 좋지. 근데 그게 규칙이 될 필요는 없어 … 근력이 충분한데
  뭐하러 헬스를 하겠어." → 성격으로 개수를 맞추지 않는다.
"""

from __future__ import annotations

import json

from sunity_shared import models
from sunity_shared.analysis import exercise_map


def _all_fixture_exercises() -> list[tuple[str, dict]]:
    library = json.loads(
        exercise_map._CORRECTIVE_EXERCISES_PATH.read_text(encoding="utf-8")
    )
    rows: list[tuple[str, dict]] = []
    for key, defect in library["defects"].items():
        rows += [(f"defects.{key}", ex) for ex in defect["exercises"]]
    for key, area in library["painAreas"].items():
        rows += [(f"painAreas.{key}", ex) for ex in area["exercises"]]
    return rows


def test_every_fixture_exercise_has_valid_kind() -> None:
    rows = _all_fixture_exercises()
    assert rows, "fixture 가 비었다"
    for group, ex in rows:
        assert "kind" in ex, f"{group} / {ex['name']} 에 kind 없음"
        assert ex["kind"] in models.EXERCISE_KINDS, (
            f"{group} / {ex['name']} kind={ex['kind']!r} 는 계약 밖"
        )


def test_same_exercise_has_same_kind_in_every_group() -> None:
    """스쿼트는 3그룹에 있다 — 어디서 보든 '근력'이어야 한다."""
    by_name: dict[str, set[str]] = {}
    for _group, ex in _all_fixture_exercises():
        by_name.setdefault(ex["name"], set()).add(ex["kind"])
    drift = {n: k for n, k in by_name.items() if len(k) != 1}
    assert not drift, f"같은 운동인데 그룹마다 kind 가 다름: {drift}"


def test_kind_reaches_map_exercises_output() -> None:
    """fixture 의 kind 가 앱까지 가는 dict 에 실린다."""
    result = exercise_map.map_exercises(
        None, pain_areas=["knee"], motion_id=None
    )
    assert result, "무릎 통증 → 운동이 나와야 한다"
    for ex in result:
        assert ex["kind"] in models.EXERCISE_KINDS


def test_output_keys_lockstep_with_contract() -> None:
    """산출 dict 키 == RECOMMENDED_EXERCISE_KEYS (계약 3벌 drift 방지)."""
    result = exercise_map.map_exercises(
        None, pain_areas=["knee"], motion_id=None
    )
    for ex in result:
        assert set(ex) == set(models.RECOMMENDED_EXERCISE_KEYS)


def test_kind_does_not_force_a_mix() -> None:
    """★ belle 이 기각한 설계 — 성격으로 개수를 맞추지 않는다.

    유연성 결함만 걸린 입력에는 유연성 운동만 나와야 하고, "균형"을 맞추려고
    근력 운동이 끼어들면 안 된다. 근력이 충분한 사람에게 헬스를 처방하지 않는다.
    """
    result = exercise_map.map_exercises(
        None, pain_areas=[], motion_id=None, deduction_keypoint_sets=["hip"]
    )
    assert result, "고관절 감점 → 운동이 나와야 한다"
    # 감점 부위(hip)가 접히는 결함 그대로만 나온다 — 성격 균형을 맞추려는 추가 유입 0.
    names = [ex["name"] for ex in result]
    assert names == ["옆으로 다리 들기", "허벅지 뒤 스트레칭"], names
