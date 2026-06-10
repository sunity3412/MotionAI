"""Phase 12 Wave 0B (Plan 12-01) — assemble.build_keypoint_report 종합 integration.

T=2 frame × 8 COCO body keypoint, 1 frame 은 knee 가용 / 1 frame 은 knee 미가용.
axisData[4..5] (frame 0 knee) finite, axisMask[5] (frame 0 knee) = True.
axisData[10..11] (frame 1 knee) = (0.0, 0.0), axisMask[5+5] (frame 1 knee) = False.

verifies:
  - result.keypointReport.joints length == 8 (R11)
  - result.keypointReport.axisData length == T*3*2 finite (R2 + R7 iter-2 — NaN 0회)
  - result.keypointReport.axisMask length == T*3 strict bool (R7 iter-2)
  - axisData[0..1] = shoulder_mid (midpoint(left_shoulder, right_shoulder))
  - axisData[2..3] = hip_mid
  - axisData[4..5] = knee_mid (가용) 또는 (0.0, 0.0) (미가용)
  - axisMask = [True,True,True, True,True,False]
"""

from __future__ import annotations

from .conftest import _make_keypoint_2d, _make_pose_frame
from sunity_shared.analysis.assemble import build_keypoint_report
from sunity_shared.analysis.keypoint_frame import (
    NUM_KEYPOINTS_PHASE12,
    KeypointReport,
)


def _frame_with_knee():
    """frame 0 — 어깨/골반/무릎 모두 박제."""
    kp = {
        "left_shoulder": _make_keypoint_2d(x=0.3, y=0.2, vis=0.9),
        "right_shoulder": _make_keypoint_2d(x=0.7, y=0.2, vis=0.9),
        "left_hip": _make_keypoint_2d(x=0.35, y=0.5, vis=0.9),
        "right_hip": _make_keypoint_2d(x=0.65, y=0.5, vis=0.9),
        "left_knee": _make_keypoint_2d(x=0.35, y=0.8, vis=0.9),
        "right_knee": _make_keypoint_2d(x=0.65, y=0.8, vis=0.9),
        "left_wrist": _make_keypoint_2d(x=0.20, y=0.50, vis=0.9),
        "right_wrist": _make_keypoint_2d(x=0.80, y=0.50, vis=0.9),
    }
    return _make_pose_frame(frame_idx=0, timestamp_ms=0, keypoints_2d=kp)


def _frame_without_knee():
    """frame 1 — 어깨/골반만, knee 누락 (compute_axis_frames knee_mid=None)."""
    kp = {
        "left_shoulder": _make_keypoint_2d(x=0.3, y=0.2, vis=0.9),
        "right_shoulder": _make_keypoint_2d(x=0.7, y=0.2, vis=0.9),
        "left_hip": _make_keypoint_2d(x=0.35, y=0.5, vis=0.9),
        "right_hip": _make_keypoint_2d(x=0.65, y=0.5, vis=0.9),
        # left_knee / right_knee 누락
        "left_wrist": _make_keypoint_2d(x=0.20, y=0.50, vis=0.9),
        "right_wrist": _make_keypoint_2d(x=0.80, y=0.50, vis=0.9),
    }
    return _make_pose_frame(frame_idx=1, timestamp_ms=111, keypoints_2d=kp)


def test_build_keypoint_report_returns_valid_report() -> None:
    """T=2 mixed knee 시나리오 → 유효 KeypointReport 반환."""
    frames = [_frame_with_knee(), _frame_without_knee()]
    report = build_keypoint_report(frames, fps=9.0)
    assert isinstance(report, KeypointReport)


def test_build_keypoint_report_joints_length_eight() -> None:
    """R11 — joints length = 8."""
    frames = [_frame_with_knee(), _frame_without_knee()]
    report = build_keypoint_report(frames, fps=9.0)
    assert len(report.joints) == NUM_KEYPOINTS_PHASE12


def test_build_keypoint_report_axis_data_finite_no_nan() -> None:
    """R2 + R7 iter-2 — axisData length T*3*2 + finite only (NaN 0회)."""
    import math

    frames = [_frame_with_knee(), _frame_without_knee()]
    report = build_keypoint_report(frames, fps=9.0)
    assert len(report.axis_data) == 2 * 3 * 2  # T*3*2
    for v in report.axis_data:
        assert math.isfinite(v), f"axisData NaN/Inf 박제: {v}"


