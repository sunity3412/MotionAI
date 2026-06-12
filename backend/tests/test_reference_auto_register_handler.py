"""Plan 17-05 Task 2 — reference-auto-register Lambda handler 통합 테스트.

박제 정신:
  · Plan 17-05 박제 — POST /reference/auto-register endpoint 인증/S3/Gemini/Firestore
    mock 통합. Firebase ID token + BELLE_UID 화이트리스트 이중 인증.
  · S3 download → /tmp 박제 (AI-SPEC §3 Pitfall #2 — presigned URL 직접 X).
  · firestore_admin.set_reference_motion_with_gemini(idempotent=True) — 기존 doc 의
    isActive/inactiveReason 보존 (belle 검수 결과 유지).
  · 외부 호출 0 — boto3 / verify_request / extract_reference_metadata /
    set_reference_motion_with_gemini 전부 monkeypatch.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest


# Lambda function 모듈 path 박제 — backend/functions/reference-auto-register/app.py.
_HANDLER_DIR = (
    Path(__file__).resolve().parents[1]
    / "functions"
    / "reference-auto-register"
)


@pytest.fixture
def handler_module(monkeypatch):
    """app.py 를 모듈로 import — sys.path 박제 후 reload 로 env 재평가."""
    sys.path.insert(0, str(_HANDLER_DIR))
    monkeypatch.setenv("VIDEO_BUCKET", "test-bucket")
    monkeypatch.setenv("BELLE_UID", "belle-uid-001")
    # 모듈 cache reset — 다른 테스트가 env 다르게 박은 경우 차단.
    if "app" in sys.modules:
        del sys.modules["app"]
    import app  # noqa: PLC0415 — 동적 import 의도.
    yield app
    if "app" in sys.modules:
        del sys.modules["app"]
    sys.path.remove(str(_HANDLER_DIR))


# ─────────────────── 더미 helpers ───────────────────


def _bearer_event(body: dict, token: str = "valid-token") -> dict:
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "body": json.dumps(body),
    }


def _ok_gemini_result(routing_branch: str = "branch_1_ipsf") -> dict:
    return {
        "motion_id": "ref-butterfly",
        "motion_name_ipsf": "Butterfly",
        "motion_name_ko": "버터플라이",
        "clip_range": {"clip_start_seconds": 1.5, "clip_end_seconds": 8.0},
        "checkpoint_joints": [
            {"joint_key": "left_knee", "expectation": "EXTEND"},
            {"joint_key": "right_knee", "expectation": "EXTEND"},
        ],
        "routing_branch": routing_branch,
        "review_required": routing_branch == "branch_3_auto",
        "inactive_reason": (
            "ipsf_whitelist_miss" if routing_branch == "branch_3_auto" else None
        ),
        "confidence": 0.85,
        "model": "gemini-3.1-pro-preview",
        "registered_at": 1700000000000,
        "latency_ms": 4200,
        "raw_response": {
            "motion_name_ipsf": "Butterfly",
            "motion_name_ko": "버터플라이",
            "clip_start_seconds": 1.5,
            "clip_end_seconds": 8.0,
            "checkpoint_joints": [
                {"joint_key": "left_knee", "expectation": "EXTEND"},
                {"joint_key": "right_knee", "expectation": "EXTEND"},
            ],
            "confidence": 0.85,
        },
        "champion_personal_alias": None,
        "ipsf_code": "B201",
    }


class _FakeS3:
    """boto3 s3 client mock — get_object 박제."""

    def __init__(self, raise_no_such_key: bool = False) -> None:
        self.raise_no_such_key = raise_no_such_key
        self.calls: list[dict] = []

    def get_object(self, **kwargs: Any) -> dict:
        self.calls.append(kwargs)
        if self.raise_no_such_key:
            from botocore.exceptions import ClientError

            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "missing"}},
                "GetObject",
            )

        class _Body:
            def read(self) -> bytes:
                return b"fake-mp4-bytes"

        return {"Body": _Body()}


# ─────────────────── 정상 path ───────────────────


class TestHappyPath:
    """정상 호출 — auth/S3/Gemini/Firestore 전부 mock → 200 + body 검증."""

    def test_happy_path_200(self, handler_module, monkeypatch) -> None:
        # verify_request → belle uid.
        monkeypatch.setattr(
            handler_module, "verify_request", lambda evt: "belle-uid-001"
        )
        # S3 mock.
        fake_s3 = _FakeS3()
        monkeypatch.setattr(handler_module, "_s3", fake_s3)
        # extract_reference_metadata mock.
        captured: dict[str, Any] = {}

        def fake_extract(video_path, studio_alias=None, override_motion_id=None):
            captured["video_path"] = video_path
            captured["studio_alias"] = studio_alias
            captured["override_motion_id"] = override_motion_id
            return _ok_gemini_result(routing_branch="branch_1_ipsf")

        monkeypatch.setattr(
            handler_module, "extract_reference_metadata", fake_extract
        )
        # set_reference_motion_with_gemini mock.
        firestore_calls: list[dict] = []

        def fake_set(motion_id, gemini_a, idempotent=True):
            firestore_calls.append(
                dict(motion_id=motion_id, gemini_a=gemini_a, idempotent=idempotent)
            )

        monkeypatch.setattr(
            handler_module,
            "set_reference_motion_with_gemini",
            fake_set,
        )

        event = _bearer_event(
            {
                "s3Key": "reference/butterfly.mp4",
                "studioAlias": None,
                "overrideMotionId": None,
            }
        )
        resp = handler_module.lambda_handler(event, None)

        assert resp["statusCode"] == 200, resp
        body = json.loads(resp["body"])
        assert body["motionId"] == "ref-butterfly"
        assert body["routingBranch"] == "branch_1_ipsf"
        assert body["reviewRequired"] is False
        assert body["geminiA"]["motion_name_ipsf"] == "Butterfly"
        assert body["geminiA"]["model"] == "gemini-3.1-pro-preview"
        # S3 호출 박힘.
        assert fake_s3.calls == [
            {"Bucket": "test-bucket", "Key": "reference/butterfly.mp4"}
        ]
        # Gemini extract 호출 박힘 — /tmp path + alias/override 전달.
        assert captured["video_path"].startswith("/tmp/")
        assert captured["studio_alias"] is None
        assert captured["override_motion_id"] is None
        # Firestore 박힘.
        assert len(firestore_calls) == 1
        assert firestore_calls[0]["motion_id"] == "ref-butterfly"
        assert firestore_calls[0]["idempotent"] is True

    def test_studio_alias_passed_through(self, handler_module, monkeypatch) -> None:
        monkeypatch.setattr(
            handler_module, "verify_request", lambda evt: "belle-uid-001"
        )
        monkeypatch.setattr(handler_module, "_s3", _FakeS3())

        captured: dict[str, Any] = {}

        def fake_extract(video_path, studio_alias=None, override_motion_id=None):
            captured["studio_alias"] = studio_alias
            captured["override_motion_id"] = override_motion_id
            return _ok_gemini_result(routing_branch="branch_2_studio")

        monkeypatch.setattr(
            handler_module, "extract_reference_metadata", fake_extract
        )
        monkeypatch.setattr(
            handler_module,
            "set_reference_motion_with_gemini",
            lambda *a, **kw: None,
        )

        event = _bearer_event(
            {
                "s3Key": "reference/foxtop.mp4",
                "studioAlias": "폭스탑",
                "overrideMotionId": "ref-foxtop",
            }
        )
        resp = handler_module.lambda_handler(event, None)
        assert resp["statusCode"] == 200
        assert captured["studio_alias"] == "폭스탑"
        assert captured["override_motion_id"] == "ref-foxtop"


# ─────────────────── 인증 ───────────────────


class TestAuth:
    """Authorization 헤더 검증 + BELLE_UID 화이트리스트."""

    def test_token_missing_returns_401(self, handler_module, monkeypatch) -> None:
        # verify_request 가 AuthError 발생.
        from sunity_shared.auth import AuthError

        def fake_verify(evt):
            raise AuthError("인증이 필요합니다.")

        monkeypatch.setattr(handler_module, "verify_request", fake_verify)
        event = {"headers": {}, "body": "{}"}
        resp = handler_module.lambda_handler(event, None)
        assert resp["statusCode"] == 401
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "unauthorized"

    def test_non_belle_uid_returns_403(self, handler_module, monkeypatch) -> None:
        monkeypatch.setattr(
            handler_module, "verify_request", lambda evt: "some-student-uid"
        )
        # _s3 / extract mock 박혀있어도 도달 전에 reject.
        monkeypatch.setattr(handler_module, "_s3", _FakeS3())

        event = _bearer_event({"s3Key": "reference/x.mp4"})
        resp = handler_module.lambda_handler(event, None)
        assert resp["statusCode"] == 403
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "forbidden"


# ─────────────────── S3 errors ───────────────────


class TestS3Errors:
    """S3 download 실패 — NoSuchKey 404."""

    def test_no_such_key_returns_404(self, handler_module, monkeypatch) -> None:
        monkeypatch.setattr(
            handler_module, "verify_request", lambda evt: "belle-uid-001"
        )
        monkeypatch.setattr(
            handler_module, "_s3", _FakeS3(raise_no_such_key=True)
        )

        event = _bearer_event({"s3Key": "reference/missing.mp4"})
        resp = handler_module.lambda_handler(event, None)
        assert resp["statusCode"] == 404
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "s3_object_not_found"

    def test_missing_s3_key_returns_400(self, handler_module, monkeypatch) -> None:
        monkeypatch.setattr(
            handler_module, "verify_request", lambda evt: "belle-uid-001"
        )

        event = _bearer_event({"studioAlias": "폭스탑"})
        resp = handler_module.lambda_handler(event, None)
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "bad_request"


# ─────────────────── Gemini 실패 ───────────────────


class TestGeminiFailure:
    """extract_reference_metadata None → 500 server_error."""

    def test_gemini_none_returns_500(self, handler_module, monkeypatch) -> None:
        monkeypatch.setattr(
            handler_module, "verify_request", lambda evt: "belle-uid-001"
        )
        monkeypatch.setattr(handler_module, "_s3", _FakeS3())
        monkeypatch.setattr(
            handler_module,
            "extract_reference_metadata",
            lambda *a, **k: None,
        )

        event = _bearer_event({"s3Key": "reference/butterfly.mp4"})
        resp = handler_module.lambda_handler(event, None)
        assert resp["statusCode"] == 500
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "server_error"


# ─────────────────── Idempotent path ───────────────────


class TestIdempotent:
    """같은 motion_id 2회 호출 — set_reference_motion_with_gemini idempotent=True 유지."""

    def test_two_calls_same_motion_id_pass_idempotent_true(
        self, handler_module, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            handler_module, "verify_request", lambda evt: "belle-uid-001"
        )
        monkeypatch.setattr(handler_module, "_s3", _FakeS3())
        monkeypatch.setattr(
            handler_module,
            "extract_reference_metadata",
            lambda *a, **k: _ok_gemini_result(),
        )
        calls: list[dict] = []

        def fake_set(motion_id, gemini_a, idempotent=True):
            calls.append(
                dict(motion_id=motion_id, idempotent=idempotent)
            )

        monkeypatch.setattr(
            handler_module,
            "set_reference_motion_with_gemini",
            fake_set,
        )

        event = _bearer_event({"s3Key": "reference/butterfly.mp4"})
        # 두 번 호출.
        handler_module.lambda_handler(event, None)
        handler_module.lambda_handler(event, None)

        # 둘 다 motion_id=ref-butterfly + idempotent=True.
        assert len(calls) == 2
        assert calls[0]["motion_id"] == "ref-butterfly"
        assert calls[0]["idempotent"] is True
        assert calls[1]["motion_id"] == "ref-butterfly"
        assert calls[1]["idempotent"] is True


# ─────────────────── firestore_admin helper 단위 테스트 ───────────────────


class TestSetReferenceMotionWithGemini:
    """set_reference_motion_with_gemini idempotent 박제 — 기존 doc 의 isActive/
    inactiveReason 보존 + geminiA 갱신.
    """

    def test_creates_new_doc_when_missing(self, monkeypatch) -> None:
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _FakeSnap:
            exists = False

        class _FakeDoc:
            def get(self):  # noqa: D401
                return _FakeSnap()

            def set(self, payload, merge=True):  # noqa: D401
                captured["payload"] = payload
                captured["merge"] = merge

        monkeypatch.setattr(firestore_admin, "_doc", lambda _p: _FakeDoc())

        gemini_a = _ok_gemini_result(routing_branch="branch_3_auto")
        firestore_admin.set_reference_motion_with_gemini(
            "ref-butterfly", gemini_a=gemini_a, idempotent=True
        )

        payload = captured["payload"]
        # geminiA 박힘.
        assert "geminiA" in payload
        # 분기 3 — isActive=false, inactiveReason 박힘.
        assert payload["isActive"] is False
        assert payload["inactiveReason"] == "ipsf_whitelist_miss"

    def test_creates_new_doc_branch_1_active_true(self, monkeypatch) -> None:
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _FakeSnap:
            exists = False

        class _FakeDoc:
            def get(self):  # noqa: D401
                return _FakeSnap()

            def set(self, payload, merge=True):  # noqa: D401
                captured["payload"] = payload

        monkeypatch.setattr(firestore_admin, "_doc", lambda _p: _FakeDoc())

        gemini_a = _ok_gemini_result(routing_branch="branch_1_ipsf")
        firestore_admin.set_reference_motion_with_gemini(
            "ref-butterfly", gemini_a=gemini_a, idempotent=True
        )

        payload = captured["payload"]
        # 분기 1 — 새 doc 박힘, isActive=True.
        assert payload["isActive"] is True
        assert payload["inactiveReason"] is None

    def test_existing_doc_preserves_isactive_when_branch_1(
        self, monkeypatch
    ) -> None:
        """기존 doc 박혀있으면 isActive/inactiveReason 보존 — geminiA 만 갱신
        (belle 검수 결과 유지). 분기 1 (이미 active) 케이스.
        """
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _FakeSnap:
            exists = True

            def to_dict(self):
                return {
                    "motionId": "ref-butterfly",
                    "isActive": True,  # belle 가 이미 검수 박은 상태.
                    "inactiveReason": None,
                    "name": "버터플라이",
                }

        class _FakeDoc:
            def get(self):  # noqa: D401
                return _FakeSnap()

            def set(self, payload, merge=True):  # noqa: D401
                captured["payload"] = payload
                captured["merge"] = merge

        monkeypatch.setattr(firestore_admin, "_doc", lambda _p: _FakeDoc())

        gemini_a = _ok_gemini_result(routing_branch="branch_1_ipsf")
        firestore_admin.set_reference_motion_with_gemini(
            "ref-butterfly", gemini_a=gemini_a, idempotent=True
        )

        payload = captured["payload"]
        # geminiA 박힘.
        assert "geminiA" in payload
        # idempotent — 기존 isActive=True 박혀있어서 payload 에 isActive 박지 X
        # (또는 박았다면 기존 True 유지 강제).
        # belle 검수 결과 보존 박제 — 기존 isActive 보존.
        if "isActive" in payload:
            assert payload["isActive"] is True
        # merge=True 강제 (다른 필드 박지 X).
        assert captured.get("merge") is True

    def test_existing_g3_updates_inactivereason(self, monkeypatch) -> None:
        """기존 doc isActive=False + G3 재호출 시 inactiveReason 갱신 박힘 (이미
        검수 안 된 doc — G3 trigger 변경된 경우).
        """
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _FakeSnap:
            exists = True

            def to_dict(self):
                return {
                    "motionId": "ref-unknown",
                    "isActive": False,
                    "inactiveReason": "ipsf_whitelist_miss",
                }

        class _FakeDoc:
            def get(self):  # noqa: D401
                return _FakeSnap()

            def set(self, payload, merge=True):  # noqa: D401
                captured["payload"] = payload

        monkeypatch.setattr(firestore_admin, "_doc", lambda _p: _FakeDoc())

        gemini_a = _ok_gemini_result(routing_branch="branch_3_auto")
        firestore_admin.set_reference_motion_with_gemini(
            "ref-unknown", gemini_a=gemini_a, idempotent=True
        )

        payload = captured["payload"]
        # G3 trigger — inactiveReason 박힘 (또는 보존).
        assert payload.get("inactiveReason") == "ipsf_whitelist_miss"
        # 기존 isActive=False 보존 (belle 가 review 미박제 상태).
        # idempotent 가 True 박혀있어서 payload 에 isActive=False 박힘 가능.
        if "isActive" in payload:
            assert payload["isActive"] is False
