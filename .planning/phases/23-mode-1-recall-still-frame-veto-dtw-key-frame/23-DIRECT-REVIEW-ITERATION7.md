# Phase 23 Direct Review - Iteration 7

Date: 2026-06-23
Reviewer: Codex direct review, no external skill/MCP
Scope: Seventh-pass review after D-15 non-zero assert/frozen manifest additions.

Reviewed artifacts:
- `23-CONTEXT.md`
- `23-01-PLAN.md`
- `23-02-PLAN.md`
- `23-03-PLAN.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- RunPod/pipeline requirements files relevant to the new eval/assert scripts

## Executive Summary

The Iteration 6 findings were mostly addressed:

- `SCORE-09` is now explicitly **not** absorbed by Phase 23-03.
- Phase 23-03 now owns only the Phase 20-04 still-frame **regression subset**.
- Kip-up was resolved to `moderate <=75`, consistent with the existing 20-04 evidence.
- `assert_stillframe_veto_gate.py` and a frozen manifest/lock are now planned.

The remaining issues are no longer about the high-level D-14 decision. They are about whether D-15 can actually work as a terminal gate on Pod:

1. The manifest lock workflow is not chronologically enforceable yet.
2. The assert script is planned to parse YAML, but PyYAML is not in the RunPod requirements and YAML is incorrectly described as stdlib.
3. The recall gate uses Korean display labels instead of canonical `FaultKey` values.
4. The non-zero gate script has no mandatory behavioral self-tests.

## Findings

### HIGH-1: The frozen manifest lock does not yet prove it was frozen before Pod measurement

**Risk**

The plan adds:

- `eval_stillframe_veto_manifest.yaml`
- `eval_stillframe_veto_manifest.lock.json`
- lock fields including manifest sha, git commit, dirty flag, created timestamp, row ids, expected-policy snapshot

That is the right direction, but the workflow is still ambiguous:

- Task 1 says the manifest and lock are created together.
- The lock rejects dirty worktree state, but creating a new manifest and lock necessarily makes the worktree dirty unless the manifest was already committed.
- Task 3 runs `git pull` and then executes the Pod eval, but it does not explicitly require the manifest lock to have been created and committed before the measurement run.
- The assert script verifies hash equality and dirty flag, but that only proves "the current manifest matches the lock." It does not prove the labels were locked before the result was known.

So a bad workflow can still happen:

```text
run Pod eval
see hard cases
edit manifest labels
generate lock
commit manifest + lock + result
assert passes
```

This is exactly the post-result relabel risk D-15 is trying to prevent.

**How I would fix it**

Make manifest freezing a separate pre-Pod step.

Add either a dedicated script:

```text
backend/research/spikes/freeze_stillframe_veto_manifest.py
```

or a subcommand:

```bash
python research/spikes/assert_stillframe_veto_gate.py freeze-manifest \
  --manifest research/spikes/eval_stillframe_veto_manifest.yaml \
  --created-at 2026-06-23T00:00:00Z
