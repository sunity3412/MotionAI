"""quick-260930-lfw Task 1 — 공급자 메일 초대: 순수 함수 + firestore_admin writer (실 Firestore 0).

38-DESIGN-v2 §W1 · 260930-lfw-PLAN 플래너 결정 (b)(c)(h).

잠그는 계약:
  · 메일 정규화(doc id 로 쓰므로 '/' 거부) · 새 코드 규칙(O·0·I·1·L 금지, 4~8자)
  · 초대 수락 가능 판정(pending + 만료 전, 경계 포함) · 명단 판정(suppliers doc 우선 → SSM ∪ BELLE_UID)
  · 수락 트랜잭션 — 세 doc 을 한 번에, 멱등 분기는 suppliers active True 일 때만(결정 (h))
  · 회수(deactivate)는 수락 초대까지 revoked, 되살리기는 reactivate 로만
  · 이관(upsert) 재실행 안전 · create/extend/revoke 규칙
테스트 메일은 전부 가짜 주소(example.com)다 — 실제 계정 앞글자 금지.
"""

from __future__ import annotations

import pytest

from sunity_shared import firestore_admin as fa
from sunity_shared import models
from sunity_shared.supplier_invites import (
    SupplierCodeConflict,
    SupplierEntry,
    invite_acceptable,
    mask_email,
    normalize_invite_email,
    roster_decision,
    validate_invite_code,
)
from tests.phase31.conftest import fake_firestore  # noqa: F401 — 픽스처 재등록(디렉터리 밖)

T0 = 1_700_000_000_000
DAY_MS = 86_400_000
EMAIL = "person@example.com"
EMAIL2 = "other@example.com"


# ─────────────────────── 순수 함수 ───────────────────────


def test_normalize_invite_email_strips_and_lowers():
    assert normalize_invite_email("  Eun.Ji@Example.COM ") == "eun.ji@example.com"


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "no-at-sign", "a b@example.com", "a/b@example.com", "a@b/c.com", "a@@b.com",
     "__a@b.com__", None, 123],
)
def test_normalize_invite_email_rejects(bad):
    with pytest.raises(ValueError):
        normalize_invite_email(bad)


def test_normalize_invite_email_length_cap():
    with pytest.raises(ValueError):
        normalize_invite_email("a" * 250 + "@b.com")


@pytest.mark.parametrize("raw,want", [(" mx kr ", "MXKR"), ("QZ2TEST", "QZ2TEST"), ("abcd", "ABCD")])
def test_validate_invite_code_normalizes(raw, want):
    assert validate_invite_code(raw) == want


@pytest.mark.parametrize(
    "bad", ["eunji", "ABC", "ABCDEFGHJ", "AB0C", "AB1C", "ABOC", "ABLC", "ABIC", "", "AB-C", None]
)
def test_validate_invite_code_rejects(bad):
    with pytest.raises(ValueError):
        validate_invite_code(bad)


def test_invite_acceptable_boundary_and_status():
    assert invite_acceptable({"status": "pending", "expiresAt": T0 + 1, "code": "MXKR"}, now_ms=T0) is True
    assert invite_acceptable({"status": "pending", "expiresAt": T0, "code": "MXKR"}, now_ms=T0) is False
    assert invite_acceptable({"status": "accepted", "expiresAt": T0 + 1, "code": "MXKR"}, now_ms=T0) is False
    assert invite_acceptable({"status": "revoked", "expiresAt": T0 + 1, "code": "MXKR"}, now_ms=T0) is False


@pytest.mark.parametrize(
    "doc",
    [None, {}, {"status": "pending"}, {"status": "pending", "expiresAt": "x", "code": "MXKR"},
     {"status": "pending", "expiresAt": True, "code": "MXKR"},
     {"status": "pending", "expiresAt": T0 + 1}, {"status": "pending", "expiresAt": T0 + 1, "code": 5},
     "not-a-dict"],
)
def test_invite_acceptable_malformed_is_false(doc):
    assert invite_acceptable(doc, now_ms=T0) is False


