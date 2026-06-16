---
phase: 11-coachcommenthook-gemini
verified: 2026-06-17T02:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
mode: mvp
re_verification: false
---

# Phase 11: CoachCommentHook 데이터 구조 + Gemini 자연어 번역만 — Verification Report

**Phase Goal:** 모든 리포트에 `CoachCommentHook`이 부착되고, Gemini는 구조화된 finding을 자연어로 번역만 한다 (판단·좌표 출력 금지). 결과 화면 카피가 AI를 "강사 보조 도구"로 포지셔닝한다. (mode: mvp — outcome verification)
**Verified:** 2026-06-17T02:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — the contract)

| # | Truth (SC) | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `CoachCommentHook`(autoFindingsSummary, openQuestionsForCoach, suggestedCues, coachComment?, reviewedBy) 타입이 데이터 계약 양쪽에 추가된다 | ✓ VERIFIED | 3-way lockstep confirmed: `coach_hook.py:60` frozen dataclass with all 5 fields + source_report provenance; `analysis.ts:934` interface + both report fields (`:921`, `:1227`); `models.py:290` re-export only (no class redefinition); `docs/contract.md §9.11.7`. All 5 SC#1 fields present. `npm run typecheck` clean. |
| 2 | 모든 리포트(BodyComparisonReport, ForcePatternInference)에 coachCommentHook이 부착된다 | ✓ VERIFIED | `force_pattern.py:255` + `body_normalizer.py:896` both have `coach_comment_hook: CoachCommentHook \| None = None`. Pipeline wiring `app.py:2161-2167` attaches force_hook + body_hook via `dataclasses.replace`. `resolve_coach_hook_bundle` guarantees both non-None (None/partial/full bundle). Verified at runtime: api-key-failure path → both hooks canned & non-None. |
| 3 | Gemini 프롬프트가 "자연어 번역만, 좌표·판단·점수 출력 금지"로 설계되고 검증된다 | ✓ VERIFIED | `coach_hook_writer.py` text-only (0 video-touch: GeminiVisionCall/files.upload/videoPath = 0), `resolve_model("B")` (0 hardcoded model), runs `_enforce_no_reject_patterns(..., forbid_measurement_units=True)`. Hook-scoped guard `_enforce_no_hook_number_patterns` rejects ALL Arabic digits; runtime-confirmed reject of 3초/180/15cm/23도/15%/2회 AND global path PASS for 30도/50% (no scene_finder regression). reject-and-fallback (no sanitize-and-emit, D-05). 33 phase11 tests pass. |
| 4 | 결과 화면 카피가 AI를 강사 보조 도구로 포지셔닝하고 기준 모션이 "하나의 참고일 뿐"으로 명시된다 | ✓ VERIFIED | `result.tsx:703` "이 분석은 강사 지도를 돕는 참고예요" + `:724` "기준 모션은 하나의 참고일 뿐이에요" + `:970` "강사에게 확인할 점" section. D-06 enforced: autoFindingsSummary/suggestedCues NOT rendered (grep=0). HIGH-2 merge fix: both reports concat (`[...force, ...body]` `:555`), not `??`-chain. belle human-verify checkpoint approved (11-02 Task 2). |
| 5 | Gemini hook-writer LLM 키 미설정 또는 hook 호출 실패 시에도 canned fallback 카피로 분석이 완료된다 | ✓ VERIFIED | Runtime-confirmed: failing api_key_loader → `build_coach_hooks` returns None → `resolve_coach_hook_bundle` produces canned hooks (both non-None). Defense-in-depth: pipeline `app.py:2139-2160` wraps hook gen in try/except → `build_canned_hook` fallback, so NO hook defect reaches `fail_analysis` (D-08). CR-01 crash path (empty/whitespace list items) reproduced → NO RAISE after fix. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `coach_hook.py` | CoachCommentHook frozen dataclass + pure validators, 0 finding imports | ✓ VERIFIED | 119 lines, `class CoachCommentHook` + `_validate_str_list`; finding-import grep = 0 (HIGH-3 circular-safe). |
| `coach_hook_builder.py` | build_canned_hook + resolve_coach_hook_bundle (implemented, not stub) + CR-01 sanitize | ✓ VERIFIED | NotImplementedError replaced; `_clean_str_list` (CR-01 fix) strips/dedupes, `[:3]`/`[:4]` caps; 0 gemini.schemas import (MEDIUM-2 duck-type). |
| `coach_hook_writer.py` | text-only GeminiCoachHookWriter, bundle\|None only | ✓ VERIFIED | `class GeminiCoachHookWriter`, `_strip_unsupported_schema_keys` reuse, 0 video/0 hardcoded model. |
| `schemas.py` | CoachHookBundle + CoachCommentHookPayload, both extra=forbid | ✓ VERIFIED | `:158` + `:182` both `extra="forbid"` + camelCase alias. |
| `guardrails.py` | hook-scoped number-free guard, global non-pollution | ✓ VERIFIED | `_enforce_no_hook_number_patterns` + `forbid_measurement_units` flag; global tuples untouched. |
| `firestore_admin.py` | `_validate_coach_comment_hook` (force scoped + body precheck) | ✓ VERIFIED | `:148` dedicated whitelist (no generic delegation), force branch `:448`, body precheck `:864`. |
| `result.tsx` | 강사에게 확인할 점 section + merge + positioning copy | ✓ VERIFIED | section `:970`, merge `:555`, copy `:703`/`:724`, D-06 non-exposure grep=0. |
| `userAnalyses.ts` | coachCommentHook null-guard normalize | ✓ VERIFIED | 7 coachCommentHook references (both reports normalized). |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| analysis.ts | models.py | 3-way lockstep re-export | ✓ WIRED |
| pipeline/app.py | coach_hook_writer.py | build_coach_hooks single call (`:2140`) | ✓ WIRED |
| pipeline/app.py | coach_hook_builder.py | resolve_coach_hook_bundle per-report fallback (`:2144`) | ✓ WIRED |
| pipeline/app.py | firestore_admin.py | complete_analysis hook dict (coachCommentHook) | ✓ WIRED |
| result.tsx | force + body coachCommentHook | concat→trim→filter→dedupe→slice(0,5) (`:555`) | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Result | Status |
| --- | --- | --- |
| phase11 suite (33 tests) | 33 passed | ✓ PASS |
| Regression (phase07/09/11/gemini, 378) | 378 passed | ✓ PASS |
| CR-01 crash repro (empty/whitespace list) | NO RAISE, clean hooks returned | ✓ PASS |
| Global guard non-regression (30도/50%) | PASS on global path | ✓ PASS |
| Hook-scoped guard (3초/180/15cm/23도/15%/2회) | all rejected | ✓ PASS |
| D-08/SC#5 api-key-failure → canned | both hooks non-None, no crash | ✓ PASS |
| app `npm run typecheck` | clean (exit 0) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| --- | --- | --- | --- |
| COACH-01 | 11-00, 11-01 | ✓ SATISFIED | CoachCommentHook 3-way lockstep + attached to both reports (SC#1, SC#2). |
| FEED-02 | 11-00, 11-01, 11-02 | ✓ SATISFIED | Pre-existing dual-coach feedback ordering (REQUIREMENTS.md marks Complete via Phase 9+11); Phase 11 hook is a layer above — 0 rework, no regression (378 tests pass). |
| FEED-03 | 11-01, 11-02 | ✓ SATISFIED | Result-screen positioning copy "강사 보조 도구" + "하나의 참고일 뿐" (result.tsx, belle-approved). |

All 3 declared requirement IDs accounted for. No orphaned requirements (REQUIREMENTS.md maps exactly COACH-01/FEED-02/FEED-03 to Phase 11).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| result.tsx | 1066 | `TODO: Firebase displayName 박제…` filler comment | ℹ️ Info | Pre-existing (IN-03), in untouched code adjacent to Phase 11. `TODO` (warning-level), not TBD/FIXME/XXX. Documented deferral. Not a blocker. |

No TBD/FIXME/XXX debt markers in any Phase 11 modified file (scan = 0). No stub patterns (NotImplementedError stubs from Wave 0 are fully replaced).

### Code Review Resolution Confirmed

- **CR-01 (BLOCKER)** — malformed LLM hook crashing analysis: **FIXED & VERIFIED**. Two-layer defense: (1) `_clean_str_list` in resolver strips/defaults so `_payload_to_hook` can never build an invalid dataclass; (2) pipeline try/except → `build_canned_hook`. Exact review reproduction now returns clean hooks with no raise. D-08/SC#5 holds.
- **WR-01** — uncapped/un-deduped LLM lists: FIXED (`[:3]`/`[:4]` + dedupe in `_clean_str_list`).
- **WR-02..05, IN-01..03** — documented deferrals; none is an active correctness break under current config. WR-02 (body-hook coupling to `force_signals_report is not None`) confirmed latent-only: `compute_force_signals` returns non-None `ForceSignalsReport` today, gate is always-true.

### Human Verification Required

None. The one human-verify checkpoint (11-02 Task 2 — result-screen copy/section visual) was completed and approved by belle during execution. Real-LLM E2E is explicitly deferred to Phase 15 실증 per ROADMAP, not a Phase 11 deliverable.

### Gaps Summary

No gaps. All 5 ROADMAP success criteria are observably true in the codebase, all 3 requirement IDs satisfied, the BLOCKER from code review is verifiably fixed (crash path reproduced and confirmed non-raising), 33 phase11 tests + 378 regression tests pass, tsc clean, and the goal — every report gains a CoachCommentHook from a text-only number-free Gemini writer surfaced as "강사에게 확인할 점" with AI-as-coach-assistant positioning — is fully achieved.

---

_Verified: 2026-06-17T02:00:00Z_
_Verifier: Claude (gsd-verifier)_
