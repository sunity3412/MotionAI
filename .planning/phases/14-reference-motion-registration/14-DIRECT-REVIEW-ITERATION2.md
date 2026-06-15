---
phase: 14-reference-motion-registration
reviewer: Codex
date: 2026-06-15
scope: direct-plan-review-iteration2
status: revise-before-execution
reviewed_plans:
  - 14-DIRECT-REVIEW.md
  - 14-01-PLAN.md
  - 14-02-PLAN.md
  - 14-03-PLAN.md
  - 14-VALIDATION.md
local_code_checked:
  - app/package.json
  - app/src/lib/referenceMotions.ts
  - app/src/types/analysis.ts
  - backend/shared/python/sunity_shared/auth.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/scripts/reprocess_reference_motions_phase4.py
  - .gitignore
---

# Phase 14 Direct Review Iteration 2

## Executive Verdict

1차 리뷰의 핵심 R1-R8은 상당히 잘 반영됐다. 특히 `meanAngles`/EXTEND를 stored active `phase4_v1.angles`에서 산출하도록 바꾼 것, "student path exact" 표현을 `REFERENCE_V1_FORCE_CONFIG` pinned parity로 정정한 것, seeder skip rule을 complete/repair/overwrite로 분리한 것, pre/post active-pose hash gate를 추가한 것은 방향이 맞다.

다만 아직 **as-is 실행은 보류**가 맞다. 2차에서 새로 보이는 가장 큰 문제는 rollback/snapshot 설계다. 현재 14-03은 rollback을 "Phase-14-added fields delete"로 설명하지만, Phase 14는 기존 필드가 이미 있는 문서를 repair/overwrite할 수 있다. pre-seed snapshot도 active pose만 hash하고 downstream field 원본을 보존하지 않는다. 이 상태에서 `--force`를 쓰거나 pre-existing `meanAngles`를 건드리면 안전하게 되돌릴 수 없다.

판정: **revise-before-execution, but close**. 아래 BLOCKER 2개와 HIGH 2개를 plan patch 후에는 실행 가능 상태로 볼 수 있다.

## Cleared From 1차 Review

- Cleared: R1 stored-sufficient conflict. `14-02-PLAN.md:49-70`, `:127-160`이 stored active angles를 source로 고정했다.
- Cleared: R2 "student path exact" mislabel. `14-01-PLAN.md:49-55`, `14-02-PLAN.md:67-70`, `14-VALIDATION.md:50`이 reference-v1 pinned config로 정정했다.
- Cleared: R3 skip rule. `14-02-PLAN.md:214-230`, `:235-244`가 complete/repair/overwrite를 분리했다.
- Cleared: R4 prose-only unchanged assertion. `14-03-PLAN.md:45-61`, `:94-103`, `:128-131`이 pre/post hash gate를 추가했다.
- Cleared: R5 partial fixture seed. `14-02-PLAN.md:100-101`, `:169-173`, `:218-220`이 11-id all-or-nothing을 넣었다.
- Cleared: R6 helper call boundary. `14-01-PLAN.md:122-124`, `14-02-PLAN.md:95-99`이 `pole_axis_measurement` + `angles` injection을 요구한다.

## Findings

### R2-1. Rollback is not snapshot-aware and can delete or fail to restore pre-existing fields

Severity: **BLOCKER**

The rollback plan says it deletes only Phase-14-added fields, but it does not preserve which fields were actually added by Phase 14 versus already present before the run. It also omits `bodyNormalizationProfile`, even though Phase 14 may repair that field for missing references.

Evidence:

- `14-02-PLAN.md:18`: default repair-missing, `--force` overwrites existing valid fields.
- `14-02-PLAN.md:214-230`: seeder may repair missing fields and `--force` may overwrite existing valid fields.
- `14-03-PLAN.md:96-103`: pre snapshot records activeVersion/angles/joints3d only.
- `14-03-PLAN.md:104-107`: rollback deletes `meanAngles*/techniqueProfile*/forceDirectionPattern*/captureViews*`, never active pose.
- `14-03-PLAN.md:21-25`: success includes `bodyNormalizationProfile`, and rollback is claimed to remove only Phase-14-added fields.
- `app/src/lib/referenceMotions.ts:81-95`: `meanAngles` can already exist and is preferred over derived fallback.

