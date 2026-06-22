# Phase 23 Direct Review

**Reviewer:** Codex direct review, no external skill/MCP  
**Reviewed at:** 2026-06-22  
**Scope:** `23-01-PLAN.md`, `23-02-PLAN.md`, `23-03-PLAN.md`, and the current production code seams they reference.

## Findings

### HIGH-1: Root-cause "coaching" is planned after the coach output has already been generated

`23-02-PLAN.md` says root-cause hypotheses should be generated as coaching, not merely stored (`23-02-PLAN.md:28`, `23-02-PLAN.md:64-65`, `23-02-PLAN.md:217`). In the current pipeline, however, coach details are built before the vision veto runs: `_build_coach_context` / dual coach writers run at `backend/functions/pipeline/app.py:2578-2668`, `assemble.build_result` consumes that output at `app.py:2670-2686`, and `_apply_vision_veto` only runs afterward at `app.py:2692-2699`. A `root_cause_hypothesis` produced inside the veto verdict therefore cannot influence `coach_details.detail2.causes`; it can only be appended to `visionVeto` audit.

**Risk:** Success Criteria #5 can pass as "audit field stored" while no backend coaching output is actually generated. A later UI phase would have no coach-report cause section to render from this phase.

**How I would fix it:** Split the work into two stages. First, collect a `VisionFaultContext` before coach writing: still-frame verdict, supported differences, root-cause hypotheses, and source/provenance. Feed that context into `_build_coach_context` so Gemini/Cerebras section assembly can generate `detail2.causes`. Second, after `assemble.build_result`, apply the downward cap and attach the same context to `visionVeto` audit. Add a test where a fake still-frame verdict with `root_cause_hypothesis="폴 밀착이 풀린 것으로 보임"` produces both `visionVeto.rootCauseHypotheses` and a matching `coachingTips[].detail2.causes[]` entry.

### HIGH-2: Support gating keyed by raw `body_part` can both lose and fabricate side-specific defects

`23-01-PLAN.md` says to support-gate differences by `body_part` before feeding the existing `_union_differences` (`23-01-PLAN.md:139-140`, `23-01-PLAN.md:147-148`). The existing union deduplicates by lower-cased raw `body_part` and keeps one item per key (`gemini_vision_scorer.py:733-762`). The existing keypoint mapper also treats an unspecified side as both sides (`vision_veto.py:159-167`).

**Risk:** This is too weak for the stated recall target of `{왼팔, 오른팔, 고개/목}` (`23-03-PLAN.md:134`, `ROADMAP.md:760`). Semantically identical outputs like "왼팔", "left arm", and "왼쪽 팔꿈치" may fail to reach K support if counted as different strings. Conversely, an ambiguous "팔" can be expanded to both sides and look like left/right support even when only one side was actually observed.

**How I would fix it:** Introduce a canonical `FaultKey` before support counting, for example `(part_scope, side, keypoint_set, fault_kind)`. Derive it from the prompt scope, normalized `body_part`, `_keypoints_for_part`, and a small normalized fault taxonomy. Treat ambiguous side as `side="unknown"` for support; only expand to both visual highlights as a lower-confidence display fallback, not as evidence for two side-specific faults. Then let `_union_differences` operate on already canonical, support-qualified records. Add tests for left/right simultaneous defects, Korean/English aliases for the same left-arm defect, and ambiguous "팔" not creating two supported side-specific faults.

### HIGH-3: The quantification plan does not require same-frame measurement inputs

`23-02-PLAN.md` asks for deterministic 칸/층 geometry from keypoints, pole/floor/hip-line baseline, and body normalization (`23-02-PLAN.md:140-147`, `23-02-PLAN.md:217`). Its wiring points to Mode 1 body-profile/reference-source-pose fetches (`23-02-PLAN.md:200-201`). In current code, `bodyComparisonSourcePose` is a reference source pose fetched separately (`app.py:2368-2376`), while same-pose frame matching is handled by DTW (`fault_zoom._matched_ref_frame`, `fault_zoom.py:44-62`) and fault zoom uses per-frame keypoint reports for the selected user/ref frames (`fault_zoom.py:193-194`).

**Risk:** A deterministic formula can still be deterministically wrong if it measures the wrong frame. "정은지 3칸, 너 2칸 ⅔" must be computed from the same student/ref frame pair that produced the still-frame verdict. Using a static source pose, video-level pole line, or body-profile summary can produce polished but frame-mismatched numbers.

