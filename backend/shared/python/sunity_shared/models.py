"""Firestore 문서 모양 + 상수. docs/contract.md §3~5, app/src/types/analysis.ts 미러.

이 파일이 바뀌면 contract.md 와 app 타입도 같이 맞춰야 한다(계약 단일 진실).
PoseFrame/PoleAxis 는 analysis/pose_frame.py 에 정의 (lockstep with app/src/types/analysis.ts).
"""

from __future__ import annotations

# ── 분석 모드 (contract.md §2 / ml_CLAUDE.md) ──────────────────────────
MODE_EXPERT = "mode1"  # 정은지(전문가) 비교
MODE_SELF = "mode3"  # 자기 성장 추적
MODES = (MODE_EXPERT, MODE_SELF)

# ── 점수 차원 (contract.md §4 / app dimensionScores) ──────────────────
# IPSF 실행 심사기준 기반 (docs/research/폴스포츠-지식.md). 신체 부위가 아니라
# 심판이 실제로 보는 실행 차원. angle 만 기준(reference) 필요, 나머지는 절대 지표.
DIM_ANGLE = "angle"        # 각도 정확도 (관절각 vs 기준)
DIM_LINE = "line"          # 라인·확장 (기술이 신전 요구하는 사지의 완성도)
DIM_STABILITY = "stability"  # 안정성·홀딩 (피크 구간 떨림)
SCORE_DIMENSIONS = (DIM_ANGLE, DIM_LINE, DIM_STABILITY)
# 기준 영상 없이 산출 가능 — mode3 자기 성장(세션 간 델타 같은 척도) 핵심.
# 2026-05-29 'balance/좌우대칭' 제거 — IPSF 근거 없음(dimensions.py 참조).
ABSOLUTE_DIMENSIONS = (DIM_LINE, DIM_STABILITY)

# ── Phase 12.5 (2026-06-07): dimensionExplanation 키 명세 ──────────────
# 결과 화면 "왜 이 점수인지" 가시화. 차원별 weight/baseline/deficit summary.
# - 키 = dimensionScores 의 부분 집합 (보유 차원만 emit).
# - weightPercent 합 = 100 (Largest Remainder Method: 3차원=[34,33,33] 등).
# - baseline = mode-aware (comparison["mode"] 추출, mode1 = 정은지 참조 / mode3 = 절대).
# - deficitSummary = 점수 산식과 동일 source (dimensions._select_window 공유):
#     angle ← kismam.top_issues / line ← line_deficits_by_joint /
#     stability ← stability_wobble_by_joint
# - 옵셔널 — 이전 빌드 doc 호환 (app/src/types/analysis.ts:DimensionExplanation 정합).
# - 신 backend 는 빈 {} 라도 항상 emit.
DIMENSION_EXPLANATION_KEYS = ("weightPercent", "baseline", "deficitSummary")

# ── 영상 형식 (contract.md: mp4/mov, ≤100MB) ───────────────────────────
VIDEO_FORMATS = ("mp4", "mov")
MAX_VIDEO_BYTES = 100 * 1024 * 1024  # design.md: 100MB 초과 불가

# ── 분석 상태 머신 (contract.md §3 AnalysisStatus) ─────────────────────
#   uploading 은 앱이 설정. 그 이후는 백엔드 pipeline 이 Admin SDK 로 갱신.
STATUS_UPLOADING = "uploading"
STATUS_QUEUED = "queued"
STATUS_FRAME_EXTRACTION = "frame_extraction"
STATUS_POSE_ANALYSIS = "pose_analysis"
STATUS_COMPARISON = "comparison"
STATUS_DONE = "done"
STATUS_FAILED = "failed"

# pipeline 이 진행하는 순서 (uploading 은 앱 몫이라 제외)
PIPELINE_SEQUENCE = (
    STATUS_QUEUED,
    STATUS_FRAME_EXTRACTION,
    STATUS_POSE_ANALYSIS,
    STATUS_COMPARISON,
    STATUS_DONE,
)

# ── 분석 오류 코드 (contract.md §5 / ml_CLAUDE.md) ────────────────────
ERR_NO_HUMAN = "no_human"
ERR_SIZE_EXCEEDED = "size_exceeded"
ERR_UNSUPPORTED_FORMAT = "unsupported_format"
ERR_SERVER_ERROR = "server_error"
# 비폴 영상 차단 안전망(belle P1 #8). mode1 비교 시 KISMAM similarity 가
# NOT_POLE_SIMILARITY_THRESHOLD 미만이면 분석 자체를 실패로 표시 — 의미 없는
# 점수를 결과 화면에 띄우지 않는다. mode3 는 reference 가 없어 적용 불가.
ERR_NOT_POLE_MOTION = "not_pole_motion"
ANALYSIS_ERROR_CODES = (
    ERR_NO_HUMAN,
    ERR_SIZE_EXCEEDED,
    ERR_UNSUPPORTED_FORMAT,
    ERR_SERVER_ERROR,
    ERR_NOT_POLE_MOTION,
)

