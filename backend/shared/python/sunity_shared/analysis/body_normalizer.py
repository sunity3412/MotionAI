"""body_normalizer — Kinematic Tree Bone-Length Reprojection + IPSF GeometricCriterion 절대 deficit + bodyNormalizationConfidence 산출. pure numpy.

Phase 6 (2026-06-08) BodyComparisonReport 본체.

박제 결정 (D-06-*):
  D-06-A1: 점수 보정 + scale ratio 메타 둘 다 출력.
  D-06-A2: 변환 방향 B (프로 reference → 수강생 체형 좌표계). 사용자 영상 위에
           "내 키로 환산된 정은지 자세" 표시.
  D-06-A3: 5 필드 (estimatedHeightScale + armScale + legScale + torsoScale +
           shoulderHipRatio) 모두 활용. shoulderHipRatio 는 키포인트 reproject
           에만 적용 — 점수 차원에는 미적용 (메모리 [[scoring-dimensions-ipsf]] 박제).
  D-06-A4: mode + confidence 병행 게이트. coaching 모드 + confidence ≥ 0.5
           → 정규화 ON. confidence < 0.5 → OFF + warning.
  D-06-B1: mode3 first = Page 9 절대 트랙 단독 (기본) + confidence 높음 + Gemini
           motion 인식 성공 시 자동 매칭 reference fallback.
  D-06-B2: reference-motions 컬렉션에 BodyProfile 필드 추가.
  D-06-B3: 통합 BodyComparisonReport + comparisonType (3 cases 만 —
           mode1 / mode3_first / mode3_progress).
  D-06-U1: Universal Principle — confidence-tiered hybrid.

belle 직접 인용 (2026-06-08): "분석이 제대로 되는 게 목표".

메모리 인용:
  - [[scoring-dimensions-ipsf]]: shoulderHipRatio 점수 차원 미적용. 균형/대칭 차원 제거.
  - [[ipsf-5-track-scoring]]: Page 9 단독 트랙 (mode3 first reference 없음 fallback).
  - [[license-blocklist-pose]]: SMPL/SMPL-X 사용 금지 — 본 모듈 numpy + stdlib only.
  - [[firestore-nested-array-flat]]: (T, J) 행렬 flat 저장. BodyComparisonSourcePose.values 도 flat.

8 warning enum (R2 fix — reference_source_pose_missing 추가):
  - low_confidence_normalization_off: confidence < 0.5 시 정규화 OFF.
  - foreshortening_off: foreshortening 감지 시 shoulderHipRatio 폭 보정 OFF.
  - shoulder_hip_ratio_off: shoulderHipRatio 폭 보정 OFF (foreshortening 동반).
  - temporal_variance_high: temporal variance > 10% (Notebook §4.2).
  - spatial_dispersion_high: spatial dispersion > 1.0 penalty.
  - reference_profile_missing: reference_profile=None + comparison_type != 'mode3_first'.
  - fallback_reference_not_found: mode3_first Gemini fallback 매칭 실패 (caller-injected, R8).
  - reference_source_pose_missing: source_keypoints=None (caller-injected, R2 fix).

C1 fix (2026-06-08 reviews revision):
  normalize_pose_by_segments 시그너처 = (source_keypoints, source_profile,
  target_profile, target_torso_px). L_ref = _ref_segment_ratio(parent, child,
  target_profile) × target_torso_px. target = student.
  이전 시그너처 (pro raw kpts + pro profile + student torso) 는
  L_ref = pro_profile_ratio × student_torso 로 uniform scale 로 degenerate.
  segment-aware 가 되려면 L_ref 는 student(target) 의 segment ratio 를 써야 한다.

C14 fix (2026-06-08 reviews revision):
  deficit code 'bad_angle' → 'pose_reliability_low'.
  IPSF Page 21 의 'bad angle' (judge 가 카메라 가림으로 angle 을 관찰 못함) 과
  본 시스템의 'pose confidence frame ratio > 0.5' 측정은 의미가 다르다.
  divergence note: docs/contract.md §8.

R2 fix (2026-06-08 round-2):
  신규 dataclass BodyComparisonSourcePose — Firestore reference 컬렉션에 영속될
  대표 hold frame 의 17 keypoint × 4채널 (x, y, z, confidence). flat values
  array (nested-array 회피) + to_keypoints_array reshape helper.

R5 fix (2026-06-08 round-2):
  spatial_dispersion_penalty 산식 자연화 = clip((C_s/shoulder_width -
  DISPERSION_BASELINE) / DISPERSION_RANGE, 0, 1). high dispersion → high penalty.

R6 fix (2026-06-08 round-2):
  to_coco17_array(pose_frames) 사용해 (T, 17, 4) 4채널 보존. 자체 (T,17,3) stack 금지.

R8 fix (2026-06-08 round-2):
  compare_body_profiles 시그너처에 extra_warnings 파라미터 추가. caller-injected
  warnings 를 frozenset 으로 validate. dataclasses.replace 우회 금지.

R9 fix (2026-06-08 round-2):
  '7 deficits' 옛 표현 정정 — 5 IPSF GeometricCriterion + 1 Sunity 자체
  pose_reliability_low. poor_transitions v1.5 deferred (Phase 8 jerk/jitter 통합).

R10 fix (2026-06-08 round-2):
  source_profile 인자는 reserved/debug. 현 구현 비사용 — 회귀 방지 test 박제.

3-way lockstep:
  - TS 미러: app/src/types/analysis.ts BodyComparisonReport / BodyComparisonSourcePose interface
  - docs/contract.md §8 + §8.2 명세
  - 변경 시 3 파일 동시 갱신 (CLAUDE.md Cross-cutting).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from .body_normalization import BodyNormalizationProfile
from .pose_frame import PoseFrame, to_coco17_array
from .skeleton import KEYPOINT_NAMES


# ── 상수 (body_normalization_measurer.py:37-73 패턴 정합) ──────────────

# Kinematic Tree (RESEARCH.md §Pattern 1). mid_hip = root. 13 edge.
# mid_shoulder / mid_hip 은 가상 keypoint (left/right 평균).
KINEMATIC_TREE_EDGES: tuple[tuple[str, str], ...] = (
    ("mid_hip", "mid_shoulder"),       # torso (root → mid_shoulder)
    ("mid_shoulder", "left_shoulder"),
    ("mid_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("right_shoulder", "right_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_elbow", "right_wrist"),
    ("mid_hip", "left_hip"),
    ("mid_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("right_hip", "right_knee"),
    ("left_knee", "left_ankle"),
    ("right_knee", "right_ankle"),
)

# D-06-A4 게이트
CONFIDENCE_GATE: float = 0.5

# Notebook §1.5 — foreshortening
FORESHORTENING_ANGLE_DEG: float = 60.0
SHOULDER_HIP_HARD_THRESHOLD_PX: float = 150.0

# Notebook §4.2 — temporal variance
TEMPORAL_VARIANCE_RATIO_THRESHOLD: float = 0.10
TEMPORAL_VARIANCE_EXCELLENT_THRESHOLD: float = 0.05

# R5 fix (2026-06-08 round-2) — spatial dispersion 산식 자연화
# 정상 자세의 C_s/shoulder_width 평균 추정값 = 1.5.
# dispersion_ratio == BASELINE (1.5) → penalty 0.0.
# dispersion_ratio == BASELINE + RANGE (3.0) → penalty 1.0.
DISPERSION_BASELINE: float = 1.5
DISPERSION_RANGE: float = 1.5

# dimensions.py:_LINE_TOL_DEG 재사용 — IPSF 각도 허용오차 20°
LINE_TOL_DEG: float = 20.0

# C14 fix — pose_reliability_low deficit 산출 임계.
# 평균 keypoint confidence < 0.4 인 frame 의 비율 > 0.5 이면 deficit 추가.
POSE_RELIABILITY_LOW_CONF_THRESHOLD: float = 0.4
POSE_RELIABILITY_LOW_FRAME_RATIO: float = 0.5

_EPS: float = 1e-8

# R2 fix — 8 warning enum frozen (reference_source_pose_missing 포함).
BODY_COMPARISON_WARNING_CODES: frozenset[str] = frozenset({
    "low_confidence_normalization_off",
    "foreshortening_off",
    "shoulder_hip_ratio_off",
    "temporal_variance_high",
    "spatial_dispersion_high",
    "reference_profile_missing",
    "fallback_reference_not_found",
    "reference_source_pose_missing",  # R2 fix — 신규 8번째
})


# ── ComparisonType (D-06-B3, W1 — 3 cases 만) ────────────────────────────

ComparisonType = Literal["mode1", "mode3_first", "mode3_progress"]


# ── ScaleProfile (D-06-A3 — 5 numeric + 1 bool 필드) ─────────────────────

@dataclass(frozen=True)
class ScaleProfile:
    """프로/수강생 체형 scale ratio (D-06-A3 — 5 필드 + apply 플래그).

    estimated_height_scale: 전체 키 비율 (target/source).
    arm_scale: 팔 길이 비율.
    leg_scale: 다리 길이 비율.
    torso_scale: 몸통 길이 비율.
    shoulder_hip_ratio: 어깨너비/골반너비 비율 — 점수 차원에는 미적용 (D-06-A3).
    shoulder_hip_ratio_applied: 폭 보정 적용 여부 (foreshortening 시 False).

    __post_init__ validator (Phase 2 v5 패턴 정합):
      5 numeric 필드 finite + strictly positive (>0). ValueError on violation.
    """

    estimated_height_scale: float
    arm_scale: float
    leg_scale: float
    torso_scale: float
    shoulder_hip_ratio: float
    shoulder_hip_ratio_applied: bool

    def __post_init__(self) -> None:
        for fname in (
            "estimated_height_scale",
            "arm_scale",
            "leg_scale",
            "torso_scale",
            "shoulder_hip_ratio",
        ):
            v = getattr(self, fname)
            if not math.isfinite(v):
                raise ValueError(
                    f"{fname} must be finite (no NaN/inf), got {v}"
                )
            if v <= 0.0:
                raise ValueError(
                    f"{fname} must be strictly positive (>0), got {v}"
                )


# ── BodyComparisonSourcePose (R2 fix 2026-06-08 round-2) ──────────────────

@dataclass(frozen=True)
class BodyComparisonSourcePose:
    """R2 fix (2026-06-08 round-2). reference 측 대표 hold frame 의 17 keypoint × 4채널 (x, y, z, confidence). Firestore reference 컬렉션에 flat values 형태로 영속 (nested-array 회피 — [[firestore-nested-array-flat]]). Plan 06-02 mode1 + mode3 fallback path 가 본 dataclass 를 fetch 해서 compare_body_profiles 의 source_keypoints 인자로 to_keypoints_array() 변환 후 전달.

    필드:
      joint_keys: RTMW COCO-17 joint 이름 17개.
      values: flat float array. 길이 = 4 × len(joint_keys).
        순서 = [x_0, y_0, z_0, c_0, x_1, y_1, z_1, c_1, ...].
      frame_index: 대표 frame 의 원본 frame index (디버깅용).
      torso_px: mid_shoulder ↔ mid_hip 픽셀 거리 (scale anchor).
      confidence: 0.0~1.0 — 대표 frame 의 평균 keypoint confidence.
      measured_at: unix ms timestamp.

    __post_init__ validator (T-06-01-05 mitigation):
      len(values) == 4 * len(joint_keys) — ValueError 위반 시.
      모든 values 가 math.isfinite — ValueError 위반 시.
      0 <= confidence <= 1.0 — ValueError 위반 시.
      torso_px > 0 — ValueError 위반 시.
    """

    joint_keys: tuple[str, ...]
    values: tuple[float, ...]
    frame_index: int
    torso_px: float
    confidence: float
    measured_at: int

    def __post_init__(self) -> None:
        expected_len = 4 * len(self.joint_keys)
        if len(self.values) != expected_len:
            raise ValueError(
                f"BodyComparisonSourcePose.values length must be 4 × "
                f"len(joint_keys) = {expected_len}, got {len(self.values)}"
            )
        for i, v in enumerate(self.values):
            if not math.isfinite(v):
                raise ValueError(
                    f"BodyComparisonSourcePose.values[{i}] must be finite, "
                    f"got {v}"
                )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"BodyComparisonSourcePose.confidence must be in [0, 1], "
                f"got {self.confidence}"
            )
        if self.torso_px <= 0.0 or not math.isfinite(self.torso_px):
            raise ValueError(
                f"BodyComparisonSourcePose.torso_px must be > 0 and finite, "
                f"got {self.torso_px}"
            )

    def to_keypoints_array(self) -> np.ndarray:
        """flat values → (J, 4) ndarray (x, y, z, confidence).

        compare_body_profiles 가 source_keypoints 로 변환할 때 사용.
        """
        return np.array(self.values, dtype=np.float32).reshape(
            len(self.joint_keys), 4
        )


# ── _ref_segment_ratio helper ─────────────────────────────────────────────

# 각 edge → BodyNormalizationProfile 5 필드 매핑.
# torso_scale, arm_scale, leg_scale, shoulder_hip_ratio 의 비율로 L_ref 산출.
def _ref_segment_ratio(
    parent: str,
    child: str,
    profile: BodyNormalizationProfile,
    *,
    apply_shoulder_hip_ratio: bool,
) -> float:
    """target_profile (student) 의 segment ratio 를 반환.

    13 edge → 5 필드 매핑:
      - mid_hip → mid_shoulder: torso_scale (1.0 self-reference).
      - mid_shoulder ↔ l/r_shoulder: shoulder_hip_ratio (apply 시) 또는 neutral 0.25.
      - mid_hip ↔ l/r_hip: 1.0 / shoulder_hip_ratio (apply 시) 또는 neutral 0.25.
      - 상완/전완 50/50 분할 (Assumption A1) — arm_scale × 0.5.
      - 대퇴/하퇴 50/50 분할 — leg_scale × 0.5.

    apply_shoulder_hip_ratio=False 시 폭 보정 OFF — mid_shoulder ↔ l/r_shoulder
    + mid_hip ↔ l/r_hip = neutral 0.25 (Phase 2 v5 회귀 안전망).

    L_ref 절대 픽셀 = ratio × target_torso_px (caller 가 곱함).
    """
    # torso (root → mid_shoulder)
    if (parent, child) == ("mid_hip", "mid_shoulder"):
        return profile.torso_scale  # = 1.0 (self-reference)

    # shoulder widths
    if (parent, child) in (
        ("mid_shoulder", "left_shoulder"),
        ("mid_shoulder", "right_shoulder"),
    ):
        if apply_shoulder_hip_ratio:
            # 어깨너비 = shoulder_hip_ratio × hip_width 의 절반.
            # 상대 ratio = shoulder_hip_ratio × 0.25 (단순 패턴, Phase 2 v5 정합).
            return profile.shoulder_hip_ratio * 0.25
        return 0.25  # neutral

    # hip widths
    if (parent, child) in (
        ("mid_hip", "left_hip"),
        ("mid_hip", "right_hip"),
    ):
        if apply_shoulder_hip_ratio:
            # 골반너비 = (1 / shoulder_hip_ratio) × 0.25
            ratio = profile.shoulder_hip_ratio if profile.shoulder_hip_ratio > _EPS else 1.0
            return (1.0 / ratio) * 0.25
        return 0.25

    # upper arms (50/50 split)
    if (parent, child) in (
        ("left_shoulder", "left_elbow"),
        ("right_shoulder", "right_elbow"),
    ):
        return profile.arm_scale * 0.5

    # forearms
    if (parent, child) in (
        ("left_elbow", "left_wrist"),
        ("right_elbow", "right_wrist"),
    ):
        return profile.arm_scale * 0.5

    # thighs (50/50 split)
    if (parent, child) in (
        ("left_hip", "left_knee"),
        ("right_hip", "right_knee"),
    ):
        return profile.leg_scale * 0.5

    # shanks
    if (parent, child) in (
        ("left_knee", "left_ankle"),
        ("right_knee", "right_ankle"),
    ):
        return profile.leg_scale * 0.5

    raise KeyError(f"_ref_segment_ratio: unknown edge ({parent}, {child})")


# ── normalize_pose_by_segments — C1 fix ───────────────────────────────────

def normalize_pose_by_segments(
    source_keypoints: dict[str, tuple[float, float, float]],
    source_profile: BodyNormalizationProfile,
    target_profile: BodyNormalizationProfile,
    target_torso_px: float,
    *,
    apply_shoulder_hip_ratio: bool = True,
) -> dict[str, tuple[float, float, float]]:
    """방향 B (D-06-A2) — source 의 모션을 target scale 로 reproject.

    source 의 키포인트가 제공하는 것은 '각 edge 의 방향 단위벡터' 뿐이며, 뼈
    길이는 target_profile 의 segment ratio × target_torso_px 로 새로 산출된다.

    C1 fix (2026-06-08 reviews): 이전 시그너처 (pro raw kpts + pro profile +
    student torso) 는 L_ref = pro_profile_ratio × student_torso 였고,
    이는 'pro 의 비율을 student 의 전체 크기로 일괄 축소' = uniform scale
    normalization 으로 degenerate. segment-aware 가 되려면 L_ref 는 student
    (target) 의 segment ratio 를 써야 한다. 그래야 동일 키 + 다른 팔/다리
    비율 두 student 가 서로 다른 normalized pose 를 받는다.

    R10 fix (2026-06-08 round-2): source_profile 인자는 의도적으로 사용 안 함.
    향후 source ↔ target 비교 디버깅이 필요하면 본 인자 활용. 현 구현이
    source_profile 을 사용하면 회귀 — test_normalize_pose_by_segments_output_
    independent_of_source_profile 가 detection.

    Args:
        source_keypoints: 변환 대상 (방향 B 에서는 pro/정은지) raw 키포인트.
          dict[str, (x, y, z)] — 방향 벡터의 source.
        source_profile: source 의 BodyProfile. **현 구현 비사용** (debugging
          reserved 인자).
        target_profile: 결과 좌표가 따라야 할 비율의 출처 (방향 B 에서는 student).
          L_ref 산출의 단독 소스.
        target_torso_px: target 영상에서 측정한 target 본인 torso 픽셀 길이
          (절대 스케일 anchor).
        apply_shoulder_hip_ratio: foreshortening 시 False — 폭 보정 OFF.

    Returns:
        dict[str, (x, y, z)] — reproject 된 keypoints. mid_hip / mid_shoulder
        가상 keypoint 도 포함. endpoint 미감지 edge 는 skip.
    """
    # unused source_profile — R10 fix (회귀 방지). 사용 시 R10 test fail.
    del source_profile  # noqa: F841

    # 1단계: mid_hip 가상 keypoint = (left_hip + right_hip) 평균 — source 기반.
    if "left_hip" not in source_keypoints or "right_hip" not in source_keypoints:
        raise ValueError(
            "normalize_pose_by_segments: source_keypoints must contain "
            "left_hip + right_hip (mid_hip root 계산용)"
        )
    lh = source_keypoints["left_hip"]
    rh = source_keypoints["right_hip"]
    mid_hip_raw = (
        (lh[0] + rh[0]) / 2,
        (lh[1] + rh[1]) / 2,
        (lh[2] + rh[2]) / 2,
    )

    # mid_shoulder 가상 keypoint = (left_shoulder + right_shoulder) 평균.
    if (
        "left_shoulder" not in source_keypoints
        or "right_shoulder" not in source_keypoints
    ):
        raise ValueError(
            "normalize_pose_by_segments: source_keypoints must contain "
            "left_shoulder + right_shoulder"
        )
    ls = source_keypoints["left_shoulder"]
    rs = source_keypoints["right_shoulder"]
    mid_shoulder_raw = (
        (ls[0] + rs[0]) / 2,
        (ls[1] + rs[1]) / 2,
        (ls[2] + rs[2]) / 2,
    )

    # source raw keypoints 확장 (가상 keypoint 추가).
    source_raw_ext: dict[str, tuple[float, float, float]] = dict(source_keypoints)
    source_raw_ext["mid_hip"] = mid_hip_raw
    source_raw_ext["mid_shoulder"] = mid_shoulder_raw

    # Root Centering — normalized output 의 root = mid_hip_raw (위치 보존).
    norm: dict[str, tuple[float, float, float]] = {}
    norm["mid_hip"] = mid_hip_raw  # root 위치는 source 기준 보존

    # 2단계: KINEMATIC_TREE_EDGES 순회. 각 edge:
    #   v_unit = (C_source - P_source) / ||C_source - P_source||
    #   L_ref = _ref_segment_ratio(parent, child, target_profile) × target_torso_px
    #   C_norm = P_norm + v_unit × L_ref
    for parent, child in KINEMATIC_TREE_EDGES:
        # endpoint 둘 다 source_raw_ext 에 있을 때만 reproject
        if parent not in source_raw_ext or child not in source_raw_ext:
            continue
        if parent not in norm:
            # parent 가 아직 norm 에 없으면 skip — tree 가 root→leaf 순서가
            # 깨졌거나 endpoint 미감지로 인한 누락
            continue

        p_src = source_raw_ext[parent]
        c_src = source_raw_ext[child]
        dx = c_src[0] - p_src[0]
        dy = c_src[1] - p_src[1]
        dz = c_src[2] - p_src[2]
        norm_len = math.sqrt(dx * dx + dy * dy + dz * dz)
        if norm_len < _EPS:
            # zero-length edge — skip (raw 키포인트 동일 위치).
            continue
        ux = dx / norm_len
        uy = dy / norm_len
        uz = dz / norm_len

        ratio = _ref_segment_ratio(
            parent,
            child,
            target_profile,
            apply_shoulder_hip_ratio=apply_shoulder_hip_ratio,
        )
        L_ref = ratio * target_torso_px

        p_norm = norm[parent]
        c_norm = (
            p_norm[0] + ux * L_ref,
            p_norm[1] + uy * L_ref,
            p_norm[2] + uz * L_ref,
        )
        norm[child] = c_norm

    return norm
