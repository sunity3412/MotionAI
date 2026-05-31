"""PoleAxisAligner 단위 테스트.

REVIEWS H-2 박제: scipy module-level import 금지 검증.
D-12: 폴 축 → Z 축 회전행렬 산출 + 키포인트 적용.

Test 1 은 scipy 부재 환경에서도 통과 (module load 만).
Test 2~8 은 scipy 의존 — 미설치 시 pytest.importorskip 으로 skip.
"""

from __future__ import annotations

import importlib
import sys

import numpy as np
import pytest


# ── Test 1: H-2 박제 — scipy 없이 모듈 import 성공 ──────────────────────

def test_module_import_without_scipy():
    """scipy 가 sys.modules 에 없어도 aligner 모듈 load 성공 (H-2 박제).

    scipy.spatial.transform.Rotation 은 compute_alignment_matrix 함수 내부에서만 import.
    scipy 미설치 환경에서도 통과해야 함.
    """
    saved_scipy = sys.modules.pop("scipy", None)
    saved_scipy_st = sys.modules.pop("scipy.spatial", None)
    saved_scipy_tr = sys.modules.pop("scipy.spatial.transform", None)
    try:
        # 이전에 import 된 모듈 캐시 제거
        sys.modules.pop("sunity_shared.analysis.pole.aligner", None)
        sys.modules.pop("sunity_shared.analysis.pole", None)

        # scipy 부재 상태에서 module import — ImportError 발생하면 안 됨
        module = importlib.import_module("sunity_shared.analysis.pole.aligner")
        assert hasattr(module, "compute_alignment_matrix"), (
            "compute_alignment_matrix 함수가 없음"
        )
        assert hasattr(module, "apply_alignment"), "apply_alignment 함수가 없음"
        # scipy 는 아직 import 되지 않았어야 함
        assert "scipy" not in sys.modules, (
            "scipy 가 module-level 에서 import 됐음 (H-2 위반)"
        )
    finally:
        if saved_scipy is not None:
            sys.modules["scipy"] = saved_scipy
        if saved_scipy_st is not None:
            sys.modules["scipy.spatial"] = saved_scipy_st
        if saved_scipy_tr is not None:
            sys.modules["scipy.spatial.transform"] = saved_scipy_tr


# ── scipy 의존 테스트 ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def scipy_module():
    """scipy importorskip — 미설치 시 이 fixture 사용하는 모든 테스트 skip."""
    return pytest.importorskip("scipy", reason="scipy 미설치 — aligner 테스트 skip")


@pytest.fixture(scope="module")
def compute_matrix_fn(scipy_module):
    """compute_alignment_matrix 함수 fixture."""
    from sunity_shared.analysis.pole.aligner import compute_alignment_matrix
    return compute_alignment_matrix


@pytest.fixture(scope="module")
def apply_fn(scipy_module):
    """apply_alignment 함수 fixture."""
    from sunity_shared.analysis.pole.aligner import apply_alignment
    return apply_alignment


# ── Test 2: identity alignment — pole 이미 Z 축에 정렬 ──────────────────

def test_identity_alignment(compute_matrix_fn):
    """pole_axis_direction = (0, 0, 1) → 회전행렬 = identity (3×3 단위행렬)."""
    from sunity_shared.analysis.pole.aligner import compute_alignment_matrix

    R = compute_alignment_matrix((0.0, 0.0, 1.0))

    expected = np.eye(3)
    assert R.shape == (3, 3), f"shape={R.shape}, (3,3) 기대"
    assert np.allclose(R, expected, atol=1e-6), (
        f"identity 기대\n실제:\n{R}"
    )


# ── Test 3: (0,1,0) → Z 축 정렬 후 (0,1,0) 벡터가 (0,0,1) 방향 ─────────

def test_alignment_y_to_z(compute_matrix_fn):
    """pole_axis_direction = (0, 1, 0) → R @ [0,1,0] ≈ [0,0,1]."""
    from sunity_shared.analysis.pole.aligner import compute_alignment_matrix

    R = compute_alignment_matrix((0.0, 1.0, 0.0))

    input_vec = np.array([0.0, 1.0, 0.0])
    result = R @ input_vec
    expected = np.array([0.0, 0.0, 1.0])

    assert np.allclose(result, expected, atol=1e-6), (
        f"R @ [0,1,0] = {result}, [0,0,1] 기대"
    )