Risk:

- If `meanAngles` already existed before Phase 14, rollback can delete a pre-existing field.
- If Phase 14 repairs missing `bodyNormalizationProfile`, rollback will leave that repaired field behind because it is not in the delete list.
- If `--force` overwrites a valid existing `bodyNormalizationProfile`, `meanAngles`, or future `techniqueProfile`, the current pre snapshot cannot restore the previous value.
- "ADD-only rollback" is only safe for fields proven absent before the run. The current snapshot does not prove that.

Recommendation:

Patch 14-03 before execution:

1. Extend `snapshot_reference_active_pose.mjs` into `snapshot_reference_phase14_state.mjs` or broaden the existing script to snapshot both:
   - active pose hashes: `activeVersion`, `angles`, `joints3d`
   - Phase 14 field state: `meanAngles`, `techniqueProfile`, `bodyNormalizationProfile`, `forceDirectionPattern`, `captureViews`, all `*UpdatedAt`, and optional `forceDirectionPatternSource` / `forceSignalsWarnings`
2. Store for each field: `{present: boolean, valueHash: string, value?: object}`. The local preseed JSON may contain values, but it must remain gitignored and secret-free.
3. Rollback must be restore-aware:
   - if field was absent before seed, delete it
   - if field existed before seed, restore the exact previous value
4. If the team wants delete-only rollback, ban `--force` for the real Phase 14 run and allow deletion only for fields absent in the pre snapshot.
5. Add `bodyNormalizationProfile*` and `bodyComparisonSourcePose*` policy explicitly: either Phase 14 is allowed to repair body profile and rollback restores/deletes it, or Phase 14 never writes it if already present and records it as pre-existing.

I would choose restore-aware rollback. It keeps `--force` usable without turning a rollback into data loss.

### R2-2. New Node scripts are planned under `backend/scripts`, but `firebase-admin` is only installed under `app/`

Severity: **BLOCKER**

The plan creates and runs Node admin scripts from `backend/scripts`. This repo has no root `package.json` and no `backend/package.json`; `firebase-admin` is in `app/package.json` only. A Node script located under `backend/scripts` cannot reliably import `firebase-admin/app` by normal Node package resolution.

Evidence:

- `14-03-PLAN.md:7-10`: new scripts are `backend/scripts/snapshot_reference_active_pose.mjs` and `backend/scripts/rollback_reference_downstream.mjs`.
- `14-03-PLAN.md:94-107`: those scripts lazy-import Firebase Admin.
- `14-03-PLAN.md:115`, `:129`, `:144`: commands run `node backend/scripts/...`.
- `app/package.json:42-45`: `firebase-admin` is an app devDependency.
- There is no root `package.json` and no `backend/package.json` in the current repo.

Risk:

- `node --check backend/scripts/snapshot_reference_active_pose.mjs` can pass syntax while runtime `import('firebase-admin/app')` fails.
- The real production gate can fail after implementation for a packaging/path reason, not a Firestore reason.
- This diverges from existing Node admin scripts, which live under `app/scripts`.

Recommendation:

Move both scripts to `app/scripts/`:

- `app/scripts/snapshot-reference-active-pose.mjs`
- `app/scripts/rollback-reference-downstream.mjs`

Then run them as:

```bash
cd app && node scripts/snapshot-reference-active-pose.mjs --mode pre
cd app && node scripts/rollback-reference-downstream.mjs --dry-run
```

Update `14-03-PLAN.md files_modified`, verify commands, runbook commands, and `.gitignore` path if needed. If scripts must stay under `backend/scripts`, add a root/backend Node package and dependency, but that is unnecessary surface area for this repo.

### R2-3. Pod Firestore read is now critical, but the plan only checks imports, not credentials/read access

Severity: **HIGH**

