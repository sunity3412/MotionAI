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
  warnings 를 frozenset 으로 validate. 우회 패턴 (dataclass replace helper) 금지.

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


# ── foreshortening 검출 (Notebook §1.5, Pattern 5) ────────────────────────


def is_foreshortening_detected(pose_frames: list[PoseFrame] | None) -> bool:
    """Notebook §1.5 — foreshortening 감지.

    조건 (둘 다 OR):
      1. 어깨-골반 벡터 vs 카메라 Z축 (0, 0, 1) 평균 각도 < FORESHORTENING_ANGLE_DEG (60°).
      2. 평균 어깨-골반 픽셀 거리 < SHOULDER_HIP_HARD_THRESHOLD_PX (150px).

    하나라도 만족 시 True. pose_frames=None or 빈 list → False.

    Pitfall 1 — 폴 위 거꾸로 매달려 몸 둥글게 마는 동작: 2D 투영 평면에서
    어깨-골반 픽셀 거리 ≈ 0 → 분모 폭발 → 모든 키포인트 오차 증폭 위양성.
    """
    if not pose_frames:
        return False

    distances: list[float] = []
    angles_deg: list[float] = []
    for f in pose_frames:
        kp = f.keypoints_3d
        needed = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
        if not all(n in kp for n in needed):
            continue
        ls, rs, lh, rh = (kp[n] for n in needed)
        msx = (ls.x + rs.x) / 2
        msy = (ls.y + rs.y) / 2
        msz = (ls.z + rs.z) / 2
        mhx = (lh.x + rh.x) / 2
        mhy = (lh.y + rh.y) / 2
        mhz = (lh.z + rh.z) / 2
        dx = mhx - msx
        dy = mhy - msy
        dz = mhz - msz
        pixel_d = math.sqrt(dx * dx + dy * dy)  # 2D image plane
        distances.append(pixel_d)
        # vs camera Z (0, 0, 1) — 어깨-골반 vector 의 z-component 의 비율
        vec_norm = math.sqrt(dx * dx + dy * dy + dz * dz)
        if vec_norm < _EPS:
            continue
        cos_a = abs(dz) / vec_norm  # |cos angle with z-axis|
        cos_a = max(-1.0, min(1.0, cos_a))
        # 각도 (벡터 - z축) = arccos(|cos_a|). z-축과 평행할수록 0°, 직교할수록 90°.
        # 정상 직립 = 어깨-골반 vector 가 y-down 평면 = z 와 직교 = 90°.
        # 누운 자세 (foreshortening) = z-축 평행 = 0°.
        angle_deg = math.degrees(math.acos(cos_a))
        # camera 시선이 z-축이라면, vector ⊥ z 이면 angle == 90°.
        # foreshortening 조건 = angle < FORESHORTENING_ANGLE_DEG.
        # 우리 fixture z=0 인 경우 angle=90° (정상 직립) — z-축 평행 케이스 없음.
        # → 본 분기에서 pixel 거리 임계만 의미. (현 합성 데이터 한계, prod NLF z 사용)
        angles_deg.append(angle_deg)

    if not distances:
        return False

    mean_dist = sum(distances) / len(distances)
    if mean_dist < SHOULDER_HIP_HARD_THRESHOLD_PX:
        return True
    if angles_deg:
        mean_angle = sum(angles_deg) / len(angles_deg)
        if mean_angle < FORESHORTENING_ANGLE_DEG:
            return True
    return False


# ── temporal variance + spatial dispersion helper ────────────────────────


