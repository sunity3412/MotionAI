---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "23"
subsystem: ml-pose-engine
status: gate_blocked
tags:
  - rtmw
  - ipsf
  - regression-sweep
  - pose-02
  - pole-axis
  - wave-3-gate
  - plan-23

dependency_graph:
  requires:
    - 01-21  # RTMWPoseEngine
    - 01-22  # RTMWLifterPoseEngine (옵션 B 선택)
    - 01-15  # IPSF GeometricCriterion + loader
  provides:
    - "backend/research/evaluations/compare_rtmw_vs_ipsf.py — RTMW vs IPSF 회귀 검증 스크립트 (POSE-01 + POSE-02 wiring)"
    - "backend/research/evaluations/reports/.gitkeep — 보고서 출력 디렉터리"
    - "backend/tests/test_compare_rtmw_vs_ipsf_smoke.py — 7 smoke 테스트 (게이트 로직 검증)"
    - "backend/tests/test_compare_rtmw_vs_ipsf_pole_axis.py — 4 POSE-02 pole-axis wiring/report/fallback 테스트"
  affects:
    - 01-24  # R&D 격리
    - 01-25  # atomic swap gate — phase1_ready_to_swap 요구

tech_stack:
  added: []
  patterns:
    - "SweepReport dataclass — MotionResult × 5 + phase1_ready_to_swap"
    - "detect_pole_axis — 영상 앞 N프레임 HoughPoleDetector 적용 → video-level PoleAxis (D-10/D-11)"
    - "compare_to_ipsf — load_criteria + hold_window 대표 각도 + |measured-target| ≤ toleranceFull"
    - "compute_phase1_ready_to_swap — gate a (ipsf) AND gate b (line/angle), None = False (T-23-03)"
    - "write_report — JSON + Markdown 이중 출력, pole_axis 블록 모든 motion 필수"
    - "TDD Task 3 — 4 pole-axis 테스트로 POSE-02 anti-pattern 영구 차단"

key_files:
  created:
    - backend/research/evaluations/compare_rtmw_vs_ipsf.py
    - backend/research/evaluations/reports/.gitkeep
    - backend/tests/test_compare_rtmw_vs_ipsf_smoke.py
    - backend/tests/test_compare_rtmw_vs_ipsf_pole_axis.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-23-SUMMARY.md
  modified: []

decisions:
  - "plan 14 (RTMPose+MB vs NLF, NLF 갭 baseline) SUPERSEDED. 본 plan 이 RTMW + IPSF tolerance baseline 으로 완전 대체."
  - "두 게이트 모두 강제: (a) IPSF within_tolerance 5/5 + (b) line/angle 5/5. 한쪽만 PASS = 보류 (D-16 정신)."
  - "T-23-03: N/A (None) 는 PASS 로 카운트 금지 — compute_phase1_ready_to_swap 에 bool 강제."
  - "T-23-04: POSE-02 wiring 자동 검증 박제 — test_compare_rtmw_vs_ipsf_pole_axis.py 4 테스트."
  - "Task 2 (blocking-human checkpoint): belle Pod 5영상 실 실행 후 보고서 검토 + plan 25 승인/보류 결정."

metrics:
  duration_minutes: 35
  completed_date: "2026-06-03"
  task_count: 2
  tasks_total: 3
  files_created: 4
  files_modified: 0
  tests_added: 11
  tests_passing: 11
---

# Phase 01 Plan 23: RTMW vs IPSF 회귀 검증 — checkpoint_reached

RTMW pivot 회귀 검증 스크립트 + POSE-02 자동 검증 박제. Task 1 + Task 3 완료. Task 2 (belle Pod 5영상 실 실행 + 검토) blocking-human checkpoint 대기 중.

---

## TL;DR

| 항목 | 내용 |
|---|---|
| **Status** | `checkpoint_reached` — Task 1 + Task 3 완료, Task 2 belle 검토 대기 |
| **Task 1** | compare_rtmw_vs_ipsf.py + reports/.gitkeep + 7 smoke 테스트 PASS |
| **Task 3** | POSE-02 pole-axis 4 테스트 PASS (wiring/report/fallback/frame-consistency) |
| **Task 2** | blocking-human checkpoint — belle Pod 5영상 sweep + 결과 검토 + plan 25 승인/보류 |
| **신규 파일** | 4 (compare_rtmw_vs_ipsf.py + .gitkeep + 2 테스트) |
| **수정 파일** | 0 |
| **단위 테스트** | 11 PASS (smoke 7 + pole-axis 4, GPU 의존 0, 0.09s) |
| **운영 코드 수정** | 0 |
| **커밋** | 2 (Task 1: 606ea86 / Task 3: 4aa8101) |

