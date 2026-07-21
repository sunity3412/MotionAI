---
phase: 32-result-readability-3-omni
plan: 02
subsystem: ui
tags: [react-native, expo-video, panresponder, motion-alignment, dtw, accessibility, video-compare]

# Dependency graph
requires:
  - phase: 28-dtw-motion-based-alignment
    provides: MotionAlignment 계약 + alignmentWarp.ts(warpTime/normalizeMotionAlignment) + VideoCompare 단일 warp 경유 지점(clampRefTarget)
  - phase: 31-api-visual-correction
    provides: faultZoomComparisons 프레임 쌍(userFrameIdx/refFrameIdx/refMatched) + result.tsx poseFrames fps 정본
provides:
  - "manualOffset.ts 순수 함수 2종(composeRefTarget 합성·클램프 / legacyOffsetFromCompareFrames median 폴백)"
  - "VideoCompare 수동 ±초 미세조정 슬라이더(PanResponder 커스텀, 신규 의존성 0) + 접근성 adjustable"
  - "정직 배지: trim_only+low_global_confidence='대략 맞춤', disabled='시작점을 직접 맞춰주세요' (자동 정렬 꺼짐 문구 폐지)"
  - "legacy doc 자동 시작 오프셋 배선 + dirty 가드(Firestore 지연 로드 반영·사용자 조정 보존)"
  - "D-03 참고 지표 diagSentence 줄겹침 최소 수리(lineHeight 35)"
