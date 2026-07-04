---
phase: quick-260704-fwb
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/coach_writer.py
  - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
  - backend/shared/python/sunity_shared/analysis/exercise_map.py
  - backend/functions/pipeline/app.py
  - backend/tests/test_coach_writer.py
  - backend/tests/gemini/test_coach_writer_v2.py
  - backend/tests/phase13/test_map_exercises.py
  - app/src/app/(tabs)/analyze.tsx
  - app/src/app/analysis/reference.tsx
  - app/src/app/analysis/loading.tsx
  - app/src/app/analysis/result.tsx
autonomous: true
requirements: [QUICK-260704-FWB]

must_haves:
  truths:
    - "코치 LLM 프롬프트(Cerebras+Gemini)가 '원인(무엇 때문에) → 기전(무엇이 무너짐) → 처방(어떻게 고침)' 구조를 강제하고, 상태 서술만 있는 문장을 금지한다"
    - "vision veto applied 분석에서 보완 운동이 결함 keypoint_set(leg/shoulder 등) 부위 운동을 포함하며, 무관한 그립 운동이 결함 부위 운동보다 앞서지 않는다"
    - "저화질 경고를 보고 '이대로 계속' 한 업로드가 not_pole_motion 으로 실패하면 '기준 동작과 너무 달라요' 대신 화질 우선 안내가 뜬다"
    - "'먼저 교정할 점' 카드가 상태 서술(primaryFault)에 원인 기전(rootCauseHypotheses)과 처방 연결을 함께 노출한다"
    - "점수/채점/게이트 로직(deduction_engine, dimensions, not_pole 임계)은 byte 무접촉이다"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/exercise_map.py"
      provides: "fault_keypoint_sets 기반 결함 부위 매칭 (_KEYPOINT_SET_TO_DEFECTS + map_exercises 신규 kwarg)"
      contains: "fault_keypoint_sets"
    - path: "backend/shared/python/sunity_shared/analysis/coach_writer.py"
      provides: "처방 구조 강제 Cerebras 프롬프트"
    - path: "app/src/app/analysis/loading.tsx"
      provides: "not_pole_motion + 저화질 플래그 → 화질 우선 에러 카피 분기"
  key_links:
    - from: "backend/functions/pipeline/app.py"
      to: "exercise_map.map_exercises"
      via: "fault_keypoint_sets kwarg (vision_fault_context 유래)"
      pattern: "fault_keypoint_sets"
    - from: "app/src/app/(tabs)/analyze.tsx"
      to: "app/src/app/analysis/loading.tsx"
      via: "router params lowQuality ('1') — reference.tsx 경유 포함"
      pattern: "lowQuality"
    - from: "app/src/app/analysis/result.tsx"
      to: "result.visionVeto.rootCauseHypotheses"
      via: "먼저 교정할 점 카드 원인 기전 렌더"
      pattern: "rootCauseHypotheses"
---

<objective>
belle 실기기 피드백 마지막 묶음(E): (1) 코칭 팁을 상태 서술이 아니라 원인 기전 + 구체 처방 구조로,
(2) 보완 운동을 실제 결함 부위(vision veto faultKey keypoint_set) 기반으로 매칭,
(3) 저화질 경고를 승인하고 진행한 업로드가 not_pole_motion 으로 실패하면 화질 우선 안내로 분기.

Purpose: kip-up fault 88점 결과 화면에서 "다리 스플릿 부족·상체 정렬 흐트러짐" 결함에
Farmer's Walk(그립)가 추천되고, 코칭이 "상체가 흐트러짐"이라는 상태 서술에 그치고,
카톡 압축본 실패가 "기준 동작과 너무 달라요"로 오해되는 3건을 닫는다.
현장 리서치 원칙: AI가 일반적 답변만 하면 수강생 이탈 — 수치는 보조, 원인이 핵심.

Output: 백엔드 프롬프트/매핑 개선 + 앱 카피/카드 분기. 점수·채점·게이트 로직 무접촉.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@app/CLAUDE.md

확정된 조사 결과 (플래너 코드 확인 완료 — executor 재조사 불필요):

