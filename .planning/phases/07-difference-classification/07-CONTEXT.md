# Phase 7: 차이 분류 - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 가 산출한 `BodyComparisonReport.findings[]` (5 IPSF GeometricCriterion deficit + Sunity pose_reliability_low) 를 입력으로 받아, 각 finding 을 **`body_type_allowed` / `needs_adjustment` / `uncertain`** 으로 자동 분류하고, 결과 화면 카피 2개 박스 (`doNotOverCorrect` / `recommendedFocus`) 를 백엔드 캔드 템플릿으로 박제하는 **분류·카피 layer**.

본 phase 가 산출 (output 본체):
- `BodyComparisonFinding` 에 `category` 필드 추가 (3 enum) — Phase 6 dataclass 확장
- `BodyComparisonFinding` 에 `phase` 필드 추가 (nullable, default `'hold'`) — v2 단계 분할 확장 포인트 박제
- `BodyComparisonReport` 에 `doNotOverCorrect: list[str]` / `recommendedFocus: list[str]` 두 배열 추가
- `BodyComparisonReport` 에 `bodyTypeInterpretation` / `recommendation` Korean canned string (per-finding) 또는 두 배열 통합 — researcher 결정 (캔드 매핑 테이블 구조 박제 단계에서)
- 결과 카피 톤 룰 박제 (금지 6종 + 권장 4종 + memory 박제 3 가지 추가) — research §10.1/§10.3 + Sunity 추가

본 phase 가 산출 X (downstream / 다른 phase 영역):
- `BodyComparisonReport` 출력 자체 (Phase 6 lock)
- 단계별 phase 분할 (entry/lock/transition/final_shape/hold) — Phase 8 또는 Plan 13 (Gemini key_moments) 박제 책임. Phase 7 v1 = `'hold'` 단일.
- LLM 동적 카피 생성 — Phase 11 (CoachCommentHook + Cerebras coach_writer)
- 보완 운동 매핑 — Phase 13
- 영상 위 오버레이 좌표 그리기 — Phase 12

</domain>

<decisions>
## Implementation Decisions

### (A) 분류 룰 — allowed / needs_adjustment / uncertain 결정 기준

- **D-07-A1:** **`body_type_adjusted` 플래그 + `deduction_score` 크기 조합 룰**.
  - `body_type_adjusted=True` (정규화 좌표 측정) + `abs(deduction_score) ≤ 0.2` → **`body_type_allowed`** (작은 차이 = 체형 영향 가능)
  - `body_type_adjusted=True` + `abs(deduction_score) > 0.2` (= 0.5, pose_reliability_low 등) → **`needs_adjustment`** (보정 후에도 남은 큰 차이)
  - `body_type_adjusted=False` (raw 좌표 측정) → **항상 `uncertain`** (정규화 안 됐으면 키 차이 섞여있어 신뢰 X)
- **D-07-A2:** uncertain 임계 = **Phase 6 D-06-U1 0.5 게이트 재사용**.
  - `report.bodyNormalizationConfidence < 0.5` → 모든 finding 의 category 를 `uncertain` 으로 강제 demotion
  - `finding.confidence < 0.5` → 해당 finding 개별 `uncertain` demotion
  - 두 게이트 동시 적용 (OR 합집합)
- **D-07-A3:** **`needs_adjustment` 분류가 빈 리스트 위험** — Phase 6 의 5 IPSF deficit 들은 대부분 정규화 좌표에서 측정되므로 `body_type_adjusted=True` 가 기본. deduction = -0.2 인 deficit 이 많으면 `allowed` 가 과다 될 수 있음. researcher 가 5 영상 sweep (`sweep_rtmw_20260603_1409` + 정은지 mode1) 데이터에서 deduction 분포를 측정해 임계 0.2 가 적정한지 검증. 0.2 가 너무 관대하면 0.3 / 0.4 로 조정 — researcher 영역.

### (B) 결과 카피 출처 — 백엔드 캔드 템플릿 + Claude 작성 + belle 검수

