# Phase 12 — Plan Check Iter-5 (Decision)

**Verifier:** gsd-plan-checker
**Date:** 2026-06-10
**Iter:** 5 (after iter-4 BLOCKED in commit 3373ce5)
**Plans:** 12-00, 12-01, 12-02, 12-03

---

## Decision: BLOCKED (1 residual blocker)

Iter-4 closed **3 of 3 blockers + 1 of 1 warning** in the main planning surface, but **B3 patch is incomplete in VALIDATION.md** (residual half-patch — same family as the original B3 finding).

---

## Iter-4 Finding Closure Status

| Finding | Iter-4 Severity | Iter-5 Status | Evidence |
|---|---|---|---|
| **B1** raw_visibility ghost field | BLOCKER | **CLOSED** | `grep raw_visibility` in 12-01-PLAN.md returns 0. Only match is 12-CONTEXT.md L343 which is the explicit clarifying note ("raw_visibility 는 Landmark2D 별개") — intentional, not a contradiction. |
| **B2** T3 task body missing | BLOCKER | **CLOSED** | 12-01-PLAN.md L330 `<task id="T3" type="auto" tdd="true">` with full action: 5 files (seed_reference_motions.py + seed-reference-motions.mjs + analysis.ts + referenceMotions.ts + test_reference_keypoint_report_seed.py), 5 sub-steps including TS interface + frontend null-guard + Node script + Python script + pipeline mode1 mirror + 4 unit tests. <verify> automated block present. |
| **B3** axisMask field 9 vs 10 schema half-patch | BLOCKER | **PARTIAL — RESIDUAL** | 12-01-PLAN.md: all sites say "10 필드" (L141, L202-205, L221-222, L242, L247, L273, L300, L323, L455). BUT 12-VALIDATION.md L41 (SC #3) + L65 (D-12-E2) still say "9 필드 incl. axisData per R2/R10". This is a residual half-patch in the verification-seed artifact — the same root failure mode as the iter-4 B3 finding. |
| **W1** UI-SPEC L507 emoji in 한정 예외 | WARNING | **CLOSED** | UI-SPEC L502-512 contains only formal `❌` anti-pattern list markers (pre-existing). 💬/🎓 emoji in 한정 예외 guidance line 0 occurrences. L512 explicitly mandates "footer/모달/카드 어디든 0 emoji". |
| **W2** UI-SPEC §5 KeypointOverlay props wrong contract | WARNING | **CLOSED** | UI-SPEC L246-258: Wave 1 props block = `videoSize / keypointReport / frameIndex / visible / jointAngles / deltaThresholdDeg` matching 12-02 Wave 1 T1 contract exactly. Wave 2 확장 note added (referenceKeypointReport split + R10 polling + useEvent 공존). Frame 동기화 §5 also rewritten (L294-296). axisMask polyline branching산식 added at L265. |

---

## NEW Findings (Introduced in Iter-5 Patch)

### B3-residual (BLOCKER) — VALIDATION.md 9 필드 half-patch

**Location:** `.planning/phases/12-realmeasurement-keypoint/12-VALIDATION.md`

**Lines:**
- L41 (SC #3 row): `Wave 0B T1 (single atomic commit per D-09-U1 mirror — 9 필드 incl. axisData per R2/R10)`
- L65 (D-12-E2 row): `Wave 0B T1 (3-way contract lockstep + KeypointReport 9 필드 incl. axisData R10)`

**Why blocker:** The verifier reads VALIDATION.md as the Nyquist task-ID source of truth at Phase 12 close-out. If VALIDATION says "9 필드" but PLAN says "10 필드", the gate at L20 (`test_keypoint_report_lockstep.py` — "10 필드 incl. axis_data + axis_mask") will pass while the SC #3 + D-12-E2 acceptance criteria still mandate "9 필드" — the verifier will record contradictory PASS/FAIL signals. This is the exact same half-patch failure mode as the original iter-4 B3 (header said axisMask, dataclass/validator/TS/normalize/docs/tests all said 9 필드/NaN sentinel).

**Fix:** Replace "9 필드" → "10 필드" at VALIDATION.md L41 and L65. Trivial 2-line patch.

---

## Goal-Backward SC Trace (4/4)

| SC | Plans | Status |
|---|---|---|
| **SC #1** result angleGuide = real currentAngle | 12-00 T2 (kismam wiring 3 site) + 12-02 T4 (enrichJoints sim removal) | Covered |
| **SC #2** "현재 N° → 기준 M°" per joint | 12-02 T4 (영역 5 각도 가이드) + 12-00 T2 (targetSource mode 분기) | Covered |
| **SC #3** 3-way data contract lockstep | 12-01 T1 single atomic commit (10 필드 in plan body — but VALIDATION L41 still 9 필드 → residual) | **Blocked by B3-residual** |
| **SC #4** 영상 위 어깨/골반/무릎/손 + axis polyline | 12-00 T4 (compute_axis_frames) + 12-01 T1 (axisData/axisMask) + 12-02 T1 (KeypointOverlay) + 12-03 T1 (useEvent sync) | Covered |

---

## Summary

3 of 3 iter-4 blockers + both warnings substantively closed in the main plan files. T3 task body, axisMask schema in 12-01, props contract in UI-SPEC §5, emoji removal at L507 — all verified.

One residual contradiction remains in 12-VALIDATION.md (L41 + L65, "9 필드") — same half-patch failure mode as original B3 finding, just in a different artifact. 2-line edit closes it.

Recommend trivial patch round (1 commit, replace "9 필드" → "10 필드" at 2 sites in VALIDATION.md) before commit + execute.

