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

from sunity_shared import firestore_admin, models, responses
from sunity_shared.auth import AuthError, verify_request
from sunity_shared.s3keys import (
    build_coach_audio_key,
    build_fault_zoom_key,
    build_rendered_compare_key,
    build_upload_key,
    parse_result_key_from_presigned_url,
)
from sunity_shared.validation import validate_analysis_id_format

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
# Phase 31 asset 확장 (contract.md "POST /playback-url — asset 확장", 리뷰 H-02).
# 표시 URL 은 매 요청 재서명이라 1시간이면 충분하다 — 영상 재생용 7일과 다르다.
_ASSET_EXPIRES = 3600
# mp3 = Phase 32 (Plan 32-16, D-18) 재생 중 큐 오디오 (contract.md §12.7).
_ASSET_CONTENT_TYPE = {"png": "image/png", "mp4": "video/mp4", "mp3": "audio/mpeg"}
# Phase 32 (Plan 32-16) — coachAudio asset 의 recordId 형식 화이트리스트
# (contract.md §12.3 'r{index:02d}:{criterion}' — criterion 은 영숫자·언더스코어).
# path injection('../' 등) 을 canonical key 구성 **전에** 차단한다 (_REF_ID_RE 선례).
# exact 비교(H-02)가 최종 방어지만, 형식 가드로 조작 입력이 key 빌더에 닿지 않게 한다.
_COACH_AUDIO_RECORD_ID_RE = re.compile(r"^r[0-9]{2}:[A-Za-z0-9_]{1,64}$")
_s3 = boto3.client("s3")


def _sign_get(key: str, *, expires: int | None = None, content_type: str | None = None) -> str | None:
    """presigned GET 발급. 실패 시 None (caller 가 500 응답).

    content_type 지정 시 ResponseContentType 을 서명에 포함한다 — 브라우저/RN 이
    S3 기본 octet-stream 대신 이미지/영상으로 렌더링하도록.
    """
    params: dict = {"Bucket": _BUCKET, "Key": key}
    if content_type:
        params["ResponseContentType"] = content_type
    try:
        return _s3.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires if expires is not None else _PLAYBACK_EXPIRES,
        )
    except Exception:  # noqa: BLE001 - 서명 실패는 서버 오류로 통일
        log.exception("presigned GET 실패")
        return None


def _handle_asset(uid: str, analysis_id: str, asset: str) -> dict:
    """asset 재서명 — 서버가 key 를 **구성**하고 저장 key 와 exact 비교 (M2-01).

    클라이언트는 asset 종류만 고르고 key 는 절대 보내지 않는다(H-02/H-05). 저장된
    key 를 그대로 서명하지 않고 canonical 형태를 서버가 새로 만들어 **전체 문자열
    일치**를 요구하는 이유(2차 리뷰 M2-01): 생성 실패로 status 가 failed 로 돌아간
    뒤에도 이전 성공분의 key 필드가 문서에 남을 수 있다. basename prefix 검사만 하면
    그 stale key 가 계속 서명된다. status=='done' + exact equality 두 가지를 모두
    요구해야 "지금 이 분석 건의 현재 asset" 만 서명된다.

    가드 위반은 전부 동일 404 — 어느 단계에서 걸렸는지 응답으로 구분되지 않는다.
    """
    doc = firestore_admin.get_analysis(uid, analysis_id) or {}
    result = doc.get("result")
    result = result if isinstance(result, dict) else {}

    if asset == models.VISUAL_KIND_CORRECTED_POSE:
        joint = result.get("correctedPoseJoint")
        stored = result.get("correctedPoseKey")
        status = result.get("correctedPoseStatus")
        # joint 부재 = canonical key 를 구성할 수 없음 → 404 (추측 서명 차단).
        expected = (
            f"results/{uid}/{analysis_id}/corrected_pose_{joint}.png"
            if isinstance(joint, str) and joint
            else None
        )
        ext = "png"
    else:
        stored = result.get("rotationVideoKey")
        status = result.get("rotationStatus")
        expected = f"results/{uid}/{analysis_id}/rotation.mp4"
        ext = "mp4"

    guards_ok = (
        status == models.VISUAL_STATUS_DONE  # failed/pending/부재 = stale key 여도 404
        and expected is not None
        and isinstance(stored, str)
        and stored == expected  # exact equality — prefix/basename 부분일치 불가
    )
    if not guards_ok:
        return responses.error("not_found", "시각 교정물을 찾을 수 없어요.", status=404)

    url = _sign_get(expected, expires=_ASSET_EXPIRES, content_type=_ASSET_CONTENT_TYPE[ext])
    if url is None:
        return responses.error("server_error", "서명 실패", status=500)

    log.info("playback-url 발급(asset) uid=%s analysis_id=%s asset=%s", uid, analysis_id, asset)
    return responses.ok({"playbackUrl": url, "expiresInSec": _ASSET_EXPIRES})


