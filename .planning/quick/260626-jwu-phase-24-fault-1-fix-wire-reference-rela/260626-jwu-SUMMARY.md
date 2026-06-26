---
phase: 24-transparent-deduction-scoring
plan: 260626-jwu (quick)
subsystem: scoring
tags: [deduction-engine, reference-relative, per-joint-deviation, granular, kismam-calibration, cross-exclusion]

requires:
  - phase: 24-transparent-deduction-scoring
    provides: "투명 감점-합산 엔진(deduction_engine.tally) + ipsf_criteria CRITERION_GROUPS + 24-05 measured-seed-survives-unavailable 게이트"
provides:
  - "reference_relative per-joint 각도 criterion (angle_vs_reference__{joint}) 8개 — 미등록 동작 granular seed"
  - "deduction_engine reference_relative over_target 분기 (baseline 0, over=max(0,dev-tol))"
  - "2-layer cross-exclusion (seed-stage expects_extension gate + engine joint_keys discard) — ipsf_absolute double-count 차단"
  - "seam 배선: per_joint_deviation(정은지 대비) → md[angle_vs_reference__{joint}]"
affects: [phase-24-pod-sweep, mode1-headline-scoring]

tech-stack:
  added: []
  patterns:
    - "프로그램 생성 criterion (JOINT_KEYS 순회 → N joint-keyed criteria, 손-작성 dict 금지)"
    - "2-layer cross-exclusion (builder profile-aware + engine profile-independent joint_keys)"

key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/ipsf_criteria.py
    - backend/shared/python/sunity_shared/analysis/deduction_engine.py
    - backend/functions/pipeline/app.py
    - backend/tests/test_deduction_engine.py
    - backend/tests/test_pipeline_deduction_seam.py

key-decisions:
  - "N joint-keyed criteria (per-joint family 아님) — criterion=1 record=1 모델 정합 + profile 없이 cross-exclusion 표현 가능"
  - "calibration = kismam 재사용(tol 20° _ANGLE_TOLERANCE_DEG + _SLOPE + _ANGLE_CAP) — 새 임계 picking 0"
  - "keypoint_set=None — router 대상 아님(seed 전용), partition assert(mapped∪gap==8) 불변"
  - "0/음수 deviation 미방출(md 슬림) — 엔진 tol gate 가 self-compare 0 도 거름"

patterns-established:
  - "reference_relative over_target: baseline=0(정은지 대비 0° 목표), measured_value=편차, unit=deg"
  - "seed-stage cross-exclusion이 line(collective) 차단을 담당(엔진은 explicit joint_keys만 보증)"

requirements-completed:
  - "24-07-FIX-①"

duration: 38min
completed: 2026-06-26
---

# Phase 24 Plan 260626-jwu (quick): reference-relative granular seed 배선 Summary

**미등록 동작(인식기 미등재 → expects_extension 전부 False → ipsf_absolute seed 빔)에서 정은지 대비 per-joint 각도 편차를 deduction 엔진 granular seed로 배선 — dimension_overall_fallback(단일 score) 대신 angle_vs_reference__{joint} 항목별 감점 내역 실현**

## Performance

- **Duration:** 38 min
- **Started:** 2026-06-26
- **Completed:** 2026-06-26
- **Tasks:** 2 (각 TDD RED→GREEN)
- **Files modified:** 5

## Accomplishments

- ipsf_criteria: JOINT_KEYS(8) 순회로 `angle_vs_reference__{joint}` reference_relative criterion 8개 프로그램 생성, `_MEASURABLE_SEED_IDS`에 합류 → `criteria_from_measured_deviations`가 seed
- deduction_engine: `_criterion_deduction`에 reference_relative over_target 분기(baseline 0.0, over=max(0,dev−tol), unit deg) 추가 — `_IPSF_ABSOLUTE_BASELINE`(180) 경로와 분리
- deduction_engine: tally HIGH-5 확장 cross-exclusion — active leg/arm/split의 claimed joint_keys에 대해 동일관절 reference_relative discard(double-count 0)
- pipeline seam: `_build_deduction_measured_deviations`가 `reference_dtw_match`+`reference_angles`로 `per_joint_deviation` 산출 → expects_extension 미소유 관절만 `angle_vs_reference__{joint}` 방출 (seed-stage cross-exclusion이 line 포함 차단)
- belle granular wish("−X 왼무릎 −Y 오른팔꿈치") 실현 경로 완성

## Task Commits

각 task TDD 2-commit(RED test → GREEN feat):

