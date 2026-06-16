---
phase: 11-coachcommenthook-gemini
reviewed: 2026-06-17T00:00:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - app/src/app/analysis/result.tsx
  - app/src/lib/userAnalyses.ts
  - app/src/types/analysis.ts
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/body_normalizer.py
  - backend/shared/python/sunity_shared/analysis/coach_hook.py
  - backend/shared/python/sunity_shared/analysis/coach_hook_builder.py
  - backend/shared/python/sunity_shared/analysis/force_pattern.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/shared/python/sunity_shared/gemini/coach_hook_writer.py
  - backend/shared/python/sunity_shared/gemini/guardrails.py
  - backend/shared/python/sunity_shared/gemini/schemas.py
  - backend/shared/python/sunity_shared/models.py
  - backend/tests/phase11/__init__.py
  - backend/tests/phase11/conftest.py
  - backend/tests/phase11/test_coach_hook_fallback.py
  - backend/tests/phase11/test_coach_hook_nested_array.py
  - backend/tests/phase11/test_coach_hook_translation_only.py
  - docs/contract.md
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-06-17
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Phase 11 adds a text-only Gemini "CoachCommentHook" writer that produces "questions to ask
your coach", a per-report fallback resolver, a Firestore strict validator, and a result-screen
section that merges the two reports' questions. The contract lockstep (TS interface ↔ Python
dataclass ↔ models.py re-export ↔ docs §9.11.7) is consistent, the dedicated
`_validate_coach_comment_hook` correctly tightens the generic validator's list[dict] hole, the
serialization path (`_dataclass_to_camel_case_dict` → camelCase → scoped validator) round-trips
cleanly, and the number-free guard is correctly scoped so the global Vision guard does not
regress on "30도"/"50%". The app-side merge correctly concats both reports' questions (avoiding
the documented `??`-chain trap) and de-dupes. All 33 phase11 tests pass.

The central design promise — "the hook is best-effort and the analysis must never fail because
of it" (D-08 / ROADMAP SC#5) — is violated by one concrete crash path: a parseable-but-malformed
Gemini payload (empty/whitespace list item) bypasses the Pydantic schema and the guardrails, then
trips `CoachCommentHook.__post_init__`, and that `ValueError` propagates up to the pipeline's broad
`except`, failing the whole analysis with `server_error`. This is the BLOCKER. The remaining
findings are robustness gaps (unbounded/uncapped LLM lists, coupling of the body hook to force
signals, an unused deficit-code enum / invalid test fixture) and minor cleanups.

## Critical Issues

### CR-01: Malformed-but-parseable Gemini hook payload fails the entire analysis (`server_error`)

**File:** `backend/shared/python/sunity_shared/analysis/coach_hook_builder.py:202-221`
(propagates via `backend/functions/pipeline/app.py:2139-2143` → broad `except` at `:2404`)

**Issue:** `_payload_to_hook` reads the LLM's `open_questions_for_coach` / `suggested_cues`
lists and passes the items **straight into** `CoachCommentHook(...)` without filtering empty
or whitespace-only strings. `CoachCommentHook.__post_init__` → `_validate_str_list`
(`coach_hook.py:53-57`) raises `ValueError` on any empty string. This `ValueError` is raised
inside `resolve_coach_hook_bundle`, which the pipeline calls **outside** any local try/except;
it is therefore caught only by `_process`'s broad `except Exception` (`pipeline/app.py:2404`),
which calls `fail_analysis(server_error)`.

The Pydantic schema does not protect against this: `CoachCommentHookPayload.open_questions_for_coach`
is declared `list[str]` with **no per-item `min_length`** (`schemas.py:164-169`), so a JSON array
containing `""` validates successfully. The number-free guardrail also does not reject empty
strings. An empty/whitespace array element is an extremely common LLM output artifact (trailing
element, blank cue). Reproduced:

```
resolve_coach_hook_bundle(
  SimpleNamespace(force_pattern_inference=SimpleNamespace(
      auto_findings_summary='요약', open_questions_for_coach=['', '   '], suggested_cues=['큐']),
      body_comparison_report=None),
  force_findings=[], body_findings=[])
# -> ValueError: open_questions_for_coach[0] must be non-empty str, got str=''
```

