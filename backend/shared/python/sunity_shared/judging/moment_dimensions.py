"""Moment-list sampling 점수 계산 (Plan 01-13 T-2).

Plan 12 dominant 가설 (a) frame-mean 한계 의 직접 해결 path:

  · 기존 dimensions.py = (T, J) 행렬에서 hold_window (가장 안정적 구간) 의 frame-mean.
  · 본 모듈 = Gemini 가 분류한 key moment 시점의 측정 각도 vs IPSF GeometricCriterion 갭.

운영 코드 무수정 — dimensions.py / kismam.py / features.py / temporal.py 0 줄 변경.
본 모듈은 spike 단독 호출용 (`backend/research/spikes/spike_gemini_moment.py`). 운영 코드
진입은 Plan 14 통과 후 별 plan 책임.

설계 원칙:
  · 8 angle joints 만 사용 (`skeleton.JOINT_KEYS`). derive joint (hip/spine/thorax/neck_nose/
    head) 절대 사용 금지 — Plan 12 (d) keypoint mapping 차이 회피.
  · 점수 스케일 = `kismam.score_from_deviation` 그대로 (dimensions.py 와 일관성).
  · `minimum_requirement` 미달 entry 별 박제 — Plan 14 게이트 (minimum 미달 0 건).

요구사항:
  · REQUIREMENTS.md POSE-01 (D-14 게이트 = 측정 각도 ↔ IPSF angle_target 갭 ≤ tolerance_full).
  · 01-15-SUMMARY decisions §3 (NLF 갭 baseline 폐기 → IPSF 객관 임계값 baseline).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..analysis import kismam
from ..analysis.skeleton import JOINT_KEYS
from .geometric_criterion import GeometricCriterion

# 신전 완전성 reference — IPSF Fully Extended Criteria (180°).
_FULL_EXTENSION_DEG = 180.0


def measure_moment_angles(
    angles_TJ,
    frame_index: int,
    joint_keys: tuple[str, ...] | list[str] | None = None,
) -> dict[str, float]:
    """주어진 frame index 의 측정 각도 dict 반환 (8 joints 만 허용).

    Args:
      angles_TJ: (T, J=8) 측정 각도 행렬. spike_rtmpose+MB → features.compute_joint_angles
                 → temporal.temporal_fill 결과.
      frame_index: T 시퀀스에서의 정수 인덱스 (Gemini KeyMoment.frame_index).
      joint_keys: 측정할 관절 key tuple. None 이면 `skeleton.JOINT_KEYS` 8 개 전부.
                  8 외 joint 요청 시 ValueError — derive joint 회피 가드.

    Returns:
      `{joint_key: angle_degrees}` dict. 길이 = len(joint_keys).

    Raises:
      ValueError: frame_index 가 [0, T) 범위 밖.
      ValueError: 요청한 joint_key 가 `skeleton.JOINT_KEYS` 에 없음 (derive joint 가드).
      ValueError: 측정 각도가 NaN 또는 inf (Plan 13 안전 — 갭 계산이 의미 없음).
    """
    a = np.asarray(angles_TJ, dtype=float)
    if a.ndim != 2 or a.shape[1] != len(JOINT_KEYS):
        raise ValueError(
            f"angles_TJ 형상은 (T, {len(JOINT_KEYS)}) 이어야 합니다. shape={a.shape}"
        )

    T = a.shape[0]
    if frame_index < 0 or frame_index >= T:
        raise ValueError(
            f"frame_index 범위 위반: frame_index={frame_index}, T={T}. "
            f"Gemini KeyMoment.frame_index 가 assign_frame_indices 후처리 통과했는지 확인."
        )

    if joint_keys is None:
        requested = tuple(JOINT_KEYS)
    else:
        requested = tuple(joint_keys)

    out: dict[str, float] = {}
    for jk in requested:
        if jk not in JOINT_KEYS:
            raise ValueError(
                f"joint_key={jk!r} 는 skeleton.JOINT_KEYS (8 joints) 에 없음. "
                f"derive joint (hip/spine/thorax/neck_nose/head) 사용 금지 "
                f"(Plan 12 (d) keypoint mapping 회피). 유효 값 = {JOINT_KEYS}."
            )
        idx = JOINT_KEYS.index(jk)
        val = float(a[frame_index, idx])
        if not np.isfinite(val):
            raise ValueError(
                f"frame {frame_index} joint={jk} 의 측정 각도가 NaN/inf — 갭 계산 불가. "
                f"temporal.temporal_fill 후 측정 각도가 유한해야 합니다."
            )
        out[jk] = val
    return out


@dataclass(frozen=True)
class CriteriaGap:
    """단일 (joint × criterion) 갭 결과.

    Fields:
      joint_key: skeleton.JOINT_KEYS 중 하나.
      measured_angle: 측정 각도 (degree).
      angle_target: GeometricCriterion.angle_target.
      gap: 절대 갭 = |measured - target|.
      beyond_tolerance: tolerance_full 초과분 (0 이상). gap - tolerance_full, clamped to 0.
      deduction: tolerance 초과 1° 당 deduction_per_step (감점값, 양수).
      minimum_met: measured 가 minimum_requirement 이상이면 True. minimum 미달 = 동작 실패.
      score: kismam.score_from_deviation(gap, tolerance_full) → 0~100.
    """

    joint_key: str
    measured_angle: float
    angle_target: float
    gap: float
    beyond_tolerance: float
    deduction: float
    minimum_met: bool
    score: int


def compute_criteria_gap(
    measured_angle: float,
    criterion: GeometricCriterion,
) -> CriteriaGap:
    """단일 (측정값, criterion) → CriteriaGap.

    Plan 14 D-14 게이트 baseline:
      `|measured - angle_target| ≤ tolerance_full` 이면 만점 근방.
      `tolerance_full` 초과 1° 당 `deduction_per_step` 감점.
      `measured < minimum_requirement` → 동작 실패 (`minimum_met = False`).

    Args:
      measured_angle: spike 측정 각도 (degree).
      criterion: belle 라벨링된 GeometricCriterion (validate() 통과 가정).

    Returns:
      CriteriaGap.
    """
    if not np.isfinite(measured_angle):
        raise ValueError(
            f"measured_angle 이 NaN/inf — 갭 계산 불가. joint={criterion.joint_key} "
            f"target={criterion.angle_target}."
        )

    gap = abs(measured_angle - criterion.angle_target)
    beyond = max(0.0, gap - criterion.tolerance_full)
    deduction = beyond * criterion.deduction_per_step
    minimum_met = measured_angle >= criterion.minimum_requirement
    score = kismam.score_from_deviation(gap, criterion.tolerance_full)
    return CriteriaGap(
        joint_key=criterion.joint_key,
        measured_angle=float(measured_angle),
        angle_target=float(criterion.angle_target),
        gap=float(gap),
        beyond_tolerance=float(beyond),
        deduction=float(deduction),
        minimum_met=bool(minimum_met),
        score=int(score),
    )


def score_moment(
    measured_angles_by_joint: dict[str, float],
    criteria: list[GeometricCriterion],
) -> dict:
    """한 moment 의 (측정 dict × criteria list) → 종합 점수 dict.

    Plan 12 dominant (a) frame-mean 대체 — 본 함수가 moment-list sampling 의 핵심.
    dimensions.py 의 line/angle 차원 키 (`DIM_LINE`, `DIM_ANGLE`) 와 동일한 의미.

    `line` 차원: 신전(180°) 요구 관절의 평균 부족분 → `kismam.score_from_deviation`.
                IPSF angle_target == 180.0 인 entry 만 line 차원에 기여.
    `angle` 차원: 모든 entry 의 평균 갭 → `kismam.score_from_deviation`.
                  criteria 가 비어있으면 None (생략).

    Args:
      measured_angles_by_joint: `{joint_key: angle_degrees}` (measure_moment_angles 결과).
      criteria: 같은 moment 의 GeometricCriterion list (load_grouped_criteria[moment_key]).

    Returns:
      ```
      {
        "line": int | None,                       # IPSF 180° 신전 평균 점수
        "angle": int | None,                      # 평균 갭 점수
        "per_joint": list[CriteriaGap],           # 각 entry 결과
        "minimum_failures": list[str],            # minimum 미달 joint_key list
        "criteria_count": int,
      }
      ```
    """
    per_joint: list[CriteriaGap] = []
    minimum_failures: list[str] = []

    for c in criteria:
        if c.joint_key not in measured_angles_by_joint:
            # 측정 각도가 누락된 entry — Plan 13 단계에서는 명확히 거부 (silent skip 금지).
            raise ValueError(
                f"criterion.joint_key={c.joint_key!r} 의 측정 각도가 측정 dict 에 없음. "
                f"measure_moment_angles 호출 시 joint_keys 에 누락된 관절을 포함하세요. "
                f"measured_keys={sorted(measured_angles_by_joint.keys())} "
                f"motion={c.motion} moment={c.moment_key}"
            )
        gap = compute_criteria_gap(measured_angles_by_joint[c.joint_key], c)
        per_joint.append(gap)
        if not gap.minimum_met:
            minimum_failures.append(c.joint_key)

    if not per_joint:
        return {
            "line": None,
            "angle": None,
            "per_joint": [],
            "minimum_failures": [],
            "criteria_count": 0,
        }

    # line: angle_target == 180.0 entry 만 (IPSF Fully Extended 신전).
    line_gaps = [
        max(0.0, _FULL_EXTENSION_DEG - g.measured_angle)
        for g, c in zip(per_joint, criteria)
        if c.angle_target == _FULL_EXTENSION_DEG
    ]
    if line_gaps:
        # tolerance_full 평균을 line 의 tol 로 사용 (entry 별 동일 가정, IPSF 기본 20°).
        line_tol = float(
            np.mean(
                [c.tolerance_full for c in criteria if c.angle_target == _FULL_EXTENSION_DEG]
            )
        )
        line_score: int | None = int(
            kismam.score_from_deviation(float(np.mean(line_gaps)), line_tol)
        )
    else:
        line_score = None

    # angle: 전 entry 평균 갭 → tolerance_full 평균.
    angle_tol = float(np.mean([c.tolerance_full for c in criteria]))
    angle_mean_gap = float(np.mean([g.gap for g in per_joint]))
    angle_score = int(kismam.score_from_deviation(angle_mean_gap, angle_tol))

    return {
        "line": line_score,
        "angle": angle_score,
        "per_joint": per_joint,
        "minimum_failures": minimum_failures,
        "criteria_count": len(per_joint),
    }
