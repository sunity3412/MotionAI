---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: 18
subsystem: pose-engine
tags: [averaging, spike, on-hold, rtmw-pivot]
status: on_hold
parent_plan: 01-17
on_hold_reason: rtmw_pivot_supersedes_lift_path_choice
on_hold_since: 2026-06-02
revisit_after: 01-23 (RTMW 회귀 검증 게이트)
requires:
  - phase: 01-08 (MP+MB baseline)
  - phase: 01-11 (RTMPose+MB sweep)
  - phase: 01-12 (cross-engine root cause)
  - phase: 01-16 (live mode trace)
  - phase: 01-17 (mapping audit)
provides:
  - "(deferred — execution pending RTMW pivot outcome)"
affects: []

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "2026-06-02 belle RTMW pivot: 두 lift path averaging 의 동기 (RTMPose+MB / MP+MB 의 좌우 noise cancel) 가 RTMW 단일 백본 채택으로 약화 — pivot 결과 (01-23 회귀) 후 averaging 의 유효성 재평가"

patterns-established: []
requirements-completed: []

duration: 0min
completed: 2026-06-02
---

# Plan 01-18: multi-engine averaging spike — ON HOLD

**상태: ON HOLD (abandoned 아님). 01-23 RTMW 회귀 검증 결과 후 재평가.**

## 왜 on hold 인가

본 plan 의 동기 = Plan 17 verdict `blocked/no-static-mapping-defect` 후속으로, lift path 자체의 좌우 keypoint noise 를 **두 lift path 평균/voting (RTMPose+MB ⊕ MediaPipe+MB)** 으로 해소.

2026-06-02 belle RTMW 무료 스택 pivot (CONTEXT D-17, D-23) 으로 운영 백본이 **RTMW 133 wholebody 단일 백본** 으로 전환:

- 평균 대상 두 lift path 중 MediaPipe+MB 가 운영 백본에서 제외 (D-23) → 두 path 평균의 의미가 약화됨.
- RTMW 자체가 133 wholebody 의 풍부한 keypoint 분포 + Apache-2.0 라이선스로 좌우 신뢰도 본질적으로 다른 baseline.
- 따라서 01-23 (RTMW vs IPSF GeometricCriterion 5영상 회귀 검증) 의 swap_frame_ratio / line·angle 결과 확인 전에 averaging path 를 spike 하는 것은 **premature**.

## 재진입 트리거 (revisit triggers)

01-23 결과 PASS path 분기:

| 01-23 결과 | 01-18 처분 |
|---|---|
| swap_ratio ≤ 0.05 + line/angle 5/5 PASS + lifter.overall ≥ 85 | **closed** — averaging 불요 (RTMW 단일 백본으로 충분) |
| swap_ratio > 0.05 OR line/angle FAIL | **재진입 검토** — averaging 의 새 대상은 RTMW2D direct vs RTMW + MotionBERT lift (01-22 의 옵션 A vs B 결정 후 합성) |
| lifter.overall < 85 but swap PASS | Plan 17 권고 우선순위 2 (pre-lift filtering / post-lift symmetry constraint) 가 averaging 보다 우선 |

## 의존성 무수정 박제

본 plan 미실행 → 의존 plan (01-08/11/12/16/17) 작업물 무수정, dimensions/technique/skeleton/features/temporal 모듈 무수정, 운영 코드 무수정.

ROADMAP Phase 1 plan 표는 본 plan 을 `[on hold]` 로 표기. memory `plan-18-on-hold-rtmw-pivot.md` 박제됨 (2026-06-02).

## Self-Check

- [x] 본 plan 미실행 박제 — 코드 변경 0건
- [x] on_hold 이유 + revisit trigger 명시
- [x] memory `plan-18-on-hold-rtmw-pivot.md` 와 일치
- [x] ROADMAP `[on hold]` 마킹과 일치

## Verdict

`on_hold` — 01-23 RTMW 회귀 결과에 따라 closed / 재진입 결정.
