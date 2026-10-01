"""Phase 38 (Plan 38-06 Task 1) — firestore_admin 공급자 링크 등록 writer + 순수 가드 1.

실 Firestore 0. backend/tests/phase31/conftest.py 의 FakeFirestore 를 재사용한다 —
mock 이 통과시켜 주는 것이 아니라 **실제 optimistic concurrency**(문서 version 대조)로
claim 의 CAS 를 재현한다. FakeFirestore 에 `batch()` 가 없어 `_FakeBatch`(create 기록 ·
commit 시 존재하면 AlreadyExists) 를 이 파일에 두고 `_db` seam 을 갈아끼운다.

잠그는 계약(38-06-PLAN behavior · 리뷰 R2·R3·R4·R8·R13):
  · 선작성 = 공개 `reference/{refId}` + 비공개 `reference/{refId}/private/registration`
    두 doc 을 한 batch 의 create 2회 + commit 1회(set 0회)로.
  · `reference/{refId}` 를 **쓰는** 11함수만 legacy `ref-*`/빈 id 를 ValueError 로 거부하고,
    읽기 3함수는 어떤 id 든 raw 로 읽는다(plan-checker 차단 2, 2026-09-28 — 38-09 baseline ·
    38-14 재diff 가 legacy 11개를 `get_reference_registration` 으로 읽는다).
  · claim 은 registering|queued 또는 lease 만료 processing 에서만 — 동시 이벤트 2 · requeue 2회
    · lease 만료 재claim · 종결 상태 거부.
  · review/failed/angles/begin_self_check 는 doc.jobId == job_id 일 때만(늦은 stale 작업이 활성
    doc 을 못 뒤집는다).
  · quick-261001-thx(belle 2026-10-01): 판정 통과 = review(isActive False 명시 + 비공개 진단) →
    사람 승인(approve → active + isActive True) 또는 반려(reject → failed + 사유). 승인/반려는 job
    가드가 아니라 상태 검사만, 누가/언제는 비공개 doc 에만, 반복 실행은 already_* 로 쓰기 0.
  · 자기 재현성은 기준 doc 이 권위 — `self_check_authorized` 3중 일치(위조 표식 · 다른 공급자
    refId · stale analysis id · pending 전 완료 훅 전부 False).
"""

from __future__ import annotations

import copy
import inspect
import logging

import pytest

from sunity_shared import firestore_admin as fa
from sunity_shared import models
from sunity_shared.analysis.skeleton import JOINT_KEYS
from sunity_shared.validation import ReferenceUploadRequest
from tests.phase31.conftest import fake_firestore  # noqa: F401 — 픽스처 재등록(디렉터리 밖)

T0 = 1_700_000_000_000
LEASE_MS = models.REGISTRATION_LEASE_SEC * 1000
REF = "0123456789abcdef0123456789abcdef"  # uuid4 hex 모양
PUBLIC = models.reference_motion_path(REF)
PRIVATE = models.reference_private_path(REF)
UPLOAD_KEY = f"reference/u1/{REF}/upload.mp4"
FINAL_KEY = f"reference/u1/{REF}/v1.mp4"
LOGGER = "sunity_shared.firestore_admin"


# ─────────────────────── batch() 보강 (FakeFirestore 에 없음) ───────────────────────


class AlreadyExists(Exception):
    """실 Firestore `create()` 가 기존 doc 을 만나면 던지는 예외의 모사."""


class _FakeBatch:
    def __init__(self, db) -> None:
        self._db = db
        self.creates: list[tuple[str, dict]] = []
        self.sets: list[tuple] = []
        self.commits = 0

    def create(self, ref, payload: dict) -> None:
        self.creates.append((ref.path, copy.deepcopy(payload)))

    def set(self, ref, payload: dict, merge: bool = False) -> None:
        self.sets.append((ref.path, copy.deepcopy(payload), merge))

    def commit(self):
        self.commits += 1
        # 실 Firestore: 하나라도 존재하면 batch 전체가 실패한다(원자성).
        for path, _payload in self.creates:
            if path in self._db.store:
                raise AlreadyExists(path)
        for path, payload in self.creates:
            self._db._apply("set", path, payload, False)
        return []


class _FakeDb:
    def __init__(self, db) -> None:
        self._db = db
        self.batches: list[_FakeBatch] = []

    def batch(self) -> _FakeBatch:
        b = _FakeBatch(self._db)
        self.batches.append(b)
        return b


@pytest.fixture
def reg_db(fake_firestore, monkeypatch):
    """FakeFirestore + `_db().batch()` + 고정 시계(`_now_ms` → T0)."""
    fdb = _FakeDb(fake_firestore)
    monkeypatch.setattr(fa, "_db", lambda: fdb)
    monkeypatch.setattr(fa, "_now_ms", lambda: T0)
    fake_firestore.fake_db = fdb
    return fake_firestore


# ─────────────────────── helpers ───────────────────────


def _form(clip_range=(1.5, 7.0)) -> ReferenceUploadRequest:
    # quick-260930-w9l — 요청에 선수 이름·선언 4·학습 동의가 없다(서버가 채운다/무시한다).
    return ReferenceUploadRequest(
        name="킵업",
        level="intermediate",
        technique_ref_id="ref-kip-up",
        clip_range=clip_range,
        fmt="mp4",
        file_size_bytes=30 * 1024 * 1024,
        duration_sec=12.4,
    )


def _create(db, ref_id: str = REF, **kw) -> None:
    fa.create_reference_registration(
        ref_id,
        supplier_uid=kw.pop("supplier_uid", "u1"),
        form=kw.pop("form", _form()),
        athlete_name=kw.pop("athlete_name", "정은지"),
        upload_key=kw.pop("upload_key", UPLOAD_KEY),
        upload_expires_at_ms=kw.pop("upload_expires_at_ms", T0 + 900_000),
        consent_at_ms=kw.pop("consent_at_ms", T0),
        supplier_code=kw.pop("supplier_code", "EUNJI"),
    )
    assert not kw


def _seed(db, status: str, *, job_id=None, lease_until=None, **extra) -> dict:
    """공개 doc 을 원하는 상태로 심는다(version 도 올린다)."""
    doc = {
        "motionId": REF,
        "supplierUid": "u1",
        "registrationStatus": status,
        "jobId": job_id,
        "leaseUntil": lease_until,
        "isActive": status == models.REGISTRATION_STATUS_ACTIVE,
        "updatedAt": T0 - 1,
    }
    doc.update(extra)
    db._apply("set", PUBLIC, doc, False)
    return copy.deepcopy(doc)


