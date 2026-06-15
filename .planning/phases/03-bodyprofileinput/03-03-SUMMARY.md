---
phase: 03-bodyprofileinput
plan: 03
subsystem: app
tags: [bodyprofile, prompt-gate, state-machine, modal, snapshot, result-screen, guest-first]

# Dependency graph
requires:
  - phase: 03-01
    provides: BodyProfile 계약 + bodyProfile.ts hook (useBodyProfile/dismissBodyProfilePrompt) + AnalysisDoc.bodyProfile snapshot 필드
  - phase: 03-02
    provides: BodyProfileForm.tsx (권유 모달 입력하기 진입에서 재사용)
provides:
  - BodyProfilePromptModal.tsx — dismissible 3-way 첫분석 권유 bottom-sheet (DimensionDetailModal 패턴)
  - analyze.tsx pendingPicked 게이트 상태머신 (pick → maybePromptBeforeRoute → continuePendingRoute 4-경로 단일 수렴)
  - result.tsx BodyProfile snapshot 표기 (storedDoc.bodyProfile, live fallback for old docs)
  - useBodyProfile 가 promptDismissedAt once-flag 노출 (normalizer all-empty→null 우회)
affects: [Phase 13 (LLM coach context bodyProfile 소비)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pendingPicked 상태머신 — pick 후 라우팅 보류, 모달 결과 4-경로(입력완료/건너뛰기/백드롭/native back) 모두 continuePendingRoute 단일 수렴 (stale closure/영상 유실 방지, R2)"
    - "dismissible 3-way bottom-sheet (버튼+백드롭+onRequestClose 모두 onSkip 수렴, equal-weight CTA, D-06 non-forcing)"
    - "snapshot-source-of-truth 표기 — 결과 화면이 live profile 아닌 storedDoc.bodyProfile snapshot 우선 (R1 재현성), old-doc 만 live fallback"
    - "once-flag 노출 — normalizer 가 all-empty→null 로 접어 유실되는 promptDismissedAt 을 raw 에서 별도 read"

key-files:
  created:
    - app/src/components/BodyProfilePromptModal.tsx
  modified:
    - app/src/app/(tabs)/analyze.tsx
    - app/src/app/analysis/result.tsx
    - app/src/lib/bodyProfile.ts

key-decisions:
  - "useBodyProfile 가 promptDismissedAt 추가 반환 — 게이트가 once-flag 를 정확히 읽어야 하는데 normalizeBodyProfile 은 all-empty→null 로 접어 미입력+dismiss 상태에서 flag 유실 (Rule 3 blocking fix)"
  - "[입력하기] 진입 폼 = 전체화면 Modal(pageSheet) — profile.tsx 와 동일 패턴, BodyProfileForm 재사용 (폼 로직 중복 0)"
  - "onSaved/onClose/native-back 모두 continuePendingRoute — 입력 도중 닫아도 보류된 영상으로 분석 재개 (영상 유실 0)"
  - "result.tsx 요약에서 weightKg 제외 — 보조 ONLY (D-05), 점수 경로 무관 + 표기 노이즈 방지"

patterns-established:
  - "pendingPicked 게이트 상태머신 + 4-경로 단일 수렴점 (R2)"
  - "snapshot-우선 표기 + live fallback (R1 재현성)"

requirements-completed: [BODY-02]

# Metrics
duration: 5min
completed: 2026-06-15
---

# Phase 3 Plan 03: 첫분석 권유 게이트 + 결과 snapshot 표기 Summary

**첫 분석 직전 1회 dismissible 권유 모달(`BodyProfilePromptModal`)을 만들고, analyze.tsx 의 pick→route 사이에 `pendingPicked` 상태머신 게이트(미입력 AND 미dismiss → 영상 보류 + 모달)를 두어 모달 결과 4-경로를 단일 `continuePendingRoute` 로 수렴시키며, result.tsx 가 live 프로필이 아닌 `storedDoc.bodyProfile` SNAPSHOT 을 source-of-truth 로 표기 — 게스트 강제 0(SC#4 graceful) + 재현성(R1) 닫음**

## Performance
- **Duration:** ~5 min
- **Started:** 2026-06-15T02:48:57Z
- **Completed:** 2026-06-15T02:53:46Z
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- `BodyProfilePromptModal.tsx` 신설 — dismissible 3-way bottom-sheet(건너뛰기 버튼 + 백드롭 Pressable + native back onRequestClose 모두 onSkip 수렴), 두 equal-weight CTA([입력하기] brand / [건너뛰기] secondary 정식 버튼), `accessibilityViewIsModal` + a11y, 토큰만(하드코딩 0)
- analyze.tsx `pendingPicked` + `promptVisible` + `formVisible` 상태머신 — `handleResult` 가 `routeAfterPick` 직접 호출 대신 `maybePromptBeforeRoute` 경유
- `maybePromptBeforeRoute`: 미입력(profile===null) AND 미dismiss(promptDismissedAt==null) → picked 보류 + 모달 / 그 외 즉시 routeAfterPick (게스트 우선, SC#4 graceful)
- `continuePendingRoute`: 입력완료/건너뛰기/백드롭/native back 4-경로 단일 수렴 — 보류된 picked 캡처 후 동일 영상으로 라우팅 재개(stale closure/영상 유실 방지, R2)
- `skipPrompt`: dismissBodyProfilePrompt(once-flag) 후 continuePendingRoute — 재권유 0 (D-06), 저장 실패해도 분석 안 막음(graceful)
- [입력하기] → BodyProfileForm 전체화면 Modal(pageSheet) 진입(03-02 재사용), onSaved/onClose 모두 continuePendingRoute
- result.tsx `storedDoc.bodyProfile` SNAPSHOT 우선 표기(분석-당시 값 재현, R1), snapshot 없는 구 doc 만 live useBodyProfile fallback, 미입력이면 row 생략(graceful), weightKg 요약 제외(D-05)
- bodyProfile.ts `useBodyProfile` 가 `promptDismissedAt` 추가 반환 — normalizer 가 all-empty→null 로 접어 유실되는 once-flag 를 raw 에서 별도 read

## Task Commits
각 태스크 atomic commit:

1. **Task 1: BodyProfilePromptModal.tsx — dismissible 첫분석 권유 시트** - `0143b30` (feat)
2. **Task 2: analyze.tsx pendingPicked 게이트 + result.tsx snapshot 표기** - `483c801` (feat)

## Files Created/Modified
- `app/src/components/BodyProfilePromptModal.tsx` (created) - dismissible 3-way bottom-sheet, equal-weight CTA, accessibilityViewIsModal, 토큰만
- `app/src/app/(tabs)/analyze.tsx` (modified) - pendingPicked 상태머신 게이트 + maybePromptBeforeRoute/continuePendingRoute/skipPrompt + 모달/폼 wiring
- `app/src/app/analysis/result.tsx` (modified) - storedDoc.bodyProfile snapshot 요약 row(live fallback, graceful 생략) + summarizeBodyProfile + 토큰 styles
- `app/src/lib/bodyProfile.ts` (modified) - useBodyProfile 가 promptDismissedAt once-flag 노출 (게이트 판별용)

## Decisions Made
- **useBodyProfile 가 promptDismissedAt 노출** (Rule 3 blocking fix): plan 게이트 조건이 `!profile?.promptDismissedAt` 을 가정했으나, 03-01 의 `normalizeBodyProfile` 은 measurement 5필드만 반환하고 all-empty 면 전체 null 을 반환한다. 즉 미입력 상태에서 dismiss 하면 normalize 가 null 이 되어 once-flag 가 유실 → 모달이 매번 재출현. 게이트가 정확히 동작하려면 once-flag 를 별도로 읽어야 하므로 `useBodyProfile` 반환에 `promptDismissedAt: number | null` 을 추가하고 raw 스냅샷에서 직접 read. profile.tsx 는 `{ profile }` 만 구조분해하므로 영향 없음(추가 필드 무시).
- **[입력하기] 폼 = 전체화면 Modal(pageSheet)**: 03-02 profile.tsx 와 동일 패턴 재사용. 신규 route 파일 0, BodyProfileForm 폼 로직 중복 0 (plan "BodyProfileForm 재사용, 폼 로직 중복 금지" 정합).
- **result.tsx 요약에서 weightKg 제외**: 보조 ONLY(D-05) 라 점수 경로 무관 + 표기 노이즈 방지. 키/경력/우세손/통증부위만 요약.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] useBodyProfile 가 promptDismissedAt 미노출 → 게이트 once-flag 판별 불가**
- **Found during:** Task 2 (게이트 조건 구현 중)
- **Issue:** plan 게이트 조건 `!profile?.promptDismissedAt` 은 useBodyProfile 의 normalized profile 에 promptDismissedAt 이 있다고 가정. 그러나 03-01 `normalizeBodyProfile` 은 (a) promptDismissedAt 을 반환값에서 제외하고 (b) measurement 5필드가 전부 비면 전체 null 반환. 따라서 미입력 게스트가 한 번 dismiss 해도 profile===null + promptDismissedAt 접근 불가 → 게이트가 매 분석마다 모달 재출현 (D-06 재권유 0 위반).
- **Fix:** `useBodyProfile` 반환 타입에 `promptDismissedAt: number | null` 추가, raw 스냅샷(`raw?.promptDismissedAt`)에서 직접 read. 게이트는 `profile === null && promptDismissedAt == null` 로 정확히 "미입력 AND 미dismiss" 판별.
- **Files modified:** app/src/lib/bodyProfile.ts
- **Commit:** 483c801

## Issues Encountered
- **pre-existing 회귀 (out-of-scope, NOT fixed)**: 03-01 SUMMARY 가 기록한 backend phase08 Gemini default-model stale test + spike/smoke collection error 는 본 plan(앱 UI 전용, backend 무변경)과 무관. SCOPE BOUNDARY 규칙에 따라 미수정.

## Known Stubs
None - 게이트는 03-01 실제 dismissBodyProfilePrompt(Firestore merge-write) + useBodyProfile 라이브 구독에 배선. result.tsx 는 실제 storedDoc.bodyProfile snapshot 소비. mock/placeholder 0.

## User Setup Required
None - 외부 서비스 설정 불필요 (기존 anonymous auth + owner-only Firestore rules 재사용, 신규 native 패키지 0).

## Next Phase Readiness
- Phase 3 자가입력 수직 슬라이스 3 wave 완료: 계약/저장(03-01) → 폼/카드(03-02) → 권유 게이트/결과 표기(03-03).
- Phase 13 LLM 이 coach context 의 bodyProfile 키(통증부위 회피·경력별 톤) 소비 가능 (현재 graceful 무시).
- **EAS native build 실기기 smoke 필요 (manual-verify)**: 첫 분석 게스트로 영상 pick → 권유 모달 1회 출현 / 건너뛰기 후 재pick 시 모달 미출현(once-flag) / [입력하기]→폼 저장 후 분석 자동 재개 / 백드롭·native back dismiss / 결과 화면 snapshot row 표기 — belle 실기기/시뮬 검증 대상 (automated typecheck/grep 전부 통과).
- 차단/우려: 없음.

---
*Phase: 03-bodyprofileinput*
*Completed: 2026-06-15*

## Self-Check: PASSED

- Created file verified on disk: app/src/components/BodyProfilePromptModal.tsx.
- SUMMARY verified on disk: .planning/phases/03-bodyprofileinput/03-03-SUMMARY.md.
- Both task commits verified in git log: 0143b30, 483c801.
- app typecheck clean (tsc --noEmit). Task 1 gates (identifiers/accessibilityViewIsModal/onRequestClose/no-hardcode) PASS. Task 2 gates (analyze identifiers / result identifiers / diff-added-line no-hardcode R3 / #FF4B33 comments preserved / no package.json change) PASS.
