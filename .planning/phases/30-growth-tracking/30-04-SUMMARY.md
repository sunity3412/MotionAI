---
phase: 30-growth-tracking
plan: 04
subsystem: ui
tags: [react-native, typescript, growth-tracking, home-card, toggle, theme-tokens]

# Dependency graph
requires:
  - phase: 30-growth-tracking
    plan: 01
    provides: "growthSelectors.ts — weeklyAverages/defaultGrowthMode/motionDeltas + WeeklyPoint/MotionDeltaRow 계약, colors.declineBlue"
  - phase: 30-growth-tracking
    plan: 03
    provides: "GrowthChart(points) 주별 평균 꺾은선 + GrowthMotionBars(rows) 동작별 ▲▼ 리스트 + index.tsx 잠정 배선(TODO(30-04))"
provides:
  - "홈 성장 카드 2층 토글(모드 D-02/D-03 × 보기 D-08/D-09) — E1(주별 평균 추이)/E2(동작별 델타)가 처음 사용자에게 노출"
  - "GrowthLockedCard 게이트를 defaultGrowthMode null 파생으로 교체(D-03 null 분기) + 주별 기준 카피 정정"
  - "phase 30 production OTA 발행 = 오케스트레이터 이월(deferred) + 실기기 확인 6항목 HUMAN-UAT 적립"
affects: [phase-16-studio-terminology]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "성장 카드 소형 세그먼트 토글 = BodyProfileForm Segmented analog 이식(import 대신 복제, 스타일 결합 방지) — 활성 탭 chipSelected 관례(brandTint+brand)"
    - "카드 높이 일정 = GROWTH_CARD_CONTENT_HEIGHT 단일 상수를 추이/동작별/빈상태/locked 본문 minHeight로 공유(하드코딩 높이 금지)"
    - "유효 모드 = modeOverride ?? defaultGrowthMode 파생값 — useState 초기값에 selector를 넣지 않아 async 도착 stale 회피"

key-files:
  created:
    - .planning/phases/30-growth-tracking/30-04-SUMMARY.md
  modified:
    - app/src/app/(tabs)/index.tsx
    - .planning/phases/30-growth-tracking/30-HUMAN-UAT.md

key-decisions:
  - "OTA 발행을 워크트리에서 하지 않고 오케스트레이터 이월 — EAS 인증은 정상이나 워크트리 격리(심링크 node_modules + base 1d0cc2d SHA)라 최종 main 머지 후 발행이 커밋 메타데이터·번들 무결성 측면에서 정확"
  - "홈 헤더 '(평균 N점)' 유지 — 전체 누적 평균은 그래프(D-02 모드 분리)와 역할이 구분되고 삭제 시 정보 손실(D-01 재량 유지 결정, 주석 박제)"
  - "[동작별] 표시 상한 MOTION_ROW_CAP=4 — 카드 높이 폭주 방지, motionDeltas 결과 slice만(델타·평균 재계산 없음)"

patterns-established:
  - "홈 성장 카드는 growthSelectors(집계)/GrowthChart·GrowthMotionBars(표시) 계약만 소비 — index.tsx에서 델타·평균·'%' 재계산 없음(invariant는 하위 층 게이트가 담당)"

requirements-completed: [E1, E2]

# Metrics
duration: 18min
completed: 2026-07-17
---

# Phase 30 Plan 04: 홈 성장 카드 2층 토글 (E1/E2 사용자 노출) Summary

**홈 성장 카드를 [추이]/[동작별] 보기 × 프로 비교/내 기록 모드의 2층 토글로 재작업해 30-01 selector·30-03 컴포넌트를 실제 화면에 배선하고(고아 해소), GrowthLockedCard 게이트를 defaultGrowthMode null 파생으로 교체하며 라벨을 주별 평균 기준으로 정정 — E1/E2가 처음 사용자에게 노출된다. OTA 발행은 최종 main 머지 후 정확성을 위해 오케스트레이터로 이월.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-07-17
- **Completed:** 2026-07-17
- **Tasks:** 2
- **Files modified:** 2 (0 created, 2 modified) + SUMMARY

