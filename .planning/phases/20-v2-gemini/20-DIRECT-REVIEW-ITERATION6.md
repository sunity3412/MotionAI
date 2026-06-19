# Phase 20 Direct Review - Iteration 6

**Reviewed:** 2026-06-19  
**Reviewer:** Codex direct review (not external reviewer)  
**Scope:** latest Phase 20 planning commit (`cce4d88`), updated `20-03-PLAN.md`, `20-04-PLAN.md`, `20-VALIDATION.md`, prior direct reviews  
**Review stance:** sixth-pass execution-readiness review. Focus = whether iteration-5 fixes fully close the curve-fit and pod-sequencing surfaces without introducing plan/tooling drift.

## Summary

Iteration 5 substantially tightened the plan:

- `eval_manifest.yaml` now has LOCKED policy fields and policy-drift checks.
- `recognition_low_confidence` copy now owns `scoringBasisLabel`, so the old "기준 동작 없음" label is not supposed to leak.
- backend validation commands are mostly standardized.
- A2 reconcile now has one structured `scoreSuppressionAudit` sink instead of "dict or log."

I still would not execute yet. The remaining issues are not about the core veto math; they are about whether the phase can be run and audited without moving targets or tooling ambiguity.

## Findings

### HIGH-1: Manifest freeze still leaves sensitivity asset selection as a tuning surface

**Risk:** The new policy freeze protects `expected_bucket`, `allowed_veto_statuses`, and score/verdict thresholds. But `source.key` for sensitivity rows is explicitly FILLABLE and excluded from the locked-policy hash. Since sensitivity assets are the data used by `derive_caps.py`, changing which videos populate `source.key` after seeing candidate sweep behavior can still tune the cap without tripping `policy-drift`.

There is also a sequencing ambiguity: the plan says the pre-sweep policy hash can be recorded by `derive_caps`, but `derive_caps` is run in step 4 after the first serial sweep in step 3. If the only durable `eval_manifest_policy_sha256_pre_sweep` is created there, it is not a trustworthy pre-sweep anchor.

**Evidence:**

- `20-04-PLAN.md:23` says LOCKED policy is frozen before the first scored sweep, while FILLABLE asset fields may be filled after freeze.
- `20-04-PLAN.md:126` says `derive_caps.py` computes `eval_manifest_policy_sha256_pre_sweep` before cap derivation, not necessarily before the first scored sweep.
- `20-04-PLAN.md:131-136` marks sensitivity `source.key` as FILLABLE while score/verdict policy is LOCKED.
- `20-04-PLAN.md:139-141` has `--phase-gate` compare the pre-sweep policy hash to the current locked-policy hash; it does not compare a pre-derivation asset/full-manifest hash.
- `20-04-PLAN.md:183-186` says freeze happens before sweep, but then runs serial sweep at step 3 and `derive_caps.py` at step 4.
- `20-VALIDATION.md:68` checks policy drift, but does not require a pre-derivation hash for the filled sensitivity asset set.

**Why it matters:** D-02 is not only "do not edit thresholds." It is also "do not choose the examples after seeing which ones make the cap pass." If the cap derives from sensitivity videos, the selected video keys need an audit lock before they are scored for derivation.

**How I would fix it:**

- Split the freeze into two explicit artifacts:
  - `eval_manifest_policy.lock.json`: created and committed before any scored sweep. Hash covers policy fields only.
  - `eval_manifest_assets.lock.json`: created and committed after sensitivity `source.key` is filled but before any scored sensitivity sweep or cap derivation. Hash covers the full manifest, or at minimum sensitivity row keys plus policy.
- Make `derive_caps.py` refuse to run unless the asset lock exists and matches the current full manifest.
- Make `--phase-gate` report and verify both:
  - `eval_manifest_policy_sha256_pre_sweep`
  - `eval_manifest_assets_sha256_pre_derivation` or `eval_manifest_sha256_pre_derivation`
- Keep `source.key` fillable only until the asset lock is created. After that, changing it is drift.

My call: policy freeze is not enough. The sensitivity asset set is part of calibration input and must be locked before scoring/derivation.

### HIGH-2: Plan front matter lost `autonomous`, which can break pod-free vs blocking sequencing

