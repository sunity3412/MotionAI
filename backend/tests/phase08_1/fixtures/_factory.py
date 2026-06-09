"""Plan 08.1-01 Wave 1 — programmatic factory helpers.

REVIEWS R9 정합 — fixture 파일 대신 함수형 factory 우선.

각 helper 는 compute_axis_deviation 의 직접 입력 dataclass 인스턴스 를 만든다.
shoulder/hip tilt 가 specified degrees 가 되도록 keypoints_3d_pole_aligned 의
좌표 를 합성 — arcsin(|Δz|/||Δ||) == tilt_deg 의 역산.

per Plan 08.1-01 must_haves (fixture factory section).
"""

from __future__ import annotations

import math
from typing import Literal

from sunity_shared.analysis.force_signals import PhaseBoundary
from sunity_shared.analysis.pole_geometry import PoleAxisMeasurement, PoleLine2D
from sunity_shared.analysis.pose_frame import (
    Keypoint2D,
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseFrame,
)

MotionPhase = Literal["entry", "ascent", "final_shape", "hold", "exit"]


# ── helpers (internal) ────────────────────────────────────────────────────


def _kp3d_default() -> Keypoint3D:
    return Keypoint3D(x=0.0, y=0.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1)


def _pole_axis_vertical() -> PoleAxis:
    return PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="vertical_fallback",
        frame_index=None,
    )


def _shoulder_aligned_pair_for_tilt(
    tilt_deg: float,
) -> tuple[Keypoint3DAligned, Keypoint3DAligned]:
    """left_shoulder=(0,0,0), right_shoulder s.t. arcsin(|dz|/||d||) == tilt_deg.

    dx=cos(θ), dy=0, dz=sin(θ) — ||d||=1, |dz|/||d|| = sin(θ) → arcsin = θ.
    """
    theta = math.radians(tilt_deg)
    return (
        Keypoint3DAligned(x=0.0, y=0.0, z=0.0),
        Keypoint3DAligned(x=math.cos(theta), y=0.0, z=math.sin(theta)),
    )


def _hip_aligned_pair_for_tilt(
    tilt_deg: float,
) -> tuple[Keypoint3DAligned, Keypoint3DAligned]:
    """동일 패턴 — left_hip=(0,0,0), right_hip with arcsin → tilt_deg."""
    theta = math.radians(tilt_deg)
    return (
        Keypoint3DAligned(x=0.0, y=0.0, z=0.0),
        Keypoint3DAligned(x=math.cos(theta), y=0.0, z=math.sin(theta)),
    )


# ── factory: pose_frame with keypoints_3d_pole_aligned ────────────────────


def make_pose_frame_with_pole_aligned(
    frame_index: int,
    shoulder_tilt_deg: float,
    hip_tilt_deg: float,
    *,
    reliability: Literal["high", "medium", "low"] = "high",
    timestamp_ms: int | None = None,
) -> PoseFrame:
    """keypoints_3d_pole_aligned 만 채운 PoseFrame — pole_aligned 분기 강제."""
    ls, rs = _shoulder_aligned_pair_for_tilt(shoulder_tilt_deg)
    lh, rh = _hip_aligned_pair_for_tilt(hip_tilt_deg)
    aligned = {
        "left_shoulder": ls,
        "right_shoulder": rs,
        "left_hip": lh,
        "right_hip": rh,
    }
    # keypoints_3d 도 함께 채워야 reliability 게이트 통과 — defaults 로 채움.
    kp3d = {
        "left_shoulder": _kp3d_default(),
        "right_shoulder": _kp3d_default(),
        "left_hip": _kp3d_default(),
        "right_hip": _kp3d_default(),
    }
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms if timestamp_ms is not None else frame_index * 111,
        raw_landmarks_33={},
        keypoints_3d=kp3d,
        keypoints_3d_pole_aligned=aligned,
        keypoints_2d=None,
        pole_extension_landmarks=None,
        pole_axis=_pole_axis_vertical(),
        reliability=reliability,
        body_shape=None,
        raw_keypoints_133=None,
    )


# ── factory: pose_frame with keypoints_2d only (image_2d fallback path) ───


def _kp2d_default(x: float, y: float) -> Keypoint2D:
    return Keypoint2D(x=x, y=y, visibility=0.9)


