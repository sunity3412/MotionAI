# Phase 24 Direct Review - Iteration 2

**Reviewer:** Codex direct self-review, no external skill/subagent  
**Reviewed at:** 2026-06-24  
**Scope:** Patched `24-01-PLAN.md`, `24-02-PLAN.md`, `24-03-PLAN.md`, `24-PATTERNS.md`, and the current Phase 18 / VisionFaultContext code surfaces they depend on.

## Verdict

1차 리뷰의 핵심 불일치는 상당수 반영됐다. `deductionBreakdown` object shape, signed-negative `points`, fallback traceability record, linear slope, `capApplied` migration scope, repo-wide band grep, Plan 03 bare gate command은 현재 계획에서 방향이 맞다.

다만 2차 기준으로는 "공식"보다 "어떤 criterion이 언제 활성화되는가"가 가장 위험하다. 지금 계획 그대로 구현하면 leg/split/reach가 같은 `FaultKey.keypoint_set` 아래에서 섞이거나, `body_relative_reach`가 부호 때문에 감점하지 않는 경로가 생길 수 있다. 내가 실행 책임자라면 아래 HIGH 항목은 구현 전에 계획에 다시 못 박겠다.

## Findings

### HIGH-1: `criterion_for_fault_key(keypoint_set)` 하나로는 leg/split/reach 라우팅을 표현할 수 없다

Plan 01은 다섯 criterion을 정의하면서 `leg_extension`과 `split_angle`을 모두 `keypoint_set="leg"`에 둔다(`24-01-PLAN.md:126-131`). 같은 블록에서 `body_relative_reach`도 hand/knee reach일 때만 활성화한다고 한다(`24-01-PLAN.md:131`). 그런데 실제 API는 `criterion_for_fault_key(keypoint_set)`로 설계되어 있고, `leg -> leg_extension or split_angle`, `arm -> arm_extension`, `line -> line` 식으로 한 keypoint set을 한 criterion에 매핑하려 한다(`24-01-PLAN.md:134`).

현재 `FaultKey`는 `part_scope`, `side`, `keypoint_set`, `fault_kind` 네 필드뿐이고(`backend/shared/python/sunity_shared/analysis/vision_veto.py:201-208`), `FAULT_KINDS`도 `pole_gap_or_bent` / `extension_or_alignment` 두 값뿐이다(`backend/shared/python/sunity_shared/analysis/vision_veto.py:180-183`). 게다가 `split` / `straddle` 키워드는 현재 `leg`로 정규화된다(`backend/shared/python/sunity_shared/analysis/vision_veto.py:238-239`). 따라서 `무릎 굽음`, `스플릿 부족`, `무릎 reach 부족`이 모두 `leg` 아래로 들어올 수 있다.

**Risk:** 구현자가 `leg`를 `leg_extension`으로 고정하면 split fault가 누락된다. 반대로 `leg`에서 `leg_extension + split_angle + body_relative_reach`를 모두 켜면 같은 fault가 과감점된다. 특히 Plan 01의 `criterion_for_fault_key_total_over_vocab` 테스트는 "8개 keypoint_set이 빠지지 않는다"만 보장하고, 같은 keypoint_set 안의 criterion 선택 정확도는 보장하지 않는다.

**How I would handle it:** `criterion_for_fault_key(keypoint_set)`를 폐기하거나 내부 helper로 낮추고, 외부 API는 전체 fault context를 받게 한다.

```python
def criteria_for_fault(
    fault_key: FaultKey,
    supported_difference: dict | None,
    measured_deviations: dict,
) -> tuple[str, ...] | CoverageGap:
    ...
```

내가 짠다면 최소 테스트를 이렇게 둔다.

- `body_part="무릎", fault_state="굽음"` -> `leg_extension`만 활성화
- `body_part="스플릿" / "straddle"` -> `split_angle`만 활성화
- `body_part="손" 또는 "무릎", fault_state`가 reach/거리/높이 부족 계열 -> `body_relative_reach`
- `body_part="그립"` -> 현재 substrate가 없으면 `coverageGaps["grip"]`, 임의 감점 금지
- 동일 measured substrate에서 minor/major severity만 바꿔도 활성 criterion set과 points는 동일

### HIGH-2: `body_relative_reach`의 `delta_notches` 부호가 감점 방향과 충돌한다

현재 `body_relative_notches()`는 `delta_notches = student_notches - reference_notches`로 산출한다(`backend/shared/python/sunity_shared/analysis/vision_veto.py:536-541`). Plan 01은 `body_relative_reach`가 이 `delta_notches`를 소비한다고만 쓰고(`24-01-PLAN.md:131`, `24-01-PLAN.md:190`), 공통 감점 공식은 `over = max(0.0, dev - crit.tolerance)`라고 되어 있다(`24-01-PLAN.md:192`).

