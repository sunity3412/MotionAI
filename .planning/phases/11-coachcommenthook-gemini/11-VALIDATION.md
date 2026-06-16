---
phase: 11
slug: coachcommenthook-gemini
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-16
revised: 2026-06-17
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 11-RESEARCH.md §Validation Architecture. Focus: D-05 translation-only enforcement (hook-scoped number-free \d guard per iter-3 HIGH-2) + D-08 fallback (api_key_loader seam per WARNING-2 + 5xx retry per iter-2 HIGH-1) + dedicated hook validator (iter-2 BLOCKER-1) + pure resolve_coach_hook_bundle per-report fallback (iter-3 HIGH-1) + schema-strip config reuse (iter-2 HIGH-1) + extra=forbid drift (iter-3 MEDIUM-1).
> [2026-06-16 review iter-1] Added degree-guard test; fallback seam = api_key_loader/None-return (not private `_client`); Wave 0 collection-green requirement (WARNING-1).
> [2026-06-16 review iter-2] degree/% guard is HOOK-SCOPED (global non-regression test added); dedicated `_validate_coach_comment_hook` (force scoped + body precheck, list[dict] reject); schema-strip config inspection test; per-report partial-bundle fallback test; 5xx retry path.
> [2026-06-17 review iter-3] fallback ownership SPLIT — `build_coach_hooks` returns CoachHookBundle|None only; pure `resolve_coach_hook_bundle` helper owns per-report fallback (partial/None tests target the helper in Task 1). Hook guard rejects ALL `\d` (3초/2회/15cm/180 + degree/%), not just degree/%. `CoachCommentHookPayload` AND `CoachHookBundle` both `ConfigDict(extra="forbid")` + drift test. Behavior-level acceptance; grep demoted to secondary.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (`backend/requirements-dev.txt`) for backend; `tsc --noEmit` (`npm run typecheck`) for app (no JS test runner) |
| **Config file** | none committed (pytest discovers `backend/tests/`); app has no jest/vitest |
| **Quick run command** | `cd backend && PYTHONPATH=shared/python python -m pytest tests/phase11 -x -q` |
| **Full suite command** | `cd backend && PYTHONPATH=shared/python python -m pytest -q` then `cd app && npm run typecheck` |
| **Estimated runtime** | ~30 seconds (backend unit) + typecheck |

---

## Sampling Rate

- **After every task commit:** `cd backend && PYTHONPATH=shared/python python -m pytest tests/phase11 -x -q`
- **After every plan wave:** `cd backend && PYTHONPATH=shared/python python -m pytest -q` then `cd app && npm run typecheck`
- **Before `/gsd-verify-work`:** Full backend suite green (incl. Vision writer test_coach_writer_v2.py + scene_finder/reference_extractor guard tests unchanged) + `tsc --noEmit` clean
- **Max feedback latency:** ~30 seconds
- **Real-LLM E2E:** explicitly deferred to Phase 15 실증 (per CONTEXT) — not a phase-11 gate

---

## Per-Task Verification Map

