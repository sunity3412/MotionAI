"""POST /upload-url · POST /reference/upload-url 입력 검증. contract.md §2 기준.

순수 함수(AWS SDK/네트워크 무관) — AWS 없이 유닛 테스트 가능해야 한다.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from . import models


class ValidationError(Exception):
    """검증 실패. http_status + (가능하면) contract 오류 code 를 실어 보낸다.

    code 가 ERROR_MESSAGE 에 있으면 앱이 동일 문구를 재사용(size_exceeded 등).
    그 외(bad_request)는 앱이 일반 처리.
    """

    def __init__(self, code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def validate_analysis_id_format(analysis_id) -> bool:
    """analysisId 형식 가드 (uuid hex 32자 전제 — 영숫자 + 길이 16 이상).

    31-10 L-03: upload-url / playback-url / visual-request 세 진입점이 같은 문자열
    규칙을 인라인으로 복제하고 있었다. S3 key path injection 방지가 목적이라 한 곳이
    느슨해지면 그 진입점만 뚫린다 — 공유 validator 로 단일화한다.

    형식 위반만 판정한다(존재/소유 여부는 호출측 Firestore 가드 몫).
    """
    return isinstance(analysis_id, str) and analysis_id.isalnum() and len(analysis_id) >= 16


@dataclass(frozen=True)
class UploadRequest:
    mode: str
    file_name: str
    file_size_bytes: int
    fmt: str
    reference_motion_id: str | None


def validate_upload_request(body: dict) -> UploadRequest:
    """contract UploadUrlRequest 검증 후 정규화. 실패 시 ValidationError.

    - format 불가  → unsupported_format (앱이 ERROR_MESSAGE 재사용)
    - 100MB 초과   → size_exceeded
    - mode1 인데 referenceMotionId 없음 → bad_request
    """
    if not isinstance(body, dict):
        raise ValidationError("bad_request", "요청 본문이 올바르지 않습니다.")

    mode = body.get("mode")
    if mode not in models.MODES:
        raise ValidationError("bad_request", "mode 는 mode1 또는 mode3 이어야 합니다.")

    file_name = body.get("fileName")
    if not isinstance(file_name, str) or not file_name.strip():
        raise ValidationError("bad_request", "fileName 이 필요합니다.")

    fmt = body.get("format")
    if fmt not in models.VIDEO_FORMATS:
        raise ValidationError(
            models.ERR_UNSUPPORTED_FORMAT,
            models.ERROR_MESSAGE[models.ERR_UNSUPPORTED_FORMAT],
        )

    size = body.get("fileSizeBytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValidationError("bad_request", "fileSizeBytes 가 올바르지 않습니다.")
    if size > models.MAX_VIDEO_BYTES:
        raise ValidationError(
            models.ERR_SIZE_EXCEEDED,
            models.ERROR_MESSAGE[models.ERR_SIZE_EXCEEDED],
        )

    ref_id = body.get("referenceMotionId")
    if mode == models.MODE_EXPERT:
        if not isinstance(ref_id, str) or not ref_id.strip():
            raise ValidationError(
                "bad_request", "mode1 은 referenceMotionId 가 필수입니다."
            )
        ref_id = ref_id.strip()
    else:
        ref_id = None  # mode3 은 비교 대상 없음

    return UploadRequest(
        mode=mode,
        file_name=file_name.strip(),
        file_size_bytes=size,
        fmt=fmt,
        reference_motion_id=ref_id,
    )


# ── Phase 38 (Plan 38-01) — POST /reference/upload-url 폼 검증 (D-07·D-08·D-14) ──
# 공급자 링크 페이지가 보낸 본문은 신뢰하지 않는다(T-38-01-3) — 클라이언트 검증(38-03
# supplierForm.ts)이 있어도 서버가 2차로 같은 규칙을 강제한다(REQ-38-6). 여기서 통과한
# 값만 38-06 writer 가 doc 에 적는다. 본문에 uid/refId 필드는 없다 — 키는 서버가
# 토큰 uid + 서버 생성 refId 로만 구성(T-38-01-2).

# 사전 선택한 기존 motionId(`ref-kip-up` 같은 seed id 또는 32 hex refId). 경로 조작 방지.
_TECHNIQUE_REF_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _is_real(v) -> bool:
    """유한 실수(bool 제외). JSON 숫자 = int|float, True/False 는 int 위장이라 거부."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _short_text(body: dict, key: str, message: str) -> str:
    v = body.get(key)
    if not isinstance(v, str):
        raise ValidationError("bad_request", message)
    v = v.strip()
    if not v or len(v) > models.REFERENCE_NAME_MAX_LEN:
        raise ValidationError("bad_request", message)
    return v


@dataclass(frozen=True)
class ReferenceUploadRequest:
    """검증·정규화된 공급자 폼(contract.md §2 ReferenceUploadUrlRequest).

    필수 동의 2(portrait·usage)는 필드로 두지 않는다 — 검증 통과 = 둘 다 True 가 불변이라
    값을 실어 보낼 이유가 없다. 학습 사용은 체크박스가 아니라 공급자 계약이 근거라 요청에
    없다(quick-260930-w9l 항목 5·11 — 서버 writer 가 consent.training·trainingBasis 를 적는다).
    선수 이름도 요청에 없다 — 서버가 공급자 displayName 으로 채운다(항목 10).
    동의 시각·문안 버전·uid 는 서버(38-06 writer)가 붙인다 — 본문의 at/version 은 무시
    (T-38-01-4). clip_range 는 (execStartS, execEndS) 초 단위 튜플 또는 None(D-06 선택).
    """

    name: str
    level: str
    technique_ref_id: str | None
    clip_range: tuple[float, float] | None
    fmt: str
    file_size_bytes: int
    duration_sec: float | None


