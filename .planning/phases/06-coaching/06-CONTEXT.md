# Phase 6: 체형 정규화 비교 엔진 (coaching 모드) - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

프로 (정은지) 의 동작 성공 원리를 수강생의 신체 비율에 맞게 재계산해 비교하는 엔진. **북극성 use case** — **160cm 프로 reference + 140cm 수강생 영상 → 체형 위양성 없이 자세 품질만 측정**.

본 phase 가 산출 (output 본체):
- 점수 차원별 deficit 의 체형 보정 (정은지 41점 같은 위양성 제거)
- 세그먼트별 scale ratio 메타 (Phase 12 오버레이가 좌표 reproject 에 소비)
- `BodyComparisonReport` 통합 schema + `comparisonType` field (mode1 / mode3_first / mode3_progress 3 케이스 통합)
- `bodyNormalizationConfidence` (success #4 박제 — coaching 모드에서 항상 출력)

본 phase 가 산출 X (downstream / 다른 phase 영역):
- 키포인트 좌표 자체의 reproject 결과 그리기 (Phase 12 오버레이 책임)
- 차이의 분류 ("체형 허용" / "개선 필요" / "uncertain") — Phase 7
- 보완 운동 매핑 — Phase 13
- 정은지 영상 자체의 BodyProfile 측정 + 다각도 캡처 — Phase 14

</domain>

<decisions>
## Implementation Decisions

### (A) 정규화 대상 — 좌표 재투영 vs 점수 보정

- **D-06-A1:** Phase 6 출력의 본체 = **점수 보정 + scale ratio 메타 둘 다 출력**. Phase 6 본체는 점수 정확성 (체형 위양성 제거) 에 집중하고, scale ratio 메타 (5 필드) 를 별도 출력해서 Phase 12 오버레이가 메타를 소비해 좌표 reproject 별도 수행. 책임 분리.
- **D-06-A2:** 좌표 변환 방향 = **B (프로 reference → 수강생 체형 좌표계)**. 의미 — 정은지의 키포인트를 "정은지가 수강생 키였다면 어디 있어야 할지" 로 reproject. Phase 12 오버레이 = 사용자 영상 위에 "내 키로 환산된 정은지 자세" 표시 → "여기로 가세요" 직관. 함수 이름 `normalizeStudentPoseToProReference` 는 "수강생 자세를 프로 reference 와 같은 평가 기준으로" 라는 의미지 변환 방향이 아님 (둘은 수학적 동치, 시각화만 다름).
- **D-06-A3:** 세그먼트별 정규화 적용 단위 = **5 필드 모두 + 하이브리드 게이트**. estimatedHeightScale + armScale + legScale + torsoScale + shoulderHipRatio 모두 활용. 단:
  - `shoulderHipRatio` (좌우 폭 비율) 는 **키포인트 reproject 에만 적용** (Phase 12 시각화 메타)
  - **점수 차원에는 미적용** — 메모리 [[scoring-dimensions-ipsf]] 박제 (좌우 비대칭 = 폴 동작의 의도적 비대칭, 감점 차원 제거 박제) 유지
  - `shoulderHipRatio` confidence 낮으면 폭 보정 자동 OFF (상하만 적용)
- **D-06-A4:** OFF 분기 = **mode + confidence 병행 게이트**. coaching 모드 + confidence ≥ 0.5 → 정규화 ON. confidence < 0.5 또는 judging 모드 (v1.5) → 정규화 OFF + warning 카피 "체형 측정 불충분, raw 비교 박제". judging 모드 plumbing 은 v1 에 박제 (mode flag 도입), 실제 활용은 v1.5.

### (B) mode1 / mode3 first / mode3 second+ 3 케이스 분기

- **D-06-B1:** **mode3 first (수강생 첫 분석, 이전 영상 X)** = **Page 9 절대 트랙 단독 (기본)** + **confidence 높음 + Gemini motion 인식 성공 시 자동 매칭 reference fallback** (체형 정규화 ON 으로 추가 비교 차원 제공). 메모리 [[ipsf-5-track-scoring]] 정합 — reference 없이도 IPSF Page 9 'all components' 절대 트랙으로 자세 품질 채점. fallback 비교 UI 는 "참고용" 으로 명시 (강제 비교 X, [[mode3-progress-not-similarity]] 박제 유지).
- **D-06-B2:** **mode1 정은지 reference BodyProfile 박제 위치** = **`reference-motions` 컬렉션에 BodyProfile 필드 추가**. Phase 14 정은지 reference 등록 시 `measure_body_profile` 호출 → `bodyNormalizationProfile` 동시 저장. Phase 6 시점 = 현재 등록된 reference 에 일회 측정 fixture 로 백필. contract (TS / Python / docs/contract.md) 의 reference-motion 타입에 `bodyNormalizationProfile` nullable 필드 추가.
- **D-06-B3:** **출력 schema** = **통합 `BodyComparisonReport` + `comparisonType` field**. 같은 dataclass 안에 `comparisonType: 'mode1' | 'mode3_first' | 'mode3_progress'` 구분 필드. 케이스별 없는 필드는 nullable. downstream (Phase 7 차이 분류 / Phase 12 오버레이 / Phase 13 보완 운동) 가 `comparisonType` 으로 UI / 로직 분기 — Phase 12.5 의 `dimensionExplanation` mode 분기 패턴과 동일. contract 3-way lockstep 단일 조작.

### Universal Principle (Phase 6 전반)

- **D-06-U1:** **confidence-tiered hybrid** (belle 2026-06-08 박제). Phase 6 전반에 적용:
  - **confidence 낮음** (< 0.5) → 안전 fallback (raw 비교, 단정 차단, 정규화 OFF + warning, mode3 first 도 Page 9 단독)
  - **confidence 높음** (≥ 0.5) → 분석 가능한 모든 path 활성화 (5 필드 정규화 + 매칭 reference fallback + 모든 차원 출력)
  - 메모리 [[feedback-analysis-first]] (분석 가능한 만큼 정확히) + [[mvp-simple-pilot-quality]] (단순 fallback) 동시 정합
  - **D-06-A3 / D-06-A4 / D-06-B1 모두 본 원칙의 구체화** — researcher / planner 는 본 원칙을 단일 게이트로 박제할 것

### Claude's Discretion

- 점수 보정 산식 magnitude (체형 차이 ratio 가 deficit 점수에 미치는 영향 크기) — researcher 가 영상 데이터 분석 후 결정. 단 **메모리 [[scoring-dimensions-ipsf]] (좌우 대칭 감점 X) + [[analysis-objectivity-no-human-scores]] (사람 점수 라벨링 영구 금지) 박제 유지**.
- 세그먼트별 정규화 알고리즘 (`normalizeByBodySegments`) 의 수학적 정의 — researcher 가 reference paper (HumanPoseNormalizer / NLF body fitting 등 비상업 R&D 평가 포함) 조사 후 박제.
- `bodyNormalizationConfidence` UI 노출 방식 — Phase 12 / 12.5 와 협업 영역. Phase 6 는 데이터 출력만 책임, UI 노출은 후속 phase.
- `shoulderHipRatio` confidence 임계값 (폭 보정 자동 OFF threshold) 의 정확한 수치 — researcher 가 belle Pod 5영상 sweep 데이터로 결정.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 6 본 phase 산출 / contract

- `.planning/ROADMAP.md` §Phase 6 — Phase 6 goal + 4 success criteria + deps (Phase 2, Phase 5)
- `.planning/REQUIREMENTS.md` PERS-01 — 체형 정규화 비교 엔진 요구사항
- `app/src/types/analysis.ts` — TS 데이터 contract (BodyNormalizationProfile 박제 박제. BodyComparisonReport 신설 필요)
- `backend/shared/python/sunity_shared/models.py` + `.../analysis/body_normalization.py` — Python 미러
- `docs/contract.md` §7 — BodyNormalizationProfile 명세 (BodyComparisonReport 추가 필요)

### Phase 2 박제 (upstream)

- `.planning/phases/02-bodynormalizationprofile-rtmw-segment/02-CONTEXT.md` — 5 필드 + warnings + confidence schema 박제
- `.planning/phases/02-bodynormalizationprofile-rtmw-segment/02-01-PLAN.md` — `measure_body_profile` 박제 위치 + helper `_angles_and_body_profile_from_video` (pipeline/app.py:306)
- `backend/shared/python/sunity_shared/analysis/body_normalization.py` — BodyNormalizationProfile dataclass + 5 필드 validator
- `backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py` — measure_body_profile 본체
- `backend/functions/pipeline/app.py:306` — `_angles_and_body_profile_from_video` helper (Phase 6 가 호출 책임)

### Phase 5 박제 (upstream)

- `.planning/phases/05-gemini/05-CONTEXT.md` — Gemini 기술 인식기 결정 박제
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` — 기술 인식 결과 (motion_id + EXTEND/BENT) 가 Phase 6 분기 정확도 결정
- `backend/shared/python/sunity_shared/analysis/technique_cache.py` — 영상 hash 캐싱

### IPSF 채점 + Studio Term 박제

- `.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md` — IPSF 5트랙 v1 scope (a + c + Page 9). mode3 first Page 9 단독 fallback 의 공식 근거
- `.planning/phases/16-studio-term-foundation/16-CONTEXT.md` — 분기 1/2/3 (AKA / 정은지 reference / 자동 수집) 박제
- `docs/research/폴스포츠-지식.md` — 도메인 지식 박제

### Downstream (Phase 6 출력 소비)

- ROADMAP §Phase 7 (차이 분류) — `BodyComparisonReport.findings[]` 소비 + body_type_allowed / needs_adjustment / uncertain 분류
- ROADMAP §Phase 12 (실측 각도 + 키포인트 오버레이) — `scaleRatios` 메타 + 방향 B reproject 좌표 소비
- ROADMAP §Phase 13 (보완 운동 + LLM 분기 카피) — 실패 원인 + 체형 차이 finding 소비

### 박제 메모리 (정합 필수)

- [[scoring-dimensions-ipsf]] — IPSF 차원 + 좌우 대칭 차원 제거 (shoulderHipRatio 폭 보정 점수 차원 미적용 박제 근거)
- [[mode3-progress-not-similarity]] — mode3 = 절대 지표 델타, %일치 헤드라인 X
- [[ipsf-5-track-scoring]] — Page 9 절대 트랙 fallback 의 공식 근거
- [[feedback-analysis-first]] — 분석 정확도 우선, confidence 높을 때 모든 path 활성화
- [[mvp-simple-pilot-quality]] — 단순 fallback + 점진적 정밀화
- [[analysis-objectivity-no-human-scores]] — 임계값 = IPSF + 정은지 측정값만, 사람 점수 라벨링 영구 금지
- [[scoring-dimensions-ipsf]] (재인용) — 균형/대칭 차원 제거 (정은지 41점 위양성 주범 제거)

### 시스템 아키텍처 (research 박제)

- `docs/research/00_시스템_아키텍처_FINAL.md` — 두 엔진 아키텍처 (체형 보정 + 힘 패턴) 박제
- `docs/research/01_체형차이_보정엔진_FINAL.md` — Phase 6 본체 reference research

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`backend/shared/python/sunity_shared/analysis/body_normalization.py::BodyNormalizationProfile`** — Phase 2 박제. 5 필드 + confidence + warnings + finite/strictly-positive validator. Phase 6 는 본 dataclass 를 입력으로 받음.
- **`backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py::measure_body_profile`** — Phase 2 박제. RTMW PoseFrame list → BodyNormalizationProfile. Phase 6 는 본 함수를 reference video 에 일회 호출 (mode1) 박제.
- **`backend/functions/pipeline/app.py:306 _angles_and_body_profile_from_video`** — Phase 2 박제 helper. Phase 6 plan 이 본 helper 를 `_process` 분기에서 호출 + Firestore AnalysisDoc 통합 책임 (Phase 2 close-out 박제 — "Phase 6 closure: production analysis document 가 bodyNormalizationProfile 을 포함").
- **`backend/shared/python/sunity_shared/analysis/assemble.py::build_dimension_explanation`** — Phase 12.5 박제. Largest Remainder weight % + mode-aware baseline + deficit summary. Phase 6 가 산출한 정규화 결과를 본 함수가 소비해 차원별 카피 박제.
- **`backend/shared/python/sunity_shared/analysis/dimensions.py`** — 각도 / 라인 / 안정성 차원 점수 산식. Phase 6 가 deficit 차감 진입 위치.
- **`backend/shared/python/sunity_shared/firestore_admin.py::get_reference_motion`** — reference-motions 컬렉션 조회. Phase 6 는 `bodyNormalizationProfile` 필드를 본 함수 반환값에서 읽음.

### Established Patterns

- **3-way contract lockstep** — `analysis.ts` ↔ `models.py` ↔ `docs/contract.md` 동시 갱신 (CLAUDE.md Cross-cutting). Phase 6 의 `BodyComparisonReport` 신설은 단일 atomic commit 으로 박제.
- **Adapter Protocol** — `interfaces.py` 박제. Phase 6 의 정규화 알고리즘 본체는 순수 함수 (numpy only) 로 박제 — 단위 테스트 + 알고리즘 교체 가능성 (`normalizeByBodySegments` 변형).
- **Pipeline `_process` 분기** — `pipeline/app.py::_process` 의 mode1 / mode3 분기 패턴. Phase 6 는 본 분기 안에 정규화 호출 박제 — comparisonType 결정 위치.
- **Singleton adapters** — `_ensure_adapters()` 박제 박제. Phase 6 가 신설 adapter (정규화 알고리즘) 추가 시 본 패턴 정합.
- **Firestore nested-array 박제 X** — `(T, J)` 행렬 flat 저장 + reshape (`firestore_admin.complete_analysis` 박제). Phase 6 의 normalizedProReference 좌표도 flat 저장 박제.

### Integration Points

- **`pipeline/app.py::_process`** — 정규화 호출 진입점. comparisonType 분기 박제. mode1 = reference BodyProfile fetch, mode3 first = motion 인식 결과로 fallback, mode3 second+ = 이전 분석 doc fetch.
- **`firestore_admin.complete_analysis`** — Firestore AnalysisDoc 에 `bodyNormalizationProfile` (Phase 2 박제) + `bodyComparisonReport` (Phase 6 신설) 저장.
- **`reference-motions` 컬렉션** — `bodyNormalizationProfile` nullable 필드 신설 (D-06-B2). 백필 스크립트 박제 필요 — 현재 등록된 정은지 reference video 에 일회 `measure_body_profile` 호출.
- **`app/src/lib/userAnalyses.ts::normalize`** — Firestore raw → AnalysisDoc 정규화. `bodyComparisonReport` 필드 추가 시 본 함수 갱신.
- **`app/src/components/result.tsx` (또는 후속 컴포넌트)** — Phase 12 / 12.5 가 본 출력 소비. comparisonType 으로 카피 분기.

</code_context>

<specifics>
## Specific Ideas

- **북극성 use case** (belle 2026-06-08 박제): **"160cm 프로 (정은지) reference + 140cm 수강생 영상 → 체형 위양성 없이 자세 품질만 측정"**. Phase 6 의 모든 알고리즘/test fixture 가 본 시나리오를 충족해야 함. researcher 의 영상 sweep 도 키 차이 영상 포함.
- **시각화 직관 우선** (belle 2026-06-08 박제): "사용자 목적은 자신의 동작에서 수정". Phase 12 오버레이는 사용자 영상 위에 "내 키로 환산된 정은지 자세" (= 변환된 reference 점) 가 그려져야 함 — 방향 B 결정의 근거.
- **점수 ≠ 시각화 동치** (belle 2026-06-08 깨우침 박제): 점수 산출은 방향 A / B 동치 (수학적). 시각화만 직관 차이. 함수 이름 `normalizeStudentPoseToProReference` (ROADMAP) 은 변환 방향 정의가 아니라 "수강생 자세를 평가 기준 위로 가져옴" 의미.
- **confidence-tiered 박제** (belle 2026-06-08 박제, D-06-U1): "지금 하이브리드로 가되 confidence 가 높아질 경우 분석할 수 있는 데로 분석하는 게 좋겠지?" — Phase 6 전반의 universal principle. researcher/planner 단일 게이트로 박제.

</specifics>

<deferred>
## Deferred Ideas

- **점수 보정 산식 magnitude** (deficit 차감 vs target 재계산 + magnitude 결정) — Phase 6 researcher 책임. 영상 데이터 분석 + IPSF GeometricCriterion 호환성 검증 후 박제.
- **세그먼트 정규화 알고리즘 reference paper** — researcher 가 HumanPoseNormalizer / NLF body fitting 비교 + `normalizeByBodySegments` 수학적 정의 박제.
- **`bodyNormalizationConfidence` UI 노출 방식** — Phase 12 / 12.5 transparency layer 후속 결정. Phase 6 는 데이터만.
- **judging 모드 plumbing 구현** — v1.5. Phase 6 에는 mode flag 도입만, 실제 정규화 OFF 분기 구현은 v1.5.
- **다각도 입력 통합** — Phase 4 dep. Phase 6 v1 은 단일 시점만.
- **`shoulderHipRatio` 측정 안정성 검증** — belle Pod 5영상 sweep (`sweep_rtmw_20260603_1409`) 에서 측정 데이터 없음. researcher 가 sweep 재실행 또는 신규 fixture 로 검증 후 임계값 박제.
- **ROADMAP Progress 섹션 갱신** — `.planning/ROADMAP.md:407-415` 의 "Phase 2~11 보류 (파일럿 후 v1.5)" reasoning 은 belle 2026-06-08 결정 ("오버레이/체형/힘 패턴 필수, 추천 순서대로 진행") 와 모순. PROJECT.md + ROADMAP.md + STATE.md 박제 갱신 필요 (별도 작업, 본 phase commit 후).

</deferred>

---

*Phase: 6-coaching*
*Context gathered: 2026-06-08*
