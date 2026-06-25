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
# - Phase 19 D-01: contributesToOverall 추가 (옵셔널). overall_from_dimensions 가
#   stability 를 종합 입력에서 제외하므로 core 차원(angle/line)=True, stability=False +
#   weightPercent=0. 옛 doc 미보유 → UI default true (옛 overall 은 stability 포함).
DIMENSION_EXPLANATION_KEYS = (
    "weightPercent",
    "baseline",
    "deficitSummary",
    "contributesToOverall",
)

# ── Phase 19 (TRUST-03): comparison.scoringBasis 명세 ──────────────────
# 결과 화면에 "어떤 SOURCE 로 채점했는지" 를 정확히 노출 (거짓 confident 점수 차단).
# 3중 계약: app/src/types/analysis.ts (Mode1Comparison/Mode3Comparison) +
# assemble.build_mode1/build_mode3 + docs/contract.md 와 lockstep.
#
# Mode1 (MODE_EXPERT) = 정은지 reference 각도와 실제 비교 → scoringBasis 는 항상
#   "reference_motion". build_mode1 이 신규 doc 에 always-emit (OPTIONAL — legacy 호환).
#   reference_motion 은 Mode1 전용 — Mode3 comparison 에는 절대 존재하지 않는다.
MODE1_SCORING_BASIS = "reference_motion"
#
# Mode3 (MODE_SELF) = reference motion 비교가 아님 → 허용 scoringBasis = 정확히 4 값
#   (reference_motion 미포함). first 는 abs_dims + extension targets, progress 는
#   이전 영상 각도 일관성 + 절대트랙. Mode3 허용값은 정확히 4개 (reference_motion 미포함).
#     reference_free_absolute              : first + 미등록 → 절대트랙(line+stability)
#     recognized_motion_absolute           : first + 등재 → 절대트랙 (reference 각도 미사용)
#     previous_analysis_plus_absolute      : progress + 등재 → 이전 일관성 + 절대트랙
#     previous_analysis_plus_reference_free_absolute : progress + 미등록 → composite
MODE3_SCORING_BASES = (
    "reference_free_absolute",
    "recognized_motion_absolute",
    "previous_analysis_plus_absolute",
    "previous_analysis_plus_reference_free_absolute",
)

