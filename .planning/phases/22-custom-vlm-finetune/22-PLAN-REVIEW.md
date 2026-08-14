# Phase 22 — Plan-Set Verification (4-Lens Panel)

**Date:** 2026-07-07
**Scope:** 22-01-PLAN.md … 22-10-PLAN.md (post-f539f01)
**Method:** 4 parallel read-only lenses — (A) gsd-plan-checker goal-backward gate, (B) decision/invariant compliance (D-01~16 + scoring invariants), (C) technical consistency vs RESEARCH/NLM-EXTRACT + codebase, (D) executability (DAG, read_first, verify-gate strength, autonomy).
**Purpose:** find every gap before belle's external-AI review.

---

## Panel verdict

| Lens | Verdict | Headline |
|------|---------|----------|
| A plan-checker | **BLOCK** | `faults[]` not pinned to deduction-engine contract → swapped output unscoreable (core invariant break) |
| B decision/invariant | PASS-WITH-CONCERNS | No BLOCKER; score-absence + no-human-label are genuinely test-enforced. HIGH: shadow→training PII seam |
| C technical | PASS-WITH-CONCERNS | No hallucinated numbers / no 2.5-era leakage. 3 MEDIUM: 2 wrong path cites + 1 real split-logic bug |
| D executability | PASS-WITH-CONCERNS | DAG/waves/FT-tags sound. Risk = weak verify-gates + autonomy/cost mismatch |

**Combined:** BLOCK on one item (P0), then a tight set of surgical fixes. No structural rework, no replan. Dependency DAG, wave ordering, FT-01~06 coverage, and the EVAL18 6-pair regression premise are all verified sound.

---

## APPLIED vs OPEN status (updated 2026-07-07 — commit 376ca4f)

> A partial revision landed on `main` (376ca4f) covering **F1–F5 only**. It was independently spot-verified (deduction_engine contract, firestore `_db()`, EVAL18 paths — all real) and is structurally clean. It is **not** a full pass and **not** an independent PASS (the edits were made and self-graded by the checker lens, then the remaining findings were left open). Do not treat Phase 22 plans as review-ready.

**APPLIED (on main @376ca4f):**
- ✅ **R-01** (P0 BLOCKER) — faults[] ⊇ deduction-engine contract + lockstep test (22-01/04/10). Grounded: `deduction_engine.py:414/418-419/438`.
- ⚠️ **R-02** (svg_spec) — label track + `check_svg_spec_validity` gate added (22-04/05/07). **Pre-empts deferred decision D1** — if belle chooses "v1-thin," this must be reverted.
- ✅ **R-09** (EVAL18 path ×5) — corrected to `dataset/pairs.yaml`.
- ✅ **R-16** (VALIDATION.md) — filled, `nyquist_compliant: true`.
- ✅ **R-07** (22-09 no-op verify) — replaced with real Firestore-count assertion.

**STILL OPEN (fable to apply — NOT on main):**
- 🔴 HIGH: **R-03** (shadow→training PII seam), **R-04** (22-04 Gemini-spend checkpoint), **R-05** (22-08 prod-pod checkpoint), **R-06** (self-deactivating balance gate — 22-02 untouched), **R-08** (22-03 prod-SSH autonomous — 22-03 untouched).
- 🟡 MEDIUM: **R-10** (validation.py miscite), **R-11** (train/val split conflation — still present in 22-04), **R-12** (circular calibration), **R-13, R-14, R-15, R-17, R-18**.
- ⚪ LOW: **R-19 … R-27**.
- Product decisions **D1/D2/D3** still unresolved (D1 already touched by R-02 above — needs belle ruling).

---

## P0 — BLOCKER (must fix before execution)

