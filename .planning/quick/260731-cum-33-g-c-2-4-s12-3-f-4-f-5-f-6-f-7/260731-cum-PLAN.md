---
phase: quick-260731-cum
plan: 01
type: execute
wave: 1
depends_on: [quick-260730-l7t, quick-260730-py1, quick-260730-szk]
files_modified:
  - app/src/lib/deductionLabels.ts
  - app/src/lib/terminologyMap.ts
  - app/src/app/analysis/loading.tsx
  - app/src/components/InjuryRiskSection.tsx
  - app/src/components/DimensionDetailModal.tsx
  - app/src/data/correctiveExercises.ts
  - app/src/data/corrective_exercises.json
  - app/src/lib/__tests__/screenVocabulary.test.ts
  - app/src/lib/__tests__/deductionSheet.test.ts
  - backend/data/terminology_map.json
  - backend/data/corrective_exercises.json
  - backend/tests/phase33/test_phrasebook_motion_specific.py
  - backend/shared/python/sunity_shared/analysis/phrasebook.py
  - app/src/lib/summarySource.ts
  - app/src/lib/__tests__/summarySource.test.ts
  - app/src/components/SummaryCard.tsx
  - app/src/lib/resultSections.ts
  - app/src/lib/__tests__/resultSections.test.ts
  - app/src/app/analysis/result.tsx
  - app/src/components/GoalGaugeBar.tsx
  - app/src/lib/audioCue.ts
autonomous: true
requirements: [S12, F-4, F-5, F-6, F-7]
user_setup: []

must_haves:
  truths:
    - "결과·로딩·시트·보완운동·부상위험 어느 화면에도 '국면·신전·재신전·완성도' 가 글자로 나오지 않는다"
    - "감점 0(100점) 문서의 요약 카드 헤드라인이 따옴표 조립문이 아니라 짧은 한 문장이고, 카드 안에서 잘리거나 넘치지 않는다"
    - "목표 게이지에서 검은 점이 '지금', 붉은 세로선이 '목표' 라는 것이 글자로 드러난다"
    - "'자세히 보기' 를 누르면 방금 누른 줄이 화면에 남은 채로 그 아래에 상세가 펼쳐진다 (화면이 통째로 아래로 튀지 않는다)"
    - "'접기' 를 누르면 최상단으로 튀지 않고 같은 자리에서 접힌다"
    - "실기기 음성 무음(F-6)은 원인 후보와 belle 실기기 판별 절차가 문서로 남고, 해결됐다고 주장하지 않는다"
  artifacts:
    - path: "app/src/lib/__tests__/screenVocabulary.test.ts"
      provides: "S12 화면 어휘 게이트 — 앱 렌더 표면 전수 스캔, 금지어 목록은 backend/data/phrasebook.json _meta.screenVocabularyGate.words 단일 출처"
      contains: "screenVocabularyGate"
    - path: "app/src/lib/resultSections.ts"
      provides: "F-7 자세히보기 앵커 선택 순수 함수 (스크롤 목표 y 결정)"
      exports: ["pickExpandAnchorY"]
    - path: "app/src/components/GoalGaugeBar.tsx"
      provides: "F-5 마커 의미 라벨(지금/목표) — 마커와 같은 스타일 소스의 스와치 동반"
      contains: "지금"
  key_links:
    - from: "app/src/lib/__tests__/screenVocabulary.test.ts"
      to: "backend/data/phrasebook.json"
      via: "_meta.screenVocabularyGate.words 직접 읽기 (목록 복제 금지)"
      pattern: "screenVocabularyGate"
    - from: "app/src/lib/summarySource.ts"
      to: "backend/shared/python/sunity_shared/analysis/phrasebook.py"
      via: "clean_dimension 헤드라인 = 용어 조립 금지 · 길이 상한 초과 시 승인 상수로 강등"
      pattern: "PRAISE_HEADLINE"
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/lib/resultSections.ts"
      via: "toggleDetailExpanded 가 pickExpandAnchorY 로 스크롤 목표 결정"
      pattern: "pickExpandAnchorY"
---

<objective>
33-G §C-2 앱 수리 **4단위(마지막)**. 남은 반려 5건을 닫는다.

