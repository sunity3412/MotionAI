"""visual_gen 어댑터 · 다운로드 경계 · safe_decode_image · judge 테스트 — 플랜 31-05.

실 외부 API 호출 0. 생성 콜 예산(8)은 31-01 smoke 에서 전량 소진됐고 추가 지출은
belle 승인 사항이라, 여기서는 mock 과 **로컬 self-signed TLS 서버**만 쓴다.

로컬 TLS 서버를 쓰는 이유(H3-05): redirect 차단을 urlopen monkeypatch 로 검증하면
_NoRedirectHandler 가 실제로 opener 체인에 물렸는지를 전혀 확인하지 못한다. 핸들러를
빼먹어도 mock 테스트는 그대로 통과한다. 그래서 진짜 301/302/303/307/308 응답을
핸들러까지 도달시킨다.
"""

from __future__ import annotations

import inspect
import json
import re
import ssl
import struct
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from sunity_shared import models
from sunity_shared.analysis import interfaces, visual_gen

_SRC = Path(visual_gen.__file__).read_text(encoding="utf-8")
_LAYER = str(Path(visual_gen.__file__).resolve().parents[2])  # .../shared/python
_RESULTS_JSON = (
    Path(__file__).resolve().parents[3]
    / ".planning/phases/31-api-visual-correction/smoke/RESULTS.json"
)


# ═══════════════ Task 1: typed 모델 + Protocol + Wan 어댑터 ═══════════════


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _RawResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _scripted_urlopen(monkeypatch):
    """urlopen 을 스크립트 큐로 교체 — 호출 기록 + 응답/예외 주입."""
    calls: list[dict] = []
    queue: list = []

    def fake_urlopen(req, timeout=None, **_kw):
        calls.append(
            {
                "url": getattr(req, "full_url", req),
                "method": getattr(req, "get_method", lambda: "GET")(),
                "headers": {k.lower(): v for k, v in getattr(req, "headers", {}).items()},
                "body": getattr(req, "data", None),
                "timeout": timeout,
            }
        )
        nxt = queue.pop(0) if queue else {"output": {"task_status": "PENDING"}}
        if isinstance(nxt, Exception):
            raise nxt
        if isinstance(nxt, bytes):
            return _RawResponse(nxt)
        return _FakeResponse(nxt)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return type("ScriptedHTTP", (), {"calls": calls, "queue": queue})()


@pytest.fixture
def wan_http(monkeypatch):
    return _scripted_urlopen(monkeypatch)


def test_protocols_declare_create_task_and_poll():
    """이미지·영상 양쪽이 2단계 계약 — 이미지 단발 generate 메서드 부재 (B2-02)."""
    for proto in (interfaces.ImageEditEngine, interfaces.VideoEditEngine):
        members = set(dir(proto))
        assert "create_task" in members
        assert "poll" in members
        assert "generate" not in members


def test_image_create_returns_task_id(wan_http):
    wan_http.queue.append({"output": {"task_id": "t-77"}, "request_id": "r-1"})
    created = visual_gen.WanImageAdapter("k-secret").create_task("https://s3/x.png", "fix knee")
    assert isinstance(created, visual_gen.VendorTaskCreated)
    assert (created.task_id, created.request_id) == ("t-77", "r-1")

    call = wan_http.calls[0]
    assert call["method"] == "POST"
    assert call["url"].startswith("https://dashscope-intl.aliyuncs.com")
    body = json.loads(call["body"])
    assert body["model"] == "wan2.7-image-pro"
    assert body["parameters"] == {"n": 1, "watermark": False, "prompt_extend": False}
    assert body["input"]["messages"][0]["content"] == [
        {"image": "https://s3/x.png"},
        {"text": "fix knee"},
    ]
    # X-DashScope-Async 없이는 task_id 대신 동기 응답이 온다 (B4-02 위반 경로).
    assert "x-dashscope-async" in call["headers"]


def test_image_poll_succeeded_returns_url(wan_http):
    wan_http.queue.append(
        {"output": {"task_status": "SUCCEEDED", "results": [{"url": "https://v/out.png"}]}}
    )
    r = visual_gen.WanImageAdapter("k").poll("t-77")
    assert r == visual_gen.VendorPollResult(state="succeeded", output_url="https://v/out.png")


def test_poll_running_is_pending(wan_http):
    wan_http.queue.append({"output": {"task_status": "RUNNING"}})
    assert visual_gen.WanImageAdapter("k").poll("t").state == "pending"


