# Phase 15 Direct Plan Review

**Reviewed:** 2026-06-17  
**Reviewer:** Codex direct review, no external GSD/agent review used  
**Scope:** `15-01-PLAN.md` .. `15-05-PLAN.md`, `15-CONTEXT.md`, `15-RESEARCH.md`, `15-VALIDATION.md`, and local code contracts referenced by the plans.

## Verdict

**Needs revision before execution.** The plan has the right high-level sequence: prepare sweep tools, revive Pod/Lambda, run real E2E evidence, then build/submit and hand off device verification. It also correctly blocks on real Pod/LLM evidence and avoids dry-run-only completion.

However, I found several execution risks that can produce false PASS evidence or block TestFlight delivery. The biggest issues are: Mode 3 sweep docs may not be discoverable as "previous" analyses, reference downstream field verification uses the wrong tool, and the current `preview` EAS profile is internal distribution while the plan expects TestFlight submission.

## Findings

### HIGH 1. Mode 3 sweep can fail to produce `deltaFromPrevious`

**Evidence**
- `backend/shared/python/sunity_shared/firestore_admin.py::get_previous_analysis` queries `status == done`, orders by `createdAt`, and skips the current doc.
- The canonical script `backend/scripts/sweep_phase8_1.py` writes `sweepCreatedAtMs`, but not `createdAt`.
- `15-01-PLAN.md` tells `sweep_phase15.py` to adapt `sweep_phase8_1.py`.
- `15-04-PLAN.md` depends on same-uid fail -> success docs producing `comparison.deltaFromPrevious`.

**Risk**
If `sweep_phase15.py` copies the Phase 8.1 doc shape and omits `createdAt`, Firestore's `order_by("createdAt")` query can exclude those sweep docs from previous-analysis lookup. Mode 3 would look like a first analysis or pair against the wrong document, while the sweep itself might still complete.

There is a second pairing risk: if all 6 pairs share one uid, a success doc must prove its `previousAnalysisId` is the matching fail doc for the same motion, not just any prior mode3 doc.

**How I would fix it**
- Add to `15-01-PLAN.md` Task 1 acceptance: `sweep_phase15.py` must set `createdAt` and `updatedAt` on every analysis doc.
- For Mode 3, use one throwaway uid per motion pair, or enforce monotonically increasing `createdAt` per fail/success pair.
- Add to `15-04-PLAN.md` acceptance: each success doc must satisfy `comparison.previousAnalysisId == <paired_fail_analysis_id>` and `deltaFromPrevious` is non-empty.
- Add a `--pair-sequential` mode to `sweep_phase15.py` so fail and success are never submitted in parallel.

### HIGH 2. Reference downstream field gate is not actually checked by the planned command

**Evidence**
- `15-03-PLAN.md` Task 1 says `backfill_reference_downstream.py --check-firestore` verifies `bodyNormalizationProfile`, `bodyComparisonSourcePose`, `techniqueProfile`, and `forceDirectionPattern`.
- The actual `_run_check_firestore()` only verifies `activeVersion`, `angles`, `anglesJointKeys`, `anglesFrames`, and frame-count sanity.
- The real Firestore merge tool for downstream fields is `app/scripts/seed-reference-downstream.mjs`; it supports `--verify` for `meanAngles`, `techniqueProfile`, `bodyNormalizationProfile`, `forceDirectionPattern`, and `captureViews`.

**Risk**
Plan 03 can mark the 11-reference field gate PASS even while the Mode 1 downstream fields are missing. That would defer failure to the expensive live E2E run, or worse, permit fallback behavior that weakens the evidence.

**How I would fix it**
- Keep `backfill_reference_downstream.py --check-firestore` only as the stored-angle sanity gate.
- Add an explicit downstream verification step:
  - `cd app && node scripts/seed-reference-downstream.mjs --input ../reference-downstream-backfill.json --verify`
  - Or add a new Python read-only checker that verifies the exact 4 Mode-1 fields plus `meanAngles`/`captureViews`.
- If fields are missing, make the plan a two-step repair:
  - Generate/update fixture with `backend/scripts/backfill_reference_downstream.py --bucket ... --output reference-downstream-backfill.json`.
  - Apply with `cd app && node scripts/seed-reference-downstream.mjs --input ../reference-downstream-backfill.json --repair-missing --motions <missing ids>`.
  - Re-run `--verify` and require `completeRequiredSet = 11/11`.

### HIGH 3. `preview` EAS build profile is internal distribution, but the plan expects TestFlight

**Evidence**
- `app/eas.json` has `build.preview.distribution = "internal"`.
- Expo docs distinguish preview builds as internal/ad hoc and not signed for app stores, while production builds are submitted to app stores or TestFlight.
- Expo's iOS submit docs say a production build is needed for store submission and show TestFlight workflows using `profile: production`.

**Risk**
`15-05-PLAN.md` says "EAS preview build + submit" to TestFlight. With the current `preview` profile, this is likely to produce an internal/ad hoc build that cannot be submitted to App Store Connect/TestFlight. The plan may block late after backend E2E is already done.

**How I would fix it**
- Do not reuse the internal `preview` profile for TestFlight.
- Add a separate store-signed profile, for example `testflight-preview`, that uses the preview channel/env but omits `distribution: "internal"`:
  - `channel: "preview"`
  - same `env` as production
  - `autoIncrement: true`
  - iOS resource class as needed
