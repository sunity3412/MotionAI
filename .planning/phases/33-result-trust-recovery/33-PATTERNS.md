# Phase 33: result-trust-recovery - Pattern Map

**Mapped:** 2026-07-23
**Files analyzed:** 12 (3 newly created, 9 modified in place)
**Analogs found:** 12 / 12 (all have a strong in-repo analog — brownfield phase)

> Read-only mapping. Every deliverable modifies an already-wired path or copies a directly-adjacent sibling. Per RESEARCH.md the disease is **provenance/data misalignment, not missing machinery** — do NOT add new libraries or new UI surfaces (D-05).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/tests/phase33/conftest.py` (NEW) | test scaffold | — | `backend/tests/phase32/conftest.py` | exact |
| `backend/tests/phase33/test_phrasebook_motion_specific.py` (NEW) | test | data-assert | `backend/tests/phase32/test_phrasebook_assembly.py` + `test_phrasebook_forbidden.py` | exact |
| `backend/tests/phase33/test_zoom_join_joint_exact.py` (NEW) | test | unit | `backend/tests/phase32/test_fault_zoom_crop_parity.py` | role-match |
| `backend/scripts/dump_analysis_doc.py` (NEW — A-0/mockup) | script/utility | request-response (read Firestore) | `backend/evals/phase24/read_veto_status.py` (+ `firestore_admin._db`) | exact |
| `.planning/phases/33-.../mockups/index.html` (NEW — D-10) | mockup | static render | `.planning/phases/32-result-readability-3-omni/mockups/index.html` | exact |
| Illustration wiring component `app/src/components/*.tsx` (NEW — D-15) | component | file-I/O (asset render) | `app/src/components/ReferenceCornerSection.tsx` (asset+theme presentational) | role-match |
| `backend/data/phrasebook.json` (MOD — D-14) | config/data | data | itself (existing `__common__.*` entry schema) | in-place |
| `backend/shared/.../analysis/phrasebook.py` (MOD if any — expect code-change-0) | service | transform | itself (`assemble_phrases:118`) | in-place |
| `backend/shared/.../analysis/fault_zoom.py` (MOD — D-12) | service/adapter | transform (PNG compose) | itself (`build_fault_zoom_comparisons:1287`, item build `:1533`) | in-place |
| `backend/functions/pipeline/app.py` (MOD — crop/audio builders) | controller (SQS consumer) | event-driven | itself (`_build_fault_zoom_comparisons:2907`, `_synthesize_coach_audio_items:3215`) | in-place |
| `app/src/app/analysis/result.tsx` (MOD — selectedZoom/cueWindows/coachAudio) | screen | request-response render | itself (`selectedZoom:1215`, `cueWindows:1601`, `coachAudio:1641`) | in-place |
| `app/src/lib/deductionLabels.ts` (MOD — join joint-exact) | utility | transform | itself (`projectDeductionRecordKeypoints:221`) | in-place |
| `app/src/components/KeypointOverlay.tsx` (MOD — D-13 hide/show) | component | render | itself | in-place |
| `app/src/theme/typography.ts` (MOD — Wave B D-17) | config | — | itself (existing token set) | in-place |

---

## Pattern Assignments (NEWLY CREATED — no in-place analog)

### `backend/tests/phase33/conftest.py` (test scaffold)

**Analog:** `backend/tests/phase32/conftest.py` — copy verbatim, change docstring phase number.

`sys.path` injection pattern (whole file, 22 lines):
```python
from __future__ import annotations
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
_LAYER = _BACKEND / "shared" / "python"
_SCRIPTS = _BACKEND / "scripts"
for _p in (_BACKEND, _LAYER, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
```
Note: phase32 conftest injects `_SCRIPTS` because later plans import `functions/*`/`scripts`. Phase 33's join/phrasebook tests are pure-function → only `_LAYER` strictly needed, but copying all three is harmless and matches the precedent.

---

### `backend/tests/phase33/test_phrasebook_motion_specific.py` (test, data-assert)

**Analog:** `backend/tests/phase32/test_phrasebook_assembly.py` (assembly priority) + `test_phrasebook_forbidden.py` (D-09 grep gate). The D-14 phase-33 novelty: assert a **motion-specific** entry now resolves BEFORE `__common__`.

Import + flat-scalar helper (from `test_phrasebook_assembly.py:11-20`):
```python
from sunity_shared.analysis import phrasebook

def _is_flat_scalar_dict(d: dict) -> bool:
    if not isinstance(d, dict):
        return False
    return all(v is None or isinstance(v, (str, int, float, bool)) for v in d.values())
```

Priority assertion to ADD (new — proves `{motion_key}.{criterion}` override wins; today 0 such keys so this test fails until data authored):
```python
def test_motion_specific_overrides_common() -> None:
    # after D-14 authoring, e.g. "ref-power-spin.split_angle" exists
    specific = phrasebook.assemble_phrases("ref-power-spin", "split_angle")
    common = phrasebook.assemble_phrases("어떤_미등재_동작", "split_angle")
    assert specific.get("cueLine") and specific["cueLine"] != common["cueLine"], \
        "동작 전용 cueLine 이 __common__ 과 동일 (override 미작동 또는 데이터 미작성)"
    assert _is_flat_scalar_dict(specific)
```

Forbidden-copy gate (reuse `test_phrasebook_forbidden.py:19-24,46-55` verbatim — it already walks `rendered_copy_strings()` for `%`, bare digits, `FORBIDDEN_PHRASES_PHRASEBOOK`). New motion-specific entries automatically fall under this gate; no new gate code needed, but keep the `test_sanity_extraction_nonzero` companion so the gate can't silently pass on 0 strings.

**"How would I know if this were wrong?" (D-18):** the override test fails if data authoring didn't land; the forbidden gate fails if a numeric/`%` snuck into new cueLines. Both are red-on-failure, not silent.

---

### `backend/tests/phase33/test_zoom_join_joint_exact.py` (test, unit)

**Analog:** `backend/tests/phase32/test_fault_zoom_crop_parity.py` — synthetic `@dataclass` fixture pattern, pure PIL/numpy, no S3/firestore import (header line: `순수 — PIL/numpy 외 의존 0`).

This test targets seam #1 (RESEARCH Pattern 1/2). Because the join lives in **TS** (`deductionLabels.ts` / `result.tsx`), the joint-exactness assertion has no python test runner. Two options for the planner:
- If seam #1 is fixed **backend-side** (criterion-keyed crops in `fault_zoom.py`): assert here that `build_fault_zoom_comparisons` emits an item whose `joint`/`region` matches the criterion that will be shown (extend the `_Match` synthetic fixture from the parity test).
- If fixed **app-side** (joint-exact `projectDeductionRecordKeypoints`): there is NO JS test runner (`npm run typecheck` is the only static gate, RESEARCH §Validation). Verification = the D-19 eyeball of regenerated PNGs + a `tsc --noEmit` pass. Document the missing automated coverage explicitly (D-18 "전수 불가 시 무엇을 못 봤는지 명시").

Synthetic-fixture skeleton to copy (`test_fault_zoom_crop_parity.py:24-31`):
```python
from sunity_shared.analysis import fault_zoom as fz

@dataclass
class _Match:
    start: int
    path: list
```

---

### `backend/scripts/dump_analysis_doc.py` (NEW — A-0 evidence + mockup real data)

**Analog:** `backend/evals/phase24/read_veto_status.py` (near-exact: reads a doc by id, prints fields, observation-only, Pod run header). Client-init comes from `firestore_admin._db()`.

Path bootstrap + firestore client (from `read_veto_status.py:13-22,34`):
```python
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent            # (scripts/ → backend)  ← adjust vs read_veto_status (evals/phase24)
sys.path.insert(0, str(BACKEND / "shared" / "python"))
sys.path.insert(0, str(BACKEND))

from sunity_shared import firestore_admin as fa   # noqa: E402
```

Read a specific doc — use the existing accessor, do NOT hand-roll a client (`firestore_admin.py:1979`):
```python
# firestore_admin.get_analysis already does the exact read (no security-rule bypass concerns)
doc = fa.get_analysis(uid, analysis_id) or {}
res = doc.get("result") or {}
# D-10 targets: uid csKWYvI3WCPYPysNQ9KkWecaUvq1 / analysis 071df9f894d64d1696f106e613f51f5c
```
The underlying client init to be aware of (`firestore_admin.py:21-30`) — lazy, module-cached, `FIREBASE_SA_PARAM`/`FIREBASE_SA_PATH` via `_auth._ensure_firebase()`; never hardcode creds (CLAUDE.md).

Run header to copy (`read_veto_status.py:8-11`) — creds env is `FIREBASE_SA_PATH=/workspace/firebase-sa.json`, `PYTHONPATH=shared/python:.`. Locally `firebase-sa.json` exists (RESEARCH Env table).

**What to dump for A-0 (D-04 evidence table):** `result.visionVeto.faultJoints`, `result.deductionBreakdown.records[].criterion` (→ `activatedCriteria`), `result.faultZoomComparisons[]` (`joint`/`region`/`deficitDeg`/`userFrameIdx`/`refFrameIdx`/`refMatch`), plus download the 3 crop PNG presigned URLs to disk and open them (D-19). This is the "pointed vs measured vs shown" divergence input.

**"How would I know if wrong?":** the dump prints raw stored values; if `faultJoints` is empty or `window_joints` empty (baseline shows 11/12 empty) that IS the A-0 finding, not an error to swallow.

---

### Mockup `.planning/phases/33-.../mockups/index.html` (NEW — D-10)

**Analog:** `.planning/phases/32-result-readability-3-omni/mockups/index.html` (46KB, single self-contained HTML; sibling `README.md`, `emphasis-tokens.md`, `section-order.md`).

Structure to copy (verified head of the phase-32 file):
- Single `<html lang="ko">`, Pretendard via jsdelivr CDN with system-font fallback comment (`design.md §2`).
- `:root` design tokens: `--brand:#FF4B33` (marked 변경 금지), `--teal:#54B8CD` for safety/error tone (red banned to avoid brand clash), light-only bg. Reuse these exact tokens.
- One shared `.phone`/`.card`/`.board` CSS shell; per-안 (variant) blocks swapped via JS — "안×케이스 전면 재제작 금지" (do not rebuild every case, vary only the changed block).
- Sticky `.topbar` (dark `#111`) with `.tabs` to switch 안 2~3개 side by side.
- `letter-spacing:0` mandatory (`iOS 26 SIGABRT` on negative letterSpacing — baked note).

Phase-33 D-10 novelty vs phase-32: three **state-transition still frames** (`재생 중` → `음성 중(정지+부위 강조)` → `재개`) in one page, and data must be belle's REAL doc `071df…` (dump via the script above), mock forbidden. Include the D-08 worst-case set (가림/인버전/모션블러/프레임밖/좌표결측), not only a good case.

---

### Illustration wiring component (NEW — D-15, app wiring = 0 today)

**Analog:** `app/src/components/ReferenceCornerSection.tsx` — the closest "asset + theme token, state-driven, silent-fallback" presentational component. `DeductionCard.tsx` / `DeductionDetailSheet.tsx` also render `Image` and can be secondary refs.

Copy these conventions (verified `ReferenceCornerSection.tsx:26-70`):
- Header comment block citing decisions (`D-09`, `amended D-10`, invariant tags), then `import { Image, ... } from 'react-native'` and `import { colors, layout, radius, spacing, typography } from '../theme'`.
- **Named export**, inline destructured prop type (not a separate interface), `StyleSheet.create` at bottom, theme tokens only — hardcoded color/spacing/radius = 0 (`ReferenceCornerSection.tsx:25` states the standard: "ScoreBreakdownSection 표준형").
- **Silent fallback**: a `'hidden'` state = render nothing; no Alert/Toast/error banner (`:13-14,34`). Apply to illustrations that fail anatomy review (D-15) — un-wired sets simply don't render.
- Image source: RN `Image` (already used here) or `expo-image` if illustration needs caching. Do NOT add a new image library (RESEARCH Standard Stack — `expo-image` is transitive Expo SDK 54; verify before use).

Assets today live under `.planning/.../samples/*.jpg` (3 files) — wiring requires moving/importing chosen sets into `app/`'s asset dir (RESEARCH Runtime State: samples are NOT bundled in `app/`).

**"How would I know if wrong?":** anatomy 전수 검수 — open every illustration file (D-19); any set with a failed limb-count/joint-direction check stays un-wired (silent-hidden), never shipped.

---

## Pattern Assignments (MODIFIED — extract current shape at the seam)

### `backend/data/phrasebook.json` (D-14 — author motion-specific entries)

**Current shape** — `entries` = 13 keys all `__common__.{criterion}` (verified). Each entry is a flat 6-slot dict (`phrasebook.json:77-84`):
```json
"__common__.leg_extension": {
  "statusLine": "무릎이 기준보다 덜 펴져 있어요",
  "whyLine": "다리 라인이 끝까지 뻗지 않으면 심사에서 신전 완성도로 감점되는 부분이에요",
  "cueLine": "발끝으로 천장을 길게 밀어낸다는 느낌으로 다리를 쭉 뻗어보세요",
  "coachQuestion": "무릎을 끝까지 펴려면 어디에 힘을 줘야 하는지 강사님께 여쭤보고 싶어요",
  "exerciseId": "legs_not_extended",
  "exerciseReason": "무릎을 끝까지 펴는 다리 신전 근력이 받쳐줘야 하기 때문이에요"
}
```
**Action:** add `"{motion_key}.{criterion}"` keys (e.g. `"ref-power-spin.split_angle"`) using the SAME 6-slot schema. `_meta.coverageMatrix.cellRule` currently claims "동작 전용 override 는 현재 0" — update `_meta` in lockstep when you add overrides. `exerciseId` MUST be an existing `corrective_exercises.json` defect key (schema note `:11`). Scope the matrix to combos that ACTUALLY emit per motion (RESEARCH Open Q3: read `activatedCriteria` per motion from the sweep report, not all 198 cells). Slot copy MUST be digit/`%`-free (D-09, enforced by the forbidden test).

### `backend/shared/.../analysis/phrasebook.py` (expect code-change-0 — D-14)

**Current lookup** already supports motion-specific (`phrasebook.py:143-151`):
```python
entries = _load_phrasebook().get("entries", {})
if motion_key:
    specific = entries.get(f"{motion_key}.{criterion}")   # ← 0 such keys today
    if isinstance(specific, dict):
        return _entry_slots(specific)
common = entries.get(f"{_COMMON_PREFIX}.{criterion}")       # all 13 hits land here
if isinstance(common, dict):
    return _entry_slots(common)
return _fail_closed_slots()
```
No code change expected. If a hard-gate (direction contradiction → fail-closed, D-14) needs enforcing beyond data, it would extend `_fail_closed_slots()` (`:105-115`), but prefer data + the forbidden test.

### `backend/shared/.../analysis/fault_zoom.py` (D-12 — crop provenance / 8 defects)

**Current per-item emit** (`fault_zoom.py:1533-1557`) — scalar-only (Firestore flat), badge baked via `_mark`:
```python
item = {
    "joint": unit.joint, "deficitDeg": deficit, "png": png,
    "userFrameIdx": int(u_kp_idx), "refFrameIdx": int(r_kp_idx),   # keypointReport index space, NOT 9fps
    "refMatched": not ref_match_failed,
}
if kind: item["kind"] = kind
if unit.region: item["region"] = unit.region
item["refMatch"] = "failed" if ref_match_failed else "dtw"
```
Ref side draws no line/mark (Gate B, `:1529`) → defect #1. Badge bake (`_mark:606`) → defect #6 (belle wants OFF; but W4 badge-move is Wave B — coordinate so W1 doesn't re-bake, RESEARCH State-of-Art). fps landmine: route ALL indices through `_to_rep_idx` (`:195`), never hardcode 9/18 (defect #4). Keep items scalar — `firestore_admin._validate_dict_only_scalars` (`:1418-1435`) rejects nested. Contract 3-way lockstep (`models.py` + `analysis.ts` + `contract.md`) if the item shape changes.

### `backend/functions/pipeline/app.py` (crop + audio builders)

**Crop builder** (`_build_fault_zoom_comparisons:2907`) — crops sourced from vision-veto joints (seam #1 root, `:2936`):
```python
fault_joints = list(vv.get("faultJoints") or [])   # if empty → top-2 keypoint deltas fallback (:2970)
```
**Audio builder** (`_synthesize_coach_audio_items:3215`) — Polly reads `cueLine` verbatim (`:3229`), so W3 phrasebook fix propagates to voice; fail-closed records (no cueLine) are skipped (`:3279-3284`):
```python
resp = _get_polly_client().synthesize_speech(Text=rec["cueLine"], ...)  # neural
```
Both are stored artifacts (S3 PNG / mp3) → editing code does NOTHING to belle's existing doc; requires 6-motion Pod re-sweep to regenerate (D-25, RESEARCH Runtime State).

### `app/src/app/analysis/result.tsx` (selectedZoom / cueWindows / coachAudio)

**`selectedZoom` join** (`:1215-1229`) — region-first FIRST-MATCH, the defect-5 mechanism:
```typescript
const kps = new Set(projectDeductionRecordKeypoints(selectedRecord, vetoFaultJoints));
for (const z of result.faultZoomComparisons ?? []) {
  if (z.tier === 'advisory') continue;                 // defect #8: advisory never shown
  const zoomKps = z.region ? [...(REGION_MEMBER_KEYPOINTS[z.region] ?? [])] : [z.joint];
  if (zoomKps.some((k) => kps.has(k))) return z;        // FIRST region match → mismatch
}
```
**`cueWindows`** (`:1601-1635`) — subtitle text = `rec.cueLine` (same source as voice); spot-check-hidden records excluded (`isRecordHidden`, `:1604`). fps from `keypointReport.fps || 9`. **`coachAudioAnalysisId`** (`:1641`) — gate only ('done' + items>0); resign/prefetch owned by `audioCue.ts`.

### `app/src/lib/deductionLabels.ts` (join joint-exact — seam #1 fix candidate)

**`projectDeductionRecordKeypoints`** (`:221-240`) — the `source==='vision'` branch that projects to ALL faultJoints (defect #5 root):
```typescript
if (record.criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) {
  const jk = record.criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
  const kp = KEYPOINT_FROM_ANGLE_KEY[jk];
  return kp ? [kp] : [];
}
if (record.source === 'vision') return [...(faultJoints ?? [])];   // ← projects to ALL pointed joints
```
`buildDeductionMarkers` (`:242`) consumes the same projection (single source for markers + cues + zoom). Fixing here (joint-exact) is OTA-only but depends on the crop carrying the right joint; the source (backend) fix removes it at origin (RESEARCH Open Q2 — decide after A-0).

### `app/src/components/KeypointOverlay.tsx` (D-13 — hide-by-default / show-on-demand)

Current: renders body keypoints + axis polyline over video, `react-native-svg`, tokens only (`:31-41`). Action-text pills already removed (`:10-13` — "재생 중엔 번호 점만"). D-13 = keypoints hidden by default + opt-in toggle (analog `KeypointOverlayToggle.tsx` already exists for persistence via async-storage). No new library.

### `app/src/theme/typography.ts` (Wave B — D-17 type scale)

Existing token set (`:23-65`) already has the phase-32 emphasis scale (`badge/bodySm/bodyMd/bodyLg/title/headline`, `:59-65`) alongside legacy (`caption:12`, `boxLabel:15`, `score:50`). D-17 = consistency sweep across these; `track()` returns 0 (negative letterSpacing → iOS SIGABRT, `:4`). Hardcoding forbidden — extend tokens, don't inline.

---

## Shared Patterns

### Firestore Admin client init (backend scripts + pipeline)
**Source:** `backend/shared/.../firestore_admin.py:21-30` (`_db()` lazy singleton) + `get_analysis:1979`
**Apply to:** the new `dump_analysis_doc.py` script and any A-0 readback. Never hand-roll a firebase-admin client; call `firestore_admin.get_analysis(uid, id)`. Creds via `_auth._ensure_firebase()` (Parameter Store / `FIREBASE_SA_PATH`), never hardcoded.

### Phrasebook fail-closed (no-fabrication)
**Source:** `phrasebook.py:105-115` `_fail_closed_slots()` + `phrasebook.json.failClosed`
**Apply to:** all D-14 authoring — an unsupported/contradicting combo must return `{statusLine, whyLine, coachQuestion, failClosed:True}` with NO `cueLine`/`exerciseId`. 틀린 조언보다 조언 없는 게 낫다 (D-14). Voice + subtitle auto-skip fail-closed records.

### Presentational component standard ("ScoreBreakdownSection 표준형")
**Source:** `ReferenceCornerSection.tsx:25` (stated standard), applies across `app/src/components/*.tsx`
**Apply to:** the new illustration component + any result.tsx sub-render. Named export + inline prop type + header decision-comment + `StyleSheet` at bottom + theme tokens only + silent `'hidden'` fallback (no Alert/Toast). Brand `#FF4B33` unchanged, light-only.

### Scalar-only Firestore payload
**Source:** `firestore_admin.py:1418-1435` `_validate_dict_only_scalars`
**Apply to:** any change to `faultZoomComparisons[]` items — keep flat scalars (no nested array/dict). Contract lockstep across `models.py` + `analysis.ts` + `docs/contract.md`.

### Stored-artifact regeneration gate (D-19/D-25)
**Source:** RESEARCH Runtime State + `read_veto_status.py` run header
**Apply to:** every crop/voice change — the stored PNG/mp3 in belle's doc will NOT update from a code edit. Verification = Pod re-boot (`rbpnmxhbfoeg35` OFF, belle-gated) + 6-motion re-sweep (`backend/evals/phase25/run_sweep.py` + `assert_gates.py`) + open the regenerated artifacts. "typecheck/pytest pass" with no artifact opened = D-19 failure.

## No Analog Found

None. Every deliverable has a strong in-repo analog (this is a brownfield expression-layer phase). The only "novel" work is content (illustration pixels, Korean phrasebook copy, HTML mockup layout), whose *wiring/structure* still copies an existing sibling.

Fixture-less registered motions (`ref-foxtop`, `ref-foxtop-split`, `ref-invert`, `ref-sideway-spin`) have no paired `fixtures/phase15/*` — per D-23 the planner must name an alternative verification path (belle real docs) for these; not a missing analog, a missing test input.

## Metadata

**Analog search scope:** `backend/tests/phase32/`, `backend/scripts/`, `backend/evals/phase24/`, `backend/shared/.../analysis/{phrasebook,fault_zoom,firestore_admin}.py`, `backend/functions/pipeline/app.py`, `app/src/components/`, `app/src/app/analysis/result.tsx`, `app/src/lib/deductionLabels.ts`, `app/src/theme/typography.ts`, `.planning/phases/32-.../mockups/`.
**Files scanned:** ~20 (targeted reads at named seams; no full-file re-reads).
**Pattern extraction date:** 2026-07-23
