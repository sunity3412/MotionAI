# Phase 14: reference-motion-registration - Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 6 (5 new/modified code/doc + contract trio)
**Analogs found:** 6 / 6 (all exact or strong role-match; analogs pre-named in 14-RESEARCH.md and verified file:line)

> All file access for this mapping was read-only. The only file written is this PATTERNS.md.
> D-01 mandates 동일 코드 1벌: the backfill MUST call the SAME `sunity_shared.analysis`
> functions `_process` calls. Any hand-rolled equivalent breaks the false-positive guarantee.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/scripts/backfill_reference_downstream.py` (new — backfill orchestrator, Pod-run) | script (admin CLI) | batch / transform (S3→RTMW→compute→JSON) | `backend/scripts/extract_reference_body_profiles.py` + `backend/scripts/backfill_body_data_new6.py` | exact |
| `app/scripts/seed-reference-downstream.mjs` (new OR extend existing seeder) | script (Node admin seed) | batch / file-I/O → Firestore merge | `app/scripts/seed-reference-body-profile.mjs` | exact |
| `backend/shared/python/sunity_shared/firestore_admin.py` (modify — new merge helper OR extend `update_reference_body_data`) | service (Firestore writer) | CRUD (atomic merge, ADD-only) | `firestore_admin.update_reference_body_data` (:850) | exact |
| `backend/tests/test_reference_backfill.py` (new) | test | unit (fixture pose_frames → assert == student-path) | `backend/tests/test_pipeline_body_profile_injection.py` | role-match |
| `docs/contract.md` §3 + `app/src/types/analysis.ts` `ReferenceMotion` (modify — 3-way lockstep) | config (data contract) | request-response (GET /reference passthrough) | existing `ReferenceMotion` block (contract:105, types:398) | exact |
| `docs/<capture-guide>.md` (new — SC#3 촬영 가이드) | doc | n/a | no code analog (markdown deliverable) | n/a |

**Compute reuse (NOT a new file — call these in-place, the spine of D-01):**
`backend/functions/pipeline/app.py::_extract_video_analysis_inputs` (:1135) and `_process` downstream
order (:1610 EXTEND, :1899 force_signals, :1932 force_pattern). The backfill replicates this exact
call order against reference S3 video, never re-implements it.

## Pattern Assignments

### `backend/scripts/backfill_reference_downstream.py` (script, batch/transform — Pod-run)

**Primary analog:** `backend/scripts/extract_reference_body_profiles.py`
**Secondary analog (per-motion loop + `update_reference_body_data` write):** `backend/scripts/backfill_body_data_new6.py`

**RESEARCH verdict to encode (14-RESEARCH.md §D-02):** meanAngles + EXTEND are STORED-SUFFICIENT
but compute them here anyway for consistency; BodyNormalizationProfile + ForceDirectionPattern are
HYBRID-NEEDED → require live `pose_frames` from a single RTMW re-inference per motion. One RTMW run
per motion produces ALL four outputs (no double inference).

**sys.path injection + lazy heavy-import pattern** (`extract_reference_body_profiles.py:38-48`):
```python
# W3 — sys.path 주입 (in-script, `-m` 미사용).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))
# 헤비 의존 (imageio / rtmlib / boto3) 는 main() 안에서 lazy import — `--help`
# 가 Mac 로컬 환경에서도 exit 0 가능 (의존성 부재 시 fail-fast 는 측정 실행 시).
```

**Motion-ID set — default-5 trap (Pitfall 1, [[reference-library-phase4-all11]]):** the existing
`DEFAULT_MOTION_IDS` is the original 5 (`extract_*:59-65`) and new6 is a separate list
(`backfill_body_data_new6.py:54-61`). Phase 14 covers ALL 11. Define the full 11-id constant and/or
require `--motions` explicitly; never run with a default that is a subset.
```python
# extract_reference_body_profiles.py:59-65 — DEFAULT is only 5 (the trap)
DEFAULT_MOTION_IDS: tuple[str, ...] = (
    "ref-climb", "ref-foxtop", "ref-foxtop-split", "ref-invert", "ref-sideway-spin",
)
# backfill_body_data_new6.py:54-61 — the other 6
NEW6_MOTION_IDS = [
    "ref-kip-up", "ref-peter-pan", "ref-power-spin",
    "ref-elbow-twist-sister", "ref-pdshape", "ref-combo",
]
# Phase 14: union of both = 11. Pass --motions for all 11 (or default to the 11-union).
```

**S3 download + RTMW estimate per motion** (`extract_reference_body_profiles.py:209-237`,
`backfill_body_data_new6.py:72-77,187-189`):
```python
def _download_video(s3_client, bucket: str, motion_id: str, target: Path) -> None:
    key = f"reference/{motion_id}.mp4"
    s3_client.download_file(bucket, key, str(target))