# ── Test 4: anti-parallel — (0,0,-1) → 180° 회전 ────────────────────────

def test_alignment_anti_parallel(compute_matrix_fn):
    """pole_axis_direction = (0, 0, -1) → R @ [0,0,-1] ≈ [0,0,1] (180° 회전)."""
    from sunity_shared.analysis.pole.aligner import compute_alignment_matrix

    R = compute_alignment_matrix((0.0, 0.0, -1.0))

    input_vec = np.array([0.0, 0.0, -1.0])
    result = R @ input_vec
    expected = np.array([0.0, 0.0, 1.0])

    assert np.allclose(np.abs(result), np.abs(expected), atol=1e-6), (
        f"R @ [0,0,-1] = {result}, |[0,0,1]| 기대"
    )


# ── Test 5: apply_alignment key set 보존 ──────────────────────────────

def test_apply_alignment_preserves_keys(scipy_module):
    """keypoints_3d (dict 5 키) + R → output dict 5 키 (동일 set)."""
    from sunity_shared.analysis.pole.aligner import apply_alignment
    from sunity_shared.analysis.pose_frame import Keypoint3D

    keypoints = {
        "nose": Keypoint3D(0.0, 0.1, 0.2, confidence=0.9, uncertainty_proxy=0.1),
        "left_shoulder": Keypoint3D(0.3, 0.4, 0.1, confidence=0.85, uncertainty_proxy=0.15),
        "right_shoulder": Keypoint3D(-0.3, 0.4, 0.1, confidence=0.85, uncertainty_proxy=0.15),
        "left_hip": Keypoint3D(0.15, -0.1, 0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_hip": Keypoint3D(-0.15, -0.1, 0.0, confidence=0.9, uncertainty_proxy=0.1),
    }
    R = np.eye(3)  # identity

    result = apply_alignment(keypoints, R)

    assert set(result.keys()) == set(keypoints.keys()), (
        f"output key set={set(result.keys())}, input={set(keypoints.keys())} 기대"
    )
    assert len(result) == 5


# ── Test 6: apply_alignment identity R → 좌표 변화 없음 ─────────────────

def test_apply_alignment_numerical(scipy_module):
    """identity R + keypoints_3d → output 좌표 = input 좌표 (atol=1e-6)."""
    from sunity_shared.analysis.pole.aligner import apply_alignment
    from sunity_shared.analysis.pose_frame import Keypoint3D

    keypoints = {
        "nose": Keypoint3D(0.1, 0.2, 0.3, confidence=0.9, uncertainty_proxy=0.1),
        "left_hip": Keypoint3D(0.15, -0.1, 0.0, confidence=0.9, uncertainty_proxy=0.1),
    }
    R = np.eye(3)

    result = apply_alignment(keypoints, R)

    for name, kp_in in keypoints.items():
        kp_out = result[name]
        assert np.allclose(
            [kp_out.x, kp_out.y, kp_out.z],
            [kp_in.x, kp_in.y, kp_in.z],
            atol=1e-6,
        ), f"{name}: input={kp_in.x,kp_in.y,kp_in.z}, output={kp_out.x,kp_out.y,kp_out.z}"


# ── Test 7: compute_alignment_matrix → (3,3) + det ≈ ±1 ──────────────

def test_compute_alignment_matrix_returns_3x3(scipy_module):
    """어떤 pole_axis 입력이든 (3,3) ndarray 반환 + det ≈ ±1."""
    from sunity_shared.analysis.pole.aligner import compute_alignment_matrix

    test_cases = [
        (0.0, 0.0, 1.0),
        (0.0, 1.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 0.0, -1.0),
        (1.0, 1.0, 0.0),  # 정규화 전 벡터도 허용
    ]
    for vec in test_cases:
        R = compute_alignment_matrix(vec)
        assert R.shape == (3, 3), f"{vec}: shape={R.shape}"
        det = np.linalg.det(R)
        assert abs(abs(det) - 1.0) < 1e-6, f"{vec}: det={det:.6f}, ±1 기대"


# ── Test 8: zero vector → ValueError ─────────────────────────────────

def test_compute_alignment_matrix_zero_vector_raises(scipy_module):
    """zero vector → ValueError."""
    from sunity_shared.analysis.pole.aligner import compute_alignment_matrix

    with pytest.raises(ValueError, match="zero vector"):
        compute_alignment_matrix((0.0, 0.0, 0.0))
