---
phase: 11-coachcommenthook-gemini
reviewer: Codex
date: 2026-06-16
scope: direct-plan-review-iteration-2
status: revise-before-execution
reviewed_artifacts:
  - 11-CONTEXT.md
  - 11-RESEARCH.md
  - 11-PATTERNS.md
  - 11-VALIDATION.md
  - 11-00-PLAN.md
  - 11-01-PLAN.md
  - 11-02-PLAN.md
  - 11-REVIEWS.md
local_code_checked:
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/shared/python/sunity_shared/gemini/client.py
  - backend/shared/python/sunity_shared/gemini/guardrails.py
  - backend/shared/python/sunity_shared/gemini/scene_finder.py
  - backend/shared/python/sunity_shared/gemini/reference_extractor.py
  - backend/shared/python/sunity_shared/gemini/schemas.py
  - backend/functions/pipeline/app.py
---

# Phase 11 Direct Review - Iteration 2

## Verdict

The first review was mostly incorporated correctly. The revised plan now separates Phase 11 from the Vision `GeminiCoachWriter`, moves hook generation after `ForcePatternInference`, and merges both reports' UI questions. Those are the right fixes.

I still would not execute yet. The remaining risks are now lower-level but concrete:

1. The proposed Firestore validation still uses the generic flat validator for `coachCommentHook`, but that validator allows `list[dict]`, while the Phase 11 contract says hook list fields must be `list[str]` only.
2. The plan adds degree/percent rejection to the global Gemini guardrail, which can break existing Phase 17 Gemini Vision calls that legitimately return notes containing "30도" or "50%".
3. The new text-only writer plan does not explicitly reuse the existing schema-stripping generate config, even though the existing Gemini client documents why raw Pydantic schema can cause Gemini 400s.

Fix those before execution. After that, I would consider Phase 11 plan-ready.

## Findings

### BLOCKER-1: `coachCommentHook` needs a hook-specific validator; the generic flat validator allows `list[dict]`

The revised plan still says to validate `coachCommentHook` by delegating to `_validate_flat_dict_no_nested_array`. That is not strict enough for the Phase 11 hook contract.

Evidence:
- `firestore_admin._validate_flat_dict_no_nested_array` explicitly allows list items that are dicts if each dict is scalar-only (`firestore_admin.py:78-90`).
- Plan 11 requires `openQuestionsForCoach` and `suggestedCues` to be `list[str]` only.
- Plan 11-01 Task 2 says `coachCommentHook` should delegate to `_validate_flat_dict_no_nested_array` (`11-01-PLAN.md:147-149`).
- Plan 11-00/11-01 tests expect `coachCommentHook.openQuestionsForCoach = list[dict]` to be rejected.
- `BodyComparisonReport` still routes through the generic validator (`firestore_admin.py:779-783`), so the body report path would also allow a malformed hook unless it gets a hook-specific precheck.

Risk:
- A raw dict bug or corrupted Firestore write can persist `openQuestionsForCoach: [{...}]` and still pass validation.
- The planned nested-array test will either fail forever or be weakened to match the wrong validator behavior.
- The Firestore shape may remain technically nested-array-safe but violates the stricter Phase 11 contract and app assumptions.

My fix:
- Add `_validate_coach_comment_hook(payload, *, path)` with an explicit whitelist:
  - scalar-or-null fields: `autoFindingsSummary`, `coachComment`, `reviewedBy`, `sourceReport`
  - required list fields: `openQuestionsForCoach`, `suggestedCues`
  - list fields must be `list[str]` of non-empty strings; reject `list[dict]`, `list[list]`, tuple, unknown keys.
- In `_validate_force_pattern_inference`, call `_validate_coach_comment_hook` for `key == "coachCommentHook"` before the generic nested-dict reject branch.
- For body comparison, do not rely only on `_validate_flat_dict_no_nested_array`. Add a minimal body report precheck in `complete_analysis`:
  - if `body_comparison_report.get("coachCommentHook") is not None`, call `_validate_coach_comment_hook(...)`
  - then run the existing generic validator for the rest.
- Add tests for both force and body paths:
  - flat `list[str]` hook passes
  - `list[dict]` hook rejects
  - nested list rejects
  - unknown hook key rejects

