# Phase 15 Direct Plan Review — Iteration 3

**Reviewed:** 2026-06-17  
**Reviewer:** Codex direct review, no external GSD/agent review used  
**Scope:** `15-01-PLAN.md` .. `15-05-PLAN.md` after iteration-2 patches, plus local backend contracts that Phase 15 depends on.

## Verdict

**Still not execution-ready.** The iteration-2 fixes closed most of the earlier issues: SSM is now included in the RunPod URL sync, `testflight-preview` uses `--auto-submit-with-profile production`, Mode 1 coverage is no longer overstated as 11 live student videos, SCORE-04 is intentionally pinned to `MODE_SELF`, and `autoIncrement` is checked.

The remaining blockers are about execution identity and side effects. The plan now uses parse-compatible `uploads/phase15-{motion}/correct|fault.mp4` keys, which fixes `/analyze` parsing but also makes the dataset upload look exactly like a production app upload. Because the bucket notification watches `uploads/`, fixture upload can enqueue Lambda/RunPod analysis before the planned Firestore docs and sweep controls exist. In addition, the same fixed `uid`/`analysis_id` pairs are reused across Mode 1, Mode 3, and reruns, so evidence can overwrite or race itself.

## Findings

### HIGH 1. Parse-compatible fixture uploads can trigger the production S3 → SQS → Lambda path

**Evidence**
- `15-01-PLAN.md` now uploads the dataset to keys such as `uploads/phase15-climb/correct.mp4` and `uploads/phase15-climb/fault.mp4`.
- `backend/shared/python/sunity_shared/s3keys.py` accepts exactly `uploads/{uid}/{analysisId}.{mp4|mov}`.
- `backend/README.md` configures bucket notification for `s3:ObjectCreated:*` with prefix `uploads/`.
- `backend/functions/pipeline/app.py::handler` parses every notified upload key and, in RunPod delegate mode, writes `status=queued` before POSTing to the Pod.
- `firestore_admin.update_analysis_status` uses `set(..., merge=True)`, so it can create or partially mutate `users/{uid}/analyses/{analysisId}` even when the intended sweep doc has not been created yet.

**Risk**

Task 3 in `15-01` says "upload fixtures", but those uploads are not inert fixtures. They can immediately enqueue production analysis for `users/phase15-{motion}/analyses/correct|fault`. If the matching analysis doc does not exist yet, Lambda/RunPod can create partial failed/queued state. If the doc is created later by `sweep_phase15.py`, the sweep may reuse a doc already touched by the production path. This can produce false evidence, stale status, or duplicate analysis for the same S3 object.

This is a stronger version of the iteration-2 key issue: the key is now parser-compatible, but that compatibility activates the production trigger.

**How I would fix it**
- Store reusable Phase 15 source videos outside the notified app upload namespace, for example `fixtures/phase15/{motion}/correct.mp4` and `fixtures/phase15/{motion}/fault.mp4`.
- Let `phase15_keys.json` reference those fixture keys as immutable source inputs.
- For a real `/analyze` smoke, create a unique temporary app-style object only after creating its Firestore doc:
  - `uid=phase15_smoke_<epoch>`
  - `analysisId=<alphanumeric_unique_id>`
  - key `uploads/{uid}/{analysisId}.mp4`
  - doc includes `mode`, `referenceMotionId` if needed, `createdAt`, and `updatedAt`
- Do not both rely on S3 notification and manually call `_process`/`/analyze` for the same object. Pick one trigger path per evidence item.

### HIGH 2. Fixed `uid=phase15-{motion}` and `analysis_id=correct|fault` collide across modes and reruns

**Evidence**
- `15-01-PLAN.md` defines stable keys where parser output is `uid=phase15-{motion}`, `analysis_id=correct|fault`.
- `15-03-PLAN.md` runs Mode 1 evidence for the success videos.
- `15-04-PLAN.md` runs Mode 3 fail -> success pairs using the same video set.
- A Firestore analysis doc path is `users/{uid}/analyses/{analysisId}`; it cannot simultaneously represent a Mode 1 `MODE_EXPERT` run and a Mode 3 `MODE_SELF` run.

**Risk**

The success video for a motion is needed in both Mode 1 and Mode 3, but the current identity maps both to the same document: `users/phase15-{motion}/analyses/correct`. Running `15-03` and `15-04` can overwrite each other's `mode`, `referenceMotionId`, `comparison`, result payload, status, timestamps, and evidence. Rerunning the phase also reuses the same ids, so stale or partially failed data can be mistaken for a fresh run.

This undermines both key claims: Mode 1 reference comparison evidence and Mode 3 `previousAnalysisId` pairing evidence.

