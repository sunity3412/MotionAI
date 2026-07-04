# Phase 15 Direct Plan Review — Iteration 4

**Reviewed:** 2026-06-17  
**Reviewer:** Codex direct review, no external GSD/agent review used  
**Scope:** `15-01-PLAN.md` .. `15-05-PLAN.md` after iteration-3 remediation patches, plus local backend contracts.

## Verdict

**Much closer, but still not execution-ready.** The iteration-3 blockers were mostly addressed in the right direction: reusable videos moved to `fixtures/phase15`, source fixture keys are separated from analysis identity, Mode 3 evidence moved to `15-04` as single owner, and Lambda env preservation is now explicitly asserted.

The remaining risks are narrower but still capable of breaking execution. The biggest issue is dependency graph drift: `15-02` now uses Plan 01 fixture/sweep machinery while still declaring no dependency on `15-01`; `15-03` still wants a 13-video aggregate that depends on `15-04` while both plans remain same-wave siblings. There is also one concrete parser-contract bug: Mode 1 `analysisId` examples can include hyphenated motion slugs, but `parse_upload_key` only accepts alphanumeric analysis ids.

## Findings

### HIGH 1. `15-02` now relies on Plan 01 artifacts but does not depend on `15-01`

**Evidence**
- `15-02-PLAN.md` has `depends_on: []`.
- `15-02-PLAN.md` Task 2 says the live LLM smoke uses `Plan 01 fixtures/phase15/climb/correct` through the sweep controlled trigger.
- `15-01-PLAN.md` is the plan that creates `upload_phase15_dataset.py`, `sweep_phase15.py`, and `phase15_keys.json`, and uploads `fixtures/phase15/...`.

**Risk**

The scheduler can run `15-01` and `15-02` in parallel because both are wave 1 with no dependencies. Under that graph, Plan 02 can reach its liveness E2E before the fixture source keys, sweep script, or keys JSON exist. The bring-up could fail for a planning-order reason rather than a Pod/LLM reason, producing noisy escalation.

**How I would fix it**
- If Plan 02's smoke should use `sweep_phase15.py` and `fixtures/phase15`, set `15-02` to `depends_on: ["15-01"]`.
- If Pod bring-up must remain independent, make Plan 02 self-contained:
  - create one temporary Firestore doc in Plan 02,
  - copy an already-known existing S3 object to `uploads/{uid}/{analysisId}.mp4`,
  - call `/analyze` or let notification run,
  - do not mention Plan 01 fixtures/sweep in Plan 02.

### HIGH 2. Mode 1 `analysisId={motion}success` can violate the S3 upload parser

**Evidence**
- `backend/shared/python/sunity_shared/s3keys.py` accepts `uploads/{uid}/{analysis_id}.{ext}`, where `analysis_id` must match `[A-Za-z0-9]+`.
- `15-01-PLAN.md` says Mode 1 can use `analysisId=영숫자 unique(예: {motion}success)`.
- Several Phase 15 motion slugs include hyphens: `elbow-twist-sister`, `kip-up`, `power-spin`, `peter-pan`.

**Risk**

If the executor follows the example literally, it can generate keys like `uploads/phase15_mode1_<runId>/elbow-twist-sistersuccess.mp4`. That key does not parse, so Lambda skips it or Pod `/analyze` rejects it before inference. This reintroduces the exact class of key-format failure that iteration 2 was meant to close, but only for hyphenated motions.

**How I would fix it**
- For every generated `analysisId`, derive an alphanumeric id from a sanitized slug or hash:
  - `elbowtwistsisterSuccess<runId>`
  - or `m<shortHash>Success<runId>`
- Add a dry-run assertion that builds every planned `uploads/{uid}/{analysisId}.mp4` key and passes it through `parse_upload_key`.
- Reject any `analysisId` containing characters outside `[A-Za-z0-9]`; do not rely on prose saying "영숫자" while the example is unsafe.

### HIGH 3. `15-03` still depends on `15-04` evidence for SC4 while the graph allows parallel execution

**Evidence**
- `15-03-PLAN.md` and `15-04-PLAN.md` both declare `depends_on: ["15-01", "15-02"]`.
- `15-03-PLAN.md` Task 3 says the 13/13 SC4 integrated row is filled after `15-04` produces MODE_SELF status counts.
- `15-03-PLAN.md` still lists the SC4 aggregate in its acceptance and done conditions.

**Risk**

The ownership race for MODE_SELF docs is improved, but the evidence dependency remains. `15-03` cannot complete its stated SC4 aggregate until `15-04` completes, yet the dependency graph does not encode that. A wave runner can execute both in parallel and either leave `15-03` incomplete or force it to wait on a sibling outside the declared graph.

**How I would fix it**
- Best option: move the 13/13 SC4 aggregate to `15-05` or a small final aggregation plan that depends on both `15-03` and `15-04`.
- Keep `15-03` acceptance to Mode 1 7/7 only.
- Keep `15-04` acceptance to Mode 3 6/6 only.
- If the aggregate must stay in `15-03`, change `15-03` to depend on `15-04` and move it to a later wave.

### MEDIUM 4. `15-01` still mixes mutually different trigger contracts

