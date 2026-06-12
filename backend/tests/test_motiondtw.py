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


def test_per_joint_deviation_identical_sequences_zero():
    """같은 시퀀스 self-compare → 모든 관절 deviation = 0 (만점 보장).

    gsd-debug same-video-score-mismatch (2026-06-12) 회귀 방지.
    같은 영상을 두 번 분석했을 때 frame 단위 noise 가 없다면 KISMAM 만점 (score=100)
    가 보장되어야 한다.
    """
    T, J = 30, 8
    A = np.cumsum(np.ones((T, J)) * 3.0, axis=0)  # 시간에 따라 단조 증가
    path = [(i, i) for i in range(T)]
    dev = per_joint_deviation(path, A.copy(), A.copy())
    assert np.allclose(dev, 0.0), f"identical sequence deviation must be 0, got {dev}"


def test_per_joint_deviation_robust_to_outlier_frames():
    """RTMW outlier frame 에 robust — mean 이 아니라 median 사용.

    gsd-debug same-video-score-mismatch (2026-06-12): RTMW 가 inverted 자세에서
    소수 frame 에 60° 짜리 outlier 를 만들고 나머지 frame 은 일치하는 상황.
    mean deviation 이면 60·k/T 로 score 가 폭락 — median 은 outlier 영향 차단.

    시나리오: 20 frame 중 18 frame 은 user == ref (0° 차이), 2 frame 만 60° 차이.
      mean = 60 * 2/20 = 6.0
      median = 0.0   ← 이 함수가 반환해야 할 값
    """
    T, J = 20, 3
    A_ref = np.zeros((T, J))
    A_user = np.zeros((T, J))
    # 2개 frame 에 joint 1 만 60° outlier
    A_user[3, 1] = 60.0
    A_user[7, 1] = 60.0
    path = [(i, i) for i in range(T)]
    dev = per_joint_deviation(path, A_user, A_ref)
    # median 이면 18/20 = 90% 가 0 이므로 median = 0.
    assert dev[0] == pytest.approx(0.0)
    assert dev[1] == pytest.approx(0.0), (
        f"outlier 2 frames in 20 should not move median — got {dev[1]:.2f}"
    )
    assert dev[2] == pytest.approx(0.0)


def test_per_joint_deviation_picks_persistent_offset_over_noise():
    """일관된 mean 차이는 잡고, 산발적 noise 는 무시.

    user joint 1 이 ref 보다 일관되게 ~10° 더 큼 (실제 자세 차이) +
    user joint 0 이 1 frame 만 50° outlier (RTMW noise).
    → joint 1 = 10° (실신호), joint 0 = 0° (noise 무시).
    """
    T, J = 30, 2
    A_ref = np.zeros((T, J))
    A_user = np.zeros((T, J))
    A_user[:, 1] = 10.0  # 일관된 10° 차이
    A_user[5, 0] = 50.0  # 단 1 frame outlier on joint 0
    path = [(i, i) for i in range(T)]
    dev = per_joint_deviation(path, A_user, A_ref)
    assert dev[0] == pytest.approx(0.0), f"single-frame noise should be ignored, got {dev[0]:.2f}"
    assert dev[1] == pytest.approx(10.0), f"persistent 10° offset must be preserved, got {dev[1]:.2f}"


def test_empty_sequence_raises():
    with pytest.raises(ValueError):
        dtw(np.zeros((0, 2)), _wave(5))
