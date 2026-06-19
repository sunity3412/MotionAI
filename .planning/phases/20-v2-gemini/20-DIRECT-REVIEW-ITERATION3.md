# Phase 20 Direct Review - Iteration 3

**Reviewed:** 2026-06-19  
**Reviewer:** Codex direct review (not external reviewer)  
**Scope:** latest Phase 20 planning commit (`4252134`), updated `20-01~04-PLAN.md`, `20-CONTEXT.md`, `20-RESEARCH.md`, `20-VALIDATION.md`, prior direct reviews  
**Review stance:** third-pass execution-readiness review. Focus = false-green routes introduced by the iteration-2 fixes, especially tests that are specified but not actually runnable.

## Summary

Iteration 2 closed most of the previous hard gaps on paper:

- `keep_local_video` now includes the veto toggle.
- cap mutation is tested with a scoped `SEVERITY_CAP['major']=50` monkeypatch while production caps remain placeholder.
- `scoreSuppressed` is contract-locked in `analysis.ts` / `models.py` / `docs/contract.md`.
- adapter toggle ownership is now pipeline-only.
- 20-04 now has `--phase-gate` fail-closed pytest, per-row `visionVeto.status`, and a stronger sensitivity diversity floor.

I would still patch the items below before execution. The biggest remaining blocker is that the plan requires an RN render/component test, but the app repo currently has no app test runner or test script. That can make V-8 look covered while only `npm run typecheck` actually runs.

## Findings

### HIGH-1: V-8 requires an RN render test, but the app has no runnable test path

**Risk:** 20-03 and 20-VALIDATION now correctly require a render/component test proving suppressed Mode3 hides the entire score card. However, the actual verify command only runs backend pytest plus `npm run typecheck`, and `app/package.json` has no `test` script or configured app test dependency surface. The result is a false-green path: the plan can claim `test_result_suppressed_hides_full_score_card GREEN` while no render assertion ever runs.

**Evidence:**

- `20-03-PLAN.md:197` requires `test_result_suppressed_hides_full_score_card` as an RN render/component test.
- `20-03-PLAN.md:223` verifies only backend pytest plus `cd ../app && npm run typecheck`.
- `20-03-PLAN.md:231` repeats the render-test acceptance criterion, but does not name an executable app test command.
- `20-VALIDATION.md:55` defines V-8 as "RN render/component test".
- `20-VALIDATION.md:78` maps 20-03-T3 to "unit (mocked) + RN render", but the command still ends in `npm run typecheck`.
- `app/package.json:5-13` has scripts for `start`, platform runs, `web`, `typecheck`, and seed scripts only. No `test`.

**Why it matters:** The previous failure was overconfident UI. TypeScript can pass while `OctagonScore`, grade badge, summary, caption, or header copy still render. For this phase, UI absence is behavior, not cosmetics.

**How I would fix it:**

- Preferred: add a real app test command and test file to the plan:
  - add `app/src/app/analysis/result.test.tsx` or a colocated render test;
  - add `app/package.json` `test` script;
  - include the script in 20-03 verify, for example `cd app && npm run test -- result`;
  - add any required test config explicitly to `files_modified`.
- If adding a render runner is too much for this phase, do not pretend it is a render test. Add a pod-free static assertion script instead, such as `app/scripts/assert-result-score-suppression.mjs`, and verify it in CI. It should fail unless:
  - `isScoreSuppressed` gates the entire score-card branch;
  - `OctagonScore`, `gradeBadge`, `LevelBenchmark`, score caption, score-derived summary, and "점수를 확인해보세요" are all under the non-suppressed branch.
- Update `20-VALIDATION.md` and 20-03 acceptance to name the actual executable command.

My call: I would use the static script if the app currently has no test culture. It is less ideal than render testing, but it is real automation and avoids introducing a Jest/React Native testing stack mid-phase.

### HIGH-2: `isScoreSuppressed` reintroduces `scoringBasis` as a suppression signal despite saying it must not