def _compute_temporal_variance_per_segment(
    pose_frames: list[PoseFrame], segment_pair: tuple[str, str]
) -> tuple[float, float]:
    """단일 segment 의 (normalized_variance, mean_length).

    normalized_variance = var(length over frames) / mean(length)^2.
    NaN-safe — mean < EPS 시 (0.0, 0.0).
    """
    start_name, end_name = segment_pair
    lengths: list[float] = []
    for f in pose_frames:
        kp = f.keypoints_3d
        if start_name not in kp or end_name not in kp:
            continue
        s = kp[start_name]
        e = kp[end_name]
        L = math.sqrt((e.x - s.x) ** 2 + (e.y - s.y) ** 2 + (e.z - s.z) ** 2)
        lengths.append(L)
    if not lengths:
        return 0.0, 0.0
    mean_L = sum(lengths) / len(lengths)
    if mean_L < _EPS:
        return 0.0, 0.0
    var = sum((x - mean_L) ** 2 for x in lengths) / len(lengths)
    normalized_var = var / (mean_L * mean_L)
    return normalized_var, mean_L


def _compute_spatial_dispersion(pose_frames: list[PoseFrame]) -> float:
    """Notebook §4.2 B — C_s(t) = (1/J) Σ_j ||P_j(t) - centroid(t)||₂.

    shoulder_width 로 정규화 (frame-wise). 전체 frame 평균 반환.
    NaN-safe.

    R6 fix: pose_frames → keypoints 변환은 to_coco17_array(pose_frames) 사용해
    (T, 17, 4) 4채널 보존. joint_uncertainty 가 4번째 채널에서 lookup.
    """
    if not pose_frames:
        return 0.0
    # R6 fix — to_coco17_array (T, 17, 4) 4채널 보존
    arr_4ch = to_coco17_array(pose_frames)  # (T, 17, 4)
    # 좌표만 (T, 17, 3) — 4번째 channel = uncertainty_proxy (현 산식 비사용)
    coords = arr_4ch[:, :, :3]
    T = coords.shape[0]
    if T == 0:
        return 0.0
    ratios: list[float] = []
    # shoulder index (left_shoulder=5, right_shoulder=6 in KEYPOINT_NAMES)
    ls_idx = KEYPOINT_NAMES.index("left_shoulder")
    rs_idx = KEYPOINT_NAMES.index("right_shoulder")
    for t in range(T):
        frame_coords = coords[t]  # (17, 3)
        # NaN mask
        valid_mask = np.all(np.isfinite(frame_coords), axis=1)
        if not np.any(valid_mask):
            continue
        valid_pts = frame_coords[valid_mask]
        centroid = valid_pts.mean(axis=0)
        dists = np.linalg.norm(valid_pts - centroid, axis=1)
        c_s = float(dists.mean())
        # shoulder width
        ls = frame_coords[ls_idx]
        rs = frame_coords[rs_idx]
        if not (np.all(np.isfinite(ls)) and np.all(np.isfinite(rs))):
            continue
        sw = float(np.linalg.norm(rs - ls))
        if sw > _EPS:
            ratios.append(c_s / sw)
    if not ratios:
        return 0.0
    return sum(ratios) / len(ratios)


# ── compute_body_normalization_confidence (D-06-U1 박제) ──────────────────


# temporal variance 산출에 사용하는 5 핵심 segment.
_TEMPORAL_SEGMENT_PAIRS: tuple[tuple[str, str], ...] = (
    ("left_shoulder", "left_elbow"),    # l_upper_arm
    ("left_elbow", "left_wrist"),       # l_lower_arm
    ("left_hip", "left_knee"),          # l_thigh
    ("left_knee", "left_ankle"),        # l_lower_leg
    ("left_shoulder", "left_hip"),      # torso (간이)
)


