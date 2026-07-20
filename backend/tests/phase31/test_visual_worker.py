"""visual worker — claim 4상태 소비 + action 실행 + snapshot-only handoff — 담당 플랜 31-09.

실 Firestore/네트워크/Pod/S3 미접촉 — LOCAL ONLY. 공용 스캐폴드(경쟁 transaction·
주입 시계·DashScope urllib mock)는 backend/tests/phase31/conftest.py 소유.

여기서 검증하는 것은 "함수가 돌아간다" 가 아니라 **crash 가 어디서 나든 유료 외부
호출이 정확히 한 번이고 임시 생체 프레임이 남지 않는다** 는 계약이다.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_APP = (
    Path(__file__).resolve().parents[2] / "functions" / "visual-worker" / "app.py"
)


def _load_worker():
    """하이픈 디렉터리의 Lambda 핸들러를 `visual_worker` 로 적재 (backend 테스트 관례)."""
    if "visual_worker" in sys.modules:
        return sys.modules["visual_worker"]
    spec = importlib.util.spec_from_file_location("visual_worker", _APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules["visual_worker"] = module
    spec.loader.exec_module(module)
    return module


worker = _load_worker()

UID = "u1"
ANALYSIS_ID = "a1"
JOINT = "left_knee"


# ─────────────────────── 공용 fake ───────────────────────


class FakeSQS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.visibility: list[dict] = []
        self.fail_send = False

    def send_message(self, **kw):
        if self.fail_send:
            raise RuntimeError("send failed (injected)")
        self.sent.append(kw)
        return {"MessageId": "m"}

    def change_message_visibility(self, **kw):
        self.visibility.append(kw)


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict] = {}
        self.deleted: list[tuple[str, str]] = []
        self.puts: list[tuple[str, str]] = []
        self.copies: list[tuple[str, str]] = []
        self.delete_errors: list[dict] = []
        self.remaining_after_delete: list[str] | None = None

    # -- 최소 S3 API --
    def generate_presigned_url(self, _op, Params=None, ExpiresIn=None):  # noqa: N803
        return f"https://dashscope-intl.aliyuncs.com/{Params['Bucket']}/{Params['Key']}"

    def head_object(self, Bucket, Key):  # noqa: N803
        entry = self.objects.get((Bucket, Key))
        if entry is None:
            raise _not_found()
        return {"Metadata": entry.get("Metadata", {}), "ContentLength": len(entry["Body"])}

    def get_object(self, Bucket, Key):  # noqa: N803
        entry = self.objects.get((Bucket, Key))
        if entry is None:
            raise _not_found()
        return {"Body": _Streaming(entry["Body"])}

    def put_object(self, Bucket, Key, Body, ContentType=None, Metadata=None):  # noqa: N803
        self.puts.append((Bucket, Key))
        self.objects[(Bucket, Key)] = {"Body": Body, "Metadata": Metadata or {}}

    def copy_object(self, Bucket, Key, CopySource, MetadataDirective=None, Metadata=None, ContentType=None):  # noqa: N803
        self.copies.append((Bucket, Key))
        src = self.objects[(CopySource["Bucket"], CopySource["Key"])]
        assert MetadataDirective == "REPLACE", "H7-08: sha256 metadata 보존에 REPLACE 필수"
        self.objects[(Bucket, Key)] = {"Body": src["Body"], "Metadata": Metadata or {}}

    def upload_file(self, filename, bucket, key, ExtraArgs=None):  # noqa: N803
        with open(filename, "rb") as fh:
            self.objects[(bucket, key)] = {"Body": fh.read(), "Metadata": {}}
        self.puts.append((bucket, key))

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):  # noqa: N803
        keys = sorted(k for (b, k) in self.objects if b == Bucket and k.startswith(Prefix))
        return {"KeyCount": len(keys), "Contents": [{"Key": k} for k in keys], "IsTruncated": False}

    def delete_objects(self, Bucket, Delete):  # noqa: N803
        if self.delete_errors:
            return {"Deleted": [], "Errors": self.delete_errors}
        for obj in Delete["Objects"]:
            self.objects.pop((Bucket, obj["Key"]), None)
            self.deleted.append((Bucket, obj["Key"]))
        return {"Deleted": Delete["Objects"], "Errors": []}

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.objects.pop((Bucket, Key), None)
        self.deleted.append((Bucket, Key))


class _Streaming:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self):
        return self._body


def _not_found():
    class _ClientError(Exception):
        response = {"Error": {"Code": "404"}}

    return _ClientError("not found")


class FakeAdapter:
    """벤더 어댑터 대역. create/poll 호출 횟수가 과금 계약의 관측점이다."""

    def __init__(self) -> None:
        self.create_calls: list[tuple] = []
        self.poll_calls: list[str] = []
        self.create_result = None
        self.poll_results: list = []
        self.create_raises: Exception | None = None

    def create_task(self, url, prompt):
        self.create_calls.append((url, prompt))
        if self.create_raises is not None:
            raise self.create_raises
        return self.create_result

    def poll(self, task_id):
        self.poll_calls.append(task_id)
        if not self.poll_results:
            raise AssertionError("poll 결과 미주입")
        return self.poll_results.pop(0) if len(self.poll_results) > 1 else self.poll_results[0]


# ─────────────────────── fixtures ───────────────────────


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("VISUAL_QUEUE_URL", "https://sqs.local/q")
    monkeypatch.setenv("VISUAL_INPUT_BUCKET", "visual-input-bkt")
    monkeypatch.setenv("VIDEO_BUCKET", "video-bkt")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "k-test")
    monkeypatch.setenv("RUNPOD_ANALYZE_URL", "https://pod.example/analyze")
    monkeypatch.setenv("RUNPOD_AUTH_TOKEN", "t-test")
    # 31-13 채택 임계값. CALIBRATION.json 이 blocked 라 운영값은 아직 없다 —
    # 테스트는 명시 주입하고, **미주입 시 fail-closed** 를 별도 테스트가 검증한다.
    monkeypatch.setenv("DISPLAY_JUDGE_CONFIDENCE", "0.7")
    monkeypatch.setenv("TRAINING_JUDGE_CONFIDENCE", "0.9")
    monkeypatch.setenv("DISPLAY_POSE_TOL_DEG", "12")
    monkeypatch.setenv("TRAINING_POSE_TOL_DEG", "6")
    monkeypatch.setenv("PRESERVE_POSE_TOL_DEG", "15")


@pytest.fixture
def wired(monkeypatch, fake_firestore, fake_clock, env):
    """worker 의 모든 외부 seam 을 대역으로 교체하고 관측 핸들을 돌려준다."""
    sqs, s3, adapter = FakeSQS(), FakeS3(), FakeAdapter()
    monkeypatch.setattr(worker, "_sqs", lambda: sqs)
    monkeypatch.setattr(worker, "_s3", lambda: s3)
    monkeypatch.setattr(worker, "_adapter", lambda _kind: adapter)
    monkeypatch.setattr(worker, "_now_ms", fake_clock)
    monkeypatch.setattr(worker, "_put_metric", lambda *a, **k: None)
    return {
        "db": fake_firestore,
        "clock": fake_clock,
        "sqs": sqs,
        "s3": s3,
        "adapter": adapter,
    }


def _job_id(kind="correctedPose"):
    from sunity_shared import models

    return models.visual_job_id(UID, ANALYSIS_ID, kind)


def seed_job(db, clock, *, kind="correctedPose", **overrides):
    """job + analysis 문서를 reserve 직후 형상으로 심는다."""
    from sunity_shared import models

    job_id = _job_id(kind)
    doc = {
        "uid": UID,
        "analysisId": ANALYSIS_ID,
        "kind": kind,
        "state": "reserved",
        "nextAction": "create",
        "dispatchState": "pending",
        "nextDispatchAtMs": clock(),
        "outboxSeq": 1,
        "claimedOutboxSeq": 0,
        "claimState": None,
        "claimOwner": None,
        "claimLeaseExpiresAt": 0,
        "generation": 1,
        "attempt": 0,
        "retryCount": 0,
        "taskId": None,
        "requestKey": None,
        "leaseOwner": None,
        "leaseExpiresAt": 0,
        "failureReason": None,
        "pendingTerminalState": None,
        "pendingFailureReason": None,
        "pairAttempt": 0,
        "cleanupAttempt": 0,
        "inputSealed": False,
        "privacyBlocker": None,
        "cleanupVerifiedAtMs": 0,
        "requestedAtMs": clock(),
        "updatedAtMs": clock(),
        "quotaDateKey": None,
        "reservationId": None,
    }
    if kind == "correctedPose":
        doc.update(
            {
                "jointKey": JOINT,
                "targetDeg": 175.0,
                "srcKey": f"visual-input/{UID}/{ANALYSIS_ID}/abc123_src.png",
                "sourceHash": "a" * 64,
            }
        )
    else:
        doc["myVideoKey"] = f"uploads/{UID}/{ANALYSIS_ID}.mp4"
    doc.update(overrides)
    db.store[models.visual_job_doc_path(job_id)] = doc
    db.store[models.analysis_doc_path(UID, ANALYSIS_ID)] = {
        # reserve_visual_job 이 job 예약과 같은 transaction 에서 'pending' 을 쓴다 —
        # 그 형상을 그대로 재현해야 "terminal 로 안 갔다" 를 검증할 수 있다.
        "result": {
            f"{kind}Status": models.VISUAL_STATUS_PENDING,
            f"{kind}UpdatedAtMs": clock(),
        },
        "learningOptIn": True,
        "consentCapturedAtMs": clock(),
    }
    return job_id, doc


def read_job(db, job_id):
    from sunity_shared import models

    return db.store[models.visual_job_doc_path(job_id)]


def read_analysis(db):
    from sunity_shared import models

    return db.store[models.analysis_doc_path(UID, ANALYSIS_ID)]


def sqs_event(job_id, *, action, generation=1, outbox_seq=1, message_id="m1"):
    return {
        "Records": [
            {
                "messageId": message_id,
                "receiptHandle": f"rh-{message_id}",
                "body": json.dumps(
                    {
                        "jobId": job_id,
                        "generation": generation,
                        "action": action,
                        "outboxSeq": outbox_seq,
                    }
                ),
            }
        ]
    }


class Ctx:
    def __init__(self, rid="req-1") -> None:
        self.aws_request_id = rid


def _created(task_id="task-1"):
    from sunity_shared.analysis import visual_gen

    return visual_gen.VendorTaskCreated(task_id=task_id)


def _poll(state, **kw):
    from sunity_shared.analysis import visual_gen

    if state == "succeeded":
        kw.setdefault("output_url", "https://dashscope-intl.aliyuncs.com/out.png")
    return visual_gen.VendorPollResult(state=state, **kw)


def worker_code() -> str:
    """docstring/주석을 제거한 **실행 코드만**.

    금지 심볼 검사가 산문까지 훑으면 "이걸 쓰지 말라" 고 적은 주석 자체가 걸린다 —
    그러면 규칙을 문서화할 수 없게 되어 결국 주석이 지워진다. 코드만 본다.
    """
    import ast
    import re

    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                body.pop(0)
    src = ast.unparse(tree)
    return re.sub(r"#.*", "", src)


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


# ═══════════════ 메시지 경계 ═══════════════


def test_malformed_message_goes_to_batch_item_failures(wired):
    """스키마 위반은 재시도해도 같다 — 조용히 삼키지 않고 DLQ 로 보낸다 (M2-02)."""
    event = {"Records": [{"messageId": "bad", "receiptHandle": "r", "body": "{not json"}]}
    out = worker.lambda_handler(event, Ctx())
    assert out["batchItemFailures"] == [{"itemIdentifier": "bad"}]


@pytest.mark.parametrize(
    "body",
    [
        {"jobId": "", "generation": 1, "action": "poll", "outboxSeq": 1},
        {"jobId": "j", "generation": 1, "action": "nope", "outboxSeq": 1},
        {"jobId": "j", "generation": "x", "action": "poll", "outboxSeq": 1},
        {"jobId": "j", "generation": 1, "action": None, "outboxSeq": 1},
    ],
)
def test_schema_violations_rejected(wired, body):
    event = {"Records": [{"messageId": "b", "receiptHandle": "r", "body": json.dumps(body)}]}
    assert worker.lambda_handler(event, Ctx())["batchItemFailures"]


def test_iam_probe_consumes_without_external_calls(wired):
    """31-12 canary — send 권한만 확인한다. 외부 0 + 정상 ACK (H4-02)."""
    event = {
        "Records": [
            {
                "messageId": "p",
                "receiptHandle": "r",
                "body": json.dumps(
                    {"jobId": "j", "generation": 1, "action": "iam_probe", "outboxSeq": 1}
                ),
            }
        ]
    }
    out = worker.lambda_handler(event, Ctx())
    assert out["batchItemFailures"] == []
    assert wired["adapter"].create_calls == [] and wired["adapter"].poll_calls == []


# ═══════════════ B5-01 / B6-01 claim 4상태 ═══════════════


def test_duplicate_delivery_runs_external_call_exactly_once(wired):
    """standard SQS 중복 2건 → claimed 1 + busy 1. 유료 외부 호출은 정확히 1회 (T-31-62)."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3)
    wired["adapter"].poll_results = [_poll("pending")]

    first = worker.lambda_handler(
        sqs_event(job_id, action="poll", outbox_seq=3, message_id="d1"), Ctx("req-a")
    )
    assert first["batchItemFailures"] == []
    assert len(wired["adapter"].poll_calls) == 1

    # 두 번째 전달은 **이전 seq** 라 stale 이다. 같은 seq 의 동시 전달은 아래 테스트가 본다.
    second = worker.lambda_handler(
        sqs_event(job_id, action="poll", outbox_seq=3, message_id="d2"), Ctx("req-b")
    )
    assert second["batchItemFailures"] == []
    assert len(wired["adapter"].poll_calls) == 1, "stale 재전달이 유료 호출을 또 태웠다"


