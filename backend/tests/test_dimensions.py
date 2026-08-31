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
    # profile.hold_window 가 있으면 그 창을 국면 힌트로 사용 (TechniqueProfile frozen → replace)
    #
    # quick-260831-gyk 기대값 변경 정당화: profile 창은 이제 국면 힌트 "상한"이지 창 그
    # 자체가 아니다 — 힌트 창 내부에서 분산-최소 부창을 재선택한다 (이 수리의 정의 변경,
    # belle 08-31 파워스핀 위양성). 종전 단언 (s,e) == (5,15) 정확 일치 → 포함 불변식
    # (5 <= s' < e' <= 15) + 부창 폭 규칙 w = max(2, min(10, 10//4)) = 2 로 갱신.
    # constant 포즈 → 분산 0 균일 → 결정론 tie-break(첫 부창) = (5, 7).
    import dataclasses
    p = dataclasses.replace(_profile(), hold_window=(5, 15))
    angles = _pose({"left_knee": 175}, t=30)
    sliced, (s, e) = dimensions._select_window(angles, p)
    assert 5 <= s < e <= 15
    assert e - s == 2  # w = max(2, min(10, 10//4)) = 2
    assert (s, e) == (5, 7)  # 균일 분산 → 첫 부창 (결정론)
    assert sliced.shape[0] == 2


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


# ── quick-260831-gyk — Gemini 국면 창을 "힌트"로 강등: 힌트 창 내부 안정 부창 재선택 ──
# belle 08-31 × 판정(파워스핀 정타 leg_extension -20 위양성): Gemini hold ±2초 창이
# 스핀 진입 전환부를 측정 창에 섞었다. 수리 = profile.hold_window 를 verbatim 쓰지 않고
# 그 창 **내부에서** 기존 hold_window(분산 최소) 로직으로 안정 부창을 재선택한다.
# 33-A4 국면 게이트 목적(국면 밖 프레임 배제)은 유지 — 부창은 항상 힌트 창 내부.


def test_select_window_reselects_stable_subwindow_inside_hint():
    # Test 1 (전환부 오염 차단): 힌트 창 앞부분 = 각도가 크게 변하는 전환부,
    # 뒷부분 = 일정한 홀드. 기대 = 부창이 홀드 구간에 안착(전환부 프레임 배제).
    import dataclasses
    t = 24
    angles = np.full((t, J), 90.0)
    knee = JOINT_KEYS.index("right_knee")
    # 프레임 0..11 = 전환부(20/150 요동), 12..23 = 홀드(178 일정)
    for i in range(12):
        angles[i, knee] = 20.0 if i % 2 == 0 else 150.0
    angles[12:, knee] = 178.0
    p = dataclasses.replace(_profile(), hold_window=(0, t))  # 힌트 창 = 전체
    sliced, (s, e) = dimensions._select_window(angles, p)
    assert s >= 12, "부창이 전환부를 배제하고 홀드 구간에 안착해야 한다"
    assert e <= t
    assert np.allclose(sliced[:, knee], 178.0)


def test_select_window_subwindow_always_inside_hint():
    # Test 2 (포함 불변식): 어떤 입력이든 (s', e') 는 clamp 된 힌트 창 내부
    # — s' >= s, e' <= e, s' < e'. 33-A4 국면 게이트 목적 유지의 기계 증명.
    import dataclasses
    rng = np.random.default_rng(1)
    t = 40
    angles = rng.uniform(20.0, 180.0, size=(t, J))
    for hint in [(5, 35), (0, 40), (10, 12), (-3, 100), (20, 23)]:
        p = dataclasses.replace(_profile(), hold_window=hint)
        sliced, (s, e) = dimensions._select_window(angles, p)
        cs = max(0, min(int(hint[0]), t))
        ce = max(cs, min(int(hint[1]), t))
        assert cs <= s < e <= ce, f"hint={hint} → ({s},{e}) 가 힌트 창 밖"
        assert sliced.shape[0] == e - s


def test_select_window_empty_hint_falls_back_to_full_auto():
    # Test 3 (WR-05 보존): clamp 후 s == e 인 빈 힌트 창은 종전대로 전체 자동
    # hold_window 폴백 (기존 test_select_window_* 계열과 공존).
    import dataclasses
    t = 30
    angles = np.full((t, J), 90.0)
    knee = JOINT_KEYS.index("left_knee")
    rng = np.random.default_rng(2)
    angles[:20, knee] = rng.uniform(20.0, 180.0, size=20)  # 앞 20프레임 요동
    angles[20:, knee] = 175.0  # 뒤 10프레임 홀드
    p = dataclasses.replace(_profile(), hold_window=(50, 60))  # clamp → (30, 30)
    sliced, (s, e) = dimensions._select_window(angles, p)
    auto_s, auto_e = dimensions.hold_window(angles)
    assert (s, e) == (auto_s, auto_e)
    assert np.array_equal(sliced, angles[auto_s:auto_e])


def test_select_window_no_profile_hint_unchanged():
    # Test 4 (profile 없음 무변경): profile=None / hold_window=None 경로는 종전
    # hold_window(a) 그대로 — byte-동일 결과.
    rng = np.random.default_rng(3)
    angles = rng.uniform(20.0, 180.0, size=(25, J))
    auto_s, auto_e = dimensions.hold_window(angles)
    for p in (None, _profile()):  # _profile() 은 hold_window 기본값 None
        sliced, (s, e) = dimensions._select_window(angles, p)
        assert (s, e) == (auto_s, auto_e)
        assert np.array_equal(sliced, angles[s:e])


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
    #
    # quick-260831-gyk 기대값 변경 정당화: 테스트 의도(점수 함수들과 창 공유, drift 0)는
    # 그대로 성립 — shape 단언만 새 의미로 갱신. 힌트 창 (3,13) 내부 부창 재선택으로
    # shape == 부창 폭 w = max(2, min(10, 10//4)) = 2 (종전 10 = verbatim 창 폭).
    import dataclasses
    p = dataclasses.replace(_profile(), hold_window=(3, 13))
    angles = _pose({"left_knee": 170}, t=20)
    sliced_a, _ = dimensions._select_window(angles, p)
    assert sliced_a.shape[0] == 2
    # line_score 도 같은 window 사용 (rep = mean of windowed)
    ls = dimensions.line_score(angles, p)
    assert ls is not None  # 점수 산출 정상
