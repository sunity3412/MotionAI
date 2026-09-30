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



# ── quick-260930-w9l — 기준 동작 썸네일 재서명 (asset 'thumbnail') ──────────────────────
# doc 에 서명 URL 을 박지 않는다(7일 만료 함정 — motionThumbs.ts 주석). 공개 doc 의 thumbnailS3Key 를
# 서버가 구성한 키와 exact 비교하고 1시간 서명. 가드 위반은 전부 같은 404.

_THUMB_REF = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
_THUMB_DOC = {
    "motionId": _THUMB_REF,
    "isActive": True,
    "supplierUid": "sup1",
    "videoS3Key": f"reference/sup1/{_THUMB_REF}/v1.mp4",
    "thumbnailS3Key": f"reference/sup1/{_THUMB_REF}/thumb.jpg",
}


def _thumb_event(ref_id=_THUMB_REF, asset="thumbnail"):
    return _event({"referenceMotionId": ref_id, "asset": asset})


def test_thumbnail_active_doc_signs_1h_jpeg(patched, monkeypatch):
    app, fake_s3 = patched
    _set_ref_doc(monkeypatch, app, dict(_THUMB_DOC))
    resp = app.lambda_handler(_thumb_event(), None)
    assert resp["statusCode"] == 200
    payload = json.loads(resp["body"])
    assert set(payload) == {"playbackUrl", "expiresInSec"}
    assert payload["expiresInSec"] == 3600
    call = fake_s3.calls[0]
    assert call["op"] == "get_object"
    assert call["params"]["Key"] == f"reference/sup1/{_THUMB_REF}/thumb.jpg"
    assert call["params"]["ResponseContentType"] == "image/jpeg"
    assert call["expires"] == 3600


@pytest.mark.parametrize(
    "patch",
    [
        {"thumbnailS3Key": None},  # 키 없음(레거시 11개 · 썸네일 실패 등록)
        {"thumbnailS3Key": f"reference/other/{_THUMB_REF}/thumb.jpg"},  # 다른 uid 키
        {"thumbnailS3Key": f"reference/sup1/{_THUMB_REF}/v1.mp4"},  # 영상 키 위장
        {"thumbnailS3Key": "uploads/sup1/x.jpg"},  # prefix 밖
        {"isActive": False},  # 숨김 doc
        {"supplierUid": None},  # canonical 구성 불가
    ],
)
def test_thumbnail_guard_violations_are_same_404(patched, monkeypatch, patch):
    app, fake_s3 = patched
    doc = dict(_THUMB_DOC, **patch)
    doc = {k: v for k, v in doc.items() if v is not None}
    _set_ref_doc(monkeypatch, app, doc)
    resp = app.lambda_handler(_thumb_event(), None)
    _set_ref_doc(monkeypatch, app, None)
    absent = app.lambda_handler(_thumb_event(), None)
    assert resp["statusCode"] == 404
    assert json.loads(resp["body"]) == json.loads(absent["body"])
    assert fake_s3.calls == []


def test_thumbnail_legacy_ref_doc_404(patched, monkeypatch):
    app, fake_s3 = patched
    _set_ref_doc(monkeypatch, app, dict(_ACTIVE_DOC))
    resp = app.lambda_handler(_thumb_event("ref-power-spin"), None)
    assert resp["statusCode"] == 404
    assert fake_s3.calls == []


@pytest.mark.parametrize("asset", ["coachAudio", "video", "", 1])
def test_reference_with_other_asset_is_400(patched, monkeypatch, asset):
    app, fake_s3 = patched
    _set_ref_doc(monkeypatch, app, dict(_THUMB_DOC))
    resp = app.lambda_handler(_thumb_event(asset=asset), None)
    assert resp["statusCode"] == 400
    assert fake_s3.calls == []


def test_reference_without_asset_still_signs_video(patched, monkeypatch):
    """asset 없는 기존 영상 재서명 무회귀 — 7일, videoS3Key."""
    app, fake_s3 = patched
    _set_ref_doc(monkeypatch, app, dict(_THUMB_DOC))
    resp = app.lambda_handler(_event({"referenceMotionId": _THUMB_REF}), None)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["expiresInSec"] == 7 * 24 * 60 * 60
    assert fake_s3.calls[0]["params"]["Key"] == f"reference/sup1/{_THUMB_REF}/v1.mp4"
    assert "ResponseContentType" not in fake_s3.calls[0]["params"]
