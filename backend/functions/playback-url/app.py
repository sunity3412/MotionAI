"""POST /playback-url — 영상 재생용 S3 presigned GET URL 재발급.

박제 (2026-06-06 belle): myVideoUrl 의 S3 signed URL 은 7일 TTL.
mode3 second+ 가 일주일 뒤 prev 영상 fetch 시 만료 → 영상 안 뜸 보고.

흐름:
  앱 → POST /playback-url { analysisId, ext } + Firebase ID 토큰
  Lambda → uid 검증 → s3 key 빌드(uid 박제) → presigned GET 발급
  앱 → 새 URL 로 영상 재생

박제 보안: ext 박제로 S3 path injection 방지 (mp4|mov 만).
uid 가 token 박제 — caller 가 자기 영상만 fetch 가능.
"""

from __future__ import annotations

import logging
import os

import boto3

from sunity_shared import responses
from sunity_shared.auth import AuthError, verify_request
from sunity_shared.s3keys import build_upload_key

log = logging.getLogger()
log.setLevel(logging.INFO)

_BUCKET = os.environ["VIDEO_BUCKET"]
_PLAYBACK_EXPIRES = 7 * 24 * 60 * 60  # 7일 (S3 sign v4 + IAM 사용자 키 한계)
_ALLOWED_EXT = ("mp4", "mov")
_s3 = boto3.client("s3")


def lambda_handler(event: dict, _context) -> dict:
    # 1. Firebase Auth
    try:
        uid = verify_request(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)

    # 2. body 파싱
    body = responses.parse_json_body(event)
    analysis_id = body.get("analysisId", "")
    ext = body.get("ext", "mp4")

    if not analysis_id or not isinstance(analysis_id, str):
        return responses.error("bad_request", "analysisId 필수", status=400)
    if ext not in _ALLOWED_EXT:
        return responses.error("bad_request", f"ext 는 {_ALLOWED_EXT} 중 하나여야 합니다", status=400)
    # analysisId 정합 (uuid hex 32자) — path injection 방지
    if not (analysis_id.isalnum() and len(analysis_id) >= 16):
        return responses.error("bad_request", "analysisId 형식 오류", status=400)

    # 3. presigned GET (uid 가 token 박제 — caller 가 자기 영상만 fetch)
    key = build_upload_key(uid, analysis_id, ext)
    try:
        url = _s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": _BUCKET, "Key": key},
            ExpiresIn=_PLAYBACK_EXPIRES,
        )
    except Exception:  # noqa: BLE001
        log.exception("presigned GET 실패")
        return responses.error("server_error", "서명 실패", status=500)

    log.info("playback-url 발급 uid=%s analysis_id=%s ext=%s", uid, analysis_id, ext)
    return responses.ok({"playbackUrl": url, "expiresInSec": _PLAYBACK_EXPIRES})
