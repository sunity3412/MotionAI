---
phase: 13-llm-coaching-detail
plan: A
subsystem: api
tags: [corrective-exercises, exercise-mapping, firestore, react-native, 3-way-contract, pers-03]

# Dependency graph
requires:
  - phase: 09-force-pattern
    provides: forcePatternInference.findings[] (sourceSignal + jointHint) — exercise mapping input
  - phase: 03-body-profile
    provides: bodyProfile.painAreas snapshot (PAIN_AREAS frozenset) — exercise mapping input
provides:
  - Committed corrective exercise library fixture (5 defect + 8 painArea keys, NotebookLM e688fb4e)
  - Pure map_exercises(force_pattern_inference, pain_areas, motion_id) -> list[dict] (3~5 cap, dedup)
  - 3-way contract field recommendedExercises (analysis.ts + models.py + contract.md §4)
  - Firestore _validate_recommended_exercises scoped validator + complete_analysis wiring
  - App-side byte-copy mirror (corrective_exercises.json + correctiveExercises.ts typed wrapper)
  - result.tsx 보완 운동 section + RecommendedExerciseModal full-library browse
affects: [13-B-llm-coaching, future-pers-04-fitness-norms]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure mapping fn mirrors force_pattern.py (numpy/AWS-free, lazy fixture cache, frozenset validators)"
    - "Scoped Firestore validator (_validate_recommended_exercises) mirrors _validate_force_pattern_inference — nested-array ban preserved"
    - "App data mirror = backend JSON byte-copy + typed wrapper + full-content deep-equal lockstep test (HIGH-2)"

key-files:
  created:
    - backend/data/corrective_exercises.json
    - backend/shared/python/sunity_shared/analysis/exercise_map.py
    - app/src/data/corrective_exercises.json
    - app/src/data/correctiveExercises.ts
    - app/src/components/RecommendedExerciseModal.tsx
    - backend/tests/phase13/ (infra + 5 test files)
  modified:
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/shared/python/sunity_shared/models.py
    - app/src/types/analysis.ts
    - app/src/lib/userAnalyses.ts
    - app/src/app/analysis/result.tsx
    - app/tsconfig.json
    - docs/contract.md

key-decisions:
  - "Exercise content verbatim from RESEARCH §B (NotebookLM e688fb4e) — no fabrication, sourceRef on every item"
  - "painAreas consumed for exercise mapping ONLY (D-05) — map_exercises receives no scoring values; grep gate enforces"
  - "App mirror is byte-copy of backend canonical JSON (HIGH-2) — deep-equal lockstep, not name-set smoke check"
  - "보완 운동 section visible if recommendations exist OR library non-empty (MEDIUM-1) — browse entry never disappears"

patterns-established:
  - "Corrective library as committed fixture (aka-mapping.json convention) loaded by pure code"
  - "resolveJsonModule enabled for JSON byte-copy import in TS"

requirements-completed: [PERS-03]

# Metrics
duration: ~45min
completed: 2026-06-16
---

# Phase 13 Plan A: Corrective Exercises Summary

**분석 실패 원인 후보 + 통증부위를 결함/통증부위별 보완 운동 3~5개로 매핑하는 순수 함수 + 3-way 계약 필드 recommendedExercises + 결과 화면 보완 운동 섹션과 전체 라이브러리 "다른 운동 보기" 모달 (app JSON byte-copy mirror).**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-06-16
- **Tasks:** 3
- **Files modified:** 8 modified + 11 created (incl. tests)

## Accomplishments

- Corrective exercise library fixture: 5 defect keys (grip_weak/shoulder_unstable/core_weak/legs_not_extended/hip_hamstring_tight) + 8 painArea keys (= models.PAIN_AREAS), each exercise cites NotebookLM e688fb4e source.
- Pure `map_exercises(force_pattern_inference, pain_areas, motion_id)` — joins findings sourceSignal/jointHint to defect keys + painAreas to painArea keys, painArea-avoid exercises prioritized, name dedup, 3~5 cap, graceful None/empty. D-05 hardwall: no scoring values in, grep gate verifies no scoring-path tokens.
- 3-way contract `recommendedExercises` added atomically to analysis.ts (RecommendedExercise interface), models.py (RECOMMENDED_EXERCISE_KEYS + MAX_RECOMMENDED_EXERCISES), docs/contract.md §4. Scoped Firestore validator `_validate_recommended_exercises` (len<=5 cap + flat scalar — nested-array ban preserved) + complete_analysis kwarg wiring.
- Pipeline calls map_exercises after force_pattern_inference_dict build, consuming only painAreas (D-05, weightKg never enters scoring path).
- App data path: `app/src/data/corrective_exercises.json` is a byte-for-byte copy of the backend fixture (HIGH-2), imported by `correctiveExercises.ts` typed wrapper (resolveJsonModule enabled). RecommendedExerciseModal browses the full library; result.tsx 보완 운동 section keeps the browse entry even with empty recommendations (MEDIUM-1).

