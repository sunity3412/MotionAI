"""visual job 데이터 계약 (상태·outbox·claim·finalize·dispatcher) — 담당 플랜 31-02.

실 Firestore/네트워크/Pod 미접촉 — LOCAL ONLY. in-memory Firestore 는 문서 version 을
실제로 검사하므로 CAS/경쟁은 "mock 이 통과시켜 주는" 게 아니라 진짜 conflict/재시도로
재현된다 (backend/tests/phase31/conftest.py 소유).

리뷰 근거: B3-01/02/03, B4-01/03, B5-01, H5-03~06, B6-01/04, H6-01/07, B7-03/04,
B8-01~06, B9-01/02, H9-01/04/07, B10-01~03, H10-01, B11-01/04.
"""

from __future__ import annotations

import pytest

from sunity_shared import firestore_admin, models

UID = "u1"
AID = "a1"
ROT = models.VISUAL_KIND_ROTATION
CP = models.VISUAL_KIND_CORRECTED_POSE
LEASE = models.VISUAL_CLAIM_LEASE_MS
T0 = 1_700_000_000_000


def _seed_analysis(uid: str = UID, aid: str = AID) -> None:
    firestore_admin._doc(models.analysis_doc_path(uid, aid)).set(
        {"status": "done", "updatedAt": 1, "result": {"overallScore": 80}}
    )


def _analysis(uid: str = UID, aid: str = AID) -> dict:
    return firestore_admin._doc(models.analysis_doc_path(uid, aid)).get().to_dict()


def _job(job_id: str) -> dict | None:
    return firestore_admin.read_visual_job(job_id)


def _reserve(kind: str = ROT, **kw) -> dict:
    kw.setdefault("now_ms", T0)
    return firestore_admin.reserve_visual_job(UID, AID, kind, **kw)


def _capture_tx(monkeypatch, fake, call):
    """_run_in_transaction 을 가로채 transaction 함수만 뽑아낸다(실행 없이).

    같은 pre-state 를 읽는 두 워커의 **진짜 interleave** 를 만들기 위해 필요하다 —
    순차 호출은 두 번째가 첫 commit 결과를 보게 되어 경쟁이 아니다.
    """
    captured = []
    monkeypatch.setattr(
        firestore_admin, "_run_in_transaction", lambda fn: captured.append(fn) or None
    )
    call()
    monkeypatch.setattr(firestore_admin, "_run_in_transaction", fake.run_in_transaction)
    return captured[0]


# ══════════════════════ seam 무결성 ══════════════════════


def test_all_firestore_seams_exist(fake_firestore):
    """conftest 가 patch 하는 seam 이름이 전부 실제로 존재하는지 (오타 seam 방지)."""
    assert fake_firestore.missing_seams == ()


# ══════════════════════ reserve (B3-03 / T-31-05) ══════════════════════


def test_reserve_writes_job_and_analysis_pending_atomically(fake_firestore):
    _seed_analysis()
    out = _reserve()
    assert out["created"] is True

    job_id = models.visual_job_id(UID, AID, ROT)
    job = _job(job_id)
    assert job["state"] == "reserved"
    # 초기 outbox — 예약 즉시 dispatch 가능해야 한다.
    assert (job["nextAction"], job["dispatchState"], job["outboxSeq"]) == ("create", "pending", 1)
    # claim 초기값은 clear 상태 (B6-01) — create 가 owner CAS 에 막히지 않는다.
    assert (job["claimState"], job["claimOwner"], job["claimLeaseExpiresAt"]) == (None, None, 0)
    assert job["claimedOutboxSeq"] == 0
    # privacy 초기값 (B6-03/B6-04).
    assert job["inputSealed"] is False
    assert job["privacyBlocker"] is None
    assert job["cleanupVerifiedAtMs"] == 0
    # 표시 상태는 같은 transaction 에서 pending.
    assert _analysis()["result"][f"{ROT}Status"] == "pending"
    assert fake_firestore.commit_count == 1


def test_reserve_returns_analysis_missing_and_writes_nothing(fake_firestore):
    out = _reserve()
    assert out == {"created": False, "reason": "analysis_missing"}
    assert _job(models.visual_job_id(UID, AID, ROT)) is None


def test_reserve_is_idempotent_and_consumes_quota_once(fake_firestore):
    _seed_analysis()
    first = _reserve(date_key="20260720", user_limit=5)
    second = _reserve(date_key="20260720", user_limit=5)
    assert first["created"] is True
    assert second["created"] is False
    assert second["job"]["state"] == "reserved"  # 호출측 분기 근거 (B2-03).
    counter = firestore_admin._doc(models.visual_quota_doc_path(UID, "20260720")).get().to_dict()
    assert counter["count"] == 1


def test_reserve_enforces_daily_limit(fake_firestore):
    _seed_analysis()
    firestore_admin._doc(models.visual_quota_doc_path(UID, "20260720")).set({"count": 3})
    out = _reserve(date_key="20260720", user_limit=3)
    assert out == {"created": False, "reason": "daily_limit"}
    assert _job(models.visual_job_id(UID, AID, ROT)) is None


def test_reserve_retry_of_failed_job_bumps_generation_and_resets_outbox(fake_firestore):
    _seed_analysis()
    _reserve()
    job_id = models.visual_job_id(UID, AID, ROT)
    firestore_admin._doc(models.visual_job_doc_path(job_id)).set(
        {
            "state": "failed",
            "failureReason": "moderation",
            "generation": 1,
            "outboxSeq": 7,
            "claimState": "claimed",
            "claimOwner": "old",
            "claimLeaseExpiresAt": T0 + 999,
            "privacyBlocker": "cleanup_blocked",
            "inputSealed": True,
        },
        merge=True,
    )
    out = _reserve(allow_retry_failed=True)
    assert out["created"] is True
    job = _job(job_id)
    assert job["generation"] == 2
    assert (job["state"], job["outboxSeq"], job["dispatchState"]) == ("reserved", 1, "pending")
    assert (job["claimState"], job["claimOwner"], job["claimLeaseExpiresAt"]) == (None, None, 0)
    assert job["privacyBlocker"] is None and job["inputSealed"] is False
    assert job["failureReason"] is None


def test_reserve_without_retry_flag_does_not_revive_failed_job(fake_firestore):
    _seed_analysis()
    _reserve()
    job_id = models.visual_job_id(UID, AID, ROT)
    firestore_admin._doc(models.visual_job_doc_path(job_id)).set({"state": "failed"}, merge=True)
    out = _reserve(allow_retry_failed=False)
    assert out["created"] is False and out["job"]["state"] == "failed"


def test_concurrent_reserve_creates_one_job_and_one_quota_unit(fake_firestore, monkeypatch):
    """T-31-05 — 이중 소비/고아 quota 불가. 진짜 interleave 로 검증."""
    _seed_analysis()
    fn_a = _capture_tx(
        monkeypatch, fake_firestore, lambda: _reserve(date_key="20260720", user_limit=5)
    )
    fn_b = _capture_tx(
        monkeypatch, fake_firestore, lambda: _reserve(date_key="20260720", user_limit=5)
    )
    res_a, res_b = fake_firestore.run_contended(fn_a, fn_b)

    assert res_a["created"] is True
    assert res_b["created"] is False  # 재시도 시 이미 존재하는 job 을 본다.
    counter = firestore_admin._doc(models.visual_quota_doc_path(UID, "20260720")).get().to_dict()
    assert counter["count"] == 1
    assert fake_firestore.conflict_count == 1


