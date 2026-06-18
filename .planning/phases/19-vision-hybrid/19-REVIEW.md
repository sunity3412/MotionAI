---
phase: 19-vision-hybrid
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - app/scripts/_smoke_joints_normalize.mjs
  - app/src/app/analysis/result.tsx
  - app/src/components/DimensionDetailModal.tsx
  - app/src/lib/joints.ts
  - app/src/lib/normalizePose3d.ts
  - app/src/lib/simulatedResult.ts
  - app/src/types/analysis.ts
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - backend/shared/python/sunity_shared/analysis/dimensions.py
  - backend/shared/python/sunity_shared/analysis/kismam.py
  - backend/shared/python/sunity_shared/models.py
  - backend/tests/test_anchor_known_answer.py
  - backend/tests/test_assemble.py
  - backend/tests/test_assemble_dimension_explanation.py
  - backend/tests/test_dimensions.py
  - backend/tests/test_kismam.py
  - backend/tests/test_pipeline_mode3.py
  - docs/contract.md
findings:
  critical: 1
  warning: 7
  info: 4
  total: 12
status: issues_found
---

# Phase 19: Code Review Report

**Reviewed:** 2026-06-18
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Phase 19 replaces mean-based aggregation with an IPSF deduction model (`kismam.overall_score`) and a `min-of-core` overall (`dimensions.overall_from_dimensions`), adds a Mode3 unknown-move gate (`scoringBasis` 4-value enum + `is_reference_free_motion`), a v1 vision-veto pass-through hook (`_apply_vision_veto`), and a 3D-skeleton normalization path (`normalizePose3d.normalizeFrames` consumed by `joints.ts`).

The scoring redesign itself is disciplined about overfit: thresholds (`_SPLIT_FAIL_THRESHOLD_DEG=160`, `_IPSF_TOLERANCE_DEG=20`) are IPSF-cited, the penalty coefficient (`_PENALTY_PER_DEG=1.2`) is flagged `[ASSUMED]`, and the anchor test deliberately avoids hardcoding score targets. Numeric edge handling in `normalizePose3d` and the dimensions helpers is thorough (epsilon guards, finite checks, frame-count preservation).

The principal defect is a **3-way contract drift**: the canonical `overallScore` description in all three contract surfaces still says "평균" (average) while the implementation is now `min-of-core`. There is also a latent key-name mismatch between the `_apply_vision_veto` production caller and its test that will silently break v2. Remaining items are robustness/consistency warnings and documentation cleanups.

## Critical Issues

### CR-01: `overallScore` contract description still says "평균" (average) across all 3 surfaces — implementation is `min-of-core`

**File:** `docs/contract.md:161`, `app/src/types/analysis.ts:339`, `backend/shared/python/sunity_shared/analysis/assemble.py:681-682`

**Issue:** Phase 19 D-01 replaced the averaging formula with `overall_from_dimensions = min-of-core(angle/line)` (see `dimensions.py:378-394`, `kismam.overall_score` deduction model). The `DimensionExplanation`/`contributesToOverall` portion of the contract was updated to describe `min-of-core` (contract.md:194), but the **canonical `overallScore` line was not**:

- `docs/contract.md:161` — `overallScore ... 0~100 종합 (mode1=3차원 평균, mode3=절대 차원 평균)`
- `app/src/types/analysis.ts:339` — `overallScore: number; // 0~100. mode1=3차원 평균, mode3=절대 차원 평균`
- `assemble.py:681-682` docstring — `overall_score 는 파이프라인이 모드별로 계산 (mode1 = 3차원 평균, mode3 = 절대 차원 평균)`
- `pipeline/app.py:1999` inline comment — `overall = dimensions.overall_from_dimensions(dimension_scores)  # 4차원 평균`

This is a direct violation of the project's contract-first invariant (CLAUDE.md Cross-cutting: "Change all three together"). The headline field semantics are now wrong in the single source of truth that the app and any downstream consumer rely on. A reader implementing UI copy or score-explanation logic from the contract will describe the score incorrectly (e.g. "average of dimensions"), which is exactly the trust/transparency failure mode Phase 19 set out to fix.

