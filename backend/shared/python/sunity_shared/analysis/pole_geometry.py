"""PoleLine2D + PoleAxisMeasurement + CoordinateSpace enum + 점-직선 거리 helper.

Plan 08-00 신설 (2026-06-09) — REVIEWS Cycle 1 R1 blocker 해소.

PoleAxis (pose_frame.py 박제 본체) 는 direction-only — image 평면에서 axis 까지의
점-직선 거리를 산출할 수 없다. 본 모듈은 PoleAxis 본체 변경 0 으로 image 2D 평면의
선 정보 (PoleLine2D) + axis_3d 메타 묶음 (PoleAxisMeasurement) 을 신설하여 그 한계를
보강한다.

Phase 1 의 HoughPoleDetector 는 이미 image 평면에서 검출 (`pole/detector.py`) —
PoleLine2D 는 본 검출 결과의 image-평면 표현. axis 거리 계산은 image 2D 점-직선 거리
공식을 사용하며, line 미가용 시 coordinate_space='unavailable' + caller 가 distance
필드를 None 으로 박제 (graceful degrade).

lockstep:
  - TS 미러: app/src/types/analysis.ts — PoleLine2D / PoleAxisMeasurement /
    CoordinateSpace / ContactPrimitiveKind interface
  - contract.md §9.0 Coordinate/Scale Contract
  - 변경 시 3-way 동시 갱신 (CLAUDE.md Cross-cutting).

per REVIEWS Cycle 1 R1 + Suggestions §1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .pose_frame import PoleAxis


# ── Type aliases ──────────────────────────────────────────────────────────

# REVIEWS Cycle 1 Suggestions §1: distance metric 의 좌표공간 명시 강제.
#   image_2d:     image 평면 normalized 0~1 좌표 (Phase 1 Hough 검출 공간)
#   pole_aligned: PoleAxis 정렬 3D 좌표 (Keypoint3DAligned)
#   world_3d:     metric world 3D 좌표 (Keypoint3D)
#   unavailable:  계산 불가 — caller 가 numeric 필드 None + warning 박제
CoordinateSpace = Literal["image_2d", "pole_aligned", "world_3d", "unavailable"]

# REVIEWS Cycle 1 R3: 12 contact point 의 본질적 분류.
#   keypoint:     COCO-17 직접 가용 keypoint (left_hand 등 10 point)
#   segment:      두 keypoint 의 mid-segment 거리로 산출 (inner_thigh 2 point)
#   region_proxy: 다중 keypoint midpoint region proxy (hip 1 point)
ContactPrimitiveKind = Literal["keypoint", "segment", "region_proxy"]

PoleLineSource = Literal["detected", "vertical_fallback"]

_COORDINATE_SPACES = frozenset({"image_2d", "pole_aligned", "world_3d", "unavailable"})
_POLE_LINE_SOURCES = frozenset({"detected", "vertical_fallback"})


# ── PoleLine2D ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PoleLine2D:
    """image 평면 (normalized 0~1) 의 폴 축 직선 박제.

    point_image: 직선 위의 한 점 (x, y), normalized 0~1.
    direction_image: 직선 방향 단위벡터 (dx, dy), norm ≈ 1.0.
    confidence: 검출 신뢰도 [0.0, 1.0].
    source: 'detected' (Hough 성공) | 'vertical_fallback' (수직 가정).

    Phase 1 HoughPoleDetector 가 이미 image 평면 검출 — 본 dataclass 는 그
    표현 contract. Phase 1 박제 본체 변경 0.
    """

    point_image: tuple[float, float]
    direction_image: tuple[float, float]
    confidence: float
    source: PoleLineSource

    def __post_init__(self) -> None:
        if self.source not in _POLE_LINE_SOURCES:
            raise ValueError(
                f"source must be one of {_POLE_LINE_SOURCES}, got {self.source!r}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )
        dx, dy = self.direction_image
        norm = (dx * dx + dy * dy) ** 0.5
        if abs(norm - 1.0) > 1e-3:
            raise ValueError(
                "direction_image must be a unit vector (norm ≈ 1.0), "
                f"got norm={norm}"
            )


# ── PoleAxisMeasurement ───────────────────────────────────────────────────

@dataclass(frozen=True)
class PoleAxisMeasurement:
    """axis_3d (PoleAxis, direction-only) + line (image 2D position) 묶음.

    REVIEWS Cycle 1 R1 blocker 해소 — axis_3d 단독으로는 image 평면 점-직선 거리
    산출 불가. line 가용 시 image_2d 공간에서 산출. line=None 시 coordinate_space
    가 'unavailable' 강제 + caller 가 distance 필드 None + warning
    'pole_line_missing' 박제.

    axis_3d: Phase 1 박제 PoleAxis (direction-only). 본체 변경 0.
    line: image 2D PoleLine2D. fallback 시 None.
    coordinate_space: distance 산출 좌표공간. line=None 시 'unavailable'.
    frame_index: video-level (Phase 1 D-10) 시 None.
    """

    axis_3d: PoleAxis
    line: PoleLine2D | None
    coordinate_space: CoordinateSpace
    frame_index: int | None = None

    def __post_init__(self) -> None:
        if self.coordinate_space not in _COORDINATE_SPACES:
            raise ValueError(
                f"coordinate_space must be one of {_COORDINATE_SPACES}, "
                f"got {self.coordinate_space!r}"
            )
        # invariant: line None ↔ coordinate_space == 'unavailable'.
        if self.line is None and self.coordinate_space != "unavailable":
            raise ValueError(
                "line=None requires coordinate_space='unavailable', "
                f"got {self.coordinate_space!r}"
            )
        if self.line is not None and self.coordinate_space == "unavailable":
            raise ValueError(
                "line is present but coordinate_space='unavailable' — "
                "must be 'image_2d' (or pole_aligned/world_3d future)"
            )


# ── helpers ────────────────────────────────────────────────────────────────

def point_to_pole_line_distance_2d(
    point: tuple[float, float],
    line: PoleLine2D,
) -> float:
    """image 2D 점-직선 수직거리.

    direction_image 가 unit vector 가정 (PoleLine2D.__post_init__ 가 보장).
    공식: |(p - p0) × d| = |(x - x0) * dy - (y - y0) * dx|.

    NaN 입력 시 NaN 반환 (graceful) — caller 가 warning 박제.
    """
    x, y = point
    x0, y0 = line.point_image
    dx, dy = line.direction_image
    return float(np.abs((x - x0) * dy - (y - y0) * dx))


def build_pole_axis_measurement(
    axis_3d: PoleAxis,
    line: PoleLine2D | None,
    *,
    frame_index: int | None = None,
) -> PoleAxisMeasurement:
    """line 존재 여부로 coordinate_space 자동 결정.

    line 가용 → 'image_2d', line=None → 'unavailable'.
    future plan 이 pole_aligned 3D lift 도입 시 본 helper 가 분기 확장.
    """
    if line is None:
        coordinate_space: CoordinateSpace = "unavailable"
    else:
        coordinate_space = "image_2d"
    return PoleAxisMeasurement(
        axis_3d=axis_3d,
        line=line,
        coordinate_space=coordinate_space,
        frame_index=frame_index,
    )


__all__ = (
    "CoordinateSpace",
    "ContactPrimitiveKind",
    "PoleLineSource",
    "PoleLine2D",
    "PoleAxisMeasurement",
    "point_to_pole_line_distance_2d",
    "build_pole_axis_measurement",
)
