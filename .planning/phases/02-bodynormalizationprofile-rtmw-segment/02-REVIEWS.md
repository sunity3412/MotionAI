---
phase: 2
phase_dir: .planning/phases/02-bodynormalizationprofile-rtmw-segment
plan_revision: v4
reviewers: [codex]
attempted_reviewers: [claude, codex]
reviewed_at: 2026-06-07T13:12:33Z
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

The plan is unusually thorough and has clearly absorbed prior review feedback, especially around B8 signature preservation, R&D isolation, and avoiding mutable sidecar state. I would not approve it as-is for phase closure, though. Two issues are material: the NLF -> SMPL-X beta comparison path risks producing scientifically meaningless profiles if it tries to derive body ratios from beta without the actual SMPL-X model/joints, and Task 5b still pushes a multi-step console workflow onto belle despite project constraints. The core measurer/pipeline-helper work is directionally sound.

### Strengths

- Strong traceability from BODY-01 to tasks, tests, and ROADMAP criteria.
- Good correction from the earlier sidecar design: `estimate_with_profile()` plus local tuple return is the right race-safe shape for `_RTMWNlfCompat`.
- Firestore/AnalysisDoc deferral is pragmatic and matches Phase 2 scope better than the earlier 4-way lockstep.
- Test plan covers important regressions: y-down convention, stale profile leakage, B8 signatures, import isolation, and warning lockstep.
- R&D import isolation is well-scoped: deployable paths are scanned while `backend/research` remains allowed.

### Concerns

- **HIGH:** The planned `beta_to_body_profile(beta)` is not valid if it is truly "pure NumPy, weights-free" for real SMPL-X beta. Beta coefficients only become body geometry through SMPL-X shapedirs, joint regression, and model data. A weights-free conversion can be a CI fake, but it must not satisfy ROADMAP criterion 4.

- **HIGH:** Task 5b still requires belle to run four repo-root commands, manage env, generate reports, and commit. Project context says belle is non-developer and console/multistep work should not be handed to her. This is a phase-closure blocker unless an operator/agent runs it or it is reduced to one audited command.

- **MEDIUM:** Phase 2 says "automatic output" and "shared input for both engines," but the plan intentionally leaves `_process` unchanged and does not persist or return the profile in the live analysis path. That may be acceptable as a narrowed v1 scope, but the ROADMAP closure language must not imply product-path output yet.

- **MEDIUM:** `BodyNormalizationProfile.__post_init__` currently validates only `confidence` and `warnings` type in [body_normalization.py](/Users/kimtaesung/Dev/SunityMotion/backend/shared/python/sunity_shared/analysis/body_normalization.py:30). The plan relies on the measurer to avoid NaN/inf, but the data contract itself still allows invalid numeric scales.

- **MEDIUM:** `pose_too_inverted` depends on pole-axis sign. If detected pole axes can have arbitrary direction, dot-product inversion can flip warnings. The plan should require a canonical pole-axis sign or use image y-order directly for this warning.

- **MEDIUM:** Synthetic plus adapter-path validation is good, but body-ratio measurement from a full pole trick clip is vulnerable to foreshortening, motion, and occlusion bias. Deferring real RTMW output to v1.5 is honest, but it weakens criterion 1.

- **LOW:** The `estimatedHeightScale` semantic guard only scans `sunity_shared`. Misuse could happen in `backend/functions`, research scripts, or TS once the field is surfaced.

- **LOW:** Verification like `grep -c "bodyNormalizationProfile" app/src/types/analysis.ts -> 1` is brittle. Prefer scoped regex against `AnalysisDoc`.

### Suggestions

- Replace `beta_to_body_profile(beta)` with `smplx_joints_to_body_profile(joints)` for real comparison. CI can use synthetic joint arrays; Pod execution should use actual fitted SMPL-X joints/vertices.
- Convert Task 5b into one script, for example `python -m backend.research.evaluations.run_body_profile_gap_report --videos ... --date ...`, with extract -> loader -> compare -> manifest handled internally.
- Add finite/positive validation for all numeric `BodyNormalizationProfile` fields, not just confidence.
- Clarify ROADMAP status: Phase 2 closes "measurer + helper ready," while "product analysis document contains profile" is Phase 6.
- Canonicalize `PoleAxis.axis_vector` direction before inversion checks, or define inversion from y-down shoulder/hip ordering independent of pole sign.

### Risk Assessment

**Overall risk: MEDIUM-HIGH.** The main implementation path is credible, but the R&D comparison and human checkpoint can undermine phase closure. If those two HIGH items are fixed, the remaining risks are manageable and mostly about validation depth rather than architecture.

## Consensus Summary

Only one reviewer produced usable output, so this is a single-reviewer synthesis rather than true cross-reviewer consensus.

### Highest Priority Findings

- **HIGH:** Replace the planned weights-free `beta_to_body_profile(beta)` as the real SMPL-X comparison path. ROADMAP criterion 4 needs actual fitted SMPL-X joints or vertices, not a fake beta-only conversion.
- **HIGH:** Replace Task 5b's four-command belle console workflow with one audited command or have an operator/agent run it. The project constraints explicitly avoid handing multistep console work to belle.

### Medium Priority Findings

- ROADMAP closure wording should distinguish "measurer + helper ready" from product-path analysis output, which is deferred to Phase 6.
- `BodyNormalizationProfile` should validate numeric scale fields for finite and positive values at the contract boundary.
- `pose_too_inverted` should not depend on arbitrary pole-axis sign.
- Real RTMW output remains deferred to v1.5, so criterion 1 is only partially proven in Phase 2.

### Divergent Views

No divergent views were available because Claude was not authenticated and no other external reviewer was available.
