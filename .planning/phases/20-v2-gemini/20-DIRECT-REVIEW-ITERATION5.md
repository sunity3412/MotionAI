# Phase 20 Direct Review - Iteration 5

**Reviewed:** 2026-06-19  
**Reviewer:** Codex direct review (not external reviewer)  
**Scope:** latest Phase 20 planning commit (`52ed54e`), updated `20-03-PLAN.md`, `20-04-PLAN.md`, `20-VALIDATION.md`, prior direct reviews  
**Review stance:** fifth-pass execution-readiness review. Focus = whether iteration-4 fixes are now structurally locked, and whether the new manifest/validation layer can still become a tuning surface.

## Summary

Iteration 4 fixed the two big issues from the previous review:

- `low_confidence` now has a dedicated resolver path and no longer has to collapse through `_SAFE_DEFAULT_BRANCH` into `unheld`.
- phase18 row policy is no longer supposed to be inferred from names or pair ids; `eval_manifest.yaml` is now the row-local authority.
- the suppression script is cwd-stable and self-tested.
- duplicate output tags were cleaned up.

I still see two issues I would patch before execution:

- `eval_manifest.yaml` can now become the place where expected policy is changed after seeing Pod/sweep results unless its policy fields are frozen before derivation/gate.
- `low_confidence` may still leak "기준 동작 없음" through `scoringBasisLabel` even if the header copy is reason-specific.

## Findings

### HIGH-1: `eval_manifest.yaml` is authoritative, but not yet frozen before sweep/derivation

**Risk:** Iteration 4 correctly adds `eval_manifest.yaml` as the source of `expected_bucket`, `allowed_veto_statuses`, and score expectations. But the plan only says the manifest is hashed and reported by the gate. It does not require the policy portion of the manifest to be committed/frozen before Pod sweep, sensitivity collection, cap derivation, or baseline snapshot. That means the system has moved away from pair-id hardcoding, but the manifest itself can become the new goalpost-moving surface.

**Evidence:**

- `20-04-PLAN.md:25-26` makes `eval_manifest.yaml` the authority for every row's expected status/bucket and score/verdict expectation.
- `20-04-PLAN.md:39-43` says `assert_baseline_v2.py` reads the manifest and reports its hash.
- `20-04-PLAN.md:157-160` accepts manifest-sourced policy, but only checks that the implementation reads the manifest, not when or how the manifest policy was frozen.
- `20-04-PLAN.md:178-188` fills sensitivity/eval manifest keys, derives caps, re-sweeps, and reports the gate hash in one Pod workflow. The report hash proves what was used at the end, not that policy was independent of observed outputs.

**Why it matters:** This phase is explicitly about avoiding curve-fit. Excluding phase18 rows from `derive_caps.py` is necessary, but not sufficient if `expected_bucket`, `allowed_veto_statuses`, `max_score`, `min_score`, or `fault_must_be_lt_success` can be edited after seeing sweep output.

**How I would fix it:**

- Split manifest fields into locked policy vs collected asset fields:
  - locked: `row_id`, `expected_bucket`, `allowed_veto_statuses`, score/verdict expectation, source dataset class
  - fillable before first scored run: concrete `source.key` for newly collected sensitivity videos
- Require a pre-sweep policy hash, e.g. `eval_manifest_policy_sha256_pre_sweep`, recorded before cap derivation.
- Make `assert_baseline_v2.py --phase-gate` report both the locked policy hash and the full manifest hash. If policy fields changed after derivation began, fail or require an explicit review note.
- In the Pod how-to, add a hard step: commit/freeze manifest policy before the first sweep used for cap derivation. After that, only video asset keys may be filled.

My call: this is the remaining curve-fit risk. I would block Pod execution until manifest policy freezing is explicit.

### HIGH-2: `low_confidence` can still show "기준 동작 없음" through `scoringBasisLabel`

**Risk:** The resolver now separates `recognition_low_confidence` from `unheld`, and the header copy is planned to branch by `scoreSuppressedReason`. But existing UI also renders `cmp.scoringBasisLabel`. Existing backend label mapping says `reference_free_absolute` means "기준 동작 없음." If the low-confidence suppressed path still carries that basis/label, the page can simultaneously say "동작 인식 신뢰도가 낮음" and "기준 동작 없음."

**Evidence:**

- `backend/shared/python/sunity_shared/analysis/assemble.py:597-603` maps reference-free Mode3 bases to "기준 동작 없음" labels.
- `app/src/app/analysis/result.tsx:682-683` renders `cmp.scoringBasisLabel` whenever it is present.
- `20-03-PLAN.md:241` still routes suppressed results through `scoringBasis`/`scoringBasisLabel` work; the exact low-confidence label override is not locked as an acceptance test.
- `20-03-PLAN.md:273` explicitly checks reason-specific header copy, but not that the visible `scoringBasisLabel` also avoids "기준 없음" for `recognition_low_confidence`.
- `20-VALIDATION.md:59` still describes V-8 broadly as "기준 없음", while `20-VALIDATION.md:69-70` says low confidence must not be labeled as unheld.

