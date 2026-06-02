---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "22"
subsystem: ml-pose-engine
status: complete
tags:
  - rtmw
  - 3d-path
  - motionbert-lifter
  - option-b
  - plan-22
  - wave-3
  - belle-checkpoint
  - lr-swap-gate

dependency_graph:
  requires:
    - 01-07  # MotionBERT-lite spike — Apache-2.0 lifter 박제
    - 01-17  # keypoint mapping fix (Cycle 3 audit, swap_ratio 회귀 root cause)
    - 01-19  # PoseEngine Protocol + PoseFrame.body_shape
    - 01-20  # weights_manifest.json (RTMW 2D production_eligible=true)
    - 01-21  # RTMWPoseEngine (plan 21 운영 path)
  provides:
    - "backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/lifter_pipeline.py — RTMWLifterPoseEngine (옵션 B 실 구현, PoseEngine Protocol)"
    - "backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/three_d_path_decision.md §5 — selected: option_b 마커 박제 (plan 24 grep 의존)"
    - "RTMW 2D + MotionBERT 3D 결합 운영 path — single camera 3D 산출 가능"
    - "selected-path pytest 게이트 (test_rtmw_3d_path_selected.py) — swap_ratio 0 + z 분산 > 0 회귀 방지"
  affects:
    - 01-23  # 회귀 검증 — 본 plan 의 선택된 path 입력
    - 01-24  # R&D 격리 — 비선택 옵션 A (rtmw3d_engine.py) + MediaPipeWithLifterEngine 격리 대상
    - 01-25  # pipeline atomic swap — RTMWLifterPoseEngine 운영 path 연결

tech_stack:
  added: []
  patterns:
    - "DI factory (create_with_engines) — 단위 테스트 mock RTMW + mock lifter 주입"
    - "lazy DI _ensure_components — rtmw_engine/lifter 미주입 시 plan 21 + plan 07 lazy 생성"
    - "PoseFrame replace (dataclass frozen=True) — keypoints_3d/keypoints_3d_pole_aligned/reliability 교체, raw_keypoints_133/keypoints_2d/pole_axis 보존"
    - "plan 17 mapping fix 정합 — KEYPOINT_NAMES (skeleton.py) 단일 source of truth"
    - "selected-path pytest 게이트 — synthetic mock 입력으로 swap_ratio 회귀 차단"

key_files:
  created:
    - backend/tests/test_rtmw_3d_path_selected.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-22-SUMMARY.md
  modified:
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/lifter_pipeline.py
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw3d_engine.py
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/three_d_path_decision.md
    - backend/tests/test_rtmw_3d_path.py

decisions:
  - "belle 결정 = approved: option_b (2026-06-03). RTMW 2D + MotionBERT lifter 운영 path 확정."
  - "옵션 A (RTMW3DPoseEngine) 비선택 — plan 24 R&D 격리 입력. weights_manifest 의 rtmw3d-x-384x288 entry 는 production_eligible=false 유지."
  - "옵션 B 결정 근거 (우선순위): 라이선스 (RTMW3D restricted vs RTMW 2D+MotionBERT Apache-2.0 박제) > 단계 분리 (2D/3D 독립 디버깅, plan 17 mapping fix 정합) > plan 23 회귀 검증 이연 (정확도/latency 측정 후 재평가)."
  - "MediaPipeWithLifterEngine (plan 08) 도 plan 24 R&D 격리 대상 — RTMW path 가 MediaPipe 를 대체."
  - "COCO-17 → H3.6M 17 변환은 pose_lifters/mediapipe_to_h36m17.py 의 H36M_TO_COCO17_LIMB_PAIRS canonical (plan 17 Cycle 3 audit) 정합. 본 plan 의 _coco17_to_h36m17_xy 가 동일 규칙으로 역방향 구현."
  - "test_rtmw_3d_path.py::test_both_engines_unselected_raises_not_implemented → test_unselected_option_a_raises_not_implemented 갱신 — Task 1 stub-level 게이트의 Task 2 후 의미 변화 반영 (옵션 B 실 구현 후 옵션 A 만 stub 검증)."

