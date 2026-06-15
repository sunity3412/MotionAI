---
phase: 03-bodyprofileinput
verified: 2026-06-15T03:30:00Z
status: human_needed
score: 4/4 roadmap success criteria verified (6/6 plan must-have truths verified)
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  note: "Initial goal-backward verification. 03-REVIEW.md (code review) ran prior but is advisory, not a verifier run."
human_verification:
  - test: "iPhone SE급 작은 화면(시뮬레이터 또는 실기기)에서 마이 → 내 몸 정보 입력 → 5필드 모두 탭하여 키보드 open 상태에서 저장 CTA 가 가려지지 않고 스크롤로 도달·탭 가능, 통증부위 칩이 하단 safe area 와 겹치지 않음. 부분 입력 저장도 성공."
    expected: "키보드가 떠도 저장 CTA 가 접근 가능하고 칩이 안전 영역을 침범하지 않음. 부분 입력 저장 성공 후 카드가 요약 갱신."
    why_human: "키보드 레이아웃·safe-area 겹침은 실제 디바이스 렌더에서만 확인 가능 (R6, 03-02 PLAN human-check 항목)."
  - test: "첫 분석 게스트로 영상 pick → 권유 모달 1회 출현. [건너뛰기]/백드롭/native back 으로 dismiss 후 재pick 시 모달 미출현(once-flag). [입력하기]→폼 저장 후 동일 영상으로 분석 자동 재개. 결과 화면에 BodyProfile snapshot row 표기."
    expected: "권유 모달이 분석을 막지 않고 4-경로 모두 보류된 영상으로 분석을 재개. once-flag 후 재권유 없음. 결과 화면이 분석-당시 입력값을 표기."
    why_human: "모달 출현/dismiss 타이밍, pendingPicked 라우팅 재개, once-flag 영속, snapshot 표기는 실제 분석 플로우 실행으로만 확인 가능 (R2/R1, 03-02·03-03 PLAN human-check 항목)."
  - test: "CR-01 회귀 — 프로필을 이미 입력한 사용자가 콜드스타트(앱 첫 진입 직후) 또는 느린 네트워크 상태에서 영상을 pick 했을 때 권유 모달이 잘못 뜨는지 확인."
    expected: "이상적: 기존 프로필 사용자에게는 모달이 뜨지 않아야 함. 현재 코드는 loading 플래그를 게이트에서 무시하므로 로딩 중 pick 시 모달이 잘못 뜰 수 있음 (CR-01)."
    why_human: "타이밍 의존 race (구독 미완료 시점 pick)는 실기기에서 재현 확인이 필요. WARNING으로 분류 — 폴리시 결정(게스트 우선 통과 vs 게이트 보강) 필요."
---

# Phase 3: 자가입력 BodyProfileInput Verification Report

**Phase Goal:** 사용자가 키·몸무게·경력·통증부위·우세손을 앱에서 1회 입력하고, 분석에 BodyProfile이 함께 전달된다 (영상으로 단정 불가한 항목 보조)
**Verified:** 2026-06-15T03:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

> Note: ROADMAP marks this phase `Mode: mvp`, but the phase Goal is a feature-statement with explicit numbered Success Criteria (not an "As a... I want... so that..." User Story). Verification proceeds against the 4 ROADMAP Success Criteria (the binding contract) plus the 6+4+5 PLAN must-have truths, using standard goal-backward methodology.

## Goal Achievement