**Fix:** Update the three contract surfaces (and the stray comments) to the actual semantics. Suggested wording:
```
overallScore   number   0~100 종합 = core 차원(angle/line)의 min (min-of-core).
                        stability 는 종합 입력에서 제외(보조 지표). core 부재 시 절대트랙 단독.
```
Also fix `pipeline/app.py:1999` (`# 4차원 평균` → `# min-of-core (angle/line); stability 비기여`) and `assemble.py:681-682`.

## Warnings

### WR-01: `_apply_vision_veto` production dict uses `overallScore`, but its contract test asserts on `overall` — v2 will key the wrong field

**File:** `backend/functions/pipeline/app.py:1631-1656` (caller `:2223`); test `backend/tests/test_pipeline_mode3.py:228-241`

**Issue:** In production, `_apply_vision_veto(result, ...)` receives the `assemble.build_result` dict whose keys are `overallScore` / `dimensionScores` (see `assemble.py:714-716`). The test `test_vision_hook_passthrough` constructs `score_result = {"overall": 73, "dimensionScores": {...}}` — key `overall`, not `overallScore`. For v1 this is harmless because the hook is pure identity (`out is score_result`), so the test passes. But the test encodes the **wrong field name** as the contract, and the docstring promises "v2 가 mutation 도입 시 이 hook 이 차원 강등을 적용한다." When v2 reads/mutates `score_result["overall"]`, it will silently miss the real key (`overallScore`) on production data and KeyError or no-op. The pass-through test gives false confidence that the shape is correct.

**Fix:** Align the test fixture key to the production contract:
```python
score_result = {
    "overallScore": 73,
    "dimensionScores": {"angle": 70, "line": 75, "stability": 80},
}
snapshot = {"overallScore": score_result["overallScore"], ...}
...
assert score_result["overallScore"] == snapshot["overallScore"]
```
Or document on `_apply_vision_veto` that v2 must read `overallScore` (not `overall`).

### WR-02: `score_from_deviation` does not guard NaN/Inf deviation input — produces 0, silently masking missing data

**File:** `backend/shared/python/sunity_shared/analysis/kismam.py:111-117`

**Issue:** `score_from_deviation(deviation_deg, tol)` computes `z = deviation/tol` then `100*exp(-0.5*z*z)`. If `deviation_deg` is `NaN` (a joint with no finite frames), `np.exp(-0.5*NaN)` is `NaN`, and `int(round(NaN))` raises `ValueError: cannot convert float NaN to integer`. If `deviation_deg` is `+Inf`, `exp(-Inf)=0` → score 0 (treated as a maximal fault). The deduction `overall_score` (`kismam.py:228`) similarly does `max(0, dev - tol)`; with `NaN` deviation, `total_penalty` becomes `NaN` → `int(round(NaN))` raises. `assess` (`kismam.py:156`) coerces input via `np.asarray(..., dtype=float)` but does not reject NaN/Inf, and upstream `per_joint_deviation` / `extension_deviation` can yield NaN when a joint is never observed.

**Fix:** Sanitize at the scoring boundary:
```python
def score_from_deviation(deviation_deg, tolerance_deg=_IPSF_TOLERANCE_DEG):
    d = float(deviation_deg)
    if not np.isfinite(d):
        return 0  # or skip — but never raise
    z = d / max(tolerance_deg, 1e-6)
    return max(0, min(100, int(round(100.0 * float(np.exp(-0.5 * z * z))))))
```
And in `overall_score`, skip non-finite `a.deviation_deg` rather than letting `NaN` poison `total_penalty`.

### WR-03: `_deficit_summary_for` uses `max(dict, key=dict.get)` — works but breaks if values are NaN

**File:** `backend/shared/python/sunity_shared/analysis/assemble.py:320, 326`

**Issue:** `worst_key = max(line_defs, key=line_defs.get)` / `max(stab_wobble, key=...)`. The producing helpers (`line_deficits_by_joint`, `stability_wobble_by_joint`) already filter `np.isnan` (dimensions.py:331, 354), so in normal flow this is safe. However, the comparison against NaN is order-dependent and would silently pick an arbitrary key if a NaN ever slipped through (NaN comparisons are always False). This couples correctness of `assemble` to an invariant enforced two modules away with no local guard.

**Fix:** Defensive: filter to finite values before `max`, or assert the helper contract locally:
```python
finite = {k: v for k, v in line_defs.items() if v == v}  # drop NaN
if finite:
    worst_key = max(finite, key=finite.get)
```

