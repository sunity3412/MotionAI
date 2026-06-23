# Phase 23 Direct Review - Iteration 8

Date: 2026-06-23
Reviewer: Codex direct review, no external skill/MCP
Scope: Eighth-pass review after D-16 terminal gate operationalization.

Reviewed artifacts:
- `23-CONTEXT.md`
- `23-03-PLAN.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- RunPod/pipeline dependency files relevant to the eval gate

## Executive Summary

D-16 fixes the largest Iteration 7 issues:

- Manifest is now JSON, not YAML.
- PyYAML is no longer required for the Pod-terminal assert path.
- Freeze is split into a pre-Pod script.
- Recall expectations now use canonical `FaultKey`.
- Assert behavior tests are mandatory.

The remaining risks are narrower but still important for the terminal gate:

1. `lock_git_commit` being an ancestor of current `HEAD` does not prove the result was produced after the lock.
2. The manifest row set contract conflicts with multi-arm results (`production_still`, `direct_adapter_still`, `whole_video_baseline`).
3. EVAL18 regression-pair computation needs explicit pair mapping in the manifest.
4. Coverage thresholds and gate grouping are referenced but not frozen as manifest policy.

## Findings

### HIGH-1: Lock ancestry must be checked against the result run commit, not only current `HEAD`

**Risk**

D-16 now requires:

- pre-Pod freeze script
- `lock_git_commit`
- assert verifies `lock_git_commit` is an ancestor of current `HEAD`
- result JSON records `manifest_lock_git_commit`

That is better than D-15, but it still proves only:

```text
the lock is an ancestor of the repository state at assert time
```

It does not prove:

```text
the Pod measurement was executed after that lock existed
```

A bad sequence is still possible:

```text
run eval on Pod before freeze
see results
freeze manifest/lock
edit or regenerate result JSON to include manifest_lock_git_commit
assert sees lock ancestor of current HEAD and passes
```

This is not about malicious actors only. In a manual Pod workflow, it is easy to accidentally run the sweep, then realize the lock is missing, create it, and continue.

**How I would fix it**

Make the eval harness itself enforce and record the lock state at run start.

`eval_stillframe_veto.py` should refuse to run unless:

- `eval_stillframe_veto_manifest.lock.json` exists
- current manifest sha equals lock `manifest_sha256`
- `lock_git_commit` is an ancestor of the current run `HEAD`
- worktree is clean except for the intended output path, or output path is absent

The result JSON should include:

```json
{
  "run_git_commit": "<git rev-parse HEAD at eval start>",
  "worktree_dirty_at_run": false,
  "manifest_lock_git_commit": "<lock.lock_git_commit>",
  "manifest_sha256": "<lock.manifest_sha256>",
  "eval_command": "...",
  "result_generated_at": "..."
}
```

Then the assert script should check:

- `lock_git_commit` is an ancestor of `result.run_git_commit`, not just current `HEAD`.
- `result.run_git_commit` is an ancestor of current `HEAD`.
- `result.worktree_dirty_at_run` is false.
- `result.manifest_lock_git_commit == lock.lock_git_commit`.
- `result.manifest_sha256 == lock.manifest_sha256`.

This does not make a manually edited JSON impossible, but it makes the intended workflow mechanically auditable and catches the common accidental post-result freeze path.

### HIGH-2: Manifest row identity is underspecified for multi-arm results

**Risk**

The plan requires:

```text
result row set == manifest row set
```

But the eval measures multiple arms:

- `production_still`
- `direct_adapter_still`
- `whole_video_baseline`

If the result JSON has one row per `(case, arm)`, then result rows will exceed manifest rows and the assert script will fail valid results as "extra rows."

If the result JSON has only one row per manifest case and hides arms inside nested fields, then the current row-set language is too vague: the assert could validate only the production row and silently miss whole-video baseline or direct-adapter cache isolation failures.

This matters because Phase 23-03 depends on cross-arm claims:

- production still-frame recall beats same-model whole-video baseline
- whole-video baseline cache key differs from production still cache key
- direct adapter does not prewarm production gate runs
- cold/warm determinism is separated by arm

**How I would fix it**

Choose one result shape and lock it.

Preferred shape:

```json
{
  "cases": [
    {
      "row_id": "eval18-kip-up-fault",
      "arms": {
        "production_still": {...},
        "whole_video_baseline": {...},
        "direct_adapter_still": {...}
      }
    }
  ]
}
```

Manifest:

```json
{
  "rows": [
    {
      "row_id": "eval18-kip-up-fault",
      "required_arms": ["production_still", "whole_video_baseline"],
      "optional_arms": ["direct_adapter_still"]
    }
  ]
}
```

Assert rules:

- Manifest `row_id` set equals result `cases[].row_id` set.
- For each case, all `required_arms` are present exactly once.
- No unknown arm appears.
- Production specificity/recall gates read only `arms.production_still`.
- Whole-video baseline recall comparison reads `arms.whole_video_baseline`.
- Cache isolation compares keys across arms inside the same case.

This avoids both false failures and silent baseline omissions.

### MEDIUM-1: EVAL18 regression pairs need explicit manifest pair mapping

**Risk**

The plan requires:

```text
eval18_discrimination_regression_count = 0
```

for the four pairs:

- power-spin
- peter-pan
- elbow-twist-sister
- pdshape

But the current manifest schema lists row-level fields and does not explicitly include pair linkage, such as:

- `regression_pair_id`
- `pair_role: fault | success`
- `success_row_id`
- `fault_row_id`

Without pair mapping, the assert script has to infer from `row_id` naming or motion ids. That reintroduces hardcoded known-answer logic into the gate and makes row renames dangerous.

**How I would fix it**

Add pair policy to the manifest.

Option A, row-local:

```json
{
  "row_id": "eval18-power-spin-fault",
  "regression_pair_id": "eval18-power-spin",
  "pair_role": "fault"
}
```

```json
{
  "row_id": "eval18-power-spin-success",
  "regression_pair_id": "eval18-power-spin",
  "pair_role": "success"
}
```

Option B, top-level:

```json
{
  "regression_pairs": [
    {
      "pair_id": "eval18-power-spin",
      "fault_row_id": "eval18-power-spin-fault",
      "success_row_id": "eval18-power-spin-success",
      "min_margin": 1
    }
  ]
}
```

The lock should snapshot this pair policy, and the assert script should compute margins only from this manifest mapping.

### MEDIUM-2: Coverage thresholds and gate grouping should be locked as manifest policy

**Risk**

`23-03-PLAN.md` says:

```text
clean_evaluable_count >= COVERAGE_MIN
```

and references "manifest-defined COVERAGE_MIN", but the manifest schema currently lists only row fields.

If `COVERAGE_MIN` is implemented as a script constant, future changes can alter terminal-gate strictness without changing the frozen manifest. If it is inferred from row counts, it may be unclear whether occluded/spinning/tempo-shifted rows are in the same denominator or different gate groups.

**How I would fix it**

Add top-level locked gate policy:

```json
{
  "gate_policy": {
    "clean_coverage_min": 4,
    "clean_gate_case_classes": [
      "elite_clean",
      "imperfect_clean",
      "occluded",
      "spinning"
    ],
    "alignment_abstention_case_classes": ["tempo_shifted"],
    "known_fault_case_classes": ["known_fault"],
    "required_arms": ["production_still", "whole_video_baseline"]
  }
}
```

The lock should include `gate_policy`, and the assert script should recompute coverage from the locked policy rather than from hardcoded constants.

### MEDIUM-3: Canonical `FaultKey` needs a single serialized schema owner

**Risk**

D-16 correctly changes recall from Korean display labels to canonical `FaultKey`. But the manifest example introduces values such as:

- `pole_gap_or_bent`
- `extension_or_alignment`
- `head_neck`

If these strings are not the same enum vocabulary emitted by `VisionFaultContext.to_trace_dict()`, the gate can fail even when the system found the intended fault.

**How I would fix it**

Define one serializer/validator:

```python
FaultKey.to_dict()
FaultKey.from_dict()
```

with locked enum values for:

- `part_scope`
- `side`
- `keypoint_set`
- `fault_kind`

Then require:

- manifest `expected_recall_keys` validates through `FaultKey.from_dict`
- result `recall_set` is produced by `FaultKey.to_dict`
- assert compares normalized `FaultKey` tuples, not free-form dicts

Add one test where an unknown `fault_kind` in the manifest fails before any Pod result is accepted.

## Consolidated Recommendation

Before execution, I would update 23-03 with:

1. `run_git_commit` and `worktree_dirty_at_run` in result JSON, and assert lock ancestry against `run_git_commit`.
2. A locked result shape for multi-arm data, preferably `cases[].arms.{production_still, whole_video_baseline, direct_adapter_still}`.
3. Manifest-owned EVAL18 pair mapping.
4. Manifest-owned `gate_policy` for coverage and arm requirements.
5. A shared `FaultKey` JSON schema/validator.

D-16 made the terminal gate much more real. These remaining changes close the places where the assert script could still be forced to infer structure or trust the wrong timestamp.
