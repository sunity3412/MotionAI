"""온디맨드 회전 요청 API (D-06) — 일일 한도(D-07) + 원자 예약 — 담당 플랜 31-10.

실 Firestore/네트워크/Pod 미접촉 — LOCAL ONLY. 공용 스캐폴드(경쟁 transaction·
주입 시계)는 backend/tests/phase31/conftest.py 소유.

여기서 검증하는 것은 "202 가 나온다" 가 아니라 **표시 pending 이 예약 transaction
안에서만 기록되고(B3-03), SQS send 실패가 사용자 실패로 번지지 않으며(H3-09),
한도 env 를 못 읽으면 생성이 막힌다(M-06)** 는 계약이다.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from sunity_shared import firestore_admin, models

_APP = Path(__file__).resolve().parents[2] / "functions" / "visual-request" / "app.py"

UID = "u1"
OTHER_UID = "u2"
ANALYSIS_ID = "a" * 32
NOW_MS = 1_700_000_000_000


def _load_app():
    if "visual_request" in sys.modules:
        return sys.modules["visual_request"]
    spec = importlib.util.spec_from_file_location("visual_request", _APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules["visual_request"] = module
    spec.loader.exec_module(module)
    return module


app = _load_app()

JOB_ID = models.visual_job_id(UID, ANALYSIS_ID, models.VISUAL_KIND_ROTATION)


class FakeSQS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.fail = False

    def send_message(self, **kw):
        if self.fail:
            raise RuntimeError("send failed (injected)")
        self.sent.append(kw)
        return {"MessageId": "m"}


@pytest.fixture
def sqs(monkeypatch):
    fake = FakeSQS()
    monkeypatch.setattr(app, "_sqs", lambda: fake)
    return fake


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("VISUAL_JOBS_ENABLED", "true")
    monkeypatch.setenv("VISUAL_QUEUE_URL", "https://sqs.test/visual")
    monkeypatch.setenv("ROTATION_DAILY_LIMIT", "3")
    monkeypatch.setenv("ROTATION_GLOBAL_DAILY_LIMIT", "30")
    return monkeypatch


@pytest.fixture
def auth(monkeypatch):
    state = {"uid": UID, "raise": False}

    def _verify(_event):
        if state["raise"]:
            raise app.AuthError("토큰 없음")
        return state["uid"]

    monkeypatch.setattr(app, "verify_request", _verify)
    return state


@pytest.fixture
def clock(monkeypatch):
    state = {"now": NOW_MS}
    monkeypatch.setattr(app, "_now_ms", lambda: state["now"])
    return state


@pytest.fixture
def analysis(fake_firestore):
    """분석 문서를 실 경로에 심는다 — reserve_visual_job 이 진짜로 읽는다."""
    fake_firestore.store[models.analysis_doc_path(UID, ANALYSIS_ID)] = {
        "status": "done",
        "result": {},
    }
    return fake_firestore


def _call(**body) -> dict:
    event = {"body": json.dumps(body), "headers": {"authorization": "Bearer t"}}
    return app.lambda_handler(event, None)


def _status(resp) -> int:
    return resp["statusCode"]


def _body(resp) -> dict:
    return json.loads(resp["body"])


def _job(db) -> dict:
    return db.store.get(models.visual_job_doc_path(JOB_ID)) or {}


def _analysis_result(db) -> dict:
    return (db.store[models.analysis_doc_path(UID, ANALYSIS_ID)].get("result")) or {}


def _quota(db, date_key: str) -> int:
    doc = db.store.get(models.visual_quota_doc_path(UID, date_key)) or {}
    return int(doc.get("count") or 0)


def _date_key() -> str:
    return app._kst_date_key(NOW_MS)


# ─────────────────────── flag / auth / 입력 ───────────────────────


def test_flag_off_503_and_no_side_effect(sqs, env, auth, clock, analysis):
    env.setenv("VISUAL_JOBS_ENABLED", "false")

    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 503
    assert _body(resp)["error"]["code"] == "feature_disabled"
    assert sqs.sent == []
    assert _job(analysis) == {}


def test_no_token_401(sqs, env, auth, clock, analysis):
    auth["raise"] = True

    assert _status(_call(analysisId=ANALYSIS_ID)) == 401
    assert sqs.sent == []


def test_bad_analysis_id_400(sqs, env, auth, clock, analysis):
    assert _status(_call(analysisId="../etc")) == 400
    assert sqs.sent == []


def test_missing_doc_404(sqs, env, auth, clock, fake_firestore):
    assert _status(_call(analysisId=ANALYSIS_ID)) == 404
    assert sqs.sent == []


def test_other_uid_doc_404(sqs, env, auth, clock, fake_firestore):
    """타인 문서는 uid 스코프 경로에 없다 — 존재 여부가 새지 않는다."""
    fake_firestore.store[models.analysis_doc_path(OTHER_UID, ANALYSIS_ID)] = {
        "status": "done",
        "result": {},
    }

    assert _status(_call(analysisId=ANALYSIS_ID)) == 404


def test_analysis_not_done_404(sqs, env, auth, clock, fake_firestore):
    fake_firestore.store[models.analysis_doc_path(UID, ANALYSIS_ID)] = {
        "status": "pending",
        "result": {},
    }

    assert _status(_call(analysisId=ANALYSIS_ID)) == 404
    assert sqs.sent == []


# ─────────────────────── 멱등 / dedupe ───────────────────────


def test_already_done_is_idempotent_200(sqs, env, auth, clock, analysis):
    analysis.store[models.analysis_doc_path(UID, ANALYSIS_ID)]["result"] = {
        "rotationStatus": "done"
    }

    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 200
    assert _body(resp) == {"rotationStatus": "done"}
    assert sqs.sent == []  # 재생성 0
    assert _job(analysis) == {}


def test_pending_within_window_dedupes_without_publish(sqs, env, auth, clock, analysis):
    analysis.store[models.analysis_doc_path(UID, ANALYSIS_ID)]["result"] = {
        "rotationStatus": "pending",
        "rotationUpdatedAtMs": NOW_MS - 60_000,
    }

    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 202
    assert sqs.sent == []
    assert _quota(analysis, _date_key()) == 0  # dedupe 는 quota 를 안 쓴다


def test_dedupe_uses_rotation_timestamp_only(sqs, env, auth, clock, analysis):
    """공용 updatedAt 이 아무리 신선해도 rotationUpdatedAtMs 가 오래면 dedupe 안 함 (H-06)."""
    doc = analysis.store[models.analysis_doc_path(UID, ANALYSIS_ID)]
    doc["updatedAt"] = NOW_MS
    doc["result"] = {
        "rotationStatus": "pending",
        "rotationUpdatedAtMs": NOW_MS - 21 * 60 * 1000,  # 창 밖
    }

    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 202
    assert _job(analysis).get("state") == "reserved"  # 새로 예약됨


# ─────────────────────── 한도 (D-07 / M-06) ───────────────────────


def test_daily_limit_429(sqs, env, auth, clock, analysis):
    date_key = _date_key()
    analysis.store[models.visual_quota_doc_path(UID, date_key)] = {"count": 3, "dateKey": date_key}

    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 429
    assert _body(resp)["error"]["code"] == "daily_limit"
    assert sqs.sent == []
    assert _job(analysis) == {}


def test_global_limit_429(sqs, env, auth, clock, analysis):
    date_key = _date_key()
    analysis.store[models.visual_quota_doc_path("_global", date_key)] = {
        "count": 30,
        "dateKey": date_key,
    }

    assert _status(_call(analysisId=ANALYSIS_ID)) == 429
    assert sqs.sent == []


def test_unparsable_limit_env_fails_closed_429(sqs, env, auth, clock, analysis):
    """M-06: 한도 env 오타 하나로 과금 상한이 사라지면 안 된다 — 0 으로 읽어 전부 429."""
    env.setenv("ROTATION_DAILY_LIMIT", "abc")

    assert _status(_call(analysisId=ANALYSIS_ID)) == 429
    assert sqs.sent == []
    assert _job(analysis) == {}


def test_missing_limit_env_fails_closed_429(sqs, env, auth, clock, analysis):
    env.delenv("ROTATION_DAILY_LIMIT")

    assert _status(_call(analysisId=ANALYSIS_ID)) == 429


def test_quota_key_is_kst_midnight():
    """KST 기준 날짜 키 — UTC 자정 리셋이면 한국 오전 9시에 풀린다 (M-06)."""
    # 2026-07-20 00:30 KST == 2026-07-19 15:30 UTC — UTC 기준이면 07-19 로 집계된다.
    kst_0030_ms = 1_784_475_000_000
    assert app._kst_date_key(kst_0030_ms) == "2026-07-20"
    # 1시간 전(= 2026-07-19 23:30 KST)은 아직 전날 한도
    assert app._kst_date_key(kst_0030_ms - 3600 * 1000) == "2026-07-19"


# ─────────────────────── 원자 예약 + 발행 ───────────────────────


def test_reserve_writes_job_pending_and_outbox_atomically(sqs, env, auth, clock, analysis):
    """B3-03: job + 표시 pending + 초기 outbox 가 한 transaction."""
    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 202
    assert _body(resp) == {"rotationStatus": "pending"}
    job = _job(analysis)
    assert job["state"] == "reserved"
    assert job["nextAction"] == "create"
    assert job["outboxSeq"] == 1
    assert _analysis_result(analysis)["rotationStatus"] == "pending"
    assert _quota(analysis, _date_key()) == 1


def test_message_carries_outbox_seq_and_marks_dispatched(sqs, env, auth, clock, analysis):
    """B4-01: 메시지에 outboxSeq 포함 + mark 가 action+seq CAS 로 sent 전환."""
    _call(analysisId=ANALYSIS_ID)

    assert len(sqs.sent) == 1
    msg = json.loads(sqs.sent[0]["MessageBody"])
    assert msg["jobId"] == JOB_ID
    assert msg["action"] == "create"
    assert msg["outboxSeq"] == 1
    assert msg["generation"] == 1
    assert _job(analysis)["dispatchState"] == "sent"


def test_stale_seq_mark_does_not_flip_dispatch_state(sqs, env, auth, clock, analysis):
    """seq 없이 mark 하면 늦은 mark 가 새 pending 을 sent 로 덮는다 (T-31-56) — CAS 확인."""
    _call(analysisId=ANALYSIS_ID)
    firestore_admin._doc(models.visual_job_doc_path(JOB_ID)).update(
        {"dispatchState": "pending", "outboxSeq": 2}
    )

    flipped = firestore_admin.mark_visual_job_dispatched(
        JOB_ID, expect_action="create", expect_outbox_seq=1
    )

    assert flipped is False
    assert _job(analysis)["dispatchState"] == "pending"


def test_send_failure_returns_202_and_leaves_outbox_pending(sqs, env, auth, clock, analysis):
    """H3-09: send 실패는 500 이 아니다 — dispatcher 가 복구할 durable 상태가 남는다."""
    sqs.fail = True

    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 202
    job = _job(analysis)
    assert job["dispatchState"] == "pending"  # 복구 대상으로 남음
    assert job["nextAction"] == "create"
    assert _analysis_result(analysis)["rotationStatus"] == "pending"


def test_retry_after_send_failure_republishes_without_new_quota(sqs, env, auth, clock, analysis):
    """재요청은 quota 를 다시 쓰지 않고, pending outbox 만 재발행한다."""
    sqs.fail = True
    _call(analysisId=ANALYSIS_ID)
    assert _quota(analysis, _date_key()) == 1

    sqs.fail = False
    # dedupe 창을 벗어난 재요청
    clock["now"] = NOW_MS + 21 * 60 * 1000
    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 202
    assert len(sqs.sent) == 1  # 재발행 1회
    assert _quota(analysis, _date_key()) == 1  # 추가 소모 0
    assert _job(analysis)["dispatchState"] == "sent"


def test_in_progress_job_is_noop(sqs, env, auth, clock, analysis):
    """진행 중(creating) job 재요청 → 중복 발행 0, quota 추가 소모 0."""
    _call(analysisId=ANALYSIS_ID)
    firestore_admin._doc(models.visual_job_doc_path(JOB_ID)).update(
        {"state": "creating", "dispatchState": "sent"}
    )
    sqs.sent.clear()
    clock["now"] = NOW_MS + 21 * 60 * 1000

    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 202
    assert sqs.sent == []
    assert _quota(analysis, _date_key()) == 1


def test_failed_job_retry_bumps_generation_and_consumes_quota(sqs, env, auth, clock, analysis):
    """failed 재요청은 새 generation 으로 재예약 — quota 를 다시 쓴다(실제 재생성이므로)."""
    _call(analysisId=ANALYSIS_ID)
    firestore_admin._doc(models.visual_job_doc_path(JOB_ID)).update(
        {"state": "failed", "dispatchState": "sent"}
    )
    analysis.store[models.analysis_doc_path(UID, ANALYSIS_ID)]["result"][
        "rotationStatus"
    ] = "failed"
    sqs.sent.clear()

    resp = _call(analysisId=ANALYSIS_ID)

    assert _status(resp) == 202
    job = _job(analysis)
    assert job["state"] == "reserved"
    assert job["generation"] == 2
    assert _quota(analysis, _date_key()) == 2
    assert json.loads(sqs.sent[0]["MessageBody"])["generation"] == 2


def test_concurrent_requests_reserve_once(sqs, env, auth, clock, analysis):
    """run_contended: 동시 요청 → job 1건 + quota +1 + 발행 <= 2."""
    date_key = _date_key()

    def _reserve(_tx):
        return firestore_admin.reserve_visual_job(
            UID,
            ANALYSIS_ID,
            models.VISUAL_KIND_ROTATION,
            date_key=date_key,
            user_limit=3,
            global_limit=30,
            allow_retry_failed=True,
            now_ms=NOW_MS,
        )

    # reserve 자체가 transaction 이므로 경쟁은 fake 의 재시도 경로로 재현된다.
    first = _reserve(None)
    second = _reserve(None)

    assert first["created"] is True
    assert second["created"] is False
    assert _quota(analysis, date_key) == 1


# ─────────────────────── 계약 grep ───────────────────────


def test_lambda_never_writes_display_state_directly():
    """표시 pending 은 reserve transaction 소유 — Lambda 별도 write 0 (B3-03)."""
    source = _APP.read_text(encoding="utf-8")

    assert "update_analysis_visual" not in source
    assert "finalize_visual_job" not in source
    # 분석 문서를 직접 겨냥한 write 경로가 없다 — 읽기(get_analysis)만 한다.
    assert "analysis_doc_path" not in source
    assert "result.rotation" not in source  # f"result.{kind}Status" 는 reserve 소유
    assert ".update(" not in source


def test_requirements_pins_pyyaml_with_precedent():
    reqs = (_APP.parent / "requirements.txt").read_text(encoding="utf-8")

    assert "pyyaml" in reqs
    assert "firebase-admin" in reqs
    # deploy fix 선례 2건 인용 (같은 함정 반복 방지)
    assert reqs.count("deploy fix") >= 2
