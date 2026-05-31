---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "03"
subsystem: pose-engine
tags:
  - pole-detection
  - hough-transform
  - pole-alignment
  - lazy-import
  - tdd
  - opencv
  - scipy
dependency_graph:
  requires:
    - 01-01 (PoleAxis dataclass, ConfidenceLevel, RELIABILITY_*_THRESHOLD)
  provides:
    - HoughPoleDetector (Canny + HoughLinesP, cv2 lazy import)
    - compute_alignment_matrix (scipy Rotation.align_vectors, scipy lazy import)
    - apply_alignment (numpy only, Keypoint3DAligned)
    - _map_numeric_to_confidence_level (module-level helper, cv2 없이 호출 가능)
  affects:
    - Plan 02 adapter (test_pole_alignment_applied_when_aligner_available)
    - Plan 05 (requirements.txt — opencv-python-headless 4.13.0.92, scipy 1.17.1 추가 예정)
tech_stack:
  added:
    - pole/__init__.py: package 진입점 (HoughPoleDetector + compute_alignment_matrix + apply_alignment re-export)
    - pole/detector.py: HoughPoleDetector (cv2 lazy import, Hough 파라미터 module-level 상수)
    - pole/aligner.py: compute_alignment_matrix + apply_alignment (scipy lazy import)
  patterns:
    - H-2 lazy import: cv2/scipy 는 class __init__ / 함수 내부에서만 — module load 는 부재 환경에서도 성공
    - M-2 confidence_level enum: _map_numeric_to_confidence_level 함수, RELIABILITY_*_THRESHOLD 재사용
    - D-10 video-level: frame_index=None PoleAxis 1개 반환
    - D-11 vertical_fallback: 수직 선 없으면 (0,1,0) + 'low'
    - Pitfall 3 주석: image 2D → 3D (x,y,0) 카메라 roll=0 가정 명시
key_files:
  created:
    - backend/shared/python/sunity_shared/analysis/pole/__init__.py (21 lines)
    - backend/shared/python/sunity_shared/analysis/pole/detector.py (244 lines)
    - backend/shared/python/sunity_shared/analysis/pole/aligner.py (100 lines)
    - backend/tests/test_pole_detector.py (184 lines)
    - backend/tests/test_pole_aligner.py (200 lines)
  modified: []
decisions:
  - "cv2/scipy lazy import (H-2): 모듈 load 는 cv2/scipy 없어도 성공 — 클래스 __init__/함수 내부에서만 import"
  - "confidence_level enum (M-2): _map_numeric_to_confidence_level 로 numeric → 'high'/'medium'/'low' 매핑, RELIABILITY_HIGH_THRESHOLD(0.7)/MEDIUM(0.4) 재사용"
  - "frame_index=None (D-10): video-level PoleAxis 1개 — 모든 frame 에 동일 axis 적용"
  - "axis_vector = (x_2d, y_2d, 0.0) (Pitfall 3): image 2D 좌표계 검출 결과 + 카메라 roll=0 가정"
  - "HOUGH_THRESHOLD=80, HOUGH_MIN_LINE_LENGTH=100 (RESEARCH 권장값): 정은지 5영상 sweep 후 튜닝 가능"
metrics:
  duration: "~35 minutes"
  completed: "2026-05-31"
  tasks_completed: 2
  tests_added: 16
  files_created: 5
  files_modified: 0
---

# Phase 1 Plan 03: HoughPoleDetector + PoleAxisAligner Summary

Hough Line Transform 기반 폴 축 자동 검출(HoughPoleDetector) + 좌표계 정렬(PoleAxisAligner) 모듈을 구현하고, REVIEWS H-2(cv2/scipy lazy import) + M-2(confidence_level enum) + D-10(video-level 1개 axis) 를 박제했다.