# vertical-fallback pole axis — reference 영상은 폴 거의 수직 (PoleDetector 비용 회피)
default_pole = PoleAxis(axis_vector=(0.0, 1.0, 0.0), confidence_level="low",
                        source="vertical_fallback", frame_index=None)
frames = extractor.extract(str(video_path))
pose_frames = rtmw_engine.estimate(frames, default_pole)   # live PoseFrame list (HYBRID input)
if not pose_frames:
    raise RuntimeError(f"pose_frames empty for {motion_id}")
```

**The four-output compute — MUST mirror `_process` call order** (synthesized from 14-RESEARCH.md
Code Examples; each fn is the exact one `_process` calls, cited inline):
```python
# angles — ONE temporal_fill only (double-smooth banned, Pitfall 3 / REVIEWS R5).
#   mirrors _extract_video_analysis_inputs (pipeline/app.py:1174-1176)
kp = to_coco17_array(pose_frames)
angles = temporal_fill(compute_joint_angles(kp), joint_uncertainty(kp))

# 1) meanAngles (STORED-SUFFICIENT, app derives via deriveMeanAngles — compute here for parity)
mean_angles = {k: float(np.nanmean(angles, axis=0)[i]) for i, k in enumerate(skeleton.JOINT_KEYS)}

# 2) EXTEND profile (STORED-SUFFICIENT input: angles). Same fn pipeline/app.py:1610 calls.
profile = FallbackRecognizer().recognize(angles)        # joint_expectations
#   A1/Open-Q1: Fallback (angles-only) vs Gemini (needs S3 video). Planner: confirm recognizer.

# 3) BodyNormalizationProfile (HYBRID input: pose_frames). Same fn pipeline/app.py:1171 calls.
body_profile = measure_body_profile(pose_frames)

# 4) ForceDirectionPattern (HYBRID input: pose_frames). Same fns pipeline/app.py:1899,1932 call.
pole_meas = build_pole_axis_measurement(axis_3d=default_pole, line=None, frame_index=None)
fsr = fs.compute_force_signals(pose_frames, pole_meas, body_profile,
                               angles=angles, fps=9.0,
                               motion_id=getattr(profile, "motion_id", None),
                               technique_profile=None)
fpi = fp.infer_force_direction_pattern(fsr, motion_id=getattr(profile, "motion_id", None),
                                       mode_context="mode1")   # A4: reference = mode1 target
```

**camelCase dict conversion** — reuse `_dataclass_to_camel_case_dict` (pipeline) or the explicit
field maps in the analogs (`extract_*:_bp_to_camel_dict :68-79`, `backfill_body_data_new6.py:161-177`).
Do NOT hand-roll a new converter shape — match the stored format exactly.

**dry-run + JSON-fixture emit + per-motion graceful failure** (`extract_*:344-393`):
```python
# per-motion try/except so one bad motion does not abort the batch
for motion_id in motion_ids:
    try:
        _download_video(s3, bucket, motion_id, video_path)
        motions_out[motion_id] = _measure_one(...)
    except Exception:
        log.error("[%s] FAIL — %s", motion_id, traceback.format_exc())
