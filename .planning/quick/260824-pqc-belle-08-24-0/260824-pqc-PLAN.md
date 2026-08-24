---
phase: quick-260824-pqc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/src/app/analysis/result.tsx
  - app/src/components/DeductionDetailSheet.tsx
  - app/src/components/VideoCompare.tsx
  - app/src/components/DefectIllustration.tsx
  - app/src/lib/illustrationScene.ts
  - app/src/lib/illustrationHow.ts
  - app/src/lib/progressCaption.ts
  - app/src/lib/ghostPose.ts
  - app/src/lib/__tests__/illustrationScene.test.ts
  - app/src/lib/__tests__/illustrationHow.test.ts
  - app/src/lib/__tests__/progressCaption.test.ts
  - app/src/lib/__tests__/ghostPose.test.ts
  - app/src/lib/__tests__/screenVocabulary.test.ts
  - app/src/lib/deductionSheet.ts
  - app/assets/illustrations/
autonomous: true
requirements: [QUICK-260824-PQC]

must_haves:
  truths:
    - "결과 화면 어디에도 일러스트가 렌더되지 않는다 — 부위 상세 시트의 목표 자세 카드, 재생 중 영상 위 큐 일러스트(illu-float), 발전 캡션(저번보다 나아졌어요), 잔상(ghostPose)·rotate 오버레이 전부"
    - "부위 상세 시트는 goalLine 을 항상 상단 goalBox 텍스트 경로로 표시한다 (nc2 그림 카드 분기 소멸 — 같은 문장 이중 표시 없음)"
    - "시트의 실사진 비교(크롭 카드)·원인 문구·수치(numNote)·미션(cueLine)·확인하기·강사 연결·AI 고지는 종전 그대로 렌더된다 (회귀 0)"
    - "영상 재생 큐(자막·음성·부위 강조·빨간 점)는 종전 그대로 동작한다 (voiceCueRecordId 계열 무접촉)"
    - "app/src 전체에서 삭제 모듈 참조 grep 0, typecheck GREEN, node --test 전량 실패 0 (기지 illustrationScene fail 8 은 파일 삭제로 소멸)"
  artifacts:
    - path: "app/src/app/analysis/result.tsx"
      provides: "일러스트 배선(슬롯·available·큐·발전캡션 재료) 제거된 결과 화면"
    - path: "app/src/components/DeductionDetailSheet.tsx"
      provides: "illustrationSlot/illustrationAvailable 없는 부위 상세 시트 (항상 텍스트 경로)"
    - path: "app/src/lib/__tests__/screenVocabulary.test.ts"
      provides: "삭제된 illustrationScene.ts EXCLUSIONS 항목이 정리된 어휘 게이트"
  key_links:
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/components/DeductionDetailSheet.tsx"
      via: "DeductionDetailSheet JSX props (illustrationSlot/illustrationAvailable 부재)"
      pattern: "DeductionDetailSheet"
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/components/VideoCompare.tsx"
      via: "VideoCompare props (renderCueIllustration 미전달 = 기존 fail-closed 렌더 0)"
      pattern: "VideoCompare"
---

<objective>
일러스트 기능 전면 제거 (belle 2026-08-24 결정: "일러스트 기능을 아예 빼고 서비스를 구성하자. 확대비교랑 모션 분석에 집중").

제거 범위 = 전부: 결함 일러스트 카드(목표 자세), 킵업 승인본(20-1 잔상 baked), 발전 캡션("저번보다 나아졌어요"), 오늘 배선된 파워스핀 rotate·ghostPose. 컴포넌트·lib 4종·테스트 4종·에셋 21장까지 죽은 코드 0 (CLAUDE.md 슬롭 금지 — git 이력으로 복구 가능).