def test_roster_decision_doc_first_then_ssm_then_belle():
    doc = {"active": True, "code": "MXKR", "displayName": "정은지"}
    assert roster_decision(doc, {}, "", "u1") == SupplierEntry(code="MXKR", display_name="정은지")
    # doc 이 있으면 active 가 결정한다 — SSM 에 있어도 막힌다(결정 (b)).
    assert roster_decision({"active": False}, {"u1": "BELLE"}, "u1", "u1") is None
    assert roster_decision(None, {"u1": "BELLE"}, "", "u1") == SupplierEntry("BELLE", None)
    assert roster_decision(None, {}, "belle-1", "belle-1") == SupplierEntry(None, None)
    assert roster_decision(None, {}, "belle-1", "u9") is None
    assert roster_decision(None, {}, "", "") is None  # 빈 BELLE_UID 는 통과 재료가 아니다
    assert roster_decision(None, {"u2": None}, "", "u2") == SupplierEntry(None, None)


def test_mask_email():
    assert mask_email(EMAIL) == "p***@example.com"
    for bad in (None, "", "noat", "@example.com", 5):
        assert mask_email(bad) == "***"


# ─────────────────────── Firestore writer (fake) ───────────────────────

INV = models.supplier_invite_path(EMAIL)
SUP = models.supplier_path("u1")
CODE = models.supplier_code_path("MXKR")


@pytest.fixture
def db(fake_firestore, monkeypatch):
    monkeypatch.setattr(fa, "_now_ms", lambda: T0)
    return fake_firestore


def _pending(db, email=EMAIL, code="MXKR", name="정은지", expires=T0 + 14 * DAY_MS):
    db.store[models.supplier_invite_path(email)] = {
        "email": email, "code": code, "displayName": name, "createdAt": T0,
        "expiresAt": expires, "status": "pending", "acceptedUid": None, "acceptedAt": None,
    }


def test_create_invite_writes_pending_doc(db):
    fa.create_supplier_invite(" Person@Example.com ", " mx kr ", "정은지", days=14, now_ms=T0)
    assert db.store[INV] == {
        "email": EMAIL, "code": "MXKR", "displayName": "정은지", "createdAt": T0,
        "expiresAt": T0 + 14 * DAY_MS, "status": "pending", "acceptedUid": None, "acceptedAt": None,
    }


def test_create_invite_rejects_existing_code_doc(db):
    db.store[CODE] = {"supplierUid": "u7", "displayName": "x", "active": True}
    with pytest.raises(ValueError):
        fa.create_supplier_invite(EMAIL, "MXKR", "정은지", days=14, now_ms=T0)
    assert INV not in db.store


def test_create_invite_rejects_code_on_other_pending_invite(db):
    _pending(db, email=EMAIL2, code="MXKR")
    with pytest.raises(ValueError):
        fa.create_supplier_invite(EMAIL, "MXKR", "정은지", days=14, now_ms=T0)
    assert INV not in db.store


def test_create_invite_rejects_same_email_pending(db):
    _pending(db)
    with pytest.raises(ValueError, match="extend"):
        fa.create_supplier_invite(EMAIL, "QZTEST", "정은지", days=14, now_ms=T0)
    assert db.store[INV]["code"] == "MXKR"


@pytest.mark.parametrize("status", ["accepted", "revoked"])
def test_create_invite_rejects_email_with_accepted_uid(db, status):
    _pending(db)
    db.store[INV].update({"status": status, "acceptedUid": "u1", "acceptedAt": T0})
    with pytest.raises(ValueError, match="reactivate"):
        fa.create_supplier_invite(EMAIL, "QZTEST", "정은지", days=14, now_ms=T0 + 1)
    assert db.store[INV]["status"] == status


def test_create_invite_overwrites_revoked_before_accept(db):
    _pending(db)
    db.store[INV].update({"status": "revoked", "revokedAt": T0})
    fa.create_supplier_invite(EMAIL, "QZTEST", "정은지", days=7, now_ms=T0 + 5)
    doc = db.store[INV]
    assert doc["status"] == "pending" and doc["code"] == "QZTEST"
    assert doc["expiresAt"] == T0 + 5 + 7 * DAY_MS
    assert "revokedAt" not in doc