def _angles_kwargs(**over) -> dict:
    frames = over.pop("frames", 3)
    kw = dict(
        job_id="A",
        angles_flat=[float(i) for i in range(frames * len(JOINT_KEYS))],
        joint_keys=list(JOINT_KEYS),
        frames=frames,
        real_fps=10.0,
        keypoint_report={"jointKeys": list(JOINT_KEYS), "frames": frames, "conf": [0.9] * 3},
    )
    kw.update(over)
    return kw


# ─────────────────────── seam 존재 ───────────────────────


def test_fake_firestore_seams_present(fake_firestore):
    assert fake_firestore.missing_seams == ()


# ─────────────────────── create_reference_registration (R13 · D-04 · D-08) ───────────────────────


def test_create_reference_registration_batch_creates_public_and_private(reg_db):
    _create(reg_db)

    batches = reg_db.fake_db.batches
    assert len(batches) == 1
    b = batches[0]
    assert b.commits == 1
    assert b.sets == []  # set 0회 — 선작성은 create 만
    assert [p for p, _ in b.creates] == [PUBLIC, PRIVATE]

    public = dict(b.creates[0][1])
    assert set(public) == {
        "motionId", "supplierUid", "supplierCode", "source", "name", "athleteName", "level",
        "uploadKey", "uploadExpiresAt", "isActive", "registrationStatus", "jobId", "leaseUntil",
        "registrationUpdatedAt", "createdAt", "updatedAt",
    }
    assert public["motionId"] == REF
    assert public["supplierUid"] == "u1"
    assert public["supplierCode"] == "EUNJI"
    assert public["source"] == "supplier-link"
    assert public["name"] == "킵업" and public["athleteName"] == "정은지"
    assert public["level"] == "intermediate"
    assert public["uploadKey"] == UPLOAD_KEY
    assert public["uploadExpiresAt"] == T0 + 900_000
    assert public["isActive"] is False
    assert public["registrationStatus"] == models.REGISTRATION_STATUS_REGISTERING
    assert public["jobId"] is None and public["leaseUntil"] is None
    assert public["registrationUpdatedAt"] == T0 == public["createdAt"] == public["updatedAt"]
    # 공개 doc 에 없어야 하는 것 — videoS3Key(활성화 때 v1) · 동의 · 선언 · techniqueRefId · clipRange
    for forbidden in ("videoS3Key", "consent", "techniqueRefId", "clipRange", "isCombo",
                      "isSplit", "hasHold", "standingStart"):
        assert forbidden not in public

    private = dict(b.creates[1][1])
    # quick-260930-w9l — 선언 4(isCombo·isSplit·hasHold·standingStart)는 새 doc 에 쓰지 않는다
    # (소비처 0). 학습은 체크박스가 아니라 공급자 계약 근거(trainingBasis)로 true.
    assert set(private) == {
        "supplierUid", "consent", "techniqueRefId", "clipRange", "updatedAt",
    }
    assert private["supplierUid"] == "u1"
    assert private["consent"] == {
        "portrait": True, "usage": True, "training": True,
        "trainingBasis": "supplier_contract",
        "version": "2026-09-30", "at": T0, "uid": "u1",
    }
    assert models.CONSENT_VERSION == "2026-09-30"
    for gone in ("silent",):
        assert gone not in private["consent"]
    assert private["techniqueRefId"] == "ref-kip-up"
    assert private["clipRange"] == {"execStartS": 1.5, "execEndS": 7.0}
    assert private["updatedAt"] == T0

    # commit 이 store 에 반영됐다(뒤 테스트가 이어 쓸 수 있다).
    assert reg_db.store[PUBLIC]["registrationStatus"] == "registering"
    assert reg_db.store[PRIVATE]["consent"]["version"] == models.CONSENT_VERSION


def test_create_reference_registration_clip_range_key_absent_when_none(reg_db):
    _create(reg_db, form=_form(clip_range=None), supplier_code=None)
    b = reg_db.fake_db.batches[0]
    public, private = b.creates[0][1], b.creates[1][1]
    assert "clipRange" not in private
    assert private["consent"]["training"] is True
    assert public["supplierCode"] is None


def test_create_reference_registration_athlete_name_comes_from_argument(reg_db):
    """공개 athleteName 은 폼이 아니라 호출측이 넘긴 공급자 displayName(w9l 항목 10)."""
    _create(reg_db, athlete_name="김선수")
    public = reg_db.fake_db.batches[0].creates[0][1]
    assert public["athleteName"] == "김선수"


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_create_reference_registration_requires_athlete_name(reg_db, bad):
    with pytest.raises(ValueError):
        _create(reg_db, athlete_name=bad)
    assert reg_db.fake_db.batches == [] or all(b.commits == 0 for b in reg_db.fake_db.batches)


def test_create_reference_registration_payloads_have_no_nested_list(reg_db):
    _create(reg_db)
    b = reg_db.fake_db.batches[0]
    for _path, payload in b.creates:
        fa._validate_flat_dict_no_nested_array(payload, path="create")  # raise 없음


def test_create_reference_registration_existing_doc_propagates_already_exists(reg_db):
    _seed(reg_db, "active", job_id="Z")
    with pytest.raises(AlreadyExists):
        _create(reg_db)
    # 기존 doc 무변경 — create 는 set/merge 로 강등되지 않는다.
    assert reg_db.store[PUBLIC]["registrationStatus"] == "active"
    assert PRIVATE not in reg_db.store


# ─────────────────────── legacy ref-* 가드 — 쓰기 9 만 (차단 2) ───────────────────────

_DIAG = {
    "personRatio": 0.538,
    "lowConfidenceJoints": ["left_ankle"],
    "standMaterialUnreadable": [],
    "standingStart": "floor_violation",
    "nStand": 9,
}