def test_same_seq_active_lease_is_busy_not_acked(wired):
    """same-seq + 유효 lease = busy → change_visibility + batchItemFailures (M6-03).

    정상 ACK 하면 이 action 의 재전달 기회가 사라진다.
    """
    from sunity_shared import firestore_admin, models

    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3)
    # 다른 worker 가 먼저 claim 한 상태를 만든다.
    firestore_admin.claim_visual_job_action(
        job_id, generation=1, action="poll", outbox_seq=3,
        owner="other", lease_ms=models.VISUAL_CLAIM_LEASE_MS, now_ms=clock(),
    )
    wired["adapter"].poll_results = [_poll("pending")]

    out = worker.lambda_handler(sqs_event(job_id, action="poll", outbox_seq=3), Ctx("me"))

    assert out["batchItemFailures"] == [{"itemIdentifier": "m1"}], "busy 를 정상 ACK 하면 안 된다"
    assert len(wired["sqs"].visibility) == 1
    assert wired["sqs"].visibility[0]["VisibilityTimeout"] > 0
    assert wired["adapter"].poll_calls == [], "busy 인데 외부 호출이 나갔다"


def test_expired_lease_allows_reclaim_by_exactly_one_worker(wired):
    """lease 만료 후 재전달 → 'claimed' 재실행. crash 복구의 유일 경로다 (B5-01)."""
    from sunity_shared import firestore_admin, models

    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3)
    firestore_admin.claim_visual_job_action(
        job_id, generation=1, action="poll", outbox_seq=3,
        owner="crashed", lease_ms=models.VISUAL_CLAIM_LEASE_MS, now_ms=clock(),
    )
    clock.advance(models.VISUAL_CLAIM_LEASE_MS + 1)
    wired["adapter"].poll_results = [_poll("pending")]

    out = worker.lambda_handler(sqs_event(job_id, action="poll", outbox_seq=3), Ctx("me"))

    assert out["batchItemFailures"] == []
    assert len(wired["adapter"].poll_calls) == 1
    assert read_job(db, job_id)["attempt"] == 1


