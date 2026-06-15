---
phase: 03-bodyprofileinput
reviewed: 2026-06-15T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - app/src/app/(tabs)/analyze.tsx
  - app/src/app/(tabs)/profile.tsx
  - app/src/app/analysis/loading.tsx
  - app/src/app/analysis/result.tsx
  - app/src/components/BodyProfileForm.tsx
  - app/src/components/BodyProfilePromptModal.tsx
  - app/src/lib/bodyProfile.ts
  - app/src/lib/userAnalyses.ts
  - app/src/types/analysis.ts
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/models.py
  - backend/tests/test_body_profile.py
  - docs/contract.md
findings:
  critical: 1
  warning: 5
  info: 4
  total: 10
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-06-15
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 03 adds a self-input BodyProfile feature: a shared form, a first-analysis prompt gate, a data-source layer with dual (client+server) normalization, per-analysis snapshotting, and a 3-way contract addition. The 3-way contract lockstep (analysis.ts / models.py / contract.md), the Firestore nested-array discipline (flat `painAreas` scalar array), theme-token usage, Korean copy, and no-emoji rules are all respected — those mandated constraints hold up.

The defects are in runtime behavior, not constraint compliance. The most serious is a load-race in the prompt gate that misfires the modal for users who already have a profile (BLOCKER). Several merge-write and normalization-divergence issues degrade correctness of the live profile and the gate, and a few quality items remain.

## Critical Issues

### CR-01: Prompt gate misfires during async profile load — re-prompts users who already have a profile

**File:** `app/src/app/(tabs)/analyze.tsx:142-151` (also `65`)
**Issue:** `useBodyProfile()` returns `{ profile, promptDismissedAt, loading }`, but `analyze.tsx` destructures only `profile` and `promptDismissedAt` and ignores `loading`. The Firestore subscription starts with `profile = null` and `promptDismissedAt = null` and only populates after the `onSnapshot`/`onAuthStateChanged` round-trip resolves. The gate condition is:

```ts
const notEntered = profile === null;
const notDismissed = promptDismissedAt == null;
if (notEntered && notDismissed) { /* show prompt */ }
```

If the user picks a video before the snapshot has loaded (cold start, slow network, or auth not yet ready — the file itself notes the "콜드스타트 race" for `uid`), `profile` is still `null` and `promptDismissedAt` is still `null`, so an existing-profile user (or a user who already dismissed) is wrongly shown the prompt. This contradicts the stated invariant "프로필이 이미 있거나 이미 dismiss 했으면 즉시 routeAfterPick — 분석을 막지 않음". It is a correctness defect in the core gating logic and produces a visibly wrong UX on the pilot's primary flow.

**Fix:** Gate on the loading flag; while loading, do not branch on `null` (either route straight through or briefly defer). Minimal fix:

```ts
const { profile, promptDismissedAt, loading } = useBodyProfile();
// ...
const maybePromptBeforeRoute = (picked: Picked) => {
  // 프로필 구독이 아직 로딩 중이면 게이트 판정을 신뢰할 수 없다 (null = 미입력 오판).
  // 게스트 우선 — 로딩 중에는 막지 말고 그대로 진행.
  if (loading) { routeAfterPick(picked); return; }
  const notEntered = profile === null;
  const notDismissed = promptDismissedAt == null;
  if (notEntered && notDismissed) {
    setPendingPicked(picked);
    setPromptVisible(true);
    return;
  }
  routeAfterPick(picked);
};
```

(Routing through on `loading` favors the non-forcing/guest-first design over a guaranteed prompt; if a guaranteed prompt is required, defer the pick until `loading === false` instead.)

## Warnings

### WR-01: `saveBodyProfile` merge-write never clears a previously-set field

**File:** `app/src/lib/bodyProfile.ts:168-178`
**Issue:** `saveBodyProfile` does `setDoc(ref, { bodyProfile: { ...partial, updatedAt } }, { merge: true })`. Firestore `merge: true` performs a **deep merge on nested maps**. The form always sends every scalar field (`heightCm`, `weightKg`, `experience`, `dominantHand`) and passes `null` for empty ones, so scalars are correctly overwritten — but `null` written into a map field is preserved as `null`, which is the intended clear. The real gap is asymmetric: any caller that sends a *partial* object (the function name and signature `Partial<BodyProfile>` explicitly invite this) cannot clear a field, because an omitted key is left untouched by the deep merge. A future partial caller intending to remove `experience` would silently retain the old value. The current form happens to send all keys, so this is latent, but the contract (`Partial<BodyProfile>`) advertises behavior the implementation does not provide.

