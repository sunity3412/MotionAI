# Phase 19 Plan Direct Review

**Reviewer:** Codex direct review (no external review skill)
**Reviewed:** 2026-06-18
**Scope:** `19-01-PLAN.md` through `19-04-PLAN.md`, `19-D05-VISION-GROUNDING-SPIKE.md`, validation docs, and the referenced implementation files.

## Verdict

**Needs revision before execution.**

The phase direction is correct: the real bug is score aggregation and trust framing, not DTW itself. The plan also correctly separates v1 deterministic fixes from v2 vision veto. However, several plan details will either fail against the current code or produce a result that is not actually visible to the user. I would revise the plan before implementation, then execute in the same wave order.

## Findings

### BLOCKER-1 — Mode3 "unknown move" cannot be detected from `copyBranch` alone

**Risk:** Plan 04 says to branch on `MotionBranchInfo.copyBranch` and treat `_SAFE_DEFAULT_BRANCH` as the missing-reference case. In the current code, `_SAFE_DEFAULT_BRANCH.copyBranch` is also `"branch2_eunji_reference"` (`assemble.py:68-77`), the same value used by real branch2 reference motions. A copyBranch-only implementation cannot distinguish "known Eunji reference" from "unknown / reference-free". The TRUST-03 gate could silently keep using reference-style copy for truly unknown motions.

**What I would do:** Keep `copyBranch` backward compatible and add an explicit helper instead of overloading it:

```python
def is_reference_free_motion(info: MotionBranchInfo | None) -> bool:
    return (
        info is None
        or (
            info.angleSource == "unavailable"
            and info.angleFixtureKey is None
            and info.ipsfCode is None
            and not info.officialName
        )
    )
```

Then pass `branch_info` into `_mode3_comparison(...)` and test all three cases: branch1, real branch2, and fallback reference-free. Do not change the existing Phase 13 expectation that unknown IDs default to branch2 copy unless the broader routing contract is deliberately updated.

### BLOCKER-2 — TRUST-03 says "show the basis on screen", but Plan 04 is backend-only

**Risk:** `files_modified` for Plan 04 only includes `pipeline/app.py` and `assemble.py`. The current result screen does not read a new Mode3 basis field. `DimensionDetailModal` also ignores backend `explanation.baseline` and recomputes baseline text locally (`DimensionDetailModal.tsx:87-132`). If Plan 04 only adds a backend optional key, the user may still not see "기준 동작 없음 — 절대 자세 기준 평가".

**What I would do:** Add a small 3-way optional contract and render it:

- Backend `build_mode3(..., scoring_basis="reference_free_absolute")` emits:
  - `scoringBasis: "reference_free_absolute" | "previous_analysis" | "reference_motion"`
  - `scoringBasisLabel: "기준 동작 없음 — 절대 자세 기준 평가"`
- Update `app/src/types/analysis.ts`, `docs/contract.md`, and `app/src/app/analysis/result.tsx`.
- Render the basis under the result header for Mode3 and use it in `DimensionDetailModal` instead of hardcoded "세계 심사 기준" copy when reference-free.

This makes TRUST-03 observable instead of just stored.

### BLOCKER-3 — Existing tests contradict the new scoring semantics

**Risk:** Plan 02 says "기존 test_dimensions.py 케이스 회귀 0", but `test_overall_from_dimensions_is_mean` currently asserts mean behavior. Plan 02 intentionally replaces mean with core-min / stability-excluded aggregation. Similarly, `test_score_monotonic_decreasing_with_deviation` uses 15° for all joints; with a tolerance dead zone, that can remain 100 and fail the old strict monotonic assertion.

**What I would do:** Make Wave 0 update old tests as part of the RED contract:

- Rename `test_overall_from_dimensions_is_mean` to `test_overall_from_dimensions_uses_core_dimensions`.
- Assert `{"angle": 40, "line": 80, "stability": 99} -> 40`.
- Assert `{"stability": 99} -> 99` only as the no-core fallback.
- Change kismam monotonic test to use values beyond tolerance, e.g. `0°`, `30°`, `60°`, and add a separate "within tolerance remains high" test.

Then Plan 02 can honestly require "unrelated existing cases regression 0" rather than "all old expectations still pass."

### HIGH-1 — `DimensionExplanation.weightPercent` becomes misleading after stability is excluded

**Risk:** `build_dimension_explanation` currently assigns equal `weightPercent` across displayed dimensions (`assemble.py:230-265`), and the contract defines it as overall contribution. Plan 02 excludes `stability` from `overall_from_dimensions`, so a 3-way `[34,33,33]` contribution display is false even if not always prominent in the UI.

**What I would do:** Make contribution explicit:

- Either set `weightPercent` over contributing dimensions only and set stability to `0`, or add `contributesToOverall: boolean`.
- Update `DimensionExplanation` in TS and contract.
- Keep `stability` displayed, but label it as diagnostic / auxiliary when it does not contribute to overall.

### HIGH-2 — Plan 04 needs a path-based angle median helper, not "reuse per_joint_deviation" directly

**Risk:** `per_joint_deviation(...)` returns median absolute differences only. It does not return current/target angle medians for `JointAssessment.current_angle` and `target_angle`. If implementation follows the prose loosely, it can fix the score source but still leave displayed angles inconsistent.

