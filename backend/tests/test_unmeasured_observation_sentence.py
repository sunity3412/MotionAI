"""quick-260925-nnt — 못 잰 부위 질문 한 줄: Gemini 가 본 것을 belle 방향 문장으로 (belle 09-25).
belle: "정확히 재기 어려웠던 부분이면 분석을 못했다는 말이냐?" → 그렇다 → "왼팔을 굽혀 폴을 감싸 안는 것이 동작의 문제가 될 수 있어요 같은 방향으로".
단언: (1) 명사형 어미 → "-는/은 것" 절(아는 어미만, 모르면 None) (2) 세 꼴(절/인용/라벨) (3) 09-25 climb 실수 저장 doc 의 gap 그대로 넣으면 그 문장
(4) 정타(gap 0)는 질문 0 (5) 말투에 "싶어요"(수강생 목소리) 없음. 실 Gemini/Pod/Firestore 호출 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared.analysis import phrasebook  # noqa: E402


@pytest.mark.parametrize(
    "fault_state, clause",
    [
        ("왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안음", "왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안는 것"),
        ("양다리 벌어짐 각도가 기준에 비해 현저히 좁음", "양다리 벌어짐 각도가 기준에 비해 현저히 좁은 것"),
        ("기준 영상 대비 양다리 벌림 각도가 다소 좁음", "기준 영상 대비 양다리 벌림 각도가 다소 좁은 것"),
        ("굽혀서 안고 있음", "굽혀서 안고 있는 것"),
        ("왼쪽 무릎이 펴지지 않음", "왼쪽 무릎이 펴지지 않는 것"),
        ("상체가 폴에서 떨어짐", "상체가 폴에서 떨어지는 것"),
        ("팔꿈치가 굽힘", "팔꿈치가 굽히는 것"),
        ("그립이 흔들림.", "그립이 흔들리는 것"),
        ("머리가 덜 젖혀져 시선 방향이 다름", "머리가 덜 젖혀져 시선 방향이 다른 것"),  # 09-25 kip-up 실수 Gemini 원문
    ],
)
def test_nominal_ending_becomes_a_clause(fault_state, clause):
    assert phrasebook.observation_clause_ko(fault_state) == clause


@pytest.mark.parametrize("fault_state", [None, "", "좁", "왼팔의 자세와 그립 방식이 기준과 완전히 다르다", "x" * 81])
def test_unknown_or_bad_endings_give_none(fault_state):
    assert phrasebook.observation_clause_ko(fault_state) is None


def test_three_sentence_shapes():
    assert app.unmeasured_question_text("왼팔 및 왼손", "왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안음") == (
        "왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안는 것이 동작의 문제가 될 수 있어요. 강사님과 확인해보세요."
    )
    assert app.unmeasured_question_text("왼팔 및 왼손", "왼팔의 자세가 기준과 완전히 다르다.") == (
        "이렇게 보였어요: \"왼팔의 자세가 기준과 완전히 다르다\". 잰 값은 없어요. 강사님과 확인해보세요."
    )
    assert app.unmeasured_question_text("목표 지점까지 몸을 뻗어 닿는 정도", None) == (
        "이번 영상에서 정확히 재기 어려웠던 부분이 있어요 (목표 지점까지 몸을 뻗어 닿는 정도). 강사님과 확인해보세요."
    )


def _climb_breakdown():
    # 2026-09-25 Pod climb 실수(465b4029) 저장 doc 의 coverageGaps 그대로.
    return {"records": [], "coverageGaps": [{
        "reason": "no_grip_proximity_measurement", "faultState": "왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안음",
        "keypointSet": "grip", "ruleId": None, "faultType": "grip", "bodyPart": "왼팔 및 왼손"}]}


def test_climb_gap_from_0925_becomes_belles_sentence():
    obs = app.collect_unmeasured_observations(_climb_breakdown())
    assert obs == [{"label": "왼팔 및 왼손", "observation": "왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안음"}]
    text = app.unmeasured_question_text(**obs[0])
    assert text == "왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안는 것이 동작의 문제가 될 수 있어요. 강사님과 확인해보세요."
    assert "싶어요" not in text


def test_reach_gap_and_fallback_record_use_the_label_shape_and_dedup():
    bd = {"records": [{"ruleId": "quantification_unavailable_dimension_overall"}],
          "coverageGaps": [{"keypointSet": "body_relative_reach", "bodyPart": "reach", "faultState": None},
                           {"keypointSet": "grip", "bodyPart": "왼팔 및 왼손", "faultState": "안음"},
                           {"keypointSet": "grip", "bodyPart": "왼팔 및 왼손", "faultState": "안음"}]}
    obs = app.collect_unmeasured_observations(bd)
    assert [o["label"] for o in obs] == ["목표 지점까지 몸을 뻗어 닿는 정도", "왼팔 및 왼손", "세부 부위별 측정"]
    assert obs[0]["observation"] is None and obs[2]["observation"] is None


def test_no_gaps_means_no_question():
    assert app.collect_unmeasured_observations({"records": [], "coverageGaps": []}) == []
    assert app.collect_unmeasured_observations(None) == []


# ── SCHEMA v8.2 observation_ko — 짧은 관찰문 채택 조건 (부위 + 동작 꼴일 때만) ───────────


def test_short_observation_is_preferred_when_it_is_part_plus_action():
    bd = {"records": [], "coverageGaps": [{
        "keypointSet": "grip", "bodyPart": "왼팔 및 왼손",
        "faultState": "왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안음", "observationKo": "왼팔을 굽혀 폴을 감싸 안음"}]}
    obs = app.collect_unmeasured_observations(bd)
    assert obs[0]["observation"] == "왼팔을 굽혀 폴을 감싸 안음"
    assert app.unmeasured_question_text(**obs[0]) == "왼팔을 굽혀 폴을 감싸 안는 것이 동작의 문제가 될 수 있어요. 강사님과 확인해보세요."


@pytest.mark.parametrize("bad", [None, "", "완전히 다름", "굽힘", "x" * 41, "왼팔의 자세와 그립 방식이 기준과 완전히 다르다"])
def test_malformed_short_observation_falls_back_to_the_long_one(bad):
    bd = {"records": [], "coverageGaps": [{"keypointSet": "grip", "bodyPart": "왼팔 및 왼손",
                                          "faultState": "왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안음", "observationKo": bad}]}
    assert app.collect_unmeasured_observations(bd)[0]["observation"] == "왼팔을 크게 굽혀 가슴 앞으로 가져와 폴을 감싸 안음"


def test_schema_and_prompt_carry_the_observation_rule():
    from sunity_shared.analysis import gemini_vision_scorer as gvs
    props = gvs.build_schema()["properties"]["differences"]["items"]
    assert "observation_ko" in props["properties"] and "observation_ko" in props["required"]
    for prompt in (gvs._PROMPT, gvs._COMPARISON_PROMPT):
        assert "부위 + 동작" in prompt and "강사가 봐야 할 곳이 바뀌지 않으면 뺀다" in prompt
    assert gvs.PROMPT_VERSION == "v11.3" and gvs.SCHEMA_VERSION == "v8.2"


def test_one_line_per_keypoint_set_even_when_labels_differ():
    """09-25 Pod climb 실수 실측: 고개 지목이 '머리 및 목'·'머리' 두 라벨(둘 다 line)로 와 같은 말이 두 줄 떴다 → 한 줄."""
    bd = {"records": [], "coverageGaps": [
        {"faultType": "pointed_not_scored", "keypointSet": "arm_extension", "bodyPart": "왼팔", "faultState": "…", "observationKo": "왼팔을 굽혀 폴을 감싸 안음"},
        {"faultType": "pointed_not_scored", "keypointSet": "arm_extension", "bodyPart": "왼팔", "faultState": "…", "observationKo": "왼팔을 굽혀 폴을 감싸 안음"},
        {"faultType": "pointed_not_scored", "keypointSet": "line", "bodyPart": "머리 및 목", "faultState": "…", "observationKo": "고개를 숙임"},
        {"faultType": "pointed_not_scored", "keypointSet": "line", "bodyPart": "머리", "faultState": "…", "observationKo": "고개를 아래로 숙임"},
    ]}
    obs = app.collect_unmeasured_observations(bd)
    assert [o["label"] for o in obs] == ["왼팔", "머리 및 목"]
    assert [app.unmeasured_question_text(**o) for o in obs] == [
        "왼팔을 굽혀 폴을 감싸 안는 것이 동작의 문제가 될 수 있어요. 강사님과 확인해보세요.",
        "고개를 숙이는 것이 동작의 문제가 될 수 있어요. 강사님과 확인해보세요.",
    ]