@pytest.mark.parametrize("days", [0, models.SUPPLIER_INVITE_MAX_DAYS + 1])
def test_create_invite_rejects_days_out_of_range(db, days):
    with pytest.raises(ValueError):
        fa.create_supplier_invite(EMAIL, "MXKR", "정은지", days=days, now_ms=T0)


def test_extend_invite_pending_only(db):
    _pending(db)
    before = dict(db.store[INV])
    fa.extend_supplier_invite(EMAIL, days=30, now_ms=T0 + 100)
    after = db.store[INV]
    assert after["expiresAt"] == T0 + 100 + 30 * DAY_MS
    assert {k: v for k, v in after.items() if k != "expiresAt"} == {
        k: v for k, v in before.items() if k != "expiresAt"
    }
    with pytest.raises(ValueError):
        fa.extend_supplier_invite(EMAIL, days=models.SUPPLIER_INVITE_MAX_DAYS + 1, now_ms=T0)
    with pytest.raises(ValueError):
        fa.extend_supplier_invite(EMAIL, days=0, now_ms=T0)


@pytest.mark.parametrize("status", ["accepted", "revoked", None])
def test_extend_invite_non_pending_rejected_no_write(db, status):
    if status is not None:
        _pending(db)
        db.store[INV]["status"] = status
    snapshot = dict(db.store)
    with pytest.raises(ValueError):
        fa.extend_supplier_invite(EMAIL, days=14, now_ms=T0)
    assert db.store == snapshot


def test_revoke_invite(db):
    _pending(db)
    fa.revoke_supplier_invite(EMAIL)
    assert db.store[INV]["status"] == "revoked" and db.store[INV]["acceptedUid"] is None
    db.store[INV].update({"status": "accepted", "acceptedUid": "u1"})
    with pytest.raises(ValueError, match="deactivate"):
        fa.revoke_supplier_invite(EMAIL)
    assert db.store[INV]["status"] == "accepted"
    with pytest.raises(ValueError):
        fa.revoke_supplier_invite(EMAIL2)


def test_upsert_supplier_idempotent(db):
    assert fa.upsert_supplier("u1", email="Person@Example.com", code="BELLE", display_name="벨",
                              active=True, since_ms=T0) is True
    sup = db.store[SUP]
    assert sup == {"email": EMAIL, "code": "BELLE", "displayName": "벨", "active": True, "since": T0}
    assert db.store[models.supplier_code_path("BELLE")] == {
        "supplierUid": "u1", "displayName": "벨", "active": True,
    }
    snapshot = {k: dict(v) for k, v in db.store.items()}
    assert fa.upsert_supplier("u1", email=EMAIL, code="BELLE", display_name="다른",
                              active=True, since_ms=T0 + 9) is False
    assert db.store == snapshot


def test_upsert_supplier_without_code(db):
    assert fa.upsert_supplier("u2", email=None, code=None, display_name=None,
                              active=True, since_ms=T0) is True
    assert db.store[models.supplier_path("u2")]["code"] is None
    assert not any(k.startswith("supplierCodes/") for k in db.store)


def test_accept_creates_three_docs(db):
    _pending(db)
    entry = fa.accept_supplier_invite("u1", " Person@Example.com", now_ms=T0 + 10)
    assert entry == SupplierEntry(code="MXKR", display_name="정은지")
    assert db.store[SUP] == {"email": EMAIL, "code": "MXKR", "displayName": "정은지",
                             "active": True, "since": T0 + 10}
    assert db.store[CODE] == {"supplierUid": "u1", "displayName": "정은지", "active": True}
    inv = db.store[INV]
    assert inv["status"] == "accepted" and inv["acceptedUid"] == "u1" and inv["acceptedAt"] == T0 + 10
    assert db.read_after_write_seen is False


