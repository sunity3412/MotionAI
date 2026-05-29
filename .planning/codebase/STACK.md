# Technology Stack

**Analysis Date:** 2026-05-29

Sunity AI Coach is a three-component monorepo. Each component has its own runtime and dependency set:

- `/app` — React Native + Expo mobile app (TypeScript)
- `/backend` — AWS Lambda serverless API + analysis pipeline (Python, SAM)
- `/backend/runpod_inference` — GPU inference server (Python, FastAPI) deployed on RunPod
- `/ml` — Documentation only (`ml/ml_CLAUDE.md`). The actual ML code lives under `backend/shared/python/sunity_shared/analysis/`.

## Languages

**Primary:**
- TypeScript (~5.9.2) - Mobile app under `app/src/` (React Native, strict mode)
- Python 3.12 - Lambda runtime (`backend/template.yaml` `Runtime: python3.12`); analysis core + handlers under `backend/`

**Secondary:**
- Python 3.x on GPU pod - RunPod inference server `backend/runpod_inference/server.py` (PyTorch base image)
- JavaScript (ESM `.mjs`) - Node admin scripts `app/scripts/seed-reference-motions.mjs`, `app/scripts/verify-firebase.mjs`

## Runtime

**Mobile App:**
- Expo SDK ~54.0.33 (`app/package.json`)
- React 19.1.0 / React Native 0.81.5
- New Architecture enabled (`app/app.json` `newArchEnabled: true`)
- Expo Router ~6.0.23 (file-based routing, entry `expo-router/entry`)

**Backend (Lambda):**
- Python 3.12, ARM64 architecture (`backend/template.yaml` `Architectures: [arm64]`)
- Default function Timeout 15s / MemorySize 256MB; pipeline function 900s / 1024MB
- `boto3` provided by the Lambda runtime (not vendored in `requirements.txt`)

**RunPod GPU Server:**
- PyTorch + CUDA base image (RunPod PyTorch 2.4 or similar; `torch`/`torchvision` supplied by base image, not pinned)
- Uvicorn single worker: `uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1`
- CUDA required — NLF model diverges to NaN on CPU (`backend/shared/python/sunity_shared/analysis/pose_estimator.py`)

**Package Manager:**
- App: npm (lockfile `app/package-lock.json` expected; `package.json` `private: true`)
- Backend: pip via SAM build; per-function `requirements.txt` + dev `backend/requirements-dev.txt`
- No `.nvmrc` or `.python-version` files detected; Python version is pinned in `backend/template.yaml`.

## Frameworks

**Mobile (Core):**
- `expo` ~54.0.33 - App framework
- `expo-router` ~6.0.23 - File-based navigation (`app/src/app/`)
- `react-native` 0.81.5 / `react` 19.1.0 - UI runtime
- `react-native-safe-area-context` ~5.6.0, `react-native-screens` ~4.16.0 - Navigation primitives
- `react-native-svg` 15.12.1 - Score gauge / chart rendering (`app/src/components/OctagonScore.tsx`, `GrowthChart.tsx`)

**Mobile (Media & UX):**
- `expo-image-picker` ~17.0.11 - Camera/gallery video selection
- `expo-video` ~3.0.16 - Result-screen video playback
- `expo-linear-gradient` ~15.0.8 - Home brand gradient
- `expo-linking` ~8.0.12, `expo-constants` ~18.0.13, `expo-status-bar` ~3.0.9
- `expo-updates` ~29.0.17 - OTA updates (channel-based, EAS)

**Backend (Lambda handlers):**
- AWS SAM (`AWS::Serverless-2016-10-31`) - IaC, `backend/template.yaml`
- AWS HTTP API (`AWS::Serverless::HttpApi`) - 2 routes: `POST /upload-url`, `GET /reference`
- AWS SQS - async analysis queue (`AnalysisQueue` + `AnalysisDLQ`)
- Standard-library `urllib` for RunPod HTTP delegation (no `requests` dependency)

**GPU Inference Server:**
- FastAPI >=0.115,<1.0 - `backend/runpod_inference/server.py`
- Uvicorn[standard] >=0.30,<1.0 - ASGI server
- Pydantic >=2.5,<3.0 - request/response models

**Testing:**
- pytest >=8,<9 (`backend/requirements-dev.txt`) - Backend unit tests under `backend/tests/`
- TypeScript `tsc --noEmit` (`npm run typecheck`) - App type checking (no JS test runner configured)

**Build/Dev:**
- EAS Build / EAS CLI >= 19.0.0 (`app/eas.json`) - App build & submit, channels development/preview/production
- SAM CLI (`backend/samconfig.toml`) - `sam build` / `sam deploy`, stack `sunity-motion-pilot`, region `ap-northeast-2`
- `sam build --use-container` required (Mac native binaries fail on Lambda Linux — see project memory)

## Key Dependencies

**Mobile (Critical):**
- `firebase` ^12.13.0 - JS SDK v12 modular API. Auth (anonymous + ID tokens) + Firestore client (`app/src/lib/firebase.ts`)
- `@react-native-async-storage/async-storage` 2.2.0 - Firebase Auth persistence backing store
- `firebase-admin` ^13.10.0 (devDependency) - Admin SDK for the reference-motion seed script only

**Backend (Critical):**
- `firebase-admin` >=6,<7 - Firestore Admin + Firebase Auth ID-token verification (all 3 functions)
- `numpy` >=1.26,<2.0 (RunPod) / >=1.26,<3 (Lambda + dev) - Analysis algorithm core (DTW, joint angles, scoring)

