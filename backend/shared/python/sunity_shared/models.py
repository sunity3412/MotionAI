"""Firestore 문서 모양 + 상수. docs/contract.md §3~5, app/src/types/analysis.ts 미러.

이 파일이 바뀌면 contract.md 와 app 타입도 같이 맞춰야 한다(계약 단일 진실).
"""

from __future__ import annotations

# ── 분석 모드 (contract.md §2 / ml_CLAUDE.md) ──────────────────────────
MODE_EXPERT = "mode1"  # 정은지(전문가) 비교
MODE_SELF = "mode3"  # 자기 성장 추적
MODES = (MODE_EXPERT, MODE_SELF)

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

# ── 분석 오류 코드 (contract.md §5 / ml_CLAUDE.md 4종) ─────────────────
ERR_NO_HUMAN = "no_human"
ERR_SIZE_EXCEEDED = "size_exceeded"
ERR_UNSUPPORTED_FORMAT = "unsupported_format"
ERR_SERVER_ERROR = "server_error"
ANALYSIS_ERROR_CODES = (
    ERR_NO_HUMAN,
    ERR_SIZE_EXCEEDED,
    ERR_UNSUPPORTED_FORMAT,
    ERR_SERVER_ERROR,
)

# UI 고정 문구. app/src/types/analysis.ts ERROR_MESSAGE 와 동일 문자열.
ERROR_MESSAGE = {
    ERR_NO_HUMAN: "영상에서 사람을 찾지 못했어요. 전신이 보이게 다시 촬영해주세요.",
    ERR_SIZE_EXCEEDED: "100MB 이하 영상만 분석할 수 있어요.",
    ERR_UNSUPPORTED_FORMAT: "mp4, mov 형식의 영상만 분석할 수 있어요.",
    ERR_SERVER_ERROR: "분석 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
}


def analysis_doc_path(uid: str, analysis_id: str) -> str:
    """Firestore: users/{uid}/analyses/{analysisId} (보안 규칙 격리 경로)."""
    return f"users/{uid}/analyses/{analysis_id}"


def reference_motion_path(motion_id: str) -> str:
    """Firestore: reference/motions/{motionId} (앱 읽기 전용)."""
    return f"reference/motions/{motion_id}"


REFERENCE_MOTIONS_COLLECTION = "reference/motions"