@pytest.mark.parametrize("case", ["missing", "expired", "revoked"])
def test_accept_returns_none_without_write(db, case):
    if case != "missing":
        _pending(db, expires=T0 if case == "expired" else T0 + DAY_MS)
        if case == "revoked":
            db.store[INV]["status"] = "revoked"
    snapshot = {k: dict(v) for k, v in db.store.items()}
    assert fa.accept_supplier_invite("u1", EMAIL, now_ms=T0) is None
    assert db.store == snapshot


def test_accept_idempotent_for_same_uid_active(db):
    _pending(db)
    first = fa.accept_supplier_invite("u1", EMAIL, now_ms=T0)
    snapshot = {k: dict(v) for k, v in db.store.items()}
    assert fa.accept_supplier_invite("u1", EMAIL, now_ms=T0 + 5) == first
    assert db.store == snapshot


def test_accept_accepted_invite_other_uid_is_none(db):
    _pending(db)
    fa.accept_supplier_invite("u1", EMAIL, now_ms=T0)
    snapshot = {k: dict(v) for k, v in db.store.items()}
    assert fa.accept_supplier_invite("u2", EMAIL, now_ms=T0) is None
    assert db.store == snapshot


def test_accept_accepted_invite_with_inactive_supplier_is_none(db):
    """BLOCKER 1 — 수락된 초대 + suppliers active False → None, 쓰기 0."""
    _pending(db)
    fa.accept_supplier_invite("u1", EMAIL, now_ms=T0)
    db.store[SUP]["active"] = False
    snapshot = {k: dict(v) for k, v in db.store.items()}
    assert fa.accept_supplier_invite("u1", EMAIL, now_ms=T0) is None
    assert db.store == snapshot


def test_accept_accepted_invite_with_missing_supplier_is_none(db):
    _pending(db)
    db.store[INV].update({"status": "accepted", "acceptedUid": "u1", "acceptedAt": T0})
    snapshot = {k: dict(v) for k, v in db.store.items()}
    assert fa.accept_supplier_invite("u1", EMAIL, now_ms=T0) is None
    assert db.store == snapshot


def test_inactive_supplier_cannot_accept_new_pending_invite(db):
    """되살리기는 reactivate 로만 — active False uid 는 새 초대도 수락 못 한다(결정 (h))."""
    db.store[SUP] = {"active": False}
    _pending(db)
    snapshot = {k: dict(v) for k, v in db.store.items()}
    assert fa.accept_supplier_invite("u1", EMAIL, now_ms=T0) is None
    assert db.store == snapshot


def test_accept_code_owned_by_other_uid_raises_without_write(db):
    _pending(db)
    db.store[CODE] = {"supplierUid": "u7", "displayName": "x", "active": True}
    snapshot = {k: dict(v) for k, v in db.store.items()}
    with pytest.raises(SupplierCodeConflict):
        fa.accept_supplier_invite("u1", EMAIL, now_ms=T0)
    assert db.store == snapshot


def test_accept_malformed_email_is_none(db):
    assert fa.accept_supplier_invite("u1", "not an email", now_ms=T0) is None


def test_accept_contended_same_uid_single_supplier(db, monkeypatch):
    _pending(db)
    captured = []
    monkeypatch.setattr(fa, "_run_in_transaction", lambda fn: captured.append(fn))
    fa.accept_supplier_invite("u1", EMAIL, now_ms=T0)
    fa.accept_supplier_invite("u1", EMAIL, now_ms=T0 + 1)
    a, b = db.run_contended(*captured)
    assert a == b == SupplierEntry("MXKR", "정은지")
    assert db.conflict_count == 1
    assert [k for k in db.store if k.startswith("suppliers/")] == [SUP]
    assert db.store[SUP]["since"] == T0
    assert db.read_after_write_seen is False


