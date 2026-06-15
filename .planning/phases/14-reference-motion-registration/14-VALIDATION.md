---
phase: 14
slug: reference-motion-registration
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-15
revised: 2026-06-15
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `14-RESEARCH.md` § Validation Architecture. Per-task rows filled in by the planner.
> Revised 2026-06-15 to incorporate the Codex direct-plan review (14-DIRECT-REVIEW.md): R1 stored-angle
> source + angle-delta/hash gate, R2 reference-v1 pinned config + env-flip divergence, R3 complete/repair/
> overwrite seed split, R4 pre/post active-pose hash JSON gate, R5 11-id all-or-nothing seed, R6 helper
> call-boundary parity.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend); app gate = `tsc --noEmit` |
| **Config file** | none committed (no pytest.ini); tests under `backend/tests/` |
| **Quick run command** | `cd backend && python -m pytest tests/test_reference_backfill.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q` |
| **App gate** | `cd app && npm run typecheck` |
| **Estimated runtime** | ~30 seconds (backend unit suite) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_reference_backfill.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -q` + `cd app && npm run typecheck`
- **Before `/gsd-verify-work`:** Full suite green + pre/post active-pose hash JSON summary (unchangedActivePoseCount==11) + manual Firestore read of all 11 references (4 fields each) + belle visual spot-check before any active flip.
- **Max feedback latency:** ~30 seconds (per-task quick run)

---

## Success Criterion → Validation Map

| SC | Behavior | Test Type | Automated Command / Check | File Exists |
|----|----------|-----------|---------------------------|-------------|
| SC#1 | All 11 references appear in Mode 1 list | integration | seeder `--verify` reads all 11 + `referenceMotions.ts normalize()` returns 11; `cd app && npm run typecheck` | ✅ 14-01 (TS), 14-02 (seeder), 14-03 (run) |
| SC#2 (presence) | Each reference has meanAngles + EXTEND + BodyNormalizationProfile + ForceDirectionPattern | integration | post-seed Firestore read asserts `completeDownstreamFieldCount==11` (4 fields + captureViews present + non-empty for all 11) | ✅ 14-03 (verify-read) |
| SC#2 (compute = reference-v1 pinned config, D-01/R2) | Backfill outputs equal `_process` downstream outputs under REFERENCE_V1_FORCE_CONFIG (recognizer=Fallback, technique_profile=None, preflight_label_gate_passed=None, layer-2 off) — provably exact FOR THAT CONFIG, NOT "student path exact"; plus an env-flip test proving the result CHANGES under preflight=True | unit | pytest: fixture `pose_frames` + STORED `angles` + injected `pole_axis_measurement` to backfill helper AND `_process` downstream calls under REFERENCE_V1_FORCE_CONFIG → identical dataclasses; second assertion with `preflight_label_gate_passed=True` differs | ✅ 14-01 (RED+env-flip) → 14-02 (GREEN) |
| SC#2 (R1 angle integrity) | meanAngles/EXTEND sourced from STORED phase4_v1 angles; re-run angles validation-only with a hash + delta gate | unit + run | pytest: `meanAnglesSource=="reference.phase4_v1.angles"` + `techniqueProfileSource=="reference.phase4_v1.angles"`; run: storedAnglesHash/rerunAnglesHash/anglesFrames recorded, `anglesFrames==len(pose_frames)`, `maxAngleDelta<=1.0 deg` OR seed aborted | ✅ 14-02 (helper) / 14-03 (run gate) |
| SC#3 | Multi-angle capture guide documented | manual | review `docs/reference-capture-guide.md` contains 촬영 조건·앵글·시점 수 | ✅ 14-02 |
| SC#4 | Single-view graceful + low confidence | unit | pytest: vertical-fallback `line=None` → contact metrics None + `pole_line_missing` warning (no crash); captureViews=1 flag | ✅ 14-01 |
| D-02 verdict | Stored-sufficient vs hybrid correctness | unit | pytest: `measure_body_profile`/`compute_force_signals` diverge on reconstructed-from-flat data (HYBRID); EXTEND/meanAngles match from `angles` alone (STORED-SUFFICIENT) | ✅ 14-01 |
| R4 active-pose integrity | active phase4_v1 joints3d/angles/activeVersion provably unchanged | integration | `snapshot_reference_active_pose.mjs --mode post` JSON summary: `unchangedActivePoseCount==11`, `changedActivePoseCount==0` (byte-level sha256, not a prose assertion) | ✅ 14-03 |
| R5 all-or-nothing | seeding is all-or-nothing on 11 ids | integration | backfill exits non-zero + no fixture if failures>0/len!=11/NaN-inf; seeder rejects real-run unless fixture has exactly 11 ids; run summary `seededMotionCount==11` | ✅ 14-02 (script+seeder) / 14-03 (run) |

---

## Per-Task Verification Map

> Constraint: no 3 consecutive tasks without an automated verify. (14-03 Task 2 is the sole human-check; preceded by 14-03 Task 1 automated + the wave-merge full suite.)

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-T1 | 14-01 | 1 | REF-01 | T-14-01, T-14-03 | Read-only audit; keys-not-values; zero `set(`; prints completeRequiredSet count (feeds R3) | integration | `node --check app/scripts/audit-reference-fields.mjs` + grep 11 IDs + grep `set(`==0 | ✅ | ⬜ pending |
| 14-01-T2 | 14-01 | 1 | REF-01 | — | Single temporal_fill; no fabricated findings; reference-v1 pinned-config parity (REFERENCE_V1_FORCE_CONFIG, injected pole_axis_measurement+angles, R6) + env-flip divergence test (R2) | unit | `cd backend && python -m pytest tests/test_reference_backfill.py -q` | ✅ | ⬜ pending |
| 14-01-T3 | 14-01 | 1 | REF-01 | T-14-02 | Optional/nullable fields; 3-way (or 4-way if Python mirror found via R8 recheck) lockstep; no T-scaled array | unit (typecheck) | `cd app && npm run typecheck` + grep contract/TS fields | ✅ | ⬜ pending |
| 14-02-T1 | 14-02 | 2 | REF-01 | T-14-04, T-14-05, T-14-13 | meanAngles/EXTEND from STORED phase4_v1 angles (R1); ONE RTMW re-inference for live-frame fields only; stored-vs-rerun hash+delta gate (epsilon 1.0 deg); No Firestore write; never overwrite active pose; pins REFERENCE_V1_FORCE_CONFIG (preflight=None/technique=None) — provably exact for that config, NOT student-path-exact (R2) | unit | `cd backend && python -m pytest tests/test_reference_backfill.py -x -q` + `--help` exit 0 | ✅ | ⬜ pending |
| 14-02-T2 | 14-02 | 2 | REF-01 | T-14-06, T-14-07 | ADD-only merge; nested-array reject; no active flip; dry-run-first; skip only when ALL Phase-14 required fields valid; repair-missing default; complete/repair/overwrite split (R3); 11-id all-or-nothing real-run (R5) | unit | `node --check seed-reference-downstream.mjs` + import `update_reference_downstream_data` | ✅ | ⬜ pending |
| 14-02-T3 | 14-02 | 2 | REF-01 | — | No emoji; doc deliverable | manual/grep | `grep 촬영 조건 / 앵글 / 시점 docs/reference-capture-guide.md` | ✅ | ⬜ pending |
| 14-03-T1 | 14-03 | 3 | REF-01 | T-14-08..12, T-14-14 | Commit-push-before-Pod; Pod /health ABORT GATE (STOP if not ok — no CPU NaN run); pre/post byte-level active-pose hash gate (R4, unchangedActivePoseCount==11); all-or-nothing seed (R5); ADD-only; rollback runbook + risk-response table; no secrets in log | integration | `node --check` both snapshot+rollback scripts; grep `unchangedActivePoseCount` + `completeDownstreamFieldCount` + `health` in 14-BACKFILL-RUN.md; seeder `--verify`; full suite | ✅ | ⬜ pending |
| 14-03-T2 | 14-03 | 3 | REF-01 | T-14-09 | belle approval before any production state change; no flip; pre/post hash summary reviewed | manual (human-check) | belle reviews verify-read table + hash summary + spot-check | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements (folded into Plan 14-01, Wave 1)

> Phase 14 has no separate Wave 0; the Wave-0 audit/test/contract scaffolding is Plan 14-01 (the first wave). All compute (14-02) and run (14-03) depend on it.

- [x] `backend/tests/test_reference_backfill.py` — SC#2 reference-v1 pinned-config parity (REFERENCE_V1_FORCE_CONFIG, RED target) + env-flip divergence test (R2), SC#4 graceful, D-02 verdict → **14-01 T2**
- [x] Firestore-read audit (no GPU): which of 11 have a body profile (A2) + completeRequiredSet count (feeds R3) → **14-01 T1**
- [x] Extend seeder `--verify` to assert the 4 new fields on all 11; complete/repair/overwrite split (R3); 11-id all-or-nothing (R5) → **14-02 T2** (seeder) / **14-03 T1** (run)
- [x] Capture-guide markdown skeleton (SC#3) → **14-02 T3**
- [x] Pod env fail-fast check at backfill start (rtmlib/imageio/boto3/firebase-admin) + Pod /health abort gate → **14-02 T1** (in script) / **14-03 T1** (at run)
- [x] Pre/post active-pose hash snapshot scripts + rollback runbook (R4) → **14-03 T1** (snapshot_reference_active_pose.mjs + rollback_reference_downstream.mjs)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-angle capture guide is complete + reproducible | REF-01 (SC#3) | Documentation deliverable, no executable assertion | Review `docs/reference-capture-guide.md`: must specify 촬영 조건, 앵글, 시점 수 such that registration accuracy is reproducible |
| belle visual spot-check of backfilled fields | REF-01 | belle approves production state ([[pod-ops-claude-runs]]) | 14-03 Task 2: review 11-motion verify-read table + pre/post hash summary (unchangedActivePoseCount==11) + sane-value spot-check before any flip; Claude never flips active without approval |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (14-03 T2 is the single human-check, preceded by automated 14-03 T1 + wave full suite)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (audit + backfill cover all 11)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned (revised per 14-DIRECT-REVIEW.md — R1–R8 folded)
</content>
