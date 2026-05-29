<!-- refreshed: 2026-05-29 -->
# Concerns

**Analysis Date:** 2026-05-29

Pilot-stage MVP. Each item is tagged **INTENTIONAL SCAFFOLD** (deliberate placeholder awaiting ML/infra) vs **GENUINE** (real debt/risk) vs **RESOLVED/WATCH** so the planner can tell MVP gaps apart from actual problems.

## Security

- **Exposed AWS key pending deactivation (GENUINE — HIGH).** `plan.md` cleanup queue lists an active leaked `sunity-api` key (`AKIA...64A`) queued to deactivate but **not yet done**. Also queued: rotate `sunity-motion` admin key and `RUNPOD_AUTH_TOKEN`, then SAM redeploy. **Do this first.**
- **Secrets hygiene otherwise sound (VERIFIED — no issue).** No hardcoded secrets in code; no `.env` git-tracked; `app/.env` confirmed gitignored. Backend keys via SSM Parameter Store — Cerebras `CEREBRAS_KEY_PARAM` (`backend/shared/python/sunity_shared/analysis/coach_writer.py:25`), Firebase SA `FIREBASE_SA_PARAM` (`backend/shared/python/sunity_shared/auth.py`). Firebase web config in `app/src/lib/firebase.ts` uses `EXPO_PUBLIC_*` (public-by-design).
- **Firestore rules are sole access enforcement, but `firestore.rules` not in repo (WATCH).** `app/src/lib/firebase.ts:4`. The `users/{uid}/analyses/{id}` ownership invariant can't be reviewed from source. Recommend vendoring the rules file into the repo.
- **RunPod auth = single static shared secret over public proxy URL (ACCEPTABLE FOR PILOT).** Fail-closed (503) when unset at `backend/runpod_inference/server.py:94-102`; no rotation or scoping.

## Tech Debt

- **`TechniqueRecognizer` is a conservative placeholder (INTENTIONAL SCAFFOLD).** `backend/shared/python/sunity_shared/analysis/technique.py:57-88` — `FallbackRecognizer` never identifies the move (`name="미상"`), only flags elbows/knees ≥150° as `EXTEND`. So `line` scoring under-penalizes by design. Swappable via Protocol (Gemini / Pole-arina) — the documented next work item (commit `6375097`).
- **Scoring tolerances are unvalidated heuristics (GENUINE — MEDIUM).** `dimensions.py:33-40` (`_LINE_TOL_DEG=20`, `_STABILITY_TOL_DEG=8`) plus a hard `NOT_POLE_SIMILARITY_THRESHOLD` gate (`backend/functions/pipeline/app.py:247-255`) that can false-reject unusual-but-valid pole videos. Needs tuning on real footage ("P0 #4").
- **App simulated result = dev/demo fixture (INTENTIONAL SCAFFOLD).** `app/src/lib/simulatedResult.ts`, `app/src/lib/simulationWriter.ts`; result-screen fallback fires only when no Firestore doc exists (`app/src/app/analysis/result.tsx:137-139`). Contract-identical to real `AnalysisResult`; samples labeled `샘플 · …`.
- **`currentAngle` not yet produced by backend (INTENTIONAL SCAFFOLD).** `app/src/app/analysis/result.tsx:72-98` — reference `meanAngles` are real, but user current angles are still fixture until NLF backfills them.
- **`/ml` directory is a stub (DOCUMENTATION DEBT).** Only `ml/ml_CLAUDE.md` exists; real ML lives in `backend/shared/python/sunity_shared/analysis/` and `backend/runpod_inference/`.

## Known Bugs

- **TestFlight build 9 launch crash — fixed in source, not shipped (RESOLVED/UNSHIPPED).** `letterSpacing: -1` SIGABRT on iOS 26.4.2; removed at `app/src/app/analysis/loading.tsx:478-485`. Needs build 10 to ship.
- **React Hook-order risk — preemptively fixed (RESOLVED).** `loading.tsx:329-339` moved above early returns.
- **S3 playback expiry / content-type pitfalls (RESOLVED — guardrail).** 7-day TTL at `backend/functions/pipeline/app.py:65-69`; `Content-Type` set on PUT at `app/src/lib/api.ts:52-77`. Caveat: Lambda fallback temp creds cap presigned TTL at session length.

