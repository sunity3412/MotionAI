"""Phase 8 Force Signals — Layer 1 휴리스틱 + 4 metric 산출 본체.

Plan 08-02 신설 (2026-06-09) — REVIEWS Cycle 1 R1/R2/R3/R4/R5 반영.

본 모듈은 Phase 8 의 본체 산출 layer — Plan 08-00 박제 contract 위에 4 metric
함수 박제:

  - compute_phase_boundaries  : Layer 1 휴리스틱 (preflight gate ceiling 박제)
  - compute_axis_deviation    : pelvis/chest distance from pole axis
  - compute_stability_metrics : jitter (degree/frame) + jerk (deg/sec^3 FPS-normalized)
  - compute_contact_stability : 12 contact point 별 distance/ratio/release detection
  - compute_force_signals     : umbrella (4 metric + overall_confidence + warnings)

REVIEWS Cycle 1 핵심 박제 메모:

  R1 (PoleAxis position 부재):
    point_to_pole_line_distance_2d(point, line) 사용. line=None 시 distance None
    + warning 'pole_line_missing' + coordinate_space='unavailable' (graceful).

  R2 (torso_scale 오용):
    body_scale.median_torso_length(pose_frames, space='image_2d') denominator 사용.
    **body_normalization 모듈 / torso_scale 사용 영구 금지** — drift defense
    test 가 source code grep 검증. observed length 미가용 (valid frame < 5) 시
    None + warning 'scale_unavailable'.

  R3 (contact primitive 불명확):
    yaml entry 의 kind 필드 (keypoint / segment / region_proxy) 별 lookup 분기.
    ContactStabilityMetric = evidence-with-confidence:
      estimated_stable: bool | None (None=evidence 불충분)
      distance_to_pole_norm: distance / observed_torso_length
      near_pole_ratio: phase 내 frame 중 distance <= 0.08 비율
      lost_near_pole_at_ms: distance > 0.20 첫 timestamp (debounce 2 frames)

  R4 (Layer-1 5-phase 미검증):
    Layer 1 confidence default = 'low' (preflight gate 검증 전).
    preflight_label_gate_passed=True → 'medium' 승급.
    preflight_label_gate_passed=False → 'low' + warning 'preflight_label_gate_failed'.
    preflight_label_gate_passed=None  → 'low' + warning 'preflight_gate_pending'.

    REVIEWS Cycle 2 NEW HIGH #2 차단 — `_layer1_confidence_from_preflight` helper
    분리 박제. Plan 08-03 의 Layer 2 success/except 분기가 본 helper 의 ceiling 을
    위로 promote 영구 금지 (ceiling 도구화).

  R5 (FPS-dependent threshold drift):
    _compute_jerk(angles, fps) 안에서 dt=1/fps 정규화 강제 — deg/sec^3 (NOT
    deg/frame^3). JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED 박제.
    jerk_unit='deg_per_sec_cubed' 박제.

    **temporal_fill 호출 영구 금지** — angles 인자는 caller (pipeline._process) 가
    이미 temporal_fill 1회 적용 후 전달. umbrella 의 double smoothing 차단.

per Plan 08-00 contract + Plan 08-01 schema lockstep + REVIEWS Cycle 1.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np
import yaml

from . import dimensions
from .body_scale import median_torso_length
from .pole_geometry import (
    CoordinateSpace,
    PoleAxisMeasurement,
    PoleLine2D,
    point_to_pole_line_distance_2d,
)
from .pose_frame import Keypoint3DAligned, PoleAxis, PoseFrame

if TYPE_CHECKING:
    # Layer 2 hook — Plan 08-03 활성화.
    from ..judging.gemini_moment_extractor import GeminiMomentExtractor  # noqa: F401


log = logging.getLogger(__name__)


# ── Type aliases (Plan 08-01 schema mirror) ────────────────────────────────

# 5-phase motion split (entry → lock → transition → final_shape → hold).
MotionPhase = Literal["entry", "lock", "transition", "final_shape", "hold"]

# axis deviation direction (priority: distance_delta > y_delta > x_delta).
DeviationDirection = Literal[
    "up", "down", "left", "right", "outward", "inward", "unknown"
]

SeverityLevel = Literal["low", "medium", "high"]

MetricConfidence = Literal["low", "medium", "high"]

# 12 contact point — Plan 08-00 §9.0.7 contact 분류 표 정합.
ContactPoint = Literal[
    "left_hand",
    "right_hand",
    "left_inner_thigh",
    "right_inner_thigh",
    "left_knee",
    "right_knee",
    "left_foot",
    "right_foot",
    "left_ankle",
    "right_ankle",
    "hip",
    "unknown",
]


# ── Literal 검증 집합 ──────────────────────────────────────────────────────

_MOTION_PHASES = frozenset(
    {"entry", "lock", "transition", "final_shape", "hold"}
)
_DEVIATION_DIRECTIONS = frozenset(
    {"up", "down", "left", "right", "outward", "inward", "unknown"}
)
_SEVERITY_LEVELS = frozenset({"low", "medium", "high"})
_METRIC_CONFIDENCES = frozenset({"low", "medium", "high"})
_CONTACT_POINTS = frozenset(
    {
        "left_hand",
        "right_hand",
        "left_inner_thigh",
        "right_inner_thigh",
        "left_knee",
        "right_knee",
        "left_foot",
        "right_foot",
        "left_ankle",
        "right_ankle",
        "hip",
        "unknown",
    }
)
_PHASE_SOURCES = frozenset({"heuristic", "gemini_assisted", "heuristic_fallback"})
_SCALE_DENOMINATORS = frozenset({"observed_torso_length", "unavailable"})
_MEASUREMENT_KINDS = frozenset({"keypoint", "segment", "region_proxy"})
_JERK_UNITS = frozenset({"deg_per_sec_cubed"})
_COORDINATE_SPACES = frozenset(
    {"image_2d", "pole_aligned", "world_3d", "unavailable"}
)


# ── Module-level 상수 (Layer 1 휴리스틱 + 4 metric thresholds) ───────────

# Layer 1 휴리스틱 thresholds — IPSF-inspired starting hypothesis (REVIEWS R4).
# belle Pod sweep sanity check 가 manual gate (08-VALIDATION.md).
LAYER1_GROUND_Y_RATIO = 0.85
LAYER1_HAND_POLE_DIST_LOCK = 0.15
LAYER1_VELOCITY_MID = 0.03
LAYER1_VELOCITY_HIGH = 0.06
LAYER1_MIN_PHASE_FRAMES = 2

# AxisDeviationMetric thresholds (normalized to observed_torso_length).
AXIS_PELVIS_DISTANCE_THRESHOLDS = (0.15, 0.30)  # (medium, high)
AXIS_CHEST_DISTANCE_THRESHOLDS = (0.20, 0.40)
AXIS_TILT_THRESHOLDS_DEG = (10.0, 25.0)

# StabilityMetric — jitter is frame-rate dependent (deg/frame).
# jitter_score is frame-rate dependent — DO NOT compare across fps.
JITTER_SEVERITY_THRESHOLDS = (8.0, 20.0)  # deg/frame

# StabilityMetric — jerk FPS-normalized (deg/sec^3, REVIEWS R5).
JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED = (5000.0, 15000.0)

JERK_MAD_K = 3.0
JERK_SMOOTH_WINDOW = 3

UNSTABLE_BODY_PART_THRESHOLD_DEG = 12.0

# ContactStabilityMetric thresholds (observed_torso_length 단위).
CONTACT_PROXIMITY_THRESHOLD_NORM = 0.08
CONTACT_LOST_THRESHOLD_NORM = 0.20
CONTACT_HOLD_MIN_FRAMES = 2
LOST_CONTACT_DEBOUNCE_FRAMES = 2
NEAR_POLE_RATIO_STABLE = 0.8
NEAR_POLE_RATIO_UNSTABLE = 0.3

# overall_confidence weighting.
RELIABILITY_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.3}
LOW_RELIABILITY_PHASE_THRESHOLD = 0.4

# Layer 2 agreement (Plan 08-03 활성화 시 사용).
LAYER_AGREEMENT_TOLERANCE_FRAMES = 2
LAYER_DISAGREEMENT_MAJOR_FRAMES = 5

# body_scale.median_torso_length 의 최소 valid frame 박제 (mirror).
MIN_VALID_FRAMES_FOR_SCALE = 5


# ── 12 contact point lookup tables (Plan 08-00 §9.0.7 정합) ──────────────

# 9 keypoint-direct + unknown.
_CONTACT_POINT_TO_KEYPOINTS: dict[str, str] = {
    "left_hand": "left_wrist",
    "right_hand": "right_wrist",
    "left_knee": "left_knee",
    "right_knee": "right_knee",
    "left_foot": "left_ankle",  # COCO-17 은 foot 키 없음 — ankle 로 근사
    "right_foot": "right_ankle",
    "left_ankle": "left_ankle",
    "right_ankle": "right_ankle",
}

# 2 segment — (start_keypoint, end_keypoint) midpoint.
_CONTACT_POINT_TO_SEGMENT: dict[str, tuple[str, str]] = {
    "left_inner_thigh": ("left_hip", "left_knee"),
    "right_inner_thigh": ("right_hip", "right_knee"),
}

# 1 region_proxy — list of keypoint names → centroid.
_CONTACT_POINT_TO_REGION: dict[str, tuple[str, ...]] = {
    "hip": ("left_hip", "right_hip"),
}

# yaml path — repo root 기준.
_CONTACT_POINTS_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "judging_data"
    / "contact_points.yaml"
)
_CONTACT_POINTS_CACHE: dict | None = None


# ── 5 frozen dataclass (Plan 08-01 schema mirror, REVIEWS Cycle 1 신설 필드) ──


@dataclass(frozen=True)
class PhaseBoundary:
    """5-phase motion split boundary — Layer 1 휴리스틱 산출.

    REVIEWS R4 신설: preflight_label_gate_passed nullable.
      True  = pre-flight 25-timestamp label gate PASS → confidence='medium' 승급
      False = gate FAIL → confidence='low' + warning 'preflight_label_gate_failed'
      None  = gate 미실행 (default) → confidence='low' + warning 'preflight_gate_pending'
    """

    phase: MotionPhase
    start_frame_idx: int
    end_frame_idx: int
    start_ms: int
    end_ms: int
    confidence: MetricConfidence
    source: Literal["heuristic", "gemini_assisted", "heuristic_fallback"]
    preflight_label_gate_passed: bool | None = None

    def __post_init__(self) -> None:
        if self.phase not in _MOTION_PHASES:
            raise ValueError(
                f"phase must be one of {_MOTION_PHASES}, got {self.phase!r}"
            )
        if self.confidence not in _METRIC_CONFIDENCES:
            raise ValueError(
                f"confidence must be one of {_METRIC_CONFIDENCES}, "
                f"got {self.confidence!r}"
            )
        if self.source not in _PHASE_SOURCES:
            raise ValueError(
                f"source must be one of {_PHASE_SOURCES}, got {self.source!r}"
            )


@dataclass(frozen=True)
class AxisDeviationMetric:
    """pelvis/chest distance from pole axis + shoulder/hip tilt.

    REVIEWS R1/R2 신설: coordinate_space + scale_denominator 동행.
      line 미가용 → 모든 distance None + coordinate_space='unavailable' +
        scale_denominator='unavailable' + warning 'pole_line_missing'.
      torso_length 미가용 → distance None + scale_denominator='unavailable' +
        warning 'scale_unavailable'.
    """

    phase: MotionPhase
    pelvis_distance_from_pole_axis: float | None
    chest_distance_from_pole_axis: float | None
    shoulder_tilt: float | None
    hip_tilt: float | None
    deviation_direction: DeviationDirection
    severity: SeverityLevel
    confidence: MetricConfidence
    coordinate_space: CoordinateSpace
    scale_denominator: Literal["observed_torso_length", "unavailable"]
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.phase not in _MOTION_PHASES:
            raise ValueError(
                f"phase must be one of {_MOTION_PHASES}, got {self.phase!r}"
            )
        if self.deviation_direction not in _DEVIATION_DIRECTIONS:
            raise ValueError(
                f"deviation_direction must be one of {_DEVIATION_DIRECTIONS}, "
                f"got {self.deviation_direction!r}"
            )
        if self.severity not in _SEVERITY_LEVELS:
            raise ValueError(
                f"severity must be one of {_SEVERITY_LEVELS}, got {self.severity!r}"
            )
        if self.confidence not in _METRIC_CONFIDENCES:
            raise ValueError(
                f"confidence must be one of {_METRIC_CONFIDENCES}, "
                f"got {self.confidence!r}"
            )
        if self.coordinate_space not in _COORDINATE_SPACES:
            raise ValueError(
                f"coordinate_space must be one of {_COORDINATE_SPACES}, "
                f"got {self.coordinate_space!r}"
            )
        if self.scale_denominator not in _SCALE_DENOMINATORS:
            raise ValueError(
                f"scale_denominator must be one of {_SCALE_DENOMINATORS}, "
                f"got {self.scale_denominator!r}"
            )
        # invariant: coordinate_space='unavailable' ↔ 모든 distance None.
        if self.coordinate_space == "unavailable":
            if (
                self.pelvis_distance_from_pole_axis is not None
                or self.chest_distance_from_pole_axis is not None
            ):
                raise ValueError(
                    "coordinate_space='unavailable' requires all distance "
                    "fields to be None (REVIEWS R1 invariant)"
                )


@dataclass(frozen=True)
class StabilityMetric:
    """phase 내 jitter + jerk + hold_stability_score + unstable_body_parts.

    REVIEWS R5 신설: jerk_unit='deg_per_sec_cubed' (FPS-normalized).
      jitter_score is frame-rate dependent (deg/frame).
      jerk_score is FPS-normalized (deg/sec^3) — same across 9 fps / 18 fps.
    """

    phase: MotionPhase
    jitter_score: float
    jerk_score: float
    jerk_unit: Literal["deg_per_sec_cubed"] = "deg_per_sec_cubed"
    hold_stability_score: float | None = None
    unstable_body_parts: list[str] = field(default_factory=list)
    severity: SeverityLevel = "low"
    confidence: MetricConfidence = "low"
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.phase not in _MOTION_PHASES:
            raise ValueError(
                f"phase must be one of {_MOTION_PHASES}, got {self.phase!r}"
            )
        if self.jerk_unit not in _JERK_UNITS:
            raise ValueError(
                f"jerk_unit must be one of {_JERK_UNITS}, got {self.jerk_unit!r}"
            )
        if self.severity not in _SEVERITY_LEVELS:
            raise ValueError(
                f"severity must be one of {_SEVERITY_LEVELS}, got {self.severity!r}"
            )
        if self.confidence not in _METRIC_CONFIDENCES:
            raise ValueError(
                f"confidence must be one of {_METRIC_CONFIDENCES}, "
                f"got {self.confidence!r}"
            )


@dataclass(frozen=True)
class ContactStabilityMetric:
    """contact point × phase 별 evidence-with-confidence (REVIEWS R3).

    estimated_stable: bool | None (None = evidence 불충분, warning 'contact_evidence_only').
    measurement_kind: motion_id 미인식 시 None (warning 'motion_unrecognized').
    """

    phase: MotionPhase
    contact_point: ContactPoint
    measurement_kind: Literal["keypoint", "segment", "region_proxy"] | None
    estimated_stable: bool | None
    distance_to_pole_norm: float | None
    near_pole_ratio: float | None
    lost_near_pole_at_ms: int | None
    coordinate_space: CoordinateSpace
    severity: SeverityLevel
    confidence: MetricConfidence
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.phase not in _MOTION_PHASES:
            raise ValueError(
                f"phase must be one of {_MOTION_PHASES}, got {self.phase!r}"
            )
        if self.contact_point not in _CONTACT_POINTS:
            raise ValueError(
                f"contact_point must be one of {_CONTACT_POINTS}, "
                f"got {self.contact_point!r}"
            )
        if (
            self.measurement_kind is not None
            and self.measurement_kind not in _MEASUREMENT_KINDS
        ):
            raise ValueError(
                f"measurement_kind must be one of {_MEASUREMENT_KINDS} or None, "
                f"got {self.measurement_kind!r}"
            )
        if self.coordinate_space not in _COORDINATE_SPACES:
            raise ValueError(
                f"coordinate_space must be one of {_COORDINATE_SPACES}, "
                f"got {self.coordinate_space!r}"
            )
        if self.severity not in _SEVERITY_LEVELS:
            raise ValueError(
                f"severity must be one of {_SEVERITY_LEVELS}, got {self.severity!r}"
            )
        if self.confidence not in _METRIC_CONFIDENCES:
            raise ValueError(
                f"confidence must be one of {_METRIC_CONFIDENCES}, "
                f"got {self.confidence!r}"
            )


@dataclass(frozen=True)
class ForceSignalsReport:
    """Phase 8 umbrella — 4 metric + overall_confidence + top-level warnings.

    Firestore lockstep: nested list 회피 — phase_boundaries / axis_metrics /
    stability_metrics / contact_metrics 는 모두 flat list[dict] 으로 박제.
    """

    version: str = "1.0"
    overall_confidence: MetricConfidence = "low"
    warnings: list[str] = field(default_factory=list)
    phase_boundaries: list[PhaseBoundary] = field(default_factory=list)
    axis_metrics: list[AxisDeviationMetric] = field(default_factory=list)
    stability_metrics: list[StabilityMetric] = field(default_factory=list)
    contact_metrics: list[ContactStabilityMetric] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.overall_confidence not in _METRIC_CONFIDENCES:
            raise ValueError(
                f"overall_confidence must be one of {_METRIC_CONFIDENCES}, "
                f"got {self.overall_confidence!r}"
            )


# ── 5 public function stubs (Task 2/3 박제 본체) ──────────────────────────


def compute_phase_boundaries(
    pose_frames: list[PoseFrame],
    pole_axis_measurement: PoleAxisMeasurement,
    body_profile: object | None,
    angles: np.ndarray,
    *,
    motion_id: str | None = None,
    fps: float = 9.0,
    preflight_label_gate_passed: bool | None = None,
    gemini_extractor: object | None = None,
    video_uri: str | None = None,
) -> list[PhaseBoundary]:
    """Layer 1 휴리스틱 5-phase boundary 산출.

    Task 2 에서 본체 박제. preflight_label_gate_passed → confidence 분기 (REVIEWS R4).
    """
    raise NotImplementedError("Task 2 가 본체 박제")


def compute_axis_deviation(
    pose_frames: list[PoseFrame],
    phase_boundaries: list[PhaseBoundary],
    pole_axis_measurement: PoleAxisMeasurement,
    *,
    fps: float = 9.0,
) -> list[AxisDeviationMetric]:
    """pelvis/chest distance from pole axis (image_2d, REVIEWS R1/R2).

    Task 2 에서 본체 박제. point_to_pole_line_distance_2d + median_torso_length 사용.
    body_normalization 모듈 import 영구 금지 (drift defense).
    """
    raise NotImplementedError("Task 2 가 본체 박제")


def compute_stability_metrics(
    angles: np.ndarray,
    phase_boundaries: list[PhaseBoundary],
    pose_frames: list[PoseFrame],
    *,
    fps: float = 9.0,
) -> list[StabilityMetric]:
    """jitter (dimensions.stability_wobble 직접 호출) + jerk (FPS-normalized).

    Task 2 에서 본체 박제. jerk_unit='deg_per_sec_cubed' 강제 (REVIEWS R5).
    """
    raise NotImplementedError("Task 2 가 본체 박제")


def compute_contact_stability(
    pose_frames: list[PoseFrame],
    phase_boundaries: list[PhaseBoundary],
    pole_axis_measurement: PoleAxisMeasurement,
    motion_id: str | None,
    *,
    fps: float = 9.0,
) -> list[ContactStabilityMetric]:
    """12 contact point evidence-with-confidence (REVIEWS R3).

    Task 2 에서 본체 박제. yaml entry 의 kind 별 lookup 분기.
    """
    raise NotImplementedError("Task 2 가 본체 박제")


def compute_force_signals(
    pose_frames: list[PoseFrame],
    pole_axis_measurement: PoleAxisMeasurement,
    body_profile: object | None,
    *,
    angles: np.ndarray,
    fps: float,
    motion_id: str | None = None,
    preflight_label_gate_passed: bool | None = None,
    gemini_extractor: object | None = None,
    video_uri: str | None = None,
) -> ForceSignalsReport:
    """Phase 8 umbrella — 4 metric + overall_confidence + warnings (REVIEWS R5).

    Task 3 에서 본체 박제. angles 인자 = caller (pipeline._process) 가 이미
    temporal_fill 1회 적용 후 전달. **본 함수는 temporal_fill 호출 영구 금지**
    (double smoothing 차단).
    """
    raise NotImplementedError("Task 3 가 본체 박제")


# ── Layer 1 preflight gate ceiling helper (REVIEWS Cycle 2 NEW HIGH #2 정합) ──


def _layer1_confidence_from_preflight(
    preflight_label_gate_passed: bool | None,
) -> tuple[MetricConfidence, list[str]]:
    """preflight gate 3-state → (confidence, warnings) 박제.

    REVIEWS R4 정합 — Layer 1 default = 'low'.

    Plan 08-03 의 Layer 2 success/except 분기가 본 helper 의 ceiling 을
    위로 promote 영구 금지 (REVIEWS Cycle 2 NEW HIGH #2 차단).

    True  → ('medium', [])
    False → ('low', ['preflight_label_gate_failed'])
    None  → ('low', ['preflight_gate_pending'])
    """
    if preflight_label_gate_passed is True:
        return ("medium", [])
    if preflight_label_gate_passed is False:
        return ("low", ["preflight_label_gate_failed"])
    return ("low", ["preflight_gate_pending"])


def _min_confidence(
    agreement: MetricConfidence,
    ceiling: MetricConfidence,
) -> MetricConfidence:
    """min(agreement, ceiling) — Layer 2 success 분기에서 preflight gate ceiling 박제.

    Plan 08-03 의 Layer 2 success/except 분기 모두 본 helper 로 ceiling 적용 강제.
    REVIEWS Cycle 2 NEW HIGH #2 — Layer-2 except 분기가 ceiling 위로 promote 차단.

    order: low < medium < high.
    """
    _ORDER = {"low": 0, "medium": 1, "high": 2}
    if agreement not in _METRIC_CONFIDENCES:
        raise ValueError(
            f"agreement must be one of {_METRIC_CONFIDENCES}, got {agreement!r}"
        )
    if ceiling not in _METRIC_CONFIDENCES:
        raise ValueError(
            f"ceiling must be one of {_METRIC_CONFIDENCES}, got {ceiling!r}"
        )
    if _ORDER[agreement] <= _ORDER[ceiling]:
        return agreement
    return ceiling


__all__ = (
    # Type aliases
    "MotionPhase",
    "DeviationDirection",
    "SeverityLevel",
    "MetricConfidence",
    "ContactPoint",
    # Dataclasses
    "PhaseBoundary",
    "AxisDeviationMetric",
    "StabilityMetric",
    "ContactStabilityMetric",
    "ForceSignalsReport",
    # Public functions
    "compute_phase_boundaries",
    "compute_axis_deviation",
    "compute_stability_metrics",
    "compute_contact_stability",
    "compute_force_signals",
    # Layer 1 preflight ceiling helpers (Plan 08-03 reuse)
    "_layer1_confidence_from_preflight",
    "_min_confidence",
)
