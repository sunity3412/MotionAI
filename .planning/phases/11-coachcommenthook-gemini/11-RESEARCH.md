# Phase 11: CoachCommentHook 데이터 구조 + Gemini 자연어 번역만 - Research

**Researched:** 2026-06-16
**Domain:** Contract-first data-layer extension (TS↔Python↔docs 3-way lockstep) + LLM "translation-only" enforcement + result-screen positioning copy. Vision-independent text/data layer.
**Confidence:** HIGH (all findings verified against actual repo code; no external deps introduced)

> ## ⚠ [SUPERSEDED 2026-06-16 Codex review iter-1 + iter-2] — READ THIS FIRST, OVERRIDES STALE GUIDANCE BELOW
>
> Several sections below (Summary :43, Alternatives :89, Architecture diagram :125, Recommended structure :161, **Pattern 3 :214-226**, Pitfall 5 :311-315, Code Examples :330, Open Questions :398-401) still describe the **pre-review** design of *extending* `GeminiCoachWriter.write_report_hook()` on the same dual-track Gemini call path, gating on `self._client is None`, and a result-screen `??` chain. **That design is REPLACED.** Implement the LOCKED design instead:
>
> 1. **Separate text-only writer** `gemini/coach_hook_writer.py::GeminiCoachHookWriter` — Vision `GeminiCoachWriter.write()` is UNTOUCHED (iter-1 BLOCKER-1). No `videoPath`/`GeminiVisionCall`.
> 2. **Fallback seam = `api_key_loader` + None-return**, NOT private `self._client` (iter-1 WARNING-2).
> 3. **Hook generated AFTER `force_pattern_inference` exists / before `complete_analysis`** — NOT on the existing :1945 dual-track coach call site (iter-1 BLOCKER-2). `coach_details` (joint) and `coach_hooks` (report) are separate pipeline vars (iter-1 BLOCKER-3).
> 4. **Dedicated `_validate_coach_comment_hook`** (force scoped branch + body `complete_analysis` precheck) — do NOT delegate to the generic `_validate_flat_dict_no_nested_array`, which allows `list[dict]` (iter-2 BLOCKER-1).
> 5. **Degree/% guard is HOOK-SCOPED only** (`forbid_measurement_units` flag or `_enforce_no_hook_number_patterns`) — do NOT add `°|도|deg|%` to the global `_SCORE_PATTERNS`; scene_finder/reference_extractor legitimately echo "30도"/"50%" (iter-2 BLOCKER-2).
> 6. **Reuse `_strip_unsupported_schema_keys(CoachHookBundle.model_json_schema())` + `HttpOptions(timeout=_HTTP_TIMEOUT_MS)` config** + a `_generate_with_retry`-style 5xx/ValidationError retry path — raw Pydantic schema 400s live (iter-2 HIGH-1).
> 7. **Per-report partial fallback** — resolve each report independently so a partial `CoachHookBundle` still gives BOTH reports a hook (iter-2 HIGH-2).
> 8. **UI** = concat/trim/dedupe/slice of BOTH reports' `openQuestionsForCoach` — NOT a first-non-null `??` chain (iter-1 HIGH-2).
>
> **[iter-3 2026-06-17 additions]:** (9) `GeminiCoachHookWriter.build_coach_hooks(...) -> CoachHookBundle | None` returns ONLY bundle/None; per-report fallback lives in a PURE `coach_hook_builder.resolve_coach_hook_bundle(bundle, *, force_findings, body_findings) -> tuple[CoachCommentHook, CoachCommentHook]` (writer/pipeline책임 분리, iter-3 HIGH-1). (10) Hook guard rejects ALL Arabic digits (`\d`), not just degree/% — bare "3초"/"2회"/"15cm"/"180" also rejected (number-free D-04, iter-3 HIGH-2). (11) BOTH `CoachCommentHookPayload` AND `CoachHookBundle` carry `ConfigDict(extra="forbid")` + drift test (iter-3 MEDIUM-1).
>
> The historical text below is kept for context only. Where it conflicts with this banner, **this banner wins.**

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `CoachCommentHook`(코치협업용 per-리포트 스캐폴드)과 이미 출시된 `tip.detail2`(13, 수강생용 per-관절 코칭)는 **공존 / 별도 유지**한다. 레벨·용도가 다름(수강생 vs 코치협업). 13 코드 재작업 0. `analysis.ts:186` 의 "Phase 11+13 압축 layer" 주석은 detail2 가 둘의 압축 표현이란 뜻이지 통합 지시가 아니다.
- **D-02:** `CoachCommentHook` 부착 단위 = **리포트별 1개씩** (BodyComparisonReport, ForcePatternInference 각각에 `coachCommentHook` 필드). ROADMAP success #2 "모든 리포트에 부착" 직접 충족 + 질문·큐의 출처(어느 리포트) 보존. v2 코치 콘솔이 필요 시 집계.
- **D-03:** AI 생성 필드(autoFindingsSummary / openQuestionsForCoach / suggestedCues) = **기존 13 `GeminiCoachWriter` 재사용/확장** (report-hook 생성 메서드 추가, 1회 분석의 기존 LLM 호출 경로에 통합, `_build_coach_context` 공유). 모델 = **Gemini** (ROADMAP 고정). 영상 미사용 — 구조화 finding 텍스트 입력만.
- **D-04:** "Gemini 번역만" 원칙 = Gemini 는 엔진이 이미 계산한 finding 을 한국어로 풀어 설명만 하고, **새 수치·좌표·점수·판정을 생성하지 않는다.** 수치(점수·실측 각도)는 앱에 계속 나오되 그 출처는 측정 엔진 — LLM 이 자기 숫자/판정을 만들면 위양성·신뢰붕괴 + 강사 대체 인상(FEED-03 위반). [[analysis-objectivity-no-human-scores]] · "수치는 보조, 원인이 핵심" 정합.
- **D-05:** 강제 방법 = **프롬프트 제약 + 단위테스트(금지패턴 0 검증)**. 시스템 프롬프트에 "수치·좌표·점수·판정 출력 금지, finding 자연어 풀이만" + 골든 finding 입력 → 출력에 좌표/점수/판정 패턴 0 assert (13-C `forbidden_in_copy` 패턴 재사용). **런타임 sanitize 는 채택 안 함**(자연어 손상 위험). 강제 메커니즘 세부는 Claude 재량.
- **D-06:** v1 수강생 결과 화면엔 **`openQuestionsForCoach` 만 노출**한다 — "강사에게 확인할 점" 섹션. `autoFindingsSummary`/`suggestedCues` = 데이터만 저장(v1 화면 비노출). `coachComment`/`reviewedBy` = **v2** (강사 입력 — v1 엔 빈/null 필드). 근거: COACH-01 "UI/입력은 v2" 는 **강사가 입력하는** 부분을 미루는 뜻 → AI 생성 읽기전용 필드 노출은 v1 가능.
- **D-07:** 포지셔닝 카피 = **결과 화면 상단 1줄 + 코치 섹션 헤더**. 가볍게(예: "이 분석은 강사 지도를 돕는 참고예요") + D-06 의 "강사에게 확인할 점" 섹션이 포지셔닝을 강화. **전용 강조 배너는 채택 안 함**(매 분석 반복 노출 거슬림).
- **D-08:** LLM 키(Gemini/Cerebras) 미설정 시 **canned fallback 카피로 분석이 완료**된다. 기존 graceful no-op(lazy import → `_client is None`) 패턴 재사용. Hook 의 AI 필드는 fallback 시 템플릿/canned 로 채움 → 분석 자체는 절대 실패하지 않음.