def compute_body_normalization_confidence(
    pose_frames: list[PoseFrame] | None,
    student_profile: BodyNormalizationProfile,
    reference_profile: BodyNormalizationProfile | None,
    comparison_type: ComparisonType,
) -> tuple[float, list[str]]:
    """RESEARCH.md §Pattern 3 — confidence 산식 + warnings emit.

    1) base = student_profile.confidence.
    2) pose_frames=None or 빈 list → temporal_penalty = spatial_dispersion_penalty
       = 0.0. base + reference_match_bonus 만.
    3) pose_frames 있을 때:
       - R6 fix: keypoints_4ch = to_coco17_array(pose_frames) (T, 17, 4).
       - temporal_penalty = 5 핵심 segment 의 normalized_variance 평균.
         clip ((variance - 0.05) / 0.05, 0, 1).
    4) R5 fix — spatial_dispersion_penalty:
       - dispersion_ratio = _compute_spatial_dispersion(pose_frames)
       - penalty = clip((dispersion_ratio - DISPERSION_BASELINE) /
         DISPERSION_RANGE, 0.0, 1.0). high dispersion → high penalty.
    5) reference_match_bonus = 0.0 if reference_profile is None
       else 0.1 × min(reference_profile.confidence, 1.0).
    6) confidence = clamp(0, 1, base - 0.5*temporal_penalty -
       0.3*spatial_dispersion_penalty + reference_match_bonus).
    7) warnings:
       - temporal_penalty > 0.5 → 'temporal_variance_high'.
       - R5 fix: spatial_dispersion_penalty > 0.5 → 'spatial_dispersion_high'.
       - reference_profile is None + comparison_type != 'mode3_first' →
         'reference_profile_missing'.
    """
    base = float(student_profile.confidence)
    warnings: list[str] = []

    if pose_frames is None or len(pose_frames) == 0:
        temporal_penalty = 0.0
        spatial_dispersion_penalty = 0.0
    else:
        # R6 fix — to_coco17_array 사용. 호출 자체가 temporal_penalty 산출과
        # spatial dispersion 산출 path 의 일관성 보장.
        _ = to_coco17_array(pose_frames)  # 4채널 보존 보장 (회귀 가드)

        variances = []
        for pair in _TEMPORAL_SEGMENT_PAIRS:
            v, _mean = _compute_temporal_variance_per_segment(pose_frames, pair)
            # normalized_variance = (std/mean)^2. ratio = std/mean = sqrt(var).
            variances.append(math.sqrt(v))
        avg_var_ratio = sum(variances) / len(variances) if variances else 0.0
        # ratio 0.05 baseline ~ 5% (excellent), 0.10 → penalty=1.0
        temporal_penalty = max(
            0.0,
            min(
                1.0,
                (avg_var_ratio - TEMPORAL_VARIANCE_EXCELLENT_THRESHOLD)
                / TEMPORAL_VARIANCE_EXCELLENT_THRESHOLD,
            ),
        )

        # R5 fix — spatial dispersion 산식 자연화
        dispersion_ratio = _compute_spatial_dispersion(pose_frames)
        spatial_dispersion_penalty = max(
            0.0,
            min(
                1.0,
                (dispersion_ratio - DISPERSION_BASELINE) / DISPERSION_RANGE,
            ),
        )

    reference_match_bonus = (
        0.0
        if reference_profile is None
        else 0.1 * min(float(reference_profile.confidence), 1.0)
    )

    confidence = (
        base
        - 0.5 * temporal_penalty
        - 0.3 * spatial_dispersion_penalty
        + reference_match_bonus
    )
    confidence = max(0.0, min(1.0, confidence))

    if temporal_penalty > 0.5:
        warnings.append("temporal_variance_high")
    if spatial_dispersion_penalty > 0.5:
        warnings.append("spatial_dispersion_high")
    if reference_profile is None and comparison_type != "mode3_first":
        warnings.append("reference_profile_missing")

    return confidence, warnings


# ── BodyComparisonFinding (IPSF deficit + Sunity pose_reliability_low) ───

# R9 fix (2026-06-08 round-2): 5 IPSF geometric + 1 Sunity 자체 신호.
# '7 deficits' 옛 표현 사용 금지. poor_transitions v1.5 deferred (Phase 8 통합).
_DEFICIT_CODES: frozenset[str] = frozenset({
    "knee_toe_alignment",
    "clean_lines",
    "extension",
    "posture",
    "body_placement",
    "pose_reliability_low",  # C14 fix — 구 bad_angle rename
})


