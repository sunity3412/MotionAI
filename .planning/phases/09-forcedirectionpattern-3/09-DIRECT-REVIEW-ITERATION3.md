---
phase: 09-forcedirectionpattern-3
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review-iteration-3
status: revise-before-execution
reviewed_plans:
  - 09-01-PLAN.md
  - 09-02-PLAN.md
  - 09-VALIDATION.md
notes:
  - "09-RESEARCH.md treated as background only per user instruction; no research update required."
---

# Phase 9 Direct Review: Iteration 3

## Executive Verdict

3차 수정본은 2차 리뷰의 핵심 항목을 대부분 제대로 반영했다. 특히 frontend `normalize()` 는 typed `result` 변수를 쓰도록 바뀌었고, Firestore warning validator 는 strict `list[str]` 쪽으로 정리됐고, `MappingProxyType` + AST extractor target mismatch 도 `_FORCE_PATTERN_COPY_DATA` 로 맞춰졌다. pipeline test 경로도 `backend/tests/pipeline/test_pipeline_phase9.py` 로 정리됐다.

그래도 **as-is 실행은 아직 보류**가 맞다. 이번에 남은 리스크는 큰 아키텍처 문제가 아니라 “실행하면 테스트가 바로 깨질 가능성이 높은 세부 불일치”다. 특히 Wave 0 fixture factory 가 현재 Phase 8 dataclass 생성자와 맞지 않고, dataclass warning validator spec 과 테스트가 서로 충돌하며, `pelvis_drop` detector 는 실제 `AxisDeviationMetric` 의 nullable tilt 값을 고려하지 않아 TypeError 가능성이 있다.

저라면 아래 BLOCKER/HIGH 항목만 짧게 패치한 뒤 실행한다. 수정량은 작지만, 안 고치고 실행하면 Wave 0~1 초반에서 불필요하게 멈출 가능성이 높다.

## What Was Fixed Since Iteration 2

- Frontend R1 fixed: `09-01-PLAN.md:570-595` now uses `result?.forcePatternInference`, reconstructs `result`, and explicitly forbids top-level `forcePatternInference`.
- Firestore R2 mostly fixed: validator loops now reject non-string and empty-string warning entries in `09-01-PLAN.md:462-470` and `09-01-PLAN.md:499-505`.
- MappingProxy R3 fixed: AST extractor now targets `_FORCE_PATTERN_COPY_DATA`, `_MODE_PREFIX`, `_FALLBACK_BODY` and asserts `_FORCE_PATTERN_COPY_DATA >= 18` in `09-02-PLAN.md:318-321`.
- Pipeline path R4 fixed: T4 now consistently creates/runs `backend/tests/pipeline/test_pipeline_phase9.py` in `09-02-PLAN.md:844-895`; VALIDATION rows also reference that path.
- T4 stale helper guidance R5 fixed: the plan now explicitly says to use real `_process`, not a mini-helper, and names the real Phase 8 reference test in `09-02-PLAN.md:853-867`.
- Dataclass coverage R6 improved: strict validator test cases were added for invalid warning entries, invalid `joint_hint`, empty `version`, and non-`ForcePatternFinding` findings in `09-01-PLAN.md:179-187`.
- R7 mostly fixed: the key `ForcePatternInference(...)` construction example is now in dataclass field order at `09-01-PLAN.md:171`.
- R8 narrowed correctly: `MappingProxyType` is intentionally scoped only to `_FORCE_PATTERN_COPY`, with threat model language updated in `09-02-PLAN.md:242` and `09-02-PLAN.md:990-999`.

## Remaining Findings

### R1. Wave 0 fixture factory does not match current Phase 8 dataclasses

Severity: **BLOCKER**

Plan 09-01 tells `conftest.py` to expose:

- `_make_phase_boundary(phase='lock', start_ms=0, end_ms=1000, confidence='high', source='pose')`
- `_make_contact_metric(phase='lock', estimated_stable=True, near_pole_ratio=1.0, warnings=(), measurement_kind='keypoint', contact_point='left_hand')`

Evidence: `09-01-PLAN.md:198-204`.

Actual `PhaseBoundary` requires `start_frame_idx`, `end_frame_idx`, `start_ms`, `end_ms`, and `source` must be one of `"heuristic"`, `"gemini_assisted"`, `"heuristic_fallback"`. `source='pose'` is invalid. Evidence: `backend/shared/python/sunity_shared/analysis/force_signals.py:330-337`.