_WRITERS = {
    "create_reference_registration": lambda rid: fa.create_reference_registration(
        rid, supplier_uid="u1", form=_form(), athlete_name="정은지", upload_key=UPLOAD_KEY,
        upload_expires_at_ms=T0 + 900_000, consent_at_ms=T0,
    ),
    "claim_registration": lambda rid: fa.claim_registration(rid, "A", now_ms=T0),
    "set_registration_queued": lambda rid: fa.set_registration_queued(rid, queued_reason="pod_down"),
    "set_registration_expired": lambda rid: fa.set_registration_expired(rid),
    "set_registration_review": lambda rid: fa.set_registration_review(
        rid, "A", video_s3_key=FINAL_KEY, video_etag='"abc"', diagnostics=dict(_DIAG),
    ),
    "approve_reference_registration": lambda rid: fa.approve_reference_registration(rid, by="ops:t"),
    "reject_reference_registration": lambda rid: fa.reject_reference_registration(
        rid, reason="화면이 어두워요", by="ops:t",
    ),
    "deactivate_reference_registration": lambda rid: fa.deactivate_reference_registration(rid, by="ops:t"),
    "set_registration_failed": lambda rid: fa.set_registration_failed(
        rid, "A", error={"code": "low_confidence", "message": "m", "joints": ["왼쪽 발목"]},
    ),
    "set_reference_angles": lambda rid: fa.set_reference_angles(rid, **_angles_kwargs()),
    "begin_self_check": lambda rid: fa.begin_self_check(rid, job_id="A", analysis_id="a1"),
    "set_reference_self_check": lambda rid: fa.set_reference_self_check(
        rid, status="done", uid="u1", analysis_id="a1", job_id="A", score=97.3,
    ),
}

_READERS_AND_UNGUARDED = (
    "get_reference_registration",
    "get_reference_registration_private",
    "list_reference_registrations_by_status",
    "create_analysis_doc",
    "self_check_authorized",
)


@pytest.fixture
def firestore_call_log(monkeypatch):
    """어떤 seam 이든 닿으면 기록 — 가드는 Firestore 호출보다 먼저여야 한다."""
    calls: list[str] = []

    def _touch(name):
        def _f(*_a, **_k):
            calls.append(name)
            raise AssertionError(f"{name} 호출됨 — 가드가 Firestore 보다 먼저여야 한다")
        return _f

    for seam in ("_db", "_doc", "_collection", "_run_in_transaction"):
        monkeypatch.setattr(fa, seam, _touch(seam))
    return calls


@pytest.mark.parametrize("bad_id", ["ref-kip-up", ""], ids=["legacy", "empty"])
@pytest.mark.parametrize("writer", sorted(_WRITERS))
def test_writers_reject_legacy_ref_id(firestore_call_log, writer, bad_id):
    with pytest.raises(ValueError, match="legacy|invalid"):
        _WRITERS[writer](bad_id)
    assert firestore_call_log == []


def test_exactly_twelve_writers_are_guarded_and_readers_are_not():
    assert set(_WRITERS) == {
        "create_reference_registration", "claim_registration", "set_registration_queued",
        "set_registration_expired", "set_registration_review", "set_registration_failed",
        "set_reference_angles", "begin_self_check", "set_reference_self_check",
        "approve_reference_registration", "reject_reference_registration",
        "deactivate_reference_registration",
    }
    assert not hasattr(fa, "set_registration_active")  # 운영 호출자(파이프라인) 하나뿐이라 대체
    for name in _WRITERS:
        assert "_require_registration_ref_id" in inspect.getsource(getattr(fa, name)), name
    for name in _READERS_AND_UNGUARDED:
        assert "_require_registration_ref_id" not in inspect.getsource(getattr(fa, name)), name


def test_legacy_ref_id_read_allowed(fake_firestore):
    fake_firestore._apply("set", "reference/ref-kip-up", {"name": "kip-up", "isActive": True}, False)
    got = fa.get_reference_registration("ref-kip-up")
    assert got is not None
    assert got["name"] == "kip-up" and got["isActive"] is True
    assert got["motionId"] == "ref-kip-up"
    assert fa.get_reference_registration("ref-none") is None
    assert fa.get_reference_registration_private("ref-kip-up") is None


def test_get_reference_registration_reads_top_level_raw(reg_db):
    _create(reg_db)
    pub = fa.get_reference_registration(REF)
    prv = fa.get_reference_registration_private(REF)
    assert pub["registrationStatus"] == "registering" and pub["motionId"] == REF
    assert prv["consent"]["uid"] == "u1"
    assert "consent" not in pub


# ─────────────────────── claim_registration (R3) ───────────────────────


def test_claim_registration_missing_doc_false(reg_db):
    assert fa.claim_registration(REF, "A", now_ms=T0) is False
    assert PUBLIC not in reg_db.store


def test_claim_registration_from_registering_sets_processing_job_lease(reg_db):
    _create(reg_db)
    assert fa.claim_registration(REF, "A", lease_sec=900, now_ms=T0) is True
    doc = reg_db.store[PUBLIC]
    assert doc["registrationStatus"] == "processing"
    assert doc["jobId"] == "A"
    assert doc["leaseUntil"] == T0 + 900_000
    assert doc["registrationUpdatedAt"] == T0 and doc["updatedAt"] == T0
    # 다른 필드는 보존(update 어법).
    assert doc["uploadKey"] == UPLOAD_KEY and doc["isActive"] is False


def test_two_concurrent_claims_second_false(reg_db):
    """동시 이벤트 2 = 한 번만 실행 — A 뒤 B 는 lease 안이라 False, doc 은 A 그대로."""
    _create(reg_db)
    assert fa.claim_registration(REF, "A", now_ms=T0) is True
    assert fa.claim_registration(REF, "B", now_ms=T0 + 1000) is False
    doc = reg_db.store[PUBLIC]
    assert doc["jobId"] == "A" and doc["leaseUntil"] == T0 + LEASE_MS


def test_claim_contended_cas_only_one_succeeds(reg_db, monkeypatch):
    """같은 pre-state 를 읽은 두 트랜잭션 — FakeFirestore 의 실제 conflict/재시도 경로."""
    _create(reg_db)
    captured = []
    monkeypatch.setattr(fa, "_run_in_transaction", lambda fn: captured.append(fn))
    fa.claim_registration(REF, "A", now_ms=T0)
    fa.claim_registration(REF, "B", now_ms=T0 + 5)
    tx_a, tx_b = captured
    result_a, result_b = reg_db.run_contended(tx_a, tx_b)
    assert result_a is True
    assert result_b is False  # conflict → 재시도 → A 의 lease 를 보고 포기
    assert reg_db.conflict_count == 1
    assert reg_db.store[PUBLIC]["jobId"] == "A"
    assert reg_db.read_after_write_seen is False


def test_reclaim_after_lease_expiry_logs_old_job(reg_db, caplog):
    _create(reg_db)
    assert fa.claim_registration(REF, "A", now_ms=T0) is True
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert fa.claim_registration(REF, "B", now_ms=T0 + LEASE_MS + 1) is True
    doc = reg_db.store[PUBLIC]
    assert doc["jobId"] == "B"
    assert doc["leaseUntil"] == T0 + LEASE_MS + 1 + LEASE_MS
    assert doc["registrationStatus"] == "processing"
    assert any("A" in r.getMessage() and "lease" in r.getMessage().lower() for r in caplog.records)


