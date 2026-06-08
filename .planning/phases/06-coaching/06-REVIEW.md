---
phase: 06-coaching
reviewed: 2026-06-08T00:00:00Z
depth: standard
files_reviewed: 39
files_reviewed_list:
  - app/package.json
  - app/scripts/revert-reference-body-profile.mjs
  - app/scripts/seed-reference-body-profile.mjs
  - app/src/lib/userAnalyses.ts
  - app/src/types/analysis.ts
  - backend/functions/pipeline/app.py
  - backend/scripts/README_extract_reference_body_profiles.md
  - backend/scripts/extract_reference_body_profiles.py
  - backend/shared/python/sunity_shared/analysis/body_normalizer.py
  - backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
  - backend/shared/python/sunity_shared/analysis/technique.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/shared/python/sunity_shared/models.py
  - backend/tests/phase06/__init__.py
  - backend/tests/phase06/conftest.py
  - backend/tests/phase06/fixtures/__init__.py
  - backend/tests/phase06/fixtures/_factory.py
  - backend/tests/phase06/fixtures/_generate.py
  - backend/tests/phase06/fixtures/fixture_160cm_pro_vs_140cm_student.json
  - backend/tests/phase06/fixtures/fixture_foreshortening_lying_pose.json
  - backend/tests/phase06/fixtures/fixture_high_dispersion_arms_sprawled.json
  - backend/tests/phase06/fixtures/fixture_lefty_vs_righty_twist.json
  - backend/tests/phase06/fixtures/fixture_split_angle_hipline.json
  - backend/tests/phase06/fixtures/fixture_unstable_arm_swing.json
  - backend/tests/phase06/fixtures/test_fixtures_loadable.py
  - backend/tests/phase06/fixtures/test_reference_body_data.json
  - backend/tests/phase06/test_backfill_scripts_dry_run.py
  - backend/tests/phase06/test_body_comparison_report_lockstep.py
  - backend/tests/phase06/test_body_normalizer_confidence.py
  - backend/tests/phase06/test_body_normalizer_ipsf_deficit.py
  - backend/tests/phase06/test_body_normalizer_kinematic_tree.py
  - backend/tests/phase06/test_compare_body_profiles.py
  - backend/tests/phase06/test_dataclass_to_camel_case_dict.py
  - backend/tests/phase06/test_firestore_admin_body_comparison.py
  - backend/tests/phase06/test_firestore_admin_update_reference_body_data.py
  - backend/tests/phase06/test_gemini_recognizer_populates_motion_id.py
  - backend/tests/phase06/test_phase06_integration_smoke.py
  - backend/tests/phase06/test_pipeline_body_comparison.py
  - backend/tests/phase06/test_pipeline_firestore_integration.py
  - backend/tests/phase06/test_technique_profile_motion_id.py
  - backend/tests/test_pipeline_body_profile_injection.py
  - backend/tests/test_pipeline_gemini_integration.py
  - backend/tests/test_pipeline_recognizer_switch.py
  - docs/contract.md
findings:
  critical: 3
  warning: 7
  info: 5
  total: 15
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-06-08T00:00:00Z
**Depth:** standard
**Files Reviewed:** 39
**Status:** issues_found

## Summary

Phase 6 implements the body-normalization comparison engine (PERS-01): RTMW segment-ratio measurement, kinematic-tree reprojection, IPSF absolute deficits, and a `BodyComparisonReport` written to Firestore. The dataclass design is careful (frozen, post-init validation, frozenset warning enum) and the 3-way contract lockstep tests (TS + Python + docs/contract.md) are solid. Test coverage is broad (20+ files, 6 synthetic fixtures, mock-based pipeline smoke).

However, adversarial review surfaced three production-blocking defects centered on a **case-convention split between write paths (camelCase, via the seed script and `complete_analysis`) and read paths (snake_case `BodyNormalizationProfile(**dict)` in the pipeline)**. Every test stub builds reference docs with snake_case keys, so the entire production path is unverified — the integration smoke tests pass while production will raise `TypeError: unexpected keyword argument` on the first real Mode 1 analysis. A related coerce helper exists for `BodyComparisonSourcePose` but was not extended to `BodyNormalizationProfile`. A second blocker: `BodyComparisonSourcePose.values` validates `math.isfinite` per element but the `_coerce_source_pose_dict` helper applies `float()` blindly, surfacing a confusing `TypeError` instead of a `ValueError`, and the prev-doc / matched-ref paths share this gap.

