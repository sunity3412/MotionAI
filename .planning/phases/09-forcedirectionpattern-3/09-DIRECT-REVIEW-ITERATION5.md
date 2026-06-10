---
phase: 09-forcedirectionpattern-3
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review-iteration-5
status: ready-with-minor-notes
reviewed_plans:
  - 09-01-PLAN.md
  - 09-02-PLAN.md
  - 09-VALIDATION.md
notes:
  - "09-RESEARCH.md treated as background only per user instruction; no research update required."
---

# Phase 9 Direct Review: Iteration 5

## Executive Verdict

5차 수정본은 4차에서 남긴 실행 전 hardening 항목을 사실상 반영했다. `ForcePatternFinding.phase` invalid case, tuple `warnings`, tuple `findings` 테스트가 추가됐고, dataclass validator guidance도 `isinstance(..., list)`까지 확장됐다. Firestore validator test count와 frontend `undefined` wording도 정리됐다.

판정은 **ready-with-minor-notes**다. 이제 큰 execution blocker는 보이지 않는다. 다만 `_MOTION_PHASES` import 지시가 한 줄에서 누락된 점과 Firestore validator의 “화이트리스트” 문구가 실제 구현보다 강하게 쓰인 점은 실행 전에 작은 패치로 정리하는 게 좋다.

저라면 더 이상 리뷰 루프를 돌리지 않고, 아래 minor items만 바로 고친 뒤 Phase 9 실행으로 넘어간다.

## What Was Fixed Since Iteration 4

- R1 fixed: invalid phase test added in `09-01-PLAN.md:189`; implementation guidance now requires `phase in _MOTION_PHASES` in `09-01-PLAN.md:285`.
- R2 fixed: tuple container rejects added for finding warnings, inference warnings, and inference findings in `09-01-PLAN.md:190-192`; implementation guidance now requires `isinstance(findings, list)` and `isinstance(warnings, list)` in `09-01-PLAN.md:282-285`.
- R3 fixed: file table and threat register now say `1 PASS + 12 reject`, not the old `PASS + 4 reject`, in `09-01-PLAN.md:136` and `09-01-PLAN.md:705`.
- R4 fixed: frontend summary now correctly says missing `forcePatternInference` remains `undefined` and that this is allowed by the optional TS contract in `09-01-PLAN.md:31`.

## Remaining Findings

### R1. `_MOTION_PHASES` is required but missing from the concrete import line

Severity: **LOW-MEDIUM**

The validator guidance says `ForcePatternFinding` must check:

```text
phase in _MOTION_PHASES
```

Evidence: `09-01-PLAN.md:285`.

But the concrete import instruction still says:

```python
from .force_signals import MetricConfidence, MotionPhase
```

Evidence: `09-01-PLAN.md:271`.

`_MOTION_PHASES` exists in the current codebase at `backend/shared/python/sunity_shared/analysis/force_signals.py:123`, so importing it is technically possible. The plan just needs to say so in the import line.

Risk:

- Executor copies the import line literally, implements the phase check, and gets `NameError: name '_MOTION_PHASES' is not defined`.

Recommendation:

Change the import instruction to:

```python
from .force_signals import MetricConfidence, MotionPhase, _MOTION_PHASES
```

Alternatively define a local `_MOTION_PHASES = frozenset({"entry", "lock", "transition", "final_shape", "hold"})` in `force_pattern.py`, but importing the existing set is cleaner for lockstep.

### R2. Firestore validator says “8 field whitelist” but does not whitelist scalar keys

Severity: **LOW-MEDIUM**

The validator docstring says:

```python
"""Phase 9 finding entry dict 검증 — 8 필드 화이트리스트."""
```

Evidence: `09-01-PLAN.md:464-465`.

But the implementation accepts any scalar key in finding dicts:

```python
for k, v in d.items():
    if v is None or isinstance(v, (str, int, float, bool)):
        continue
```

Evidence: `09-01-PLAN.md:468-471`.

So `{"unexpectedScalar": "x"}` passes. That may be acceptable if this validator’s only responsibility is Firestore nested-array safety, but then the “8 field whitelist” wording is inaccurate.

Risk:

- Low immediate runtime risk because the dataclass path controls normal backend writes.
- Contract risk if future call paths pass raw dicts directly into `complete_analysis(force_pattern_inference=...)`.

Recommendation:

Pick one:

1. Enforce actual key whitelist:

```python
_FORCE_PATTERN_FINDING_KEYS = frozenset({
    "pattern", "phase", "sourceSignal", "source_signal", "reason",
    "interpretation", "confidence", "jointHint", "joint_hint", "warnings",
})
if k not in _FORCE_PATTERN_FINDING_KEYS:
    raise ValueError(...)
```

2. Or rename the docstring/comment to “nested-array safety validator” and explicitly state scalar extra keys are not rejected here.

Given Phase 9’s schema-lockstep emphasis, I would enforce the whitelist and add one reject test for an unexpected scalar key.

### R3. Validation runtime estimate is now stale

Severity: **LOW**

`09-VALIDATION.md` quick command now includes both `tests/phase09/` and `tests/pipeline/test_pipeline_phase9.py`, but estimated runtime still says `~15 seconds (phase09 only)`.

Evidence: `09-VALIDATION.md:23-25`.

Risk:

- None for correctness.
- Minor planning accuracy issue.

Recommendation:

Update the estimate to mention `phase09 + pipeline_phase9`, or remove the exact 15-second claim.

## Technical Recommendation

I would apply a tiny final patch:

1. Add `_MOTION_PHASES` to the `force_pattern.py` import instruction.
2. Either enforce Firestore finding-key whitelist or soften the misleading “8 field whitelist” wording.
3. Refresh the quick-run runtime estimate.

After that, execute Phase 9. I would not request a sixth full review unless the execution plan changes materially.

## Final Recommendation

Proceed after the minor patch above. The plan is now structurally sound: schema lockstep, inference logic, canned copy safety, pipeline wiring, and validation gates are aligned enough for implementation.
