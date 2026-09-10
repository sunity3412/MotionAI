"""운동 식별자(id) 계약 게이트 (quick-260910-woq Task 3).

왜 있나 — 2026-09-10 에 운동 이름이 영문 → 한글로 바뀌자(quick-260910-vwh),
이름으로 라이브러리를 되짚던 앱 모달이 **개명 이전 모든 분석에서 빈 화면**이 됐다.
근본 원인은 이름이 표시 문자열과 조인 키를 겸한 것이다. id 를 도입해 갈랐으니,
id 가 그 역할을 못 하게 되는 상황들을 여기서 막는다.

여기서 지키는 것:
  1. fixture 43행 전부 id 보유, 형식은 스네이크 케이스(표시명 파생 금지).
  2. 축4 — 서로 다른 운동이 같은 id 를 쓰면 fail (같은 id -> 같은 이름).
  3. 축5 — 같은 운동은 어느 그룹에 있든 같은 id (같은 이름 -> 같은 id).
  4. map_exercises 가 id 를 함께 싣는다 (앱의 조인 키가 doc 까지 도달).
  5. dedup 이 **id 기준**이다 — 이름이 갈라져도 같은 운동은 한 번만 나간다.
  6. 라이브러리가 정합인 동안 id dedup 과 name dedup 의 결과가 같다 (무행동 회귀).
"""

from __future__ import annotations

import copy
import itertools
import json
import re

import pytest

from sunity_shared import models
from sunity_shared.analysis import exercise_map

_ID_PATTERN = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")

# 실측 (quick-260910-woq 착수 시점): 43행 / 유니크 id 28.
# 종전 29 에서 하나 준 것은 vwh 가 팔꿈치 통증 항목을 '어깨 위로 밀기'로 교체해
# 기존 운동과 합쳐졌기 때문이다. 숫자가 바뀌면 옛 이름 표(app/src/data/
# legacyExerciseNames.ts)도 함께 봐야 하므로 일부러 박아 둔다.
_EXPECTED_ROWS = 43
_EXPECTED_UNIQUE_IDS = 28


def _library() -> dict:
    return json.loads(
        exercise_map._CORRECTIVE_EXERCISES_PATH.read_text(encoding="utf-8")
    )


def _rows() -> list[tuple[str, dict]]:
    library = _library()
    rows: list[tuple[str, dict]] = []
    for key, defect in library["defects"].items():
        rows += [(f"defects.{key}", ex) for ex in defect["exercises"]]
    for key, area in library["painAreas"].items():
        rows += [(f"painAreas.{key}", ex) for ex in area["exercises"]]
    return rows


# ── 라이브러리 불변식 ────────────────────────────────────────────────────────


def test_every_exercise_has_snake_case_id() -> None:
    rows = _rows()
    assert len(rows) == _EXPECTED_ROWS, "라이브러리 행 수가 바뀌었다"
    for group, ex in rows:
        ex_id = ex.get("id")
        assert isinstance(ex_id, str) and ex_id, f"{group} / {ex['name']} 에 id 없음"
        # 한글 표시명에서 id 를 만들면 개명 때 같은 결함이 재발한다. ASCII 스네이크만.
        assert _ID_PATTERN.match(ex_id), f"{group} id 형식 위반: {ex_id!r}"


def test_unique_id_count_is_pinned() -> None:
    ids = {ex["id"] for _g, ex in _rows()}
    assert len(ids) == _EXPECTED_UNIQUE_IDS


def test_axis4_no_two_exercises_share_an_id() -> None:
    """축4 — 같은 id 인데 이름이 다르면 서로 다른 운동이 id 를 공유한 것이다."""
    names_by_id: dict[str, set[str]] = {}
    for _g, ex in _rows():
        names_by_id.setdefault(ex["id"], set()).add(ex["name"])
    collided = {i: n for i, n in names_by_id.items() if len(n) > 1}
    assert not collided, f"id 충돌: {collided}"


def test_axis5_same_exercise_has_same_id_in_every_group() -> None:
    """축5 — 스쿼트는 3그룹에 있다. 어디서 보든 같은 id 여야 한다."""
    ids_by_name: dict[str, set[str]] = {}
    groups_by_name: dict[str, list[str]] = {}
    for group, ex in _rows():
        ids_by_name.setdefault(ex["name"], set()).add(ex["id"])
        groups_by_name.setdefault(ex["name"], []).append(group)
    split = {n: i for n, i in ids_by_name.items() if len(i) > 1}
    assert not split, f"같은 이름인데 그룹마다 id 가 다름: {split}"
    # 여러 그룹에 실린 운동이 실제로 있어야 이 축이 사문이 아니다.
    assert len(groups_by_name["스쿼트"]) >= 3, groups_by_name["스쿼트"]
    assert len(groups_by_name["옆으로 다리 들기"]) >= 2


