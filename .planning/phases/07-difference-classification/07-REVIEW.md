---
phase: 07-difference-classification
reviewed: 2026-06-08T00:00:00Z
type: plan-risk-review
depth: standard
scope: phase_7_plans_no_implementation
files_reviewed: 9
files_reviewed_list:
  - .planning/phases/07-difference-classification/07-CONTEXT.md
  - .planning/phases/07-difference-classification/07-RESEARCH.md
  - .planning/phases/07-difference-classification/07-PATTERNS.md
  - .planning/phases/07-difference-classification/07-VALIDATION.md
  - .planning/phases/07-difference-classification/07-01-PLAN.md
  - .planning/phases/07-difference-classification/07-02-PLAN.md
  - backend/shared/python/sunity_shared/analysis/body_normalizer.py
  - app/src/types/analysis.ts
  - app/src/lib/userAnalyses.ts
findings:
  critical: 2
  warning: 4
  info: 1
  total: 7
status: addressed
addressed_at: 2026-06-08T16:00:00Z
addressed_by: planner (iteration 2 revision)
addressed_in:
  - 07-01-PLAN.md (CR-01 render_finding_copy + CR-02 12 global keys + WR-01 placeholder uncertain + WR-03 _EMPTY_FOCUS_FALLBACK + WR-04 test_copy_templates_resolver_coverage)
  - 07-02-PLAN.md (CR-01 used_reference_fallback thread + WR-02 frontend normalize Task 3 re-added + WR-03 recommended_focus_fallback + INF-01 preserves_measurement_fields test)
  - 07-RESEARCH.md (Q1/Q2/Q4 RESOLVED revised; Canned String Coverage Audit 33 keys; Schema Extension +recommended_focus_fallback)
  - 07-VALIDATION.md (new test rows + iteration 2 finding map)
---

# Phase 7: Plan Risk Review

## Summary

Phase 7 is still in planning state. The planned implementation files are not present yet: `backend/shared/python/sunity_shared/analysis/copy_templates.py` does not exist, `backend/tests/phase07/` does not exist, and the current `BodyComparisonFinding` / `BodyComparisonReport` contracts are still Phase 6 only.

This review therefore evaluates the Phase 7 plan and its fit against the current Phase 6 code. The plan is directionally sound: keep classification pure-Python, use backend canned copy, preserve TS/Python/docs lockstep, and reuse the Phase 6 Firestore camelCase converter. The main risks are not dependency or security risks; they are contract mismatches that would make planned tests fail or silently ship generic/misleading copy.

Overall risk is **MEDIUM-HIGH until CR-01 and CR-02 are resolved**. After those fixes, the phase is executable with normal implementation risk.

## Current Implementation Status

- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:787-849` currently has no Phase 7 fields (`category`, `phase`, `body_type_interpretation`, `recommendation`, `do_not_over_correct`, `recommended_focus`).
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:1264-1297` still returns raw `findings` directly in `BodyComparisonReport`.
- `app/src/types/analysis.ts:490-550` still exposes the Phase 6 TS contract.
- `app/src/lib/userAnalyses.ts:27-56` still casts `raw.result` directly and does not normalize nested `bodyComparisonReport` fields.

## Critical Issues

### CR-01: `mode3_first + used_reference_fallback` dedicated copy is unreachable with the planned function contract

**Evidence:**
- `07-RESEARCH.md:1089-1093` resolves a single fallback recommendation: "이 동작은 기준 영상이 없어..."
- `07-01-PLAN.md:222` fixtures expect that exact fallback copy.
- `07-02-PLAN.md:193` calls `render_finding_copy(f.deficit_code, category, group, comparison_type)` without passing `used_reference_fallback`.
- `07-01-PLAN.md:278` defines `render_finding_copy()` without a fallback/context parameter.

**Issue:** `classify_findings()` can demote all findings to `uncertain`, but `copy_templates.render_finding_copy()` cannot know that the reason was `used_reference_fallback=True`. It will return the normal per-deficit `mode3_first` copy, not the resolved single fallback copy. There is also a test contradiction: `07-01-PLAN.md:264` expects mode3 prefix `"세계 심사 기준 (IPSF) 으로 보면"`, while `07-02-PLAN.md:175` expects the recommendation to start with `"이 동작은 기준 영상이 없어"`.

**Impact:** The Plan 02 fallback test will either fail, or the implementation will pass by weakening the assertion and production will show the wrong explanation for the Page 9-only path.

**Recommended mitigation:**
- Add explicit context to the copy path:
  - `render_finding_copy(..., *, used_reference_fallback: bool = False)` or
  - `copy_context: Literal["normal", "mode3_first_reference_missing"] = "normal"`.
