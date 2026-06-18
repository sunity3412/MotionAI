# Phase 19 Plan Direct Review — Iteration 3

**Reviewer:** Codex direct review (no external review skill)
**Reviewed:** 2026-06-18
**Scope:** Current `19-01-PLAN.md` through `19-04-PLAN.md`, `19-VALIDATION.md`, and referenced app/backend code.

## Verdict

**Needs targeted revision before execution.**

Iteration 2 feedback is mostly handled. The plan now covers optional `contributesToOverall`, `simulatedResult.ts`, per-test anchor gating, production single-source normalization, stable frame counts, source-based `scoringBasis`, UI visibility, and vision hook identity. The remaining issues are not broad design problems; they are execution-contract mismatches that can still make the implementation fail typecheck/smoke or drift from the stated Mode3 truth contract.

## Findings

### HIGH-1 — Plan 03 still does not pin down how the `.mjs` smoke imports TypeScript production code

**Risk:** Plan 03 correctly says the smoke must call production `normalizeFrames`, not copy the algorithm (`19-03-PLAN.md:97-98`). It also says to compile TS first if Node cannot import TS directly. But the actual verify command is still only:

```sh
cd app && npm run typecheck && node scripts/_smoke_joints_normalize.mjs
```

(`19-03-PLAN.md:107`)

The app has `typescript` as a devDependency but no `tsx`, `ts-node`, or `esbuild` (`app/package.json:41-44`). A plain `.mjs` script cannot directly import `app/src/lib/normalizePose3d.ts` under Node. If the executor writes a direct TS import, the smoke fails at runtime; if they copy the math to avoid that, the smoke stops proving production behavior.

**What I would do:** Make the smoke script own the compile/import path, with no new package install:

1. Inside `_smoke_joints_normalize.mjs`, create a temp output directory.
2. Run the local TypeScript binary, not a network-dependent install path:
   `node_modules/typescript/bin/tsc src/lib/normalizePose3d.ts --module commonjs --target ES2020 --outDir <tmp> --skipLibCheck`.
3. Use `createRequire(import.meta.url)` to require the compiled `normalizePose3d.js`.
4. Assert that `normalizeFrames` exists, then run the current synthetic/fallback/last-resort/whole-null cases.
5. Delete the temp directory on exit.

Then keep the verify command as `node scripts/_smoke_joints_normalize.mjs`; the script itself proves the production TS module is importable through the same path it tests. Also add an acceptance line that rejects any local `function normalizeFrames` definition inside the smoke file, so the no-copy rule is mechanically checkable.

### HIGH-2 — Plan 04 has a `scoringBasis` enum contradiction between backend helper and Mode3 contract

**Risk:** Plan 04 says Mode3 must never emit `reference_motion` (`19-04-PLAN.md:144`, `19-04-PLAN.md:157`) and the app `Mode3Comparison.scoringBasis` enum intentionally excludes it (`19-04-PLAN.md:182`). But the same plan tells `assemble.build_mode3` to accept an enum that includes `"reference_motion"` (`19-04-PLAN.md:146`), and the model contract wording says `5-enum(reference_motion 은 mode1 전용)` inside the Mode3 comparison update (`19-04-PLAN.md:183`).

That leaves two incompatible contracts:

- Backend `build_mode3` can accept or emit a value the app type says Mode3 cannot contain.
- Tests may pass by treating `reference_motion` as a global basis value while the UI contract treats it as forbidden for Mode3.

**What I would do:** Remove `reference_motion` from `build_mode3` entirely. Mode1 should not be modeled through `Mode3Comparison`; if Mode1 needs a visible basis label, put it on `build_mode1` or a separate shared display helper. For `build_mode3`, the allowed values should be exactly:

```python
{
    "reference_free_absolute",
    "recognized_motion_absolute",
    "previous_analysis_plus_absolute",
    "previous_analysis_plus_reference_free_absolute",
}
```