### Observable Truths — ROADMAP Success Criteria (binding contract)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| SC1 | 마이페이지 또는 첫 분석 직전 화면에서 키·몸무게·경력·통증부위·우세손을 입력할 수 있다 | ✓ VERIFIED | `BodyProfileForm.tsx` renders 5 real controls: NumberField(키, 키:203), NumberField(몸무게, 키:214), Segmented(경력, 키:218), Segmented(우세손, 키:227), chip multi-select(통증부위, 키:240). Entry points: `profile.tsx` BodyProfileCard (full-screen Modal, 키:175) + `analyze.tsx` prompt [입력하기]→form (formVisible state, 키:68). Not stubs — interactive + save CTA wired. |
| SC2 | 입력값이 Firestore에 저장되고 분석 요청 시 백엔드로 전달된다 | ✓ VERIFIED | Save: `saveBodyProfile` merge-write to `users/{uid}.bodyProfile` (bodyProfile.ts:168-178), called from form (키:147). Backend pass-through traced E2E: loading.tsx `getBodyProfileOnce()` → snapshot to analysis doc (loading.tsx:108,120) → userAnalyses `normalizeBodyProfile(raw.bodyProfile)` preserves (userAnalyses.ts:231) → pipeline `meta.get("bodyProfile")` → `models.normalize_body_profile` → `body_profile=` kwarg into `_build_coach_context` which emits `"bodyProfile"` key (app.py:745,784,1828). |
| SC3 | weightKg는 보조 정보로만 사용되고 분석 단정 근거로 쓰이지 않는다 (코드 주석 + 사용처 제한) | ✓ VERIFIED | D-05 grep gate: `weightKg|weight_kg` returns 0 matches across all 6 scoring-consumer modules (dimensions/kismam/body_normalization/body_normalizer/force_signals/force_pattern, exit code 1 = no match). Code comments present in bodyProfile.ts:68, BodyProfileForm.tsx:100,149, contract.md:402, result.tsx (excluded from summary). |
| SC4 | 미입력 사용자도 분석이 graceful하게 진행된다 | ✓ VERIFIED | Dual normalize never throws: `normalizeBodyProfile` returns null on all-empty/invalid (bodyProfile.ts:62-96); `normalize_body_profile` returns None graceful (models.py:83). loading.tsx snapshot conditional `...(bodyProfile ? { bodyProfile } : {})` (키:120). pipeline emits `"bodyProfile": None` when absent (app.py:784). 17/17 backend tests GREEN incl. coach-context-with-None. Gate routes through when not gating (analyze.tsx:150). |

**Score: 4/4 ROADMAP Success Criteria VERIFIED**

