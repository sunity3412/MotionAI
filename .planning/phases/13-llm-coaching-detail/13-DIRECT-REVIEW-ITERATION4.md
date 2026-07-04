---
phase: 13-llm-coaching-detail
review: direct-codex-iteration-4
reviewed_at: 2026-06-16
status: conditional-pass-minor-cleanup
plans_reviewed:
  - 13-A-corrective-exercises-PLAN.md
  - 13-B-llm-branch-copy-PLAN.md
  - 13-REVIEW-FIXES.md
  - 13-PATTERNS.md
  - 13-PLAN-CHECK.md
---

# Phase 13 Direct Review — Iteration 4

## Verdict

Conditional pass with minor cleanup. The 3rd-review risks are materially addressed:

- Plan A now includes `app/tsconfig.json` and explicitly requires `resolveJsonModule` for the app JSON import.
- Plan B now treats `angleFixtureKey` as nullable for `no_angle_criterion`, preserving `ref-climb` as a no-fake-angle case.
- `13-REVIEW-FIXES.md` now fixes `MotionBranchInfo` as a frozen dataclass, not a dict.
- `13-PATTERNS.md` and `13-PLAN-CHECK.md` now supersede the stale `is_registered` route.

I would not send this back for another architecture cycle. Before execution, I would make two small wording patches so the executor cannot drift from the now-correct contract.

## Findings

### MEDIUM-1: Plan B still has two local `MotionBranchInfo` examples that permit dicts

The supersession ledger correctly locks `MotionBranchInfo` to a frozen dataclass, but Plan B still has stale dict wording in Task 2.

Evidence:

- `13-REVIEW-FIXES.md:35` says `MotionBranchInfo = @dataclass(frozen=True)`, "dict 아님", and consumers use attribute access.
- `13-B-llm-branch-copy-PLAN.md:137` still says `MotionBranchInfo = lookup_motion_branch 가 반환하는 dict/dataclass(...)`.
- `13-B-llm-branch-copy-PLAN.md:149` still uses a dict-like test example: `assemble.build_result(..., branch_info={copyBranch:"branch2_eunji_reference",...})`.
- The same plan uses attribute access everywhere else: `branch_info.copyBranch` at `13-B-llm-branch-copy-PLAN.md:137`, and `_build_coach_context` examples use `branch_info.officialName` / `branch_info.copyBranch` at `13-B-llm-branch-copy-PLAN.md:183`.

Risk:

- A test could pass a dict while production passes a dataclass, or implementation code could use attribute access against a dict. This should fail fast in unit tests, but the contract no longer needs to leave this ambiguity.

How I would fix it:

- Patch `13-B-llm-branch-copy-PLAN.md:137` to: `MotionBranchInfo = @dataclass(frozen=True)` with the exact field list from `13-REVIEW-FIXES.md:35`.
- Patch `13-B-llm-branch-copy-PLAN.md:149` to instantiate the dataclass in tests, e.g. `MotionBranchInfo(copyBranch="branch2_eunji_reference", ...)`.
- Add a tiny assertion in `test_motion_ipsf_map_coverage.py` or `test_build_result_branch_passthrough.py` that `lookup_motion_branch("ref-foxtop")` returns `MotionBranchInfo`, not `dict`.

### LOW-1: Verification summary still says `angleFixtureKey cover` for all production motions

The task action and acceptance criteria are now correct, but the verification summary remains slightly ambiguous.

Evidence:

- Correct contract: `13-B-llm-branch-copy-PLAN.md:146-147` allows `angleFixtureKey` null for `no_angle_criterion`.
- Correct acceptance: `13-B-llm-branch-copy-PLAN.md:156` says `angleFixtureKey` is required only for `ipsf_registered_fixture/eunji_measured_yaml` and null for `no_angle_criterion(ref-climb)`.
- Ambiguous summary: `13-B-llm-branch-copy-PLAN.md:253` says `REGISTERED_MOTIONS 전수 non-unknown copyBranch + angleSource + angleFixtureKey cover`.

Risk:

- Low. The acceptance criteria are clearer and should govern. Still, the summary can mislead a checklist-driven executor into forcing a fake fixture key for `ref-climb`.

How I would fix it:

- Change line 253 to: `REGISTERED_MOTIONS 전수 non-unknown copyBranch + angleSource cover; angleFixtureKey non-null only for ipsf_registered_fixture/eunji_measured_yaml, null for no_angle_criterion(ref-climb).`

## Closed Since Iteration 3

| Prior issue | Iteration 4 status |
|-------------|--------------------|
| `angleFixtureKey` required vs nullable contradiction | Closed in action and acceptance; one LOW wording cleanup remains in verification summary. |
| app JSON import missing `resolveJsonModule` contract | Closed. Plan A includes `app/tsconfig.json` and acceptance line for `resolveJsonModule`. |
| stale `is_registered` route in PATTERNS / PLAN-CHECK | Closed. Both now point to `branch_info.copyBranch` / `lookup_motion_branch` and supersede boolean routing. |
| dict vs dataclass for `MotionBranchInfo` | Mostly closed in `13-REVIEW-FIXES.md`; Plan B still needs two local wording patches. |

## Narrow Gate Status

| Gate | Iteration 4 status | Notes |
|------|--------------------|-------|
| criteria 7 IPSF angles | PASS | Current five motions avoid fake IPSF fixtures; future IPSF fixture path stays human-gated. Keep `ref-climb` null. |
| 3-way contract / Firestore nested-array | PASS | Plain camelCase scalar dict + scoped validator + app JSON import contract are now covered. |
| D-05 painAreas boundary | PASS | painAreas remains mapping/coaching-only with a no-scoring-leak gate. |
| criteria 5 Pod dependency | PASS | Pod/Cerebras E2E remains a blocking human checkpoint and is not auto-claimed. |

## Recommendation

No more architecture replanning needed. I would apply the two Plan B wording cleanups above, then execute Phase 13 with the existing human checkpoints.
