"""inter-thigh split 각도 측정 — 합성 정답 좌표로 결정적 검증. AWS 불필요.

belle 검증 방법 #1: 알려진 다리 기하 → 알려진 split 각(±2°) + 단조성 으로 측정
정확도를 증명한다. 점수 밴드 단언 0 — 구조적/기하 단언만(수치 채우기 금지).
split = 두 허벅지(hip→knee) 방향벡터 사이각: 모음≈0°, 직교≈90°, full split≈180°.
"""

import numpy as np
import pytest

from sunity_shared.analysis.features import max_split, split_angle_series
from sunity_shared.analysis.skeleton import kp_index

TOL_DEG = 2.0


def _frame(legs):
    """1프레임 (1,17,3) keypoint. legs = {keypoint_name: (x, y)} (z=0)."""
    kp = np.zeros((1, 17, 3), dtype=float)
    for name, (x, y) in legs.items():
        kp[0, kp_index(name)] = [float(x), float(y), 0.0]
    return kp


def _split_of(legs):
    return float(split_angle_series(_frame(legs))[0])


# ─────────────── 합성 정답: 알려진 기하 → 알려진 split (±2°) ───────────────


def test_legs_together_is_zero():
    """양 허벅지 평행(둘 다 수직 아래) → split ≈ 0°. 골반 너비 무관."""
    legs = {
        "left_hip": (-1, 0), "right_hip": (1, 0),
        "left_knee": (-1, -1), "right_knee": (1, -1),  # 둘 다 (0,-1) 방향
    }
    assert _split_of(legs) == pytest.approx(0.0, abs=TOL_DEG)


def test_perpendicular_is_ninety():
    """한 허벅지 수평·한 허벅지 수직 → split ≈ 90°."""
    legs = {
        "left_hip": (-1, 0), "right_hip": (1, 0),
        "left_knee": (-3, 0),   # 좌 허벅지 수평 (-1,0) 방향
        "right_knee": (1, -2),  # 우 허벅지 수직 (0,-1) 방향
    }
    assert _split_of(legs) == pytest.approx(90.0, abs=TOL_DEG)


def test_full_split_is_one_eighty():
    """양 허벅지가 반대 수평으로 일직선 → split ≈ 180° (full split)."""
    legs = {
        "left_hip": (-1, 0), "right_hip": (1, 0),
        "left_knee": (-2, 0),  # 좌 허벅지 (-1,0)
        "right_knee": (2, 0),  # 우 허벅지 (1,0)
    }
    assert _split_of(legs) == pytest.approx(180.0, abs=TOL_DEG)


def test_uses_z_coordinate():
    """3D 측정 확인 — z 를 무시하면 다른 값이 나오는 배치."""
    legs2d = {
        "left_hip": (0, 0), "right_hip": (0, 0),
        "left_knee": (0, -1), "right_knee": (0, -1),
    }
    kp = _frame(legs2d)
    # 우 무릎을 z 축으로만 벌림 → 2D(xy)로는 0°, 3D로는 90°.
    kp[0, kp_index("right_knee")] = [0.0, 0.0, -1.0]
    kp[0, kp_index("left_knee")] = [0.0, -1.0, 0.0]
    assert float(split_angle_series(kp)[0]) == pytest.approx(90.0, abs=TOL_DEG)


# ─────────────── 단조성: 더 벌릴수록 split 증가 ───────────────


def test_monotonic_increasing_with_spread():
    """좌 허벅지 고정·우 허벅지를 0°→180° 로 회전 → split 단조 증가."""
    splits = []
    for deg in range(0, 181, 15):
        rad = np.radians(deg)
        # 좌 허벅지: 수직 아래 (0,-1). 우 허벅지: deg 만큼 벌린 방향.
        legs = {
            "left_hip": (-1, 0), "right_hip": (1, 0),
            "left_knee": (-1, -1),
            "right_knee": (1 + np.sin(rad), -np.cos(rad)),
        }
        splits.append(_split_of(legs))
    diffs = np.diff(splits)
    assert np.all(diffs > 0), f"단조 증가 위반: {splits}"
    assert splits[0] == pytest.approx(0.0, abs=TOL_DEG)
    assert splits[-1] == pytest.approx(180.0, abs=TOL_DEG)


# ─────────────── NaN-safety ───────────────


def test_nan_keypoint_makes_frame_nan_others_finite():
    """한 프레임의 정의 keypoint 가 NaN → 그 프레임만 NaN, 나머지는 정상."""
    good = {
        "left_hip": (-1, 0), "right_hip": (1, 0),
        "left_knee": (-2, 0), "right_knee": (2, 0),
    }
    kp = np.concatenate([_frame(good), _frame(good), _frame(good)], axis=0)
    kp[1, kp_index("left_knee")] = [np.nan, np.nan, np.nan]
    out = split_angle_series(kp)
    assert out.shape == (3,)
    assert np.isnan(out[1])
    assert np.isfinite(out[0]) and out[0] == pytest.approx(180.0, abs=TOL_DEG)
    assert np.isfinite(out[2]) and out[2] == pytest.approx(180.0, abs=TOL_DEG)


def test_rejects_2d_input():
    with pytest.raises(ValueError):
        split_angle_series(np.zeros((1, 17, 2)))


def test_fourth_channel_ignored():
    """4채널(xyz+불확실도) → 불확실도 채널 무시, 좌표만 사용."""
    legs = {
        "left_hip": (-1, 0), "right_hip": (1, 0),
        "left_knee": (-2, 0), "right_knee": (2, 0),
    }
    kp3 = _frame(legs)
    kp4 = np.zeros((1, 17, 4), dtype=float)
    kp4[0, :, :3] = kp3[0]
    kp4[0, :, 3] = 9.9  # 불확실도 — split 에 영향 없어야
    assert float(split_angle_series(kp4)[0]) == pytest.approx(180.0, abs=TOL_DEG)


# ─────────────── max_split: peak 프레임/값 ───────────────


def test_max_split_picks_peak_frame_and_value():
    series = np.array([10.0, 45.0, 120.0, 90.0, 30.0])
    value, idx = max_split(series)
    assert idx == 2
    assert value == pytest.approx(120.0)


def test_max_split_ignores_nan():
    series = np.array([np.nan, 60.0, np.nan, 150.0, np.nan])
    value, idx = max_split(series)
    assert idx == 3
    assert value == pytest.approx(150.0)


def test_max_split_all_nan_returns_sentinel():
    value, idx = max_split(np.array([np.nan, np.nan]))
    assert idx == -1
    assert np.isnan(value)


def test_max_split_on_real_series():
    """split_angle_series → max_split 통합: peak 가 가장 벌린 프레임."""
    narrow = {
        "left_hip": (-1, 0), "right_hip": (1, 0),
        "left_knee": (-1, -1), "right_knee": (1, -1),  # ~0°
    }
    wide = {
        "left_hip": (-1, 0), "right_hip": (1, 0),
        "left_knee": (-2, 0), "right_knee": (2, 0),  # ~180°
    }
    kp = np.concatenate([_frame(narrow), _frame(wide), _frame(narrow)], axis=0)
    value, idx = max_split(split_angle_series(kp))
    assert idx == 1
    assert value == pytest.approx(180.0, abs=TOL_DEG)
