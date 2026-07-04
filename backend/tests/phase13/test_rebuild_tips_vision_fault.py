"""rebuild_tips_for_vision_fault 단위 테스트 (quick-260704-fwb follow-up, pod 검증).

발견: build_result 의 angle>=95 분기가 "거의 동일한 자세" 일반 팁 1개로 tips 를
대체하며 듀얼 코치 detail2 를 통째로 버림 — kip-up(vision veto 감점 88 + kismam
angle=100) 에서 (1) 카피 모순 (2) 처방 코칭 미노출. apply 이후 pipeline 이 표시만
재조립하는 순수 함수의 행동 계약을 고정한다:

  1. veto applied + 일반 팁 + coach_details 존재 → per-joint tips + detail2 방출,
     veto faultJoints 관절 선두.
  2. veto 미적용(부재/not_applicable 등) → 입력 그대로 (byte-동등, 하위호환).
  3. coach_details 빈 경우 → 일반 팁 유지 (수치 폴백 "0° 차이" 모순 차단).
  4. per-joint tips 가 이미 있으면 그대로 (기존 동작 불변).
  5. 채점 무접촉 — 점수/veto 필드 불변.
"""

from __future__ import annotations

import copy

from sunity_shared.analysis import assemble
from sunity_shared.analysis.kismam import JointAssessment


def _assess(key: str, label: str, score: int = 100, deviation: float = 0.0) -> JointAssessment:
    return JointAssessment(
        key=key, label_ko=label, score=score, deviation_deg=deviation, part="상체"
    )


_ASSESSMENTS = [
    _assess("left_shoulder", "왼쪽 어깨"),
    _assess("left_elbow", "왼쪽 팔꿈치"),
    _assess("right_shoulder", "오른쪽 어깨"),
]


def _detail2(note: str) -> dict:
    return {
        "causes": [
            {"title": "코어 긴장 부족", "explanation": "코어 긴장이 풀려 상체 지지가 무너져요.", "fix": "플랭크 30초 3세트"},
        ],
        "coachNote": note,
    }


_COACH_DETAILS = {
    "left_shoulder": {"detail": "어깨 실행 지시 한 줄", "detail2": _detail2("강사와 함께 영상 확인")},
    "left_elbow": {"detail": "팔꿈치 실행 지시 한 줄", "detail2": _detail2("강사와 함께 영상 확인")},
    "right_shoulder": {"detail": "오른어깨 실행 지시 한 줄", "detail2": _detail2("강사와 함께 영상 확인")},
}

_GENERIC_TIP = {
    "joint": None,
    "title": "정은지 선수와 거의 동일한 자세입니다",
    "detail": "관절각 일치도 100점 — 자세 차이가 거의 없어요. 안정성·라인 차원도 함께 확인해 보세요.",
}


def _result(veto: dict | None, tips: list | None = None) -> dict:
    out: dict = {
        "overallScore": 88,
        "dimensionScores": {"angle": 100, "line": 95},
        "tips": tips if tips is not None else [dict(_GENERIC_TIP)],
    }
    if veto is not None:
        out["visionVeto"] = veto
    return out


def test_veto_applied_angle100_emits_per_joint_tips_with_detail2() -> None:
    """(1) applied + 일반 팁 → per-joint tips + detail2, fault 관절 선두."""
    result = _result({
        "status": "applied",
        "tallyFinal": 88,
        "faultJoints": ["right_shoulder"],
    })
    rebuilt = assemble.rebuild_tips_for_vision_fault(
        result, _ASSESSMENTS, _COACH_DETAILS
    )
    tips = rebuilt["tips"]
    assert len(tips) == 3
    # veto fault 관절이 선두, 나머지는 top 순서 보존.
    assert [t["joint"] for t in tips] == ["right_shoulder", "left_shoulder", "left_elbow"]
    # detail2 (causes/coachNote) 가 유저에게 도달.
    for t in tips:
        assert "detail2" in t
        assert t["detail2"]["causes"]
    # 일반 팁 카피 소멸.
    assert all(t.get("joint") is not None for t in tips)


