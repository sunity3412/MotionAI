# Phase 24: 투명 감점-합산 채점 엔진 - Pattern Map

**Mapped:** 2026-06-24 (revised post-Codex-review: 5(+gap) criteria, linear slope, OBJECT contract; revised ITERATION 2: criteria_for_fault router, insufficient-reach direction, baselineValue/baselineKind, line/leg no-double-count, artifact-gated structural generalization)
**Files analyzed:** 9 (3 NEW, 5 EDIT, 2 contract-lockstep EDIT)
**Analogs found:** 9 / 9 (all in-repo — this is a refactor, not greenfield)

This phase is a surgical refactor of the existing Python ML scoring pipeline. Every new file has a strong in-repo analog because the deduction-tally engine reuses the established pure-function / contract-lockstep / eval-gate conventions. The single seam is `_apply_vision_veto` in `pipeline/app.py::_process` (the band cap), replaced by `deduction_engine.tally(...)`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/analysis/deduction_engine.py` (NEW) | service (pure algorithm core) | transform | `kismam.py` (`overall_score`) + `dimensions.py` (`line_score`) | exact (role + flow) |
| `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py` (NEW — code constant; YAML optional) | config (grouping/weight table + criteria_for_fault router) | transform (lookup/route) | `dimensions.py` constants (`_LINE_TOL_DEG`/`_SPLIT_FAIL_THRESHOLD_DEG`) + `vision_veto._KEYPOINT_SET_BY_KEYWORD` (the keyword-route precedent) | role-match |
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
(1) SELECT criteria via the PUBLIC `ipsf_criteria.criteria_for_fault(fault_key, supported_difference, measured_deviations)` router (HIGH-1 — split vs leg vs reach vs line is routed on body_part/fault_state + substrate, NOT a keypoint_set map), then group joints per ACTIVATED criterion BEFORE the loop (one deviation per criterion, not per joint — cures −60 runaway).
(2) HIGH-5 cross-criterion exclusion: when a `leg_extension`/`arm_extension` criterion is activated, EXCLUDE its joint substrate from the `line` collective deficit so a single bent joint is not deducted twice (line deducts only the residual line-dominant substrate).
(3) DIRECTION-aware dead-zone (HIGH-2): `over_target` criteria use `over = max(0, dev - tol)`; the `insufficient_reach` criterion (body_relative_reach) uses `shortfall = max(0, reference_notches - student_notches - tol)` ≡ `max(0, -delta_notches - tol)` — a SHORT reach deducts, an over-reach yields 0 (NOT `abs()`, NOT `max(0, delta_notches - tol)`).
(4) LINEAR points mapping — `raw = over * crit.slope`, `slope = kismam._PENALTY_PER_DEG` reused VERBATIM (single shared slope, NOT re-fit per criterion). MEDIUM-2: do NOT delegate the deviation→points mapping to `kismam.score_from_deviation` (that is a gaussian z=dev/tol mapping with a different distribution + cap behavior). `score_from_deviation` is referenced ONLY as the scale/NaN-safe precedent, not as the points function.
(5) `capped = min(raw, crit.ipsf_cap)` BEFORE adding to total.
(6) the ONLY final clamp is `max(0, ...)` — REMOVE the `min(100, ...)` upper clamp's role as a band (100 is the baseline, not a ceiling on the result; `final = max(0, round(100 + Σ record.points))` where `points` is SIGNED NEGATIVE — equivalently `max(0, round(100 - total))`). See Anti-Patterns.
(7) explicit `quantification unavailable` fallback FIRST: `final = dimension_overall` + ONE traceable fallback record (criterion='dimension_overall_fallback', ruleId='quantification_unavailable_dimension_overall', baselineValue=100, points=round(dimension_overall-100,1) signed-negative, unit='score_delta', deviationSource='dimension_overall') so `100 + Σ points == final` holds on the fallback path too (MEDIUM-1). NEVER reset to 100.

**Dead-zone + 0-fail discontinuity to reuse** (`dimensions.py::line_score` lines 261-267): the one genuinely IPSF-anchored discontinuity — `if any(a < _SPLIT_FAIL_THRESHOLD_DEG for a in rep_angles): return 0`. The slope/cap numbers are `[ASSUMED]`; the 160° split 0-fail and 20° tolerance are `[CITED: 19-IPSF §A 트랙1]`.

**Frozen dataclass for the record value-object** (pattern from `gemini_vision_scorer.py:125` `@dataclass(frozen=True) class VisionVerdict`): define `@dataclass(frozen=True) class DeductionRecord` (fields incl. `baseline_value` numeric measurement target + `baseline_kind` str|None — HIGH-3) and `DeductionBreakdown`. `DeductionBreakdown.to_dict()` emits the OBJECT `{baseline, records, final, coverageGaps, fallback}` (HIGH-1, records carrying `baselineValue`/`baselineKind`); `to_records()` is the internal `to_dict()["records"]` helper.

---

### `ipsf_criteria.py` (NEW — config, grouping table + fault-context router)

**Analog:** `dimensions.py` module-level constants (lines 158-176) — SCREAMING_SNAKE_CASE constants with cited tolerance values and `[CITED]`/`[ASSUMED]` tags inline. The router's keyword-substring routing copies `vision_veto._KEYPOINT_SET_BY_KEYWORD` (L233-251) style.

**Pattern to copy** (`dimensions.py:164-176`):
```python
# 허용오차(도). z=dev/tol 가우시안 → tol 만큼 벗어나면 점수 ~61.
_LINE_TOL_DEG = 20.0      # 완전 신전(180°) 대비 부족분. IPSF 각도 허용오차 20° 기준.
# [CITED: 19-IPSF-DEDUCTION-NOTES §A 트랙1].
_SPLIT_FAIL_THRESHOLD_DEG = 160.0
```

**Phase 24 criteria set (canonical — substrate-honest, with direction):** define FIVE criteria scoped to what the substrate can actually measure today, each carrying `deviation_source` ∈ {ipsf_absolute, reference_relative} AND `direction` ∈ {over_target, insufficient_reach}:
- `leg_extension` (both knees / ankle→hip line; angle substrate; ipsf_absolute; over_target)
- `arm_extension` (both elbows / wrist→shoulder; angle substrate; ipsf_absolute; over_target)
- `split_angle` (inner-thigh, both legs as one; angle + 160° binary fail; ipsf_absolute; over_target)
- `line` (clean_lines — the COLLECTIVE 180°-deficit criterion `dimensions.line_score`/`extension_deviation` compute over ALL EXTEND joints; ipsf_absolute; over_target; profile-gated on `profile.expects_extension` → empty joint_expectations yields None → 0 contribution, ND-06 honest 0; HIGH-5: line EXCLUDES substrate already claimed by an activated leg/arm extension criterion — no cross-criterion double count)
- `body_relative_reach` (HIGH-4/HIGH-2 — the ONE `reference_relative` criterion; direction `insufficient_reach`; consumes `bodyRelativeNotches.delta_notches` (baseline-relative) for the `_NOTCH_REACH_KEYPOINTS` hand/knee reach; unit `notch`; scored as `shortfall = max(0, reference_notches − student_notches − tol)` so a SHORT reach deducts and an over-reach does not; activated only for hand/knee reach faults; this is what makes per-move `baseline_kind` a genuine scoring substrate, ND-05)

These map onto `skeleton.JOINT_KEYS` + the `FaultKey` keypoint_set vocabulary (`FAULT_KEYPOINT_SETS`, imported from vision_veto — do NOT hand-relist) + `_NOTCH_REACH_KEYPOINTS`. Tag every slope/cap as `[ASSUMED]`, tolerance/160°-split as `[CITED]`. The single slope is `kismam._PENALTY_PER_DEG=1.2` reused as a LINEAR per-unit slope (MEDIUM-2 — NOT a gaussian).

**PUBLIC router `criteria_for_fault(fault_key, supported_difference, measured_deviations)` (HIGH-1):** a single `keypoint_set`→criterion map CANNOT express `leg`→{leg_extension | split_angle | body_relative_reach} because split/straddle/스플릿/스트래들 all normalize to `keypoint_set="leg"` (vision_veto.py:238-239), as does a knee-reach fault. So the PUBLIC selection API routes on `supported_difference.body_part`/`fault_state` (lowercase substring match, mirroring `_KEYPOINT_SET_BY_KEYWORD`) + the available `measured_deviations`: split→split_angle; knee/leg+bend→leg_extension; elbow/arm+bend→arm_extension; hand/knee+reach-shortfall→body_relative_reach; line/line-dominant→line (excluding leg/arm-claimed substrate, HIGH-5); grip / head_neck / torso / shoulder / hip→coverage-gap sentinel (0 deduction). INVARIANT (ND-02): the router NEVER reads `supported_difference.severity` — activation + points are a pure function of body_part/fault_state + substrate (severity-invariant). The old `criterion_for_fault_key(keypoint_set)` is DEMOTED to an internal `_criterion_for_keypoint_set` total-coverage helper (TOTAL over the 8 keypoint_sets, mapped {leg, arm, line} + gap {head_neck, grip, torso, shoulder, hip}, ∪ == all 8, ∩ == ∅) — it is NOT the selection API (it cannot disambiguate split vs leg vs reach).

**FUTURE coverage-gap candidates (NOT criteria):** `toe_alignment`, `posture`/torso, `pole_contact`/grip, `head_neck`, `shoulder`, `hip` have NO measurable substrate today. They live in `COVERAGE_GAP_KEYPOINT_SETS` (the five FaultKey keypoint_sets {head_neck, grip, torso, shoulder, hip}) as TRACKED deferred gaps with a deferral reason, NOT as criteria. Do NOT open a criterion the substrate cannot feed (ND-06 honesty). Research recommends code constant first (small table), YAML fixture later (`judging_data/*.yaml` precedent).

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

**Single-major-fault dominance** (`test_kismam.py:46-57`, `test_single_major_fault_dominates`): one joint at 50°, assert score drops far below the mean-formula value — directional assert, NOT a sweep-target number (`# 보유 sweep 수치 타깃 아님` comment — curve-fit ban). Phase 24 must add: `test_no_final_band`, `test_criterion_grouping_no_runaway`, `test_score_independent_of_severity_enum`, `test_coverage_gap_no_band`, `test_breakdown_serializes_flat` (OBJECT, baselineValue/baselineKind), `test_unavailable_emits_traceable_record` (MEDIUM-1), `test_body_relative_reach_uses_baseline` (ND-05), `test_reach_insufficient_direction` (HIGH-2), `test_line_criterion_empty_expectations_zero` (ND-06), `test_line_leg_no_cross_double_count` (HIGH-5), `test_criteria_for_fault_selects_split_not_leg` + `test_criteria_for_fault_severity_invariant` (HIGH-1), `test_criterion_for_keypoint_set_total_over_vocab`.

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
**Phase 24 divergence:** REMOVE the case-by-case expected-verdict/score asserts (`assert_baseline.py:55-70` `expected != verdict`, `f < s` margin — the curve-fit band asserts ND-07 retires). REPLACE with the pod-free SYNTHETIC gates (RESEARCH "The ND-07 gates"): traceability (`final == max(0, round(100 + Σ records.points))` signed-negative + every record has non-null `ruleId`/`criterion`/finite `measuredValue` + a `deviationSource` + a numeric `baselineValue`; the quantification_unavailable fallback record PASSES, MEDIUM-1), monotonicity (synthetic deviation sweep, fixed criterion set, zero inversions), determinism (math + criterion-selection, conditional on verdict cache). The phase18 generalization check is ARTIFACT-GATED (HIGH-4): it runs ONLY against the real Pod-generated `backend/evals/phase24/baseline/phase24_breakdowns.json`; if absent it emits `SKIPPED (phase24 breakdown fixture absent)` (NOT a failure) and does NOT fabricate inputs or call synthetic fixtures "phase18-derived". The generalization check is STRUCTURAL not numeric (MEDIUM-1): success member traceable-within-tolerance, fault member strictly larger same-criterion shortfall — NO `≥ 95` numeric bound in the pure gate (that lives in the Pod checkpoint as an OBSERVATION). Keep phase18 fixtures (`pairs.yaml`) as fault-label source; retire only the score-band asserts. The verify command is the BARE `python evals/phase24/assert_gates.py` (its exit code propagates — MEDIUM-3, no trailing `echo "exit=$?"`).

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

**Call-site pattern to preserve** (`app.py:3123-3139`): `_build_vision_quantification_result(...)` runs first (Phase 23, KEEP), then the seam. Replace the band mutation with: build the named substrate via `_build_deduction_measured_deviations(...)` (HIGH-3 — extension_deviation/line_score deg + delta_notches with student/reference notches forwarded for the insufficient-reach shortfall, NEVER a 0-100 score as a deviation), call `deduction_engine.tally(quantification, ctx, dimension_overall=..., measured_deviations=<named substrate>, dimension_scores=..., baseline_kind=<string>)` → set `result['overallScore'] = breakdown.final` and `result['deductionBreakdown'] = breakdown.to_dict()` (OBJECT). Criterion selection is the engine's `criteria_for_fault` router (HIGH-1) — the seam does NOT pre-route by keypoint_set or read severity. KEEP `_apply_score_suppression` (MODE_SELF), the `GEMINI_VISION_VETO_ENABLED` toggle (REUSE per A4 — no env rename), and the `vision_fault_context is None` legacy fallback branch. Derive `baseline_kind = _baseline_kind_for_profile(profile)` ONCE at the seam (name/motion_id string-match, NOT category) and thread it as a STRING into both quantification + apply paths (engine never gets the profile — no NameError surface).

**Coach-gate (HIGH-6):** `cap_would_apply = (severity in ("moderate","major"))` — band-free coach-root-cause eligibility (continuity of today's moderate/major trigger, NOT byte-identical legacy; the old form also depended on score-below-cap). `eligible_for_coach` unchanged.

**Mode3 hold semantics preserved** (`app.py:2020-2023`): `if mode == models.MODE_SELF: return _veto_passthrough(score_result, "mode3_held")` — Mode3 still uses absolute-dimension delta, no reference anchor.

---

### `gemini_vision_scorer.py` (EDIT — semantic reframe, docstring-only)

**Analog:** self (`VisionVerdict`, lines 125-141). `assess_fault_severity` already emits `score`-free `VisionVerdict(primary_fault, severity, differences)` — ND-02's demotion is half-built. Phase 24 reframes the three docstrings (L5/L129/L134) that call `severity` an `apply_downward_cap` input → describe it as a CRITERION POINTER (HIGH-5): severity LOCATES which measured criterion is implicated (via criteria_for_fault on body_part/fault_state) and is never even read for selection. The objectivity guards STAY: `_SCORE_PATTERN` leak guard (line 113), `score` field permanently absent (line 15), `response_schema` score/overall field-count 0 (line 148). No schema/code change — only the docstring framing changes. No `apply_downward_cap` string may remain in the docstrings.

---

### `models.py` (EDIT — contract Python side)

**Analog:** `VISION_VETO_KEYS` (lines 110-116) — the exact precedent for a flat-key tuple with a 3-way-lockstep comment block.

**Pattern to copy** (`models.py:70-116`): block comment citing `app/src/types/analysis.ts ... + docs/contract.md §10` 3-way lockstep, then `_KEYS` tuple of scalar field names. Add `DEDUCTION_RECORD_KEYS = ("criterion", "measuredValue", "baselineValue", "baselineKind", "deviation", "ruleId", "points", "unit", "ipsfAnchor", "source", "deviationSource")` (HIGH-3 — `baselineValue` numeric measurement target + `baselineKind` per-move string, NOT a single ambiguous `baseline`) and `DEDUCTION_BREAKDOWN_KEYS = ("baseline", "records", "final", "coverageGaps", "fallback")` (the breakdown-level `baseline` is the numeric 100 score baseline, distinct from the record-level `baselineValue`). Firestore nested-array ban → `records`/`coverageGaps` are lists of flat dicts (mirrors `angleDeltas`/`bodyRelativeNotches`, line 101-105). The breakdown is an OBJECT (HIGH-1). Also: `VISION_VETO_KEYS` `capApplied` → `tallyFinal` (band retired, Task 3).

---

### `app/src/types/analysis.ts` (EDIT — contract TS side)

**Analog:** `VisionVeto` discriminated union (lines 389-400) and `VisionAngleDelta` (line 360) — the precedent for OPTIONAL, list-of-flat-objects, legacy-doc-tolerant contract types.

**Pattern to copy** (`analysis.ts:360,389-400`): add `export interface DeductionRecord { criterion: string; measuredValue: number; baselineValue: number; baselineKind?: 'floor' | 'pole_vertical' | 'hip_line'; deviation: number; ruleId: string; points: number; unit: 'deg' | 'notch' | 'score_delta'; ipsfAnchor?: string; source: 'geometry'; deviationSource: 'ipsf_absolute' | 'reference_relative' | 'dimension_overall'; }` (HIGH-3 — `baselineValue` numeric target + optional `baselineKind`, no single `baseline` that collides with `DeductionBreakdown.baseline=100`) and `export interface DeductionBreakdown { baseline: 100; records: DeductionRecord[]; final: number; coverageGaps?: { faultType: string; reason: string }[]; fallback?: 'quantification_unavailable' | 'gemini_silent'; }`. Add `deductionBreakdown?: DeductionBreakdown` (the OBJECT) to `AnalysisResult` — OPTIONAL for legacy-doc compat (no migration, A5). The `unit`/`deviationSource` unions are EXTENDED with `score_delta`/`dimension_overall` for the MEDIUM-1 fallback record. Update the `overallScore` semantics comment (was "min-of-core possibly capped" → now "`deductionBreakdown.final`"). `capApplied` → `tallyFinal` in VisionVeto (Task 3). `import type` for type-only imports (project convention).

---

## Anti-Patterns (Phase 24 must NOT reintroduce)

- **Final-score band** (`min(final, K)` / `SEVERITY_CAP` / `apply_downward_cap`): the only clamp is `max(0, …)`. 100 is the baseline, never a ceiling on the result. (ND-01.)
- **Gemini severity in the score arithmetic** or read for criterion selection: severity LOCATES a criterion via `criteria_for_fault` (body_part/fault_state), never a number, never read by the router (ND-02, HIGH-1).
- **Per-joint runaway** (both legs = −60): group correlated joints into ONE criterion before the loop (ND-04a).
- **Averaging criterion deductions** (dilution): SUM, never average (ND-04c).
- **Cross-criterion double-count** (a bent knee deducted in BOTH leg_extension AND line): line excludes leg/arm-claimed substrate (HIGH-5).
- **abs(delta_notches) / over-direction reach** (punishing an over-reach as a fault): reach is insufficient-reach shortfall only (HIGH-2).
- **Gaussian points mapping** (`score_from_deviation` as the points function): LINEAR `raw = over * slope` only; gaussian is referenced only as the NaN-safe/scale precedent (MEDIUM-2).
- **Curve-fitting the 6 정은지 pairs** (numeric ≥95 pure-gate bound, re-fitting slope/cap/tolerance to a target): pure gate is STRUCTURAL; numeric high-score is an OBSERVATION in the Pod checkpoint (MEDIUM-1, [[scoring-redesign-must-generalize-no-overfit]]).
- **Synthetic fixtures masquerading as phase18-derived** (HIGH-4): the generalization check runs only against the real Pod-generated `phase24_breakdowns.json`; SKIPPED if absent.
- **Hardcoded `baseline_kind="hip_line"`** at the seam: derive per-move via `_baseline_kind_for_profile` (BLOCKER B).

---

**Files scanned:** ~12 (read targeted sections of vision_veto.py, kismam.py, dimensions.py, pipeline/app.py, models.py, gemini_vision_scorer.py, technique.py, test_kismam.py, assert_baseline.py, pairs.yaml, analysis.ts)
</content>
