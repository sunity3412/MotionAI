# Phase 20 Direct Review - Iteration 4

**Reviewed:** 2026-06-19  
**Reviewer:** Codex direct review (not external reviewer)  
**Scope:** latest Phase 20 planning commit (`f57f3d7`), updated `20-03-PLAN.md`, `20-04-PLAN.md`, `20-VALIDATION.md`, prior direct reviews  
**Review stance:** fourth-pass execution-readiness review. Focus = whether iteration-3 fixes actually compose with existing code and whether new validation surfaces have authoritative data sources.

## Summary

Iteration 3 materially improved the plan:

- V-8 is no longer a fake RN render test; it now has a runnable Node static check.
- `isScoreSuppressed` is strict on `result.scoreSuppressed === true`.
- `low_confidence` is separated conceptually from "기준 없음" via `scoreSuppressedReason`.
- 20-04 no longer forces `applied` for every fault row.

I still would not execute yet. Two fixes need tightening before implementation:

- The current resolver plan can still classify `low_confidence` as `unheld` because existing code maps `motion_id=None` to the safe-default reference-free branch.
- The new "data-driven" per-row status rule does not yet define an authoritative manifest for the phase18 regression rows; only `sensitivity.yaml` gets `expected_veto_status`.

## Findings

### HIGH-1: `low_confidence` can still collapse back into `unheld`

**Risk:** Iteration 3 says `low_confidence` should produce `scoreSuppressedReason='recognition_low_confidence'`, not "기준 없음." But the planned priority says "둘 다 해당이면 미보유 branch metadata 의 'unheld' 우선." In the current code, `low_confidence` returns `motion_id=None`; `lookup_motion_branch(None)` returns `_SAFE_DEFAULT_BRANCH`; and `is_reference_free_motion(_SAFE_DEFAULT_BRANCH)` returns true. That means a low-confidence result can satisfy both signals and be assigned `unheld`, undoing the fix.

**Evidence:**

- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py:174-181` returns `category='low_confidence'` and `motion_id=None`.
- `backend/shared/python/sunity_shared/analysis/assemble.py:106-116` maps missing `motion_id` to `_SAFE_DEFAULT_BRANCH`.
- `backend/shared/python/sunity_shared/analysis/assemble.py:145-150` treats the safe-default branch as reference-free.
- `20-03-PLAN.md:229` says if both low-confidence and branch metadata apply, `'unheld'` wins.
- `20-03-PLAN.md:206` expects low confidence to emit `recognition_low_confidence`.

**Why it matters:** This is exactly the semantic bug iteration 3 intended to fix. A known or potentially known move with uncertain recognition can still be shown as "기준 없음."

**How I would fix it:**

- Add a dedicated resolver, e.g. `_score_suppression_reason(profile, branch_info)`, and test it directly.
- Resolver order should treat recognizer category as provenance:
  - `profile.category == 'low_confidence'` -> `recognition_low_confidence`, even if `motion_id=None` caused safe-default branch lookup.
  - `profile.category == 'unregistered'` -> `unheld`.
  - concrete branch metadata with unavailable basis -> `unheld`.
- Do not treat `_SAFE_DEFAULT_BRANCH` from `motion_id=None` as proof of unheld when the category is `low_confidence`.
- Add the exact regression test: `category='low_confidence', motion_id=None, branch_info=_SAFE_DEFAULT_BRANCH` must produce `recognition_low_confidence`.

My call: reason priority should be `low_confidence` first, then true unregistered/unheld. "Safe default because we do not know" is not the same as "the move is definitely unheld."

### HIGH-2: Data-driven per-row status has no source manifest for phase18 regression rows

**Risk:** 20-04 says `assert_baseline_v2.py` will read row-local `expected_veto_status` from a manifest. But the only planned manifest with that field is `sensitivity.yaml`, which covers `must_drop` and `must_stay_high`. The 6 phase18 rows, including kip-up and the 4 regression pairs, still come from `backend/evals/phase18/dataset/pairs.yaml`; the plan does not add a phase20 overlay manifest that assigns `expected_bucket` / allowed status to those rows.

**Evidence:**

- `20-04-PLAN.md:34-36` adds `expected_veto_status` only to `backend/evals/phase20/sensitivity.yaml`.
- `20-04-PLAN.md:118` defines `sensitivity.yaml` as two buckets: `must_drop` and `must_stay_high`.
- `20-04-PLAN.md:121` expects phase18 regression fault rows to allow `applied | not_applicable`, but does not name the data source for those row expectations.
- `20-04-PLAN.md:139-141` acceptance says the gate must not use generic fault labels, but no phase20 regression expectation file is listed in `files_modified`.
- `20-04-PLAN.md:7-15` lists baseline outputs, but no input manifest/overlay for phase18 regression expectations.

**Why it matters:** "Data-driven" can silently become hardcoded logic in `assert_baseline_v2.py`. That reintroduces the ambiguity iteration 3 was trying to remove, especially for kip-up vs already-discriminating fault rows.

**How I would fix it:**

- Add a source manifest, not just output fields. Options:
  - `backend/evals/phase20/eval_manifest.yaml`
  - or `backend/evals/phase20/phase18_expectations.yaml`
- Include every gate row with:
  - `row_id`
  - source dataset/key
  - `expected_bucket`: `must_drop | must_stay_high | regression | gate_blocked`
  - `allowed_veto_statuses`: list, not a single enum
  - score/verdict expectation, e.g. `max_score`, `min_score`, `fault_must_be_lt_success`
- Make `assert_baseline_v2.py` read this manifest for both phase18 and sensitivity rows.
- Keep `sensitivity.yaml` for generalization assets, but do not make it the only source of row-local status policy.

My call: do not let `assert_baseline_v2.py` infer phase18 row policy from names like "fault" or from hardcoded pair ids. Put it in a manifest and hash/report it.

### MEDIUM-1: `scoreSuppressedReason` is optional even when `scoreSuppressed=true`

**Risk:** The UI now depends on `scoreSuppressedReason` for different copy, but Task 2 makes both `scoreSuppressed?: boolean` and `scoreSuppressedReason?: ...` independently optional. That allows `scoreSuppressed=true` with no reason to pass typecheck and 3-way grep. The frontend then has to invent a default, which can easily fall back to the wrong "기준 없음" copy.

**Evidence:**

- `20-03-PLAN.md:33` describes both result fields as optional.
- `20-03-PLAN.md:173-180` adds `scoreSuppressed?: boolean` and `scoreSuppressedReason?: 'unheld' | 'recognition_low_confidence'`.
- `20-03-PLAN.md:234-235` makes header/scoring basis copy branch on `scoreSuppressedReason`.
- `20-03-PLAN.md:190-191` acceptance only greps that both fields exist in 3 files; it does not enforce their relationship.

**Why it matters:** This is a contract-drift path. The system can hide the score but still present an ambiguous or wrong reason.

**How I would fix it:**

- Make a discriminated type for suppression state:

```ts
type ScoreSuppression =
  | { scoreSuppressed: true; scoreSuppressedReason: 'unheld' | 'recognition_low_confidence' }
  | { scoreSuppressed?: false; scoreSuppressedReason?: never };
