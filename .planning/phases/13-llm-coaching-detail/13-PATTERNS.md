# Phase 13: 보완 운동 추천 + LLM 분기 카피 + coaching detail 완성 - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 12 (Plan A: 6 / Plan B: 6, some shared)
**Analogs found:** 12 / 12 (every new file maps to an in-repo, production-exercised analog — zero greenfield infra per RESEARCH §Summary)

> **Direct-review supersession (see 13-REVIEW-FIXES.md).** 본 문서의 "Branch baseline copy" 섹션은 단일 `is_registered` boolean / derived map 가정으로 작성되었으나 2·3차 리뷰로 뒤집혔다. 충돌 시 우선순위: 13-REVIEW-FIXES.md > plan `<action>` > 본 문서. 실 라우팅 = `lookup_motion_branch(motion_id) -> MotionBranchInfo`(frozen dataclass; `copyBranch` + `angleSource` + `angleFixtureKey` 직교). 아래 `is_registered is True/False/None` 분기·`derive ipsf_code` 표현은 **superseded**.

> All file access in this map is read-only. The only file written is this PATTERNS.md.
> Honors: D-05 (BodyProfile/painAreas → mapping+coaching ONLY, never scoring), 3-way contract lockstep (analysis.ts ↔ models.py ↔ contract.md atomic), light theme + #FF4B33 + theme tokens only (no hardcoded values).

## File Classification

### Plan A — 보완 운동 (criteria 1-4, no GPU)

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/data/corrective_exercises.json` (NEW) | config / fixture | transform (static lookup) | `backend/data/aka-mapping.json` | exact |
| `backend/shared/python/sunity_shared/analysis/exercise_map.py` (NEW) | service (ML core, pure fn) | transform | `backend/shared/.../analysis/force_pattern.py` (+ fixture loader from `force_signals.py`) | role-match (pure fn over findings) |
| `backend/shared/python/sunity_shared/firestore_admin.py` (MODIFY: `_validate_recommended_exercises` + complete_analysis wiring) | middleware (validator) | request-response (write guard) | `_validate_force_pattern_inference` (firestore_admin.py:343) | exact |
| `app/src/types/analysis.ts` (MODIFY: `RecommendedExercise` + `recommendedExercises?` field) | model (contract) | request-response | `CoachingTipDetail` / `DimensionExplanation` interfaces (analysis.ts:188, 239) | exact |
| `backend/shared/python/sunity_shared/models.py` + `docs/contract.md §4` (MODIFY: contract mirror) | model (contract) | request-response | BodyProfile 3-way lockstep block (models.py:37) | exact |
| `app/src/lib/userAnalyses.ts` (MODIFY: `recommendedExercises` null-guard in `normalize()`) | utility (data-source) | event-driven (onSnapshot) | forcePatternInference null-guard (userAnalyses.ts:90-110) | exact |
| `app/src/components/RecommendedExerciseModal.tsx` (NEW) | component (modal) | event-driven (UI) | `app/src/components/CoachingTipDetailModal.tsx` | exact |
| `app/src/app/analysis/result.tsx` (MODIFY: "보완 운동" section + modal mount) | component (screen) | event-driven | "코칭 팁" section + `CoachingTipDetailModal` mount (result.tsx:854, 949) | exact |
| `backend/functions/pipeline/app.py` (MODIFY: `map_exercises(...)` call + thread into build_result) | service (orchestrator) | event-driven (SQS) | force_pattern_inference wiring (app.py:1920-1950) | exact |

### Plan B — LLM 분기 카피 + coaching detail (criteria 5-8)

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/data/motion_ipsf_map.json` (NEW) | config / fixture | transform (static lookup) | `backend/data/reference-motions-branch2.json` + `aka-mapping.json` | exact |
| `backend/shared/python/sunity_shared/analysis/assemble.py` (MODIFY: `branch_info: MotionBranchInfo \| None` kwarg via `lookup_motion_branch` + `copyBranch` branch copy; `ipsf_code`/`is_registered` boolean superseded — see 13-REVIEW-FIXES.md) | service (assembler) | transform | `build_dimension_explanation` self (assemble.py:63) — extend mode-aware → branch-aware | exact |
| `backend/shared/python/sunity_shared/analysis/coach_writer.py` (MODIFY: `_build_prompt` signature + `_SYSTEM` guard + angle fixture inject) | adapter (LLM) | request-response (LLM call) | `coach_writer.py::_build_prompt` self (coach_writer.py:49) | exact |
| Pod/Lambda env `CEREBRAS_KEY_PARAM` + SSM SecureString (OPS, no code) | config | secret | `_load_api_key()` pattern (coach_writer.py:33) + auth.py FIREBASE_SA_PARAM | exact |

