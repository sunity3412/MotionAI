"""quick-260910-vwh Task 3 — 목록 구성이 분석 보고를 따라간다.

belle 2026-09-10: "균형 잡히게 섞는거 물론 좋지. 근데 그게 규칙이 될 필요는 없어.
분석마다 다를거아냐. 근력이 충분한데 뭐하러 헬스를 하겠어 … 말이 그렇다는거지
분석 보고에 따라 조절 되어야 한다는 말이야."

지키는 것 둘:
  (a) 감점이 걸린 **부위마다 대표를 하나씩** 먼저. 남는 자리는 감점 큰 부위부터
      두 번째. 한 부위가 목록을 독식하지 않는다.
  (b) 준비운동(kind=warmup)은 목록 앞. 원인 판단이 아니라 다치지 말라는 상식이다.

하지 않는 것:
  성격(근력/유연성)으로 개수를 맞추지 않는다 → test_exercise_kind_contract.py
"""

from __future__ import annotations

from sunity_shared.analysis.exercise_map import map_exercises

# 결과 카드가 실제로 그리는 행 수 (app ResultExerciseTab MAX_ROWS).
# 이 안에 부위가 몇 개 들어오는지가 belle 이 화면에서 보는 것이다.
_VISIBLE_ROWS = 3


def test_each_deducted_part_gets_a_representative_first() -> None:
    """어깨·다리·엉덩이가 걸리면 화면에 보이는 3행에 세 부위가 다 들어온다."""
    names = [
        e["name"]
        for e in map_exercises(
            None,
            pain_areas=[],
            motion_id=None,
            deduction_keypoint_sets=["shoulder", "leg", "hip"],
        )
    ]
    assert names[:_VISIBLE_ROWS] == [
        "팔굽혀펴기",  # shoulder
        "허벅지 뒤 스트레칭",  # leg
        "옆으로 다리 들기",  # hip
    ]
    # 2라운드에서야 leg 의 두 번째가 온다 — 부위 대표를 다 채운 뒤다.
    assert names[3] == "스쿼트"


def test_second_pick_follows_deduction_size_order() -> None:
    """부위 순서(감점 큰 순)를 뒤집으면 목록 순서도 따라 뒤집힌다."""
    def names(parts: list[str]) -> list[str]:
        return [
            e["name"]
            for e in map_exercises(
                None, pain_areas=[], motion_id=None, deduction_keypoint_sets=parts
            )
        ]

    assert names(["shoulder", "leg"])[0] == "팔굽혀펴기"
    assert names(["leg", "shoulder"])[0] == "허벅지 뒤 스트레칭"


def test_warmup_goes_first() -> None:
    """준비운동은 목록 앞 — 감점 부위 운동보다도 먼저 데운다."""
    result = map_exercises(
        None,
        pain_areas=["hip"],
        motion_id=None,
        deduction_keypoint_sets=["shoulder"],
    )
    names = [e["name"] for e in result]
    assert result[0]["kind"] == "warmup"
    assert names == ["앞뒤로 다리 흔들기", "팔굽혀펴기", "비둘기 자세"]


def test_no_warmup_leaves_order_untouched() -> None:
    """준비운동이 없으면 순서를 흔들지 않는다 (회귀 가드)."""
    names = [
        e["name"]
        for e in map_exercises(
            None,
            pain_areas=["shoulder"],
            motion_id=None,
            deduction_keypoint_sets=["torso"],
        )
    ]
    assert names == ["플랭크", "팔굽혀펴기", "매달려 어깨 내리기"]


def test_one_part_still_yields_one_representative_first() -> None:
    """부위가 하나면 그 부위 대표가 1순위 — 하한을 만들지 않는다."""
    names = [
        e["name"]
        for e in map_exercises(
            None, pain_areas=[], motion_id=None, deduction_keypoint_sets=["grip"]
        )
    ]
    assert names == ["파머스 워크"]
