# Phase 15 — Plan Check (Pre-Execution Verification)

**Checked:** 2026-06-17
**Plans:** 15-01..15-05 (5 plans, 3 waves)
**Verdict:** PASSED with WARNINGS (no BLOCKERs)

This is an OPERATIONAL VALIDATION phase — every capability is already built (RESEARCH verified file:line). Verification focuses on whether the plans prove the goal on real video/device, not on missing implementation.

---

## Coverage Matrix (SC + Requirement → Task)

| SC / Req | Owning Plan·Task | Checkable Acceptance | Status |
|----------|------------------|----------------------|--------|
| SC1 / MODE-01 (Mode 1 expert score, 11 ref) | 15-03 T1 (field verify) + T2 (real E2E MODE_EXPERT, referenceMotionId lockstep) | server_error 0, overallScore+dimensionScores recorded, line non-None | COVERED |
| SC2 / MODE-02 (Mode 3 session delta) | 15-04 T1 (fail→success same-uid MODE_SELF pair → deltaFromPrevious) | delta present, abs-metric diff, sign = improvement, not %-match headline | COVERED |
| SC3 / SCORE-04 (위양성 gate) | 15-01 T2 (assert tool) + 15-03 T3 (assert vs FROZEN 08.1, success=low / fail=fault-caught) | sha256 == c94bb8 hard-gate, no recalibrate | COVERED |
| SC4 (diverse video, crash-free, consistent) | partial: 15-03 (6 fail + 7 success E2E, server_error 0) + 15-05 device | no explicit "consistent/crash-free across diverse set" assert | PARTIAL (W-1) |
| SC5 / DELIV-01 (TestFlight guest device) | 15-05 T1 (eas env fix) + T2 (build/submit Claude PASS) + checkpoint (belle device) | preview.env assert, build crash 0, verify-before-handoff | COVERED |

All 4 requirement IDs (MODE-01, MODE-02, SCORE-04, DELIV-01) appear in plan `requirements` frontmatter and map to concrete tasks. No requirement dropped.

---

## Critical-Path Ordering (dead Pod / creds)

- Wave 1: 15-01 (pure tools, autonomous) ‖ 15-02 (Pod bring-up + Lambda env sync, autonomous:false, belle checkpoint).
- Wave 2: 15-03, 15-04 both `depends_on: ["15-01","15-02"]` → gated on live Pod. No real-E2E can run against the 404 Pod. CORRECT.
- Wave 3: 15-05 `depends_on: ["15-03","15-04"]` → device build only after backend E2E green. CORRECT.
- Lambda env sync (15-02 T2) explicitly switches to `sunity-motion` creds (sunity-api = AccessDenied). Pitfall 2 addressed.

Dependency graph: acyclic, no forward/missing refs, wave numbers consistent with depends_on. PASS.

---

## Focused Checks (per verification_focus)

1. **위양성 gate integrity** — 15-01 T2 + 15-03 T3 assert against FROZEN `tilt_thresholds.yaml` sha256 `c94bb8…e87c`; hard-gate non-zero exit on drift; `grep` for `calibrate_tilt_thresholds` import = 0 in acceptance. No Phase-15 re-derivation. PASS (D-02 / calibration-source-hard-gate honored).
2. **Mode 3 mechanism** — 15-04 T1 submits fail (prev) then success (cur) as TWO MODE_SELF docs under the SAME throwaway uid so `get_previous_analysis(mode=MODE_SELF)` + `build_mode3.deltaFromPrevious` fire. Mechanism is correctly specified, not assumed. PASS.
3. **DELIV-01 handoff** — 15-05 is autonomous:false; Claude fixes eas preview env + runs build/submit + confirms PASS; belle checkpoint is gate="blocking" AFTER Claude-side PASS. No unverified build handed to belle. PASS (D-09 / verify-before-handoff).
4. **Open question A1** — 15-03 T1 runs `backfill_reference_downstream.py --check-firestore` over the explicit 11 IDs (5-subset default avoided) and backfills if missing, BEFORE the Mode-1 sweep. Field-presence verified, not assumed. PASS.
5. **Objectivity** — All plans use success/fail input labels only; `분석결과/*.md` never used as ground-truth score. D-06 hard-guard present in every relevant task + threat register. PASS.
6. **Operational realism** — Pod create (15-02 checkpoint) and device test (15-05 checkpoint) correctly autonomous:false / human-action. Scriptable tools (15-01) autonomous:true. PASS.

