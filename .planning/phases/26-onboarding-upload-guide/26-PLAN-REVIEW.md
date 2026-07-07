# Phase 26 Plan Review

**Reviewed:** 2026-07-07  
**Reviewer:** Codex direct review (external reviewer/CLI not used)  
**Scope:** `26-01-PLAN.md` through `26-06-PLAN.md`, checked against `26-CONTEXT.md`, `26-UI-SPEC.md`, `26-PATTERNS.md`, and referenced local code.

## Verdict

Phase 26 is mostly well-bounded and the two likely reviewer misunderstandings are handled correctly:

- `not_pole` gate/threshold immutability is intentional and repeatedly protected by plan acceptance gates. This is not a missing backend fix.
- `learningOptIn` is intentionally added as a contract/storage field only. The Phase 22 manifest filter is explicitly flagged as follow-up, so the plan does not falsely claim D-09 is fully enforced downstream.

I found one **HIGH** implementation risk in Plan 02. I would block execution of that task until the plan is amended. The rest are medium/low plan-quality risks.

## Findings

### HIGH-1: Plan 02 under-specifies `result.tsx` fallback removal and can create a React hook-order regression

**Files/lines:**
- `.planning/phases/26-onboarding-upload-guide/26-02-PLAN.md:93-123`
- `app/src/app/analysis/result.tsx:571-584`
- `app/src/app/analysis/result.tsx:586-760` and onward
- `app/src/lib/userAnalyses.ts:351-394`

Plan 02 Task 2 removes `getSimulatedResult` and says `result` should become null when `storedDoc?.result` is absent, then render a Korean missing-result state. The current component is built around a guaranteed non-null `result`: it synthesizes one from `getSimulatedResult()` at `result.tsx:571-584`, then immediately derives `grade`, `cmp`, calls multiple hooks (`useReferenceMotion`, `useAnalysisDoc(prevAnalysisId)`, `useEffect`, many `useMemo`s), and renders a large tree.

If an implementer follows the plan literally and adds an early return after `result` becomes null, the first render can call fewer hooks than the later render where Firestore supplies `result`. That is a classic React "rendered more hooks than during the previous render" failure. `npm --prefix app run typecheck` will not catch it.

**How I would handle it:**

I would amend Plan 02 before execution:

1. Keep `AnalysisResult` as a wrapper that only reads params, `useAnalysisDoc`, body profile fallback state, and handles loading/missing-result UI.
2. Move the current non-null result UI into a child component, e.g. `AnalysisResultContent`, with props `{ result, storedDoc, analysisMode, referenceMotionId, referenceMotionName, bodyProfileSummary }`.
3. Mount `AnalysisResultContent` only when `storedDoc?.result` is non-null. The child always receives a real `AnalysisResult`, so its hook order is stable.
4. Add an acceptance criterion that `result` is not nullable inside `AnalysisResultContent` and that missing-result UI is rendered by the wrapper, not by conditional returns halfway through the old component.

If execution had already started, I would stop and either keep the dev fallback for this phase or do the wrapper/child split in the same patch. I would not accept a simple "return missing state before score render" patch in this 2k-line screen.

### MEDIUM-1: `/analysis/samples` to `/help` route migration is valid but not recorded as a decision

**Files/lines:**
- `.planning/phases/26-onboarding-upload-guide/26-CONTEXT.md:20-24`
- `.planning/phases/26-onboarding-upload-guide/26-UI-SPEC.md:184-190`
- `.planning/phases/26-onboarding-upload-guide/26-PATTERNS.md:18-19`
- `.planning/phases/26-onboarding-upload-guide/26-02-PLAN.md:32-38`
- `.planning/phases/26-onboarding-upload-guide/26-02-PLAN.md:105-112`
- `.planning/phases/26-onboarding-upload-guide/26-03-PLAN.md:136-139`

The context and UI contract describe `analysis/samples.tsx` as the screen to replace. Plan 02 instead creates top-level `/help`, deletes `analysis/samples.tsx`, and Plan 03 redirects the old entry link to `/help`.

This can be a good product decision: `/help` is a clearer permanent route than `/analysis/samples`. The issue is that it is a plan-level deviation from the contract wording, not captured as an explicit D-xx or "planner decision". That invites review churn and can miss stale deep links outside TypeScript.

**How I would handle it:**

I would pick one of two approaches:

- Conservative: keep `app/src/app/analysis/samples.tsx` as a temporary redirect/shim to `/help`, then remove it in a later cleanup.
- Cleaner: amend Plan 02 with an explicit "route migration decision: `/analysis/samples` is deleted, `/help` is canonical" and add a repo-wide verification `rg "/analysis/samples|analysis/samples" app docs .planning` with expected intentional matches only.

Given this is internal Expo routing and typed routes are not enabled, I would not block the phase on it, but I would make the decision explicit before execution.

### MEDIUM-2: Critical privacy/gate behavior is mostly verified by grep, not behavior

