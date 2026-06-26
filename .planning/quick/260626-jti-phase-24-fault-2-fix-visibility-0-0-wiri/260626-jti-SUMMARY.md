---
task: 260626-jti
phase: 24
fault: "② visibility=0.0 wiring"
subsystem: backend/pipeline
tags: [bugfix, wiring, vision-gate, alignment, pose-frame]
key-files:
  modified:
    - backend/functions/pipeline/app.py
    - backend/tests/test_pipeline_vision_gate.py
commits:
  - 81e7f56
status: complete
---

# Phase 24 결함 ② Fix: `_pose_frame_keypoints` visibility=0.0 배선 버그 Summary

`_pose_frame_keypoints` 가 부재 필드 `.keypoints` 대신 실제 `PoseFrame.keypoints_3d`
(dict[str, Keypoint3D]) 의 confidence 평균을 읽도록 고쳐, 모든 클립에서 alignment
visibility 가 0.0 으로 죽어 Gemini collect 가 low_alignment 로 bail 하던 배선 버그를 해소.

## 확인한 버그 (코드로 검증)

- `PoseFrame` 의 실제 필드는 `keypoints_3d: dict[str, Keypoint3D]`
  (`backend/shared/python/sunity_shared/analysis/pose_frame.py:231`). `keypoints` 속성은 없음.
- `Keypoint3D.confidence: float` 0.0~1.0 (`pose_frame.py:114`).
- 구코드 `getattr(pf, "keypoints", None)` → 항상 `None`. dict-fallback `pf.get("keypoints")`
  도 키 부재. 설령 `keypoints_3d` 를 잡았어도 `for kp in (kps or [])` 는 dict 를 순회하면
  KEY(문자열)만 돌아 `getattr(str, "confidence")` = None → `confs=[]` → `mean_conf=None`.
- 결과 체인: `mean_conf=None` → `SelectedFramePair.student_confidence=None`
  (`app.py:1718`) → alignment `visibility=0.0` (전 클립) → `local_ok` 항상 실패 →
  Gemini collect `low_alignment` bail. (메모리 핸드오프: pod sweep vis=0.0 on all 12 members.)

## 적용한 Fix

- `_pose_frame_keypoints` 가 `pf.keypoints_3d` (+ dict-pf fallback `pf.get("keypoints_3d")`)
  를 읽음. dict 면 `.values()` 로 순회해 각 `.confidence` 수집, finite 값만 평균.
  결측/실패 → `None` graceful 유지 (try/except → None, 분석 흐름 차단 0).
- 반환 keypoints 객체도 `keypoints_3d` 로 일관 (`student_keypoints: object` generic 이라 호환).
- 순수 helper 유지 — 신규 heavy import 0. finite 검사는 이미 import 된 `np.isfinite` 사용
  (`math` 미import 라 numpy 재사용; 새 의존 회피).

## 손대지 않은 것 (제약 준수)

- alignment 임계값 (`_ALIGN_VIS_MIN`, `_ALIGN_GLOBAL_T1/T2`), slope, cap, scoring 로직 무변경.
- 밴드/cap 산식 무도입.

## Deviations from Plan

`np.isfinite` 사용 — 계획은 "numpy/stdlib only" 였고 `math` 가 app.py 에 미import 라
이미 모듈 전역에 있는 `np` 를 재사용 (신규 import 0). 동작 동일, 제약 내 결정.
그 외 plan 그대로 실행.

## Gates

- `python3 -m pytest backend/tests/test_pipeline_vision_gate.py -q` → 38 passed (신규 3건 포함).
- `python3 -m pytest backend/tests/test_pipeline_deduction_seam.py -q` → 18 passed (인접 회귀 0).
- Band grep `apply_downward_cap|SEVERITY_CAP|capApplied` over
  `backend/shared/python` + `backend/functions` → **0 matches**.
- Pod/GPU/network 미실행 (제약 준수).

## 추가한 회귀 가드 (test_pipeline_vision_gate.py::TestPoseFrameKeypoints)

- `test_reads_keypoints_3d_confidence_mean` — confidences [0.6,0.7,0.8,0.9] → mean_conf ≈ 0.75 > 0
  (visibility 가 더 이상 죽지 않음).
- `test_empty_keypoints_returns_none_conf` — 빈 keypoints_3d → mean_conf=None.
- `test_out_of_range_idx_returns_none` — 범위 밖 idx / 빈 list → None.

## Self-Check: PASSED

- backend/functions/pipeline/app.py — FOUND (modified, committed)
- backend/tests/test_pipeline_vision_gate.py — FOUND (modified, committed)
- commit 81e7f56 — FOUND in git log