def test_reserve_reads_everything_before_writing_anything(fake_firestore):
    """H9-04 — job + reservation + 두 key 승격이 단일 commit 단위이려면 read-all-before-write.

    Firestore transaction 은 write 이후의 read 를 허용하지 않는다. nested @transactional
    로 reservation claim 을 부르면 이 규율이 깨져 부분 commit 이 가능해진다.
    """
    _seed_analysis()
    _make_reservation(keys=(K1, K2))
    out = firestore_admin.reserve_visual_job(
        UID, AID, CP, reservation_id="res-1", reservation_owner="p1", now_ms=T0
    )
    assert out["created"] is True
    assert fake_firestore.read_after_write_seen is False


def test_reserve_rejects_nested_payload(fake_firestore):
    _seed_analysis()
    with pytest.raises(TypeError):
        _reserve(payload={"joint": "knee", "nested": {"a": 1}})


# ══════════════════════ transition (B4-01 / B6-01 / H5-03 / H6-07) ══════════════════════


def _reserved_job(kind: str = ROT) -> str:
    _seed_analysis()
    _reserve(kind)
    return models.visual_job_id(UID, AID, kind)


def _force(job_id: str, **fields) -> None:
    firestore_admin._doc(models.visual_job_doc_path(job_id)).set(fields, merge=True)


def test_transition_returns_snapshot_and_bumps_outbox_seq(fake_firestore):
    job_id = _reserved_job()
    _force(job_id, state="creating", outboxSeq=4, taskId=None)

    snap = firestore_admin.transition_visual_job(
        job_id,
        expect_states=("creating",),
        updates={"state": "polling", "taskId": "t-1"},
        next_action="poll",
        expect_outbox_seq=4,
        now_ms=T0,
        next_dispatch_at_ms=T0 + 5_000,
    )
    assert snap["state"] == "polling"
    assert snap["outboxSeq"] == 5
    assert snap["nextAction"] == "poll"
    assert snap["dispatchState"] == "pending"
    assert snap["nextDispatchAtMs"] == T0 + 5_000
    assert _job(job_id)["outboxSeq"] == 5


def test_transition_clears_claim_fields_on_new_outbox_seq(fake_firestore):
    """B6-01 — 새 seq 는 다음 action 을 위해 claim 을 비운다. audit seq 는 이전 값."""
    job_id = _reserved_job()
    _force(
        job_id,
        state="polling",
        outboxSeq=4,
        taskId="t-1",
        claimState="claimed",
        claimOwner="w1",
        claimLeaseExpiresAt=T0 + LEASE,
        claimedOutboxSeq=4,
    )
    snap = firestore_admin.transition_visual_job(
        job_id,
        expect_states=("polling",),
        updates={"state": "fetching"},
        next_action="fetch",
        expect_outbox_seq=4,
        expect_claim_owner="w1",
        now_ms=T0,
    )
    assert (snap["claimState"], snap["claimOwner"], snap["claimLeaseExpiresAt"]) == (None, None, 0)
    assert snap["claimedOutboxSeq"] == 4  # audit 유지
    assert snap["outboxSeq"] == 5
    assert snap["claimedOutboxSeq"] != snap["outboxSeq"]


def test_transition_rejects_terminal_state(fake_firestore):
    job_id = _reserved_job()
    with pytest.raises(ValueError, match="finalize_visual_job"):
        firestore_admin.transition_visual_job(
            job_id,
            expect_states=("reserved",),
            updates={"state": "done"},
            next_action=None,
            expect_outbox_seq=1,
        )


def test_transition_requires_next_action_for_nonterminal_except_creating(fake_firestore):
    job_id = _reserved_job()
    _force(job_id, state="creating", outboxSeq=2, taskId="t-1")
    with pytest.raises(ValueError, match="next_action 필수"):
        firestore_admin.transition_visual_job(
            job_id,
            expect_states=("creating",),
            updates={"state": "polling"},
            next_action=None,
            expect_outbox_seq=2,
        )


def test_transition_polling_requires_task_id(fake_firestore):
    job_id = _reserved_job()
    _force(job_id, state="creating", outboxSeq=2, taskId=None)
    with pytest.raises(ValueError, match="taskId 필수"):
        firestore_admin.transition_visual_job(
            job_id,
            expect_states=("creating",),
            updates={"state": "polling"},
            next_action="poll",
            expect_outbox_seq=2,
        )


def test_transition_creating_requires_lease(fake_firestore):
    job_id = _reserved_job()
    with pytest.raises(ValueError, match="leaseOwner/leaseExpiresAt"):
        firestore_admin.transition_visual_job(
            job_id,
            expect_states=("reserved",),
            updates={"state": "creating"},
            next_action=None,
            expect_outbox_seq=1,
        )


def test_transition_postprocessing_requires_postprocess_action(fake_firestore):
    job_id = _reserved_job(CP)
    _force(job_id, state="pose_checking", outboxSeq=3)
    with pytest.raises(ValueError, match="postprocess"):
        firestore_admin.transition_visual_job(
            job_id,
            expect_states=("pose_checking",),
            updates={"state": "postprocessing"},
            next_action="fetch",
            expect_outbox_seq=3,
        )


def test_retry_ready_to_creating_forces_task_id_none(fake_firestore):
    job_id = _reserved_job()
    _force(job_id, state="retry_ready", outboxSeq=6, generation=2, taskId=None)
    with pytest.raises(ValueError, match="taskId=None"):
        firestore_admin.transition_visual_job(
            job_id,
            expect_states=("retry_ready",),
            updates={
                "state": "creating",
                "taskId": "leftover",
                "leaseOwner": "w1",
                "leaseExpiresAt": T0 + LEASE,
            },
            next_action=None,
            expect_outbox_seq=6,
        )


def test_retry_ready_to_creating_mints_request_key_for_new_generation(fake_firestore):
    """H5-03 — 옛 generation 의 멱등키가 새 세대로 새면 벤더가 이전 결과를 돌려준다."""
    job_id = _reserved_job()
    _force(job_id, state="retry_ready", outboxSeq=6, generation=2, taskId=None)
    snap = firestore_admin.transition_visual_job(
        job_id,
        expect_states=("retry_ready",),
        updates={
            "state": "creating",
            "leaseOwner": "w1",
            "leaseExpiresAt": T0 + LEASE,
            "requestKey": f"{job_id}:gen1",  # caller 제공값은 무시돼야 한다.
        },
        next_action=None,
        expect_outbox_seq=6,
        now_ms=T0,
    )
    assert snap["generation"] == 3
    assert snap["requestKey"] == f"{job_id}:gen3"
    assert snap["dispatchState"] is None and snap["nextAction"] is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expect_generation": 99},
        {"expect_outbox_seq": 99},
    ],
)
def test_transition_cas_mismatch_returns_none_without_writing(fake_firestore, kwargs):
    job_id = _reserved_job()
    _force(job_id, state="polling", outboxSeq=4, taskId="t-1", generation=1)
    before = _job(job_id)
    call = {
        "expect_states": ("polling",),
        "updates": {"state": "fetching"},
        "next_action": "fetch",
        "expect_outbox_seq": 4,
    }
    call.update(kwargs)
    assert firestore_admin.transition_visual_job(job_id, **call) is None
    assert _job(job_id) == before


