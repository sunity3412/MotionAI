---
phase: 06-coaching
fixed_at: 2026-06-08T00:00:00Z
review_path: .planning/phases/06-coaching/06-REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 10
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-06-08T00:00:00Z
**Source review:** `.planning/phases/06-coaching/06-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 10 (3 Critical + 7 Warning, Info skipped per instructions)
- Fixed: 10
- Skipped: 0

**Test results:**
- `backend/tests/phase06/`: **136 passed, 1 skipped** (baseline 120 + 16 new tests added by this fix pass).
- adjacent pipeline tests (`tests/test_pipeline_body_profile_injection.py` + `tests/test_pipeline_gemini_integration.py` + `tests/test_pipeline_recognizer_switch.py`): **26 passed**.
- combined: **162 passed, 1 skipped**.
- `cd app && npm run typecheck`: **EXIT 0** (clean).

## Decisions

- **WR-01 (`torso_px` field): keep + document + add pipeline sanity-check log.**
  Review offered two paths — delete the dead field (contract change cascading across TS / Python dataclass / docs §8.2 / seed script schema / extract script `_sp_to_camel_dict` / 6 fixtures) or use it for sanity check. Deletion is contract-breaking + already-deployed-data-breaking (Plan 06-03 fixture has `torsoPx`). Chose to **use** it: documented its role in the `BodyComparisonSourcePose` docstring, and added a `log.warning` in the mode1 path when `target_torso / ref.torso_px` ratio falls outside `[1/3, 3]` — catches "filmed from across the room" cases. No frozenset/warning enum change needed → no 3-way lockstep churn. Future plan can promote the log to a `source_torso_px_mismatch` warning enum if telemetry shows it useful.

- **WR-02 (magic-number fallback): full removal + new warning enum (3-way lockstep).**
  The `200.0 * torso_scale` sentinel hid measurement failures behind a passable scale. Chose to gate `target_torso_px is None` to `gate_open = False` and emit `target_torso_px_missing` warning. This required 3-way contract lockstep: `body_normalizer.BODY_COMPARISON_WARNING_CODES` (frozenset 8 → 9), `app/src/types/analysis.ts` comment block, `docs/contract.md §8` warnings table, and `test_body_comparison_report_lockstep.py` 8 → 9 enum check. All updated together. The lockstep gate test (`test_docs_contract_md_section_8`) still passes.

- **WR-03 (anonymous-pipeline uid): closure rebind in `_process`.**
  The review suggested either closure or `recognize()` API extension. Chose the lower-blast-radius closure rebind — no Protocol change, no Gemini recognizer touch. `_ensure_recognizer` keeps its `"anonymous-pipeline"` default (safety net for any code path that bypasses `_process`); `_process` rebinds `unregistered_hook` to a closure capturing the real `uid` on every entry.

- **WR-05 (KeyError vs neutral): chose Option 1 (module-load assert) per review's preference.**
  Added `_KNOWN_REF_SEGMENT_RATIO_EDGES` frozenset + bidirectional assert at module load. Future contributor adding a tree edge without ratio mapping (or removing one without cleaning up) gets `AssertionError` at `import body_normalizer` — fail at dev time, not on every user's analysis.

- **WR-06 (Enum branch dead code): added positive contract-lock test.**
  Did **not** convert any field to Enum (that would break Firestore serialization). Added test that asserts `BodyComparisonReport(...)` → camelCase dict produces plain `str` for `comparisonType` + `deficitCode`. Future contributor switching to Enum gets a failing test before merge.

- **WR-07 (motion_query_hint leak): always rebind in `_process`.**
  Did **not** extend `TechniqueRecognizer` Protocol (would touch Gemini adapter + Fallback adapter + Protocol definition + tests for both). Simplest fix is the if/else rebind — always set, even to `None`. The Protocol extension is a future plan if more recognizer attributes need request-scoped state.

## Fixed Issues

### CR-01: `BodyNormalizationProfile(**ref_profile_dict)` crashes on camelCase Firestore docs

**Files modified:** `backend/functions/pipeline/app.py`, `backend/tests/phase06/test_coerce_body_profile_dict.py`
**Commit:** `6449eca`
**Applied fix:** Added `_coerce_body_profile_dict(raw)` helper mirroring `_coerce_source_pose_dict`. Accepts both camelCase (production Firestore) and snake_case (test fixtures) and emits snake_case kwargs. Applied at all three call sites (mode1 ref / mode3_first matched / mode3_progress prev). Added end-to-end regression test that drives `_process` with a production-shape camelCase reference doc — verified to FAIL without the fix (`TypeError: BodyNormalizationProfile.__init__() got an unexpected keyword argument 'estimatedHeightScale'`) and PASS with it.

### CR-02: `mode3_progress` reads camelCase prev doc but constructs from snake_case

**Files modified:** `backend/functions/pipeline/app.py`, `backend/tests/phase06/test_coerce_body_profile_dict.py`
**Commit:** `6449eca`
**Applied fix:** Same helper from CR-01 applied to `prev["bodyNormalizationProfile"]`. Added explicit regression test `test_pipeline_mode3_progress_with_production_camel_case_prev_doc` that drives `_process` with a production-shape camelCase prev doc (matching exactly what `_dataclass_to_camel_case_dict(profile)` produces in `complete_analysis`) and verifies the analysis completes successfully.

### CR-03: `_coerce_source_pose_dict` silently mints invalid `BodyComparisonSourcePose`

**Files modified:** `backend/functions/pipeline/app.py`
**Commit:** `6449eca`
**Applied fix:** Replaced silent `or` defaults with explicit `None` checks. `joint_keys` and `values` missing → `ValueError` with diagnostic message. Other scalar fields (`frame_index`, `torso_px`, `confidence`, `measured_at`) → `ValueError` if missing rather than silent sentinel. Fixed the `_g("values", "values")` typo by switching to direct `raw.get("values")` (TS/Python field names match — no alias needed). The dataclass `__post_init__` now sees real values and validates them properly (`torso_px > 0`, `0 <= confidence <= 1.0`).

### WR-01: `BodyComparisonSourcePose.torso_px` persisted but never consumed

**Files modified:** `backend/functions/pipeline/app.py`, `backend/shared/python/sunity_shared/analysis/body_normalizer.py`
**Commit:** `ef629df`
**Applied fix:** Documented the field's purpose in the `BodyComparisonSourcePose` docstring (it's a reference-side anchor for downstream R&D + sanity checks, not used by the target-anchored normalization algorithm). Added a `log.warning` in the mode1 path when `target_torso / ref.torso_px` ratio is outside `[1/3, 3]` — catches dramatic camera-distance mismatches. Storage cost is now justified by an actual consumer. Future warning-enum promotion is documented inline.

### WR-02: Magic-number fallback `200.0 * torso_scale` masks data quality issues

**Files modified:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py`, `app/src/types/analysis.ts`, `docs/contract.md`, `backend/tests/phase06/test_body_comparison_report_lockstep.py`
**Commit:** `df1cb9d`
**Applied fix:** Added `'target_torso_px_missing'` to `BODY_COMPARISON_WARNING_CODES` frozenset (8 → 9). Extended `gate_open` condition to require `target_torso_px is not None`. Removed the `200.0 * torso_scale` magic-number fallback. Updated 3-way contract lockstep (TS comment block, docs §8 warnings table, lockstep test). The `test_docs_contract_md_section_8` enum gate now checks 9 codes.

