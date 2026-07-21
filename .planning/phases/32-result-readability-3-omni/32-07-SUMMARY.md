---
phase: 32-result-readability-3-omni
plan: 07
subsystem: ui
tags: [react-native, typography, theme-tokens, pure-function, node-test, coachmark, summary-card, tdd]

# Dependency graph
requires:
  - phase: 32-04
    provides: 목업 게이트 확정 (강조 체계 D-05 / 게임 프레임 범위 D-10) → emphasis-tokens.md 승인본
  - phase: 32-06
    provides: SummaryPraise/Mission/MissionOutcome/DeductionRecord 계약 타입 (구조적 소비 대상 — import 아님)
provides:
  - 결과 화면용 신규 타이포 토큰 (E2 스케일, 하한 17) — badge/bodySm/bodyMd/bodyMdBold/bodyLg/title/headline
  - summarySource.deriveSummaryContent — 잘한 점/오늘 고칠 것/다음 행동 선정 순수 함수 (백엔드 단일 원천 + legacy 폴백 + 스팟체크 강등)
  - SummaryCard 컴포넌트 (D-01 요약 1장, 수치 1곳 규칙)
  - ResultCoachmarks + coachmark.ts (D-07 첫 1회 코치마크 + AsyncStorage 플래그)
affects: [32-10, 32-11, 32-12, 32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "구조적 타이핑으로 계약 타입 소비 (analysis.ts import 0) — 32-06 계약과 컴파일 비결합, 배선 시 자연 결합"
    - "node --test type-stripping 순수 함수 테스트 (신규 npm 의존성 0, pickerFailure.test.ts 선례)"
    - "옵션 b 토큰 확장 — 전역값 상향 없이 결과 화면용 신규 단계만 추가"
    - "interface-first — 컴포넌트 props 계약만 확정, result.tsx 배선은 후속 플랜"

key-files:
  created:
    - app/src/lib/coachmark.ts
    - app/src/components/ResultCoachmarks.tsx
    - app/src/lib/summarySource.ts
    - app/src/lib/__tests__/summarySource.test.ts
    - app/src/components/SummaryCard.tsx
  modified:
    - app/src/theme/typography.ts

key-decisions:
  - "D-05 토큰 = 게이트 확정 E2 스케일 채택 + 하한 17 강제 (E2 badge 16→17 상향)"
  - "강조 강(800)은 배포 폰트(Pretendard Regular/Bold)에 맞춰 '700'으로 매핑 — 크기 계층으로 강조 확보"
  - "criteria_met 판정 = 측정값이 규칙 허용 내 신호(metCriteria) — clean_dimension(감점 0)과 별개, 안 잰 것 칭찬 금지 가드"
  - "수치 1곳 = SummaryCard 는 점수 배지만 수치 렌더, praise evidence 는 상세 카드(32-10) 담당 (D-01·D-09 동시 충족)"
  - "Pretendard 실제 로드(D-05 후반)는 이 플랜 파일 범위 밖(_layout/asset) — 32-11 배선으로 이월"

patterns-established:
  - "잘한 점 단일 원천 = 백엔드 summaryPraise, legacy doc 만 로컬 폴백 (스팟체크 교차검증 문장 == 화면 문장)"
  - "요약 카드 수치 1곳 규칙 (헤드라인 수치 금지 D-09 + 점수 소형 보조 D-01)"

requirements-completed: [D-01, D-05, D-06, D-07, D-09, D-26]

# Metrics
duration: ~20min
completed: 2026-07-21
---

# Phase 32 Plan 07: 요약 카드 본체 + 강조 토큰 + 코치마크 Summary

**결과 화면 첫인상 본체를 interface-first로 완성 — E2 강조 타이포 토큰(하한 17), 백엔드 단일 원천 잘한 점 선정 순수 함수(폴백+스팟체크 강등), 수치 1곳 요약 카드, 첫 1회 코치마크. result.tsx 무접촉으로 32-11 배선만 남김.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-21T11:50Z (approx)
- **Completed:** 2026-07-21T12:10Z
- **Tasks:** 3 (Task 2 = TDD RED→GREEN)
- **Files modified:** 6 (5 created, 1 modified)

## Accomplishments
- **D-05 강조 토큰:** 결과 화면용 신규 타이포 단계 7종 추가(E2 스케일, 하한 17, lineHeight ≥ fontSize×1.3, letterSpacing track()=0). 전역 토큰 무변경(옵션 b — 전 화면 파급 통제).
- **D-06/D-26 선정 순수 함수:** `deriveSummaryContent` — 잘한 점 doc 우선(blocker 5) → 스팟체크 불일치 강등 → legacy 폴백(mission_improved 1순위 → clean_dimension → criteria_met → null). 미측정·커버리지 갭 차원 칭찬 가드. node --test 11/11 pass.
- **D-01/D-09 요약 카드:** `SummaryCard` — 잘한 점 1(null=정직 고지) + 오늘 고칠 것 1(탭→점프) + 다음 행동 1(행동 큐 브랜드 pill) + 점수 소형 배지(수치 1곳). evidence 수치 비렌더.
- **D-07 코치마크:** `ResultCoachmarks` 오버레이 2종(라이트 테마) + `coachmark.ts` 첫 1회 AsyncStorage 플래그(onboarding.ts 구조).

## Task Commits

1. **Task 1: 강조 토큰(D-05) + 코치마크(D-07)** - `499663f` (feat)
2. **Task 2 RED: summarySource 실패 테스트** - `a1aebf7` (test)
3. **Task 2 GREEN: summarySource 구현** - `0b4e324` (feat)
4. **Task 3: SummaryCard 요약 카드** - `cbe7d96` (feat)

**Plan metadata:** SUMMARY 커밋은 이 문서와 함께 (STATE/ROADMAP 는 오케스트레이터 소관 — 병렬 executor 무접촉).

_Task 2 는 TDD(RED a1aebf7 → GREEN 0b4e324). REFACTOR 불필요(구조 양호)._

## Files Created/Modified
- `app/src/theme/typography.ts` - (modify) 결과 화면 강조 토큰 7종 추가(E2, 하한 17). 전역 토큰 무변경.
- `app/src/lib/coachmark.ts` - (create) 결과 코치마크 첫 1회 플래그 — `@sunity:result_coachmark_seen`, 읽기 실패=본 것으로 간주.
- `app/src/components/ResultCoachmarks.tsx` - (create) 코치마크 2종 오버레이(brandTint 라이트 배경, 탭 닫힘, 토큰만).
- `app/src/lib/summarySource.ts` - (create) `deriveSummaryContent` 선정 순수 함수(구조적 타이핑, react/expo/analysis import 0).
- `app/src/lib/__tests__/summarySource.test.ts` - (create) node --test 11건(7 behavior + 가드/분기).
- `app/src/components/SummaryCard.tsx` - (create) 요약 카드 1장(수치 1곳, praise null 정직 고지, 하드코딩 0).

## Decisions Made

플랜 Task 1 이 위임한 "토큰 채택값·사유 기록"에 따른 결정:

1. **D-05 스케일 = 게이트 확정 E2 + 하한 17.** 32-GATE-DECISIONS.md 가 "E2(강, 하한 17)"로 확정했으므로 emphasis-tokens.md 의 E2 열을 채택. 단 E2 열의 badge=16 은 belle 확정 하한 17("폰트 젤 작은 것들 정말 너무 작음")을 위반하므로 17 로 상향. 플랜 action 텍스트의 폴백 예시(bodySm 17/bodyMd 19 = E1 값)보다 게이트 확정값(E2)을 우선(게이트가 토큰 수치의 단일 출처 — read_first 규정).
2. **강조 강(800) → '700' 매핑.** emphasis 규칙표의 weight 800 은 우리가 배포하는 폰트 파일(Pretendard Regular/Bold 2종)에 대응 파일이 없다. 기존 bodyBold='700' 관례와 정합하도록 '700'(Bold)로 매핑하고, 강조는 크기 계층(headline 30 vs body 21)으로 확보.
3. **criteria_met 판정 신호 = metCriteria.** D-06 의 "기준 충족"을 clean_dimension(감점 0)과 구분하기 위해, DimensionSignal 에 `metCriteria`(측정값이 실존 규칙 허용 내 — caller/32-09 판정, 자의적 수치 아님) 필드를 두고 정직하게 분리. clean(감점 0) > criteria_met(허용 내) > null 순.
4. **수치 1곳 해석.** D-01 '점수 소형 보조 확정' + D-09 '카드당 수치 1곳'을 동시 충족하려면 요약 카드의 수치 렌더처는 점수 배지 1곳뿐. praise.evidenceValue/Unit 은 props 통과만 하고 렌더하지 않으며, 근거 수치는 상세 감점 카드(32-10 게이지/배지)가 담당 — 컴포넌트 헤더에 명시.

## Deviations from Plan

None (auto-fix Rule 1/2/3 해당 없음) - 플랜대로 실행. 위 "Decisions Made"는 플랜이 명시 위임한 토큰 채택 결정으로 deviation 아님.

## Known Stubs / Interface-First Deferrals

이 플랜은 **interface-first**(플랜 objective 명시 — result.tsx 무접촉). 아래는 스텁이 아니라 **계약대로의 의도된 미배선 상태**로, 후속 플랜이 해소:

- **컴포넌트 미배선:** `SummaryCard`/`ResultCoachmarks` 는 props 계약만 확정, 실제 doc 데이터 결합과 result.tsx 렌더 배치는 **32-11** 소관. (플랜 success_criteria: "32-11이 배선만 하면 되는 상태".)
- **Pretendard 실제 로드 미포함(★D-05 후반 이월):** D-05 = "E2 + Pretendard 실제 로드"인데, 폰트 로드는 `_layout`/asset 번들 변경이 필요하고 이 플랜의 files_modified(typography.ts/coachmark.ts/ResultCoachmarks.tsx/summarySource.ts/SummaryCard.tsx) 범위 밖. 토큰 절반은 완료, **폰트 로드 절반은 32-11 배선(또는 전용 폰트 태스크)으로 이월** — belle "폰트 너무 작음" 피드백의 완전 해소는 토큰 상향(완료) + 폰트 로드(이월) 둘 다 필요. typography.ts 의 fontFamily 매핑(Pretendard-Regular/Bold)은 이미 존재.

## Issues Encountered

- **워크트리 node_modules 부재.** 워크트리에 app/node_modules 가 없어 `npm run typecheck` 직접 실행 불가. 32-06 선례대로 main 리포 node_modules 를 app/node_modules 로 임시 심링크(gitignored — 커밋 0)해 `tsc --noEmit` 수행, 검증 후 심링크 제거. **merge 후 main 전체 typecheck 는 오케스트레이터가 수행**(mcp_tools 규정). 로컬 typecheck 결과: 전 파일 clean(EXIT 0).

## Threat Flags

None - T-32-15(잘한 점 생성) mitigate 는 계획대로 구현(단일 원천 + 소스 enum + 미측정 가드 + 근거 전무 null, Test 4·5). 신규 신뢰 경계 없음.

## Next Phase Readiness
- **32-11(배선):** SummaryCard/ResultCoachmarks props 계약 확정 — result.tsx 에서 `deriveSummaryContent(doc)` 결과 + score + 코치마크 플래그(hasSeenResultCoachmark)만 결합하면 됨. Pretendard 로드도 여기서 동반 권장.
- **32-10(감점 카드):** 신규 토큰(badge/bodyLg/title/headline)과 emphasis 규칙 공유 — 상세 카드 게이지 배지가 praise evidence 수치를 담당(수치 1곳 규칙의 반대 짝).
- **32-13(스팟체크):** summarySource 가 summaryPraise 를 그대로 소비 + spotCheckPraiseMismatch 강등 훅 확정 — 교차검증 문장 == 화면 문장 구조 성립.

## Self-Check: PASSED

- 6 소스 파일 + SUMMARY.md 전부 존재(FOUND).
- 4 커밋(499663f/a1aebf7/0b4e324/cbe7d96) 전부 git 이력 존재.
- result.tsx / STATE.md / ROADMAP.md / 32-GATE-DECISIONS.md 무접촉 확인.
- node --test 11/11 pass, app 전체 tsc --noEmit EXIT 0.

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-21*
