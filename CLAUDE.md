# CLAUDE.md — Sunity AI Coach

> 작업 시작 전 반드시 이 순서로 읽을 것: CLAUDE.md → design.md → plan.md

---

## 1. 프로젝트 한 줄 요약

폴스포츠 수강생이 연습 영상을 올리면 AI가 프로 선수 모션과 비교해 자세 교정 피드백을 주는 모바일 앱.

**북극성**: 폴스포츠 학원에서 수강생이 혼자 앱을 켜고 분석 결과를 확인하는 것.

---

## 2. 파일럿 목표 (개발의 최우선 기준)

```
Step 1. 앱 MVP 완성 → 정은지 선수(폴스포츠 세계챔피언)에게 시연
Step 2. 정은지 선수 촬영 → 백엔드로 업로드 → 기준 모션 자동 등록
Step 3. 폴스포츠 학원 파일럿 실증

파일럿 성공 기준:
  수강생이 혼자서 아래 두 가지를 완료할 수 있어야 함

  - Mode 3: 본인 영상 2개 비교 → 성장 확인
  - Mode 1: 정은지 모션 불러와 비교 → 전문가 기준 점수 확인

```

**파일럿 최소 요건**

```
✅ 영상 업로드 → 관절 분석 → 결과 화면 (Mode 3)
✅ 정은지 기준 모션 1개 이상 → 비교 점수 (Mode 1)
✅ TestFlight로 게스트 모드 바로 사용 가능
❌ 결제 플랜 불필요   ❌ 회원가입 강제 불필요
```

---

## 3. 기술 스택 (결정 완료 — 변경 금지)

```
앱        : React Native + Expo (TypeScript)
백엔드     : AWS Lambda (Python) + API Gateway + SQS
DB        : Firebase Firestore
스토리지   : AWS S3 + CloudFront
ML        : YOLO11 → ViTPose-S → MotionDTW (FastDTW)
LLM       : Cerebras (빠른 추론)
결제       : RevenueCat (iOS/Android 통합)
배포       : EAS Build (Expo)
시크릿     : AWS Parameter Store (.env 하드코딩 금지)
```

> ⚠️ 서니티에는 이미 sunity.ai 운영 플랫폼(EC2: Next.js+Spring Boot)이 있음.
> Motion AI는 반드시 별도 Lambda+S3 인프라로 분리. 기존 EC2에 얹지 말 것.

---

## 4. 디자인 시스템

> **모든 UI 작업 전 design.md 필독.**

```
브랜드 컬러 : #FF4B33  (절대 변경 금지)
폰트        : Pretendard
테마        : 라이트 전용 (다크 모드 구현 불필요)
배경        : 가입/로그인/서브 = 흰색(#FFFFFF), 홈 = 브랜드 그라디언트.
             다크 블랙 배경 금지. 상세는 design.md §5-1 참조.
```

미설계 화면도 멈추지 말 것. design.md 규칙 따라 자체 판단으로 구현.
(알림창, 에러 팝업, 권한 요청 등 모두 포함)

---

## 5. 세부 컨텍스트 파일 위치

```
ML 파이프라인 작업   → /ml/CLAUDE.md
앱 (React Native)   → /app/CLAUDE.md
백엔드 (Lambda)     → /backend/CLAUDE.md
현재 할 일          → /plan.md         ← 매 세션 반드시 확인
개발 원칙/에이전트   → /docs/principles.md
화면 스펙 (IA)      → /docs/ia.md      ← 특정 화면 작업 시 참조
```

> IA 참조 방법: "docs/ia.md에서 AC-VID 관련 스펙 읽고 구현해줘"

---

## 6. 멀티 플랫폼 전환 프로토콜

```
전환 순서: Claude Code ↔ Cursor AI (Opus) ↔ Codex

전환 전 반드시:

  1. plan.md 업데이트 (완료/진행중/다음 할 것)
  2. 미완성 파일에 TODO 주석 삽입

새 플랫폼 세션 시작:
  CLAUDE.md → design.md → plan.md 읽기 → "현재 상태 요약해줘" 확인
```

**모델 선택**

```
일반 구현    : claude-sonnet-4-6
복잡한 설계  : claude-opus-4-6 (필요할 때만)
UI 빠른 생성 : Codex Sub-Agents
```

---

## 7. 코드 품질 원칙

