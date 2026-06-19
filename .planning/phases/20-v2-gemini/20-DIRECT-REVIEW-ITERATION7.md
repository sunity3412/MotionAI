# Phase 20 Direct Review - Iteration 7

**Reviewed:** 2026-06-19  
**Reviewer:** Codex direct review (not external reviewer)  
**Scope:** latest Phase 20 planning commit (`e2b45c5`), updated `20-03-PLAN.md`, `20-04-PLAN.md`, `20-VALIDATION.md`, prior direct reviews  
**Review stance:** seventh-pass execution-readiness review. Focus = whether iteration-6 asset locking actually covers the calibration input and whether terminal evidence now requires it consistently.

## Summary

Iteration 6 fixed the mechanical issues from the previous pass:

- `autonomous` front matter is restored (`20-03=true`, `20-04=false`).
- stray `</content></invoke>` tags are gone from active plan/validation files.
- sweep commands now use `PYTHONPATH=shared/python`.
- `eval_manifest_assets.lock.json` was added to close the asset-selection tuning surface.

The remaining blockers are narrower but still important:

- the new asset lock appears to hash `eval_manifest`, while `derive_caps.py` still derives from `sensitivity.yaml`;
- older text still says `derive_caps.py` creates the pre-sweep policy hash, contradicting the new durable-lock model;
- the final Pod evidence/output sections still mostly mention only policy drift, not asset drift.

## Findings

### HIGH-1: Asset lock does not yet cover the actual derive input (`sensitivity.yaml`)

**Risk:** Iteration 6 correctly says sensitivity asset choice is calibration input. But the lock is described as `eval_manifest_assets.lock.json` over `eval_manifest` full manifest / `source.key`. Meanwhile `derive_caps.py` still reads `sensitivity.yaml` rows and `video_key` as its cap-derivation input. If `sensitivity.yaml.video_key` changes or diverges from `eval_manifest.yaml.source.key`, the cap can be derived from a different asset set than the one locked in `eval_manifest_assets.lock.json`.

**Evidence:**

- `20-04-PLAN.md:27` says the asset lock hashes the full manifest or sensitivity row keys+policy, framed around `eval_manifest`.
- `20-04-PLAN.md:40-41` defines `sensitivity.yaml` as the generalization asset manifest with `video_key`.
- `20-04-PLAN.md:129` says `derive_caps.py` validates the sensitivity manifest and rejects missing/TODO `video_key`, which confirms `sensitivity.yaml` is the derive input.
- `20-04-PLAN.md:131` adds `eval_manifest_assets.lock.json` with `full_manifest_sha256` and `sensitivity_keys[]`, but does not require hashing `sensitivity.yaml`.
- `20-04-PLAN.md:141` says sensitivity rows are source-mapped, but there is no explicit invariant that `sensitivity.yaml.video_key == eval_manifest.yaml[source.dataset=sensitivity].source.key`.
- `20-04-PLAN.md:195` again describes filling both `sensitivity.yaml` video keys and `eval_manifest.yaml` source keys before running `derive_caps.py`.

**Why it matters:** D-02 is about locking calibration input. The actual calibration input is not just `eval_manifest`; it is also the `sensitivity.yaml` content consumed by `derive_caps.py`.

**How I would fix it:**

- Make `eval_manifest_assets.lock.json` cover both files:

```json
{
  "eval_manifest_sha256_pre_derivation": "...",
  "sensitivity_manifest_sha256_pre_derivation": "...",
  "policy_sha256": "...",
  "sensitivity_keys": ["..."]
}
```

- Add a required cross-file invariant:
  - every sensitivity row in `eval_manifest.yaml` maps to exactly one row in `sensitivity.yaml`;
  - `eval_manifest.source.key == sensitivity.yaml.video_key`;
  - row bucket/direction is consistent.
- Make `derive_caps.py` fail if either file differs from the asset lock or if the two files disagree.
- Add tests:
  - `test_derive_caps_rejects_sensitivity_yaml_drift_after_asset_lock`;
  - `test_eval_manifest_sensitivity_keys_match_sensitivity_yaml`.

My call: lock the data file that actually feeds derivation, not only the gate manifest.

### HIGH-2: Policy-lock ownership is contradictory: derive both creates and only verifies it

**Risk:** The new lock model says `eval_manifest_policy.lock.json` must be created before the first scored sweep, and `derive_caps.py` should only read/verify it. But older text still says `derive_caps.py` computes and records `eval_manifest_policy_sha256_pre_sweep` before cap derivation. That leaves implementers with two incompatible paths, one of which recreates the original problem: a "pre-sweep" hash generated after sweep output exists.

**Evidence:**

- `20-04-PLAN.md:130` still says `derive()` computes `eval_manifest_policy_sha256_pre_sweep` and records it to provenance/report output.
- `20-04-PLAN.md:131` then says the policy hash must come from `eval_manifest_policy.lock.json` created before scored sweep, and derive only reads the lock.
- `20-04-PLAN.md:144` still describes report fields as including `eval_manifest_policy_sha256_pre_sweep` from derive-time freeze.
- `20-04-PLAN.md:166` acceptance still greps for `compute_locked_policy_sha256` inside `derive()` as if derive creates the freeze.
- `20-04-PLAN.md:191` correctly says the lock file is created before sweep, so the implementation target is inconsistent within the same plan.

