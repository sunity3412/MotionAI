"""Mode3 좌우 대칭 편차 — 결정적 검증. AWS 불필요."""

import numpy as np
import pytest

from sunity_shared.analysis.selfmotion import symmetry_deviation
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS


def test_perfect_symmetry_zero():
    a = np.tile(np.arange(NUM_JOINTS, dtype=float), (10, 1))
    # 좌우 같은 값으로 맞춤
    for lk, rk in [
        ("left_elbow", "right_elbow"),
        ("left_shoulder", "right_shoulder"),
        ("left_hip", "right_hip"),
        ("left_knee", "right_knee"),
    ]:
        a[:, JOINT_KEYS.index(rk)] = a[:, JOINT_KEYS.index(lk)]
    dev = symmetry_deviation(a)
    assert np.allclose(dev, 0.0)


def test_asymmetry_assigned_to_both_sides():
    a = np.zeros((5, NUM_JOINTS))
    a[:, JOINT_KEYS.index("left_knee")] = 30.0  # 오른쪽은 0 → 30 비대칭
    dev = symmetry_deviation(a)
    assert dev[JOINT_KEYS.index("left_knee")] == pytest.approx(30.0)
    assert dev[JOINT_KEYS.index("right_knee")] == pytest.approx(30.0)
    assert dev[JOINT_KEYS.index("left_elbow")] == pytest.approx(0.0)


def test_wrong_shape_raises():
    with pytest.raises(ValueError):
        symmetry_deviation(np.zeros((5, NUM_JOINTS + 2)))
