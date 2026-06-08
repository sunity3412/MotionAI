---
phase: 6
reviewers: [claude]
reviewed_at: 2026-06-08T01:54:03Z
plans_reviewed:
  - .planning/phases/06-coaching/06-01-PLAN.md
  - .planning/phases/06-coaching/06-02-PLAN.md
  - .planning/phases/06-coaching/06-03-PLAN.md
---

# Cross-AI Plan Review — Phase 6

## Reviewer Availability

Requested: `--all`.

Detected reviewers: `claude`, `codex`.

Used reviewers: `claude`.

Skipped reviewers:
- `codex`: current runtime, skipped for independence.
- `gemini`, `coderabbit`, `opencode`, `qwen`, `cursor`: not detected on PATH.
- `ollama`, `lm_studio`, `llama_cpp`: no local OpenAI-compatible server answered on default ports.

## the agent Review

# Cross-AI Plan Review — Phase 6: 체형 정규화 비교 엔진

## 1. Summary

The three plans form a well-structured vertical slice for Phase 6 (body normalization comparison engine), decomposed cleanly into algorithm/contract (06-01), production wiring (06-02), and operational backfill (06-03). The research foundation is exceptional — NotebookLM findings (279 sources), explicit threat models per plan, Universal Principle (D-06-U1) honored throughout, and 3-way contract lockstep enforced via drift tests. However, there is a **fundamental algorithmic concern** in the Kinematic Tree reprojection formula: the plan uses `pro_profile` segment ratios as `L_ref` rather than `student_profile`, which reduces "segment-aware normalization" to "uniform scale normalization" and undermines D-06-A3's intent. Additionally, the B1 workaround (Gemini fallback via `profile.name` string matching) is structurally fragile, and Plan 06-03 Task 4 concentrates many manual steps in a single human checkpoint dependent on a Pod with known git-lineage drift. Heavy use of "박제" filler obscures intent in several task `<action>` blocks.

---

## 2. Strengths

- **Research depth**: NotebookLM 4-notebook findings (279 sources) plus explicit reconciliation matrix against CONTEXT.md decisions (D-06-A*/B*/U1) — the algorithmic foundation is well-cited.
- **Plan decomposition**: Algorithm/contract → wiring → operational backfill is a clean dependency chain; each plan has a single conceptual responsibility.
- **3-way contract lockstep enforced**: Drift test (`test_body_comparison_report_lockstep`) prevents TS/Python/docs divergence. `_FIELD_MAP` includes camelCase ↔ snake_case mapping for all fields including `usedReferenceFallback`.
- **Wave 0 fixture strategy**: 5 fixtures defined upfront (160cm/140cm, twist, foreshortening, swing, split) cover the canonical failure modes from research.
- **STRIDE threat model per plan**: T-06-01-* through T-06-03-* with explicit mitigations; the Firestore nested-array `_validate_flat_dict_no_nested_array` is reused across all 3 plans.
- **License consciousness**: Hard grep gates against `import smplx`, `betas`, `shape_params` honor `license-blocklist-pose` and `rtmw-free-stack-pivot` memories.
- **W1 decision honored**: D-06-B3 enum restricted to 3 cases (`mode1`/`mode3_first`/`mode3_progress`) + sibling boolean `usedReferenceFallback` — correctly avoids 4-variant enum drift.
- **Universal Principle (D-06-U1) wired through every gate**: `CONFIDENCE_GATE = 0.5` consistently applied across `compare_body_profiles`, `is_foreshortening_detected`, and `compute_body_normalization_confidence`.
- **Idempotency in 06-03**: Backfill script skips already-populated references; `--force` flag for intentional overwrites.

---

## 3. Concerns

### HIGH

