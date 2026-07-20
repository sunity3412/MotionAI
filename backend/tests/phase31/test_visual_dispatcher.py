"""visual dispatcher — outbox 복구 발행 + privacy janitor delete-fence — 담당 플랜 31-09.

실 Firestore/네트워크/S3 미접촉 — LOCAL ONLY. 공용 스캐폴드(경쟁 transaction·주입
시계)는 backend/tests/phase31/conftest.py 소유.

여기서 검증하는 핵심은 두 가지다:
  (a) worker 가 CAS 직후 crash 했을 때 **누군가는** 다음 action 을 발행한다.
      "재전달 no-op 멱등" 은 복구가 아니다 — 아무도 재전달을 만들어주지 않는다.
  (b) janitor 의 delete 가 살아있는 job 의 입력을 절대 지우지 않고, lease 만료 뒤
      되살아난 이전 claimant 의 늦은 delete 도 통과하지 못한다 (B11-01/B11-04).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_APP = Path(__file__).resolve().parents[2] / "functions" / "visual-dispatch" / "app.py"


def _load():
    if "visual_dispatch_app" in sys.modules:
        return sys.modules["visual_dispatch_app"]
    spec = importlib.util.spec_from_file_location("visual_dispatch_app", _APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules["visual_dispatch_app"] = module
    spec.loader.exec_module(module)
    return module


dispatcher = _load()

UID = "u1"
ANALYSIS_ID = "a1"
BUCKET = "visual-input-bkt"


class FakeSQS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send_message(self, **kw):
        self.sent.append(kw)
        return {"MessageId": "m"}


class FakeS3:
    def __init__(self) -> None:
        self.objects: set[tuple[str, str]] = set()
        self.deleted: list[tuple[str, str]] = []
        self.fail_delete = False

    def delete_object(self, Bucket, Key):  # noqa: N803
        if self.fail_delete:
            raise RuntimeError("delete failed (injected)")
        self.objects.discard((Bucket, Key))
        self.deleted.append((Bucket, Key))


@pytest.fixture
def wired(monkeypatch, fake_firestore, fake_clock):
    monkeypatch.setenv("VISUAL_QUEUE_URL", "https://sqs.local/q")
    sqs, s3 = FakeSQS(), FakeS3()
    monkeypatch.setattr(dispatcher, "_sqs", lambda: sqs)
    monkeypatch.setattr(dispatcher, "_s3", lambda: s3)
    monkeypatch.setattr(dispatcher, "_now_ms", fake_clock)
    metrics: dict = {}
    monkeypatch.setattr(
        dispatcher,
        "_put_metric",
        lambda name, value=1.0: metrics.setdefault(name, []).append(value),
    )
    return {"db": fake_firestore, "clock": fake_clock, "sqs": sqs, "s3": s3, "metrics": metrics}


def seed_job(db, clock, job_id, **overrides):
    from sunity_shared import models

    doc = {
        "uid": UID, "analysisId": ANALYSIS_ID, "kind": "correctedPose",
        "state": "polling", "nextAction": "poll", "dispatchState": "pending",
        "nextDispatchAtMs": clock(), "outboxSeq": 3, "generation": 1,
        "claimedOutboxSeq": 0, "claimState": None, "claimOwner": None,
        "claimLeaseExpiresAt": 0, "taskId": "t1", "updatedAtMs": clock(),
    }
    doc.update(overrides)
    db.store[models.visual_job_doc_path(job_id)] = doc
    return doc


def sent_bodies(sqs):
    return [json.loads(m["MessageBody"]) for m in sqs.sent]


# ═══════════════ 스캐폴드 ═══════════════


def test_scaffold_fake_firestore_alive(fake_firestore):
    """in-memory Firestore seam 이 transaction CAS 를 실제로 검사하는지."""
    from sunity_shared import firestore_admin

    firestore_admin._doc("scaffold/a").set({"n": 1})

    def _bump(tx):
        snap = firestore_admin._doc("scaffold/a").get(transaction=tx)
        tx.update(firestore_admin._doc("scaffold/a"), {"n": snap.to_dict()["n"] + 1})
        return snap.to_dict()["n"]

    firestore_admin._run_in_transaction(_bump)
    assert fake_firestore.store["scaffold/a"]["n"] == 2


# ═══════════════ (1) outbox 발행 ═══════════════


def test_pending_items_published_with_exact_action_and_seq(wired):
    """action/outboxSeq 가 틀리면 worker 가 stale 로 버려 job 이 영구 정지한다."""
    db, clock = wired["db"], wired["clock"]
    seed_job(db, clock, "j-poll", state="polling", nextAction="poll", outboxSeq=3)
    seed_job(db, clock, "j-fetch", state="fetching", nextAction="fetch", outboxSeq=5)
    seed_job(db, clock, "j-retry", state="retry_ready", nextAction="create", outboxSeq=7, taskId=None)

    dispatcher.dispatch_pending(clock())

    bodies = {b["jobId"]: b for b in sent_bodies(wired["sqs"])}
    assert bodies["j-poll"]["action"] == "poll" and bodies["j-poll"]["outboxSeq"] == 3
    assert bodies["j-fetch"]["action"] == "fetch" and bodies["j-fetch"]["outboxSeq"] == 5
    assert bodies["j-retry"]["action"] == "create" and bodies["j-retry"]["outboxSeq"] == 7
    for job_id in ("j-poll", "j-fetch", "j-retry"):
        assert db.store[f"visualJobs/{job_id}"]["dispatchState"] == "sent"


def test_terminal_and_future_due_are_not_published(wired):
    db, clock = wired["db"], wired["clock"]
    seed_job(db, clock, "j-done", state="done", nextAction=None, dispatchState=None)
    seed_job(db, clock, "j-future", nextDispatchAtMs=clock() + 600_000)

    dispatcher.dispatch_pending(clock())

    assert sent_bodies(wired["sqs"]) == []


def test_sent_recovery_only_reissues_same_seq_expired_claims(wired):
    """H6-01 — claim 직후 crash 만 복구한다. 정상 sent 재발행은 0이어야 한다.

    정상 sent 를 재발행하면 유료 action 이 두 번 나간다.
    """
    from sunity_shared import models

    db, clock = wired["db"], wired["clock"]
    # (a) claim 직후 crash: same-seq claim + lease 만료 → 복구 대상.
    seed_job(
        db, clock, "j-crashed", dispatchState="sent", outboxSeq=3,
        claimedOutboxSeq=3, claimState="claimed", claimOwner="dead",
        claimLeaseExpiresAt=clock() - 1,
    )
    # (b) 미claim sent (lease 0) → 아직 아무도 안 집었다. 재발행 0.
    seed_job(db, clock, "j-unclaimed", dispatchState="sent", outboxSeq=3, claimLeaseExpiresAt=0)
    # (c) 구 seq claim → 이전 action 의 흔적. 재발행 0.
    seed_job(
        db, clock, "j-oldseq", dispatchState="sent", outboxSeq=5,
        claimedOutboxSeq=3, claimState="claimed", claimOwner="x",
        claimLeaseExpiresAt=clock() - 1,
    )
    # (d) lease 유효 → 진행 중. 재발행 0.
    seed_job(
        db, clock, "j-active", dispatchState="sent", outboxSeq=3,
        claimedOutboxSeq=3, claimState="claimed", claimOwner="alive",
        claimLeaseExpiresAt=clock() + models.VISUAL_CLAIM_LEASE_MS,
    )

    dispatcher.dispatch_pending(clock())

    ids = [b["jobId"] for b in sent_bodies(wired["sqs"])]
    assert ids == ["j-crashed"], f"복구 대상 오판: {ids}"


def test_null_next_action_is_never_published(wired):
    """creating 항목은 outbox 를 안 남기는 게 정상. 들어와도 action:null 메시지 금지."""
    db, clock = wired["db"], wired["clock"]
    seed_job(db, clock, "j-creating", state="creating", nextAction=None, dispatchState="pending")

    dispatcher.dispatch_pending(clock())

    assert sent_bodies(wired["sqs"]) == []


def test_scan_age_metric_emitted(wired):
    db, clock = wired["db"], wired["clock"]
    seed_job(db, clock, "j1", nextDispatchAtMs=clock() - 120_000)

    dispatcher.dispatch_pending(clock())

    assert wired["metrics"]["ScannedOutboxMaxAgeMs"][0] >= 120_000


def test_dispatch_is_bounded_per_cycle(wired):
    db, clock = wired["db"], wired["clock"]
    for i in range(40):
        seed_job(db, clock, f"j{i:03d}")

    dispatcher.dispatch_pending(clock())

    assert len(wired["sqs"].sent) <= dispatcher.DISPATCH_LIMIT


def test_backlog_drains_across_cycles(wired):
    """H4-08 — cursor 를 스캔 끝까지 밀면 뒤쪽이 영구 starvation 된다."""
    db, clock = wired["db"], wired["clock"]
    for i in range(60):
        seed_job(db, clock, f"j{i:03d}")

    seen = set()
    for _ in range(10):
        wired["sqs"].sent.clear()
        dispatcher.dispatch_pending(clock())
        seen.update(b["jobId"] for b in sent_bodies(wired["sqs"]))

    assert len(seen) == 60, f"drain 미완: {len(seen)}/60"


def test_send_failure_leaves_pending_for_next_cycle(wired, monkeypatch):
    """발행 실패 시 'sent' 로 마킹하면 안 된다 — 그러면 영영 재발행되지 않는다."""
    db, clock = wired["db"], wired["clock"]
    seed_job(db, clock, "j1")

    def _boom(**kw):
        raise RuntimeError("sqs down")

    monkeypatch.setattr(wired["sqs"], "send_message", _boom)
    dispatcher.dispatch_pending(clock())

    assert db.store["visualJobs/j1"]["dispatchState"] == "pending"


def test_worker_crash_after_cas_is_recovered(wired):
    """★ B5-01 — CAS 직후 send 전 crash → dispatcher 가 정확한 다음 action 을 발행한다."""
    db, clock = wired["db"], wired["clock"]
    seed_job(
        db, clock, "j-crash", state="fetching", nextAction="fetch",
        dispatchState="pending", outboxSeq=4, nextDispatchAtMs=clock() - 1,
    )

    dispatcher.dispatch_pending(clock())

    bodies = sent_bodies(wired["sqs"])
    assert len(bodies) == 1
    assert bodies[0]["action"] == "fetch" and bodies[0]["outboxSeq"] == 4
    assert db.store["visualJobs/j-crash"]["dispatchState"] == "sent"


# ═══════════════ (2) privacy janitor delete-fence ═══════════════


def seed_reservation(db, clock, reservation_id, job_id, keys, *, expired=True, state="open"):
    from sunity_shared import models

    path = models.visual_input_reservation_doc_path(job_id, reservation_id)
    db.store[path] = {
        "jobId": job_id,
        "reservationId": reservation_id,
        "bucket": BUCKET,
        "state": state,
        "expectedKeys": list(keys),
        "createdKeys": list(keys),
        "leaseExpiresAt": clock() - 1 if expired else clock() + 600_000,
        "claimLeaseExpiresAt": 0,
        "createdAtMs": clock() - 1000,
    }
    return path


def seed_object(db, clock, key, refs):
    from sunity_shared import models

    path = models.visual_input_object_doc_path(BUCKET, key)
    db.store[path] = {
        "bucket": BUCKET, "key": key, "state": "active", "generation": 1,
        "refs": refs, "updatedAtMs": clock(),
    }
    return path


def test_expired_reservation_input_is_deleted(wired):
    """B10-01 — 만료 reservation 하나만 참조하는 key 는 회수된다."""
    db, clock = wired["db"], wired["clock"]
    key = f"visual-input/{UID}/{ANALYSIS_ID}/x_src.png"
    seed_reservation(db, clock, "r1", "job-1", [key])
    seed_object(db, clock, key, {"r1": {"kind": "reservation", "expireAt": clock() - 1}})
    wired["s3"].objects.add((BUCKET, key))

    dispatcher.sweep_reservations(clock())

    assert (BUCKET, key) in wired["s3"].deleted


def test_live_job_ref_blocks_deletion(wired):
    """B11-04 — job ref 는 만료되지 않는다. 살아있는 job 의 입력을 지우면 안 된다."""
    db, clock = wired["db"], wired["clock"]
    key = f"visual-input/{UID}/{ANALYSIS_ID}/y_src.png"
    seed_reservation(db, clock, "r1", "job-1", [key])
    seed_object(
        db, clock, key,
        {
            "r1": {"kind": "reservation", "expireAt": clock() - 1},
            "job-1": {"kind": "job"},  # expireAt 없음 = 영구 live
        },
    )
    wired["s3"].objects.add((BUCKET, key))

    dispatcher.sweep_reservations(clock())

    assert wired["s3"].deleted == [], "살아있는 job 의 입력을 삭제했다"


def test_late_claimant_cannot_delete_after_lease_expiry(wired):
    """B11-01 — lease 만료 후 되살아난 J1 의 늦은 delete 는 generation 으로 차단된다.

    lease 길이는 보조 방어일 뿐이고 실제 방어는 commit_key_delete 의 fencing token
    재검증이다. producer 는 만료된 deleting 도 회수하지 못한다.
    """
    from sunity_shared import firestore_admin, models

    db, clock = wired["db"], wired["clock"]
    key = f"visual-input/{UID}/{ANALYSIS_ID}/z_src.png"
    seed_object(db, clock, key, {"r1": {"kind": "reservation", "expireAt": clock() - 1}})

    token_j1 = firestore_admin.claim_key_for_delete(
        BUCKET, key, deleting_ref="r1", owner="J1",
        lease_ms=models.VISUAL_OBJECT_DELETE_LEASE_MS, now_ms=clock(),
    )
    assert token_j1 is not None

    clock.advance(models.VISUAL_OBJECT_DELETE_LEASE_MS + 1)
    # producer 는 만료여도 deleting 을 회수하지 않는다.
    assert db.store[models.visual_input_object_doc_path(BUCKET, key)]["state"] == "deleting"

    token_j2 = firestore_admin.claim_key_for_delete(
        BUCKET, key, deleting_ref="r1", owner="J2",
        lease_ms=models.VISUAL_OBJECT_DELETE_LEASE_MS, now_ms=clock(),
    )
    assert token_j2 is not None and token_j2["generation"] > token_j1["generation"]

    assert not firestore_admin.commit_key_delete(BUCKET, key, token=token_j1, now_ms=clock())
    assert firestore_admin.commit_key_delete(BUCKET, key, token=token_j2, now_ms=clock())


def test_commit_is_rechecked_immediately_before_delete(wired):
    """B11-01 — commit_key_delete 는 DeleteObject **직전**에 있어야 한다.

    claim 시점에만 검사하면 그 사이 회수가 일어난 뒤 늦은 delete 가 새 입력을 지운다.
    """
    source = _APP.read_text(encoding="utf-8")
    body = source.split("def _delete_key_with_fence")[1].split("\ndef ")[0]
    commit_at = body.index("commit_key_delete")
    delete_at = body.index("delete_object")
    assert commit_at < delete_at, "commit 재검증이 delete 뒤에 있다"


def test_delete_failure_registers_orphan(wired):
    """실패했지만 아무도 모르는 PII 를 만들지 않는다 — 반드시 orphan 으로 남긴다."""
    db, clock = wired["db"], wired["clock"]
    key = f"visual-input/{UID}/{ANALYSIS_ID}/f_src.png"
    seed_reservation(db, clock, "r1", "job-1", [key])
    seed_object(db, clock, key, {"r1": {"kind": "reservation", "expireAt": clock() - 1}})
    wired["s3"].objects.add((BUCKET, key))
    wired["s3"].fail_delete = True

    dispatcher.sweep_reservations(clock())

    assert [p for p in db.store if p.startswith("visualOrphans/")], "orphan 미기록"


def test_multi_key_reservation_deletes_every_recorded_key(wired):
    """B9-03 — expectedKeys ∪ createdKeys. record 직전 crash 분도 회수돼야 한다."""
    db, clock = wired["db"], wired["clock"]
    keys = [
        f"visual-input/{UID}/{ANALYSIS_ID}/a_src.png",
        f"visual-input/{UID}/{ANALYSIS_ID}/a_trainsrc.png",
    ]
    seed_reservation(db, clock, "r1", "job-1", keys)
    for key in keys:
        seed_object(db, clock, key, {"r1": {"kind": "reservation", "expireAt": clock() - 1}})
        wired["s3"].objects.add((BUCKET, key))

    dispatcher.sweep_reservations(clock())

    assert {k for _b, k in wired["s3"].deleted} == set(keys)


def test_janitor_claim_crash_is_recovered_after_lease(wired):
    """B9-01 — claim 직후 crash 한 reservation 이 방치되면 PII 가 영원히 남는다."""
    db, clock = wired["db"], wired["clock"]
    key = f"visual-input/{UID}/{ANALYSIS_ID}/c_src.png"
    path = seed_reservation(db, clock, "r1", "job-1", [key])
    seed_object(db, clock, key, {"r1": {"kind": "reservation", "expireAt": clock() - 1}})
    wired["s3"].objects.add((BUCKET, key))
    db.store[path].update(
        {"state": "claimed_by_janitor", "claimOwner": "dead", "claimLeaseExpiresAt": clock() - 1}
    )

    dispatcher.sweep_reservations(clock())

    assert (BUCKET, key) in wired["s3"].deleted


def test_unexpired_reservation_is_not_swept(wired):
    """TTL 이 안 지난 reservation 은 정상 producer 의 것이다 — 건드리면 안 된다."""
    db, clock = wired["db"], wired["clock"]
    key = f"visual-input/{UID}/{ANALYSIS_ID}/live_src.png"
    seed_reservation(db, clock, "r1", "job-1", [key], expired=False)
    seed_object(db, clock, key, {"r1": {"kind": "reservation", "expireAt": clock() + 600_000}})
    wired["s3"].objects.add((BUCKET, key))

    dispatcher.sweep_reservations(clock())

    assert wired["s3"].deleted == []


def test_orphan_sweep_deletes_and_closes(wired):
    from sunity_shared import firestore_admin

    db, clock = wired["db"], wired["clock"]
    key = f"visual-input/{UID}/{ANALYSIS_ID}/o_src.png"
    seed_object(db, clock, key, {})
    wired["s3"].objects.add((BUCKET, key))
    orphan_id = firestore_admin.upsert_visual_orphan(BUCKET, key, now_ms=clock(), reason="test")

    dispatcher.sweep_orphans(clock())

    assert (BUCKET, key) in wired["s3"].deleted
    assert db.store[f"visualOrphans/{orphan_id}"]["state"] == "closed"


def test_orphan_claim_crash_is_recovered_after_lease(wired):
    """B9-01 (orphan 판) — claim 된 순간 스캔에서 사라지면 그 객체는 영구 잔존한다.

    reservation 과 같은 함정이라 같은 방식으로 두 state 를 훑는지 고정한다.
    """
    from sunity_shared import firestore_admin

    db, clock = wired["db"], wired["clock"]
    key = f"visual-input/{UID}/{ANALYSIS_ID}/oc_src.png"
    seed_object(db, clock, key, {})
    wired["s3"].objects.add((BUCKET, key))
    orphan_id = firestore_admin.upsert_visual_orphan(BUCKET, key, now_ms=clock(), reason="test")
    db.store[f"visualOrphans/{orphan_id}"].update(
        {"state": "claimed", "claimOwner": "dead", "claimLeaseExpiresAt": clock() - 1}
    )

    dispatcher.sweep_orphans(clock())

    assert (BUCKET, key) in wired["s3"].deleted


def test_orphan_never_deletes_input_of_a_live_job(wired):
    """B11-04 — orphan 경로도 job ref 를 live 로 계산해야 한다."""
    from sunity_shared import firestore_admin

    db, clock = wired["db"], wired["clock"]
    key = f"visual-input/{UID}/{ANALYSIS_ID}/p_src.png"
    seed_object(db, clock, key, {"job-1": {"kind": "job"}})
    wired["s3"].objects.add((BUCKET, key))
    firestore_admin.upsert_visual_orphan(BUCKET, key, now_ms=clock(), reason="test")

    dispatcher.sweep_orphans(clock())

    assert wired["s3"].deleted == []


def test_janitor_metrics_emitted(wired):
    clock = wired["clock"]
    dispatcher.sweep_reservations(clock())
    dispatcher.sweep_orphans(clock())

    for name in (
        "VisualReservationOpenCount", "VisualReservationOldestAgeMs",
        "VisualOrphanOpenCount", "VisualOrphanOldestAgeMs",
    ):
        assert name in wired["metrics"], f"{name} metric 미방출"


def test_janitor_failure_does_not_block_outbox_dispatch(wired, monkeypatch):
    """복구 주체가 부수 작업 때문에 통째로 죽으면 안 된다."""
    db, clock = wired["db"], wired["clock"]
    seed_job(db, clock, "j1")

    def _boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(dispatcher, "sweep_reservations", _boom)
    result = dispatcher.lambda_handler({}, None)

    assert result["dispatch"]["sent"] == 1


def test_dispatcher_source_has_no_banned_symbols():
    """운영 경로 금지 심볼 — 산문(docstring)은 제외하고 코드만 본다."""
    import ast
    import re

    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                body.pop(0)
    code = re.sub(r"#.*", "", ast.unparse(tree))
    for banned in ("fail_analysis", "import requests", "google.genai", "list_object_versions"):
        assert banned not in code
