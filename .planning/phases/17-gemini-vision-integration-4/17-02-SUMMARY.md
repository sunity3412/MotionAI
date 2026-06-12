---
phase: 17-gemini-vision-integration-4
plan: 02
subsystem: backend
tags: [gemini, vision, finding, guardrail, pipeline, python]

# Dependency graph
requires:
  - phase: 17-gemini-vision-integration-4 (plan 01)
    provides: GeminiVisionCall + FindingFlags + resolve_model("C") + _gemini_vision_enabled
  - phase: 06-rtmw-engine
    provides: _extract_video_analysis_inputs (RTMW 1회 박제) + local_video_path 박제
provides:
  - sunity_shared.gemini.scene_finder.find_scene_flags — 영역 C Finding 4 flag + G4 가드
  - pipeline._call_wave1_scene_finder — wave 1 진입점 (skip 조건 + graceful)
  - pipeline._resolve_is_reference — S3 key prefix 1차 + Firestore mode 2차
  - pipeline._finding_enabled — GEMINI_FINDING_ENABLED env gate
  - firestore_admin.complete_analysis(gemini_c=...) — geminiC flat object 박제
affects:
  - 17-gemini-vision-integration-4 (plan 03 영역 D keypoint refinement — occlusion_severe gate)
  - 17-gemini-vision-integration-4 (eval plan — E5 PASS rate 측정 source)

# Tech tracking
tech-stack:
  added:
    - sunity_shared.gemini.scene_finder 모듈 신설
    - pipeline app.py wave 1 wiring 박제 (4 helper 신설)
  patterns:
    - "G4 reference 가드 (is_reference=True + occlusion_severe=True → flag 전체 폐기)"
    - "Graceful 폴백 (call None / 예외 흡수 → 빈 flag dict / None) — 분석 흐름 차단 0"
    - "is_reference 박제 다중 source (S3 key prefix 1차 + Firestore mode 2차) — T-17-09 spoofing 정합"
    - "_process 시그너처 변경 0 박제 — RunPod / Lambda SQS caller 변경 0"
    - "B4 hard gate (S3 재다운로드 / RTMW 재실행 0) — local_video_path 만 사용"

key-files:
  created:
    - backend/shared/python/sunity_shared/gemini/scene_finder.py
    - backend/tests/gemini/test_scene_finder.py
    - backend/tests/test_pipeline_geminic_wiring.py
  modified:
    - backend/shared/python/sunity_shared/gemini/__init__.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/functions/pipeline/app.py

key-decisions:
  - "find_scene_flags 는 dict 반환 (FindingFlags Pydantic 인스턴스 직접 노출 X) — caller (pipeline) 는 model_dump 박혀있는 flat dict 만 박제. meta (model / tokens_used / latency_ms) 와 guardrail_triggered / error 박제도 같은 dict 안에 박힌다 (flat object Firestore 박제 정합)."
  - "_call_wave1_scene_finder 가 별도 helper — find_scene_flags 박제 직접 호출 X. Skip 조건 (GEMINI_FINDING_ENABLED OFF / local_video_path None / 예외) 박제가 _process 본체에 들어가면 reader 복잡도 증가 + 향후 wave 2 (B/D) 호출 시 async helper 박제 정합 (asyncio.gather wave 2)."
  - "is_reference 박제는 두 source (S3 key prefix + Firestore mode) — T-17-09 spoofing 가드. 단일 source (Firestore mode 만) 박제 시 사용자가 mode 박제 fabricated 영상 업로드 시 reference 분기 우회 risk. S3 key prefix 가 1차 — 정은지 등록 영상은 무조건 reference/ 박힘."
  - "_process 시그너처 박제 변경 0 (`_process(bucket, key, uid, analysis_id)`) — is_reference 인자 추가 박제 X. 3차 R-W3 정합. RunPod server.py:111 / Lambda SQS path 둘 다 caller 갱신 0."
  - "tokens_used 박제 = 0 placeholder — GeminiVisionCall.call() 시그너처는 parsed 결과만 반환 (response 객체 미전달). usage_metadata 박제는 후속 plan (Phase 17 eval/F8) 에서 client 박제 시그너처 확장 시 박힘. 본 plan 박제는 latency_ms 만 실측."
  - "graceful 예외 흡수 (BLE001 noqa) — find_scene_flags 가 ValueError (G1 객관성 가드 매치) raise 시에도 wave 1 helper 가 흡수. 본래 G1 은 hard fail (caller 인지) 의도지만, wave 1 의 hard fail 이 전체 분석 흐름을 차단하면 사용자가 결과 화면을 못 봄 — Phase 17 eval/guardrail plan 에서 raw text log 로 추적 + 운영자 alert path 박힐 예정 (본 plan scope 외)."

