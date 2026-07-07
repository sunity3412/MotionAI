# Phase 28 Plan Review

**Reviewed:** 2026-07-07  
**Reviewer:** Codex direct review (external reviewer/CLI not used)  
**Scope:** `28-01-PLAN.md` through `28-08-PLAN.md`, checked against `28-CONTEXT.md`, `28-RESEARCH.md`, `28-PATTERNS.md`, `28-VALIDATION.md`, Phase 26/27 overlap plans, and referenced local code.

## Verdict

The phase strategy is coherent: reuse existing `MotionMatch`, emit second-based anchors, keep scoring and veto still untouched, reuse `vision_veto` thresholds, and let the app consume alignment defensively. The user-specified constraints are mostly reflected:

- Veto still at `app.py:1720` does share the fps bug, but leaving it out of Phase 28 is correct because it is Gemini veto input and can move scores.
- The 8.0/25.0 tier thresholds are correctly sourced from production `vision_veto._ALIGN_GLOBAL_T1/T2`.
- Degenerate new-analysis cases should emit `tier: "disabled"` instead of `None`; the plan mostly adopts this, though one Wave 0 test description still needs cleanup.
- Phase 26/27 ordering is real. Current local code does not yet contain `faultZoomStatus` or `update_analysis_fault_zoom`, so the Phase 28 symbol gates should stop 28-03/28-04/28-07 if executed now.

I found one **HIGH** implementation risk that would make a required user-visible feature fail while most local gates still pass. I would amend that before execution.

## Findings

### HIGH-1: `refMatch` is added in `fault_zoom.py` but dropped by `app.py` before Firestore

