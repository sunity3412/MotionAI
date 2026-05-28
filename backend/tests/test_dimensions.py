"""IPSF 실행 차원 점수 — 절대 지표(라인/균형/안정성)의 의미 검증. AWS 불필요."""

import numpy as np

from sunity_shared.analysis import dimensions
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS

J = NUM_JOINTS


def _pose(angle_map: dict[str, float], t: int = 30) -> np.ndarray:
    """모든 프레임이 동일한 (정지) 포즈. angle_map 외 관절은 90°."""
    base = np.full(J, 90.0)
    for k, v in angle_map.items():
        base[JOINT_KEYS.index(k)] = v
    return np.tile(base, (t, 1))


def test_balance_perfect_symmetry_is_high():
    # 좌우 완전 대칭 → 균형 100.
    a = _pose({})
    assert dimensions.balance_score(a) == 100


def test_balance_asymmetry_lowers_score():
    sym = dimensions.balance_score(_pose({}))
    asym = dimensions.balance_score(_pose({"left_knee": 90, "right_knee": 140}))
    assert asym < sym


def test_line_full_extension_is_high():
    # 사지가 180°(완전 신전) → 라인 만점에 가까움.
    straight = dimensions.line_score(_pose({k: 180.0 for k in (
        "left_elbow", "right_elbow", "left_knee", "right_knee")}))
    bent = dimensions.line_score(_pose({k: 158.0 for k in (
        "left_elbow", "right_elbow", "left_knee", "right_knee")}))
    assert straight == 100
    assert bent < straight


def test_stability_still_pose_beats_shaky():
    a_still = _pose({"left_knee": 170})
    # 떨리는 시퀀스 — 프레임마다 흔들림 추가.
    rng = np.random.default_rng(0)
    a_shaky = a_still + rng.normal(0, 25, size=a_still.shape)
    assert dimensions.stability_score(a_still) > dimensions.stability_score(a_shaky)


def test_single_frame_stability_is_neutral_high():
    # 프레임 1개 — 떨림 측정 불가 → 감점 근거 없음.
    assert dimensions.stability_score(_pose({}, t=1)) == 100


def test_absolute_scores_have_three_keys_no_reference():
    d = dimensions.absolute_dimension_scores(_pose({"left_knee": 175}))
    assert set(d) == {"line", "balance", "stability"}
    assert all(0 <= v <= 100 for v in d.values())


def test_overall_from_dimensions_is_mean():
    assert dimensions.overall_from_dimensions({"a": 80, "b": 60, "c": 70}) == 70
    assert dimensions.overall_from_dimensions({}) == 0