# --dry-run: print JSON to stdout, no file. real-run: write JSON fixture for the .mjs seeder.
```

---

### `app/scripts/seed-reference-downstream.mjs` (script, file-I/O → Firestore merge)

**Analog:** `app/scripts/seed-reference-body-profile.mjs` (extend payload + required-field lists)

**Three-step structure — validate BEFORE Firebase init (R7 fix, ADC-safe dry-run)**
(`seed-reference-body-profile.mjs:135-181`):
```js
// Step 1 — parse + load + validate (Firebase 미접촉, ADC 의존 X).
const args = parseArgs(process.argv.slice(2));   // --profiles <path> [--dry-run] [--force]
const payload = loadProfilesPayload(args.profiles);   // validates required fields per motion
// Step 2 — dry-run early return BEFORE Firebase init (ADC 미설정 환경 안전).
if (args.dryRun) { console.log(JSON.stringify({dryRun:true, ...}, null, 2)); return; }
// Step 3 — real-run: Firebase Admin init (ADC) + batch.set(merge:true) + verify read.
const { applicationDefault, initializeApp } = await import('firebase-admin/app');
initializeApp({ credential: applicationDefault(), projectId: 'sunity-ai-coach' });
```

**Required-field validation + nested-array rejection** (`seed-reference-body-profile.mjs:61-119`).
Extend `REQUIRED_*_FIELDS` with the new payloads (meanAngles keys, techniqueProfile/EXTEND,
forceDirectionPattern). Keep the nested-array guard — Firestore flat-array rule
([[firestore-nested-array-flat]]):
```js
// values 안에 nested array 금지 (flat float/string list 보장)
for (let i = 0; i < sp.values.length; i++) {
  if (Array.isArray(sp.values[i])) {
    throw new Error(`[${motionId}] ...values[${i}] nested array 금지`);
  }
}
```

**Idempotent skip + ADD-only merge + verify read** (`seed-reference-body-profile.mjs:189-241`):
```js
// idempotent — --force 미설정 시 이미 박제된 doc skip
if (!args.force) {
  const snap = await ref.get();
  const existing = snap.exists ? snap.data() : null;
  if (existing && existing.<newField> !== undefined) { skipped++; continue; }
}
const docPayload = {
  meanAngles: data.meanAngles,
  techniqueProfile: data.techniqueProfile,
  bodyNormalizationProfile: data.bodyNormalizationProfile,
  forceDirectionPattern: data.forceDirectionPattern,
  // ...UpdatedAt: Date.now() per field (Phase 6 convention, lines 209,213)
};
batch.set(db.collection('reference').doc(motionId), docPayload, { merge: true });
// verify loop reads all docs back and prints which new fields are present (extend to 4 fields × 11)
```

> NOTE: `seed-reference-body-profile.mjs` already writes `bodyNormalizationProfile` (Phase 6). For
> the 6 later-added motions that may lack it (A2 / Open-Q2), this seeder (or the new one) must run
> for all 11. The `--force` flag overwrites; default is idempotent skip.

---

### `backend/shared/python/sunity_shared/firestore_admin.py` (service, CRUD — atomic merge)

**Analog:** `update_reference_body_data` (:850-926) — exact pattern to extend or clone.

**Validation → flat-array gate → `set(merge=True)` + structured log** (:873-926):
```python
def update_reference_body_data(motion_id, body_profile, source_pose=None) -> None:
    if not motion_id: raise ValueError("motion_id required")
    missing_bp = [k for k in _REF_BODY_PROFILE_REQUIRED if k not in body_profile]
    if missing_bp: raise ValueError(f"body_profile missing required fields: {missing_bp}")
    _validate_flat_dict_no_nested_array(body_profile, path="bodyNormalizationProfile")
    # ... source_pose None-aware validation, values length == 4 × len(jointKeys) ...
    now_ms = int(time.time() * 1000)
    payload = {"bodyNormalizationProfile": body_profile,
               "bodyNormalizationProfileUpdatedAt": now_ms}
    _doc(models.reference_motion_path(motion_id)).set(payload, merge=True)   # ADD-only merge
    log.info("update_reference_body_data ok motion_id=%s ...", motion_id, ...)
