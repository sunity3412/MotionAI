---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "21"
subsystem: ml-pose-engine
status: complete
tags:
  - rtmw
  - pose-engine
  - license-gate
  - coco-wholebody
  - apache-2.0
  - plan-21
  - wave-2
  - tdd

dependency_graph:
  requires:
    - 01-19  # PoseEngine Protocol + PoseFrame.body_shape + BodyNormalizationProfile
    - 01-20  # weights_manifest.json production_eligible=true (rtmw-x-384x288)
  provides:
    - "backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py — RTMWPoseEngine (PoseEngine Protocol 구현)"
    - "backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py — RTMW133ToCOCO17Adapter"
    - "backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/wholebody_keypoints.py — RTMW_KEYPOINT_INDICES 133개"
    - "backend/shared/python/sunity_shared/config.py — get_pose_engine() POSE_ENGINE env"
    - "PoseFrame.raw_keypoints_133 — D-20 RTMW 133 원본 보존 필드 (nullable)"
  affects:
    - 01-22  # 3D path (RTMW3D 또는 lifter) — RTMWPoseEngine 위에 추가 가능
    - 01-25  # pipeline atomic swap — RTMWPoseEngine 를 운영 path 에 연결

tech_stack:
  added:
    - "rtmlib (lazy import — __init__ 내부, H-2 박제)"
  patterns:
    - "DI factory (create_with_inferencer) — 단위 테스트 mock 주입"
    - "manifest gate — production_eligible=true 검증 (D-25, T-21-01 mitigation)"
    - "lazy import (H-2 박제) — module-level rtmlib/mmpose/mmcv 0건"
    - "backend-agnostic adapter (rtmw_133_to_coco17.py) — rtmlib 의존 0"
    - "TDD RED→GREEN (2 tasks)"

key_files:
  created:
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/wholebody_keypoints.py
    - backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py
    - backend/shared/python/sunity_shared/config.py
    - backend/tests/test_rtmw_133_to_coco17_adapter.py
    - backend/tests/test_rtmw_engine.py
    - backend/tests/fixtures/rtmw_keypoints.py
  modified:
    - backend/shared/python/sunity_shared/analysis/adapters/__init__.py
    - backend/shared/python/sunity_shared/analysis/pose_engines/__init__.py
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/__init__.py
    - backend/shared/python/sunity_shared/analysis/pose_frame.py
    - backend/tests/test_pose_frame_contract.py

decisions:
  - "COCO-WholeBody hand 순서 = thumb-first (92=thumb_cmc, 96=index_finger_mcp). 초기 RED 테스트 오기재(92=index_mcp) → 표준 기준으로 수정."
  - "raw_keypoints_133 = PoseFrame 신규 필드 (nullable). D-20 원본 보존. 기존 10→11 필드 lockstep 갱신."
  - "GRIP_LEFT_SOURCE_INDICES = (91, 96, 100) — hand_root + index_mcp + middle_mcp 평균 (A2 belle confirm 보류)."
  - "AST import 검사 = tree.body (module-level) 만 검사. 함수 내 lazy import 허용."

metrics:
  duration_minutes: 14
  completed_date: "2026-06-02"
  tasks_completed: 2
  tasks_total: 2
  files_created: 7
  files_modified: 5
  tests_added: 23
  tests_passed: 30
---

# Phase 01 Plan 21: RTMWPoseEngine + RTMW133ToCOCO17Adapter — RTMW 통합 Summary

**One-liner:** rtmlib RTMW 133 wholebody 를 PoseEngine Protocol 구현체로 통합. weights_manifest 라이선스 게이트 (D-25) + COCO-17 + 폴 확장 어댑터 (D-20) + POSE_ENGINE config 플래그 (D-21) 모두 박제. plan 22 (3D path) 진입 가능.

---

## Tasks Completed

