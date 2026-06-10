---
phase: 09-forcedirectionpattern-3
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review
status: revise-before-execution
reviewed_plans:
  - 09-01-PLAN.md
  - 09-02-PLAN.md
  - 09-CONTEXT.md
  - 09-RESEARCH.md
  - 09-VALIDATION.md
---

# Phase 9 Direct Review

## Executive Verdict

방향은 맞다. Phase 9를 Phase 8/8.1 `ForceSignalsReport` 위의 deterministic 추론 레이어로 두고, LLM/RunPod 없이 `forcePatternInference`를 만드는 구조는 현재 코드베이스와 잘 맞는다. 특히 raw axis tilt guard, 3-way contract lockstep, Firestore scoped validator, canned copy grep gate는 좋은 안전장치다.

다만 **현재 plan 그대로 실행하면 Wave 0/1 초반에 import 또는 dataclass 정의 단계에서 바로 깨질 가능성이 높다.** 내 판정은 **as-is 실행 보류, 짧은 plan patch 후 실행**이다.

가장 먼저 고쳐야 할 것은 4개다.

1. `ForcePatternInference` dataclass 필드 순서가 Python 문법상 잘못되어 있다.
2. `force_pattern.py`와 `force_pattern_copy.py`가 서로 top-level import하는 순환 import 구조다.
3. pipeline wiring이 존재하지 않는 `models.MODE_REFERENCE`를 사용한다.
4. axis warning guard가 실제 Phase 8.1 warning surface와 어긋난다.

저라면 09-01/09-02를 바로 실행하지 않고, **09-PLAN-PATCH.md 또는 plan 파일 직접 수정**으로 아래 blocker를 먼저 정리한다. 수정량은 작지만 실행 안정성에는 결정적이다.

## Reviewed Inputs

- `.planning/phases/09-forcedirectionpattern-3/09-CONTEXT.md`
- `.planning/phases/09-forcedirectionpattern-3/09-RESEARCH.md`
- `.planning/phases/09-forcedirectionpattern-3/09-VALIDATION.md`
- `.planning/phases/09-forcedirectionpattern-3/09-01-PLAN.md`
- `.planning/phases/09-forcedirectionpattern-3/09-02-PLAN.md`
- `backend/shared/python/sunity_shared/analysis/force_signals.py`
- `backend/functions/pipeline/app.py`
- `backend/shared/python/sunity_shared/firestore_admin.py`
- `backend/shared/python/sunity_shared/models.py`
- `app/src/types/analysis.ts`
- `app/src/lib/userAnalyses.ts`
- `backend/tests/pipeline/test_pipeline_phase8.py`

## Blockers

### R1. `ForcePatternInference` dataclass field order will raise at import time

Severity: **BLOCKER**

Plan 09-01 defines:

```python
ForcePatternInference(
    version: str,
    findings: list[ForcePatternFinding],
    overall_confidence: MetricConfidence,
    warnings: list[str] = field(default_factory=list),
    mode_context: ModeContext,
)
```

This violates Python dataclass rules: a non-default field (`mode_context`) cannot follow a default field (`warnings`). Evidence: `09-01-PLAN.md:236`.

Risk:

- `import sunity_shared.analysis.force_pattern` fails before any Phase 9 test can run.
- The verify command in `09-01-T2` imports `ForcePatternInference`, so Wave 0 stops immediately.

Recommendation:

Move `mode_context` before `warnings`, or give `mode_context` a default. I would choose explicit non-default ordering:

```python
@dataclass(frozen=True)
class ForcePatternInference:
    version: str
    findings: list[ForcePatternFinding]
    overall_confidence: MetricConfidence
    mode_context: ModeContext
    warnings: list[str] = field(default_factory=list)
```

Then update docs/tests to preserve camelCase output as `modeContext` and `warnings`.

### R2. `force_pattern.py` and `force_pattern_copy.py` have a circular import

Severity: **BLOCKER**

Plan 09-02 T1 creates `force_pattern_copy.py` with:

```python
from .force_pattern import ForceSourceSignal, ModeContext
```

Evidence: `09-02-PLAN.md:201-207`.

Then T2 adds to `force_pattern.py`:

```python
from .force_pattern_copy import fallback_body, force_pattern_canned_text, joint_hint_for
```

Evidence: `09-02-PLAN.md:360-363`.

Risk:

- If the import is inserted with other imports at the top, `force_pattern_copy` imports `ForceSourceSignal` from a partially initialized `force_pattern` module before aliases are defined.
- Even if it happens to work after aliases are defined, this is brittle and will regress as soon as imports move.

Recommendation:

Break the cycle. The cleanest option is: `force_pattern_copy.py` should not runtime-import `force_pattern.py` at all. Use `TYPE_CHECKING` or duplicate local string type aliases there:

```python
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .force_pattern import ForceSourceSignal, ModeContext

ForceSourceSignal = Literal[
    "axis_tilt", "pelvis_drop", "late_contact",
    "high_jitter", "high_jerk", "abnormal_release",
]
ModeContext = Literal["mode1", "mode3_first", "mode3_progress"]
```

I would also avoid importing `fallback_body` into `force_pattern.py`; inference should not need it. Let downstream callers import fallback from `force_pattern_copy.py` directly.

### R3. Pipeline wiring uses `models.MODE_REFERENCE`, which does not exist

Severity: **BLOCKER**

Plan 09-02 T4 says:

```python
if mode == models.MODE_REFERENCE:
    mode_context = "mode1"
```

Evidence: `09-02-PLAN.md:763-764`.

Actual constants are:

- `models.MODE_EXPERT = "mode1"`
- `models.MODE_SELF = "mode3"`

Evidence: `backend/shared/python/sunity_shared/models.py:10-11`.

Risk:

- `_process` fails with `AttributeError: module ... has no attribute MODE_REFERENCE` for every analysis after Phase 9 wiring lands.

Recommendation:

Use the existing constant:

```python
if mode == models.MODE_EXPERT:
    mode_context: fp.ModeContext = "mode1"
elif mode == models.MODE_SELF:
    ...
else:
    mode_context = "mode3_first"  # or raise earlier, matching current mode validation
```

Also add a pipeline test that would have caught this by running the existing mock `_process` path from `backend/tests/pipeline/test_pipeline_phase8.py`.

### R4. Axis warning guard misses the actual Phase 8.1 transitional warning surface

Severity: **HIGH**

Plan 09-02 T2 defines:

```python
_AXIS_IGNORE_WARNINGS = {
    "axis_metric_transitional",
    "tilt_unavailable",
    "tilt_thresholds_fallback",
}
```

Evidence: `09-02-PLAN.md:378-386`.

Actual code uses:

- per-axis metric warning: `phase_8_1_wave_0_transitional`
- top-level report warning: `axis_metric_transitional`

Evidence: `backend/shared/python/sunity_shared/analysis/force_signals.py:1669-1677`, `docs/contract.md:854`.

Risk:

- The core D-09-A2 guard is not aligned with the real upstream contract.
- A future axis metric with stale transitional warning could leak into Phase 9 if raw tilt values are non-null.
- The current implementation sketch only checks `axis.warnings`, not `force_signals_report.warnings`, so top-level `axis_metric_transitional` is ignored.

Recommendation:

Include both per-metric and top-level signals:

```python
_AXIS_IGNORE_WARNINGS = frozenset({
    "axis_metric_transitional",
    "phase_8_1_wave_0_transitional",
    "tilt_unavailable",
    "tilt_thresholds_fallback",
})

report_axis_blocked = "axis_metric_transitional" in force_signals_report.warnings
axis_blocked = report_axis_blocked or axis is None or any(
    w in _AXIS_IGNORE_WARNINGS for w in axis.warnings
)
```

Add tests for both cases: top-level report warning and per-axis warning.

## High-Risk Findings

### R5. The `grep -cE "박제|%일치|유사도"` gate conflicts with the file contents the plan asks us to write

Severity: **HIGH**

Plan 09-02 T1 asks `force_pattern_copy.py` to include docstrings/comments with "박제" language, then verifies the entire file has zero occurrences:

- module docstring/comment instructions: `09-02-PLAN.md:195-197`, `09-02-PLAN.md:231-236`, `09-02-PLAN.md:273`
- verify command: `09-02-PLAN.md:315`

Risk:

- The task can pass AST copy-value tests but fail the broader grep gate because comments/docstrings contain "박제".
- Or the executor removes useful rationale comments just to satisfy a blunt grep.

Recommendation:

Scope the "박제/%일치/유사도" check to copy values only, using the AST extractor already planned for `_FORCE_PATTERN_COPY`, `_MODE_PREFIX`, and `_FALLBACK_BODY`. If a raw grep is kept, remove all such words from docstrings/comments in that module. I prefer the AST-only gate because the user-facing risk is in emitted copy, not implementation comments.

