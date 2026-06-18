# Phase 19 Plan Direct Review — Iteration 5

**Reviewer:** Codex direct review (no external review skill)
**Reviewed:** 2026-06-18
**Scope:** Current `19-01-PLAN.md`, `19-03-PLAN.md`, `19-04-PLAN.md`, `19-VALIDATION.md`, and existing tests impacted by the plan.

## Verdict

**Needs one narrow revision before execution.**

Iteration 4 feedback is addressed in the plan: Mode1 `scoringBasis` is now a serialized optional contract field, Mode3 validation is enum/value based instead of raw prose grep, and the smoke script now uses thrown errors plus `process.exitCode` after `finally`. The remaining issue is a concrete backend-suite regression caused by the new `build_mode1` fields.

## Finding

### HIGH-1 — `build_mode1` will break an existing exact-dict test unless `test_assemble.py` is updated

**Risk:** Plan 04 now says `assemble.build_mode1` must always emit:

```python
out["scoringBasis"] = "reference_motion"
out["scoringBasisLabel"] = ...
```

(`19-04-PLAN.md:164`)

That is the right contract decision, but the existing `backend/tests/test_assemble.py::test_mode1_shape_and_clamp` currently asserts exact equality:

```python
assert c == {
    "mode": "mode1",
    "referenceMotionId": "m1",
    "referenceMotionName": "인사이드 레그 행",
    "athleteName": "정은지",
    "similarity": 100,
}
```

Adding the two new fields will fail this test even if the implementation is correct. Current Plan 04 `files_modified` does not include `backend/tests/test_assemble.py`, and the Plan 04 verify command does not run it. So the phase can pass the new focused tests while breaking an existing contract test in the full backend suite.

**What I would do:** Add `backend/tests/test_assemble.py` to Plan 04 `files_modified` and update the exact expectation:

```python
assert c == {
    "mode": "mode1",
    "referenceMotionId": "m1",
    "referenceMotionName": "인사이드 레그 행",
    "athleteName": "정은지",
    "similarity": 100,
    "scoringBasis": "reference_motion",
    "scoringBasisLabel": "정은지 측정 각도 기준 비교",
}
```

If the label uses a longer phrase, assert exact product copy there or assert only that it contains `"정은지"` and `"측정 각도 기준"`. I would prefer exact copy if the plan fixes the label string.

Also extend `test_mode1_segment_scores_included_only_when_given` to assert that `scoringBasis` remains present both with and without `segmentScores`; otherwise a future refactor could accidentally emit basis only for simple Mode1.

Add this focused verification to Plan 04:

```sh
cd backend && python -m pytest \
  tests/test_assemble.py::test_mode1_shape_and_clamp \
  tests/test_assemble.py::test_mode1_segment_scores_included_only_when_given \
  tests/test_pipeline_mode3.py::test_mode1_scoring_basis_reference_motion \
  -x -q
```

## Resolved Since Iteration 4

- Mode1 basis is now explicitly serialized through `Mode1Comparison.scoringBasis?: 'reference_motion'` and `build_mode1`.
- Mode3 basis validation is now enum/value based; explanatory prose can mention `reference_motion` safely.
- Plan 03 smoke cleanup now avoids inline `process.exit()` and uses `process.exitCode` after `finally`.

## Suggested Plan Edit

Patch Plan 04 to include `backend/tests/test_assemble.py` in `files_modified`, update the two Mode1 assembly tests above, and add the focused pytest command to verification. After that, I would consider Phase 19 execution-ready from a planning standpoint.

## Residual Risk

After this patch, remaining risk is implementation/calibration rather than plan consistency. The plan has enough test and contract coverage to proceed.
