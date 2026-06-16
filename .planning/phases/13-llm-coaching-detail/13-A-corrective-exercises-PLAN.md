---
phase: 13-llm-coaching-detail
plan: A
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/data/corrective_exercises.json
  - backend/shared/python/sunity_shared/analysis/exercise_map.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/functions/pipeline/app.py
  - app/src/types/analysis.ts
  - backend/shared/python/sunity_shared/models.py
  - docs/contract.md
  - app/src/lib/userAnalyses.ts
  - app/src/data/correctiveExercises.ts
  - app/src/components/RecommendedExerciseModal.tsx
  - app/src/app/analysis/result.tsx
  - backend/tests/phase13/__init__.py
  - backend/tests/phase13/conftest.py
  - backend/tests/phase13/fixtures/sample_force_pattern_inference.json
  - backend/tests/phase13/test_corrective_exercises_fixture.py
  - backend/tests/phase13/test_map_exercises.py
  - backend/tests/phase13/test_exercise_map_no_scoring_leak.py
  - backend/tests/phase13/test_recommended_exercises_lockstep.py
  - backend/tests/phase13/test_corrective_exercises_app_lockstep.py
autonomous: true
requirements: [PERS-03]
must_haves:
  truths:
    - "분석 결과(실패 원인 후보 + 통증부위)에 맞는 보완 운동 3~5개가 result 에 산출된다 (criteria 1,2)"
    - "매핑은 forcePatternInference.findings + bodyProfile.painAreas + motion_id 를 입력으로 쓴다 (criteria 3)"
    - "사용자가 결과 화면에서 보완 운동 카드를 보고 '다른 운동 보기' 모달로 전체 라이브러리(app/src/data/correctiveExercises.ts)를 열람한다 — Firestore recommendedExercises 는 3~5 개인화 subset, 모달은 풀 라이브러리 browse (criteria 4, HIGH-1 옵션 a)"
    - "painAreas 가 dimension_scores 등 채점 경로로 유입되지 않는다 (D-05)"
  artifacts:
    - path: "backend/data/corrective_exercises.json"
      provides: "5 defect-key + 8 painArea-key 보완운동 라이브러리 fixture"
      contains: "\"defects\""
    - path: "backend/shared/python/sunity_shared/analysis/exercise_map.py"
      provides: "pure map_exercises(force_pattern_inference, pain_areas, motion_id) -> list[dict]"
      exports: ["map_exercises"]
    - path: "app/src/data/correctiveExercises.ts"
      provides: "백엔드 corrective_exercises.json 의 app-side mirror (전체 라이브러리 browse data source) + schemaVersion"
      contains: "schemaVersion"
    - path: "app/src/components/RecommendedExerciseModal.tsx"
      provides: "다른 운동 보기 전체 라이브러리 모달 (correctiveExercises.ts read)"
      min_lines: 60
  key_links:
    - from: "backend/functions/pipeline/app.py"
      to: "exercise_map.map_exercises"
      via: "force_pattern_inference_dict 직후 호출 + complete_analysis(recommended_exercises=)"
      pattern: "map_exercises\\("
    - from: "app/src/app/analysis/result.tsx"
      to: "result.recommendedExercises"
      via: "보완 운동 섹션 카드 렌더 + RecommendedExerciseModal mount"
      pattern: "recommendedExercises"
    - from: "app/src/components/RecommendedExerciseModal.tsx"
      to: "app/src/data/correctiveExercises.ts"
      via: "전체 라이브러리 운동 목록 import 후 browse (Firestore subset 아님)"
      pattern: "correctiveExercises"
---

<objective>
분석 결과의 실패 원인 후보(Phase 9 forcePatternInference.findings)와 자가입력 통증부위(BodyProfile.painAreas)에 맞춰 보완 운동·스트레칭을 자동 매핑하고, 결과 화면에 3~5개 카드 + "다른 운동 보기" 모달로 표시한다. PERS-03 — "분석 → 행동 → 재구매". (ROADMAP Phase 13 success criteria 1-4, D-03/D-04/D-05.)