**Risk:** 20-03 now says `scoreSuppressed` is a 3-way contract and "scoringBasis 단독을 억제 신호로 쓰지 않는다." But the planned frontend boolean still includes `result.scoreSuppressed === true || <reference-free scoringBasis 판정>`. That fallback makes `scoringBasis` a suppression signal again. It can hide contract drift because the backend can fail to emit `scoreSuppressed` and the UI still appears to work by inferring from `scoringBasis`.

**Evidence:**

- `20-03-PLAN.md:23` says scoringBasis alone must not be used as the suppression signal.
- `20-03-PLAN.md:167` repeats that `scoreSuppressed` is the display/trust policy and `scoringBasis` is only a source label.
- `20-03-PLAN.md:214` defines `isScoreSuppressed = cmp.mode === 'mode3' && (result.scoreSuppressed === true || <reference-free scoringBasis 판정>)`.
- `20-VALIDATION.md:55` says V-8 requires `scoreSuppressed` 3-way lockstep and no scoringBasis-only dependency.

**Why it matters:** The whole point of adding `scoreSuppressed` was to make backend intent explicit and testable. The fallback weakens that contract and can let the implementation regress back to "label drives policy."

**How I would fix it:**

- For new Phase 20 documents, make frontend suppression strictly `result.scoreSuppressed === true`.
- If legacy documents need fallback behavior, name it separately and make it visibly legacy-only:
  - `const isLegacyReferenceFreeWithoutSuppressionFlag = ...`
  - do not count that fallback as satisfying V-8 or the 3-way contract.
- Add an acceptance test/static check that a Phase 20 result with `reference_free_absolute` but missing `scoreSuppressed` does not pass the contract test. It should be treated as producer-contract failure, not silently inferred in UI.

My call: I would remove the fallback from this phase. Optional legacy tolerance can be a separate compatibility branch, but the trust-critical path should fail loud when the backend omits the flag.

### MEDIUM-1: `low_confidence` is conflated with "미보유/기준 없음"

**Risk:** 20-03 uses `category in {unregistered, low_confidence} OR is_reference_free_motion(...)` to set `scoreSuppressed=True` and show "기준 없음." That is safe against overconfident scores, but it changes the meaning of low recognizer confidence. `low_confidence` means "the recognizer could not confidently classify this video"; it does not necessarily mean "the project has no basis/reference for this move."

**Evidence:**

- `20-CONTEXT.md:34-35` defines branch 3 as neither IPSF-listed nor Eunji-held, displayed as "기준 없음."
- `gemini_technique_recognizer.py:14-18` documents separate fallback cases: `low_confidence` and `unregistered`.
- `gemini_technique_recognizer.py:168-181` returns category `low_confidence` when mean confidence is below threshold, with `motion_id=None`.
- `gemini_technique_recognizer.py:186-205` separately returns category `unregistered` for true unregistered scope.
- `assemble.py:130-150` defines reference-free from branch metadata, not recognizer confidence.
- `20-03-PLAN.md:194` requires `unregistered, low_confidence` to agree with `is_reference_free_motion`.
- `20-03-PLAN.md:213` OR-combines both into 미보유 handling.

**Why it matters:** Showing "기준 데이터가 없어 정확한 점수를 드릴 수 없어요" for a known move with low recognizer confidence is misleading. It also makes A2 impossible to interpret: a low-confidence classification and an ipsf_map branch disagreement are not the same class of issue.

**How I would fix it:**

- Keep the safety behavior: suppress confident score for `low_confidence`.
- Split the reason:
  - `scoreSuppressedReason='unheld'` for true branch-3 / unregistered / reference-free.
  - `scoreSuppressedReason='recognition_low_confidence'` for recognizer uncertainty.
- Contract that reason alongside `scoreSuppressed` in `analysis.ts`, `models.py`, and `docs/contract.md`.
- UI copy should differ:
  - unheld: "기준 없음"
  - low confidence: "동작 인식 신뢰도가 낮아 기준을 확정할 수 없어요"