# ── Phase 20 (SCORE-08, TRUST-08) + Phase 24 (ND-01, 밴드 제거): visionVeto audit 명세 ──
# 비전 채점 결과 audit. status 가 채점 실행을 증명한다 (부재 ≠ 실행, HIGH-1). Phase 24:
# severity→고정천장 밴드 제거 — applied 시 tallyFinal(감점 합산 최종) 동반.
# 점수 자체는 §10 deductionBreakdown.final 이며 tallyFinal 는 그 audit mirror.
# applied 시에만 severity/tallyFinal 동반 (discriminated — analysis.ts VisionVeto union).
# 객관성: 사람/AI 점수 라벨 아님 — status/severity enum + tallyFinal(측정규칙 산출 정수)만.
# 3-way lockstep: app/src/types/analysis.ts VisionVeto + docs/contract.md §4.
VISION_VETO_STATUSES = (
    "applied",          # cap 적용 (overallScore 하향)
    "not_applicable",   # cap 미적용 (minor/None/placeholder — 점수 불변)
    "disabled",         # 토글 OFF (adapter 미호출)
    "skipped_error",    # adapter None(키부재/실패) → v1 graceful + WARNING
    "missing_local_video",  # local_video_path None (graceful, HIGH-1)
    "mode3_held",       # Mode3 = veto 보류 (고정 reference 없음, belle 2026-06-20)
    "missing_reference",  # Mode1 인데 reference 영상 부재 → 진공 판정 회피 (graceful)
    # ── Phase 23-01 신규 score-free status (3-way lockstep) ──
    "low_alignment_confidence",  # D-03/H4 — 글로벌+로컬 DTW 정렬 신뢰도 낮음 → 거짓결함
                                 # fabricate 안 하고 보류 (score 불변, cap 미적용)
    "resource_limited",          # D-09 MED-1/D-13 HIGH-2 (Option A) — planned call 전부
                                 # 완료 전 예산(호출/upload/wall-clock) 소진 → fail-closed
                                 # 보류 (부분 샘플 verdict 비결정성 차단, score 불변)
)
# primaryFault(UI B1): applied 시에만 동반하는 지배적 결함 DESCRIPTION(자연어). "왜 점수가
# 내려갔는지" 앱 노출용. 점수/숫자 라벨 절대 금지(객관성). legacy doc 호환 위해 optional.
# faultJoints(#3, 2026-06-21): applied 시에만 동반 가능한 정식 keypoint 이름 list — Gemini
# differences[].body_part 를 vision_veto.fault_joints_from_differences 로 매핑한 결과. 앱
# 마커가 진짜 결함 관절을 강조하게 한다(각도편차 최대 관절 폴백 대체). 매핑 0 이면 키 부재.
# faultJointDeficits(2026-06-21): {keypoint: Gemini 시각 추정 deviation deg} — fault-zoom
# deficit 숫자 source. kismam delta 는 veto 결함을 못 잡아 과소 → Gemini 추정을 쓴다.
#
# ── Phase 23-02 (D-02/D-04/D-11 MED-1/D-12 HIGH-1): 정량화 DESCRIPTIVE 필드 ──
# applied 시에만 동반 (discriminated). 점수 아님 — 각도(도)/칸/원인가설 텍스트만.
# quantificationStatus(available|unavailable): applied audit 에 **필수**. unavailable 이면
#   angleDeltas/bodyRelativeNotches 부재 + status='applied'+tallyFinal 유지(강등 금지).
# angleDeltas: frame-specific per-joint 각도 (verdict 프레임 쌍 user/ref_frame_idx 의 행
#   값만 — DTW median 아님, D-10 HIGH-3). 각 항목 {joint,student_deg,reference_deg,delta_deg,
#   direction,source='geometry'}. percent 0(D-08).
# bodyRelativeNotches: 결정적 칸/층 (keypoint+baseline → 정수/분수 칸, source='geometry',
#   Gemini 미산출, D-08 H2). percent 0.
# windowMedianAngleDeltas: robustness 용 window median (still 정확 각도 아님 — 별도 키 +
#   sourceFrameIndices/windowPolicy 동반, D-10 HIGH-3).
# rootCauseHypotheses: support-gated 원인 가설 (source='vision_hypothesis', "~로 보임"
#   가설형, D-13 MED-1). cap_would_apply=true(eligible_for_coach) 일 때만 생성.
VISION_VETO_KEYS = (
    "status", "severity", "tallyFinal", "primaryFault", "faultJoints",
    "faultJointDeficits",
    # Phase 23-02 정량화 (applied 시에만, score-free, percent-free).
    "quantificationStatus", "angleDeltas", "bodyRelativeNotches",
    "windowMedianAngleDeltas", "rootCauseHypotheses",
)

