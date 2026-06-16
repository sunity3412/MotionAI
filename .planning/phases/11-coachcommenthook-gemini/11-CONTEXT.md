# Phase 11: CoachCommentHook 데이터 구조 + Gemini 자연어 번역만 - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

모든 리포트(BodyComparisonReport, ForcePatternInference)에 `CoachCommentHook`(autoFindingsSummary / openQuestionsForCoach / suggestedCues / coachComment? / reviewedBy)을 부착하고, **Gemini가 구조화된 finding을 자연어로 번역만**(좌표·판단·점수 출력 금지) 하며, 결과 화면 카피가 AI를 **"강사 보조 도구"**로 포지셔닝한다 (기준 모션 = "하나의 참고일 뿐").

ROADMAP Phase 11 Goal + Success Criteria 1-5 가 scope 앵커. 요건: COACH-01, FEED-03 (FEED-02 는 이미 Complete).

**핵심 스코프 잠금 (belle 2026-06-16):** Phase 11 = **영상을 직접 보지 않는 "Vision 독립" 텍스트/데이터 레이어**다. 측정·채점 엔진(RTMW+DTW+각도)이 점수·각도의 주인이고, Phase 11 Gemini는 그 엔진이 낸 구조화 finding(텍스트)만 자연어로 풀이한다. **영상을 직접 보는 Gemini Vision/omni 기반 코칭은 Phase 17 scope** — 본 phase 에서 영상 멀티모달 호출은 하지 않는다.
</domain>

<decisions>
## Implementation Decisions

### Hook 구조 & 기존 13 detail2 관계
- **D-01:** `CoachCommentHook`(코치협업용 per-리포트 스캐폴드)과 이미 출시된 `tip.detail2`(13, 수강생용 per-관절 코칭)는 **공존 / 별도 유지**한다. 레벨·용도가 다름(수강생 vs 코치협업). 13 코드 재작업 0. 13-A/13-C 의 "별도 유지" 철학과 일관. analysis.ts:186 의 "Phase 11+13 압축 layer" 주석은 detail2 가 둘의 압축 표현이란 뜻이지 통합 지시가 아니다.
- **D-02:** `CoachCommentHook` 부착 단위 = **리포트별 1개씩** (BodyComparisonReport, ForcePatternInference 각각에 `coachCommentHook` 필드). ROADMAP success #2 "모든 리포트에 부착" 직접 충족 + 질문·큐의 출처(어느 리포트) 보존. v2 코치 콘솔이 필요 시 집계.

### AI 필드 생성 주체 & "번역만" 강제
- **D-03:** AI 생성 필드(autoFindingsSummary / openQuestionsForCoach / suggestedCues) = **기존 13 `GeminiCoachWriter` 재사용/확장** (report-hook 생성 메서드 추가, 1회 분석의 기존 LLM 호출 경로에 통합, `_build_coach_context` 공유). 모델 = **Gemini** (ROADMAP 고정). 영상 미사용 — 구조화 finding 텍스트 입력만.
  - **[2026-06-16 review correction]** Codex 직접 plan-review(11-REVIEWS.md BLOCKER-1, 오케스트레이터가 코드로 재검증)에서 D-03 의 "재사용/확장" 을 기존 Vision writer 의 **출력 스키마 확장**으로 구현하면 안 됨이 확인됨. 근거: `coach_writer_v2.py:1` = "Gemini Pro Vision" 전용, `write()` 가 `videoPath` 없으면 `{_fallbackReason: video_path_missing}` 반환(:414-417) / 있으면 `GeminiVisionCall.call(video_path)` 호출(:430). 그 writer 를 확장하면 (a) Phase 11 "Vision 독립" 잠금 위반 또는 (b) Phase 11/17 경계 침범이 발생하고, strict `CoachPayload`(joints-only) + `_coach_user_visible_keys` joint 집계 contract 가 hook 키로 오염됨(BLOCKER-3). **해소:** D-03 의 intent(모델=Gemini, text-only, `_build_coach_context` 철학 + `_enforce_no_reject_patterns` 가드 재사용)는 그대로 보존하되, 구현은 **별도 text-only writer** `backend/shared/python/sunity_shared/gemini/coach_hook_writer.py` 의 `GeminiCoachHookWriter` 로 한다(기존 Vision `GeminiCoachWriter.write()` 무수정, `GeminiVisionCall`/`videoPath` 미접촉). "single call" = 1회 분석당 hook 호출 **1회**로 두 리포트(force + body) hook 을 함께 묶는다(report 당 1회 아님, joint writer 의 dict 재사용 아님). belle 원문 D-03 wording 은 위 문장 그대로 유지 — 본 항목은 명시적 addendum (silent rewrite 아님).

