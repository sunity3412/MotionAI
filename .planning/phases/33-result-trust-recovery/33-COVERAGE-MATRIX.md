---
phase: 33-result-trust-recovery
plan: 20
title: Canonical 11-motion coverage matrix
status: CANONICAL
authored: 2026-07-23
requirements: [D-18, D-23, D-27]
cited_by: [33-06, 33-08, 33-09, 33-16]
sources_of_truth:
  registered_motions: "backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py REGISTERED_MOTIONS (len == 10, verified against backend/tests/test_gemini_motion_classifier.py::test_10_motions_exactly)"
  phase25_fixtures: "backend/evals/phase25/baseline/phase25_sweep_report.json results[] motion_id (6 distinct: climb, elbow-twist-sister, kip-up, pdshape, peter-pan, power-spin — each with a success + fault member)"
  reference_library: ".planning/debug/ref-student-substrate-gap.md ## 재처리 위험도 표 (11 reference docs) + M8 lineage split"
---

# 33-COVERAGE-MATRIX.md — the ONE canonical coverage source

> **CANONICAL. This is the single per-motion coverage inventory for phase 33.**
> 33-06 / 33-08 / 33-09 / 33-16 MUST cite this file and MUST NOT carry a divergent
> inventory (codex suggestion 10 / D-23). If a coverage claim in any of those plans
> disagrees with a row here, this file wins and the plan is corrected — never the reverse.

## Why this exists

Four plans (33-06/08/09/16) each carried their own coverage inventory, and they
disagreed. Codex found the divergence (33-REVIEWS.md L56, L148). The concrete conflicts:

1. **5 non-paired, not 4.** 11 reference docs − 6 phase25 fixtures = **5** fixture-less
   motions. The plans list only four (`ref-foxtop`, `ref-foxtop-split`, `ref-invert`,
   `ref-sideway-spin`) and silently drop the fifth — **`ref-combo`**.
2. **33-06 vs 33-16 disagreed on the four.** 33-06's four excluded `ref-sideway-spin`;
   33-16's four included `ref-sideway-spin` but excluded `ref-combo`. Neither listed the
   full five.
3. **`REGISTERED_MOTIONS` = 10, not 11.** `combo` is **not** registered (verified against
   code, not prose — see grounding below). Any plan that treats the reference library as
   "11 registered" is wrong: it is **10 registered + 1 unregistered (`ref-combo`)**.
4. **climb lacks the mode1 margin/separation substrate 33-06 assumes.** `ref-climb` has a
   phase25 fixture, but it is a **mode1 comparison-gate motion with no score** — there is
   no margin/separation to measure. 33-06's margin sweep does not apply to it.

Without one matrix, a motion can silently fall through the gaps of four disagreeing
inventories — a D-18 silent-skip and a D-23 "6동작 전수" violation. This matrix makes
per-motion verification explicit and forces climb / sideway-spin / combo to explicit
resolution before execution.

## Grounding (verified against code — not asserted)

| Fact | Value | Source (grep-checked 2026-07-23) |
|------|-------|----------------------------------|
| `REGISTERED_MOTIONS` count | **10** | `gemini_motion_classifier.py:26` frozenset; `test_gemini_motion_classifier.py:28` `assert len == 10` |
| Registered members | climb, foxtop, foxtop-split, invert, sideway-spin, kip-up, power-spin, peter-pan, elbow-twist-sister, pdshape | `gemini_motion_classifier.py:29-40` |
| `combo` registered? | **NO** — absent from the frozenset | not present in `gemini_motion_classifier.py:26-41` |
| phase25 fixtures | **6** distinct motion_id, each success + fault | `backend/evals/phase25/baseline/phase25_sweep_report.json` `results[]` → {climb, elbow-twist-sister, kip-up, pdshape, peter-pan, power-spin} |
| reference library | **11** docs | `.planning/debug/ref-student-substrate-gap.md` 재처리 위험도 표 (11 rows) |
| Non-paired = 11 − 6 | **5** | foxtop, foxtop-split, invert, sideway-spin, combo |
| M8 axis lineage split | 원본 5 = bukuroo-06-06 `(x,0,y)` / 후속 6 = direct-06-12 `(x,y,0)` | `ref-student-substrate-gap.md` M8 + 재처리 위험도 표 계보 column |

