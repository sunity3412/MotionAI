---
phase: 14-reference-motion-registration
reviewed: 2026-06-15T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - backend/scripts/backfill_reference_downstream.py
  - app/scripts/seed-reference-downstream.mjs
  - app/scripts/snapshot-reference-phase14-state.mjs
  - app/scripts/rollback-reference-downstream.mjs
  - app/scripts/audit-reference-fields.mjs
  - backend/shared/python/sunity_shared/firestore_admin.py
  - app/src/lib/referenceMotions.ts
  - app/src/types/analysis.ts
  - backend/tests/test_reference_backfill.py
  - backend/tests/conftest.py
  - docs/contract.md
  - docs/reference-capture-guide.md
findings:
  critical: 2
  warning: 6
  info: 3
  total: 11
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-06-15
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 14 ships admin CLI tooling to backfill 4 downstream fields onto the 11 정은지
reference docs without touching active pose. The data-integrity invariants that
matter most — never writing `joints3d`/`angles`/`activeVersion`, the scoped
`forceDirectionPattern` validator vs generic nested-array rejection, the
keys-not-values logging discipline, and the robust mean/p99 angle gate — are all
present and largely well-built. The Python orchestrator and the
`firestore_admin.update_reference_downstream_data` merge helper correctly enforce
ADD-only payloads and route `forceDirectionPattern` through the existing
`_validate_force_pattern_inference` scoped validator.

The defects are concentrated in the **completeness/skip logic of the JS seeder and
the safety scripts**, which trust *presence* of a field rather than its *validity*.
Two of these are blockers because they cause silent data-integrity failures: a
corrupt-but-present field is reported "complete" and never repaired, and a
`--motions` subset can silently drop requested motions. The remaining items are
robustness/consistency warnings.

## Critical Issues

### CR-01: Seeder treats present-but-invalid existing fields as "complete" — corrupt data never repaired and silently skipped

**File:** `app/scripts/seed-reference-downstream.mjs:281-288, 391-398, 403`
**Issue:**
`hasAllRequired(existing)` (line 281) and the per-field repair test (line 403,
`existing[f] === undefined || existing[f] === null`) decide completeness purely on
*presence and non-null*, never on *validity*. The seeder rigorously validates the
**incoming fixture** (`validateSeedEntry` → `rejectNestedArray` /
`validateForceDirectionPattern`, lines 234-263) but applies **no validation to the
existing Firestore value**.

Consequences for the default repair-missing run:
- A reference whose `meanAngles` was previously written as an empty object `{}`,
  or whose `forceDirectionPattern` is a malformed/legacy shape, satisfies
  `existing[f] !== null` → `fieldMissing = false` → the field is **not** rewritten.
- If all 5 required keys are merely *present*, `hasAllRequired` returns true and the
  whole doc is `skipComplete` (line 394-398), so the corrupt field is never touched
  even though the operator ran the backfill expecting repair.

This directly undermines the phase's core promise (reference accuracy = trust). The
`--verify` path (line 361-377) has the same blind spot — it reports `complete=true`
on a present-but-empty field, giving false confidence that the library is healthy.

**Fix:** Reuse the same field-level validators that gate the fixture to gate the
*existing* value before deciding skip/repair. At minimum treat an empty
`meanAngles`/object, or a `forceDirectionPattern` that fails
`validateForceDirectionPattern`, as missing:

```js
function fieldValid(motionId, field, value) {
  if (value === undefined || value === null) return false;
  try {
    if (field === 'meanAngles') {
      return value && typeof value === 'object' && Object.keys(value).length > 0;
    }
    if (field === 'forceDirectionPattern') {
      validateForceDirectionPattern(motionId, value);
      return true;
    }
    if (field === 'captureViews') return typeof value === 'number';
    rejectNestedArray(motionId, field, value); // techniqueProfile / bodyNormalizationProfile
    return value && typeof value === 'object';
  } catch {
    return false; // present but malformed → treat as repairable
  }
}
// hasAllRequired + the line 403 fieldMissing test must use fieldValid(), not a null check.
```

### CR-02: `--motions` subset silently drops requested ids that are absent from the fixture

**File:** `app/scripts/seed-reference-downstream.mjs:316-318`
**Issue:**
```js
const targetIds = isSubsetRun
  ? args.motions.filter((m) => ids.includes(m))
  : ids;
```
When the operator runs `--motions ref-foo,ref-bar --repair-missing` and `ref-bar`
is not present in `seedPayload`, `ref-bar` is silently filtered out. No warning, no
non-zero exit. The final summary (`repairMissing=… skippedComplete=…`) counts only
the motions that *were* found, so an operator who asked to repair two motions and
sees `repairMissing=1` has no signal that one request was dropped. Given this is a
data-repair tool for an 11-doc production library, a silently-missed motion is a
data-integrity failure (operator believes a reference was fixed when it was not).

**Fix:** Fail closed when a requested id is missing from the fixture:

```js
const missing = args.motions.filter((m) => !ids.includes(m));
if (missing.length) {
  console.error(`[seed FAIL] --motions 요청 중 fixture 에 없는 id: ${missing.join(',')}`);
  process.exit(1);
}
const targetIds = isSubsetRun ? args.motions : ids;
```

## Warnings

### WR-01: rollback `--motions` does not trim — whitespace-padded ids silently match nothing

**File:** `app/scripts/rollback-reference-downstream.mjs:49`
**Issue:**
```js
else if (argv[i] === '--motions' && i + 1 < argv.length) { out.motions = argv[i + 1].split(','); i++; }
```
Unlike the seeder (line 92-95) and the Python orchestrator (line 805), this split
has no `.map(s => s.trim()).filter(Boolean)`. A natural invocation
`--motions "ref-climb, ref-invert"` yields `["ref-climb", " ref-invert"]`; the
padded `" ref-invert"` never matches `pre.motions[motionId]`, so line 75 logs
`pre 스냅샷에 doc 없음 — skip` and that motion is silently **not rolled back**. During
an incident response this is the worst time for a silent skip.

**Fix:** Mirror the seeder: `out.motions = argv[i + 1].split(',').map((s) => s.trim()).filter(Boolean);`

### WR-02: `_has_nan_or_inf` misses `np.float32` (and any non-`float`-subclass numpy scalar)

**File:** `backend/scripts/backfill_reference_downstream.py:600-608`
**Issue:**
The R5 all-or-nothing NaN/inf guard only recognizes Python `float`
(`isinstance(obj, float)`). `np.float64` happens to subclass `float` and is caught,
but `np.float32` does **not**, and would pass the guard as a non-float object →
`return False`. The seed payload is largely sanitized by `_dataclass_to_camel_dict`
(which converts `np.floating`→`float`), so today most values are native floats — but
this guard is the *last line of defense* against shipping NaN into Firestore, and it
silently trusts that every upstream converter was perfect. A future field that
bypasses the camel converter (e.g. a hand-built dict) could smuggle a `np.float32`
NaN past the gate.

**Fix:** Broaden the scalar test to cover numpy floats explicitly:

```python
if isinstance(obj, (float, np.floating)):
    return not math.isfinite(float(obj))
```

### WR-03: snapshot/audit "complete" counts share the present-not-valid blind spot (CR-01) and can mask a bad backfill

**File:** `app/scripts/snapshot-reference-phase14-state.mjs:217, 225`; `app/scripts/audit-reference-fields.mjs:72-74, 120`
**Issue:**
`seededMotionCount` (snapshot line 217) and `completeRequiredSet` (audit line 120)
use the same `present()`/`hasField()` non-null check as CR-01. The snapshot's
`downstreamComplete` (line 214) does additionally apply `nonEmpty()` which is better,
but `seededMotionCount` and the audit do not. Because these are the
post-backfill verification artifacts an operator reads to decide the run succeeded,
a present-but-empty field will inflate the "complete/seeded" count and mask exactly
the corruption CR-01 fails to repair. (Snapshot's own comment at line 217 says
"4 신필드" but the check iterates the 5-element `PHASE14_REQUIRED` — minor comment
drift that compounds the confusion.)

**Fix:** Route the snapshot `seeded` and the audit `complete` checks through the same
`present(...) && nonEmpty(...)` predicate the snapshot already defines for
`downstreamComplete`, and correct the "4 신필드" comment to "5 (PHASE14_REQUIRED)".

### WR-04: angle-integrity gate compares `nanmean`/`nanpercentile` that silently degrade to NaN when a joint column is all-NaN — masked only by `math.isfinite` on the aggregate

**File:** `backend/scripts/backfill_reference_downstream.py:533-553`
**Issue:**
`diff = np.abs(stored_angles - rerun_angles)` followed by `np.nanmean(diff)` /
`np.nanpercentile(diff, 99)`. If stored and rerun disagree on *which* frames/joints
are NaN (plausible since rerun is a fresh RTMW pass on a hard/occluded motion), the
per-element `diff` is NaN exactly where either operand is NaN, and `nanmean`/
`nanpercentile` ignore those — so a motion where a whole joint column diverged in
NaN-coverage (e.g. stored had the knee, rerun lost it) contributes **zero** to the
gate. The gate then passes on a motion whose pose-version actually shifted in a way
the robust statistics cannot see. The `gate_failed` clause does guard the
all-NaN-aggregate case (`not math.isfinite(mean_delta)`), but that only fires when
*every* comparable element is NaN, not when a subset is.

This is a correctness concern for the gate's stated job (catch systematic
pose-version drift before backfilling derived fields). It is a WARNING rather than a
BLOCKER because the diagnostic logging (line 538-546) records `over1deg` and argmax,
giving a human a chance to catch it, and because the dominant failure mode (uniform
shift) is still caught.

**Fix:** Add a NaN-coverage check to the gate — abort if the fraction of comparable
(non-NaN) elements drops below a threshold, or if rerun NaN-coverage differs
materially from stored:

```python
comparable = np.isfinite(diff)
coverage = float(comparable.mean()) if diff.size else 1.0
if coverage < 0.95:  # rerun lost/gained too many joints to trust the delta
    raise RuntimeError(f"[{motion_id}] angle gate — NaN coverage {coverage:.2%} < 95%, pose-version 재검증 필요")
```

### WR-05: seeder `validateForceDirectionPattern` does not require the `version` field that the TS/Python contract declares non-empty

**File:** `app/scripts/seed-reference-downstream.mjs:150-188`
**Issue:**
`ForcePatternInference` (analysis.ts:877, `version: string` "non-empty";
contract §9.11) and the helper's diagnostics treat `version` as a required scalar.
The seeder's scoped validator accepts any scalar top-level keys but never asserts
`version`/`overallConfidence`/`modeContext` are present, so a fixture missing
`version` would seed a contract-invalid `forceDirectionPattern` that the app's
`normalize()` (`referenceMotions.ts:155-160`) passes straight through as an object.
The Python production validator `_validate_force_pattern_inference` has the same gap
(it only blocks nested/unknown shapes, not missing required scalars), so this is a
shared contract-enforcement gap rather than a seeder-only one.

**Fix:** After the loop, assert the required scalar surface:

```js
for (const req of ['version', 'overallConfidence', 'modeContext']) {
  if (typeof fdp[req] !== 'string' || !fdp[req]) {
    throw new Error(`[${motionId}] forceDirectionPattern.${req} 누락/빈 문자열`);
  }
}
```

### WR-06: `dataclasses.asdict` deep-copies large body/keypoint structures and can choke on numpy arrays nested in dataclass fields

**File:** `backend/scripts/backfill_reference_downstream.py:182-205`
**Issue:**
`_dataclass_to_camel_dict` calls `dataclasses.asdict(obj)` (line 193), which performs
a recursive deep copy and uses `copy.deepcopy` on non-dataclass leaf values. If any
dataclass field is a raw `np.ndarray` (not unusual for force/body intermediate
products), `asdict` deep-copies the whole array per call, and any ndarray that
survives into the resulting dict will later fail `_has_nan_or_inf` silently (WR-02)
and fail the JS `rejectNestedArray` only if it happens to serialize as a list. The
code assumes every nested value is dataclass/Enum/list/dict/scalar (docstring line
186), but does not defend against an ndarray leaf. Given the comment claims parity
with `pipeline._dataclass_to_camel_case_dict`, confirm that converter handles
ndarray leaves; if it does, mirror that handling here.

**Fix:** Add an explicit ndarray branch before the scalar fallback:

```python
if isinstance(obj, np.ndarray):
    return [_dataclass_to_camel_dict(x) for x in obj.tolist()]
```

## Info

### IN-01: `_run_check_firestore` reads full `angles` array just to take `len()`, defeating the "no expensive work" intent

**File:** `backend/scripts/backfill_reference_downstream.py:389, 408-410`
**Issue:** The pre-flight gate advertises itself as cheap (no S3/RTMW), but
`get_reference_motion(mid)` pulls the entire flattened `angles` array (thousands of
floats per doc × 11) over the wire purely to compute `len(angles)`. This is a read
cost, not a correctness bug, but it partially defeats the "fail fast before
expensive work" framing. Consider reading only `anglesFrames`/`anglesJointKeys` and
a `count`/length signal if Firestore SDK allows field masking, or document that the
gate still downloads full angle arrays.

### IN-02: `audit-reference-fields.mjs` and `referenceMotions.ts` duplicate the `hasField`/present idiom and the 11-id list across 5 files

**File:** `app/scripts/audit-reference-fields.mjs:32-46`; `seed-reference-downstream.mjs:34-46`; `snapshot-reference-phase14-state.mjs:30-33`; `rollback-reference-downstream.mjs:24-27`
**Issue:** `ALL_MOTION_IDS`, `PHASE14_REQUIRED`, and the `present()/hasField()` helper
are copy-pasted across four scripts. Given the project's explicit Pitfall-1 concern
("절대 5-subset default 금지"), a single shared module would prevent the lists from
drifting out of sync. Not a defect today (all four lists match), but a maintenance
risk for exactly the invariant the project most wants protected.
**Fix:** Extract `app/scripts/_referenceConstants.mjs` exporting `ALL_MOTION_IDS`,
`PHASE14_REQUIRED`, and a validity predicate; import in all four scripts.

### IN-03: `rollback` aborts the entire batch if any single motion's pre-snapshot lacks a stored value

**File:** `app/scripts/rollback-reference-downstream.mjs:83-86`
**Issue:** During `--confirm`, a `present:true` snapshot record without an embedded
`value` triggers `process.exit(1)` mid-plan. Because this happens after the plan is
built but the all-or-nothing abort is correct, it is safe — but the error fires
per-motion inside the loop, so an operator rolling back 11 motions during an incident
sees the abort only for the first offending motion with no summary of which others
would also fail. Consider collecting all such errors and reporting them together
before exiting, so the operator can fix the snapshot in one pass.

---

_Reviewed: 2026-06-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
