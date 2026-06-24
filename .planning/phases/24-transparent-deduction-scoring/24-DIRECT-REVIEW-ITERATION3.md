# Phase 24 Direct Review - Iteration 3

**Reviewer:** Codex direct self-review, no external skill/subagent  
**Reviewed at:** 2026-06-24  
**Scope:** Post-iteration-2 patched `24-01-PLAN.md`, `24-02-PLAN.md`, `24-03-PLAN.md`, `24-PATTERNS.md`, `24-VALIDATION.md`, and the current pipeline/app.py seams referenced by those plans.

## Verdict

2차 리뷰의 HIGH 항목들은 대부분 문서상 반영됐다. `criteria_for_fault(...)`, insufficient-reach sign, `baselineValue`/`baselineKind`, artifact-gated generalization, line/leg no-double-count, structural generalization은 이제 계획에 들어와 있다.

남은 리스크는 새 설계 자체보다 "반영된 설계를 실제 seam에서 실행할 수 있는가"다. 특히 Gemini-silent path와 context apply path가 아직 계획 문장끼리 충돌한다. 내가 실행한다면 아래 HIGH 항목은 코드 작성 전에 다시 패치한다.

## Findings

### HIGH-1: Gemini-silent measured deduction 요구와 `supported_differences` 기반 activation이 충돌한다

Plan 01의 must-have는 Gemini가 fault를 짚지 않아도 measured dimension/kismam deviation이 점수에 반영되어야 한다고 못 박는다(`24-01-PLAN.md:17-20`). 테스트도 `test_gemini_silent_not_100`을 요구한다(`24-01-PLAN.md:197`, `24-01-PLAN.md:272`). 그런데 tally action은 criterion activation을 `fault_context`의 `supported_difference / FaultKey`를 순회해서만 만든다(`24-01-PLAN.md:217`). Gemini-silent면 supported differences가 비어 있으므로 activated set이 비고, 이후 "For each ACTIVATED criterion" 루프가 돌지 않는다.

**Risk:** 가장 중요한 Phase 20 보존 케이스가 문서대로 구현하면 `records=()`, `final=100`으로 끝난다. `dimension_overall`은 unavailable fallback에서만 record로 쓰이고(`24-01-PLAN.md:216`), quantification이 available인 Gemini-silent 경로에서는 자동으로 final에 반영되지 않는다.

**How I would handle it:** activation source를 둘로 나눈다.

```python
activated = criteria_from_measured_deviations(measured_deviations)
activated |= criteria_from_gemini_supported_differences(fault_context, measured_deviations)
```

- `criteria_from_measured_deviations`는 finite/nonzero measured substrate가 있는 measurable criteria를 seed한다. 이게 Gemini-silent 방어다.
- `criteria_for_fault(...)`는 Gemini가 짚은 fault를 라우팅하거나 coverage gap을 남기는 역할로 둔다.
- `gemini_silent` 테스트는 `supported_differences=[]` 상태에서 measured leg deviation만으로 `leg_extension` record가 생기는지 확인해야 한다.
- line/leg no-double-count는 이 seed 단계 뒤에 적용한다.

### HIGH-2: `_build_deduction_measured_deviations(...)`를 호출하라는 위치에 필요한 인자가 없다

Plan 02는 helper를 `_build_deduction_measured_deviations(*, angles, profile, assessments, dimension_scores, quantification)`로 정의한다(`24-02-PLAN.md:156-160`). 그런데 같은 Plan 02는 `_apply_vision_veto`와 `_apply_vision_veto_from_context` 안에서 이 helper를 만들고 tally를 호출하라고 한다(`24-02-PLAN.md:165`).

현재 `_apply_vision_veto`는 `angles`와 `profile`은 받지만 `assessments`는 받지 않는다(`backend/functions/pipeline/app.py:1971-1981`). 더 큰 문제는 context path인 `_apply_vision_veto_from_context(score_result, ctx, quantification)`가 `angles`, `profile`, `assessments`를 전혀 받지 않는다는 점이다(`backend/functions/pipeline/app.py:2088`). 현재 `_process` seam에는 이 값들이 모두 있다(`backend/functions/pipeline/app.py:3091-3107`, `3130-3139`).

**Risk:** 구현자가 Plan 02 문장을 그대로 따르면 context path에서 NameError가 나거나, 급히 `score_result`/`dimensionScores`만으로 substrate를 재구성하면서 HIGH-3의 "score-not-deviation" 문제가 재발한다.

**How I would handle it:** substrate는 `_process` seam에서 한 번 만든 뒤 apply path로 넘긴다.

```python
measured_deviations = _build_deduction_measured_deviations(
    angles=angles,
    profile=profile,
    assessments=assessments,
    dimension_scores=dimension_scores,
    quantification=quantification,
)
result = _apply_vision_veto(..., measured_deviations=measured_deviations, baseline_kind=baseline_kind)
```

그리고 `_apply_vision_veto_from_context(...)`는 `measured_deviations`를 필수 keyword로 받게 한다. context path 테스트는 helper가 apply 내부에서 profile을 찾지 않고, seam에서 만들어진 named substrate를 그대로 쓰는지 확인해야 한다.

### HIGH-3: Mode3 breakdown 기대가 문서끼리 충돌한다

Plan 03은 "Mode3 deductionBreakdown is NOT silently expected"라고 정리했다(`24-03-PLAN.md:23`). Plan 02 Task 2도 `mode3_held`는 early passthrough이며 Mode3에 reference-anchored tally를 넣지 않는다고 한다(`24-02-PLAN.md:165`). 그런데 Plan 02 Task 4는 `test_pipeline_mode3.py`를 "overallScore=deductionBreakdown.final" assert로 전환하라고 쓴다(`24-02-PLAN.md:237`, `24-02-PLAN.md:263`).

