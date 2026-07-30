---
phase: quick-260730-szk
plan: 01
type: execute
wave: 1
depends_on: [quick-260730-l7t, quick-260730-py1]
files_modified:
  - app/src/lib/focusShape.ts
  - app/src/lib/__tests__/focusShape.test.ts
  - app/src/lib/deductionLabels.ts
  - app/src/lib/deductionSheet.ts
  - app/src/lib/__tests__/deductionSheet.test.ts
  - app/src/components/KeypointOverlay.tsx
  - app/src/components/PartChipsRow.tsx
  - app/src/components/DeductionDetailSheet.tsx
  - app/src/app/analysis/result.tsx
  - .planning/quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/sweep_markers_focus.test.ts
autonomous: true
requirements: [S19, S1, S2, S3, F-8]
user_setup: []

must_haves:
  truths:
    - "음성 큐 구간에서 강조가 kp 게이트를 통과하면 사지 모양을 따르는 선(가시 구간만)으로, 미달이면 부위 원으로 나온다 (원만 나오지 않는다)"
    - "음성 큐 강조(선·원)가 1.4초 주기로 깜빡인다 (dim 배경은 깜빡이지 않는다)"
    - "감점 마커는 항목(부위) 단위 그룹 경계 1개로 묶여 나오고, 그 부위 멤버 관절의 개별 빨강 원이 함께 나열되지 않는다"
    - "감점 = 실선 / 참고 = 점선 이고, 참고 표면의 안내 문형이 전 표면에서 한 문장 소스로 같다"
    - "영상 카드 아래에 부위 칩(다리/어깨/팔/참고: N)이 보이고, 감점 칩을 누르면 그 부위 상세 시트가 열린다"
    - "결과 화면에 들어온 직후(스켈레톤 토글 OFF·음성 큐 없음) 영상 위 마커가 0개다 — 마커는 음성 큐 강조와 스켈레톤 토글에서만 나온다"
    - "감점 0(cleanPass) 문서에서는 칩 행 자체가 렌더되지 않는다"
    - "마커가 숨겨진 상태에서 보이지 않는 탭 타깃이 남지 않는다 (진입점은 칩·내역 행·재생바 틱·여백 범례)"
  artifacts:
    - path: "app/src/lib/focusShape.ts"
      provides: "S19 선/원 분기 순수 로직 — 사지 체인 사전 + 가시 구간 추출 (동작명 분기 0)"
      exports: ["LIMB_CHAINS", "PROXIMAL_INSET_T", "buildFocusShapes", "PULSE_PERIOD_MS"]
      min_lines: 90
    - path: "app/src/lib/__tests__/focusShape.test.ts"
      provides: "선/원 분기·가시 구간·몸통 가로지르기 금지 단위 검증 (node --test)"
    - path: "app/src/components/PartChipsRow.tsx"
      provides: "S3 부위 칩 행 렌더 (승인 목업 ① .jointchips)"
      contains: "buildPartChips"
    - path: ".planning/quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/sweep_markers_focus.test.ts"
      provides: "등재 10동작 criteria yaml 파생 일반화 스위프 (부위 그룹·칩·선/원 분기)"
  key_links:
    - from: "app/src/components/KeypointOverlay.tsx"
      to: "app/src/lib/focusShape.ts"
      via: "focus 강조 형태 산출 소비 (기하 규칙 사본 0)"
      pattern: "from '\\.\\./lib/focusShape'"
    - from: "app/src/components/PartChipsRow.tsx"
      to: "app/src/lib/deductionSheet.ts"
      via: "칩 부위 정의 = regionPartKeyForRecord 재사용 (두 번째 그룹핑 규칙 금지)"
      pattern: "regionPartKeyForRecord|buildPartChips"
    - from: "app/src/app/analysis/result.tsx"
      to: "KeypointOverlay.markersVisible"
      via: "F-8 상시 마커 제거 게이트 (스켈레톤 토글 OR 음성 큐)"
      pattern: "markersVisible"
    - from: "app/src/lib/deductionLabels.ts"
      to: "buildDeductionMarkers.partGroups"
      via: "부위 그룹 마커 = 시트 부위 = 칩 부위 단일 출처"
      pattern: "partGroups"
---

<objective>
33-G §C-2 앱 수리 **2단위**. 승인 목업 7R 대비 반려분 중 **영상 위 표시 계층**을 수리한다.

- **S19 (FAIL / M-3)** — 음성 큐 강조가 지금은 `bounds circle` 하나뿐이고 `Animated` 가 0건이다.
  승인본 `.legfx` 규칙(kp 게이트 통과 → 사지 **모양 선**(가시 구간만) / 미달 → **부위 원**)과
  `.legfx.pulse` **1.4s** 를 구현한다.