**ML / Inference (RunPod-only, `backend/runpod_inference/requirements.txt`):**
- `ultralytics` >=8.2 - YOLO11n person bounding-box detection (`pose_estimator.py`)
- NLF (Neural Localizer Fields, NeurIPS'24) - 3D HMR model, TorchScript `backend/scripts/nlf_l_multi.torchscript`, downloaded from GitHub release in `setup.sh`
- `torch` / `torchvision` - Supplied by RunPod base image (not pinned); `torchvision` import required for TorchScript op registration
- `imageio` >=2.34 + `imageio-ffmpeg` >=0.5.1 - Frame extraction (`frame_extractor.py`, 9 fps / 640px downsample)
- Pillow (`PIL`) - Frame resize + YOLO image input
- `boto3` >=1.34,<2.0 - S3 download on the pod

**LLM:**
- `cerebras.cloud.sdk` (Cerebras) - Korean coaching-sentence generation, model `llama3.1-8b` (`coach_writer.py`). Imported lazily; graceful no-op when key unset.

**Analysis core (pure Python + numpy, `backend/shared/python/sunity_shared/analysis/`):**
- `motiondtw.py` - Sakoe-Chiba band-constrained DTW (FastDTW approximation; interface allows swap to `fastdtw`)
- `features.py`, `temporal.py`, `kismam.py`, `dimensions.py`, `technique.py`, `segments.py`, `assemble.py`, `skeleton.py`

## Configuration

**Mobile environment (`app/.env`, template `app/.env.example`):**
- `EXPO_PUBLIC_FIREBASE_API_KEY`, `_AUTH_DOMAIN`, `_PROJECT_ID`, `_STORAGE_BUCKET`, `_MESSAGING_SENDER_ID`, `_APP_ID` - Firebase web config (not secret; security enforced by Firestore rules)
- `EXPO_PUBLIC_API_BASE_URL` - SAM `ApiBaseUrl` output (e.g. `https://xxxx.execute-api.ap-northeast-2.amazonaws.com/pilot`)
- `EXPO_PUBLIC_` prefix vars are inlined at build time by Expo SDK 54.

**App build config:**
- `app/app.json` - Expo config (bundle `com.sunity.aicoach`, owner `sunity3412`, EAS projectId `d2872ef6-...`, updates URL `https://u.expo.dev/d2872ef6-...`)
- `app/eas.json` - Build profiles + iOS submit config (appleId `sunity3412@gmail.com`, teamId `8ZL3YL358P`, ascAppId `6772934567`)
- `app/tsconfig.json` - Extends `expo/tsconfig.base`, `strict: true`

**Backend config:**
- `backend/template.yaml` - SAM template (functions, SQS, HTTP API, log groups w/ 30-day retention)
- `backend/samconfig.toml` - Deploy defaults (stack `sunity-motion-pilot`, region `ap-northeast-2`, `Stage=pilot`)
- Secrets live in AWS SSM Parameter Store (`/sunity/motion/firebase-sa`, `CEREBRAS_KEY_PARAM`) — never hardcoded. Lambda env vars: `VIDEO_BUCKET`, `FIREBASE_SA_PARAM`, `RUNPOD_ANALYZE_URL`, `RUNPOD_AUTH_TOKEN`.
- RunPod env vars: `RUNPOD_AUTH_TOKEN`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `FIREBASE_SA_JSON`/`FIREBASE_SA_PATH`, `CUDA_VISIBLE_DEVICES`, optional `NLF_MODEL_PATH`/`YOLO_WEIGHTS_PATH`.

**Secret files present (gitignored — contents not read):**
- `firebase-sa.json`, `sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json` - Firebase Admin service-account keys
- `sunity-api_accessKeys.csv` - AWS access keys
- `.firebaserc` - Firebase project alias (`sunity-ai-coach`)
- `firestore.rules` - Firestore security rules

## Platform Requirements

**Development:**
- Node + npm (Expo SDK 54 / React Native 0.81) for `/app`
- Python 3.12 + SAM CLI + Docker Desktop (`sam build --use-container`) for `/backend`
- AWS account (region `ap-northeast-2`), Firebase project `sunity-ai-coach`

**Production:**
- iOS/Android via EAS Build; iOS submit to App Store Connect app `6772934567`
- Backend on AWS Lambda (ARM64) + API Gateway HTTP API + SQS, stack `sunity-motion-pilot`
- GPU inference on RunPod pod (CUDA GPU required; NLF model loaded into VRAM at startup)
- Video storage on S3 bucket `sunity-motion-pilot-videos` (created out-of-band, not by SAM template)

## Declared-but-Not-Yet-Implemented

These appear in `CLAUDE.md` / `app/CLAUDE.md` as the intended stack but are NOT present in code as of this analysis:

- RevenueCat / `react-native-purchases` - No payment SDK in `app/package.json` (pilot intentionally has no billing)
- CloudFront - Not referenced; video delivery uses S3 presigned URLs directly
- `victory-native` / `react-native-gifted-charts` - Documented in `app/CLAUDE.md` but not installed; charts currently use `react-native-svg` directly
- ViTPose-S - Listed in `CLAUDE.md` 2D pipeline but superseded by NLF 3D backbone (see `pose_estimator.py` docstring)

---

*Stack analysis: 2026-05-29*
