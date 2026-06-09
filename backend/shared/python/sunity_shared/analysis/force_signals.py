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


# ── 4 metric 함수 본체 + 25+ private helper ──────────────────────────────


# ── compute_phase_boundaries: Layer 1 휴리스틱 (REVIEWS R4) ───────────────


def _should_invoke_layer2(
    motion_id: str | None,
    gemini_extractor: object | None,
    video_uri: str | None,
) -> bool:
    """Layer 2 hook (Plan 08-03 활성화). 본 plan 항상 False."""
    return False


def _layer1_heuristic_boundaries(
    pose_frames: list[PoseFrame],
    angles: np.ndarray,
) -> list[tuple[str, int, int]]:
    """5-phase split — entry / lock / transition / final_shape / hold.

    Layer 1 휴리스틱 — frame 수 균등 분할 starting hypothesis. belle Pod sweep
    sanity check (08-VALIDATION.md) 가 manual gate.

    Edge cases:
      T < 10 frames → single 'hold' phase.
      all-NaN angles → single 'hold' phase (heavy occlusion).

    Returns:
      list of (phase_name, start_frame_idx, end_frame_idx). end-exclusive.
    """
    T = len(pose_frames)
    if T < 10:
        return [("hold", 0, T)]
    # all-NaN angles → 휴리스틱 신호 부족 → single hold.
    if angles.size > 0 and np.all(np.isnan(angles)):
        return [("hold", 0, T)]

    # 균등 분할 starting hypothesis — belle 검수 후 boundary 조정 예정.
    e1 = max(LAYER1_MIN_PHASE_FRAMES, T // 5)
    e2 = max(e1 + LAYER1_MIN_PHASE_FRAMES, 2 * T // 5)
    e3 = max(e2 + LAYER1_MIN_PHASE_FRAMES, 3 * T // 5)
    e4 = max(e3 + LAYER1_MIN_PHASE_FRAMES, 4 * T // 5)
    return [
        ("entry", 0, e1),
        ("lock", e1, e2),
        ("transition", e2, e3),
        ("final_shape", e3, e4),
        ("hold", e4, T),
    ]


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
    """Layer 1 휴리스틱 5-phase boundary 산출 (REVIEWS R4).

    preflight_label_gate_passed → confidence 분기:
      True  → 'medium' / False → 'low' + warning / None → 'low' + warning.

    Layer 2 (Plan 08-03 활성화) — _should_invoke_layer2 가 본 plan 항상 False.
    """
    # Layer 2 hook — 본 plan 본체 = no-op.
    if _should_invoke_layer2(motion_id, gemini_extractor, video_uri):
        # Plan 08-03 가 Layer 2 활성화.
        pass

    raw = _layer1_heuristic_boundaries(pose_frames, angles)
    base_confidence, _base_warnings = _layer1_confidence_from_preflight(
        preflight_label_gate_passed
    )
    # motion_id 미인식 시 source='heuristic_fallback'.
    source: Literal[
        "heuristic", "gemini_assisted", "heuristic_fallback"
    ] = "heuristic" if motion_id else "heuristic_fallback"

    boundaries: list[PhaseBoundary] = []
    dt_ms = 1000.0 / fps if fps > 0 else 111.0
    for phase_name, s, e in raw:
        boundaries.append(
            PhaseBoundary(
                phase=phase_name,  # type: ignore[arg-type]
                start_frame_idx=s,
                end_frame_idx=e,
                start_ms=int(round(s * dt_ms)),
                end_ms=int(round(e * dt_ms)),
                confidence=base_confidence,
                source=source,
                preflight_label_gate_passed=preflight_label_gate_passed,
            )
        )
    return boundaries


# ── compute_axis_deviation: REVIEWS R1 + R2 ─────────────────────────────


def _observed_torso_length(pose_frames: list[PoseFrame]) -> float | None:
    """body_scale.median_torso_length(image_2d) 단순 호출. REVIEWS R2 정합."""
    return median_torso_length(pose_frames, space="image_2d")


def _kp2d_xy(frame: PoseFrame, name: str) -> tuple[float, float] | None:
    """frame.keypoints_2d 에서 (x, y) 추출. 결손 시 None."""
    kp2d = frame.keypoints_2d
    if not kp2d or name not in kp2d:
        return None
    kp = kp2d[name]
    x, y = float(kp.x), float(kp.y)
    if not (np.isfinite(x) and np.isfinite(y)):
        return None
    return (x, y)


def _midpoint(p1: tuple[float, float], p2: tuple[float, float]) -> tuple[float, float]:
    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


def _pelvis_position_image_2d(frame: PoseFrame) -> tuple[float, float] | None:
    """left_hip + right_hip midpoint (image_2d). missing → None."""
    lh = _kp2d_xy(frame, "left_hip")
    rh = _kp2d_xy(frame, "right_hip")
    if lh is None or rh is None:
        return None
    return _midpoint(lh, rh)


def _chest_position_image_2d(frame: PoseFrame) -> tuple[float, float] | None:
    """left_shoulder + right_shoulder midpoint."""
    ls = _kp2d_xy(frame, "left_shoulder")
    rs = _kp2d_xy(frame, "right_shoulder")
    if ls is None or rs is None:
        return None
    return _midpoint(ls, rs)


def _line_direction_angle_deg(line: PoleLine2D) -> float:
    """pole line 의 image 평면 방향 각 (degrees, atan2)."""
    dx, dy = line.direction_image
    return float(np.degrees(np.arctan2(dy, dx)))


def _shoulder_tilt_2d(frame: PoseFrame, line: PoleLine2D) -> float | None:
    """shoulder line vs pole line direction angle (signed degrees)."""
    ls = _kp2d_xy(frame, "left_shoulder")
    rs = _kp2d_xy(frame, "right_shoulder")
    if ls is None or rs is None:
        return None
    sh_dx = rs[0] - ls[0]
    sh_dy = rs[1] - ls[1]
    sh_angle = float(np.degrees(np.arctan2(sh_dy, sh_dx)))
    return sh_angle - _line_direction_angle_deg(line)


def _hip_tilt_2d(frame: PoseFrame, line: PoleLine2D) -> float | None:
    """hip line vs pole line direction angle."""
    lh = _kp2d_xy(frame, "left_hip")
    rh = _kp2d_xy(frame, "right_hip")
    if lh is None or rh is None:
        return None
    hp_dx = rh[0] - lh[0]
    hp_dy = rh[1] - lh[1]
    hp_angle = float(np.degrees(np.arctan2(hp_dy, hp_dx)))
    return hp_angle - _line_direction_angle_deg(line)


def _severity_from_distance(
    distance: float | None,
    thresholds: tuple[float, float],
) -> SeverityLevel:
    """thresholds = (medium_cutoff, high_cutoff)."""
    if distance is None or not np.isfinite(distance):
        return "low"
    if distance >= thresholds[1]:
        return "high"
    if distance >= thresholds[0]:
        return "medium"
    return "low"


def _max_severity(*levels: SeverityLevel) -> SeverityLevel:
    """low < medium < high. 최대 반환."""
    order = {"low": 0, "medium": 1, "high": 2}
    best: SeverityLevel = "low"
    for s in levels:
        if order[s] > order[best]:
            best = s
    return best


def _deviation_direction_from_pelvis(
    frame_positions: list[tuple[float, float]],
    line: PoleLine2D,
) -> DeviationDirection:
    """positions 의 중심 vs pole line 의 위치 관계 → outward/inward/up/down 등.

    image 평면 기준: line 의 normal 방향으로 멀어지면 outward.
    """
    if not frame_positions:
        return "unknown"
    # mean position.
    mx = float(np.mean([p[0] for p in frame_positions]))
    my = float(np.mean([p[1] for p in frame_positions]))
    # line origin + direction.
    x0, y0 = line.point_image
    dx, dy = line.direction_image
    # signed perpendicular distance (cross product 부호) → 좌/우.
    cross = (mx - x0) * dy - (my - y0) * dx
    # signed projection along direction → 위/아래.
    proj = (mx - x0) * dx + (my - y0) * dy
    abs_cross = abs(cross)
    abs_proj = abs(proj)
    # outward / inward 결정: signed_perpendicular_distance 의 절대값이 크면 outward.
    if abs_cross > abs_proj:
        return "outward"
    if proj > 0:
        return "down"
    return "up"


def compute_axis_deviation(
    pose_frames: list[PoseFrame],
    phase_boundaries: list[PhaseBoundary],
    pole_axis_measurement: PoleAxisMeasurement,
    *,
    fps: float = 9.0,
) -> list[AxisDeviationMetric]:
    """pelvis/chest distance from pole axis + tilt (REVIEWS R1 + R2).

    line 미가용 → distance None + coordinate_space='unavailable' + warning.
    torso_length 미가용 → distance None + scale_denominator='unavailable' + warning.
    """
    line = pole_axis_measurement.line
    torso_length = _observed_torso_length(pose_frames)

    if line is None:
        coordinate_space: CoordinateSpace = "unavailable"
        scale_denominator: Literal[
            "observed_torso_length", "unavailable"
        ] = "unavailable"
        warnings_base = ["pole_line_missing"]
        if torso_length is None:
            warnings_base.append("scale_unavailable")
        return [
            AxisDeviationMetric(
                phase=b.phase,
                pelvis_distance_from_pole_axis=None,
                chest_distance_from_pole_axis=None,
                shoulder_tilt=None,
                hip_tilt=None,
                deviation_direction="unknown",
                severity="low",
                confidence="low",
                coordinate_space=coordinate_space,
                scale_denominator=scale_denominator,
                warnings=list(warnings_base),
            )
            for b in phase_boundaries
        ]

    # line 가용.
    coordinate_space = "image_2d"
    if torso_length is None:
        scale_denominator = "unavailable"
        scale_warnings = ["scale_unavailable"]
    else:
        scale_denominator = "observed_torso_length"
        scale_warnings = []

    metrics: list[AxisDeviationMetric] = []
    for b in phase_boundaries:
        phase_frames = pose_frames[b.start_frame_idx : b.end_frame_idx]
        # pelvis distances.
        pelvis_positions = [
            p for p in (_pelvis_position_image_2d(f) for f in phase_frames) if p is not None
        ]
        chest_positions = [
            p for p in (_chest_position_image_2d(f) for f in phase_frames) if p is not None
        ]
        # raw distances.
        pelvis_dists_raw = [
            point_to_pole_line_distance_2d(p, line) for p in pelvis_positions
        ]
        chest_dists_raw = [
            point_to_pole_line_distance_2d(p, line) for p in chest_positions
        ]
        # tilts.
        shoulder_tilts = [
            t
            for t in (_shoulder_tilt_2d(f, line) for f in phase_frames)
            if t is not None
        ]
        hip_tilts = [
            t for t in (_hip_tilt_2d(f, line) for f in phase_frames) if t is not None
        ]

        # normalize if torso_length 가용. 아니면 None + warning.
        if torso_length is not None and pelvis_dists_raw:
            pelvis_dist: float | None = float(np.median(pelvis_dists_raw)) / torso_length
        else:
            pelvis_dist = None
        if torso_length is not None and chest_dists_raw:
            chest_dist: float | None = float(np.median(chest_dists_raw)) / torso_length
        else:
            chest_dist = None

        shoulder_tilt_val = float(np.median(shoulder_tilts)) if shoulder_tilts else None
        hip_tilt_val = float(np.median(hip_tilts)) if hip_tilts else None

        # severity.
        sev_pelvis = _severity_from_distance(
            pelvis_dist, AXIS_PELVIS_DISTANCE_THRESHOLDS
        )
        sev_chest = _severity_from_distance(
            chest_dist, AXIS_CHEST_DISTANCE_THRESHOLDS
        )
        sev_shoulder = _severity_from_distance(
            abs(shoulder_tilt_val) if shoulder_tilt_val is not None else None,
            AXIS_TILT_THRESHOLDS_DEG,
        )
        sev_hip = _severity_from_distance(
            abs(hip_tilt_val) if hip_tilt_val is not None else None,
            AXIS_TILT_THRESHOLDS_DEG,
        )
        severity = _max_severity(sev_pelvis, sev_chest, sev_shoulder, sev_hip)

        # deviation direction.
        if pelvis_positions:
            direction = _deviation_direction_from_pelvis(pelvis_positions, line)
        else:
            direction = "unknown"

        # confidence (frame 신뢰도 기반).
        if torso_length is None:
            metric_confidence: MetricConfidence = "low"
        elif phase_frames:
            high_count = sum(
                1 for f in phase_frames if getattr(f, "reliability", "low") == "high"
            )
            ratio = high_count / max(1, len(phase_frames))
            if ratio >= 0.7:
                metric_confidence = "medium"
            elif ratio >= LOW_RELIABILITY_PHASE_THRESHOLD:
                metric_confidence = "low"
            else:
                metric_confidence = "low"
        else:
            metric_confidence = "low"

        metrics.append(
            AxisDeviationMetric(
                phase=b.phase,
                pelvis_distance_from_pole_axis=pelvis_dist,
                chest_distance_from_pole_axis=chest_dist,
                shoulder_tilt=shoulder_tilt_val,
                hip_tilt=hip_tilt_val,
                deviation_direction=direction,
                severity=severity,
                confidence=metric_confidence,
                coordinate_space=coordinate_space,
                scale_denominator=scale_denominator,
                warnings=list(scale_warnings),
            )
        )

    return metrics


# ── compute_stability_metrics: REVIEWS R5 FPS-normalized ────────────────


def _compute_jerk(angles_window: np.ndarray, fps: float) -> float:
    """3차 미분 (deg/sec^3) — dt=1/fps 정규화 강제 (REVIEWS R5).

    deg/frame^3 → deg/sec^3 conversion: divide by dt^3.
    MAD outlier rejection — median + JERK_MAD_K * MAD 초과 제거.
    """
    if angles_window.shape[0] < 5:
        return 0.0
    dt = 1.0 / fps if fps > 0 else 1.0
    # 3차 미분: deg/frame^3.
    raw_jerk_per_frame = np.abs(np.diff(angles_window, n=3, axis=0))
    # → deg/sec^3 (FPS-normalized).
    jerk_per_sec_cubed = raw_jerk_per_frame / (dt ** 3)
    # MAD outlier rejection (per-joint).
    median = np.nanmedian(jerk_per_sec_cubed, axis=0)
    mad = np.nanmedian(np.abs(jerk_per_sec_cubed - median), axis=0)
    threshold = median + JERK_MAD_K * mad
    filtered = np.where(
        jerk_per_sec_cubed > threshold, np.nan, jerk_per_sec_cubed
    )
    result = float(np.nanmedian(filtered))
    if not np.isfinite(result):
        return 0.0
    return result


def _compute_unstable_body_parts(
    angles_window: np.ndarray,
) -> list[str]:
    """dimensions.stability_wobble_by_joint reuse + threshold filter."""
    if angles_window.shape[0] < 2:
        return []
    by_joint = dimensions.stability_wobble_by_joint(angles_window, profile=None)
    return [
        name
        for name, wobble in by_joint.items()
        if wobble > UNSTABLE_BODY_PART_THRESHOLD_DEG
    ]


def _severity_from_jitter(jitter: float) -> SeverityLevel:
    medium, high = JITTER_SEVERITY_THRESHOLDS
    if jitter >= high:
        return "high"
    if jitter >= medium:
        return "medium"
    return "low"


def _severity_from_jerk(jerk: float) -> SeverityLevel:
    medium, high = JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED
    if jerk >= high:
        return "high"
    if jerk >= medium:
        return "medium"
    return "low"


def compute_stability_metrics(
    angles: np.ndarray,
    phase_boundaries: list[PhaseBoundary],
    pose_frames: list[PoseFrame],
    *,
    fps: float = 9.0,
) -> list[StabilityMetric]:
    """phase 별 jitter (deg/frame) + jerk (deg/sec^3 FPS-normalized) + unstable parts.

    jitter_score = dimensions.stability_wobble(sliced) 직접 호출 (drift defense).
    jerk_score = _compute_jerk(sliced, fps) (REVIEWS R5).
    hold_stability_score = phase=='hold' 일 때만, dimensions.stability_wobble.
    """
    a = np.asarray(angles, dtype=float)
    if a.ndim != 2:
        raise ValueError("angles must be (T, J) 2D array")

    metrics: list[StabilityMetric] = []
    for b in phase_boundaries:
        s, e = b.start_frame_idx, b.end_frame_idx
        sliced = a[s:e]
        if sliced.shape[0] < 2:
            jitter = 0.0
            jerk = 0.0
            unstable: list[str] = []
        else:
            jitter = float(dimensions.stability_wobble(sliced, profile=None))
            jerk = _compute_jerk(sliced, fps)
            unstable = _compute_unstable_body_parts(sliced)

        hold_score: float | None = None
        if b.phase == "hold" and sliced.shape[0] >= 2:
            hold_score = float(dimensions.stability_wobble(sliced, profile=None))

        # severity = max(jitter, jerk) severity.
        sev = _max_severity(
            _severity_from_jitter(jitter),
            _severity_from_jerk(jerk),
        )

        # confidence — phase 내 frame reliability 비율.
        phase_frames = pose_frames[s:e] if pose_frames else []
        warnings_list: list[str] = []
        if phase_frames:
            high_count = sum(
                1 for f in phase_frames if getattr(f, "reliability", "low") == "high"
            )
            low_count = sum(
                1 for f in phase_frames if getattr(f, "reliability", "low") == "low"
            )
            ratio_low = low_count / max(1, len(phase_frames))
            if ratio_low >= LOW_RELIABILITY_PHASE_THRESHOLD:
                metric_confidence: MetricConfidence = "low"
                warnings_list.append("occlusion_high_in_phase")
            elif high_count / max(1, len(phase_frames)) >= 0.7:
                metric_confidence = "medium"
            else:
                metric_confidence = "low"
        else:
            metric_confidence = "low"

        metrics.append(
            StabilityMetric(
                phase=b.phase,
                jitter_score=jitter,
                jerk_score=jerk,
                jerk_unit="deg_per_sec_cubed",
                hold_stability_score=hold_score,
                unstable_body_parts=unstable,
                severity=sev,
                confidence=metric_confidence,
                warnings=warnings_list,
            )
        )

    return metrics


# ── compute_contact_stability: REVIEWS R3 evidence-with-confidence ──────


def _load_expected_contact_points(motion_id: str | None) -> list[dict]:
    """yaml.safe_load + motion_id lookup + cache."""
    global _CONTACT_POINTS_CACHE
    if _CONTACT_POINTS_CACHE is None:
        try:
            with open(_CONTACT_POINTS_PATH) as f:
                _CONTACT_POINTS_CACHE = yaml.safe_load(f)
        except (OSError, yaml.YAMLError) as exc:
            log.warning("contact_points.yaml load failed: %s", exc)
            _CONTACT_POINTS_CACHE = {"motions": {}, "default": {"expected_contact_points": []}}
    if motion_id is None:
        return []
    motions = _CONTACT_POINTS_CACHE.get("motions", {})
    entry = motions.get(motion_id)
    if entry is None:
        return []
    return list(entry.get("expected_contact_points", []))


def _contact_point_position(
    contact_point: str,
    kind: str,
    frame: PoseFrame,
) -> tuple[float, float] | None:
    """kind 별 lookup — keypoint / segment / region_proxy.

    image_2d 좌표 반환. missing keypoint → None.
    """
    if kind == "keypoint":
        kp_name = _CONTACT_POINT_TO_KEYPOINTS.get(contact_point)
        if kp_name is None:
            return None
        return _kp2d_xy(frame, kp_name)
    if kind == "segment":
        seg = _CONTACT_POINT_TO_SEGMENT.get(contact_point)
        if seg is None:
            return None
        p1 = _kp2d_xy(frame, seg[0])
        p2 = _kp2d_xy(frame, seg[1])
        if p1 is None or p2 is None:
            return None
        return _midpoint(p1, p2)
    if kind == "region_proxy":
        region = _CONTACT_POINT_TO_REGION.get(contact_point)
        if region is None:
            return None
        positions = [
            p for p in (_kp2d_xy(frame, name) for name in region) if p is not None
        ]
        if not positions:
            return None
        cx = float(np.mean([p[0] for p in positions]))
        cy = float(np.mean([p[1] for p in positions]))
        return (cx, cy)
    return None


def _detect_contact_evidence(
    contact_point: str,
    kind: str,
    phase_frames: list[PoseFrame],
    line: PoleLine2D,
    torso_length: float,
    *,
    fps: float,
) -> tuple[bool | None, float | None, float | None, int | None]:
    """phase 내 contact_point evidence 산출.

    Returns:
      (estimated_stable, distance_to_pole_norm, near_pole_ratio, lost_near_pole_at_ms).
    """
    distances: list[float] = []
    timestamps: list[int] = []
    for f in phase_frames:
        pos = _contact_point_position(contact_point, kind, f)
        if pos is None:
            continue
        raw = point_to_pole_line_distance_2d(pos, line)
        if not np.isfinite(raw):
            continue
        distances.append(raw / torso_length)
        timestamps.append(int(getattr(f, "timestamp_ms", 0)))

    if len(distances) < CONTACT_HOLD_MIN_FRAMES:
        return (None, None, None, None)

    arr = np.asarray(distances, dtype=float)
    distance_norm = float(np.median(arr))
    near_count = int(np.sum(arr <= CONTACT_PROXIMITY_THRESHOLD_NORM))
    ratio = float(near_count) / float(len(arr))

    # estimated_stable.
    if ratio >= NEAR_POLE_RATIO_STABLE and len(arr) >= CONTACT_HOLD_MIN_FRAMES:
        stable: bool | None = True
    elif ratio < NEAR_POLE_RATIO_UNSTABLE:
        stable = False
    else:
        stable = None  # evidence 불충분.

    # lost_near_pole_at_ms — debounce 2 frames.
    lost_at: int | None = None
    consecutive = 0
    for i, d in enumerate(arr):
        if d > CONTACT_LOST_THRESHOLD_NORM:
            consecutive += 1
            if consecutive >= LOST_CONTACT_DEBOUNCE_FRAMES:
                lost_at = timestamps[i]
                break
        else:
            consecutive = 0

    return (stable, distance_norm, ratio, lost_at)


def _detect_abnormal_release(
    metric: ContactStabilityMetric,
    phase_boundaries: list[PhaseBoundary],
) -> str | None:
    """lock.start_ms <= lost_near_pole_at_ms <= hold.end_ms → abnormal release."""
    if metric.lost_near_pole_at_ms is None:
        return None
    lock = next((b for b in phase_boundaries if b.phase == "lock"), None)
    hold = next((b for b in phase_boundaries if b.phase == "hold"), None)
    if lock is None or hold is None:
        return None
    if lock.start_ms <= metric.lost_near_pole_at_ms <= hold.end_ms:
        return "abnormal_release_during_hold"
    return None


def _severity_from_contact_ratio(ratio: float | None) -> SeverityLevel:
    """near_pole_ratio → severity. high ratio = low severity."""
    if ratio is None:
        return "low"
    if ratio >= NEAR_POLE_RATIO_STABLE:
        return "low"
    if ratio >= NEAR_POLE_RATIO_UNSTABLE:
        return "medium"
    return "high"


def compute_contact_stability(
    pose_frames: list[PoseFrame],
    phase_boundaries: list[PhaseBoundary],
    pole_axis_measurement: PoleAxisMeasurement,
    motion_id: str | None,
    *,
    fps: float = 9.0,
) -> list[ContactStabilityMetric]:
    """12 contact point evidence-with-confidence (REVIEWS R3).

    motion_id None / 미인식 → fallback (measurement_kind=None +
    estimated_stable=None + warning 'motion_unrecognized').
    """
    line = pole_axis_measurement.line
    torso_length = _observed_torso_length(pose_frames)
    expected = _load_expected_contact_points(motion_id)

    coordinate_space: CoordinateSpace = (
        "image_2d" if line is not None else "unavailable"
    )

    results: list[ContactStabilityMetric] = []

    if not expected:
        # motion_id 미인식 fallback.
        fallback_points: list[dict] = [
            {"name": "left_hand", "kind": "keypoint"},
            {"name": "right_hand", "kind": "keypoint"},
            {"name": "left_foot", "kind": "keypoint"},
            {"name": "right_foot", "kind": "keypoint"},
        ]
        for b in phase_boundaries:
            for fb in fallback_points:
                warnings_list = ["motion_unrecognized", "contact_evidence_only"]
                if line is None:
                    warnings_list.append("pole_line_missing")
                if torso_length is None:
                    warnings_list.append("scale_unavailable")
                results.append(
                    ContactStabilityMetric(
                        phase=b.phase,
                        contact_point=fb["name"],  # type: ignore[arg-type]
                        measurement_kind=None,
                        estimated_stable=None,
                        distance_to_pole_norm=None,
                        near_pole_ratio=None,
                        lost_near_pole_at_ms=None,
                        coordinate_space="unavailable" if line is None else "image_2d",
                        severity="low",
                        confidence="low",
                        warnings=warnings_list,
                    )
                )
        return results

    # 정상 path — yaml entry 별 산출.
    for b in phase_boundaries:
        phase_frames = pose_frames[b.start_frame_idx : b.end_frame_idx]
        for entry in expected:
            contact_name = entry["name"]
            kind = entry["kind"]

            if line is None or torso_length is None:
                # evidence 산출 불가.
                stable: bool | None = None
                dist_norm: float | None = None
                ratio: float | None = None
                lost_at: int | None = None
            else:
                stable, dist_norm, ratio, lost_at = _detect_contact_evidence(
                    contact_name, kind, phase_frames, line, torso_length, fps=fps
                )

            warnings_list = []
            if line is None:
                warnings_list.append("pole_line_missing")
            if torso_length is None:
                warnings_list.append("scale_unavailable")
            if stable is None and (line is not None and torso_length is not None):
                warnings_list.append("contact_evidence_only")

            severity = _severity_from_contact_ratio(ratio)
            metric_confidence: MetricConfidence = (
                "medium" if (line is not None and torso_length is not None and stable is not None) else "low"
            )

            metric = ContactStabilityMetric(
                phase=b.phase,
                contact_point=contact_name,  # type: ignore[arg-type]
                measurement_kind=kind,  # type: ignore[arg-type]
                estimated_stable=stable,
                distance_to_pole_norm=dist_norm,
                near_pole_ratio=ratio,
                lost_near_pole_at_ms=lost_at,
                coordinate_space=coordinate_space,
                severity=severity,
                confidence=metric_confidence,
                warnings=warnings_list,
            )
            # abnormal release detection — frozen dataclass 박제 시 dataclasses.replace.
            abnormal = _detect_abnormal_release(metric, phase_boundaries)
            if abnormal is not None:
                from dataclasses import replace

                metric = replace(
                    metric,
                    warnings=list(metric.warnings) + [abnormal],
                )
            results.append(metric)

    return results


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
