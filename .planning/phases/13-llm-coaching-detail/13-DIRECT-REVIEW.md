---
phase: 13-llm-coaching-detail
reviewer: Codex
date: 2026-06-16
scope: direct-plan-review
status: revise-before-execution
reviewed_plans:
  - 13-CONTEXT.md
  - 13-RESEARCH.md
  - 13-PATTERNS.md
  - 13-VALIDATION.md
  - 13-A-corrective-exercises-PLAN.md
  - 13-B-llm-branch-copy-PLAN.md
  - 13-PLAN-CHECK.md
local_code_checked:
  - backend/data/aka-mapping.json
  - backend/data/reference-motions-branch2.json
  - backend/judging_data/criteria/ref-foxtop.yaml
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - backend/shared/python/sunity_shared/analysis/coach_writer.py
  - backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py
  - backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/shared/python/sunity_shared/models.py
  - backend/functions/pipeline/app.py
---

# Phase 13 Direct Plan Review

## Verdict

Phase 13 is mostly well-shaped: the A/B split is right, D-05 is treated seriously, `recommendedExercises` has the correct scoped-validator strategy, and criteria 5 is honestly kept as a Pod/Cerebras checkpoint instead of being overclaimed by unit tests.

I would still revise before execution. There are two material gaps:

1. Plan B assumes `aka-mapping.json` can produce `motion_id -> ipsfCode`, but current production `TechniqueProfile.motion_id` values are `ref-*` reference ids and `aka-mapping.json` has no `motionId`. Without an explicit join fixture, criteria 6/7 can silently fall back to old copy.
2. Plan A says the "다른 운동 보기" modal browses the full exercise library, but the app only receives `result.recommendedExercises` 3-5 items and no app-readable full-library data source is planned.

Fix those before execution. The rest can proceed with smaller wording/test improvements.

## Narrow Gate Review

| Gate | Verdict | Notes |
|------|---------|-------|
| criteria 7 registered IPSF angles | PARTIAL | The blocking human checkpoint is correct. Do not lock NotebookLM-synthesized angles without belle/NotebookLM recheck. Also do not let generic "180°" copy override non-180 fixture targets. |
| 3-way contract + Firestore nested-array | PASS | `recommendedExercises` is plain camelCase scalar dict, and Plan A T3 adds a scoped validator before writing to `result.recommendedExercises`. This is the right pattern. |
| D-05 painAreas boundary | PASS | `painAreas` flows into exercise mapping and coach context only. Scoring inputs stay clean, and the grep/AST gate is appropriate. |
| criteria 5 Pod dependency | PASS | Real video -> real Cerebras -> Firestore `tip.detail2` requires Pod/env/SSM. Keeping it as a blocking human checkpoint is appropriate. |

## Findings

### BLOCKER-1: `motion_ipsf_map.json` cannot be derived from current data as specified

Plan B Task 2 says to create `backend/data/motion_ipsf_map.json` from `aka-mapping.json + reference-motions-branch2.json`, keyed by `motion_id`.

Evidence:
- `13-B-llm-branch-copy-PLAN.md:109-116` says `motion_ipsf_map.json` is keyed by `"<motion_id>"` and looked up by `profile.motion_id`.
- `backend/data/aka-mapping.json:9-18` entries have `studioName`, aliases, `ipsfCode`, and `isRegistered`, but no `motionId`.
- `backend/data/reference-motions-branch2.json:10-16` has `motionId: "ref-foxtop"` for branch 2, but only for branch 2.
- `gemini_motion_classifier.py:20-29` defines the current recognized scope as `ref-climb`, `ref-foxtop`, `ref-foxtop-split`, `ref-invert`, `ref-sideway-spin`.
- `gemini_technique_recognizer.py:312-320` stores the canonical `ref-*` value as `TechniqueProfile.motion_id`.

Risk:
- Branch 2 `ref-foxtop` can map, but branch 1 cannot reliably map from the 13 AKA entries because there is no shared key.
- `is_registered` may be `None` for real analyses, so `build_dimension_explanation` preserves old mode-aware copy instead of criteria 6 branch copy.
- Tests can pass if they call `build_dimension_explanation(..., is_registered=True)` directly, while pipeline wiring never supplies `True`.

Required plan patch:
- Make `motion_ipsf_map.json` an explicit curated join table, not "derived" from `aka-mapping.json`.
- Include every production `REGISTERED_MOTIONS` id with a deliberate branch decision:
  - `ref-foxtop`: branch2, `isRegistered:false`, `ipsfCode:null`
  - `ref-foxtop-split`, `ref-invert`, `ref-climb`, `ref-sideway-spin`: explicit branch1/branch2/unknown decisions, with source notes
- Add a test that iterates `REGISTERED_MOTIONS` and asserts each recognized `motion_id` has a `motion_ipsf_map` entry or a deliberate `isRegistered:null` fallback reason.
- For future AKA-only ids, add explicit `motionId` to `aka-mapping.json` or a separate alias-to-motion table; do not infer it from display names during execution.

### HIGH-1: "다른 운동 보기" has no app-side full-library data source

Plan A stores 3-5 matched exercises in Firestore and says the modal browses the full library.

Evidence:
- `13-A-corrective-exercises-PLAN.md:29-31` requires 3-5 result exercises and full-library modal browsing.
- `13-A-corrective-exercises-PLAN.md:160-166` adds `recommendedExercises?: RecommendedExercise[]` and a `RecommendedExerciseModal`, but no `app/src/data/*` fixture, API, or `allExercises` result field.
- `backend/data/corrective_exercises.json` is a backend fixture; React Native cannot assume runtime access to that backend file.

Risk:
- The modal can only show the same 3-5 `recommendedExercises`, so criteria 4 is not actually delivered.
- A late implementation may duplicate content ad hoc in the component, creating contract drift from the backend fixture.

