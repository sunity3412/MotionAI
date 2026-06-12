---
phase: 17-gemini-vision-integration-4
plan: 06A
subsystem: telemetry
tags: [phoenix, opentelemetry, openinference, optional-import]

requires:
  - phase: 17-gemini-vision-integration-4
    provides: "Phase 17 Wave 1~4 의 4 영역 client 박제 (Plan 01~05 SUMMARY)"
provides:
  - "sunity_shared.eval.phoenix_setup.bootstrap_tracing — Phoenix OpenTelemetry tracer 박제 (in-process/OTLP/noop 3 path)"
  - "TELEMETRY_OK module-level 상수 — caller 가 extras 설치 여부 분기"
  - "3개 runtime requirements.txt 에 telemetry extras 박힘 (W1 정합)"
affects: [phase-17-plan-06B, phase-17-plan-06C, phase-17-rollout]

tech-stack:
  added:
    - arize-phoenix (>=4.0,<5.0)
    - openinference-instrumentation-google-genai (>=0.1,<1.0)
    - opentelemetry-sdk (>=1.27,<2.0)
    - opentelemetry-exporter-otlp-proto-http (>=1.27,<2.0)
    - opentelemetry-api (>=1.27,<2.0)
  patterns:
    - "Module-level optional-import 가드 — extras 미설치 시 sentinel False + noop 분기 박제"
    - "Idempotent bootstrap — `_BOOTSTRAPPED` 상태 플래그 박제로 2회 호출 시 instrument 1회만"
    - "Indirection function (`_px_launch_app` / `_otlp_span_exporter` / `_instrument_google_genai`) — 테스트가 외부 호출 0 박제"

key-files:
  created:
    - backend/shared/python/sunity_shared/eval/__init__.py
    - backend/shared/python/sunity_shared/eval/phoenix_setup.py
    - backend/tests/eval/__init__.py
    - backend/tests/eval/test_phoenix_setup.py
  modified:
    - backend/runpod_inference/requirements.txt
    - backend/functions/pipeline/requirements.txt
    - backend/shared/python/requirements.txt

key-decisions:
  - "Module-level optional-import 가드 박제 — telemetry extras 가 3개 runtime 중 한쪽에 누락돼도 import 자체가 깨지지 않게. W1 (Codex 2차 review caveat) 정합."
  - "TELEMETRY_OK public 상수 노출 — caller (4 영역 client) 가 `if TELEMETRY_OK:` 가드 박제 가능."
  - "Pod 는 in-process Phoenix UI 호스트 (`PHOENIX_INPROCESS=1`) + OTLP 양쪽 박제, Lambda 는 OTLP HTTP exporter 만 (250MB 한도 정합)."

patterns-established:
  - "Optional-import 가드 패턴 — try/except ImportError + sentinel False + noop 분기. extras 미설치 분석 흐름 차단 0 보장."

requirements-completed:
  - VISION-01
  - VISION-02
  - VISION-03
  - VISION-04

duration: 5 min
completed: 2026-06-12
---

# Phase 17 Plan 06A: Telemetry deps + Phoenix optional-import 부트스트랩 Summary

**Phoenix OpenTelemetry tracer 박제 + telemetry extras optional-import 가드 — 3개 runtime requirements.txt + bootstrap_tracing 분기 박제 (in-process/OTLP/noop 3 path).**

## Performance

- **Duration:** 5 min (Sub-phase 06A 단독)
- **Started:** 2026-06-12T03:13:00Z
- **Completed:** 2026-06-12T03:18:00Z
- **Tasks:** 1 (Task 1 — Sub-phase 06A)
- **Files modified:** 7

## Accomplishments

- `arize-phoenix>=4.0,<5.0` / `openinference-instrumentation-google-genai>=0.1,<1.0` / `opentelemetry-sdk>=1.27,<2.0` / `opentelemetry-exporter-otlp-proto-http>=1.27,<2.0` 박제 — Pod (in-process + OTLP 양쪽 가능) / Lambda (OTLP only) / shared layer (`opentelemetry-api`) 분리 박제.
- `phoenix_setup.bootstrap_tracing(in_process=None)` — idempotent + 3 path 분기 (in-process Pod / OTLP HTTP / graceful noop).
- W1 정합 — extras 미설치 환경에서도 `from sunity_shared.eval import bootstrap_tracing, TELEMETRY_OK` 박제 + bootstrap_tracing() 호출 노예외.
- 6 케이스 테스트 박제 — 정상 path 4 + W1 회귀 2 (extras 미설치 noop + extras installed importorskip).

## Task Commits

1. **Task 1 (Sub-phase 06A): telemetry deps + Phoenix optional-import 부트스트랩** — `f72bb72` (feat)

## Files Created/Modified

- `backend/shared/python/sunity_shared/eval/__init__.py` — eval 패키지 진입 박제 (TELEMETRY_OK / bootstrap_tracing 노출).
- `backend/shared/python/sunity_shared/eval/phoenix_setup.py` — 부트스트랩 + optional-import 가드 본체.
- `backend/tests/eval/test_phoenix_setup.py` — 6 케이스 테스트.
- `backend/runpod_inference/requirements.txt` — arize-phoenix + openinference + opentelemetry-sdk/exporter 박제.
- `backend/functions/pipeline/requirements.txt` — OTLP exporter + Instrumentor (Lambda 250MB 한도 — Phoenix UI 의존성 제외).
- `backend/shared/python/requirements.txt` — opentelemetry-api 공통 layer.

## Decisions Made

- Module-level optional-import 가드 박제 — sentinel `_TELEMETRY_OK` 가 False 면 bootstrap_tracing 첫 줄에서 noop 반환. W1 (Codex 2차 review caveat) 정합.
- Pod = in-process + OTLP 양쪽 가능 / Lambda = OTLP only — 환경별 extras 차이 박제.
- Indirection function (`_px_launch_app` / `_otlp_span_exporter` / `_instrument_google_genai`) — 테스트가 외부 호출 0 박제 가능.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Sub-phase 06B 진입 가능 — 4 영역 client 의 TELEMETRY_OK gate 박제 + guardrail span event 박제.

---
*Phase: 17-gemini-vision-integration-4*
*Sub-phase: 06A*
*Completed: 2026-06-12*
