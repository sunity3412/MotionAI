# Phase 23 Direct Review — Iteration 4

Reviewer: Codex direct local review  
Date: 2026-06-22  
Scope: latest 23-CONTEXT / 23-01 / 23-02 / 23-03 after Iteration 3 fixes. No external skills, MCP, or web sources used.

## Verdict

Iteration 3 feedback has largely been incorporated. The plan now includes `cap_would_apply`, a typed `VisionFaultContext`, required `quantificationStatus` on applied audits, existing coach-cause UI wording, and FP/abstention split in eval.

I would still patch the items below before execution. The remaining risks are mostly boundary issues introduced by the new typed context: the plan asks one object to represent pre-apply collection data, post-apply audit data, and post-quantification geometry data.

## Findings

### HIGH-1: `VisionFaultContext.to_audit_dict()` overreaches; final audit status and quantification data are not available at collection time

`VisionFaultContext` is introduced in 23-01 as a pre-coach collection object with fields including `status`, `verdict`, `cap_would_apply`, and `quantification_status`, plus serializers `to_coach_context()`, `to_audit_dict()`, and `to_trace_dict()` (`23-01-PLAN.md:278`, `23-01-PLAN.md:288`). But the final `visionVeto.status` is decided only after `_apply_vision_veto` recomputes the cap against the built result (`23-01-PLAN.md:93-101`; current code does this at `backend/functions/pipeline/app.py:1727-1762`). Separately, the actual geometry payload is produced by 23-02 Task 1/2/4 after frame-specific angles and notches are computed (`23-02-PLAN.md:266-275`).

That means a pre-coach `VisionFaultContext` cannot safely own a complete `to_audit_dict()` unless the serializer is explicitly parameterized by the final apply decision and the later quantification result. The current field list has `quantification_status`, but it does not list the payload fields that Task 4 wants to serialize, such as `angleDeltas`, `bodyRelativeNotches`, `windowMedianAngleDeltas`, or quantification warning reasons (`23-02-PLAN.md:275`, `23-02-PLAN.md:282-285`). This creates two likely failure modes:

- `to_audit_dict()` emits an `applied`-looking audit from a pre-apply candidate, drifting from `_apply_vision_veto` final status.
- Implementers mutate or side-load raw dict fields after quantification, undermining the typed-owner guarantee that D-11 wanted.

**How I would fix it:** split the objects or make enrichment explicit.

Preferred shape:
- `VisionFaultContext`: pre-apply/pre-coach verdict context only. Fields: collection status, verdict, supported differences, selected frame pairs, alignment, telemetry, `cap_would_apply`.
- `VisionQuantificationResult`: post-geometry result. Fields: `quantificationStatus`, `angleDeltas`, `bodyRelativeNotches`, `windowMedianAngleDeltas`, warnings.
- `VisionVetoAuditBuilder` or `ctx.to_audit_dict(final_status=..., cap_applied=..., quantification=...)`: called only inside `_apply_vision_veto` after final cap computation.

Add tests that call `ctx.to_audit_dict()` without final status/quantification and expect it to fail fast or omit final audit fields. Also test the applied-but-quant-unavailable path through `_apply_vision_veto`, not only through the serializer.

### HIGH-2: `resource_limited` is treated as an eval abstention, but it is a resource/completion failure

23-03 now correctly separates false positives from abstentions, but it classifies `low_alignment_confidence` and `resource_limited` together as abstention (`23-03-PLAN.md:114`). That weakens the eval. `low_alignment_confidence` is a semantic alignment abstention; `resource_limited` means the planned sampling/support process did not complete under budget. Those are operationally different.

If `resource_limited` is counted as a normal abstention, a broken or under-budgeted implementation can avoid clean-case false positives and partially avoid recall obligations by timing out or exhausting the sample budget. The cost/latency gate helps, but it does not by itself assert that the intended quorum was completed.

**How I would fix it:** split eval outcome classes:

- `alignment_abstention_count`: `low_alignment_confidence` only.
- `resource_incomplete_count`: `resource_limited` / `samplingComplete=false`.
- `clean_abstention_count`: alignment abstentions only, if allowed by case class.
- `completion_pass`: every non-budget-stress eval case has `samplingComplete=true` and status is not `resource_limited`.

For the main Pod gate, `resource_limited` should fail completion/resource coverage unless the manifest marks the case as an intentional budget-stress case. It should not count as a true negative and should not be grouped with tempo-shift alignment abstention.

### MEDIUM-1: `_collect_vision_fault_context(score_result, ...)` invites the wrong call order

The plan says `_collect_vision_fault_context(score_result, ...)` reads `score_result["overallScore"]` to compute `cap_would_apply` (`23-01-PLAN.md:289-290`). But in the current pipeline, the final result dict is not available until `assemble.build_result(...)`, which happens after coach generation (`backend/functions/pipeline/app.py:2588-2670`). The numeric `overall` is available earlier (`backend/functions/pipeline/app.py:2441-2442`).

Because the function name and signature say `score_result`, an implementer can easily create the dict by moving `build_result` earlier or by calling collect after build_result. Either option risks breaking the now-critical order: collect before coach, coach before build_result, apply after build_result.

**How I would fix it:** change the contract to pass exactly what exists at that point:

```python
_collect_vision_fault_context(
    *,
    overall_score: int,
    dimension_scores: dict,
    mode: str,
    local_video_path: str | None,
    ...
)
```

Then add an ordering test or trace assertion: `overall` computed -> collect called -> `_build_coach_context` called -> coach writers called -> `assemble.build_result` called -> `_apply_vision_veto` called. Also assert no `assemble.build_result` call occurs before coach generation in the production path.

### MEDIUM-2: eval cache isolation is still under-specified across production, direct-adapter, baseline, cold, and warm arms

23-03 measures production seam, optional direct-adapter comparison, and same-model whole-video baseline (`23-03-PLAN.md:111-112`). It also measures cold-cache and warm-cache determinism (`23-03-PLAN.md:115`). The plan requires trace fields including `cacheKey` and `cacheHit` (`23-03-PLAN.md:126`, `23-03-PLAN.md:131`), but it does not require cache isolation between arms.

If direct-adapter still-frame runs, production seam runs, and whole-video baseline runs share a cache namespace or run in an order that warms each other, the cold/warm result can be misleading. This is especially important because the phase is changing `input_granularity`, selector version, frame indices, and path type.

**How I would fix it:** make each eval arm explicit:

- `arm`: `production_still`, `direct_adapter_still`, `whole_video_baseline`.
- `cache_namespace` or `run_id` per arm and per cold repetition.
- Cold assertions: `cacheHit=false` for the first cold run of each arm.
- Warm assertions: same cache key as the immediately preceding cold run and `cacheHit=true`.
- Cross-arm assertion: whole-video baseline cache key differs from still-frame production cache key; direct-adapter is not allowed to pre-warm the production gate run unless the harness marks it as warm intentionally.

## What Looks Resolved

- Iteration 3 HIGH-1 is reflected: `cap_would_apply` is now part of collect and coach injection gates.
- Iteration 3 HIGH-2 is mostly reflected: clean-case FP and abstention are split and coverage is required.
- Iteration 3 MED-1 is reflected: applied audits now require `quantificationStatus`, including unavailable.
- Iteration 3 MED-2 is reflected at the plan level: typed `VisionFaultContext` and serializer names are present.
- Iteration 3 LOW-1 is reflected: existing `CoachingTipDetailModal` may surface `detail2.causes` without new UI work.

## Recommended Patch Order

1. Fix the context/audit boundary first: pre-apply context must not own final audit status alone.
2. Split `resource_limited` out of eval abstention before Pod measurement.
3. Rename collect inputs from `score_result` to pre-build primitives like `overall_score`.
4. Add cache isolation fields to the eval manifest and JSON before the harness is written.
