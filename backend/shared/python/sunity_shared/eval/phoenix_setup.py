"""Phase 17 Plan 06A — Phoenix OpenTelemetry 부트스트랩 (W1 정합 optional-import).

박제 정신:
  · AI-SPEC §5 + §7 Phoenix 5 metric 박제 — google-genai SDK 자동 계측으로 4 영역의
    latency / cost / parse_success / guardrail trigger 를 span 화.
  · **W1 (Codex 2차 review caveat 정합)** — telemetry extras (arize-phoenix /
    openinference-instrumentation-google-genai / opentelemetry-*) 가 3개 runtime
    중 한쪽에 누락돼도 import 자체는 절대 깨지지 않게 module-level optional import
    가드 박제. 미설치 시 module-level 상수 `TELEMETRY_OK = False` + bootstrap_tracing
    이 첫 줄에서 noop 반환 — 분석 흐름 차단 0.
  · in-process (Pod, `PHOENIX_INPROCESS=1`) / OTLP HTTP (Lambda, `PHOENIX_OTLP_ENDPOINT`
    박힘) / 둘 다 미설정 (graceful noop) — 3 path 박제.
  · idempotent — bootstrap_tracing() 가 2회 호출돼도 TracerProvider /
    Instrumentor 가 1회만 박힌다 (`_BOOTSTRAPPED` 상태 박제).

테스트 가능성:
  · `_px_launch_app` / `_otlp_span_exporter` / `_instrument_google_genai` 는
    monkeypatch 가능. tests/eval/test_phoenix_setup.py 가 외부 네트워크 호출 0 박제.
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


# ─────────────────── optional import 가드 (W1 정합) ───────────────────
#
# extras 가 Pod / Lambda 중 한쪽에 누락돼도 import 자체는 깨지지 않게 박제.
# 미설치 시 `_TELEMETRY_OK = False` + bootstrap_tracing 이 noop 반환.

try:
    import phoenix as _phoenix  # type: ignore[import-not-found]
    from openinference.instrumentation.google_genai import (  # type: ignore[import-not-found]
        GoogleGenAIInstrumentor,
    )
    from opentelemetry import trace as _otel_trace  # type: ignore[import-not-found]
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found]
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource  # type: ignore[import-not-found]
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
    from opentelemetry.sdk.trace.export import (  # type: ignore[import-not-found]
        BatchSpanProcessor,
    )

    _TELEMETRY_OK: bool = True
except ImportError as _import_exc:  # pragma: no cover - 환경 의존 분기
    log.warning(
        "Phase 17 telemetry extras 미설치: %s — bootstrap_tracing noop (분석 흐름 차단 0).",
        _import_exc,
    )
    _TELEMETRY_OK = False
    _phoenix = None  # type: ignore[assignment]
    GoogleGenAIInstrumentor = None  # type: ignore[assignment,misc]
    _otel_trace = None  # type: ignore[assignment]
    OTLPSpanExporter = None  # type: ignore[assignment,misc]
    Resource = None  # type: ignore[assignment,misc]
    TracerProvider = None  # type: ignore[assignment,misc]
    BatchSpanProcessor = None  # type: ignore[assignment,misc]


# caller 가 `from sunity_shared.eval import TELEMETRY_OK` 박제 가능 (public).
TELEMETRY_OK: bool = _TELEMETRY_OK


# idempotent guard — bootstrap_tracing 2회 호출돼도 instrument 1회만.
_BOOTSTRAPPED: bool = False


# 서비스 이름 박제 (Phoenix UI 에서 4 영역 구분 — span resource attribute).
_SERVICE_NAME: str = "sunity-motion-phase17"


# ─────────────────── monkeypatch hooks (test 박제) ───────────────────
#
# 테스트가 외부 네트워크 호출 / Phoenix UI launch 0 박제 위해 indirection 박제.
# 실 호출 path 는 thin wrapper — 테스트에서 monkeypatch 대상.


def _px_launch_app() -> Any:
    """Pod in-process Phoenix UI launch — monkeypatch 대상."""
    if _phoenix is None:  # pragma: no cover - TELEMETRY_OK 가 False 면 진입 X
        return None
    return _phoenix.launch_app()


def _otlp_span_exporter(endpoint: str) -> Any:
    """OTLP HTTP exporter — monkeypatch 대상."""
    if OTLPSpanExporter is None:  # pragma: no cover
        return None
    return OTLPSpanExporter(endpoint=endpoint)


def _instrument_google_genai(tracer_provider: Any | None = None) -> None:
    """google-genai SDK 자동 계측 박제 — monkeypatch 대상.

    GoogleGenAIInstrumentor 가 `from google import genai` 의 generate_content 호출
    을 자동 span 화. caller (4 영역 client) 는 별도 span 박제 0 — 자동 계측만으로
    latency / cost / token 메트릭 박힘.
    """
    if GoogleGenAIInstrumentor is None:  # pragma: no cover
        return
    instrumentor = GoogleGenAIInstrumentor()
    if tracer_provider is not None:
        instrumentor.instrument(tracer_provider=tracer_provider)
    else:
        instrumentor.instrument()


def _build_tracer_provider() -> Any:
    """TracerProvider 박제 — Resource attribute 에 service.name 박힘.

    Phoenix UI / OTLP collector 에서 4 영역 구분용.
    """
    if TracerProvider is None or Resource is None:  # pragma: no cover
        return None
    resource = Resource.create({"service.name": _SERVICE_NAME})
    return TracerProvider(resource=resource)


# ─────────────────── public entry point ───────────────────


def bootstrap_tracing(in_process: bool | None = None) -> None:
    """Phoenix OpenTelemetry tracer 부트스트랩 + google-genai 자동 계측 박제.

    Args:
      in_process: True 면 Pod in-process Phoenix UI launch (`px.launch_app`).
        False 면 OTLP HTTP exporter (env `PHOENIX_OTLP_ENDPOINT`).
        None (기본) 면 env `PHOENIX_INPROCESS=="1"` 박힘 여부로 자동 결정.

    분기:
      1. `TELEMETRY_OK == False` (extras 미설치) → 첫 줄에서 noop 반환.
      2. 이미 부트스트랩됨 (`_BOOTSTRAPPED == True`) → noop (idempotent).
      3. in_process True → `_px_launch_app()` + Instrumentor.
      4. in_process False + `PHOENIX_OTLP_ENDPOINT` 박힘 → OTLPSpanExporter + Instrumentor.
      5. 모두 미해당 → graceful noop (no-op TracerProvider, instrument 0회).
    """
    global _BOOTSTRAPPED

    # 분기 1 — W1 optional-import 가드. extras 미설치 시 분석 흐름 차단 0.
    if not _TELEMETRY_OK:
        return

    # 분기 2 — idempotent (2회 호출돼도 instrument 1회만).
    if _BOOTSTRAPPED:
        return

    # env 박제 → in_process 결정.
    if in_process is None:
        in_process = os.environ.get("PHOENIX_INPROCESS") == "1"

    otlp_endpoint = os.environ.get("PHOENIX_OTLP_ENDPOINT")

    # 분기 3 — Pod in-process path.
    if in_process:
        _px_launch_app()
        provider = _build_tracer_provider()
        if provider is not None and _otel_trace is not None:
            _otel_trace.set_tracer_provider(provider)
        _instrument_google_genai(tracer_provider=provider)
        _BOOTSTRAPPED = True
        log.info("Phase 17 Phoenix tracing 부트스트랩 — in-process (Pod).")
        return

    # 분기 4 — Lambda OTLP path.
    if otlp_endpoint:
        exporter = _otlp_span_exporter(otlp_endpoint)
        provider = _build_tracer_provider()
        if (
            provider is not None
            and exporter is not None
            and BatchSpanProcessor is not None
            and _otel_trace is not None
        ):
            provider.add_span_processor(BatchSpanProcessor(exporter))
            _otel_trace.set_tracer_provider(provider)
        _instrument_google_genai(tracer_provider=provider)
        _BOOTSTRAPPED = True
        log.info(
            "Phase 17 Phoenix tracing 부트스트랩 — OTLP HTTP (endpoint=%s).",
            otlp_endpoint,
        )
        return

    # 분기 5 — graceful noop (env 미설정, in_process False).
    log.info(
        "Phase 17 Phoenix tracing 부트스트랩 skip — "
        "PHOENIX_INPROCESS / PHOENIX_OTLP_ENDPOINT 미설정 (graceful noop)."
    )


__all__ = ["TELEMETRY_OK", "bootstrap_tracing"]
