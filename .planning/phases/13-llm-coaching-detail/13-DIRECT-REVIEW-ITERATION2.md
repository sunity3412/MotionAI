---
phase: 13-llm-coaching-detail
reviewer: Codex
date: 2026-06-16
scope: direct-plan-review-iteration2
status: revise-before-execution
reviewed_plans:
  - 13-A-corrective-exercises-PLAN.md
  - 13-B-llm-branch-copy-PLAN.md
  - 13-RESEARCH.md
  - 13-DIRECT-REVIEW.md
local_code_checked:
  - app/tsconfig.json
  - app/src/components/CoachingTipDetailModal.tsx
  - backend/judging_data/criteria/ref-climb.yaml
  - backend/judging_data/criteria/ref-foxtop.yaml
  - backend/judging_data/criteria/ref-foxtop-split.yaml
  - backend/judging_data/criteria/ref-invert.yaml
  - backend/judging_data/criteria/ref-sideway-spin.yaml
  - backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py
---

# Phase 13 Direct Review — Iteration 2

## Verdict

The first review findings were mostly incorporated:

- Plan A now has an app-side full-library data path for "다른 운동 보기".
- Plan B now makes `motion_ipsf_map.json` an explicit curated join table.
- Plan B adds `build_result` pass-through tests.
- Plan B separates universal 180° extension copy from non-180 move-specific angles.
- The bad `cd backend && cd backend` verify command was fixed.

I would still revise before execution. The remaining issue is more subtle: current production `ref-*` motions do not fit a single `isRegistered` boolean. For example, `ref-invert` is IPSF-registered, but the current angle data is explicitly 정은지 measured-angle data, not IPSF joint-angle data. `ref-climb` is IPSF category-based but has no geometric angle criterion. If `isRegistered` alone drives both baseline copy and angle fixture selection, tests can pass while the prompt still cites the wrong source.

## Findings

### BLOCKER-1: `isRegistered` is overloaded; registration branch and angle source need separate fields

Plan B now requires every `REGISTERED_MOTIONS` id to have a `motion_ipsf_map` entry, but it still allows `isRegistered:null` fallback for production ids and uses `is_registered` as the main branch switch.

Evidence:
- `13-B-llm-branch-copy-PLAN.md:116-119` allows each current production id to be `branch1/branch2/unknown`, with `isRegistered:null` fallback.
- `13-B-llm-branch-copy-PLAN.md:127-130` has `lookup_motion_ipsf(...) -> tuple[str | None, bool | None]`, so downstream code only sees `ipsf_code` and `is_registered`.
- Current recognized production ids are exactly five `ref-*` values in `gemini_motion_classifier.py:20-29`.
- `ref-invert.yaml:7-17` says the move is IPSF Body Position Inverted, but the angle dimension is 정은지 measured data because body-position scoring is deferred.
- `ref-climb.yaml:8-27` says the move belongs to IPSF Transitions & Climbs, but has no anatomical angle target.
- `ref-foxtop-split.yaml:7-14` and `ref-sideway-spin.yaml:7-14` are explicitly IPSF-unregistered and use 정은지 reference measured values.

Risk:
- A production motion can be IPSF-registered but still need measured-angle source for the current Phase 13 prompt.
- A production motion can be IPSF-related but have no valid joint-angle fixture.
- `isRegistered:null` can pass the coverage test while skipping criteria 6 copy for a current user-facing motion.

My fix:
- Change `motion_ipsf_map.json` schema from one boolean to an explicit routing object:

```json
{
  "ref-invert": {
    "copyBranch": "branch1_ipsf_registered",
    "ipsfCode": "BODY_POSITION_INVERTED",
    "officialName": "Body Position Inverted",
    "angleSource": "eunji_measured_yaml",
    "angleFixtureKey": "ref-invert",
    "criteriaYaml": "ref-invert.yaml",
    "sourceNote": "IPSF registered, but joint-angle criteria deferred to Body Position phase"
  }
}
```

