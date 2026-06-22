# Phase 23 Direct Review — Iteration 3

Reviewer: Codex direct local review  
Date: 2026-06-22  
Scope: latest 23-CONTEXT / 23-01 / 23-02 / 23-03 after Iteration 2 fixes. No external skills, MCP, or web sources used.

## Verdict

The Iteration 2 architecture fixes are mostly reflected: collect/apply ownership is now split, still-frame extraction cleanup is specified, Mode 3 is deferred, and eval trace fields are much stronger.

I still would not treat the phase as execution-ready until the HIGH items below are patched. The remaining risks are less about "missing feature" and more about subtle status semantics: the plan now collects a vision verdict before coach generation, but cap applicability and applied/not-applicable status are finalized later.

## Findings

### HIGH-1: pre-coach root-cause injection can violate the "non-applied paths do not inject causes" rule

The revised plan says `_collect_vision_fault_context` runs before coach generation and its `VisionFaultContext` is injected into `_build_coach_context` (`23-02-PLAN.md:290`, `23-02-PLAN.md:297-300`). It also says non-applied paths must not inject vision causes into coach output (`23-02-PLAN.md:294`, `23-02-PLAN.md:310`).

The problem is that "applied" is not just a verdict property. In the current implementation, a vision verdict becomes `applied` only if `apply_downward_cap(overall, severity)` returns a value lower than `overallScore` (`backend/functions/pipeline/app.py:1727-1762`). The cap function itself is `min(overall, cap)` (`backend/shared/python/sunity_shared/analysis/vision_veto.py:104-118`). So a real verdict can be valid but still become `not_applicable`, for example `severity="minor"` with `overallScore=88`, or `severity="moderate"` with `overallScore=70`.

`23-01-PLAN.md:259` names the collect input `score_result_or_meta`, but it does not explicitly require an `overallScore`/cap eligibility decision or a `willApplyVisionCap` flag before coach injection. That leaves a path where the coach already receives "폴 밀착이 풀린 것으로 보임", then `_apply_vision_veto` later returns `not_applicable`. That would directly contradict the non-applied-path test.

**How I would fix it:** make cap eligibility part of the pre-coach contract. `_collect_vision_fault_context` should receive the prospective `overallScore` or complete `score_result`, compute `cap_would_apply = apply_downward_cap(overallScore, verdict.severity) < overallScore` with the same production cap function, and expose it on `VisionFaultContext`. Only inject root-cause data into coach writers when `cap_would_apply=true` and the status is otherwise eligible. If the product wants root-cause coaching even when the cap does not lower the score, split that into a separate explicit status such as `visionFaultCandidate`, but do not reuse the current `applied` semantics.

Add tests:
- `severity="minor"`, `overallScore=88` -> audit `not_applicable`, coach causes do not include vision root cause.
- `severity="moderate"`, `overallScore=92` -> audit `applied`, coach causes include vision root cause.
- `severity="none"` or score-free statuses -> no coach root-cause injection.

### HIGH-2: eval false-positive gate can pass by abstaining on clean cases

The eval plan requires `false_positive_count = 0` across elite clean / imperfect clean / occluded / spinning / tempo-shifted cases (`23-03-PLAN.md:138`, `23-03-PLAN.md:149`). It also allows tempo-shifted/start-offset cases to become `low_alignment_confidence` (`23-03-PLAN.md:140`, `23-03-PLAN.md:151`).

That is directionally right, but the metric is under-specified. A harness that returns `low_alignment_confidence` for all clean cases can report `false_positive_count=0` while providing no evidence that specificity was preserved on evaluable clean inputs. This is especially risky because 23-03 now has strong trace fields (`23-03-PLAN.md:104`, `23-03-PLAN.md:147`), so the pass/fail can look rigorous while the denominator is still wrong.

**How I would fix it:** separate false positives from abstentions in the JSON and gates:
- `clean_applied_fault_count`
- `clean_true_negative_count`
- `clean_abstention_count`
- `clean_evaluable_count`
- `abstention_allowed` per case

Then gate by case class. For elite clean / imperfect clean / occluded / spinning, require an evaluable non-fault result (`none` or `not_applicable`) unless the manifest explicitly marks the case as alignment-unverifiable. For tempo-shifted, allow `low_alignment_confidence`, but count it as an abstention, not a true negative. Keep `false_positive_count=0`, but add a coverage threshold so "all abstained" cannot pass.

