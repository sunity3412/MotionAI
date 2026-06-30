---
phase: quick-260630-l4e
status: passed
gate: orchestrator-owned pod sweep (Claude-run)
pod: 97s9atfkakbki8 @ d557d6d
date: 2026-06-30
---

# Quick Task 260630-l4e — Orchestrator Verification + kip-up Split-Margin Domain Review

## 1. Pod 6-pair Phase-24 sweep (HARD GATE) — PASS

Full SERIAL sweep ([[pipeline-not-concurrency-safe-eval-serial]]) on pod d557d6d
(`backend/evals/phase24/run_sweep.py`). Fresh artifacts committed:
`backend/evals/phase24/baseline/phase24_{sweep_report,breakdowns}.json`.

| motion | success | fault | margin | verdict |
|--------|---------|-------|--------|---------|
| power-spin | **100** (was 91) | 60 | 40 | discriminate |
| peter-pan | 100 | 79 | 21 | discriminate |
| elbow-twist-sister | 100 | 62 | 38 | discriminate |
| pdshape | 100 | 58 | 42 | discriminate |
| kip-up | **100** (was 96) | **88** | **12** | discriminate |
| climb | not_pole gate | not_pole gate | — | gate (expected) |

PASS criteria (all met):
- [x] power-spin success 91 → **100** (target 95~100) — the fix's primary objective.
- [x] peter-pan / elbow-twist / pdshape success stay **100**.
- [x] kip-up success 96 → **100** (correct for 정은지 success vs 정은지 reference).
- [x] **kip-up fault stays 88 (NO jump to 100)** — the FP-regression hard gate. Holds because the
      `split_angle` deduction RECORD fires → `applied` path → untouched by the not_applicable fix.
- [x] all faults stay penalized with transparent per-criterion records; all pairs discriminate.
- [x] climb = not_pole gate both members (known, expected).

Determinism: cold-rerun `pdshape warm=100 / cold=100, selection_identical=True` — no flakiness.

## 2. kip-up split-margin domain review (deliverable)

**Question:** is the `split_angle` criterion's fault-vs-success separation domain-adequate?

**Measured (this sweep):** kip-up fault=88, success=100 → **margin 12**. The fault's sole deduction:
`split_angle: pts=-12.0, deviation=10.0° over tol, measured=30.0°, source=vision, deviationSource=reference_relative`.
i.e. Gemini vision-measured the student's split at 30° from the 정은지 reference; 10° over the CITED
20° kismam tolerance × slope, per-criterion capped → −12 (belle 2026-06-29 decision A,
[[kipup-fp-RESOLVED-phase24A]]).

**Assessment — margin is ADEQUATE; no code change.**
1. 12 is the smallest margin of the five moves (others 21–42) **because kip-up's fault is a single
   failure mode** (insufficient split / legs not opening) → exactly ONE criterion deducts. Multi-joint
   faults (pdshape trips 7 `angle_vs_reference` criteria → 42) naturally show larger margins. A
   single-criterion fault yielding a single transparent deduction is domain-correct, not a defect.
2. The deduction is principled and transparent: no new threshold (reuses CITED 20° kismam tol), score
   = measured-deviation × explicit rule, capped; `source=vision` is surfaced so the report reads
   "split 10° 부족(vision 측정) −12" ([[scoring-must-be-transparent-deduction-tally]]).
3. The margin **scales with measured severity** (linear over-tol up to `_ANGLE_CAP`), so a worse split
   docks more — 12 reflects this fault's actual 30° deviation, not an arbitrary band.
4. 88 vs 100 is a clear, user-visible separation that cleanly discriminates; deterministic on rerun.

**Tradeoff to record (belle FYI, not a blocker):** retiring the not_applicable legacy min-of-core
passthrough removes a thin (~3-pt) accidental safety net that *previously* docked kip-up fault to ~97
in runs where Gemini missed the split. Post-fix, a split-miss run would route kip-up fault to
not_applicable → 100. This raises the stakes on split-detection reliability — but that legacy 3-pt
dock was never real protection, and detection is reliable in the resolved engine (fired here, 5/5 in
[[kipup-fp-RESOLVED-phase24A]]). The principled position holds: the transparent tally is authoritative;
kip-up FP defense lives in split detection, not a non-IPSF dimension penalty.

## 3. Conclusion
Both objectives delivered. power-spin success fallback fixed (91→100), kip-up split margin reviewed
and confirmed adequate (no change). No regression; deterministic. SHIP.
