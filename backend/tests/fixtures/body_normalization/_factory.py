"""PoseFrame test factory helper (HIGH-2 v1→v2 박제).

PoseFrame.from_dict 는 production 코드에 없으므로 test-only factory 로 분리.
production `pose_frame.py` 수정 0.

JSON list → tuple 변환 (axis_vector), Keypoint3D.uncertainty_proxy 보정 등.

Phase 2 v5 박제:
  - PoleAxis 4-field (axis_vector / confidence_level / source / frame_index) 정합.
  - PoseFrame 11 필드 (frame_index / timestamp_ms / raw_landmarks_33 / keypoints_3d
    / keypoints_3d_pole_aligned / keypoints_2d / pole_extension_landmarks
    / pole_axis / reliability / body_shape / raw_keypoints_133).
  - body_shape: None (RTMW path — Phase 2 측정기 미주입 시점).
"""

from __future__ import annotations

from typing import Any

from sunity_shared.analysis.pose_frame import (
    Keypoint2D,
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseExtensionLandmark,
    PoseFrame,
)


def _kp3d_from_dict(raw: dict[str, Any]) -> Keypoint3D:
    """Keypoint3D dict → dataclass. uncertainty_proxy=1-confidence 보정."""
    conf = float(raw["confidence"])
    return Keypoint3D(
        x=float(raw["x"]),
        y=float(raw["y"]),
        z=float(raw["z"]),
        confidence=conf,
        uncertainty_proxy=float(raw.get("uncertainty_proxy", 1.0 - conf)),
    )


def _kp3d_aligned_from_dict(raw: dict[str, Any]) -> Keypoint3DAligned:
    return Keypoint3DAligned(
        x=float(raw["x"]),
        y=float(raw["y"]),
        z=float(raw["z"]),
    )


def _kp2d_from_dict(raw: dict[str, Any]) -> Keypoint2D:
    return Keypoint2D(
        x=float(raw["x"]),
        y=float(raw["y"]),
        visibility=float(raw["visibility"]),
    )


def _ext_from_dict(raw: dict[str, Any]) -> PoseExtensionLandmark:
    return PoseExtensionLandmark(
        x=float(raw["x"]),
        y=float(raw["y"]),
        z=float(raw["z"]),
        confidence=float(raw["confidence"]),
    )


def _pole_axis_from_dict(raw: dict[str, Any]) -> PoleAxis:
    """PoleAxis 4 필드. axis_vector JSON list → tuple."""
    ax = raw["axis_vector"]
    return PoleAxis(
        axis_vector=(float(ax[0]), float(ax[1]), float(ax[2])),
        confidence_level=raw["confidence_level"],
        source=raw["source"],
        frame_index=raw.get("frame_index"),
    )


def pose_frame_from_dict(raw: dict[str, Any]) -> PoseFrame:
    """JSON dict → PoseFrame dataclass.

    HIGH-2 v1→v2 박제: timestamp_ms (ms 단위, seconds 단위 금지),
    Keypoint3D.uncertainty_proxy=1-confidence, PoleAxis 4 필드 (origin 박멸).

    Phase 2 v5 박제 (MEDIUM-3 v5):
      body_shape 는 None (RTMW path) — measurer 가 video-level 측정 후 주입.
    """
    keypoints_3d = {
        name: _kp3d_from_dict(v) for name, v in raw["keypoints_3d"].items()
    }
    keypoints_3d_pole_aligned = {
        name: _kp3d_aligned_from_dict(v)
        for name, v in raw["keypoints_3d_pole_aligned"].items()
    }
    keypoints_2d = (
        {name: _kp2d_from_dict(v) for name, v in raw["keypoints_2d"].items()}
        if raw.get("keypoints_2d") is not None
        else None
    )
    pole_extension = (
        {
            name: _ext_from_dict(v)
            for name, v in raw["pole_extension_landmarks"].items()
        }
        if raw.get("pole_extension_landmarks") is not None
        else None
    )
    pole_axis = (
        _pole_axis_from_dict(raw["pole_axis"])
        if raw.get("pole_axis") is not None
        else None
    )
    # raw_keypoints_133 — RTMW path. fixture 는 keypoints_3d 와 동일한 17개만 가질 수 있음.
    raw_133 = raw.get("raw_keypoints_133")
    raw_keypoints_133 = (
        {name: _kp3d_from_dict(v) for name, v in raw_133.items()}
        if raw_133 is not None
        else None
    )

    return PoseFrame(
        frame_index=int(raw["frame_index"]),
        timestamp_ms=int(raw["timestamp_ms"]),
        raw_landmarks_33={},  # RTMW path 는 빈 dict
        keypoints_3d=keypoints_3d,
        keypoints_3d_pole_aligned=keypoints_3d_pole_aligned,
        keypoints_2d=keypoints_2d,
        pole_extension_landmarks=pole_extension,
        pole_axis=pole_axis,
        reliability=raw.get("reliability", "low"),
        body_shape=None,  # Phase 2 v5 MEDIUM-3 박제: RTMW path — measurer 가 주입
        raw_keypoints_133=raw_keypoints_133,
    )
