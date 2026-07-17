---
phase: 30-growth-tracking
reviewed: 2026-07-17T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - app/scripts/assert-growth-selectors.mjs
  - app/src/app/(tabs)/index.tsx
  - app/src/components/GrowthChart.tsx
  - app/src/components/GrowthMotionBars.tsx
  - app/src/lib/growthSelectors.ts
  - app/src/theme/colors.ts
  - app/src/types/analysis.ts
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - backend/shared/python/sunity_shared/models.py
  - backend/tests/test_assemble.py
  - backend/tests/test_pipeline_mode3.py
  - docs/contract.md
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 30: Code Review Report

**Reviewed:** 2026-07-17
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 30 (성장 그래프 재작업 + mode3 recognized-motion 계약 방출) 전체 diff 를 base
`8d3cd3f6` 기준으로 검토했다. 검증 실행 결과: `pytest tests/test_assemble.py
tests/test_pipeline_mode3.py` 53 passed, `tsc --noEmit` 무오류, `node
--experimental-strip-types scripts/assert-growth-selectors.mjs` 통과 (Node 24).

계약 3-way lockstep 은 실제로 관통 확인했다: `assemble.build_mode3`
(recognized_motion_id/name kwargs + id-None 시 두 키 미추가) → `pipeline
_mode3_comparison` first/progress 양 분기 배선 → Firestore 저장(flat scalar 라
nested-array 검증 무저촉) → 앱 `userAnalyses.normalize` 가 `result` 를 통과시켜
comparison 신규 키 보존 → `analysis.ts` Mode3Comparison + `contract.md` §4 갱신.
`GrowthChart` prop 형상 변경(`scores: number[]` → `points: WeeklyPoint[]`)은 소비처가
index.tsx 단일이라 파급 없음. 하드코딩 색상 신규 추가 0 (declineBlue 는 정식 토큰,
brand #FF4B33 무접촉), 등락률(%) 문자열·모듈로 연산자 0 확인.

Critical(차단) 결함은 없다. 다만 홈 헤더 혼합 평균의 NaN/억제점수 유입, 주별 점 수
무제한으로 인한 차트 라벨 겹침 회귀, motionDeltas 방어 분기의 모드 혼합 경로,
build_mode3 타입 강제 ValueError 의 분석 전체 실패 전파 등 4건의 Warning 을 찾았다.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: 홈 헤더 평균이 NaN·억제 점수를 그대로 합산 — "평균 NaN점" 렌더 가능 + HIGH-1 신뢰 계약과 비정합

**File:** `app/src/app/(tabs)/index.tsx:73-79`
**Issue:** `averageScore` 의 필터가 `typeof s === 'number'` 뿐이다. `typeof NaN ===
'number'` 는 true 이므로 NaN `overallScore` 문서가 하나라도 있으면 합계 전체가 NaN
이 되고, 호출부(125행)는 `avg != null` 검사만 하므로(NaN != null → true) 헤더에
"(평균 NaN점)" 이 그대로 렌더된다. 같은 diff 의 `growthSelectors.hasUsableGrowthScore`
는 `Number.isFinite` + `scoreSuppressed !== true` 를 명시 방어하는데(HIGH-1: "결과
화면에서 숨긴 점수를 홈 성장 지표에도 되살리지 않는다"), 같은 홈 화면의 헤더 평균은
`scoreSuppressed: true` 인 mode3 문서의 숨긴 점수(예: 90)를 평균에 되살린다. 모드
혼합 유지는 주석으로 명시 결정(D-01 재량)이지만 NaN·suppressed 유입은 결정 범위에
없다.
**Fix:**
```ts
function averageScore(analyses: AnalysisDoc[]): number | null {
  const scores = analyses
    .map((a) => a.result)
    .filter((r): r is NonNullable<typeof r> => !!r && r.scoreSuppressed !== true)
    .map((r) => r.overallScore)
    .filter((s) => typeof s === 'number' && Number.isFinite(s));
  if (scores.length === 0) return null;
  return Math.round(scores.reduce((sum, s) => sum + s, 0) / scores.length);
}
```

### WR-02: 추이 차트 주별 점 개수 무제한 — 활동 주가 늘면 라벨 겹침으로 판독 불가 (구현 전 상한 6 회귀)

**File:** `app/src/components/GrowthChart.tsx:41-112`, `app/src/app/(tabs)/index.tsx:379-382`
**Issue:** 구 구현은 `analyses.slice(0, 6)` 로 최근 6건만 그렸으나, 신 구현은
`weeklyAverages(analyses, effectiveMode)` 전체(사용자의 모든 활동 주)를 그대로
전달하고 GrowthChart 도 상한이 없다. viewBox 폭 320(innerW 284)에서 모든 점에 점수
라벨(fontSize 10) + 주 라벨(fontSize 9, "12/29주" ≈ 30px)을 그리므로, 활동 주가
약 8개를 넘으면(파일럿 2~3개월 사용) 주 라벨이 물리적으로 겹쳐 판독 불가가 된다.
motionDeltas 쪽은 `MOTION_ROW_CAP=4` 상한이 있는데 추이 쪽만 무상한이라 비대칭.
**Fix:** GrowthCard 에서 최근 N주만 slice 해 전달 (델타/평균 재계산 없음 —
MOTION_ROW_CAP 선례와 동일 패턴):
```ts
const TREND_WEEK_CAP = 8; // GrowthChart 폭 320 에서 라벨 무겹침 상한
const trendPoints = useMemo(
  () => weeklyAverages(analyses, effectiveMode).slice(-TREND_WEEK_CAP),
  [analyses, effectiveMode],
);
```

### WR-03: motionDeltas 의 else 분기가 malformed mode1 문서를 '내 기록' 그룹에 합산 — 방어 경로에서 D-02 모드 비혼합 위반

**File:** `app/src/lib/growthSelectors.ts:158-166`
**Issue:** 그룹핑 분기가 `doc.mode === 'mode1' && cmp?.mode === 'mode1'` 이 아니면
전부 `key='self'` (배지 '내 기록') 로 보낸다. `hasUsableGrowthScore` 는
`result.comparison` 존재/형상을 검증하지 않으므로, comparison 이 누락·손상된 mode1
문서(런타임 Firestore 데이터는 TS 계약을 보증하지 않음 — normalize 도 comparison 을
검증하지 않음)가 이 분기로 떨어지면 mode1 점수가 mode3 '내 기록' 행의 주별 평균·델타에
섞인다. 파일 헤더가 명시한 불변("mode3 는 전부 key='self'", D-02 모드 비혼합)이 방어
경로에서 조용히 깨진다.
**Fix:** else 분기를 mode3 전용으로 좁히고, 그 외(형상 불일치)는 skip:
```ts
if (doc.mode === 'mode1' && cmp?.mode === 'mode1') {
  key = cmp.referenceMotionId; label = cmp.referenceMotionName; badge = '프로 비교';
} else if (doc.mode === 'mode3') {
  key = 'self'; label = '내 기록'; badge = '내 기록';
} else {
  continue; // mode1 인데 comparison 형상 불일치 — 어느 그룹에도 합산 금지
}
```

### WR-04: build_mode3 의 recognized 타입 강제 ValueError 가 분석 전체 실패(server_error)로 전파 — 적립 전용 옵셔널 필드의 과대 blast radius

**File:** `backend/shared/python/sunity_shared/analysis/assemble.py:675-686`, `backend/functions/pipeline/app.py:3363-3369, 3406-3409`
**Issue:** `recognized_motion_id/name` 이 비-str 이면 ValueError(T-30-03)를 raise
하는데, 파이프라인 호출부는 이를 잡지 않으므로 `_process` 의 광역 except 가
`server_error` 로 분석 전체를 실패시킨다. 이 필드는 "이번 phase 화면 미소비, 데이터
적립 전용"(contract.md §4) 인데, 인식기 경계는 런타임 타입을 보증하지 않는다 —
특히 `gemini_technique_recognizer._profile_from_cache` 는
`motion_id=cached.get("motion")` 으로 캐시 dict 값을 무검증 복원한다(캐시 손상/구
스키마 혼재 시 비-str 가능). 부가 audit 필드 하나 때문에 사용자 분석이 통째로
죽는 것은 파이프라인 전반의 graceful-degrade 관례(scene_finder·coach writer 전부
예외 흡수)와 비대칭이다. builder 의 타입 강제(T-30-03) 자체는 유지하되, 호출부에서
경계를 흡수해야 한다.
**Fix:** 파이프라인 호출부(양 분기)에서 str 경계 정규화 후 전달:
```python
_rm_id = profile.motion_id if isinstance(profile.motion_id, str) else None
_rm_name = profile.name if isinstance(profile.name, str) else None
if profile.motion_id is not None and _rm_id is None:
    log.warning("recognized_motion_id 비-str — 적립 생략 (분석 계속): %r", profile.motion_id)
comparison = assemble.build_mode3(..., recognized_motion_id=_rm_id, recognized_motion_name=_rm_name)
```

## Info

### IN-01: GrowthLockedCard 카피가 '같은 모드' 조건을 누락

**File:** `app/src/app/(tabs)/index.tsx:440-442`
**Issue:** 게이트(`defaultGrowthMode !== null`)는 "어느 한 모드에서 주별 점 ≥2" 인데,
카피는 "서로 다른 주에 분석을 2번 이상 하면" 이다. mode1 을 1주차에, mode3 를 2주차에
한 사용자는 카피 조건을 충족했는데도 잠금 상태가 유지돼 혼란 여지가 있다.
**Fix:** "같은 방식(프로 비교/내 기록)으로 서로 다른 주에 2번 이상 분석하면" 류로
같은-모드 조건을 카피에 반영.

### IN-02: assert-growth-selectors.mjs 가 package.json scripts 에 미등록 — 시맨틱 락이 어떤 게이트에서도 실행되지 않음

**File:** `app/scripts/assert-growth-selectors.mjs:8`, `app/package.json:5-14`
**Issue:** 실행 커맨드가 파일 헤더 주석에만 있다. 앱의 유일한 정적 게이트는
`typecheck` 뿐이라, selector 로직이 바뀌어도 이 assertion 을 아무도 돌리지 않으면
조용히 부패한다(HIGH-2 로 만든 락의 목적 상실). 시드 스크립트들은 scripts 에 등록된
선례가 있다.
**Fix:** `"check:growth": "node --experimental-strip-types scripts/assert-growth-selectors.mjs"`
를 scripts 에 추가하고 phase 검증 절차에서 typecheck 와 함께 호출.

### IN-03: 표시 주별 평균(개별 반올림)과 델타(raw 차 반올림)의 반올림 비대칭 — "같은 숫자인데 ▲+1점" 가능

**File:** `app/src/lib/growthSelectors.ts:24, 179`
**Issue:** 추이 차트는 주별 `Math.round(rawAvg)` 를 표시하고, 동작별 델타는
`Math.round(latest.rawAvg − prev.rawAvg)` 다. 예: raw 74.6 → 75.4 는 차트에
75 → 75 로 평평하게 보이는데 동작별에는 "▲ +1점" 이 뜬다. 주석으로 의도(정밀도
보존)를 박제했으나 사용자 관점 표시 불일치가 남는다.
**Fix:** 표시 정합을 우선한다면 `delta = Math.round(latest.rawAvg) −
Math.round(prev.rawAvg)` 로 통일 검토 (또는 현행 유지 시 결정 근거를 30-CONTEXT 에
명시).

---

_Reviewed: 2026-07-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