**Fix:** Either (a) document that callers must send all clearable fields (tighten the type away from `Partial`), or (b) for true clears, write `deleteField()` for omitted keys. At minimum add a comment that omitted keys are NOT cleared under deep merge so future callers do not assume otherwise.

### WR-02: `validateNumber` accepts decimals/`Infinity`-adjacent input the keypad cannot produce, but the snapshot path can

**File:** `app/src/components/BodyProfileForm.tsx:85-90`
**Issue:** `validateNumber` uses `Number(trimmed)` and `Number.isFinite(n)`. In the form this is safe because `onChangeHeight`/`onChangeWeight` strip to `[0-9]` with `maxLength=3`. However the same numeric range constants are duplicated three times (form, `bodyProfile.ts`, `models.py`) and only the form coerces to integer-via-stripping. `normalizeBodyProfile` (client) and `normalize_body_profile` (server) both accept any finite number in range, including floats like `165.7`. If a value reaches Firestore by any path other than this form (dev console, future import, another writer), a float is stored and rendered verbatim as `165.7cm`. Not a crash, but the "integer cm/kg" assumption is enforced only by the keyboard, not by the normalizers that are supposed to be the defensive boundary.

**Fix:** Round/reject non-integers in both normalizers if integer is the contract (e.g. `if (!Number.isInteger(value)) return null;` client; `if value != int(value): return None` server), so the defensive layer matches the form's intent.

### WR-03: Three independent copies of the same enum→KO label maps risk lockstep drift