**Files/lines:**
- `.planning/phases/28-dtw-motion-based-alignment/28-05-PLAN.md:7-9`
- `.planning/phases/28-dtw-motion-based-alignment/28-05-PLAN.md:103-106`
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py:925-935`
- `backend/functions/pipeline/app.py:2625-2642`
- `.planning/phases/28-dtw-motion-based-alignment/28-07-PLAN.md:68-69`

Plan 28-05 says `build_fault_zoom_comparisons` will add `"refMatch": "failed" | "dtw"` and Plan 28-07 consumes that field for the "same moment not found" caption. But the actual Firestore-facing result item is not the dict returned by `fault_zoom.py`. `_render_fault_zoom` in `app.py` rebuilds each item from selected keys (`joint`, `deficitDeg`, `imageUrl`, `tier`, optional `kind`, optional `region`) and currently drops all other keys.

So if 28-05 is executed as written, tests can pass in `fault_zoom.py`, but the app will never see `FaultZoomComparison.refMatch`. The D-04 caption path is dead, and 28-08's end-to-end `refMatch` doc check will fail late. Worse, 28-05 explicitly requires `git diff --name-only` to include only `fault_zoom.py` plus tests, which prevents the necessary `app.py` pass-through.

**How I would handle it:**

I would amend 28-05 before execution:

1. Add `backend/functions/pipeline/app.py` to `files_modified`, or explicitly move the pass-through to 28-04 if that is where the post-27 mapper lives.
2. In `_render_fault_zoom`, after `region` pass-through, copy only valid scalar provenance:
   ```python
   if c.get("refMatch") in ("dtw", "failed"):
       item["refMatch"] = c["refMatch"]
   ```
3. If Phase 27-06 has already refactored zoom into post-complete `update_analysis_fault_zoom`, apply the same pass-through in that mapper, not only the pre-27 local shape.
4. Replace the 28-05 diff gate with a narrower safety gate: `app.py` may change only in `_render_fault_zoom`/zoom result mapping, while `_build_selected_frame_pair` remains untouched.
5. Add a unit test that exercises the pipeline/render mapper, not only `build_fault_zoom_comparisons`, and asserts the final `result["faultZoomComparisons"][0]["refMatch"]` survives.

This is a blocker because the contract and UI plan depend on a field that the current persistence mapper would discard.

### MEDIUM-1: The VideoCompare grep gate can allow an unwarped `slowerTime` write in the active alignment path

**Files/lines:**
- `.planning/phases/28-dtw-motion-based-alignment/28-06-PLAN.md:72-79`
- `app/src/components/VideoCompare.tsx:398-400`
- `.planning/phases/28-dtw-motion-based-alignment/28-RESEARCH.md:291-293`

Plan 28-06 correctly says every right-player seek path must go through `targetRefTime`. The verify command, however, allows lines containing `slowerTime` as a legacy exception. In the current code, `togglePlay` directly assigns `rightPlayer.currentTime = slowerTime`. If an implementer leaves that line in a branch that also runs when alignment is active, the grep still passes, but scrub/restart/start-sync can still use absolute time and trigger the stutter described in Pitfall 7.

**How I would handle it:**

I would make the code shape easier to verify:

1. Introduce a tiny helper such as `setRightToStudentTime(tStudent)` that performs `rightPlayer.currentTime = targetRefTime(tStudent)`.
2. Keep legacy absolute sync in a clearly named `setBothAbsoluteTime(t)` branch guarded by `!alignmentActive`.
3. Change the grep gate so direct `rightPlayer.currentTime =` appears only inside those helpers, or require every active-path call site to use `setRightToStudentTime`.

This is not a design blocker, but the current acceptance gate is weaker than the plan's own Pitfall 7 requirement.

### MEDIUM-2: Wave 0 still says `path=[]` returns `None`, conflicting with the final degenerate contract

**Files/lines:**
- `.planning/phases/28-dtw-motion-based-alignment/28-01-PLAN.md:93-101`
- `.planning/phases/28-dtw-motion-based-alignment/28-02-PLAN.md:81-92`
- `.planning/phases/28-dtw-motion-based-alignment/28-07-PLAN.md:31-32`

28-02 fixes the contract: `match=None` means no alignment context and may return `None`; build failures for a new analysis (`path=[]`, invalid fps, insufficient anchors) emit `tier: "disabled"` with empty anchors. That is the right behavior because it prevents the legacy "reanalyze and it will work" banner loop.

But 28-01 still asks the initial RED test to expect `path=[] -> None`, then 28-02 tells the implementer to update that expectation. That creates avoidable churn in the foundational contract test.

**How I would handle it:**

I would amend 28-01 now:

- `match=None -> None`
- `path=[] -> {"tier": "disabled", "reason": "empty_path", "anchors": [], "anchorCount": 0}`
- `user_fps <= 0` or `ref_fps <= 0 -> tier "disabled", reason "invalid_fps"`

Then 28-02 can turn the RED test green without rewriting the core expectation.

### MEDIUM-3: The validator should tie empty anchors to `tier: "disabled"`

**Files/lines:**
- `.planning/phases/28-dtw-motion-based-alignment/28-03-PLAN.md:118-121`
- `.planning/phases/28-dtw-motion-based-alignment/28-01-PLAN.md:129-130`

28-03's validator allows empty anchors as a vacuous monotonic list for degenerate disabled output. That part is fine. What is missing is the inverse invariant: `warped` and `trim_only` should require at least two anchor pairs.

The app normalizer is stricter, but persistence should reject contradictory data instead of storing `tier: "warped", anchors: []` and letting the app silently fall back.

**How I would handle it:**

In `_validate_motion_alignment`:

- If `tier == "disabled"`, allow `anchors == []`.
- If `tier in ("warped", "trim_only")`, require `len(anchors) >= 4` and `anchorCount >= 2`.
- Add tests for `warped` with empty anchors and `trim_only` with one pair.

This keeps the backend contract aligned with the app normalizer and makes malformed Firestore state easier to diagnose.

## Intentional Choices Reviewed

### Veto still fps bug is intentionally out of scope

I agree with the boundary. Current code confirms `_build_selected_frame_pair` calls `_matched_ref_frame(reference_dtw_match, u_idx, r_n)` at `app.py:1720`, so it shares the same ref-fps domain bug. But this path feeds Gemini veto stills. Changing `_matched_ref_frame` itself would change both display and veto inputs, and can move scores. Phase 28 should keep `_matched_ref_frame` logic unchanged and fix only the fault_zoom display caller.

### Threshold reuse is correct

`vision_veto.py` currently defines `_ALIGN_GLOBAL_T1 = 8.0` and `_ALIGN_GLOBAL_T2 = 25.0`. Reusing those constants, with lockstep tests and source comments, satisfies the calibration-source-hard-gate. I would not introduce a new DTW distance band in this phase.

### Phase 26/27 ordering is correctly gated

The current repo state lacks `faultZoomStatus` and `update_analysis_fault_zoom`, so starting the overlapping 28 tasks today should stop. The Phase 28 plan's symbol-based gates are therefore necessary, not bureaucracy. Preserve them.

## Recommended Plan Amendments Before Execution

1. Patch 28-05 so `refMatch` is copied through the pipeline/zoom result mapper into Firestore, with a mapper-level unit test.
2. Strengthen 28-06 verification so active alignment cannot leave any `rightPlayer.currentTime = slowerTime` path unwarped.
3. Update 28-01's initial RED tests to the final W3 contract: degenerate build failures emit `tier: "disabled"`, not `None`.
4. Tighten 28-03 validation so empty anchors are valid only for `tier: "disabled"`.
5. Optionally make 28-05 depend on 28-04, or state that mode3 fault_zoom degradation is acceptable until the same wave completes.

## Final Assessment

I would proceed after amending HIGH-1. Without that amendment, Phase 28 can complete most backend/app work but still fail the D-04 user promise because `refMatch` never reaches `result.tsx`. The scoring no-touch boundary, threshold reuse, disabled-degenerate behavior, and Phase 26/27 ordering choices are otherwise defensible and should be preserved.
