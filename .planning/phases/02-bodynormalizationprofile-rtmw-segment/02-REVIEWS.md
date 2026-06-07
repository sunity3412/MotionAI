---
phase: 2
phase_dir: .planning/phases/02-bodynormalizationprofile-rtmw-segment
plan_revision: v2
reviewers: [codex]
attempted_reviewers: [claude, codex]
reviewed_at: 2026-06-07T11:45:10Z
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

The plan is much stronger than a typical phase plan: it has clear traceability, explicit gates, fixture strategy, lockstep contract checks, R&D isolation, and a realistic human checkpoint for SMPL-X comparison. However, I would not approve it as-is. The main risks are not missing ambition; they are integration mismatches with the current pipeline/tests, a likely wrong `pose_too_inverted` coordinate convention, and an R&D gate that can fail or break tests after implementation.

### Strengths

- Strong traceability from BODY-01 success criteria to concrete tasks and tests.
- Good correction of earlier plan issues: `PoseFrame.from_dict` is acknowledged as absent, fixtures are test-only, and SMPL-X is kept out of product code.
- `measure_body_profile()` is appropriately scoped as a pure numpy function.
- Firestore propagation is a reasonable answer to "Phase 6 consumer can access it."
- The plan correctly treats the real NLF -> SMPL-X report as a human/RunPod gate, not something a scaffold can satisfy.
- Contract lockstep testing for warning enums and scale semantics is valuable.

### Concerns

- **HIGH:** Task 4 changes `_angles_from_video` / `_angles_and_video_path_from_video` return contracts but does not include all existing migration work. Current tests explicitly lock `_angles_from_video(...) -> np.ndarray` in [test_pipeline_recognizer_switch.py](/Users/kimtaesung/Dev/SunityMotion/backend/tests/test_pipeline_recognizer_switch.py:225), and Gemini integration stubs return only `angles` or `(angles, path)`. Without updating those tests/stubs, `pytest tests/ -x` will fail.

- **HIGH:** `pose_too_inverted` is probably sign-wrong for the current RTMW coordinate convention. RTMW stores image pixel coordinates where `y` increases downward, and the default pole axis is `(0, 1, 0)` in [app.py](/Users/kimtaesung/Dev/SunityMotion/backend/functions/pipeline/app.py:214). For upright posture, `mid_shoulder - mid_hip` has negative y, so `dot(torso_vec, pole_axis) < 0` would flag normal upright frames as inverted. The proposed "raw y flip but same PoleAxis" test is also mathematically invalid.

- **HIGH:** Task 5a/5b test lifecycle is inconsistent. Task 5a plans a smoke test that asserts `load_nlf_smplx_keypoints()` raises `NotImplementedError`; Task 5b then replaces that stub. Unless the smoke test is updated in Task 5b, the final full suite will fail.

- **HIGH:** The R&D report gate still lacks a reliable RTMW input generation path. The plan acknowledges the Phase 1 sweep keypoint dump is absent, but Task 5b's command still assumes `.../sweep_rtmw_<date>/keypoints/` exists. Add an explicit RTMW extraction/profile-generation path from the same 5 videos.

- **MEDIUM:** Import isolation only scans `sunity_shared`. Product/deployed code also includes `backend/functions` and `backend/runpod_inference`; a legal leak through `pipeline/app.py` would not be caught. The isolation test should cover all deployable product paths, excluding `backend/research` and tests.

- **MEDIUM:** Firestore `bodyNormalizationProfile` is a new `AnalysisDoc` field, but Task 4 does not require updating `docs/contract.md`'s `AnalysisDoc` section. Updating only `analysis.ts` and `firestore_admin.py` leaves the contract incomplete.

- **MEDIUM:** Dependency ordering is inconsistent. Task 6 depends only on Task 5a, but the summary chain places it after blocking human Task 5b. Run Task 6 before the human gate so R&D isolation and REQUIREMENTS RTMW alignment land even if the Pod report is delayed.

- **LOW:** Some verification commands are path-fragile. From `cd backend`, `python -m backend.research...` is likely wrong; existing R&D docs run that module from repo root. Use either repo-root execution or `python -m research.evaluations...`.

### Suggestions

- Treat Task 4 as a full call-contract migration: update `test_pipeline_recognizer_switch.py`, all Gemini integration stubs, docstrings, and any return annotation gates in the same atomic commit.
- Consider a small `PoseEstimateResult` dataclass instead of naked tuples. It will reduce tuple-order mistakes across `_RTMWNlfCompat`, `_angles_from_video`, and Gemini path helpers.
- Redefine inversion with verified RTMW coordinates. Likely options: use `mid_hip - mid_shoulder`, or compute from pole-aligned coordinates with a documented "up/down" convention. Add a fixture derived through `convert_rtmw_keypoints_to_coco17_and_pole_ext`, not only synthetic hand-authored frames.
- Revise Task 5b so it also updates/removes the "stub must raise" smoke test after implementation.
- Extend import-isolation scanning to `backend/shared/python/sunity_shared`, `backend/functions`, and `backend/runpod_inference`, and optionally catch dynamic imports like `importlib.import_module("smplx")`.
- Add explicit finite/zero-denominator tests for torso length, hip width, shoulder width, and all scale outputs. `BodyNormalizationProfile.__post_init__` does not currently validate finite numeric scale values.

### Risk Assessment

**Overall risk: MEDIUM-HIGH.** The architecture is sound and the plan is detailed, but the current version has several high-probability integration failures and one likely algorithmic sign error. Fixing the tuple migration scope, inversion convention, and Task 5 lifecycle would bring this down to MEDIUM.

## Consensus Summary

Only one reviewer produced usable output, so this is a single-reviewer synthesis rather than true cross-reviewer consensus.

### Highest Priority Findings

- **HIGH:** Task 4 needs a complete call-contract migration for `_angles_from_video`, `_angles_and_video_path_from_video`, existing signature tests, Gemini integration stubs, docstrings, and any return annotation gates.
- **HIGH:** `pose_too_inverted` likely uses the wrong sign convention for RTMW image coordinates and default pole-axis orientation. The test design should be revised against verified RTMW coordinates.
- **HIGH:** Task 5a and Task 5b have a conflicting test lifecycle: a smoke test that expects `NotImplementedError` must be updated or removed when the real loader is implemented.
- **HIGH:** The R&D gap-report gate still needs an explicit RTMW extraction/profile-generation path from the same five comparison videos.

### Medium Priority Findings

- Import isolation should cover deployable product paths, including `backend/functions` and `backend/runpod_inference`, not only `sunity_shared`.
- The new Firestore top-level `bodyNormalizationProfile` field should be added to `docs/contract.md`'s `AnalysisDoc` section.
- Task 6 should be ordered before the blocking human/RunPod gate so product-safe cleanup and requirement alignment can land while the R&D report is pending.

### Divergent Views

No divergent views were available because Claude was not authenticated and no other external reviewer was available.
