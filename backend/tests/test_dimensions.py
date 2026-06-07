"""IPSF 실행 차원 점수 — 절대 지표(라인/안정성)의 의미 검증. AWS 불필요.

2026-05-29: 균형(좌우 대칭) 차원 제거. line 은 기술 조건부(EXTEND 관절만 평가)이므로
TechniqueProfile 을 함께 넘긴다.
"""

import numpy as np

from sunity_shared.analysis import dimensions, technique
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS

J = NUM_JOINTS
_EXT = ("left_elbow", "right_elbow", "left_knee", "right_knee")


def _pose(angle_map: dict[str, float], t: int = 30) -> np.ndarray:
    """모든 프레임이 동일한 (정지) 포즈. angle_map 외 관절은 90°."""
    base = np.full(J, 90.0)
    for k, v in angle_map.items():
        base[JOINT_KEYS.index(k)] = v
    return np.tile(base, (t, 1))


def _profile(extend=_EXT) -> technique.TechniqueProfile:
    """주어진 관절을 EXTEND, 나머지는 BENT_OK 로 보는 명시 프로파일(결정적 테스트용)."""
    exp = {
        k: technique.JOINT_EXTEND if k in extend else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(name="t", category="unknown", joint_expectations=exp)


def test_line_full_extension_is_high():
    # 신전 요구 사지가 180° → 라인 만점. 살짝 굽으면 감점.
    p = _profile()
    straight = dimensions.line_score(_pose({k: 180.0 for k in _EXT}), p)
    bent = dimensions.line_score(_pose({k: 158.0 for k in _EXT}), p)
    assert straight == 100
    assert bent is not None and bent < straight


def test_line_none_when_no_extension_required():
    # 전부 의도적 굽힘(EXTEND 관절 없음) → 라인 평가 대상 아님 → None(가짜 점수 안 만듦).
    p = _profile(extend=())
    assert dimensions.line_score(_pose({k: 90.0 for k in _EXT}), p) is None


def test_line_only_penalizes_required_joints():
    # 무릎은 굽었지만(의도) 팔꿈치만 신전 요구 → 무릎 굽힘이 라인을 깎지 않는다.
    bent_knees = _pose({"left_knee": 90, "right_knee": 90,
                        "left_elbow": 180, "right_elbow": 180})
    only_elbows = _profile(extend=("left_elbow", "right_elbow"))
    assert dimensions.line_score(bent_knees, only_elbows) == 100


def test_stability_still_pose_beats_shaky():
    a_still = _pose({"left_knee": 170})
    rng = np.random.default_rng(0)
    a_shaky = a_still + rng.normal(0, 25, size=a_still.shape)
    assert dimensions.stability_score(a_still) > dimensions.stability_score(a_shaky)


def test_single_frame_stability_is_neutral_high():
    assert dimensions.stability_score(_pose({}, t=1)) == 100


def test_absolute_scores_keys_no_reference():
    d = dimensions.absolute_dimension_scores(_pose({"left_knee": 175}), _profile())
    assert set(d) == {"line", "stability"}
    assert all(0 <= v <= 100 for v in d.values())


def test_absolute_scores_drops_line_when_not_applicable():
    # EXTEND 관절 없음 → line 생략, stability 만.
    d = dimensions.absolute_dimension_scores(_pose({}), _profile(extend=()))
    assert set(d) == {"stability"}


def test_extension_deviation_targets_only_required_joints():
    dev = dimensions.extension_deviation(_pose({"left_knee": 150}), _profile())
    # 어깨(BENT_OK)는 항상 0, 신전 요구 무릎은 180-150=30.
    assert dev[JOINT_KEYS.index("left_shoulder")] == 0
    assert dev[JOINT_KEYS.index("left_knee")] == 30


def test_overall_from_dimensions_is_mean():
    assert dimensions.overall_from_dimensions({"a": 80, "b": 60, "c": 70}) == 70
    assert dimensions.overall_from_dimensions({}) == 0


# ── Phase 12.5 v4 — 신 helpers 단위 테스트 (Codex v3 HIGH-2 fix) ────────


def test_select_window_uses_profile_when_set():
    # profile.hold_window 가 있으면 그 구간 그대로 사용 (TechniqueProfile 은 frozen → replace)
    import dataclasses
    p = dataclasses.replace(_profile(), hold_window=(5, 15))
    angles = _pose({"left_knee": 175}, t=30)
    sliced, (s, e) = dimensions._select_window(angles, p)
    assert (s, e) == (5, 15)
    assert sliced.shape[0] == 10


def test_select_window_falls_back_to_auto():
    # profile.hold_window 가 None (default) 이면 hold_window() 자동 사용
    p = _profile()
    angles = _pose({"left_knee": 175}, t=30)
    sliced, (s, e) = dimensions._select_window(angles, p)
    # 모두 동일 포즈 → 어떤 window 든 분산 0. shape > 0 만 확인.
    assert sliced.shape[0] > 0


def test_select_window_single_frame_graceful():
    p = _profile()
    angles = _pose({}, t=1)
    sliced, (s, e) = dimensions._select_window(angles, p)
    assert sliced.shape[0] == 1
    assert (s, e) == (0, 1)


def test_line_deficits_by_joint_extend_only():
    # EXTEND 관절 = elbows + knees. default 90° → 신전 부족 90, left_knee 150 → 30
    p = _profile()
    angles = _pose({"left_knee": 150}, t=20)
    defs = dimensions.line_deficits_by_joint(angles, p)
    assert set(defs.keys()) <= set(_EXT)  # EXTEND 관절만
    assert defs["left_knee"] == 30.0
    # 90 default 일 때 신전 부족 = 90 (180 - 90)
    assert defs["left_elbow"] == 90.0
    assert defs["right_elbow"] == 90.0
    assert defs["right_knee"] == 90.0


def test_line_deficits_no_extend_joints():
    # profile.expects_extension 모두 False → 빈 dict
    p = _profile(extend=())
    angles = _pose({"left_knee": 150}, t=20)
    defs = dimensions.line_deficits_by_joint(angles, p)
    assert defs == {}


def test_stability_wobble_by_joint_basic():
    # 모든 frame 동일 = wobble 0
    p = _profile()
    angles_still = _pose({"left_knee": 175}, t=30)
    wobble = dimensions.stability_wobble_by_joint(angles_still, p)
    assert all(v == 0.0 for v in wobble.values())
    # 흔들리는 영상 = wobble > 0
    rng = np.random.default_rng(42)
    angles_shaky = angles_still + rng.normal(0, 25, size=angles_still.shape)
    wobble_shaky = dimensions.stability_wobble_by_joint(angles_shaky, p)
    assert any(v > 5.0 for v in wobble_shaky.values())


def test_stability_wobble_single_frame_empty():
    # T=1 → 떨림 측정 불가 → 빈 dict
    p = _profile()
    angles = _pose({}, t=1)
    wobble = dimensions.stability_wobble_by_joint(angles, p)
    assert wobble == {}


def test_helpers_share_window_with_score_functions():
    # _select_window 가 line_score / stability_score 와 같은 window 사용 (drift 0)
    import dataclasses
    p = dataclasses.replace(_profile(), hold_window=(3, 13))
    angles = _pose({"left_knee": 170}, t=20)
    sliced_a, _ = dimensions._select_window(angles, p)
    assert sliced_a.shape[0] == 10
    # line_score 도 같은 window 사용 (rep = mean of windowed)
    ls = dimensions.line_score(angles, p)
    assert ls is not None  # 점수 산출 정상
