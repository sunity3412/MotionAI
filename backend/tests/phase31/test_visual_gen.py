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


# ═════════════ Task 2: safe_decode_image + download_vendor_asset ═════════════


def _png_claiming(width: int, height: int) -> bytes:
    """헤더가 width×height 를 주장하는 작은 PNG — 압축 bomb 재현용."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00"))
        + chunk(b"IEND", b"")
    )


def _real_image(fmt: str, size=(64, 48), **save_kw) -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", size, (10, 120, 200)).save(buf, format=fmt, **save_kw)
    return buf.getvalue()


_DECODE_CAPS = dict(
    allowed_formats=("PNG", "JPEG"),
    max_decoded_bytes=1024 * 1024,
    max_pixels=16 * 1024 * 1024,
    max_edge=8192,
)


def test_safe_decode_accepts_normal_image():
    img = visual_gen.safe_decode_image(_real_image("PNG"), **_DECODE_CAPS)
    assert img.size == (64, 48)


def test_safe_decode_rejects_compressed_bomb():
    """압축 1KB 미만인데 20000x20000 을 주장 — len(data) cap 은 통과한다."""
    bomb = _png_claiming(20000, 20000)
    assert len(bomb) < _DECODE_CAPS["max_decoded_bytes"]
    with pytest.raises(visual_gen.ImageDecodeError) as e:
        visual_gen.safe_decode_image(bomb, **_DECODE_CAPS)
    assert e.value.reason in ("bomb", "bad_dimension")


def test_safe_decode_rejects_oversize_edge():
    with pytest.raises(visual_gen.ImageDecodeError) as e:
        visual_gen.safe_decode_image(_png_claiming(9000, 10), **_DECODE_CAPS)
    assert e.value.reason == "bad_dimension"


def test_safe_decode_rejects_disallowed_format():
    with pytest.raises(visual_gen.ImageDecodeError) as e:
        visual_gen.safe_decode_image(_real_image("GIF"), **_DECODE_CAPS)
    assert e.value.reason == "bad_format"


def test_safe_decode_rejects_oversize_bytes_before_open():
    with pytest.raises(visual_gen.ImageDecodeError) as e:
        visual_gen.safe_decode_image(b"x" * (2 * 1024 * 1024), **_DECODE_CAPS)
    assert e.value.reason == "too_large"


def test_safe_decode_rejects_unreadable_bytes():
    with pytest.raises(visual_gen.ImageDecodeError) as e:
        visual_gen.safe_decode_image(b"not an image at all", **_DECODE_CAPS)
    assert e.value.reason == "unreadable"


def test_safe_decode_restores_global_pixel_cap():
    """MAX_IMAGE_PIXELS 는 PIL 전역이다 — 실패 경로에서도 되돌려놔야 한다."""
    from PIL import Image

    before = Image.MAX_IMAGE_PIXELS
    with pytest.raises(visual_gen.ImageDecodeError):
        visual_gen.safe_decode_image(_png_claiming(20000, 20000), **_DECODE_CAPS)
    assert Image.MAX_IMAGE_PIXELS == before


# ── self-signed TLS 로컬 서버 (H3-05) ──

_HUGE_BYTES = 200 * 1024 * 1024


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_a):  # 테스트 출력 오염 방지
        pass

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler 규약
        redirect = re.fullmatch(r"/r(\d{3})", self.path)
        if redirect:
            self.send_response(int(redirect.group(1)))
            self.send_header("Location", "https://127.0.0.1/elsewhere")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/badtype":
            self._body(b"<html/>", "text/html")
            return
        if self.path == "/big":
            self._body(b"z" * (256 * 1024), "image/png")
            return
        if self.path == "/huge":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(_HUGE_BYTES))
            self.end_headers()
            block = b"q" * (1024 * 1024)
            for _ in range(_HUGE_BYTES // len(block)):
                self.wfile.write(block)
            return
        self._body(b"payload-bytes", "image/png")

    def _body(self, body: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def tls_server(tmp_path_factory):
    d = tmp_path_factory.mktemp("tls")
    cert, key = str(d / "cert.pem"), str(d / "key.pem")
    proc = subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", key, "-out", cert, "-days", "1",
            "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1",
        ],
        capture_output=True,
    )
    if proc.returncode != 0:
        pytest.skip("openssl 미가용 — TLS 통합 테스트 skip")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"https://127.0.0.1:{httpd.server_address[1]}", cert
    httpd.shutdown()
    httpd.server_close()


def _local_kwargs(cert: str) -> dict:
    return dict(
        allowed_content_types=("image/png", "application/octet-stream"),
        _test_allowed_hosts=("127.0.0.1",),
        _test_allow_private=True,
        _test_ssl_context=ssl.create_default_context(cafile=cert),
    )


def test_download_streams_to_file_with_sha256(tls_server, tmp_path):
    import hashlib

    base, cert = tls_server
    dest = tmp_path / "out.png"
    asset = visual_gen.download_vendor_asset(
        f"{base}/ok", str(dest), max_bytes=1024 * 1024, **_local_kwargs(cert)
    )
    assert dest.read_bytes() == b"payload-bytes"
    assert asset.sha256 == hashlib.sha256(b"payload-bytes").hexdigest()
    assert (asset.size_bytes, asset.content_type) == (13, "image/png")
    assert asset.path == str(dest)


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_download_rejects_every_redirect_code(tls_server, tmp_path, code):
    """실제 30x 응답이 _NoRedirectHandler 까지 도달하는지 (H3-05).

    핸들러를 opener 에 물리는 것을 빼먹으면 여기서만 잡힌다 — urlopen mock 으로는
    영원히 통과한다.
    """
    base, cert = tls_server
    dest = tmp_path / f"r{code}"
    with pytest.raises(visual_gen.VendorDownloadError) as e:
        visual_gen.download_vendor_asset(
            f"{base}/r{code}", str(dest), max_bytes=1024, **_local_kwargs(cert)
        )
    assert e.value.reason == "redirect"
    assert not dest.exists()


def test_download_rejects_bad_content_type(tls_server, tmp_path):
    base, cert = tls_server
    with pytest.raises(visual_gen.VendorDownloadError) as e:
        visual_gen.download_vendor_asset(
            f"{base}/badtype", str(tmp_path / "x"), max_bytes=1024 * 1024, **_local_kwargs(cert)
        )
    assert e.value.reason == "bad_content_type"


def test_download_aborts_and_deletes_when_over_cap(tls_server, tmp_path):
    base, cert = tls_server
    dest = tmp_path / "big.png"
    with pytest.raises(visual_gen.VendorDownloadError) as e:
        visual_gen.download_vendor_asset(
            f"{base}/big", str(dest), max_bytes=100 * 1024, **_local_kwargs(cert)
        )
    assert e.value.reason == "too_large"
    assert not dest.exists()


@pytest.mark.parametrize(
    "url,reason",
    [
        ("http://x.aliyuncs.com/a.png", "bad_scheme"),
        ("https://evilaliyuncs.com/a.png", "bad_host"),
        ("https://aliyuncs.com.attacker.net/a.png", "bad_host"),
    ],
)
def test_download_url_policy(tmp_path, url, reason):
    with pytest.raises(visual_gen.VendorDownloadError) as e:
        visual_gen.download_vendor_asset(
            url,
            str(tmp_path / "x"),
            max_bytes=1024,
            allowed_content_types=("image/png",),
            _test_allow_private=True,
        )
    assert e.value.reason == reason


def test_download_rejects_host_resolving_to_private_ip(tmp_path):
    with pytest.raises(visual_gen.VendorDownloadError) as e:
        visual_gen.download_vendor_asset(
            "https://localhost/a.png",
            str(tmp_path / "x"),
            max_bytes=1024,
            allowed_content_types=("image/png",),
            _test_allowed_hosts=("localhost",),
        )
    assert e.value.reason == "private_ip"


def test_no_production_http_escape_hatch():
    assert "allow_http" not in _SRC
    assert "_NoRedirectHandler(urllib.request.HTTPRedirectHandler)" in _SRC
    assert "ProxyHandler({})" in _SRC


def test_download_rss_stays_bounded_in_fresh_subprocess(tls_server, tmp_path):
    """200MB 다운로드의 RSS 증가를 **별도 프로세스**에서 실측 (H3-06).

    같은 프로세스에서 ru_maxrss delta 를 재면 pytest/PIL 이 이미 올려둔 peak 에
    묻혀 항상 0 이 나온다 — 스트리밍이 깨져 전체를 메모리로 받아도 통과하는
    무의미한 측정이 된다.
    """
    base, cert = tls_server
    dest = tmp_path / "huge.bin"
    child = f"""
