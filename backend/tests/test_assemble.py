"""결과 조립 — contract.md §4 키/모드 로직 검증. AWS 불필요."""

import numpy as np

from sunity_shared.analysis import assemble, kismam
from sunity_shared.analysis.interfaces import FallbackCoachWriter
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
        assert set(j) <= {
            "key", "labelKo", "score", "issue",
            "currentAngle", "targetAngle", "deltaDeg", "direction",
        }
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


def test_mode1_segment_scores_included_only_when_given():
    seg = {
        "base": 82,
        "extension": 64,
        "baseMotionId": "ref-plank-spin",
        "baseMotionName": "플랭크 스핀",
    }
    c = assemble.build_mode1(REF, similarity=70, segment_scores=seg)
    assert c["segmentScores"] == seg
    # 단일 모션(segment 없음)이면 키 자체가 없음
    assert "segmentScores" not in assemble.build_mode1(REF, similarity=70)


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


def test_joint_structured_fields_when_angles_given():
    # user 무릎이 기준보다 23도 작음(덜 펴짐) → extend 방향, deltaDeg 음수
    a = kismam.assess(
        deviation_deg=[23.0] + [0.0] * (NUM_JOINTS - 1),  # left_knee 가 JOINT_KEYS[0] 일 필요 X — 거리만 검사용
        user_angles={"left_knee": 145.0, "right_hip": 110.0},
        reference_angles={"left_knee": 168.0, "right_hip": 95.0},
    )
    by_key = {j["key"]: j for j in assemble.build_joints(a)}
    knee = by_key["left_knee"]
    assert knee["currentAngle"] == 145.0
    assert knee["targetAngle"] == 168.0
    assert knee["deltaDeg"] == -23.0
    assert knee["direction"] == "extend"  # delta < 0 → 펴기
    hip = by_key["right_hip"]
    assert hip["deltaDeg"] == 15.0
    assert hip["direction"] == "close"  # delta > 0 → 더 모으기


def test_joint_structured_fields_omitted_when_no_angles():
    a = kismam.assess(deviation_deg=[0.0] * NUM_JOINTS)  # 각도 정보 없음
    for j in assemble.build_joints(a):
        assert "currentAngle" not in j
        assert "targetAngle" not in j
        assert "deltaDeg" not in j
        assert "direction" not in j


def test_fallback_coach_writer_returns_empty():
    # CoachWriter 폴백 — Cerebras 미연결 시 빈 dict → assemble 수치 폴백.
    assert FallbackCoachWriter().write({}) == {}