Beyond the camelCase blockers, several quality issues weaken robustness: a stale 2D `torso_px` is persisted but never read, a magic-number fallback (`200.0 * torso_scale`) sneaks into the normalizer when frame extraction fails, the `dimensionExplanation` shadow path uses windowing constants that disagree with the fixture-driven `_compute_temporal_variance_per_segment`, and `record_unregistered_keyword` hardcodes `uid="anonymous-pipeline"` — the very TODO comment in the code admits this loses the originating user. The integration tests are extensive but **stub out the field-name mismatch**, so they cannot detect any of the blockers in production. Recommend halting any Mode 1 reference seeding until BL-01/BL-02 are fixed and re-verified end-to-end against an actual Firestore document.

## Critical Issues

### CR-01: `BodyNormalizationProfile(**ref_profile_dict)` will crash on camelCase Firestore reference docs

**File:** `backend/functions/pipeline/app.py:684-689` (mirror occurrences at `:776-778`, `:812-814`)
**Issue:** The pipeline unpacks the Firestore `bodyNormalizationProfile` dict directly into the dataclass constructor:
```python
ref_profile_dict = ref.get("bodyNormalizationProfile")
ref_profile = (
    BodyNormalizationProfile(**ref_profile_dict)
    if ref_profile_dict
    else None
)
```
`BodyNormalizationProfile` declares snake_case fields (`estimated_height_scale`, `arm_scale`, `leg_scale`, `torso_scale`, `shoulder_hip_ratio`). However, three different write paths persist camelCase:

1. `backend/scripts/extract_reference_body_profiles.py:_bp_to_camel_dict` emits `estimatedHeightScale` / `armScale` / `legScale` / `torsoScale` / `shoulderHipRatio` (lines 68-79).
2. `app/scripts/seed-reference-body-profile.mjs` validates the same camelCase keys (`REQUIRED_BODY_PROFILE_FIELDS`, lines 22-30) and merges them verbatim into Firestore.
3. `firestore_admin.complete_analysis` writes `bodyNormalizationProfile` produced by `_dataclass_to_camel_case_dict(student_profile)` (`pipeline/app.py:880-882`), so every previous analysis's stored profile is camelCase too — affecting line 812's `mode3_progress` path.

Every Phase 6 integration test (e.g. `test_phase06_integration_smoke._ref_profile_dict`, `test_pipeline_body_comparison._ref_profile_dict`, `test_pipeline_firestore_integration._ref_profile_dict`) builds reference docs with snake_case keys, so the tests pass but the **first real Mode 1 analysis against a properly-seeded reference will raise `TypeError: __init__() got an unexpected keyword argument 'estimatedHeightScale'`**, which is caught by the broad `except Exception` in `lambda_handler` (line 945) and mapped to `server_error` — i.e. silent failure for the user with no diagnostic. Same for `mode3_progress` and the Gemini `mode3_first` fallback paths.

**Fix:** Introduce a coerce helper mirroring `_coerce_source_pose_dict` and use it everywhere `BodyNormalizationProfile` is built from a Firestore dict:
```python
def _coerce_body_profile_dict(raw: dict | None) -> dict | None:
    if raw is None:
        return None
    def _g(snake: str, camel: str):
        return raw[snake] if snake in raw else raw.get(camel)
    return {
        "estimated_height_scale": float(_g("estimated_height_scale", "estimatedHeightScale")),
        "arm_scale":             float(_g("arm_scale",             "armScale")),
        "leg_scale":             float(_g("leg_scale",             "legScale")),
        "torso_scale":           float(_g("torso_scale",           "torsoScale")),
        "shoulder_hip_ratio":    float(_g("shoulder_hip_ratio",    "shoulderHipRatio")),
        "confidence":            float(_g("confidence",            "confidence")),
        "warnings":              list(_g("warnings",               "warnings") or []),
    }
# call sites:
ref_profile = BodyNormalizationProfile(**_coerce_body_profile_dict(ref_profile_dict)) if ref_profile_dict else None
```
Add a regression test that drives `_process` end-to-end with a **camelCase** reference document (matching what the seed script actually writes) — the existing smoke tests are blind to this drift.