# ── Phase 24 (SCORE-10~16, ND-01/ND-07): 투명 감점-합산 계약 ─────────────
# 점수 = baseline(100) − Σ(criterion별 측정편차 × 명시규칙 감점). severity→고정밴드
# (Phase 20 SEVERITY_CAP/apply_downward_cap) **제거·교체**. 결과 숫자(50이든 70이든)는
# tally 출력일 뿐 범위가 아님 — 보고서가 감점 내역("−X −Y −Z = 점수")을 노출하는 게 핵심
# ([[scoring-must-be-transparent-deduction-tally]]).
#
# OBJECT shape (HIGH-1): deductionBreakdown 은 {baseline, records, final, coverageGaps,
#   fallback} 객체(bare list 아님). records/coverageGaps 는 flat dict 의 list (Firestore
#   nested-array 금지 — angleDeltas/bodyRelativeNotches 와 동일 형식).
# baseline 분리 (HIGH-3): breakdown-level `baseline` = 점수 baseline 100(미감점 천장,
#   재-floor 금지). record-level `baselineValue` = 그 criterion 의 수치 측정 기준
#   (180°/160°/reference_notches 등). record-level `baselineKind` = reach criterion 의
#   per-move baseline(vision_veto.BASELINE_KINDS: floor|pole_vertical|hip_line),
#   그 외 criterion 은 None — 키는 **항상** 방출(present-but-nullable, MEDIUM-2).
# strictness (MEDIUM-2): record 내부는 STRICT — `baselineKind` present-but-nullable
#   (optional 아님), `ipsfAnchor`+`baselineValue` 는 모든 record 에 REQUIRED(추적성 게이트).
#   legacy-compat 는 whole `deductionBreakdown?` 필드 + breakdown-level coverageGaps?/
#   fallback? 에서만.
# points 부호 (HIGH-2): 각 record.points 는 SIGNED NEGATIVE (UX 가 −X 표시).
#   final = max(0, round(100 + Σ record.points)) — 유일한 clamp 은 max(0,…)(상한 밴드 없음).
# fallback 의미: quantificationStatus=='unavailable' → final = dimension_overall(100 으로
#   리셋 금지) + ONE traceable fallback record(criterion='dimension_overall_fallback',
#   unit='score_delta', deviationSource='dimension_overall')로 100+Σpoints==final 유지
#   (MEDIUM-1). 'gemini_silent' = Gemini 무지목인데 measured 감점이 적용된 관측 마커.
# coverageGaps provenance (MEDIUM-3): 각 entry 는 flat-scalar bodyPart/faultState/
#   keypointSet/ruleId(supported_difference 에서 채움) 동반 → 보이지만-0감점 gap 추적가능.
# 3-way lockstep: app/src/types/analysis.ts DeductionRecord/DeductionBreakdown +
#   docs/contract.md §10.
DEDUCTION_RECORD_KEYS = (
    "criterion", "measuredValue", "baselineValue", "baselineKind",
    "deviation", "ruleId", "points", "unit", "ipsfAnchor", "source",
    "deviationSource",
)
DEDUCTION_BREAKDOWN_KEYS = ("baseline", "records", "final", "coverageGaps", "fallback")

# ── Phase 20 (TRUST-07): scoreSuppressed + scoreSuppressedReason 명세 ───
# Mode3 미보유/저신뢰 동작의 점수카드 전체 억제 신호. scoringBasis 단독이 아닌 명시
# 플래그로 backend↔frontend drift 차단 (iter2 HIGH-3).
# 불변식 (iter4 MEDIUM-1, producer-contract): scoreSuppressed=True 면 scoreSuppressedReason
# 는 REQUIRED. scoreSuppressed=False/부재면 scoreSuppressedReason 없어야 함 (discriminated
# suppression type). 누락은 producer-contract FAILURE (fail-loud, UI silent 추론/default
# 카피 금지). 사유 분리 (iter3 MEDIUM-1):
#   unheld                    = 미보유 (is_reference_free branch metadata) → '기준 없음' 카피
#   recognition_low_confidence = recognizer 신뢰도 낮음 (동작은 알 수 있어도 분류 불확실) →
#                                '동작 인식 신뢰도 낮음' 카피. 미보유 아님.
# 3-way lockstep: app/src/types/analysis.ts ScoreSuppression + docs/contract.md §4.
SCORE_SUPPRESSED_KEY = "scoreSuppressed"
SCORE_SUPPRESSED_REASON_KEY = "scoreSuppressedReason"
SCORE_SUPPRESSED_REASONS = ("unheld", "recognition_low_confidence")

# ── Phase 20 iter5 MEDIUM-2: scoreSuppressionAudit 명세 ─────────────────
# A2 reconcile 단일 structured sink — recognizer category 와 branch is_reference_free
# 출처가 달라 불일치 시 정확히 이 필드로 보고한다 (log.warning '또는' 대안 폐기,
# log 는 additive only never alternative). resolvedReason = resolver 최종 reason.
# 3-way lockstep: app/src/types/analysis.ts ScoreSuppressionAudit + docs/contract.md §4.
SCORE_SUPPRESSION_AUDIT_KEYS = (
    "recognizerCategory",
    "branchReferenceFree",
    "resolvedReason",
)

