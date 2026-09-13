"""quick-260913-udr Task 1 — rot180 inversion 순수 모듈: 회전·역매핑·불일치 계기.

검증 대상: sunity_shared/analysis/inversion_rot180.py (numpy 만 — 로컬).
GPU 실경로(RunPod Pod)는 여기서 검증하지 않는다 — Pod 0대. SUMMARY 가 승계한다.

Behavior (260913-udr-PLAN Task 1, 코디네이터 정정 1 반영):
  1. 회전 두 번 = 항등. 한 번 = 프레임별 np.rot90(f, 2). C-contiguous, dtype 보존.
  2. 픽셀 규약과 좌표 규약이 일치 — 켜진 픽셀의 회전 위치를 unrotate 하면 원좌표.
  3. unrotate 는 자기역원 (프레임 밖 좌표·NaN 포함, NaN 은 NaN 으로 통과).
  4. 불일치는 torso 정규화라 해상도 무관.
  5. torso 는 **클립 중앙값** 하나 — 붕괴 프레임(torso 0)에서 폭주하지 않고, 유효
     torso 가 하나도 없으면 전부 NaN (inf 금지).
  6. 대표 사례 재현: 한 관절 421px / torso 561px = 0.75 (MEASUREMENTS §5).
  7. choose_pass 사유 5종이 순서대로 난다.
  8. 180° 회전은 손잡이(chirality)를 보존하고 수평 flip 은 뒤집는다 — 좌우 인덱스
     스왑이 필요 없는 이유를 박제.
  9. 순수성: torch / cv2 / onnxruntime / rtmlib / boto3 import 0, inversion_warp import 0.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from sunity_shared.analysis import inversion_rot180 as ir
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES

# COCO body 인덱스 (RTMW 133 의 선두 17 = COCO-17 순서)
_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP = 5, 6, 11, 12
_R_ELBOW = 8


def _body17(shoulder_y: float = 100.0, hip_y: float = 300.0) -> np.ndarray:
    """비대칭 골격 (17,2). 왼어깨 x < 오른어깨 x. torso = |hip_y - shoulder_y|."""
    k = np.zeros((17, 2), dtype=float)
    k[:, 0] = 200.0
    k[:, 1] = (shoulder_y + hip_y) / 2.0
    k[_L_SHOULDER] = (150.0, shoulder_y)
    k[_R_SHOULDER] = (250.0, shoulder_y)
    k[_L_HIP] = (170.0, hip_y)
    k[_R_HIP] = (230.0, hip_y)
    k[7] = (120.0, shoulder_y + 40.0)  # left_elbow
    k[_R_ELBOW] = (280.0, shoulder_y + 40.0)
    return k


def _cross_z(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def _handedness(k: np.ndarray) -> float:
    """어깨벡터(오른어깨-왼어깨) x 몸통벡터(엉덩이중점-어깨중점) 의 2D 외적 부호."""
    shoulder_vec = k[_R_SHOULDER] - k[_L_SHOULDER]
    torso_vec = (k[_L_HIP] + k[_R_HIP]) / 2.0 - (k[_L_SHOULDER] + k[_R_SHOULDER]) / 2.0
    return np.sign(_cross_z(shoulder_vec, torso_vec))


# ── 1. 회전 ────────────────────────────────────────────────────────────────

def test_rotate_twice_is_identity_and_once_matches_rot90():
    rng = np.random.default_rng(7)
    frames = rng.integers(0, 256, size=(3, 5, 8, 3), dtype=np.uint8)
    once = ir.rotate_frames_180(frames)
    assert once.dtype == frames.dtype
    assert once.flags["C_CONTIGUOUS"]
    for t in range(3):
        assert np.array_equal(once[t], np.rot90(frames[t], 2))
    assert np.array_equal(ir.rotate_frames_180(once), frames)
    with pytest.raises(ValueError):
        ir.rotate_frames_180(frames[0])  # ndim 3 — (T,H,W,C) 만 받는다


# ── 2. 픽셀 규약 = 좌표 규약 ──────────────────────────────────────────────

def test_pixel_and_point_conventions_agree():
    H, W = 4, 6
    frame = np.zeros((1, H, W, 1), dtype=np.uint8)
    frame[0, 1, 2, 0] = 255  # (x=2, y=1) 한 점을 켠다
    rotated = ir.rotate_frames_180(frame)
    ys, xs = np.nonzero(rotated[0, :, :, 0])
    assert (int(xs[0]), int(ys[0])) == (3, 2)  # 켜진 픽셀은 (x=3, y=2) 에 있다
    back = ir.unrotate_points_180(np.array([[3.0, 2.0]]), W, H)
    assert np.array_equal(back, np.array([[2.0, 1.0]]))


# ── 3. 자기역원 ────────────────────────────────────────────────────────────

def test_unrotate_is_involution_including_outside_and_nan():
    W, H = 640, 360
    pts = np.array(
        [[0.0, 0.0], [639.0, 359.0], [12.5, 200.25], [-40.0, 500.0], [900.0, -3.0],
         [np.nan, 10.0], [np.nan, np.nan]]
    )
    twice = ir.unrotate_points_180(ir.unrotate_points_180(pts, W, H), W, H)
    finite = np.isfinite(pts)
    assert np.array_equal(twice[finite], pts[finite])
    assert np.isnan(twice[~finite]).all()  # NaN 은 마스킹하지 않고 NaN 으로 통과
    assert np.isnan(twice).sum() == 3


# ── 4. 해상도 무관 ────────────────────────────────────────────────────────

def test_disagreement_is_resolution_invariant():
    rng = np.random.default_rng(3)
    a = np.stack([_body17() + rng.normal(0, 5, (17, 2)) for _ in range(6)])
    b = np.stack([_body17() + rng.normal(0, 5, (17, 2)) for _ in range(6)])
    d_small = ir.joint_disagreement(a, b)
    d_big = ir.joint_disagreement(a * 3.7, b * 3.7)
    assert d_small.shape == (6, 17)
    assert np.all(np.isfinite(d_small))
    assert np.allclose(d_small, d_big)


# ── 5. 클립 중앙값 torso — 붕괴 프레임에서 폭주 금지, inf 금지 ─────────────

def test_disagreement_uses_clip_median_torso_never_inf():
    # 코디네이터 정정 1: 프레임별 torso 는 붕괴 프레임에서 0 → 불일치 p99 5.98e10 폭주.
    # 클립 중앙값(하나의 스칼라)이면 같은 데이터에서 p99 3.191 로 정상화된다.
    T = 9
    a = np.stack([_body17() for _ in range(T)])
    b = np.stack([_body17() for _ in range(T)])
    b[:, _R_ELBOW, 0] += 100.0  # 모든 프레임에서 오른팔꿈치만 100px 벌어짐

    # 프레임 4 의 2차 패스가 붕괴 — 어깨·엉덩이가 한 점에 뭉개져 torso 0.
    b[4, [_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP]] = (200.0, 200.0)
    # 프레임 6 의 1차 패스는 엉덩이 결측(NaN) — 이 프레임 torso 는 풀에 못 들어간다.
    a[6, _L_HIP] = np.nan

    d = ir.joint_disagreement(a, b)
    assert d.shape == (T, 17)
    assert not np.isinf(d).any()  # inf 는 계기의 거짓말 — 절대 금지
    # 클립 torso 중앙값 = 200 (정상 프레임 전부 200) → 붕괴 프레임도 그 값으로 나눈다.
    assert d[4, _R_ELBOW] == pytest.approx(100.0 / 200.0)
    assert np.isfinite(d[4, :]).all()
    # 결측 관절은 그 관절만 NaN, 같은 프레임의 다른 관절은 유효.
    assert np.isnan(d[6, _L_HIP])
    assert d[6, _R_ELBOW] == pytest.approx(0.5)
    assert d[0, _R_ELBOW] == pytest.approx(0.5)

    # 유효 torso 가 클립 어디에도 없으면 전부 NaN (0 나눗셈 없이).
    zero = np.zeros((T, 17, 2))
    d_zero = ir.joint_disagreement(zero, zero)
    assert np.isnan(d_zero).all()
    nan_clip = np.full((T, 17, 2), np.nan)
    d_nan = ir.joint_disagreement(nan_clip, a)
    assert np.isnan(d_nan).all()  # 한쪽이 전부 결측이면 불일치를 잴 쌍이 없다


# ── 6. 대표 사례 (MEASUREMENTS §5) ────────────────────────────────────────

def test_representative_case_right_elbow_0_75_torso():
    # t=8.1s: right_elbow(관측 실패) 421px = 0.75 torso, torso 561px.
    T = 5
    a = np.stack([_body17(shoulder_y=100.0, hip_y=661.0) for _ in range(T)])
    b = a.copy()
    b[:, _R_ELBOW, 0] += 421.0
    d = ir.joint_disagreement(a, b)
    assert d[2, _R_ELBOW] == pytest.approx(0.75, abs=1e-2)
    assert d[2, _L_HIP] == pytest.approx(0.0)

    summary = ir.disagreement_summary(d)
    assert summary["valid_pairs"] == T * 17
    assert summary["per_joint"]["right_elbow"][0] == pytest.approx(0.75, abs=1e-2)
    assert summary["max"] == pytest.approx(0.75, abs=1e-2)
    assert list(summary["per_joint"].keys()) == list(KEYPOINT_NAMES)

    empty = ir.disagreement_summary(np.full((T, 17), np.nan))
    assert empty["valid_pairs"] == 0
    assert np.isnan(empty["p50"]) and np.isnan(empty["p90"]) and np.isnan(empty["max"])


# ── 7. choose_pass 사유 순서 ───────────────────────────────────────────────

def test_choose_pass_reasons_in_order():
    W, H = 640, 360
    good = np.zeros((133, 3), dtype=np.float32)
    good[:, 0] = 300.0
    good[:, 1] = 200.0
    scores = np.full((133,), 0.9, dtype=np.float32)
    first = (good.copy(), scores)

    assert ir.choose_pass(None, (good, scores), W, H) == ir.PassChoice(False, ir.REASON_FIRST_MISSING)
    assert ir.choose_pass(first, None, W, H) == ir.PassChoice(False, ir.REASON_SECOND_MISSING)

    nonfinite = good.copy()
    nonfinite[40, 0] = np.nan  # body-17 밖(얼굴)이어도 133 전량 유한이어야 한다
    assert ir.choose_pass(first, (nonfinite, scores), W, H).reason == ir.REASON_SECOND_NONFINITE

    out = good.copy()
    out[_R_ELBOW, 0] = W * 2.0  # body-17 이 허용 마진(25%) 밖으로 대탈출
    assert ir.choose_pass(first, (out, scores), W, H).reason == ir.REASON_SECOND_OUT_OF_BOUNDS

    slightly_out = good.copy()
    slightly_out[_R_ELBOW, 0] = -W * ir.BOUNDS_TOLERANCE * 0.5  # 마진 안 — 정상 좌표
    adopted = ir.choose_pass(first, (slightly_out, scores), W, H)
    assert adopted == ir.PassChoice(True, ir.REASON_ADOPTED)


# ── 8. 손잡이 보존 — 회전은 det=+1, flip 은 det=-1 ─────────────────────────

def test_rotation_preserves_handedness_flip_does_not():
    W, H = 640, 360
    k = _body17()
    base = _handedness(k)
    assert base != 0.0

    rotated = ir.unrotate_points_180(k, W, H)
    assert _handedness(rotated) == base  # 180° 회전 — 좌우 인덱스 스왑 불필요

    flipped = k.copy()
    flipped[:, 0] = (W - 1) - flipped[:, 0]  # x 만 뒤집는 수평 flip
    assert _handedness(flipped) == -base  # flip 이라면 스왑이 필요했을 것


# ── 9. 순수성 ─────────────────────────────────────────────────────────────

class TestPurity:
    """numpy 만. heavy 어댑터 의존 0, PR 워프 모듈 의존 0 (R-8)."""

    def test_no_heavy_imports(self):
        for line in inspect.getsource(ir).splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for mod in ("torch", "cv2", "onnxruntime", "rtmlib", "boto3"):
                assert not stripped.startswith((f"import {mod}", f"from {mod}")), line

    def test_no_inversion_warp_dependency(self):
        for line in inspect.getsource(ir).splitlines():
            if line.strip().startswith("#"):
                continue
            assert "inversion_warp" not in line, line
