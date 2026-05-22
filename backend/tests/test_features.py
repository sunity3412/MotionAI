"""3D 관절각/특징벡터/불확실도 — 합성 좌표로 결정적 검증. AWS 불필요."""

import numpy as np
import pytest

from sunity_shared.analysis import skeleton
from sunity_shared.analysis.features import (
    compute_joint_angles,
    feature_vector,
    fill_gaps,
    joint_uncertainty,
)


def _straight_frame():
    """3D keypoint 한 프레임. 왼쪽 팔꿈치를 직각(90도)으로 배치."""
    kp = np.zeros((17, 3), dtype=float)
    kp[skeleton.kp_index("left_shoulder")] = [0.0, 1.0, 0.0]
    kp[skeleton.kp_index("left_elbow")] = [0.0, 0.0, 0.0]
    kp[skeleton.kp_index("left_wrist")] = [1.0, 0.0, 0.0]
    return kp


def test_right_angle_elbow():
    frames = _straight_frame()[None, :, :]  # (1,17,3)
    angles = compute_joint_angles(frames)
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert angles.shape == (1, skeleton.NUM_JOINTS)
    assert abs(angles[0, j] - 90.0) < 1e-6


def test_uses_z_coordinate():
    """z 를 버리면 0도가 나오는 배치 — 진짜 3D 계산임을 확인."""
    kp = np.zeros((1, 17, 3), dtype=float)
    kp[0, skeleton.kp_index("left_shoulder")] = [0, 1, 0]
    kp[0, skeleton.kp_index("left_elbow")] = [0, 0, 0]
    kp[0, skeleton.kp_index("left_wrist")] = [0, 1, 1]
    angles = compute_joint_angles(kp)
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert abs(angles[0, j] - 45.0) < 1e-6


def test_fourth_channel_ignored_for_angles():
    """4채널(xyz+불확실도) 입력 — 불확실도 채널은 각도 계산에서 무시."""
    kp = np.zeros((1, 17, 4), dtype=float)
    kp[0, :, :3] = _straight_frame()
    kp[0, :, 3] = 9.9  # 불확실도 — 각도에 영향 없어야
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert abs(compute_joint_angles(kp)[0, j] - 90.0) < 1e-6


def test_rejects_2d_input():
    with pytest.raises(ValueError):
        compute_joint_angles(np.zeros((1, 17, 2)))


def test_joint_uncertainty_takes_max_of_defining_keypoints():
    kp = np.zeros((1, 17, 4), dtype=float)
    # left_elbow 각 = shoulder/elbow/wrist 3점. 그 중 하나만 큰 불확실도.
    kp[0, skeleton.kp_index("left_shoulder"), 3] = 0.2
    kp[0, skeleton.kp_index("left_elbow"), 3] = 0.9
    kp[0, skeleton.kp_index("left_wrist"), 3] = 0.1
    u = joint_uncertainty(kp)
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert u[0, j] == pytest.approx(0.9)  # 3점 중 최댓값


def test_joint_uncertainty_zero_without_uncertainty_channel():
    u = joint_uncertainty(np.zeros((3, 17, 3)))
    assert u.shape == (3, skeleton.NUM_JOINTS)
    assert np.all(u == 0.0)


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