- **D-04:** "Gemini 번역만" 원칙 = Gemini 는 엔진이 이미 계산한 finding 을 한국어로 풀어 설명만 하고, **새 수치·좌표·점수·판정을 생성하지 않는다.** 수치(점수·실측 각도)는 앱에 계속 나오되 그 출처는 측정 엔진 — LLM 이 자기 숫자/판정을 만들면 위양성·신뢰붕괴 + 강사 대체 인상(FEED-03 위반). [[analysis-objectivity-no-human-scores]] · "수치는 보조, 원인이 핵심" 정합.
  - **[2026-06-16 review correction]** HIGH-1: Phase 11 hook prose 는 **number-free** 로 잠금. 기존 `_SCORE_PATTERNS`(점/분수)·`_JUDGMENT_PATTERNS` 는 `도`/`°`/`deg`/`%` 를 안 잡으므로, hook 전용 reject regex `\d+(\.\d+)?\s*(°|도|deg)` + 백분율을 추가하고 hook 프롬프트에 도(degree) deviation 을 **주입하지 않는다.** 수치는 측정 엔진/UI 소유 (해설자-심판 비유 — 전광판 숫자의 주인은 심판).
- **D-05:** 강제 방법 = **프롬프트 제약 + 단위테스트(금지패턴 0 검증)**. 시스템 프롬프트에 "수치·좌표·점수·판정 출력 금지, finding 자연어 풀이만" + 골든 finding 입력 → 출력에 좌표/점수/판정/도(degree) 패턴 0 assert (13-C `forbidden_in_copy` 패턴 재사용). 런타임 sanitize 는 채택 안 함(자연어 손상 위험) — **reject-and-fallback** (금지패턴 매치 시 canned hook 대체). 강제 메커니즘 세부는 Claude 재량(belle: "강제는 네가 코드로").

### v1 노출 범위 (데이터 vs 화면)
- **D-06:** v1 수강생 결과 화면엔 **`openQuestionsForCoach` 만 노출**한다 — "강사에게 확인할 점" 섹션. 수강생이 강사한테 가져갈 거리 → 학원 도입·강사 보조 도구 포지셔닝 직접 지원. `autoFindingsSummary`/`suggestedCues` = 데이터만 저장(v1 화면 비노출). `coachComment`/`reviewedBy` = **v2** (강사 입력 — v1 엔 빈/null 필드). 근거: COACH-01 "UI/입력은 v2" 는 **강사가 입력하는** 부분을 미루는 뜻 → AI 생성 읽기전용 필드 노출은 v1 가능.
  - **[2026-06-16 review correction]** HIGH-2: 결과 화면은 **두 리포트(force + body)의 openQuestionsForCoach 를 병합**해 노출한다(첫 non-null array 만 고르는 `??`-chain 금지 — array 는 nullish 아니라 force hook 존재 시 body 질문이 영구 누락됨). concat → trim → Boolean filter → de-dupe → slice(0,5).

### "강사 보조 도구" 포지셔닝 카피 (FEED-03)
- **D-07:** 포지셔닝 카피 = **결과 화면 상단 1줄 + 코치 섹션 헤더**. 가볍게(예: "이 분석은 강사 지도를 돕는 참고예요") + D-06 의 "강사에게 확인할 점" 섹션이 포지셔닝을 강화. 전용 강조 배너는 채택 안 함(매 분석 반복 노출 거슬림).