### CR-02: `mode3_progress` reads `prev["bodyNormalizationProfile"]` as camelCase but constructs from snake_case

**File:** `backend/functions/pipeline/app.py:810-814`
**Issue:** The mode3_progress branch does:
```python
prev_profile = BodyNormalizationProfile(
    **prev["bodyNormalizationProfile"]
)
```
`get_previous_analysis` returns the Firestore document `to_dict()` (`firestore_admin.py:321-350`), and `complete_analysis` stores `bodyNormalizationProfile` after running it through `_dataclass_to_camel_case_dict` (`pipeline/app.py:880-882, 891`, then `firestore_admin.py:169` writes the dict verbatim). So `prev["bodyNormalizationProfile"]` is **always camelCase in production** yet the dataclass requires snake_case. Same TypeError as CR-01, but specifically affects every user's second-and-later Mode 3 analysis — i.e. the entire "progress over time" feature. There is no production test that constructs `prev_doc` with camelCase; `test_process_mode3_progress_with_prev_body_profile` (`test_pipeline_body_comparison.py:561-585`) uses `_ref_profile_dict()` which is snake_case.

The `bodyComparisonSourcePose` half of the same call site **does** route through `_coerce_source_pose_dict` (line 818), which proves the author knew Firestore stores camelCase — but only applied the fix to one of two payloads.

**Fix:** Apply the helper from CR-01 to all three Firestore-sourced `BodyNormalizationProfile(**...)` call sites (`:686, :776-778, :812-814`). Add a `mode3_progress` test that builds `prev_doc` with the actual camelCase shape produced by `_dataclass_to_camel_case_dict(profile)`.

### CR-03: `_coerce_source_pose_dict` silently mints invalid `BodyComparisonSourcePose` for malformed Firestore data

**File:** `backend/functions/pipeline/app.py:444-468`
**Issue:** The helper coerces fields with `or` fallbacks that hide real data corruption:
```python
joint_keys = _g("joint_keys", "jointKeys") or ()
values = _g("values", "values") or ()
...
"frame_index": int(_g("frame_index", "frameIndex") or 0),
"torso_px": float(_g("torso_px", "torsoPx") or 1.0),
"confidence": float(_g("confidence", "confidence") or 0.0),
"measured_at": int(_g("measured_at", "measuredAt") or 0),
```
Problems:
1. `joint_keys = (), values = ()` passes the validator (`len(values) == 4 * 0 == 0`) and yields a "pose" with zero keypoints — `to_keypoints_array()` then returns a `(0, 4)` ndarray that flows into `compare_body_profiles → normalize_pose_by_segments` which immediately raises `ValueError("source_keypoints must contain left_hip + right_hip")`, caught by the broad `except Exception` → `server_error`. The seed script schema validation (`seed-reference-body-profile.mjs:99-110`) is the only thing preventing this; any out-of-band Firestore write (admin console, future migration) bypasses it.
2. `torso_px` falling back to `1.0` is a defensible-but-misleading sentinel that **passes** the dataclass validator (`torso_px > 0`) yet produces an absurdly small reproject scale. A real measurement failure would silently degrade analysis quality instead of failing loudly.
3. `_g("values", "values")` — the second positional is a typo; both arguments are the same key, so the camelCase/snake_case alias logic does nothing for `values`. (The keys are literally identical for `values` and `confidence` in TS contract too, so behavior matches — but the helper's intent is obscured and a future renamer will be misled.)
4. `float(v)` over each value in `values` will raise `TypeError` (not the more specific `ValueError` the dataclass would have produced) if any element is `None` or a list (e.g. Firestore wrote nested arrays before the W5 validator was in place). The TypeError is then swallowed by `lambda_handler`.

**Fix:** Validate inputs explicitly, do not invent sentinels:
```python
def _coerce_source_pose_dict(raw: dict | None) -> dict | None:
    if raw is None:
        return None
    def _g(snake, camel):
        return raw[snake] if snake in raw else raw.get(camel)
    joint_keys = _g("joint_keys", "jointKeys")
    values     = _g("values",     "values")
    if not joint_keys or not values:
        raise ValueError(
            "bodyComparisonSourcePose missing joint_keys or values "
            "(firestore document corrupted — refusing to coerce silently)"
        )
    return {
        "joint_keys":  tuple(joint_keys),
        "values":      tuple(float(v) for v in values),
        "frame_index": int(_g("frame_index", "frameIndex")),
        "torso_px":    float(_g("torso_px",    "torsoPx")),
        "confidence":  float(_g("confidence",  "confidence")),
        "measured_at": int(_g("measured_at",  "measuredAt")),
    }
```
Let the dataclass validators reject malformed `torso_px <= 0`, and the caller's `try/except RuntimeError` map it to `server_error` with a usable log message.

## Warnings

### WR-01: `BodyComparisonSourcePose.torso_px` is persisted but never consumed

**File:** `backend/functions/pipeline/app.py:692-698, 781-791, 817-824` and `backend/shared/python/sunity_shared/analysis/body_normalizer.py:1194-1202`
**Issue:** The seed pipeline (`extract_reference_body_profiles.py:_build_source_pose`) measures `torso_px` on the reference's representative hold frame, persists it (`bodyComparisonSourcePose.torsoPx`), validates it (`__post_init__` enforces `torso_px > 0`), and reshapes it via `to_keypoints_array()`. But `compare_body_profiles` only uses **`target_torso_px`** (the student's torso pixel from `_extract_target_torso_px(pose_frames)`) when computing L_ref. The reference's `torso_px` is fetched, parsed, and then discarded — it is dead in the scoring path.

