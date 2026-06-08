---
phase: 06-coaching
plan: 02
subsystem: backend-pipeline-wiring
tags: [pipeline-wiring, firestore, body-normalizer, gemini-fallback, retro-phase5-patch, phase-06]
status: complete
requirements: [PERS-01]
dependency_graph:
  requires: [Phase 6-01 (body_normalizer 본체 + 3-way contract), Phase 5 (Gemini recognizer), Phase 2 (BodyNormalizationProfile + measure_body_profile)]
  provides: [pipeline _process production wiring, complete_analysis(body_comparison_report=) Firestore 저장 path, _match_reference_by_motion_id exact-match, _extract_target_torso_px helper, _dataclass_to_camel_case_dict 4-case]
  affects: [Phase 6-03 (정은지 reference 백필 진입 가능), Phase 7 (차이 분류 — bodyComparisonReport 소비), Phase 12 (오버레이 — scaleProfile 소비), Phase 13 (보완 운동 — findings 소비)]
tech_stack:
  added: []
  patterns: [unified video extraction (R3 single helper), non-null fallback profile (R4), caller-injected extra_warnings (R8), exact-match motion_id lookup (C2), NamedTuple 반환 4종, _validate_flat_dict_no_nested_array recursive validator (W5), camelCase 변환 4-case helper (C8)]
key_files:
  created:
    - backend/tests/phase06/test_technique_profile_motion_id.py
    - backend/tests/phase06/test_gemini_recognizer_populates_motion_id.py
    - backend/tests/phase06/test_pipeline_body_comparison.py
    - backend/tests/phase06/test_firestore_admin_body_comparison.py
    - backend/tests/phase06/test_pipeline_firestore_integration.py
    - backend/tests/phase06/test_dataclass_to_camel_case_dict.py
    - backend/tests/phase06/test_phase06_integration_smoke.py
  modified:
    - backend/shared/python/sunity_shared/analysis/technique.py
    - backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/shared/python/sunity_shared/analysis/body_normalizer.py
    - app/src/lib/userAnalyses.ts
    - backend/tests/test_pipeline_recognizer_switch.py
    - backend/tests/test_pipeline_body_profile_injection.py
    - backend/tests/test_pipeline_gemini_integration.py
decisions:
  - "C2 + R1 retro Phase 5 patch: TechniqueProfile.motion_id 필드 (위치: dataclass 맨 끝, hold_window 뒤) + Gemini recognizer 4 path keyword populate. mode3-first Gemini fallback path 가 firestore_admin.get_reference_motion(motion_id) exact-match 사용."
  - "R3 fix: 단일 _extract_video_analysis_inputs(bucket, key, default_pole, *, keep_local_video=False) helper. 기존 _angles_and_video_path_from_video 폐기. S3 download + frame extract + RTMW estimate 1회만 실행 (T-06-02-06 mitigation). Phase 2 helper _angles_and_body_profile_from_video 무수정 보존."
  - "R4 fix: student_profile 반환 타입 = BodyNormalizationProfile (non-null). measure_body_profile 의 _fallback_profile 정합 (confidence=0.0 + warnings 박제). caller 별도 None check 불요."
  - "R2 wiring: mode1 + mode3 fallback 양 path 가 reference 의 bodyComparisonSourcePose 도 fetch. source_keypoints=ref_source_pose.to_keypoints_array() 전달. _extract_target_torso_px helper 신설 (target 영상 mid_shoulder ↔ mid_hip 픽셀 거리)."
  - "R8 fix: extra_warnings injection (compare_body_profiles 의 신규 파라미터). caller 가 'fallback_reference_not_found' / 'reference_source_pose_missing' 주입. dataclasses.replace 우회 패턴 금지."
  - "W5 nested-array validator: _validate_flat_dict_no_nested_array + _validate_dict_only_scalars 2종. list[str] (warnings) + list[dict-of-scalars-only] (findings) 허용. list[list] / list[dict-with-nested-list] TypeError raise."
  - "C8 4-case _dataclass_to_camel_case_dict: None / dataclass / list / dict / Enum / scalar 명시적 처리. BodyComparisonReport 의 중첩 ScaleProfile + list[BodyComparisonFinding] 모두 camelCase 변환."
  - "Rule 1 fix: body_normalizer.measure_ipsf_absolute_deficits 의 expects 변수가 TechniqueProfile.expects_extension method 객체를 iterate 시도하던 버그 — joint_expectations dict 에서 JOINT_EXTEND 값 키로 derive 변경."