| Task | Name | Commits | Status |
|------|------|---------|--------|
| 1 | RTMW 133 키포인트 인덱스 표 + RTMW133ToCOCO17Adapter + 폴 확장 | `232d217` (RED), `29c5167` (GREEN) | DONE |
| 2 | RTMWPoseEngine + weights_manifest 라이선스 게이트 + POSE_ENGINE config 플래그 | `050002b` (RED), `04ddee0` (GREEN) | DONE |

---

## Verification Results

### Task 1

```
$ python3 -m pytest backend/tests/test_rtmw_133_to_coco17_adapter.py -v
13 passed in 0.14s
```

- `test_rtmw_keypoint_indices_total_133` — RTMW_KEYPOINT_INDICES 133개 PASS
- `test_rtmw_body_17_indices_match_coco` — COCO-17 표준 인덱스 1:1 PASS
- `test_rtmw_foot_6_indices_present` — foot 6 (17~22) PASS
- `test_rtmw_hand_indices_present` — left_hand_root=91, right_hand_root=112 PASS
- `test_rtmw133_to_coco17_mapping_exact` — RTMW_133_TO_COCO17 17개 PASS
- `test_rtmw_pole_extension_includes_toe_heel_grip` — POLE_EXTENSION_MAP 6개 PASS
- `test_pole_grip_derived_from_hand_root` — GRIP source indices 포함 PASS
- `test_convert_keypoints_basic` — PoseFrame 반환 + keypoints_3d 17개 + raw_keypoints_133 133개 PASS
- `test_convert_low_score_keypoint_marked` — score=0.1 → uncertainty_proxy>0.85 PASS
- `test_convert_pole_axis_preserved` — pole_axis 동일 객체 보존 (H-3) PASS
- `test_convert_reliability_from_mean_score` — 0.9→high, 0.1→low PASS
- `test_convert_body_shape_none` — body_shape=None (D-21) PASS
- `test_adapter_no_rtmlib_import` — module-level import 0건 PASS

### Task 2

```
$ python3 -m pytest backend/tests/test_rtmw_engine.py -v
10 passed in 0.11s
```

- `test_rtmw_engine_implements_pose_engine_protocol` — estimate 시그니처 (frames, pole_axis) PASS
- `test_rtmw_engine_estimate_returns_list_pose_frame` — list[PoseFrame] len=T PASS
- `test_rtmw_engine_loads_manifest_on_init` — production_eligible 가중치 포함 manifest PASS
- `test_rtmw_engine_rejects_non_eligible_weights` — LicenseViolationError raise PASS
- `test_rtmw_engine_module_level_no_rtmlib_import` — tree.body 검사 0건 PASS
- `test_rtmw_engine_no_human_raises_nohumanerror` — 빈 결과 → NoHumanError PASS
- `test_pose_engines_init_lazy_exports_rtmw` — lazy export 성공 PASS
- `test_config_get_pose_engine_returns_rtmw_by_default` — 기본값 'RTMW' PASS
- `test_config_get_pose_engine_respects_env` — NLF_SMPLX env 반영 PASS
- `test_config_invalid_pose_engine_raises` — ValueError raise PASS

### Manifest gate 회귀 (Plan 01-20)

```
$ python3 -m pytest backend/tests/test_rtmw_weights_manifest.py -q
7 passed in 0.01s
```

### 계약 회귀 (Plan 01-19)

```
$ python3 -m pytest backend/tests/test_pose_frame_contract.py backend/tests/test_pose_engine_contract.py -q
20 passed in 0.05s
```

### 전체 계획 관련 테스트

```
$ python3 -m pytest backend/tests/test_rtmw_engine.py backend/tests/test_rtmw_133_to_coco17_adapter.py backend/tests/test_rtmw_weights_manifest.py backend/tests/test_pose_frame_contract.py backend/tests/test_pose_engine_contract.py ... -q
62 passed in 0.12s
```

---

## Acceptance Criteria 검증