### Claude's Discretion
- "기준 모션 = 하나의 참고일 뿐" 문구 위치: Mode 1(정은지 비교) 화면 기준모션 라벨 근처 (Claude 배치).
- `CoachCommentHook` 필드 세부 스키마(타입·nullable·Firestore flat 저장 형태), 강제 단위테스트 fixture, fallback canned 카피 톤 — Claude 재량 (단 3-way lockstep + [[firestore-nested-array-flat]] 준수).
- autoFindingsSummary / suggestedCues 의 내용 성격(요약 길이, 큐 개수) — Claude 재량.

### Deferred Ideas (OUT OF SCOPE)
- **Gemini Vision/omni 가 영상을 직접 보고 코칭 텍스트 풍부화** → **Phase 17** (Gemini Vision Integration 4영역의 "coach"). 본 phase 는 Vision 영상 호출을 하지 않음(경계).
- **코치 입력 UI**(coachComment 작성, reviewedBy 배정) — COACH-01 "UI/입력은 v2". v1 은 빈/null 필드 + 데이터 구조만.
- **마이페이지 코칭 글 스타일 선택**([[coaching-tone-customization]]) — 포지셔닝 카피와 별개. 본 phase 외.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COACH-01 | 모든 리포트(BodyComparisonReport, ForcePatternInference 등)에 `CoachCommentHook`(autoFindingsSummary, openQuestionsForCoach, suggestedCues, coachComment?, reviewedBy) 부착. UI/입력은 v2 옵션. | Standard Stack §"Hook 부착 surface" + Architecture Pattern 1 (per-report dataclass field) + Pattern 4 (scoped validator). Reports = `force_pattern.ForcePatternInference` + `body_normalizer.BodyComparisonReport` frozen dataclasses (확인됨). v2 필드(`coachComment`/`reviewedBy`) = nullable, v1 = null. |
| FEED-02 | (이미 Complete — Phase 9/11) 피드백 순서/부위별 언어. | 기존 `force_pattern_copy` + dual-coach. **본 phase 에서 재작업 0** — coach hook 은 그 위 layer. Traceability 상 FEED-02 = Complete. |
| FEED-03 | 결과 화면 카피가 AI를 "강사 보조 도구"로 포지셔닝 (AI 대체 인상 제거). | Architecture Pattern 5 (positioning copy in `result.tsx`) + D-07. 기존 `_COACH_NOTE_REQUIRED_WORDS` ("강사"/"함께"/"확인") + `contract.md:725` "(b) AI = 강사 보조 도구" 정합. |
</phase_requirements>

## Summary

Phase 11 is a **contract-layer extension phase with zero new external dependencies**. It adds one new data structure (`CoachCommentHook`) to two existing frozen-dataclass reports (`ForcePatternInference`, `BodyComparisonReport`), populates the AI-generated text fields by extending the already-operational `GeminiCoachWriter` (or its dual-track call path), exposes one field (`openQuestionsForCoach`) on the result screen, and adds positioning copy. Every integration point already exists in the codebase — the work is pattern-replication, not greenfield.

The two highest-risk surfaces are both **landmines, not unknowns**: (1) the project-wide Firestore nested-array ban enforced by `firestore_admin._validate_flat_dict_no_nested_array` — a `coachCommentHook` attached to a report that *already* contains `findings: list[dict]` introduces a `dict → list[dict]` + `dict → list[str]` shape that the **existing report scoped validators will reject** unless they are extended (the `_validate_force_pattern_inference` validator explicitly raises on any unexpected top-level key); and (2) the "translation-only" guarantee, which already has a battle-tested enforcement primitive — `gemini.guardrails._enforce_no_reject_patterns` (score/coordinate/judgment regex → ValueError) plus the AST-grep forbidden-phrase test pattern used in Phase 9 (`test_force_pattern_copy_no_forbidden.py`) and Phase 13 (`test_branch2_forbidden_phrase_gate.py`).

**Primary recommendation:** Treat this as a 3-way-lockstep contract change (analysis.ts ↔ models.py re-export ↔ docs/contract.md) plus a per-report scoped Firestore validator extension, reusing `GeminiCoachWriter` + `_build_coach_context` (D-03), `guardrails._enforce_no_reject_patterns` for runtime objectivity guard, and the AST forbidden-phrase test pattern for the D-05 "번역만" unit test. No package installs. No Vision/video call. No score/angle generation by the LLM — the hook's numbers (if any) must be copied from the engine's existing finding fields, never minted by Gemini.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CoachCommentHook schema definition | Data contract (TS + Python + docs) | — | Pure type; 3-way lockstep mandate (CLAUDE.md Cross-cutting). No runtime tier owns "the type". |
| AI text-field generation (autoFindingsSummary / openQuestionsForCoach / suggestedCues) | Backend pipeline (`pipeline/app.py` `_process` LLM call path) | ML adapter (`GeminiCoachWriter`) | D-03 — reuse existing 13 Gemini coach call. Engine owns findings; Gemini translates text only. |
| Hook attachment to each report | ML analysis assembly (`assemble.py` / report dataclasses) | Backend pipeline (wiring) | D-02 — per-report field. Report dataclasses live in `force_pattern.py` / `body_normalizer.py`. |
| Firestore-safe serialization of hook | Firestore Admin (`firestore_admin.complete_analysis` + scoped validators) | — | Nested-array ban enforced here. New validator path needed (existing report validators reject unknown keys). |
| "Translation-only" enforcement | Backend (prompt + runtime guard + unit test) | — | D-05 — prompt constraint + `_enforce_no_reject_patterns` runtime guard + AST forbidden-phrase test. No client tier. |
| openQuestionsForCoach display + positioning copy | App screen (`result.tsx`) | App theme tokens | D-06/D-07 — student-facing read-only render. Light theme, brand #FF4B33, theme tokens only. |
| Fallback (key unset → canned) | ML adapter (graceful no-op) + assembly | — | D-08 — reuse `_client is None → {}` pattern; assembly fills canned hook. |

