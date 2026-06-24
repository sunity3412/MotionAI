---
phase: 24
slug: transparent-deduction-scoring
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-24
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 24-RESEARCH.md "## Validation Architecture" (ND-07 gates: traceability / monotonicity / determinism / generalization).
> Revised 2026-06-24 post-Codex-review (24-DIRECT-REVIEW): OBJECT contract (HIGH-1a), signed-negative points (HIGH-2a), named substrate builder (HIGH-3a), body_relative_reach scoring substrate (HIGH-4a/ND-05), broadened cap-removal test scope (HIGH-5a), band-free coach-gate continuity (HIGH-6a), traceable fallback record (MEDIUM-1a), linear slope (MEDIUM-2a), non-masking gate command (MEDIUM-3a), 5-criteria PATTERNS sync (MEDIUM-4a).
> Revised 2026-06-24 post-Codex-review ITERATION 2: criteria_for_fault fault-context router replacing the keypoint_set map (HIGH-1), body_relative_reach insufficient-reach shortfall direction (HIGH-2), DeductionRecord.baselineValue/baselineKind split (HIGH-3), artifact-gated phase18 generalization gate (HIGH-4), line↔leg/arm cross-criterion no-double-count (HIGH-5), structural (not numeric ≥95) pure generalization bound (MEDIUM-1).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| **Config file** | none — tests under `backend/tests/` |
| **Quick run command** | `cd backend && python -m pytest tests/ -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q && python evals/phase24/assert_gates.py` |
| **Estimated runtime** | ~30 seconds (pure unit) / Pod-serial eval separate |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -q`
- **After every plan wave:** Run full unit suite
- **Before `/gsd-verify-work`:** Pure-first gates (traceability / monotonicity / determinism / criterion-selection) green; Pod-serial generalization gate run once with GPU (generates phase24_breakdowns.json)
- **Max feedback latency:** 30 seconds (pure); Pod eval is out-of-band serial

---

## Per-Task Verification Map

> Planner fills this from PLAN.md tasks. The ND-07 gates are pure-first (numpy, no GPU) then Pod-serial sampling per RESEARCH Validation Architecture.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 24-01-T1 | 24-01 | 1 | SCORE-16, SCORE-12, SCORE-14 | T-24-01 | contract lockstep OBJECT shape (HIGH-1a) + signed-negative points (HIGH-2a) + DeductionRecord.baselineValue/baselineKind split (HIGH-3) + deviationSource/unit unions extended (dimension_overall/score_delta, MEDIUM-1a) + fallback; FIVE criteria incl. `line`/clean_lines + `body_relative_reach` (reference_relative, insufficient-reach direction, baseline-driven via delta_notches — ND-05/HIGH-4a/HIGH-2); line/leg substrate profile-gated (empty joint_expectations → honest 0 — ND-06) + line excludes leg/arm-claimed substrate (HIGH-5); LINEAR slope (MEDIUM-2a); PUBLIC criteria_for_fault router (split-not-leg/leg/reach/line/gap on body_part/fault_state, severity-invariant — HIGH-1) + internal _criterion_for_keypoint_set TOTAL+PARTITIONING over all 8 FaultKey keypoint_sets; TRACKED deferred coverage gaps; no final ceiling; no per-criterion baseline_kind | unit | `cd backend && python -m pytest tests/test_deduction_engine.py -k "contract or criteria or lockstep or coverage or router" -x -q` + `cd app && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 24-01-T2 | 24-01 | 1 | SCORE-10, SCORE-11, SCORE-12, SCORE-13, SCORE-14, SCORE-15 | T-24-01, T-24-02, T-24-03 | measured-substrate base (not 100−Gemini); criterion selection via criteria_for_fault router (HIGH-1); line excludes leg/arm substrate (HIGH-5, no cross double-count); reach scored as insufficient-reach shortfall max(0, ref−student−tol) (HIGH-2); unavailable→dimension_overall (never 100) + traceable fallback record (MEDIUM-1a); gemini-silent still deducts; profile-gated line/leg substrate honest 0 when absent; body_relative_reach uses baseline (ND-05); LINEAR slope `raw=over*crit.slope` (MEDIUM-2a, no gaussian delegate); to_dict() OBJECT with baselineValue/baselineKind (HIGH-1a/HIGH-3); NaN-safe; severity not in arithmetic; coverage-gap not a band | unit | `cd backend && python -m pytest tests/test_deduction_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 24-01-T3 | 24-01 | 1 | SCORE-10..16 | T-24-01 | V5 input validation via deviation guards; 18+ unit gates incl. test_criteria_for_fault_selects_split_not_leg + test_criteria_for_fault_severity_invariant (HIGH-1), test_line_leg_no_cross_double_count (HIGH-5), test_reach_insufficient_direction (HIGH-2), test_unavailable_emits_traceable_record (MEDIUM-1a), test_body_relative_reach_uses_baseline (ND-05/HIGH-4a), test_line_criterion_empty_expectations_zero (ND-06 honest 0) | unit | `cd backend && python -m pytest tests/test_deduction_engine.py -x -q && python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 24-02-T1 | 24-02 | 2 | SCORE-10 | — | band code+comments removed; gemini_vision_scorer docstrings reframed severity→criterion-pointer (HIGH-5a, no code change); to_audit_dict reshaped band-free (tallyFinal, no capApplied); helpers preserved | unit | `cd backend && python -c "from sunity_shared.analysis import vision_veto; assert not hasattr(vision_veto,'apply_downward_cap') and not hasattr(vision_veto,'SEVERITY_CAP')"` | ❌ W0 | ⬜ pending |
| 24-02-T2 | 24-02 | 2 | SCORE-10, SCORE-13, SCORE-14, SCORE-15, SCORE-16 | T-24-04, T-24-05, T-24-06, T-24-10 | tally fed measured overallScore + NAMED `_build_deduction_measured_deviations` substrate (no dimension SCORE fed as a deviation — HIGH-3a; student/reference notches forwarded for the insufficient-reach shortfall — HIGH-2); criterion selection routes via criteria_for_fault, seam does NOT call the demoted criterion_for_fault_key or read severity (HIGH-1/ND-02); baseline_kind derived by name/motion_id string-match + threaded as a string into apply paths (no profile→no NameError); cap_would_apply band-free coach-root-cause eligibility (severity in moderate/major — continuity NOT byte-identical legacy, HIGH-6a; minor/none do NOT fire); result['deductionBreakdown'] set as OBJECT via to_dict() (HIGH-1a) + validated via `_validate_deduction_breakdown` top-level-dict in complete_analysis (no kwarg); nested-array validator; no silent no-op (WARNING+audit) | unit/integration | `cd backend && python -m pytest tests/test_pipeline_deduction_seam.py -x -q` | ❌ W0 | ⬜ pending |
| 24-02-T3 | 24-02 | 2 | SCORE-16 | — | capApplied band field retired→tallyFinal across all 3 lockstep locations (analysis.ts ↔ models.py ↔ contract.md §4) + result.tsx consumer migrated to deductionBreakdown.final (OBJECT) | unit | `cd app && npx tsc --noEmit` + `grep -L capApplied app/src/types/analysis.ts docs/contract.md` | ❌ W0 | ⬜ pending |
| 24-02-T4 | 24-02 | 2 | SCORE-10, SCORE-16, SCORE-09 | T-24-05, T-24-06, T-24-10 | math-determinism; baseline_kind name-match test; score-not-deviation regression (HIGH-3a); criteria_for_fault routing at the seam (split-not-leg / grip-coverage-gap — HIGH-1); gemini-silent<100 (Phase 20 preserved); coach-gate band-free continuity (eligible_for_coach fires moderate/major, NOT minor/none — HIGH-6a); Mode3/toggle preserved; ALL FOUR broken caller test files migrated band-free (test_vision_veto + test_pipeline_vision_gate + test_pipeline_mode3 + test_gemini_vision_scorer — HIGH-5a broadened); repo-wide `rg apply_downward_cap|SEVERITY_CAP|capApplied|cap_applied` == 0 in live code/tests | integration | `cd backend && python -m pytest tests/test_pipeline_deduction_seam.py -x -q && python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 24-03-T1 | 24-03 | 3 | SCORE-16, SCORE-09 | T-24-07, T-24-11 | objectivity; traceability unified signed-negative formula + numeric baselineValue + fallback record passes (HIGH-2a/MEDIUM-1a); determinism scoped honest (math+criterion-selection); monotonicity given fixed criterion set; phase18 verdict/margin asserts retired; phase18 generalization ARTIFACT-GATED (runs only vs real phase24_breakdowns.json, SKIPPED if absent — HIGH-4) + STRUCTURAL not numeric ≥95 (MEDIUM-1); sensitivity deferred; gate command does NOT mask nonzero exit (MEDIUM-3a — bare `python evals/phase24/assert_gates.py`) | gate | `cd backend && python evals/phase24/assert_gates.py` | ❌ W0 | ⬜ pending |
| 24-03-T2 | 24-03 | 3 | SCORE-16 | T-24-07 | gates catch planted violations; fallback-record traceability passes (MEDIUM-1a); structural generalization (same-criterion shortfall direction, no ≥95 bound — MEDIUM-1) + artifact-absent SKIPPED tested (HIGH-4) | unit | `cd backend && python -m pytest tests/test_phase24_gates.py -x -q` | ❌ W0 | ⬜ pending |
| 24-03-T3 | 24-03 | 3 | SCORE-09 | T-24-08, T-24-09 | serial-only Pod sweep; fresh layer/Pod; generates+commits phase24_breakdowns.json (HIGH-4); numeric ≥95 is an OBSERVATION not a fail-gate (MEDIUM-1) | manual (Pod-serial) | `python backend/scripts/sweep_phase15.py --pair-sequential` then `python backend/evals/phase24/assert_gates.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_deduction_engine.py` — traceability + monotonicity + determinism + router-selection + fallback-record + body-relative-baseline + reach-direction + line/leg-no-double-count unit gates for the new engine
- [ ] Replace case-by-case band asserts in `backend/evals/phase18/assert_baseline.py` with the pod-free traceability/monotonicity/determinism gates (generalization artifact-gated)
- [ ] Existing pytest infrastructure (`backend/tests/`) covers unit needs — no framework install

*Planner refines against the engine module names it mints.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generalization (real Phase-24 breakdown artifact + unseen + above-cutoff sensitivity set) | ND-07 generalization gate | Requires Pod GPU + serial sweep; the phase24_breakdowns.json artifact does not exist until the Pod run (HIGH-4); sensitivity set collection deferred | Run `backend/scripts/sweep_phase15.py --pair-sequential` on Pod, generate+commit `backend/evals/phase24/baseline/phase24_breakdowns.json`, then run `python backend/evals/phase24/assert_gates.py` (now the structural generalization check runs against the real artifact). Confirm coach (정은지) ≈95-100 emerges as an OBSERVATION (not a pure-gate bound — MEDIUM-1) and faults show a strictly larger same-criterion shortfall than their success pair (structural) without bands; kip-up=floor only when named; cold re-run criterion selection identical |

*Pure synthetic gates are automated; the phase18 generalization gate runs only against the Pod-generated artifact; the unseen sensitivity set is Pod-serial deferred.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
</content>