- [x] RTMWPoseEngine 이 PoseEngine Protocol 구현체 (estimate(frames, pole_axis) → list[PoseFrame])
- [x] RTMW133ToCOCO17Adapter 가 133 → COCO-17 + 폴 확장 변환
- [x] POSE_ENGINE config 플래그 박제 (기본 RTMW, R&D NLF_SMPLX)
- [x] weights_manifest 라이선스 게이트 작동 (LicenseViolationError)
- [x] 다운스트림 변경 0 (기존 MediaPipePoseEngine 코드 무수정)
- [x] rtmlib module-level import 0 (AST tree.body 검사 통과)
- [x] PoseFrame.body_shape = None (RTMW path, D-21)
- [x] raw_keypoints_133 = {이름: Keypoint3D} 133개 (D-20 원본 보존)

---

## Deviations from Plan

### [Rule 1 - Bug] COCO-WholeBody hand 순서 초기 오기재 수정

- **Found during:** Task 1 테스트 실행 중 Test 4 실패
- **Issue:** RED 테스트 작성 시 `left_index_finger_mcp == 92` 로 오기재 (COCO-WholeBody thumb-first 표준: 92=thumb_cmc, 96=index_mcp)
- **Fix:** Test 4 를 COCO-WholeBody 공식 표준 (thumb-first, 92=thumb_cmc, 96=index_mcp) 으로 수정. `left_thumb_cmc == 92` 검증으로 교체.
- **Files modified:** `backend/tests/test_rtmw_133_to_coco17_adapter.py`
- **Commit:** `29c5167` (Task 1 GREEN 함께 포함)
- **Justification:** 공식 COCO-WholeBody 표준 적용. `COCO-WholeBody + mmpose hand annotation format (thumb→index→middle→ring→little)` 인용.

### [Rule 2 - Missing critical functionality] PoseFrame.raw_keypoints_133 필드 추가 (D-20)

- **Found during:** Task 1 구현 중 — test_convert_keypoints_basic 가 `result.raw_keypoints_133` 접근
- **Issue:** PoseFrame 에 `raw_keypoints_133` 필드 없음. D-20 "RTMW 133 원본 보존" 요구사항.
- **Fix:** PoseFrame 에 `raw_keypoints_133: dict[str, Keypoint3D] | None = None` 11번째 필드 추가. `test_pose_frame_contract.py::EXPECTED_POSE_FRAME_FIELDS` 10→11 갱신 (lockstep).
- **Files modified:** `backend/shared/python/sunity_shared/analysis/pose_frame.py`, `backend/tests/test_pose_frame_contract.py`
- **Commit:** `29c5167` (Task 1 GREEN)
- **Justification:** D-20 계약 직접 이행. PoseFrame 필드 추가 = 본 plan must_haves 항목 (rtmw_engine.py → raw_keypoints_133 에 133 원본 보존 명시).

### [Rule 1 - Bug] AST import 검사 scope 수정 (module-level 정확히 한정)

- **Found during:** Task 2 테스트 실행 중 Test 5 실패
- **Issue:** `ast.walk(tree)` 는 함수 내부 `try: from rtmlib import ...` (lazy import) 도 포함 → rtmw_engine.py H-2 lazy import 도 검출되어 테스트 실패.
- **Fix:** AST 검사를 `tree.body` (module-level 직접 자식) 만으로 한정. 함수 내 lazy import 는 허용.
- **Files modified:** `backend/tests/test_rtmw_engine.py`, `backend/tests/test_rtmw_133_to_coco17_adapter.py`
- **Commit:** `04ddee0` (Task 2 GREEN)
- **Justification:** H-2 박제 의도 정확히 반영 — "module-level import 금지" = 파일 최상위 레벨 import 금지. 함수/클래스 내 lazy import 는 H-2 목적상 허용.

**Total deviations:** 3 (Rule 1 × 2, Rule 2 × 1). 모두 자동 수정.