patterns-established:
  - "Wave 1 helper pattern — find_scene_flags 호출 단위 박제 분리 (skip + graceful + 예외 흡수). 후속 wave 2 (영역 B/D 병렬) 박제 시 동일 패턴 박힌다."
  - "Reference 영상 판별 다중 source — S3 key + Firestore mode OR. 후속 plan (영역 A reference 등록) 박제 시 동일 패턴 박힘."

requirements-completed:
  - VISION-03

# Metrics
duration: ~45min
completed: 2026-06-12
---

# Phase 17 Plan 02: Gemini Vision 영역 C Finding 장면 인식 Summary

**영역 C Finding 4 flag (그립/백벤드/occlusion/카메라 angle) 을 Gemini 3.5 Flash 로 호출 + Pod _process 의 RTMW estimate 직후 wave 1 wiring + G4 정은지 영상 occlusion_severe FP 가드 + Firestore geminiC 박제**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-06-12 (Plan 17-01 직후)
- **Completed:** 2026-06-12
- **Tasks:** 2 (TDD — RED → GREEN per task)
- **Files modified:** 6 (3 created + 3 modified)
- **Tests added:** 25 (11 scene_finder + 14 pipeline wiring)

## Accomplishments

- `sunity_shared.gemini.scene_finder.find_scene_flags(video_path, is_reference=False)` 신설 — 영상 path → 4 flag dict (grip_visible / backbend_present / occlusion_severe / camera_angle_problematic) + notes_ko + meta (model / tokens_used / latency_ms) + guardrail_triggered + error 박제.
- **G4 정은지 영상 가드** — `is_reference=True + occlusion_severe=True` 동시 시 4 flag 전체 False 폐기 + `guardrail_triggered="G4_reference_occlusion_fp"` 박힘. PROJECT.md "고수가 낮게 나오는 위양성 (정은지 영상 41점 같은) 없이" 직격 방지. notes_ko 는 audit 용 보존.
- **Graceful 폴백** — `GeminiVisionCall.call()` 가 None 반환 시 (API 키 미설정 / 4xx / schema 검증 실패 / Files API FAILED / timeout) 빈 flag dict + `error="api_or_schema_fail"` + latency_ms 박힘. 분석 흐름 차단 0.
- **Model 결정 단일 source** — `resolve_model("C", env_override=GEMINI_C_MODEL_OVERRIDE or GEMINI_C_MODEL)`. raw default string 박제 0. ALLOWED_MODELS 미통과 시 `ValueError` (graceful X — hard fail). `GEMINI_C_MODEL_OVERRIDE` 는 emergency manual override path (E5 PASS rate 미달 운영 대응).
- **Pipeline wave 1 wiring** — `_extract_video_analysis_inputs` 직후 + recognizer.recognize 직전 박제. 4 helper 신설:
    - `_resolve_is_reference(key, meta)` — S3 key prefix `reference/` 1차 + Firestore mode `mode1_register` 2차.
    - `_finding_enabled()` — `GEMINI_FINDING_ENABLED` env (default "1") 박제 falsy 검사.
    - `_call_wave1_scene_finder(local_video_path, is_reference)` — skip 조건 (None local / OFF env / 예외) 박제 흡수.
    - `find_scene_flags` import + 호출.
- **B4 hard gate 박제** — `find_scene_flags` 안에서 boto3 S3 download / `_POSE_ESTIMATOR` / `_RTMW_ENGINE` 호출 0. caller `local_video_path` (Phase 6 `_extract_video_analysis_inputs` 가 1회만 download + RTMW 1회만 실행) 만 사용. 테스트 박제로 회귀 차단.
- **`_process` 시그너처 변경 0** — `_process(bucket, key, uid, analysis_id)` 박제 그대로. is_reference 박제는 내부 변수. RunPod server.py:111 / Lambda SQS path 둘 다 caller 갱신 0 (3차 R-W3 정합).
- **Firestore `geminiC` 박제** — `firestore_admin.complete_analysis(gemini_c=...)` kwarg 박제. flat object 박제 ([[firestore-nested-array-flat]] 정합, W5 validator 재사용 회귀 차단). gemini_c=None 시 Firestore payload 에 `geminiC` 박힘 0 (불필요한 None 박제 차단).
- 25 unit tests — 외부 네트워크 / S3 / RTMW 호출 0.

## Task Commits

각 task atomic commit (TDD — RED → GREEN per task):

1. **Task 1: find_scene_flags 모듈 + G4 정은지 영상 가드 + Firestore geminiC kwarg** — `dbb9d1c` (feat)
2. **Task 2: pipeline _process 영역 C wave 1 wiring + gemini_c kwarg 전달** — `ff017ef` (feat)

