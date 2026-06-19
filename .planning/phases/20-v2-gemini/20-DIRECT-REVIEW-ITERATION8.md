# Direct Review - Iteration 8

Reviewer: Codex  
Scope:
- `.planning/phases/20-v2-gemini/20-01~04-PLAN.md`
- `.planning/phases/20-v2-gemini/20-CONTEXT.md`
- `.planning/phases/20-v2-gemini/20-RESEARCH.md`
- `.planning/phases/20-v2-gemini/20-VALIDATION.md`

Focus:
- Downward-only invariant
- No curve-fit path through `SEVERITY_CAP`
- Vision objectivity and label leakage
- Pod sequencing / terminal eval gate
- Iteration 7 remediation diff

## Findings

### HIGH-1 - Freeze locks still lack auditable temporal provenance, so a post-result re-freeze can pass the gate

Location:
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:142`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:143`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:208`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:209`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:221`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:223`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:281`

Iteration 7 correctly moved lock creation into `freeze_eval_manifest.py` and made `derive_caps.py` / `assert_baseline_v2.py` read-verify only. That closes the previous implementation ownership hole.

The remaining gap is chronology. The plan says the policy lock and asset lock must be created and committed before the scored sweep / derivation, but the proposed lock schemas only prove that the current files match the current locks. They do not prove when those locks were created relative to the scored sweep, baseline assertion, or failed attempts.

Current effect:
- An operator can change `eval_manifest.yaml` or `sensitivity.yaml` after observing results.
- They can rerun `freeze_eval_manifest.py policy/assets`.
- The new lock hashes will match the new files.
- `--phase-gate` will pass because it verifies equality, not pre-result chronology.

That is still a curve-fit path. It is narrower than before, but for this phase's stated purpose the audit trail must prove "frozen before measurement", not only "frozen at some point".

What I would do:
- Add immutable provenance fields to both lock files:
  - `lock_git_commit`
  - `lock_created_at_utc`
  - `lock_command`
  - `git_dirty: false`
  - optionally `lock_actor` if available from git config
- Make `freeze_eval_manifest.py policy/assets` refuse to create locks when the worktree is dirty, unless a documented `--allow-dirty-for-dev-only` flag is used and rejected by phase-gate.
- Make `assert_baseline_v2.py --phase-gate` report:
  - `policy_lock_git_commit`
  - `assets_lock_git_commit`
  - `baseline_git_commit`
  - `lock_commits_precede_baseline_commit`
- Require `20-04-SUMMARY.md` to list the policy-lock commit, asset-lock commit, sweep commit/log artifact, and baseline commit in chronological order.

This is the last structural gap I would still block on before treating 20-04 as execution-ready. Hash equality is necessary, but it is not enough for anti-curve-fit evidence.

### MEDIUM-1 - The top-level phase-gate truth still omits asset hashes, despite later sections requiring them

Location:
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:30`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:31`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:59`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:60`
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:190`

The detailed artifact and acceptance sections now require asset-hash evidence:
- `eval_manifest_assets_sha256_pre_derivation`
- `sensitivity_manifest_sha256_pre_derivation`

But the top `must_haves` truth still says the baseline report proves only the locked policy hash and full manifest hash, and the per-row phase-gate status list only names:
- `eval_manifest_policy_sha256`
- `eval_manifest_policy_sha256_pre_sweep`
- `eval_manifest_policy_match`

That top block is likely what an implementer will scan first. Because it is framed as "single source of truth", the omission can cause the asset-drift guard added in iteration 7 to be implemented only in lower-level report details, not in the headline terminal gate contract.

What I would do:
- Rewrite the top truth to explicitly include both asset hashes and sensitivity hashes in the baseline report / phase-gate evidence list.
- Keep the same exact field names as the artifact section.
- Add `eval_manifest_assets_match` and `sensitivity_manifest_match` or equivalent booleans to the top-level terminal gate truth.

### LOW-1 - Unbalanced markdown emphasis in the `must_haves` block makes the gate contract easy to misread

Location:
- `.planning/phases/20-v2-gemini/20-04-PLAN.md:31`

The `**--phase-gate...` text opens bold emphasis but does not close it. This is not a runtime defect, but the line is part of the most important safety contract in the phase. Rendering ambiguity here is cheap to avoid.

What I would do:
- Close the emphasis marker while fixing MEDIUM-1.
- Prefer splitting that long YAML string into shorter bullets if the planning format allows it.

## Checks That Now Look Solid

The iteration 7 changes materially improved the plan:
- `sensitivity.yaml` is now included in the locked asset set, so vision/source mapping cannot drift silently.
- `derive_caps.py` is now read-verify only and no longer owns lock creation.
- `freeze_eval_manifest.py` owns both policy and asset lock creation.
- `--phase-gate` now has explicit policy-drift and asset-drift failure conditions.
- Stale guard-count wording was removed from the active plan.

I do not see a remaining score-up path through the vision schema itself. The objectivity boundary still looks intact: vision evidence stays descriptive, while scores remain in the trusted non-vision manifest path.

I also do not see a remaining silent-skip path in the pod sequencing after the latest gate changes. The remaining problem is auditability of when the locks were produced, not whether the gate checks the currently declared artifacts.

## Verdict

Not execution-ready yet because HIGH-1 leaves a real anti-curve-fit audit gap.

After adding lock chronology/provenance and cleaning the top-level gate truth, I would expect this phase to be ready for implementation. The core architecture is now close: downward-only evaluation, non-vision scoring authority, and terminal gate sequencing are all substantially better than in earlier iterations.
