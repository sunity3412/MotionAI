"""Plan 38-06 Task 2 — reference-upload-url Lambda handler 테스트 (AWS/Firestore/SSM 0).

잠그는 계약(38-06-PLAN behavior · contract.md §2 POST /reference/upload-url · 리뷰 R4·R5):
  · 인증 실패 401 · 화이트리스트 밖 403(SSM 파라미터 부재/env 미설정 = 거부, 조용한 통과 금지)
  · `{"probe": true}` 는 판정 + supplierCode 만 돌려주고 presign·doc 부작용 0(D-12)
  · 정상 body: presign 이 **먼저**, 그 **뒤** 공개+비공개 doc batch create — create 가 실패하면
    URL 이 응답에 실리지 않는다(고아 객체 없음, R4). uploadExpiresAt = 서명 만료와 같은 상수.
  · 본문의 uid/refId 는 절대 읽지 않는다(V4) — 키·doc 은 토큰 uid + 서버 uuid4 hex 만.
  · 서명은 upload 키(`reference/{uid}/{refId}/upload.{ext}`)에만(R5).
외부 호출 0 — verify_request_claims / _load_supplier_map / _s3 / create_reference_registration /
get_supplier / accept_supplier_invite / boto3.client("ssm") 전부 monkeypatch
(test_reference_auto_register_handler.py 어법). 픽스처가 FIREBASE_SA_* env 를 지우고
firestore_admin._db 를 막아 둔다 — 셸에 SA 경로가 있어도 실 Firestore 에 닿지 않는다.

quick-260930-lfw(38-DESIGN-v2 §W1): 403 은 `not_invited`(error.email = 토큰 메일) 하나.
명단 판정 = suppliers/{uid} doc 우선 → SSM ∪ BELLE_UID → 검증 메일이면 초대 수락.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import pytest

from sunity_shared import models
from sunity_shared.s3keys import build_reference_upload_key
from sunity_shared.validation import ReferenceUploadRequest, validate_analysis_id_format
from tests.phase31.conftest import fake_firestore  # noqa: F401 — 픽스처 재등록(디렉터리 밖)

_HANDLER_DIR = Path(__file__).resolve().parents[1] / "functions" / "reference-upload-url"
_UPLOAD_URL_DIR = Path(__file__).resolve().parents[1] / "functions" / "upload-url"

OK_BODY = {
    "name": "킵업",
    "athleteName": "정은지",
    "level": "intermediate",
    "techniqueRefId": "ref-kip-up",
    "isCombo": False,
    "isSplit": True,
    "hasHold": False,
    "standingStart": True,
    "clipRange": {"execStartS": 1.5, "execEndS": 7},
    "consent": {"portrait": True, "usage": True, "silent": True, "training": True},
    "format": "mp4",
    "fileSizeBytes": 30 * 1024 * 1024,
    "durationSec": 12.4,
}


@pytest.fixture
def handler_module(monkeypatch):
    """app.py 를 모듈로 import — sys.path 주입 + env + 모듈 캐시 리셋(auto-register 테스트 어법)."""
    sys.path.insert(0, str(_HANDLER_DIR))
    monkeypatch.setenv("VIDEO_BUCKET", "test-bucket")
    monkeypatch.setenv("BELLE_UID", "belle-uid-001")
    monkeypatch.setenv("SUPPLIER_UIDS_PARAM", "/sunity/motion/supplier-uids-test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    for var in ("FIREBASE_SA_PATH", "FIREBASE_SA_JSON", "FIREBASE_SA_PARAM"):
        monkeypatch.delenv(var, raising=False)
    if "app" in sys.modules:
        del sys.modules["app"]
    import app  # noqa: PLC0415 — 동적 import 의도.

    def _no_real_firestore():
        raise AssertionError("테스트가 실 Firestore 에 닿으려 했다")

    monkeypatch.setattr(app.firestore_admin, "_db", _no_real_firestore)
    app._roster_cache.clear()
    yield app
    if "app" in sys.modules:
        del sys.modules["app"]
    sys.path.remove(str(_HANDLER_DIR))


# ─────────────────── helpers ───────────────────


def _bearer_event(body: dict, token: str = "valid-token") -> dict:
    return {"headers": {"Authorization": f"Bearer {token}"}, "body": json.dumps(body)}


class _FakeS3:
    def __init__(self, events: list[str], *, raise_exc: bool = False) -> None:
        self.events = events
        self.raise_exc = raise_exc
        self.calls: list[dict[str, Any]] = []

    def generate_presigned_url(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        self.events.append("presign")
        if self.raise_exc:
            raise RuntimeError("signing failed")
        return "https://s3.example/put?sig=1"


class _FakeCreate:
    def __init__(self, events: list[str], *, raise_exc: Exception | None = None) -> None:
        self.events = events
        self.raise_exc = raise_exc
        self.calls: list[dict[str, Any]] = []

    def __call__(self, ref_id: str, **kwargs: Any) -> None:
        self.calls.append({"ref_id": ref_id, **kwargs})
        self.events.append("create")
        if self.raise_exc is not None:
            raise self.raise_exc


def _claims(uid, email=None, verified=False):
    return {"uid": uid, "email": email, "email_verified": verified}


class _Recorder:
    """호출 인자를 기록하고 정해 둔 값을 돌려준다(예외면 던진다)."""

    def __init__(self, result=None) -> None:
        self.result = result
        self.calls: list[tuple] = []

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _wire(app, monkeypatch, *, uid="u1", supplier_map=None, belle_uid=None,
          presign_fail=False, create_exc=None, email=None, verified=False,
          supplier_doc=None, accept_result=None):
    """인증·명단·S3·Firestore 를 한 번에 붙인다. 반환 (events, s3, create).

    get_supplier(기본 None)·accept_supplier_invite(기본 None) 는 `app._get_supplier_stub`·
    `app._accept_stub` 로 꺼내 호출을 셀 수 있다.
    """
    if supplier_map is None:
        supplier_map = {"u1": "EUNJI", "u2": None}
    if belle_uid is not None:
        monkeypatch.setattr(app, "_BELLE_UID", belle_uid)
    monkeypatch.setattr(app, "verify_request_claims", lambda evt: _claims(uid, email, verified))
    monkeypatch.setattr(app, "_load_supplier_map", lambda: dict(supplier_map))
    get_stub = _Recorder(supplier_doc)
    accept_stub = _Recorder(accept_result)
    monkeypatch.setattr(app.firestore_admin, "get_supplier", get_stub)
    monkeypatch.setattr(app.firestore_admin, "accept_supplier_invite", accept_stub)
    app._get_supplier_stub = get_stub
    app._accept_stub = accept_stub
    events: list[str] = []
    s3 = _FakeS3(events, raise_exc=presign_fail)
    create = _FakeCreate(events, raise_exc=create_exc)
    monkeypatch.setattr(app, "_s3", s3)
    monkeypatch.setattr(app.firestore_admin, "create_reference_registration", create)
    return events, s3, create


# ─────────────────── 인증 · 화이트리스트 ───────────────────


def test_auth_error_returns_401(handler_module, monkeypatch):
    from sunity_shared.auth import AuthError

    def _raise(_evt):
        raise AuthError("인증이 필요합니다.")

    monkeypatch.setattr(handler_module, "verify_request_claims", _raise)
    resp = handler_module.lambda_handler({"headers": {}, "body": "{}"}, None)
    assert resp["statusCode"] == 401
    assert json.loads(resp["body"])["error"]["code"] == "unauthorized"


def test_empty_whitelist_and_no_belle_uid_returns_403(handler_module, monkeypatch):
    events, s3, create = _wire(handler_module, monkeypatch, uid="u1", supplier_map={}, belle_uid="")
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 403
    assert json.loads(resp["body"])["error"]["code"] == "not_invited"
    assert events == []


def test_uid_not_in_whitelist_returns_403(handler_module, monkeypatch, caplog):
    events, s3, create = _wire(handler_module, monkeypatch, uid="u9")
    with caplog.at_level(logging.WARNING):
        resp = handler_module.lambda_handler(_bearer_event(OK_BODY), None)
    assert resp["statusCode"] == 403
    assert json.loads(resp["body"])["error"]["code"] == "not_invited"
    assert events == []
    assert any("not_invited" in r.getMessage() and "u9" in r.getMessage() for r in caplog.records)


def test_belle_uid_passes_without_map_entry(handler_module, monkeypatch):
    _wire(handler_module, monkeypatch, uid="belle-uid-001", supplier_map={})
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body == {"probe": True, "uid": "belle-uid-001", "supplierCode": None, "displayName": None}


def test_roster_rules_via_authorize(handler_module, monkeypatch):
    """옛 _is_supplier 규칙이 roster_decision 경로에서 그대로 유지된다(doc 없음일 때)."""
    _wire(handler_module, monkeypatch)
    auth = handler_module._authorize
    monkeypatch.setattr(handler_module, "_BELLE_UID", "")
    assert auth(_claims("u1"), {}) is None
    handler_module._roster_cache.clear()
    assert auth(_claims("u1"), {"u1": None}) is not None
    handler_module._roster_cache.clear()
    assert auth(_claims(""), {}) is None  # env 미설정 = 빈 uid 도 통과 재료 아님
    monkeypatch.setattr(handler_module, "_BELLE_UID", "belle-uid-001")
    handler_module._roster_cache.clear()
    assert auth(_claims("belle-uid-001"), {}) is not None
    handler_module._roster_cache.clear()
    assert auth(_claims("u9"), {"u1": "EUNJI"}) is None


# ─────────────────── probe (D-12) ───────────────────


def test_probe_returns_whitelist_verdict_and_code_without_side_effects(handler_module, monkeypatch):
    events, s3, create = _wire(handler_module, monkeypatch, uid="u1")
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {
        "probe": True, "uid": "u1", "supplierCode": "EUNJI", "displayName": None,
    }
    assert events == []
    assert s3.calls == [] and create.calls == []


def test_probe_code_null_when_uid_has_no_code(handler_module, monkeypatch):
    _wire(handler_module, monkeypatch, uid="u2")
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert json.loads(resp["body"])["supplierCode"] is None


def test_probe_must_be_boolean_true(handler_module, monkeypatch):
    """`"probe": 1` / `"yes"` 는 probe 가 아니다 — 폼 검증으로 떨어져 400."""
    events, s3, create = _wire(handler_module, monkeypatch, uid="u1")
    for value in (1, "yes", "true"):
        resp = handler_module.lambda_handler(_bearer_event({"probe": value}), None)
        assert resp["statusCode"] == 400, value
        assert json.loads(resp["body"])["error"]["code"] == "bad_request"
    assert events == []


# ─────────────────── 정상 경로 (R4 순서 · R5 upload 키) ───────────────────


def test_happy_path_presign_then_create_then_200(handler_module, monkeypatch):
    events, s3, create = _wire(handler_module, monkeypatch, uid="u1")
    resp = handler_module.lambda_handler(_bearer_event(OK_BODY), None)

    assert resp["statusCode"] == 200, resp
    body = json.loads(resp["body"])
    assert set(body) == {"refId", "uploadUrl", "s3Key", "expiresInSec"}
    ref_id = body["refId"]
    assert validate_analysis_id_format(ref_id) and len(ref_id) == 32  # uuid4 hex
    assert body["uploadUrl"] == "https://s3.example/put?sig=1"
    assert body["s3Key"] == build_reference_upload_key("u1", ref_id, "mp4")
    assert body["s3Key"] == f"reference/u1/{ref_id}/upload.mp4"
    assert body["expiresInSec"] == models.REFERENCE_UPLOAD_EXPIRES_SEC == 900

    # 순서 — 서명 먼저, create 뒤 (R4).
    assert events == ["presign", "create"]

    # presign 인자 — upload-url 과 같은 Params, ContentType 없음, ExpiresIn = 한 상수.
    assert s3.calls == [
        {
            "ClientMethod": "put_object",
            "Params": {"Bucket": "test-bucket", "Key": body["s3Key"]},
            "ExpiresIn": 900,
        }
    ]

    # create 인자 — 토큰 uid · 서버 refId · 검증된 폼 · 만료 = 서명 만료와 같은 값.
    assert len(create.calls) == 1
    c = create.calls[0]
    assert c["ref_id"] == ref_id
    assert c["supplier_uid"] == "u1"
    assert isinstance(c["form"], ReferenceUploadRequest)
    assert c["form"].name == "킵업" and c["form"].clip_range == (1.5, 7.0)
    assert c["upload_key"] == body["s3Key"]
    assert isinstance(c["upload_expires_at_ms"], int) and isinstance(c["consent_at_ms"], int)
    assert c["upload_expires_at_ms"] - c["consent_at_ms"] == 900 * 1000
    assert c["supplier_code"] == "EUNJI"


def test_happy_path_mov_format_signs_mov_key(handler_module, monkeypatch):
    _events, s3, _create = _wire(handler_module, monkeypatch, uid="u2")
    resp = handler_module.lambda_handler(_bearer_event({**OK_BODY, "format": "mov"}), None)
    body = json.loads(resp["body"])
    assert body["s3Key"].endswith("/upload.mov")
    assert s3.calls[0]["Params"]["Key"] == body["s3Key"]


def test_body_uid_and_ref_id_are_ignored(handler_module, monkeypatch):
    """V4 — 본문 uid/refId 는 어떤 호출 인자에도 닿지 않는다."""
    events, s3, create = _wire(handler_module, monkeypatch, uid="u1")
    # techniqueRefId 는 정당한 폼 필드라 None 으로 비운다 — "ref-kip-up" 이 주입 refId 로만 남게.
    evil = {**OK_BODY, "techniqueRefId": None, "uid": "evil", "refId": "ref-kip-up"}
    resp = handler_module.lambda_handler(_bearer_event(evil), None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["refId"] != "ref-kip-up" and not body["refId"].startswith("ref-")
    assert body["s3Key"].startswith("reference/u1/")
    dump = repr(s3.calls) + repr(create.calls) + resp["body"]
    assert "evil" not in dump and "ref-kip-up" not in dump
    assert create.calls[0]["supplier_uid"] == "u1"
    assert create.calls[0]["ref_id"] == body["refId"]


def test_source_never_reads_body_uid_or_ref_id(handler_module):
    src = (_HANDLER_DIR / "app.py").read_text(encoding="utf-8")
    for pattern in ('body.get("uid")', 'body["uid"]', 'body.get("refId")', 'body["refId"]'):
        assert pattern not in src, pattern


# ─────────────────── 실패 경로 ───────────────────


def test_validation_error_maps_code_message_status(handler_module, monkeypatch):
    events, s3, create = _wire(handler_module, monkeypatch, uid="u1")
    resp = handler_module.lambda_handler(
        _bearer_event({**OK_BODY, "durationSec": 45.0, "isCombo": False}), None
    )
    assert resp["statusCode"] == 400
    err = json.loads(resp["body"])["error"]
    assert err == {
        "code": "too_long",
        "message": models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_LONG],
    }
    assert events == []


def test_presign_failure_500_no_doc_created(handler_module, monkeypatch):
    events, s3, create = _wire(handler_module, monkeypatch, uid="u1", presign_fail=True)
    resp = handler_module.lambda_handler(_bearer_event(OK_BODY), None)
    assert resp["statusCode"] == 500
    assert json.loads(resp["body"])["error"]["code"] == "server_error"
    assert events == ["presign"]
    assert create.calls == []


def test_create_failure_500_without_upload_url(handler_module, monkeypatch):
    """create 가 실패(AlreadyExists 포함)하면 URL 을 버린다 — 응답에 uploadUrl 없음(R4 고아 방지)."""
    events, s3, create = _wire(
        handler_module, monkeypatch, uid="u1", create_exc=RuntimeError("AlreadyExists")
    )
    resp = handler_module.lambda_handler(_bearer_event(OK_BODY), None)
    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert body["error"]["code"] == "server_error"
    assert "uploadUrl" not in resp["body"]
    assert "https://s3.example" not in resp["body"]
    assert events == ["presign", "create"]


# ─────────────────── SSM 화이트리스트 로더 (D-03) ───────────────────


class _FakeSSM:
    def __init__(self, value: str | None = None, exc: Exception | None = None) -> None:
        self.value = value
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    def get_parameter(self, **kwargs: Any) -> dict:
        self.calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        return {"Parameter": {"Value": self.value}}


def _wire_ssm(app, monkeypatch, fake_ssm: _FakeSSM) -> None:
    monkeypatch.setattr(app, "_supplier_cache", None)

    def _client(name, **_kw):
        assert name == "ssm"
        return fake_ssm

    monkeypatch.setattr(app.boto3, "client", _client)


def test_load_supplier_map_parses_ssm_value_and_caches(handler_module, monkeypatch):
    ssm = _FakeSSM(value="u1:EUNJI, u2, u3:bad code")
    _wire_ssm(handler_module, monkeypatch, ssm)
    m1 = handler_module._load_supplier_map()
    assert m1 == {"u1": "EUNJI", "u2": None, "u3": None}
    assert ssm.calls[0]["Name"] == "/sunity/motion/supplier-uids-test"
    m2 = handler_module._load_supplier_map()
    assert m2 == m1
    assert len(ssm.calls) == 1  # 60초 캐시


def test_load_supplier_map_cache_expires_after_ttl(handler_module, monkeypatch):
    ssm = _FakeSSM(value="u1:EUNJI")
    _wire_ssm(handler_module, monkeypatch, ssm)
    clock = [1000.0]
    monkeypatch.setattr(handler_module.time, "monotonic", lambda: clock[0])
    handler_module._load_supplier_map()
    clock[0] += handler_module._SUPPLIER_CACHE_TTL_S - 1
    handler_module._load_supplier_map()
    assert len(ssm.calls) == 1
    clock[0] += 2
    handler_module._load_supplier_map()
    assert len(ssm.calls) == 2


def test_load_supplier_map_ssm_failure_returns_empty_and_warns_without_value(
    handler_module, monkeypatch, caplog
):
    ssm = _FakeSSM(exc=RuntimeError("ParameterNotFound: secret-value-xyz"))
    _wire_ssm(handler_module, monkeypatch, ssm)
    with caplog.at_level(logging.WARNING):
        assert handler_module._load_supplier_map() == {}
    msgs = [r.getMessage() for r in caplog.records]
    assert any("supplier-uids" in m and "supplier-uids-test" in m for m in msgs)
    assert not any("secret-value-xyz" in m for m in msgs)  # 예외 본문 로그 금지
    # 실패는 캐시하지 않는다 — 다음 호출이 다시 SSM 을 본다.
    handler_module._load_supplier_map()
    assert len(ssm.calls) == 2


def test_ssm_failure_end_to_end_denies_all_but_belle(handler_module, monkeypatch):
    ssm = _FakeSSM(exc=RuntimeError("AccessDenied"))
    _wire_ssm(handler_module, monkeypatch, ssm)
    monkeypatch.setattr(handler_module.firestore_admin, "get_supplier", lambda uid: None)
    accept_calls = []
    monkeypatch.setattr(
        handler_module.firestore_admin,
        "accept_supplier_invite",
        lambda *a: accept_calls.append(a),
    )
    monkeypatch.setattr(handler_module, "verify_request_claims", lambda evt: _claims("u1"))
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 403
    monkeypatch.setattr(
        handler_module, "verify_request_claims", lambda evt: _claims("belle-uid-001")
    )
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 200
    assert accept_calls == []  # 메일 미인증 claims — 수락 시도 0


# ─────────────────── 모듈 상수 · requirements ───────────────────


def test_expires_constant_is_shared_with_models(handler_module):
    assert handler_module._EXPIRES == models.REFERENCE_UPLOAD_EXPIRES_SEC
    assert handler_module._SUPPLIER_CACHE_TTL_S == 60


def test_requirements_txt_copies_upload_url(handler_module):
    ours = (_HANDLER_DIR / "requirements.txt").read_text(encoding="utf-8")
    theirs = (_UPLOAD_URL_DIR / "requirements.txt").read_text(encoding="utf-8")
    assert ours == theirs


# ─────────────────── quick-260930-lfw — 메일 초대 · not_invited · 회수 ───────────────────

X_MAIL = "x@y.com"


def _probe(app):
    resp = app.lambda_handler(_bearer_event({"probe": True}), None)
    return resp["statusCode"], json.loads(resp["body"])


def test_probe_supplier_doc_active_returns_display_name(handler_module, monkeypatch):
    _wire(handler_module, monkeypatch, uid="u7", supplier_map={},
          supplier_doc={"active": True, "code": "MXKR", "displayName": "정은지"})
    status, body = _probe(handler_module)
    assert status == 200
    assert body == {"probe": True, "uid": "u7", "supplierCode": "MXKR", "displayName": "정은지"}
    assert handler_module._accept_stub.calls == []


def test_probe_ssm_only_returns_code_and_null_name(handler_module, monkeypatch):
    _wire(handler_module, monkeypatch, uid="u8", supplier_map={"u8": "BELLE"})
    status, body = _probe(handler_module)
    assert status == 200
    assert body["supplierCode"] == "BELLE" and body["displayName"] is None


def test_inactive_doc_overrides_ssm(handler_module, monkeypatch):
    _wire(handler_module, monkeypatch, uid="u8", supplier_map={"u8": "BELLE"},
          supplier_doc={"active": False})
    status, body = _probe(handler_module)
    assert status == 403 and body["error"]["code"] == "not_invited"


def test_verified_email_accepts_then_cache_serves_second_call(handler_module, monkeypatch):
    from sunity_shared.supplier_invites import SupplierEntry

    _wire(handler_module, monkeypatch, uid="u9", supplier_map={}, email=X_MAIL, verified=True,
          accept_result=SupplierEntry("QZTEST", "시험"))
    status, body = _probe(handler_module)
    assert status == 200
    assert body == {"probe": True, "uid": "u9", "supplierCode": "QZTEST", "displayName": "시험"}
    assert handler_module._accept_stub.calls[0][:2] == ("u9", X_MAIL)
    status2, _ = _probe(handler_module)
    assert status2 == 200
    assert len(handler_module._get_supplier_stub.calls) == 1  # 수락 직후 캐시 갱신
    assert len(handler_module._accept_stub.calls) == 1


def test_negative_cache_does_not_block_new_invite(handler_module, monkeypatch):
    """W3 — 첫 호출 403(캐시에 None) → 초대가 생김 → TTL 전 두 번째 호출 200."""
    from sunity_shared.supplier_invites import SupplierEntry

    _wire(handler_module, monkeypatch, uid="u9", supplier_map={}, email=X_MAIL, verified=True)
    status, _ = _probe(handler_module)
    assert status == 403
    handler_module._accept_stub.result = SupplierEntry("QZTEST", "시험")
    status, body = _probe(handler_module)
    assert status == 200 and body["supplierCode"] == "QZTEST"
    assert len(handler_module._get_supplier_stub.calls) == 1
    assert len(handler_module._accept_stub.calls) == 2


def test_unverified_email_never_accepts_and_403_carries_email(handler_module, monkeypatch):
    _wire(handler_module, monkeypatch, uid="u9", supplier_map={}, email=X_MAIL, verified=False)
    status, body = _probe(handler_module)
    assert status == 403
    assert body == {"error": {"code": "not_invited", "message": models.SUPPLIER_NOT_INVITED_MESSAGE,
                              "email": X_MAIL}}
    assert handler_module._accept_stub.calls == []


def test_no_email_claim_403_email_null(handler_module, monkeypatch):
    _wire(handler_module, monkeypatch, uid="u9", supplier_map={}, email=None, verified=True)
    status, body = _probe(handler_module)
    assert status == 403 and body["error"]["email"] is None
    assert handler_module._accept_stub.calls == []


def test_get_supplier_failure_is_500_not_403(handler_module, monkeypatch):
    _wire(handler_module, monkeypatch, uid="u9", supplier_map={},
          supplier_doc=RuntimeError("firestore down"))
    status, body = _probe(handler_module)
    assert status == 500 and body["error"]["code"] == "server_error"


def test_accept_code_conflict_is_500(handler_module, monkeypatch):
    from sunity_shared.supplier_invites import SupplierCodeConflict

    _wire(handler_module, monkeypatch, uid="u9", supplier_map={}, email=X_MAIL, verified=True,
          accept_result=SupplierCodeConflict("MXKR"))
    status, body = _probe(handler_module)
    assert status == 500 and body["error"]["code"] == "server_error"


def test_upload_uses_accepted_entry_code(handler_module, monkeypatch):
    from sunity_shared.supplier_invites import SupplierEntry

    events, s3, create = _wire(handler_module, monkeypatch, uid="u9", supplier_map={},
                               email=X_MAIL, verified=True,
                               accept_result=SupplierEntry("QZTEST", "시험"))
    resp = handler_module.lambda_handler(_bearer_event(OK_BODY), None)
    assert resp["statusCode"] == 200
    assert create.calls[0]["supplier_code"] == "QZTEST"


def test_not_invited_log_masks_email(handler_module, monkeypatch, caplog):
    _wire(handler_module, monkeypatch, uid="u9", supplier_map={}, email=X_MAIL, verified=True)
    with caplog.at_level(logging.INFO):
        _probe(handler_module)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "x***@y.com" in text
    assert X_MAIL not in text


def test_deactivate_reactivate_end_to_end_on_fake_firestore(handler_module, monkeypatch, fake_firestore):
    """BLOCKER 1 — 진짜 firestore_admin 함수로: 수락 → 회수 → 403(초대 revoked) → 되살리기 → 200."""
    import time as _time

    fa = handler_module.firestore_admin
    now = [int(_time.time() * 1000)]  # 핸들러가 수락 시각으로 실제 시계를 쓴다
    monkeypatch.setattr(fa, "_now_ms", lambda: now[0])
    monkeypatch.setattr(handler_module, "_load_supplier_map", lambda: {})
    monkeypatch.setattr(
        handler_module, "verify_request_claims", lambda evt: _claims("u9", X_MAIL, True)
    )
    fa.create_supplier_invite(X_MAIL, "QZTEST", "시험", days=14, now_ms=now[0] - 1000)

    status, body = _probe(handler_module)
    assert status == 200 and body["supplierCode"] == "QZTEST"

    handler_module._roster_cache.clear()
    fa.set_supplier_active("u9", False)
    status, body = _probe(handler_module)
    assert status == 403 and body["error"]["code"] == "not_invited"
    assert fake_firestore.store[models.supplier_invite_path(X_MAIL)]["status"] == "revoked"

    handler_module._roster_cache.clear()
    fa.set_supplier_active("u9", True)
    status, body = _probe(handler_module)
    assert status == 200 and body["supplierCode"] == "QZTEST"
    assert fake_firestore.read_after_write_seen is False
