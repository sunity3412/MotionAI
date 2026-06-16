---
phase: 11-coachcommenthook-gemini
reviewer: Codex
date: 2026-06-16
scope: direct-plan-review
status: revise-before-execution
reviewed_artifacts:
  - 11-CONTEXT.md
  - 11-RESEARCH.md
  - 11-PATTERNS.md
  - 11-VALIDATION.md
  - 11-00-PLAN.md
  - 11-01-PLAN.md
  - 11-02-PLAN.md
local_code_checked:
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
  - backend/shared/python/sunity_shared/gemini/client.py
  - backend/shared/python/sunity_shared/gemini/guardrails.py
  - backend/shared/python/sunity_shared/gemini/schemas.py
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - backend/shared/python/sunity_shared/analysis/force_pattern.py
  - backend/shared/python/sunity_shared/analysis/body_normalizer.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/shared/python/sunity_shared/models.py
  - app/src/types/analysis.ts
  - app/src/app/analysis/result.tsx
  - app/src/lib/userAnalyses.ts
  - docs/contract.md
---

# Phase 11 Direct Plan Review

## Verdict

Do not execute Phase 11 exactly as written.

The phase intent is sound: contract-first `CoachCommentHook`, flat Firestore-safe shape, reject-and-fallback for LLM overreach, and v1 UI exposing only "강사에게 확인할 점" are the right product boundaries.

The execution plan has one serious architectural mismatch: it says Phase 11 is a Vision-independent text/data layer, but then anchors implementation to the current `GeminiCoachWriter.write()` / dual-track coach path, which is explicitly video-dependent and has a joint-card output contract. If implemented literally, Phase 11 either never gets real Gemini text in text-only cases, or it violates the Phase 11/Phase 17 boundary by using Gemini Vision.

I would revise the plan before execution. The clean fix is to keep the existing Gemini coach writer untouched and add a separate text-only hook writer that consumes the completed report findings after both reports exist. If cost/latency matters, bundle both report hooks in one text call, not one call per report.

## Findings

### BLOCKER-1: "Vision 독립" scope conflicts with reusing `GeminiCoachWriter.write()`

Phase 11 context locks the phase as "Vision 독립" and says Gemini translates structured finding text only. The current `GeminiCoachWriter` is not that component.