**How I would fix it:** Define a `FramePairMeasurementContext` contract: `user_frame_idx`, `ref_frame_idx`, user/ref keypoints from `keypointReport` at those exact indices, baseline kind, pole/floor/hip-line source, visibility/confidence, and selector version. Compute angle deltas and notches only from that context. If any required per-frame input is missing, omit the quantification with `quantificationStatus="unavailable"` and a warning, rather than falling back to a mismatched source pose. Add tests where a deliberately mismatched ref frame would produce a different notch value and must be rejected.

### MEDIUM-1: Wall-clock/upload budget exhaustion has no explicit result contract

`23-01-PLAN.md` says budget exhaustion should produce a graceful partial result (`23-01-PLAN.md:142`, `23-01-PLAN.md:150`), but the status lockstep only adds `low_alignment_confidence` (`23-01-PLAN.md:196`, `23-01-PLAN.md:206-209`). Current status contracts also have no partial/resource-limited state (`models.py:74-82`, `analysis.ts:350-353`, `contract.md:176-195`).

**Risk:** An executor can return `applied` based on partial sampling without telling downstream code that the precision/support quorum was incomplete. That weakens the false-positive gate this phase is trying to protect.

**How I would fix it:** Fail closed on incomplete quorum: return a score-free `resource_limited` or `sampling_incomplete` status unless the minimum support quorum completed before the budget ended. Add this status to Python/TS/contract lockstep, and include telemetry such as `completedCalls`, `plannedCalls`, `uploadCount`, `durationMs`, and `samplingComplete`. If the team wants to apply caps from partial data, require `samplingComplete=false` plus a stricter support threshold and make that explicit in tests.

### MEDIUM-2: The eval acceptance can pass by string presence, not by exercised behavior

`23-03-PLAN.md` correctly requires the production path, but its harness acceptance mostly checks source text with grep, such as `_apply_vision_veto` appearing in the eval script (`23-03-PLAN.md:96-107`). The real production setup includes reference fetch, DTW match creation, reference video download, and the final `_apply_vision_veto` call (`app.py:2356-2414`, `app.py:2459-2472`, `app.py:2692-2699`).

**Risk:** A harness can contain `_apply_vision_veto` and still bypass the hard parts: frame selector, cache key, upload accounting, local alignment confidence, or reference-frame mapping. That would re-prove the spike without validating the production integration.

**How I would fix it:** Require runtime trace fields in `eval_stillframe_veto_phase23.json`: `entrypoint`, `selectorVersion`, `studentFrameIndices`, `referenceFrameIndices`, `alignmentConfidence`, `cacheKey`, `cacheHit`, `callCount`, `uploadCount`, `durationMs`, and `pathUsed`. Gate on those fields, not just grep. Ideally run one `_process`-level integration case on Pod with real S3/reference data; if that is too expensive, add a fake-Firestore/fake-S3 integration test that reaches `_process` through the same wiring.

### MEDIUM-3: The objectivity grep gates are over-broad

`23-02-PLAN.md` says recursive schema/prompt tests should reject `"점수"`, `"100"`, `"percent"`, and related strings (`23-02-PLAN.md:185-190`). Existing schema descriptions intentionally contain negative guard text like "점수 아님" and "숫자 점수 금지" (`gemini_vision_scorer.py:144`, `gemini_vision_scorer.py:148`), and `_SCORE_PATTERN` is the real output leak guard (`gemini_vision_scorer.py:97`).

**Risk:** A literal recursive grep can fail on correct negative instructions, or worse, incentivize removing explicit "do not output scores" prompt/schema guidance. That weakens objectivity instead of strengthening it.

**How I would fix it:** Test forbidden output fields separately from negative instructions. For `build_schema`, recursively reject property keys matching `score|overall|rating|percent|100`, but allow descriptions that say scores are forbidden. For prompts, reject positive score examples and output-format requests like `NN/100`, while allowing explicit negative instructions. Keep `_SCORE_PATTERN` tests for generated raw text.

## Overall Assessment

The revised Phase 23 plan is materially stronger than the earlier review target: Mode 3 is formally deferred, percent notation is banned, deterministic geometry is required, local DTW confidence is acknowledged, and 23-03 now targets same-model baseline and a wider eval matrix.

I would still patch the plan before execution. The two most important fixes are: move/root the root-cause path so it actually feeds coaching, and replace raw `body_part` support counting with canonical side-aware fault keys. Without those, the phase can look complete in audit fields while missing the user-facing coaching outcome or corrupting the left/right recall target.
