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
        "result": {}, "learningOptIn": True, "consentCapturedAtMs": clock(),
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