```

Required workflow:

1. Create `eval_stillframe_veto_manifest.yaml`.
2. Commit the manifest.
3. Run the freeze command from a clean worktree.
4. Commit `eval_stillframe_veto_manifest.lock.json`.
5. Pod pulls that commit.
6. Pod eval creates only the result JSON.
7. Assert script verifies `lock_git_commit` is an ancestor of current `HEAD` and that the lock was not dirty/dev-only.

Acceptance I would add:

- Freeze command refuses to run if manifest is uncommitted or worktree is dirty.
- Assert script fails if `lock_git_commit` is not an ancestor of current `HEAD`.
- Task 3 explicitly says the Pod run starts from a commit that already contains manifest + lock.
- Result JSON records `manifest_lock_git_commit`.

### HIGH-2: YAML parsing can fail on Pod because PyYAML is not in RunPod requirements

**Risk**

`23-03-PLAN.md` says the assert script uses `stdlib(json/yaml/hashlib/subprocess for git)`.

But `yaml` is not Python stdlib. In this repo:

- `backend/requirements-dev.txt` includes `pyyaml>=6`.
- `backend/functions/pipeline/requirements.txt` includes `pyyaml>=6.0,<7.0`.
- `backend/runpod_inference/setup.sh` installs only `backend/runpod_inference/requirements.txt`.
- `backend/runpod_inference/requirements.txt` does not currently include PyYAML.

Since Task 3 is Pod-terminal and calls the assert script before accepting the JSON, the gate can fail at import time even when the actual eval result is valid.

**How I would fix it**

Choose one:

1. Prefer stdlib-only:
   - Change the manifest from YAML to JSON:
     - `eval_stillframe_veto_manifest.json`
     - `eval_stillframe_veto_manifest.lock.json`
   - Use only `json`, `hashlib`, and `subprocess`.

2. Keep YAML:
   - Add `pyyaml>=6.0,<7.0` to `backend/runpod_inference/requirements.txt`.
   - Add that file to `23-03-PLAN.md` `files_modified`.
   - Make the assert script fail loud with a clear message if PyYAML is missing.

My preference is option 1 for this gate. The manifest is machine-owned and terminal-gate critical; avoiding a runtime dependency is simpler.

### MEDIUM-1: `expected_recall_set` should use canonical `FaultKey`, not Korean display labels

**Risk**

The manifest examples use:

```yaml
expected_recall_set: [왼팔, 오른팔, 고개·목]
```

But Phase 23-01 explicitly introduced canonical `FaultKey(part_scope, side, keypoint_set, fault_kind)` to avoid drift between strings such as:

- `왼팔`
- `left arm`
- `왼쪽 팔꿈치`
- ambiguous `팔`

If the eval gate compares Korean display labels, it can fail or pass for the wrong reason:

- a display-copy rename breaks the gate even though canonical detection is correct
- two labels map to one fault and inflate recall
- one canonical fault appears under a different localized phrase and is missed

**How I would fix it**

Change the manifest field:

```yaml
expected_recall_keys:
  - part_scope: upper_body
    side: left
    keypoint_set: arm
    fault_kind: pole_gap_or_bent
  - part_scope: upper_body
    side: right
    keypoint_set: arm
    fault_kind: pole_gap_or_bent
  - part_scope: upper_body
    side: unknown
    keypoint_set: head_neck
    fault_kind: extension_or_alignment
```

Keep display labels only as optional documentation:

```yaml
display_label_ko: "왼팔"
```

The assert script should compare against `supported_differences[].fault_key` or the serialized canonical key from `VisionFaultContext.to_trace_dict()`, not rendered Korean text.

### MEDIUM-2: The assert gate needs mandatory behavioral tests, not only AST/grep checks

**Risk**

Task 2 verification currently checks:

- AST parse
- presence of `sys.exit` or `raise SystemExit`
- grep for key terms
- "possibly" fake-result self-test

For a terminal gate, grep is too weak. A script can contain all the right words and still:

- trust precomputed booleans
- accept `"true"` as a string
- not detect missing rows
- ignore manifest hash mismatch
- misclassify kip-up `major <=50` as a pass despite the D-14 moderate policy

**How I would fix it**

Make self-tests required, either as pytest or as a built-in `--self-test`.

Minimum fixtures:

- valid minimal fixture exits 0
- manifest hash mismatch exits non-zero
- missing row exits non-zero
- extra unmanifested row exits non-zero
- string `"true"` where bool is required exits non-zero
- `resource_limited` on non-budget-stress row exits non-zero
- kip-up severity `major` with score 50 exits non-zero for severity misclassification
- kip-up severity `moderate` with score 80 exits non-zero for cap application failure
- EVAL18 pair with fault >= success increments regression count and exits non-zero

Add:

```text
backend/tests/test_assert_stillframe_veto_gate.py
```

and update Task 2 verify:

```bash
cd backend
python -m pytest tests/test_assert_stillframe_veto_gate.py -q
```

## Consolidated Recommendation

Before Phase 23-03 execution, I would make these plan edits:

1. Split manifest freeze from Pod measurement and require a committed pre-Pod lock.
2. Use JSON manifest or add PyYAML to RunPod requirements explicitly.
3. Change recall expectations from display labels to canonical `FaultKey` keys.
4. Make assertion script behavioral tests mandatory.

D-15 has the right intent. These changes make it operational instead of just descriptive.