## Standard Stack

### Core

This phase introduces **no new libraries**. It reuses existing project assets. The "stack" here is the set of in-repo modules to extend.

| Asset | Location | Purpose | Why Standard |
|-------|----------|---------|--------------|
| `GeminiCoachWriter` | `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` | finding 텍스트 → 한국어 자연어 (이미 동작). report-hook 생성 메서드 추가 surface. | D-03 명시 재사용. `.write(context: dict) -> dict` B3 시그니처 hard gate (CerebrasCoachWriter 와 100% 동일). [VERIFIED: repo grep] |
| `_build_coach_context(...)` | `pipeline/app.py:798` | Cerebras/Gemini 양 writer 공유 단일 context dict. | D-03 "context 공유" 직접 충족. 이미 mode/joints/dimensionScores/sceneFlags/branchInfo 포함. [VERIFIED: repo read] |
| `guardrails._enforce_no_reject_patterns` | `backend/shared/python/sunity_shared/gemini/guardrails.py:47` | 점수(`\d+점`,`\d+/\d+`)·좌표(`좌표`,`x=`,`y=`)·판단(`잘했다`,`훌륭`,`완벽`) 정규식 → ValueError. | D-05 "번역만" 런타임 객관성 가드의 기성 primitive. [VERIFIED: repo read] |
| `firestore_admin._validate_flat_dict_no_nested_array` + scoped validators | `firestore_admin.py:45` + `:343`(force) `:481`(keypoint) `:415`(exercises) | nested-array 차단. | [[firestore-nested-array-flat]] 강제 게이트. 신규 hook 의 `list[str]` 필드 통과 가능 형태로 설계 필수. [VERIFIED: repo read] |
| `_dataclass_to_camel_case_dict` | `pipeline/app.py:1482` | frozen dataclass → camelCase Firestore dict (4-case helper). | 신규 hook dataclass 도 동일 helper 로 직렬화. [VERIFIED: repo read] |
| AST forbidden-phrase test pattern | `backend/tests/phase09/test_force_pattern_copy_no_forbidden.py`, `backend/tests/phase13/test_branch2_forbidden_phrase_gate.py` | 정적 문자열 상수에서 금지 표현 0 hit assert. | D-05 "골든 finding → 금지패턴 0" 단위테스트 precedent. [VERIFIED: repo read] |

### Supporting

| Asset | Location | Purpose | When to Use |
|-------|----------|---------|-------------|
| `CerebrasCoachWriter` graceful no-op | `analysis/coach_writer.py:145` | 키 미설정 시 `_client is None` → `write()` 반환 `{}`. | D-08 fallback 패턴 1:1 재사용. |
| `assemble.assemble_dual_coach_sections` | `assemble.py:404` | 13-C 섹션형 듀얼 coach 조립 (cross-fill). | hook AI 필드가 dual-track 산출을 소비할 경우 참조 (단 hook 은 report-level, detail2 는 joint-level — 별도 path). |
| `models.normalize_*` 방어 정규화 | `models.py:103` (`normalize_body_profile`) | malformed → None graceful. | hook 읽기 측(app) defensive normalize 패턴(`userAnalyses.ts:normalize`) precedent. |
| `gemini.config.resolve_model` | `gemini/config.py` | `gemini-3.1-pro-preview` / `gemini-3.5-flash` 화이트리스트(404 차단). | hook 생성에 Gemini 직접 호출 시 raw model string 금지 — 본 모듈 경유. [[gemini-latest-model-versions]] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ~~Extend existing `GeminiCoachWriter.write` / add `write_report_hook`~~ **[SUPERSEDED — separate `GeminiCoachHookWriter` module, banner item 1]** | New standalone `GeminiCoachHookWriter` (text-only, schema-strip config reuse) | D-03 says "report-hook 생성 메서드 추가". A **separate method** is cleaner (different output shape: hook ≠ joint coaching) but must still share `_build_coach_context`. Recommend separate method, same context, same client/guardrails. |
| Runtime sanitize of LLM output | Prompt constraint + guard + test (D-05) | **D-05 explicitly rejects runtime sanitize** (corrupts natural language). Guard = reject-and-fallback, not edit. Do NOT regex-strip and re-emit. |
| Per-report scoped validator | Reuse generic `_validate_flat_dict_no_nested_array` | Generic validator allows `dict → list[str]` and `dict → list[dict-of-scalars]`, which covers the hook IF attached at a path that routes through the generic validator. But reports route through their OWN scoped validators (`_validate_force_pattern_inference`) which **reject unknown top-level keys**. See Pitfall 1. |

**Installation:** None. No `npm install` / `pip install`. This phase adds zero dependencies.

## Package Legitimacy Audit

> Not applicable — this phase installs **no external packages**. All assets are in-repo modules. Slopcheck/registry verification skipped (no new dependencies). Existing deps (`firebase`, `cerebras.cloud.sdk`, `google-genai` via lazy import) are already in the project and out of scope for this phase.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────────┐
  S3 ObjectCreated ──► SQS ──► pipeline/app.py::_process                │
                         │     (single analysis pass, existing)         │
                         │                                              │
                         │  ① 측정 엔진 (RTMW + DTW + 각도)             │
                         │     → assessments, dimension_scores,         │
                         │       force_signals_report                   │
                         │            │                                 │
                         │            ▼                                 │
                         │  ② 리포트 산출 (engine owns numbers)         │
                         │     force_pattern.infer_force_direction_     │
                         │       pattern() → ForcePatternInference      │
                         │     body_normalizer.compare_body_profiles()  │
                         │       → BodyComparisonReport                 │
                         │            │                                 │
                         │            ▼                                 │
                         │  ③ NEW: per-report CoachCommentHook 생성     │
                         │     _build_coach_context (shared, D-03)      │
                         │            │                                 │
                         │      ┌─────┴──────┐                          │
                         │   GeminiCoachWriter   key unset / fail       │
                         │   .write_report_hook  ───► canned fallback   │
                         │   (TEXT-ONLY)              (D-08)            │
                         │      │  guardrails._enforce_no_reject_       │
                         │      │  patterns (score/coord/judgment)     │
                         │      ▼                                       │
                         │   hook dict {autoFindingsSummary,            │
                         │     openQuestionsForCoach[], suggestedCues[],│
                         │     coachComment=null, reviewedBy=null}      │
                         │            │ (flat: list[str] only)          │
                         │            ▼                                 │
                         │  ④ attach hook → each report dataclass       │
                         │     (coachCommentHook field, D-02)           │
                         │            │                                 │
                         │            ▼ _dataclass_to_camel_case_dict   │
                         │  ⑤ firestore_admin.complete_analysis         │
                         │     scoped validator (nested-array gate)     │
                         └────────────┬────────────────────────────────┘
                                      ▼
                         Firestore users/{uid}/analyses/{id}.result
                                      │ onSnapshot
                                      ▼
                         app result.tsx — render openQuestionsForCoach
                         ("강사에게 확인할 점") + positioning copy (D-06/D-07)
