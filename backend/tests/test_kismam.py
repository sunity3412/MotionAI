"""KISMAM 점수/Top-3 — 결정적 검증. AWS 불필요."""

import numpy as np
import pytest

from sunity_shared.analysis import kismam
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS, PARTS


def test_zero_deviation_full_score():
    a = kismam.assess(np.zeros(NUM_JOINTS))
    assert all(j.score == 100 for j in a)
    assert kismam.overall_score(a) == 100
    ps = kismam.part_scores(a)
    assert set(ps) == set(PARTS)
    assert all(v == 100 for v in ps.values())


def test_score_monotonic_decreasing_with_deviation():
    dev0 = np.zeros(NUM_JOINTS)
    dev1 = np.full(NUM_JOINTS, 15.0)
    dev2 = np.full(NUM_JOINTS, 45.0)
    s0 = kismam.overall_score(kismam.assess(dev0))
    s1 = kismam.overall_score(kismam.assess(dev1))
    s2 = kismam.overall_score(kismam.assess(dev2))
    assert s0 > s1 > s2
    assert 0 <= s2 <= 100


def test_tolerance_gaussian_value():
    # dev == tol → z=1 → 100*exp(-0.5) ≈ 61
    dev = np.zeros(NUM_JOINTS)
    j = JOINT_KEYS.index("left_knee")
    dev[j] = kismam.DEFAULT_TOLERANCE_DEG["left_knee"]
    a = kismam.assess(dev)
    assert a[j].score == pytest.approx(61, abs=1)


def test_top_issues_picks_worst_three():
    dev = np.zeros(NUM_JOINTS)
    dev[JOINT_KEYS.index("left_knee")] = 40
    dev[JOINT_KEYS.index("right_hip")] = 30
    dev[JOINT_KEYS.index("left_elbow")] = 20
    top = kismam.top_issues(kismam.assess(dev), n=3)
    assert [t.key for t in top] == ["left_knee", "right_hip", "left_elbow"]
    assert top[0].score <= top[1].score <= top[2].score


def test_assess_rejects_wrong_length():
    with pytest.raises(ValueError):
        kismam.assess(np.zeros(NUM_JOINTS + 1))


def test_part_scores_average_within_part():
    dev = np.zeros(NUM_JOINTS)
    # 하체(무릎)만 크게 → 하체 점수만 낮아야
    dev[JOINT_KEYS.index("left_knee")] = 60
    dev[JOINT_KEYS.index("right_knee")] = 60
    ps = kismam.part_scores(kismam.assess(dev))
    assert ps["하체"] < ps["상체"]
    assert ps["상체"] == 100 and ps["코어"] == 100
