---
phase: quick-260831-isk
plan: 01
subsystem: scoring
tags: [deduction-engine, vision-veto, split-angle, kip-up, tolerance]

requires:
  - phase: quick-260831-kipup-diagnosis
    provides: "진단 정본 DIAGNOSIS.md — vision tol 이중 적용이 dev==tol 경계 결함을 지움 + 사전 박제 예측(fault 80 < correct 100)"
provides:
  - "_criterion_deduction vision_sourced tol-bypass — vision-sourced reference_relative 편차는 tol 재적용 없이 전량 감점(over = dev)"
  - "kip-up 페어 스윕 방향 FAIL(fault 100 = correct 100) 수리 — 방향 복원 fault 80 < correct 100"
  - "vision tol-bypass 단위 테스트 4건 + 260831 실 verdict fixture 1건"
affects: [scoring, phase25-eval, pair-sweep, kip-up]

tech-stack:
  added: []
  patterns: ["source-조건부 tol: vision-sourced 는 support 게이트가 노이즈 게이트(tol 생략), geometry-sourced 는 무차별 측정 마진(tol 유지)"]

key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/deduction_engine.py
    - backend/tests/test_deduction_engine.py

key-decisions:
  - "A안 채택(플랜 확정): _criterion_deduction 키워드 인자 vision_sourced(기본 False) — md dict 계약 무변경, geometry 경로 byte-불변"
  - "test_record_moment_engraving.py 무접촉 — deviation 수치 미박제 실측 확인(record 존재 단언만)"
  - "test_vision_measured_split_emits_source_vision 키 형상 단언을 cap-인지 helper 로 전환 — 플랜 미열거 7번째 사이트, 동일 규율(정당화 주석) 적용"

patterns-established:
  - "vision-sourced tol-bypass: record.source 결정 마커(vision_measured dict)를 tol 분기에도 재사용 — source 판정 단일 진실"

requirements-completed: []

duration: 7min
completed: 2026-08-31
---

# Quick 260831-isk: vision-sourced tol 재적용 제거 (kip-up 방향 FAIL 수리) Summary

**vision 이 지지한 split 편차에 tol(20°) 재적용을 제거(over = dev)해 kip-up 페어 스윕 방향 FAIL(fault 100 = correct 100)을 수리 — 단일 함수 + 단일 call site, 새 튜닝 상수 0**

## Performance

- **Duration:** 7 min
- **Started:** 2026-08-31T04:39:16Z
- **Completed:** 2026-08-31T04:46:12Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- `_criterion_deduction` 에 `vision_sourced: bool = False` 키워드 인자 추가, reference_relative/over_target 분기에서 `over = d if vision_sourced else max(0.0, d - tol)`. 호출부(단일 call site)는 `vision_sourced=cid in vision_measured` 전달 — record 의 `source="vision"` 을 결정하는 것과 같은 마커라 판정 진실이 하나다.
- DIAGNOSIS 사전 박제 예측과 산술 일치 실증: dev 20°(kip-up 재현) → raw 24.0(1.2×20) → per-record cap → points **-20.0**, 단독 record final **80**. correct 상당(supported_differences 0건) → record 0, final 100 무변화. **방향 복원: fault 80 < correct 100.**
- 260831 로컬 재현 verdict 를 순수 dict fixture 로 박제(Gemini 호출 0): 명시 각도쌍 student 145°/reference 165° → 산술 편차 20° → -20.0. severity 는 fixture 필드로만 존재(ND-01 준수 — 산식 미사용).
- 결함을 박제했던 프로덕션 재현 테스트(`test_phase25_kipup_real_cache_doc_injects_split_deviation`, "dev 20==tol → dead-zone → final 99")를 뒤집어 정정: split record 방출, final **79**(shoulder -0.7 + split -20.0, 실행 집계캡 40 안).

## Task Commits

1. **Task 1: vision-sourced tol-bypass 구현 (RED→GREEN)**
   - RED `b35e2512` (test): 신규 4테스트 — 3 FAIL(예상 사유 그대로: dead-zone/over-tol) / geometry 대조 1 PASS
   - GREEN `42547f7a` (feat): deduction_engine.py 수정 후 4/4 PASS