def test_stale_and_completed_are_acked_without_external_calls(wired):
    """구식 seq / 이미 진행한 job → 외부 0 + 정상 ACK. 재발행 불필요."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=7)

    stale = worker.lambda_handler(sqs_event(job_id, action="poll", outbox_seq=3), Ctx())
    assert stale["batchItemFailures"] == []

    completed = worker.lambda_handler(
        sqs_event(job_id, action="poll", outbox_seq=99), Ctx()
    )
    assert completed["batchItemFailures"] == []
    assert wired["adapter"].poll_calls == []


def test_generation_mismatch_is_noop(wired):
    """구세대 메시지 → 외부 0. 모더레이션 재시도 후 옛 메시지가 살아 돌아오는 경우다."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3, generation=2)
    out = worker.lambda_handler(
        sqs_event(job_id, action="poll", generation=1, outbox_seq=3), Ctx()
    )
    assert out["batchItemFailures"] == []
    assert wired["adapter"].poll_calls == []


def test_worker_never_reconstructs_job_from_inbound_message(wired):
    """B6-01 정적 계약: claim 반환 snapshot 만 action/CAS 에 쓴다.

    claim 이전 메시지 값으로 job 을 재구성하면 이미 한 칸 진행한 job 을 옛 seq 로
    다시 건드린다. 정적 grep 으로 회귀를 막는다.
    """
    source = _APP.read_text(encoding="utf-8")
    handle = source.split("def _handle_job(")[1].split("\ndef ")[0]
    # claim 결과 분기 이후 구간에서 msg[...] 를 다시 읽지 않아야 한다.
    after_claim = handle.split('res["job"]')[1]
    assert "msg[" not in after_claim, "claim 이후 inbound msg 재사용 (B6-01 위반)"


# ═══════════════ B8-01 create status 분기 ═══════════════


def test_reserved_acquire_creates_exactly_one_vendor_task(wired):
    """최초 reserved → acquired → **즉시** vendor create 1회 (B8-01).

    creating 전이만 하고 no-op 으로 끝나면 정상 create 가 영영 안 나간다 (T-31-85).
    """
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock)
    wired["adapter"].create_result = _created("task-9")

    out = worker.lambda_handler(sqs_event(job_id, action="create"), Ctx())

    assert out["batchItemFailures"] == []
    assert len(wired["adapter"].create_calls) == 1
    job = read_job(db, job_id)
    assert job["state"] == "polling" and job["taskId"] == "task-9"
    assert job["nextAction"] == "poll"


def test_concurrent_create_yields_one_vendor_call(wired):
    """동시 same-seq 2건 → acquired 1 / busy·stale 1 → vendor create 총 1회."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock)
    wired["adapter"].create_result = _created()

    worker.lambda_handler(sqs_event(job_id, action="create", message_id="c1"), Ctx("r1"))
    worker.lambda_handler(sqs_event(job_id, action="create", message_id="c2"), Ctx("r2"))

    assert len(wired["adapter"].create_calls) == 1


def test_create_unconfirmed_never_recreates(wired):
    """creating + lease 만료 + taskId 부재 → 수동 판정. **자동 재생성 금지** (B2-02).

    create 가 벤더에 도달했는지 알 수 없으므로 재시도는 곧 이중 과금이다.
    """
    from sunity_shared import models

    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(
        db, clock, state="creating", nextAction=None, dispatchState=None,
        leaseOwner="dead", leaseExpiresAt=clock() - 1, requestKey=f"{_job_id()}:gen1",
    )
    worker.lambda_handler(sqs_event(job_id, action="create"), Ctx())

    assert wired["adapter"].create_calls == [], "unconfirmed 에서 재생성이 나갔다"
    job = read_job(db, job_id)
    # correctedPose 라 postprocessing 경유 (H9-09) — 직접 failed 로 가지 않는다.
    assert job["state"] == "postprocessing"
    assert job["pendingFailureReason"] == "create_unconfirmed"
    assert job["inputSealed"] is True
    assert job["state"] not in models.VISUAL_TERMINAL_STATES


def test_create_resume_when_task_id_already_written(wired):
    """taskId write 직후 crash → polling 재개 + create 재호출 0."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(
        db, clock, state="creating", nextAction=None, dispatchState=None,
        taskId="t-existing", leaseOwner="dead", leaseExpiresAt=clock() - 1,
        requestKey=f"{_job_id()}:gen1",
    )
    worker.lambda_handler(sqs_event(job_id, action="create"), Ctx())

    assert wired["adapter"].create_calls == []
    job = read_job(db, job_id)
    assert job["state"] == "polling" and job["taskId"] == "t-existing"


def test_sync_succeeded_is_rejected_async_only(wired):
    """create 가 sync succeeded 를 반환 → typed 실패 종결 (B4-02).

    taskId 없이 산출물만 있으면 재개/멱등 계약이 성립하지 않는다.
    """
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock)
    wired["adapter"].create_result = _poll("succeeded", output_url="https://x/y.png")

    worker.lambda_handler(sqs_event(job_id, action="create"), Ctx())

    job = read_job(db, job_id)
    assert job["state"] == "postprocessing"
    assert job["pendingFailureReason"] == "vendor_error"
    assert job["state"] != "polling"


