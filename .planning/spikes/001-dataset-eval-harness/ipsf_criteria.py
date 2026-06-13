"""IPSF GeometricCriterion 박제 — Phase 4 Camera Angle AI spike 평가 ground truth.

모든 criterion 은 NotebookLM IPSF Aerial Pole Sports Code of Points 2024-2025 query
(2026-06-13) 결과 기반. source_ref 에 page citation 박제 — 평가 결과 검증 가능.

belle 원칙:
- 사람 점수 라벨링 금지 (analysis-objectivity-no-human-scores)
- IPSF 가 ground truth, 사람 의견 아님 (judging-baseline-ipsf-code-of-points)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


CriterionKind = Literal[
    "fully_extended",        # 180° target ±20° tolerance
    "hold_time",             # 최소 2초
    "spin_rotation",         # 최소 720° 연속
    "twist_alignment",       # 어깨↔골반 방향 차이
    "split_angle",           # any angle/perspective 180°
    "presentation",          # poor positioning / angle to judges
    "start_end_visibility",  # 정면 심판석 visible
]


@dataclass(frozen=True)
class IPSFCriterion:
    """IPSF Code of Points 박제 criterion. 모든 field 는 IPSF 규정 인용으로 검증 가능."""
    name: str
    kind: CriterionKind
    target: float | tuple[float, float] | None  # target angle / time / rotation
    tolerance: float | None                       # ± allowed deviation
    fail_threshold: float | None                  # below/above this = 0 점
    deduction: float | None                       # 감점 점수 (없으면 None = fail only)
    source_ref: str                               # IPSF page citation


# ── NotebookLM IPSF query 2026-06-13 결과 기반 박제 ────────────────────────────

FULLY_EXTENDED = IPSFCriterion(
    name="Fully Extended",
    kind="fully_extended",
    target=180.0,
    tolerance=20.0,
    fail_threshold=160.0,
    deduction=None,
    source_ref="IPSF Aerial Pole Sports CoP 2024-2025 (Fully Extended Criteria)",
)

HOLD_TIME = IPSFCriterion(
    name="Hold Time",
    kind="hold_time",
    target=2.0,        # seconds
    tolerance=0.0,     # 2초 미만 허용 불가
    fail_threshold=2.0,
    deduction=None,    # fail = 0점 처리
    source_ref="IPSF Aerial Pole Sports CoP 2024-2025 Page 8",
)

SPIN_ROTATION = IPSFCriterion(
    name="Spin Rotation",
    kind="spin_rotation",
    target=720.0,      # degrees, fixed position
    tolerance=0.0,
    fail_threshold=720.0,
    deduction=2.0,     # 720° 스핀 2회 미수행 시 -2.0점 (페널티)
    source_ref="IPSF Aerial Pole Sports CoP 2024-2025 Page 10, Page 95",
)

TWIST_ALIGNMENT = IPSFCriterion(
    name="Twist Alignment (Deficit Posture)",
    kind="twist_alignment",
    target=None,       # 어깨와 골반 방향 차이 = 정성적 + 불필요한 굽힘 시 감점
    tolerance=None,
    fail_threshold=None,
    deduction=0.2,     # 척추/어깨 불필요 굽힘 -0.2점
    source_ref="IPSF Aerial Pole Sports CoP 2024-2025 Page 87",
)

SPLIT_ANGLE = IPSFCriterion(
    name="Split Angle (all angles/perspectives)",
    kind="split_angle",
    target=180.0,
    tolerance=None,    # "must remain the same from all angles/perspectives"
    fail_threshold=180.0,  # 180° 요구 위치에선 어떤 angle 에서도 일직선
    deduction=None,
    source_ref="IPSF Aerial Pole Sports CoP 2024-2025 Page 19 / Aerial Hoop CoP Page 15",
)

PRESENTATION = IPSFCriterion(
    name="Poor presentation (occlusion / poor angle)",
    kind="presentation",
    target=None,
    tolerance=None,
    fail_threshold=None,
    deduction=0.5,     # poor positioning / angle to judges = -0.5점 / 발생
    source_ref="IPSF Aerial Pole Sports CoP 2024-2025 Page 10, Page 94, Page 106",
)

START_END_VISIBILITY = IPSFCriterion(
    name="Start/end visibility to judges",
    kind="start_end_visibility",
    target=None,
    tolerance=None,
    fail_threshold=None,
    deduction=0.5,     # 등/사각지대로 시작·끝 = -0.5점 (start/end -0.2점)
    source_ref="IPSF Aerial Pole Sports CoP 2024-2025 Page 13",
)


ALL_CRITERIA: dict[str, IPSFCriterion] = {
    "fully_extended": FULLY_EXTENDED,
    "hold_time": HOLD_TIME,
    "spin_rotation": SPIN_ROTATION,
    "twist_alignment": TWIST_ALIGNMENT,
    "split_angle": SPLIT_ANGLE,
    "presentation": PRESENTATION,
    "start_end_visibility": START_END_VISIBILITY,
}


# ── Phase 4 spike 평가 axis 매핑 ──────────────────────────────────────────────
# CONTEXT.md D-13 (a)(b)(c) 평가 axis 가 IPSF criterion 으로 직접 매핑됨.
# 이게 Spike 001 의 핵심 발견: Phase 4 가 IPSF 채점 정확도의 직접 요건.

PHASE4_EVAL_AXIS_MAPPING: dict[str, list[str]] = {
    # (a) 가상 카메라 앵글 변환 정확도 = IPSF split angle (page 19) 다각도 일관성
    "axis_a_angle_transform_accuracy": [
        "split_angle",          # 어떤 angle 에서도 180° 유지 — 직접 metric
        "fully_extended",       # 변환 view 의 180° tolerance 정합
    ],
    # (b) AI 가상 뷰 합성 품질 = IPSF presentation (page 10/94/106) occlusion 보완
    "axis_b_synthesis_quality": [
        "presentation",         # poor angle = -0.5/회 → 합성 view 는 이 감점 제거
        "start_end_visibility", # 정면 심판석 시점 (page 13) 복원
    ],
    # (c) RTMW 재추론 pose 정확도 향상 = IPSF criterion 만족 frame rate ↑
    "axis_c_pose_accuracy_lift": [
        "fully_extended",       # 180° 측정 정확도
        "twist_alignment",      # 어깨↔골반 방향 (page 87) 측정 정확도
        "hold_time",            # 2초 hold 검출 정확도 (page 8)
        "spin_rotation",        # 720° 연속 회전 검출 정확도 (page 10/95)
    ],
}
