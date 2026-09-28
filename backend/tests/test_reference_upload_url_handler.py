"""Plan 38-06 Task 2 — reference-upload-url Lambda handler 테스트 (AWS/Firestore/SSM 0).

잠그는 계약(38-06-PLAN behavior · contract.md §2 POST /reference/upload-url · 리뷰 R4·R5):
  · 인증 실패 401 · 화이트리스트 밖 403(SSM 파라미터 부재/env 미설정 = 거부, 조용한 통과 금지)
  · `{"probe": true}` 는 판정 + supplierCode 만 돌려주고 presign·doc 부작용 0(D-12)
  · 정상 body: presign 이 **먼저**, 그 **뒤** 공개+비공개 doc batch create — create 가 실패하면
    URL 이 응답에 실리지 않는다(고아 객체 없음, R4). uploadExpiresAt = 서명 만료와 같은 상수.
  · 본문의 uid/refId 는 절대 읽지 않는다(V4) — 키·doc 은 토큰 uid + 서버 uuid4 hex 만.
  · 서명은 upload 키(`reference/{uid}/{refId}/upload.{ext}`)에만(R5).
외부 호출 0 — verify_request / _load_supplier_map / _s3 / create_reference_registration /
boto3.client("ssm") 전부 monkeypatch(test_reference_auto_register_handler.py 어법).
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
    if "app" in sys.modules:
        del sys.modules["app"]
    import app  # noqa: PLC0415 — 동적 import 의도.

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


def _wire(app, monkeypatch, *, uid="u1", supplier_map=None, belle_uid=None,
          presign_fail=False, create_exc=None):
    """인증·화이트리스트·S3·Firestore 를 한 번에 붙인다. 반환 (events, s3, create)."""
    if supplier_map is None:
        supplier_map = {"u1": "EUNJI", "u2": None}
    if belle_uid is not None:
        monkeypatch.setattr(app, "_BELLE_UID", belle_uid)
    monkeypatch.setattr(app, "verify_request", lambda evt: uid)
    monkeypatch.setattr(app, "_load_supplier_map", lambda: dict(supplier_map))
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

    monkeypatch.setattr(handler_module, "verify_request", _raise)
    resp = handler_module.lambda_handler({"headers": {}, "body": "{}"}, None)
    assert resp["statusCode"] == 401
    assert json.loads(resp["body"])["error"]["code"] == "unauthorized"


def test_empty_whitelist_and_no_belle_uid_returns_403(handler_module, monkeypatch):
    events, s3, create = _wire(handler_module, monkeypatch, uid="u1", supplier_map={}, belle_uid="")
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 403
    assert json.loads(resp["body"])["error"]["code"] == "forbidden"
    assert events == []


def test_uid_not_in_whitelist_returns_403(handler_module, monkeypatch, caplog):
    events, s3, create = _wire(handler_module, monkeypatch, uid="u9")
    with caplog.at_level(logging.WARNING):
        resp = handler_module.lambda_handler(_bearer_event(OK_BODY), None)
    assert resp["statusCode"] == 403
    assert json.loads(resp["body"])["error"]["code"] == "forbidden"
    assert events == []
    assert any("forbidden" in r.getMessage() and "u9" in r.getMessage() for r in caplog.records)


def test_belle_uid_passes_without_map_entry(handler_module, monkeypatch):
    _wire(handler_module, monkeypatch, uid="belle-uid-001", supplier_map={})
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body == {"probe": True, "uid": "belle-uid-001", "supplierCode": None}


def test_is_supplier_pure_rules(handler_module, monkeypatch):
    monkeypatch.setattr(handler_module, "_BELLE_UID", "")
    assert handler_module._is_supplier("u1", {}) is False
    assert handler_module._is_supplier("u1", {"u1": None}) is True
    assert handler_module._is_supplier("", {}) is False  # env 미설정 = 빈 uid 도 통과 재료 아님
    monkeypatch.setattr(handler_module, "_BELLE_UID", "belle-uid-001")
    assert handler_module._is_supplier("belle-uid-001", {}) is True
    assert handler_module._is_supplier("u9", {"u1": "EUNJI"}) is False


# ─────────────────── probe (D-12) ───────────────────


def test_probe_returns_whitelist_verdict_and_code_without_side_effects(handler_module, monkeypatch):
    events, s3, create = _wire(handler_module, monkeypatch, uid="u1")
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"probe": True, "uid": "u1", "supplierCode": "EUNJI"}
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
    monkeypatch.setattr(handler_module, "verify_request", lambda evt: "u1")
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 403
    monkeypatch.setattr(handler_module, "verify_request", lambda evt: "belle-uid-001")
    resp = handler_module.lambda_handler(_bearer_event({"probe": True}), None)
    assert resp["statusCode"] == 200


# ─────────────────── 모듈 상수 · requirements ───────────────────


def test_expires_constant_is_shared_with_models(handler_module):
    assert handler_module._EXPIRES == models.REFERENCE_UPLOAD_EXPIRES_SEC
    assert handler_module._SUPPLIER_CACHE_TTL_S == 60


def test_requirements_txt_copies_upload_url(handler_module):
    ours = (_HANDLER_DIR / "requirements.txt").read_text(encoding="utf-8")
    theirs = (_UPLOAD_URL_DIR / "requirements.txt").read_text(encoding="utf-8")
    assert ours == theirs