def test_no_veto_or_not_applied_keeps_generic_tip_byte_identical() -> None:
    """(2) veto 부재/not_applicable → 입력 그대로 (clean 케이스 하위호환)."""
    for veto in (None, {"status": "not_applicable"}, {"status": "mode3_held"}):
        result = _result(veto)
        snapshot = copy.deepcopy(result)
        rebuilt = assemble.rebuild_tips_for_vision_fault(
            result, _ASSESSMENTS, _COACH_DETAILS
        )
        assert rebuilt == snapshot


def test_empty_coach_details_keeps_generic_tip() -> None:
    """(3) coach_details 빈 dict/None → 일반 팁 유지 ("0° 차이" 수치 폴백 모순 차단)."""
    for details in ({}, None, {"_meta": {"model": "x"}}):
        result = _result({"status": "applied", "tallyFinal": 88})
        snapshot = copy.deepcopy(result)
        rebuilt = assemble.rebuild_tips_for_vision_fault(result, _ASSESSMENTS, details)
        assert rebuilt == snapshot


def test_existing_per_joint_tips_untouched() -> None:
    """(4) per-joint tips 가 이미 있으면 (angle<95 정상 경로) 그대로."""
    per_joint_tips = [
        {"joint": "left_knee", "title": "왼쪽 무릎 신전", "detail": "무릎을 펴세요."},
    ]
    result = _result({"status": "applied", "tallyFinal": 88}, tips=per_joint_tips)
    snapshot = copy.deepcopy(result)
    rebuilt = assemble.rebuild_tips_for_vision_fault(
        result, _ASSESSMENTS, _COACH_DETAILS
    )
    assert rebuilt == snapshot


def test_rebuild_does_not_touch_scores_or_veto() -> None:
    """(5) 채점 무접촉 — tips 외 필드(점수/veto/dimension) byte-동등."""
    result = _result({
        "status": "applied",
        "tallyFinal": 88,
        "faultJoints": ["left_shoulder"],
    })
    snapshot = copy.deepcopy(result)
    rebuilt = assemble.rebuild_tips_for_vision_fault(
        result, _ASSESSMENTS, _COACH_DETAILS
    )
    assert rebuilt["overallScore"] == snapshot["overallScore"]
    assert rebuilt["dimensionScores"] == snapshot["dimensionScores"]
    assert rebuilt["visionVeto"] == snapshot["visionVeto"]
    # 입력 result 자체는 mutate 하지 않음 (copy-on-write).
    assert result == snapshot


def test_build_result_then_rebuild_end_to_end_kipup_shape() -> None:
    """kip-up 형상 e2e: build_result(angle=100 → 일반 팁) 후 rebuild 로 detail2 복원."""
    result = assemble.build_result(
        _ASSESSMENTS,
        dimension_scores={"angle": 100, "line": 95},
        overall_score=100,
        comparison={"mode": "mode1"},
        my_video_url="https://example/video.mp4",
        coach_details=_COACH_DETAILS,
    )
    # build_result 는 여전히 일반 팁 (byte-동등 회귀 가드 — 채점/조립 본체 무접촉).
    assert len(result["tips"]) == 1 and result["tips"][0]["joint"] is None
    # veto 가 이후 감점 적용됐다고 가정 (pipeline 순서 재현).
    result["visionVeto"] = {"status": "applied", "tallyFinal": 88, "faultJoints": ["left_elbow"]}
    result["overallScore"] = 88
    rebuilt = assemble.rebuild_tips_for_vision_fault(
        result, _ASSESSMENTS, _COACH_DETAILS
    )
    tips = rebuilt["tips"]
    assert [t["joint"] for t in tips] == ["left_elbow", "left_shoulder", "right_shoulder"]
    assert all("detail2" in t for t in tips)