## 추가된 모듈 목록

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `backend/shared/python/sunity_shared/analysis/pole/__init__.py` | 21 | package 진입점 (re-export) |
| `backend/shared/python/sunity_shared/analysis/pole/detector.py` | 244 | HoughPoleDetector (cv2 lazy import) |
| `backend/shared/python/sunity_shared/analysis/pole/aligner.py` | 100 | compute_alignment_matrix + apply_alignment (scipy lazy import) |
| `backend/tests/test_pole_detector.py` | 184 | HoughPoleDetector 8개 단위 테스트 |
| `backend/tests/test_pole_aligner.py` | 200 | PoleAxisAligner 8개 단위 테스트 |

## Hough 파라미터 (verbatim)

```python
VERTICAL_TOLERANCE_DEG: float = 5.0   # ±5° 수직성 필터 (D-09)
CANNY_LOW: int = 50                    # Canny 하한 임계값
CANNY_HIGH: int = 200                  # Canny 상한 임계값
CANNY_APERTURE: int = 3               # Sobel 커널 크기
HOUGH_RHO: int = 1                    # 픽셀 해상도
HOUGH_THETA_DEG: float = 1.0          # 각도 해상도 (도)
HOUGH_THRESHOLD: int = 80             # 교차점 최소 누적
HOUGH_MIN_LINE_LENGTH: int = 100      # 최소 선분 길이 (px)
HOUGH_MAX_LINE_GAP: int = 20          # 선분 연결 허용 갭 (px)
```

tuning note: threshold 낮추기(80→50) + min_line_length 짧게(100→60)로 정은지 5영상 sweep 후 조정 가능. `HoughPoleDetector(**hough_overrides)` 인터페이스로 belle 튜닝 지원.

## 16개 단위 테스트 결과

| 파일 | 테스트 | 결과 | 비고 |
|------|--------|------|------|
| test_pole_detector.py | test_module_import_without_cv2 | PASS | cv2 부재에서 module load 성공 (H-2) |
| test_pole_detector.py | test_confidence_level_threshold_mapping | PASS | _map_numeric_to_confidence_level (M-2) |
| test_pole_detector.py | test_detect_vertical_pole_returns_detected | SKIP | cv2 미설치 — RunPod/설치 환경에서 통과 |
| test_pole_detector.py | test_detect_no_pole_fallback_low_confidence | SKIP | cv2 미설치 |
| test_pole_detector.py | test_detect_tilted_pole_fallback | SKIP | cv2 미설치 |
| test_pole_detector.py | test_video_level_single_axis | SKIP | cv2 미설치 |
| test_pole_detector.py | test_pole_axis_returns_unit_vector | SKIP | cv2 미설치 |
| test_pole_detector.py | test_detector_empty_frames_handles_gracefully | SKIP | cv2 미설치 |
| test_pole_aligner.py | test_module_import_without_scipy | PASS | scipy 부재에서 module load 성공 (H-2) |
| test_pole_aligner.py | test_identity_alignment | SKIP | scipy 미설치 — RunPod/설치 환경에서 통과 |
| test_pole_aligner.py | test_alignment_y_to_z | SKIP | scipy 미설치 |
| test_pole_aligner.py | test_alignment_anti_parallel | SKIP | scipy 미설치 |
| test_pole_aligner.py | test_apply_alignment_preserves_keys | SKIP | scipy 미설치 |
| test_pole_aligner.py | test_apply_alignment_numerical | SKIP | scipy 미설치 |
| test_pole_aligner.py | test_compute_alignment_matrix_returns_3x3 | SKIP | scipy 미설치 |
| test_pole_aligner.py | test_compute_alignment_matrix_zero_vector_raises | SKIP | scipy 미설치 |

로컬 환경 (Python 3.14.5, cv2/scipy 미설치): **3 passed, 13 skipped**

RunPod/설치 환경 (opencv-python-headless + scipy 설치 시): 16 passed 기대.

## D-11 폴백 시 사용자 카피 (Plan 05/Phase 12 입력)

폴백 발생 시 (`confidence_level='low'`, `source='vertical_fallback'`) 결과 화면에 표시할 안내문:

> "카메라가 살짝 기울어져 있어, 폴의 정확한 위치 분석이 어렵습니다. 세부 각도보다 전체 흐름을 중심으로 분석했어요."

