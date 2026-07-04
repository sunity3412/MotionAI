# Phase 15 Direct Plan Review — Iteration 5

**Reviewed:** 2026-06-17  
**Reviewer:** Codex direct review, no external GSD/agent review used  
**Scope:** `15-01-PLAN.md` .. `15-05-PLAN.md` after iteration-4 remediation patches, plus local S3/Lambda/RunPod contracts.

## Verdict

**Close, but one trigger-contract blocker remains.** The iteration-4 issues were mostly addressed: `15-02` is now self-contained instead of depending on Plan 01 fixtures, generated `analysisId` values are explicitly alphanumeric, SC4 13/13 aggregation moved to `15-05`, SSM-vs-Lambda equality was restored, Mode 1 false-positive scoring became observational, and `phase15_keys.json` is now listed.

The remaining blocker is that the new `direct-process` path still copies the fixture into `uploads/{uid}/{analysisId}.mp4` before directly calling `_process`. In this production bucket, any `uploads/` object creation triggers S3 -> SQS -> Lambda. That means `direct-process` is not actually direct-only: it can also enqueue the production path and double-run the same analysis.

## Findings

### HIGH 1. `direct-process` still copies into `uploads/`, so S3 notification can double-trigger the run

**Evidence**
- `backend/README.md` configures S3 notification for `s3:ObjectCreated:*` with prefix `uploads/`.
- `15-01-PLAN.md` defines `direct-process(default)` as: create analysis doc, copy fixture to `uploads/{uid}/{analysisId}.mp4`, then call `pipeline._process(bucket, copied-uploads-key, uid, analysisId)` directly.
- `15-01-PLAN.md` also says this avoids async S3/SQS timing and that only one trigger is invoked.

**Risk**

The copy itself is an S3 `ObjectCreated` event under `uploads/`. Even if the script only calls `_process` once, the bucket can still enqueue Lambda for the same object. With RunPod delegation enabled, Lambda may set the same doc to queued and POST to the Pod while the direct `_process` path is already running. That reintroduces the double-analysis race the plan is trying to eliminate.

This affects `15-03` and `15-04` because both use `sweep_phase15.py --trigger direct-process default`.

**How I would fix it**
- Make `direct-process` truly direct:
  - create the Firestore doc,
  - call `_process(bucket, sourceS3Key, uid, analysisId)` using the `fixtures/phase15/...` key directly,
  - do not copy anything into `uploads/`.
- Only `notification` and `analyze` modes should create `uploads/{uid}/{analysisId}.mp4` keys.
- In the script, enforce the invariant:
  - `direct-process` => no `copy_object` to `uploads/`.
  - `notification` => copy to `uploads/`, do not call `_process` or `/analyze`.
  - `analyze` => see HIGH 2 before allowing it on the live bucket.

### HIGH 2. Plan 02's direct `/analyze` smoke has the same `uploads/` notification collision

**Evidence**
- `15-02-PLAN.md` now makes the smoke self-contained: create a temporary Firestore doc, copy an existing S3 object to `uploads/{uid}/{analysisId}.mp4`, then choose either direct `/analyze` POST or S3 notification.
- The live bucket notification watches all `uploads/` object creation.
- `backend/runpod_inference/server.py::analyze` requires an `uploads/{uid}/{analysisId}` key, so direct `/analyze` currently still needs the object to exist under `uploads/`.

**Risk**

If the executor chooses direct `/analyze` after copying to `uploads/`, the copy can also trigger Lambda notification. The same smoke doc can be processed once by direct Pod `/analyze` and once by the production Lambda delegate path.

**How I would fix it**
- For the live production bucket, make Plan 02 use notification-only smoke:
  - create the doc,
  - copy to `uploads/{uid}/{analysisId}.mp4`,
  - let S3 -> Lambda -> RunPod `/analyze` be the only trigger,
  - verify CloudWatch/Pod logs show the delegate path.
- If direct `/analyze` must be tested separately, run it against an isolated bucket/prefix without bucket notification, or temporarily disable notification only with explicit approval. I would not do that for this phase.
- Update Plan 02 wording to remove the "direct `/analyze` or notification" choice on the live bucket.

### MEDIUM 3. Plan 02 automated verify depends on undefined `$PIPELINE_FN`