문제는 "학생 reach가 reference보다 짧다"는 일반적인 fault가 `student_notches < reference_notches`, 즉 `delta_notches < 0`이라는 점이다. 이 값을 그대로 `dev`로 넣으면 `max(0, negative - tolerance)`라서 감점이 0이 된다. 반대로 `abs(delta_notches)`를 쓰면 reference보다 더 멀리 뻗은 경우도 부족 reach로 처벌할 수 있다.

**Risk:** Phase 24가 어렵게 연 `body_relative_reach` criterion이 실제 부족 reach fault를 놓치거나, 방향이 반대인 움직임을 감점한다. 그러면 `baseline_kind`가 scoring substrate라는 Plan 02의 핵심 주장도 시험에서는 통과하지만 실제 동작 의미와 어긋날 수 있다.

**How I would handle it:** criterion config에 `direction`을 명시하고, reach 부족은 아래처럼 정의한다.

```python
shortfall = max(0.0, reference_notches - student_notches - tolerance)
# equivalently: max(0.0, -delta_notches - tolerance)
```

그리고 테스트는 반드시 양방향을 둔다.

- reference 3칸, student 2칸 -> 감점 발생
- reference 2칸, student 3칸 -> `insufficient_reach` 기준 감점 0
- tolerance 이내 shortfall -> 감점 0
- left/right/unknown side가 `_NOTCH_REACH_KEYPOINTS` 중 어느 keypoint를 집계하는지 고정

### HIGH-3: `DeductionRecord.baseline` 타입과 의미가 충돌한다

Plan 01의 lockstep contract는 record key를 `("criterion", "measuredValue", "baseline", "deviation", ...)`로 정의한다(`24-01-PLAN.md:120`). TS 타입도 `baseline: number`라고 못 박는다(`24-01-PLAN.md:122`). 그런데 tally action은 record를 만들 때 `baseline from the baseline_kind arg`라고 되어 있다(`24-01-PLAN.md:196`). `baseline_kind`는 `"floor" | "pole_vertical" | "hip_line"` 문자열이다.

**Risk:** 구현자가 문장을 따르면 Python은 `baseline="hip_line"` 같은 string을 record에 넣고 TS/contract와 충돌한다. 반대로 TS를 따르면 numeric baseline만 남고, reach criterion에서 어떤 baseline kind가 scoring에 쓰였는지 record-level audit이 사라진다. `DeductionBreakdown.baseline=100`과 `DeductionRecord.baseline`도 이름이 같아 score baseline인지 measurement target인지 헷갈린다.

**How I would handle it:** 필드를 분리한다.

- `DeductionBreakdown.baseline`: score baseline `100`
- `DeductionRecord.baselineValue`: numeric target/reference value, 예: `180`, `160`, `reference_notches`, `100`
- `DeductionRecord.baselineKind?: "floor" | "pole_vertical" | "hip_line"`: reach criterion에만 필수

최소 수정으로 `baseline` 이름을 유지해야 한다면, `baseline`은 numeric으로만 두고 `baselineKind`를 추가한다. 이 경우 Python `DEDUCTION_RECORD_KEYS`, TS `DeductionRecord`, docs §10, lockstep test를 모두 같이 바꿔야 한다.

### HIGH-4: Plan 03의 phase18 일반화 게이트는 현재 repo fixture만으로는 실행 불가능하다

Plan 03은 "phase18 `pairs.yaml` fault labels + stored quantification"으로 일반화 게이트를 돌린다고 한다(`24-03-PLAN.md:93`) 그리고 `assert_gates.py`가 "available pure + phase18-derived fixtures"에서 0으로 종료해야 한다고 한다(`24-03-PLAN.md:104`).

하지만 현재 Phase 18 fixture에는 새 tally 입력이 없다. `pairs.yaml`은 fault 라벨과 S3 key만 갖고 있고(`backend/evals/phase18/dataset/pairs.yaml:41-119`), baseline JSON도 old scorer의 `fault_overall`, `success_overall`, `margin`, `verdict` 스냅샷뿐이다(`backend/evals/phase18/baseline/eval18_serial_baseline.json:14-20`). Phase 24 `deductionBreakdown`, quantification, measured deviation substrate는 없다.

**Risk:** `assert_gates.py`가 세 가지 중 하나로 흐를 가능성이 크다.

- old overall score를 새 tally 결과처럼 읽는다.
- synthetic fixture를 "phase18-derived"라고 부른다.
- gate를 통과시키기 위해 일반화 부분을 사실상 빈 검사로 만든다.

셋 다 ND-07 게이트 신뢰도를 떨어뜨린다.

**How I would handle it:** pod-free와 Pod-serial 경계를 더 엄격히 나눈다.

