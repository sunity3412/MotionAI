---
phase: 24-transparent-deduction-scoring
plan: 05 (DESIGN — belle 검토용, 미실행)
subsystem: scoring
tags: [deduction-tally, measured-seed, engine-gate, low-alignment, gap-closure, false-green-test]
status: DESIGN — belle 방향 확인 대기 (코드 미수정)

# Dependency graph
requires:
  - phase: 24, plan: 04
    provides: low_alignment_confidence apply-seam tally-eligibility + measured_deviations 전달 (이 fix 의 전제 — apply seam 은 이미 seed 를 정확히 넘김)
  - phase: 24, plan: 01
    provides: deduction_engine.tally, criteria_from_measured_deviations, criteria_for_fault
provides:
  - deduction_engine.tally 가 quantification unavailable 일 때도 measured-seed(정렬-독립 RTMW 각도 편차)를 소비해 granular 감점을 산출 (dimension_overall_fallback 은 양쪽 substrate 가 모두 빈 경우에만)
affects: [24-eval-gates-pod-resweep]
---

# Phase 24 Plan 05 (DESIGN): measured-seed 가 엔진 게이트에서 버려지는 결함 수정

> **상태: 설계안. 코드 미수정.** belle 의 (A)(B) 방향 확인 후 `/gsd-quick` 또는 `/gsd-execute-phase` 로 실행.

---

## 1. 한 줄 요약

24-04 가 **apply seam** 두 곳을 고쳐 low_alignment 를 tally-eligible 로 만들고 measured_deviations 를 전달했지만, **엔진(`deduction_engine.tally`) branch (1)** 가 `quantificationStatus == "unavailable"` 이면 그 measured_deviations 를 **쳐다보지도 않고 폐기**한다. 한 레이어 빠진 미완성 fix. 이 plan 은 엔진 게이트를 고쳐 측정-seed 가 살아서 granular 감점을 내게 한다.

---

## 2. Root Cause (전부 로컬 산출물로 확증 — pod 불필요)

### 2-1. 증상 (`backend/evals/phase24/baseline/phase24_breakdowns.json`, 6/26 02:50 재-sweep)

fault clip 전부 `fallback=quantification_unavailable`, record 1개(`dimension_overall_fallback`)뿐. granular 측정-감점 0개.

| clip | overall | fallback | records | activated |
|---|---|---|---|---|
| power-spin fault | 72 | quantification_unavailable | 1 | dimension_overall_fallback |
| peter-pan fault | 79 | quantification_unavailable | 1 | dimension_overall_fallback |
| elbow-twist-sister fault | 59 | quantification_unavailable | 1 | dimension_overall_fallback |
| pdshape fault | 60 | quantification_unavailable | 1 | dimension_overall_fallback |
| kip-up fault | 100 | quantification_unavailable | 1 | dimension_overall_fallback |
| (peter-pan/kip-up success) | 100 | None | 0 | — (not_applicable, 정상) |

### 2-2. 인과 체인

1. **collect bail** — `_collect_vision_fault_context` (`app.py:1829-1833`): fault clip 은 자세가 흐트러져 DTW 정렬 신뢰도 낮음 → `alignment.adoption == "low_alignment_confidence"` → `return _ctx("low_alignment_confidence", frame_pairs=[])`. **frame_pairs 가 빈 채로** ctx 반환.

2. **quantification unavailable** — 메인 seam (`app.py:3281-3303`): `selected_pair = ctx.selected_frame_pairs[0] if ... else None` → frame_pairs=[] 이므로 `None` → `_build_vision_quantification_result(selected_frame_pair=None)` → **`quantificationStatus="unavailable"`**.

3. **measured_deviations 는 살아있음** — 같은 seam: `_build_deduction_measured_deviations(angles=angles, profile=profile, ...)`. angles/profile 은 **RTMW 에서 항상 가용** (frame pair 와 무관) → fault clip 은 `{leg_extension, arm_extension, line}` 등 **NON-EMPTY** 각도 편차를 들고 apply 에 도달.

