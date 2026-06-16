---
phase: 11
slug: coachcommenthook-gemini
status: secured
threats_open: 0
threats_closed: 9
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
created: 2026-06-17
---

# SECURITY.md — Phase 11 (coachcommenthook-gemini)

**Audit date:** 2026-06-17
**ASVS Level:** 1
**block_on:** high
**Threats Closed:** 9/9
**threats_open:** 0
**Register source:** PLAN.md `<threat_model>` blocks (11-00 / 11-01 / 11-02) + prompt threat_register (register_authored_at_plan_time: true)

This audit VERIFIES each declared mitigation against the implementation. Every threat
verified by a grep/AST/runtime match in the cited file, not by documentation or intent.

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-11-01 | Tampering | mitigate | CLOSED | `coach_hook.py:60-116` `CoachCommentHook` frozen dataclass + `__post_init__` → `_validate_str_list` (`:32-57`) rejects list[dict]/list[list]/empty-str. Firestore backstop `firestore_admin.py:148-203` `_validate_coach_comment_hook` rejects list[dict]/tuple/nested on BOTH force-scoped branch (`:448-449`, fired ABOVE generic nested-dict reject) AND body precheck (`:864-868`, before generic validator). |
| T-11-02 | Tampering/Repudiation | mitigate | CLOSED | Hook-scoped `\d` guard `_enforce_no_hook_number_patterns` (`guardrails.py:55-76`) lives OUTSIDE global `_SCORE/_COORDINATE/_JUDGMENT_PATTERNS` tuples (`:26-44`). `forbid_measurement_units` is opt-in (default False, `:84`). Writer applies it reject-and-fallback (`coach_hook_writer.py:216-225` → returns None, no sanitize). Runtime confirmed: global guard does NOT reject `30도`/`50%`; hook guard rejects `23도/15%/3초/2회/15cm/180`; `87점` still rejected. gemini suite 111 PASS (no scene_finder/reference_extractor regression). |
| T-11-03 | DoS | mitigate | CLOSED | CR-01 (BLOCKER) fix verified in commit `70544a2`: `coach_hook_builder.py:180-199` `_clean_str_list` strips empty/whitespace + order-preserving dedupe; `_payload_to_hook` (`:202-249`) caps `[:3]`/`[:4]` and re-defaults so dataclass can never raise. Pipeline backstop `pipeline/app.py:2139-2160` wraps `build_coach_hooks` + `resolve_coach_hook_bundle` in try/except → `build_canned_hook` fallback, so no hook defect reaches `fail_analysis` (D-08). App null-guard `userAnalyses.ts:40-56` `normalizeCoachHook` returns null on non-object; merge uses `?? []` (`result.tsx:550,553`). phase11 33 tests PASS. |
| T-11-04 | Elevation of Privilege | mitigate | CLOSED | `result.tsx` renders ONLY `openQuestionsForCoach` (`:548-561,975`). Grep confirms ZERO render usage of `autoFindingsSummary`/`suggestedCues`/`coachComment`/`reviewedBy` (appear only in comment lines 546-547). v1 dataclass forces `coach_comment`/`reviewed_by` = None (`coach_hook.py:85-86`, `coach_hook_builder.py:161-162,247-248`); no write endpoint added. |
| T-11-05 | Information Disclosure | mitigate | CLOSED | `coach_hook_writer.py:98,117` loads key via `_default_api_key_loader` (Parameter Store seam), lazy `genai.Client` (`:168-170`). All log statements use `model=%s` only — key never logged (`:119,122,197,200,203,221,237,239`). `grep _client` → 0 (no private client field exposure). |
| T-11-06 | Tampering | mitigate | CLOSED | `pipeline/app.py:2126-2167` hook stored in separate `_force_hook`/`_body_hook` vars; `force_pattern_inference.coach_comment_hook` / `body_comparison_report.coach_comment_hook` via `dataclasses.replace`. `coach_details` (joint writer, `:2028`) is never written by the hook block — separate writer (`GeminiCoachHookWriter`) + separate `CoachHookBundle` schema, no mixing into joint `CoachPayload`. |
| T-11-07 | Tampering | mitigate | CLOSED | `coach_hook_builder.py:252-291` `resolve_coach_hook_bundle` pure helper returns `tuple[CoachCommentHook, CoachCommentHook]`; each report independently resolved (payload present → `_payload_to_hook`, else `build_canned_hook`) so None/partial/full bundle ALWAYS yields both non-None hooks (COACH-01 SC#2). No gemini.schemas import (duck-typed, `:167-177`). `test_coach_hook_fallback.py` 3-case (None/partial/full) PASS. |
| T-11-08 | Tampering | mitigate | CLOSED | `schemas.py:157-158` `CoachCommentHookPayload` and `:181-182` `CoachHookBundle` both `ConfigDict(extra="forbid")` → stray top-level key raises ValidationError (no silent drop). `test_bundle_extra_forbid` PASS. |
| T-11-SC | Tampering (supply chain) | accept | CLOSED | Accepted risk recorded below. Verified: zero requirements.txt/package.json changes across all Phase 11 commits (latest dep change is pre-existing phase 04/17). No novel third-party imports in coach_hook_writer.py. |

## Accepted Risks Log

- **T-11-SC (supply chain — npm/pip install):** Phase 11 adds zero new packages.
  Verified via git history (no `requirements.txt`/`package.json` diff in any Phase 11
  commit `58be472..HEAD`) and import inspection (writer uses only pre-existing
  `json`/`logging`/`time`/`typing`/`pydantic`/`google` + internal `sunity_shared`).
  Disposition `accept` is appropriate — no install task means no new attack surface.

## Unregistered Flags

None. All three SUMMARY.md `## Threat Flags` sections report "None — 신규 보안 surface 0",
and the new attack surface introduced (LLM output → CoachCommentHook → Firestore →
app render) is fully mapped to T-11-01 through T-11-08. No new entry point appeared
during implementation without a threat mapping.

## Verification Commands Run

- `cd backend && PYTHONPATH=shared/python python3 -m pytest tests/phase11 -q` → 33 passed
- `cd backend && PYTHONPATH=shared/python python3 -m pytest tests/gemini -q` → 111 passed
  (confirms global guard non-pollution / scene_finder / reference_extractor no regression)
- Runtime guard scoping check: global guard PASSES `30도`/`50%`; hook guard REJECTS
  `23도`/`23°`/`15%`/`3초`/`2회`/`15cm`/`180`; `87점` rejected globally.

## Deferred Review Findings (NOT blockers, documented in 11-REVIEW.md)

These are robustness/cleanup items, not gaps in any declared mitigation. They do not
re-open any threat under the current configuration:

- **WR-02 / IN-02** — body hook attachment is nested under `if force_signals_report is
  not None:`; gate is always-true today (`compute_force_signals` returns non-None), so
  no body hook is lost currently. Latent coupling — candidate for follow-up cleanup.
- **WR-03 / WR-04** — writer guard runs on the production raw-text path; the
  `parsed`/duck-bundle shortcuts are test-injection seams. Real `genai` responses use a
  stripped-dict `response_schema` (not the Pydantic class), so they always traverse the
  guarded raw-text branch. Number-free / objectivity lock not bypassable in production.
- **WR-05** — test fixture uses an unenforced `deficit_code`; `_DEFICIT_CODES` frozenset
  is defined but not validated at the dataclass boundary. Test-fidelity / Phase-7 scope,
  not a Phase 11 mitigation gap.
- **IN-01 / IN-03** — dead retry artifacts (`time.sleep(0.0)`, unreachable `bundle = None`)
  and a pre-existing UI TODO filler comment. Cosmetic.
