"""29-06 Task 2 — playback-url referenceMotionId 재서명 확장 unit 테스트 (mock).

박제 정신:
  · 29-CONTEXT D-09 — D1(Mode1 비교영상 안 뜸) fix: 진단이 presigned 7일 TTL
    만료를 확정 → reference videoS3Key 재서명 경로 신설.
  · 29-PLAN-REVIEW HIGH-2 — 경계 가드 4종(존재·isActive·videoS3Key·prefix)
    전부 통과해야 서명. 실패는 전부 동일 404 (숨김 doc 존재 leak 0).
  · T-29-06-01 — 클라이언트 임의 S3 키 서명 불가 (body 의 s3Key 류 무시).
  · 기존 analysisId 경로 요청/응답 byte-호환 무회귀 (mode3 prev 재발급).
  · 외부 호출 0 — verify_request / get_reference_motion / _s3 전부 monkeypatch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_HANDLER_DIR = Path(__file__).resolve().parents[1] / "functions" / "playback-url"


@pytest.fixture
def handler_module(monkeypatch):
    """app.py 를 모듈로 import — sys.path 박제 후 캐시 reset (env 재평가)."""
    sys.path.insert(0, str(_HANDLER_DIR))
    monkeypatch.setenv("VIDEO_BUCKET", "test-bucket")
    if "app" in sys.modules:
        del sys.modules["app"]
    import app  # noqa: PLC0415 — 동적 import 의도.

    yield app
    if "app" in sys.modules:
        del sys.modules["app"]
    sys.path.remove(str(_HANDLER_DIR))


class _FakeS3:
    """generate_presigned_url 캡처 — 서명 대상 Key 를 검증에 사용."""

    def __init__(self):
        self.calls: list[dict] = []

    def generate_presigned_url(self, operation, Params, ExpiresIn):  # noqa: N803
        self.calls.append({"op": operation, "params": Params, "expires": ExpiresIn})
        return f"https://signed.example/{Params['Key']}"


@pytest.fixture
def patched(handler_module, monkeypatch):
    """공통 mock: 인증 uid 고정 + S3 fake. reference doc 은 테스트별 주입."""
    fake_s3 = _FakeS3()
    monkeypatch.setattr(handler_module, "_s3", fake_s3)
    monkeypatch.setattr(handler_module, "verify_request", lambda _event: "uid-001")
    return handler_module, fake_s3


def _event(body: dict) -> dict:
    return {"headers": {"Authorization": "Bearer t"}, "body": json.dumps(body)}


def _set_ref_doc(monkeypatch, handler_module, doc):
    monkeypatch.setattr(
        handler_module.firestore_admin,
        "get_reference_motion",
        lambda motion_id: doc,
    )


_ACTIVE_DOC = {
    "motionId": "ref-power-spin",
    "isActive": True,
    "videoS3Key": "reference/ref-power-spin.mp4",
}


def test_reference_active_doc_signs_200(patched, monkeypatch):
    app, fake_s3 = patched
    _set_ref_doc(monkeypatch, app, dict(_ACTIVE_DOC))
    resp = app.lambda_handler(_event({"referenceMotionId": "ref-power-spin"}), None)
    assert resp["statusCode"] == 200
    payload = json.loads(resp["body"])
    assert payload["playbackUrl"].endswith("reference/ref-power-spin.mp4")
    assert payload["expiresInSec"] == 7 * 24 * 60 * 60  # TTL 7일 불변 (T-29-06-02)
    assert fake_s3.calls[0]["params"]["Key"] == "reference/ref-power-spin.mp4"


def test_reference_doc_absent_404(patched, monkeypatch):
    app, fake_s3 = patched
    _set_ref_doc(monkeypatch, app, None)
    resp = app.lambda_handler(_event({"referenceMotionId": "ref-ghost"}), None)
    assert resp["statusCode"] == 404
    assert fake_s3.calls == []  # 서명 미발생


def test_reference_inactive_doc_404_indistinguishable(patched, monkeypatch):
    """isActive === False → 404. 부재 케이스와 응답 구분 불가 (leak 0)."""
    app, fake_s3 = patched
    inactive = dict(_ACTIVE_DOC, isActive=False)
    _set_ref_doc(monkeypatch, app, inactive)
    resp_inactive = app.lambda_handler(
        _event({"referenceMotionId": "ref-power-spin"}), None
    )
    _set_ref_doc(monkeypatch, app, None)
    resp_absent = app.lambda_handler(_event({"referenceMotionId": "ref-ghost"}), None)
    assert resp_inactive["statusCode"] == 404
    # 응답 body 동일 (statusCode + error code + message) — 존재 여부 leak 0.
    assert json.loads(resp_inactive["body"]) == json.loads(resp_absent["body"])
    assert fake_s3.calls == []


def test_reference_non_prefix_key_404(patched, monkeypatch):
    """videoS3Key 가 reference/ prefix 아님 (예: uploads/...) → 서명 거부 404."""
    app, fake_s3 = patched
    bad = dict(_ACTIVE_DOC, videoS3Key="uploads/uid-x/evil.mp4")
    _set_ref_doc(monkeypatch, app, bad)
    resp = app.lambda_handler(_event({"referenceMotionId": "ref-power-spin"}), None)
    assert resp["statusCode"] == 404
    assert fake_s3.calls == []


def test_reference_missing_video_key_404(patched, monkeypatch):
    app, fake_s3 = patched
    no_key = {k: v for k, v in _ACTIVE_DOC.items() if k != "videoS3Key"}
    _set_ref_doc(monkeypatch, app, no_key)
    resp = app.lambda_handler(_event({"referenceMotionId": "ref-power-spin"}), None)
    assert resp["statusCode"] == 404
    assert fake_s3.calls == []


def test_both_ids_provided_400(patched):
    app, fake_s3 = patched
    resp = app.lambda_handler(
        _event({"analysisId": "a" * 32, "referenceMotionId": "ref-power-spin"}), None
    )
    assert resp["statusCode"] == 400
    assert fake_s3.calls == []


def test_arbitrary_s3_key_param_ignored(patched, monkeypatch):
    """body 에 s3Key 류 키를 넣어도 서명은 doc videoS3Key 만 (T-29-06-01)."""
    app, fake_s3 = patched
    _set_ref_doc(monkeypatch, app, dict(_ACTIVE_DOC))
    resp = app.lambda_handler(
        _event(
            {
                "referenceMotionId": "ref-power-spin",
                "s3Key": "uploads/other-uid/steal.mp4",
                "videoS3Key": "uploads/other-uid/steal.mp4",
                "key": "../../etc/passwd",
            }
        ),
        None,
    )
    assert resp["statusCode"] == 200
    assert len(fake_s3.calls) == 1
    assert fake_s3.calls[0]["params"]["Key"] == "reference/ref-power-spin.mp4"


def test_reference_id_format_whitelist_400(patched, monkeypatch):
    """path injection 형식 거부 (영숫자·하이픈만)."""
    app, fake_s3 = patched
    _set_ref_doc(monkeypatch, app, dict(_ACTIVE_DOC))
    for bad_id in ("../secret", "ref/evil", "a b", "x" * 65):
        resp = app.lambda_handler(_event({"referenceMotionId": bad_id}), None)
        assert resp["statusCode"] == 400, bad_id
    assert fake_s3.calls == []


def test_analysis_id_path_unchanged(patched):
    """기존 analysisId 경로 무회귀 — 요청/응답 byte-호환 (mode3 prev 재발급)."""
    app, fake_s3 = patched
    analysis_id = "b" * 32
    resp = app.lambda_handler(_event({"analysisId": analysis_id, "ext": "mp4"}), None)
    assert resp["statusCode"] == 200
    payload = json.loads(resp["body"])
    assert set(payload.keys()) == {"playbackUrl", "expiresInSec"}
    assert payload["expiresInSec"] == 7 * 24 * 60 * 60
    # uid-scoped build_upload_key 경유 (임의 키 아님)
    assert fake_s3.calls[0]["params"]["Key"] == f"uploads/uid-001/{analysis_id}.mp4"


def test_analysis_id_bad_ext_400(patched):
    app, _ = patched
    resp = app.lambda_handler(
        _event({"analysisId": "c" * 32, "ext": "avi"}), None
    )
    assert resp["statusCode"] == 400


def test_neither_id_400(patched):
    app, _ = patched
    resp = app.lambda_handler(_event({}), None)
    assert resp["statusCode"] == 400
