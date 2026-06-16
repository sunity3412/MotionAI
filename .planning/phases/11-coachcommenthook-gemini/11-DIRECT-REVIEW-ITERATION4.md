---
phase: 11-coachcommenthook-gemini
reviewer: Codex
date: 2026-06-17
scope: direct-plan-review-iteration-4
status: revise-before-wave-0
basis:
  - .planning/phases/11-coachcommenthook-gemini/11-CONTEXT.md
  - .planning/phases/11-coachcommenthook-gemini/11-00-PLAN.md
  - .planning/phases/11-coachcommenthook-gemini/11-01-PLAN.md
  - .planning/phases/11-coachcommenthook-gemini/11-02-PLAN.md
  - .planning/phases/11-coachcommenthook-gemini/11-VALIDATION.md
  - .planning/phases/11-coachcommenthook-gemini/11-RESEARCH.md
  - .planning/phases/11-coachcommenthook-gemini/11-PATTERNS.md
  - backend/shared/python/sunity_shared/gemini/guardrails.py
---

# Phase 11 Direct Review — Iteration 4

## Verdict

3차 리뷰의 핵심 지적은 현재 계획에 대체로 반영됐다. `11-01-PLAN.md` 는 `build_coach_hooks -> CoachHookBundle | None`, pure `resolve_coach_hook_bundle`, all-digit hook guard, 양쪽 Pydantic schema `extra=forbid`, schema-strip config 재사용까지 반영했고, `11-VALIDATION.md` 도 ready/nyquist true 상태로 올라왔다.

하지만 Wave 0 을 바로 실행하기엔 아직 위험하다. 남은 문제는 core architecture 가 아니라 **Wave 0 테스트 스캐폴드와 canonical context 의 잔여 불일치**다. 이 상태로 시작하면 테스트가 오래된 fallback 의미를 박제하거나, Wave 1 에서 생길 심볼을 top-level import 해서 collection-green 계약을 깨뜨릴 수 있다.

## Findings

### HIGH 1 — Wave 0 fallback test scaffold still describes the old ownership model

**Evidence**

- `11-01-PLAN.md:131-144` 는 최신 설계를 명확히 한다. `GeminiCoachHookWriter.build_coach_hooks(...)` 는 parsed bundle 또는 `None` 만 반환하고, canned/per-report fallback 은 `resolve_coach_hook_bundle(...)` 가 소유한다.
- `11-VALIDATION.md:58-59` 도 같은 방향으로 수정됐다. api key fail 은 `build_coach_hooks -> None`, 그 뒤 `resolve_coach_hook_bundle` 가 canned 를 채운다.
- 그런데 Wave 0 계획의 test scaffold 설명은 아직 `hook writer ... None 반환 seam → build_canned_hook 반환 + 분석 status done assert` 라고 적는다(`11-00-PLAN.md:135`). 이 문장은 writer 또는 writer test 가 canned 를 직접 반환해야 하는 것처럼 읽힌다.

**Risk**

Wave 0 는 실패 테스트를 먼저 박는 단계라서, 여기서 잘못된 expectation 이 들어가면 이후 Wave 1 구현이 최신 설계와 테스트 사이에서 충돌한다. 구현자가 11-00 을 따라가면 writer 가 canned 를 만들거나, fallback test 가 pipeline/analysis status 까지 과하게 요구할 수 있다. 그러면 3차에서 분리한 책임 경계가 다시 무너진다.

**My fix**

`11-00-PLAN.md:135` 를 아래 의미로 다시 써야 한다.

- writer seam test: api_key_loader fail / 4xx / guard reject / retry exhausted → `build_coach_hooks(...) is None`.
- fallback policy test: `resolve_coach_hook_bundle(None|partial|full, ...)` → 항상 `(force_hook, body_hook)` 둘 다 non-None.
- "analysis status done" 은 Wave 1 Task 2 wiring 또는 integration-level assertion 으로 둔다. Wave 0/Task 1 pure helper test 가 Firestore/pipeline 완료 상태까지 주장하지 않게 한다.

나는 `test_coach_hook_fallback.py` 를 writer seam tests + pure resolver tests 로 나누고, 분석 완료 보장은 `test_coach_hook_nested_array.py` 또는 Task 2 summary gate 로 옮기겠다.

### HIGH 2 — Collection-green is under-specified for Wave-1-only symbols

