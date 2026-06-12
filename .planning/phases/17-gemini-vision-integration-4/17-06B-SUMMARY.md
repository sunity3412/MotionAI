---
phase: 17-gemini-vision-integration-4
plan: 06B
subsystem: telemetry
tags: [phoenix, opentelemetry, guardrail, llm-judge, smart-sampling]

requires:
  - phase: 17-gemini-vision-integration-4
    provides: "Sub-phase 06A (Phoenix bootstrap + TELEMETRY_OK gate 박제)"
provides:
  - "4 영역 client (client/scene_finder/coach_writer_v2/reference_extractor) 의 guardrail span event 박제 (G1/G2/G3/G4/G5)"
  - "LLM judge (영역 B 코칭 톤 binary pass + belle 라벨 calibration mode) — gemini-3.5-flash"
  - "Smart sampling (AI-SPEC §7 7 rule) + Firestore eval/phase17 박제 helper"
affects: [phase-17-plan-06C, phase-17-production-rollout]

tech-stack:
  added: []
  patterns:
    - "TELEMETRY_OK gate 박제 — 모든 span 박제 라인 앞에 `if TELEMETRY_OK and _tracer is not None:` 박제. extras 미설치 시 분석 흐름 차단 0."
    - "Single-line span event 박제 — done gate `grep 'add_event.*guardrail'` 정합."
    - "judge LLM indirection (`_call_judge_llm`) — 테스트가 외부 호출 0."
    - "sampling random indirection (`_random`) — 테스트가 deterministic seed."

key-files:
  created:
    - backend/shared/python/sunity_shared/eval/llm_judge.py
    - backend/shared/python/sunity_shared/eval/sampling.py
    - backend/tests/eval/test_llm_judge.py
    - backend/tests/eval/test_sampling.py
  modified:
    - backend/shared/python/sunity_shared/gemini/client.py
    - backend/shared/python/sunity_shared/gemini/scene_finder.py
    - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
    - backend/shared/python/sunity_shared/gemini/reference_extractor.py

key-decisions:
  - "LLM judge model = gemini-3.5-flash — memory [[gemini-latest-model-versions]] 정합 (2.5 영구 금지)."
  - "G1 (점수/판단) vs G5 (좌표) 분기 박제 — guardrails ValueError 메시지 내 '좌표' 어휘로 식별."
  - "Smart sampling priority — guardrail_triggered 가 score 양극단보다 먼저 (100% > 20%). 1회 매치 후 short-circuit."
  - "Firestore eval/phase17 박제 helper 가 graceful skip — 박제 실패가 분석 흐름 차단 0."

patterns-established:
  - "TELEMETRY_OK gate 패턴 — span 박제 라인 앞 모든 곳에 박힘. 4 module × 평균 2.5 gate = 10 gate."
  - "Span event single-line 박제 — `grep` 친화적 형식. attributes dict 동일 라인 박제."

requirements-completed:
  - VISION-01
  - VISION-02
  - VISION-03
  - VISION-04

duration: 7 min
completed: 2026-06-12
---

# Phase 17 Plan 06B: 4 영역 guardrail span + LLM judge + Smart sampling Summary

**4 영역 client (client/scene_finder/coach_writer_v2/reference_extractor) 의 G1/G2/G3/G4/G5 guardrail span event 박제 + Gemini Flash LLM judge (belle 라벨 calibration) + AI-SPEC §7 7 rule Smart sampling + Firestore eval/phase17 박제 helper.**

## Performance

- **Duration:** 7 min (Sub-phase 06B 단독)
- **Started:** 2026-06-12T03:18:00Z
- **Completed:** 2026-06-12T03:25:00Z
- **Tasks:** 2 (Task 1b + Task 2)
- **Files modified:** 8

## Accomplishments

- **Task 1b — 4 영역 guardrail span event 박제** —
  - client.py: G1 (점수/판단 어휘) + G5 (좌표) span event + parse_success / retry_count / model attribute 박제.
  - scene_finder.py: G4 (정은지 영상 occlusion FP) span event.
  - coach_writer_v2.py: G2 (강사 톤 검증 폴백) span event.
  - reference_extractor.py: G3 (IPSF 화이트리스트 miss → branch_3_auto) span event.
  - 총 5 span event (G1/G2/G3/G4/G5) + 10 TELEMETRY_OK gate.
- **Task 2 — LLM judge + Smart sampling 박제** —
  - `judge_coach_tone(coach_payload, belle_label=None)` — Gemini Flash text-only judge + belle binary 라벨 calibration mode (confidence 1.0/0.0 박제, correlation ≥ 0.7 gate 입력).
  - `should_sample(analysis_doc)` — AI-SPEC §7 7 rule (isReference/guardrail/score 양극단/causes 최소/영역C flag/branch_3_auto/baseline) priority order 박제.
  - `record_eval_sample(...)` — Firestore eval/phase17/samples/{analysis_id} 박제 helper (graceful skip).

## Task Commits

1. **Task 1b (Sub-phase 06B step 1): 4 영역 client guardrail span event 박제** — `9101225` (feat)
2. **Task 2 (Sub-phase 06B step 2): LLM judge + Smart sampling + Firestore eval 박제** — `75fa1f0` (feat)

## Files Created/Modified

- `backend/shared/python/sunity_shared/eval/llm_judge.py` — judge_coach_tone (Gemini Flash text-only) + belle 라벨 calibration mode.
- `backend/shared/python/sunity_shared/eval/sampling.py` — should_sample (7 rule priority) + record_eval_sample helper.
- `backend/tests/eval/test_llm_judge.py` — 5 케이스.
- `backend/tests/eval/test_sampling.py` — 9 케이스 (7 rule × edge case 확장).
- `backend/shared/python/sunity_shared/gemini/client.py` — G1/G5 span event + parse_success attribute.
- `backend/shared/python/sunity_shared/gemini/scene_finder.py` — G4 span event.
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` — G2 span event.
- `backend/shared/python/sunity_shared/gemini/reference_extractor.py` — G3 span event.

## Decisions Made

- LLM judge model = `gemini-3.5-flash` — memory [[gemini-latest-model-versions]] 정합 (2.5 영구 금지).
- G1 vs G5 분기 — guardrails ValueError 메시지 내 '좌표' 어휘 검색으로 식별. 별도 exception type 박제 회피 (기존 guardrails.py 시그너처 회귀 0).
- Span event single-line 박제 — `grep "add_event.*guardrail"` done gate 정합. attributes dict 동일 라인.
- Smart sampling priority — guardrail_triggered 가 score 양극단보다 먼저 (100% > 20%). 1회 매치 후 short-circuit.
- Firestore eval/phase17 박제 helper graceful skip — eval 박제 실패 → log warning + noop, 분석 흐름 차단 0.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- 초기 박제 시 span event 가 multi-line 형식 (attributes dict 별도 줄) — plan done gate `grep "add_event.*guardrail" ... | wc -l` 가 0 반환. 4 파일 모두 single-line 형식으로 reformat 후 5 박힘 (done gate ≥ 4 통과).

## Next Phase Readiness

- Sub-phase 06C 진입 가능 — Promptfoo local eval config + 30 entry dataset + assertion script 박제.

---
*Phase: 17-gemini-vision-integration-4*
*Sub-phase: 06B*
*Completed: 2026-06-12*
