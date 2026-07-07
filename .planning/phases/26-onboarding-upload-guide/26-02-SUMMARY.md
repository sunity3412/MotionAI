---
phase: 26-onboarding-upload-guide
plan: 02
subsystem: ui
tags: [react-native, expo-router, faq, onboarding, dead-code-removal, hooks-order]

# Dependency graph
requires:
  - phase: 20-25 (result screen)
    provides: result.tsx 결과 화면 (wrapper/Content 분리 대상)
provides:
  - "이용 방법/FAQ 화면 (/help canonical 라우트, 정적 아코디언 6항목)"
  - "FAQ 에서 튜토리얼 재진입점 (router.push('/tutorial'), D-03)"
  - "시뮬레이션 샘플 경로 완전 제거 (samples.tsx + simulationWriter + simulatedResult + result.tsx dev 폴백)"
  - "result.tsx wrapper(AnalysisResult) / child(AnalysisResultContent) 분리 — 훅 순서 회귀 방지 패턴"
affects: [26-03 (analyze.tsx 진입 링크 /analysis/samples → /help 교체), 26-06 (라우트 이관 최종 봉인)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "wrapper/child 분리로 조건부 데이터 렌더 시 훅 순서 안정화 (non-null prop 으로 child 마운트 gate)"
    - "정적 FAQ 아코디언 (모듈 상수 FAQ_ITEMS + 단일 expandedId 토글)"

key-files:
  created:
    - app/src/app/help.tsx
  modified:
    - app/src/app/analysis/result.tsx
  deleted:
    - app/src/app/analysis/samples.tsx
    - app/src/lib/simulationWriter.ts
    - app/src/lib/simulatedResult.ts

key-decisions:
  - "/help 를 canonical 라우트로 신설, /analysis/samples 삭제 (redirect shim 없음 — typed routes 미사용, 내부 라우팅 전용)"
  - "child props = 실제 소비 집합 {result, name, bodyProfileSummary} — 플랜의 제안 목록(storedDoc/analysisMode/referenceMotionId/referenceMotionName)은 시뮬 폴백 전용이라 폴백 제거와 함께 소멸"
  - "FAQ 는 Figma 확정 프레임 부재(Figma Contract = 튜토리얼 + 다이얼로그만)로 samples 골격 재사용 (UI-SPEC S2)"

patterns-established:
  - "wrapper/Content 분리: 데이터 부재 시 wrapper 가 로딩/미보유 UI, child 는 non-null 데이터로만 마운트 → 렌더 간 훅 개수 불변 (리뷰 HIGH-1)"

requirements-completed: [ONBD-01]

# Metrics
duration: 25min
completed: 2026-07-07
---

# Phase 26 Plan 02: 이용방법/FAQ 교체 + 샘플 미리보기 데드코드 제거 Summary

**샘플 결과 미리보기(samples.tsx)를 정적 이용방법/FAQ 화면(/help)으로 교체하고, 시뮬레이션 샘플 경로를 result.tsx dev 폴백까지 완전 제거하면서 result.tsx 를 wrapper/Content 로 분리해 훅 순서 회귀 없이 missing-result 상태를 렌더하도록 만들었다.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-07T23:10Z (approx)
- **Completed:** 2026-07-07T23:27Z
- **Tasks:** 2
- **Files:** 1 created, 1 modified, 3 deleted

## Accomplishments
- `app/src/app/help.tsx` 신설 — samples 골격 재사용한 정적 FAQ 아코디언 6항목(기대설정: 무엇을 측정/강사 보조 포지셔닝/원본 업로드 이유/촬영 거리·구도/실패 대처/보관·삭제 정책) + 튜토리얼 재진입점 (F2/D-05/D-03).
- 시뮬레이션 샘플 경로 3파일 삭제(samples.tsx, simulationWriter.ts, simulatedResult.ts) + result.tsx 의 getSimulatedResult dev 폴백 제거 — `grep -rn "simulationWriter\|simulatedResult" app/src` 매치 0.
- result.tsx 를 `AnalysisResult`(wrapper) + `AnalysisResultContent`(child)로 분리 — child 는 non-null `AnalysisResult` 타입으로만 마운트, doc.result 부재 시 wrapper 가 로딩/한국어 미보유 안내를 렌더. early-return 단순 패치 없이 훅 순서 안정화 (리뷰 HIGH-1).
- `npm --prefix app run typecheck` GREEN, backend diff 0, JS-only (OTA 가능).

## Task Commits

1. **Task 1: help.tsx 이용방법/FAQ 화면 신설** - `dd1deb7` (feat)
2. **Task 2: 샘플 미리보기 코드 제거 + result.tsx wrapper/Content 분리** - `4ad500f` (refactor)
3. **Fixup: help.tsx 주석 죽은 라우트 문자열 제거** - `f3ba61e` (docs)

## Files Created/Modified
- `app/src/app/help.tsx` (신규, 196줄) - 정적 이용방법/FAQ 화면. FAQ_ITEMS 6항목 아코디언 + `튜토리얼 다시 보기` 텍스트 링크(router.push('/tutorial')). 토큰만, 인라인 hex 0.
- `app/src/app/analysis/result.tsx` (수정) - getSimulatedResult import/폴백 제거, wrapper(AnalysisResult)/child(AnalysisResultContent) 분리, 미보유 상태 한국어 안내 렌더. 헤더 주석 갱신.
- `app/src/app/analysis/samples.tsx` (삭제) - 샘플 미리보기 화면 (/analysis/samples 라우트 소멸).
- `app/src/lib/simulationWriter.ts` (삭제) - 샘플 시딩 writer (소비자 0).
- `app/src/lib/simulatedResult.ts` (삭제) - 시뮬 결과 데이터 (소비자 0).

## Decisions Made
- **/help canonical, shim 없음:** CONTEXT/UI-SPEC 의 "samples.tsx 교체"를 톱레벨 `/help` 신설 + `/analysis/samples` 삭제로 확정 (플랜 라우트 이관 결정, 리뷰 MEDIUM-1). analyze.tsx 진입 링크 교체는 26-03 소유.
- **child props = 실제 소비 집합:** 아래 Deviations 참조.
- **FAQ = samples 골격:** Figma Contract 가 튜토리얼 + 다이얼로그만 확정하고 FAQ 프레임은 없어 UI-SPEC S2 폴백(samples 레이아웃 골격 재사용) 적용.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] child props = 실제 소비 집합으로 조정 (플랜 제안 목록과 상이)**
- **Found during:** Task 2 (result.tsx wrapper/Content 분리)
- **Issue:** 플랜은 child props 를 `{ result, storedDoc, analysisMode, referenceMotionId, referenceMotionName, bodyProfileSummary }` 로 제안했으나, (a) `storedDoc/analysisMode/referenceMotionId/referenceMotionName` 는 **제거된 시뮬 폴백 전용**이라 폴백 제거 후 child 에서 소비 0, (b) child 가 실제 사용하는 `name`(헤더 카피)이 제안 목록에 누락. 제안 목록 그대로 넘기면 unused prop + 필요한 prop 누락.
- **Fix:** child 실제 소비 집합 `{ result, name, bodyProfileSummary }` 로 확정 (child 는 useRouter() 자체 호출). `result` 는 non-nullable `AnalysisResult` 타입 — 하드 AC 충족.
- **Files modified:** app/src/app/analysis/result.tsx
- **Verification:** typecheck GREEN, `grep`으로 child 본문 storedDoc/result null 분기 0 확인
- **Committed in:** 4ad500f

