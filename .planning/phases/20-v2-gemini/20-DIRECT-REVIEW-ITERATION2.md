# Phase 20 Direct Review - Iteration 2

**Reviewed:** 2026-06-19  
**Reviewer:** Codex direct review (not external reviewer)  
**Scope:** updated `.planning/phases/20-v2-gemini/20-01~04-PLAN.md`, `20-VALIDATION.md`, prior `20-DIRECT-REVIEW.md` amendments  
**Review stance:** second-pass safety review after HIGH/MEDIUM amendments. Focus = remaining false-green routes and new ambiguity introduced by the fixes.

## Summary

The first-pass findings were mostly addressed. The plan now has the right hard gates for:

- `keep_local_video` with `GEMINI_VISION_VETO_ENABLED`;
- `visionVeto.status` instead of applied/absent ambiguity;
- `--self-check` vs `--phase-gate`;
- `SEVERITY_CAP_PROVENANCE`;
- schema/dataclass introspection instead of raw grep;
- prompt/schema-versioned `VisionVetoCache`.

That is a real improvement. I would still patch several details before execution. The largest remaining issues are: 20-03 tests assume a numeric cap before 20-04 fills it, Mode3 "score suppression" can still leak score-derived UI, and `scoreSuppressed` is not locked into the same contract rigor as `visionVeto`.

## Findings

### HIGH-1: 20-03 cap-application tests assume `major` already has a numeric cap, but 20-01 intentionally leaves it `None`

**Risk:** 20-03 says the pipeline test should mock a `major` verdict and assert `overallScore=100` gets capped. But 20-01 explicitly creates `SEVERITY_CAP = {"minor": None, "moderate": None, "major": None}` until 20-04 derives real values. Without an explicit test override, the cap path either fails during 20-03 or, worse, the implementation only tests pass-through/not-applicable behavior and never proves the mutation path before Pod.

**Evidence:**

- `20-01-PLAN.md:94` sets all cap values, including `major`, to placeholder `None`.
- `20-01-PLAN.md:95` requires real `sensitivity_manifest_sha256` before caps are filled.
- `20-03-PLAN.md:88` expects adapter mock `severity='major'(cap<100)` to lower `overallScore=100`.
- `20-03-PLAN.md:111` applies the cap only if `capped < score_result["overallScore"]`.

**Why it matters:** The phase's structural safety claim depends on proving the actual mutation path. If 20-03 runs before 20-04, the real module state is no-cap.

**How I would fix it:**

- In 20-03 tests, explicitly monkeypatch the cap table:

```python
monkeypatch.setitem(vision_veto.SEVERITY_CAP, "major", 50)
```

- Make the test name say this is a temporary derived-cap fixture, not production calibration.
- Keep 20-01 provenance tests unchanged; the monkeypatch should be scoped to the pipeline test only.
- Add one acceptance criterion: "cap mutation test monkeypatches `SEVERITY_CAP['major']=50` because production caps remain placeholder until 20-04."

This keeps D-02 intact while still proving `_apply_vision_veto` mutates downward once a valid cap exists.

### HIGH-2: Mode3 score suppression can still leak score-derived UI outside `OctagonScore`

**Risk:** 20-03 says suppress `OctagonScore`/`LevelBenchmark`, but the current screen also computes and renders score-derived `grade`, `summary`, header copy, and score caption. If only the octagon is hidden or greyed, the user can still see a grade badge or "90점 이상이면..." guidance, which violates D-08's "confident score 금지" for unheld moves.

**Evidence:**

- `result.tsx:443` computes `grade = scoreGrade(result.overallScore)`.
- `result.tsx:491-496` computes mode3 summary from `result.overallScore`.
- `result.tsx:677` tells mode3 users "점수를 확인해보세요."
- `result.tsx:737-745` renders `OctagonScore`, `gradeBadge`, `summary`, `LevelBenchmark`, and score caption.
- `20-03-PLAN.md:191` only calls out `OctagonScore(737)/LevelBenchmark(742)` suppression.
- `20-03-PLAN.md:203` acceptance only greps for `OctagonScore` suppression.

**Why it matters:** The product failure was "confident 97" despite no basis. Score-derived badges/copy are part of that confidence, not just the octagon.

**How I would fix it:**

- Define one `isScoreSuppressed` boolean in `result.tsx`.
- When true, replace the entire score card with a "기준 없음" state. Do not render:
  - `OctagonScore`
  - `gradeBadge`
  - score-derived `summary`
  - `LevelBenchmark`
  - score caption
  - "점수를 확인해보세요" header copy
