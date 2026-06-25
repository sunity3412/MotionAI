---
phase: 24-transparent-deduction-scoring
plan: 04
subsystem: scoring
tags: [vision-veto, deduction-tally, low-alignment, measured-seed, gap-closure, objectivity]

# Dependency graph
requires:
  - phase: 24-transparent-deduction-scoring
    plan: 02
    provides: _apply_vision_veto_from_context seam, deduction_engine.tally wiring, _build_deduction_measured_deviations substrate, no_fault tally-eligibility, to_audit_dict(tallyFinal)
  - phase: 24-transparent-deduction-scoring
    plan: 01
    provides: deduction_engine.tally, criteria_from_measured_deviations measured seed, criteria_for_fault Gemini router
  - phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame
    provides: assess_alignment_confidence + _collect_vision_fault_context low_alignment collect-side bail (UNCHANGED)
provides:
  - low_alignment_confidence is measured-seed tally-eligible at the apply seam (RTMW deviations deduct under low Gemini alignment; Gemini faults stay absent)
  - to_audit_dict emits collectionStatus for both final statuses (measured-only provenance preserved)
affects: [24-eval-gates-pod-resweep, mode-1-mode-3-testflight]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Routing/coverage fix (NOT a slope/cap re-fit): one collection_status moves from score-free passthrough into the measured-seed tally branch; thresholds + slope untouched"
    - "Alignment-independent measured seed: RTMW extension deficit + body-relative notches deduct regardless of student<->reference DTW alignment; Gemini fault localization stays deferred on poorly-aligned frames"
    - "Objectivity boundary preserved by empty supported_differences: criteria_for_fault adds nothing for low_alignment -> no fabricated Gemini-located faults"

key-files:
  created: []
  modified:
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/analysis/vision_veto.py
    - backend/tests/test_pipeline_deduction_seam.py
    - backend/tests/test_vision_veto.py
    - backend/tests/test_pipeline_vision_gate.py

decisions:
  - "low_alignment_confidence moved OUT of passthrough_map and INTO the tally-eligible set {candidate_verdict, no_fault, low_alignment_confidence}; remaining non-measuring siblings (resource_limited/disabled/mode3_held/missing_reference/missing_current_video/skipped_error) stay score-free passthrough byte-unchanged"
  - "to_audit_dict now emits collectionStatus for applied AND not_applicable (was absent) — required to satisfy must_have #3 (report shows measurement-only provenance). Rule 2 fix, in the plan's named vision_veto.py target"
  - "Collect-side bail (_collect_vision_fault_context low_alignment), eligible_for_coach (candidate_verdict-only), and assess_alignment_confidence thresholds are all UNCHANGED — this is a coverage/routing fix, not a re-calibration"

requirements-completed: [SCORE-16]

# Metrics
duration: ~25min
completed: 2026-06-26
---

# Phase 24 Plan 04: low_alignment Measured-Seed Tally-Eligibility Summary

**Closes the 24-03 real-video BLOCKER by making `low_alignment_confidence` tally-eligible for the MEASURED seed only: the apply seam now routes the alignment-independent RTMW measured deviations (extension deficits + body-relative notches) through `deduction_engine.tally` even when Gemini alignment was low, so a measurable geometric deviation DEDUCTS — while Gemini vision-located faults stay absent (`supported_differences=[]` -> `criteria_for_fault` adds nothing, no fabricated faults).**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-26
- **Completed:** 2026-06-26
- **Tasks:** 3 (2 with commits; Task 3 = verification-only, no diff)
- **Files modified:** 5 (0 created, 5 modified — 2 production, 3 test)

## Accomplishments
- **Seam routing (Task 1):** in `_apply_vision_veto_from_context`, `low_alignment_confidence` moved out of `passthrough_map` and added to the tally-eligible gate `{candidate_verdict, no_fault, low_alignment_confidence}`. Because the low_alignment ctx carries `supported_differences=[]`, only `criteria_from_measured_deviations` (the measured seed) fires — `criteria_for_fault` adds zero Gemini-located records. The Phase 23 collect-side bail, `eligible_for_coach` (candidate_verdict-only), and `assess_alignment_confidence` thresholds are all UNCHANGED.
- **Audit provenance (Rule 2 fix):** `to_audit_dict` now emits `collectionStatus` for both `applied` and `not_applicable` (it previously did not emit it at all in the final-audit path). This is what makes must_have #3 true — the report transparently shows a low_alignment deduction was measurement-only (no Gemini-located fault). The plan's critical_context assumed `to_audit_dict` already emitted it; the code did not, so I added it within the plan's named `vision_veto.py` target.
- **Tests (Task 2):** four seam tests (measured-deduction-applied with measured-only `deviationSource` + collectionStatus provenance + coach-ineligible; clean-geometry not_applicable; no-fabricated-Gemini-faults; sibling-passthrough non-regression) + one vision_veto unit test (collect-status coach-ineligibility + audit provenance). Migrated `test_apply_passthrough_score_free_status` to drop low_alignment from the score-free passthrough set.
- **Regression (Task 3):** Phase 24 + Phase 20/23 targeted suites green (196 passed); band grep (`apply_downward_cap|SEVERITY_CAP|capApplied`) across `backend/shared/python` + `backend/functions` = 0; production change scope is exactly `app.py` + `vision_veto.py`.

## Task Commits

