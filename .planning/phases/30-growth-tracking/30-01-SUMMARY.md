---
phase: 30-growth-tracking
plan: 01
subsystem: ui
tags: [react-native, typescript, growth-tracking, pure-functions, selectors, theme-tokens]

# Dependency graph
requires:
  - phase: 29-mode3-result-screen-completion
    provides: "result.tsx scoreSuppressed 점수카드 숨김 기준 (isScoreSuppressed) — HIGH-1 홈 지표 제외 정합의 소스"
  - phase: 28-dtw-motion-based-alignment
    provides: "alignmentWarp.ts 순수 selector 모듈 골격 (헤더 순수성 선언 + 방어적 소비)"
provides:
  - "growthSelectors.ts — 주별 평균(weeklyAverages)·기본 모드 폴백(defaultGrowthMode)·동작별 점수 델타(motionDeltas) 순수 selector"
  - "hasUsableGrowthScore predicate — 성장 지표 단일 자격 관문 (scoreSuppressed 제외, HIGH-1)"
  - "WeeklyPoint / MotionDeltaRow 타입 계약 (30-03/30-04 소비)"
  - "colors.declineBlue 테마 토큰 — 하락 ▼ 표시 (D-06)"
  - "assert-growth-selectors.mjs — selector 시맨틱 테스트 (신규 devDep 0)"
affects: [30-03-component, 30-04-home-card, phase-16-studio-terminology]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "순수 함수 selector 모듈 (alignmentWarp.ts analog) — react/데이터소스 의존 0, tsc + Node assert 로만 검증"
    - "Node 24 내장 타입 스트리핑으로 .ts 직접 import 하는 .mjs 시맨틱 테스트 (신규 프레임워크·devDep 0)"

key-files:
  created:
    - app/src/lib/growthSelectors.ts
    - app/scripts/assert-growth-selectors.mjs
  modified:
    - app/src/theme/colors.ts

key-decisions:
  - "hasUsableGrowthScore 를 유일한 집계 자격 관문으로 두어 3 selector 전부 경유 (중복 자격 필터 없음) — HIGH-1 신뢰 계약을 단일 지점에서 강제"
  - "createdAt Firestore Timestamp 변환 헬퍼 미도입 — AnalysisDoc.createdAt 은 이미 number(ms), normalize 가 변환 (계약 확인, 가정 아님)"
  - "declineBlue 는 highlight(#006FFD) alias 신규 토큰 — progressGreen/Red 재사용 금지(D-06 부호-색 반대)"

patterns-established:
  - "성장 집계 selector = 순수 함수 + 타입 계약, 화면(30-03/04)은 계약만 소비 (interface-first)"
  - "선택자 규칙은 fixture 기반 Node assert 로 잠금 — typecheck/grep 이 못 잡는 회귀(모드혼합·폴백·억제 제외·델타 부호) 방지"

requirements-completed: [E1, E2]

# Metrics
duration: 22min
completed: 2026-07-17
---

# Phase 30 Plan 01: 성장 추적 데이터 계층 Summary

**주별 평균·모드 분리·기본 모드 폴백·동작별 점수 델타를 계산하는 순수 selector(growthSelectors.ts) + scoreSuppressed 제외 단일 관문(hasUsableGrowthScore) + ▼ 하락 declineBlue 토큰, Node assert 시맨틱 테스트로 잠금.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-07-17
- **Completed:** 2026-07-17
- **Tasks:** 3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- `growthSelectors.ts` 신설 — 5 named export(weeklyAverages/defaultGrowthMode/motionDeltas/weekStartOf/hasUsableGrowthScore) + WeeklyPoint/MotionDeltaRow 타입 계약. D-01/D-02/D-03/D-05/D-07 규칙 + HIGH-1 suppressed 제외를 타입·주석과 함께 제공.
- HIGH-1 신뢰 계약: hasUsableGrowthScore 단일 관문으로 scoreSuppressed===true 분석이 평균·델타·기본모드 후보에서 전부 제외 — 결과화면에서 숨긴 점수를 홈 성장 지표로 되살리지 않음.
- `colors.declineBlue` 토큰 신설(D-06) — highlight alias, 성장 카드 하락 ▼ 전용. brand #FF4B33 무변경.
- `assert-growth-selectors.mjs` 시맨틱 테스트(HIGH-2) — 신규 devDependency 0, Node 24 타입 스트리핑으로 growthSelectors.ts 직접 import. 28 assert 케이스로 주간 bucket·모드 비혼합·폴백 3분기·억제 제외·그룹핑·정수 point 델타·NaN 방어 검증.

