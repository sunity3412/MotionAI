# Phase 24 Plan Direct Review - Iteration 4

**Scope:** 3차 리뷰 반영 후의 `24-01-PLAN.md`, `24-02-PLAN.md`, `24-PATTERNS.md`, `24-VALIDATION.md`와 현재 live code seam.

**Method:** 외부 스킬/외부 리뷰 없이 자체 코드-플랜 대조로 검토.

## Verdict

3차 HIGH 대부분은 방향상 반영됐다. 특히 `criteria_from_measured_deviations(...)` seed가 들어가면서 Gemini-silent measured deduction 요구는 이제 Plan 01에서 성립한다(`24-01-PLAN.md:149`, `24-01-PLAN.md:221`, `24-01-PLAN.md:276`).

다만 4차 기준으로는 Plan 02의 production wiring이 아직 실행 가능한 형태로 충분히 닫히지 않았다. 핵심 리스크는 둘이다.

1. `_process`에서 `quantification` / `measured_deviations`를 context+legacy 양쪽에 어떻게 공급할지 현재 제어흐름과 충돌한다.
2. legacy whole-video path가 `criteria_for_fault(...)`에 필요한 `FaultKey` / supported-difference provenance를 안정적으로 제공한다는 보장이 없다.

내가 구현한다면, 이 두 항목을 먼저 고친 뒤 나머지 문구/검증 drift를 정리하겠다.

## Findings

### HIGH-1: `_process`의 "build once before both branches" 지시가 현재 제어흐름과 맞지 않는다

Plan 02는 `_process` seam에서 `baseline_kind`와 `measured_deviations`를 한 번 만들고, context branch와 legacy branch 양쪽 `_apply_vision_veto(...)`로 thread하라고 한다(`24-02-PLAN.md:25`, `24-02-PLAN.md:31`, `24-02-PLAN.md:166`, `24-02-PLAN.md:174`). 그런데 현재 live code는 `quantification`을 `if vision_fault_context is not None:` 내부에서만 만든다(`backend/functions/pipeline/app.py:3115-3139`). legacy branch는 바로 `_apply_vision_veto(...)`를 호출하고 `quantification` 변수가 없다(`backend/functions/pipeline/app.py:3140-3149`).

Plan 02 line 174는 "just before the if block"에서 `measured_deviations`를 만든다고 하면서 동시에 `quantification`은 `_build_vision_quantification_result(...)` 직후에 필요하다고 쓴다. 하지만 그 `_build_vision_quantification_result(...)` 호출 자체가 현재는 if branch 내부에 있다. 그대로 구현하면 legacy branch에서 미정의 변수 또는 `None` semantics가 섞이고, body-relative reach substrate가 branch마다 다르게 빠질 수 있다.

**내 대처:** `_process`에서 먼저 `baseline_kind = _baseline_kind_for_profile(profile)`를 계산한다. 그 다음 branch별로 `quantification`을 명시적으로 결정한다.

- context branch: 기존처럼 `_build_vision_quantification_result(..., baseline_kind=baseline_kind)`를 호출한다.
- legacy branch: 둘 중 하나를 선택한다. (a) `quantification = VisionQuantificationResult(quantificationStatus="unavailable", warnings=["legacy_no_selected_frame_pair"])`로 명시하고 fallback tally를 타게 한다. (b) legacy whole-video path를 tally 대상에서 제외하고 audit에 `legacy_no_quantification`으로 남긴다.

그 후에야 `measured_deviations = _build_deduction_measured_deviations(..., quantification=quantification)`을 만들고 같은 branch의 `_apply_vision_veto(...)`에 넘긴다. "무조건 if 이전 once"보다 "branch별 quantification 확정 후 one call per executed path"가 더 안전하다. 정말 def+one-call invariant가 필요하면, helper를 호출하는 작은 local seam 함수로 감싸서 executed path마다 한 번만 호출되도록 테스트해야 한다.

### HIGH-2: legacy path가 `criteria_for_fault(...)` 입력을 충분히 만들지 못한다

Plan 02는 context path와 legacy fallback을 모두 보존하면서 둘 다 `deduction_engine.tally(...)`로 바꾸겠다고 한다(`24-02-PLAN.md:75`, `24-02-PLAN.md:168`, `24-02-PLAN.md:325`). 그런데 Plan 01의 engine selection은 `fault_context.supported_differences`와 `FaultKey`를 순회해 `ipsf_criteria.criteria_for_fault(fault_key, supported_difference, measured_deviations)`를 호출하는 구조다(`24-01-PLAN.md:221`, `24-01-PLAN.md:228`).

