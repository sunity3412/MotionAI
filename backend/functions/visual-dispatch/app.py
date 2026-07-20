"""visual dispatcher — durable outbox 발행 + privacy janitor. 담당 플랜 31-09.

**별도 Lambda 인 이유** (H3-09 + T-31-58): 복구 경로가 worker 와 같은 함수/동시성을
공유하면, worker 가 backlog 로 concurrency 를 다 먹었을 때 복구가 굶는다. 정확히
복구가 필요한 순간에 복구가 멈추는 구조다. reserved concurrency 1 + EventBridge
rate(1분) 로 분리한다.

두 가지 일을 한다:

  (1) **outbox 발행** — `list_dispatch_pending` 이 돌려주는 두 종류를 발행한다.
      (a) dispatchState=='pending' + due — CAS 는 성공했는데 SQS send 가 유실된 경우.
      (b) dispatchState=='sent' 인데 same-seq claim 이 만료된 경우 (6차 H6-01) —
          **claim 직후 crash 의 유일한 복구 주체**다. "재전달 no-op 멱등" 은 복구가
          아니다. 아무도 재전달을 만들어주지 않기 때문이다.

  (2) **privacy janitor** — 만료 reservation / orphan 의 임시 생체 프레임을 회수한다.
      삭제는 항상 3단이다: claim CAS → `claim_key_for_delete`(자기 ref 소비 + live
      ref 0 → deleting fence) → **외부 delete 직전** `commit_key_delete(token)` 재검증.
      3단이 다 필요한 이유는 11차 B11-01 이다: lease 만료 뒤 되살아난 이전 claimant
      의 늦은 delete 를 lease 길이로는 막을 수 없고, generation fencing token 비교만이
      막는다. job ref 는 만료되지 않으므로(B11-04) 살아있는 job 의 입력은 절대
      삭제되지 않는다.

금지: fail_analysis / 사용자 문서 직접 수정 / 서명 URL 로깅.
"""

from __future__ import annotations

import json
import logging
import os
import random

import boto3

from sunity_shared import firestore_admin, models

log = logging.getLogger()
log.setLevel(logging.INFO)

METRIC_NAMESPACE = "SunityVisual"

DISPATCH_LIMIT = 20
JANITOR_LIMIT = 20
ORPHAN_BACKOFF_MS = 600_000

_SQS = None
_S3 = None


def _sqs():
    global _SQS
    if _SQS is None:
        _SQS = boto3.client("sqs")
    return _SQS


def _s3():
    global _S3
    if _S3 is None:
        _S3 = boto3.client("s3")
    return _S3


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


def _owner() -> str:
    return f"janitor-{random.getrandbits(48):012x}"


def _put_metric(name: str, value: float = 1.0) -> None:
    try:
        boto3.client("cloudwatch").put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[{"MetricName": name, "Value": float(value)}],
        )
    except Exception:  # noqa: BLE001 - 관측 실패가 복구를 막으면 안 된다
        log.warning("metric put failed metric=%s", name)


# ── (1) outbox 발행 ─────────────────────────────────────────────────────


def dispatch_pending(now_ms: int) -> dict:
    queue_url = os.environ.get("VISUAL_QUEUE_URL")
    if not queue_url:
        log.error("VISUAL_QUEUE_URL 미설정 — 발행 불가")
        return {"sent": 0, "skipped": 0}

    res = firestore_admin.list_dispatch_pending(now_ms, limit=DISPATCH_LIMIT)
    sent = skipped = 0
    for item in res.get("items") or []:
        action = item.get("nextAction")
        if not action or action not in models.VISUAL_NEXT_ACTIONS:
            # creating 항목은 outbox 를 기록하지 않으므로 여기 없는 게 정상이다.
            # 혹시 들어와도 action:null 메시지를 만들어 DLQ 를 오염시키지 않는다.
            skipped += 1
            continue
        job_id = item["jobId"]
        try:
            _sqs().send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(
                    {
                        "jobId": job_id,
                        "generation": int(item.get("generation") or 0),
                        "action": action,
                        "outboxSeq": int(item.get("outboxSeq") or 0),
                    }
                ),
            )
        except Exception:  # noqa: BLE001 - 다음 순회가 다시 집는다
            log.warning("dispatch send failed job_id=%s", job_id)
            continue
        firestore_admin.mark_visual_job_dispatched(
            job_id,
            expect_action=action,
            expect_outbox_seq=int(item.get("outboxSeq") or 0),
            expect_generation=int(item.get("generation") or 0),
        )
        sent += 1

    # M6-01: 이 값은 **스캔 window 안** due 항목의 최고 경과다(전체 backlog 최고령이
    # 아니다). truncated 와 함께 봐야 알람 해석이 맞는다.
    _put_metric("ScannedOutboxMaxAgeMs", float(res.get("scanned_outbox_max_age_ms") or 0))
    if res.get("truncated"):
        _put_metric("OutboxScanTruncated", 1.0)
    return {"sent": sent, "skipped": skipped}


