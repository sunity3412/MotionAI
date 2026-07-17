# Phase 29 Direct Plan Review

**Reviewer:** Codex direct review (no external reviewer)
**Date:** 2026-07-09
**Scope:** `29-CONTEXT.md`, `29-RESEARCH.md`, `29-VALIDATION.md`, `29-01-PLAN.md` through `29-08-PLAN.md`, plus the referenced source seams.

## Verdict

I would not execute Phase 29 as-is. The plan is directionally strong and much better than a naive "just wire the UI" phase, but I found two HIGH risks that can leave required user-facing behavior broken while the planned gates still pass.

My action would be: patch `29-03`, `29-04`, `29-06`, and `29-VALIDATION` before execution. `29-01`, `29-02`, `29-05`, `29-07`, and `29-08` are mostly coherent after those amendments, though I would also tighten the final gate wording noted under Medium.

## Findings

### HIGH-1: Mode3 `ipsf_absolute` records have no keypoint/region projection, so markers and zoom drilldown can silently fail

**Evidence**

- `29-03-PLAN.md:95-100` says mode3 zoom should derive joints from `deductionBreakdown.records`, but current `DeductionRecord` objects only carry `criterion`, values, units, source, and `deviationSource`; they do not carry a keypoint field (`backend/shared/python/sunity_shared/analysis/deduction_engine.py:54-65`, `:71-91`).
- The actual mode3 measured seeds are criterion ids such as `leg_extension`, `arm_extension`, and `line` (`backend/functions/pipeline/app.py:2244-2246`, `:2284-2301`; `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py:65-123`).
- The app projection helpers only understand `angle_vs_reference__{joint}` and `source === 'vision'`; `leg_extension`, `arm_extension`, and `line` return no keypoints (`app/src/app/analysis/result.tsx:284-305`; `app/src/lib/deductionLabels.ts:185-216`).
- `29-04-PLAN.md:15` promises mode3 markers, and `29-03-PLAN.md:18` promises record-joint/zoom-joint matching. Those promises are not locked by the current plan because the missing projection is in app helper logic, not in the backend render call alone.

**Risk**

Power-spin is the only currently meaningful mode3 `ipsf_absolute` content path. Its likely record is `leg_extension`. With the plan as written, the breakdown section may render a row, but the row can have no matching marker number, no action phrase, and no selected zoom image in the drilldown because the app cannot project `leg_extension` to the legs region. Backend tests in `29-03` can still pass if `_render_fault_zoom` is called with a chosen region, because the app-side `selectedZoom` matching still returns `null`.

**What I would do**

Block execution until the plan explicitly adds a criterion projection layer:

1. Add a shared helper in `app/src/lib/deductionLabels.ts`, for example `projectDeductionRecordKeypoints(record, faultJoints)`, and make both `buildDeductionMarkers` and `result.tsx` `recordProjectedKeypoints` use it.
2. Map `leg_extension -> REGION_MEMBER_KEYPOINTS.legs` or at least `[left_knee, right_knee]`, `arm_extension -> REGION_MEMBER_KEYPOINTS.arms` or elbow/hand proxy consistently with `KEYPOINT_FROM_ANGLE_KEY`, and decide whether `line` gets a region or intentionally has no zoom.
3. Amend `29-03` so backend mode3 zoom emits `region: 'legs'` for `leg_extension` records instead of assuming a keypoint field exists on records.
4. Amend `29-04` acceptance criteria to require a fixture-level check: a mode3 `deductionBreakdown.records=[{criterion:'leg_extension', ...}]` produces a numbered breakdown row, a marker/group marker, and `selectedZoom` matches a `faultZoomComparisons` item with `region:'legs'`.

Without this patch, D-08 is at high risk of becoming "backend generated an asset, app cannot attach it to the row."

### HIGH-2: `/playback-url` reference re-signing blocks raw S3 keys but does not require active/public reference docs

**Evidence**

