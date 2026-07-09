---
phase: 30-growth-tracking
type: direct-plan-review
reviewer: codex
date: 2026-07-09
status: changes_requested
external_reviewers_used: false
findings:
  high: 3
  medium: 2
  low: 0
---

# Phase 30 Direct Plan Review

외부 리뷰어 없이 Phase 30 계획서와 현재 코드 계약을 직접 대조했다. 리뷰 범위는
`.planning/phases/30-growth-tracking/*`, 홈 성장 카드 관련 앱 코드, mode3 백엔드
comparison 조립 경로다.

## Findings

### HIGH-1: scoreSuppressed 결과가 홈 성장 그래프/델타에 다시 노출될 수 있음

Phase 30 selector 계획은 `weeklyAverages`와 `motionDeltas`에서 `status === done`이고
`result?.overallScore`가 finite인 분석을 집계 대상으로 삼는다
(`30-01-PLAN.md:75`, `30-01-PLAN.md:77`). 그런데 현재 `AnalysisResult`에는
`scoreSuppressed: true` 계약이 있고, 결과 화면은 mode3의 suppressed 결과에서 점수 카드
전체를 숨긴다. 백엔드도 suppressed 케이스에서 점수는 계산되지만 사용자에게 권위 있는
점수처럼 보이지 않게 하는 의도로 `scoreSuppressed`를 기록한다.

이 상태로 Phase 30을 구현하면 branch3/low_confidence 같은 suppressed mode3 결과가
홈 화면의 주간 평균, 성장선, 동작별 델타에 반영된다. 결과 화면에서는 숨긴 점수가 홈
화면에서 다시 "성장"으로 노출되는 셈이라 신뢰 계약이 깨진다.

내가 수정한다면:

- `growthSelectors.ts`에 공통 predicate를 둔다. 예: `hasUsableGrowthScore(a)`,
  `a.result?.scoreSuppressed !== true`, finite `overallScore`, mode 일치를 모두 여기서
  검사한다.
- `weeklyAverages`와 `motionDeltas`는 같은 predicate만 사용하게 한다.
- suppressed 분석만 있는 경우에는 `defaultGrowthMode` fallback에서도 제외한다.
- selector semantic test에 `scoreSuppressed: true`인데 `overallScore`가 있는 fixture를
  넣고, 주간 평균/델타/기본 모드 후보에서 모두 제외되는지 검증한다.
- 필요하면 주석으로 "결과 화면에서 숨긴 점수는 홈 성장 지표에도 쓰지 않는다"는 계약을
  남긴다.

### HIGH-2: 프론트 핵심 로직 검증이 typecheck/grep 위주라 의미 있는 회귀를 못 잡음

Phase 30의 핵심은 UI 자체보다 순수 데이터 규칙이다. 주간 bucket, mode1/mode3 분리,
latest mode 기반 default, fallback, 동작별 grouping, first delta null, point delta
표시가 모두 selector 규칙에 걸려 있다. 그런데 `30-01-PLAN.md:83-92`와
`30-04-PLAN.md:97-108`의 검증은 `npm run typecheck`와 grep/code review가 대부분이다.
현재 `app/package.json`에도 프론트 테스트 스크립트가 없다.

이 검증으로는 잘못된 weekStart, mode 혼합 평균, fallback 누락, delta 부호 오류,
scoreSuppressed 포함 같은 문제를 통과시킬 수 있다.

내가 수정한다면:

- 새 테스트 프레임워크를 들이지 말고, 현재 devDependency인 TypeScript만 이용한 작은
  semantic check를 추가한다. 예: `app/scripts/assert-growth-selectors.mjs`.
- 스크립트는 `growthSelectors.ts`를 임시 디렉터리로 컴파일하거나 transpile한 뒤 fixture를
  실행해 Node `assert`로 검증한다.
- 최소 fixture는 다음을 포함한다.
  - 월요일 weekStart 계산
  - mode1/mode3 평균 비혼합
  - latest mode default와 "2주 미만이면 다른 mode fallback"
  - `scoreSuppressed: true` 제외
  - mode1은 reference motion 기준 grouping
  - mode3는 "내 기록" 단일 row
  - delta는 퍼센트가 아닌 point 차이
- acceptance gate를 `cd app && node scripts/assert-growth-selectors.mjs && npm run typecheck`
  로 올린다.

