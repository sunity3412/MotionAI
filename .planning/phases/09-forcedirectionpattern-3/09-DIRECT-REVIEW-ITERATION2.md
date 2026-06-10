---
phase: 09-forcedirectionpattern-3
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review-iteration-2
status: revise-before-execution
reviewed_plans:
  - 09-01-PLAN.md
  - 09-02-PLAN.md
  - 09-VALIDATION.md
notes:
  - "09-RESEARCH.md treated as background only per user instruction; no research update required."
---

# Phase 9 Direct Review: Iteration 2

## Executive Verdict

수정본은 1차 리뷰의 핵심 blocker 대부분을 제대로 반영했다. `ForcePatternInference` dataclass 필드 순서, `force_pattern_copy.py` runtime import cycle, `models.MODE_REFERENCE` 오타, axis warning surface는 계획 본문에서 개선됐다.

그래도 **as-is 실행은 아직 보류**가 맞다. 남은 문제는 알고리즘 방향이 아니라 실행 계획의 불일치다. 특히 frontend null-guard snippet은 현재 `userAnalyses.ts` 타입 구조에서 typecheck를 깨뜨릴 가능성이 높고, `MappingProxyType` 변경과 AST grep gate가 서로 맞지 않으며, pipeline test 경로가 plan/verify/VALIDATION에서 서로 다르다.

저라면 실행 전에 09-01/09-02에 짧은 patch를 한 번 더 넣고 간다. 수정량은 작다.

## What Was Fixed Since Iteration 1

- R1 fixed: `ForcePatternInference` field order now puts `mode_context` before defaulted `warnings` in `09-01-PLAN.md:242`.
- R2 fixed: `force_pattern_copy.py` no longer runtime-imports `force_pattern.py`; it uses local Literal aliases plus `TYPE_CHECKING` in `09-02-PLAN.md:204-224`.
- R3 fixed in plan body: pipeline wiring uses `models.MODE_EXPERT` in `09-02-PLAN.md:804`.
- R4 mostly fixed in plan body: axis guard is now two-tier with `_AXIS_IGNORE_WARNINGS_PER_METRIC` and `_AXIS_IGNORE_WARNINGS_REPORT` in `09-02-PLAN.md:397-412`.
- R5 fixed in intent: raw file grep was removed from T1 verify and replaced with AST copy-value gate in `09-02-PLAN.md:339-342`.
- R6 fixed: Wave 1 now reuses Wave 0 `_IPSF_TOLERANCE_DEG` instead of redefining it in `09-02-PLAN.md:393`.

## Remaining Findings

### R1. Frontend null-guard snippet will likely fail `tsc`

Severity: **BLOCKER**

Plan 09-01 T6 says to add:

```ts
const rawForcePattern = (raw?.result?.forcePatternInference ?? null) as
  | ForcePatternInference
  | null;
```

Evidence: `09-01-PLAN.md:554-559`.

Actual `normalize()` receives `raw: Record<string, unknown>`, and the existing code already narrows `raw.result` through:

```ts
let result = raw.result as AnalysisDoc['result'] | undefined;
```

In TypeScript, `raw.result` is `unknown`; property access through `raw?.result?.forcePatternInference` is not safe. The code should use the already typed `result`, not the raw Firestore object.

Risk:

- `cd app && npm run typecheck` fails in Wave 0.
- The plan claims Wave 0 is schema lockstep, but this is a frontend compile blocker.

Recommendation:

Use current file style:

```ts
const rawForcePattern = result?.forcePatternInference ?? null;
const forcePatternInference = rawForcePattern
  ? {
      ...rawForcePattern,
      findings: (rawForcePattern.findings ?? []).map((f) => ({
        ...f,
        warnings: f.warnings ?? [],
        jointHint: f.jointHint ?? null,
      })),
      warnings: rawForcePattern.warnings ?? [],
    }
  : null;

if (result) {
  result = {
    ...result,
    forcePatternInference,
  };
}
```

Do not add `forcePatternInference` as a loose variable only at return time unless `result` is also reconstructed. `forcePatternInference` belongs under `result`, not at the top-level `AnalysisDoc`.