## Pattern Assignments

### `backend/data/corrective_exercises.json` (fixture, transform)

**Analog:** `backend/data/aka-mapping.json`

**Header + entries pattern** (aka-mapping.json:1-9) — copy the metadata header convention exactly:
```jsonc
{
  "schemaVersion": "1.0.0",
  "lastUpdated": "2026-06-16",
  "sourceNotebook": "e688fb4e-a4fb-4e83-a168-9c4726a98e09",
  "sourceNotebookName": "폴스포츠에 대한 지식",
  "defects": { ... },   // RESEARCH §B "Defect → exercises" table (5 keys, ≥5 each)
  "painAreas": { ... }  // RESEARCH §B "painArea → safe-reinforce" table (8 keys = PAIN_AREAS frozenset)
}
```
- Per-exercise object carries `sourceRef` citing `NotebookLM e688fb4e [n]` — mirror the `sourceRef` field already used on every aka-mapping entry (aka-mapping.json:15). Content verbatim from RESEARCH §NotebookLM B.
- Recommended schema is in RESEARCH §"Plan A — Storage Decision". `painAreas` keys MUST be the 8-member `PAIN_AREAS` frozenset (models.py:51-60), `defects` keys MUST be the 5 keys from RESEARCH §B (`grip_weak`/`shoulder_unstable`/`core_weak`/`legs_not_extended`/`hip_hamstring_tight`).

---

### `backend/shared/.../analysis/exercise_map.py` (service, pure fn — NEW)

**Analog:** `force_pattern.py` (pure-fn module conventions) + `force_signals.py` fixture loader.

**Module header pattern** (force_pattern.py:1-15) — open with docstring stating purity + 3-way lockstep + `from __future__ import annotations`:
```python
"""...
Pure function + numpy-free + AWS-free (Layer 2 / boto3 영구 차단).
3-way contract lockstep: analysis.ts ↔ models.py ↔ docs/contract.md §4.
"""
from __future__ import annotations
```

**Fixture loader pattern** — copy the lazy repo-root path + cache from `force_signals.py:229-235` (NOT a network/Firestore read):
```python
_CORRECTIVE_EXERCISES_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "data" / "corrective_exercises.json"   # NOTE: backend/data/, not judging_data/
)
_CORRECTIVE_EXERCISES_CACHE: dict | None = None
```
(force_signals loads from `judging_data/`; for `backend/data/*.json` the same `parent.parent...` chain resolves to `backend/`, then `/ "data"`.)

**Frozenset validators + dedup/cap pattern** — mirror force_pattern.py `_FORCE_SOURCE_SIGNALS` frozenset (force_pattern.py:84) and the Top-3 ranking idea (`_rank_top3` cited in RESEARCH Pitfall 4): cap output at 3~5, dedup, painArea-avoid lines prioritized.

**Signature** (RESEARCH §"Plan A — Exercise mapping function"):
```python
def map_exercises(
    force_pattern_inference: dict | None,  # result.forcePatternInference (camelCase findings[])
    pain_areas: list[str],                  # bodyProfile.painAreas (PAIN_AREAS frozenset)
    motion_id: str | None,                  # technique_profile.motion_id (optional gating)
) -> list[dict]:
    ...
```
**Input field shape** (force_pattern.py finding dict, RESEARCH §Code Examples): each finding is camelCase `{pattern, phase, sourceSignal, reason, interpretation, confidence, jointHint, warnings}`. Join `sourceSignal` + `jointHint` → defect key; `painAreas[]` → painArea key.

**D-05 guard:** this fn may read `painAreas` but the result feeds ONLY mapping output — never `dimension_scores`. Add a grep-gate test (RESEARCH §Anti-Patterns + §Wave 0 Gaps).

---

### `firestore_admin._validate_recommended_exercises` (middleware, write guard — NEW + wire)

**Analog:** `_validate_force_pattern_inference` (firestore_admin.py:343-404)

