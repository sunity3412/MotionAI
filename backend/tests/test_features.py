"""관절각/특징벡터 — 합성 좌표로 결정적 검증. AWS 불필요."""

import numpy as np
import pytest

from sunity_shared.analysis import skeleton
from sunity_shared.analysis.features import (
    compute_joint_angles,
    feature_vector,
    fill_gaps,
)


def _straight_frame():
    """모든 keypoint 를 둔 한 프레임. 팔꿈치를 직각으로 세팅."""
    kp = np.zeros((17, 2), dtype=float)
    # left elbow 각도 = 어깨-팔꿈치-손목. 90도가 되도록 배치
    kp[skeleton.kp_index("left_shoulder")] = [0.0, 1.0]
    kp[skeleton.kp_index("left_elbow")] = [0.0, 0.0]
    kp[skeleton.kp_index("left_wrist")] = [1.0, 0.0]
    return kp


def test_right_angle_elbow():
    frames = _straight_frame()[None, :, :]  # (1,17,2)
    angles = compute_joint_angles(frames)
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert angles.shape == (1, skeleton.NUM_JOINTS)
    assert abs(angles[0, j] - 90.0) < 1e-6


def test_low_confidence_becomes_nan():
    kp = np.zeros((1, 17, 3), dtype=float)
    kp[0, skeleton.kp_index("left_shoulder")] = [0, 1, 0.9]
    kp[0, skeleton.kp_index("left_elbow")] = [0, 0, 0.05]  # 저신뢰 → 결측
    kp[0, skeleton.kp_index("left_wrist")] = [1, 0, 0.9]
    angles = compute_joint_angles(kp, min_conf=0.3)
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert np.isnan(angles[0, j])


def test_fill_gaps_interpolates_and_fills_all_nan_column():
    a = np.array([[10.0, np.nan], [np.nan, np.nan], [30.0, np.nan]])
    f = fill_gaps(a)
    assert f[1, 0] == pytest.approx(20.0)  # 선형보간
    assert np.all(f[:, 1] == 0.0)  # 전체 결측 → 0


def test_feature_vector_shape_and_layout():
    a = np.tile(np.arange(skeleton.NUM_JOINTS, dtype=float), (5, 1))  # (5,J)
    F = feature_vector(a, alpha=0.1, beta=0.02)
    J = skeleton.NUM_JOINTS
    assert F.shape == (5, 3 * J)
    # 상수 각도 → 속도/가속 0, 앞 J 열은 원본 각도
    assert np.allclose(F[:, :J], a)
    assert np.allclose(F[:, J:], 0.0)


def test_feature_vector_single_frame_no_crash():
    F = feature_vector(np.ones((1, skeleton.NUM_JOINTS)))
    assert F.shape == (1, 3 * skeleton.NUM_JOINTS)
