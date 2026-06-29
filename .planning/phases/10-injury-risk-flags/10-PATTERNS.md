# Phase 10: 부상 위험 신호 플래그 (injury-risk-flags) - Pattern Map

**Mapped:** 2026-06-29
**Files analyzed:** 10 (3 create, 7 modify)
**Analogs found:** 10 / 10 (every file has a strong in-repo analog — net-new layer, zero new deps)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/analysis/safety_flags.py` | service (pure analysis core) | transform / batch | `analysis/force_pattern.py` + `analysis/kismam.py` | exact (role + flow) |
| `backend/functions/pipeline/app.py::_process` (inject) | controller (pipeline orchestrator) | request-response / batch | same file, `force_signals` + `force_pattern_inference` blocks (lines 3458–3507, 3785) | exact (self-analog) |
| `backend/shared/python/sunity_shared/firestore_admin.py` (`_validate_safety_flags`) | middleware (write-time validator) | transform | `_validate_force_signals_report` (firestore_admin.py:223) | exact |
| `app/src/types/analysis.ts` (`SafetyFlag` type) | model (contract mirror) | transform | `ForceSignalsReport` / `forceSignalsReport` (analysis.ts:1018, 518) | exact |
| `backend/shared/python/sunity_shared/models.py` (Python mirror) | model (contract mirror) | transform | force_signals re-export + `EXPERIENCE_LEVELS` (models.py:206, 465) | exact |
| `docs/contract.md` (`SafetyFlag` doc) | config (contract doc) | n/a | §9 ForceSignalsReport (contract.md:994) | exact |
| `app/src/app/analysis/result.tsx` + `InjuryRiskSection`/`InjuryRiskFlagCard` | component (RN screen + cards) | event-driven (onSnapshot render) | `AccuracyLimitBadge.tsx` + `강사에게 확인할 점` block (result.tsx:1151) | exact |
| `app/src/theme/colors.ts` (`warnAmberBg`) | config (theme token) | n/a | `warnAmber` + Phase 12 token block (colors.ts:46) | exact |
| `backend/tests/phase10/*` (6 files + `__init__.py`) | test | transform | `backend/tests/phase09/test_force_pattern_dataclass.py` + `phase08/conftest.py` | exact |

---

## Pattern Assignments

### `backend/shared/python/sunity_shared/analysis/safety_flags.py` (NEW — service, transform)

**Analog:** `analysis/kismam.py` (module-header + pure-function style) and `analysis/force_signals.py` (frozen dataclass + `__post_init__` enum validation). RESEARCH names `kismam`/`force_pattern` explicitly.

**Module-header docstring convention** (copy from `kismam.py:1-23`): open with `"""<purpose>` then cite source-of-truth and tag every threshold `[CITED]` / `[ASSUMED]`. This is mandatory for D-07 provenance (Pitfall 3). Note the exact `[ASSUMED]`/`[CITED]` tagging at `kismam.py:19-21`:
```python
"""KISMAM — 관절 편차(도) → 0~100 점수 + ...
관절별 점수 매핑(score_from_deviation): score = 100·exp(-½·z²) — Z-score 가우시안 감쇠.
  penalty_per_deg 는 [ASSUMED] v1 휴리스틱이다 — ... 보유 13영상 sweep 으로 재calibrate 금지
  (D-05 경계, [[scoring-redesign-must-generalize-no-overfit]]). tol(허용오차) 만 IPSF [CITED].
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import numpy as np
from .skeleton import JOINT_KEYS, JOINT_LABEL_KO, ...
```
Note: `from __future__ import annotations` at top (project-wide convention), relative imports (`from .skeleton import ...`), numpy as the only numeric dep.

**Frozen-dataclass + enum-validation pattern** (copy from `force_signals.py:401-437` `StabilityMetric`):
```python
@dataclass(frozen=True)
class StabilityMetric:
    phase: MotionPhase
    jitter_score: float
    jerk_score: float
    ...
    unstable_body_parts: list[str] = field(default_factory=list)
    severity: SeverityLevel = "low"
    confidence: MetricConfidence = "low"
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.severity not in _SEVERITY_LEVELS:
            raise ValueError(
                f"severity must be one of {_SEVERITY_LEVELS}, got {self.severity!r}"
            )
```
Mirror this for `SafetyFlag`: `@dataclass(frozen=True)`, `field(default_factory=list)` for any list, and a `__post_init__` that validates `flag_type`/`severity`/`confidence`/`mode_scope` against module-level `frozenset`/tuple enums (`_SEVERITY_LEVELS = ("low","medium","high")` style). **Keep all fields scalar** — no nested lists (Firestore ban, Pitfall 1). RESEARCH Pattern 1 gives the field list.

**Pure-function signature style** (copy from `kismam.py:111-124` `score_from_deviation`): module-level function, type-hinted, numpy-only, NaN-degrades-to-floor rather than raising:
```python
def score_from_deviation(deviation_deg: float, tolerance_deg: float = _IPSF_TOLERANCE_DEG) -> int:
    d = float(deviation_deg)
    if not np.isfinite(d):
        return 0  # 측정 불가 = 최대 결함. raise 금지
    z = d / max(tolerance_deg, 1e-6)
    return max(0, min(100, int(round(100.0 * float(np.exp(-0.5 * z * z))))))
```
Phase 10 REUSES `score_from_deviation(dev, tol=20.0)` directly for D-03 asymmetry quantification — import it, do not reimplement. `compute_safety_flags(...)` itself returns `list[SafetyFlag]` (RESEARCH Pattern 1/2 for the posture-AND-control-loss gate).

**Joint triplets to consume** (from `skeleton.py:39-50`): `JOINT_ANGLES["left_hip"] = ("left_shoulder","left_hip","left_knee")` = D-04 trunk-femur proxy; `left_knee=("left_hip","left_knee","left_ankle")` and `left_elbow=("left_shoulder","left_elbow","left_wrist")` = D-05 hyperextension joints. `JOINT_KEYS` is the 8-joint contract tuple.

---

### `backend/functions/pipeline/app.py::_process` (MODIFY — controller, inject)

**Analog:** the `force_signals` + `force_pattern_inference` blocks in the same function (the canonical "compute report → camelCase dict → pass to complete_analysis" pattern).

**How `force_signals_report` is currently computed** (lines 3458-3468) — inject `compute_safety_flags` immediately after this, before `complete_analysis`:
```python
force_signals_report = fs.compute_force_signals(
    inputs.pose_frames,
    inputs.pole_axis_measurement,
    student_profile,
    angles=angles,
    fps=9.0,
    motion_id=getattr(profile, "motion_id", None),
    ...
)
force_signals_dict = _dataclass_to_camel_case_dict(force_signals_report)
```

**Mode/profile derivation already in scope** (mirror the existing usages): mode-context branch at lines 3481-3489 (`mode == models.MODE_EXPERT`); `models.normalize_body_profile(meta.get("bodyProfile"))` already called at line 3270 and 3573 (D-06 `experience` source); `ref.get(...)` pattern at lines 2976-3104 (D-06 `reference.level` source). The Phase 9 block uses `_dataclass_to_camel_case_dict(...)` to flatten — Phase 10 follows the same: build `result["safetyFlags"] = [_dataclass_to_camel_case_dict(f) for f in safety_flags]` (or a dedicated `_safety_flag_to_camel`).

**How the report reaches Firestore** (line 3785-3794): `force_signals_dict` is passed as a kwarg `force_signals_report=force_signals_dict`:
```python
firestore_admin.complete_analysis(
    uid, analysis_id, result,
    ...
    force_signals_report=force_signals_dict,
    force_pattern_inference=force_pattern_inference_dict,
    ...
)
```
**Decision for planner (RESEARCH A5):** `forceSignalsReport` is stored *inside* `payload["result"]` yet still passed as a kwarg (so the scoped validator runs). Recommended: set `result["safetyFlags"]` directly in `_process` AND add a `safety_flags=` kwarg to `complete_analysis` (or validate `result.get("safetyFlags")` inline) so `_validate_safety_flags` fires before write — mirror exactly how `force_signals_report=` triggers `_validate_force_signals_report` (firestore_admin.py:917-921).

---

### `backend/shared/python/sunity_shared/firestore_admin.py` (MODIFY — `_validate_safety_flags`)

**Analog:** `_validate_force_signals_report` (firestore_admin.py:223-285) + its helper `_validate_metric_dict_with_scalar_lists` (firestore_admin.py:288+). This is the proven scoped-validator that lets a `list[dict]` through while preserving the project-wide nested-array ban.

**Validator structure to mirror** (firestore_admin.py:223-285):
```python
def _validate_force_signals_report(payload: dict, *, path: str = "forceSignalsReport") -> None:
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(f"... dict 입력만 허용. path={path!r} got {type(payload).__name__}")
    for key, value in payload.items():
        sub_path = f"{path}.{key}"
        if value is None or isinstance(value, (str, int, float, bool)):
            continue
        ...
        if isinstance(value, list):
            for i, item in enumerate(value):
                item_path = f"{sub_path}[{i}]"
                if not isinstance(item, dict):
                    raise ValueError(f"{item_path} metric list 원소는 dict 박제 강제: ...")
                _validate_metric_dict_with_scalar_lists(item, path=item_path)
            continue
```
For `_validate_safety_flags`: `result["safetyFlags"]` is a top-level `list[dict]` (not wrapped in an object). Validate each flag dict as scalar-only via `_validate_dict_only_scalars` (firestore_admin.py:104) — Phase 10 flags have **no** whitelisted scalar-list fields (keep every field scalar), so it's stricter than force_signals and can reuse `_validate_dict_only_scalars` directly per element. The whitelist pattern (firestore_admin.py:215-220 `_FORCE_SIGNALS_SCALAR_LIST_KEYS_IN_METRIC`) is the model if any list field is ever needed.

**Where to wire the call** — mirror firestore_admin.py:917-921:
```python
if force_signals_report is not None:
    _validate_force_signals_report(force_signals_report)
    payload["result"]["forceSignalsReport"] = force_signals_report
```
Add a sibling `if safety_flags is not None: _validate_safety_flags(safety_flags); payload["result"]["safetyFlags"] = safety_flags`. (Note: the Phase 9 `_validate_force_pattern_inference` at line 922-927 is itself a "Phase 8 패턴 1:1 mirror" — this exact mirroring is the established convention; follow it again.)

---

### Contract 3-mirror (MODIFY — model)

**Shared invariant:** `app/src/types/analysis.ts` ↔ `backend/shared/.../models.py` ↔ `docs/contract.md` change in lockstep (CLAUDE.md cross-cutting; CONTEXT Claude's-Discretion explicitly requires it).

**TS analog** (`analysis.ts:1018-1026` `ForceSignalsReport` interface + `:870` `SeverityLevel` + `:518` optional field on `AnalysisResult`):
```typescript
export type SeverityLevel = 'low' | 'medium' | 'high';   // line 870 — REUSE for SafetyFlag.severity

export interface ForceSignalsReport {     // line 1018 — structural analog
  version: string;
  overallConfidence: MetricConfidence;
  ...
}
// On AnalysisResult (line 518): optional + nullable so legacy docs + graceful-omit work:
forceSignalsReport?: ForceSignalsReport | null;
```
Add `export type SafetyFlagType = ...; export interface SafetyFlag {...}` (RESEARCH Code Examples gives exact fields, all camelCase), then `safetyFlags?: SafetyFlag[] | null;` on `AnalysisResult`. Reuse existing `SeverityLevel` and `ExperienceLevel`/`SkillLevel` (analysis.ts:19, 578) — do NOT redefine. Keep `CoachingTipDetail.injuryRisk` (analysis.ts:203) UNTOUCHED (D-01 — independent LLM layer).

**Python analog** (`models.py:206` enum tuple + `:465-470` re-export pattern):
```python
EXPERIENCE_LEVELS = ("beginner", "intermediate", "advanced")   # line 206 — D-06 input enum, REUSE

# models.py re-exports analysis dataclasses at file bottom (line 465):
from .analysis.force_signals import (  # noqa: E402, F401 — 파일 하단 re-export 패턴
    ...
    ForceSignalsReport,
)
```
Mirror: define `SAFETY_FLAG_TYPES`/`SAFETY_FLAG_SEVERITIES` tuples (or reuse force_signals `_SEVERITY_LEVELS`) and re-export `SafetyFlag` from `analysis.safety_flags` at the file bottom following the `# noqa: E402, F401` convention.

**contract.md analog** (`docs/contract.md:994-1126` §9 ForceSignalsReport): add a new `§N. SafetyFlag` section with the same table layout (`| field (camel) / field (snake) | type | cardinality |`) and the dated changelog footer style (contract.md:1451).

---

### `app/src/app/analysis/result.tsx` + `InjuryRiskSection` / `InjuryRiskFlagCard` (CREATE/MODIFY — component, event-driven)

**Analogs (named by UI-SPEC):** `AccuracyLimitBadge.tsx` (icon-row + title + description container, amber border) and the `강사에게 확인할 점` section block in result.tsx (section title + sub + card + per-row icon+text).

**`AccuracyLimitBadge` container pattern** (`AccuracyLimitBadge.tsx:31-72`) — the closest match for `InjuryRiskFlagCard`:
```tsx
export function AccuracyLimitBadge({ visible }: AccuracyLimitBadgeProps) {
  if (!visible) return null;                         // graceful omit — copy this guard
  return (
    <View style={styles.container} accessibilityRole="alert" accessibilityLabel={...}>
      <View style={styles.row}>
        <Ionicons name="warning" size={14} color={colors.warnAmber} />
        <Text style={styles.title}>{LINE_OCCLUSION}</Text>
      </View>
      <Text style={styles.description}>{LINE_SIDE}</Text>
    </View>
  );
}
const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.accuracyLimitBg,   // Phase 10: swap to colors.warnAmberBg
    borderWidth: 1, borderColor: colors.warnAmber, borderRadius: radius.card,
    paddingVertical: 12, paddingHorizontal: spacing.screenX, marginTop: 8,
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  title: { ...typography.boxLabel, color: colors.accuracyLimitText },
  description: { ...typography.caption, color: colors.textSecondary, marginTop: 4 },
});
```
Copy verbatim, change `backgroundColor` to `colors.warnAmberBg` (per UI-SPEC §Color), `Ionicons size={16}` (UI-SPEC row 1), and copy strings from UI-SPEC Copywriting Contract. Note the **block-comment-citing-spec** convention at the file top (AccuracyLimitBadge.tsx:1-15) — write the equivalent citing `10-UI-SPEC.md`.

**Section-block + conditional-render pattern** (`result.tsx:1151-1170` 강사에게 확인할 점):
```tsx
{openQuestionsForCoach.length > 0 && (        // conditional render — Phase 10: safetyFlags.length > 0
  <>
    <Text style={styles.sectionTitle}>강사에게 확인할 점</Text>
    <Text style={styles.coachSectionSub}>아래 질문을 강사와 함께 확인해보세요.</Text>
    <View style={[styles.card, styles.coachCard]}>
      {openQuestionsForCoach.map((q, i) => (
        <View key={`${q}-${i}`} style={styles.coachQuestionRow}>
          <Ionicons name="chatbubble-ellipses-outline" size={16} color={colors.brand} />
          <Text style={styles.coachQuestionText}>{q}</Text>
        </View>
      ))}
    </View>
  </>
)}
```
Mirror this for `InjuryRiskSection`: `{safetyFlags && safetyFlags.length > 0 && (...)}` — **omit entirely when empty** (UI-SPEC: no "안전합니다" reassurance). Note `coachQuestionRow`/`coachQuestionText` styles (result.tsx:1569-1579) are the exact icon-row + flex-shrinking-text shape to reuse.

**Placement** (UI-SPEC): render **immediately after the `OctagonScore` card block** (result.tsx:830-871) and **before the "동작 비교" section** (result.tsx:881-884 `<Text style={styles.sectionTitle}>동작 비교</Text>`). The score card is gated by `isScoreSuppressed`; insert the injury section right after that ternary closes.

**Icon/section conventions:** `Ionicons name="warning"` (warnAmber) per UI-SPEC; `highlightNumbers()` (result.tsx:115) for any inline number (avoid leading with a number); brand red `#FF4B33` FORBIDDEN for this section.

---

### `app/src/theme/colors.ts` (MODIFY — config, additive token)

**Analog:** `warnAmber` declaration + the Phase 12 / Phase 4 additive token blocks (colors.ts:46, 37-62) inside the single `as const` object.

**Existing `warnAmber` + additive-block convention** (colors.ts:46, 54-62):
```typescript
warnAmber: '#E6A300', // ⚠ occlusion badge
...
// ── Phase 4 신설 토큰 (04-UI-SPEC §Color) ─────────────────────────────
// alias 방식 — 기존 토큰 hex 복사 ...
accuracyLimitBg: '#F5F5F5', // 정확도 제한 배지 배경 (softBg alias)
accuracyLimitText: '#E6A300', // 정확도 제한 배지 텍스트 (warnAmber alias)
} as const;
```
Add inside the same `as const` object (additive, brand hex unchanged), following the dated-comment-citing-UI-SPEC convention:
```typescript
// ── Phase 10 신설 토큰 (10-UI-SPEC §Color) ────────────────────────────
warnAmberBg: '#FFF6E5', // 부상 위험 배너 surface (light amber tint)
```
Do NOT touch `brand: '#FF4B33'` (CLAUDE.md §4 hard rule). Token-only — hardcoding colors in components is forbidden.

---

### `backend/tests/phase10/*` (CREATE — test, transform)

**Analogs:** `backend/tests/phase09/test_force_pattern_dataclass.py` (pure-function/dataclass unit test) + `backend/tests/phase08/conftest.py` (programmatic fixture factory). `backend/tests/conftest.py` already injects `shared/python` on `sys.path` (no path hacks needed).

**Unit-test + kwargs-factory pattern** (phase09/test_force_pattern_dataclass.py:1-44):
```python
"""Plan 09-01 Wave 0 — ... __post_init__ validator ...
per Plan 09-01 must_haves + RESEARCH §"Pattern 1".
"""
from __future__ import annotations
import dataclasses
import pytest
from sunity_shared.analysis.force_pattern import ForcePatternFinding, ForcePatternInference

def _kwargs(**overrides) -> dict:
    base = dict(pattern="release", phase="lock", source_signal="axis_tilt", ...)
    base.update(overrides)
    return base

def test_invalid_pattern_enum_raises() -> None:
    with pytest.raises(ValueError, match="pattern"):
        ForcePatternFinding(**_kwargs(pattern="nonsense"))
```
Mirror: a `_kwargs(**overrides)` factory for `SafetyFlag`, `pytest.raises(ValueError, match=...)` for `__post_init__` enum violations, and the docstring-cites-plan convention.

**Fixture-factory pattern** (phase08/conftest.py): build synthetic `(T, 17, 4)` arrays and a low-control-loss `ForceSignalsReport` programmatically (the elite-no-FP fixture). Create `backend/tests/phase10/__init__.py` + `conftest.py`. Required files per RESEARCH Validation Architecture: `test_safety_flags_firing_rule.py` (D-02 elite-no-FP — the headline gate), `test_safety_flags_hyperextension.py` (D-05 cross-product sign), `test_safety_flags_asymmetry.py` (D-03), `test_safety_flags_level.py` (D-06 mode1-only), `test_safety_flags_contract.py` (`_validate_safety_flags` scalar-only). Run: `python -m pytest backend/tests/phase10 -x -q`.

---

## Shared Patterns

### Threshold provenance tagging (D-07 — Pitfall 3)
**Source:** `analysis/kismam.py:19-21, 60-66` (`[ASSUMED]` / `[CITED]` inline tags + `[[scoring-redesign-must-generalize-no-overfit]]` citation)
**Apply to:** `safety_flags.py` module header and every threshold constant. Absolute joint cutoffs (knee >5°, elbow >10°) cite external literature in the comment; relative cutoffs cite reference-anchor / KISMAM tol=20°. NEVER "matches our 13 videos."

### Frozen dataclass + `__post_init__` enum guard
**Source:** `analysis/force_signals.py:401-437` (`StabilityMetric`), enum tuples `_SEVERITY_LEVELS` / `_METRIC_CONFIDENCES`
**Apply to:** `SafetyFlag` dataclass. `@dataclass(frozen=True)`, `field(default_factory=list)`, validate enums in `__post_init__`, raise `ValueError` with the `f"X must be one of {ENUM}, got {self.x!r}"` message shape.

### Firestore nested-array scoped validator
**Source:** `firestore_admin.py:104` (`_validate_dict_only_scalars`), `:223` (`_validate_force_signals_report`), wired at `:917-921`
**Apply to:** `_validate_safety_flags` + its `complete_analysis` call site. Keep every `SafetyFlag` field scalar (Pitfall 1). Generic `_validate_flat_dict_no_nested_array` would mishandle `list[dict]`.

### Contract 3-mirror lockstep
**Source:** `analysis.ts:1018` ↔ `models.py:465` re-export ↔ `contract.md:994` §9
**Apply to:** `SafetyFlag` type added to all three simultaneously; reuse existing `SeverityLevel` / `ExperienceLevel` / `SkillLevel` enums rather than redefining.

### Graceful conditional-render + spec-citing comments (RN)
**Source:** `result.tsx:1151` (`length > 0 &&` omit-when-empty), `AccuracyLimitBadge.tsx:32` (`if (!visible) return null`), file-top block comment citing UI-SPEC
**Apply to:** `InjuryRiskSection` (omit when no flags — no reassurance text), `InjuryRiskFlagCard`. Tokens only, no hardcoded colors/spacing.

### `_dataclass_to_camel_case_dict` → result-dict assembly
**Source:** `pipeline/app.py:3468` (`force_signals_dict = _dataclass_to_camel_case_dict(force_signals_report)`)
**Apply to:** flattening `list[SafetyFlag]` → `result["safetyFlags"]` (scalar-only camelCase dicts).

---

## No Analog Found

None. Every file in this phase has a strong in-repo analog (this is a net-new layer built entirely from existing substrate; RESEARCH confirms zero new packages).

The single genuinely novel piece is the **D-05 cross-product hyperextension direction math** inside `safety_flags.py` — it has no code analog (RESEARCH Pattern 3 supplies the algorithm; it consumes `to_coco17_array` 3D coords from `inputs.keypoints_4ch`). The *module/dataclass/test scaffolding* around it still follows the analogs above; only the geometry body is new.

## Metadata

**Analog search scope:** `backend/shared/python/sunity_shared/analysis/`, `backend/shared/python/sunity_shared/{firestore_admin,models}.py`, `backend/functions/pipeline/app.py`, `backend/tests/phase08`/`phase09`, `app/src/types/analysis.ts`, `app/src/app/analysis/result.tsx`, `app/src/components/AccuracyLimitBadge.tsx`, `app/src/theme/colors.ts`, `docs/contract.md`
**Files scanned:** 12 source files + 2 test-dir listings
**Pattern extraction date:** 2026-06-29