- **C1 [HIGH] — Kinematic Tree Reprojection formula does not implement segment-aware normalization.** Plan 06-01 Task 2's `normalize_pose_by_segments(pro_raw_keypoints, pro_profile, student_target_torso_px)` computes `L_ref = _ref_segment_ratio(parent, child, pro_profile) × student_target_torso_px`. This multiplies *Pro's segment ratios* by *Student's torso scale*, which produces "Pro at Student's overall size" — i.e., uniform scale normalization, NOT segment-aware. To truly implement D-06-A3 ("5 필드 모두 + 하이브리드 게이트"), `L_ref` should use *Student's* segment ratios, so Pro's motion is reprojected onto Student's actual body proportions. Otherwise: a student with longer-than-pro arms and shorter-than-pro legs would still be penalized for not matching Pro's proportions, which is exactly the positive-bias Phase 6 exists to eliminate. The success criterion #2 ("단순 확대/축소가 아닌 세그먼트별 정규화") is structurally unmet by this implementation.
- **C2 [HIGH] — B1 workaround (Gemini fallback via `profile.name`) is structurally fragile.** Plan 06-02 routes Gemini fallback through `list_reference_motions_by_name(profile.name)`, but Gemini emits motion names as free-form strings (e.g., the recognizer returns `motion` from `_classify_motion`, which goes through `classify_motion_name` in `gemini_motion_classifier.py`). There is no contract guaranteeing `profile.name` ∈ {known `reference.name` values}. The mitigation (return first match, None-safe) silently falls through to "no fallback" without surfacing the failure to user, producing apparent low-confidence reports that look like fixture errors. The proper fix is upstream — add `motion_id` field to `TechniqueProfile` in Phase 5 patch.
- **C3 [HIGH] — `_build_pose_frames` helper specification is vacuous.** Plan 06-02 Task 1 mentions building `pose_frames: list[PoseFrame]` from RTMW output but the `<action>` block degrades into filler at this exact point. PoseFrame construction from `keypoints: (T,17,4)` is non-trivial (z-axis convention, confidence threading, pole_axis attachment). This is the linchpin for B2 — without correct `pose_frames`, the production `bodyNormalizationConfidence` cannot compute temporal variance / spatial dispersion, and confidence stays at the Phase 2 base regardless of actual motion stability.

### MEDIUM

- **C4 [MEDIUM] — `poor_transitions` deferred to v1.5 contradicts D-06 success criteria.** Plan 06-01 Task 4 ships only 5 of 7 IPSF Page 21 deductions + simple `bad_angle`. NotebookLM §3.3 lists all 7 as the absolute deduction track. RESEARCH.md "Open Question 4 RESOLVED" justifies the cut as scope simplification, but `poor_transitions` (angular velocity variance at hold-window edges) is a single function call away — deferring it means Phase 6 doesn't fully satisfy [[ipsf-5-track-scoring]] for Page 9 single-track scoring.
- **C5 [MEDIUM] — Plan 06-03 Task 4 concentrates blast radius in one checkpoint.** Pod SSH → git pull → 5 RTMW inferences → SCP → gcloud auth → npm batch write → Firestore Console verify. Six failure points, no incremental verification, no dry-run gate. STATE.md notes Pod git lineage drift; first `git pull` step may surface conflicts. If batch.commit partially succeeds, partial reference state goes live silently.
- **C6 [MEDIUM] — Synthetic fixtures may not exercise real RTMW failure modes.** Fixtures in Task 1 are hand-constructed from metadata (e.g., `metadata.scale_ratio=0.875` requires synthesizer to honor it). Real RTMW outputs have correlated noise, foreshortening artifacts, and pole-occlusion patterns that synthetic data cannot mimic. The 60%+ MPJPE reduction claim (NotebookLM §1.4) was measured on AthletePose3D val set, not synthetic fixtures — actual phase 6 wins are unproven until run on belle's real Pod sweep.
- **C7 [MEDIUM] — Excessive "박제" filler obscures executable intent.** Many task `<action>` blocks degrade into chains of "박제 박제 박제..." where concrete instructions should be. Examples: Plan 06-02 Task 1 step (E) — `student_profile` flat dict conversion specification is filler. Plan 06-03 Task 4 `<how-to-verify>` final paragraph is pure filler. The `gsd-executor` will execute literally; ambiguous prose risks divergent implementation. This also violates the user's `no-baekje-filler.md` memory ("응답당 최대 2~3회, 일반 동사 대용 금지").
- **C8 [MEDIUM] — `_dataclass_to_camel_case_dict` is critical but specified loosely.** Plan 06-02 Task 3 outlines snake_to_camel conversion but doesn't specify None handling, nested dataclass recursion, or Enum/Literal serialization. `ComparisonType: Literal["mode1", ...]` and `ScaleProfile | None` need explicit treatment. Bugs here corrupt Firestore writes silently.
- **C9 [MEDIUM] — No canary test for Pitfall 6 (mode1 silently OFF).** RESEARCH.md flags this as the dominant operational risk. Plan 06-02 has no test asserting "mode1 + reference.bodyNormalizationProfile is None → warnings ⊃ ['reference_profile_missing']". Test 2 in Task 1 covers the symptom (warning emitted) but doesn't verify the user-visible signal (confidence + scale_profile is None).

