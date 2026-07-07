# Phase 22 — Direct Plan Review (Codex, no external reviewers)

**Date:** 2026-07-07  
**Scope:** `22-01-PLAN.md` through `22-10-PLAN.md`  
**Method:** direct read-through against `22-CONTEXT.md`, `22-RESEARCH.md`, `22-VALIDATION.md`, and the current pipeline/eval code. No external reviewer/CLI was invoked.

## Assumption

Per belle's clarification, I treat the existing plan-checker fixes as already applied:

- F1: deduction-engine contract substrate for `faults[]`
- F2: `svg_spec` label track + gate
- F3: EVAL18 path correction
- F4: `22-VALIDATION.md` authored
- F5: hollow verify strengthened where noted by the self-check

Dependency graph and FT-01..FT-06 coverage are unchanged and look structurally sound.

## Verdict

**BLOCK until the P0/P1 items below are patched.**

This is not a replan recommendation. The phase direction, wave order, and major artifacts are coherent. The remaining risk is mostly at execution boundaries: production Pod mutation, customer-video training ingress, fail-open gates, and validation commands that can let a bad model proceed.

## P0 — Must Fix Before Execution

### DR-01 · Shadow-derived customer video can bypass the anonymization/manifest gate

**Evidence**

- `22-03-PLAN.md` creates `vlm_shadow/{video_hash}` production verdict logs.
- `22-04-PLAN.md` Task 2 consumes `Firestore vlm_shadow` directly when assembling JSONL.
- `22-04-PLAN.md` filters `anonymized=true` for manifest rows in the Gemini teacher path, but the shadow path is described as a direct Firestore input, not as a manifest-joined media source.

**Impact**

If build_jsonl can recover or reference frames for an unregistered `video_hash`, production customer video can enter training without the D-12 anonymization gate. That breaks the phase's privacy contract at the exact point where the mistake becomes persistent model weight.

**What I would do**

- Make `build_jsonl.py` require every shadow-derived sample to join through `manifest.json` by `video_hash`.
- If no manifest row exists, or `anonymized != true`, allow **text-only verdict labels only** and emit no video/media reference.
- To use frames, require `anonymized=true` plus an anonymized S3 key registered in the manifest.
- Add a test: unregistered shadow `video_hash` produces `0` video-referencing samples.
- Add `_meta.shadow_unregistered_dropped` / `_meta.shadow_text_only_count` so the executor cannot hide the drop rate.

### DR-02 · Production serving Pod mutation is still too autonomous

**Evidence**

- `22-03-PLAN.md` is `autonomous: true`, but Task 3 SSHes into the current serving Pod, changes `start_server.sh`, enables `VLM_SHADOW_LOG=1`, restarts the server, and writes a VRAM artifact.
- `22-08-PLAN.md` is also `autonomous: true`, but Task 2 installs and boots vLLM on the serving Pod, changing GPU memory pressure in the live analysis path.

**Impact**

A mistaken executor can take down the live NLF/RTMW analysis service. The plan has good cohabitation criteria, but those criteria run after the risky mutation.

**What I would do**

- Reclassify `22-03` Task 3 and `22-08` Tasks 2/3 as blocking checkpoints, or split them into separate non-autonomous pod-operation plans.
- Prefer a clone/canary serving Pod first: same image, same volume/script shape, no live traffic.
- Only touch the production Pod after the clone shows: warmup OK, analysis smoke OK, Firestore write OK, `nvidia-smi` budget OK, rollback command documented.
- If using the current Pod is unavoidable, add a rollback block to the plan before the action: env revert, `start_server.sh` revert path, restart command, health check, and Lambda URL/env sync check.

### DR-03 · SFT assert gate can fail and still pass the automated verify

**Evidence**

- `22-07-PLAN.md` Task 3 verify ends with `python3 backend/evals/phase22/assert_gates.py; test $? -le 1`.
- The same task is the gate before serving/swap work.

**Impact**

Exit code `1` means FAIL by the phase's own gate semantics. Accepting `<= 1` lets a failed SFT model move forward as if the automated step passed.

**What I would do**

- Split gate modes:
  - Local unit mode: tests can assert `SKIPPED != FAIL` when no Pod artifact exists.
  - Post-Pod gate mode: require `assert_gates.py` exit `0`.
- Change the execution verify after Pod artifacts exist to `python3 backend/evals/phase22/assert_gates.py --require-pass`.
- Make Wave 5 entry require either `PASS` or explicit belle decision to hold/scope down. No implicit proceed on FAIL.

## P1 — High Risk / Fix Before Full Run

### DR-04 · Train/val split has two owners

**Evidence**