## Files Created/Modified

- **Created:**
    - `backend/shared/python/sunity_shared/gemini/scene_finder.py` — find_scene_flags + G4 가드 + graceful 폴백 (206 lines).
    - `backend/tests/gemini/test_scene_finder.py` — 11 unit tests (정상 / G4 발동 / G4 미발동 / 비reference occlusion / graceful 폴백 / env override / disallowed model / complete_analysis kwarg 검증).
    - `backend/tests/test_pipeline_geminic_wiring.py` — 14 통합 tests (wave 1 helper 5 + is_reference 판별 5 + import/source grep 2 + B4 hard gate 1 + 예외 흡수 1).
- **Modified:**
    - `backend/shared/python/sunity_shared/gemini/__init__.py` — `find_scene_flags` export 박제 (3 lines).
    - `backend/shared/python/sunity_shared/firestore_admin.py` — `complete_analysis` 시그너처에 `gemini_c: dict | None = None` kwarg 추가 + `geminiC` Firestore 박제 + W5 validator 호출 (9 lines).
    - `backend/functions/pipeline/app.py` — import `find_scene_flags` + 4 helper 신설 + `_process` 안 wave 1 호출 + `complete_analysis(gemini_c=...)` 박제 (104 lines).

## Decisions Made

- **find_scene_flags 는 dict 반환 (FindingFlags Pydantic 인스턴스 직접 노출 X)**: caller (pipeline) 가 Firestore 박제 시 flat dict 박혀야 함. Pydantic instance 그대로 박으면 caller 가 `.model_dump()` 호출 박제 책임 — 분리. dict 반환으로 meta (model / tokens_used / latency_ms) + guardrail_triggered + error 박제도 동일 dict 안 통합.
- **`_call_wave1_scene_finder` 별도 helper**: skip 조건 (None local / OFF env / 예외 흡수) 박제가 `_process` 본체에 들어가면 reader 복잡도 증가. 향후 wave 2 (B/D 병렬) 박제 시 동일 패턴 박힘 — 미리 분리.
- **is_reference 다중 source (S3 key + Firestore mode)**: T-17-09 spoofing 가드. 단일 source (Firestore mode 만) 박제 시 사용자가 mode 박제 fabricated 영상 업로드 시 reference 분기 우회 risk. S3 key prefix `reference/` 가 1차 — 정은지 등록 영상은 무조건 그 prefix 박힘.
- **`_process` 시그너처 박제 변경 0**: 3차 R-W3 정합. `is_reference` 인자 추가 박제 X — RunPod server.py:111 / Lambda SQS path 둘 다 caller 갱신 0. is_reference 박제는 내부 변수 `is_reference_local`.
- **tokens_used = 0 placeholder**: `GeminiVisionCall.call()` 박제 시그너처는 parsed 결과만 반환 (response 객체 미전달). usage_metadata 박제는 후속 plan (Phase 17 eval/F8 — Phoenix trace join) 에서 client 박제 시그너처 확장 시 박힘. 본 plan 박제 scope 는 latency_ms 만 실측.
- **graceful 예외 흡수 (BLE001 noqa) — wave 1 helper 박제**: `find_scene_flags` 가 `ValueError` (G1 객관성 가드 매치) raise 시에도 wave 1 helper 가 흡수. 본래 G1 은 hard fail (caller 인지) 의도지만, wave 1 의 hard fail 이 전체 분석 흐름을 차단하면 사용자가 결과 화면을 못 봄. Phase 17 eval/guardrail plan 박제에서 raw text log 추적 + 운영자 alert path 박힐 예정.

## Deviations from Plan

None — plan 박제 정신 그대로 실행. 다음은 plan 박제 정합 보조 박제:

- Plan task 2 의 `<behavior>` 항목 박제 "find_scene_flags 호출 횟수 + scene_result 가 None 일 때도 complete_analysis 가 정상 호출되는지" 통합 검증은 `_process` 본체 박제 dependency depth 가 깊어 (recognizer.recognize → KISMAM → Phase 6/8/9/12 까지 박혀야 complete_analysis 호출 도달) 본 plan 박제 단위 단순 unit 박제로 fully reachable X. 대신:
    - `_call_wave1_scene_finder` 박제 helper 단위로 1회 호출 + skip 분기 검증 (5 케이스).
    - `_resolve_is_reference` 박제 helper 단위로 분기 검증 (5 케이스).
    - `find_scene_flags` 박제 source grep 회귀 (2 케이스 — import + 호출 라인).
    - 실 `_process` 종단 통합 박제는 후속 Phase 17 eval plan / E6 정은지 영상 게이트 박제로 위임.
