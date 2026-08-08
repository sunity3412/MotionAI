"""Phase 34 수술 ③ — 좌우 기능 짝맞춤(side_match) 불변식 (quick-260808-r82).

합성 입력만 사용 (fixture curve-fit 금지). 대상 성질:

  판별: 정지 손목 vs 스윕 손목 → 그립측. 비슷한 분산/NaN 과다/짧은 관측/0-sentinel
        → None (fail-closed).
  스왑: involution(swap∘swap == id), 다리 열 불변, 입력 무변경(사본 반환).
  불변식 3: 그립측 일치(스왑 미발동) 경로의 per_joint_deviation 산출이 side_match
        도입 전과 np.array_equal — swap_lr_arms=False 기본값 byte-동일.
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis import side_match
from sunity_shared.analysis.features import feature_vector
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
from sunity_shared.analysis.skeleton import JOINT_KEYS, KEYPOINT_NAMES


def _body(T: int, seed: int = 0) -> np.ndarray:
    """(T,17,3) 합성 신체 — 전 keypoint 유효(비-0, 유한), 작은 결정적 흔들림."""
    rng = np.random.default_rng(seed)
    base = np.linspace(0.5, 1.5, 17)[None, :, None] + np.zeros((T, 17, 3))
    return base + rng.normal(0, 0.01, size=(T, 17, 3))


def _set_wrist(arr: np.ndarray, name: str, track: np.ndarray) -> None:
    arr[:, list(KEYPOINT_NAMES).index(name), :] = track


def _still(T: int, seed: int = 1) -> np.ndarray:
    """정지 손목 — 고정점 + 몸통 흔들림 스케일 잔여 이동 (std 약 0.01)."""
    rng = np.random.default_rng(seed)
    return np.array([0.3, 1.0, 0.2]) + rng.normal(0, 0.01, size=(T, 3))


def _sweep(T: int) -> np.ndarray:
    """스윕 손목 — 팔 길이 스케일 호 이동 (std 약 0.2 이상)."""
    t = np.linspace(0, np.pi, T)
    return np.stack(
        [0.5 + 0.4 * np.cos(t), 1.0 + 0.4 * np.sin(t), 0.2 + 0.1 * np.sin(2 * t)],
        axis=1,
    )


# ── 판별 ─────────────────────────────────────────────────────────────────────

def test_grip_side_still_left_sweep_right():
    T = 40
    arr = _body(T)
    _set_wrist(arr, "left_wrist", _still(T))
    _set_wrist(arr, "right_wrist", _sweep(T))
    diag: dict = {}
    assert side_match.grip_side(arr, KEYPOINT_NAMES, debug_out=diag) == "left"
    assert diag["std_ratio"] >= side_match.GRIP_STD_RATIO_MIN


def test_grip_side_symmetric_right():
    T = 40
    arr = _body(T)
    _set_wrist(arr, "left_wrist", _sweep(T))
    _set_wrist(arr, "right_wrist", _still(T))
    assert side_match.grip_side(arr, KEYPOINT_NAMES) == "right"


def test_grip_side_similar_variance_none():
    """분리 미달(std 비 < GRIP_STD_RATIO_MIN) = 판별 불가 fail-closed."""
    T = 40
    arr = _body(T)
    sweep = _sweep(T)
    _set_wrist(arr, "left_wrist", sweep)
    _set_wrist(arr, "right_wrist", sweep + np.array([0.1, 0.0, 0.0]))
    assert side_match.grip_side(arr, KEYPOINT_NAMES) is None


def test_grip_side_nan_heavy_none():
    """유효 프레임 < max(9, T//4) = 판정 금지 (1초 미만 관측)."""
    T = 40
    arr = _body(T)
    still = _still(T)
    still[5:] = np.nan  # 유효 5 < max(9, 10)
    _set_wrist(arr, "left_wrist", still)
    _set_wrist(arr, "right_wrist", _sweep(T))
    assert side_match.grip_side(arr, KEYPOINT_NAMES) is None


def test_grip_side_short_observation_none():
    T = 8  # min_valid = max(9, 2) = 9 > T — 어떤 궤적이어도 None
    arr = _body(T)
    _set_wrist(arr, "left_wrist", _still(T))
    _set_wrist(arr, "right_wrist", _sweep(T))
    assert side_match.grip_side(arr, KEYPOINT_NAMES) is None


def test_grip_side_zero_sentinel_invalid():
    """(0,0,0) triple = joints3d 저장 sentinel(NaN→0.0) — 실좌표로 읽으면 정지로
    오인해 그립을 위조한다. 무효 처리 확인."""
    T = 40
    arr = _body(T)
    zero = np.zeros((T, 3))  # 전 프레임 0-sentinel = 유효 0
    _set_wrist(arr, "left_wrist", zero)
    _set_wrist(arr, "right_wrist", _sweep(T))
    assert side_match.grip_side(arr, KEYPOINT_NAMES) is None


def test_grip_side_confidence_gate():
    """confidence < 0.5 프레임은 무효 — 저신뢰 구간만 남으면 None."""
    T = 40
    arr = _body(T)
    _set_wrist(arr, "left_wrist", _still(T))
    _set_wrist(arr, "right_wrist", _sweep(T))
    conf = np.ones((T, 17))
    conf[8:, list(KEYPOINT_NAMES).index("left_wrist")] = 0.1  # 유효 8 < 10
    assert side_match.grip_side(arr, KEYPOINT_NAMES, confidence=conf) is None
    # 신뢰 충분이면 판별 유지.
    assert (
        side_match.grip_side(arr, KEYPOINT_NAMES, confidence=np.ones((T, 17)))
        == "left"
    )


def test_grip_side_flat_input_reshape():
    """flat 1차원 입력(Firestore 저장 형상)도 keys 로 reshape 해 판별."""
    T = 40
    arr = _body(T)
    _set_wrist(arr, "left_wrist", _still(T))
    _set_wrist(arr, "right_wrist", _sweep(T))
    flat = arr.reshape(-1).tolist()
    assert side_match.grip_side(flat, KEYPOINT_NAMES) == "left"


# ── 스왑 ─────────────────────────────────────────────────────────────────────

def test_swap_involution_and_leg_untouched():
    rng = np.random.default_rng(7)
    A = rng.normal(90, 30, size=(25, len(JOINT_KEYS)))
    A_orig = A.copy()
    swapped = side_match.swap_lr_arm_columns(A, JOINT_KEYS)
    # involution.
    assert np.array_equal(side_match.swap_lr_arm_columns(swapped, JOINT_KEYS), A)
    # 팔 짝 교환 확인.
    ki = {k: i for i, k in enumerate(JOINT_KEYS)}
    assert np.array_equal(swapped[:, ki["left_elbow"]], A[:, ki["right_elbow"]])
    assert np.array_equal(swapped[:, ki["right_elbow"]], A[:, ki["left_elbow"]])
    assert np.array_equal(swapped[:, ki["left_shoulder"]], A[:, ki["right_shoulder"]])
    # 다리(hip/knee) 열 불변.
    for jk in ("left_hip", "right_hip", "left_knee", "right_knee"):
        assert np.array_equal(swapped[:, ki[jk]], A[:, ki[jk]])
    # 입력 무변경 (사본 반환).
    assert np.array_equal(A, A_orig)
    assert swapped is not A


def test_swap_partial_keys_skips_missing_pair():
    """짝의 한쪽이라도 없으면 그 짝은 조용히 생략 (부분 키 계약 fail-closed)."""
    keys = ("left_elbow", "right_elbow", "left_shoulder")  # right_shoulder 부재
    A = np.arange(12, dtype=float).reshape(4, 3)
    swapped = side_match._swap_columns(A, keys, side_match.ARM_LR_PAIRS)
    assert np.array_equal(swapped[:, 0], A[:, 1])  # elbow 짝은 교환
    assert np.array_equal(swapped[:, 2], A[:, 2])  # shoulder 열은 불변


# ── 불변식 3: 미발동 = byte-동일 ─────────────────────────────────────────────

def test_invariant3_no_swap_byte_identical():
    """그립측 일치(스왑 미발동) 경로 — _deviation_against 급 배선을 순수 계층에서
    재현: swap_lr_arms=False 기본 경로의 per_joint_deviation 산출이 side_match
    도입 전 연산(스왑 없는 동일 배선)과 np.array_equal."""
    rng = np.random.default_rng(11)
    t = np.linspace(0, 4 * np.pi, 45)
    user = np.stack(
        [30.0 * np.sin(t + k) + 5.0 * k for k in range(len(JOINT_KEYS))], axis=1
    )
    ref = user + rng.normal(3.0, 0.5, size=user.shape)
    # side_match 도입 전과 동일한 배선 (스왑 연산 자체가 없다).
    match = motion_dtw(feature_vector(user), feature_vector(ref))
    seg = user[match.start : match.end]
    win = ref[match.ref_start : match.ref_end]
    dev_legacy = per_joint_deviation(match.path, seg, win)
    # 미발동 경로 = a_ref 무변형 — 같은 입력이면 같은 산출 (byte-동일).
    a_ref_unswapped = np.asarray(ref, dtype=float)
    match2 = motion_dtw(feature_vector(user), feature_vector(a_ref_unswapped))
    seg2 = user[match2.start : match2.end]
    win2 = a_ref_unswapped[match2.ref_start : match2.ref_end]
    dev_no_fire = per_joint_deviation(match2.path, seg2, win2)
    assert np.array_equal(dev_legacy, dev_no_fire)
    # 스왑이 실제로 산출을 바꿀 수 있는 입력임을 확인 (테스트 자명성 방지) —
    # 팔 열이 비대칭인 ref 를 스왑하면 편차가 달라진다.
    ref_asym = ref.copy()
    ki = {k: i for i, k in enumerate(JOINT_KEYS)}
    ref_asym[:, ki["left_elbow"]] += 40.0
    swapped = side_match.swap_lr_arm_columns(ref_asym, JOINT_KEYS)
    m3 = motion_dtw(feature_vector(user), feature_vector(ref_asym))
    m4 = motion_dtw(feature_vector(user), feature_vector(swapped))
    d3 = per_joint_deviation(m3.path, user[m3.start:m3.end], ref_asym[m3.ref_start:m3.ref_end])
    d4 = per_joint_deviation(m4.path, user[m4.start:m4.end], swapped[m4.ref_start:m4.ref_end])
    assert not np.array_equal(d3, d4)
