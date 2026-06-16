# Phase 11: CoachCommentHook + Gemini 자연어 번역만 - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 11 (8 modified + 1 optional new module + 3 new test files)
**Analogs found:** 11 / 11 (every integration point already exists in-repo — pattern-replication, not greenfield)

> **3-way lockstep mandate (CLAUDE.md Cross-cutting):** `app/src/types/analysis.ts` ↔ `backend/.../models.py` (re-export) ↔ `docs/contract.md` MUST change in one atomic commit. Planner: assign all three to the same plan/wave.

---

## ⚠️ LANDMINE — Asymmetric Firestore validator (read first)

The two reports persist through **different** validators. `coachCommentHook` attached to each report hits a different gate:

| Report | Validator | Whitelist behavior | Phase 11 action |
|--------|-----------|--------------------|-----------------|
| `ForcePatternInference` | **scoped** `_validate_force_pattern_inference` (`firestore_admin.py:343`, called at `:794-799`) | Whitelist-only — `warnings`/`findings` ONLY. Any other top-level key → `raise ValueError(f"{sub} unexpected ...")` at `:398-404` | **MUST extend** — add a `key == "coachCommentHook"` branch delegating to `_validate_flat_dict_no_nested_array` |
| `BodyComparisonReport` | **generic** `_validate_flat_dict_no_nested_array` (called at `firestore_admin.py:780`) | Accepts any flat dict + `list[str]` | **Likely NO change** — verify on first write |

Verified at `firestore_admin.py:794-799` (scoped) vs `:780` (generic). The scoped validator's terminal `raise ValueError(f"{sub} unexpected type...")` (`:402-404`) is the exact branch that fails the analysis with `server_error` if you skip the extension. Test BOTH paths.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/src/types/analysis.ts` | data-contract (TS) | transform | same file — `ForcePatternInference` L908, `BodyComparisonReport` L1174, optional report fields on `AnalysisResult` L334-354 | exact (in-file precedent) |
| `backend/shared/python/sunity_shared/models.py` | data-contract (Python re-export) | transform | same file — re-export block L271-277 | exact (in-file precedent) |
| `docs/contract.md` | data-contract (docs) | — | §8 BodyComparisonReport / §9.11 ForcePatternInference | exact |
| `backend/shared/.../analysis/force_pattern.py` | model (frozen dataclass) | transform | `ForcePatternInference` L228 (this file) | exact |
| `backend/shared/.../analysis/body_normalizer.py` | model (frozen dataclass) | transform | `BodyComparisonReport` L861 (this file) | exact |
| `backend/shared/.../analysis/coach_hook.py` (NEW, opt) | model + util (canned fallback) | transform | `CoachingCause`/dataclass pattern + `coach_writer.py` no-op | role-match |
| `backend/shared/.../gemini/coach_writer_v2.py` | service / ML adapter | request-response (LLM) | `GeminiCoachWriter.write` L388 (this file) | exact |
| `backend/shared/.../gemini/guardrails.py` | util (guard) | transform | `_enforce_no_reject_patterns` L47 (reuse as-is, no edit) | exact |
| `backend/shared/.../firestore_admin.py` | service (persistence validator) | CRUD | `_validate_force_pattern_inference` L343 | exact |
| `backend/functions/pipeline/app.py` | controller (orchestration) | event-driven (SQS) | dual-track coach call site L1957-2026 | exact |
| `app/src/app/analysis/result.tsx` | component (screen) | request-response (render) | force-pattern section render L524-538 / L779-794 | exact |
| `backend/tests/phase11/*` | test | — | `phase09/test_force_pattern_copy_no_forbidden.py`, `phase13/test_branch2_forbidden_phrase_gate.py` | exact |

---

## Pattern Assignments

### `app/src/types/analysis.ts` (data-contract, TS) + `models.py` + `contract.md`

**Analog (TS report interface to mirror):** `ForcePatternInference` L908-920, `BodyComparisonReport` L1174-1199.

