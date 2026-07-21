---
phase: 32-result-readability-3-omni
plan: 10
subsystem: ui
tags: [react-native, deduction-card, goal-gauge, mission-badge, drilldown-sheet, injury-safety, translation-layer, d-08, d-09, d-10, d-14, d-15, d-20]

# Dependency graph
requires:
  - phase: 32-06
    provides: "DeductionRecord 확장 8키(recordId·statusLine·whyLine·cueLine·tolerance 등) + Mission 계약"
  - phase: 32-07
    provides: "E2 강조 토큰(typography.ts — badge/bodySm/bodyMd/bodyMdBold/bodyLg, 하한 17)"
  - phase: 32-09
    provides: "프로덕션 실측 doc(recordId·3단 문구·tolerance·mission·summaryPraise 방출) — 32-11 배선 입력"
provides:
  - "DeductionCard — 상태→왜→줌쌍→게이지→행동→미션→물어보기 완결 카드 (props 로컬 타입, 배선 대기)"
  - "gaugeGeometry.computeGaugeGeometry — 규칙 상수(tolerance) 기반 게이지 스케일 순수 함수 + node --test 4건"
  - "GoalGaugeBar — 목표까지 남은 정도를 길이로만 표현, 수치는 소형 배지 1곳(94°→71°), geometry null 시 미표시"
  - "MissionBadge — 오늘의 미션 / mode3 기록 갱신 배지 (게임 프레임 요소)"
  - "DeductionDetailSheet 3단화 + gate ⑤ 참조 원형(회색 근거 박스·확인하기·강사 줄·AI 고지) + 측정 문구 잘림 해소"
  - "InjuryRiskSection 안전 톤 강화 — 혼자 고치지 말고 강사와 함께 보기 코치 유도(D-14, 게임 프레임 0)"
