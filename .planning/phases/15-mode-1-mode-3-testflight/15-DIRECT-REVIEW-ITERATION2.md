# Phase 15 Direct Plan Review — Iteration 2

**Reviewed:** 2026-06-17  
**Reviewer:** Codex direct review, no external GSD/agent review used  
**Scope:** Updated `15-01-PLAN.md` .. `15-05-PLAN.md` after the first direct review, plus local service contracts.

## Verdict

**Needs another revision before execution.** The first-review fixes are mostly incorporated: Mode 3 now requires `createdAt` and pair verification, downstream reference verification uses `seed-reference-downstream.mjs --verify`, TestFlight now uses a store-signed `testflight-preview` profile, Mode 3 wording is aligned to "N점 발전", the threshold path is corrected, and runtime SIGABRT is moved to device verification.

The remaining risks are lower in number but still execution-blocking. The main issue is that the planned Phase 15 fixture S3 keys are not valid `/analyze` keys, while `15-02` uses Pod `/analyze` for the liveness E2E. There are also coverage and operational sync gaps that can create false evidence or make a later deploy revert the Pod URL.

## Findings

### HIGH 1. Phase 15 fixture S3 keys are invalid for Pod `/analyze`

**Evidence**
- `15-01-PLAN.md` Task 3 uploads fixtures to `uploads/phase15/{motion}-correct.mp4` and `uploads/phase15/{motion}-fault.mp4`.
- `backend/runpod_inference/server.py::analyze` calls `parse_upload_key(req.key)` and rejects invalid keys with HTTP 400.
- `backend/shared/python/sunity_shared/s3keys.py` accepts only `uploads/{uid}/{analysisId}.{mp4|mov}`, where `analysisId` is alphanumeric.
- `15-02-PLAN.md` Task 2 says to call Pod `/analyze` with a dataset video such as `climb-correct`.

**Risk**
The bring-up liveness E2E in Plan 02 will fail before inference starts: `/analyze` cannot parse `uploads/phase15/climb-correct.mp4`. Direct `pipeline._process()` sweeps can use arbitrary S3 keys because uid/analysis_id are passed explicitly, but `/analyze` is stricter and mirrors the Lambda delegation contract.

Using `uploads/phase15/...` also puts non-analysis fixture objects under the app upload prefix. S3 notifications may enqueue them only for Lambda to skip as invalid keys.

**How I would fix it**
- Store reusable fixtures outside the app upload namespace, for example `fixtures/phase15/{motion}-correct.mp4`.
- For any `/analyze` smoke test, copy one fixture to a valid temporary key:
  - `uploads/phase15_smoke/<alphanumeric_analysis_id>.mp4`
  - create the matching Firestore doc under `users/phase15_smoke/analyses/<analysis_id>`
  - call `/analyze` with that key and require 202.
- Keep `sweep_phase15.py` direct `_process()` runs separate from `/analyze` runs, and document which path each task verifies.

### HIGH 2. RunPod URL sync is not durable across deploys

**Evidence**
- `backend/template.yaml` sets `RUNPOD_ANALYZE_URL` from SSM dynamic reference `/sunity/motion/runpod-analyze-url`.
- `.claude/scripts/setup_pod_full.sh` safely merges the new URL into the live Lambda env, but it does not update the SSM parameter.
- `15-02-PLAN.md` requires Lambda env sync, but does not require updating the SSM source of truth.
- `.planning/debug/phase17-e2e-five-issues.md` already records a prior class of failures where deploy-time env values reset runtime configuration.

**Risk**
Plan 02 can pass immediately after `update-function-configuration`, then a later SAM deploy can restore the old RunPod URL from SSM. The phase evidence would be true at the moment of testing but not stable for TestFlight/device UAT.

**How I would fix it**
- Treat `/sunity/motion/runpod-analyze-url` as the durable source of truth.
- On Pod replacement:
  - update SSM `/sunity/motion/runpod-analyze-url` to the new `/analyze` URL,
  - merge-update the live Lambda env from `get-function-configuration` so no existing env is dropped,
  - verify both SSM and Lambda env match the new URL.
- Add a post-sync assertion that `RUNPOD_AUTH_TOKEN`, `VIDEO_BUCKET`, and `FIREBASE_SA_PARAM` still exist in Lambda env after the update.

### MEDIUM 3. Mode 1 "11 reference" E2E coverage is still not proven

**Evidence**
- `15-CONTEXT.md` D-04 says Mode 1 comparison target is all 11 registered references.
- `15-01-PLAN.md` Task 3 uploads 13 local dataset videos: 7 success and 6 fail.
- The registered reference list includes 11 ids: `ref-climb`, `ref-foxtop`, `ref-foxtop-split`, `ref-invert`, `ref-sideway-spin`, `ref-combo`, `ref-elbow-twist-sister`, `ref-kip-up`, `ref-pdshape`, `ref-peter-pan`, `ref-power-spin`.
- The Phase 15 local dataset described in context covers the 6 success/fail pair motions plus combo, not all original 11 reference motions.