def test_transition_rejects_write_from_worker_that_lost_the_claim(fake_firestore):
    """T-31-70 — 재claim 당한 늦은 worker 의 결과 write 차단."""
    job_id = _reserved_job()
    _force(
        job_id,
        state="polling",
        outboxSeq=4,
        taskId="t-1",
        claimState="claimed",
        claimOwner="w2",  # 이미 w2 가 재claim.
        claimLeaseExpiresAt=T0 + LEASE,
        claimedOutboxSeq=4,
    )
    assert (
        firestore_admin.transition_visual_job(
            job_id,
            expect_states=("polling",),
            updates={"state": "fetching"},
            next_action="fetch",
            expect_outbox_seq=4,
            expect_claim_owner="w1",
            now_ms=T0,
        )
        is None
    )


def test_transition_rejects_write_after_lease_expiry_even_for_same_owner(fake_firestore):
    """H6-07 — owner 가 맞아도 lease 가 만료됐으면 남이 이미 가져갔을 수 있다."""
    job_id = _reserved_job()
    _force(
        job_id,
        state="polling",
        outboxSeq=4,
        taskId="t-1",
        claimState="claimed",
        claimOwner="w1",
        claimLeaseExpiresAt=T0,
        claimedOutboxSeq=4,
    )
    assert (
        firestore_admin.transition_visual_job(
            job_id,
            expect_states=("polling",),
            updates={"state": "fetching"},
            next_action="fetch",
            expect_outbox_seq=4,
            expect_claim_owner="w1",
            now_ms=T0,  # now >= lease → 만료.
        )
        is None
    )


# ══════════════════════ claim 4상태 (B5-01 / B6-01 / T-31-62) ══════════════════════


def _pollable(job_id: str, **extra) -> None:
    base = dict(
        state="polling", outboxSeq=4, generation=1, nextAction="poll", taskId="t-1",
        claimedOutboxSeq=0, claimState=None, claimOwner=None, claimLeaseExpiresAt=0,
    )
    base.update(extra)
    _force(job_id, **base)


def _claim(job_id, owner="w1", now_ms=T0, seq=4, gen=1, action="poll"):
    return firestore_admin.claim_visual_job_action(
        job_id, generation=gen, action=action, outbox_seq=seq, owner=owner,
        lease_ms=LEASE, now_ms=now_ms,
    )


def test_claim_unclaimed_returns_claimed_with_updated_snapshot(fake_firestore):
    job_id = _reserved_job()
    _pollable(job_id)
    out = _claim(job_id)
    assert out["status"] == "claimed"
    # 반환 snapshot 이 owner handoff 의 유일 출처 (B6-01).
    assert out["job"]["claimOwner"] == "w1"
    assert out["job"]["claimedOutboxSeq"] == 4
    assert out["job"]["claimLeaseExpiresAt"] == T0 + LEASE
    assert _job(job_id)["claimState"] == "claimed"


def test_claim_same_seq_with_live_lease_is_busy(fake_firestore, fake_clock):
    """중복 전달이 유료 action 을 두 번 태우지 못하게 — busy 는 정상 ACK 금지."""
    job_id = _reserved_job()
    _pollable(job_id)
    assert _claim(job_id, owner="w1", now_ms=fake_clock())["status"] == "claimed"
    fake_clock.advance(LEASE - 1)  # lease 만료 직전.
    out = _claim(job_id, owner="w2", now_ms=fake_clock())
    assert out["status"] == "busy"
    assert out["job"]["claimOwner"] == "w1"  # 무변경.


def test_claim_same_seq_after_lease_expiry_is_reclaimable(fake_firestore, fake_clock):
    job_id = _reserved_job()
    _pollable(job_id)
    _claim(job_id, owner="w1", now_ms=fake_clock())
    fake_clock.advance(LEASE + 1)  # lease 만료 직후.
    out = _claim(job_id, owner="w2", now_ms=fake_clock())
    assert out["status"] == "claimed"
    assert out["job"]["claimOwner"] == "w2"


@pytest.mark.parametrize(
    # seq 는 **앞선 값**만 stale 이다 — job 이 이미 지나친 seq(arg < job)는 'completed'
    # 로 분류된다(아래 별도 테스트). 둘을 같은 통에 넣으면 계약이 흐려진다.
    "kw", [{"gen": 2}, {"action": "fetch"}, {"seq": 9}]
)
def test_claim_mismatch_is_stale(fake_firestore, kw):
    job_id = _reserved_job()
    _pollable(job_id)
    assert _claim(job_id, **kw)["status"] == "stale"


@pytest.mark.parametrize(
    "extra,arg_seq",
    [
        ({"outboxSeq": 9}, 4),  # 이미 다음 instance 로 진행.
        ({"state": "done"}, 4),  # terminal.
    ],
)
def test_claim_already_advanced_or_terminal_is_completed(fake_firestore, extra, arg_seq):
    job_id = _reserved_job()
    _pollable(job_id, **extra)
    assert _claim(job_id, seq=arg_seq)["status"] == "completed"


def test_claim_does_not_judge_on_claimed_seq_alone(fake_firestore):
    """B5-01 박제 — claimedOutboxSeq 만 같고 lease/owner 가 없으면 재claim 가능해야 한다."""
    job_id = _reserved_job()
    _pollable(job_id, claimedOutboxSeq=4, claimState=None, claimOwner=None, claimLeaseExpiresAt=0)
    assert _claim(job_id, owner="w9")["status"] == "claimed"


# ══════════════════════ mark dispatched (B4-01 / T-31-56) ══════════════════════


def test_mark_dispatched_requires_generation_action_and_seq(fake_firestore):
    job_id = _reserved_job()
    _force(job_id, dispatchState="pending", nextAction="poll", outboxSeq=4, generation=1)
    assert firestore_admin.mark_visual_job_dispatched(
        job_id, expect_action="poll", expect_outbox_seq=4, expect_generation=1
    )
    assert _job(job_id)["dispatchState"] == "sent"


@pytest.mark.parametrize(
    "kw", [{"expect_action": "fetch"}, {"expect_outbox_seq": 3}, {"expect_generation": 2}]
)
def test_late_mark_from_previous_action_cannot_clobber_next_continuation(fake_firestore, kw):
    """이전 action 의 늦은 mark 가 새 continuation 의 pending 을 'sent' 로 덮으면
    dispatcher 가 영영 재발행하지 않는다."""
    job_id = _reserved_job()
    _force(job_id, dispatchState="pending", nextAction="poll", outboxSeq=4, generation=1)
    call = {"expect_action": "poll", "expect_outbox_seq": 4, "expect_generation": 1}
    call.update(kw)
    assert firestore_admin.mark_visual_job_dispatched(job_id, **call) is False
    assert _job(job_id)["dispatchState"] == "pending"


# ══════════════════════ begin_visual_job_create (B8-01 / T-31-85) ══════════════════════


def _begin(job_id, owner="w1", now_ms=T0, gen=1, seq=1):
    return firestore_admin.begin_visual_job_create(
        job_id, expect_generation=gen, expect_outbox_seq=seq,
        now_ms=now_ms, owner=owner, lease_ms=LEASE,
    )