2. **Task 2: 기존 기대값 정정 + 실 verdict fixture** - `b23d9e2a` (test)
3. **Task 3: 전체 무회귀 + 게이트** - 코드 변경 없음(검증 실행만)

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/deduction_engine.py` — `_criterion_deduction` vision_sourced tol-bypass + 단일 call site 전달. ipsf_absolute 분기·DORMANT critical 분기·vision_veto.py 무접촉.
- `backend/tests/test_deduction_engine.py` — 신규 5테스트(tol-bypass 4 + 실 verdict fixture 1), 기존 기대값 7사이트 정정(전건 `quick-260831-isk` 정당화 주석).

## 점수 이동 예고 (08-09 교훈 — 의무 조항)

- **영향 범위:** 현행 vision 주입은 `split_angle` 뿐 — `vision_measured` dict 의 유일 키(플래너 실측). 다른 criterion 의 점수 경로는 코드상 도달 불가.
- **이동 방향:** vision-supported split 결함의 감점 발화 문턱이 tol 20°에서 **0°**(support 게이트만)로 내려간다. 종전 dead-zone(1~20°) 케이스가 새로 감점되고, tol 초과 케이스도 deviation 이 over-tol 대신 전량이라 감점이 커진다(대부분 per-record cap -20 포화).
- **예상 이동:**
  - kip-up fault 상당(vision split 편차 20°): **100 → 약 80** (DIAGNOSIS 사전 박제, 단위 fixture 로 실증).
  - correct 영상(supported_differences 0건): **무변화** (support 게이트가 그대로 입구).
  - split 을 vision 이 짚지 않는 동작: **무변화**.
  - geometry 채점 전 경로(geometric md 실재): **byte-불변** (기본값 False, 기존 geometric 테스트 무수정 PASS).
- **안정성:** 모델 세대의 크기 추정 드리프트(50°↔20°)는 per-record cap(-20)이 흡수 — 20° 이상이면 어차피 -20 포화라 점수가 세대 간 안정.

## Verification (예측 먼저 박제 → 측정)

| 게이트 | 사전 예측 | 실측 | 판정 |
|--------|-----------|------|------|
| 신규 4테스트 (RED) | 3 FAIL / 1 PASS | 3 failed / 1 passed | PASS |
| 신규 4테스트 (GREEN) | 4 PASS | 4 passed | PASS |
| 대상 2파일 전건 | 전건 PASS | 86 passed | PASS |
| 전체 pytest | failed 0, passed ≥ 4532+5 | **4537 passed / 0 failed** (20 skipped, 기존) | PASS |
| phase24 assert_gates | PASS (합성 breakdown 은 dev 0 주입 불발 / geometric md 직주입) | "Phase 24 gates PASS" | PASS |
| phase25 assert_gates | PASS (상속 7 + artifact 구조 5) | "Phase 25 gates PASS" | PASS |
| 실 verdict fixture | record -20.0 / final 80 / correct 100 | 일치 | PASS |

STOP 규칙 발동 0건 — curve-fit 조정 0.

## TDD Gate Compliance

RED(`b35e2512` test) → GREEN(`42547f7a` feat) 순서 성립. REFACTOR 불필요(구현 diff 최소).

## Decisions Made

- 플랜 A안 그대로 구현 — `md` dict 계약(cid→float) 무변경, B안(dev+tol 주입)은 투명 표기 오염으로 플랜 단계에서 기각됨.
- 플랜이 열거하지 않은 7번째 기대값 사이트 발견: `test_vision_measured_split_emits_source_vision` 의 `set(rec.to_dict()) == set(DEDUCTION_RECORD_KEYS)` 단언 — dev 30 이 종전 sub-cap(raw 12)이라 rawPoints/capApplied 가 안 나왔던 것. cap-인지 공용 helper(`_assert_record_keys`)로 전환 + 정당화 주석 (Task 3 (1) 규율 적용).
- `test_record_moment_engraving.py` 는 무접촉 — record 존재/순간 필드 부재만 단언, deviation 수치 미박제 실측 확인.

## Deviations from Plan

None — plan executed exactly as written. (7번째 기대값 사이트는 플랜 Task 3 (1)이 명시한 "원거리 소비처 동일 규율 정정" 경로로 처리 — deviation 아님.)

## Known Stubs

None — 순수 산술 변경, 스텁 0.

## Threat Flags

None — 새 입력면 0 (기존 `_vision_measured_deviation` finite/양수 검증 + support 게이트 + `np.isfinite` 가드 + per-record cap 그대로, T-isk-01 mitigation 재사용 확인).

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- 실영상 확증은 Pod 필요(시연 시 기동 규율) — 다음 Pod 세션에서 kip-up 페어 재스윕 시 fault ≈ 80 / correct 100 예측 대조 가능.
- phase25 원장(6월)의 vision 50° 케이스도 cap 포화(-20)라 점수 동일 — 세대 드리프트 흡수 실증은 코드 산술로 확인됨.

## Self-Check: PASSED

- 파일 실재: deduction_engine.py / test_deduction_engine.py / 본 SUMMARY — 3/3 FOUND
- 커밋 실재: b35e2512 / 42547f7a / b23d9e2a — 3/3 FOUND
- 정당화 주석 실재: `quick-260831-isk` 인용 테스트 9곳 + 엔진 2곳

---
*Phase: quick-260831-isk*
*Completed: 2026-08-31*