## Performance

- **NLF 3D needs GPU; CPU → NaN (INTENTIONAL — infra in progress).** `backend/shared/python/sunity_shared/analysis/pose_estimator.py:26-29,82-83`. This is the in-flight 2D→3D `#7-follow` pivot. Production routes to RunPod (`backend/runpod_inference/server.py`); the Lambda fallback is flow-verification only (produces NaN).
- **RunPod single-worker / single-Pod (PILOT-ACCEPTABLE).** `server.py:24-27` (workers=1, GPU-VRAM bound). No autoscaling.
- **Pod lifecycle is manual / ephemeral (GENUINE — OPERATIONAL RISK).** `plan.md` shows the Pod ID + proxy URL change on recreate, requiring a CloudFormation `RunpodAnalyzeUrl` update each time; a stopped Pod silently breaks all real analysis. Add `/health` (`server.py:153-160`) monitoring.

## Fragile Areas

- **Flat-array angle storage needs manual reshape on every read (GENUINE — MEDIUM).** Firestore bans nested arrays, so `(T, J)` angle matrices are flattened with `anglesJointKeys` / `anglesFrames` (`backend/functions/pipeline/app.py:156-168,303-311`). Readers must reshape with the *stored* joint count (`pipeline/app.py:192,238`), NOT the current `skeleton.NUM_JOINTS`; a mismatch silently corrupts DTW. **Never reorder `skeleton.JOINT_KEYS` without a migration.**
- **`referenceMotionId` omission bug-class (GENUINE — pattern).** `app/src/app/analysis/loading.tsx:96-111`. App writes the doc; backend reads by field name. The fixed bug (commit `b63c245`) was the app omitting `referenceMotionId` → backend "기준 모션 없음", surfacing only in Mode 1 real analysis. Keep the `setDoc` payload and backend `meta.get(...)` in lockstep.
- **Broad `except Exception` (LOW).** 9 occurrences (`pipeline/app.py:358`, `runpod_inference/server.py:129`, `coach_writer.py:36,66,93`). Mostly intentional graceful degradation with `log.exception`; risk is masking fixable bugs as a generic `server_error`. Typed excepts (`NoHumanError`, `NotPoleMotionError`) precede the catch-all.

## Test Coverage Gaps

- **No app tests at all (GENUINE — MEDIUM).** Zero `*.test.*` / `*.spec.*` under `app/src`. App↔backend Firestore contract, upload flow, status-machine rendering, and result enrichment are all unverified. See `TESTING.md`.
- **Backend ML adapters untested (EXPECTED).** `coach_writer`, `frame_extractor`, `pose_estimator`, `interfaces`, `skeleton` lack tests (heavy deps / GPU). The algorithm core IS tested (16 backend test files). Manual smoke scripts: `backend/scripts/_nlf_smoke.py`, `verify_nlf_*.py`.
- **Lambda handlers untested (LOW).** `functions/upload-url/app.py`, `functions/reference-api/app.py` — thin wrappers over tested shared modules.

## Dependencies at Risk

- **Expo SDK / firebase v12 sensitivity (WATCH).** `app/src/lib/firebase.ts:13-16` uses `@ts-expect-error` for `getReactNativePersistence` (missing from firebase v12 default types); `app/AGENTS.md` warns "Expo HAS CHANGED." Pin versions before upgrades.
- **iOS 26 native style regressions (WATCH).** The `letterSpacing` SIGABRT shows iOS 26+ changed native style handling; audit other negative numeric style values and test on iOS 26+ before submit.

## Missing Critical Features (both tied to `#7-follow`)

- Real per-video user angles in results — blocks fully accurate Mode 1/3 numbers.
- Technique classification for true IPSF-conditional scoring — blocks differentiated per-move scoring.