### WR-04: `normalizeFrames` last-resort clones `prevValid` whose joint count may differ from the current frame

**File:** `app/src/lib/normalizePose3d.ts:215-221`

**Issue:** When a frame cannot be normalized but `prevValid` exists, the code pushes `prevValid.map(...)`. `prevValid` was produced from an earlier frame and has that frame's joint count. If frame `t` has a different joint count (e.g. a truncated/garbled frame from a malformed Firestore doc), the output frame at index `t` will have the previous frame's joint count, not `jointKeys.length`. `PoseViewer3D` indexes joints per frame; a frame with the wrong joint count could mis-render or index out of bounds. The zero-skeleton fallback (`:220`) correctly uses `jointKeys.length`, but the prev-clone path does not.

**Fix:** Normalize the clone to the expected joint count, or only clone when `prevValid.length === (jointCount > 0 ? jointCount : jointKeys.length)`; otherwise fall back to `zeroSkeleton(jointKeys.length)`.

### WR-05: `hold_window` minimum window `w = max(2, ...)` can exceed `t`, producing an empty slice for `t==1` edge interplay

**File:** `backend/shared/python/sunity_shared/analysis/dimensions.py:186-199`

**Issue:** `hold_window` returns early for `t <= 1`, so the loop only runs for `t >= 2`, and `w = max(2, min(t, t//4))` is bounded by `min(t, ...)` so `w <= t` — this specific function is safe. The concern is `_select_window` (`:292-311`): when a `profile.hold_window` is supplied with `s == e` (e.g. `(5, 5)` after clamping), `a[s:e]` is an **empty** slice. Downstream `line_score` (`:249`) and `stability_score` (`:234`) guard `shape[0] == 0` / `< 2`, but `extension_deviation` (`:277-278`) does `np.mean(sliced, axis=0) if sliced.shape[0] > 0 else zeros` — fine. However `_hold_window_median_dict` in the pipeline (`app.py:1615-1617`) guards `sliced.shape[0] == 0` and returns `{}`, which then makes `kismam.assess` emit all `target_angle=None`. So a degenerate `hold_window` silently strips all displayed target angles for mode3-first without any warning. Not a crash, but a quiet quality degradation.

**Fix:** In `_select_window`, after clamping, if `s == e` fall back to the auto `hold_window(a)` rather than returning an empty window, and/or log when a profile-supplied window collapses to empty.

### WR-06: `build_keypoint_report` imports `math as _math` inside loops/closures repeatedly

**File:** `backend/shared/python/sunity_shared/analysis/assemble.py:841, 881`

**Issue:** `import math as _math` appears inside the per-frame loop (`:841`) and again before the axis loop (`:881`), and `_safe` is defined as a closure inside the `for af in axis_frames` loop (`:883`). Re-importing per iteration and re-defining the closure per frame is wasteful and obscures intent; more importantly the `assert` statements at `:905-909` enforce length invariants at runtime — if any branch above miscounts (e.g. a future edit forgets to append for one joint), the function raises `AssertionError` in production rather than degrading gracefully. Asserts can also be stripped under `python -O`, silently disabling the only length guard.

**Fix:** Hoist `import math` to module top. Move `_safe` out of the loop. Replace the length `assert`s with explicit `if len(...) != ...: raise ValueError(...)` (or rely on `KeypointReport.__post_init__`) so the invariant is not optimized away.

### WR-07: `_load_motion_ipsf_map` caches a mutable module-level dict shared across all invocations without copy

**File:** `backend/shared/python/sunity_shared/analysis/assemble.py:63, 80-88, 102`

**Issue:** `_MOTION_IPSF_MAP_CACHE` is a module-global dict populated once and returned by reference from `_load_motion_ipsf_map()`. `lookup_motion_branch` only reads `entry = _load_..._map().get(motion_id)` then `.get(...)` on it, so today there is no mutation. But the cache is shared across Lambda invocations and threads (RunPod single-worker mitigates, but Lambda containers are reused), and exposing the raw cached dict invites a future caller to mutate it and corrupt all subsequent analyses. Combined with no file-not-found guard (`read_text` will raise if `motion_ipsf_map.json` is missing), a deploy that omits the data file fails every analysis with an unhandled exception inside `lookup_motion_branch` rather than degrading to `_SAFE_DEFAULT_BRANCH`.

