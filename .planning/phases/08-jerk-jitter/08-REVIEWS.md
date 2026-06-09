---
phase: 8
reviewers: [codex]
reviewed_at: 2026-06-09T03:35:00Z
plans_reviewed:
  - .planning/phases/08-jerk-jitter/08-00-PLAN.md
  - .planning/phases/08-jerk-jitter/08-01-PLAN.md
  - .planning/phases/08-jerk-jitter/08-02-PLAN.md
  - .planning/phases/08-jerk-jitter/08-03-PLAN.md
prior_review_referenced: .planning/phases/08-jerk-jitter/08-DIRECT-REVIEW.md
cycles_recorded: [1, 2]
latest_cycle: 2
latest_verdict: revise-before-execute
latest_unresolved_high: 4
---

# Cross-AI Plan Review — Phase 8

This review is the cycle-1 convergence-loop pass. A prior manual review
(`08-DIRECT-REVIEW.md`, status `high-risk-revise-before-execution`) is referenced
but not echoed. Codex was asked to produce an independent assessment and call out
items the prior review missed.

## Codex Review

**Plan 08-01**

**Summary:** Good intent for contract lockstep and drift-defense, but it is not safe as the foundation plan because its Wave-0 fixtures and schema assume pole-position and model fields that do not exist. This plan would likely encode a false coordinate contract before the real measurement contract is settled.

**Strengths**

- Atomic TS/Python/docs contract update is the right pattern.
- Extracting `dimensions.stability_wobble()` is a useful drift-defense step.
- `contact_points.yaml` is the right place for motion-specific contact expectations, if treated as domain config rather than truth labels.

**Concerns**

- HIGH, 08-01 Task 1: fixtures invent `pole_axis.base_point`, but current `PoleAxis` has only `axis_vector`, `confidence_level`, `source`, `frame_index` (`backend/shared/python/sunity_shared/analysis/pose_frame.py:166`).
- HIGH, 08-01 Task 1: fixture factory spec appears incompatible with current dataclasses: `PoseFrame(frame_idx=...)` vs `frame_index`, `Keypoint3DAligned(..., visibility=...)` although it only has `x/y/z`, and `BodyNormalizationProfile.asymmetry` though no such field exists.
- HIGH, 08-01 Task 1/2: synthetic fixtures bake in pole origin, torso scale, contact semantics, phase timings, and jerk thresholds before those contracts are valid.
- MEDIUM, 08-01 Task 3: grep-based lockstep tests can pass from comments/placeholders and do not prove type shape, dataclass constructor compatibility, or camelCase serialization.

**Suggestions**

- Insert `08-00 Coordinate/Scale Contract` before this plan.
- Replace most JSON fixtures with programmatic factories until pole distance and contact semantics are fixed.
- Make lockstep tests parse actual TS/Python structures where possible, not comments.

**Risk Assessment:** HIGH — schema and fixtures are likely to codify physically invalid assumptions.

---

**Plan 08-02**

**Summary:** The module boundary is good, but the core computations are not physically or numerically safe as written. Axis and contact metrics depend on a pole line position that does not exist, and stability/jerk thresholds are frame-rate and smoothing dependent.

**Strengths**

- `force_signals.py` as a separate diagnostic module is appropriate.
- Reusing `dimensions.stability_wobble()` reduces drift.
- Confidence fields and low-reliability warnings are necessary and well-aligned with project invariants.

**Concerns**

- HIGH, 08-02 Task 2: `compute_axis_deviation()` cannot compute "distance to pole axis" from direction alone. The aligner rotates only; it does not translate to a pole centerline (`backend/shared/python/sunity_shared/analysis/pole/aligner.py:29`).
- HIGH, 08-02 Task 2: `torso_scale` is a torso-relative ratio, usually self-reference around 1.0, not an observed length denominator (`backend/shared/python/sunity_shared/analysis/body_normalization.py:65`).
- HIGH, 08-02 Task 2: Layer-1 phase signals mix "image-down" assumptions with `keypoints_3d_pole_aligned`; after rotation, `y` is not guaranteed to mean screen-ground direction.
- HIGH, 08-02 Task 2/3: `temporal_fill()` is already applied in `_extract_video_analysis_inputs()` (`backend/functions/pipeline/app.py:431`); calling it again in `compute_force_signals()` risks double smoothing.
- HIGH, 08-02 Task 2: jerk is `deg/frame^3`, so the same motion changes value if target FPS changes. At 9 fps, short phase windows also make third differences unstable.
- MEDIUM, 08-02 Task 2: contact uses COCO-17 proxies for hands/feet/thighs despite RTMW 133 and pole extension landmarks being available.

