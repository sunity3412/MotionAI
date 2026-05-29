# External Integrations

**Analysis Date:** 2026-05-29

Sunity AI Coach integrates four external systems: Firebase (Auth + Firestore), AWS (S3 + SQS + Lambda + SSM + API Gateway), RunPod (GPU inference), and Cerebras (LLM). The Motion AI infrastructure is intentionally separated from the existing sunity.ai EC2 platform.

## APIs & External Services

**Self-hosted HTTP API (AWS API Gateway HTTP API):**
- `POST /upload-url` - Issues S3 presigned PUT URL + analysisId
  - Handler: `backend/functions/upload-url/app.py`
  - Auth: Firebase ID token (`Authorization: Bearer <idToken>`)
  - App client: `app/src/lib/api.ts` `requestUploadUrl()`
- `GET /reference` - Lists reference motions (정은지 expert motions, screen #9)
  - Handler: `backend/functions/reference-api/app.py`
  - Auth: Firebase ID token
- Base URL injected to app via `EXPO_PUBLIC_API_BASE_URL`; SAM output `ApiBaseUrl`
- CORS: `AllowOrigins: ["*"]`, methods GET/POST/OPTIONS (`backend/template.yaml`)

**RunPod GPU Inference (delegated analysis):**
- `POST /analyze` `{bucket, key}` - Triggers async GPU pose analysis, returns 202 immediately
  - Server: `backend/runpod_inference/server.py` (FastAPI)
  - Auth: shared-secret header `X-RunPod-Token` (== `RUNPOD_AUTH_TOKEN`)
  - Caller: `backend/functions/pipeline/app.py` `_delegate_to_runpod()` via stdlib `urllib`
  - Endpoint shape: `https://<pod-id>-8000.proxy.runpod.net/analyze` (behind Cloudflare — custom User-Agent set to bypass bot block 1010)
- `GET /health` - Liveness probe (no auth)
- Models pulled at pod setup: NLF TorchScript from `https://github.com/isarandi/nlf/releases/download/v0.3.2/nlf_l_multi_0.3.2.torchscript` (`backend/runpod_inference/setup.sh`)

**Cerebras (LLM):**
- Coaching-sentence generation, model `llama3.1-8b`
  - Client: `cerebras.cloud.sdk.Cerebras` in `backend/shared/python/sunity_shared/analysis/coach_writer.py`
  - Endpoint: `chat.completions.create` with `response_format={"type": "json_object"}`
  - Auth: API key from SSM Parameter Store, env var `CEREBRAS_KEY_PARAM` names the parameter
  - Graceful degradation: returns `{}` on missing key / failure / timeout → numeric fallback sentences (no fabricated output)

## Data Storage

**Databases:**
- Firebase Firestore (project `sunity-ai-coach`, `.firebaserc`)
  - App client (JS SDK v12): `app/src/lib/firebase.ts` `getFirestore(app)`
  - Backend Admin client: `backend/shared/python/sunity_shared/firestore_admin.py`
  - Collections:
    - `users/{uid}/analyses/{analysisId}` - per-user analysis docs (status, result, error, flat-stored `angles`)
    - `reference/{motionId}` - expert reference motions (read-only to clients; written by seed script)
  - Result-writing app-side helpers: `app/src/lib/userAnalyses.ts`, `app/src/lib/referenceMotions.ts`
  - Note: angle matrices stored flat (`angles` + `anglesJointKeys` + `anglesFrames`) — Firestore nested-array restriction; reader reshapes (`firestore_admin.complete_analysis`)

**File Storage:**
- AWS S3 bucket `sunity-motion-pilot-videos` (region `ap-northeast-2`)
  - Created out-of-band via awscli (NOT by SAM template — preserves existing `reference/` videos)
  - Key scheme (`backend/shared/python/sunity_shared/s3keys.py`):
    - `uploads/{uid}/{analysisId}.{mp4|mov}` - user uploads (30-day lifecycle expiry)
    - `results/` - analysis outputs
    - `reference/` - expert reference videos (presigned 7-day)
  - Upload: app PUTs directly to presigned URL (`app/src/lib/api.ts` `uploadToS3`); video never passes through Lambda
  - Playback: `pipeline` issues presigned GET URLs, 7-day expiry (`_PLAYBACK_EXPIRES`)
  - Content-Type set on PUT (`video/mp4` / `video/quicktime`) so `expo-video` recognizes the object

**Caching:**
- None (no Redis/Memcached). NLF model cached in GPU VRAM at pod startup.

## Authentication & Identity

**Auth Provider:** Firebase Authentication (anonymous + ID tokens; guest mode supported)
- App: Firebase JS SDK Auth with AsyncStorage persistence (`app/src/lib/firebase.ts`)
- Token flow: app calls `user.getIdToken()` → sends `Authorization: Bearer <idToken>` → backend verifies
- Backend verification: `backend/shared/python/sunity_shared/auth.py` `verify_request()` via `firebase_admin.auth.verify_id_token`
- Firestore Admin (backend) bypasses security rules using service-account credentials — app never gets admin rights
- Security rules: `firestore.rules` — deny-by-default; users access only their own `users/{uid}/**`; `reference/**` read-only to authed users, writes blocked

**Service account credentials (multi-source, `auth.py` `_load_service_account_dict`):**
1. `FIREBASE_SA_JSON` - inline JSON (RunPod pod, no SSM access)
2. `FIREBASE_SA_PATH` - file path (RunPod mounted seed)
3. `FIREBASE_SA_PARAM` - AWS SSM Parameter Store `/sunity/motion/firebase-sa` (Lambda default)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/Datadog). Errors logged to CloudWatch via Python `logging`.

