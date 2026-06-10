"""Phase 12 Wave 0B (Plan 12-01) — KeypointReport 신설 schema.

KeypointOverlay (Wave 1+) 가 소비할 flat 좌표 + 신뢰도 + 축 폴리라인 묶음.
TS interface (`app/src/types/analysis.ts::KeypointReport`) + docs §9.12 와
3-way atomic commit lockstep — Phase 9 D-09-U1 mirror.

설계 정합 (Codex 직접 리뷰 2026-06-10):
  R1 — RTMW adapter 가 keypoints_2d 채움 (12-00 Wave 0A T1).
  R2 — axisData 별도 field, 3-point polyline (shoulder_mid/hip_mid/knee_mid?).
  R3 — fps required (default 제거).
  R6 — confidence source = clamp(Keypoint2D.visibility, 0, 1).
  R7 iter-2 — axisData finite only (NaN 0회), axisMask flat T×3 bool.
  R10 — 10 필드 (warnings 포함).
  R11 — 8 body keypoint, axis 는 별도 axisData.
  H3 iter-4 (Codex) — data/confidence finite + confidence ∈ [0, 1].

Firestore 저장 — flat 강제 ([[firestore-nested-array-flat]]).
`_validate_keypoint_report` scoped validator 가 nested list reject.

Phase 책임 경계:
  - Phase 12 = raw 수치 (KeypointOverlay)
  - Wave 1 = UI 소비 (mask 참조해서 polyline 2-point or 3-point 분기)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal


# ── KeypointName Literal (R11 정합 — 8 body keypoint) ─────────────────────
# axis 는 별도 axisData (compute_axis_frames 산출) — 본 enum 에 포함 X.

KeypointName = Literal[
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_hand",
    "right_hand",
]
"""8 body keypoint enum — Wave 1 KeypointOverlay 가 라벨 lookup.