```

**The objectivity hard-wall:** numbers in the hook (if any) flow ②→④ from the engine. Gemini (③) emits only Korean prose; the guard rejects any LLM-minted number/coordinate/judgment.

### Recommended Project Structure (touched files only — no new dirs)

```
backend/shared/python/sunity_shared/
├── analysis/
│   ├── force_pattern.py          # + CoachCommentHook dataclass (or shared module) + field on ForcePatternInference
│   ├── body_normalizer.py        # + coachCommentHook field on BodyComparisonReport
│   └── coach_hook.py (NEW, opt)  # CoachCommentHook dataclass + canned fallback builder (shared by both reports)
├── gemini/
│   └── coach_writer_v2.py        # + write_report_hook(context) -> hook dict (TEXT-ONLY)
├── models.py                     # re-export CoachCommentHook (mirror pattern)
└── firestore_admin.py            # extend _validate_force_pattern_inference + add coachCommentHook handling

backend/functions/pipeline/app.py # wire hook generation into _process; attach to reports before complete_analysis
docs/contract.md                  # §9.11 / §8 — add CoachCommentHook sub-section (3-way lockstep)
app/src/types/analysis.ts         # CoachCommentHook interface + field on both report interfaces
app/src/app/analysis/result.tsx   # "강사에게 확인할 점" section + positioning copy (top 1-liner + coach header)

backend/tests/phase11/            # NEW
├── test_coach_hook_translation_only.py   # golden finding → 0 forbidden pattern
├── test_coach_hook_fallback.py           # key unset → canned hook, analysis completes
└── test_coach_hook_nested_array.py       # validator passes hook; rejects nested list
```

### Pattern 1: Per-report frozen-dataclass field + 3-way contract mirror

**What:** Add `coach_comment_hook` (snake_case) as a nullable field on each report frozen dataclass; mirror as `coachCommentHook?: CoachCommentHook | null` in TS; document in contract.md. Field order rule: non-default → default (Python dataclass) — add as `= None` default at the END of the field list (precedent: `ForcePatternInference.warnings` default_factory at end).

**When to use:** Always — this is the COACH-01 data-structure core.

**Example (precedent — frozen dataclass with default at end):**
```python
# Source: backend/shared/python/sunity_shared/analysis/force_pattern.py:228 (verified)
@dataclass(frozen=True)
class ForcePatternInference:
    version: str
    findings: list[ForcePatternFinding]
    overall_confidence: MetricConfidence
    mode_context: ModeContext
    warnings: list[str] = field(default_factory=list)
    # Phase 11: add nullable hook AFTER all non-default fields (dataclass rule)
    # coach_comment_hook: CoachCommentHook | None = None
```

### Pattern 2: Flat hook dataclass — list fields are `list[str]` only

**What:** `CoachCommentHook` MUST serialize to a flat dict whose values are scalars or `list[str]`. NO `list[dict]`, NO nested dict. This guarantees nested-array safety regardless of where it's attached.

**Hook field shape recommendation (Claude's discretion per CONTEXT, constrained by nested-array ban):**
```python
@dataclass(frozen=True)
class CoachCommentHook:
    auto_findings_summary: str               # 1 paragraph KO summary (text only)
    open_questions_for_coach: list[str]      # ["왼쪽 무릎 굽힘이 의도된 동작인지 강사와 확인", ...]
    suggested_cues: list[str]                # ["고관절 외회전 의식", ...]
    coach_comment: str | None = None         # v2 — null in v1
    reviewed_by: str | None = None           # v2 — null in v1
    # Recommend a "source" scalar so v2 coach console can aggregate by report (D-02 rationale)
    # source_report: str | None = None       # "forcePatternInference" | "bodyComparisonReport"
```
**Why `list[str]` not `list[dict]`:** When attached to a report that already has `findings: list[dict]`, the report dict becomes `{findings: [...], coachCommentHook: {openQuestionsForCoach: [str,...]}}`. The generic validator (`firestore_admin.py:78-96`) allows `dict → list[str]`; but `list[dict]` inside the hook would need a per-entry scalar check. Keeping list fields as `list[str]` sidesteps the entire `_validate_dict_only_scalars` complexity.

### Pattern 3: TEXT-ONLY LLM method sharing `_build_coach_context`

> **[SUPERSEDED 2026-06-16 Codex review]** Do NOT add `GeminiCoachWriter.write_report_hook` or gate on `self._client`. Use a SEPARATE `GeminiCoachHookWriter` (own module), `api_key_loader`/None-return seam, reused `_strip_unsupported_schema_keys` config + retry path, hook-scoped degree/% guard. See top-of-file banner items 1-2, 5-6.

**What:** Add `GeminiCoachWriter.write_report_hook(context: dict) -> dict` that consumes the SAME `_build_coach_context` output (D-03) and emits ONLY Korean prose fields. System prompt must forbid numbers/coordinates/scores/judgments. Reuse the existing `_COACH_SYSTEM_INSTRUCTION` objectivity clause (`coach_writer_v2.py`: "절대 금지: 점수 / 등급 / x= / y= / 좌표 / 잘했다 / 훌륭 / 완벽 / 양호").

**Example (existing objectivity prompt clause to reuse/adapt):**
```python
# Source: backend/shared/python/sunity_shared/gemini/coach_writer_v2.py (verified)
_COACH_SYSTEM_INSTRUCTION = (
    "당신은 폴스포츠 강사를 보조하는 코칭 AI 입니다. 강사를 대체하지 않습니다.\n"
    ...
    "절대 금지: 점수 / 등급 / x= / y= / 좌표 / 잘했다 / 훌륭 / 완벽 / 양호.\n"
)
```

### Pattern 4: Per-report scoped validator extension (NOT a new generic path)

**What:** The report scoped validators **reject unknown top-level keys**. `_validate_force_pattern_inference` (firestore_admin.py:402) raises `ValueError(f"{sub} unexpected type ...")` on any key that isn't `warnings`/`findings`. Adding `coachCommentHook` to a report dict WILL trip this. Extend each report's scoped validator to recognize `coachCommentHook` and validate it as a flat dict (delegate to `_validate_flat_dict_no_nested_array(value, path=...)`).

**Example (the rejecting branch to extend):**
```python
# Source: backend/shared/python/sunity_shared/firestore_admin.py:367-404 (verified)
for key, value in payload.items():
    ...
    if key == "findings": ...
    # Phase 11: add
    # if key == "coachCommentHook":
    #     _validate_flat_dict_no_nested_array(value, path=sub); continue
    raise ValueError(f"{sub} unexpected list at forcePatternInference top-level ...")
