---
phase: quick-260824-bxf
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md
  - .planning/quick/260824-bxf-criterion-split-angle-12-split-21/measure_split_flip.mjs
  - app/src/lib/progressCaption.ts
  - app/src/components/DefectIllustration.tsx
  - app/src/app/analysis/result.tsx
  - app/src/lib/__tests__/progressCaption.test.ts
autonomous: true
requirements: [QUICK-BXF-01]

must_haves:
  truths:
    - "split_angle 20° 개선에는 캡션이 붙지 않고, 30° 개선에는 붙는다 (문턱 21)"
    - "타 criterion 은 종전 문턱 12 그대로 — 12° 개선 표시 / 11.9° 미표시"
    - "기본 문턱 null 이면 캡션 전면 비활성 (fail-closed 의미 유지)"
    - "split_angle 문턱 21 의 근거(같은-영상 플립 교차표)가 리포에 원장 파일로 남아 있고, 규칙 커밋이 측정 결과 커밋보다 먼저다"
  artifacts:
    - path: ".planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md"
      provides: "판정 규칙(측정 전 박제) + split_angle 플립 교차표 실측 결과"
    - path: ".planning/quick/260824-bxf-criterion-split-angle-12-split-21/measure_split_flip.mjs"
      provides: "읽기 전용 Firestore 교차표 측정 스크립트 (PII 마스크)"
    - path: "app/src/lib/progressCaption.ts"
      provides: "PROGRESS_NOISE_THRESHOLDS (기본 12 + byCriterion split_angle 21) + criterion 기반 문턱 조회"
      contains: "PROGRESS_NOISE_THRESHOLDS"
    - path: "app/src/lib/__tests__/progressCaption.test.ts"
      provides: "경계 테스트 — split 20/21/30, 타 criterion 11.9/12, 전면 비활성"
  key_links:
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/components/DefectIllustration.tsx"
      via: "criterion prop = sheetView.primaryCriterion (prevHow 산출과 같은 값)"
      pattern: "criterion=\\{sheetView"
    - from: "app/src/components/DefectIllustration.tsx"
      to: "buildProgressCaption"
      via: "criterion 인자 전달 (문턱을 criterion 으로 조회)"
      pattern: "buildProgressCaption\\(matched, criterion"
    - from: "app/src/lib/progressCaption.ts"
      to: ".planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md"
      via: "split_angle 21 출처 주석 (원장 경로·측정일·표본수)"
      pattern: "SPLIT-FLIP-CROSSTAB"
---

<objective>
발전 캡션 노이즈 문턱을 단일 상수(12)에서 criterion별 유연 구조(기본 12 + split_angle 21)로 전환한다.

belle 승인(2026-08-24): "split 은 21" 은 숫자 예외가 아니라 규칙의 일반화 —
`문턱_c = max(전역 12, ceil(해당 criterion 자체 노이즈 P95_c) + 1)`.
split_angle 은 자체 P95 = 20 (vision 20° 단위 양자화, NOISE-MEASUREMENT.md 08-22 실측 n=103)이라 21 이 나온다.

Purpose: 풀링 문턱 12 로는 split_angle 의 한 스텝(20°) 요동이 "발전"으로 캡션에 나간다 — 08-22 원장의 관측 항목이자 belle 결정 대기였던 건의 해소. 근거 원장(같은-영상 플립 교차표)은 08-22 세션에서 실측만 되고 파일이 없으므로, 재실측해 박제부터 한다 (measure-first: 규칙 커밋 → 측정 커밋 → 코드, 260822-oe1 선례).

Output: 교차표 원장 파일 + 문턱 맵 코드 + 경계 테스트 + 전량 게이트 GREEN.

범위 밖 (실행 금지): OTA 발행(eas update — belle 결정 대기), 시뮬 실증(오케스트레이터가 실행 후 별도 수행, 260730-py1 선례), Firestore/S3/프로덕션 쓰기 일체.
사용자 노출 문구에 노이즈/측정 오차 개념 추가 금지 (belle 08-24 — 캡션 부재는 설명하지 않는다).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/kimtaesung/Dev/SunityMotion/CLAUDE.md
@/Users/kimtaesung/Dev/SunityMotion/app/src/lib/progressCaption.ts
@/Users/kimtaesung/Dev/SunityMotion/app/src/lib/__tests__/progressCaption.test.ts
@/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260822-oe1-progress-caption/NOISE-MEASUREMENT.md
@/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260822-oe1-progress-caption/measure_noise.mjs
@/Users/kimtaesung/Dev/SunityMotion/app/src/components/DefectIllustration.tsx
@/Users/kimtaesung/Dev/SunityMotion/app/src/app/analysis/result.tsx
</context>

