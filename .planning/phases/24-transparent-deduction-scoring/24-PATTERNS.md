# Phase 24: 투명 감점-합산 채점 엔진 - Pattern Map

**Mapped:** 2026-06-24 (revised post-Codex-review: 5(+gap) criteria, linear slope, OBJECT contract)
**Files analyzed:** 9 (3 NEW, 5 EDIT, 2 contract-lockstep EDIT)
**Analogs found:** 9 / 9 (all in-repo — this is a refactor, not greenfield)

This phase is a surgical refactor of the existing Python ML scoring pipeline. Every new file has a strong in-repo analog because the deduction-tally engine reuses the established pure-function / contract-lockstep / eval-gate conventions. The single seam is `_apply_vision_veto` in `pipeline/app.py::_process` (the band cap), replaced by `deduction_engine.tally(...)`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/analysis/deduction_engine.py` (NEW) | service (pure algorithm core) | transform | `kismam.py` (`overall_score`) + `dimensions.py` (`line_score`) | exact (role + flow) |
| `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py` (NEW — code constant; YAML optional) | config (grouping/weight table) | transform (lookup) | `dimensions.py` constants (`_LINE_TOL_DEG`/`_SPLIT_FAIL_THRESHOLD_DEG`) | role-match |
| `backend/tests/test_deduction_engine.py` (NEW) | test | transform | `backend/tests/test_kismam.py` | exact |
| `backend/evals/phase24/assert_gates.py` (NEW) | test (eval gate) | batch | `backend/evals/phase18/assert_baseline.py` | exact |
| `backend/shared/python/sunity_shared/analysis/vision_veto.py` (EDIT — remove band) | service (pure core) | transform | self (Phase 20-01) | exact |
| `backend/functions/pipeline/app.py` (EDIT — replace `_apply_vision_veto` seam) | controller (orchestration) | event-driven (SQS) | self (`_process`) | exact |
| `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` (EDIT — reframe severity docstrings, no code change to schema) | adapter (Gemini) | request-response | self (`VisionVerdict`) | exact |
| `backend/shared/python/sunity_shared/models.py` (EDIT — add `DEDUCTION_*_KEYS`) | model (contract) | — | `VISION_VETO_KEYS` (lines 110-116) | exact |
| `app/src/types/analysis.ts` (EDIT — add `DeductionBreakdown`) | model (contract) | — | `VisionVeto` union (lines 389-400) | exact |

## Pattern Assignments

### `deduction_engine.py` (NEW — service, pure transform)

**Analog:** `backend/shared/python/sunity_shared/analysis/kismam.py::overall_score` (lines 213-243) — this is the deduction-accumulation foundation. Copy its shape, then layer criterion-grouping + per-criterion cap on top.

**Module-header docstring pattern** (copy from `vision_veto.py:1-41`): open with `"""..."""` stating purpose + numpy-only constraint + cited section. The new module MUST state "numpy 외 의존이 0 — boto3/Gemini/네트워크/firestore import 절대 금지" verbatim-style (matches `vision_veto.py:3`).

**`from __future__ import annotations`** at top (every analysis module: `vision_veto.py:43`, `kismam.py`, `dimensions.py`).

**Core accumulation pattern to copy** (`kismam.py:233-243`):
```python
total_penalty = 0.0
for a in assessments:
    dev = float(a.deviation_deg)
    # WR-02: 측정 불가(NaN/Inf) 편차는 건너뛴다 — int(round(NaN)) ValueError 차단.
    if not np.isfinite(dev):
        continue
    over = max(0.0, dev - tol[a.key])          # dead-zone (ND-03): tol 안이면 감점 0
    total_penalty += over * w[a.key] * _PENALTY_PER_DEG   # _PENALTY_PER_DEG=1.2 [ASSUMED]