def test_begin_create_acquires_and_writes_full_set(fake_firestore):
    job_id = _reserved_job()
    out = _begin(job_id)
    assert out["status"] == "acquired"
    job = out["job"]
    assert job["state"] == "creating"
    assert job["leaseOwner"] == "w1" and job["leaseExpiresAt"] == T0 + LEASE
    assert job["requestKey"] == f"{job_id}:gen1"
    # H9-03 full write set — 옛 create 메시지가 즉시 stale 이 되도록 seq 를 올린다.
    assert job["outboxSeq"] == 2
    assert (job["nextAction"], job["dispatchState"], job["nextDispatchAtMs"]) == (None, None, 0)
    assert (job["claimState"], job["claimOwner"], job["claimLeaseExpiresAt"]) == (None, None, 0)
    # acquired snapshot 의 새 seq 로 creating→polling CAS 가 성립해야 한다.
    assert firestore_admin.transition_visual_job(
        job_id, expect_states=("creating",), updates={"state": "polling", "taskId": "t-1"},
        next_action="poll", expect_outbox_seq=job["outboxSeq"], now_ms=T0,
    ) is not None


def test_begin_create_old_message_becomes_stale_after_acquire(fake_firestore):
    job_id = _reserved_job()
    _begin(job_id)
    assert _begin(job_id, owner="w2", seq=1)["status"] == "busy"


def test_begin_create_busy_when_other_owner_holds_live_lease(fake_firestore):
    job_id = _reserved_job()
    _force(job_id, state="creating", leaseOwner="w1", leaseExpiresAt=T0 + LEASE, taskId=None)
    assert _begin(job_id, owner="w2")["status"] == "busy"


def test_begin_create_unconfirmed_when_lease_expired_without_task_id(fake_firestore):
    """B2-02 — 자동 재생성 금지. create 가 벤더에 닿았는지 알 수 없어 재시도가 이중 과금."""
    job_id = _reserved_job()
    _force(job_id, state="creating", leaseOwner="w1", leaseExpiresAt=T0, taskId=None)
    assert _begin(job_id, owner="w2", now_ms=T0 + 1)["status"] == "unconfirmed"


def test_begin_create_resume_when_task_id_present(fake_firestore):
    job_id = _reserved_job()
    _force(job_id, state="creating", leaseOwner="w1", leaseExpiresAt=T0, taskId="t-1")
    assert _begin(job_id, owner="w2", now_ms=T0 + 1)["status"] == "resume"


@pytest.mark.parametrize("kw", [{"gen": 9}, {"seq": 9}])
def test_begin_create_stale_on_mismatch(fake_firestore, kw):
    job_id = _reserved_job()
    assert _begin(job_id, **kw)["status"] == "stale"


def test_begin_create_stale_when_not_yet_due(fake_firestore):
    job_id = _reserved_job()
    _force(job_id, nextDispatchAtMs=T0 + 10_000)
    assert _begin(job_id, now_ms=T0)["status"] == "stale"


def test_concurrent_begin_create_yields_exactly_one_acquire(fake_firestore, monkeypatch):
    """M8-04 — 동시 same-seq 2건에서 vendor create 는 정확히 1회."""
    job_id = _reserved_job()
    fn_a = _capture_tx(monkeypatch, fake_firestore, lambda: _begin(job_id, owner="w1"))
    fn_b = _capture_tx(monkeypatch, fake_firestore, lambda: _begin(job_id, owner="w2"))
    res_a, res_b = fake_firestore.run_contended(fn_a, fn_b)

    statuses = sorted([res_a["status"], res_b["status"]])
    assert statuses.count("acquired") == 1
    assert statuses[0] in ("acquired", "busy", "stale")
    assert _job(job_id)["leaseOwner"] == "w1"


# ══════════════════════ finalize (B3-02 / H4-07 / B8-02 / B8-03) ══════════════════════


def _rotation_ready(seq: int = 5) -> str:
    job_id = _reserved_job()
    _force(job_id, state="fetching", outboxSeq=seq, generation=1)
    return job_id


def _finalize_done(job_id, **kw):
    kw.setdefault("expect_states", ("fetching",))
    return firestore_admin.finalize_visual_job(
        job_id, terminal_state="done", failure_reason=None, job_meta={"vendorTaskId": "t-1"},
        display_status="done", key=f"results/{UID}/{AID}/rotation.mp4", now_ms=T0, **kw,
    )


def test_finalize_writes_job_terminal_and_display_in_one_transaction(fake_firestore):
    job_id = _rotation_ready()
    fake_firestore.commit_count = 0
    assert _finalize_done(job_id) == "finalized"

    job = _job(job_id)
    assert job["state"] == "done" and job["failureReason"] is None
    assert job["nextAction"] is None and job["dispatchState"] is None
    result = _analysis()["result"]
    assert result[f"{ROT}Status"] == "done"
    assert result["rotationVideoKey"] == f"results/{UID}/{AID}/rotation.mp4"
    assert result[f"{ROT}UpdatedAtMs"] == T0
    assert fake_firestore.commit_count == 1  # 두 문서가 하나의 transaction.
    # 분석 공용 updatedAt 은 시각물이 흔들지 않는다 (D-03 경계).
    assert _analysis()["updatedAt"] == 1


def test_finalize_derives_identity_from_job_not_caller(fake_firestore):
    """H4-07 — caller 가 남의 analysisId 를 주입해도 job 문서 값만 쓴다."""
    job_id = _rotation_ready()
    firestore_admin._doc(models.analysis_doc_path(UID, "victim")).set({"result": {}})
    assert _finalize_done(job_id) == "finalized"
    assert _analysis(UID, "victim")["result"] == {}
    assert _analysis()["result"][f"{ROT}Status"] == "done"


def test_finalize_rejects_key_outside_owner_prefix(fake_firestore):
    job_id = _rotation_ready()
    with pytest.raises(ValueError, match="prefix 필수"):
        firestore_admin.finalize_visual_job(
            job_id, terminal_state="done", failure_reason=None, job_meta=None,
            display_status="done", key="results/other/a1/x.mp4",
            expect_states=("fetching",), now_ms=T0,
        )


@pytest.mark.parametrize(
    "kw,msg",
    [
        ({"terminal_state": "done", "display_status": "failed", "key": "results/u1/a1/x.mp4",
          "failure_reason": None}, "display_status='done'"),
        ({"terminal_state": "done", "display_status": "done", "key": None,
          "failure_reason": None}, "canonical key 필수"),
        ({"terminal_state": "done", "display_status": "done", "key": "results/u1/a1/x.mp4",
          "failure_reason": "timeout"}, "failure_reason=None"),
        ({"terminal_state": "failed", "display_status": "failed",
          "key": "results/u1/a1/x.mp4", "failure_reason": "timeout"}, "canonical key 금지"),
        ({"terminal_state": "failed", "display_status": "done", "key": None,
          "failure_reason": "timeout"}, "display_status='failed'"),
        ({"terminal_state": "failed", "display_status": "failed", "key": None,
          "failure_reason": "nope"}, "failure_reason must be"),
    ],
)
def test_finalize_rejects_contradictory_combinations(fake_firestore, kw, msg):
    job_id = _rotation_ready()
    with pytest.raises(ValueError, match=msg):
        firestore_admin.finalize_visual_job(
            job_id, job_meta=None, expect_states=("fetching",), now_ms=T0, **kw
        )


def test_finalize_stale_no_op_when_claim_owner_or_lease_lost(fake_firestore):
    job_id = _rotation_ready()
    _force(job_id, claimState="claimed", claimOwner="w2", claimLeaseExpiresAt=T0 + LEASE,
           claimedOutboxSeq=5)
    assert _finalize_done(job_id, expect_claim_owner="w1", expect_outbox_seq=5) == "stale"
    assert _job(job_id)["state"] == "fetching"

    _force(job_id, claimOwner="w1", claimLeaseExpiresAt=T0)  # 만료.
    assert _finalize_done(job_id, expect_claim_owner="w1", expect_outbox_seq=5) == "stale"
    assert _job(job_id)["state"] == "fetching"