**Why it matters:** A lock is only useful if its creation point is unambiguous. If derive can create the lock, a post-sweep policy can become the "frozen" policy.

**How I would fix it:**

- Remove the derive-generated freeze path entirely.
- Add one explicit freeze helper or mode, for example:

```bash
cd backend && PYTHONPATH=shared/python python evals/phase20/assert_baseline_v2.py --freeze-policy
cd backend && PYTHONPATH=shared/python python evals/phase20/assert_baseline_v2.py --freeze-assets
```

- Or create `freeze_eval_manifest.py` with two commands: `policy` and `assets`.
- Make `derive_caps.py` only verify lock files and fail if they are missing or mismatched.
- Update acceptance to grep that `derive_caps.py` reads `eval_manifest_policy.lock.json`, not that it writes `eval_manifest_policy_sha256_pre_sweep`.

My call: freeze creation should live in a separate, auditable step. Derivation should be a consumer of locks, never the creator.

### MEDIUM-1: Asset-drift is not propagated to terminal evidence and summary requirements

**Risk:** The implementation section adds asset-drift checks, but terminal gate bullets, threat register, verification, success criteria, and output still mostly mention policy drift only. A person writing `20-04-SUMMARY.md` could follow the output block and omit `eval_manifest_assets_sha256_pre_derivation` while still appearing compliant.

**Evidence:**

- `20-04-PLAN.md:146` requires `eval_manifest_assets_sha256_pre_derivation` in `eval20_gate_report.json`.
- `20-04-PLAN.md:184-187` Task 2 summary still describes only policy freeze/drift.
- `20-04-PLAN.md:204-206` phase-gate checklist mentions policy drift and report keys, but omits asset drift and `eval_manifest_assets_sha256_pre_derivation`.
- `20-04-PLAN.md:218-228` threat model still describes only policy freeze as the manifest curve-fit mitigation; there is no asset-drift threat row.
- `20-04-PLAN.md:239-260` verification, success criteria, and output omit the asset lock/hash.
- `20-VALIDATION.md:71` V-14 report keys omit `eval_manifest_assets_sha256_pre_derivation`.
- `20-VALIDATION.md:125` manual sensitivity instructions still say fill source keys after policy freeze and then sweep; they do not require the asset lock before scoring.

**How I would fix it:**

- Add `asset-drift 없음` to the Task 2 phase-gate checklist.
- Add `eval_manifest_assets_sha256_pre_derivation` to:
  - `eval20_gate_report.json` expected keys;
  - V-14 report evidence;
  - verification/success/output blocks;
  - `20-04-SUMMARY.md` required content.
- Add a threat row such as `T-20-15f`: sensitivity asset set changed after lock.
- Update manual V-5 instructions to require `eval_manifest_assets.lock.json` before any scored sensitivity sweep.

My call: if asset lock is a HIGH fix, it must appear in the terminal evidence contract, not only in the implementation paragraph.

### MEDIUM-2: Test counts and gate counts are stale after adding asset-lock tests

**Risk:** The plan now adds `test_phase_gate_fails_on_asset_drift` and `test_derive_caps_requires_asset_lock`, but the acceptance text still says `test_assert_baseline_v2.py 6 케이스` and the phase gate is still described as `8 게이트`. These are small inconsistencies, but they are exactly the kind of checklist drift that causes reviewers to miss whether new guards were actually implemented.

**Evidence:**

- `20-04-PLAN.md:147-154` lists the original tests plus two asset-lock tests.
- `20-04-PLAN.md:162` still says `test_assert_baseline_v2.py 6 케이스 GREEN`.
- `20-04-PLAN.md:176` still says `8 게이트 코드 존재`, despite adding asset-drift.
- `20-04-PLAN.md:180` done text still says `8 게이트` and mentions iter5 policy-drift, but not iter6 asset-drift.

**How I would fix it:** Either avoid numeric counts or update them to the exact current count after deciding whether asset-drift is a separate gate. I would avoid counts and list required guard names instead.

## Requested Focus Points

### Downward-only invariant

Still structurally sound. The plan continues to rely on min-cap mutation, cap-mutation tests, and no raise/no score increase paths. No new upward-score path found.

### Curve-fit prohibition

Closer, but not closed. Policy locks and asset locks are the right shape, but the asset lock must include `sensitivity.yaml`, because that is the file `derive_caps.py` actually consumes.

### Objectivity

Objectivity remains acceptable. I do not see score fields or human labels leaking into the vision schema. The remaining objectivity risk is calibration-input drift, not prompt/schema leakage.

### Pod sequencing

The front matter and command shape issues from iteration 6 are fixed. The remaining sequencing issue is ownership of lock creation: freeze steps must happen before scoring and outside `derive_caps.py`.

## Verdict

**Not execution-ready yet.**

I would block on HIGH-1 and HIGH-2. MEDIUM-1 and MEDIUM-2 are documentation/evidence consistency fixes, but they should be patched before Pod execution so the terminal summary cannot omit asset-drift proof.