- Keep `dimensionScores`/diagnostic details if useful, but present them as non-authoritative observations.
- Add a component test or render smoke test for suppressed Mode3 asserting those score-derived elements are absent.

I would treat "hide only the octagon" as not satisfying D-08.

### HIGH-3: `scoreSuppressed` is not contract-locked like `visionVeto`

**Risk:** 20-03 Task 3 introduces `scoreSuppressed`, but it is not included in Task 3's file list and not given a 3-way contract lockstep. Task 2 only locks `visionVeto`. This creates a route where backend emits a suppression signal that frontend/types/docs do not agree on, or where frontend infers suppression from `scoringBasis` but backend later changes the signal shape.

**Evidence:**

- `20-03-PLAN.md:134-164` locks only `visionVeto` in `analysis.ts`, `models.py`, and `docs/contract.md`.
- `20-03-PLAN.md:168-169` Task 3 files omit `app/src/types/analysis.ts`, `backend/shared/python/sunity_shared/models.py`, and `docs/contract.md`.
- `20-03-PLAN.md:189` says `scoreSuppressed?: boolean` should be added using the Task 2 pattern, but that is not reflected in Task 3 files or acceptance.
- `20-03-PLAN.md:237` mentions `scoreSuppressed schema 키 추가`, but the detailed task does not lock it.

**Why it matters:** D-08 is user-facing trust behavior. It deserves the same contract discipline as `visionVeto`.

**How I would fix it:**

- Decide the location explicitly:
  - preferred: `result.scoreSuppressed?: boolean` if it controls the whole result display;
  - acceptable: `comparison.scoreSuppressed?: boolean` if strictly Mode3 comparison-local.
- Add `scoreSuppressed` to:
  - `app/src/types/analysis.ts`
  - `backend/shared/python/sunity_shared/models.py`
  - `docs/contract.md`
- Add a 3-way grep/enum acceptance criterion, similar to `visionVeto`.
- Include those files in Task 3 or expand Task 2 to cover both `visionVeto` and `scoreSuppressed`.

I would not rely on `scoringBasis` alone as the suppression signal. It is a source label; suppression is a display/trust policy.

### MEDIUM-1: `_gemini_vision_veto_enabled()` ownership is still ambiguous across pipeline and shared adapter

**Risk:** 20-03 says the toggle owner can be pipeline or adapter, but 20-02's shared adapter action still says `assess_fault_severity()` checks `_gemini_vision_veto_enabled()`. A shared analysis module should not import `backend/functions/pipeline/app.py`, and duplicating the env helper creates drift risk.

**Evidence:**

- `20-02-PLAN.md:107` says `assess_fault_severity()` checks `_gemini_vision_veto_enabled()`/key.
- `20-03-PLAN.md:105` says toggle ownership is pipeline or adapter, "one place", and pipeline uses it for gates.
- `20-03-PLAN.md:108-109` already guards OFF before calling the adapter.

**Why it matters:** Toggle drift can recreate the no-op bug: pipeline preserves video, but adapter decides disabled, or vice versa. Import direction can also become architecturally wrong.

**How I would fix it:**

- Make pipeline the owner of `GEMINI_VISION_VETO_ENABLED`.
- Make `gemini_vision_scorer.assess_fault_severity()` check only adapter-local prerequisites: API key/client, cache, local file, Gemini response validity.
- Add acceptance:
  - `gemini_vision_scorer.py` does not import `backend.functions.pipeline` or define `_gemini_vision_veto_enabled`.
  - `_apply_vision_veto` is the only feature-toggle gate.

Alternative: create a tiny shared config helper in `sunity_shared`, but then both pipeline and adapter must import that same helper. I prefer pipeline ownership because it keeps the adapter reusable and side-effect-light.

### MEDIUM-2: Phase gate proves `status='applied'` for kip-up, but not that vision ran for every eval row

**Risk:** 20-04 now requires `visionVeto.status='applied'` for kip-up, which is good. But D-04 says vision is always called for Mode1/Mode3 scoring. V-2/V-3 success and regression rows can still pass by score alone even if their `visionVeto.status` is `disabled`, `missing_local_video`, or `skipped_error`.

**Evidence:**

