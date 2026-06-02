---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: 04
subsystem: pose-engine
tags: [nlf, isolation, superseded, rtmw-pivot]
status: superseded
superseded_by: 01-24
superseded_on: 2026-06-02
requires:
  - phase: 01-06 (compare_engines.py belle checkpoint — pre-pivot path)
provides:
  - "(none — not executed; replaced by 01-24)"
affects: []

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "2026-06-02 belle RTMW pivot: NLF + MediaPipe + 비선택 3D path R&D 격리 책임을 01-24 로 통합 이관"

patterns-established: []
requirements-completed: []

duration: 0min
completed: 2026-06-02
---

# Plan 01-04: NLF R&D 격리 (NLF 전용) — SUPERSEDED

**상태: SUPERSEDED — 미실행. 01-24 가 본 plan 의 범위를 흡수·확장한다.**

## 왜 superseded 인가

2026-06-02 belle RTMW 무료 스택 pivot (`.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md` D-17~D-25, memory `rtmw-free-stack-pivot.md`) 으로 운영 백본이 **MediaPipe + MotionBERT → RTMW 133 wholebody (Apache-2.0) 단일 백본** 으로 전환되었다. 결과:

- 본 plan 의 격리 범위는 NLF 단독이었으나, pivot 후 격리 대상이 **NLF + MediaPipe + 비선택 3D path** 로 확장됨.
- 따라서 단일 격리 작업을 01-24 로 통합하는 것이 D-23 (다운스트림 무수정 + 단일 격리 path) 에 부합.

ROADMAP Phase 1 plan 표는 본 plan 을 `[SUPERSEDED]` 로 표기하며, 01-24 가 supersede 책임을 박제한다.

## 대체 경로

| 본 plan 의 책임 | 이관처 |
|---|---|
| NLF 코드 backend/research/ 이동 | 01-24 T-1 (확장: NLF + MediaPipe + 비선택 3D path) |
| .samignore + ImportError 가드 | 01-24 T-2 |
| H-1 wave 순서 (Plan 06 belle 승인 후 진행) | 01-23 belle 회귀 검증 게이트 (RTMW pivot 의 새 게이트) |

## Self-Check

- [x] 본 plan 미실행 박제 — 코드 변경 0건
- [x] 책임 이관처 (01-24) 명시
- [x] ROADMAP `[SUPERSEDED]` 마킹과 일치

## Verdict

`superseded` — 01-24 가 RTMW pivot scope 로 본 plan 의 범위를 흡수·확장.
