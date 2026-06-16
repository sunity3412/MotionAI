---
phase: 13-llm-coaching-detail
review: direct-codex-iteration-3
reviewed_at: 2026-06-16
status: revise-before-execution
plans_reviewed:
  - 13-A-corrective-exercises-PLAN.md
  - 13-B-llm-branch-copy-PLAN.md
  - 13-REVIEW-FIXES.md
  - 13-RESEARCH.md
  - 13-PATTERNS.md
  - 13-PLAN-CHECK.md
---

# Phase 13 Direct Review — Iteration 3

## Verdict

The core architecture has converged. Iteration 2's major risks are mostly closed:

- Plan B now uses `copyBranch + angleSource + angleFixtureKey` instead of an overloaded `isRegistered` boolean.
- `motion_ipsf_map.json` is now explicitly curated, not derived from `aka-mapping.json`.
- `registered_move_angles.json` has an `angleFixtureKey` contract.
- Plan A now uses an app-side JSON mirror plus a typed wrapper for the full-library modal.
- Empty personalized recommendations no longer remove the browse entry point.

I would still revise before execution. The remaining problems are smaller than the previous blockers, but they are exactly the kind that can make an executor write failing tests or reintroduce a stale implementation path.

## Findings

### HIGH-1: `angleFixtureKey` is both required and nullable for `no_angle_criterion`

Plan B correctly models `ref-climb` as `angleSource=no_angle_criterion` with no angle fixture, but several contract lines still say every current `REGISTERED_MOTIONS` entry must have `angleFixtureKey`.

Evidence:

- `13-B-llm-branch-copy-PLAN.md:35` says every current motion has `non-unknown copyBranch + angleSource + angleFixtureKey + non-empty sourceNote`.
- `13-B-llm-branch-copy-PLAN.md:130` assigns `ref-climb` `angleFixtureKey=null`, `criteriaYaml=null`.
- `13-B-llm-branch-copy-PLAN.md:146-147` correctly says `no_angle` allows null.
- `13-B-llm-branch-copy-PLAN.md:156` repeats that all five ids have `angleFixtureKey`.
- `13-REVIEW-FIXES.md:71` says every entry has `angleFixtureKey`, then `13-REVIEW-FIXES.md:74` treats `no_angle_criterion` as fixture-less.
- The code fixture confirms why null is correct: `backend/judging_data/criteria/ref-climb.yaml:8-21` says climbs have no anatomical angle target, and `hold_moment` is intentionally empty at `ref-climb.yaml:25-27`.

Risk:

- A test writer may assert `angleFixtureKey is not None` for all five current motions, forcing a fake key for `ref-climb`.
- A future implementation may put `ref-climb` into `registered_move_angles.json` just to satisfy the non-null wording, which would violate the no-fake-angle gate.

How I would fix it:

- Change every "all ids have angleFixtureKey" line to: every entry has the `angleFixtureKey` field; it is non-null only for `ipsf_registered_fixture` and `eunji_measured_yaml`; it must be null for `no_angle_criterion`.
- Update Plan B acceptance line 156 to:
  `motion_ipsf_map.json covers all 5 ids; each has non-unknown copyBranch, angleSource, sourceNote; angleFixtureKey is required for ipsf_registered_fixture/eunji_measured_yaml and null for no_angle_criterion.`
- Update `13-REVIEW-FIXES.md:71` with the same nullable-field wording.

### HIGH-2: app JSON import requires `resolveJsonModule`, but `app/tsconfig.json` is not in Plan A's modified-file set

Plan A now uses `app/src/data/correctiveExercises.ts` to import `./corrective_exercises.json`. That is the right data-source fix, but the current app tsconfig does not enable JSON imports.

Evidence:

- `app/tsconfig.json:1-5` only sets `"strict": true`; there is no `resolveJsonModule`.
- Plan A lists `app/src/data/corrective_exercises.json` and `app/src/data/correctiveExercises.ts` in `files_modified` at `13-A-corrective-exercises-PLAN.md:16-17`.
- Plan A says `resolveJsonModule` must be enabled if absent at `13-A-corrective-exercises-PLAN.md:189`.
- But `app/tsconfig.json` is not listed in Plan A `files_modified` (`13-A-corrective-exercises-PLAN.md:7-27`) or acceptance criteria (`13-A-corrective-exercises-PLAN.md:199-208`).

Risk:

- The executor may create the JSON wrapper but skip `tsconfig.json` because it is not in the planned file set.
- `npm run typecheck` should catch this, but it turns a planned implementation into an avoidable failure loop.

How I would fix it:

- Add `app/tsconfig.json` to Plan A `files_modified`.
- Add an acceptance criterion: `app/tsconfig.json enables resolveJsonModule for corrective_exercises.json import`.
- Keep `npm run typecheck` as the final guard.

### MEDIUM-1: `13-PATTERNS.md` and `13-PLAN-CHECK.md` still preserve the old `is_registered` route