```

- 작은 단위로 작업. 한 번에 전체 코드베이스 변경 금지.
- 의미있는 테스트만. 수치 채우기 금지.
- 이모지 금지. 슬롭 코드 금지.
- 막히면 "Do not work yet" 후 질문 먼저.
- 작업 완료 시 plan.md 업데이트.

```

<!-- GSD:project-start source:PROJECT.md -->

## Project

**Sunity AI Coach**

폴스포츠 수강생이 연습 영상을 올리면 AI가 프로 선수(정은지) 모션과 비교해 자세 교정 피드백을 주는 모바일 앱. 수강생은 학원에서 혼자 앱을 켜고 본인 영상을 올려 분석 결과와 점수를 확인한다. 현재 파일럿 MVP 단계로, 정은지 선수 시연 → 폴스포츠 학원 실증을 목표로 한다.

**Core Value:** **분석 정확도.** 점수가 믿을 만하고, 첫 분석이 "전문가 수준으로 구체적"이어야 한다. 고수가 낮게 나오는 위양성(정은지 영상 41점 같은) 없이 점수가 실제 자세 품질을 반영하고, 출력은 단순 수치가 아니라 "왜 안 되는지 + 무엇이 필요한지"를 제시해야 한다 (수치는 보조, 원인이 핵심). 현장 리서치 결론: AI가 일반적 답변만 하면 수강생은 이탈하고, 각도 수치만 보여주면 강사 철학과 충돌한다 — 분석 정확도가 곧 신뢰이고, 신뢰가 곧 도입이다. 트레이드오프가 생기면 분석 정확도를 우선한다 (비용 하한은 구독료 수준).

### Constraints

- **Tech stack**: 결정 완료, 변경 금지 — Expo+RN(TS) / Lambda(Python)+SAM / Firestore / S3 / YOLO11→NLF 3D→MotionDTW / Cerebras LLM / EAS Build. (CLAUDE.md §3)
- **인프라**: Motion AI는 반드시 별도 Lambda+S3. 기존 sunity.ai EC2에 얹지 말 것.
- **시크릿**: AWS Parameter Store 사용. `.env` 하드코딩 금지.
- **디자인**: 브랜드 컬러 #FF4B33 (변경 금지), Pretendard, 라이트 전용. UI는 Figma 우선(fileKey jrdI7kp245HkPfLB0nclsz), design.md는 보조.
- **GPU 의존**: NLF 3D는 CUDA 필수 (CPU에서 NaN). 실분석은 RunPod Pod에 위임. Pod 생명주기 수동 — 재생성 시 proxy URL 변경 → Lambda env 동기화 필요.
- **외부 의존**: Gemini 기술 인식기는 belle의 Gemini API 키(Google AI Studio) 필요 → Parameter Store/Pod env 주입.
- **품질 원칙**: 작은 단위 작업, 의미있는 테스트만, 이모지·슬롭 코드 금지. (CLAUDE.md §7)

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

- `/app` — React Native + Expo mobile app (TypeScript)
- `/backend` — AWS Lambda serverless API + analysis pipeline (Python, SAM)
- `/backend/runpod_inference` — GPU inference server (Python, FastAPI) deployed on RunPod
- `/ml` — Documentation only (`ml/ml_CLAUDE.md`). The actual ML code lives under `backend/shared/python/sunity_shared/analysis/`.

## Languages

- TypeScript (~5.9.2) - Mobile app under `app/src/` (React Native, strict mode)
- Python 3.12 - Lambda runtime (`backend/template.yaml` `Runtime: python3.12`); analysis core + handlers under `backend/`
- Python 3.x on GPU pod - RunPod inference server `backend/runpod_inference/server.py` (PyTorch base image)
- JavaScript (ESM `.mjs`) - Node admin scripts `app/scripts/seed-reference-motions.mjs`, `app/scripts/verify-firebase.mjs`

## Runtime

- Expo SDK ~54.0.33 (`app/package.json`)
- React 19.1.0 / React Native 0.81.5
- New Architecture enabled (`app/app.json` `newArchEnabled: true`)
- Expo Router ~6.0.23 (file-based routing, entry `expo-router/entry`)
- Python 3.12, ARM64 architecture (`backend/template.yaml` `Architectures: [arm64]`)
- Default function Timeout 15s / MemorySize 256MB; pipeline function 900s / 1024MB
- `boto3` provided by the Lambda runtime (not vendored in `requirements.txt`)
- PyTorch + CUDA base image (RunPod PyTorch 2.4 or similar; `torch`/`torchvision` supplied by base image, not pinned)
- Uvicorn single worker: `uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1`
- CUDA required — NLF model diverges to NaN on CPU (`backend/shared/python/sunity_shared/analysis/pose_estimator.py`)
- App: npm (lockfile `app/package-lock.json` expected; `package.json` `private: true`)
- Backend: pip via SAM build; per-function `requirements.txt` + dev `backend/requirements-dev.txt`
- No `.nvmrc` or `.python-version` files detected; Python version is pinned in `backend/template.yaml`.

