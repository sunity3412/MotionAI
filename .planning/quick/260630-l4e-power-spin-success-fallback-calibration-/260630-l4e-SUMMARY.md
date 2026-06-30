---
phase: quick-260630-l4e
plan: 01
subsystem: backend/scoring (vision veto seam)
tags: [phase24, transparent-tally, vision-veto, power-spin, scoring-accuracy]
requires:
  - "deduction_engine.tally(...).final (authoritative transparent score)"
provides:
  - "not_applicable branch overallScore = breakdown.final (legacy min-of-core passthrough retired)"
affects:
  - "정은지 success power-spin score (was pinned 91, now tracks transparent tally = 100 when clean)"
tech-stack:
  added: []
  patterns:
    - "transparent deduction tally is authoritative in every measured path (no legacy min-of-core leak)"
key-files:
  created: []
  modified:
    - backend/functions/pipeline/app.py
    - backend/tests/test_pipeline_deduction_seam.py
    - backend/tests/test_pipeline_vision_gate.py
decisions:
  - "not_applicable 분기는 breakdown.final 을 overallScore 로 사용 — clean tally(empty records, quant available) → final=100. 레거시 dimensions.overall_from_dimensions = min(angle,line) passthrough 제거."
  - "quant-unavailable+empty 케이스는 applied 경로(dimension_overall_fallback record)로 라우팅되어 영향 없음(BLOCKER A — honest conservative fallback 보존)."
metrics:
  duration: ~15m
  completed: 2026-06-30
---

# Quick Task 260630-l4e: power-spin success fallback calibration Summary

One-line behavioral fix retiring the last legacy min-of-core passthrough: the `not_applicable` branch of `_apply_vision_veto_from_context` now sets `overallScore = breakdown.final`, so a clean transparent tally (empty records, quant available) shows the tally's own 100 instead of the legacy `min(angle, line)` dimension that pinned 정은지 success power-spin to 91.

## What Was Built

### Task 1 — app.py one-line behavioral change (commit `850fcc4`)
`backend/functions/pipeline/app.py::_apply_vision_veto_from_context` — the `not_applicable` (has_deduction False) return previously spread `{**score_result, ...}` without overriding `overallScore`, silently passing through the legacy `score_result["overallScore"]` (= `dimensions.overall_from_dimensions` = `min(angle, line)`). Added a single key `"overallScore": breakdown.final` alongside the existing `deductionBreakdown` entry, with a Korean comment citing Phase 24 and the two governing principles. `final = max(0, round(100 + Σ points))` = 100 when records are empty (`deduction_engine.py:285`), aligning the displayed score with the transparent tally that already computed it.

The `applied` branch (already sets `overallScore: breakdown.final`) and the non-tally passthrough (`{**score_result, "visionVeto": audit}`) are untouched. No new constants, no threshold changes — does NOT violate [[calibration-source-hard-gate]].

### Task 2 — unit tests pinning the new behavior (commit `d557d6d`)
- `test_gemini_silent_clean_geometry_not_applicable`: flipped the retired `overallScore == 99` legacy assertion to `overallScore == deductionBreakdown["final"] == 100`, docstring updated.
- New `test_clean_not_applicable_uses_tally_final_not_legacy_dimension`: seeds a CLEAN no_fault context (quant available, empty `measured_deviations`) with a legacy `score_result["overallScore"] = 91` (the power-spin success number) and asserts the returned `overallScore` is `breakdown.final` (== 100), NOT 91 — proving the min-of-core dimension no longer leaks.
- `test_pipeline_vision_gate.py::test_not_applicable_has_no_quantification_fields`: same retired legacy passthrough (88) updated to `final == 100`, preserving the test's primary discriminated-audit intent.

## Verification

### Task 1 verify (`tests/test_pipeline_deduction_seam.py -x -q`)
After the app.py edit alone, `test_gemini_silent_clean_geometry_not_applicable` correctly went red (`assert 100 == 99`) — confirming the behavioral change landed; Task 2 updates the test to the new authoritative behavior.

### Task 2 verify (four named files) — GREEN
```
$ .venv/bin/python -m pytest tests/test_pipeline_deduction_seam.py tests/test_deduction_engine.py tests/test_vision_veto.py tests/test_pipeline_vision_gate.py -q
........................................................................ [ 51%]
.....................................................................  [100%]
141 passed in 0.76s
```

### grep — override present in BOTH branches
```
$ grep -n "overallScore.*breakdown.final" functions/pipeline/app.py
2272:                "overallScore": breakdown.final,   # (pre-existing)
2380:                "overallScore": breakdown.final,   # applied branch
2398:                "overallScore": breakdown.final,   # not_applicable branch (NEW)
```

### Regression — zero new failures
Full collectible backend suite (excluding pre-existing gemini-env / smoke / module-collision collection errors documented in MEMORY):
- At pre-change commit `5351bb3`: **101 failed, 1823 passed, 19 skipped**.
- At this HEAD `d557d6d`: **101 failed, 1824 passed, 19 skipped** (the +1 passing = the new test).

Identical 101 pre-existing failures (all in gemini-env / phase06-08-09 body-comparison / reference-handler files — none touch the not_applicable scoring path). Zero regression introduced. `tests/test_pipeline_mode3.py` (34) also green — mode3 routes through `mode3_held` passthrough, unaffected.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_pipeline_vision_gate.py pinned the same retired legacy passthrough**
- **Found during:** Task 2 (running the four named verify files)
- **Issue:** `test_not_applicable_has_no_quantification_fields` asserted `overallScore == 88`, the exact legacy min-of-core passthrough the fix retires. With empty records the transparent tally yields `final == 100`, so this assertion failed.
- **Fix:** Updated the score assertion to `overallScore == deductionBreakdown["final"] == 100`, preserving the test's primary intent (the not_applicable audit has no quantification fields). The plan's Task 2 verify block explicitly includes this file and expects it green, so the update is in-scope.
- **Files modified:** backend/tests/test_pipeline_vision_gate.py
- **Commit:** d557d6d

## Orchestrator-Owned (NOT executed here)
Per <success_criteria>, the executor scope is code + local unit tests only. The hard gate is owned by the orchestrator (Claude runs on pod):
- Full 6-pair Phase-24 SERIAL sweep ([[pipeline-not-concurrency-safe-eval-serial]]) `backend/evals/phase24/run_sweep.py` after this fix.
- PASS criteria: power-spin success 91 → 95~100; peter-pan/elbow-twist/pdshape success stay 100; kip-up success 95~100; **kip-up fault stays ≤ ~88 (NO jump to 100) — HARD GATE**; all other faults stay penalized.
- If kip-up fault jumps to 100 → escalate to belle as a decision (do not ship silently) ([[kipup-fp-RESOLVED-phase24A]]).
- kip-up split-margin domain review (documentation deliverable).

## Commits
- `850fcc4` fix(quick-260630-l4e): not_applicable 도 breakdown.final 을 overallScore 로
- `d557d6d` test(quick-260630-l4e): clean not_applicable → overallScore == breakdown.final

## Self-Check: PASSED
- backend/functions/pipeline/app.py — FOUND (override at line 2398)
- backend/tests/test_pipeline_deduction_seam.py — FOUND (new test present, 6 passing in file group)
- backend/tests/test_pipeline_vision_gate.py — FOUND (updated assertion green)
- commit 850fcc4 — FOUND in git log
- commit d557d6d — FOUND in git log (HEAD)