def make_pose_frame_with_image_2d_only(
    frame_index: int,
    shoulder_tilt_deg: float,
    hip_tilt_deg: float,
    pole_line: PoleLine2D,
    *,
    reliability: Literal["high", "medium", "low"] = "high",
    timestamp_ms: int | None = None,
) -> PoseFrame:
    """keypoints_2d 만 채운 PoseFrame — image_2d fallback 분기 강제.

    shoulder 벡터 의 방향 angle = pole_line direction angle + shoulder_tilt_deg.
    즉 `_shoulder_tilt_2d` 가 계산하는 `sh_angle - pole_dir_angle` == shoulder_tilt_deg.
    """
    dx, dy = pole_line.direction_image
    pole_angle_deg = math.degrees(math.atan2(dy, dx))

    # shoulder line.
    sh_angle = math.radians(pole_angle_deg + shoulder_tilt_deg)
    ls_xy = (0.5, 0.5)
    rs_xy = (ls_xy[0] + 0.1 * math.cos(sh_angle), ls_xy[1] + 0.1 * math.sin(sh_angle))

    # hip line.
    hp_angle = math.radians(pole_angle_deg + hip_tilt_deg)
    lh_xy = (0.5, 0.6)
    rh_xy = (lh_xy[0] + 0.1 * math.cos(hp_angle), lh_xy[1] + 0.1 * math.sin(hp_angle))

    kp2d = {
        "left_shoulder": _kp2d_default(*ls_xy),
        "right_shoulder": _kp2d_default(*rs_xy),
        "left_hip": _kp2d_default(*lh_xy),
        "right_hip": _kp2d_default(*rh_xy),
    }
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms if timestamp_ms is not None else frame_index * 111,
        raw_landmarks_33={},
        keypoints_3d={},
        keypoints_3d_pole_aligned={},  # 빈 dict → pole_aligned 분기 skip
        keypoints_2d=kp2d,
        pole_extension_landmarks=None,
        pole_axis=_pole_axis_vertical(),
        reliability=reliability,
        body_shape=None,
        raw_keypoints_133=None,
    )


def make_pose_frame_neither_path(
    frame_index: int,
    *,
    reliability: Literal["high", "medium", "low"] = "low",
    timestamp_ms: int | None = None,
) -> PoseFrame:
    """둘 다 미가용 PoseFrame — compute_axis_deviation 의 'tilt_unavailable' 분기 강제."""
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms if timestamp_ms is not None else frame_index * 111,
        raw_landmarks_33={},
        keypoints_3d={},
        keypoints_3d_pole_aligned={},
        keypoints_2d=None,
        pole_extension_landmarks=None,
        pole_axis=_pole_axis_vertical(),
        reliability=reliability,
        body_shape=None,
        raw_keypoints_133=None,
    )


# ── factory: phase boundary / pole_axis_measurement ──────────────────────


def make_phase_boundary(
    phase: MotionPhase,
    start: int,
    end: int,
    *,
    timestamp_ms_per_frame: int = 111,
) -> PhaseBoundary:
    return PhaseBoundary(
        phase=phase,
        start_frame_idx=start,
        end_frame_idx=end,
        start_ms=start * timestamp_ms_per_frame,
        end_ms=end * timestamp_ms_per_frame,
        confidence="medium",
        source="heuristic",
        preflight_label_gate_passed=None,
    )


def make_pole_axis_measurement_vertical_fallback() -> PoleAxisMeasurement:
    """line=None → coordinate_space='unavailable' (image_2d path 사용 X)."""
    return PoleAxisMeasurement(
        axis_3d=_pole_axis_vertical(),
        line=None,
        coordinate_space="unavailable",
        frame_index=None,
    )


def make_pole_line_vertical() -> PoleLine2D:
    """수직 pole line — image_2d fallback path 의 입력 line."""
    return PoleLine2D(
        point_image=(0.5, 0.0),
        direction_image=(0.0, 1.0),  # 수직 y 축 → angle=90°
        confidence=0.9,
        source="vertical_fallback",
    )


def make_pole_axis_measurement_with_line(line: PoleLine2D) -> PoleAxisMeasurement:
    return PoleAxisMeasurement(
        axis_3d=_pole_axis_vertical(),
        line=line,
        coordinate_space="image_2d",
        frame_index=None,
    )