```
`body_comparison_report` currently routes through the **generic** `_validate_flat_dict_no_nested_array` (firestore_admin.py:780) — that path already accepts a nested flat dict with `list[str]`, so the BodyComparisonReport side may need NO validator change IF the hook is flat. **Verify both report attach-paths in planning.** (force_pattern uses scoped validator; body_comparison uses generic — asymmetric.)

### Pattern 5: Result-screen positioning copy + read-only section (light theme, tokens only)

**What:** Render `openQuestionsForCoach` as a "강사에게 확인할 점" card in `result.tsx`; add a top 1-liner ("이 분석은 강사 지도를 돕는 참고예요") + coach-section header copy; place "기준 모션은 하나의 참고일 뿐" near the mode1 reference label (`result.tsx:684` `styles.refName`). Use ONLY `src/theme/` tokens — hardcoding colors/spacing forbidden (app/CLAUDE.md). Existing section-render pattern: `result.forcePatternInference?.findings ?? []` guard (result.tsx:525) — mirror for `coachCommentHook?.openQuestionsForCoach ?? []`.

### Anti-Patterns to Avoid

- **Touching `tip.detail2` / CoachingTipDetail (analysis.ts:198):** D-01 — coexist, separate. Zero rework of 13 code. The hook is report-level; detail2 is joint-level.
- **Letting Gemini mint numbers:** Any score/angle in the hook must be copied from existing engine finding fields, never generated. Guard enforces this; do not bypass.
- **Runtime sanitize:** D-05 forbids regex-stripping LLM output. Guard = reject + fallback, never edit-and-emit.
- **Attaching a `list[dict]` inside the hook:** Trips nested-array validators. Keep list fields `list[str]`.
- **Changing one contract side only:** analysis.ts ↔ models.py(re-export) ↔ contract.md MUST change in one atomic commit (CLAUDE.md Cross-cutting; precedent D-09-U1 atomic lockstep).
- **Calling Gemini Vision / passing `videoPath` to the hook generator:** Phase 11 is Vision-independent. The hook generator consumes structured finding TEXT only, not `local_video_path`. (Phase 17 owns video.)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reject LLM score/coordinate/judgment output | Custom regex scanner | `gemini.guardrails._enforce_no_reject_patterns(text, context=...)` | Already covers `\d+점`, `\d+/\d+`, `좌표`, `x=`, `y=`, `잘했다`, `훌륭`, `완벽`. Battle-tested across Gemini areas. |
| Static forbidden-phrase unit test | New assertion harness | AST-extract pattern from `test_force_pattern_copy_no_forbidden.py` / `test_branch2_forbidden_phrase_gate.py` | Proven: walks string constants, `@pytest.mark.parametrize` over forbidden tuple. |
| Firestore nested-array safety | Manual dict flattening | `_validate_flat_dict_no_nested_array` + per-report scoped validator | Project-wide gate. Reinventing risks `INDEX_ENTRIES_COUNT_LIMIT_EXCEEDED` + write failures ([[firestore-nested-array-flat]], [[firestore-index-entry-limit]]). |
| dataclass → camelCase Firestore dict | Manual key conversion | `_dataclass_to_camel_case_dict` (pipeline/app.py:1482) | 4-case helper already handles dataclass/dict/list/scalar. |
| LLM key-unset graceful fallback | New try/except scaffolding | `_client is None → {}` pattern (coach_writer.py:178) + retry wrapper `_call_coach_writer_with_retry` | D-08 mandates reuse. |
| Gemini model string | Hardcode `"gemini-3.1-pro-preview"` | `gemini.config.resolve_model(...)` | 404 silent-fallback guard; suffix-required. [[gemini-latest-model-versions]] |

**Key insight:** Every primitive this phase needs already exists and is tested. The danger is NOT missing tooling — it's the asymmetric validator paths (scoped vs generic) and the contract-lockstep discipline.

## Runtime State Inventory

> Phase 11 is a **greenfield contract/data extension**, not a rename/refactor/migration. No existing stored string is being renamed.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `coachCommentHook` is a NEW nullable field. Old `analyses` docs simply lack it; app read side must null-guard (`?? []`), same as `recommendedExercises`/`forcePatternInference` backward-compat pattern. | App-side null guard only. No data migration. |
| Live service config | None — no n8n/Datadog/external config touches this. | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | Existing only: `CEREBRAS_KEY_PARAM` (coach_writer.py), Gemini key (Parameter Store / Pod env), `GEMINI_COACH_ENABLED`. No NEW env var required for Phase 11 (hook rides the existing coach path). If a separate toggle is desired, follow `_VISION_ENV_DEFAULTS` pattern — Claude's discretion. | None (reuse). |
| Build artifacts | None — no `pyproject.toml`/package rename; shared layer redeploys via `sam build --use-container` on any backend change (existing workflow). | Standard SAM redeploy. |

**Nothing found requiring migration:** Verified — new nullable field on existing reports; backward-compat handled by app-side null guards (precedent: `forcePatternInference?`, `recommendedExercises?` already nullable in `AnalysisResult`).

## Common Pitfalls

### Pitfall 1: Report scoped validators reject the new `coachCommentHook` key
**What goes wrong:** Attaching `coachCommentHook` to `ForcePatternInference` → `complete_analysis` calls `_validate_force_pattern_inference` → the final `raise ValueError(f"{sub} unexpected ...")` fires because the validator only whitelists `warnings`/`findings`. Analysis fails with `server_error`.
**Why it happens:** Reports route through OWN scoped validators (firestore_admin.py:794-799), NOT the generic flat validator. The scoped validators are deliberately strict (whitelist-only).
**How to avoid:** Extend `_validate_force_pattern_inference` to whitelist `coachCommentHook` and delegate to `_validate_flat_dict_no_nested_array`. Note the **asymmetry**: `body_comparison_report` uses the GENERIC validator (firestore_admin.py:780), which already accepts a flat dict — so BodyComparisonReport may need no validator change. Test BOTH paths.
**Warning signs:** Pipeline `fail_analysis(server_error)`; `TypeError`/`ValueError` mentioning `forcePatternInference.coachCommentHook` in logs.

### Pitfall 2: list[dict] inside the hook trips the nested-array gate
**What goes wrong:** Modeling `openQuestionsForCoach` as `list[{question, jointHint}]` (list[dict]) → inside a report that's itself a list[dict] entry context, `_validate_dict_only_scalars` rejects nested structures.
**Why it happens:** [[firestore-nested-array-flat]] — Firestore forbids nested arrays; the validator enforces list elements be scalar or flat-scalar-dict only.
**How to avoid:** Keep `openQuestionsForCoach` / `suggestedCues` as `list[str]`. If structured questions are needed later, that's a v2 schema change.
**Warning signs:** `TypeError ... must be scalar (firestore-nested-array-flat ...)`.

### Pitfall 3: 3-way lockstep drift
**What goes wrong:** Adding the field to analysis.ts but not models.py/contract.md (or vice-versa) → app expects a field backend never writes, or backend writes a shape app can't read.
**Why it happens:** Three files intentionally mirror each other (CLAUDE.md Cross-cutting); easy to edit one.
**How to avoid:** Single atomic commit touching all three (precedent: Phase 9 D-09-U1). models.py re-exports the dataclass from the analysis module (pattern at models.py:271, :307, :328).
**Warning signs:** TS `tsc --noEmit` passes but runtime field missing; or backend test asserts a key the contract doesn't list.

### Pitfall 4: Gemini mints a number/judgment and it ships
**What goes wrong:** LLM emits "무릎이 87° 정도로 보입니다" or "자세가 훌륭합니다" → violates D-04 objectivity + FEED-03 (강사 대체 인상).
**Why it happens:** LLMs hallucinate measurements; prompt alone is insufficient.
**How to avoid:** Two layers — (1) prompt forbids it (reuse `_COACH_SYSTEM_INSTRUCTION` clause), (2) call `guardrails._enforce_no_reject_patterns(raw_text, context="coach_hook")` → on ValueError, fall back to canned hook (D-08). Do NOT sanitize-and-emit (D-05).
**Warning signs:** Forbidden-pattern unit test fails on golden fixtures; guard ValueError in logs.

### Pitfall 5: Hook generation adds a second LLM round-trip  [PARTIALLY SUPERSEDED — single hook call is fine; it is a SEPARATE text-only writer, NOT the dual-track joint call. See banner item 3]
**What goes wrong:** Generating the hook in a SEPARATE Gemini call doubles latency/cost and breaks D-03 "1회 분석의 기존 LLM 호출 경로에 통합".
**Why it happens:** Naively adding `write_report_hook` as an independent call.
**How to avoid:** D-03 says integrate into the existing call path sharing `_build_coach_context`. Either (a) extend the existing coach call's output schema to also return hook fields, or (b) accept one additional call ONLY if pilot scale makes it negligible — but prefer single-call. Confirm with planner; this is the main open design choice.
**Warning signs:** Two Gemini invocations per analysis in logs; latency regression.

### Pitfall 6: SAM native-deps build skipped after shared-layer change
**What goes wrong:** Editing `sunity_shared` and deploying without `--use-container` → ImportError on Lambda Linux.
**Why it happens:** Mac-native binaries fail on Lambda ([[sam-build-native-deps]]).
**How to avoid:** `sam build --use-container` (Docker Desktop on). Pure-Python additions are low-risk but follow the project rule.
**Warning signs:** Lambda ImportError post-deploy.

## Code Examples

### Reuse the objectivity runtime guard (D-05 enforcement layer 2)
```python
# Source: backend/shared/python/sunity_shared/gemini/guardrails.py:47 (verified)
from sunity_shared.gemini.guardrails import _enforce_no_reject_patterns

