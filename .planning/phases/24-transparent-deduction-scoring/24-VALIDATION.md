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
> Source: 24-RESEARCH.md "## Validation Architecture" (4 ND-07 gates: traceability / monotonicity / determinism / generalization).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| **Config file** | none — tests under `backend/tests/` |
| **Quick run command** | `cd backend && python -m pytest tests/ -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q && python evals/phase18/assert_baseline.py` |
| **Estimated runtime** | ~30 seconds (pure unit) / Pod-serial eval separate |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -q`
- **After every plan wave:** Run full unit suite
- **Before `/gsd-verify-work`:** Pure-first gates (traceability / monotonicity / determinism) green; Pod-serial generalization gate run once with GPU
- **Max feedback latency:** 30 seconds (pure); Pod eval is out-of-band serial

---

## Per-Task Verification Map

> Planner fills this from PLAN.md tasks. The 4 ND-07 gates are pure-first (numpy, no GPU) then Pod-serial sampling per RESEARCH Validation Architecture.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 24-01-T1 | 24-01 | 1 | SCORE-16, SCORE-12 | T-24-01 | contract lockstep; criteria config validated, no final ceiling | unit | `cd backend && python -m pytest tests/test_deduction_engine.py -k "contract or criteria or lockstep" -x -q` + `cd app && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 24-01-T2 | 24-01 | 1 | SCORE-10, SCORE-11, SCORE-12, SCORE-13, SCORE-14, SCORE-15 | T-24-01, T-24-02, T-24-03 | NaN-safe; severity not in arithmetic; coverage-gap not a band | unit | `cd backend && python -m pytest tests/test_deduction_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 24-01-T3 | 24-01 | 1 | SCORE-10..16 | T-24-01 | V5 input validation via deviation guards | unit | `cd backend && python -m pytest tests/test_deduction_engine.py -x -q && python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 24-02-T1 | 24-02 | 2 | SCORE-10 | — | band code removed; helpers preserved | unit | `cd backend && python -c "from sunity_shared.analysis import vision_veto; assert not hasattr(vision_veto,'apply_downward_cap')"` | ❌ W0 | ⬜ pending |
| 24-02-T2 | 24-02 | 2 | SCORE-10, SCORE-13, SCORE-15, SCORE-16 | T-24-04, T-24-05, T-24-06 | nested-array validator; no silent no-op (WARNING+audit) | unit/integration | `cd backend && python -m pytest tests/test_pipeline_deduction_seam.py -x -q` | ❌ W0 | ⬜ pending |
| 24-02-T3 | 24-02 | 2 | SCORE-10, SCORE-16, SCORE-09 | T-24-05, T-24-06 | determinism; Mode3/toggle preserved | integration | `cd backend && python -m pytest tests/test_pipeline_deduction_seam.py -x -q && python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 24-03-T1 | 24-03 | 3 | SCORE-16, SCORE-09 | T-24-07 | objectivity; sensitivity honestly deferred | gate | `cd backend && python evals/phase24/assert_gates.py` | ❌ W0 | ⬜ pending |
| 24-03-T2 | 24-03 | 3 | SCORE-16 | T-24-07 | gates catch planted violations | unit | `cd backend && python -m pytest tests/test_phase24_gates.py -x -q` | ❌ W0 | ⬜ pending |
| 24-03-T3 | 24-03 | 3 | SCORE-09 | T-24-08, T-24-09 | serial-only Pod sweep; fresh layer/Pod | manual (Pod-serial) | `python backend/scripts/sweep_phase15.py --pair-sequential` then `python backend/evals/phase24/assert_gates.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_deduction_tally.py` — traceability + monotonicity + determinism unit gates for the new engine
- [ ] Replace case-by-case band asserts in `backend/evals/phase18/assert_baseline.py` with traceability/monotonicity gates
- [ ] Existing pytest infrastructure (`backend/tests/`) covers unit needs — no framework install

*Planner refines against the engine module names it mints.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generalization (unseen + above-cutoff sensitivity set) | ND-07 generalization gate | Requires Pod GPU + serial sweep; sensitivity set collection deferred | Run `backend/scripts/sweep_phase15.py --pair-sequential` on Pod, confirm coach (정은지) ≈95-100 emerges as a RESULT and faults still deduct without bands |

*Pure gates are automated; generalization gate is Pod-serial.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