- `29-06-PLAN.md:113-119` adds a `referenceMotionId` path that signs `videoS3Key` after a Firestore lookup. It requires auth and blocks client-provided S3 keys, which is necessary but not sufficient.
- The current admin helper returns any `reference/{id}` doc without filtering `isActive` (`backend/shared/python/sunity_shared/firestore_admin.py:1522-1529`).
- The app hides inactive reference docs client-side (`app/src/lib/referenceMotions.ts:70-78`), so `isActive === false` is meaningful product/security state, not cosmetic state.
- Auto-registration explicitly creates or preserves inactive reference docs for rejected/G3 routes (`backend/shared/python/sunity_shared/firestore_admin.py:1406-1425`, `:1458-1472`).
- `29-06-PLAN.md:114` also says `reference_motions/{id}`, while the canonical collection used by code is `reference` (`app/src/lib/referenceMotions.ts:7`, `:212-214`; `backend/shared/python/sunity_shared/models.py:443`).

**Risk**

An authenticated user could request a re-signed URL for an inactive or not-yet-approved reference doc if they can guess or learn the `referenceMotionId`. That bypasses the app's active-reference filter and can expose videos that were intentionally hidden pending review. This is especially risky because `/playback-url` holds S3 signing authority.

The collection-name drift is a separate execution risk: using literal `reference_motions` instead of `models.REFERENCE_MOTIONS_COLLECTION` would make the fix fail in production even if mock tests pass.

**What I would do**

Block `29-06` until it is patched:

1. Change the plan language from `reference_motions/{id}` to canonical `reference/{id}` and require use of `models.REFERENCE_MOTIONS_COLLECTION` / `models.reference_motion_path`.
2. Add a backend helper or inline guard: `ref is not None`, `ref.get("isActive") is not False`, `videoS3Key` exists, and `videoS3Key` starts with `reference/`. For the current catalog, I would additionally require either `videoS3Key == f"reference/{referenceMotionId}.mp4"` or an explicit allowlisted prefix if shared-base naming requires it.
3. Return 404 for inactive/missing/no-video refs so callers cannot distinguish hidden docs from absent docs.
4. Add tests to `backend/tests/test_playback_url_reference.py`: inactive ref returns 404, non-`reference/` key is rejected, wrong collection literal is not used, raw `s3Key` body is ignored, existing `analysisId` path remains byte-compatible.

If all active reference videos are intended public-to-authenticated-users, this is still the minimum boundary I would enforce before giving a new API path S3 signing power.

## Medium Findings

### MEDIUM-1: D-02 score switch gate allows large clean-score elevation without an explicit product checkpoint

`29-02-PLAN.md:79-82` and `29-05-PLAN.md:82-88` allow a clean tally to become `final == 100`, and `29-05-PLAN.md:83` explicitly allows success scores to rise above the old baseline. That may be consistent with the transparent tally philosophy, but the criteria coverage is very narrow in this phase: research says 4 of 5 registered mode3 motions effectively fallback, while power-spin has the meaningful criteria.

I would add a `29-05` output table with old `overallScore`, new `tally.final`, records count, criteria ids, and coverage/fallback state for every key. If any clean doc jumps materially to 100 because only one narrow criterion passed, I would stop for a product decision rather than silently shipping it. This is not a blocker if belle has explicitly accepted "criterion-clean = 100," but the acceptance should be visible in the sweep summary.

### MEDIUM-2: Final UAT verification grep is too weak

`29-08-PLAN.md:130-136` requires 10 HUMAN-UAT items, but the automated verify is only `grep -c "D-1"`, which can pass while missing several required items. I would replace it with explicit grep checks for `D-14`, `D-01`, `D-06`, `D-08`, `D-09`, `D-11`, `D-12`, `F1`, and `iPad`, or a small script that validates the table rows.

## No High Concern

- `29-01` correctly avoids creating a nonexistent `SafetyFlag.recommendation` backend field and keeps the implementation OTA-safe.
- `29-02` correctly preserves `visionVeto.status === "mode3_held"` instead of overloading `applied`.
- `29-05` correctly prevents Pod production restart before the sweep gate passes.
- `29-07` correctly identifies the old-build OTA crash hazard from static `expo-screen-orientation` imports and uses `requireOptionalNativeModule` plus lazy `require`.

## Final Recommendation

Patch HIGH-1 and HIGH-2 before `/gsd-execute-phase 29`. After those amendments, I would execute in the planned wave order, but I would keep the D-02 score-switch table as a visible checkpoint in `29-05-SUMMARY.md` before restarting the Pod and before publishing OTA in `29-08`.