- Suggested fields:
  - `copyBranch`: `branch1_ipsf_registered | branch2_eunji_reference | unknown`
  - `ipsfCode`: string or null
  - `angleSource`: `ipsf_registered_fixture | eunji_measured_yaml | no_angle_criterion | unavailable`
  - `angleFixtureKey`: string or null
  - `criteriaYaml`: string or null
  - `sourceNote`: required non-empty string
- For current `REGISTERED_MOTIONS`, do not allow `copyBranch:"unknown"` unless there is a blocking human checkpoint before Task 2. Unknown is acceptable for future/new motion ids, not for the five current ids.
- Replace `lookup_motion_ipsf(...) -> tuple` with `lookup_motion_branch(...) -> MotionBranchInfo` dict/object so app.py and coach_writer can use copy branch, angle source, display name, and fixture key consistently.
- Add tests:
  - every current `REGISTERED_MOTIONS` entry has non-unknown `copyBranch`
  - every `copyBranch=branch1_ipsf_registered` entry declares an `angleSource`
  - `angleSource=eunji_measured_yaml` loads `criteria/{motion_id}.yaml`
  - `angleSource=no_angle_criterion` does not inject fake angles and uses a non-angle prompt line

### HIGH-1: `registered_move_angles.json` has no key contract linking it to `motion_ipsf_map`

Plan B says `registered_move_angles.json` contains Ayesha and other verified IPSF angle fixtures, while `motion_ipsf_map.json` is keyed by production `motion_id`. The join key between the two is not specified.

Evidence:
- `13-B-llm-branch-copy-PLAN.md:40-42` expects `registered_move_angles.json` to contain "Ayesha".
- `13-B-llm-branch-copy-PLAN.md:116-120` keys `motion_ipsf_map.json` by `ref-*` production ids.
- `13-B-llm-branch-copy-PLAN.md:157-165` says app.py injects `angle_fixture`, but does not define whether lookup uses `motion_id`, `ipsfCode`, officialName, or a display alias.

Risk:
- `motion_ipsf_map` can classify a motion as branch 1, but angle fixture lookup can miss and silently omit criteria 7 data.
- Tests can pass with direct `_build_prompt(... angle_fixture={...})` while production never finds that fixture.

My fix:
- Make `registered_move_angles.json` keyed by the same `angleFixtureKey` used in `motion_ipsf_map`.
- Prefer production-stable keys:

```json
{
  "schemaVersion": "1.0.0",
  "angles": {
    "ipsf-ayesha": { "...": "..." },
    "ref-invert": { "angleSource": "eunji_measured_yaml", "criteriaYaml": "ref-invert.yaml" }
  }
}
```

- Add `angleFixtureKey` to every `motion_ipsf_map` entry and test:
  - if `angleSource=ipsf_registered_fixture`, `registered_move_angles.angles[angleFixtureKey]` exists
  - if `angleSource=eunji_measured_yaml`, `backend/judging_data/criteria/{angleFixtureKey}.yaml` exists
  - if `angleSource=no_angle_criterion`, the prompt states that this move has no joint-angle fixture rather than inventing one

### HIGH-2: Plan A's app mirror lockstep test claims content lockstep but only checks names

Plan A added `app/src/data/correctiveExercises.ts`, which closes the first review's modal data-source gap. But the planned lockstep test is too weak.

Evidence:
- `13-A-corrective-exercises-PLAN.md:176-181` says the app mirror contains backend fixture schema/version/content.
- The proposed test checks schemaVersion, defect/painArea key sets, and exercise name set only.
- Exercise behavior depends on `setsReps`, `purpose`, `sourceRef`, `avoid`, and trigger fields, not just names.

Risk:
- App and backend can drift in actual prescription text while tests stay green.
- Source citations can disappear from the app-side library without detection.

