# Phase 3: 자가입력 BodyProfileInput - Research

**Researched:** 2026-06-15
**Domain:** React Native (Expo SDK 54) form UX + Firestore guest-uid storage + 3-way data contract + coach_writer LLM hook seam
**Confidence:** HIGH (codebase patterns verified by direct read; RN component choices CITED from Expo docs; pole-sports body-part list ASSUMED pending domain confirm)

## Summary

This phase adds a **5-field self-input body profile** (키 cm / 몸무게 kg / 경력 초·중·고급 / 통증부위 칩 다중선택 / 우세손 좌·우·양) to an app that is already end-to-end functional. The work is **almost entirely frontend + one data-contract field + one backend read-seam** — no new HTTP endpoint, no Firestore rules change, no new ML algorithm. The app currently has **zero `TextInput` usage** (this is the app's first real form), so the input components (numeric input, segmented control, multi-select chips, single-select) must be built from RN primitives following existing theme tokens. The "가벼운 권유" first-analysis prompt can reuse the existing `Modal` bottom-sheet pattern (`DimensionDetailModal.tsx`).

The single most important architectural finding: **the analysis document is created client-side** in `app/src/app/analysis/loading.tsx:101` via `setDoc(doc(db,'users',uid,'analyses',analysisId), {...})`, exactly where `referenceMotionId` is conditionally spread. **BodyProfile should be snapshotted into the analysis doc at this same point**, and the pipeline reads it for free via the existing `firestore_admin.get_analysis(uid, analysis_id)` → `meta` dict (the same mechanism `referenceMotionId` already uses). This means: (1) no change to `UploadUrlRequest` / `validate_upload_request` / the upload-url Lambda; (2) the coach_writer hook (D-04) is a 2-line addition to `_build_coach_context()` in `pipeline/app.py:738`. The profile itself lives in a persistent `users/{uid}` profile doc (read in profile.tsx + loading.tsx), so it survives across analyses.

**Primary recommendation:** Build a `BodyProfileCard` (마이페이지 상시 편집) + a dismissible `BodyProfilePromptModal` (첫 분석 직전 1회) feeding a shared `BodyProfileForm`. Store at `users/{uid}` doc field `bodyProfile` via a new `app/src/lib/bodyProfile.ts` data-source hook (mirroring `userAnalyses.ts` `normalize()` defensiveness). Snapshot the profile into the analysis doc at `loading.tsx` doc-creation. Add the `BodyProfile` type 3-way lockstep (TS `analysis.ts` ↔ Python `models.py` ↔ `docs/contract.md`) and inject it into `_build_coach_context` as the Phase 13 consumption seam. Use RN-primitive components (no new dependency) so EAS Build risk stays at zero.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 입력 진입점 = **마이페이지 상시 편집 + 첫 분석 직전 1회 가벼운 권유** (둘 다). 게스트 우선·강제 아님. 회원가입 뒤로 미루지 않음(지금·선택 입력). 정식 출시 큐레이션 온보딩은 deferred.
- **D-02:** 마이페이지(`app/src/app/(tabs)/profile.tsx`)는 현재 정적 게스트 정보 카드 — Phase 3 가 BodyProfile 편집 카드/화면 추가.
- **D-03:** 빠른 선택형. 경력=초/중/고급 구간선택, 통증부위=신체부위 칩 다중선택, 우세손=좌/우/양, 키=숫자(cm), 몸무게=숫자(kg).
- **D-04:** 저장 + 결과화면 표기 + coach_writer LLM 컨텍스트 훅. Phase 3 는 데이터가 coach_writer 까지 흐르는 경로만 확보, 실 LLM 활성 검증은 Phase 13.
- **D-05:** 키·몸무게(`weightKg`/`heightCm`)는 **보조 정보로만** — 분석 단정 근거 X (코드 주석 + 사용처 제한). 통증부위·경력은 coach 컨텍스트로만, 점수 산출 직접 가중 X.
- **D-06:** 명확한 "건너뛰기" + 부분 입력 허용 + 재권유 안 함. 미입력이어도 분석 graceful.

### Claude's Discretion
- 통증부위 칩의 정확한 부위 목록 (폴스포츠 맥락) — plan/research 에서 IPSF·도메인 참조로 확정.
- BodyProfile Firestore 저장 위치 (`users/{uid}` doc 또는 `users/{uid}/profile`) + 분석 요청 전달 메커니즘(upload body vs pipeline user-doc read) — 기존 contract 패턴에 맞춰 결정. **3-way contract lockstep 준수 필수.**
- 결과화면 BodyProfile 표기 위치/형식 — design.md + Figma 우선.

### Deferred Ideas (OUT OF SCOPE)
- 회원가입 후 큐레이션 온보딩 (정식 출시 후속).
- 유연성·근력 자가입력 (부정확, ROADMAP 명시 제외).
- 통증부위 → 부상 위험 신호 연동 (Phase 10 SAFE-01).
- 실 LLM 코칭에서 BodyProfile 소비 (Phase 13).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BODY-02 | 사용자가 키·몸무게·경력·통증부위·우세손을 1회 입력하고 분석에 BodyProfile이 함께 전달된다. weightKg는 보조 정보로만 사용, 유연성·근력 자가입력은 받지 않음. | UI/UX Flow (§A) + RN input components (§B) + 3-way contract location (§Architecture Patterns / §Data Contract) + Firestore `users/{uid}` storage + analysis-doc snapshot at `loading.tsx:101` + coach_writer seam at `_build_coach_context` (§Coach Hook). `weightKg` 보조-only 박제 via code comment + 미사용 in scoring path (§Pitfall 5). graceful missing via `normalize()` defensive pattern (§Pitfall 6). |
</phase_requirements>

---

# PRIORITY 1 — UI/UX FLOW (belle's emphasis)

## A. End-to-End UX Flow Map

Two entry points (D-01), one shared form. Both paths are **fully optional and skippable** (D-06).

```
ENTRY POINT 1 — 마이페이지 상시 편집 (always available, primary)
─────────────────────────────────────────────────────────────
(tabs)/profile.tsx
  └─ [현재] 게스트 카드 + 통계 + 정보리스트 (정적)
  └─ [NEW] BodyProfileCard
        ├─ 미입력 상태: "내 몸 정보 입력하기 ›" (brandTint 카드, 권유 톤)
        │     │  탭
        │     ▼
        │   BodyProfileForm (전체화면 route 또는 인라인 확장)
        │     ├─ 키(숫자) · 몸무게(숫자) · 경력(segmented) ·
        │     │   통증부위(chips multi) · 우세손(segmented single)
        │     ├─ [저장]  → users/{uid}.bodyProfile merge-write → 카드 채워짐
        │     └─ [닫기/뒤로] → 저장 안 함, 부분입력도 저장 가능 (D-06)
        │
        └─ 입력됨 상태: 요약 표시 ("165cm · 중급 · 어깨·손목" 등) + "수정 ›"
              탭 → 같은 BodyProfileForm (기존값 prefill)

ENTRY POINT 2 — 첫 분석 직전 1회 가벼운 권유 (dismissible, no-nag)
─────────────────────────────────────────────────────────────
(tabs)/analyze.tsx  →  [모드선택] → [영상소스선택] → pick
                                          │
              ┌───────────────────────────┘
              ▼
  [GATE] 프로필 미입력 AND 아직 권유 안 봄(once flag) ?
    ├─ NO  → 기존 흐름 그대로 (routeAfterPick → /analysis/loading)
    └─ YES → BodyProfilePromptModal (Modal bottom-sheet, 백드롭 dim)
               ├─ 헤드라인: "더 정확한 코칭을 위해 (선택)"
               ├─ 부텍스트: "키·경력·통증부위를 알려주면 분석이 더 구체적이에요"
               ├─ [입력하기]   → BodyProfileForm → 저장 → 분석 계속
               ├─ [건너뛰기]   → once flag 세팅 → 분석 계속 (재권유 X)
               └─ 백드롭 탭/닫기 = 건너뛰기와 동일 (once flag 세팅)

  ※ once flag = AsyncStorage 'bodyProfilePromptSeen' (또는
    users/{uid}.bodyProfile.promptDismissedAt). 한 번 건너뛰면 다시 안 뜸 (D-06).
    프로필이 이미 있으면 게이트 자체 통과 (모달 미표시).
```

**Key state transitions:**
| From | Trigger | To | Notes |
|------|---------|----|----|
| profile 미입력 카드 | tap | BodyProfileForm | prefill 없음 |
| BodyProfileForm | 저장 (전체/부분) | profile 요약 카드 | merge-write, partial OK |
| BodyProfileForm | 뒤로/닫기 | 이전 화면 | 미저장 (또는 명시 저장만) |
| analyze pick | gate=YES | PromptModal | 1회만 |
| PromptModal | 건너뛰기/dismiss | loading | once flag set, no re-nag |
| PromptModal | 입력하기→저장 | loading | profile now attached to analysis doc |

**Critical wiring detail (verified):** The analysis document is created in `app/src/app/analysis/loading.tsx:101` (`setDoc(...)`), NOT in `analyze.tsx`. The prompt modal lives at the end of `analyze.tsx`'s pick flow (before `router.push('/analysis/loading')`), but the **profile snapshot onto the analysis doc happens in `loading.tsx`** by reading `users/{uid}.bodyProfile` and spreading it into the `setDoc` payload (same spot as `referenceMotionId`).

## B. RN + Expo Input Component Patterns (Expo SDK 54)

The app has **no existing `TextInput`** — this is the first form. **Recommendation: build all four input types from RN core primitives** (`TextInput`, `Pressable`) — zero new dependency, zero EAS Build risk, full theme-token control. Do NOT add `@react-native-segmented-control/segmented-control` or any chip library — they are unnecessary for 3-5 closed-set choices and add native-build surface area.

| Field | Input type | Primitive | Implementation notes |
|-------|-----------|-----------|---------------------|
| 키 (cm) | 숫자 | `TextInput` | `keyboardType="number-pad"` `[CITED: reactnative.dev/docs/textinput]`, `maxLength={3}`, suffix "cm" rendered as sibling `Text`. Validate 90–250 range, allow empty (D-06). `returnKeyType="done"`. |
| 몸무게 (kg) | 숫자 | `TextInput` | `keyboardType="number-pad"`, `maxLength={3}`, suffix "kg". Validate 25–200 range, allow empty. `weightKg` 보조-only comment 박제 (D-05). |
| 경력 | 구간 단일선택 | row of `Pressable` chips (segmented) | 3 options 초/중/고급 — custom segmented row (selected = `colors.brand` bg + `textWhite`, unselected = `colors.cardBg` + border). Closed set → string-literal union. |
| 통증부위 | 다중선택 칩 | wrap of `Pressable` chips | `flexWrap:'wrap'` chip grid, toggle selected state, `string[]` value. Selected = `colors.brandTint`/`brand`. Empty array = 없음 (graceful). |
| 우세손 | 단일선택 | row of `Pressable` chips (segmented) | 좌/우/양 — same segmented pattern as 경력. |

**iOS `number-pad` caveat:** `number-pad` keyboard has no "done"/dismiss button on iOS. Provide an explicit tap-outside-to-dismiss (`Keyboard.dismiss()` via a wrapping `Pressable`) or a visible "완료" affordance, since the form is short. `[CITED: reactnative.dev/docs/textinput keyboardType]`

**Why custom Pressable chips over a library `SegmentedControl`:** `@react-native-segmented-control/segmented-control` renders native iOS UISegmentedControl whose styling can't honor brand `#FF4B33` / Pretendard cleanly and adds a native module (EAS Build prebuild surface — see `eas-build-gotchas` memory). For 3 options the custom row is ~30 lines and fully theme-compliant. `[CITED: docs.expo.dev/versions/latest/sdk/segmented-control]`

**No new charts/library needed.** (`victory-native` / `react-native-gifted-charts` in app/CLAUDE.md are NOT installed and NOT needed here.)

## C. "가벼운 권유" Pattern (first-analysis, non-forcing)

**Reuse the existing Modal bottom-sheet pattern** from `app/src/components/DimensionDetailModal.tsx` (verified: `Modal` + `Pressable` backdrop + bottom-sheet, `radius.modal=20`, backdrop dim). Build `BodyProfilePromptModal` on the same skeleton.

Non-forcing requirements (D-06):
- **Dismissible 3 ways:** [건너뛰기] button, backdrop tap, native back — all equivalent.
- **Skip is visually equal-weight**, not a tiny gray link buried under a big CTA. Two clear choices: [입력하기] (brand) + [건너뛰기] (secondary, but not hidden).
- **No-nag once flag:** persist dismissal so it never re-appears. Store in `users/{uid}.bodyProfile.promptDismissedAt` (preferred — travels with profile, survives reinstall via Firestore) OR AsyncStorage `bodyProfilePromptSeen` (simpler, device-local). Recommend the Firestore field for cross-device consistency, but AsyncStorage is acceptable for pilot.
- **Gate logic:** show modal only if `bodyProfile` is null/absent AND `promptDismissedAt` unset. Once profile exists, gate is permanently bypassed.

**Fitness/coaching-app convention (MEDIUM confidence, WebSearch):** optional body-data onboarding is universally presented as a single dismissible interstitial with a clear "skip"/"later" affordance, value-framed ("for more accurate coaching"), never blocking the core action. This matches D-01/D-06 exactly. `[ASSUMED — general UX pattern, not a Sunity-specific source]`

## D. Partial-Input & Skip UX (D-06)

- **Every field independently optional.** Save writes only filled fields (merge). A profile with only 키 + 경력 is valid.
- **`normalize()` on read** (mirror `userAnalyses.ts:27`) returns a `BodyProfile` with each field `null`/empty when absent — never throws on malformed/partial data.
- **Empty states:** profile card shows "내 몸 정보 입력하기" when fully empty; shows partial summary ("165cm · 경력 미입력" or just the filled fields) when partial.
- **Analysis graceful (SC#4):** if `bodyProfile` is absent on the analysis doc, pipeline proceeds on `BodyNormalizationProfile` alone. The `_build_coach_context` injection must be `bodyProfile or None`-safe.

## E. Accessibility (mandatory per analyze.tsx)

Every pressable in this app carries a11y props (verified `analyze.tsx:195`, `SourceCard:291`). Form requirements:
- **Chips/segmented:** `accessibilityRole="button"` + `accessibilityState={{ selected: isSelected }}` + `accessibilityLabel` (e.g. "경력 중급, 선택됨"). Use `selected` not `checked` for single-select; for multi-select chips `selected` is also correct.
- **TextInput:** `accessibilityLabel="키, 센티미터"` + `accessibilityHint` if non-obvious. `keyboardType` provides numeric semantics.
- **Skip/dismiss:** `accessibilityRole="button"` + clear label "건너뛰기".
- **Modal:** `accessibilityViewIsModal` on the sheet container so VoiceOver traps focus inside.
- `hitSlop` on small chips (existing convention: `hitSlop={10}`).

## F. design.md / Figma Alignment

- **Brand `#FF4B33` only via `colors.brand`** — never hardcode (app/CLAUDE.md, verified `colors.ts` is the single source). Selected chip = `colors.brand`; tint = `colors.brandTint`.
- **Light theme only** — white bg (`colors.bg`), card bg `colors.cardBg`, border `colors.divider`, radius `radius.card`=15.
- **Pretendard** via `typography` tokens (`listTitle`, `caption`, `boxLabel`). No hardcoded fontSize.
- **Input height** token exists: `layout.inputHeight=54` (§5-3-1) — use for the numeric `TextInput` and CTA.
- **CTA button:** `radius.button=13`, height 54, full-width (design.md §5-3) — `colors.brand` bg, `colors.textWhite`.
- **Error color is teal `colors.inputError` (#54B8CD)**, intentionally NOT brand red (verified `colors.ts` comment) — use for validation messages.
- **Figma:** Per `ui-figma-first` memory, **check Figma fileKey `jrdI7kp245HkPfLB0nclsz` for any 프로필/BodyProfile/마이페이지 편집 screens before finalizing layout.** The planner should run a Figma read (get_design_context) on that file during planning; if a profile-edit frame exists, it is the source of truth over self-interpreted layout. `[ASSUMED — Figma not read in this research session; planner/discuss must verify]`

---

# PRIORITY 2 — Data Contract & Integration

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| BodyProfile input UI (form, chips, prompt) | App (RN screens/components) | — | Pure presentation + local validation |
| BodyProfile persistence | App data-source hook → Firestore `users/{uid}` | — | Client owns its profile doc (rules allow owner write); same pattern as analyses |
| Profile→analysis attach | App (loading.tsx setDoc) | — | Analysis doc is created client-side; snapshot at creation, like referenceMotionId |
| Profile→coach delivery | API/Pipeline (read via get_analysis meta) | — | Pipeline already reads the analysis doc; zero new endpoint |
| coach_writer consumption | API/Pipeline (_build_coach_context) | LLM (Phase 13) | Phase 3 wires the seam; Phase 13 consumes |
| Contract type definition | Cross-cutting (TS ↔ Python ↔ docs) | — | 3-way lockstep mandate |

## Standard Stack

**No new packages.** This phase uses only what is already installed.

### Core (all already present — verified `app/package.json` via CLAUDE.md inventory)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-native (`TextInput`, `Pressable`, `Modal`) | 0.81.5 | All form inputs + prompt sheet | Core primitives; no native module added |
| @react-native-async-storage/async-storage | 2.2.0 | Optional once-flag for prompt | Already a dep (Firebase Auth persistence) |
| firebase (firestore) | ^12.13.0 | `users/{uid}` profile doc read/write (`setDoc`/`onSnapshot`/`doc`) | Already the app's data layer |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom Pressable segmented | `@react-native-segmented-control/segmented-control` | Native module → EAS prebuild surface + can't theme brand color/Pretendard cleanly. Rejected. |
| Custom chip wrap | `react-native-sectioned-multi-select` / dropdown libs | Overkill for ~6 closed-set body parts; adds dependency + modal UX mismatch. Rejected. |
| Firestore once-flag | AsyncStorage once-flag | AsyncStorage simpler but device-local (lost on reinstall). Firestore field travels with profile. Either acceptable for pilot. |

**Installation:** None. (No `npm install` required — this is a strict win for EAS Build stability per `eas-build-gotchas` memory.)

## Package Legitimacy Audit

> Not applicable — this phase installs **no external packages**. All components are built from already-installed React Native core + existing Firebase/AsyncStorage deps. No registry verification needed.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── APP (React Native) ───────────────────────────┐
│                                                                            │
│  profile.tsx ──┐                          analyze.tsx (pick flow)          │
│  (상시 편집)    │                              │                            │
│                ▼                              ▼ gate: profile null & !seen  │
│         BodyProfileForm  ◄──────────  BodyProfilePromptModal (dismissible) │
│           (shared)                            │ skip → once-flag             │
│                │ 저장(부분 OK)                  │                            │
│                ▼                              ▼                            │
│      lib/bodyProfile.ts  ──setDoc(merge)──►  Firestore users/{uid}         │
│      (hook: useBodyProfile, normalize())     .bodyProfile { heightCm,...}  │
│                ▲                                      │                     │
│                │ onSnapshot                          │ read on analysis    │
│                └──────────────────────────────────────┘   start            │
│                                                       ▼                     │
│              loading.tsx setDoc(analysis) ── spread bodyProfile ──┐         │
│              users/{uid}/analyses/{id}.bodyProfile  (snapshot)    │         │
└──────────────────────────────────────────────────────────────────┼────────┘
                                                                     │ S3 PUT → SQS
                                                                     ▼
┌─────────────────────── BACKEND (Lambda → RunPod) ─────────────────────────┐
│  pipeline/app.py::_process                                                 │
│    meta = firestore_admin.get_analysis(uid, id)   ◄── reads bodyProfile    │
│              │                                         (FREE — same as      │
│              ▼                                          referenceMotionId)  │
│    _build_coach_context(..., body_profile=meta.get("bodyProfile"))         │
│              │  [D-04 SEAM — Phase 13 consumes]                             │
│              ▼                                                              │
│    coach_writer.write(context)   (Cerebras / Gemini)                       │
│    complete_analysis(..., bodyProfile=...)  → result echo (결과화면 표기)   │
└────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (new/changed files)
```
app/src/
├── components/
│   ├── BodyProfileForm.tsx        # shared form (chips, numeric, segmented)
│   └── BodyProfilePromptModal.tsx # first-analysis dismissible sheet (reuse Modal pattern)
├── lib/
│   └── bodyProfile.ts             # useBodyProfile() hook + normalize() + saveBodyProfile()
├── app/(tabs)/
│   └── profile.tsx                # + BodyProfileCard (edit entry)
├── app/(tabs)/
│   └── analyze.tsx                # + prompt gate before routeAfterPick
├── app/analysis/
│   └── loading.tsx                # snapshot bodyProfile into analysis setDoc
└── types/
    └── analysis.ts                # + BodyProfile type (3-way lockstep #1)

backend/shared/python/sunity_shared/
└── models.py                      # + BodyProfile constants/shape (3-way lockstep #2)

backend/functions/pipeline/
└── app.py                         # _build_coach_context body_profile arg (D-04 seam)

docs/
└── contract.md                    # + BodyProfile section (3-way lockstep #3)
```

### Pattern 1: Data-source hook with defensive normalize (MANDATORY)
**What:** A `lib/bodyProfile.ts` exposing `useBodyProfile()` (onSnapshot subscription) + `saveBodyProfile(partial)` (merge setDoc) + `normalize(raw)`.
**When to use:** All profile reads/writes — screens never touch Firestore directly (verified app convention `userAnalyses.ts`, `referenceMotions.ts`).
**Example (pattern, not literal):**
```typescript
// Source: app/src/lib/userAnalyses.ts:27 (normalize) + :288 (onSnapshot hook)
function normalize(raw: Record<string, unknown> | undefined): BodyProfile {
  // 각 필드 독립 검증, 부분/없음 graceful (D-06). 잘못된 타입 → null/[].
  const heightCm = typeof raw?.heightCm === 'number' ? raw.heightCm : null;
  const experience = ['beginner','intermediate','advanced'].includes(raw?.experience as string)
    ? raw!.experience as ExperienceLevel : null;
  const painAreas = Array.isArray(raw?.painAreas)
    ? (raw!.painAreas as unknown[]).filter((x): x is string => typeof x === 'string')
    : [];
  // ...weightKg, dominantHand
  return { heightCm, weightKg, experience, painAreas, dominantHand };
}
```

### Pattern 2: String-literal unions for closed sets (MANDATORY)
**What:** `经력`/우세손 are closed sets → union types (verified convention `AnalysisMode = 'mode1'|'mode3'`, `ScoreDimension`).
```typescript
export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced';
export type DominantHand = 'left' | 'right' | 'both';
export type PainArea = 'shoulder' | 'wrist' | 'lower_back' | 'knee' | 'ankle' | 'neck' | 'hip' | 'elbow';
```

### Pattern 3: Snapshot-at-creation (not live-link)
**What:** Copy the profile into the analysis doc when the analysis is created (`loading.tsx:101`), rather than having the pipeline cross-read the profile doc. This makes the analysis self-contained and reproducible (the profile at analysis time is preserved even if the user later edits it). Mirrors how `referenceMotionId` is already snapshotted.

### Anti-Patterns to Avoid
- **Adding a native segmented-control / chip library** — unnecessary native build surface (EAS risk), can't honor brand theme. Use Pressable.
- **Routing the profile through `UploadUrlRequest`** — would force editing `validation.py` + the upload-url Lambda + contract for a value the pipeline can already read from the analysis doc. Snapshot at `loading.tsx` instead.
- **Storing `painAreas` as a nested array inside another array** — Firestore nested-array ban. A top-level `string[]` field is fine (Firestore allows arrays of scalars; only arrays-of-arrays are banned). See Pitfall 7.
- **Hardcoding `#FF4B33`, fontSize, spacing** — forbidden (app/CLAUDE.md). Tokens only.
- **Letting `weightKg` reach any scoring code** — D-05 violation. Keep it in profile/coach-context only.

## Data Contract — 3-Way Lockstep (Claude's Discretion → recommended shape)

> **MANDATORY:** edit all three together (CLAUDE.md Cross-cutting). The TS type, the Python mirror, and `docs/contract.md` must change in one atomic commit.

**Recommended `BodyProfile` shape (TS — `app/src/types/analysis.ts`):**
```typescript
// 자가입력 보조 프로필 (Phase 3, BODY-02). 영상으로 단정 불가한 항목 보완.
// 모든 필드 optional/nullable — 부분입력·미입력 graceful (D-06).
// weightKg = 보조 정보 ONLY — 분석 단정·점수 가중 금지 (D-05).
export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced';
export type DominantHand = 'left' | 'right' | 'both';
export type PainArea =
  | 'shoulder' | 'wrist' | 'lower_back' | 'knee' | 'ankle' | 'neck' | 'hip' | 'elbow';

export interface BodyProfile {
  heightCm: number | null;        // 90–250, 보조
  weightKg: number | null;        // 25–200, 보조 ONLY (D-05) — never in scoring
  experience: ExperienceLevel | null;
  painAreas: PainArea[];          // 다중선택, [] = 없음 (flat scalar array — nested-array safe)
  dominantHand: DominantHand | null;
  updatedAt?: number;             // epoch ms
  promptDismissedAt?: number;     // 첫 분석 권유 건너뛰기 once-flag (옵션)
}
```
- **Python mirror** (`backend/shared/python/sunity_shared/models.py`): constants `EXPERIENCE_LEVELS = ("beginner","intermediate","advanced")`, `DOMINANT_HANDS = ("left","right","both")`, `PAIN_AREAS = (...)`, and a doc-shape comment. Since the profile is **not validated by an HTTP Lambda** (it's written client-side under owner-only rules), no `validate_*` function is strictly required — but the pipeline should **defensively read** it (treat unknown values as None). Add a small `normalize_body_profile(meta_dict) -> dict | None` helper used by `_process`.
- **`docs/contract.md`:** add a "BodyProfile (자가입력)" section documenting the field, storage location (`users/{uid}.bodyProfile` + snapshot copy on `users/{uid}/analyses/{id}.bodyProfile`), and the D-05 weightKg constraint.

**Storage location decision (Claude's discretion → recommended):**
- **Profile of record:** `users/{uid}` document, field `bodyProfile` (single doc, simplest, one onSnapshot). Rules already permit owner read/write (verified `firestore.rules` `users/{uid}/{document=**}`). No rules change.
- **Per-analysis snapshot:** `users/{uid}/analyses/{analysisId}.bodyProfile` (copied at creation in `loading.tsx`). Pipeline reads via existing `get_analysis()` `meta` dict.
- (Alternative `users/{uid}/profile/body` subdoc also works but adds a second collection/subscription for no benefit at this scope.)

## Coach Hook Seam (D-04)

The exact injection point is **`_build_coach_context()` at `backend/functions/pipeline/app.py:738`** (verified). It returns the single dict both Cerebras (`coach_writer.py`) and Gemini (`gemini/coach_writer_v2.py`) writers consume.

**Phase 3 deliverable (seam only):**
```python
# pipeline/app.py _build_coach_context — add a kwarg + a context key.
def _build_coach_context(*, mode, assessments, dim_scores, local_video_path,
                          scene_flags, body_profile: dict | None = None) -> dict:
    return {
        "mode": mode,
        "joints": [...],
        "videoPath": local_video_path,
        "dimensionScores": dim_scores,
        "sceneFlags": scene_flags,
        # Phase 3 (D-04): 자가입력 컨텍스트 훅. Phase 13 LLM 이 소비 (통증부위 회피
        # 언급·경력별 톤 분기). 현 writer 들은 미사용 키 graceful 무시 (B3 정합).
        # weightKg 는 보조 ONLY (D-05) — 점수 산출 경로 진입 금지.
        "bodyProfile": body_profile,  # or None — 미입력 graceful
    }
```
The caller (`_process`, ~line 1813) passes `body_profile=normalize_body_profile(meta.get("bodyProfile"))`. **Existing writers already ignore unknown context keys** (verified comment at `_build_coach_context:750-751`: "Cerebras 는 `context.get('joints')` 만 박제하므로 신규 키 무시 graceful"). So Phase 3 adds the key with zero risk to current behavior; Phase 13 wires actual prompt consumption.

**Result-screen 표기 (D-04):** echo the profile into the analysis result so the result screen can display it. Either (a) `complete_analysis(...)` stores a `bodyProfile` echo on the result, or (b) the result screen reads `users/{uid}.bodyProfile` directly via the hook. **(b) is simpler and live** (no backend change for display) — recommend (b) for the 결과화면 표기, while the snapshot-on-analysis-doc serves the coach pipeline. Final 표기 위치/형식 defers to Figma (Claude's discretion).

## Phase 2 Complementarity (`BodyNormalizationProfile`)

`BodyNormalizationProfile` (Phase 2, `body_normalization.py`) is **video-measured torso-relative ratios** (armScale/legScale/shoulderHipRatio/confidence) — it is NOT the self-input profile. They are **orthogonal and complementary**:
- `BodyNormalizationProfile` = measured geometry → drives体型 normalization scoring (Phase 6).
- `BodyProfile` (this phase) = self-reported context (경력/통증/우세손) → drives **coach narration tone** (Phase 13), NOT scoring.
- **They never merge.** `BodyProfile.heightCm` does NOT feed `BodyNormalizationProfile.estimatedHeightScale` (that scale is a torso-relative heuristic, not absolute cm). Keeping them separate enforces D-05 (height stays 보조). If analysis runs with no `BodyProfile`, `BodyNormalizationProfile` alone is sufficient (SC#4).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Profile persistence | Custom AsyncStorage serialization of the whole profile | Firestore `users/{uid}.bodyProfile` via hook | Firestore already the data layer; survives reinstall; owner-only rules already exist |
| Profile→pipeline transport | New `/profile` HTTP endpoint + Lambda | Snapshot into analysis doc, read via `get_analysis()` meta | Endpoint/Lambda/validation/contract churn for a value the pipeline already reads |
| Defensive read of partial data | Ad-hoc field checks in screens | `normalize()` in the data-source hook | Established convention; one place handles partial/malformed |
| Segmented/chip UI | Native segmented-control library | Pressable rows/wrap with theme tokens | No native build surface; full brand theming |

**Key insight:** In this codebase the "right" amount of code for Phase 3 is small precisely because the analysis-doc-created-client-side pattern + `get_analysis()` meta read + writer-ignores-unknown-keys all already exist. The temptation to build an endpoint or a contract-validated request field is the over-engineering trap.

## Common Pitfalls

### Pitfall 1: Contract drift (editing one of three)
**What goes wrong:** Adding `BodyProfile` to TS but not `models.py`/`contract.md` (or vice-versa) → silent divergence.
**How to avoid:** Single atomic commit touching `analysis.ts` + `models.py` + `docs/contract.md`. Verification step: grep all three for `BodyProfile`/`painAreas` and confirm field parity.
**Warning signs:** Pipeline reads a field the TS never writes, or a chip value the Python doesn't recognize.

### Pitfall 2: Hardcoded theme values
**What goes wrong:** Writing `#FF4B33`, `fontSize: 16`, `padding: 12` directly (forbidden, app/CLAUDE.md).
**How to avoid:** Import from `theme` (`colors.brand`, `typography.caption`, `spacing.cardPadding`, `radius.card`, `layout.inputHeight`). Grep gate: no hex/`fontSize:` literals in new files.

### Pitfall 3: Forcing signup / blocking the analysis
**What goes wrong:** Making the prompt mandatory or routing it as a required step.
**How to avoid:** Gate is bypassable 3 ways; once-flag prevents re-nag; guest anonymous uid is the only identity (no auth gate). Pilot is guest-first (CLAUDE.md §2).

### Pitfall 4: 통증부위 chip list domain accuracy
**What goes wrong:** Generic body-part list not matching pole-sports injury reality (e.g., omitting 손목/어깨 which are the highest-load joints in pole).
**How to avoid:** **Confirm the list against domain sources** — NotebookLM IPSF / `docs/research/폴스포츠-지식.md` / `pole-sports-motion-analysis-techniques.md` (all present, grep-verified). Proposed list (ASSUMED, see Assumptions A1): 어깨(shoulder)·손목(wrist)·허리(lower_back)·무릎(knee)·발목(ankle)·목(neck)·고관절(hip)·팔꿈치(elbow). belle/도메인 confirm in discuss-phase or plan.

### Pitfall 5: weightKg leaking into scoring
**What goes wrong:** Some future code uses `weightKg` as a scoring input (D-05 violation — 분석 단정 근거 금지).
**How to avoid:** (1) code comment on the field + on the context key; (2) `weightKg` only ever appears in `bodyProfile` context dict and 결과화면 표기 — never imported by `dimensions.py`/`kismam.py`/`body_normalizer.py`. Verification: grep scoring modules for `weightKg`/`weight` → must be 0.

### Pitfall 6: Missing/partial profile not graceful
**What goes wrong:** Pipeline or screen crashes when `bodyProfile` is absent or partial.
**How to avoid:** `normalize()` returns all-null/empty on absence; `_build_coach_context` accepts `None`; `_process` proceeds on `BodyNormalizationProfile` alone (SC#4). Test: analysis with no profile completes `done`.

### Pitfall 7: Firestore nested-array on painAreas
**What goes wrong:** Assuming `string[]` is banned (it is not — only **arrays-of-arrays** are). Conversely, nesting `bodyProfile` containing an array inside the analysis-doc's existing array fields would break.
**How to avoid:** `painAreas: string[]` as a top-level field of the `bodyProfile` map is Firestore-legal (array of scalars). Do NOT put `bodyProfile` inside any existing array field. The existing `_validate_flat_dict_no_nested_array` / scoped validators apply to `result.*` reports, not to this top-level profile field — but keep `painAreas` flat-scalar to be safe. `[VERIFIED: firestore-nested-array-flat memory + firestore_admin.py validators]`

## Code Examples

### Numeric input with suffix + range validation (cm)
```typescript
// Source pattern: app/src/app/(tabs)/analyze.tsx (state + Korean error) + RN TextInput docs
const [heightStr, setHeightStr] = useState('');
const heightCm = heightStr === '' ? null : Number(heightStr);
const heightErr = heightCm != null && (heightCm < 90 || heightCm > 250)
  ? '키를 다시 확인해주세요.' : null;
<View style={styles.inputRow}>
  <TextInput
    value={heightStr}
    onChangeText={(t) => setHeightStr(t.replace(/[^0-9]/g, ''))}
    keyboardType="number-pad"
    maxLength={3}
    placeholder="165"
    accessibilityLabel="키, 센티미터"
    style={styles.numInput} // height: layout.inputHeight, border: colors.inputBorder
  />
  <Text style={styles.suffix}>cm</Text>
</View>
{heightErr && <Text style={styles.error}>{heightErr}</Text>} // colors.inputError
```

### Segmented single-select (경력 / 우세손)
```typescript
// Source pattern: analyze.tsx SourceCard a11y (accessibilityRole/State)
function Segmented<T extends string>({ options, value, onChange, label }: {
  options: { value: T; labelKo: string }[]; value: T | null;
  onChange: (v: T) => void; label: string;
}) {
  return (
    <View style={styles.segRow} accessibilityLabel={label}>
      {options.map((o) => {
        const selected = o.value === value;
        return (
          <Pressable key={o.value} onPress={() => onChange(o.value)}
            accessibilityRole="button"
            accessibilityState={{ selected }}
            accessibilityLabel={`${o.labelKo}${selected ? ', 선택됨' : ''}`}
            hitSlop={6}
            style={[styles.seg, selected && styles.segSelected]}>
            <Text style={[styles.segText, selected && styles.segTextSelected]}>{o.labelKo}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}
// styles.segSelected: { backgroundColor: colors.brand }; segTextSelected: { color: colors.textWhite }
```

### Multi-select chips (통증부위)
```typescript
const [pain, setPain] = useState<PainArea[]>([]);
const toggle = (a: PainArea) =>
  setPain((p) => p.includes(a) ? p.filter((x) => x !== a) : [...p, a]);
<View style={styles.chipWrap /* flexDirection:'row', flexWrap:'wrap', gap */}>
  {PAIN_OPTIONS.map((o) => {
    const on = pain.includes(o.value);
    return (
      <Pressable key={o.value} onPress={() => toggle(o.value)}
        accessibilityRole="button" accessibilityState={{ selected: on }}
        accessibilityLabel={`${o.labelKo}${on ? ', 선택됨' : ''}`}
        style={[styles.chip, on && styles.chipOn]}>
        <Text style={[styles.chipText, on && styles.chipTextOn]}>{o.labelKo}</Text>
      </Pressable>
    );
  })}
</View>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Native segmented-control libs for option pickers | Custom themed Pressable rows | ongoing | Avoids native module + theming limits; Expo SDK 56 even ships drop-in but still native-styled |
| App had no form inputs | This phase introduces the first `TextInput` | Phase 3 | Establishes the app's form convention — keep it primitive + token-driven |

**Deprecated/outdated:** none relevant. (App is on Expo SDK 54; SDK 56 exists but the project is pinned to 54 and must not upgrade for this phase — `Expo HAS CHANGED` AGENTS.md warning.)

## Runtime State Inventory

> Not a rename/refactor/migration phase — this is greenfield feature addition. Section included for completeness with explicit "none" findings.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — new `users/{uid}.bodyProfile` field is additive; no existing record carries the old shape. Verified: no `bodyProfile` field exists today (grep of `analysis.ts`/`models.py`). | none |
| Live service config | None — no n8n/Datadog/external service references the profile. Verified: feature is app+Firestore only. | none |
| OS-registered state | None. | none |
| Secrets/env vars | None — no new secret. Firestore config already in `EXPO_PUBLIC_*`. | none |
| Build artifacts | None — no new package → no new build artifact. EAS Build unaffected (no `npm install`). | none |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 통증부위 list = 어깨/손목/허리/무릎/발목/목/고관절/팔꿈치 | Pitfall 4 / Data Contract | Domain-inaccurate chip set; users can't express real pain location. **Confirm against `폴스포츠-지식.md` / NotebookLM IPSF / belle in plan or discuss.** |
| A2 | Figma file `jrdI7kp245HkPfLB0nclsz` may contain a 프로필/편집 frame | §F | Self-interpreted layout diverges from intended design. **Planner must run Figma get_design_context before finalizing form layout.** |
| A3 | once-flag stored in `users/{uid}.bodyProfile.promptDismissedAt` (vs AsyncStorage) | §C | Either works; Firestore = cross-device, AsyncStorage = device-local. Low risk — planner picks. |
| A4 | 결과화면 표기 reads profile live via hook (no backend echo) | §Coach Hook | If Figma demands the snapshot-at-analysis-time value displayed, need the analysis-doc echo instead. Low risk. |
| A5 | Height 90–250 cm / weight 25–200 kg validation ranges | §B | Cosmetic; overly tight ranges could reject valid edge users. Easy to widen. |

## Open Questions

1. **통증부위 정확 목록 (A1)**
   - What we know: pole-sports loads 손목/어깨/허리 heavily; domain docs exist in repo.
   - What's unclear: the exact canonical KO labels + whether to include 손가락/전완 etc.
   - Recommendation: planner greps `docs/research/폴스포츠-지식.md` + NotebookLM IPSF lookup; confirm 6–8 chip list with belle if ambiguous.

2. **Figma profile-edit frame (A2)**
   - What we know: `ui-figma-first` memory mandates Figma over self-interpretation; fileKey known.
   - What's unclear: whether a BodyProfile/마이 편집 frame actually exists in that file.
   - Recommendation: planner runs Figma `get_design_context` on `jrdI7kp245HkPfLB0nclsz` at planning time; fall back to design.md tokens if absent.

3. **결과화면 표기 위치/형식**
   - What we know: D-04 requires display; format is Claude's discretion → Figma.
   - Recommendation: small info row in result.tsx ("키 165cm · 경력 중급 · 통증 어깨") — confirm placement against Figma.

## Environment Availability

> No external tools/services beyond the existing stack. App is RN+Firestore; backend change is a Python kwarg. No new runtime dependency.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| firebase/firestore (client) | profile read/write | ✓ | ^12.13.0 | — |
| @react-native-async-storage/async-storage | optional once-flag | ✓ | 2.2.0 | use Firestore field instead |
| firebase-admin (pipeline read) | get_analysis meta | ✓ | >=6,<7 | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none required.

## Validation Architecture

> nyquist_validation default-enabled (no config override read denying it). Included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework (app) | `tsc --noEmit` via `npm run typecheck` — the only static gate (no JS test runner configured; verified app/CLAUDE.md) |
| Framework (backend) | pytest >=8,<9 (`backend/requirements-dev.txt`), tests under `backend/tests/` |
| Config file (app) | `app/tsconfig.json` (strict) |
| Quick run command (app) | `cd app && npm run typecheck` |
| Quick run command (backend) | `cd backend && python -m pytest tests/ -x -q` |
| Full suite (backend) | `cd backend && python -m pytest tests/` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| BODY-02 | `BodyProfile` 3-way type parity (TS↔Python) | static | `cd app && npm run typecheck` + grep parity | ✅ (typecheck) / ❌ parity grep (Wave 0) |
| BODY-02 | `normalize_body_profile()` handles partial/absent/malformed → None or null fields | unit | `pytest backend/tests/test_body_profile.py -x` | ❌ Wave 0 (new) |
| BODY-02 | pipeline `_build_coach_context` includes `bodyProfile` key, accepts None | unit | `pytest backend/tests/ -k coach_context -x` | ❌ Wave 0 (new) |
| BODY-02 (SC#4) | analysis completes `done` with no profile (graceful) | integration | existing pipeline smoke test path | ✅ (existing) extend |
| BODY-02 (D-05) | `weightKg` absent from scoring modules | grep gate | `! grep -rn "weightKg\|weight_kg" backend/shared/python/sunity_shared/analysis/{dimensions,kismam,body_normalizer}.py` | ✅ (grep) |
| D-06 | app `normalize()` returns graceful on partial profile | unit (manual/typecheck) | typecheck + (no JS runner — assert via review) | ✅ typecheck only |

### Sampling Rate
- **Per task commit:** `npm run typecheck` (app) / `pytest -x -q` (backend touched).
- **Per wave merge:** full `pytest backend/tests/`.
- **Phase gate:** typecheck clean + full backend suite green + D-05 grep gate (0 matches) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `backend/tests/test_body_profile.py` — covers `normalize_body_profile` partial/absent/malformed + coach-context injection (BODY-02, SC#4, D-06).
- [ ] D-05 grep gate wired into verification (weightKg absent from scoring).
- [ ] 3-way parity grep gate (BodyProfile fields present in `analysis.ts` + `models.py` + `contract.md`).
- [ ] (App) No JS test runner exists — UI behavior validated by `tsc` + manual/review. Do NOT introduce Jest this phase (scope creep); rely on typecheck + structured manual checklist.

## Security Domain

> security_enforcement default-enabled. Pole body-profile is low-sensitivity personal data but still PII-adjacent (health-ish: 통증부위). Brief ASVS pass.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Anonymous Firebase Auth already; no new auth |
| V3 Session Management | no | No change |
| V4 Access Control | yes | Firestore rules `users/{uid}/{**}` owner-only (verified) — profile inherits owner isolation. No rules change needed. |
| V5 Input Validation | yes | Client validates ranges (height/weight) + closed-set unions; pipeline defensively normalizes unknown values to None. |
| V6 Cryptography | no | No new secrets/crypto |
| V7/V9 Data Protection | yes (light) | 통증부위 is health-adjacent → keep under owner-only rules, no analytics export, no third-party share. Pilot guest-only. |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Spoofed/garbage profile values written client-side | Tampering | Owner-only rules limit blast radius to own doc; pipeline defensively normalizes (unknown enum → None); no profile value feeds scoring (D-05) so a forged height can't game a score. |
| Cross-user profile read | Info Disclosure | `users/{uid}` rules deny non-owner (verified `firestore.rules`). |
| Health-adjacent PII (통증부위) leakage | Info Disclosure | Stay within owner-scoped Firestore; do not log profile in plaintext analytics; no export. |

## Sources

### Primary (HIGH confidence)
- Codebase direct read (verified this session): `app/src/app/(tabs)/profile.tsx`, `analyze.tsx`, `app/src/app/analysis/loading.tsx` (setDoc:101), `app/src/lib/{userAnalyses,api,firebase}.ts`, `app/src/types/analysis.ts`, `app/src/theme/{index,colors,typography}.ts`, `app/src/components/DimensionDetailModal.tsx`, `backend/shared/python/sunity_shared/{validation,models,firestore_admin}.py`, `backend/functions/{upload-url,pipeline}/app.py` (_build_coach_context:738, get_analysis:1037), `firestore.rules`.
- `app/CLAUDE.md`, `app/AGENTS.md` (Expo SDK 54 pin), root `CLAUDE.md`, `.planning/{ROADMAP,REQUIREMENTS}.md`, `03-CONTEXT.md`.
- Memory: `firestore-nested-array-flat`, `eas-build-gotchas`, `ui-figma-first`, `feedback-analysis-first`.

### Secondary (MEDIUM confidence)
- Expo SDK docs — SegmentedControl/segmented-control (drop-in replacement, native styling tradeoff). `[CITED]`
- React Native `TextInput` `keyboardType` (`number-pad`, iOS no-done-key caveat). `[CITED]`

### Tertiary (LOW confidence)
- WebSearch — RN multi-select / fitness-app optional-onboarding UX convention (general pattern, not Sunity-specific). `[ASSUMED]`

## Metadata

**Confidence breakdown:**
- UI/UX flow: HIGH — derived from verified existing screens (profile/analyze/loading) + existing Modal pattern; only Figma layout is unverified (A2).
- Input components: HIGH — RN primitives are stable; choice to avoid native libs is well-grounded in EAS/theme constraints.
- Integration/contract: HIGH — exact seams (loading.tsx:101 setDoc, get_analysis meta, _build_coach_context:738) read directly.
- 통증부위 domain list: LOW-MEDIUM — proposed but ASSUMED (A1), needs domain confirm.
- Pitfalls: HIGH — grounded in verified project rules (nested-array, theme tokens, guest-first, D-05).

**Research date:** 2026-06-15
**Valid until:** 2026-07-15 (stable — RN/Firestore/contract patterns slow-moving; re-check only if Expo SDK upgraded or contract refactored)
