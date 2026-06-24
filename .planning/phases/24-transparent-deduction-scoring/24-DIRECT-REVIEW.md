# Phase 24 Direct Review

**Reviewer:** Codex direct self-review, no external skill/subagent  
**Reviewed at:** 2026-06-24  
**Scope:** `24-01-PLAN.md`, `24-02-PLAN.md`, `24-03-PLAN.md`, phase research/pattern docs, and the current production code seams they reference.

## Verdict

Phase 24의 방향은 맞다. `SEVERITY_CAP` / `apply_downward_cap` 밴드를 없애고, Gemini를 "점수 산출자"가 아니라 "측정 대상 지목자"로 낮추는 결정은 현재 scoring 철학과 잘 맞는다.

다만 지금 계획 그대로 실행하면 몇 가지가 실제 구현에서 깨질 가능성이 높다. 특히 `DeductionBreakdown` 저장 모양, signed `points` 산식, 측정 기질 생성, `capApplied` 제거 범위는 실행 전에 반드시 고쳐야 한다.

내 의견은 **바로 execute 하지 말고 Plan 01/02/03 문서를 먼저 패치한 뒤 실행**하는 것이다. 아래 HIGH 항목들은 implementation 전에 막아야 한다.

## Findings

### HIGH-1: `deductionBreakdown` 계약이 object인지 list인지 서로 다르다

`24-01-PLAN.md`는 TS/Python/docs 계약을 `DeductionBreakdown { baseline, records, final, coverageGaps, fallback }` object로 정의한다(`24-01-PLAN.md:116-120`). 그런데 `24-02-PLAN.md`는 seam에서 `result['deductionBreakdown'] = breakdown.to_records()`를 저장한다고 쓴다(`24-02-PLAN.md:24`, `24-02-PLAN.md:49-50`, `24-02-PLAN.md:62-63`). `result.tsx` 마이그레이션도 `result.deductionBreakdown?.final`을 읽는 전제다(`24-02-PLAN.md:189`).

**Risk:** 백엔드는 list를 저장하고 프론트/contract는 object를 기대하는 상태가 된다. TypeScript는 새 타입으로 통과해도 운영 Firestore 문서에서는 `deductionBreakdown.final`이 없고, 추적성 게이트도 저장된 shape와 다른 객체를 검증할 수 있다.

**How I would handle it:** 저장 계약은 object 하나로 고정한다.

- `result["deductionBreakdown"] = breakdown.to_dict()`
- `breakdown.to_records()`는 내부 helper 또는 `to_dict()["records"]` 구현 detail로만 둔다.
- `complete_analysis`에는 `_validate_deduction_breakdown(result.get("deductionBreakdown"))`를 추가한다. 이 validator는 top-level dict를 받고, `records`/`coverageGaps`는 list-of-flat-dicts만 허용한다.
- Plan 02의 "list-of-flat-dicts" 표현은 "object containing list-of-flat-dicts"로 바꾼다.

### HIGH-2: `points` 부호와 traceability 산식이 충돌한다

Plan 01은 `DeductionRecord.points`를 음수 감점으로 만들라고 한다: `points=-round(capped,1)` (`24-01-PLAN.md:188`). 그런데 여러 곳에서 `final == baseline − Σ(records.points)`라고 쓴다(`24-01-PLAN.md:27`, `24-01-PLAN.md:174`, `24-01-PLAN.md:233`, `24-01-PLAN.md:292`). `points=-9`이면 `100 - (-9) = 109`가 되어 산식이 뒤집힌다. Plan 03은 한 곳에서만 `100 - sum(-r.points)`로 올바른 형태를 쓴다(`24-03-PLAN.md:86`).

**Risk:** 구현자가 문서 중 어느 문장을 따르느냐에 따라 record sign, final 산식, traceability gate가 서로 다르게 구현된다. 이건 점수 엔진에서 가장 위험한 종류의 불일치다.

**How I would handle it:** 감점 내역 UX가 "−X"를 보여야 하므로 `points`는 signed negative로 유지한다. 대신 모든 산식을 다음으로 통일한다.

```text
deducted = sum(-record.points for record in records)
final = max(0, round(baseline - deducted))
equivalently: final = max(0, round(baseline + sum(record.points)))
```

그리고 `test_breakdown_serializes_flat`, `check_traceability`, docs §10, success criteria를 모두 이 산식으로 바꾼다. 더 깔끔하게 하려면 `points` 대신 positive `deductionPoints`로 바꾸는 방법도 있지만, 그러면 보고서 표기에서 다시 부호를 붙여야 하므로 지금은 signed `points`를 명시하는 편이 낫다.