context path는 `VisionFaultContext.supported_differences`에 rich dict를 담고, `_faultKey`를 trace에 사용할 수 있다(`backend/shared/python/sunity_shared/analysis/vision_veto.py:623-630`, `backend/shared/python/sunity_shared/analysis/vision_veto.py:669-688`). 반면 legacy whole-video fallback은 `assess_fault_severity(...)`의 `VisionVerdict.differences`를 그대로 `supported=list(verdict.differences or ())`로 넣는다(`backend/functions/pipeline/app.py:1899-1905`), 또는 `_apply_vision_veto(...)` legacy path에서 아예 plain `VisionVerdict`만 만든다(`backend/functions/pipeline/app.py:2033-2038`). `VisionVerdict` 자체는 `primary_fault`, `severity`, `differences`뿐이다(`backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:125-141`).

즉 legacy 경로는 `criteria_for_fault(...)`가 기대하는 canonical `FaultKey`를 누가, 언제, 어떤 실패처리로 만들지 Plan 02에 빠져 있다. 이 상태에서는 measured seed는 돌아갈 수 있어도, Gemini가 찍은 vision-only fault의 criterion 추가나 coverage gap provenance가 legacy path에서 사라질 수 있다.

**내 대처:** legacy를 둘 중 하나로 명확히 정리한다.

- 선호안: legacy whole-video fallback을 Phase 24 tally routing 대상에서 제외하고, `visionVeto.status="legacy_no_fault_context"` 또는 기존 graceful status로 남긴다. production still-pair context path만 transparent deduction seam으로 삼으면 입력 계약이 단순해진다.
- 보존안: legacy verdict를 즉시 minimal `VisionFaultContext`로 wrap한다. `verdict.differences`의 각 dict에 `vision_veto.fault_key_from_difference(d)`로 `_faultKey`를 붙이고, `selected_frame_pairs=[]`, `quantificationStatus="unavailable"` 또는 explicit legacy quantification을 넣는다. 이 wrap helper를 테스트해 `criteria_for_fault` 또는 coverage gap이 legacy에서도 실제로 호출되는지 검증한다.

내 기준으로는 선호안이 더 낫다. Phase 24의 목적은 transparent measured tally이고, whole-video legacy path는 reference-selected-frame substrate가 없어 오히려 설계 표면을 흐린다.

### MEDIUM-1: "severity locates criterion" 표현이 아직 남아 있고, 구현자를 잘못 이끈다

Plan 01은 이제 "Gemini text/fault label locates, severity is NOT read"로 상당히 정리됐다(`24-01-PLAN.md:228`, `24-01-PLAN.md:315`, `24-01-PLAN.md:324`). 하지만 Plan 02와 PATTERNS에는 여전히 `severity LOCATES` / `criterion pointer` 표현이 남아 있다(`24-02-PLAN.md:118`, `24-02-PLAN.md:168`, `24-02-PLAN.md:300`, `24-02-PLAN.md:329`, `24-PATTERNS.md:165`, `24-PATTERNS.md:188`, `24-VALIDATION.md:49`).

이 표현은 "severity는 selection에서 읽지 않는다"와 같은 문장 안에 같이 들어가 있어 내부 모순이다. 실제로 criterion을 locate하는 것은 `supported_difference.body_part/fault_state` 및 `_faultKey`이고, severity는 arithmetic/selection에서 제외되며 coach root-cause eligibility에만 쓰인다.

**내 대처:** 모든 문구를 아래처럼 통일한다.

> Gemini supported_difference / fault label locates the criterion via `criteria_for_fault`; severity is ignored by criterion selection and scoring, and is used only for `coachRootCauseEligible` continuity.

그리고 `gemini_vision_scorer.py` reframe target도 "severity is a criterion pointer"가 아니라 "verdict/differences carry a criterion pointer; severity remains a non-scoring label"로 고친다.

### MEDIUM-2: `24-PATTERNS.md`가 measured seed를 아직 핵심 패턴으로 반영하지 않는다

Plan 01의 핵심은 activation source가 두 개라는 점이다. measured seed가 먼저 measurable criteria를 활성화하고, Gemini router가 fault-pointed criteria/coverage gap을 더한다(`24-01-PLAN.md:149`, `24-01-PLAN.md:221`). 그런데 `24-PATTERNS.md`의 Phase 24 divergence는 여전히 `(1) SELECT criteria via criteria_for_fault(...)`로 시작한다(`24-PATTERNS.md:45-52`). 테스트 패턴 목록에도 `test_gemini_silent_not_100`이 없다(`24-PATTERNS.md:104`).

