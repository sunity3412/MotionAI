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

Phase 32 (32-14, D-22 1단) — 표시층 8→12 승격:
  - _KEYPOINT_NAMES 에 left/right_ankle + left/right_elbow append (legacy 8 순서 불변).
  - 감점 무유입: 각도층 skeleton.JOINT_ANGLES·kismam·dimensions 무접촉.
  - 하위호환: joints 배열 길이가 capability source — legacy 8 doc 과 신규 12 doc
    을 소비처가 길이로 판별 (version 필드는 참고).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal


# ── KeypointName Literal (R11 정합 + 32-14 D-22 1단 확장 — 12 body keypoint) ──
# axis 는 별도 axisData (compute_axis_frames 산출) — 본 enum 에 포함 X.
# Phase 32 (32-14): RTMW 백본이 이미 검출하는 발목·팔꿈치를 표시층으로 승격.
# 감점 반영(2단)은 관절별 신뢰도 실측 게이트 뒤 — 각도층(skeleton.JOINT_ANGLES)·
# 감점 모듈은 본 확장에서 무접촉 (T-32-34 mitigate).

KeypointName = Literal[
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_hand",
    "right_hand",
    "left_ankle",
    "right_ankle",
    "left_elbow",
    "right_elbow",
]
"""12 body keypoint enum (8 legacy + 32-14 발목·팔꿈치 4) — KeypointOverlay 라벨 lookup.

`left_hand` / `right_hand` 는 COCO-17 의 `left_wrist` / `right_wrist` 에
매핑된다 (loose hand 박제). ankle/elbow 는 COCO-17 동명 키 1:1 (32-14).
하위호환: 기존 doc 은 joints 8 — **joints 배열이 capability source** (길이 판별).
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
    # ── 32-14 (D-22 1단) 신규 — legacy 8 뒤에 append (기존 8 순서 불변) ──
    "left_ankle",
    "right_ankle",
    "left_elbow",
    "right_elbow",
)

NUM_KEYPOINTS_PHASE12: int = len(_KEYPOINT_NAMES)
"""12 — KeypointReport.joints 방출 길이 (len 파생 — 하드코딩 금지, 32-14).

legacy doc 은 8 (phase12~32-13 방출분). 소비처는 상수가 아니라 각 doc 의
joints 배열 길이를 신뢰할 것 (capability source).
"""

_AXIS_POLYLINE_POINTS: int = 3
"""R2 정합 — axisData polyline = shoulder_mid + hip_mid + knee_mid?."""

_VALID_RELIABILITY: frozenset[str] = frozenset({"high", "medium", "low"})

# COCO-17 → KeypointName 매핑 (assemble.build_keypoint_report 가 사용).
# left_hand → left_wrist 등 loose mapping 박제.
# 32-14: ankle/elbow 는 COCO-17 동명 키 1:1 (RTMW _build_keypoints_2d_from_rtmw
# 가 skeleton.KEYPOINT_NAMES 17개 전수를 keypoints_2d 에 채움 — 추출만 확장).
JOINT_KEY_TO_ANGLE_KEY: dict[str, str] = {
    "left_shoulder": "left_shoulder",
    "right_shoulder": "right_shoulder",
    "left_hip": "left_hip",
    "right_hip": "right_hip",
    "left_knee": "left_knee",
    "right_knee": "right_knee",
    "left_hand": "left_wrist",
    "right_hand": "right_wrist",
    "left_ankle": "left_ankle",
    "right_ankle": "right_ankle",
    "left_elbow": "left_elbow",
    "right_elbow": "right_elbow",
}


@dataclass(frozen=True)
class KeypointReport:
    """Phase 12 신설 — KeypointOverlay 소비.

    10 필드 (R10 + R7 iter-2 정합):
      version        : str (non-empty, "1.0" legacy / "1.1" 32-14 12관절 — 참고용,
                        판별은 joints 길이 = capability source)
      joints         : list[str] (len == 8(legacy) | 12(32-14 확장), _KEYPOINT_NAMES tuple)
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


def upsample_to_fps(
    report: KeypointReport, target_fps: float
) -> KeypointReport:
    """KeypointReport 시각 frame rate 만 target_fps 로 선형 보간.

    Phase 12 hotfix (2026-06-11 belle UAT 1차):
      - 분석 알고리즘 (DTW / threshold / Phase 6/7/8 calibration) 은 9fps 유지.
      - KeypointOverlay 시각 부드러움만 위해 저장 시점에 30fps 로 upsample.
      - Firestore size 3.3x (170 KiB → ~560 KiB, 예산 < 700 KiB 안).

    `data` / `confidence` / `axis_data` = 선형 보간.
    `reliability` / `axis_mask` = nearest-neighbor (categorical / boolean).
    `warnings` = 그대로 유지 (per-frame 아님).

    target_fps <= report.fps → 원본 반환.
    report.frames < 2 → 원본 반환 (보간 불가).
    """
    if target_fps <= report.fps:
        return report
    if report.frames < 2:
        return report

    src_frames = report.frames
    src_duration = src_frames / report.fps
    new_frames = int(round(src_duration * target_fps))
    if new_frames <= src_frames:
        return report

    J = len(report.joints)
    # new_t : 0..src_frames-1 범위의 float 위치 (보간 인덱스)
    new_t = [
        min(max(i * (report.fps / target_fps), 0.0), float(src_frames - 1))
        for i in range(new_frames)
    ]

    def _interp_flat(src: list[float], outer: int) -> list[float]:
        """flat src[T * outer] 를 new_frames * outer 로 선형 보간."""
        out: list[float] = [0.0] * (new_frames * outer)
        for n, t in enumerate(new_t):
            lo = int(t)
            hi = min(lo + 1, src_frames - 1)
            w = t - lo
            for c in range(outer):
                a = src[lo * outer + c]
                b = src[hi * outer + c]
                out[n * outer + c] = a + (b - a) * w
        return out

    def _nearest_per_frame(src: list, length: int) -> list:
        """per-frame[T] 을 new_frames 로 nearest-neighbor 복제."""
        return [src[min(int(round(t)), length - 1)] for t in new_t]

    new_data = _interp_flat(report.data, J * 2)
    new_confidence = _interp_flat(report.confidence, J)
    new_axis_data = _interp_flat(report.axis_data, _AXIS_POLYLINE_POINTS * 2)
    new_reliability = _nearest_per_frame(report.reliability, src_frames)
    new_axis_mask_per_frame = _nearest_per_frame(
        [
            report.axis_mask[t * _AXIS_POLYLINE_POINTS : (t + 1) * _AXIS_POLYLINE_POINTS]
            for t in range(src_frames)
        ],
        src_frames,
    )
    new_axis_mask: list[bool] = []
    for chunk in new_axis_mask_per_frame:
        new_axis_mask.extend(chunk)

    return KeypointReport(
        version=report.version,
        joints=list(report.joints),
        frames=new_frames,
        fps=float(target_fps),
        data=new_data,
        confidence=new_confidence,
        reliability=new_reliability,
        axis_data=new_axis_data,
        axis_mask=new_axis_mask,
        warnings=list(report.warnings),
    )


__all__ = [
    "KeypointName",
    "KeypointReport",
    "NUM_KEYPOINTS_PHASE12",
    "JOINT_KEY_TO_ANGLE_KEY",
    "_KEYPOINT_NAMES",
    "_AXIS_POLYLINE_POINTS",
    "_VALID_RELIABILITY",
    "upsample_to_fps",
]