4. **엔진이 문 앞에서 폐기** — `deduction_engine.tally` branch (1) (`deduction_engine.py:162-184`):
   ```python
   status = getattr(quantification, "quantificationStatus", None)
   if quantification is None or status == "unavailable":
       ...                                        # md 는 line 157 에서 계산됐지만
       return DeductionBreakdown(records=(fallback_record,), ...)   # 쳐다보지도 않고 early-return
   ```
   measured_deviations(`md`)는 함수 진입부(line 157)에서 이미 계산됐으나 branch (1) 은 참조하지 않는다. 측정-seed 전량 폐기 → `dimension_overall_fallback` 한 덩어리.

### 2-3. 핵심 진단 — 독립 substrate 두 개의 혼동

| substrate | 출처 | 정렬 의존성 | low_alignment 시 |
|---|---|---|---|
| `quantification` (reach/notch 칸 기하) | frame-pair keypoints | **의존** (DTW 정렬된 still-pair 필요) | unavailable (정당) |
| `measured_deviations` (IPSF 각도 편차) | RTMW joint angles + profile | **독립** (관절각은 정렬 무관) | **available, 멀쩡** |

엔진이 둘을 한 덩어리로 취급한다. `low_alignment` = "정렬 실패 = reach 기하 측정 불가" 이지 "각도 측정 불가" 가 아닌데, branch (1) 가 reach 기하 부재를 이유로 **각도 편차까지 같이 버린다.** 이것이 24-04 의 설계 의도(RTMW 측정 편차는 정렬-독립 → 감점해야 함)와 정면 충돌한다.

### 2-4. 왜 24-04 가 통과하면서도 실패했나 (false-green test)

24-04 테스트 `test_low_alignment_measured_deduction_applied` (`test_pipeline_deduction_seam.py:308-338`) 는 `quantification=_quant("available")` 를 넘긴다(line 320). 심지어 line 335 는 `assert "dimension_overall" not in sources  # available quant → fallback 아님` 으로 **available 일 때만 fallback 을 피한다는 사실을 본인이 명시**한다. 그러나 production low_alignment 경로는 frame_pairs=[] → **`unavailable`** quantification 을 만든다. 테스트 fixture 가 production wiring 과 갈라져 branch (1) 을 한 번도 실행하지 않았고, 그래서 196개 테스트가 green 이면서도 실제 sweep 은 전량 fallback 으로 붕괴했다.

> **교훈(테스트 게이트 강화):** low_alignment seam 테스트의 quantification fixture 는 production 과 동일하게 `unavailable` 이어야 한다. 이 fix 의 테스트 항목에 포함.

---

## 3. Fix 설계

### 3-1. 변경 위치 (단일 파일, 순수 함수)

`backend/shared/python/sunity_shared/analysis/deduction_engine.py` 의 `tally()` 한 함수. numpy 외 의존 0 유지 — boto3/Gemini/네트워크 import 없음, 결정적. **apply seam(app.py)·collect(vision_veto.py)·thresholds·slope·cap 전부 UNCHANGED** — 이것은 라우팅/소비 결함 fix 이지 재calibration 이 아니다([[calibration-source-hard-gate]]).

### 3-2. 구조 변경 — 폴백 결정을 criterion 선택 *뒤로* 이동

현재: `(1) unavailable-fallback → (2) criterion 선택 → (3) 감점`.
변경: `(2) criterion 선택 먼저 → (1') 폴백은 "활성 criterion 0 AND quant unavailable" 일 때만 → (3) 감점`.