This is not a bug today (the algorithm is target-anchored by design per C1 fix) but it means: (a) the storage cost is wasted, (b) the validator gives false confidence that bad reference data was filtered out when it wasn't used at all, and (c) anyone reading the code will be misled into thinking the field matters.

**Fix:** Either delete `torso_px` from `BodyComparisonSourcePose` (and the seed pipeline) entirely, or use it for a sanity check (e.g. emit a warning if `|target_torso_px - reference.torso_px| / target_torso_px > 3.0` to detect "user filmed from across the room" cases). Document the decision in `body_normalizer.py:204-225` so the field's role is clear.

### WR-02: Magic-number fallback for `torso_px` masks data quality issues

**File:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py:1194-1196`
**Issue:**
```python
torso_px = target_torso_px if target_torso_px is not None else (
    200.0 * float(student_profile.torso_scale)
)
```
When `_extract_target_torso_px` returns `None` (no valid frames with all four shoulder/hip endpoints), the normalizer silently picks `200 × torso_scale ≈ 200 px` as the scale anchor. For a student filmed at a different focal length this produces silently-wrong absolute pixel distances throughout the IPSF deficit measurements — the deficits will still be computed (against `0.3 × shoulder_width` etc., which scale with the bad reproject) but the meaning of the deductions diverges from reality.

A `target_torso_px = None` path should emit a warning (e.g. `'target_torso_px_missing'`) and either disable the normalization (`gate_open = False`) or fall back to a measurement derived from the actual `pose_frames` average shoulder width.

**Fix:** Add `target_torso_px_missing` to `BODY_COMPARISON_WARNING_CODES`, and in `compare_body_profiles`:
```python
if target_torso_px is None:
    warnings.append("target_torso_px_missing")
    gate_open = False  # don't pretend we can reproject
```
Remove the `200.0 * torso_scale` magic number.

### WR-03: `record_unregistered_keyword` hardcodes `uid="anonymous-pipeline"`, losing user attribution

**File:** `backend/functions/pipeline/app.py:209-212`
**Issue:** The inline `_record_unregistered` closure that becomes `GeminiTechniqueRecognizer.unregistered_hook` passes a hardcoded UID:
```python
def _record_unregistered(keyword: str, video_hash: str) -> None:
    firestore_admin.record_unregistered_keyword(
        keyword, uid="anonymous-pipeline", video_hash=video_hash
    )
