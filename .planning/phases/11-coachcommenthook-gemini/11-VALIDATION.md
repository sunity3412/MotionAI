---
phase: 11
slug: coachcommenthook-gemini
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-16
revised: 2026-06-16
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 11-RESEARCH.md §Validation Architecture. Focus: D-05 translation-only enforcement (incl. degree/% per review HIGH-1) + D-08 fallback (api_key_loader seam per WARNING-2) + nested-array safety.
> [2026-06-16 review revision] Added degree-guard test; fallback seam = api_key_loader/None-return (not private `_client`); Wave 0 collection-green requirement (WARNING-1).

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
- **Before `/gsd-verify-work`:** Full backend suite green (incl. Vision writer test_coach_writer_v2.py unchanged) + `tsc --noEmit` clean
- **Max feedback latency:** ~30 seconds
- **Real-LLM E2E:** explicitly deferred to Phase 15 실증 (per CONTEXT) — not a phase-11 gate

---

## Per-Task Verification Map

| Req | Behavior | Test Type | Automated Command | File Exists |
|-----|----------|-----------|-------------------|-------------|
| COACH-01 | CoachCommentHook attaches to both reports; serializes flat (no nested array; list[str] only) | unit | `python -m pytest tests/phase11/test_coach_hook_nested_array.py -x` | ❌ W0 |
| COACH-01 | Scoped validator (`ForcePatternInference`) accepts `coachCommentHook` key AND rejects `list[dict]`/nested-list | unit | `python -m pytest tests/phase11/test_coach_hook_nested_array.py -x` | ❌ W0 |
| COACH-01 | TS↔Python↔contract shapes mirror; app null-guard compiles | typecheck | `cd app && npm run typecheck` | ✅ existing gate |
| COACH-01 | coach_hook.py = dataclass + pure validators only; no circular import (force_pattern↔coach_hook) | unit | `PYTHONPATH=shared/python python -c "import sunity_shared.analysis.force_pattern, sunity_shared.analysis.coach_hook"` | ❌ W0 |
| FEED-03 / D-04 | Golden finding → hook text has 0 score/coord/judgment patterns | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py -x` | ❌ W0 |
| FEED-03 / D-04 / HIGH-1 | Hook prose number-free: `_enforce_no_reject_patterns("23도"/"23°"/"15%")` raises ValueError | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py::test_guard_rejects_degree -x` | ❌ W0 |
| FEED-03 / D-05 | Runtime guard rejects LLM-minted number/judgment (mock LLM emits "87점"/"훌륭"/"23도" → reject → canned fallback) | unit | `python -m pytest tests/phase11/test_coach_hook_translation_only.py::test_guard_rejects_score -x` | ❌ W0 |
| ROADMAP #5 / D-08 / WARNING-2 | api_key_loader fail / hook call returns None → canned hook returned, analysis completes (status done). Seam = api_key_loader/None, NOT private `_client` | unit | `python -m pytest tests/phase11/test_coach_hook_fallback.py -x` | ❌ W0 |
| COACH-01 / BLOCKER-1 | Vision GeminiCoachWriter.write() untouched (separate text-only writer) | regression | `git diff --stat backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` (0 lines) + `python -m pytest tests/gemini/test_coach_writer_v2.py -x` | ✅ existing gate |
| FEED-03 / D-06,D-07 / HIGH-2 | Both reports' openQuestionsForCoach merged (concat/dedupe/slice); positioning copy present; autoFindingsSummary/suggestedCues stored-not-displayed; coachComment/reviewedBy null in v1 | typecheck + manual | `cd app && npm run typecheck` (+ manual UI verify, E2E deferred Phase 15) | manual |

*Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/shared/python/sunity_shared/analysis/coach_hook_builder.py` — `build_canned_hook` stub raising `NotImplementedError` (WARNING-1: keeps Wave-0 test collection GREEN while behavior RED; Wave 1 implements)
- [ ] `backend/tests/phase11/conftest.py` — shared golden `ForcePatternFinding` / `BodyComparisonFinding` fixtures
- [ ] `backend/tests/phase11/test_coach_hook_translation_only.py` — golden finding fixtures + mock-LLM forbidden-output cases **incl. degree/% (`23도`/`23°`/`15%`)** (COACH-01/FEED-03/D-04/D-05/HIGH-1). Pattern from `tests/phase09/test_force_pattern_copy_no_forbidden.py` and `tests/phase13/test_branch2_forbidden_phrase_gate.py`
- [ ] `backend/tests/phase11/test_coach_hook_fallback.py` — api_key_loader fail / None-return seam → canned hook; assert analysis completes (D-08, WARNING-2). MUST NOT assert private `_client` shape
- [ ] `backend/tests/phase11/test_coach_hook_nested_array.py` — scoped validators pass a valid flat hook AND reject `list[dict]`/nested-list (Pitfall 1+2)
- [ ] Collection MUST be green (`pytest tests/phase11 --co` 0 errors); RED is assertion/NotImplementedError level (WARNING-1)
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
- [ ] Wave 0 covers all MISSING references (translation-only incl. degree, fallback seam, nested-array)
- [ ] Wave 0 collection green (no top-level import errors masquerading as RED)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
</content>
