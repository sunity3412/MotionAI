---
phase: 30-growth-tracking
fixed_at: 2026-07-17T00:00:00Z
review_path: .planning/phases/30-growth-tracking/30-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 30: Code Review Fix Report

**Fixed at:** 2026-07-17
**Source review:** .planning/phases/30-growth-tracking/30-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Warning 4 / Critical 0 — fix_scope=critical_warning, Info 3건 제외)
- Fixed: 4
- Skipped: 0

검증: 앱 fix 3건 각각 `npm run typecheck` PASS + `node --experimental-strip-types
scripts/assert-growth-selectors.mjs` PASS. 백엔드 fix 1건 `pytest tests/test_assemble.py
tests/test_pipeline_mode3.py -q` 53 passed (T-30-03 builder 타입 강제 테스트 포함 전건
유지). 채점 수학·breakdown 무접촉, 하드코딩 색상 신규 0, 이모지 0.

## Fixed Issues

### WR-01: 홈 헤더 평균이 NaN·억제 점수를 그대로 합산

**Files modified:** `app/src/app/(tabs)/index.tsx`
**Commit:** 618b44b
**Applied fix:** `averageScore` 필터를 `hasUsableGrowthScore` 와 동일 기준으로 강화 —
`result` 존재 + `scoreSuppressed !== true` 선필터 후 `typeof === 'number' &&
Number.isFinite` 로 NaN 배제. "(평균 NaN점)" 렌더 불가 + HIGH-1(결과화면에서 숨긴
점수를 홈 지표에 되살리지 않음) 정합. 모드 혼합 유지(D-01 재량 결정)는 무접촉.

### WR-02: 추이 차트 주별 점 개수 무제한 — 라벨 겹침 회귀

**Files modified:** `app/src/app/(tabs)/index.tsx`
**Commit:** 3971113
**Applied fix:** `TREND_WEEK_CAP = 8` 상수 추가(구 구현 slice(0,6) 상한 정신 계승,
GrowthChart 폭 320 에서 주 라벨 무겹침 상한), `trendPoints` 에
`.slice(-TREND_WEEK_CAP)` 적용 — 최근 주 우선, 평균·델타 재계산 없음
(MOTION_ROW_CAP 선례와 동일 표시층 slice 패턴). D-08 카드 높이 상수
(GROWTH_CARD_CONTENT_HEIGHT) 계약 무접촉.

### WR-03: motionDeltas else 분기가 malformed mode1 문서를 '내 기록'에 합산

**Files modified:** `app/src/lib/growthSelectors.ts`
**Commit:** f38bfd0
**Applied fix:** 그룹핑 else 분기를 `doc.mode === 'mode3'` 전용으로 협착하고, 그 외
(mode1 인데 comparison 형상 불일치)는 `continue` 로 어느 그룹에도 합산하지 않음 —
방어 경로에서의 D-02 모드 비혼합 위반 제거([[mode3-progress-not-similarity]] 정합).

### WR-04: build_mode3 recognized 타입 강제 ValueError 가 분석 전체 실패로 전파

**Files modified:** `backend/functions/pipeline/app.py`
**Commit:** 60c09fd
**Applied fix:** `_mode3_comparison` 진입부에서 str 경계 정규화 —
`_rm_id`/`_rm_name` = isinstance(str) 통과분만, 비-str 은 해당 필드만 drop +
`log.warning` (fail-open for optional accretion field). first/progress 양 분기
호출부를 `_rm_id`/`_rm_name` 전달로 교체. builder 의 T-30-03 타입 강제(오염 데이터
적립 방지)는 그대로 유지 — drop 이 곧 방지. graceful-degrade 관례
(scene_finder·coach writer)와 대칭 회복, 사용자 분석은 계속 진행.

## Skipped Issues

없음. (Info 3건 IN-01~03 은 fix_scope=critical_warning 범위 밖 — 미착수.)

---

_Fixed: 2026-07-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