This directly contradicts the writer→resolver split's stated guarantee that the hook is
best-effort and "분석 절대 실패 안 함" (D-08, comment at `pipeline/app.py:2125`). A cosmetic
coaching hook can take down a real analysis.

**Fix:** Sanitize and re-default inside `_payload_to_hook` so the resolver can never produce a
dataclass that fails its own validator (reject-and-fallback, not raise):

```python
def _clean_str_list(items, fallback):
    cleaned = [s.strip() for s in items if isinstance(s, str) and s.strip()]
    return cleaned if cleaned else list(fallback)

questions = _read("open_questions_for_coach")
if not isinstance(questions, (list, tuple)):
    questions = []
questions = _clean_str_list(questions, [_GENERIC_QUESTION])[:3]

cues = _read("suggested_cues")
if not isinstance(cues, (list, tuple)):
    cues = []
cues = _clean_str_list(cues, _FORCE_CUE_DEFAULTS if is_force else _BODY_CUE_DEFAULTS)[:4]
```

Alternatively (defense in depth), wrap the `resolve_coach_hook_bundle` call in `pipeline/app.py`
in a try/except that logs and falls back to `build_canned_hook` on any exception, so a hook
defect can never reach `fail_analysis`.

## Warnings

### WR-01: LLM-supplied hook lists are never capped or de-duplicated

**File:** `backend/shared/python/sunity_shared/analysis/coach_hook_builder.py:202-221`

**Issue:** The canned path caps `open_questions_for_coach` to 3 and `suggested_cues` to 4
(`build_canned_hook:144,149`), but the LLM path (`_payload_to_hook`) applies no cap and no
de-dupe. The Pydantic schema sets no `max_length`, the Firestore `_validate_coach_comment_hook`
sets no list-length limit, and the app merge only `slice(0,5)`s `openQuestionsForCoach` — never
`suggestedCues`. A verbose Gemini response can persist an unbounded list to Firestore, inflating
the document and the per-field index. Inconsistent with the system prompt's stated "강사 질문
1~3 / 수강생 큐 2~4" contract.

**Fix:** Apply the same caps/de-dupe in `_payload_to_hook` as `build_canned_hook` (see CR-01 fix
snippet uses `[:3]`/`[:4]`), and add `max_length` to the schema fields so over-long lists are
rejected/retried at parse time.

### WR-02: Body-report hook attachment is coupled to `force_signals_report` being non-None

**File:** `backend/functions/pipeline/app.py:2091,2147-2154`

**Issue:** The entire CoachCommentHook block (force hook AND body hook) lives inside
`if force_signals_report is not None:`. The body report's hook is therefore attached only when
force signals exist. Today `compute_force_signals` is typed to return a `ForceSignalsReport`
(non-None), so the gate is effectively always true — but the coupling is latent and fragile: if
force-signals ever short-circuits to `None` (or the gate is moved), a valid
`bodyComparisonReport` would silently ship without its hook, and the "강사에게 확인할 점"
section would lose its body questions with no warning. The body hook does not logically depend on
force signals.

**Fix:** Compute and attach the body hook independently of the force-signals gate, or hoist the
hook block out of the `force_signals_report is not None` branch and guard each report
independently (`if body_comparison_report is not None:` / `if force_pattern_inference is not
None:`).

### WR-03: Guardrails are applied to `response.text` but skipped when `response.parsed` is used

**File:** `backend/shared/python/sunity_shared/gemini/coach_hook_writer.py:212-229`

**Issue:** For a real Gemini response the code runs `_enforce_no_reject_patterns(raw_text,
forbid_measurement_units=True)` on `response.text`, then returns `response.parsed` if it is a
`CoachHookBundle`. If the SDK populates `parsed` from a response whose `text` is empty or
differs from the serialized structured output, the number-free / objectivity guard can be
bypassed (or, conversely, run against text that does not match what is stored). The guard and the
accepted payload should be derived from the same source.