def test_finalize_orphaned_analysis_closes_job_only(fake_firestore):
    job_id = _rotation_ready()
    firestore_admin._doc(models.analysis_doc_path(UID, AID)).delete()
    assert _finalize_done(job_id) == "orphaned_analysis"
    job = _job(job_id)
    assert job["state"] == "failed" and job["failureReason"] == "orphaned_analysis"


def test_finalize_commit_loss_then_retry_is_stale_and_documents_agree(fake_firestore):
    """commit 응답 유실 후 재호출은 no-op 이어야 하고, 두 문서는 일치해야 한다."""
    # 패키지 경로 명시 — bare `conftest` 는 먼저 로드된 아무 conftest 를 잡는다
    # (2026-08-28 실측: 전체 스위트에서 tests/phase33/conftest.py 가 잡혀 ImportError).
    from tests.phase31.conftest import CommitLost

    job_id = _rotation_ready()
    fake_firestore.commit_lost(True)
    with pytest.raises(CommitLost):
        _finalize_done(job_id, expect_outbox_seq=5)
    fake_firestore.commit_lost(False)

    # commit 은 실제로 성사됐다.
    assert _job(job_id)["state"] == "done"
    assert _analysis()["result"][f"{ROT}Status"] == "done"
    # 재호출은 expect_states 불일치로 조용히 stale.
    assert _finalize_done(job_id, expect_outbox_seq=5) == "stale"
    assert _job(job_id)["state"] == "done"
    assert _analysis()["result"][f"{ROT}Status"] == "done"


# ── correctedPose privacy gate — unconditional (8차 B8-02 / T-31-86) ──


def _corrected_pose_job(**extra) -> str:
    _seed_analysis()
    _reserve(CP)
    job_id = models.visual_job_id(UID, AID, CP)
    base = dict(state="postprocessing", outboxSeq=6, generation=1,
                inputSealed=True, privacyBlocker=None, cleanupVerifiedAtMs=0)
    base.update(extra)
    _force(job_id, **base)
    return job_id


def _cp_finalize(job_id, terminal="done", **kw):
    if terminal == "done":
        kw.setdefault("key", f"results/{UID}/{AID}/corrected.png")
        kw.setdefault("failure_reason", None)
        kw.setdefault("display_status", "done")
    else:
        kw.setdefault("key", None)
        kw.setdefault("failure_reason", "pose_gate_failed")
        kw.setdefault("display_status", "failed")
    return firestore_admin.finalize_visual_job(
        job_id, terminal_state=terminal, job_meta=None,
        expect_states=("postprocessing",), now_ms=T0, **kw,
    )


@pytest.mark.parametrize("terminal", ["done", "failed"])
@pytest.mark.parametrize(
    "extra,cleanup,msg",
    [
        ({"inputSealed": False}, T0, "inputSealed=True 필수"),
        ({"inputSealed": True}, None, "cleanupVerifiedAtMs>0 필수"),
    ],
)
def test_corrected_pose_terminal_gate_is_unconditional(
    fake_firestore, terminal, extra, cleanup, msg
):
    """B8-02 — (done|failed) x (inputSealed False | cleanupVerified 0) 네 조합 전부 거부.

    'inputSealed==True 이면' 같은 조건부로 쓰면 inputSealed=False 인 job 이 게이트를
    통째로 건너뛴다 (T-31-86). 실패해도 임시 생체 프레임은 지워져야 한다.
    """
    job_id = _corrected_pose_job(**extra)
    with pytest.raises(ValueError, match=msg):
        _cp_finalize(job_id, terminal, cleanup_verified_at_ms=cleanup)
    assert _job(job_id)["state"] == "postprocessing"


@pytest.mark.parametrize("terminal", ["done", "failed"])
def test_corrected_pose_terminal_passes_with_full_privacy_evidence(fake_firestore, terminal):
    job_id = _corrected_pose_job()
    assert _cp_finalize(job_id, terminal, cleanup_verified_at_ms=T0) == "finalized"
    job = _job(job_id)
    assert job["state"] == terminal
    assert job["cleanupVerifiedAtMs"] == T0
    assert job["privacyBlocker"] is None
    assert _analysis()["result"][f"{CP}Status"] == terminal


def test_cleanup_blocked_recovers_in_one_transaction(fake_firestore):
    """B8-03 — cleanup 재확인과 blocker clear 와 terminal 이 한 transaction."""
    job_id = _corrected_pose_job(privacyBlocker="cleanup_blocked")
    fake_firestore.commit_count = 0
    assert _cp_finalize(job_id, "done", cleanup_verified_at_ms=T0 + 10) == "finalized"
    job = _job(job_id)
    assert job["privacyBlocker"] is None
    assert job["cleanupVerifiedAtMs"] == T0 + 10
    assert job["state"] == "done"
    assert fake_firestore.commit_count == 1


def test_cleanup_blocked_cannot_be_cleared_without_reverification(fake_firestore):
    job_id = _corrected_pose_job(privacyBlocker="cleanup_blocked", cleanupVerifiedAtMs=T0)
    with pytest.raises(ValueError, match="재확인 없이 terminal 금지"):
        _cp_finalize(job_id, "done", cleanup_verified_at_ms=None)
    assert _job(job_id)["state"] == "postprocessing"


@pytest.mark.parametrize("banned", ["privacyBlocker", "cleanupVerifiedAtMs"])
def test_finalize_rejects_privacy_fields_via_job_meta(fake_firestore, banned):
    job_id = _corrected_pose_job()
    with pytest.raises(ValueError, match=f"{banned} 지정 금지"):
        firestore_admin.finalize_visual_job(
            job_id, terminal_state="done", failure_reason=None,
            job_meta={banned: None}, display_status="done",
            key=f"results/{UID}/{AID}/c.png", expect_states=("postprocessing",),
            cleanup_verified_at_ms=T0, now_ms=T0,
        )


def test_cleanup_blocked_is_not_a_terminal_failure_reason():
    """B6-04 — cleanup 미완을 terminal 실패로 적으면 PII 가 남은 채 복구 주체가 사라진다."""
    assert "cleanup_blocked" not in models.VISUAL_FAILURE_REASONS
    assert models.VISUAL_PRIVACY_BLOCKERS == ("cleanup_blocked",)


# ══════════════════════ read / update_analysis_visual ══════════════════════


def test_read_visual_job_returns_none_when_absent(fake_firestore):
    assert firestore_admin.read_visual_job("nope") is None
    job_id = _reserved_job()
    assert firestore_admin.read_visual_job(job_id)["state"] == "reserved"


def test_update_analysis_visual_has_no_url_param_and_no_top_level_updated_at(fake_firestore):
    import inspect

    params = inspect.signature(firestore_admin.update_analysis_visual).parameters
    assert not any("url" in p.lower() for p in params)

    _seed_analysis()
    firestore_admin.update_analysis_visual(
        UID, AID, ROT, status="done", key=f"results/{UID}/{AID}/r.mp4"
    )
    doc = _analysis()
    assert doc["result"]["rotationVideoKey"] == f"results/{UID}/{AID}/r.mp4"
    assert doc["updatedAt"] == 1  # top-level 미갱신.


def test_update_analysis_visual_enforces_key_prefix(fake_firestore):
    _seed_analysis()
    with pytest.raises(ValueError, match="prefix 필수"):
        firestore_admin.update_analysis_visual(UID, AID, ROT, status="done", key="results/x/y/z.mp4")