```

- In Python/docs, state the same invariant: if `scoreSuppressed is True`, `scoreSuppressedReason` is required.
- Add tests:
  - `scoreSuppressed=true` without reason fails producer validation.
  - `scoreSuppressed=false` with reason fails producer validation.
  - frontend copy has no default "기준 없음" for missing reason.

My call: once the UI copy is reason-specific, the reason is no longer optional on suppressed results.

### MEDIUM-2: The static suppression script needs cwd-stable paths and a negative self-test

**Risk:** The plan says the script reads `src/app/analysis/result.tsx`, but validation sometimes runs it from repo root as `node app/scripts/assert-result-score-suppression.mjs`. That command will not have `app/` as the working directory. Also, because this script replaces the render test, it should prove it can fail on an intentionally unguarded score-card sample; otherwise a weak implementation can simply check token presence and exit 0.

**Evidence:**

- `20-03-PLAN.md:238` specifies `fs.readFileSync('src/app/analysis/result.tsx','utf8')`.
- `20-03-PLAN.md:245` runs the script after `cd ../app`, which matches that relative path.
- `20-VALIDATION.md:27-28` and `20-VALIDATION.md:31` run `node app/scripts/assert-result-score-suppression.mjs` from repo root.
- `20-03-PLAN.md:238-241` defines heuristic static checks, but no negative fixture/self-test for the checker itself.

**Why it matters:** This can produce either false red (wrong cwd) or false green (checker implementation too weak). Since this script is now the main V-8 automation, it needs its own guardrails.

**How I would fix it:**

- Make the script cwd-independent:

```js
const resultPath = new URL('../src/app/analysis/result.tsx', import.meta.url);
```

- Or standardize every command to `cd app && node scripts/assert-result-score-suppression.mjs`.
- Add `--self-test` with in-memory fixtures:
  - a guarded sample must pass;
  - an unguarded `OctagonScore` sample must fail;
  - unguarded header copy must fail.
- Update verify to run:

```bash
cd app && node scripts/assert-result-score-suppression.mjs --self-test && node scripts/assert-result-score-suppression.mjs && npm run typecheck
```

My call: if this script is replacing RN render tests, self-test is cheap and worth it.

### LOW-1: 20-03 and 20-04 have duplicate closing `</output>` tags

**Risk:** Both plan files close `<output>` twice. Humans can ignore this, but GSD tooling or simple tag scanners may misparse the final section.

**Evidence:**

- `20-03-PLAN.md:312-315` has one `<output>` and two `</output>` tags.
- `20-04-PLAN.md:219-222` has one `<output>` and two `</output>` tags.
- `20-01-PLAN.md` and `20-02-PLAN.md` have balanced output tags.

**How I would fix it:** Remove the extra closing tag in both files. I would do this before execution because it is low-risk and prevents automation friction.

## Requested Focus Points

### Downward-only invariant

Still structurally sound. I do not see a path where vision raises a score. The remaining risks are classification/suppression semantics and validation metadata, not upward mutation.

### Curve-fit prohibition

The new data-driven status direction is correct, but it needs a real phase20 row expectation manifest for phase18 rows. Without that, status policy can move back into code and become another form of hidden fitting.

### Objectivity

The vision schema remains fine. The remaining objectivity issue is semantic labeling: safe-default branch metadata caused by `low_confidence` must not be treated as proof that no basis exists.

### Pod sequencing

The self-check/phase-gate split remains good. I would tighten the input manifest before Pod work so the terminal gate's expected status policy is reviewable before sweep output exists.

## Verdict

**Not execution-ready yet.**

I would block on HIGH-1 and HIGH-2. MEDIUM-1 and MEDIUM-2 are small but should be patched in the same pass because they protect the exact iteration-3 fixes. LOW-1 is mechanical cleanup.