Purpose: 8+라운드 판정에도 수렴 실패한 표면을 걷어내고 확대비교·모션 분석에 집중. 시트에는 실사진 비교·원인 문구·수치·미션이 남아 "어떻게" 역할이 성립.
Output: 일러스트 참조 0 인 app/src + 게이트 GREEN (typecheck + node --test 전량 실패 0).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/kimtaesung/Dev/SunityMotion/CLAUDE.md
@/Users/kimtaesung/Dev/SunityMotion/app/src/app/analysis/result.tsx
@/Users/kimtaesung/Dev/SunityMotion/app/src/components/DeductionDetailSheet.tsx
@/Users/kimtaesung/Dev/SunityMotion/app/src/components/DefectIllustration.tsx
</context>

<scope_fence>
- OTA 발행 금지 (제거 후 새 OTA 필요하지만 belle 한마디 대기 — 준비만, 발행은 범위 밖).
- Firestore·백엔드 무접촉. `.planning` 원장(문턱 실측 등) 무접촉.
- VideoCompare 는 코드 무접촉 — `renderCueIllustration` optional prop 은 잔류 (오케스트레이터 결정: 미전달 = 기존 fail-closed 렌더 0, 큐 행 레이아웃 회귀 0 우선). 허용되는 유일한 변경 = 해당 prop doc 주석의 stale 참조("33-14 illustrationSlot 선례") 갱신 (주석만, 코드 0).
- lib/deductionSheet.ts 는 뷰모델·테스트 무접촉 — 허용되는 유일한 변경 = `primaryMeasure` 주석의 "illustrationHow 가 정한다" 문장 갱신 (주석만). `buildCauseGroupKeys`·`splitGoalClause`·`primaryMeasure` export/필드는 잔류 (제거 시 58K 테스트 파일 연쇄 — 4종 lib 범위 밖).
- `voiceCueRecordId`·큐 자막·음성·부위 강조 경로 무접촉 (일러스트가 아니라 음성 큐 기능).
</scope_fence>

<tasks>

<task type="auto">
  <name>Task 1: 표시 배선 제거 — result.tsx / DeductionDetailSheet / DefectIllustration 삭제</name>
  <files>app/src/app/analysis/result.tsx, app/src/components/DeductionDetailSheet.tsx, app/src/components/VideoCompare.tsx (주석만), app/src/components/DefectIllustration.tsx (삭제)</files>
  <action>
**A. `app/src/components/DefectIllustration.tsx` 파일 삭제** (`git rm`). 621줄 — 그림 카드·how 오버레이(baked/rotate)·발전 캡션·잔상 렌더 본체 전부.

**B. `app/src/app/analysis/result.tsx` 배선 제거** (4193줄 — 라인 번호는 편집 중 이동하므로 심볼 앵커로 찾을 것):

1. import 제거: `DefectIllustration` (`../../components/DefectIllustration`), `illustrationAssetForPart` 와 `hasIllustrationFor` (`../../lib/illustrationScene`, 별도 2줄), `findPreviousComparable`/`extractCriterionMeasure` import 블록 (`../../lib/progressCaption`). `useMyAnalyses` 는 `userAnalyses` import 에서 이름만 제거 (`useAnalysisDoc` 잔류 — 다른 소비처 있음). `buildCauseGroupKeys` 는 `deductionSheet` import 블록에서 이름만 제거 (`buildPartChips`/`buildPartGroups`/`buildRegionSheetView`/`composeCueSubtitleKo` 잔류).
2. `const { analyses: doneAnalyses } = useMyAnalyses({ doneOnly: true });` 와 그 위 quick-260822-oe1 주석 블록 제거 — 발전 캡션 전용 구독이었음 (grep 검증 완료: result.tsx 내 doneAnalyses 소비처 = illustrationSlot 클로저 1곳뿐).
3. `const causeGroupKeys = useMemo(...)` + `const cueIllustrationForRecordId = (...)` 함수와 그 위 33-G S23/quick-260802-mrg 주석 블록 제거 (causeGroupKeys 소비처 = cueIllustrationForRecordId 뿐 — grep 검증 완료).
4. VideoCompare JSX 에서 `renderCueIllustration={cueIllustrationForRecordId}` prop 과 그 위 33-G S23 주석 3줄 제거. 합성 mp4 분기 주석(§12.9, "cueWindows·cueRefSnapSecs·audioAnalysisId·timelineTicks·renderCueIllustration 이 전부 VideoCompare props") 에서 `renderCueIllustration` 열거만 삭제 — 주석의 이중 발화 방지 논리는 유효하므로 문장 유지.
5. DeductionDetailSheet JSX 에서 `illustrationSlot={(maxHeight, how) => {...}}` render prop 전체 (prevDoc/prevHow 산출 + DefectIllustration 렌더 + ghostSource 조인 — quick-260822-oe1/260824-bxf/260824-jw4 배선) 와 `illustrationAvailable={illustrationAssetForPart(...) != null}` (quick-260818-nc2) 및 그 위 33-14 (A-7, D-15) 주석 블록 제거.