<interface_context>
현행 계약 (Task 2 가 바꾸는 것):

- `progressCaption.ts` 는 `PROGRESS_NOISE_THRESHOLD_DEG: number | null = 12` 단일 상수를 export 하고, `buildProgressCaption(asset, current, prev, thresholdDeg = PROGRESS_NOISE_THRESHOLD_DEG, anchors = HOW_ANCHORS)` 시그니처로 마지막-인자 테스트 주입을 받는다.
- 프로덕션 호출은 단 한 곳: `DefectIllustration.tsx:175-178` 의 `buildProgressCaption(matched, how, prevHow)` — criterion 을 모른다.
- criterion 은 상류 `result.tsx:3550-3577` illustrationSlot 렌더 prop 안에 있다: `extractCriterionMeasure(prevDoc, sheetView.primaryCriterion)` 으로 prevHow 를 만들 때 쓰는 `sheetView.primaryCriterion` 이 그 값이다.
- 구 상수명 참조는 `progressCaption.ts` 와 `progressCaption.test.ts` 두 파일뿐 (grep 실측 완료 — 다른 소비처 없음).
</interface_context>

<tasks>

<task type="auto">
  <name>Task 1: split_angle 플립 교차표 재실측·원장 박제 (규칙 커밋 → 측정 커밋)</name>
  <files>.planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md, .planning/quick/260824-bxf-criterion-split-angle-12-split-21/measure_split_flip.mjs</files>
  <action>
    **순서가 규칙이다 (measure-first, 260822-oe1 선례): 커밋 1 = 규칙+스크립트(결과 수치 0) → 측정 실행 → 커밋 2 = 결과 append.** 기존 `.planning/quick/260822-oe1-progress-caption/NOISE-MEASUREMENT.md` 는 소급 수정 금지 — 이번 산출물은 전부 새 quick 디렉터리의 새 파일.

    (1) `SPLIT-FLIP-CROSSTAB.md` 작성 — "## 판정 규칙 (측정 전 박제)" 섹션만 먼저:
    - 문턱 일반화 규칙 (belle 08-24 승인): `threshold_c = max(전역 12, ceil(P95_c) + 1)`. 전역 12 와 P95_c 의 출처 = NOISE-MEASUREMENT.md (2026-08-22, 페어 282 / |Δdelta| 표본 1017 / 풀링 P95 11.60; split_angle 행 n=103, P95=20.00, 값이 0 아니면 20 인 20° 양자화). 규칙 적용 산출: split_angle → max(12, ceil(20)+1) = 21. **이 문턱값들은 이미 커밋된 08-22 P95 표에서 유도되며, 이번 재실측 수치로 바꾸지 않는다** — 재실측은 "20° 스텝 = 측정 요동" 근거(교차표)의 원장화가 목적.
    - 교차표 정의: 페어 모집단 = measure_noise.mjs 와 **동일한 페어 구성 규칙**((a) 같은-영상: 같은 uid+fileName+anglesFrames+mode(+mode1 이면 referenceMotionId), deterministic/historical 분류 경계 2026-08-09T00:00+09:00 / (b) 48h 세션: 같은 uid+referenceMotionId mode1 인접 연속 짝 ≤48h, (a) 짝 이중 계상 제외) 중 **두 doc 모두 split_angle deg record 보유**인 페어. 산출 = 페어 종류별(same-video historical / same-video deterministic / session48h) (delta_i, delta_j) 값 조합 교차표 + 플립 비율(delta_i ≠ delta_j 인 페어 / 전체) + split_angle |Δdelta| 분포(n/min/median/P95/max).
    - 예측 사전 박제: 같은-영상 historical 페어 플립 ≈ 36.4% 부근 / deterministic 페어 플립 0 / 48h 페어 플립 0 (08-22 세션 구두 실측 — 원장 없음이 이번 작업의 이유). **산출이 예측과 달라도 그대로 박제한다 (수치 조작 금지). 규칙·코드 문턱(12/21)은 그대로 두고, 불일치는 SUMMARY 관측 항목으로 belle 에 보고.**
    - 관측 노트(결정 아님): 규칙을 08-22 표의 타 criterion 에 기계 적용하면 left_shoulder(P95 13.94)→15, leg_extension(P95 61.61, keypoint 포화 이상치 관측)→63 이 나오지만, belle 승인 범위 = "기본 12 + split_angle 21" 이고 현재 캡션 소비 경로(progressSentence 보유 앵커 = ref-kip-up--leg)의 criterion 은 split_angle 뿐 — 타 criterion 오버라이드는 belle 결정 없이 추가하지 않는다 (짜맞추기 방지).

    (2) `measure_split_flip.mjs` 작성 — measure_noise.mjs 를 본떠 새 파일 (원본 무수정): createRequire 앵커 `new URL('../../../app/scripts/measure_noise_anchor.mjs', import.meta.url)` 로 app/node_modules 의 firebase-admin devDependency 를 빌리는 패턴, `select()` 필드 마스크(mode/status/createdAt/fileName/anglesFrames/result.comparison.referenceMotionId/result.deductionBreakdown.records 만 — bodyProfile·영상 URL·키 미수집), uid 앞 6자+`…` 절단, 페어 구성·criterion 첫-record 선택·비유한값 skip 규칙을 그대로 재사용하되 표본을 split_angle 로 한정하고 위 (1) 정의의 교차표·플립 비율·분포를 markdown 표로 stdout 출력. **쓰기 API 호출 0 (get/listDocuments 만 — set/update/delete 금지).**

    커밋 1: `docs(quick-260824-bxf): split_angle 플립 교차표 판정 규칙 박제 (측정 전)` — md(규칙 섹션만) + mjs.

    (3) 측정 실행: `GOOGLE_APPLICATION_CREDENTIALS=/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json node /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260824-bxf-criterion-split-angle-12-split-21/measure_split_flip.mjs` → 출력을 md 의 "## 측정 결과" 섹션으로 append (측정 시각 포함). 예측 대비 자평 1줄 포함.

    커밋 2: `docs(quick-260824-bxf): 교차표 측정 결과 박제`.
  </action>
  <verify>
    <automated>test -f /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md && grep -v '^\s*//' /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260824-bxf-criterion-split-angle-12-split-21/measure_split_flip.mjs | grep -c '\.set(\|\.update(\|\.delete(' | grep -qx 0 && git -C /Users/kimtaesung/Dev/SunityMotion log --oneline --follow -- .planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md | wc -l | grep -qxE ' *2'</automated>
  </verify>
  <done>원장 md 에 규칙 섹션과 측정 결과 섹션이 있고, git 이력에서 규칙 커밋이 결과 커밋보다 먼저이며(파일 대상 커밋 정확히 2개), 스크립트에 Firestore 쓰기 호출이 0 이고 PII 마스크(select 마스크 + uid 절단)가 적용돼 있다. NOISE-MEASUREMENT.md diff = 0.</done>