| Req | Behavior | Test Type | Automated Command | File Exists |
|-----|----------|-----------|-------------------|-------------|
| COACH-01 | CoachCommentHook attaches to both reports; serializes flat (list[str] only) | unit | `python -m pytest tests/phase11/test_coach_hook_nested_array.py -x` | ❌ W0 |
| COACH-01 / iter-2 BLOCKER-1 | Dedicated `_validate_coach_comment_hook` accepts flat list[str] hook AND rejects list[dict] / nested list / unknown key — **FORCE path** (`_validate_force_pattern_inference` branch) | unit | `python -m pytest tests/phase11/test_coach_hook_nested_array.py -x` | ❌ W0 |
| COACH-01 / iter-2 BLOCKER-1 | Same dedicated validator runs on **BODY path** via `complete_analysis` precheck (generic validator alone allows list[dict] → precheck mandatory) | unit | `python -m pytest tests/phase11/test_coach_hook_nested_array.py -x` | ❌ W0 |
| COACH-01 | TS↔Python↔contract shapes mirror; app null-guard compiles | typecheck | `cd app && npm run typecheck` | ✅ existing gate |
| COACH-01 | coach_hook.py = dataclass + pure validators only; no circular import (force_pattern↔coach_hook) | unit | `PYTHONPATH=shared/python python -c "import sunity_shared.analysis.force_pattern, sunity_shared.analysis.coach_hook"` | ❌ W0 |
| FEED-03 / D-04 | Golden finding → hook text has 0 score/coord/judgment patterns | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py -x` | ❌ W0 |
| FEED-03 / D-04 / iter-3 HIGH-2 | **Hook-scoped number-free guard:** hook guard (`_enforce_no_hook_number_patterns` or `forbid_measurement_units=True`) raises on **ALL Arabic digits** — "3초"/"2회"/"15cm"/"180" (bare numeric) + "23도"/"23°"/"23 deg"/"15%" (degree/%). Behavior assert, not grep. | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py::test_hook_guard_rejects_all_digits -x` | ❌ W0 |
| FEED-03 / iter-2 BLOCKER-2 | **Global-guard non-regression:** default `_enforce_no_reject_patterns("등이 30도 이상 후굴" / "50% 가려짐")` does NOT raise (scene_finder/reference_extractor unaffected) | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py::test_global_guard_allows_degree_percent -x` | ❌ W0 |
| FEED-03 / D-05 | Runtime guard rejects LLM-minted score/judgment/digit (mock LLM "87점"/"훌륭"/"3초" → reject → build_coach_hooks None → resolve canned fallback) | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py::test_guard_rejects_score -x` | ❌ W0 |
| COACH-01 / iter-2 HIGH-1 | Hook writer config reuses `_strip_unsupported_schema_keys(CoachHookBundle.model_json_schema())` — config passed to generate_content has 0 `$defs`/`additionalProperties`/`discriminator` keys | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py::test_config_schema_stripped -x` | ❌ W0 |
| COACH-01 / iter-3 MEDIUM-1 | **extra=forbid drift:** `CoachHookBundle.model_validate({...valid..., "unexpected": 1})` raises ValidationError; `CoachCommentHookPayload` stray key raises (LLM-boundary schema-drift, separate from Firestore validator) | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py::test_bundle_extra_forbid -x` | ❌ W0 |
| ROADMAP #5 / D-08 / WARNING-2 / iter-2 HIGH-1 | api_key_loader fail / None-return → `build_coach_hooks` returns None; resolve_coach_hook_bundle fills canned, analysis completes (status done). + 5xx APIError → 1 retry; 4xx → None. Seam = api_key_loader/None, NOT private `_client` | unit | `python -m pytest tests/phase11/test_coach_hook_fallback.py -x` | ❌ W0 |
| COACH-01 / iter-3 HIGH-1 | **Pure `resolve_coach_hook_bundle`** fallback: bundle=None → both canned; partial bundle (one report payload only) → present side converted + missing side canned; full bundle → both converted. BOTH hooks non-None in all 3 cases. Helper is pure (no AWS/Firestore I/O). Test targets the helper in Task 1 (NOT pipeline wiring). | unit | `python -m pytest tests/phase11/test_coach_hook_fallback.py::test_resolve_coach_hook_bundle -x` | ❌ W0 |
| COACH-01 / BLOCKER-1 (iter-1) | Vision GeminiCoachWriter.write() untouched (separate text-only writer) | regression | `git diff --stat backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` (0 lines) + `python -m pytest tests/gemini/test_coach_writer_v2.py -x` | ✅ existing gate |
| FEED-03 / D-06,D-07 / HIGH-2 (iter-1) | Both reports' openQuestionsForCoach merged (concat/dedupe/slice); positioning copy present; autoFindingsSummary/suggestedCues stored-not-displayed; coachComment/reviewedBy null in v1 | typecheck + manual | `cd app && npm run typecheck` (+ manual UI verify, E2E deferred Phase 15) | manual |

*Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/shared/python/sunity_shared/analysis/coach_hook_builder.py` — `build_canned_hook` stub raising `NotImplementedError` + `resolve_coach_hook_bundle` stub raising `NotImplementedError` (WARNING-1: keeps Wave-0 test collection GREEN while behavior RED; Wave 1 implements both)
- [ ] `backend/tests/phase11/conftest.py` — shared golden `ForcePatternFinding` / `BodyComparisonFinding` fixtures
- [ ] `backend/tests/phase11/test_coach_hook_translation_only.py` — golden finding fixtures + (a) forbidden-phrase 0-hit + (b) **hook-scoped number-free** reject of ALL `\d` ("3초"/"2회"/"15cm"/"180" + "23도"/"23°"/"23 deg"/"15%", iter-3 HIGH-2) + (c) **global-guard non-regression** ("30도"/"50%" PASS, iter-2 BLOCKER-2) + (d) score/judgment reject + (e) **schema-strip config inspection** ($defs/additionalProperties absent, iter-2 HIGH-1) + (f) **extra=forbid drift** (CoachHookBundle + CoachCommentHookPayload stray key → ValidationError, iter-3 MEDIUM-1). Pattern from `tests/phase09/test_force_pattern_copy_no_forbidden.py` and `tests/phase13/test_branch2_forbidden_phrase_gate.py`
- [ ] `backend/tests/phase11/test_coach_hook_fallback.py` — api_key_loader fail / None-return seam + 5xx retry / 4xx None (iter-2 HIGH-1) → `build_coach_hooks` None; assert analysis completes (D-08, WARNING-2). + **pure `resolve_coach_hook_bundle`** 3-case fallback (None / partial / full → both hooks non-None, iter-3 HIGH-1) — test targets the PURE helper, not pipeline. MUST NOT assert private `_client` shape
- [ ] `backend/tests/phase11/test_coach_hook_nested_array.py` — **dedicated `_validate_coach_comment_hook`** (NOT generic) passes valid flat list[str] hook AND rejects list[dict] / nested list / unknown key, on **FORCE path AND BODY precheck path** (iter-2 BLOCKER-1)
- [ ] Collection MUST be green (`pytest tests/phase11 --co` 0 errors); RED is assertion/NotImplementedError/AttributeError level (WARNING-1)
- [ ] No framework install needed (pytest already present)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Result-screen merged "강사에게 확인할 점" section (BOTH reports' openQuestionsForCoach) + positioning 1-liner + Mode 1 "하나의 참고일 뿐" label renders correctly with theme tokens | FEED-03 / D-06,D-07 / HIGH-2 | No RN UI test runner; visual/theme correctness | Run app, open a completed analysis with both report hooks, confirm BOTH reports' questions appear merged+deduped, positioning copy appears; confirm autoFindingsSummary/suggestedCues NOT shown. E2E deferred to Phase 15 |
| Real Gemini hook generation produces objective Korean prose (number-free) | FEED-03 / D-04 | Requires live Gemini key + real analysis | Deferred to Phase 15 실증 (real-LLM E2E) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (translation-only incl. hook-scoped number-free \d + global non-regression, fallback seam + retry, dedicated validator force+body, schema-strip config, pure resolve_coach_hook_bundle fallback, extra=forbid drift)
- [ ] Wave 0 collection green (no top-level import errors masquerading as RED)
- [ ] **fallback ownership split resolved** (build_coach_hooks returns bundle|None only; pure `resolve_coach_hook_bundle` helper owns per-report fallback; partial/None tests target the helper in Task 1, iter-3 HIGH-1)
- [ ] **bare-numeric hook guard covered** (hook guard rejects ALL `\d` — 3초/2회/15cm/180 + degree/%; global guard non-regression intact, iter-3 HIGH-2)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** ready (plan-validation contract complete per iter-3; Wave 0 tests not yet written → wave_0_complete: false)