metrics:
  duration_minutes: ~120
  completed_date: "2026-06-08"
  tasks_total: 5
  tasks_completed: 5
  tests_total: 55
  tests_passed: 55
  phase06_full_suite: 107
  pipeline_regression_check: 156
---

# Phase 6 Plan 02: pipeline wiring + Firestore 통합 + retro Phase 5 patch Summary

**One-liner:** Phase 6 vertical slice production wiring — Plan 06-01 algorithm + contract 본체를 production code path 에 연결: C2 + R1 retro Phase 5 patch (TechniqueProfile.motion_id 맨 끝 + Gemini 4 path populate) + R3 단일 `_extract_video_analysis_inputs` helper (RTMW 1회 실행 보장) + R4 student_profile non-null + R2 reference source_pose fetch + R8 extra_warnings injection + W1 comparisonType 3 cases + W5 `_validate_flat_dict_no_nested_array` + C8 `_dataclass_to_camel_case_dict` 4-case + C14 grep gate + C15 SAM artifact 박제 + 7 신규 test 파일 (55 case PASS).

## Status

- Tasks executed: **5 / 5** (Task 0 retro Phase 5 patch → Task 4 통합 smoke)
- 신규 test: **55 / 55 PASS** (pytest backend/tests/phase06/)
- 전체 phase06 suite: **107 / 107 PASS** (Plan 06-01 의 52 + 본 plan 의 55)
- 기존 pipeline regression check: **156 / 156 PASS** (회귀 0)
- TypeScript: `tsc --noEmit` clean
- SAM template: `sam validate` exit 0
- Commits: 5 atomic + 1 metadata (예정)
- Plan 06-03 진입 가능: 정은지 reference 5개 영상의 bodyNormalizationProfile + bodyComparisonSourcePose 백필 (별도 plan).

## Task 별 산출 + 검증

### Task 0 — C2 + R1 retro Phase 5 patch (commit `8c5b002`)

**Files**:
- `backend/shared/python/sunity_shared/analysis/technique.py` — `motion_id: str | None = None` 필드 (위치: dataclass 맨 끝, hold_window 뒤).
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` — 4 path keyword argument `motion_id=` populate:
  - low_confidence path → motion_id=None
  - unregistered path → motion_id=None
  - _build_profile 정상 path → motion_id=motion (canonical)
  - _profile_from_cache → motion_id=cached.get("motion")

**Tests (9 PASS)**:
- `test_technique_profile_motion_id.py` (4 test) — dataclass field + import success (R1) + default None + FallbackRecognizer 회귀 부재.
- `test_gemini_recognizer_populates_motion_id.py` (5 test) — Gemini 4 path motion_id populate + keyword arg 정합.

**R1 fix 핵심**: 기존 plan 의 'name 바로 아래' 위치는 default 있는 필드가 non-default 필드 앞에 오는 Python dataclass 위반 → `import TechniqueProfile` 자체 거부. motion_id 를 dataclass 의 모든 default-있는 필드 (required_split_deg, requires_hold, is_symmetric, hold_window) 뒤로 배치 → Python 규칙 정합.

### Task 1 — pipeline _process body_normalizer wiring + R3/R4/R2/R8 (commit `2e7d97c`)

**Files**:
- `backend/functions/pipeline/app.py` — 대규모 wiring:
  - `_VideoAnalysisInputs` NamedTuple (4 field: angles / student_profile / pose_frames / local_video_path).
  - `_extract_video_analysis_inputs(bucket, key, default_pole, *, keep_local_video=False) -> _VideoAnalysisInputs` — 단일 통합 helper. S3 download + frame extract + RTMW estimate 1회 실행 (R3 fix).
  - `_match_reference_by_motion_id(motion_id: str | None) -> dict | None` — exact-match (C2 fix).
  - `_extract_target_torso_px(pose_frames) -> float | None` — 평균 mid_shoulder ↔ mid_hip 픽셀 거리 (R2 wiring).
  - `_coerce_source_pose_dict(raw) -> dict | None` — Firestore stored dict → BodyComparisonSourcePose 생성자 dict 변환 (snake/camel 자동).
  - `_dataclass_to_camel_case_dict` + `_snake_to_camel` — C8 4-case helper.
  - `_RTMW_ENGINE` singleton 추가 — `_ensure_adapters` 가 `_POSE_ESTIMATOR._engine` 재사용.
  - 기존 `_angles_and_video_path_from_video` 폐기. Phase 2 `_angles_and_body_profile_from_video` 무수정 보존.
  - `_process` 의 mode1 / mode3 first / mode3 progress 분기 모두 `body_normalizer.compare_body_profiles` 호출 — `source_keypoints` 전달 + `extra_warnings` injection.
  - `complete_analysis` 호출에 `body_comparison_report` + `body_normalization_profile` kwarg 추가 (camelCase 변환 적용).
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py` — Rule 1 bug fix: `measure_ipsf_absolute_deficits` 의 `expects` 변수가 method 객체 iterate 시도 → `joint_expectations` dict 에서 JOINT_EXTEND 값 키로 derive.
- 기존 pipeline test 3종 업데이트 (legacy helper 폐기 정합):
  - `test_pipeline_recognizer_switch.py` — `TestB8FixSignature.test_unified_extract_video_analysis_inputs_helper_exists` 신설.
  - `test_pipeline_body_profile_injection.py` — `test_b8_signature_lock_preserved` 갱신 (R3 fix 정합).
  - `test_pipeline_gemini_integration.py` — `_stub_extract_inputs` helper 신설 (3 test 갱신).