# ══════════════════════ dispatcher (H4-08 / H5-06 / H6-01 / M6-01) ══════════════════════


def _dispatch_job(job_id: str, **fields) -> None:
    base = dict(
        uid=UID, analysisId=AID, kind=ROT, state="polling", generation=1, outboxSeq=4,
        nextAction="poll", dispatchState="pending", nextDispatchAtMs=T0 - 1_000,
        claimState=None, claimOwner=None, claimLeaseExpiresAt=0, claimedOutboxSeq=0,
    )
    base.update(fields)
    firestore_admin._doc(models.visual_job_doc_path(job_id)).set(base)


def test_list_dispatch_pending_uses_only_equality_query(fake_firestore):
    """복합 인덱스 필요 쿼리를 쓰면 fake query 가 즉시 실패한다 (운영 FAILED_PRECONDITION 예방)."""
    _dispatch_job("j001")
    firestore_admin.list_dispatch_pending(T0)
    assert {f for _c, f, _op, _v in fake_firestore.query_log} == {"dispatchState"}
    assert all(op == "==" for _c, _f, op, _v in fake_firestore.query_log)


def test_list_dispatch_pending_filters_not_due_and_reports_scan_window_age(fake_firestore):
    _dispatch_job("j001", nextDispatchAtMs=T0 - 5_000)
    _dispatch_job("j002", nextDispatchAtMs=T0 + 60_000)  # 아직 아님.
    out = firestore_admin.list_dispatch_pending(T0)
    assert [i["jobId"] for i in out["items"]] == ["j001"]
    assert out["scanned_outbox_max_age_ms"] == 5_000


def test_list_dispatch_pending_drains_full_backlog_across_calls(fake_firestore):
    """H4-08 — 매번 앞에서 N개만 보면 뒤쪽이 영구 starvation 된다. cursor 순환으로 전량 drain."""
    total = 1_200
    for i in range(total):
        _dispatch_job(f"j{i:05d}")

    seen: set[str] = set()
    for _ in range(200):
        out = firestore_admin.list_dispatch_pending(T0, limit=20, max_scan=100)
        seen.update(i["jobId"] for i in out["items"])
        if len(seen) == total:
            break
    assert len(seen) == total


def test_list_dispatch_pending_sets_truncated_when_scan_budget_hit(fake_firestore):
    for i in range(50):
        _dispatch_job(f"j{i:05d}")
    out = firestore_admin.list_dispatch_pending(T0, limit=5, max_scan=10)
    assert out["truncated"] is True
    out2 = firestore_admin.list_dispatch_pending(T0, limit=5, max_scan=500)
    assert out2["truncated"] is False


def test_sent_recovery_only_reissues_same_seq_expired_claims(fake_firestore):
    """H6-01 — claim 직후 crash 의 durable 복구 주체. 정상 sent 재발행은 0이어야 한다."""
    # 복구 대상: same-seq claim + lease 만료 + nonterminal.
    _dispatch_job("r001", dispatchState="sent", claimState="claimed", claimOwner="w1",
                  claimedOutboxSeq=4, claimLeaseExpiresAt=T0 - 1)
    # 미claim sent (lease 0) — worker 가 아직 안 집었을 뿐, 복구 대상 아님.
    _dispatch_job("s001", dispatchState="sent", claimLeaseExpiresAt=0)
    # 구 seq claim — 이미 다음 instance 로 넘어갔다.
    _dispatch_job("s002", dispatchState="sent", claimState="claimed", claimOwner="w1",
                  claimedOutboxSeq=3, claimLeaseExpiresAt=T0 - 1)
    # 유효 lease — 아직 작업 중.
    _dispatch_job("s003", dispatchState="sent", claimState="claimed", claimOwner="w1",
                  claimedOutboxSeq=4, claimLeaseExpiresAt=T0 + LEASE)
    # terminal — 복구 불필요.
    _dispatch_job("s004", dispatchState="sent", state="done", claimState="claimed",
                  claimOwner="w1", claimedOutboxSeq=4, claimLeaseExpiresAt=T0 - 1)

    out = firestore_admin.list_dispatch_pending(T0)
    recovered = [i["jobId"] for i in out["items"] if i["recovery"]]
    assert recovered == ["r001"]
    # dispatchState 를 pending 으로 되돌리지 않는다 (B5-01).
    assert _job("r001")["dispatchState"] == "sent"


def test_pending_and_sent_cursors_are_independent(fake_firestore):
    _dispatch_job("j001")
    _dispatch_job("s001", dispatchState="sent", claimState="claimed", claimOwner="w1",
                  claimedOutboxSeq=4, claimLeaseExpiresAt=T0 - 1)
    firestore_admin.list_dispatch_pending(T0, max_scan=1)
    pending_cursor = firestore_admin._doc(models.visual_dispatch_cursor_doc_path()).get().to_dict()
    sent_cursor = firestore_admin._doc(
        models.visual_dispatch_sent_cursor_doc_path()
    ).get().to_dict()
    assert pending_cursor["lastId"] == "j001"
    assert sent_cursor["lastId"] == "s001"


# ══════════════════════ reservation (B8-05 / B8-06 / B9-01) ══════════════════════

BUCKET = "sunity-visual-input"
K1 = "visual-input/u1/a1/src.png"
K2 = "visual-input/u1/a1/train.png"


def _make_reservation(rid="res-1", owner="p1", keys=(K1,), now_ms=T0):
    job_id = models.visual_job_id(UID, AID, CP)
    firestore_admin.create_input_reservation(
        job_id, rid, owner=owner, bucket=BUCKET, source_hash="h1",
        expected_keys=list(keys), now_ms=now_ms,
    )
    for k in keys:
        firestore_admin.acquire_key_ownership(
            BUCKET, k, ref=rid, kind="reservation", now_ms=now_ms,
            expire_at_ms=now_ms + models.VISUAL_INPUT_RESERVATION_TTL_MS,
        )
    return job_id


def test_create_input_reservation_is_create_only(fake_firestore):
    job_id = _make_reservation()
    firestore_admin.create_input_reservation(
        job_id, "res-1", owner="p2", bucket=BUCKET, source_hash="h2",
        expected_keys=["other"], now_ms=T0,
    )
    data = firestore_admin._doc(
        models.visual_input_reservation_doc_path(job_id, "res-1")
    ).get().to_dict()
    assert data["owner"] == "p1" and data["expectedKeys"] == [K1]


def test_claim_reservation_for_job_requires_open_owner_and_unexpired(fake_firestore):
    job_id = _make_reservation()
    assert firestore_admin.claim_reservation_for_job(job_id, "res-1", owner="p1", now_ms=T0)
    # 이미 claimed_by_job — 재claim 불가.
    assert not firestore_admin.claim_reservation_for_job(job_id, "res-1", owner="p1", now_ms=T0)


def test_claim_reservation_for_job_fails_once_janitor_took_it(fake_firestore):
    job_id = _make_reservation()
    expired = T0 + models.VISUAL_INPUT_RESERVATION_TTL_MS + 1
    assert firestore_admin.claim_reservation_for_janitor(
        job_id, "res-1", owner="jan1", now_ms=expired
    )
    assert not firestore_admin.claim_reservation_for_job(
        job_id, "res-1", owner="p1", now_ms=expired
    )


