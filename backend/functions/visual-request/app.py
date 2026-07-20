"""POST /visual/rotation — 카메라앵글 회전 참고 영상 온디맨드 생성 요청 (D-06).

contract.md "POST /visual/rotation" 절. 건당 수분·과금이라 자동 생성하지 않는다 —
버튼 → 백그라운드 생성 → 카드 갱신.

**이 함수가 하는 write 는 reserve_visual_job 단 하나다.** 표시 상태 'pending' 도,
초기 outbox(nextAction='create'/dispatchState='pending'/outboxSeq=1)도 전부 그
transaction 안에서 기록된다 (3차 리뷰 B3-03). 여기서 pending 을 따로 쓰면 SQS send
성공 후 pending write 가 유실되거나, 늦은 pending 이 이미 terminal 이 된 상태를
덮어쓰는 창이 생긴다.

**SQS send 는 best-effort 다** (H3-09). send 가 실패해도 500 이 아니라 202 를 준다 —
dispatchState='pending' 이 durable 하게 남아 VisualDispatchFunction 이 재발행하기
때문이다. 여기서 500 을 주면 사용자는 quota 를 소모한 채 실패를 보고, 재요청은
기존 job 을 만나 no-op 이 되어 영영 생성되지 않는다.

금지: 분석 문서 직접 수정(표시 상태는 reserve transaction 소유) / 서명 URL 로깅 /
DashScope 직접 호출(생성 주체는 worker).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3

from sunity_shared import firestore_admin, models, responses
from sunity_shared.auth import AuthError, verify_request
from sunity_shared.validation import validate_analysis_id_format

log = logging.getLogger()
log.setLevel(logging.INFO)

# 진행 중 재요청 dedupe 창. 전용 timestamp(rotationUpdatedAtMs)만 본다 — 공용
# updatedAt 은 다른 경로가 건드리므로 dedupe 기준이 될 수 없다 (리뷰 H-06).
_DEDUPE_WINDOW_MS = 20 * 60 * 1000

# KST(UTC+9) 자정 리셋 (contract.md M-06). 파일럿 사용자가 전원 한국이라 UTC 자정
# 리셋은 한국 시간 오전 9시에 한도가 풀리는 혼란을 준다.
_KST = timezone(timedelta(hours=9))

# 이미 진행 중인 job 상태 — 재요청은 no-op 202 (중복 과금 0).
_IN_PROGRESS_STATES = ("creating", "polling", "retry_ready", "fetching")

_SQS = None


def _sqs():
    global _SQS
    if _SQS is None:
        _SQS = boto3.client("sqs")
    return _SQS


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


def _kst_date_key(now_ms: int) -> str:
    """KST 기준 날짜 키 (visualQuota 집계 단위)."""
    return datetime.fromtimestamp(now_ms / 1000, tz=_KST).strftime("%Y-%m-%d")


def _parse_limit(name: str) -> int:
    """한도 env fail-closed 파싱 (리뷰 M-06).

    파싱 불가/음수/부재는 **0** 이다 — 전부 429. 여기서 "안전한 기본값"으로 폴백하면
    오타 하나로 과금 상한이 조용히 사라진다. 한도를 못 읽는 상태는 생성을 막는 쪽이
    맞다(사용자는 재시도할 수 있지만, 소진된 크레딧은 못 되돌린다).
    """
    raw = os.environ.get(name)
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        log.error("한도 env 파싱 실패 — fail-closed(0) name=%s", name)
        return 0
    return value if value >= 0 else 0


def _enabled() -> bool:
    return os.environ.get("VISUAL_JOBS_ENABLED") == "true"


def _dispatch(job: dict) -> None:
    """best-effort SQS 발행 + 성공 시에만 outbox CAS (B4-01).

    실패해도 예외를 올리지 않는다 — dispatchState 가 'pending' 으로 남아
    VisualDispatchFunction 이 복구한다 (H3-09).
    """
    queue_url = os.environ.get("VISUAL_QUEUE_URL")
    if not queue_url:
        log.error("VISUAL_QUEUE_URL 미설정 — dispatcher 복구에 위임")
        return

    job_id = models.visual_job_id(
        job.get("uid"), job.get("analysisId"), models.VISUAL_KIND_ROTATION
    )
    action = job.get("nextAction") or "create"
    outbox_seq = int(job.get("outboxSeq") or 0)
    generation = int(job.get("generation") or 0)
    try:
        _sqs().send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(
                {
                    "jobId": job_id,
                    "generation": generation,
                    "action": action,
                    "outboxSeq": outbox_seq,
                }
            ),
        )
    except Exception:  # noqa: BLE001 - dispatcher 가 재발행한다
        log.warning("visual-request send 실패 job_id=%s — outbox pending 유지", job_id)
        return

    firestore_admin.mark_visual_job_dispatched(
        job_id,
        expect_action=action,
        expect_outbox_seq=outbox_seq,
        expect_generation=generation,
    )


def lambda_handler(event: dict, _context) -> dict:
    # 1. feature flag — 조용한 폴백 (D-08). 앱은 에러를 띄우지 않고 버튼을 비활성화.
    if not _enabled():
        return responses.error("feature_disabled", "아직 사용할 수 없는 기능이에요.", status=503)

    # 2. Firebase Auth
    try:
        uid = verify_request(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)

    # 3. 입력 검증 (공유 validator — L-03)
    body = responses.parse_json_body(event)
    analysis_id = body.get("analysisId", "")
    if not validate_analysis_id_format(analysis_id):
        return responses.error("bad_request", "analysisId 형식 오류", status=400)

    # 4. 존재·소유·상태 가드 합산 단일 404 — 타인 analysisId 존재 여부를 떠보는
    #    경로가 없다 (playback-url guards_ok 선례).
    doc = firestore_admin.get_analysis(uid, analysis_id)
    result = (doc or {}).get("result")
    result = result if isinstance(result, dict) else {}
    if doc is None or doc.get("status") != "done":
        return responses.error("not_found", "분석 결과를 찾을 수 없어요.", status=404)

    now_ms = _now_ms()
    rotation_status = result.get("rotationStatus")

    # 5. 이미 완료 — 멱등 200. URL 은 담지 않는다(표시 URL 은 playback-url asset).
    if rotation_status == models.VISUAL_STATUS_DONE:
        return responses.ok({"rotationStatus": models.VISUAL_STATUS_DONE})

    # 6. 진행 중 재요청 dedupe — SQS 미발행. 전용 timestamp 만 본다 (H-06).
    if rotation_status == models.VISUAL_STATUS_PENDING:
        updated = int(result.get("rotationUpdatedAtMs") or 0)
        if now_ms - updated < _DEDUPE_WINDOW_MS:
            return responses.ok({"rotationStatus": models.VISUAL_STATUS_PENDING}, status=202)

    # 7. 한도 (KST 자정 리셋, fail-closed)
    date_key = _kst_date_key(now_ms)
    user_limit = _parse_limit("ROTATION_DAILY_LIMIT")
    global_limit = _parse_limit("ROTATION_GLOBAL_DAILY_LIMIT")

    # 8. 원자 예약 — job + 표시 pending + 초기 outbox 가 한 transaction (B3-03).
    #    rotation 은 임시 입력이 없다(회전은 결과 영상만 만든다) — correctedPose 의
    #    reservation/inputSealed 계약은 여기 해당 없음.
    res = firestore_admin.reserve_visual_job(
        uid,
        analysis_id,
        models.VISUAL_KIND_ROTATION,
        date_key=date_key,
        user_limit=user_limit,
        global_limit=global_limit,
        allow_retry_failed=True,
        now_ms=now_ms,
    )

    if res.get("reason") == "daily_limit":
        return responses.error("daily_limit", "오늘 생성 한도를 다 썼어요.", status=429)
    if res.get("reason") is not None:
        # analysis_missing 등 — 가드와 같은 단일 404 로 합산.
        return responses.error("not_found", "분석 결과를 찾을 수 없어요.", status=404)

    job = res.get("job") or {}
    created = bool(res.get("created"))

    # 9. best-effort dispatch. 신규 예약이거나, 기존 job 의 outbox 가 아직 pending
    #    (= 이전 send 유실) 이면 재발행한다.
    if created or job.get("dispatchState") == "pending":
        _dispatch(job)
    elif job.get("state") in _IN_PROGRESS_STATES:
        # 진행 중 — 중복 발행 0 (worker 가 이미 소비 중).
        log.info("rotation 진행 중 no-op uid=%s analysis_id=%s state=%s", uid, analysis_id, job.get("state"))

    log.info(
        "visual-request 접수 uid=%s analysis_id=%s created=%s date_key=%s",
        uid,
        analysis_id,
        created,
        date_key,
    )
    return responses.ok({"rotationStatus": models.VISUAL_STATUS_PENDING}, status=202)
