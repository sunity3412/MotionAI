"""POST /upload-url 입력 검증. contract.md §2 UploadUrlRequest 기준.

순수 함수(boto3/네트워크 무관) — AWS 없이 유닛 테스트 가능해야 한다.
"""

from __future__ import annotations

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
