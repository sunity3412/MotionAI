# Phase 23: Mode 1 결함 recall 복구 — still-frame veto + 기준선 정량화 - Pattern Map

**Mapped:** 2026-06-22
**Files analyzed:** 7 modified (no greenfield files — this phase mutates existing analysis modules)
**Analogs found:** 7 / 7 (every changed file IS its own best analog — modify-in-place)

> **Read-first note for planner/executor:** This phase is NOT greenfield. Every "new"
> behavior attaches to an *existing* function. The closest analog for each modified
> file is almost always a sibling function in the SAME file (the established convention
> is the pattern to copy). Do not introduce new modules where an existing adapter/core
> boundary already holds the seam. The decisive design fact: the veto adapter boundary
> was *built for this swap* — `VisionVetoCache.build_key` already carries
> `input_granularity`, and `_aggregate_comparison_verdict` already does N-sample +
> per-part union. The work is swapping the INPUT (whole-video → still pair) behind that
> boundary, not rebuilding it.

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `analysis/gemini_vision_scorer.py` | adapter (Gemini boundary) | request-response (VLM) | self — `_upload_video`/`_call_gemini_comparison`/`_aggregate_comparison_verdict` | exact (in-file) |
| `analysis/vision_veto.py` | core (pure, numpy-only) | transform | self — `worst_pose_timestamp`/`fault_joints_from_differences`/`apply_downward_cap` | exact (in-file) |
| `functions/pipeline/app.py` (`_apply_vision_veto`) | orchestration (SQS consumer) | event-driven → request-response | self — existing `_apply_vision_veto` + `_attach_fault_zoom_comparisons` wiring | exact (in-file) |
| `analysis/motiondtw.py` | core (pure, numpy-only) | transform | self — `MotionMatch`/`per_joint_deviation`/`dtw` | exact (in-file) |
| `analysis/fault_zoom.py` | core/util (PIL crop) | file-I/O (image bytes) | self — `_matched_ref_frame`/`build_fault_zoom_comparisons` | exact (in-file) |
| `analysis/features.py` + `dimensions.py` | core (pure scoring math) | transform | self — `compute_joint_angles`/`JOINT_ANGLES` | exact (in-file) |
| `analysis/skeleton.py` | core (constants/topology) | n/a (lookup tables) | self — `JOINT_TO_PART`/`JOINT_ANGLES` | exact (in-file) |

---

## Pattern Assignments

### `analysis/gemini_vision_scorer.py` (adapter, request-response)

**Analog:** self — the existing comparison path. The whole-video → still swap happens here.

**The swap point — `_upload_video` (lines 505-533).** This is the ONLY place that
turns a local path into a Gemini handle. D-01 (still-frame pair) replaces the video
file with one (or N) still image(s). Same `client.files.upload` API, same ACTIVE-wait,
same ASCII-safe-path + temp-file cleanup, same File-API delete in caller's `finally`.
Copy this function's structure for an image-upload sibling (e.g. `_upload_image`); keep
the same TimeoutError / `_state_name` / `os.unlink(tmp)` discipline:
```python
uploaded = client.files.upload(
    file=upload_path,
    config=genai_types.UploadFileConfig(mime_type=_mime(local_video_path)),
)
# ... PROCESSING poll loop, ACTIVE check, tmp cleanup ...
```
The `_mime()` helper (478-484) must gain image branches (png/jpeg). The 48h-TTL +
20GB-storage leak is real (see header comment line 641-652) — every uploaded handle
MUST be deleted in `finally`; still-images are cheaper but the discipline is identical.

**The contents-ordering analog — `_call_gemini_comparison` (lines 799-828).** This is
the reference-anchored two-input call. For D-01 the still path keeps the SAME ordering
contract `[기준 라벨, 기준 핸들, 학생 라벨, 학생 핸들, 프롬프트]`, swapping video
handles for image handles. Keep `temperature=0.0`, `response_schema=build_schema()`,
`thinking_config`, 180s timeout identical (objectivity + determinism parity, D-06):
```python
contents=[
    "기준(정타) 영상:", ref_uploaded,
    "평가 대상(학생) 영상:", student_uploaded,
    _build_comparison_prompt(at_seconds),
],
```