The plans and `13-REVIEW-FIXES.md` now supersede this, but stale pattern docs remain in the execution context.

Evidence:

- `13-PATTERNS.md:31` still describes `assemble.py` as `ipsf_code` / `is_registered` kwargs.
- `13-PATTERNS.md:225-234` still shows `build_dimension_explanation(..., ipsf_code, is_registered)` and branches on `is_registered is True/False/None`.
- `13-PLAN-CHECK.md:21` still says "build_dimension_explanation is_registered branch".
- Plan A/B read `13-REVIEW-FIXES.md` first inside each task, which reduces the risk, but both plan context blocks still include `13-PATTERNS.md`.

Risk:

- An executor using `PATTERNS.md` as the implementation analog can resurrect `lookup_motion_ipsf` or `is_registered` even though the plan action says not to.
- This is especially risky because the stale pattern looks like concrete code guidance.

How I would fix it:

- Add a top-of-file supersession note to `13-PATTERNS.md`, mirroring `13-RESEARCH.md:4`, saying the branch-copy section is superseded by `13-REVIEW-FIXES.md`.
- Better: patch `13-PATTERNS.md:225-234` to show `branch_info: MotionBranchInfo | None = None` and `lookup_motion_branch`.
- Patch `13-PLAN-CHECK.md:21` from `is_registered branch` to `copyBranch branch_info`.

### MEDIUM-2: `MotionBranchInfo` is described as dict-or-dataclass, but call sites use attribute style

Plan B says `MotionBranchInfo` can be a dict or dataclass, but later examples use `branch_info.copyBranch`. That is fine for a dataclass, but not for a plain dict.

Evidence:

- `13-REVIEW-FIXES.md:35` says `MotionBranchInfo` can be a dict or dataclass.
- `13-B-llm-branch-copy-PLAN.md:137-142` describes branch selection as `branch_info.copyBranch`.
- `13-B-llm-branch-copy-PLAN.md:185` says the same richer object is shared into `app.py`, `_build_coach_context`, and `assemble.build_result`.

Risk:

- One executor may implement a plain dict and another may write attribute-style consumers.
- This would fail quickly in tests, but it is easy to avoid in the contract.

How I would fix it:

- Pick one representation in the plan.
- My preference: use a small frozen dataclass in `assemble.py` or a nearby fixture helper:
  `MotionBranchInfo(copyBranch: str, ipsfCode: str | None, officialName: str, angleSource: str, angleFixtureKey: str | None, criteriaYaml: str | None, sourceNote: str)`.
- If using dict instead, update all prose to `branch_info["copyBranch"]` or `branch_info.get("copyBranch")`.

### LOW-1: "byte-for-byte" is stronger than the planned lockstep test

Plan A repeatedly says the app JSON is byte-for-byte copied from the backend JSON, but the planned test allows deep-equal canonical JSON comparison.

Evidence:

- `13-A-corrective-exercises-PLAN.md:36` and `13-A-corrective-exercises-PLAN.md:189` say byte-for-byte copy.
- `13-A-corrective-exercises-PLAN.md:194` says the test can use canonical hash or deep-equal.

Risk:

- This is not a product bug if content is identical. It is only a wording/test precision mismatch.

How I would fix it:

- Either enforce real `sha256(bytes)` equality, or soften the wording to "content-identical app mirror".
- I would use deep-equal as the actual gate and stop saying byte-for-byte, because formatting-only drift is not meaningful to the app.

## Narrow Gate Status

| Gate | Iteration 3 status | Notes |
|------|--------------------|-------|
| criteria 7 IPSF angles | PASS with human checkpoint | The critical correction is in place: current five production motions route to `eunji_measured_yaml` or `no_angle_criterion`; future IPSF fixtures are gated. Fix HIGH-1 wording so `ref-climb` stays fixture-less. |
| 3-way contract / Firestore nested-array | PASS with tsconfig caveat | Plain camelCase scalar dict + scoped validator is still the right shape. Add `app/tsconfig.json` to Plan A because JSON import is now part of the contract. |
| D-05 painAreas boundary | PASS | Plan A still keeps painAreas in mapping/coaching only, with a no-scoring-leak grep gate. |
| criteria 5 Pod dependency | PASS | Keeping Cerebras E2E as a blocking Pod checkpoint remains appropriate. |

## Recommendation

Patch before execution:

1. Fix nullable `angleFixtureKey` wording for `no_angle_criterion` in Plan B and `13-REVIEW-FIXES.md`.
2. Add `app/tsconfig.json` + `resolveJsonModule` to Plan A file/acceptance contract.
3. Supersede or patch stale `is_registered` sections in `13-PATTERNS.md` and `13-PLAN-CHECK.md`.
4. Choose dict or dataclass for `MotionBranchInfo` and make prose/call sites consistent.

After those edits, I would move Phase 13 from "revise-before-execution" to "ready for execution with human checkpoints".