```python
def tally(quantification, fault_context, *, dimension_overall, measured_deviations,
          dimension_scores, baseline_kind, criterion_groups=ipsf_criteria.CRITERION_GROUPS):
    md = measured_deviations or {}
    crit_by_id = {c["id"]: c for c in criterion_groups}
    coverage_gaps = []

    status = getattr(quantification, "quantificationStatus", None)
    quant_unavailable = quantification is None or status == "unavailable"

    # (2) CRITERION SELECTION — measured seed 는 정렬-독립이므로 먼저 평가.
    seeded = ipsf_criteria.criteria_from_measured_deviations(md)
    pointed = set()
    differences = _supported_differences(fault_context)
    for diff in differences:
        res = ipsf_criteria.criteria_for_fault(_fault_key_for(diff), diff, md)
        if isinstance(res, ipsf_criteria.CoverageGap):
            coverage_gaps.append(_gap_to_dict(res)); continue
        pointed.update(res)
    activated = set(seeded) | pointed
    gemini_silent = not differences
    if activated & {"leg_extension", "arm_extension"} and "line" in activated:
        activated.discard("line")

    # (1') UNAVAILABLE FALLBACK — quant 불가 AND 측정/지목 seed 전무일 때만 (양쪽 substrate 빔).
    if quant_unavailable and not activated:
        ... 현재 branch (1) 본문 그대로 (dimension_overall_fallback) ...
        return DeductionBreakdown(records=(fallback_record,), ...,
                                  fallback="quantification_unavailable")

    # quant 불가 BUT 각도 seed 있음 → reach/notch substrate 측정 못 했음을 coverage gap 으로 명시
    # (honest, ND-06/07). reach criterion 은 _notch_shortfall 가 notches 부재로 None → 자연 honest-0.
    if quant_unavailable:
        coverage_gaps.append({
            "faultType": "body_relative_reach", "reason": "quantification_unavailable",
            "bodyPart": "reach", "faultState": None,
            "keypointSet": "body_relative_reach",
            "ruleId": "reach_substrate_unavailable_low_alignment",
        })

    # (3)-(8) per-criterion 감점 — 현재 로직 그대로.
    records = [...]
    final = max(0, round(_BASELINE + sum(r.points for r in records)))
    fallback = "gemini_silent" if (gemini_silent and records) else None
    return DeductionBreakdown(baseline=int(_BASELINE), records=tuple(records),
                              final=final, coverage_gaps=tuple(coverage_gaps), fallback=fallback)
```

### 3-3. 왜 reach criterion 은 별도 처리가 필요 없나

- `_build_deduction_measured_deviations` 는 `quantification.bodyRelativeNotches` 가 truthy 일 때만 `md["body_relative_notches"]` 를 넣는다 → quant unavailable 이면 md 에 notch 키 부재 → `criteria_from_measured_deviations` 가 reach criterion 을 seed 하지 않는다.
- 설령 활성화돼도 `_criterion_deduction` → `_notch_shortfall(quantification, crit)` 가 `bodyRelativeNotches` None 으로 `None` 반환 → 감점 record 미방출(honest 0).
- 따라서 reach 는 자연스럽게 0 기여. 우리는 그 사실을 **coverage gap 으로 노출**해 "정렬이 낮아 reach 칸은 측정 못 했음" 을 리포트가 투명하게 보이게만 한다(추적성, ND-06/07).

---

## 4. Edge-case 행렬 (회귀 0 검증)

| 경로 | quantification | md | 기대 결과 | 비고 |
|---|---|---|---|---|
| **low_alignment 각도 fault** | unavailable | {leg/line:>tol} | **granular records** (leg_extension 등), final=100−Σ | ← 이 fix 의 타깃 |
| low_alignment reach-only fault | unavailable | {} | dimension_overall_fallback + coverage gap | 각도 부재 → 폴백 정당(honest 한계) |
| low_alignment 깨끗 | unavailable | {} | dimension_overall_fallback | 현 not_applicable 과 final 동일(=dim_overall) — §6 주의 |
| candidate_verdict (정렬 OK) | available | {…} | 변동 없음 (이미 동작) | 회귀 0 |
| no_fault 깨끗 | available | {} | not_applicable | 회귀 0 |
| **legacy 단일영상** | None | None | dimension_overall_fallback | `app.py:2167` 경로 — 보존 |

핵심: 폴백은 **`quant_unavailable AND not activated`** 일 때만. legacy(None,None) 와 reach-only 는 폴백 유지, 각도 seed 가 있을 때만 granular 로 전환.

---

## 5. 테스트 계획 (전부 순수 단위 — pod 불필요)

