"""결과 조립 — contract.md §4 키/모드 로직 검증. AWS 불필요."""

import numpy as np

from sunity_shared.analysis import assemble, kismam
from sunity_shared.analysis.interfaces import (
    FallbackCoachWriter,
    NotImplementedFrameExtractor,
    NotImplementedPoseEstimator,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS

REF = {"motionId": "m1", "name": "인사이드 레그 행", "athleteName": "정은지"}


def _assess(dev_map=None):
    dev = np.zeros(NUM_JOINTS)
    for k, v in (dev_map or {}).items():
        dev[JOINT_KEYS.index(k)] = v
    return kismam.assess(dev)


def test_result_has_exact_contract_keys():
    a = _assess({"left_knee": 50})
    r = assemble.build_result(
        a, assemble.build_mode1(REF, similarity=72), my_video_url="s3://my"
    )
    assert set(r) == {
        "overallScore",
        "partScores",
        "joints",
        "tips",
        "comparison",
        "myVideoUrl",
    }
    assert set(r["partScores"]) == {"상체", "코어", "하체"}
    assert len(r["tips"]) == 3
    assert len(r["joints"]) == NUM_JOINTS
    for j in r["joints"]:
        assert set(j) <= {"key", "labelKo", "score", "issue"}
    for t in r["tips"]:
        assert set(t) == {"joint", "title", "detail"}


def test_issue_only_when_below_threshold():
    a = _assess({"left_knee": 60})  # 무릎만 크게 → 무릎만 issue
    joints = {j["key"]: j for j in assemble.build_joints(a)}
    assert "issue" in joints["left_knee"]
    assert "issue" not in joints["right_elbow"]


def test_mode1_shape_and_clamp():
    c = assemble.build_mode1(REF, similarity=140)
    assert c == {
        "mode": "mode1",
        "referenceMotionId": "m1",
        "referenceMotionName": "인사이드 레그 행",
        "athleteName": "정은지",
        "similarity": 100,  # clamp
    }


def test_mode3_first_has_no_delta():
    c = assemble.build_mode3(True, None, None, {"상체": 80, "코어": 70, "하체": 60})
    assert c == {"mode": "mode3", "isFirst": True}


def test_mode3_delta_from_previous():
    c = assemble.build_mode3(
        False,
        "prev123",
        {"상체": 70, "코어": 60, "하체": 50},
        {"상체": 78, "코어": 60, "하체": 45},
    )
    assert c["previousAnalysisId"] == "prev123"
    assert c["deltaFromPrevious"] == {"상체": 8, "코어": 0, "하체": -5}


def test_referenceVideoUrl_only_when_given():
    a = _assess()
    r1 = assemble.build_result(a, assemble.build_mode1(REF, 90), "s3://my")
    r2 = assemble.build_result(
        a, assemble.build_mode1(REF, 90), "s3://my", reference_video_url="s3://ref"
    )
    assert "referenceVideoUrl" not in r1
    assert r2["referenceVideoUrl"] == "s3://ref"


def test_cerebras_detail_used_when_present_else_fallback():
    a = _assess({"left_knee": 50})
    top = kismam.top_issues(a, n=3)
    tips = assemble.build_tips(top, {"left_knee": "무릎을 더 펴세요"})
    by_joint = {t["joint"]: t for t in tips}
    assert by_joint["left_knee"]["detail"] == "무릎을 더 펴세요"
    # 다른 관절은 폴백 문장(실제 편차값 포함, 위조 아님)
    other = next(t for k, t in by_joint.items() if k != "left_knee")
    assert "차이가 납니다" in other["detail"]


def test_stub_interfaces_raise_or_empty():
    import pytest

    with pytest.raises(NotImplementedError):
        NotImplementedFrameExtractor().extract("/tmp/v.mp4")
    with pytest.raises(NotImplementedError):
        NotImplementedPoseEstimator().estimate(np.zeros((1, 17, 3)))
    assert FallbackCoachWriter().write({}) == {}
