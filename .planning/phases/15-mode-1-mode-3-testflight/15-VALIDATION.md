---
phase: 15
slug: mode-1-mode-3-testflight
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-17
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **This phase is validation-by-evidence, not unit-test-driven.** The "tests" are real-E2E sweeps producing Firestore evidence docs asserted against the locked 08.1 baseline (mirrors 08.1's evidence-doc pattern). See `15-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest ≥8,<9 (`backend/requirements-dev.txt`) |
| **Framework (app)** | None — `tsc --noEmit` only (`app/package.json` `typecheck`). No JS test runner (existing convention). |
| **Config file** | `backend/tests/conftest.py`; no app test config |
| **Quick run command** | `PYTHONPATH=backend/shared/python python3 -m pytest backend/tests/phase15 -x` (if any unit asserts added) |
| **Full suite command** | `PYTHONPATH=backend/shared/python python3 -m pytest backend/tests -q` + `cd app && npm run typecheck` |
| **Estimated runtime** | backend suite ~minutes; real E2E sweep gated on live Pod (GPU, minutes/video) |

---

## Sampling Rate

- **After every task commit:** Run quick backend suite if the task touched pure Python (assert scripts, filename normalization). Operational tasks (Pod restart, env sync, EAS build) are verified by their own CLI evidence.
- **After every plan wave:** Full backend suite + `tsc --noEmit`.
- **Before `/gsd-verify-work`:** Backend suite green + real-E2E evidence docs present + belle device handoff PASS.
- **Max feedback latency:** backend asserts < 120s; real-E2E gated on Pod (not latency-bound).

---

## Per-Task Verification Map

> Plan task IDs assigned by planner. Verification TYPE per requirement is locked here.

| Requirement | Behavior | Verify Type | Automated / Evidence Command |
|-------------|----------|-------------|------------------------------|
| MODE-01 | Mode 1 real E2E across 11 refs, expert-grade score | integration (real Pod sweep) | upload+sweep → Firestore docs → assert score reflects quality, not 위양성 |
| MODE-02 | Mode 3 session delta on same-user pair | integration (real E2E pair) | pair sweep → `deltaFromPrevious[dim]` present + sign correct |
| SCORE-04 | 위양성: 정은지 success=high+low-severity / fail=fault-caught, not high | integration + assert vs frozen baseline | compare run severity/score to `08.1-SWEEP-EVIDENCE.md` (no re-calibrate) |
| DELIV-01 | Guest completes Mode 1+3 on real device, video plays | manual (device, belle) | EAS preview build → device → belle handoff (CONTEXT D-09) |

*Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] **Sweep variant for non-`reference/` S3 keys** — `sweep_phase8_1.py` assumes `reference/{name}.mp4` source keys; Phase 15 dataset (6 success/fail pairs from `~/Downloads/정은지 선수 추가 영상/`) needs an upload-then-sweep step (Claude's discretion, CONTEXT D-05).
- [ ] **Mode-1 / 위양성 evidence assertion script** — compares new run severity/score to frozen `08.1-SWEEP-EVIDENCE.md` thresholds; evidence-doc style, no threshold re-calibration ([[calibration-source-hard-gate]]).
- [ ] **Reference field-presence check** — verify 11 `reference/{motionId}` docs carry downstream fields (forceDirectionPattern, bodyComparisonSourcePose, bodyNormalizationProfile, EXTEND profile) before Mode-1 sweep (RESEARCH open question A1 — `reference-downstream-backfill.json` untracked).
- [ ] No app test framework — rely on `tsc --noEmit` + manual device verification (existing convention).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Guest Mode 1+3 device completion + video playback | DELIV-01 | Requires physical iOS device + TestFlight build; only a human can confirm tap-flow + playback | Claude ships EAS preview build (env-fixed) + verifies build/submit PASS → belle installs via TestFlight → completes Mode 1 + Mode 3 as anonymous guest → confirms result video plays. Handoff only after Claude-side PASS (CONTEXT D-09). |
| Score "expert-grade specificity" judgment | MODE-01 / SCORE-04 | Whether a score "reflects quality" is partly qualitative | Claude asserts numeric/severity against baseline; belle eyeballs that the report reads as expert-level (not generic). No human SCORE labeling as ground truth ([[analysis-objectivity-no-human-scores]]). |

---

## Validation Sign-Off

- [ ] Every requirement has a verify type assigned (integration evidence or manual-device)
- [ ] Wave 0 covers the 3 MISSING tooling gaps (sweep variant, evidence assert, ref field-presence)
- [ ] 위양성 gate asserts against FROZEN 08.1 baseline — no re-calibration
- [ ] Real-E2E gated on live Pod (Claude runs Pod ops)
- [ ] Device verification is belle-only, post Claude-side PASS
- [ ] `nyquist_compliant: true` set after planner maps task IDs

**Approval:** pending
