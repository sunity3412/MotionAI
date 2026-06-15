# Phase 3: 자가입력 BodyProfileInput - Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 9 (3 new, 6 modified)
**Analogs found:** 9 / 9 (all have an in-repo analog — this phase adds zero new pattern categories)

## File Classification

| New/Modified File | New? | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `app/src/lib/bodyProfile.ts` | NEW | data-source hook | request-response / CRUD (Firestore read+write) | `app/src/lib/userAnalyses.ts` | exact (role + flow) |
| `app/src/components/BodyProfileForm.tsx` | NEW | component (form) | transform (input → state → merge-write) | `app/src/app/(tabs)/profile.tsx` (StatBox/InfoRow helpers) + `analyze.tsx` (state+error+a11y) | role-match |
| `app/src/components/BodyProfilePromptModal.tsx` | NEW | component (modal) | event-driven (show/dismiss) | `app/src/components/DimensionDetailModal.tsx` | exact (Modal bottom-sheet) |
| `app/src/types/analysis.ts` | MOD | model (contract, TS) | n/a (type) | existing unions `AnalysisMode`/`ScoreDimension` + `BodyNormalizationProfile` interface (same file) | exact |
| `app/src/app/(tabs)/profile.tsx` | MOD | component (screen) | request-response | itself (existing card pattern — add `BodyProfileCard`) | exact |
| `app/src/app/(tabs)/analyze.tsx` | MOD | component (screen) | event-driven (gate before route) | itself (existing pick flow + busy state) | exact |
| `app/src/app/analysis/loading.tsx` | MOD | component (screen) | transform (snapshot into setDoc) | itself — `setDoc` at line 101 (spread next to `referenceMotionId`) | exact |
| `backend/shared/python/sunity_shared/models.py` | MOD | model (contract, Python) | n/a (constants) | existing `MODES`/`SCORE_DIMENSIONS` tuples + `SYNTHESIS_WARNING_CODES` frozenset | exact |
| `backend/functions/pipeline/app.py` | MOD | service (pipeline) | request-response (meta read → coach context) | `_build_coach_context` (line 738) + `meta.get("referenceMotionId")` (line 1564) | exact |
| `docs/contract.md` | MOD | config (contract doc) | n/a | existing `§7 BodyNormalizationProfile` section | exact |