After the 1차 fix, the Pod backfill must read stored active angles from Firestore before computing `meanAngles`/EXTEND and before the angle integrity gate. The plan adds `firebase-admin` to the Pod import check, but import success is not credential success.

Evidence:

- `14-02-PLAN.md:39-42`: backfill reads `reference/{id}.phase4_v1.angles`.
- `14-02-PLAN.md:123-130`: lazy-import `firebase-admin`, then read stored angles.
- `14-03-PLAN.md:12-18`: user setup only covers local Node ADC for the seeder.
- `14-03-PLAN.md:117-118`: Pod step checks import of `firebase-admin`, not a Firestore read.
- `backend/shared/python/sunity_shared/auth.py:40-60`: Python Firestore auth needs `FIREBASE_SA_JSON`, `FIREBASE_SA_PATH`, or `FIREBASE_SA_PARAM`.
- `.planning/STATE.md` says the Pod has `FIREBASE_SA_PATH`, but the plan should gate it explicitly.

Risk:

- Pod starts the expensive S3/RTMW flow and fails at the stored-angle read.
- A future runner might have rtmlib/boto3 but no Firebase SA mounted.
- Failure mode is operational, not caught by 14-02 `--help` or import checks.

Recommendation:

Add a Pod Firestore credential/read gate before any S3 download:

```text
python backend/scripts/backfill_reference_downstream.py --check-firestore --motions ref-climb
```

The check should read one reference doc, verify `activeVersion`, `angles`, `anglesJointKeys`, and `anglesFrames`, and exit before video work. Use `sunity_shared.firestore_admin` / `auth._ensure_firebase()` rather than duplicating a direct `credentials.Certificate(...)` path, because `auth.py` already supports `FIREBASE_SA_JSON`, `FIREBASE_SA_PATH`, and `FIREBASE_SA_PARAM`.

Also add Pod-side setup to 14-03:

```yaml
user_setup:
  - service: runpod-firestore-sa
    env_vars: [FIREBASE_SA_PATH or FIREBASE_SA_JSON]
```

### R2-4. `ReferenceMotion` type will gain fields, but `referenceMotions.ts normalize()` will strip them

Severity: **HIGH**

14-01 updates `app/src/types/analysis.ts` and `docs/contract.md`, but it does not include `app/src/lib/referenceMotions.ts`. The current `normalize()` function returns a constructed object and only includes a fixed subset of fields. New fields in Firestore will not appear in the normalized `ReferenceMotion` object.

Evidence:

- `14-01-PLAN.md:186-224`: contract + TS interface update only.
- `14-01-PLAN.md:7-12`: `files_modified` excludes `app/src/lib/referenceMotions.ts`.
- `app/src/lib/referenceMotions.ts:132-154`: return object includes `meanAngles` and `referenceKeypointReport`, but not `bodyNormalizationProfile`, `techniqueProfile`, `forceDirectionPattern`, or `captureViews`.
- `app/src/types/analysis.ts:398-447`: `ReferenceMotion` already declares `bodyNormalizationProfile`, but `normalize()` currently drops it.

Risk:

- Firestore can be correct while the app hook silently hides the new fields.
- Phase 15 or UI code may trust `useReferenceMotion()` and see missing values even after Phase 14 succeeds.
- Type/interface lockstep gives a false sense of availability because runtime normalization does not match it.

Recommendation:

Add `app/src/lib/referenceMotions.ts` to 14-01 Task 3 `files_modified` and action. Normalize and return at least:

- `bodyNormalizationProfile`
- `techniqueProfile`
- `forceDirectionPattern`
- `captureViews`

Keep them optional/null-safe. Add a small typecheck or unit-level assertion if there is a local test pattern; otherwise `cd app && npm run typecheck` plus grep is acceptable for this narrow change.

### R2-5. Diagnostic `forceSignalsReport` in the fixture can collide with seeder validation

Severity: **MEDIUM-HIGH**

14-02 wants to retain a per-motion `forceSignalsReport` summary in the fixture and run log. The seeder also validates per-motion payloads and rejects nested arrays. If diagnostics live beside seed fields in each motion payload, the seeder can either reject useful diagnostics or accidentally seed fields that were intended artifact-only.

