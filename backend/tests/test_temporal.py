"""시간축 폐색 보간 — 합성 시퀀스로 결정적 검증. AWS/모델 불필요."""

import numpy as np
import pytest

from sunity_shared.analysis import skeleton
from sunity_shared.analysis.temporal import occluded_mask, temporal_fill


def test_occluded_mask_flags_uncertainty_outlier():
    # 한 프레임만 불확실도가 폭발 → 폐색으로 잡힌다.
    angles = np.full((11, 1), 50.0)
    u = np.full((11, 1), 0.1)
    u[5, 0] = 100.0
    mask = occluded_mask(angles, u)
    assert mask[5, 0]
    assert mask.sum() == 1


def test_occluded_mask_flags_nan_angle_without_uncertainty():
    angles = np.array([[10.0], [np.nan], [30.0]])
    mask = occluded_mask(angles)
    assert mask[1, 0]
    assert mask.sum() == 1


def test_occluded_mask_reverts_when_relative_judgement_unreliable():
    # outlier_k 를 비현실적으로 낮추면 절반 이상이 '이상치' → 상대판정 폐기,
    # 진짜 NaN 프레임만 폐색으로 남는다.
    angles = np.zeros((10, 1))
    angles[0, 0] = np.nan
    u = np.arange(10, dtype=float).reshape(10, 1)
    mask = occluded_mask(angles, u, outlier_k=0.05)
    assert mask.sum() == 1 and mask[0, 0]


def test_temporal_fill_interpolates_occluded_frame():
    # 선형 추세 각도, 한 프레임만 NLF 가 엉뚱한 값 + 불확실도 폭발.
    T = 11
    angles = np.linspace(0, 100, T).reshape(T, 1)
    angles[5, 0] = 999.0
    u = np.full((T, 1), 0.1)
    u[5, 0] = 100.0
    filled = temporal_fill(angles, u, smooth_window=1)  # 보간만 — 스무딩 끔
    assert abs(filled[5, 0] - 50.0) < 1e-6  # 인접 보간 → 추세값 복원


def test_temporal_fill_interpolates_nan_without_uncertainty():
    angles = np.array([[10.0], [np.nan], [30.0]])
    filled = temporal_fill(angles, smooth_window=1)
    assert abs(filled[1, 0] - 20.0) < 1e-6


def test_temporal_fill_all_nan_column_becomes_zero():
    filled = temporal_fill(np.full((4, 1), np.nan), smooth_window=1)
    assert np.all(filled == 0.0)


def test_temporal_fill_smoothing_reduces_jitter():
    # 평탄 신호 + 1프레임 지터. 전부 신뢰(폐색 아님)라도 스무딩이 지터를 줄인다.
    angles = np.full((11, 1), 50.0)
    angles[5, 0] = 80.0
    u = np.full((11, 1), 0.1)
    filled = temporal_fill(angles, u, smooth_window=5)
    assert 50.0 < filled[5, 0] < 80.0


def test_temporal_fill_keeps_clean_linear_signal():
    # 선형 신호의 중앙부는 대칭 이동평균에도 그대로 보존된다.
    angles = np.linspace(0, 100, 21).reshape(21, 1)
    u = np.full((21, 1), 0.1)
    filled = temporal_fill(angles, u, smooth_window=5)
    assert np.allclose(filled[5:16, 0], angles[5:16, 0], atol=1e-6)


def test_temporal_fill_preserves_shape():
    rng = np.random.RandomState(0)
    angles = rng.rand(15, skeleton.NUM_JOINTS) * 100.0
    filled = temporal_fill(angles, np.full_like(angles, 0.1))
    assert filled.shape == angles.shape


def test_temporal_fill_rejects_mismatched_uncertainty():
    with pytest.raises(ValueError):
        temporal_fill(np.zeros((5, 2)), np.zeros((5, 3)))