- In `classify_findings()`, pass `used_reference_fallback` into `render_finding_copy()`.
- Decide one exact output shape:
  - Either the fallback copy is unprefixed and starts with `"이 동작은 기준 영상이 없어"`, or
  - the fixture must expect `"세계 심사 기준 (IPSF) 으로 보면 이 동작은 기준 영상이 없어..."`.
- Add an exact assertion for this path, not only `contains "강사"` or `startswith`.

### CR-02: Actual `clean_lines` findings will resolve to `global`, but canned copy has only `arm` / `leg`

**Evidence:**
- Current Phase 6 code emits `clean_lines` with `joint_key=None` at `body_normalizer.py:1027-1030`.
- `07-02-PLAN.md:159-161` excludes `clean_lines` from `_DEFICIT_TO_GROUP` and only uses `_JOINT_TO_GROUP` when `joint_key` is present.
- `07-02-PLAN.md:186` falls back to `_DEFICIT_TO_GROUP.get(..., "global")`.
- `07-RESEARCH.md:460-486` and `07-RESEARCH.md:597-605` define `clean_lines` copy only for `arm` and `leg`, not `global`.

**Issue:** The planned resolver maps real `clean_lines` outputs to `global`, causing `render_finding_copy()` to miss the key and return generic fallback copy. This means one of the main IPSF deficit types loses the intended body-part-specific explanation.

**Impact:** Tests may still pass if they only assert non-None copy, but production will degrade to generic "AI 분석 결과" wording for `clean_lines`.

**Recommended mitigation:**
- Change the Phase 6 finding to preserve extension source:
  - simplest: set `joint_key` to the dominant failed joint when emitting `clean_lines`, or add `joint_keys: list[str]` later if a multi-joint contract is acceptable.
- If the schema must stay unchanged, make `_resolve_joint_group()` accept `technique_profile` or an optional `default_clean_lines_group` computed from `expects`.
- Add a test that starts from the real current shape: `BodyComparisonFinding(deficit_code="clean_lines", joint_key=None, ...)`, then asserts the copy is not the generic fallback and the resolved group is `arm` or `leg`.

## Warnings

### WR-01: `body_type_allowed` placeholder is fail-open if Plan 01 lands without Plan 02 wiring

**Evidence:** `07-01-PLAN.md:351-368` makes `category` required and adds `category="body_type_allowed"` to all six `measure_ipsf_absolute_deficits()` call sites, with Plan 02 later replacing categories via `classify_findings()`.

**Issue:** During the Plan 01-only state, every raw deficit appears as `body_type_allowed`. Direct callers exist today in `backend/tests/phase06/test_body_normalizer_ipsf_deficit.py`, and any future direct consumer would see a misleading category.

**Impact:** If Plan 01 is merged/deployed separately, Phase 7 can temporarily produce "do not overcorrect" semantics for all findings, including `pose_reliability_low`.

**Recommended mitigation:**
- Treat Plan 01 + Plan 02 as one non-deployable branch and do not release after Plan 01.
- Safer code-level alternative: make the temporary category default `uncertain`, not `body_type_allowed`.
- Add a guard test after full Phase 7: direct `measure_ipsf_absolute_deficits()` is either internal-only or returns fail-safe `uncertain` placeholders.

### WR-02: Frontend normalization decision contradicts earlier Phase 7 context and leaves old docs unguarded

**Evidence:**
- `07-CONTEXT.md:147` says `app/src/lib/userAnalyses.ts::normalize` should be extended for Phase 7.
- `07-RESEARCH.md:328` says existing Firestore docs need graceful default handling in `userAnalyses.normalize()`.
- `07-02-PLAN.md:84` and `07-RESEARCH.md:1103-1107` delete the frontend normalize task and defer old-doc guards to Phase 12.
- Current `userAnalyses.ts:47-56` simply casts `raw.result`.

**Issue:** The plan makes `doNotOverCorrect` and `recommendedFocus` non-optional in TS, but old Firestore documents can lack both fields. That creates a runtime/contract gap for any result component that trusts the TS type before Phase 12 adds local null guards.

**Impact:** Not necessarily a Phase 7 backend failure, but it creates a sharp edge for Phase 12 and can produce `undefined.map` style UI errors if a component reads old analyses.

**Recommended mitigation:**
- Prefer adding a small Phase 7 normalization helper now:
  - `report.doNotOverCorrect ?? []`
  - `report.recommendedFocus ?? []`
  - per-finding `category ?? "uncertain"`, `phase ?? "hold"`.
