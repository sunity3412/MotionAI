---
phase: 11-coachcommenthook-gemini
reviewer: Codex
date: 2026-06-16
scope: direct-plan-review-iteration-3
status: revise-before-execution
basis:
  - .planning/phases/11-coachcommenthook-gemini/11-CONTEXT.md
  - .planning/phases/11-coachcommenthook-gemini/11-00-PLAN.md
  - .planning/phases/11-coachcommenthook-gemini/11-01-PLAN.md
  - .planning/phases/11-coachcommenthook-gemini/11-02-PLAN.md
  - .planning/phases/11-coachcommenthook-gemini/11-VALIDATION.md
  - .planning/phases/11-coachcommenthook-gemini/11-RESEARCH.md
  - .planning/phases/11-coachcommenthook-gemini/11-PATTERNS.md
  - .planning/ROADMAP.md
---

# Phase 11 Direct Review — Iteration 3

## Verdict

2차 리뷰의 핵심 블로커는 계획상 대부분 반영됐다. 특히 별도 text-only `GeminiCoachHookWriter`, hook-scoped degree/% guard, `_strip_unsupported_schema_keys` config 재사용, 전용 `_validate_coach_comment_hook`, per-report fallback, UI concat 병합은 현재 계획에 들어와 있다.

다만 바로 실행하기엔 아직 두 가지 HIGH 리스크가 남아 있다. 하나는 fallback/resolution 책임과 테스트 gate 의 소유권이 문서 안에서 충돌하는 점이고, 다른 하나는 "number-free" 요구가 실제 hook guard/test 에서는 degree/% 중심으로 좁게 구현될 수 있는 점이다. 나는 이 두 가지를 고친 뒤 Wave 0/1 실행을 시작하겠다.

## Findings

### HIGH 1 — Fallback/resolution ownership is internally inconsistent

**Evidence**

- `11-01-PLAN.md:95-96` 는 api_key_loader 실패/None 반환/partial bundle 에 대해 `build_canned_hook` 반환 및 두 리포트 모두 hook 부착을 Task 1 behavior 로 둔다.
- 같은 계획의 `11-01-PLAN.md:120-123` 은 `GeminiCoachHookWriter.build_coach_hooks(...) -> CoachHookBundle | None` 이며 키 실패 시 `None` 을 반환한다고 정의한다.
- 또 `11-01-PLAN.md:128` 은 per-report resolution 을 Task 2 pipeline caller 가 수행한다고 못박는다.
- 그런데 Task 1 acceptance 는 `test_coach_hook_fallback.py` 전체 PASS 를 요구한다(`11-01-PLAN.md:130-131`), 반면 partial bundle 을 실제 report dataclass 에 붙이는 구현은 Task 2 에 있다(`11-01-PLAN.md:189-194`, `:206`).

**Risk**

실행자가 이 상태로 들어가면 두 갈래로 흔들릴 가능성이 높다.

- writer 가 canned hook 까지 반환하게 만들면 `CoachHookBundle | None` 경계가 깨지고 writer/pipeline 책임이 섞인다.
- writer 는 `None` 만 반환하게 두면 Task 1 의 fallback test 전체 PASS 조건이 과도해져, 테스트를 약하게 만들거나 Task 2 범위를 Task 1 로 끌어올 수 있다.

**My fix**

나는 책임을 이렇게 자르겠다.

1. `GeminiCoachHookWriter` 는 순수하게 `CoachHookBundle | None` 만 반환한다. api key fail, 4xx, guard reject 는 모두 `None`.
2. `coach_hook_builder.py` 에 pure helper 를 하나 추가한다. 예: `resolve_coach_hook_bundle(bundle, *, force_findings, body_findings) -> tuple[CoachCommentHook, CoachCommentHook]`.
3. partial/None bundle fallback test 는 이 pure helper 를 대상으로 둔다. 그러면 Task 1 에서 fallback semantics 를 GREEN 으로 만들 수 있고, Task 2 는 그 결과를 `dataclasses.replace(...)` 로 붙이는 wiring 만 책임진다.
4. 만약 helper 를 추가하지 않을 거라면, Task 1 acceptance 에서 `test_partial_bundle_per_report` 를 제외하고 Task 2 acceptance 로만 옮긴다.