# ── Phase 13 (Plan 13-A, PERS-03): recommendedExercises 계약 명세 ───────
# 분석 결과(실패 원인 후보 + 통증부위)에 맞춘 보완 운동 3~5개 개인화 subset.
# - 생산자 = analysis/exercise_map.map_exercises(force_pattern_inference, pain_areas,
#   motion_id) (pure fn, Layer 2 boto3-free). 입력은 Phase 9 findings + bodyProfile
#   painAreas + motion_id 만 — painAreas 는 매핑 출력에만 흐르고 점수 경로 미진입 (D-05).
# - 검증 = firestore_admin._validate_recommended_exercises scoped validator
#   (len <= 5 cap + 각 item flat scalar — firestore-nested-array-flat 보존).
# - 각 운동 dict = plain camelCase scalar {name, setsReps, purpose, sourceRef?}.
#   static fixture(backend/data/corrective_exercises.json) 산출이라 normalizer 불필요.
# - 3-way lockstep: app/src/types/analysis.ts:RecommendedExercise ↔ 본 계약 ↔
#   docs/contract.md §4. 세 곳 동시 갱신 필수.
RECOMMENDED_EXERCISE_KEYS = ("name", "setsReps", "purpose", "sourceRef")
MAX_RECOMMENDED_EXERCISES = 5

# ── Phase 3 (Plan 03-01) — BodyProfile 자가입력 계약 (3-way lockstep #2) ──
# 사람용 명세: docs/contract.md "BodyProfile (자가입력)" 섹션.
# TS 미러: app/src/types/analysis.ts (ExperienceLevel/DominantHand/PainArea
#   union + interface BodyProfile + AnalysisDoc.bodyProfile).
# 이 셋(analysis.ts / models.py / contract.md)이 바뀌면 동시 갱신 필수.
#
# 저장: 라이브 users/{uid}.bodyProfile + per-analysis SNAPSHOT
#   users/{uid}/analyses/{id}.bodyProfile (결과 화면 재현성, R1 — 결과는
#   분석-당시 snapshot 을 source-of-truth 로 읽음, live 프로필 아님).
# 자가입력 보조 데이터 — 점수/분석 단정에 사용 금지. weightKg 는 특히 보조
# ONLY 이며 scoring/analysis consumer 모듈에 유입되면 안 됨 (D-05).
EXPERIENCE_LEVELS = ("beginner", "intermediate", "advanced")
DOMINANT_HANDS = ("left", "right", "both")
# 폴스포츠 고하중 관절 (docs/research/폴스포츠-지식.md 정합) — 통증부위 다중선택.
PAIN_AREAS = (
    "shoulder",
    "wrist",
    "lower_back",
    "knee",
    "ankle",
    "neck",
    "hip",
    "elbow",
)

# height/weight 합리적 범위 (범위 밖 → None, 위조/오타 graceful 차단).
_BODY_HEIGHT_CM_MIN = 90
_BODY_HEIGHT_CM_MAX = 250
_BODY_WEIGHT_KG_MIN = 25
_BODY_WEIGHT_KG_MAX = 200


def _coerce_number_in_range(value, lo, hi):  # noqa: ANN001
    """숫자 + 범위 검증 helper. bool 은 int subclass 라 명시 거부.

    lo/hi 는 inclusive. 비-숫자·범위 밖 → None.

    [WR-02] cm/kg 는 정수 계약이다. 폼은 정수만 보내지만 이 normalizer 는 폼이
    아닌 경로(dev 콘솔·import·타 writer)로 들어온 float(165.7) 도 방어하는 경계
    이므로, 정수가 아닌 값은 거부한다. 165.0 처럼 정수와 동일한 float 는 허용.
    """
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    if value != int(value):
        return None
    if value < lo or value > hi:
        return None
    return value