**Suggestions**

- Add `PoleLine2D` or `PoleAxisMeasurement(point_on_axis, coordinate_space)` first.
- Use observed torso length, e.g. median shoulder-hip distance in the same coordinate space, not `BodyNormalizationProfile.torso_scale`.
- Treat v1 contact as `nearPoleRatio`, `distanceToPoleNorm`, `lostNearPoleAtMs`, `measurementKind`, and `confidence`; keep `estimatedStable` nullable unless evidence is strong.
- Normalize derivatives by `dt = 1 / fps`; add 9 fps vs 18 fps equivalence tests.

**Risk Assessment:** HIGH — implementation would produce plausible-looking but ungrounded signals.

---

**Plan 08-03**

**Summary:** Production wiring has useful coverage goals, but the Gemini and pipeline integration are riskier than the plan states. It duplicates an existing Gemini moment path, uses the same env switch as recognizer activation, and references pipeline fields that are not currently returned.

**Strengths**

- Gemini failure fallback to Layer 1 is directionally correct.
- Firestore validation tests are planned.
- Pipeline ON/OFF tests and mode coverage are the right integration test targets.

**Concerns**

- HIGH, 08-03 Task 2: plan calls `inputs.pole_axis`, but `_VideoAnalysisInputs` currently returns only `angles`, `student_profile`, `pose_frames`, `local_video_path` (`backend/functions/pipeline/app.py:375`).
- HIGH, 08-03 Task 2: current pipeline passes a vertical fallback `default_pole` into pose estimation, not a detected pole line (`backend/functions/pipeline/app.py:697`).
- HIGH, 08-03 Task 1/2: `GeminiTechniqueRecognizer` already wraps `GeminiMomentExtractor` and returns/caches moments (`backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py:145`); a new singleton can cause duplicate upload, latency, cost, and inconsistent boundary sources.
- HIGH, 08-03 Task 2: "default off via `RECOGNIZER_BACKEND` unset" is weak. Production likely sets Gemini for Phase 5, which would also activate Phase 8 Layer 2. Use a separate `FORCE_SIGNALS_LAYER2_ENABLED`.
- MEDIUM, 08-03 Task 2: proposed `_should_keep_local_video()` checks only `RECOGNIZER_BACKEND == "gemini"`, while existing `_gemini_enabled()` also supports `GEMINI_RECOGNIZER_ENABLED` and truthy aliases.
- MEDIUM, 08-03 Task 1: `_map_moments_to_5phase` assumes `hold` timestamp means hold start and `setup` means lock start. That is not guaranteed by the existing prompt.
- MEDIUM, 08-03 Task 1: the hardcoded local model name is stale-risky. Official Google docs currently list `gemini-3-pro-preview`; this should be env/config-driven and validated with `models.list`.

**Suggestions**

- Reuse recognizer-extracted moments: expose them on `TechniqueProfile`, return a richer recognition result, or read from `TechniqueCache`.
- Add a separate Layer-2 flag and make Phase 8 Gemini default-off independently of Phase 5 recognizer.
- Add monotonic boundary validation and explicit missing-moment behavior.
- Make model name config-driven; fail closed or fallback when unavailable.

**Risk Assessment:** HIGH — integration can silently double-call Gemini and still consume invalid coordinate metrics.

---

**Phase Overall**

**Summary:** The phase goal is correct: Phase 9 needs phase boundaries, axis deviation, stability, and contact evidence. The current plans are not safe to execute as written because two upstream contracts are missing: pole position and observed distance scale. Without those, `AxisDeviationMetric` and `ContactStabilityMetric` are not merely noisy; they are physically undefined.