Evidence:
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py:1-25` documents this writer as Gemini Pro Vision coach output.
- `coach_writer_v2.py:414-430` returns `video_path_missing` when `context["videoPath"]` is absent and calls `GeminiVisionCall.call(video_path)` when present.
- `coach_writer_v2.py:188-198` builds a prompt that says to observe the video and joint deviations together.
- `backend/tests/gemini/test_coach_writer_v2.py:352-370` hard-locks "no videoPath -> no Gemini call".

Risk:
- If Phase 11 passes no video, Gemini hook generation silently becomes canned fallback, so roadmap success criterion #3 is overclaimed.
- If Phase 11 passes video to make Gemini run, the phase stops being Vision-independent and collides with Phase 17's ownership.
- Editing `GeminiCoachWriter.write()` to make it text-only would break Phase 13/17 behavior and tests.

My fix:
- Do not change `GeminiCoachWriter.write(context)`.
- Add a separate `GeminiCoachHookWriter` or `coach_hook_writer.py` text-only adapter. It should use `resolve_model`, a hook-specific Pydantic schema, and `_enforce_no_reject_patterns`, but not `GeminiVisionCall` or `videoPath`.
- Interpret "single call" as "one hook call per analysis bundling both report hooks", not "reuse the existing Vision writer result dict". If the no-extra-round-trip constraint is absolute, the plan needs an explicit contract refactor for the dual-track writer wrapper, not a casual schema extension.

### BLOCKER-2: The planned hook call site runs before `ForcePatternInference` exists

The plan places hook generation around the existing dual-track coach call, but the force-pattern report is built later.

Evidence:
- `_build_coach_context` and the dual-track coach calls happen at `backend/functions/pipeline/app.py:1945-2026`.
- `assemble.build_result(...)` is called at `pipeline/app.py:2027-2043`.
- `ForcePatternInference` is created after that at `pipeline/app.py:2087-2116`.
- `_build_coach_context` currently contains top joint deviations, dimension scores, scene flags, body profile, and branch info (`pipeline/app.py:827-853`), not `ForcePatternFinding` or `BodyComparisonFinding` objects.

Risk:
- A hook generated at the planned site cannot translate `ForcePatternInference.findings` because they do not exist yet.
- The implementer may accidentally generate hook copy from generic top joint deviations, duplicating `tip.detail2` instead of translating the report findings required by COACH-01.
- Body comparison can be available earlier, but force and body hooks need one consistent post-report assembly point.

My fix:
- Generate hooks after `force_pattern_inference` is created and after the high-score finding gate runs.
- Delay `body_comparison_report_dict = _dataclass_to_camel_case_dict(...)` until after hook attachment, or re-convert after `dataclasses.replace`.
- Build a dedicated hook context from `body_comparison_report.findings` and `force_pattern_inference.findings`, using only existing structured text and enum fields. Do not reuse `kismam.top_issues` as the source for Phase 11.

### BLOCKER-3: Extending the existing writer output schema can corrupt the joint-card contract

The current coach writer contract is "non-underscore keys are joint keys". Adding report-level hook keys to the same dict is unsafe.

Evidence:
- `CoachPayload` is a strict Pydantic schema with only `joints` (`backend/shared/python/sunity_shared/gemini/schemas.py:121-130`).
- `GeminiCoachWriter.write()` returns `{joint_key: {"detail", "detail2": ...}}` or reserved `_` keys (`coach_writer_v2.py:400-405`).
- `_coach_user_visible_keys` treats every non-underscore key as user-visible success (`pipeline/app.py:875-879`).
- `_strip_reserved_keys` only strips keys starting with `_` (`pipeline/app.py:856-862`).
- Existing tests assert the success result's visible key is exactly a joint key (`backend/tests/gemini/test_coach_writer_v2.py:253-264`).

Risk:
- A key like `coachCommentHook` or `reportHooks` would be counted as a joint key by retry/fallback logic.
- `assemble_dual_coach_sections` would ignore non-joint hook keys while the pipeline still thinks Gemini succeeded.
- Changing `write()` to return a mixed report/joint payload will break the B3 hard gate and Phase 13/17 assumptions.

My fix:
- Keep `coach_details` and `coach_hooks` as separate pipeline variables.
- If a single Gemini call must return both joint coach copy and hooks, create an explicit wrapper return type and update `_coach_user_visible_keys`, audit extraction, and tests to distinguish joint success from hook success.
- Preferred for Phase 11 MVP: separate text-only hook writer, one bundled hook payload, no mixing with joint detail writer output.

### HIGH-1: "수치 출력 금지" is not actually enforced for degree/angle numbers

The plan repeatedly says score/coordinate/judgment and sometimes "수치" are forbidden, but the guard/test set does not catch degrees.

Evidence:
- `_SCORE_PATTERNS` catches `87점` and `9/10`, but not `23도` or `23°` (`backend/shared/python/sunity_shared/gemini/guardrails.py:23-44`).
- The existing Gemini coach prompt includes numeric degree deviations (`coach_writer_v2.py:174-177`).
- Plan 11's forbidden tuple includes `"점"`, `"/10"`, `"좌표"`, `"x="`, `"y="`, judgment words, but no degree/angle regex.

Risk:
- Gemini can output "무릎이 23도 차이" and pass the planned tests.
- That may violate D-04/D-05 if Phase 11 hook prose is supposed to be number-free and only the measurement engine/UI owns numbers.

My fix:
- Make the policy explicit before coding:
  - Option A, recommended for MVP: hook prose is number-free. Add hook-only regex rejects for `\d+(\.\d+)?\s*(°|도|deg)`, percentages, and score labels. Do not include numeric deviations in the hook prompt.
  - Option B: engine-derived numbers are allowed. Then the guard must verify every numeric token in LLM output is present in structured input, which is more work and not worth it for this phase.

### HIGH-2: Wave 2 UI drops one report's questions

Plan 11-02 proposes a nullish-coalescing read:

```ts
result.forcePatternInference?.coachCommentHook?.openQuestionsForCoach
  ?? result.bodyComparisonReport?.coachCommentHook?.openQuestionsForCoach
  ?? []
```

Risk:
- Arrays are not nullish, so if the force hook exists, body-comparison questions are never shown.
- If the force hook exists with an empty array, the body questions are still hidden.
- This undercuts the "all reports have hooks" product value.

My fix:
- Merge, filter, de-dupe, and cap the two arrays:

```ts
const openQuestions = [
  ...(result.forcePatternInference?.coachCommentHook?.openQuestionsForCoach ?? []),
  ...(result.bodyComparisonReport?.coachCommentHook?.openQuestionsForCoach ?? []),
]
  .map((q) => q.trim())
  .filter(Boolean)
  .filter((q, i, arr) => arr.indexOf(q) === i)
  .slice(0, 5);
