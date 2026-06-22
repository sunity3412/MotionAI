# Phase 23 Direct Review - Iteration 5

Date: 2026-06-23
Reviewer: Codex direct review, no external skill/MCP
Scope: Fifth-pass review of Phase 23 plan artifacts after D-12 updates.

Reviewed artifacts:
- `23-CONTEXT.md`
- `23-01-PLAN.md`
- `23-02-PLAN.md`
- `23-03-PLAN.md`
- Prior direct reviews through Iteration 4

## Executive Summary

The D-12 updates resolved the largest object-ownership ambiguity: `VisionFaultContext` is now pre-apply/pre-coach only, `VisionQuantificationResult` owns post-geometry measurements, and the final audit is explicitly produced through `ctx.to_audit_dict(final_status=..., cap_applied=..., quantification=...)`.

The remaining risks are now mostly integration risks:

1. `VisionQuantificationResult` is specified and serialized, but the production call site that constructs it before `_apply_vision_veto` is still implicit.
2. Sampling completion semantics are split across Phase 23-01 and Phase 23-03: 23-01 allows a normal `applied` result after quorum even if budget expires, while 23-03 treats incomplete sampling as a completion failure.
3. Root-cause hypotheses are introduced inside Gemini differences, but the plan does not yet say they must be derived only from support-gated differences.
4. The pre-final `VisionFaultContext.status` name can still be confused with final audit status unless renamed or hard-enumerated.

## Findings

### HIGH-1: `VisionQuantificationResult` construction is still not wired as an explicit production step

**Risk**

The plan now cleanly separates:
- `VisionFaultContext`: pre-apply/pre-coach context
- `VisionQuantificationResult`: post-geometry measurements
- final audit dict: `_apply_vision_veto` serialization output

However, the production step that creates `VisionQuantificationResult` is still implied rather than specified as a concrete call site.

Evidence:
- `23-02-PLAN.md` Task 2 defines the notch helper and says it returns `VisionQuantificationResult`.
- `23-02-PLAN.md` Task 4 says `_apply_vision_veto` passes Task 2's `VisionQuantificationResult` into `ctx.to_audit_dict(...)`.
- `23-02-PLAN.md` Task 5 says `_apply_vision_veto(..., quantification=<VisionQuantificationResult, 23-02 Task 2/4>)`, but does not define the production function that builds that object, where it is called, or which exact selected-frame/reference inputs it consumes.

This leaves room for a passing serializer test while production still sends `None`, a raw dict, stale angle data, or a quantification object built after the audit has already been emitted.

**How I would fix it**

Add one explicit production seam:

```python
quantification = _build_vision_quantification_result(
    fault_context=vision_fault_context,
    selected_frame_pair=selected_frame_pair,
    current_measurements=current_measurements,
    reference_measurements=reference_measurements,
    body_profile=body_profile,
    pole_geometry=pole_geometry,
)
```

Then require the pipeline order:

```text
overall_score
-> _collect_vision_fault_context(...)
-> coach context/writers
-> _build_result(...)
-> _build_vision_quantification_result(...)
-> _apply_vision_veto(..., quantification=quantification)
```

If geometry or frame-pair inputs are missing, `_build_vision_quantification_result` should return:

```python
VisionQuantificationResult(
    quantificationStatus="unavailable",
    warnings=[...],
)
```

It should not return `None`.

Acceptance tests I would add:
- Cap-applied path calls `_build_vision_quantification_result` exactly once before `_apply_vision_veto`.
- `_apply_vision_veto` receives a `VisionQuantificationResult`, not a dict or `None`.
- Applied audit always includes `quantificationStatus`.
- Non-applied audit still has no final measurement fields.
- Missing per-frame inputs produce `quantificationStatus="unavailable"` through the full `_apply_vision_veto` path.

### HIGH-2: Sampling completion semantics can make `applied` results nondeterministic

**Risk**

`23-01-PLAN.md` says that if the budget is exhausted after quorum is complete, the result is still a normal `applied`.

`23-03-PLAN.md` now correctly says `resource_limited` is a completion failure, not an abstention, and adds `completion_pass` requiring non-budget-stress cases to be sampling-complete and not `resource_limited`.

The gap is the intermediate case:

```text
quorum complete
budget exhausted
not all planned Gemini calls sampled
normal applied
```

If this remains allowed, the same clip can produce an `applied` decision based on a partial sample set whose size depends on wall-clock timing, cache warmth, network latency, or Gemini response time. That undermines the Phase 23 evaluation gate because a clean `applied` result may hide incomplete sampling unless every applied audit also carries reliable sampling telemetry.

