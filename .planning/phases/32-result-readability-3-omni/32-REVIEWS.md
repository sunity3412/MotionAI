---
phase: 32
reviewers: [codex]
reviewed_at: 2026-07-21T05:09:22Z
plans_reviewed: [32-01-PLAN.md, 32-02-PLAN.md, 32-03-PLAN.md, 32-04-PLAN.md, 32-05-PLAN.md, 32-06-PLAN.md, 32-07-PLAN.md, 32-08-PLAN.md, 32-09-PLAN.md, 32-10-PLAN.md, 32-11-PLAN.md, 32-12-PLAN.md, 32-13-PLAN.md, 32-14-PLAN.md, 32-15-PLAN.md]
---

# Cross-AI Plan Review — Phase 32

> 리뷰어 가용성: codex만 탐지됨 (gemini/opencode/qwen/cursor/coderabbit 미설치, 로컬 모델 서버 없음).
> claude CLI는 설치되어 있으나 이 리뷰가 Claude Code 세션 내부에서 실행되어 독립성 규칙에 따라 스킵.
> 프롬프트: PROJECT.md(80줄) + ROADMAP §32 + 32-CONTEXT.md(D-01~D-30) + 32-RESEARCH.md + 플랜 15개 전문 (283KB).

## Codex Review


## Summary

전체적으로 요구사항 추적, 사용자 게이트, 하위호환, graceful failure, 계약 3면 관리가 매우 잘 설계돼 있습니다. 다만 현재 상태로 실행하면 UI가 신규 백엔드 데이터보다 먼저 승인되는 배포 순서, 네이티브 오디오 모듈의 OTA 불가능성, 미션 개선도 계산에 필요한 기준값 부재, spot-check의 불안정한 record index, PR 인버전의 선행 포즈 검출 순환 의존 때문에 phase 목표를 실제 환경에서 검증하지 못할 가능성이 큽니다.

**Overall Risk: HIGH.** 구현 착수 전에 아래 차단 항목을 계획에 반영하는 것이 필요합니다.

## 실행 전 차단 항목

1. **미션 이력 계약 재설계**
   - `prev.mission`에는 이전 감점값·편차·목표가 없어 `missionOutcome`의 개선량을 계산할 수 없습니다.
   - `criterion`만으로 동일 결함을 판별하면 좌우 관절과 반복 record가 합쳐집니다.
   - `faultKey`를 `motion + ruleId + criterion + joint/side` 기반 안정 ID로 만들고 baseline 측정값을 저장해야 합니다.

2. **배포 순서 수정**
   - 32-09 신규 방출은 32-13까지 프로덕션에 배포되지 않는데, 32-12에서 UI 실기기 승인을 먼저 받습니다.
   - `pipeline/app.py`와 playback-url은 Lambda 코드이므로 Pod `git pull`만으로 배포되지 않습니다.
   - 32-09 뒤 Lambda/SAM 배포 → 실제 신규 분석 → 32-11/12 UI 검증 순서가 필요합니다.