def test_deactivate_revokes_accepted_invite_and_blocks_accept(db):
    _pending(db)
    fa.accept_supplier_invite("u1", EMAIL, now_ms=T0)
    out = fa.set_supplier_active("u1", False, now_ms=T0 + 50)
    assert out == {"code": "MXKR", "revokedInvite": "p***@example.com"}
    assert db.store[SUP]["active"] is False
    assert db.store[CODE]["active"] is False
    inv = db.store[INV]
    assert inv["status"] == "revoked" and inv["revokedAt"] == T0 + 50
    assert inv["acceptedUid"] == "u1" and inv["acceptedAt"] == T0  # 이력으로 남긴다
    snapshot = {k: dict(v) for k, v in db.store.items()}
    assert fa.accept_supplier_invite("u1", EMAIL, now_ms=T0 + 60) is None
    assert db.store == snapshot
    assert roster_decision(fa.get_supplier("u1"), {"u1": "MXKR"}, "", "u1") is None
    assert db.read_after_write_seen is False


def test_deactivate_ssm_only_uid_creates_inactive_doc(db):
    out = fa.set_supplier_active("u5", False, now_ms=T0)
    assert out == {"code": None, "revokedInvite": None}
    assert db.store[models.supplier_path("u5")] == {"active": False}
    assert roster_decision(fa.get_supplier("u5"), {"u5": "BELLE"}, "", "u5") is None


def test_reactivate_restores_supplier_and_code_not_invite(db):
    _pending(db)
    fa.accept_supplier_invite("u1", EMAIL, now_ms=T0)
    fa.set_supplier_active("u1", False, now_ms=T0 + 1)
    fa.set_supplier_active("u1", True, now_ms=T0 + 2)
    sup = fa.get_supplier("u1")
    assert sup["active"] is True
    assert db.store[CODE]["active"] is True
    assert db.store[INV]["status"] == "revoked"
    assert roster_decision(sup, {}, "", "u1") == SupplierEntry("MXKR", "정은지")


def test_reactivate_without_doc_raises(db):
    with pytest.raises(ValueError):
        fa.set_supplier_active("nobody", True, now_ms=T0)
    assert db.store == {}


def test_list_invites_and_suppliers(db):
    _pending(db)
    _pending(db, email=EMAIL2, code="QZTEST")
    fa.upsert_supplier("u1", email=None, code=None, display_name=None, active=True, since_ms=T0)
    invites = fa.list_supplier_invites()
    assert sorted(i["email"] for i in invites) == [EMAIL2, EMAIL]
    sups = fa.list_suppliers()
    assert [s["uid"] for s in sups] == ["u1"]


def test_get_supplier_missing_is_none(db):
    assert fa.get_supplier("zz") is None


# ─────────────────────── 입구(auth) · 응답(responses) ───────────────────────


@pytest.mark.parametrize(
    "decoded,want",
    [
        ({"uid": "u1", "email": EMAIL, "email_verified": True},
         {"uid": "u1", "email": EMAIL, "email_verified": True}),
        ({"uid": "u1", "email": EMAIL, "email_verified": "true"},
         {"uid": "u1", "email": EMAIL, "email_verified": False}),
        ({"uid": "u1"}, {"uid": "u1", "email": None, "email_verified": False}),
        ({"uid": "u1", "email": "", "email_verified": True},
         {"uid": "u1", "email": None, "email_verified": True}),
    ],
)
def test_verify_request_claims_reads_email_strictly(monkeypatch, decoded, want):
    from firebase_admin import auth as fb_auth

    from sunity_shared import auth

    monkeypatch.setattr(auth, "_ensure_firebase", lambda: None)
    monkeypatch.setattr(fb_auth, "verify_id_token", lambda token: dict(decoded))
    event = {"headers": {"Authorization": "Bearer t"}}
    assert auth.verify_request_claims(event) == want
    assert auth.verify_request(event) == "u1"  # 다른 5 함수의 입구는 그대로 uid


def test_responses_error_extra_cannot_override_code_or_message():
    import json

    from sunity_shared import responses

    resp = responses.error("not_invited", "m", status=403,
                           extra={"email": EMAIL, "code": "x", "message": "y"})
    assert resp["statusCode"] == 403
    assert json.loads(resp["body"]) == {"error": {"code": "not_invited", "message": "m", "email": EMAIL}}
    assert json.loads(responses.error("a", "b")["body"]) == {"error": {"code": "a", "message": "b"}}
