---
phase: 26-onboarding-upload-guide
plan: 01
subsystem: ui
tags: [expo-router, async-storage, onboarding, tutorial, react-native]

requires:
  - phase: existing app foundation
    provides: index.tsx onAuthStateChanged 게스트 진입 라우팅, result.tsx AsyncStorage 선례
provides:
  - 첫 실행 1회 기대설정 튜토리얼 화면 (스와이프 + 건너뛰기 + 시작하기)
  - onboarding.ts 첫 실행 플래그 helper (hasSeenTutorial / markTutorialSeen)
  - index.tsx 첫 실행 감지 라우팅 분기 (미시청 → /tutorial)
affects: [26-02, 26-03, 26-06, FAQ 재진입 화면(이용방법/FAQ S2)]

tech-stack:
  added: []
  patterns:
    - "AsyncStorage 로컬 1회성 플래그를 src/lib helper 로 격리 (@sunity: prefix, 양방향 graceful)"
    - "RN 코어 ScrollView horizontal pagingEnabled 페이저 + onMomentumScrollEnd dot index (신규 의존성 0)"
    - "종료 단일 수렴 finish() — canGoBack 분기로 첫실행(replace)/재진입(push) 모두 자연 복귀"

key-files:
  created:
    - app/src/lib/onboarding.ts
    - app/src/app/tutorial.tsx
  modified:
    - app/src/app/index.tsx

key-decisions:
  - "hasSeenTutorial 읽기 실패 시 true 반환 — 홈 진입 차단·재노출 루프 방지 (graceful 방향='본 것으로 간주', T-26-02)"
  - "튜토리얼 페이저는 RN 코어 ScrollView 로 자작 — 신규 라이브러리 도입 0 (OTA 배포 가능)"
  - "finish() 단일 수렴 + canGoBack 분기 — 첫 실행은 홈 replace, FAQ 재진입은 back"

patterns-established:
  - "온보딩 로컬 플래그 helper: @sunity: prefix + try/catch graceful, 화면은 lib 경유"
  - "풀스크린 스와이프 온보딩: pagingEnabled + useWindowDimensions width + CTA 자리 예약(레이아웃 점프 방지)"

requirements-completed: [ONBD-01]

duration: 18min
completed: 2026-07-07
---

# Phase 26 Plan 01: 온보딩·기대설정 튜토리얼 Summary

**첫 실행 게스트에게 1회 노출되는 기대설정 스와이프 튜토리얼 + AsyncStorage 첫 실행 감지 라우팅 (신규 의존성 0, OTA 배포 가능)**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-07-07
- **Completed:** 2026-07-07
- **Tasks:** 2
- **Files modified:** 3 (신규 2 / 수정 1)

## Accomplishments
- `onboarding.ts` — 첫 실행 1회 플래그 helper. `hasSeenTutorial()`(읽기 실패 시 graceful true), `markTutorialSeen()`(fire-and-forget). `@sunity:tutorial_seen` 키로 Firebase Auth backing store 충돌 회피.
- `index.tsx` — `onAuthStateChanged` 라우팅에 첫 실행 분기 추가. 미시청 게스트 → `/tutorial`, 시청 완료/재실행 → `/(tabs)`. 기존 bootstrapping 깜빡임 방지 패턴 유지.
- `tutorial.tsx` — 기대설정 3슬라이드(무엇을 측정/강사 보조 포지셔닝/원본 촬영 안내) 스와이프 화면. dot 인디케이터 + 우상단 건너뛰기 + 마지막 슬라이드 시작하기 CTA. `finish()` 단일 수렴으로 스킵/완료 모두 `markTutorialSeen()` 후 canGoBack 분기 복귀.

## Task Commits

1. **Task 1: onboarding.ts 플래그 helper + index.tsx 라우팅 분기** - `51ac1ce` (feat)
2. **Task 2: tutorial.tsx 스와이프 튜토리얼 화면** - `7a44ae2` (feat)

## Files Created/Modified
- `app/src/lib/onboarding.ts` (신규) — 첫 실행 1회 플래그 read/write helper (graceful)
- `app/src/app/tutorial.tsx` (신규) — 기대설정 스와이프 튜토리얼 화면
- `app/src/app/index.tsx` (수정) — 미시청 게스트 → /tutorial 라우팅 분기

## Decisions Made
- **읽기 실패 graceful 방향 = true**: `hasSeenTutorial()` 의 AsyncStorage 읽기가 실패하면 "본 것으로 간주"해 홈으로 진입시킨다. 읽기 오류가 홈 진입을 막거나 매 실행 튜토리얼 재노출 루프를 만드는 것이 더 나쁜 UX이기 때문 (T-26-02 mitigate).
- **페이저 자작**: 코드베이스에 pagingEnabled 페이저 무존재. UI-SPEC Registry Safety 준수로 RN 코어 ScrollView 로 자작 — 신규 의존성 0, package.json diff 0 (OTA 안전).
- **CTA 자리 예약**: 비마지막 슬라이드에 `ctaPlaceholder`(동일 높이 View)를 렌더해 마지막 슬라이드 전환 시 레이아웃 점프를 막음.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Figma MCP 미접근 (서브에이전트 툴셋 제약)**: 실행 에이전트 툴셋에 Figma MCP(`get_metadata`/`get_screenshot`)가 노출되지 않아 튜토리얼 프레임을 직접 조회하지 못함. 플랜의 명시적 fallback("Figma 카피가 있으면 그대로, 없으면 (1)측정 범위 (2)강사 보조 (3)원본 촬영 안내")에 따라 26-UI-SPEC S1 **구조 계약**(스와이프+dot+건너뛰기+시작하기 CTA)과 기대설정 카피로 구현. 비주얼 최종 정합(슬라이드 수/카피/레이아웃)은 26-06 checkpoint 에서 belle 육안 확인 예정 — 이때 Figma 실물과 차이가 있으면 카피/슬라이드만 조정하면 되며 구조·라우팅은 계약 충족.
- **worktree node_modules 부재**: 타입체크(`tsc`) 실행을 위해 메인 체크아웃 `app/node_modules` 를 worktree 에 임시 symlink 후 typecheck(EXIT 0) 확인, 완료 후 symlink 제거. 커밋에 미포함(개별 `git add` 로 스테이징).

## User Setup Required
None - no external service configuration required. JS-only 변경 (native 모듈 추가 0), OTA(expo-updates) 배포 가능.

## Next Phase Readiness
- 첫 실행 라우팅·플래그 기반 확보 — S2(이용방법/FAQ)에서 `튜토리얼 다시 보기` 재진입 시 `/tutorial` push 하면 finish() 의 canGoBack 분기로 자연 복귀 (재진입 경로 검증됨).
- 튜토리얼 비주얼 belle 확인은 26-06 checkpoint 에서 일괄 수행 (verification 명시).
- 슬라이드 카피는 Figma 확정 시 교체 여지 — 구조/라우팅 불변.

## Threat Flags

None — 신규 네트워크/인증/스키마 surface 없음. AsyncStorage 로컬 플래그는 threat register T-26-01(accept)/T-26-02(mitigate 충족) 범위 내.

---
*Phase: 26-onboarding-upload-guide*
*Completed: 2026-07-07*