### R2. Firestore validator behavior says strict `list[str]`, but the code block still accepts arbitrary scalars

Severity: **HIGH**

The behavior section correctly says warnings must be non-empty `str` only:

- `09-01-PLAN.md:410-411`

But the implementation snippet still accepts `str/int/float/bool/None` in warning lists:

- finding warnings loop: `09-01-PLAN.md:448-455`
- top-level warnings loop: `09-01-PLAN.md:482-486`

Risk:

- `warnings: [true, 1, null]` passes the validator despite the contract saying warning codes are `string[]`.
- The tests still only mention non-scalar rejection, so this can slip through.

Recommendation:

Change both validator loops to strict string checks:

```python
for i, item in enumerate(v):
    if not isinstance(item, str) or not item:
        raise ValueError(f"{sub}[{i}] must be non-empty str warning code")
```

Add tests for:

- `warnings=[1]` rejects
- `warnings=[True]` rejects
- `warnings=[None]` rejects
- `warnings=[""]` rejects

This should apply to both top-level `ForcePatternInference.warnings` and each finding's `warnings`.

### R3. `MappingProxyType` breaks the planned AST forbidden-copy extractor

Severity: **HIGH**

The plan now wraps copy maps:

```python
_FORCE_PATTERN_COPY_DATA = {...}
_FORCE_PATTERN_COPY = MappingProxyType(_FORCE_PATTERN_COPY_DATA)
```

Evidence: `09-02-PLAN.md:234-242`.

But the AST extractor still scans assignment targets only in:

```python
{"_FORCE_PATTERN_COPY", "_MODE_PREFIX", "_FALLBACK_BODY"}
```

Evidence: `09-02-PLAN.md:315-321`.

With `MappingProxyType`, the string values live in `_FORCE_PATTERN_COPY_DATA` and likely `_MODE_PREFIX_DATA`, not `_FORCE_PATTERN_COPY` or `_MODE_PREFIX`. The planned extractor will either miss almost all copy values or fail the sanity check (`>= 22 strings`).

Risk:

- T1 fails even though the implementation is otherwise correct.
- Or worse, if the sanity threshold is weakened later, forbidden copy values are no longer scanned.

Recommendation:

Update the extractor target set:

```python
target_id in {
    "_FORCE_PATTERN_COPY_DATA",
    "_MODE_PREFIX_DATA",
    "_FALLBACK_BODY",
}
```

If `_MODE_PREFIX` is not split into `_MODE_PREFIX_DATA`, keep whichever target actually contains the literal strings. Also add an explicit assertion that at least 18 values came from `_FORCE_PATTERN_COPY_DATA`.

### R4. Pipeline test path is inconsistent across 09-02 and VALIDATION

Severity: **HIGH**

The revised T4 file list correctly says:

- `backend/tests/pipeline/test_pipeline_phase9.py`

Evidence: `09-02-PLAN.md:773-778`, `09-02-PLAN.md:844`.

But the commit message, pre-commit gate, verify command, and VALIDATION still reference the old path:

- `09-02-PLAN.md:931-943`: `tests/phase09/test_force_pattern_pipeline_wiring.py`
- `09-VALIDATION.md:60-61`: same old path

Risk:

- Executor may create one file and run another.
- T4 can fail at verify time even if the correct pipeline test exists.
- Validation map no longer reflects the plan.

Recommendation:

Use only:

```bash
cd backend && pytest tests/pipeline/test_pipeline_phase9.py -x -q
```

Update all of these together:

- T4 commit message
- T4 pre-commit gate
- T4 `<verify>`
- `09-VALIDATION.md` rows `09-W1-P1` and `09-W1-P2`
- Wave 1 success criteria if needed

### R5. The T4 test instructions still contain contradictory old guidance

Severity: **MEDIUM-HIGH**

T4 now correctly says not to extract a helper and to reuse real `_process`:

- `09-02-PLAN.md:844-853`

But the pseudocode immediately after still says:

