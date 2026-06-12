---
phase: 17-gemini-vision-integration-4
plan: 03
subsystem: backend
tags: [gemini, vision, keypoint, augmenter, pydantic, guardrail, pipeline, python]

# Dependency graph
requires:
  - phase: 17-gemini-vision-integration-4
    plan: 01
    provides: GeminiVisionCall + KeypointRefinement schema + resolve_model("D", ...) + _gemini_vision_enabled OR-gate
  - phase: 17-gemini-vision-integration-4
    plan: 02
    provides: find_scene_flags occlusion_severe (영역 D 의 게이트 1 입력) + _call_wave1_scene_finder
  - phase: 06-rtmw-engine
    provides: to_coco17_array + uncertainty_proxy + skeleton.JOINT_KEYS (CheckpointJoint Literal 정합)
  - phase: 12-keypoint-overlay
    provides: KeypointReport (frozen dataclass) + build_keypoint_report + upsample_to_fps
provides:
  - sunity_shared.gemini.keypoint_augmenter.augment_low_confidence — 영역 D 진입점
  - RefinedKeypoint.joint_key 필드 (Plan 17-01 schema 박제 보강)
  - pipeline._call_wave2_keypoint_augmenter / _d_enabled / _low_uncertainty_frame_indices /
    _apply_keypoint_refinement_to_report
  - _VideoAnalysisInputs.keypoints_4ch 필드 (3차 R-B3 정합)
  - firestore_admin.complete_analysis gemini_d kwarg
affects:
  - app (사용자에게 보여지는 KeypointReport 시각화) — 후속 plan (좌표계 계약 + 2D→3D lifter)
    이 들어올 자리만 박제

# Tech tracking
tech-stack:
  added:
    - sunity_shared.gemini.keypoint_augmenter 모듈 신설
  patterns:
    - 3D scoring 행렬 (coco_array) 격리 패턴 — augment_low_confidence 시그너처에 영구 박제 X
    - G5 좌표 환각 가드 — 인접 frame ±2 정규화 L2 거리 임계값 0.15 + neighbor confidence 임계 0.3
    - mirror hint audit — left/right pair swap 의심 frame index Firestore 박제 (correction 후속)
    - normalized [0,1] coordinate self-return (3차 R-B3) — frame_w/h 인자 박제 0

key-files:
  created:
    - backend/shared/python/sunity_shared/gemini/keypoint_augmenter.py
    - backend/tests/gemini/test_keypoint_augmenter.py
    - backend/tests/test_pipeline_geminid_wiring.py
    - .planning/phases/17-gemini-vision-integration-4/17-03-SUMMARY.md
  modified:
    - backend/shared/python/sunity_shared/gemini/__init__.py (augment_low_confidence export)
    - backend/shared/python/sunity_shared/gemini/schemas.py (RefinedKeypoint.joint_key 필드 박제)
    - backend/shared/python/sunity_shared/firestore_admin.py (complete_analysis gemini_d kwarg)
    - backend/functions/pipeline/app.py (_VideoAnalysisInputs.keypoints_4ch 필드 + wave 2 wiring)
    - backend/tests/gemini/test_schemas.py (RefinedKeypoint.joint_key 신설 보강)
    - backend/tests/test_pipeline_gemini_integration.py (_VideoAnalysisInputs 박제 보강)
    - backend/tests/pipeline/test_pipeline_phase8.py (_VideoAnalysisInputs 박제 보강)
    - backend/tests/pipeline/test_pipeline_phase9.py (_VideoAnalysisInputs 박제 보강)