def test_requeue_twice_claims_once(reg_db):
    """requeue 2회(queued 에서 두 전달자) — 첫 claim 만 True."""
    _seed(reg_db, "queued", queuedReason="pod_down")
    assert fa.claim_registration(REF, "R1", now_ms=T0) is True
    assert fa.claim_registration(REF, "R2", now_ms=T0 + 10) is False
    assert reg_db.store[PUBLIC]["jobId"] == "R1"


@pytest.mark.parametrize("status", ["active", "failed", "expired"])
def test_claim_from_terminal_states_false(reg_db, status):
    before = _seed(reg_db, status, job_id="OLD")
    assert fa.claim_registration(REF, "NEW", now_ms=T0 + LEASE_MS * 10) is False
    assert reg_db.store[PUBLIC] == before


def test_claim_registration_requires_job_id(reg_db):
    _create(reg_db)
    with pytest.raises(ValueError):
        fa.claim_registration(REF, "", now_ms=T0)


# ─────────────────────── queued / expired (R4) ───────────────────────


def test_set_registration_queued_only_from_registering(reg_db, caplog):
    _create(reg_db)
    assert fa.set_registration_queued(REF, queued_reason="pod_down") is True
    doc = reg_db.store[PUBLIC]
    assert doc["registrationStatus"] == "queued" and doc["queuedReason"] == "pod_down"
    assert doc["registrationUpdatedAt"] == T0

    assert fa.claim_registration(REF, "A", now_ms=T0) is True  # queued → processing
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert fa.set_registration_queued(REF, queued_reason="pod_down") is False
    assert reg_db.store[PUBLIC]["registrationStatus"] == "processing"
    assert any("queued" in r.getMessage() for r in caplog.records)


def test_set_registration_queued_requires_reason(reg_db):
    _create(reg_db)
    with pytest.raises(ValueError):
        fa.set_registration_queued(REF, queued_reason="")


def test_set_registration_expired_only_from_registering(reg_db):
    _create(reg_db)
    assert fa.set_registration_expired(REF) is True
    assert reg_db.store[PUBLIC]["registrationStatus"] == "expired"
    assert reg_db.store[PUBLIC]["registrationUpdatedAt"] == T0


@pytest.mark.parametrize("status", ["queued", "processing"])
def test_set_registration_expired_false_from_other_states(reg_db, status):
    before = _seed(reg_db, status, job_id="A" if status == "processing" else None)
    assert fa.set_registration_expired(REF) is False
    assert reg_db.store[PUBLIC] == before


def test_set_registration_expired_missing_doc_false(reg_db):
    assert fa.set_registration_expired(REF) is False


# ─────────────────────── review / failed (R3 job 가드) ───────────────────────


def test_set_registration_review_with_matching_job_writes_public_and_private(reg_db):
    """판정 통과 = review — isActive False 명시(수강생 picker 비노출, T-thx-01) + 비공개 진단을 한 트랜잭션에."""
    _create(reg_db)
    assert fa.claim_registration(REF, "A", now_ms=T0) is True
    commits_before = reg_db.commit_count
    assert fa.set_registration_review(
        REF, "A", video_s3_key=FINAL_KEY, video_etag='"abc"', diagnostics=dict(_DIAG)
    ) is True
    assert reg_db.commit_count == commits_before + 1
    doc = reg_db.store[PUBLIC]
    assert doc["registrationStatus"] == "review" and doc["isActive"] is False
    assert doc["videoS3Key"] == FINAL_KEY and doc["videoETag"] == '"abc"'
    assert doc["leaseUntil"] is None and doc["jobId"] == "A"
    assert doc["registrationUpdatedAt"] == T0 and doc["updatedAt"] == T0
    assert "registrationDiagnostics" not in doc  # 진단은 비공개 doc 에만(R13)
    prv = reg_db.store[PRIVATE]
    assert prv["registrationDiagnostics"] == _DIAG
    assert prv["updatedAt"] == T0
    assert prv["consent"]["version"] == models.CONSENT_VERSION  # merge — 동의 보존
    assert reg_db.read_after_write_seen is False


def test_set_registration_review_forces_is_active_false_even_if_doc_said_true(reg_db):
    _seed(reg_db, "processing", job_id="A", lease_until=T0 + LEASE_MS, isActive=True)
    assert fa.set_registration_review(
        REF, "A", video_s3_key=FINAL_KEY, video_etag='"e"', diagnostics=dict(_DIAG)
    ) is True
    assert reg_db.store[PUBLIC]["isActive"] is False


def test_set_registration_review_writes_thumbnail_key_when_given(reg_db):
    """quick-260930-w9l — 같은 트랜잭션 update 에 thumbnailS3Key. None 이면 키 없음."""
    thumb = f"reference/u1/{REF}/thumb.jpg"
    _create(reg_db)
    assert fa.claim_registration(REF, "A", now_ms=T0) is True
    assert fa.set_registration_review(
        REF, "A", video_s3_key=FINAL_KEY, video_etag='"abc"', thumbnail_s3_key=thumb, diagnostics=dict(_DIAG)
    ) is True
    assert reg_db.store[PUBLIC]["thumbnailS3Key"] == thumb


def test_set_registration_review_without_thumbnail_has_no_key(reg_db):
    _create(reg_db)
    assert fa.claim_registration(REF, "A", now_ms=T0) is True
    assert fa.set_registration_review(
        REF, "A", video_s3_key=FINAL_KEY, video_etag='"abc"', thumbnail_s3_key=None, diagnostics=dict(_DIAG)
    ) is True
    assert "thumbnailS3Key" not in reg_db.store[PUBLIC]