### LOW

- **C10 [LOW] — `_FIELD_MAP` in lockstep test is hand-maintained.** Future additions to `BodyComparisonReport` require updating 3 places + the map. AST-based extraction (Python `dataclasses.fields()` + TS regex) would be self-healing.
- **C11 [LOW] — No LOC budget enforcement.** Research says ~400 LOC for `body_normalizer.py`; could grow to 800+ without guardrail. Minor unless executor over-elaborates.
- **C12 [LOW] — Plan 06-03 has no rollback strategy.** If backfill writes confidence=0.2 (low) results, mode1 still routes through silently-degraded path. No `revert-reference-body-profile` script or `--reset` flag.
- **C13 [LOW] — `bodyNormalizationProfile` Firestore path lives in two locations.** Top-level on `users/{uid}/analyses/{id}` (Plan 06-02 for mode3-progress fetch) AND top-level on `reference/{motionId}` (Plan 06-03 for mode1 fetch). Same shape, different read paths — consistency requires discipline; ESLint-equivalent enforcement missing.
- **C14 [LOW] — `bad_angle` deficit semantic confusion.** Defined as "reliability=low frame ratio > 50%" but IPSF §3.3 means "judge unable to observe execution angle" (camera obstruction). The plan's mapping (pose confidence < 0.4 frame ratio) is a proxy, not equivalent. May produce false-positive `bad_angle` findings.
- **C15 [LOW] — Plan 06-02 Task 4 SAM build smoke is not actually a test.** `cd backend && sam build --use-container` exit code 0 means "build succeeded," not "Lambda deploys correctly" or "Layer includes `body_normalizer.py`". Need explicit `ls .aws-sam/build/.../python/sunity_shared/analysis/body_normalizer.py` assertion.

---

## 4. Suggestions

