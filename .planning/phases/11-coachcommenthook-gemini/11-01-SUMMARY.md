---
phase: 11-coachcommenthook-gemini
plan: 01
subsystem: backend-coach-hook
tags: [coach-hook, gemini, text-only-writer, number-free-guard, firestore-validator, pipeline-wiring]
requires:
  - CoachCommentHook (Phase 11 Wave 0, 11-00)
  - coach_hook_builder stubs (11-00)
  - gemini.guardrails._enforce_no_reject_patterns (Phase 17)
  - gemini.client._strip_unsupported_schema_keys (Phase 17)
  - ForcePatternInference (Phase 9) / BodyComparisonReport (Phase 7)
provides:
  - GeminiCoachHookWriter (text-only, bundle|None only)
  - CoachHookBundle + CoachCommentHookPayload (둘 다 extra=forbid)
  - guardrails._enforce_no_hook_number_patterns + forbid_measurement_units flag
  - coach_hook_builder.build_canned_hook (구현)
  - coach_hook_builder.resolve_coach_hook_bundle (pure helper, per-report 폴백 소유)
  - firestore_admin._validate_coach_comment_hook (force scoped + body precheck)
  - ForcePatternInference.coach_comment_hook / BodyComparisonReport.coach_comment_hook 필드
  - pipeline single-call hook wiring (post-force-pattern / pre-complete window)
affects:
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/firestore_admin.py
tech-stack:
  added: []
  patterns:
    - "text-only Gemini writer (영상 입력 seam 없음) — Vision GeminiCoachWriter 무수정 (BLOCKER-1)"
    - "hook-scoped number-free 가드 (모든 \\d reject, 글로벌 가드 미오염 — iter-2 BLOCKER-2)"
    - "schema-strip config 재사용 (CoachHookBundle nested $defs inline — iter-2 HIGH-1)"
    - "duck-type resolver (analysis layer → gemini.schemas 비결합 — iter-4 MEDIUM-2)"
    - "scoped Firestore validator (force 브랜치 + body precheck — generic 위임 금지)"
key-files:
  created:
    - backend/shared/python/sunity_shared/gemini/coach_hook_writer.py
  modified:
    - backend/shared/python/sunity_shared/gemini/schemas.py
    - backend/shared/python/sunity_shared/gemini/guardrails.py
    - backend/shared/python/sunity_shared/analysis/coach_hook_builder.py
    - backend/shared/python/sunity_shared/analysis/force_pattern.py
    - backend/shared/python/sunity_shared/analysis/body_normalizer.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/functions/pipeline/app.py
decisions:
  - "writer 는 bundle|None 만 반환 (canned 미생성) — per-report 폴백은 pure resolve_coach_hook_bundle 단독 소유 (iter-3 HIGH-1)"
  - "hook-scoped number-free 가드는 글로벌 tuple 밖 별도 helper/flag — scene_finder/reference_extractor '30도'/'50%' 비회귀 (iter-2 BLOCKER-2)"
  - "CoachHookBundle/CoachCommentHookPayload 둘 다 extra=forbid + camelCase alias (Gemini JSON ↔ TS contract)"
  - "_validate_coach_comment_hook 전용 화이트리스트 — generic _validate_flat_dict_no_nested_array 위임 0 (list[dict] reject)"
  - "pipeline hook wiring = lazy import (Lambda 250MB 한도 정합)"
metrics:
  duration: ~40m
  completed: 2026-06-17
  tasks: 2
  files: 8
---

# Phase 11 Plan 01: text-only CoachCommentHook writer + pipeline wiring Summary

신규 text-only `GeminiCoachHookWriter` 가 1회 분석당 hook 1회 호출로 두 리포트의 `CoachCommentHook` 텍스트를 함께 산출하고, pure helper `resolve_coach_hook_bundle` 가 per-report 폴백을 소유하며, hook-scoped number-free 가드 + 전용 Firestore validator (`_validate_coach_comment_hook`) 로 list[str]-only 게이트를 통과시켜 Wave 0 의 28 RED 테스트를 GREEN 으로 전환했다 (5 regression-guard PASS 유지).