### HIGH-3: mode3 recognizedMotionId/Name 백엔드 검증이 false-green 가능

`30-02-PLAN.md`는 mode3 comparison에 `recognizedMotionId`와 `recognizedMotionName`을
저장하는 것이 핵심이다. 하지만 검증은 grep으로 `recognized_motion_id=profile.motion_id`
두 곳을 찾고 `python -m pytest tests/ -q -k "mode3 or assemble"`을 실행하는 수준이다
(`30-02-PLAN.md:120-125`).

현재 pipeline 테스트의 `_profile()` fixture는 `motion_id`를 채우지 않는다. 따라서 실제
`_mode3_comparison` 경로에서 profile에 motion id가 있을 때 comparison에 camelCase 필드가
나오는지 검증하지 못한다. 또한 `assemble.build_mode3`에는 first/no previous early return이
있어서, recognized 필드를 return 이후에 붙이면 첫 분석 케이스에서 누락될 수 있다.

내가 수정한다면:

- `backend/tests/test_assemble.py`에 `is_first=True`이면서
  `recognized_motion_id="ref-foo"`, `recognized_motion_name="Foo"`를 넘기는 테스트를
  추가한다. early return 전에도 필드가 들어가는지 확인한다.
- progress 케이스도 같은 필드를 검증한다.
- `backend/tests/test_pipeline_mode3.py`에 `TechniqueProfile(motion_id="ref-foo", name="Foo")`
  fixture를 별도로 추가하고, 첫 분석과 progress 분석 둘 다 comparison에
  `recognizedMotionId`/`recognizedMotionName`이 있는지 assert한다.
- `motion_id is None`일 때는 두 key가 아예 없는 negative test도 유지한다.
- grep count는 보조 검증으로만 남기고, acceptance의 주 검증은 pytest assertion으로 바꾼다.

### MEDIUM-1: GrowthCard 고정 높이 요구가 자동 검증되지 않음

`30-04-PLAN.md`는 tab 전환과 locked/growth/chart/by-motion 상태 전환에도 카드 높이가
점프하지 않아야 한다고 요구한다. 하지만 acceptance는 typecheck, grep, code review 중심이고
실제 높이 변화나 화면 렌더링을 측정하지 않는다.

내가 수정한다면:

- `GROWTH_CARD_CONTENT_HEIGHT` 같은 상수를 두고 chart, by-motion, locked body가 같은
  minHeight를 쓰게 한다.
- acceptance에 해당 상수 사용 여부를 추가한다.
- 가능하면 Expo/web 또는 RN 테스트가 가능한 환경에서 최소 한 번 screenshot/manual UAT를
  요구하고, 결과를 `30-HUMAN-UAT.md`에 남긴다.

### MEDIUM-2: 30-01의 "legacy" grep 기준이 계획 자체와 충돌할 수 있음

`30-01-PLAN.md`는 D-07 출처 주석을 남기라고 하면서, acceptance에서는 `phase|legacy` 같은
단어가 필터 코드에 없어야 한다고 grep 검증을 요구한다. 구현자가 필요한 주석에 `legacy`를
남기면 false fail이 나고, 반대로 위험한 필터가 다른 표현으로 들어가면 grep을 통과할 수
있다.

내가 수정한다면:

- bare word grep 대신 주석을 제거한 소스에 대해 금지 패턴을 검사하는 작은 static script를
  둔다.
- 금지 기준도 `phase`, `legacy` 같은 단어가 아니라 `phaseId`, `milestone`, 특정 날짜/버전
  비교처럼 실제 필터링에 쓰일 수 있는 property 접근으로 좁힌다.
- D-07 설명 주석은 허용 목록으로 명시한다.

## Overall Recommendation

Phase 30은 방향은 맞지만, 지금 계획 그대로 실행하면 "결과 화면에서는 숨긴 mode3 점수"가 홈
성장 지표로 되살아나는 문제가 가장 크다. 나는 HIGH-1을 먼저 반영해 selector 계약을 고치고,
그 계약을 HIGH-2의 semantic test로 잠근 뒤, HIGH-3의 백엔드 recognized motion 테스트를
추가한 상태에서 구현을 시작하겠다.

현재 상태는 `changes_requested`로 보는 것이 맞다.