### WR-03: `record_unregistered_keyword` hardcodes `uid="anonymous-pipeline"`

**Files modified:** `backend/functions/pipeline/app.py`, `backend/tests/phase06/test_unregistered_hook_uid_threading.py`
**Commit:** `e873d22`
**Applied fix:** In `_process`, after `_ensure_recognizer()`, rebind `recognizer.unregistered_hook` to a closure that captures the real caller `uid` via default-arg trick (`_uid=uid`). The `_ensure_recognizer` default hook keeps `"anonymous-pipeline"` as safety net for non-`_process` paths (none today). Updated comment to reflect this. Added regression test that verifies the rebound hook calls `record_unregistered_keyword(uid="user-42", ...)` with the real `uid` from `_process` invocation.

### WR-04: `_extract_target_torso_px` uses 2D distance, diverges from 3D algorithm semantics

**Files modified:** `backend/functions/pipeline/app.py`, `backend/scripts/extract_reference_body_profiles.py`, `backend/tests/phase06/test_pipeline_body_comparison.py`
**Commit:** `30a2cc6`
**Applied fix:** Switched both `_extract_target_torso_px` (pipeline) and `_frame_torso_px` (extract script) to 3D Euclidean distance (`sqrt(dx^2 + dy^2 + dz^2)`). `is_foreshortening_detected` still uses 2D (intentional — the detection is about projection failure, not anchor scale). Added regression test using a forward-lean fixture (dy=50, dz=150) that verifies 3D distance ≈ 158 is computed, not 2D 50 — guards against future revert to 2D-only.