metrics:
  duration_minutes: 25
  completed_date: "2026-06-03"
  task_count: 2
  files_created: 2
  files_modified: 4
  tests_added: 3
  tests_passing: 139  # 5 + 3 새 tests + 131 회귀
---

# Phase 01 Plan 22: RTMW 3D Path 결정 + 옵션 B 실 구현 Summary

D-18 단일 카메라 3D path = RTMW 2D + MotionBERT lifter 확정. belle = `approved: option_b` (2026-06-03). 옵션 A (RTMW3D 직접) 는 비선택 — plan 24 R&D 격리 입력. plan 23 회귀 검증 진입 게이트 통과.

---

## belle Checkpoint 결과

**응답:** `approved: option_b` (2026-06-03)

**박제 위치:** `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/three_d_path_decision.md` §5 — 마커 라인 `selected: option_b` 정확 문자열 (plan 24 grep 의존).

### 선택 근거 (핵심 3가지, 우선순위 순)

1. **라이선스 정합 (기준 c):** 옵션 A 의 RTMW3D `rtmw3d-x-384x288` 은 `weights_manifest.json` 에서 `license_status: restricted` + `production_eligible: false` (plan 20 audit 박제). 옵션 A 채택 시 belle 가중치 승급 결정 + commercial-clean 가중치 확보 필요 — 비용/일정 리스크. 옵션 B 는 RTMW 2D (plan 20 belle 승급 완료) + MotionBERT lite Apache-2.0 (plan 07 SUMMARY 박제) 로 즉시 조립 가능.

2. **단계 분리 (기준 b/d):** 옵션 B 의 2D (plan 21 RTMW) + 3D (plan 07 MotionBERT) 분리 path → plan 23 회귀 검증에서 swap_ratio + latency 를 각 단계별로 측정 가능. plan 17 mapping fix (Cycle 3 audit) 가 옵션 B 의 H3.6M ↔ COCO-17 변환에 즉시 적용 — swap_ratio 회귀 게이트 (`test_selected_engine_no_left_right_swap`) 강제.

3. **정확도 비교는 plan 23 이연 (기준 a):** 본 plan 단계에서 (a) 측정 불가. plan 23 의 ms/frame + 정확도가 임계 미달이면 옵션 A 재평가 (plan 24/25 입력). 단, 옵션 B 의 라이선스/단계 분리 이점이 plan 23 결과보다 선결과제.

---

## 비선택 옵션 A — plan 24 R&D 격리 대상

옵션 A (`rtmw3d_engine.py` RTMW3DPoseEngine) 는 **비선택, NotImplementedError stub 유지**. plan 24 가 격리 처리.

| 격리 대상 | 파일 | 비고 |
|-----------|------|------|
| RTMW3DPoseEngine | `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw3d_engine.py` | NotImplementedError stub (`__init__` + `estimate()` 둘 다). docstring 갱신 — "옵션 B 선택, plan 24 R&D 격리 대상" 명시. |
| RTMW3D 가중치 entry | `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/weights_manifest.json` | `rtmw3d-x-384x288` entry 의 `production_eligible: false` 유지 (D-25 게이트 잠금). |
| MediaPipeWithLifterEngine | `backend/shared/python/sunity_shared/analysis/pose_engines/mediapipe_lifter_engine.py` | RTMW path 가 MediaPipe path 를 대체 — plan 24 R&D 격리 대상 (별도 acceptance). |

### plan 24 의 acceptance 가 의존하는 grep

```bash
# 본 plan 의 §5 marker — plan 24 conditional 격리 acceptance 의 입력
grep -E "^selected: option_(a|b)$" backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/three_d_path_decision.md
# 결과: selected: option_b
```

---

## Task 별 산출

### Task 1 (Wave 3, 이미 완료 — commit 255fa76)

- `three_d_path_decision.md` 신설 (§1~§6 본문, §5 PENDING)
- `rtmw3d_engine.py` 옵션 A stub (LicenseViolationError 가드 + NotImplementedError)
- `lifter_pipeline.py` 옵션 B stub (NotImplementedError)
- `pose_engines/rtmw/__init__.py` + `pose_engines/__init__.py` lazy export
- `backend/tests/test_rtmw_3d_path.py` — 5 contract tests PASS

