# Phase 19 Plan Direct Review — Iteration 2

**Reviewer:** Codex direct review (no external review skill)
**Reviewed:** 2026-06-18
**Scope:** Revised `19-01-PLAN.md` through `19-04-PLAN.md`, `19-VALIDATION.md`, and the current code they reference.

## Verdict

**Needs one more revision before execution.**

The first-review blockers are mostly addressed: RED is no longer collection-only, `copyBranch` is no longer the only proposed reference-free signal, `scoringBasis` is planned through the UI, the DTW display helper is now explicit, and 3D normalization now uses `joints3dKeys`. The remaining issues are narrower but still important because they can break typecheck, produce misleading Mode3 basis labels, or make the new smoke tests pass without testing production code.

## Findings

### BLOCKER-1 — `contributesToOverall` as required will break app typecheck unless simulated data and old-doc compatibility are handled

**Risk:** Plan 02 adds `DimensionExplanation.contributesToOverall` as a required TS field but `app/src/lib/simulatedResult.ts` currently constructs `DimensionExplanation` objects with only `weightPercent`, `baseline`, and `deficitSummary`. Plan 02 does not list `simulatedResult.ts` in `files_modified`, yet it requires `cd app && npm run typecheck`.

It also says the field is "required" while previous Firestore docs obviously do not have it. Runtime is tolerant because the UI reads optional data, but the type should model historical docs unless a normalizer backfills it.

**What I would do:** Make the field optional in TS and treat missing as legacy:

```ts
contributesToOverall?: boolean;
```

For new backend docs, always emit it. In UI code, default missing to `true` for legacy docs because old overall did include stability. Also update `app/src/lib/simulatedResult.ts` in Plan 02 or Plan 04 so simulated docs reflect new semantics. If the team wants the field required, add a normalization step in `userAnalyses.ts` that fills it for every existing explanation entry before casting to `AnalysisResult`.

### BLOCKER-2 — Plan 03 smoke script duplicates the algorithm instead of exercising `reshapePose3dData`

**Risk:** Plan 03 says `_smoke_joints_normalize.mjs` may reproduce the same coordinate math because it cannot import TS directly. That can pass while `app/src/lib/joints.ts` is wrong. It verifies an independent copy, not production behavior.

**What I would do:** Use one source of truth. Best option: move the pure normalization math into a tiny JS-compatible module that both `joints.ts` and the smoke script call, or add a Node script that compiles/imports the actual TS function before running assertions. If that is too much for this phase, remove the smoke script as an automated proof and make the acceptance criterion explicit: typecheck + code inspection + device verification. Do not claim `node scripts/_smoke_joints_normalize.mjs` proves `reshapePose3dData` unless it calls the production function.

### HIGH-1 — Module-level anchor skip contradicts the always-on synthetic above-cutoff case

**Risk:** Plan 01 says `pytestmark = pytest.mark.skipif(not RUN_ANCHORS, ...)` at module level, then later says the synthetic above-cutoff case is env-gate independent and should always run. Module-level `pytestmark` will skip every test in the file, including the synthetic case.

**What I would do:** Apply the skip marker only to real-video/GPU tests:

```python
requires_anchor_env = pytest.mark.skipif(
    os.environ.get("RUN_PHASE19_ANCHORS") != "1",
    reason="RUN_PHASE19_ANCHORS=1 + S3/GPU 필요",
)

@requires_anchor_env
@pytest.mark.parametrize(...)
def test_anchor_fault_lower_than_correct(...):
    ...

def test_above_cutoff_synthetic_stays_high():
    ...
```

### HIGH-2 — `scoringBasis="reference_motion"` is misleading for Mode3 first analysis

**Risk:** Current `_mode3_comparison` first-analysis path does not compare against a reference motion. It uses absolute dimensions and extension targets from the recognized profile. The revised Plan 04 says branch1 / real branch2 can emit `scoringBasis="reference_motion"` in Mode3, but that can be false for first analysis. This recreates the trust problem the phase is trying to remove.

**What I would do:** Split the labels by actual scoring source, not motion catalog branch:

- Mode3 first + reference-free: `reference_free_absolute`
- Mode3 first + recognized profile: `recognized_motion_absolute`
- Mode3 progress: `previous_analysis_plus_absolute`

