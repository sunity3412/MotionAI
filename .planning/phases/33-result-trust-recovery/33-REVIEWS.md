---
phase: 33
reviewers: [codex]
reviewed_at: 2026-07-23T10:10:48Z
plans_reviewed: [33-02, 33-03, 33-04, 33-05, 33-06, 33-07, 33-08, 33-09, 33-10, 33-11, 33-12, 33-13, 33-14, 33-15, 33-16]
note: "gemini/coderabbit/opencode/qwen/cursor not installed; claude skipped (self). Single external reviewer = codex (codex-cli 0.144.6). See RESUME memory codex-reviewer-smplx-bias — stack (RTMW) was pre-fenced in the prompt; codex did not push a stack change this run. All findings verified to be about plan release-mechanics, not stack."
---

# Cross-AI Plan Review — Phase 33 (result-trust-recovery, C+M3 substrate re-plan)

Reviewer: **codex** (codex-cli 0.144.6). Read-only review; git verified clean afterward (no edits).

## Codex Review

## Summary

The re-plan has the right conceptual spine—backup → isolated re-extraction → derived-data refresh → M3 → full verification → activation—and the presentation dependency graph has no obvious ordering hole. However, the current substrate plans do not yet provide a genuinely isolated staged release. In the current code, `--no-flip` writes to `versions/phase4_v1`, which is already the active version name; 33-04 reads old top-level data and does not write its output back; and 33-06 has no implemented way to test the staged version. Combined with an underspecified M3 change and a non-atomic data/code activation, these are release-blocking defects. Overall assessment: structurally strong, operationally unsafe until the substrate release mechanics are corrected.

## Strengths

- 33-02 → 33-07 follows the authoritative Task 0–5 order from D-27. Backup precedes planned writes, and 33-07 is blocked on 33-06.
- All presentation work is gated on 33-07, directly or transitively. I found no dependency path allowing 33-08+ to execute before substrate activation, satisfying D-28.
- D-20/D-29 are repeated consistently: tolerance, slope, cap, and calibration epsilons are explicitly pinned.
- 33-03, 33-06, 33-07, and 33-16 recognize Pod termination, GPU approval, serial execution, environment setup, and SSM/Lambda synchronization.
- The plans correctly demand artifact inspection rather than accepting code/test success alone: actual crops, analysis values, audio, and simulator output are opened.
- 33-02 includes dual-copy backup, completeness checks, frame-shape checks, and hashes.
- 33-06 uses margins rather than target score fitting and includes M8, safety flags, self-comparison, determinism, and threshold immutability.
- The RTMW choice remains fixed and appropriately out of scope.

## Concerns

- **HIGH — 33-03 does not create a truly staged version (D-31).** Current `reprocess_reference_motions_phase4.py` fixes `PIPELINE_VERSION = "phase4_v1"` and writes `reference/{id}/versions/phase4_v1`. The current production documents already report `activeVersion='phase4_v1'`. Therefore `--no-flip` overwrites the backing document named by the active pointer; it only avoids updating the top-level mirror. A consumer resolving `activeVersion` would see staged data prematurely, rollback loses the old `phase4_v1` version, and 33-07’s `activeVersion` proof is meaningless because the value does not change.

- **HIGH — 33-04 cannot perform the backfill described (D-27/D-31).** The current `backfill_reference_downstream.py` explicitly says `NEVER writes Firestore` and reads stored angles through top-level `get_reference_motion()`, which remains the old active data before 33-07. It outputs only a seed JSON for four derived fields plus `captureViews`; it does not merge seven fields into the staged version. `bodyComparisonSourcePose` has no concrete producer. `extract_reference_keypoint_reports.py` likewise writes a local JSON and currently defaults to five motions and 18 fps. As written, 33-04 can pass its grep checks while leaving the staged reference incomplete or deriving fields from the old reference.

- **HIGH — 33-06 cannot actually validate the staged reference.** `get_reference_motion()` and the production pipeline read the top-level reference document; there is no candidate-version resolver in `run_sweep.py`. “Point the sweep at the versioned reprocessed reference” is an intention, not an implemented mechanism. Thus 33-06 will either test the old production reference or require an undocumented temporary flip, violating D-31.

- **HIGH — M3 is underspecified and can leak into scoring behavior (33-05, D-20/D-29).** Changing segment selection legitimately changes deduction inputs even if the formula is unchanged. More seriously, `find_action_segment()` returns only a user `(start,end)` range. The proposed alternative “window the reference when `nu < nr`” cannot be represented by the current API without also carrying a reference range. A best-match reference window could remove difficult reference phases and systematically inflate scores. “Scoring files unchanged” does not prove alignment-only behavior.