**File:** `app/src/app/(tabs)/profile.tsx:42-61`, `app/src/app/analysis/result.tsx:71-90`, `app/src/components/BodyProfileForm.tsx:44-68`
**Issue:** `EXPERIENCE_LABEL`/`HAND_LABEL`/`PAIN_AREA_LABEL` (and the form's option arrays) are duplicated verbatim across three files, each annotated "analysis.ts union 정합 / BodyProfileForm 과 동일 KO 매핑". When a new `PainArea` or `ExperienceLevel` is added to the union (the contract explicitly anticipates union changes), TypeScript will flag `Record<Union, string>` only where a `Record` type is used — but a missed file produces `undefined` rendered to the user with no compile error if any copy drifts to a non-exhaustive shape. This is a maintainability/correctness hazard given the project's own emphasis on single-source label mapping (`DIMENSION_LABEL_KO` is centralized in `analysis.ts` for exactly this reason).

**Fix:** Centralize `EXPERIENCE_LABEL_KO` / `DOMINANT_HAND_LABEL_KO` / `PAIN_AREA_LABEL_KO` as `Record<Union, string>` consts in `app/src/types/analysis.ts` (next to `DIMENSION_LABEL_KO`) and import them in all three screens, so an added union member fails the build until every label is supplied.

### WR-04: `dismissBodyProfilePrompt` failure is swallowed and re-prompts forever

**File:** `app/src/app/(tabs)/analyze.tsx:164-171`, `app/src/lib/bodyProfile.ts:181-189`
**Issue:** `skipPrompt` calls `dismissBodyProfilePrompt()` inside a `try/catch` that intentionally swallows errors so analysis is not blocked (guest-first — acceptable per D-06). But the consequence is unbounded: if the once-flag write keeps failing (offline guest, rules transient), the user is re-prompted on **every** subsequent first-pick because `promptDismissedAt` never persists. The comment says "재권유 0, D-06" but the swallow path silently violates that guarantee. There is no in-memory fallback flag for the current session.

**Fix:** Set a session-local "already prompted this session" ref/state so that even when the persisted write fails, the modal is not shown again within the session:

```ts
const skipPrompt = async () => {
  promptedThisSession.current = true; // 세션 내 재권유 차단 (영속 실패 graceful)
  try { await dismissBodyProfilePrompt(); } catch {}
  continuePendingRoute();
};
```
and include `promptedThisSession.current` in the gate condition.

### WR-05: `getBodyProfileOnce` failure is unhandled and will reject the upload flow

**File:** `app/src/lib/bodyProfile.ts:157-165`, consumed at `app/src/app/analysis/loading.tsx:107`
**Issue:** `getBodyProfileOnce()` calls `getDoc(...)` with no try/catch. In `startAnalysisUpload` it is `await`ed before the analysis doc is created (`const bodyProfile = await getBodyProfileOnce();`). If the `getDoc` rejects (offline, transient Firestore error), the rejection propagates up and aborts the entire upload — the snapshot read is purely auxiliary (D-06 graceful: all-empty just omits the snapshot) yet a read failure now blocks the core analysis. The live `useBodyProfile` hook already degrades its `onSnapshot` error to `null`; the one-shot path should too.

**Fix:** Make the snapshot read non-fatal:

```ts
export async function getBodyProfileOnce(): Promise<BodyProfile | null> {
  const uid = auth.currentUser?.uid;
  if (!uid) return null;
  try {
    const snap = await getDoc(doc(db, 'users', uid));
    const raw = snap.exists()
      ? (snap.data()?.bodyProfile as Record<string, unknown> | undefined)
      : undefined;
    return normalizeBodyProfile(raw);
  } catch {
    return null; // 보조 snapshot — 읽기 실패해도 분석 흐름 막지 않음 (D-06).
  }
}
```

## Info

### IN-01: Snapshot drops `updatedAt`/`promptDismissedAt` silently — documented but undefended at one boundary

**File:** `app/src/lib/bodyProfile.ts:95`, `backend/shared/python/sunity_shared/models.py:130-136`
**Issue:** Both normalizers return only the five measurement fields and drop the optional `updatedAt`/`promptDismissedAt`. This is correct and consistent (snapshot reproducibility), but the live `useBodyProfile` hook reads `promptDismissedAt` from `raw` *separately* (`bodyProfile.ts:137-138`) precisely because the normalizer strips it. This split is subtle: any future reader who assumes `normalizeBodyProfile` returns the full doc will lose the once-flag. The behavior is well-commented; flagged only so the asymmetry is tracked.
**Fix:** No code change required; consider a unit assertion that `normalizeBodyProfile` output never contains `promptDismissedAt`/`updatedAt` to lock the contract.

### IN-02: `validateNumber` `unit` interpolation produces awkward Korean for range copy

**File:** `app/src/components/BodyProfileForm.tsx:88`
**Issue:** Error string `` `${lo}${unit} ~ ${hi}${unit} 사이로 입력해주세요.` `` yields "90cm ~ 250cm 사이로 입력해주세요." which is fine, but the same helper is reused with `unit='kg'` and the message is acceptable. Minor: a single `~` with surrounding spaces is stylistically inconsistent with the rest of the Korean copy (which uses `·`). Cosmetic only.
**Fix:** Optional copy polish; no functional issue.

### IN-03: `maxLength={3}` on weight is fine but height edge values rely on it implicitly

**File:** `app/src/components/BodyProfileForm.tsx:308`
**Issue:** `maxLength={3}` caps input at 999, which comfortably covers height (≤250) and weight (≤200). The validators reject out-of-range anyway, so this is defensive redundancy, not a bug. Noted because the cap is a magic number co-located with range constants that are themselves duplicated (see WR-03/WR-02); a 4-digit future range would require touching both.
**Fix:** None required.

### IN-04: `result.tsx` falls back to `liveProfile` for old docs — can show a profile that did not exist at analysis time

**File:** `app/src/app/analysis/result.tsx:430-435`
**Issue:** `const bodyProfileSnapshot = storedDoc?.bodyProfile ?? liveProfile;`. The comment correctly scopes this as a fallback "only for old docs without a snapshot". But because `storedDoc?.bodyProfile` is `null` (not `undefined`) whenever the normalizer folds an all-empty snapshot to `null` (`userAnalyses.ts:231`), the `?? liveProfile` fallback also triggers for *new* analyses that genuinely had no profile at the time — displaying the user's *current* live profile on a past result that was run without one. This subtly breaks the "snapshot reproducibility" intent the feature is built around.
**Fix:** Distinguish "doc has no `bodyProfile` key (old doc)" from "doc had an empty profile (new doc, intentionally null)". Preserve `undefined` vs `null` through `normalize` for `bodyProfile`, and only fall back to `liveProfile` when the key is truly absent (`storedDoc && !('bodyProfile' in rawDoc)`).

---

_Reviewed: 2026-06-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
