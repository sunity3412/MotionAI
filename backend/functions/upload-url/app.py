"""POST /upload-url — S3 presigned PUT URL 발급.

contract.md §2:
  요청  UploadUrlRequest  { mode, fileName, fileSizeBytes, format, referenceMotionId? }
  응답  UploadUrlResponse { analysisId, uploadUrl, s3Key, expiresInSec }

흐름(계약 §1): 이 함수는 analysisId 와 presigned URL 만 만든다.
Firestore users/{uid}/analyses/{id} 문서(status='uploading') 생성과 S3 PUT 은
앱이 직접 한다. 영상은 절대 Lambda 를 거치지 않는다.
"""

from __future__ import annotations

import logging
import os
import uuid

import boto3  # Lambda 런타임 제공

from sunity_shared import responses
from sunity_shared.auth import AuthError, verify_request
from sunity_shared.s3keys import build_upload_key
from sunity_shared.validation import ValidationError, validate_upload_request

log = logging.getLogger()
log.setLevel(logging.INFO)

_BUCKET = os.environ["VIDEO_BUCKET"]
_EXPIRES = 900  # presigned URL 만료(초)
_s3 = boto3.client("s3")


def lambda_handler(event: dict, _context) -> dict:
    # 1. 인증 (Firebase Auth UID, 익명 포함)
    try:
        uid = verify_request(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)

    # 2. 입력 검증 (contract UploadUrlRequest)
    try:
        req = validate_upload_request(responses.parse_json_body(event))
    except ValidationError as e:
        return responses.error(e.code, e.message, status=e.http_status)

    # 3. analysisId = Firestore 문서 ID. S3 키에 uid/analysisId 박아 트리거가 역추적
    analysis_id = uuid.uuid4().hex
    s3_key = build_upload_key(uid, analysis_id, req.fmt)

    # 4. presigned PUT URL. ContentType 을 묶지 않아 RN 클라이언트가
    #    헤더 불일치로 서명 실패하는 일을 피한다(키 프리픽스로 권한 제한됨).
    try:
        upload_url = _s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": _BUCKET, "Key": s3_key},
            ExpiresIn=_EXPIRES,
        )
    except Exception:  # noqa: BLE001 - 서명 실패는 서버 오류로 통일
        log.exception("presigned URL 생성 실패 analysis_id=%s", analysis_id)
        return responses.error(
            "server_error", "업로드 URL 생성에 실패했어요.", status=500
        )

    log.info("upload-url ok uid=%s analysis_id=%s mode=%s", uid, analysis_id, req.mode)
    return responses.ok(
        {
            "analysisId": analysis_id,
            "uploadUrl": upload_url,
            "s3Key": s3_key,
            "expiresInSec": _EXPIRES,
        }
    )