**The five non-paired (fixture-less) motions are:**
`ref-foxtop`, `ref-foxtop-split`, `ref-invert`, `ref-sideway-spin`, `ref-combo`.
(The plans' "four" was missing `ref-combo`.)

## Column legend

- **registered** — in `REGISTERED_MOTIONS` (10). `combo` = no.
- **paired fixture** — has a phase25 success+fault fixture pair (6 motions).
- **success / fault** — fixture member availability for that motion.
- **self-comparison substitute** — for fixture-less motions, the named substitute proof
  (`backend/scripts/verify_self_comparison.py --reference-version <candidate>`: feed the
  reference video back as the student, expect near-full-marks). Closes R-3 (no silent skip).
- **M8 visual-check** — original-5 lineage (bukuroo-06-06, `(x,0,y)`) re-processes to
  `(x,y,0)`; these 5 need a Simulator eyeball of overlay + fault-zoom crop after re-extract
  (R-5, success criterion 4). direct-06-12 motions were already `(x,y,0)` → no layout flip.
- **presentation coverage** — which of A-1 (motion-standards table, 33-08), A-2 (coach
  voice / phrasebook, 33-09), A-5 (fault-zoom crops, 33-12) apply.
- **verification owner** — the plan that actually verifies this motion.

## The matrix (11 rows)

| # | motionId | lineage | registered | paired fixture | success | fault | self-comparison substitute | M8 visual-check | presentation (A-1/A-2/A-5) | verification owner |
|---|----------|---------|:---:|:---:|:---:|:---:|---|:---:|---|---|
| 1 | ref-kip-up | direct-06-12 | yes | **yes** | yes | yes | n/a (fixture) | no | A-1, A-2, A-5 | 33-06 margin sweep + 33-16 gate |
| 2 | ref-peter-pan | direct-06-12 | yes | **yes** | yes | yes | n/a (fixture) | no | A-1, A-2, A-5 | 33-06 margin sweep + 33-16 gate |
| 3 | ref-power-spin | direct-06-12 | yes | **yes** | yes | yes | n/a (fixture) | no | A-1, A-2, A-5 | 33-06 margin sweep + 33-16 gate (belle "천장" → 옆으로 fixed at A-1/A-2) |
| 4 | ref-pdshape | direct-06-12 | yes | **yes** | yes | yes | n/a (fixture) | no | A-1, A-2, A-5 | 33-06 margin sweep (+2-run stability, R-6) + 33-16 gate |
| 5 | ref-elbow-twist-sister | direct-06-12 | yes | **yes** | yes | yes | n/a (fixture) | no | A-1, A-2, A-5 | 33-06 margin sweep + **33-21 elbow-twist HALT route** + 33-16 gate |
| 6 | **ref-climb** | bukuroo-06-06 | yes | **yes** | yes | yes | n/a (fixture) | **YES** | A-1, A-2, A-5 | 33-06 **comparison-gate check (NO margin — scoreless)** + 33-16 M8 eyeball |
| 7 | ref-foxtop | bukuroo-06-06 | yes | **no** | — | — | **yes** — `verify_self_comparison.py` (inversion-positive, R-3) | **YES** | A-1 (substitute row), A-2 (cue from A-1 substitute) | 33-06 self-comparison + 33-08 A-1 + 33-09 A-2 + 33-16 substitute |
| 8 | ref-foxtop-split | bukuroo-06-06 | yes | **no** | — | — | **yes** — `verify_self_comparison.py` (inversion-positive, R-3) | **YES** | A-1 (substitute row), A-2 | 33-06 self-comparison + 33-08 A-1 + 33-09 A-2 + 33-16 substitute |
| 9 | ref-invert | bukuroo-06-06 | yes | **no** | — | — | **yes** — `verify_self_comparison.py` (inversion-positive, R-3) | **YES** | A-1 (substitute row), A-2 | 33-06 self-comparison + 33-08 A-1 + 33-09 A-2 + 33-16 substitute |
| 10 | **ref-sideway-spin** | bukuroo-06-06 | yes | **no** | — | — | **yes** — `verify_self_comparison.py` (non-inversion, coverage-only) | **YES** | A-1 (substitute row), A-2 | 33-06 self-comparison + 33-08 A-1 + 33-09 A-2 + 33-16 substitute |
| 11 | **ref-combo** | direct-06-12 | **NO** | **no** | — | — | **yes** — `verify_self_comparison.py` + **R-4 2-run determinism** (`RTMW_DETERMINISTIC=1`) | no | **A-2 `__common__` only** (not in A-1; no A-5 — no fixture to analyze) | 33-06 self-comparison + R-4 determinism |

**Row count check:** 11 references. Registered = 10 (rows 1–10). Unregistered = 1 (row 11, combo).
Paired fixtures = 6 (rows 1–6). Fixture-less = 5 (rows 7–11).

## Explicit resolution of the three ambiguous motions

### (a) ref-climb — registered, fixtured, but SCORELESS

- **Status:** registered (in `REGISTERED_MOTIONS`), has a phase25 fixture (success + fault).
- **The 33-06 assumption is wrong for climb.** climb is a **mode1 comparison-gate motion
  with no score** (`ref-student-substrate-gap.md` 재처리 위험도 표 row 9: "mode1 comparison
  gate 전용(점수 없음)"; the substrate rescore ran "5동작(climb 제외)" precisely because
  climb emits no margin/separation). There is no `여유 = tol − max편차` to compute — climb
  has no per-joint deviation score.
- **How climb IS verified (no silent skip):** its fixture is exercised at the
  **comparison-gate level** — mode1 must correctly gate the real climb (the not_pole /
  comparison gate behaves; it neither wrongly rejects the genuine climb nor fabricates a
  score). climb is **original-5 lineage (bukuroo-06-06)**, so after re-extraction its axis
  layout flips `(x,0,y) → (x,y,0)` → it is a **mandatory M8 Simulator eyeball** target
  (overlay + fault-zoom crop, success criterion 4). Its A-1/A-2/A-5 presentation still
  applies. **What climb does NOT get:** a margin/separation number (there is none).
- **Owner:** 33-06 comparison-gate check + 33-16 M8 device eyeball. 33-06 MUST NOT list
  climb among the margin-sweep motions.

### (b) ref-sideway-spin — registered, fixture-less, non-inversion

- **Status:** registered, **no** phase25 fixture, non-inversion (역위 0.7%, run 1 — not PR-affected).
- **This is the motion 33-06 dropped and 33-16 kept.** Reconciled: it is one of the **five**
  fixture-less motions and MUST be covered.
- **Verification path:** `verify_self_comparison.py --reference-version <candidate>`
  (feed ref-sideway-spin back as the student → expect near-full-marks on the re-processed
  substrate). Because it is fixture-less, R-3's "named substitute" applies **for coverage
  even though it is not inversion-positive** — the PR-regression concern (R-3's "4종") does
  not apply, but the **D-23 coverage obligation does**. This distinction is exactly the gap
  that let it fall out of the plans.
- **M8:** original-5 lineage (bukuroo-06-06) → mandatory Simulator eyeball after re-extract.
- **Owner:** 33-06 self-comparison + 33-08 A-1 (substitute row) + 33-09 A-2 (cue) + 33-16 substitute.

### (c) ref-combo — UNREGISTERED, fixture-less, inversion-positive

- **Status:** **NOT registered** — `combo` is absent from `REGISTERED_MOTIONS` (verified
  against `gemini_motion_classifier.py:26-41` and `test_gemini_motion_classifier.py:28`).
- **Is unregistered intended? YES.** `REGISTERED_MOTIONS` was frozen at 10 by the P1
  decision (2026-06-27, quick-260627-afq step 4). combo — a compound move — was never given
  a motion-specific recognizer scope. Unregistered motions route through the Page-9 absolute
  track for scoring and through the phrasebook **`__common__`** path for coaching copy
  (`phrasebook.json` `_meta`: "미등재 동작은 `__common__` 경로로 동일 phrasing"). This is by
  design, not an omission.
- **How combo is still substrate-verified (no silent skip):** combo IS one of the 11
  reference docs and gets re-extracted with the other 10, so its substrate must be proven.
  Verification = `verify_self_comparison.py` **plus R-4 determinism** — combo is the longest
  clip (931 frames) with a known non-determinism history (backfill gate saw 23.43° → 0.193°
  run-to-run variance). It MUST be re-processed with `RTMW_DETERMINISTIC=1` and run **twice**,
  recording the between-run variance (rollback trigger if it exceeds `P99_EPSILON_DEG`).
- **Presentation:** **A-2 `__common__` only.** combo is NOT in A-1 (33-08 covers registered
  motions) and has **no A-5 crop** (no fixture to analyze). direct-06-12 lineage → no M8 flip.
- **Owner:** 33-06 self-comparison + R-4 determinism recording.

## Consumer contract (what each citing plan must do)

- **33-06** (S4 shadow-candidate verify): margin sweep runs on the **5 scoring fixtures**
  (kip-up, peter-pan, power-spin, pdshape, elbow-twist-sister) at equal frequency; **climb**
  is verified by comparison-gate (no margin); the **5 fixture-less** motions
  (foxtop, foxtop-split, invert, sideway-spin, combo) run `verify_self_comparison.py`;
  combo additionally records R-4 2-run determinism. No divergent inventory.
- **33-08** (A-1 motion standards): 6 fixture rows first, then extend to the **10 registered**
  motions; the **4 fixture-less registered** (foxtop, foxtop-split, invert, sideway-spin)
  carry named substitute evidence; **combo is out of A-1** (unregistered) and that omission
  is intentional per this matrix (not a silent skip).
- **33-09** (A-2 coach voice): author motion-specific cues for the **10 registered** motions;
  combo falls through to `__common__` by design (record it as such, not as a gap).
- **33-16** (phase gate device UAT): re-sweep the **6 fixtures** serially; verify the
  **5 fixture-less** motions via named substitute; M8 Simulator eyeball for the
  **original-5 lineage** (climb, foxtop, foxtop-split, invert, sideway-spin).

## "이 산출물이 틀렸다면 어떻게 알았을까" (D-18)

A motion missing a **verification owner** or a **substitute** shows up as a **visible blank
cell** in the matrix above — caught by inspection before 33-06 runs. The row-count check
(11 = 6 fixtures + 5 fixture-less; 10 registered + 1 unregistered) is arithmetic and fails
loudly if a motion is added or dropped. The grounding table is grep-checkable against code,
so a drift in `REGISTERED_MOTIONS` (e.g. combo silently registered) breaks the cited line
number, not just prose.
