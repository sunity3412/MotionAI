---
phase: 24-transparent-deduction-scoring
plan: 05-A
subsystem: scoring
tags: [deduction-tally, measured-seed, engine-gate, low-alignment, false-green-test, gap-closure]
requires:
  - phase: 24, plan: 04
    provides: low_alignment_confidence apply-seam tally-eligibility + measured_deviations 전달
  - phase: 24, plan: 01
    provides: deduction_engine.tally, criteria_from_measured_deviations, criteria_for_fault
provides:
  - deduction_engine.tally 가 quantification unavailable 일 때도 measured-seed(정렬-독립 RTMW 각도 편차)를 소비해 granular 감점을 산출. dimension_overall_fallback 은 quant 불가 AND 활성 criterion 0(양쪽 substrate 빔)일 때만.
  - coverage_gap reach_substrate_unavailable_low_alignment (reach 칸 측정 불가 투명 노출, ND-06/07)
affects: [24-eval-gates-pod-resweep]
tech-stack:
  added: []
  patterns: [pure-function-routing, criterion-selection-before-fallback]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/deduction_engine.py
    - backend/tests/test_deduction_engine.py
    - backend/tests/test_pipeline_deduction_seam.py
    - backend/tests/test_phase24_gates.py
decisions:
  - "폴백 결정을 criterion 선택 뒤로 이동 — measured seed(정렬-독립)는 quant unavailable 에서도 살아 granular 감점(ND-01)"
  - "reach coverage_gap 은 activated 경로(각도 seed 존재)에서만 방출 — 빈-seed 폴백/legacy(None,None) 단일영상 오표기 방지(§3-2 binding)"
metrics:
  duration: ~45m
  completed: 2026-06-26
  tasks: 3
  files: 4
---

# Phase 24 Plan 05-A: measured-seed engine-gate fix Summary

`deduction_engine.tally()` 의 unavailable-fallback 게이트가 정렬-독립 measured-seed(RTMW 각도 편차)를 문 앞에서 폐기하던 결함을 닫았다 — 폴백 결정을 criterion 선택 *뒤로* 이동해, quantification 이 unavailable 이어도 측정 각도 seed 가 있으면 per-criterion granular 감점을 산출하고, 폴백은 quant 불가 AND 활성 criterion 0(양쪽 substrate 빔)일 때만 발화한다.

## What changed

### Task 1 — engine fix (`deduction_engine.py`, commit 6e10c66)
- `tally()` 구조를 `(1) unavailable-fallback → (2) criterion 선택 → (3) 감점` 에서 `(2) criterion 선택 → (1') 조건부 폴백 → (3) 감점` 으로 재배치 (24-05-FIX-DESIGN §3-2).
- 폴백 가드: `if quant_unavailable and not activated:` — 본문 로직/record 필드/rule_id(`quantification_unavailable_dimension_overall`)/final 산식(`max(0, round(dim))`) UNCHANGED.
- quant 불가 BUT activated(각도 seed 존재) 경로: 폴백을 건너뛰고 coverage_gaps 에 reach 칸 측정 불가 entry 1개(faultType=body_relative_reach, ruleId=`reach_substrate_unavailable_low_alignment`) append (ND-06/07 투명 추적성).
- 모듈 docstring 에 24-05 변경 의도 Korean 보강. slope/cap/tolerance/baseline 상수 미변경, numpy 외 import 0(순수 함수 유지).

### Task 2 — engine unit guards + reconcile (`test_deduction_engine.py`, commit a556d44)
- 신규 6종: CORE 회귀 가드(quant 불가+각도 seed → granular, 폴백 아님) / 빈-seed 폴백 보존 / legacy(None,None) 폴백 보존 / 단조성(ND-07) / reach coverage_gap 추적성(ND-06) / 결정성(to_dict 동일).
- 기존 `test_unavailable_falls_back_not_100`·`test_unavailable_emits_traceable_record` 를 빈-seed(`_measured()` + `_ctx([])`) 폴백 계약으로 reconcile.

