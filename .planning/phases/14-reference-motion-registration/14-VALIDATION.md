---
phase: 14
slug: reference-motion-registration
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-15
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `14-RESEARCH.md` § Validation Architecture. Per-task rows filled in by the planner.

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
- **Before `/gsd-verify-work`:** Full suite green + manual Firestore read of all 11 references (4 fields each) + belle visual spot-check before any active flip.
- **Max feedback latency:** ~30 seconds (per-task quick run)

---

## Success Criterion → Validation Map

| SC | Behavior | Test Type | Automated Command / Check | File Exists |
|----|----------|-----------|---------------------------|-------------|
| SC#1 | All 11 references appear in Mode 1 list | integration | seeder `--verify` reads all 11 + `referenceMotions.ts normalize()` returns 11; `cd app && npm run typecheck` | ✅ 14-01 (TS), 14-02 (seeder), 14-03 (run) |
| SC#2 (presence) | Each reference has meanAngles + EXTEND + BodyNormalizationProfile + ForceDirectionPattern | integration | post-seed Firestore read asserts 4 fields present + non-empty for all 11 | ✅ 14-03 (verify-read) |
| SC#2 (compute = student path, D-01) | Backfill outputs equal student `_process` downstream outputs, incl. the SAME pinned `preflight_label_gate_passed` value (provably exact, not default-equivalent) | unit | pytest: fixture `pose_frames`/`angles` to backfill helper AND `_process` downstream calls with `preflight_label_gate_passed=None` + `technique_profile=None`; identical dataclasses | ✅ 14-01 (RED) → 14-02 (GREEN) |
| SC#3 | Multi-angle capture guide documented | manual | review `docs/reference-capture-guide.md` contains 촬영 조건·앵글·시점 수 | ✅ 14-02 |
| SC#4 | Single-view graceful + low confidence | unit | pytest: vertical-fallback `line=None` → contact metrics None + `pole_line_missing` warning (no crash); captureViews=1 flag | ✅ 14-01 |
| D-02 verdict | Stored-sufficient vs hybrid correctness | unit | pytest: `measure_body_profile`/`compute_force_signals` diverge on reconstructed-from-flat data (HYBRID); EXTEND/meanAngles match from `angles` alone (STORED-SUFFICIENT) | ✅ 14-01 |

---

## Per-Task Verification Map

> Constraint: no 3 consecutive tasks without an automated verify. (14-03 Task 2 is the sole human-check; preceded by 14-03 Task 1 automated + the wave-merge full suite.)

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-T1 | 14-01 | 1 | REF-01 | T-14-01, T-14-03 | Read-only audit; keys-not-values; zero `set(` | integration | `node --check app/scripts/audit-reference-fields.mjs` + grep 11 IDs + grep `set(`==0 | ✅ | ⬜ pending |
| 14-01-T2 | 14-01 | 1 | REF-01 | — | Single temporal_fill; no fabricated findings; D-01 parity pins SAME `preflight_label_gate_passed`=None (provably exact) | unit | `cd backend && python -m pytest tests/test_reference_backfill.py -q` | ✅ | ⬜ pending |
| 14-01-T3 | 14-01 | 1 | REF-01 | T-14-02 | Optional/nullable fields; lockstep; no T-scaled array | unit (typecheck) | `cd app && npm run typecheck` + grep contract/TS fields | ✅ | ⬜ pending |
| 14-02-T1 | 14-02 | 2 | REF-01 | T-14-04, T-14-05 | No Firestore write; never overwrite active pose; keys-not-values; pins `preflight_label_gate_passed=None` + `technique_profile=None` (D-01 exact parity) | unit | `cd backend && python -m pytest tests/test_reference_backfill.py -x -q` + `--help` exit 0 | ✅ | ⬜ pending |
| 14-02-T2 | 14-02 | 2 | REF-01 | T-14-06, T-14-07 | ADD-only merge; nested-array reject; no active flip; dry-run-first | unit | `node --check seed-reference-downstream.mjs` + import `update_reference_downstream_data` | ✅ | ⬜ pending |
| 14-02-T3 | 14-02 | 2 | REF-01 | — | No emoji; doc deliverable | manual/grep | `grep 촬영 조건 / 앵글 / 시점 docs/reference-capture-guide.md` | ✅ | ⬜ pending |
| 14-03-T1 | 14-03 | 3 | REF-01 | T-14-08..12 | Commit-push-before-Pod; Pod /health ABORT GATE (STOP if not ok — no CPU NaN run); ADD-only; active pose read-only; distinct verify-read step; no secrets in log | integration | grep 11 IDs + `activeVersion` + `health` in 14-BACKFILL-RUN.md; seeder `--verify`; full suite | ✅ | ⬜ pending |
| 14-03-T2 | 14-03 | 3 | REF-01 | T-14-09 | belle approval before any production state change; no flip | manual (human-check) | belle reviews verify-read table + spot-check | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements (folded into Plan 14-01, Wave 1)

> Phase 14 has no separate Wave 0; the Wave-0 audit/test/contract scaffolding is Plan 14-01 (the first wave). All compute (14-02) and run (14-03) depend on it.

- [x] `backend/tests/test_reference_backfill.py` — SC#2 compute parity incl. pinned preflight-gate parity (RED target), SC#4 graceful, D-02 verdict → **14-01 T2**
- [x] Firestore-read audit (no GPU): which of 11 have a body profile (A2) → **14-01 T1**
- [x] Extend seeder `--verify` to assert the 4 new fields on all 11 → **14-02 T2** (seeder) / **14-03 T1** (run)
- [x] Capture-guide markdown skeleton (SC#3) → **14-02 T3**
- [x] Pod env fail-fast check at backfill start (rtmlib/imageio/boto3) + Pod /health abort gate → **14-02 T1** (in script) / **14-03 T1** (at run)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-angle capture guide is complete + reproducible | REF-01 (SC#3) | Documentation deliverable, no executable assertion | Review `docs/reference-capture-guide.md`: must specify 촬영 조건, 앵글, 시점 수 such that registration accuracy is reproducible |
| belle visual spot-check of backfilled fields | REF-01 | belle approves production state ([[pod-ops-claude-runs]]) | 14-03 Task 2: review 11-motion verify-read table + sane-value spot-check before any flip; Claude never flips active without approval |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (14-03 T2 is the single human-check, preceded by automated 14-03 T1 + wave full suite)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (audit + backfill cover all 11)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
