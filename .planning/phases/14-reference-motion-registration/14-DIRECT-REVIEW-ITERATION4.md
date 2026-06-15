---
phase: 14-reference-motion-registration
reviewer: Codex
date: 2026-06-15
scope: direct-plan-review-iteration4
status: go-after-test-gate-patch
reviewed_plans:
  - 14-DIRECT-REVIEW.md
  - 14-DIRECT-REVIEW-ITERATION2.md
  - 14-DIRECT-REVIEW-ITERATION3.md
  - 14-01-PLAN.md
  - 14-02-PLAN.md
  - 14-03-PLAN.md
  - 14-VALIDATION.md
local_code_checked:
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/technique.py
  - backend/shared/python/sunity_shared/analysis/force_signals.py
  - backend/shared/python/sunity_shared/analysis/force_pattern.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/scripts/extract_reference_body_profiles.py
  - backend/scripts/reprocess_reference_motions_phase4.py
  - backend/scripts/backfill_body_data_new6.py
  - .gitignore
---

# Phase 14 Direct Review Iteration 4

## Executive Verdict

3차 리뷰의 두 항목은 계획에 반영됐다. `forceDirectionPattern`은 scoped `_validate_force_pattern_inference`로 분리됐고, JS seeder도 같은 scoped shape를 허용하도록 계획이 바뀌었다. Pod `--check-firestore`도 all-11 cheap metadata gate로 확장됐다. 1차/2차의 큰 data-loss/active-pose/packaging 리스크도 현재 계획에서는 닫힌 상태다.

내 판정은 **go-after-test-gate-patch**다. 설계 블로커는 새로 발견하지 못했다. 다만 D-01 parity는 Phase 14의 핵심 보증인데, 현재 자동 검증 커맨드는 parity test가 여전히 `importorskip`으로 skip돼도 통과할 수 있다. 이건 실행 전 반드시 한 번 패치해야 한다.

## Cleared From 3차 Review

- Cleared: R3-1 validator mismatch. `14-02-PLAN.md`가 `forceDirectionPattern`에 generic flat validator를 쓰지 않고 existing `_validate_force_pattern_inference(...)`를 쓰도록 바뀌었다. Seeder도 `findings[].warnings: string[]`를 허용하는 scoped JS validator를 요구한다.
- Cleared: R3-2 one-doc Firestore gate. `14-03-PLAN.md` production run은 `--check-firestore --motions <all 11 explicitly>`를 쓰고, S3/RTMW 전에 all-11 metadata completeness를 확인한다.

## Findings

### R4-1. D-01 parity can still be skipped while the automated gate passes

Severity: **HIGH**

14-01은 `backfill_reference_downstream` module이 아직 없을 때 parity/env-flip tests를 `pytest.importorskip`으로 guard하라고 지시한다. 이 자체는 Wave 0 RED-target으로는 괜찮다. 문제는 14-02 이후다. 14-02 acceptance는 "importorskip no longer skips"라고 쓰지만, 자동 커맨드는 pytest output에서 `passed|error`만 grep한다. 그러면 helper가 아직 import되지 않아 parity가 skip되고 다른 테스트가 pass해도 command가 성공할 수 있다.

Evidence:

- `14-01-PLAN.md:167-169`: parity + env-flip tests are guarded with `pytest.importorskip` on `backfill_reference_downstream`.
- `14-01-PLAN.md:197`: automated gate explicitly accepts `passed|skipped|error`.
- `14-01-PLAN.md:203`: Wave 0 acceptance allows D-01 parity to be skipped while the helper does not exist.
- `14-02-PLAN.md:208`: Wave 2 automated gate runs pytest and greps only `passed|error`; skipped parity is not made fatal.
- `14-02-PLAN.md:213`: prose acceptance says importorskip must no longer skip, but no machine assertion enforces that.

Risk:

- The backfill script can be syntactically present while `compute_reference_downstream` is not imported by the test as intended.
- D-01 "same functions under REFERENCE_V1_FORCE_CONFIG" can remain unproven, even though the automated gate prints `HELP_OK`.
- This is exactly the guarantee that protects Phase 14 from writing plausible-looking but semantically divergent reference downstream fields.

Recommendation:

Patch 14-02 verification so skipped parity is a hard failure after the helper exists. I would do one of these:

1. Preferred: split the tests.
   - In 14-01, keep the importorskip RED-target behavior.
   - In 14-02, remove `importorskip` or add a separate `test_reference_backfill_helper_import_required_after_implementation` that fails unless `compute_reference_downstream` imports.
2. Add a CLI marker/env gate:
   - `PHASE14_REQUIRE_BACKFILL_HELPER=1 cd backend && python -m pytest tests/test_reference_backfill.py -x -q`
   - In the test file, if that env is set, do not `importorskip`; import normally and fail on missing helper.
3. At minimum, make the 14-02 automated command assert no skipped tests:

```bash
cd backend && python -m pytest tests/test_reference_backfill.py -x -q | tee /tmp/phase14-pytest.txt
! grep -qi "skipped" /tmp/phase14-pytest.txt
```

The cleanest version is option 2 because it preserves 14-01's scaffold behavior while making 14-02's implementation gate strict.

### R4-2. `motion_id` semantics are intentionally pinned to fallback, but the plan should assert that choice explicitly

Severity: **MEDIUM**

This is not a new blocker, because the research/plan repeatedly chooses FallbackRecognizer for v1. But the current helper signature accepts `motion_id`, the orchestrator passes the known reference `motion_id`, and then the helper text says `compute_force_signals(... motion_id=getattr(profile, "motion_id", None) ...)`. Since `FallbackRecognizer` returns a `TechniqueProfile` with `motion_id=None`, the known reference id is effectively ignored for force signals and force pattern inference.

Evidence:

- `14-02-PLAN.md:104`: `compute_reference_downstream(... motion_id=None, mode_context="mode1", ...)` accepts `motion_id`.
- `14-02-PLAN.md:171-172`: orchestrator calls the helper with `motion_id=motion_id`.
- `14-02-PLAN.md:174-178`: helper creates `profile = FallbackRecognizer().recognize(...)` and passes `motion_id=getattr(profile,"motion_id",None)` to `compute_force_signals`.
- `backend/shared/python/sunity_shared/analysis/technique.py:57-64`, `:106-113`: `TechniqueProfile.motion_id` defaults to `None`, and `FallbackRecognizer` does not set it.
- `backend/shared/python/sunity_shared/analysis/force_signals.py:1447-1458`: `motion_id=None` sends contact stability through the unrecognized fallback path.
- `backend/shared/python/sunity_shared/analysis/force_pattern.py:720-722`: `motion_id is not None` enables the force-pattern motion-id boost.

Risk:

- This may be the intended `REFERENCE_V1_FORCE_CONFIG` behavior, but if Phase 15 expects reference force fields to use selected `referenceMotionId` semantics, the stored reference force fields will be weaker/different than that future comparison path.
- The helper's `motion_id` parameter looks meaningful, but the described implementation can ignore it for force computation. That invites future implementer drift.

Recommendation:

Patch the plan to make the choice machine-checkable:

- If the intended v1 config is truly fallback/unrecognized, record it explicitly in `REFERENCE_V1_FORCE_CONFIG`, for example `forceMotionIdSource: "fallback_profile_motion_id"` and `forceMotionId: null`, and add a parity assertion that helper output uses `motion_id=None`.
- If reference-known semantics are desired, change the helper to pass the helper argument: `motion_id=motion_id` to both `compute_force_signals` and `infer_force_direction_pattern`, then update the 14-01 parity direct-call reference to do the same.

I would keep the current fallback/null behavior for Phase 14 because A1 already resolved FallbackRecognizer for v1. But I would still add an assertion so Phase 15 cannot accidentally assume the reference force fields were generated with known-reference contact/boost semantics.

## My Execution Advice

I would not send this into 14-02 execution until R4-1 is patched. It is small, but it protects the most important claim in the phase. R4-2 can be handled as a plan clarification/test assertion; it does not need to block the data run if the team accepts fallback/null as the v1 reference config.

After R4-1 is patched, the plan is execution-ready by my standard: validator scope is correct, active pose is protected by pre/post JSON hash gates, rollback is restore-aware, Pod credential/completeness failure happens before expensive work, and seeding is all-or-nothing on all 11.

