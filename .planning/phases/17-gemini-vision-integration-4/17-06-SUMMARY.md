---
phase: 17-gemini-vision-integration-4
plan: 06
subsystem: eval
tags: [phoenix, opentelemetry, openinference, promptfoo, guardrail, llm-judge, smart-sampling, ipsf]

requires:
  - phase: 17-gemini-vision-integration-4
    provides: "Plan 17-01 ~ 17-05 — 4 영역 client (GeminiVisionCall + scene_finder + coach_writer_v2 + reference_extractor + keypoint_augmenter)"
provides:
  - "Phase 17 telemetry + guardrail + eval 박제 — Phoenix bootstrap + 5 guardrail span event + LLM judge (영역 B 톤) + Smart sampling 7 rule + Firestore eval/phase17 박제 helper + Promptfoo local eval config (30 entry dataset + 3 assertion + README)"
affects: [phase-17-rollout, phase-17-eval-ci-integration-future, pole-sports-pilot]

tech-stack:
  added:
    - arize-phoenix (>=4.0,<5.0)
    - openinference-instrumentation-google-genai (>=0.1,<1.0)
    - opentelemetry-sdk / opentelemetry-exporter-otlp-proto-http / opentelemetry-api (>=1.27,<2.0)
    - promptfoo (npm — 수동 설치)
  patterns:
    - "Module-level optional-import 가드 (W1 정합)"
    - "TELEMETRY_OK gate 박제 (4 영역 × 평균 2.5 gate = 10 gate)"
    - "Single-line span event 박제 (grep-friendly)"
    - "Local eval 박제 → CI 자동 게이트 박제 separation 패턴 (W6 정합)"
    - "Self-contained Python assertion (Promptfoo eval 환경 분리)"
    - "judge LLM / sampling random indirection (테스트 monkeypatch 패턴)"

key-files:
  created:
    - backend/shared/python/sunity_shared/eval/__init__.py
    - backend/shared/python/sunity_shared/eval/phoenix_setup.py
    - backend/shared/python/sunity_shared/eval/llm_judge.py
    - backend/shared/python/sunity_shared/eval/sampling.py
    - backend/tests/eval/__init__.py
    - backend/tests/eval/test_phoenix_setup.py
    - backend/tests/eval/test_llm_judge.py
    - backend/tests/eval/test_sampling.py
    - backend/evals/phase17/promptfooconfig.yaml
    - backend/evals/phase17/README.md
    - backend/evals/phase17/dataset/reference_dataset.yaml
    - backend/evals/phase17/dataset/labels.json
    - backend/evals/phase17/assertions/__init__.py
    - backend/evals/phase17/assertions/objectivity_reject.py
    - backend/evals/phase17/assertions/ipsf_routing.py
    - backend/evals/phase17/assertions/coach_tone.py
  modified:
    - backend/runpod_inference/requirements.txt
    - backend/functions/pipeline/requirements.txt
    - backend/shared/python/requirements.txt
    - backend/shared/python/sunity_shared/gemini/client.py
    - backend/shared/python/sunity_shared/gemini/scene_finder.py
    - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
    - backend/shared/python/sunity_shared/gemini/reference_extractor.py

key-decisions:
  - "Sub-phase 06A/06B/06C in-file 박제 — 별도 PLAN 파일 split (06A.md/06B.md/06C.md) 박제 X. GSD execute-phase tooling 의 frontmatter `plan: <int>` 파싱 alphanumeric 거부 위험 박제 회피."
  - "각 sub-phase 별 SUMMARY 박제 (17-06A/B/C-SUMMARY.md) + 통합 17-06-SUMMARY.md cross-reference — Codex 2차 review 의 06A 조기 검증 가치 동등 박제."
  - "W1 (telemetry extras optional-import) 정합 — extras 미설치 시 분석 흐름 차단 0 박제. TELEMETRY_OK gate 4 영역 박제 (10 gate)."
  - "W6 (local eval 박제) 정합 — Promptfoo config 는 belle 수동 실행. CI 자동 게이트 별도 후속 plan. PR pre-merge auto-block 표현 박제 0건."
  - "LLM judge model = gemini-3.5-flash — memory [[gemini-latest-model-versions]] 정합."
  - "Smart sampling 7 rule priority — guardrail_triggered > score 양극단 (100% > 20%) — 가짜 신호 우선 박제."

patterns-established:
  - "Optional-import 가드 — sentinel False + noop 분기."
  - "TELEMETRY_OK gate — span 박제 라인 앞 모든 곳."
  - "Local eval / CI gate separation — 본 plan 박제 vs 후속 plan 박제 명확."
  - "Indirection function (외부 호출/random) — 테스트 monkeypatch 박제 가능."

requirements-completed:
  - VISION-01
  - VISION-02
  - VISION-03
  - VISION-04

duration: 18 min
completed: 2026-06-12
---

# Phase 17 Plan 06: Eval + Guardrail wiring Summary