def test_rotation_create_failure_finalizes_directly(wired):
    """H9-09 kind 분기 — rotation 은 임시 입력·pair 가 없어 postprocessing 을 안 거친다."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, kind="rotation")
    wired["adapter"].create_result = _poll("failed")

    worker.lambda_handler(sqs_event(job_id, action="create"), Ctx())

    job = read_job(db, job_id)
    assert job["state"] == "failed" and job["failureReason"] == "vendor_error"
    assert read_analysis(db)["result"]["rotationStatus"] == "failed"


def test_rotation_rejects_video_key_outside_own_identity(wired):
    """남의 객체를 벤더로 보내는 경로 차단 (H-05). key 를 신뢰하지 않는다."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, kind="rotation", myVideoKey="uploads/victim/other.mp4")

    worker.lambda_handler(sqs_event(job_id, action="create"), Ctx())

    assert wired["adapter"].create_calls == []
    assert read_job(db, job_id)["failureReason"] == "invalid_output"


def test_creating_internal_transition_emits_no_sqs_message(wired):
    """H7-01: reserved→creating 은 nextAction=None 이라 SQS 로 나가면 안 된다.

    action:null 메시지는 스키마 위반이라 DLQ 만 오염시킨다.
    """
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock)
    wired["adapter"].create_result = _created()

    worker.lambda_handler(sqs_event(job_id, action="create"), Ctx())

    actions = [json.loads(m["MessageBody"])["action"] for m in wired["sqs"].sent]
    assert None not in actions and all(a for a in actions)
    assert actions == ["poll"]


# ═══════════════ poll ═══════════════


def test_poll_success_transitions_without_storing_url(wired):
    """H3-01 — succeeded 시점에 outputUrl 을 기록하지 않는다. fetch 가 재-poll 한다."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3)
    wired["adapter"].poll_results = [_poll("succeeded", output_url="https://vendor/x.png")]

    worker.lambda_handler(sqs_event(job_id, action="poll", outbox_seq=3), Ctx())

    job = read_job(db, job_id)
    assert job["state"] == "fetching" and job["nextAction"] == "fetch"
    assert "https://vendor/x.png" not in json.dumps(job)
    assert "outputUrl" not in job


def test_poll_timeout_after_max_attempts(wired):
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(
        db, clock, state="polling", nextAction="poll", taskId="t1",
        outboxSeq=3, attempt=worker.MAX_POLLS - 1,
    )
    wired["adapter"].poll_results = [_poll("pending")]

    worker.lambda_handler(sqs_event(job_id, action="poll", outbox_seq=3), Ctx())

    job = read_job(db, job_id)
    assert job["state"] == "postprocessing" and job["pendingFailureReason"] == "timeout"


def test_moderation_retry_promotes_generation_and_request_key(wired):
    """B4-03 + H5-03: retry_ready → creating 이 generation+1 + 새 gen requestKey."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3)
    wired["adapter"].poll_results = [_poll("blocked")]

    worker.lambda_handler(sqs_event(job_id, action="poll", outbox_seq=3), Ctx())
    job = read_job(db, job_id)
    assert job["state"] == "retry_ready" and job["taskId"] is None
    assert job["nextAction"] == "create" and job["retryCount"] == 1

    wired["adapter"].create_result = _created("task-2")
    worker.lambda_handler(
        sqs_event(job_id, action="create", generation=job["generation"], outbox_seq=job["outboxSeq"]),
        Ctx("r2"),
    )
    job2 = read_job(db, job_id)
    assert job2["generation"] == job["generation"] + 1
    assert job2["requestKey"].endswith(f":gen{job2['generation']}")


def test_second_moderation_block_is_terminal(wired):
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(
        db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3, retryCount=1
    )
    wired["adapter"].poll_results = [_poll("blocked")]

    worker.lambda_handler(sqs_event(job_id, action="poll", outbox_seq=3), Ctx())

    assert read_job(db, job_id)["pendingFailureReason"] == "moderation"


# ═══════════════ outbox durability ═══════════════


def test_send_failure_leaves_pending_outbox_for_dispatcher(wired):
    """send 실패는 예외를 전파하지 않고 outbox 를 pending 으로 남긴다 (B3-01).

    복구 주체는 worker 가 아니라 dispatcher 다.
    """
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3)
    wired["adapter"].poll_results = [_poll("succeeded")]
    wired["sqs"].fail_send = True

    out = worker.lambda_handler(sqs_event(job_id, action="poll", outbox_seq=3), Ctx())

    assert out["batchItemFailures"] == []
    job = read_job(db, job_id)
    assert job["state"] == "fetching"
    assert job["dispatchState"] == "pending" and job["nextAction"] == "fetch"


def test_transition_clears_claim_so_next_action_can_be_claimed(wired):
    """B6-01: 새 outboxSeq 를 만들 때 claim 필드가 원자 clear 되어야 한다."""
    db, clock = wired["db"], wired["clock"]
    job_id, _ = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3)
    wired["adapter"].poll_results = [_poll("succeeded")]

    worker.lambda_handler(sqs_event(job_id, action="poll", outbox_seq=3), Ctx())

    job = read_job(db, job_id)
    assert job["claimState"] is None and job["claimOwner"] is None
    assert job["claimedOutboxSeq"] != job["outboxSeq"]


def test_late_worker_with_lost_lease_cannot_write(wired, monkeypatch):
    """H6-07: owner 가 같아도 lease 가 만료됐으면 결과 write 는 거부된다."""
    from sunity_shared import firestore_admin, models

    db, clock = wired["db"], wired["clock"]
    job_id, job = seed_job(db, clock, state="polling", nextAction="poll", taskId="t1", outboxSeq=3)
    res = firestore_admin.claim_visual_job_action(
        job_id, generation=1, action="poll", outbox_seq=3,
        owner="slow", lease_ms=models.VISUAL_CLAIM_LEASE_MS, now_ms=clock(),
    )
    snap = res["job"]
    clock.advance(models.VISUAL_CLAIM_LEASE_MS + 1)

    out = worker._advance(
        job_id, snap, next_state="fetching", updates={}, next_action="fetch", owner="slow"
    )
    assert out is None
    assert read_job(db, job_id)["state"] == "polling"


# ═══════════════ D-08 fail-closed calibration ═══════════════


def test_missing_calibration_env_raises_instead_of_guessing(monkeypatch):
    """31-13 CALIBRATION.json 은 blocked 상태라 임계값을 방출하지 않는다.

    값이 없을 때 기본값을 **지어내면** 근거 없는 교정 이미지가 사용자에게 노출된다.
    """
    monkeypatch.delenv("DISPLAY_POSE_TOL_DEG", raising=False)
    with pytest.raises(worker._CalibrationMissing):
        worker._required_float_env("DISPLAY_POSE_TOL_DEG")

    monkeypatch.setenv("DISPLAY_POSE_TOL_DEG", "not-a-number")
    with pytest.raises(worker._CalibrationMissing):
        worker._required_float_env("DISPLAY_POSE_TOL_DEG")