affects: [32-03(실물 게이트·OTA 발행), 32-04(목업 게이트), 32-11(참고 지표 표현 전면 수정)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "수동 오프셋 = 단일 warp 경유 지점(clampRefTarget) 합성 → 재생 제어 전부 자동 반영"
    - "오프셋 활성 시 master(left)/follow(right) 승격(followActive/followTick) — 절대 동기 back-seek 가 오프셋을 되돌리는 것 차단"
    - "ref 미러(manualOffsetRef) + dirty 가드(userAdjustedRef)로 tick stale 클로저·비동기 prop 함정 회피"

key-files:
  created:
    - app/src/lib/manualOffset.ts
    - app/src/lib/__tests__/manualOffset.test.ts
  modified:
    - app/src/components/VideoCompare.tsx
    - app/src/app/analysis/result.tsx

key-decisions:
  - "오프셋 활성 legacy 경로를 master/follow 로 승격(followActive) — 계획 밖 통합 버그 수정(Rule 1)"
  - "슬라이더 = PanResponder 커스텀(신규 npm 의존성 0, D-16 원칙 준수) + 접근성 increment/decrement 폴백"
  - "sliderBound = max(±3초, legacy 자동 오프셋 크기)로 확장해 큰 자동 오프셋도 썸 표현 가능"

patterns-established:
  - "composeRefTarget 단일 합성 지점: 오프셋 0 + 정상 입력 범위면 legacy 동작 byte-보존"
  - "legacyOffsetFromCompareFrames median: 단일 이상치 쌍이 오프셋을 지배하지 못함"

requirements-completed: [D-16, D-03]

# Metrics
duration: 26min
completed: 2026-07-21
---

# Phase 32 Plan 02: Wave-1 즉시 수리 앱 2건 (동작 비교 초 맞춤 + 참고 지표 겹침) Summary

**DTW 저신뢰에서 "끄지 않고" 수동 ±초 슬라이더 + legacy median 자동 오프셋 + '대략/직접 맞춤' 정직 배지로 동작 비교 초 맞춤을 실현하고(D-16), 참고 지표 장문 줄겹침을 lineHeight 수리(D-03)**

## Performance

- **Duration:** ~26 min
- **Started:** 2026-07-21T15:22Z (KST)
- **Completed:** 2026-07-21T15:48:15+09:00
- **Tasks:** 3 (Task 1 = TDD 2 commits)
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- **manualOffset.ts 순수 함수 2종** (player/react 의존 0, node --test 6/6): `composeRefTarget`(raw+offset 합성 + [0,dR] 클램프, dR 0/NaN·비유한 입력 안전) / `legacyOffsetFromCompareFrames`(유효 쌍 오프셋의 median, 이상치 견고, 유효 쌍 0 → null, fps 인자 전용)
- **VideoCompare 수동 미세조정 슬라이더**: PanResponder 커스텀(신규 의존성 0) + 현재 오프셋 라벨 + 리셋 + 접근성(adjustable/increment/decrement). 전 tier 공통 노출
- **단일 warp 경유 지점 합성**: `clampRefTarget` 내부 `composeRefTarget` 호출로 drift 보정 tick·togglePlay·seek·restart 전부 자동 반영
- **정직 배지 교체**: `trim_only + low_global_confidence` → "대략 맞춤" + 미세조정 유도 / `disabled` → "시작점을 직접 맞춰주세요" 직접 맞춤 유도. **'자동 정렬 꺼짐' 리터럴 앱 소스 0**
- **legacy 폴백 배선**: result.tsx 가 `legacyOffsetFromCompareFrames`(median) → `initialOffsetSec`, analysisId → `resetKey`. dirty 가드로 Firestore 지연 로드 반영 + 사용자 조정 후 미덮어쓰기
- **D-03 최소 수리**: diagSentence lineHeight 21 → 35 (fontSize 25×1.4)로 '동작 흐름'/'안정성' 장문 줄겹침 해소

## Task Commits

1. **Task 1: manualOffset 순수 함수 (TDD)** - `069ffc6` (test, RED) → `48b2056` (feat, GREEN)
2. **Task 2: VideoCompare 슬라이더 + 배지 + legacy 폴백** - `3901f91` (feat)
3. **Task 3: 참고 지표 겹침 최소 수리** - `c9730eb` (fix)

_Task 1 은 tdd="true" 라 RED(test)→GREEN(feat) 2 커밋. REFACTOR 불요(코드 clean)._

## Files Created/Modified
- `app/src/lib/manualOffset.ts` - 오프셋 합성/legacy median 폴백 순수 함수 (import 0)
- `app/src/lib/__tests__/manualOffset.test.ts` - node --test 6 케이스(합성·클램프·median·이상치·null·fps 인자)
- `app/src/components/VideoCompare.tsx` - 수동 슬라이더 UI·핸들러, composeRefTarget 합성, followActive/followTick 승격, 배지 카피 교체, initialOffsetSec/resetKey props + dirty 가드
- `app/src/app/analysis/result.tsx` - legacyStartOffsetSec 산출(fps 정본 환산) + VideoCompare 배선, diagSentence lineHeight 수리

## Decisions Made
- **PanResponder 커스텀 슬라이더**: D-16 원문은 "슬라이더"지만 신규 npm 의존성 0 원칙(belle) 준수 위해 RN 내장 PanResponder 로 트랙+썸 직접 구현. 접근성은 accessibilityRole="adjustable" + onAccessibilityAction(±0.1초)로 드래그 불가 사용자 폴백.
- **sliderBound 동적 확장**: 범위 ±3초 기본이나 legacy 자동 오프셋이 더 크면 `max(3, ceil(|initialOffsetSec|))`로 확장해 큰 자동 오프셋도 썸이 표현 가능·드래그 점프 방지.
- **리셋 = 자동 제안값 복귀**: legacy=initialOffsetSec / 정렬 활성=0 으로 복귀 + dirty 해제(이후 지연 도착 재반영). 단순 0 복귀 아님.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 오프셋 활성 legacy 경로 master/follow 승격 (followActive/followTick)**
- **Found during:** Task 2 (VideoCompare 슬라이더 배선)
- **Issue:** 계획은 "clampRefTarget 내 composeRefTarget 합성 → drift 보정 tick·togglePlay·seek 전부 자동 반영"으로 기술. 그러나 이는 **정렬 활성 경로에서만** 참이다. legacy(disabled/부재) 경로 — 수동 오프셋의 주 사용처 — 의 drift 보정은 **절대 동기(mutual back-seek: `Math.abs(cL-cR)` drift → 느린 쪽으로 되돌림)**·togglePlay/seekBoth/stepBy 의 절대 시각 분기를 쓴다. 여기에 오프셋을 걸면 `cR = cL + offset`(의도)를 drift 로 오인해 매 tick 되돌리고, 음의 오프셋 시 **master(left)까지 back-seek** 해 오프셋이 유지되지 않고 버벅인다.
- **Fix:** 오프셋 존재를 감지하는 `followActive`(렌더 스코프 = `alignmentActive || manualOffsetSec !== 0`) / `followTick`(tick 스코프 = `activeTick || manualOffsetRef.current !== 0`)를 도입. 이 조건이면 정렬 활성 경로와 동일한 master(left)/follow(right=clampRefTarget(cL)) 모델을 legacy+offset 에도 적용(tick drift·duration·togglePlay isAtEnd/needsStartSync·seekBoth maxAllowed·stepBy base·shouldPauseAtEnd). **오프셋 0 이면 `followActive === alignmentActive` 라 기존 legacy mutual-sync 경로 byte-보존**(렌더/동작 diff 0).
- **Files modified:** app/src/components/VideoCompare.tsx
- **Verification:** typecheck clean + composeRefTarget(t,0,dR) 가 legacy 호출부(t 항상 [0,dR] 내)에서 클램프 no-op 임을 소스 확인 → 오프셋 0 경로 무회귀. iOS 번들(expo export) 성공.
- **Committed in:** `3901f91` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — 계획의 "자동 반영" 가정이 legacy 경로에서 성립하지 않는 통합 버그)
**Impact on plan:** 이 수정 없이는 D-16 의 핵심(legacy doc 에서 수동/자동 오프셋)이 재생 중 되돌려져 무력화된다. 오프셋 0 경로는 byte-보존이라 기존 동작 무회귀. 스코프 크리프 없음(D-16 실현에 필수).