### BLOCKER-2: Adding degree/% patterns to the global Gemini guardrail can break existing Vision areas

The revised plan says to add `°|도|deg|%` patterns to `_SCORE_PATTERNS` in `guardrails.py`. That function is global and is used by `GeminiVisionCall` whenever `enforce_object_guard=True`.

Evidence:
- `GeminiVisionCall.call()` calls `_enforce_no_reject_patterns(raw_text, ...)` for all callers with `enforce_object_guard=True` (`client.py:342-348`).
- Scene finder uses `enforce_object_guard=True` (`scene_finder.py:161-169`) and its prompt defines visual conditions using "30도" and "50%" (`scene_finder.py:67-78`). The model's `notes_ko` can reasonably repeat those phrases.
- Reference extractor also uses `enforce_object_guard=True` (`reference_extractor.py:333-341`), and its schema includes numeric timestamp/confidence fields (`schemas.py:68-80`), so global numeric expansion should be treated carefully.
- Plan 11's number-free policy is hook-specific, not a Phase 17-wide policy.

Risk:
- Phase 17 scene/finding calls may start returning graceful fallback or raising guard errors only because the note says "50% 이상 가려짐" or "30도 후굴".
- This is a cross-phase behavioral regression caused by a Phase 11-only rule.

My fix:
- Do not put degree/% into the global `_SCORE_PATTERNS`.
- Add a hook-only guard path:
  - either `_enforce_no_hook_number_patterns(text, context="coach_hook")` in `coach_hook_writer.py`, called after `_enforce_no_reject_patterns`, or
  - extend `_enforce_no_reject_patterns(..., forbid_measurement_units: bool = False)` and use `True` only from `GeminiCoachHookWriter`.
- Add regression tests that the default global guard still allows a neutral phrase like `"등이 30도 이상 후굴"` unless the hook-specific flag/helper is used.

### HIGH-1: Text-only Gemini writer must reuse the existing schema-stripping config path

The plan says the new writer should call `genai.Client(...).models.generate_content` with `response_schema=CoachHookBundle`, but the existing Gemini client already documents that direct Pydantic schema can produce Gemini API 400s unless unsupported schema keys are stripped.

Evidence:
- `client.py:267-290` builds `GenerateContentConfig` with `_strip_unsupported_schema_keys(self.schema.model_json_schema())`.
- The comments at `client.py:271-275` say Pydantic 2 schemas can include unsupported `additionalProperties`/`$defs`, causing Gemini 400 `INVALID_ARGUMENT`.
- `CoachHookBundle` will be a nested Pydantic schema, so it is exactly the kind of schema that can produce `$defs`.

Risk:
- Unit tests with monkeypatched clients pass, but live Gemini hook generation returns `None`/fallback because the schema config is invalid.
- The phase appears to work through canned fallback while the real LLM path never functions.

My fix:
- Factor a shared helper out of `GeminiVisionCall` for text calls, or import the existing private helper deliberately with a comment:
  - `_strip_unsupported_schema_keys`
  - `genai_types.GenerateContentConfig`
  - `HttpOptions(timeout=_HTTP_TIMEOUT_MS)`
- Add a unit test for `GeminiCoachHookWriter` that inspects the config passed to `generate_content` and asserts no `additionalProperties`, `$defs`, or `discriminator` keys remain.
- Add a retry/parse path mirroring `GeminiVisionCall._generate_with_retry`, at least for schema validation failure and 5xx.

### HIGH-2: `CoachHookBundle` fields are optional, but pipeline fallback must be per-report

The revised schema idea has two optional report hooks, but the pipeline plan mostly describes fallback when the whole hook call returns `None`.

Evidence:
- Plan 11-01 defines `CoachHookBundle` with optional `force_pattern_inference` and `body_comparison_report` fields.
- The pipeline action says `build_coach_hooks(...)` returns `None` on key/reject failure, then per-report canned fallback is used (`11-01-PLAN.md:149`).
- It does not explicitly say what happens when the bundle is non-null but one report hook is missing/null.

Risk:
- Gemini can return only one report hook and pass schema validation.
- One report can be attached with an LLM hook while the other remains `None`, violating COACH-01 success criterion #2: all reports get `coachCommentHook`.