**Evidence**
- `15-02-PLAN.md` automated verify calls `aws lambda get-function-configuration --function-name "$PIPELINE_FN"`.
- The plan does not define `PIPELINE_FN`.
- Local infrastructure files show the pilot pipeline function name is `sunity-motion-pilot-pipeline` (`backend/template.yaml`, `.claude/scripts/setup_pod_full.sh`).

**Risk**

The SSM/Lambda equality and env-preservation verify can fail because the shell variable is empty, not because the Lambda config is wrong. That creates a false blocker during Pod bring-up.

**How I would fix it**
- Make the verify command self-contained:
  - `PIPELINE_FN="${PIPELINE_FN:-sunity-motion-pilot-pipeline}"`, or
  - hardcode `sunity-motion-pilot-pipeline` for this pilot phase, matching existing scripts.
- Record the resolved function name in `15-POD-BRINGUP-EVIDENCE.md`.

### MEDIUM 4. SC4 aggregate verify in `15-05` only checks summary files exist

**Evidence**
- `15-05-PLAN.md` Task 1 owns the 13-video SC4 aggregate.
- Its automated verify only checks that `15-03-SUMMARY.md` and `15-04-SUMMARY.md` exist.
- Acceptance requires total 13, status counts, and `unexpected pipeline 실패 == 0`.

**Risk**

Both summary files can exist while missing status counts, containing partial runs, or recording `server_error > 0`. The automated gate would still pass the precondition and rely entirely on manual table filling.

**How I would fix it**
- Add a small verifier for the aggregate evidence:
  - parse `15-03` Mode 1 count and `15-04` Mode 3 count,
  - require `mode1_total == 7`,
  - require `mode3_total == 6`,
  - require combined `total == 13`,
  - require combined `server_error == 0`,
  - fail if any count is missing.
- At minimum, add grep/assert checks for the exact count rows in the two summaries before creating `15-SC4-AGGREGATE-EVIDENCE.md`.

### LOW 5. `15-04` still contains stale SC4 ownership wording

**Evidence**
- `15-03-PLAN.md` now says 13-video SC4 aggregation is owned by `15-05`.
- `15-05-PLAN.md` now owns `15-SC4-AGGREGATE-EVIDENCE.md`.
- `15-04-PLAN.md` still says `15-03`'s 13/13 integrated row is filled after `15-04` completes.

**Risk**

The graph is now mostly correct, but stale prose in `15-04` can lead an executor to put SC4 aggregate evidence back into `15-03` or to write inconsistent summaries.

**How I would fix it**
- Update the stale `15-04` objective text to say:
  - `15-05` owns the 13/13 SC4 aggregate after both `15-03` and `15-04` complete.
  - `15-04` only provides Mode 3 6-video status counts for that later aggregate.

## Iteration-4 Closure Status

| Iteration-4 issue | Iteration-5 status |
|---|---|
| `15-02` relies on Plan 01 artifacts without dependency | Resolved by self-contained smoke, but direct `/analyze` option still collides with notification; see HIGH 2 |
| Mode 1 `analysisId` can include hyphens | Resolved in `15-01`: alphanumeric-only IDs plus every-key parse assertion |
| `15-03` SC4 aggregate depends on `15-04` without graph edge | Resolved by moving aggregate to `15-05`; stale `15-04` prose remains |
| Trigger contract mixed `_process`, notification, `/analyze` | Improved with `--trigger`, but `direct-process` still writes to `uploads/`; see HIGH 1 |
| SSM-vs-Lambda equality missing from verify | Resolved in logic, but verify command needs a defined pipeline function name |
| Mode 1 false-positive gate subjective | Resolved by making Mode 1 score observational only |
| `phase15_keys.json` missing from artifacts | Resolved |

## Recommended Patch Order

1. Change `direct-process` to call `_process` on `sourceS3Key` directly and never write to `uploads/`.
2. Restrict Plan 02 live-bucket smoke to notification-only, or move direct `/analyze` smoke to an isolated non-notified environment.
3. Define `PIPELINE_FN` explicitly in Plan 02 verify.
4. Add a real SC4 aggregate count verifier in Plan 05.
5. Remove stale SC4 ownership prose from Plan 04.