# UI 고정 문구. app/src/types/analysis.ts ERROR_MESSAGE 와 동일 문자열.
ERROR_MESSAGE = {
    ERR_NO_HUMAN: "영상에서 사람을 찾지 못했어요. 전신이 보이게 다시 촬영해주세요.",
    ERR_SIZE_EXCEEDED: "100MB 이하 영상만 분석할 수 있어요.",
    ERR_UNSUPPORTED_FORMAT: "mp4, mov 형식의 영상만 분석할 수 있어요.",
    ERR_SERVER_ERROR: "분석 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
    ERR_NOT_POLE_MOTION: "선택한 기준 동작과 너무 달라요. 폴스포츠 동작이 맞는지 확인하고 다시 시도해주세요.",
}

# 비폴 차단 임계값. mode1 비교 결과 similarity(KISMAM overall_score) 가
# 이 값 미만이면 ERR_NOT_POLE_MOTION 으로 분기. 보수적으로 시작(위양성 방지) —
# 실제 폴 영상이라도 동작이 매우 달라 30 점 이하 나올 수 있으니 25 점.
# 시연·튜닝 데이터 누적 후 belle 와 조정.
NOT_POLE_SIMILARITY_THRESHOLD = 25


def analysis_doc_path(uid: str, analysis_id: str) -> str:
    """Firestore: users/{uid}/analyses/{analysisId} (보안 규칙 격리 경로)."""
    return f"users/{uid}/analyses/{analysis_id}"


def reference_motion_path(motion_id: str) -> str:
    """Firestore: reference/{motionId} (앱 읽기 전용)."""
    return f"reference/{motion_id}"


# Firestore 컬렉션 경로는 홀수 segment 여야 함. "reference/motions" 같은 2-segment는
# invalid path 라 collection() 호출 시 ValueError. → reference 단일 컬렉션 채택.
REFERENCE_MOTIONS_COLLECTION = "reference"

# ── PoseFrame / PoleAxis re-export (lockstep with app/src/types/analysis.ts) ──
# Phase 1 D-04/D-05/D-11/D-12 계약 타입.
# 변경 시 analysis/pose_frame.py + app/src/types/analysis.ts + docs/contract.md §6 동시 갱신.
from .analysis.pose_frame import (  # noqa: E402 — 파일 하단 re-export 패턴
    ConfidenceLevel,
    Landmark3D,
    PoleAxis,
    PoleAxisSource,
    PoseFrame,
    ReliabilityLevel,
)

# RTMW pivot (2026-06-02, Plan 01-19) — D-19/D-21 박제.
#   BodyNormalizationProfile = SMPL-X β 없이 segment 비율 + confidence + warnings.
#   PoseFrame.body_shape: Optional[BodyNormalizationProfile] = None nullable.
# TS 미러: app/src/types/analysis.ts BodyNormalizationProfile interface.
# 변경 시 TS + contract.md §6 동시 갱신 (CLAUDE.md Cross-cutting).
from .analysis.body_normalization import (  # noqa: E402 — 파일 하단 re-export 패턴
    BodyNormalizationProfile,
)

# Phase 6 (2026-06-08, Plan 06-01) — D-06-B3 박제.
#   BodyComparisonReport = comparisonType (3 cases — W1) + scaleProfile + findings
#   + bodyNormalizationConfidence + usedReferenceFallback boolean.
# 확장: ScaleProfile, BodyComparisonFinding, BodyComparisonSourcePose, ComparisonType Literal.
# C14 deficit_code 'pose_reliability_low' (IPSF judge-observation 'bad_angle' 과
# 의미 다름 — divergence docs/contract.md §8.1).
# R2 (2026-06-08 round-2 reviews) — BodyComparisonSourcePose 신규 (reference 측
# 대표 hold frame keypoints flat 영속, Firestore nested-array 회피).
# R8 (round-2) — compare_body_profiles extra_warnings 파라미터 + frozenset validation.
# Phase 7 (2026-06-08, Plan 07-01) — 차이 분류 schema 확장.
#   BodyComparisonFinding +4 필드 (category / phase / body_type_interpretation /
#     recommendation) — D-07-A1 + D-07-C1.
#   BodyComparisonReport +3 필드 (do_not_over_correct / recommended_focus /
#     recommended_focus_fallback) — D-07-B3 + WR-03 fix.
#   WR-01 fix: measure_ipsf_absolute_deficits 의 6 호출 위치 placeholder
#     category="uncertain" (fail-safe — Plan 02 가 재할당).
# iteration 2 cross-AI review fix 7 finding 정합 (CR-01/CR-02/WR-01/WR-03/WR-04).
# TS 미러: app/src/types/analysis.ts
#   BodyComparisonReport / BodyComparisonFinding / ScaleProfile /
#   BodyComparisonSourcePose / ComparisonType interface.
# 변경 시 TS + docs/contract.md §8 + §8.2 + §8.3 동시 갱신 (CLAUDE.md Cross-cutting).
from .analysis.body_normalizer import (  # noqa: E402 — 파일 하단 re-export 패턴
    BodyComparisonFinding,
    BodyComparisonReport,
    BodyComparisonSourcePose,
    ComparisonType,
    ScaleProfile,
)

