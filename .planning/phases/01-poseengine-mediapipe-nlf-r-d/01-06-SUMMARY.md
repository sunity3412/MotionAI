---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "06"
subsystem: pose-engine
tags:
  - compare-engines
  - regression-verification
  - mediapipe-vs-nlf
  - wave2-gate
  - belle-checkpoint
dependency_graph:
  requires:
    - 01-02 (MediaPipePoseEngine, pose_engines/mediapipe_engine.py)
    - 01-03 (HoughPoleDetector, pole/detector.py, pole/aligner.py)
    - 01-01 (PoseFrame, PoleAxis, to_coco17_array, compute_frame_reliability)
  provides:
    - compare_engines.py: MediaPipe vs NLF 회귀 검증 스크립트 (D-13~D-16 박제)
    - EngineResult dataclass: 엔진 결과 계약
    - generate_markdown_report(): JSON payload → Markdown 보고서
    - reports/.gitkeep: 보고서 출력 디렉터리 확보
    - smoke 10개 테스트 (10 passed)
  affects:
    - Wave 3 (Plan 04 NLF 격리 + Plan 05 atomic swap): belle 승인 후에만 진행 (H-1)
tech_stack:
  added:
    - backend/research/__init__.py: R&D 비교군 평가 패키지 루트
    - backend/research/evaluations/__init__.py: compare_engines re-export
    - backend/research/evaluations/compare_engines.py: 회귀 검증 스크립트
    - backend/research/evaluations/reports/.gitkeep: 보고서 출력 디렉터리
    - backend/tests/test_compare_engines_smoke.py: 10개 smoke 테스트
  patterns:
    - EngineResult dataclass (공정 비교 계약)
    - lazy import (mediapipe, nlf, boto3, FrameExtractor — 모듈 load 시 불필요)
    - tempfile auto-cleanup (T-1-03 threat mitigation)
    - phase1_ready_to_swap gate (D-08/D-16/H-1 박제)
key_files:
  created:
    - backend/research/__init__.py (17 lines)
    - backend/research/evaluations/__init__.py (14 lines)
    - backend/research/evaluations/compare_engines.py (430 lines)
    - backend/research/evaluations/reports/.gitkeep (0 lines)
    - backend/tests/test_compare_engines_smoke.py (190 lines)
  modified: []
decisions:
  - "Wave 2 시점 NLF 옛 위치 import — sunity_shared.analysis.pose_estimator (H-1 박제)"
  - "EngineResult.avg_keypoint_confidence: NLF는 NaN (MediaPipe만 유효)"
  - "phase1_ready_to_swap: 4개 게이트(D-14 + D-15 ①②③) 모두 PASS여야 true"
  - "AVG_CONFIDENCE_THRESHOLD=0.5 placeholder — A9 belle 확정 후 갱신"
  - "_safe_float(): NaN/Inf → JSON None 변환 (JSON 직렬화 안전)"
  - "보고서 출력: JSON + Markdown 동시 (args.out과 같은 이름, .md 확장자)"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-31"
  tasks_completed: 1
  tests_added: 10
  files_created: 5
  files_modified: 0
---

# Phase 1 Plan 06: MediaPipe vs NLF 회귀 검증 스크립트 Summary

compare_engines.py 회귀 검증 스크립트를 구현하고 D-13(5영상)·D-14(±5점 허용)·D-15(4지표)·D-16(실패 시 보류) 게이트를 코드로 박제했다. Wave 2 시점 NLF 옛 위치 import(H-1) + A9 placeholder(0.5) + L-2 실행경로(/workspace/SunityMotion)를 문서화. 10개 smoke 테스트 통과. belle가 RunPod에서 5영상 실행 후 Wave 3 승인 게이트를 결정한다.

## Task 1 완료 — compare_engines.py + smoke 테스트

### 생성된 파일 목록

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `backend/research/__init__.py` | 17 | R&D 비교군 평가 패키지 루트 |
| `backend/research/evaluations/__init__.py` | 14 | compare_engines re-export |
| `backend/research/evaluations/compare_engines.py` | 430 | MediaPipe vs NLF 회귀 검증 스크립트 |
| `backend/research/evaluations/reports/.gitkeep` | 0 | 보고서 출력 디렉터리 확보 |
| `backend/tests/test_compare_engines_smoke.py` | 190 | 10개 smoke 테스트 |

### D-14 + D-15 게이트 박제 확인

| 게이트 | 코드 필드 | 기준 | 위치 |
|--------|-----------|------|------|
| D-14: 점수 갭 | `within_tolerance_5pt` | `abs(mp - nlf) <= 5.0` | compare_engines.py:193 |
| D-15 ①: 위양성 없음 | `mediapipe_score_ge_70` | `mp_score >= 70.0` | compare_engines.py:200 |
| D-15 ②: Top-3 겹침 | `top3_overlap_2_of_3` | `overlap_count >= 2` | compare_engines.py:207 |
| D-15 ③: avg confidence | `avg_confidence_ok` | `avg_conf >= 0.5 (A9)` | compare_engines.py:213 |
| D-15 ④: ms/frame | `mediapipe_ms_per_frame` | 측정값 기록 (SLA 판단은 belle) | compare_engines.py:218 |