- **S12 (PARTIAL)** — 화면 어휘 게이트(7R#1 "국면·신전·재신전·완성도 화면 금지")의 앱측 잔재.
  33-G 는 3곳으로 적었으나 실측 결과 **렌더되는 표면이 더 있다**(용어줄 `terminologyMap.line`,
  보완운동 제목·목적, 부상위험 제목). 3곳만 고치면 게이트가 다시 새므로 **렌더 표면 전수 + 게이트
  테스트**로 닫는다.
- **F-4 (FAIL)** — 100점 헤드라인 폰트 상자 이탈 + 카피 어색. 근본원인은 앱이 아니라 **백엔드**
  `phrasebook.assemble_praise` 가 `"감점 없이 통과한 항목이 있어요 — '{용어 전문}'"` 로 조립하는 것.
  조립 제거(뿌리) + 앱측 길이 통제(이미 저장된 doc 도 화면에서 고쳐 보이게).
- **F-5 (FAIL)** — 목표 게이지의 붉은 세로선 vs 검은 점 의미 불명. 마커와 같은 스타일의 스와치 +
  단어 라벨로 명시.
- **F-6 (FAIL, 원인 미상)** — 실기기 음성 무음. §9 유력 가설(`playsInSilentMode`)은 이미 반증.
  **재조사만** 한다. 원인을 특정 못 하면 고쳤다고 하지 않는다.
- **F-7 (FAIL)** — "자세히 보기" 가 "확 내려감". 앵커를 바꿔 전환을 연속적으로 만든다.

Purpose: belle 확인 ② 반려 12건 중 §C-2 앱 잔여분 종결 → §C-4(Pod) 진입.
Output: 어휘 게이트 테스트 1개 + 카피/표현 수리 4건 + F-6 조사 기록 + 시뮬 확인 요청표.

**채점 무접촉(D-44)**: 점수값·산식·임계·`deductionBreakdown` 소비 규칙 diff 0. 전부 표현 계층.
**배포 없음(D-45)**: OTA·EAS 금지.
**재논의 없음(D-39)**: 스펙 = 승인 목업 7R + EVIDENCE §9. belle 에게 질문 금지 — 잔여 판단은
아래 `Q-` 항목으로 자체 도출했고, 집행 중 새 판단이 필요하면 `Q-` 를 이어 붙여 SUMMARY 에 적는다.
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
@app/src/lib/deductionLabels.ts
@app/src/lib/summarySource.ts
@app/src/components/SummaryCard.tsx
@app/src/components/GoalGaugeBar.tsx
@app/src/lib/audioCue.ts
</context>

<approved_spec_extract>
이 단위가 대조할 스펙만 발췌. **이 표가 정답이고 구현이 다르면 구현이 틀린 것**(D-40).

| 축 | 근거 원문 | 규칙 |
|---|---|---|
| S12 어휘 게이트 | 목업 7R#1 `:87-92` "'마무리 스플릿 국면' 같은 채점 내부 용어(국면·신전·재신전·완성도)를 **화면 문장에서 제거**하고 강사 화법으로. … 일반 규칙 2건 박제 = 카피 AI 의 국면 사지 방향 소비 + **화면 어휘 게이트**(동작명 하드코딩 금지)" | 금지어 4개. 목록 데이터 = `backend/data/phrasebook.json` `_meta.screenVocabularyGate.words` (**단일 출처 — 복제 금지**) |
| S12 보존 축 | 목업 7R#1 `:88-91` "record 원문·수치는 ⑤ 대조 표에 **보존**(사실값 불변)" | 내부 기록(주석·provenance·계약 타입 주석)은 그대로. 바뀌는 건 **화면에 나오는 문자열만** |
| F-4 | EVIDENCE §9-2 F-4 "terminologyMap 문구를 **따옴표로 헤드라인에 조립** — 길이 통제 불가. **카피 재작성**" | 조립 제거 + 길이 통제 |
| F-4 수치 금지 | D-09 / `summarySource.ts:18` "헤드라인 문자열에 측정 수치를 넣지 않는다" | 재작성 카피에 숫자·단위·% 0 |
| F-5 | EVIDENCE §9-2 F-5 "붉은 세로선 vs 검은 점 의미 불명. **기호만으로 현재/허용선 구분 불가. 라벨 명시**" | 라벨 = belle 직접 지시. D-05 ③("최후에 한 줄")보다 우선 |
| F-5 수치 규칙 | `GoalGaugeBar.tsx:5-16` (D-10) "게이지도 각도 숫자 확대 금지 … 화면 문자열은 단위 원문 배지 뿐(% 환산 금지)" | 라벨은 **단어**. 새 수치 노출 0 |
| F-6 | EVIDENCE §9-2 F-6 "시뮬에선 재생. 유력 = playsInSilentMode 미지정. **조사**" / 33-G "**유력 가설 반증** — 이미 설정됨. 원인 재조사 필요" | 조사 지시. **수리 지시 아님** |
| F-7 | EVIDENCE §9-2 F-7 "의도된 앵커 스크롤(D-17)이나 **펼침 인지 안 됨** — 전환 표현 조정 후보" / 33-G F-7 "전환 표현 조정(D-05 순서, **Claude 재량**)" | 목표 = "펼쳐졌다"가 인지되는 것. 수단은 재량 |
| D-05 순서 | 33-CONTEXT D-05 "① 없앤다 → ② 자명하게 → ③ 최후에 한 줄. 한 화면에 새로 추가되는 문장은 최대 1줄" | 문장 수 증가 금지. **단어 라벨은 문장이 아니다** |
</approved_spec_extract>

<self_derived_decisions>
1~3단위가 `M-`/`N-`/`P-` 를 썼으므로 이번 접두는 **`Q-`**.

| # | 지점 | 결정 | 근거 |
|---|---|---|---|
| **Q-1** | 33-G 가 적은 S12 잔재 3곳 vs 실측 더 많음 | **렌더 표면 전수**를 고친다. 3곳 리스트는 부분 목록으로 취급 | 33-G 서두 "belle 의 §9 발견 12건은 부분 목록" 과 같은 성격. 3곳만 고치면 시트 용어줄·보완운동 제목에 그대로 남아 belle 이 또 본다 = 반려 3회 |
| **Q-2** | "화면 표면" 판정 기준 | **`<Text>` 로 도달 가능한 문자열**. 주석·타입 주석·소비자 없는 데이터 필드는 대상 밖 — 단, 제외는 **소비자 0 grep 증거**를 SUMMARY 에 남긴다 | 목업 7R#1 "record 원문 보존" = 내부 기록 유지. 증거 없는 제외는 게이트 무력화 |
| **Q-3** | `DimensionDetailModal.tsx` (완성도 4곳) | **파일 삭제.** import 0건 확인 후 | `result.tsx:1395`·`:3255` 가 "구 DimensionDetailModal **제거** — D-03/D-12" 라고 이미 선언했는데 파일만 남았다. 삭제가 승인된 상태의 완성이고 D-05 ①(없앤다) |
| **Q-4** | `InjuryRiskSection.tsx:59` "과**신전**" | **바꾼다.** 금지어 substring 이고 수강생 어휘도 아니다 | 게이트가 `w in text` substring 매칭. 예외를 두면 게이트가 데이터가 아니라 판단에 의존하게 된다 |
| **Q-5** | `illustrationScene.ILLUSTRATION_SCENES[].provenance` 의 "신전" | **유지 + 게이트 제외.** `sceneCoversParts`/`illustrationMotionForPart`/`hasIllustrationFor` 어느 것도 반환하지 않음(소비자 0) | Q-2. 33-14 검수 증거 원문이라 바꾸면 증거가 훼손된다 |
| **Q-6** | 어휘 목록을 앱에 복제할 것인가 | **복제 금지.** 게이트 테스트가 `backend/data/phrasebook.json` 을 직접 읽는다(테스트 전용 경로, 번들 미포함) | 단일 출처. 복제하면 다음 라운드에 drift |
| **Q-7** | 백엔드 어휘 게이트가 terminology·praise 헤드라인을 안 본다 | `test_screen_vocabulary_gate` 스코프를 **`phrasebook.rendered_copy_strings()`** 로 확장 | '완성도' 가 `terminology_map.json` 에 살아남은 구조적 이유가 이 스코프 누락이다. 뿌리에서 막는다 |
| **Q-8** | F-4 를 앱에서 고칠지 백엔드에서 고칠지 | **둘 다.** 백엔드 = 조립 제거(뿌리, 새 doc), 앱 = 조립형·과길이 강등(이미 저장된 doc 4건도 화면에서 고쳐 보임 = 시뮬 검증 가능) | 백엔드만 고치면 §C-4 Pod 재산출 전까지 화면으로 확인할 수 없다. 앱만 고치면 새 doc 이 또 긴 문장을 만든다 |
| **Q-9** | 앱측 강등 조건 | ① 조립형(` — '…'` 로 끝남) ② 길이 > `PRAISE_HEADLINE_MAX_CHARS` | belle 표현 그대로 "따옴표 조립" + "길이 통제 불가" 두 축을 각각 막는다 |
| **Q-10** | `PRAISE_HEADLINE_MAX_CHARS` 값 | **24.** 승인 상수 최장(`'측정된 자세에서 기본 기준은 지켰어요'` = 20자) + 여유 4 | 자의적 픽셀 추정 금지. 승인된 문장이 전부 통과하고 조립형(약 50자)이 걸리는 최소값 |
| **Q-11** | 강등 시 무엇을 보여주나 | 이미 있는 **승인 로컬 상수** `PRAISE_HEADLINE[source]` | 새 카피 발명 0. 스팟체크 불일치 강등(32-13)이 쓰는 것과 **같은 경로**라 검증된 표면 |
| **Q-12** | 백엔드 clean_dimension 헤드라인에서 용어를 빼면 "어느 차원이 깨끗했나" 정보 손실 | **수용.** 그 용어줄은 부위 시트가 이미 렌더한다(`DeductionDetailSheet:133` `terminologyPlain`) | D-05 ①. 같은 정보를 두 곳에서 말하지 않는다 |
| **Q-13** | `clean_dimensions` 루프 유지 여부 | **유지.** 용어 매핑이 있는 차원이 실제로 있을 때만 칭찬 방출 | D-06 "근거 없는 칭찬 금지" 게이트가 이 루프다. 문장만 바꾸고 근거 판정은 안 건드린다 |
| **Q-14** | F-5 라벨 배치 = 마커 위 절대배치 vs 범례 | **범례.** 마커와 동일 스타일 스와치 + 단어를 legendRow 에 둔다 | 절대배치는 두 마커가 가까울 때 겹치고, 겹침 회피 규칙 = 새 기하 = 수리에 새 범위. 범례는 충돌 자체가 없다 |
| **Q-15** | 기존 `goalHint` 문장('목표까지 줄이기') | **제거하고 그 자리를 범례로 대체** | D-05 문장 수 증가 금지: 문장 −1, 단어 라벨 +2 = 순감. 방향 정보는 기하(점이 선의 좌/우) + a11y 라벨에 유지 |
| **Q-16** | 스와치가 마커와 달라질 위험 | 색·모양을 **마커 style 과 같은 토큰/상수에서 파생** | 스와치가 마커와 다르면 라벨이 오히려 거짓이 된다 |
| **Q-17** | F-7 앵커를 어디로 | **요약 카드 자신의 상단**(`anchor:summaryCard`). 펼침·접기 **양쪽 다** | 누른 줄이 화면에 남고 그 아래에 새 내용이 나타나면 "펼쳐졌다"가 자명(D-05 ②). 게다가 요약 카드 y 는 펼침으로 **변하지 않아** 기존 stale-y 경합(펼치기 전 측정한 y 로 스크롤)도 같이 사라진다 |
| **Q-18** | 33-15 의 "재탭 = 최상단 복귀" 변경 | **변경한다**(접기도 요약 카드 앵커). D-17 원 반려는 "재탭 안 접힘" 이었고 그건 토글+라벨로 이미 해결 | 최상단 복귀는 승인 스펙이 아니라 구현 선택이고, F-7 이 지적한 "확 튐" 과 같은 성질이다 |
| **Q-19** | F-7 폴백 | 요약 앵커 미기록 → 기존 `DETAIL_ANCHOR_KEYS` → `scrollToEnd` (기존 체인을 뒤에 그대로 붙임) | 이미 동작하는 경로를 지우지 않는다 |
| **Q-20** | F-6 에 코드 변경을 넣을 것인가 | **원인 특정 = 불가**(실기기 없음). 따라서 **PASS 주장 금지·33-G FAIL 유지.** 다만 소스 증거표가 **세션 쓰기 순서 경합**을 실증하면 후보 완화 1건까지 허용하되 라벨은 끝까지 `후보(미확정)` | "안 되는 걸 고쳤다고 하는 게 가장 나쁘다". 동시에 확인 ③ 이 1회뿐(D-45)이라 근거 있는 후보까지 버리면 다음 반려를 예약하는 셈. 두 요구를 **라벨 정직성**으로 동시에 만족시킨다 |
| **Q-21** | F-6 후보 완화의 안전 조건 | ① 기존 성공 경로의 **상위집합**(시뮬에서 관측 변화 0) ② 되돌리는 방법 1줄 명시 ③ `speakCue` 반환 semantics 불변 | 검증 불가한 변경은 최소한 회귀 불가여야 한다 |
</self_derived_decisions>

<tasks>

<task type="auto">
  <name>Task 1: S12 화면 어휘 게이트 — 렌더 표면 전수 + 게이트 테스트</name>
  <files>app/src/lib/deductionLabels.ts, app/src/lib/terminologyMap.ts, backend/data/terminology_map.json, app/src/app/analysis/loading.tsx, app/src/components/InjuryRiskSection.tsx, app/src/components/DimensionDetailModal.tsx, app/src/data/correctiveExercises.ts, app/src/data/corrective_exercises.json, backend/data/corrective_exercises.json, app/src/lib/__tests__/screenVocabulary.test.ts, app/src/lib/__tests__/deductionSheet.test.ts, backend/tests/phase33/test_phrasebook_motion_specific.py</files>
  <action>
S12 를 "3곳 패치" 가 아니라 **게이트로** 닫는다(Q-1).

(1) **게이트 테스트 신설** — `app/src/lib/__tests__/screenVocabulary.test.ts`
(node --test, Node 24 type stripping, 신규 의존성 0. `summarySource.test.ts` 헤더 관례 따를 것).
- 금지어 = `backend/data/phrasebook.json` 의 `_meta.screenVocabularyGate.words` 를 **읽어서** 사용
  (현재 값 = 국면·신전·재신전·완성도). 목록을 앱에 적어두지 말 것(Q-6).
- 스캔 범위 = `app/src/**/*.ts`, `app/src/**/*.tsx`, `app/src/data/*.json`.
  `.ts/.tsx` 는 **주석 제거 후** 검사(`//` 줄 주석 + 블록 주석). `__tests__/**` 제외.
  json 은 문자열 **값**만 검사(키 제외).
- 제외 레지스트리 = 파일→필드 맵 1개. 현 시점 유일 항목 `src/lib/illustrationScene.ts` 의
  `provenance`(Q-5). 각 항목에 **소비자 0 사유**를 주석으로 적을 것. 제외를 늘리려면 grep 증거가
  있어야 하고 SUMMARY 에 근거를 쓴다.
- 위반 시 `파일:줄:단어` 를 전부 나열하고 실패.

(2) **렌더 표면 교체** — 아래 표대로. 문장을 늘리지 말고 같거나 짧게(D-05).

| 파일 | 현재 | 교체 |
|---|---|---|
| `deductionLabels.ts:479` | `leg_extension: '다리 신전(펴짐)'` | `'다리 펴기'` |
| `deductionLabels.ts:480` | `arm_extension: '팔 신전(펴짐)'` | `'팔 펴기'` |
| `terminologyMap.ts:14` + `backend/data/terminology_map.json` 동일 키 | `line: '팔다리를 끝까지 펴서 만드는 라인의 완성도'` | `'팔다리를 끝까지 펴서 만드는 라인'` |
| `loading.tsx:68` | `…회전 속도보다 라인의 완성도가 더 중요해요.` | `…회전 속도보다 라인이 곧은지가 더 중요해요.` |
| `loading.tsx:72` | `작은 각도 차이가 완성도의 차이를 만듭니다…` | `작은 각도 차이가 자세의 차이를 만듭니다…` |
| `InjuryRiskSection.tsx:59` | `'무릎·팔꿈치 과신전 가능성'` | `'무릎·팔꿈치 과하게 젖혀짐'` (Q-4) |
| `correctiveExercises.ts:57` | `legs_not_extended: '다리 신전 강화'` | `'다리 펴기 강화'` |
| `corrective_exercises.json` purpose 5건 | `다리 신전 근력 기반` / `단측 다리 신전 강화` / `발목/종아리 신전 마무리` / `능동 다리 신전 가동` / `측면 다리 신전 근력` | `다리 펴는 근력 기반` / `한쪽 다리 펴기 강화` / `발목·종아리 펴기 마무리` / `능동 다리 펴기 가동` / `측면 다리 펴는 근력` |

`corrective_exercises.json` 은 `app/src/data/` 와 `backend/data/` 가 **byte-for-byte 미러**다
(`backend/tests/phase13/test_corrective_exercises_app_lockstep.py`). 두 파일을 동일하게 고칠 것.
`sourceRef` 인용값은 건드리지 말 것. `terminology_map.json` 도 `backend/tests/phase32/
test_terminology_lockstep.py` 로 앱 미러와 묶여 있다 — 같이 고칠 것.

(3) **사문 삭제** — `app/src/components/DimensionDetailModal.tsx` 삭제(Q-3). 먼저
`grep -rn "DimensionDetailModal" app/src` 로 **import 0건**(현재는 주석 참조만)을 확인하고,
삭제 후 typecheck clean 을 증거로 남긴다. 다른 파일의 역사적 주석 참조는 그대로 둔다.

(4) **백엔드 게이트 스코프 확장(뿌리 차단, Q-7)** — `backend/tests/phase33/
test_phrasebook_motion_specific.py::test_screen_vocabulary_gate` 는 지금 phrasebook fixture 의
`entries/safetyEntries/failClosed` 만 본다. `phrasebook.rendered_copy_strings()`(terminology terms +
summaryPraise 헤드라인 상수 포함)도 스캔에 더해 '완성도' 가 terminology 에 살아남은 구조적 구멍을
막는다. 경로 정보가 있는 기존 fixture walk 는 **유지**하고 옆에 덧붙일 것.

(5) **기존 테스트 정합** — `deductionSheet.test.ts:231` 이 `'고칠 것 2 — 다리 신전(펴짐) (−20점)'`
를 기대한다. 새 라벨로 갱신(기대 문자열만 — 로직 기대는 그대로).

**일반화(single-motion-fixation 금지)**: 이번 변경은 전부 criterion/defect 키 맵과 공용 카피라
동작 분기가 없다. 게이트가 `app/src/**` 전수를 스캔해 0 hit 인 것이 곧 10동작 일반화 증거다 —
`grep -rn "power-spin\|kip-up" app/src --include='*.ts' --include='*.tsx'` 로 동작별 카피 파일이
따로 없음을 확인해 SUMMARY 에 수치로 적을 것.

**금지**: 점수·산식·임계 변경 0. 새 문장 추가 0. 주석·타입 주석·`provenance` 의 내부 용어는
그대로 둘 것(목업 7R#1 "record 원문 보존").
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && node --test app/src/lib/__tests__/screenVocabulary.test.ts && node --test app/src/lib/__tests__/deductionSheet.test.ts && python3 -m pytest backend/tests/phase33/test_phrasebook_motion_specific.py backend/tests/phase32/test_terminology_lockstep.py backend/tests/phase13/test_corrective_exercises_app_lockstep.py -q && cd app && npm run typecheck</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && ! grep -rn "국면\|신전\|완성도" src/ --include='*.ts' --include='*.tsx' --include='*.json' | grep -v "__tests__" | grep -v "illustrationScene.ts" | grep -v "^src/types/" | grep -v "//" | grep -vE ":[0-9]+:[[:space:]]*(\*|/\*)"</automated>
  </verify>
  <done>
`screenVocabulary.test.ts` 존재·통과(금지어 목록을 `backend/data/phrasebook.json` 에서 읽음 — 앱에
목록 리터럴 0). 교체 표 8행 전건 반영. `corrective_exercises.json` 2벌 + `terminology_map.json`
2벌이 각각 lockstep 테스트 통과. `DimensionDetailModal.tsx` 파일 부재 + typecheck clean. 백엔드
`test_screen_vocabulary_gate` 가 `rendered_copy_strings()` 도 스캔. `deductionSheet.test.ts` 기존
케이스 무회귀. 두 번째 `<automated>` grep 이 제외 레지스트리·주석 밖에서 **0줄**.
SUMMARY 에 (a) 렌더 표면 전수 목록 + 제외 항목별 소비자 0 grep 증거, (b) 동작명 grep 수치.
  </done>
</task>

<task type="auto">
  <name>Task 2: F-4 헤드라인 조립 제거·길이 통제 + F-7 자세히보기 전환</name>
  <files>backend/shared/python/sunity_shared/analysis/phrasebook.py, app/src/lib/summarySource.ts, app/src/lib/__tests__/summarySource.test.ts, app/src/components/SummaryCard.tsx, app/src/lib/resultSections.ts, app/src/lib/__tests__/resultSections.test.ts, app/src/app/analysis/result.tsx</files>
  <action>
**F-4 — 근본원인은 앱이 아니라 백엔드다.** 33-G 는 `result.tsx:475-505 계열` 로 적었지만 실측
근본원인은 `phrasebook.assemble_praise`(`phrasebook.py:179`, `:223`)가
`_PRAISE_HEADLINE_CLEAN_DIMENSION_PREFIX + f"'{term}'"` 로 **terminology 전문을 따옴표로 붙이는**
것이다. 결과물 `"감점 없이 통과한 항목이 있어요 — '동작의 전체 흐름이 기준 자세와 얼마나 나란히
이어지는지'"`(약 50자)가 `SummaryCard.praiseHeadline`(`typography.bodyLg` 24/700)에 들어가 belle 이
본 상자 이탈이 된다. 이 사실을 SUMMARY 에 **정정 기록**으로 남길 것(33-G 행의 지목 위치가 틀렸음).

(a) **백엔드 조립 제거** — 상수를 접미 조립용 prefix 가 아니라 **완성 문장 1개**로 바꾼다
(이름에서 `_PREFIX` 를 떼서 조립 의도를 지운다). `clean_dimensions` 루프와 terminology 조회는
**그대로 유지**(Q-13 — 근거 없는 칭찬 금지 게이트). `rendered_copy_strings()` 의 상수 나열도 같이
갱신. 새 문장에 수치·단위·% 0(D-09). 잃는 정보(어느 차원이 깨끗했나)는 부위 시트 용어줄이 이미
렌더한다(Q-12).

(b) **앱측 길이 통제** — `summarySource.selectPraise` 의 doc 우선 분기에서, doc headline 이
**조립형**(` — '` 로 시작하는 꼬리 + `'` 로 끝남) **이거나** 길이 > `PRAISE_HEADLINE_MAX_CHARS`
(= 24, Q-10)이면 **그 source 의 승인 로컬 상수** `PRAISE_HEADLINE[source]` 로 강등한다(Q-11).
`source`·`evidenceValue`·`evidenceUnit` 은 그대로 통과. 강등 사유는 코드 주석으로만 — 화면에
새 문장 0. 이 경로가 있어야 이미 저장된 doc 4건도 시뮬에서 고쳐 보인다(Q-8).

(c) **상자 이탈 방어** — `SummaryCard.praiseHeadline` 에 `numberOfLines={2}`. (b)의 상한과 함께
두 겹 방어이고 정상 카피에서는 절대 잘리지 않아야 한다 — 승인 상수 4개의 실제 글자 수를 SUMMARY 에
적어 상한 대비 여유를 보일 것.

(d) **테스트** — `summarySource.test.ts` 에 3케이스 추가: ① 조립형 doc headline → 로컬 상수로
강등되고 source 보존 ② 25자 doc headline → 강등 ③ 승인 상수 4개 전부 상한 이하(회귀 가드).
기존 Test 1~5 는 그대로 통과해야 한다(Test 1 의 17자 헤드라인은 상한 이하라 무영향).

---

**F-7 — 앵커를 요약 카드 자신으로 옮긴다(Q-17).** 현재 `toggleDetailExpanded`(`result.tsx:2130`)는
펼치는 즉시 **펼치기 전에 측정된** `anchor:scoreGauge`/`anchor:scoreBreakdown` y 로 점프한다.
요약 카드에서 한참 아래라 belle 이 "확 내려감" 으로 읽었고, 그 측정 y 자체도 stale 이다.

(e) **순수 함수 추출** — `app/src/lib/resultSections.ts` 에
`pickExpandAnchorY(cardY, keys, pad)` 를 추가한다. 첫 번째로 기록된 키의 `max(0, y - pad)` 를
반환하고, 하나도 없으면 `null`(호출측이 폴백, Q-19). `resultSections.test.ts` 에 4케이스:
첫 키 우선 / 두 번째 폴백 / 전무 → null / 음수 클램프.

(f) **배선** — `SummaryCard` 를 감싸는 위치에 `onLayout` 으로 `anchor:summaryCard` y 를 기록하고
(`setCardY` 재사용 — record 키와 충돌 없는 전용 슬롯), 펼침·접기 **양쪽 다**
`pickExpandAnchorY(cardY, ['anchor:summaryCard', ...DETAIL_ANCHOR_KEYS], 12)` 결과로 스크롤한다
(Q-18). `null` 이면 펼침은 `scrollToEnd`, 접기는 `y: 0` 폴백. 요약 카드 y 는 펼침으로 변하지
않으므로 layout 대기가 필요 없다 — 이 점을 코드 주석에 근거로 남길 것.

**무회귀 확인**: `jumpToRecordKey`·`jumpToQuestion`·`jumpToCollapsedList`·`DETAIL_ANCHOR_KEYS`
기록 지점 무변경. `SummaryCard` 의 `expanded` prop·`접기` 라벨·chevron 방향(33-15 D-17, 이미
PASS)은 건드리지 않는다.

**금지**: 점수·산식·임계 0. 새 사용자 문장 0. `praise` 근거 판정(`clean_dimensions`·스팟체크
강등) 로직 변경 0.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && node --test app/src/lib/__tests__/summarySource.test.ts && node --test app/src/lib/__tests__/resultSections.test.ts && python3 -m pytest backend/tests/phase32 backend/tests/phase33 -q && cd app && npm run typecheck</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && ! grep -q "_PRAISE_HEADLINE_CLEAN_DIMENSION_PREFIX}'" backend/shared/python/sunity_shared/analysis/phrasebook.py && grep -q "numberOfLines={2}" app/src/components/SummaryCard.tsx && grep -q "pickExpandAnchorY" app/src/app/analysis/result.tsx && grep -q "anchor:summaryCard" app/src/app/analysis/result.tsx && echo GATES_OK</automated>
  </verify>
  <done>
백엔드 `assemble_praise` 에 용어 보간 조립 0. 앱 `selectPraise` 가 조립형·과길이 headline 을 승인
상수로 강등하고 source/evidence 는 보존. `SummaryCard.praiseHeadline` 에 `numberOfLines={2}`.
`pickExpandAnchorY` 가 `resultSections.ts` 에 존재하고 4케이스 통과. `result.tsx` 가 펼침·접기
양쪽에서 `anchor:summaryCard` 우선 앵커를 쓴다. phase32/phase33 백엔드 회귀 0, 앱 테스트 무회귀,
typecheck clean. SUMMARY 에 (a) 33-G F-4 지목 위치 정정 기록, (b) 승인 상수 4개 글자 수 대 상한 24 표.
  </done>
</task>

<task type="auto">
  <name>Task 3: F-5 게이지 기호 라벨 + F-6 실기기 무음 재조사(원인 미상 시 수리 금지)</name>
  <files>app/src/components/GoalGaugeBar.tsx, app/src/lib/audioCue.ts</files>
  <action>
**F-5 — 기호에 이름을 붙인다(범례 방식, Q-14).**
`GoalGaugeBar.tsx` 의 `legendRow` 에서 `goalHint` 문장을 빼고(Q-15) 그 자리에 범례 2칸을 둔다:
`[검은 점 스와치] 지금` · `[브랜드 세로선 스와치] 목표`. 스와치의 색·모양·테두리는
`styles.currentMarker`/`styles.targetMarker` 와 **같은 토큰에서 파생**해야 한다(Q-16 — 스와치와
마커가 어긋나면 라벨이 오히려 거짓이 된다). 크기만 축소한다. 수치 배지(`badgePill`)는 그대로 —
게이지의 유일한 수치 노출점 규칙(D-09/D-10) 불변.

- 허용 오차 밴드(`tolBand`)에는 라벨을 붙이지 않는다. belle 이 지목한 건 "붉은 세로선 vs 검은 점"
  두 기호이고, 밴드까지 이름 붙이면 요소가 늘어 D-07 ⑥(화면이 전보다 단순해야)에 어긋난다.
- a11y 라벨(`:90`)의 방향 문구(`목표까지 늘리기/줄이기`)는 **유지** — 화면 문장은 줄이되 스크린
  리더 정보는 잃지 않는다.
- 하드코딩 금지: hex 리터럴 0, `colors`/`radius`/`typography` 토큰만(app/CLAUDE.md).
- `computeGaugeGeometry` 및 `null` 반환(규칙 상수 부재 시 게이지 미표시) 경로는 무변경.

---

**F-6 — 조사가 산출물이다. 원인을 특정 못 하면 고치지 않는다(Q-20).**

(1) **소스 증거표 작성**(SUMMARY 절 `## F-6 재조사`). 아래를 **직접 읽고** 파일:줄로 인용할 것:
- `app/node_modules/expo-audio/ios/AudioModule.swift` `setAudioMode` — `playsInSilentMode` 가
  카테고리·옵션으로 어떻게 매핑되는지, 세션 **활성화**(`setActive`)는 누가 하는지.
- `app/node_modules/expo-video/ios/VideoManager.swift` `setAudioSession()` — 언제 불리고 어떤
  조건에서 공유 `AVAudioSession` 카테고리/옵션을 **덮어쓰는지**(muted 플레이어일 때 분기 포함).
- `app/src/components/VideoCompare.tsx:377-384` — 두 플레이어의 `muted` 값.
- `app/src/lib/audioCue.ts` `hydrate()` — `setAudioModeAsync` 가 **몇 번** 불리는지, 실패가 어떻게
  삼켜지는지, `setIsAudioActiveAsync` 호출 유무(grep).
- `VideoCompare.tsx:689-745` — 음성 큐 경로에서 발화 직전·직후 `pause()`/`play()` 가 몇 번 일어나는지.
증거표는 **사실만**(파일:줄 + 인용). 추론은 다음 항목으로 분리해서 쓴다.

(2) **후보 순위표** — 증거로 뒷받침되는 것만. 각 행에 `근거(파일:줄)` / `시뮬에서 관측 불가한
이유` / `실기기에서 이 후보를 참·거짓으로 만드는 관찰` 을 적는다. 근거 없는 추측은 쓰지 말 것.

(3) **belle 실기기 판별 절차**(SUMMARY `## F-6 실기기 판별 절차`) — 로그 없이 belle 이 혼자 할 수
있는 **분기형** 절차로. 최소 다음 포함: ① 무음 스위치를 **끈 상태**(벨 모드)로 같은 재생 →
소리 남/안 남 ② 무음 ON + 미디어 볼륨 최대 ③ 이어폰 연결 후 재생 ④ 음악 앱 재생 중 앱 진입 시
음악이 작아지는지(우리 세션 활성 여부). 각 결과가 어느 후보를 확정·기각하는지 화살표로 매핑.
**결과 화면에서 LogBox 경고 배너를 먼저 닫아야 재생 버튼이 눌린다**는 것도 절차에 적을 것
(1~3단위 실측).

(4) **수리 여부** — 위 (1)이 **세션 쓰기 순서 경합**(우리 오디오 모드 1회 쓰기가 이후 비디오
play/pause 마다의 세션 재설정에 덮인다)을 **파일:줄로 실증할 때에만** 후보 완화 1건까지 허용:
`speakCue` 가 재생 직전에 오디오 모드를 **다시 선언**하도록. 조건(Q-21) — `speakCue` 의 boolean
반환 semantics·호출부 계약 불변 / 실패는 기존처럼 조용히 삼킴 / 시뮬에서 관측 가능한 변화 0 /
**되돌리는 방법 1줄**을 SUMMARY 에 명시. 실증하지 못하면 **`audioCue.ts` 를 건드리지 말 것.**

(5) **라벨 규율(위반 = blocking)** — SUMMARY·33-G 재채점 제안 어디에도 F-6 을 PASS·해결로 쓰지
않는다. 표기는 `FAIL 유지 — 원인 미상. 후보 N건 + 실기기 판별 절차. (코드 변경 시) 후보 적용,
미확정`. 이 사이클에서 가장 나쁜 실패는 안 되는 걸 고쳤다고 하는 것이다.

**금지**: 새 패키지 0(`expo-av` 등 도입 금지). 오디오 on/off 기본값(off, 학원 소음) 변경 0.
`prefetchCueAudio`·`stopCue`·`isCueSpeaking` 계약 변경 0. 화면에 새 문장 0.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npm run typecheck && node --test src/lib/__tests__/gaugeGeometry.test.ts && node --test src/lib/__tests__/cueTrack.test.ts</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && grep -q "지금" src/components/GoalGaugeBar.tsx && grep -q "목표" src/components/GoalGaugeBar.tsx && ! grep -qE "#[0-9a-fA-F]{3,8}" src/components/GoalGaugeBar.tsx && ! grep -q "{goalHint}" src/components/GoalGaugeBar.tsx && ! grep -q "expo-av" package.json && echo GATES_OK</automated>
  </verify>
  <done>
게이지 범례에 `지금`·`목표` 단어 라벨 + 마커와 같은 토큰에서 파생한 스와치가 있고, hex 리터럴 0,
`goalHint` 문장은 제거됐으며 a11y 라벨의 방향 문구는 유지. 배지·`computeGaugeGeometry`·null 폴백
무변경. SUMMARY 에 `## F-6 재조사`(증거표·후보 순위표) + `## F-6 실기기 판별 절차`(분기형)가 있고
F-6 은 어디에도 PASS 로 적히지 않았다. `audioCue.ts` 변경이 있다면 실증 근거·되돌리는 방법 1줄·
`후보(미확정)` 라벨이 함께 있다. typecheck clean, 신규 패키지 0.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore doc → 앱 렌더 | 백엔드가 쓴 `summaryPraise`·`deductionBreakdown` 문자열을 앱이 그린다. 이 단위의 신뢰 경계는 **표시 정직성**(없는 근거를 말하지 않기, 검증 못 한 걸 고쳤다고 하지 않기)이지 인증이 아니다 |
| 앱 ↔ iOS 오디오 세션 | `expo-audio` 와 `expo-video` 가 **같은 전역 `AVAudioSession`** 을 공유한다. 이 경계 자체가 F-6 조사 대상 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-33G4-01 | Repudiation(거짓 완료 주장) | F-6 | mitigate | 실기기 검증 불가 → PASS 라벨 금지를 `<action>`·`<done>`·`success_criteria` 3중 고정. 코드 변경 시 `후보(미확정)` + 되돌리는 방법 필수 |
| T-33G4-02 | Information Disclosure(거짓 구체성) | 어휘 교체 문구 | mitigate | 교체는 **표로 고정**(실행자 즉흥 작문 금지). 내부 기록(주석·provenance)은 원문 보존이라 사실값 변형 0 |
| T-33G4-03 | Tampering(단일 출처 훼손) | terminology·corrective 미러 | mitigate | 두 파일 동시 수정 + 기존 lockstep 테스트(phase32·phase13)를 `<automated>` 에 포함 |
| T-33G4-04 | Elevation(범위 침범) | 이미 PASS 인 S1·S3·S6·S7·S18·S20·F-8 | mitigate | 이 단위는 카피 상수·게이지 범례·스크롤 앵커·오디오 세션만 만진다. 마커·시트·칩 구조 파일은 `files_modified` 밖 + 기존 앱 테스트 무회귀 게이트 |
| T-33G4-05 | Denial of Service(렌더 붕괴) | `numberOfLines={2}` 절삭 | mitigate | 상한 24 와 승인 상수 실측 글자 수(≤20) 대조를 `<done>` 에 요구 — 정상 카피는 절대 절삭되지 않음을 수치로 증명 |
| T-33G4-06 | Tampering(정보 유실) | `goalHint` 문장 제거 | accept | 방향 정보는 기하 + a11y 라벨에 잔존. D-05 문장 순감이 belle 지시(라벨 명시)와 양립하는 유일한 형태 |
| T-33G4-SC | Tampering | npm/pip/cargo installs | mitigate | **신규 패키지 0**(설치 태스크 없음 → legitimacy 체크포인트 불요). `expo-av` grep 게이트로 오디오 스택 교체 시도 차단 |
</threat_model>

<verification>
1. `node --test app/src/lib/__tests__/screenVocabulary.test.ts` — S12 어휘 게이트(앱 전수)
2. `node --test` — `deductionSheet` / `summarySource` / `resultSections` / `gaugeGeometry` / `cueTrack` 무회귀 + 신규 케이스
3. `python3 -m pytest backend/tests/phase32 backend/tests/phase33 backend/tests/phase13/test_corrective_exercises_app_lockstep.py -q` — 미러 lockstep + 백엔드 어휘 게이트 확장
4. `cd app && npm run typecheck`
5. grep 게이트: 앱 금지어 0(제외 레지스트리·주석 밖) / `assemble_praise` 용어 보간 0 /
   `numberOfLines={2}` 존재 / `pickExpandAnchorY`·`anchor:summaryCard` 배선 존재 /
   `GoalGaugeBar` hex 0 · `지금`·`목표` 존재 / `expo-av` 0
6. **시뮬 실렌더 + 승인 목업 대조 = 오케스트레이터**(실행자 도구에 시뮬 없음). 실행자는
   `## 시뮬 확인 요청 (오케스트레이터)` 표까지. **33-G 표는 미갱신 — 제안만.**
</verification>

<success_criteria>
- 앱 렌더 표면 어디에도 국면·신전·재신전·완성도 0 (게이트 테스트가 상시 강제, 목록은 백엔드 단일 출처)
- 백엔드가 더 이상 terminology 전문을 헤드라인에 조립하지 않고, 앱이 조립형·과길이 헤드라인을
  승인 상수로 강등한다 (이미 저장된 doc 4건도 화면에서 고쳐 보임)
- 목표 게이지의 두 기호에 이름이 붙고, 게이지의 **문장 수는 늘지 않았다**
- 자세히 보기·접기가 누른 줄을 화면에 남긴 채 전환된다 (최상단·하단으로 튀지 않음)
- F-6 = 원인 미상으로 정직하게 남고, 증거표·후보 순위표·belle 실기기 분기 절차가 문서화됐다.
  어디에도 PASS 로 적히지 않았다
- 채점 무접촉(점수값·산식·임계 diff 0) · 배포 없음 · 신규 패키지 0 · 새 RN 경고 0
- 33-G 표 **미갱신**, 시뮬 확인 요청표 + 재채점 제안만 SUMMARY 에
</success_criteria>

<output>
Create `.planning/quick/260731-cum-33-g-c-2-4-s12-3-f-4-f-5-f-6-f-7/260731-cum-SUMMARY.md` when done.

SUMMARY 필수 절:
- 변경 요지(파일별) + 자체 도출 결정 `Q-22` 이후 추가분
- 검증 결과 표(테스트 수·게이트 결과·어휘 전수 스캔 hit 0 증거)
- `## S12 렌더 표면 전수` — 고친 표면 목록 + 제외 항목별 **소비자 0 grep 증거**
- `## F-4 지목 위치 정정` — 33-G 가 `result.tsx:475-505` 로 적었으나 근본원인은 백엔드 조립
- `## F-6 재조사` — 소스 증거표(파일:줄 인용) + 후보 순위표
- `## F-6 실기기 판별 절차` — belle 이 혼자 할 수 있는 분기형 절차(LogBox 배너 먼저 닫기 포함)
- `## 시뮬 확인 요청 (오케스트레이터)` — 항목별 도달 경로·승인 요소·PASS 조건 표.
  최소: pdshape 100 doc 헤드라인(F-4, 잘림·넘침 0) / 파워스핀·킵업 doc 게이지 범례(F-5) /
  자세히 보기·접기 전환(F-7, 전·후 캡처 2장) / 시트 용어줄·보완운동·부상위험 문구(S12) /
  1~3단위 산출(S1·S3·S6·S7·F-8) 회귀 0 / LogBox 신규 경고 0.
  **F-6 은 시뮬 검증 대상이 아님을 명시**(실기기 확인 ③)
- `## 33-G 재채점 제안` — 표는 미갱신, 행별 제안 판정과 근거(F-6 은 FAIL 유지)
- 이관 항목(발견분)
</output>