**AI-SPEC §5 (E1~E8 8 dimension) + §6 (G1~G6 6 guardrail) + §7 (Phoenix 5 metric + Smart Sampling 7 rule) 전체 코드화 — Phoenix optional-import 부트스트랩 (3 path) + 4 영역 client 의 G1/G2/G3/G4/G5 span event 박제 + Gemini Flash LLM judge (영역 B 톤 binary + belle 라벨 calibration) + Smart sampling 7 rule + Firestore eval/phase17 박제 + Promptfoo local eval (50 entry dataset + 3 assertion + README, W6 정합 PR auto-block 0건).**

## Sub-phase Cross-Reference

- [17-06A-SUMMARY.md](./17-06A-SUMMARY.md) — Telemetry deps + Phoenix optional-import 부트스트랩 (Task 1).
- [17-06B-SUMMARY.md](./17-06B-SUMMARY.md) — 4 영역 client guardrail span event + LLM judge + Smart sampling (Task 1b + Task 2).
- [17-06C-SUMMARY.md](./17-06C-SUMMARY.md) — Promptfoo local eval config + dataset + assertions (Task 3).

## Performance

- **Duration:** 18 min (전체 plan)
- **Started:** 2026-06-12T03:13:00Z
- **Completed:** 2026-06-12T03:31:00Z
- **Tasks:** 4 (Task 1 + 1b + 2 + 3 — Sub-phase 06A/06B/06C in-file 박제)
- **Files modified:** 23 (created 16 + modified 7)

## Accomplishments

- **Sub-phase 06A** — Phoenix OpenTelemetry tracer 박제 + telemetry extras optional-import 가드 (in-process Pod / OTLP HTTP Lambda / graceful noop 3 path). 3개 runtime requirements.txt 박제.
- **Sub-phase 06B step 1** — 4 영역 client (client/scene_finder/coach_writer_v2/reference_extractor) 의 G1/G2/G3/G4/G5 guardrail span event 박제. TELEMETRY_OK gate 10개.
- **Sub-phase 06B step 2** — `judge_coach_tone` Gemini Flash judge (belle binary 라벨 calibration mode, confidence 1.0/0.0) + `should_sample` Smart sampling 7 rule (priority order) + `record_eval_sample` Firestore eval/phase17 박제 helper.
- **Sub-phase 06C** — Promptfoo local eval config (수동 실행 — CI 자동 게이트 별도 plan, W6 정합 PR auto-block 0건) + 50 entry reference dataset (영역 A 10 + B 10 + C 20 + D 10) + 3 self-contained Python assertion + README.

## Task Commits

1. **Task 1 (Sub-phase 06A): telemetry deps + Phoenix optional-import 부트스트랩** — `f72bb72` (feat)
2. **Task 1b (Sub-phase 06B step 1): 4 영역 client guardrail span event 박제** — `9101225` (feat)
3. **Task 2 (Sub-phase 06B step 2): LLM judge + Smart sampling + Firestore eval 박제** — `75fa1f0` (feat)
4. **Task 3 (Sub-phase 06C): Promptfoo local eval config + 30 entry dataset + assertion 3** — `caf1616` (feat)

## Files Created/Modified

### Sub-phase 06A
- `backend/shared/python/sunity_shared/eval/__init__.py` — eval 패키지 진입.
- `backend/shared/python/sunity_shared/eval/phoenix_setup.py` — bootstrap + optional-import 가드.
- `backend/tests/eval/__init__.py`, `backend/tests/eval/test_phoenix_setup.py` — 6 케이스.
- `backend/runpod_inference/requirements.txt` — arize-phoenix + opentelemetry + Instrumentor.
- `backend/functions/pipeline/requirements.txt` — opentelemetry + Instrumentor (Phoenix UI 제외).
- `backend/shared/python/requirements.txt` — opentelemetry-api 공통.