## What Was Built

### Task 1 — text-only writer + schema + number-free 가드 + canned/resolve builder (commit 98cd890)

- **`coach_hook_writer.py` (신규):** `GeminiCoachHookWriter.build_coach_hooks(*, force_findings, body_findings) -> CoachHookBundle | None`. `resolve_model("B")` + `_strip_unsupported_schema_keys(CoachHookBundle.model_json_schema())` config 재사용 (iter-2 HIGH-1) + text-only `client.models.generate_content` (영상 입력 경로 미접촉) + `_enforce_no_reject_patterns(raw, context="coach_hook", forbid_measurement_units=True)` 가드 → reject 시 None (reject-and-fallback, sanitize 없음, D-05) + 4xx 즉시 None / 5xx 1회 retry / ValidationError·JSONDecodeError 1회 retry. **canned 미생성** (iter-3 HIGH-1). client 주입 seam (`client=`) 로 외부 네트워크 0 테스트. `_client` 필드 검사 0 (WARNING-2 — fallback seam = api_key_loader/None-return).
- **`schemas.py`:** `CoachCommentHookPayload` (auto_findings_summary / open_questions_for_coach: list[str] / suggested_cues: list[str]) + `CoachHookBundle` (두 optional report hook). **둘 다 `ConfigDict(extra="forbid")`** + camelCase alias (`to_camel` + `populate_by_name=True`) — Gemini JSON ↔ TS contract.
- **`guardrails.py`:** `_enforce_no_hook_number_patterns` (모든 Arabic digit `\d` reject) + `_enforce_no_reject_patterns` 에 `forbid_measurement_units` 파라미터 추가 (True 일 때만 hook-scoped \d 게이트 적용). 글로벌 `_SCORE_PATTERNS`/`_COORDINATE_PATTERNS`/`_JUDGMENT_PATTERNS` tuple **무수정** — "30도"/"50%" 기본 가드 PASS (iter-2 BLOCKER-2).
- **`coach_hook_builder.py`:** `build_canned_hook` 구현 (finding interpretation/recommendation 텍스트만 조합 — number-free, 점수/판정 어휘 0) + `resolve_coach_hook_bundle` pure helper (bundle None/partial/full → 항상 양쪽 non-None CoachCommentHook, duck-type — `gemini.schemas` import 0, iter-4 MEDIUM-2). degenerate payload 도 canned default 로 보강해 dataclass 경계 raise 0.

### Task 2 — 전용 validator + dataclass 필드 + pipeline wiring (commit 52b3b9b)

- **`firestore_admin.py`:** `_validate_coach_comment_hook(payload, *, path)` 전용 strict 화이트리스트 (scalar 키 4 / list[str] 키 2 / unknown-key reject / list[dict]·list[list]·tuple reject) — generic `_validate_flat_dict_no_nested_array` 위임 0 (iter-2 BLOCKER-1). `_validate_force_pattern_inference` 의 nested-dict reject 브랜치 **위에** `coachCommentHook` 전용 브랜치 추가 + `complete_analysis` 의 `body_comparison_report` 블록에 hook precheck (generic 단독 우회 차단).
- **`force_pattern.py` / `body_normalizer.py`:** `coach_comment_hook: CoachCommentHook | None = None` 필드 (모든 default 뒤 맨 끝, D-02 field-order). `coach_hook` import (순환 안전 — HIGH-3).
- **`pipeline/app.py`:** force_pattern_inference 생성 + high-score gate 직후, complete_analysis 직전 window 에서 **single call** `GeminiCoachHookWriter().build_coach_hooks(...)` (lazy import) → `resolve_coach_hook_bundle(bundle, ...)` → `dataclasses.replace` 양 dataclass → hook 부착 후 두 dict 재변환. `coach_details`(joint writer) 무오염 — `coach_hooks` 별도 변수 (BLOCKER-3). 폴백 정책 미보유 — helper tuple 소비만 (iter-3 HIGH-1).

## Verification Results

