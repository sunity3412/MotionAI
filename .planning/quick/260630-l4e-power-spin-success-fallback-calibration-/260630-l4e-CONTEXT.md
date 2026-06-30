# Quick Task 260630-l4e: power-spin success fallback calibration + kip-up split margin domain review — Context

**Gathered:** 2026-06-30
**Status:** Investigation complete (pod evidence captured) — ready for planning
**Pod:** 97s9atfkakbki8 (ssh root@213.173.104.4 -p 35122), HEAD 5351bb3

<domain>
## Task Boundary

Two analysis-accuracy items on the Phase-24 transparent deduction tally:

1. **power-spin success fallback calibration** — 정은지 success power-spin (vs 정은지 reference)
   scores **91**, but belle spec [[score-spec-95-100-elite-vision-fix]] requires 같은 정은지 = 95~100.
2. **kip-up split margin domain review** — confirm the `split_angle` reference-relative criterion's
   fault-vs-success separation is domain-adequate (likely a documentation outcome, not a code change).
</domain>

<evidence>
## Root Cause (pod-verified, runId 1782526430 baseline + live probes)

### Score path for a CLEAN measured success video
`pipeline/app.py::_apply_vision_veto_from_context` (line ~2350):
- Calls `deduction_engine.tally(...)` with `dimension_overall = score_result["overallScore"]`.
- The tally is the authoritative transparent score: `final = max(0, 100 + Σ points)`.
- For power-spin success: ALL measured deviations are within the CITED 20° IPSF tolerance
  (leg_extension=9.3°, line=8.84°, every per-joint angle_vs_reference < 11°), and Gemini is
  silent (n_supported_differences=0). So `criteria_from_measured_deviations` seeds nothing
  (seeds only when `dev > 20°`), `activated` is empty → **tally `final` = 100, records = ()**.

### The bug
When records are empty, the wrapper takes the `not_applicable` branch (app.py:2388-2396) which
returns `{**score_result, ...}` **WITHOUT overriding `overallScore`** — so the displayed score
stays `score_result["overallScore"]` = `dimensions.overall_from_dimensions` = **`min(angle, line)`**
(dimensions.py:384). The `line` core dimension applies a *continuous, non-IPSF* sub-tolerance penalty
→ 91 for power-spin's 8.84° extension deficit. That is exactly the continuous-penalty philosophy the
Phase-24 transparent tally was built to retire ([[scoring-must-be-transparent-deduction-tally]]).

**Net:** the transparent tally said "clean → 100"; the wrapper discards that and shows the legacy
min-of-core dimension (91). peter-pan/elbow-twist/pdshape success = 100 only because their
`dimension_overall` happens to already be 100.

### Quant non-determinism (observed)
power-spin `quantificationStatus` varies run-to-run (committed baseline = unavailable → 91 via
`dimension_overall_fallback` RECORD; live probe = available → 91 via `not_applicable` passthrough).
Both paths land on the same legacy min-of-core 91. The quant-unavailable+empty case routes through
the `applied` path (fallback record present) and is NOT the target here; it is the honest conservative
fallback when nothing could be measured (BLOCKER A — do not blindly reset to 100).

## Fix direction (principled, NOT recalibration)
Make the `not_applicable` branch use `breakdown.final` as `overallScore` (it already equals 100 when
the tally ran clean with measurement substrate). No thresholds/constants change → does not violate
[[calibration-source-hard-gate]]. Aligns displayed score with the transparent tally.

## REGRESSION GUARD (mandatory verification)
A FAULT that the 20° tally tolerates AND Gemini misses currently relies on the legacy min-of-core to
dock it. The thin case is **kip-up fault**: in runs where the split is not detected (no `split_angle`
record), it lands in `not_applicable` and keeps `dimension_overall` (~97). The fix would push it to
100 → re-open the FP. The resolved kip-up state (fault=88, [[kipup-fp-RESOLVED-phase24A]]) relies on a
`split_angle` RECORD firing (→ `applied` path → unaffected). **The fix MUST be gated by a full 6-pair
pod sweep proving kip-up fault stays low (≤ ~88) and every fault stays penalized.** If kip-up fault
jumps to 100, surface to belle as a decision (do not ship silently).
</evidence>

<verification>
## Required pod verification (Claude runs — [[pod-ops-claude-runs]])
Full 6-pair Phase-24 sweep (`backend/evals/phase24/run_sweep.py`) after the fix, SERIAL
([[pipeline-not-concurrency-safe-eval-serial]]). PASS criteria:
- power-spin success: 91 → **95~100**
- peter-pan / elbow-twist / pdshape success: **stay 100**
- kip-up success: 95~100 (was 96)
- **kip-up fault: stays ≤ ~88 (NO jump to 100)** ← hard gate
- all other faults: stay penalized (power-spin 47, peter-pan 79, elbow 61, pdshape 60 ± noise)
- Local: existing deduction_engine / vision-veto unit tests stay green.
</verification>

<canonical_refs>
## Canonical References
- `backend/functions/pipeline/app.py::_apply_vision_veto_from_context` (~2308-2399) — the fix site
- `backend/shared/python/sunity_shared/analysis/deduction_engine.py::tally` — authoritative `final`
- `backend/shared/python/sunity_shared/analysis/dimensions.py::overall_from_dimensions` — legacy min-of-core
- `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py` — split_angle criterion (tol 20° CITED)
- `backend/evals/phase24/run_sweep.py` + `baseline/phase24_sweep_report.json` — verification harness
- Memory: [[scoring-must-be-transparent-deduction-tally]], [[score-spec-95-100-elite-vision-fix]],
  [[calibration-source-hard-gate]], [[kipup-fp-RESOLVED-phase24A]], [[pipeline-not-concurrency-safe-eval-serial]]
</canonical_refs>
