# Phase 20 Direct Review - v2 Gemini Vision Veto

**Reviewed:** 2026-06-19  
**Reviewer:** Codex direct review (not external reviewer)  
**Scope:** `.planning/phases/20-v2-gemini/20-01~04-PLAN.md`, `20-CONTEXT.md`, `20-RESEARCH.md`, `20-VALIDATION.md`  
**Review stance:** false-positive fix safety review. Primary failure mode = vision accidentally lets a false positive survive or creates a new overconfident score.

## Summary

The phase direction is mostly right: D-01 through D-08 are coherent, and the plans repeatedly encode the right primitives: terminal `min()` cap, no weighted blending, no score fields in the Gemini schema, severity-only vision output, sequential Pod eval, and branch-3 Mode3 score suppression.

The remaining risks are not about the high-level intent. They are about execution gaps where the system could still pass green while the trust-critical behavior is not actually proven:

- the veto can be enabled while `local_video_path` is not preserved;
- the Pod terminal gate can be mistaken for success through self-consistency mode;
- `SEVERITY_CAP` can still be hardened before real sensitivity assets exist;
- the objectivity grep gate is too blunt and may fight the implementation;
- the severity verdict cache key is underspecified for prompt/schema changes.

I would not start implementation until the first three are patched into the plan as hard gates.

## Findings

### HIGH-1: Veto ON can still pass through without a local video path

**Risk:** D-04 says Mode1/Mode3 scoring path always calls vision, but the current code only preserves `local_video_path` when `_gemini_enabled() or _gemini_vision_enabled()` is true. The new veto toggle proposed in 20-03 is separate. If existing Phase 17 vision toggles are OFF and only `GEMINI_VISION_VETO_ENABLED=1` is ON, `_apply_vision_veto` can receive `local_video_path=None` and return the v1 score unchanged.

**Evidence:**

- `20-03-PLAN.md:98` proposes `_gemini_vision_veto_enabled()` and returning when `local_video_path is None`.
- `backend/functions/pipeline/app.py:1833` currently uses `keep_local_video=_gemini_enabled() or _gemini_vision_enabled()`.
- `backend/functions/pipeline/app.py:2226` currently calls `_apply_vision_veto(result, local_video_path, angles)`.

**Why it matters:** This violates the phase's strongest invariant operationally. The math can be downward-only, but if the video path is missing the veto silently becomes a no-op.

**How I would fix it:**

- Add `_gemini_vision_veto_enabled()` before wiring the hook.
- Include it in the extraction retention gate:
  - `keep_local_video=_gemini_enabled() or _gemini_vision_enabled() or _gemini_vision_veto_enabled()`
- Add a pod-free test with existing vision toggles OFF and `GEMINI_VISION_VETO_ENABLED=1`, asserting adapter call receives `local_video_path`.
- Add an explicit audit status for missing video path. Do not rely on `visionVeto` absence alone.

Recommended audit shape:

```python
"visionVeto": {
    "status": "applied" | "not_applicable" | "disabled" | "skipped_error" | "missing_local_video",
    "severity": "minor" | "moderate" | "major" | None,
    "capApplied": int | None,
}
```

If keeping `visionVeto` only when applied is preferred for product UX, add a separate internal/eval field so the terminal gate can prove the veto actually ran.

### HIGH-2: Pod terminal gate can be misread as green when only self-consistency ran

**Risk:** 20-04 correctly says Pod eval is terminal and must not silently skip, but Task 1 asks `assert_baseline_v2.py` to pass self-consistency when the Pod baseline is absent. The command also appends `echo "exit=$?"`, which makes it easy for automation or a human skim to treat "self-consistency GREEN" as a phase gate pass.

**Evidence:**

- `20-04-PLAN.md:46` says 20-04 is a Pod-dependent terminal gate.
- `20-04-PLAN.md:53` says Pod down must block and silent skip is forbidden.
- `20-04-PLAN.md:94` says baseline absence runs self-consistency and "Pod sweep 대기".
- `20-04-PLAN.md:99` uses `python evals/phase20/assert_baseline_v2.py; echo "exit=$?"`.
- `20-04-PLAN.md:159` lists self-consistency GREEN under verification.

