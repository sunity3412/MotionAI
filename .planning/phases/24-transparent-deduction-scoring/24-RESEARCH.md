# Phase 24: 투명 감점-합산 채점 엔진 - Research

**Researched:** 2026-06-24
**Domain:** Scoring engine refactor (band-cap → transparent deduction-tally) anchored in IPSF Code of Points; pure-Python numpy algorithm core inside the shared Lambda/RunPod pipeline
**Confidence:** HIGH on existing-code facts (read directly) and IPSF deduction structure (NotebookLM, authoritative). MEDIUM-LOW on the recommended penalty-curve FORM (it is a design recommendation that *diverges* from IPSF's actual fixed-deduction model — flagged below).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **ND-01 (엔진 교체):** `score = baseline(100) − Σ(per-criterion measured-deviation × explicit-rule deduction)`. REMOVE `SEVERITY_CAP` + `apply_downward_cap` (severity→fixed-ceiling). The resulting number (50, 70, whatever) is a tally output, **not a band**. The point is the report exposes the deduction breakdown. ([[scoring-must-be-transparent-deduction-tally]])
- **ND-03 (감점 규칙 anchor = geometric tolerance expansion):** Expand `dimensions.py` tolerance + per-unit penalty (`_LINE_TOL_DEG` / `_PENALTY_PER_DEG=1.2`, Phase 19) to ALL dimensions (angle / line / distance notches·levels). **Same functional form, single rule, same slope for every video** (curve-fit ban). Within tolerance (small deviation) = 0 deduction.
- **ND-04 (criterion 묶음 + IPSF 상한):** (a) Correlated joints grouped into ONE IPSF criterion measured once (both legs = "leg extension/line" one criterion → no 30+30 double-count). (b) Each criterion's deduction = deviation→tolerance→curve, **capped at that fault's IPSF severity weight**. (c) criterion deductions are **summed** (no averaging — prevents the pre-Phase-19 dilution bug). **→ supersedes 20-D05 "worst-pose dominates" with a summation structure.** The IPSF cap is a **fault-type rule** (video-invariant, traceable), NOT the forbidden **final-score band**. Final score has no ceiling/floor except 0.
- **ND-05 (baseline = 100):** baseline = the coach/athlete the user chose to learn from = 100 for that user (now 정은지, generalizes to any coach). **IPSF-registered official moves → IPSF judging criteria are the baseline.** Consistent with 20-D07 3-branch ((1)IPSF official→IPSF judging / (2)unregistered+coach→coach compare / (3)neither→validity gate). Per-move baseline geometry ([[output-needs-baselined-quantification-layer]]: kip-up=floor / aerial=pole-vertical·hip-line) is the measurement foundation. Mode3 (reference-free) = session-to-session delta of absolute IPSF/criterion metrics ([[mode3-progress-not-similarity]]).
- **ND-02 (Gemini 강등):** Gemini NEVER produces a score. It only points at **where to measure / what fault type**. Score = measurement + rule. Existing `gemini_vision_scorer.assess_fault_severity` already emits score 0 / severity enum only → reinterpret severity enum from "cap input" to "measured-target pointer + criterion identifier".
- **ND-06 (매핑 강제):** Design goal = every Gemini-pointed fault converts to a geometric measurement term (angle / distance notch·level / line deviation) and gets deducted. Visible-but-uncovered = a **coverage gap log** (temporary, dev-only) + 0 deduction — **NEVER an arbitrary band injection**. Shipping product must not have "visible but 0-deduction".
- **ND-07 (eval 게이트):** Remove case-by-case expected-score manifest (moderate≤75 / major=50 = curve-fit). New gates = (1) **traceability** (every −point reverse-derivable from a named deviation + named rule), (2) **monotonicity** (deviation↑ → score↓, zero inversions), (3) **determinism** (same input = same breakdown; temp 0 + caching), (4) **generalization** (unseen + above-cutoff sensitivity set, both false-positive AND false-negative). 정은지 95~100 is a **result, not a target**.

### Claude's Discretion
- Exact curve form / tolerance width / IPSF severity-weight mapping formula (research/plan + IPSF CoP lookup + eval; curve-fit ban — anchor = geometric tolerance + IPSF weights only).
- Report deduction-breakdown UX strength/format (follow-up UI phase + Figma; backend does compute + store only).
- Exact criterion-group definition (which joints = one IPSF criterion) (plan + technique profile + IPSF criterion data).

### Deferred Ideas (OUT OF SCOPE)
- App display/rendering of the breakdown (`result.tsx` / coach-report) = follow-up UI phase. This phase = backend compute + store only.
- Top-end discrimination (within-20° good vs perfect) = separate phase.
- Self vision-model fine-tuning (Phase 22) — the "measured-target / fault-type" labels collected here are its training set; keep the measurement-term definitions consistent with that label schema.
- sensitivity set construction (unseen + above-cutoff) = ND-07 generalization-gate input asset; collection is separate (same as Phase 18 Deferred).
</user_constraints>

<phase_requirements>
## Phase Requirements

Phase requirement IDs are **TBD — to be created in the plan** (CONTEXT: "plan 에서 신설 — SCORE-09 흡수 + 신규"). Suggested IDs the planner can mint, each traced to a locked decision:

| Suggested ID | Description | Research Support |
|----|-------------|------------------|
| SCORE-09 | Replace `SEVERITY_CAP`+`apply_downward_cap` band layer with deduction-tally engine | ND-01; vision_veto.py L65/L104/L89 are the removal targets; engine integrates at `_apply_vision_veto` site in `_process` (app.py:3130) |
| SCORE-10 | Per-criterion deduction rule (geometric tolerance + single-slope curve, all dimensions) | ND-03; `dimensions._LINE_TOL_DEG`/`_PENALTY_PER_DEG`, `kismam.overall_score` over-tol accumulation = starting point |
| SCORE-11 | Criterion grouping + per-fault-type IPSF cap, summed (no avg) | ND-04; IPSF "Clean Lines/Extension = one collective criterion covering both limbs" (NotebookLM, see §IPSF) |
| SCORE-12 | Gemini role demotion — severity enum reinterpreted as measure-target + criterion id, never a score | ND-02; `gemini_vision_scorer.VisionVerdict` already score-free |
| SCORE-13 | Per-move baseline branch (floor / pole_vertical / hip_line) as 1st-class measurement input | ND-05; `vision_veto.FramePairMeasurementContext.baseline_kind` (BASELINE_KINDS) already exists |
| SCORE-14 | Measurable-fault mapping table (Gemini fault → geometric term) + coverage-gap log | ND-06; `vision_veto.fault_key_from_difference`, `_keypoint_set_for`, `fault_joint_deficits_from_differences` |
| SCORE-15 | Deduction-breakdown record computed + stored (contract lockstep), Firestore nested-array safe | ND-02 backend portion; `models.VISION_VETO_KEYS` + `analysis.ts VisionVeto` |
| SCORE-16 | New eval gates (traceability / monotonicity / determinism / generalization) replacing band asserts | ND-07; `backend/evals/phase18/assert_baseline.py` is the replacement target |
</phase_requirements>

## Summary

Phase 24 surgically replaces ONE layer in an otherwise production-wired scoring path. The current scoring assembles `overall = dimensions.overall_from_dimensions(dimension_scores)` (a `min` of core angle/line dims) and then `_apply_vision_veto` lowers it to `min(overall, SEVERITY_CAP[severity])` using a Gemini-derived severity enum and three hardcoded ceilings (minor=90/moderate=75/major=50). belle has rejected those ceilings philosophically: a fixed final-score band is human judgment injected per-video and defeats the purpose of an objective AI. The replacement is a transparent tally: start at baseline 100, and for each IPSF execution criterion, convert the *measured* geometric deviation (already produced by the Phase 23 quantification layer — angle deltas + body-relative notches) into a deduction via a single video-invariant rule, cap each criterion's deduction at its IPSF fault-type weight, sum them, and store the full breakdown.

The most important research finding (HIGH confidence, NotebookLM IPSF Code of Points) reshapes the plan: **real IPSF deductions are FIXED FLAT per occurrence (not proportional to deviation magnitude), have NO per-fault-type cap (only a global −25.0 technical cap), and use binary pass/fail per element.** This means ND-03's "per-degree proportional curve" and ND-04's "per-fault-type IPSF cap" are *engineering interpretations that diverge from literal IPSF*, chosen because they make the tally **monotonic and traceable** (belle's actual gates) where literal IPSF fixed-flat deductions would not give monotonicity. The good news: IPSF strongly supports ND-04's criterion grouping — "Clean Lines / Full Extension" is explicitly judged as ONE collective criterion across both legs/both arms, not left+right separately, which directly cures belle's −60 runaway concern. The tolerance values (20° split tolerance, fully-extended geometry) are genuine IPSF facts.

**Primary recommendation:** Build a new pure module `sunity_shared/analysis/deduction_engine.py` that consumes the Phase 23 quantification output (`VisionQuantificationResult.angleDeltas` + `bodyRelativeNotches`) plus the IPSF criterion grouping, emits a `DeductionBreakdown` (list of per-criterion records: measured value, baseline, deviation, applied rule, −points, IPSF anchor citation), and computes `final = max(0, 100 − Σ capped per-criterion deductions)`. Wire it at the exact site `_apply_vision_veto` currently mutates `overallScore` (app.py:3130), preserving collect→coach→quantification ordering. Use a **piecewise-linear, dead-zone + single-slope + per-criterion-cap** curve form (recommendation, NOT IPSF fact — tag `[ASSUMED]`). Replace `assert_baseline.py`'s expected-verdict asserts with traceability/monotonicity/determinism gates; keep generalization deferred to the sensitivity set.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Geometric measurement (angle deltas, notches) | ML algorithm core (`fault_zoom`/`vision_veto.build_quantification_result`) | — | Phase 23 output; deterministic keypoint+baseline math. Consumed, not rebuilt. |
| Fault localization / criterion id | Gemini adapter (`gemini_vision_scorer`) | ML core (FaultKey mapping) | ND-02 — Gemini points at what/where; never scores. |
| Deduction rule + summation | ML algorithm core (NEW `deduction_engine.py`, pure numpy) | — | Pure, unit-testable, no AWS/Gemini. Same path Lambda+RunPod. |
| Criterion grouping (which joints = 1 criterion) | ML core (technique profile + new grouping table) | IPSF data fixture | ND-04; IPSF judges Clean Lines as one collective criterion. |
| Baseline geometry selection (floor/pole/hip) | ML core (`FramePairMeasurementContext.baseline_kind`) | technique recognizer | ND-05; per-move 1st-class. |
| Engine integration / orchestration | Pipeline (`pipeline/app.py::_process`) | RunPod server (reuses `_process`) | 분기 0, 코드 1벌. Single seam at the old veto site. |
| Breakdown persistence | Firestore Admin (`firestore_admin.complete_analysis`) | contract (`models.py`↔`analysis.ts`) | Nested-array ban → flat or list-of-flat-dicts. |
| Breakdown display | Follow-up UI phase (`app/src/app/analysis/result.tsx`) | — | OUT OF SCOPE this phase. |

## Standard Stack

No new external packages. This is an internal refactor of pure-Python numpy code inside the existing shared pipeline.

### Core (existing, reused)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | >=1.26,<3 (Lambda/dev), >=1.26,<2.0 (RunPod) | All deduction math (deltas, accumulation, clamp) | Already the numeric backbone of `kismam`/`dimensions`/`features`; pure-fn convention |
| pytest | >=8,<9 | Unit + eval gates | `backend/requirements-dev.txt`; existing `backend/tests/test_*.py` |
| PyYAML | (dev/runtime, used by criteria loader) | IPSF criterion-group fixture if stored as YAML | `judging_data/*.yaml` precedent (`ref-*.yaml`, `fitness_norms_kspo.yaml`) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `deduction_engine.py` module | Extend `kismam.overall_score` in place | In-place keeps one file but mixes the old per-joint-avg semantics with the new criterion-grouped tally → harder to keep monotonicity test isolated. New pure module is cleaner and matches the adapter-boundary convention. Recommend NEW module that `kismam`/`dimensions` can delegate to. |
| IPSF criterion grouping as code constant | YAML fixture in `judging_data/` | YAML matches `ref-*.yaml`/`criteria/*.yaml` precedent and lets belle adjust grouping without code change; code constant is simpler to unit-test. Recommend code constant first (small, ~6 criteria) with the option to externalize later. |

**Installation:** None — no new dependencies.

## Package Legitimacy Audit

Not applicable — this phase installs **zero** external packages. It is an internal refactor using already-vendored `numpy` / `pytest` / `PyYAML`. No `npm`/`pip`/`cargo` additions. (slopcheck step skipped: no candidate packages.)

## Architecture Patterns

### System Architecture Diagram

```
S3 ObjectCreated → SQS → pipeline._process  (shared Lambda CPU-fallback / RunPod GPU)
                                │
        ┌───────────────────────┴───────────────────────────────────────────┐
        │ angles (RTMW) ── dimensions / kismam ── dimension_scores            │
        │                                   │                                 │
        │              overall = overall_from_dimensions(dim_scores)  ◄─ today: min-of-core
        │                                   │
        │   _collect_vision_fault_context (Gemini, 1 call) ──► VisionFaultContext
        │       · select_worst_frame_candidates / alignment gate              │
        │       · assess_fault_context (still-pair) ──► verdict + supported_differences + FaultKeys
        │                                   │                                 │
        │   _build_vision_quantification_result ──► VisionQuantificationResult │
        │       · angleDeltas (frame-specific)                                │
        │       · bodyRelativeNotches (baseline_kind: floor/pole/hip)  ◄── MEASUREMENT INPUT
        │                                   │                                 │
        │  ╔══════════════════════════════ PHASE 24 REPLACES HERE ═══════════╗ │
        │  ║ OLD: _apply_vision_veto → min(overall, SEVERITY_CAP[severity])  ║ │
        │  ║ NEW: deduction_engine.tally(                                    ║ │
        │  ║        quantification, fault_context, criterion_groups,         ║ │
        │  ║        baseline_kind, technique_profile)                        ║ │
        │  ║      → DeductionBreakdown(records[], final = max(0,100−Σcaps))  ║ │
        │  ╚═════════════════════════════════════════════════════════════════╝ │
        │                                   │                                 │
        │   result['overallScore'] = breakdown.final                          │
        │   result['deductionBreakdown'] = breakdown.to_records()             │
        │   (_apply_score_suppression for MODE_SELF preserved)                │
        └────────────────────────────────── firestore_admin.complete_analysis ┘
```

### Recommended Project Structure
```
backend/shared/python/sunity_shared/analysis/
├── deduction_engine.py     # NEW — pure tally: deviation→rule→cap→sum. numpy only.
├── ipsf_criteria.py (or .yaml fixture)  # NEW — criterion grouping + per-fault IPSF weights
├── vision_veto.py          # EDIT — REMOVE SEVERITY_CAP/apply_downward_cap/PROVENANCE.
│                           #        KEEP worst_pose_timestamp, FaultKey, quantification,
│                           #        FramePairMeasurementContext, body_relative_notches.
├── dimensions.py           # KEEP tolerance constants; engine reads _LINE_TOL_DEG etc.
├── kismam.py               # KEEP score_from_deviation; engine may delegate accumulation here
├── fault_zoom.py / gemini_vision_scorer.py  # KEEP (measurement input / fault pointer)
backend/functions/pipeline/app.py  # EDIT — replace _apply_vision_veto body / call site
backend/evals/phase24/   # NEW — traceability/monotonicity/determinism asserts (replaces phase18 band asserts)
```

### Pattern 1: Deduction tally (replaces band cap)
**What:** baseline 100 minus the sum of per-criterion capped deductions.
**When to use:** as the single overall-score producer after dimensions + quantification.
**Example (recommended skeleton — curve form is `[ASSUMED]`):**
```python
# Source: derived from kismam.overall_score (existing accumulation) + IPSF criterion grouping
# [ASSUMED] curve form — see Open Questions / IPSF divergence note.
def tally(criterion_measurements, criterion_groups) -> DeductionBreakdown:
    records = []
    total = 0.0
    for crit in criterion_groups:                       # ND-04 (a): one measure per criterion
        dev = aggregate_deviation(crit, criterion_measurements)  # e.g. max over grouped joints
        over = max(0.0, dev - crit.tolerance_deg)        # ND-03 dead-zone (no deduction in-tol)
        raw = over * crit.slope                          # single slope, all videos (curve-fit ban)
        capped = min(raw, crit.ipsf_cap)                 # ND-04 (b): per-fault-type IPSF cap
        total += capped                                  # ND-04 (c): SUM, never average
        records.append(DeductionRecord(
            criterion=crit.id, measured=dev, baseline=crit.baseline,
            deviation=over, rule=crit.rule_id, points=-round(capped, 1),
            ipsf_anchor=crit.ipsf_citation,
        ))
    return DeductionBreakdown(records=records, final=max(0, round(100.0 - total)))
```

### Anti-Patterns to Avoid
- **Final-score band (forbidden):** any `min(final, K)` / `max(final, K)` for K≠0. The ONLY clamp is `max(0, …)`. (ND-01, belle gate.)
- **Re-deriving severity→ceiling:** do not reintroduce `SEVERITY_CAP` under a new name. Severity enum is now a *criterion pointer*, not a number.
- **Averaging across joints/criteria:** reintroduces the pre-Phase-19 dilution bug (a major fault averaged away). SUM only. (ND-04c.)
- **Per-joint summation without grouping:** left-leg + right-leg both bent = double-count → belle's −60 runaway. Group correlated joints into one criterion first. (ND-04a, IPSF "one collective criterion".)
- **Curve-fit to 6 pairs:** slope/tolerance/cap values must come from IPSF/geometry, never tuned so the 6 jeongeunji pairs hit target scores. (`[[scoring-redesign-must-generalize-no-overfit]]`.)
- **Gemini producing a number:** `_SCORE_PATTERN` leak guard already exists in `gemini_vision_scorer`; keep percent/score-free. (ND-02.)
- **Concurrent eval:** `_process` is global-shared → eval/sweep SERIAL only. (`[[pipeline-not-concurrency-safe-eval-serial]]`.)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deviation → 0..100 mapping | New gaussian/curve | `kismam.score_from_deviation` (z=dev/tol) | Already shared by `dimensions`; consistent scale; NaN-safe (returns 0 on non-finite) |
| Frame-specific angle deltas | Re-extract from angles | `vision_veto.build_quantification_result` → `angleDeltas` | Phase 23 same-frame deterministic output |
| Body-relative distance measurement | New cell/notch math | `vision_veto.body_relative_notches` + `FramePairMeasurementContext` | Deterministic floor/pole/hip baseline; percent-free; Phase 23 done |
| Worst-pose frame selection | New key-moment picker | `vision_veto.worst_pose_timestamp` / `select_worst_frame_candidates` | Reused, key_moments-based |
| Fault → keypoint/criterion mapping | New NLP on Korean body_part | `vision_veto.fault_key_from_difference` / `_keypoint_set_for` / `fault_joints_from_differences` | canonical FaultKey vocabulary, locked enums |
| Hold-window selection for representative pose | New windowing | `dimensions._select_window` | Single source — drift guard (Codex HIGH-2 precedent) |

**Key insight:** Phase 23 already produced the entire deterministic *measurement* substrate. Phase 24 is almost purely a *rule + summation + serialization* layer on top — resist rebuilding measurement.

## Runtime State Inventory

> This is a refactor/replace phase. Categories answered explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing Firestore analysis docs carry `visionVeto` with `severity`/`capApplied` and `overallScore` computed by the old band path. New docs will carry `deductionBreakdown` + a band-free `overallScore`. | Code change only — new docs use new shape. **No migration of old docs** (pilot; results are re-runnable). App must tolerate docs without `deductionBreakdown` (legacy) — keep field OPTIONAL in contract. |
| Live service config | `GEMINI_VISION_VETO_ENABLED` env toggle (Lambda + RunPod Pod env) gates the whole veto/quantification collection. Phase 24 engine should ride the SAME toggle (or a renamed one). If renamed, Lambda env + Pod env must be re-set. | Decide in plan: reuse `GEMINI_VISION_VETO_ENABLED` (no env change) vs introduce `DEDUCTION_ENGINE_ENABLED` (requires belle to set Lambda env + Pod env — [[user-beginner-stepwise]], do via CLI). **Recommend reuse** to avoid env drift. |
| OS-registered state | None — no Task Scheduler / launchd / pm2 entries reference scoring constants. Verified: scoring lives entirely in repo Python. | None. |
| Secrets/env vars | No secret names change. Gemini key (`/sunity/motion/gemini-api-key`) and RunPod token unchanged — engine adds no new secret. | None. |
| Build artifacts | Lambda layer (`sunity_shared` → `/opt/python`) must be rebuilt+deployed after editing `vision_veto.py`/adding `deduction_engine.py` (`sam build --use-container` + `sam deploy`). Pod must `git pull` the new module ([[gsd-pod-work-push-first]]). | `sam build --use-container` + deploy; Pod `git pull`; re-run eval on Pod. |

**The canonical question — after every repo file is updated, what runtime still has the old behavior cached?** The deployed Lambda layer and the running RunPod Pod both hold the OLD `vision_veto.py`. Both must be redeployed/pulled. No DB-stored score-rule cache exists (rules are code constants).

## Common Pitfalls

### Pitfall 1: Treating the IPSF "cap" as belle's forbidden band
**What goes wrong:** Implementer reads "IPSF cap" and reintroduces a final-score ceiling.
**Why:** The word "cap" is overloaded. ND-04's cap is **per-criterion / per-fault-type** (e.g., "leg-extension fault can deduct at most −X"), applied BEFORE summation. belle's banned band is on the **final overall score**.
**How to avoid:** Caps live inside `tally()` per criterion record; the only operation on `final` is `max(0, …)`. Add a test asserting no constant ceiling on `final`.
**Warning signs:** any literal near the return of `tally` other than `0` and `100`.

### Pitfall 2: Per-degree slope presented as IPSF fact
**What goes wrong:** Writing "1° = −X pts per IPSF" — it is NOT. IPSF deductions are fixed-flat per occurrence, not proportional (NotebookLM, HIGH confidence).
**Why:** ND-03's proportional curve is an *engineering* choice to get monotonicity (belle's actual gate), which literal IPSF fixed-flat would violate.
**How to avoid:** Tag every slope/tolerance/cap numeric as `[ASSUMED]` unless it is the 20° split tolerance / fully-extended geometry (those ARE IPSF). Comment the divergence (mirror `kismam.py`'s existing `[ASSUMED] _PENALTY_PER_DEG` precedent).
**Warning signs:** a comment claiming IPSF mandates a per-degree value.

### Pitfall 3: Double-counting correlated joints
**What goes wrong:** Summing left_knee + right_knee deductions when both are bent the same way → −60 runaway (belle's stated fear).
**Why:** IPSF judges "Clean Lines / Full Extension" as ONE collective criterion across both limbs (NotebookLM, HIGH).
**How to avoid:** Aggregate grouped joints to ONE deviation per criterion (e.g., max or representative) before applying the rule. Group table is the ND-04 deliverable.
**Warning signs:** number of deduction records > number of distinct IPSF criteria.

### Pitfall 4: Coverage gap silently becoming a band
**What goes wrong:** A Gemini-pointed fault with no geometric rule yields 0 deduction and the implementer "fixes" it by injecting a flat penalty.
**Why:** ND-06 forbids arbitrary penalty; the honest temporary state is 0 + coverage-gap log.
**How to avoid:** When a fault has no mapped measurement term, emit a `coverageGap` audit entry (fault type + reason) and 0 deduction. Eval gate counts coverage gaps (design goal: 0 at ship).
**Warning signs:** a deduction with `rule=None` but `points<0`.

### Pitfall 5: Determinism loss via Gemini sampling
**What goes wrong:** Same video yields different breakdowns run-to-run (Phase 18 exact-score drift).
**Why:** Gemini severity is sampled (N=`VISION_VETO_SAMPLES`, rank-median). The *measurement* is deterministic; the *fault pointer* may vary.
**How to avoid:** Score depends on deterministic geometry; Gemini only selects WHICH criterion. Cache verdict (temp 0 + existing severity cache). Determinism gate runs the same cached input twice and asserts identical breakdown.
**Warning signs:** monotonicity/determinism gate flaky across reruns.

## Code Examples

### Existing accumulation core to delegate to (the summation foundation)
```python
# Source: backend/shared/python/sunity_shared/analysis/kismam.py:213 (overall_score)
# 100 에서 시작해 관절별 허용오차 초과분(over = max(0, dev - tol))을 누적 감점.
total_penalty = 0.0
for a in assessments:
    over = max(0.0, dev - tol[a.key])
    total_penalty += over * w[a.key] * _PENALTY_PER_DEG   # _PENALTY_PER_DEG=1.2 [ASSUMED]
return max(0, min(100, int(round(100.0 - total_penalty))))
# Phase 24: same shape, but (1) grouped per criterion, (2) per-criterion ipsf_cap before sum,
# (3) inputs from quantification angleDeltas/notches not raw kismam deviations.
```

### Existing per-criterion measurement input (Phase 23 output consumed by the engine)
```python
# Source: backend/shared/python/sunity_shared/analysis/vision_veto.py:497 (body_relative_notches)
# 각 항목: {keypoint, student_notches, reference_notches, delta_notches, baseline_kind, source='geometry'}
# + build_quantification_result → angleDeltas (frame-specific, percent-free)
```

### Old band cap to delete (the supersede target)
```python
# Source: backend/shared/python/sunity_shared/analysis/vision_veto.py:104 (apply_downward_cap) — REMOVE
cap = SEVERITY_CAP.get(severity)   # SEVERITY_CAP{minor:90,moderate:75,major:50,none:None}
if cap is None: return overall
return min(overall, cap)           # ← the forbidden band. Phase 24 deletes this.
```

## State of the Art

| Old Approach | Current (Phase 24) Approach | When Changed | Impact |
|--------------|------------------------------|--------------|--------|
| `min(overall, SEVERITY_CAP[severity])` fixed ceilings (Phase 20-04 spec_anchored) | `100 − Σ(per-criterion capped deduction)` transparent tally | This phase (2026-06-24) | Final score becomes an explainable tally output, not a band; report exposes −X −Y −Z = N |
| Gemini severity feeds a numeric cap | Gemini severity = criterion pointer only | This phase | ND-02; score = measurement + rule |
| `kismam.overall_score` per-joint accumulation (avg-free already, Phase 19) | criterion-grouped accumulation with IPSF cap | This phase | ND-04 cures −60 runaway + dilution |
| `assert_baseline.py` case-by-case expected verdict/score | traceability/monotonicity/determinism gates | This phase | ND-07; removes curve-fit manifest |

**Deprecated/outdated by this phase:**
- `vision_veto.SEVERITY_CAP`, `apply_downward_cap`, `SEVERITY_CAP_PROVENANCE` — removed.
- `backend/evals/phase18/assert_baseline.py` band asserts (moderate≤75/major=50) — replaced by phase24 gates (keep phase18 fixtures as fault-label/regression source, retire the score-band asserts).
- The 23-03 `moderate≤75` regression subset — corrected by this phase (per CONTEXT canonical refs).

## IPSF Domain Findings (NotebookLM — anchored, do not invent)

> Notebook: **96b061e8-bb7c-41c5-8606-8ceef2ce1aa3** "IPSF Rules and Advanced Strength Pole Moves Guide" (70 sources, IPSF Code of Points 2021–2024 / 2025–2027). All claims below are `[CITED: NotebookLM IPSF CoP]` unless marked otherwise.

### 1. Deduction structure (ND-04 cap question)
- Deductions are a **strictly categorized fixed-point system**: Singular (deducted every occurrence) + Overall (once). `[CITED]`
- **No per-fault-type cap on execution deductions** — "If an athlete performs 15 movements with micro-bent knees, they are penalized −0.2 fifteen times." `[CITED]`
- The ONLY ceiling is the **total technical-deduction cap of −25.0 points** (poor execution + falls + balance + missing elements accumulate to this). `[CITED]`
- Per-occurrence values: Clean lines / Extension / Posture / Knee-toe alignment = **−0.2** each; Poor presentation / poor transition / loss of balance = −0.5; Slip = −1.0; Fall = −3.0; Missing/unrecognizable element = −3.0; Form errors capped at −1.0 (once-off). `[CITED]`
- **Implication for ND-04:** A literal "per-fault-type IPSF cap" does NOT exist in IPSF. The plan's per-criterion cap is therefore an **engineering interpretation** `[ASSUMED]` — recommend mapping the *global* −25 cap and the relative per-occurrence weights (−0.2 vs −0.5 vs −3.0) into per-criterion ceilings on the 0..100 scale, so a single criterion cannot zero the score but severe categories (fall-equivalent) weigh far more than line errors. This honors IPSF's *relative weighting* while giving the monotonic, bounded behavior belle wants.

### 2. Magnitude scaling (ND-03 curve question)
- IPSF deductions do **NOT scale with fault magnitude** — fixed flat per occurrence, binary pass/fail per element ("a judge does not decide small vs large fall"). `[CITED]`
- **Implication for ND-03:** A *proportional per-degree curve is a deliberate divergence from literal IPSF*, justified because belle's gate is **monotonicity** (deviation↑ → score↓), which fixed-flat deductions cannot provide for a continuous measurement pipeline. Tag the curve `[ASSUMED]`. The one genuinely IPSF-anchored piece is the **binary 0-point element-fail** at the split threshold (already in `dimensions.line_score`: `<160° → 0`, `[CITED: 19-IPSF §A 트랙1]`).

### 3. Criterion grouping (ND-04a — cures −60 runaway)
- **Clean Lines / Full Extension = ONE collective criterion covering both upper AND lower limbs together** ("legs and arms," fingers and toes). "If an athlete bends both knees … treated as ONE occurrence of a Clean Lines / Extension fault, rather than double-deducting left then right." `[CITED]` — **direct domain support for ND-04a.**
- **Knee-toe alignment (pointed toes):** lower-limb region kneecap→big-toe straight line. `[CITED]`
- **Posture / Extension:** torso, spine, neck, shoulders judged as one postural unit (central axis). `[CITED]`
- **Recommended criterion groups** (for the ND-04 grouping table, anchored): (1) Leg extension/line (both knees, ankle→hip), (2) Arm extension/line (both elbows, wrist→shoulder), (3) Split angle (inner-thigh hip→knee lines, both legs as one), (4) Toe/foot point + knee-toe alignment, (5) Posture/torso (spine/neck/shoulders), (6) Pole contact/grip (proximity). Maps onto the existing 8 JOINT_KEYS + `FaultKey` keypoint_set vocabulary (`arm/shoulder/leg/hip/head_neck/grip/torso/line`).

### 4. Fully-extended geometry + split tolerance (ND-03/05 measurement)
- **Arms fully extended = wrist→shoulder straight line; legs = ankle-bone→hip-bone straight line; hyperextension counts as fully extended.** `[CITED]` — matches `dimensions.extension_deviation` (180° target on EXTEND joints).
- **Split: 180° target, ±20° tolerance → 160° minimum; measured by inner-thigh hip→knee lines; must hold from ALL perspectives (3D).** `[CITED]` — confirms `_LINE_TOL_DEG=20`, `_SPLIT_FAIL_THRESHOLD_DEG=160`.
- If a "Fully Extended" element is micro-bent → element not awarded (0). `[CITED]`

### 5. Per-move baseline geometry (ND-05)
- IPSF does **NOT** define a universal mathematical per-move reference angle; baseline varies by category and uses anatomical anchors. `[CITED]`
  - **Flips / floor-based:** hips are the anchoring point; floor is the baseline (full rotation = hips pass over head). `[CITED]` → maps to `baseline_kind="floor"` / `"hip_line"`.
  - **Splits:** self-referential inner-thigh hip→knee line. `[CITED]`
  - **Horizontal (Iron X / flatline):** 90° to vertical pole, ±20°. `[CITED]` → `baseline_kind="pole_vertical"`.
  - **Inversions:** purely anatomical (hips over head), NO mathematical pole-axis angle. `[CITED]`
- **"kip-up" is an unrecognized colloquial studio move** — the CoP gives it no geometric criteria; for floor starts the floor is the baseline. `[CITED]` (Consistent with `[[phase15-recognizer-student-video-line-none]]` — unregistered moves fall to the absolute/floor baseline.) Confirms ND-05's existing `BASELINE_KINDS = ("floor","pole_vertical","hip_line")` is the right enum; the per-move→baseline mapping is the recognizer/branch's job, not new geometry.

## Open Questions

1. **ND-03 curve form (the single biggest design call).**
   - Known: IPSF is fixed-flat (no proportional scaling). belle's gate is monotonicity. `_PENALTY_PER_DEG=1.2` + dead-zone already exist.
   - Unclear: exact form — pure linear-above-tolerance, piecewise (linear then saturating toward the per-criterion cap), or step+linear hybrid (binary 0-fail at 160° split + linear elsewhere).
   - Recommendation `[ASSUMED]`: **dead-zone + single linear slope per criterion, saturating at the per-criterion IPSF-relative cap**, PLUS the IPSF binary 0-fail for split <160° (the one CoP-mandated discontinuity). Linear gives provable monotonicity; saturation prevents runaway; single slope across all dimensions/videos satisfies the curve-fit ban. Derive slope from the existing 1.2 precedent, NOT from the 6 pairs. Confirm exact slope per dimension in plan + eval (monotonicity gate, not score-target gate).

2. **Per-criterion cap derivation.**
   - Known: IPSF has no per-fault-type cap, only global −25 and relative per-occurrence weights (−0.2 line vs −3.0 fall).
   - Recommendation `[ASSUMED]`: set per-criterion caps proportional to IPSF relative weights scaled to 0..100 (e.g., line/extension criteria modest caps, fall/major-collapse criteria large), so the sum can reach low scores via multiple criteria but no single line error zeros the score. Document the scaling as `[ASSUMED]` interpretation of the −25 global cap.

3. **Engine toggle.** Reuse `GEMINI_VISION_VETO_ENABLED` (no env change, recommended) vs new `DEDUCTION_ENGINE_ENABLED` (env re-set on Lambda + Pod). Decide in plan.

4. **Deduction record schema final shape** (contract lockstep) — see Data Contract below; confirm key names with `analysis.ts` reviewer.

## Data Contract (deduction breakdown record)

Firestore forbids nested arrays. A `deductionBreakdown` as a **list of flat dicts** is allowed (top-level array of maps, each map's values are scalars). This mirrors how `visionVeto.angleDeltas` / `bodyRelativeNotches` are already stored (list of flat dicts). Recommended shape (lockstep `models.py` ↔ `analysis.ts` ↔ `docs/contract.md`):

```ts
// app/src/types/analysis.ts (new, OPTIONAL for legacy-doc compat)
export interface DeductionRecord {
  criterion: string;          // e.g. 'leg_extension' (IPSF criterion id)
  measuredValue: number;      // measured geometry (deg or notches)
  baseline: number;           // 100-baseline reference value
  deviation: number;          // over-tolerance amount used for the rule
  ruleId: string;             // named rule (traceability gate)
  points: number;             // negative deduction (e.g. -9)
  unit: 'deg' | 'notch';
  ipsfAnchor?: string;        // CoP citation / 'engineering_interpretation'
  source: 'geometry';         // never 'vision_score'
}
export interface DeductionBreakdown {
  baseline: 100;
  records: DeductionRecord[];
  final: number;              // max(0, 100 - Σ capped points)
  coverageGaps?: { faultType: string; reason: string }[];  // ND-06 honest temp state
}
// AnalysisResult gains:  deductionBreakdown?: DeductionBreakdown;
```
Python mirror in `models.py` as `DEDUCTION_RECORD_KEYS` / `DEDUCTION_BREAKDOWN_KEYS` tuples (precedent: `VISION_VETO_KEYS`). `overallScore` semantics change from "min-of-core (possibly capped)" to "`deductionBreakdown.final`" — update the `analysis.ts:440` comment.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | engine + eval | ✓ | 3.14.5 local / 3.12 Lambda runtime | — |
| numpy | tally math | ✓ (vendored) | per requirements | — |
| pytest | unit + gate tests | ✓ | >=8,<9 | — |
| RunPod Pod (CUDA) | real-video eval (NLF/RTMW GPU) | conditional | per HANDOFF Pod env | CPU fallback = NaN (flow-only, not real scores) |
| Gemini API key (SSM `/sunity/motion/gemini-api-key`) | fault-pointer collection in eval | conditional | — | engine runs on stored quantification without live Gemini for pure unit/gate tests |
| `nlm` CLI (NotebookLM) | IPSF lookups (done in this research) | ✓ | authenticated | — |

**Missing/blocking with no fallback:** Real end-to-end eval requires the Pod (GPU) up and Gemini credits ([[gemini-credits-depleted-2026-06-20]] — verify credits before sweep). Pure deduction-engine unit/gate tests need NEITHER (they consume stored/synthetic quantification). **Recommend: build the engine + gates pure-first (Pod-free), then Pod-gate.**

## Validation Architecture

> nyquist_validation = true (config). This section drives VALIDATION.md generation. The 4 ND-07 gates REPLACE the phase18 case-by-case band asserts.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 |
| Config file | none (no pytest.ini/pyproject) — discovery via `backend/tests/` + `backend/tests/conftest.py` |
| Quick run command | `cd backend && python -m pytest tests/test_deduction_engine.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests -q` |
| Eval gate (pure) | `python backend/evals/phase24/assert_gates.py` (exit 0 = PASS) |
| Eval gate (Pod, serial) | `python backend/scripts/sweep_phase15.py --mode all --trigger direct-process --pair-sequential` then assert |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| SCORE-09 | band cap removed; final has no ceiling but 0 | unit | `pytest tests/test_deduction_engine.py::test_no_final_band -x` | ❌ Wave 0 |
| SCORE-10 | dead-zone + single slope; in-tol = 0 deduction | unit | `pytest tests/test_deduction_engine.py::test_deadzone_and_slope -x` | ❌ Wave 0 |
| SCORE-11 | grouped criteria summed, no double-count, per-criterion cap | unit | `pytest tests/test_deduction_engine.py::test_criterion_grouping_no_runaway -x` | ❌ Wave 0 |
| SCORE-12 | Gemini severity never enters score arithmetic | unit | `pytest tests/test_deduction_engine.py::test_score_independent_of_severity_enum -x` | ❌ Wave 0 |
| SCORE-13 | baseline_kind selects floor/pole/hip measurement | unit | `pytest tests/test_deduction_engine.py::test_baseline_branch -x` | ❌ Wave 0 (reuse vision_veto fixtures) |
| SCORE-14 | unmapped fault → coverage gap + 0, never penalty | unit | `pytest tests/test_deduction_engine.py::test_coverage_gap_no_band -x` | ❌ Wave 0 |
| SCORE-15 | breakdown record shape + Firestore-flat (no nested array) | unit | `pytest tests/test_deduction_engine.py::test_breakdown_serializes_flat -x` | ❌ Wave 0 |
| SCORE-16 | 4 gates pass on fixture set | gate | `python backend/evals/phase24/assert_gates.py` | ❌ Wave 0 |

### The 4 ND-07 gates (how they sample/verify)
- **Traceability gate:** for every record, assert `final == 100 − Σ(records.points)` exactly AND each record has non-null `ruleId` + named `criterion` + finite `measuredValue`/`deviation`. Sample = every analysis in the fixture set. (belle: "명명백백하면 의외 점수도 OK" — this IS that gate.)
- **Monotonicity gate:** synthetic sweep — for one criterion, feed increasing deviation (e.g. 0,10,20,…,90°) holding others fixed; assert `final` is non-increasing (zero inversions). Pure, no Pod. Sample = each criterion independently.
- **Determinism gate:** run the same stored quantification input through `tally()` twice (and the cached Gemini verdict path twice); assert byte-identical breakdown. Replaces Phase 18 exact-score drift. Sample = full fixture set ×2.
- **Generalization gate (partial / deferred input):** false-positive (elite/correct videos must stay high — e.g. 정은지 correct ≥ ~95 as a *result* not target) AND false-negative (fault videos must drop) on the phase18 6 pairs PLUS an above-cutoff unseen sensitivity set. Sensitivity-set collection is Deferred (asset not built) — gate runs on available pairs now, full generalization when the set exists. SERIAL only (`--pair-sequential`).

### Sampling Rate
- **Per task commit:** `pytest tests/test_deduction_engine.py -x -q` (< 5 s, pure).
- **Per wave merge:** full `pytest tests -q` + `python backend/evals/phase24/assert_gates.py`.
- **Phase gate:** all unit + traceability/monotonicity/determinism green pure-first; then Pod serial sweep for generalization before `/gsd-verify-work`. belle final TestFlight verification last (Phase 15, Pod kept up).

### Wave 0 Gaps
- [ ] `backend/tests/test_deduction_engine.py` — covers SCORE-09..15
- [ ] `backend/evals/phase24/assert_gates.py` — traceability/monotonicity/determinism (replaces phase18 band asserts)
- [ ] `backend/shared/python/sunity_shared/analysis/deduction_engine.py` + criterion-group fixture — the module under test
- [ ] Synthetic quantification fixtures (angleDeltas/notches at swept deviations) for monotonicity — no Pod needed
- [ ] Framework install: none (pytest already present)

## Security Domain

> security_enforcement = true (ASVS L1). This phase is internal scoring math with no new I/O surface; most ASVS categories N/A.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new auth surface; pipeline triggered by SQS (existing) |
| V3 Session Management | no | — |
| V4 Access Control | no | Firestore Admin write path unchanged (`firestore_admin`) |
| V5 Input Validation | yes | Engine inputs (quantification deltas, criterion config) must be finite-checked; reuse `score_from_deviation` NaN-safety; reject malformed criterion config (raise, like `_faultkey_validate`) |
| V6 Cryptography | no | No crypto; no secrets added |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| NaN/Inf deviation poisoning the tally (int(round(NaN)) crash) | Tampering/DoS | `np.isfinite` guard → treat as max-deviation or skip (existing `kismam`/`overall_score` precedent) |
| Gemini-controlled text steering a score (prompt-injection via fault label) | Tampering | ND-02 — Gemini text only selects criterion; score is pure geometry. `_SCORE_PATTERN` leak guard stays. |
| Coverage-gap exploited to mask faults | Repudiation | Coverage gaps logged + counted by eval gate (auditable), 0-deduction not a hidden band |
| Non-determinism enabling inconsistent scores | Repudiation | Determinism gate + temp 0 + caching |

## Project Constraints (from CLAUDE.md / backend CLAUDE.md / memory)
- Tech stack fixed; no new libs. Korean for user-facing copy/comments, English identifiers. No emojis. No slop. Cite specs by section shorthand (`19-IPSF §A`, `contract.md §4`).
- Pure-function algorithm core (no boto3/Gemini/network in `deduction_engine.py`); adapters lazy-imported (existing convention).
- Single scoring path, two runtimes — integrate in ONE place (`_process`), 분기 0 코드 1벌.
- Firestore nested-array ban → flat / list-of-flat-dicts only.
- Contract lockstep: change `analysis.ts` + `models.py` + `docs/contract.md` together.
- Objectivity: no human score labels as ground truth; deductions only from measured deviation + explicit rule.
- Eval/sweep SERIAL only (`_process` not concurrency-safe).
- Pod ops run by Claude (SSH/sweep/env); belle approves production + domain calls. Push before Pod follows.
- Plan needs external cross-AI review for a change this large ([[cross-ai-plan-review-good]], HANDOFF) — `plan_review_convergence=true` in config.

## Assumptions Log
| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Per-degree proportional curve (single slope) for ND-03 | Open Q1, IPSF §2 | IPSF is fixed-flat; if belle wants literal IPSF binary deductions, monotonicity gate is unmeetable — surface in discuss before locking |
| A2 | Per-criterion cap derived from IPSF *relative* weights scaled to 0..100 (IPSF has no per-fault cap, only global −25) | ND-04, IPSF §1 | Wrong scaling could make scores too lenient/harsh; eval generalization gate catches gross errors |
| A3 | Recommended 6 criterion groups (leg/arm/split/toe/posture/grip) | IPSF §3 | If grouping wrong, double-count or miss; anchored to IPSF "collective criterion" text — low risk but confirm with technique profile |
| A4 | Reuse `GEMINI_VISION_VETO_ENABLED` toggle (no env rename) | Runtime State, Open Q3 | If renamed without setting Pod+Lambda env, engine silently no-ops |
| A5 | No migration of legacy Firestore docs (pilot, re-runnable) | Runtime State | If belle wants historical re-score, add a backfill task |
| A6 | `deductionBreakdown` stored as list-of-flat-dicts is Firestore-legal | Data Contract | Mirrors existing `angleDeltas`; low risk |
| A7 | Slope value reused/derived from existing `_PENALTY_PER_DEG=1.2` (itself already `[ASSUMED]`) | Code Examples | Inherits the existing assumption; must NOT recalibrate on 6 pairs |

## Sources

### Primary (HIGH confidence)
- **Existing code (read directly):** `vision_veto.py` (SEVERITY_CAP L65 / apply_downward_cap L104 / PROVENANCE L89 / FaultKey / quantification / FramePairMeasurementContext / body_relative_notches), `dimensions.py` (_LINE_TOL_DEG / _PENALTY_PER_DEG / line_score / overall_from_dimensions), `kismam.py` (overall_score / score_from_deviation), `fault_zoom.py`, `gemini_vision_scorer.py` (VisionVerdict score-free / assess_fault_context), `pipeline/app.py` (_collect_vision_fault_context / _apply_vision_veto / _apply_score_suppression / _process wiring), `technique.py` (TechniqueProfile / expects_extension), `skeleton.py` (JOINT_KEYS), `models.py` (VISION_VETO_KEYS / dimension keys), `analysis.ts` (VisionVeto union / AnalysisResult), `backend/evals/phase18/{pairs.yaml,assert_baseline.py,eval18_serial_baseline.json}`, `.planning/phases/19-vision-hybrid/19-IPSF-DEDUCTION-NOTES.md`, `.planning/config.json`.
- **NotebookLM IPSF CoP (96b061e8-bb7c-41c5-8606-8ceef2ce1aa3):** deduction structure (fixed-flat, no per-fault cap, global −25, per-occurrence values), criterion grouping (Clean Lines = one collective criterion both limbs), fully-extended geometry + 20°/160° split tolerance, per-move baselines (floor/pole-vertical/hip-line; kip-up unrecognized → floor). conversation_id 84d5c7b2-9a71-44d1-9513-5d7071279264.

### Secondary (MEDIUM confidence)
- Project memory items cited inline ([[scoring-must-be-transparent-deduction-tally]], [[scoring-redesign-must-generalize-no-overfit]], [[mode3-progress-not-similarity]], [[pipeline-not-concurrency-safe-eval-serial]], [[phase23-pod-eval-gate-fail-2026-06-24]], etc.).

### Tertiary (LOW confidence)
- None — every claim is code-verified or NotebookLM-cited. Curve-form/cap-scaling recommendations are explicitly tagged `[ASSUMED]` (engineering choices, not facts).

## Metadata
**Confidence breakdown:**
- Existing-code facts: HIGH — read the actual files this session.
- IPSF deduction structure / criterion grouping / tolerances: HIGH — authoritative NotebookLM CoP, multi-source citations.
- Penalty-curve FORM + per-criterion cap scaling: LOW-MEDIUM — deliberate engineering divergence from literal IPSF; tagged `[ASSUMED]`, must be confirmed in discuss/plan + eval (monotonicity, not score-target).
- Data contract shape: MEDIUM — mirrors existing `visionVeto` list-of-flat-dicts precedent; confirm names with reviewer.

**Research date:** 2026-06-24
**Valid until:** ~30 days (stable internal code; IPSF CoP versioned 2021–2027 so domain facts are durable). Re-check Pod/Gemini credit status before any eval sweep.
