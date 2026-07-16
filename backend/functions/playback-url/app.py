"""POST /playback-url — 영상 재생용 S3 presigned GET URL 재발급.

박제 (2026-06-06 belle): myVideoUrl 의 S3 signed URL 은 7일 TTL.
mode3 second+ 가 일주일 뒤 prev 영상 fetch 시 만료 → 영상 안 뜸 보고.

29-CONTEXT D-09 — D1 fix (진단: presigned 7일 TTL 만료 확정 — 신선/구 mode1 doc
referenceVideoUrl 모두 AccessDenied "Request has expired", 동일 키 재서명은 206).
referenceMotionId 재서명 경로 확장: mode1 우측(정은지) 영상도 7일 후 재발급 가능.

흐름:
  앱 → POST /playback-url { analysisId, ext } + Firebase ID 토큰        (기존)
  앱 → POST /playback-url { referenceMotionId } + Firebase ID 토큰     (신규)
  Lambda → uid 검증 → s3 key 빌드/조회 → presigned GET 발급
  앱 → 새 URL 로 영상 재생

박제 보안: ext 박제로 S3 path injection 방지 (mp4|mov 만).
uid 가 token 박제 — caller 가 자기 영상만 fetch 가능.
reference 는 클라이언트 S3 키 직접 수용 금지 — Firestore canonical
reference/{id} doc 의 videoS3Key 화이트리스트 경유만 (T-29-06-01).

# 29-PLAN-REVIEW HIGH-2 — isActive/prefix 가드: auto-registration 이 reject/G3
# 경로에서 inactive doc 을 실제로 만들므로, 무가드 서명은 미승인 reference 영상이
# id 추측만으로 노출되는 EoP. 가드 실패는 전부 동일 404 (숨김 doc 존재 leak 0).
"""

from __future__ import annotations

import logging
import os
import re

import boto3

from sunity_shared import firestore_admin, responses
from sunity_shared.auth import AuthError, verify_request
from sunity_shared.s3keys import build_upload_key

log = logging.getLogger()
log.setLevel(logging.INFO)

_BUCKET = os.environ["VIDEO_BUCKET"]
_PLAYBACK_EXPIRES = 7 * 24 * 60 * 60  # 7일 (S3 sign v4 + IAM 사용자 키 한계)
_ALLOWED_EXT = ("mp4", "mov")
# referenceMotionId 형식 화이트리스트 (path injection 방지 — analysisId 검증 스타일).
# 실측 id 예: ref-power-spin (영숫자 + 하이픈).
_REF_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")
# 재서명 허용 S3 키 prefix (Task 1 실측: 전 11 doc videoS3Key = reference/*.mp4).
_REF_KEY_PREFIX = "reference/"
_s3 = boto3.client("s3")


def _sign_get(key: str) -> str | None:
    """presigned GET 발급. 실패 시 None (caller 가 500 응답)."""
    try:
        return _s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": _BUCKET, "Key": key},
            ExpiresIn=_PLAYBACK_EXPIRES,
        )
    except Exception:  # noqa: BLE001 - 서명 실패는 서버 오류로 통일
        log.exception("presigned GET 실패")
        return None


def _handle_reference(uid: str, reference_motion_id: str) -> dict:
    """referenceMotionId 재서명 — Firestore doc videoS3Key 화이트리스트 경유만.

    경계 가드 4종 전부 통과해야 서명 (하나라도 실패 → 동일 404 not_found —
    inactive/부재/무영상 케이스가 응답으로 구분되지 않게, 숨김 doc leak 0):
      (a) doc 존재  (b) isActive is not False  (c) videoS3Key 존재
      (d) videoS3Key 가 reference/ prefix (allowlist)
    """
    if not _REF_ID_RE.match(reference_motion_id):
        return responses.error("bad_request", "referenceMotionId 형식 오류", status=400)

    # canonical 컬렉션 = models.REFERENCE_MOTIONS_COLLECTION("reference") —
    # get_reference_motion 이 models.reference_motion_path 경유 (리터럴 금지).
    doc = firestore_admin.get_reference_motion(reference_motion_id)
    key = (doc or {}).get("videoS3Key")
    guards_ok = (
        doc is not None
        and doc.get("isActive") is not False  # 29-PLAN-REVIEW HIGH-2 — EoP 차단
        and isinstance(key, str)
        and key.startswith(_REF_KEY_PREFIX)  # 29-PLAN-REVIEW HIGH-2 — prefix 가드
    )
    if not guards_ok:
        return responses.error("not_found", "기준 모션을 찾을 수 없어요.", status=404)

    url = _sign_get(key)
    if url is None:
        return responses.error("server_error", "서명 실패", status=500)

    log.info("playback-url 발급(reference) uid=%s ref_id=%s", uid, reference_motion_id)
    return responses.ok({"playbackUrl": url, "expiresInSec": _PLAYBACK_EXPIRES})


def lambda_handler(event: dict, _context) -> dict:
    # 1. Firebase Auth
    try:
        uid = verify_request(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)

    # 2. body 파싱
    body = responses.parse_json_body(event)
    analysis_id = body.get("analysisId", "")
    reference_motion_id = body.get("referenceMotionId", "")
    ext = body.get("ext", "mp4")

    # analysisId / referenceMotionId 상호 배타 (contract.md §2)
    if analysis_id and reference_motion_id:
        return responses.error(
            "bad_request", "analysisId 와 referenceMotionId 는 동시 사용 불가", status=400
        )

    if reference_motion_id:
        if not isinstance(reference_motion_id, str):
            return responses.error("bad_request", "referenceMotionId 형식 오류", status=400)
        return _handle_reference(uid, reference_motion_id)

    if not analysis_id or not isinstance(analysis_id, str):
        return responses.error("bad_request", "analysisId 필수", status=400)
    if ext not in _ALLOWED_EXT:
        return responses.error("bad_request", f"ext 는 {_ALLOWED_EXT} 중 하나여야 합니다", status=400)
    # analysisId 정합 (uuid hex 32자) — path injection 방지
    if not (analysis_id.isalnum() and len(analysis_id) >= 16):
        return responses.error("bad_request", "analysisId 형식 오류", status=400)

    # 3. presigned GET (uid 가 token 박제 — caller 가 자기 영상만 fetch)
    key = build_upload_key(uid, analysis_id, ext)
    url = _sign_get(key)
    if url is None:
        return responses.error("server_error", "서명 실패", status=500)

    log.info("playback-url 발급 uid=%s analysis_id=%s ext=%s", uid, analysis_id, ext)
    return responses.ok({"playbackUrl": url, "expiresInSec": _PLAYBACK_EXPIRES})
