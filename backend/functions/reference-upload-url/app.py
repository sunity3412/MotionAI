"""POST /reference/upload-url — 공급자 링크 기준 영상 presigned PUT 발급 + 등록 doc 선작성.

contract.md §2 `POST /reference/upload-url` · Phase 38 D-03(화이트리스트) / D-04(선작성) /
D-08(동의 서버 기록) / D-12(probe) · 리뷰 R4(서명 → create 순서, uploadExpiresAt) /
R5(upload 키만 서명).

  요청  ReferenceUploadUrlRequest { name, athleteName, level, techniqueRefId?, isCombo?,
        isSplit, hasHold, standingStart, clipRange?, consent, format, fileSizeBytes,
        durationSec? }   또는   { probe: true }
  응답  ReferenceUploadUrlResponse { refId, uploadUrl, s3Key, expiresInSec }
        probe → SupplierProbeResponse { probe: true, uid, supplierCode }

흐름: 인증 → SSM 화이트리스트(∪ BELLE_UID) → (probe | 폼 검증 → 서버 refId → presign
`reference/{uid}/{refId}/upload.{ext}` → 공개 `reference/{refId}` + 비공개
`reference/{refId}/private/registration` batch create → 응답). 이후 S3 PUT 은 브라우저가
직접 하고 ObjectCreated → SQS → pipeline(38-07)이 등록을 잇는다. 영상은 절대 Lambda 를
거치지 않는다.

본문의 uid/refId 는 절대 읽지 않는다(V4) — 키·doc 은 토큰 uid 와 서버 uuid4 hex 로만.
서명 → create 순서인 이유: 서명은 순수 함수(네트워크 0)라 실패가 드물고, create 실패 시
URL 을 안 주면 객체가 생길 수 없다(고아 객체 없음). 반대 순서면 registering doc 만 남는데
그것도 uploadExpiresAt 스윕이 expired 로 닫는다(R4) — 그래도 남기지 않는 쪽을 고른다.

env (38-09 template 이 박는다):
  · VIDEO_BUCKET — S3 영상 버킷명.
  · BELLE_UID — belle Firebase uid (SSM 화이트리스트와 합집합).
  · SUPPLIER_UIDS_PARAM — SSM 파라미터명(기본 models.SUPPLIER_UIDS_PARAM_DEFAULT),
    값은 `uid:CODE, uid, ...` (models.parse_supplier_uids).
  · FIREBASE_SA_PARAM — 인증(sunity_shared.auth).
운영 규칙(T-38-06-2): 익명 uid 는 화이트리스트에 올리지 않는다 — 공급자는 로그인 계정만.
"""

from __future__ import annotations

import logging
import os
import time
import uuid

import boto3  # Lambda 런타임 제공

from sunity_shared import firestore_admin, models, responses
from sunity_shared.auth import AuthError, verify_request
from sunity_shared.s3keys import build_reference_upload_key
from sunity_shared.validation import ValidationError, validate_reference_upload_request

log = logging.getLogger()
log.setLevel(logging.INFO)

_BUCKET = os.environ["VIDEO_BUCKET"]
# 리뷰 R4 — presign ExpiresIn 과 doc uploadExpiresAt 이 **한 상수**(900). 두 값이 어긋나면
# 스윕이 만료를 판정하는 시각과 URL 이 실제로 죽는 시각이 갈린다. 900 리터럴 금지.
_EXPIRES = int(models.REFERENCE_UPLOAD_EXPIRES_SEC)
_BELLE_UID = os.environ.get("BELLE_UID", "")
_SUPPLIER_UIDS_PARAM = os.environ.get("SUPPLIER_UIDS_PARAM", models.SUPPLIER_UIDS_PARAM_DEFAULT)
_SUPPLIER_CACHE_TTL_S = 60
_s3 = boto3.client("s3")

# (map, loaded_at monotonic) — Lambda 컨테이너 수명 동안 60초 캐시.
_supplier_cache: tuple[dict[str, str | None], float] | None = None


def _load_supplier_map() -> dict[str, str | None]:
    """SSM `SUPPLIER_UIDS_PARAM` → {uid: 강사코드|None} (D-03·D-12). 60초 모듈 캐시.

    파라미터 부재·권한 거부·형식 오류 = **빈 맵**(warning 만 — 값·예외 본문은 로그에
    남기지 않는다, T-38-06-6) → BELLE_UID 외 전부 403(조용한 통과 금지). 실패는 캐시하지
    않는다 — 일시 장애 뒤 다음 요청이 곧바로 복구된다.
    """
    global _supplier_cache
    now = time.monotonic()
    if _supplier_cache is not None and now - _supplier_cache[1] < _SUPPLIER_CACHE_TTL_S:
        return _supplier_cache[0]
    try:
        value = boto3.client("ssm").get_parameter(
            Name=_SUPPLIER_UIDS_PARAM, WithDecryption=True
        )["Parameter"]["Value"]
        supplier_map = models.parse_supplier_uids(value)
    except Exception:  # noqa: BLE001 - 조회 실패 = 빈 화이트리스트(값·예외 본문 로그 금지)
        log.warning("supplier-uids 조회 실패 param=%s", _SUPPLIER_UIDS_PARAM)
        return {}
    _supplier_cache = (supplier_map, now)
    return supplier_map