@dataclass(frozen=True)
class BodyComparisonFinding:
    """단일 IPSF GeometricCriterion deficit (RESEARCH.md Example 1).

    R9 fix (2026-06-08 round-2): 5 IPSF geometric + 1 Sunity pose_reliability_low.

    C14 fix (2026-06-08 reviews): deficit_code enum 6종. 'bad_angle' → 'pose_reliability_low' rename.
    IPSF Page 21 의 'bad angle' (judge 가 카메라 가림으로 angle 을 관찰 못함) 과
    본 시스템의 'pose-estimation confidence frame 비율' 측정은 의미가 다르다.
    docs/contract.md §8.1 divergence note 참조.

    필드:
      deficit_code: 6 enum 중 하나.
      joint_key: nullable — finding 이 단일 관절에 귀속될 때만.
      measured_value: 측정값 (각도 deg / 거리 px).
      deduction_score: IPSF Page 21 절대 감점 (-0.2, -0.5).
      confidence: 0.0~1.0.
      body_type_adjusted: 정규화된 keypoint 에서 측정되었는지 (True = 정규화 좌표,
        False = raw 좌표). 체형 ratio 를 deduction 에 직접 곱하지 않는 것이 핵심.
    """

    deficit_code: str
    joint_key: str | None
    measured_value: float
    deduction_score: float
    confidence: float
    body_type_adjusted: bool

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"BodyComparisonFinding.confidence must be in [0, 1], "
                f"got {self.confidence}"
            )


# ── BodyComparisonReport (W1 3 ComparisonType + usedReferenceFallback) ──


