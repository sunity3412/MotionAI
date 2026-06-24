---
phase: 24
slug: transparent-deduction-scoring
status: draft
nyquist_compliant: false
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
| TBD | TBD | TBD | SCORE-09.. | — | N/A (internal math) | unit | `python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |

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