이 문서는 Plan 02의 read-first/context에 포함되어 있다(`24-02-PLAN.md:95`, `24-02-PLAN.md:109`). 실행자가 PATTERNS를 먼저 따르면 3차에서 고친 Gemini-silent 방어를 다시 빠뜨릴 수 있다.

**내 대처:** `24-PATTERNS.md`의 divergence step 1을 이렇게 바꾼다.

```text
(1) ACTIVATE criteria from two sources:
    seeded = criteria_from_measured_deviations(measured_deviations)
    pointed = union(criteria_for_fault(...) over supported_differences)
    activated = seeded | pointed
    then group/exclude line-leg substrate.
```

그리고 test pattern 목록에 `test_gemini_silent_not_100`을 추가한다.

### MEDIUM-3: `_build_deduction_measured_deviations` 검증 조건이 서로 다르다

Plan 02 acceptance는 `_build_deduction_measured_deviations`가 "def + ONE seam call"이어야 한다고 말한다(`24-02-PLAN.md:184`). 그런데 verification은 `grep -n "_build_deduction_measured_deviations" ... returns >= 2 hits`라고 되어 있다(`24-02-PLAN.md:317`). `>= 2`는 apply path 내부 호출이 추가되어도 통과할 수 있어, 3차 HIGH-2의 재발을 잡지 못한다.

**내 대처:** 검증을 count-based로 바꾼다. 예를 들어 `rg -n "_build_deduction_measured_deviations\\(" backend/functions/pipeline/app.py`의 결과가 정확히 `def` + allowed seam call(s)인지 검사하고, `_apply_vision_veto` / `_apply_vision_veto_from_context` 함수 body에는 호출이 없다는 unit/source test를 둔다. 만약 HIGH-1 대처처럼 branch별 one-call을 허용한다면, acceptance 문구도 "apply paths 내부 0, executed seam path에서 1"로 바꿔야 한다.

### MEDIUM-4: `gemini_vision_scorer` schema의 band wording이 reframe 범위 밖에 남는다

Plan 02는 `gemini_vision_scorer.py`의 L5/L129/L134 docstring만 reframe 대상으로 잡고, schema/code는 변경하지 않는다고 한다(`24-02-PLAN.md:108`, `24-02-PLAN.md:118`). 하지만 현재 live schema description에도 `none → cap 미적용` 문구가 있다(`backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:157-160`). Phase 24의 band removal 검증이 `apply_downward_cap|SEVERITY_CAP|capApplied` 중심이면 이 "cap 미적용"은 남을 수 있다.

**내 대처:** `gemini_vision_scorer.py`에서 `cap|캡|ceiling|band` 류 문구를 schema description까지 포함해 제거한다. schema code 자체를 바꾸라는 뜻이 아니라, field description을 "정타/결함 없음 = none; 점수 아님; scoring input 아님" 정도로 바꾸면 된다. acceptance도 `rg -n "apply_downward_cap|SEVERITY_CAP|capApplied|cap_applied|cap 미적용|하향 캡" ...`처럼 band prose를 잡도록 넓힌다.

## Recommended Patch Order

1. Plan 02의 `_process` seam 지시를 branch-aware quantification flow로 고친다.
2. legacy path를 "tally 제외" 또는 "minimal VisionFaultContext wrap" 중 하나로 결정하고, 그 결정에 맞는 테스트를 추가한다.
3. `severity locates criterion` 문구를 `supported_difference/fault label locates criterion`으로 일괄 치환한다.
4. `24-PATTERNS.md`에 measured seed activation과 `test_gemini_silent_not_100`을 반영한다.
5. `_build_deduction_measured_deviations` 검증을 exact/source-test 기반으로 강화한다.
6. `gemini_vision_scorer.py` schema description의 residual band wording을 제거 대상으로 추가한다.

## Close

이제 Phase 24의 큰 방향은 유지해도 된다. 다만 Plan 02를 현 상태로 실행하면 context path는 어느 정도 구현 가능해도 legacy path와 quantification threading에서 흔들릴 가능성이 높다. 내가라면 legacy를 과감히 tally 밖으로 빼거나 minimal context로 명시적으로 wrap해서, Phase 24의 scoring seam을 "입력 계약이 닫힌 한 경로"로 줄인 뒤 실행한다.