- `pytest tests/phase11 -q` — **33 passed** (28 formerly-RED → GREEN, 5 regression-guard 유지).
- `pytest tests/phase07 tests/phase09 tests/phase11 -q` — 267 passed.
- `pytest tests/gemini -q` — 111 passed (Vision writer + scene_finder/reference_extractor 가드 비회귀).
- Vision writer 무수정: `git diff --stat 1deee48 -- coach_writer_v2.py` → 0 줄 (BLOCKER-1).
- 신규 writer 영상 미접촉: `grep -cE "GeminiVisionCall|files.upload|videoPath|video_path|active_file" coach_hook_writer.py` → 0. `_client` → 0. `gemini-3` 하드코딩 → 0.
- builder gemini.schemas import: AST import-check → 0 (docstring 언급 1건은 false-positive, iter-4 MEDIUM-2).
- writer build_canned_hook/resolve Call·Import: AST → 0 (docstring 1건 false-positive, iter-4 LOW-1 = AST 우선).
- schema-strip config: `_strip_unsupported_schema_keys(CoachHookBundle.model_json_schema())` 결과에 `$defs`/`additionalProperties`/`discriminator` → 0.
- 글로벌 가드 비회귀: `_enforce_no_reject_patterns('등이 30도 이상 후굴', context='scene_finder')` / "50%" → 예외 0 (PASS). hook 가드: "3초"/"180"/"15cm"/"23도"/"15%" → ValueError.
- **hook wiring 줄번호 (BLOCKER-2):** force_pattern_inference 생성 = 2102, `build_coach_hooks` 호출 = 2135, `resolve_coach_hook_bundle` = 2139, `complete_analysis` = 2327 → 2102 < 2135 < 2327 (post-force-pattern / pre-complete window 충족).
- **single call:** `grep -c ".build_coach_hooks(" app.py` → 1 (분석 path 당 1회, report 당 별도 invoke 0).
- coach_details 무오염: hook 키 주입 0 (comment 언급 1건만).
- 순환 import: `force_pattern + body_normalizer + coach_hook + coach_hook_builder` 동시 import 통과 + `ForcePatternInference.coach_comment_hook` default None.

## Deviations from Plan

None - plan executed exactly as written.

설계 명세상 옵션 A(`_enforce_no_hook_number_patterns`)와 옵션 B(`forbid_measurement_units` flag) 둘 다 구현했다 — action L124-127 이 둘 중 하나를 요구했으나 Wave 0 테스트가 둘 다 probe 하므로(translation-only test L77-92) 양쪽 seam 을 제공하는 것이 명세 준수다 (별도 deviation 아님).

## TDD Gate Compliance

본 plan 의 RED 게이트(test 파일)는 Wave 0 (11-00) 에서 collection-green + intentional-RED 로 이미 commit 됨 (test commit 선행). 본 plan 의 두 commit 은 GREEN 전환 `feat` 이다 (RED→GREEN 시퀀스 충족 — RED 는 Wave 0 소유).

## Known Stubs

None — Wave 0 의 `build_canned_hook` / `resolve_coach_hook_bundle` NotImplementedError stub 을 본 plan 이 구현으로 교체했다. v2 강사 콘솔 필드(coach_comment / reviewed_by)는 v1 영구 None (D-06 — Phase 11 scope 밖, stub 아님).

## Threat Flags

None — 신규 보안 surface 0. T-11-02(LLM 수치/판정 mint) → number-free 가드 reject-and-fallback, T-11-03(malformed hook) → _validate_coach_comment_hook list[dict] reject, T-11-06(joint-card 집계 오염) → coach_hooks 별도 변수, T-11-07(partial bundle) → resolve_coach_hook_bundle, T-11-08(schema drift) → extra=forbid 모두 런타임 enforcement 로 mitigate disposition 충족.

## Self-Check: PASSED

- created file `backend/shared/python/sunity_shared/gemini/coach_hook_writer.py`: FOUND.
- commit 98cd890 (Task 1): FOUND in git log.
- commit 52b3b9b (Task 2): FOUND in git log.
- phase11 게이트: 33 passed (RED→GREEN + guards 유지).
