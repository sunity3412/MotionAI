"""Firestore 문서 모양 + 상수. docs/contract.md §3~5, app/src/types/analysis.ts 미러.

이 파일이 바뀌면 contract.md 와 app 타입도 같이 맞춰야 한다(계약 단일 진실).
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
DIM_LINE = "line"          # 라인·확장 (사지 신전 완성도)
DIM_BALANCE = "balance"    # 균형·정렬 (좌우 대칭)
DIM_STABILITY = "stability"  # 안정성·홀딩 (피크 구간 떨림)
SCORE_DIMENSIONS = (DIM_ANGLE, DIM_LINE, DIM_BALANCE, DIM_STABILITY)
# 기준 영상 없이 산출 가능 — mode3 자기 성장(세션 간 델타 같은 척도) 핵심.
ABSOLUTE_DIMENSIONS = (DIM_LINE, DIM_BALANCE, DIM_STABILITY)

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