### HIGH-3: seam에서 `measured_deviations`를 어떻게 만들지 빠져 있다

Plan 01의 `tally()`는 `dimension_overall`, `measured_deviations`, `dimension_scores`, `baseline_kind`를 받는다고 정의한다(`24-01-PLAN.md:179-182`). 하지만 현재 pipeline seam에서 실제로 있는 값은 `angles`, `profile`, `assessments`, `dimension_scores`, `quantification`이다(`backend/functions/pipeline/app.py:2987-2998`, `app.py:3091-3139`). `dimension_scores`는 0~100 점수이고, `angleDeltas`는 student-reference delta라서 IPSF absolute deviation이 아니다.

**Risk:** 구현자가 급하게 `dimension_scores`나 `angleDeltas`를 `measured_deviations`로 넘기면 `leg_extension`/`line`이 student-vs-180/160 기준이 아니라 score 또는 reference-relative delta로 감점된다. Plan 01이 막으려는 HIGH F 문제가 그대로 생긴다.

**How I would handle it:** Plan 02 Task 2에 명시적인 substrate builder를 추가한다.

```python
measured_deviations = _build_deduction_measured_deviations(
    angles=angles,
    profile=profile,
    assessments=assessments,
    dimension_scores=dimension_scores,
    quantification=quantification,
)
```

이 helper는 최소한 다음을 named shape로 반환해야 한다.

- `extension_deficits_by_joint`: `dimensions.extension_deviation(angles, profile)` / `line_deficits_by_joint` 기반
- `line_score` 또는 `line_deficit`: `dimensions.line_score`와 동일 source임을 검증
- `split_angle` source: 실제 split 각도 또는 명시적 unavailable
- `body_relative_notches`: reference-relative criterion을 둘 경우에만 사용

그리고 seam test는 "dimension score 72를 deviation 72도로 착각하지 않는다"는 회귀를 하나 넣는 게 좋다.

### HIGH-4: `baseline_kind`와 `bodyRelativeNotches`가 scoring에 쓰이지 않을 수 있다

Plan 01은 현재 criterion을 네 개로 제한한다: `leg_extension`, `arm_extension`, `split_angle`, `line`이며 모두 `ipsf_absolute`라고 설명한다(`24-01-PLAN.md:108`, `24-01-PLAN.md:122-127`). 반면 같은 계획은 `reference_relative` criterion test도 요구한다(`24-01-PLAN.md:170`, `24-01-PLAN.md:229`). Plan 02는 `baseline_kind`를 per-move로 파생하고 `_build_vision_quantification_result`에 threading하는 것을 큰 성공 조건으로 둔다(`24-02-PLAN.md:23`, `24-02-PLAN.md:219`).

**Risk:** 네 기준이 전부 IPSF-absolute이면 `bodyRelativeNotches`와 `baseline_kind`는 scoring에는 쓰이지 않고 audit label로만 남는다. 그러면 "kip-up=floor baseline" 같은 Plan 02의 핵심 주장이 실제 점수에 영향을 주지 않는다.

**How I would handle it:** 둘 중 하나로 정리해야 한다.

1. Phase 24에서 body-relative reach를 실제 점수 substrate로 쓰려면, 작은 범위의 `reference_relative` criterion을 추가한다. 예: `body_relative_reach`가 `bodyRelativeNotches.delta_notches`를 소비하고, support된 fault key가 손/무릎 reach에 해당할 때만 활성화된다.
2. 아직 reach criterion을 신뢰하지 못한다면, `baseline_kind`와 `bodyRelativeNotches`는 이번 phase에서 audit-only라고 명시하고 SCORE-14/Plan 02 성공 조건에서 "scoring substrate" 표현을 제거한다.

내가 한다면 1번을 택하되, grip/head/torso 전체를 무리하게 매핑하지 않고 현재 측정 가능한 hand/knee reach만 좁게 열겠다. coverage gap은 그대로 남긴다.

### HIGH-5: `capApplied` 제거 범위가 실제 full suite 범위보다 좁다

Plan 02 Task 4는 `test_vision_veto.py`와 `test_pipeline_vision_gate.py`만 broken caller로 명시한다(`24-02-PLAN.md:206-210`, `24-02-PLAN.md:228`). 하지만 현재 repo에는 다른 live tests와 source docstring도 old band 계약을 직접 참조한다:

- `backend/tests/test_pipeline_mode3.py`가 `vision_veto.SEVERITY_CAP` monkeypatch와 `capApplied` assert를 여러 번 사용한다.
- `backend/tests/test_gemini_vision_scorer.py:208-210`이 `vision_veto.apply_downward_cap`을 직접 호출한다.
- `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:5`, `:129`, `:134` docstring이 severity를 `apply_downward_cap` 입력이라고 설명한다.

**Risk:** Plan 02가 문서대로 끝나도 `cd backend && python -m pytest tests/ -q`가 깨지거나, 더 나쁘게는 old band 개념이 live source comments에 남는다.

**How I would handle it:** Task 4 범위를 넓힌다.

- `backend/tests/test_pipeline_mode3.py`를 files_modified에 추가하고, cap-specific assertions를 tally/toggle/mode3-held assertions로 바꾼다.
- `backend/tests/test_gemini_vision_scorer.py`의 `none` verdict test는 "score-free severity output"과 `_SCORE_PATTERN` guard로 재작성한다.
- `gemini_vision_scorer.py` docstring에서 `apply_downward_cap` 언급을 "criterion pointer" 의미로 바꾼다.
- Acceptance grep을 live code/test 전체로 확장한다:

```bash
rg -n "apply_downward_cap|SEVERITY_CAP|capApplied|cap_applied" \
  backend/shared/python backend/functions backend/tests app/src docs/contract.md
```

필요하면 migration 중 planning archive는 제외하되, live code와 tests는 0이어야 한다.

### HIGH-6: `cap_would_apply`의 "STRICT PARITY" 설명이 현재 동작과 정확히 같지 않다

현재 `cap_would_apply`는 `apply_downward_cap(overall_score, severity) < overall_score`로 계산된다(`backend/functions/pipeline/app.py:1878-1880`, `app.py:1899-1900`). 즉 old cap 기준으로 이미 낮은 점수라면 `moderate`/`major`라도 false가 될 수 있다. Plan 02는 이를 `severity in ("moderate","major")`로 바꾸면서 "오늘의 coach-injection trigger를 EXACTLY reproduces"라고 쓴다(`24-02-PLAN.md:25`, `24-02-PLAN.md:62-69`, `24-02-PLAN.md:241`).

**Risk:** 이건 band-free 방향으로는 합리적일 수 있지만 "exact parity"는 아니다. 이미 낮은 점수의 moderate/major verdict에서 coach root-cause injection이 새로 켜질 수 있다. 반대로 old cap threshold를 계속 들고 있으면 밴드 제거 철학과 충돌한다.

**How I would handle it:** 용어를 정직하게 바꾼다. `cap_would_apply`는 legacy field name으로 두더라도 의미는 `coachRootCauseEligible`로 문서화하고, "strict parity" 표현을 제거한다. 테스트도 두 케이스를 명시한다.

- `minor`/`none`은 false
- `moderate`/`major`는 overall이 이미 낮아도 true로 할지, 아니면 별도 product 결정을 요구할지

내 선택은 severity-only로 coach context를 주입하는 것이다. 다만 이것은 "band-free continuity behavior"이지 "exact old behavior"는 아니다.

### MEDIUM-1: quantification unavailable fallback은 traceability gate와 충돌한다

Plan 01은 quantification unavailable이면 `final=dimension_overall`, `records=()`일 수 있다고 한다(`24-01-PLAN.md:181`). 동시에 traceability는 `final`이 record points로 역산되어야 한다고 한다(`24-01-PLAN.md:27`, `24-03-PLAN.md:86`).

**Risk:** fallback이 실제로 중요한 false-negative 방어인데, 그 경로는 breakdown에 아무 record가 없어 "왜 78점인지"를 설명하지 못한다. 추적성 gate가 fallback을 예외 처리하면 belle의 "명명백백" 원칙이 가장 불안한 경로에서 약해진다.

**How I would handle it:** fallback도 record로 만든다. 예:

- `criterion="dimension_overall_fallback"`
- `ruleId="quantification_unavailable_dimension_overall"`
- `points=dimension_overall - 100` (negative)
- `unit="score"` 또는 별도 `unit: "score_delta"` 허용
- `deviationSource="dimension_overall"`

이렇게 하면 fallback도 `100 + sum(points) == final`로 추적된다. 이 방식을 쓰려면 contract의 `unit` / `deviationSource` union을 확장해야 한다.

### MEDIUM-2: deduction curve 지시가 `score_from_deviation`과 linear slope 사이에서 흔들린다

