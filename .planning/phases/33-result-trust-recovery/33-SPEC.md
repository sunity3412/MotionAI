# Phase 33: Result Trust Recovery — Scoring Redesign Specification

**Created:** 2026-07-24
**Ambiguity score:** 0.161 (gate: ≤ 0.20)
**Requirements:** 5 locked

> **Scope note:** This SPEC covers the **채점 산식 재설계(scoring redesign)** pivot inserted mid-phase (Wave 6, 33-06). It supersedes the phase-33 premise D-20/D-29 ("채점 산식 무접촉") which belle explicitly reversed on 2026-07-24 ([[scoring-ipsf-deduction-cap-no-zero-pileup]]). It does NOT re-spec the 표현/flip track (A-1~A-7, 33-07~33-16), which remains governed by 33-CONTEXT.md and is blocked on this redesign. The M3 sub-spec `33-M3-SPEC.md` (33-05, alignment) is a separate artifact and is untouched.

## Goal

The overall score changes from **unbounded per-joint deduction accumulation that collapses multi-joint execution faults to 0** to a **two-track IPSF-anchored deduction model**: execution deductions (line/angle deviations) are capped in aggregate at −40 (floor 60), while critical faults (required full-extension not met = element non-recognition) bypass that cap and can drive the score to 0.

## Background

`backend/shared/python/sunity_shared/analysis/deduction_engine.py::tally` computes `final = max(0, round(100 + Σ record.points))` (line 349). Each per-joint record is clamped by `PER_RECORD_DEDUCTION_CAP = 20` and a per-criterion `ipsf_cap = 90`, but **there is no aggregate cap on the summed deductions**. `overallScore = breakdown.final` directly (`backend/functions/pipeline/app.py:2530/2621/2691`).

Verified failure (elbow-twist "다관절 결함" video, candidate shadow re-analysis):
- `dimensionScores = {angle: 58, stability: 73}` — the angle dimension itself scores 58.
- `deductionBreakdown`: 8 joint records (both shoulders/elbows/hips/knees, each `(deviation − 20°) × 1.2`, all individually under the −20 per-record cap) sum to **−111.4** → `final = max(0, 100 − 111.4) = 0`.

belle's eyeball: the failed video genuinely has many multi-joint faults, but **0 is excessive** — it conflicts with our own angle=58 and with IPSF, where execution deductions total-cap at −25.0 on the ~56–63 IPSF scale (per-routine total, not per-joint), while full-extension non-recognition zeroes the *element* separately. "IPSF로 가야 공감을 준다 (0점 뭉침 = 이탈)."

The redesign closes this by introducing an aggregate execution-deduction cap and separating a critical-fault track — WITHOUT touching the substrate (재추출 33-03 / 백필 33-04 / M3 33-05, all verified good).

## Requirements

1. **Aggregate execution-deduction cap**: The summed execution-track deductions cannot reduce the score below floor 60.
   - Current: `final = max(0, 100 + Σ points)` with no aggregate cap; execution deductions sum without bound (elbow-twist Σ = −111.4 → 0)
   - Target: execution-track deductions are aggregated then capped at −40 before subtraction: `capped_exec = min(40, Σ|execution points|)`. A video with only execution faults (no critical fault) scores ≥ 60
   - Acceptance: the elbow-twist fixture (execution-only, Σ raw ≈ −111.4) yields `overallScore == 60`; a fixture with small execution deductions (Σ raw < 40) is unchanged from the pre-cap value (cap not reached)

2. **Critical-fault track bypasses the cap and can reach 0**: Required full-extension not met (element non-recognition) is a separate, uncapped track.
   - Current: full-extension 0-fail (split_angle < 160°) produces at most −20 (per-record clamp), indistinguishable in floor from ordinary execution faults; there is no track separation
   - Target: critical deductions (required-extension element below its recognition threshold) are summed separately and NOT subject to the −40 execution cap: `final = max(0, 100 − min(40, Σ|execution|) − Σ|critical|)`; a video that fails a required full-extension element can reach 0
   - Acceptance: a fixture with a full-extension 0-fail element scores below 60 (and can reach 0 when critical + execution deductions ≥ 100); a fixture with the same execution deviations but NO critical fault scores ≥ 60

3. **IPSF-proportional cap provenance**: The −40 execution cap is derived from IPSF, not fixture-tuned.
   - Current: no aggregate cap exists; the only IPSF-cited constants are tolerance 20° / split 160° 0-fail (`ipsf_criteria.py` [CITED]); slope/per-criterion caps are [ASSUMED]
   - Target: the −40 cap is documented as the IPSF execution-deduction total-cap (−25 on the ~60-pt IPSF execution scale ≈ 42% of range → −40 on our 0–100) — a single project-level constant, NOT re-fit per fixture ([[scoring-redesign-must-generalize-no-overfit]])
   - Acceptance: the cap is a single named constant with an IPSF-provenance comment; no per-fixture or per-criterion variant of the aggregate cap exists in code

4. **Transparency preserved**: The capped tally remains a reversible, itemized deduction breakdown.
   - Current: `DeductionBreakdown` emits per-record `points`, `rawPoints`/`capApplied` for record-level clamps; `100 + Σ points == final` traceability holds
   - Target: aggregate execution cap and critical-track separation are represented transparently in `deductionBreakdown` (e.g. capped-execution marker + track labels) so the final score remains reconstructable from the breakdown ([[scoring-must-be-transparent-deduction-tally]]); engine stays numpy-pure and deterministic (no boto3/Gemini/network)
   - Acceptance: for every re-verified fixture, `overallScore` is reconstructable from `deductionBreakdown` alone (execution-cap + critical-sum arithmetic checks out); `deduction_engine` imports remain numpy-only

