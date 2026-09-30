"""POST /reference/upload-url — 공급자 링크 기준 영상 presigned PUT 발급 + 등록 doc 선작성.

contract.md §2 `POST /reference/upload-url` · Phase 38 D-03(화이트리스트) / D-04(선작성) /
D-08(동의 서버 기록) / D-12(probe) · 리뷰 R4(서명 → create 순서, uploadExpiresAt) /
R5(upload 키만 서명).

  요청  ReferenceUploadUrlRequest { name, athleteName, level, techniqueRefId?, isCombo?,
        isSplit, hasHold, standingStart, clipRange?, consent, format, fileSizeBytes,
        durationSec? }   또는   { probe: true }
  응답  ReferenceUploadUrlResponse { refId, uploadUrl, s3Key, expiresInSec }
        probe → SupplierProbeResponse { probe: true, uid, supplierCode, displayName }
  403   { error: { code: 'not_invited', message, email } } — email = 토큰 메일(없으면 null)

흐름: 인증(uid·email·email_verified) → 명단 판정 → (probe | 폼 검증 → 서버 refId → presign
`reference/{uid}/{refId}/upload.{ext}` → 공개 `reference/{refId}` + 비공개
`reference/{refId}/private/registration` batch create → 응답). 이후 S3 PUT 은 브라우저가
직접 하고 ObjectCreated → SQS → pipeline(38-07)이 등록을 잇는다. 영상은 절대 Lambda 를
거치지 않는다.

명단 판정(quick-260930-lfw, 38-DESIGN-v2 §W1 — probe·업로드가 같은 `_authorize` 를 쓴다):
  ① `suppliers/{uid}` doc 이 있으면 그 active 가 결정(SSM·BELLE_UID 보다 우선 — deactivate 가
     SSM 에 남은 uid 도 막는다). doc 이 없으면 SSM ∪ BELLE_UID. 결과(통과든 None 이든)를
     uid 별 60초 `_roster_cache` 에 담는다.
  ② 그래도 밖이고 토큰 email_verified 가 True 이고 메일이 있으면 **캐시 적중 여부와 무관하게**
     초대 수락(firestore_admin.accept_supplier_invite)을 시도한다 — 음성 캐시가 방금 만든
     초대를 60초 막지 않게. 수락되면 그 uid 캐시를 바로 갱신한다.
  ③ 그래도 밖이면 403 not_invited(error.email = 토큰 메일). 로그에는 가린 메일만.
  get_supplier·accept 예외는 500 server_error — 조용히 403 으로 바꾸지 않는다.
  캐시 때문에 deactivate 는 warm 컨테이너에 최대 60초 늦게 닿는다(라이브 확인이 65초
  기다리는 이유).

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
초대 수락은 email_verified 토큰만 한다(익명 토큰엔 메일이 없다).
"""

from __future__ import annotations

import logging
import os
import time
import uuid

import boto3  # Lambda 런타임 제공

from sunity_shared import firestore_admin, models, responses, supplier_invites
from sunity_shared.auth import AuthError, verify_request_claims
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
# uid → (SupplierEntry | None, loaded_at monotonic) — get_supplier + roster_decision 결과만.
# 초대 수락 시도는 이 캐시를 거치지 않는다(음성 캐시가 수락을 막지 않게, 체커 W3).
_roster_cache: dict[str, tuple[supplier_invites.SupplierEntry | None, float]] = {}
_ROSTER_CACHE_MAX = 512


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


def _authorize(claims: dict, supplier_map: dict[str, str | None]):
    """명단 판정 + 초대 수락 → SupplierEntry | None. Firestore 예외는 호출측이 500 으로.

    모듈 docstring "명단 판정" ①②. firestore_admin 함수는 모듈 속성으로 부른다(테스트가
    seam 을 바꿀 수 있게).
    """
    uid = claims.get("uid") or ""
    if not uid:
        return None
    now = time.monotonic()
    hit = _roster_cache.get(uid)
    if hit is not None and now - hit[1] < _SUPPLIER_CACHE_TTL_S:
        entry = hit[0]
    else:
        doc = firestore_admin.get_supplier(uid)
        entry = supplier_invites.roster_decision(doc, supplier_map, _BELLE_UID, uid)
        if len(_roster_cache) >= _ROSTER_CACHE_MAX:
            _roster_cache.clear()
        _roster_cache[uid] = (entry, now)
    email = claims.get("email")
    if entry is None and claims.get("email_verified") is True and email:
        entry = firestore_admin.accept_supplier_invite(uid, email, int(time.time() * 1000))
        if entry is not None:
            _roster_cache[uid] = (entry, time.monotonic())  # 38-DESIGN-v2 "수락 직후 무효화"
    return entry


def lambda_handler(event: dict, _context) -> dict:
    # 1. 인증 (Firebase Auth UID + email·email_verified). 익명도 토큰은 통과하지만 명단에 없고
    #    메일도 없어 2 에서 막힌다.
    try:
        claims = verify_request_claims(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)
    uid = claims["uid"]
    email = claims.get("email")

    # 2. 명단 판정 + 초대 수락 (38-DESIGN-v2 §W1). Firestore 실패는 500 — 403 으로 강등 금지.
    body = responses.parse_json_body(event)
    supplier_map = _load_supplier_map()
    try:
        entry = _authorize(claims, supplier_map)
    except Exception:  # noqa: BLE001 - 명단/수락 Firestore 실패 = server_error(조용한 403 금지)
        log.exception("reference-upload-url roster 실패 uid=%s", uid)
        return responses.error("server_error", "권한 확인에 실패했어요.", status=500)
    if entry is None:
        log.warning(
            "reference-upload-url not_invited uid=%s email=%s verified=%s supplier_count=%s "
            "belle_uid_set=%s",
            uid,
            supplier_invites.mask_email(email) if email else None,
            claims.get("email_verified") is True,
            len(supplier_map),
            bool(_BELLE_UID),
        )
        return responses.error(
            models.SUPPLIER_ERR_NOT_INVITED,
            models.SUPPLIER_NOT_INVITED_MESSAGE,
            status=403,
            extra={"email": email},
        )

    # 3. probe (D-12) — 페이지 진입 게이트 + 강사 코드 줄 재료. 수락 말고 부작용 0.
    #    bool True 만 probe 로 본다. 응답은 옛 모양을 넓힌다(플래너 결정 (a) — 배포된 옛 웹
    #    번들이 supplierCode 를 읽는다).
    if body.get("probe") is True:
        return responses.ok(
            {
                "probe": True,
                "uid": uid,
                "supplierCode": entry.code,
                "displayName": entry.display_name,
            }
        )

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
            supplier_code=entry.code,
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