def test_set_registration_review_stale_job_false_no_change(reg_db, caplog):
    _seed(reg_db, "processing", job_id="B", lease_until=T0 + LEASE_MS)
    before = copy.deepcopy(reg_db.store[PUBLIC])
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert fa.set_registration_review(
            REF, "A", video_s3_key=FINAL_KEY, video_etag='"e"', diagnostics=dict(_DIAG)
        ) is False
    assert reg_db.store[PUBLIC] == before
    assert PRIVATE not in reg_db.store
    assert any("stale" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("status", ["queued", "review", "active", "failed"])
def test_set_registration_review_requires_processing(reg_db, status):
    before = _seed(reg_db, status, job_id="A")
    assert fa.set_registration_review(
        REF, "A", video_s3_key=FINAL_KEY, video_etag='"e"', diagnostics=dict(_DIAG)
    ) is False
    assert reg_db.store[PUBLIC] == before
    assert PRIVATE not in reg_db.store


def test_set_registration_review_rejects_empty_key_etag_or_bad_diagnostics(reg_db):
    _seed(reg_db, "processing", job_id="A", lease_until=T0 + LEASE_MS)
    with pytest.raises(ValueError):
        fa.set_registration_review(REF, "A", video_s3_key="", video_etag='"e"', diagnostics=dict(_DIAG))
    with pytest.raises(ValueError):
        fa.set_registration_review(REF, "A", video_s3_key=FINAL_KEY, video_etag="", diagnostics=dict(_DIAG))
    with pytest.raises(TypeError):
        fa.set_registration_review(
            REF, "A", video_s3_key=FINAL_KEY, video_etag='"e"', diagnostics={"rows": [[1, 2]]}
        )
    assert reg_db.store[PUBLIC]["registrationStatus"] == "processing"


def test_set_registration_failed_writes_private_error_in_same_transaction(reg_db):
    _create(reg_db)
    assert fa.claim_registration(REF, "A", now_ms=T0) is True
    commits_before = reg_db.commit_count
    err = {"code": "low_confidence", "message": "일부 관절을 못 읽었어요.", "joints": ["왼쪽 발목"]}
    assert fa.set_registration_failed(REF, "A", error=err) is True
    assert reg_db.commit_count == commits_before + 1  # 공개+비공개가 한 트랜잭션
    pub = reg_db.store[PUBLIC]
    assert pub["registrationStatus"] == "failed" and pub["leaseUntil"] is None
    assert pub["isActive"] is False
    assert "registrationError" not in pub  # 실패 상세는 비공개 doc 에만(R13)
    prv = reg_db.store[PRIVATE]
    assert prv["registrationError"] == err
    assert prv["updatedAt"] == T0
    assert prv["consent"]["version"] == models.CONSENT_VERSION  # merge — 동의 보존


def test_set_registration_failed_error_missing_code_or_message_raises(reg_db):
    _seed(reg_db, "processing", job_id="A", lease_until=T0 + LEASE_MS)
    with pytest.raises(ValueError):
        fa.set_registration_failed(REF, "A", error={"message": "m"})
    with pytest.raises(ValueError):
        fa.set_registration_failed(REF, "A", error={"code": "server_error"})
    assert reg_db.store[PUBLIC]["registrationStatus"] == "processing"


def test_stale_job_failure_on_active_doc_no_change(reg_db, caplog):
    """늦게 끝난 stale 작업 B 의 실패가 A 가 활성화한 doc 을 못 뒤집는다(R3)."""
    _seed(reg_db, "active", job_id="A", videoS3Key=FINAL_KEY)
    before = copy.deepcopy(reg_db.store[PUBLIC])
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert fa.set_registration_failed(
            REF, "B", error={"code": "server_error", "message": "late"}
        ) is False
    assert reg_db.store[PUBLIC] == before
    assert PRIVATE not in reg_db.store
    assert any("stale" in r.getMessage() for r in caplog.records)


def test_same_job_failure_after_active_is_noop(reg_db):
    before = _seed(reg_db, "active", job_id="A", videoS3Key=FINAL_KEY)
    assert fa.set_registration_failed(REF, "A", error={"code": "server_error", "message": "x"}) is False
    assert reg_db.store[PUBLIC] == before


# ─────────────────────── set_reference_angles (D-05 · Success ④) ───────────────────────


def test_set_reference_angles_payload_keys_exact(reg_db):
    _seed(reg_db, "processing", job_id="A", lease_until=T0 + LEASE_MS)
    assert fa.set_reference_angles(REF, **_angles_kwargs()) is True
    doc = reg_db.store[PUBLIC]
    written = {k for k in doc if k.startswith("angles") or k.startswith("reference")}
    assert written == {"angles", "anglesJointKeys", "anglesFrames", "anglesUpdatedAt",
                       "anglesRealFps", "referenceKeypointReport"}
    assert doc["angles"] == [float(i) for i in range(3 * len(JOINT_KEYS))]
    assert doc["anglesJointKeys"] == list(JOINT_KEYS)
    assert doc["anglesFrames"] == 3
    assert doc["anglesRealFps"] == 10.0
    assert doc["anglesUpdatedAt"] == T0
    assert doc["referenceKeypointReport"]["frames"] == 3
    assert doc["registrationStatus"] == "processing"  # merge — 상태 무접촉


def test_set_reference_angles_split_angle_only_when_given(reg_db):
    _seed(reg_db, "processing", job_id="A", lease_until=T0 + LEASE_MS)
    assert fa.set_reference_angles(REF, **_angles_kwargs(split_angle=171.5)) is True
    assert reg_db.store[PUBLIC]["referenceSplitAngle"] == 171.5


def test_set_reference_angles_length_mismatch_raises(reg_db):
    before = _seed(reg_db, "processing", job_id="A", lease_until=T0 + LEASE_MS)
    kw = _angles_kwargs()
    kw["angles_flat"] = kw["angles_flat"][:-1]
    with pytest.raises(ValueError, match="frames"):
        fa.set_reference_angles(REF, **kw)
    assert reg_db.store[PUBLIC] == before


def test_set_reference_angles_nested_report_raises_type_error(reg_db):
    before = _seed(reg_db, "processing", job_id="A", lease_until=T0 + LEASE_MS)
    kw = _angles_kwargs(keypoint_report={"rows": [[0.1, 0.2], [0.3, 0.4]]})
    with pytest.raises(TypeError):
        fa.set_reference_angles(REF, **kw)
    assert reg_db.store[PUBLIC] == before


@pytest.mark.parametrize("fps", [0, None, -1.0])
def test_set_reference_angles_real_fps_invalid_raises(reg_db, fps):
    _seed(reg_db, "processing", job_id="A", lease_until=T0 + LEASE_MS)
    with pytest.raises(ValueError, match="real_fps"):
        fa.set_reference_angles(REF, **_angles_kwargs(real_fps=fps))


def test_set_reference_angles_stale_job_false_no_change(reg_db):
    before = _seed(reg_db, "processing", job_id="B", lease_until=T0 + LEASE_MS)
    assert fa.set_reference_angles(REF, **_angles_kwargs(job_id="A")) is False
    assert reg_db.store[PUBLIC] == before


# ─────────────────────── begin_self_check / self_check_authorized (R2 · R8) ───────────────────────


@pytest.mark.parametrize("status", ["review", "active"])
def test_begin_self_check_review_or_active_and_job_match(reg_db, status):
    """quick-261001-thx — review 중에도 자기 재현성이 돈다(selfScore 가 검수 재료)."""
    _seed(reg_db, status, job_id="A", videoS3Key=FINAL_KEY)
    assert fa.begin_self_check(REF, job_id="A", analysis_id="a1") is True
    doc = reg_db.store[PUBLIC]
    assert doc["selfCheckAnalysisId"] == "a1"
    assert doc["selfCheckStatus"] == "pending"
    assert doc["selfCheckJobId"] == "A"
    assert doc["updatedAt"] == T0


@pytest.mark.parametrize(
    "status,job_id",
    [("processing", "A"), ("active", "B"), ("failed", "A")],
    ids=["processing", "stale-job", "failed"],
)
def test_begin_self_check_false_unless_review_or_active_with_job(reg_db, status, job_id):
    before = _seed(reg_db, status, job_id=job_id)
    assert fa.begin_self_check(REF, job_id="A", analysis_id="a1") is False
    assert reg_db.store[PUBLIC] == before


def test_begin_self_check_requires_analysis_id(reg_db):
    _seed(reg_db, "active", job_id="A")
    with pytest.raises(ValueError):
        fa.begin_self_check(REF, job_id="A", analysis_id="")


_REF_DOC = {"supplierUid": "u1", "selfCheckAnalysisId": "a1", "selfCheckJobId": "A"}


def test_self_check_authorized_true_when_all_match():
    assert fa.self_check_authorized(_REF_DOC, uid="u1", analysis_id="a1", job_id="A") is True


def test_self_check_authorized_forged_marker_false():
    """정상 사용자 u9 가 자기 분석 doc 에 남의 refId 표식을 넣었다 — supplierUid != u9."""
    assert fa.self_check_authorized(_REF_DOC, uid="u9", analysis_id="a1", job_id="A") is False


def test_self_check_authorized_other_supplier_ref_false():
    other = {**_REF_DOC, "supplierUid": "u2"}
    assert fa.self_check_authorized(other, uid="u1", analysis_id="a1", job_id="A") is False


def test_self_check_authorized_stale_analysis_id_false():
    assert fa.self_check_authorized(_REF_DOC, uid="u1", analysis_id="a0", job_id="A") is False


def test_self_check_authorized_stale_job_false():
    assert fa.self_check_authorized(_REF_DOC, uid="u1", analysis_id="a1", job_id="Z") is False


def test_self_check_authorized_completion_before_pending_false():
    """pending 선기록 전 — selfCheckAnalysisId 가 없다(R8)."""
    doc = {"supplierUid": "u1", "registrationStatus": "active", "jobId": "A"}
    assert fa.self_check_authorized(doc, uid="u1", analysis_id="a1", job_id="A") is False


@pytest.mark.parametrize("doc", [None, {}], ids=["none", "empty"])
def test_self_check_authorized_none_or_empty_false(doc):
    assert fa.self_check_authorized(doc, uid="u1", analysis_id="a1", job_id="A") is False


def test_self_check_authorized_empty_inputs_never_match_missing_fields():
    doc = {"supplierUid": "u1", "selfCheckAnalysisId": None, "selfCheckJobId": None}
    assert fa.self_check_authorized(doc, uid="u1", analysis_id=None, job_id=None) is False
    assert fa.self_check_authorized(doc, uid="u1", analysis_id="", job_id="") is False


def test_self_check_authorized_is_pure(monkeypatch):
    for seam in ("_db", "_doc", "_collection", "_run_in_transaction"):
        monkeypatch.setattr(fa, seam, lambda *a, **k: (_ for _ in ()).throw(AssertionError(seam)))
    assert fa.self_check_authorized(_REF_DOC, uid="u1", analysis_id="a1", job_id="A") is True


# ─────────────────────── approve / reject (quick-261001-thx — 사람 검수) ───────────────────────


def _seed_review(db, **extra) -> dict:
    doc = _seed(db, "review", job_id="A", videoS3Key=FINAL_KEY, **extra)
    db._apply("set", PRIVATE, {"supplierUid": "u1", "registrationDiagnostics": dict(_DIAG)}, False)
    return doc


def test_approve_review_to_active_with_private_review_record(reg_db):
    _seed_review(reg_db)
    assert fa.approve_reference_registration(REF, by="ops:belle") == "approved"
    pub = reg_db.store[PUBLIC]
    assert pub["registrationStatus"] == "active" and pub["isActive"] is True
    assert pub["registrationUpdatedAt"] == T0 and pub["updatedAt"] == T0
    assert "review" not in pub  # 누가/언제는 비공개 doc 에만(R13)
    prv = reg_db.store[PRIVATE]
    assert prv["review"] == {"decision": "approved", "by": "ops:belle", "at": T0}
    assert prv["registrationDiagnostics"] == _DIAG  # merge — 진단 보존
    assert reg_db.read_after_write_seen is False


def test_approve_is_idempotent_already_approved_writes_nothing(reg_db):
    _seed_review(reg_db)
    assert fa.approve_reference_registration(REF, by="ops:belle") == "approved"
    commits = reg_db.commit_count
    pub, prv = copy.deepcopy(reg_db.store[PUBLIC]), copy.deepcopy(reg_db.store[PRIVATE])
    assert fa.approve_reference_registration(REF, by="ops:other") == "already_approved"
    assert reg_db.store[PUBLIC] == pub and reg_db.store[PRIVATE] == prv
    assert reg_db.commit_count <= commits + 1  # 읽기 전용 트랜잭션 — 쓰기 0


@pytest.mark.parametrize("status", ["processing", "failed", "registering", "queued", "expired"])
def test_approve_from_other_states_raises(reg_db, status):
    before = _seed(reg_db, status, job_id="A")
    with pytest.raises(ValueError):
        fa.approve_reference_registration(REF, by="ops:belle")
    assert reg_db.store[PUBLIC] == before


def test_approve_active_without_approved_record_raises(reg_db):
    """active 인데 비공개 review.decision 이 approved 가 아니다(예: 옛 active 경로) — 이 CLI 의 대상이 아니다."""
    before = _seed(reg_db, "active", job_id="A")
    with pytest.raises(ValueError):
        fa.approve_reference_registration(REF, by="ops:belle")
    assert reg_db.store[PUBLIC] == before


def test_approve_missing_doc_raises(reg_db):
    with pytest.raises(ValueError):
        fa.approve_reference_registration(REF, by="ops:belle")


def test_reject_review_to_failed_with_reason(reg_db):
    _seed_review(reg_db)
    assert fa.reject_reference_registration(REF, reason="화면이 어두워요", by="ops:belle") == "rejected"
    pub = reg_db.store[PUBLIC]
    assert pub["registrationStatus"] == "failed" and pub["isActive"] is False
    assert pub["registrationUpdatedAt"] == T0
    prv = reg_db.store[PRIVATE]
    msg = models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_REJECTED].replace("{reason}", "화면이 어두워요")
    assert prv["registrationError"] == {"code": "rejected", "message": msg, "reason": "화면이 어두워요"}
    assert "{reason}" not in prv["registrationError"]["message"]
    assert prv["review"] == {"decision": "rejected", "by": "ops:belle", "at": T0, "reason": "화면이 어두워요"}
    assert reg_db.read_after_write_seen is False


