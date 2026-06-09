"""median_torso_length helper — observed shoulder-hip midpoint Euclidean median.

Plan 08-00 신설 (2026-06-09) — REVIEWS Cycle 1 R2 blocker 해소.

**CRITICAL drift defense (R2)**: `BodyNormalizationProfile.torso_scale` 은 segment
비율 (1.0 self-reference) 이지 observed length 가 아니다 — axis distance / contact
distance metric 의 denominator 로 사용 금지. 본 모듈은 observed shoulder-hip
midpoint 의 Euclidean distance median 을 산출하는 단일 함수 만 export.

본 모듈은 `body_normalization.py` 를 **영구히 import 하지 않는다** — drift defense.
`test_torso_scale_is_not_used_as_denominator` 가 본체 source 에서 'BodyNormalizationProfile'
참조 영구 차단을 검증.

space 분기:
  - 'image_2d':     PoseFrame.keypoints_2d   (Keypoint2D)
  - 'pole_aligned': PoseFrame.keypoints_3d_pole_aligned (Keypoint3DAligned)
  - 'world_3d':     PoseFrame.keypoints_3d   (Keypoint3D)

shoulder midpoint = (left_shoulder + right_shoulder) / 2
hip midpoint      = (left_hip + right_hip) / 2
torso length      = euclidean(shoulder_mid, hip_mid)
return            = median over valid frames (>=5 valid frames required)

valid frame < 5 시 None 반환 — caller 가 warning 'scale_unavailable' 박제.

per REVIEWS Cycle 1 R2 + Suggestions §1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    # forward-ref — runtime import 회피 (drift defense + 순환 방지).
    from .pose_frame import PoseFrame


# ── Type aliases ──────────────────────────────────────────────────────────

Space = Literal["image_2d", "pole_aligned", "world_3d"]

_SPACES = frozenset({"image_2d", "pole_aligned", "world_3d"})

_MIN_VALID_FRAMES = 5  # < 5 frame → None + 'scale_unavailable' warning source.

_REQUIRED_KEYPOINTS = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")


# ── helpers ────────────────────────────────────────────────────────────────

def _lookup_coords_2d(kp: object) -> tuple[float, float] | None:
    """Keypoint2D 좌표 추출. attr 결손 시 None."""
    x = getattr(kp, "x", None)
    y = getattr(kp, "y", None)
    if x is None or y is None:
        return None
    return (float(x), float(y))


def _lookup_coords_3d(kp: object) -> tuple[float, float, float] | None:
    """Keypoint3D / Keypoint3DAligned 좌표 추출. attr 결손 시 None."""
    x = getattr(kp, "x", None)
    y = getattr(kp, "y", None)
    z = getattr(kp, "z", None)
    if x is None or y is None or z is None:
        return None
    return (float(x), float(y), float(z))


def _frame_keypoint_dict(frame: "PoseFrame", space: Space) -> dict | None:
    """space 에 해당하는 keypoint dict 반환. 없으면 None."""
    if space == "image_2d":
        return frame.keypoints_2d
    if space == "pole_aligned":
        return frame.keypoints_3d_pole_aligned
    if space == "world_3d":
        return frame.keypoints_3d
    return None


def median_torso_length(
    pose_frames: list["PoseFrame"],
    *,
    space: Space,
) -> float | None:
    """observed shoulder-hip midpoint Euclidean median.

    Args:
        pose_frames: PoseFrame list (보통 60 frame).
        space: 'image_2d' | 'pole_aligned' | 'world_3d'.

    Returns:
        median torso length (float) if valid frame >= 5 else None.
        None 반환 시 caller 가 warning 'scale_unavailable' 박제 (R2).
    """
    if space not in _SPACES:
        raise ValueError(
            f"space must be one of {_SPACES}, got {space!r}"
        )

    lengths: list[float] = []
    for frame in pose_frames:
        kp_dict = _frame_keypoint_dict(frame, space)
        if not kp_dict:
            continue
        # 4 required keypoint 중 하나라도 missing → 해당 frame skip.
        if any(name not in kp_dict for name in _REQUIRED_KEYPOINTS):
            continue

        if space == "image_2d":
            ls = _lookup_coords_2d(kp_dict["left_shoulder"])
            rs = _lookup_coords_2d(kp_dict["right_shoulder"])
            lh = _lookup_coords_2d(kp_dict["left_hip"])
            rh = _lookup_coords_2d(kp_dict["right_hip"])
            if ls is None or rs is None or lh is None or rh is None:
                continue
            shoulder_mid = np.array(
                [(ls[0] + rs[0]) / 2.0, (ls[1] + rs[1]) / 2.0],
                dtype=np.float64,
            )
            hip_mid = np.array(
                [(lh[0] + rh[0]) / 2.0, (lh[1] + rh[1]) / 2.0],
                dtype=np.float64,
            )
        else:
            ls = _lookup_coords_3d(kp_dict["left_shoulder"])
            rs = _lookup_coords_3d(kp_dict["right_shoulder"])
            lh = _lookup_coords_3d(kp_dict["left_hip"])
            rh = _lookup_coords_3d(kp_dict["right_hip"])
            if ls is None or rs is None or lh is None or rh is None:
                continue
            shoulder_mid = np.array(
                [
                    (ls[0] + rs[0]) / 2.0,
                    (ls[1] + rs[1]) / 2.0,
                    (ls[2] + rs[2]) / 2.0,
                ],
                dtype=np.float64,
            )
            hip_mid = np.array(
                [
                    (lh[0] + rh[0]) / 2.0,
                    (lh[1] + rh[1]) / 2.0,
                    (lh[2] + rh[2]) / 2.0,
                ],
                dtype=np.float64,
            )

        diff = shoulder_mid - hip_mid
        length = float(np.linalg.norm(diff))
        if not np.isfinite(length):
            continue
        lengths.append(length)

    if len(lengths) < _MIN_VALID_FRAMES:
        return None
    return float(np.median(np.array(lengths, dtype=np.float64)))


__all__ = (
    "Space",
    "median_torso_length",
)