**Strengths**

- Good decomposition into schema, core computation, and production wiring.
- Correct instinct to keep Phase 8 as diagnostic signals, not final force-pattern claims.
- Confidence propagation and warning codes are necessary for downstream Phase 9/10/11.
- Single-camera-first is respected; no SMPL-X recommendation is introduced.

**Concerns**

- HIGH: R1 is a hard blocker for axis/contact metrics. It can only be deferred if those fields become `null`/unavailable or are explicitly changed to image-plane measurements.
- HIGH: thresholds are not defensible yet. The ban on human-score labels does not forbid using 정은지 numeric distributions as sanity checks, but it does forbid treating them as ground truth or tuning thresholds until "pro = low."
- HIGH: Layer-1 motion-agnostic segmentation is unrealistic as a medium-confidence default for spinning pole, inverts, climbs, partial clips, and already-airborne starts.
- HIGH: 9 fps downsampling makes derivative thresholds and min-frame debounces operational constants, not portable motion metrics.
- MEDIUM: allowing `list[str]` inside `list[dict]` is technically manageable with tests, but it weakens the project's stricter Firestore invariant. Prefer scalar per-metric warning fields unless the invariant is formally updated.
- MEDIUM: manual validation gates are placed after implementation; the most important gates should happen before consuming outputs downstream.

**Suggestions**

1. Add `08-00` before execution:
   - define pole line position and coordinate space;
   - define observed torso-length scale helper;
   - decide image-2D vs aligned-3D metric names;
   - define keypoint/segment/region contact primitives.
2. Re-scope v1:
   - axis/contact outputs are evidence with confidence, not truth;
   - jerk is diagnostic-only until FPS-normalized and sweep-tested;
   - phase boundaries can be emitted, but Layer 1 defaults to low confidence unless preflight labels pass.
3. Move validation earlier:
   - 25 manually labeled timestamps before Phase 9 consumes phase-specific signals;
   - 9 fps vs 18 fps derivative invariance test;
   - at least one real saved pose trace, not only synthetic JSON.

**Risk Assessment:** HIGH — the current plan would produce high-confidence downstream inputs from invalid geometry.

**Phase-Level Verdict:** `block`

As written, do not execute 08-01/08-02/08-03. A narrowed schema-only slice is acceptable only if it explicitly avoids claiming pole-distance/contact metrics until the pole-position and scale contracts are fixed.

**Direct Focus Answers**

- R1 hard blocker: yes, for current success criteria #1 and #3. Deferrable only by outputting unavailable/2D-proxy fields.
- Thresholds: domain/IPSF-inspired thresholds are fine as starting hypotheses; 정은지 distributions may be sanity checks, not calibration ground truth.
- Layer 1 realism: not credible as universal medium-confidence segmentation. Use low-confidence fallback until labeled validation passes.
- Frame-rate: not robust. Normalize by `dt`, avoid double smoothing, and test resampling.
- Firestore `list[str]`: not necessarily a Firestore crash, but it is a local invariant foot-gun.
- Default-off Layer 2: not credible if it shares Phase 5's recognizer env.
- Wave-0 fixtures: too assumption-heavy; delay or make them factory-based.
- Prior missed items: dataclass fixture mismatches, nonexistent `inputs.pole_axis`, current pipeline vertical fallback pole, duplicate Gemini moment path, env helper drift, fragile grep lockstep, and unvalidated Gemini-to-5-phase mapping.

Sources checked: local files cited above, plus Google's current Gemini model docs: https://ai.google.dev/models/gemini and https://ai.google.dev/gemini-api/docs/gemini-3.

---

## Consensus Summary

Only one external reviewer (Codex) was invoked in this cycle, so "consensus"
below is between Codex and the prior `08-DIRECT-REVIEW.md`. Items where both
reviewers converge are treated as high-priority.

### Agreed Strengths

- Decomposition into (a) contract lockstep, (b) pure compute module, (c)
  production wiring is correct.