**C. `app/src/components/DeductionDetailSheet.tsx` prop·분기 제거:**

1. Props interface 에서 `illustrationSlot`(render prop, 주석 포함)·`illustrationAvailable`(quick-260818-nc2 주석 포함) 제거 + 함수 시그니처 destructure 2줄 제거.
2. `ILLUST_VIEWPORT_FRACTION` 상수(적응형 상한 주석 포함)·`ILLUST_CHIP` 상수 제거.
3. `const [scrollH, setScrollH] = React.useState(0);` 와 그 주석, ScrollView 의 `onLayout={(e) => setScrollH(...)}` 제거 (scrollH 소비처 = 일러스트 상한뿐).
4. `const howInput = view.primaryMeasure;` (quick-260818-nnm 주석 포함), `const primaryBlock = ...`, `const illustCaption = splitGoalClause(...)` 제거. import 에서 `splitGoalClause` 이름 제거 (`ADVISORY_CHIP_KO`/`objectJosaKo`/`RegionSheetView` 잔류).
5. 일러스트 렌더 블록 전체 제거 — `{illustrationSlot && illustrationAvailable ? (...illustCard...) : illustrationSlot ? (...) : null}` 와 그 위 33-14/quick-260818-nc2 주석. 뒤따르는 bullets·coachConnect·aiNoteBox 는 그대로. goalLine goalBox 는 항상 렌더 경로가 됨 (분기 소멸 — quick-260818-nc2 의 "그림 카드로 내리기" 로직 자체가 사라짐).
6. styles 에서 `illustCard`·`illustCap` 제거.
7. `import React from 'react'` — React.useState/React.ReactNode 소비처가 전부 사라지므로 제거 (jsx: react-jsx 라 JSX 는 무관).
8. 주석 정리: 파일 헤더의 "→ facing → 일러스트" 를 "→ facing" 으로, "위치만 일러스트 뒤로 이동" 등 일러스트 언급을 belle 08-24 전면 제거 결정 1줄로 대체. goalBox 위 quick-260818-nnm 주석의 그림 카드 언급 제거.

**D. `app/src/components/VideoCompare.tsx` 주석만:** `renderCueIllustration` prop doc 주석(33-G S23 블록)의 "33-14 illustrationSlot 선례" 참조 2곳을 "소비처 0 — 일러스트 전면 제거 (belle 08-24). 미전달 = 렌더 0 (fail-closed)" 로 갱신. **코드 변경 0** (prop·illu-float 블록·styles 잔류 — scope_fence 참조).
  </action>
  <verify>
    <automated>npm --prefix /Users/kimtaesung/Dev/SunityMotion/app run typecheck && ! grep -rnE "DefectIllustration|illustrationSlot|illustrationAvailable|cueIllustrationForRecordId|findPreviousComparable|extractCriterionMeasure|buildCauseGroupKeys|doneAnalyses" /Users/kimtaesung/Dev/SunityMotion/app/src/app /Users/kimtaesung/Dev/SunityMotion/app/src/components</automated>
  </verify>
  <done>typecheck GREEN. src/app + src/components 에서 삭제 심볼 참조 0 (주석 포함). DefectIllustration.tsx 파일 부재. VideoCompare 는 주석 diff 만 (git diff 로 코드 변경 0 확인).</done>