def test_reject_is_idempotent_already_rejected_writes_nothing(reg_db):
    _seed_review(reg_db)
    assert fa.reject_reference_registration(REF, reason="화면이 어두워요", by="ops:belle") == "rejected"
    pub, prv = copy.deepcopy(reg_db.store[PUBLIC]), copy.deepcopy(reg_db.store[PRIVATE])
    assert fa.reject_reference_registration(REF, reason="다른 사유", by="ops:x") == "already_rejected"
    assert reg_db.store[PUBLIC] == pub and reg_db.store[PRIVATE] == prv


def test_reject_active_raises_unpublish_out_of_scope(reg_db):
    _seed_review(reg_db)
    assert fa.approve_reference_registration(REF, by="ops:belle") == "approved"
    before = copy.deepcopy(reg_db.store[PUBLIC])
    with pytest.raises(ValueError):
        fa.reject_reference_registration(REF, reason="사유", by="ops:belle")
    assert reg_db.store[PUBLIC] == before


@pytest.mark.parametrize("status", ["processing", "registering", "queued", "expired"])
def test_reject_from_other_states_raises(reg_db, status):
    before = _seed(reg_db, status, job_id="A")
    with pytest.raises(ValueError):
        fa.reject_reference_registration(REF, reason="사유", by="ops:belle")
    assert reg_db.store[PUBLIC] == before


