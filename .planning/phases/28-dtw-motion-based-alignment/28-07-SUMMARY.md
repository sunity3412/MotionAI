---
phase: 28-dtw-motion-based-alignment
plan: 07
subsystem: motion-alignment (result 화면 소비 배선 — alignment prop + D-04 캡션 + D-05 배너)
tags: [dtw, alignment, result-screen, warp-consume, ref-match-caption, legacy-upsell, wave-5, typecheck, ota, display-only]
requirements: [ALGN-04, ALGN-05]
dependency_graph:
  requires:
    - "28-01/28-06 (alignmentWarp.ts normalizeMotionAlignment — 소비측 방어적 재검증 함수)"
    - "28-03 (MotionAlignment 계약 analysis.ts + FaultZoomComparison.refMatch — result.motionAlignment 소비 형상)"
    - "28-05 (refMatch='failed' 방출 + mapper 생존 — Firestore doc 까지 refMatch 도달 보장)"
    - "28-06 (VideoCompare alignment prop 계약 — undefined/null = legacy 100% 보존)"
    - "27-07 (faultZoomStatus placeholder — 선행 심볼 게이트)"
    - "quick-260705-r6v (zoom 카드가 DeductionDetailSheet 시트로 이관 — refMatch 캡션 렌더 위치)"
  provides:
    - "result.motionAlignment → normalizeMotionAlignment(useMemo) → VideoCompare alignment prop 소비 활성화 (신규 doc 워핑 흐름)"
    - "refMatch='failed' 정직 캡션 (DeductionDetailSheet 확대 이미지 하단 — D-04 앱측)"
    - "D-05 legacy 배너 + 재분석 CTA (motionAlignment 필드 부재만, tier 판정 0 — W3)"
  affects:
    - "28-08 (end-of-phase 실기기 UAT — 정렬 체감/배너/캡션 시각 확인)"
    - "22-* (source:'vlm' alignment 도 동일 prop 경유 소비 — 상위 호환)"
tech_stack:
  added: []
  patterns:
    - "소비측 normalizeMotionAlignment 재검증 (T-28-02, ASVS V5) — malformed/legacy → null = 절대시계 폴백"
    - "legacy 판정 = 필드 부재(undefined)만 — malformed null·tier 'disabled'와 구분 (배지=VideoCompare/배너=화면 레벨 책임 분리)"
    - "캡션 판정은 호출측(result.tsx)이 zoom.refMatch 로 계산 → 시트에 boolean prop 전달 (시트가 enum 의미 무지)"
    - "theme 토큰만 — brandTint/spacing.cardPadding/radius.card 재사용, 하드코딩 hex 증가 0"
key_files:
  created: []
  modified:
    - app/src/app/analysis/result.tsx
    - app/src/components/DeductionDetailSheet.tsx
decisions:
  - "refMatch 캡션 위치 = DeductionDetailSheet (계획의 'fault_zoom 카드 렌더부'는 quick-260705-r6v 로 메인 섹션이 시트로 이관된 상태 — 심볼 재탐색으로 실제 렌더 위치 확정, 계획 라인 참조 금지 지시 준수)"
  - "캡션 판정은 result.tsx 가 selectedZoom?.refMatch === 'failed' 로 계산해 refMatchFailed boolean prop 으로 전달 — 시트는 refMatch enum 의미를 몰라도 됨 + result.tsx 에 refMatch 참조 확보(acceptance)"
  - "banner 조건 = result.motionAlignment === undefined 단독 (result 는 AnalysisResultContent 에서 non-null 타입이라 result != null 가드 불요). tier 판정 0 (W3 — disabled 는 배너 아님)"
  - "alignment useMemo 의존 = [result] (result.motionAlignment 채워짐/부재 모두 result 참조 변경으로 반영, onSnapshot rerender 정합)"
metrics:
  duration_min: 20
  tasks_completed: 2
  files_created: 0
  files_modified: 2
  completed_date: 2026-07-08
---

# Phase 28 Plan 07: result 화면 소비 배선 (alignment prop + D-04 캡션 + D-05 배너) Summary