**New `CoachCommentHook` interface** — model on the existing optional-field convention. Add `coachCommentHook?: CoachCommentHook | null` to BOTH report interfaces. List fields are `string[]` ONLY (nested-array ban — see Pattern 2 below).

**Optional-nullable field precedent** (backward compat — old docs lack the field, app null-guards on read). From `AnalysisResult` L334-354:
```typescript
// Phase 6 (Plan 06-01) — D-06-B3. 체형 정규화 비교 리포트.
// Plan 06-02 wiring 에서 backend pipeline 이 채움 (currently nullable).
bodyComparisonReport?: BodyComparisonReport | null;
...
// 옵셔널 — 이전 빌드 doc 호환 (dimensionExplanation 패턴).
recommendedExercises?: RecommendedExercise[];
```

**DO NOT TOUCH** `CoachingTipDetail` (L198) / `detail2` (L181) — D-01 coexist, zero 13 rework. Note the existing comment at L186/L345 already documents the Phase 11 boundary ("Phase 11 CoachCommentHook ... findings[].interpretation 위 LLM 자연어 풍부화") — read it, do not interpret it as a merge instruction.

**Python re-export precedent** (`models.py` mirrors the dataclass from the analysis module — do NOT redefine):
```python
# models.py:271-277 (verified) — file-bottom re-export pattern
from .analysis.body_normalizer import (  # noqa: E402 — 파일 하단 re-export 패턴
    BodyComparisonFinding,
    BodyComparisonReport,
    ...
)
# 변경 시 TS + docs/contract.md §8 ... 동시 갱신 (CLAUDE.md Cross-cutting).
```
Add `CoachCommentHook` to the import-and-reexport block from wherever the dataclass is defined (recommend a shared `coach_hook.py` so both reports import one definition).

---

### `backend/shared/.../analysis/force_pattern.py` + `body_normalizer.py` (model, frozen dataclass)

**Analog:** `ForcePatternInference` L228-252 (force_pattern.py), `BodyComparisonReport` L861-883 (body_normalizer.py).

**Field-order rule (Python dataclass — non-default → default):** add the hook as a nullable field at the END. Precedent — `ForcePatternInference.warnings` is the trailing `field(default_factory=...)`:
```python
# force_pattern.py:248-252 (verified)
    version: str
    findings: list[ForcePatternFinding]
    overall_confidence: MetricConfidence
    mode_context: ModeContext
    warnings: list[str] = field(default_factory=list)
    # Phase 11: add AFTER all non-default fields →
    # coach_comment_hook: CoachCommentHook | None = None
```
```python
# body_normalizer.py:875-883 (verified) — already has many trailing defaults
    used_reference_fallback: bool = False
    # Phase 11: add coach_comment_hook: CoachCommentHook | None = None at end
```

**Validation precedent** — both dataclasses use `__post_init__` strict checks (`force_pattern.py:254+`, `body_normalizer.py:842+`). If `CoachCommentHook` is a frozen dataclass it should mirror this: validate `open_questions_for_coach`/`suggested_cues` are `list[str]` of non-empty strings (precedent `ForcePatternInference.__post_init__` warnings loop, `force_pattern.py:215-225`).

**Pattern 2 — flat hook (list[str] ONLY):**
```python
@dataclass(frozen=True)
class CoachCommentHook:
    auto_findings_summary: str          # text only — stored, NOT displayed v1
    open_questions_for_coach: list[str] # ["왼쪽 무릎 굽힘이 의도된 동작인지 강사와 확인", ...] — v1 displayed
    suggested_cues: list[str]           # stored, NOT displayed v1
    coach_comment: str | None = None    # v2 — null in v1
    reviewed_by: str | None = None      # v2 — null in v1
    # source_report: str | None = None  # optional scalar for v2 console aggregation (D-02 provenance)
```
NEVER `list[dict]` — trips the nested-array gate. If structured questions are wanted later, that is a v2 schema change.

---

### `backend/shared/.../gemini/coach_writer_v2.py` (service / ML adapter, request-response)