5. **Structural-invariant re-verification across all 6 fixtures**: The redesign generalizes without per-fixture curve-fitting.
   - Current: only elbow-twist was shadow-re-analyzed; separation floor (gate2) was discarded as fixture-specific curve-fit ([[judgment-must-not-fixate-on-recent-fixture]])
   - Target: all 6 fixtures re-analyzed and judged against structural invariants only (see Acceptance Criteria), never per-fixture target scores
   - Acceptance: all 5 structural invariants below hold across all 6 fixtures simultaneously

## Boundaries

**In scope:**
- Aggregate execution-deduction cap (−40 / floor 60) in `deduction_engine.tally`
- Two-track separation: execution track (capped) vs critical/full-extension-non-recognition track (uncapped, floor 0)
- IPSF-provenance documentation of the −40 constant
- Transparent `deductionBreakdown` representation of the cap + tracks
- Structural-invariant re-verification across all 6 fixtures (requires a fresh Pod for GPU re-analysis)

**Out of scope:**
- Substrate (재추출 33-03 / 백필 33-04 / M3 33-05) — verified good, not re-run ([[RESUME-phase33-scoring-redesign-pivot-2026-07-24]])
- flip (33-07) and score-dependent 표현 track (A-1~A-7, 33-08~33-16) — blocked until this redesign is verified; flip explicitly on hold
- gate2 separation floor — discarded (fixture curve-fit + Gemini variance)
- Fault visualization (crop position / illustration) — independent of scoring, may proceed in parallel
- Re-tuning tolerance (20°), slope (1.2), per-record cap (−20), or per-criterion cap (90) — unchanged; only the NEW aggregate cap + track split are added
- Per-fixture target scores / expected-range calibration — banned as overfit ([[scoring-redesign-must-generalize-no-overfit]])

## Constraints

- `deduction_engine` must stay numpy-pure and deterministic — no boto3/Gemini/network/firestore imports (existing invariant, engine header)
- The −40 cap is a single project-level constant with IPSF provenance — not re-fit per fixture or per criterion
- 정은지 (elite) videos must remain 95–100 — the cap must not move near-zero-deduction scores ([[score-spec-95-100-elite-vision-fix]])
- The pipeline has exactly one scoring seam (`분기 0, 코드 1벌`) — Lambda and RunPod share `_process`; the change lands in `deduction_engine` only
- Re-verification is serial per fixture — `/analyze` concurrent calls contaminate ([[pipeline-not-concurrency-safe-eval-serial]]); requires belle GPU greenlight + fresh EU-RO-1 4090 Network Storage Pod (D-30: all Pods currently terminated)
- Contract mirror: if `deductionBreakdown` shape changes, update `app/src/types/analysis.ts` + `models.py` together

## Acceptance Criteria

Structural invariants — must ALL hold across ALL 6 fixtures simultaneously (no per-fixture target scores):

- [ ] **INV-1 Elite floor**: 정은지 / well-executed videos score ≥ 95
- [ ] **INV-2 Execution floor**: videos with execution faults only (no critical/full-extension miss) score ≥ 60 and never below 60
- [ ] **INV-3 Critical descent**: videos with a required full-extension element not met score < 60 (and reach 0 when critical + execution deductions ≥ 100)
- [ ] **INV-4 Discrimination preserved**: within the fixture set, better-executed videos score strictly higher than worse-executed ones (monotone margin preserved; no rank inversions vs. eyeball ordering)
- [ ] **INV-5 Monotone deduction**: a strictly worse posture (larger measured deviation) never yields a higher score than a milder one — the deduction is monotone in measured deviation
- [ ] **INV-6 Reconstructability**: for every fixture, `overallScore` is reconstructable from `deductionBreakdown` via `max(0, 100 − min(40, Σexec) − Σcritical)`
- [ ] **INV-7 elbow-twist anchor**: the elbow-twist failure fixture (execution-only, Σ raw ≈ −111.4) scores exactly 60

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                              |
|--------------------|-------|------|--------|----------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Cap −40, two-track, critical floor-0 all locked    |
| Boundary Clarity   | 0.80  | 0.70 | ✓      | Substrate/flip/gate2/visualization explicitly out  |
| Constraint Clarity | 0.80  | 0.65 | ✓      | IPSF proportional anchor, numpy-pure, single seam  |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 7 structural invariants, no per-fixture targets    |
| **Ambiguity**      | 0.161 | ≤0.20| ✓      |                                                    |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective | Question summary                              | Decision locked                                                        |
|-------|-------------|-----------------------------------------------|------------------------------------------------------------------------|
| 1     | Researcher  | Execution-fault floor (aggregate cap value)?  | Floor 60 / cap −40, IPSF proportional (−25 on ~60 IPSF ≈ 42% → −40)     |
| 1     | Researcher  | Critical (full-extension miss) vs the cap?    | Critical bypasses cap — can go lower (two-track separation)             |
| 2     | Boundary    | How low can the critical track go?            | To 0 (element itself absent) — no separate critical floor              |
| 2     | Boundary    | Re-verification pass/fail without overfit?    | Structural invariants only — no per-fixture target scores               |

---

*Phase: 33-result-trust-recovery*
*Spec created: 2026-07-24*
*Next step: /gsd-discuss-phase 33 — implementation decisions (execution/critical track partition, routing, deductionBreakdown shape)*