**Why it matters:** This is the same semantic class as the previous low-confidence collapse bug, just through a second UI field. The score may be hidden correctly, but the user-facing reason can still be wrong.

**How I would fix it:**

- Make reason-specific suppression copy canonical for all visible suppressed-state text, not just the header.
- Add an explicit mapping:
  - `unheld` -> basis/copy may say 기준 데이터 없음
  - `recognition_low_confidence` -> copy says recognition confidence is low; it must not contain "기준 없음" or "기준 동작 없음"
- Add backend test: `test_low_confidence_scoring_basis_label_not_unheld`.
- Extend `assert-result-score-suppression.mjs` or a targeted source assertion so the low-confidence branch cannot render the legacy reference-free label.

My call: do not leave `scoringBasisLabel` derived from `scoringBasis` alone once suppression reason exists. The reason should own the copy.

### MEDIUM-1: Validation commands are still cwd/PYTHONPATH ambiguous

**Risk:** The plan-level verify commands use `cd backend && PYTHONPATH=shared/python ...`, but the validation table's quick/full commands run backend pytest from repo root without the same `PYTHONPATH`. The per-task table also lists `pytest tests/...` commands without declaring the working directory. This can produce false red or inconsistent local verification.

**Evidence:**

- `20-VALIDATION.md:28-29` uses `python -m pytest backend/tests/ -q` and `python backend/evals/phase20/assert_baseline_v2.py --self-check` from repo root, with no `PYTHONPATH=backend/shared/python`.
- `20-03-PLAN.md:258` uses `cd backend && PYTHONPATH=shared/python ...`.
- `20-04-PLAN.md:148` uses `cd backend && PYTHONPATH=shared/python ...`.
- `20-VALIDATION.md:85-86` lists `pytest tests/...` and `python evals/...` paths that only make sense from `backend/`, but that cwd is not stated in the command.

**Why it matters:** The plan is now execution-heavy. A reviewer or implementer following the validation table should get the same result as the task plans.

**How I would fix it:**

- Standardize all backend validation commands to the exact same shape:

```bash
cd backend && PYTHONPATH=shared/python python -m pytest tests/ -q
```

- For phase20 self-check/gate, also run from backend:

```bash
cd backend && PYTHONPATH=shared/python python evals/phase20/assert_baseline_v2.py --self-check
```

- Or add one checked-in wrapper script and make every table point to it.

My call: this is not architectural, but I would patch it now because it prevents noisy execution failures.

### MEDIUM-2: A2 audit still has two possible sinks, so the invariant is not contract-locked

**Risk:** The A2 reconcile plan says category/branch mismatch is reported through `result['scoreSuppressionAudit']` dict or `log.warning`. That leaves implementers free to choose either, and tests can accidentally assert the weaker one. The invariant is important enough to have exactly one observable contract.

**Evidence:**

- `20-03-PLAN.md:243` says mismatch is reported by `result['scoreSuppressionAudit'] dict 또는 log.warning`.
- `20-03-PLAN.md:268` accepts "audit 필드/log 보고", again leaving the sink optional.
- `20-VALIDATION.md:69` says mismatch audit is reported, but does not define the required observable field or log code.

**Why it matters:** A2 exists because recognizer category and `ipsf_map` branch metadata have different provenance. If mismatch reporting is optional or split, future debugging can lose the evidence needed to know why a suppressed result chose one reason over the other.

**How I would fix it:**

- Pick one required sink. I would use a structured field because it is easiest to assert and preserve in terminal artifacts:

```json
"scoreSuppressionAudit": {
  "recognizerCategory": "low_confidence",
  "branchReferenceFree": true,
  "resolvedReason": "recognition_low_confidence"
}
```

- If logs are still useful, make them additive, not an alternative.
- Add `test_recognizer_ipsf_map_reconcile` assertions for exact keys and values.

My call: remove the "or." A single structured audit contract is more useful than a warning that may disappear in async or Pod logs.

## Requested Focus Points

### Downward-only invariant

Structurally strong after the prior fixes. I do not see a remaining score-increase path in the plan. The cap mutation test and `min(current_score, cap)` style invariant still cover the important path.

### Curve-fit prohibition

Improved, but still not fully locked. The remaining curve-fit path is no longer "6 pairs are used by derive_caps"; it is "manifest policy is adjusted after seeing eval output." Freeze the policy fields before Pod execution.

### Objectivity

The vision schema/objectivity layer remains sound. The remaining objectivity-adjacent issue is user-facing reason leakage through `scoringBasisLabel`, not model prompt/schema leakage.

### Pod sequencing

The terminal gate design is now mostly sound: self-check is not approval, baseline absence fails closed, and Pod work is blocking. I would only standardize validation commands and freeze manifest policy before running the Pod workflow.

## Verdict

**Not execution-ready yet.**

I would patch HIGH-1 and HIGH-2 before Pod work. MEDIUM-1 and MEDIUM-2 are small enough to fix in the same pass and will make the execution/review trail cleaner.