**N-sample + per-part union (D-05) — `_aggregate_comparison_verdict` (676-727) +
`_union_differences` (733-762).** This already exists and already does exactly what
D-05 asks: N calls (`VISION_VETO_SAMPLES`, default 3) → rank-median severity →
`_union_differences` keeps the highest-severity/deviation item per `body_part` so no
sample's caught fault (e.g. 왼팔) is lost. For the still path the work is: extend the
per-call loop to also iterate the per-PART prompts × selected key-frames, then feed all
parsed verdicts into the SAME `_union_differences` aggregation. Do NOT write a second
aggregator — extend the sample set fed into this one. Severity stays median (정타 100
보존), union only widens `differences`.

**Cache key already swap-ready (D-06) — `VisionVetoCache.build_key` (340-376).** The key
ALREADY includes `input_granularity` (currently the module constant
`INPUT_GRANULARITY = "whole"`, line 88). For the still path, pass a distinct granularity
token (e.g. `"frame"` / `"frame_pair"`) so still-input verdicts never collide with
whole-video verdicts. The key also folds in `PROMPT_VERSION`/`SCHEMA_VERSION`/`n{samples}`
via `globals()` — so **bump `PROMPT_VERSION` (line 70) and/or `SCHEMA_VERSION` (line 71)
whenever the still prompt or schema changes** (the header comment mandates this; stale
verdicts auto-invalidate). `reference_hash` is already in the key for PAIR keying.

**no-score schema — `build_schema` (131-196) + `VisionVerdict` (109-125).** Objectivity
hard gate (D-06): `VisionVerdict` has NO score field, `build_schema` has NO
score/overall/rating field. The new **quantification fields** (D-02: angle direct +
body-relative 칸/층 text) must attach as DESCRIPTIVE strings/numbers only. The schema
already has the right shape to extend: `approx_angle_deviation_deg` (number),
`extension_gaps[].approx_gap_deg`, plus free-text `correct_state`/`fault_state`/`ipsf_note`.
Add quantification as more observational fields (e.g. a body-relative `notches` text
field) — never as a normalized score. The `_SCORE_PATTERN` leak guard (line 97, checked
at 655 + per-sample at 696) will discard any verdict that leaks "NN점/NN%/NN/100".

**Top-level orchestration to mirror — `assess_fault_severity` (546-667).** The 7-step
flow (client → hash/key → cache lookup → upload+call → score-leak guard → parse → store)
is the template. The still path threads through steps (4)-(5) with image handles instead
of one video handle; everything else (graceful `None` on key absence / API failure,
cache hit short-circuit) is unchanged.

---

### `analysis/vision_veto.py` (core, transform)

**Analog:** self — pure numpy/stdlib functions, zero heavy deps (module header line 3
forbids boto3/Gemini/network imports). Any new helper added here MUST stay pure.

**worst-pose / key-frame selection — `worst_pose_timestamp` (241-278).** Returns the
dominant-fault timestamp (seconds) from `profile.key_moments` (hold > peak > all,
earliest). D-03/Claude's-discretion key-frame selection (±window, top-K) should extend
this pattern: a new pure function that returns a *list* of candidate seconds (or
frame indices) from the same `key_moments` source. Keep the explicit `is not None`
check (line 272-273) — `or` wrongly drops `timestamp 0.0` (video-start hold). Keep
"신규 Gemini moment 호출 0" — read profile only.