**Evidence**
- `15-01-PLAN.md` says not to create a new analysis path and requires `pipeline._process` direct import/call.
- The same task also says the recommended controlled trigger is: create doc -> copy fixture to `uploads/{uid}/{analysisId}.mp4` -> let production S3 notification drive the pipeline.
- Acceptance requires a grep count for `_process`, regardless of which trigger mode the script actually implements.

**Risk**

The plan says "single controlled trigger", but the implementation contract is still ambiguous. A script that uses notification does not need to call `_process`; a script that calls `_process` does not need to copy into `uploads/`; a careless implementation can satisfy the grep check and still double-trigger by doing both. The current acceptance checks the presence of `_process`, not mutual exclusion of trigger paths.

**How I would fix it**
- Pick one default for Phase 15 sweeps.
- My preference: use direct `_process(bucket, sourceS3Key, uid, analysisId)` for sweep evidence, because it is deterministic and avoids async S3/SQS timing. Reserve `/analyze` or S3 notification for a single Plan 02 smoke.
- If both modes are useful, implement explicit mutually exclusive flags:
  - `--trigger direct-process`
  - `--trigger notification`
  - `--trigger analyze`
- Acceptance should assert exactly one trigger mode was selected and that the other two paths were not invoked.

### MEDIUM 5. `15-02` automated verification no longer proves SSM equals live Lambda

**Evidence**
- `15-02-PLAN.md` acceptance requires SSM `/sunity/motion/runpod-analyze-url` to equal live Lambda `RUNPOD_ANALYZE_URL`.
- The current automated verify reads only Lambda `Environment.Variables` and checks four keys are present.
- It does not query SSM or compare the SSM value to the Lambda env value.

**Risk**

The env-preservation check is useful, but it can pass while the SSM source of truth remains stale. A later `sam deploy` can still revert Lambda to the old Pod URL even though the current verify printed `ALL_PRESENT`.

**How I would fix it**
- Add a single machine check that reads both values and compares them:
  - `aws ssm get-parameter --name /sunity/motion/runpod-analyze-url`
  - `aws lambda get-function-configuration --query Environment.Variables.RUNPOD_ANALYZE_URL`
- Fail if either is empty or if they differ.
- Keep the four-key Lambda env preservation assertion as a separate check.

### MEDIUM 6. Mode 1 success "not false-positive" gate is still subjective

**Evidence**
- `15-03-PLAN.md` says success videos should have a high overall score and no unfair fault penalty.
- The plan does not define a numeric floor, severity condition, or exact finding predicate for this Mode 1 side of SCORE-04.
- `15-04` has the stronger frozen-baseline `MODE_SELF` gate, but `15-03` still claims a Mode 1 SCORE-04 side gate.

**Risk**

An executor can mark Mode 1 "비위양성" as PASS based on a vague reading of "high" or "부당". That makes the evidence hard to reproduce and hard to reject when the score is borderline.

**How I would fix it**
- Either make the Mode 1 item observational only and leave the SCORE-04 gate entirely to `15-04`, or define deterministic thresholds.
- Example deterministic shape:
  - `overallScore >= <explicit floor>`
  - no high-severity finding in the success rows
  - `server_error == 0`
  - `referenceMotionId` matches expected motion
- If no defensible floor exists yet, do not make this a blocking PASS/FAIL gate in Phase 15.

### LOW 7. `phase15_keys.json` is produced but not listed as a modified artifact

**Evidence**
- `15-01-PLAN.md` says `upload_phase15_dataset.py` outputs `backend/scripts/phase15_keys.json`.
- `files_modified` lists the three scripts, but not `backend/scripts/phase15_keys.json`.

**Risk**

Some GSD-style execution/reporting tools use `files_modified` to verify expected outputs. The generated keys file can be missed in summaries or artifact checks even though later plans depend on it.

**How I would fix it**
- Add `backend/scripts/phase15_keys.json` to `15-01-PLAN.md` `files_modified`.
- Also list it under artifacts with schema `sourceS3Key/motionId/mode/label/referenceMotionId`.

## Iteration-3 Closure Status

| Iteration-3 issue | Iteration-4 status |
|---|---|
| Fixture uploads under `uploads/` trigger production path | Mostly resolved by `fixtures/phase15`; see HIGH 1 for new dependency drift |
| Fixed doc identity collides across modes/reruns | Mostly resolved by per-run/per-mode identity; see HIGH 2 for alphanumeric `analysisId` bug |
| `15-03` reuses `15-04` MODE_SELF docs without dependency | Partly resolved by moving MODE_SELF ownership to `15-04`; SC4 cross-plan aggregate still needs graph fix |
| Lambda env preservation not asserted | Mostly resolved; four-key check added, but SSM equality verify regressed |

## Recommended Patch Order

1. Decide whether `15-02` depends on `15-01`; if yes, encode it. If no, make its smoke test independent.
2. Sanitize all generated `analysisId` values and dry-run every generated upload key through `parse_upload_key`.
3. Move 13/13 SC4 aggregation to `15-05` or encode a real dependency from the aggregate owner to both `15-03` and `15-04`.
4. Make `sweep_phase15.py` trigger mode explicit and mutually exclusive; remove acceptance checks that only grep for `_process`.
5. Restore SSM-vs-Lambda URL equality to `15-02` automated verification.
6. Either define deterministic Mode 1 false-positive thresholds or make that row observational.