- **HIGH — data, code, and environment are not activated as one release unit (33-05–33-07, D-31).** C+M3 is valid only as the tuple `{9fps reference, PR=1, M3 code, derived fields}`. The plan flips reference data but has no explicit deployment of the 33-05 M3 commit to the production Pod. Conversely, rollback lists data restoration and a later `git revert`, allowing unsafe intermediate combinations such as old 18fps data with new M3.

- **HIGH — warm-Pod reuse can run stale code (33-04/33-06/33-07, D-30).** The Pod is bootstrapped in 33-03, then local code changes occur in 33-04 and 33-05. 33-06 says to reuse the warm Pod if available but never synchronizes the new commit or restarts the Python process. The sweep may therefore run without the 9fps backfill change or M3 fix. `/health 200` proves liveness, not source revision or model/environment parity.

- **HIGH — the 11-document flip is non-atomic (33-07, D-31).** `_flip_active_pointer` updates documents sequentially and overwrites `versions/pre_phase4` on each rerun. A crash can leave a mixed reference library. The post-flip check analyzes only one fixture and cannot detect partial activation across eleven documents. Re-running the flip can also replace the rollback snapshot with already-modified data.

- **HIGH — executable verification is substantially weaker than the prose gates.**
  - 33-04 verifies constants, not that staged fields were written.
  - 33-06 only greps for `PASS|FAIL`; a document containing failures passes the command.
  - 33-07 only greps evidence text rather than reading all eleven documents.
  - 33-05’s shell expression can print `scoring untouched OK` and exit successfully after a pytest failure because the final `|| echo ...` absorbs the failure.
  
  D-18 requires blocking devices, not evidence documents containing the right words.

- **MEDIUM — backup integrity does not yet prove the S3 recovery copy (33-02, D-31).** Per-document hashes inside the same JSON detect later modification but do not prove that the S3 object contains identical bytes. The plan also leaves a FAILED output matching the backup glob, and no restore rehearsal proves that Firestore values can be round-tripped from JSON.

- **MEDIUM — coverage inventories conflict (33-06/08/09/16, D-23).** Eleven reference documents minus the six named fixtures leaves five non-paired motions, not four. 33-06’s four exclude sideway-spin; 33-16’s four include sideway-spin but exclude combo. Current `REGISTERED_MOTIONS` contains ten motions, not eleven—combo is not registered. Meanwhile climb lacks the mode1 margin/separation substrate demanded by 33-06. A single canonical coverage matrix is missing.

- **MEDIUM — several success gates are not objectively decidable.** In 33-06, “gap significantly reduced” and pdshape stability “significantly smaller than ±30” lack predeclared numerical boundaries. Safety “no new FP/FN” also lacks an explicit oracle. These permit post-hoc gate interpretation.

- **MEDIUM — the elbow-twist branch has no closed workflow (33-06, D-32).** If the margin remains below `+2.0°`, either branch creates substantial new work—technical investigation or reference replacement—but there is no loop back through backup, reprocess, backfill, and re-verification. 33-07 must remain blocked rather than treating the question as an inline subtask.

- **MEDIUM — production traffic can contaminate supposedly serial evaluation (33-03/06, D-30).** Resynchronizing Lambda to the evaluation Pod before completing substrate verification can allow real analyses to run concurrently with reprocessing or sweeps. “SERIAL” currently governs planned calls, not external production traffic.

- **MEDIUM — Pod approval is not always represented as a blocking checkpoint.** 33-04’s cold path and 33-16 Task 1 describe requesting greenlight inside an automatic task. They should use explicit blocking checkpoints like 33-03 and 33-06.

- **LOW — 33-11 embeds expiring presigned URLs.** A phone review delayed beyond the URL TTL can appear as a design failure. Downloaded real assets with provenance would remain compliant with D-10.

## Suggestions

1. **Replace `phase4_v1` staging with immutable candidate IDs.**  
   Make the script accept `--version phase33-cm3-{run_id}` and refuse overwrites. Keep run 1 and run 2 under separate IDs, compare them, then designate one candidate in a release manifest. Assert that `candidateVersion != activeVersion`.

2. **Create a release manifest tying the substrate together.**  
   Record candidate reference ID, per-document hashes, code commit SHA, target fps, PR flag, deterministic flag, derived-field schema version, and verification result. Both activation and rollback should operate on this tuple.

3. **Rewrite 33-04 around the staged candidate.**  
   It must:
   - read `versions/{candidate}` rather than top-level;
   - derive all required fields from that candidate;
   - merge them back into the same candidate only;
   - define a real producer for `bodyComparisonSourcePose`;
   - reuse Task 1’s pose/keypoint output where possible instead of re-inferring;
   - read fps from candidate metadata or a CLI argument instead of a global hardcode.