**What I would do:** Add a dedicated helper in `pipeline/app.py`:

```python
def _angles_to_dtw_median_dicts(path, user_seg, ref_angles, joint_keys):
    # returns (user_median_by_joint, ref_median_by_joint)
```

It should collect path-aligned `(user_frame, ref_frame)` values per joint and compute finite medians for both sides. Use it in Mode1 and Mode3-progress. For Mode3-first, use the same hold-window source as `extension_deviation` rather than whole-clip mean.

### HIGH-3 — Plan 03 references the wrong key set for 3D normalization

**Risk:** Plan 03 says to lookup hips/shoulders via `JointKeys`, but `joints3dKeys` are COCO-17 keypoint names from `skeleton.KEYPOINT_NAMES`, not the 8 angle `JOINT_KEYS`. Using the wrong index source will normalize around the wrong points or fail.

**What I would do:** In `reshapePose3dData(flat, jointKeys, frames)`, derive indices from the `jointKeys` argument:

```ts
const leftHip = jointKeys.indexOf('left_hip');
const rightHip = jointKeys.indexOf('right_hip');
const leftShoulder = jointKeys.indexOf('left_shoulder');
const rightShoulder = jointKeys.indexOf('right_shoulder');
```

Also validate every coordinate is finite before rendering.

### HIGH-4 — 3D fallback should not leave raw pixel coordinates in place

**Risk:** Plan 03 says hip/shoulder missing can skip normalization. If it skips, the same raw pixel-scale frame can remain outside the camera frustum, so the blank viewer persists for occluded frames.

**What I would do:** Use fallback normalization, not raw passthrough:

1. Primary: hip midpoint center + torso length scale.
2. Fallback: finite-joint centroid center + max axis range / bounding-box scale.
3. Last resort: return `null` for that frame or sequence, rather than returning unnormalized raw pixels.

Acceptance should assert normalized coordinates stay within a bounded range, e.g. `maxAbsCoord <= 3`, for a synthetic raw COCO-17 frame centered near `(320, 240)`.

### HIGH-5 — Plan 01's RED verification is too weak

**Risk:** Plan 01 mostly verifies with `pytest --co`, which only proves import/collection. A test can be collected and still assert the wrong behavior. Since later plans depend on these RED tests, weak RED verification can let implementation drift.

**What I would do:** For Wave 0, run the selected tests normally and record expected failures by name in `19-01-SUMMARY.md`. If keeping automation green is required, use collection plus an explicit source assertion checklist: each new test must fail against the current mean/stability behavior when run alone, except GPU anchor tests which must skip.

### MEDIUM-1 — `penalty_per_deg=2.0` is an unreviewed product decision

**Risk:** The plan labels the penalty coefficient as IPSF-derived, but the exact degree-to-0..100 mapping is still an assumption. Too high creates false negatives on acceptable videos; too low preserves the Phase 15 false positive.

**What I would do:** Name this as an explicit v1 heuristic, not an IPSF fact. Put the constants in code with `[ASSUMED]` comments and boundary tests:

- within tolerance stays high;
- one major fault dominates;
- multiple moderate faults accumulate;
- above-cutoff synthetic remains high.

Do not tune the coefficient from the six D-05 videos. Use those only for direction checks.

### MEDIUM-2 — Plan 04 should move `branch_info` lookup earlier

**Risk:** Current pipeline computes `branch_info` after Mode1/Mode3 scoring (`app.py:1945-1947`). TRUST-03 needs branch info during Mode3 scoring and comparison construction.

**What I would do:** Compute `branch_info = assemble.lookup_motion_branch(getattr(profile, "motion_id", None))` immediately after `profile = recognizer.recognize(...)`, then pass it to `_mode3_comparison(...)`, `_build_coach_context(...)`, and `build_result(...)`. This avoids duplicate lookup and keeps coach/result/scoring basis aligned.

### MEDIUM-3 — D-05 anchor test should have a real enable path

**Risk:** A permanently skipped `test_anchor_known_answer.py` gives a false sense of coverage. The plan says Pod/GPU can activate it later, but it does not define the activation contract.

**What I would do:** Use an explicit env gate:

```python
RUN_PHASE19_ANCHORS=1 pytest tests/test_anchor_known_answer.py -q
```

Skip unless the env var and required S3/GPU configuration are present. In the skipped test body, keep the real fixture list and expected dominant dimension metadata so activation is mechanical.

## Suggested Plan Changes

1. Revise Plan 01 to update conflicting old tests and prove RED behavior, not only collection.
2. Revise Plan 02 to update `build_dimension_explanation`, comments, and contract semantics for non-contributing stability.
3. Revise Plan 03 to use `joints3dKeys` / COCO-17 indices and add a numeric normalization smoke check.
4. Revise Plan 04 to add explicit reference-free basis detection, move `branch_info` lookup before scoring, and include frontend files for visible scoring basis.
5. Keep v2 vision veto as pass-through only in this phase; do not add Gemini scoring behavior until Phase 18 / anchor validation gives enough evidence.

## Execution Order After Revision

I would still keep the current wave shape:

1. Wave 0: tests and contract expectations.
2. Wave 1A: scoring core.
3. Wave 1B: 3D normalization.
4. Wave 2: pipeline basis/display/hook wiring.

The difference is that Wave 0 must lock the semantics above before code changes begin.