def test_reject_machine_failed_doc_raises(reg_db):
    """기계 실패(예: no_human)로 failed 인 doc 은 반려 대상이 아니다 — already_rejected 로 위장하지 않는다."""
    before = _seed(reg_db, "failed", job_id="A")
    reg_db._apply("set", PRIVATE, {"registrationError": {"code": "no_human", "message": "m"}}, False)
    with pytest.raises(ValueError):
        fa.reject_reference_registration(REF, reason="사유", by="ops:belle")
    assert reg_db.store[PUBLIC] == before


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_reject_requires_reason(reg_db, bad):
    before = _seed_review(reg_db)
    with pytest.raises(ValueError):
        fa.reject_reference_registration(REF, reason=bad, by="ops:belle")
    assert reg_db.store[PUBLIC] == before


@pytest.mark.parametrize("fn", ["approve", "reject"])
def test_approve_reject_require_by(reg_db, fn):
    _seed_review(reg_db)
    with pytest.raises(ValueError):
        if fn == "approve":
            fa.approve_reference_registration(REF, by="")
        else:
            fa.reject_reference_registration(REF, reason="사유", by="")


def test_deactivate_active_sets_is_active_false_and_private_record(reg_db):
    """승인 뒤 내리기 — 상태는 active 그대로, isActive False(picker 에서 빠짐), 누가/언제/사유는 비공개에만."""
    _seed_review(reg_db)
    assert fa.approve_reference_registration(REF, by="ops:belle") == "approved"
    assert fa.deactivate_reference_registration(REF, by="ops:belle", reason="  다른 영상으로 바꿈 ") == "deactivated"
    pub = reg_db.store[PUBLIC]
    assert pub["registrationStatus"] == "active" and pub["isActive"] is False
    assert "deactivation" not in pub
    prv = reg_db.store[PRIVATE]
    assert prv["deactivation"] == {"by": "ops:belle", "at": T0, "reason": "다른 영상으로 바꿈"}
    assert prv["review"]["decision"] == "approved"  # merge — 승인 기록 보존
    assert reg_db.read_after_write_seen is False


def test_deactivate_without_reason_has_no_reason_key(reg_db):
    _seed(reg_db, "active", job_id="A")
    assert fa.deactivate_reference_registration(REF, by="ops:belle") == "deactivated"
    assert reg_db.store[PRIVATE]["deactivation"] == {"by": "ops:belle", "at": T0}


def test_deactivate_is_idempotent_already_inactive_writes_nothing(reg_db):
    _seed(reg_db, "active", job_id="A")
    assert fa.deactivate_reference_registration(REF, by="ops:belle") == "deactivated"
    pub, prv = copy.deepcopy(reg_db.store[PUBLIC]), copy.deepcopy(reg_db.store[PRIVATE])
    assert fa.deactivate_reference_registration(REF, by="ops:x", reason="또") == "already_inactive"
    assert reg_db.store[PUBLIC] == pub and reg_db.store[PRIVATE] == prv


@pytest.mark.parametrize("status", ["review", "processing", "failed", "registering", "queued", "expired"])
def test_deactivate_non_active_raises(reg_db, status):
    before = _seed(reg_db, status, job_id="A")
    with pytest.raises(ValueError):
        fa.deactivate_reference_registration(REF, by="ops:belle")
    assert reg_db.store[PUBLIC] == before
    assert PRIVATE not in reg_db.store


def test_deactivate_missing_doc_and_long_reason_raise(reg_db):
    with pytest.raises(ValueError):
        fa.deactivate_reference_registration(REF, by="ops:belle")
    before = _seed(reg_db, "active", job_id="A")
    with pytest.raises(ValueError):
        fa.deactivate_reference_registration(REF, by="ops:belle", reason="가" * 201)
    with pytest.raises(ValueError):
        fa.deactivate_reference_registration(REF, by="")
    assert reg_db.store[PUBLIC] == before


# ─────────────────────── set_reference_self_check (R2 · R8) ───────────────────────


def _seed_self_check(db) -> dict:
    return _seed(
        db, "active", job_id="A", videoS3Key=FINAL_KEY,
        selfCheckAnalysisId="a1", selfCheckStatus="pending", selfCheckJobId="A",
    )


