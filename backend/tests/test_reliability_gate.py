"""Phase 1 H-4 게이트 단위 테스트 — Success #4 박제.

D-05: 각도 low reliability 마킹 정책 박제 (저신뢰 keypoint → 각도 low_reliability).
H-4: compute_angle_with_reliability 게이트 — 마킹이 목적, 계산 자체는 진행.
ANGLE_REQUIRED_KEYPOINTS: 각도 키 → 필수 keypoint 목록 상수.
"""

import pytest

from sunity_shared.analysis.pose_frame import (
    Keypoint3D,
    RELIABILITY_HIGH_THRESHOLD,
    RELIABILITY_MEDIUM_THRESHOLD,
)
from sunity_shared.analysis.reliability import (
    ANGLE_REQUIRED_KEYPOINTS,
    compute_angle_with_reliability,
)


def _make_keypoint(confidence: float) -> Keypoint3D:
    """테스트용 Keypoint3D (uncertainty_proxy = 1 - confidence)."""
    return Keypoint3D(
        x=0.0,
        y=0.0,
        z=0.0,
        confidence=confidence,
        uncertainty_proxy=1.0 - confidence,
    )


# ── Test 1 ────────────────────────────────────────────────────────────────

def test_compute_angle_with_reliability_high():
    """모든 필수 keypoint confidence >= RELIABILITY_MEDIUM_THRESHOLD → low_reliability=False."""
    angle_key = "left_knee_flex"
    required = ANGLE_REQUIRED_KEYPOINTS[angle_key]
    # 모든 keypoint 를 고신뢰로 설정 (>= 0.7)
    keypoints = {name: _make_keypoint(0.8) for name in required}

    compute_fn = lambda kps: 90.0  # noqa: E731

    result = compute_angle_with_reliability(angle_key, keypoints, compute_fn)

    assert "low_reliability" in result
    assert result["low_reliability"] is False
    assert "value" in result
    assert result["value"] == 90.0


# ── Test 2 ────────────────────────────────────────────────────────────────

def test_compute_angle_with_reliability_low():
    """필수 keypoint 1개 confidence < RELIABILITY_MEDIUM_THRESHOLD → low_reliability=True."""
    angle_key = "right_knee_flex"
    required = ANGLE_REQUIRED_KEYPOINTS[angle_key]

    # 대부분 고신뢰, 한 개만 저신뢰 (< 0.4)
    keypoints = {name: _make_keypoint(0.9) for name in required}
    low_confidence_kp = required[0]
    keypoints[low_confidence_kp] = _make_keypoint(0.1)

    compute_fn = lambda kps: 85.0  # noqa: E731

    result = compute_angle_with_reliability(angle_key, keypoints, compute_fn)

    assert result["low_reliability"] is True
    # value 는 None 이거나 계산값 — 마킹이 목적 (계산은 진행)
    assert "value" in result


# ── Test 3 ────────────────────────────────────────────────────────────────

def test_required_keypoints_per_angle_table():
    """ANGLE_REQUIRED_KEYPOINTS 최소 5개 entry + 각 entry 는 list[str]."""
    assert isinstance(ANGLE_REQUIRED_KEYPOINTS, dict)
    assert len(ANGLE_REQUIRED_KEYPOINTS) >= 5

    # 5개 필수 entry 존재 확인
    required_keys = {
        "left_knee_flex",
        "right_knee_flex",
        "left_elbow_flex",
        "right_elbow_flex",
        "hip_axis",
    }
    for key in required_keys:
        assert key in ANGLE_REQUIRED_KEYPOINTS, f"{key} 는 ANGLE_REQUIRED_KEYPOINTS 에 있어야 한다"

    # 각 entry 는 list[str]
    for key, kp_list in ANGLE_REQUIRED_KEYPOINTS.items():
        assert isinstance(kp_list, list), f"{key}: list 가 아님"
        assert len(kp_list) >= 2, f"{key}: keypoint 가 2개 이상이어야 한다"
        for kp in kp_list:
            assert isinstance(kp, str), f"{key}: keypoint name 이 str 이 아님"


# ── Test 4 ────────────────────────────────────────────────────────────────

def test_reliability_threshold_uses_pose_frame_constants():
    """reliability.py 가 pose_frame.RELIABILITY_HIGH_THRESHOLD 등을 재사용 (단일 진실)."""
    from sunity_shared.analysis.reliability import _LOW_THRESHOLD

    # reliability.py 의 임계값 상수가 pose_frame 상수와 같은 값 사용
    # (MEDIUM_THRESHOLD 기반으로 low_reliability 마킹)
    assert _LOW_THRESHOLD == RELIABILITY_MEDIUM_THRESHOLD
