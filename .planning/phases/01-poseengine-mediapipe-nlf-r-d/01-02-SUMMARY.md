---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "02"
subsystem: pose-engine
tags:
  - mediapipe-adapter
  - coco17-mapping
  - pole-extension
  - lazy-import
  - tdd
dependency_graph:
  requires:
    - 01-01 (PoseFrame/PoleAxis/Landmark3D/Keypoint3D dataclasses, compute_frame_reliability)
    - 01-01 (tests/fixtures/mediapipe_landmarks.py mock fixtures)
  provides:
    - PoseEngine Protocol (interfaces.py — estimate(frames, pole_axis)->list[PoseFrame])
    - MediaPipePoseEngine 어댑터 (lazy mediapipe import, factory DI)
    - MediaPipe33ToCOCO17 매핑 + 폴 확장 6키 (adapters/mediapipe_to_coco17.py)
    - 20개 단위 테스트 (19 pass, 1 skip)
  affects:
    - backend/shared/python/sunity_shared/analysis/interfaces.py (PoseEngine Protocol 추가)
    - backend/shared/python/sunity_shared/analysis/adapters/ (신규 패키지)
    - backend/shared/python/sunity_shared/analysis/pose_engines/ (신규 패키지)
tech_stack:
  added:
    - adapters/mediapipe_to_coco17.py: 33→COCO-17 + 폴 확장(toe/heel/grip) 변환 어댑터
    - pose_engines/mediapipe_engine.py: MediaPipePoseEngine lazy import 패턴
    - pose_engines/__init__.py: lazy __getattr__ export (H-2 박제)
  patterns:
    - TDD RED/GREEN per task (pytest)
    - Lazy import (mediapipe: __init__ 내부에서만)
    - DI factory classmethod (create_with_landmarker — mock 주입)
    - Duck-typed MediaPipe API 변환 (M-1 raw_visibility/raw_presence)
    - Derived landmark 평균 (M-3 grip)
key_files:
  created:
    - backend/shared/python/sunity_shared/analysis/interfaces.py (85 lines, PoseEngine 추가)
    - backend/shared/python/sunity_shared/analysis/adapters/__init__.py (23 lines)
    - backend/shared/python/sunity_shared/analysis/adapters/mediapipe_to_coco17.py (331 lines)
    - backend/shared/python/sunity_shared/analysis/pose_engines/__init__.py (23 lines)
    - backend/shared/python/sunity_shared/analysis/pose_engines/mediapipe_engine.py (204 lines)
    - backend/tests/test_adapter_mediapipe_to_coco17.py (338 lines)
    - backend/tests/test_pose_engine_interface.py (286 lines)
  modified:
    - backend/shared/python/sunity_shared/analysis/interfaces.py (PoseEngine Protocol + DEPRECATED 마킹)
decisions:
  - "PoseEstimator(기존) DEPRECATED 마킹 — PoseEngine이 유일한 신규 계약. 하위호환 유지"
  - "adapters/ 디렉터리: 스키마 변환 어댑터 모음 (RESEARCH 권장 구조)"
  - "pose_engines/ 디렉터리: 포즈 엔진 어댑터 (MediaPipe 제품, NLF는 R&D 격리)"
  - "GRIP_LEFT = (15,17,21): wrist+pinky+thumb 평균 (A2 belle confirm 보류)"
  - "pole.aligner import 실패 시 raw xyz → Keypoint3DAligned 복사 폴백 (Plan 03 완성 전)"
  - "미감지 frame sentinel: PoseFrame.empty + pole_axis 보존 (H-3 박제)"
metrics:
  duration: "~9 minutes"
  completed: "2026-05-31"
  tasks_completed: 2
  tests_added: 20
  files_created: 7
  files_modified: 1
---

# Phase 1 Plan 02: PoseEngine Protocol + MediaPipe 33→COCO-17 어댑터 Summary

PoseEngine Protocol(estimate→list[PoseFrame]) + MediaPipePoseEngine lazy import 어댑터 + MediaPipe33→COCO-17+폴 확장 변환 어댑터를 구현하고 20개 단위 테스트로 박제했다.