def normalize_body_profile(meta_value) -> dict | None:  # noqa: ANN001
    """자가입력 BodyProfile 방어 정규화 (D-06 graceful, raise 안 함).

    owner-write client 값이라 HTTP validator(validate_upload_request)와 달리
    실패 시 ValidationError 가 아니라 None / per-field None 을 반환한다.

    per-field 검증:
      · heightCm/weightKg : 숫자 + 범위 (90~250 / 25~200), 밖이면 None.
      · experience        : EXPERIENCE_LEVELS 멤버만, 아니면 None.
      · dominantHand      : DOMINANT_HANDS 멤버만, 아니면 None.
      · painAreas         : PAIN_AREAS 멤버인 string 만 유지 (비-string·비-멤버 제거).
      · 알 수 없는 키     : 무시.

    전 필드 None/빈([]) 이면 전체 None 반환 ("all-empty → omit snapshot" — R5).
    """
    if not isinstance(meta_value, dict):
        return None

    height = _coerce_number_in_range(
        meta_value.get("heightCm"), _BODY_HEIGHT_CM_MIN, _BODY_HEIGHT_CM_MAX
    )
    weight = _coerce_number_in_range(
        meta_value.get("weightKg"), _BODY_WEIGHT_KG_MIN, _BODY_WEIGHT_KG_MAX
    )

    exp = meta_value.get("experience")
    experience = exp if exp in EXPERIENCE_LEVELS else None

    hand = meta_value.get("dominantHand")
    dominant_hand = hand if hand in DOMINANT_HANDS else None

    raw_pain = meta_value.get("painAreas")
    pain_areas: list[str] = []
    if isinstance(raw_pain, list):
        pain_areas = [
            p for p in raw_pain if isinstance(p, str) and p in PAIN_AREAS
        ]

    if (
        height is None
        and weight is None
        and experience is None
        and dominant_hand is None
        and not pain_areas
    ):
        return None

    return {
        "heightCm": height,
        "weightKg": weight,
        "experience": experience,
        "painAreas": pain_areas,
        "dominantHand": dominant_hand,
    }


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

