"""Phase 12 Wave 0A R2 (Codex 직접 리뷰 2026-06-10) — axis polyline 정의 검증.

기존 plan 의 axis = midpoint(left_shoulder, right_shoulder) 단일 점 박제는
12-CONTEXT.md "중심축 = 어깨중심 ↔ 골반중심 ↔ 무릎중심 선" 과 모순. AxisFrame
3 point 폴리라인 박제.

cite: 12-00-PLAN.md Task T4.
"""

from __future__ import annotations

import dataclasses

import pytest

from sunity_shared.analysis.dimensions import AxisFrame, compute_axis_frames

from .conftest import (
    _make_default_keypoints_2d_full,
    _make_pose_frame,
    _make_pose_frames_sequence,
)


def test_axis_frame_dataclass_frozen():
    """AxisFrame 은 frozen=True dataclass — 변경 시 FrozenInstanceError."""
    frame = AxisFrame(
        shoulder_mid=(0.5, 0.2),
        hip_mid=(0.5, 0.5),
        knee_mid=(0.5, 0.8),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        frame.shoulder_mid = (0.1, 0.1)  # type: ignore[misc]


def test_compute_axis_frames_3_point_full():
    """모든 keypoint 있으면 3 point AxisFrame (knee_mid 포함)."""
    frames = _make_pose_frames_sequence(n_frames=3, with_keypoints_2d=True)
    result = compute_axis_frames(frames)
    assert len(result) == 3
    for axis in result:
        assert axis is not None
        # 좌우 어깨 x=0.3, 0.7 → midpoint x=0.5
        assert axis.shoulder_mid[0] == pytest.approx(0.5)
        assert axis.shoulder_mid[1] == pytest.approx(0.2)
        assert axis.hip_mid[0] == pytest.approx(0.5)
        assert axis.hip_mid[1] == pytest.approx(0.5)
        assert axis.knee_mid is not None
        assert axis.knee_mid[0] == pytest.approx(0.5)
        assert axis.knee_mid[1] == pytest.approx(0.8)


def test_compute_axis_frames_no_knee():
    """knee keypoint 누락 시 knee_mid=None (어깨↔골반 선만)."""
    kp = _make_default_keypoints_2d_full()
    del kp["left_knee"]
    del kp["right_knee"]
    frame = _make_pose_frame(keypoints_2d=kp)
    result = compute_axis_frames([frame])
    assert len(result) == 1
    assert result[0] is not None
    assert result[0].knee_mid is None
    assert result[0].shoulder_mid[0] == pytest.approx(0.5)
    assert result[0].hip_mid[0] == pytest.approx(0.5)


def test_compute_axis_frames_no_shoulder_returns_none():
    """어깨 keypoint 누락 시 AxisFrame=None (전체 폴리라인 불가)."""
    kp = _make_default_keypoints_2d_full()
    del kp["left_shoulder"]
    frame = _make_pose_frame(keypoints_2d=kp)
    result = compute_axis_frames([frame])
    assert result == [None]


def test_compute_axis_frames_no_hip_returns_none():
    """골반 keypoint 누락 시 AxisFrame=None."""
    kp = _make_default_keypoints_2d_full()
    del kp["right_hip"]
    frame = _make_pose_frame(keypoints_2d=kp)
    result = compute_axis_frames([frame])
    assert result == [None]


def test_compute_axis_frames_no_keypoints_2d_returns_none():
    """keypoints_2d=None (RTMW R1 fallback) → AxisFrame=None."""
    frame = _make_pose_frame(keypoints_2d=None)
    result = compute_axis_frames([frame])
    assert result == [None]


def test_compute_axis_frames_empty_keypoints_2d_returns_none():
    """keypoints_2d={} (빈 dict, image dim 0 fallback) → AxisFrame=None."""
    frame = _make_pose_frame(keypoints_2d={})
    result = compute_axis_frames([frame])
    assert result == [None]


def test_compute_axis_frames_mixed_sequence():
    """일부 frame keypoints_2d 있고 일부 None → 1:1 list 정합."""
    frame_ok = _make_pose_frame(
        frame_idx=0, keypoints_2d=_make_default_keypoints_2d_full()
    )
    frame_missing = _make_pose_frame(frame_idx=1, keypoints_2d=None)
    result = compute_axis_frames([frame_ok, frame_missing])
    assert len(result) == 2
    assert result[0] is not None
    assert result[1] is None