## 생성된 파일 목록

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `analysis/interfaces.py` | 85 | PoseEngine Protocol 추가 (PoseEstimator DEPRECATED) |
| `analysis/adapters/__init__.py` | 23 | 어댑터 패키지 초기화 |
| `analysis/adapters/mediapipe_to_coco17.py` | 331 | 33→COCO-17 + 폴 확장 6키 변환 |
| `analysis/pose_engines/__init__.py` | 23 | lazy __getattr__ export (H-2) |
| `analysis/pose_engines/mediapipe_engine.py` | 204 | MediaPipePoseEngine Tasks API 어댑터 |
| `tests/test_adapter_mediapipe_to_coco17.py` | 338 | 어댑터 단위 테스트 10개 |
| `tests/test_pose_engine_interface.py` | 286 | 엔진 단위 테스트 10개 |

## PoseEngine Protocol 시그니처

```python
# backend/shared/python/sunity_shared/analysis/interfaces.py
class PoseEngine(Protocol):
    def estimate(
        self,
        frames: np.ndarray,       # (T,H,W,3) RGB uint8
        pole_axis: "PoleAxis",    # PoleDetector 산출 (D-10/D-11)
    ) -> "list[PoseFrame]":
        """프레임 시퀀스 → list[PoseFrame]. 전 프레임 미감지 시 NoHumanError."""
        ...
```

RESEARCH §Pattern 1 + D-04 + REVIEWS H-3 (pole_axis 인자) 박제.

## MediaPipe 33→COCO-17 매핑 표

| COCO-17 keypoint | MediaPipe index | MediaPipe 명칭 |
|------------------|-----------------|-----------------|
| nose | 0 | nose |
| left_eye | 2 | left eye (center) |
| right_eye | 5 | right eye (center) |
| left_ear | 7 | left ear |
| right_ear | 8 | right ear |
| left_shoulder | 11 | left shoulder |
| right_shoulder | 12 | right shoulder |
| left_elbow | 13 | left elbow |
| right_elbow | 14 | right elbow |
| left_wrist | 15 | left wrist |
| right_wrist | 16 | right wrist |
| left_hip | 23 | left hip |
| right_hip | 24 | right hip |
| left_knee | 25 | left knee |
| right_knee | 26 | right knee |
| left_ankle | 27 | left ankle |
| right_ankle | 28 | right ankle |

A1 belle 확정 보류 — RESEARCH §Pattern 3 기반 명칭 추론. Plan 06 회귀 검증(정은지 5영상) 후 갱신 예정.

## 폴 확장 매핑 표

| 폴 확장 키 | 값 | 비고 |
|------------|-----|------|
| left_heel | MP[29] | raw 직접 추출 |
| right_heel | MP[30] | raw 직접 추출 |
| left_foot_index | MP[31] | raw 직접 추출 (toe) |
| right_foot_index | MP[32] | raw 직접 추출 (toe) |
| pole_grip_left | avg(MP[15,17,21]) | derived: wrist+pinky+thumb — A2 belle confirm 보류 |
| pole_grip_right | avg(MP[16,18,22]) | derived: wrist+pinky+thumb — A2 belle confirm 보류 |

## 20개 단위 테스트 결과

```
tests/test_adapter_mediapipe_to_coco17.py    (10 tests)
  PASS: test_coco17_index_mapping_exact
  PASS: test_pole_extension_includes_toe_heel_grip
  PASS: test_pole_grip_derived_from_wrist_pinky_thumb
  PASS: test_convert_landmarks_basic
  PASS: test_convert_raw_visibility_presence_named_correctly
  PASS: test_convert_pole_extension_present
  PASS: test_convert_low_confidence_keypoint_marked
  PASS: test_pole_axis_preserved_in_pose_frame
  PASS: test_reliability_computed_from_mean_visibility
  SKIP: test_pole_alignment_applied_when_aligner_available  (pole.aligner Plan 03 미완성)

tests/test_pose_engine_interface.py           (10 tests)
  PASS: test_engine_estimate_returns_pose_frames
  PASS: test_engine_propagates_pole_axis_to_pose_frame
  PASS: test_engine_no_human_error
  PASS: test_engine_partial_detection_sentinel
  PASS: test_engine_timestamp_monotonic
  PASS: test_engine_model_path_missing
  PASS: test_engine_lazy_import_no_mediapipe
  PASS: test_module_import_without_mediapipe
  PASS: test_confidence_conversion_in_engine
  PASS: test_reliability_set_in_engine
                                              ─────────
                                              19 passed, 1 skipped
```

Test 10 (adapter): `pytest.importorskip("sunity_shared.analysis.pole.aligner")` — Plan 03 완성 후 통과 예정.

## belle 확정 보류 항목