def test_no_threshold_literals_in_worker_source():
    """임계값 리터럴 금지 (H3-02/B4-05) — 판정 기준은 env 주입뿐이다."""
    source = _APP.read_text(encoding="utf-8")
    for env_name in (
        "DISPLAY_JUDGE_CONFIDENCE",
        "TRAINING_JUDGE_CONFIDENCE",
        "DISPLAY_POSE_TOL_DEG",
        "TRAINING_POSE_TOL_DEG",
        "PRESERVE_POSE_TOL_DEG",
    ):
        assert f'_required_float_env("{env_name}")' in source, f"{env_name} 미소비"
        assert f'"{env_name}",' not in source, f"{env_name} 에 기본값 fallback 금지"


# ═══════════════ correctedPose 체인 (Task 2) ═══════════════

PNG_1PX = None


def _png_bytes(color=(10, 20, 30)):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(color=(10, 20, 30)):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="JPEG")
    return buf.getvalue()


def _verdict(confidence: float, **overrides):
    """7축 전부 통과하는 JudgeVerdict. 축은 visual_gen.JUDGE_AXES 단일 출처."""
    from sunity_shared.analysis import visual_gen

    axes = {axis: True for axis in visual_gen.JUDGE_AXES}
    axes.update(overrides)
    return visual_gen.JudgeVerdict(confidence=float(confidence), reason="test", **axes)


def _pose_payload(angles: dict, *, width=1000.0, height=1000.0, ok=True):
    """지정 관절이 정확히 그 각도가 되도록 keypoint 3점을 배치한 /pose-image 응답.

    좌표는 정규화([0,1])라 pose_gate 가 width/height 를 곱해 등방 px 로 되돌린다.
    """
    import math

    from sunity_shared.analysis.fault_zoom import ARROW_JOINT_MAP

    keypoints = {}
    for joint, deg in angles.items():
        prox, vertex, distal = ARROW_JOINT_MAP[joint]
        vx, vy = 0.5, 0.5
        r = 0.2
        rad = math.radians(deg)
        keypoints[vertex] = [vx, vy, 0.9]
        keypoints[prox] = [vx + r, vy, 0.9]
        keypoints[distal] = [vx + r * math.cos(rad), vy + r * math.sin(rad), 0.9]
    return {"ok": ok, "width": width, "height": height, "keypoints": keypoints}


class PoseServer:
    """/pose-image 대역. 호출 순서대로 payload 를 돌려준다 (원본 → 생성물)."""

    def __init__(self, *payloads) -> None:
        self.queue = list(payloads)
        self.calls = 0

    def __call__(self, pose_url, image_b64, token, timeout_s):
        self.calls += 1
        if not self.queue:
            return None
        return self.queue.pop(0) if len(self.queue) > 1 else self.queue[0]


@pytest.fixture
def cp(monkeypatch, wired):
    """correctedPose 체인용 추가 대역 — 다운로드/judge/pose/pair."""
    from sunity_shared.analysis import pair_store, pose_gate, visual_gen

    state = dict(wired)
    src_png = _png_bytes((1, 2, 3))
    after_png = _png_bytes((9, 9, 9))
    state["src_png"] = src_png
    state["after_png"] = after_png
    state["vendor_bytes"] = after_png

    import hashlib

    src_hash = hashlib.sha256(src_png).hexdigest()
    state["src_hash"] = src_hash

    def _fake_download(url, dest, **kw):
        with open(dest, "wb") as fh:
            fh.write(state["vendor_bytes"])
        return visual_gen.DownloadedAsset(
            path=dest,
            sha256=hashlib.sha256(state["vendor_bytes"]).hexdigest(),
            size_bytes=len(state["vendor_bytes"]),
            content_type="image/png",
        )

    monkeypatch.setattr(visual_gen, "download_vendor_asset", _fake_download)

    verdict = _verdict(0.95)
    state["verdict"] = verdict
    state["judge_calls"] = []

    def _fake_judge(before, after, context, **kw):
        state["judge_calls"].append(context)
        result = state["verdict"]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(visual_gen, "judge_corrected_pose", _fake_judge)

    # 원본/생성물 모두 목표 관절 175도 + 다른 관절 보존.
    state["pose_server"] = PoseServer(
        _pose_payload({JOINT: 175.0, "right_knee": 180.0}),
        _pose_payload({JOINT: 175.0, "right_knee": 180.0}),
    )
    monkeypatch.setattr(
        pose_gate, "_post_pose_image", lambda *a, **k: state["pose_server"](*a, **k)
    )

    state["pair_calls"] = []
    state["pair_result"] = "committed"

    def _fake_pair(*a, **kw):
        state["pair_calls"].append(kw)
        result = state["pair_result"]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(pair_store, "store_training_pair", _fake_pair)
    monkeypatch.setattr(
        pair_store, "validate_hmac_key_set",
        lambda raw: {"active": "v1", "keys": {"v1": b"k" * 32}} if raw else None,
    )
    monkeypatch.setenv("PAIR_ID_HMAC_KEYS", json.dumps({"active": "v1"}))
    monkeypatch.setenv("PAIRS_BUCKET", "pairs-bkt")
    return state


def seed_fetching(cp, **overrides):
    """fetching 상태 job + srcKey S3 객체까지 심는다."""
    db, clock = cp["db"], cp["clock"]
    job_id, job = seed_job(
        db, clock, state="fetching", nextAction="fetch", taskId="t1",
        outboxSeq=4, sourceHash=cp["src_hash"], **overrides,
    )
    cp["s3"].objects[("visual-input-bkt", job["srcKey"])] = {
        "Body": cp["src_png"], "Metadata": {"sha256": cp["src_hash"]}
    }
    return job_id, job


def run(cp, job_id, action, seq):
    return worker.lambda_handler(
        sqs_event(job_id, action=action, outbox_seq=seq, message_id=action), Ctx(f"r-{action}")
    )


def run_chain(cp, job_id):
    """fetch → judge → pose_check → postprocess 를 각각 별도 invocation 으로."""
    db = cp["db"]
    for action in ("fetch", "judge", "pose_check", "postprocess"):
        job = read_job(db, job_id)
        if job["state"] in ("done", "failed"):
            break
        run(cp, job_id, action, job["outboxSeq"])
    return read_job(db, job_id)


