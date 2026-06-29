---
phase: 10
slug: injury-risk-flags
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-29
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `10-RESEARCH.md` §Validation Architecture. The headline gate is **elite (정은지) posture-alone → zero flags** (no-false-positive).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| **Config file** | `backend/tests/conftest.py` (no pytest.ini; phase dirs `backend/tests/phaseNN/`) |
| **Quick run command** | `python -m pytest backend/tests/phase10 -x -q` |
| **Full suite command** | `python -m pytest backend/tests -q` |
| **App static gate** | `cd app && npm run typecheck` (tsc --noEmit) — only app gate; covers the `SafetyFlag` 3-mirror addition |
| **Estimated runtime** | ~10 seconds (phase10 quick); full backend suite ~minutes |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/phase10 -x -q` (+ `cd app && npm run typecheck` for contract/UI tasks)
- **After every plan wave:** Run `python -m pytest backend/tests -q` (full backend — guards no regression in `force_signals`/`dimensions`/`assemble`)
- **Before `/gsd-verify-work`:** Full backend suite green + `npm run typecheck` green
- **Max feedback latency:** ~10 seconds (phase10 quick run)

---

## Per-Task Verification Map

| Req | Behavior | Threat Ref | Test Type | Automated Command | File Exists | Status |
|-----|----------|------------|-----------|-------------------|-------------|--------|
| SAFE-01 / D-02 | **Elite no-FP:** 정은지 reference angles + all-`low` control-loss → **zero flags** | T-tampering | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py::test_elite_posture_alone_no_flag -x` | ❌ W0 | ⬜ pending |
| SAFE-01 / D-02 | Posture met AND control-loss → flag; posture met + no control-loss → no flag | — | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py -x` | ❌ W0 | ⬜ pending |
| D-05 | Cross-product: synthetic flexed knee → no flag; synthetic reverse-bend knee + control-loss → flag | — | unit | `pytest backend/tests/phase10/test_safety_flags_hyperextension.py -x` | ❌ W0 | ⬜ pending |
| D-03 | student_LR >> ref_LR (+control-loss) → asymmetry flag; equal asymmetry → none (reference-anchored) | — | unit | `pytest backend/tests/phase10/test_safety_flags_asymmetry.py -x` | ❌ W0 | ⬜ pending |
| D-06 | Mode1 advanced ref × beginner experience (+control-loss) → level_mismatch; same in Mode3 → no flag (mode1-only) | T-tampering (experience spoof) | unit | `pytest backend/tests/phase10/test_safety_flags_level.py -x` | ❌ W0 | ⬜ pending |
| SAFE-01 contract | `result["safetyFlags"]` scalar-only; `_validate_safety_flags` rejects nested list | T-firestore-nested-array | unit | `pytest backend/tests/phase10/test_safety_flags_contract.py -x` | ❌ W0 | ⬜ pending |
| SAFE-01 determinism | Same input → identical flags (LLM-free, D-01) | — | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py::test_deterministic -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase10/__init__.py` — new phase test package (no Phase-10 tests exist yet)
- [ ] The 7 test files mapped above (`test_safety_flags_firing_rule.py`, `_hyperextension.py`, `_asymmetry.py`, `_level.py`, `_contract.py`)
- [ ] Shared fixture: 정은지 reference angle matrix + low control-loss `ForceSignalsReport` (the **elite-no-FP** fixture). Reuse the success/fail pair dataset ([[jeongeunji-success-fail-pair-dataset]]) as a **known-answer regression set, NOT a fit target** ([[calibration-source-hard-gate]] — no 13-video curve-fit)
- [ ] Synthetic hyperextension fixtures: hand-built `(T,17,4)` arrays for flexed vs reverse-bent knee/elbow (avoids needing real injury videos; keeps thresholds literature-sourced)
- No framework install needed (pytest present).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Amber warning section renders on result screen, distinct from white cards + neutral `AccuracyLimitBadge`, with possibility-only + expert-referral copy | SAFE-01 / D-08 | RN visual rendering not covered by typecheck; requires device/simulator | Run app, open a result with ≥1 active SafetyFlag, confirm amber section appears after score gauge, before "동작 비교"; confirm no "안전합니다" reassurance when no flags |

*App static gate (`npm run typecheck`) covers the contract type addition; visual render is the only manual item.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