@dataclass(frozen=True)
class BodyComparisonReport:
    """체형 정규화 비교 리포트 (D-06-B3 통합 schema + 3 ComparisonType, W1).

    TS camelCase ↔ Python snake_case 1:1 (3-way lockstep — analysis.ts +
    docs/contract.md §8 동시 갱신).

    W1: comparison_type 은 3 cases (mode1 / mode3_first / mode3_progress).
        Gemini fallback 신호는 sibling boolean `used_reference_fallback` (default False).
        mode3_first + used_reference_fallback=True 로 처리.

    Phase 12 / 12.5 / Phase 7 downstream 이 comparisonType 으로 UI / 로직 분기.
    """

    comparison_type: ComparisonType
    body_normalization_confidence: float
    scale_profile: ScaleProfile | None = None
    findings: list[BodyComparisonFinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reference_motion_id: str | None = None
    reference_athlete_name: str | None = None
    previous_analysis_id: str | None = None
    used_reference_fallback: bool = False  # W1 — Gemini fallback 신호

    def __post_init__(self) -> None:
        # confidence 범위
        if not (0.0 <= self.body_normalization_confidence <= 1.0):
            raise ValueError(
                f"body_normalization_confidence must be in [0, 1], "
                f"got {self.body_normalization_confidence}"
            )
        # comparison_type literal 검증
        if self.comparison_type not in ("mode1", "mode3_first", "mode3_progress"):
            raise ValueError(
                f"comparison_type must be one of (mode1, mode3_first, "
                f"mode3_progress), got {self.comparison_type!r}"
            )
        # mode3_progress 는 previous_analysis_id 필수
        if (
            self.comparison_type == "mode3_progress"
            and self.previous_analysis_id is None
        ):
            raise ValueError(
                "comparison_type='mode3_progress' requires previous_analysis_id"
            )
        # used_reference_fallback 은 mode3_first 에서만 True 허용
        if (
            self.used_reference_fallback
            and self.comparison_type != "mode3_first"
        ):
            raise ValueError(
                f"used_reference_fallback=True 는 comparison_type='mode3_first' "
                f"에서만 허용. got {self.comparison_type}"
            )
        # warnings type
        if not isinstance(self.warnings, list):
            raise TypeError(
                f"warnings must be list[str], got {type(self.warnings).__name__}"
            )
        # R8 fix: 모든 warnings element 가 BODY_COMPARISON_WARNING_CODES 내
        for i, w in enumerate(self.warnings):
            if not isinstance(w, str):
                raise TypeError(
                    f"warnings[{i}] must be str, got {type(w).__name__}"
                )
            if w not in BODY_COMPARISON_WARNING_CODES:
                raise ValueError(
                    f"warnings[{i}]='{w}' not in BODY_COMPARISON_WARNING_CODES. "
                    f"valid: {sorted(BODY_COMPARISON_WARNING_CODES)}"
                )


# ── IPSF Absolute Deficit 측정 (C14 fix: pose_reliability_low) ───────────


def measure_ipsf_absolute_deficits(
    angles: np.ndarray | None,
    technique_profile,
    normalized_keypoints: dict | None = None,
    *,
    pose_frames: list | None = None,
) -> list[BodyComparisonFinding]:
    """IPSF Page 21 절대 deficit 산식 + Sunity pose_reliability_low (C14 fix).

    R9 fix (2026-06-08 round-2): 5 IPSF geometric + 1 Sunity pose_reliability_low.
    '7 deficits' 옛 표현 사용 금지. poor_transitions v1.5 deferred.

    체형 ratio 는 곱하지 않음 — IPSF 절대 기준 정합 (Notebook §3.3).
    split 각도는 hip→knee 라인 각도만 사용. toe-to-toe Euclidean 절대 금지
    (Notebook §3.4 위양성 회피).

    Args:
        angles: (T, J) joint angles 또는 None (raw 좌표만 사용 시).
        technique_profile: Gemini 기술 인식 결과 (expects_extension 등).
        normalized_keypoints: 정규화된 keypoint dict (체형 보정 좌표) 또는 None.
        pose_frames: pose-estimation confidence 측정용 (pose_reliability_low).

    Returns:
        list[BodyComparisonFinding].
    """
    findings: list[BodyComparisonFinding] = []
    body_type_adjusted = normalized_keypoints is not None

    # 1) pose_reliability_low (C14 fix — 구 bad_angle rename)
    if pose_frames:
        low_conf_count = 0
        total = 0
        for f in pose_frames:
            kp = f.keypoints_3d
            if not kp:
                continue
            avg_conf = sum(v.confidence for v in kp.values()) / len(kp)
            total += 1
            if avg_conf < POSE_RELIABILITY_LOW_CONF_THRESHOLD:
                low_conf_count += 1
        if total > 0:
            ratio = low_conf_count / total
            if ratio > POSE_RELIABILITY_LOW_FRAME_RATIO:
                findings.append(
                    BodyComparisonFinding(
                        deficit_code="pose_reliability_low",
                        joint_key=None,
                        measured_value=float(ratio),
                        deduction_score=-0.5,
                        confidence=0.9,
                        body_type_adjusted=body_type_adjusted,
                    )
                )

    # 2) 5 IPSF GeometricCriterion (v1 단순 산식). normalized_keypoints 가 있을 때만.
    if normalized_keypoints is None:
        return findings

    # knee_toe_alignment (-0.2): kneecap → toe 180° 직선 정렬 실패.
    # RTMW COCO-17 에는 big_toe 없음 → ankle 사용. 단순 v1: hip-knee-ankle 각도.
    # 좌측만 측정 (v1 단순; v1.5 양쪽).
    if all(k in normalized_keypoints for k in ("left_hip", "left_knee", "left_ankle")):
        lh = np.array(normalized_keypoints["left_hip"])
        lk = np.array(normalized_keypoints["left_knee"])
        la = np.array(normalized_keypoints["left_ankle"])
        v1 = lh - lk
        v2 = la - lk
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 > _EPS and n2 > _EPS:
            cos_a = float(np.dot(v1, v2) / (n1 * n2))
            cos_a = max(-1.0, min(1.0, cos_a))
            angle = math.degrees(math.acos(cos_a))
            # 180° 기준 ±LINE_TOL_DEG (20°)
            if abs(angle - 180.0) > LINE_TOL_DEG:
                findings.append(
                    BodyComparisonFinding(
                        deficit_code="knee_toe_alignment",
                        joint_key="left_knee",
                        measured_value=float(angle),
                        deduction_score=-0.2,
                        confidence=0.85,
                        body_type_adjusted=body_type_adjusted,
                    )
                )

    # clean_lines (-0.2): technique_profile.expects_extension 관절들의 평균 각도
    # < 180 - LINE_TOL_DEG. technique_profile 가 None 또는 expects_extension 없을 시 skip.
    expects = getattr(technique_profile, "expects_extension", None) if technique_profile else None
    if expects:
        # expects = list of joint keys (e.g., ('left_elbow', 'right_elbow')).
        joint_angles_to_check = []
        for joint_key in expects:
            tri = {
                "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
                "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
                "left_knee": ("left_hip", "left_knee", "left_ankle"),
                "right_knee": ("right_hip", "right_knee", "right_ankle"),
            }.get(joint_key)
            if tri is None or not all(k in normalized_keypoints for k in tri):
                continue
            a = np.array(normalized_keypoints[tri[0]])
            b = np.array(normalized_keypoints[tri[1]])
            c = np.array(normalized_keypoints[tri[2]])
            v1 = a - b
            v2 = c - b
            n1 = np.linalg.norm(v1)
            n2 = np.linalg.norm(v2)
            if n1 > _EPS and n2 > _EPS:
                cos_a = float(np.dot(v1, v2) / (n1 * n2))
                cos_a = max(-1.0, min(1.0, cos_a))
                joint_angles_to_check.append(math.degrees(math.acos(cos_a)))
        if joint_angles_to_check:
            mean_angle = sum(joint_angles_to_check) / len(joint_angles_to_check)
            if mean_angle < (180.0 - LINE_TOL_DEG):
                findings.append(
                    BodyComparisonFinding(
                        deficit_code="clean_lines",
                        joint_key=None,
                        measured_value=float(mean_angle),
                        deduction_score=-0.2,
                        confidence=0.85,
                        body_type_adjusted=body_type_adjusted,
                    )
                )

    # extension (-0.2): mid_shoulder ↔ mid_hip ↔ neck 라인 평균 각도 < 160°.
    # neck 미존재 → mid_shoulder 위 50px 가정. v1 단순.
    if (
        "mid_shoulder" in normalized_keypoints
        and "mid_hip" in normalized_keypoints
    ):
        ms = np.array(normalized_keypoints["mid_shoulder"])
        mh = np.array(normalized_keypoints["mid_hip"])
        neck = ms + np.array([0.0, -50.0, 0.0])
        v1 = mh - ms
        v2 = neck - ms
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 > _EPS and n2 > _EPS:
            cos_a = float(np.dot(v1, v2) / (n1 * n2))
            cos_a = max(-1.0, min(1.0, cos_a))
            ang = math.degrees(math.acos(cos_a))
            if ang < 160.0:
                findings.append(
                    BodyComparisonFinding(
                        deficit_code="extension",
                        joint_key=None,
                        measured_value=float(ang),
                        deduction_score=-0.2,
                        confidence=0.7,
                        body_type_adjusted=body_type_adjusted,
                    )
                )

    # posture (-0.2): 좌우 어깨 line z-axis 깊이 차이 > shoulder_width × 0.3.
    if all(
        k in normalized_keypoints for k in ("left_shoulder", "right_shoulder")
    ):
        ls = np.array(normalized_keypoints["left_shoulder"])
        rs = np.array(normalized_keypoints["right_shoulder"])
        shoulder_width = float(np.linalg.norm(rs - ls))
        z_diff = abs(float(ls[2] - rs[2]))
        if shoulder_width > _EPS and z_diff > shoulder_width * 0.3:
            findings.append(
                BodyComparisonFinding(
                    deficit_code="posture",
                    joint_key=None,
                    measured_value=float(z_diff),
                    deduction_score=-0.2,
                    confidence=0.8,
                    body_type_adjusted=body_type_adjusted,
                )
            )

    # body_placement (-0.2): mid_hip 의 폴 축 (PoleAxis) 대비 수평 거리.
    # 단순 v1: mid_hip.x 가 normalized_keypoints 의 mid_shoulder.x 와 shoulder_width × 0.5 초과 차이.
    if (
        "mid_hip" in normalized_keypoints
        and "mid_shoulder" in normalized_keypoints
        and "left_shoulder" in normalized_keypoints
        and "right_shoulder" in normalized_keypoints
    ):
        mh = np.array(normalized_keypoints["mid_hip"])
        ms = np.array(normalized_keypoints["mid_shoulder"])
        ls = np.array(normalized_keypoints["left_shoulder"])
        rs = np.array(normalized_keypoints["right_shoulder"])
        shoulder_width = float(np.linalg.norm(rs - ls))
        horizontal_diff = abs(float(mh[0] - ms[0]))
        if shoulder_width > _EPS and horizontal_diff > shoulder_width * 0.5:
            findings.append(
                BodyComparisonFinding(
                    deficit_code="body_placement",
                    joint_key=None,
                    measured_value=float(horizontal_diff),
                    deduction_score=-0.2,
                    confidence=0.75,
                    body_type_adjusted=body_type_adjusted,
                )
            )

    return findings


# ── compare_body_profiles (W1 + R8 fix extra_warnings + R2 fix source_keypoints) ──


def compare_body_profiles(
    pose_frames: list[PoseFrame] | None,
    student_profile: BodyNormalizationProfile,
    reference_profile: BodyNormalizationProfile | None,
    comparison_type: ComparisonType,
    *,
    source_keypoints: dict[str, tuple[float, float, float]] | np.ndarray | None = None,
    angles: np.ndarray | None = None,
    technique_profile=None,
    reference_motion_id: str | None = None,
    reference_athlete_name: str | None = None,
    previous_analysis_id: str | None = None,
    used_reference_fallback: bool = False,
    target_torso_px: float | None = None,
    extra_warnings: list[str] | None = None,
) -> BodyComparisonReport:
    """체형 정규화 비교 본체 — D-06-U1 confidence-tiered hybrid.

    1) confidence + warnings 산출.
    2) foreshortening 검출 → shoulderHipRatio OFF 게이트 (W6).
    3) confidence < CONFIDENCE_GATE 또는 reference_profile=None 또는 source_keypoints=None
       → 정규화 OFF, scale_profile=None, findings=raw IPSF deficit.
    4) confidence >= gate + reference_profile + source_keypoints 있을 시 →
       ScaleProfile 산출 + normalize_pose_by_segments + findings (body_type_adjusted=True).
    5) R8 fix: extra_warnings merge + frozenset validate.
    6) BodyComparisonReport 조립.

    C1 fix: normalize_pose_by_segments 인자 순서 = (source_keypoints,
    source_profile, target_profile, target_torso_px). source = pro reference.

    R2 fix: source_keypoints 는 ndarray 또는 dict. caller (Plan 06-02) 가
    BodyComparisonSourcePose.to_keypoints_array() 로 변환해 전달.

    R8 fix: extra_warnings 는 caller-injected warning list. 내부 산출 warnings 와
    merge + dedup. BodyComparisonReport.__post_init__ 의 frozenset 검증이 gate.
    우회 패턴 (dataclass replace helper) 금지.
    """
    # 1) confidence 산출
    confidence, warnings = compute_body_normalization_confidence(
        pose_frames, student_profile, reference_profile, comparison_type
    )

    # 2) foreshortening (W6)
    foreshortening = is_foreshortening_detected(pose_frames) if pose_frames else False
    apply_shoulder_hip_ratio = not foreshortening
    if foreshortening:
        if "foreshortening_off" not in warnings:
            warnings.append("foreshortening_off")
        if "shoulder_hip_ratio_off" not in warnings:
            warnings.append("shoulder_hip_ratio_off")

    # mode3_progress 의 previous_analysis_id 게이트는 __post_init__ 에서 검증
    # (None 시 ValueError).

    # 4) 정규화 gate
    gate_open = (
        confidence >= CONFIDENCE_GATE
        and reference_profile is not None
        and source_keypoints is not None
    )

    scale_profile: ScaleProfile | None = None
    normalized_keypoints: dict | None = None

    if not gate_open:
        if "low_confidence_normalization_off" not in warnings:
            warnings.append("low_confidence_normalization_off")
        if source_keypoints is None:
            # R2 fix — production 에서 백필 미완 reference 의 silently OFF 차단.
            if "reference_source_pose_missing" not in warnings:
                warnings.append("reference_source_pose_missing")
    else:
        # 5 필드 ScaleProfile (student vs pro reference)
        ratio_height = (
            float(student_profile.estimated_height_scale)
            / max(float(reference_profile.estimated_height_scale), _EPS)
        )
        ratio_arm = (
            float(student_profile.arm_scale)
            / max(float(reference_profile.arm_scale), _EPS)
        )
        ratio_leg = (
            float(student_profile.leg_scale)
            / max(float(reference_profile.leg_scale), _EPS)
        )
        ratio_torso = (
            float(student_profile.torso_scale)
            / max(float(reference_profile.torso_scale), _EPS)
        )
        ratio_sh = (
            float(student_profile.shoulder_hip_ratio)
            / max(float(reference_profile.shoulder_hip_ratio), _EPS)
        )
        scale_profile = ScaleProfile(
            estimated_height_scale=ratio_height,
            arm_scale=ratio_arm,
            leg_scale=ratio_leg,
            torso_scale=ratio_torso,
            shoulder_hip_ratio=ratio_sh,
            shoulder_hip_ratio_applied=apply_shoulder_hip_ratio,
        )

        # normalize_pose_by_segments — C1 fix (source_keypoints, source_profile,
        # target_profile, target_torso_px)
        # source = pro reference, target = student.
        source_kp_dict: dict[str, tuple[float, float, float]]
        if isinstance(source_keypoints, np.ndarray):
            # ndarray (J, 4 또는 3) → dict
            if source_keypoints.ndim != 2 or source_keypoints.shape[1] < 3:
                raise ValueError(
                    f"source_keypoints ndarray shape (J, >=3) expected, "
                    f"got {source_keypoints.shape}"
                )
            source_kp_dict = {
                name: (
                    float(source_keypoints[i, 0]),
                    float(source_keypoints[i, 1]),
                    float(source_keypoints[i, 2]),
                )
                for i, name in enumerate(KEYPOINT_NAMES)
                if i < source_keypoints.shape[0]
            }
        else:
            source_kp_dict = source_keypoints  # type: ignore[assignment]

        torso_px = target_torso_px if target_torso_px is not None else (
            200.0 * float(student_profile.torso_scale)
        )

        normalized_keypoints = normalize_pose_by_segments(
            source_kp_dict,
            reference_profile,  # source_profile (R10 fix — 비사용)
            student_profile,  # target_profile (C1 fix)
            torso_px,
            apply_shoulder_hip_ratio=apply_shoulder_hip_ratio,
        )

    # 5) IPSF deficit 측정 (gate 무관 — confidence 낮으면 raw 좌표만)
    findings = measure_ipsf_absolute_deficits(
        angles,
        technique_profile,
        normalized_keypoints=normalized_keypoints,
        pose_frames=pose_frames,
    )

    # 6) R8 fix — extra_warnings merge + validate (frozenset)
    if extra_warnings:
        for w in extra_warnings:
            if w not in BODY_COMPARISON_WARNING_CODES:
                raise ValueError(
                    f"invalid extra_warning: '{w}' not in "
                    f"BODY_COMPARISON_WARNING_CODES"
                )
        # dedup, preserve order: 기존 warnings 먼저, 그다음 extra
        merged_warnings = list(
            dict.fromkeys([*warnings, *extra_warnings])
        )
    else:
        merged_warnings = warnings

    # 7) BodyComparisonReport 조립 — __post_init__ 의 frozenset 검증 통과 보장.
    return BodyComparisonReport(
        comparison_type=comparison_type,
        body_normalization_confidence=confidence,
        scale_profile=scale_profile,
        findings=findings,
        warnings=merged_warnings,
        reference_motion_id=reference_motion_id,
        reference_athlete_name=reference_athlete_name,
        previous_analysis_id=previous_analysis_id,
        used_reference_fallback=used_reference_fallback,
    )
