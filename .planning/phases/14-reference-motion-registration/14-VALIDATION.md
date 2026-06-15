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
> Revised 2026-06-15 (iteration 2) per 14-DIRECT-REVIEW-ITERATION2.md: R2-1 restore-aware rollback +
> broadened Phase-14-state snapshot, R2-2 Node scripts moved to app/scripts, R2-3 Pod --check-firestore
> credential gate, R2-4 referenceMotions.ts normalize() field surfacing, R2-5 seedPayload/diagnostics
> fixture split, R2-6 JSON-summary gate (not markdown grep), R2-7 14-03 requirements:[REF-01] restored.
> Revised 2026-06-15 (iteration 3) per 14-DIRECT-REVIEW-ITERATION3.md: R3-1 forceDirectionPattern uses the
> scoped _validate_force_pattern_inference (not the generic flat validator) in the helper + JS seeder +
> 14-01 fixtures (valid findings[].warnings accepted / nested-or-unknown rejected); R3-2 --check-firestore
> extended to an all-11 cheap metadata gate (no S3/RTMW) so non-ref-climb completeness fails fast.
> Revised 2026-06-15 (iteration 4) per 14-DIRECT-REVIEW-ITERATION4.md: R4-1 the D-01 parity RED-target
> import is env-gated on PHASE14_REQUIRE_BACKFILL_HELPER (importorskip when unset, hard-fail-on-missing
> when =1) and 14-02's BOTH pytest gates run with PHASE14_REQUIRE_BACKFILL_HELPER=1 + assert no skipped
> tests, so a skipped D-01 parity can no longer pass the automated gate; R4-2 the reference force fields
> are pinned to motion_id=None (forceMotionIdSource='fallback_profile_motion_id', forceMotionId=null) and
> a parity assertion + REFERENCE_V1_FORCE_CONFIG record + Phase-15 caveat make that fallback/null choice
> machine-checkable.

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
- **Before `/gsd-verify-work`:** Full suite green + the 14-BACKFILL-RUN-SUMMARY.json Node assertion (unchangedActivePoseCount==11) + manual Firestore read of all 11 references (4 fields each) + belle visual spot-check before any active flip.
- **Max feedback latency:** ~30 seconds (per-task quick run)

---

## Success Criterion → Validation Map