**Fix:** Wrap the file read in try/except returning an empty map (then `lookup_motion_branch` naturally falls back to `_SAFE_DEFAULT_BRANCH`), and return a read-only / copied view from the loader. Example:
```python
def _load_motion_ipsf_map() -> dict:
    global _MOTION_IPSF_MAP_CACHE
    if _MOTION_IPSF_MAP_CACHE is None:
        try:
            raw = json.loads(_MOTION_IPSF_MAP_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log.exception("motion_ipsf_map load 실패 — 안전 기본 사용")
            raw = {}
        _MOTION_IPSF_MAP_CACHE = {k: v for k, v in raw.items() if not str(k).startswith("_")}
    return _MOTION_IPSF_MAP_CACHE
```

## Info

### IN-01: `simulatedResult.ts` mode1/mode3 fixtures omit `scoringBasis`/`scoringBasisLabel`

**File:** `app/src/lib/simulatedResult.ts:275-300, 416-438`

**Issue:** The Phase 19 contract adds `scoringBasis`/`scoringBasisLabel` to both `Mode1Comparison` and `Mode3Comparison`, and `DimensionDetailModal` branches on `scoringBasis` (`isReferenceFreeBasis`). The simulated/demo fixtures never set these fields, so the demo path always renders the legacy "세계 심사 기준" copy and never exercises the new reference-free copy branch (`formulaFor` referenceFree path). Demo screens won't reflect the new trust-visibility behavior. Fields are optional so this is not a type error.

**Fix:** Add representative `scoringBasis` values to at least the mode3-first and mode3-plateau scenarios (e.g. `reference_free_absolute`) so the reference-free copy path is demoable.

### IN-02: `build_keypoint_report` NaN-check comment `# noqa: PLR0124 — NaN check` plus duplicate finite check

**File:** `backend/shared/python/sunity_shared/analysis/assemble.py:830-847`

**Issue:** The `(x == x) and (y == y)` self-comparison NaN check (`:833-834`) is immediately followed by an Inf/finite check via `_math.isfinite` (`:843`). `math.isfinite` already returns False for NaN, making the self-comparison block redundant. Two overlapping guards for the same condition increase maintenance surface.

**Fix:** Drop the `(x == x)` block and rely solely on `math.isfinite(x) and math.isfinite(y)`.

### IN-03: Duplicated "박제 박제 박제 ..." filler in docstrings

**File:** `backend/shared/python/sunity_shared/analysis/dimensions.py:246`, `assemble.py:188-189`, `simulatedResult.ts:208`

**Issue:** Several docstrings/comments contain repeated filler tokens, e.g. `extension_deviation 박제 박제 박제 박제 박제 박제 박제` (dimensions.py:246) and `99% 박제 박제` (assemble.py:189). These are noise that obscures the actual rationale and violate the project memory guidance to avoid filler use of the term. Not a behavior issue.

**Fix:** Replace with the intended prose (e.g. "line_score / stability_score 와 동일 windowing 사용 — drift 방지").

### IN-04: `_PENALTY_PER_DEG` and `NOT_POLE_SIMILARITY_THRESHOLD` are unvalidated magic constants with `[ASSUMED]` status

**File:** `backend/shared/python/sunity_shared/analysis/kismam.py:66`, `backend/shared/python/sunity_shared/models.py:244`

**Issue:** `_PENALTY_PER_DEG = 1.2` is honestly flagged `[ASSUMED]` and the no-overfit memory is cited — good discipline. However, since `overall_score` is now `100 - sum(over_i * weight_i * 1.2)`, with the default weight `1.0` for all 8 joints, a single joint at `dev = 103°` (over = 83°) already drives `overall` to 0 (`83 * 1.2 = ~99.6` penalty). The deduction is uncapped per-joint and additive across 8 joints, so two moderate faults (`over ~42°` each) also zero the score. This may be intentional ("single major fault dominates"), but there is no test asserting the *upper* sensitivity boundary (the existing tests only check `< 70` and `>= 90`). Without an upper-bound test the coefficient could silently become a curve-fit knob in a later phase.

**Fix:** Add a test pinning the intended behavior at the boundary (e.g. "two ~30° faults should not both zero the score unless that's intended") and document the additive/uncapped property explicitly in the docstring.

---

_Reviewed: 2026-06-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