# Phase 8 Force Signals (Plan 08-01 revised — REVIEWS Cycle 1).
# Plan 08-02 신설 후 import 활성화 (force_signals.py dataclass 본체 박제 후).
# 본 plan 은 placeholder = forward-declare 주석만 (3-way lockstep 의 Python 측면
# 박제 위치 강제 — Plan 07-01 / 06-01 패턴 정합).
#
# Plan 08-00 박제 §9.0 contract 위에 박제:
#   - CoordinateSpace (image_2d / pole_aligned / world_3d / unavailable)
#   - ContactPrimitiveKind (keypoint / segment / region_proxy)
#   - PoleAxisMeasurement (axis_3d + line + coordinate_space)
#   - median_torso_length helper (body_scale.py)
#
# REVIEWS Cycle 1 반영 schema (lockstep test_force_signals_lockstep.py 가 grep 검증):
#   R1/R2: AxisDeviationMetric.{pelvis_distance_from_pole_axis,
#          chest_distance_from_pole_axis} nullable + coordinate_space +
#          scale_denominator 동행.
#   R3:    ContactStabilityMetric = evidence-with-confidence: estimated_stable
#          nullable + distance_to_pole_norm + near_pole_ratio +
#          lost_near_pole_at_ms + measurement_kind.
#   R4:    PhaseBoundary.preflight_label_gate_passed nullable 신설.
#   R5:    StabilityMetric.jerk_unit='deg_per_sec_cubed' + jerk_score (deg/sec^3
#          FPS-normalized).
#
# from .analysis.force_signals import (
#     MotionPhase,
#     DeviationDirection,
#     SeverityLevel,
#     MetricConfidence,
#     ContactPoint,
#     PhaseBoundary,                  # fields: phase, start_frame_idx, end_frame_idx,
#                                     #         start_ms, end_ms, confidence, source,
#                                     #         preflight_label_gate_passed
#     AxisDeviationMetric,            # fields: phase, pelvis_distance_from_pole_axis,
#                                     #         chest_distance_from_pole_axis,
#                                     #         shoulder_tilt, hip_tilt,
#                                     #         deviation_direction, severity,
#                                     #         confidence, coordinate_space,
#                                     #         scale_denominator, warnings
#     StabilityMetric,                # fields: phase, jitter_score, jerk_score,
#                                     #         jerk_unit, hold_stability_score,
#                                     #         unstable_body_parts, severity,
#                                     #         confidence, warnings
#     ContactStabilityMetric,         # fields: phase, contact_point,
#                                     #         measurement_kind, estimated_stable,
#                                     #         distance_to_pole_norm,
#                                     #         near_pole_ratio,
#                                     #         lost_near_pole_at_ms,
#                                     #         coordinate_space, severity,
#                                     #         confidence, warnings
#     ForceSignalsReport,             # fields: version, overall_confidence, warnings,
#                                     #         phase_boundaries, axis_metrics,
#                                     #         stability_metrics, contact_metrics
# )
#
# AnalysisResult lockstep:
#   forceSignalsReport optional + nullable (Plan 08-02 wiring 박제 후 활성화).
#
# 20 warning code enum (docs/contract.md §9.8 mirror):
#   기존 13: occlusion_high_in_phase / layer2_unavailable / layer_disagreement_minor /
#           layer_disagreement_major / layer2_call_failed / motion_unrecognized /
#           motion_unrecognized_layer1_only / abnormal_release_during_hold /
#           partial_motion_video / video_too_short / heavy_occlusion /
#           entry_not_detected / all_frames_unreliable.
#   Cycle 1 신설 6: pole_line_missing / scale_unavailable /
#           preflight_label_gate_failed / fps_normalization_applied /
#           contact_evidence_only / coordinate_space_unavailable.
#   Cycle 2 신설 1: preflight_gate_pending (gate 미실행 default).