**Validator pattern** (firestore_admin.py:343-401) — 1:1 mirror: scoped validator that whitelists ONLY the expected list-of-dict shape, rejects nested dict / unexpected lists, preserves the global nested-array ban (`_validate_dict_only_scalars` body unchanged):
```python
def _validate_recommended_exercises(payload, *, path="recommendedExercises") -> None:
    if payload is None:
        return
    if not isinstance(payload, list):   # recommendedExercises is list[dict]
        raise ValueError(...)
    if len(payload) > 5:                # criteria 2 cap (mirror findings len > 3 guard at :390)
        raise ValueError(...)
    for i, item in enumerate(payload):
        _validate_dict_only_scalars(item, path=f"{path}[{i}]")  # each exercise = flat scalars
```

**Wiring** (firestore_admin.py:751-756) — mirror the `force_pattern_inference is not None` block: gate on `recommended_exercises is not None`, call the scoped validator, then assign `payload["result"]["recommendedExercises"] = ...`. Add `recommended_exercises` param to `complete_analysis(...)` signature.

> Decide: if each exercise object is purely scalar (name/setsReps/purpose/sourceRef strings), `_validate_dict_only_scalars` per item suffices — no new whitelist needed for list[str] sub-fields. If any exercise carries a list, copy the `findings`-style key whitelist (firestore_admin.py:389-397).

---

### `app/src/types/analysis.ts` (model — RecommendedExercise + field)

**Analog:** `CoachingTipDetail` / `CoachingCause` interfaces (analysis.ts:188-202) + `dimensionExplanation?` optional-field convention (analysis.ts:301).

**New interface** (mirror CoachingCause shape + the per-interface Korean comment-block + Phase tag convention at analysis.ts:184-202):
```typescript
// Phase 13 (2026-06-16): 보완 운동 추천 (PERS-03). 결함/통증부위 → 큐레이션 매핑.
// source: backend exercise_map.map_exercises (corrective_exercises.json fixture).
export interface RecommendedExercise {
  name: string;
  setsReps: string;
  purpose: string;
  sourceRef?: string;
}
```

**New field on AnalysisResult** (mirror `dimensionExplanation?` optional pattern at analysis.ts:299-301 — optional for backward-compat with old docs):
```typescript
  recommendedExercises?: RecommendedExercise[]; // Phase 13 — optional (이전 빌드 doc 호환)
```

---

### `models.py` + `docs/contract.md §4` (model — contract mirror)

**Analog:** BodyProfile 3-way lockstep block (models.py:37-41) + `dimensionExplanation` entry in contract.md §4 (contract.md:163, 180-195).

**Lockstep co-edit mandate** (models.py:37-41) — the exact comment that names all three files and demands simultaneous edit. Replicate this header for the new `recommendedExercises` shape. `docs/contract.md §4` (contract.md:157-169) is where `recommendedExercises RecommendedExercise[] optional ← Phase 13` line goes, plus a `RecommendedExercise` shape block modeled on the `DimensionExplanation` block at contract.md:180-191.

> models.py side: `recommendedExercises` is produced by the pure `exercise_map` module and validated in firestore_admin, so models.py needs only the contract-comment + any frozenset of allowed keys if a normalizer is added. There is no per-user write path (fixture is static), so NO `normalize_recommended_exercises` is required unless the planner wants defensive parity with `normalize_body_profile` (models.py:89).

---

### `app/src/lib/userAnalyses.ts` (utility — null-guard)

**Analog:** forcePatternInference null-guard (userAnalyses.ts:90-110)

**Pattern** (userAnalyses.ts:97-110) — copy the `if (result?.X) { ... }` defensive shape so old docs lacking the field degrade to undefined:
```typescript
// Phase 13 recommendedExercises null-guard — mirrors forcePatternInference (lines 97-110).
if (Array.isArray(result?.recommendedExercises)) {
  normalizedResult.recommendedExercises = result.recommendedExercises;
}
```
The TS interface keeps the field optional (`?`) so `normalize()` is the compat layer (per the comment at userAnalyses.ts:52).

---

### `app/src/components/RecommendedExerciseModal.tsx` (component — NEW)

**Analog:** `CoachingTipDetailModal.tsx` (whole file — the documented backdrop/gesture fix)

