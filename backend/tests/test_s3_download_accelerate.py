"""quick-260923-weq — 영상 다운로드 클라이언트만 S3 Transfer Acceleration 을 탄다.

EU-RO Pod ↔ 서울 S3 직결은 연결 단위로 멎는다(2026-09-23 실측: 30MB 4회 중 3회 5~7KB/s,
첫 분석 다운로드 55MB 에 30분). 같은 Pod 에서 가속 엔드포인트는 4/4 8.5MB/s.
`S3_USE_ACCELERATE=1` 이면 `_s3_dl` 만 가속 엔드포인트, `_s3`(업로드·서명 URL)는 그대로여야 한다 —
앱이 받는 재생 URL 이 가속 호스트로 바뀌면 GB 당 과금이 앱 트래픽에도 붙는다.
미설정이면 둘이 같은 객체(Lambda 경로 byte-동일).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _reload_app(monkeypatch, accelerate: str | None):
    if accelerate is None:
        monkeypatch.delenv("S3_USE_ACCELERATE", raising=False)
    else:
        monkeypatch.setenv("S3_USE_ACCELERATE", accelerate)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    sys.modules.pop("app", None)
    import app  # noqa: WPS433

    return importlib.reload(app)


def test_download_client_uses_accelerate_only_when_flagged(monkeypatch):
    app = _reload_app(monkeypatch, "1")
    assert app._s3_dl is not None and app._s3_dl is not app._s3
    assert app._s3_dl.meta.config.s3.get("use_accelerate_endpoint") is True
    assert not (app._s3.meta.config.s3 or {}).get("use_accelerate_endpoint")


def test_download_goes_through_patched_plain_client_without_flag(monkeypatch):
    """플래그 없으면 호출 시점의 app._s3 를 쓴다 — 테스트 관례(가짜 _s3 주입)와 Lambda 경로 보존."""
    app = _reload_app(monkeypatch, None)
    calls = []

    class _Fake:
        def download_file(self, b, k, d):
            calls.append((b, k, d))

    monkeypatch.setattr(app, "_s3", _Fake())
    app._s3_download("b", "k", "/tmp/x")
    assert calls == [("b", "k", "/tmp/x")]


def test_download_client_is_plain_without_flag(monkeypatch):
    app = _reload_app(monkeypatch, None)
    assert app._s3_dl is None
