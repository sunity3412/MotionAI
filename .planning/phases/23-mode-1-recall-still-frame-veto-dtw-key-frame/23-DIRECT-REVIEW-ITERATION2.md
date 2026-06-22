# Phase 23 Direct Review - Iteration 2

**Reviewer:** Codex direct review, no external skill/MCP  
**Reviewed at:** 2026-06-22  
**Scope:** latest `23-CONTEXT.md`, `23-01-PLAN.md`, `23-02-PLAN.md`, `23-03-PLAN.md`, after 1st-review fixes were folded in.

## Findings

### HIGH-1: `VisionFaultContext` changes the production path, but 23-01/23-03 still treat `_apply_vision_veto` as the owner of the live Gemini call

The revised 23-02 correctly adds a pre-coach `VisionFaultContext` so root-cause hypotheses can reach `coach_details.detail2.causes` (`23-02-PLAN.md:245-263`). But 23-01 still describes `_apply_vision_veto` as the still-frame callsite into `assess_fault_severity` (`23-01-PLAN.md:42-45`, `23-01-PLAN.md:195-200`), and 23-03 still defines the production eval path as `_apply_vision_veto -> frame selection -> DTW gating -> cache` (`23-03-PLAN.md:15`, `23-03-PLAN.md:40-42`, `23-03-PLAN.md:87`, `23-03-PLAN.md:101`).

Current production ordering is also important: coach generation happens before `_apply_vision_veto` (`backend/functions/pipeline/app.py:2578-2699`). After the 23-02 fix, the real production path must become "collect vision context before coach -> generate coach -> apply cap/audit from the same context". If `_apply_vision_veto` still owns the Gemini call, the pipeline either calls Gemini twice or the coach still cannot consume the verdict.

**Risk:** 23-03 can validate the old seam while the actual fixed design uses a different path. The "verdict Gemini call is 1회" acceptance (`23-02-PLAN.md:259`, `23-02-PLAN.md:271`) is not enforceable unless the ownership split is explicit.

**How I would fix it:** Add an explicit two-function contract to 23-01:

- `_collect_vision_fault_context(...) -> VisionFaultContext | VisionVetoStatus`: frame selection, local/global alignment, still image extraction, Gemini call, support gating, cache key, telemetry.
- `_apply_vision_veto(score_result, vision_fault_context=...) -> dict`: no Gemini call when context is provided; only downward cap + audit/status attach.

Then update 23-03 to gate the actual path as `collect context before coach -> coach writers consume it -> build_result -> apply context`. Required trace fields should include `contextCollectedBeforeCoach=true`, `contextReusedForAudit=true`, and `geminiCallCount=1`.

### HIGH-2: Still-frame image extraction and cleanup are not specified, even though the API now requires image paths

23-01 Task 1 defines `assess_fault_severity(student_frame_path, reference_frame_path, ...)` and `_upload_image(client, path)` (`23-01-PLAN.md:105`, `23-01-PLAN.md:109`). Task 3 then says `_apply_vision_veto` should compute student/ref frame indices and call the still path (`23-01-PLAN.md:196-197`). But no task specifies how those frame indices become local PNG/JPEG files, where temporary files live, how they are cleaned, or whether extracted frames reuse `FfmpegFrameExtractor`.

The current code only extracts frame arrays for fault zoom inside `_render_fault_zoom` (`backend/functions/pipeline/app.py:1824-1832`) and that happens after veto. Also, `keypoint_report_dict` is built after `_apply_vision_veto` runs (`app.py:2692-2699`, `app.py:2863-2909`), while local alignment and `FramePairMeasurementContext` require selected-frame keypoint visibility/confidence.

**Risk:** An executor can satisfy adapter-level tests with fake image paths while production has no reliable way to create or clean the still files. Local alignment confidence may be implemented without real per-frame keypoint visibility because that data is currently produced later.

**How I would fix it:** Add a concrete `SelectedFramePair` helper in the plan:

- Inputs: user/ref video paths, `MotionMatch`, candidate user frame indices, and either `pose_frames` or prebuilt keypoint reports.
- Outputs: `student_frame_path`, `reference_frame_path`, `user_frame_idx`, `ref_frame_idx`, keypoints/confidence for both frames, and cleanup handles.
- Cleanup: `finally` unlinks all generated local image files independently of Gemini File API deletion.

Move `build_keypoint_report(pose_frames, fps=9.0)` or an equivalent per-frame confidence extraction before vision context collection, or define that the context uses `pose_frames` directly. Add a production-level test that fails if `_upload_image` is called with a nonexistent path or if temp frame files remain after exceptions.