**Factual cross-checks performed:**
- 11 canonical motion IDs (`ALL_MOTION_IDS` in `backfill_reference_downstream.py`) match 15-03 T1's hardcoded `--motions` list exactly.
- `--check-firestore` mode exists in the backfill script (line 797).
- Dataset confirmed present: 6 fail + 7 success videos at `~/Downloads/정은지 선수 추가 영상/`; double-extension typo `pdshape-correct.mp4  .mp4` is real and 15-01 T3 handles it; fail-name Korean→slug mapping matches actual filenames.

---

## WARNINGS (should fix, execution may proceed)

### W-1 [requirement_coverage] SC4 ("다양한 영상 크래시 없이 일관") has no explicit assert
- Plans: 15-03 / 15-05
- SC4 demands consistent, crash-free analysis across diverse videos. 15-03 runs 13 videos through `_process` but its acceptance only asserts `server_error 0` per Mode-1 success run + per-pair completion. There is no consolidated "all N videos completed without crash / tracking failure (no_human / not_pole_motion anomalies)" evidence line, and SC4's robustness is otherwise implicitly delegated to the single belle device run.
- Fix: Add an acceptance line to 15-03 (or 15-04) that records a crash/failure tally across the full 13-video sweep (completed vs no_human/not_pole_motion/server_error) into the evidence doc, so SC4 is observable, not inferred. (Deferred bulk stress-set is correctly out of scope per CONTEXT — this only needs the existing 13 to report consistency.)

### W-2 [task_completeness] Several Wave-2/3 `<verify>` automated commands are dry-run/pytest proxies, not the real-E2E gate
- Plans: 15-03 T2/T3, 15-04 T1
- The real assertions (Mode-1 score, 위양성 PASS, deltaFromPrevious sign) are produced by GPU sweeps recorded in evidence .md, but the machine-checkable `<verify>` blocks run `--dry-run` or unrelated pytest (`-k "mode3 or assemble"`). This is acceptable for a Pod-gated phase (the plans state evidence lives in the doc), but it means task "green" from the automated verify does NOT prove the requirement — a verifier could mark these PASS on dry-run alone.
- Fix: Make the evidence-doc PASS table the explicit completion gate in each task's `<done>` (already partially present) and ensure `/gsd-verify-work` keys on the evidence tables, not the dry-run exit. No plan restructure required.

### W-3 [assumption] A3 (Gemini/Cerebras key validity) gates D-03 but has no fallback branch if BOTH fail
- Plans: 15-02 T2, 15-04 T2
- D-12 allows graceful degrade (one side drop → cross-fill = PASS), but D-03 requires at least one REAL LLM call to succeed. If both SSM keys are unfunded/invalid (A3 = LOW confidence, unverified this session), the gate cannot be met and the plans have no escalation step — execution would stall mid-wave.
- Fix: Add an early key-liveness check in 15-02 (one real recognizer/coach call during bring-up already exists — make "both-fail → escalate to belle for key refresh" an explicit branch rather than a silent stall).

---

## INFO

- 15-04 T1 fail→success ordering assumes the fail run is submitted first so it becomes "previous". The plan states this; ensure the sweep driver preserves submission order per pair (sequential, not parallel) or get_previous_analysis may pick the wrong prior. Worth a one-line note in execution.
- combo.mp4 correctly scoped Mode-1-only (no pair), consistent with Deferred.

---

## Verdict

No BLOCKERs. The plans correctly sequence the dead-Pod / creds critical path, freeze the 위양성 baseline (no recalibration), implement the real Mode-3 two-doc mechanism, verify reference fields before relying on them, honor objectivity, and enforce verify-before-handoff for the device build. Three WARNINGS (SC4 consistency assert, evidence-vs-dry-run gating clarity, both-LLM-fail escalation) should be addressed but do not block execution.