def test_full_corrected_pose_chain_reaches_done_with_no_input_left(cp):
    """PASS 체인 → done + canonical key + inputSealed + 임시 프레임 0 + cleanup 증명."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    assert job["state"] == "done"
    assert job["canonicalKey"].endswith(f"corrected_pose_{JOINT}.png")
    assert job["inputSealed"] is True
    assert job["cleanupVerifiedAtMs"] > 0
    assert job["privacyBlocker"] is None
    # 임시 생체 프레임이 exact prefix 아래 하나도 남지 않았다.
    remaining = [
        k for (b, k) in cp["s3"].objects
        if b == "visual-input-bkt" and k.startswith(f"visual-input/{UID}/{ANALYSIS_ID}/")
    ]
    assert remaining == []
    assert read_analysis(cp["db"])["result"]["correctedPoseStatus"] == "done"


def test_pose_gate_receives_preserved_targets_from_source_frame(cp):
    """★ preserved_targets 를 실제로 넘기는지 — 안 넘기면 게이트가 목표 관절만 본다.

    31-01 실측에서 8개 중 6개가 "목표는 맞췄지만 포즈를 새로 그린" 산출물이었다.
    """
    from sunity_shared.analysis import pose_gate

    captured = {}
    original = pose_gate.measure_generated_pose

    def _spy(image_bytes, **kw):
        captured.update(kw)
        return original(image_bytes, **kw)

    pose_gate.measure_generated_pose, saved = _spy, pose_gate.measure_generated_pose
    try:
        cp["adapter"].poll_results = [_poll("succeeded")]
        job_id, _ = seed_fetching(cp)
        run_chain(cp, job_id)
    finally:
        pose_gate.measure_generated_pose = saved

    assert captured.get("preserved_targets"), "preserved_targets 미전달 — 게이트가 무력하다"
    assert captured.get("preserve_tolerance_deg") is not None
    # 원본 프레임에서 잰 각도이며 목표 관절 외 관절을 포함해야 의미가 있다.
    assert "right_knee" in captured["preserved_targets"]
    assert captured["preserved_targets"]["right_knee"] == pytest.approx(180.0, abs=0.5)


def test_whole_pose_regeneration_is_rejected(cp):
    """목표 관절은 맞췄는데 다른 관절이 흔들린 산출물 → 불통과 + 노출 0."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    cp["pose_server"] = PoseServer(
        _pose_payload({JOINT: 175.0, "right_knee": 180.0}),  # 원본
        _pose_payload({JOINT: 175.0, "right_knee": 90.0}),  # 생성물: 무릎이 새로 그려짐
    )
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    assert job["state"] == "failed"
    assert job["failureReason"] == "pose_gate_failed"
    assert job.get("poseGatePreservedViolation") == "right_knee"
    assert read_analysis(cp["db"])["result"]["correctedPoseStatus"] == "failed"


def test_unmeasurable_source_frame_fails_closed(cp):
    """원본을 못 재면 '보존됐는지' 판정 자체가 불가 → 통과시키지 않는다."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    cp["pose_server"] = PoseServer(None)  # /pose-image 도달 실패
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    assert job["state"] == "failed" and job["failureReason"] == "pose_gate_unavailable"


# ── D-08 fail-closed: 채택 임계값 부재 ──


@pytest.mark.parametrize(
    "missing,expected",
    [
        ("DISPLAY_JUDGE_CONFIDENCE", "judge_failed"),
        ("TRAINING_JUDGE_CONFIDENCE", "judge_failed"),
        ("DISPLAY_POSE_TOL_DEG", "pose_gate_unavailable"),
        ("TRAINING_POSE_TOL_DEG", "pose_gate_unavailable"),
        ("PRESERVE_POSE_TOL_DEG", "pose_gate_unavailable"),
    ],
)
def test_missing_calibration_never_shows_the_card(cp, monkeypatch, missing, expected):
    """31-13 CALIBRATION 은 blocked 이고 임계값을 방출하지 않는다.

    값이 없을 때 기본값을 지어내면 근거 없는 교정 이미지가 노출된다. 카드를 안 띄우는
    쪽으로 닫힌다.
    """
    monkeypatch.delenv(missing, raising=False)
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    assert job["state"] == "failed"
    assert job["failureReason"] == expected
    assert job.get("canonicalKey") is None
    assert read_analysis(cp["db"])["result"]["correctedPoseStatus"] == "failed"


# ── fetch: 재-poll / 정규화 / hash conflict ──


def test_fetch_repolls_task_id_and_never_persists_url(cp):
    """H3-01 — 저장된 URL 이 아니라 taskId 재-poll 로 fresh URL 을 얻는다."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    run(cp, job_id, "fetch", 4)

    assert cp["adapter"].poll_calls == ["t1"]
    job = read_job(cp["db"], job_id)
    assert job["state"] == "judging"
    blob = json.dumps(job)
    assert "http://" not in blob and "https://" not in blob
    assert "signedUrl" not in blob


def test_jpeg_output_is_reencoded_to_png(cp):
    """H4-05/H4-06 — JPEG 로 와도 canonical 은 PNG. EXIF 는 재인코딩으로 떨어진다."""
    cp["vendor_bytes"] = _jpeg_bytes()
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    run(cp, job_id, "fetch", 4)

    job = read_job(cp["db"], job_id)
    staged = cp["s3"].objects[("visual-input-bkt", job["stagingKey"])]
    assert staged["Body"][:8] == b"\x89PNG\r\n\x1a\n"
    assert staged["Metadata"]["sha256"] == job["afterHash"]


def test_staging_hash_conflict_blocks_overwrite(cp):
    """H6-03 — deterministic key 인데 내용이 다르다 = 덮어쓰지 않고 종결한다."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, job = seed_fetching(cp)
    staging = worker._staging_key(job)
    cp["s3"].objects[("visual-input-bkt", staging)] = {
        "Body": b"other", "Metadata": {"sha256": "deadbeef"}
    }
    before_puts = len(cp["s3"].puts)

    run(cp, job_id, "fetch", 4)

    assert len(cp["s3"].puts) == before_puts, "hash 불일치인데 overwrite 했다"
    assert read_job(cp["db"], job_id)["pendingFailureReason"] == "invalid_output"


def test_staging_reuse_skips_second_put(cp):
    """같은 정규화 PNG 재실행 → HEAD 재사용, 재PUT 0 (멱등)."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)
    run(cp, job_id, "fetch", 4)
    puts_after_first = len(cp["s3"].puts)

    # 같은 seq 로 되돌려 재실행 (재전달 모사).
    cp["db"].store[__import__("sunity_shared.models", fromlist=["x"]).visual_job_doc_path(job_id)].update(
        {"state": "fetching", "nextAction": "fetch", "outboxSeq": 4, "claimState": None,
         "claimOwner": None, "claimLeaseExpiresAt": 0, "claimedOutboxSeq": 0}
    )
    cp["adapter"].poll_results = [_poll("succeeded")]
    run(cp, job_id, "fetch", 4)

    assert len(cp["s3"].puts) == puts_after_first, "동일 내용인데 재PUT 했다"


@pytest.mark.parametrize(
    "reason,expected",
    [("too_large", "judge_input_too_large"), ("bomb", "judge_input_too_large"),
     ("unreadable", "invalid_output"), ("bad_format", "invalid_output"),
     ("bad_dimension", "invalid_output")],
)
def test_decode_errors_split_into_two_typed_failures(reason, expected):
    """M5-01 — 크기 초과와 손상/포맷 불일치는 운영 대응이 다르므로 분리한다."""
    from sunity_shared.analysis import visual_gen

    assert worker._decode_failure_reason(visual_gen.ImageDecodeError(reason)) == expected