**2. [Rule 3 - Blocking] 고아 import 정리 (AnalysisMode)**
- **Found during:** Task 2
- **Issue:** 폴백 제거로 `analysisMode` 파생과 `mode` 파라미터가 소멸하면서 `AnalysisMode` 타입 import 가 고아가 됨.
- **Fix:** `import type { ... }` 에서 `AnalysisMode` 제거.
- **Files modified:** app/src/app/analysis/result.tsx
- **Verification:** typecheck GREEN
- **Committed in:** 4ad500f

**3. [Rule 3 - Blocking] 검증 게이트 정합 — 주석의 죽은 심볼 문자열 제거**
- **Found during:** Task 2 verify + 라우트 이관 봉인 체크
- **Issue:** 갱신한 주석에 `simulationWriter`/`simulatedResult`(result.tsx) 및 `analysis/samples`(help.tsx) 리터럴이 들어가 플랜의 잔존 참조 grep 게이트(`grep -rn "simulationWriter\|simulatedResult" app/src` = 0, 라우트 이관 봉인)를 오탐으로 깨뜨림.
- **Fix:** 두 주석을 심볼 리터럴 없이 의미만 서술하도록 재작성. 최종 `analysis/samples` 매치 = analyze.tsx 1곳(26-03 소유)만 잔존.
- **Files modified:** app/src/app/analysis/result.tsx, app/src/app/help.tsx
- **Verification:** `grep -rn "simulationWriter\|simulatedResult" app/src` = 0, `grep -rn "analysis/samples" app docs` = analyze.tsx 1곳
- **Committed in:** 4ad500f (result.tsx), f3ba61e (help.tsx)

