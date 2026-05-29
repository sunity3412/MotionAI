<!-- refreshed: 2026-05-29 -->
# Structure

**Analysis Date:** 2026-05-29

## Repository Layout

Sunity AI Coach is a three-component monorepo. Each component has its own runtime, dependency manifest, and `*_CLAUDE.md` context file.

```text
SunityMotion/
├── CLAUDE.md                  # Root project context (read first)
├── design.md                  # Design system (read before any UI work)
├── plan.md                    # Current work queue (check every session)
├── README.md
├── contract.md                # App <-> backend data contract
├── ia.md                      # Screen specs / information architecture
├── reference-motions.md       # Reference (pro) motion catalog notes
├── athlete-checklist.md
├── sunity_aws_guide.md        # AWS setup guide (SAM-adapted)
├── research/                  # Pole-sports technique research (ML design source)
│
├── app/                       # React Native + Expo frontend (TypeScript)
│   ├── app_CLAUDE.md / AGENTS.md
│   ├── assets/fonts/          # Pretendard font files
│   ├── scripts/
│   └── src/
│       ├── app/               # expo-router file-based routes (screens)
│       │   ├── _layout.tsx        # Root layout
│       │   ├── index.tsx          # Entry/splash
│       │   ├── (tabs)/            # Tab navigator group
│       │   │   ├── _layout.tsx
│       │   │   ├── index.tsx       # Home
│       │   │   ├── analyze.tsx     # Start analysis
│       │   │   ├── history.tsx     # Past analyses
│       │   │   └── profile.tsx     # My page / settings
│       │   └── analysis/          # Analysis flow screens
│       │       ├── reference.tsx   # Pick pro reference motion (Mode 1)
│       │       ├── samples.tsx     # Sample picker
│       │       ├── loading.tsx     # Upload + status machine
│       │       └── result.tsx      # Result / scoring screen
│       ├── components/         # Reusable UI (GrowthChart, OctagonScore, VideoCompare)
│       ├── lib/               # Data sources, HTTP client, Firebase, fixtures
│       ├── theme/             # colors / typography / index (design tokens)
│       └── types/             # analysis.ts (shared TS types)
│
├── backend/                   # AWS Lambda (Python 3.12 ARM64) + SAM
│   ├── backend_CLAUDE.md / README.md
│   ├── template.yaml          # SAM stack `sunity-motion-pilot`
│   ├── samconfig.toml
│   ├── requirements-dev.txt
│   ├── yolo11n.pt             # YOLO11 detector weights
│   ├── functions/            # Lambda handlers (thin wrappers)
│   │   ├── upload-url/         # Presigned S3 upload URL
│   │   ├── reference-api/      # Reference motion CRUD
│   │   └── pipeline/           # Main analysis pipeline (SQS-triggered)
│   ├── shared/python/sunity_shared/   # Shared Lambda layer (real logic lives here)
│   │   ├── analysis/          # ML pipeline + scoring (see below)
│   │   ├── auth.py            # Firebase token verification
│   │   ├── events.py          # SQS/event helpers
│   │   ├── firestore_admin.py # Firestore writes
│   │   ├── models.py          # Pydantic/data models
│   │   ├── responses.py       # HTTP response helpers
│   │   ├── s3keys.py          # S3 key conventions
│   │   └── validation.py      # Input validation
│   ├── runpod_inference/     # FastAPI GPU server (reuses analysis/ code)
│   │   └── server.py          # POST /analyze, /health
│   ├── scripts/              # Manual verify/overlay utilities + render outputs
│   └── tests/                # pytest suite (conftest.py injects shared/python)
│
└── ml/                        # Documentation only (ml_CLAUDE.md); no executable code
```

## Key File Locations

