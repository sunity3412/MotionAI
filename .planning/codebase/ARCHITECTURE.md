<!-- refreshed: 2026-05-29 -->
# Architecture

**Analysis Date:** 2026-05-29

## System Overview

Sunity AI Coach is a three-component monorepo. A React Native app uploads practice videos directly to S3; an async serverless pipeline analyzes joint motion and writes results to Firestore; the app reads results live via Firestore listeners. Heavy ML (3D pose) runs on a RunPod GPU server that reuses the same pipeline code as the Lambda.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      App — React Native + Expo (TypeScript)               │
│  Screens (expo-router)          Data-source hooks         HTTP client     │
│  `app/src/app/`                 `app/src/lib/*.ts`        `app/src/lib/api.ts` │
└───────┬───────────────────────────┬───────────────────────────┬──────────┘
        │ (1) POST /upload-url        │ (3) onSnapshot subscribe   │ (2) PUT video
        │     GET /reference          │     users/{uid}/analyses   │
        ▼                            ▼                            ▼
┌──────────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐
│  HTTP API (API Gateway)  │  │  Firebase Firestore  │  │   AWS S3 bucket    │
│  upload-url / reference  │  │  users/{uid}/...     │  │  uploads/ results/ │
│  `backend/functions/*`   │  │  reference/{id}      │  │  reference/        │
└──────────┬───────────────┘  └──────────▲───────────┘  └─────────┬──────────┘
           │ presigned PUT URL            │ Admin SDK write         │ s3:ObjectCreated
           │                              │                         ▼
           │                   ┌──────────┴──────────┐    ┌──────────────────┐
           │                   │  Analysis pipeline  │◀───│   SQS queue +DLQ │
           │                   │  `functions/pipeline│    │  AnalysisQueue   │
           │                   │  /app.py`           │    └──────────────────┘
           │                   └──────────┬──────────┘
           │           RunPod delegate    │ (or local fallback)
           │           (HTTP POST /analyze)▼
           │                   ┌─────────────────────────────────────────────┐
           │                   │  ML core `backend/shared/.../sunity_shared/  │
           │                   │  analysis/` — features→temporal→DTW→KISMAM→  │
           │                   │  dimensions→assemble (model-agnostic, pure)  │
           │                   │  Adapters: ffmpeg / NLF 3D pose / Cerebras   │
           │                   └─────────────────────────────────────────────┘
           │                   ┌─────────────────────────────────────────────┐
           └──────────────────▶│  RunPod GPU server (FastAPI)                 │
                               │  `backend/runpod_inference/server.py`        │
                               └─────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| App screens | UI, navigation, video pick, upload orchestration | `app/src/app/` |
| App data-source hooks | Firestore subscriptions; isolate screens from data source | `app/src/lib/userAnalyses.ts`, `app/src/lib/referenceMotions.ts` |
| App HTTP client | Authed calls to backend HTTP API + S3 PUT | `app/src/lib/api.ts` |
| Data contract (TS) | Single source of types shared with backend | `app/src/types/analysis.ts` |
| upload-url Lambda | Issue presigned S3 PUT URL + analysisId | `backend/functions/upload-url/app.py` |
| reference Lambda | List reference motions (GET /reference) | `backend/functions/reference-api/app.py` |
| pipeline Lambda | SQS consumer: orchestrate analysis OR delegate to RunPod | `backend/functions/pipeline/app.py` |
| RunPod GPU server | Run the same `_process` on GPU (NLF 3D pose) | `backend/runpod_inference/server.py` |
| ML analysis core | Pure algorithm modules (no model/AWS deps) | `backend/shared/python/sunity_shared/analysis/` |
| ML adapters | Heavy-dependency boundary (ffmpeg / NLF / Cerebras) | `backend/shared/.../analysis/{frame_extractor,pose_estimator,coach_writer}.py` |
| Firestore Admin client | Backend-only write/read bypassing security rules | `backend/shared/.../firestore_admin.py` |
| Data contract (Python) | Mirror of TS contract: statuses, modes, errors | `backend/shared/.../models.py` |
| Infra | SAM template: API, SQS, layer, functions, log retention | `backend/template.yaml` |

## Pattern Overview

**Overall:** Event-driven serverless backend with a contract-first, decoupled mobile client. The backend is layered around a model-agnostic algorithm core wrapped by swappable adapters; the app is a thin presentation layer over data-source abstraction hooks.

