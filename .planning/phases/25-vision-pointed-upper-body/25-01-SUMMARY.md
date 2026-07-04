---
phase: 25-vision-pointed-upper-body
plan: 01
subsystem: backend-scoring
tags: [vision-veto, deduction-seed, window-median, pointed-joints, SCORE-15]
requires:
  - phase: 24 (deduction_engine tally + angle_vs_reference criterion 8종)
  - quick-260702-o0c f513587 (reverted) — _emit_reference_relative helper 재사용 소스
provides:
  - vision_veto.pointed_joints_from_supported_differences (좁은 pointed 매퍼, 순수 함수)
  - _build_deduction_measured_deviations 관절 단위 2-source merge (vision_pointed_joints + seed_audit_out kwarg)
  - 호출부 배선 (app.py vision_fault_context 분기 → pointed 도출 → kwarg 전달)
affects:
  - 25-02/25-03 (짚기 커버리지 — 집계 fold + 프롬프트 보강)
  - 25-04 (eval harness — seed_audit_out 구조 게이트 소비)
tech-stack:
  added: []
  patterns:
    - "감점용(pointed) 매퍼와 표시용(fault_joints) 매퍼 분리 — broad 확장 금지"
    - "seed 관절 단위 2-source merge (window=pointed 만 / DTW=silent 유지)"
key-files:
  created:
    - backend/tests/test_vision_pointed_mapper.py (156 lines, 12 tests)
    - backend/tests/test_deduction_seed_pointed_merge.py (245 lines, 8 tests)
  modified:
    - backend/shared/python/sunity_shared/analysis/vision_veto.py (+54)
    - backend/functions/pipeline/app.py (+94/-17)
decisions:
  - "OD-1 반영: side=unknown → 양측 관절 window eligible (판정은 측정+tol 20° 게이트)"
  - "wm entry NaN/0/형상불량은 wm_by_joint 미등재 → 해당 관절 DTW fallback 강하 (f513587 의 '미방출' 과 달리 plan behavior 명시대로 fallback)"
  - "window 집계 출처는 로그+seed_audit_out 로만 관측 — record source 는 기존 geometry 표기 유지 (스키마 변경 0)"
metrics:
  duration: ~9 min (04:50–04:59 UTC)
  completed: 2026-07-04
  tasks: 2/2 (both TDD RED→GREEN)
  tests: 20 신규 (12 mapper + 8 merge), 관련 스위트 262 passed (baseline 242 + 20, 회귀 0)
---

# Phase 25 Plan 01: vision-pointed seed-stage 관절 단위 merge Summary

Gemini 가 짚은(supported faultKey) 관절만 worst-window median 으로 감점 seed 를 방출하고 silent 관절은 full-path DTW median 을 유지하는 관절 단위 2-source merge — 260702-o0c 경로 either/or FAIL(success 위양성 4건)의 정확한 해소.

## Tasks

| Task | Name | Commits | Result |
|------|------|---------|--------|
| 1 | 좁은 pointed-joint 매퍼 (vision_veto 순수 함수) | 9c59437 (RED) / fe79a06 (GREEN) | 12 tests PASS |
| 2 | seed-stage 관절 단위 merge 배선 | 04349b5 (RED) / 981090a (GREEN) | 8 tests PASS |

## What Was Built

**Task 1 — `pointed_joints_from_supported_differences` (vision_veto.py):**
- canonical `_faultKey`(FaultKey) 만 소비 — body_part 자유텍스트 재파싱 금지 (T-25-01). dict 는 `FaultKey.from_dict` 시도, enum 밖/형상불량 graceful skip.
- 명시 keypoint_set 4종만 매핑 (`shoulder→shoulder / arm→elbow / leg→knee / hip→hip`), line/torso/head_neck/grip 방출 0 — 표시용 `fault_joints_from_differences` 의 trunk/양다리 broad 확장과 분리 (리서치 함정 ⑥).
- OD-1: side=unknown → 양측 eligible. 출력 = JOINT_KEYS 순서 안정 tuple, dedup, spurious 키 0.