4. **Add an explicit shadow-reference resolver for 33-06.**  
   `run_sweep.py`, safety verification, and self-comparison should accept `--reference-version {candidate}` or an injected reference provider. The evidence must prove which candidate hash was consumed without modifying production top-level fields.

5. **Specify M3 before implementation.**  
   Define paired user and reference ranges in `MotionMatch`, minimum reference-phase coverage, boundary behavior for `nu < nr`, and fail-closed behavior when alignment is ambiguous. Add invariants:
   - already-aligned inputs produce byte-identical deviations;
   - identical inputs remain zero;
   - no motion-key branches;
   - no reference phase is silently removed below the coverage floor;
   - formula/constants remain hash-identical.

6. **Deploy and roll back code plus data together.**  
   Before 33-06/07, sync the exact commit to the Pod, restart the server, and expose its commit SHA in health output. Activation should verify `{commit SHA, candidate ID, env}` together. Rollback should quiesce traffic and restore the compatible code/data/env tuple, with no mixed intermediate state.

7. **Make activation resumable and auditable.**  
   Prefer a single global release pointer consumed by all reference readers. If top-level mirrors must remain, use a maintenance window, deployment status document, immutable preimages, idempotent per-doc writes, and 11/11 post-write hash verification. Do not overwrite `pre_phase4`.

8. **Strengthen 33-02.**  
   Write to a temporary file, emit a separate PASS manifest, compute a whole-file SHA-256, upload that checksum as S3 metadata, re-download and compare bytes, and rehearse restore into an isolated collection/emulator before 33-03.

9. **Replace grep gates with data gates.**  
   Have verification commands parse JSON and fail unless:
   - all eight 33-06 items are exactly PASS;
   - no rollback trigger is true;
   - all eleven candidate documents share the expected hash/version;
   - immutable scoring constants and formula files match a pre-phase manifest.

10. **Create one 11-motion coverage table.**  
    For each reference, record registered/unregistered status, paired fixture, success/fault availability, self-comparison substitute, M8 visual check, and presentation coverage. Explicitly resolve climb, sideway-spin, and combo before execution.

11. **Add traffic isolation and explicit Pod checkpoints.**  
    Use a dedicated evaluation Pod or drain Lambda traffic while serial gates run. Add blocking greenlight checkpoints to 33-04’s cold path and 33-16, plus commit/env/model-init canaries rather than relying on `/health` alone.

12. **Turn the elbow-twist branch into a formal HALT loop.**  
    If `< +2.0°`, 33-06 should remain incomplete and route to a defined gap-closure plan that returns through reprocess/backfill/reverification. It must not unblock 33-07.

## Risk Assessment

**Overall risk: HIGH.** The conceptual ordering and presentation dependencies are good, but the current implementation anchors make the safety story invalid: staged writes reuse the active version name, backfill operates on the wrong source and does not persist, staged verification lacks a resolver, and activation does not atomically bind M3 code to the new reference data. These are production-data and score-trust risks, not documentation polish. After immutable candidate staging, candidate-aware backfill/verification, release-tuple deployment, and machine-enforced gates are added, the residual risk should fall to MEDIUM.

---

## Consensus Summary (single reviewer — orchestrator synthesis)

Only one external CLI (codex) was available, so this is codex's assessment plus an orchestrator note separating **must-fix-before-execute** from **pilot-scope-optional**. Codex's overall verdict: **structurally strong, operationally unsafe** until the substrate *release mechanics* are corrected — HIGH risk, reducible to MEDIUM after fixes.

### Agreed Strengths (codex-confirmed, matches the internal plan-checker)
- Substrate Task 0–5 order (33-02→33-07) is correct; backup precedes writes; 33-07 gated on 33-06.
- All presentation plans (33-08+) gate on substrate flip (33-07) — D-28 holds, no ordering hole.
- D-20/D-29 no-scoring-refit invariant is stated consistently; margins-not-target-scores in 33-06.
- Eyes-on artifact inspection (D-19) and dual-copy backup + hashes (33-02) present.