def test_set_reference_self_check_done_writes_score(reg_db):
    _seed_self_check(reg_db)
    assert fa.set_reference_self_check(
        REF, status="done", uid="u1", analysis_id="a1", job_id="A", score=97.3
    ) is True
    doc = reg_db.store[PUBLIC]
    assert doc["selfCheckStatus"] == "done"
    assert doc["selfScore"] == 97.3
    assert doc["selfScoreUpdatedAt"] == T0 and doc["updatedAt"] == T0
    assert doc["selfCheckAnalysisId"] == "a1"  # 표식 보존


def test_set_reference_self_check_failed_has_no_score_key(reg_db):
    _seed_self_check(reg_db)
    assert fa.set_reference_self_check(
        REF, status="failed", uid="u1", analysis_id="a1", job_id="A"
    ) is True
    doc = reg_db.store[PUBLIC]
    assert doc["selfCheckStatus"] == "failed"
    assert "selfScore" not in doc


@pytest.mark.parametrize(
    "uid,analysis_id,job_id",
    [("u9", "a1", "A"), ("u1", "a0", "A"), ("u1", "a1", "Z")],
    ids=["forged-uid", "stale-analysis", "stale-job"],
)
def test_set_reference_self_check_unauthorized_false_no_change(reg_db, caplog, uid, analysis_id, job_id):
    before = _seed_self_check(reg_db)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert fa.set_reference_self_check(
            REF, status="done", uid=uid, analysis_id=analysis_id, job_id=job_id, score=50.0
        ) is False
    assert reg_db.store[PUBLIC] == before
    assert any("self_check" in r.getMessage() for r in caplog.records)


def test_completion_hook_before_pending_is_skipped(reg_db):
    """완료 훅이 pending 선기록보다 먼저 왔다(R8) — doc 에 표식이 없으니 스킵."""
    before = _seed(reg_db, "active", job_id="A", videoS3Key=FINAL_KEY)
    assert fa.set_reference_self_check(
        REF, status="done", uid="u1", analysis_id="a1", job_id="A", score=99.0
    ) is False
    assert reg_db.store[PUBLIC] == before


def test_set_reference_self_check_missing_doc_false(reg_db):
    assert fa.set_reference_self_check(
        REF, status="done", uid="u1", analysis_id="a1", job_id="A", score=1.0
    ) is False


def test_set_reference_self_check_invalid_status_raises(reg_db):
    _seed_self_check(reg_db)
    with pytest.raises(ValueError):
        fa.set_reference_self_check(REF, status="finished", uid="u1", analysis_id="a1", job_id="A")


def test_set_reference_self_check_done_without_score_raises(reg_db):
    before = _seed_self_check(reg_db)
    with pytest.raises(ValueError):
        fa.set_reference_self_check(REF, status="done", uid="u1", analysis_id="a1", job_id="A")
    with pytest.raises(ValueError):
        fa.set_reference_self_check(
            REF, status="done", uid="u1", analysis_id="a1", job_id="A", score=float("nan")
        )
    assert reg_db.store[PUBLIC] == before


# ─────────────────────── create_analysis_doc ───────────────────────


class _CreateOnlyDoc:
    def __init__(self, log: list) -> None:
        self._log = log

    def create(self, payload: dict) -> None:
        self._log.append(("create", copy.deepcopy(payload)))

    def set(self, payload: dict, merge: bool = False) -> None:  # noqa: D401
        self._log.append(("set", payload, merge))


def test_create_analysis_doc_create_once_at_users_path(monkeypatch):
    calls: list = []
    paths: list[str] = []

    def _doc(path):
        paths.append(path)
        return _CreateOnlyDoc(calls)

    monkeypatch.setattr(fa, "_doc", _doc)
    payload = {"analysisId": "a1", "mode": "mode1", "status": "uploading",
               "referenceMotionId": REF, "createdAt": T0, "updatedAt": T0,
               models.ANALYSIS_FIELD_SELF_CHECK_FOR_REFERENCE: REF,
               models.ANALYSIS_FIELD_SELF_CHECK_JOB_ID: "A"}
    fa.create_analysis_doc("u1", "a1", payload)
    assert paths == [models.analysis_doc_path("u1", "a1")]
    assert calls == [("create", payload)]


@pytest.mark.parametrize("missing", ["analysisId", "mode", "status"])
def test_create_analysis_doc_missing_required_keys_raises(monkeypatch, missing):
    calls: list = []
    monkeypatch.setattr(fa, "_doc", lambda _p: _CreateOnlyDoc(calls))
    payload = {"analysisId": "a1", "mode": "mode1", "status": "uploading"}
    del payload[missing]
    with pytest.raises(ValueError, match=missing):
        fa.create_analysis_doc("u1", "a1", payload)
    assert calls == []


def test_create_analysis_doc_id_mismatch_raises(monkeypatch):
    calls: list = []
    monkeypatch.setattr(fa, "_doc", lambda _p: _CreateOnlyDoc(calls))
    with pytest.raises(ValueError):
        fa.create_analysis_doc("u1", "a1", {"analysisId": "a2", "mode": "mode1", "status": "uploading"})
    assert calls == []


# ─────────────────────── list_reference_registrations_by_status ───────────────────────


def test_list_reference_registrations_by_status_single_equality_query(fake_firestore):
    fake_firestore._apply("set", "reference/r-q1", {"registrationStatus": "queued", "supplierUid": "u1"}, False)
    fake_firestore._apply("set", "reference/r-q2", {"registrationStatus": "queued", "supplierUid": "u2"}, False)
    fake_firestore._apply("set", "reference/r-p", {"registrationStatus": "processing"}, False)
    fake_firestore._apply("set", "reference/ref-kip-up", {"name": "kip-up"}, False)  # legacy — status 없음
    fake_firestore._apply("set", "reference/r-q1/private/registration", {"registrationStatus": "queued"}, False)

    rows = fa.list_reference_registrations_by_status("queued")
    assert sorted(r["motionId"] for r in rows) == ["r-q1", "r-q2"]
    assert fake_firestore.query_log == [("reference", "registrationStatus", "==", "queued")]


def test_list_reference_registrations_by_status_accepts_review(fake_firestore):
    fake_firestore._apply("set", "reference/r-rv", {"registrationStatus": "review"}, False)
    rows = fa.list_reference_registrations_by_status(models.REGISTRATION_STATUS_REVIEW)
    assert [r["motionId"] for r in rows] == ["r-rv"]


def test_list_reference_registrations_by_status_rejects_unknown_status(fake_firestore):
    with pytest.raises(ValueError):
        fa.list_reference_registrations_by_status("done")
    assert fake_firestore.query_log == []