# 옛 웹 번들(38-13 배포분)이 보내는 필드 — 검증 없이 무시한다(quick-260930-w9l 항목 9).
# 서 있는 시작은 파이프라인 no_standing_start 가 영상으로 판정한다. 목록은 문서용이며
# 코드는 이 키들을 읽지 않는다.
IGNORED_LEGACY_REFERENCE_FIELDS = (
    "athleteName",
    "isCombo",
    "isSplit",
    "hasHold",
    "standingStart",
    "consent.silent",
    "consent.training",
)

_CONSENT_MESSAGE = "필수 동의 2가지에 체크해주세요."


def validate_reference_upload_request(body: dict) -> ReferenceUploadRequest:
    """contract ReferenceUploadUrlRequest 검증 후 정규화. 실패 시 ValidationError.

    검사 순서·코드는 고정(앱 supplierForm 클라이언트 검증과 같은 순서 — 첫 위반 하나만 답한다):
      본문 → name → level → techniqueRefId → clipRange → consent(portrait·usage true)
      → format → fileSizeBytes → durationSec.
    옛 필드(IGNORED_LEGACY_REFERENCE_FIELDS)는 읽지 않는다 — 와도 통과(옛 웹 번들 호환).
    - format 불가       → unsupported_format (ERROR_MESSAGE 재사용)
    - 1GB 초과          → too_large (REGISTRATION_ERROR_MESSAGE 재사용 — 수강생 100MB 문구 아님)
    - durationSec 있고 5초 미만 → too_short / 120초 초과 → too_long
      (REGISTRATION_ERROR_MESSAGE 재사용). None 은 통과 — 웹이 metadata 를 못 읽은 경우
      fail-open(RESEARCH A12), 실제 길이는 파이프라인 probe 가 다시 거른다(38-07, R9).
    - 그 외 규칙 위반   → bad_request (message 는 페이지가 그대로 보여줄 한국어 안내)
    """
    if not isinstance(body, dict):
        raise ValidationError("bad_request", "요청 본문이 올바르지 않습니다.")

    name = _short_text(body, "name", "동작 이름을 고르거나 입력해주세요.")

    level = body.get("level")
    if level not in models.REFERENCE_LEVELS:
        raise ValidationError("bad_request", "레벨을 고르세요.")

    technique_ref_id = body.get("techniqueRefId")
    if technique_ref_id is not None:
        if not isinstance(technique_ref_id, str) or not _TECHNIQUE_REF_ID_RE.match(
            technique_ref_id
        ):
            raise ValidationError("bad_request", "techniqueRefId 가 올바르지 않습니다.")

    clip_range: tuple[float, float] | None = None
    raw_clip = body.get("clipRange")
    if raw_clip is not None:
        if not isinstance(raw_clip, dict):
            raise ValidationError("bad_request", "clipRange 가 올바르지 않습니다.")
        start = raw_clip.get("execStartS")
        end = raw_clip.get("execEndS")
        if not (_is_real(start) and _is_real(end) and 0 <= start < end):
            raise ValidationError("bad_request", "clipRange 가 올바르지 않습니다.")
        clip_range = (float(start), float(end))

    consent = body.get("consent")
    if not isinstance(consent, dict):
        raise ValidationError("bad_request", _CONSENT_MESSAGE)
    for key in ("portrait", "usage"):
        if consent.get(key) is not True:
            raise ValidationError("bad_request", _CONSENT_MESSAGE)

    fmt = body.get("format")
    if fmt not in models.VIDEO_FORMATS:
        raise ValidationError(
            models.ERR_UNSUPPORTED_FORMAT,
            models.ERROR_MESSAGE[models.ERR_UNSUPPORTED_FORMAT],
        )

    size = body.get("fileSizeBytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValidationError("bad_request", "fileSizeBytes 가 올바르지 않습니다.")
    if size > models.REFERENCE_MAX_VIDEO_BYTES:
        raise ValidationError(
            models.REG_ERR_TOO_LARGE,
            models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_LARGE],
        )

    duration_sec: float | None = None
    raw_duration = body.get("durationSec")
    if raw_duration is not None:
        if not _is_real(raw_duration) or raw_duration <= 0:
            raise ValidationError("bad_request", "durationSec 가 올바르지 않습니다.")
        duration_sec = float(raw_duration)
        if duration_sec < models.REFERENCE_MIN_DURATION_SEC:
            raise ValidationError(
                models.REG_ERR_TOO_SHORT,
                models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_SHORT],
            )
        if duration_sec > models.REFERENCE_MAX_DURATION_SEC:
            raise ValidationError(
                models.REG_ERR_TOO_LONG,
                models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_LONG],
            )

    return ReferenceUploadRequest(
        name=name,
        level=level,
        technique_ref_id=technique_ref_id,
        clip_range=clip_range,
        fmt=fmt,
        file_size_bytes=size,
        duration_sec=duration_sec,
    )