1. **Task 1: low_alignment_confidence -> measured-seed tally-eligible at apply seam** — `ce98310` (feat)
2. **Task 2: seam + unit tests (measured deduction under low alignment, no fabricated Gemini faults)** — `94667e2` (test; includes the Rule 2 `to_audit_dict` collectionStatus fix)
3. **Task 3: targeted suite + band grep** — verification-only, no diff (the `<files>` test target was finalized in Task 2; suites green + grep 0).

## Files Created/Modified
- `backend/functions/pipeline/app.py` — `_apply_vision_veto_from_context`: low_alignment moved into the tally-eligible gate; docstring + inline comments updated; `passthrough_map` no longer contains `low_alignment_confidence`.
- `backend/shared/python/sunity_shared/analysis/vision_veto.py` — `collection_status` enum comment documents apply-seam eligibility; `to_audit_dict` emits `collectionStatus` (provenance preservation).
- `backend/tests/test_pipeline_deduction_seam.py` — 4 new low_alignment seam tests.
- `backend/tests/test_vision_veto.py` — 1 new collect-status/audit-provenance unit test.
- `backend/tests/test_pipeline_vision_gate.py` — migrated `test_apply_passthrough_score_free_status` (low_alignment dropped from the passthrough set).

## Decisions Made
- **Sibling statuses stay passthrough.** Only `low_alignment_confidence` moved; `resource_limited`/`disabled`/`mode3_held`/`missing_reference`/`missing_current_video`/`skipped_error` remain genuinely-unmeasurable score-free passthrough (no `deductionBreakdown`). Asserted by `test_low_alignment_does_not_regress_sibling_passthrough` + the migrated gate test.
- **Coach eligibility untouched.** `low_alignment` does NOT inject coach root-cause — alignment was low, there is no Gemini cause to render. `eligible_for_coach` stays `candidate_verdict AND cap_would_apply` (asserted in both the seam test and the new vision_veto test).
- **HIGH-3 score-not-deviation unchanged.** The measured seed remains `_build_deduction_measured_deviations` output (extension_deviation deg + body-relative notches only); no 0-100 dimension SCORE enters as a deviation. Not weakened.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] to_audit_dict did not emit collectionStatus**
- **Found during:** Task 2 (writing the provenance assertion)
- **Issue:** The plan's critical_context and must_have #3 require that a low_alignment `applied` audit preserves `collectionStatus=low_alignment_confidence` so the report shows the deduction was measurement-only. Reading `vision_veto.py:to_audit_dict`, the final-audit path built `audit` fresh and never added `collectionStatus` (only `to_coach_context_dict`/`to_trace_dict` emitted it). Without this, must_have #3 was unverifiable.
- **Fix:** Added `audit["collectionStatus"] = self.collection_status` to `to_audit_dict` (emitted for both `applied` and `not_applicable`).
- **Files modified:** `backend/shared/python/sunity_shared/analysis/vision_veto.py`
- **Verification:** `test_low_alignment_measured_deduction_applied` asserts `visionVeto.collectionStatus == "low_alignment_confidence"`; `test_low_alignment_collect_status_coach_ineligible_audit_provenance` asserts it on the unit `to_audit_dict("applied")` call; no existing test asserted its absence; 196 targeted tests green.
- **Committed in:** `94667e2`

**2. [Rule 1 - Bug] Existing test asserted low_alignment as score-free passthrough**
- **Found during:** Task 1 (verification suite)
- **Issue:** `test_apply_passthrough_score_free_status` looped `("low_alignment_confidence", "resource_limited")` and asserted `status` unchanged — directly contradicting the plan's intended behavior change.
- **Fix:** Removed `low_alignment_confidence` from that loop (it is now covered by the dedicated Task 2 tests) and broadened the loop to the genuine non-measuring siblings, asserting no `deductionBreakdown` is produced.
- **Files modified:** `backend/tests/test_pipeline_vision_gate.py`
- **Committed in:** `ce98310`

**Total deviations:** 2 auto-fixed (1 missing-functionality, 1 stale-test bug). Both are in the plan's named edit targets; no scope creep.

## Known Stubs
None — the seam produces real `deductionBreakdown` objects from the alignment-independent measured substrate. The not_applicable path (clean geometry) is an honest "no measurable deviation" result, not a placeholder.

## Threat Flags
None — no new network/auth/file/schema surface. The change is an in-process routing fix on an existing scoring seam; no new Gemini call, no new persisted field shape (`collectionStatus` is an existing audit key emitted by sibling serializers).

## User Setup Required
None for the code. **Orchestrator-owned, pending:** Pod layer re-sweep regenerates `backend/evals/phase24/baseline/phase24_breakdowns.json` against this routing change (fault members should now carry non-null measured `deductionBreakdown` records, kip-up FP re-checked, generalization gate runs on real breakdowns), then re-present to belle for verification. This re-sweep + belle verification is the Task-3 checkpoint resume per the plan `<acceptance>` — NOT part of this autonomous plan's code gates.

## Self-Check: PASSED

- Files: `app.py`, `vision_veto.py`, `test_pipeline_deduction_seam.py`, `test_vision_veto.py`, `test_pipeline_vision_gate.py` all present and modified; `24-04-SUMMARY.md` written.
- Commits: `ce98310`, `94667e2` both in history.
- Tests: 196 targeted (Phase 24 + Phase 20/23) pass; band grep = 0; production change scope = app.py + vision_veto.py only.

---
*Phase: 24-transparent-deduction-scoring*
*Completed: 2026-06-26*