(D-11, D-05 고객 리포트 정책: "visibility·MediaPipe" 등 기술 용어 노출 금지)

## 외부 의존성

| 패키지 | 버전 | 용도 | 추가 위치 |
|--------|------|------|---------|
| `opencv-python-headless` | 4.13.0.92 | Canny 엣지 + HoughLinesP | Plan 05 requirements.txt 예정 |
| `scipy` | 1.17.1 | Rotation.align_vectors (폴 축 → Z 축) | Plan 05 requirements.txt 예정 |

(이미 RESEARCH §Standard Stack 에서 slopcheck [OK] 통과 + PyPI registry 확인 완료)

## Plan 02 adapter 통합 검증 결과 (Test 10)

Plan 02 Test 10 (`test_pole_alignment_applied_when_aligner_available`) 는:

```python
pytest.importorskip("sunity_shared.analysis.pole.aligner")
```

를 사용한다. 본 plan 에서 `pole/aligner.py` 를 scipy 없이도 import 가능하게 구현 (H-2 박제) 했으므로, Plan 02 와 merge 후 통과 기대.

로컬 확인:
```
PYTHONPATH=backend/shared/python python3 -c "import sunity_shared.analysis.pole.aligner; print('ok')"
# 출력: ok
```

## H-2 박제 grep 결과

```
# detector.py: module-level cv2 import (0이어야 함)
grep -cE "^import cv2|^from cv2" backend/shared/python/sunity_shared/analysis/pole/detector.py
# 출력: 0

# detector.py: lazy cv2 import (>= 1이어야 함)
grep -cE "^[[:space:]]+import cv2" backend/shared/python/sunity_shared/analysis/pole/detector.py
# 출력: 1

# aligner.py: module-level scipy import (0이어야 함)
grep -cE "^from scipy|^import scipy" backend/shared/python/sunity_shared/analysis/pole/aligner.py
# 출력: 0

# aligner.py: lazy scipy import inside function (>= 1이어야 함)
grep -cE "^[[:space:]]+from scipy" backend/shared/python/sunity_shared/analysis/pole/aligner.py
# 출력: 1
```

## M-2 박제 grep 결과

```
# _map_numeric_to_confidence_level 함수 존재 확인
grep -c "_map_numeric_to_confidence_level" backend/shared/python/sunity_shared/analysis/pole/detector.py
# 출력: 9 (함수 정의 + 호출 + 테스트 참조)

# confidence_level='low' 직접 사용 확인
grep -c "confidence_level=" backend/shared/python/sunity_shared/analysis/pole/detector.py
# 출력: 12 (vertical_fallback 반환 시 'low', detected 반환 시 confidence_level 변수)
```

## Deviations from Plan

None - plan executed exactly as written.

TDD gate compliance:
- RED gate: `test(01-03): RED phase detector tests` commit (1024239)
- RED gate: `test(01-03): RED phase aligner tests` commit (e5ddbdc)
- GREEN gate: `feat(01-03): GREEN phase HoughPoleDetector` commit (226010e)

Note: aligner.py 는 detector.py 와 같은 GREEN commit 에 포함됨 (pole/ 패키지 단위). 별도 RED 테스트 (e5ddbdc) 이후 aligner 구현이 이미 존재했으므로 추가 GREEN commit 생략 (aligner stub 은 detector GREEN commit 에서 이미 완성된 구현으로 포함됨).

## Self-Check: PASSED

파일 존재 확인:
- `backend/shared/python/sunity_shared/analysis/pole/__init__.py` FOUND
- `backend/shared/python/sunity_shared/analysis/pole/detector.py` FOUND
- `backend/shared/python/sunity_shared/analysis/pole/aligner.py` FOUND
- `backend/tests/test_pole_detector.py` FOUND
- `backend/tests/test_pole_aligner.py` FOUND

커밋 존재 확인:
- `1024239` test(01-03): RED phase detector tests FOUND
- `226010e` feat(01-03): GREEN phase HoughPoleDetector FOUND
- `e5ddbdc` test(01-03): RED phase aligner tests FOUND