- Reusing `dimensions.stability_wobble()` (drift defense) is the right pattern.
- Keeping Gemini as a soft adapter with Layer-1 fallback is directionally right.
- `force_signals.py` as a diagnostic-only module separate from `dimensions.py`
  is correct.

### Agreed Concerns (HIGH — must address before execution)

1. **Pole position is undefined.** Both reviews flag this as the central
   blocker: `PoleAxis` has direction only. `compute_axis_deviation()` and
   contact proximity cannot be physically computed. Either add a
   `PoleLine2D` / `PoleAxisMeasurement` contract first, or downgrade these
   metrics to image-plane proxies with an explicit `coordinateSpace` field.
2. **`torsoScale` is the wrong distance denominator.** Both reviews call out
   that `BodyNormalizationProfile.torsoScale` is a torso-relative proportion,
   not an absolute length. Introduce a separate `median_torso_length()` helper.
3. **Contact stability is over-specified.** `left_inner_thigh`,
   `right_inner_thigh`, and `hip` are not COCO-17 keypoints; they are segments
   or regions. Either move to RTMW-133 / segment-to-pole distance, or relax
   `estimatedStable` to nullable evidence (`distanceToPoleNorm`,
   `nearPoleRatio`, `lostNearPoleAtMs`) in v1.
4. **Layer-1 5-phase heuristic is not validated for real pole sports.**
   Universal "ground → grab → lift → shape → hold" assumptions break for
   spinning pole, inverts, climbs, partial clips, and already-airborne starts.
   Pre-flight 25-timestamp labelling gate is required before downstream
   phases consume phase-specific signals.
5. **Jerk/jitter is frame-rate-dependent + double-smoothing risk.** Pipeline
   already applies `temporal_fill()` once. Phase 8 plan calls it again.
   Thresholds in `deg/frame^3` change meaning if FPS changes. Normalize by
   `dt = 1/fps` and add 9 fps vs 18 fps invariance tests.

### Agreed Concerns (MEDIUM)

6. **Layer-2 Gemini duplicates an existing Gemini call path.** The recognizer
   already wraps `GeminiMomentExtractor`. A second singleton risks double
   uploads, double cost, and inconsistent timestamps. Reuse the recognizer's
   already-extracted moments via `TechniqueProfile` / `TechniqueCache`.
7. **Hardcoded `DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"` is stale.**
   Make model name config-driven and validate via `models.list` at startup.
8. **Firestore validator extension weakens the flat-array invariant.** Allowing
   `list[str]` inside `list[dict]` is serializable but a local foot-gun.
   Prefer per-metric scalar `warningCode` until the invariant is formally
   updated.
9. **Heavy synthetic Wave-0 fixtures encode unsettled assumptions.** Replace
   most JSON fixtures with programmatic factories; add at least one real saved
   pose trace.

### Newly Surfaced Concerns (Codex-only, not in prior direct review)

- **HIGH (08-01 Task 1)**: fixture spec uses dataclass field names that don't
  match real code — `PoseFrame(frame_idx=...)` vs actual `frame_index`,
  `Keypoint3DAligned(..., visibility=...)` although the real class only has
  `x/y/z`, and `BodyNormalizationProfile.asymmetry` though no such field
  exists. Plan would fail at fixture load time.
- **HIGH (08-03 Task 2)**: plan references `inputs.pole_axis` but
  `_VideoAnalysisInputs` does not currently expose that field (`pipeline/app.py:375`).
- **HIGH (08-03 Task 2)**: pipeline currently passes a vertical fallback
  `default_pole` into pose estimation, not a detected pole line
  (`pipeline/app.py:697`). Phase 8 assumes a detected pole line is available.
- **HIGH (08-03 Task 2)**: "default-off via `RECOGNIZER_BACKEND` unset" shares
  the same env switch as Phase 5 recognizer. If Phase 5 is on, Phase 8 Layer-2
  is on too, eliminating the safety mechanism. Introduce a separate
  `FORCE_SIGNALS_LAYER2_ENABLED` flag.