### Task 2 (본 commit aed6c35)

**three_d_path_decision.md §5:**
- `selected: option_b` 마커 라인 박제 (정확 문자열, plan 24 grep 의존)
- 결정일자 (2026-06-03), 응답자 (belle), 선택 path 명시
- 결정 근거 (라이선스 / 단계 분리 / plan 23 이연) 3개 박제
- 비선택 옵션 A 의 격리 대상 표 박제

**lifter_pipeline.py — RTMWLifterPoseEngine 실 구현:**
- `estimate()` 의 NotImplementedError 제거.
- 흐름: RTMW 2D (`_rtmw_engine.estimate`) → COCO-17 xy 추출 (`_extract_coco17_xy_from_pose_frames`) → COCO-17 → H3.6M 17 변환 (`_coco17_to_h36m17_xy`, 12 limb 직접 + 5 파생) → `_lifter.lift()` (T, 17, 3) → H3.6M → COCO-17 역변환 (`h36m17_to_coco17_subset`) → `_replace_keypoints` (PoseFrame frozen=true → `dataclasses.replace`).
- `_ensure_components` — rtmw_engine / lifter 미주입 시 plan 21 RTMWPoseEngine + plan 07 MotionBertLifter lazy 생성.
- D-20 / H-3 박제: raw_keypoints_133 / keypoints_2d / pole_axis / pole_extension_landmarks 모두 보존 (replace 가 keypoints_3d / keypoints_3d_pole_aligned / reliability 만 교체).
- plan 17 mapping fix 정합: `KEYPOINT_NAMES` (`skeleton.py`) 단일 source of truth → 좌/우 인덱스 swap 회귀 0.

**rtmw3d_engine.py:**
- docstring 갱신 — "옵션 A 어댑터 stub (Plan 01-22 비선택, R&D 격리 대상)" 명시.
- 코드 변경 없음 — NotImplementedError stub 유지 (`__init__` + `estimate()` 2개).

**test_rtmw_3d_path_selected.py — 3 new tests (DI factory):**
1. `test_selected_engine_no_not_implemented` — mock RTMW + mock lifter 주입 시 estimate() 가 `list[PoseFrame]` 반환 (NotImplementedError 미발생).
2. `test_selected_engine_z_coord_filled` — 모든 limb keypoint 의 z 가 NaN 아님 + 분산 > 0 (스칼라 0 채움 회귀 방지).
3. `test_selected_engine_no_left_right_swap` — 합성 입력 (좌=+x, 우=-x) → 어깨/팔꿈치/손목/엉덩이/무릎/발목 6쌍 모두 모든 프레임에서 좌.x > 우.x. swap_ratio = 0 (plan 17 회귀 방지).

**test_rtmw_3d_path.py 갱신:**
- `test_both_engines_unselected_raises_not_implemented` → `test_unselected_option_a_raises_not_implemented` 로 갱신. Task 2 후 옵션 B 실 구현으로 옵션 B 의 NotImplementedError 검증은 본 테스트에서 제거 (test_rtmw_3d_path_selected.py 가 list[PoseFrame] contract 검증으로 대체). 옵션 A 만 stub 유지 검증.

---

## Selected-Path pytest 결과 (Plan 22 Task 2 acceptance)

```
cd backend && python3 -m pytest tests/test_rtmw_3d_path_selected.py -x -q
... [100%]
3 passed in 0.06s
```

**3 tests PASS** — `test_selected_engine_no_not_implemented`, `test_selected_engine_z_coord_filled`, `test_selected_engine_no_left_right_swap`.

---

## 회귀 검증 (Plan 22 Task 2)