**Analog:** `GeminiCoachWriter` class L350, `.write(context: dict) -> dict` L388, `_COACH_SYSTEM_INSTRUCTION` L139 (objectivity clause), wired into prompt at L189.

**Pattern 3 — TEXT-ONLY method sharing context.** Add `write_report_hook(context: dict) -> dict` consuming the SAME `_build_coach_context` output (D-03). Reuse the existing objectivity system-prompt clause (`_COACH_SYSTEM_INSTRUCTION`, L139) — it already forbids 점수/등급/좌표/판정 vocabulary. Two-layer enforcement (D-05): prompt + runtime guard (next section).

**Graceful no-op precedent** (D-08 — `coach_writer.py:178`, same in both writers):
```python
# coach_writer.py:178 (verified)
def write(self, context: dict) -> dict:
    ...
    if self._client is None:
        return {}   # key unset → assemble fills canned hook
```
`write_report_hook` MUST follow this: `if self._client is None: return {}`.

**Model string:** if calling Gemini directly, route through `gemini.config.resolve_model` (NEVER hardcode `"gemini-3.1-pro-preview"`). Cerebras fallback model = `gpt-oss-120b` (`coach_writer.py:149`); `llama3.1-8b` is 404-deprecated.

---

### `backend/shared/.../gemini/guardrails.py` (util — REUSE, no edit)

**Analog:** `_enforce_no_reject_patterns` L47 — reuse AS-IS. Do not add a new scanner.

```python
# guardrails.py:47 (verified) — score/coord/judgment regex → ValueError (reject-and-fallback)
def _enforce_no_reject_patterns(text: str, *, context: str, allow_coords: bool = False) -> None:
    ...  # _SCORE_PATTERNS (\d+점, \d+/\d+) + _COORDINATE_PATTERNS (좌표, x=, y=)
         # + _JUDGMENT_PATTERNS (잘했다, 훌륭, 완벽) → raise ValueError
```

**Usage (D-05 — reject-and-fallback, NOT runtime sanitize):**
```python
raw = self._call_gemini(context)
try:
    _enforce_no_reject_patterns(raw, context="coach_hook")  # default allow_coords=False
except ValueError:
    log.warning("coach hook objectivity guard tripped — canned fallback")
    return {}   # D-08 — NEVER regex-strip-and-emit (D-05 forbids)
```
For the hook, leave `allow_coords=False` (default) — the hook is prose for students, no coordinates allowed.

---

### `backend/shared/.../firestore_admin.py` (service, CRUD) — ⚠️ LANDMINE

**Analog:** `_validate_force_pattern_inference` L343-404. The rejecting branch is L398-404.

**Pattern 4 — extend the scoped validator** (force_pattern path ONLY). Add a `coachCommentHook` whitelist branch BEFORE the terminal raise:
```python
# firestore_admin.py:389-401 (verified) — the branch to extend
        if key == "findings":
            ...
            continue
        # Phase 11 — add ABOVE the terminal raise:
        if key == "coachCommentHook":
            _validate_flat_dict_no_nested_array(value, path=sub)  # flat dict + list[str] OK
            continue
        raise ValueError(
            f"{sub} unexpected list at forcePatternInference top-level ..."  # L398
        )
```
Note the value type: `coachCommentHook` serializes to a `dict`, so it also has to survive the `isinstance(value, dict)` branch at L371-374 which currently `raise`s on ANY nested dict. The whitelist branch for `coachCommentHook` must be added in the dict-handling path too (delegate to `_validate_flat_dict_no_nested_array`). **Verify the exact branch order at implementation time.**

`bodyComparisonReport` routes through the GENERIC validator (`:780`) which already accepts flat dict + `list[str]` → likely no change, but write-test it (Assumption A2).

---

### `backend/functions/pipeline/app.py` (controller, event-driven)

**Analogs:**
- `_build_coach_context(...)` call — L1945-1956 (shared context, D-03 reuses this exact dict).
- 13-C dual-track coach call site — L1957-2026 (where hook generation hooks in; runs once, attaches per-report).
- `_dataclass_to_camel_case_dict` — L1482-1502 (serialize the hook dataclass → camelCase Firestore dict; 5-case helper already handles dataclass/Enum/list/dict/scalar).
- Report assembly sites — force_pattern ~L2099, body_comparison ~L1776+ (attach `coach_comment_hook` to each report before `build_result`/`complete_analysis`).