My fix:
- Best: do not manually mirror a TS object. Add `app/src/data/corrective_exercises.json` as a byte-for-byte copy generated from `backend/data/corrective_exercises.json`, and make `correctiveExercises.ts` a typed wrapper around it. Add a small sync script or test that compares canonical JSON hashes.
- If keeping a manual TS object, make the test compare full normalized content:
  - `schemaVersion`
  - all defect keys
  - all painArea keys
  - every exercise `{name, setsReps, purpose, sourceRef}`
  - every painArea `avoid`
  - every trigger `sourceSignals` and `jointHints`
- The current "name set only" test should be treated as a smoke check, not a drift gate.

### MEDIUM-1: Result section visibility conflicts with "modal always works"

Plan A says the recommended exercise section hides when `recommendedExercises` is missing or empty, but the same action says the full-library modal should always work.

Evidence:
- `13-A-corrective-exercises-PLAN.md:178-179` says the modal browses full library, but the `recommendedExercises` card section is hidden when empty.
- The "다른 운동 보기" button is planned inside that section.

Risk:
- Analyses with no findings or no mapped exercises have no visible entry point to the library, despite criteria 4 saying the user can browse it.

My fix:
- Render the "보완 운동" section when either:
  - `recommendedExercises.length > 0`, or
  - `CORRECTIVE_EXERCISES` has any library items.
- If no personalized recommendations exist, show a short neutral state and keep the browse button:
  - "이번 분석에서는 뚜렷한 보완 운동 매핑이 없어요."
  - "전체 보완 운동 보기"
- Add a frontend unit or snapshot-style test if the project has one; if not, add a manual UAT line specifically for empty recommendations.

### MEDIUM-2: 13-RESEARCH still contains superseded guidance

The updated plans correctly override first-review issues, but `13-RESEARCH.md` still says the fixture is derived and that branch 1 copy is "세계 심사 기준 + 180°".

Evidence:
- `13-RESEARCH.md:230-238` still recommends a derived `motion_ipsf_map.json`.
- `13-RESEARCH.md:296-308` still shows branch true -> "세계 심사 기준 (IPSF) + 180°".
- The execution context for both plans still includes `13-RESEARCH.md`.

Risk:
- An implementer following `read_first` can get conflicting instructions from research and plan action text.
- This is exactly the kind of drift that causes execution agents to reintroduce old review failures.

My fix:
- Patch `13-RESEARCH.md` with a short "Direct review supersession" note:
  - `motion_ipsf_map` is curated, not derived.
  - `isRegistered` is not enough; use `copyBranch + angleSource`.
  - `180°` is extension-only, not universal angle baseline.
- Or add a `13-REVIEW-FIXES.md` referenced by both plans' `<read_first>` before `13-RESEARCH.md`.

## Closed Findings From Iteration 1

- 1차 BLOCKER-1 partially closed: `motion_ipsf_map` is no longer blindly derived, but needs richer branch/source schema.
- 1차 HIGH-1 closed directionally: app-side library data path added.
- 1차 HIGH-2 closed directionally: `build_result` pass-through is now explicitly planned and tested.
- 1차 HIGH-3 closed directionally: non-180 angle preservation is now planned.
- 1차 WARNING-1 closed directionally: branch-2 yaml double-prefix is explicitly tested.
- 1차 WARNING-2 closed: verify command no longer repeats `cd backend`.

## Final Recommendation

Do one more patch before execution:

1. Replace `isRegistered`-only routing with `copyBranch + angleSource + angleFixtureKey`.
2. Make current five `REGISTERED_MOTIONS` fail-closed: no unknown copy branch without a human checkpoint.
3. Strengthen the app mirror lockstep test to compare full exercise content, or use JSON copy/generation.
4. Keep the full-library browse button visible even when personalized recommendations are empty.
5. Update or supersede stale `13-RESEARCH.md` guidance.

After that, I would mark Phase 13 execution-ready.