affects: [32-11 (result.tsx 배선 — 카드·시트·게이지 소비), 32-13 (recordId 스팟체크 조인)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "게이지 의미 = 순수 기하 모듈로 분리 정의 + node --test 고정 — 자의 시각 비율 금지(리뷰 HIGH)"
    - "수치 노출 구조 격리 = 게이지 소형 배지 또는 폴백 배지 1곳만(formatGoalBadge 단일 출처) — 헤드라인 수치 0(D-09)"
    - "카드 props 로컬 타입(계약 직접 의존 0) — interface-first, doc→props 매핑은 배선 플랜(32-11) 소관"
    - "줌 이미지 양측 독립 로딩/onError 폴백 — 만료 presigned URL 크래시 0(T-32-23)"

key-files:
  created:
    - app/src/lib/gaugeGeometry.ts
    - app/src/lib/__tests__/gaugeGeometry.test.ts
    - app/src/components/GoalGaugeBar.tsx
    - app/src/components/MissionBadge.tsx
    - app/src/components/DeductionCard.tsx
  modified:
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/components/InjuryRiskSection.tsx

key-decisions:
  - "게이지 스케일 도메인 = [min(current,target)−tolerance, max+tolerance] — tolerance 는 규칙 상수(record.tolerance)만, 부재 시 null(게이지 미표시)로 D-09 자의 수치를 시각 비율로도 재생산 금지"
  - "수치 배지 문자열은 formatGoalBadge 단일 출처 — 게이지 정상 경로(GoalGaugeBar)와 게이지 불가 폴백(DeductionCard)이 동일 문자열('94°→71°')"
  - "줌 두 이미지를 인라인(공용 서브컴포넌트 아님) — 양측 onError 각각 소유(리뷰 반영: 양측 이미지 상태 처리)"
  - "DeductionDetailSheet Props 무변경 — 기존 record.statusLine/whyLine/cueLine 옵셔널 필드만 읽어 result.tsx 무접촉(배선 32-11)"
  - "InjuryRiskSection 은 SafetyFlag[] 소비 유지 + D-14 코치 유도 문구만 강화 — 문구집 safetyEntries 톤과 정합, 게임 프레임 요소 import 0"

patterns-established:
  - "번역 레이어 컴포넌트 = 수치 격리(1곳) + 정직 폴백(게이지 불가/legacy/이미지 실패) + E2 토큰(하한 17, lineHeight 잘림 방지)"

requirements-completed: [D-08, D-09, D-10, D-14, D-15, D-20]

# Metrics
duration: ~50min
completed: 2026-07-21
---

# Phase 32 Plan 10: 감점 카드 번역 레이어 (3단+게이지+미션 완결형) Summary

**감점 카드를 상태→왜→줌쌍→목표 게이지→행동→미션→물어보기의 완결형으로 재구성하고(수치는 게이지 배지 1곳), 게이지 스케일을 규칙 상수(tolerance) 기반 순수 기하로 정의·테스트해 자의 시각 비율을 차단했으며, 드릴다운 시트는 gate ⑤ 참조 원형(회색 근거 박스·강사 줄·AI 고지)으로 3단화하고 위험 결함 카드는 게임 프레임 없는 안전 톤으로 개편 — result.tsx 무접촉, 배선(32-11)만 남김**

## Performance

- **Duration:** ~50 min (컨텍스트 정독 + 구현)
- **Started:** 2026-07-21T13:50:00Z (approx)
- **Completed:** 2026-07-21T14:41:00Z
- **Tasks:** 3 (Task 1 = TDD)
- **Files modified:** 7 (created 5 / modified 2)

## Accomplishments

- **gaugeGeometry (순수 기하 + 테스트):** `computeGaugeGeometry(current, target, tolerance)` 가 도메인 `[min−tol, max+tol]` 선형 위치 4종(ratio/targetRatio/tolBandStart/tolBandEnd)을 산출하고, tolerance 부재(0/음수/비유한)·current/target 비유한이면 `null`(게이지 불가). node --test 4건이 스케일 정의·경계·불가·방향대칭을 고정 — 리뷰 HIGH(자의 시각 비율 금지)를 구조로 강제.
- **GoalGaugeBar:** 목표까지 남은 정도를 트랙 길이·마커로만 표현(D-10 belle 강한 교정 "각도 숫자 확대 금지"), 수치는 소형 배지 1곳(`94°→71°`)에만. geometry null 시 **컴포넌트가 null 반환** → 호출측 폴백. 사용자 노출 문자열에 `%` 0(백분율은 트랙 좌표 계산 내부만).
- **MissionBadge:** `mission`(오늘의 미션)·`record`(mode3 기록 갱신) 두 variant, AccuracyLimitBadge 전형(visible/null/토큰/accessibility). D-10 안 B의 게임 프레임 요소.
- **DeductionCard:** 상태문(수치 0)→이유문→인라인 줌쌍(양측 로딩 placeholder+onError 폴백)→게이지(불가 시 수치 배지 폴백)→행동문(cueLine 부재=fail-closed 강사 유도)→미션 배지(isSafety 제외, D-14)→'강사님께 물어보기'(recordId 조인). props 로컬 타입 — 배선 32-11.
- **DeductionDetailSheet 3단화(D-15):** 상단 3단 + gate ⑤ 참조 원형(회색 "이 원인은 어떻게 측정됐나" 근거 박스=수치 여기만, 확인하기 불릿, terminologyMap 용어줄, 강사 연결 줄, AI 추정 고지 박스). 측정 문구를 bodySm(19/25)로 교체해 **상단 글자 잘림**(구 body 25/lineHeight 21) 해소. 투명 감점 내역 삭제 0(계층화만).
- **InjuryRiskSection 안전 톤(D-14):** "혼자 고치지 말고, 강사와 이 화면을 함께 보세요" 코치 유도 문구를 중립 배경 박스로 노출(추가 amber 경보 아님). 게이지·미션·배지 등 게임 프레임 요소 import 0.

## Task Commits

Each task committed atomically (Task 1 = TDD RED→GREEN→components):

1. **Task 1 (RED): gaugeGeometry 실패 테스트** - `e18427f` (test)
2. **Task 1 (GREEN): gaugeGeometry 구현** - `5bcdccb` (feat)
3. **Task 1 (컴포넌트): GoalGaugeBar + MissionBadge** - `32ebcda` (feat)
4. **Task 2: DeductionCard 완결 카드** - `5f92342` (feat)
5. **Task 3: DeductionDetailSheet 3단화 + InjuryRiskSection 안전 톤** - `82acd60` (feat)

**Plan metadata:** (아래 최종 커밋 — SUMMARY)

## Files Created/Modified

- `app/src/lib/gaugeGeometry.ts` - 게이지 스케일·마커·채움 비율 순수 함수(react 의존 0)
- `app/src/lib/__tests__/gaugeGeometry.test.ts` - node --test 4건(스케일 정의·경계·불가·방향대칭)
- `app/src/components/GoalGaugeBar.tsx` - 실측 단위 목표 게이지(수치 배지 1곳, geometry null 시 null) + formatGoalBadge/unitSymbol export
- `app/src/components/MissionBadge.tsx` - 오늘의 미션·mode3 기록 갱신 배지(variant, visible/null 전형)
- `app/src/components/DeductionCard.tsx` - 3단+인라인 줌+게이지+미션 완결 카드(props 로컬 타입)
- `app/src/components/DeductionDetailSheet.tsx` - 상단 3단 + gate ⑤ 참조 원형 + 측정 문구 잘림 해소(Props 무변경)
- `app/src/components/InjuryRiskSection.tsx` - D-14 코치 유도 문구 + 안전 톤 강화(게임 프레임 0)

## Decisions Made

- **게이지 스케일 = 규칙 상수 기반 도메인만.** tolerance 부재 시 게이지를 그리지 않는다 — D-09가 막으려던 자의 수치를 시각 비율로 재생산하지 않기 위함(리뷰 HIGH). 테스트로 고정.
- **수치 노출 1곳 격리.** `formatGoalBadge` 단일 출처로 게이지 정상 경로와 폴백 경로가 동일 배지 문자열을 렌더 — 헤드라인/전면 수치 0(D-09/D-10).
- **줌 이미지 인라인 2벌.** 공용 서브컴포넌트로 묶지 않고 양측 이미지 각각 onError 소유 — 리뷰의 "양측 이미지 상태 처리" 명시 이행 + 만료 presigned URL 크래시 0(T-32-23).
- **시트 Props 무변경.** 기존 record 옵셔널 필드(statusLine/whyLine/cueLine)만 읽어 result.tsx 무접촉 — 배선은 32-11.
- **InjuryRiskSection 은 계약 무변경.** SafetyFlag[] 소비 유지 + D-14 코치 유도 문구만 강화(문구집 safetyEntries 톤 정합).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] GoalGaugeBar 백분율 스타일 타입 오류**
- **Found during:** Task 1 (GoalGaugeBar typecheck)
- **Issue:** `pctStr` 가 `string` 을 반환해 RN `ViewStyle.left/width`(DimensionValue = `` `${number}%` ``)에 미할당 — tsc TS2769 3건.
- **Fix:** `pctStr` 반환 타입을 `` `${number}%` `` 템플릿 리터럴로 명시(SegmentRow 인라인 백분율 선례와 동형).
- **Files modified:** app/src/components/GoalGaugeBar.tsx
- **Verification:** tsc 0 errors.
- **Committed in:** `32ebcda` (Task 1 컴포넌트 커밋)