| SC | Behavior | Test Type | Automated Command / Check | File Exists |
|----|----------|-----------|---------------------------|-------------|
| SC#1 | All 11 references appear in Mode 1 list | integration | seeder `--verify` reads all 11 + `referenceMotions.ts normalize()` returns 11 AND surfaces the new fields (R2-4); `cd app && npm run typecheck` | ✅ 14-01 (TS + normalize), 14-02 (seeder), 14-03 (run) |
| SC#2 (presence) | Each reference has meanAngles + EXTEND + BodyNormalizationProfile + ForceDirectionPattern | integration | post-seed Firestore read asserts `completeDownstreamFieldCount==11` (4 fields + captureViews present + non-empty for all 11) via 14-BACKFILL-RUN-SUMMARY.json | ✅ 14-03 (verify-read + JSON summary) |
| SC#2 (compute = reference-v1 pinned config, D-01/R2/R4-1/R4-2) | Backfill outputs equal `_process` downstream outputs under REFERENCE_V1_FORCE_CONFIG (recognizer=Fallback, technique_profile=None, preflight_label_gate_passed=None, layer-2 off, motion_id=None) — provably exact FOR THAT CONFIG, NOT "student path exact"; plus an env-flip test proving the result CHANGES under preflight=True; the parity RED-target is env-gated (R4-1) and 14-02 runs it with PHASE14_REQUIRE_BACKFILL_HELPER=1 + no-skipped so it cannot silently SKIP | unit | pytest: fixture `pose_frames` + STORED `angles` + injected `pole_axis_measurement` to backfill helper AND `_process` downstream calls under REFERENCE_V1_FORCE_CONFIG (motion_id=None into compute_force_signals + infer_force_direction_pattern, R4-2) → identical dataclasses; second assertion with `preflight_label_gate_passed=True` differs; 14-02 gate: `PHASE14_REQUIRE_BACKFILL_HELPER=1 pytest -x -q` then `! grep -qi skipped` (R4-1) | ✅ 14-01 (env-gated RED+env-flip+motion_id) → 14-02 (GREEN, strict) |
| SC#2 (R1 angle integrity) | meanAngles/EXTEND sourced from STORED phase4_v1 angles; re-run angles validation-only with a hash + delta gate | unit + run | pytest: `meanAnglesSource=="reference.phase4_v1.angles"` + `techniqueProfileSource=="reference.phase4_v1.angles"` (in diagnostics); run: storedAnglesHash/rerunAnglesHash/anglesFrames recorded, `anglesFrames==len(pose_frames)`, `maxAngleDelta<=1.0 deg` OR seed aborted | ✅ 14-02 (helper) / 14-03 (run gate) |
| SC#3 | Multi-angle capture guide documented | manual | review `docs/reference-capture-guide.md` contains 촬영 조건·앵글·시점 수 | ✅ 14-02 |
| SC#4 | Single-view graceful + low confidence | unit | pytest: vertical-fallback `line=None` → contact metrics None + `pole_line_missing` warning (no crash); captureViews=1 flag | ✅ 14-01 |
| D-02 verdict | Stored-sufficient vs hybrid correctness | unit | pytest: `measure_body_profile`/`compute_force_signals` diverge on reconstructed-from-flat data (HYBRID); EXTEND/meanAngles match from `angles` alone (STORED-SUFFICIENT) | ✅ 14-01 |
| R2-3/R3-2 Pod Firestore gate (all-11 metadata) | Pod credential + all-11 completeness verified before S3/RTMW | run | `python backend/scripts/backfill_reference_downstream.py --check-firestore --motions <all 11 explicitly>` exits 0 (reads activeVersion+angles+anglesJointKeys+anglesFrames + frame-count sanity for EACH of the 11 via auth._ensure_firebase, NO S3/RTMW) before any S3 work; ANY incomplete doc → STOP naming the motion | ✅ 14-02 (mode) / 14-03 (run gate) |
| R2-4 normalize() surfacing | new fields not stripped by the hook | unit (typecheck+grep) | `cd app && npm run typecheck` + grep `referenceMotions.ts normalize()` returns bodyNormalizationProfile/techniqueProfile/forceDirectionPattern/captureViews | ✅ 14-01 |
| R2-5 fixture split | seedPayload seeded, diagnostics never seeded | unit (grep) | backfill emits `seedPayload` + `diagnostics`; seeder reads only `seedPayload`; forceSignalsReportSummary lives only in diagnostics (grep both scripts) | ✅ 14-02 |
| R3-1 forceDirectionPattern scoped validator | the reference mirror validates forceDirectionPattern with the scoped force-pattern validator, NOT the generic flat validator (which would reject a valid findings[].warnings:string[]) | unit | pytest: `_validate_force_pattern_inference` accepts `findings[0].warnings=["axis_signal_unavailable"]`, rejects `findings[0].warnings=[["nested"]]` / unknown finding key; helper applies it to forceDirectionPattern + generic flat validator to meanAngles/techniqueProfile/bodyNormalizationProfile; JS seeder mirrors the scoped rules | ✅ 14-01 (fixtures) / 14-02 (helper + seeder) |
| R4-1 strict skip gate | a skipped D-01 parity test can no longer pass the automated gate once the helper exists | unit | 14-01 parity/env-flip import is env-gated on `PHASE14_REQUIRE_BACKFILL_HELPER` (importorskip unset / hard-fail-on-missing when =1); 14-02 BOTH pytest gates run `PHASE14_REQUIRE_BACKFILL_HELPER=1 python -m pytest tests/test_reference_backfill.py -x -q` piped through `tee` + `! grep -qi "skipped"` | ✅ 14-01 (env-gated test) / 14-02 (strict gate, T1+T2) |
| R4-2 motion_id=null force-config | reference force fields are produced with motion_id=None (fallback/null), the known-reference contact/boost does NOT fire, and the choice is machine-checked | unit | pytest: parity reference passes `motion_id=None` into `compute_force_signals` + `infer_force_direction_pattern`, asserts `FallbackRecognizer().recognize(angles).motion_id is None`; helper records `forceMotionIdSource="fallback_profile_motion_id"` + `forceMotionId=null` in REFERENCE_V1_FORCE_CONFIG + diagnostics; capture-guide notes Phase 15 must not assume selected-referenceMotionId force semantics | ✅ 14-01 (assertion) / 14-02 (helper + diagnostics + guide) |
| R4/R2-6 active-pose integrity | active phase4_v1 joints3d/angles/activeVersion provably unchanged, gated on JSON | integration | `snapshot-reference-phase14-state.mjs --mode post` writes 14-BACKFILL-RUN-SUMMARY.json; Node assertion: `unchangedActivePoseCount==11`, `changedActivePoseCount==0` (byte-level sha256, asserted on JSON not a markdown grep) | ✅ 14-03 |
| R2-1 restore-aware rollback | pre-seed snapshot captures full Phase-14 field state; rollback restores/deletes | integration | snapshot records {present, valueHash, value?} for all Phase-14 fields incl. bodyNormalizationProfile/bodyComparisonSourcePose; rollback deletes absent-before, restores present-before; never touches active pose (`node --check` + grep zero active-pose write) | ✅ 14-03 |
| R5 all-or-nothing | seeding is all-or-nothing on 11 ids | integration | backfill exits non-zero + no fixture if failures>0/len(seedPayload)!=11/NaN-inf; seeder rejects real-run unless seedPayload has exactly 11 ids; JSON summary `seededMotionCount==11` | ✅ 14-02 (script+seeder) / 14-03 (run) |