**Key Characteristics:**
- **Contract-first:** `app/src/types/analysis.ts` and `backend/shared/.../models.py` mirror each other and `docs/contract.md`. Changing one requires changing all three.
- **No video through Lambda:** App PUTs video directly to S3 via presigned URL; S3 `ObjectCreated` → SQS → pipeline. Avoids Lambda payload/timeout limits.
- **Single pipeline, two runtimes:** `pipeline/app.py::_process` runs either on Lambda (CPU fallback, produces NaN without GPU) or RunPod GPU (operational). RunPod imports the Lambda module by path and reuses `_process` — zero branching.
- **Adapter boundary:** Algorithm core (`features`/`temporal`/`motiondtw`/`kismam`/`dimensions`/`assemble`) is pure and unit-tested; heavy deps (ffmpeg, torch/NLF, Cerebras) sit behind `Protocol`-typed adapters and are lazy-imported.
- **Live state via Firestore:** App never polls the backend; it subscribes to `users/{uid}/analyses/{id}` with `onSnapshot` and reacts to status transitions.

## Layers

**App presentation layer:**
- Purpose: Render screens, handle navigation and video picking
- Location: `app/src/app/` (file-based routing via expo-router)
- Contains: Screen components, the analysis flow (`analysis/`), bottom tabs (`(tabs)/`)
- Depends on: `app/src/lib/` hooks + client, `app/src/theme/` tokens, `app/src/types/`
- Used by: expo-router (entry `expo-router/entry`)

**App data-access layer:**
- Purpose: Isolate screens from data source (Firestore today, REST later)
- Location: `app/src/lib/`
- Contains: Firestore subscription hooks (`useMyAnalyses`, `useAnalysisDoc`, `useReferenceMotion`), HTTP client (`api.ts`), Firebase init (`firebase.ts`)
- Depends on: `firebase` SDK, `EXPO_PUBLIC_*` env
- Used by: Screen components

**Backend API layer:**
- Purpose: Synchronous app-facing endpoints
- Location: `backend/functions/upload-url/`, `backend/functions/reference-api/`
- Contains: Two HTTP API Lambdas (auth → validate → respond)
- Depends on: `sunity_shared` (auth, responses, validation, s3keys, firestore_admin)
- Used by: App `api.ts`

**Backend async pipeline layer:**
- Purpose: Run analysis off the request path
- Location: `backend/functions/pipeline/`
- Contains: SQS consumer; orchestration + RunPod delegation
- Depends on: `sunity_shared.analysis.*`, `firestore_admin`, S3, optional RunPod HTTP
- Used by: SQS (triggered by S3 ObjectCreated)

**ML algorithm core layer:**
- Purpose: Model-agnostic scoring math
- Location: `backend/shared/python/sunity_shared/analysis/`
- Contains: `features`, `temporal`, `motiondtw`, `kismam`, `dimensions`, `segments`, `technique`, `skeleton`, `selfmotion`, `assemble`
- Depends on: numpy only (pure)
- Used by: pipeline `_process`

**ML adapter layer:**
- Purpose: Bridge core to heavy/external dependencies
- Location: `backend/shared/.../analysis/{frame_extractor,pose_estimator,coach_writer}.py`, contracts in `interfaces.py`
- Contains: `FrameExtractor` (ffmpeg), `PoseEstimator` (NLF 3D), `CoachWriter` (Cerebras LLM)
- Depends on: imageio/ffmpeg, torch/NLF, requests
- Used by: pipeline `_process` (lazy-imported in `_ensure_adapters()`)

## Data Flow

### Primary Analysis Path (Mode 1 / Mode 3)

1. User selects mode + picks video (`app/src/app/(tabs)/analyze.tsx`), routed to loading screen
2. App requests presigned URL: `POST /upload-url` (`app/src/lib/api.ts:43` → `backend/functions/upload-url/app.py:33`)
3. App creates Firestore doc `status='uploading'` then PUTs video to S3 (`app/src/app/analysis/loading.tsx:82` `startAnalysisUpload`)
4. S3 `ObjectCreated` → SQS `AnalysisQueue` (`backend/template.yaml:79`)
5. pipeline Lambda consumes message, parses uid/analysisId from key (`backend/functions/pipeline/app.py:315` `lambda_handler`, `backend/shared/.../s3keys.py:34`)
6. **Delegate path (prod):** Lambda sets `status='queued'`, POSTs to RunPod `/analyze`; RunPod runs `_process` on GPU (`backend/runpod_inference/server.py:163`)
7. **Fallback path (dev):** Lambda runs `_process` directly (`backend/functions/pipeline/app.py:206`)
8. `_process`: status transitions → extract frames → NLF 3D keypoints → joint angles → temporal fill → technique profile → dimensions (line/stability) → mode branch
9. Mode 1: load reference motion, DTW align, KISMAM deviation, `not_pole_motion` guard, segment scores; Mode 3: absolute dims + delta vs previous analysis (`_mode3_comparison`)
10. Assemble `AnalysisResult`, write `status='done'` + result + flat angles to Firestore (`firestore_admin.complete_analysis`)
11. App's `useAnalysisDoc` `onSnapshot` fires → loading screen auto-navigates to `/analysis/result`