### Task 3 — seam false-green 교정 + reach gap 신규 (`test_pipeline_deduction_seam.py`, commit bfcadf6)
- low_alignment 4종 `_quant("available")` → `_quant("unavailable")` 로 교정 — production wiring(frame_pairs=[] → quantification UNAVAILABLE)과 일치(§2-4 false-green 교훈).
- `test_low_alignment_measured_deduction_applied`: unavailable 에서도 leg_extension granular record(fix 핵심 검증).
- `test_low_alignment_clean_geometry_not_applicable` → `test_low_alignment_empty_seed_unavailable_fallback` 로 재정의: 빈 seed → dimension_overall_fallback 1개 + fallback flag, 위양성 measured fabricate 0, status=applied(TRUST-08).
- 신규 `test_low_alignment_unavailable_emits_reach_coverage_gap`: quant 불가 + 각도 seed → granular 감점 유지하면서 reach 칸 측정 불가를 coverageGaps 로 투명 노출.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test reconcile] phase24 gate `_fallback_breakdown` 빈-seed 교정**
- **Found during:** Task 3 verification (Phase 24 + 20/23 targeted suite)
- **Issue:** `test_phase24_gates.py::_fallback_breakdown` 가 `leg=40` seed + 무릎 굽음 diff 로 폴백을 기대 — fix 후 비-빈 각도 seed 는 granular 경로로 가 폴백 record 0개 → `test_traceability_gate_passes_fallback_record` FAIL. 이는 Task 1 변경이 직접 유발한 reconcile(엔진/seam 테스트와 동일 class)이고 verification suite 의 일부라 수정 필수.
- **Fix:** `_fallback_breakdown` 를 `_tally({}, _ctx([]), ..., quantification=_unavailable_quant())` 빈-seed 폴백 계약으로 교정.
- **Files modified:** `backend/tests/test_phase24_gates.py` (plan files_modified 목록 밖 — verification 의존)
- **Commit:** 2253e77

### Design-vs-test inconsistency 해소 (surfaced)

24-05-FIX-DESIGN 내부 불일치 1건을 §3-2(엔진 spec, Task 1 "정확히 구현·재해석 금지" 가 binding)를 따라 해소:
- §5-2 item 8 + §4 matrix 는 "low_alignment reach-only(md={}) → dimension_overall_fallback + reach coverage gap 포함" 을 기대.
- 그러나 §3-2 코드는 reach coverage gap 을 **activated 경로(각도 seed 존재)에서만** append 하고, 빈-seed 폴백 경로는 그 전에 return 한다. 폴백 경로에 reach gap 을 넣으면 ruleId 가 `..._low_alignment` 인데 legacy(quantification=None, md=None) 단일영상 경로(low alignment 와 무관)까지 오표기되므로 §3-2 의 scoping 이 정당.
- 해소: 신규 seam 테스트를 achievable 한 activated 경로(unavailable + 각도 seed → granular + reach gap)로 구현하고, reach-only 빈-seed 케이스는 `test_low_alignment_empty_seed_unavailable_fallback` 이 폴백 shape(reach gap 없음)을 검증. 두 테스트가 비중복으로 ND-06/07 + 폴백 계약을 모두 커버. 코드 NOT 변경(§3-2 그대로).

### Behavior shift (의도된 결과 — belle 재검증 필요)

fix 후 low_alignment fault 의 final 은 `dimension_overall`(예: power-spin 72) 이 아니라 granular tally `100−Σ(각도 감점)` 로 바뀐다(ND-01/05 의도된 결과). Pod 재-sweep 으로 elite/success 95-100 유지(위양성 0) + fault 변별 유지 + 일반화 게이트(`assert_gates.py`) 통과 재확인 필요 — orchestrator-owned 체크포인트. kip-up FP 는 비-각도형 결함이라 이 fix 로 안 풀린다((B) Gemini 경로 별도 plan).

## Verification (로컬 — pod/GPU 불필요)

| Gate | 결과 |
|---|---|
| GATE 1 — 직접 영향 suite (`test_deduction_engine` + `test_pipeline_deduction_seam`) | 48 passed |
| GATE 2/3 — Phase 24 + 20/23 targeted (deduction_engine + phase24_gates + deduction_seam + vision_veto + assert_stillframe_veto_gate + pipeline_vision_gate) | 143 passed |
| GATE 4 — band grep (`apply_downward_cap\|SEVERITY_CAP\|capApplied`) over shared/python + functions | 0 matches |
| 순수성 — deduction_engine.py import | dataclasses + numpy + relative ipsf_criteria 만 (boto3/Gemini/network/firestore 0) |
| 구조 가드 — criteria_from_measured_deviations index < `quant_unavailable and not activated` index | PASS |

### Pre-existing failures (out of scope, NOT caused by this change)
전체 backend suite 의 15개 파일(33 failed)은 pre-existing — pre-work commit ec58618 에서 동일하게 33 failed/162 passed (HEAD 와 byte-parity). 전부 phase06(body comparison) / phase08·gemini model env / pipeline phase8·9 / gemini wiring / height-scale semantics 도메인으로 deduction routing 변경과 무관. (별도 collection-error spike/smoke 11종도 pre-existing `backend`/`fixtures` 모듈 path 이슈.) deferred — 본 plan scope 아님.

## Commits

- `6e10c66` feat(24-05): tally() 폴백 게이트를 criterion 선택 뒤로 이동 + reach coverage_gap
- `a556d44` test(24-05): 엔진 measured-seed 소비 회귀 가드 6종 + unavailable 폴백 reconcile
- `bfcadf6` test(24-05): low_alignment seam false-green 교정 + reach coverage gap 신규 테스트
- `2253e77` test(24-05): phase24 gate _fallback_breakdown 빈-seed 폴백 reconcile (deviation)

## Self-Check: PASSED
- 4 modified files 존재 확인 (FOUND)
- 4 commits 존재 확인 (FOUND)