`left_hand` / `right_hand` 는 COCO-17 의 `left_wrist` / `right_wrist` 에
매핑된다 (loose hand 박제). v2 의 wrist 신설은 후속 plan 책임.
"""

_KEYPOINT_NAMES: tuple[KeypointName, ...] = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_hand",
    "right_hand",
)

NUM_KEYPOINTS_PHASE12: int = len(_KEYPOINT_NAMES)
"""8 — KeypointReport.joints 기본 길이 (R10/R11 정합)."""

_AXIS_POLYLINE_POINTS: int = 3
"""R2 정합 — axisData polyline = shoulder_mid + hip_mid + knee_mid?."""

_VALID_RELIABILITY: frozenset[str] = frozenset({"high", "medium", "low"})

# COCO-17 → KeypointName 매핑 (assemble.build_keypoint_report 가 사용).
# left_hand → left_wrist 등 loose mapping 박제.
JOINT_KEY_TO_ANGLE_KEY: dict[str, str] = {
    "left_shoulder": "left_shoulder",
    "right_shoulder": "right_shoulder",
    "left_hip": "left_hip",
    "right_hip": "right_hip",
    "left_knee": "left_knee",
    "right_knee": "right_knee",
    "left_hand": "left_wrist",
    "right_hand": "right_wrist",
}


@dataclass(frozen=True)
class KeypointReport:
    """Phase 12 신설 — KeypointOverlay 소비.

    10 필드 (R10 + R7 iter-2 정합):
      version        : str (non-empty, "1.0" 초기)
      joints         : list[str] (len == 8, _KEYPOINT_NAMES tuple)
      frames         : int (>= 0)
      fps            : float (> 0) — R3 정합, default 제거
      data           : list[float] (flat, len == T × J × 2 — finite only, H3 iter-4)
      confidence     : list[float] (flat, len == T × J — finite + [0, 1], H3 iter-4)
      reliability    : list[str] (len == T, item ∈ {"high","medium","low"})
      axis_data      : list[float] (R6 iter-2 snake_case; camelCase = "axisData")
                        flat, len == T × 3 × 2, finite only (R7 iter-2 — NaN 0회).
                        knee_mid 미가용 frame 은 (0.0, 0.0) placeholder.
      axis_mask      : list[bool] (R7 iter-2 신설; camelCase = "axisMask")
                        flat, len == T × 3, knee_mid 미가용 frame 은 false.
                        UI 가 mask 참조해서 polyline 2-point or 3-point 분기.
      warnings       : list[str] (non-empty str only)

    `_dataclass_to_camel_case_dict` (pipeline/app.py) 변환:
      axis_data -> axisData / axis_mask -> axisMask.

    non-default → default 순서 강제 (Phase 9 D-09-R1 mirror).
    """

    version: str
    joints: list[str]
    frames: int
    fps: float
    data: list[float]
    confidence: list[float]
    reliability: list[str]
    axis_data: list[float]
    axis_mask: list[bool]
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # ── 1. scalar 검증 ─────────────────────────────────────────────────
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("version must be non-empty str")
        if not isinstance(self.frames, int) or self.frames < 0:
            raise ValueError(f"frames must be int >= 0, got {self.frames!r}")
        # R3 — fps required, > 0.
        if not isinstance(self.fps, (int, float)) or self.fps <= 0:
            raise ValueError(f"fps must be > 0, got {self.fps!r}")
        if not math.isfinite(float(self.fps)):
            raise ValueError(f"fps must be finite, got {self.fps!r}")

        # ── 2. joints 검증 ─────────────────────────────────────────────────
        if not isinstance(self.joints, list):
            raise ValueError(
                f"joints must be list (contract list[str]), "
                f"got {type(self.joints).__name__}"
            )
        if len(self.joints) < 1:
            raise ValueError("joints must have at least 1 entry")
        for i, j in enumerate(self.joints):
            if not isinstance(j, str) or not j:
                raise ValueError(
                    f"joints[{i}] must be non-empty str, got {type(j).__name__}={j!r}"
                )

        T = self.frames
        J = len(self.joints)

        # ── 3. data — flat T*J*2, finite only (H3 iter-4) ─────────────────
        if not isinstance(self.data, list):
            raise ValueError(
                f"data must be list (contract flat list[float]), "
                f"got {type(self.data).__name__}"
            )
        if len(self.data) != T * J * 2:
            raise ValueError(
                f"data length must be frames*joints*2 = {T * J * 2}, "
                f"got {len(self.data)}"
            )
        for i, v in enumerate(self.data):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(
                    f"data[{i}] must be number, got {type(v).__name__}={v!r}"
                )
            if not math.isfinite(float(v)):
                raise ValueError(
                    f"data finite required at index {i} (H3 iter-4 — no NaN/Inf), "
                    f"got {v!r}"
                )

        # ── 4. confidence — flat T*J, finite + [0, 1] (H3 iter-4) ─────────
        if not isinstance(self.confidence, list):
            raise ValueError(
                f"confidence must be list, got {type(self.confidence).__name__}"
            )
        if len(self.confidence) != T * J:
            raise ValueError(
                f"confidence length must be frames*joints = {T * J}, "
                f"got {len(self.confidence)}"
            )
        for i, v in enumerate(self.confidence):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(
                    f"confidence[{i}] must be number, got {type(v).__name__}={v!r}"
                )
            fv = float(v)
            if not math.isfinite(fv) or not (0.0 <= fv <= 1.0):
                raise ValueError(
                    f"confidence range [0, 1] finite required at index {i} "
                    f"(H3 iter-4), got {v!r}"
                )

        # ── 5. reliability — len T, item ∈ {"high","medium","low"} ────────
        if not isinstance(self.reliability, list):
            raise ValueError(
                f"reliability must be list, got {type(self.reliability).__name__}"
            )
        if len(self.reliability) != T:
            raise ValueError(
                f"reliability length must be frames = {T}, got {len(self.reliability)}"
            )
        for i, r in enumerate(self.reliability):
            if r not in _VALID_RELIABILITY:
                raise ValueError(
                    f"reliability[{i}] must be one of {sorted(_VALID_RELIABILITY)}, "
                    f"got {r!r}"
                )

        # ── 6. axis_data — flat T*3*2, finite only (R2 + R7 iter-2) ───────
        if not isinstance(self.axis_data, list):
            raise ValueError(
                f"axis_data must be list, got {type(self.axis_data).__name__}"
            )
        if len(self.axis_data) != T * _AXIS_POLYLINE_POINTS * 2:
            raise ValueError(
                f"axis_data length must be frames*3*2 = "
                f"{T * _AXIS_POLYLINE_POINTS * 2}, got {len(self.axis_data)}"
            )
        for i, v in enumerate(self.axis_data):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(
                    f"axis_data[{i}] must be number, got {type(v).__name__}={v!r}"
                )
            if not math.isfinite(float(v)):
                raise ValueError(
                    f"axis_data finite required at index {i} (R7 iter-2 — no NaN/Inf), "
                    f"got {v!r}"
                )

        # ── 7. axis_mask — flat T*3 bool strict (R7 iter-2) ───────────────
        if not isinstance(self.axis_mask, list):
            raise ValueError(
                f"axis_mask must be list, got {type(self.axis_mask).__name__}"
            )
        if len(self.axis_mask) != T * _AXIS_POLYLINE_POINTS:
            raise ValueError(
                f"axis_mask length must be frames*3 = "
                f"{T * _AXIS_POLYLINE_POINTS}, got {len(self.axis_mask)}"
            )
        for i, m in enumerate(self.axis_mask):
            # bool 은 int 의 subclass — type(m) is bool strict check (0/1 false-positive 차단).
            if type(m) is not bool:
                raise ValueError(
                    f"axis_mask[{i}] must be bool strict (H3 iter-4 — "
                    f"int 0/1 reject), got {type(m).__name__}={m!r}"
                )

        # ── 8. warnings — list[str] non-empty ─────────────────────────────
        if not isinstance(self.warnings, list):
            raise ValueError(
                f"warnings must be list, got {type(self.warnings).__name__}"
            )
        for i, w in enumerate(self.warnings):
            if not isinstance(w, str) or not w:
                raise ValueError(
                    f"warnings[{i}] must be non-empty str, "
                    f"got {type(w).__name__}={w!r}"
                )


__all__ = [
    "KeypointName",
    "KeypointReport",
    "NUM_KEYPOINTS_PHASE12",
    "JOINT_KEY_TO_ANGLE_KEY",
    "_KEYPOINT_NAMES",
    "_AXIS_POLYLINE_POINTS",
    "_VALID_RELIABILITY",
]