**Reuse the exact context build (D-03):**
```python
# pipeline/app.py:1945 (verified) — shared by both writers; reuse for the hook
coach_context = _build_coach_context(
    mode=mode, assessments=assessments, dim_scores=dimension_scores,
    local_video_path=local_video_path, scene_flags=scene_result,
    branch_info=branch_info, body_profile=models.normalize_body_profile(...),
)
```

**Integration point (Pitfall 5 — single round-trip):** the dual-track block at L1963-2026 already calls `_call_coach_writer_with_retry("gemini", _ensure_gemini_coach_writer().write, coach_context)`. Generate the hook in the SAME path sharing `coach_context` — either extend that call's output schema or add `write_report_hook` on the same writer/context. Do NOT add an independent second Gemini round-trip (breaks D-03 "1회 분석의 기존 LLM 호출 경로에 통합").

**Serialize precedent (L1493):**
```python
if dataclasses.is_dataclass(obj):
    raw = dataclasses.asdict(obj)
    return {_snake_to_camel(k): _dataclass_to_camel_case_dict(v) for k, v in raw.items()}
```
The hook dataclass passes through this unchanged → `coachCommentHook: {autoFindingsSummary, openQuestionsForCoach[], suggestedCues[], coachComment, reviewedBy}`.

---

### `app/src/app/analysis/result.tsx` (component, render — light theme, tokens only)

**Analog:** force-pattern section render L524-538 (null-guard) + L779-794 (card section), mode1 reference label `styles.refName` L684 (positioning-copy site).

**Pattern 5 — null-guarded read + read-only section (D-06).** Mirror the `?? []` guard:
```typescript
// result.tsx:525 (verified) — guard precedent
const list = result.forcePatternInference?.findings ?? [];
// Phase 11 →
const openQuestions = result.forcePatternInference?.coachCommentHook?.openQuestionsForCoach
  ?? result.bodyComparisonReport?.coachCommentHook?.openQuestionsForCoach ?? [];
// render "강사에게 확인할 점" only if openQuestions.length > 0
```