def write_report_hook(self, context: dict) -> dict:
    if self._client is None:
        return {}  # D-08 graceful → assemble fills canned hook
    raw = self._call_gemini(context)  # text-only prompt
    try:
        _enforce_no_reject_patterns(raw, context="coach_hook")  # score/coord/judgment → ValueError
    except ValueError:
        log.warning("coach hook objectivity guard tripped — canned fallback")
        return {}  # NOT sanitize-and-emit (D-05)
    return self._parse_hook(raw)
```

### Scoped-validator extension (firestore_admin)
```python
# Source pattern: backend/shared/python/sunity_shared/firestore_admin.py:389-401 (verified)
if key == "findings":
    ...
    continue
if key == "coachCommentHook":            # Phase 11 add
    _validate_flat_dict_no_nested_array(value, path=sub)  # accepts flat dict + list[str]
    continue
raise ValueError(f"{sub} unexpected list at forcePatternInference top-level ...")
```

### Forbidden-phrase unit test (D-05 — golden finding → 0 forbidden patterns)
```python
# Source pattern: backend/tests/phase09/test_force_pattern_copy_no_forbidden.py (verified)
import pytest
_FORBIDDEN = ("점", "/10", "좌표", "x=", "y=", "잘했다", "훌륭", "완벽", "양호")  # extend per guardrails

@pytest.mark.parametrize("phrase", _FORBIDDEN)
def test_hook_text_has_no_forbidden(phrase):
    hook = build_canned_hook(GOLDEN_FINDING)  # or mock-LLM golden output
    blob = hook.auto_findings_summary + " ".join(hook.open_questions_for_coach) + " ".join(hook.suggested_cues)
    assert phrase not in blob, f"금지 표현 '{phrase}' in hook: {blob!r}"
```

### App read-side null guard (backward compat)
```typescript
// Source pattern: app/src/app/analysis/result.tsx:525 (verified — forcePatternInference guard)
const openQuestions = result.forcePatternInference?.coachCommentHook?.openQuestionsForCoach ?? [];
// render "강사에게 확인할 점" only if openQuestions.length > 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Gemini coach = joint-level only (`detail2`) | + report-level `CoachCommentHook` (this phase) | Phase 11 | Adds coach-collaboration data layer above per-joint coaching. Coexist (D-01). |
| Cerebras-only coaching | Dual-track (Gemini + Cerebras, GEMINI_COACH_ENABLED) | Phase 13-C / 17-04 | Hook generation rides the existing Gemini path. |
| Cerebras `llama3.1-8b` | `gpt-oss-120b` (Cerebras) | 2026-06-06 (deprecation) | If hook uses Cerebras fallback, model = `gpt-oss-120b`. [VERIFIED: coach_writer.py:149] |
| Gemini 2.5 / plain Pro | `gemini-3.1-pro-preview` (suffix req.) / `gemini-3.5-flash` | current | `resolve_model` raises on stale strings. [[gemini-latest-model-versions]] |

