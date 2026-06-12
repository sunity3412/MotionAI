"""POST /reference/auto-register — 정은지 영상 → Gemini A → reference 자동 등록.

Plan 17-05 박제. AI-SPEC §1b 영역 A "Output Consequence" 직격 — reference DB 는 모든
mode1 비교의 baseline 이라 잘못된 IPSF 명칭/clipRange/checkpointJoints 가 박히면
전체 분석 오염. Firebase Auth + BELLE_UID 화이트리스트 이중 인증, G3 guardrail
(IPSF 미매치 → isActive=false), idempotent upsert (belle 검수 결과 보존) 3 박제.

흐름:
  1. Firebase ID token 검증 (sunity_shared.auth.verify_request).
  2. BELLE_UID env 화이트리스트 — belle 만 endpoint 호출 가능 (403 reject).
  3. body { s3Key, studioAlias?, overrideMotionId? } parse.
  4. S3 download → /tmp/<basename>.mp4 박제 (AI-SPEC §3 Pitfall #2: presigned URL 직접 X).
  5. extract_reference_metadata(local_path, studio_alias, override_motion_id) 호출 →
     Gemini A Pro Vision → ReferenceRegistration schema validated dict.
  6. None 이면 500 server_error (Gemini 실패 — caller 재시도 가능).
  7. firestore_admin.set_reference_motion_with_gemini(motion_id, gemini_a,
     idempotent=True) — reference/{motion_id} upsert. 기존 doc 의 isActive/
     inactiveReason 보존.
  8. 200 { motionId, routingBranch, reviewRequired, geminiA }.

env (template.yaml 박힘):
  · VIDEO_BUCKET — S3 영상 버킷명.
  · FIREBASE_SA_PARAM — SSM Parameter Store 의 Firebase 서비스 계정 JSON 키.
  · BELLE_UID — belle Firebase uid (1인 호출 박제).
  · GEMINI_A_MODEL (optional) — resolve_model('A', env_override=...) 단일 source.

Lambda Timeout 240s (W2 정합) — Files API 폴링 upper bound 120s + Pro 호출 ~15s +
Pydantic / S3 download / Firestore write ~5s + cold start/jitter 100s. 120s 박제는
폴링만으로 timeout 예산 소진 위험 (3차 R-W2).
"""

from __future__ import annotations

import logging
import os

import boto3  # Lambda 런타임 제공
from botocore.exceptions import ClientError

from sunity_shared import responses
from sunity_shared.auth import AuthError, verify_request
from sunity_shared.firestore_admin import set_reference_motion_with_gemini
from sunity_shared.gemini.reference_extractor import extract_reference_metadata

log = logging.getLogger()
log.setLevel(logging.INFO)


_BUCKET = os.environ.get("VIDEO_BUCKET", "")
_BELLE_UID = os.environ.get("BELLE_UID", "")
_s3 = boto3.client("s3")


def _basename_from_s3_key(s3_key: str) -> str:
    """S3 key (예: 'reference/butterfly.mp4') → basename ('butterfly.mp4') 박제.

    /tmp/<basename> 박제 정합. AWS Lambda /tmp 는 512MB 제한 — reference 영상
    (영상당 통상 20-50MB) 충분.
    """
    return s3_key.rsplit("/", 1)[-1] or "ref-auto.mp4"


def _download_s3_to_tmp(s3_key: str) -> str:
    """S3 객체 다운로드 → /tmp/<basename>. presigned URL 직접 X (AI-SPEC §3 Pitfall #2).

    Returns:
      로컬 path (/tmp/<basename>).

    Raises:
      ClientError: NoSuchKey / NoSuchBucket / AccessDenied 등.
    """
    obj = _s3.get_object(Bucket=_BUCKET, Key=s3_key)
    body = obj["Body"].read()
    local_path = f"/tmp/{_basename_from_s3_key(s3_key)}"
    with open(local_path, "wb") as f:
        f.write(body)
    return local_path


def lambda_handler(event: dict, _context) -> dict:
    # 1. Firebase ID token 검증.
    try:
        uid = verify_request(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)

    # 2. BELLE_UID 화이트리스트 — belle 만 호출 가능.
    # env 미설정 시 reject (조용한 통과 금지 — 운영 실수 1차 차단).
    if not _BELLE_UID or uid != _BELLE_UID:
        log.warning(
            "reference-auto-register forbidden — uid=%s belle_uid_set=%s",
            uid,
            bool(_BELLE_UID),
        )
        return responses.error(
            "forbidden",
            "이 endpoint 는 reference 등록 권한이 박혀있는 계정만 호출 가능합니다.",
            status=403,
        )

    # 3. body parse.
    body = responses.parse_json_body(event)
    s3_key = body.get("s3Key")
    if not s3_key or not isinstance(s3_key, str):
        return responses.error(
            "bad_request",
            "s3Key 가 필요합니다 (reference 영상 S3 key).",
            status=400,
        )
    studio_alias = body.get("studioAlias")
    override_motion_id = body.get("overrideMotionId")

    # 4. S3 download.
    try:
        local_path = _download_s3_to_tmp(s3_key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "NoSuchKey":
            return responses.error(
                "s3_object_not_found",
                f"S3 객체를 찾지 못했습니다: {s3_key}",
                status=404,
            )
        log.exception("S3 download 실패 s3_key=%s code=%s", s3_key, code)
        return responses.error(
            "server_error",
            "영상 다운로드에 실패했어요.",
            status=500,
        )
    except Exception:  # noqa: BLE001 - 다운로드 단계 server_error 통일
        log.exception("S3 download 실패 s3_key=%s", s3_key)
        return responses.error(
            "server_error",
            "영상 다운로드에 실패했어요.",
            status=500,
        )

    # 5. extract_reference_metadata 호출.
    try:
        gemini_a = extract_reference_metadata(
            local_path,
            studio_alias=studio_alias,
            override_motion_id=override_motion_id,
        )
    except ValueError as exc:
        # ALLOWED_MODELS 박제 외 또는 G1 guardrail (좌표/점수/판단 어휘 매치).
        # graceful X — caller hard fail 인지 박제.
        log.warning("Gemini A hard fail s3_key=%s: %s", s3_key, exc)
        return responses.error("server_error", str(exc), status=500)

    if gemini_a is None:
        log.warning(
            "extract_reference_metadata None s3_key=%s — Gemini 호출 실패 (graceful).",
            s3_key,
        )
        return responses.error(
            "server_error",
            "Gemini Vision 호출에 실패했어요. 잠시 후 다시 시도해주세요.",
            status=500,
        )

    motion_id = gemini_a["motion_id"]

    # 6. Firestore upsert (idempotent).
    try:
        set_reference_motion_with_gemini(
            motion_id,
            gemini_a=gemini_a,
            idempotent=True,
        )
    except Exception:  # noqa: BLE001 - Firestore 실패 server_error 통일
        log.exception(
            "set_reference_motion_with_gemini 실패 motion_id=%s", motion_id
        )
        return responses.error(
            "server_error",
            "reference 등록에 실패했어요.",
            status=500,
        )

    log.info(
        "reference-auto-register ok motion_id=%s routing_branch=%s "
        "review_required=%s",
        motion_id,
        gemini_a.get("routing_branch"),
        gemini_a.get("review_required"),
    )

    return responses.ok(
        {
            "motionId": motion_id,
            "routingBranch": gemini_a.get("routing_branch"),
            "reviewRequired": gemini_a.get("review_required"),
            "geminiA": gemini_a,
        }
    )