def _handle_coach_audio(uid: str, analysis_id: str, record_id) -> dict:  # noqa: ANN001
    """coachAudio asset 재서명 (Phase 32 Plan 32-16, D-18 — contract.md §12.7 / H-02).

    _handle_asset 과 동일 규율: 클라이언트는 recordId 만 지정하고 key 는 절대
    보내지 않는다. 서버가 canonical key 를 **구성**(s3keys.build_coach_audio_key —
    저장 측과 단일 출처)하고 result.coachAudio.items 중 같은 recordId 항목의 저장
    key 와 **전체 문자열 exact 비교** 후에만 서명한다 (prefix/basename 부분일치
    불가 — stale key·타 객체 열람 차단, M2-01 선례). uid 는 토큰 유래 — 타 uid 의
    recordId 로 구성한 canonical key 는 본인 doc 의 저장 key 와 일치할 수 없다.

    가드 위반은 전부 동일 404 — 어느 단계에서 걸렸는지 응답으로 구분되지 않는다.
    """
    if not isinstance(record_id, str) or not _COACH_AUDIO_RECORD_ID_RE.match(record_id):
        return responses.error("bad_request", "recordId 형식 오류", status=400)

    doc = firestore_admin.get_analysis(uid, analysis_id) or {}
    result = doc.get("result")
    result = result if isinstance(result, dict) else {}
    coach_audio = result.get("coachAudio")
    coach_audio = coach_audio if isinstance(coach_audio, dict) else {}
    status = coach_audio.get("status")
    items = coach_audio.get("items")
    items = items if isinstance(items, list) else []

    expected = build_coach_audio_key(uid, analysis_id, record_id)
    stored = next(
        (
            it.get("key")
            for it in items
            if isinstance(it, dict) and it.get("recordId") == record_id
        ),
        None,
    )
    guards_ok = (
        status == models.COACH_AUDIO_STATUS_DONE  # failed/부재 = stale key 여도 404
        and isinstance(stored, str)
        and stored == expected  # exact equality — 서버 구성 canonical 만 서명
    )
    if not guards_ok:
        return responses.error("not_found", "코칭 오디오를 찾을 수 없어요.", status=404)

    url = _sign_get(expected, expires=_ASSET_EXPIRES, content_type=_ASSET_CONTENT_TYPE["mp3"])
    if url is None:
        return responses.error("server_error", "서명 실패", status=500)

    log.info(
        "playback-url 발급(coachAudio) uid=%s analysis_id=%s record_id=%s",
        uid, analysis_id, record_id,
    )
    return responses.ok({"playbackUrl": url, "expiresInSec": _ASSET_EXPIRES})