1. **Task 1 RED: engine 단언** - `abef36a` (test)
2. **Task 1 GREEN: criterion + 엔진 분기 + cross-exclusion** - `811e3f9` (feat)
3. **Task 2 RED: seam 단언** - `6682c63` (test)
4. **Task 2 GREEN: seam 배선** - `c958ff3` (feat)

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py` - reference_relative 8 criteria 프로그램 생성 + `_MEASURABLE_SEED_IDS` 확장 (skeleton.JOINT_KEYS import)
- `backend/shared/python/sunity_shared/analysis/deduction_engine.py` - `_criterion_deduction` reference_relative 분기 + tally cross-exclusion 확장
- `backend/functions/pipeline/app.py` - `_build_deduction_measured_deviations` reference-relative seed 블록 + 호출부(3319) reference_dtw_match/reference_angles thread
- `backend/tests/test_deduction_engine.py` - 6 신규 케이스 + criterion 표 단언 갱신(5 core + 8 reference_relative)
- `backend/tests/test_pipeline_deduction_seam.py` - 5 신규 seam 케이스(합성 MotionMatch identity path)

## Decisions Made

- **N joint-keyed criteria 채택** (per-joint family 아님): criterion=1 record=1 모델에 정합, 엔진 cross-exclusion을 profile 없이 표현 가능, id가 관절을 운반.
- **calibration 기존 재사용**: tol `_ANGLE_TOLERANCE_DEG`=20° + `_SLOPE`(kismam._PENALTY_PER_DEG) + `_ANGLE_CAP`. 새 tolerance/slope 상수 도입 0 ([[calibration-source-hard-gate]] 준수).
- **2-layer cross-exclusion**: seed-stage(builder, profile 보유)가 expects_extension True 관절은 reference_relative md 자체를 안 만든다(line/leg/arm/split 전부 expects_extension 파생이므로 정확). 엔진-stage는 active leg/arm/split의 explicit joint_keys로 추가 discard(profile-독립 + testable).
- **0/음수 deviation 미방출**: md 슬림화. 엔진 tol gate(over≤0 skip)가 self-compare 0을 거름 — 위양성 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 기존 criterion-count 테스트 갱신**
- **Found during:** Task 1 (criterion 표 확장)
- **Issue:** `test_criterion_groups_five_criteria`가 정확히 5 criteria(set 동등)를 단언 — 설계상 8 reference_relative criterion 추가 시 필연적으로 실패.
- **Fix:** `test_criterion_groups_core_plus_reference_relative`로 갱신: 5 core ⊆ ids 보존 단언 + reference_relative 8개(== len(JOINT_KEYS)) 구조/태그 단언. curve-fit 아님(개수·태그 구조만).
- **Files modified:** backend/tests/test_deduction_engine.py
- **Verification:** test_deduction_engine.py 36 passed
- **Committed in:** abef36a (RED) / 811e3f9 (GREEN)

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking — 설계 변경에 따른 기존 테스트 갱신)
**Impact on plan:** 설계가 명시한 criterion 추가의 직접 귀결. scope creep 없음. 새 contract 키 0(DeductionRecord/models/analysis.ts 불변 — test_contract_lockstep green).

## Issues Encountered

- **로컬 python 기본값 = 3.14.5** (repo 타겟 3.12). 전체 backend 스위트에 11개 collection error(`No module named 'backend'` — backend.-prefixed import 쓰는 smoke 테스트) + 50개 pre-existing 실패(test_pipeline_geminid_wiring `augment_low_confidence` 등 무관 서브시스템)가 존재. **pristine 트리(ec58618) 비교로 검증**: mine 50 vs pristine 51 실패, "in MINE but NOT pristine" diff = 비어 있음 → 내 변경이 도입한 신규 실패 0. 차이 1건은 pre-existing flaky 테스트(`test_reads_keypoints_3d_confidence_mean`)가 내 run에서 우연히 통과. 모두 본 task scope 밖(deferred — 인프라/python-version 이슈).

## Gate Results (constraints)

1. **`pytest tests/test_deduction_engine.py tests/test_pipeline_deduction_seam.py -q`** → green (36 + 23 = 59 passed).
2. **Phase 24 + adjacent** (`test_deduction_engine` + `test_pipeline_deduction_seam` + `test_vision_veto` + `test_pipeline_vision_gate` + `test_phase24_gates`) → **146 passed**.
3. **band grep** (`apply_downward_cap|SEVERITY_CAP|capApplied` over backend/shared/python + backend/functions, 주석 제외) → **0**.
4. **Engine purity** (`import boto3|firebase|requests|google` over ipsf_criteria.py + deduction_engine.py) → **0** (numpy + skeleton[순수] 만).
5. **calibration**: 새 tolerance/slope 상수 도입 0 — `_ANGLE_TOLERANCE_DEG`/`_SLOPE`/`_ANGLE_CAP` 재사용만.
6. **contract mirror**: DeductionRecord/models 키 변경 0 → app/src/types/analysis.ts 변경 불요(test_contract_lockstep green).

## Next Phase Readiness

- **score-shift의 pod 재검증은 본 task 범위 외 — 후속 sweep 필수**: elite/success 95-100 유지, fault 변별 유지, 일반화 게이트(assert_gates.py), self-compare 0. 미등록 동작 Mode1 헤드라인이 dimension_overall(72 등 단일 score) → reference_relative per-joint granular 합산으로 바뀌므로 점수 분포 재확인 필요.
- 결함 ② (Gemini visibility/kip-up FP) 및 recognizer/IPSF 동작 등록(Phase 15 도메인 난제)은 별도.

## Self-Check: PASSED

- 5 modified files 모두 FOUND.
- 4 commits(abef36a, 811e3f9, 6682c63, c958ff3) 모두 FOUND.

---
*Phase: 24-transparent-deduction-scoring*
*Completed: 2026-06-26*