**Tests (13 PASS)** — `test_pipeline_body_comparison.py`:
- Test 1: mode1 full ref → comparisonType 'mode1' + scaleProfile != None.
- **Test 2 (C9 canary)**: mode1 missing ref_profile → reference_profile_missing + bodyNormalizationConfidence < 0.5.
- **Test 3 (R2 canary)**: mode1 missing source_pose → reference_source_pose_missing + scaleProfile None.
- **Test 4 (R2 wiring)**: mode1 fetches both profile + source_pose → source_keypoints ndarray (17, 4).
- Test 5: mode3 first no Gemini → mode3_first + usedReferenceFallback False.
- **Test 6 (C2 + W1 + R2)**: mode3 first + Gemini exact-match → usedReferenceFallback True.
- **Test 7 (C2 + R8)**: mode3 first + Gemini motion_id no ref → fallback_reference_not_found via extra_warnings + dataclasses.replace 부재.
- Test 8: mode3 progress → mode3_progress + previousAnalysisId != None.
- **Test 9 (R3)**: `_extract_video_analysis_inputs` 1회 호출 시 RTMW estimate call_count == 1.
- **Test 10 (R3)**: legacy helper `_angles_and_video_path_from_video` 폐기 + `_extract_video_analysis_inputs` 신설.
- **Test 11 (R4)**: measure_body_profile fallback path → student_profile is BodyNormalizationProfile 인스턴스.
- Test 12 (B2): 불안정 swing pose_frames → bodyNormalizationConfidence < 0.5.
- **Test 13 (R2)**: `_extract_target_torso_px(pose_frames)` 정합.

### Task 2 — firestore_admin.complete_analysis + W5 (commit `a60b034`)

**Files**:
- `backend/shared/python/sunity_shared/firestore_admin.py`:
  - `complete_analysis(uid, analysis_id, result, *, angles=None, ..., body_comparison_report=None, body_normalization_profile=None)` 시그너처 확장.
  - bodyComparisonReport = `result` 내부 (AnalysisResult.bodyComparisonReport 정합).
  - bodyNormalizationProfile = top-level (mode3 progress prev fetch path).
  - `_validate_flat_dict_no_nested_array(payload, *, path="")` — recursive validator (W5).
  - `_validate_dict_only_scalars(d, *, path)` — list[dict] 원소 안에서 nested 금지 (store_gemini_cache:186-199 패턴 재사용).
  - 두 dict 모두 validator 통과 강제 — 위반 시 TypeError + path 정보.

**Tests (10 PASS)** — `test_firestore_admin_body_comparison.py`:
- Test 1: body_comparison_report kwarg → result 내부.
- Test 2-3: W5 list[str] + list[dict-of-scalars] 허용.
- Test 4: W5 list[list] reject.
- Test 5: W5 list[dict-with-nested-list] reject.
- Test 6: body_comparison_report=None → key 부재.
- Test 7: body_normalization_profile dict → top-level.
- Test 8 (C14): pose_reliability_low finding 통과.
- Test 9: scaleProfile 안의 list[scalar] 허용 (top-level dict 안).
- Test 10 (C2): list_reference_motions_by_name 신설 폐기.

### Task 3 — _dataclass_to_camel_case_dict (C8) + frontend I2 (commit `fc75212`)