- **S1 (PARTIAL)** — 마커를 **항목(부위) 단위 그룹**으로 통일한다(현재 스플릿 다리만 그룹, 어깨는
  관절 원 나열 = 2R#1 금지 사항).
- **S2 (PARTIAL)** — **실선 = 감점 / 점선 = 참고** 형태 구분을 그룹 경계까지 넓히고, 참고 안내
  문형을 한 소스로 통일한다(3R#3).
- **S3 (PARTIAL)** — 승인본 `.jointchips` **부위 칩**을 신설하고, 칩의 부위 정의는 1단위가 만든
  `regionPartKeyForRecord` 를 재사용한다(두 번째 그룹핑 규칙 금지).
- **F-8 (FAIL / D-42)** — `result.tsx:1530` "skeletonVisible 무관 상시 렌더" 를 제거한다. 마커는
  음성 큐 강조와 스켈레톤 토글에서만. 상시 진입점은 **부위 칩**이 대체한다.

Purpose: belle 확인 ② 반려의 영상 위 표시 축(§9 M-3 "빤짝빤짝 깜빡이기도 했는데", F-8 상시 마커,
2R#1 "동그라미가 7개") 해소. 재논의 없음(D-39) — 스펙 = 승인 목업 7R + EVIDENCE §9.
Output: 순수 로직 1모듈 + 칩 컴포넌트 1개 + 오버레이/화면 배선 + 10동작 스위프 + 시뮬 확인 요청표.

**채점 무접촉(D-44)**: 점수값·산식·임계·`deductionBreakdown` 소비 규칙 변경 0. 표현 계층만.
**배포 없음(D-45)**: OTA·EAS 금지. 일괄 배포는 §C-4 후 1회.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/CLAUDE.md
@.planning/phases/33-result-trust-recovery/33-G-MOCKUP-DIFF.md
@.planning/phases/33-result-trust-recovery/.continue-here.md
@app/src/components/KeypointOverlay.tsx
@app/src/lib/deductionLabels.ts
@app/src/lib/deductionSheet.ts
</context>

<approved_spec_extract>
승인 목업 `mockups/index.html` 에서 이 단위가 대조할 스펙만 발췌했다. **이 표가 정답이고,
구현이 이 표와 다르면 구현이 틀린 것이다**(D-40).

| 축 | 승인본 원문 근거 | 규칙 |
|---|---|---|
| pulse 주기 | `:227-228` `.legfx.pulse{animation:legpulse 1.4s ease-in-out infinite}` + `@keyframes legpulse{0%,100%{opacity:1;} 50%{opacity:.5;}}` | **1.4초 주기, opacity 1 → 0.5 → 1**. 대상 = 강조 선·원 SVG. `.dim` 은 별 div = **정적** |
| 모양 선 | `:222-224` `.legfx polyline{stroke:brand; stroke-width:5}` + `.halo{stroke:rgba(255,255,255,.72); stroke-width:9}` / `:452-453` 실 좌표 2줄(halo 먼저, core 나중) | **흰 halo 아래 + 브랜드 코어 위**, 굵기 비 9:5 |
| 부위 원 | `:225-226` `.legfx circle{stroke:brand; stroke-width:4}` + `.halo{stroke-width:8}` / `:454-455` `r=28` | 같은 halo 규칙, 굵기 비 8:4 |
| 선/원 분기 | `:219-221` 주석 "접힌 왼다리는 kp 게이트 미달+가림 → 모양 선을 긋지 않고 부위 원(circle)으로 표시 — '확신 없는 모양선은 긋지 않는다'" / `:442-443` 오른다리 conf 0.63/0.69/0.79 = **선**, 왼다리 knee 0.43·ankle 0.29 = **원** | **한 컷 안에서 측별로 섞인다.** 게이트 = 기존 `KEYPOINT_LOW_CONFIDENCE_THRESHOLD = 0.5` (신규 임계 금지) |
| 가시 구간만 | `:447-448` "오른다리 선 시작점 = hip 관절이 엉덩이 하단이라 선이 엉덩이를 가로질렀음 → hip→knee 실좌표 선분의 **65% 지점**(178.1,360.5)부터 — 가시 다리 구간만" | 근위 관절을 끝점으로 쓰지 않고 다음 관절 쪽으로 **inset** |
| 몸통 가로지르기 금지 | `:449-450` "일반 규칙(A-5/33-12): 멈춤 컷 마커는 감점 record 가 지칭하는 관절 그룹 위에 — **인접 관절이나 몸통을 가로지르는 연결선 금지**. record.jointKeys 로 키잉(동작명 하드코딩 금지)" | 좌↔우 교차 연결선 구조적 불가능해야 함 |
| 그룹 마커 | `:184-188` `.mkg{border:3px solid brand; border-radius:50%; box-shadow: 흰 링}` / `:331-335` "그룹 경계 = doc keypointReport kp34 실좌표의 **항목별 bounding**" / `:314-317` "1라운드는 관절 단위 원 7개 — 항목은 3개인데 동그라미가 7개라 혼란(belle) → **항목 단위 그룹 3개**" | 항목 단위 1경계. **관절 원 나열 금지** |
| 실선/점선 | `:182` `.mk.adv{border-style:dashed}` `:187` `.mkg.adv{border-style:dashed}` / `:348-350` legend "실선 그룹 = 감점 항목의 부위 … **점선 = 참고** — 점수 감점은 되지 않지만 회전·힘 같은 전체 동작에 영향을 줄 수 있는 부위예요" | 형태로 구분(실선/점선) + 문형 |
| 참고 문형 | `:336` title="왼손 (참고 — 감점은 아니지만 회전·힘에 영향을 줄 수 있어요)" / `:1091` `참고 — 감점은 아니지만 회전·힘에 영향` | 짧은 칩형 + 긴 안내형 2종, **전 표면 동일 소스** |
| 부위 칩 | `:192-196` `.jointchips{display:flex; gap:8}` `button{border:1px solid line-2; background:#fff; border-radius:999px; padding:8px 14px; font-size:14px; font-weight:800}` `.on{background:brand; color:#fff}` `.ref{color:#8b93a1; border-style:dashed; font-weight:600}` / `:338-342` `다리` `어깨` `참고: 손` / `:317` "그룹이나 아래 **부위 버튼**을 누르면 ② 상세로 이동해요" | 칩 = 상시 진입점 |
| 표시 수 | `:349` "화면의 표시 수 = **항목 수** = 3" | 칩 수 == 그룹 수 == 부위 시트 수 |
</approved_spec_extract>

<self_derived_decisions>
D-39 = 재논의 없음. 승인본이 답을 직접 주지 않는 지점은 아래 **N-항목**으로 자체 도출했다
(1단위가 M-1~M-21 을 썼으므로 이번 접두는 `N-`). 실행자는 이 결정을 그대로 따르고,
집행 중 새 판단이 필요하면 SUMMARY 에 `N-` 를 이어 붙여 기록한다. **belle 에게 묻지 않는다.**

| # | 지점 | 결정 | 근거 |
|---|---|---|---|
| **N-1** | "항목" 단위가 무엇인가 (마커 그룹 = record? 부위?) | **부위(`regionPartKeyForRecord`)**. 마커 그룹 = 칩 = 부위 시트 = 같은 단위 | 승인본 ①의 항목 3개(다리·어깨·참고 손)가 ②의 시트 3개·칩 3개와 1:1 이고, 1단위가 시트를 이미 부위 단위로 만들었다. record 단위로 두면 어깨 좌·우가 원 2개로 나열돼 2R#1 위반 |
| **N-2** | 부위 그룹에 감점 record 가 2건이면 배지 번호 | **번호 오름차순 병합 배지**(`2·3`). 1건이면 기존 원 배지 그대로 | 재생바 틱이 이미 같은 규칙(`buildDeductionTicks` "같은 시점은 번호 오름차순 병합", `VideoCompare:1269` `circledNumberKo` 조인). 번호 자체를 없애면 D-18 양방향 대응(이미 PASS)이 깨진다 |
| **N-3** | 병합 배지 탭 대상 | **첫(최소) 번호의 record** → 그 부위 시트가 열리고 블록 2개가 보인다 | 틱 선례 `onTickPress(tick.numbers[0])`. 부위 시트라 어느 멤버로 열어도 같은 시트 |
| **N-4** | 그룹에 흡수된 관절의 개별 원 | **브랜드 강조 원·번호 미렌더.** 스켈레톤 ON 이면 일반 흰 점(추적 스켈레톤 소속)으로만 | 2R#1 "관절 원 나열 금지". 현 구현이 그룹 타원 + 멤버 빨강 원 4개를 동시에 그리는 것이 S1 PARTIAL 의 실체 |
| **N-5** | 참고(advisory) 마커 색 | **앱 기존 `colors.advisoryOrange` 유지.** 승인본 CSS 회색(`#8b93a1`)으로 바꾸지 않는다 | S2 의 판정축은 "실선/점선" **형태** 구분이다. 색을 회색으로 바꾸면 표·확대 카드·칩의 주황 2단 시각 언어(quick-260704-fz4, 이미 PASS)와 3표면이 어긋난다 — over-generalize-breaks-approved 방지 |
| **N-6** | 참고 칩 탭 목적지 | **인라인 안내 1줄 펼침**(기존 긴 문형 상수 재사용). 크롭 포함 advisory 상세 시트는 **이관** | advisory 는 `record` 가 없어(`matchZoomForDeductionRecord` 가 advisory 제외) 시트 뷰모델 입력이 성립하지 않는다. 시트를 새로 만드는 것은 수리에 새 범위(D-39) |
| **N-7** | pulse 구현 방식 | **강조 레이어를 별 `Animated.View` + 자체 `<Svg>` 로 분리하고 View opacity 를 `useNativeDriver: true` 로 애니메이트** | react-native-svg prop 애니메이션은 native driver 불가 → JS 구동 시 프레임마다 리렌더 + RN 경고 위험. 결과 화면에 이미 정체 미상 LogBox 배너가 있어(1단위 미해결) 새 경고를 얹지 않는다 |
| **N-8** | dim 도 깜빡이나 | **아니오.** dim `Rect` 는 기존 `<Svg>` 에 정적으로 남기고 강조 선/원만 pulse | 승인본 `.dim` 은 `.legfx.pulse` 밖의 별 div. 화면 전체가 밝기 진동하면 S18(이미 PASS)의 "정지+dim" 표현이 깨진다 |
| **N-9** | reduce-motion 대응 | **이 단위 범위 밖** — 기록만 | 승인본이 pulse 를 지정했고 a11y 분기는 새 범위. 무한 깜빡임의 a11y 우려는 deferred 로 남긴다 |
| **N-10** | 근위 inset 값 | **체인의 근위 관절 역할로 키잉**: `hip → 0.65`, `shoulder → 0` | 0.65 = 승인본 7R 실좌표 실측(`hip(161.3,334.7) → (178.1,360.5)`). shoulder 0 = 승인본이 팔 체인 선을 제시하지 않았고 어깨 관절 자체는 몸통을 가로지르지 않는다 → 값 날조 금지. 관절 역할 키잉이라 10동작 동일 |
| **N-11** | 선의 점 집합 | **focus 관절이 속한 사지 체인에서 focus 관절을 포함하는 최장 연속 고신뢰 구간** | 승인본이 다리 record 의 jointKeys 에 ankle 이 없는데도 ankle 까지 그렸다(`:442`) → 승인본 규칙은 "focus 가 짚은 사지의 **가시 구간 전체**". "가시 구간만" 문구가 곧 conf 게이트 |
| **N-12** | 좌↔우 연결 | **체인 사전을 측별 사지 4개로만 정의**(L/R 다리, L/R 팔). 교차 쌍은 체인에 없다 | `:449` "몸통을 가로지르는 연결선 금지" 를 데이터 구조로 강제 — 조건문으로 막으면 새 criterion 에서 다시 뚫린다 |
| **N-13** | 마커 숨김 시 번호 ↔ 내역 행 대응 | **허용.** 내역 행·재생바 틱·여백 범례·부위 칩 4진입점이 남으므로 번호 의미는 유지 | D-42 가 상시 마커를 제거하라고 명시했고, 승인본 ①의 "표시 수 = 항목 수" 는 칩 행이 담당한다 |
| **N-14** | cleanPass(감점 0) 문서 | **칩 행 자체 미렌더** | 승인본 ① 은 감점 항목 화면이다. 칩 0개 빈 행은 "새 문장 0"(D-05·S5) 위반 |
| **N-15** | 마커 숨김 시 탭 레이어 | `tapTargets` 를 빈 배열로 만들어 **보이지 않는 44pt Pressable 이 남지 않게** 한다 | 안 보이는 탭 = belle 반려 계열 결함(신뢰). 마커가 없으면 탭도 없다 |
</self_derived_decisions>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 순수 로직 — S19 선/원 분기 + 부위 그룹·칩 단위 + 참고 문형 단일화</name>
  <files>app/src/lib/focusShape.ts, app/src/lib/__tests__/focusShape.test.ts, app/src/lib/deductionLabels.ts, app/src/lib/deductionSheet.ts, app/src/lib/__tests__/deductionSheet.test.ts</files>
  <behavior>
    `focusShape.test.ts` (신규):
    - 다리 focus + hip/knee/ankle conf 0.63/0.69/0.79 → 체인 1개, 점 3개(선), `insetT === 0.65`
    - 같은 focus 인데 knee conf 0.43 · ankle 0.29 → 그 측은 체인 0개 · 원 그룹 1개 (승인본 7R 컷 2 재현)
    - 양다리 focus 에서 오른쪽만 고신뢰 → **선 1개 + 원 1개 동시 반환**(측별 혼재)
    - `left_shoulder` 단독 focus + elbow/hand 저신뢰 → 체인 0개 · 원 그룹 1개
    - `left_shoulder` + elbow/hand 고신뢰 → 팔 체인 선, `insetT === 0`
    - `[left_shoulder, right_shoulder]` focus → **어떤 체인에도 좌·우 관절이 함께 들어가지 않는다**(N-12)
    - focus 관절이 report 에 없거나 전부 저신뢰 → `{ chains: [], circleGroups: [] }` (환각 드로잉 0)
    - `PULSE_PERIOD_MS === 1400`
    `deductionSheet.test.ts` (기존 파일 확장 — 기존 25 테스트 무회귀):
    - 어깨 좌 + 어깨 우 2 record → `partGroups` 1개, `numbers` 오름차순, `badgeLabel === '2·3'` 형태(N-2)
    - 감점 record 1건 부위 → `badgeLabel` 이 단일 숫자
    - `partGroups` 의 `keypoints` 합집합이 그 부위 멤버 record 투영의 합집합과 같다 (누락 0)
    - `buildPartChips`: 감점 부위 칩 순서 = 첫 등장 순, 라벨 = 부위 시트 제목과 동일 문자열
    - `buildPartChips`: attention 관절만 있는 부위 → `kind === 'advisory'`, 라벨 `참고: {부위}`
    - `buildPartChips`: records 0 → 빈 배열 (N-14)
    - 참고 문형 상수 2종(칩형·안내형)이 export 되고, 문자열이 승인본 원문과 일치
  </behavior>
  <action>
**1-A. `app/src/lib/focusShape.ts` 신설 (순수 모듈, RN import 0).**
모듈 헤더 주석에 승인본 근거를 `mockups/index.html:219-228,442-450` 형태로 인용하고 N-10~N-12 를 명기한다.

- `LIMB_CHAINS`: 측별 사지 4개 체인. 각 항목 = `{ proximalRole: 'hip' | 'shoulder'; keypoints: readonly KeypointName[] }`
  로, 근위→원위 순서. 다리 = hip → knee → ankle(좌/우), 팔 = shoulder → elbow → hand(좌/우).
  `KeypointName` 은 `../types/analysis` 에서 `import type` 으로 받는다. **좌·우가 섞인 체인은 정의하지 않는다(N-12).**
  `KeypointOverlay.BONES` 의 `shoulder↔shoulder` / `hip↔hip` / `shoulder↔hip` 같은 몸통 쌍은 체인이 아니므로 복사하지 말 것.
- `PROXIMAL_INSET_T: Record<'hip' | 'shoulder', number>` = `{ hip: 0.65, shoulder: 0 }`. 두 값 각각에
  근거 주석(0.65 = 승인본 실좌표 실측 / 0 = 승인본 미제시 → 날조 금지)을 붙인다.
- `PULSE_PERIOD_MS = 1400` — 승인본 `.legfx.pulse` 1.4s 단일 선언. 오버레이가 import 한다(사본 금지).
- `buildFocusShapes(input)` 순수 함수:
  - 입력 = `{ focusKeypoints: readonly KeypointName[]; confidenceOf: (kp: KeypointName) => number | null; threshold: number }`.
    좌표는 받지 않는다 — 좌표/여백/정규화는 오버레이 책임(D-12 §12 UI 산출 금지 관례와 정합).
  - 반환 = `{ chains: { keypoints: KeypointName[]; insetT: number }[]; circleGroups: KeypointName[][] }`.
  - 알고리즘: 각 체인마다 `focusKeypoints` 와의 교집합이 비면 skip. 교집합이 있으면 체인 배열 위에서
    **focus 관절을 포함하는 최장 연속 고신뢰 런**(`confidenceOf(kp) != null && >= threshold`)을 구한다(N-11).
    런 길이 ≥ 2 → `chains` 에 `{ keypoints: run, insetT: PROXIMAL_INSET_T[proximalRole] }`.
    런 길이 < 2 → 그 체인의 focus∩고신뢰 관절들을 `circleGroups` 에 1묶음으로. 고신뢰 0 이면 아무것도 넣지 않는다.
  - 체인 어디에도 안 속하는 focus 관절(예: 미래 확장 관절)은 고신뢰인 것만 모아 `circleGroups` 마지막 1묶음으로 — fail-open 아님, 원은 항상 안전한 표시.
  - `insetT` 는 런의 첫 원소가 그 체인의 **근위 관절 자체일 때만** 적용한다(런이 knee 부터 시작하면 inset 0 — 이미 몸통 밖).

**1-B. `deductionLabels.ts` — `buildDeductionMarkers` 에 `partGroups` 추가 (기존 3필드 무변경).**
기존 `recordNumbers` / `keypointNumbers` / `groupMarkers` 산출 로직은 **한 줄도 바꾸지 않는다**
(내역 행 번호·행동구 후보 게이트·틱이 그대로 소비 중). 반환 객체에만 필드를 더한다:

```
partGroups: { partKey: string; numbers: number[]; badgeLabel: string; keypoints: KeypointName[] }[]
```

산출 규칙: records 를 순회하며 `regionPartKeyForRecord(rec, faultJoints)`(deductionSheet 에서 import —
**두 번째 그룹핑 규칙 작성 금지**) 로 부위 키를 얻고, 부위별로 (a) `recordNumbers[i]` 가 null 아닌 것만
`numbers` 에 push, (b) `projectDeductionRecordKeypoints(rec, faultJoints)` 전부를 `keypoints` 합집합에 넣는다.
순서 = 부위 첫 등장 순. `numbers` 는 오름차순 정렬. `badgeLabel` = `numbers.join('·')`(N-2), `numbers` 가
비면 그 부위는 `partGroups` 에서 제외(번호 없는 경계 = 고아 표시). 투영 keypoint 가 0개인 부위
(`line` 계열 collective criterion 등)도 제외 — 그릴 자리가 없다.

⚠ `deductionSheet.ts` → `deductionLabels.ts` 는 이미 한 방향 의존이다. 순환을 만들지 않도록
`regionPartKeyForRecord` 를 `deductionLabels` 로 옮기지 말고, **`partGroups` 산출 함수를
`deductionSheet.ts` 에 두고 `buildDeductionMarkers` 가 그것을 호출**하는 방향이 순환이면
반대로 `buildPartGroups(records, recordNumbers, faultJoints)` 를 `deductionSheet.ts` 에 export 하고
`result.tsx` 가 `markers` 와 나란히 호출한다. 어느 쪽이든 **부위 키 산출 사본은 0벌**이어야 한다.
`import` 방향을 실제 파일에서 확인한 뒤 결정하고, 선택 근거를 SUMMARY 에 `N-` 로 기록한다.

**1-C. `deductionSheet.ts` — 칩 빌더 + 부위 라벨 export + 참고 문형 단일화.**
- 기존 private `titleForPartKey` 를 `export function partLabelKo(partKey: string): string` 으로 승격
  (호출부 그대로). 칩 라벨과 시트 제목이 문자 단위로 같아야 한다(승인본 어휘 통일).
- `buildPartChips(input)` 신설:
  - 입력 = `{ records: DeductionRecord[]; recordNumbers: (number | null)[]; faultJoints; attentionKeypoints: readonly KeypointName[]; estimatedArea: boolean }`
  - 반환 = `{ partKey: string; label: string; kind: 'deduction' | 'advisory'; firstRecordIndex: number | null; numbers: number[] }[]`
  - 감점 칩: `partGroups` 와 동일 부위 집합·동일 순서(사본 금지 — 같은 헬퍼 소비). `label = partLabelKo(partKey)`,
    `firstRecordIndex` = 그 부위의 최소 번호를 가진 record 인덱스(N-3).
  - 참고 칩: `attentionKeypoints` 를 `BODY_PART_OF_KEYPOINT` 로 접어 부위 토큰 dedup(감점 부위와 겹치면 제외),
    `label = '참고: ' + BODY_PART_LABEL_KO[token]`, `kind='advisory'`, `firstRecordIndex = null`.
    순서 = 기존 `PART_ORDER`.
  - `records.length === 0` → `[]`(N-14). `estimatedArea === true` → `[]` (IN-01 전용 진입점 카드가
    이미 있고, 저신뢰에서 부위 단정 칩은 S17 PASS 를 깬다).
- 참고 문형 상수 2종을 export 하고 **다른 파일의 사본을 지운다**:
  - `ADVISORY_NOTE_KO` = 기존 `:68` 긴 안내 문형 문자열 그대로(값 변경 0).
  - `ADVISORY_CHIP_KO` = `'참고 — 감점은 아니지만 회전·힘에 영향'` (승인본 `:1091`·`DeductionDetailSheet:99`
    와 문자 동일). `DeductionDetailSheet.tsx` 의 local `CHIP_ADVISORY` 선언을 제거하고 이 상수를 import 한다.

**금지**: 새 임계 상수 신설(conf 0.5 = `KeypointOverlay.KEYPOINT_LOW_CONFIDENCE_THRESHOLD` 재사용,
20° = 기존 상수), 동작명 문자열(`power-spin`·`kip-up` 등) 등장, 채점 필드 재계산, 초 추정(인덱스 ÷ fps).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && node --test app/src/lib/__tests__/focusShape.test.ts && node --test app/src/lib/__tests__/deductionSheet.test.ts && cd app && npm run typecheck && grep -Ev '^[[:space:]]*(//|\*|/\*)' src/lib/focusShape.ts src/lib/deductionSheet.ts src/lib/deductionLabels.ts | grep -Eci "power-spin|kip-up|pdshape|foxtop|peter-pan|sideway-spin|elbow-twist" | grep -qx 0 && grep -c "PULSE_PERIOD_MS = 1400" src/lib/focusShape.ts | grep -qx 1 && grep -Ev '^[[:space:]]*(//|\*|/\*)' src/components/DeductionDetailSheet.tsx | grep -c "감점은 아니지만" | grep -qx 0 && echo GATE_OK</automated>
  </verify>
  <done>`focusShape.test.ts` 신규 8축 + `deductionSheet.test.ts` 기존 25 무회귀 + 신규 7축 전부 pass. typecheck clean. focusShape/deductionSheet/deductionLabels 주석 제외 본문에 동작명 0건. `PULSE_PERIOD_MS = 1400` 단일 선언. `DeductionDetailSheet.tsx` 본문에 참고 문형 사본 0건(lib 상수 import).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: KeypointOverlay 렌더 — 선/원 분기 + pulse 1.4s + 점선 그룹 + 마커 가시성 게이트</name>
  <files>app/src/components/KeypointOverlay.tsx</files>
  <behavior>
    (렌더 컴포넌트라 단위 테스트 대상이 아님 — 계약은 Task 1 순수 함수가 지고, 이 태스크의 검증축은
    typecheck + grep 게이트 + Task 3 의 시뮬 확인 요청표다. `<behavior>` 는 구현이 만족해야 할
    관찰 가능한 조건으로 읽는다:)
    - `markersVisible` 미전달(기존 소비처 = `PoseCompareFrames`, reference 측) → 렌더 diff 0
    - `markersVisible={false}` → 그룹 경계·번호 배지·확정 빨강 원·참고 점선 원·탭 레이어 전부 0
    - `focusKeypoints` 고신뢰 사지 → polyline(halo 아래 + brand 위), 미달 → 타원, 둘 다 pulse
    - `focusKeypoints` 고신뢰 0 → dim 도 미렌더 (기존 게이트 보존)
    - 그룹 경계에 흡수된 관절 → 브랜드 강조 원·번호 미렌더 (스켈레톤 ON 이면 일반 흰 점만)
  </behavior>
  <action>
**2-A. props 확장 (하위호환 default 로 렌더 diff 0).**
- `markersVisible?: boolean` (default `true`) — F-8 게이트. 감점 마커 계층(그룹 경계 + 번호 배지 +
  확정/참고 개별 원 + 탭 히트 레이어)만 끈다. **`focusBounds`/dim/스켈레톤에는 영향 주지 않는다**
  (음성 큐 강조는 D-42 가 유지하라고 명시). JSDoc 에 D-42 근거를 적는다.
- `groupMarkers` 항목 타입을 `{ number: number; keypoints: KeypointName[]; badgeLabel?: string; advisory?: boolean }`
  로 확장(둘 다 optional → 기존 호출 무회귀). `badgeLabel` 미전달 시 `String(number)` 폴백.

**2-B. 선/원 분기 + pulse — 기존 `focusBounds` 블록 교체.**
`buildFocusShapes` 를 `../lib/focusShape` 에서 import 하고, `focusKeypoints` 가 있을 때
`confidenceOf = (kp) => positions.get(kp)?.confidence ?? null`, `threshold = KEYPOINT_LOW_CONFIDENCE_THRESHOLD`
로 호출한다. 결과를 좌표로 환산:
- 각 `chain` → 점 배열 = `keypoints.map(kp => positions.get(kp)!)`. 첫 원소가 그 체인 근위 관절이고
  `insetT > 0` 이면 첫 점을 `lerp(p0, p1, insetT)` 로 대체(승인본 65% 규칙). `Polyline` 로 그린다 —
  halo(`stroke="#FFFFFF"`, opacity 0.72, 굵기 = core × 9/5) 먼저, brand core 나중. 굵기는 기존
  `STROKE_HI` 파생으로 잡아 `sizeScale` 규칙을 자동 계승한다(신규 절대 px 금지).
- 각 `circleGroup` → 기존 `boundsFor(group)` 으로 타원. halo(굵기 = core × 8/4) 먼저, brand core 나중.
- **dim `Rect` 는 기존 `<Svg>` 에 그대로 남긴다**(N-8). 렌더 조건 = `chains.length + circleGroups.length > 0`
  (강조 없는 어두운 화면 금지 = 기존 규칙 승계).
- 강조 도형(선·원)만 **별 `Animated.View`(`StyleSheet.absoluteFillObject`, `pointerEvents="none"`) 안의
  자체 `<Svg viewBox="0 0 1 1" preserveAspectRatio="none">`** 로 옮기고, 그 View 의 `opacity` 를
  애니메이트한다(N-7). 구현:
  - `const pulse = useRef(new Animated.Value(1)).current;` — 다른 hook 들과 함께 **early return 이전**에 선언(hook 순서 규칙).
  - `useEffect` 안에서 `Animated.loop(Animated.sequence([Animated.timing(pulse, { toValue: 0.5, duration: PULSE_PERIOD_MS / 2, easing: Easing.inOut(Easing.ease), useNativeDriver: true }), Animated.timing(pulse, { toValue: 1, duration: PULSE_PERIOD_MS / 2, easing: Easing.inOut(Easing.ease), useNativeDriver: true })]))` 를
    시작하고, cleanup 에서 `loop.stop()` + `pulse.setValue(1)`. 의존성 = 강조 존재 여부 boolean 1개
    (매 프레임 재구독 금지 — 좌표 배열을 의존성에 넣지 말 것).
  - 강조가 없으면 loop 을 시작하지 않는다.
  - `Animated`·`Easing` 은 `react-native` 에서 import. **신규 npm 의존성 0**(reanimated 도입 금지 —
    네이티브 빌드 필요, OTA 불가).

**2-C. 실선/점선 그룹 (S2).**
`groupMarkers` 렌더에서 `advisory === true` 이면 `stroke={colors.advisoryOrange}`(N-5) +
`strokeDasharray` (기존 개별 참고 점의 `(3 * S) / W` 규칙 재사용, 상수 신설 0), 배지도 advisoryOrange.
`advisory` 아니면 현행 brand 실선 그대로.

**2-D. 그룹 흡수 관절의 개별 원 억제 (S1 / N-4).**
`groupBounds` 산출 후 `groupedKeypoints = new Set(groupMarkers.flatMap(g => g.keypoints))` 를 만들고,
keypoint circle 루프에서 `groupedKeypoints.has(joint)` 인 관절은 `isHi`/`num` 을 강제로 끈다
(→ 스켈레톤 ON 이면 일반 흰 점, OFF 면 기존 게이트로 미렌더). `attentionJoints` 는 영향 없음
(참고 점은 그룹에 안 들어간다).

**2-E. 배지 병합 표기 (N-2).**
배지 텍스트를 `g.badgeLabel ?? String(g.number)` 로 바꾸고, 문자 길이 ≥ 2 면 원 대신 **`Rect`
(rx = 높이/2, 폭 = 글자수 파생, brand fill + 흰 stroke)** 로 그려 숫자가 잘리지 않게 한다.
길이 1 은 기존 `Circle` 경로 유지(무회귀).

**2-F. 마커 가시성 게이트 적용 (F-8).**
`markersVisible === false` 이면 (a) `groupBounds` 렌더 skip, (b) keypoint circle 루프에서 `isHi`/`isAttn`
강조 원·번호 skip(스켈레톤 ON 이면 일반 흰 점은 유지), (c) `tapTargets` 를 빈 배열로 만들어
Pressable 레이어 자체가 렌더되지 않게 한다(N-15).

**금지**: `reanimated`/신규 패키지, `useNativeDriver: false`, 하드코딩 색·px(테마 토큰 + 기존 파생 상수만),
`skeletonVisible` 기본값 변경, `visible` prop semantics 변경, reference 측 오버레이 거동 변경.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npm run typecheck && grep -c "PULSE_PERIOD_MS" src/components/KeypointOverlay.tsx | grep -qv '^0$' && grep -c "useNativeDriver: true" src/components/KeypointOverlay.tsx | grep -qv '^0$' && grep -Ev '^[[:space:]]*(//|\*|/\*)' src/components/KeypointOverlay.tsx | grep -c "useNativeDriver: false" | grep -qx 0 && grep -c "markersVisible" src/components/KeypointOverlay.tsx | grep -qv '^0$' && grep -c "reanimated" package.json | grep -qx 0 && node -e "const s=require('fs').readFileSync('src/components/KeypointOverlay.tsx','utf8'); if(!/Animated\.loop/.test(s)) throw new Error('no Animated.loop'); if(!/loop\.stop\(\)/.test(s)) throw new Error('no loop cleanup'); if(!/buildFocusShapes/.test(s)) throw new Error('focusShape 미소비'); console.log('OVERLAY_OK')"</automated>
  </verify>
  <done>typecheck clean. `buildFocusShapes` 소비 + `PULSE_PERIOD_MS` import(1.4s 사본 0) + `Animated.loop` + `loop.stop()` cleanup + `useNativeDriver: true` 존재, `false` 0건. `markersVisible` prop 존재. `reanimated` 미도입. 신규 hex 색 리터럴은 기존 `#FFFFFF` 계열 halo 외 증가 없음(diff 로 확인).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: result.tsx 배선 — 부위 칩 행 + F-8 상시 마커 제거 + 10동작 스위프 + 시뮬 확인 요청표</name>
  <files>app/src/components/PartChipsRow.tsx, app/src/app/analysis/result.tsx, .planning/quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/sweep_markers_focus.test.ts</files>
  <behavior>
    `sweep_markers_focus.test.ts` — `backend/judging_data/criteria/*.yaml` **10개 전부**에서 파생한
    합성 record 로 아래 불변식을 검사한다(동작명 하드코딩 0, glob 파생):
    - 각 동작: `partGroups.length === buildPartChips(kind==='deduction').length === 부위 시트 수` (표시 수 = 항목 수)
    - 각 동작: 모든 감점 record 의 투영 keypoint 가 **정확히 한** `partGroups` 항목에 속한다 (고아·중복 0)
    - 각 동작: `partGroups[*].badgeLabel` 이 그 부위 멤버 번호 오름차순 조인과 일치
    - 각 동작: 칩 라벨 == 그 부위 시트 제목(`partLabelKo`) 문자 동일
    - 각 동작 × 각 criterion: `buildFocusShapes` 결과에 좌·우 관절이 함께 든 체인 0개
    - 각 동작 × 각 criterion: 전 관절 conf 0.9 → 체인 또는 원이 1개 이상 / 전 관절 conf 0.1 → 체인 0 · 원 0
    - 스위프 산출 요약(동작별 부위 수·칩 수·선/원 분기 수)을 이 디렉터리 `sweep_markers_focus.json` 으로 남긴다
  </behavior>
  <action>
**3-A. `app/src/components/PartChipsRow.tsx` 신설.**
승인본 `.jointchips` 규칙 렌더. props = `{ chips: PartChip[]; onPressPart: (recordIndex: number) => void }`.
- 컨테이너: `flexDirection:'row'`, `flexWrap:'wrap'`, `gap: spacing` 토큰, 카드 내부 여백 정합.
- 감점 칩: `Pressable`, 흰 배경 + `colors` 테두리 토큰 + `borderRadius: 999`, 두꺼운 글자.
  `onPress={() => onPressPart(chip.firstRecordIndex!)}`. `accessibilityRole="button"`,
  `accessibilityLabel` = `` `${chip.label} 부위 상세 보기` ``, `hitSlop={8}`.
- 참고 칩: `Pressable` 이지만 목적지는 **인라인 안내 토글**(N-6) — 눌리면 칩 행 아래에
  `ADVISORY_NOTE_KO` 1줄을 회색 캡션으로 펼치고 다시 누르면 접는다. 형태 = 점선 테두리 +
  `colors.advisoryOrange` 글자(N-5, 승인본 `.ref` 의 dashed/약한 글자 규칙 계승, 색만 앱 언어).
  `accessibilityLabel` = `` `${chip.label} — ${ADVISORY_CHIP_KO}` ``.
- **하드코딩 색·radius·spacing 금지** — `src/theme` 토큰만. `StyleSheet.create` 는 파일 하단.
- 이모지 0, 새 문장 신설 0(라벨·문형은 전부 lib 상수/빌더 산출).

**3-B. `result.tsx` 배선.**
1. `buildPartChips` / `partGroups` 소비 memo 를 `markers` memo 바로 아래에 추가.
   입력의 `attentionKeypoints` 는 **기존 `attentionKeypoints` memo**(`:1034`)를, `estimatedArea` 는
   기존 `attributionUnreliable` 을 그대로 넘긴다(새 판정 신설 금지).
2. `overlayGroupMarkers` 를 `attributionUnreliable ? [] : (hasBreakdownRecords ? partGroups : markers.groupMarkers)` 로
   바꾼다. `partGroups` 를 쓰는 경로에서는 **`overlayMarkerNumbers` 를 `{}`** 로 넘겨 개별 번호 점을
   끈다(N-4 — 그룹 배지가 번호를 진다). legacy(breakdown 부재)는 현행 그대로.
3. **F-8**: `leftOverlay` 의 `KeypointOverlay` 에 `markersVisible={overlayVisible || opts?.voiceCueRecordId != null}` 를
   추가한다. `:1527-1531` 의 "감점 마커(…)는 skeletonVisible 무관 상시 렌더" 주석을 **D-42 근거로 교체**
   (문구가 남으면 grep 게이트 FAIL). `visible={true}` 는 유지 — 음성 큐 dim/강조가 이 레이어에 얹힌다.
4. 칩 행 렌더: `<VideoCompare ... />` **직후**, `result.motionAlignment === undefined` 배너 블록 **이전**에
   `chips.length > 0 && <PartChipsRow chips={chips} onPressPart={setDetailRecordIndex} />` 를 넣는다
   (승인본 ① 은 칩을 캡처 카드 바로 아래에 둔다). `setDetailRecordIndex` 는 기존 시트 state — 진입점
   신설이 아니라 5번째 진입점 추가.
5. 회귀 보호: `onLegendPress` / `onTickPress` / `cueWindows` / `audioAnalysisId` / `fullscreenLegend` /
   `alignment` prop 은 **한 글자도 건드리지 않는다**(S18·S20 PASS 보존).

**3-C. 10동작 일반화 스위프 (`sweep_markers_focus.test.ts`).**
`node --test` + `node:assert/strict`, 신규 의존성 0. `backend/judging_data/criteria/*.yaml` 를
`fs.readdirSync` **glob 파생**으로 열고(동작 목록 하드코딩 금지) 각 yaml 의 criterion id 목록으로
합성 `DeductionRecord[]` 를 만든다. yaml 파싱은 1단위 `sweep_sheet_blocks.test.ts` 의 방식을 그대로
재사용한다(같은 파일 형식 — 파서 사본 만들지 말고 그 접근을 따를 것). 위 `<behavior>` 7축을 검사하고
요약 JSON 을 이 디렉터리에 쓴다.

**3-D. SUMMARY 에 `## 시뮬 확인 요청 (오케스트레이터)` 표 작성.**
실행자는 `mcp__ios-simulator__*` 를 갖고 있지 않다 → **33-G 표(S19·S1·S2·S3·F-8 행)를 갱신하지 말고**
재채점 제안만 별 절에 적는다. 표 열 = `# / 케이스 / 도달 경로 / 대조할 승인 요소 / PASS 조건`.
1단위 SUMMARY 의 같은 절 형식을 따르고, 아래를 **반드시** 포함한다:

- **F-8**: 결과 화면 진입 직후(스켈레톤 토글 OFF) 영상 위 마커 **0개** + 칩 행 보임 → 토글 ON 시 부위
  그룹 경계 등장. PASS 조건에 "칩·재생바 cuedot·내역 행·여백 범례 4진입점이 살아있다" 포함.
- **S19 pulse**: **정지 스크린샷으로 판정 불가** → `mcp__ios-simulator__record_video` 로 재생 중 음성 큐
  구간을 **3초 이상** 녹화하거나, 그것이 불가하면 `mcp__ios-simulator__screenshot` 을 **0.35초 간격 5장**
  연속 캡처해 강조 도형의 밝기가 진동하는지 확인. PASS 조건 = 1.4초 주기로 밝아짐/어두워짐이 왕복하고
  **dim 배경은 일정**(N-8). 도달 경로 = 동작 비교 카드 재생 → 재생바 cuedot 위치 도달 시 자동 정지+자막.
- **S19 선/원**: 파워스핀 80(팔꿈치·어깨·무릎 각 1건)에서 **다리 부위 큐**를 잡아 선이 나오는지,
  가림·저신뢰 측에서 원으로 떨어지는지. PASS 조건에 "선이 몸통을 가로지르지 않는다(좌우 연결 0)",
  "선 시작점이 엉덩이 관절이 아니라 다리 쪽으로 들어와 있다"(승인본 65%) 포함.
- **S1 / N-4**: 엘보 60 doc(한 부위 2감점 존재, 확대 카드 0장)에서 토글 ON 시 **부위 경계 1개 + 병합
  배지(`2·3` 형태)**, 그 부위 멤버 관절에 **개별 빨강 원 나열 0**. 파워스핀 80 에서 **어깨 그룹이
  생겼는지**(현재 FAIL 축).
- **S2**: 참고 관절이 있는 doc 에서 점선 형태 확인 + 참고 칩의 인라인 안내 문장이 시트 onecap 문장과
  **같은 문장**인지 대조.
- **S3**: 칩 수 == 부위 시트 수(파워스핀 3 / 킵업 2), 칩 탭 → 그 부위 시트가 열리고 1단위의 블록 N개
  구조가 그대로 보임(회귀 0).
- **cleanPass**: pdshape 100 에서 칩 행이 **아예 없음**(N-14).
- **회귀**: S18(음성 중 정지·dim·"잠시 멈춤" 라벨·자막) / S20(cuedot 탭 → 항목 이동) / 1단위 시트 구조 /
  IN-01 예상 부위 카드 — 4축 무회귀.
- **LogBox**: 1단위에서 관측된 정체 미상 경고 배너가 **늘지 않았는지**(Animated 도입으로 새 경고 유발 여부).

렌더 가능한 검증 doc 4건은 **§C-1 이전 산출이라 `userVideoSec`/`refVideoSec` 가 없다** — 이 단위는 그
필드에 새로 의존하지 않으므로 위 케이스 전부 도달 가능하다. 도달 불가 케이스가 생기면 SUMMARY 에
"§C-4 doc 재산출 후 판정" 으로 명시하고 PASS 를 주장하지 말 것.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && node --test .planning/quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/sweep_markers_focus.test.ts && node --test app/src/lib/__tests__/focusShape.test.ts && node --test app/src/lib/__tests__/deductionSheet.test.ts && node --test app/src/lib/__tests__/visualCards.test.mjs && cd app && npm run typecheck && grep -c "skeletonVisible 무관 상시 렌더" src/app/analysis/result.tsx | grep -qx 0 && grep -c "markersVisible" src/app/analysis/result.tsx | grep -qv '^0$' && grep -c "PartChipsRow" src/app/analysis/result.tsx | grep -qv '^0$' && grep -Ev '^[[:space:]]*(//|\*|/\*)' src/components/PartChipsRow.tsx | grep -Ec "#[0-9A-Fa-f]{3,6}" | grep -qx 0 && grep -Ec "compareFrames\.(userIdx|refIdx) /" src/app/analysis/result.tsx | grep -qx 0 && node -e "const s=require('fs').readFileSync('src/app/analysis/result.tsx','utf8'); for(const p of ['onLegendPress={openRecordByNumber}','onTickPress={openRecordByNumber}','cueWindows={cueWindows}','audioAnalysisId={coachAudioAnalysisId}']) if(!s.includes(p)) throw new Error('회귀: '+p); console.log('WIRING_OK')" && ls ../.planning/quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/sweep_markers_focus.json</automated>
  </verify>
  <done>스위프 10동작 7축 pass + 기존 앱 테스트(deductionSheet 25+·visualCards) 무회귀 + typecheck clean. `result.tsx` 에 "skeletonVisible 무관 상시 렌더" 0건, `markersVisible`·`PartChipsRow` 배선 존재. `PartChipsRow.tsx` 본문 hex 색 리터럴 0(토큰만). S18/S20 배선 4개 문자열 그대로 존재. `sweep_markers_focus.json` 생성. SUMMARY 에 시뮬 확인 요청표(F-8·pulse 다중프레임·선/원·S1 병합배지·S2 문형·S3 칩수·cleanPass·회귀 4축·LogBox) + 33-G 재채점 **제안**(표 미갱신) 기재.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore doc → 앱 렌더 | 백엔드가 쓴 `deductionBreakdown`/`keypointReport`/`faultZoomComparisons` 를 앱이 그린다. 신뢰 경계는 **표시 정직성**(없는 걸 그리지 않기)이지 인증이 아니다 — 이 단위는 네트워크·인증·시크릿 표면을 건드리지 않는다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-33G3-01 | Tampering(표시 왜곡) | `focusShape.buildFocusShapes` | mitigate | 저신뢰·결측 좌표에서 선을 긋지 않고 원으로 강등, 둘 다 불가면 빈 결과. 단위 테스트 2축(전 관절 0.1 → 체인 0·원 0)으로 고정 |
| T-33G3-02 | Information Disclosure(거짓 구체성) | 부위 칩 라벨·참고 문형 | mitigate | 라벨은 `partLabelKo`(시트 제목과 문자 동일), 문형은 `ADVISORY_NOTE_KO`/`ADVISORY_CHIP_KO` 단일 상수. 신규 문장 조립 금지 — grep 게이트가 사본 0 확인 |
| T-33G3-03 | Denial of Service(성능·크래시) | `Animated.loop` 무한 애니메이션 | mitigate | `useNativeDriver: true` + 의존성 boolean 1개 + cleanup `loop.stop()`. 강조 없으면 loop 미시작. `useNativeDriver: false` grep 금지 게이트 |
| T-33G3-04 | Repudiation(검증 공백) | 실행자 자기 렌더 검증 불가 | mitigate | 33-G 표 갱신 금지 + 시뮬 확인 요청표(도달 경로·승인 요소·PASS 조건) 위임. pulse 는 다중 프레임/녹화 절차 명시 |
| T-33G3-05 | Elevation(범위 침범) | 이미 PASS 인 S18·S20·S14~S17·1단위 시트 | mitigate | prop 4개 문자열 존재 assert + `markersVisible` default `true` + `visible`/`skeletonVisible` semantics 무변경 + 기존 테스트 무회귀 게이트 |
| T-33G3-SC | Tampering | npm/pip/cargo installs | mitigate | **신규 패키지 0** (`Animated`/`Easing` = react-native 내장, `reanimated` 도입 금지 — `grep -c reanimated package.json == 0` 게이트). 설치 태스크가 없으므로 legitimacy 체크포인트 불요 |
</threat_model>

<verification>
1. `node --test app/src/lib/__tests__/focusShape.test.ts` — 선/원 분기 8축
2. `node --test app/src/lib/__tests__/deductionSheet.test.ts` — 기존 25 무회귀 + 부위 그룹·칩 7축
3. `node --test app/src/lib/__tests__/visualCards.test.mjs` — 1단위 산출 무회귀
4. `node --test .planning/quick/260730-szk-.../sweep_markers_focus.test.ts` — **등재 10동작 일반화** 7축
5. `cd app && npm run typecheck`
6. grep 게이트: 동작명 0 / `PULSE_PERIOD_MS = 1400` 단일 / 참고 문형 사본 0 / "상시 렌더" 문구 0 /
   `useNativeDriver: false` 0 / `reanimated` 0 / `PartChipsRow` hex 색 0 / 초 추정(`compareFrames.*Idx /`) 0
7. S18·S20 배선 4문자열 존재 assert
8. **시뮬 실렌더 + 승인 목업 대조 = 오케스트레이터**(실행자 도구 없음). 실행자는 요청표까지.
</verification>

<success_criteria>
- 음성 큐 강조가 kp 게이트 통과 시 사지 모양 선(가시 구간만) / 미달 시 부위 원으로 갈리고, 한 컷 안에서
  측별 혼재가 가능하다 (승인본 7R 컷 2 재현)
- 강조 도형이 1.4초 주기로 깜빡이고 dim 배경은 정적이다
- 감점 마커가 부위 단위 그룹 경계 1개로 묶이고 멤버 관절의 개별 빨강 원 나열이 0이다
- 감점 = 실선 / 참고 = 점선 이고 참고 문형이 전 표면 한 소스다
- 부위 칩이 영상 카드 아래에 보이고, 감점 칩 탭 → 그 부위 시트(1단위 블록 구조 그대로)가 열린다
- 결과 화면 진입 직후 영상 위 마커 0개, 보이지 않는 탭 타깃 0개
- 등재 10동작 스위프에서 `표시 수 == 항목 수 == 시트 수`, 좌우 교차 체인 0, 동작명 분기 0
- 채점 무접촉(점수값·산식·임계 diff 0) · 배포 없음 · 신규 패키지 0
- 33-G 표는 **미갱신**, 시뮬 확인 요청표 + 재채점 제안만 SUMMARY 에
</success_criteria>

<output>
Create `.planning/quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/260730-szk-SUMMARY.md` when done.

SUMMARY 필수 절:
- 변경 요지(파일별) + 자체 도출 결정 `N-16` 이후 추가분
- 검증 결과 표(테스트 수·게이트 결과·스위프 10동작 수치)
- `## 시뮬 확인 요청 (오케스트레이터)` — 표 + pulse 다중 프레임/녹화 절차
- `## 33-G 재채점 제안` — 표는 미갱신, 행별 제안 판정과 근거
- 이관 항목(advisory 상세 시트 = N-6, reduce-motion = N-9, 그 외 발견)
</output>