Recommended patch:
- Choose one explicit data path:
  - Add `app/src/data/correctiveExercises.ts` generated or manually mirrored from the backend fixture, with a lockstep test comparing schema/version, or
  - Store a small `exerciseAlternates` / `recommendedExerciseCandidates` scalar list in Firestore if product wants personalized alternates, or
  - Narrow criteria 4 to "recommended exercise detail modal" and stop claiming full-library browsing.
- If keeping full-library browse, add the app data file to Plan A frontmatter, tests, and acceptance criteria.

### HIGH-2: Plan B does not fully lock the `build_result -> build_dimension_explanation` wiring

Plan B Task 2 adds kwargs to `build_dimension_explanation`, and Task 3 says pipeline will pass branch data through `build_result`. But `build_result` is the function that actually calls `build_dimension_explanation`, and Task 3's file list does not include `assemble.py`.

Evidence:
- `assemble.py:271-282` current `build_result` signature has no `ipsf_code` / `is_registered`.
- `assemble.py:317-323` calls `build_dimension_explanation(...)` internally.
- `pipeline/app.py:1862-1876` calls `assemble.build_result(...)`.
- `13-B-llm-branch-copy-PLAN.md:142-145` says to wire branch data through `build_result/assemble`, but Task 3 files only list `coach_writer.py`, `app.py`, and `test_coach_prompt_angle_fixture.py`.

Risk:
- Implementer may pass `ipsf_code` to `build_result` and get a runtime `TypeError`.
- Or they may only update `build_dimension_explanation` unit tests and forget the production `build_result` pass-through.

Required patch:
- In Plan B Task 2 or Task 3, explicitly modify `assemble.build_result(..., ipsf_code=None, is_registered=None)` and forward those kwargs into `build_dimension_explanation`.
- Add a test that calls `assemble.build_result(..., is_registered=False)` and verifies `result["dimensionExplanation"]` gets branch-2 copy. Directly testing `build_dimension_explanation` is not enough.

### HIGH-3: Criteria 7 fixture can be bypassed by generic branch-1 "180°" baseline copy

The checkpoint for registered move angles is good, but Plan B's branch-1 baseline and tests over-focus on the string "180°".

Evidence:
- `13-B-llm-branch-copy-PLAN.md:88-96` correctly blocks fixture lock until ambiguous angles are verified.
- `13-B-llm-branch-copy-PLAN.md:112-118` then says registered branch baseline should include "세계 심사 기준" and "180°", and the test only asserts those substrings.
- RESEARCH itself flags non-180 examples such as Ayesha top shoulder 110° and top elbow 20-30°.

Risk:
- The plan may pass criteria 6 tests while still teaching the LLM/UI that every registered angle is a 180° extension target.
- That contradicts the criteria 7 goal: cite the correct per-move, per-joint definition angles.

Recommended patch:
- Split branch-1 baseline by dimension:
  - angle: "IPSF 동작별 정의 각도"
  - line: "IPSF 신전 기준, 해당 동작에서 EXTEND인 팔꿈치/무릎은 180°"
  - stability: "hold 구간 안정성"
- Add a test fixture with at least one non-180 registered angle and assert the prompt includes that value without replacing it with 180.
- Keep "180°" as a line/extension copy only, not universal angle copy.

### WARNING-1: Branch-2 criteria yaml path is ambiguous

Plan B Task 3 says `angle_fixture = ... ref-{motion_id}.yaml` for branch 2.

Evidence:
- Current branch-2 motion id is already `ref-foxtop`.
- The actual file is `backend/judging_data/criteria/ref-foxtop.yaml`.

Risk:
- A literal `ref-{motion_id}.yaml` implementation would try `ref-ref-foxtop.yaml`.

Recommended patch:
- Specify a helper: `criteria_path = criteria_dir / f"{motion_id}.yaml"` when `motion_id.startswith("ref-")`; never prepend another `ref-`.
- Add a branch-2 test that uses real `motion_id="ref-foxtop"` and confirms measured angles are loaded from `criteria/ref-foxtop.yaml`.

### WARNING-2: Plan B Task 3 verify command has a bad second `cd backend`

Evidence:
- `13-B-llm-branch-copy-PLAN.md:147-149` uses `cd backend && pytest ... && cd backend && pytest ...`.

Risk:
- After the first `cd backend`, the second `cd backend` tries to enter `backend/backend` and fails.

Patch:
- Replace with:
  - `cd backend && python -m pytest tests/phase13/test_coach_prompt_angle_fixture.py -x -q && python -m pytest tests/phase13 -q`

## What Looks Strong

- Plan A's `recommendedExercises` Firestore shape is correctly kept as list-of-flat-scalar dicts, with a scoped validator preserving the project-wide nested-array rule.
- Plan A's D-05 guard is meaningful: `map_exercises()` does not accept `dimension_scores`, and the grep/AST gate watches for scoring-token drift.
- Plan B's criteria 5 checkpoint is correctly non-autonomous and operational. Pod + SSM + uvicorn restart are real prerequisites.
- Plan B's branch-2 forbidden-phrase gate is the right kind of narrow test: it directly protects the user-visible copy problem from Phase 12.5.

## Final Recommendation

Do not execute Phase 13 exactly as written. Patch the two blockers/high-risk data-flow issues first:

1. Add an explicit production `motion_id -> branch/ipsfCode` join contract and tests over current `REGISTERED_MOTIONS`.
2. Decide how the app gets the full corrective exercise library for "다른 운동 보기".
3. Add `build_result` branch pass-through tests.
4. Tighten criteria 7 so per-joint fixture angles can override generic 180° copy.

After those patches, the phase is execution-ready.