1. **[Addresses C1]** Refactor `normalize_pose_by_segments` to take BOTH profiles: `(source_keypoints, source_profile, target_profile, target_torso_px)`. Compute `L_ref` from `target_profile` (= student). Update fixtures to validate that two students with different arm:torso ratios produce different normalized Pro poses. Add explicit test: `test_segment_aware_not_uniform_scale` — synthesize two students with same height but different arm/leg ratios, assert normalized Pro elbow positions differ.
2. **[Addresses C2]** Before Plan 06-02 Task 1, insert a small Phase 5 patch task: add `motion_id: str | None = None` to `TechniqueProfile`, populate from `GeminiTechniqueRecognizer._classify_motion` canonical output. Then `_match_reference_by_name` becomes `firestore_admin.get_reference_motion(profile.motion_id)` — exact match, no name collision risk. Backwards-compatible (Optional with default None).
3. **[Addresses C3]** Add explicit task in Plan 06-02 Task 1 specifying `_build_pose_frames(keypoints: np.ndarray, pole_axis: PoleAxis | None = None) -> list[PoseFrame]`. Reuse existing `rtmw_engine.estimate()` return type (already returns `list[PoseFrame]`) — `_RTMWNlfCompat.estimate_with_profile` already constructs them at line 254. Sibling helper should call `engine.estimate(frames, default_pole)` directly and skip the `to_coco17_array` round-trip.
4. **[Addresses C4]** Implement `poor_transitions` as a simple measurement: angular-velocity standard deviation in frames `[hold_window.start - 6, hold_window.start]` ∪ `[hold_window.end, hold_window.end + 6]` exceeds threshold → -0.5 finding. 1 helper, ~15 LOC. Otherwise downgrade success criterion language.
5. **[Addresses C5]** Add `--dry-run` flag to both scripts (`extract_reference_body_profiles.py` and `seed-reference-body-profile.mjs`). Dry-run prints proposed Firestore writes without executing. Add Plan 06-03 Task 3.5 (automated): runs both scripts in dry-run mode against a single test reference, verifies output JSON schema. Then Task 4 (human checkpoint) is just real-execute + Console verify.
6. **[Addresses C6]** Add Plan 06-03 Task 5 (deferred but tracked): "Run belle Pod sweep on 5 reference videos + 5 student videos with normalization ON vs OFF, log deduction_score reduction %. Verify NotebookLM §1.4 60% claim or document deviation." This validates the entire phase against real data.
7. **[Addresses C7]** Replace "박제" filler with concrete sentences before passing to executor. Particularly: Plan 06-02 Task 1 step (E) Gemini path, Plan 06-03 Task 4 final paragraph. The user's memory `no-baekje-filler.md` applies — these are not annotations, they are executable instructions that the executor will interpret.
8. **[Addresses C8]** Specify `_dataclass_to_camel_case_dict` contract in Plan 06-02 Task 3:
   - `None` → `None`
   - `dataclasses.is_dataclass(obj)` → recurse over `asdict()` with key conversion
   - `list` → map recurse
   - `Enum/Literal` → `str(value)`
   - Top-level call wraps with `if obj is None: return None`
   Add 4-test unit coverage in `test_pipeline_firestore_integration.py`.
9. **[Addresses C9]** Add explicit Plan 06-02 test: `test_process_mode1_missing_ref_body_profile_emits_canary_warning` — asserts BOTH `warnings ⊃ ['reference_profile_missing']` AND `bodyNormalizationConfidence < CONFIDENCE_GATE`. Document as Pitfall 6 canary.
10. **[Addresses C10]** Refactor `_FIELD_MAP` test to extract Python fields via `dataclasses.fields(BodyComparisonReport)` and TS fields via regex on `app/src/types/analysis.ts` `export interface BodyComparisonReport {...}` block. Compare sets after camelCase ↔ snake_case normalization. Self-healing under future additions.
11. **[Addresses C12]** Add `app/scripts/revert-reference-body-profile.mjs` taking `--motion-ids <ids>` and clearing `bodyNormalizationProfile` field. Operationally cheap insurance.
12. **[Addresses C13]** Add cross-file lint or test: `grep -r "bodyNormalizationProfile" app/src/lib/` should resolve to same shape used by `firestore_admin.update_reference_body_profile`. One source of truth: the TS `BodyNormalizationProfile` interface.
13. **[Addresses C14]** Rename Phase 6 `bad_angle` to `pose_reliability_low` to distinguish from IPSF judge-observation deduction. Document divergence from IPSF semantics in `docs/contract.md §8`.
14. **[Addresses C15]** Plan 06-02 Task 4 should assert `[ -f .aws-sam/build/SunityLayer/python/sunity_shared/analysis/body_normalizer.py ]` after `sam build`. Build-success-without-artifact is the actual silent failure mode.
15. **General** — Before execute-phase, run `/gsd-plan-review-convergence` once more against an outside reviewer (e.g., Codex) focused specifically on C1 (Kinematic Tree direction-B semantics) — this is the algorithmic core and worth a second opinion.