If the enum must stay small, use `scoringBasisLabel` as the exact user-facing truth and avoid `reference_motion` for Mode3 unless reference angles actually entered the score.

### HIGH-3 — Reference-free plus previous-analysis needs a composite basis

**Risk:** For Mode3 progress on an unknown motion, the score can include previous-analysis angle consistency plus reference-free absolute line/stability. A single `reference_free_absolute` or `previous_analysis` basis loses half the truth.

**What I would do:** Either add a composite enum (`previous_analysis_plus_reference_free_absolute`) or make `scoringBasis` a list of basis components. The UI can still show one concise label, but the backend contract should not force a lossy basis.

### HIGH-4 — Plan 03 frame-level `null` does not fit the current `reshapePose3dData` return type or viewer assumptions

**Risk:** `reshapePose3dData` returns `number[][][] | null`; `PoseViewer3D` expects every frame to be `number[][]`. Plan 03 says last-resort invalid frames become `null` or are skipped. Returning per-frame null violates the type. Skipping frames can also desynchronize `currentFrame`, `ipsfViolationFrames`, and video/keypoint timelines.

**What I would do:** Keep frame count stable. For last-resort frames, either reuse the previous valid normalized frame, emit a finite all-zero skeleton frame, or return `null` for the entire sequence if the sequence cannot be normalized safely. Do not silently drop individual frames unless every consumer is updated to understand reindexed frames.

### MEDIUM-1 — `weightPercent=0` for stability needs UI copy, not only contract data

**Risk:** Plan 02 adds `contributesToOverall` and `weightPercent=0`, but the visible score row currently shows score, subtitle, track, and deficit summary. If the modal or row never explains "diagnostic only", users may still assume stability affects overall because it is displayed next to core dimensions.

**What I would do:** In Plan 04, when `contributesToOverall === false`, show a quiet note in `DimensionDetailModal`, e.g. "종합점수에는 직접 합산하지 않는 보조 지표입니다." Keep the main row clean, but make the detail view honest.

### MEDIUM-2 — Plan 04 still needs test coverage for `build_mode3` backward compatibility

**Risk:** `assemble.build_mode3` has existing tests expecting exact dict equality for first analysis. Adding optional `scoringBasis` only when provided preserves those, but this should be explicit. If implementation emits default basis unconditionally, existing tests will fail.

**What I would do:** Add or update tests:

- Existing `build_mode3(is_first=True)` remains exactly `{"mode": "mode3", "isFirst": True}` when no basis is provided.
- New basis tests assert `scoringBasis` and `scoringBasisLabel` only appear when passed.

### MEDIUM-3 — `_apply_vision_veto` identity should be tested by object equality and mutation safety

**Risk:** The plan says identity, but it is ambiguous whether that means same object instance or equal values. If it deep-copies today, later code may assume mutation isolation; if it returns the same object, later code may mutate shared state.

**What I would do:** Decide and test explicitly. For v1 pass-through, I would require same object identity while OFF:

```python
out = app._apply_vision_veto(score_result, ...)
assert out is score_result
```

When v2 starts mutating, switch the contract deliberately.

## Suggested Plan Changes

1. Add `app/src/lib/simulatedResult.ts` to Plan 02 or make `contributesToOverall` optional with legacy defaulting.
2. Revise Plan 03 smoke so it calls production normalization code, or downgrade the smoke claim to "algorithm specimen" and rely on device verification.
3. Mark only real-video anchor tests with `RUN_PHASE19_ANCHORS`; keep the synthetic above-cutoff test always-on.
4. Replace Mode3 `reference_motion` basis with actual scoring-source labels, especially for first analysis and progress cases.
5. Keep `reshapePose3dData` frame count stable or return whole-sequence null; do not return/drop per-frame null without changing the viewer contract.

## Residual Risk After These Fixes

After the above, the plan is execution-ready for v1. The remaining real risk is product calibration: `penalty_per_deg` is still a v1 heuristic. The revised plan correctly labels it `[ASSUMED]`; the key is to keep D-05 as direction validation only and not tune the constants to the six known videos.