내 선호는 2번이다. fallback 정책은 pipeline I/O 보다 pure function 으로 박는 편이 테스트가 싸고, Firestore/analysis path 와도 분리된다.

### HIGH 2 — "Number-free" lock is broader than the planned guard/test

**Evidence**

- `11-CONTEXT.md:27-29` 는 hook prose 를 number-free 로 잠그고, Gemini 가 새 수치/좌표/점수/판정을 만들면 안 된다고 한다.
- 하지만 Wave 1 behavior 는 금지 패턴을 "점수/좌표/판정/도/%" 중심으로 정의한다(`11-01-PLAN.md:88-93`, `:126-138`).
- 현재 공용 guard 는 `\d+점`, `\d+/\d+`, 좌표, 판단 어휘만 막는다(`backend/shared/python/sunity_shared/gemini/guardrails.py:26-44`, `:47-52`). 여기에 degree/% 만 hook-scoped 로 더해도 `"3초"`, `"2회"`, `"15cm"`, `"180"` 같은 bare/measurement 숫자는 통과한다.

**Risk**

Gemini 가 "3초 더 버티기", "2회 반복", "15cm 정도" 같은 숫자 cue 를 만들면 D-04 의 "LLM 이 새 수치를 만들지 않는다"를 위반하지만 test/guard 는 놓친다. 이건 사용자가 보는 `openQuestionsForCoach` 에도 들어갈 수 있어 신뢰 리스크가 크다.

**My fix**

hook 전용 guard 는 degree/% 만이 아니라 hook text value 전체에서 Arabic digit 을 reject 하도록 만든다.

- 예: `_enforce_no_hook_number_patterns(text, *, context="coach_hook")` 가 `\d` 를 잡는다.
- 글로벌 `_enforce_no_reject_patterns` 는 그대로 둔다. scene_finder/reference_extractor 의 "30도"/"50%" 회귀는 현재 계획처럼 별도 테스트로 보호한다.
- test fixture 에 `"3초"`, `"2회"`, `"15cm"`, `"180"` 을 추가한다. 기존 `"23도"`, `"23°"`, `"15%"` 는 유지한다.
- 정말 엔진 숫자를 hook 에 복사해야 한다면 그때는 "source-tagged engine number only" 같은 별도 화이트리스트를 설계해야 한다. 현재 locked design 은 number-free 이므로 전부 reject 가 맞다.

### MEDIUM 1 — `CoachHookBundle` report-level `extra="forbid"` is not explicit

**Evidence**

- 현재 소스의 Gemini schema precedent 는 `CoachPayload` 같은 top-level model 에 `model_config = ConfigDict(extra="forbid")` 를 둔다(`backend/shared/python/sunity_shared/gemini/schemas.py:121-124`).
- Phase 11 계획은 `CoachCommentHookPayload` 와 `CoachHookBundle` 생성을 말하지만, `CoachHookBundle` 자체에도 `extra="forbid"` 를 둔다고 명시하지 않는다(`11-01-PLAN.md:118`).

**Risk**

Pydantic 기본값이 extra ignore 로 남으면 Gemini 가 typo/top-level stray key 를 내도 조용히 버려진다. 예를 들어 `bodyComparison` 같은 잘못된 키가 무시되고 body fallback 으로 보정되면 분석은 성공하지만 live schema drift 를 조기에 잡지 못한다.

**My fix**

두 Pydantic 모델 모두에 명시적으로 둔다.

```python
model_config = ConfigDict(extra="forbid")
```

그리고 `CoachHookBundle.model_validate({"force_pattern_inference": ..., "unexpected": ...})` 가 ValidationError 를 내는 단위테스트를 추가한다. Firestore validator 의 unknown-key reject 와 별개로, LLM response boundary 에서도 schema drift 를 잡아야 한다.