**Section render precedent** (`sectionTitle` + `styles.card`, theme tokens only — L779):
```tsx
<Text style={styles.sectionTitle}>실패 원인 후보</Text>   {/* L779 */}
<View style={styles.card}> ... </View>
```
New "강사에게 확인할 점" section follows this exact shape. **Theme tokens ONLY** — `colors.brand` (#FF4B33), `colors.cardBg`, `spacing.cardPadding`, `colors.divider` (styles block L1034+). Hardcoding colors/spacing forbidden (`app/CLAUDE.md`).

**Positioning copy (D-07):** top 1-liner ("이 분석은 강사 지도를 돕는 참고예요") + coach-section header. "기준 모션은 하나의 참고일 뿐" near the mode1 reference label `styles.refName` (`result.tsx:684`, inside the `refCard` block L677-684). Verify copy against Figma (fileKey jrdI7kp245HkPfLB0nclsz) before finalizing ([[ui-figma-first]]).

**v1 exposure (D-06):** ONLY `openQuestionsForCoach` renders. `autoFindingsSummary`/`suggestedCues` stored-not-displayed. `coachComment`/`reviewedBy` null in v1.

---

### `backend/tests/phase11/*` (test)

**Analogs:** `backend/tests/phase09/test_force_pattern_copy_no_forbidden.py` (AST forbidden-phrase grep gate), `backend/tests/phase13/test_branch2_forbidden_phrase_gate.py`.

**Forbidden-phrase test precedent** (`phase09/test_force_pattern_copy_no_forbidden.py:1-30`): imports `FORBIDDEN_PHRASES_*` tuples, walks string constants via `ast`, `@pytest.mark.parametrize` over the forbidden tuple. Replicate for D-05 "번역만":
```python
_FORBIDDEN = ("점", "/10", "좌표", "x=", "y=", "잘했다", "훌륭", "완벽", "양호")  # align to guardrails

@pytest.mark.parametrize("phrase", _FORBIDDEN)
def test_hook_text_has_no_forbidden(phrase):
    hook = build_canned_hook(GOLDEN_FINDING)
    blob = hook.auto_findings_summary + " ".join(hook.open_questions_for_coach) + " ".join(hook.suggested_cues)
    assert phrase not in blob
```

**Three new test files (Wave 0):**
- `test_coach_hook_translation_only.py` — golden finding → 0 forbidden patterns + `test_guard_rejects` (mock LLM emits "87점"/"훌륭" → ValueError → canned fallback).
- `test_coach_hook_fallback.py` — `_client is None` → canned hook, analysis completes (D-08).
- `test_coach_hook_nested_array.py` — scoped validator PASSES a flat hook AND REJECTS a `list[dict]`/nested-list hook (covers Pitfall 1+2, BOTH report paths).
- `conftest.py` — shared golden `ForcePatternFinding`/`BodyComparisonFinding` fixtures.

Run: `cd backend && python -m pytest tests/phase11 -x -q`; full gate adds `cd app && npm run typecheck`.

---

## Shared Patterns

### Objectivity runtime guard
**Source:** `backend/shared/.../gemini/guardrails.py:47` (`_enforce_no_reject_patterns`)
**Apply to:** Every LLM text field in the hook (coach_writer_v2 `write_report_hook`). Reject-and-fallback (raise → canned), NEVER sanitize-and-emit (D-05).

### Graceful no-op fallback
**Source:** `backend/shared/.../analysis/coach_writer.py:178` (`if self._client is None: return {}`)
**Apply to:** `write_report_hook` + assembly (D-08 — analysis NEVER fails on missing key; canned hook fills in).

### Frozen-dataclass field-order + `__post_init__` validation
**Source:** `force_pattern.py:228-252` (trailing `field(default_factory)`), `:215-225` (list[str] strict loop)
**Apply to:** `CoachCommentHook` + the new nullable field on both reports (default `= None` at END).

### dataclass → camelCase Firestore dict
**Source:** `pipeline/app.py:1482` (`_dataclass_to_camel_case_dict`)
**Apply to:** Hook serialization in pipeline assembly. No manual key conversion.

### Scoped nested-array validator
**Source:** `firestore_admin.py:343` (force) — extend; `:780` (generic, body) — likely reuse unchanged
**Apply to:** Both report persistence paths. ⚠️ asymmetric — see LANDMINE.

### 3-way contract lockstep
**Source:** `models.py:271-277` re-export + co-edit comment (`:270`)
**Apply to:** `analysis.ts` ↔ `models.py` ↔ `contract.md` — single atomic commit.

---

## No Analog Found

None. Every integration point has an exact in-repo precedent. The only NEW artifacts are:

| File | Role | Data Flow | Reason (not "no analog" — just new) |
|------|------|-----------|-------------------------------------|
| `backend/shared/.../analysis/coach_hook.py` (optional) | model | transform | New module recommended so both reports import ONE `CoachCommentHook` definition + share the canned-fallback builder. Dataclass pattern itself = `force_pattern.py` analog. |
| `backend/tests/phase11/*` | test | — | New dir; pattern = phase09/phase13 tests. |

---

## Metadata

**Analog search scope:** `backend/shared/python/sunity_shared/{analysis,gemini}/`, `backend/functions/pipeline/`, `app/src/types/`, `app/src/app/analysis/`, `backend/tests/phase09|13/`, `docs/contract.md`.
**Files scanned (read):** 11 source files + 2 context docs.
**Verified line numbers:** all analog excerpts read directly from repo this session (HIGH confidence).
**Open design fork (planner decides):** single-call schema extension vs. one extra text-only Gemini call for hook generation — both honor D-03 (RESEARCH Open Question 1 / Pitfall 5).
**Pattern extraction date:** 2026-06-16
