"""Phase 17 Plan 06A — Phoenix 부트스트랩 optional-import 가드 테스트.

박제 정신:
  · phoenix_setup.bootstrap_tracing 가 (1) extras 설치된 정상 path 와 (2) extras
    미설치 ImportError path 양쪽 모두 분석 흐름 차단 0.
  · idempotent — 2회 호출 시 launch_app / OTLPSpanExporter / GoogleGenAIInstrumentor
    가 1회만 박힌다.
  · 외부 네트워크 호출 0 — px.launch_app / OTLPSpanExporter / GoogleGenAIInstrumentor
    는 monkeypatch.

테스트 매트릭스 (PLAN done gate 6 케이스 정합):
  1. env PHOENIX_INPROCESS=1 stub → px.launch_app 1회.
  2. env PHOENIX_OTLP_ENDPOINT 박힘 → OTLPSpanExporter 박힘.
  3. 둘 다 미설정 → graceful noop.
  4. 2회 호출 idempotent — instrument 1회만.
  5. W1 회귀: _TELEMETRY_OK=False stub → bootstrap_tracing(...) 노예외 + 모든 분기 noop.
  6. W1 회귀: pytest.importorskip("phoenix") — telemetry extras installed 검증.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest


# ─────────────────── helper ───────────────────


def _reload_phoenix_setup(force_telemetry_ok: bool = True):
    """모듈 캐시 리셋 후 reimport — bootstrap idempotent 상태 박제 회피.

    force_telemetry_ok: 정상 path 4 케이스 테스트는 extras 미설치 환경에서도
      bootstrap_tracing 의 분기 로직을 검증해야 함 — TELEMETRY_OK 강제 True 박제.
      W1 회귀 (test 5) 만 force_telemetry_ok=False 박제.
    """
    import sunity_shared.eval.phoenix_setup as ps

    importlib.reload(ps)
    if force_telemetry_ok and not ps.TELEMETRY_OK:
        # extras 미설치 환경에서도 분기 로직 검증 — monkeypatch 로 강제 박제.
        ps.TELEMETRY_OK = True
        ps._TELEMETRY_OK = True
    # idempotent 상태 박제 회피 — reload 후에도 _BOOTSTRAPPED False 강제.
    ps._BOOTSTRAPPED = False
    return ps


# ─────────────────── 정상 path 4 케이스 ───────────────────


def test_bootstrap_inprocess_path(monkeypatch):
    """W1-1: env PHOENIX_INPROCESS=1 → px.launch_app 1회 + Instrumentor 1회."""
    monkeypatch.setenv("PHOENIX_INPROCESS", "1")
    monkeypatch.delenv("PHOENIX_OTLP_ENDPOINT", raising=False)
    ps = _reload_phoenix_setup()

    launch_calls: list[None] = []
    instrument_calls: list[None] = []

    monkeypatch.setattr(
        ps, "_px_launch_app", lambda: launch_calls.append(None) or object()
    )
    monkeypatch.setattr(
        ps,
        "_instrument_google_genai",
        lambda tracer_provider=None: instrument_calls.append(None),
    )
    # extras 미설치 환경에서 _build_tracer_provider 가 None 반환 시도 stub.
    monkeypatch.setattr(ps, "_build_tracer_provider", lambda: object())

    ps.bootstrap_tracing()

    assert len(launch_calls) == 1
    assert len(instrument_calls) == 1


def test_bootstrap_otlp_path(monkeypatch):
    """W1-2: env PHOENIX_OTLP_ENDPOINT 박힘 → OTLPSpanExporter 박힘."""
    monkeypatch.delenv("PHOENIX_INPROCESS", raising=False)
    monkeypatch.setenv("PHOENIX_OTLP_ENDPOINT", "http://phoenix.local:6006/v1/traces")
    ps = _reload_phoenix_setup()

    exporter_calls: list[str] = []
    instrument_calls: list[None] = []

    def fake_exporter(endpoint: str):
        exporter_calls.append(endpoint)
        return object()

    monkeypatch.setattr(ps, "_otlp_span_exporter", fake_exporter)
    monkeypatch.setattr(
        ps,
        "_instrument_google_genai",
        lambda tracer_provider=None: instrument_calls.append(None),
    )
    # extras 미설치 시에도 분기 검증 — provider 가 None 이면 add_span_processor 미진입.
    # exporter_calls 만 검증해도 OTLP path 진입 박제 확인 가능.

    ps.bootstrap_tracing()

    assert exporter_calls == ["http://phoenix.local:6006/v1/traces"]
    assert len(instrument_calls) == 1


def test_bootstrap_noop_when_env_missing(monkeypatch):
    """W1-3: 둘 다 미설정 → graceful noop (예외 X, instrument 0회)."""
    monkeypatch.delenv("PHOENIX_INPROCESS", raising=False)
    monkeypatch.delenv("PHOENIX_OTLP_ENDPOINT", raising=False)
    ps = _reload_phoenix_setup()

    instrument_calls: list[None] = []
    launch_calls: list[None] = []

    monkeypatch.setattr(ps, "_px_launch_app", lambda: launch_calls.append(None))
    monkeypatch.setattr(
        ps,
        "_instrument_google_genai",
        lambda tracer_provider=None: instrument_calls.append(None),
    )

    # 예외 발생 X.
    ps.bootstrap_tracing()

    assert launch_calls == []
    assert instrument_calls == []


def test_bootstrap_idempotent(monkeypatch):
    """W1-4: 두 번 호출해도 instrument 1회만 박힌다."""
    monkeypatch.setenv("PHOENIX_INPROCESS", "1")
    ps = _reload_phoenix_setup()

    launch_calls: list[None] = []
    instrument_calls: list[None] = []

    monkeypatch.setattr(
        ps, "_px_launch_app", lambda: launch_calls.append(None) or object()
    )
    monkeypatch.setattr(
        ps,
        "_instrument_google_genai",
        lambda tracer_provider=None: instrument_calls.append(None),
    )
    monkeypatch.setattr(ps, "_build_tracer_provider", lambda: object())

    ps.bootstrap_tracing()
    ps.bootstrap_tracing()

    assert len(launch_calls) == 1
    assert len(instrument_calls) == 1


# ─────────────────── W1 회귀 (optional-import) ───────────────────


def test_bootstrap_noop_when_telemetry_unavailable(monkeypatch):
    """W1-5: _TELEMETRY_OK=False stub → bootstrap_tracing(...) 노예외 + 모든 분기 noop.

    Pod 에 extras 누락된 시뮬 — import 자체는 성공 (top-level optional import 가드)
    + bootstrap 가 첫 줄에서 noop 반환.
    """
    monkeypatch.setenv("PHOENIX_INPROCESS", "1")
    ps = _reload_phoenix_setup(force_telemetry_ok=False)

    # 강제로 False 박제 (extras 설치된 환경 시뮬 분리).
    monkeypatch.setattr(ps, "TELEMETRY_OK", False, raising=False)
    monkeypatch.setattr(ps, "_TELEMETRY_OK", False, raising=False)

    sentinel: list[str] = []

    def should_not_run(*_a, **_kw):
        sentinel.append("called")
        return object()

    monkeypatch.setattr(ps, "_px_launch_app", should_not_run)
    monkeypatch.setattr(ps, "_otlp_span_exporter", should_not_run)
    monkeypatch.setattr(ps, "_instrument_google_genai", should_not_run)

    # 예외 발생 X — 분석 흐름 차단 0.
    ps.bootstrap_tracing()

    assert sentinel == []


def test_telemetry_extras_installed_check():
    """W1-6: telemetry extras 가 환경에 설치돼있는지 CI 별도 게이트.

    extras 박혀있어야 통과 — 미설치 시 skip (개발/Pod 환경 분리). CI extras
    설치 회귀 단독 게이트.
    """
    pytest.importorskip("phoenix")
    pytest.importorskip("openinference.instrumentation.google_genai")
    pytest.importorskip("opentelemetry.sdk")
    pytest.importorskip("opentelemetry.exporter.otlp.proto.http.trace_exporter")