```

**Pattern for Phase 14:** add `_REF_*_REQUIRED` tuples for the new fields (meanAngles keys,
techniqueProfile, forceDirectionPattern) and either extend this fn or add a sibling
`update_reference_downstream_data`. ALWAYS `merge=True`, ADD-only, never touch
`joints3d`/`angles`/`activeVersion` (Pitfall 4 / D-02). Per-field `*UpdatedAt` epoch-ms timestamp.

> The backfill script may write directly via this helper (as `backfill_body_data_new6.py:207` does)
> OR emit a JSON fixture for the `.mjs` seeder (as `extract_*` does). RESEARCH recommends the
> JSON-fixture + `.mjs` path (proven dry-run/atomic/idempotent cycle) — planner's discretion.

---

### `backend/tests/test_reference_backfill.py` (test, unit)

**Analog:** `backend/tests/test_pipeline_body_profile_injection.py` (pipeline-module import + synthetic
PoseFrame fixtures + dataclass assertions).

**Pipeline-module import-by-path + reload isolation** (:30-44):
```python
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path: sys.path.insert(0, str(_PIPELINE))
def _import_pipeline():
    sys.modules.pop("app", None)
    import app
    return importlib.reload(app)
```

**Synthetic PoseFrame fixtures** (:50-60) — seed-derived `Keypoint3D`/`Keypoint3DAligned`/`PoseFrame`
so the measurer/force fns produce deterministic, distinct outputs without GPU.

**Tests to write (14-RESEARCH.md Validation map, Wave 0 gaps):**
- SC#2 compute parity: feed one fixture `pose_frames`/`angles` to the backfill helper AND to the
  `_process` downstream calls; assert identical dataclasses (proves D-01 동일 코드 1벌).
- SC#4 single-view graceful: vertical-fallback `line=None` → `compute_force_signals` contact metrics
  return None + `pole_line_missing` warning, no crash (force_signals.py:1443-1542 graceful path).
- D-02 verdict: assert `measure_body_profile`/`compute_force_signals` fail/NaN on
  reconstructed-from-flat data (proves HYBRID necessity); assert EXTEND/meanAngles match from
  `angles` alone (proves STORED-SUFFICIENT).

Run: `cd backend && python -m pytest tests/test_reference_backfill.py -x -q`.

---

### `docs/contract.md` §3 + `app/src/types/analysis.ts` `ReferenceMotion` (config, 3-way lockstep)

**Analog:** the existing `ReferenceMotion` block (contract.md:105-128, analysis.ts:398-447).

**Current state (verified):**
- `app/src/types/analysis.ts:398-447` ALREADY declares `meanAngles?`, `bodyNormalizationProfile?`,
  `bodyComparisonSourcePose?`. It does NOT declare `techniqueProfile`/EXTEND or `forceDirectionPattern`.
- `docs/contract.md:105-128` §3 table does NOT list `meanAngles`/`bodyNormalizationProfile`/
  `bodyComparisonSourcePose`/`techniqueProfile`/`forceDirectionPattern` at all.

**Action (Open-Q3, CLAUDE.md Cross-cutting lockstep):** add the new optional fields to BOTH the
contract §3 field table and the TS interface (and Python `models.py` if a typed mirror exists),
following the existing comment style that cites the phase/plan + memory:
```typescript
// Phase 6 (Plan 06-01, D-06-B2) — reference 측 BodyNormalizationProfile. ... nullable.
bodyNormalizationProfile?: BodyNormalizationProfile | null;
```
App `referenceMotions.ts normalize()` (:70+) ignores unknown fields gracefully, so Mode 1 list does
NOT break before the type update — but the lockstep rule still requires updating all sides together.

**Single-view confidence flag (SC#4 / D-03 / Open-Q4):** all 11 are single-view → add a lightweight
`captureViews: 1` (or `singleView: true`) flag and rely on existing `confidence` fields
(bodyNormalizationProfile.confidence + force report overall_confidence). Confirm field name in discuss.

---

### `docs/<capture-guide>.md` (doc, SC#3)

No code analog. Markdown deliverable documenting 촬영 조건/앵글/시점 수 for the 정은지 session
(D-03: 다각도 protocol reduced to doc-only; single-view is the computed baseline). Manual-review SC.

## Shared Patterns

### Versioned write / active-flip / rollback (use ONLY if a `versions/` write is chosen)
**Source:** `backend/scripts/reprocess_reference_motions_phase4.py` (`_write_versioned` :314-333,
`_flip_active_pointer` :339-404 with all-or-nothing `len(completed)==len(motion_ids)` gate + top-level
mirror) and `backend/scripts/rollback_reference_motions_phase4.py` (`--to-version pre_phase4`, mirror
restore :45-50).
**Apply to:** the backfill script IF planner chooses a versioned write. RESEARCH (A3) RECOMMENDS
top-level ADD-only merge instead (consumers read top-level directly; new fields are derived data, not
a pose re-version). If versioned: snapshot pre-backfill top-level into `versions/pre_phase14` for
rollback symmetry, and gate the active flip on all 11 complete.

### Firestore flat-array + 40k index-entry rule
**Source:** [[firestore-nested-array-flat]] / [[firestore-index-entry-limit]]; enforced by
`_validate_flat_dict_no_nested_array` (firestore_admin) and the `.mjs` nested-array guards.
**Apply to:** every new field. New fields are SMALL (meanAngles = 8 floats, EXTEND = 8 entries,
bodyNormalizationProfile = 7 fields, forceDirectionPattern = flat list[dict]) → no 40k risk. Do NOT
add any new per-frame (T-scaled) array to the reference doc (Pitfall 5).

### Pod ops / commit-before-Pod
**Source:** [[pod-ops-claude-runs]] / [[gsd-pod-work-push-first]] (CONTEXT 운영 환경).
**Apply to:** the backfill run. Claude runs the Pod backfill; belle approves any flip. Commit→push
before Pod work. Pod `qcf38vvsmub1y4` is UP, Lambda `RUNPOD_ANALYZE_URL` synced. Add a fail-fast
import check (rtmlib/imageio/boto3) at backfill start.

### Secret hygiene
**Source:** `reprocess_*` T-04-W5-01 (env values never logged). **Apply to:** Pod `AWS_*`/
`FIREBASE_SA_*` and Node ADC — log keys-not-values; SA key never printed.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `docs/<capture-guide>.md` | doc | n/a | Pure markdown deliverable (SC#3); no code analog — follow existing `docs/*.md` prose style |

## Metadata

**Analog search scope:** `backend/scripts/`, `backend/functions/pipeline/`,
`backend/shared/python/sunity_shared/`, `backend/tests/`, `app/scripts/`, `app/src/lib/`,
`app/src/types/`, `docs/`.
**Files scanned (read):** extract_reference_body_profiles.py, backfill_body_data_new6.py,
seed-reference-body-profile.mjs, reprocess_reference_motions_phase4.py (header + payload + flip),
rollback_reference_motions_phase4.py (header), firestore_admin.py (update_reference_body_data),
pipeline/app.py (_extract_video_analysis_inputs + _process downstream), referenceMotions.ts,
analysis.ts (ReferenceMotion), contract.md (§3), test_pipeline_body_profile_injection.py.
**Pattern extraction date:** 2026-06-15

## PATTERN MAPPING COMPLETE
