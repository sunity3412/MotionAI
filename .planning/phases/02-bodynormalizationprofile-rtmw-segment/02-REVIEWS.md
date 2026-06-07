---
phase: 2
phase_dir: .planning/phases/02-bodynormalizationprofile-rtmw-segment
reviewers: [codex]
attempted_reviewers: [claude, codex]
reviewed_at: 2026-06-07T10:01:29Z
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

## Summary

`02-01-PLAN.md` is directionally strong and well aligned with BODY-01: it keeps RTMW as the operating backbone, avoids new heavy dependencies, defines confidence/warnings, adds tests, and preserves SMPL-X as R&D-only. However, as written it has several execution blockers and one scope/acceptance mismatch. The biggest issue is that `_RTMWNlfCompat.estimate()` currently returns only a COCO array, so injecting `body_shape` into internal `PoseFrame` objects is likely discarded and not available downstream. The R&D comparison is also only stubbed while the roadmap success criterion requires an actual gap report.

## Strengths

- Clear mapping from ROADMAP success criteria to tasks and tests.
- Good architectural boundary: pure numpy measurer under `sunity_shared.analysis`, R&D comparison under `backend/research`.
- Conservative smoothing choice: MAD rejection plus robust median is reasonable for occlusion-heavy pole-sports footage.
- Warnings-first design matches the project's "do not overclaim" coaching principle.
- Firestore persistence is intentionally deferred, which avoids schema churn during a narrow algorithm phase.
- The import-isolation idea is valuable for SMPL-X/NLF license containment.

## Concerns

- **HIGH: `body_shape` injection may be discarded.** `backend/functions/pipeline/app.py` returns `to_coco17_array(pose_frames)`, not `PoseFrame[]`. If the profile is only attached before conversion, the phase does not actually make BodyNormalizationProfile available to downstream engines.

- **HIGH: Fixture plan references APIs/schema that do not exist.** The plan says fixtures should pass `PoseFrame.from_dict()`, but `pose_frame.py` has no `from_dict`. The proposed JSON also uses `timestamp_seconds`, `origin`, and incomplete `Keypoint3D` fields, while the dataclasses require `timestamp_ms`, no `origin` on `PoleAxis`, and `uncertainty_proxy`.

- **HIGH: Task 6 import-isolation test would fail as written.** Existing `sunity_shared` still has lazy MediaPipe imports in `pose_engines/mediapipe_engine.py`. Blocking `mediapipe` imports globally without removing or exempting legacy modules creates an immediate test failure and expands scope beyond Phase 2.

- **HIGH: R&D comparison success criterion is not actually met.** Task 5 creates a `NotImplementedError` SMPL-X stub, but ROADMAP criterion 4 requires a same-video NLF -> SMPL-X beta gap report. A scaffold plus smoke test should not count as completion of that criterion.

- **MEDIUM: Synthetic-only tests can validate math but not RTMW integration.** Because no real RTMW keypoint dump is used, tests will not catch real coordinate orientation, confidence distribution, keypoint naming, or adapter quirks.

- **MEDIUM: Inversion warning likely depends on coordinate convention.** `mid_shoulder.y < mid_hip.y` may be wrong depending on whether coordinates are image, RTMW normalized, or pole-aligned. Synthetic fixtures can accidentally encode the same wrong assumption.

- **MEDIUM: `armScale`, `legScale`, and `estimatedHeightScale` semantics are under-specified.** `estimatedHeightScale = (arm + leg + torso) / 3` is not an estimated height scale in the normal sense. This could mislead Phase 6 unless the contract explicitly says it is a torso-relative proportion heuristic.

- **LOW: Lockstep warning enum is only grep-verified.** Current lockstep tests check field presence, not warning enum consistency. The plan's supplemental grep is useful but should become an automated assertion.

## Suggestions

- Add an explicit propagation design before implementation: either return a `PoseEstimationResult(pose_frames, coco17_array, body_profile)` object, add a helper that downstream can call, or persist `bodyNormalizationProfile` at the analysis-result boundary now. Test the actual boundary that Phase 6 will consume.

- Replace JSON fixture deserialization assumptions with a real helper: either add `PoseFrame` test factory functions in Python, or implement explicit `pose_frame_from_dict()` test utility matching the actual dataclasses.

- Narrow Task 6 import isolation to `backend.research`, `research`, `nlf`, `smplx`, and `smpl_x` first. Treat MediaPipe removal as a separate cleanup unless this phase also deletes or quarantines existing MediaPipe modules.

- Split R&D harness into two acceptance levels: scaffold smoke test for this plan, and real gap-report generation as a required manual or automated gate before marking ROADMAP criterion 4 complete.

- Add one real RTMW fixture if possible, even a small regenerated dump from one known video. Keep synthetic cases for warning coverage, but include one integration fixture for naming and coordinate sanity.

- Use pole-aligned torso direction or a documented coordinate-frame helper for `pose_too_inverted`, instead of raw `y` comparisons.

- Update contract wording for `estimatedHeightScale` to state "torso-relative body proportion heuristic, not absolute height," or defer that field's meaningful use until BODY-02/Phase 6.

## Risk Assessment

**Overall risk: HIGH as written.** The plan is conceptually solid, but it currently has at least three implementation blockers: discarded `body_shape` propagation, nonexistent fixture deserialization, and an import-isolation rule that conflicts with existing shared code. It also risks overstating completion of the R&D comparison criterion. Once those are corrected, the remaining algorithmic risk looks medium and manageable.

---

## Consensus Summary

Only one reviewer produced usable output, so this is a single-reviewer synthesis rather than true cross-reviewer consensus.

### Agreed Strengths

- The plan is well aligned with BODY-01 and the RTMW pivot.
- The pure numpy measurer boundary is appropriate.
- The R&D-vs-production separation is the right architecture.
- Warnings-first confidence handling matches the product's trust constraints.
- The planned tests are broad in intent and cover unit, contract, pipeline, and isolation surfaces.

### Agreed Concerns

- **Highest priority:** BodyNormalizationProfile propagation is not proven because the current pipeline adapter converts `PoseFrame[]` to a COCO array and discards `body_shape`.
- **Highest priority:** fixture/schema assumptions must be aligned with the actual `PoseFrame`, `PoleAxis`, and `Keypoint3D` dataclasses.
- **Highest priority:** MediaPipe import blocking conflicts with existing lazy MediaPipe modules under `sunity_shared`; the isolation rule needs narrowing or a separate cleanup plan.
- **Highest priority:** an SMPL-X stub cannot satisfy the roadmap's R&D gap-report criterion.
- **Medium priority:** at least one real RTMW fixture should supplement synthetic fixtures to catch coordinate and keypoint-name drift.

### Divergent Views

No divergent views were available because Claude was not authenticated and no other external reviewer was available.