1. **"먼저 교정할 점" 카드** = `result.visionVeto.primaryFault` 를 app/src/app/analysis/result.tsx:1194-1207
   이 직접 렌더 (LLM 코칭 팁 아님). 원인 기전 데이터는 **이미 Firestore doc 에 있다**:
   `visionVeto.rootCauseHypotheses[]` = `{text ("~로 보임" 가설), faultKey {keypoint_set,...}, supportCount}`
   (app/src/types/analysis.ts:395 applied variant 에 이미 타입 존재, normalize 통과 확인됨 — 260702-q8q 가
   실패원인 상세 시트에서 이미 소비). `visionVeto.faultJoints` (정식 keypoint 이름 list) 도 존재.
2. **코칭 팁 생성 경로**: 13-C 섹션형 듀얼 — `_build_coach_context` (backend/functions/pipeline/app.py:824)
   가 kismam top 3 관절 deviation + angleFixture + visionFault(rootCauseHypotheses) 를 담아
   Gemini(coach_writer_v2, 원인 causes title/explanation + coachNote 담당) 와
   Cerebras(coach_writer.py, 처방 causes[].fix + injuryRisk 담당) 를 양쪽 호출,
   `assemble.assemble_dual_coach_sections` (assemble.py:459) 가 섹션 조립. 실측 데이터
   (deviation_deg, 동작별 정의각도 fixture, vision 가설)는 이미 프롬프트에 주입돼 있음 —
   부족한 건 **출력 구조 지시** (기전 사슬 + 처방).