### HIGH-3: Angle quantification still has two incompatible frame semantics

23-02 Task 1 asks for per-joint angle deltas from student/ref angle matrices using DTW median semantics (`23-02-PLAN.md:111-117`). Task 2 then says 칸/각도 must be computed only from the exact frame pair that produced the verdict via `FramePairMeasurementContext` (`23-02-PLAN.md:148`, `23-02-PLAN.md:154`). These are different contracts: a DTW-path median can be correct for scoring, but it is not the same as "this still frame shows knee 145° vs reference 178°".

**Risk:** The product can show precise-looking frame-specific numbers that were actually computed from a median over a window/path. That undermines the whole "same-frame deterministic quantification" fix.

**How I would fix it:** Decide one semantic and name it in the data model:

- If the displayed sentence is frame-specific, compute `student_deg` and `reference_deg` from `FramePairMeasurementContext.user_frame_idx/ref_frame_idx` only.
- If median is desired for robustness, call it `windowMedianAngleDeltas`, store `sourceFrameIndices`/`windowPolicy`, and do not phrase it as the still frame's exact angle.

Tests should include a case where the selected frame angle differs from the DTW median; the expected output must make the chosen semantic unambiguous.

### MEDIUM-1: `resource_limited` is added in action text but not fully locked in acceptance/verification

The revised 23-01 action says `resource_limited` must be added to Python/TS/docs lockstep (`23-01-PLAN.md:200`). But the artifact still says `models.py` provides only `low_alignment_confidence` (`23-01-PLAN.md:35-40`), and the acceptance grep only checks `low_alignment_confidence` across the three contract files (`23-01-PLAN.md:210-213`).

**Risk:** The fail-closed budget status can be omitted while the plan still passes its own checklist. That reopens the partial-sampling false-positive risk the revised plan is trying to close.

**How I would fix it:** Update must-haves and acceptance to require both statuses:

- `low_alignment_confidence`
- `resource_limited` or the final chosen `sampling_incomplete`

Also require TS discriminated-union checks that `resource_limited` has no `severity`, `capApplied`, `primaryFault`, `angleDeltas`, `bodyRelativeNotches`, or `rootCauseHypotheses`, but may include telemetry.

### MEDIUM-2: Coach writer changes are listed, but the verification command does not run the coach writer tests

23-02 now correctly includes `backend/shared/python/sunity_shared/analysis/coach_writer.py`, `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py`, and `backend/tests/test_coach_writer.py` in the file list (`23-02-PLAN.md:12-22`). Task 5 acceptance explicitly requires both writers to read and render the new vision-fault key (`23-02-PLAN.md:269-270`). But the automated verification for Task 5 only runs `tests/test_pipeline_vision_gate.py` (`23-02-PLAN.md:265-267`).

**Risk:** The pipeline test can pass with a fake or monkeypatched writer while the real prompt-building paths still ignore `VisionFaultContext`. That is the exact false-pass Task 5 says it wants to prevent.

**How I would fix it:** Change Task 5 verification to:

```bash
cd backend && python -m pytest tests/test_pipeline_vision_gate.py tests/test_coach_writer.py -x -q
```

Add assertions that inspect the actual Cerebras and Gemini prompt payloads or normalized writer inputs, not only final assembled tips.

### LOW-1: The context domain still says Mode 3 also gets the same alignment/quantification

The top-level domain statement still says "Mode 3에도 동일 정렬·정량화를 적용한다" (`23-CONTEXT.md:9`), while D-07 formally defers Mode 3 (`23-CONTEXT.md:40-42`) and all plans are Mode 1 focused.

**Risk:** Low execution risk because D-07 and the plans are clear, but it is a stale source-of-truth conflict for downstream agents reading top-down.

**How I would fix it:** Edit the domain paragraph to say Mode 3 is deferred to Backlog B-15a, matching D-07 and the roadmap.

## Overall Assessment

The first-review fixes were folded in substantially: canonical `FaultKey`, same-frame measurement, `resource_limited`, runtime eval traces, and real coach-writer consumption are now present in the plan. The remaining blocker is architectural: once `VisionFaultContext` must exist before coach generation, `_apply_vision_veto` can no longer be the only production seam that owns the Gemini call.

I would patch that seam definition before execution. Otherwise implementation will drift into either duplicate Gemini calls or an eval harness that validates the old path while the intended user-facing root-cause coaching depends on a new path.
