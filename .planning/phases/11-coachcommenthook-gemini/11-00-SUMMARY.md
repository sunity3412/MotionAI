---
phase: 11-coachcommenthook-gemini
plan: 00
subsystem: backend-contract
tags: [coach-hook, gemini, contract-lockstep, tdd-scaffold, firestore]
requires:
  - ForcePatternInference (Phase 9)
  - BodyComparisonReport (Phase 7)
  - gemini.guardrails._enforce_no_reject_patterns (Phase 17)
provides:
  - CoachCommentHook (3-way lockstep type)
  - coach_hook_builder.build_canned_hook (stub)
  - coach_hook_builder.resolve_coach_hook_bundle (stub)
  - phase11 Nyquist test scaffold (collection-green + intentional RED)
affects:
  - app/src/types/analysis.ts
  - backend/shared/python/sunity_shared/models.py
  - docs/contract.md
tech-stack:
  added: []
  patterns:
    - "module split (dataclass vs builder) for circular-import safety (HIGH-3)"
    - "collection-green + intentional-RED Wave 0 test scaffold (getattr/signature probe)"
    - "3-way contract lockstep (TS interface ↔ Python re-export ↔ docs §)"
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/coach_hook.py
    - backend/shared/python/sunity_shared/analysis/coach_hook_builder.py
    - backend/tests/phase11/__init__.py
    - backend/tests/phase11/conftest.py
    - backend/tests/phase11/test_coach_hook_translation_only.py
    - backend/tests/phase11/test_coach_hook_fallback.py
    - backend/tests/phase11/test_coach_hook_nested_array.py
  modified:
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
decisions:
  - "coach_hook.py = frozen dataclass + pure validator only; builder/resolver in separate coach_hook_builder.py (HIGH-3 circular-import block)"
  - "list 필드 list[str] 전용; __post_init__ strict + Wave 1 전용 Firestore validator (nested-array safe)"
  - "coach_comment/reviewed_by/source_report = v1 None default (D-06 — v2 강사 콘솔)"
  - "Wave 0 test scaffold never top-level imports Wave-1 symbols — getattr/signature probe → RED, collection GREEN (WARNING-1/iter-4 HIGH-2)"
metrics:
  duration: ~25m
  completed: 2026-06-17
  tasks: 2
  files: 9
---

# Phase 11 Plan 00: CoachCommentHook 계약 + Wave 0 Nyquist scaffold Summary

CoachCommentHook 타입을 analysis.ts ↔ models.py ↔ contract.md 3-way lockstep 으로 추가하고, circular-import 회피를 위해 dataclass(`coach_hook.py`)와 builder/resolver 진입점(`coach_hook_builder.py`)을 분리했으며, Phase 11 의 5-파일 test scaffold 를 collection-green + intentional-RED 상태로 박제했다.

## What Was Built

### Task 1 — CoachCommentHook dataclass + 3-way lockstep (atomic, commit 58be472)

- **`coach_hook.py` (신규):** `@dataclass(frozen=True) class CoachCommentHook` — 3 non-default 필드 (`auto_findings_summary: str`, `open_questions_for_coach: list[str]`, `suggested_cues: list[str]`) → 3 default 필드 (`coach_comment / reviewed_by / source_report: str | None = None`). `__post_init__` 가 list 필드를 `_validate_str_list` pure helper 로 strict 검증 (list[dict]/nested list → ValueError). finding 클래스 import 0 (HIGH-3 순환 차단).
- **`analysis.ts`:** `CoachCommentHook` interface 추가 (list 필드 = `string[]`, scalar = `string | null`) + `ForcePatternInference` / `BodyComparisonReport` 두 interface 에 `coachCommentHook?: CoachCommentHook | null` 추가.
- **`models.py`:** `from .analysis.coach_hook import CoachCommentHook` re-export only (재정의 0).
- **`contract.md`:** §9.11.7 CoachCommentHook 하위 섹션 (필드 표 + list[str] 전용 + v1 null) + §8 BodyComparisonReport 표에 `coachCommentHook` row.

