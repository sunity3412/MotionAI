# Phase 24 — 투명 감점-합산 채점 ND-07 게이트 (pod-free)

Phase 24 는 채점의 한 레이어를 교체한다: `min(overall, SEVERITY_CAP[severity])` 고정-천장
밴드 → `final = max(0, round(100 + Σ signed-negative points))` 투명 감점-합산. 이 디렉터리는
그 tally 가 **추적가능·단조·결정적**임을 Pod/GPU 없이 증명하는 게이트다.

`assert_gates.py` 는 Phase 18 의 case-by-case 밴드 매니페스트(verdict-consistency /
discriminate-margin)를 **대체**한다. 그 매니페스트는 curve-fit 유발(moderate≤75 / major=50)
이라 ND-07 이 RETIRE 했다. phase18 의 `pairs.yaml` fault 라벨 + `known_false_positive`/
`known_gate_blocked` 추적은 **보존**(일반화 게이트의 fault-label 소스로 재사용).

> **정은지 95~100 은 RESULT, not a target.** 순수 게이트는 합성 데이터 위에서 tally 가
> 추적가능/단조/결정적임만 증명한다. 보유 6 페어에 수치 ≥95 를 맞추는 bound 는 순수
> 게이트에 **절대 미적용**(MEDIUM-1 — slope/cap/tolerance 가 `[ASSUMED]`이라 curve-fit 유발).

## 게이트 (importable 함수 — `assert_gates.py`)

| 함수 | 무엇을 증명 | scope |
|---|---|---|
| `check_traceability(breakdowns)` | 모든 −point 역산가능; `final == max(0, round(100 + Σ records.points))`(signed-negative points, HIGH-2 통합식); 각 record 의 non-null ruleId/criterion + finite measuredValue/deviation + 수치 baselineValue + deviationSource + ipsfAnchor | 합성 fixture set 전체. **fallback record 포함**(criterion='dimension_overall_fallback', unit='score_delta', deviationSource='dimension_overall', baselineValue=100 — MEDIUM-1, 예외가 아니라 PASS) |
| `check_monotonicity()` | criterion 별 합성 편차 sweep(0..90°) → `final` 비증가(zero inversion) | **ACTIVATED CRITERION SET 고정** — sweep 내내 같은 fault_context 로 criteria 선택 불변. per-criterion `min(raw, ipsf_cap)`-before-sum 이 고정 set 의 global monotonicity 보존 |
| `check_determinism()` | 같은 stored 입력 → byte-identical breakdown(to_dict 직렬화 비교) | **MATH-determinism**, frame-pair hash verdict cache **조건부**. Gemini 샘플링이 결정적이라는 주장 **아님** |
| `check_criterion_selection_determinism()` | criterion SELECTION 이 `supported_differences` 의 **순수 함수** — 무관 필드(severity/telemetry) 변주에 불변 | 실제 Phase-18 drift(Gemini → 다른 fault set → 다른 selection) 방어 게이트 |
| `check_generalization(pairs, breakdowns)` | phase18 6-페어 STRUCTURAL 일반화 | **ARTIFACT-GATED**(HIGH-4) + **STRUCTURAL**(MEDIUM-1) — 아래 |

## determinism scope 정직성

실제 Phase-18 drift 는 tally **수학**이 아니라 **Gemini 샘플링**(다른 fault set → 다른
criterion selection)이었다. 그래서 determinism 을 둘로 명시 분리한다:

- **MATH-determinism** (`check_determinism`): 같은 입력 → byte-identical breakdown. verdict
  cache(temp 0 + frame-pair hash) 조건부. Gemini-sampling 결정성 주장 아님.
- **criterion-SELECTION-determinism** (`check_criterion_selection_determinism`): 활성 criterion
  set 이 `supported_differences` 의 순수 함수. severity/telemetry 같은 무관 필드는 selection 을
  바꾸면 안 된다. cold-re-run-identical-selection 검증은 Task 3 Pod 체크포인트.

## monotonicity-given-fixed-criterion-set scope