# ── (2) privacy janitor ─────────────────────────────────────────────────


def _delete_key_with_fence(bucket: str, key: str, *, deleting_ref: str, owner: str, now_ms: int) -> bool:
    """claim → commit 재검증 → delete → HEAD404 확인. 한 단계라도 실패하면 False.

    `commit_key_delete` 를 **DeleteObject 직전**에 두는 것이 핵심이다 (B11-01).
    claim 시점에만 검사하면 그 사이 lease 가 만료되고 다른 janitor 가 회수한 뒤에
    이 호출이 살아 돌아와 새 입력을 지울 수 있다.
    """
    token = firestore_admin.claim_key_for_delete(
        bucket,
        key,
        deleting_ref=deleting_ref,
        owner=owner,
        lease_ms=models.VISUAL_OBJECT_DELETE_LEASE_MS,
        now_ms=now_ms,
    )
    if token is None:
        # 다른 live ref 가 있다(=살아있는 job 이 이 입력을 쓰고 있다). 삭제 금지.
        return False
    if not firestore_admin.commit_key_delete(bucket, key, token=token, now_ms=_now_ms()):
        log.warning("delete fence 재검증 실패 — 늦은 claimant 차단 key_ref=%s", deleting_ref)
        return False
    try:
        _s3().delete_object(Bucket=bucket, Key=key)
    except Exception:  # noqa: BLE001
        log.warning("janitor delete failed ref=%s", deleting_ref)
        return False
    return True


def sweep_reservations(now_ms: int, *, limit: int = JANITOR_LIMIT) -> dict:
    """만료 reservation 회수. bounded cursor 순환 (H8-01)."""
    owner = _owner()
    deleted = failed = 0
    open_count = 0
    oldest_age = 0

    for job_id, reservation_id, data in _scan_reservations(limit):
        open_count += 1
        oldest_age = max(oldest_age, now_ms - int(data.get("createdAtMs") or now_ms))
        if not firestore_admin.claim_reservation_for_janitor(
            job_id, reservation_id, owner=owner, now_ms=now_ms
        ):
            continue
        bucket = data.get("bucket")
        # B9-03: expectedKeys ∪ createdKeys. record 직전 crash 로 createdKeys 에만
        # 있는 객체가 생길 수 있어 합집합이어야 전부 회수된다.
        keys = firestore_admin.reservation_keys(data)
        ok = True
        for key in keys:
            if not _delete_key_with_fence(
                bucket, key, deleting_ref=reservation_id, owner=owner, now_ms=now_ms
            ):
                ok = False
                firestore_admin.upsert_visual_orphan(
                    bucket, key, now_ms=now_ms, reason="reservation_sweep_failed"
                )
        if ok:
            firestore_admin.close_reservation(
                job_id, reservation_id, owner=owner, now_ms=now_ms
            )
            deleted += len(keys)
        else:
            failed += 1

    _put_metric("VisualReservationOpenCount", float(open_count))
    _put_metric("VisualReservationOldestAgeMs", float(oldest_age))
    _put_metric("VisualReservationSweepDeleted", float(deleted))
    if failed:
        _put_metric("VisualReservationSweepFailed", float(failed))
    return {"deleted": deleted, "failed": failed, "open": open_count}


def _scan_by_state(collection: str, state: str, cursor_path: str, limit: int) -> list:
    """durable cursor 순환으로 한 state 를 bounded 열거 (H8-01).

    등가 필터 1개 + __name__ 정렬만 쓴다 — 등가+range 복합은 composite index 를
    요구해 운영에서 FAILED_PRECONDITION 으로 죽는다. cursor 로 이어 스캔하고 끝에서
    wrap 하므로 limit 을 넘는 backlog 도 여러 호출에 걸쳐 전량 처리된다.
    """
    last_id = (firestore_admin._snap_dict(firestore_admin._doc(cursor_path).get()) or {}).get(
        "lastId"
    )

    def _query(start_after):
        q = firestore_admin._collection(collection).where(
            filter=firestore_admin._field_filter("state", "==", state)
        )
        q = q.order_by("__name__")
        if start_after:
            q = firestore_admin._query_start_after_name(q, collection, start_after)
        return q.limit(limit)

    rows = list(_query(last_id).stream())
    if not rows and last_id:
        rows = list(_query(None).stream())  # wrap
    firestore_admin._doc(cursor_path).set({"lastId": rows[-1].id if rows else None})
    return rows