### R-01 · `faults[]` measurement substrate not pinned to the deduction-engine contract
**Lens A-F1.** `schema.py` (22-01 T1) defines `REPORT_KEYS` top-level but never pins the `faults[]` sub-structure to what the live scoring path consumes: `fault_category` **plus** `student_angle_deg` / `reference_angle_deg` / `measurement_basis` (gemini_vision_scorer SCHEMA v8.1 `differences[]`). Plan 01 only validates `fault_category`. If training labels (22-04) drop the angle pairs, the swapped model output (22-10) converts to a `VisionVerdict` with no measurement substrate → **Phase 24 deduction engine produces no deduction → the "model spots, Phase 24 scores" invariant silently breaks.**

**Fix:**
- 22-01 T1: define `faults[]` as a superset of v8.1 `differences[]` — `fault_category`, `student_angle_deg`, `reference_angle_deg`, `measurement_basis`, `root_cause_hypothesis`, `source`. Add a **lockstep test**: `faults[]` schema ⊇ deduction-engine consumed keys.
- 22-04: ensure Gemini teacher's raw `differences[]` measurement fields survive into the assistant `faults[]` label (not stripped by the new key list).
- 22-10: add a test that the converted `VisionVerdict` feeds `deduction_engine` and yields a non-empty deduction on a known fault.

---

## P1 — HIGH

### R-02 · `svg_spec` is a mandated v1 output with no label track and no gate
**Lens A-F2.** D-01 places SVG visual spec in v1. It appears **only** in schema.py (22-01). No task generates/validates `svg_spec` labels (target_angle / force_vector / ideal_trajectory); teacher distillation (22-04) is silent on producing those vectors; bake-off 4 axes (22-05) and `assert_gates` 5 checks (22-07) omit it. A model emitting null/garbage `svg_spec` passes every gate.
**Fix (belle decision — see D1 below):** either (a) add an `svg_spec` label track (target_angle deterministically from reference/IPSF; force/trajectory from teacher + dedicated filter) **and** an svg_spec validity axis in run_bakeoff/assert_gates, or (b) explicitly declare svg_spec v1-thin in D-01/plan-01 with belle sign-off.

### R-03 · Shadow-distillation → training bypasses the D-12 anonymization gate (PII/consent seam)
**Lens B-F3.** shadow track (c) logs production customer-video verdicts keyed by `video_hash` (22-03); 22-04 turns those into training samples that feed **video frames** to the VLM. Those production videos aren't in the manifest, so the `anonymized=true` gate (which keys on manifest rows) can be bypassed → face pixels can enter training.
**Fix:** 22-04 build_jsonl must only consume shadow-derived samples whose `video_hash` is manifest-registered with `anonymized=true`; otherwise use text-only labels (no frames) or force anonymize+register first. Add test: "video-referencing samples with unregistered video_hash = 0."

### R-04 · 22-04 spends Gemini API at batch scale with no cost checkpoint
**Lens D-E02.** Teacher distillation runs the whole manifest through `gemini-3.1-pro-preview` + `gemini-3.5-flash` judge — real money, with a documented credit-depletion history — yet 22-04 is `autonomous:true` while 22-06/07 gate Pod rental. Inconsistent risk treatment.
**Fix:** add a `checkpoint:human-verify` cost-approval task before the batch (mirror 22-06 T1), or at minimum a belle-notify at the spend point + pre-batch credit check (the plan already has the 429 abort; elevate it to an approval gate).

### R-05 · 22-08 mutates the PRODUCTION serving pod, autonomous, behind syntax-only gates
**Lens D-E03.** Deploys vLLM co-located with live NLF/RTMW (Pitfall 3: vLLM preemption → NLF OOM → **live analysis outage**), marked `autonomous:true` with only `bash -n` + grep gates. An autonomous executor could take down production.
**Fix:** add a blocking checkpoint before 22-08 T2 (D-14 cohab is a real decision/risk point), or split the pod-mutation into a belle-approved step.