### R6. Wave 1 duplicates `_IPSF_TOLERANCE_DEG` already specified in Wave 0

Severity: **MEDIUM-HIGH**

Wave 0 already requires `_IPSF_TOLERANCE_DEG = 20.0` in `force_pattern.py` (`09-01-PLAN.md:214`). Wave 1 T2 then tells the executor to add the same constant again (`09-02-PLAN.md:368-374`).

Risk:

- Duplicate definition or contradictory edits, depending on how literally the executor follows the plan.
- This is small mechanically, but it signals plan drift between Wave 0 and Wave 1.

Recommendation:

Make Wave 1 say "reuse the Wave 0 `_IPSF_TOLERANCE_DEG` constant" instead of adding it.

### R7. The ForcePattern validators are under-specified for list element types

Severity: **MEDIUM**

The plan validates enum values, confidence range, and non-empty interpretation, but it does not clearly require:

- `ForcePatternFinding.warnings` is `list[str]`
- `ForcePatternInference.warnings` is `list[str]`
- every `ForcePatternInference.findings` item is a `ForcePatternFinding`
- `version` is non-empty

Evidence: `09-01-PLAN.md:215-216`, `09-01-PLAN.md:234-236`.

Risk:

- Internal misuse can still construct structurally invalid dataclasses that later become Firestore payloads.
- Firestore validator catches some serialized bad shapes, but earlier failure is cheaper and easier to debug.

Recommendation:

Add these checks in `__post_init__` and unit tests. I would keep the Firestore scoped validator as defense-in-depth, not the first line of defense.

### R8. Pipeline test plan is too ambiguous for the risk level

Severity: **MEDIUM**

T4 includes ellipses and several alternatives for testing `_process` wiring (`09-02-PLAN.md:812-851`). There is already a strong existing mock E2E pattern in `backend/tests/pipeline/test_pipeline_phase8.py`.

Risk:

- The executor may create a mirrored mini-helper test that does not exercise real `_process`.
- The wrong constant issue in R3 is exactly the kind of bug a real mock `_process` test catches.

Recommendation:

Make the plan explicit: add Phase 9 tests under `backend/tests/pipeline/test_pipeline_phase9.py` and copy the fixture style from `test_pipeline_phase8.py`. Required cases:

- mode1 emits `modeContext == "mode1"`
- mode3 first emits `modeContext == "mode3_first"`
- mode3 progress emits `modeContext == "mode3_progress"`
- `complete_analysis` receives camelCase `force_pattern_inference`
- no Gemini/Cerebras/RunPod dependency is introduced

I would not extract a new helper unless the `_process` block becomes hard to test with the existing mock fixtures.

## Medium-Risk Findings

### R9. `force_pattern_copy.py` should not be treated as immutable if it exposes mutable dicts

Severity: **MEDIUM**

The plan calls `_FORCE_PATTERN_COPY` a "singleton" and "runtime mutation X", but a module-level dict is mutable in Python. The underscore is convention, not enforcement.

Risk:

- Tests or future code can mutate copy at runtime.
- This matters because the plan positions canned copy as caller-controlled input 0.

Recommendation:

Either accept the convention and stop claiming immutability, or wrap with `MappingProxyType`:

```python
from types import MappingProxyType

_FORCE_PATTERN_COPY_DATA = {...}
_FORCE_PATTERN_COPY = MappingProxyType(_FORCE_PATTERN_COPY_DATA)
```

Tests can still inspect it as a mapping.

### R10. `warnings` contract says string list, but validators allow any scalar

Severity: **MEDIUM**

The planned Firestore validator accepts `str/int/float/bool/None` inside warnings. The contract and dataclass language say `list[str]`.

Risk:

- Firestore payloads can contain `warnings: [true, 1]` and pass.
- Frontend and docs expect warning codes, not arbitrary scalar values.

Recommendation:

For Phase 9, be stricter than the old generalized helper:

```python
if key == "warnings":
    if not all(isinstance(item, str) for item in value):
        raise ValueError(...)
```

The existing Phase 8 validator's permissive scalar behavior does not need to be copied if Phase 9 can start cleaner.

### R11. Finding confidence factor may over-penalize contact/stability when axis is absent

Severity: **MEDIUM**