**Why it matters:** This phase exists to repair a trust-breaking false positive. A "green" artifact that has not run real RTMW + Gemini + sweep validation is worse than a red gate because it can unblock ship with the core claim unproven.

**How I would fix it:**

- Split the commands:
  - `assert_baseline_v2.py --self-check` may exit 0 without Pod baseline.
  - `assert_baseline_v2.py --phase-gate` must exit non-zero unless `eval20_serial_baseline.json` exists and all V-1/V-2/V-3/V-4/V-5 pass.
- Remove `; echo "exit=$?"` from verify commands.
- Add a required terminal evidence file, for example:
  - `backend/evals/phase20/baseline/eval20_serial_baseline.json`
  - `backend/evals/phase20/baseline/eval20_gate_report.json`
- Make `20-04-SUMMARY.md` illegal to create in "approved" form unless the phase-gate command passed.

Plan wording I would add:

> Pod-free self-check is not a phase gate and must not be recorded as approval. The default assert command fails closed when Pod baseline artifacts are missing.

### HIGH-3: `SEVERITY_CAP` still has a route to harden before real sensitivity assets exist

**Risk:** The plan says caps come from IPSF severity + sensitivity, not the 6 pairs. But the sensitivity set collection is deferred, and 20-04 Task 1 creates a TODO manifest. If implementation proceeds before real sensitivity videos exist, cap values may effectively be chosen from IPSF semantics plus the six known pairs. That is still a curve-fit path in practice.

**Evidence:**

- `20-CONTEXT.md:99` requires 미보유 + above-cutoff sensitivity as a generalization hard gate.
- `20-CONTEXT.md:108` says sensitivity asset collection is deferred.
- `20-04-PLAN.md:92` says `derive_caps.py` derives from IPSF severity + sensitivity.
- `20-04-PLAN.md:93` says `sensitivity.yaml` initially contains TODO markers and real video keys are filled after collection.
- `20-04-PLAN.md:122` says sweep output + sensitivity set are used to derive caps.

**Why it matters:** The 6-pair set is single-athlete and intentionally not a calibration set. If sensitivity is not real and populated, the "not curve-fit" invariant is mostly textual.

**How I would fix it:**

- `derive_caps.py` must fail closed if sensitivity entries are TODO, missing video keys, or below a minimum count.
- Require at least two distinct buckets before cap derivation:
  - false-positive/fault cases that must drop;
  - above-cutoff cases that must stay high.
- Ensure phase18 six pairs are not accepted as derive inputs. They should only be accepted by `assert_baseline_v2.py` as regression verification.
- Write the cap provenance into `vision_veto.py` as data, not just a comment:

```python
SEVERITY_CAP_PROVENANCE = {
    "source": "phase20_sensitivity",
    "sensitivity_manifest_sha256": "...",
    "phase18_pairs_used_for_derivation": False,
}
```

I would block any patch that fills `moderate` or `major` while `sensitivity_manifest_sha256` is absent or still contains TODO entries.

### MEDIUM-1: Objectivity grep gate is too blunt and can conflict with required implementation text

**Risk:** 20-02 requires grep zero for `"score"`/`"overall"`/`"rating"` in `gemini_vision_scorer.py`, but the same file must contain `_SCORE_PATTERN`, comments/docstrings about "no score", and possibly validation errors that mention forbidden fields. The grep can either fail on correct code or get weakened until it no longer guards the schema.

**Evidence:**

- `20-02-PLAN.md:100` requires `_SCORE_PATTERN`.
- `20-02-PLAN.md:110` requires grep zero for `"score"`/`"overall"`/`"rating"` schema keys.
- The existing spike includes `overall_qualitative` in schema at `backend/research/spikes/spike_vision_grounding_pair.py:217`, which should not be copied into the production veto schema if strict no-overall is desired.

**Why it matters:** Objectivity should be enforced structurally. Raw file grep is brittle and can create false confidence.