- "full `_process` 호출은 SAM-shape event + ML adapter 필요"
- "본 test 는 `_process`의 Phase 9 wiring 블록만 단위 함수로 분리하거나..."
- mentions a likely non-existent `backend/tests/phase08/test_pipeline_force_signals_wiring.py`

Evidence: `09-02-PLAN.md:880-918`.

Risk:

- The executor gets two mutually exclusive instructions.
- A mini-helper test could reappear, which defeats the R3 fix.

Recommendation:

Delete the old pseudocode guidance and replace it with a direct instruction to copy the existing pattern from `backend/tests/pipeline/test_pipeline_phase8.py`. That file already imports pipeline as module `app` from `functions/pipeline`, patches `_extract_video_analysis_inputs`, and captures `complete_analysis`.

### R6. Dataclass strict validators are specified but not test-covered

Severity: **MEDIUM**

Plan 09-01 now says:

- `version` must be non-empty
- `findings` must contain `ForcePatternFinding`
- `warnings` must be `list[str]`
- `joint_hint` must be `None | str`

Evidence: `09-01-PLAN.md:242-250`.

But the test behavior list still only covers the old cases:

- invalid pattern
- invalid source signal
- confidence range
- empty interpretation
- too many findings
- invalid mode context

Evidence: `09-01-PLAN.md:171-173`.

Risk:

- The stricter validator can be skipped or partially implemented while tests still pass.

Recommendation:

Add explicit `test_force_pattern_dataclass.py` cases for:

- `ForcePatternFinding(warnings=[1])` raises
- `ForcePatternFinding(joint_hint=123)` raises
- `ForcePatternInference(version="")` raises
- `ForcePatternInference(findings=[object()])` raises
- `ForcePatternInference(warnings=[1])` raises

### R7. `ForcePatternInference` construction snippet still uses old keyword order

Severity: **LOW-MEDIUM**

The dataclass order is fixed, and keyword construction is legal. But examples still use `warnings=...` before `mode_context=...`:

- `09-02-PLAN.md:515-521`
- `09-01-PLAN.md:171`

Risk:

- Low runtime risk because keywords are fine.
- Moderate readability risk because the plan just fixed field ordering for dataclass rules, but examples obscure the intended order.

Recommendation:

Normalize examples to:

```python
ForcePatternInference(
    version="1.0",
    findings=findings,
    overall_confidence=overall,
    mode_context=mode_context,
    warnings=umbrella_warnings,
)
```

### R8. Threat model still claims immutable copy dict without matching all planned wraps

Severity: **LOW**

T1 says to apply `MappingProxyType` to `_FORCE_PATTERN_COPY`, `_MODE_PREFIX`, and `_JOINT_HINT_BY_SIGNAL`, but the verify command only checks `_FORCE_PATTERN_COPY`.

Evidence:

- wrap instruction: `09-02-PLAN.md:242`
- verify: `09-02-PLAN.md:340`
- threat language: `09-02-PLAN.md:1038`, `09-02-PLAN.md:1047`

Risk:

- Minor. `_FORCE_PATTERN_COPY` is the important one.
- But the plan says "immutable dict" broadly, and only one mapping is verified.

Recommendation:

Either verify all three mappings are `MappingProxyType`, or narrow the claim to `_FORCE_PATTERN_COPY` only.

## Technical Recommendation

I would apply a small patch with four concrete edits before execution:

1. Replace T6 frontend snippet to use typed `result?.forcePatternInference`, then reconstruct `result`.
2. Rewrite `_validate_force_pattern_*` warning loops to enforce non-empty `str` only, and add corresponding tests.
3. Update forbidden-copy AST extractor targets to the `*_DATA` variables introduced for `MappingProxyType`.
4. Rename all T4/VALIDATION references to `backend/tests/pipeline/test_pipeline_phase9.py` and delete old helper-extraction guidance.

After that, I would consider the plan ready to execute.

## Final Recommendation

Do **not** execute the revised plan as-is. The algorithmic and architectural issues from iteration 1 are largely fixed, but the remaining plan inconsistencies are enough to break Wave 0 or Wave 1 verification. Patch the items above, then proceed.

