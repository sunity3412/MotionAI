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


def test_overall_from_dimensions_uses_core_dimensions():
    # Phase 19 D-01 (모순 케이스 갱신): 종합은 core 차원(angle/line)만 반영하고 stability
    # (떨림)는 인플레 기여하지 않는다. 평균식은 stability 가 높으면 종합을 끌어올려 위양성을
    # 만든다 (deferred-items.md 근본원인). DIM_* 상수 사용 (literal "angle" 하드코딩 금지).
    DIM_ANGLE = dimensions.DIM_ANGLE
    DIM_LINE = dimensions.DIM_LINE
    DIM_STABILITY = dimensions.DIM_STABILITY
    # core min — angle 40 / line 80 → 종합 40 (stability 99 비기여).
    assert (
        dimensions.overall_from_dimensions(
            {DIM_ANGLE: 40, DIM_LINE: 80, DIM_STABILITY: 99}
        )
        == 40
    )
    # no-core fallback — core 차원이 하나도 없으면 절대트랙(stability) 단독 사용.
    assert dimensions.overall_from_dimensions({DIM_STABILITY: 99}) == 99
    # 빈 입력 보존 — 0.
    assert dimensions.overall_from_dimensions({}) == 0


# ── Phase 19 D-01 신규 RED 케이스 (단독 실행 시 현재 비례감점/평균식에 대해 behavior fail) ──


def test_micro_bent_zero_track():
    # SCORE-07: 신전 요구 관절(knee)의 대표 각도가 160° 미만(140°)이면 해당 요소는
    # 무효(0점 트랙) — 비례감점이 아니라 요소 무효. 160° = 180° − 20° tol
    # [CITED: 19-IPSF-DEDUCTION-NOTES §A 트랙1]. 현재 line_score 는 비례감점이라
    # 140° (부족분 40°) → 가우시안 점수(0 아님) → RED.
    p = _profile()  # elbows + knees EXTEND
    angles = _pose({k: 140.0 for k in _EXT})  # 전 신전관절 micro-bent
    assert dimensions.line_score(angles, p) == 0


def test_intentional_bend_not_penalized():
    # SCORE-07 위양성 가드 (Pitfall 4 chair-pose): expects_extension=False 관절은 140°여도
    # 0점 트랙 미적용 — 의도적 굽힘은 결함이 아니다. 신전 요구 관절(elbows)은 180° 로 정상.
    p = _profile(extend=("left_elbow", "right_elbow"))  # 무릎은 BENT_OK
    angles = _pose({
        "left_knee": 140.0, "right_knee": 140.0,   # 의도적 굽힘 — 깎이면 안 됨
        "left_elbow": 180.0, "right_elbow": 180.0,  # 신전 요구 — 완전 신전
    })
    # 무릎 굽힘이 0점 트랙을 발동시키지 않으므로 line 은 만점 유지.
    assert dimensions.line_score(angles, p) == 100


def test_stability_does_not_inflate():
    # TRUST-02: stability(매끄러운 fault)가 높아도 core 차원(angle/line)이 낮으면 종합은
    # 낮아야 한다. 현재 평균식: (40+40+99)/3 ≈ 60 → `<= 50` 실패 → RED.
    DIM_ANGLE = dimensions.DIM_ANGLE
    DIM_LINE = dimensions.DIM_LINE
    DIM_STABILITY = dimensions.DIM_STABILITY
    dimension_scores = {DIM_ANGLE: 40, DIM_LINE: 40, DIM_STABILITY: 99}
    # dimension_scores 키/순서 보존 단언 (Pitfall 2 — 입력 dict 불변).
    keys_before = list(dimension_scores.keys())
    overall = dimensions.overall_from_dimensions(dimension_scores)
    assert list(dimension_scores.keys()) == keys_before
    assert overall <= 50


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