**How I would fix it:**

- Replace raw grep with schema introspection:
  - `build_schema()["properties"]` must not contain forbidden property names.
  - nested properties must not contain `score`, `overall`, `rating`, `점수`.
  - `VisionVerdict` dataclass fields must be exactly allowed names.
- Keep `_SCORE_PATTERN` allowed in implementation.
- Explicitly forbid copying `overall_qualitative` from the spike into production schema.

### MEDIUM-2: Severity verdict cache key is underspecified for prompt/schema changes

**Risk:** 20-02 suggests reusing a video hash + model + yaml_version cache pattern. That is enough for recognizer profile stability, but severity veto verdicts are sensitive to prompt wording, response schema, and `at_seconds` handling. A stale verdict could survive prompt/schema changes.

**Evidence:**

- `20-02-PLAN.md:101` proposes video-hash + model + yaml_version for severity verdict cache.
- `backend/shared/python/sunity_shared/analysis/technique_cache.py:172` documents recognizer cache key tuple `(video_hash, model_name, yaml_version)`.
- `20-02-PLAN.md:101` also says `at_seconds` is a worst-pose hint.

**Why it matters:** If the prompt is fixed after a bad severity classification, the cache can preserve the old result and make eval look deterministic while still wrong.

**How I would fix it:**

- Create a separate `VisionVetoCache`, or namespace the existing cache.
- Key by:
  - `video_hash`
  - `model_name`
  - `prompt_version`
  - `schema_version`
  - `at_seconds_bucket` or explicit `input_granularity`
- Add a test that changing `PROMPT_VERSION` invalidates the cache.

## Requested Focus Points

### 1. Downward-only invariant

The plan structurally chooses the right primitive: `apply_downward_cap(overall, severity)` via `min(overall, cap)` in 20-01 and `_apply_vision_veto` terminal cap in 20-03. That is the correct way to prevent vision from raising scores.

Residual risk is operational, not mathematical: if the veto is skipped because `local_video_path` is missing or the toggle is off, the output is not raised, but the false positive still survives. HIGH-1 is the practical hole I would close first.

### 2. Curve-fit prohibition

The documents repeatedly say "6 pairs are regression, not fit target", which is good. The weak point is that sensitivity collection is deferred while cap derivation is in-scope. Without a fail-closed sensitivity requirement, the cap table can still be chosen by looking at the six known outcomes.

I would make populated sensitivity assets a hard precondition for cap derivation.

### 3. Objectivity

The direction is good: Gemini emits fault/severity/geometric observations, not score. `VisionVerdict` has no score field, and `_SCORE_PATTERN` is required. The production schema should not inherit `overall_qualitative` from the spike if the no-overall rule is strict.

I would use schema/dataclass introspection tests instead of raw grep.

### 4. Pod sequencing and terminal gate

The intent is strong: `20-04` is marked Pod-dependent, serial-only, blocking, and silent-skip forbidden. The enforcement should be stronger. A default assert command should fail when Pod artifacts are absent; self-check should be opt-in and named as non-approval.

## Recommended Plan Patch Before Execute

1. Patch 20-03 to add `_gemini_vision_veto_enabled()` into `keep_local_video`.
2. Patch 20-03 audit contract to include explicit veto status, not just applied/absent.
3. Patch 20-04 so default `assert_baseline_v2.py` fails closed without Pod baseline; self-check becomes `--self-check`.
4. Patch 20-04 so `derive_caps.py` refuses to emit caps unless sensitivity assets are real, populated, and non-TODO.
5. Patch 20-02 objectivity tests to inspect schema/dataclass fields rather than raw file grep.
6. Patch 20-02 cache design to include prompt/schema versioning for severity verdicts.

## Verdict

**Not implementation-blocked by architecture, but plan should be tightened before execution.**

The high-level design is correct for a false-positive repair phase. The three HIGH findings are enough that I would not let the phase proceed on the current docs without amendments, because all three can produce a false green: veto not actually run, terminal gate not actually run, or cap values derived without real generalization evidence.