</task>

<task type="auto">
  <name>Task 2: lib 4종·테스트 4종·에셋 21장 제거 + 잔존 참조 grep 0</name>
  <files>app/src/lib/illustrationScene.ts (삭제), app/src/lib/illustrationHow.ts (삭제), app/src/lib/progressCaption.ts (삭제), app/src/lib/ghostPose.ts (삭제), app/src/lib/__tests__/illustrationScene.test.ts (삭제), app/src/lib/__tests__/illustrationHow.test.ts (삭제), app/src/lib/__tests__/progressCaption.test.ts (삭제), app/src/lib/__tests__/ghostPose.test.ts (삭제), app/assets/illustrations/ (삭제), app/src/lib/__tests__/screenVocabulary.test.ts, app/src/lib/deductionSheet.ts (주석만)</files>
  <action>
1. `git rm` lib 4종: `illustrationScene.ts`(장면 표·에셋 매핑·provenance), `illustrationHow.ts`(HOW_ANCHORS·buildHowOverlay — rotate 포함), `progressCaption.ts`(buildProgressCaption·findPreviousComparable·extractCriterionMeasure·PROGRESS_NOISE_THRESHOLDS — split_angle 문턱 상수는 캡션 전용이라 함께 삭제. 문턱 실측 원장은 .planning 에 잔존, 무접촉), `ghostPose.ts`(GHOST_ALIGN·GHOST_EDGES·buildGhostPoseForAsset).
2. `git rm` __tests__ 4종: `illustrationScene.test.ts`(기지 실패 8 포함 — 삭제로 소멸), `illustrationHow.test.ts`, `progressCaption.test.ts`, `ghostPose.test.ts`.
3. `git rm -r app/assets/illustrations/` — jpg 21장 전부 (번들 크기 절감, git 이력으로 복구 가능). Task 1 에서 DefectIllustration.tsx(유일한 require 소비처)가 이미 삭제됐으므로 번들러 참조 0.
4. `app/src/lib/__tests__/screenVocabulary.test.ts` — EXCLUSIONS 레지스트리에서 `'lib/illustrationScene.ts': ['provenance']` 항목과 그 근거 주석 블록 제거 (빈 맵 `{}` 로 남기고 레지스트리 설명 주석은 유지 — 스캔 로직 무접촉).
5. `app/src/lib/deductionSheet.ts` — `primaryMeasure` doc 주석의 "그릴지 말지는 illustrationHow 가 정한다" 문장을 "일러스트 전면 제거 (belle 08-24) — 현재 소비처 없음, 필드는 뷰모델·테스트 무접촉 원칙으로 잔류" 로 교체. **코드 변경 0** (필드·export 잔류 — scope_fence 참조).
  </action>
  <verify>
    <automated>! grep -rnE "DefectIllustration|illustrationScene|illustrationHow|progressCaption|ghostPose|assets/illustrations|buildProgressCaption|hasIllustrationFor|illustrationAssetForPart|buildHowOverlay|HOW_ANCHORS|GHOST_ALIGN|buildGhostPoseForAsset|PROGRESS_NOISE" /Users/kimtaesung/Dev/SunityMotion/app/src && [ ! -d /Users/kimtaesung/Dev/SunityMotion/app/assets/illustrations ]</automated>
  </verify>
  <done>app/src 전체(주석·테스트 포함)에서 삭제 모듈·심볼 참조 grep 0. assets/illustrations 디렉터리 부재. deductionSheet.ts 는 주석 diff 만.</done>
</task>

<task type="auto">
  <name>Task 3: 전량 게이트 — typecheck + node --test 남은 테스트 실패 0</name>
  <files>(변경 없음 — 게이트 실행만. 실패 시 Task 1/2 산출물 수리)</files>
  <action>