**part mapping seed (D-05) — `_PART_KEYWORDS` (142-156) + `_keypoints_for_part` (170-201)
+ `fault_joints_from_differences` (204-215).** The Korean-free-text → keypoint mapping
already covers 어깨/팔꿈치/손/무릎/엉덩이/라인/상체. D-05 adds per-part PROMPTS (머리/목,
그립); the mapping table here is where new body-part keywords (머리/목/그립) attach. Note
the highlight set is currently 8 keypoints (`_HIGHLIGHT_KEYPOINTS`, 133-138); 머리/그립
have no skeleton keypoint, so map to nearest (the `ankle → knee` precedent at line 153
shows the "미표시 keypoint → 최근접" convention).

**hard-cap invariant — `apply_downward_cap` (104-118).** Do NOT touch the cap math.
`SEVERITY_CAP` (65-70) is spec-anchored (major=50/moderate=75/minor=90/none=None), and
`SEVERITY_CAP_PROVENANCE` (89-101) data-pins the rationale with
`phase18_pairs_used_for_derivation=False` (permanent INVARIANT). The still-frame swap
changes the INPUT to the verdict, never the cap. Vision is down-only (min cap), 정타 =
no cap = 100 preserved.

---

### `functions/pipeline/app.py` :: `_apply_vision_veto` (orchestration, event-driven)

**Analog:** self — the existing veto wiring (1662-1767) is the single integration seam
(per CONTEXT integration points: "`_apply_vision_veto` = 입력 swap의 단일 지점").

**The call into the adapter (1715-1720)** is what changes for D-01/D-03:
```python
at = vision_veto.worst_pose_timestamp(profile)
verdict = gemini_vision_scorer.assess_fault_severity(
    local_video_path,
    at_seconds=at,
    reference_video_path=reference_video_path,
)
```
Today it passes full video paths + a single `at_seconds`. The still path needs the
student worst-pose frame + DTW-matched reference frame (D-01). The reference is already
downloaded locally for Mode1 (see wiring `reference_local_video_path`, app.py 2462-2480)
and the DTW match (`reference_dtw_match`, set at line 2414) is already in scope. The
existing `status` enum (1684-1692: disabled / mode3_held / missing_local_video /
missing_reference / skipped_error / not_applicable / applied) is the audit pattern to
extend — D-03's "veto 보류 + 비교 신뢰도 낮음" should add a NEW status enum value (e.g.
`low_alignment_confidence`) rather than fabricating a fault. Follow `_veto_passthrough`
(1651-1659) for any new non-applied status (score unchanged + explicit
`visionVeto.status`).

**Down-only mutation + audit (1727-1760)** is the template for any new quantification
field on the applied path: `verdict.primary_fault`, `faultJoints`, `faultJointDeficits`
are already attached as descriptive (non-score) audit. D-02 quantification text/angle
fields attach the SAME way (descriptive only, no score). Keep the terminal
`min`-cap-only contract (1728-1729).

**DTW-match plumbing already exists.** `reference_dtw_match = match` (2414) flows to
`_attach_fault_zoom_comparisons(..., dtw_match=reference_dtw_match)` (2931). For D-01,
the same `match` (a `MotionMatch`) is the source of the matched-reference-frame for the
still pair — reuse `fault_zoom._matched_ref_frame(match, user_frame, ref_n)` (see below),
do NOT recompute DTW.

---

### `analysis/motiondtw.py` (core, transform)

**Analog:** self — `MotionMatch` (72-77) + `dtw` (26-69).

**Alignment-confidence signal (D-03) — `MotionMatch.distance` (line 76).** Already
computed as the normalized DTW distance (smaller = more similar). D-03 gating adds ONLY
a threshold check on this existing field — no new DTW computation. The normalization
(`D[n,m] / (n+m)`, line 69) makes it length-invariant and comparable across videos. The
gating lives in the pipeline (`_apply_vision_veto`), not here — keep this module pure.

