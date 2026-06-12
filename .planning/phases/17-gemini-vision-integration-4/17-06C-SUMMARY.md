---
phase: 17-gemini-vision-integration-4
plan: 06C
subsystem: eval
tags: [promptfoo, local-eval, dataset, assertion, ipsf]

requires:
  - phase: 17-gemini-vision-integration-4
    provides: "Sub-phase 06A (Phoenix bootstrap) + 06B (4 영역 span + LLM judge + sampling)"
provides:
  - "Promptfoo local eval config (수동 실행 — CI 자동 게이트는 별도 후속 plan, W6 정합)"
  - "30-entry reference dataset (정은지 5건 labeled + 나머지 25건 TODO)"
  - "External assertion script 3개 (E1 객관성 / E2-E3 IPSF routing / E4 coach tone)"
  - "belle 실행 절차 README (CI 자동 게이트 별도 plan 박제 명시)"
affects: [phase-17-rollout, phase-17-eval-ci-integration-future]

tech-stack:
  added:
    - promptfoo (npm — 수동 설치)
  patterns:
    - "Local eval 박제 패턴 — config / dataset / assertion 코드만 박고 CI 자동화는 별도 plan. PR pre-merge auto-block 표현 박제 0건 (W6 정합)."
    - "Custom Python provider 박제 — Promptfoo 가 child process 로 sunity_shared.gemini.* 호출 위임."
    - "External assertion (self-contained Python) — Promptfoo eval 환경이 sunity_shared layer 가용성 보장 박제 X 라 별도 패키지로 분리."

key-files:
  created:
    - backend/evals/phase17/promptfooconfig.yaml
    - backend/evals/phase17/README.md
    - backend/evals/phase17/dataset/reference_dataset.yaml
    - backend/evals/phase17/dataset/labels.json
    - backend/evals/phase17/assertions/__init__.py
    - backend/evals/phase17/assertions/objectivity_reject.py
    - backend/evals/phase17/assertions/ipsf_routing.py
    - backend/evals/phase17/assertions/coach_tone.py
  modified: []

key-decisions:
  - "W6 (2차 R) 정합 박제 — 본 plan = local eval (belle 수동 실행). PR pre-merge 자동 block 표현 박제 0건. CI 자동 게이트는 별도 후속 plan ('Phase 17C — eval CI integration')."
  - "Dataset entry 박제 50개 — plan done gate ≥30 박제, AI-SPEC §5 매트릭스 (영역 A 10 + B 10 + C 20 + D 10) 박제."
  - "정은지 5건 label_status=labeled (Plan 12 referenceKeypointReport 재사용) + 25건 TODO (학원 파일럿 진입 시 belle PR 박제)."
  - "Assertion script 가 sunity_shared 와 분리된 self-contained Python — Promptfoo eval 환경의 PYTHONPATH 의존성 박제 회피."

patterns-established:
  - "Local eval 박제 → CI 자동 게이트 박제 separation 패턴 — 본 plan 박제는 코드 (config/dataset/assertion) 만, runtime 자동화 박제는 별도 plan."

requirements-completed:
  - VISION-01
  - VISION-02
  - VISION-03
  - VISION-04

duration: 6 min
completed: 2026-06-12
---

# Phase 17 Plan 06C: Promptfoo local eval config + dataset + assertion Summary

**Promptfoo local eval config (belle 수동 실행) + 50-entry reference dataset (정은지 5건 labeled + 25건 TODO) + 3개 self-contained Python assertion (E1 객관성/E2-E3 IPSF routing/E4 coach tone) + README 박제 — W6 정합 PR auto-block 표현 0건.**

## Performance

- **Duration:** 6 min (Sub-phase 06C 단독)
- **Started:** 2026-06-12T03:25:00Z
- **Completed:** 2026-06-12T03:31:00Z
- **Tasks:** 1 (Task 3)
- **Files modified:** 8

## Accomplishments

- `backend/evals/phase17/promptfooconfig.yaml` — custom Python provider 4개 (region A/B/C/D) + external assertion 3개 박제. 임계값 박제 (E1=100% / E2=90% / E3=90% / E4=85% / E5=95% / E6=100% / E7=90% / E8 latency p95).
- `dataset/reference_dataset.yaml` — 50 entry (영역 A 10 + B 10 + C 20 + D 10).
- `dataset/labels.json` — 정은지 5건 labeled + 25건 TODO 박제.
- `assertions/objectivity_reject.py` — AI-SPEC §6 G1 reject regex (점수/좌표/판단). region D 좌표 우회.
- `assertions/ipsf_routing.py` — E2/E3 IPSF 명칭 + routing_branch 매치 (partial match score 0.5).
- `assertions/coach_tone.py` — E4 강사 보조 톤 (부위별 용어 14 + 강사/함께/확인 3 어휘 + blocklist 4 패턴).
- `README.md` — belle 실행 절차 + 임계값 표 + **"CI 자동 게이트 별도 plan"** 명시 박제.

## Task Commits

1. **Task 3 (Sub-phase 06C): Promptfoo local eval config + 30 entry dataset + assertion 3** — `caf1616` (feat)

## Files Created/Modified

- `backend/evals/phase17/promptfooconfig.yaml` — Promptfoo config 본체.
- `backend/evals/phase17/README.md` — 실행 절차 + 임계값 표.
- `backend/evals/phase17/dataset/reference_dataset.yaml` — 50 entry.
- `backend/evals/phase17/dataset/labels.json` — 라벨링 sheet.
- `backend/evals/phase17/assertions/objectivity_reject.py` — E1.
- `backend/evals/phase17/assertions/ipsf_routing.py` — E2/E3.
- `backend/evals/phase17/assertions/coach_tone.py` — E4.

## Decisions Made

- W6 (2차 R) 정합 박제 — 본 plan = **local eval**. CI 자동 게이트 (.github/workflows/phase17-evals.yml) 는 별도 후속 plan. PR pre-merge 자동 block 표현 박제 0건.
- Dataset entry 50 박제 — done gate ≥30 박제. 영역 매트릭스 박제 (영역 A 10 + B 10 + C 20 + D 10).
- 정은지 5건 label_status=labeled + Plan 12 referenceKeypointReport 재사용 박제 (소스 명시).
- Assertion script self-contained Python — Promptfoo eval 환경의 sunity_shared 가용성 박제 회피. AI-SPEC §6 G1 reject regex 박제는 sunity_shared.gemini.guardrails 와 동일 패턴 mirror (manual sync 박제).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- belle 수동 실행 가능 — `cd backend/evals/phase17 && promptfoo eval --config promptfooconfig.yaml`.
- 후속 plan 박제 — "Phase 17C — eval CI integration" (`.github/workflows/phase17-evals.yml` + PR comment bot + main branch protection).
- 라벨링 진입 — 학원 파일럿 시 belle 가 TODO 25건 PR 박제.

---
*Phase: 17-gemini-vision-integration-4*
*Sub-phase: 06C*
*Completed: 2026-06-12*