전량 게이트 실행 (260824-bxf 정본 커맨드 재사용):
1. `npm --prefix /Users/kimtaesung/Dev/SunityMotion/app run typecheck`
2. `cd /Users/kimtaesung/Dev/SunityMotion/app && node --test src/lib/__tests__/*.test.ts src/lib/__tests__/*.test.mjs`

판정 기준: 일러스트 테스트 4파일 삭제로 총 테스트 수는 직전 기준선 234 에서 감소한다 — 감소는 예상이며, **남은 테스트 실패 0** 이 게이트 (직전 기준선의 기지 실패 1건 = illustrationScene test 8 은 파일 삭제로 소멸했으므로 이제 허용 실패 0). exit code 0 필수.

실패가 나오면 이 태스크에서 원인을 Task 1/2 편집분으로 좁혀 수리 (테스트 완화·skip 금지). 특히 screenVocabulary.test.ts 는 앱 소스 전수 스캔이라 Task 1/2 의 주석 잔재를 잡아낼 수 있다.

SUMMARY 에 기록할 것: 테스트 수 before/after, 삭제 파일 목록(코드 라인 수·에셋 21장), OTA 미발행 (belle 한마디 대기 — 발행 준비 상태만 명시), 시뮬 실증 = 오케스트레이터 후속.
  </action>
  <verify>
    <automated>npm --prefix /Users/kimtaesung/Dev/SunityMotion/app run typecheck && cd /Users/kimtaesung/Dev/SunityMotion/app && node --test src/lib/__tests__/*.test.ts src/lib/__tests__/*.test.mjs 2>&1 | tail -15</automated>
  </verify>
  <done>typecheck GREEN + node --test 전량 exit 0, fail 0 (기지 실패 포함 잔존 실패 없음). 시뮬 실증·OTA 는 범위 밖 (오케스트레이터/belle 후속).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 없음 (신규) | 순수 제거 작업 — 새 입력 표면·네트워크 경로·패키지 설치 0 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-pqc-01 | DoS (회귀) | DeductionDetailSheet 렌더 경로 | mitigate | 분기 제거 후 goalBox 항상-텍스트 경로 성립을 typecheck + screenVocabulary 전수 스캔 + node --test 전량으로 검증; 시뮬 육안은 오케스트레이터 후속 |
| T-pqc-02 | Tampering | 번들 에셋 require | mitigate | 에셋 삭제 전 유일 require 소비처(DefectIllustration.tsx)를 Task 1 에서 선삭제 — Metro 번들 깨짐 원천 차단 (typecheck·grep 0 게이트) |
</threat_model>

<verification>
- typecheck GREEN + node --test 전량 실패 0 (Task 3).
- grep 0: `DefectIllustration|illustrationScene|illustrationHow|progressCaption|ghostPose|assets/illustrations` 가 app/src 에 부재 (Task 2 게이트).
- 부재 확인: DefectIllustration.tsx, lib 4종, __tests__ 4종, assets/illustrations/ 디렉터리.
- 회귀 0 확인(구조적): VideoCompare·deductionSheet.ts 는 git diff 주석만, voiceCueRecordId 계열 무접촉, 시트 크롭·블록·불릿·고지 렌더 경로 무접촉.
- OTA 미발행 (belle 결정 대기). Firestore/백엔드/.planning 원장 무접촉.
</verification>

<success_criteria>
- 일러스트 기능 전면 제거 완료: 컴포넌트 1 + lib 4 + 테스트 4 + 에셋 21장 삭제, 배선 3면(시트 슬롯·큐 일러스트·발전 캡션) 제거.
- 남은 표시(시트 실사진 비교·원인·수치·미션, 영상 큐 자막·음성·강조) 회귀 0.
- 게이트 전량 GREEN (typecheck + node --test 실패 0 — 기지 실패도 0).
</success_criteria>

<output>
Create `.planning/quick/260824-pqc-belle-08-24-0/260824-pqc-SUMMARY.md` when done.
</output>
