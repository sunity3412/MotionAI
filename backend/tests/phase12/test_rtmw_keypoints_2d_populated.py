"""Phase 12 Wave 0A R1 (Codex 직접 리뷰 2026-06-10) — RTMW adapter keypoints_2d 채움 검증.

기존: rtmw_133_to_coco17.py:226 `keypoints_2d=None` → Phase 12 KeypointOverlay 의
데이터 source 부재. 본 test 가 R1 fix 회귀 차단.

cite: 12-00-PLAN.md Task T1 + Codex iter-1 R1 + RESEARCH §Pattern 1.
"""

from __future__ import annotations

import numpy as np
import pytest

from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import (
    _build_keypoints_2d_from_rtmw,
    convert_rtmw_keypoints_to_coco17_and_pole_ext,
)
from sunity_shared.analysis.pose_frame import Keypoint2D, PoleAxis


# ── fixture: 133 keypoint 합성 array ──────────────────────────────────────────

def _make_synthetic_keypoints_133(*, w_px: int = 1920, h_px: int = 1080) -> np.ndarray:
    """RTMW 133 wholebody (x, y, z) 합성 — 화면 중앙 +/- 박제."""
    # 1920x1080 frame 안 다양한 위치 박제 — center=(960, 540).
    arr = np.zeros((133, 3), dtype=np.float32)
    # 좌측 (x=0.3 → 576px), 우측 (x=0.7 → 1344px), 어깨 y=0.2 → 216px / 골반 y=0.5 / 무릎 y=0.8.
    # COCO-17 index 5 = left_shoulder, 6 = right_shoulder, 11/12 = hip, 13/14 = knee.
    for i in range(17):
        arr[i, 0] = float(w_px) * (0.3 if i % 2 == 1 else 0.7)
        arr[i, 1] = float(h_px) * (0.2 + 0.05 * i)
        arr[i, 2] = 0.0  # z = 0 (2D 추론)
    # 나머지 17~132 도 화면 안 박제.
    for i in range(17, 133):
        arr[i, 0] = float(w_px) * 0.5
        arr[i, 1] = float(h_px) * 0.5
        arr[i, 2] = 0.0
    return arr


def _make_synthetic_scores_133() -> np.ndarray:
    """133 score — 0.9 default (high confidence)."""
    return np.full((133,), 0.9, dtype=np.float32)


def _default_pole_axis() -> PoleAxis:
    return PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="high",
        source="detected",
        frame_index=None,
    )


# ── test cases ────────────────────────────────────────────────────────────────

def test_rtmw_keypoints_2d_not_none():
    """R1 회귀 차단: convert_rtmw_keypoints_to_coco17_and_pole_ext() 호출 시
    PoseFrame.keypoints_2d 가 None 이 아니어야 함."""
    kp_133 = _make_synthetic_keypoints_133()
    scores = _make_synthetic_scores_133()
    frame = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=kp_133,
        scores_133=scores,
        image_width=1920,
        image_height=1080,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=_default_pole_axis(),
    )
    assert frame.keypoints_2d is not None, "R1 회귀 — keypoints_2d=None"
    assert isinstance(frame.keypoints_2d, dict)


def test_rtmw_keypoints_2d_has_8_body_joints():
    """8 body joint (어깨/엘보/손목/골반/무릎 좌우) + nose 등 11+ entry."""
    kp_133 = _make_synthetic_keypoints_133()
    scores = _make_synthetic_scores_133()
    frame = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=kp_133,
        scores_133=scores,
        image_width=1920,
        image_height=1080,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=_default_pole_axis(),
    )
    required = {
        "left_shoulder", "right_shoulder",
        "left_elbow", "right_elbow",
        "left_wrist", "right_wrist",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
    }
    assert required.issubset(frame.keypoints_2d.keys())
    # 17 COCO joint 전체 박제 (nose 포함).
    assert len(frame.keypoints_2d) == 17


def test_rtmw_keypoints_2d_normalized_to_01():
    """모든 x, y 가 [0, 1] 정규화 범위 (image px → normalized)."""
    kp_133 = _make_synthetic_keypoints_133()
    scores = _make_synthetic_scores_133()
    frame = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=kp_133,
        scores_133=scores,
        image_width=1920,
        image_height=1080,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=_default_pole_axis(),
    )
    for name, kp in frame.keypoints_2d.items():
        assert isinstance(kp, Keypoint2D)
        assert 0.0 <= kp.x <= 1.0, f"{name} x={kp.x} out of [0,1]"
        assert 0.0 <= kp.y <= 1.0, f"{name} y={kp.y} out of [0,1]"


def test_rtmw_keypoints_2d_visibility_in_01():
    """visibility 가 [0, 1] (np.clip 박제 회귀)."""
    kp_133 = _make_synthetic_keypoints_133()
    # score 범위 밖 (음수, > 1) 박제 — clamp 검증.
    scores = np.full((133,), 0.9, dtype=np.float32)
    scores[5] = -0.5  # left_shoulder (COCO-17 idx 5) — clamp to 0.0
    scores[6] = 1.5   # right_shoulder — clamp to 1.0
    frame = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=kp_133,
        scores_133=scores,
        image_width=1920,
        image_height=1080,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=_default_pole_axis(),
    )
    for name, kp in frame.keypoints_2d.items():
        assert 0.0 <= kp.visibility <= 1.0, f"{name} visibility={kp.visibility} out of [0,1]"
    assert frame.keypoints_2d["left_shoulder"].visibility == pytest.approx(0.0)
    assert frame.keypoints_2d["right_shoulder"].visibility == pytest.approx(1.0)


def test_rtmw_keypoints_2d_image_dim_zero_returns_empty():
    """R1 fallback: img_w=0 또는 img_h=0 → _build_keypoints_2d_from_rtmw 빈 dict.

    rtmw_133_to_coco17 의 keypoint_2d_unavailable 경로 — Wave 1 UI 가 graceful fallback.
    """
    kp_133 = _make_synthetic_keypoints_133()
    scores = _make_synthetic_scores_133()
    # img_w=0 case
    result = _build_keypoints_2d_from_rtmw(kp_133, scores, img_w=0, img_h=1080)
    assert result == {}
    # img_h=0 case
    result = _build_keypoints_2d_from_rtmw(kp_133, scores, img_w=1920, img_h=0)
    assert result == {}
    # 둘 다 음수
    result = _build_keypoints_2d_from_rtmw(kp_133, scores, img_w=-1, img_h=-1)
    assert result == {}