The plan defines `cf = min(axis.confidence, stability.confidence)`, with axis or stability missing falling back to `low` (`09-02-PLAN.md:330`). That means a high-confidence contact finding can be reduced because an unrelated axis metric is unavailable.

Risk:

- Contact-only or stability-only findings become systematically low-confidence when axis data is missing.
- This may be defensible as conservative v1, but it should be explicit.

Recommendation:

Use source-specific confidence factors:

- axis/pelvis signals: `min(axis.confidence, stability.confidence)` or axis-only
- stability signals: `stability.confidence`
- contact signals: `contact.confidence` plus phase/stability fallback if needed

If keeping the global min, document it as a deliberate false-positive reduction strategy and add a test proving contact confidence is intentionally capped when axis is missing.

### R12. The plan references a non-existent Phase 8 schema test path

Severity: **LOW-MEDIUM**

Plan 09-01 references `backend/tests/phase08/test_axis_schema_lockstep.py`, but the actual axis schema test is under `backend/tests/phase08_1/test_axis_schema_lockstep.py`. The Phase 8 umbrella lockstep test is `backend/tests/phase08/test_force_signals_lockstep.py`.

Risk:

- Executor wastes time looking for the wrong pattern source.
- Minor, but it undermines the "mirror existing pattern" instruction.

Recommendation:

Update references to:

- `backend/tests/phase08/test_force_signals_lockstep.py`
- `backend/tests/phase08_1/test_axis_schema_lockstep.py`
- `backend/tests/phase08/test_firestore_lockstep.py`
- `backend/tests/phase08_1/test_firestore_axis_validator.py`

## What I Would Do

I would keep the two-wave shape, but patch it before execution.

### Patch 09-01

1. Fix `ForcePatternInference` field order.
2. Add stricter dataclass validators for `warnings`, `findings`, and `version`.
3. In docs, specify both `phase_8_1_wave_0_transitional` and top-level `axis_metric_transitional`.
4. In tests, prefer dataclass `fields()` or targeted interface-block extraction over broad grep for schema lockstep where possible.

### Patch 09-02

1. Remove runtime import from `force_pattern_copy.py` to `force_pattern.py`, or make it `TYPE_CHECKING` only.
2. Do not import `fallback_body` in `force_pattern.py`; keep fallback copy as a downstream helper.
3. Reuse `_IPSF_TOLERANCE_DEG` from Wave 0.
4. Expand `_AXIS_IGNORE_WARNINGS` and check `force_signals_report.warnings`.
5. Replace `models.MODE_REFERENCE` with `models.MODE_EXPERT`.
6. Replace the raw "박제" grep with AST-scoped copy-value checks.
7. Make pipeline tests reuse `backend/tests/pipeline/test_pipeline_phase8.py` style directly.

## Technical Recommendation

The implementation should keep `force_pattern.py` as the dependency root:

```text
force_signals.py  ──►  force_pattern.py  ──►  pipeline/app.py
                 └──►  force_pattern_copy.py  (lookup-only, no runtime import back)
```

Avoid this:

```text
force_pattern.py  ◄──►  force_pattern_copy.py
```

For copy type annotations, runtime type reuse is not worth the import cycle. A duplicated `Literal` alias in `force_pattern_copy.py` is acceptable because lockstep tests already verify the values.

For the axis guard, I would treat the upstream warning model as two-tiered:

```python
report_axis_unavailable = "axis_metric_transitional" in report.warnings
metric_axis_unavailable = axis is None or any(
    w in _AXIS_IGNORE_WARNINGS for w in axis.warnings
)

if report_axis_unavailable or metric_axis_unavailable:
    warnings.append("axis_signal_unavailable")
    skip_axis_detectors()
```

That matches actual Phase 8.1 behavior and makes D-09-A2 enforceable.

## Positive Notes

- The phase boundary is well scoped: deterministic Layer 1 only, no Gemini/Cerebras leakage.
- 3-way contract lockstep is the right move for a new Firestore field consumed by Phase 11/12.
- The "0 findings means empty list, not fabricated cards" decision is correct.
- The AST copy gate is the right class of test; it just needs to be scoped to emitted strings.
- Reusing `backend/tests/pipeline/test_pipeline_phase8.py` gives a cheap real `_process` verification path.

## Final Recommendation

Do **not** execute 09-01/09-02 as-is. Apply the blocker fixes above, then execute. After those corrections, the plan is technically sound enough for autonomous implementation.