- `tokens_used` 박제 placeholder 0 박힘 — AI-SPEC §7 M2 박제 source (response.usage_metadata.total_token_count) 는 `GeminiVisionCall.call()` 박제 시그너처 확장 필요. 본 plan 박제 scope (wave 1 wiring + G4 가드) 외 — 후속 eval plan 에서 client 박제 시그너처 확장 시 실값 박힘.

## Issues Encountered

- 기존 pre-existing test collection errors 10건 (`tests/test_compare_engines_smoke.py`, `tests/test_debug_gap_root_cause_smoke.py`, `tests/test_spike_*.py` 등) — 본 plan scope 외 (다른 phase 박제 책임). 회귀 0 — 본 plan 박제 박힌 파일 (`tests/gemini/test_scene_finder.py` + `tests/test_pipeline_geminic_wiring.py`) 25 tests 모두 PASS, 회귀 검증 (`tests/gemini/`, `tests/test_pipeline_vision_gate.py`, `tests/test_firestore_admin_gemini_cache.py`, `tests/pipeline/`) 127 tests 모두 PASS.

## Known Stubs

- `find_scene_flags` 의 `tokens_used` 박제 = 0 placeholder. AI-SPEC §7 M2 박제 (token cost trace) 박제는 후속 plan (Phase 17 eval/F8 — Phoenix trace join) 에서 `GeminiVisionCall.call()` 박제 시그너처 확장 시 박힘. 본 plan 박제 scope 외.

## User Setup Required

None — 본 plan 박제는 코드 베이스만. 운영 deployment 시:
- Lambda env: 기존 `GEMINI_API_KEY` 박제 (Phase 5 박제 재사용) + `GEMINI_FINDING_ENABLED` default "1" (Plan 17-01 박제 정합).
- RunPod env: 동일 — GEMINI_API_KEY + GEMINI_FINDING_ENABLED.
- 운영 대응 시 `GEMINI_C_MODEL_OVERRIDE=gemini-3.1-pro-preview` 박제 manual override (E5 PASS rate 미달 시).
- Firestore: 기존 `users/{uid}/analyses/{id}` doc 에 `geminiC` 필드 자동 박힘 — 별도 schema 박제 0.

## Self-Check: PASSED

- 6 expected files (3 created + 3 modified) 모두 FOUND.
- 2 commits (dbb9d1c, ff017ef) 모두 git log 에 FOUND.
- 25 unit tests 모두 PASSED — `pytest backend/tests/gemini/test_scene_finder.py backend/tests/test_pipeline_geminic_wiring.py -q`.
- 회귀 검증: `pytest backend/tests/gemini/ backend/tests/test_pipeline_vision_gate.py backend/tests/test_firestore_admin_gemini_cache.py backend/tests/pipeline/` → 127 tests PASS, 회귀 0.
- `python3 -c "from sunity_shared.gemini import find_scene_flags"` 통과 (export 박제).
- `python3 -c "from sunity_shared.gemini.scene_finder import find_scene_flags"` 통과.
- `grep -n "find_scene_flags" backend/functions/pipeline/app.py | grep -v ^[0-9]*:#` 결과 5건 (import 1 + 호출/주석 4 — 박제 ≥ 2 통과).
- `grep -n "gemini_c" backend/shared/python/sunity_shared/firestore_admin.py | grep -v ^[0-9]*:#` 결과 11건 (kwarg + 박제 박힘 ≥ 1 통과).
- G4 가드 회귀: `test_reference_with_occlusion_triggers_guardrail` PASS — `guardrail_triggered="G4_reference_occlusion_fp"` 박힘 검증.

## Next Phase Readiness

- Plan 03 (영역 D keypoint refinement) 가 본 plan 박제 `find_scene_flags` 결과의 `occlusion_severe` flag 박제 skip gate 로 사용 — Firestore `geminiC.occlusion_severe` 박제 직접 조회 또는 `_process` 안 scene_result 박제 변수 재사용.
- Plan 04 / 05 (영역 B / 영역 A) wave 2 호출도 동일 패턴 박힘 — `_call_wave2_*` helper 신설 후 asyncio.gather 박제 병렬화 (현 wave 1 은 단독 호출이라 asyncio 박제 X — `_call_wave1_scene_finder` 박제 sync, 후속 wave 2 박제 시 async wrapper 박힐 예정).
- 후속 Phase 17 eval plan (E5 PASS rate / E6 정은지 영상 게이트) 가 본 plan 박제 `geminiC` 박제 Firestore 필드 박제 source 로 사용.

---
*Phase: 17-gemini-vision-integration-4*
*Completed: 2026-06-12*