# Phase 11 (2026-06-17, Plan 11-00) — COACH-01 CoachCommentHook 신설.
#   CoachCommentHook = 리포트별 LLM 코칭 코멘트 hook (D-02 per-report 단위).
#   list 필드 = list[str] 전용 (nested array 금지). coach_comment / reviewed_by =
#   v1 항상 None (D-06 — v2 강사 콘솔 입력).
# HIGH-3: coach_hook.py 는 finding 클래스를 import 하지 않는다 (force_pattern /
#   body_normalizer 가 coach_hook 을 import 하므로 역참조 시 순환). builder 로직은
#   별도 모듈 coach_hook_builder.py.
# 본 위치는 re-export only (재정의 금지 — dataclass 본체는 coach_hook.py 에만 존재).
# TS 미러: app/src/types/analysis.ts CoachCommentHook interface.
# 변경 시 TS + docs/contract.md §9.11.7 + §8 동시 갱신 (CLAUDE.md Cross-cutting).
from .analysis.coach_hook import (  # noqa: E402, F401 — 파일 하단 re-export 패턴
    CoachCommentHook,
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
#   R1/R2: [Plan 08.1-00 Wave 0 박제 hard break] BodyLineTiltMetric 의
#          pelvis_distance_from_pole_axis / chest_distance_from_pole_axis /
#          coordinate_space / scale_denominator / deviation_direction 5 필드 영구
#          제거. tilt-only metric — IPSF Code of Points 글로벌 distance 항목 부재
#          (NotebookLM citation 9). per D-01.
#   R3:    ContactStabilityMetric = evidence-with-confidence: estimated_stable
#          nullable + distance_to_pole_norm + near_pole_ratio +
#          lost_near_pole_at_ms + measurement_kind.
#   R4:    PhaseBoundary.preflight_label_gate_passed nullable 신설.
#   R5:    StabilityMetric.jerk_unit='deg_per_sec_cubed' + jerk_score (deg/sec^3
#          FPS-normalized).
#
# Plan 08-02 활성화 (2026-06-09) — Plan 08-01 placeholder forward-declare 의
# 주석 prefix 제거. 3-way lockstep 의 Python 측면 active import 박제.
# 본 import 활성화 후에도 Plan 08-01 lockstep test 가 PASS 유지 강제 — field
# 이름이 grep 검증 source (placeholder 시기 + active import 시기 모두 통과).
from .analysis.force_signals import (  # noqa: E402, F401 — 파일 하단 re-export 패턴
    BodyLineTiltMetric,
    ContactPoint,
    ContactStabilityMetric,
    DeviationDirection,
    ForceSignalsReport,
    MetricConfidence,
    MotionPhase,
    PhaseBoundary,
    SeverityLevel,
    StabilityMetric,
)

# Phase 12 Wave 0B (Plan 12-01, 2026-06-10) — KeypointReport 신설 박제.
#   KeypointReport = 8 body keypoint flat + axisData polyline + axisMask.
#   TS 미러: app/src/types/analysis.ts KeypointReport interface.
#   docs 미러: docs/contract.md §9.12.
# 변경 시 양쪽 + docs/contract.md §9.12 동시 갱신 (CLAUDE.md Cross-cutting).
from .analysis.keypoint_frame import (  # noqa: E402, F401 — 파일 하단 re-export 패턴
    NUM_KEYPOINTS_PHASE12,
    KeypointName,
    KeypointReport,
)
# Field name lockstep — Plan 08-01 lockstep test grep source (active import 시기에도
# 통과 유지). camelCase ↔ snake_case mirror 박제 위치.
#   PhaseBoundary: phase / start_frame_idx / end_frame_idx / start_ms / end_ms /
#                  confidence / source / preflight_label_gate_passed (R4)
#   BodyLineTiltMetric: [Plan 08.1-00 Wave 0 hard break — 6 필드 only]
#                  phase / shoulder_tilt / hip_tilt / severity / confidence /
#                  warnings. Wave 0 stub: 모든 phase 에 대해 shoulder_tilt=None /
#                  hip_tilt=None / severity='low' / confidence='low' /
#                  warnings=['phase_8_1_wave_0_transitional']. Wave 1 가 실 tilt
#                  측정 알고리즘 + 정은지 분포 기반 threshold 배포.
#   StabilityMetric: phase / jitter_score / jerk_score /
#                  jerk_unit='deg_per_sec_cubed' (R5) / hold_stability_score /
#                  unstable_body_parts / severity / confidence / warnings
#   ContactStabilityMetric: phase / contact_point / measurement_kind (R3) /
#                  estimated_stable (R3, nullable) / distance_to_pole_norm (R3) /
#                  near_pole_ratio (R3) / lost_near_pole_at_ms (R3) /
#                  coordinate_space / severity / confidence / warnings
#   ForceSignalsReport: version / overall_confidence / warnings /
#                  phase_boundaries / axis_metrics / stability_metrics /
#                  contact_metrics
#   AnalysisResult field: forceSignalsReport optional (Plan 08-03 wiring 박제 후 활성화)
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
#   Cycle 1 신설 5: pole_line_missing / scale_unavailable /
#           preflight_label_gate_failed / fps_normalization_applied /
#           contact_evidence_only.
#           ([Plan 08.1-00 Wave 0 박제 제거] coordinate_space_unavailable —
#           BodyLineTiltMetric coordinate_space 필드 hard break 동행).
#   Cycle 2 신설 1: preflight_gate_pending (gate 미실행 default).
#   Phase 8.1 신설 2: axis_metric_transitional (top-level, compute_force_signals
#           가 stub 검출 시 emit) / phase_8_1_wave_0_transitional (axis_metrics
#           per-metric, compute_axis_deviation stub 박제 default).
#   Phase 4 신설 2 (Plan 04-01, POSE-03 D-08): ai_synthesis_failed (합성 어댑터
#           실패 → graceful degrade 발동) / ai_synthesis_partial (일부 frame
#           만 합성 성공 — indeterminate 응답 다수). docs/contract.md §9.8 mirror.

# ── Phase 4 Wave 1 (Plan 04-01) — SYNTHESIS_WARNING_CODES 박제 ──
# POSE-03 D-08 — Phase 4 합성 어댑터의 public warning enum.
# 3-way lockstep: docs/contract.md §9.8 + app/src/types/analysis.ts
# SynthesisWarningCode union 동시 갱신 (R3 fix). raw reason
# ('gemini_api_error' / 'gemini_parse_error' / 'g4_reference_guard' /
# 'exception' / 'invalid_input_shape' / 'model_resolve_failed' 등) 은
# ai_synthesis_meta["debugWarnings"] 에만 보존되고 본 frozenset 에는
# 포함하지 않는다 (HIGH-4 raw ↔ public 분리).
SYNTHESIS_WARNING_CODES: frozenset[str] = frozenset(
    {
        "ai_synthesis_failed",
        "ai_synthesis_partial",
    }
)