**Task 2 — `_build_deduction_measured_deviations` merge (app.py):**
- keyword-only `vision_pointed_joints=None`, `seed_audit_out=None` — default None → legacy/mode3/pointed-없음 경로 byte-동일 (테스트로 증명).
- f513587 `_emit_reference_relative` helper 복원 (JOINT_KEYS 검증 / NaN·0·음수 skip / expects_extension cross-exclusion — 이중감점 방어 재구현 0).
- merge: `jk ∈ pointed AND jk ∈ wm_by_joint` → window abs(delta_deg), 그 외 전부 DTW per_joint_deviation. wm NaN/0/형상불량 entry 는 해당 관절 DTW 강하.
- 관찰: `angle_vs_reference seed pointed=%d window=%d fallback=%d` 로그 + seed_audit_out `{pointed, window_joints, fallback_joints}` (25-04 eval 입력, production 미전달 → 부작용 0).
- 호출부(app.py vision_fault_context 분기): quantification 빌드 직후 pointed 도출 → kwarg 전달. legacy 분기 무접촉.

## Verification (all GREEN)

- `pytest tests/test_vision_pointed_mapper.py -q` → 12 passed
- `pytest tests/test_deduction_seed_pointed_merge.py -q` → 8 passed
- `pytest tests/ -k "deduction or vision or criteria" -q --continue-on-collection-errors` → **262 passed** (HEAD~4 baseline 242 passed, +20 신규, FAIL 0). 11 collection errors 는 temp worktree 로 HEAD~4 와 diff IDENTICAL 확인 (pre-existing `No module named 'backend'` env 이슈 — 25-RESEARCH Validation Architecture 정합).
- 관련 스위트 명시 실행: deduction_seam/vision_gate/deduction_engine/vision_veto/phase24_gates/gemini_vision_scorer/features/fault_zoom → 255 passed, 회귀 0.
- at_seconds 게이트: `git diff HEAD -- functions/pipeline/app.py | grep -c 'at_seconds'` == 0 (`_collect_vision_fault_context` 호출 at_seconds=None 불변).
- 밴드 grep 게이트: 비주석 `SEVERITY_CAP|apply_downward_cap` == 0.
- 금지 조항: 신규 튜닝 상수 0 (매핑 dict 만, 수치 임계 0) / 밴드 0 / kip-up 특정 분기 0 / motiondtw.py 무접촉 (diff 4파일만) / 스키마·Firestore 계약 변경 0.

## Deviations from Plan

None - plan executed exactly as written.

(참고: behavior "wm delta NaN/0 → fallback 강하" 는 f513587 원본의 "미방출" 과 다른 지점이나, 플랜 behavior 명세가 명시적으로 fallback 을 요구해 그대로 구현 — deviation 아님.)

## Known Stubs

None — seed_audit_out 은 production 미전달 관측 파라미터(의도된 eval 전용 인터페이스, 25-04 가 소비).

## TDD Gate Compliance

- RED: 9c59437 (`test(25-01)` mapper, ImportError 로 FAIL 확인) → GREEN: fe79a06 (`feat(25-01)`)
- RED: 04349b5 (`test(25-01)` merge, 7 failed/1 passed — 신규 kwarg 부재로 FAIL 확인) → GREEN: 981090a (`feat(25-01)`)

## Next (Wave 후속)

- 25-02/25-03: 상체 faultKey 짚기 커버리지 (support 집계 fold + upper_body 프롬프트 보강 + 캐시 버전 bump)
- 25-04: eval harness (seed_audit_out 구조 게이트 + success 멤버 짚기-FP 관측) → Pod 6페어 sweep 이 최종 심판 (success 6/6==100)

## Self-Check: PASSED

- backend/shared/python/sunity_shared/analysis/vision_veto.py: FOUND (`def pointed_joints_from_supported_differences`)
- backend/functions/pipeline/app.py: FOUND (`vision_pointed_joints`)
- backend/tests/test_vision_pointed_mapper.py: FOUND (156 lines ≥ 40)
- backend/tests/test_deduction_seed_pointed_merge.py: FOUND (245 lines ≥ 60)
- Commits 9c59437 / fe79a06 / 04349b5 / 981090a: FOUND in git log