return max(0, min(100, int(round(100.0 - total_penalty))))
```
**Phase 24 divergence (must implement):**
(1) group joints per criterion BEFORE the loop (one deviation per criterion, not per joint — cures −60 runaway).
(2) LINEAR points mapping — `raw = over * crit.slope`, `slope = kismam._PENALTY_PER_DEG` reused VERBATIM (single shared slope, NOT re-fit per criterion). MEDIUM-2: do NOT delegate the deviation→points mapping to `kismam.score_from_deviation` (that is a gaussian z=dev/tol mapping with a different distribution + cap behavior). `score_from_deviation` is referenced ONLY as the scale/NaN-safe precedent, not as the points function.
(3) `capped = min(raw, crit.ipsf_cap)` BEFORE adding to total.
(4) the ONLY final clamp is `max(0, ...)` — REMOVE the `min(100, ...)` upper clamp's role as a band (100 is the baseline, not a ceiling on the result; `final = max(0, round(100 + Σ record.points))` where `points` is SIGNED NEGATIVE — equivalently `max(0, round(100 - total))`). See Anti-Patterns.
(5) explicit `quantification unavailable` fallback FIRST: `final = dimension_overall` + ONE traceable fallback record (criterion='dimension_overall_fallback', ruleId='quantification_unavailable_dimension_overall', points=round(dimension_overall-100,1) signed-negative, unit='score_delta', deviationSource='dimension_overall') so `100 + Σ points == final` holds on the fallback path too (MEDIUM-1). NEVER reset to 100.

**Dead-zone + 0-fail discontinuity to reuse** (`dimensions.py::line_score` lines 261-267): the one genuinely IPSF-anchored discontinuity — `if any(a < _SPLIT_FAIL_THRESHOLD_DEG for a in rep_angles): return 0`. The slope/cap numbers are `[ASSUMED]`; the 160° split 0-fail and 20° tolerance are `[CITED: 19-IPSF §A 트랙1]`.

**Frozen dataclass for the record value-object** (pattern from `gemini_vision_scorer.py:125` `@dataclass(frozen=True) class VisionVerdict`): define `@dataclass(frozen=True) class DeductionRecord` and `DeductionBreakdown`. `DeductionBreakdown.to_dict()` emits the OBJECT `{baseline, records, final, coverageGaps, fallback}` (HIGH-1); `to_records()` is the internal `to_dict()["records"]` helper.

---

### `ipsf_criteria.py` (NEW — config, grouping table)

**Analog:** `dimensions.py` module-level constants (lines 158-176) — SCREAMING_SNAKE_CASE constants with cited tolerance values and `[CITED]`/`[ASSUMED]` tags inline.

**Pattern to copy** (`dimensions.py:164-176`):
```python
# 허용오차(도). z=dev/tol 가우시안 → tol 만큼 벗어나면 점수 ~61.
_LINE_TOL_DEG = 20.0      # 완전 신전(180°) 대비 부족분. IPSF 각도 허용오차 20° 기준.
# [CITED: 19-IPSF-DEDUCTION-NOTES §A 트랙1].
_SPLIT_FAIL_THRESHOLD_DEG = 160.0
```

**Phase 24 criteria set (canonical — substrate-honest, MEDIUM-4 corrected):** define FIVE criteria scoped to what the substrate can actually measure today:
- `leg_extension` (both knees / ankle→hip line; angle substrate; ipsf_absolute)
- `arm_extension` (both elbows / wrist→shoulder; angle substrate; ipsf_absolute)
- `split_angle` (inner-thigh, both legs as one; angle + 160° binary fail; ipsf_absolute)
- `line` (clean_lines — the COLLECTIVE 180°-deficit criterion `dimensions.line_score`/`extension_deviation` compute over ALL EXTEND joints; ipsf_absolute; profile-gated on `profile.expects_extension` → empty joint_expectations yields None → 0 contribution, ND-06 honest 0)
- `body_relative_reach` (HIGH-4 — the ONE `reference_relative` criterion; consumes `bodyRelativeNotches.delta_notches` (baseline-relative) for the `_NOTCH_REACH_KEYPOINTS` hand/knee reach; unit `notch`; activated only for hand/knee reach faults; this is what makes per-move `baseline_kind` a genuine scoring substrate, ND-05)

These map onto `skeleton.JOINT_KEYS` + the `FaultKey` keypoint_set vocabulary (`FAULT_KEYPOINT_SETS`, imported from vision_veto — do NOT hand-relist) + `_NOTCH_REACH_KEYPOINTS`. Tag every slope/cap as `[ASSUMED]`, tolerance/160°-split as `[CITED]`. The single slope is `kismam._PENALTY_PER_DEG=1.2` reused as a LINEAR per-unit slope (MEDIUM-2 — NOT a gaussian).

**FUTURE coverage-gap candidates (NOT criteria — MEDIUM-4):** `toe_alignment`, `posture`/torso, `pole_contact`/grip, `head_neck`, `shoulder`, `hip` have NO measurable substrate today. They live in `COVERAGE_GAP_KEYPOINT_SETS` (the five FaultKey keypoint_sets {head_neck, grip, torso, shoulder, hip}) as TRACKED deferred gaps with a deferral reason, NOT as criteria. Do NOT open a criterion the substrate cannot feed (ND-06 honesty). `criterion_for_fault_key` is TOTAL over the 8 keypoint_sets: mapped {leg, arm, line} → criteria, gap {head_neck, grip, torso, shoulder, hip} → allow-listed reason; partition (∪ == all 8, ∩ == ∅). Research recommends code constant first (small table), YAML fixture later (`judging_data/*.yaml` precedent).

---

### `test_deduction_engine.py` (NEW — test)

**Analog:** `backend/tests/test_kismam.py` (lines 1-60). Copy its structure exactly — these are the monotonicity/dead-zone/single-fault-dominance tests Phase 24 needs.

**Imports + AWS-free header** (`test_kismam.py:1-7`):
```python
"""... — 결정적 검증. AWS 불필요."""
import numpy as np
import pytest
from sunity_shared.analysis import kismam
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS, PARTS
```

**Monotonicity test pattern to copy** (`test_kismam.py:19-31`, `test_score_monotonic_decreasing_with_deviation`): sweep deviation past the dead-zone (0/30/60°, all > 20° tol) and assert `s0 > s1 > s2`. This IS the ND-07 monotonicity gate at unit level.

**Dead-zone test** (`test_kismam.py:34-41`, `test_within_tolerance_remains_high`): all-10° (< 20° tol) → score ≥ 90.

**Single-major-fault dominance** (`test_kismam.py:46-57`, `test_single_major_fault_dominates`): one joint at 50°, assert score drops far below the mean-formula value — directional assert, NOT a sweep-target number (`# 보유 sweep 수치 타깃 아님` comment — curve-fit ban). Phase 24 must add: `test_no_final_band`, `test_criterion_grouping_no_runaway`, `test_score_independent_of_severity_enum`, `test_coverage_gap_no_band`, `test_breakdown_serializes_flat` (OBJECT), `test_unavailable_emits_traceable_record` (MEDIUM-1), `test_body_relative_reach_uses_baseline` (ND-05), `test_line_criterion_empty_expectations_zero`, `test_criterion_for_fault_key_total_over_vocab`.

---

### `backend/evals/phase24/assert_gates.py` (NEW — eval gate)

**Analog:** `backend/evals/phase18/assert_baseline.py` (lines 1-70). Copy its structure: pod-free self-consistency checker, `exit 0 = PASS`, accumulate `failures: list[str]`, YAML-import-guard.

**Pattern to copy** (`assert_baseline.py:1-46`):
```python
#!/usr/bin/env python3
"""... eval set — baseline self-consistency 검사 (pod-free).
박제 정신: ... 객관성(D-06): baseline 점수는 채점기 출력 스냅샷(라벨 아님).
exit 0 = PASS, non-zero = FAIL.
"""
from __future__ import annotations
import json, pathlib, sys
try:
    import yaml
except ImportError:
    sys.exit("PyYAML 필요: pip install pyyaml")
_HERE = pathlib.Path(__file__).resolve().parent
def main() -> int:
    failures: list[str] = []
    ...
```
**Phase 24 divergence:** REMOVE the case-by-case expected-verdict/score asserts (`assert_baseline.py:55-70` `expected != verdict`, `f < s` margin — the curve-fit band asserts ND-07 retires). REPLACE with the 4 gates (RESEARCH "The 4 ND-07 gates"): traceability (`final == max(0, round(100 + Σ records.points))` signed-negative + every record has non-null `ruleId`/`criterion`/finite `measuredValue` + a `deviationSource`; the quantification_unavailable fallback record PASSES, MEDIUM-1), monotonicity (synthetic deviation sweep, fixed criterion set, zero inversions), determinism (math + criterion-selection, conditional on verdict cache), generalization (partial — phase18 6 pairs false-pos/false-neg, sensitivity set SKIPPED). Keep phase18 fixtures (`pairs.yaml`) as fault-label source; retire only the score-band asserts. The verify command is the BARE `python evals/phase24/assert_gates.py` (its exit code propagates — MEDIUM-3, no trailing `echo "exit=$?"`).

---

### `vision_veto.py` (EDIT — remove band layer)

**Analog:** self. REMOVE `SEVERITY_CAP` (lines 65-70), `SEVERITY_CAP_PROVENANCE` (lines 89-101), `apply_downward_cap` (lines 104-118), and the band-related docstring section (lines 14-40). KEEP `worst_pose_timestamp`, `fault_joints_from_differences`, `FaultKey`, `_NOTCH_REACH_KEYPOINTS`, `body_relative_notches`, `build_quantification_result`, `FramePairMeasurementContext`, `BASELINE_KINDS`. The file docstring's "비전은 점수를 절대 올리지 않는다" invariant stays in spirit (now: Gemini never produces a number — ND-02).

**The exact code to delete** (`vision_veto.py:104-118`):
```python
def apply_downward_cap(overall: int, severity: str | None) -> int:
    cap = SEVERITY_CAP.get(severity)
    if cap is None:
        return overall
    return min(overall, cap)           # ← the forbidden band. Phase 24 deletes this.
```

**`to_audit_dict` reshape:** signature `(*, final_status, cap_applied=None, ...)` → `(*, final_status, breakdown_final=None, ...)`; emit `tallyFinal` not `capApplied`.

---

### `pipeline/app.py` (EDIT — replace the seam)

**Analog:** self (`_process`). The single integration seam is `_apply_vision_veto` (lines 1971-2150) and its call sites at `_process` (lines 3115-3149). Preserve collect→coach→quantification ordering (comment at 3108-3114).

**Call-site pattern to preserve** (`app.py:3123-3139`): `_build_vision_quantification_result(...)` runs first (Phase 23, KEEP), then the seam. Replace the band mutation with: build the named substrate via `_build_deduction_measured_deviations(...)` (HIGH-3 — extension_deviation/line_score deg + delta_notches, NEVER a 0-100 score as a deviation), call `deduction_engine.tally(quantification, ctx, dimension_overall=..., measured_deviations=<named substrate>, dimension_scores=..., baseline_kind=<string>)` → set `result['overallScore'] = breakdown.final` and `result['deductionBreakdown'] = breakdown.to_dict()` (OBJECT). KEEP `_apply_score_suppression` (MODE_SELF), the `GEMINI_VISION_VETO_ENABLED` toggle (REUSE per A4 — no env rename), and the `vision_fault_context is None` legacy fallback branch. Derive `baseline_kind = _baseline_kind_for_profile(profile)` ONCE at the seam (name/motion_id string-match, NOT category) and thread it as a STRING into both quantification + apply paths (engine never gets the profile — no NameError surface).

**Coach-gate (HIGH-6):** `cap_would_apply = (severity in ("moderate","major"))` — band-free coach-root-cause eligibility (continuity of today's moderate/major trigger, NOT byte-identical legacy; the old form also depended on score-below-cap). `eligible_for_coach` unchanged.

**Mode3 hold semantics preserved** (`app.py:2020-2023`): `if mode == models.MODE_SELF: return _veto_passthrough(score_result, "mode3_held")` — Mode3 still uses absolute-dimension delta, no reference anchor.

---

### `gemini_vision_scorer.py` (EDIT — semantic reframe, docstring-only)

**Analog:** self (`VisionVerdict`, lines 125-141). `assess_fault_severity` already emits `score`-free `VisionVerdict(primary_fault, severity, differences)` — ND-02's demotion is half-built. Phase 24 reframes the three docstrings (L5/L129/L134) that call `severity` an `apply_downward_cap` input → describe it as a CRITERION POINTER (HIGH-5). The objectivity guards STAY: `_SCORE_PATTERN` leak guard (line 113), `score` field permanently absent (line 15), `response_schema` score/overall field-count 0 (line 148). No schema/code change — only the docstring framing changes (in `deduction_engine`/`_process`, severity selects WHICH criterion, never a number). No `apply_downward_cap` string may remain in the docstrings.

---

### `models.py` (EDIT — contract Python side)

**Analog:** `VISION_VETO_KEYS` (lines 110-116) — the exact precedent for a flat-key tuple with a 3-way-lockstep comment block.

**Pattern to copy** (`models.py:70-116`): block comment citing `app/src/types/analysis.ts ... + docs/contract.md §10` 3-way lockstep, then `_KEYS` tuple of scalar field names. Add `DEDUCTION_RECORD_KEYS = ("criterion", "measuredValue", "baseline", "deviation", "ruleId", "points", "unit", "ipsfAnchor", "source", "deviationSource")` and `DEDUCTION_BREAKDOWN_KEYS = ("baseline", "records", "final", "coverageGaps", "fallback")`. Firestore nested-array ban → `records`/`coverageGaps` are lists of flat dicts (mirrors `angleDeltas`/`bodyRelativeNotches`, line 101-105). The breakdown is an OBJECT (HIGH-1). Also: `VISION_VETO_KEYS` `capApplied` → `tallyFinal` (band retired, Task 3).

---

### `app/src/types/analysis.ts` (EDIT — contract TS side)

**Analog:** `VisionVeto` discriminated union (lines 389-400) and `VisionAngleDelta` (line 360) — the precedent for OPTIONAL, list-of-flat-objects, legacy-doc-tolerant contract types.

**Pattern to copy** (`analysis.ts:360,389-400`): add `export interface DeductionRecord { criterion: string; measuredValue: number; baseline: number; deviation: number; ruleId: string; points: number; unit: 'deg' | 'notch' | 'score_delta'; ipsfAnchor?: string; source: 'geometry'; deviationSource: 'ipsf_absolute' | 'reference_relative' | 'dimension_overall'; }` and `export interface DeductionBreakdown { baseline: 100; records: DeductionRecord[]; final: number; coverageGaps?: { faultType: string; reason: string }[]; fallback?: 'quantification_unavailable' | 'gemini_silent'; }`. Add `deductionBreakdown?: DeductionBreakdown` (the OBJECT) to `AnalysisResult` — OPTIONAL for legacy-doc compat (no migration, A5). The `unit`/`deviationSource` unions are EXTENDED with `score_delta`/`dimension_overall` for the MEDIUM-1 fallback record. Update the `overallScore` semantics comment (was "min-of-core possibly capped" → now "`deductionBreakdown.final`"). `capApplied` → `tallyFinal` in VisionVeto (Task 3). `import type` for type-only imports (project convention).

---

## Shared Patterns

### Pure-function algorithm core (no AWS/network/Gemini)
**Source:** `vision_veto.py:3`, `kismam.py`, `dimensions.py`
**Apply to:** `deduction_engine.py`, `ipsf_criteria.py`
numpy is the only import beyond stdlib + sibling `from . import kismam`/`from . import ipsf_criteria`. boto3/Gemini/firestore/network imports forbidden. Heavy deps stay behind the existing adapter boundary; the engine consumes already-computed quantification. Relative imports within the package (`from . import kismam`, `from .skeleton import JOINT_KEYS`).

### NaN/Inf guard before accumulation
**Source:** `kismam.py:236-240`, `overall_score`
**Apply to:** `deduction_engine.tally`
`if not np.isfinite(dev): continue` — non-finite deviation skipped, never poisons the tally (`int(round(NaN))` ValueError). RESEARCH Security V5 + Pitfall mandates this.

### Module docstring cites the spec section
**Source:** every analysis module (`vision_veto.py:1`, `dimensions.py` `[CITED: 19-IPSF §A 트랙1]`)
**Apply to:** all NEW files
`"""..."""` header stating purpose + constraint + cited section shorthand. Tag engineering choices `[ASSUMED]`, IPSF facts `[CITED: 19-IPSF §A]`. Korean for the why, English identifiers, no emojis.

### 3-way contract lockstep
**Source:** `models.py:73` ("3-way lockstep: app/src/types/analysis.ts ... + docs/contract.md §4")
**Apply to:** `models.py` + `analysis.ts` + `docs/contract.md` together
Any deduction-record key change touches all three in one wave. Firestore nested-array ban → records/coverageGaps list-of-flat-dicts only; the breakdown itself is an OBJECT.

### Objectivity — no human/AI score labels as ground truth
**Source:** `gemini_vision_scorer.py:11-15`, `assert_baseline.py:8`
**Apply to:** engine, eval gate, Gemini adapter
Deductions come ONLY from measured deviation + explicit named rule. Gemini text selects a criterion, never a number. `_SCORE_PATTERN` leak guard stays. Eval baselines are scorer-output snapshots, not labels.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | None. Every file has a strong in-repo analog (refactor phase). |

## Metadata

**Analog search scope:** `backend/shared/python/sunity_shared/analysis/`, `backend/functions/pipeline/`, `backend/shared/python/sunity_shared/models.py`, `backend/tests/`, `backend/evals/phase18/`, `app/src/types/analysis.ts`
**Files scanned:** ~12 (read targeted sections of vision_veto.py, kismam.py, dimensions.py, pipeline/app.py, models.py, gemini_vision_scorer.py, test_kismam.py, assert_baseline.py, analysis.ts)
**Pattern extraction date:** 2026-06-24 (revised post-Codex-review)
</content>
