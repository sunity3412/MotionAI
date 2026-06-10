---
phase: 09-forcedirectionpattern-3
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review-iteration-4
status: minor-revision-before-execution
reviewed_plans:
  - 09-01-PLAN.md
  - 09-02-PLAN.md
  - 09-VALIDATION.md
notes:
  - "09-RESEARCH.md treated as background only per user instruction; no research update required."
---

# Phase 9 Direct Review: Iteration 4

## Executive Verdict

4차 수정본은 3차 리뷰의 주요 execution blocker를 거의 다 해소했다. Wave 0 fixture spec은 실제 Phase 8 dataclass와 맞춰졌고, Firestore warning matrix도 action text까지 확장됐고, `pelvis_drop` nullable tilt guard와 ranking tie-break fixture 오류도 반영됐다. T1의 fragile `collect-only` gate를 제거한 결정도 합리적이다.

그래도 바로 실행하기 전에 작은 패치를 한 번 더 넣는 게 낫다. 남은 핵심은 `ForcePatternFinding` / `ForcePatternInference` dataclass runtime validator가 계약만큼 엄격하지 않은 부분이다. Phase 9의 Wave 0 목표가 “schema lockstep + input validation”인 만큼, 이 정도는 실행 전에 닫는 게 비용 대비 이득이 크다.

제 판정은 **minor-revision-before-execution**이다. 알고리즘/파이프라인 계획은 이제 실행 가능한 수준이고, 아래 R1/R2만 고치면 `ready-for-execution`으로 봐도 된다.

## What Was Fixed Since Iteration 3

- R1 fixed: Wave 0 fixture spec now matches actual `PhaseBoundary` and `ContactStabilityMetric` constructor fields in `09-01-PLAN.md:201-209`.
- R2 fixed: dataclass warning validator guidance now rejects empty strings via `isinstance(w, str) and w` in `09-01-PLAN.md:279-281`.
- R3 fixed in action text: Firestore validator tests now require the full strict warning matrix, total `1 PASS + 12 reject`, in `09-01-PLAN.md:217-224`.
- R4 fixed: `_detect_pelvis_drop` now has an explicit `None` tilt guard and regression test in `09-02-PLAN.md:357` and `09-02-PLAN.md:567`.
- R5 fixed: ranking tie-break fixture now expects `high_jitter` first when its confidence is higher in `09-02-PLAN.md:726`.
- R6 fixed by design choice: T1 no longer tries fragile `pytest --collect-only` before missing modules exist; it uses AST syntax check and leaves collection to later gates in `09-01-PLAN.md:236-238`.
- R7 fixed: quick gate now includes `tests/pipeline/test_pipeline_phase9.py` in `09-VALIDATION.md:23-31` and `09-02-PLAN.md:901`.
- R8 fixed: the always-pass severity placeholder test was removed; only AST + substring guards remain in `09-02-PLAN.md:628` and `09-02-PLAN.md:1030`.

## Remaining Findings

### R1. `ForcePatternFinding.phase` runtime validation is specified but not implemented or tested

Severity: **MEDIUM-HIGH**

The behavior section says `ForcePatternFinding.__post_init__` validates that `phase` is a `force_signals.MotionPhase` Literal value.

Evidence: `09-01-PLAN.md:252`.

But the implementation guidance lists checks for `pattern`, `source_signal`, `confidence`, `interpretation`, `joint_hint`, and `warnings`, while omitting `phase`.

Evidence: `09-01-PLAN.md:271-281`.

The planned dataclass tests also omit an invalid phase case.

Evidence: `09-01-PLAN.md:173-188`.

Risk:

- `ForcePatternFinding(phase='other', ...)` can be constructed if the executor follows the action block literally.
- Later `_rank_top3` uses `_PHASE_PRIORITY[f.phase]`; invalid phase then fails later as `KeyError`, far from the source of the bad data.

Recommendation:

Add a module-level `_MOTION_PHASES` import or reuse from `force_signals` if exported. Then validate:

```python
if self.phase not in _MOTION_PHASES:
    raise ValueError(...)
```

Add:

```python
ForcePatternFinding(phase="other", ...) raises
```

to `test_force_pattern_dataclass.py`.

### R2. Dataclass list fields do not enforce the container type

Severity: **MEDIUM**

The contract says `warnings: list[str]` and `findings: list[ForcePatternFinding]`.

Evidence: `09-01-PLAN.md:253`, `09-01-PLAN.md:271-279`.

But the validator guidance only checks element predicates:

```python
all(isinstance(f, ForcePatternFinding) for f in findings)
all(isinstance(w, str) and w for w in warnings)
```

That accepts tuples like `warnings=("x",)` and `findings=(finding,)`, even though the Firestore contract and TS contract are array/list-based.

Risk:

- Internal callers can create schema objects that violate the declared list contract.
- `dataclasses.asdict` still serializes tuples differently enough to make this a subtle contract drift rather than an obvious type error.

Recommendation:

Validate container type before element checks:

```python
if not isinstance(self.warnings, list):
    raise ValueError("warnings must be list[str]")
if not isinstance(self.findings, list):
    raise ValueError("findings must be list[ForcePatternFinding]")
```

Apply the same `warnings must be list[str]` check to `ForcePatternFinding.warnings`. Add tests for tuple warnings and tuple findings.

### R3. Some summary/threat text still says the old Firestore validator test count

Severity: **LOW**

The detailed action text is fixed to `1 PASS + 12 reject`, but the file table and threat register still say `PASS + 4 reject` / `5 case`.

Evidence:

- `09-01-PLAN.md:136`
- `09-01-PLAN.md:701`

Risk:

- Low execution risk because the actual task action is explicit.
- It can still confuse a future reviewer or executor scanning the summary first.

Recommendation:

Update those two stale phrases to match the full matrix: `1 PASS + 12 reject`.

### R4. Frontend normalization wording says `?? null`, but the snippet preserves `undefined`

Severity: **LOW**

The summary says `normalize()` does `forcePatternInference ?? null`.

Evidence: `09-01-PLAN.md:31`.

The actual snippet only normalizes when `result?.forcePatternInference` exists; if the field is missing, it remains `undefined`.

Evidence: `09-01-PLAN.md:591-609`.

This is not a typecheck blocker because `AnalysisResult.forcePatternInference?: ForcePatternInference | null` permits `undefined`. It is only a contract wording mismatch.

Recommendation:

Either change the summary to “optional field remains absent when missing”, or make the snippet explicitly set:

```ts
forcePatternInference: result.forcePatternInference ?? null
```

I would choose the wording change unless UI code requires strict null.

## Technical Recommendation

I would make one small Wave 0 patch:

1. Add `phase` runtime validation to `ForcePatternFinding`.
2. Enforce list container type for `warnings` and `findings`.
3. Add 3 dataclass tests: invalid phase, tuple warnings, tuple findings.
4. Update the two stale Firestore validator count references.

After that, I would execute Phase 9. The remaining frontend `undefined` vs `null` wording is not enough to block execution unless downstream UI explicitly relies on null.

## Final Recommendation

The plan is close. Do **not** spend another full planning cycle on it. Patch the dataclass validator hardening and stale count text, then proceed with execution.