key-decisions:
  - "B2 hard gate (Codex review 2026-06-12) — 3D coco_array 는 본 plan 의 영역 D 입력/출력 양쪽
    에서 격리. augment_low_confidence 시그너처에 coco_array / rtmw_array 영구 박제 X. user-visible
    KeypointReport.data + confidence 만 보강. DTW/KISMAM/8 관절각 차원 점수는 D 영향 0 — 좌표계 계약
    (RTMW pole-aligned 3D ↔ Gemini normalized 2D pixel) + 2D→3D lifter 박은 후속 plan 에서 3D 주입 재진입."
  - "3차 R-B3 정합 — Gemini 가 normalized [0,1] 좌표 self-return. frame_w/h 인자 박제 0. KeypointRefinement
    Pydantic schema 의 Field(ge=0, le=1) 1차 차단 + augment_low_confidence prompt 가 'frame 좌상=(0,0),
    우하=(1,1)' 강제."
  - "_VideoAnalysisInputs 확장 (NamedTuple 6번째 필드 keypoints_4ch) — _extract_video_analysis_inputs
    의 line 675 to_coco17_array 결과 그대로 박제. 재계산 0건 — Phase 6 의 'RTMW estimate 1회' 보장 유지.
    회귀 test 박제 (to_coco17_array call_count == 1)."
  - "삽입 위치 (2차 R-B1 정정) — build_keypoint_report 직후 + complete_analysis 직전. build_result +
    DTW/dim_scores 는 wave 2 진입 전 완료 — D 가 점수 surface 0."
  - "uncertainty_proxy frame 식별 = `keypoints_4ch[:, :, 3].max(axis=1) > 0.5`. `min < 0.5` 박제 0
    (의미 정반대 — 이전 plan 박제 오해 정정 회귀 가드)."
  - "RefinedKeypoint.joint_key 필드 박제 보강 — Plan 17-01 schema 박제 누락 정합 박제. JointKeyLiteral
    8개 (skeleton.JOINT_KEYS) — Plan 17-03 prompt + caller 정합."
  - "schema 의 8 keypoint (elbow/shoulder/hip/knee) vs KeypointReport 의 8 keypoint (shoulder/hip/knee/hand)
    mismatch — 겹치는 6개 (shoulder/hip/knee) 만 KeypointReport 박제 가능. elbow 는 audit-only
    (Firestore geminiD.refined 박힘, KeypointReport 보강 skip)."
  - "G5 가드 가 인접 frame 정규화 L2 거리 ≥ 0.15 좌표 폐기. 인접 frame confidence < 0.3 면 비교 skip
    (둘 다 못 믿는 케이스). elbow 는 KeypointReport 에 비교 데이터 없음 → 무조건 통과 (audit only)."
  - "GEMINI_D_ENABLED default OFF (Plan 17-01 _VISION_ENV_DEFAULTS 박제 정합) — 운영자 박제 opt-in
    (AI-SPEC §4 영역 D 'Pod 에서 RTMW failure path 만 호출, 빈도 낮음' 정합)."

patterns-established:
  - "3D scoring 격리 — Gemini Vision 출력의 2D normalized pixel 좌표가 3D pole-aligned scoring 행렬을
    직접 mutate 하지 못하게 함수 시그너처 차원에서 박제 (coco_array 인자 박제 0건)."
  - "Plan 박제 정합 schema 보강 — Plan 17-01 의 RefinedKeypoint 가 joint_key 필드 누락 박제 시 후속 plan
    이 발견 + 보강. Plan 17-01 의 test_schemas.py 의 valid payload 박제도 동시 보강 (4 케이스)."
  - "frozen dataclass 보강 = dataclasses.replace — KeypointReport.data/confidence/reliability/warnings
    동시 박제 + 원본 보존."

requirements-completed:
  - VISION-04

# Metrics
duration: ~80min
completed: 2026-06-12
---

# Phase 17 Plan 03: Gemini Vision 영역 D Keypoint 보강 Summary

**RTMW 저신뢰 keypoint frame 을 Gemini 3.1 Pro Preview 영상 이해로 보강 — user-visible
KeypointReport.data + confidence 만 보강 + 3D scoring 행렬 (coco_array) 영구 격리 (B2)
+ G5 좌표 환각 가드 + mirror hint audit + Firestore geminiD 박제**

## Performance

- **Duration:** ~80 min
- **Started:** 2026-06-12 (Plan 17-03 worktree start, after Plan 17-02 박제)
- **Completed:** 2026-06-12T02:31:14Z
- **Tasks:** 2 (atomic commit per task)
- **Files modified:** 11 (4 created + 7 modified)

## Accomplishments

- `sunity_shared.gemini.keypoint_augmenter.augment_low_confidence` 신설 — 영역 D 진입점.
  RTMW 의 `uncertainty_proxy > 0.5` frame 의 8 관절 (elbow/shoulder/hip/knee) 을 Gemini
  Pro Vision 으로 보강. 정규화 [0,1] 좌표 self-return + chunked 호출 (25 frame chunk —
  KeypointRefinement.refined max_length=200 / 8 joints 정합).