### Fallback (ROADMAP success #5)
- **D-08:** LLM 키(Gemini/Cerebras) 미설정 시 **canned fallback 카피로 분석이 완료**된다. 기존 graceful no-op(lazy import → `_client is None`) 패턴 재사용. Hook 의 AI 필드는 fallback 시 템플릿/canned 로 채움 → 분석 자체는 절대 실패하지 않음.
  - **[2026-06-16 review correction]** WARNING-2: 기존 Gemini writer 는 `_client` 필드가 없음(`GeminiCoachWriter.__init__` = `_api_key_loader`/`_model_override`). 따라서 신규 `GeminiCoachHookWriter` 의 fallback 의존 seam 은 **`api_key_loader` 실패 또는 hook 호출이 None 반환** → canned hook 으로 정의하고, 그 seam 을 테스트한다(Cerebras 의 private `_client is None` shape 을 직접 검사하지 않음).

### Claude's Discretion
- "기준 모션 = 하나의 참고일 뿐" 문구 위치: Mode 1(정은지 비교) 화면 기준모션 라벨 근처 (Claude 배치).
- `CoachCommentHook` 필드 세부 스키마(타입·nullable·Firestore flat 저장 형태), 강제 단위테스트 fixture, fallback canned 카피 톤 — Claude 재량 (단 3-way lockstep + [[firestore-nested-array-flat]] 준수).
- autoFindingsSummary / suggestedCues 의 내용 성격(요약 길이, 큐 개수) — Claude 재량.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 로드맵·요건
- `.planning/ROADMAP.md` §"Phase 11" — Goal + Success Criteria 1-5 + Mode:mvp + UI hint
- `.planning/REQUIREMENTS.md` — `COACH-01`(CoachCommentHook 데이터 구조, UI/입력은 v2), `FEED-03`(강사 보조 도구 포지셔닝), `FEED-02`(이미 Complete — 피드백 순서/부위별 언어)
- `.planning/PROJECT.md` — 핵심가치(분석 정확도, 수치는 보조 원인이 핵심), v2 연기 목록

### 데이터 계약 (3-way lockstep — 동시 갱신 필수)
- `app/src/types/analysis.ts` — `CoachingTipDetail`(L198, detail2 — 공존 대상), `ForcePatternInference`(L908), `BodyComparisonReport`(L1174), `AnalysisResult`(L317, 리포트 필드). L186/L345 에 Phase 11 책임 경계 주석 박제됨 — 반드시 읽을 것.
- `backend/shared/python/sunity_shared/models.py` — BodyComparisonReport / ForcePatternInference 모델 (L251~273), detail2 normalize
- `docs/contract.md` — API 계약 단일 출처

### 코드 통합 지점
- `backend/functions/pipeline/app.py` — `GeminiCoachWriter` / `_ensure_gemini_coach_writer` / `_build_coach_context` / 13-C dual-track (joint coach 경로 — **무수정**, hook 은 별도 writer/변수). hook 생성 site = force_pattern_inference 생성(:2099-2115) 이후 / complete_analysis(:2286) 이전.
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` — **무수정** (Vision 전용). hook 은 신규 `coach_hook_writer.py`.
- `backend/shared/python/sunity_shared/gemini/guardrails.py` — `_enforce_no_reject_patterns` 재사용(hook 가드).
- `backend/shared/python/sunity_shared/analysis/coach_writer.py` — graceful no-op(lazy import) fallback 패턴(개념 참조).
- `backend/shared/python/sunity_shared/analysis/assemble.py` — build_result / 리포트 조립.
- `app/src/app/analysis/result.tsx` — 결과 화면(상단 포지셔닝 1줄 + "강사에게 확인할 점" 섹션 + 코치섹션 헤더 카피).

### Phase 간 조율 (중요)
- `.planning/ROADMAP.md` §"Phase 17: Gemini Vision Integration — 4 영역 통합" — Phase 17 의 "coach" 영역이 본 phase 텍스트 코칭과 **겹침**. Phase 17 계획 시 Phase 11 텍스트 레이어와의 관계 조율 필요. 본 phase 는 Vision 영상 호출을 하지 않음(경계).

### 메모리
- `analysis-objectivity-no-human-scores`, `gemini-vision-active-use`, `gemini-latest-model-versions`, `coaching-tone-customization`, `feedback-analysis-first`, `field-research-stakeholders`, `section-dual-coach-report`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_build_coach_context`(pipeline/app.py:798): hook context source 철학 재사용 — 단 hook 은 **report findings(force/body)** 만 소비(`kismam.top_issues` / generic top-joint deviation 아님 — `tip.detail2` 중복 회피, D-03 correction).
- `_enforce_no_reject_patterns`(guardrails.py:47): hook 런타임 가드 재사용 + 도(degree) regex 추가.
- `tip.detail2`(CoachingTipDetail, analysis.ts:198): 공존 대상 — 손대지 않음(D-01).
- 13-C `forbidden_in_copy` 금지문구 검사 패턴: D-05 "번역만" 단위테스트에 재사용.
- graceful no-op(coach_writer.py lazy import): D-08 fallback 개념 — 단 seam 은 `api_key_loader`/None-return (D-08 correction).
- `resolve_model("B")`(gemini/config.py): hook writer 모델 = region B (코칭) — raw model string 하드코딩 금지.