---

## Known Stubs

없음 — RTMWPoseEngine.estimate() 는 실제 rtmlib 호출 경로 구현. sha256 검증은 현재 `sha256=null` (plan 20 미확보) → 스킵 패턴 (plan 22 에서 실제 다운로드 후 sha256 채움 예정). 이는 plan 20 에서 이미 documented ("sha256 = null 은 의도 — plan 21 가중치 다운로드 시 박제 예정").

---

## Threat Flags

없음 — 신규 네트워크 endpoint / Firestore 스키마 / S3 path 변경 없음. 본 plan 의 threat register (T-21-01/02/SC) 모두 mitigation 완료:

- **T-21-01** (manifest 우회) → `_load_eligible_weight` 가 manifest 필수 + production_eligible 검증 (LicenseViolationError)
- **T-21-02** (module-level import silent fail) → `test_rtmw_engine_module_level_no_rtmlib_import` (tree.body 검사) PASS
- **T-21-SC** (sha256 무결성) → sha256=null 이면 스킵 (plan 22 다운로드 시 박제 예정)
- **T-21-03** (POSE_ENGINE=NLF_SMPLX 운영 오설정) → config.py 경고 로그 + plan 25 배포 템플릿이 POSE_ENGINE=RTMW 강제 예정

---

## Plan 22 진입 게이트

본 plan 의 RTMWPoseEngine 이 plan 19 Protocol 을 정확히 구현하고 단위 테스트 30개 PASS.

plan 22 진입 가능 조건 충족:
- [x] RTMWPoseEngine.estimate(frames, pole_axis) → list[PoseFrame] 동작
- [x] weights_manifest 라이선스 게이트 작동 (rtmw-x-384x288 production_eligible=true)
- [x] RTMW133ToCOCO17Adapter backend-agnostic (rtmlib import 0)
- [x] POSE_ENGINE config 플래그 박제
- [x] PoseFrame.raw_keypoints_133 D-20 원본 보존 필드 박제

plan 22 목표: RTMWPoseEngine 위에 3D path (RTMW3D 또는 lifter) 통합.

---

## TDD Gate Compliance

- Task 1: `test(01-21): add failing RTMW 133→COCO-17 adapter + keypoint indices tests (RED)` (`232d217`) → `feat(01-21): RTMW 133 키포인트 인덱스 표 + RTMW133ToCOCO17Adapter + 폴 확장` (`29c5167`). RED → GREEN 순서 commit 게이트 통과.
- Task 2: `test(01-21): add failing RTMWPoseEngine + POSE_ENGINE config tests (RED)` (`050002b`) → `feat(01-21): RTMWPoseEngine + LicenseViolationError + POSE_ENGINE config 플래그` (`04ddee0`). RED → GREEN 순서 commit 게이트 통과.

---

## Self-Check: PASSED

**파일 존재 확인:**

- `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py` — FOUND
- `backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py` — FOUND
- `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/wholebody_keypoints.py` — FOUND
- `backend/shared/python/sunity_shared/config.py` — FOUND
- `backend/tests/test_rtmw_133_to_coco17_adapter.py` — FOUND
- `backend/tests/test_rtmw_engine.py` — FOUND
- `backend/tests/fixtures/rtmw_keypoints.py` — FOUND

**커밋 존재 확인:**

- `232d217` test(01-21): RED Task 1 — FOUND
- `29c5167` feat(01-21): GREEN Task 1 — FOUND
- `050002b` test(01-21): RED Task 2 — FOUND
- `04ddee0` feat(01-21): GREEN Task 2 — FOUND

**테스트 통과 확인:**

- 13 tests (Task 1) + 10 tests (Task 2) + 7 tests (manifest, Plan 01-20 회귀) = 30 PASS
- 62 total tests (포함 Plan 01-19 계약 회귀) = 62 PASS