---

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** 타입 정합 수정만 — 로직/스코프 변경 0.

## Issues Encountered

- **worktree node_modules 부재:** typecheck 하니스로 메인 체크아웃 node_modules 임시 심볼릭 링크(gitignored) 생성 후 tsc 실행, 완료 후 제거(32-06/07 선례). 커밋 무접촉.
- 초기 파일 쓰기 시 메인 체크아웃 경로로 쏠림 → 워크트리 경로로 정정(격리 유지).

## Threat Model Compliance

- **T-32-22 (수치 신뢰):** 수치 삽입 경로를 게이지/수치 배지 1곳으로 구조 격리 + 게이지 스케일은 규칙 상수 기반 정의 수학만(geometry null = 미표시). 준수.
- **T-32-23 (크래시):** statusLine 부재 폴백 + zoomPair 옵셔널 + 줌 이미지 양측 onError 폴백. 준수.
- **T-32-24 (Info Disclosure):** 신규 서명 표면 0 — zoomPair 는 기존 presigned URI 를 props 로 받기만(배선 32-11), 이 플랜은 서명 코드 무추가. 준수.

신규 위협 표면 없음 (Threat Flags 없음).

## Known Stubs

없음 — 컴포넌트는 interface-first(props 로컬 타입)로 완결이며, doc→props 배선은 플랜이 명시적으로 32-11 소관으로 지정. 하드코딩 빈 데이터가 UI로 흐르는 경로 0(빈/실패/만료는 정직한 폴백으로 처리).

## Next Phase Readiness

- 감점 카드 표면 전체(카드·시트·게이지·미션·안전)가 완결 — 32-11이 result.tsx에서 recordId 조인으로 배선(줌쌍 URI·mission·onAskCoach 연결)만 하면 됨.
- 게이지 의미가 테스트로 고정 + 불가 케이스 정직 생략 → D-09/D-14 invariant가 컴포넌트 구조로 강제됨.
- 실기기 확인 대기(HUMAN-UAT 이월): 카드 3단 렌더·게이지 길이 표현·시트 잘림 해소는 32-11 배선 후 시뮬레이터/실기기 육안 필요.

## Self-Check: PASSED

- FOUND: app/src/lib/gaugeGeometry.ts + gaugeGeometry.test.ts (node --test 4/4 pass)
- FOUND: GoalGaugeBar.tsx / MissionBadge.tsx / DeductionCard.tsx (created)
- FOUND: DeductionDetailSheet.tsx / InjuryRiskSection.tsx (modified)
- FOUND commits: e18427f / 5bcdccb / 32ebcda / 5f92342 / 82acd60
- 파일 삭제 0 (전 커밋 add/modify만) · result.tsx·STATE.md·ROADMAP.md 무접촉
- tsc 0 errors (full app — 배선 소비처 result.tsx 미파손 확인)

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-21*