### Reference Motion Listing (Mode 1 selection)

1. Mode 1 selected without preselected motion → `/analysis/reference`
2. App reads `reference/{motionId}` collection (currently direct Firestore subscribe in `app/src/lib/referenceMotions.ts`; backend `GET /reference` exists as the future swap-in)
3. Selected `referenceMotionId` carried as route param → loading → stored on analysis doc so backend can locate the reference angles

**State Management:**
- Auth + analysis state lives in Firestore; app holds it via React hooks (`useState` + `onSnapshot`). No global app store (no Redux/Zustand).
- Backend has no shared mutable state across invocations except cached singletons (Firestore client, ML adapters, RunPod pipeline module).

## Key Abstractions

**Data contract (mirrored types):**
- Purpose: Single shared shape between app, backend, ML
- Examples: `app/src/types/analysis.ts`, `backend/shared/.../models.py`, `docs/contract.md`
- Pattern: Manual mirror — comments in each file mandate co-editing

**Data-source hook:**
- Purpose: Decouple screens from the backing store so it can be swapped without touching UI
- Examples: `app/src/lib/userAnalyses.ts`, `app/src/lib/referenceMotions.ts`
- Pattern: `useXxx()` returns `{ data, loading, error }`; internals subscribe to Firestore

**Adapter Protocol:**
- Purpose: Pluggable heavy/external dependencies behind the algorithm core
- Examples: `backend/shared/.../analysis/interfaces.py` (`FrameExtractor`, `PoseEstimator`, `CoachWriter`)
- Pattern: `typing.Protocol`; concrete adapters live as sibling modules; lazy instantiated

**TechniqueRecognizer / TechniqueProfile:**
- Purpose: IPSF scoring is technique-conditional (a bent knee can be correct or a fault depending on the move). Recognizer supplies which joints must extend
- Examples: `backend/shared/.../analysis/technique.py` (`FallbackRecognizer` today; Gemini/Pole-arina adapter planned)
- Pattern: swappable recognizer; scoring layer (`dimensions.py`) depends only on the profile

**S3 key as routing token:**
- Purpose: Reconstruct uid/analysisId from the upload key, no DB lookup needed at trigger time
- Examples: `backend/shared/.../s3keys.py` — `uploads/{uid}/{analysisId}.{ext}`
- Pattern: build + regex-parse pair

## Entry Points

**App:**
- Location: `expo-router/entry` (package.json `main`), root layout `app/src/app/_layout.tsx`, intro `app/src/app/index.tsx`
- Triggers: App launch
- Responsibilities: Light-theme status bar, headerless stack; intro does anonymous Firebase sign-in then routes to `(tabs)`

**HTTP API Lambdas:**
- Location: `backend/functions/upload-url/app.py::lambda_handler`, `backend/functions/reference-api/app.py::lambda_handler`
- Triggers: API Gateway HTTP API (`POST /upload-url`, `GET /reference`)
- Responsibilities: Firebase token auth → validate → S3/Firestore action → JSON response

**Pipeline Lambda:**
- Location: `backend/functions/pipeline/app.py::lambda_handler`
- Triggers: SQS (S3 ObjectCreated upstream)
- Responsibilities: Per-message dispatch to RunPod delegate or local `_process`

**RunPod server:**
- Location: `backend/runpod_inference/server.py` (`POST /analyze`, `GET /health`)
- Triggers: Pipeline Lambda HTTP delegation
- Responsibilities: Token-auth, parse key, run `_process` in a background task on GPU

## Architectural Constraints