**Files**:
- `app/src/lib/userAnalyses.ts` — Korean defensive comment 추가 + literal "bodyComparisonReport" (I2 positive assertion). TS 타입 정합 — runtime 변환 없음.

**Tests (12 PASS)**:
- `test_dataclass_to_camel_case_dict.py` (7 test) — 5 case 명시 + `_snake_to_camel` helper + scalar passthrough + dict input.
- `test_pipeline_firestore_integration.py` (5 test) — end-to-end mock-based:
  - Test 1: mode1 → complete_analysis 의 body_comparison_report arg camelCase 필드.
  - Test 2: R4 student_profile → body_normalization_profile arg camelCase 필드.
  - Test 3: body_comparison_report=None graceful.
  - Test 4: validator TypeError raise 정합.
  - Test 5: userAnalyses.ts I2 positive assertion.

### Task 4 — Phase 6 통합 smoke + C14 grep gate + C15 (commit `77383a1`)

**Files**:
- `backend/tests/phase06/test_phase06_integration_smoke.py` (11 test) — must_haves.truths 통합:
  - `test_full_pipeline_mode1_smoke` — 전체 mode1 end-to-end.
  - `test_full_pipeline_mode3_first_no_fallback_smoke` — Gemini OFF.
  - **`test_full_pipeline_mode3_first_with_gemini_fallback_smoke` (C2 + W1 + R2)** — matched ref → usedReferenceFallback True.
  - **`test_full_pipeline_mode3_first_with_gemini_motion_id_no_ref_match_smoke` (C2 + R8)** — fallback_reference_not_found.
  - **`test_full_pipeline_mode1_ref_source_pose_missing_smoke` (R2 canary)** — reference_source_pose_missing + scaleProfile None.
  - **`test_full_pipeline_rtmw_estimate_call_count_is_one_smoke` (R3)** — estimate call_count == 1.
  - **`test_full_pipeline_student_profile_non_null_smoke` (R4)** — fallback_profile crash 0.
  - `test_full_pipeline_all_must_haves_emitted` — comparisonType 3 cases + warnings frozenset.
  - **`test_pose_reliability_low_deficit_code_in_findings` (C14)** — pose_reliability_low deficit + bad_angle 부재.
  - **`test_c14_no_bad_angle_literal_in_phase06_files` (C14 final grep gate)** — 5 파일 모두 bad_angle 부재.
  - **`test_c15_sam_build_artifacts_documented`** — Layer src 5종 박제.

**SAM 검증**: `sam validate` exit 0 (CLI 실행). `sam build --use-container` 는 Docker Desktop 가용 환경에서 별도 단계 — Plan 의 C15 spec 은 src 파일 박제만 본 plan 책임.

## Deviations from Plan

### 1. [Rule 1 - Bug] body_normalizer.measure_ipsf_absolute_deficits 의 expects iterate 오류