- **B2 hard gate 정합** — 3D `coco_array` (pipeline `inputs.keypoints_4ch`) 는 본 plan 의
  영역 D wave 입력/출력 양쪽에서 격리. `augment_low_confidence` 시그너처:
  `(video_path, low_uncertainty_frame_indices, keypoint_report_2d) -> dict | None`.
  `coco_array` / `rtmw_array` / `frame_w` / `frame_h` 인자 영구 박제 X. user-visible
  `KeypointReport.data` + `confidence` 만 보강 — DTW/KISMAM/8 관절각 차원 점수는
  D 영향 0.
- **3차 R-B3 정합** — Gemini 가 normalized [0,1] 좌표 self-return. `KeypointRefinement`
  Pydantic schema 의 `x_normalized`/`y_normalized` Field(ge=0, le=1) 가 1차 차단 +
  prompt 의 "frame 좌상=(0,0), 우하=(1,1)" 강제. RTMW 의 기존 좌표 (hint) prompt 박제 X
  (편향 방지 — Gemini 의 독립 추정).
- `RefinedKeypoint.joint_key` 필드 박제 보강 — Plan 17-01 schema 박제 누락 정합 박제.
  `JointKeyLiteral` 8개 (skeleton.JOINT_KEYS) — Plan 17-03 prompt + caller 정합.
  Plan 17-01 test_schemas.py 의 valid payload 박제 4 케이스도 동시 보강.
- **G5 좌표 환각 가드** — 보강된 (frame_index, joint_key, x, y) 가 `keypoint_report_2d.data`
  의 인접 frame (±2) 동일 joint 좌표 (정규화 [0,1]) 와 L2 거리 검증. ≥ 0.15 면 폐기 +
  `guardrail_blocked_count++`. 인접 frame `confidence` < 0.3 면 비교 skip (둘 다 못 믿는
  케이스). elbow 는 KeypointReport 에 없음 → 비교 데이터 없음 → 무조건 통과 (audit only,
  geminiD.refined 박힘).
- **mirror hint audit** — refined 의 left/right pair (elbow/shoulder/hip/knee) 의 frame 내
  좌우 픽셀 위치 swap 의심 시 (`refined left.x > right.x AND RTMW 원본 반대`)
  `mirror_hint[frame_idx] = "swap_lr"` 박제. 1차 PR 은 audit 만 — mirror correction 자체는
  후속 plan.
- **pipeline `_process` wiring** — build_keypoint_report 직후 + complete_analysis 직전 (2차 R-B1
  정정 위치). 게이트 3종: ① occlusion_severe (Plan 17-02 영역 C 결과), ② GEMINI_D_ENABLED
  env (default OFF, opt-in), ③ local_video_path (B4 hard gate — S3 재다운로드 X). 빈 low_uncertainty
  frame indices 는 augment 내부에서 graceful 빈 dict 반환.
- **`_VideoAnalysisInputs.keypoints_4ch` 신설** (3차 R-B3 정합) — `_extract_video_analysis_inputs`
  의 line 675 `to_coco17_array(pose_frames)` 결과를 NamedTuple 6번째 필드에 박제. 재계산
  0건 — Phase 6 의 "RTMW estimate 1회" 보장 유지 (회귀 test: `to_coco17_array` call_count == 1).
- **`uncertainty_proxy` 정정 정합** — `keypoints_4ch[:, :, 3].max(axis=1) > 0.5` 인 frame 식별.
  `min < 0.5` 박제 0 (의미 정반대 — 이전 plan 박제 오해 정정 회귀 가드).
- `firestore_admin.complete_analysis` 의 `gemini_d` kwarg 박제 — Firestore top-level
  `geminiD` 박힘 (user-visible `result.keypointReport` 와 audit 분리, WARNING-3 정합).
  W5 validator 재사용 — flat object 박제 (augmentedFrames + originalRtmwUncertaintyProxy +
  guardrailBlockedCount + mirrorHint + model).