---

## Per-Task Verification Map

> Constraint: no 3 consecutive tasks without an automated verify. (14-03 Task 2 is the sole human-check; preceded by 14-03 Task 1 automated + the wave-merge full suite.)

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-T1 | 14-01 | 1 | REF-01 | T-14-01, T-14-03 | Read-only audit; keys-not-values; zero `set(`; prints completeRequiredSet count (feeds R3) | integration | `node --check app/scripts/audit-reference-fields.mjs` + grep 11 IDs + grep `set(`==0 | ✅ | ⬜ pending |
| 14-01-T2 | 14-01 | 1 | REF-01 | T-14-18, T-14-19 | Single temporal_fill; no fabricated findings; reference-v1 pinned-config parity (REFERENCE_V1_FORCE_CONFIG, injected pole_axis_measurement+angles, R6) + env-flip divergence test (R2) + R3-1 forceDirectionPattern scoped-validator fixtures (valid findings[].warnings accepted / nested-or-unknown rejected); parity RED-target import env-gated on PHASE14_REQUIRE_BACKFILL_HELPER (R4-1); motion_id=None parity (compute_force_signals + infer_force_direction_pattern, FallbackRecognizer profile motion_id None) + REFERENCE_V1_FORCE_CONFIG forceMotionId=null (R4-2) | unit | `cd backend && python -m pytest tests/test_reference_backfill.py -q` (unset → parity skips; `PHASE14_REQUIRE_BACKFILL_HELPER=1` → strict in 14-02) | ✅ | ⬜ pending |
| 14-01-T3 | 14-01 | 1 | REF-01 | T-14-02 | Optional/nullable fields; 3-way (or 4-way if Python mirror found via R8 recheck) lockstep; normalize() surfaces the new fields (R2-4); no T-scaled array | unit (typecheck) | `cd app && npm run typecheck` + grep contract/TS fields + grep normalize() surfaces 4 fields | ✅ | ⬜ pending |
| 14-02-T1 | 14-02 | 2 | REF-01 | T-14-04, T-14-05, T-14-13, T-14-15, T-14-19 | --check-firestore gate before S3/RTMW (R2-3, auth._ensure_firebase not hand-rolled cert; all-11 cheap metadata completeness check, no S3/RTMW — R3-2); meanAngles/EXTEND from STORED phase4_v1 angles (R1); ONE RTMW re-inference for live-frame fields only; stored-vs-rerun hash+delta gate (epsilon 1.0 deg); split seedPayload/diagnostics fixture (R2-5); No Firestore write; never overwrite active pose; pins REFERENCE_V1_FORCE_CONFIG (preflight=None/technique=None/motion_id=None) — provably exact for that config, NOT student-path-exact (R2); reference force motion_id=None fallback/null recorded in config + diagnostics (R4-2); pytest gate runs with PHASE14_REQUIRE_BACKFILL_HELPER=1 + no-skipped (R4-1) | unit | `cd backend && PHASE14_REQUIRE_BACKFILL_HELPER=1 python -m pytest tests/test_reference_backfill.py -x -q \| tee /tmp/phase14-pytest-t1.txt \| grep -E passed\|error` + `! grep -qi skipped /tmp/phase14-pytest-t1.txt` + `--help` exit 0 + grep `check-firestore` + grep `seedPayload` | ✅ | ⬜ pending |
| 14-02-T2 | 14-02 | 2 | REF-01 | T-14-06, T-14-07, T-14-18, T-14-19 | Seeder reads only seedPayload (R2-5); ADD-only merge; helper applies scoped `_validate_force_pattern_inference` to forceDirectionPattern + generic flat validator to the other three dicts, seeder mirrors the scoped rules (R3-1); nested-array reject on the flat dicts; no active flip; dry-run-first; skip only when ALL Phase-14 required fields valid; repair-missing default; complete/repair/overwrite split (R3); 11-id all-or-nothing real-run (R5); pytest gate runs with PHASE14_REQUIRE_BACKFILL_HELPER=1 + no-skipped so D-01 parity cannot SKIP (R4-1) | unit | `node --check seed-reference-downstream.mjs` + grep `seedPayload` + import `update_reference_downstream_data` + `PHASE14_REQUIRE_BACKFILL_HELPER=1` pytest R3-1+parity fixtures + `! grep -qi skipped` | ✅ | ⬜ pending |
| 14-02-T3 | 14-02 | 2 | REF-01 | — | No emoji; doc deliverable | manual/grep | `grep 촬영 조건 / 앵글 / 시점 docs/reference-capture-guide.md` | ✅ | ⬜ pending |
| 14-03-T1 | 14-03 | 3 | REF-01 | T-14-08..12, T-14-14, T-14-16, T-14-17 | Commit-push-before-Pod; Pod /health ABORT GATE (STOP if not ok — no CPU NaN run); Pod --check-firestore gate (all 11 IDs, cheap metadata, no S3/RTMW) before S3/RTMW (R2-3, R3-2); broadened pre/post Phase-14-state snapshot under app/scripts (R2-1/R2-2); JSON-summary gate (R2-6, unchangedActivePoseCount==11) not markdown grep; all-or-nothing seed (R5); ADD-only; RESTORE-aware rollback runbook + risk-response table; no secrets in log | integration | `node --check` both snapshot+rollback scripts (via `cd app`); JSON assertion on 14-BACKFILL-RUN-SUMMARY.json; grep `health` in 14-BACKFILL-RUN.md; seeder `--verify`; full suite | ✅ | ⬜ pending |
| 14-03-T2 | 14-03 | 3 | REF-01 | T-14-09 | belle approval before any production state change; no flip; pre/post hash JSON summary reviewed | manual (human-check) | belle reviews verify-read table + JSON summary + spot-check | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements (folded into Plan 14-01, Wave 1)