```
The TODO comment immediately above (line 206-208) admits the problem: "uid 정보 없음 — _process caller 시점에서 알지만 cache 생성 시점엔 미상". The result is that `term_collection/{keyword}.unique_users` is a single-element set (`["anonymous-pipeline"]`) regardless of how many distinct users encountered the term — the Phase 16 TERM-DATA-01 promotion logic (`pending → reviewing → approved`) will never see a real `unique_users` count, defeating the whole point of the schema.

The hook signature was already designed for this (`B3 fix` comment in `gemini_technique_recognizer.py:25-28`); the pipeline just isn't threading the UID through. `_process` knows the UID — it's a function parameter.

**Fix:** Capture the UID in a closure built inside `_process` or pass it through the recognizer interface. Simplest:
```python
# in _process, before recognizer.recognize:
if hasattr(recognizer, "unregistered_hook") and recognizer.unregistered_hook is not None:
    def _hook_with_uid(keyword: str, video_hash: str, _uid=uid) -> None:
        firestore_admin.record_unregistered_keyword(keyword, uid=_uid, video_hash=video_hash)
    recognizer.unregistered_hook = _hook_with_uid
```
Or refactor `_ensure_recognizer` to return a factory that takes UID. Either way, remove the `"anonymous-pipeline"` literal.

### WR-04: `_extract_target_torso_px` uses 2D distance silently — divergence from algorithm's 3D semantics

**File:** `backend/functions/pipeline/app.py:495-519` and `backend/scripts/extract_reference_body_profiles.py:112-133`
**Issue:** Both helpers compute torso pixel distance from x/y only:
```python
dx = mh_x - ms_x
dy = mh_y - ms_y
d = (dx * dx + dy * dy) ** 0.5
```
Yet the rest of the kinematic tree (`normalize_pose_by_segments`, `_compute_temporal_variance_per_segment`, `_compute_spatial_dispersion`) operate in 3D (`(x, y, z)`). The mid-shoulder/mid-hip distance picked as the **scale anchor** for L_ref is therefore the **projected 2D distance**, not the 3D bone length the rest of the algorithm uses. For a person leaning toward or away from the camera (very common in pole sports — backbends, leans), the 2D torso pixel can be 20-40% smaller than the 3D torso, scaling every reprojected segment proportionally and inflating spurious deficits.

There's a quiet acknowledgement in `body_normalizer.py:514` (`pixel_d = math.sqrt(dx * dx + dy * dy)  # 2D image plane`) for foreshortening detection, but the anchor itself should be the 3D distance for self-consistency with the segment-ratio math.

**Fix:** Use 3D Euclidean distance for the anchor in both `_extract_target_torso_px` and `_frame_torso_px` (extract script):
```python
dx = mh_x - ms_x
dy = mh_y - ms_y
dz = mh_z - ms_z
d = (dx * dx + dy * dy + dz * dz) ** 0.5
```
Keep the 2D variant only inside `is_foreshortening_detected` where projection is the point.

### WR-05: `_ref_segment_ratio` raises `KeyError` for unmapped edges instead of returning a neutral ratio