## Task Commits

1. **Task 1: 라이브러리 fixture + phase13 test 인프라 + 스키마 게이트** - `3068a7c` (feat)
2. **Task 2: 순수 map_exercises 매핑 함수 + D-05 비유입 게이트** - `0e9302a` (test, RED) → `c89b670` (feat, GREEN)
3. **Task 3: 3-way 계약 + validator + pipeline wiring + frontend + app mirror** - `1580a6f` (feat)

**Deferred log:** `0f1197e` (docs: out-of-scope phase08 gemini test note)

## Files Created/Modified

- `backend/data/corrective_exercises.json` - Corrective exercise library fixture (5 defect + 8 painArea, NotebookLM content)
- `backend/shared/python/sunity_shared/analysis/exercise_map.py` - Pure map_exercises mapping function
- `backend/shared/python/sunity_shared/firestore_admin.py` - _validate_recommended_exercises + complete_analysis kwarg
- `backend/shared/python/sunity_shared/models.py` - recommendedExercises contract comment + RECOMMENDED_EXERCISE_KEYS/MAX
- `backend/functions/pipeline/app.py` - map_exercises call (painAreas only) + complete_analysis wiring
- `docs/contract.md` - §4 recommendedExercises field + RecommendedExercise shape block
- `app/src/types/analysis.ts` - RecommendedExercise interface + AnalysisResult.recommendedExercises
- `app/src/lib/userAnalyses.ts` - normalize() recommendedExercises null-guard
- `app/src/data/corrective_exercises.json` - byte-copy of backend fixture
- `app/src/data/correctiveExercises.ts` - typed wrapper + browse sections helper
- `app/src/components/RecommendedExerciseModal.tsx` - full-library browse modal
- `app/src/app/analysis/result.tsx` - 보완 운동 section + modal mount + styles
- `app/tsconfig.json` - resolveJsonModule: true
- `backend/tests/phase13/` - __init__/conftest + fixture + 5 test files

## Decisions Made

- Exercise content taken verbatim from RESEARCH §B (NotebookLM e688fb4e) tables; every exercise has a sourceRef citing the notebook — no fabricated content (analysis-objectivity).
- App mirror is the byte-copy of the backend canonical JSON (HIGH-2 option BEST), enforced by full-content deep-equal lockstep test, not a name-set smoke check.
- 보완 운동 section visibility = recommendations exist OR library non-empty (MEDIUM-1): the "전체 보완 운동 보기" entry never disappears even when personalization is empty.

## Deviations from Plan

None - plan executed exactly as written. The plan's prescribed file list, schema, validator pattern, and UI structure were followed directly. One docstring rephrase in exercise_map.py (replacing the literal token `dimension_scores` with "차원 채점 값") was needed so the D-05 grep gate stays strict and meaningful — this is consistent with the plan's intent (the gate must catch real scoring-path references, not its own explanatory prose).

## Issues Encountered

- **Pre-existing out-of-scope test failure:** `backend/tests/phase08/test_gemini_model_env_driven.py::test_gemini_moment_extractor_default_is_non_eol` fails on the base commit (Gemini moment-extractor default `gemini-2.5-pro` set by quick-task 260615-cxe vs the test's non-EOL assertion). Not related to Plan 13-A (no Gemini model edits here). Logged in `deferred-items.md`, not fixed per SCOPE BOUNDARY. All phase13 tests (30) pass; phases 06/07/08/08.1/09/12 = 645 passed, 1 skipped, with this single pre-existing failure unchanged.

## Known Stubs

None. The corrective library fixture is fully populated; map_exercises wires real data end-to-end into result.recommendedExercises and the full-library modal.

## Next Phase Readiness

- Plan 13-B (LLM coaching / motion branch routing) can proceed independently (depends_on: []).
- recommendedExercises now flows pipeline → Firestore → app result screen. Real values appear once a pipeline analysis runs (GPU Pod); the full-library modal is always available regardless of analysis output.

---
*Phase: 13-llm-coaching-detail*
*Completed: 2026-06-16*