**Evidence**

- Wave 0 는 `pytest tests/phase11 --co` collection green 을 hard gate 로 둔다(`11-00-PLAN.md:145`, `:148`).
- 같은 Wave 0 scaffold 는 아직 존재하지 않는 선택지 심볼을 테스트 대상으로 언급한다: `_enforce_no_hook_number_patterns` 또는 `forbid_measurement_units=True`(`11-00-PLAN.md:130`), `CoachHookBundle`/`CoachCommentHookPayload` extra=forbid drift(`11-VALIDATION.md:57`, `:71`), partial/full bundle resolver case(`11-00-PLAN.md:135`).
- 현재 실제 guardrails 함수에는 `forbid_measurement_units` 인자가 없고 `_enforce_no_hook_number_patterns` 도 없다(`backend/shared/python/sunity_shared/gemini/guardrails.py:47-52`).

**Risk**

테스트 파일이 새 심볼을 top-level import 하면 Wave 0 의 의도인 "collection green + behavior RED" 가 아니라 collection error 가 난다. 이건 이미 validation 이 막으려는 실패 형태와 정확히 반대다. 특히 `CoachHookBundle` 은 Wave 1 Task 1 에서 생기는 schema 라서, Wave 0 test 가 `from ...schemas import CoachHookBundle` 를 top-level 에 두면 바로 깨진다.

**My fix**

Wave 0 test 작성 규칙을 명시해야 한다.

- top-level import 는 현재 존재하는 모듈만 허용한다.
- future symbol 은 test body 안에서 `getattr(module, "Name", None)` 로 찾고, 없으면 `assert symbol is not None` 으로 RED 를 만든다. collection error 는 금지한다.
- `test_hook_guard_rejects_all_digits` 는 `_enforce_no_hook_number_patterns` 가 있으면 그것을 쓰고, 아니면 `_enforce_no_reject_patterns` 의 signature 에 `forbid_measurement_units` 가 생겼는지 런타임에 확인한다. 둘 다 없으면 assertion failure 로 RED.
- `test_bundle_extra_forbid` 는 `CoachHookBundle` / `CoachCommentHookPayload` import 를 test body 로 미루거나, Wave 1 Task 1 이후에만 GREEN 되는 assertion 으로 작성한다.
- `test_resolve_coach_hook_bundle` 의 partial/full bundle 입력은 schema class 가 없을 때 `types.SimpleNamespace` 또는 minimal duck object 로 표현할지, 아니면 schema 존재 assertion 후 RED 로 둘지 계획에 고정한다. 내 선호는 resolver 가 duck-type object/dict 를 받게 해서 `SimpleNamespace` 로 Wave 0 RED 를 만들고, Wave 1 에서 실제 Pydantic payload 도 같은 경로로 통과시키는 것이다.

### MEDIUM 1 — Canonical context still says degree/% guard, not all-digit guard

**Evidence**

- `11-CONTEXT.md:27-29` 는 D-04/D-05 correction 을 여전히 degree/% 중심으로 설명한다. `\d+...도/deg` 와 백분율을 추가한다고 되어 있고, bare `"3초"`, `"2회"`, `"15cm"`, `"180"` 같은 숫자 전면 금지는 없다.
- 반면 최신 실행 계획과 validation 은 hook text 의 모든 Arabic digit reject 로 바뀌었다(`11-01-PLAN.md:100`, `:124-127`, `11-VALIDATION.md:53`).
- `11-RESEARCH.md` / `11-PATTERNS.md` 상단 배너에는 iter-3 추가가 있지만, context 는 downstream agents 가 먼저 읽는 canonical decision 문서로 계속 참조된다.

**Risk**

실행자가 context 를 기준으로 구현하면 degree/% 만 막는 가드를 만들 수 있다. 그 경우 3차에서 막으려 한 `"3초"`, `"2회"` 류 numeric cue 가 다시 통과한다.

**My fix**

`11-CONTEXT.md` 에 iter-3 addendum 을 추가한다.

- D-04 correction: "hook prose number-free = 모든 Arabic digit(`\d`) reject" 로 명시.
- D-05 correction: 골든 finding test 도 degree/% 가 아니라 all-digit guard 를 포함한다고 명시.
- code_context 의 guardrails 재사용 설명도 "도 regex 추가"가 아니라 "hook-only all-digit guard 추가"로 맞춘다.