### R-06 · Self-deactivating balance gate (fail-open)
**Lens D-E04 / B-F6.** `test_manifest_consistency` balance gate only activates when `_meta.collection_complete=true` — a flag the executor sets itself. Left false, the equal-distribution assertion is silently skipped; a stub with an empty manifest passes.
**Fix:** make the balance test fail-closed — assert `collection_complete==true` AND balance at the point 22-04 consumes the manifest (build_jsonl entry gate), or drive the gate off actual S3 object count, not a self-set flag.

### R-07 · 22-09 Task 2 verify is a no-op `print()`
**Lens D-E01 / A-F5 / B-F5.** `python3 -c "print('… see SUMMARY')"` asserts nothing; the real deliverable (≥20 shadow docs across ≥7 motions, analysis-failure 0) lives only in acceptance_criteria. Hollow execution passes.
**Fix:** replace with a Firestore-count assertion (exit nonzero if <20 docs / <7 motions), or reclassify as checkpoint/manual and drop the fake `<automated>`.

### R-08 · 22-03 Task 3 is pod-required (prod SSH) but autonomous + doc-grep gate
**Lens D-E05.** SSH to prod pod, enable `VLM_SHADOW_LOG=1` in prod `start_server.sh`, live smoke, `nvidia-smi` poll — gated only by `test -f 22-POD-VRAM.md && grep -cE "peak|피크"`. An autonomous executor without SSH gets stuck or fabricates the doc.
**Fix:** reclassify Task 3 as pod-required (non-autonomous / explicit checkpoint); replace the grep with a check that parses a numeric peak-VRAM field.

---

## P2 — MEDIUM

### R-09 · EVAL18 path wrong in 5 places *(3-lens corroborated: A-F3 / C-F1 / D-E07)*
Cited `backend/evals/phase18/pairs.yaml`; actual is `backend/evals/phase18/dataset/pairs.yaml` (verified: `dataset/pairs.yaml` exists, root `pairs.yaml` does NOT; `assert_baseline.py:38 _PAIRS = _HERE/"dataset"/"pairs.yaml"`). **Substance is correct:** 6 pairs, kip-up=`known_false_positive`, climb=`known_gate_blocked` → "변별 4 + known 2" is accurate.
**Fix — 5 exact locations (grep-verified 2026-07-07):**
- `22-05-PLAN.md:65` (read_first)
- `22-07-PLAN.md:35` (`key_links.to:` — its `pattern:"phase18"` grep still passes, masking the error)
- `22-07-PLAN.md:102` (read_first)
- `22-08-PLAN.md:124` (read_first)
- `22-09-PLAN.md:92` (read_first)
All → `backend/evals/phase18/dataset/pairs.yaml`.

### R-10 · 22-01 read_first miscites `validation.py` + `_as_tj` *(C-F2 / D-E06)*
Cited `analysis/validation.py`; actual is `sunity_shared/validation.py` (no `/analysis/`). The "순수 함수" line is there (`validation.py:3`) but `_as_tj` is **not** — it's in `analysis/dimensions.py`. Two errors: wrong dir + wrong symbol.
**Fix:** point purity-rule cite to `sunity_shared/validation.py:3`; point `_as_tj` to `analysis/dimensions.py`.

### R-11 · train/val split logic conflict between 22-04 and 22-07
**Lens C-F3.** 22-04 builds a **video_hash-level** split (train.jsonl + val.jsonl; Test 6 guards leakage). 22-07 runs `swift sft --dataset train.jsonl --split_dataset_ratio 0.02`, which re-splits train.jsonl **randomly** ignoring val.jsonl and without video_hash grouping → orphans 22-04's val.jsonl and **voids the leakage guarantee**. 22-04's "D-06 split_dataset_ratio 정합" comment conflates two split mechanisms.
**Fix:** pick one owner — either drop `--split_dataset_ratio` in 22-07 and pass 22-04's val.jsonl via `--val_dataset`, or have 22-04 emit one combined jsonl and let swift split. Make 04↔07 consistent.