- **D-07-B1:** **백엔드 캔드 템플릿** 박제. `BodyComparisonReport` 안에 `doNotOverCorrect: list[str]` + `recommendedFocus: list[str]` 두 배열 명시 출력. 백엔드가 `(deficit_code, category, joint_key)` 조합으로 Korean canned string 박제 (mapping table). 객관성 확보 + Cerebras 의존 X + Phase 11 에서 나중 LLM 풍부화 가능 (강사 보조 layer).
- **D-07-B2:** **카피 작성 주체** = Claude 가 research §10.1 4 예문 직접 박제 + 나머지 deficit_code × category × joint_key 조합 동일 톤 확장. belle 가 plan 단계에서 검수. 작성 후 5 IPSF × 3 category 조합 (15 카피) + pose_reliability_low × 3 (3 카피) = 약 18 카피 박제 예상.
- **D-07-B3:** **카피 분배 룰** = `body_type_allowed` → `doNotOverCorrect[]`, `needs_adjustment` → `recommendedFocus[]`, `uncertain` → 별도 카피 출력 또는 화면 분리 (researcher / planner 가 schema 박제 시 결정 — uncertain 박스 별도 박제 vs recommendedFocus 안에 "강사 확인 권유" 톤 박제 후보).

### (C) 동작 단계 분할 — v1 단순화

- **D-07-C1:** **v1 = 단일 `'hold'` moment**. `BodyComparisonFinding` 에 `phase` 필드 추가, nullable, 기본값 `'hold'`. 5 IPSF deficit + pose_reliability_low 모두 `phase='hold'` 로 v1 박제. Phase 8 (force pattern, phase 별 산출 박제) 또는 Plan 13 (Gemini key_moments) 통합 시점에 다수 phase 자연 확장 (entry/peak/setup/release 등) — TS/Python contract 변경 X (필드 그대로 활용).

### (D) 카피 톤 + 금지/권장 표현 룰

- **D-07-D1:** **research §10.1 권장 4종 + §10.3 금지 6종 박제** + Sunity 추가 3종 룰:
  - **(a) 가능성 언어** — 단정 ("~다", "~합니다") → 가능성 ("~로 보입니다", "~일 가능성이 있어요", "~로 보이네요"). memory `[[analysis-objectivity-no-human-scores]]` 정합.
  - **(b) AI = 강사 보조 도구 톤** — "AI 가 정확히 분석했어요" → "AI 분석 결과예요. 강사와 함께 확인 권유". memory `[[feedback-no-echo-confirm]]` 정합. Phase 11 (FEED-03) 박제 미리 정합.
  - **(c) 부위별 원인 언어 (수치 단독 X)** — "각도 87° 차이" → "고관절 안정성이 필요해 보이네요" / "코어 컨트롤이 약해 보입니다". 부위 키워드: 고관절·후굴·코어·내전근·전완근·광배·흉곽·골반·견갑 등. research 박제 (P0 수강생/강사 설문조사) + memory `[[feedback-analysis-first]]` 정합.
- **D-07-D2:** **금지 표현 6종 grep gate** — 백엔드 canned string mapping table 박제 후 단위 test 에서 6종 금지 표현 (`프로보다 못합니다` / `정답 자세가 아닙니다` / `근육량이 부족합니다` / `체형이 안 맞습니다` / `대회 총점` / `다리 각도.*감점입니다`) grep 검증. 회귀 차단.
- **D-07-D3:** **mode 분기 (mode1 vs mode3 first vs mode3 progress) 카피 톤** — Phase 12.5 의 `dimensionExplanation` 이 이미 mode 분기 박제. Phase 7 카피도 `comparisonType` 으로 분기 — 예: `mode1` "정은지 선수 기준" vs `mode3_first` "Page 9 절대 기준" vs `mode3_progress` "이전 영상 대비". 카피 mapping table 의 키에 comparisonType 포함.

### Universal Principle (Phase 7 전반)

- **D-07-U1:** **confidence-tiered 정합 (Phase 6 D-06-U1 재사용)**. 0.5 게이트 단일 박제 — Phase 6 와 동일 임계. 별도 임계 도입 X (일관성). researcher / planner 는 본 원칙 단일 게이트로 박제.

### Claude's Discretion

- **canned string mapping table 의 정확한 18 카피 본문 작성** — Claude 가 research §10.1 톤 박제 + 5 deficit × 3 category × mode 분기 조합 카피 초안 박제. plan 단계에서 belle 검수. 출력 형식 (yaml / Python dict / Firestore doc) 은 planner 결정.
- **uncertain 화면 표시 방식** — `recommendedFocus[]` 안에 "AI 확신 부족, 강사 확인 권유" 톤으로 통합 vs 별도 `uncertainFindings[]` 배열 신설. researcher / planner 가 frontend Phase 12 와 책임 경계 박제 시 결정. Phase 7 v1 은 백엔드 출력만, 화면 노출은 후속 phase.
- **deduction 임계 0.2 의 정확도 검증** — researcher 가 영상 데이터 sweep 으로 임계 0.2 / 0.3 / 0.4 비교 후 박제. 가설: 0.2 가 IPSF Page 21 표준 감점 단위에 정합 (-0.2 단계 감점).
- **카피 매핑 키 (deficit_code × category × joint_key × comparisonType) 의 정확한 차원** — joint_key 가 결합되면 5 × 3 × 17 × 3 = 765 카피 폭발. joint_key 는 부위 그룹 (arm / leg / torso) 으로 축소 후 매핑 — researcher / planner 박제.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 7 본 phase 산출 / contract