- **MEDIUM (08-03 Task 2)**: `_should_keep_local_video()` checks only
  `RECOGNIZER_BACKEND == "gemini"`, while existing `_gemini_enabled()` also
  honors `GEMINI_RECOGNIZER_ENABLED` truthy aliases. Helper drift.
- **MEDIUM (08-03 Task 1)**: `_map_moments_to_5phase()` assumes
  `setup → lock start` and `hold → hold start`, but the recognizer prompt
  does not contractually guarantee this semantics.
- **MEDIUM (08-01 Task 3)**: lockstep tests are grep-based, which can pass
  on placeholder comments and prove nothing about type shape, dataclass
  constructor compatibility, or camelCase serialization.

### Divergent Views

- No active divergence: Codex broadly confirms the prior direct review's
  verdict and extends it with concrete file/line evidence of additional
  contract mismatches (dataclass fields, `inputs.pole_axis`, vertical-fallback
  pole). Both reviews converge on `block` / `revise-before-execution`.

### Recommended Next Steps

1. Pause execution of 08-01/02/03 as currently written.
2. Author a thin `08-00 Coordinate/Scale Contract` plan:
   - add `PoleLine2D` or `PoleAxisMeasurement(point_on_axis, coordinate_space)`;
   - add `median_torso_length(pose_frames, *, space)` helper;
   - choose image-2D vs aligned-3D for axis/contact distance and store
     `coordinateSpace` explicitly;
   - define contact primitives (`keypoint`, `segment`, `region_proxy`).
3. Revise 08-01 schema to align with the new coordinate contract; replace
   JSON fixtures with factories; fix dataclass field-name mismatches
   (`frame_index`, no `visibility`, no `asymmetry`).
4. Revise 08-02 to use observed torso length, FPS-normalized derivatives,
   single smoothing pass, and contact as evidence-with-confidence (not boolean
   truth).
5. Revise 08-03 to (a) reuse recognizer-extracted moments, (b) introduce a
   dedicated `FORCE_SIGNALS_LAYER2_ENABLED` flag, (c) move model name to
   config/env with startup validation, (d) expose `pole_axis` on
   `_VideoAnalysisInputs` once 08-00 lands.
6. Move pre-flight validation gates (25-timestamp labels, FPS invariance,
   pole-line overlay) to BEFORE downstream Phase 9 consumes Phase 8 outputs.

To incorporate feedback into planning:

```
/gsd-plan-phase 8 --reviews
```

---

# Cross-AI Plan Review — Phase 8 (Cycle 2)

Cycle 2 of the plan-review-convergence loop. Cycle 1 verdict was `block` with
9 HIGH concerns (including 1 BLOCKER, R1). The planner replan (commit
`b606192`) inserted a NEW Wave-0 plan `08-00-PLAN.md` and revised 08-01/02/03.
This cycle audits whether each Cycle 1 HIGH is actually addressed in the plan
text — not merely claimed in the replan summary — and surfaces new HIGH risks
introduced by the revision.

- **cycle:** 2
- **reviewers:** [codex]
- **reviewed_at:** 2026-06-09T03:35:00Z
- **plans_reviewed:**
  - .planning/phases/08-jerk-jitter/08-00-PLAN.md (NEW Wave-0)
  - .planning/phases/08-jerk-jitter/08-01-PLAN.md (revised)
  - .planning/phases/08-jerk-jitter/08-02-PLAN.md (revised)
  - .planning/phases/08-jerk-jitter/08-03-PLAN.md (revised)
- **prior_review_referenced:** 08-REVIEWS.md cycle 1 (this file, above)

## Codex Review (Cycle 2)

### 1. Cycle 1 HIGH Resolution Audit