## Task Commits

Each task was committed atomically:

1. **Task 1: growthSelectors.ts 순수 selector** - `0994b65` (feat)
2. **Task 2: colors.ts declineBlue 토큰 (D-06)** - `16dd253` (feat)
3. **Task 3: growthSelectors 시맨틱 테스트 (HIGH-2)** - `23b1a0b` (test)

## Files Created/Modified
- `app/src/lib/growthSelectors.ts` - 주별 평균·기본 모드·동작별 델타 순수 selector + hasUsableGrowthScore predicate (D-01/D-02/D-03/D-05/D-07 + HIGH-1)
- `app/src/theme/colors.ts` - declineBlue: '#006FFD' 하락 표시 토큰 추가 (D-06)
- `app/scripts/assert-growth-selectors.mjs` - fixture 기반 Node assert 시맨틱 테스트

## Decisions Made
- **단일 자격 관문:** weeklyAverages/motionDeltas/defaultGrowthMode 가 전부 hasUsableGrowthScore 를 경유하도록 설계 — suppressed/NaN/비수치/모드불일치 배제를 한 predicate 에서만 정의(HIGH-1 정합, 중복 필터 없음).
- **createdAt 직접 사용:** AnalysisDoc.createdAt 은 계약상 number(epoch ms)이고 userAnalyses.normalize 가 number 로 정규화하므로 Timestamp 변환 헬퍼를 넣지 않음(가정 금지 원칙 하에 계약 확인 후 결정).
- **'%' 부재 게이트 대응:** 월요일 주 버킷은 `getDay()===0 ? 6 : day-1` 로 모듈로 없이 계산, 등락률 퍼센트 산출 없음 — mode3-progress-not-similarity invariant 정합.

## Deviations from Plan

None - plan executed exactly as written. 모든 acceptance gate(typecheck·순수성·% 부재·scoreSuppressed·legacy 필터 부재·assert 실행·devDep 무변경)를 초안 그대로 통과.

## Issues Encountered
- 워크트리에 `node_modules` 부재로 `tsc` 미해결 → 메인 체크아웃(`app/node_modules`)을 워크트리 `app/`에 symlink 하여 typecheck·타입 스트리핑 실행(빌드 환경 준비, 커밋에 미포함).
- `node --experimental-strip-types` 실행 시 MODULE_TYPELESS_PACKAGE_JSON 경고 발생 — 비치명적(ESM 재파싱), 테스트 exit 0 · "growth-selectors semantic checks passed" 정상 출력.

## Known Stubs
None - 3 selector 전부 실제 로직 구현. 30-03/30-04 가 소비할 계약(타입+함수)이 확정됨.

## User Setup Required
None - no external service configuration required. 앱 JS-only 변경(OTA 가능), 백엔드 방출 필드는 이 plan 스코프 밖(후속 plan).

## Next Phase Readiness
- 30-03(컴포넌트)·30-04(홈 카드 통합)가 import 할 타입·함수 계약 확정: WeeklyPoint, MotionDeltaRow, weeklyAverages, defaultGrowthMode, motionDeltas, weekStartOf, hasUsableGrowthScore + colors.declineBlue.
- mode3 인식 동작명 방출 필드(D-04 백엔드 층)는 이 plan 스코프 밖 — 후속 plan(백엔드 3-way lockstep)에서 처리. 현 motionDeltas 는 mode3 를 '내 기록' 단일 그룹으로 처리(legacy 폴백 정합).

## Self-Check: PASSED

- Files verified on disk: growthSelectors.ts, assert-growth-selectors.mjs, colors.ts, 30-01-SUMMARY.md
- Commits verified in git log: 0994b65, 16dd253, 23b1a0b, 4d6f013

---
*Phase: 30-growth-tracking*
*Completed: 2026-07-17*