### Observable Truths — PLAN must-have truths (additive detail)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 01-1 | BodyProfile 3-way lockstep (TS·Python·contract.md) | ✓ VERIFIED | analysis.ts:19-42 (3 unions + interface), models.py:48-118 (3 const tuples + normalizer), contract.md:386-425 (field table + storage). Identical field set. |
| 01-2 | 미입력/부분/잘못된 bodyProfile graceful | ✓ VERIFIED | 17 backend tests pass (None/{}/partial/bad-enum/range/non-string filter). |
| 01-3 | bodyProfile snapshot→pipeline meta→coach context thin E2E | ✓ VERIFIED | Full chain traced (see SC2). |
| 01-4 | snapshot 보존 → 결과 화면 분석-당시 값 read (R1) | ✓ VERIFIED | userAnalyses.ts:231 preserves; result.tsx:434 reads `storedDoc?.bodyProfile`. |
| 01-5 | loading.tsx getBodyProfileOnce (raw spread 아님, R5) | ✓ VERIFIED | loading.tsx:108 `getBodyProfileOnce()`, not raw getDoc spread. |
| 01-6 | weightKg scoring 미유입 (D-05/R4) | ✓ VERIFIED | 6-module grep gate 0 matches. |
| 02-1 | 5필드 입력·저장 (SC#1) | ✓ VERIFIED | BodyProfileForm 5 controls + saveBodyProfile. |
| 02-2 | Firestore 저장 (SC#2) | ✓ VERIFIED | saveBodyProfile merge-write. |
| 02-3 | 부분입력 graceful + 카드 요약/미입력 표시 | ✓ VERIFIED | summarizeBodyProfile (profile.tsx:64), Segmented toggle-clear, empty→null. |
| 02-4 | 작은 화면 keyboard-safe CTA (R6) | ? UNCERTAIN | KeyboardAvoidingView+ScrollView+insets present (BodyProfileForm.tsx:163-191) but layout-on-device only confirmable by human → human_verification. |
| 03-1 | 첫 분석 dismissible 권유 모달 1회 (D-01) | ✓ VERIFIED (artifact) / ? device-behavior | Modal artifact wired; CR-01 affects misfire-on-load (see Anti-Patterns) → human check. |
| 03-2 | 3-way dismiss + once-flag 재권유 0 (D-06) | ✓ VERIFIED | onRequestClose/backdrop/button all→onSkip (modal:30,37,59); skipPrompt→dismissBodyProfilePrompt (analyze.tsx:164). |
| 03-3 | 프로필 있으면 게이트 통과, 미입력 graceful (SC#4) | ⚠️ PARTIAL | Logic present (analyze.tsx:142-151) BUT `loading` flag ignored → CR-01 race (see below). Steady-state correct; cold-start can misfire. |
| 03-4 | pendingPicked 라우팅 보류/재개 4-경로 수렴 (R2) | ✓ VERIFIED | continuePendingRoute single sink (analyze.tsx:155-161), 4 paths converge. |
| 03-5 | result.tsx storedDoc.bodyProfile SNAPSHOT 표기 (R1) | ✓ VERIFIED | result.tsx:434 snapshot-first, summary row 673-680. |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app/src/types/analysis.ts` | BodyProfile interface + 3 unions + AnalysisDoc.bodyProfile | ✓ VERIFIED | interface @34, unions @19-22, AnalysisDoc.bodyProfile @337 |
| `backend/shared/.../models.py` | constants + normalize_body_profile | ✓ VERIFIED | @48-51, @83; 17 tests cover |
| `docs/contract.md` | BodyProfile section | ✓ VERIFIED | §"BodyProfile (자가입력)" @386 |
| `app/src/lib/bodyProfile.ts` | hook + normalizer + getBodyProfileOnce + save + dismiss | ✓ VERIFIED | all 5 exports present, substantive |
| `app/src/lib/userAnalyses.ts` | snapshot preserve | ✓ VERIFIED | @231 normalizeBodyProfile |
| `backend/tests/test_body_profile.py` | normalize + coach-context tests | ✓ VERIFIED | 17 passed |
| `app/src/components/BodyProfileForm.tsx` | 5-field form, keyboard-safe, a11y, tokens | ✓ VERIFIED | 435 lines, all 5 controls, KAV+ScrollView, accessibilityState |
| `app/src/app/(tabs)/profile.tsx` | BodyProfileCard entry | ✓ VERIFIED | useBodyProfile @78, form Modal @175 |
| `app/src/components/BodyProfilePromptModal.tsx` | dismissible 3-way sheet | ✓ VERIFIED | 118 lines, accessibilityViewIsModal, onRequestClose |
| `app/src/app/(tabs)/analyze.tsx` | pendingPicked gate state machine | ⚠️ ORPHANED-flag | Gate present but ignores `loading` (CR-01) |
| `app/src/app/analysis/result.tsx` | snapshot display | ✓ VERIFIED | @434 snapshot-first, summary row |
| `app/src/app/analysis/loading.tsx` | snapshot-at-creation | ✓ VERIFIED | @108 getBodyProfileOnce, @120 conditional spread |

### Key Link Verification

| From | To | Via | Status |
| ---- | -- | --- | ------ |
| loading.tsx | analysis doc .bodyProfile | getBodyProfileOnce() → setDoc spread | ✓ WIRED (loading.tsx:108,120) |
| userAnalyses normalize | AnalysisDoc.bodyProfile | normalizeBodyProfile(raw.bodyProfile) | ✓ WIRED (userAnalyses.ts:231) |
| pipeline _process | _build_coach_context body_profile | normalize_body_profile(meta.get('bodyProfile')) | ✓ WIRED (app.py:1828→745→784) |
| BodyProfileForm | saveBodyProfile | save CTA onPress merge-write | ✓ WIRED (BodyProfileForm.tsx:147) |
| profile.tsx card | BodyProfileForm | tab→form Modal | ✓ WIRED (profile.tsx:175) |
| analyze.tsx pick | BodyProfilePromptModal | gate: profile null AND !dismissed | ⚠️ PARTIAL (gate ignores loading — CR-01) |
| PromptModal dismiss | dismissBodyProfilePrompt → continuePendingRoute | once-flag + resume | ✓ WIRED (analyze.tsx:164-171) |
| result.tsx | storedDoc.bodyProfile | useAnalysisDoc().doc.bodyProfile | ✓ WIRED (result.tsx:434) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| profile.tsx BodyProfileCard | profile | useBodyProfile() → Firestore onSnapshot users/{uid} | ✓ real Firestore subscription | ✓ FLOWING |
| result.tsx summary row | bodyProfileSnapshot | storedDoc.bodyProfile (useAnalysisDoc Firestore) | ✓ real analysis doc snapshot | ✓ FLOWING |
| pipeline coach context | body_profile | meta.get('bodyProfile') from get_analysis Firestore | ✓ real meta read | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| normalize_body_profile graceful (all cases) | `pytest tests/test_body_profile.py -q` | 17 passed in 0.29s | ✓ PASS |
| App contract typechecks (3-way TS side) | `npm run typecheck` | clean (tsc --noEmit) | ✓ PASS |
| D-05 weightKg gate (6 scoring modules) | `grep -rnE "weightKg|weight_kg" <6 modules>` | exit 1, 0 matches | ✓ PASS |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` declared for this app/UI phase. (Backend logic covered by pytest spot-check above.)

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| BODY-02 | 03-01, 03-02, 03-03 | 키·몸무게·경력·통증부위·우세손 1회 입력 + 분석에 BodyProfile 전달, weightKg 보조-only, 유연성·근력 미입력 | ✓ SATISFIED | All 4 ROADMAP SC verified above. REQUIREMENTS.md:31 marked [x], :156 Phase 3 Complete. No orphaned requirement IDs (BODY-02 is the only ID mapped to Phase 3 and all 3 plans claim it). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| analyze.tsx | 65,142-151 | Gate destructures `{profile, promptDismissedAt}`, ignores `loading` from useBodyProfile() | ⚠️ Warning (CR-01) | During async profile load both are null → existing-profile/already-dismissed user can be wrongly prompted on cold start / slow network. Does NOT block input or analysis; affects only the optional dismissible nudge. |
| result.tsx | 958 | `userName={undefined /* TODO: Firebase displayName */}` | ℹ️ Info | Pre-existing from Phase 12.5 (commit e968074, 2026-06-07) — NOT introduced by Phase 3. Not attributable. |
| BodyProfileForm.tsx | 200,211,305 | `placeholder="예: 165"` etc. | ℹ️ Info | Legitimate TextInput placeholder props (UI hints), not stubs. |
| models.py | 244,261,283 | "placeholder" comments | ℹ️ Info | Phase 8 forward-declare comments, unrelated to Phase 3. |

No Phase-3-introduced TBD/FIXME/XXX debt markers. No hardcoded theme values in phase files (verified by PLAN grep gates + spot review). Firestore nested-array discipline respected (flat painAreas scalar array).

### Human Verification Required

See `human_verification` in frontmatter. Three items:
1. **R6 keyboard-safe form on small screen** — device layout only.
2. **First-analysis prompt flow E2E** — modal once-flag, pendingPicked resume, snapshot display.
3. **CR-01 race regression** — does an existing-profile user get wrongly prompted on cold start? (WARNING — policy decision needed.)

### Gaps Summary

No BLOCKER gaps. All 4 ROADMAP Success Criteria are observably achieved in the codebase: the 5-field form exists and is wired to Firestore (SC1, SC2), the BodyProfile is passed end-to-end to the pipeline coach context with dual graceful normalization (SC2, SC4), and weightKg is provably excluded from all 6 scoring modules (SC3). 17 backend tests pass, typecheck clean.

**CR-01 (code-review BLOCKER) is assessed as a WARNING, not a goal-blocker.** The phase GOAL is "user inputs profile once AND BodyProfile is passed to analysis." CR-01 is a load-race in the *optional, dismissible* first-analysis prompt — a convenience nudge that, by design, must never block analysis (guest-first, SC4). The defect causes the nudge to *over-show* (wrongly prompt an existing-profile user during async load), which is a UX-polish correctness issue, not a failure of input capture, Firestore persistence, backend pass-through, or graceful degradation. The always-available marquee entry point (마이페이지 BodyProfileCard) is unaffected, and the prompt's own dismiss path routes analysis through regardless. The fix is small (gate on `loading`), but it does not gate phase goal achievement.

Status is **human_needed** (not passed) because three behaviors require device/runtime confirmation that grep cannot verify (keyboard layout, full prompt flow, CR-01 race reproduction). All automated checks pass.

---

_Verified: 2026-06-15T03:30:00Z_
_Verifier: Claude (gsd-verifier)_