### R-12 · error-profile circular-calibration risk *(B-F4)*
`measure_error_profile.py` (22-01 T2) source (실사용 371 + reference) is not separated from bake-off/eval fixtures + hard_negative. If perturbation design calibrates on eval data → violates `calibration-source-hard-gate`.
**Fix:** exclude eval-fixture/holdout `video_hash` from the measurement source; record excluded list in `_meta`; test intersection = 0. (Note: measuring a distribution is not itself curve-fit; the gate is about source↔validation separation.)

### R-13 · `measure_error_profile` `source_doc_count ≥ 30` not in the automated gate *(D-E08)*
Firestore-credential-bound; `<automated>` only checks JSON key presence. Without creds an empty profile passes, then 22-01 T3 perturb samples from a hollow distribution.
**Fix:** add `assert _meta.source_doc_count >= 30` to the verify (with documented reference-data fallback if <30).

### R-14 · 22-04 verify commands weak *(D-E09)*
Task 1 verify is a source-string grep (`assert 'files.delete' in src`) — a comment with the literal passes. Task 3 ends in `aws s3 ls …/jsonl/` which **exits 0 on an empty prefix**.
**Fix:** Task 1 — unit-test the delete-in-finally lifecycle with a mock client. Task 3 — `aws s3 ls … | grep -q train.jsonl` (fail-closed).

### R-15 · 22-03 Task 2 regression check is collect-only *(D-E11)*
`pytest backend/tests -q -x --co -q | tail -1` uses `--co` (collect-only) — lists test names, does not run them, so it never verifies the "baseline FAILED diff IDENTICAL / 회귀 0" claim.
**Fix:** run the actual suite and diff the pass/fail set, or drop the misleading `--co` clause.