def test_max_image_pixels_capped_once_at_module_load():
    """M5-03 — 호출마다 세우면 예외 경로에서 원복이 빠져 전역이 오염된다."""
    from PIL import Image

    assert Image.MAX_IMAGE_PIXELS == worker._MAX_IMAGE_PIXELS


# ── judge ──


def test_judge_failure_routes_through_postprocessing(cp):
    """H5-05 — 실패도 cleanup 을 우회하지 않는다."""
    cp["verdict"] = None
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    run(cp, job_id, "fetch", 4)
    job = read_job(cp["db"], job_id)
    run(cp, job_id, "judge", job["outboxSeq"])

    job = read_job(cp["db"], job_id)
    assert job["state"] == "postprocessing"
    assert job["pendingFailureReason"] == "judge_failed"
    assert job["inputSealed"] is True


def test_judge_input_too_large_is_distinct_terminal(cp):
    from sunity_shared.analysis import visual_gen

    cp["verdict"] = visual_gen.JudgeInputTooLargeError("too big")
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)
    assert job["failureReason"] == "judge_input_too_large"


def test_display_pass_but_training_fail_yields_done_without_pair(cp):
    """B4-05 — 노출 기준과 학습 적재 기준은 실패 비용이 달라 분리돼 있다."""
    from sunity_shared.analysis import visual_gen

    cp["verdict"] = _verdict(0.8)  # display(0.7) 통과, training(0.9) 미달
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    assert job["state"] == "done"
    assert job["pairEligible"] is False
    assert cp["pair_calls"] == []


# ── canonical / pair / consent ──


def test_canonical_copy_preserves_sha_metadata(cp):
    """H7-08 — REPLACE + sha256 없이 copy 하면 다음 replay 가 integrity conflict 오판."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    canonical = cp["s3"].objects[("video-bkt", job["canonicalKey"])]
    assert canonical["Metadata"]["sha256"] == job["afterHash"]


def test_consent_revoked_between_pose_check_and_postprocess(cp):
    """H5-01 — S3 PUT 직전 동의를 재read 한다. 철회면 적재 0."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    for action in ("fetch", "judge", "pose_check"):
        run(cp, job_id, action, read_job(cp["db"], job_id)["outboxSeq"])

    read_analysis(cp["db"])["learningOptIn"] = False  # 철회
    run(cp, job_id, "postprocess", read_job(cp["db"], job_id)["outboxSeq"])

    job = read_job(cp["db"], job_id)
    assert cp["pair_calls"] == [], "철회했는데 페어가 적재됐다"
    assert job["pairStoreStatus"] == "skipped_consent"
    assert job["state"] == "done", "동의 철회가 사용자 표시를 막으면 안 된다"


def test_pair_id_fixed_at_pose_check_not_reselected(cp):
    """B5-03 — postprocess 가 active key 를 다시 고르면 키 회전 시 이중 적재된다."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    for action in ("fetch", "judge", "pose_check"):
        run(cp, job_id, action, read_job(cp["db"], job_id)["outboxSeq"])
    fixed = read_job(cp["db"], job_id)
    assert fixed["pairId"] and fixed["pairHmacKeyVersion"] == "v1"

    run(cp, job_id, "postprocess", fixed["outboxSeq"])
    assert cp["pair_calls"][0]["pair_id"] == fixed["pairId"]

    source = worker_code()
    post = source.split("def _action_postprocess")[1]
    assert "validate_hmac_key_set" not in post, "postprocess 가 키를 재선택한다"


def test_hmac_config_failure_does_not_block_display(cp, monkeypatch):
    """H6-05 — 학습 설정 실수가 제품 기능을 죽이면 안 된다."""
    from sunity_shared.analysis import pair_store

    monkeypatch.setattr(pair_store, "validate_hmac_key_set", lambda raw: None)
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    assert job["state"] == "done", "HMAC env 오류가 correctedPose 노출을 막았다"
    assert job["pairStoreStatus"] == "failed_config"
    assert cp["pair_calls"] == []


def test_pair_network_failure_does_not_delay_cleanup_or_finalize(cp):
    """H7-07/H8-02 — pair 는 부산물이다. self-loop 없이 즉시 cleanup/finalize 로 간다."""
    cp["pair_result"] = "failed"
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    assert job["state"] == "done"
    assert job["pairStoreStatus"] == "failed"
    assert int(job.get("pairAttempt") or 0) == 0, "pair 재시도 self-loop 가 생겼다"


def test_pair_conflict_is_quarantined_not_retried(cp, monkeypatch):
    """M6-04 — 같은 pairId 에 다른 내용이 있으면 재시도로 풀 문제가 아니다."""
    metrics = []
    monkeypatch.setattr(worker, "_put_metric", lambda name, value=1.0: metrics.append(name))
    cp["pair_result"] = "conflict"
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    assert job["pairStoreStatus"] == "conflict"
    assert "VisualPairConflict" in metrics
    assert len(cp["pair_calls"]) == 1, "conflict 를 재시도했다"


# ── cleanup ──


def test_cleanup_removes_every_object_under_exact_prefix(cp):
    """비-버저닝 단일 delete 로 완전 소거 — version 열거 불필요 (B6-03)."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, job = seed_fetching(cp)
    extra = f"visual-input/{UID}/{ANALYSIS_ID}/extra_frame.png"
    cp["s3"].objects[("visual-input-bkt", extra)] = {"Body": b"x", "Metadata": {}}
    # 다른 분석의 프레임은 건드리면 안 된다.
    other = f"visual-input/{UID}/other-analysis/keep.png"
    cp["s3"].objects[("visual-input-bkt", other)] = {"Body": b"y", "Metadata": {}}

    run_chain(cp, job_id)

    assert ("visual-input-bkt", extra) not in cp["s3"].objects
    assert ("visual-input-bkt", other) in cp["s3"].objects, "다른 분석 프레임을 지웠다"


def test_cleanup_blocked_never_finalizes_terminal(cp, monkeypatch):
    """B6-04 — cleanup 미완을 terminal 로 적으면 PII 가 남은 채 복구 주체가 사라진다."""
    metrics = []
    monkeypatch.setattr(worker, "_put_metric", lambda name, value=1.0: metrics.append(name))
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)
    for action in ("fetch", "judge", "pose_check"):
        run(cp, job_id, action, read_job(cp["db"], job_id)["outboxSeq"])

    cp["s3"].delete_errors = [{"Code": "AccessDenied", "Key": "k"}]
    for _ in range(worker.CLEANUP_ATTEMPT_MAX):
        job = read_job(cp["db"], job_id)
        if job["state"] != "postprocessing":
            break
        run(cp, job_id, "postprocess", job["outboxSeq"])

    job = read_job(cp["db"], job_id)
    assert job["state"] == "postprocessing", "cleanup 미완인데 terminal 로 갔다"
    assert job["privacyBlocker"] == "cleanup_blocked"
    assert "VisualCleanupBlocked" in metrics
    assert read_analysis(cp["db"])["result"]["correctedPoseStatus"] == "pending"

    # 해결 후 재구동 → remaining 0 재확인 뒤에만 종결.
    cp["s3"].delete_errors = []
    run(cp, job_id, "postprocess", read_job(cp["db"], job_id)["outboxSeq"])
    job = read_job(cp["db"], job_id)
    assert job["state"] == "done" and job["cleanupVerifiedAtMs"] > 0
    assert job["privacyBlocker"] is None