def test_janitor_cannot_delete_input_of_a_job_that_reserved_it(fake_firestore):
    """B8-06 barrier — janitor 확인 → producer reserve → janitor claim 실패 → delete 0."""
    _seed_analysis()
    job_id = _make_reservation()
    expired = T0 + models.VISUAL_INPUT_RESERVATION_TTL_MS + 1

    # producer 가 먼저 reserve (claim + ownership 승격).
    out = firestore_admin.reserve_visual_job(
        UID, AID, CP, reservation_id="res-1", reservation_owner="p1", now_ms=T0
    )
    assert out["created"] is True

    # 이제 janitor 는 claim 조차 못 한다.
    assert not firestore_admin.claim_reservation_for_janitor(
        job_id, "res-1", owner="jan1", now_ms=expired
    )
    # key ownership 도 job 소유로 넘어가 삭제가 불가능하다.
    assert firestore_admin.claim_key_for_delete(
        BUCKET, K1, deleting_ref="res-1", owner="jan1",
        lease_ms=models.VISUAL_OBJECT_DELETE_LEASE_MS, now_ms=expired,
    ) is None


def test_janitor_claim_crash_is_recovered_after_lease_expiry(fake_firestore):
    """B9-01 — claim CAS 직후 SIGKILL. lease 전에는 재실행 0, lease 후 새 owner 재claim."""
    job_id = _make_reservation()
    expired = T0 + models.VISUAL_INPUT_RESERVATION_TTL_MS + 1
    assert firestore_admin.claim_reservation_for_janitor(
        job_id, "res-1", owner="jan1", now_ms=expired
    )
    # lease 유효 구간 — 다른 janitor 는 못 가져간다.
    assert not firestore_admin.claim_reservation_for_janitor(
        job_id, "res-1", owner="jan2", now_ms=expired + models.VISUAL_JANITOR_CLAIM_LEASE_MS - 1
    )
    # lease 만료 후 — 반드시 재claim 되어야 PII 가 남지 않는다.
    after = expired + models.VISUAL_JANITOR_CLAIM_LEASE_MS + 1
    assert firestore_admin.claim_reservation_for_janitor(
        job_id, "res-1", owner="jan2", now_ms=after
    )
    data = firestore_admin._doc(
        models.visual_input_reservation_doc_path(job_id, "res-1")
    ).get().to_dict()
    assert data["claimOwner"] == "jan2" and data["claimAttempt"] == 2


def test_close_reservation_releases_key_refs_atomically(fake_firestore):
    """B10-03 — release 를 미루면 ownership 문서가 영구 잔존해 이후 cleanup 이 skip 된다."""
    job_id = _make_reservation(keys=(K1, K2))
    fake_firestore.commit_count = 0
    assert firestore_admin.close_reservation(job_id, "res-1", now_ms=T0)
    assert fake_firestore.commit_count == 1
    for k in (K1, K2):
        assert models.visual_input_object_doc_path(BUCKET, k) not in fake_firestore.store
    data = firestore_admin._doc(
        models.visual_input_reservation_doc_path(job_id, "res-1")
    ).get().to_dict()
    assert data["state"] == "closed"
    assert data["expireAt"] is not None


def test_reservation_ttl_covers_pipeline_timeout(fake_firestore):
    """H9-01 — TTL 은 pipeline 최대 실행시간 + 보상구간을 덮어야 한다."""
    pipeline_timeout_ms = 900 * 1000
    assert models.VISUAL_INPUT_RESERVATION_TTL_MS > pipeline_timeout_ms
    assert models.VISUAL_CLAIM_LEASE_MS < 1_800_000  # SQS visibility.
    assert models.VISUAL_CLAIM_LEASE_MS > 300 * 1000  # worker timeout.
    assert models.VISUAL_OBJECT_DELETE_LEASE_MS > 120 * 1000  # dispatcher timeout.


def test_reserve_promotes_all_keys_or_none(fake_firestore):
    """H10-01 — 두 key 승격과 job 생성이 단일 commit 단위."""
    _seed_analysis()
    job_id = _make_reservation(keys=(K1, K2))
    out = firestore_admin.reserve_visual_job(
        UID, AID, CP, reservation_id="res-1", reservation_owner="p1", now_ms=T0
    )
    assert out["created"] is True
    for k in (K1, K2):
        refs = fake_firestore.store[models.visual_input_object_doc_path(BUCKET, k)]["refs"]
        assert set(refs) == {job_id}
        assert refs[job_id]["kind"] == "job"


def test_reserve_creates_nothing_when_one_key_is_being_deleted(fake_firestore):
    _seed_analysis()
    job_id = _make_reservation(keys=(K1, K2))
    firestore_admin._doc(models.visual_input_object_doc_path(BUCKET, K2)).set(
        {"state": "deleting"}, merge=True
    )
    out = firestore_admin.reserve_visual_job(
        UID, AID, CP, reservation_id="res-1", reservation_owner="p1", now_ms=T0
    )
    assert out == {"created": False, "reason": "reservation_lost"}
    assert firestore_admin.read_visual_job(job_id) is None
    # 한쪽만 승격되는 일이 없어야 한다.
    refs = fake_firestore.store[models.visual_input_object_doc_path(BUCKET, K1)]["refs"]
    assert set(refs) == {"res-1"}


def test_reserve_reports_reservation_lost_when_janitor_owns_it(fake_firestore):
    _seed_analysis()
    _make_reservation()
    job_id = models.visual_job_id(UID, AID, CP)
    expired = T0 + models.VISUAL_INPUT_RESERVATION_TTL_MS + 1
    firestore_admin.claim_reservation_for_janitor(job_id, "res-1", owner="jan1", now_ms=expired)
    out = firestore_admin.reserve_visual_job(
        UID, AID, CP, reservation_id="res-1", reservation_owner="p1", now_ms=expired
    )
    assert out == {"created": False, "reason": "reservation_lost"}
    assert firestore_admin.read_visual_job(job_id) is None


# ══════════════════════ key ownership delete fence (B10-01~03 / B11-01/04) ══════════════════════


DEL_LEASE = models.VISUAL_OBJECT_DELETE_LEASE_MS


def test_claim_key_for_delete_consumes_own_ref_first(fake_firestore):
    """B10-01 / T-31-89 — 자기 ref 를 live 로 세면 삭제가 영원히 멈춘다."""
    firestore_admin.acquire_key_ownership(
        BUCKET, K1, ref="res-A", kind="reservation", now_ms=T0, expire_at_ms=T0 + 10
    )
    token = firestore_admin.claim_key_for_delete(
        BUCKET, K1, deleting_ref="res-A", owner="jan1", lease_ms=DEL_LEASE, now_ms=T0 + 100
    )
    assert token is not None and token["generation"] == 1
    doc = fake_firestore.store[models.visual_input_object_doc_path(BUCKET, K1)]
    assert doc["state"] == "deleting" and doc["refs"] == {}


def test_claim_key_for_delete_skips_when_another_ref_is_live(fake_firestore):
    """B9-02 — 다른 reservation 이 같은 key 를 아직 쓰고 있으면 삭제 불가."""
    firestore_admin.acquire_key_ownership(
        BUCKET, K1, ref="res-A", kind="reservation", now_ms=T0, expire_at_ms=T0 + 10
    )
    firestore_admin.acquire_key_ownership(
        BUCKET, K1, ref="res-B", kind="reservation", now_ms=T0, expire_at_ms=T0 + 100_000
    )
    assert firestore_admin.claim_key_for_delete(
        BUCKET, K1, deleting_ref="res-A", owner="jan1", lease_ms=DEL_LEASE, now_ms=T0 + 100
    ) is None
    doc = fake_firestore.store[models.visual_input_object_doc_path(BUCKET, K1)]
    assert doc["state"] == "active" and set(doc["refs"]) == {"res-B"}


