---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: 05
subsystem: pipeline
tags: [atomic-swap, mediapipe, superseded, rtmw-pivot]
status: superseded
superseded_by: 01-25
superseded_on: 2026-06-02
requires:
  - phase: 01-04 (NLF 격리 — also superseded)
  - phase: 01-06 (compare_engines.py belle checkpoint)
provides:
  - "(none — not executed; replaced by 01-25)"
affects: []

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "2026-06-02 belle RTMW pivot: pipeline/app.py atomic swap 대상을 MediaPipe 가 아닌 RTMW 로 변경 → 01-25 가 책임"

patterns-established: []
requirements-completed: []

duration: 0min
completed: 2026-06-02
---

# Plan 01-05: pipeline/app.py atomic swap (NLF→MediaPipe) — SUPERSEDED

**상태: SUPERSEDED — 미실행. 01-25 가 swap 책임을 RTMW 대상으로 가져간다.**

## 왜 superseded 인가

2026-06-02 belle RTMW pivot (CONTEXT D-17, D-21, D-23, D-24) 으로 운영 백본이 **MediaPipe → RTMW 133 wholebody** 로 변경. 본 plan 은 NLF→MediaPipe atomic swap 을 박제했으나 MediaPipe 자체가 운영 백본에서 제외 (D-23) 되었으므로 swap 의 대상이 RTMW 로 바뀜.

D-08 (atomic swap, 중간 상태 없음) 의 정신은 유지되며, 단지 swap 의 destination 이 다를 뿐이다. 01-25 가 동일한 atomic 약속을 RTMW 대상으로 박제한다.

ROADMAP Phase 1 plan 표는 본 plan 을 `[SUPERSEDED]` 로 표기하며, 01-25 가 supersede 책임을 박제한다.

## 대체 경로

| 본 plan 의 책임 | 이관처 |
|---|---|
| pipeline/app.py NLF → MediaPipe 1:1 swap | 01-25 T-1 (대상 변경: NLF → RTMW) |
| RunPod requirements + setup.sh + README MediaPipe 셋업 | 01-25 T-2 (RTMW 가중치 + rtmlib 셋업) |
| heavy import lazy (H-2) | 01-25 동일 박제 |
| poleAxis 메타 보존 (D-12 / H-3) | 01-25 동일 박제 |
| Wave 순서 (Plan 06 belle 승인 + Plan 04 격리 후 진행) | 01-25 는 01-23 (belle 회귀 승인) + 01-24 (격리) 후 진행 |

## Self-Check

- [x] 본 plan 미실행 박제 — 코드 변경 0건
- [x] 책임 이관처 (01-25) 명시
- [x] ROADMAP `[SUPERSEDED]` 마킹과 일치

## Verdict

`superseded` — 01-25 가 atomic swap 의 destination 을 MediaPipe → RTMW 로 갱신해 흡수.