def _handle_rendered_compare(uid: str, analysis_id: str) -> dict:
    """renderedCompare asset 재서명 (Phase 35 quick-260808-jix — contract.md §12.9 / H-02).

    _handle_asset(:83) 규율 복제: 클라이언트는 asset 종류만 지정하고 key 는 절대
    보내지 않는다. 서버가 canonical key 를 **구성**(s3keys.build_rendered_compare_key
    — 저장 측 pipeline 과 단일 출처)하고 doc `result.renderedCompare.status == 'done'`
    + 저장 key **전체 문자열 exact 비교** 후에만 서명한다 (M2-01 — 생성 실패로
    failed 로 돌아간 뒤 남은 stale key 차단). uid 는 토큰 유래 — 타 uid 객체는
    canonical 구성 자체가 불일치라 서명 불가 (T-35J-01).

    **V-0 규율** — 존재 확인 없는 추측 서명 금지: done + exact 이중 가드가 그
    구현이다 (260806-sjt 선례 — done 은 리그 ALL PASS 업로드 완료에만 부착되므로
    가드 통과 = 객체 실존).

    가드 위반은 전부 동일 404 — 어느 단계에서 걸렸는지 응답으로 구분되지 않는다.
    """
    doc = firestore_admin.get_analysis(uid, analysis_id) or {}
    result = doc.get("result")
    result = result if isinstance(result, dict) else {}
    rendered = result.get("renderedCompare")
    rendered = rendered if isinstance(rendered, dict) else {}
    status = rendered.get("status")
    stored = rendered.get("key")

    expected = build_rendered_compare_key(uid, analysis_id)
    guards_ok = (
        status == models.RENDERED_COMPARE_STATUS_DONE  # failed/부재 = stale key 여도 404
        and isinstance(stored, str)
        and stored == expected  # exact equality — prefix/basename 부분일치 불가
    )
    if not guards_ok:
        return responses.error("not_found", "비교 영상을 찾을 수 없어요.", status=404)

    url = _sign_get(expected, expires=_ASSET_EXPIRES, content_type=_ASSET_CONTENT_TYPE["mp4"])
    if url is None:
        return responses.error("server_error", "서명 실패", status=500)

    log.info(
        "playback-url 발급(renderedCompare) uid=%s analysis_id=%s", uid, analysis_id
    )
    return responses.ok({"playbackUrl": url, "expiresInSec": _ASSET_EXPIRES})