- Build and submit that profile: `eas build --profile testflight-preview --platform ios --auto-submit` or build first, then `eas submit --platform ios --profile production`.
- Keep the existing `preview` profile for direct internal install only.

### MEDIUM 4. Mode 3 success criteria says degree improvement, but current contract is score-point delta

**Evidence**
- `docs/contract.md` defines `deltaFromPrevious` as dimension score deltas, keyed by `line`, `stability`, and optionally `angle`.
- `backend/shared/python/sunity_shared/analysis/assemble.py::build_mode3` computes `cur_dimension_scores[d] - prev_dimension_scores[d]`.
- `app/src/app/analysis/result.tsx` renders "지난 분석보다 N점 발전했어요!".
- `15-CONTEXT.md` and `15-04-PLAN.md` still use examples like "무릎 신전 8° 개선".

**Risk**
If Phase 15 is validation-only, it cannot honestly prove a degree-level knee-extension delta because the current product contract exposes score deltas, not joint-angle deltas. This can create a false product claim during device UAT.

**How I would fix it**
- If Phase 15 remains validation-only, revise the plan text and acceptance to "N점 발전" / dimension score delta.
- If "무릎 신전 8° 개선" is truly required, split it into an implementation task before validation:
  - add a joint-angle delta field to backend result shape,
  - update `app/src/types/analysis.ts`, `backend/shared/python/sunity_shared/models.py`, and `docs/contract.md` lockstep,
  - render the degree delta in UI,
  - add regression tests.

### MEDIUM 5. Frozen threshold YAML path is inconsistent in planning docs

**Evidence**
- Actual loader path in `force_signals.py` resolves to `backend/judging_data/tilt_thresholds.yaml`.
- `sweep_phase8_1.py` also uses `backend/judging_data/tilt_thresholds.yaml`.
- The current checksum matches the frozen evidence: `c94bb8c7cc87120255c244548bd59464840130cbf9144fd109490588a3e1e87c`.
- `15-CONTEXT.md` lists `backend/shared/python/sunity_shared/analysis/tilt_thresholds.yaml`, which does not exist.

**Risk**
An implementer can build `assert_falsepositive_gate.py` against the wrong path, fail open into fallback, or fail closed for the wrong reason. That weakens the SCORE-04 gate.

**How I would fix it**
- Update Phase 15 docs to name `backend/judging_data/tilt_thresholds.yaml` as the only source-of-truth.
- In `assert_falsepositive_gate.py`, import or mirror the same path used by `force_signals.py`.
- Require the evidence doc to show both:
  - checksum equals `c94bb8...e87c`
  - `tilt_thresholds_fallback` count is 0 in all analyzed force-signal warnings.

### MEDIUM 6. SCORE-04 assert terms are under-specified

**Evidence**
- Plans use terms like "overallScore 높음", "높은 점수 안 줌", and "fault-caught".
- The frozen 08.1 evidence objectively defines success axis severity as 25/25 `low`, but it does not define a fail-video score cutoff or exact fault-detection fields for the new failure videos.

**Risk**
The assert script can become subjective or arbitrary. Because Phase 15 explicitly bans human score labels, the plan needs objective machine criteria before execution starts.

**How I would fix it**
- Define constants in `15-03-PLAN.md` before writing the assert script:
  - success gate: exact axis severity expectation and minimum acceptable score/dimension thresholds, if any.
  - fail gate: max acceptable overall/dimension score, or required finding/deficit keys by motion/fault label.
  - objectivity rule: no human-authored score labels, only fault category labels.
- If exact fault criteria cannot be defined now, downgrade fail-video fault assertions to "manual evidence review" and move automated per-fault gating to Phase 18.

### LOW 7. Runtime SIGABRT cannot be proven by EAS build logs

**Evidence**
- `15-05-PLAN.md` Task 2 accepts "build log SIGABRT/native crash 0".
- The known issue is a release runtime crash after interaction; a build log cannot prove that path.
- The human TestFlight checkpoint does cover runtime launch/tap flow.

**Risk**
Claude-side evidence can overclaim crash freedom before the physical-device check.

**How I would fix it**
- Reword Task 2 acceptance to static/build checks only: typecheck, `track=()=>0`, no negative letterSpacing pattern, build success, submit success.
- Keep runtime SIGABRT as a required belle TestFlight checkpoint result.
- Record device result in `15-DELIV-EVIDENCE.md`, not just build logs.

## Positive Notes

- The current plans correctly gate real E2E on live Pod bring-up and Lambda URL sync.
- The dual-LLM "both fail => blocking escalation" branch in `15-02-PLAN.md` closes a real silent-fallback risk.
- `15-03-PLAN.md` now requires SC4 crash/failure tally evidence, which fixes the earlier implicit coverage gap.
- `15-03` and `15-04` no longer treat dry-run or pytest pre-checks as sufficient completion evidence.
- The objectivity boundary is correctly stated: human-authored analysis docs are not score ground truth.

## Recommended Patch Order

1. Patch `15-01` and `15-04` for Mode 3 createdAt/pairing guarantees.
2. Patch `15-03` reference verification/backfill commands to use `seed-reference-downstream.mjs --verify` and the two-step repair path.
3. Patch `15-05` to introduce a store-signed TestFlight profile separate from internal `preview`.
4. Decide whether Mode 3 UAT expects point deltas or degree deltas; revise plan wording or add a real implementation task.
5. Patch threshold path and SCORE-04 assert constants before writing `assert_falsepositive_gate.py`.