**Path semantics for frame matching — `dtw` returns `path[(user_idx, ref_idx)...]`
(local indices)** consumed by `per_joint_deviation` (103-130, median to absorb RTMW
jitter). `fault_zoom._matched_ref_frame` already reads `match.start` + `match.path` to
map a student frame to the same-pose reference frame — that is the existing key-frame
correspondence for D-01.

---

### `analysis/fault_zoom.py` (core/util, file-I/O)

**Analog:** self — `_matched_ref_frame` (44-62) + `build_fault_zoom_comparisons` (133-215).

**Same-pose frame pair (D-01 reuse) — `_matched_ref_frame` (44-62).** Already computes
the student↔정은지 same-pose reference frame from the DTW match (median ref_idx for
1:N DTW correspondence, line 59-62). This is exactly the matched-reference-frame the
still-frame veto needs. The still path should reuse this function (or its logic) to pick
the reference frame that pairs with the student worst-pose frame — do not write a second
matcher.

**Visual 칸/층 overlay attach point (D-02, deferred to v1.1) —
`build_fault_zoom_comparisons` (133-215) + `_mark` (107-119).** `_mark` already draws a
brand-color marker + a numeric `deg` badge on the crop (PIL default font = digits/ASCII
only; Korean caption is the app's job — line 9 comment). The arrow + 칸/층 visual overlay
(D-02 v1.1) layers ON TOP of these crops here. v1 (this phase) is text+angle only, so
this file may be untouched in v1 — but it is the documented site for the v1.1 overlay.
The composed PNG → S3 upload → `imageUrl` round-trip lives in pipeline
`_attach_fault_zoom_comparisons` (app.py ~1832-1859).

---

### `analysis/features.py` + `analysis/dimensions.py` (core, transform)

**Analog:** self — `compute_joint_angles` (features.py 36-55) + `JOINT_ANGLES`
(skeleton.py 39-48, consumed here).

**Scale-invariant angle source (D-02 angle-direct) — `compute_joint_angles` (36-55).**
Produces `(T, NUM_JOINTS)` joint angles in degrees from 3D keypoints — already
scale-invariant (3D, not pixel distance), already computed and stored in
`keypointReport`. D-02's "무릎 145° vs 정은지 178°, 33° 더 굽음" comes directly from
per-joint angle deltas (student vs DTW-matched reference frame). The 8 angles in
`JOINT_ANGLES` (left/right × elbow/shoulder/hip/knee) are the available set. Reuse
`dimensions.line_deficits_by_joint` (320) / the `_select_window` + median pattern for
the per-joint delta numbers; do NOT compute cm/m absolute distances (D-02 forbids —
single-camera scale ambiguity).

**Body-relative distance (D-02 칸/층 text)** is NOT angle-based — it needs the
`body_normalization` profile (arm/leg/torso/height ratios) to express "정은지 3칸, 너
2칸 ⅔" as a ratio (정은지 reach = 100% = N칸, student as a fraction). The profiles are
already measured/stored/wired for both student and reference (see `body_normalization.py`
+ `body_normalization_measurer.py`; Mode1 fetch at app.py 2362-2408 via
`compare_body_profiles`). Attach the 칸/층 text as a descriptive field on the comparison
report — never a score.

---

### `analysis/skeleton.py` (core, constants)

**Analog:** self — `JOINT_TO_PART` (70-79) + `JOINT_ANGLES` (39-48).

**Part-split seed (D-05) — `JOINT_TO_PART` (70-79).** Maps the 8 joints to 상체/코어/하체
(PART_UPPER/CORE/LOWER, 65-68). D-05 per-part prompts (상체/하체/라인 + 머리/그립) use
this as the partition seed. Note 머리/그립 are NOT in the 17-keypoint skeleton's angle
joints — extending parts beyond the 8 angle joints means the new parts map to vision-only
detection (Gemini sees them in the still) and to nearest keypoints for overlay (the
`ankle → knee` precedent in `vision_veto._PART_KEYWORDS`). Keep `JOINT_KEYS` order stable
(line 50 comment: "항상 이 순서를 사용") — many `(T, J)` consumers depend on it.

---

## Shared Patterns

### Adapter boundary + lazy heavy-import (apply to: gemini_vision_scorer.py)
**Source:** `gemini_vision_scorer.py` module header (51-53) + `_ensure_client` (456-475).
`google.genai` is imported ONLY inside functions (never top-level). The analysis core
stays import-light. New still-path code keeps `from google.genai import types` lazy and
inside the call function. Key/SDK failure → `RuntimeError` → caller converts to graceful
`None` (Pitfall 5). Module-cached singleton client (`_CLIENT`, line 103).

### Objectivity hard gate — no score field, ever (apply to: ALL files)
**Source:** `gemini_vision_scorer.VisionVerdict` (109-125) + `build_schema` (131-196) +
`_SCORE_PATTERN` (97). D-06 + [[analysis-objectivity-no-human-scores]]. Every new
quantification field (angle delta, 칸/층 text, root-cause hypothesis) is DESCRIPTIVE
(string/observational number), never a normalized 0-100 score and never a human/AI score
label. The leak guard (line 655 + 696) discards verdicts that emit "NN점/NN%/NN/100".

### Determinism via cache, not temp alone (apply to: gemini_vision_scorer.py)
**Source:** module header (20-32) + `VisionVetoCache` (318-433). `temperature=0.0` plus
the explicit cache (keyed on prompt/schema/granularity/n-samples versions) gives
"same input = same verdict". Still path: pass a new `input_granularity`, and bump
`PROMPT_VERSION`/`SCHEMA_VERSION` when prompt/schema change (auto stale-invalidation).

### Graceful degradation — feature never blocks analysis (apply to: pipeline, fault_zoom, gemini_vision_scorer)
**Source:** `_apply_vision_veto` try/except (1763-1767) + `_attach_fault_zoom_comparisons`
caller try (app.py 2920-2938) + `build_fault_zoom_comparisons` per-item skip (204-205).
Every veto/zoom/quantification failure is logged + swallowed; the v1 score path always
survives. Use `# noqa: BLE001` with a Korean reason at boundaries (project convention).

### Down-only veto — terminal min cap (apply to: pipeline, vision_veto)
**Source:** `vision_veto.apply_downward_cap` (104-118) + `_apply_vision_veto` (1728-1729).
Vision can only LOWER the score (min cap), never raise it. This is the structural fix for
the kip-up 100/100 위양성. The still swap changes recall (what faults are SEEN), not the
cap math. D-03 low-confidence → 보류 (no cap, explicit status), never a fabricated cap.

### Korean comments cite the spec; identifiers stay English (apply to: ALL files)
**Source:** every module header. New code cites `23-CONTEXT` decisions by id (D-01..D-06)
and memory박제 ([[...]]) the same way existing comments cite `Phase 20`, `belle 2026-06-22`,
`MEDIUM-1`. No emojis (CLAUDE.md §7).

---

## No Analog Found

None. Every file in scope is a modification of an existing module whose sibling functions
already establish the exact pattern to follow. There is no greenfield file in this phase.

The two genuinely NEW behaviors — (a) per-part prompt × key-frame fan-out feeding the
existing union aggregator, and (b) DTW-confidence gating with a new `visionVeto.status`
value — both attach to existing seams (`_aggregate_comparison_verdict` /
`_apply_vision_veto` status enum). They are extensions, not new modules.

## Metadata

**Analog search scope:** `backend/shared/python/sunity_shared/analysis/`,
`backend/functions/pipeline/app.py`, `backend/runpod_inference/server.py` (entry only).
**Files scanned:** gemini_vision_scorer.py, vision_veto.py, motiondtw.py, fault_zoom.py,
features.py, dimensions.py, skeleton.py, pipeline/app.py (targeted ranges).
**Pattern extraction date:** 2026-06-22