- **Threading:** App is single-threaded JS (React Native). Lambdas are single-invocation. RunPod runs FastAPI with `--workers 1` (NLF holds GPU VRAM) and uses `BackgroundTasks` for analysis; a module-load lock guards pipeline import (`backend/runpod_inference/server.py:59`).
- **Global state / singletons:** Firestore Admin client (`firestore_admin._client`), ML adapters (`pipeline._FRAME_EXTRACTOR/_POSE_ESTIMATOR/_COACH_WRITER`), recognizer (`_RECOGNIZER`), RunPod pipeline module (`_pipeline_module`), and app auth (`globalThis.__sunityAuth`) are all module/global cached.
- **Firestore nested-array ban:** Firestore forbids nested arrays, so the `(T, J)` angle matrix is stored flat (`angles` + `anglesJointKeys` + `anglesFrames`) and reshaped on read. See `firestore_admin.complete_analysis` and `app/src/types/analysis.ts` `AnalysisDoc`.
- **Infra separation:** Motion AI must run on its own Lambda/S3 infra, fully separate from the existing sunity.ai EC2 platform (`CLAUDE.md §3`, `template.yaml` description).
- **External S3 bucket:** The video bucket is NOT created by the SAM template (preserves a pre-existing bucket with reference videos); bucket notification/lifecycle/CORS are configured out-of-band (`backend/template.yaml:67`).
- **GPU requirement:** NLF 3D pose inference requires GPU; the Lambda CPU fallback path produces NaN and exists only for flow validation.
- **No dark theme:** Light theme only; dark backgrounds banned except the analysis loading screen's intentional navy exception (`app/src/app/analysis/loading.tsx`).

## Anti-Patterns

### Reading Firestore by polling instead of subscribing

**What happens:** Fetching analysis status with one-shot reads or timers.
**Why it's wrong:** The backend updates status asynchronously across several stages; polling misses transitions and wastes reads.
**Do this instead:** Subscribe with `onSnapshot` via the hooks in `app/src/lib/userAnalyses.ts` (`useAnalysisDoc`, `useMyAnalyses`). The loading screen reacts to `done`/`failed` automatically.

### Editing one side of the data contract only

**What happens:** Adding a field to `app/src/types/analysis.ts` without updating `backend/shared/.../models.py` / `assemble.py` / `docs/contract.md`.
**Why it's wrong:** Keys are matched by string between app and backend; drift silently breaks result rendering.
**Do this instead:** Treat the contract as one unit — change `analysis.ts`, `models.py`, the `assemble` builders, and `docs/contract.md` together.

### Routing video bytes through Lambda

**What happens:** Uploading the video file as a Lambda request body.
**Why it's wrong:** Exceeds payload/timeout limits; the architecture deliberately keeps video off Lambda.
**Do this instead:** Use the presigned PUT flow — `POST /upload-url` then direct S3 PUT (`app/src/lib/api.ts`, `backend/functions/upload-url/app.py`).

### Calling ML adapters in the RunPod-delegate path

**What happens:** Importing ffmpeg/torch/NLF at module top level in `pipeline/app.py`.
**Why it's wrong:** In delegate mode the Lambda never runs `_process`; eager imports add cold-start cost for nothing.
**Do this instead:** Keep adapters lazy inside `_ensure_adapters()` (`backend/functions/pipeline/app.py:123`).

### Hardcoding theme values

**What happens:** Literal colors/radii/spacing in screen styles.
**Why it's wrong:** Breaks the design system (brand `#FF4B33`, tokenized spacing/radius).
**Do this instead:** Import from `app/src/theme/` (`colors`, `radius`, `spacing`, `layout`, `typography`).

## Error Handling

**Strategy:** Map domain failures to a closed set of contract error codes; surface user-facing Korean messages; record failures on the Firestore doc so the app shows them live.

**Patterns:**
- Pipeline catches `NoHumanError` → `no_human`, `NotPoleMotionError` → `not_pole_motion`, anything else → `server_error`, via `firestore_admin.fail_analysis` (`backend/functions/pipeline/app.py:342`, mirrored in `runpod_inference/server.py:105`).
- HTTP Lambdas return `responses.error(code, msg, status)`; `AuthError` → 401, `ValidationError` → its `http_status`.
- App layers errors: local upload error > Firestore doc error > default (`app/src/app/analysis/loading.tsx:303`). Hook subscription errors degrade gracefully to empty state.
- `not_pole_motion` is a safety gate (Mode 1): if KISMAM similarity < `NOT_POLE_SIMILARITY_THRESHOLD`, analysis fails rather than showing a meaningless score.

## Cross-Cutting Concerns

**Logging:** Backend uses stdlib `logging` (INFO) to CloudWatch; log groups have 30-day retention (`template.yaml:211`). App uses `console.warn` guarded by `__DEV__`.
**Validation:** Backend `sunity_shared.validation.validate_upload_request`; app validates format/size client-side in `analyze.tsx` (`mp4`/`mov`, ≤100MB) mirroring `models.py` constants.
**Authentication:** Firebase Auth (anonymous/guest allowed). App sends `Authorization: Bearer <idToken>`; backend `sunity_shared.auth.verify_request`. Firestore security rules (`firestore.rules`) isolate `users/{uid}/**` to the owner; backend writes via Admin SDK which bypasses rules. Service account loaded from AWS Parameter Store (`FIREBASE_SA_PARAM`), never hardcoded.

---

*Architecture analysis: 2026-05-29*
