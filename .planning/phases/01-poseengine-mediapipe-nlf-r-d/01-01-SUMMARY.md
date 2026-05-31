---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "01"
subsystem: pose-engine
tags:
  - data-contract
  - pose-frame
  - pole-axis
  - reliability-gate
  - tdd
dependency_graph:
  requires: []
  provides:
    - PoseFrame dataclass (Python + TS + contract.md 3-way lockstep)
    - PoleAxis dataclass
    - ReliabilityLevel / ConfidenceLevel type aliases
    - compute_angle_with_reliability stub
    - Wave 1/2 test fixtures
  affects:
    - backend/shared/python/sunity_shared/ (new pose_frame.py, reliability.py)
    - app/src/types/analysis.ts (PoseFrame/PoleAxis interfaces added)
    - docs/contract.md (§3 corrected, §6 new section)
tech_stack:
  added:
    - pose_frame.py: frozen dataclass pattern, Literal types
    - reliability.py: compute_angle_with_reliability gate stub
  patterns:
    - TDD RED/GREEN per task (pytest)
    - 3-way lockstep (Python dataclass, TS interface, contract.md)
    - Dependency injection (compute_fn arg in reliability gate)
key_files:
  created:
    - backend/shared/python/sunity_shared/analysis/pose_frame.py (317 lines)
    - backend/shared/python/sunity_shared/analysis/reliability.py (91 lines)
    - backend/tests/test_pose_frame_contract.py (215 lines)
    - backend/tests/test_reliability_gate.py (106 lines)
    - backend/tests/fixtures/__init__.py (6 lines)
    - backend/tests/fixtures/synthetic_frames.py (84 lines)
    - backend/tests/fixtures/mediapipe_landmarks.py (132 lines)
  modified:
    - backend/shared/python/sunity_shared/models.py (+re-export PoseFrame/PoleAxis)
    - app/src/types/analysis.ts (+PoseFrame/PoleAxis interfaces, 115 lines added)
    - docs/contract.md (§3 angles flat correction + §6 new 80 lines)
decisions:
  - "RELIABILITY_HIGH_THRESHOLD=0.7 / RELIABILITY_MEDIUM_THRESHOLD=0.4 — defensible default (belle 검토 후 갱신 가능)"
  - "to_coco17_array() returns (T,17,4) NaN-filled for missing frames"
  - "_LOW_THRESHOLD reuses RELIABILITY_MEDIUM_THRESHOLD — single source of truth"
  - "ROADMAP Success#3 already had video-level wording from --reviews replan (L-1 pre-resolved)"
metrics:
  duration: "~45 minutes"
  completed: "2026-05-31"
  tasks_completed: 3
  tests_added: 12
  files_created: 7
  files_modified: 3
---

# Phase 1 Plan 01: PoseFrame 데이터 계약 3-way Lockstep Summary

PoseFrame + PoleAxis Python dataclass, TS interface, docs/contract.md §6 를 동일 필드 집합으로 정의하고, reliability 게이트 stub + Wave 1/2 테스트 픽스처를 생성했다.

## 생성된 파일 목록

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `backend/shared/python/sunity_shared/analysis/pose_frame.py` | 317 | PoseFrame + PoleAxis + Landmark3D + Keypoint3D + compute_frame_reliability |
| `backend/shared/python/sunity_shared/analysis/reliability.py` | 91 | compute_angle_with_reliability stub + ANGLE_REQUIRED_KEYPOINTS |
| `backend/tests/test_pose_frame_contract.py` | 215 | PoseFrame 계약 단위 테스트 8개 |
| `backend/tests/test_reliability_gate.py` | 106 | reliability gate 단위 테스트 4개 |
| `backend/tests/fixtures/__init__.py` | 6 | fixture 패키지 |
| `backend/tests/fixtures/synthetic_frames.py` | 84 | Hough 검출용 합성 프레임 3종 |
| `backend/tests/fixtures/mediapipe_landmarks.py` | 132 | MediaPipe 33-landmark mock 4종 |

수정된 파일:
- `backend/shared/python/sunity_shared/models.py`: PoseFrame/PoleAxis re-export 추가
- `app/src/types/analysis.ts`: PoseFrame/PoleAxis/Landmark3D 등 TS interface 추가 (~115줄)
- `docs/contract.md`: §3 angles flat 정정(M-5) + §6 신규 PoseFrame/PoleAxis 섹션(~80줄)

## 12개 contract+gate 테스트 결과

```
backend/tests/test_pose_frame_contract.py  (8 tests)   PASS
backend/tests/test_reliability_gate.py     (4 tests)   PASS
                                           ─────────
                                           12 passed
```