### 5-1. 엔진 직접 단위 (`backend/tests/test_deduction_engine*.py`)
1. `tally(quant=unavailable, md={leg_extension:30})` → leg_extension record 존재, `fallback != "quantification_unavailable"`, final<100. **(핵심 회귀 가드)**
2. `tally(quant=unavailable, md={})` → dimension_overall_fallback 유지(폴백 보존).
3. `tally(quant=None, md=None)` → 폴백 유지(legacy 보존).
4. **단조성:** `md={leg:20}` 의 감점 < `md={leg:40}` 의 감점(ND-07).
5. quant unavailable + 각도 seed → coverage_gaps 에 `reach_substrate_unavailable_low_alignment` 포함(추적성).
6. 결정성: 동일 입력 2회 호출 → byte-동일 breakdown.

### 5-2. seam fixture 수정 (false-green 차단)
7. `test_low_alignment_measured_deduction_applied` 등 low_alignment seam 테스트의 `_quant("available")` → **`_quant("unavailable")`** 로 교정(production wiring 일치). 교정 후에도 leg_extension record 가 나와야 한다(= 이 fix 가 통과시켜야 green). line 335 의 `"dimension_overall" not in sources` 단언은 **fix 후에도 유지**(각도 seed 가 살아 dimension_overall 폴백을 안 탐).
8. 신규 seam 테스트: low_alignment + unavailable quant + reach-only(md={}) → dimension_overall_fallback + coverage gap(honest 한계 명시).

> 7번이 이 plan 의 안전망 핵심: fixture 를 production 과 일치시키면 fix 전에는 RED(현재 폐기), fix 후 GREEN. 이게 없으면 같은 false-green 이 재발한다.

---

## 6. belle 판단/검증 필요 사항 (실행 전 확인)

1. **점수 출처 전환의 의미** — fix 후 low_alignment fault 의 final 은 `dimension_overall`(예: power-spin 72) 이 아니라 **granular tally `100−Σ(각도 감점)`** 로 바뀐다. 두 값은 다를 수 있다. 이는 Phase 24 ND-01/ND-05(tally 가 점수 source-of-truth, dimension_overall 은 degenerate 폴백) 의 **의도된 결과**지만, pod 재-sweep 으로 아래를 반드시 재확인:
   - elite/success clip 95-100 유지 (위양성 0)
   - fault clip 변별 유지 (moderate, success 와 분리)
   - 단조성·결정성·일반화 게이트(`assert_gates.py`) 통과
2. **kip-up 은 이 fix 로 안 풀린다** — kip-up fault 는 비-각도형 결함이라 md 각도 키가 비어(extension/line 편차 없음) §4 의 "reach-only" 행처럼 여전히 폴백된다. kip-up FP 는 **(B) Gemini 시각 경로** 숙제로 분리 확정(별도 plan). 이 plan 의 scope 아님.
3. **객관성 불변** — measured seed 만 점화하고 `supported_differences=[]` 이라 `criteria_for_fault` 는 0 record. Gemini-located fault fabricate 없음([[analysis-objectivity-no-human-scores]]). 사람 점수 라벨 미주입.

---

## 7. Scope / Non-goals

- **In:** `deduction_engine.tally` branch 재구조화 + coverage gap 1종 추가 + low_alignment seam 테스트 fixture 교정 + 엔진 단위 테스트 6종.
- **Out:** slope/cap/tolerance 재calibration(금지), collect-side bail 로직, assess_alignment_confidence threshold, kip-up/(B) Gemini 경로, apply seam 라우팅(24-04 에서 이미 완료).
- **검증:** 로컬 = 단위 테스트 + band grep 0. 실증 = pod 1회 재-sweep → `phase24_breakdowns.json` 재생성 → §6 게이트 → belle verification.

---

## 8. 실행 순서 (belle 승인 후)

1. `/gsd-quick` 또는 `/gsd-execute-phase 24` 진입.
2. 엔진 fix (commit) → 엔진 단위 테스트 (commit) → seam fixture 교정 (commit).
3. 로컬 게이트: Phase 24 + 20/23 타깃 suite green, band grep(`apply_downward_cap|SEVERITY_CAP|capApplied`) = 0.
4. 로컬 commit 후 GitHub push([[gsd-pod-work-push-first]]).
5. pod ON → 재-sweep → `assert_gates.py` → belle 에게 §6 결과 재-present.
6. belle verification 통과 시 pod Stop.

---
*Phase: 24-transparent-deduction-scoring · Plan 05 DESIGN · 2026-06-26 · 코드 미수정, belle 검토 대기*