# ── 산출 계약 ────────────────────────────────────────────────────────────────


def test_id_reaches_map_exercises_output() -> None:
    """앱의 조인 키가 doc 까지 간다 — 이게 없으면 신 doc 도 이름 조인으로 되돌아간다."""
    result = exercise_map.map_exercises(None, pain_areas=["knee"], motion_id=None)
    assert result, "무릎 통증 → 운동이 나와야 한다"
    library_ids = {ex["id"] for _g, ex in _rows()}
    for ex in result:
        assert isinstance(ex.get("id"), str) and ex["id"], f"id 누락: {ex}"
        assert ex["id"] in library_ids, f"라이브러리에 없는 id: {ex['id']}"
    assert set(result[0]) == set(models.RECOMMENDED_EXERCISE_KEYS)


@pytest.fixture
def _renamed_library(monkeypatch) -> dict:
    """같은 id 를 가진 항목의 **이름만** 그룹마다 다르게 만든 라이브러리.

    개명이 그룹별로 어긋나게 반영된 상황을 흉내낸다. dedup 이 이름 기준이면 같은
    운동이 두 벌 나가고, id 기준이면 한 번만 나간다 — 두 구현을 가르는 입력이다.
    """
    library = copy.deepcopy(_library())
    for ex in library["painAreas"]["knee"]["exercises"]:
        ex["name"] = f"개명-{ex['name']}"
    monkeypatch.setattr(exercise_map, "_CORRECTIVE_EXERCISES_CACHE", library)
    return library


def test_dedup_is_by_id_not_name(_renamed_library) -> None:
    """축5 파생 — 이름이 갈라져도 같은 운동은 한 번만 나간다."""
    # leg 감점 → legs_not_extended 대표(스쿼트) + 무릎 통증 → 스쿼트(개명본).
    # 같은 id(squats)가 두 경로로 들어온다.
    result = exercise_map.map_exercises(
        None,
        pain_areas=["knee"],
        motion_id=None,
        deduction_keypoint_sets=["leg"],
    )
    ids = [ex["id"] for ex in result]
    assert "squats" in ids, ids
    assert ids.count("squats") == 1, f"같은 운동이 두 벌 나갔다: {ids}"
    # 대조 — 이름은 실제로 갈라져 있다(이름 기준이었다면 통과했을 입력).
    names = [ex["name"] for ex in result]
    assert len(set(names)) == len(names)


# ── 무행동 회귀 (라이브러리가 정합인 동안 결과는 종전과 같다) ────────────────


def _name_deduped(rows: list[dict]) -> list[str]:
    """종전 구현(name 기준 dedup)을 그대로 재현해 비교 대조군으로 쓴다."""
    seen: set[str] = set()
    out: list[str] = []
    for ex in rows:
        name = ex.get("name")
        if not isinstance(name, str) or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def test_id_dedup_matches_name_dedup_on_the_real_library() -> None:
    """라이브러리가 정합(이름 <-> id 일대일)이면 두 방식의 산출이 같아야 한다.

    4개 doc 표본 대신 **어휘 전수**로 잰다 — 감점 부위 어휘 8값의 1~2개 조합 전부
    x 통증부위 8값의 0~1개. 표본보다 넓고, 표본이 안 건드리는 조합까지 덮는다.
    """
    parts = sorted(exercise_map._KEYPOINT_SET_TO_DEFECTS)
    pain_options: list[list[str]] = [[]] + [[a] for a in sorted(models.PAIN_AREAS)]
    combos = [[p] for p in parts] + [list(c) for c in itertools.permutations(parts, 2)]

    checked = 0
    for kp_sets in combos:
        for pain in pain_options:
            result = exercise_map.map_exercises(
                None,
                pain_areas=pain,
                motion_id=None,
                deduction_keypoint_sets=kp_sets,
            )
            assert _name_deduped(result) == [ex["name"] for ex in result], (
                f"id dedup 과 name dedup 이 갈렸다: kp={kp_sets} pain={pain}"
            )
            checked += 1
    # 표본 수를 박제한다 — 어휘가 늘면 여기도 같이 늘어야 한다.
    assert checked == len(combos) * len(pain_options)
    assert checked >= 500, checked