| ID | Status | Justification |
|---|---|---|
| R1 | FULLY RESOLVED | 08-00 defines `PoleLine2D` / `PoleAxisMeasurement` and `point_to_pole_line_distance_2d()` with `line=None → coordinate_space='unavailable'`; 08-02 uses nullable axis distances instead of direction-only `PoleAxis` (08-00 lines 32–33, 265–282; 08-02 lines 438–457). |
| R2 | FULLY RESOLVED | 08-00 adds `median_torso_length()` and bans `BodyNormalizationProfile`; 08-02 imports/uses it with drift-defense tests (08-00 lines 283–294, 347; 08-02 lines 438–439, 571–576). |
| R3 | FULLY RESOLVED | Contact primitive kinds, YAML `kind`, nullable `estimatedStable`, `nearPoleRatio`, and segment/region-proxy handling are specified and tested (08-00 line 35; 08-01 lines 317–363; 08-02 lines 498–531). |
| R4 | PARTIALLY RESOLVED | Spec/CSV and function parameter exist, but production wiring hardcodes `preflight_label_gate_passed=None`; a PASS cannot be applied without code/config changes (08-00 lines 466–488; 08-03 lines 427–435, 583–588). |
| R5 | FULLY RESOLVED | Jerk is `deg/sec^3` via `dt=1/fps`, `temporal_fill()` is banned inside `compute_force_signals()`, and tests cover call count and FPS invariance (08-02 lines 474–489, 608–624, 640–646). |
| R6 | FULLY RESOLVED | Layer 2 uses `TechniqueProfile.key_moments`; `gemini_extractor` arg removed and duplicate-Gemini-call test specified. `_gemini_enabled()` is reused for local-video retention (08-03 lines 272–295, 342–348, 427–440). |
| R7 | FULLY RESOLVED | Separate `FORCE_SIGNALS_LAYER2_ENABLED` flag plus four env-combination pipeline tests are specified (08-03 lines 30, 462–470, 508–511). |
| R8 | NOT RESOLVED | The revised default `gemini-2.0-flash-exp` is stale; per Google's current docs Gemini 2.0 Flash is scheduled to be shut down (2026-06-01) and the current stable Flash family is `gemini-3.5-flash`. Also the real model default lives in `judging/gemini_moment_extractor.py`, not just `gemini_technique_recognizer.py` — only one of the two call paths is being made env-driven. |
| R10 | FULLY RESOLVED | `_VideoAnalysisInputs` is extended with `pole_axis_measurement`, built from vertical fallback with `line=None`, exposing `coordinate_space='unavailable'` instead of pretending detection exists (08-03 lines 384–390, 494–505). |
| H1 | FULLY RESOLVED | Factories use `frame_index`, omit `visibility` for `Keypoint3DAligned`, and omit `asymmetry`; grep acceptance criteria enforce these (08-00 lines 301–318, 348–351). |

### 2. New HIGH Concerns (introduced by the Cycle 2 revision)

1. **Preflight gate cannot pass in production.** `pipeline/app.py::_process` is
   planned to hardcode `preflight_label_gate_passed=None` (08-03 lines 427–
   435). The manual checkpoint instructs belle to set the gate to `True` via
   "Lambda env or force_signals call," but no env-driven plumbing path is
   defined in any of the four plans. Result: even after a successful 25-
   timestamp PASS, Layer-1 confidence cannot reach `medium` without a code
   change. This is the residual R4 blocker.
2. **Layer-2 failure upgrades unvalidated Layer-1 confidence to `medium`.**
   The Layer-2 try/except branch (08-03 lines 288–295) does
   `_promote_layer1(..., "medium", "heuristic", ["layer2_call_failed"], ...)`,
   bypassing `_layer1_confidence_from_preflight()`. A failed Gemini-assisted
   path must not promote Layer-1 above whatever the preflight gate allows.
   This contradicts the Cycle 1 R4 fix in the same plan.
3. **Firestore flat-array invariant is weakened.** `ForceSignalsReport` carries
   metric arrays of dicts with `warnings: list[str]` and
   `unstableBodyParts: list[str]` (08-01 lines 436–439). 08-03 expands
   `_validate_dict_only_scalars` to permit scalar lists inside `list[dict]`
   (08-03 lines 297–299). Cycle 1 flagged this as MEDIUM; in Cycle 2 it is
   relaxed into the validator itself — which is a project-wide invariant
   change, not a Phase-8-scoped one. Either (a) formally re-state the
   invariant, or (b) keep warning lists as separate top-level fields.

### 3. MEDIUM / LOW Concerns