If someone calls `build_mode3(scoring_basis="reference_motion")`, I would fail the test with `ValueError` or avoid accepting free-form strings by using constants. Then align `models.py`, `docs/contract.md`, and `analysis.ts` to the same four-value Mode3 enum.

### MEDIUM-1 — `test_unknown_move_gate` mixes Mode1 into a Mode3 gate

**Risk:** Plan 01 asks `test_unknown_move_gate` in `test_pipeline_mode3.py` to parametrize five labels, including Mode1 `reference_motion` (`19-01-PLAN.md:131-137`). But Plan 04 and the app contract simultaneously require Mode3 to have no `reference_motion`.

This is testable, but it is easy to implement awkwardly: the Mode3 test may need a Mode1 `_process` harness just to cover the fifth enum, or a broad assertion may accidentally blur "global scoring basis values" with "Mode3 comparison values."

**What I would do:** Split the tests:

- `test_mode1_scoring_basis_reference_motion` covers `MODE_EXPERT` and asserts `reference_motion`.
- `test_unknown_move_gate` covers only the four Mode3 values and has one explicit invariant: no Mode3 comparison emits `reference_motion`.

That keeps the Mode3 RED test aligned with the TypeScript enum and makes the Mode1 case a separate contract instead of a special exception inside a Mode3 gate.

### MEDIUM-2 — Reference-free absolute scoring still names `posture`, but executable score dimensions are only `angle`, `line`, and `stability`

**Risk:** Plan 04 describes the reference-free absolute track as `line/stability/posture` (`19-04-PLAN.md:145`). The current scoring dimension contract is three dimensions: `angle`, `line`, `stability` (`app/src/types/analysis.ts:119`; `backend/shared/python/sunity_shared/analysis/dimensions.py:151-155`). The actual absolute scoring helper returns line and stability only (`dimensions.py:337-344`).

`posture` exists elsewhere as a body-normalizer/deduction concept, but it is not a `dimensionScores` key. Leaving it in the Phase 19 execution plan can cause one of two bad outcomes: implementers add an undocumented `posture` score key and break the app/contract, or the product copy implies a posture score that is not actually computed.

**What I would do:** For Phase 19, remove `posture` from the executable scoring path and write:

> reference-free absolute track = `line` + `stability` in `dimensionScores`; posture deductions remain a future/non-score evidence layer unless promoted through the full 3-way contract.

If posture should become a real score dimension, make that a separate explicit plan: add `posture` to `ScoreDimension`, backend `ABSOLUTE_DIMENSIONS`, contract docs, UI labels, weighting, `dimensionExplanation`, and tests. I would not fold that into this phase implicitly.

## Resolved Since Iteration 2

- `contributesToOverall` is now optional/legacy-safe and `simulatedResult.ts` is included in Plan 02.
- Anchor tests are now per-test env-gated, with the synthetic above-cutoff case intended to remain always-on.
- Plan 03 now uses `normalizePose3d.ts` as a single source and forbids per-frame null/drop.
- Plan 04 now distinguishes Mode3 first reference-free, first recognized, progress known, and progress reference-free composite basis labels.
- `DimensionDetailModal` now has planned copy for `contributesToOverall === false`.
- `build_mode3` backward compatibility and `_apply_vision_veto` same-object identity are now explicit test targets.

## Suggested Plan Edits

1. Update Plan 03 with a deterministic TypeScript compile/import recipe inside `_smoke_joints_normalize.mjs`, and make the no-algorithm-copy check mechanical.
2. Remove `reference_motion` from the `build_mode3` accepted enum and Mode3 schema language; keep it only in Mode1.
3. Split the Mode1 `reference_motion` test out of `test_unknown_move_gate`.
4. Replace `line/stability/posture` with `line/stability` for Phase 19, or formally promote `posture` through the full backend/app/docs contract in a separate scope.

## Residual Risk After These Fixes

After these revisions, I would treat Phase 19 as execution-ready. The remaining risk is calibration quality, not plan structure: `penalty_per_deg` and known-answer anchors are still direction-validation tools, not a proof of production-grade scoring accuracy.