**File:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py:346`
**Issue:** The 13 edges in `KINEMATIC_TREE_EDGES` are covered by the chained `if` blocks, but any future edge addition (e.g. neck → nose, hand-grip extensions) will hit the `raise KeyError(...)` line. Inside `normalize_pose_by_segments`, this raises straight up the call stack and is caught by the pipeline's broad `except Exception` → `server_error`. That's a fail-closed posture for an internal invariant, but the edge list is in the same module — any contributor adding an edge has to remember to update `_ref_segment_ratio` or the entire pipeline fails for every user. There's no automated cross-check between the two constants.

**Fix:** Either:
1. Add a module-load-time assertion (`assert {edge in KINEMATIC_TREE_EDGES} ⊆ {known mappings}`) so the import itself fails fast if a contributor adds an edge without ratio mapping, or
2. Return a neutral `1.0` (or `0.25` for width edges) with a `log.warning` for unknown edges instead of crashing the analysis.

Option 1 is preferable — it forces the bug into developer time, not user time.

### WR-06: `_dataclass_to_camel_case_dict` Enum branch is unreachable for `BodyComparisonReport`

**File:** `backend/functions/pipeline/app.py:535-555` and `backend/tests/phase06/test_dataclass_to_camel_case_dict.py:112-122`
**Issue:** The function's order of operations is:
1. `dataclasses.is_dataclass(obj)` → `dataclasses.asdict(obj)` → recurse on dict.
2. `isinstance(obj, Enum)` → `str(obj.value)`.

`dataclasses.asdict` deep-copies the dataclass and recursively converts nested dataclasses/dicts/lists. It does NOT special-case `Enum`; an `Enum`-typed field becomes the Enum **instance** inside the resulting dict. But after `asdict`, the **next call into `_dataclass_to_camel_case_dict`** with the inner dict goes through the `isinstance(obj, dict)` branch — and **inside that dict comprehension**, each value is passed through `_dataclass_to_camel_case_dict(v)`, so an Enum inside a dataclass *would* hit the Enum branch then. OK, the Enum branch is technically reachable for nested Enum values.

However, `BodyComparisonReport` does NOT contain any Enum fields — `comparison_type` is a `Literal["mode1", ...]` (a plain `str`), and `deficit_code` in findings is a `str`. The unit test `test_dataclass_to_camel_case_dict_serializes_enum_literal` (line 112) tests a synthetic `_Color` enum, not the actual production type. So the Enum branch is dead code for the actual production payload. Not a bug — just a maintenance trap: future contributors might assume `comparison_type` will be coerced via the Enum branch and switch it to an `Enum`, only to discover `dataclasses.asdict` returns the Enum instance and Firestore SDK can't serialize it.

**Fix:** Add a unit test that proves `_dataclass_to_camel_case_dict(BodyComparisonReport(...))` produces a plain `str` for `comparisonType` and `deficitCode`, locking the contract. Or, better, add a positive Enum integration test (`BodyComparisonReport` with an Enum field) so the Enum path is exercised by code that actually flows through `complete_analysis`.

### WR-07: Pipeline overwrites `recognizer.motion_query_hint` without restoring it — leaks across analyses

**File:** `backend/functions/pipeline/app.py:654-656`
**Issue:**
```python
ref_motion_id = meta.get("referenceMotionId")
if mode == models.MODE_EXPERT and ref_motion_id and hasattr(recognizer, "motion_query_hint"):
    recognizer.motion_query_hint = str(ref_motion_id)
```
The `_RECOGNIZER` singleton survives across SQS messages (and across `BackgroundTask` invocations on RunPod). Setting `motion_query_hint` is a module-global mutation that is never reset. Sequence:
1. Mode 1 analysis A sets `motion_query_hint = "ref-foxtop"`.
2. Mode 3 (self) analysis B starts immediately after. The `if` guard fails (mode is `MODE_SELF`), so the hint is **not** reset. The Gemini extractor is queried with `motion_query = "ref-foxtop"` even though analysis B is the student's own video — Gemini will be biased toward labeling whatever motion they did as `foxtop`.

This is a stateful adapter sharing module-global state across requests, which the `_RECOGNIZER_LOCK`/double-checked locking pattern was meant to avoid. The HIGH-1 v4 fix for `_POSE_ESTIMATOR` ("사이드카 mutable instance attribute pattern 영구 폐기", `_RTMWNlfCompat.estimate_with_profile` docstring) already identified this anti-pattern but it crept back in via the recognizer.

**Fix:** Reset the hint before each analysis, or pass it as an argument to `recognize`:
```python
if hasattr(recognizer, "motion_query_hint"):
    recognizer.motion_query_hint = (
        str(ref_motion_id) if mode == models.MODE_EXPERT and ref_motion_id else None
    )