def _handle_fault_zoom(uid: str, analysis_id: str) -> dict:
    """faultZoom asset 배치 재서명 (quick-260824-q6p — contract.md 'faultZoom' 절 / H-02).

    _handle_coach_audio/_handle_rendered_compare 규율 복제: 클라이언트는 asset
    종류만 지정하고 key 는 절대 보내지 않는다(H-05). 서버가 item 별 canonical
    key 를 **구성**(s3keys.build_fault_zoom_key — 저장 측 pipeline
    _fault_zoom_upload_items 와 단일 출처)하고 doc
    `result.faultZoomStatus == 'done'` + 저장 key **전체 문자열 exact 비교**
    후에만 서명한다 (M2-01 — 생성 실패 뒤 남은 stale key 차단).

    소급(legacy doc): imageKey 부재 item 은 저장 imageUrl 에서 key 를 **서버가**
    파싱(parse_result_key_from_presigned_url — 후보 추출 전용, 출력 비신뢰)해
    canonical 과 exact 비교한다 (T-q6p-03). 백필 0 — 클라이언트 URL 파싱 0.
    uid 는 토큰 유래 — 타 uid 키는 canonical 구성 자체가 불일치라 서명 불가
    (T-q6p-01).

    가드 위반(status 비-done / 파싱 실패 / 전 item 불일치 = 서명 0건)은 전부
    동일 404 — 어느 단계에서 걸렸는지 응답으로 구분되지 않는다 (T-q6p-02).
    """
    doc = firestore_admin.get_analysis(uid, analysis_id) or {}
    result = doc.get("result")
    result = result if isinstance(result, dict) else {}
    if result.get("faultZoomStatus") != models.FAULT_ZOOM_STATUS_DONE:
        return responses.error(
            "not_found", "확대 비교 이미지를 찾을 수 없어요.", status=404
        )

    comparisons = result.get("faultZoomComparisons")
    comparisons = comparisons if isinstance(comparisons, list) else []
    out: list[dict] = []
    for item in comparisons:
        if not isinstance(item, dict):
            continue
        joint = item.get("joint")
        if not isinstance(joint, str) or not joint:
            continue
        criterion = item.get("criterion")
        key_base = criterion if isinstance(criterion, str) and criterion else joint
        canonical = build_fault_zoom_key(
            uid, analysis_id, item.get("tier"), key_base
        )
        stored = item.get("imageKey")
        if not (isinstance(stored, str) and stored):
            # 소급 경로 — imageKey 없는 legacy doc 은 저장 imageUrl 파싱.
            stored = parse_result_key_from_presigned_url(item.get("imageUrl"))
        if stored != canonical:
            continue  # exact 불일치 — stale/cross-uid/오염 item 은 서명 제외.
        url = _sign_get(
            canonical, expires=_ASSET_EXPIRES, content_type=_ASSET_CONTENT_TYPE["png"]
        )
        if url is None:
            continue
        entry: dict = {"joint": joint, "playbackUrl": url}
        # 앱 join 키 재료 echo — 서버 echo 필드 == 앱 zoomCardKey 입력
        # (tier×(criterion|joint) 유일성 축, app/src/lib/faultZoomUrls.ts
        # zoomCardKey lockstep — doc item 과 echo item 에 같은 함수 적용).
        if isinstance(item.get("tier"), str):
            entry["tier"] = item["tier"]
        if isinstance(criterion, str):
            entry["criterion"] = criterion
        out.append(entry)

    if not out:
        return responses.error(
            "not_found", "확대 비교 이미지를 찾을 수 없어요.", status=404
        )

    log.info(
        "playback-url 발급(faultZoom) uid=%s analysis_id=%s items=%d",
        uid, analysis_id, len(out),
    )
    return responses.ok({"items": out, "expiresInSec": _ASSET_EXPIRES})


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
    asset = body.get("asset")

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
    # analysisId 정합 (uuid hex 32자) — path injection 방지. 공유 validator (L-03).
    if not validate_analysis_id_format(analysis_id):
        return responses.error("bad_request", "analysisId 형식 오류", status=400)

    # Phase 31 asset 확장 — 미지정이면 아래 기존 경로가 바이트 동일하게 동작한다.
    # (검증 순서를 기존 그대로 두어 asset 미지정 요청의 응답이 1바이트도 안 바뀌게 한다.)
    if asset is not None:
        # Phase 32 (Plan 32-16, D-18) — coachAudio 는 visual job 이 아니라 별도
        # 분기 (VISUAL_JOB_KINDS 무접촉 — 기존 asset 종류의 응답 바이트 불변).
        if asset == models.PLAYBACK_ASSET_COACH_AUDIO:
            return _handle_coach_audio(uid, analysis_id, body.get("recordId"))
        # Phase 35 (quick-260808-jix) — renderedCompare 도 visual job 이 아니라
        # 별도 분기 (VISUAL_JOB_KINDS 무접촉 — 기존 asset 종류의 응답 바이트 불변).
        if asset == models.PLAYBACK_ASSET_RENDERED_COMPARE:
            return _handle_rendered_compare(uid, analysis_id)
        # quick-260824-q6p — faultZoom 도 visual job 이 아니라 별도 분기
        # (VISUAL_JOB_KINDS 무접촉 — 기존 asset 종류의 응답 바이트 불변).
        if asset == models.PLAYBACK_ASSET_FAULT_ZOOM:
            return _handle_fault_zoom(uid, analysis_id)
        if asset not in models.VISUAL_JOB_KINDS:
            return responses.error(
                "bad_request", f"asset 은 {list(models.VISUAL_JOB_KINDS)} 중 하나여야 합니다", status=400
            )
        return _handle_asset(uid, analysis_id, asset)

    # 3. presigned GET (uid 가 token 박제 — caller 가 자기 영상만 fetch)
    key = build_upload_key(uid, analysis_id, ext)
    url = _sign_get(key)
    if url is None:
        return responses.error("server_error", "서명 실패", status=500)

    log.info("playback-url 발급 uid=%s analysis_id=%s ext=%s", uid, analysis_id, ext)
    return responses.ok({"playbackUrl": url, "expiresInSec": _PLAYBACK_EXPIRES})