My fix:
- After parsing a bundle, resolve each report independently:
  - if `bundle.force_pattern_inference` exists, convert it to `CoachCommentHook`; else `build_canned_hook(force_findings, source_report="forcePatternInference")`
  - same for body comparison.
- Add a test where the mocked bundle has only one report hook and assert both report dataclasses still get `coach_comment_hook`.

### HIGH-3: `11-RESEARCH.md` and `11-PATTERNS.md` still contain pre-review instructions that contradict the locked design

The main plans and roadmap were corrected, but research/pattern files still tell implementers to reuse/extend `GeminiCoachWriter`, use `_client`, hook into the same dual-track path, and use a `??` chain in the UI.

Evidence:
- `11-RESEARCH.md:43-54` still frames implementation as extending `GeminiCoachWriter` / existing LLM call path.
- `11-RESEARCH.md:398-401` still recommends extending the existing output schema.
- `11-PATTERNS.md:115-131` still says to add `write_report_hook` to `GeminiCoachWriter` and follow `_client is None`.
- `11-PATTERNS.md:183-202` still says to generate the hook in the same dual-track call path.
- `11-PATTERNS.md:217-224` still shows the old UI `??` chain that drops body questions.

Risk:
- Downstream implementers are explicitly told to read `11-RESEARCH.md` and `11-PATTERNS.md`; they can follow stale instructions over the corrected plan.
- This reopens the first review's BLOCKER-1/2/3 and HIGH-2.

My fix:
- Patch `11-RESEARCH.md` and `11-PATTERNS.md`, not just the plan files:
  - mark the old `GeminiCoachWriter.write_report_hook` approach as superseded
  - replace `_client` fallback with `api_key_loader`/None-return seam
  - replace same-path dual-track integration with post-force-pattern `GeminiCoachHookWriter`
  - replace UI `??` chain with concat/trim/dedupe/slice
- Keep a short "superseded by Codex review" note if you want historical context, but do not leave stale instructions as live recommendations.

### WARNING-1: Several Phase 11 files contain stray `</content>` / `</invoke>` tool tags

Evidence:
- `rg "</content>|</invoke>" .planning/phases/11-coachcommenthook-gemini` finds tags in `11-CONTEXT.md`, all three plan files, and `11-VALIDATION.md`.

Risk:
- Most Markdown readers ignore them, but workflow parsers or artifact tooling may treat them as literal content.
- It is also noise for future reviewers.

Fix:
- Remove the stray tags from the affected Phase 11 files.

### WARNING-2: Roadmap success criterion #5 still names Cerebras, but Phase 11 hook fallback is now Gemini/hook-writer based

Evidence:
- `.planning/ROADMAP.md:336` says "Cerebras 키 미설정 시에도 fallback 카피로 분석이 완료된다".
- The revised Phase 11 implementation is a Gemini text-only hook writer with `api_key_loader` fallback, and does not use Cerebras for hook generation.

Risk:
- Acceptance criteria can be tested against the wrong provider.

Fix:
- Change criterion #5 to "Gemini/hook LLM key unset or hook call failure -> canned fallback; analysis completes".
- If existing Cerebras coach writer fallback is still relevant, keep it in Phase 13/17 criteria, not Phase 11 hook criteria.

## Closed From Iteration 1

- The plan no longer mutates `GeminiCoachWriter.write()` and now introduces a separate text-only writer.
- Hook generation is now planned after `ForcePatternInference` exists.
- `coach_details` and `coach_hooks` are separated.
- UI question collection is corrected in `11-02-PLAN.md` to merge both report arrays.
- Circular import risk is addressed by splitting `coach_hook.py` and `coach_hook_builder.py`.
- Wave 0 collection-green RED is now explicitly planned.

## Final Recommendation

Patch the validator strategy and guardrail scope before execution. Those two are real runtime risks, not wording polish.

Minimum plan changes:

1. Add `_validate_coach_comment_hook` and use it for both force and body report paths.
2. Make degree/% rejection hook-specific, not global.
3. Reuse/factor the existing Gemini schema-stripping generate config for the text-only writer.
4. Define per-report fallback for partial `CoachHookBundle`.
5. Clean stale `11-RESEARCH.md` / `11-PATTERNS.md` instructions and stray tool tags.

After those changes, Phase 11 should be ready to execute.
