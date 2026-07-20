"""분석측 correctedPose enqueue + SAM template 배선 게이트 — 담당 플랜 31-10.

실 Firestore/네트워크/Pod/S3 미접촉 — LOCAL ONLY. 공용 스캐폴드는 conftest.py 소유.

여기서 검증하는 것은 "job 이 만들어진다" 가 아니라 **어느 지점에서 크래시가 나도
임시 생체 프레임이 잔존하지 않고, 살아있는 남의 입력을 지우지 않는다**는 계약이다.
비-버저닝 전용 버킷이라 delete 1회 = 완전 소거이고, 그래서 "누가 지울 권한을
갖는가" 가 유일한 안전장치다 (10차 B10-01~03 / 11차 B11-01~04).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from sunity_shared import firestore_admin, models

_BACKEND = Path(__file__).resolve().parents[2]
_APP = _BACKEND / "functions" / "pipeline" / "app.py"
_TEMPLATE = _BACKEND / "template.yaml"
_DRYRUN = _BACKEND / "scripts" / "visual_infra_dryrun.py"

UID = "u1"
ANALYSIS_ID = "a" * 32
JOINT = "left_knee"
BUCKET = "sunity-motion-pilot-visual-input"
SRC_PNG = b"\x89PNG\r\n\x1a\nfake-frame-bytes"
SOURCE_HASH = hashlib.sha256(SRC_PNG).hexdigest()
SRC_KEY = f"visual-input/{UID}/{ANALYSIS_ID}/{SOURCE_HASH}.png"
JOB_ID = models.visual_job_id(UID, ANALYSIS_ID, models.VISUAL_KIND_CORRECTED_POSE)
NOW_MS = 1_700_000_000_000


def _load_pipeline():
    if "pipeline_app" in sys.modules:
        return sys.modules["pipeline_app"]
    spec = importlib.util.spec_from_file_location("pipeline_app", _APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules["pipeline_app"] = module
    spec.loader.exec_module(module)
    return module


app = _load_pipeline()


# ─────────────────────── fake AWS ───────────────────────


class _ClientError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict] = {}
        self.puts: list[tuple[str, str]] = []
        self.deleted: list[tuple[str, str]] = []
        self.put_error: str | None = None
        self.head_error = False

    def put_object(self, Bucket, Key, Body=None, ContentType=None, Metadata=None, **kw):  # noqa: N803
        if self.put_error:
            raise _ClientError(self.put_error)
        if kw.get("IfNoneMatch") == "*" and (Bucket, Key) in self.objects:
            raise _ClientError("PreconditionFailed")
        self.objects[(Bucket, Key)] = {"Body": Body, "Metadata": Metadata or {}}
        self.puts.append((Bucket, Key))

    def head_object(self, Bucket, Key):  # noqa: N803
        if self.head_error:
            raise _ClientError("500")
        entry = self.objects.get((Bucket, Key))
        if entry is None:
            raise _ClientError("404")
        return {"Metadata": entry["Metadata"]}

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.objects.pop((Bucket, Key), None)
        self.deleted.append((Bucket, Key))


class FakeSQS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.fail = False

    def send_message(self, **kw):
        if self.fail:
            raise RuntimeError("send failed (injected)")
        self.sent.append(kw)
        return {"MessageId": "m"}


class FakeTarget:
    """CorrectedPoseTarget 대역 — enqueue 는 to_payload() 스칼라만 소비한다."""

    user_frame_idx = 3

    def to_payload(self) -> dict:
        return {"jointKey": JOINT, "targetDeg": 175.0, "provenanceVersion": "cp-target-v1"}


@pytest.fixture
def s3(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(app, "_s3", fake)
    return fake


@pytest.fixture
def sqs(monkeypatch):
    fake = FakeSQS()
    monkeypatch.setattr(app, "_sqs", lambda: fake)
    return fake


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("VISUAL_JOBS_ENABLED", "true")
    monkeypatch.setenv("VISUAL_INPUT_BUCKET", BUCKET)
    monkeypatch.setenv("VISUAL_QUEUE_URL", "https://sqs.test/visual")
    return monkeypatch


@pytest.fixture
def analysis(fake_firestore):
    fake_firestore.store[models.analysis_doc_path(UID, ANALYSIS_ID)] = {
        "status": "done",
        "result": {},
    }
    return fake_firestore


def _enqueue(request_id: str = "req-a", target=None, src_png: bytes = SRC_PNG):
    app._enqueue_corrected_pose_job(
        uid=UID,
        analysis_id=ANALYSIS_ID,
        target=FakeTarget() if target is None else target,
        src_png=src_png,
        request_id=request_id,
    )


def _job(db) -> dict:
    return db.store.get(models.visual_job_doc_path(JOB_ID)) or {}


def _object_doc(db, key: str = SRC_KEY) -> dict | None:
    return db.store.get(models.visual_input_object_doc_path(BUCKET, key))


def _reservation(db, reservation_id: str) -> dict | None:
    return db.store.get(models.visual_input_reservation_doc_path(JOB_ID, reservation_id))


# ─────────────────────── flag / target 게이트 ───────────────────────


def test_flag_off_touches_nothing(s3, sqs, env, analysis):
    env.setenv("VISUAL_JOBS_ENABLED", "false")

    _enqueue()

    assert s3.puts == []
    assert sqs.sent == []
    assert _job(analysis) == {}


def test_target_none_skips(s3, sqs, env, analysis):
    """B2-01: 불확실하면 생성하지 않는다 — 잘못된 target 으로 과금하느니 생략."""
    app._enqueue_corrected_pose_job(
        uid=UID, analysis_id=ANALYSIS_ID, target=None, src_png=SRC_PNG, request_id="r"
    )

    assert s3.puts == []
    assert sqs.sent == []


def test_missing_bucket_env_skips(s3, sqs, env, analysis):
    env.delenv("VISUAL_INPUT_BUCKET")

    _enqueue()

    assert s3.puts == []
    assert _job(analysis) == {}


# ─────────────────────── upload-first 순서 (B3-03) ───────────────────────


def test_happy_path_puts_before_reserve_then_dispatches(s3, sqs, env, analysis):
    _enqueue()

    assert s3.puts == [(BUCKET, SRC_KEY)]
    job = _job(analysis)
    assert job["state"] == "reserved"
    assert job["srcKey"] == SRC_KEY
    assert job["sourceHash"] == SOURCE_HASH
    assert job["jointKey"] == JOINT
    msg = json.loads(sqs.sent[0]["MessageBody"])
    assert msg == {"jobId": JOB_ID, "generation": 1, "action": "create", "outboxSeq": 1}
    assert job["dispatchState"] == "sent"


def test_src_key_uses_full_64_hex(s3, sqs, env, analysis):
    """M7-02: prefix 절단은 불필요한 충돌 차단만 늘린다."""
    _enqueue()

    key = s3.puts[0][1]
    hash_segment = key.rsplit("/", 1)[-1].removesuffix(".png")
    assert len(hash_segment) == 64
    assert hash_segment == SOURCE_HASH


def test_put_is_conditional_and_carries_hash_metadata(s3, sqs, env, analysis, monkeypatch):
    seen = {}

    original = s3.put_object

    def _spy(**kw):
        seen.update(kw)
        return original(**kw)

    monkeypatch.setattr(s3, "put_object", _spy)
    _enqueue()

    assert seen["IfNoneMatch"] == "*"
    assert seen["Metadata"]["sha256"] == SOURCE_HASH
    assert seen["ContentType"] == "image/png"


def test_analysis_display_pending_written_by_reserve_only(s3, sqs, env, analysis):
    """B3-03: 표시 pending 은 reserve transaction 안에서만."""
    _enqueue()

    result = analysis.store[models.analysis_doc_path(UID, ANALYSIS_ID)]["result"]
    assert result["correctedPoseStatus"] == "pending"

    source = _APP.read_text(encoding="utf-8")
    assert "update_analysis_visual" not in source


# ─────────────────────── preflight (B6-03) ───────────────────────


@pytest.mark.parametrize("state", ["reserved", "creating", "done", "failed"])
def test_preflight_skips_put_when_job_exists(s3, sqs, env, analysis, state):
    """job 이 어떤 state 로든 있으면 source PUT 0.

    done/failed 뒤에 새 입력을 올리면 cleanup 이 끝난 뒤 PII 가 되살아난다.
    """
    firestore_admin._doc(models.visual_job_doc_path(JOB_ID)).set(
        {"state": state, "dispatchState": "sent", "srcKey": SRC_KEY, "outboxSeq": 1}
    )

    _enqueue()

    assert s3.puts == []
    assert sqs.sent == []


def test_preflight_resends_pending_outbox_without_put(s3, sqs, env, analysis):
    """이전 send 유실분은 PUT 없이 재발행만 한다."""
    firestore_admin._doc(models.visual_job_doc_path(JOB_ID)).set(
        {
            "state": "reserved",
            "dispatchState": "pending",
            "srcKey": SRC_KEY,
            "nextAction": "create",
            "outboxSeq": 1,
            "generation": 1,
        }
    )

    _enqueue()

    assert s3.puts == []
    assert len(sqs.sent) == 1
    assert _job(analysis)["dispatchState"] == "sent"


# ─────────────────────── 조건부 PUT 경쟁 (B5-02 / M6-02 / M4-04) ───────────────────────


def test_existing_object_same_hash_is_reused(s3, sqs, env, analysis):
    """412 → HEAD 해시 일치 → 재사용(재 PUT 0). 동일 바이트면 안전하다."""
    s3.objects[(BUCKET, SRC_KEY)] = {"Body": SRC_PNG, "Metadata": {"sha256": SOURCE_HASH}}

    _enqueue()

    assert s3.puts == []  # 조건부 PUT 이 막혔고 재 PUT 도 없다
    assert _job(analysis)["state"] == "reserved"


def test_existing_object_hash_mismatch_blocks_everything(s3, sqs, env, analysis):
    """M4-04: 같은 key 에 다른 바이트 = collision/tampering → job 0, 벤더 호출 0."""
    s3.objects[(BUCKET, SRC_KEY)] = {"Body": b"other", "Metadata": {"sha256": "deadbeef"}}

    _enqueue()

    assert _job(analysis) == {}
    assert sqs.sent == []
    assert s3.deleted == []  # 남의 객체를 지우지도 않는다
    assert _object_doc(analysis) is None  # ownership 종료 경로 release 완료


def test_put_failure_releases_ownership_and_closes_reservation(s3, sqs, env, analysis):
    s3.put_error = "InternalError"

    _enqueue(request_id="req-x")

    assert _job(analysis) == {}
    assert _object_doc(analysis) is None
    assert _reservation(analysis, "req-x")["state"] == "closed"


def test_head_failure_after_precondition_blocks(s3, sqs, env, analysis):
    s3.objects[(BUCKET, SRC_KEY)] = {"Body": SRC_PNG, "Metadata": {"sha256": SOURCE_HASH}}
    s3.head_error = True

    _enqueue()

    assert _job(analysis) == {}
    assert sqs.sent == []


# ─────────────────────── reservation (B7-05 / B8-05 / B8-06) ───────────────────────


def test_reservation_created_before_put(s3, sqs, env, analysis, monkeypatch):
    """PUT 직후 SIGKILL 에도 janitor 가 회수할 수 있으려면 순서가 이래야 한다."""
    order: list[str] = []

    real_create = firestore_admin.create_input_reservation

    def _create(*a, **kw):
        order.append("reservation")
        return real_create(*a, **kw)

    original_put = s3.put_object

    def _put(**kw):
        order.append("put")
        return original_put(**kw)

    monkeypatch.setattr(firestore_admin, "create_input_reservation", _create)
    monkeypatch.setattr(s3, "put_object", _put)

    _enqueue()

    assert order[:2] == ["reservation", "put"]


def test_reservation_is_per_invocation_not_overwritten(s3, sqs, env, analysis):
    """B8-05: 동시 invocation 이 서로의 expectedKeys 를 잃으면 회수 대상에서 빠진다."""
    firestore_admin.create_input_reservation(
        JOB_ID,
        "req-a",
        owner="req-a",
        bucket=BUCKET,
        source_hash=SOURCE_HASH,
        expected_keys=["key-a"],
        now_ms=NOW_MS,
    )
    firestore_admin.create_input_reservation(
        JOB_ID,
        "req-b",
        owner="req-b",
        bucket=BUCKET,
        source_hash=SOURCE_HASH,
        expected_keys=["key-b"],
        now_ms=NOW_MS,
    )

    assert _reservation(analysis, "req-a")["expectedKeys"] == ["key-a"]
    assert _reservation(analysis, "req-b")["expectedKeys"] == ["key-b"]


def test_reservation_lost_means_producer_deletes_nothing(s3, sqs, env, analysis, monkeypatch):
    """B8-06: janitor 가 이미 회수했으면 내 삭제는 0 (남의 판단을 뒤집지 않는다)."""
    monkeypatch.setattr(
        firestore_admin,
        "reserve_visual_job",
        lambda *a, **kw: {"created": False, "reason": "reservation_lost"},
    )

    _enqueue()

    assert s3.deleted == []
    assert _job(analysis) == {}


def test_successful_reserve_promotes_ownership_to_job(s3, sqs, env, analysis):
    """승격된 job ref 는 만료되지 않는다 (B11-04) — 살아있는 job 의 입력 보호."""
    _enqueue(request_id="req-a")

    doc = _object_doc(analysis)
    assert doc is not None
    assert set(doc["refs"]) == {JOB_ID}
    assert doc["refs"][JOB_ID]["kind"] == "job"
    assert "expireAt" not in doc["refs"][JOB_ID]


def test_deleting_state_fences_new_producer(s3, sqs, env, analysis):
    """B11-01: 회수 중인 key 를 producer 가 되살리면 늦은 delete 가 새 입력을 지운다."""
    firestore_admin._doc(models.visual_input_object_doc_path(BUCKET, SRC_KEY)).set(
        {
            "bucket": BUCKET,
            "key": SRC_KEY,
            "state": "deleting",
            "refs": {},
            "generation": 1,
            "deleteOwner": "janitor",
            "deleteLeaseExpiresAt": 0,  # 만료됐어도 회수 금지
        }
    )

    _enqueue()

    assert s3.puts == []
    assert _job(analysis) == {}


# ─────────────────────── terminal replay / inputSealed (B6-03) ───────────────────────


def test_terminal_replay_deletes_this_invocation_input(s3, sqs, env, analysis, monkeypatch):
    """cleanup 이 끝난 job 뒤에 남은 새 입력 = 되살아난 PII → 즉시 삭제."""
    monkeypatch.setattr(
        firestore_admin,
        "reserve_visual_job",
        lambda *a, **kw: {"created": False, "job": {"state": "done", "inputSealed": True}},
    )

    _enqueue()

    assert (BUCKET, SRC_KEY) in s3.deleted
    # ownership 문서는 'deleting' tombstone 으로 남는다 — 31-09 janitor 와 동일 규약.
    # 이 tombstone 이 있어야 늦게 살아난 claimant 의 acquire 가 영구 차단된다(B11-01).
    doc = _object_doc(analysis)
    assert doc["state"] == "deleting"
    assert doc["refs"] == {}


def test_in_progress_job_input_is_not_deleted(s3, sqs, env, analysis, monkeypatch):
    """진행 중 job(inputSealed False)의 입력은 건드리지 않는다 — worker 가 쓰는 중."""
    monkeypatch.setattr(
        firestore_admin,
        "reserve_visual_job",
        lambda *a, **kw: {"created": False, "job": {"state": "creating", "inputSealed": False}},
    )

    _enqueue()

    assert s3.deleted == []


def test_loser_releases_its_ref_immediately(s3, sqs, env, analysis, monkeypatch):
    """B11-03: loser 가 ref 를 안 놓으면 winner 의 terminal cleanup 이 TTL 만큼 막힌다."""
    monkeypatch.setattr(
        firestore_admin,
        "reserve_visual_job",
        lambda *a, **kw: {"created": False, "job": {"state": "creating", "inputSealed": False}},
    )

    _enqueue(request_id="req-b")

    doc = _object_doc(analysis)
    assert doc is None or "req-b" not in (doc.get("refs") or {})
    assert _reservation(analysis, "req-b")["state"] == "closed"


def test_compensation_delete_goes_through_claim_and_commit(s3, sqs, env, analysis, monkeypatch):
    """B11-02: 같은 key 를 쓰는 다른 live ref 가 있으면 보상 삭제도 삭제 0.

    직접 delete_object 를 부르는 구현이면 여기서 남의 입력이 사라진다.
    """
    monkeypatch.setattr(
        firestore_admin,
        "reserve_visual_job",
        lambda *a, **kw: {"created": False, "job": {"state": "done", "inputSealed": True}},
    )
    # 다른 invocation(B)이 같은 key 에 live ref 를 갖고 있는 상태를 만든다.
    _enqueue(request_id="req-a")  # 먼저 객체/ownership 생성 후 삭제 시도
    s3.deleted.clear()

    firestore_admin.acquire_key_ownership(
        BUCKET,
        SRC_KEY,
        ref="req-b-live",
        kind="job",
        now_ms=NOW_MS,
    )

    _enqueue(request_id="req-c")

    assert s3.deleted == []  # live ref 존재 → 삭제 차단


def test_producer_never_calls_delete_object_directly():
    """B11-02 grep — 삭제 경로는 claim/commit 을 통과하는 한 곳뿐이어야 한다."""
    source = _APP.read_text(encoding="utf-8")
    visual_block = source[source.index("_CORRECTED_POSE_MAX_PUT_RETRY") :]
    # delete_object 호출은 _delete_owned_key 안의 1회뿐.
    assert visual_block.count("delete_object(") == 1
    assert "claim_key_for_delete" in visual_block
    assert "commit_key_delete" in visual_block


# ─────────────────────── orphan 보상 (H6-02 / H7-04) ───────────────────────


def test_analysis_missing_compensates_orphan_input(s3, sqs, env, fake_firestore, monkeypatch):
    """분석 문서가 없으면 job 이 안 생긴다 — 이번 입력은 확실한 고아."""
    _enqueue()

    assert (BUCKET, SRC_KEY) in s3.deleted
    assert _job(fake_firestore) == {}


def test_reserve_exception_keeps_input_when_job_actually_committed(
    s3, sqs, env, analysis, monkeypatch
):
    """commit 응답만 유실된 경우 — job 은 살아있으므로 그 입력을 지우면 안 된다."""

    def _boom(*a, **kw):
        firestore_admin._doc(models.visual_job_doc_path(JOB_ID)).set(
            {"state": "reserved", "srcKey": SRC_KEY}
        )
        raise RuntimeError("commit response lost")

    monkeypatch.setattr(firestore_admin, "reserve_visual_job", _boom)

    _enqueue()

    assert s3.deleted == []  # 살아있는 job 의 입력 보존


def test_reserve_exception_deletes_input_when_no_job(s3, sqs, env, analysis, monkeypatch):
    monkeypatch.setattr(
        firestore_admin,
        "reserve_visual_job",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    _enqueue()

    assert (BUCKET, SRC_KEY) in s3.deleted


def test_failed_compensation_delete_records_mandatory_orphan_doc(
    s3, sqs, env, analysis, monkeypatch
):
    """H7-04: '지우려다 실패했는데 아무도 모르는 PII' 를 만들지 않는다 — 옵션 아님."""
    monkeypatch.setattr(
        firestore_admin,
        "reserve_visual_job",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    def _fail_delete(**kw):
        raise RuntimeError("delete failed")

    monkeypatch.setattr(s3, "delete_object", _fail_delete)
    monkeypatch.setattr(app.boto3, "client", lambda *a, **kw: _NoopCW())

    _enqueue()

    orphans = [p for p in analysis.store if p.startswith("visualOrphans/")]
    assert len(orphans) == 1
    doc = analysis.store[orphans[0]]
    assert doc["bucket"] == BUCKET
    assert doc["key"] == SRC_KEY
    assert doc["state"] == "open"


class _NoopCW:
    def put_metric_data(self, **kw):
        return {}


# ─────────────────────── 발행 실패 = dispatcher 복구 (H3-09) ───────────────────────


def test_send_failure_leaves_pending_outbox(s3, sqs, env, analysis):
    sqs.fail = True

    _enqueue()

    job = _job(analysis)
    assert job["state"] == "reserved"
    assert job["dispatchState"] == "pending"  # dispatcher 가 재발행
    assert (BUCKET, SRC_KEY) in s3.objects  # 입력은 살아있어야 한다


def test_enqueue_never_raises(s3, sqs, env, analysis, monkeypatch):
    """분석은 이미 complete — 이 훅의 어떤 실패도 사용자 결과를 막지 않는다."""
    monkeypatch.setattr(
        firestore_admin,
        "read_visual_job",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("firestore down")),
    )

    _enqueue()  # 예외가 새어나오면 테스트 실패


def test_hook_does_not_import_visual_gen():
    """생성/판정은 worker 소유 — 분석 경로에서 벤더 모듈을 끌어오지 않는다.

    주석의 언급이 아니라 **실제 import/호출**을 본다.
    """
    source = _APP.read_text(encoding="utf-8")

    assert "import visual_gen" not in source
    assert "from sunity_shared.analysis import visual_gen" not in source
    assert "dashscope-intl" not in source
    assert "generate_corrected_pose" not in source