import json, resource, ssl, sys
sys.path.insert(0, {_LAYER!r})
from sunity_shared.analysis import visual_gen

def rss_bytes():
    v = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return v if sys.platform == "darwin" else v * 1024

baseline = rss_bytes()
visual_gen.download_vendor_asset(
    {base + "/huge"!r}, {str(dest)!r},
    max_bytes={_HUGE_BYTES + 1},
    allowed_content_types=("application/octet-stream",),
    _test_allowed_hosts=("127.0.0.1",),
    _test_allow_private=True,
    _test_ssl_context=ssl.create_default_context(cafile={cert!r}),
)
peak = rss_bytes()
print(json.dumps({{"baseline_bytes": baseline, "peak_bytes": peak,
                   "delta_bytes": peak - baseline, "platform": sys.platform}}))
"""
    proc = subprocess.run(
        [sys.executable, "-c", child], capture_output=True, text=True, timeout=600
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    measured = json.loads(proc.stdout.strip().splitlines()[-1])
    assert dest.stat().st_size == _HUGE_BYTES
    assert measured["delta_bytes"] < 64 * 1024 * 1024, measured


# ═════════════ Task 3: prepare_judge_payload + judge ═════════════


def _verdict(**overrides) -> visual_gen.JudgeVerdict:
    base = {axis: True for axis in visual_gen.JUDGE_AXES}
    base.update({"confidence": 0.9, "reason": "ok"})
    base.update(overrides)
    return visual_gen.JudgeVerdict(**base)


@pytest.fixture
def gemini_http(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return _scripted_urlopen(monkeypatch)


def _gemini_reply(payload: dict) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}


def _verdict_payload(**overrides) -> dict:
    p = {axis: True for axis in visual_gen.JUDGE_AXES}
    p.update({"confidence": 0.91, "reason": "preserved"})
    p.update(overrides)
    return p


def _inline_images(body: bytes) -> list[bytes]:
    import base64 as _b64

    parts = json.loads(body)["contents"][0]["parts"]
    return [_b64.b64decode(p["inline_data"]["data"]) for p in parts if "inline_data" in p]


def test_prepare_payload_normalizes_large_images_under_cap():
    """4000x3000 원본 2장이 정규화 후 16MB 상한 아래로 들어간다."""
    big = _real_image("PNG", size=(4000, 3000))
    body = visual_gen.prepare_judge_payload(big, big, "p")
    assert len(body) < visual_gen.JUDGE_BODY_MAX_BYTES
    parts = json.loads(body)["contents"][0]["parts"]
    assert [p["text"] for p in parts if "text" in p] == ["BEFORE (원본)", "AFTER (생성)", "p"]
    assert all(p["inline_data"]["mime_type"] == "image/jpeg" for p in parts if "inline_data" in p)


def test_prepare_payload_downscales_to_2048_edge():
    from io import BytesIO

    from PIL import Image

    body = visual_gen.prepare_judge_payload(
        _real_image("PNG", size=(4000, 1000)), _real_image("PNG"), "p"
    )
    img = Image.open(BytesIO(_inline_images(body)[0]))
    assert max(img.size) == 2048


def test_prepare_payload_strips_exif():
    from io import BytesIO

    from PIL import Image

    exif = Image.Exif()
    exif[271] = "SecretCameraMaker"
    src = _real_image("JPEG", exif=exif.tobytes())
    assert b"SecretCameraMaker" in src

    out = _inline_images(visual_gen.prepare_judge_payload(src, src, "p"))[0]
    assert b"SecretCameraMaker" not in out
    assert not dict(Image.open(BytesIO(out)).getexif())


def test_prepare_payload_raises_when_serialized_body_exceeds_cap(monkeypatch):
    monkeypatch.setattr(visual_gen, "JUDGE_BODY_MAX_BYTES", 1024)
    with pytest.raises(visual_gen.JudgeInputTooLargeError):
        visual_gen.prepare_judge_payload(_real_image("PNG"), _real_image("PNG"), "p")


def test_bomb_input_is_rejected_before_any_gemini_call(gemini_http):
    """bomb 은 판정 API 로 나가기 전에 typed 로 끝난다 (H4-06)."""
    bomb = _png_claiming(20000, 20000)
    with pytest.raises(visual_gen.JudgeInputTooLargeError):
        visual_gen.judge_corrected_pose(bomb, bomb, {}, api_key="k")
    assert gemini_http.calls == []


def test_judge_parses_verdict_and_sends_key_in_header_only(gemini_http):
    gemini_http.queue.append(_gemini_reply(_verdict_payload(clothing_ok=False)))
    v = visual_gen.judge_corrected_pose(
        _real_image("PNG"), _real_image("PNG"), {"correction_hint": "왼 무릎"}, api_key="G-SECRET"
    )
    assert v is not None
    assert v.clothing_ok is False and v.identity_ok is True
    assert v.confidence == pytest.approx(0.91)

    call = gemini_http.calls[0]
    assert call["url"] == visual_gen.GEMINI_ENDPOINT
    assert "gemini-3.5-flash" in call["url"]
    assert call["headers"]["x-goog-api-key"] == "G-SECRET"
    assert "G-SECRET" not in call["url"]
    texts = [p["text"] for p in json.loads(call["body"])["contents"][0]["parts"] if "text" in p]
    assert any("왼 무릎" in t for t in texts)


def test_judge_returns_none_without_key_and_makes_no_request(gemini_http):
    assert visual_gen.judge_corrected_pose(_real_image("PNG"), _real_image("PNG"), {}) is None
    assert gemini_http.calls == []


def test_judge_retries_once_on_5xx_then_fails_closed(gemini_http):
    for _ in range(2):
        gemini_http.queue.append(
            urllib.error.HTTPError(visual_gen.GEMINI_ENDPOINT, 503, "x", {}, None)
        )
    assert (
        visual_gen.judge_corrected_pose(_real_image("PNG"), _real_image("PNG"), {}, api_key="k")
        is None
    )
    assert len(gemini_http.calls) == 2


def test_judge_recovers_when_retry_succeeds(gemini_http):
    gemini_http.queue.append(urllib.error.HTTPError(visual_gen.GEMINI_ENDPOINT, 500, "x", {}, None))
    gemini_http.queue.append(_gemini_reply(_verdict_payload()))
    v = visual_gen.judge_corrected_pose(_real_image("PNG"), _real_image("PNG"), {}, api_key="k")
    assert v is not None and len(gemini_http.calls) == 2


def test_judge_does_not_retry_on_4xx(gemini_http):
    gemini_http.queue.append(urllib.error.HTTPError(visual_gen.GEMINI_ENDPOINT, 400, "x", {}, None))
    assert (
        visual_gen.judge_corrected_pose(_real_image("PNG"), _real_image("PNG"), {}, api_key="k")
        is None
    )
    assert len(gemini_http.calls) == 1


@pytest.mark.parametrize(
    "reply",
    [
        {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]},
        {"candidates": []},
        {},
    ],
)
def test_judge_fails_closed_on_malformed_reply(gemini_http, reply):
    gemini_http.queue.append(reply)
    assert (
        visual_gen.judge_corrected_pose(_real_image("PNG"), _real_image("PNG"), {}, api_key="k")
        is None
    )


def test_judge_fails_closed_when_axis_missing(gemini_http):
    payload = _verdict_payload()
    del payload["pole_ok"]
    gemini_http.queue.append(_gemini_reply(payload))
    assert (
        visual_gen.judge_corrected_pose(_real_image("PNG"), _real_image("PNG"), {}, api_key="k")
        is None
    )


def test_judge_key_absent_from_logs(gemini_http, caplog):
    gemini_http.queue.append(urllib.error.HTTPError(visual_gen.GEMINI_ENDPOINT, 400, "x", {}, None))
    with caplog.at_level("DEBUG"):
        visual_gen.judge_corrected_pose(
            _real_image("PNG"), _real_image("PNG"), {}, api_key="LEAKME"
        )
    assert "LEAKME" not in caplog.text


def test_pass_helpers_take_threshold_as_argument():
    """모듈이 임계값을 알면 31-13 calibration 이 grid 를 못 돈다 (H3-02)."""
    for fn in (visual_gen.judge_display_pass, visual_gen.judge_training_pass):
        param = inspect.signature(fn).parameters["min_confidence"]
        assert param.kind is inspect.Parameter.KEYWORD_ONLY
        assert param.default is inspect.Parameter.empty
    assert not re.search(r"(?<![\w.])0\.\d+", _SRC), "판정 임계값 리터럴 금지"


def test_confidence_boundary_is_inclusive():
    v = _verdict(confidence=0.80)
    assert visual_gen.judge_display_pass(v, min_confidence=0.80) is True
    assert visual_gen.judge_display_pass(v, min_confidence=0.81) is False


def test_display_and_training_thresholds_diverge_on_same_verdict():
    """같은 판정이 노출은 통과, 학습 적재는 탈락 — 실패 비용이 다르기 때문 (B4-05)."""
    v = _verdict(confidence=0.80)
    assert visual_gen.judge_display_pass(v, min_confidence=0.70) is True
    assert visual_gen.judge_training_pass(v, min_confidence=0.95) is False


@pytest.mark.parametrize("axis", ["single_person_ok", "no_extra_limbs"])
def test_hard_rejection_beats_high_confidence(axis):
    v = _verdict(confidence=1.0, **{axis: False})
    assert visual_gen.judge_display_pass(v, min_confidence=0.0) is False
    assert visual_gen.judge_training_pass(v, min_confidence=0.0) is False


def test_preservation_axis_failure_blocks_pass():
    """전면 재생성 실패 유형 — correction_visible 은 참인데 보존 축이 깨진 경우.

    31-01 실측에서 8건 중 6건이 이 형태였다(자세 전면 재생성, 1건은 복장 색까지
    변경). 이 케이스가 통과하면 judge 는 무의미하다.
    """
    for broken in ("identity_ok", "clothing_ok", "background_ok", "pole_ok"):
        v = _verdict(confidence=1.0, correction_visible=True, **{broken: False})
        assert visual_gen.judge_display_pass(v, min_confidence=0.0) is False


def test_judge_stays_lambda_compatible():
    for banned in ("google.genai", "google_genai", "from google", "pydantic", "import requests"):
        assert banned not in _SRC
    assert "generativelanguage" in _SRC
    assert "x-goog-api-key" in _SRC
    assert visual_gen.PROMPT_VERSION == "judge-v1"


def test_prepare_payload_called_only_inside_judge():
    """워커가 prepare 를 선호출하면 같은 이미지를 두 번 decode 한다 (M4-02)."""
    assert _SRC.count("prepare_judge_payload(") == 2  # def + judge_corrected_pose 내 1회
    assert "prepare_judge_payload(" in inspect.getsource(visual_gen.judge_corrected_pose)
