"""quick-260824-q6p — playback-url asset 'faultZoom' 배치 재서명 unit 테스트 (mock).

박제 정신:
  · faultZoomComparisons[].imageUrl 은 분석 시점 7일 presigned — 7일 뒤 비교
    패널이 전부 회색이 되는 결함(belle 08-24 실기기)을 열람 시점 재발급으로 수리.
  · H-05 — 클라이언트는 key 를 절대 보내지 않는다. 서버가 canonical key 를
    구성(s3keys.build_fault_zoom_key — 저장 측과 단일 출처)하고 저장/파싱 key 와
    **전체 문자열 exact 비교** 후에만 서명 (M2-01).
  · 소급(legacy doc) — imageKey 부재 item 은 저장 imageUrl 을 **서버가** 파싱
    (parse_result_key_from_presigned_url — 후보 추출 전용, 출력 비신뢰). 백필 0.
  · T-q6p-01 — 타 uid 키는 canonical 불일치로 서명 0 (cross-uid 차단).
  · T-q6p-02 — 가드 위반 전부 동일 404 (leak 0).
  · 기존 asset 미지정 analysisId 경로 요청/응답 byte-호환 무회귀.
  · 외부 호출 0 — verify_request / get_analysis / _s3 전부 monkeypatch
    (test_playback_url_reference.py fixture 패턴 그대로).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from sunity_shared.s3keys import (
    build_fault_zoom_key,
    parse_result_key_from_presigned_url,
)

_HANDLER_DIR = Path(__file__).resolve().parents[1] / "functions" / "playback-url"

_UID = "uid-001"
_AID = "a" * 32


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
    """generate_presigned_url 캡처 — 서명 대상 Key/ExpiresIn/ContentType 검증용."""

    def __init__(self):
        self.calls: list[dict] = []

    def generate_presigned_url(self, operation, Params, ExpiresIn):  # noqa: N803
        self.calls.append({"op": operation, "params": Params, "expires": ExpiresIn})
        return f"https://signed.example/{Params['Key']}"


@pytest.fixture
def patched(handler_module, monkeypatch):
    """공통 mock: 인증 uid 고정 + S3 fake. analysis doc 은 테스트별 주입."""
    fake_s3 = _FakeS3()
    monkeypatch.setattr(handler_module, "_s3", fake_s3)
    monkeypatch.setattr(handler_module, "verify_request", lambda _event: _UID)
    return handler_module, fake_s3


def _event(body: dict) -> dict:
    return {"headers": {"Authorization": "Bearer t"}, "body": json.dumps(body)}


def _set_analysis_doc(monkeypatch, handler_module, doc):
    monkeypatch.setattr(
        handler_module.firestore_admin,
        "get_analysis",
        lambda uid, analysis_id: doc,
    )


def _canonical(tier: str | None, key_base: str, uid: str = _UID) -> str:
    return build_fault_zoom_key(uid, _AID, tier, key_base)


def _doc(comparisons: list, status: str | None = "done") -> dict:
    result: dict = {"faultZoomComparisons": comparisons}
    if status is not None:
        result["faultZoomStatus"] = status
    return {"result": result}


def _post_fault_zoom(app) -> dict:
    return app.lambda_handler(
        _event({"analysisId": _AID, "asset": "faultZoom"}), None
    )


# ── (a) done + imageKey exact → 200 ────────────────────────────────────────────


def test_done_doc_with_image_key_signs_200(patched, monkeypatch):
    app, fake_s3 = patched
    key = _canonical("confirmed", "split_angle")
    _set_analysis_doc(
        monkeypatch,
        app,
        _doc([{"joint": "left_knee", "tier": "confirmed",
               "criterion": "split_angle", "imageKey": key,
               "imageUrl": "https://stale.example/x"}]),
    )
    resp = _post_fault_zoom(app)
    assert resp["statusCode"] == 200
    payload = json.loads(resp["body"])
    assert payload["expiresInSec"] == 3600
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["joint"] == "left_knee"
    assert item["tier"] == "confirmed"
    assert item["criterion"] == "split_angle"
    assert item["playbackUrl"].endswith(key)
    # 서명 파라미터 — canonical key + 1시간 + image/png (표시 즉시 소비).
    assert fake_s3.calls[0]["params"]["Key"] == key
    assert fake_s3.calls[0]["expires"] == 3600
    assert fake_s3.calls[0]["params"]["ResponseContentType"] == "image/png"


# ── (b)(c) 소급 — imageKey 없는 legacy doc 은 imageUrl 파싱 ─────────────────────


def test_legacy_doc_virtual_hosted_url_parsed_and_signed(patched, monkeypatch):
    app, fake_s3 = patched
    key = _canonical("confirmed", "left_knee")
    url = (
        f"https://test-bucket.s3.ap-northeast-2.amazonaws.com/{key}"
        "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=604800"
    )
    _set_analysis_doc(
        monkeypatch, app, _doc([{"joint": "left_knee", "imageUrl": url}])
    )
    resp = _post_fault_zoom(app)
    assert resp["statusCode"] == 200
    assert fake_s3.calls[0]["params"]["Key"] == key


def test_legacy_doc_path_style_url_parsed_and_signed(patched, monkeypatch):
    app, fake_s3 = patched
    key = _canonical("confirmed", "left_knee")
    url = (
        f"https://s3.ap-northeast-2.amazonaws.com/test-bucket/{key}"
        "?X-Amz-Signature=abc"
    )
    _set_analysis_doc(
        monkeypatch, app, _doc([{"joint": "left_knee", "imageUrl": url}])
    )
    resp = _post_fault_zoom(app)
    assert resp["statusCode"] == 200
    assert fake_s3.calls[0]["params"]["Key"] == key


# ── (d) stale key — exact 불일치 item 제외, 전 item 불일치 = 404 ────────────────


def test_stale_image_key_item_excluded_partial_success(patched, monkeypatch):
    app, fake_s3 = patched
    good = _canonical("confirmed", "split_angle")
    _set_analysis_doc(
        monkeypatch,
        app,
        _doc([
            # stale — 이전 성공분 잔재 (다른 analysis 키).
            {"joint": "left_elbow", "tier": "confirmed",
             "imageKey": f"results/{_UID}/{'b' * 32}/zoom_left_elbow.png"},
            {"joint": "left_knee", "tier": "confirmed",
             "criterion": "split_angle", "imageKey": good},
        ]),
    )
    resp = _post_fault_zoom(app)
    assert resp["statusCode"] == 200
    payload = json.loads(resp["body"])
    assert [it["joint"] for it in payload["items"]] == ["left_knee"]
    assert len(fake_s3.calls) == 1  # stale item 은 서명 자체가 없다


def test_all_items_mismatch_404(patched, monkeypatch):
    app, fake_s3 = patched
    _set_analysis_doc(
        monkeypatch,
        app,
        _doc([{"joint": "left_knee", "tier": "confirmed",
               "imageKey": "results/uid-001/wrong/zoom_left_knee.png"}]),
    )
    resp = _post_fault_zoom(app)
    assert resp["statusCode"] == 404
    assert fake_s3.calls == []


# ── (e) status 게이트 — pending/failed/부재 = 404 ──────────────────────────────


@pytest.mark.parametrize("status", ["pending", "failed", None])
def test_status_not_done_404(patched, monkeypatch, status):
    app, fake_s3 = patched
    key = _canonical("confirmed", "left_knee")
    _set_analysis_doc(
        monkeypatch,
        app,
        _doc([{"joint": "left_knee", "imageKey": key}], status=status),
    )
    resp = _post_fault_zoom(app)
    assert resp["statusCode"] == 404
    assert fake_s3.calls == []  # stale key 여도 서명 미발생


def test_guard_failures_indistinguishable_404(patched, monkeypatch):
    """status 게이트 404 와 전 item 불일치 404 의 응답 body 동일 (leak 0)."""
    app, _ = patched
    _set_analysis_doc(
        monkeypatch, app, _doc([{"joint": "j", "imageKey": "k"}], status="failed")
    )
    resp_status = _post_fault_zoom(app)
    _set_analysis_doc(
        monkeypatch, app,
        _doc([{"joint": "left_knee", "imageKey": "results/x/y/zoom_z.png"}]),
    )
    resp_mismatch = _post_fault_zoom(app)
    assert resp_status["statusCode"] == resp_mismatch["statusCode"] == 404
    assert json.loads(resp_status["body"]) == json.loads(resp_mismatch["body"])


# ── (f) cross-uid — 타 사용자 키 재서명 차단 ───────────────────────────────────


def test_cross_uid_key_blocked_404(patched, monkeypatch):
    """토큰 uid-001 인데 item key 가 uid-002 경로 → canonical 불일치 → 404.

    imageKey 경로와 imageUrl 파싱(소급) 경로 양쪽 모두 차단돼야 한다.
    """
    app, fake_s3 = patched
    other_key = build_fault_zoom_key("uid-002", _AID, "confirmed", "left_knee")
    _set_analysis_doc(
        monkeypatch,
        app,
        _doc([
            {"joint": "left_knee", "tier": "confirmed", "imageKey": other_key},
            {"joint": "left_elbow", "tier": "confirmed",
             "imageUrl": (
                 "https://test-bucket.s3.ap-northeast-2.amazonaws.com/"
                 f"results/uid-002/{_AID}/zoom_left_elbow.png?X-Amz-Expires=1"
             )},
        ]),
    )
    resp = _post_fault_zoom(app)
    assert resp["statusCode"] == 404
    assert fake_s3.calls == []


# ── (g) tier/key_base 매핑 — advisory prefix · criterion 우선 · joint 폴백 ─────


def test_advisory_tier_signs_adv_prefix_key(patched, monkeypatch):
    app, fake_s3 = patched
    key = _canonical("advisory", "left_shoulder")
    assert "/zoom_adv_left_shoulder.png" in key
    _set_analysis_doc(
        monkeypatch,
        app,
        _doc([{"joint": "left_shoulder", "tier": "advisory", "imageKey": key}]),
    )
    resp = _post_fault_zoom(app)
    assert resp["statusCode"] == 200
    assert fake_s3.calls[0]["params"]["Key"] == key


def test_criterion_card_uses_criterion_and_legacy_uses_joint(patched, monkeypatch):
    app, fake_s3 = patched
    crit_key = _canonical("confirmed", "angle_vs_reference__left_knee")
    joint_key = _canonical("confirmed", "right_elbow")
    _set_analysis_doc(
        monkeypatch,
        app,
        _doc([
            {"joint": "left_knee", "tier": "confirmed",
             "criterion": "angle_vs_reference__left_knee", "imageKey": crit_key},
            # legacy 카드 — criterion 부재 → joint 키.
            {"joint": "right_elbow", "tier": "confirmed", "imageKey": joint_key},
        ]),
    )
    resp = _post_fault_zoom(app)
    assert resp["statusCode"] == 200
    assert [c["params"]["Key"] for c in fake_s3.calls] == [crit_key, joint_key]


# ── (h) 순수 함수 직접 ─────────────────────────────────────────────────────────


def test_build_fault_zoom_key_prefix_mapping():
    assert (
        build_fault_zoom_key("u", "a", "confirmed", "split_angle")
        == "results/u/a/zoom_split_angle.png"
    )
    assert (
        build_fault_zoom_key("u", "a", "advisory", "left_knee")
        == "results/u/a/zoom_adv_left_knee.png"
    )
    # tier None/legacy — confirmed 취급 (zoom_ prefix).
    assert (
        build_fault_zoom_key("u", "a", None, "left_knee")
        == "results/u/a/zoom_left_knee.png"
    )


def test_parse_result_key_virtual_hosted():
    url = (
        "https://bkt.s3.ap-northeast-2.amazonaws.com/results/u/a/zoom_x.png"
        "?X-Amz-Signature=s"
    )
    assert parse_result_key_from_presigned_url(url) == "results/u/a/zoom_x.png"


def test_parse_result_key_path_style():
    url = "https://s3.ap-northeast-2.amazonaws.com/bkt/results/u/a/zoom_x.png?q=1"
    assert parse_result_key_from_presigned_url(url) == "results/u/a/zoom_x.png"
    # s3- 변형 (구 리전 엔드포인트).
    url2 = "https://s3-ap-northeast-2.amazonaws.com/bkt/results/u/a/zoom_x.png"
    assert parse_result_key_from_presigned_url(url2) == "results/u/a/zoom_x.png"


def test_parse_result_key_url_encoded_path():
    url = "https://bkt.s3.amazonaws.com/results/u/a/zoom%5Fx.png"
    assert parse_result_key_from_presigned_url(url) == "results/u/a/zoom_x.png"


@pytest.mark.parametrize(
    "bad", [None, "", 123, "not a url", "https://s3.amazonaws.com/", "https://s3.amazonaws.com/bucket-only"]
)
def test_parse_result_key_malformed_returns_none(bad):
    assert parse_result_key_from_presigned_url(bad) is None


# ── (i) 무회귀 — asset 미지정 analysisId 경로 응답 형상 불변 ────────────────────


def test_analysis_id_path_without_asset_unchanged(patched):
    app, fake_s3 = patched
    resp = app.lambda_handler(_event({"analysisId": _AID, "ext": "mp4"}), None)
    assert resp["statusCode"] == 200
    payload = json.loads(resp["body"])
    assert set(payload.keys()) == {"playbackUrl", "expiresInSec"}
    assert payload["expiresInSec"] == 7 * 24 * 60 * 60
    assert fake_s3.calls[0]["params"]["Key"] == f"uploads/{_UID}/{_AID}.mp4"