- **38 unit/통합 test** (Task 1: 13 + Task 2: 25). 외부 네트워크 호출 0 — 모든 GeminiVisionCall /
  augment_low_confidence / 외부 API stub. B2 hard gate 회귀 직접 검증 (3D coco_array np.array_equal
  True / 시그너처 인자 0건 / call_order 박제).

## Task Commits

각 task atomic commit:

1. **Task 1**: `5960e54` — `feat(17-03): augment_low_confidence 모듈 + G5 좌표 환각 가드 + Firestore geminiD schema`
2. **Task 2**: `fb421d2` — `feat(17-03): pipeline _process wave 2 영역 D wiring + 3D coco_array 불변 회귀 (B2 정합)`

## Files Created/Modified

**Created (4)**:
- `backend/shared/python/sunity_shared/gemini/keypoint_augmenter.py` — 영역 D 진입점 (augment_low_confidence + G5 가드 helper + mirror hint helper + prompt)
- `backend/tests/gemini/test_keypoint_augmenter.py` — 13 단위 test
- `backend/tests/test_pipeline_geminid_wiring.py` — 25 통합 test (B2 + R-B3 회귀 포함)
- `.planning/phases/17-gemini-vision-integration-4/17-03-SUMMARY.md` (본 파일)

**Modified (7)**:
- `backend/shared/python/sunity_shared/gemini/__init__.py` — augment_low_confidence export
- `backend/shared/python/sunity_shared/gemini/schemas.py` — RefinedKeypoint.joint_key 필드 박제
- `backend/shared/python/sunity_shared/firestore_admin.py` — complete_analysis gemini_d kwarg
- `backend/functions/pipeline/app.py` — _VideoAnalysisInputs.keypoints_4ch 필드 + wave 2 wiring + 4 helper 신설 + import augment_low_confidence
- `backend/tests/gemini/test_schemas.py` — RefinedKeypoint 박제 보강 (4 케이스)
- `backend/tests/test_pipeline_gemini_integration.py` — _VideoAnalysisInputs 박제 보강 (회귀 fix)
- `backend/tests/pipeline/test_pipeline_phase8.py` / `phase9.py` — _VideoAnalysisInputs 박제 보강 (회귀 fix)

## Decisions Made

- **B2 hard gate (시그너처 차원 격리)**: 3D coco_array 가 augment_low_confidence 의 입력/출력
  양쪽에서 영구 박제 0건. inspect.signature 회귀 직접 검증. 좌표계 계약 (RTMW pole-aligned
  3D ↔ Gemini normalized 2D pixel) + 2D→3D lifter 박은 별도 후속 plan 으로 분리.
- **3차 R-B3 (frame_w/h 인자 박제 0)**: Gemini self-normalize 강제. 본 prompt 의 좌상=(0,0)/
  우하=(1,1) + KeypointRefinement schema 의 Field(ge=0, le=1) 1차 차단. coordinate space
  혼선 0.
- **Schema 보강 (RefinedKeypoint.joint_key)**: Plan 17-01 의 schema 박제 누락 — joint_key 없으면
  여러 frame×joint 가 동일 (frame_index, x, y) 박제 시 caller 가 어떤 joint 인지 알 수 없음.
  Plan 17-03 prompt + caller 정합 — joint_key Literal 8개 박제.
- **schema 8 (elbow) vs KeypointReport 8 (hand) mismatch — audit-only 분기**: schema 는 angle
  scoring 기준 8 joint (elbow/shoulder/hip/knee), KeypointReport 는 body visualization 기준
  8 joint (shoulder/hip/knee/hand). 겹치는 6개만 KeypointReport 보강 박제. elbow 는 audit
  only — Firestore geminiD.refined 박힘 (후속 plan 이 visualization 확장 시 박제 가능).
- **G5 가드 임계값 박제**: 인접 frame ±2 + L2 거리 0.15 + neighbor confidence 0.3. 너무
  넓으면 환각 통과, 너무 좁으면 정상 frame 폐기. 0.15 = 정규화 [0,1] 좌표계 박제 "15% 거리"
  (영상 width/height 의 15%). Plan 박제 정신 정합.
- **mirror hint 1차 PR = audit only**: refined left/right pair swap 의심 frame index 만
  Firestore 박제. 실제 mirror correction (좌표 swap 적용) 은 후속 plan — 1차 박제로 회귀
  surface 정합 (오탐지 시 사용자 시각화 왜곡 risk).