- If this stays deferred, make TS fields optional until Phase 12 hardens reads, or add a Phase 12 blocker explicitly referencing this review.

### WR-03: `recommended_focus[]` will often be empty by design, but tests allow that without product-level acceptance

**Evidence:** `07-RESEARCH.md:350-376` notes the current deduction distribution is only `-0.2` or `-0.5`, so all adjusted IPSF geometric deficits become `body_type_allowed`; `needs_adjustment` mostly appears only for `pose_reliability_low`. `07-02-PLAN.md:258-259` allows both aggregate arrays to be empty in integration tests.

**Issue:** The Phase 7 goal says it outputs two result-copy boxes (`doNotOverCorrect` / `recommendedFocus`). In common high-quality videos, `recommended_focus[]` may be empty, so the backend technically satisfies the schema but not necessarily the expected result-screen experience.

**Impact:** The result screen can appear to lack next-step guidance exactly when a user expects coaching feedback.

**Recommended mitigation:**
- Keep the backend list empty if there is no real focus, but add an explicit contract field or documented frontend fallback:
  - `recommendedFocusFallback`, or
  - Phase 12 required copy: "현재 영상에서 즉시 보정할 항목이 명확히 보이지 않아요. 강사와 함께 다음 단계를 정해보세요."
- Add one integration test for the empty-focus path that asserts the downstream fallback contract is documented, not merely that an empty list is acceptable.

### WR-04: Tests do not verify resolver coverage from real findings to `_COPY_TEMPLATES`

**Evidence:** `07-01-PLAN.md:260` iterates `_COPY_TEMPLATES.keys()` and checks render success. That proves every declared template renders, but not that every real `BodyComparisonFinding` resolves to a declared template key.

**Issue:** This misses the `clean_lines -> global` gap in CR-02 and would miss future resolver/template drift.

**Impact:** Phase 7 can pass render coverage while production falls back to generic copy.

**Recommended mitigation:**
- Add a resolver coverage test:
  - Create one representative finding per Phase 6 emitted deficit shape.
  - Run `_resolve_joint_group(finding)`.
  - Assert `(finding.deficit_code, category, group) in _COPY_TEMPLATES` for all three categories.
- Make fallback tests separate and rare; generic fallback should not be used for known Phase 6 deficit codes.

## Info

### INF-01: `dataclasses.replace` ban is not the core safety property

**Evidence:** `07-RESEARCH.md:297` and `07-02-PLAN.md:179` ban `dataclasses.replace` and enforce this by AST grep.

**Issue:** The desired safety property is "new classified findings pass `BodyComparisonFinding.__post_init__` and preserve all original measurement fields." A blanket grep for `dataclasses.replace` does not test that property. Manual reconstruction can also drift if fields are added later.

**Recommended mitigation:**
- Replace the grep-only test with behavioral checks:
  - output finding is a different object,
  - original six measurement fields are preserved exactly,
  - invalid category raises through `__post_init__`.
- If project convention still forbids `replace`, keep the grep as a secondary convention test, not the primary correctness gate.

## Risk Assessment

| Dimension | Risk | Driver |
|---|---|---|
| Contract correctness | HIGH | CR-01 and CR-02 are direct mismatches between planned signatures, expected fixtures, and current Phase 6 finding shapes. |
| User-facing copy quality | MEDIUM-HIGH | Known findings can fall back to generic copy; fallback mode3 copy is ambiguous. |
| Frontend compatibility | MEDIUM | Non-optional TS arrays plus old Firestore docs plus raw cast in `userAnalyses.normalize()`. |
| Backend implementation complexity | LOW | Pure function + dict literal approach is appropriate and dependency-free. |
| Security / secrets | LOW | No new network, auth, package, or secret surface. |
| Test coverage | MEDIUM | Planned tests are numerous but miss resolver-to-template coverage and fallback exactness. |

## Recommended Gates Before Execute

1. Fix CR-01 by threading `used_reference_fallback` or an explicit copy context into `render_finding_copy()`, then align the exact expected fallback string.
2. Fix CR-02 by making `clean_lines` resolver coverage match current Phase 6 output (`joint_key=None`) or by changing Phase 6 to emit enough joint context.
3. Decide Plan 01/Plan 02 release gating: do not deploy the placeholder category state.
4. Add old-doc normalization or explicitly mark Phase 12 blocked on `bodyComparisonReport` null/default guards.
5. Add resolver coverage tests that prove every known Phase 6 deficit shape maps to a non-generic canned template.

## Verification Notes

No Phase 7 automated tests were run because the Phase 7 implementation and `backend/tests/phase07/` do not exist yet. This review is based on plan artifacts and current Phase 6 source contracts.