def test_build_keypoint_report_axis_mask_length_and_values() -> None:
    """R7 iter-2 — axisMask length T*3 bool. frame 1 knee 미가용 → mask[5] = False."""
    frames = [_frame_with_knee(), _frame_without_knee()]
    report = build_keypoint_report(frames, fps=9.0)
    assert len(report.axis_mask) == 2 * 3
    # frame 0 — 모두 True.
    assert report.axis_mask[0] is True  # shoulder
    assert report.axis_mask[1] is True  # hip
    assert report.axis_mask[2] is True  # knee 가용
    # frame 1 — knee 만 False.
    assert report.axis_mask[3] is True  # shoulder
    assert report.axis_mask[4] is True  # hip
    assert report.axis_mask[5] is False  # knee 미가용


def test_build_keypoint_report_axis_data_midpoints() -> None:
    """axisData[0..5] = (shoulder_mid, hip_mid, knee_mid) for frame 0."""
    frames = [_frame_with_knee(), _frame_without_knee()]
    report = build_keypoint_report(frames, fps=9.0)
    # frame 0 — shoulder_mid = midpoint(0.3, 0.7) = (0.5, 0.2).
    assert report.axis_data[0] == 0.5
    assert report.axis_data[1] == 0.2
    # frame 0 — hip_mid = midpoint(0.35, 0.65) = (0.5, 0.5).
    assert report.axis_data[2] == 0.5
    assert report.axis_data[3] == 0.5
    # frame 0 — knee_mid = midpoint(0.35, 0.65) = (0.5, 0.8).
    assert report.axis_data[4] == 0.5
    assert report.axis_data[5] == 0.8
    # frame 1 — shoulder_mid + hip_mid 박제, knee_mid = (0.0, 0.0).
    assert report.axis_data[6] == 0.5  # shoulder_x
    assert report.axis_data[7] == 0.2  # shoulder_y
    assert report.axis_data[8] == 0.5  # hip_x
    assert report.axis_data[9] == 0.5  # hip_y
    assert report.axis_data[10] == 0.0  # knee_mid placeholder
    assert report.axis_data[11] == 0.0


def test_build_keypoint_report_empty_pose_frames_returns_none() -> None:
    """H4 iter-4 — 빈 list → None."""
    assert build_keypoint_report([], fps=9.0) is None


def test_build_keypoint_report_all_keypoints_2d_none_returns_none() -> None:
    """H4 iter-4 — 모든 frame 의 keypoints_2d=None → None."""
    frames = [_make_pose_frame(frame_idx=i, keypoints_2d=None) for i in range(3)]
    assert build_keypoint_report(frames, fps=9.0) is None


def test_build_keypoint_report_first_frame_none_ok_others_present() -> None:
    """H4 iter-4 — 첫 frame keypoints_2d None 단독은 drop 사유 X.

    frame 0 = None, frame 1 = 정상 → None 반환 X (정상 frame 보존).
    """
    frames = [
        _make_pose_frame(frame_idx=0, keypoints_2d=None),
        _frame_with_knee(),
    ]
    report = build_keypoint_report(frames, fps=9.0)
    assert report is not None
    assert report.frames == 2
    # frame 0 = placeholder + reliability "low".
    assert report.reliability[0] == "low"


def test_build_keypoint_report_invalid_fps_raises() -> None:
    """R3 — fps <= 0 → ValueError."""
    import pytest

    frames = [_frame_with_knee()]
    with pytest.raises(ValueError, match="fps"):
        build_keypoint_report(frames, fps=0)
    with pytest.raises(ValueError, match="fps"):
        build_keypoint_report(frames, fps=-1.0)


def test_build_keypoint_report_data_length_invariant() -> None:
    """data length = T * J * 2 — __post_init__ 통과 후 동등 검증."""
    frames = [_frame_with_knee(), _frame_without_knee()]
    report = build_keypoint_report(frames, fps=9.0)
    assert len(report.data) == 2 * 8 * 2
    assert len(report.confidence) == 2 * 8
    assert len(report.reliability) == 2


def test_build_keypoint_report_hand_maps_to_wrist() -> None:
    """JOINT_KEY_TO_ANGLE_KEY — left_hand → left_wrist 매핑 정합.

    pose_frame 이 wrist 박제하면 build_keypoint_report 의 left_hand 좌표 = wrist 값.
    joints[6] = 'left_hand' (KeypointName 순서: shoulder, hip, knee, hand).
    """
    frames = [_frame_with_knee()]
    report = build_keypoint_report(frames, fps=9.0)
    # joints[6] = 'left_hand' (per _KEYPOINT_NAMES tuple 순서).
    assert report.joints[6] == "left_hand"
    # frame 0 의 left_wrist = (0.20, 0.50) — frame 0 의 data[6*2 .. 6*2+1] 박제.
    base = 6 * 2
    assert report.data[base] == 0.20
    assert report.data[base + 1] == 0.50