## Frameworks

- `expo` ~54.0.33 - App framework
- `expo-router` ~6.0.23 - File-based navigation (`app/src/app/`)
- `react-native` 0.81.5 / `react` 19.1.0 - UI runtime
- `react-native-safe-area-context` ~5.6.0, `react-native-screens` ~4.16.0 - Navigation primitives
- `react-native-svg` 15.12.1 - Score gauge / chart rendering (`app/src/components/OctagonScore.tsx`, `GrowthChart.tsx`)
- `expo-image-picker` ~17.0.11 - Camera/gallery video selection
- `expo-video` ~3.0.16 - Result-screen video playback
- `expo-linear-gradient` ~15.0.8 - Home brand gradient
- `expo-linking` ~8.0.12, `expo-constants` ~18.0.13, `expo-status-bar` ~3.0.9
- `expo-updates` ~29.0.17 - OTA updates (channel-based, EAS)
- AWS SAM (`AWS::Serverless-2016-10-31`) - IaC, `backend/template.yaml`
- AWS HTTP API (`AWS::Serverless::HttpApi`) - 2 routes: `POST /upload-url`, `GET /reference`
- AWS SQS - async analysis queue (`AnalysisQueue` + `AnalysisDLQ`)
- Standard-library `urllib` for RunPod HTTP delegation (no `requests` dependency)
- FastAPI >=0.115,<1.0 - `backend/runpod_inference/server.py`
- Uvicorn[standard] >=0.30,<1.0 - ASGI server
- Pydantic >=2.5,<3.0 - request/response models
- pytest >=8,<9 (`backend/requirements-dev.txt`) - Backend unit tests under `backend/tests/`
- TypeScript `tsc --noEmit` (`npm run typecheck`) - App type checking (no JS test runner configured)
- EAS Build / EAS CLI >= 19.0.0 (`app/eas.json`) - App build & submit, channels development/preview/production
- SAM CLI (`backend/samconfig.toml`) - `sam build` / `sam deploy`, stack `sunity-motion-pilot`, region `ap-northeast-2`
- `sam build --use-container` required (Mac native binaries fail on Lambda Linux — see project memory)

## Key Dependencies

