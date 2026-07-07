# Phase 27 Plan Review

**Reviewed:** 2026-07-07  
**Reviewer:** Codex direct review (external reviewer/CLI not used)  
**Scope:** `27-01-PLAN.md` through `27-09-PLAN.md`, checked against `27-CONTEXT.md`, `27-RESEARCH.md`, `27-PATTERNS.md`, `27-VALIDATION.md`, and referenced local code.

## Verdict

The high-level strategy is sound and the likely reviewer misunderstandings are mostly prevented:

- The "1 minute" target is not treated as a hard gate. Accuracy/no-regression is the hard gate.
- Frame count and resolution are intentionally unchanged. The plan uses handle reuse, inline transfer, and overlap, so pixel-level input fidelity is preserved.
- Full async veto is correctly rejected. The plan overlaps preparation/generate work but keeps score/verdict finalization synchronous.
- The three Pod work plans (`27-02`, `27-08`, `27-09`) all include blocking human checkpoints before Pod mutation or paid eval work.

I found two **HIGH** risks that I would amend before execution. Both are fixable at the plan level.

## Findings

### HIGH-1: Plan 05's prefetch start point does not exist in the current pipeline shape

**Files/lines:**
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-05-PLAN.md:67-84`
- `backend/functions/pipeline/app.py:1281-1324`
- `backend/functions/pipeline/app.py:3111-3123`

Plan 05 says Gemini upload/scene/moment prefetch starts after S3 download and before RTMW, hiding Gemini work under the ~51s pose stage. The current code does not expose that seam. `_process` calls `_extract_video_analysis_inputs(...)` at `app.py:3111-3118`, and only receives `local_video_path` at `app.py:3122-3123` after `_extract_video_analysis_inputs` has already downloaded S3, extracted frames, run RTMW, computed angles, and built pose metadata.

Inside `_extract_video_analysis_inputs`, the local video path is created at `app.py:1299-1304`, but frame extraction and RTMW run immediately inside the same helper at `app.py:1305-1306`. There is no caller-visible "download complete, pose not started" point.

If Plan 05 is executed literally, prefetch will start after RTMW is done. That still may reduce duplicate uploads via Plan 04, but it will not deliver the intended overlap with the pose stage.

**How I would handle it:**

I would amend Plan 05 before implementation:

1. Add an explicit refactor task that splits local video acquisition from pose extraction, e.g. `_download_analysis_video(...) -> local_video_path`, then `_extract_video_analysis_inputs_from_local(local_video_path, ...)`.
2. Start `GeminiFileSession.get_or_upload(local_video_path)` and other pose-independent futures after local path creation and before `_FRAME_EXTRACTOR.extract(...)` / `_RTMW_ENGINE.estimate(...)`.
3. Preserve the Phase 6 invariant: RTMW estimate still runs once, and cleanup still happens after all futures and zoom work.
4. Add a verification that stage logs show `gemini_upload_prefetch` starts before or during `frame_extract`/`rtmw`, not after `rtmw`.

Without that amendment, I would downgrade the expected timing benefit and not claim pose-shadow overlap.

### HIGH-2: `GeminiMomentExtractor` self-upload fallback can still leak File API files

**Files/lines:**
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-04-PLAN.md:69-83`
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-04-PLAN.md:136-140`
- `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py:350-384`

Plan 04 wires preuploaded handles into the moment extractor and says a `None` handle falls back to the existing self-upload path. The current self-upload path uploads at `gemini_moment_extractor.py:350`, polls, generates, and returns at `:384`, but it does not delete the uploaded file.

That matters because this phase is explicitly motivated by the 20GB Gemini Files storage incident. If `GeminiFileSession.get_or_upload(...)` returns `None` or the optimized path is disabled, moment extraction can still upload and leave the file behind. Plan 03's session close cannot delete a handle it never owned.

**How I would handle it:**

I would amend Plan 04 Task 1:

1. Extend `GeminiMomentExtractor.extract_key_moments(...)` / `_call_gemini(...)` with `preuploaded_handle=None`.
2. If a handle is supplied, skip upload/poll/delete and use the supplied handle.
3. If no handle is supplied, preserve current behavior except wrap the owned upload in `try/finally client.files.delete(name=...)`.
4. Add fake-client tests for both paths: supplied handle is not deleted by extractor, self-upload is deleted exactly once even on parse/generate error.

This is a blocker for me because it is a DoS/privacy regression surface, not just a missed optimization.

### MEDIUM-1: `result.timingsMs` is introduced without contract lockstep

**Files/lines:**
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-01-PLAN.md:15-34`
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-01-PLAN.md:77-83`
- `app/src/types/analysis.ts:515-560`
- `backend/shared/python/sunity_shared/firestore_admin.py:907-918`

Plan 01 stores `result.timingsMs` as a new result field. Backend flat validation will likely accept a `dict[str, int]`, but the app `AnalysisResult` type and `docs/contract.md` do not define the field.

That may be acceptable for backend-only observability, but this project has repeatedly enforced contract lockstep for result fields. Leaving it undocumented makes later review/debugging harder.

**How I would handle it:**

Either:

- Add `timingsMs?: Record<string, number>` to `AnalysisResult` and document it in `docs/contract.md`, with a note that it is backend/audit-only and not user-facing, or
- Store it as a top-level backend audit field outside `result` and document why it intentionally does not enter the app contract.

I would not leave it as an implicit extra result field.

### MEDIUM-2: `GeminiFileSession.get_or_upload` lock scope can serialize unrelated uploads

**Files/lines:**
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-03-PLAN.md:83-90`
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-05-PLAN.md:77-84`

Plan 03 says `get_or_upload` is protected by a single lock over the whole method. If that lock spans upload and ACTIVE polling, concurrent student/reference upload attempts will serialize. That is safe, but it reduces the benefit of Plan 05's prefetch.

**How I would handle it:**

Keep correctness first, but narrow the lock:

- Protect the path-to-handle map and in-flight markers with a lock.
- Perform upload/poll outside the global lock.
- Use per-path in-flight futures/events if duplicate same-path calls are possible.

This is not a correctness blocker if HIGH-1 is fixed, but it is worth addressing while implementing the session.

### MEDIUM-3: Plan 06 improves user-visible completion but not total worker occupancy

**Files/lines:**
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-06-PLAN.md:50-56`
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-06-PLAN.md:116-123`

Plan 06 moves zoom after `complete_analysis` but keeps it in the same BackgroundTask. That is correct for D-06 UX: the app sees `status='done'` before zoom. It does not necessarily improve RunPod throughput, because the worker remains occupied until post-complete zoom finishes.

**How I would handle it:**

I would keep the plan as-is if the goal is user-perceived completion. But I would make the distinction explicit in `27-06-SUMMARY.md` and `27-TIMING-AFTER.md`: "time to first result" improved, "server task total duration" may still include zoom.

## Intentional Choices Reviewed

### 1 minute is not a hard gate

This is handled correctly. `27-CONTEXT.md` D-01 makes accuracy/no-regression the hard gate, and `27-09-PLAN.md` repeats that time is reported as realistic maximum reduction, not a pass/fail threshold.

If a reviewer asks why the plan does not guarantee 1 minute, I would answer: because the correct gate is EVAL18 no-regression plus measured improvement. The "1 minute" label is product pressure, not an engineering acceptance threshold.

### No frame or resolution reduction

This is handled correctly. Plans 04 and 05 focus on File API handle reuse, inline still PNG, and overlap. I did not see any plan step that intentionally reduces video frame count, max side, or model input fidelity.

The only caveat is Plan 06's frame-array reuse. That must reuse the exact same `FfmpegFrameExtractor(target_fps=9.0, max_side=640)` output, not introduce a separate sampling path.

### Veto full async is rejected

This is handled correctly. Plan 05 overlaps upload/generate work and fan-out execution, but the final verdict/score path remains synchronous. Plan 06 only lets zoom images arrive later, which is a presentation artifact and does not alter score/verdict/faults.

### Pod checkpoints

This is handled correctly. `27-02`, `27-08`, and `27-09` each have a blocking belle approval step before Pod work. That matches the Phase 22 lesson and should be preserved.

## Recommended Plan Amendments Before Execution

1. Patch Plan 05 so the prefetch seam is real: split local video download from frame extraction/RTMW, then start Gemini futures before pose work.
2. Patch Plan 04 so `GeminiMomentExtractor` deletes self-uploaded File API files on every fallback/error path.
3. Decide where `timingsMs` lives contractually and update `analysis.ts`/`contract.md` or move it out of `result`.
4. Prefer a narrower `GeminiFileSession` lock so different video uploads do not serialize unnecessarily.

## Final Assessment

I would proceed after amending HIGH-1 and HIGH-2. The phase's intent is technically coherent, and the four reviewer-confusion points are defensible. The two blockers are implementation-plan gaps: one would erase the main overlap benefit, and the other can preserve a known Gemini File API leak path.
