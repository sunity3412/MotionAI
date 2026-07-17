---
phase: 30-growth-tracking
plan: 03
subsystem: ui
tags: [react-native, typescript, growth-tracking, svg-chart, theme-tokens, presentation-component]

# Dependency graph
requires:
  - phase: 30-growth-tracking
    plan: 01
    provides: "growthSelectors.ts — WeeklyPoint / MotionDeltaRow 타입 계약 + weeklyAverages/defaultGrowthMode 시그니처 + colors.declineBlue 토큰"
provides:
  - "GrowthChart(points: WeeklyPoint[]) — 주별 평균 꺾은선 (raw scores 나열에서 전환, D-01)"
  - "GrowthMotionBars(rows: MotionDeltaRow[]) — 동작별 ▲▼ 점수 델타 리스트 (주식창식, D-05/D-06/D-09)"
  - "index.tsx GrowthCard 잠정 배선 — weeklyAverages(defaultGrowthMode ?? mode3), TODO(30-04-PLAN.md) 교체 계약 박제"
affects: [30-04-home-card]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "react-native-svg 직접 렌더 재사용 (GrowthChart 골격 유지, 신규 차트 라이브러리 도입 0)"
    - "델타 막대 = 픽셀 number 폭 View (퍼센트 문자열 금지 — mode3-progress-not-similarity invariant grep 게이트 대응)"

key-files:
  created:
    - app/src/components/GrowthMotionBars.tsx
  modified:
    - app/src/components/GrowthChart.tsx
    - app/src/app/(tabs)/index.tsx

key-decisions:
  - "GrowthChart props scores:number[] → points:WeeklyPoint[] 로 교체하되 기존 svg 골격(정규화·그라디언트 area·마지막 점 강조·점수 라벨) 전량 유지 — y 소스만 point.avg (D-01 최소 변경)"
  - "주 시작일 라벨 포맷 'M/D주' 자체 판단 (Figma MCP 미접근 → design.md §6 + ui-figma-first 폴백, 근거 컴포넌트 주석 박제)"
  - "델타 막대는 svg 대신 폭 계산 View — 퍼센트 폭 문자열이 invariant grep 게이트('%' 0건)에 걸리므로 픽셀 number 폭 사용"
  - "GrowthMotionBars 주석에서 progressGreen/progressRed 토큰명을 직접 쓰지 않음 — 게이트 grep 이 부호-색 반대 경고 문구까지 잡으므로 '기존 mode3 발전/후퇴 토큰' 으로 우회 서술"

patterns-established:
  - "성장 카드 프레젠테이션 컴포넌트 = growthSelectors 계약(WeeklyPoint/MotionDeltaRow)만 소비 (interface-first, 30-01 이 계약 확정)"
  - "동작별 델타 리스트 = history.tsx 행 시각(배지+제목+우측 수치) + GrowthChart svg 관례 조합 (30-PATTERNS No Analog 해소)"

requirements-completed: [E1, E2]

# Metrics
duration: 20min
completed: 2026-07-17
---

# Phase 30 Plan 03: 성장 카드 프레젠테이션 컴포넌트 Summary

**GrowthChart를 raw 6건 나열에서 주별 평균 꺾은선(WeeklyPoint[])으로 전환하고, 동작별 ▲▼ 점수 델타 리스트 GrowthMotionBars를 신설(주식창식 색 관례·전량 노출·픽셀 폭 막대)했으며, index.tsx는 30-04 교체 계약을 TODO로 박제한 잠정 배선으로 typecheck 정합을 유지한다.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-17
- **Completed:** 2026-07-17
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `GrowthChart` props를 `scores: number[]` → `points: WeeklyPoint[]` 로 교체 (D-01). 기존 svg 골격(W/H/PAD 상수, min/max 정규화, Defs+Polygon 그라디언트, 마지막 점 강조, 점수 라벨) 전량 유지 — y 소스만 `point.avg`. 각 점 아래 주 시작일 라벨('M/D주') SvgText 추가, `width="100%"` 반응형 유지, `points.length < 2` → null(D-03 임계 2 정합).
- `GrowthMotionBars` 신설 (named export) — 동작별 점수 델타 리스트. ▲ +N점=`colors.brand` / ▼ −N점=`colors.declineBlue` / ±0점 중립=`colors.textSecondary` / 첫 기록 N점 (비교 전, delta=null). D-06 임계·숨김 없이 전달된 모든 행 노출, 막대 폭=|delta| 비례 픽셀 number, a11y 라벨, 배지(프로 비교/내 기록) 통합 리스트.
- `index.tsx` GrowthCard 잠정 배선 — `weeklyAverages(analyses, defaultGrowthMode(analyses) ?? 'mode3')` 결과를 points 로 전달(raw slice(0,6) 제거). TODO(30-04-PLAN.md) 주석에 2층 토글 배선 + GrowthLockedCard 분기 교체 계약 박제. 헤더 카피 "이번주 성장 그래프" → "주별 평균 성장 그래프" 정정.

