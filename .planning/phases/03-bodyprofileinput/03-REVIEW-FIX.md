---
phase: 03-bodyprofileinput
fixed_at: 2026-06-15T00:00:00Z
review_path: .planning/phases/03-bodyprofileinput/03-REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 9
skipped: 1
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-06-15
**Source review:** .planning/phases/03-bodyprofileinput/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 10
- Fixed: 9
- Skipped: 1 (CR-01 — already fixed in a prior commit, nothing to apply)

**Note:** IN-02/IN-03 were initially deferred as cosmetic/"none required" but were
applied in a follow-up pass (commit 0e63f56) at the user's request to close out
everything fixable now.

**Verification:** `cd app && npm run typecheck` (tsc --noEmit) passes clean after
every app/TS edit. `cd backend && python -m pytest tests/test_body_profile.py -q`
passes (20 tests, up from 17; pytest 9.0.3 via system python3). No RunPod/GPU
path touched.

## Fixed Issues

### WR-01: `saveBodyProfile` merge-write never clears a previously-set field

**Files modified:** `app/src/lib/bodyProfile.ts`
**Commit:** 45c134c (shared with WR-05)
**Applied fix:** The reviewer's minimum fix (a). Added a comment documenting that
Firestore `merge: true` deep-merges nested maps, so omitted keys are NOT cleared
and a future partial caller intending to remove a field must write
`deleteField()`. No behavior change — the current form sends all keys, so this is
latent; the comment prevents a future partial caller from assuming clear-on-omit.

### WR-05: `getBodyProfileOnce` failure is unhandled and will reject the upload flow

**Files modified:** `app/src/lib/bodyProfile.ts`
**Commit:** 45c134c (shared with WR-01)
**Applied fix:** Wrapped the `getDoc` in try/catch returning `null` on failure
(mirrors the live `useBodyProfile` `onSnapshot` error degrade), so a transient
Firestore read no longer aborts `startAnalysisUpload`. Dev-only `console.warn`
behind `__DEV__`, matching the hook's existing pattern.

### WR-04: `dismissBodyProfilePrompt` failure is swallowed and re-prompts forever

**Files modified:** `app/src/app/(tabs)/analyze.tsx`
**Commit:** ffe07df
**Applied fix:** Added a `promptedThisSession` ref (via `useRef`), set it before
the persist write inside `skipPrompt`, and added it to the gate condition in
`maybePromptBeforeRoute`. Even when the once-flag persist fails (offline guest,
rules transient), the modal is not re-shown within the session. Matches the
reviewer's suggested shape.

### WR-03: Three independent copies of the same enum→KO label maps risk lockstep drift

**Files modified:** `app/src/types/analysis.ts`, `app/src/app/(tabs)/profile.tsx`,
`app/src/app/analysis/result.tsx`, `app/src/components/BodyProfileForm.tsx`
**Commit:** 3ec8c48
**Applied fix:** Centralized `EXPERIENCE_LABEL_KO` / `DOMINANT_HAND_LABEL_KO` /
`PAIN_AREA_LABEL_KO` as `Record<Union, string>` consts in `analysis.ts` next to
`DIMENSION_LABEL_KO`, and imported them in all three consumers. `BodyProfileForm`
keeps its value-ordering arrays (display order) but derives labels from the
central maps via `.map`. Adding a union member now fails the build until every
label is supplied.

### WR-02: `validateNumber`/normalizers accept non-integer cm/kg the keypad cannot produce

**Files modified:** `app/src/lib/bodyProfile.ts`,
`backend/shared/python/sunity_shared/models.py`,
`backend/tests/test_body_profile.py`
**Commit:** dae103c
**Applied fix:** Added integer enforcement in both defensive normalizers —
`if (!Number.isInteger(value)) return null;` (client `numberInRange`) and
`if value != int(value): return None` (server `_coerce_number_in_range`).
Integer-valued floats like `165.0` stay accepted. Added two unit tests
(reject `165.7`/`55.5`, keep `165.0`). The 3-way contract is unaffected
(the integer constraint is a normalizer-internal tightening, not a type/shape
change), so `analysis.ts`/`contract.md` did not need to change.

### IN-01: Snapshot drops `updatedAt`/`promptDismissedAt` — documented but undefended

**Files modified:** `backend/tests/test_body_profile.py`
**Commit:** 8e258b6
**Applied fix:** The reviewer's suggested unit assertion. Added a test asserting
`normalize_body_profile` output never contains `updatedAt`/`promptDismissedAt`
and exposes exactly the five measurement keys, locking the strip-metadata
contract so a future reader cannot assume the full doc and lose the once-flag.

### IN-04: `result.tsx` falls back to `liveProfile` for old docs — can show a profile that did not exist at analysis time

**Files modified:** `app/src/lib/userAnalyses.ts`, `app/src/app/analysis/result.tsx`
**Commit:** 9e1a22d
**Status:** fixed: requires human verification
**Applied fix:** Preserved the `undefined` (key absent = old doc) vs `null`
(present-but-empty = new doc) distinction. `userAnalyses` now only sets the
`bodyProfile` key when it is present in the raw doc (`'bodyProfile' in raw`);
`result.tsx` falls back to `liveProfile` only when `storedDoc?.bodyProfile ===
undefined`, not on `null`. The no-doc case (`storedDoc === null`) still falls
back to live, unchanged. **Flagged for human verification:** this is a
state/reproducibility logic change; typecheck confirms type-correctness but the
intended runtime behavior (old docs fall back, new empty docs do not, live
profile never leaks onto a past result) should be confirmed against real
Firestore docs of both shapes.

### IN-02: `validateNumber` range-copy polish

**Files modified:** `app/src/components/BodyProfileForm.tsx`
**Commit:** 0e63f56
**Applied fix:** Tightened the range error copy from `90cm ~ 250cm 사이로...`
to `90~250cm 사이로...` — range bound by a space-free tilde with the unit
appended once. The reviewer's `·` suggestion was rejected because `·` is a
list/middle-dot separator, semantically wrong for a numeric range; `~` is the
conventional Korean range notation.

### IN-03: `maxLength={3}` magic number co-located with duplicated range constants

**Files modified:** `app/src/components/BodyProfileForm.tsx`
**Commit:** 0e63f56
**Applied fix:** Added a `maxLength` prop to `NumberField` and derive it at the
call sites from the actual range constants (`String(HEIGHT_CM_MAX).length`,
`String(WEIGHT_KG_MAX).length`). The disconnected magic `3` is gone — the input
cap now follows the range bound automatically if it ever widens. Behavior is
unchanged (both maxima are 3-digit).

## Skipped Issues

### CR-01: Prompt gate misfires during async profile load

**File:** `app/src/app/(tabs)/analyze.tsx:142-151`
**Reason:** skipped: already fixed in commit 02555f7 (nothing to apply). Verified
the loading-gate guard is present — `analyze.tsx` destructures
`loading: profileLoading` from `useBodyProfile()` (line 65) and
`maybePromptBeforeRoute` routes straight through while `profileLoading` is true
(lines 146-150). Not re-applied.

---

_Fixed: 2026-06-15_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
