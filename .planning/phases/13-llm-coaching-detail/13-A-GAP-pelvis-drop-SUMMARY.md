---
phase: 13-llm-coaching-detail
plan: A-GAP-pelvis-drop
subsystem: api
tags: [corrective-exercises, exercise-mapping, force-signal-coverage, gap-closure, regression-guard]

# Dependency graph
requires:
  - phase: 13-llm-coaching-detail/A
    provides: corrective-exercise library + map_exercises + 3-way contract (the plan this gap-closes)
  - phase: 09-force-pattern
    provides: ForceSourceSignal (6 signals) — _FORCE_SOURCE_SIGNALS frozenset, joint_hint_for
provides:
  - glute_hip_unstable defect (pelvis_drop coverage) — closes the silent-miss gap
  - Durable ForceSourceSignal→defect coverage regression test (belle's standard guard)
affects: [13-B-llm-coaching, future force-signal additions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Coverage-guard test: every force_pattern ForceSourceSignal must map to >=1 corrective defect (motion-agnostic standard)"

key-files:
  created:
    - backend/tests/phase13/test_force_signal_exercise_coverage.py
  modified:
    - backend/data/corrective_exercises.json
    - app/src/data/corrective_exercises.json
    - backend/shared/python/sunity_shared/analysis/exercise_map.py
    - backend/tests/phase13/test_corrective_exercises_fixture.py
    - backend/tests/phase13/test_corrective_exercises_app_lockstep.py
    - app/src/data/correctiveExercises.ts

key-decisions:
  - "New defect glute_hip_unstable (not extend hip_hamstring_tight) — pelvis_drop = glute-medius/hip-abductor STABILITY deficit, domain-distinct from hip_hamstring_tight flexibility/tightness"
  - "jointHints include exact joint_hint_for(pelvis_drop) = '엉덩이 관절' so both signal-hit and hint-hit match paths fire"
  - "Exercise content sourced from NotebookLM e688fb4e [7] (중둔근/골반 안정화 cross-query) — no fabricated medical claims"
  - "Mapping stays motion-agnostic (keyed on force signals + joint hints, not per-motion) per belle's standard"

# Metrics
duration: ~25min
completed: 2026-06-16
---

# Phase 13 Plan A GAP: pelvis_drop Corrective Coverage Summary

**Phase 9 가 emit 할 수 있는 6 ForceSourceSignal 중 유일하게 보완운동 매핑이 없던 `pelvis_drop`(lateral pelvic drop = 중둔근/고관절 외전근 불안정)에 신규 `glute_hip_unstable` defect 를 추가해 silent miss 를 닫고, "모든 감지 가능한 실패 원인은 >=1 보완 동작에 매핑되어야 한다"는 belle 표준을 영속 회귀 테스트로 박제.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-16
- **Tasks:** RED regression test → GREEN fix (TDD)
- **Files:** 1 created + 6 modified

## The Gap (verified, then closed)

Phase 9 `force_pattern.py` can emit 6 `ForceSourceSignal`: `axis_tilt, pelvis_drop, late_contact, high_jitter, high_jerk, abnormal_release`. The corrective library had 5 defects and none covered `pelvis_drop`:
- `pelvis_drop` was in no defect's `triggers.sourceSignals`.
- `joint_hint_for("pelvis_drop")` = "엉덩이 관절", which did NOT substring-match any defect's `jointHints` under `_defect_keys_from_findings`'s rule (`h in joint_hint or joint_hint in h`) — "고관절" (hip_hamstring_tight) does not substring-match "엉덩이 관절".

Result: a real detected failure cause (lateral pelvic drop) produced ZERO corrective exercises. Now closed.

## Accomplishments

- **RED regression test** (`test_force_signal_exercise_coverage.py`): asserts every member of `force_pattern_copy.ForceSourceSignal` (lockstep-checked against `force_pattern._FORCE_SOURCE_SIGNALS`, all 6) maps to >=1 defect via `_defect_keys_from_findings`, using a synthetic finding (`sourceSignal` + `joint_hint_for(signal)`) per signal. Failed pre-fix on `pelvis_drop`, passes post-fix. Includes a lockstep sanity test (copy-module signal set == force_pattern frozenset) and a `pelvis_drop`-specific pin.
- **GREEN fix**: new `glute_hip_unstable` defect — `sourceSignals: [pelvis_drop]`, `jointHints: [둔근, 중둔근, 골반, 엉덩이 관절, 고관절 외전근]`, 5 exercises (Lateral Leg Raise, Plank with Leg Lift, Side Planks, Squats, Lunges) sourced from NotebookLM `e688fb4e` [7].
- **Lockstep contracts honored**: backend + app `corrective_exercises.json` updated byte-identically (`cp`), full-content deep-equal lockstep passes. `_DEFECT_KEYS` frozenset + both test key-sets + TS `DEFECT_TITLES` (`glute_hip_unstable: '둔근·골반 안정화'`) extended. `npm run typecheck` clean.
- **D-05 hard wall intact**: `test_exercise_map_no_scoring_leak.py` still passes (no scoring tokens added to `exercise_map.py`); painAreas never enter any scoring path.

## Task Commits

1. **RED — ForceSourceSignal coverage regression** - `7bde2de` (test)
2. **GREEN — glute_hip_unstable defect closes pelvis_drop gap** - `6431d64` (feat)

## Decisions Made

- **New defect, not an extension.** `pelvis_drop` (Trendelenburg-type lateral pelvic drop) is a glute-medius / hip-abductor STABILITY+strength deficit — domain-distinct from `hip_hamstring_tight` (flexibility/tightness). A separate `glute_hip_unstable` defect is the domain-correct mapping and keeps the library readable; extending the flexibility defect with stability exercises would conflate two different physio targets.
- **Exact joint-hint inclusion.** Added the literal `joint_hint_for("pelvis_drop")` value ("엉덩이 관절") to `jointHints` so both the `sourceSignal` and `jointHint` match paths fire — defense in depth against either input field being absent.
- **NotebookLM-sourced content.** Cross-queried the project's corrective-exercise notebook (`e688fb4e`) for 중둔근/골반 안정화 운동; content is from the polesports knowledge sources. No fabricated medical claims; every exercise carries `sourceRef "NotebookLM e688fb4e [7]"`.
- **Motion-agnostic.** Mapping remains keyed on force signals + joint hints, not per-motion, per belle's 2026-06-16 standard ("새 영상이 들어와도 동작은 동작").

## Deviations from Plan

- The objective referenced `_FORCE_SOURCE_SIGNALS` as living in `force_pattern_copy.py`; it actually lives in `force_pattern.py`, while `force_pattern_copy.py` exposes the equivalent `ForceSourceSignal` Literal. The regression test uses `typing.get_args(ForceSourceSignal)` from the copy module (the copy-module-local source) and adds a lockstep assertion that this set equals `force_pattern._FORCE_SOURCE_SIGNALS`. Same 6-signal guarantee, no weaker. [Rule 3 - blocking import resolved]

## Known Stubs

None. The new defect is fully populated (5 exercises, real triggers) and wired through the same `map_exercises` path; `glute_hip_unstable` now returns exercises for any `pelvis_drop` finding.

## Issues Encountered

- **Pre-existing out-of-scope failures (NOT caused by this change):** `cd backend && pytest -q` shows collection errors (missing heavy/optional deps: `fixtures`, `google.genai`, mediapipe/rtmpose spike tests) and phase06 failures (`ModuleNotFoundError: No module named 'google'`) plus the phase08 gemini-EOL test already logged in 13-A's deferred-items. Verified by stashing this change and re-running a representative phase06 test — it fails identically on the clean tree. None of the modules I touched are imported by those tests. Per SCOPE BOUNDARY, not fixed. The relevant in-scope suite `tests/phase13` = 33 passed.

## Verification

- `cd backend && .venv/bin/pytest tests/phase13 -q` → 33 passed
- `cd backend && .venv/bin/pytest tests/phase13/test_force_signal_exercise_coverage.py -q` → 3 passed (fails pre-fix)
- `cd backend && .venv/bin/pytest tests/phase13/test_exercise_map_no_scoring_leak.py -q` → 1 passed (D-05 intact)
- `cd app && npm run typecheck` → clean
- backend/app `corrective_exercises.json` byte-identical (`diff` clean)

## Self-Check: PASSED

- Created file exists: `backend/tests/phase13/test_force_signal_exercise_coverage.py` FOUND.
- Commits present: `7bde2de` (test RED), `6431d64` (feat GREEN) FOUND in git history.

---
*Phase: 13-llm-coaching-detail*
*Gap-closure on already-complete plan 13-A (ROADMAP 13-A status unchanged: [x])*
*Completed: 2026-06-16*
