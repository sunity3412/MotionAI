---
phase: quick-260629-cej
plan: 01
subsystem: backend/analysis
tags: [split-angle, ipsf, geometry, measurement-primitive, kip-up]
requires: [backend/shared/python/sunity_shared/analysis/features.py, skeleton.py]
provides: [split_angle_series, max_split]
affects: []
tech-stack:
  added: []
  patterns: [pure-numpy-geometry, _angle_deg-reuse]
key-files:
  created:
    - backend/tests/test_split_angle.py
  modified:
    - backend/shared/python/sunity_shared/analysis/features.py
decisions:
  - "split = 두 허벅지(hip→knee) 방향벡터 사이각 (hip-center subtended 각 아님)"
metrics:
  duration: ~10m
  completed: 2026-06-29
  tasks: 2
  files: 2
---

# Phase quick-260629-cej Plan 01: Split-Angle Geometric Measurement Primitive Summary

객관 inter-thigh split 각도 측정 primitive(`split_angle_series` + `max_split`)를 IPSF "inner thighs hips-to-knees lines" 정의로 순수 numpy 구현하고, 알려진 다리 기하→알려진 각도(0/90/180°±2°) + 단조성 합성 정답으로 측정 정확도를 증명했다. pod/AWS/엔진 무관, 채점 wiring은 후속 task.

## What Was Built

- `split_angle_series(keypoints)` — COCO-17 keypoints (T,17,3|4) → 프레임별 inter-thigh split(도). 좌 허벅지(left_hip→left_knee)·우 허벅지(right_hip→right_knee) 방향벡터 사이각. 모음≈0° / 직교≈90° / full split≈180°, 더 벌릴수록 단조 증가, NaN-safe. 기존 `_angle_deg`(원점 vertex 재사용)·`kp_index` 호출, 중복 구현 0.
- `max_split(split_series)` — 유한값 중 peak(값, 프레임 인덱스), 전부 NaN이면 (nan, -1). dynamic 동작(kip-up)의 변별 순간 = 최대 벌림 peak (안정 hold-window 아님).
- `backend/tests/test_split_angle.py` — 합성 정답(0/90/180°±2°), 단조성(우 허벅지 0→180° 회전), 3D(z) 사용, NaN 프레임 격리, 2D reject, 4채널 무시, max_split peak/NaN/sentinel/실시계열 통합. 12 테스트 통과.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] split 측정식 = hip-center subtended 각 → inter-thigh 방향벡터 각**
- **Found during:** Task 1 verify (PLAN `<verify>` 실행)
- **Issue:** PLAN `<action>`의 리터럴 식 `_angle_deg(left_knee, hip_center, right_knee)`(hip-center vertex subtended 각)는 PLAN 자신의 `<done>`("near-parallel ~0°") 및 must_haves("legs-together≈0°")와 모순. 골반 너비 때문에 다리가 평행(모음)해도 subtended 각이 0이 아니라 90°가 나옴(검증 출력 확인: 90.0).
- **Fix:** IPSF "inner thighs hips-to-knees lines" 정의에 충실하게 두 허벅지 **방향벡터**(left_hip→left_knee, right_hip→right_knee) 사이각으로 측정. 원점을 vertex로 둔 `_angle_deg` 재사용(중복 구현 금지 유지). 결과: 모음 0° / 직교 90° / full split 180° — must_haves·`<done>`·`<verify>` 전부 충족, 단조성 성립.
- **Files modified:** backend/shared/python/sunity_shared/analysis/features.py
- **Commit:** ac1a0b9

## Verification

- Task 1 verify(PLAN): near-parallel 0.0° / full split 180.0° / perpendicular 90.0° / max_split (120.0, 3) / all-nan (nan, -1).
- Task 2: `pytest tests/test_split_angle.py -q` → 12 passed.
- 회귀: `pytest tests/test_split_angle.py tests/test_features.py -q` → 28 passed (features 회귀 0).

## Known Stubs

None — 측정 primitive + 검증 완비. 채점 wiring(_process max-split deficit, reference split 재-seed, md 빌더 주입)은 설계 문서(15-SPLIT-MEASUREMENT-DESIGN §구현순서 2~5)대로 후속 task로 명시 분리됨(stub 아님, 의도된 범위 경계).

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/features.py (split_angle_series, max_split defs)
- FOUND: backend/tests/test_split_angle.py
- FOUND commit ac1a0b9 (feat), 75cb534 (test)