</task>

<task type="auto">
  <name>Task 2: progressCaption 문턱 맵 전환 + criterion 배선 (기존 테스트 정합 갱신)</name>
  <files>app/src/lib/progressCaption.ts, app/src/components/DefectIllustration.tsx, app/src/app/analysis/result.tsx, app/src/lib/__tests__/progressCaption.test.ts</files>
  <action>
    `app/src/lib/progressCaption.ts`:
    - `PROGRESS_NOISE_THRESHOLD_DEG` 단일 상수를 제거하고 구조로 교체: `export interface ProgressNoiseThresholds { defaultDeg: number | null; byCriterion: Readonly<Record<string, number>> }` + `export const PROGRESS_NOISE_THRESHOLDS: ProgressNoiseThresholds = { defaultDeg: 12, byCriterion: { split_angle: 21 } }`.
    - **각 값에 출처 주석 필수**: defaultDeg 12 = `.planning/quick/260822-oe1-progress-caption/NOISE-MEASUREMENT.md` (측정일 2026-08-22, 페어 282 / |Δdelta| 표본 1017, 풀링 P95 11.60 → max(1, ceil)=12). split_angle 21 = 규칙 `max(전역 12, ceil(P95_c)+1)` (belle 08-24 승인), P95_c=20.00 (같은 원장 criterion 표 n=103, 20° 양자화) → 21, 플립 근거 원장 = `.planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md` (측정일 2026-08-24). 재측정 도구 경로도 주석에 남긴다.
    - 순수 조회 함수 추가: `export function resolveProgressNoiseThresholdDeg(criterion: string, thresholds: ProgressNoiseThresholds = PROGRESS_NOISE_THRESHOLDS): number | null` — `defaultDeg == null` 이면 무조건 null (**전면 비활성 의미 유지** — 오버라이드가 있어도 꺼진다, fail-closed BELLE-0821-P3 계승), 아니면 byCriterion 정확 일치 유한값 오버라이드, 없으면 defaultDeg.
    - `buildProgressCaption` 시그니처 전환: `(asset, criterion: string | null | undefined, current, prev, thresholds: ProgressNoiseThresholds = PROGRESS_NOISE_THRESHOLDS, anchors = HOW_ANCHORS)` — 문턱 결정은 함수 안에서 criterion 으로 `resolveProgressNoiseThresholdDeg` 조회. criterion 이 null/undefined/빈 문자열이면 캡션 null (fail-closed — 배선 불일치를 기본 문턱으로 덮지 않는다, BELLE-0821-P4 계승). 마지막-인자 주입 패턴은 thresholds 객체로 유지 (기존 number 주입은 정합 갱신 — 아래 테스트).
    - 나머지 게이트(unit deg/유한값/개선<문턱/악화/미등록 asset/progressSentence 부재) 로직·주석 불변.

    `app/src/components/DefectIllustration.tsx`: `criterion?: string | null` prop 추가 (quick-260824-bxf 출처 주석 — prevHow 를 만든 criterion 과 같은 값이어야 문턱이 의미를 갖는다는 docstring) → 호출을 `buildProgressCaption(matched, criterion, how, prevHow)` 로.

    `app/src/app/analysis/result.tsx`: illustrationSlot 안 `<DefectIllustration ...>` 에 `criterion={sheetView?.primaryCriterion ?? null}` 전달 — prevHow 산출(`extractCriterionMeasure(prevDoc, sheetView.primaryCriterion)`)과 **같은 값** (두 번째 규칙 금지).

    `app/src/lib/__tests__/progressCaption.test.ts` 정합 갱신 (신규 경계 테스트는 Task 3): 기존 3a/3b/4/4b 의 4번째 인자 number 주입을 `criterion` 인자 + `{ defaultDeg: 12, byCriterion: {} }` 주입으로 전환 (기존 검증 의미 보존 — criterion 은 임의 문자열, 예: 'split_angle' 아닌 'any_criterion'), 3c 의 `PROGRESS_NOISE_THRESHOLD_DEG` 참조를 `PROGRESS_NOISE_THRESHOLDS.defaultDeg` 로, 문턱 null 케이스를 `{ defaultDeg: null, byCriterion: {} }` 주입으로. 헤더 주석의 검증 축 서술도 갱신.

    금지: 사용자 노출 문구 변경/추가 0, 하드코딩 색상/스타일 0(스타일 무접촉), 이모지 0, OTA 실행 0.
  </action>
  <verify>
    <automated>npm --prefix /Users/kimtaesung/Dev/SunityMotion/app run typecheck && node --test /Users/kimtaesung/Dev/SunityMotion/app/src/lib/__tests__/progressCaption.test.ts && grep -rc "PROGRESS_NOISE_THRESHOLD_DEG\b" /Users/kimtaesung/Dev/SunityMotion/app/src | grep -v ':0$' | wc -l | grep -qx 0</automated>
  </verify>
  <done>typecheck GREEN + progressCaption 테스트 전건 pass. 구 상수명은 app/src 에서 소멸. 프로덕션 경로에서 문턱이 record 의 criterion 으로 조회되고(split_angle→21, 그 외→12), defaultDeg null = 전면 비활성이 유지된다.</done>