def test_moderation_maps_to_blocked(wan_http):
    wan_http.queue.append(
        {
            "output": {
                "task_status": "FAILED",
                "code": "DataInspectionFailed",
                "message": "Input data may contain inappropriate content.",
            }
        }
    )
    r = visual_gen.WanVideoEditAdapter("k").poll("t")
    assert (r.state, r.failure_reason) == ("blocked", "moderation")


def test_vendor_failure_and_broken_json_map_to_vendor_error(wan_http):
    wan_http.queue.append({"output": {"task_status": "FAILED", "code": "InternalError"}})
    wan_http.queue.append(b"<html>gateway timeout</html>")
    wan_http.queue.append(urllib.error.URLError("boom"))
    adapter = visual_gen.WanVideoEditAdapter("k")
    assert adapter.poll("t").failure_reason == "vendor_error"
    assert adapter.poll("t").failure_reason == "vendor_error"  # 비-JSON 본문
    assert adapter.poll("t").failure_reason == "vendor_error"  # 네트워크 예외


def test_succeeded_without_url_is_invalid_output(wan_http):
    wan_http.queue.append({"output": {"task_status": "SUCCEEDED"}})
    assert visual_gen.WanImageAdapter("k").poll("t").failure_reason == "invalid_output"


def test_create_moderation_block_is_typed(wan_http):
    wan_http.queue.append(
        {"output": {"code": "DataInspectionFailed", "message": "inappropriate content"}}
    )
    r = visual_gen.WanImageAdapter("k").create_task("https://s3/x.png", "p")
    assert (r.state, r.failure_reason) == ("blocked", "moderation")


def test_api_key_never_reaches_logs_or_url(wan_http, caplog):
    wan_http.queue.append(urllib.error.URLError("boom"))
    with caplog.at_level("DEBUG"):
        visual_gen.WanImageAdapter("SECRET-KEY-123").poll("t")
    assert "SECRET-KEY-123" not in caplog.text
    assert "SECRET-KEY-123" not in wan_http.calls[0]["url"]


def test_video_adapter_uses_videoedit_model_and_pinned_parameters(wan_http):
    wan_http.queue.append({"output": {"task_id": "t-1"}})
    visual_gen.WanVideoEditAdapter("k").create_task("https://s3/x.mp4", "rotate 90")
    body = json.loads(wan_http.calls[0]["body"])
    assert body["model"] == "wan2.7-videoedit"
    assert body["parameters"] == {
        "resolution": "720P",
        "watermark": False,
        "prompt_extend": False,
        "seed": 42,
    }


def test_failure_reasons_are_subset_of_contract():
    """typed 실패 사유는 models 단일 출처만 쓴다 — 새 문자열 발명 금지."""
    reasons = set(re.findall(r'failure_reason="([a-z_]+)"', _SRC))
    assert reasons
    assert reasons <= set(models.VISUAL_FAILURE_REASONS)
    with pytest.raises(ValueError):
        visual_gen.VendorPollResult(state="failed", failure_reason="made_up_reason")
    with pytest.raises(ValueError):
        visual_gen.VendorPollResult(state="not_a_state")
    with pytest.raises(ValueError):
        visual_gen.VendorPollResult(state="succeeded")  # url 없는 성공 금지


def test_adapters_have_no_internal_polling_loop():
    """어댑터가 스스로 폴링하면 taskId 를 journal 못 한 채 죽어 작업이 고아가 된다."""
    for cls in (visual_gen.WanImageAdapter, visual_gen.WanVideoEditAdapter, visual_gen._WanAdapterBase):
        src = inspect.getsource(cls)
        assert "sleep" not in src
        assert "while " not in src
    assert "import time" not in _SRC
    assert "requests" not in _SRC


def test_async_only_gate_reflects_smoke_results():
    """IMAGE_ENGINE_SYNC 가 RESULTS.json 실측과 어긋나면 실패 (B4-02 드리프트 방어)."""
    results = json.loads(_RESULTS_JSON.read_text(encoding="utf-8"))
    chosen = next(c for c in results["candidates"] if c["model"] == results["chosen_model"])
    assert visual_gen.IMAGE_MODEL == results["chosen_model"]
    assert visual_gen.IMAGE_ENGINE_SYNC is bool(chosen["sync"])
    assert visual_gen.IMAGE_ENGINE_BLOCKED is visual_gen.derive_engine_blocked(
        bool(chosen["sync"]), bool(results["blocked"])
    )


def test_sync_only_candidate_is_blocked():
    """sync-only 후보(qwen-image-edit-plus 류)는 품질과 무관하게 v1 불가."""
    assert visual_gen.derive_engine_blocked(True, False) is True
    assert visual_gen.derive_engine_blocked(False, True) is True
    assert visual_gen.derive_engine_blocked(False, False) is False