### MEDIUM 2 — Resolver payload boundary should avoid analysis→gemini schema coupling

**Evidence**

- `11-00-PLAN.md:124` 는 `coach_hook_builder.py` 가 `coach_hook.CoachCommentHook` 만 import 한다고 말한다.
- 최신 Wave 1 계획은 `resolve_coach_hook_bundle(...)` 가 `CoachCommentHookPayload -> CoachCommentHook` 변환을 수행한다고 적는다(`11-01-PLAN.md:141-143`).
- `CoachCommentHookPayload` / `CoachHookBundle` 은 `sunity_shared.gemini.schemas` 에 추가될 Pydantic adapter schema 다(`11-01-PLAN.md:129`).

**Risk**

구현자가 resolver 에서 `sunity_shared.gemini.schemas` 를 top-level import 하면 analysis layer 가 Gemini adapter schema 에 의존한다. 이건 pure helper 의 의미를 약하게 만들고, Wave 0 collection-green 문제도 다시 키운다. 지금 계획은 "pure / I/O 없음"은 말하지만 "gemini schema import 금지"는 명확히 말하지 않는다.

**My fix**

`coach_hook_builder.py` 는 Gemini Pydantic class 를 import 하지 않고 duck type 으로 변환하게 한다.

- `bundle` 타입은 `object | dict | None` 정도로 받고, attribute access 와 dict access 를 모두 지원한다.
- payload 변환은 `_payload_to_hook(payload: object | dict, *, source_report: str)` 내부에서 `auto_findings_summary` / `open_questions_for_coach` / `suggested_cues` 를 읽어 `CoachCommentHook` 으로 만든다.
- acceptance 에 `grep -c "sunity_shared.gemini.schemas" backend/shared/python/sunity_shared/analysis/coach_hook_builder.py -> 0` 또는 AST import check 를 추가한다.

### LOW 1 — Some acceptance checks are still grep-shaped where behavior checks would be cleaner

**Evidence**

- `11-01-PLAN.md:151` 는 writer 파일에 `build_canned_hook|resolve_coach_hook_bundle` 문자열이 0 이어야 한다고 한다. 주석이나 docstring 에서도 false positive 가 날 수 있다.
- `11-01-PLAN.md:153` 는 `extra="forbid"` grep count 가 기존 대비 2 증가해야 한다고 한다. 기존 schema 파일의 다른 변경과 섞이면 약하다.

**Risk**

실제 동작은 맞는데 문자열 때문에 실패하거나, 문자열은 맞는데 import/call 구조가 틀린 상태를 놓칠 수 있다.

**My fix**

grep 은 보조로 두고, AST/behavior 테스트로 승격한다.

- writer module AST 에서 `build_canned_hook` / `resolve_coach_hook_bundle` import 또는 call 이 없는지 검사.
- Pydantic drift 는 이미 `model_validate(..., "unexpected") -> ValidationError` behavior test 로 충분하다. grep count 는 제거하거나 secondary evidence 로 낮춘다.

## Resolved Since Iteration 3

- 3차 HIGH-1: fallback ownership split 은 `11-01-PLAN.md:69`, `:131-144`, `11-VALIDATION.md:58-59` 에 반영됐다.
- 3차 HIGH-2: hook guard all-digit reject 는 `11-01-PLAN.md:100`, `:124-127`, `11-VALIDATION.md:53` 에 반영됐다.
- 3차 MEDIUM-1: `CoachCommentHookPayload` 와 `CoachHookBundle` 양쪽 `extra=forbid` 및 drift test 가 `11-01-PLAN.md:129`, `11-VALIDATION.md:57` 에 들어갔다.
- 3차 MEDIUM-2: validation frontmatter 는 `status: ready`, `nyquist_compliant: true`, `revised: 2026-06-17` 로 정리됐다(`11-VALIDATION.md:1-8`).

## Go / No-Go

**No-go for Wave 0 until HIGH 1 and HIGH 2 are fixed.**  
Wave 1 core design 은 이제 큰 방향이 맞다. 하지만 Wave 0 가 실패 테스트를 박제하는 단계라, 스캐폴드의 의미와 collection-green 규칙을 먼저 정리해야 한다. HIGH 1/2 수정 후에는 Phase 11 계획은 conditional pass 로 볼 수 있다.