- `20-VALIDATION.md:47` ties status proof to V-1 kip-up only.
- `20-VALIDATION.md:48-49` define V-2/V-3 by score outcome only.
- `20-04-PLAN.md:139` requires `status='applied'` only for kip-up.

**Why it matters:** "정타 95~100 유지" is only meaningful if the veto actually evaluated the clean posture and chose not to cap it. If vision skipped, the score staying high does not prove the clean-path invariant.

**How I would fix it:**

- In `assert_baseline_v2.py --phase-gate`, require every eval row to have an allowed non-skip status:
  - false-positive/fault cases expected to drop: `applied`
  - clean/above-cutoff cases expected to stay high: `not_applicable`
  - never allowed in phase-gate rows: `disabled`, `missing_local_video`, `skipped_error`, absent `visionVeto`
- Add counts to `eval20_gate_report.json`:
  - `vision_veto_status_counts`
  - `rows_without_veto_status`
  - `skipped_error_rows`

This turns D-04 from a code-path assertion into an eval artifact.

### MEDIUM-3: Sensitivity "minimum 2 buckets / total >=2" is too weak for a generalization gate

**Risk:** The fail-closed improvement prevents TODO assets, but the minimum bar can still be one `must_drop` and one `must_stay_high` video. That is technically a two-bucket sensitivity set, but it is not enough to justify cap derivation for a trust-critical score change.

**Evidence:**

- `20-04-PLAN.md:20` requires minimum 2 distinct buckets.
- `20-04-PLAN.md:55` says bucket completion allows cap derivation.
- `20-04-PLAN.md:102` gives example minimum "bucket 당 ≥1, 총 ≥2".

**Why it matters:** This phase is explicitly avoiding curve-fit to a tiny 6-pair set. A 2-video sensitivity set is still too small to carry that claim.

**How I would fix it:**

- Define a concrete minimum before cap derivation. My suggested floor:
  - `must_drop`: at least 2 videos across at least 2 motion ids;
  - `must_stay_high`: at least 3 videos across at least 2 motion ids;
  - at least 2 distinct capture sessions or camera setups if available.
- If assets are unavailable, leave `SEVERITY_CAP` as placeholder and keep 20-04 blocked.
- Record the diversity summary in `eval20_gate_report.json`.

This is still modest, but it is meaningfully better than 1+1.

### MEDIUM-4: `--phase-gate` fail-closed behavior is in acceptance, but not in the automated verify command

**Risk:** 20-04 Task 1's verify command only runs `--self-check`. The acceptance criteria mention that `--phase-gate` must fail when the baseline is missing, but the automated command does not prove it.

**Evidence:**

- `20-04-PLAN.md:110-112` verify only runs `assert_baseline_v2.py --self-check`.
- `20-04-PLAN.md:115` acceptance requires `--phase-gate` absent-baseline non-zero.
- `20-VALIDATION.md:57` says V-11 includes argparse mode branch and terminal evidence checks.

**Why it matters:** This is exactly the false-green class fixed in iteration 1. If fail-closed mode is not tested in pod-free automation, it can regress.

**How I would fix it:**

- Add a pod-free unit test for `assert_baseline_v2` mode behavior.
- Or add a script-level pytest that runs `--phase-gate` against a temp empty baseline dir and asserts non-zero.
- Keep `--self-check` as the quick command, but make V-11 automated through pytest, not manual acceptance prose.

## Non-Blocking Notes

- `VisionVetoCache` versioning is much better than the first plan. I would also include `input_granularity` explicitly in the key even when `at_seconds` is only a prompt hint, so future frame-input optimization does not collide with whole-video verdicts.
- `visionVeto` would be stronger as a TypeScript discriminated union:

```ts
type VisionVeto =
  | { status: 'applied'; severity: VisionSeverity; capApplied: number }
  | { status: 'not_applicable'; severity?: VisionSeverity; capApplied?: never }
  | { status: 'disabled' | 'skipped_error' | 'missing_local_video'; severity?: never; capApplied?: never };
```

This prevents `status: 'applied'` without `capApplied` at compile time.

## Verdict

**Improved, but not execution-ready yet.**

I would patch HIGH-1 through HIGH-3 before implementation. MEDIUM-1 through MEDIUM-4 can be patched in the same sweep because they are mostly plan wording and test acceptance changes, not architecture changes.

The biggest practical action: make the Mode3 score suppression contract complete, and make the 20-03 cap-path test explicitly monkeypatch a numeric cap while real caps remain blocked until 20-04.
