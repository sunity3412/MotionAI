# Phase 22 Direct Review Iteration 2

Date: 2026-07-07
Reviewer: Codex direct review, no external reviewer
Baseline: `main@a94014c`

## Scope

Reviewed the Phase 22 plan after the DR-01 through DR-07 fix pass committed in
`a94014c`. This pass used the committed plan files and
`22-DIRECT-REVIEW.md` as inputs. The uncommitted `22-PLAN-REVIEW.md` was treated
as historical reviewer context only and was not modified.

## Verdict

Pass with fixups.

The original direct-review high-risk set is materially covered:

- DR-01: shadow dataset wiring is now fail-closed on manifest registration and anonymization.
- DR-02: production Pod mutations are no longer autonomous and now require canary/rollback checkpoints.
- DR-03: fail-open gate semantics were removed in favor of `--require-pass`.
- DR-04: split ownership is centralized in `build_jsonl.py`.
- DR-05: Gemini distillation has an explicit cost checkpoint.
- DR-06: `collection_complete` is now asserted before JSONL build.
- DR-07: teacher test and S3 `head-object` checks were added.

I do not see a new P0 architecture blocker. I would not send Phase 22 back for a
large replan. I would, however, fix the items below before execution or another
external review pass, because they can cause a plan executor to verify the wrong
thing or silently miss a regression.

## Findings

### P1: `22-VALIDATION.md` is now stale relative to the revised plan

Evidence:

- `22-VALIDATION.md` still maps `22-03-3` to Pod smoke / peak VRAM, but the
  current `22-03-PLAN.md` makes `22-03-3` a production-Pod approval checkpoint
  and moves Pod deploy/smoke to `22-03-4`.
- `22-VALIDATION.md` still maps `22-04-3` to distill JSONL generation, but the
  current `22-04-PLAN.md` makes `22-04-3` the Gemini cost checkpoint and moves
  distill/full JSONL generation to `22-04-4`.
- `22-VALIDATION.md` still uses the old `22-08-2` and `22-08-3` task meanings,
  while the current `22-08-PLAN.md` inserts a canary/rollback checkpoint before
  the production vLLM mutation.
- The validation contract does not yet include the newly important checks:
  `test_gemini_teacher.py`, `--require-pass`, `s3api head-object`,
  `collection_complete`, or the new production checkpoint artifacts.

Impact:

The plan files have been fixed, but the canonical validation map can still drive
reviewers or executors toward the pre-DR task IDs and weaker checks. That creates
false confidence: Phase 22 could look validated while DR-02, DR-05, DR-06, or
DR-07 are not actually exercised through the validation document.

Recommended fix:

Update `22-VALIDATION.md` in the same pass as the plan fixes:

- Renumber the affected `22-03`, `22-04`, and `22-08` rows.
- Add explicit manual rows for the production approval/cost checkpoints.
- Add automated rows for `test_gemini_teacher.py`, `collection_complete`,
  `s3api head-object`, and `assert_gates.py --require-pass`.
- Make the validation matrix point at the current task IDs, not the pre-DR
  numbering.

If I were handling this, I would treat this as the only must-fix before execution
handoff. It is documentation-only, but it is the document most likely to be used
as the execution gate.

### P1: `22-03` full-suite baseline check can still hide failures

Evidence:

`22-03-PLAN.md` asks for:

```bash
python3 -m pytest backend/tests/phase22/test_shadow_wiring.py -x -q &&
python3 -m pytest backend/tests -q 2>&1 | tail -3
```

The second command is a pipeline. Without `pipefail`, the pipeline exit status is
the status of `tail`, not `pytest`. That means a full-suite failure can be
displayed in the last three lines while the command still exits successfully.

Impact:

This weakens the baseline-regression guard. Since the plan intentionally allows
known existing failures, the check cannot simply require full-suite PASS, but it
does need to assert that the failure set did not grow.

Recommended fix:

Replace the pipeline with a small compare step:

- Capture full pytest output to a temporary artifact.
- Parse the FAILED/ERROR test node IDs.
- Compare them against the recorded baseline failure set.
- Fail if any new Phase 22-related failure appears or if the failure count grows
  unexpectedly.

If no baseline artifact is intended, make this an explicit manual validation item
instead of presenting it as an automated verifier.

### P2: Optional `val.jsonl` ownership is improved but still inconsistent

Evidence:

- `22-04-PLAN.md` Task 2 allows the no-`val.jsonl` branch when ms-swift does not
  support explicit validation files, with validation ownership falling to the
  Phase 22 eval gate.
- `22-04-PLAN.md` Task 4 still says the build generates
  `train.jsonl`/`val.jsonl` and uploads them.
- The Task 4 automated verifier checks only `train.jsonl` via S3 `head-object`.
- The success criteria still describe `train/val JSONL` as the direct input to
  `22-07`.
- `22-07-PLAN.md` correctly says explicit val is used only if supported, but
  still refers to train/val loss artifacts in one place.

Impact:

The plan now contains the right idea, but the acceptance surface is split between
two possible contracts. An executor could skip `val.jsonl` without proving that
validation ownership moved to the eval gate, or a reviewer could incorrectly
fail a valid no-val branch.

Recommended fix:

Define one explicit contract field, for example:

```text
validation_owner = explicit_val_jsonl | phase22_eval_gate
```

Then make Task 4 verification assert exactly one of:

- `train.jsonl` and `val.jsonl` both exist in S3, or
- `train.jsonl` exists and `_meta.validation_owner=phase22_eval_gate` is present.

Mirror the same wording in `22-04` success criteria and the `22-07` SFT loss
artifact description.

### P2: Pod VRAM artifact check is still text-presence oriented

Evidence:

`22-03-PLAN.md` now requires a peak VRAM artifact, but the automated verifier is
still effectively a text presence check:

```bash
test -f .planning/phases/22-custom-vlm-finetune/22-POD-VRAM.md &&
grep -cE "peak|피크" .planning/phases/22-custom-vlm-finetune/22-POD-VRAM.md
```

Impact:

This confirms that an artifact mentions peak VRAM, but not that it contains a
numeric value usable for scope-down decisions. This is lower risk than the
production mutation blocker, but it leaves the canary decision less auditable.

Recommended fix:

Require a parseable field such as:

```yaml
peak_vram_gb: 39.8
model_variant: Qwen2.5-VL-7B
pod_type: RunPod RTX A6000
```

Then verify it with a parser or at least a regex that extracts a numeric GB
value and fails if missing.

## Product Decisions Still Open

The prior product decisions D1 through D3 remain product-scope decisions rather
than implementation blockers. I would keep them open unless execution requires a
specific answer:

- D1: exact license posture and release/distribution boundary.
- D2: acceptable quality/cost tradeoff for Gemini distillation volume.
- D3: production rollout threshold for the vLLM path versus keeping it pilot-only.

## Suggested Next Action

Make one narrow follow-up patch:

1. Sync `22-VALIDATION.md` to the DR-adjusted task graph.
2. Replace the `22-03` full-suite `tail -3` verifier with an asserted baseline
   comparison or mark it manual.
3. Normalize the `val.jsonl` contract through a single `validation_owner` field.
4. Tighten the Pod VRAM artifact check to require a numeric `peak_vram_gb`.

After that, I would consider the Phase 22 plan ready for execution gating. No
second large replan is warranted from this review.
