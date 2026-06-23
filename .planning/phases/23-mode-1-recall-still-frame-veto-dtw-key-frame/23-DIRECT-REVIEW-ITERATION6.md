# Phase 23 Direct Review - Iteration 6

Date: 2026-06-23
Reviewer: Codex direct review, no external skill/MCP
Scope: Sixth-pass review after D-13 fixes and D-14 Phase 20-04 absorption.

Reviewed artifacts:
- `23-CONTEXT.md`
- `23-01-PLAN.md`
- `23-02-PLAN.md`
- `23-03-PLAN.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md`
- `.planning/phases/20-v2-gemini/20-04-EVAL-EVIDENCE.md`

## Executive Summary

D-13 is substantially incorporated. The explicit quantification seam, `collection_status`, support-gated root causes, and `applied => samplingComplete=true` policy are now present in the plans.

The new risk is D-14: Phase 23-03 now claims ownership of the Phase 20-04 SEVERITY_CAP sweep gate. That is directionally reasonable because the veto input changed from whole-video to still-frame, but the absorption currently loses or blurs several guarantees that made 20-04 a terminal gate:

1. SCORE-09/generalization sensitivity coverage is not fully carried into 23-03.
2. The gate is described as machine-checkable, but no non-zero assertion script is planned.
3. `kip-up <= 50` conflicts with the existing 20-04 evidence where kip-up fault was accepted at 75/moderate.
4. Global tracking documents now disagree about whether 20-04/SCORE-09 is pending, superseded, or owned by Phase 23-03.

## Findings

### HIGH-1: D-14 absorbs 20-04 but drops the SCORE-09 generalization gate

**Risk**

`23-03-PLAN.md` now says it supersedes Phase 20-04 by checking:

- elite clean score remains 95-100
- kip-up fault score <= 50
- final score determinism
- EVAL18 four-pair discrimination regression count = 0

Those are important, but they are not the full Phase 20-04/SCORE-09 contract.

The global roadmap still defines Phase 20's generalization hard gate as:

- no overfit to the owned Jung Eunji set
- sensitivity cases containing unsupported motions and above-cutoff cases
- bidirectional false-positive/false-negative validation

`REQUIREMENTS.md` also still has `SCORE-09` pending under Phase 20. The original `20-04-PLAN.md` went much further than the current D-14 absorption: it had sensitivity manifests, diversity floors, policy/assets locks, drift detection, and git chronology to prove that the eval policy/assets were frozen before the scored sweep. `23-03-PLAN.md` does not yet import those controls.

So Phase 23-03 can appear to supersede 20-04 while only preserving the known-answer regression subset. That risks silently losing SCORE-09.

**How I would fix it**

Pick one of two explicit policies:

1. Narrow D-14:
   - Say 23-03 supersedes only the still-frame SEVERITY_CAP regression sweep.
   - Leave `SCORE-09` pending as a separate generalization/sensitivity gate.
   - Update ROADMAP/REQUIREMENTS/STATE so nobody thinks SCORE-09 is closed.

2. Fully absorb SCORE-09 into 23-03:
   - Add a frozen eval manifest for Phase 23 with:
     - known-fault rows
     - elite/imperfect clean rows
     - unsupported-motion sensitivity rows
     - above-cutoff sensitivity rows
     - per-row expected bucket/status/max/min policy
   - Add a diversity floor equivalent to 20-04:
     - must-drop rows across at least two motion ids
     - must-stay-high rows across at least two motion ids
     - preferably distinct capture sessions/camera setups
   - Add policy and asset lock files, or a lighter equivalent:
     - policy frozen before scored sweep
     - asset set frozen before Pod run
     - gate fails if manifest/policy/assets drift after lock

My preference: use option 2 only if Phase 23 truly owns SCORE-09. Otherwise, keep D-14 scoped to still-frame regression and do not mark 20-04/SCORE-09 as superseded beyond that subset.

### HIGH-2: The Phase 23-03 gate is not enforced by a non-zero assertion command

**Risk**

`23-03-PLAN.md` says the result JSON has machine-checkable fields, but Task 1 verification is only AST parse plus a grep for concurrency primitives. Task 2 is a blocking human checkpoint where a person reads the JSON fields and decides.

That is weaker than the terminal-gate semantics Phase 20-04 had. A JSON file can be committed with:

- missing fields
- string `"true"` instead of boolean `true`
- stale pass fields
- inconsistent aggregate counts
- row-level failures hidden under summary fields
- D-14 fields present but not actually enforced

The plan would still satisfy "file exists" style acceptance unless the reviewer manually catches it.

**How I would fix it**

Add a dedicated gate script:

```text
backend/research/spikes/assert_stillframe_veto_gate.py
```

Required command:

```bash
cd backend
python research/spikes/assert_stillframe_veto_gate.py \
  --results research/spikes/reports/eval_stillframe_veto_phase23.json \
  --manifest research/spikes/eval_stillframe_veto_manifest.yaml
```

It should exit non-zero on any failure and emit a compact gate report.

Minimum checks:

- required top-level and row-level fields exist with exact bool/int/list types
- every manifest row appears exactly once in results
- no extra unmanifested row is silently counted in pass metrics
- `coverage_pass`, `completion_pass`, `determinism_*`, arm cache isolation, and D-14 gates are recomputed from rows, not trusted from precomputed JSON fields
- `kipup_fault_score_le_50`, `elite_clean_score_in_95_100`, and `eval18_discrimination_regression_count` are derived from actual final scores
- `resource_limited` and `samplingComplete=false` fail non-budget-stress rows
- missing `visionVeto`, `skipped_error`, `missing_local_video`, and unallowed statuses fail