> Validation note (research §Don't-Hand-Roll): do **NOT** modify `validation.py` or the upload-url Lambda. The profile is snapshotted into the analysis doc client-side and read via `get_analysis()` meta — same mechanism `referenceMotionId` already uses. `validation.py` is included below only as the analog for the OPTIONAL Python defensive normalizer (`normalize_body_profile`), not as a file to edit for an HTTP validator.

---

## Pattern Assignments

### `app/src/lib/bodyProfile.ts` (NEW — data-source hook, Firestore CRUD)

**Analog:** `app/src/lib/userAnalyses.ts` (THE mandatory pattern — research Pattern 1)

**Header / isolation comment + imports** (`userAnalyses.ts:1-19`):
```typescript
// 분석 기록 데이터 소스 레이어 ...
// users/{uid}/analyses 컬렉션 onSnapshot 구독. 화면은 데이터 소스에 무지하도록 격리 —
// 나중에 GraphQL/REST 로 바꿔도 이 파일만 교체(referenceMotions.ts 와 동일 패턴).
// 익명 인증(게스트)도 정상 — 보안 규칙: users/{uid}/{**} 본인만 read/write.
import { collection, doc, onSnapshot, query, orderBy, type FirestoreError } from 'firebase/firestore';
import { onAuthStateChanged } from 'firebase/auth';
import { useEffect, useState } from 'react';
import { auth, db } from './firebase';
```
> For Phase 3 add `setDoc` (merge write) and `serverTimestamp`/`Date.now()` to the firestore import. Subscribe to the **doc** `users/{uid}` (single doc, field `bodyProfile`) using the `useAnalysisDoc` single-doc subscription shape, not the collection query.

**Defensive `normalize()` — copy this exact shape** (`userAnalyses.ts:27-42`, each field independently validated, returns `null` on bad type → research D-06 graceful):
```typescript
function normalize(id: string, raw: Record<string, unknown>): AnalysisDoc | null {
  const mode = raw.mode === 'mode1' || raw.mode === 'mode3' ? raw.mode : null;
  const fileName = typeof raw.fileName === 'string' ? raw.fileName : null;
  const createdAt = typeof raw.createdAt === 'number' ? raw.createdAt : null;
  // ... if any required field invalid → return null
}
```
For BodyProfile, each field is independently optional (NOT null-the-whole-doc). Research §Pattern 1 gives the literal target:
```typescript
function normalize(raw: Record<string, unknown> | undefined): BodyProfile {
  const heightCm = typeof raw?.heightCm === 'number' ? raw.heightCm : null;
  const experience = ['beginner','intermediate','advanced'].includes(raw?.experience as string)
    ? raw!.experience as ExperienceLevel : null;
  const painAreas = Array.isArray(raw?.painAreas)
    ? (raw!.painAreas as unknown[]).filter((x): x is string => typeof x === 'string') : [];
  // weightKg, dominantHand same per-field guard
  return { heightCm, weightKg, experience, painAreas, dominantHand };
}
```

**Single-doc `onSnapshot` hook + auth-race guard — copy from `useAnalysisDoc`** (`userAnalyses.ts:231-273`):
```typescript
export function useAnalysisDoc(analysisId: string | undefined) {
  const [docState, setDocState] = useState<AnalysisDoc | null>(null);
  const [uid, setUid] = useState<string | null>(auth.currentUser?.uid ?? null);
  useEffect(() => onAuthStateChanged(auth, (u) => setUid(u?.uid ?? null)), []);
  useEffect(() => {
    if (!uid || !analysisId) { setDocState(null); setLoading(false); return; }
    const ref = doc(db, 'users', uid, 'analyses', analysisId);
    const unsub = onSnapshot(ref,
      (snap) => { setDocState(snap.exists() ? normalize(snap.id, snap.data() as ...) : null); setLoading(false); },
      (err: FirestoreError) => { if (__DEV__) console.warn('[useAnalysisDoc] error', err); setDocState(null); setLoading(false); });
    return unsub;
  }, [uid, analysisId]);
  return { doc: docState, loading };
}
```
> `useBodyProfile()` mirrors this against `doc(db,'users',uid)` (no analysisId param). `saveBodyProfile(partial)` = `setDoc(doc(db,'users',uid), { bodyProfile: {...partial, updatedAt: Date.now()} }, { merge: true })`. The `onAuthStateChanged` cold-start race guard (`userAnalyses.ts:239-242, 283-286`) is mandatory — guest uid may not be ready on mount.

---

### `app/src/components/BodyProfileForm.tsx` (NEW — form component)

**Analog (helpers + StyleSheet-at-bottom + token usage):** `app/src/app/(tabs)/profile.tsx`
**Analog (state + Korean inline error + a11y on pressables):** `app/src/app/(tabs)/analyze.tsx` (cited by research §B/§E)

**Token-only styles (NO hardcoded color/spacing — `app/CLAUDE.md` ban)** (`profile.tsx:13, 144-205`):
```typescript
import { colors, layout, radius, spacing, typography } from '../../theme';
// ...
card: {
  backgroundColor: colors.cardBg,
  borderWidth: layout.cardBorderWidth,
  borderColor: colors.divider,
  borderRadius: radius.card,        // = 15
  padding: spacing.cardPadding,
},
avatar: { backgroundColor: colors.brandTint, ... },
```
> Form-specific tokens flagged by research §F: `layout.inputHeight` (=54) for the numeric `TextInput` and CTA, `radius.button` (=13) for CTA, `colors.brand` for selected chip bg, `colors.textWhite` for selected chip text, `colors.inputError` (#54B8CD teal, NOT brand red) for validation messages.

**Small named presentational helpers with inline prop types — copy `StatBox`/`InfoRow` shape** (`profile.tsx:96-131`):
```typescript
function StatBox({ label, value, suffix }: { label: string; value: string; suffix: string }) {
  return ( <View style={styles.statBox}>...</View> );
}
```
> Build `Segmented<T>` (경력/우세손) and chip-wrap (통증부위) as these same in-file named helpers. Research §Code-Examples gives literal `Segmented` + multi-select chip bodies.

**Numeric input + Korean inline error pattern** — research §B/§Code-Examples (source pattern = `analyze.tsx` state+error). New `TextInput` (app's first form): `keyboardType="number-pad"`, `maxLength={3}`, suffix as sibling `<Text>`, range-validate (height 90–250 / weight 25–200), allow empty (D-06). iOS `number-pad` has no done key → wrap in `Pressable` calling `Keyboard.dismiss()`.

> **D-05 박제:** put a code comment on `weightKg` state + field that it is 보조 ONLY, never scoring.

---

### `app/src/components/BodyProfilePromptModal.tsx` (NEW — dismissible bottom-sheet)

**Analog:** `app/src/components/DimensionDetailModal.tsx` (research §C, verified)

**Modal bottom-sheet skeleton + imports** (`DimensionDetailModal.tsx:1-31`):
```typescript
import { Modal, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { colors, radius, spacing, typography } from '../theme';
// bottom sheet 형식, 백드롭 dim 50%, 핸들 + 제목 + ✕ 닫기 + CTA
interface Props {
  visible: boolean;
  onClose: () => void;
  // ... domain props
}
```
> Copy the `Modal` + `Pressable` backdrop + bottom-sheet container structure (radius.modal=20). For BodyProfilePromptModal the dismiss must be equal-weight 3 ways (D-06): [건너뛰기] button + backdrop `Pressable onPress={onClose}` + native back — all set the once-flag. Add `accessibilityViewIsModal` on the sheet (research §E). Two clear CTAs: [입력하기] (`colors.brand`) + [건너뛰기] (secondary, not a buried gray link).

---

### `app/src/types/analysis.ts` (MOD — TS contract, 3-way lockstep #1)

**Analog:** existing closed-set unions + the `BodyNormalizationProfile` interface **in the same file** (research Pattern 2).

**String-literal union pattern** (`analysis.ts:8, 59`):
```typescript
export type AnalysisMode = 'mode1' | 'mode3';
export type ScoreDimension = 'angle' | 'line' | 'stability';
```
> Add `ExperienceLevel`, `DominantHand`, `PainArea` unions + `BodyProfile` interface. Research §Data-Contract gives the literal recommended shape (heightCm/weightKg/experience/painAreas/dominantHand all nullable, `painAreas: PainArea[]` flat scalar array, optional `updatedAt`/`promptDismissedAt`). Include the lockstep header comment citing the Python mirror + `docs/contract.md` (pattern: every contract block in this file cites its Python lockstep file — see `BodyNormalizationProfile` comment at `analysis.ts:879-890`).

**Header co-edit mandate to replicate** (`analysis.ts:1-4`):
```typescript
// 이 파일이 바뀌면 docs/contract.md 와 백엔드도 같이 맞춰야 함.
```

---

### `app/src/app/(tabs)/profile.tsx` (MOD — add BodyProfileCard)

**Analog:** itself. Insert a `BodyProfileCard` between the 게스트 카드 (`profile.tsx:45-56`) and 통계 (`:58-66`), or after 통계. Reuse `styles.card` (token-driven) and the `Ionicons` + `useMyAnalyses`-style hook (swap to `useBodyProfile()`).

**Card render + empty/filled summary** — follow the existing card JSX (`profile.tsx:45-56`) and the InfoRow list (`:68-82`). Empty state = brandTint 권유 card ("내 몸 정보 입력하기 ›"); filled = summary row ("165cm · 중급 · 어깨·손목") + "수정 ›". Both tap → `BodyProfileForm`.

---

### `app/src/app/(tabs)/analyze.tsx` (MOD — first-analysis prompt gate)

**Analog:** itself (existing pick flow + `busy` state + `routeAfterPick`). The prompt gate sits **before** `router.push('/analysis/loading')`. Gate logic: show modal only if `bodyProfile` null/absent AND once-flag unset; otherwise pass through unchanged. (Research §A critical-wiring: the modal lives here, but the profile SNAPSHOT happens in `loading.tsx`.)

> Mirror the existing `try/catch/finally` + `busy` reset convention (CLAUDE.md app error-handling notes) and a11y props on the new pressables.

---

### `app/src/app/analysis/loading.tsx` (MOD — snapshot profile into analysis doc)

**Analog:** itself — the `setDoc` at **line 101**, spread `bodyProfile` at the exact spot `referenceMotionId` is conditionally spread.

**The seam (verified `loading.tsx:100-111`):**
```typescript
const now = Date.now();
await setDoc(doc(db, 'users', uid, 'analyses', analysisId), {
  analysisId,
  mode: input.mode,
  status: 'uploading',
  fileName: input.fileName,
  createdAt: now,
  updatedAt: now,
  ...(input.referenceMotionId
    ? { referenceMotionId: input.referenceMotionId }
    : {}),
});
```
> Read `users/{uid}.bodyProfile` (via the hook or a one-shot `getDoc`) before this `setDoc` and add `...(bodyProfile ? { bodyProfile } : {})` alongside `referenceMotionId` (research Pattern 3 — snapshot-at-creation, NOT live cross-read). Self-contained/reproducible: the profile-at-analysis-time is preserved. Do NOT nest `bodyProfile` inside any existing array field (Firestore nested-array ban, research Pitfall 7 — top-level `painAreas: string[]` scalar array is legal).

---

### `backend/shared/python/sunity_shared/models.py` (MOD — Python contract mirror, lockstep #2)

**Analog:** existing tuple constants + frozenset enum in the same file.

**Tuple-constant pattern** (`models.py:10-23`):
```python
MODE_EXPERT = "mode1"
MODE_SELF = "mode3"
MODES = (MODE_EXPERT, MODE_SELF)
DIM_ANGLE = "angle"
SCORE_DIMENSIONS = (DIM_ANGLE, DIM_LINE, DIM_STABILITY)
```
**Frozenset enum pattern** (`models.py:260`):
```python
SYNTHESIS_WARNING_CODES: frozenset[str] = frozenset(...)
```
> Add `EXPERIENCE_LEVELS = ("beginner","intermediate","advanced")`, `DOMINANT_HANDS = ("left","right","both")`, `PAIN_AREAS = (...)` + a doc-shape comment. Research recommends a small `normalize_body_profile(meta_dict) -> dict | None` helper (defensive read, unknown enum → None) used by `_process` — model it on `validation.py`'s pure-function style below.

**Defensive pure-function analog** (`validation.py:36-86`) — per-field guard, returns normalized value, never trusts input types:
```python
def validate_upload_request(body: dict) -> UploadRequest:
    if not isinstance(body, dict): raise ValidationError("bad_request", ...)
    mode = body.get("mode")
    if mode not in models.MODES: raise ValidationError("bad_request", ...)
    # each field: get → type/range check → normalize or None
```
> `normalize_body_profile` differs: it returns `None`/null fields instead of raising (D-06 graceful — the profile is owner-written client-side, not an HTTP request). No new `validate_*` HTTP validator, no upload-url Lambda edit.

---

### `backend/functions/pipeline/app.py` (MOD — coach-context seam, D-04)

**Analog:** itself — `_build_coach_context` (line 738) + the `meta.get("referenceMotionId")` read (line 1564) + the caller (line 1813).

**Add a kwarg + a context key (verified `_build_coach_context:738-779`):**
```python
def _build_coach_context(*, mode, assessments, dim_scores, local_video_path, scene_flags) -> dict:
    return {
        "mode": mode,
        "joints": [ ... kismam.top_issues(assessments, n=3) ... ],
        "videoPath": local_video_path,
        "dimensionScores": dim_scores,
        "sceneFlags": scene_flags,
    }
```
> Add `body_profile: dict | None = None` kwarg and `"bodyProfile": body_profile` key. The existing docstring (`:748-751`) already states writers ignore unknown keys ("Cerebras 는 `context.get('joints')` 만 박제하므로 신규 키 무시 graceful") — so Phase 3 adds the key with ZERO behavior change; Phase 13 consumes it.

**Caller passes the snapshotted profile (verified `:1813-1818`):**
```python
coach_context = _build_coach_context(
    mode=mode, assessments=assessments, dim_scores=dimension_scores,
    local_video_path=local_video_path, scene_flags=scene_result,
)
```
> Add `body_profile=normalize_body_profile(meta.get("bodyProfile"))`. The `meta` dict is already in scope from `get_analysis()` at `:1508` and `meta.get("referenceMotionId")` at `:1564` is the exact same free-read mechanism — no new endpoint, no get_analysis change.

---

### `docs/contract.md` (MOD — human-readable contract, lockstep #3)

**Analog:** existing `## §7. BodyNormalizationProfile` section (`contract.md:331-384`) — same shape: type aliases → interface fields → D-결정 요약 → Firestore 저장 path.
> Add a "BodyProfile (자가입력)" section documenting fields, storage location (`users/{uid}.bodyProfile` + per-analysis snapshot `users/{uid}/analyses/{id}.bodyProfile`), the D-05 weightKg 보조-only constraint, and graceful-missing (SC#4). Place near §7 (the other body-profile section) for discoverability.

---

## Shared Patterns

### Data-source isolation (data hook + defensive normalize)
**Source:** `app/src/lib/userAnalyses.ts:27` (`normalize`) + `:231-273` (`useAnalysisDoc` onSnapshot) + `:239-242` (auth-race guard)
**Apply to:** `bodyProfile.ts` (read+write), every screen consuming the profile (`profile.tsx`, `analyze.tsx`, `loading.tsx`, result screen)
**Rule:** screens never touch Firestore directly; one `normalize()` handles partial/malformed → null/[].

### 3-way contract lockstep (single atomic commit)
**Source:** `app/src/types/analysis.ts:1-4` co-edit mandate + `models.py` tuples + `docs/contract.md §7`
**Apply to:** `analysis.ts` + `models.py` + `contract.md` for the `BodyProfile` type — change all three together (research Pitfall 1; verification = grep all three for `BodyProfile`/`painAreas`).

### Theme tokens only (no hardcoded color/spacing)
**Source:** `app/src/app/(tabs)/profile.tsx:13, 144-205` (imports `{ colors, layout, radius, spacing, typography }`, StyleSheet at bottom referencing tokens)
**Apply to:** `BodyProfileForm.tsx`, `BodyProfilePromptModal.tsx`, the `BodyProfileCard` in `profile.tsx`
**Rule:** brand `#FF4B33` only via `colors.brand`; validation error via `colors.inputError` (teal, NOT red); input height `layout.inputHeight`=54. Grep gate: no hex / `fontSize:` literals in new files.

### Accessibility props on every pressable
**Source:** `analyze.tsx:195`/SourceCard:291 (`accessibilityRole`/`accessibilityState`/`accessibilityLabel`/`hitSlop`) — cited research §E
**Apply to:** every chip/segment/CTA in `BodyProfileForm.tsx` + dismiss buttons in `BodyProfilePromptModal.tsx`
**Rule:** chips use `accessibilityState={{ selected }}`; modal sheet uses `accessibilityViewIsModal`.

### Snapshot-at-creation into analysis doc (not live cross-read)
**Source:** `app/src/app/analysis/loading.tsx:100-111` (`referenceMotionId` conditional spread) + pipeline `meta.get("referenceMotionId")` at `pipeline/app.py:1564`
**Apply to:** `loading.tsx` (spread `bodyProfile`) + `pipeline/app.py` (`meta.get("bodyProfile")`)
**Rule:** profile is copied into the analysis doc at creation; pipeline reads it for free from `get_analysis()` meta — exactly like `referenceMotionId`. No upload-url Lambda / `validation.py` change.

### Writer-ignores-unknown-context-keys (Phase 13 seam, zero-risk now)
**Source:** `backend/functions/pipeline/app.py:748-751` docstring + `coach_writer.py` `context.get('joints')`-only consumption
**Apply to:** `_build_coach_context` new `bodyProfile` key
**Rule:** adding a context key is graceful — current writers ignore it; Phase 13 wires actual prompt consumption.

### weightKg 보조-only containment (D-05)
**Source:** new constraint (no existing analog — enforced by comment + grep gate)
**Apply to:** `analysis.ts` `weightKg` field, `models.py` shape, `_build_coach_context` key
**Rule:** `weightKg`/`weight` must never appear in scoring modules. Verification grep (research §Test-Map): `! grep -rn "weightKg\|weight_kg" backend/shared/python/sunity_shared/analysis/{dimensions,kismam,body_normalizer}.py` → 0 matches.

---

## No Analog Found

None. Every new/modified file maps to an existing in-repo pattern. This is the key finding of the research (§Don't-Hand-Roll): the "right" amount of code for Phase 3 is small precisely because the data-hook, snapshot-at-creation, meta-read, and writer-ignores-unknown-keys patterns all already exist.

| Item | Note |
|------|------|
| `painAreas` exact KO label list | NOT a missing analog — it's a domain-content decision (research A1). Planner confirms against `docs/research/폴스포츠-지식.md` / NotebookLM IPSF / belle. Code pattern (string-literal union + chip wrap) is fully covered. |
| Figma profile-edit frame | Layout source-of-truth (research A2). Planner runs Figma `get_design_context` on `jrdI7kp245HkPfLB0nclsz` before finalizing `BodyProfileForm` layout; fall back to design.md tokens if absent. |

---

## Metadata

**Analog search scope:** `app/src/lib/`, `app/src/components/`, `app/src/app/(tabs)/`, `app/src/app/analysis/`, `app/src/types/`, `backend/shared/python/sunity_shared/`, `backend/functions/pipeline/`, `docs/`
**Files read for excerpts:** `userAnalyses.ts`, `analysis.ts`, `loading.tsx`, `profile.tsx`, `DimensionDetailModal.tsx`, `validation.py`, `models.py` (grep), `pipeline/app.py` (lines 738-828, 1504-1573, 1813), `contract.md` (section index), `firestore.rules`
**Pattern extraction date:** 2026-06-15
**Verification notes:** Seam line numbers confirmed live this session — `loading.tsx setDoc`:101, `_build_coach_context`:738, caller:1813, `meta.get("referenceMotionId")`:1564, `get_analysis` meta:1508. firestore.rules `users/{uid}/{document=**}` owner-only (line 9) — no rules change needed.