```
Better: extend the `TechniqueRecognizer` Protocol to accept a `motion_hint: str | None = None` kwarg in `recognize()` and route it locally, eliminating the mutable singleton attribute entirely.

## Info

### IN-01: `_g("values", "values")` — degenerate alias lookup

**File:** `backend/functions/pipeline/app.py:460`
**Issue:** `_g("values", "values")` passes the same key twice. The intent (camelCase/snake_case alias) is identical for `values` (the TS and Python field names match), but the call obscures the helper's purpose. A grep for `jointKeys` finds the alias logic; a grep for `values` does not.
**Fix:** Just call `raw.get("values")` directly, with a comment "no alias — TS/Python names match", to avoid future confusion.

### IN-02: Korean term "박제" used outside the technical-term context

**File:** `backend/functions/pipeline/app.py` (multiple lines: 145, 146, 147, 156, 159, 162, 169, 173, 179, 180, 183, 184, 188, 191, 218, 231, 251, 256, 290, 293, 365, 369, 471, 486, 522, 526, 535, 615, 654, 736, 765, 811, 830, 867, 868, 870, 876, 895, 905), `backend/shared/python/sunity_shared/analysis/body_normalizer.py:208`, `backend/shared/python/sunity_shared/firestore_admin.py` (multiple)
**Issue:** Per the user's memory note `no-baekje-filler` ("박제 는 전용어, 응답당 최대 2~3회. 일반 동사 대용 금지"), "박제" is a reserved domain term meaning "embedding/pinning a design decision" — not a generic verb. The Phase 6 comments use "박제" as filler — "박제 정신", "박제 정합", "박제 보존", "박제 검증" — in dozens of places where the intended meaning is "정합" / "보존" / "유지" / "결정사항". This violates a stated project convention.
**Fix:** Replace generic uses of "박제" with the actual concept: "정합" (consistency), "유지" (preservation), "결정" (decision), "고정" (locking). Limit "박제" to its true meaning ("이 결정은 박제됐다" = "this decision is now pinned/canonical").

### IN-03: `_compute_temporal_variance_per_segment` uses an `len(lengths)` divisor instead of `len-1` for variance

**File:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py:571`
**Issue:** Population variance (`/ n`) is used:
```python
var = sum((x - mean_L) ** 2 for x in lengths) / len(lengths)
```
For a temporal sample (N=30ish frames), Bessel's correction (`/ (n-1)`) would be the conventional choice. The difference is small for N=30 (`30/29 ≈ 1.034`) but for short clips (N=10) it's ~11%. The penalty thresholds (`0.05` excellent, `0.10` high) were calibrated against `_factory.gen_fixture_unstable_arm_swing` which uses N=30, so either convention works in the test but production users filming 5-second clips at 9 fps (45 frames) will be just at the edge.
**Fix:** Either document the choice (`# population variance — matches the calibration set in _factory`) or switch to sample variance and re-calibrate. No functional bug today; flagged so it doesn't become one when shorter clips ship.

### IN-04: `_extract_target_torso_px` returns `None` for any frame that lacks one of four endpoints — too brittle

**File:** `backend/functions/pipeline/app.py:495-519`
**Issue:** The `if not all(n in kp for n in needed):` short-circuit skips an entire frame the moment one of the four needed keypoints is missing from `keypoints_3d`. RTMW outputs always include all 17 COCO keypoints (with low confidence values for occluded ones), so this rarely triggers — but the helper also skips frames where the distance computes to `<=0`, which can happen for fully-curled-up poses near the centroid. If most frames are skipped, the helper returns `None`, triggering WR-02's silent fallback.
**Fix:** Consider falling back to a confidence-weighted distance computed over all frames where at least one shoulder and one hip are present, rather than requiring all four.

### IN-05: Tests duplicate `_ref_profile_dict` / `_ref_source_pose_dict` across 4 files with snake_case keys

**File:** `backend/tests/phase06/test_pipeline_body_comparison.py:109-145`, `backend/tests/phase06/test_pipeline_firestore_integration.py:54-78`, `backend/tests/phase06/test_phase06_integration_smoke.py:70-94`, `backend/tests/test_pipeline_recognizer_switch.py`
**Issue:** Four nearly-identical helpers build reference docs with snake_case keys — and all four are wrong relative to production (see CR-01). Duplication makes the bug "look correct" in 4 places at once. Consolidate into a single fixture helper.
**Fix:** Move the helper into `backend/tests/phase06/fixtures/_factory.py` and shape it to match what `update_reference_body_data` actually writes (camelCase). That single source of truth will surface CR-01 immediately when tests are re-run.

## Structural Findings (fallow)

No `<structural_findings>` block was provided with this review request; cross-module structural pre-pass was not run for this review.

---

_Reviewed: 2026-06-08T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