## Accomplishments
- `index.tsx` GrowthCard 2층 토글 재작업 (D-02/D-03/D-08/D-09): 보기 토글 [추이]/[동작별] + 모드 토글 프로 비교/내 기록(=[추이]에만 노출, D-09). 소형 `GrowthToggle<T>` helper를 BodyProfileForm Segmented analog로 이식(import 대신 복제 — 스타일 결합 방지). 활성 탭 = chipSelected 관례(colors.brandTint bg + colors.brand border/text), a11y 세트(Role/State/Label + hitSlop) 포함.
- 상태 설계(D-03): `view`(trend/byMotion) + `modeOverride`(AnalysisMode|null). 유효 모드 = `modeOverride ?? defaultGrowthMode(analyses)` 파생 — useState 초기값에 selector를 넣지 않아 analyses 비동기 도착 stale 회피. 사용자가 명시 선택한 모드의 주별 점 2개 미만이면 빈 차트 대신 안내 카피(같은 높이).
- 보기 배선(D-08/D-09): [추이]=`weeklyAverages(analyses, effectiveMode)`→GrowthChart, [동작별]=`motionDeltas(analyses).slice(0, 4)`→GrowthMotionBars(모드 토글 숨김). 30-03 잠정 배선(`?? 'mode3'` + TODO(30-04)) 완전 소거 — 30-03이 남긴 고아 GrowthMotionBars가 [동작별] 탭에서 실렌더로 해소.
- 카드 높이 일정(MEDIUM-1): `GROWTH_CARD_CONTENT_HEIGHT=152` 단일 상수를 추이/동작별/빈상태 본문(growthBody minHeight)과 GrowthLockedCard(growthLocked minHeight)가 공유 — 서로 다른 하드코딩 높이 없음.
- 라벨 정정(D-01): 헤더는 30-03이 이미 "주별 평균 성장 그래프"로 정정("이번주 성장 그래프" 0건 유지). GrowthLockedCard 카피는 주별 기준 불일치("분석을 2번 이상 하면" = 같은 주 2건이면 점 1개)를 "서로 다른 주에 분석을 2번 이상 하면 성장 그래프가 보여요"로 정정(D-03 null 분기).
- 렌더 게이트 교체(D-03 null): `analyses.length >= 2`(hasGrowth) → `defaultGrowthMode(analyses) !== null` 파생(useMemo). 양쪽 모드 다 주별 점 2개 미만이면 locked.
- 홈 헤더 "(평균 N점)" 유지 결정 + 근거 주석 박제(전체 누적 평균은 그래프와 역할 구분, D-01 재량).
- 30-HUMAN-UAT.md에 OTA 이월 ops 노트 + 실기기 확인 6항목 append (30-02 기존 항목 무손상).

## Task Commits

Each task was committed atomically:

1. **Task 1: GrowthCard 2층 토글 + GrowthMotionBars 배선 + locked 분기 + 라벨 정정** - `5f970ea` (feat)
2. **Task 2: OTA 오케스트레이터 이월 + 실기기 확인 항목 HUMAN-UAT 적립** - `00fb5d7` (docs)

## Files Created/Modified
- `app/src/app/(tabs)/index.tsx` - GrowthCard 2층 토글(모드×보기) + GrowthToggle helper + GrowthChart/GrowthMotionBars 배선 + GrowthLockedCard null 게이트 + GROWTH_CARD_CONTENT_HEIGHT 상수 + 헤더 유지 주석 (D-01/D-02/D-03/D-08/D-09)
- `.planning/phases/30-growth-tracking/30-HUMAN-UAT.md` - Plan 30-04 OTA 이월 ops 노트 + 실기기 확인 6항목 (batch UAT 적립)

## Decisions Made
- **OTA 오케스트레이터 이월:** EAS 인증은 정상(`whoami` → sunity3412)이나 워크트리 격리 실행이라 발행을 워크트리에서 하지 않는다 — (1) `app/node_modules`가 메인 심링크(번들 무결성), (2) 워크트리 HEAD SHA(base 1d0cc2d + 30-04)가 오케스트레이터의 최종 wave 3 머지 커밋과 달라 EAS update가 잘못된 커밋 메타데이터로 발행될 위험. 최종 main에서 발행하는 것이 정확(parallel_execution deferred-to-orchestrator 경로).
- **홈 헤더 유지:** averageScore "(평균 N점)"은 전체 누적(모드 혼합)이라 그래프(D-02 모드 분리)와 성격이 다르고, 헤더는 "전체 누적" 맥락이라 역할이 구분됨 — 삭제 시 정보 손실이라 유지(D-01 재량).
- **동작별 표시 상한 4:** motionDeltas 결과를 slice(0,4)만 함(재계산 없음) — 카드 높이 폭주 방지, 최신 활동순 상위. 상한은 Claude 재량(30-CONTEXT).
- **[동작별]도 locked에 묶는 단순 규칙:** defaultGrowthMode null(양 모드 주별 점 <2)이면 [동작별] 데이터만 있어도 locked — 추이가 기본 보기이고 파일럿 데이터 규모에서 분기 복잡도가 비용 대비 낮음(플랜 명시 규칙).