</task>

<task type="auto">
  <name>Task 3: 경계 테스트 추가 + 전량 게이트</name>
  <files>app/src/lib/__tests__/progressCaption.test.ts</files>
  <behavior>
    프로덕션 맵 `PROGRESS_NOISE_THRESHOLDS` 를 그대로 쓰는 경계 검증 (주입 아님 — 실배선 값):
    - split_angle 개선 20° (prev delta 20 → cur 0) → 캡션 null (문턱 21 미달 — 20° 한 스텝은 양자화 요동)
    - split_angle 개선 21° → 캡션 표시 (경계 = 문턱 포함, 기존 3b 관행)
    - split_angle 개선 30° → 캡션 표시
    - 타 criterion (예: angle_vs_reference__left_hip) 개선 12° → 캡션 표시 (종전 문턱 유지)
    - 타 criterion 개선 11.9° → 캡션 null
    - `{ defaultDeg: null, byCriterion: { split_angle: 21 } }` 주입 시 split_angle 대폭 개선도 null (전면 비활성이 오버라이드보다 우선)
    - `resolveProgressNoiseThresholdDeg`: 'split_angle'→21 / 미등록 criterion→12 / defaultDeg null→null
  </behavior>
  <action>
    위 behavior 를 `progressCaption.test.ts` 에 신규 섹션("6) criterion별 문턱 — quick-260824-bxf")으로 추가. asset 은 기존 ASSET('ref-kip-up--leg') 재사용, 측정값은 차이형 deg 헬퍼로 구성. 수치 채우기 금지 — 위 경계 케이스만.

    전량 게이트 실행: `npm --prefix /Users/kimtaesung/Dev/SunityMotion/app run typecheck` + `cd /Users/kimtaesung/Dev/SunityMotion/app && node --test src/lib/__tests__/*.test.ts src/lib/__tests__/*.test.mjs`.
    허용되는 실패 = **기지 1건 (illustrationScene test 8) 만**. 신규 실패 0. 그 외 실패가 나오면 이 작업의 회귀이므로 수리 후 재실행 (허용 목록 확장 금지).

    커밋: `feat(quick-260824-bxf): 발전 캡션 문턱 criterion별 전환 — 기본 12 + split_angle 21` (Task 2 코드 + Task 3 테스트를 실행자 재량으로 1~2 커밋).
  </action>
  <verify>
    <automated>npm --prefix /Users/kimtaesung/Dev/SunityMotion/app run typecheck && cd /Users/kimtaesung/Dev/SunityMotion/app && node --test src/lib/__tests__/*.test.ts src/lib/__tests__/*.test.mjs 2>&1 | tail -20</automated>
  </verify>
  <done>typecheck GREEN. node --test 전량에서 실패 = illustrationScene test 8 단 1건 (신규 실패 0). 경계 7케이스가 프로덕션 맵 실값으로 통과.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| measure_split_flip.mjs → Firestore | 프로덕션 사용자 분석 데이터를 admin 자격으로 읽음 (PII 인접) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-bxf-01 | Information Disclosure | measure_split_flip.mjs | mitigate | select() 필드 마스크로 bodyProfile·영상 URL·키 미수집 + 출력 uid 앞 6자 절단 (measure_noise.mjs T-oe1-01 계승) |
| T-bxf-02 | Tampering | Firestore (프로덕션) | mitigate | 쓰기 API 호출 0 (get/listDocuments 만) — Task 1 grep 게이트로 기계 검증 |
| T-bxf-03 | Tampering | 문턱 근거 원장 | mitigate | 규칙 커밋이 측정 결과 커밋보다 선행 (git 이력 게이트) — 사후 짜맞추기 구조적 차단 |
| T-bxf-SC | Tampering | 패키지 설치 | accept | 신규 npm/pip 설치 0 (기존 app devDependency firebase-admin 재사용) — 해당 없음 |
</threat_model>

<verification>
- Task 1: 원장 파일 존재 + 규칙→결과 커밋 순서 + 쓰기 API 0 (comment-filtered grep) + NOISE-MEASUREMENT.md 무수정.
- Task 2: typecheck + progressCaption 단위 테스트 + 구 상수명 소멸 grep.
- Task 3: typecheck + node --test 전량 (허용 실패 = illustrationScene test 8 단 1건).
- 커버리지 감사 (description 항목 → task): (1) 교차표 재실측·박제 → Task 1 / (2) 문턱 맵 전환 + 출처 주석 → Task 2 / (3) 경계 테스트 → Task 3 / (4) typecheck + 전량 테스트 → Task 2·3 verify. 범위 밖 명시: OTA·시뮬 실증.
</verification>

<success_criteria>
- SPLIT-FLIP-CROSSTAB.md 에 규칙(측정 전 커밋)과 교차표 실측(같은-영상 플립 비율 / 48h 플립 비율 / |Δdelta| 분포)이 박제됨 — 수치는 산출 그대로 (36.4% 와 달라도 조작 0, 불일치는 SUMMARY 관측으로 보고).
- 코드 문턱 = 기본 12 + split_angle 21 (규칙 max(12, ceil(P95_c)+1) 의 산출), 각 값에 원장 경로·측정일·표본수 주석.
- buildProgressCaption 이 record 의 criterion 으로 문턱을 조회하고, criterion 부재·defaultDeg null 은 fail-closed.
- 경계: split 20° 미표시 / 21° 표시 / 30° 표시 / 타 criterion 12° 표시 / 11.9° 미표시.
- typecheck GREEN + node --test 전량 신규 실패 0 (기지 illustrationScene test 8 만 허용).
- OTA 미발행, Firestore 쓰기 0, 사용자 노출 문구 변경 0.
</success_criteria>

<output>
Create `.planning/quick/260824-bxf-criterion-split-angle-12-split-21/260824-bxf-SUMMARY.md` when done.
SUMMARY 필수 항목: 교차표 실측 수치(예측 36.4%/0 대비 자평), 규칙→측정→코드 커밋 해시 순서, belle 보고 항목(수치 불일치 시 관측 + OTA 발행 결정 대기 유지).
</output>