**Risk:** The latest commit removed `autonomous` from `20-03-PLAN.md` and `20-04-PLAN.md`. Earlier plan files in this phase still carry it, and the previous diff shows `20-04` used to be `autonomous: false`. For a phase with pod-free work followed by a blocking-human Pod gate, losing this metadata can cause execution tooling to choose a default. Depending on that default, 20-04 could be treated as runnable when it should stop, or not scheduled when Task 1 should run.

**Evidence:**

- `20-01-PLAN.md:10` has `autonomous: true`.
- `20-02-PLAN.md:10` has `autonomous: true`.
- `20-03-PLAN.md:1-15` has no `autonomous` field.
- `20-04-PLAN.md:1-17` has no `autonomous` field.
- `git show cce4d88` removed `autonomous: true` from 20-03 and `autonomous: false` from 20-04.
- `20-04-PLAN.md:175-201` still depends on a blocking-human Pod checkpoint, so metadata ambiguity matters.

**Why it matters:** This phase's safety depends on pod-free automation stopping before terminal Pod evidence. A missing front-matter field is exactly the kind of small metadata drift that can cause a silent skip or an accidental run.

**How I would fix it:**

- Restore the explicit metadata:
  - `20-03-PLAN.md`: `autonomous: true`
  - `20-04-PLAN.md`: `autonomous: false`
- Add a validation note or simple grep check that every `*-PLAN.md` in this phase has an `autonomous:` field.
- Keep the task-level `checkpoint:human-verify` gate as the second line of defense, not the only sequencing signal.

My call: do not rely on executor defaults for a Pod terminal gate. Make the top-level metadata explicit again.

### MEDIUM-1: Stray `</content></invoke>` tags can confuse plan parsers

**Risk:** The previous duplicate `</output>` issue was fixed, but the latest commit added closing `</content>` and `</invoke>` tags at the end of several files. Those tags do not have matching opening tags in the files. Humans can ignore them; simple XML-ish or GSD section parsers may not.

**Evidence:**

- `20-03-PLAN.md:348-349` ends with `</content>` and `</invoke>`.
- `20-04-PLAN.md:253-254` ends with `</content>` and `</invoke>`.
- `20-VALIDATION.md:144-145` ends with `</content>` and `</invoke>`.
- `20-01-PLAN.md` and `20-02-PLAN.md` do not have those tags.

**How I would fix it:** Remove those six trailing lines. Then run a cheap structural grep for unmatched `</content>` / `</invoke>` across the phase directory.

My call: this is mechanical, but it should be fixed before handing the plans to automation.

### MEDIUM-2: Sweep commands still violate the backend command shape

**Risk:** Iteration 5 standardized backend commands around `cd backend && PYTHONPATH=shared/python ...`, but the actual Pod sweep command still omits `PYTHONPATH`. The validation doc repeats the same command. This reintroduces the command drift that iteration 5 tried to remove.

**Evidence:**

- `20-04-PLAN.md:77` says all backend commands use `cd backend && PYTHONPATH=shared/python ...`.
- `20-04-PLAN.md:182` repeats that rule for Pod work.
- `20-04-PLAN.md:185` uses `cd backend && python scripts/sweep_phase15.py ...` without `PYTHONPATH=shared/python`.
- `20-VALIDATION.md:123` has the same sweep command without `PYTHONPATH=shared/python`.

**How I would fix it:**

```bash
cd backend && PYTHONPATH=shared/python python scripts/sweep_phase15.py --keys-file scripts/phase15_keys.json --mode mode1 --pair-sequential
```

Apply the same shape anywhere the sweep command appears, including README output generated by 20-04.

My call: if the rule is "all backend commands," sweep needs to follow it too.

## Requested Focus Points

### Downward-only invariant

Still structurally sound. I do not see a score-increase path in the veto logic. The remaining blockers are plan execution integrity and calibration auditability.

### Curve-fit prohibition

Improved, but still not closed. Policy fields are locked, but the sensitivity asset set is calibration input too. Lock the filled source keys before they are scored for derivation.

### Objectivity

Vision schema/objectivity remains acceptable. The `recognition_low_confidence` label leak is now covered by reason-owned copy and a targeted test. I would keep that fix.

### Pod sequencing

The human checkpoint text is strong, but front-matter metadata and stray tags now weaken tooling reliability. Restore `autonomous` and remove unmatched tags before running any executor.

## Verdict

**Not execution-ready yet.**

I would block on HIGH-1 and HIGH-2. MEDIUM-1 and MEDIUM-2 are small, mechanical fixes and should be patched in the same pass.