3. **보완 운동**: `exercise_map.map_exercises` (pipeline app.py:3682 호출) 가
   forcePatternInference.findings 의 sourceSignal/jointHint 만으로 backend/data/corrective_exercises.json
   의 defects 트리거를 매칭. vision veto 결함(faultKey.keypoint_set: "arm","shoulder","leg","hip",
   "head_neck","grip","torso","line" — vision_veto.py:77 FAULT_KEYPOINT_SETS)은 **전혀 안 들어감** →
   kip-up 결함(leg split + 상체)에 grip_weak(Farmer's Walk) 미스매치. 호출 시점(3682)은
   `_apply_vision_veto` (3466) 이후라 `vision_fault_context` 와 `result["visionVeto"]` 둘 다 스코프 내.
   defect 키 6종: grip_weak / shoulder_unstable / core_weak / legs_not_extended / hip_hamstring_tight /
   glute_hip_unstable.
4. **저화질 흐름**: analyze.tsx:108-125 `checkLowQuality` (짧은변<720 또는 <6Mbps) →
   `lowQualityPicked` 모달 → `continueLowQuality` (:252) 가 승인 경로. 라우팅은
   `routeAfterPick` (:132) — mode1+referenceMotionId/mode3 → `/analysis/loading` 직행,
   mode1 미선택 → `/analysis/reference` (reference.tsx:76 이 loading 으로 재라우팅, name/uri/size/format
   passthrough — 여기도 플래그 통과 필요). loading.tsx 에러 분기 = :351-403
   (`isNotPole` → '기준 동작과 너무 달라요' + tipCard). 백엔드/계약 변경 불필요 — 앱 로컬 param 전달로 충분.
</context>

<tasks>

<task type="auto">
  <name>Task 1: 코치 프롬프트 처방화 — 원인 기전 + 구체 처방 구조 강제 (백엔드)</name>
  <files>backend/shared/python/sunity_shared/analysis/coach_writer.py, backend/shared/python/sunity_shared/gemini/coach_writer_v2.py, backend/tests/test_coach_writer.py, backend/tests/gemini/test_coach_writer_v2.py</files>
  <action>
    프롬프트/조립 개선만 — 새 모델·새 파이프라인·새 LLM 호출 금지. JSON 응답 스키마
    ({detail, detail2:{causes[{title,explanation,fix}], injuryRisk, coachNote}}) 와
    _normalize_entry / validator(tone_validation, 14 용어 게이트) 는 형상 불변.

    (1) coach_writer.py `_SYSTEM` + `_build_prompt`:
    - causes 각 항목의 explanation 은 "무엇 때문에(원인) → 무엇이 무너짐(결과 기전)" 사슬로
      쓰도록 지시. belle 예시 톤: "왼팔 위치가 불안정해 상체 지지가 무너지고, 그로 인해 균형이
      흐트러질 수 있어요" — 상태 서술 단독("상체가 흐트러졌어요")을 금지하는 명시 라인 추가.
    - fix 는 "그 원인일 경우 어떻게 연습/교정하는지" 구체 행동 지시(자세 큐/반복 방법) 로 쓰도록
      지시 강화. detail(카드 한 줄) 도 관찰 서술이 아니라 실행 지시형으로.
    - 거짓 구체성 금지 유지·강화: 주입된 실측(관절별 deviation_deg, angleFixture 각도,
      visionFault 가설 텍스트)만 인용, 측정 안 된 수치·부위 생성 금지 라인 유지.
    - `_format_vision_fault_lines`: rootCauseHypotheses 를 "원인 사슬의 출발점으로 사용하라"는
      지시 문구로 승격 (현재는 '참고' 힌트). vision_fault dict 에 supportedDifferences 가 있으면
      서술 텍스트 필드만 골라 실측 근거 라인으로 추가 렌더 — 키 존재를 방어적으로 확인하고
      없으면 기존 동작 불변 (fabrication 0).
    (2) coach_writer_v2.py `_COACH_SYSTEM_INSTRUCTION` + `_build_prompt`:
    - explanation 기전 사슬 구조(원인 → 무너지는 것) 요구 라인 추가, "차이가 작아도 잠재 원인"
      가이드와 공존. coachNote(강사 확인) 톤과 14 용어 게이트는 유지 — validator 를 깨지 않는
      범위에서 지시 라인만 추가.
    (3) 테스트: 기존 test_coach_writer.py / gemini/test_coach_writer_v2.py 에 프롬프트 문자열
    단위테스트 추가 — (a) 기전 사슬 지시 라인이 시스템/유저 프롬프트에 포함, (b) 상태-서술-금지
    라인 포함, (c) vision_fault 없는 입력에서 프롬프트가 기존과 동등(기전 지시 외 diff 없음 —
    graceful 불변), (d) supportedDifferences 부재 시 크래시 0. LLM 실호출 없는 순수 프롬프트
    빌드 테스트만 (의미있는 테스트 원칙).

    점수 경로 무접촉: dimensions/deduction_engine/kismam/vision_veto 판정 로직 파일은 열지도 않는다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python3 -m pytest tests/test_coach_writer.py tests/gemini/test_coach_writer_v2.py tests/phase13/test_coach_prompt_angle_fixture.py tests/phase13/test_section_dual_coach.py -q</automated>
  </verify>
  <done>프롬프트 빌드 테스트 신규 포함 전부 PASS. 기존 coach 조립/각도 fixture/섹션 듀얼 테스트 회귀 0. 스키마·validator 형상 불변.</done>
</task>

<task type="auto">
  <name>Task 2: 보완 운동 결함 부위 매칭 — vision faultKey keypoint_set 배선 (백엔드)</name>
  <files>backend/shared/python/sunity_shared/analysis/exercise_map.py, backend/functions/pipeline/app.py, backend/tests/phase13/test_map_exercises.py</files>
  <action>
    새 데이터 소스 발명 금지 — 기존 corrective_exercises.json defect 6종에 부위별 사전 매핑만 추가.

    (1) exercise_map.py:
    - 모듈 상수 `_KEYPOINT_SET_TO_DEFECTS: dict[str, tuple[str, ...]]` 신설
      (FAULT_KEYPOINT_SETS 8값 전부 커버, vision_veto import 금지 — 순수성 유지, 문자열 리터럴로):
      leg → (hip_hamstring_tight, legs_not_extended) / hip → (glute_hip_unstable, hip_hamstring_tight) /
      shoulder → (shoulder_unstable,) / arm → (shoulder_unstable,) / head_neck → (shoulder_unstable,) /
      grip → (grip_weak,) / torso → (core_weak,) / line → (core_weak,).
      스플릿 각도 부족 = 고관절 유연성 → hip_hamstring_tight 를 leg 의 1순위로 (belle 케이스 정합).
    - `map_exercises` 에 `fault_keypoint_sets: list[str] | None = None` kwarg 추가 (default None =
      기존 동작 byte-동일, 하위호환). None 아니면 순서 보존·중복 제거로 defect 키 도출.
    - 정렬 우선순위: painArea 안전 운동(기존 유지, 최우선) → **fault 유래 defect(신규, 2순위)** →
      forcePatternInference 유래 defect(기존, 3순위). dedup/cap(_MAX_EXERCISES=5) 로직 재사용.
      알 수 없는 keypoint_set 값은 조용히 skip (graceful).
    - 순수성 보존: 입력은 plain list[str], numpy/AWS/네트워크 0
      (test_exercise_map_no_scoring_leak.py grep 게이트 통과 유지).
    (2) pipeline app.py 호출부(:3682 부근):
    - `result.get("visionVeto", {}).get("status") == "applied"` 이고 `vision_fault_context` 가
      None 아닐 때만 keypoint_set 목록 도출: `vision_fault_context.supported_differences[]` 의
      `_faultKey.keypoint_set` + `root_cause_hypotheses[].fault_key.keypoint_set` 를 순서 보존·중복
      제거로 join → `map_exercises(..., fault_keypoint_sets=...)` 전달. 그 외(not applied/None/예외)
      는 None 전달 = 기존 경로 불변. 도출 실패는 try/except 로 감싸 분석을 죽이지 않음
      (log.exception + None 폴백).
    (3) 테스트 (tests/phase13/test_map_exercises.py 확장):
    - kip-up 시나리오: fault_keypoint_sets=["leg","shoulder"] + grip 트리거 findings 동시 입력 →
      출력 앞순위에 hip_hamstring_tight/legs_not_extended/shoulder_unstable 계열 운동, grip 운동이
      결함 부위 운동보다 앞서지 않음.
    - fault_keypoint_sets=None → 기존 결과와 동일 (회귀 가드).
    - painArea 우선순위 불변 / dedup·cap(≤5) 불변 / 미지 keypoint_set graceful /
      출력 형상 {name,setsReps,purpose,sourceRef} 불변 (recommendedExercises 계약·TS 변경 0).

    D-05 하드월 유지: painAreas·fault 매핑 모두 점수 경로 진입 0. 채점 파일 무접촉.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python3 -m pytest tests/phase13/ -q</automated>
  </verify>
  <done>phase13 전체 PASS (신규 fault 매칭 + 기존 lockstep/no-scoring-leak/coverage 회귀 0). fault_keypoint_sets=None 경로 byte-동등. 계약(RecommendedExercise) 변경 0.</done>
</task>

<task type="auto">
  <name>Task 3: 앱 — 저화질 not_pole 문구 분기 + '먼저 교정할 점' 원인·처방 구조 노출</name>
  <files>app/src/app/(tabs)/analyze.tsx, app/src/app/analysis/reference.tsx, app/src/app/analysis/loading.tsx, app/src/app/analysis/result.tsx</files>
  <action>
    앱 로컬 처리만 — 백엔드/계약(analysis.ts·models.py·contract.md) 변경 0. 한국어 카피,
    이모지 금지, 색·간격은 src/theme 토큰만.

    (A) 저화질 플래그 로컬 전달 (analyze → [reference →] loading):
    - analyze.tsx: `Picked` 로컬 타입에 `lowQuality?: boolean` 추가. `continueLowQuality` (:252)
      에서 보류 picked 에 lowQuality:true 를 심어 라우팅 재개 — "경고를 봤는데 진행한" 업로드만
      플래그 (스펙 정합; 경고 없이 통과한 영상은 플래그 X). `routeAfterPick` (:132) 의 두 push
      (loading 직행 / reference 경유) params 에 `lowQuality: picked.lowQuality ? '1' : undefined` 추가.
    - reference.tsx: useLocalSearchParams 에 lowQuality 추가, `startAnalysis` (:76) 의 loading
      push params 로 passthrough.
    - loading.tsx: useLocalSearchParams (:265) 에 lowQuality 추가. failed 분기 (:351)에서
      `isNotPole && lowQuality === '1'` 이면 — errorTitle 을 "영상 화질이 낮아 분석하지 못했을 수
      있어요" 계열로, 본문(:372 ERROR_MESSAGE 자리)을 "영상 화질이 낮아 자세를 인식하지 못했을 수
      있어요. 원본 화질 영상으로 다시 시도하거나 앱에서 직접 촬영해 주세요." 로 교체하고,
      isNotPole tipCard (:384) 항목을 화질 우선 순서(원본 화질/직접 촬영 → 기준 동작 일치 → 전신)
      로 조정. 저화질 플래그 없는 not_pole 은 기존 카피 그대로 (회귀 0). errorCode·차단 임계 무접촉.
    (B) result.tsx '먼저 교정할 점' 카드 (:1194-1207) 처방 구조:
    - primaryFault(상태) 아래에 원인 기전 렌더: `result.visionVeto.rootCauseHypotheses` (applied
      variant, 이미 타입 존재) 의 text 를 supportCount 내림차순 상위 최대 2건, "~로 보임" 가설
      어투 그대로 (측정 안 된 단정 금지). 없으면 섹션 생략 (graceful — legacy doc 크래시 0).
    - 처방 연결: `displayTips` 중 `tip.joint` 이 `result.visionVeto.faultJoints` 에 포함되는 첫
      팁이 있으면 그 팁의 detail(실행 지시 한 줄)을 "이렇게 교정해 보세요:" 라벨과 함께 표시,
      매칭 팁이 없으면 "아래 코칭 팁에서 관절별 교정 방법을 확인하세요." 한 줄 폴백.
      기존 vetoLeadNote(:1203) 는 이 구조와 중복되지 않게 문구 정리.
    - 스타일은 기존 tipDetail/vetoLeadNote 패턴 재사용 + StyleSheet 하단 추가, theme 토큰만.
      accessibility 속성 기존 관례 유지.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npm run typecheck</automated>
  </verify>
  <done>tsc --noEmit clean. 저화질 승인 업로드의 not_pole 실패만 화질 카피로 분기(플래그 없으면 기존 카피). '먼저 교정할 점' 카드가 상태→원인 기전→처방 순으로 렌더, rootCauseHypotheses 부재 doc 에서 크래시 0. 계약 파일 diff 0.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM 출력 → 앱 표시 | Cerebras/Gemini 코칭 텍스트가 사용자에게 렌더됨 (기존 validator/normalize 경로 유지) |
| 라우터 params → 화면 분기 | lowQuality 문자열 param — 표시 카피 분기에만 사용, 로직/점수 무영향 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-fwb-01 | Tampering | coach 프롬프트 주입 데이터 | mitigate | 기존 _normalize_entry/tone_validation 게이트 유지, 스키마 형상 불변 — 지시 라인만 추가 |
| T-fwb-02 | Info Disclosure | lowQuality param | accept | 표시 분기 전용 로컬 플래그, 민감정보 아님, 백엔드 미전송 |
| T-fwb-SC | Tampering | 패키지 설치 | accept | 신규 패키지 0 (npm/pip install 없음) |
</threat_model>

<verification>
- backend: `python3 -m pytest tests/test_coach_writer.py tests/gemini/test_coach_writer_v2.py tests/phase13/ -q` 전부 PASS, 회귀 0
- app: `npm run typecheck` clean
- 채점 무접촉 grep: `git diff --name-only` 에 dimensions.py / deduction_engine.py / kismam.py / vision_veto.py / models.py / types/analysis.ts 부재
- LLM 실출력 품질 + 보완운동 실매칭 확인 = pod 재기동 후 kip-up 재분석 (orchestrator+belle 체크리스트 — executor SSH 금지):
  1. 코칭 팁 causes 가 "X 때문에 Y가 무너짐 → Z 연습" 구조인지
  2. kip-up fault 결과의 보완 운동에 다리/고관절/어깨 운동 포함, Farmer's Walk 류 그립 운동이 선두 아님
  3. 카톡 압축본(저화질 경고 승인) not_pole 실패 시 화질 안내 문구
</verification>

<success_criteria>
- 코치 양 writer 프롬프트가 기전 사슬 + 처방 구조를 강제 (프롬프트 단위테스트로 고정)
- vision veto 결함 부위가 보완 운동 매칭에 배선 (None 폴백 하위호환, 계약 불변)
- 저화질 승인 업로드의 not_pole 실패가 화질 우선 안내로 분기 (앱 로컬, 백엔드 변경 0)
- '먼저 교정할 점' 카드 = 상태 + 원인 기전 + 처방 연결
- 점수/채점/게이트 파일 무접촉
</success_criteria>

<output>
Create `.planning/quick/260704-fwb-coach-prescriptive-exercise-match/260704-fwb-SUMMARY.md` when done
</output>
