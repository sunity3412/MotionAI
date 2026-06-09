"""Phase 8 fixture factory — programmatic dataclass 박제.

REVIEWS Cycle 1 R9 권고 정합 — JSON fixture 보다 programmatic factory 우선.
REVIEWS Cycle 1 H1 (dataclass mismatch) 영구 차단 — 본 factory 가 실제 dataclass
시그너처 정확히 mirror:
  - PoseFrame(frame_index=..., timestamp_ms=...) (frame_idx 아님)
  - Keypoint3DAligned(x, y, z) (visibility 필드 없음)
  - BodyNormalizationProfile 7 필드 (asymmetry 필드 없음)

JSON fixture 박제는 Plan 08-01 가 본 factory 위에 박제.

per Plan 08-00 Task 1 <behavior>.
"""

from __future__ import annotations

from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.pole_geometry import (
    PoleAxisMeasurement,
    PoleLine2D,
    build_pole_axis_measurement,
)
from sunity_shared.analysis.pose_frame import (
    Keypoint2D,
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseFrame,
)


# ── keypoint factories ────────────────────────────────────────────────────

def make_keypoint3d(
    x: float,
    y: float,
    z: float,
    *,
    confidence: float = 1.0,
) -> Keypoint3D:
    """Keypoint3D 박제 — uncertainty_proxy = 1.0 - confidence 자동 산출."""
    return Keypoint3D(
        x=x,
        y=y,
        z=z,
        confidence=confidence,
        uncertainty_proxy=1.0 - confidence,
    )


def make_keypoint3d_aligned(x: float, y: float, z: float) -> Keypoint3DAligned:
    """Keypoint3DAligned 박제 — visibility 필드 없음 (REVIEWS H1)."""
    return Keypoint3DAligned(x=x, y=y, z=z)


def make_keypoint2d(
    x: float,
    y: float,
    *,
    visibility: float = 1.0,
) -> Keypoint2D:
    """Keypoint2D 박제 — image normalized 0~1 좌표."""
    return Keypoint2D(x=x, y=y, visibility=visibility)


# ── PoseFrame factory ──────────────────────────────────────────────────────

def make_pose_frame(
    frame_index: int,
    timestamp_ms: int,
    *,
    keypoints_3d_pole_aligned: dict | None = None,
    keypoints_3d: dict | None = None,
    keypoints_2d: dict | None = None,
    pole_axis: PoleAxis | None = None,
    reliability: str = "high",
) -> PoseFrame:
    """PoseFrame 박제 — frame_index 정확히 명시 (REVIEWS H1, frame_idx 아님).

    PoseFrame.empty() 박제 시그너처 정합 + 본 factory 는 keypoint 채울 때 사용.
    """
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        raw_landmarks_33={},
        keypoints_3d=keypoints_3d or {},
        keypoints_3d_pole_aligned=keypoints_3d_pole_aligned or {},
        keypoints_2d=keypoints_2d,
        pole_extension_landmarks=None,
        pole_axis=pole_axis,
        reliability=reliability,  # type: ignore[arg-type]
    )


# ── BodyNormalizationProfile factory ──────────────────────────────────────

def make_body_profile(
    *,
    estimated_height_scale: float = 1.0,
    arm_scale: float = 1.0,
    leg_scale: float = 1.0,
    torso_scale: float = 1.0,
    shoulder_hip_ratio: float = 1.0,
    confidence: float = 1.0,
    warnings: list[str] | None = None,
) -> BodyNormalizationProfile:
    """BodyNormalizationProfile 7 필드 박제 — asymmetry 필드 없음 (REVIEWS H1)."""
    return BodyNormalizationProfile(
        estimated_height_scale=estimated_height_scale,
        arm_scale=arm_scale,
        leg_scale=leg_scale,
        torso_scale=torso_scale,
        shoulder_hip_ratio=shoulder_hip_ratio,
        confidence=confidence,
        warnings=list(warnings) if warnings is not None else [],
    )


# ── Pole geometry factories ────────────────────────────────────────────────

def make_pole_line_2d(
    *,
    point_image: tuple[float, float] = (0.5, 0.5),
    direction_image: tuple[float, float] = (0.0, 1.0),
    confidence: float = 0.9,
    source: str = "detected",
) -> PoleLine2D:
    """vertical pole default (image y-down 가정, direction (0, 1))."""
    return PoleLine2D(
        point_image=point_image,
        direction_image=direction_image,
        confidence=confidence,
        source=source,  # type: ignore[arg-type]
    )


def make_pole_axis(
    *,
    axis_vector: tuple[float, float, float] = (0.0, 1.0, 0.0),
    confidence_level: str = "high",
    source: str = "detected",
    frame_index: int | None = None,
) -> PoleAxis:
    """vertical pole default — Phase 1 D-11 'detected' source."""
    return PoleAxis(
        axis_vector=axis_vector,
        confidence_level=confidence_level,  # type: ignore[arg-type]
        source=source,  # type: ignore[arg-type]
        frame_index=frame_index,
    )


def make_pole_axis_measurement(
    *,
    line: PoleLine2D | None = None,
    axis_3d: PoleAxis | None = None,
    frame_index: int | None = None,
) -> PoleAxisMeasurement:
    """PoleAxisMeasurement 박제 — line=None 시 coordinate_space='unavailable' 자동."""
    if axis_3d is None:
        axis_3d = make_pole_axis()
    return build_pole_axis_measurement(
        axis_3d=axis_3d,
        line=line,
        frame_index=frame_index,
    )


__all__ = (
    "make_keypoint3d",
    "make_keypoint3d_aligned",
    "make_keypoint2d",
    "make_pose_frame",
    "make_body_profile",
    "make_pole_line_2d",
    "make_pole_axis",
    "make_pole_axis_measurement",
)