**How I would fix it**
- Decouple source fixture keys from analysis document identity.
- Generate analysis identity per run and per mode:
  - Mode 1: `uid=phase15_mode1_<runId>`, `analysisId=<motion>Success` or another alphanumeric unique id.
  - Mode 3: `uid=phase15_mode3_<motion>_<runId>`, `analysisId=fault<runId>` and `success<runId>`.
- If the production `/analyze` contract requires the S3 key to encode the analysis identity, copy the immutable fixture into a unique `uploads/{uid}/{analysisId}.mp4` key for that one run.
- Require evidence tables to record `runId`, `uid`, `analysisId`, `mode`, `s3Key`, and `createdAt` so stale docs are visibly rejected.

### HIGH 3. `15-03` says it reuses `15-04` MODE_SELF docs but does not depend on `15-04`

**Evidence**
- `15-03-PLAN.md` and `15-04-PLAN.md` are both wave 2 and both depend only on `15-01` and `15-02`.
- `15-03-PLAN.md` Task 3 says `15-04` already produces the same success/fail `MODE_SELF` docs and that `15-03` should reuse them, with duplicate sweep forbidden.
- Because the two plans are in the same wave, `15-03` cannot assume `15-04` has completed.

**Risk**

The execution graph allows `15-03` and `15-04` to run in parallel. Under that graph, `15-03` may look for MODE_SELF docs that do not exist yet, or it may create its own MODE_SELF docs despite the "duplicate sweep forbidden" instruction. Combined with fixed ids from HIGH 2, this creates a direct race over the same Firestore document paths.

**How I would fix it**
- Choose one owner for MODE_SELF success/fail evidence.
- Best option: move SCORE-04 MODE_SELF severity assertion into `15-04`, then make `15-03` only own Mode 1 and reference-field evidence.
- Alternative: make `15-03` depend on `15-04` and explicitly consume `15-04-SUMMARY.md` / `15-MODE3-DUALCOACH-EVIDENCE.md`.
- If parallel execution is required, remove the reuse claim and give `15-03` its own unique MODE_SELF run ids.

### MEDIUM 4. Lambda env sync verifies URL equality but not env preservation

**Evidence**
- Iteration 2 asked for post-sync assertion that `RUNPOD_AUTH_TOKEN`, `VIDEO_BUCKET`, and `FIREBASE_SA_PARAM` still exist after `update-function-configuration`.
- `15-02-PLAN.md` now verifies SSM `/sunity/motion/runpod-analyze-url` equals live Lambda `RUNPOD_ANALYZE_URL`.
- The plan text says existing env keys are preserved, but the automated verify only queries the RunPod URL value.

**Risk**

`update-function-configuration --environment Variables=...` replaces the Lambda environment map unless the executor merges the existing values correctly. The plan says to preserve them, but without a machine assertion a bad merge can pass the current URL check while dropping auth, bucket, or Firebase SA env. That would make the next analysis fail in a way that looks like a Pod or model issue.

**How I would fix it**
- Add a post-update assertion that reads the full Lambda env and fails if any critical key is missing:
  - `RUNPOD_ANALYZE_URL`
  - `RUNPOD_AUTH_TOKEN`
  - `VIDEO_BUCKET`
  - `FIREBASE_SA_PARAM`
- Record the presence check in `15-POD-BRINGUP-EVIDENCE.md` without printing secret values.
- Prefer a small merge script over hand-written CLI JSON so the executor cannot accidentally replace the whole env map.

## Iteration-2 Closure Status

| Iteration-2 issue | Iteration-3 status |
|---|---|
| Fixture keys invalid for `/analyze` | Parser issue resolved, but production-trigger side effect introduced; see HIGH 1 |
| RunPod URL not durable across deploys | Mostly resolved by SSM + live Lambda sync; env preservation still needs assertion |
| Mode 1 11-reference coverage overstated | Resolved in plan text: 11 field-verified, 7 live student videos |
| SCORE-04 mode ambiguity | Resolved by explicit `MODE_SELF` rationale; no longer treating as blocker |
| EAS submit profile ambiguity | Resolved with `--auto-submit-with-profile production` |
| `autoIncrement` missing from assertion | Resolved in `15-05` node assertion |

## Recommended Patch Order

1. Move reusable Phase 15 videos out of `uploads/`; use `fixtures/phase15/...` or another non-notified prefix.
2. Change `sweep_phase15.py`/`phase15_keys.json` contract so fixture source keys are separate from generated analysis doc identities.
3. Generate unique `uid`/`analysisId` per mode and per run; only create temporary `uploads/{uid}/{analysisId}.mp4` keys for controlled `/analyze` smoke tests.
4. Resolve the `15-03` / `15-04` dependency conflict by giving MODE_SELF evidence one owner.
5. Add Lambda env-preservation assertion to `15-02`.