def _is_supplier(uid: str, supplier_map: dict[str, str | None]) -> bool:
    """화이트리스트 판정 — SSM map ∪ BELLE_UID. env 미설정(빈 BELLE_UID)은 통과 재료가 아니다."""
    if not uid:
        return False
    return uid in supplier_map or (bool(_BELLE_UID) and uid == _BELLE_UID)


def lambda_handler(event: dict, _context) -> dict:
    # 1. 인증 (Firebase Auth UID). 익명도 토큰은 통과하지만 화이트리스트에 없어 2 에서 막힌다.
    try:
        uid = verify_request(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)

    # 2. 화이트리스트 (D-03) — 파라미터 없음 / env 미설정 = 403 (조용한 통과 금지).
    body = responses.parse_json_body(event)
    supplier_map = _load_supplier_map()
    if not _is_supplier(uid, supplier_map):
        log.warning(
            "reference-upload-url forbidden uid=%s supplier_count=%s belle_uid_set=%s",
            uid,
            len(supplier_map),
            bool(_BELLE_UID),
        )
        return responses.error("forbidden", "공급자로 등록된 계정만 쓸 수 있어요.", status=403)

    # 3. probe (D-12) — 페이지 '내 코드' 카드 재료. 부작용 0. bool True 만 probe 로 본다.
    if body.get("probe") is True:
        return responses.ok({"probe": True, "uid": uid, "supplierCode": supplier_map.get(uid)})

    # 4. 폼 검증 (contract ReferenceUploadUrlRequest — 38-01 순수 검증, 첫 위반 하나만 답한다).
    try:
        req = validate_reference_upload_request(body)
    except ValidationError as e:
        return responses.error(e.code, e.message, status=e.http_status)

    # 5. refId = Firestore doc id = 서버 uuid4 hex. 업로드 키는 토큰 uid + refId 만(V4, R5) —
    #    `upload.{ext}` 에만 서명하고 확정 키 `v1.{ext}` 는 서버 copy_object 전용이다.
    ref_id = uuid.uuid4().hex
    s3_key = build_reference_upload_key(uid, ref_id, req.fmt)

    # 6. presigned PUT. ContentType 을 묶지 않아 브라우저/RN 클라이언트가 헤더 불일치로 서명
    #    실패하는 일을 피한다(키 프리픽스 `reference/*` 로 권한 제한 — 38-09 template).
    #    서명은 순수 계산이라 네트워크 0. 실패면 doc 을 만들지 않는다.
    try:
        upload_url = _s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": _BUCKET, "Key": s3_key},
            ExpiresIn=_EXPIRES,
        )
    except Exception:  # noqa: BLE001 - 서명 실패는 서버 오류로 통일(doc 미생성)
        log.exception("presigned URL 생성 실패 uid=%s ref_id=%s", uid, ref_id)
        return responses.error("server_error", "업로드 URL 생성에 실패했어요.", status=500)

    # 7. 공개 + 비공개 doc batch create (D-04·D-08·R13). uploadExpiresAt 은 서명 만료와
    #    같은 상수(R4). 실패면 **URL 은 버린다** — 응답에 싣지 않으므로 객체가 생길 수 없고
    #    고아 객체가 남지 않는다. 동의 시각은 서버 시각(D-08 부인 방지).
    now_ms = int(time.time() * 1000)
    try:
        firestore_admin.create_reference_registration(
            ref_id,
            supplier_uid=uid,
            form=req,
            upload_key=s3_key,
            upload_expires_at_ms=now_ms + _EXPIRES * 1000,
            consent_at_ms=now_ms,
            supplier_code=supplier_map.get(uid),
        )
    except Exception:  # noqa: BLE001 - Firestore 실패(AlreadyExists 포함) server_error 통일
        log.exception("등록 doc 선작성 실패 uid=%s ref_id=%s", uid, ref_id)
        return responses.error("server_error", "등록 문서 생성에 실패했어요.", status=500)

    # 8. 응답.
    log.info(
        "reference-upload-url ok uid=%s ref_id=%s level=%s combo=%s",
        uid,
        ref_id,
        req.level,
        req.is_combo,
    )
    return responses.ok(
        {
            "refId": ref_id,
            "uploadUrl": upload_url,
            "s3Key": s3_key,
            "expiresInSec": _EXPIRES,
        }
    )
