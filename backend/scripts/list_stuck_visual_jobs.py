#!/usr/bin/env python3
"""운영자용 visual job 조회 + 재구동 + reconciler. 담당 플랜 31-09.

worker/dispatcher 가 자동으로 못 푸는 세 가지가 사람 손을 필요로 한다:

  1. **create_unconfirmed** — creating lease 만료 + taskId 부재. create 가 벤더에
     도달했는지 알 수 없어 자동 재생성이 곧 이중 과금이다 (B2-02). 벤더 콘솔에서
     실제 과금 여부를 확인한 뒤 사람이 판정한다.
  2. **privacyBlocker='cleanup_blocked'** — 임시 생체 프레임이 남았다. terminal 로
     가지 않고 멈춰 있는 상태이며, 원인(권한/버킷 정책)을 고친 뒤 재구동해야 한다.
  3. **job↔analysis 표시 불일치** — 이 스크립트가 `update_analysis_visual` 의
     **유일한 정당 호출자**다 (31-02 계약). production worker 경로는 절대 호출하지
     않으며 31-09 acceptance grep 이 강제한다.

사용:
  python3 backend/scripts/list_stuck_visual_jobs.py --profile sunity-motion
  python3 backend/scripts/list_stuck_visual_jobs.py --redispatch
  python3 backend/scripts/list_stuck_visual_jobs.py --redispatch-cleanup
  python3 backend/scripts/list_stuck_visual_jobs.py --reconcile
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_LAYER = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

from sunity_shared import firestore_admin, models  # noqa: E402

VISUAL_JOBS_COLLECTION = "visualJobs"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _scan_jobs() -> list[tuple[str, dict]]:
    """전체 job 순회. 운영 규모(하루 수백 건)에서 인덱스 없이 충분하다."""
    col = firestore_admin._collection(VISUAL_JOBS_COLLECTION).order_by("__name__")
    return [(snap.id, snap.to_dict()) for snap in col.stream()]


def _age_minutes(job: dict, now_ms: int) -> float:
    return round((now_ms - int(job.get("updatedAtMs") or now_ms)) / 60000.0, 1)


def collect(stale_minutes: int, now_ms: int) -> dict:
    stale_ms = stale_minutes * 60_000
    buckets: dict = {"stale": [], "create_unconfirmed": [], "cleanup_blocked": [], "mismatched": []}

    for job_id, job in _scan_jobs():
        state = job.get("state")
        terminal = state in models.VISUAL_TERMINAL_STATES
        row = {
            "jobId": job_id,
            "kind": job.get("kind"),
            "state": state,
            "dispatchState": job.get("dispatchState"),
            "nextAction": job.get("nextAction"),
            "outboxSeq": job.get("outboxSeq"),
            "generation": job.get("generation"),
            "attempt": job.get("attempt"),
            "failureReason": job.get("failureReason") or job.get("pendingFailureReason"),
            "privacyBlocker": job.get("privacyBlocker"),
            "ageMinutes": _age_minutes(job, now_ms),
            "uid": job.get("uid"),
            "analysisId": job.get("analysisId"),
        }

        if job.get("privacyBlocker") == models.VISUAL_PRIVACY_BLOCKER_CLEANUP:
            buckets["cleanup_blocked"].append(row)
        if (job.get("failureReason") or job.get("pendingFailureReason")) == "create_unconfirmed":
            buckets["create_unconfirmed"].append(row)
        if not terminal and (now_ms - int(job.get("updatedAtMs") or now_ms)) >= stale_ms:
            buckets["stale"].append(row)
        if terminal:
            analysis = firestore_admin.get_analysis(job.get("uid"), job.get("analysisId")) or {}
            shown = (analysis.get("result") or {}).get(f"{job.get('kind')}Status")
            expected = (
                models.VISUAL_STATUS_DONE if state == "done" else models.VISUAL_STATUS_FAILED
            )
            if shown != expected:
                row["shown"] = shown
                row["expected"] = expected
                buckets["mismatched"].append(row)

    return buckets


def collect_privacy(now_ms: int) -> dict:
    """janitor 가 아직 못 치운 reservation/orphan (7차 H7-04 운영 가시성)."""
    out: dict = {"reservations": [], "orphans": []}
    for snap in firestore_admin._collection("visualInputReservations").order_by("__name__").stream():
        data = snap.to_dict()
        if data.get("state") == "closed":
            continue
        out["reservations"].append(
            {
                "id": snap.id,
                "state": data.get("state"),
                "bucket": data.get("bucket"),
                "keys": firestore_admin.reservation_keys(data),
                "expired": int(data.get("leaseExpiresAt") or 0) <= now_ms,
            }
        )
    for snap in firestore_admin._collection("visualOrphans").order_by("__name__").stream():
        data = snap.to_dict()
        if data.get("state") == "closed":
            continue
        out["orphans"].append(
            {
                "id": snap.id,
                "state": data.get("state"),
                "bucket": data.get("bucket"),
                "key": data.get("key"),
                "attempt": data.get("attempt"),
                "lastError": data.get("lastError"),
            }
        )
    return out


def _table(rows: list[dict], columns: tuple[str, ...]) -> str:
    if not rows:
        return "  (없음)"
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in columns}
    header = "  " + " | ".join(c.ljust(widths[c]) for c in columns)
    sep = "  " + "-+-".join("-" * widths[c] for c in columns)
    body = [
        "  " + " | ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns) for r in rows
    ]
    return "\n".join([header, sep, *body])


_COLUMNS = (
    "jobId", "kind", "state", "dispatchState", "nextAction",
    "outboxSeq", "attempt", "failureReason", "privacyBlocker", "ageMinutes",
)


def redispatch(rows: list[dict], queue_url: str, *, action_override: str | None = None) -> int:
    import boto3

    sqs = boto3.client("sqs")
    sent = 0
    for row in rows:
        action = action_override or row.get("nextAction")
        if not action or action not in models.VISUAL_NEXT_ACTIONS:
            print(f"  skip {row['jobId']}: nextAction 없음 (state={row['state']})")
            continue
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(
                {
                    "jobId": row["jobId"],
                    "generation": int(row.get("generation") or 0),
                    "action": action,
                    "outboxSeq": int(row.get("outboxSeq") or 0),
                }
            ),
        )
        sent += 1
        print(f"  재발행 {row['jobId']} action={action} seq={row.get('outboxSeq')}")
    return sent


def reconcile(rows: list[dict]) -> int:
    """terminal job 과 analysis 표시의 불일치를 복구한다.

    이 스크립트가 update_analysis_visual 의 유일한 정당 호출자다 (31-02).
    """
    fixed = 0
    for row in rows:
        firestore_admin.update_analysis_visual(
            row["uid"],
            row["analysisId"],
            kind=row["kind"],
            status=row["expected"],
        )
        fixed += 1
        print(f"  복구 {row['jobId']}: {row.get('shown')} -> {row['expected']}")
    return fixed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="sunity-motion")
    parser.add_argument("--stale-minutes", type=int, default=30)
    parser.add_argument("--redispatch", action="store_true", help="pending 항목 SQS 재발행")
    parser.add_argument(
        "--redispatch-cleanup",
        action="store_true",
        help="cleanup_blocked 항목의 postprocess 를 재발행 (원인 해소 후에 쓸 것)",
    )
    parser.add_argument(
        "--reconcile", action="store_true", help="terminal job ↔ analysis 표시 불일치 복구"
    )
    args = parser.parse_args(argv)

    os.environ.setdefault("AWS_PROFILE", args.profile)
    now = _now_ms()
    buckets = collect(args.stale_minutes, now)
    privacy = collect_privacy(now)

    print(f"\n== nonterminal stale (>{args.stale_minutes}분) ==")
    print(_table(buckets["stale"], _COLUMNS))

    print("\n== 수동 판정 필요 — 중복 과금 회피 (create_unconfirmed) ==")
    print(
        "  create 가 벤더에 도달했는지 알 수 없다. **자동 재생성 금지** — 벤더 콘솔에서\n"
        "  실제 과금/생성 여부를 확인한 뒤에만 사람이 재요청할 것."
    )
    print(_table(buckets["create_unconfirmed"], _COLUMNS))

    print("\n== 임시 생체 프레임 잔존 — cleanup 재구동 필요 (cleanup_blocked) ==")
    print(
        "  이 job 들은 terminal 로 가지 않고 멈춰 있다(의도된 동작). 버킷 권한/정책을\n"
        "  고친 뒤 --redispatch-cleanup 으로 postprocess 를 재발행하면 remainingObject\n"
        "  0 을 재확인한 뒤에만 종결된다."
    )
    print(_table(buckets["cleanup_blocked"], _COLUMNS))
    for row in buckets["cleanup_blocked"]:
        prefix = f"visual-input/{row['uid']}/{row['analysisId']}/"
        print(f"    잔존 prefix: s3://{os.environ.get('VISUAL_INPUT_BUCKET', '?')}/{prefix}")

    print("\n== janitor 미처리 reservation / orphan ==")
    print(_table(privacy["reservations"], ("id", "state", "bucket", "expired")))
    print(_table(privacy["orphans"], ("id", "state", "bucket", "key", "attempt", "lastError")))

    print("\n== terminal job ↔ analysis 표시 불일치 ==")
    print(_table(buckets["mismatched"], ("jobId", "kind", "state", "shown", "expected")))

    queue_url = os.environ.get("VISUAL_QUEUE_URL")
    if args.redispatch or args.redispatch_cleanup:
        if not queue_url:
            print("\nVISUAL_QUEUE_URL 미설정 — 재발행 불가")
            return 1
    if args.redispatch:
        print("\n== 재발행 ==")
        pending = [r for r in buckets["stale"] if r.get("dispatchState") == "pending"]
        print(f"  총 {redispatch(pending, queue_url)}건")
    if args.redispatch_cleanup:
        print("\n== cleanup 재구동 ==")
        print(f"  총 {redispatch(buckets['cleanup_blocked'], queue_url, action_override='postprocess')}건")
    if args.reconcile:
        print("\n== reconcile ==")
        print(f"  총 {reconcile(buckets['mismatched'])}건")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