단조성은 ACTIVATED CRITERION SET 이 **고정**일 때만 주장한다(criteria 선택을 sweep 동안
불변으로 유지). criterion selection 자체가 바뀌면(예: Gemini 가 다른 fault 를 짚으면) 단조성은
그 축에서 정의되지 않는다 — 그 축은 selection-determinism 게이트가 담당.

## traceability 공식

```
final == max(0, round(100 + Σ records.points))     # points SIGNED NEGATIVE (HIGH-2)
```

유일한 clamp 은 `max(0, …)` — 상한 밴드 없음(ND-01). fallback record(quantification
unavailable)도 이 식을 만족: `points = dimension_overall − 100`(signed-negative),
`final = dimension_overall`, `baselineValue = 100`. 추적성 게이트는 이 fallback 을 **PASS**
하지 skip 하지 않는다(MEDIUM-1 — belle "명명백백하면 의외 점수도 OK").

## generalization (ARTIFACT-GATED + STRUCTURAL)

phase18 6-페어 일반화는 **실 Pod sweep 이 생성·커밋한** `baseline/phase24_breakdowns.json`
에만 돈다(HIGH-4). 이 artifact 가 생기기 전엔 순수 게이트가 합성 입력을 **fabricate 하지
않는다** — 옛 `eval18_serial_baseline.json` 의 overall 을 tally 결과로 읽지 않고, breakdown 을
합성하지도 않는다. artifact 부재면:

```
SKIPPED (phase24 breakdown fixture absent)
```

를 출력하고 acceptance 가 "partial generalization skipped" 를 받는다.

artifact PRESENT 면 검사는 **STRUCTURAL not numeric**(MEDIUM-1):

- **success/elite 멤버**: deduction record 부재 OR 모든 record 의 `deviation ≤` 그 criterion
  tolerance(추적가능 within-tolerance) → PASS. **수치 ≥95 가 아니라 structural property.**
- **fault 멤버**: 같은 named criterion 에서 success 보다 **strictly 큰 shortfall**(같은
  criterion id, fault.deviation > success.deviation) → PASS(false-negative 방향).

수치 high-score(≈95-100) 관측은 **Task 3 Pod 체크포인트의 OBSERVATIONAL report** 이지 순수
게이트의 fail bound 가 아니다. unseen + above-cutoff sensitivity set 이 생긴 뒤에만 hard
gate 로 승격 가능 — 그 전까진:

```
SKIPPED (sensitivity set deferred — Pod-serial, see Task 3 checkpoint)
```

## pod-free vs Pod-serial 분리

| | 어디서 | 무엇 |
|---|---|---|
| **pod-free (이 게이트)** | `python evals/phase24/assert_gates.py` (exit 0 = PASS) | 합성 traceability / monotonicity / determinism / criterion-selection. 일반화는 artifact 부재 시 SKIPPED |
| **Pod-serial (Task 3)** | `sweep_phase15.py --pair-sequential` + sam deploy | 실 영상 sweep → `phase24_breakdowns.json` 생성·커밋, STRUCTURAL 일반화 실측, 수치 high-score OBSERVATION, cold-re-run selection. SERIAL only([[pipeline-not-concurrency-safe-eval-serial]]) |

## 실행

```bash
# pod-free 순수 게이트 (exit code 가 게이트 exit code — MEDIUM-3, 마스킹 없음)
cd backend && python3 evals/phase24/assert_gates.py

# 게이트 단위 테스트
cd backend && python3 -m pytest tests/test_phase24_gates.py -x -q
```

## 객관성 (D-06 / [[analysis-objectivity-no-human-scores]])

게이트는 사람 점수 라벨을 ground truth 로 절대 쓰지 않는다. 감점은 명명 편차 + 명명
규칙에서만 나온다. 합성 fixture 는 엔지니어링 기하(합성 각/notch)일 뿐 보유 영상에
curve-fit 한 타깃이 아니다(slope/cap/tolerance 재calibrate 금지).