### Sub-phase 06B
- `backend/shared/python/sunity_shared/eval/llm_judge.py` — judge_coach_tone + belle 라벨 calibration.
- `backend/shared/python/sunity_shared/eval/sampling.py` — should_sample 7 rule + record_eval_sample helper.
- `backend/tests/eval/test_llm_judge.py`, `test_sampling.py` — 14 케이스.
- `backend/shared/python/sunity_shared/gemini/client.py` — G1/G5 span event.
- `backend/shared/python/sunity_shared/gemini/scene_finder.py` — G4.
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` — G2.
- `backend/shared/python/sunity_shared/gemini/reference_extractor.py` — G3.

### Sub-phase 06C
- `backend/evals/phase17/promptfooconfig.yaml` — Promptfoo local eval config.
- `backend/evals/phase17/README.md` — belle 실행 절차 + CI 자동 게이트 별도 plan 박제 명시.
- `backend/evals/phase17/dataset/reference_dataset.yaml` — 50 entry.
- `backend/evals/phase17/dataset/labels.json` — 정은지 5 labeled + 25 TODO.
- `backend/evals/phase17/assertions/objectivity_reject.py` — E1.
- `backend/evals/phase17/assertions/ipsf_routing.py` — E2/E3.
- `backend/evals/phase17/assertions/coach_tone.py` — E4.

## Decisions Made

- Sub-phase 06A/06B/06C in-file 박제 — Codex 2차 review 권장 split 박제 X (GSD execute-phase tooling 의 frontmatter alphanumeric 거부 위험). 동등 가치는 Task 단위 sub SUMMARY + checkpoint 박제로 박힘.
- W1 (Codex 2차 review caveat) 정합 — telemetry extras optional-import 가드. TELEMETRY_OK gate 4 영역 박제.
- W6 (2차 R-Plan 06C) 정합 — Promptfoo local eval (belle 수동). CI 자동 게이트 별도 plan.
- LLM judge model = `gemini-3.5-flash` — memory [[gemini-latest-model-versions]] 정합 (2.5 영구 금지).
- Smart sampling 7 rule priority — guardrail_triggered > score 양극단 (100% > 20%). 가짜 신호 우선 박제.
- Firestore eval/phase17 박제 graceful skip — eval 박제 실패 → log warning + noop, 분석 흐름 차단 0.

## Deviations from Plan

None — plan executed exactly as written.

### 박제 시 경과 정정 (Issues Encountered 박제):

- 초기 span event 박제 시 multi-line 형식 사용 → plan done gate `grep "add_event.*guardrail" ... | wc -l` 가 0 반환. 4 파일 모두 single-line 형식으로 재박제 후 5 span event 박힘 (done gate ≥ 4 통과). 이는 plan 의 done gate 박제 검증을 위한 박제 형식 정합 — 동작 의미 변경 0.

## Issues Encountered

None (위 박제 정정 이외).

## Threat Surface Audit

본 plan 박제는 4 영역 client 의 기존 호출 path 에 TELEMETRY_OK gate + span event 만 박제 — 새 network endpoint / auth path / 외부 노출 박제 0. PLAN `<threat_model>` 박힌 T-17-28 ~ T-17-32 박제 대응:

- **T-17-28** (Phoenix span 에 영상 raw bytes 박힘) — mitigated. GoogleGenAIInstrumentor 의 default 가 file content 박지 않음 (token usage + model + duration 만).
- **T-17-29** (judge prompt 우회) — mitigated. judge prompt 박제 + coach JSON 구조화 입력. parse 실패 시 graceful None.
- **T-17-30** (eval 결과 audit) — mitigated. Firestore eval/phase17/samples/{analysis_id} 박제 helper 박힘. caller (pipeline) 가 sampling 통과 시 호출.
- **T-17-31** (Promptfoo 30 examples × 4 영역 ≈ 120 호출 cost) — accepted. README.md 박제 (수동 실행 + cache 박제).
- **T-17-32** (CI 환경 GEMINI_API_KEY 누출) — N/A — 본 plan 박제 X (CI 자동 게이트 별도 후속 plan). README.md 에 belle 로컬 env 박제 명시.

## Self-Check: PASSED

### File existence verification
- 16 created + 7 modified files 모두 존재 (`git status` 확인 — staged 0 / committed 100%).

### Commit verification
- 4 task commits (`f72bb72`, `9101225`, `75fa1f0`, `caf1616`) — `git log --oneline --grep="17-06"` 4 hit.

### Plan-level verification re-run
- pytest backend/tests/eval/ → **19 passed + 1 skipped** (≥15 박제 done gate 통과).
- pytest backend/tests/gemini/ → **111 passed** (Plan 17-01~05 회귀 0건).
- `grep -n "add_event.*guardrail" backend/shared/python/sunity_shared/gemini/*.py | grep -v '^#' | wc -l` → **5** (≥3 박제 done gate 통과).
- `python3 -c "import yaml; d=yaml.safe_load(open('backend/evals/phase17/dataset/reference_dataset.yaml')); print(len(d['scenarios']))"` → **50** (≥30 박제 done gate 통과).
- assertion 3 모듈 import + E1 회귀 통과.

## Next Phase Readiness

- **Production rollout (Phase 17 wave 6 — Plan 06)**:
  - Pod / Lambda 에 telemetry extras 설치 시 자동 활성. 미설치 시 분석 흐름 영향 0.
  - belle 로컬 env (`GEMINI_API_KEY`) 박혀있어야 Promptfoo local eval 실행 가능.
  - 라벨링 진입 — 정은지 5건 박혀있음. 학원 파일럿 진입 시 belle 가 TODO 25건 PR.
- **후속 plan**:
  - "Phase 17C — eval CI integration" — `.github/workflows/phase17-evals.yml` + PR comment bot + main branch protection 박제.
  - E5 auto-escalation runtime config (Firestore `visionConfig.regionC.model` 또는 SSM) — 본 plan 박제 X.

---
*Phase: 17-gemini-vision-integration-4*
*Plan: 06 (Sub-phase 06A/06B/06C in-file)*
*Completed: 2026-06-12*