**Bottom-sheet pattern** (CoachingTipDetailModal.tsx:37-95) — copy the entire Modal scaffold: `transparent` + `animationType="slide"`, `backdrop` View with `backdropTop` Pressable (tap=close) and a pure-View `sheet` so ScrollView gestures aren't intercepted. THIS IS THE LOAD-BEARING GOTCHA (comment at CoachingTipDetailModal.tsx:44-47):
```tsx
<View style={styles.backdrop}>
  <Pressable style={styles.backdropTop} onPress={onClose} />
  <View style={[styles.sheet, { height: sheetHeight }]}>  {/* useWindowDimensions, not maxHeight */}
    ...<ScrollView style={styles.scroll}>...
```

**Theme tokens** (CoachingTipDetailModal.tsx:20, 135-283) — import `{ colors, radius }` from `'../theme'`; use `colors.brand` (#FF4B33), `colors.divider`, `radius.card`, `radius.button`. NO hardcoded brand color/spacing (app/CLAUDE.md). Card list maps over exercises mirroring the `causeCard` map (CoachingTipDetailModal.tsx:107-121). The "다른 운동 보기" full-library browse (criteria 4) is the modal content; section card shows the 3~5 matched, modal shows the broader library.

---

### `app/src/app/analysis/result.tsx` (screen — section + mount)

**Analog:** "코칭 팁" section + `CoachingTipDetailModal` mount (result.tsx:851-933, 948-955)

**Section insert point** (RESEARCH §"Plan A — result.tsx attachment"): after "코칭 팁" section (renders through result.tsx:933, before the closing `</ScrollView>`). Section order: 동작 비교(712) → 실패 원인 후보(775) → 구간별 점수(806) → 세부 점수(828) → 코칭 팁(854) → **[NEW] 보완 운동**.

**Section header pattern** (result.tsx:854): `<Text style={styles.sectionTitle}>보완 운동</Text>` then a card list of `result.recommendedExercises` + a "다른 운동 보기" Pressable (mirror the "자세히 ›" Pressable at result.tsx:905-913).

**Modal mount + state pattern** (result.tsx:508-511 state + 949-955 mount): add `const [exerciseModalOpen, setExerciseModalOpen] = useState(false)` mirroring the `detailDim`/tip modal state, mount `<RecommendedExerciseModal visible={...} onClose={...} />` next to the existing modals (result.tsx:937-960).

**Theme import already present** (result.tsx:60): `import { colors, layout, radius, spacing, typography } from '../../theme'` — reuse, do not add hardcoded values.

---

### `backend/functions/pipeline/app.py` (orchestrator — map_exercises wiring)

**Analog:** force_pattern_inference wiring (app.py:1920-1950) + build_result call site (app.py:1862-1876)

**Wiring point** (RESEARCH §"Plan A — Exercise mapping function" "When"): right after `force_pattern_inference_dict` is built (app.py:1948), call:
```python
recommended_exercises = exercise_map.map_exercises(
    force_pattern_inference_dict,
    pain_areas=(body_profile_snapshot or {}).get("painAreas", []),
    motion_id=getattr(profile, "motion_id", None),
)
```
Then thread `recommended_exercises` into the `complete_analysis(...)` write (the call that persists `result.forcePatternInference` — mirror app.py:1948-1950 → firestore_admin payload). It is a plain `list[dict]` (already camelCase), so NO `_dataclass_to_camel_case_dict` pass needed (unlike force_signals at app.py:1909).

> `body_profile_snapshot` already flows through `_process` (it is the snapshot read for the analysis doc). Confirm its variable name at wiring time; painAreas is the ONLY field consumed (D-05 — never weightKg into scoring).

---

### `assemble.build_dimension_explanation` (assembler — ipsfCode branch)

**Analog:** `build_dimension_explanation` itself (assemble.py:63-130) — the mode-aware baseline machinery is the template; add a branch layer above it.

**Backward-compatible kwarg pattern** (assemble.py:63-69, exactly how `joint_angles`/`profile` were added in 12.5) — append new kwargs defaulting to None so existing callers and old behavior are unchanged:
```python
def build_dimension_explanation(
    assessments, dimension_scores, comparison,
    joint_angles=None, profile=None,
    branch_info: "MotionBranchInfo | None" = None,  # NEW (frozen dataclass — SUPERSEDES ipsf_code/is_registered)
) -> dict[str, dict]:
```

**Branch baseline copy** — extend the `_DIMENSION_BASELINES_MODE1/MODE3` selection (assemble.py:32-41, 98-99). Branch on `branch_info.copyBranch`:
- `copyBranch == "branch1_ipsf_registered"` → "세계 심사 기준 (IPSF)" — 단 "180°" 는 **angle 차원이 아니라 line/EXTEND 관절 전용** (3차 HIGH-1/2차 HIGH-3). angle 차원 baseline = 동작별 정의 각도(NON-180).
- `copyBranch == "branch2_eunji_reference"` → "정은지 선수 기준 자세" — NEVER "세계 심사 기준" (criteria 6 + 8). 측정 각도는 `angleSource=eunji_measured_yaml` → `criteria/{angleFixtureKey}.yaml`.
- `branch_info is None` (motion_id 미인식 / FallbackRecognizer) → existing mode-aware baseline (assemble.py:99) = backward compat.

**branch_info resolution** — at the assemble.py call site (or a small helper), `lookup_motion_branch(profile.motion_id)` loads the **curated** `motion_ipsf_map.json` (NOT derived) and returns `MotionBranchInfo`. `angleSource` (`ipsf_registered_fixture | eunji_measured_yaml | no_angle_criterion`) selects the angle fixture independently of `copyBranch`. Do NOT add `ipsf_code`/branch fields to the TechniqueProfile scoring path (objectivity / D-05).

**criteria-8 grep gate:** add a forbidden-phrase test (precedent `FORBIDDEN_PHRASES_PHASE9_REGEX`, RESEARCH §Wave 0 Gaps) asserting branch-2 copy never contains "세계 심사 기준" / "180°".

---

### `coach_writer._build_prompt` + `_SYSTEM` (LLM adapter — angle fixture inject)

**Analog:** `coach_writer.py::_build_prompt` (coach_writer.py:49-86) + `_SYSTEM` (coach_writer.py:18-30)

**Signature extension** (coach_writer.py:49) — add `motion_name`, `branch`, `angle_fixture` so the LLM cites correct degrees (criteria 7). The existing `joints` line-builder (coach_writer.py:69-74) stays; prepend the per-move IPSF/measured angles:
```python
def _build_prompt(joints: list[dict], motion_name: str | None = None,
                  branch: str | None = None, angle_fixture: dict | None = None) -> str:
```
- branch-1 (registered) angles from RESEARCH §NotebookLM A table; branch-2 angles from the on-disk criteria yaml (already validated).
- `_SYSTEM` (coach_writer.py:18) gets ONE added line: "정확한 기준 각도만 인용, 임의 수치 생성 금지" (RESEARCH §"Plan B — IPSF angle fixture").

**Caller threading** — `context` dict already carries `mode`/`joints` (coach_writer.py:117, app.py:750). Add `motion_name`/`branch`/`angle_fixture` to the `coach_context` built before `_COACH_WRITER.write(...)` (app.py:1852/1860). `write()` (coach_writer.py:107-143) passes `context` to `_build_prompt` — extend that call.

**No activation code change** (coach_writer.py:33-46, 89-105): real Cerebras = OPS only (SSM param + `CEREBRAS_KEY_PARAM` on Pod + uvicorn restart). The graceful no-op (`self._client is None` → `{}` → assemble numeric fallback) is the correct unset behavior.

---

### Cerebras activation (OPS — no code)

**Analog:** `_load_api_key()` (coach_writer.py:33-46) — the SSM-param-by-env pattern (mirrors auth.py `FIREBASE_SA_PARAM`).

**Steps** (RESEARCH §"Plan B — Real Cerebras activation path", criteria 5 — the ONLY Pod-dependent item):
1. SSM SecureString (e.g. `/sunity/motion/cerebras-key`).
2. Lambda env `CEREBRAS_KEY_PARAM=<name>` (SAM template / `aws lambda update-function-configuration`).
3. **Pod** env `CEREBRAS_KEY_PARAM` + restart uvicorn (`--workers 1`; module-cached `_COACH_WRITER` created at first `_process`). memory `pod-ops-claude-runs`, `runpod-gpu-env`, `next-pod-use-network-storage`.
4. Keep `GEMINI_COACH_ENABLED` OFF (Cerebras-only `else` branch, app.py:1858-1860).
5. Verify `/health` (`auth_configured:true, pipeline_loaded:true`) → run 1 real analysis → grep Firestore doc `tips[].detail2`.

## Shared Patterns

### 3-way Contract Lockstep
**Source:** models.py:37-41 (BodyProfile block) + `_validate_force_pattern_inference` (firestore_admin.py:343) + drift tests (`backend/tests/phase09/test_firestore_lockstep_phase9.py`, `test_force_pattern_lockstep.py`).
**Apply to:** `recommendedExercises` (Plan A) and any `RecommendedExercise` field. Edit `app/src/types/analysis.ts` + `backend/shared/.../models.py` (contract comment) + `docs/contract.md §4` in ONE atomic commit. camelCase in Firestore, the helper `_snake_to_camel`/`_dataclass_to_camel_case_dict` (app.py:1362) handles dataclass→camel IF a dataclass is introduced (the exercise list is built as plain camelCase dicts, so the helper is bypassed — note this in the plan).

### Firestore Nested-Array Ban (scoped validator)
**Source:** `_validate_force_pattern_inference` (firestore_admin.py:343-404) + `_validate_dict_only_scalars` (firestore_admin.py:104) whose body must never change.
**Apply to:** `recommendedExercises` (new `_validate_recommended_exercises`). Whitelist the one expected list-of-dict; per-item `_validate_dict_only_scalars`; cap length (criteria 2). Never loosen the global validator (memory `firestore-nested-array-flat`).

### Committed Fixture + Lazy Cached Loader
**Source:** `force_signals.py:229-235` (repo-root Path + module cache) loading `judging_data/*.yaml`; `backend/data/aka-mapping.json` precedent.
**Apply to:** both new fixtures (`corrective_exercises.json`, `motion_ipsf_map.json`). JSON (not YAML) to match `backend/data/*.json` precedent. No Firestore, no seed script (RESEARCH Storage Decision; memory `user-beginner-stepwise`).

### BodyProfile → Coaching-Only (D-05 guard)
**Source:** models.py:46-47 comment ("weightKg 는 scoring/analysis consumer 모듈에 유입되면 안 됨") + RESEARCH §Anti-Patterns grep gate.
**Apply to:** `exercise_map.map_exercises` (reads painAreas), `coach_writer` context. Add a grep/AST gate test asserting painAreas/weightKg never reach `dimension_scores` (precedent `test_force_pattern_no_severity_use.py`).

### Theme Tokens Only (light theme)
**Source:** result.tsx:60 import + CoachingTipDetailModal.tsx:20, 135-283 (`colors.brand`/`colors.divider`/`radius.card`/`radius.button`).
**Apply to:** `RecommendedExerciseModal.tsx` + result.tsx new section. Brand #FF4B33 via `colors.brand` only. Light theme; no dark backgrounds (app/CLAUDE.md, CLAUDE.md §4).

### Test Infra (phase13 mirror of phase09)
**Source:** `backend/tests/phase09/conftest.py` + `__init__.py` + lockstep/forbidden-phrase tests.
**Apply to:** new `backend/tests/phase13/{__init__.py,conftest.py,fixtures/}` — sample ForcePatternInference JSON + bodyProfile painAreas inputs; forbidden-phrase regex gate for criteria 8 (precedent `FORBIDDEN_PHRASES_PHASE9_REGEX`). Run: `python -m pytest backend/tests/phase13/ -x`.

## No Analog Found

None. Every Phase 13 file maps to an existing, production-exercised analog (RESEARCH §Summary: "~80% wiring over existing structures"). The two genuinely-new *content* fixtures (`corrective_exercises.json`, `motion_ipsf_map.json`) are new data but follow the exact `backend/data/*.json` + fixture-loader patterns above; their content is fully sourced from NotebookLM (RESEARCH §A/§B).

## Metadata

**Analog search scope:** `backend/shared/python/sunity_shared/analysis/` (assemble, coach_writer, force_pattern, force_signals, models), `backend/shared/python/sunity_shared/firestore_admin.py`, `backend/functions/pipeline/app.py`, `backend/data/`, `backend/judging_data/`, `app/src/types/analysis.ts`, `app/src/lib/userAnalyses.ts`, `app/src/components/CoachingTipDetailModal.tsx`, `app/src/app/analysis/result.tsx`, `docs/contract.md`, `backend/tests/phase09/`.
**Files scanned:** ~16 source files read (targeted, non-overlapping ranges).
**Pattern extraction date:** 2026-06-16

## PATTERN MAPPING COMPLETE