**Deprecated/outdated:** Do not call Gemini 2.5 or `gemini-3.1-pro` (no `-preview`) — 404. Do not use `llama3.1-8b` on Cerebras — 404.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Single LLM-call integration is preferable to a second round-trip for hook generation (D-03 "기존 LLM 호출 경로에 통합"). The exact mechanism (extend existing call's schema vs. one extra cheap call) is a planner decision. | Pitfall 5 | If a second call is acceptable at pilot scale, simpler code; if not, schema extension needed. Low risk — both honor D-03 intent; confirm with planner. |
| A2 | `BodyComparisonReport` storage routes through the GENERIC `_validate_flat_dict_no_nested_array` (firestore_admin.py:780) and may need no scoped-validator change, while `ForcePatternInference` (scoped validator) does. | Pattern 4 / Pitfall 1 | If body path is actually scoped elsewhere, validator change needed there too. Verified at firestore_admin.py:779-799 — body uses generic, force uses scoped. Confirm no later override. |
| A3 | Recommended hook field shape (`list[str]` for openQuestionsForCoach/suggestedCues, nullable coach_comment/reviewed_by) satisfies COACH-01 while staying nested-array-safe. CONTEXT marks detailed schema as Claude's discretion. | Pattern 2 | Wrong shape → nested-array reject. Mitigated by keeping lists scalar. User confirmation not required (discretion), but verify against Firestore on first write. |
| A4 | No new env-var toggle is required (hook rides `GEMINI_COACH_ENABLED` path). | Runtime State Inventory | If product wants independent hook toggle, add following `_VISION_ENV_DEFAULTS` pattern. Trivial. |

**If this table is non-empty:** A1/A2/A4 are design choices the planner should lock; A3 is discretion-validated. None block planning.

## Open Questions

1. **Single-call vs. separate hook-generation call (the one real design fork).**
   - What we know: D-03 mandates reuse of `GeminiCoachWriter` + `_build_coach_context` and "integration into the existing 1-analysis LLM call path."
   - What's unclear: whether the existing coach call's response schema is extended to also carry hook fields, or a dedicated `write_report_hook` makes a second (cheap, text-only) call.
   - Recommendation: Prefer extending output schema (single call) for cost/latency; if schema coupling is awkward, a single extra text-only call at pilot scale is acceptable. Planner decides; both satisfy D-03.

2. **Hook attachment timing in `_process`.**
   - What we know: reports are built at force_pattern (app.py:2099) and body_comparison (app.py:1776+) sites; coach call sits at app.py:1945-2026 (before `build_result`).
   - What's unclear: whether hook generation runs once (shared context) and attaches to both reports, or per-report.
   - Recommendation: Generate once from shared context, attach a per-report hook instance (D-02 keeps per-report provenance via a `source_report` scalar). Avoids double LLM cost.

3. **autoFindingsSummary / suggestedCues content character (length, cue count).**
   - What we know: CONTEXT marks this Claude's discretion.
   - Recommendation: summary = 1 short paragraph; suggestedCues = 2–4 items; openQuestionsForCoach = 1–3 items (example: "왼쪽 무릎 굽힘이 의도된 동작인지 강사와 확인"). Keep terse — student carries to instructor.

## Environment Availability

> Phase 11 is code/config-only on top of existing infra. No NEW external dependency.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Gemini API key (Parameter Store / Pod env) | AI hook text generation | Existing (Phase 13-C/17 wired) | — | D-08 canned fallback (analysis still completes) |
| Cerebras key (`CEREBRAS_KEY_PARAM`) | Dual-track fallback writer | Existing | gpt-oss-120b | D-08 canned fallback |
| Firestore Admin (firebase-admin) | Hook persistence | Existing | >=6,<7 | — (required, already present) |
| SAM CLI + Docker (`--use-container`) | Shared-layer redeploy | Existing dev workflow | — | — |
| `tsc --noEmit` | App type gate | Existing (`npm run typecheck`) | TS ~5.9 | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None new — real LLM E2E is deferred to Phase 15 实证 (CONTEXT code_context). v1 can complete via canned fallback without live keys.

## Validation Architecture

> nyquist_validation ENABLED (config has no explicit false). This section drives VALIDATION.md, focused on D-05 translation-only enforcement + D-08 fallback.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (`backend/requirements-dev.txt`) for backend; `tsc --noEmit` (`npm run typecheck`) for app (no JS test runner). |
| Config file | none committed (pytest discovers `backend/tests/`); app has no jest/vitest. |
| Quick run command | `cd backend && python -m pytest tests/phase11 -x -q` |
| Full suite command | `cd backend && python -m pytest -q` then `cd app && npm run typecheck` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COACH-01 | CoachCommentHook attaches to both reports; serializes flat (no nested array) | unit | `python -m pytest tests/phase11/test_coach_hook_nested_array.py -x` | ❌ Wave 0 |
| COACH-01 | TS↔Python↔contract shapes mirror; app null-guard compiles | typecheck | `cd app && npm run typecheck` | n/a (existing gate) |
| FEED-03 / D-04 | Golden finding → hook text has 0 score/coord/judgment patterns | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py -x` | ❌ Wave 0 |
| FEED-03 / D-04 | Runtime guard rejects LLM-minted number/judgment (mock LLM emits "87점"/"훌륭" → ValueError → canned fallback) | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py::test_guard_rejects -x` | ❌ Wave 0 |
| ROADMAP #5 / D-08 | Key unset (`_client is None`) → canned hook returned, analysis completes (status done) | unit | `python -m pytest tests/phase11/test_coach_hook_fallback.py -x` | ❌ Wave 0 |
| D-06 | openQuestionsForCoach renders; autoFindingsSummary/suggestedCues stored-not-displayed; coachComment/reviewedBy null in v1 | typecheck + manual | `npm run typecheck` (+ manual UI verify, deferred E2E Phase 15) | manual |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/phase11 -x -q`
- **Per wave merge:** `python -m pytest -q` (full backend) + `cd app && npm run typecheck`
- **Phase gate:** Full backend suite green + `tsc --noEmit` clean before `/gsd-verify-work`. Real-LLM E2E explicitly deferred to Phase 15 (CONTEXT).

### Wave 0 Gaps
- [ ] `backend/tests/phase11/test_coach_hook_translation_only.py` — golden finding fixtures + mock-LLM forbidden-output cases (covers COACH-01/FEED-03/D-04/D-05). Pattern from `tests/phase09/test_force_pattern_copy_no_forbidden.py`.
- [ ] `backend/tests/phase11/test_coach_hook_fallback.py` — `_client is None` → canned hook; assert analysis completes (D-08).
- [ ] `backend/tests/phase11/test_coach_hook_nested_array.py` — assert scoped validators pass a valid flat hook AND reject a `list[dict]`/nested-list hook (covers Pitfall 1+2).
- [ ] `backend/tests/phase11/conftest.py` — shared golden `ForcePatternFinding`/`BodyComparisonFinding` fixtures.
- [ ] No framework install needed (pytest already present).

## Security Domain

> `security_enforcement` not set to false → included. Phase 11 is text/data-layer with no new auth surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new auth; existing Firebase anonymous + ID-token verify unchanged. |
| V3 Session Management | no | Unchanged. |
| V4 Access Control | yes (minor) | Hook is read-only student data under `users/{uid}/analyses/{id}` — existing Firestore rules already scope by uid. v2 coach `reviewedBy`/`coachComment` write path is OUT OF SCOPE (no write surface added now). |
| V5 Input Validation | yes | LLM output is untrusted: `guardrails._enforce_no_reject_patterns` (objectivity) + Firestore scoped validator (nested-array/type). App side defensive-normalize on read (precedent `userAnalyses.ts`). |
| V6 Cryptography | no | No new crypto. Secrets stay in Parameter Store (no `.env` hardcode — CLAUDE.md §3). |

### Known Threat Patterns for {Gemini text-gen + Firestore data layer}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM emits fabricated score/coordinate/judgment (objectivity violation → false trust) | Tampering / Repudiation | Prompt constraint + `_enforce_no_reject_patterns` reject-and-fallback + forbidden-phrase unit test (D-04/D-05). |
| LLM prompt-injection via finding text bleeds numbers into prose | Tampering | Hook consumes structured finding fields, not free user text; guard is output-side. |
| Malformed/oversized hook breaks Firestore write or app render | DoS | Scoped validator rejects bad shapes → `fail_analysis`; app null-guards on read. |
| Secret leakage of Gemini/Cerebras keys | Information Disclosure | Keys in Parameter Store only; lazy import; no key in logs (existing pattern). |
| v2 coach-write fields exposed prematurely | Elevation of Privilege | `coachComment`/`reviewedBy` are null read-only in v1; NO write endpoint added (COACH-01 "UI/입력은 v2"). |

## Project Constraints (from CLAUDE.md)

- **No emojis** anywhere in code or output (CLAUDE.md §7).
- **Korean for user-facing copy and most comments;** identifiers/code in English (Cross-cutting).
- **Contract-first 3-way lockstep:** `app/src/types/analysis.ts` ↔ `backend/.../models.py` ↔ `docs/contract.md` change together (Cross-cutting; CLAUDE.md §3 infra separation N/A here).
- **Secrets in AWS Parameter Store** — no `.env` hardcode (CLAUDE.md §3).
- **App UI:** brand `#FF4B33` immutable; Pretendard; light theme only (no dark bg); theme tokens only — hardcoding colors/spacing forbidden (app/CLAUDE.md, design.md). UI = Figma-first ([[ui-figma-first]], fileKey jrdI7kp245HkPfLB0nclsz) — verify result-screen copy/section against Figma before finalizing.
- **Small-unit work; meaningful tests only; no slop/number-filler** (CLAUDE.md §7).
- **`sam build --use-container`** mandatory for backend shared-layer changes ([[sam-build-native-deps]]).
- **Objectivity charter** ([[analysis-objectivity-no-human-scores]]): no human-score ground truth; LLM emits no scores/judgments — directly governs D-04/D-05.
- **Firestore nested-array ban** ([[firestore-nested-array-flat]], [[firestore-index-entry-limit]]): flat list[scalar]; reshape on read.
- **"수치는 보조, 원인이 핵심"** (PROJECT core value): hook prose explains cause, numbers come from engine only.

## Sources

### Primary (HIGH confidence — repo verification)
- `backend/functions/pipeline/app.py` — `_build_coach_context` (:798), dual-track coach call site (:1945-2026), `_dataclass_to_camel_case_dict` (:1482), report assembly (force_pattern :2099, body_comparison :1776+).
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` — `GeminiCoachWriter`, `_COACH_SYSTEM_INSTRUCTION` objectivity clause, `.write` B3 signature.
- `backend/shared/python/sunity_shared/gemini/guardrails.py:47` — `_enforce_no_reject_patterns` (score/coord/judgment regex).
- `backend/shared/python/sunity_shared/analysis/coach_writer.py:145,178` — Cerebras graceful no-op (`_client is None → {}`), `gpt-oss-120b`.
- `backend/shared/python/sunity_shared/analysis/force_pattern.py:228` — `ForcePatternInference` frozen dataclass (field-order rule).
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:862` — `BodyComparisonReport` frozen dataclass.
- `backend/shared/python/sunity_shared/firestore_admin.py:45,343,724,780,794` — generic + scoped validators, `complete_analysis`.
- `app/src/types/analysis.ts:181,198,317,851,908,1056,1174` — CoachingTip/Detail, AnalysisResult, ForcePatternInference, BodyComparisonReport, Phase 11 boundary comments (:186,:345).
- `backend/tests/phase09/test_force_pattern_copy_no_forbidden.py`, `backend/tests/phase13/test_branch2_forbidden_phrase_gate.py` — forbidden-phrase test patterns.
- `docs/contract.md:464,725,1134,1177` — §8 BodyComparisonReport, §9.11 ForcePatternInference, "AI = 강사 보조 도구", Phase 11 책임 경계.
- `.planning/REQUIREMENTS.md` (COACH-01, FEED-02 Complete, FEED-03), `.planning/phases/11-coachcommenthook-gemini/11-CONTEXT.md` (D-01..D-08).

### Secondary (MEDIUM)
- Memory: [[firestore-nested-array-flat]], [[firestore-index-entry-limit]], [[analysis-objectivity-no-human-scores]], [[gemini-latest-model-versions]], [[sam-build-native-deps]], [[section-dual-coach-report]], [[field-research-stakeholders]].

### Tertiary (LOW)
- None — no WebSearch needed; phase is fully internal.

## Metadata

**Confidence breakdown:**
- Standard stack (in-repo assets): HIGH — every asset read directly in the repo this session.
- Architecture (patterns, validator paths): HIGH — verified exact line numbers and validator branch behavior; the scoped-vs-generic asymmetry (A2) is the one item to re-confirm at attach time.
- Pitfalls: HIGH — pitfalls derived from actual validator reject branches and project memory landmines.
- Open design fork (single vs second LLM call): MEDIUM — both options honor D-03; planner decision.

**Research date:** 2026-06-16
**Valid until:** 2026-07-16 (stable internal code; re-verify if `coach_writer_v2.py` / `firestore_admin.py` validators change before planning).