3. **오디오 네이티브 빌드 추가**
   - 현재 [package.json](/Users/kimtaesung/Dev/SunityMotion/app/package.json)에 `expo-speech`와 `expo-audio`가 없습니다.
   - 네이티브 모듈을 추가한 후 기존 TestFlight 바이너리에 OTA만 발행할 수 없습니다. Expo도 네이티브 코드가 바뀌면 새 build/runtime이 필요하다고 명시합니다. [Expo runtime version 문서](https://docs.expo.dev/eas-update/runtime-versions/)
   - 현재 [app.json](/Users/kimtaesung/Dev/SunityMotion/app/app.json)은 `appVersion` 정책과 `version: 1.0.0`을 사용하므로 새 native build 전에 앱 버전 또는 runtimeVersion도 변경해야 기존 바이너리와 혼선이 없습니다.

4. **32-11 의존성 수정**
   - 32-11은 `cueTrack`과 VideoCompare의 `cueWindows`를 소비하지만 `depends_on`에 32-08이 없습니다.
   - 로드맵의 “각 wave는 이전 wave 전체 완료 후” 설명과 여러 `depends_on`도 일치하지 않습니다.

5. **spot-check 계약 재설계**
   - 백엔드에는 앱 `summarySource.ts`가 만드는 praise headline이 없어 “동일 헤드라인 교차검증”이 불가능합니다.
   - `hiddenRecordIndices`는 정렬·필터·추가 record에 취약합니다.
   - `recordId` 기반 검증 결과와 backend-generated summary candidate가 필요합니다.

6. **PR 인버전 아키텍처 선행 확정**
   - “추론 전 keypoint로 인버전 검출”은 keypoint가 아직 없으므로 순환 의존입니다.
   - 1차 추론→검출→워프→2차 추론인지, recognizer 선행 신호인지 명시해야 합니다.
   - 워프 후 예측 좌표를 원본 영상 좌표로 inverse-transform하는 절차도 없습니다.

7. **D-23 준수 또는 결정 변경**
   - D-23은 “웨이브마다 fixture 6동작 전수 스윕”인데 32-03은 명시적으로 1건만 검증합니다.
   - 비용상 축소하려면 CONTEXT 결정을 수정 승인받아야 하며, 계획이 임의로 범위를 줄이면 안 됩니다.

---

## Plan-by-plan Review

### [32-01 — 백엔드 수리](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-01-PLAN.md)

**Summary**

원인이 특정된 두 수리를 계약 변경 없이 수행하는 좋은 wave-1 계획입니다. 다만 저신뢰 anchor를 무조건 신뢰하는 경로와 기존 테스트 파일 변경 범위가 덜 명시돼 있습니다.

**Strengths**

- degenerate와 low-confidence를 명확히 분리합니다.
- crop framing과 marker confidence를 분리해 채점 오염을 막습니다.
- 기존 validator 통과를 직접 테스트합니다.

**Concerns**

- **MEDIUM:** `distance > T2`의 첫 anchor 자체가 이상치여도 trim offset으로 사용됩니다. 최대 offset·anchor sanity 검사가 없습니다.
- **MEDIUM:** 변경 가능하다고 명시한 `tests/test_motion_alignment*.py`가 `files_modified`에 없습니다.
- **MEDIUM:** D-23의 wave별 6동작 스윕 없이 단위테스트만 수행합니다.

**Suggestions**

- 첫 anchor 유효성, offset 범위, duration clamp 테스트를 추가합니다.
- 기존 테스트 파일을 frontmatter에 포함합니다.
- “채점 불변”은 파일 diff 외에 동일 fixture score snapshot으로 확인합니다.

**Risk Assessment: MEDIUM** — 수정 자체는 국소적이지만 잘못된 저신뢰 anchor가 비교를 더 크게 어긋나게 할 수 있습니다.

---

### [32-02 — 앱 초 맞춤·겹침 수리](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-02-PLAN.md)

**Summary**

수동 보정의 단일 합성 지점과 순수 함수 분리는 좋지만, D-16 문구와 직접 충돌하는 legacy 배지 및 상태 초기화 문제가 있습니다.

**Strengths**

- 모든 재생 경로가 한 clamp 지점을 통과하도록 설계했습니다.
- fps를 호출부에서 전달해 9/18fps 혼동을 줄입니다.
- line-height 근본 원인을 정확히 고칩니다.

**Concerns**

- **HIGH:** D-16은 `"자동 정렬 꺼짐" 배지 폐지`인데 계획은 degenerate에서 해당 문구를 유지합니다.
- **HIGH:** `initialOffsetSec`을 state 초기값으로만 쓰면 Firestore 지연 로드나 analysis 변경 때 갱신되지 않습니다.
- **MEDIUM:** 단일 fault zoom pair에서 legacy offset을 구하면 이상치 하나에 좌우됩니다.
- **MEDIUM:** PanResponder의 accessibility action 동작 테스트가 없습니다.

**Suggestions**

- disabled도 `"직접 맞춤"` 또는 `"시작점을 직접 맞춰주세요"`로 변경합니다.
- `analysisId` 변경 시 reset하고, 사용자가 조절한 뒤에는 prop 갱신이 덮어쓰지 않도록 dirty flag를 둡니다.
- 여러 matched pair의 median offset과 outlier rejection을 사용합니다.

**Risk Assessment: HIGH** — D-16 위반과 비동기 state 문제로 실기기 게이트가 잘못된 상태를 검증할 수 있습니다.

---

### [32-03 — 실물 게이트](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-03-PLAN.md)

**Summary**

운영 절차와 사람 결정을 한 checkpoint로 묶은 점은 실용적이지만, 프로덕션 Pod·OTA 변경과 의사결정이 너무 강하게 결합돼 있습니다.

**Strengths**

- health check, rollback group, 앱 완전 종료 2회 등 실전 사고 이력을 반영했습니다.
- D-17을 고장 수리 후에만 결정한다는 원칙을 지킵니다.

**Concerns**

- **HIGH:** D-23의 wave별 6동작 스윕을 1 fixture로 축소하면서 사용자 결정 변경을 받지 않습니다.
- **MEDIUM:** crop parity를 육안만으로 판정합니다.
- **MEDIUM:** Pod 재생성 승인이 필요할 수 있는데 Task 1이 `auto`입니다.
- **MEDIUM:** 한 fixture가 low-confidence alignment와 relaxed crop을 모두 재현한다는 보장이 없습니다.

**Suggestions**

- D-23을 그대로 지키거나, display-only wave는 대표 fixture만 허용하도록 CONTEXT를 개정 승인받습니다.
- crop bbox 좌표·side length를 metadata/log로 남겨 수치 parity도 확인합니다.
- Pod 생성이 필요하면 별도 blocking checkpoint로 분리합니다.

**Risk Assessment: HIGH** — 프로덕션 변경과 결정 게이트가 얽혀 실패 시 원인 분리가 어렵습니다.

---

### [32-04 — 리서치·목업 게이트](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-04-PLAN.md)

**Summary**

미결 UI 결정을 구현 전에 닫는 구조가 좋고, 최악 데이터 케이스를 포함한 점이 강점입니다. 산출물 규모와 결정 기록 범위를 조금 더 엄밀히 할 필요가 있습니다.

**Strengths**

- D-10의 확정 3요소를 모든 안의 공통 하한으로 둡니다.
- 연구의 불확실성을 숨기지 않고 belle에게 전달합니다.
- 감점 0·부분 실패·근거 부족 케이스를 선제적으로 다룹니다.

**Concerns**

- **MEDIUM:** 세로 스크롤 vs 가로 넘김 결정이 추가되지만 must-have와 후속 소비 위치가 없습니다.
- **MEDIUM:** 참고 지표 수치가 D-09 적용 대상인지 목업 검증 규칙이 모호합니다.
- **LOW:** 여러 대안×최악 케이스 조합이 과도한 목업 작업으로 번질 수 있습니다.

**Suggestions**

- 각 결정에 `decision ID → 후속 plan/task` 표를 만듭니다.
- 목업은 공통 shell과 데이터 fixture를 공유해 변형만 비교합니다.
- D-09 검사표에 심사 정보 코너도 명시적으로 포함합니다.

**Risk Assessment: MEDIUM** — 게이트 설계는 강하지만 결정 추적이 누락되면 후속 구현이 재해석될 수 있습니다.

---

### [32-05 — 문구집·용어 맵](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-05-PLAN.md)

**Summary**

LLM이 골격을 소유하지 못하게 한 방향은 매우 적절하지만, 10개 entry와 generic fallback만으로 “동작×결함별 전문가 문구” 목표를 충족했다고 보기 어렵습니다.

**Strengths**

- 문구집, 조립 함수, 금지어 테스트, 사람 감수의 다중 품질 장치가 있습니다.
- 실제 방출 key를 먼저 조사하도록 했습니다.
- LLM 실패 시 고정 골격이 남습니다.

**Concerns**

- **HIGH:** `entries ≥ 10`은 6동작×주요 결함 커버리지를 보장하지 않습니다.
- **HIGH:** generic fallback은 D-11이 금지한 일반론을 다시 유입할 수 있습니다.
- **HIGH:** 용어 맵은 앱에만 있고 백엔드 문구와는 주석으로만 정합됩니다. “단일 출처”가 아닙니다.
- **MEDIUM:** `exerciseReason`에 연결될 운동 ID가 없어 D-13의 결함→운동 관계가 불명확합니다.
- **MEDIUM:** NotebookLM 근거가 fixture에 snapshot되지 않아 재현성이 낮습니다.
- **MEDIUM:** belle에게 대표 3~5개만 보여주면 전체 corpus 승인이 아닙니다.

**Suggestions**

- 실제 fixture 방출 조합 기준 coverage matrix와 최소 커버리지 비율을 둡니다.
- 미지원 조합은 generic 조언 대신 “정확한 방법은 강사에게 확인”으로 fail closed합니다.
- terminology를 공용 JSON fixture로 만들고 TS/Python 양쪽에서 소비하거나 lockstep 테스트를 둡니다.
- `exerciseId`, `phrasebookVersion`, 근거 source를 저장합니다.
- 감수용 HTML/CSV 전체 목록을 제공합니다.

**Risk Assessment: HIGH** — 문구 품질은 phase 핵심인데 현재 acceptance는 형식만 보장하고 전문성 커버리지를 보장하지 않습니다.

---

### [32-06 — 미션 엔진·계약](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-06-PLAN.md)

**Summary**

계약 3면과 순수 함수 분리는 좋지만 미션 데이터 모델이 D-26/D-27을 계산하기에 부족하며 D-14와 충돌합니다.

**Strengths**

- 선택 규칙과 escalation을 단위테스트 가능한 함수로 분리합니다.
- legacy normalize와 scoped validator를 함께 설계했습니다.
- 신규 persistence를 기존 result 경로 안에 제한합니다.

**Concerns**

- **HIGH:** 이전 mission에 baseline points/deviation/measured 값이 없어 “개선량”을 계산할 수 없습니다.
- **HIGH:** 동일 `criterion`만으로 streak를 계산하면 좌우·동작·rule이 다른 결함이 합쳐집니다.
- **HIGH:** D-14는 safety를 미션화하지 말라고 하지만 `selectedBy='safety'`인 mission을 생성합니다.
- **HIGH:** 실제 `get_previous_analysis()`는 같은 mode만 필터링하고 같은 motion/reference는 확인하지 않습니다.
- **MEDIUM:** 문자열 길이, 질문 개수, streak 상한 검증이 없습니다.
- **MEDIUM:** `deltaSummary`를 string으로 저장하면 계산 결과와 사용자 문구 책임이 섞입니다.

**Suggestions**

- `safetyTriage`와 `mission`을 별도 결과로 분리합니다.
- `faultId`, `baselinePoints`, `baselineDeviation`, `targetValue`, `unit`, `motionId`를 mission에 저장합니다.
- 이전 분석 조회를 동일 mode+motion/reference로 제한합니다.
- outcome에는 수치 데이터만 저장하고 사람 문장은 phrasebook 조립 단계에서 만듭니다.

**Risk Assessment: HIGH** — 현재 스키마로는 phase 핵심 루프가 정확히 동작할 수 없습니다.

---

### [32-07 — SummaryCard·타이포·코치마크](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-07-PLAN.md)

**Summary**

UI를 interface-first로 분리한 점은 좋지만, 칭찬 근거와 D-09 수치 위치가 더 엄격하게 정의돼야 합니다.

**Strengths**

- 전역 타이포 변경 대신 결과 화면 전용 토큰을 추가합니다.
- 근거가 없으면 praise를 null로 반환합니다.
- 선정 로직을 React에서 분리해 테스트합니다.

**Concerns**

- **HIGH:** SummaryCard에 score 배지와 evidenceBadge가 동시에 있으면 “카드당 수치 한 곳”을 위반할 수 있습니다.
- **MEDIUM:** dimension score만으로 “감점 0”을 판정하면 미측정/저커버리지 값을 칭찬할 수 있습니다.
- **MEDIUM:** 32-06 baseline 부족 때문에 mode3의 정량 개선 headline을 신뢰성 있게 만들 수 없습니다.
- **LOW:** gate 값 미확정 시 32-GATE-DECISIONS를 이 autonomous plan이 수정하도록 하지만 frontmatter에 파일이 없습니다.

**Suggestions**

- score와 evidence를 하나의 numeric trust cluster로 통합하거나 둘 중 하나만 표시합니다.
- praise eligibility에 coverage, confidence, spot-check 결과를 포함합니다.
- GATE-DECISIONS는 gate plan만 수정하고 32-07은 읽기 전용으로 유지합니다.

**Risk Assessment: MEDIUM** — 컴포넌트 구조는 좋지만 잘못된 칭찬이 신뢰도를 직접 훼손할 수 있습니다.

---

### [32-08 — 자막 큐·샘플 게이트](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-08-PLAN.md)

**Summary**

자막을 기존 tick에 얹는 구현은 효율적이지만, 실제 기기 TTS와 다른 macOS 샘플을 사용하면 핵심 샘플 게이트가 유효하지 않습니다.

**Strengths**

- 신규 타이머 없이 기존 재생 tick을 재사용합니다.
- fps 오류 시 빈 큐로 fail safe합니다.
- 자막과 오디오 구현 결정을 분리합니다.

**Concerns**

- **HIGH:** macOS `say -v Yuna`는 iOS 기기 AVSpeechSynthesizer의 실제 샘플이 아닙니다.
- **HIGH:** actual device sample을 만들 네이티브 module/build 경로가 gate 전에 없습니다.
- **MEDIUM:** deduction record와 fault zoom frame 간 stable join 규칙이 없습니다.
- **MEDIUM:** 일러스트의 라이선스·생성 provenance·정은지 선수 likeness 회피가 없습니다.

**Suggestions**

- 실제 iPhone preview build에서 expo-speech 샘플을 녹음해 비교합니다.
- 큐에 `recordId/cueId`를 두고 fault zoom과 stable key로 연결합니다.
- illustration metadata에 생성 방식, 사용 권리, non-likeness 확인을 기록합니다.

**Risk Assessment: HIGH** — 잘못된 샘플을 기반으로 네이티브 아키텍처를 선택할 수 있습니다.

---

### [32-09 — 파이프라인 방출](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-09-PLAN.md)

**Summary**

순수 조립을 pipeline에 연결하는 방향은 적절하지만 실제 배포 시점과 previous-analysis 선택, 부분 실패 격리가 부족합니다.

**Strengths**

- 기존 record에 optional 필드만 추가해 하위호환을 지킵니다.
- enrichment 실패로 분석 전체를 실패시키지 않습니다.
- LLM 금지어 런타임 필터를 둡니다.

**Concerns**

- **HIGH:** 이 변경은 32-13까지 프로덕션 배포되지 않아 32-12 UI 승인이 실제 신규 데이터를 검증하지 못합니다.
- **HIGH:** `get_previous_analysis`가 동일 motion/reference를 필터링하지 않습니다.
- **HIGH:** safety flag와 phrasebook criterion의 매핑이 정의되지 않았습니다.
- **MEDIUM:** enrichment 전체를 하나의 try/except로 감싸면 record 하나 오류로 mission·모든 문구가 함께 사라질 수 있습니다.
- **MEDIUM:** `coverage_gap 계열 실존 신호`가 구체적인 필드/enum으로 계획에 고정되지 않았습니다.

**Suggestions**

- 32-09 완료 직후 Lambda/SAM을 배포하고 real analysis contract smoke를 수행합니다.
- record별 phrase 조립과 mission/question 조립 실패를 분리합니다.
- coverage와 safety mapping을 명시적 adapter 함수와 fixture로 고정합니다.

**Risk Assessment: HIGH** — 코드가 완성돼도 UI gate 시점에 실제 환경에 존재하지 않는 기능이 됩니다.

---

### [32-10 — 감점 카드·게이지](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-10-PLAN.md)

**Summary**

한 카드 안에서 주장·증거·행동을 완결하는 구조는 phase 목표에 잘 맞지만, 게이지의 수학적 의미가 정의되지 않았습니다.

**Strengths**

- 3단 문장, zoom evidence, mission을 한 컴포넌트에 모읍니다.
- safety 카드에서 게임 요소를 구조적으로 차단합니다.
- legacy fallback을 둡니다.

**Concerns**

- **HIGH:** `current/target`만으로 gauge fill 비율을 계산하면 유효 범위가 없어 자의적인 시각 비율이 됩니다.
- **HIGH:** 목표가 범위, 허용 오차, circular angle인 규칙을 단일 target/direction으로 표현할 수 없습니다.
- **HIGH:** unit enum이 `deg/notch/score_delta`뿐이라 실제 deduction unit 전체를 포괄하지 못할 가능성이 큽니다.
- **MEDIUM:** zoom 이미지 loading/error/만료 URL fallback이 없습니다.
- **MEDIUM:** `recordIndex` 기반 ask-coach 연결은 후속 spot-check 필터링에서 깨집니다.

**Suggestions**

- rule에서 `validMin/validMax/current/targetRange/tolerance/unit`을 전달하고 gauge semantic을 테스트합니다.
- gauge를 만들 수 없는 record는 숫자 badge+텍스트만 표시합니다.
- 이미지 placeholder, retry, unavailable state를 추가합니다.
- 모든 카드 상호작용은 stable `recordId`를 사용합니다.

**Risk Assessment: HIGH** — 잘못된 게이지는 D-09가 막으려던 자의적 숫자를 시각적 비율로 다시 만들 수 있습니다.

---

### [32-11 — result.tsx 대배선](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-11-PLAN.md)

**Summary**

최종 정보 위계는 좋지만 가장 큰 UI 통합 계획임에도 의존성과 테스트가 부족합니다.

**Strengths**

- 요약→위험→top-1→영상 증거 순서가 명확합니다.
- legacy, clean pass, mode3를 별도로 확인합니다.
- reference corner invariant를 유지합니다.

**Concerns**

- **HIGH:** `cueTrack`을 사용하지만 32-08 dependency가 없습니다.
- **HIGH:** 실제 32-09 backend 방출이 배포되지 않은 상태에서 legacy fallback 중심으로 검증됩니다.
- **HIGH:** 자동 질문과 hidden card가 모두 `recordIndex`를 사용해 잘못된 카드로 점프할 수 있습니다.
- **MEDIUM:** 2,000줄 이상 화면의 대배선을 typecheck와 수동 screenshot만으로 검증합니다.
- **MEDIUM:** cue windows, zoom mapping, summary 계산이 render마다 재계산되면 VideoCompare tick과 함께 성능 저하가 생길 수 있습니다.
- **MEDIUM:** Dynamic Type, VoiceOver, 작은 화면 검증이 없습니다.

**Suggestions**

- `depends_on`에 32-08을 추가합니다.
- stable record ID 기반 map을 먼저 만든 후 UI를 배선합니다.
- section-order/visibility/legacy behavior를 순수 view-model 함수로 추출해 테스트합니다.
- useMemo와 render profiling을 포함합니다.
- 실제 신규 분석 doc으로 simulator와 실기기 gate를 수행합니다.

**Risk Assessment: HIGH** — phase UI의 결합점이면서 자동 검증과 실제 backend 데이터가 부족합니다.

---

### [32-12 — 오디오·실패 UX·OTA](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-12-PLAN.md)

**Summary**

A/B 어느 선택도 phase 안에서 끝내려는 의도는 좋지만, 네이티브 build와 backend 배포가 빠져 있어 현재 계획대로는 출시할 수 없습니다.

**Strengths**

- 공식 Expo 모듈 하나만 채택합니다.
- Polly 경로에서 canonical key와 exact match를 재사용합니다.
- 실패 UX와 D-09 전 화면 검증을 함께 마감합니다.

**Concerns**

- **HIGH:** 신규 네이티브 모듈 설치 후 OTA만 발행합니다. 새 EAS/TestFlight build가 필수입니다. [Expo 공식 설명](https://docs.expo.dev/eas-update/runtime-versions/)
- **HIGH:** `runtimeVersion: appVersion`인데 앱 버전 변경 계획이 없어 기존 native binary가 호환되지 않는 update를 받을 수 있습니다.
- **HIGH:** `app/package-lock.json`, `app.json`, illustration asset 경로가 `files_modified`에 없습니다.
- **HIGH:** B안의 `speakCue(text)` 인터페이스에는 audio key/cue ID가 없어 생성된 mp3와 현재 큐를 연결할 수 없습니다.
- **HIGH:** playback URL을 큐 시점에 요청하면 네트워크 지연으로 자막과 음성이 어긋날 수 있습니다.
- **HIGH:** Lambda/SAM 배포 절차 없이 OTA만 수행합니다.
- **MEDIUM:** cloud TTS는 문자 그대로 runtime generation이므로 “런타임 신규 생성 AI 0”의 시각 생성 한정 예외임을 문서화해야 합니다.
- **MEDIUM:** grep 기반 D-09 검사는 false positive/negative가 많습니다.

**Suggestions**

- 샘플 게이트 후 A/B별 plan을 물리적으로 분기합니다.
- native module 설치 → app/runtime version bump → EAS build → TestFlight submit → compatible OTA 순으로 변경합니다.
- B안은 cue ID별 URL을 미리 발급·prefetch하고 cache합니다.
- SAM deploy, Lambda version 확인, playback smoke를 OTA 전에 수행합니다.
- `package-lock.json`과 native config 파일을 변경 목록에 포함합니다.

**Risk Assessment: HIGH** — 현재 배포 경로는 실행 불가능하거나 기존 TestFlight 바이너리를 위험하게 만들 수 있습니다.

---

### [32-13 — omni spot-check](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-13-PLAN.md)

**Summary**

완료 후 비차단 검수는 속도 측면에서 합리적이지만, 검증 대상의 안정 ID와 praise 원천, pending/failure UX가 정의되지 않았습니다.

**Strengths**

- 동기 분석 latency에서 외부 호출을 분리합니다.
- 점수는 건드리지 않고 표시만 숨깁니다.
- 모델 실패 시 분석 완료 상태를 보존합니다.

**Concerns**

- **HIGH:** 앱이 생성하는 praise headline을 백엔드가 갖고 있지 않아 동일 문장을 검증할 수 없습니다.
- **HIGH:** `hiddenRecordIndices`는 record 정렬/추가/필터에 취약합니다.
- **HIGH:** status done 직후 spot-check 전에는 잘못된 카드가 잠시 노출됐다가 사라집니다.
- **HIGH:** API 실패를 fail-open하면 “틀린 말을 내보내느니 안 보여줌” 원칙을 보장하지 못합니다.
- **HIGH:** dummy text 1콜은 실제 video+records multimodal 입력 능력을 검증하지 않습니다.
- **HIGH:** sampling frame/window, 최대 record 수, timeout, 비용 cap이 없습니다.
- **HIGH:** Task 3은 Pod 배포만 설명하지만 `pipeline/app.py`·Firestore helper는 Lambda 배포가 필요합니다.
- **MEDIUM:** hidden index의 범위·중복·최대 길이 검증이 없습니다.
- **MEDIUM:** 불일치 이유가 저장되지 않아 운영자가 오숨김을 감사하기 어렵습니다.

**Suggestions**

- backend가 `summaryCandidate`를 생성·저장하고 앱도 이를 소비하도록 단일 원천화합니다.
- `recordId → verdict/reason/confidence` 결과를 저장합니다.
- `spotCheck.status='pending'`일 때 카드 노출 정책을 명시합니다.
- 실패 시 “검수되지 않은 카드 숨김” 또는 명확한 신뢰도 배지 중 하나를 제품 결정으로 받습니다.
- 실제 짧은 fixture video로 smoke하고 strict JSON schema를 사용합니다.
- Lambda deploy와 post-deploy smoke를 별도 task로 둡니다.

**Risk Assessment: HIGH** — 검수 기능 자체가 다른 카드를 숨기거나 검수 전 카드를 노출할 위험이 있습니다.

---

### [32-14 — RTMW 12관절 확장](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-14-PLAN.md)

**Summary**

“표시 먼저, 감점 나중” fail-safe는 매우 적절하지만 backend 소비처 전수 조사가 불완전하고 일부 계획 전제가 실제 코드와 다릅니다.

**Strengths**

- 감점 모듈 무접촉을 명확히 강제합니다.
- 8/12 legacy 문서를 모두 허용합니다.
- 용량·인덱스·confidence 분포를 배포 게이트에 포함합니다.

**Concerns**

- **HIGH:** 계획은 `firestore_admin`에 len==8 강제가 있다고 전제하지만 실제 validator는 현재 joint 수에서 길이를 파생합니다. 수정 지점이 부정확합니다.
- **HIGH:** `KeypointName` Literal, docstring, Gemini keypoint augmenter의 elbow mapping 등 backend 소비처가 files/task에 없습니다.
- **MEDIUM:** 앱만 하드코딩 전수 조사하고 backend의 “8 joints” 주석·mapping·schema consumer는 조사하지 않습니다.
- **MEDIUM:** JSON 직렬화 근사는 Firestore 실제 document/index 크기 증명이 아닙니다.
- **MEDIUM:** contract version을 유지할지 bump할지 정의되지 않았습니다.
- **LOW:** verification은 마지막에 “Pod 실측 1건”이라고 쓰지만 task/acceptance는 6동작입니다.

**Suggestions**

- backend와 app 전체에 대해 `KeypointName`, `_KEYPOINT_NAMES`, `"8 joints"`, schema mapping 소비처 audit를 수행합니다.
- 실제 Firestore serializer 또는 test project write로 크기를 검증합니다.
- version을 bump하고 `joints` 목록을 capability source로 사용한다고 계약에 명시합니다.
- 신규 elbow가 Gemini refinement 경로에서 audit-only로 남을지 실제 report 보강에 참여할지 결정합니다.

**Risk Assessment: HIGH** — 핵심 방향은 안전하지만 불완전한 소비처 audit가 31의 “데이터는 있는데 렌더 0” 문제를 반복할 수 있습니다.

---

### [32-15 — PR 인버전 보정·최종 게이트](/Users/kimtaesung/Dev/SunityMotion/.planning/phases/32-result-readability-3-omni/32-15-PLAN.md)

**Summary**

가장 위험한 계획입니다. spike 결과를 production pose preprocessing으로 옮기기 위한 좌표계·추론 순서 설계가 빠져 있습니다.

**Strengths**

- 전면 적용을 금지하고 env kill switch를 둡니다.
- 비인버전 5동작, 특히 power-spin 회귀를 명시적으로 검사합니다.
- 로컬 순수 검출과 GPU 검증을 분리합니다.

**Concerns**

- **HIGH:** pose 추론 전 keypoint로 inversion을 검출할 수 없어 1차/2차 추론 순환이 생깁니다.
- **HIGH:** 워프된 영상에서 얻은 좌표를 원본 영상 좌표로 inverse-transform하는 절차가 없습니다.
- **HIGH:** 두 번 추론한다면 latency/비용 영향이 계획에 없습니다.
- **HIGH:** homography가 crop, camera intrinsic, frame별 안정화와 어떤 좌표계에서 결합되는지 없습니다.
- **HIGH:** 단위테스트가 detector만 검증하고 forward→inverse 좌표 round-trip, NaN/out-of-frame, 경계 interpolation을 검증하지 않습니다.
- **HIGH:** “invert 개선 방향”, “비인버전 변동 0”은 명확한 수치 threshold가 아닙니다.
- **MEDIUM:** 한 inversion fixture로 detection false positive/negative를 평가하기 부족합니다.
- **MEDIUM:** full pipeline cold rerun은 Gemini 외부 호출까지 포함하면 동일 출력 보장이 어렵습니다.

**Suggestions**

- 이 계획을 production execute가 아니라 별도 bounded integration spike로 먼저 바꿉니다.
- 아키텍처를 다음 중 하나로 확정합니다:
  1. recognizer/metadata 선행 검출 → 단일 warped inference,
  2. 저비용 1차 pose → inversion 검출 → 선택적 2차 inference,
  3. 원본 pose 결과의 좌표 post-correction.
- forward/inverse homography와 원본 좌표 round-trip 테스트를 필수화합니다.
- latency budget, detection precision/recall, boneCV 개선 최소치, 비인버전 허용 오차를 수치로 고정합니다.
- inversion transition·sideways·occlusion fixture를 추가합니다.

**Risk Assessment: HIGH** — 현재 설계는 좌표 품질을 개선하기보다 overlay와 채점 좌표계를 훼손할 가능성이 있습니다.

---

## Strengths

- D-01~D-30 추적성이 전반적으로 뛰어납니다.
- 4대 미결 게이트를 구현 전에 사람 결정으로 닫는 구조가 좋습니다.
- contract 3-way, scoped validator, legacy normalize를 반복 적용합니다.
- 점수·안전 영역의 fail-safe와 비차단 부가 기능 원칙이 명확합니다.
- 최악 데이터 케이스와 실기기 확인을 계획에 포함했습니다.
- “UI critical path 먼저, 엔진 레버 뒤”라는 큰 우선순위는 타당합니다.

## Suggestions

우선 다음 순서로 계획을 수정하는 것이 좋습니다.

1. 32-06 mission schema와 stable fault ID를 재설계합니다.
2. dependency graph와 D-23 sweep 정책을 정합시킵니다.
3. 32-09 이후 Lambda 배포·실분석 gate를 추가합니다.
4. 32-08 샘플 gate에 actual iPhone build 경로를 넣습니다.
5. 32-12에 native build/runtime version/TestFlight 절차를 추가합니다.
6. 32-13을 record ID·summary candidate·pending 정책 기반으로 변경합니다.
7. 32-15는 integration spike 결과가 나온 뒤 production plan으로 다시 작성합니다.
8. 모든 human checkpoint는 mock/legacy가 아닌 새 production analysis document로 최종 승인하도록 합니다.

## Final Risk Assessment

**Overall Risk: HIGH**

문서 품질과 의사결정 추적은 우수하지만, 현재 계획은 다음 세 축에서 phase 완료를 잘못 선언할 수 있습니다.

- UI가 실제 신규 backend contract를 받기 전에 승인될 수 있음
- 네이티브 오디오 기능이 기존 TestFlight 바이너리에 OTA로 배포될 수 없음
- 미션·spot-check·PR 보정의 데이터 identity와 좌표계가 충분히 정의되지 않음

이 세 문제를 수정하면 나머지는 주로 범위 관리와 검증 강화 문제로 낮아집니다.

> 참고: `gsd-review` 외부 Claude 리뷰어도 호출하려 했으나 로컬 CLI가 로그인되지 않아 독립 결과를 얻지 못했습니다. 이 리뷰는 저장소 코드와 15개 계획을 직접 대조한 결과이며 파일 수정은 하지 않았습니다.

---

## Consensus Summary

단일 리뷰어(codex)만 가용했으므로 교차 합의(2+ reviewer agreement)는 성립하지 않는다. 아래는 codex 리뷰의 최상위 항목을 우선순위로 정리한 것이다.

### Agreed Strengths (단일 리뷰어)

- D-01~D-30 요구사항 추적성과 4대 게이트(사람 결정 선행 구조)가 우수
- contract 3면(TS/Python/validator) + scoped validator + legacy normalize 패턴의 일관 적용
- 점수·안전 영역 fail-safe와 "비차단 부가 기능" 원칙이 명확

### Agreed Concerns (단일 리뷰어 — 실행 전 차단 7건)

1. **미션 이력 계약** (32-06/32-09): prev.mission에 baseline 측정값 부재 → 개선량 계산 불가. criterion 단독 판별은 좌우 관절 병합. 안정 faultKey + baseline 저장 필요
2. **배포 순서** (32-09/32-11/32-12): 32-09 백엔드 방출이 32-13까지 미배포인데 32-12에서 UI 실기기 승인 선행. pipeline/app.py는 Lambda라 Pod git pull로 배포 안 됨 → 32-09 후 SAM 배포+실분석 게이트 필요
3. **오디오 네이티브 빌드** (32-08/32-12): expo-speech/expo-audio 미설치 상태에서 OTA만 계획 → 네이티브 모듈은 새 EAS build+TestFlight 필수, runtimeVersion(appVersion) 정합 필요. macOS `say` 샘플은 iOS 실기기 TTS 대변 못함
4. **32-11 의존성 누락**: cueTrack/cueWindows 소비하는데 depends_on에 32-08 없음
5. **spot-check 계약** (32-13): praise headline 원천이 앱에만 있어 교차검증 불성립, hiddenRecordIndices는 정렬/필터에 취약 → backend summaryCandidate + recordId 기반 재설계
6. **PR 인버전 순환 의존** (32-15): "추론 전 keypoint로 검출"은 keypoint가 아직 없음. 1차 추론→검출→워프→2차 추론 여부 + inverse-transform 절차 미정 → production plan 전에 bounded integration spike 권고
7. **D-23 위반** (32-01/32-03): "웨이브마다 6동작 전수 스윕" 결정 대비 1 fixture만 검증 — CONTEXT 개정 승인 없이 임의 축소 불가

### Divergent Views

해당 없음 (단일 리뷰어).