Purpose: 점수만으로 끝나지 않고 사용자가 다음 연습 행동을 받게 한다. NotebookLM 큐레이션 운동을 결함/통증부위별로 매핑.
Output: 커밋된 라이브러리 fixture(백엔드) + app-side mirror(correctiveExercises.ts) + 순수 매핑 함수 + 3-way 계약 필드 `recommendedExercises` + result.tsx 보완 운동 섹션 + 전체 라이브러리 모달. GPU/Pod 불필요, 단위테스트로 전부 검증.

Negative scope fence: D-01 (연령·성별 + 국민체력100 규준 맞춤 = v2 PERS-04) 와 D-02 (`backend/judging_data/fitness_norms_kspo.yaml` = 커밋된 채 대기, v1 미소비) 는 본 phase 비대상 — 매핑 입력은 Phase 9 findings + painAreas 만(D-03), 체력 자동 등급배치 금지. fitness_norms_kspo.yaml 을 import/소비하지 않는다.
HIGH-1 (direct review) 박제: "다른 운동 보기" = 옵션 (a) 전체 라이브러리 app data path. 옵션 (b) 개인화 alternates(v2) / 옵션 (c) narrow scope 금지 — 모달은 풀 라이브러리를 browse 한다.
</objective>

<phase_goal>
**As a** 폴스포츠 수강생, **I want to** 분석 결과에서 내 실패 원인과 통증부위에 맞는 보완 운동을 바로 받고 더 많은 운동을 열람할 수 있길, **so that** 점수를 확인한 뒤 무엇을 연습할지 알고 다음 세션으로 이어간다.
</phase_goal>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/13-llm-coaching-detail/13-CONTEXT.md
@.planning/phases/13-llm-coaching-detail/13-RESEARCH.md
@.planning/phases/13-llm-coaching-detail/13-PATTERNS.md
@.planning/phases/13-llm-coaching-detail/13-VALIDATION.md
@./CLAUDE.md
@./backend/CLAUDE.md
@./app/CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: 라이브러리 fixture + Wave 0 test 인프라 + 보완운동 fixture 스키마 게이트</name>
  <files>backend/data/corrective_exercises.json, backend/tests/phase13/__init__.py, backend/tests/phase13/conftest.py, backend/tests/phase13/fixtures/sample_force_pattern_inference.json, backend/tests/phase13/test_corrective_exercises_fixture.py</files>
  <read_first>
    - backend/data/aka-mapping.json (헤더/엔트리/sourceRef 메타 컨벤션 analog — 1:1 mirror)
    - .planning/phases/13-llm-coaching-detail/13-RESEARCH.md §"NotebookLM Primary-Source Findings B" (운동 content verbatim + cite) + §"Plan A — Storage Decision" (스키마)
    - backend/shared/python/sunity_shared/models.py L51-60 (PAIN_AREAS 8 멤버 frozenset — painAreas 키 정합 강제)
    - backend/tests/phase09/conftest.py (phase13 test 인프라 mirror 대상)
  </read_first>
  <action>
    `backend/data/corrective_exercises.json` 신설. 헤더는 aka-mapping.json 컨벤션 그대로: `schemaVersion:"1.0.0"`, `lastUpdated:"2026-06-16"`, `sourceNotebook:"e688fb4e-a4fb-4e83-a168-9c4726a98e09"`, `sourceNotebookName:"폴스포츠에 대한 지식"`. 두 최상위 키: `defects`(정확히 5 키 — `grip_weak`/`shoulder_unstable`/`core_weak`/`legs_not_extended`/`hip_hamstring_tight`)와 `painAreas`(정확히 8 키 = models.PAIN_AREAS 멤버 — shoulder/wrist/lower_back/knee/ankle/neck/hip/elbow). 각 defect = `{triggers:{sourceSignals:[...], jointHints:[...]}, exercises:[...]}` 이며 exercises 는 결함당 5개 이상, 각 항목 = `{name, setsReps, purpose, sourceRef}` (sourceRef 는 "NotebookLM e688fb4e [n]" 형식). 각 painArea = `{avoid:str, exercises:[{name,setsReps,purpose,sourceRef}, ...]}`. 운동 content 는 RESEARCH §B "Defect → exercises" + "painArea → safe-reinforce" 표에서 verbatim — 임의 생성 금지. trigger sourceSignals 는 force_pattern.py ForceSourceSignal enum(axis_tilt/pelvis_drop/late_contact/high_jitter/high_jerk/abnormal_release) 값만 사용. **schemaVersion 은 Task 3 의 app-side mirror(correctiveExercises.ts)와 lockstep 키이므로 정확히 박제.**
    phase13 test 인프라 신설: `backend/tests/phase13/__init__.py`(빈 파일) + `conftest.py`(phase09 conftest mirror — repo-root path resolution + fixture 로더 헬퍼) + `fixtures/sample_force_pattern_inference.json`(camelCase findings[] 샘플 — pattern/phase/sourceSignal/reason/interpretation/confidence/jointHint/warnings 키, late_contact + axis_tilt 신호 최소 2 finding 포함).
    `test_corrective_exercises_fixture.py`: fixture 로드 + 스키마 검증 — defects 정확히 5 키, painAreas 정확히 8 키 = models.PAIN_AREAS set, 각 defect exercises >= 5, 모든 exercise 가 name/setsReps/purpose/sourceRef 필드 보유, sourceRef 가 "NotebookLM" 포함.
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/phase13/test_corrective_exercises_fixture.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - corrective_exercises.json 이 유효 JSON 이고 defects 5 키 / painAreas 8 키(=PAIN_AREAS) 정확히 일치
    - 각 defect 의 exercises >= 5, 각 exercise 가 name/setsReps/purpose/sourceRef 보유
    - schemaVersion 박제 (app mirror lockstep 키)
    - sample_force_pattern_inference.json fixture 존재 + findings[] camelCase
    - test_corrective_exercises_fixture.py 그린
  </acceptance_criteria>
  <done>라이브러리 fixture + phase13 test 인프라 박제, 스키마 게이트 통과 (criteria 1).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 순수 map_exercises 매핑 함수 + D-05 비유입 grep 게이트</name>
  <files>backend/shared/python/sunity_shared/analysis/exercise_map.py, backend/tests/phase13/test_map_exercises.py, backend/tests/phase13/test_exercise_map_no_scoring_leak.py</files>
  <read_first>
    - backend/shared/python/sunity_shared/analysis/force_pattern.py L1-110 (pure-fn 모듈 컨벤션 + frozenset 검증 + 모듈 헤더 + from __future__)
    - backend/shared/python/sunity_shared/analysis/force_signals.py L229-235 (lazy repo-root Path + module cache 로더 — backend/data/ 는 parent×5 / "data")
    - .planning/phases/13-llm-coaching-detail/13-RESEARCH.md §"Plan A — Exercise mapping function" + §"Common Pitfalls Pitfall 4"(dedup/cap) + §"Code Examples"(finding dict 키)
    - backend/tests/phase09/test_force_pattern_no_severity_use.py (D-05 grep/AST 게이트 precedent)
  </read_first>
  <behavior>
    - 입력: late_contact finding + painArea ["wrist"] → grip_weak 운동 + wrist painArea 운동이 출력에 포함
    - 출력 길이는 항상 3~5 로 cap, 중복(name) 제거
    - painArea avoid 안전 라인이 우선 정렬됨
    - force_pattern_inference=None + pain_areas=[] → 빈 list (크래시 X)
    - motion_id=None → move-specific gating 없이 generic 결함 운동만 (graceful)
    - 반환 dict 항목은 plain camelCase scalar (name/setsReps/purpose/sourceRef) — dataclass 아님
  </behavior>
  <action>
    `exercise_map.py` 신설. 모듈 헤더 docstring 에 순수성(numpy/AWS-free, Layer 2 boto3 영구 차단) + 3-way lockstep(analysis.ts ↔ models.py ↔ docs/contract.md §4) 박제 + `from __future__ import annotations`. force_signals.py L229-235 패턴으로 `_CORRECTIVE_EXERCISES_PATH`(parent×5 / "data" / "corrective_exercises.json") + `_CORRECTIVE_EXERCISES_CACHE` lazy 로더. signature = `map_exercises(force_pattern_inference: dict | None, pain_areas: list[str], motion_id: str | None) -> list[dict]`. 로직: findings[] 의 `sourceSignal`+`jointHint` 를 defect 키로 join(fixture triggers 매칭), painAreas[] 를 painArea 키로 join. 운동 union 수집 → name 기준 dedup → painArea avoid 안전 항목 우선 정렬 → 3~5 cap. force_pattern.py 스타일 frozenset 검증(_DEFECT_KEYS / PAIN_AREAS reuse) + None/빈 입력 graceful. **D-05 하드월: painAreas 는 매핑 출력에만 흘러가고 어떤 점수/dimension 경로에도 닿지 않음 — 이 함수는 dimension_scores 를 인자로 받지 않는다.**
    `test_map_exercises.py`: behavior 6항목 단위 테스트(<behavior> 미러) + sample fixture 사용.
    `test_exercise_map_no_scoring_leak.py`: AST/grep 게이트 — exercise_map.py 소스에 `dimension_scores`/`absolute_dimension_scores`/`build_dimension_explanation` 토큰 0회(주석 제외 `grep -v '^#' | grep -c`). precedent test_force_pattern_no_severity_use.py.
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/phase13/test_map_exercises.py tests/phase13/test_exercise_map_no_scoring_leak.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - map_exercises 가 3~5 cap + dedup + painArea-avoid 우선 동작
    - None/빈 입력에서 빈 list, 크래시 X
    - 반환 항목 = plain camelCase scalar dict
    - no-scoring-leak 게이트 통과(소스에 채점 토큰 0)
  </acceptance_criteria>
  <done>순수 매핑 함수 + D-05 비유입 게이트 박제 (criteria 2,3).</done>