Actual contact class is `ContactStabilityMetric`, not `ContactMetric`, and it requires fields such as `distance_to_pole_norm`, `lost_near_pole_at_ms`, `coordinate_space`, `severity`, and `confidence`. The plan does not tell the fixture to supply those.

Risk:

- Wave 0 `conftest.py` fixture creation fails before inference tests matter.
- The executor may spend time debugging generated tests instead of implementing Phase 9.

Recommendation:

Patch the fixture spec explicitly:

```python
def _make_phase_boundary(
    phase="lock",
    start_frame_idx=0,
    end_frame_idx=10,
    start_ms=0,
    end_ms=1000,
    confidence="high",
    source="heuristic",
):
    return force_signals.PhaseBoundary(...)
```

For contact, name the actual class and fill all required fields:

```python
def _make_contact_metric(...):
    return force_signals.ContactStabilityMetric(
        phase=phase,
        contact_point=contact_point,
        measurement_kind=measurement_kind,
        estimated_stable=estimated_stable,
        distance_to_pole_norm=None,
        near_pole_ratio=near_pole_ratio,
        lost_near_pole_at_ms=None,
        coordinate_space="image_2d",
        severity="low",
        confidence="high",
        warnings=list(warnings),
    )
```

### R2. Dataclass warning validator still conflicts with the new tests

Severity: **HIGH**

The test behavior now says:

- `ForcePatternFinding(warnings=[''])` raises
- `ForcePatternInference(warnings=[1])` raises

Evidence: `09-01-PLAN.md:179-187`.

But the implementation guidance only says:

```python
all(isinstance(w, str) for w in warnings)
```

Evidence: `09-01-PLAN.md:262-264`.

That accepts empty strings. So the planned tests and planned implementation disagree.

Risk:

- `test_force_pattern_dataclass.py` fails if the executor follows the implementation block.
- Warning code contract drifts between Python dataclass and Firestore validator. Firestore rejects `""`, dataclass accepts it.

Recommendation:

Use the same rule everywhere:

```python
all(isinstance(w, str) and w for w in warnings)
```

Apply this to both `ForcePatternFinding.warnings` and `ForcePatternInference.warnings`. Add `ForcePatternInference(warnings=[''])` to the tests as well, not only finding-level warnings.

### R3. Firestore validator test count undercuts the stricter behavior list

Severity: **MEDIUM-HIGH**

The behavior section requires finding-level and top-level rejects for non-str and empty-string warnings, including `[1]`, `[True]`, `[None]`, and `[""]`.

Evidence: `09-01-PLAN.md:172`.

But the action section still says `test_firestore_lockstep_phase9.py` runs only “5 cases (1 PASS + 4 reject)”.

Evidence: `09-01-PLAN.md:210`.

Risk:

- Executor can satisfy the action text while missing top-level warning rejects.
- This reopens the exact class of issue fixed in iteration 2.

Recommendation:

Change the action text to require the full matrix:

- valid payload
- nested dict reject
- list outside whitelist reject
- nested list reject
- finding warnings reject `[1]`, `[True]`, `[None]`, `[""]`
- top-level warnings reject `[1]`, `[True]`, `[None]`, `[""]`

If the exact count matters, call it “1 PASS + 11 reject cases” or use parameterized tests.

### R4. `pelvis_drop` detector can crash on nullable tilt values

Severity: **HIGH**

Plan 09-02 specifies:

```text
hip_tilt > 20.0 AND (hip_tilt - shoulder_tilt) > 10.0
```

Evidence: `09-02-PLAN.md:357`.

But current Phase 8.1 code can produce `AxisDeviationMetric(shoulder_tilt=None, hip_tilt=None, warnings=list(base_warnings))` for a phase when no tilt samples exist, without necessarily adding `tilt_unavailable` at that per-phase point.

Evidence: `backend/shared/python/sunity_shared/analysis/force_signals.py:1132-1153`.

Risk:

- `_detect_pelvis_drop` can raise `TypeError` on `None > 20.0` or `None - float`.
- This is a real production-path robustness issue, not just a test problem.

Recommendation:

Guard the detector:

```python
if axis.shoulder_tilt is None or axis.hip_tilt is None:
    return []
```

Also add a test:

```python
test_pelvis_drop_skips_when_tilt_none
```

I would also consider adding `axis_signal_unavailable` when tilt values are missing, but the minimum safe fix is to skip without raising.