**Risk**
Plan 03 can claim "11 reference 대상 Mode 1 실 E2E" while only exercising the 7 available local success videos. Field verification over 11 reference docs is useful, but it is not the same as E2E analysis for each `referenceMotionId`.

**How I would fix it**
- Make the coverage explicit:
  - 11/11 reference field verification via `seed-reference-downstream.mjs --verify`.
  - 7 local success-video Mode 1 E2E for the Phase 15 dataset.
  - Additional Mode 1 E2E for the missing registered references using existing `reference/{motionId}.mp4` copied as the student input, if the success criterion truly requires all 11.
- In the evidence table, record `referenceMotionId` coverage count separately from dataset video count.

### MEDIUM 4. SCORE-04 fail-video run mode is ambiguous

**Evidence**
- `15-03-PLAN.md` Task 3 says fail videos can be run as `MODE_EXPERT 또는 self`.
- The score and false-positive interpretation differ by mode:
  - `MODE_EXPERT` includes reference angle comparison and `referenceMotionId`.
  - `MODE_SELF` is absolute/self-progress oriented and does not prove the same reference comparison behavior.
- `15-04-PLAN.md` already owns the Mode 3 fail -> success delta evidence.

**Risk**
The same fail video can produce incomparable evidence depending on which mode the executor chooses. A fail video passing a self-mode check does not necessarily prove the Mode 1 false-positive gate against the matching registered reference.

**How I would fix it**
- Split the evidence:
  - SCORE-04 false-positive gate: run success and fail videos in `MODE_EXPERT` against their matching `referenceMotionId`.
  - MODE-02 delta gate: run fail -> success in `MODE_SELF` with pair isolation.
- Remove "또는 self" from the SCORE-04 task unless a separate rationale defines exactly what self-mode evidence proves.

### MEDIUM 5. EAS auto-submit command can select the wrong submission profile

**Evidence**
- `15-05-PLAN.md` adds `build.testflight-preview`, but submit config currently exists under `submit.production`.
- The plan action allows `eas build --profile testflight-preview --platform ios --auto-submit`.
- Expo's official automate-submissions docs state that `--auto-submit` tries a submission profile with the same name as the selected build profile by default, and `--auto-submit-with-profile=<profile-name>` is needed to use a different one.

**Risk**
If the executor uses the plain `--auto-submit` command, EAS may look for `submit.testflight-preview`, not `submit.production`. That can fail late or prompt unexpectedly.

**How I would fix it**
- Either add `submit.testflight-preview` mirroring the production iOS ASC settings, or make the command explicit:
  - `eas build --profile testflight-preview --platform ios --auto-submit-with-profile production`
  - or build first, then `eas submit --platform ios --profile production --latest`.
- Update `15-05` acceptance to reject plain `--auto-submit` unless a matching submit profile exists.

Source: Expo "Automate submissions" docs, "Selecting a submission profile".

### LOW 6. `testflight-preview` autoIncrement is not checked by the automated verify

**Evidence**
- `15-05-PLAN.md` acceptance requires `autoIncrement:true`.
- The node assertion in Task 1 checks profile existence, non-internal distribution, channel, env, and that `preview` remains internal, but does not check `autoIncrement`.

**Risk**
A missing `autoIncrement` can cause App Store Connect/TestFlight build-number rejection, especially with repeated validation builds.

**How I would fix it**
- Add `if (p.autoIncrement !== true) throw new Error('autoIncrement required')` to the Task 1 node assertion.

## First-Review Closure Status

| Prior issue | Iteration 2 status |
|---|---|
| Mode 3 `createdAt` / pairing | Resolved in plan text |
| Reference downstream verifier | Resolved in plan text |
| Internal `preview` profile for TestFlight | Mostly resolved; see MEDIUM 5 for auto-submit profile detail |
| Mode 3 degree-vs-point delta | Resolved in plan text |
| Threshold YAML path | Resolved in plan text |
| SCORE-04 terms under-specified | Improved, but see MEDIUM 4 for mode ambiguity |
| Runtime SIGABRT overclaimed by build logs | Resolved in plan text |

## Recommended Patch Order

1. Patch `15-01` and `15-02` so fixture storage keys and `/analyze` smoke keys are separate and contract-correct.
2. Patch `15-02` to update both SSM source-of-truth and live Lambda env, with env-preservation assertions.
3. Patch `15-03` to separate 11-reference coverage from 13-video dataset coverage, and add missing-reference E2E inputs if required.
4. Patch `15-03` SCORE-04 to require `MODE_EXPERT` for false-positive evidence and leave `MODE_SELF` to Plan 04.
5. Patch `15-05` auto-submit command/profile and verify `autoIncrement:true`.

