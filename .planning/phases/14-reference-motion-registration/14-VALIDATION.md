---
phase: 14
slug: reference-motion-registration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-15
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `14-RESEARCH.md` § Validation Architecture. Per-task rows are filled in by the planner once PLAN.md task IDs exist.

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
- **Before `/gsd-verify-work`:** Full suite must be green + manual Firestore read of all 11 references (4 fields each) + belle visual spot-check before any active flip.
- **Max feedback latency:** ~30 seconds (per-task quick run)

---

## Success Criterion → Validation Map

| SC | Behavior | Test Type | Automated Command / Check | File Exists |
|----|----------|-----------|---------------------------|-------------|
| SC#1 | All 11 references appear in Mode 1 list | integration | seeder `--verify` reads all 11 + `referenceMotions.ts normalize()` returns 11; `cd app && npm run typecheck` | ❌ Wave 0 |
| SC#2 (presence) | Each reference has meanAngles + EXTEND + BodyNormalizationProfile + ForceDirectionPattern | integration | post-seed Firestore read asserts 4 fields present + non-empty for all 11 | ❌ Wave 0 |
| SC#2 (compute = student path, D-01) | Backfill outputs equal student `_process` downstream outputs | unit | pytest: feed fixture `pose_frames`/`angles` to backfill helper AND to `_process` downstream calls; assert identical dataclasses | ❌ Wave 0 |
| SC#3 | Multi-angle capture guide documented | manual | review `docs/` markdown deliverable contains 촬영 조건·앵글·시점 수 | manual |
| SC#4 | Single-view graceful + low confidence | unit | pytest: vertical-fallback `line=None` → force contact metrics return None + `pole_line_missing` warning (no crash); confidence flag set | ❌ Wave 0 |
| D-02 verdict | Stored-sufficient vs hybrid correctness | unit | pytest: assert `measure_body_profile`/`compute_force_signals` fail/NaN on reconstructed-from-flat data (proves HYBRID); assert EXTEND/meanAngles match from `angles` alone (STORED-SUFFICIENT) | ❌ Wave 0 |

---

## Per-Task Verification Map

> Populated by the planner from PLAN.md task IDs. Each task maps to a row above (SC + command). Constraint: no 3 consecutive tasks without an automated verify.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {planner-filled} | — | — | REF-01 | — | — | — | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_reference_backfill.py` — covers SC#2 (compute equals student path), SC#4 (single-view graceful), D-02 verdict assertions
- [ ] Firestore-read audit task (no GPU): list which of 11 references already have a body profile (resolves open question A2)
- [ ] Extend seeder `--verify` to assert the 4 new fields on all 11 references
- [ ] Capture-guide markdown skeleton (SC#3)
- [ ] Pod env fail-fast check at backfill start (rtmlib/imageio/boto3 import)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-angle capture guide is complete + reproducible | REF-01 (SC#3) | Documentation deliverable, no executable assertion | Review `docs/` markdown: must specify 촬영 조건, 앵글, 시점 수 such that registration accuracy is reproducible |
| Active-version flip after backfill | REF-01 | belle approves production state change ([[pod-ops-claude-runs]]) | belle visual spot-check of backfilled fields before any flip; Claude never flips active without approval |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