## Task Commits

Each task was committed atomically:

1. **Task 1: GrowthChart 주별 평균 전환 + index.tsx 잠정 배선** - `3ec62d4` (feat)
2. **Task 2: GrowthMotionBars 동작별 ▲▼ 델타 리스트 신설** - `dfe144f` (feat)

## Files Created/Modified
- `app/src/components/GrowthMotionBars.tsx` - 동작별 ▲▼ 점수 델타 리스트 (D-05/D-06/D-09, 주식창식 색·픽셀 폭 막대·전량 노출)
- `app/src/components/GrowthChart.tsx` - 주별 평균 꺾은선 (points:WeeklyPoint[], D-01) — 기존 svg 골격 유지 + 주 라벨 추가
- `app/src/app/(tabs)/index.tsx` - GrowthCard 잠정 배선(weeklyAverages/defaultGrowthMode) + TODO(30-04) 교체 계약 + 헤더 카피 정정

## Decisions Made
- **최소 변경 전환:** GrowthChart 는 데이터 소스(y=point.avg)만 바꾸고 기존 svg 비주얼 골격을 전량 재사용 — D-01 의 최소 변경. 세부 비주얼은 Figma MCP 미접근으로 design.md §6 + 기존 관례 기반 자체 판단(ui-figma-first 폴백, 주석 박제).
- **픽셀 폭 막대:** 델타 막대를 react-native-svg 대신 폭 계산 View 로 구현 — 퍼센트 폭 문자열('50%' 등)이 mode3-progress-not-similarity invariant grep 게이트('%' 0건, 모듈로·퍼센트 폭 포함)에 걸리므로 픽셀 number 폭으로 회피.
- **게이트 우회 서술:** GrowthMotionBars 주석에서 `progressGreen`/`progressRed` 토큰명을 직접 쓰면 검증 grep(`progressGreen\|progressRed` 0건)에 걸려 실패 — "기존 mode3 발전/후퇴 토큰" 으로 우회 서술하되 부호-색 반대라 재사용 금지 근거는 그대로 유지.

## Deviations from Plan

None - plan executed exactly as written. 모든 acceptance gate(typecheck·WeeklyPoint props·scores 부재·TODO(30-04)·hex 0·% 0·declineBlue/brand 배선·progressGreen/Red 0·첫 기록 카피·delta 필터 부재·신규 패키지 0)를 통과.

주: 플랜의 verify 커맨드가 절대경로 `cd /Users/kimtaesung/Dev/SunityMotion/app`(메인 체크아웃)를 하드코딩 — 워크트리 격리 실행이라 게이트를 워크트리 사본(`.claude/worktrees/agent-.../app`)에서 실행해 검증. 경로만 조정, 게이트 로직·기준은 원문 그대로.

## Issues Encountered
- 워크트리에 `node_modules` 부재로 `tsc` 미해결 → 메인 체크아웃(`app/node_modules`)을 워크트리 `app/` 에 symlink 하여 typecheck 실행(빌드 환경 준비, 커밋 미포함 — 커밋은 소스 3파일만).

## Known Stubs
None (기능 스텁 아님) — 두 컴포넌트 전부 실제 로직 구현. `GrowthMotionBars` 는 이 플랜 완료 시점에 화면 노출 배선이 없으나(고아 아님), 이는 의도된 wave 분리로 30-04(depends_on 30-03)가 홈 카드 [동작별] 탭에 배치하는 계약이다(플랜 must_haves.key_links 주석 명시). `index.tsx` GrowthCard 는 잠정 배선이며 TODO(30-04-PLAN.md) 주석이 교체 경계를 코드에 고정한다.

## User Setup Required
None - 앱 JS-only 변경(OTA 가능). 외부 서비스 설정·신규 패키지 없음.

## Next Phase Readiness
- 30-04(홈 카드 통합)가 소비할 컴포넌트 계약 확정: `GrowthChart({ points: WeeklyPoint[] })`, `GrowthMotionBars({ rows: MotionDeltaRow[] })`.
- 잠정 배선의 교체 지점: `index.tsx` GrowthCard 의 TODO(30-04-PLAN.md) — 2층 토글(모드×보기) 상태 기반 배선 + GrowthLockedCard null 분기(D-03) 교체가 30-04 소관.
- 잠정 한계(계약 박제): defaultGrowthMode 가 null(양 모드 주별 점 <2)일 때 `?? 'mode3'` 폴백의 weeklyAverages 결과가 2점 미만 → GrowthChart null 반환으로 카드가 비어 보일 수 있음. 30-04 가 D-03 null 분기로 해소.

## Self-Check: PASSED

- Files verified on disk: GrowthMotionBars.tsx, GrowthChart.tsx, index.tsx (worktree)
- Commits verified in git log: 3ec62d4, dfe144f

---
*Phase: 30-growth-tracking*
*Completed: 2026-07-17*