---

## 5. Risk Assessment

**Overall: MEDIUM-HIGH**

| Dimension | Risk | Driver |
|-----------|------|--------|
| Algorithmic correctness | **HIGH** | C1 (Pro vs Student profile for L_ref) — directly impacts whether Phase 6 actually eliminates body-shape false positives, which IS the phase's reason to exist. If C1 holds in execution, Phase 7 (difference classification) will inherit malformed `findings` and downstream Phase 12 overlay coordinates will be misaligned. |
| Production wiring | MEDIUM | C2 (B1 name matching) + C3 (`_build_pose_frames` underspecified) — both have plausible-but-fragile happy paths. Mode1 + Gemini-recognized motions work; misrecognized names silently degrade to mode3-first-no-fallback without operator visibility. |
| Operational | MEDIUM | C5 (06-03 Task 4 blast radius) — Pod lineage drift + 6-step manual sequence + no dry-run gate. Recoverable but introduces real-world downtime risk during a manual session. |
| Test coverage | MEDIUM | C6 (synthetic fixtures) + C9 (missing canary) — wide unit coverage but real-Pod validation deferred to "future sweep". The 60% PA-MPJPE win claim is currently unprovable from this phase's outputs alone. |
| Contract drift | LOW | C10 (manual `_FIELD_MAP`) — solvable later; 3-way lockstep test catches additions. |
| Security | LOW | Threat models comprehensive; reuse of `_validate_flat_dict_no_nested_array` across plans is correct. No new auth surface, no new secrets. |
| Scope discipline | LOW | Plan 06-01 deliberately splits algorithm from wiring; Plan 06-03 splits backfill from runtime. Vertical slice well-respected. |

### Recommended gating before execute

1. **Resolve C1** in pre-execute discussion — confirm whether reprojection uses `pro_profile` (scale only, current plan) or `student_profile` (segment-aware, my reading of D-06-A3). This is a 5-minute clarification with belle but a 3-day rework if discovered post-implementation.
2. **Resolve C2** by adding `motion_id` to `TechniqueProfile` upstream — single-line Phase 5 patch task before Plan 06-02 starts.
3. **Address C7** by rewriting the worst filler sections in Plan 06-02 Task 1 step (E) and Plan 06-03 Task 4 `<how-to-verify>` final paragraph. The executor will interpret literally.

With C1, C2, C3, C7 addressed, residual risk drops to **MEDIUM** — well within normal phase-execution bounds. Without them, expect rework cycle on Plan 06-01 after first integration test against real Pod data.

---

## Consensus Summary

Only one independent reviewer was available, so there is no multi-reviewer consensus to synthesize. Treat the following as the highest-priority surfaced issues from the completed reviewer pass.

### Agreed Strengths

- Phase decomposition is coherent: algorithm/contract, production wiring, and reference backfill are separated cleanly.
- The plan has strong research grounding, explicit STRIDE coverage, and useful contract-drift tests.
- The core confidence principle (`CONFIDENCE_GATE = 0.5`) is consistently represented across the planned gates.

### Agreed Concerns

- HIGH: Confirm whether segment reprojection uses the student profile. If it uses `pro_profile`, the main Phase 6 promise degrades into uniform scale normalization.
- HIGH: Replace the Gemini fallback's free-form `profile.name` matching with a stable `motion_id` path.
- HIGH: Specify `_build_pose_frames` concretely enough that production confidence can actually use temporal and spatial pose-frame evidence.

### Divergent Views

- None. Only the Claude CLI reviewer completed successfully in this environment.