- `.planning/ROADMAP.md` §Phase 7 — goal + 4 success criteria + deps (Phase 6)
- `.planning/REQUIREMENTS.md` PERS-01 — 체형 정규화 비교 엔진 (Phase 6, Phase 7 공유) — 차이 분류는 Phase 7 책임
- `app/src/types/analysis.ts` §`BodyComparisonReport` / `BodyComparisonFinding` — TS contract 확장 (category / phase / doNotOverCorrect / recommendedFocus 추가)
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py` — Python 미러 (`BodyComparisonFinding` / `BodyComparisonReport` dataclass)
- `backend/shared/python/sunity_shared/models.py` — Python re-export contract
- `docs/contract.md` §8 + §8.1 — BodyComparisonReport 명세 (Phase 7 확장 필요)

### Phase 6 박제 (upstream)

- `.planning/phases/06-coaching/06-CONTEXT.md` — 통합 schema + 3 ComparisonType + D-06-U1 confidence-tiered hybrid 박제
- `.planning/phases/06-coaching/06-RESEARCH.md` — 5 IPSF GeometricCriterion + pose_reliability_low + body_type_adjusted 박제
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:773-895` — `BodyComparisonFinding` + `BodyComparisonReport` dataclass 본체
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:901-1110` — `measure_ipsf_absolute_deficits` (5 IPSF + pose_reliability_low 산식)
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:1120-1280` — `compare_body_profiles` (정규화 + finding 출력)

### Phase 5 박제 (upstream — Gemini 인식)