# reservation janitor 가 봐야 하는 state 는 **둘**이다 (9차 B9-01):
#   open                 — TTL 만료된 미사용 reservation
#   claimed_by_janitor   — 이전 janitor 가 claim 직후 crash 한 것. 이걸 안 훑으면
#                          claim 된 순간 스캔 대상에서 사라져 그 임시 생체 프레임이
#                          영원히 회수되지 않는다.
_RESERVATION_SWEEP_STATES = ("open", "claimed_by_janitor")


def _scan_reservations(limit: int):
    collection = "visualInputReservations"
    out = []
    for state in _RESERVATION_SWEEP_STATES:
        cursor_path = f"{models.visual_reservation_cursor_doc_path()}_{state}"
        for snap in _scan_by_state(collection, state, cursor_path, limit):
            data = snap.to_dict()
            job_id, _, reservation_id = snap.id.partition("_")
            if data.get("jobId"):
                job_id = data["jobId"]
            if data.get("reservationId"):
                reservation_id = data["reservationId"]
            out.append((job_id, reservation_id, data))
    return out


def sweep_orphans(now_ms: int, *, limit: int = JANITOR_LIMIT) -> dict:
    """보상 delete 실패분 재시도. 실패해도 '아무도 모르는 PII' 를 만들지 않는다."""
    owner = _owner()
    deleted = failed = 0
    open_count = 0
    oldest_age = 0

    for orphan_id, data in _scan_orphans(limit):
        open_count += 1
        oldest_age = max(oldest_age, now_ms - int(data.get("createdAtMs") or now_ms))
        claimed = firestore_admin.claim_visual_orphan(orphan_id, owner=owner, now_ms=now_ms)
        if claimed is None:
            continue
        bucket, key = claimed.get("bucket"), claimed.get("key")
        if _delete_key_with_fence(
            bucket, key, deleting_ref=orphan_id, owner=owner, now_ms=now_ms
        ):
            firestore_admin.close_visual_orphan(orphan_id, now_ms=now_ms)
            deleted += 1
        else:
            failed += 1
            firestore_admin.bump_visual_orphan(
                orphan_id,
                next_retry_at_ms=now_ms + ORPHAN_BACKOFF_MS,
                last_error="delete_or_fence_failed",
            )

    _put_metric("VisualOrphanOpenCount", float(open_count))
    _put_metric("VisualOrphanOldestAgeMs", float(oldest_age))
    _put_metric("VisualOrphanSweepDeleted", float(deleted))
    if failed:
        _put_metric("VisualOrphanSweepFailed", float(failed))
    return {"deleted": deleted, "failed": failed, "open": open_count}


# orphan 도 같은 이유로 두 state 를 훑는다 (B9-01): claim 직후 crash 한 'claimed' 를
# 빼면 그 객체가 스캔에서 사라져 영구 잔존한다.
_ORPHAN_SWEEP_STATES = ("open", "claimed")


def _scan_orphans(limit: int):
    collection = "visualOrphans"
    out = []
    for state in _ORPHAN_SWEEP_STATES:
        cursor_path = f"{models.visual_orphan_cursor_doc_path()}_{state}"
        out.extend(
            (snap.id, snap.to_dict())
            for snap in _scan_by_state(collection, state, cursor_path, limit)
        )
    return out


# ── entrypoint ──────────────────────────────────────────────────────────


def lambda_handler(_event=None, _context=None):
    now = _now_ms()
    result = {"dispatch": dispatch_pending(now)}
    # janitor 실패가 outbox 발행을 막으면 안 된다 — 둘은 독립 책임이다.
    try:
        result["reservations"] = sweep_reservations(now)
    except Exception:  # noqa: BLE001
        log.exception("reservation sweep failed")
        _put_metric("VisualReservationSweepFailed", 1.0)
    try:
        result["orphans"] = sweep_orphans(now)
    except Exception:  # noqa: BLE001
        log.exception("orphan sweep failed")
        _put_metric("VisualOrphanSweepFailed", 1.0)
    log.info(
        "visual-dispatch done sent=%s reservations=%s orphans=%s",
        result["dispatch"].get("sent"),
        (result.get("reservations") or {}).get("deleted"),
        (result.get("orphans") or {}).get("deleted"),
    )
    return result