- `firebase` ^12.13.0 - JS SDK v12 modular API. Auth (anonymous + ID tokens) + Firestore client (`app/src/lib/firebase.ts`)
- `@react-native-async-storage/async-storage` 2.2.0 - Firebase Auth persistence backing store
- `firebase-admin` ^13.10.0 (devDependency) - Admin SDK for the reference-motion seed script only
- `firebase-admin` >=6,<7 - Firestore Admin + Firebase Auth ID-token verification (all 3 functions)
- `numpy` >=1.26,<2.0 (RunPod) / >=1.26,<3 (Lambda + dev) - Analysis algorithm core (DTW, joint angles, scoring)
- `ultralytics` >=8.2 - YOLO11n person bounding-box detection (`pose_estimator.py`)
- NLF (Neural Localizer Fields, NeurIPS'24) - 3D HMR model, TorchScript `backend/scripts/nlf_l_multi.torchscript`, downloaded from GitHub release in `setup.sh`
- `torch` / `torchvision` - Supplied by RunPod base image (not pinned); `torchvision` import required for TorchScript op registration
- `imageio` >=2.34 + `imageio-ffmpeg` >=0.5.1 - Frame extraction (`frame_extractor.py`, 9 fps / 640px downsample)
- Pillow (`PIL`) - Frame resize + YOLO image input
- `boto3` >=1.34,<2.0 - S3 download on the pod
- `cerebras.cloud.sdk` (Cerebras) - Korean coaching-sentence generation, model `llama3.1-8b` (`coach_writer.py`). Imported lazily; graceful no-op when key unset.
- `motiondtw.py` - Sakoe-Chiba band-constrained DTW (FastDTW approximation; interface allows swap to `fastdtw`)
- `features.py`, `temporal.py`, `kismam.py`, `dimensions.py`, `technique.py`, `segments.py`, `assemble.py`, `skeleton.py`

## Configuration

- `EXPO_PUBLIC_FIREBASE_API_KEY`, `_AUTH_DOMAIN`, `_PROJECT_ID`, `_STORAGE_BUCKET`, `_MESSAGING_SENDER_ID`, `_APP_ID` - Firebase web config (not secret; security enforced by Firestore rules)
- `EXPO_PUBLIC_API_BASE_URL` - SAM `ApiBaseUrl` output (e.g. `https://xxxx.execute-api.ap-northeast-2.amazonaws.com/pilot`)
- `EXPO_PUBLIC_` prefix vars are inlined at build time by Expo SDK 54.
- `app/app.json` - Expo config (bundle `com.sunity.aicoach`, owner `sunity3412`, EAS projectId `d2872ef6-...`, updates URL `https://u.expo.dev/d2872ef6-...`)
- `app/eas.json` - Build profiles + iOS submit config (appleId `sunity3412@gmail.com`, teamId `8ZL3YL358P`, ascAppId `6772934567`)
- `app/tsconfig.json` - Extends `expo/tsconfig.base`, `strict: true`
- `backend/template.yaml` - SAM template (functions, SQS, HTTP API, log groups w/ 30-day retention)
- `backend/samconfig.toml` - Deploy defaults (stack `sunity-motion-pilot`, region `ap-northeast-2`, `Stage=pilot`)
- Secrets live in AWS SSM Parameter Store (`/sunity/motion/firebase-sa`, `CEREBRAS_KEY_PARAM`) — never hardcoded. Lambda env vars: `VIDEO_BUCKET`, `FIREBASE_SA_PARAM`, `RUNPOD_ANALYZE_URL`, `RUNPOD_AUTH_TOKEN`.
- RunPod env vars: `RUNPOD_AUTH_TOKEN`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `FIREBASE_SA_JSON`/`FIREBASE_SA_PATH`, `CUDA_VISIBLE_DEVICES`, optional `NLF_MODEL_PATH`/`YOLO_WEIGHTS_PATH`.
- `firebase-sa.json`, `sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json` - Firebase Admin service-account keys
- `sunity-api_accessKeys.csv` - AWS access keys
- `.firebaserc` - Firebase project alias (`sunity-ai-coach`)
- `firestore.rules` - Firestore security rules

## Platform Requirements

- Node + npm (Expo SDK 54 / React Native 0.81) for `/app`
- Python 3.12 + SAM CLI + Docker Desktop (`sam build --use-container`) for `/backend`
- AWS account (region `ap-northeast-2`), Firebase project `sunity-ai-coach`
- iOS/Android via EAS Build; iOS submit to App Store Connect app `6772934567`
- Backend on AWS Lambda (ARM64) + API Gateway HTTP API + SQS, stack `sunity-motion-pilot`
- GPU inference on RunPod pod (CUDA GPU required; NLF model loaded into VRAM at startup)
- Video storage on S3 bucket `sunity-motion-pilot-videos` (created out-of-band, not by SAM template)

## Declared-but-Not-Yet-Implemented

- RevenueCat / `react-native-purchases` - No payment SDK in `app/package.json` (pilot intentionally has no billing)
- CloudFront - Not referenced; video delivery uses S3 presigned URLs directly
- `victory-native` / `react-native-gifted-charts` - Documented in `app/CLAUDE.md` but not installed; charts currently use `react-native-svg` directly
- ViTPose-S - Listed in `CLAUDE.md` 2D pipeline but superseded by NLF 3D backbone (see `pose_estimator.py` docstring)

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

- `/app` — React Native + Expo, TypeScript
- `/backend` — AWS Lambda (Python) + SAM; also the RunPod GPU server and the shared ML pipeline
- `/ml` — documentation only (`ml/ml_CLAUDE.md`). The actual ML code lives under `backend/shared/python/sunity_shared/analysis/`.

## TypeScript / React Native (`/app`)

### Naming Patterns

- Components: PascalCase — `src/components/OctagonScore.tsx`, `src/components/GrowthChart.tsx`, `src/components/VideoCompare.tsx`
- Library/data-source modules: camelCase — `src/lib/userAnalyses.ts`, `src/lib/referenceMotions.ts`, `src/lib/api.ts`, `src/lib/firebase.ts`
- Theme tokens: lowercase — `src/theme/colors.ts`, `src/theme/typography.ts`, `src/theme/index.ts`
- Expo Router screens: lowercase route names — `src/app/analysis/result.tsx`, `src/app/(tabs)/analyze.tsx`, `src/app/_layout.tsx`. Route groups in parens — `(tabs)`.
- Scripts: kebab-case `.mjs` — `scripts/seed-reference-motions.mjs`
- camelCase verbs — `requestUploadUrl`, `uploadToS3`, `pickFromCamera`, `routeAfterPick`, `validate`, `normalize`
- React hooks: `use` prefix — `useReferenceMotion`, `useMyAnalyses`, `useAnalysisDoc`
- Screen components default-exported as PascalCase — `export default function Analyze()`
- camelCase locals/state — `referenceMotionId`, `hasPreviousMode3`, `permissionBlocked`
- Module-level constants: SCREAMING_SNAKE_CASE — `MAX_BYTES`, `ALLOWED`, `API_BASE_URL`, `CONTENT_TYPE_BY_FORMAT`, `MAX_VIDEO_BYTES`
- PascalCase `interface`/`type` — `UploadUrlRequest`, `UploadUrlResponse`, `AnalysisDoc`, `UserAnalysesState`
- String-literal unions for closed sets — `type AnalysisMode = 'mode1' | 'mode3'`, `type VideoFormat = 'mp4' | 'mov'`, `AnalysisStatus`, `AnalysisErrorCode` (`src/types/analysis.ts`)
- Local helper types declared inline near use — `type Picked = {...}` in `analyze.tsx`

### Code Style

- No Prettier or ESLint config present in `/app` (no `.prettierrc`, `.eslintrc`, `eslint.config.*`). Style is enforced by convention/consistency, not tooling.
- Observed defaults: 2-space indent, single quotes for strings, semicolons, trailing commas in multiline literals.
- `as const` used pervasively for token objects to get literal types — `colors`, `gradients`, `radius`, `spacing`, `layout` in `src/theme/`.
- `tsconfig.json` extends `expo/tsconfig.base` with `"strict": true`.
- Run: `npm run typecheck` (`tsc --noEmit`). This is the only static gate.
- Prefer `import type { ... }` for type-only imports — `import type { AnalysisMode } from '../../types/analysis'`.

### Import Organization

### Error Handling

- User-facing errors are Korean strings stored in component state and rendered inline — `setError('mp4, mov 형식의 영상만 분석할 수 있어요.')` (`analyze.tsx`).
- Async pickers wrap in `try/catch/finally`; `finally` resets the `busy` flag. Bare `catch {}` (no binding) is acceptable when the error is converted to a friendly message.
- API client throws `Error` with a compact diagnostic (`${method} ${path} ${status}: ${text.slice(0,200)}`) — `src/lib/api.ts`.
- Network/config preconditions throw early with actionable Korean text — `throw new Error('EXPO_PUBLIC_API_BASE_URL 미설정. app/.env 확인.')`.
- Firestore data is defensively normalized: a `normalize()` function validates raw doc fields and returns `null` on malformed data rather than trusting types (`src/lib/userAnalyses.ts`).

### Logging

- No logging framework. Avoid `console.log` in committed code; surface state to the user instead.

### Comments

- Heavy use of Korean block comments at the top of files and above non-obvious logic explaining the **why** (e.g. the routing rationale in `analyze.tsx`, the Content-Type S3 gotcha in `api.ts`).
- Comments cite source-of-truth docs by section — `design.md §5-4`, `contract.md §2`, `belle P1 #7`. Match this when adding code.
- No JSDoc/TSDoc convention; prose comments are preferred.

### Function & Component Design

- Screens are single default-exported functions; small presentational helpers (e.g. `SourceCard`) defined as named functions in the same file with an inline prop type.
- Props typed inline via destructuring with an object type literal.
- `StyleSheet.create({...})` placed at the bottom of the file; styles reference theme tokens, never hardcoded values (brand color `#FF4B33`, radii, spacing all come from `src/theme/`). **Hardcoding colors/spacing is forbidden** (see `app/CLAUDE.md`).
- Accessibility props are expected on pressables — `accessibilityRole`, `accessibilityLabel`, `accessibilityState`, `hitSlop` (see `analyze.tsx`).

### Module Design

- Data-source modules are isolated so screens stay ignorant of the backend (Firestore `onSnapshot` today, swappable later). Pattern documented in `src/lib/userAnalyses.ts` and `src/lib/referenceMotions.ts`.
- Named exports for hooks/functions; default export reserved for screen components.
- No barrel files except `src/theme/index.ts` (re-exports color/typography tokens + defines radius/spacing/layout).

## Python (`/backend`, shared ML pipeline, RunPod server)

### Naming Patterns

- snake_case modules — `responses.py`, `validation.py`, `s3keys.py`, `firestore_admin.py`
- Lambda handlers all named `app.py` inside their function dir — `functions/upload-url/app.py`, `functions/pipeline/app.py`, `functions/reference-api/app.py`
- Shared library package: `backend/shared/python/sunity_shared/` (deployed as a Lambda Layer to `/opt/python`)
- ML analysis package: `sunity_shared/analysis/` — `dimensions.py`, `kismam.py`, `motiondtw.py`, `technique.py`, `temporal.py`, `features.py`, `segments.py`, `assemble.py`, `selfmotion.py`, `coach_writer.py`, `skeleton.py`
- snake_case — `validate_upload_request`, `build_upload_key`, `parse_json_body`, `line_score`, `stability_score`, `absolute_dimension_scores`
- Lambda entry point: `lambda_handler(event, _context)` (unused context prefixed `_`)
- Private/internal helpers prefixed with `_` — `_resp`, `_as_tj`, `_process`, `_load_pipeline_module`
- Module-level constants SCREAMING or `_`-prefixed for private — `MODES`, `VIDEO_FORMATS`, `ERR_UNSUPPORTED_FORMAT`, `MAX_VIDEO_BYTES`, `_CORS`, `_BUCKET`, `_EXPIRES`, `_LINE_TOL_DEG`
- Dimension/key string constants centralized so app and backend share literals — `DIM_ANGLE = "angle"`, `DIM_LINE = "line"` (`dimensions.py`)
- PascalCase — `ValidationError`, `UploadRequest`, `TechniqueProfile`
- Frozen dataclasses for value objects — `@dataclass(frozen=True) class UploadRequest` (`validation.py`)
- Custom exceptions carry structured fields (`code`, `message`, `http_status`) so handlers map them to API responses.

### Code Style

- No `pyproject.toml`, `setup.cfg`, `.flake8`, or formatter config committed. Style is by convention (PEP 8, 4-space indent).
- `from __future__ import annotations` at the top of nearly every module to enable modern type-hint syntax (`str | None`, `tuple[int, int]`).
- Type hints are expected on public function signatures and dataclass fields.
- `# noqa` used sparingly with a reason — `except Exception:  # noqa: BLE001 - 서명 실패는 서버 오류로 통일`.

### Import Organization

- Within the analysis package, relative imports are used (`from . import kismam`, `from .skeleton import JOINT_KEYS`).

### Error Handling

- API layer: a typed `ValidationError(code, message, http_status)` is raised by pure validators and caught in `lambda_handler`, then converted via `responses.error(e.code, e.message, status=e.http_status)`.
- Standard response envelope: success `responses.ok(payload)`, error `{ "error": { "code", "message" } }` (`responses.py`) — mirrors `docs/contract.md`.
- Auth failures raise `AuthError` (from `sunity_shared.auth`), mapped to HTTP 401.
- Broad `except Exception` is allowed only at boundaries (e.g. presigned-URL generation) where the error is logged with `log.exception(...)` and collapsed into a `server_error` 500.
- Input parsers are defensive and never crash on malformed input — `parse_json_body` returns `{}` on bad JSON; validators raise `ValidationError("bad_request", ...)`.
- Numeric/shape contracts are enforced explicitly — `_as_tj` raises `ValueError` if the angle matrix is not `(T, NUM_JOINTS)`.

### Logging

- Stdlib `logging` only. Pattern per handler: `log = logging.getLogger(); log.setLevel(logging.INFO)`.
- Log structured key=value context, not free text — `log.info("upload-url ok uid=%s analysis_id=%s mode=%s", uid, analysis_id, req.mode)`.
- Use `log.exception(...)` inside `except` to capture tracebacks. Never log secrets.

### Comments / Docstrings

- Every module opens with a `"""..."""` docstring stating purpose and citing the contract/section it satisfies (e.g. `contract.md §2`, `보고서 5·6`).
- Function docstrings explain the **why** and edge cases, often in Korean (e.g. the `hold_window` docstring in `dimensions.py`).
- Design-decision rationale lives in the module header (see the dated re-tuning note at the top of `dimensions.py`, the RunPod startup/auth rationale in `runpod_inference/server.py`).

### Function & Module Design

- Validation/scoring logic is written as **pure functions** with no AWS/network/boto3 dependency, so it is unit-testable without AWS — explicitly stated in `validation.py` (`순수 함수(boto3/네트워크 무관)`).
- Lambda handlers are thin: authenticate → validate → do one side-effect → respond. Business logic delegated to `sunity_shared`.
- The RunPod GPU server (`runpod_inference/server.py`, FastAPI + Pydantic) reuses the Lambda pipeline's `_process` so there is exactly one analysis code path ("분기 0, 코드 1벌").
- numpy is the numeric backbone of the analysis modules; arrays are shaped `(T, J)` time × joints (note: Firestore stores these flattened — nested arrays are forbidden).

## Cross-cutting

- **Single source of truth for the API contract:** `app/src/types/analysis.ts` (TS) and `backend/shared/python/sunity_shared/models.py` + `validation.py` (Python) intentionally mirror each other and `docs/contract.md`. Change all three together.
- **Korean for user-facing copy and most comments;** identifiers and code remain English.
- **No emojis anywhere in code or output** (`CLAUDE.md` §7).
- **Cite the spec** in comments using the project's section shorthand (`design.md §5-4`, `contract.md §2`, `belle P1/P2 #n`).

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

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

- **Contract-first:** `app/src/types/analysis.ts` and `backend/shared/.../models.py` mirror each other and `docs/contract.md`. Changing one requires changing all three.
- **No video through Lambda:** App PUTs video directly to S3 via presigned URL; S3 `ObjectCreated` → SQS → pipeline. Avoids Lambda payload/timeout limits.
- **Single pipeline, two runtimes:** `pipeline/app.py::_process` runs either on Lambda (CPU fallback, produces NaN without GPU) or RunPod GPU (operational). RunPod imports the Lambda module by path and reuses `_process` — zero branching.
- **Adapter boundary:** Algorithm core (`features`/`temporal`/`motiondtw`/`kismam`/`dimensions`/`assemble`) is pure and unit-tested; heavy deps (ffmpeg, torch/NLF, Cerebras) sit behind `Protocol`-typed adapters and are lazy-imported.
- **Live state via Firestore:** App never polls the backend; it subscribes to `users/{uid}/analyses/{id}` with `onSnapshot` and reacts to status transitions.

## Layers

- Purpose: Render screens, handle navigation and video picking
- Location: `app/src/app/` (file-based routing via expo-router)
- Contains: Screen components, the analysis flow (`analysis/`), bottom tabs (`(tabs)/`)
- Depends on: `app/src/lib/` hooks + client, `app/src/theme/` tokens, `app/src/types/`
- Used by: expo-router (entry `expo-router/entry`)
- Purpose: Isolate screens from data source (Firestore today, REST later)
- Location: `app/src/lib/`
- Contains: Firestore subscription hooks (`useMyAnalyses`, `useAnalysisDoc`, `useReferenceMotion`), HTTP client (`api.ts`), Firebase init (`firebase.ts`)
- Depends on: `firebase` SDK, `EXPO_PUBLIC_*` env
- Used by: Screen components
- Purpose: Synchronous app-facing endpoints
- Location: `backend/functions/upload-url/`, `backend/functions/reference-api/`
- Contains: Two HTTP API Lambdas (auth → validate → respond)
- Depends on: `sunity_shared` (auth, responses, validation, s3keys, firestore_admin)
- Used by: App `api.ts`
- Purpose: Run analysis off the request path
- Location: `backend/functions/pipeline/`
- Contains: SQS consumer; orchestration + RunPod delegation
- Depends on: `sunity_shared.analysis.*`, `firestore_admin`, S3, optional RunPod HTTP
- Used by: SQS (triggered by S3 ObjectCreated)
- Purpose: Model-agnostic scoring math
- Location: `backend/shared/python/sunity_shared/analysis/`
- Contains: `features`, `temporal`, `motiondtw`, `kismam`, `dimensions`, `segments`, `technique`, `skeleton`, `selfmotion`, `assemble`
- Depends on: numpy only (pure)
- Used by: pipeline `_process`
- Purpose: Bridge core to heavy/external dependencies
- Location: `backend/shared/.../analysis/{frame_extractor,pose_estimator,coach_writer}.py`, contracts in `interfaces.py`
- Contains: `FrameExtractor` (ffmpeg), `PoseEstimator` (NLF 3D), `CoachWriter` (Cerebras LLM)
- Depends on: imageio/ffmpeg, torch/NLF, requests
- Used by: pipeline `_process` (lazy-imported in `_ensure_adapters()`)

## Data Flow

### Primary Analysis Path (Mode 1 / Mode 3)

### Reference Motion Listing (Mode 1 selection)

- Auth + analysis state lives in Firestore; app holds it via React hooks (`useState` + `onSnapshot`). No global app store (no Redux/Zustand).
- Backend has no shared mutable state across invocations except cached singletons (Firestore client, ML adapters, RunPod pipeline module).

## Key Abstractions

- Purpose: Single shared shape between app, backend, ML
- Examples: `app/src/types/analysis.ts`, `backend/shared/.../models.py`, `docs/contract.md`
- Pattern: Manual mirror — comments in each file mandate co-editing
- Purpose: Decouple screens from the backing store so it can be swapped without touching UI
- Examples: `app/src/lib/userAnalyses.ts`, `app/src/lib/referenceMotions.ts`
- Pattern: `useXxx()` returns `{ data, loading, error }`; internals subscribe to Firestore
- Purpose: Pluggable heavy/external dependencies behind the algorithm core
- Examples: `backend/shared/.../analysis/interfaces.py` (`FrameExtractor`, `PoseEstimator`, `CoachWriter`)
- Pattern: `typing.Protocol`; concrete adapters live as sibling modules; lazy instantiated
- Purpose: IPSF scoring is technique-conditional (a bent knee can be correct or a fault depending on the move). Recognizer supplies which joints must extend
- Examples: `backend/shared/.../analysis/technique.py` (`FallbackRecognizer` today; Gemini/Pole-arina adapter planned)
- Pattern: swappable recognizer; scoring layer (`dimensions.py`) depends only on the profile
- Purpose: Reconstruct uid/analysisId from the upload key, no DB lookup needed at trigger time
- Examples: `backend/shared/.../s3keys.py` — `uploads/{uid}/{analysisId}.{ext}`
- Pattern: build + regex-parse pair

## Entry Points

- Location: `expo-router/entry` (package.json `main`), root layout `app/src/app/_layout.tsx`, intro `app/src/app/index.tsx`
- Triggers: App launch
- Responsibilities: Light-theme status bar, headerless stack; intro does anonymous Firebase sign-in then routes to `(tabs)`
- Location: `backend/functions/upload-url/app.py::lambda_handler`, `backend/functions/reference-api/app.py::lambda_handler`
- Triggers: API Gateway HTTP API (`POST /upload-url`, `GET /reference`)
- Responsibilities: Firebase token auth → validate → S3/Firestore action → JSON response
- Location: `backend/functions/pipeline/app.py::lambda_handler`
- Triggers: SQS (S3 ObjectCreated upstream)
- Responsibilities: Per-message dispatch to RunPod delegate or local `_process`
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

### Editing one side of the data contract only

### Routing video bytes through Lambda

### Calling ML adapters in the RunPod-delegate path

### Hardcoding theme values

## Error Handling

- Pipeline catches `NoHumanError` → `no_human`, `NotPoleMotionError` → `not_pole_motion`, anything else → `server_error`, via `firestore_admin.fail_analysis` (`backend/functions/pipeline/app.py:342`, mirrored in `runpod_inference/server.py:105`).
- HTTP Lambdas return `responses.error(code, msg, status)`; `AuthError` → 401, `ValidationError` → its `http_status`.
- App layers errors: local upload error > Firestore doc error > default (`app/src/app/analysis/loading.tsx:303`). Hook subscription errors degrade gracefully to empty state.
- `not_pole_motion` is a safety gate (Mode 1): if KISMAM similarity < `NOT_POLE_SIMILARITY_THRESHOLD`, analysis fails rather than showing a meaningless score.

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->
## RTK 프로젝트 예외 (Sunity)

- `gsd-sdk` / `node .claude/get-shit-done/bin/gsd-tools.cjs` 호출은 **rtk로 감싸지 말 것** — JSON 출력을 오케스트레이터가 파싱하므로 원문 필요.
- 그 외 git/pytest/tsc/grep/ls 등 관찰용 커맨드는 rtk 접두 사용.