**Logs:**
- CloudWatch Log Groups per Lambda, 30-day retention (`backend/template.yaml` `*LogGroup`)
- RunPod server: stdlib `logging` to stdout (`backend/runpod_inference/server.py`)
- Pipeline failures mapped to Firestore `error{code,message}`: `ERR_NO_HUMAN`, `ERR_NOT_POLE_MOTION`, `ERR_SERVER_ERROR`

## CI/CD & Deployment

**Hosting:**
- App: EAS Build + EAS Update (OTA via `https://u.expo.dev/d2872ef6-...`), TestFlight distribution
- Backend: AWS Lambda (ARM64) + HTTP API + SQS, stack `sunity-motion-pilot` (region `ap-northeast-2`)
- GPU: RunPod pod running uvicorn (manual `setup.sh` + uvicorn launch)

**CI Pipeline:**
- No CI service config detected (no `.github/workflows`, no CodeBuild). Deploys are manual (`sam deploy`, `eas build`/`eas submit`).
- iOS submit automated via ASC API Key registered in EAS (`app/eas.json` submit.production.ios)

## Environment Configuration

**Mobile (`EXPO_PUBLIC_*`, build-time inlined):**
- `EXPO_PUBLIC_FIREBASE_*` (6 vars) - Firebase web config
- `EXPO_PUBLIC_API_BASE_URL` - Motion AI HTTP API base

**Lambda env vars:**
- `VIDEO_BUCKET`, `FIREBASE_SA_PARAM` (Globals)
- `RUNPOD_ANALYZE_URL`, `RUNPOD_AUTH_TOKEN` (PipelineFunction; if unset, falls back to in-Lambda NLF which yields NaN on CPU)
- `CEREBRAS_KEY_PARAM` (coach_writer; optional)

**RunPod env vars:**
- `RUNPOD_AUTH_TOKEN` (required — server returns 503 if unset), `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `FIREBASE_SA_JSON`/`FIREBASE_SA_PATH`, `CUDA_VISIBLE_DEVICES`

**Secrets location:**
- AWS SSM Parameter Store (SecureString): `/sunity/motion/firebase-sa`, Cerebras key
- Firebase Admin keys and AWS access keys exist as local gitignored files (`firebase-sa.json`, `*firebase-adminsdk*.json`, `sunity-api_accessKeys.csv`) — never committed (`.gitignore`)

## Webhooks & Callbacks

**Incoming (event-driven, not HTTP webhooks):**
- S3 `s3:ObjectCreated:*` on `sunity-motion-pilot-videos` → SQS `AnalysisQueue` → `PipelineFunction` (SQS trigger, BatchSize 1)
- Bucket notification configured out-of-band via awscli (not in SAM template; see `backend/README.md`)
- DLQ: `AnalysisDLQ` after maxReceiveCount 3

**Outgoing:**
- Lambda `PipelineFunction` → RunPod `POST /analyze` (HTTP delegation)
- RunPod server → Firestore Admin writes (status/result/error updates); app observes via `onSnapshot`

---

*Integration audit: 2026-05-29*