- `22-04-PLAN.md` creates `train.jsonl` and `val.jsonl` with a `video_hash`-level split.
- `22-07-PLAN.md` runs SFT with `--dataset train.jsonl --split_dataset_ratio 0.02`, which re-splits the training file and ignores the explicit val file.

**Impact**

The video-level leakage guarantee in 22-04 can be voided by a later random split. It also makes the authored `val.jsonl` effectively dead.

**What I would do**

- Pick one owner. I would let `build_jsonl.py` own the video-hash split and make SFT consume the explicit validation file.
- If ms-swift's current flag set cannot accept an explicit validation file, then do not emit a separate `val.jsonl`; instead make the separate held-out/eval gate the validation owner and document that SFT's internal split is not a leakage guarantee.
- In either case, remove the current double-split wording.

### DR-05 · Gemini teacher distillation is batch-costing while still autonomous

**Evidence**

- `22-04-PLAN.md` is `autonomous: true`.
- Task 1/3 run `gemini-3.1-pro-preview` plus judge calls over the manifest.
- 22-06 and 22-07 correctly gate RunPod costs, but 22-04 does not gate API spend the same way.

**Impact**

This can burn quota/credits and stall the phase without an explicit spend checkpoint. The plan already knows about prior Gemini credit depletion.

**What I would do**

- Add a blocking cost checkpoint before full distillation.
- The checkpoint should present: manifest target count, estimated teacher calls, estimated judge calls, current quota/credit probe, max rows for the first run, and abort threshold.
- Run a first batch of 10 rows, inspect filter stats and file residue, then approve the full batch.

### DR-06 · Manifest balance gate can still fail open

**Evidence**

- `22-02-PLAN.md` says the balance gate is activated by `_meta.collection_complete=true`.
- The same plan says the executor sets that flag after collection.

**Impact**

If the flag is false or omitted, an incomplete/empty seed can pass local tests and later feed JSONL/SFT. This is especially risky because motion balance is one of the core phase invariants.

**What I would do**

- At the `22-04 build_jsonl.py` entry point, assert `_meta.collection_complete is true` unless an explicit `--partial` flag is passed.
- Do not allow `--partial` runs to upload `training/phase22/jsonl/` as the canonical training set.
- Add a test where `_meta.collection_complete=false` fails JSONL build, not just manifest consistency.

### DR-07 · Some regression verifies still do not run what they claim

**Evidence**

- `22-03-PLAN.md` Task 2 uses `pytest backend/tests -q -x --co -q | tail -1`; `--co` is collect-only.
- Several cloud-effecting checks still rely on static greps or existence checks instead of a real outcome, for example File API deletion grep and S3 prefix listing in `22-04`.

**Impact**

The summary can claim "baseline FAILED diff IDENTICAL" or "JSONL uploaded" without actually proving it.

**What I would do**

- Replace collect-only regression checks with an actual full-suite command plus a recorded baseline diff.
- For Gemini File API cleanup, unit-test delete-in-finally with a fake client.
- For S3 JSONL, explicitly check for `train.jsonl` and `val.jsonl` object keys, not just a prefix listing.

## P2 — Medium / Tighten While Editing

- `22-01` acceptance requires `_meta.source_doc_count >= 30`, but the verify command only prints it. Assert the threshold in the command or move it to a manual-only row with an explicit fallback.
- `22-10` says "env 1개" as a rollback principle, but the implementation uses three role-specific env vars. I think the role-specific vars are the right design; adjust the wording to "one env per role."
- YouTube/public-video legal status is deferred to launch/legal review. That is acceptable for pilot research, but do not let LICENSE-AUDIT imply it is release-clean unless counsel signs it.

## Confirmed Sound

- The F1/F2 corrections materially improve the plan: the own-model output now has a scoring substrate and `svg_spec` is no longer an unchecked decorative field.
- The wave dependency chain is coherent and acyclic.
- FT-01..FT-06 all have a delivering plan, not only a tag.
- Training Pod rental and SFT spend are correctly checkpointed in 22-06/22-07.
- The eval lineage from Phase 24 (`EVAL_OUT_DIR` outside repo, SERIAL, artifact-gated checks, no human score labels) is the right pattern to reuse.

## Minimal Patch Set I Would Apply

1. Patch `22-04` first: manifest-join shadow samples, add distillation cost checkpoint, and fix train/val ownership.
2. Patch `22-03`/`22-08`: make production Pod mutations non-autonomous and add canary/rollback steps.
3. Patch `22-07`: require strict `assert_gates` pass after Pod artifacts exist.
4. Patch `22-02`: make collection completeness fail closed at JSONL build time.
5. Sweep verify commands for collect-only/static/existence checks and replace them with outcome assertions.

After those, I would execute Phase 22 without changing the overall plan shape.
