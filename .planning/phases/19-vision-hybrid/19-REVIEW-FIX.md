---
phase: 19-vision-hybrid
fixed_at: 2026-06-18T00:00:00Z
review_path: .planning/phases/19-vision-hybrid/19-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 19: Code Review Fix Report

**Fixed at:** 2026-06-18
**Source review:** .planning/phases/19-vision-hybrid/19-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (1 Critical + 7 Warning; Info skipped per request)
- Fixed: 8
- Skipped: 0

## Verification

- Backend (`pytest`) Phase 19 targeted suite: 71 passed, 6 skipped (kismam,
  dimensions, assemble, assemble_dimension_explanation, pipeline_mode3,
  anchor_known_answer). RED→GREEN cases stay GREEN.
- Full backend suite (excluding pre-broken gemini collection modules):
  1699 passed — identical pass count to the original main HEAD baseline,
  i.e. zero regressions introduced. The 73 pre-existing failures all depend
  on the absent `google.genai` dependency and fail identically on main HEAD.
- `cd app && tsc --noEmit`: exit 0.

## Fixed Issues

### CR-01: `overallScore` contract description still said "평균" (average) across all 3 surfaces

**Files modified:** `docs/contract.md`, `app/src/types/analysis.ts`, `backend/shared/python/sunity_shared/analysis/assemble.py`, `backend/functions/pipeline/app.py`
**Commit:** 262e1ee
**Applied fix:** Updated all three contract surfaces plus the `pipeline/app.py:1999`
inline comment from "평균" to the actual semantics: `overallScore = min-of-core(angle/line)`,
stability excluded (보조 지표), core 부재 시 절대트랙 단독. Honoured the contract-first
invariant by editing TS + Python + docs together.

### WR-01: `_apply_vision_veto` test asserted on `overall`, production key is `overallScore`

**Files modified:** `backend/tests/test_pipeline_mode3.py`, `backend/functions/pipeline/app.py`
**Commit:** 82cdfd8
**Applied fix:** Aligned `test_vision_hook_passthrough` fixture to the production
`overallScore` key (production passes `assemble.build_result`), and documented on
`_apply_vision_veto` that v2 must read/write `score_result["overallScore"]` (not `overall`).

### WR-02: `score_from_deviation` / `overall_score` did not guard NaN/Inf deviation

**Files modified:** `backend/shared/python/sunity_shared/analysis/kismam.py`
**Commit:** 7f4904a
**Applied fix:** `score_from_deviation` returns 0 for non-finite deviation instead of
raising `int(round(NaN))`. `overall_score` skips non-finite per-joint deviation rather than
poisoning `total_penalty`. Finite-input scoring semantics unchanged — no threshold
recalibration (graceful degrade only, per no-overfit constraint).

### WR-03: `_deficit_summary_for` `max(dict, key=dict.get)` breaks on NaN values

**Files modified:** `backend/shared/python/sunity_shared/analysis/assemble.py`
**Commit:** fb3f5fc
**Applied fix:** Added a local finite-value filter (`{k: v for k, v in d.items() if v == v}`)
before `max()` on both the line and stability deficit paths, decoupling correctness from
the np.isnan invariant enforced two modules away in dimensions.py.

### WR-04: `normalizeFrames` prev-clone path could emit wrong joint count

**Files modified:** `app/src/lib/normalizePose3d.ts`
**Commit:** 4c33e36
**Applied fix:** The last-resort `prevValid` clone now runs only when
`prevValid.length === (jointCount > 0 ? jointCount : jointKeys.length)`; otherwise it falls
back to a `zeroSkeleton` of the expected joint count. Preserves the per-frame joint
count == jointKeys.length invariant so PoseViewer3D cannot index out of bounds.

### WR-05: profile `hold_window` collapsing to empty slice silently strips target angles

**Files modified:** `backend/shared/python/sunity_shared/analysis/dimensions.py`
**Commit:** aab968d
**Applied fix:** In `_select_window`, when a profile-supplied window clamps to `s == e`
(empty slice), fall back to the auto `hold_window(a)` instead of returning an empty window
(which would make `_hold_window_median_dict` return `{}` → all `target_angle=None`).

### WR-06: `build_keypoint_report` re-imports math per loop + asserts strippable under -O

**Files modified:** `backend/shared/python/sunity_shared/analysis/assemble.py`
**Commit:** f555f04
**Applied fix:** Hoisted `import math` to module top, defined `_safe` once before the axis
loop (removed per-frame closure redefinition + per-iteration import), and replaced the five
length `assert`s with explicit `if len(...) != ...: raise ValueError(...)` so the only
length guard is not optimized away under `python -O`.

### WR-07: `_load_motion_ipsf_map` no file-not-found guard + exposes mutable shared cache

**Files modified:** `backend/shared/python/sunity_shared/analysis/assemble.py`
**Commit:** 6484b17
**Applied fix:** Wrapped the JSON read in `try/except (OSError, ValueError)` returning an
empty map (missing data file degrades to `_SAFE_DEFAULT_BRANCH` instead of failing every
analysis), and returns `dict(_MOTION_IPSF_MAP_CACHE)` (a shallow copy) so callers cannot
mutate the shared module-global cache across Lambda invocations / threads. Added a
module-level `log`.

## Skipped Issues

None in scope. Info findings (IN-01 through IN-04) were intentionally out of scope per the
fix request (Critical + Warning only).

---

_Fixed: 2026-06-18_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