```
cd backend && python3 -m pytest tests/test_rtmw_3d_path.py tests/test_rtmw_3d_path_selected.py \
  tests/test_rtmw_engine.py tests/test_rtmw_133_to_coco17_adapter.py tests/test_rtmw_weights_manifest.py \
  tests/test_pose_engine_contract.py tests/test_pose_engine_interface.py tests/test_pose_frame_contract.py \
  tests/test_pose_lifters_mediapipe_to_h36m17.py tests/test_mediapipe_lifter_engine.py \
  tests/test_motionbert_lifter.py -q
... [100%]
136 passed in 0.26s
```

**Wave 1~3 회귀 0** — RTMW (plan 21), 133→COCO-17 어댑터, weights manifest, PoseEngine Protocol/interface, PoseFrame contract, pose lifters (plan 17 mapping audit), MediaPipeWithLifterEngine (plan 08), MotionBertLifter (plan 07) 전부 정상.

---

## Acceptance Gates (모두 PASS)

| Gate | Command | Expected | Actual |
|------|---------|----------|--------|
| §5 marker 박제 | `grep -E "^selected: option_(a\|b)$" three_d_path_decision.md` | 매치 = 1, `selected: option_b` | PASS |
| 옵션 B NotImplementedError 제거 | `grep -c "raise NotImplementedError" lifter_pipeline.py` | 0 | PASS (0) |
| 옵션 A NotImplementedError 유지 | `grep -c "raise NotImplementedError" rtmw3d_engine.py` | ≥ 1 | PASS (2) |
| selected-path test 파일 존재 | `test -f tests/test_rtmw_3d_path_selected.py` | 존재 | PASS |
| selected-path 3 tests PASS | `pytest tests/test_rtmw_3d_path_selected.py -x -q` | 3 passed | PASS |
| 회귀 0 | `pytest tests/test_rtmw_3d_path.py tests/test_rtmw_engine.py ...` | 모두 PASS | PASS (136 tests) |

---

## 다음 plan 진입 마커 (plan 23 회귀 검증)

- 본 plan 산출 운영 path = `RTMWLifterPoseEngine` (옵션 B). plan 23 의 5영상 회귀 검증 + IPSF score 측정 입력.
- 분석 정확도 (a) + ms/frame (b) plan 23 단계에서 산출. 임계 미달 시 옵션 A 재평가 → plan 24/25 별 plan 입력.
- plan 23 단위 테스트 fixture 후보: 본 plan 의 `_MockRTMWEngine` + `_MockLifter` 패턴 — synthetic 입력으로 contract 게이트 보존.

## Deviations from Plan

### Task 1 test 의미 변화 반영 (Rule 1 - 회귀 방지 amendment)

**Found during:** Task 2 회귀 검증 (commit aed6c35 직전)
**Issue:** Task 1 의 `test_both_engines_unselected_raises_not_implemented` 는 belle 결정 전 두 엔진 모두 stub 임을 검증. Task 2 가 옵션 B 의 NotImplementedError 를 제거하면 본 테스트가 FAIL — Task 2 후 의미 변화 미반영.
**Fix:** `test_unselected_option_a_raises_not_implemented` 로 갱신 — 옵션 A 만 stub 검증 (옵션 B 의 contract 검증은 `test_rtmw_3d_path_selected.py` 가 list[PoseFrame] 반환으로 대체). 모듈 docstring 도 "Task 1 stub-level" → "Task 1+2" 로 갱신.
**Files modified:** backend/tests/test_rtmw_3d_path.py
**Commit:** aed6c35

---

## Known Stubs

- **RTMW3DPoseEngine (옵션 A)** — `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw3d_engine.py` — `__init__` + `estimate()` 둘 다 NotImplementedError. **의도된 stub** — belle = approved: option_b 박제로 비선택. plan 24 R&D 격리 대상. UI 렌더에 도달하지 않음 (pipeline 의 POSE_ENGINE config 가 RTMWLifterPoseEngine 만 선택).

## Self-Check: PASSED

- 모든 파일 존재 확인 (5 files created/modified)
- commit aed6c35 git log 매치 확인
- 3 selected-path tests PASS, 136 회귀 tests PASS
- §5 marker `selected: option_b` 정확 박제
- 옵션 A stub NotImplementedError ≥ 1 유지
- 옵션 B lifter_pipeline.py NotImplementedError 0
