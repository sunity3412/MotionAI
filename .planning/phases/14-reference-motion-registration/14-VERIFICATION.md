---
phase: 14-reference-motion-registration
verified: 2026-06-15T15:10:00Z
status: passed
score: 8/8 must-have truths verified (roadmap SC 4/4)
overrides_applied: 0
re_verification:
  previous_status: null
  note: "Initial verification — no prior VERIFICATION.md"
---

# Phase 14: 정은지 기준 모션 등록 (다각도 캡처 가이드) Verification Report

**Phase Goal:** 기존 11개 정은지 reference 가 meanAngles · EXTEND(techniqueProfile) · BodyNormalizationProfile · ForceDirectionPattern · captureViews 를 모두 갖추게 만들고, Mode 1 비교가 학생과 동일한 sunity_shared 함수를 reference-v1 pinned config(REFERENCE_V1_FORCE_CONFIG)로 거쳐 동작하도록 한다.
**Verified:** 2026-06-15T15:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                              | Status     | Evidence                                                                                                                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | All 11 references carry meanAngles + techniqueProfile + bodyNormalizationProfile + forceDirectionPattern + captureViews (SC#2) | ✓ VERIFIED | `14-BACKFILL-RUN-SUMMARY.json` `completeDownstreamFieldCount=11`; perMotion[] all 11 show every field `true`; verify-read table (RUN.md L53-65) 11/11 Y. Helper `update_reference_downstream_data` (firestore_admin.py:949) writes exactly these 5 fields. |
| 2   | Firestore verify-read confirms the 4 new fields present + non-empty for all 11 (SC#1/SC#2)                       | ✓ VERIFIED | Seeder `--verify` + `audit-reference-fields.mjs` → completeRequiredSet 11/11 (RUN.md L34-35); orchestrator-confirmed audit read-back (activeVersion 11/11). |
| 3   | check-firestore all-11 credential/read gate runs before any S3/RTMW (R2-3/R3-2)                                  | ✓ VERIFIED | `_run_check_firestore` (backfill L343) reads via `auth._ensure_firebase()`, verifies activeVersion+angles+anglesJointKeys+anglesFrames + frame-count for all 11, exits before S3/RTMW. RUN.md L20-24 records PASS with per-motion frame counts. |
| 4   | Active phase4_v1 joints3d/angles/activeVersion provably unchanged via byte-level sha256 (D-02/R4)                | ✓ VERIFIED | `14-BACKFILL-RUN-SUMMARY.json` `unchangedActivePoseCount=11, changedActivePoseCount=0`; `snapshot-reference-phase14-state.mjs` hashes ACTIVE_POSE_FIELDS and exits 1 on any valueHash diff (L190-211). |
| 5   | All-or-nothing seeding: completeDownstreamFieldCount==11 AND seededMotionCount==11 (R5)                          | ✓ VERIFIED | Gate JSON asserts both =11. Backfill exits non-zero + emits no fixture if failures>0 OR len!=11 (L709-714); seeder rejects real-run unless exactly 11 ids (L302-313). |
| 6   | RESTORE-aware pre/post snapshot + rollback (field absent→delete, field present→restore; active pose untouched) (R2-1) | ✓ VERIFIED | `rollback-reference-downstream.mjs` plans delete vs restore per `{present, value}` snapshot (L76-92); ACTIVE_POSE_FIELDS excluded (L41). `14-PRESEED-SNAPSHOT.json` present (restore values captured). |
| 7   | belle visually spot-checks backfilled fields before any production state change (no active flip)                | ✓ VERIFIED | belle approved Task 2 checkpoint:human-verify 2026-06-15 (14-03-SUMMARY.md L1, L44). In-app detail review explicitly deferred by belle to follow-up (Phase 15 scope). |
| 8   | Backfill computes via SAME sunity_shared fns under REFERENCE_V1_FORCE_CONFIG (motion_id=None), D-01 parity provably exact (D-01/R1/R2/R4-2) | ✓ VERIFIED | `compute_reference_downstream` (backfill L228) calls `measure_body_profile`, `FallbackRecognizer().recognize`, `compute_force_signals`, `infer_force_direction_pattern` with `motion_id=None`/`technique_profile=None`. pytest `PHASE14_REQUIRE_BACKFILL_HELPER=1` → 9 passed, 0 skipped (D-01 parity GREEN). |

**Score:** 8/8 truths verified

### Roadmap Success Criteria Coverage

| SC  | Criterion                                                                       | Status     | Evidence                                                            |
| --- | ------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------ |
| 1   | 등록 모션이 `reference/{motionId}` 저장 + 앱 Mode 1 목록에 나타남                | ✓ VERIFIED | 11 references pre-existing in `reference/{id}`; normalize() surfaces all fields for the Mode 1 hook (referenceMotions.ts L187-192). (No NEW capture in this phase — scope is backfill of existing 11, per CONTEXT D-01~D-05.) |
| 2   | meanAngles · EXTEND · BodyNormalizationProfile · ForceDirectionPattern 포함     | ✓ VERIFIED | Truth #1 — gate JSON 11/11 all fields true.                        |
| 3   | 다각도 캡처 가이드(촬영 조건·앵글·시점 수) 문서화                                | ✓ VERIFIED | `docs/reference-capture-guide.md` (129 lines): §1 시점 수, §2 앵글, §3 촬영 조건. |
| 4   | 단일 시점도 graceful + confidence 낮게 표기                                      | ✓ VERIFIED | captureViews=1 baseline for all 11; guide L11-19 + L16 low-confidence flag policy; `test_sc4_single_view_graceful` passes. |

### Required Artifacts

| Artifact                                                          | Expected                                  | Status     | Details                                              |
| ----------------------------------------------------------------- | ----------------------------------------- | ---------- | ---------------------------------------------------- |
| `backend/scripts/backfill_reference_downstream.py`                | Pod orchestrator, compute_reference_downstream | ✓ VERIFIED | 822 lines; contains compute_reference_downstream, check-firestore gate, integrity gate, all-or-nothing. |
| `app/scripts/seed-reference-downstream.mjs`                       | ADD-only merge seeder, 11-id all-or-nothing | ✓ VERIFIED | 443 lines; seedPayload-only, merge:true, complete/repair/overwrite split, 11-id guard. |
| `app/scripts/snapshot-reference-phase14-state.mjs`                | byte-level active-pose hash + field state | ✓ VERIFIED | 266 lines; sha256 ACTIVE_POSE_FIELDS, exit 1 on change. |
| `app/scripts/rollback-reference-downstream.mjs`                   | RESTORE-aware rollback                    | ✓ VERIFIED | 144 lines; delete-absent / restore-present, active pose excluded. |
| `app/scripts/audit-reference-fields.mjs`                          | Read-only 11-doc audit                    | ✓ VERIFIED | 150 lines; read-only.                                |
| `backend/shared/python/sunity_shared/firestore_admin.py`          | update_reference_downstream_data helper   | ✓ VERIFIED | def at L949; ADD-only merge:true, no joints3d/angles/activeVersion, scoped + generic validators. |
| `backend/tests/test_reference_backfill.py`                        | Wave-0 parity/env-flip/validator harness  | ✓ VERIFIED | 425 lines; 9 tests, 9 passed 0 skipped under strict gate. |
| `docs/reference-capture-guide.md`                                 | SC#3 capture guide                        | ✓ VERIFIED | 129 lines.                                           |
| `docs/contract.md` / `app/src/types/analysis.ts`                  | 3-way contract lockstep                   | ✓ VERIFIED | contract §3 L127-131 + analysis.ts ReferenceMotion L398-468 declare all 5 fields. |
| `14-BACKFILL-RUN.md` / `14-BACKFILL-RUN-SUMMARY.json`             | Run log + machine gate                    | ✓ VERIFIED | Gate JSON asserts all 4 sentinel counts; RUN.md documents full sequence + deviations + runbook. |

### Key Link Verification

| From                                  | To                                                       | Via                                              | Status   | Details                                                                                          |
| ------------------------------------- | -------------------------------------------------------- | ------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------ |
| backfill_reference_downstream.py      | sunity_shared.analysis (4 fns)                           | same fns, REFERENCE_V1_FORCE_CONFIG, motion_id=None | ✓ WIRED  | grep confirms measure_body_profile/compute_force_signals/infer_force_direction_pattern/FallbackRecognizer at L253-313. |
| backfill_reference_downstream.py      | reference/{id}.phase4_v1.angles (stored active)          | Firestore read + reshape; meanAngles/EXTEND source | ✓ WIRED  | techniqueProfile + meanAngles derived from STORED angles arg (L276-282), not re-run angles (R1).  |
| seed-reference-downstream.mjs         | Firestore reference/{motionId}                           | batch.set(merge:true)                            | ✓ WIRED  | seedPayload-only merge; RUN.md L33 repairMissing=11, batch.commit OK, no activeVersion flip.      |
| referenceMotions.ts normalize()       | analysis.ts ReferenceMotion                              | normalize() surfaces new optional fields         | ✓ WIRED  | All 5 fields returned (L187-192), null-safe; no longer stripped (R2-4).                          |
| snapshot (pre)                        | snapshot (post)                                          | byte-level sha256 compare → gate JSON            | ✓ WIRED  | unchangedActivePoseCount=11 / changedActivePoseCount=0.                                            |
| test_reference_backfill.py            | backfill orchestrator + sunity_shared fns                | bare import via conftest sys.path                | ✓ WIRED  | conftest injects backend/scripts; 9/9 pass under PHASE14_REQUIRE_BACKFILL_HELPER=1.               |

### Behavioral Spot-Checks

| Behavior                                          | Command                                                                 | Result            | Status |
| ------------------------------------------------- | ----------------------------------------------------------------------- | ----------------- | ------ |
| D-01 parity test GREEN, no skip (R4-1 strict)     | `PHASE14_REQUIRE_BACKFILL_HELPER=1 pytest tests/test_reference_backfill.py -q` | 9 passed in 0.20s | ✓ PASS |
| Seeder syntax valid                               | `node --check seed-reference-downstream.mjs`                            | OK                | ✓ PASS |
| Snapshot syntax valid                             | `node --check snapshot-reference-phase14-state.mjs`                     | OK                | ✓ PASS |
| Rollback syntax valid                             | `node --check rollback-reference-downstream.mjs`                        | OK                | ✓ PASS |
| Audit syntax valid                                | `node --check audit-reference-fields.mjs`                               | OK                | ✓ PASS |
| Deviation commits exist                           | `git log --oneline 0129f3e 0f03781 ab6b265 635134a ccaee7a 1016c31`     | all present       | ✓ PASS |

Live Firestore write is a production effect already executed and independently confirmed by the orchestrator (audit read-back completeRequiredSet 11/11, activeVersion 11/11) — not re-run here.

### Requirements Coverage

| Requirement | Source Plan          | Description                                                                                     | Status      | Evidence                                                                                       |
| ----------- | -------------------- | ----------------------------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------- |
| REF-01      | 14-01, 14-02, 14-03  | 정은지 기준 모션 등록 + 비교 정확도 최대화(촬영 조건/앵글 통제 + BodyNormalizationProfile·EXTEND·ForceDirectionPattern 포함) | ✓ SATISFIED | All 11 references backfilled with the required downstream fields; capture guide documents 촬영/앵글 control; truths #1-#8 verified. REQUIREMENTS.md L72 still shows `[ ]` / L168 `Pending` — a doc-status update is warranted but does not block goal achievement. |

No orphaned requirements: REF-01 is the sole Phase 14 requirement and is claimed by all 3 plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER in any phase-modified file | — | Clean |

### Deviations Reviewed (sound, documented, not silent regressions)

1. **fps 9→18 (commit `0129f3e`):** Backfill re-inference extracts at REFERENCE_TARGET_FPS=18.0 to match how phase4_v1 was produced (reprocess `--target-fps 18.0`). Without it, frame counts mismatch (ref-climb stored 257 vs 9fps-rerun 172, ratio ≈18/9) and the integrity gate always aborts. Documented in code (backfill L131-138), RUN.md L41-44, 14-03-SUMMARY L31-32. The student(9fps)-vs-reference(18fps) Mode 1 alignment is explicitly deferred to Phase 15. SOUND.
2. **Robust integrity gate (commit `0f03781`):** Changed from MAX>1.0° to (meanAngleDelta>0.1° OR p99>1.0°) to tolerate RTMW single-frame nondeterminism (ref-combo 23.43°→0.193° across runs) while still blocking systematic pose-version shifts. Documented in code (L117-128, MEAN_EPSILON_DEG=0.1 / P99_EPSILON_DEG=1.0), RUN.md L46-49, 14-03-SUMMARY L34. Final run 11/11: max<0.5° / mean~0.0025° / p99 0.005° / over1deg=0. The relaxation is principled (transient spike vs systematic shift) and consistently affects students too. SOUND.

### Human Verification Required

None outstanding. The single planned `checkpoint:human-verify` (14-03-PLAN.md:211 — belle confirms the 11-motion verify-read table + active-pose-unchanged gate + spot-checked value sanity) was completed and APPROVED by belle on 2026-06-15 (14-03-SUMMARY L1/L44). belle deliberately deferred the in-app detail review to a follow-up; that is a Phase 15 (Mode 1 comparison) concern, not a Phase 14 goal gap.

### Gaps Summary

No gaps. The phase goal is achieved end-to-end:
- All 11 정은지 references now carry meanAngles + EXTEND(techniqueProfile) + BodyNormalizationProfile + ForceDirectionPattern + captureViews (gate JSON 11/11, verify-read table 11/11, audit read-back 11/11).
- The backfill runs the SAME sunity_shared functions _process uses, pinned to REFERENCE_V1_FORCE_CONFIG with motion_id=None — provably exact for that config (9/9 parity tests GREEN, 0 skips under the strict import gate), establishing the Mode 1 comparison path Phase 15 will consume.
- Active phase4_v1 pose is byte-level unchanged (unchanged=11/changed=0); seeding is all-or-nothing (seeded=11); rollback is restore-aware; active pose was never written.
- 3-way contract lockstep (contract.md §3 / analysis.ts / referenceMotions.ts normalize) is intact; the no-Python-mirror decision is correct (reference-api is a passthrough).
- SC#3 capture guide and SC#4 single-view graceful (captureViews=1 + low-confidence policy) are documented and tested.
- Both execution deviations (18fps, robust gate) are sound and fully documented.

Minor non-blocking note: `.planning/REQUIREMENTS.md` still marks REF-01 as `[ ]` / `Pending` (L72/L168). The implementation satisfies REF-01; this is a tracking-doc lag, not a goal gap.

---

_Verified: 2026-06-15T15:10:00Z_
_Verifier: Claude (gsd-verifier)_
