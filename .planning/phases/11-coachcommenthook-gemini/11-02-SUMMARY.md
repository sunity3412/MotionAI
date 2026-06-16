---
phase: 11-coachcommenthook-gemini
plan: 02
subsystem: app-result-screen
tags: [coach-hook, result-screen, open-questions-merge, coach-positioning, null-guard, feed-03]
requires:
  - CoachCommentHook TS interface + 두 report 의 coachCommentHook? 필드 (Phase 11 Wave 0, 11-00)
  - 백엔드 hook 부착 (force + body 양쪽 coachCommentHook, Phase 11 Wave 1, 11-01)
  - app/src/theme/index.ts (colors.brand #FF4B33 / spacing / divider 토큰)
provides:
  - result.tsx "강사에게 확인할 점" 섹션 (두 리포트 openQuestionsForCoach 병합)
  - result.tsx 포지셔닝 카피 (상단 1줄 + 코치 섹션 헤더, D-07)
  - result.tsx Mode 1 기준모션 "하나의 참고일 뿐" 문구 (SC#4)
  - userAnalyses.ts normalizeCoachHook null-guard (두 report 후방호환)
affects:
  - app/src/app/analysis/result.tsx
  - app/src/lib/userAnalyses.ts
tech-stack:
  added: []
  patterns:
    - "두 리포트 질문 병합 — concat(둘 다 ?? []) → trim → filter(Boolean) → de-dupe → slice(0,5) (??-chain first-non-null 금지, HIGH-2)"
    - "D-06 노출 범위 엄수 — openQuestionsForCoach 만 렌더, autoFindingsSummary/suggestedCues/coachComment/reviewedBy 비노출"
    - "null-guard normalize mirror — forcePatternInference/recommendedExercises precedent 1:1 (malformed → null graceful)"
    - "테마 토큰만 — 신규 코드 하드코딩 hex 0 (app/CLAUDE.md)"
key-files:
  created: []
  modified:
    - app/src/app/analysis/result.tsx
    - app/src/lib/userAnalyses.ts
decisions:
  - "openQuestions 수집 = 두 리포트 concat 후 trim/dedupe/slice(0,5) — force hook 존재 시 body 질문 누락하는 ??-chain 금지 (review HIGH-2)"
  - "D-06 노출 범위: openQuestionsForCoach 만 v1 노출, autoFindingsSummary/suggestedCues 는 저장만 (grep 0)"
  - "D-07 포지셔닝: 상단 1줄 '강사 지도를 돕는 참고' + 코치 섹션 서브 헤더 — 전용 강조 배너 금지 (가벼운 톤)"
  - "userAnalyses 두 report 모두 normalizeCoachHook null-guard — 이전 빌드/한쪽-hook doc graceful (T-11-03 mitigate)"
metrics:
  duration: ~30m
  completed: 2026-06-16
  tasks: 2
  files: 2
---

# Phase 11 Plan 02: 결과 화면 "강사에게 확인할 점" 섹션 + 보조도구 포지셔닝 Summary

v1 수강생 결과 화면이 두 리포트(forcePatternInference + bodyComparisonReport)의 `coachCommentHook.openQuestionsForCoach` 를 **병합**해 "강사에게 확인할 점" 섹션으로 노출하고, AI 를 "강사 보조 도구"로 포지셔닝하는 카피(상단 1줄 + 코치 섹션 헤더 + Mode 1 기준모션 "하나의 참고일 뿐")를 추가했다. 수강생이 강사에게 가져갈 질문 거리를 화면에서 본다 — FEED-03(강사 보조 도구 포지셔닝) 직접 충족.

## What Was Built

### Task 1 — 강사 확인 섹션(두 리포트 병합) + 포지셔닝 카피 + null-guard (commit aebd2f8)

- **`result.tsx` 병합 로직 (HIGH-2):** `useMemo` 로 `[...(force?.coachCommentHook?.openQuestionsForCoach ?? []), ...(body?.coachCommentHook?.openQuestionsForCoach ?? [])]` → `.map(trim)` → `.filter(Boolean)` → de-dupe (`indexOf===i`) → `.slice(0,5)`. 첫 non-null array 만 고르는 `??`-chain 부재 (array 는 nullish 가 아니라 force hook 존재 시 body 질문 영구 누락 — review HIGH-2). 병합 길이 > 0 일 때만 "강사에게 확인할 점" 섹션 렌더 (force findings 섹션 shape mirror — sectionTitle + card).
- **D-06 노출 범위 엄수:** `openQuestionsForCoach` 만 surface. `autoFindingsSummary`/`suggestedCues` 화면 비노출 (grep 0), `coachComment`/`reviewedBy` v1 null 미렌더.
- **D-07 포지셔닝:** 결과 화면 상단 1줄 "이 분석은 강사 지도를 돕는 참고예요." + 코치 섹션 서브 "아래 질문을 강사와 함께 확인해보세요." 전용 강조 배너 없음 (가벼운 톤).
- **ROADMAP SC#4:** Mode 1(정은지 비교) 기준모션 라벨(`styles.refName`) 근처 "기준 모션은 하나의 참고일 뿐이에요." 문구.
- **테마 토큰만:** 신규 코드 하드코딩 hex 0 (브랜드 `#FF4B33`/spacing/divider 토큰 사용). 이모지 0 (신규 코드). Korean 카피.
- **`userAnalyses.ts`:** `normalizeCoachHook` null-guard 를 두 리포트(force + body) 모두에 적용 (`forcePatternInference`/`recommendedExercises` precedent 1:1 mirror — malformed → null graceful, immutable spread). 이전 빌드 doc(coachCommentHook 없음)/한쪽만 있는 doc 후방호환.

### Task 2 — 결과 화면 시각 검증 (belle, human-verify checkpoint, blocking)

- belle 가 결과 화면 UI/카피를 시각 검증하는 blocking 체크포인트. **approved** — 카피/레이아웃 수정 없음.
- 실 LLM E2E (실 Gemini hook 생성) 시각 확인은 Phase 15 실증으로 deferred — 본 checkpoint 는 UI/카피/Figma 톤 정합 검증만.

## Verification Results

- `cd app && npm run typecheck` — clean (exit 0, merge 후 main 에서 재확인).
- `grep -c "강사에게 확인할 점" result.tsx` → 5 (D-06 섹션 + 라벨/스타일 참조).
- 두 리포트 concat: `forcePatternInference?.coachCommentHook` AND `bodyComparisonReport?.coachCommentHook` 둘 다 hit (각 2). `??`-chain first-non-null 선택 0.
- 병합 파이프라인: `trim()` / `filter(Boolean)` / `slice(0,5)` 모두 hit.
- 포지셔닝 + 참고 문구: `강사 지도를 돕는|강사 보조|하나의 참고` → 10 hit (FEED-03 + SC#4).
- D-06: `autoFindingsSummary|suggestedCues` → 0 (비노출).
- 하드코딩 색상: 11-02 diff 신규 라인 hex 리터럴 → 0 (테마 토큰만).
- `coachCommentHook` null-guard: `userAnalyses.ts` → 7 hit (두 report 정규화).
- 이모지: 11-02 diff 추가 라인 이모지 → 0 (기존 `⚠` 4건은 Phase 12 주석, 본 plan 미접촉).

## Deviations from Plan

None — plan executed as written. Task 1 자동 구현 후 Task 2 blocking human-verify 체크포인트에서 belle 가 approved (수정 없음).

## TDD Gate Compliance

N/A — 본 plan 은 `tdd="false"` UI 슬라이스 (Nyquist 백엔드 계약 테스트는 Wave 0/1 소유). 정적 게이트 = `npm run typecheck` (app 유일 정적 gate, JS 테스트 러너 없음).

## Known Stubs

None. v2 강사 콘솔 필드(coachComment/reviewedBy)는 v1 영구 비노출 (D-06 — Phase 11 scope 밖, stub 아님).

## Threat Flags

None — 신규 보안 surface 0. T-11-03(malformed hook → render 크래시) → `normalizeCoachHook` null-guard 로 mitigate, T-11-04(v2 coach-write 필드 v1 노출) → `openQuestionsForCoach` 만 렌더 (D-06) 로 mitigate, T-11-SC(npm 설치) → Phase 11 신규 패키지 0 (accept).

## Self-Check: PASSED

- modified `app/src/app/analysis/result.tsx` + `app/src/lib/userAnalyses.ts`: FOUND.
- commit aebd2f8 (Task 1): FOUND in git log (merged to main via 3f41a59).
- Task 2 human-verify checkpoint: belle approved.
- `npm run typecheck`: clean on merged main.
- 모든 acceptance grep (병합/포지셔닝/D-06/null-guard) 통과.