### Task 2 — builder stub + phase11 test scaffold (commit f93ac1b)

- **`coach_hook_builder.py` (신규):** `build_canned_hook(findings, *, source_report)` + `resolve_coach_hook_bundle(bundle, *, force_findings, body_findings)` 둘 다 `raise NotImplementedError("Wave 1: 11-01 Task 1")`. finding 클래스는 `TYPE_CHECKING` 가드로만 참조 (top-level import 0).
- **`conftest.py`:** golden `ForcePatternFinding` (pull/hold/axis_tilt) + `BodyComparisonFinding` (needs_adjustment line deficit) — 실 생성자 시그니처로 빌드.
- **3 test 파일** (33 tests collected, 0 collection error):
  - `test_coach_hook_translation_only.py` — D-05 forbidden-phrase (9) + hook-scoped all-digit guard (도/% + bare 3초/2회/15cm/180) + 글로벌 비회귀 (30도/50% PASS) + score reject.
  - `test_coach_hook_fallback.py` — writer seam None-only (api_key 실패 / 4xx / 5xx retry exhausted) + 5xx→retry→성공 + pure resolver 3-case (None/partial/full → 항상 양쪽 non-None) + schema extra=forbid (getattr/SimpleNamespace, private client probe 0).
  - `test_coach_hook_nested_array.py` — 전용 `_validate_coach_comment_hook` 게이트 (force path AND body path), list[dict]/nested list/unknown key reject.

## Verification Results

- `npm run typecheck` — clean (exit 0; main-repo tsc via 임시 symlink, 작업 후 제거).
- `pytest tests/phase11 -q --co` — 33 tests collected, **0 collection error** (WARNING-1 collection-green).
- `pytest tests/phase11 -q` — 28 failed (intentional RED) + 5 passed (regression-guard: 글로벌 가드 30도/50% PASS, score reject PASS, force-path generic nested reject PASS).
- 순환 import: `force_pattern + coach_hook + coach_hook_builder + body_normalizer` 동시 import 통과.
- detail2/CoachingTipDetail grep count = 3 (불변 — D-01 무수정).
- coach_hook.py / coach_hook_builder.py finding top-level import = 0 (HIGH-3).
- Wave-1 심볼 top-level import = 0 (iter-4 HIGH-2).

## Deviations from Plan

None - plan executed exactly as written.

Note: 계획에 명시된 `test_bundle_extra_forbid` (schema extra=forbid 게이트, action L151) 를 `test_coach_hook_fallback.py` 에 getattr-only 로 포함했다 — 별도 deviation 아님 (action 명세 준수).

## Known Stubs

의도된 Wave 0 stub (Wave 1 Plan 11-01 이 GREEN 으로 전환):

| File | Symbol | Reason |
|------|--------|--------|
| coach_hook_builder.py | `build_canned_hook` | NotImplementedError — Wave 1 이 findings→canned 변환 박제 |
| coach_hook_builder.py | `resolve_coach_hook_bundle` | NotImplementedError — Wave 1 이 per-report fallback 정책 박제 |

이 stub 들은 의도적이며, Wave 0 의 목적 자체(실패-우선 테스트 박제)에 부합한다. Wave 1 (Plan 11-01 Task 1) 이 GeminiCoachHookWriter + Firestore 전용 validator + pipeline wiring 과 함께 채운다. coach_comment/reviewed_by 는 v1 영구 None (v2 강사 콘솔 — 본 phase scope 밖, D-06).

## Threat Flags

None — 신규 보안 surface 0. CoachCommentHook 은 기존 trust boundary (LLM output → Firestore) 안에서 list[str]-only 게이트를 강화하며, threat_model T-11-01/T-11-02 의 mitigate disposition 을 test scaffold 로 미리 박제했다 (Wave 1 런타임 enforcement).