### MEDIUM 2 — Validation contract metadata still says draft / non-compliant

**Evidence**

- `11-VALIDATION.md:4-6` 은 `status: draft`, `nyquist_compliant: false`, `wave_0_complete: false` 로 남아 있다.
- 본문은 이미 iter-2 수정사항을 반영해 dedicated validator, hook-scoped degree/% guard, schema-strip config, partial fallback 을 테스트 항목으로 잡고 있다(`11-VALIDATION.md:13-16`, `:42-59`, `:65-72`).

**Risk**

사람은 본문을 보고 충분하다고 판단할 수 있지만, 자동 workflow 나 다음 실행자가 frontmatter 를 gate 로 쓰면 "아직 validation 미준수" 상태로 해석될 수 있다. 반대로 본문과 metadata 가 불일치하면 실행 전 품질 기준이 애매해진다.

**My fix**

HIGH 1/HIGH 2 를 반영한 뒤, validation frontmatter 와 sign-off 를 실제 상태에 맞춘다.

- 계획 검증 계약이 완성된 상태라면 `status: ready`, `nyquist_compliant: true`.
- Wave 0 이 아직 생성 전이면 `wave_0_complete: false` 는 유지.
- Sign-off checklist 에 "fallback ownership split resolved" 와 "bare numeric hook guard covered" 를 추가한다.

### LOW 1 — Guardrail acceptance still relies on brittle grep

**Evidence**

- `11-01-PLAN.md:137` 는 `grep -nE "°|도|deg" guardrails.py` 결과가 tuple 밖에만 있어야 한다는 식의 textual check 를 둔다.
- 같은 계획에 이미 behavior-level tests 가 있다(`11-01-PLAN.md:89-91`, `:137-138`).

**Risk**

comment/docstring 의 "도" 같은 문자열 때문에 grep 결과 해석이 사람 의존이 된다. 이후 helper 이름이나 주석이 바뀌어도 false positive/false negative 가 난다.

**My fix**

grep 은 보조 확인으로 낮추고, acceptance 는 runtime behavior 로 고정한다.

- default guard: `"등이 30도 이상 후굴"`, `"신체의 50% 이상 가려짐"` PASS.
- hook guard: `"23도"`, `"23°"`, `"23 deg"`, `"15%"`, 그리고 HIGH 2 의 bare numeric cases FAIL.
- 필요하면 `_SCORE_PATTERNS` pattern strings 를 import 해서 degree/% regex 가 없음을 assert 하는 단위테스트를 둔다. grep 으로 최종 판정을 하지 않는다.

## Resolved Since Iteration 2

- `ROADMAP.md` 의 fallback criterion 은 Gemini hook-writer/api_key_loader seam 으로 교정됐다(`.planning/ROADMAP.md:336`).
- stale RESEARCH/PATTERNS 는 상단 override banner 로 잠금 설계를 명시했다(`11-RESEARCH.md:7-20`, `11-PATTERNS.md:9-21`).
- `11-01-PLAN.md` 는 별도 text-only writer, Vision writer 무수정, schema-strip config 재사용, retry, hook-scoped degree/% guard, 전용 validator, partial fallback 을 포함한다(`11-01-PLAN.md:55-64`, `:112-128`, `:177-194`).
- `11-02-PLAN.md` 는 두 리포트 질문을 concat/trim/dedupe/slice 로 병합하도록 수정되어 first-non-null `??` 누락 리스크를 해소했다(`11-02-PLAN.md:32-36`, `:70-79`).

## Go / No-Go

**No-go for Wave 1 execution until HIGH 1 and HIGH 2 are fixed in the plan/test contract.**  
그 두 가지가 반영되면 나머지는 execution-time 확인 가능한 MEDIUM/LOW 로 내려간다. 특히 dedicated Firestore validator 와 schema-strip config 는 현재 계획 방향이 맞다.