Current plan language appears to attach completion telemetry primarily to `resource_limited`, not to normal applied results.

**How I would fix it**

I would choose one policy and make it contract-level:

Option A, preferred for determinism:

```text
Main evaluation path:
Any budget exhaustion before all planned calls complete => resource_limited.
Normal applied requires samplingComplete=true.
```

Budget-stress fixtures can still validate graceful degradation, but the main Pod UAT should never accept partial sampling as normal success.

Option B, if early quorum application is intentional:

```text
supportComplete=true may allow cap application,
but samplingComplete=false must be recorded on the applied audit,
and completion_pass must fail or separately bucket it unless the fixture is marked budget_stress.
```

For Option B, add audit fields to applied results, not only `resource_limited`:

```json
{
  "supportComplete": true,
  "samplingComplete": false,
  "completedCalls": 3,
  "plannedCalls": 5,
  "budgetStress": false
}
```

Tests I would require:
- Fake-clock test where budget expires after quorum but before all planned calls.
- Main-eval fixture must not count that result as clean success.
- Warm-cache and cold-cache runs cannot change whether the clip is classified as completion-pass.

### MEDIUM-1: Root-cause hypotheses must be support-gated before entering coach/audit context

**Risk**

`23-02-PLAN.md` introduces `root_cause_hypothesis` inside Gemini `differences[]`.
`23-01-PLAN.md` adds support gates for single-frame, alias, and body-relative validation.
`VisionFaultContext` then carries `root_cause_hypotheses` into coach context.

If root causes are copied from raw Gemini differences before support filtering, an unsupported hallucinated root cause can still affect the coach report or audit even though the corresponding visual difference was dropped.

Example failure mode:

```text
Gemini raw difference:
  "left knee collapsed inward because hips opened early"

Support gate:
  drops the difference due to single-frame/no body-relative support

Bug:
  root_cause_hypothesis is still copied into coach context
```

That would reintroduce the same “one-frame explanation” problem Phase 23 is trying to prevent.

**How I would fix it**

Build root causes only from the final support-gated difference list:

```python
supported_differences = _filter_supported_differences(raw_differences, ...)
root_cause_hypotheses = _derive_root_causes_from_supported_differences(
    supported_differences
)
```

Each root cause should preserve provenance:

```python
RootCauseHypothesis(
    text=...,
    fault_key=...,
    source_difference_ids=[...],
    support_count=...,
)
```

Tests I would add:
- Unsupported single-frame root cause is absent from coach context and audit.
- Supported alias/root-cause pair survives and includes source difference IDs.
- No root cause is emitted if all visual differences are dropped by support gates.

### MEDIUM-2: `VisionFaultContext.status` should not share vocabulary with final audit status

**Risk**

D-12 correctly says final audit status belongs to `ctx.to_audit_dict(final_status=...)`, not to `VisionFaultContext`. But `VisionFaultContext` still appears to include a generic `status(collection status)` field.

That name is likely to drift back into final-state meanings such as:

```text
applied
not_applicable
low_alignment_confidence
resource_limited
```

Once that happens, pre-coach gating and final audit serialization can again become entangled.

**How I would fix it**

Rename the field:

```python
collection_status: VisionFaultCollectionStatus
```

Use a deliberately pre-final enum:

```python
candidate_verdict
no_fault
low_alignment_confidence
resource_limited
disabled
mode3_held
missing_reference
missing_current_video
skipped_error
```

Then define:

```python
eligible_for_coach = (
    collection_status == "candidate_verdict"
    and cap_would_apply is True
)
```

Tests I would add:
- `VisionFaultContext` cannot be constructed with final status `"applied"`.
- `to_audit_dict(final_status="applied", ...)` is the only path that emits final status.
- Coach gate reads `collection_status`, not final audit status.

## Consolidated Recommendation

Before execution, I would update the Phase 23 plans with four explicit contract additions:

1. Add `_build_vision_quantification_result(...)` as a named production seam and place it in the pipeline order before `_apply_vision_veto`.
2. Decide whether partial sampling can ever produce normal `applied`. My recommendation is no for the main evaluation path: normal `applied` should require `samplingComplete=true`.
3. Build `root_cause_hypotheses` only from support-gated differences, never from raw Gemini output.
4. Rename `VisionFaultContext.status` to `collection_status` and forbid final audit status values in that pre-final object.

With those changes, the Phase 23 plan should be materially safer to execute: the remaining complexity becomes implementation work rather than unresolved contract ambiguity.
