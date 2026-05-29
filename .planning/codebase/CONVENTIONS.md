# Coding Conventions

**Analysis Date:** 2026-05-29

This is a multi-component monorepo (Sunity AI Coach). Conventions differ by component:

- `/app` — React Native + Expo, TypeScript
- `/backend` — AWS Lambda (Python) + SAM; also the RunPod GPU server and the shared ML pipeline
- `/ml` — documentation only (`ml/ml_CLAUDE.md`). The actual ML code lives under `backend/shared/python/sunity_shared/analysis/`.

Project-wide rules (from `CLAUDE.md`): **no emojis, no slop code**, small focused changes, meaningful tests only.

---

## TypeScript / React Native (`/app`)

### Naming Patterns

**Files:**
- Components: PascalCase — `src/components/OctagonScore.tsx`, `src/components/GrowthChart.tsx`, `src/components/VideoCompare.tsx`
- Library/data-source modules: camelCase — `src/lib/userAnalyses.ts`, `src/lib/referenceMotions.ts`, `src/lib/api.ts`, `src/lib/firebase.ts`
- Theme tokens: lowercase — `src/theme/colors.ts`, `src/theme/typography.ts`, `src/theme/index.ts`
- Expo Router screens: lowercase route names — `src/app/analysis/result.tsx`, `src/app/(tabs)/analyze.tsx`, `src/app/_layout.tsx`. Route groups in parens — `(tabs)`.
- Scripts: kebab-case `.mjs` — `scripts/seed-reference-motions.mjs`

**Functions:**
- camelCase verbs — `requestUploadUrl`, `uploadToS3`, `pickFromCamera`, `routeAfterPick`, `validate`, `normalize`
- React hooks: `use` prefix — `useReferenceMotion`, `useMyAnalyses`, `useAnalysisDoc`
- Screen components default-exported as PascalCase — `export default function Analyze()`

**Variables:**
- camelCase locals/state — `referenceMotionId`, `hasPreviousMode3`, `permissionBlocked`
- Module-level constants: SCREAMING_SNAKE_CASE — `MAX_BYTES`, `ALLOWED`, `API_BASE_URL`, `CONTENT_TYPE_BY_FORMAT`, `MAX_VIDEO_BYTES`

**Types:**
- PascalCase `interface`/`type` — `UploadUrlRequest`, `UploadUrlResponse`, `AnalysisDoc`, `UserAnalysesState`
- String-literal unions for closed sets — `type AnalysisMode = 'mode1' | 'mode3'`, `type VideoFormat = 'mp4' | 'mov'`, `AnalysisStatus`, `AnalysisErrorCode` (`src/types/analysis.ts`)
- Local helper types declared inline near use — `type Picked = {...}` in `analyze.tsx`

### Code Style

**Formatting:**
- No Prettier or ESLint config present in `/app` (no `.prettierrc`, `.eslintrc`, `eslint.config.*`). Style is enforced by convention/consistency, not tooling.
- Observed defaults: 2-space indent, single quotes for strings, semicolons, trailing commas in multiline literals.
- `as const` used pervasively for token objects to get literal types — `colors`, `gradients`, `radius`, `spacing`, `layout` in `src/theme/`.

**Type checking:**
- `tsconfig.json` extends `expo/tsconfig.base` with `"strict": true`.
- Run: `npm run typecheck` (`tsc --noEmit`). This is the only static gate.
- Prefer `import type { ... }` for type-only imports — `import type { AnalysisMode } from '../../types/analysis'`.

### Import Organization

Observed order (e.g. `src/app/(tabs)/analyze.tsx`, `src/lib/userAnalyses.ts`):
1. Third-party / Expo / React Native packages (`@expo/vector-icons`, `expo-*`, `react`, `react-native`, `firebase/*`)
2. Local lib/hooks (`../../lib/referenceMotions`)
3. Local type imports last, via `import type` (`../../types/analysis`)
4. Theme tokens (`../../theme`)

**Path aliases:** None configured. Relative imports only (`../../lib/...`).

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

---

## Python (`/backend`, shared ML pipeline, RunPod server)

### Naming Patterns

**Files:**
- snake_case modules — `responses.py`, `validation.py`, `s3keys.py`, `firestore_admin.py`
- Lambda handlers all named `app.py` inside their function dir — `functions/upload-url/app.py`, `functions/pipeline/app.py`, `functions/reference-api/app.py`
- Shared library package: `backend/shared/python/sunity_shared/` (deployed as a Lambda Layer to `/opt/python`)
- ML analysis package: `sunity_shared/analysis/` — `dimensions.py`, `kismam.py`, `motiondtw.py`, `technique.py`, `temporal.py`, `features.py`, `segments.py`, `assemble.py`, `selfmotion.py`, `coach_writer.py`, `skeleton.py`

**Functions:**
- snake_case — `validate_upload_request`, `build_upload_key`, `parse_json_body`, `line_score`, `stability_score`, `absolute_dimension_scores`
- Lambda entry point: `lambda_handler(event, _context)` (unused context prefixed `_`)
- Private/internal helpers prefixed with `_` — `_resp`, `_as_tj`, `_process`, `_load_pipeline_module`

**Variables / constants:**
- Module-level constants SCREAMING or `_`-prefixed for private — `MODES`, `VIDEO_FORMATS`, `ERR_UNSUPPORTED_FORMAT`, `MAX_VIDEO_BYTES`, `_CORS`, `_BUCKET`, `_EXPIRES`, `_LINE_TOL_DEG`
- Dimension/key string constants centralized so app and backend share literals — `DIM_ANGLE = "angle"`, `DIM_LINE = "line"` (`dimensions.py`)

**Types/classes:**
- PascalCase — `ValidationError`, `UploadRequest`, `TechniqueProfile`
- Frozen dataclasses for value objects — `@dataclass(frozen=True) class UploadRequest` (`validation.py`)
- Custom exceptions carry structured fields (`code`, `message`, `http_status`) so handlers map them to API responses.

### Code Style

**Formatting:**
- No `pyproject.toml`, `setup.cfg`, `.flake8`, or formatter config committed. Style is by convention (PEP 8, 4-space indent).
- `from __future__ import annotations` at the top of nearly every module to enable modern type-hint syntax (`str | None`, `tuple[int, int]`).
- Type hints are expected on public function signatures and dataclass fields.
- `# noqa` used sparingly with a reason — `except Exception:  # noqa: BLE001 - 서명 실패는 서버 오류로 통일`.

### Import Organization

Observed order (e.g. `functions/upload-url/app.py`):
1. `from __future__ import annotations`
2. Stdlib (`json`, `logging`, `os`, `uuid`)
3. Third-party (`boto3`, `numpy`, `fastapi`, `pydantic`)
4. First-party `sunity_shared.*` imports
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

---

## Cross-cutting

- **Single source of truth for the API contract:** `app/src/types/analysis.ts` (TS) and `backend/shared/python/sunity_shared/models.py` + `validation.py` (Python) intentionally mirror each other and `docs/contract.md`. Change all three together.
- **Korean for user-facing copy and most comments;** identifiers and code remain English.
- **No emojis anywhere in code or output** (`CLAUDE.md` §7).
- **Cite the spec** in comments using the project's section shorthand (`design.md §5-4`, `contract.md §2`, `belle P1/P2 #n`).

---

*Convention analysis: 2026-05-29*