- `.planning/phases/05-gemini/05-CONTEXT.md` — Gemini motion_id + EXTEND/BENT 박제
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` — TechniqueProfile (motion_id + expects_extension)
- `backend/shared/python/sunity_shared/analysis/technique.py` — TechniqueProfile dataclass

### Phase 12.5 박제 (downstream 패턴 참조)

- `.planning/phases/12_5-ui-transparency/12.5-CONTEXT.md` — `dimensionExplanation` mode 분기 + weight % + deficit summary
- `backend/shared/python/sunity_shared/analysis/assemble.py::build_dimension_explanation` — Phase 7 의 canned string 박제 패턴 참조 (mode-aware baseline + Largest Remainder)

### IPSF + 도메인 박제 + 카피 룰

- `docs/research/01_체형차이_보정엔진_FINAL.md` §9 — `BodyComparisonReport` schema 박제 (category enum, doNotOverCorrect/recommendedFocus 출처)
- `docs/research/01_체형차이_보정엔진_FINAL.md` §10.1 — 권장 카피 4 예문 (Claude 초안 작성 source)
- `docs/research/01_체형차이_보정엔진_FINAL.md` §10.3 — 금지 카피 6종 (grep gate test source)
- `docs/research/폴스포츠-지식.md` — 도메인 박제 (부위별 원인 언어 어휘)
- `docs/research/폴스포츠 수강생의 설문조사.md` — P0 강사 철학 "수치보다 원인" + AI 보조 도구 포지셔닝
- `.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md` — IPSF 5트랙 v1 scope (Page 9 절대 트랙) — mode3 first uncertain 처리 정합 참고

### Downstream (Phase 7 출력 소비)

- ROADMAP §Phase 11 (CoachCommentHook + Cerebras 자연어 번역) — Phase 7 의 canned string 을 Phase 11 이 LLM 풍부화 + CoachCommentHook 의 `autoFindingsSummary` 에 통합
- ROADMAP §Phase 12 (실측 각도 + 키포인트 오버레이) — Phase 7 category 별 finding 을 화면 분기 (allowed → 회색 / needs → 강조 / uncertain → "강사 확인" 톤)
- ROADMAP §Phase 13 (보완 운동 + LLM 분기 카피) — Phase 7 의 needs_adjustment finding 을 보완 운동 매핑 input 으로 사용

### 박제 메모리 (정합 필수)

- `[[scoring-dimensions-ipsf]]` — IPSF 절대 기준, 사람 점수 라벨링 X
- `[[mode3-progress-not-similarity]]` — mode3 = 절대 지표 델타, % 일치 헤드라인 X
- `[[ipsf-5-track-scoring]]` — Page 9 절대 트랙 (uncertain 처리 시 fallback path)
- `[[feedback-analysis-first]]` — 분석 정확도 우선, 가능성 언어
- `[[mvp-simple-pilot-quality]]` — 단순 fallback + 점진 정밀화 (캔드 우선 박제 근거)
- `[[analysis-objectivity-no-human-scores]]` — 사람 점수 라벨링 영구 X, 캔드 카피 객관성 박제
- `[[feedback-no-echo-confirm]]` — AI = 강사 보조 도구 톤
- `[[no-baekje-filler]]` — 카피 작성 시 박제 단어 남용 X (단조로움 + 의미 모호)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`backend/shared/python/sunity_shared/analysis/body_normalizer.py::BodyComparisonFinding`** — Phase 6 lock. Phase 7 = 본 dataclass 에 `category: Literal["body_type_allowed", "needs_adjustment", "uncertain"]` + `phase: str | None = "hold"` + (선택) `body_type_interpretation: str | None` + `recommendation: str | None` 필드 추가 (frozen dataclass 확장).
- **`backend/shared/python/sunity_shared/analysis/body_normalizer.py::BodyComparisonReport`** — Phase 6 lock. Phase 7 = `do_not_over_correct: list[str]` + `recommended_focus: list[str]` 두 필드 추가.
- **`backend/shared/python/sunity_shared/analysis/body_normalizer.py::measure_ipsf_absolute_deficits`** (line 901+) — Phase 6 박제. Phase 7 = 본 함수 출력 (list[BodyComparisonFinding]) 을 받아 분류 + 카피 박제하는 별도 함수 (`classify_findings(findings, body_normalization_confidence)`) 신설.
- **`backend/shared/python/sunity_shared/analysis/body_normalizer.py::compare_body_profiles`** (line 1120+) — Phase 6 박제. Phase 7 = 본 함수 안에서 `classify_findings` 호출 + `do_not_over_correct` / `recommended_focus` 박제 + Report 에 주입.
- **`backend/shared/python/sunity_shared/analysis/assemble.py::build_dimension_explanation`** — Phase 12.5 박제. Phase 7 canned string mapping 의 mode 분기 패턴 참조.
- **`backend/shared/python/sunity_shared/firestore_admin.py::complete_analysis`** — Phase 6 박제. Phase 7 신설 필드 (category / phase / do_not_over_correct / recommended_focus) 가 Firestore AnalysisDoc 의 `bodyComparisonReport` 안에 자동 포함되도록 `_dataclass_to_camel_case_dict` 박제 정합 (Phase 6 C8 박제 — None/dataclass/list/dict/Enum/scalar 5 case 명시).
- **`app/src/types/analysis.ts::BodyComparisonReport`** — TS contract. Phase 7 = `doNotOverCorrect: string[]` / `recommendedFocus: string[]` 필드 + `BodyComparisonFinding.category` / `BodyComparisonFinding.phase` 필드 추가.
- **`app/src/lib/userAnalyses.ts::normalize`** — Firestore raw → AnalysisDoc 정규화. Phase 7 = 신설 필드 normalize 확장.

### Established Patterns

- **3-way contract lockstep** — `analysis.ts` ↔ `models.py` (re-export) ↔ `docs/contract.md` §8 동시 갱신 (CLAUDE.md Cross-cutting). Phase 7 의 schema 확장은 단일 atomic commit 으로 박제 (Phase 6 박제 패턴 정합).
- **Frozen dataclass + `__post_init__` validator** — `BodyComparisonFinding` / `BodyComparisonReport` 가 박제 패턴. Phase 7 신설 필드도 validator 추가 (category enum 3종 + phase nullable + 18 canned string mapping table 검증).
- **camelCase 변환** — `_dataclass_to_camel_case_dict` 박제 (Phase 6 C8). Phase 7 의 `do_not_over_correct` → `doNotOverCorrect` / `recommended_focus` → `recommendedFocus` 자동 변환.
- **Singleton adapters / lazy import** — Phase 7 의 canned string mapping table 은 stateless dict literal 박제 (singleton 불요). 모듈 import 시 1회 로드.
- **Pure functions + numpy only** — Phase 7 분류 함수 `classify_findings` 도 순수 함수 (boto3 / 네트워크 / LLM 무관). 단위 test 가능.
- **Firestore nested-array 금지** — `do_not_over_correct: list[str]` / `recommended_focus: list[str]` 는 flat list[str] 박제 (Firestore safe). `findings: list[dict-of-scalars-only]` 도 Phase 6 W5 박제 (`_validate_dict_only_scalars`) 정합.

### Integration Points

- **`pipeline/app.py::_process`** — Phase 6 박제. Phase 7 은 별도 wiring 불요 (Phase 6 `compare_body_profiles` 안에 분류 + 카피 박제 통합). pipeline 의 mode1 / mode3 분기는 그대로.
- **`firestore_admin.complete_analysis`** — Phase 7 신설 필드 자동 저장 (Phase 6 박제 정합).
- **`app/src/components/result.tsx` (또는 후속 컴포넌트)** — Phase 12 / 12.5 가 본 출력 소비. category 별 화면 분기 + 두 박스 (`doNotOverCorrect` / `recommendedFocus`) UI 박제.
- **canned string mapping table 박제 위치** — `backend/shared/python/sunity_shared/analysis/copy_templates.py` (신규 모듈) 권장. dict literal + (deficit_code, category, joint_group, comparisonType) → str. 단위 test = mapping table grep gate (D-07-D2).

</code_context>

<specifics>
## Specific Ideas

- **belle 의문 박제 (2026-06-08)**: "체형 보정해도 남는 진짜 차이" 의미 박제 완료 — `body_type_adjusted=True` (정규화 좌표) 에서 deduction 발생 = 키 차이 뺀 상태에서도 차이 남 = 진짜 자세 차이. canonical 정의 박제.
- **사용자 피로감 시나리오** (belle 박제 정신 정합): 0.5 임계 박제 — 평범한 스튜디오 영상에서 uncertain 비율 1/6 수준. 0.7 임계는 절반 uncertain 가능성 (피로감). 단 belle 박제 정신 = "분석 정확도 우선" 이므로 uncertain 노출은 명확한 카피로 정직성 박제 ("이 부분은 가림/회전으로 AI 가 확신 못 했어요").
- **카피 작성 주체** — Claude 가 research §10.1 박제 + 톤 정합 확장, belle 가 plan 단계 검수. 18 카피 (5 IPSF × 3 category + pose_reliability_low × 3) 박제 예상. plan 단계에서 본 카피 mapping 박제 완료 후 belle 1회 검수 후 진행.
- **금지 표현 grep gate** — Phase 7 박제의 단위 test 가 백엔드 canned string + Firestore output 양쪽에서 6종 금지 표현 grep 검증. 회귀 차단 박제.
- **단계 분할 v2 자연 확장 path** — Phase 7 v1 `phase='hold'` 박제 + Phase 8 또는 Plan 13 (Gemini key_moments) 통합 시 multi-phase finding 박제. 현재 schema 박제 시 v2 확장 호환 박제.

</specifics>

<deferred>
## Deferred Ideas

- **동작 단계 (entry/lock/transition/final_shape/hold) v2 확장** — Phase 8 또는 Plan 13 (Gemini key_moments) 통합 시 박제. Phase 7 v1 schema 박제는 v2 호환 (phase 필드 nullable string).
- **카피 LLM 풍부화** — Phase 11 (CoachCommentHook + Cerebras coach_writer) 책임. Phase 7 캔드 박제 후 Phase 11 이 LLM 으로 동적 풍부화 (강사 보조 layer).
- **joint_key 부위 그룹화 mapping 정확도** — researcher / planner 가 5 IPSF deficit × 17 joint 조합 → arm / leg / torso 등 부위 그룹 매핑 박제 후 sweep 데이터로 검증.
- **deduction 임계 0.2 의 5 영상 sweep 검증** — researcher 영역. 0.2 가 너무 관대하면 0.3 / 0.4 로 조정 (sweep_rtmw_20260603_1409 + 정은지 mode1 데이터 활용).
- **mode3_first Page 9 단독 분류** — mode3 first + Gemini fallback X 케이스에서 finding 분류 룰 박제. Phase 6 D-06-B1 박제 (Page 9 절대 트랙 단독) 정합. researcher 가 mode 분기 시 분류 룰 변형 박제.
- **uncertain 박스 별도 표시 vs recommendedFocus 통합** — frontend 화면 박제. Phase 7 v1 schema = 분리 가능 (`uncertain_findings` 별도 배열 신설 가능) + 통합 가능 (recommendedFocus 안에 "강사 확인 권유" 톤). Phase 12 와 책임 경계 박제.
- **categoryByPhase aggregate (v2)** — research §9 의 `keyFindings` 외 phase × category cross-tabulation summary 출력 (v2 확장).
- **CoachCommentHook 의 openQuestionsForCoach 자동 populate** — Phase 11 책임. uncertain finding 이 자동으로 openQuestionsForCoach[] 에 박제되는 wiring (Phase 7 → Phase 11).

</deferred>

---

*Phase: 7-difference-classification*
*Context gathered: 2026-06-08*