### Established Patterns
- contract-first 3-way lockstep: analysis.ts ↔ models.py ↔ contract.md 동시 갱신.
- [[firestore-nested-array-flat]]: CoachCommentHook 의 list 필드(openQuestionsForCoach 등)는 flat 저장(list[scalar] 허용, list[list] 금지).
- 옵셔널 필드 + 이전 빌드 doc 호환(dimensionExplanation/recommendedExercises 패턴): coachCommentHook 도 nullable.
- 모듈 분리(circular-import 회피): `coach_hook.py` = frozen dataclass + pure validators only; builder/writer = 별도 모듈(HIGH-3).

### Integration Points
- pipeline `_process` → force_pattern_inference 생성(:2099-2115) 이후 hook 1회 생성 → 두 리포트에 `dataclasses.replace` 로 부착 → camelCase 변환(dict) → complete_analysis(:2286).
- result.tsx → 두 리포트 openQuestionsForCoach 병합 섹션 + 포지셔닝 카피 렌더(D-06/D-07), 테마 토큰만(라이트, brand #FF4B33).
- Pod/LLM: hook 생성은 신규 text-only Gemini 경로(Vision 미사용). 실 LLM E2E 는 Phase 15 실증과 함께.
</code_context>

<specifics>
## Specific Ideas

- `openQuestionsForCoach` 예시 성격: "왼쪽 무릎 굽힘이 의도된 동작인지 강사와 확인" 식 — 수강생이 정확한 원인을 모르므로 강사에게 가져갈 질문 형태. (D-06 "강사에게 확인할 점" 섹션)
- 포지셔닝 카피 톤: AI 가 강사를 대체한다는 인상 제거. "참고/보조" 어휘. 현장 설문 — 강사 철학 충돌 우려를 푸는 카피([[field-research-stakeholders]]).
- 해설자-심판 비유(belle 설명에 사용): Gemini=해설자(말로 풀이), 측정엔진=심판(점수 주인). 전광판(앱)엔 숫자 뜨되 출처는 심판.
</specifics>

<deferred>
## Deferred Ideas

- **Gemini Vision/omni 가 영상을 직접 보고 코칭 텍스트 풍부화** → **Phase 17** (Gemini Vision Integration 4영역의 "coach"). belle 2026-06-16: "omni 더해지는 건 업데이트 더 필요한 부분." 본 phase(Vision 독립 텍스트 레이어)와 겹치는 지점이라 Phase 17 계획 시 조율.
- **코치 입력 UI**(coachComment 작성, reviewedBy 배정) — COACH-01 "UI/입력은 v2". v1 은 빈/null 필드 + 데이터 구조만.
- **마이페이지 코칭 글 스타일 선택**([[coaching-tone-customization]]) — 포지셔닝 카피와 별개. 본 phase 외.

### Reviewed Todos (not folded)
None — todo 매칭 0 (todo_count=0).
</deferred>

---

*Phase: 11-coachcommenthook-gemini*
*Context gathered: 2026-06-16*
</content>
</invoke>