- **GEMINI_D_ENABLED default OFF**: AI-SPEC §4 영역 D "Pod 에서 RTMW failure path 만 호출,
  빈도 낮음" 정합. 운영자 opt-in 박제 — Plan 17-01 _VISION_ENV_DEFAULTS 박제 정합.
- **삽입 위치 (build_keypoint_report 직후 + complete_analysis 직전)**: build_result + DTW/
  dim_scores 가 wave 2 진입 전 완료 — D 가 점수 surface 0 박제 정합. 후속 plan 이 3D 주입
  진입할 때도 본 위치 박제 정합 유지.

## Deviations from Plan

다음은 plan 정신 정합 보조 박제 — 박제 정신 변경 0:

1. **[Rule 2 - 누락된 critical functionality 보강] RefinedKeypoint.joint_key 필드 박제 보강**
   - **Found during:** Task 1 RED phase (test_refined_coords_passed_g5 ValidationError)
   - **Issue:** Plan 17-01 의 RefinedKeypoint schema 가 frame_index + x + y + confidence 만 박제 —
     joint_key 필드 박제 누락. Plan 17-03 spec 의 "{frame_index, joint_key, x_normalized,
     y_normalized, confidence}" 와 mismatch. joint_key 없으면 보강 좌표가 어떤 관절인지 caller 가
     알 수 없음 → augment 자체 박제 불가.
   - **Fix:** sunity_shared/gemini/schemas.py 의 RefinedKeypoint 에 `joint_key: JointKeyLiteral`
     필드 박제 (8개 — skeleton.JOINT_KEYS 정합). Plan 17-01 의 test_schemas.py 의 valid payload
     4 케이스 박제 보강 (joint_key="left_shoulder" 박제).
   - **Files modified:** backend/shared/python/sunity_shared/gemini/schemas.py,
     backend/tests/gemini/test_schemas.py
   - **Commit:** 5960e54
   - **Justification:** Rule 2 — Plan 17-03 spec 의 시그너처 (joint_key 박제) 가 hard requirement.
     schema 박제 없으면 augment_low_confidence 자체 박제 불가. Plan 17-01 의 schema 박제 누락이
     본 plan 의 critical functionality 차단 — graceful 우회 X (Rule 2).

2. **[Rule 3 - 회귀 차단 fix] 기존 _VideoAnalysisInputs 생성 박제 3개 test 의 keypoints_4ch 필드 박제 보강**
   - **Found during:** Task 2 GREEN phase (TypeError: __new__() missing 1 required positional
     argument: 'keypoints_4ch')
   - **Issue:** Plan 17-03 박제 6번째 필드 신설 (keypoints_4ch) → 기존 _VideoAnalysisInputs 생성
     박제 3개 test (test_pipeline_gemini_integration / phase8 / phase9) 가 TypeError.
   - **Fix:** 3개 test 의 _VideoAnalysisInputs 생성 박제에 `keypoints_4ch=np.zeros((T, 17, 4),
     dtype=float)` 박제. 회귀 test 51건 PASS.
   - **Files modified:** backend/tests/test_pipeline_gemini_integration.py,
     backend/tests/pipeline/test_pipeline_phase8.py, backend/tests/pipeline/test_pipeline_phase9.py
   - **Commit:** fb421d2

## Issues Encountered

- **Pre-existing test failures** (Plan 17-03 scope 외):
  - `tests/test_gemini_moment_extractor.py::TestExtractor::test_default_model_constant` —
    Plan 5-05 DEFAULT_GEMINI_MODEL=`gemini-2.5-flash` vs Plan 5-03 prompt 박제 `gemini-3.1-pro-preview`
    mismatch (Plan 17-01 SUMMARY "Issues Encountered" 박제 정합).
  - `tests/test_gemini_motion_classify_spike.py` / `test_mapping_audit.py` / `test_pole_detector.py`
    / `test_spike_*` 등 — `from backend.research.spikes` import path 박제 누락 (collection error).
  - `tests/test_compare_body_profile_smoke.py` / `tests/test_estimated_height_scale_consumer_semantics.py`
    / `tests/test_gemini_technique_recognizer.py` 일부 — 본 plan 변경 무관 박제 (test isolation
    artifact — 단독 실행 시 PASS).