---

## Task 1 — compare_rtmw_vs_ipsf.py (POSE-01 + POSE-02)

### 파일 구조

```
backend/research/evaluations/compare_rtmw_vs_ipsf.py
  detect_pole_axis(video_frames) → PoleAxis          # POSE-02 D-10/D-11
  run_rtmw(frames, pole_axis, engine) → list[PoseFrame]  # video-level pole_axis 박제
  compare_to_ipsf(motion, angles, criteria_dir) → list[IpsfGapEntry]
  compute_line_angle_gates(angles, pole_axis) → (bool, bool)
  compute_phase1_ready_to_swap(motions) → bool       # 두 게이트 모두 PASS 필요
  write_report(results, output_dir) → (json_path, md_path)
  main(argv) → int                                   # argparse 진입점
```

### POSE-02 wiring

- 모듈 상단 `from sunity_shared.analysis.pole_axis import HoughPoleDetector` import (T-23-04)
- `detect_pole_axis`: 앞 30 프레임 HoughPoleDetector → confidence 가중평균 → video-level PoleAxis
- D-11 폴백: HoughPoleDetector 없음 / ValueError / 빈 결과 → `PoleAxis(axis_vector=(0,1,0), confidence='low')`
- `run_rtmw`: 모든 PoseFrame.pole_axis 를 video-level PoleAxis 로 박제 (D-10 frame-재계산 금지)

### 두 게이트 (T-23-03)

- Gate (a): `within_tolerance_all = all(g.within_tolerance for g in ipsf_gaps)` — N/A = False
- Gate (b): `line_pass AND angle_pass` — None = False
- `compute_phase1_ready_to_swap` = gate_a AND gate_b

### 보고서 JSON 스키마

```json
{
  "motions": {
    "ref-invert": {
      "pole_axis": {"axis_vector": [0.0, 1.0, 0.0], "confidence": "high"},
      "ipsf_gaps": [{"joint": "left_knee", "moment": "hold", "target": 180.0, "measured": 175.0, "gap": 5.0, "within_tolerance": true}],
      "line_pass": true,
      "angle_pass": true,
      "ms_per_frame": 20.0,
      "rtmw_mean_score": 75.0,
      "lift_swap_ratio": 0.0
    }
  },
  "summary": {
    "phase1_ready_to_swap": true,
    "total_motions": 1,
    "ipsf_within_tolerance_count": 1,
    "line_pass_count": 1,
    "angle_pass_count": 1
  }
}
```

### 수용 기준 검증

| 항목 | 결과 |
|---|---|
| 7 smoke 테스트 PASS | ✓ (0.09s) |
| --help 에 --videos / --output-dir / --pose-engine / --criteria-dir 노출 | ✓ |
| grep phase1_ready_to_swap >= 2 | ✓ (14) |
| grep within_tolerance\|toleranceFull >= 3 | ✓ (24) |
| grep load_criteria >= 1 | ✓ (3) |
| grep HoughPoleDetector >= 1 | ✓ (10) |
| grep pole_axis >= 3 | ✓ (39) |

---

## Task 3 — POSE-02 pole-axis 자동 검증 (test_compare_rtmw_vs_ipsf_pole_axis.py)

### 4 테스트

| 테스트 | 검증 내용 | 결과 |
|---|---|---|
| test_compare_script_imports_hough_pole_detector | HoughPoleDetector import + detect_pole_axis 함수 존재 | PASS |
| test_report_contains_pole_axis_block_per_motion | mock 주입 → JSON 모든 motion 에 pole_axis 블록 | PASS |
| test_low_confidence_fallback_no_crash | ValueError → confidence='low' + axis=[0,1,0] + 비크래시 | PASS |
| test_frame_level_pole_axis_matches_video_level | run_rtmw 반환 frames 모두 video-level PoleAxis 동일 | PASS |

T-23-04 mitigation 완료 — sweep 이 HoughPoleDetector 없이 tolerance PASS 박제하는 anti-pattern 영구 차단.

---

## Task 2 — belle Pod sweep 실행 결과 (2026-06-03) — phase1_ready_to_swap=False

**보고서**: `backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.{json,md}`

### 결과