</task>

<task type="auto">
  <name>Task 3: 3-way 계약 lockstep + firestore validator + pipeline wiring + frontend(전체 라이브러리 모달+섹션) + app data mirror</name>
  <files>app/src/types/analysis.ts, backend/shared/python/sunity_shared/models.py, docs/contract.md, backend/shared/python/sunity_shared/firestore_admin.py, backend/functions/pipeline/app.py, app/src/lib/userAnalyses.ts, app/src/data/correctiveExercises.ts, app/src/components/RecommendedExerciseModal.tsx, app/src/app/analysis/result.tsx, backend/tests/phase13/test_recommended_exercises_lockstep.py, backend/tests/phase13/test_corrective_exercises_app_lockstep.py</files>
  <read_first>
    - app/src/types/analysis.ts L293-327 (AnalysisResult + dimensionExplanation? optional 컨벤션 + L188 CoachingTipDetail interface 모양)
    - docs/contract.md L157-195 (§4 AnalysisResult + DimensionExplanation block 형식)
    - backend/shared/python/sunity_shared/models.py L37-60 (BodyProfile 3-way lockstep 헤더 코멘트 mandate)
    - backend/shared/python/sunity_shared/firestore_admin.py L343-404 (_validate_force_pattern_inference scoped validator) + L727-762 (complete_analysis wiring 블록)
    - backend/functions/pipeline/app.py L1900-1950 (force_pattern_inference_dict build) + L2104-2125 (complete_analysis call) + L1828 (body_profile snapshot read)
    - app/src/lib/userAnalyses.ts (forcePatternInference null-guard — normalize() 패턴) + app/src/components/CoachingTipDetailModal.tsx (전체 — backdrop/gesture 패턴 + theme 토큰)
    - app/src/app/analysis/result.tsx L851-965 (코칭 팁 섹션 + 모달 mount + sectionTitle 패턴 + theme import L60)
    - backend/data/corrective_exercises.json (Task 1 산출 — app mirror 의 single source of truth, schemaVersion 키)
    - backend/tests/test_body_normalization_lockstep.py (TS↔백엔드 data drift 방어 lockstep precedent — repo-root Path 해석 + 필드 매핑 검증 패턴)
  </read_first>
  <action>
    **단일 atomic commit 으로 3-way 계약**: (1) analysis.ts — `RecommendedExercise` interface(name/setsReps/purpose/sourceRef? — CoachingTipDetail 모양 + Phase 13 코멘트) + AnalysisResult 에 `recommendedExercises?: RecommendedExercise[]`(dimensionExplanation? optional 패턴, 이전 빌드 doc 호환). (2) models.py — BodyProfile lockstep 헤더 컨벤션대로 `recommendedExercises` 계약 코멘트 추가(생산자=exercise_map, 검증=firestore_admin, static fixture 이므로 normalizer 불필요 박제). (3) docs/contract.md §4 — `recommendedExercises RecommendedExercise[] optional ← Phase 13` 라인 + DimensionExplanation block 모델로 RecommendedExercise shape block. camelCase Firestore / 본 리스트는 plain camelCase dict 라 `_dataclass_to_camel_case_dict` 우회 박제.
    firestore_admin.py: `_validate_recommended_exercises(payload, *, path="recommendedExercises")` 신설 — _validate_force_pattern_inference 1:1 mirror. None graceful, list 아니면 reject, len > 5 reject(criteria 2 cap), 각 item 에 `_validate_dict_only_scalars`(flat scalar — _validate_dict_only_scalars 본체 변경 0). complete_analysis 에 `recommended_exercises=None` kwarg 추가 + force_pattern_inference 블록 mirror 로 검증 후 `payload["result"]["recommendedExercises"]` 할당.
    pipeline app.py: L1948 force_pattern_inference_dict build 직후 `recommended_exercises = exercise_map.map_exercises(force_pattern_inference_dict, pain_areas=(models.normalize_body_profile(meta.get("bodyProfile")) or {}).get("painAreas", []) or [], motion_id=getattr(profile, "motion_id", None))` 호출(exercise_map import 추가). complete_analysis(L2104) 에 `recommended_exercises=recommended_exercises` kwarg 전달. **painAreas 만 소비, weightKg 점수 경로 진입 0 (D-05).**
    **HIGH-1 옵션 (a) app data path: `app/src/data/correctiveExercises.ts` 신설** — backend/data/corrective_exercises.json 의 schema/version/content 를 manual mirror(`export const CORRECTIVE_EXERCISES`). `schemaVersion`(백엔드와 동일 문자열) + `defects`/`painAreas` 전체 운동 목록을 typed export(RecommendedExercise[] 호환 shape). 모달이 result.recommendedExercises(3~5 subset)이 아니라 본 풀 라이브러리를 browse 하는 single source.
    userAnalyses.ts: normalize() 에 forcePatternInference null-guard mirror — `if (Array.isArray(result?.recommendedExercises)) normalizedResult.recommendedExercises = result.recommendedExercises`.
    `RecommendedExerciseModal.tsx` 신설: CoachingTipDetailModal.tsx 전체 scaffold mirror(Modal transparent + animationType="slide", backdrop pure View + backdropTop Pressable tap=close, sheet useWindowDimensions height, ScrollView). **내용 = app/src/data/correctiveExercises.ts 의 전체 라이브러리 운동 카드 목록(causeCard 패턴) — Firestore subset 이 아닌 풀 라이브러리 browse (criteria 4, HIGH-1).** theme 토큰만(colors.brand #FF4B33 / colors.divider / radius.card / radius.button) — 하드코딩 금지, 라이트 테마.
    result.tsx: "코칭 팁" 섹션(L854-917) 뒤, `</ScrollView>`(L933) 전에 "보완 운동" 섹션 추가 — sectionTitle "보완 운동" + result.recommendedExercises 카드 목록(개인화 3~5 subset) + "다른 운동 보기" Pressable(L905 tipMore 패턴). `const [exerciseModalOpen, setExerciseModalOpen] = useState(false)` 추가(detailTip 패턴) + 기존 모달 mount 옆에 `<RecommendedExerciseModal visible={exerciseModalOpen} onClose={() => setExerciseModalOpen(false)} />` mount. recommendedExercises 부재/빈 배열이면 카드 섹션 graceful 숨김(단 "다른 운동 보기" 모달은 풀 라이브러리이므로 항상 동작).
    `test_recommended_exercises_lockstep.py`: complete_analysis(recommended_exercises=[...]) → result.recommendedExercises 저장 검증 + validator 가 len>5 / nested-array reject 검증.
    **`test_corrective_exercises_app_lockstep.py`(신규, HIGH-1): backend/data/corrective_exercises.json ↔ app/src/data/correctiveExercises.ts schema/version/content lockstep** — test_body_normalization_lockstep.py 패턴으로 repo-root Path 해석, (1) 양쪽 schemaVersion 문자열 동일, (2) defects 5 키 / painAreas 8 키 동일 집합, (3) 운동 name 전체 집합이 양쪽 1:1 일치(content drift 0). 3-way contract drift test precedent 준수.
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/phase13/test_recommended_exercises_lockstep.py tests/phase13/test_corrective_exercises_app_lockstep.py -x -q && cd ../app && npm run typecheck</automated>
  </verify>
  <acceptance_criteria>
    - analysis.ts + models.py + docs/contract.md §4 가 recommendedExercises 를 동시 박제(3-way)
    - _validate_recommended_exercises 가 len>5 + nested-array reject, complete_analysis kwarg 동작
    - pipeline 이 map_exercises 호출 + complete_analysis 에 전달(painAreas만, weightKg 점수경로 0)
    - app/src/data/correctiveExercises.ts 존재 + 백엔드 fixture 와 schema/version/content lockstep (HIGH-1)
    - RecommendedExerciseModal 이 correctiveExercises.ts 풀 라이브러리를 read (result.recommendedExercises subset 아님)
    - result.tsx 에 "보완 운동" 섹션 + RecommendedExerciseModal mount, theme 토큰만 사용
    - test_recommended_exercises_lockstep.py + test_corrective_exercises_app_lockstep.py 그린 + tsc --noEmit clean
  </acceptance_criteria>
  <done>계약+검증+wiring+UI vertical slice 완성 — 결과 화면에 개인화 보완 운동 카드 + 전체 라이브러리 "다른 운동 보기" 모달 (criteria 4, HIGH-1 옵션 a).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client(BodyProfile.painAreas self-input) → pipeline | 자가입력 통증부위가 분석 doc snapshot 으로 백엔드에 흐름 |
| pipeline → Firestore (recommendedExercises write) | 매핑 결과 list[dict] 가 Firestore result 에 기록 |
| static fixture (corrective_exercises.json) → map_exercises | 커밋된 큐레이션 content (per-user write 없음) |
| backend fixture → app/src/data/correctiveExercises.ts mirror | 빌드타임 박제 mirror — runtime 백엔드 read 없음, lockstep test 가 drift 방어 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-13A-01 | Tampering (analysis integrity) | exercise_map painAreas 소비 | mitigate | painAreas 는 매핑 출력에만 — map_exercises 가 dimension_scores 미수신 + test_exercise_map_no_scoring_leak.py grep 게이트 (D-05) |
| T-13A-02 | Tampering/DoS | firestore recommendedExercises write | mitigate | scoped `_validate_recommended_exercises` 화이트리스트 + len<=5 cap, _validate_dict_only_scalars 본체 불변 (nested-array ban 보존) |
| T-13A-03 | Information Disclosure / 의료 단정 | 운동 content 카피 | accept | content 는 NotebookLM 큐레이션 운동명/세트수만, 의학적 진단·치료 단정 없음 (D-05 / objectivity). painArea avoid 는 일반 안전 라인 |
| T-13A-04 | Tampering | client 위조 painAreas | mitigate | models.normalize_body_profile 가 PAIN_AREAS frozenset 멤버만 통과 (비멤버 drop) |
| T-13A-05 | Tampering (content drift) | app mirror correctiveExercises.ts 가 backend fixture 와 어긋남 | mitigate | test_corrective_exercises_app_lockstep.py 가 schemaVersion/키/운동명 1:1 강제 (HIGH-1) |
</threat_model>

<verification>
- `cd backend && python -m pytest tests/phase13 -q` (Plan A 전 테스트 그린)
- `cd backend && python -m pytest -q` (회귀 0 — phase06/07/08/08.1/09 그린 유지)
- `cd app && npm run typecheck` (tsc --noEmit clean)
- grep: exercise_map.py 소스에 채점 토큰 0 (D-05)
- app/src/data/correctiveExercises.ts ↔ backend/data/corrective_exercises.json lockstep (HIGH-1)
</verification>

<success_criteria>
- corrective_exercises.json fixture 박제(5 defect + 8 painArea) — criteria 1
- map_exercises 가 분석당 3~5 운동 산출 — criteria 2
- 매핑 입력 = findings + painAreas + motion_id — criteria 3
- result.tsx 보완 운동 섹션 + "다른 운동 보기" 전체 라이브러리 모달(app data mirror) — criteria 4
- D-05 비유입 게이트 + app lockstep + 회귀 0
</success_criteria>

<output>
Create `.planning/phases/13-llm-coaching-detail/13-A-SUMMARY.md` when done
</output>
</content>
</invoke>
