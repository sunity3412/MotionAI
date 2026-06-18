# Phase 19 Plan Direct Review — Iteration 4

**Reviewer:** Codex direct review (no external review skill)
**Reviewed:** 2026-06-18
**Scope:** Current `19-01-PLAN.md`, `19-03-PLAN.md`, `19-04-PLAN.md`, `19-VALIDATION.md`, and referenced app/backend contracts.

## Verdict

**Needs one final consistency revision before execution.**

Iteration 3 feedback was largely absorbed. The smoke now has a local TypeScript compile/import recipe, Mode3 is correctly narrowed to four `scoringBasis` values, Mode1 was split out of the Mode3 gate, and `posture` was removed from executable `dimensionScores`. The remaining problems are smaller but still execution-relevant: two acceptance checks contradict their own instructions, and the Mode1 `scoringBasis` path is not fully contracted.

## Findings

### HIGH-1 — Mode1 `scoringBasis` is tested but not fully contracted

**Risk:** Plan 01 adds `test_mode1_scoring_basis_reference_motion` and says MODE_EXPERT should produce `scoringBasis="reference_motion"` (`19-01-PLAN.md:138`). Plan 04 also says Mode1 should set this through `build_mode1` or a separate display helper (`19-04-PLAN.md:141`, `19-04-PLAN.md:151`).

But Task 3 only updates `Mode3Comparison` with `scoringBasis/scoringBasisLabel` (`19-04-PLAN.md:190-193`). The existing app type has no Mode1 basis fields (`app/src/types/analysis.ts:239-247`). That leaves implementers with two incompatible choices:

- emit `comparison.scoringBasis` for Mode1 and leave the app/docs contract incomplete;
- avoid emitting it and make `test_mode1_scoring_basis_reference_motion` assert an internal value that is not part of the result contract.

**What I would do:** Make the decision explicit. My preferred fix is to contract Mode1 as optional, because it keeps the test meaningful and does not break legacy docs:

```ts
export interface Mode1Comparison {
  mode: 'mode1';
  referenceMotionId: string;
  referenceMotionName: string;
  athleteName: string;
  similarity: number;
  segmentScores?: SegmentScores;
  scoringBasis?: 'reference_motion';
  scoringBasisLabel?: string;
}
```

Then update `assemble.build_mode1` to emit those two fields, update `docs/contract.md`, and make the test assert the serialized Mode1 comparison. If the product does not need a Mode1 basis field, remove the serialized `scoringBasis` expectation from `test_mode1_scoring_basis_reference_motion` and instead test only that Mode1 never routes through `build_mode3`.

### HIGH-2 — The `reference_motion` grep acceptance contradicts the required docs/comments

**Risk:** Plan 04 tells implementers to document that `reference_motion` is Mode1-only and absent from Mode3 (`19-04-PLAN.md:191-193`). The same acceptance criteria then require `reference_motion` to appear zero times in the Mode3Comparison definition/Mode3 docs section (`19-04-PLAN.md:205-206`).

Both cannot be true if the docs/comments literally say "`reference_motion` is not in Mode3." The likely outcome is a false acceptance failure, or implementers removing useful explanatory comments to satisfy a brittle grep.

**What I would do:** Make the mechanical check target enum values, not prose. For example:

- TS: assert the `Mode3Comparison.scoringBasis` union has exactly the four Mode3 literals.
- Python: assert `_MODE3_SCORING_BASES == {...four values...}`.
- Docs: assert the Mode3 table lists the four Mode3 values and has no row/value named `reference_motion`.

Do not require raw `reference_motion` grep 0 across explanatory prose. Alternatively, if a strict grep is desired, avoid the literal in the Mode3 section and say "Mode1-only reference basis is excluded" without spelling the enum value there.

### MEDIUM-1 — Plan 03 cleanup guarantee conflicts with `process.exit(1)`

**Risk:** Plan 03 requires the smoke script to delete its temp directory in `try/finally` (`19-03-PLAN.md:114`), but the same instructions call `process.exit(1)` on failed assertions (`19-03-PLAN.md:107`, `19-03-PLAN.md:113`). In Node, `process.exit()` does not reliably unwind `finally`; I verified a minimal `try { process.exit(7) } finally { ... }` exits without running the `finally` body.

This is not a product correctness blocker, but it makes the smoke script fail its own cleanup contract on failure paths and can leave temp output behind during debugging.

**What I would do:** Do not call `process.exit(1)` inside the assertion path. Use thrown errors and one top-level cleanup boundary:

```js
let exitCode = 0;
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'sunity-norm-'));

try {
  // compile, import, assert
  if (typeof mod.normalizeFrames !== 'function') {
    throw new Error('normalizeFrames export missing');
  }
} catch (error) {
  exitCode = 1;
  console.error(error instanceof Error ? error.message : error);
} finally {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}

process.exitCode = exitCode;
```

That preserves cleanup and still returns non-zero.

## Resolved Since Iteration 3

- Plan 03 now uses local `node_modules/typescript/bin/tsc` plus `createRequire` for production `normalizeFrames` import.
- Plan 04 now makes `build_mode3` a four-value Mode3 enum and rejects `reference_motion`.
- `test_unknown_move_gate` now covers only Mode3 values; Mode1 is separated.
- Reference-free executable scoring is now `line + stability`; `posture` is explicitly future/non-score evidence.

## Suggested Plan Edits

1. Decide whether Mode1 `scoringBasis` is a serialized contract field. If yes, add it to `Mode1Comparison`, `build_mode1`, and `docs/contract.md`; if no, change the Mode1 test to avoid asserting a serialized `scoringBasis`.
2. Replace raw `reference_motion` grep-zero checks with enum/table-value checks, or remove the literal from explanatory Mode3 prose.
3. Change the smoke script plan from inline `process.exit(1)` to thrown assertions plus `process.exitCode` after `finally`.

## Residual Risk After These Fixes

After these edits, I would treat the plan as execution-ready. The remaining risk is implementation quality and calibration, not plan clarity.