def test_failed_terminal_also_requires_cleanup_proof(cp):
    """B7-04 — done 전용이 아니다. 실패 경로도 cleanup 후에만 종결한다."""
    cp["verdict"] = None
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)

    job = run_chain(cp, job_id)

    assert job["state"] == "failed" and job["failureReason"] == "judge_failed"
    assert job["cleanupVerifiedAtMs"] > 0
    remaining = [
        k for (b, k) in cp["s3"].objects
        if b == "visual-input-bkt" and k.startswith(f"visual-input/{UID}/{ANALYSIS_ID}/")
    ]
    assert remaining == []


def test_worker_releases_key_ownership_after_cleanup(cp):
    """B10-03 — release 를 빠뜨리면 job ref 가 영구 live 로 남아(B11-04) 이후
    같은 key 의 janitor 삭제가 영원히 skip 된다."""
    from sunity_shared import firestore_admin

    released = []
    original = firestore_admin.release_key_ownership
    firestore_admin.release_key_ownership = lambda b, k, ref: released.append((b, k, ref))
    try:
        cp["adapter"].poll_results = [_poll("succeeded")]
        job_id, job = seed_fetching(cp)
        run_chain(cp, job_id)
    finally:
        firestore_admin.release_key_ownership = original

    assert any(r[1] == job["srcKey"] and r[2] == job_id for r in released)


def test_postprocess_replay_is_idempotent(cp):
    """H4-01 — finalize 후 재전달은 'stale' no-op 이고 두 문서가 계속 일치한다."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)
    job = run_chain(cp, job_id)
    assert job["state"] == "done"
    pairs_before = len(cp["pair_calls"])

    run(cp, job_id, "postprocess", job["outboxSeq"])

    job2 = read_job(cp["db"], job_id)
    assert job2["state"] == "done"
    assert len(cp["pair_calls"]) == pairs_before, "재전달이 페어를 또 적재했다"
    assert read_analysis(cp["db"])["result"]["correctedPoseStatus"] == "done"


def test_no_urls_anywhere_in_serialized_state(cp):
    """H3-01 + M3-04 — job/analysis/SQS 3면 어디에도 URL 이 없어야 한다."""
    cp["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_fetching(cp)
    run_chain(cp, job_id)

    blobs = [
        json.dumps(read_job(cp["db"], job_id)),
        json.dumps(read_analysis(cp["db"])),
        json.dumps([m.get("MessageBody") for m in cp["sqs"].sent]),
    ]
    for blob in blobs:
        assert "http://" not in blob and "https://" not in blob
        assert "outputUrl" not in blob and "signedUrl" not in blob


# ═══════════════ rotation (Task 3) ═══════════════


@pytest.fixture
def rot(monkeypatch, wired):
    from sunity_shared.analysis import visual_gen

    state = dict(wired)
    state["content_type"] = "video/mp4"
    state["video_bytes"] = b"\x00\x00\x00\x18ftypmp42" + b"v" * 512

    def _fake_download(url, dest, **kw):
        with open(dest, "wb") as fh:
            fh.write(state["video_bytes"])
        ctype = state["content_type"].split(";")[0].strip().lower()
        allowed = kw.get("allowed_content_types") or ()
        # 31-05 의 실제 판정(startswith)을 그대로 모사한다 — 그래야 worker 가 거는
        # exact membership 방어가 의미 있는지 테스트가 판별할 수 있다.
        if not any(ctype.startswith(t) for t in allowed):
            raise visual_gen.VendorDownloadError("bad_content_type")
        import hashlib

        return visual_gen.DownloadedAsset(
            path=dest,
            sha256=hashlib.sha256(state["video_bytes"]).hexdigest(),
            size_bytes=len(state["video_bytes"]),
            content_type=ctype,
        )

    monkeypatch.setattr(visual_gen, "download_vendor_asset", _fake_download)
    return state


def seed_rotation_fetching(rot):
    return seed_job(
        rot["db"], rot["clock"], kind="rotation", state="fetching",
        nextAction="fetch", taskId="t1", outboxSeq=4,
    )


def test_rotation_fetch_streams_to_canonical_and_finalizes(rot):
    """H2-05 — 수백 MB 를 메모리에 올리지 않는다. upload_file(멀티파트) 경로."""
    rot["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_rotation_fetching(rot)

    run(rot, job_id, "fetch", 4)

    job = read_job(rot["db"], job_id)
    assert job["state"] == "done"
    key = f"results/{UID}/{ANALYSIS_ID}/rotation.mp4"
    assert ("video-bkt", key) in rot["s3"].objects
    assert rot["adapter"].poll_calls == ["t1"], "taskId 재-poll 미수행 (H3-01)"
    assert read_analysis(rot["db"])["result"]["rotationStatus"] == "done"


def test_rotation_does_not_pass_through_postprocessing(rot):
    """rotation 은 임시 입력·pair 가 없어 cleanup 계약을 경유하지 않는다."""
    rot["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_rotation_fetching(rot)

    run(rot, job_id, "fetch", 4)

    job = read_job(rot["db"], job_id)
    assert job["state"] == "done"
    assert job.get("pendingTerminalState") is None
    assert job.get("inputSealed") is not True


@pytest.mark.parametrize(
    "content_type,ok",
    [
        ("video/mp4", True),
        ("video/mp4; charset=utf-8", True),
        ("video/mp4foo", False),  # M5-02 — startswith 로는 통과해 버린다
        ("text/html", False),
    ],
)
def test_rotation_content_type_exact_membership(rot, content_type, ok):
    """M5-02 — 확장자만 맞춘 다른 포맷을 mp4 로 적재하는 경로를 닫는다."""
    rot["content_type"] = content_type
    rot["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_rotation_fetching(rot)

    run(rot, job_id, "fetch", 4)

    job = read_job(rot["db"], job_id)
    if ok:
        assert job["state"] == "done"
    else:
        assert job["state"] == "failed" and job["failureReason"] == "invalid_output"


def test_rotation_never_persists_url(rot):
    rot["adapter"].poll_results = [_poll("succeeded")]
    job_id, _ = seed_rotation_fetching(rot)

    run(rot, job_id, "fetch", 4)

    blob = json.dumps(read_job(rot["db"], job_id))
    assert "http://" not in blob and "https://" not in blob


# ═══════════════ 금지 심볼 (acceptance grep) ═══════════════


@pytest.mark.parametrize(
    "banned",
    [
        "import requests",
        "fail_analysis",
        "update_analysis_visual",
        "google.genai",
        "list_object_versions",
        "outputUrl",
        "_test_allowed_hosts",
        "_test_allow_private",
    ],
)
def test_worker_source_has_no_banned_symbol(banned):
    """운영 경로에 있으면 안 되는 심볼들 — 전부 사고 이력이 있는 것들이다."""
    assert banned not in worker_code()