Evidence:

- `14-02-PLAN.md:161-164`: retain per-motion `forceSignalsReport` summary in fixture + run-log artifact.
- `14-02-PLAN.md:214-230`: seeder loads per-motion payload, validates required fields, rejects nested arrays, then builds Firestore payload.
- `backend/shared/python/sunity_shared/firestore_admin.py:746-756`: force reports/patterns need scoped validators because generic flat dict validation is not enough.

Risk:

- A diagnostic summary with nested metric arrays can make an otherwise valid seed fixture fail.
- A future implementation can accidentally seed artifact-only raw force report data.
- Firestore flat-array rules get enforced at the wrong layer.

Recommendation:

Make the fixture schema explicit:

```json
{
  "generatedAt": "...",
  "seedPayload": {
    "ref-climb": {
      "meanAngles": {},
      "techniqueProfile": {},
      "bodyNormalizationProfile": {},
      "forceDirectionPattern": {},
      "captureViews": 1
    }
  },
  "diagnostics": {
    "ref-climb": {
      "storedAnglesHash": "...",
      "rerunAnglesHash": "...",
      "maxAngleDelta": 0.0,
      "forceSignalsReportSummary": {}
    }
  }
}
```

Seeder should read only `seedPayload`. Diagnostics should be logged and copied to `14-BACKFILL-RUN.md`, not validated as seed fields.

### R2-6. Automated 14-03 verify still greps strings instead of asserting JSON values

Severity: **MEDIUM**

The plan now requires JSON summary values, but the automated verify command still only checks that certain strings appear in `14-BACKFILL-RUN.md`.

Evidence:

- `14-03-PLAN.md:143-145`: verify command greps `unchangedActivePoseCount`, `completeDownstreamFieldCount`, and `health`.
- `14-03-PLAN.md:146-156`: acceptance requires exact values: unchanged=11, changed=0, complete=11, seeded=11.

Risk:

- A failed log containing `changedActivePoseCount: 1` and `unchangedActivePoseCount: 10` could still satisfy grep.
- This recreates a weaker version of the issue fixed in 1차 review.

Recommendation:

Emit a machine-readable summary file, for example:

```text
.planning/phases/14-reference-motion-registration/14-BACKFILL-RUN-SUMMARY.json
```

Then verify with Node:

```bash
node -e 'const s=require("./.planning/phases/14-reference-motion-registration/14-BACKFILL-RUN-SUMMARY.json"); if (s.unchangedActivePoseCount!==11 || s.changedActivePoseCount!==0 || s.completeDownstreamFieldCount!==11 || s.seededMotionCount!==11) process.exit(1)'
```

Keep the markdown run log for humans, but gate on JSON.

### R2-7. Minor metadata drift: 14-03 frontmatter dropped `requirements: [REF-01]`

Severity: **LOW**

`14-01` and `14-02` include `requirements: [REF-01]`; `14-03` no longer does.

Evidence:

- `14-03-PLAN.md:1-18` frontmatter has no `requirements`.

Recommendation:

Add it back. This is not a behavioral blocker, but it keeps planning metadata consistent.

## What I Would Patch Next

1. Move snapshot/rollback Node scripts to `app/scripts`, or add a root/backend Node package. Prefer `app/scripts`.
2. Broaden preseed snapshot to include Phase 14 downstream fields, not just active pose hashes.
3. Make rollback restore-aware:
   - restore old value if present before seed
   - delete only if absent before seed
4. Add `app/src/lib/referenceMotions.ts` to 14-01 and normalize the new fields.
5. Split fixture into `seedPayload` and `diagnostics`.
6. Add a Pod Firestore read probe before S3/RTMW work.
7. Replace markdown grep with JSON summary assertions.

## Final Recommendation

The revised plan is much closer than the first version. I would not restart the planning loop; I would apply a small patch to 14-01/14-02/14-03 and then execute.

The only true execution blockers are rollback safety and Node script location. The rollback problem matters most: production writes are acceptable only if the rollback can restore pre-existing downstream fields exactly, not just delete a guessed list of fields.