### WR-05: `_ref_segment_ratio` KeyError vs neutral fallback

**Files modified:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py`, `backend/tests/phase06/test_kinematic_tree_edge_coverage.py`
**Commit:** `7acda2e`
**Applied fix:** Added `_KNOWN_REF_SEGMENT_RATIO_EDGES` frozenset + bidirectional `assert` at module load (`KINEMATIC_TREE_EDGES ⊆ known` AND `known ⊆ KINEMATIC_TREE_EDGES`). Future contributor adding a tree edge without ratio mapping (or removing one without cleaning up the known set) gets `AssertionError` on import — fail at dev time, not on every user's analysis. Added test file with 3 cases: forward-coverage, dead-mapping detection, and live-call check across all 13 edges.

### WR-06: `_dataclass_to_camel_case_dict` Enum branch unreachable for `BodyComparisonReport`

**Files modified:** `backend/tests/phase06/test_dataclass_to_camel_case_dict.py`
**Commit:** `0143d7c`
**Applied fix:** Added positive contract-lock test `test_body_comparison_report_comparison_type_is_plain_str` that constructs a real `BodyComparisonReport` (with finding) and asserts `result["comparisonType"]` and `result["findings"][0]["deficitCode"]` are plain `str` instances (not `Enum`). Future contributor converting either field to `Enum` (and thereby breaking Firestore serialization via `dataclasses.asdict`) gets a failing test before merge.

### WR-07: Pipeline overwrites `recognizer.motion_query_hint` without restoring it

**Files modified:** `backend/functions/pipeline/app.py`, `backend/tests/phase06/test_motion_query_hint_leak.py`
**Commit:** `ca6ed25`
**Applied fix:** Changed the conditional set to an unconditional rebind: `recognizer.motion_query_hint = ref_motion_id if (mode == MODE_EXPERT and ref_motion_id) else None`. Every `_process` entry now explicitly sets (or clears) the hint — no stale value can leak from previous SQS message. Added 2-case regression test: mode3 with pre-set hint verifies reset to `None`, mode1 with `referenceMotionId` verifies set to that id.

## Skipped Issues

(none — all 10 in-scope findings fixed)

## Info findings (out of scope per instructions)

The 5 Info findings (IN-01 through IN-05) were explicitly out of scope per the objective ("SKIP Info findings"). For continuity, the documents the review flagged:
- IN-01 — `_g("values", "values")` degenerate alias: incidentally addressed by CR-03 fix (switched to direct `raw.get("values")` with comment).
- IN-02, IN-03, IN-04, IN-05 — not modified.

## Commits (8 atomic, in order)

| Commit | Subject |
|---|---|
| `6449eca` | fix(06): CR-01/CR-02/CR-03 add _coerce_body_profile_dict + harden source_pose coerce + regression test |
| `ef629df` | fix(06): WR-01 document torso_px role + add pipeline sanity-check log |
| `df1cb9d` | fix(06): WR-02 remove magic-number torso_px fallback + add target_torso_px_missing warning (3-way lockstep) |
| `e873d22` | fix(06): WR-03 thread real uid through unregistered_hook via closure rebind in _process |
| `30a2cc6` | fix(06): WR-04 use 3D Euclidean distance for torso_px anchor (self-consistent with 3D kinematic tree) |
| `7acda2e` | fix(06): WR-05 add module-load assert for KINEMATIC_TREE_EDGES vs _ref_segment_ratio coverage |
| `0143d7c` | fix(06): WR-06 add positive contract-lock test that comparisonType / deficitCode are plain str (not Enum) |
| `ca6ed25` | fix(06): WR-07 always rebind recognizer.motion_query_hint to prevent leak across analyses |

## Test files added (5)

- `backend/tests/phase06/test_coerce_body_profile_dict.py` (7 cases — CR-01/02/03)
- `backend/tests/phase06/test_unregistered_hook_uid_threading.py` (2 cases — WR-03)
- `backend/tests/phase06/test_kinematic_tree_edge_coverage.py` (3 cases — WR-05)
- `backend/tests/phase06/test_motion_query_hint_leak.py` (2 cases — WR-07)
- (also added 2 tests inline: `test_extract_target_torso_px_uses_3d_distance` in `test_pipeline_body_comparison.py` — WR-04; `test_body_comparison_report_comparison_type_is_plain_str` in `test_dataclass_to_camel_case_dict.py` — WR-06)

Net: 16 new tests on top of baseline 120 → 136 passed + 1 skipped.

---

_Fixed: 2026-06-08T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