### MEDIUM-1: applied-but-quantification-unavailable is not explicitly accepted

Task 4 says applied audits should store frame-specific angles, deterministic body-relative notches, root-cause hypothesis, and `quantificationStatus` (`23-02-PLAN.md:248`, `23-02-PLAN.md:256`, `23-02-PLAN.md:263`). It also says non-applied/held/disabled paths should not have quantification fields (`23-02-PLAN.md:251`, `23-02-PLAN.md:267`).

The missing case is "the vision veto is applied, but same-frame quantification inputs are unavailable." The threat register expects graceful handling with `quantificationStatus="unavailable"` (`23-02-PLAN.md:338`), but the acceptance criteria do not force the applied audit to preserve the cap/root-cause while omitting only the geometry fields.

**How I would fix it:** make `quantificationStatus` mandatory on applied vision audits, with values like `available` and `unavailable`. Add a test where the verdict applies a cap but `FramePairMeasurementContext` is missing required per-frame keypoints. Expected result: `visionVeto.status="applied"`, `capApplied` and root-cause fields remain, `quantificationStatus="unavailable"`, `angleDeltas`/`bodyRelativeNotches` are absent, and a warning/telemetry reason is recorded. Do not downgrade this to `not_applicable` and do not crash.

### MEDIUM-2: `VisionFaultContext` is a cross-module contract but still lacks a typed schema owner

The plan moves `VisionFaultContext` across pipeline collection, coach context injection, writer prompt payloads, audit attach, and eval trace (`23-01-PLAN.md:251`, `23-01-PLAN.md:259`, `23-02-PLAN.md:290-300`, `23-03-PLAN.md:104`). That is now a real internal API, not a local dict.

If this remains an ad hoc dict, key drift is likely: `root_cause_hypothesis` vs `rootCauseHypotheses`, status vs path, selected frames vs trace fields, and coach-only vs audit-only data can diverge while tests monkeypatch around it.

**How I would fix it:** define a single dataclass/TypedDict owner, probably in `backend/shared/python/sunity_shared/analysis/vision_veto.py` or a nearby shared model module:
- `status`
- `verdict`
- `supported_differences`
- `root_cause_hypotheses`
- `selected_frame_pairs`
- `alignment`
- `telemetry`
- `cap_would_apply`
- `quantification_status`

Give it explicit serializers: `to_coach_context()`, `to_audit_dict()`, and `to_trace_dict()`. Tests should construct this type rather than raw dicts, and writer tests should consume `to_coach_context()` so prompt payload and audit serialization cannot silently fork.

### LOW-1: UI deferral wording is now misleading for coach causes

`23-02-PLAN.md:257` says coach-report rendering is deferred and `result.tsx` / coach-report render components should not change. That is correct for new quantification UI and visual overlays. But the current app already renders `detail2.causes` in `CoachingTipDetailModal` (`app/src/components/CoachingTipDetailModal.tsx:105-125`). If Task 5 successfully injects vision root causes into `coachingTips[].detail2.causes`, they may appear in the existing modal without any UI file changes.

**How I would fix it:** adjust the scope language rather than changing UI. Say "new quantification UI, result.tsx angle/notch rendering, and visual overlays are deferred; existing coach cause rendering may surface newly generated `detail2.causes` automatically." That prevents QA from treating automatic display through the existing component as either scope creep or a missing follow-up.

## What Looks Resolved

- Mode 3 scope is now explicitly deferred to B-15a.
- `_collect_vision_fault_context` vs `_apply_vision_veto` ownership is now represented in 23-01, 23-02, and 23-03.
- `SelectedFramePair` extraction, local file cleanup, and keypoint visibility before collect are now specified.
- Eval path now requires runtime trace fields rather than source grep.
- Coach writer prompt-payload tests are now included for both writer paths.

## Recommended Patch Order

1. Patch HIGH-1 first because it affects production ordering and coach correctness.
2. Patch HIGH-2 before Pod eval, otherwise the expensive eval can produce a misleading pass.
3. Add the applied-but-quantification-unavailable test while implementing 23-02 Task 4.
4. Add the typed `VisionFaultContext` contract before writing broad pipeline tests, so the tests lock the real API shape.