`phase1_ready_to_swap = D-14 AND D-15①②③` — 4개 모두 PASS여야 Wave 3 진행.

### Wave 2 시점 NLF 옛 위치 import (H-1 박제)

```python
# compare_engines.py _run_nlf() 내부 — Wave 2 시점 옛 위치 import
from sunity_shared.analysis.pose_estimator import NlfPoseEstimator  # noqa: PLC0415 — Wave 2 옛 위치
```

H-1 박제 grep 결과:
```
grep -nE "from sunity_shared\.analysis\.pose_estimator import NlfPoseEstimator" \
  backend/research/evaluations/compare_engines.py
# → 1 match
```

### A9 placeholder (AVG_CONFIDENCE_THRESHOLD)

```python
AVG_CONFIDENCE_THRESHOLD: float = 0.5
# A9 belle 보류 — placeholder. Plan 06 Task 2 회귀 결과 후 belle가 확정값으로 갱신.
# 5영상 avg_keypoint_confidence 분포를 보고 0.5 / 0.55 / 0.6 중 결정.
```

확정 후 갱신 대상:
- `compare_engines.AVG_CONFIDENCE_THRESHOLD`
- `pose_frame.RELIABILITY_HIGH_THRESHOLD` / `RELIABILITY_MEDIUM_THRESHOLD` (Plan 01)

### L-2 실행 경로 박제 (/workspace/SunityMotion)

```bash
cd /workspace/SunityMotion
python -m backend.research.evaluations.compare_engines \
  --motions ref-ballerina-spin ref-front-hook-spin ref-plank-spin \
            ref-invert-butterfly-combo ref-gemini-to-ayesha-combo \
  --out backend/research/evaluations/reports/compare_$(date +%Y%m%d).json
```

### 10개 smoke 테스트 결과

```
backend/tests/test_compare_engines_smoke.py (10 tests)
  PASS: test_engine_result_dataclass
  PASS: test_engine_result_defaults
  PASS: test_generate_markdown_report_basic
  PASS: test_generate_markdown_report_fail_case
  PASS: test_phase1_ready_to_swap_logic_all_pass
  PASS: test_phase1_ready_to_swap_logic_one_fail
  PASS: test_avg_confidence_threshold_placeholder
  PASS: test_default_motions_count
  PASS: test_default_motions_types
  PASS: test_default_motions_contains_expected
  ──────────────────────────────────────────
  10 passed
```

## Task 2 — belle checkpoint (PENDING)

**belle가 RunPod에서 5영상 실행 후 Wave 3 승인 여부를 결정해야 함.**

Wave 3 (Plan 04 + Plan 05)는 본 checkpoint의 approved resume-signal 이후에만 진행.

보고서 위치 (실행 후 생성): `backend/research/evaluations/reports/compare_YYYYMMDD.json + .md`

## Deviations from Plan

None — plan executed exactly as written.

Wave 2 시점 NLF 옛 위치 import, A9 placeholder, L-2 실행경로 모두 계획된 박제 사항.

## Known Stubs

- `AVG_CONFIDENCE_THRESHOLD = 0.5` — A9 belle confirm 보류. Plan 06 Task 2 회귀 결과(5영상 avg_conf 분포)를 보고 belle가 확정값 결정. 현재 0.5는 placeholder — 기능은 완전히 구현됨.

## Threat Flags

없음 — 신규 네트워크 엔드포인트 없음. T-1-03(S3 reference 영상 처리 시 tempfile 자동 cleanup)은 구현에 박제됨.

## 로컬에서 실행 불가한 이유

compare_engines.py의 실제 5영상 비교는 RunPod Pod에서만 실행 가능:
1. **NLF**: GPU (CUDA) 필수 — CPU에서 NaN 발산 (CLAUDE.md 및 pose_estimator.py docstring 명시)
2. **MediaPipe**: Linux x86_64 wheel만 존재 — macOS ARM64에서는 테스트 환경 한계
3. **S3**: 정은지 reference 영상은 `sunity-motion-pilot-videos` 버킷에 있음 (AWS 자격증명 필요)
4. **FrameExtractor**: imageio/ffmpeg 의존 (로컬 미설치)

따라서 숫자를 만들지 않고 스크립트만 완성 + belle RunPod 실행 checkpoint 반환.

## Wave 3 진입 전 belle 작업 사항

1. **RunPod 5영상 실행** — Task 2 checkpoint 지침 참조
2. **A9 threshold 확정** — avg_conf 분포 확인 후 0.5 / 0.55 / 0.6 결정
3. **Phase 1 ready 결정** — phase1_ready_to_swap true → Plan 04 + 05 진행, false → D-16 보류
4. **25개 다양성 세트** — belle 지속 확보 (D-13 reminder)
5. **Plan 04는 본 checkpoint approved 후에만 진행 가능** (H-1 박제)

## Self-Check: PASSED

파일 존재 확인:
- `backend/research/__init__.py` FOUND
- `backend/research/evaluations/__init__.py` FOUND
- `backend/research/evaluations/compare_engines.py` FOUND
- `backend/research/evaluations/reports/.gitkeep` FOUND
- `backend/tests/test_compare_engines_smoke.py` FOUND

커밋 존재 확인:
- `6255380` feat(01-06): compare_engines.py 회귀 검증 스크립트 + smoke 테스트 FOUND