- **A1 (33→COCO-17 매핑)**: RESEARCH §Pattern 3 + MediaPipe 공식 문서 명칭 기반 추론. Plan 06 회귀 검증(정은지 5영상)에서 실제 좌표 확인 후 갱신. 코드 주석에 "A1 belle 확정 보류" 명시.
- **A2 (grip derived 인덱스)**: GRIP_LEFT_SOURCE_INDICES=(15,17,21), GRIP_RIGHT=(16,18,22). wrist+pinky+thumb 평균. 폴 잡는 위치에 따라 최적 조합 다를 수 있음. Plan 06 회귀 검증 후 갱신. 코드 주석에 "A2 belle confirm grip derivation" 명시.

## REVIEWS 박제 확인

| 이슈 | 확인 | 근거 |
|------|------|------|
| M-1: raw_visibility/raw_presence 명명 | FIXED | `_landmark_to_dict`: visibility→raw_visibility, presence→raw_presence |
| M-3: pole_grip_left/pole_grip_right | FIXED | POLE_EXTENSION_MAP에 derived tuple로 추가 |
| H-2: module-level mediapipe import 0 | FIXED | grep 결과 0 lines (mediapipe_engine.py) |
| H-3: pole_axis PoseFrame 보존 | FIXED | convert_landmarks_to_coco17_and_pole_ext + PoseFrame.empty 모두 pole_axis 전달 |
| H-4: reliability 어댑터 산출 | FIXED | compute_frame_reliability(mean_visibility) 호출 |
| Pitfall 1: ARM64 fail-fast | FIXED | RuntimeError 안내 "RunPod(x86_64)에서만 동작" |
| Pitfall 2: timestamp 단조 증가 | FIXED | `int(t * 1000 / self._target_fps)` |

## H-2 박제 확인 (module-level mediapipe import)

```bash
grep -nE "^import mediapipe|^from mediapipe" \
  backend/shared/python/sunity_shared/analysis/pose_engines/mediapipe_engine.py | wc -l
# → 0
```

모듈 로드 테스트:
```bash
python3 -c "from sunity_shared.analysis.pose_engines.mediapipe_engine import MediaPipePoseEngine; print('module loaded without mediapipe')"
# → module loaded without mediapipe
```

## 다음 wave (Plan 03 PoleDetector) 의존성

- `sunity_shared.analysis.pole.aligner` — `compute_alignment_matrix`, `apply_alignment` 함수 필요
- Plan 03 완성 시: adapter Test 10 (`test_pole_alignment_applied_when_aligner_available`) 자동으로 통과
- 현재 폴백: raw Keypoint3D xyz → Keypoint3DAligned 복사 (identity 회전, alignment 없음)

## Deviations from Plan

None — plan executed exactly as written.

- Task 1 RED→GREEN: 9 pass + 1 skip (Test 10 importorskip — 계획된 동작)
- Task 2 RED→GREEN: 10 pass
- pole.aligner 폴백: 계획된 `try/except ImportError` 처리 (Action §5에 명시)

## Known Stubs

- `POLE_EXTENSION_MAP['pole_grip_left'] = GRIP_LEFT_SOURCE_INDICES = (15, 17, 21)` — A2 belle confirm 보류. grip derivation 인덱스는 Plan 06 회귀 검증 후 갱신 예정. 현재 wrist+pinky+thumb 평균으로 기능은 완전히 구현됨.

## Self-Check: PASSED

파일 존재 확인:
- `backend/shared/python/sunity_shared/analysis/interfaces.py` FOUND
- `backend/shared/python/sunity_shared/analysis/adapters/__init__.py` FOUND
- `backend/shared/python/sunity_shared/analysis/adapters/mediapipe_to_coco17.py` FOUND
- `backend/shared/python/sunity_shared/analysis/pose_engines/__init__.py` FOUND
- `backend/shared/python/sunity_shared/analysis/pose_engines/mediapipe_engine.py` FOUND
- `backend/tests/test_adapter_mediapipe_to_coco17.py` FOUND
- `backend/tests/test_pose_engine_interface.py` FOUND

커밋 존재 확인:
- `ee0a6ae` test(01-02): RED phase adapter tests FOUND
- `0c79e26` feat(01-02): GREEN phase Task 1 FOUND
- `b5de382` test(01-02): RED phase engine tests FOUND
- `1c98c89` feat(01-02): GREEN phase Task 2 FOUND