Plan 01 key link는 `deduction_engine.tally`가 `kismam.score_from_deviation`으로 deviation→points mapping을 delegate한다고 쓴다(`24-01-PLAN.md:45-48`). Pattern doc도 "Don't hand-roll ... delegate to `kismam.score_from_deviation`"라고 한다(`24-PATTERNS.md:49`). 반면 실제 action은 `raw = over * crit.slope`, slope=`kismam._PENALTY_PER_DEG`라고 한다(`24-01-PLAN.md:185`), Research primary recommendation도 linear slope다(`24-RESEARCH.md:56`, `24-RESEARCH.md:318`).

**Risk:** 한 구현자는 gaussian score를 감점점수로 뒤집고, 다른 구현자는 linear slope를 쓸 수 있다. 둘 다 monotonic이지만 숫자 분포와 cap 동작이 완전히 다르다.

**How I would handle it:** Phase 24는 linear로 고정한다. `score_from_deviation`은 "기존 scale/NaN-safe precedent"로만 언급하고, points mapping delegate 문장은 삭제한다. `deduction_engine.py` acceptance도 `raw = over * crit.slope`와 `_PENALTY_PER_DEG` 사용을 검증하게 바꾼다.

### MEDIUM-3: Plan 03 verify command가 실패를 숨길 수 있다

`24-03-PLAN.md` verify command가 `cd backend && python evals/phase24/assert_gates.py; echo "exit=$?"` 형태다(`24-03-PLAN.md:99`). shell에서 마지막 명령은 `echo`라서, 앞의 gate가 실패해도 전체 command는 0으로 끝날 수 있다.

**Risk:** gate 실패를 로그에는 보이지만 automation status로는 green 처리할 수 있다. Phase 20 review 때도 같은 패턴이 terminal gate false-green 위험이었다.

**How I would handle it:** command를 둘 중 하나로 바꾼다.

```bash
cd backend && python evals/phase24/assert_gates.py
```

또는 exit code를 출력해야 한다면:

```bash
cd backend && python evals/phase24/assert_gates.py
status=$?
echo "exit=$status"
exit "$status"
```

### MEDIUM-4: Pattern map이 최신 Plan 01과 충돌한다

`24-PATTERNS.md`는 `ipsf_criteria.py`에 6개 criterion(`toe_alignment`, `posture`, `pole_contact`)을 정의하라고 말한다(`24-PATTERNS.md:66`). 최신 Plan 01은 substrate-honesty 때문에 4개 criterion만 열고 나머지는 coverage gap으로 둔다(`24-01-PLAN.md:108-110`, `24-01-PLAN.md:122-127`).

**Risk:** 실행자가 Pattern Map을 먼저 따르면 Plan 01이 의도적으로 막은 "측정 기질 없는 criterion"을 다시 열 수 있다. 그러면 ND-06의 honest coverage gap이 흐려진다.

**How I would handle it:** `24-PATTERNS.md`를 Plan 01 기준으로 정리한다. 측정 가능한 4개를 canonical로 두고, toe/posture/pole-contact는 "future coverage gap candidate"로 내려야 한다.

## Recommended Patch Order

1. Plan 01의 `DeductionBreakdown` 저장 shape와 signed `points` 산식을 먼저 고정한다.
2. Plan 02에 `_build_deduction_measured_deviations(...)` substrate builder를 추가하고, `result["deductionBreakdown"] = breakdown.to_dict()`로 수정한다.
3. `reference_relative` criterion을 실제로 하나 열지, 아니면 이번 phase에서 audit-only로 둘지 결정한다. 결정 전까지 baseline_kind를 scoring success criterion으로 두면 안 된다.
4. Plan 02 files_modified/test scope에 `test_pipeline_mode3.py`, `test_gemini_vision_scorer.py`, `gemini_vision_scorer.py` docstring migration을 추가한다.
5. `cap_would_apply`를 exact parity라고 부르지 말고 band-free coach eligibility로 재정의한다.
6. Fallback traceability record 또는 explicit fallback exception 정책을 정하고 contract/gates에 반영한다.
7. Plan 03 gate command에서 `; echo "exit=$?"`를 제거한다.
8. `24-PATTERNS.md`의 stale 6-criterion / `score_from_deviation` 지시를 최신 Plan 01 기준으로 정리한다.

## Bottom Line

이 계획은 핵심 방향이 맞지만, 지금 상태는 "좋은 철학 + 위험한 계약 불일치"에 가깝다. 내가 실행 책임자라면 HIGH-1부터 HIGH-5까지는 문서 패치 없이 구현을 시작하지 않는다. 특히 `DeductionBreakdown` shape와 `points` 산식은 나중에 코드리뷰로 잡기보다 계획에서 먼저 못 박는 게 비용이 훨씬 낮다.