> Phase 14 has no separate Wave 0; the Wave-0 audit/test/contract scaffolding is Plan 14-01 (the first wave). All compute (14-02) and run (14-03) depend on it.

- [x] `backend/tests/test_reference_backfill.py` — SC#2 reference-v1 pinned-config parity (REFERENCE_V1_FORCE_CONFIG, RED target) + env-flip divergence test (R2), SC#4 graceful, D-02 verdict → **14-01 T2**
- [x] Firestore-read audit (no GPU): which of 11 have a body profile (A2) + completeRequiredSet count (feeds R3) → **14-01 T1**
- [x] `referenceMotions.ts normalize()` surfaces the new fields so the hook does not strip them (R2-4) → **14-01 T3**
- [x] Extend seeder `--verify` to assert the 4 new fields on all 11; reads only seedPayload (R2-5); complete/repair/overwrite split (R3); 11-id all-or-nothing (R5) → **14-02 T2** (seeder) / **14-03 T1** (run)
- [x] Capture-guide markdown skeleton (SC#3) → **14-02 T3**
- [x] Pod env fail-fast check at backfill start (rtmlib/imageio/boto3/firebase-admin) + Pod /health abort gate + Pod --check-firestore all-11 cheap-metadata credential/completeness gate (R2-3, R3-2) → **14-02 T1** (in script) / **14-03 T1** (at run)
- [x] Pre/post Phase-14-state hash snapshot scripts (broadened, app/scripts) + RESTORE-aware rollback runbook (R2-1/R2-2) → **14-03 T1** (snapshot-reference-phase14-state.mjs + rollback-reference-downstream.mjs)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-angle capture guide is complete + reproducible | REF-01 (SC#3) | Documentation deliverable, no executable assertion | Review `docs/reference-capture-guide.md`: must specify 촬영 조건, 앵글, 시점 수 such that registration accuracy is reproducible |
| belle visual spot-check of backfilled fields | REF-01 | belle approves production state ([[pod-ops-claude-runs]]) | 14-03 Task 2: review 11-motion verify-read table + 14-BACKFILL-RUN-SUMMARY.json (unchangedActivePoseCount==11) + sane-value spot-check before any flip; Claude never flips active without approval |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (14-03 T2 is the single human-check, preceded by automated 14-03 T1 + wave full suite)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (audit + backfill cover all 11)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned (revised per 14-DIRECT-REVIEW.md R1–R8 + 14-DIRECT-REVIEW-ITERATION2.md R2-1–R2-7 + 14-DIRECT-REVIEW-ITERATION3.md R3-1/R3-2 + 14-DIRECT-REVIEW-ITERATION4.md R4-1/R4-2 folded)
