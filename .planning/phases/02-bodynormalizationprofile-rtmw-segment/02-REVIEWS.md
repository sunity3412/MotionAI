---
phase: 2
phase_dir: .planning/phases/02-bodynormalizationprofile-rtmw-segment
plan_revision: v3
reviewers: [codex]
attempted_reviewers: [claude, codex]
reviewed_at: 2026-06-07T12:14:36Z
plans_reviewed: [02-01-PLAN.md]
review_limitations:
  - "Claude CLI was installed but failed before review: Not logged in - Please run /login"
  - "Gemini, CodeRabbit, OpenCode, Qwen, and Cursor CLIs were missing"
  - "No local OpenAI-compatible reviewer server was running on Ollama, LM Studio, or llama.cpp"
  - "Codex CLI completed as a fallback reviewer. This is code-grounded feedback, but not fully independent from the current Codex session."
---

# Cross-AI Plan Review - Phase 2

## Reviewer Availability

- Claude CLI was installed but failed before review: `Not logged in - Please run /login`.
- Gemini, CodeRabbit, OpenCode, Qwen, and Cursor CLIs were not installed.
- No local OpenAI-compatible reviewer server was running on Ollama, LM Studio, or llama.cpp.
- Codex CLI completed as a fallback reviewer. This is useful code-grounded feedback, but it is less independent than a successful cross-model review.

## Codex Review

### Summary

The plan is unusually thorough and does a good job preserving prior review feedback, especially around B8 signature preservation, RTMW coordinate convention, lockstep schema updates, and R&D isolation. As-is, I would not approve it without one design change: `_RTMWNlfCompat.last_body_profile` as a shared mutable sidecar is risky in the RunPod/FastAPI background-task path. The plan is otherwise strong, but Task 5b also hides too much real implementation behind a human checkpoint.

### Strengths

- Clear traceability from BODY-01 success criteria to concrete tasks and tests.
- Good preservation of B8 signature locks in [test_pipeline_recognizer_switch.py](/Users/kimtaesung/Dev/SunityMotion/backend/tests/test_pipeline_recognizer_switch.py:225).
- RTMW image y-down convention is explicitly handled, with adapter-path tests planned.
- R&D import isolation is scoped correctly and avoids breaking legacy MediaPipe code prematurely.
- Contract lockstep thinking is strong: `docs/contract.md`, TS, Python dataclass, Firestore payload.
- The plan avoids new numeric dependencies like scipy and keeps the measurer as a pure numpy module.

### Concerns

- **HIGH: Shared `last_body_profile` can race or leak across analyses.** `_POSE_ESTIMATOR` is global in [pipeline/app.py](/Users/kimtaesung/Dev/SunityMotion/backend/functions/pipeline/app.py:116), and RunPod accepts FastAPI `BackgroundTasks` in [server.py](/Users/kimtaesung/Dev/SunityMotion/backend/runpod_inference/server.py:198). `--workers 1` does not prove only one background analysis is active. Sequential leakage tests are not enough.

- **HIGH: Task 5b contains substantial hidden implementation.** It asks belle to implement the real NLF -> SMPL-X beta loader, run RTMW extraction, generate reports, and commit data. That is more than a checkpoint. Also, the scaffold describes `load_nlf_smplx_keypoints() -> list[PoseFrame]`, while the actual R&D output should likely be per-video `BodyNormalizationProfile`.

- **MEDIUM: Firestore persistence expands scope.** Saving `bodyNormalizationProfile` is useful for Phase 6, but the research recommendation originally leaned toward RAM-only until Phase 6. If kept, this needs app-side type/build verification, not only backend pytest.

- **MEDIUM: Verification is still mostly synthetic.** RTMW-adapter-derived fixtures are useful, but they do not prove the real RTMW engine output distribution, detector behavior, or real video score confidence. The real keypoint dump is deferred to Task 5b, which means success criterion 1 is only partially proven before the human gate.

- **MEDIUM: `estimatedHeightScale` remains semantically weak.** The plan documents it as a torso-relative heuristic, which helps, but the field name still implies actual height. This can mislead Phase 6 unless consumers are explicitly tested to treat it as a coarse proportion hint only.

- **LOW: "AST lockstep" is mostly substring validation.** That is acceptable for enum drift, but the plan should call it string/regex lockstep rather than AST validation.

- **LOW: Import isolation does not catch all dynamic imports.** It catches `importlib.import_module("smplx")`, but not `__import__("smplx")`, nonliteral dynamic imports, or `spec_from_file_location` abuse. This is probably acceptable, but worth documenting as residual risk.

### Suggestions

- Replace the mutable sidecar with a local return path that preserves B8: add a new helper such as `_angles_and_body_profile_from_video(...) -> tuple[np.ndarray, BodyNormalizationProfile | None]`; leave `_angles_from_video(...) -> np.ndarray` unchanged for B8 compatibility.
- Add a concurrency regression test with two overlapping `_process` calls and a barriered fake estimator to prove profiles cannot cross between analyses.
- Add a stale-failure test: if pose estimation raises after a previous successful call, no old `BodyNormalizationProfile` can be written.
- Make Task 5b execution-only. Move the real NLF -> SMPL-X loader design into Task 5a or a separate auto task, and make its loader return per-video `BodyNormalizationProfile` records.
- Add app verification after `AnalysisDoc.bodyNormalizationProfile?`, for example the repo's existing TypeScript compile/test command under `app`.
- Promote one real RTMW PoseFrame JSON fixture into committed test data when Task 5b produces keypoint dumps, then run the measurer against it as a non-skip regression.

### Risk Assessment

**Overall risk: HIGH as written.** The implementation plan is technically mature, but the shared mutable sidecar is a real correctness risk in the RunPod background-task architecture, and Task 5b hides critical R&D implementation behind a manual gate. If the profile propagation is changed to a local return/helper path and Task 5b is narrowed to execution/reporting, the risk drops to **MEDIUM**.

## Consensus Summary

Only one reviewer produced usable output, so this is a single-reviewer synthesis rather than true cross-reviewer consensus.

### Highest Priority Findings

- **HIGH:** Replace the planned `_RTMWNlfCompat.last_body_profile` mutable sidecar. The global estimator plus RunPod background tasks can race or leak profiles across analyses.
- **HIGH:** Narrow Task 5b so it is an execution/reporting gate, not hidden design and implementation work for the NLF -> SMPL-X loader and RTMW extraction path.

### Medium Priority Findings

- Firestore persistence should include app-side type/build verification if `bodyNormalizationProfile` remains a top-level `AnalysisDoc` field.
- Real RTMW output coverage is still deferred; synthetic and adapter-derived fixtures do not fully prove engine-output stability.
- `estimatedHeightScale` remains a potentially misleading field name and should be protected by consumer semantics tests.

### Divergent Views

No divergent views were available because Claude was not authenticated and no other external reviewer was available.