Then Task 2 should require the Pod run to execute this assert script before the JSON is accepted.

### HIGH-3: `kip-up <= 50` conflicts with the existing 20-04 evidence that accepted kip-up at 75/moderate

**Risk**

D-14 now requires:

```text
kipup_fault_score_le_50=true
```

But the existing Phase 20-04 evidence records:

```text
kip-up correct: 100 / not_applicable
kip-up fault: 75 / moderate
```

The same evidence explicitly frames 75 as acceptable and aligned with the domain read that kip-up was a light fault, not necessarily <=50.

That creates a contract conflict:

- If kip-up must be <=50, then the 20-04 evidence was not a passing terminal gate for this criterion.
- If kip-up=75 is acceptable, then D-14 must not claim `kipup_fault_score_le_50`.
- If the implementation is pressured to force kip-up from moderate to major only to satisfy `<=50`, that becomes exactly the kind of known-answer curve-fit the plans are trying to prevent.

**How I would fix it**

Make the row policy explicit in a manifest.

Example:

```yaml
rows:
  - row_id: eval18-kip-up-fault
    expected_bucket: must_drop
    allowed_veto_statuses: [applied]
    expected_severity: major
    max_score: 50
```

or, if belle intentionally accepts the previous moderate result:

```yaml
rows:
  - row_id: eval18-kip-up-fault
    expected_bucket: must_drop
    allowed_veto_statuses: [applied]
    expected_severity: moderate
    max_score: 75
```

Do not keep both claims. My stricter recommendation is:

- If the product spec remains "wrong motion <=50", require kip-up to be `major` and final score <=50 in Phase 23 still-frame production.
- Treat the 20-04 `75/moderate` evidence as historical evidence, not proof that D-14 passes.
- Add a row-level failure message that says whether the miss was severity misclassification or cap application.

### MEDIUM-1: Supersede ownership is inconsistent across ROADMAP, REQUIREMENTS, STATE, and 23-03 front matter

**Risk**

`.planning/ROADMAP.md` now says `20-04-PLAN.md` is superseded by 23-03. But:

- `REQUIREMENTS.md` still has `SCORE-09` pending under Phase 20.
- `STATE.md` still says current focus is Phase 20 and describes 20-04 as spec-anchored with sensitivity eval deferred.
- `23-03-PLAN.md` front matter lists only `requirements: [VETO-06]`, even though it now claims to own gates tied to `SCORE-08`, `SCORE-09`, and `TRUST-06`.

This is not just documentation drift. It affects close-out: an executor could close Phase 23 without updating SCORE-09, or close Phase 20-04 as superseded while SCORE-09 is still objectively pending.

**How I would fix it**

Update ownership in one atomic doc change:

- If 23-03 fully owns the gate:
  - `23-03-PLAN.md` requirements should include `VETO-06`, `SCORE-08`, `SCORE-09`, and `TRUST-06`.
  - `REQUIREMENTS.md` should mark `SCORE-09` as pending via Phase 23-03, not Phase 20-only.
  - `STATE.md` should say Phase 20-04 is superseded by 23-03 and list what remains pending, if anything.

- If 23-03 only owns regression:
  - Keep `SCORE-09` pending under Phase 20/follow-up.
  - Change ROADMAP wording from "20-04 superseded" to "20-04 regression subset superseded; sensitivity/generalization remains pending."

### MEDIUM-2: Phase 23 manifest labels are not frozen before Pod measurement

**Risk**

23-03 relies on labels such as:

- `abstention_allowed`
- `budget_stress`
- `alignment_unverifiable`
- case class
- expected recall set
- expected D-14 row policy

Those labels are part of the gate, not passive metadata. If they can be edited after seeing Pod results, the eval can be made to pass by relabeling hard cases as budget-stress, alignment-unverifiable, or out-of-scope.

The original 20-04 plan had a much stronger approach: policy/assets frozen before measurement and verified later. 23-03 should have at least a lighter version.

**How I would fix it**

Add:

```text
backend/research/spikes/eval_stillframe_veto_manifest.yaml
backend/research/spikes/eval_stillframe_veto_manifest.lock.json
```

The lock should record:

- manifest sha256
- created timestamp
- git commit
- dirty-worktree flag, rejected for phase gate
- row ids and expected policy fields

The assertion script should fail if:

- manifest hash differs from lock
- lock was made with a dirty worktree
- result rows do not match manifest rows exactly
- any expected-policy field is missing or changed

This is lighter than recreating all of 20-04, but enough to prevent post-result relabeling.

## Consolidated Recommendation

Before executing Phase 23-03 on Pod, I would make these plan edits:

1. Decide whether 23-03 fully owns SCORE-09 or only the 20-04 regression subset.
2. Resolve the kip-up contract: `<=50/major` vs `<=75/moderate`. Do not keep both.
3. Add a frozen manifest plus non-zero assertion script for `eval_stillframe_veto_phase23.json`.
4. Update ROADMAP/REQUIREMENTS/STATE/front matter so supersede ownership is unambiguous.

After D-13, the implementation contracts are much stronger. D-14 is the remaining place where the plan can still pass on paper while losing the original terminal-gate rigor.