- **Found during:** Task 1 (mode1/mode3 path 통합 smoke 진입 시).
- **Issue:** `expects = getattr(technique_profile, "expects_extension", None)` — `TechniqueProfile.expects_extension(joint_key) -> bool` 은 method 객체. truthy 평가 후 `for joint_key in expects:` 시도 → `TypeError: 'method' object is not iterable`. Plan 06-01 의 algorithm 본체 bug (단위 테스트에서는 `expects_extension` attribute 가 없는 fake profile 만 사용했음).
- **Fix:** `joint_expectations` dict 에서 `JOINT_EXTEND` (= "extend") 값 키로 derive — `[k for k, v in joint_expectations.items() if v == "extend"]`. 의도 (Plan 06-01 docstring 의 "list of joint keys") 보존.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py:944-958`.
- **Commit:** `2e7d97c` (Task 1).

### 2. [Rule 3 - 변경] 기존 pipeline test 3종 업데이트 (legacy helper 폐기 정합)

- **Found during:** Task 1 final regression check.
- **Issue:** R3 fix 의 `_angles_and_video_path_from_video` 폐기로 기존 6 test 실패:
  - `test_pipeline_recognizer_switch.py::TestB8FixSignature::test_angles_and_video_path_helper_exists`
  - `test_pipeline_body_profile_injection.py::test_b8_signature_lock_preserved`
  - `test_pipeline_gemini_integration.py::test_process_with_gemini_recognizer_uses_gemini`
  - `test_pipeline_gemini_integration.py::test_process_without_env_uses_fallback`
  - `test_pipeline_gemini_integration.py::test_gemini_api_failure_falls_back_to_fallback`
  - `test_pipeline_gemini_integration.py::test_tempfile_cleanup`
- **Fix:** 3 test 파일 업데이트:
  - 시그너처 박제 test 를 `_extract_video_analysis_inputs` 신설 + legacy 폐기로 갱신.
  - Gemini integration test 의 `_stub_angles_with_path` factory 를 `_stub_extract_inputs(pipeline_mod, tmp_video_path)` 로 교체 (NamedTuple `_VideoAnalysisInputs` 반환).
  - `get_previous_analysis` lambda 시그너처에 `mode=None` 추가 (memory `get_previous_analysis mode 인자 박제` 정합 — pre-existing pipeline 변경 정합).
- **Files modified:** `backend/tests/test_pipeline_recognizer_switch.py`, `backend/tests/test_pipeline_body_profile_injection.py`, `backend/tests/test_pipeline_gemini_integration.py`.
- **Commit:** `2e7d97c` (Task 1).

## Deferred Issues

### test_estimated_height_scale_consumer_semantics 의 pre-existing 실패

- `test_python_consumers_have_semantic_comment_in_sunity_shared` 가 `body_normalizer.py:9` 에서 estimatedHeightScale 사용 시 인접 ±3 라인의 `torso-relative proportion heuristic` 주석 부재로 fail.
- **본 plan 의 변경 무관 — Plan 06-01 산출 시점부터 이미 실패하던 test**. `git stash` 로 모든 본 plan 변경 제거 후 재실행에도 동일 fail 확인.
- 본 plan scope 외 — Plan 06-01 의 LOW-1 v5 박제 정합 후속 fix 필요 (별도 plan 또는 06-01 hotfix).

### 그 외 4 pre-existing collection errors

- `test_compare_body_profile_smoke.py` 4 test (ModuleNotFoundError: 'backend') — `backend.research.evaluations.*` import 패턴 박제 결손. Plan 06-02 변경 무관. 별도 path 박제 fix 후속.

## Known Stubs

(없음 — Plan 06-02 산출은 production wiring. body_comparison_report 가 Firestore 에 실제로 저장되는 path 박제 + UI 노출은 Phase 12/12.5 책임.)

## Plan 06-03 진입 시그널

Plan 06-02 산출 = pipeline wiring + Firestore 통합 + frontend type 정합. Plan 06-03 책임:

1. 정은지 reference 5개 영상의 `bodyNormalizationProfile` 백필 — Phase 2 `measure_body_profile` 의 reference video path 호출.
2. `bodyComparisonSourcePose` 백필 — 대표 hold frame 의 17 keypoint × 4채널 flat values 추출 (R2 wiring 의 source 측 contract).
3. Firestore reference 컬렉션 갱신 — `seed-reference-motions.mjs` 확장 또는 신규 `seed-reference-body-profile.mjs` 신설.
4. C5 dry-run flag + C6 belle Pod sweep (deferred) + R7 dry-run ordering.

Plan 06-03 진입 = wave 3 (별도 분리 가능 — Plan 06-02 wiring 가 백필 데이터 부재 시에도 graceful — R2 canary `reference_source_pose_missing` 명시 fallback 박제).

## Self-Check: PASSED

### Created files (7 신규 test 파일)

- `backend/tests/phase06/test_technique_profile_motion_id.py` — FOUND
- `backend/tests/phase06/test_gemini_recognizer_populates_motion_id.py` — FOUND
- `backend/tests/phase06/test_pipeline_body_comparison.py` — FOUND
- `backend/tests/phase06/test_firestore_admin_body_comparison.py` — FOUND
- `backend/tests/phase06/test_pipeline_firestore_integration.py` — FOUND
- `backend/tests/phase06/test_dataclass_to_camel_case_dict.py` — FOUND
- `backend/tests/phase06/test_phase06_integration_smoke.py` — FOUND

### Commits

- `8c5b002` Task 0 — TechniqueProfile.motion_id + Gemini populate (C2 + R1)
- `2e7d97c` Task 1 — pipeline body_normalizer wiring + R3/R4/R2/R8/C2
- `a60b034` Task 2 — firestore_admin + W5 validator
- `fc75212` Task 3 — _dataclass_to_camel_case_dict + frontend I2
- `77383a1` Task 4 — Phase 6 통합 smoke + C14 grep gate + C15

전체 phase06 suite 107/107 PASS, 기존 pipeline regression check 156/156 PASS, tsc --noEmit clean, sam validate exit 0.