```

If source context matters, add a lightweight internal label like "힘 흐름" / "체형·라인" in the render layer, not a nested Firestore shape.

### HIGH-3: `coach_hook.py` can easily introduce circular imports

The plan puts `CoachCommentHook` and `build_canned_hook(findings, ...)` in one new module, while both report dataclasses will import `CoachCommentHook`.

Risk:
- If `coach_hook.py` imports `ForcePatternFinding` or `BodyComparisonFinding` at module import time for builder logic, then `force_pattern.py -> coach_hook.py -> force_pattern.py` becomes a circular import.
- This is likely because `force_pattern.py` and `body_normalizer.py` will need `CoachCommentHook | None` fields, and the builder needs to inspect those modules' finding classes.

My fix:
- Keep `coach_hook.py` dependency-light: only the frozen dataclass, validation helpers, and maybe pure string/list validators.
- Put canned/text construction in `coach_hook_builder.py` or `coach_hook_service.py`, using local imports or structural `Any`/Protocol access.
- Use `TYPE_CHECKING` only for type hints if exact finding classes are useful.

### WARNING-1: Wave 0 RED tests may fail at collection instead of test execution

Plan 11-00 wants `python -m pytest tests/phase11 -q --co` to collect successfully while tests remain RED. But Wave 0 does not clearly add stubs for Wave 1 entrypoints such as `build_canned_hook`.

Risk:
- Importing missing functions at module top level produces collection errors, not meaningful RED tests.
- That weakens the Nyquist scaffold because Wave 1 implementers debug imports instead of behavior.

My fix:
- In Wave 0, add behavior stubs that raise `NotImplementedError`, or write tests that import the module and assert the callable exists inside the test body.
- Keep collection green and make failures assertion-level or intentional `NotImplementedError` failures.

### WARNING-2: The fallback plan references `_client is None`, but the Gemini writer has no `_client`

Evidence:
- `GeminiCoachWriter` stores `_api_key_loader` and creates `GeminiVisionCall` in `_build_call`; it does not have a persistent `_client` field (`coach_writer_v2.py:363-386`).
- Existing Gemini fallback tests use `GeminiVisionCall.call() -> None` and `video_path_missing`, not `_client is None` (`backend/tests/gemini/test_coach_writer_v2.py:333-370`).

Risk:
- Tests copied from the Cerebras writer pattern will not match the actual Gemini path.

My fix:
- For the new text hook writer, expose a clear dependency seam: `api_key_loader` failure or client call returning `None` should produce canned hooks.
- Test that seam directly. Do not test for a private `_client` shape unless the new writer actually owns one.

## What Looks Strong

- The 3-way lockstep plan (`analysis.ts` + Python model/re-export + `docs/contract.md`) is correct.
- The Firestore validator landmine is real and correctly identified: `_validate_force_pattern_inference` rejects unknown nested dicts today (`firestore_admin.py:371-374`), so `coachCommentHook` needs an explicit branch.
- Keeping hook list fields as `list[str]` / `string[]` is the right Firestore shape.
- v1 exposure of only `openQuestionsForCoach` is the right product line; `coachComment` and `reviewedBy` should stay v2/null.
- Reject-and-fallback is the right runtime policy. Do not sanitize LLM text and emit the edited result.

## Recommended Plan Patch

1. Revise D-03 / Roadmap line 338: replace "기존 dual-track coach call 출력 스키마 확장" with "one text-only hook call per analysis, bundling both report hooks, after both reports are built."
2. Add a new `CoachHookBundle`/Pydantic schema with two optional report hooks:
   - `forcePatternInference: CoachCommentHookPayload | null`
   - `bodyComparisonReport: CoachCommentHookPayload | null`
3. Add `coach_hook.py` for the dataclass only; put builders/writers in separate modules to avoid circular imports.
4. Move hook generation in `pipeline/app.py` to after `force_pattern_inference` creation and before `complete_analysis`.
5. Delay report dict conversion until after hook attachment.
6. Update Wave 0 tests so collection succeeds with intentional RED behavior.
7. Update Wave 2 UI to merge both report question arrays instead of choosing the first non-null array.

After those patches, I would consider the phase execution-ready.