## Issues Encountered
- **worktree node_modules 부재**: 병렬 실행 worktree 에 node_modules 가 없어(gitignore) `tsc`/`node --test` 불가 → 메인 리포 node_modules(동일 base commit·lockfile) 심볼릭 링크로 해소(설치 아님). 심볼릭 링크는 `.gitignore`의 `node_modules/`(디렉터리 슬래시)에 매칭 안 돼 `.git/info/exclude`에 추가(로컬만, 커밋 0). 코드/의존성 변경 0.

## Known Limitations / 게이트 이월

- **Task 3 시뮬레이터 스크린샷 게이트 — 실물 게이트(32-03)로 이월**: 특정 '참고 지표' 카드('동작 흐름'/'안정성' 장문) 픽셀 렌더 확인은 실제 Firestore 분석 doc(전체 GPU 파이프라인 산출물)이 필요하다. Phase 26 이 시뮬 폴백/목업 렌더 경로를 제거했고(result.tsx:341-346), 이 worktree 에 booted 시뮬레이터·설치된 앱·dev-client·prebuilt .app 모두 부재. **대신 수행한 객관 검증**: (1) 소스 assert — lineHeight 35 ≥ fontSize 25×1.3=32.5 (32-RESEARCH Pitfall 3 규칙 충족, 다중 행 겹침 수학적 불가), (2) **expo export(iOS 전체 번들) 성공(10.1MB, exit 0)** — 내 3파일 변경이 Metro 해석·transform·번들 clean = 기동 무결성 확인("app 기동불가" 우려 해소), (3) typecheck clean. 픽셀 확인은 플랜이 명시한 **32-03 실물 게이트**(실기기·OTA 발행 포함)에서 최종 수행. 이 플랜은 OTA 미발행이라 [[verify-ui-on-simulator-before-ota]] 하드 게이트는 32-03 에 적용.

## Verification Summary
- `node --test app/src/lib/__tests__/manualOffset.test.ts` — 6 tests / 6 pass / 0 fail (exit 0)
- `cd app && npm run typecheck` — exit 0 (clean)
- `grep -r "자동 정렬 꺼짐" app/src` — 0 (문구 폐지 확인)
- `grep composeRefTarget VideoCompare.tsx` = 5 (import + clampRefTarget 합성), `PanResponder` = 22, `onAccessibilityAction` = 1, `userAdjusted` = 7
- package.json/lockfile diff 0 (신규 의존성 0)
- `expo export --platform ios` — exit 0 (번들 무결성)
- 파일 삭제 0 (`git diff --diff-filter=D` empty)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- **32-03(실물 게이트)**: 수리된 VideoCompare(슬라이더·배지·legacy 폴백)·result.tsx(겹침 수리)를 belle 실기기로 확인 후 OTA 발행(빌드 경로 청결 + 롤백 준비). Task 3 참고 지표 픽셀 확인이 여기로 이월됨.
- **32-04(목업 게이트)**: 참고 지표 표현 전면 수정(심사 정보 코너 vs 흡수)은 이 게이트 이후 32-11 소관. 이번엔 겹침만 수리.
- **blocker 없음**: manualOffset 순수 함수는 계약 무변경(신규 Firestore 필드 0), 앱 로컬 세션 상태만(영속화는 D-17 실물 게이트 후 판단).

## Self-Check: PASSED
- FOUND: app/src/lib/manualOffset.ts
- FOUND: app/src/lib/__tests__/manualOffset.test.ts
- FOUND commits: 069ffc6, 48b2056, 3901f91, c9730eb
- No file deletions across plan commits

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-21*
