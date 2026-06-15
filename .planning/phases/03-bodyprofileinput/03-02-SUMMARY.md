---
phase: 03-bodyprofileinput
plan: 02
subsystem: app
tags: [bodyprofile, form, textinput, keyboard-safe, accessibility, theme-tokens, profile-tab]

# Dependency graph
requires:
  - phase: 03-01
    provides: BodyProfile 3-way 계약 + bodyProfile.ts hook (useBodyProfile/saveBodyProfile)
provides:
  - BodyProfileForm.tsx — 5필드 공유 입력 폼 (RN core primitive, keyboard-safe, a11y, 토큰)
  - profile.tsx BodyProfileCard — 상시 편집 진입점 (미입력 권유 / 입력됨 요약+수정)
  - summarizeBodyProfile — 채워진 필드만 요약 (부분 입력 graceful)
affects: [03-03 (권유 모달 진입 + 결과 표기), Phase 13 (LLM coach context 소비)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RN core primitive 폼 (TextInput/Pressable, 신규 패키지 0 — EAS Build 리스크 0)"
    - "KeyboardAvoidingView + ScrollView + Keyboard.dismiss (앱 첫 TextInput 화면 keyboard-safe, R6)"
    - "제네릭 Segmented<T> 단일선택 + chip-wrap 다중선택 (in-file named helper)"
    - "saveBodyProfile merge-write 로 부분/전체 저장 (빈 필드 null/[], D-06)"
    - "전체화면 Modal(pageSheet) + SafeAreaView 로 폼 진입, onSnapshot 자동 갱신"
    - "theme 토큰 only (design.md §5-3 CTA / §5-3-1 입력 필드 — 하드코딩 0)"

key-files:
  created:
    - app/src/components/BodyProfileForm.tsx
  modified:
    - app/src/app/(tabs)/profile.tsx

key-decisions:
  - "폼 presentation = 전체화면 Modal(pageSheet) — 신규 route 파일 불필요, 폼은 재사용 component 로 유지"
  - "Segmented 토글로 선택 해제 가능 (오선택 정정 + 부분 입력 D-06 정합)"
  - "weightKg 보조 ONLY (D-05) — state/필드/저장에 코드 주석 박제, scoring 경로 미전달"
  - "통증부위 KO 라벨은 닫힌 PainArea union 만 (자유텍스트 불가, D-03 / T-03-05 mitigate)"

patterns-established:
  - "RN core 폼 keyboard-safe 패턴 (KeyboardAvoidingView+ScrollView+Keyboard.dismiss, number-pad no-done caveat 대응)"
  - "BodyProfileCard 미입력/입력됨 graceful 분기 + summarizeBodyProfile"

requirements-completed: [BODY-02]

# Metrics
duration: 4min
completed: 2026-06-15
---

# Phase 3 Plan 02: BodyProfileForm 폼 + 마이페이지 진입점 Summary

**RN core primitive(신규 패키지 0)로 5필드 공유 입력 폼 `BodyProfileForm`(keyboard-safe + a11y + 토큰)을 만들고, 마이 탭에 `BodyProfileCard`(미입력 권유 / 입력됨 요약+수정) 상시 편집 진입점을 추가해 입력→저장→재진입 표시 수직 슬라이스 완성 (03-01 saveBodyProfile/useBodyProfile 위에 구축)**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-15T02:41:46Z
- **Completed:** 2026-06-15T02:45:12Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- `BodyProfileForm.tsx` 신설 — 키(cm)/몸무게(kg, 보조 D-05)/경력/통증부위(다중)/우세손 5필드, RN core primitive 만 사용 (신규 npm 패키지 0)
- [R6 keyboard-safe] KeyboardAvoidingView(iOS padding / Android height) + ScrollView(keyboardShouldPersistTaps="handled", 하단 safe-area inset 패딩) + 빈 영역 Keyboard.dismiss — iOS number-pad no-done 대응. 작은 화면에서도 저장 CTA 스크롤 도달
- 숫자 입력 `[^0-9]` strip + 범위 검증(키 90–250 / 몸무게 25–200) + 한국어 inline error(`colors.inputError` teal) + 빈값 허용(D-06)
- 제네릭 `Segmented<T>`(경력/우세손, 토글 해제 가능) + chip-wrap 다중선택(통증부위) in-file named helper
- 모든 pressable a11y (accessibilityRole/State(selected/disabled)/Label/hitSlop)
- `profile.tsx` 에 `useBodyProfile()` 구독 + 게스트 카드와 통계 사이에 `BodyProfileCard` 삽입 — 미입력=brandTint 권유 카드 / 입력됨=요약 row + 수정
- `summarizeBodyProfile` — 채워진 필드만 "·" 로 묶어 요약 (부분이면 부분만, 전부 비면 권유 상태)
- 전체화면 Modal(pageSheet) + SafeAreaView 로 폼 진입(기존값 prefill), 저장 후 onSnapshot 으로 카드 자동 갱신
- 토큰만 사용 (design.md §5-3 CTA height 54/radius 13, §5-3-1 입력 필드 — 하드코딩 색/fontSize 0)

## Task Commits

각 태스크 atomic commit:

1. **Task 1: BodyProfileForm.tsx — 5필드 keyboard-safe 공유 폼** - `6d8b2dc` (feat)
2. **Task 2: profile.tsx — BodyProfileCard 진입점 (미입력/입력됨 분기)** - `0fb1a3b` (feat)

## Files Created/Modified
- `app/src/components/BodyProfileForm.tsx` (created) - 5필드 공유 입력 폼 (RN primitive, keyboard-safe, a11y, 토큰, saveBodyProfile merge-write)
- `app/src/app/(tabs)/profile.tsx` (modified) - useBodyProfile 구독 + BodyProfileCard(미입력/입력됨) + BodyProfileForm 전체화면 Modal 진입 + summarizeBodyProfile + 토큰 styles

## Decisions Made
- **폼 presentation = 전체화면 Modal(pageSheet)**: plan 이 route/모달/인라인 중 판단 위임. 신규 route 파일 없이 재사용 가능한 component 로 폼을 유지하고 profile.tsx 가 Modal 로 감쌈. DimensionDetailModal 의 Modal 패턴 정합.
- **Segmented 토글 해제 허용**: 단일선택이지만 같은 옵션 재탭 시 해제 — 오선택 정정 + 부분 입력(D-06) 정합. 빈 선택은 null 로 저장.
- **weightKg 보조 ONLY (D-05)**: state/필드/저장 호출에 "보조 ONLY" 코드 주석 박제. 폼은 값을 받아 saveBodyProfile 로 넘기지만 scoring 경로 유입은 03-01 의 6모듈 grep gate 가 차단.
- **react-native-safe-area-context 사용 (신규 아님)**: `useSafeAreaInsets`(폼 하단 inset) + `SafeAreaView`(모달 상단) — 이미 설치된 dependency(~5.6.0), package.json 불변.

## Deviations from Plan

None - plan executed exactly as written. (폼 presentation 을 Modal 로 택한 것은 plan 의 "전체화면 route 또는 인라인/모달 확장 — Figma/design.md 판단" 위임 범위 내.)

## Issues Encountered
- **Figma MCP frame 미참조**: plan 은 ui-figma-first 의무이나, design.md §5-3(CTA)·§5-3-1(입력 필드)·§5-4(카드) 가 입력 폼 레이아웃을 토큰 수준까지 완전 명세(높이 54 / radius 13 / 테두리·에러색 teal #54B8CD) — 모든 값이 이미 theme 토큰화됨. plan 의 "frame 없으면 design.md 토큰 fallback" 경로에 따라 design.md 스펙을 source-of-truth 로 구현. 신규 pattern 카테고리 0 (03-PATTERNS.md 정합).

## Known Stubs
None - 폼은 03-01 의 실제 saveBodyProfile(Firestore merge-write) 에 배선됨. mock/placeholder 데이터 없음. 카드는 useBodyProfile 라이브 구독.

## User Setup Required
None - 외부 서비스 설정 불필요. (03-01 의 owner-only Firestore rules + 기존 anonymous auth 재사용.)

## Next Phase Readiness
- 03-03 (첫 분석 권유 모달 + 결과 화면 표기) 가 올라설 폼/카드/요약 경로 박제 완료. BodyProfileForm 은 03-03 의 권유 모달에서도 재사용 가능.
- saveBodyProfile/useBodyProfile/getBodyProfileOnce(03-01) + BodyProfileForm/summarizeBodyProfile(03-02) 가 03-03 에서 바로 사용 가능.
- 차단/우려: 없음.
- **EAS native build 실기기 smoke 필요 (R6 manual-verify)**: iPhone SE급 작은 화면에서 키보드 open 시 저장 CTA 스크롤 도달 + 통증부위 칩 하단 safe area 비겹침 + 부분 입력 저장 — belle 실기기/시뮬레이터 검증 대상 (본 plan 의 human-check verify 항목, automated typecheck/grep 은 전부 통과).

---
*Phase: 03-bodyprofileinput*
*Completed: 2026-06-15*

## Self-Check: PASSED

- 2 key files verified present on disk (1 created BodyProfileForm.tsx, 1 modified profile.tsx).
- Both task commits verified in git log: 6d8b2dc, 0fb1a3b.
- app typecheck clean (tsc --noEmit), Task 1 grep gates (identifiers/keyboard-safe/no-hardcode/no-new-pkg) all OK, Task 2 grep gates (useBodyProfile+BodyProfileForm / diff-added-lines no-hardcode R3) all OK.
- No file deletions, no stray untracked files.