28-06 이 VideoCompare 에 심어둔 `alignment` prop seam 을 실제 데이터(`result.motionAlignment`)에 연결해 신규 doc 의 동작 기준 워핑을 활성화하고, 28-05 가 Firestore doc 까지 도달시킨 `refMatch='failed'` 를 확대 비교 이미지 하단의 정직 캡션으로 노출했으며, 정렬 데이터가 없는 legacy doc 사용자에게만(필드 부재 판정, tier 판정 0) 재분석 유도 배너를 띄웠다. 전부 표시/소비만 — 점수/판정 재계산 0. JS-only(OTA 가능).

## 선행 확인 (심볼 기준 — 27-07 게이트)

착수 전 `grep -c "faultZoomStatus" app/src/app/analysis/result.tsx` = 8 (>= 1) 확인 → 27-07 placeholder 실행 완료, 착수. VideoCompare 호출부(심볼 `<VideoCompare`)와 zoom 소비부(`selectedZoom`/`DeductionDetailSheet`) 존재 확인 — 26-02 wrapper 분리 여부와 무관하게 `<VideoCompare` 가 존재하는 파일(result.tsx `AnalysisResultContent`)을 기준으로 작업.

## What Was Built

### Task 1 — alignment prop 전달 + refMatch 캡션 (commit `242b6f7`)

- **result.tsx alignment 배선**: `normalizeMotionAlignment` 을 `../../lib/alignmentWarp` 에서 import. `videoAlignment = useMemo(() => normalizeMotionAlignment(result.motionAlignment ?? null), [result])` 신설 — 소비측 방어적 재검증(T-28-02, malformed/legacy → null). `<VideoCompare>` 에 `alignment={videoAlignment}` prop 전달 (28-CONTEXT D-01 주석: null = 현행 절대시계 폴백).
- **refMatch 캡션 (D-04 앱측)**: zoom 확대 카드는 quick-260705-r6v 로 메인 섹션에서 `DeductionDetailSheet` 시트로 이관된 상태 — 실제 렌더 위치를 심볼 재탐색으로 확정. result.tsx 는 `refMatchFailed={selectedZoom?.refMatch === 'failed'}` 를 시트에 전달(부재/'dtw' → false). `DeductionDetailSheet` 는 `refMatchFailed?: boolean` prop 신설 + 확대 이미지 하단에 "같은 동작 순간을 찾지 못해 전신 화면으로 보여드려요" 캡션 렌더(`refMatchNote` 스타일 = pendingText 패턴 차용, typography.caption + textSecondary, 토큰만). `zoom ?` 분기를 fragment 로 감싸 이미지 + 캡션 동시 렌더.

### Task 2 — D-05 legacy 재분석 유도 배너 (commit `cc9273a`)

- **result.tsx 배너**: 비교 카드 문맥(`{!(cmp.mode === 'mode3' && cmp.isFirst) && (...)}` 내부, VideoCompare 직하)에 legacy 배너 렌더. 조건 = `result.motionAlignment === undefined` 단독 — 필드 자체 부재(순수 legacy)만. **tier 판정 0 (W3):** 신규 분석은 degenerate 라도 tier 'disabled'로 필드가 실리므로(28-02) undefined = 순수 legacy, "재분석하면 적용" 과약속 루프 없음. disabled 안내는 VideoCompare 배지(28-06) 책임(배지=VideoCompare / 배너=화면 레벨 책임 분리, 28-RESEARCH Pattern 6).
- **내용**: 1줄 안내 "다시 분석하면 자동 구간 맞춤이 적용돼요" + 인라인 Pressable CTA "다시 분석하기" → `router.replace('/(tabs)/analyze')`(기존 재분석 라우팅 재사용, 신규 플로우 0). `accessibilityRole="button"` + `hitSlop={8}`. 스타일 = `alignUpsellBanner`/`alignUpsellText`/`alignUpsellCta`(brandTint 배경 + spacing.cardPadding + radius.card + brand 색, 토큰만, 라이트 전용, 이모지 0).

## Verification