**Fix:** Guard the actual serialized payload that will be persisted (e.g. run the guard over
`json.dumps(parsed.model_dump())` when taking the `parsed` path), or only trust `parsed` after
the guard has passed on the canonical text and fall back to JSON-parsing `raw_text` otherwise.

### WR-04: Injected/duck `CoachHookBundle` bypasses the number-free and objectivity guards entirely

**File:** `backend/shared/python/sunity_shared/gemini/coach_hook_writer.py:206-211`

**Issue:** When the response `isinstance(CoachHookBundle)` or `_looks_like_bundle(...)` is true,
the writer returns the bundle without running `_enforce_no_reject_patterns`. The guard only runs
on the "raw text" branch. A real `genai` client can return a typed/`parsed` object directly, so
in production a bundle whose text fields contain numbers or human-judgment vocabulary
("87점", "훌륭") could pass straight through to the resolver and into Firestore, defeating the
D-04/D-05 number-free lock and the objectivity charter. The guard is structurally optional rather
than mandatory.

**Fix:** Always run the guard against the concatenated text fields of any accepted bundle (real,
parsed, or duck) before returning it from `_generate_with_retry`, not only on the raw-text path.

### WR-05: Test fixture uses an invalid `deficit_code` that the dataclass never validates

**File:** `backend/tests/phase11/conftest.py:42` and
`backend/shared/python/sunity_shared/analysis/body_normalizer.py:788-795,843-856`

**Issue:** `golden_body_finding` builds `BodyComparisonFinding(deficit_code="line_not_straight",
...)`, but `line_not_straight` is not a member of `_DEFICIT_CODES` (valid codes:
`knee_toe_alignment`, `clean_lines`, `extension`, `posture`, `body_placement`,
`pose_reliability_low`). `BodyComparisonFinding.__post_init__` validates only `confidence` and
`category` — it never checks `deficit_code` against `_DEFICIT_CODES`, so the invalid code passes
silently. The golden fixture therefore exercises the builder with a code that cannot occur in
production, weakening the test's fidelity, and the `_DEFICIT_CODES` frozenset is effectively dead
(defined, never enforced).

**Fix:** Use a real deficit code in the fixture (e.g. `"clean_lines"` or `"extension"`), and add
a `deficit_code not in _DEFICIT_CODES → ValueError` guard to `BodyComparisonFinding.__post_init__`
so the enum is actually enforced at the dataclass boundary (consistent with the
`ForcePatternFinding` pattern).

## Info

### IN-01: Dead/no-op retry artifacts in the writer retry loop

**File:** `backend/shared/python/sunity_shared/gemini/coach_hook_writer.py:201,241`

**Issue:** `time.sleep(0.0)` (line 201) is a no-op "delay" before retry, and
`bundle = None  # pragma: no cover` (line 241) is unreachable — every branch above it already
returns. Both are harmless but misleading.

**Fix:** Remove `time.sleep(0.0)` (or use a real backoff if a delay is intended) and delete the
unreachable `bundle = None` line.

### IN-02: `force_signals_report is not None` gate is always-true and obscures intent

**File:** `backend/functions/pipeline/app.py:2091`

**Issue:** `compute_force_signals` is annotated to return `ForceSignalsReport` (never `None`), so
the guard reads as defensive against a condition that cannot occur, while simultaneously gating
unrelated logic (the body hook — see WR-02). This makes the control flow harder to reason about.

**Fix:** Either document why the gate exists or remove it and guard the hook/force blocks on the
objects they actually use.

### IN-03: Stray placeholder comment left in shipped UI code

**File:** `app/src/app/analysis/result.tsx:1066`

**Issue:** `userName={undefined /* TODO: Firebase displayName 박제 박제 박제 박제 */}` — a TODO
with repeated filler tokens left in committed code (pre-existing, but within a reviewed file and
adjacent to Phase 11 work).

**Fix:** Replace with a clean TODO or wire the Firebase `displayName`.

---

_Reviewed: 2026-06-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