## Deviations from Plan

None - plan executed exactly as written. 모든 acceptance gate(typecheck·key_links 4종 grep·TODO(30-04) 0·"이번주 성장 그래프" 0·GROWTH_CARD_CONTENT_HEIGHT≥2·신규 라인 hex 0·a11y 세트·모드토글 [동작별] 숨김·locked null 게이트) 통과.

주 1: 플랜 Task 1 verify 커맨드가 절대경로 `cd /Users/kimtaesung/Dev/SunityMotion/app`(메인 체크아웃)를 하드코딩 — 워크트리 격리 실행이라 게이트를 워크트리 사본(`.claude/worktrees/agent-.../app`)에서 실행해 검증(30-03과 동일 방식). 경로만 조정, 게이트 로직·기준은 원문 그대로.

주 2: Task 2 OTA 발행은 실행하지 않고 오케스트레이터 이월(위 Decisions) — 플랜 acceptance "발행 불가 시 SUMMARY deviation + 30-HUMAN-UAT.md 보류 사유 기록" 경로 충족(deferred-to-orchestrator).

## Issues Encountered
- 워크트리 진입 시 HEAD가 30-01/30-03 커밋을 포함하지 않는 다른 라인(bcc56fb)에 있어 의존 파일(growthSelectors.ts/GrowthMotionBars.tsx) 부재 → worktree_branch_check의 base(1d0cc2d, "wave 2 마감")로 `git reset --hard` 후 의존 파일 확보(정상 절차).
- 워크트리에 `node_modules` 부재 → 메인 체크아웃 `app/node_modules`를 워크트리 `app/`에 symlink하여 typecheck 실행(빌드 환경 준비, 커밋 미포함 — 반환 전 제거).

## Known Stubs
None - GrowthCard가 실제 selector/컴포넌트 계약을 소비해 E1/E2가 화면 렌더된다. 30-03이 남긴 GrowthMotionBars 고아 상태가 [동작별] 탭 실렌더로 해소됨. mode3 인식 동작명 방출 필드(D-04 백엔드)는 30-02 스코프(별도 plan) — 현 motionDeltas는 mode3를 '내 기록' 단일 그룹 처리(legacy 폴백 정합).

## Threat Flags
None - 신규 네트워크 엔드포인트·인증 경로·파일 접근·스키마 변경 없음. 홈 카드 문자열 렌더는 T-30-08 mitigate 그대로(RN `<Text>` inert, referenceMotionName 등은 GrowthMotionBars numberOfLines 경유 — index.tsx에서 raw 조립 없음). T-30-09 mitigate: effectiveMode·명시 선택 점 부족·motionDeltas 빈 배열 전 조합에서 빈 화면/예외 없는 분기 명시(GrowthLockedCard / 동일 높이 안내 카피).

## User Setup Required
None - 앱 JS-only 변경(OTA 가능). OTA 발행은 오케스트레이터가 최종 main 머지 후 메인 체크아웃에서 수행(30-HUMAN-UAT.md ops 노트 명령 박제).

## Next Phase Readiness
- E1/E2 사용자 노출 완료 — 30-01/30-03 산출물 고아 해소. Phase 30의 사용자 노출 층 종결.
- OTA 발행 = 오케스트레이터 대기(wave 3 머지 후). Pod 재가동 시 D-04 백엔드 방출 필드(30-02)가 git pull로 반영되면 [동작별] mode3 그룹핑이 학원 명칭 카테고리 체계(Phase 16)로 확장 가능.

---
*Phase: 30-growth-tracking*
*Completed: 2026-07-17*