| Concern | Location |
|---|---|
| App entry / routing | `app/src/app/_layout.tsx`, file-based routes under `app/src/app/` |
| App HTTP client | `app/src/lib/api.ts` |
| Firebase init (anon auth + Firestore) | `app/src/lib/firebase.ts` |
| App data-source hooks | `app/src/lib/userAnalyses.ts`, `app/src/lib/referenceMotions.ts` |
| App fixtures (demo/sim) | `app/src/lib/simulatedResult.ts`, `app/src/lib/simulationWriter.ts` |
| Shared TS types | `app/src/types/analysis.ts` |
| Design tokens | `app/src/theme/colors.ts`, `typography.ts`, `index.ts` |
| SAM infra definition | `backend/template.yaml`, `backend/samconfig.toml` |
| Main analysis pipeline | `backend/functions/pipeline/app.py` |
| ML pipeline + scoring | `backend/shared/python/sunity_shared/analysis/` |
| GPU inference server | `backend/runpod_inference/server.py` |
| Backend tests | `backend/tests/` (mirrors `analysis/` module names) |

## ML / Scoring Modules (`backend/shared/python/sunity_shared/analysis/`)

| File | Purpose |
|---|---|
| `frame_extractor.py` | Sample frames from video |
| `pose_estimator.py` | YOLO11 detect → NLF 3D pose (CUDA required) |
| `skeleton.py` | `JOINT_KEYS`, `NUM_JOINTS` — joint ordering (do not reorder) |
| `features.py`, `temporal.py` | Feature extraction / temporal signals |
| `motiondtw.py` | Band-constrained DTW alignment |
| `segments.py`, `selfmotion.py` | Segmentation / Mode 3 self-comparison |
| `dimensions.py` | IPSF scoring dimensions (angle/line/stability tolerances) |
| `kismam.py` | Scoring helper |
| `technique.py` | Technique recognition (currently `FallbackRecognizer` placeholder) |
| `assemble.py` | Build final `AnalysisResult` |
| `coach_writer.py` | Cerebras LLM coaching text (graceful no-op fallback) |
| `interfaces.py` | Protocol definitions (e.g. recognizer swap-in) |

## Naming Conventions

- **App screens:** expo-router file-based routing. Folder groups in parens (`(tabs)/`), screen files lowercase (`result.tsx`). Layouts are `_layout.tsx`.
- **App components:** PascalCase `.tsx` (`OctagonScore.tsx`).
- **App lib/types/theme:** camelCase `.ts` modules.
- **Backend Lambdas:** one folder per function under `functions/`, handler always `app.py`, with a co-located `requirements.txt`.
- **Backend shared modules:** snake_case `.py` under `sunity_shared/`.
- **Backend tests:** `backend/tests/test_<module>.py`, one per `analysis/` module.
- **Manual scripts:** `backend/scripts/verify_*.py`, `_*_smoke.py`; render output dirs prefixed `overlay_ref-<motion>[_variant]`.

## Where to Add New Code

- **New app screen** → add a route file under `app/src/app/` (or `app/src/app/analysis/` for the analysis flow).
- **New reusable UI** → `app/src/components/`.
- **New app data access / API call** → `app/src/lib/` (keep HTTP in `api.ts`).
- **New Lambda endpoint** → new folder under `backend/functions/` with `app.py` + `requirements.txt`, then wire into `backend/template.yaml`.
- **New shared/business logic** → `backend/shared/python/sunity_shared/` (handlers stay thin).
- **New ML/scoring step** → `backend/shared/python/sunity_shared/analysis/`, with a matching `backend/tests/test_<module>.py`.

## Special Directories

- `backend/scripts/overlay_ref-*/` — generated render/overlay outputs from manual verification runs (not app runtime code).
- `backend/.aws-sam/`, `backend/.venv*`, `app/.expo`, `node_modules`, `__pycache__` — build/cache artifacts, gitignored.
- `ml/` — documentation stub only (`ml_CLAUDE.md`); the real ML code lives in `backend/shared/python/sunity_shared/analysis/`.