- **Task 1**: `npm run typecheck` exit 0. `normalizeMotionAlignment` result.tsx=3(import+주석+useMemo) / `refMatch`=1(refMatchFailed prop 계산) / `alignment=`=1(VideoCompare prop). 하드코딩 hex=1(baseline 동일, 증가 0).
- **Task 2**: `npm run typecheck` exit 0. 배너 카피 grep=1. `accessibilityRole`=10(baseline 9 +1 = CTA Pressable). 하드코딩 hex=1(증가 0). 배너 조건식 tier 참조 0 — `grep "disabled"` 2건 전부 문서 주석(W3 근거 설명), 조건식은 `=== undefined` 단독.
- **legacy 보존**: `videoAlignment=null`(필드 부재/malformed)이면 VideoCompare 가 절대시계 100% 폴백(28-06 계약). refMatch 부재/'dtw' → 캡션 없음. motionAlignment 존재 → 배너 없음.

## Deviations from Plan

### Rule 3 (blocking, 계획 파일 범위 확장) — refMatch 캡션을 DeductionDetailSheet 에 렌더

**Found during:** Task 1
**Issue:** 계획 files_modified 는 `result.tsx` 단독이고 "fault_zoom 카드 렌더부에 캡션"을 지시했으나, 실제로는 quick-260705-r6v(파일럿 4차 피드백)로 메인 '문제 부위 확대 비교' 섹션이 삭제되고 확대 이미지가 `DeductionDetailSheet` 시트로 이관돼 있었다. result.tsx 에는 zoom 카드 인라인 렌더가 없어 캡션을 붙일 대상이 없음(계획 작성 시점 이후 구조 변경 — 계획도 "라인 번호 금지, 심볼 재탐색" 명시).
**Fix:** 캡션 판정(`selectedZoom?.refMatch === 'failed'`)은 result.tsx 가 계산해 `refMatchFailed` boolean prop 으로 시트에 전달(result.tsx 에 refMatch 참조 확보 + 시트는 enum 의미 무지). `DeductionDetailSheet` 에 prop + 캡션 렌더 추가. D-04 의도("실패 카드에 정직 캡션")를 실제 렌더 위치에서 충족.
**Files modified:** app/src/components/DeductionDetailSheet.tsx (계획 외 1파일)
**Commit:** 242b6f7 (Task 1)
**선례 정합:** 28-05 가 "계획의 result[faultZoomComparisons][0].refMatch 를 실제 반환 comparisons 구조로 재매핑"한 것과 동형(심볼 재탐색으로 계획-현실 drift 흡수).

## Notes

- **채점 무접촉:** 표시/소비만 — 점수/판정 재계산·재해석 0. deductionLabels/dimensions/veto 경로 무접촉. 신규 native 모듈 0(normalizeMotionAlignment 순수 함수, expo-video 기존 API), JS-only → OTA 가능.
- **의도된 seam 소비 완료:** 28-06 의 alignment prop seam(부재 시 legacy 100% 보존)을 실데이터에 연결 — 신규 doc 만 워핑이 흐르고 legacy/malformed 는 검증된 절대시계 폴백. 빈 데이터 UI 스텁 아님(faultZoomStatus/tier optional 선례).
- **threat 정합:** T-28-02(malformed 소비)=소비측 normalizeMotionAlignment 재검증 / T-28-17(오도 안내)=undefined 판정만 legacy + tier 판정 0(W3, 과약속 루프 차단) / T-28-14(실패 은폐)=refMatch='failed' 정직 캡션 — 전부 mitigate 반영. 신규 패키지 0(T-28-SC accept).
- **실기기 UI 확인(정렬 체감/배너/캡션)은 28-08 end-of-phase UAT 항목** — 이 플랜은 typecheck + grep 게이트까지.

## Threat Flags

None — 신규 네트워크 엔드포인트/인증/스키마 경계 0. 표시 경로 전용 소비(normalizeMotionAlignment 재검증) + boolean prop 1개 + 조건부 배너/캡션. 채점/veto 경로 무접촉.

## Commits

- `242b6f7` feat(28-07): alignment prop + refMatch 캡션
- `cc9273a` feat(28-07): D-05 legacy 재분석 유도 배너