- Change A2 from "must agree" to "must reconcile with explicit reason." Disagreement should be reported in audit fields, not hidden under one branch.

My call: I would still suppress the score for low confidence. I would not call it "기준 없음" unless branch metadata actually proves no IPSF/Eunji basis.

### MEDIUM-2: 20-04 per-row status rule over-requires `applied` for every fault row

**Risk:** The new per-row gate says fault/false-positive rows that should drop must have `visionVeto.status='applied'`, while clean/above-cutoff rows must have `not_applicable`. That is correct for kip-up and sensitivity `must_drop` rows. It is too broad for all existing fault rows in the 4 already-discriminating pairs. A fault row can remain correctly below its success row through v1 scoring alone; Gemini may legitimately return minor/none and `not_applicable`. Requiring `applied` on every fault row can pressure implementers to over-cap rows just to satisfy the status gate.

**Evidence:**

- `20-04-PLAN.md:24` says fault/false-positive rows map to `applied`, clean/above-cutoff rows to `not_applicable`.
- `20-04-PLAN.md:65` repeats the same every-row rule.
- `20-04-PLAN.md:117` encodes that rule in `assert_baseline_v2.py --phase-gate`.
- `20-04-PLAN.md:157-163` specifically lists kip-up as `applied` and clean/sensitivity as `not_applicable`, but the generic rule still says every fault row must apply.
- `20-VALIDATION.md:61` repeats the same V-14 mapping.

**Why it matters:** This can turn a good non-regression case into a false fail, or worse, nudge cap derivation toward unnecessary deductions. The terminal gate should prove vision did not skip; it should not force a cap when v1 already discriminates and Gemini does not see a major veto-worthy defect.

**How I would fix it:**

- Move expected veto status into the eval manifest per row instead of deriving it from generic fault/clean labels.
- Suggested gate:
  - `must_drop` rows, including kip-up: require `status='applied'` and expected score bound.
  - `must_stay_high` rows: require `status='not_applicable'` and high-score bound.
  - regression fault rows that already discriminate: allow `status in {'applied', 'not_applicable'}` but still require `fault < success` and no skipped statuses.
  - all rows: forbid `disabled`, `missing_local_video`, `skipped_error`, absent `visionVeto`.
- Record counts by status and by expected bucket in `eval20_gate_report.json`.

My call: I would make status expectation data-driven. That keeps D-04's "vision ran" proof without turning "fault row" into "must cap."

## Requested Focus Points

### Downward-only invariant

The mathematical path is now structurally strong: production cap values remain placeholder until 20-04, and 20-03 proves mutation with a scoped cap monkeypatch. I do not see a remaining direct "vision can raise score" hole in the plan. The remaining risk is skipped or over-broad application, not upward mutation.

### Curve-fit prohibition

The iteration-2 diversity floor is much better. The main remaining curve-fit pressure is indirect: if 20-04 requires `applied` on all fault rows, implementers may tune severity/caps to satisfy status expectations rather than generalization. MEDIUM-2 is the fix I would make.

### Objectivity

The vision schema/objectivity direction is now adequate on paper: no score fields, schema/dataclass introspection, and prompt/schema cache versioning. The new objectivity issue is semantic, not schema-level: `low_confidence` should not be reported as "기준 없음" unless branch metadata supports that claim.

### Pod sequencing

20-04 is much stronger after iteration 2: self-check is non-approval, `--phase-gate` fails closed, and pod-free pytest covers the fail-closed path. I would keep the terminal gate blocking. The only sequencing tweak I would make is data-driven expected status per eval row.

## Verdict

**Closer, but still not execution-ready.**

I would block execution on HIGH-1 and HIGH-2 because they can create false greens in the exact user-facing trust surface this phase is meant to fix. MEDIUM-1 and MEDIUM-2 should be patched in the same pass because they are small plan/contract changes that prevent misleading UX and over-constrained eval behavior.