## TS typecheck 결과

`npm run typecheck` (main repo, node_modules installed): PASS (0 errors)

## Wave 1/2 에 노출되는 public API

| 심볼 | 위치 | 용도 |
|------|------|------|
| `PoseFrame` | `pose_frame.py` | 영상 한 프레임 포즈 계약 |
| `PoleAxis` | `pose_frame.py` | 폴 축 메타 |
| `Landmark3D` | `pose_frame.py` | MediaPipe 33 raw landmark |
| `Keypoint3D` | `pose_frame.py` | COCO-17 keypoint + confidence |
| `ConfidenceLevel` | `pose_frame.py` | 'high'\|'medium'\|'low' (M-2 D-11) |
| `ReliabilityLevel` | `pose_frame.py` | 'high'\|'medium'\|'low' (H-4) |
| `compute_frame_reliability` | `pose_frame.py` | mean_visibility → ReliabilityLevel |
| `compute_angle_with_reliability` | `reliability.py` | 각도 계산 + 저신뢰 마킹 stub |
| `ANGLE_REQUIRED_KEYPOINTS` | `reliability.py` | 각도 키 → 필수 keypoint 매핑 |
| `synthetic_vertical_pole_frames` | `fixtures/synthetic_frames.py` | Hough 검출 성공 케이스 |
| `synthetic_no_pole_frames` | `fixtures/synthetic_frames.py` | Hough 검출 실패 케이스 |
| `synthetic_tilted_pole_frames` | `fixtures/synthetic_frames.py` | 기울어진 폴 케이스 |
| `make_mock_world_landmarks_33` | `fixtures/mediapipe_landmarks.py` | 33 landmark mock |
| `make_mock_no_human_result` | `fixtures/mediapipe_landmarks.py` | NoHumanError 트리거 케이스 |

## REVIEWS 박제 확인

| 이슈 | 확인 | 근거 |
|------|------|------|
| H-3: PoseFrame.pole_axis 필드 누락 | FIXED | `pole_axis: PoleAxis \| None` Python + `poleAxis: PoleAxis \| null` TS + contract.md §6 |
| H-4: reliability 게이트 미존재 | FIXED | `PoseFrame.reliability`, `compute_frame_reliability`, `compute_angle_with_reliability` |
| M-1: raw_visibility/raw_presence 명명 | FIXED | `raw_visibility: float`, `raw_presence: float` in Landmark3D |
| M-2: confidence_level enum | FIXED | `ConfidenceLevel = Literal['high','medium','low']` |
| M-5: contract.md angles[][] 불일치 | FIXED | `angles? number[] flat 시퀀스` (§3 정정) |
| L-1: ROADMAP Success#3 wording | PRE-RESOLVED | `--reviews` replan 에서 이미 정정됨 (video-level PoleAxis) |

## belle 확정 보류 항목

- **A1 (MediaPipe COCO-17 매핑 공식 검증)**: Wave 1 Plan 02 (MediaPipePoseEngine 어댑터) Task 1에서 수동 검증 예정. `MediaPipe33ToCOCO17Adapter` 구현 시 COCO-17 인덱스 매핑 확정 필요.
- **임계값 조정**: `RELIABILITY_HIGH_THRESHOLD=0.7` / `RELIABILITY_MEDIUM_THRESHOLD=0.4` 는 defensible default. belle 검토 후 조정 가능 — 조정 시 `pose_frame.py` 두 상수만 변경하면 downstream 전체 반영.

## Deviations from Plan

None - plan executed exactly as written.

Note: L-1 (ROADMAP Success#3 wording 정정)은 `--reviews` replan 시 이미 반영되어 있어 추가 작업 불필요였음. 이를 deviation 이 아닌 pre-resolved 로 분류.

## Self-Check: PASSED

파일 존재 확인:
- `backend/shared/python/sunity_shared/analysis/pose_frame.py` FOUND
- `backend/shared/python/sunity_shared/analysis/reliability.py` FOUND
- `backend/tests/test_pose_frame_contract.py` FOUND
- `backend/tests/test_reliability_gate.py` FOUND
- `backend/tests/fixtures/synthetic_frames.py` FOUND
- `backend/tests/fixtures/mediapipe_landmarks.py` FOUND

커밋 존재 확인:
- `48c7a1d` test(01-01): RED phase contract tests FOUND
- `6e96b84` feat(01-01): GREEN phase PoseFrame FOUND
- `1c79efa` test(01-01): RED phase reliability tests FOUND
- `1ad3a14` feat(01-01): GREEN phase reliability + contract.md FOUND
- `180579f` feat(01-01): TS interfaces + fixtures FOUND