def test_job_ref_stays_live_forever_until_explicit_release(fake_firestore):
    """B11-04 / T-31-94 — job ref 에 만료를 적용하면 살아있는 job 의 입력이 삭제된다."""
    firestore_admin.acquire_key_ownership(
        BUCKET, K1, ref="res-A", kind="reservation", now_ms=T0, expire_at_ms=T0 + 10
    )
    firestore_admin.acquire_key_ownership(
        BUCKET, K1, ref="job-1", kind="job", now_ms=T0, expire_at_ms=T0 + 10
    )
    far_future = T0 + 10 * models.VISUAL_INPUT_RESERVATION_TTL_MS
    # reservation ref 는 만료됐지만 job ref 가 살아 있어 삭제 불가.
    assert firestore_admin.claim_key_for_delete(
        BUCKET, K1, deleting_ref="res-A", owner="jan1", lease_ms=DEL_LEASE, now_ms=far_future
    ) is None
    # 자기 ref 는 소비됐지만 job ref 는 그대로 남아 key 를 지킨다.
    doc = fake_firestore.store[models.visual_input_object_doc_path(BUCKET, K1)]
    assert set(doc["refs"]) == {"job-1"} and doc["state"] == "active"

    # worker 의 explicit release 후에야 삭제 가능해진다.
    firestore_admin.acquire_key_ownership(
        BUCKET, K1, ref="res-B", kind="reservation", now_ms=far_future, expire_at_ms=far_future + 10
    )
    firestore_admin.release_key_ownership(BUCKET, K1, ref="job-1")
    assert firestore_admin.claim_key_for_delete(
        BUCKET, K1, deleting_ref="res-B", owner="jan1", lease_ms=DEL_LEASE,
        now_ms=far_future + 100,
    ) is not None


def test_producer_never_reclaims_a_deleting_key_even_after_lease_expiry(fake_firestore):
    """B11-01 / T-31-93 — 만료 deleting 을 producer 가 회수하면 늦은 delete 가 새 입력을 지운다."""
    firestore_admin.acquire_key_ownership(
        BUCKET, K1, ref="res-A", kind="reservation", now_ms=T0, expire_at_ms=T0 + 10
    )
    j1 = firestore_admin.claim_key_for_delete(
        BUCKET, K1, deleting_ref="res-A", owner="jan1", lease_ms=DEL_LEASE, now_ms=T0 + 100
    )
    after = T0 + 100 + DEL_LEASE + 1  # J1 lease 만료.

    # producer 는 만료 여부와 무관하게 항상 fence 된다.
    assert firestore_admin.acquire_key_ownership(
        BUCKET, K1, ref="res-B", kind="reservation", now_ms=after, expire_at_ms=after + 10_000
    ) is False

    # 회수는 janitor 전용.
    j2 = firestore_admin.claim_key_for_delete(
        BUCKET, K1, deleting_ref="res-B", owner="jan2", lease_ms=DEL_LEASE, now_ms=after
    )
    assert j2 is not None and j2["generation"] == 2
    assert firestore_admin.commit_key_delete(BUCKET, K1, token=j2, now_ms=after + 1) is True

    # ★ 살아 돌아온 J1 의 늦은 delete 는 generation fencing 으로 차단된다.
    assert firestore_admin.commit_key_delete(BUCKET, K1, token=j1, now_ms=after + 1) is False


def test_commit_key_delete_rejects_expired_lease(fake_firestore):
    firestore_admin.acquire_key_ownership(
        BUCKET, K1, ref="res-A", kind="reservation", now_ms=T0, expire_at_ms=T0 + 10
    )
    token = firestore_admin.claim_key_for_delete(
        BUCKET, K1, deleting_ref="res-A", owner="jan1", lease_ms=DEL_LEASE, now_ms=T0 + 100
    )
    assert firestore_admin.commit_key_delete(
        BUCKET, K1, token=token, now_ms=T0 + 100 + DEL_LEASE + 1
    ) is False


def test_release_key_ownership_removes_doc_when_last_ref_goes(fake_firestore):
    firestore_admin.acquire_key_ownership(BUCKET, K1, ref="job-1", kind="job", now_ms=T0)
    firestore_admin.release_key_ownership(BUCKET, K1, ref="job-1")
    assert models.visual_input_object_doc_path(BUCKET, K1) not in fake_firestore.store


def test_acquire_key_ownership_rejects_unknown_kind(fake_firestore):
    with pytest.raises(ValueError):
        firestore_admin.acquire_key_ownership(BUCKET, K1, ref="x", kind="bogus", now_ms=T0)


# ══════════════════════ orphan registry (H9-07 / B9-01) ══════════════════════


def _orphan_id() -> str:
    return models.visual_input_object_doc_path(BUCKET, K1).rsplit("/", 1)[-1]


def test_upsert_visual_orphan_reopens_a_closed_incident(fake_firestore):
    """H9-07 — 같은 key 가 재발했는데 closed 로 두면 두 번째 사고가 조용히 묻힌다."""
    oid = firestore_admin.upsert_visual_orphan(BUCKET, K1, now_ms=T0, reason="delete_failed")
    firestore_admin.close_visual_orphan(oid, now_ms=T0 + 10)
    assert firestore_admin._doc(models.visual_orphan_doc_path(oid)).get().to_dict()["state"] == "closed"

    firestore_admin.upsert_visual_orphan(BUCKET, K1, now_ms=T0 + 100, reason="delete_failed_again")
    data = firestore_admin._doc(models.visual_orphan_doc_path(oid)).get().to_dict()
    assert data["state"] == "open"
    assert data["generation"] == 2
    assert data["attempt"] == 0


def test_claim_visual_orphan_recovers_after_claim_crash(fake_firestore):
    oid = firestore_admin.upsert_visual_orphan(BUCKET, K1, now_ms=T0, reason="delete_failed")
    assert firestore_admin.claim_visual_orphan(oid, owner="jan1", now_ms=T0) is not None
    # lease 유효 구간엔 재claim 0 (중복 delete 방지).
    assert firestore_admin.claim_visual_orphan(
        oid, owner="jan2", now_ms=T0 + models.VISUAL_JANITOR_CLAIM_LEASE_MS - 1
    ) is None
    # 만료 후엔 반드시 재claim (claim 직후 crash 복구 — B9-01).
    got = firestore_admin.claim_visual_orphan(
        oid, owner="jan2", now_ms=T0 + models.VISUAL_JANITOR_CLAIM_LEASE_MS + 1
    )
    assert got is not None and got["claimOwner"] == "jan2" and got["attempt"] == 2


def test_bump_visual_orphan_returns_claim_and_sets_backoff(fake_firestore):
    oid = firestore_admin.upsert_visual_orphan(BUCKET, K1, now_ms=T0, reason="x")
    firestore_admin.claim_visual_orphan(oid, owner="jan1", now_ms=T0)
    assert firestore_admin.bump_visual_orphan(oid, next_retry_at_ms=T0 + 60_000, last_error="5xx")
    data = firestore_admin._doc(models.visual_orphan_doc_path(oid)).get().to_dict()
    assert data["state"] == "open" and data["claimOwner"] is None
    assert firestore_admin.claim_visual_orphan(oid, owner="jan2", now_ms=T0 + 1) is None
    assert firestore_admin.claim_visual_orphan(oid, owner="jan2", now_ms=T0 + 60_001) is not None