| 게이트 | 결과 | 박제 기준 | 판정 |
|---|---|---|---|
| IPSF within_tolerance | 1/5 PASS | 5/5 | FAIL |
| line PASS | 3/5 PASS | 5/5 | FAIL |
| angle PASS | 0/5 PASS | 5/5 | FAIL |
| pole_axis high confidence | 0/5 | 5/5 | FAIL |

| 모션 | IPSF | line | angle | ms/f | rtmw_score |
|---|---|---|---|---|---|
| ref-climb | PASS | PASS | FAIL | 2201 | 95.4 |
| ref-foxtop-split | FAIL | FAIL | FAIL | 2164 | 93.0 |
| ref-foxtop | FAIL | FAIL | FAIL | 2083 | 93.3 |
| ref-invert | FAIL | PASS | FAIL | 2116 | 93.6 |
| ref-sideway-spin | FAIL | PASS | FAIL | 2009 | 94.8 |

### 핵심 진단 (root cause 3종 동시 발현)

1. **IPSF criteria target=180° 일률** — 모든 hold moment shoulder/hip/knee target=180° (완전 EXTEND 가정). measured 21~107° = 굽힘 자세. FallbackRecognizer 한계 (Plan 11 박제 그대로) — Phase 5 (Gemini 기술 인식기) 통합 전엔 IPSF angle 게이트 의미 없음.
2. **HoughPoleDetector 미설치** — 5영상 모두 axis_vector=(0,1,0) low confidence (수직 폴백). D-11 박제대로 fallback 동작은 했으나 실제 카메라 각도 반영 0.
3. **AKA 매핑 vs yaml 정합 미검증** — belle 매핑 (`ref-foxtop` ← 인버트 버터플라이 등) 의 yaml hold target 이 그 자세의 IPSF 기준인지 belle/정은지/NotebookLM IPSF CoP 재검증 필요.

### belle Pod sweep 진행 중 함정 5종 (재사용 박제)

| 함정 | Fix | Commit |
|---|---|---|
| `imageio` pyav 플러그인 누락 | `pip install 'imageio[pyav]'` | — |
| rtmlib 0.0.15 `pose` alias 부재 | `RTMW_ONNX_PATH` env var 강제 | 3b27c25 |
| rtmlib Wholebody batch 미지원 | 단일 (H,W,3) frame 입력 | 375c21c |
| mmpose `chumpy` 빌드 fail | `pip install --no-build-isolation chumpy` 선행 | — |
| onnx 위치 패턴 | `<weights_root>/20230928/rtmpose_onnx/<model>/end2end.onnx` | — |

상세 박제 → 메모리 [[runpod-gpu-env.md]] 누적.

### 결정 path

| 조건 | 결과 | 다음 행동 |
|---|---|---|
| IPSF 5/5 + line/angle 5/5 PASS | phase1_ready_to_swap=True | "approved: proceed to plan 25" → Wave 5 진입 |
| **한쪽이라도 FAIL** | **phase1_ready_to_swap=False** | **"blocked" → D-16 보류 → 후속 plan 의논 중 (Phase 5 선행 vs Plan 26 root cause 3종 동시 fix)** |

---

## Deviations from Plan

없음 — 계획대로 실행.

---

## Threat Surface Scan

신규 네트워크 엔드포인트 없음. 신규 인증 경로 없음. 파일 접근 = 로컬 영상 + 보고서 출력 (연구 디렉터리, 운영 Lambda 미포함).

---

## Self-Check: PASSED

- compare_rtmw_vs_ipsf.py 존재: ✓ (/Users/kimtaesung/Dev/SunityMotion/backend/research/evaluations/compare_rtmw_vs_ipsf.py)
- reports/.gitkeep 존재: ✓
- test_compare_rtmw_vs_ipsf_smoke.py 존재: ✓
- test_compare_rtmw_vs_ipsf_pole_axis.py 존재: ✓
- 커밋 606ea86 존재: ✓ (Task 1)
- 커밋 4aa8101 존재: ✓ (Task 3)
- 11 테스트 PASS (0.09s): ✓
- 운영 코드 수정 0줄: ✓
- 사람 점수 라벨링 0건: ✓
- 이모지 0건: ✓
- Task 2 blocking-human checkpoint 정상 반환: ✓
- Task 2 belle Pod sweep 실행 완료 (2026-06-03): ✓
- 보고서 박제: ✓ (`backend/research/evaluations/reports/sweep_rtmw_20260603_1409/`)
- 게이트 판정: phase1_ready_to_swap=False (D-16 보류)
- root cause 3종 박제: ✓ (Phase 5 통합 + HoughPoleDetector + yaml 재검증)
- 후속 plan 의논: 진행 중