---

**Total deviations:** 3 auto-fixed (전부 Rule 3 blocking)
**Impact on plan:** 모두 폴백 제거의 필연적 정리 + 검증 게이트 정합. 하드 AC(child result non-nullable, missing-result 분리, 잔존 참조 0) 전부 충족. 스코프 크리프 없음.

## Issues Encountered
- **worktree node_modules 부재:** 병렬 실행 worktree 에 `app/node_modules` 가 없어 `tsc` 실행 불가. 메인 체크아웃의 gitignored node_modules 로 심볼릭 링크를 걸어 typecheck 게이트를 실행(동일 base commit + 무변경 package.json). 심링크는 커밋하지 않음(파일별 명시 stage — `git add <file>` 만 사용, 심링크 미포함). 코드 영향 0.

## Threat Flags
없음 — 정적 콘텐츠 + 데드코드 삭제, 신규 네트워크/인증/스키마 표면 0. T-26-03(FAQ 보관·삭제 정책 카피)은 D-08 취지("분석에만 사용하고 안전하게 보관해요. 언제든 삭제를 요청하실 수 있어요")와 동일하게 고정 — 과장/허위 고지 없음.

## Known Stubs
없음 — help.tsx FAQ 는 의도적 정적 콘텐츠(데이터 소스 스텁 아님). result.tsx 미보유 상태는 실 데이터 부재 시 한국어 안내(시뮬 데이터 렌더 금지).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `/help` 라우트 존재 보장 완료. 26-03 이 analyze.tsx 진입 링크 `/analysis/samples` → `/help` 로 교체 예정 (파일 소유권 분리 — 같은 wave 충돌 방지).
- 라우트 이관 최종 "app/docs 매치 0" 봉인은 26-06 phase 마감 verification 이 재확인.
- `/tutorial` 라우트(S1 튜토리얼)는 별도 플랜 산출물 — help.tsx 는 문자열 라우트로 참조(typed routes 미사용이라 typecheck 무관).

## Self-Check: PASSED

- Created/modified present: help.tsx, result.tsx, 26-02-SUMMARY.md — all FOUND.
- Deleted absent: samples.tsx, simulationWriter.ts, simulatedResult.ts — all ABSENT.
- Commits present: dd1deb7 (feat), 4ad500f (refactor), f3ba61e (docs) — all FOUND.

---
*Phase: 26-onboarding-upload-guide*
*Completed: 2026-07-07*