**Files/lines:**
- `.planning/phases/26-onboarding-upload-guide/26-03-PLAN.md:96-107`
- `.planning/phases/26-onboarding-upload-guide/26-03-PLAN.md:140-150`
- `.planning/phases/26-onboarding-upload-guide/26-04-PLAN.md:82-93`
- `.planning/phases/26-onboarding-upload-guide/26-06-PLAN.md:111-119`
- `.planning/phases/26-onboarding-upload-guide/26-06-PLAN.md:131-140`

The plan protects key flows with grep checks: `learningOptIn`, `trainingOptIn`, `_talkv_`, `lowQuality: true`, and branch strings. That is useful, but not enough for the two highest-trust paths:

- opt-in default off and mode1 pass-through to Firestore
- `_talkv_` warning priority and lowQuality not_pole priority

Plan 06 has manual verification, which is good, but it comes after implementation and relies on product-owner confirmation rather than a small repeatable guard.

**How I would handle it:**

I would add one focused implementation requirement:

- Extract pure helpers where practical, e.g. `isKakaoCompressedVideoName(source)` and a tiny route-param builder for `trainingOptIn`/`lowQuality`, then test those with the app's existing test approach if available.
- If no app test harness exists, strengthen Plan 06 with explicit simulator/manual transcripts and Firestore evidence screenshots/IDs in `26-06-SUMMARY.md`.

I would not turn this into a backend phase. The current app-only boundary should stay intact.

### LOW-1: `trainingOptIn` param vs `learningOptIn` field naming can confuse future reviewers

**Files/lines:**
- `.planning/phases/26-onboarding-upload-guide/26-03-PLAN.md:34-46`
- `.planning/phases/26-onboarding-upload-guide/26-03-PLAN.md:85-94`
- `.planning/phases/26-onboarding-upload-guide/26-03-PLAN.md:130-138`

The stored contract field is `learningOptIn`, but the route param is `trainingOptIn`. Behavior can still be correct, but this naming split makes reviews and grep-based verification harder.

**How I would handle it:**

I would rename the route param to `learningOptIn` as well, unless there is a strong reason to keep "training". If the split remains, add a one-line comment in `analyze.tsx`, `reference.tsx`, and `loading.tsx`: route param `trainingOptIn` maps to Firestore contract field `learningOptIn`.

### LOW-2: Plan 03 deployment note says JS-only while editing a Python source file

**Files/lines:**
- `.planning/phases/26-onboarding-upload-guide/26-03-PLAN.md:7-13`
- `.planning/phases/26-onboarding-upload-guide/26-03-PLAN.md:55`
- `.planning/phases/26-onboarding-upload-guide/26-03-PLAN.md:85-93`

Plan 03 edits `backend/shared/python/sunity_shared/models.py` as a comment-only contract mirror. That is consistent with the 3-way lockstep rule and does not touch scoring/gate logic, but "JS-only" is imprecise.

**How I would handle it:**

I would change the note to: "App runtime change is OTA-safe; backend Python edit is comment-only contract mirror, no Lambda redeploy." This avoids the appearance that the plan forgot it touches `backend/`.

## Intentional Choices Reviewed

### `not_pole` gate unchanged

I agree with the plan's treatment. `26-CONTEXT.md` explicitly says gate/threshold changes are deferred until pilot measurement. Plans 03, 04, and 06 protect that boundary with backend diff checks, branch-priority checks, and manual verification.

If a reviewer flags "why not fix the gate now?", my answer would be: not in this phase. This phase reduces false user blame by improving capture guidance and failure copy. The backend threshold/torso-scale work is a separate scoring-track decision with higher false-positive risk.

### `learningOptIn` stored now, Phase 22 filter later

I agree with the plan's treatment. Plan 03 is careful: it adds a boolean contract field, records false safely when the param is absent or malformed, and requires the SUMMARY to flag that Phase 22 still needs a `learningOptIn === true` manifest filter.

If a reviewer says D-09 is incomplete, I would classify that as a known deferred enforcement point, not a Phase 26 blocker, provided the SUMMARY flag is actually written and the field is stored consistently.

## Recommended Plan Amendments Before Execution

1. Patch Plan 02 Task 2 to require the `AnalysisResult` wrapper/`AnalysisResultContent` split before removing `getSimulatedResult`.
2. Add an explicit route migration decision for `/analysis/samples` -> `/help`, or keep a redirect shim.
3. Rename `trainingOptIn` route param to `learningOptIn`, or add comments documenting the mapping.
4. Upgrade verification for opt-in and `_talkv_` from grep-only to at least pure-helper tests or recorded manual evidence in `26-06-SUMMARY.md`.

## Final Assessment

I would proceed with Phase 26 after amending HIGH-1. Without that amendment, Plan 02 can turn a UI/content cleanup into a runtime React failure in one of the largest screens in the app. The `not_pole` and `learningOptIn` choices are defensible as written and should be preserved.