- Plan 03 Task 1의 pod-free `assert_gates.py`는 traceability/monotonicity/determinism/criterion-selection synthetic gates까지만 PASS 대상으로 둔다.
- Phase 18 일반화는 `backend/evals/phase24/baseline/phase24_breakdowns.json` 같은 명시 artifact가 있을 때만 실행한다.
- 그 artifact는 Task 3 Pod sweep 후 생성/커밋하거나, 없으면 `SKIPPED (phase24 breakdown fixture absent)`를 출력하고 acceptance에서도 "partial generalization skipped"를 인정한다.
- "phase18-derived fixtures"라는 표현은 실제 Phase 24 quantification/breakdown fixture가 생기기 전까지 쓰지 않는다.

### HIGH-5: `line` criterion과 leg/arm extension이 같은 substrate를 이중 감점할 수 있다

Plan 01은 `leg_extension`과 `arm_extension`을 각각 knee/elbow extension criterion으로 두고(`24-01-PLAN.md:127-128`), 동시에 `line`을 `dimensions.line_score` / `extension_deviation`이 모든 extend joint over ALL EXTEND joints로 계산하는 collective criterion이라고 둔다(`24-01-PLAN.md:130`). tally action은 "for each criterion in criterion_groups"로 deviation을 집계한다(`24-01-PLAN.md:190`).

**Risk:** 같은 굽은 무릎/팔꿈치가 `leg_extension` 또는 `arm_extension`에서 한 번 감점되고, `line`의 collective 180도 deficit에서 다시 감점될 수 있다. `test_criterion_grouping_no_runaway`는 "양쪽 다리 두 개를 하나의 leg_extension record로 묶는다"는 것만 막고, cross-criterion double count는 막지 않는다.

**How I would handle it:** line criterion의 책임을 둘 중 하나로 좁힌다.

1. `line`은 `FaultKey.keypoint_set == "line"` 또는 line-dominant fault에서만 활성화하고, explicit leg/arm extension이 활성화된 같은 substrate는 제외한다.
2. 또는 `line`을 residual criterion으로 만들어 leg/arm/split에 이미 할당된 joints를 빼고 남은 clean-line substrate만 본다.

내 선택은 1번이다. 구현 비용이 낮고, Phase 18 label의 `dominant_dimension: line`과도 맞다. acceptance에는 "single bent knee cannot emit both `leg_extension` and `line` records unless two independent measured substrates are present and named" 테스트를 추가하겠다.

### MEDIUM-1: false-positive `>= ~95`는 "RESULT not target" 주석만으로는 curve-fit 위험을 다 막지 못한다

Plan 03은 success/elite member가 high로 남아야 한다며 `>= ~95` 같은 result-shaped bound를 둔다(`24-03-PLAN.md:93`). 주석으로 "RESULT not target"을 달라고 했지만, 같은 정은지 6-pair fixture 위에서 숫자 bound를 걸면 구현자가 그 bound에 맞춰 slope/cap/tolerance를 조정하고 싶어지는 압력이 생긴다.

**Risk:** 새 감점식이 "명명백백한 감점 record"보다 "정은지 success를 95 이상으로 유지"에 맞춰질 수 있다. 특히 Phase 24는 slope/cap/tolerance가 `[ASSUMED]`인 부분이 많아서 이 위험이 실제다.

**How I would handle it:** pure gate에서는 숫자 bound보다 구조 bound를 우선한다.

- success member에 감점 record가 없거나 tolerance 이내인 이유가 traceable하면 PASS
- fault member는 같은 criterion set 또는 named criterion에서 더 큰 shortfall을 보여야 PASS
- numeric high-score bound는 Pod sweep checkpoint의 observational report로 두고, fail gate로 만들려면 sensitivity set이 추가된 뒤에 승격

## Recommended Patch Order

1. `criterion_for_fault_key(keypoint_set)`를 전체 `FaultKey`/difference 기반 `criteria_for_fault(...)`로 재설계한다.
2. `body_relative_reach`의 부호/direction/tolerance/side aggregation을 명시한다.
3. `DeductionRecord.baseline`을 numeric baseline과 `baselineKind`로 분리한다.
4. `line`과 leg/arm extension의 cross-criterion double count 정책을 정한다.
5. Plan 03의 phase18 일반화 gate를 "artifact 있을 때 실행"으로 바꾸고, 현재 pod-free acceptance는 synthetic gates 중심으로 낮춘다.
6. `>= ~95`는 당장 hard gate가 아니라 observational checkpoint로 둔다.

## Bottom Line

2차 기준으로 Phase 24는 1차의 계약 불일치 대부분을 회수했지만, criterion activation 설계가 아직 실행 가능한 수준으로 구체화되지 않았다. 내가 구현한다면 지금 바로 코드로 들어가지 않고, HIGH-1~HIGH-4를 먼저 계획에 패치한다. 특히 `leg` 하나에서 `leg_extension` / `split_angle` / `body_relative_reach`를 구분하는 API와 `delta_notches` 감점 방향은 나중에 코드리뷰에서 고치기보다 지금 설계에서 고정하는 편이 훨씬 싸다.