**Risk:** 테스트 작성자가 Mode3에도 `deductionBreakdown`이 있어야 한다고 구현하거나, 반대로 구현은 passthrough인데 테스트가 실패한다. 이는 Phase 24 scope를 Mode1 tally에서 Mode3 session-delta redesign으로 넓혀버릴 수 있다.

**How I would handle it:** `overallScore == deductionBreakdown.final`은 Mode1 tally-applied path에만 적용한다. Mode3 tests는 다음을 확인한다.

- `visionVeto.status == "mode3_held"`
- `deductionBreakdown` 없음 또는 legacy-compatible absent
- `tallyFinal` 없음
- `_apply_score_suppression`은 기존처럼 실행

Mode3용 transparent breakdown은 별도 follow-up으로 둔다.

### MEDIUM-1: "severity가 criterion을 locate한다"는 표현이 새 router와 모순된다

Plan 01은 "Gemini severity LOCATES which criterion"이라고 쓴다(`24-01-PLAN.md:20`). Plan 02의 docstring migration도 severity를 "criterion pointer"로 설명하라고 한다(`24-02-PLAN.md:118`). 동시에 새 router의 핵심 invariant는 `criteria_for_fault`가 severity를 절대 읽지 않는다는 것이다(`24-01-PLAN.md:155`, `24-01-PLAN.md:207`).

**Risk:** 코드 테스트는 severity-invariant를 요구하는데, docstring과 threat model은 severity가 selection 의미를 가진 것처럼 남는다. 다음 구현자가 `severity != none`을 activation 조건으로 착각할 수 있다.

**How I would handle it:** 표현을 모두 "Gemini supported_difference / fault label locates criterion"으로 바꾼다. `severity`는 score/selection이 아니라 `coachRootCauseEligible`의 보조 신호로만 둔다.

### MEDIUM-2: record field optionality가 gate strictness와 맞지 않는다

TS contract는 `baselineKind?: ...`와 `ipsfAnchor?: string`으로 둔다(`24-01-PLAN.md:133`). 하지만 Python contract는 `DEDUCTION_RECORD_KEYS`에 `baselineKind`를 포함하고(`24-01-PLAN.md:131`), traceability gate는 모든 record에 `ipsfAnchor`와 numeric `baselineValue`가 있어야 한다고 한다(`24-03-PLAN.md:18`, `24-03-PLAN.md:92`). Test도 record keys가 `DEDUCTION_RECORD_KEYS`와 같아야 한다고 요구한다(`24-01-PLAN.md:280-281`).

**Risk:** backend는 `baselineKind=None` key를 항상 내보내는데 TS는 omitted도 허용한다. `ipsfAnchor`도 게이트는 required인데 타입은 optional이라 contract drift가 생긴다.

**How I would handle it:** legacy compatibility는 `deductionBreakdown?` 자체에만 둔다. 새 record 내부는 strict하게 한다.

- `baselineKind: 'floor' | 'pole_vertical' | 'hip_line' | null`
- `ipsfAnchor: string`
- `coverageGaps`/`fallback`은 optional이어도 무방하지만, `records` 안의 traceability fields는 required

### MEDIUM-3: coverage gap audit가 "왜 gap인지"는 말하지만 "어떤 evidence인지"가 약하다

현재 TS shape는 `coverageGaps?: { faultType: string; reason: string }[]`다(`24-01-PLAN.md:133`). 그런데 router는 `supported_difference.body_part/fault_state`를 읽어 gap을 판단한다(`24-01-PLAN.md:147-155`). gap entry가 `faultType`/`reason`만 가지면 "그립 gap"은 남지만 어떤 Gemini evidence가 그 gap을 만들었는지 record-level trace가 약하다.

**Risk:** belle 검증에서 "보이는데 0감점"이 나왔을 때 coverage gap은 보이지만, 어떤 `body_part`/`fault_state`가 deferred로 빠졌는지 바로 확인하기 어렵다. flat dict 제약을 지키면서도 더 잘 남길 수 있다.

**How I would handle it:** coverage gap도 flat scalar provenance를 가진다.

```ts
coverageGaps?: {
  faultType: string;
  reason: string;
  bodyPart?: string;
  faultState?: string;
  keypointSet?: string;
  ruleId?: string;
}[]
```

Firestore nested-array 금지는 그대로 지키고, Pod checkpoint에서 gap triage가 쉬워진다.

## Recommended Patch Order

1. Plan 01 Task 2에 `criteria_from_measured_deviations(...)` seed 단계를 추가해서 Gemini-silent measured deduction이 실제로 가능하게 한다.
2. Plan 02에서 `_build_deduction_measured_deviations(...)` 생성 위치를 `_process` seam으로 옮기고, `measured_deviations`를 apply/context path로 thread한다.
3. Mode3 테스트 기대를 "deductionBreakdown absent + mode3_held + suppression preserved"로 정리한다.
4. "severity locates criterion" 표현을 전부 "supported_difference locates criterion"으로 바꾼다.
5. `DeductionRecord` TS optionality를 backend/gate strictness와 맞춘다.
6. coverage gap entry에 flat provenance fields를 추가한다.

## Bottom Line

3차 기준으로 Phase 24 계획은 거의 구현 가능한 수준까지 왔다. 다만 지금 상태로 바로 실행하면 Gemini-silent 방어가 비어 있고, context apply path에서 measured substrate를 만들 위치가 틀려 있다. 내가 구현 책임자라면 HIGH-1/HIGH-2/HIGH-3만 먼저 문서 패치한 뒤 코드로 들어간다.