## Known Stubs

None — 본 plan 의 영역 D 보강은 user-visible KeypointReport.data + confidence 박제 (실제
좌표 + 신뢰도 박제). placeholder / 빈 데이터 / "데이터 없음" 박제 X. graceful 폴백 (Gemini
호출 None / 가드 통과 0) 시도 분석 흐름 계속 (KeypointReport 원본 유지 — stub 박제 X).

## Threat Flags

None — 본 plan 의 변경은 기존 trust boundary 안에서만 박제. 신규 외부 통신 path 박제 X
(Gemini Vision 호출은 Plan 17-01 의 GeminiVisionCall 박제 통과). geminiD Firestore 박제는
기존 result 박제 path 박제 정합 (auth/network surface 변경 0).

## User Setup Required

- 운영 시 belle 가 `GEMINI_D_ENABLED=1` Lambda env (또는 Pod env) 박제만으로 영역 D wave
  활성. 코드 변경 0.
- `GEMINI_API_KEY` 박제는 Plan 17-01 의 `_load_api_key` 박제 정합 — env / SSM fallback 박제.
  본 plan 추가 박제 0.
- **별도 후속 plan 박제 — 3D 주입 (B2 deferred)**: 좌표계 계약 (RTMW pole-aligned 3D ↔
  Gemini normalized 2D pixel) + 2D→3D lifter + coco_array in-place 주입 + 보강된 3D 좌표
  로 DTW/KISMAM/각도 재계산. ROADMAP 추가 박제 (Phase 17B 또는 18 후보).

## Self-Check: PASSED

- 4 expected created files 모두 FOUND:
  - `backend/shared/python/sunity_shared/gemini/keypoint_augmenter.py`
  - `backend/tests/gemini/test_keypoint_augmenter.py`
  - `backend/tests/test_pipeline_geminid_wiring.py`
  - `.planning/phases/17-gemini-vision-integration-4/17-03-SUMMARY.md`
- 7 expected modified files 모두 git diff 박제 확인.
- 2 commits (5960e54, fb421d2) 모두 git log 박제.
- 38 단위/통합 test 모두 PASSED — `pytest backend/tests/gemini/test_keypoint_augmenter.py
  backend/tests/test_pipeline_geminid_wiring.py -q`.
- 173 directly impacted test 모두 PASSED — Phase 17 + pipeline 회귀 sweep (포함:
  test_pipeline_phase8/9 / pipeline_gemini_integration / pipeline_mode3 / pipeline_dispatch /
  pipeline_body_profile_injection).
- Plan verification grep 회귀 PASS:
  - `grep -n augment_low_confidence backend/functions/pipeline/app.py | grep -v '^#' | grep -c .` = 10 (≥ 2 박제 정합)
  - `grep -n "enforce_object_guard=False" backend/shared/python/sunity_shared/gemini/keypoint_augmenter.py | grep -c .` = 3 (≥ 1 박제 정합)
  - B2 시그너처 회귀: `inspect.signature` 에 `coco_array` / `rtmw_array` 0건 — PASS.
  - 3D mutate 회귀: `coco_array[.*] =` near `augment_low_confidence` = 0건 — PASS.

## Next Phase Readiness

- 본 plan 의 영역 D 박제는 운영자 박제 `GEMINI_D_ENABLED=1` 박제만으로 활성 — 코드 변경 0.
- KeypointReport.data + confidence 박제 보강 → app 의 KeypointOverlay (Wave 1+) 가 자동
  소비 (Phase 12 패턴 정합). 사용자가 보는 시각화 풍부화.
- Firestore geminiD audit 박제 → eval/guardrail plan 박제 (별도 plan) 이 guardrail_blocked_count
  + mirror_hint 추적 가능.
- **후속 plan 박제 readiness — 3D 주입 (B2 deferred)**: 좌표계 계약 + 2D→3D lifter 박은 다음,
  본 plan 의 `_apply_keypoint_refinement_to_report` helper 박제와 동일 패턴으로 coco_array
  에 3D 좌표 박제 (in-place mutate). DTW/KISMAM/각도 재계산. ROADMAP 박제 시 진입.

---
*Phase: 17-gemini-vision-integration-4*
*Completed: 2026-06-12*