### Highest-priority concerns — MUST address before execute (all HIGH, codex; orchestrator concurs — these are real, verified against the SEED/scripts)
1. **Staging version-name collision (33-03).** `reprocess_reference_motions_phase4.py` writes `versions/phase4_v1`, which *is* the active version name → `--no-flip` overwrites the active-pointed backing doc, consumers can see staged data early, rollback loses old phase4_v1, and 33-07's `activeVersion` proof is a no-op. **Fix: immutable candidate version IDs (`phase33-cm3-{run_id}`), refuse overwrite, assert candidate != active.**
2. **Backfill can't write the staged doc (33-04).** `backfill_reference_downstream.py` never writes Firestore and reads top-level (old) data → 33-04 can pass grep checks while the staged reference stays incomplete/derived-from-old. **Fix: rewrite 33-04 to read+merge the candidate version; define a real `bodyComparisonSourcePose` producer; read fps from candidate metadata not the global constant.**
3. **No candidate-version resolver (33-06).** `run_sweep.py`/pipeline read top-level reference → 33-06 tests the *old* reference unless an undocumented flip happens (violates D-31). **Fix: add `--reference-version {candidate}` injection to sweep/safety/self-comparison.**
4. **M3 underspecified + scoring-leak risk (33-05).** `find_action_segment` returns only a user (start,end); "window the reference when nu<nr" needs a reference range the API can't carry, and a best-match reference window could silently drop hard reference phases → inflated scores. "Scoring files unchanged" does not prove alignment-only. **Fix: spec paired user+reference ranges, a reference-phase coverage floor, fail-closed on ambiguity, and byte-identical-deviation invariants BEFORE implementing.**
5. **No atomic release tuple (33-05–33-07).** C+M3 is only valid as {9fps ref, PR=1, M3 code, derived fields}; plan flips data but never deploys the M3 commit to the production Pod, and rollback (`git revert` later) allows old-18fps-data + new-M3 intermediates. **Fix: deploy code+data+env as one release; rollback restores the compatible tuple.**
6. **Warm-Pod can run stale code (33-04/06/07).** Pod bootstrapped in 33-03, code changes in 33-04/05, but 33-06 reuses the warm Pod without syncing the commit/restarting → sweep may run without the 9fps/M3 changes. `/health 200` proves liveness, not source revision. **Fix: sync exact commit + restart + expose commit SHA in health; canary, not just /health. (Extends the internal checker's WARNING 2.)**
7. **Non-atomic 11-doc flip (33-07).** Sequential writes, overwrites `versions/pre_phase4` each rerun, post-flip check reads one fixture only → a crash leaves a mixed library undetected. **Fix: idempotent per-doc writes, 11/11 post-write hash check, never overwrite pre_phase4.**
8. **Grep gates weaker than prose gates.** `grep PASS|FAIL` passes on a doc *containing* a failure; 33-05's trailing `|| echo ... OK` absorbs a pytest failure. **Fix: JSON data-gates that fail unless all 8 items are exactly PASS and scoring-constant manifests match.**

### Should-fix (MEDIUM, codex; orchestrator: fold into the same replan)
- **Coverage inventory conflicts (33-06/08/09/16, D-23):** 11−6 = **5** non-paired motions, not 4; 33-06's four exclude sideway-spin, 33-16's four include it but drop combo; `REGISTERED_MOTIONS` has **10** (combo unregistered); climb lacks mode1 substrate. → **Need one canonical 11-motion coverage matrix** resolving climb/sideway-spin/combo. (This is a concrete factual gap and should be fixed.)
- **Non-decidable gates (33-06):** "gap significantly reduced" / "significantly < ±30" / "no new FP/FN" need predeclared numeric boundaries + an oracle.
- **Elbow-twist branch not a closed HALT loop (33-06, D-32):** a `< +2.0°` outcome must route back through reprocess/backfill/reverify, not resolve inline while 33-07 unblocks.
- **Production-traffic contamination (33-03/06, D-30):** re-syncing Lambda to the eval Pod before verification lets real analyses run concurrently with the sweep — "SERIAL" only governs *planned* calls. → dedicated eval Pod or drain Lambda during gates.
- **Pod approval not always a blocking checkpoint (33-04 cold path, 33-16 Task 1).**
- **S3 backup byte-integrity + restore rehearsal (33-02).**

### Orchestrator note — pilot-scope judgment (belle decides)
Codex's suggestions #2 (release manifest) and #7 (maintenance window / global release pointer) are release-engineering that may exceed pilot scope. But their *underlying defects* (1, 3, 5, 7 above) are real and cheap to fix at the staging-primitive level. Recommendation: adopt the **candidate-version-ID + candidate-aware backfill/verify + commit-pinned Pod deploy + JSON data-gates** core (concerns 1–8), plus the **canonical coverage matrix** and **elbow-twist HALT loop**; treat full release-manifest tooling as optional. The M3 spec (concern 4) is the one that most directly touches Core Value (score trust) and should be written before any M3 code.

### Divergent Views
None — single reviewer. The internal plan-checker (PASSED) and codex do not contradict: the checker verified plan *structure/coverage*; codex found *implementation-anchor* defects (does the referenced script actually do what the plan claims). Both are valid layers; codex's are the higher-severity set.