- `preflight_gate_pending` warning is emitted by 08-02 but is not present in
  the 19-code warning enum in 08-01 §9.8.
- `TechniqueCache` cache-hit reconstruction currently does not round-trip
  `moments`; on a cache hit `TechniqueProfile.key_moments` will be `None`,
  silently disabling Layer 2. Plan needs a deserialization step.
- 08-03 references `from .features import assign_frame_indices`, but the
  helper currently lives in `sunity_shared.judging`. Import path drift.
- Monotonic boundary validation only catches frame-order violations; it does
  not resolve the Cycle 1 semantic ambiguity that `setup → lock start` and
  `hold → hold start` are not contractually guaranteed by the recognizer
  prompt.
- The 9 fps / 18 fps jerk invariance test uses linear interpolation to
  upsample, which by construction flattens third-difference noise. This may
  hide rather than prove FPS robustness; a real captured 18 fps trace would
  be a stronger test.

### 4. Per-Plan Risk Assessment

- **08-00:** MEDIUM — coordinate/scale contract is sound; the preflight gate
  is document-only until 08-03 plumbs it.
- **08-01:** HIGH — schema introduces nested scalar lists inside metric
  arrays (Firestore invariant exposure).
- **08-02:** MEDIUM — core R1/R2/R3/R5 fixes are well specified; warning-enum
  completeness and FPS-invariance test realism are open.
- **08-03:** HIGH — stale Gemini model default, preflight plumbing gap,
  Layer-2-failure confidence promotion, and Firestore invariant change all
  land here.

### 5. Phase-Level Verdict

`revise-before-execute`

The geometry/scale blockers (R1/R2/R3/R5/R10/H1) are substantively closed,
and Layer-2 reuse (R6) and env separation (R7) land cleanly. Execution should
wait for: (a) env/config plumbing for `preflight_label_gate_passed` so the
gate is actually reachable from belle's manual checkpoint; (b) Layer-2
failure path that does not promote Layer-1 confidence; (c) a decision on
whether to relax the Firestore flat-array invariant project-wide or keep
warnings as flat siblings; (d) a current Gemini Flash model default applied
in both `gemini_technique_recognizer.py` AND
`judging/gemini_moment_extractor.py`.

### 6. CYCLE_SUMMARY

CYCLE_SUMMARY: current_high=4

## Consensus Summary (Cycle 2)

Only Codex was invoked this cycle. Compared with Cycle 1:

- **Closed:** R1, R2, R3, R5, R6, R7, R10, H1 (8 of 9 prior HIGHs FULLY
  RESOLVED).
- **Still open (Cycle 1 carryover):** R4 (partial — plumbing gap), R8 (model
  default).
- **Newly raised (Cycle 2):** Layer-2 failure confidence promotion, Firestore
  flat-array invariant relaxation.

Net unresolved HIGH = 4 (R4 partial + R8 not-resolved + 2 new).

### Recommended Next Steps Before Execution

1. Add env-driven plumbing for `preflight_label_gate_passed` in
   `pipeline/app.py::_process` (e.g. `os.environ.get("PREFLIGHT_LABEL_GATE_PASSED", "")` → bool) so the gate becomes reachable without code edits.
2. In `force_signals.compute_phase_boundaries`, route the Layer-2 except
   branch through `_layer1_confidence_from_preflight()` so failure cannot
   exceed the preflight-gated ceiling.
3. Make `GEMINI_MODEL` env-driven in BOTH
   `gemini_technique_recognizer.py` AND
   `judging/gemini_moment_extractor.py`, and pick a model that is not
   end-of-life as of 2026-06-09 (verify against Google's deprecation page).
4. Either (a) make ForceSignalsReport metrics carry no list fields (move
   `warnings` and `unstableBodyParts` to top-level keyed maps), or (b)
   explicitly update the project Firestore invariant ADR before relaxing
   `_validate_dict_only_scalars`.
5. Add `preflight_gate_pending` to the §9.8 warning enum and document the
   `TechniqueCache` round-trip for `key_moments`.

To incorporate feedback into planning:

```
/gsd-plan-phase 8 --reviews
```

