"""MotionDTW — 합성 시퀀스로 결정적 검증. AWS 불필요."""

import numpy as np
import pytest

from sunity_shared.analysis.motiondtw import (
    dtw,
    find_action_segment,
    motion_dtw,
    per_joint_deviation,
)


def _wave(n, phase=0.0, amp=1.0):
    t = np.linspace(0, 2 * np.pi, n)
    return np.stack([amp * np.sin(t + phase), amp * np.cos(t + phase)], axis=1)


def test_identical_distance_zero():
    X = _wave(30)
    d, path = dtw(X, X)
    assert d == pytest.approx(0.0, abs=1e-9)
    assert path[0] == (0, 0) and path[-1] == (29, 29)


def test_similar_less_than_dissimilar():
    ref = _wave(40)
    near = _wave(40, phase=0.05)
    far = _wave(40, phase=np.pi)  # 역위상
    d_near, _ = dtw(near, ref)
    d_far, _ = dtw(far, ref)
    assert d_near < d_far


def test_segment_search_finds_embedded_motion():
    ref = _wave(30)
    idle = np.zeros((25, 2))
    user = np.concatenate([idle, _wave(30), idle])  # 앞뒤 대기 구간
    s, e = find_action_segment(user, ref, radius=8)
    # 동작은 대략 25~55 구간 — 시작이 대기 끝 근처여야
    assert 15 <= s <= 35
    assert (e - s) == len(ref)


def test_motion_dtw_trims_and_aligns():
    ref = _wave(30)
    user = np.concatenate([np.zeros((20, 2)), _wave(30), np.zeros((10, 2))])
    m = motion_dtw(user, ref, radius=8)
    assert m.end - m.start == len(ref)
    assert m.distance < 0.05  # 동작 자체는 거의 동일
    assert m.path[0][1] == 0 and m.path[-1][1] == len(ref) - 1


def test_per_joint_deviation_picks_offset_joint():
    T, J = 20, 3
    A_ref = np.zeros((T, J))
    A_user = np.zeros((T, J))
    A_user[:, 1] = 12.0  # 1번 관절만 12도 벗어남
    path = [(i, i) for i in range(T)]
    dev = per_joint_deviation(path, A_user, A_ref)
    assert dev[0] == pytest.approx(0.0)
    assert dev[1] == pytest.approx(12.0)
    assert dev[2] == pytest.approx(0.0)


def test_empty_sequence_raises():
    with pytest.raises(ValueError):
        dtw(np.zeros((0, 2)), _wave(5))