### R5. Ranking tie-break test fixture has contradictory math

Severity: **HIGH**

The `test_tie_break_confidence_desc` example says:

```text
high_jerk confidence=0.6 vs high_jitter confidence=0.6375
score 동일 = 0.51 → high_jerk first if confidence higher
```

Evidence: `09-02-PLAN.md:736`.

But `0.6375` is greater than `0.6`. If score, phase priority, and signal priority are equal, the implementation should put `high_jitter` first by confidence DESC.

Risk:

- A correct `_rank_top3` implementation fails the planned test.
- Or the executor distorts the ranking implementation to satisfy a bad example.

Recommendation:

Either change the expected winner to `high_jitter`, or choose numbers where `high_jerk` actually has higher confidence while preserving equal score. The simpler patch is:

```text
Expected: high_jitter first, because confidence 0.6375 > 0.6.
```

### R6. T1 RED test collection is fragile unless imports are delayed

Severity: **MEDIUM**

T1 writes RED tests before `force_pattern.py`, docs §9.11, and validators exist, then runs:

```bash
pytest tests/phase09/ --collect-only -q | grep ...
```

Evidence: `09-01-PLAN.md:214-222`.

The same section says the tests import `force_pattern.ForcePatternFinding` and `ForcePatternInference`.

Evidence: `09-01-PLAN.md:212`.

Risk:

- If those imports are top-level, pytest collection fails because `force_pattern.py` does not exist yet.
- The pipe also lacks `pipefail`, so a collection failure can be hidden if later pipeline stages still succeed unexpectedly.

Recommendation:

Make the RED-test instruction explicit:

- No top-level import of modules that do not exist yet in T1.
- Put missing-module imports inside test functions, or create a minimal importable schema stub in T2 before running collect.
- Replace the pipe gate with a safer command or add `set -o pipefail` in a shell script.

### R7. Wave-level quick gate still omits the pipeline integration test

Severity: **LOW-MEDIUM**

T4 correctly runs:

```bash
cd backend && pytest tests/pipeline/test_pipeline_phase9.py -x -q
```

Evidence: `09-02-PLAN.md:892-895`.

But the global “after every task commit” and Wave 1 summary still emphasize only:

```bash
cd backend && pytest tests/phase09/ -x -q
```

Evidence: `09-VALIDATION.md:23-31`, `09-02-PLAN.md:911`, `09-02-PLAN.md:971`.

The final full backend suite will catch it, but the fast Wave 1 gate can give a false sense of completion while skipping `tests/pipeline/test_pipeline_phase9.py`.

Recommendation:

Change Wave 1 fast gate to:

```bash
cd backend && pytest tests/phase09/ tests/pipeline/test_pipeline_phase9.py -x -q
```

Keep full backend suite as the final regression gate.

### R8. One severity-guard test is intentionally always-pass

Severity: **LOW**

`test_stability_severity_access_is_allowed_by_guard` checks for a placeholder string that is not expected to exist.

Evidence: `09-02-PLAN.md:619-637`.

Risk:

- This test documents intent, but it does not verify behavior.

Recommendation:

Either remove it, or replace it with a direct assertion that the AST guard only flags receiver names in the axis set and ignores a synthetic `stab.severity` snippet parsed in-memory.

## Technical Recommendation

I would patch the plan in this order:

1. Fix Wave 0 `conftest.py` fixture specs to match `PhaseBoundary` and `ContactStabilityMetric`.
2. Make dataclass warning validators reject empty strings and add the missing top-level empty-string test.
3. Expand `test_firestore_lockstep_phase9.py` action text to match the full strict warning matrix.
4. Add nullable tilt guards to `_detect_pelvis_drop` and a regression test.
5. Correct the `test_tie_break_confidence_desc` fixture expectation.
6. Make T1 RED test collection robust by delaying missing-module imports.
7. Include `tests/pipeline/test_pipeline_phase9.py` in the Wave 1 fast gate.

After those patches, I would consider the plan ready to execute. The remaining design choices, including conservative global confidence capping when axis is missing, are acceptable if intentionally documented as v1 behavior.

## Final Recommendation

Do **not** execute the 3차 revised plan as-is. The architecture is now mostly sound, and the 2차 blockers are largely fixed, but the current plan still contains enough concrete execution mismatches to break early tests. Patch the items above, then proceed with Phase 9 execution.