### R-16 · 22-VALIDATION.md is an unfilled template *(A-F4)*
Every field is a `{placeholder}`, `nyquist_compliant: false`, empty per-task map. Passes existence but was never authored. Mitigant: every `auto` task carries an inline `<automated>` verify.
**Fix:** fill it (framework=pytest, quick/full commands, per-task map from the plans' `<automated>` blocks, Manual-Only rows for the Pod tasks per R-08/R-05/R-17) and set `nyquist_compliant: true`; or explicitly record that inline verifies supersede.

### R-17 · 22-07 Task 3 gate accepts FAIL *(D-E12)*
`python3 assert_gates.py; test $? -le 1` accepts exit 1 (FAIL) and, with no artifacts, SKIPPED→0. Confirms only "doesn't crash," not that SFT passed.
**Fix:** label it a smoke; true gate is the Pod-run judgment in SUMMARY. Consider `test $? -eq 0` once artifacts exist.

### R-18 · "3-track" label framing over-implies shadow at first SFT *(D-E10 / A-F6)*
build_jsonl (22-04, Wave 2) reads shadow (22-03, Wave 1) which only accrues from live traffic → near-empty at first build. It's really 2 tracks (perturb + distill) at build time.
**Fix:** state explicitly that track (c) is best-effort/may be empty at first build and grows for later re-training; confirm the 3-way consistency test tolerates an empty shadow track (don't gate on its presence).

---

## P3 — LOW / polish

- **R-19** `TechniqueRecognizer` Protocol is in `analysis/technique.py:77`, not `interfaces.py` — fix read_first in 22-08 T1 / 22-10 T1. *(D-E13)*
- **R-20** schema.py "numpy 외 서드파티 의존 0" is violated at import time by the `vision_veto` import for `FAULT_CATEGORIES` — make it lazy/function-local, or vendor the enum tuple with a lockstep test (as 22-08 already does for REPORT_KEYS). *(D-E15)*
- **R-21** 22-09 Task 3 `shadow_report` verify is a `hasattr` smoke with no math backstop — add a unit test over a synthetic vlm_shadow fixture asserting agreement-rate math. *(D-E14)*
- **R-22** Dual wave numbering: D-16 "Wave 0–4" (conceptual) vs frontmatter/ROADMAP "Wave 1–7" (execution). Add a one-line mapping note (Wave 0 = exec 1; 1 = 2–3; 2 = 4; 3 = 5–7; 4 = follow-on). *(A-F7 / B-F8 / C / D)*
- **R-23** coach-writer line cite `747-762` — `_ensure_gemini_coach_writer` ~750 ✓ but `_call_coach_writer_with_retry` is ~908. Split the cite. *(C-F4)*
- **R-24** Add `22-05` to 22-07 `depends_on` (it directly imports run_bakeoff.py + fixtures; only transitively present via 06); similarly note 22-08 reads schema.py directly. Clarity only — DAG is still acyclic. *(D DAG note)*
- **R-25** bake-off `grounding L2` on base (non-fine-tuned) 8B models may be near-random / non-discriminative — record in 22-BAKEOFF-RESULT.md that selection weights the discriminating axes (temporal/JSON) if grounding is degenerate. *(A-F8)*
- **R-26** Add a bake-off score-key rejection test (output with score-key → score_json penalize/discard) so the no-score invariant is test-enforced at *every* model-output boundary. *(B-F7)*
- **R-27** Normalize model-ID spelling (`Qwen 3.6-VL-8B` vs `Qwen3.6-VL-8B`); keep A6 (exact HF/ms-swift IDs) deferred to Wave 1. *(C-F6)*

---

## Items needing belle's product decision (not mechanical)

> **STATUS 2026-07-07: belle 결정 대기 — fable 수정/재검증 시점에 확정.** 아래 3건은 수정 내용을 좌우하므로 fable이 R-02/R-06 손대기 전 belle 확답 필요.

- **D1 (→R-02):** svg_spec — full v1 label track + gate, OR declared v1-thin with sign-off. *(미결)*
- **D2 (→B-F1):** D-11 `<loc_NNN>` was reinterpreted as plain 3-digit integer text ("loc_NNN 어휘확장 아님"). Functionally same 0–999 grid, but token representation differs and an external reviewer will read the decision text literally. Surface + get a one-line sign-off, or restore special-token form. *(미결)*
- **D3 (→R-06/B-F2):** balance gate `max ≤ 2×min` relaxes the "다른 영상들도 다 동일한 빈도수" invariant. Expose `_meta.balance_ratio` as a belle parameter with target 1.0 and document the 2:1 as a time-boxed seed-stage allowance. *(미결)*

---

## Verified sound (no action)

- Dependency DAG acyclic; frontmatter waves monotonic with depends_on; match ROADMAP 743-752; no parallel-edit conflict (pipeline/app.py touched by 03/09/10 strictly sequential).
- FT-01~06 all covered by a real delivering task (not just tagged).
- No hallucinated numbers, no 2024-superseded techniques, no 2.5-era model leakage; version pins (ms-swift 4.4.0 / vllm 0.24.0 / lmms-eval 0.7.2) + "re-check by 2026-07-20" caveat carried; A8 flag-rename + A6 model-ID deferrals present.
- Score-absence + no-human-numeric-label invariants are test-enforced at schema / JSONL-build / vlm_judge-parser / swap-conversion boundaries. eval-SERIAL upheld everywhere. Firestore flat-storage / nested-array ban / SSM secrets honored.
- Codebase spot-checks confirm real: FAULT_CATEGORIES owner (`vision_veto.py:102`), store_gemini_cache (`firestore_admin.py:1423`), `_apply_vision_veto` (`app.py:2248`), phase24 assert_gates/run_sweep, phase18 dataset (6 pairs), RTMW-133 is the deployed engine, coach_writer default model `gpt-oss-120b`.

---

## Open for later (not this phase's build)

- **C-F5:** ms-swift 4.4.0 MPO loss-mixing rests on a single web citation NLM flagged uncertain. Wave 4 is boundary-only, so no plan change now — re-verify the swift RLHF/MPO doc before the Wave 4 RL build.
