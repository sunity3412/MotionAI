---
phase: 08-jerk-jitter
plan: 03
subsystem: backend-pipeline-frontend
tags: [phase-08, layer2-recognizer-reuse, pipeline-wiring, firestore, frontend-normalize, sam-smoke, reviews-cycle-2-revised, post-sweep-fix, axis-metric-redesign-pending]

# Dependency graph
requires:
  - phase: 08-jerk-jitter
    plan: "00"
    provides: PoleLine2D + PoleAxisMeasurement + CoordinateSpace + ContactPrimitiveKind + build_pole_axis_measurement + median_torso_length + 25-timestamp preflight spec
  - phase: 08-jerk-jitter
    plan: "01"
    provides: ForceSignalsReport 3-way schema + 20 warning code enum + contact_points.yaml + 6 programmatic fixture builders
  - phase: 08-jerk-jitter
    plan: "02"
    provides: force_signals.py 본체 (5 dataclass + compute_force_signals umbrella + _layer1_confidence_from_preflight + _min_confidence ceiling helper)
provides:
  - force_signals.compute_phase_boundaries Layer 2 활성 — TechniqueProfile.key_moments reuse (REVIEWS R6 정합, 신규 GeminiMomentExtractor singleton 영구 차단)
  - FORCE_SIGNALS_LAYER2_ENABLED env flag (Phase 5 RECOGNIZER_BACKEND 와 분리, REVIEWS R7)
  - PREFLIGHT_LABEL_GATE_PASSED env helper (`_preflight_label_gate_passed()`, REVIEWS Cycle 2 NEW HIGH #1 / R4 carryover)
  - GEMINI_MODEL env wiring 양쪽 (judging/gemini_moment_extractor.py + analysis/gemini_technique_recognizer.py) — default 'gemini-2.5-flash', REVIEWS Cycle 2 R8 carryover
  - firestore_admin scoped validator `_validate_force_signals_report` — list[str] inside list[dict] 화이트리스트 (REVIEWS Cycle 2 NEW HIGH #3 / firestore-nested-array-flat 영구 보존)
  - complete_analysis(force_signals_report=) kwarg
  - _VideoAnalysisInputs.pole_axis_measurement 5번째 필드 (REVIEWS R10)
  - HoughPoleDetector.detect_with_line() image-space PoleLine2D 박제 (in-line fix B, post-sweep)
  - compute_axis_deviation pole_aligned 3D fallback (in-line fix B', RTMW keypoints_2d 부재 대응)
  - _map_moments_to_5phase setup/hold/release 단독 boundary 도출 (in-line fix C, monotonic 위반 by construction 차단)
  - userAnalyses.normalize() forceSignalsReport null-guard (WR-02 B1 패턴 정합)
  - 19 phase08 신설 test + 11 pipeline 통합 test + 1 phase06 brittle assertion 구조적 강화
affects:
  - Phase 9 force_pattern 추론 — 4 metric 직접 입력 source
  - Phase 12 결과 화면 오버레이 — coordinate_space 별 overlay 분기
  - Phase 8.5 (NEW, 신설 예정) — axis distance metric 도메인 정합 redesign (pole_aligned origin 미정의 + thresholds 단위 mismatch 해소)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Layer 2 = recognizer moments reuse 패턴 — TechniqueProfile.key_moments 박제 source 단일화. Phase 5 GeminiTechniqueRecognizer 가 이미 호출한 moments 를 Phase 8 가 직접 활용 → 중복 Gemini call 영구 차단 (REVIEWS R6). TechniqueCache round-trip 박제 (REVIEWS Cycle 2 §3 MEDIUM)."
    - "Env separation 패턴 — FORCE_SIGNALS_LAYER2_ENABLED 별도 flag (Phase 5 RECOGNIZER_BACKEND 와 분리, REVIEWS R7). default off — env 박제 unset 시 Layer 2 비활성. 운영 활성화는 belle env 박제만으로 가능 (코드 변경 0)."
    - "Scoped validator 패턴 (REVIEWS Cycle 2 NEW HIGH #3) — `_validate_dict_only_scalars` 본체 변경 영구 0. firestore-nested-array-flat 메모 정합 보존. 대신 `_validate_force_signals_report` 신설 — forceSignalsReport 안 metric dict 의 warnings/unstableBodyParts list[str] 만 화이트리스트. 다른 path (bodyComparisonReport) 는 strict 유지 → 회귀 0."
    - "Env helper 3-state 패턴 — `_preflight_label_gate_passed()` 가 '1'/'true'/'on'/'yes' → True, '0'/'false'/'off'/'no' → False, '' (unset) → None. compute_force_signals 호출 시 본 helper 결과 박제 → belle 운영 작업 시 env 박제만으로 Layer 1 confidence='medium' 승급 (코드 변경 0)."
    - "In-line sweep-driven fix 패턴 — Plan 03 의 manual checkpoint sweep 결과 발견된 4 fix (race / pole detection / pole_aligned fallback / Layer 2 mixing) 를 commit c71c75b + f627905 로 in-line 박제. PLAN 박제 정신상 'manual sweep 후 발견된 정합성 fix' 는 Plan 03 scope extension (4건 deviation 박제)."

key-files:
  created:
    - backend/tests/phase08/test_compute_phase_boundaries_layer2.py
    - backend/tests/phase08/test_compute_force_signals_layer2.py
    - backend/tests/phase08/test_firestore_lockstep.py
    - backend/tests/phase08/test_gemini_model_env_driven.py
    - backend/tests/pipeline/__init__.py
    - backend/tests/pipeline/test_pipeline_phase8.py
  modified:
    - backend/shared/python/sunity_shared/analysis/force_signals.py
    - backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
    - backend/shared/python/sunity_shared/analysis/technique.py
    - backend/shared/python/sunity_shared/analysis/pole/detector.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
    - backend/functions/pipeline/app.py
    - app/src/lib/userAnalyses.ts
    - backend/tests/test_pipeline_gemini_integration.py
    - backend/tests/phase06/test_technique_profile_motion_id.py

key-decisions:
  - "Plan 08-03 R6: Layer 2 = TechniqueProfile.key_moments reuse — 신규 GeminiMomentExtractor singleton 영구 차단. TechniqueProfile.key_moments 필드 신설 (technique.py) + GeminiTechniqueRecognizer._build_profile populate + TechniqueCache round-trip (source_response_excerpt 박제 추가, REVIEWS Cycle 2 §3 MEDIUM). compute_phase_boundaries(technique_profile=) 인자 — gemini_extractor 인자 deprecated noop."
  - "Plan 08-03 R7: FORCE_SIGNALS_LAYER2_ENABLED 별도 env flag — Phase 5 RECOGNIZER_BACKEND 와 분리. default off (env unset → Layer 2 비활성). `_force_signals_layer2_env_enabled()` helper + `_force_signals_layer2_enabled()` pipeline helper 박제."
  - "Plan 08-03 R8 carryover (Codex Cycle 2): 실 default 위치 = judging/gemini_moment_extractor.py:48 — recognizer.py 가 아님. `DEFAULT_GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')` 박제 (gemini-2.0-flash-exp 2026-06-01 EOL, gemini-3.1-pro-preview hardcoded 박제 영구 제거). 'gemini-2.5-flash' = 현재 stable Flash family. Gemini 3.x Pro 가용 시 belle env 박제 변경 (코드 변경 0). recognizer.py 도 동일 GEMINI_MODEL env reuse."
  - "Plan 08-03 R10: _VideoAnalysisInputs 5번째 필드 `pole_axis_measurement` 신설. _extract_video_analysis_inputs 본체에 `build_pole_axis_measurement(axis_3d=..., line=...)` 박제. (in-line fix B 전: vertical fallback + line=None → coordinate_space='unavailable' / fix B 후: HoughPoleDetector.detect_with_line + line 박제 → coordinate_space='image_2d')."
  - "Plan 08-03 Cycle 2 NEW HIGH #1 (R4 carryover plumbing): pipeline/app.py 의 `_preflight_label_gate_passed()` env helper 신설 (PREFLIGHT_LABEL_GATE_PASSED env 3-state). compute_force_signals 호출 시 본 helper 결과 박제 — belle 운영 작업 시 코드 변경 0."
  - "Plan 08-03 Cycle 2 NEW HIGH #2 (Layer-2 except ceiling): compute_phase_boundaries 의 Layer 2 success/except 분기 둘 다 `_layer1_confidence_from_preflight()` ceiling 박제 + `_min_confidence(agreement, ceiling)`. Cycle 1 hardcoded 'medium' 박제 영구 제거. preflight=None → 'low' 강제."
  - "Plan 08-03 Cycle 2 NEW HIGH #3 (Firestore invariant): `_validate_dict_only_scalars` 본체 변경 영구 0 (firestore-nested-array-flat 보존). 신설 scoped validator `_validate_force_signals_report` — forceSignalsReport 안 metric dict 의 warnings/unstableBodyParts list[str] 만 화이트리스트. complete_analysis(force_signals_report=) kwarg path 만 본 validator. body_comparison_report path strict 유지 (회귀 0)."
  - "Plan 08-03 (in-line fix B, post-sweep): HoughPoleDetector.detect_with_line() — vertical line midpoint x median → PoleLine2D(point_image, direction_image, confidence, source='detected'). pipeline._ensure_adapters() _POLE_DETECTOR lazy init + cv2 graceful 분기. sweep 결과 5/5 영상 axisCoordSpace='unavailable' false negative 발견 → image_2d 진입 활성."
  - "Plan 08-03 (in-line fix B', post-sweep): compute_axis_deviation pole_aligned 3D fallback path — RTMW pose engine 이 PoseFrame.keypoints_2d 박제 X (3D pole_aligned 만 채움) → median_torso_length(image_2d) None → distance 정규화 불가. 해결: keypoints_2d 부재 감지 시 pole_aligned 자동 fallback (distance = sqrt(x²+y²), denominator = median_torso_length(pole_aligned)). warning 'coordinate_space_pole_aligned_fallback' + 'keypoints_2d_missing' 박제."
  - "Plan 08-03 (in-line fix C, post-sweep): _map_moments_to_5phase Layer 1 by_phase mixing 제거. setup/hold/release 3 moment 필수 — lock_start~hold_start 3등분 = transition/final_shape start. monotonic 위반 by construction 차단. setup/hold/release 누락 시 raise → Layer 1 fallback (graceful fallback 정신 유지)."
  - "Plan 08-03 (in-line fix A, post-sweep ops 정합): belle Pod sweep 시 sweep_temp/ S3 prefix 사용 — SQS race condition 우회 (production upload key path 영향 0, sweep ops 전용)."
  - "Plan 08-03 (deviation Rule 1): phase06/test_technique_profile_motion_id.py 의 brittle 'motion_id == fields[-1]' assertion → 구조적 안전 조건 (default 필드는 non-default 필드 뒤) 검증으로 박제. Plan 08-03 의 key_moments 신설 박제 forward-compatible 박제."

patterns-established:
  - "Plan 08-03 R6 패턴 — Phase 5 박제 GeminiTechniqueRecognizer 의 산출물 (TechniqueProfile.key_moments) 을 Phase 8 가 직접 reuse. 같은 Gemini call 의 결과를 두 phase 가 공유 = 중복 호출 영구 차단. TechniqueCache round-trip 박제로 cache-hit reconstruction 시 key_moments 도 정합."
  - "Plan 08-03 NEW HIGH #3 패턴 — strict validator 본체 변경 없이 path-specific 화이트리스트 추가. project-wide 영향 0 + 박제 정책 (firestore-nested-array-flat) 보존 + 새 path 의 graceful relaxation. scoped validator 신설은 'project memory 보존하면서 새 path 만 허용' 의 표준 박제 패턴."
  - "Plan 08-03 NEW HIGH #1 패턴 — env 3-state helper (`'1'/'true'/'on'/'yes' → True`, `'0'/'false'/'off'/'no' → False`, `'' → None`) 가 hardcoded 박제 영구 제거. 운영 활성화 = env 박제만, 코드 commit 없음."
  - "Plan 08-03 in-line sweep fix 패턴 — manual checkpoint sweep 실행 중 발견된 정합성 fix 는 Plan scope extension 으로 박제 (4건 deviation 섹션 박제). 다음 plan 으로 이연 시 sweep-to-prod gap 누적 → 본 Plan 안에서 즉시 fix + commit + push."

requirements-completed: [FORCE-01]

# Metrics
duration: ~270min (Task 1 + Task 2 fc3b6b7/ced1d87 ~120min + manual checkpoint 자동화 sweep validation + in-line fix B/B'/C ~150min)
completed: 2026-06-09
---

# Phase 8 Plan 03: Layer 2 Gemini 활성 + pipeline wiring + Firestore scoped validator + frontend normalize + post-sweep fix Summary

**force_signals.compute_phase_boundaries Layer 2 활성 (recognizer moments reuse, R6) + FORCE_SIGNALS_LAYER2_ENABLED env separation (R7) + GEMINI_MODEL env wiring 양쪽 (R8 carryover) + _preflight_label_gate_passed env helper (Cycle 2 NEW HIGH #1) + Layer 2 except 분기 ceiling 박제 (Cycle 2 NEW HIGH #2) + Firestore scoped validator (Cycle 2 NEW HIGH #3 — `_validate_dict_only_scalars` 본체 무수정) + _VideoAnalysisInputs.pole_axis_measurement (R10) + pipeline _process Phase 8 wiring + userAnalyses.normalize forceSignalsReport null-guard. 본 plan 의 manual checkpoint sweep 결과 발견된 4 정합성 fix (A race / B pole detection / B' pole_aligned 3D fallback / C Layer 2 monotonic) 를 in-line commit (c71c75b + f627905) 박제. Phase 8 종료 — 단, 정은지 5/5 영상 axis severity='high' 도메인 정합성 문제는 Phase 8.5 (NEW, axis-metric-redesign) 로 신설.**

## Performance

- **Duration:** ~270 min (Task 1 fc3b6b7 + Task 2 ced1d87 ~120min + manual checkpoint 자동화 ~30min + sweep 3차 + in-line fix B/B'/C ~120min)
- **Tasks:** 3 atomic commits (Task 1/Task 2/Task 3 manual checkpoint) + 2 in-line sweep-driven fix commits
- **Files modified:** 16 (10 modified + 6 created)
- **Test count:** Phase 08 103 PASS (Plan 08-00 18 + Plan 08-01 11 + Plan 08-02 51 + Plan 08-03 신설 23). Pipeline 11 신설 + 35 기존 = 46 PASS. 회귀 0 (phase06 156 + phase07 88 + pipeline 11 + phase08 103 = 358 PASS + 1 skipped).

## Accomplishments

- **R6 해소 (Layer 2 reuse, 신규 Gemini call 영구 차단)**: TechniqueProfile.key_moments 필드 신설 (analysis/technique.py). GeminiTechniqueRecognizer._build_profile populate + TechniqueCache round-trip 박제 (source_response_excerpt 박제 추가, REVIEWS Cycle 2 §3 MEDIUM 정합 — cache-hit reconstruction 시 key_moments None 으로 silently 비활성 영구 차단). force_signals.compute_phase_boundaries(technique_profile=) 인자 신설 — 본 인자의 key_moments reuse. gemini_extractor 인자 deprecated noop.
- **R7 해소 (env separation)**: FORCE_SIGNALS_LAYER2_ENABLED 별도 env flag. `_force_signals_layer2_env_enabled()` (force_signals.py) + `_force_signals_layer2_enabled()` (pipeline/app.py) helper 박제. default off — env unset 시 Layer 2 비활성. RECOGNIZER_BACKEND='gemini' 만으로는 Phase 8 Layer 2 활성 안 됨.
- **R8 carryover 해소 (Codex Cycle 2)**: 실 default 위치 = judging/gemini_moment_extractor.py:48 (recognizer.py 아님). `DEFAULT_GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')` 박제. 'gemini-2.0-flash-exp' literal grep 0 안전망. recognizer.py 도 동일 GEMINI_MODEL env reuse. Gemini 3.x Pro 가용 시 belle env 박제 변경 (코드 변경 0).
- **R10 해소 (pole_axis_measurement 노출)**: _VideoAnalysisInputs NamedTuple 5번째 필드 `pole_axis_measurement` 신설. _extract_video_analysis_inputs 본체에 `build_pole_axis_measurement(axis_3d=detected_pole, line=detected_line)` 박제 (in-line fix B 후 image_2d 활성). 기존 test_pipeline_gemini_integration.py 의 _stub_extract_inputs fixture 도 5번째 필드 추가.
- **Cycle 2 NEW HIGH #1 (R4 carryover plumbing)**: pipeline/app.py 의 `_preflight_label_gate_passed()` env helper 신설 (PREFLIGHT_LABEL_GATE_PASSED env 3-state). compute_force_signals 호출 시 본 helper 결과 박제. Cycle 1 의 hardcoded `preflight_label_gate_passed=None` 박제 영구 제거 (grep guard 0). belle 운영 작업: 25-timestamp PASS 후 `aws lambda update-function-configuration` 또는 RunPod env 박제 `PREFLIGHT_LABEL_GATE_PASSED=1` 박제만으로 gate flip.
- **Cycle 2 NEW HIGH #2 (Layer-2 except ceiling)**: compute_phase_boundaries 의 Layer 2 success/except 분기 둘 다 `_layer1_confidence_from_preflight(preflight_label_gate_passed)` ceiling 박제 + `_min_confidence(agreement, ceiling)`. Cycle 1 hardcoded 'medium' 박제 영구 제거. preflight=None except → 'low' 강제, preflight=True except → 'medium' 유지 (NOT 'high' promote).
- **Cycle 2 NEW HIGH #3 (Firestore invariant)**: `_validate_dict_only_scalars` 본체 변경 영구 0 ([[firestore-nested-array-flat]] 메모 영구 보존). 신설 scoped validator `_validate_force_signals_report(payload: dict) -> None` — `forceSignalsReport` 필드 안 metric dict 의 `warnings: list[str]` / `unstableBodyParts: list[str]` 만 화이트리스트. complete_analysis(force_signals_report=) kwarg 전달 시에만 본 validator 호출. body_comparison_report path 는 기존 strict validator 유지 → 회귀 0 (phase06 156 PASS).
- **pipeline wiring (1줄 호출)**: compare_body_profiles 호출 직후 force_signals.compute_force_signals 호출 + force_signals_dict 변환 + complete_analysis 의 force_signals_report kwarg 박제. mode 분기 무관 (mode1 / mode3_first / mode3_progress 모두). `_get_force_signals_layer2_recognizer()` singleton (Phase 5 `_ensure_recognizer` 재사용, 신규 instance 영구 차단).
- **frontend normalize**: userAnalyses.ts normalize() 의 result spread 안 bodyComparisonReport null-guard 직후 forceSignalsReport null-guard 박제 (Phase 7 WR-02 B1 immutable spread + ?? null fallback 패턴). 7 필드 default (version / overallConfidence / warnings / phaseBoundaries / axisMetrics / stabilityMetrics / contactMetrics).
- **In-line fix A (sweep ops 정합)**: belle Pod sweep 시 S3 sweep_temp/ prefix 사용 — SQS race condition 우회 (production upload key path 영향 0, sweep ops 전용 박제). 3차 sweep 5/5 영상 schema 정합 + 0 server_error.
- **In-line fix B (pole_geometry image_2d 활성)**: HoughPoleDetector.detect_with_line() 신설 — vertical line midpoint x median → PoleLine2D(point_image, direction_image, confidence, source='detected'). pipeline._ensure_adapters() _POLE_DETECTOR lazy init + cv2 graceful 분기 (test 환경 정합). _extract_video_analysis_inputs default_pole 박제 X → detected_pole + line 박제. 결과: low confidence 도 PoleLine2D 박제 → axis distance 산출 가능.
- **In-line fix B' (pole_aligned 3D fallback)**: compute_axis_deviation 이 keypoints_2d 부재 감지 시 pole_aligned 3D 경로 자동 fallback (RTMW pose engine 이 PoseFrame.keypoints_2d 박제 X 발견 후). pole_aligned 공간 산식: pelvis_distance = sqrt(x²+y²), chest_distance = sqrt(x²+y²), tilt = arcsin(|Δz|/||Δ||), denominator = median_torso_length(pole_aligned). warning 'coordinate_space_pole_aligned_fallback' + 'keypoints_2d_missing' 박제.
- **In-line fix C (Layer 2 Gemini moments 단독)**: _map_moments_to_5phase Layer 1 by_phase mixing 제거. setup/hold/release 3 moment 필수, lock_start ~ hold_start 3등분 = transition/final_shape start. monotonic 위반 by construction 차단. setup/hold/release 누락 시 raise → Layer 1 fallback (기존 graceful fallback 정신 유지).

## Task Commits

Each task / fix committed atomically:

1. **Task 1: Layer 2 wiring + Cycle 2 NEW HIGH #2/#3 + R8 carryover** — `fc3b6b7` (feat) — force_signals.py 본체 확장 + judging/gemini_moment_extractor.py + analysis/gemini_technique_recognizer.py + analysis/technique.py + firestore_admin.py + phase06 brittle assertion fix + 23 신설 test
2. **Task 2: pipeline wiring + Cycle 2 NEW HIGH #1 + R10 + frontend** — `ced1d87` (feat) — pipeline/app.py wiring + _preflight_label_gate_passed + _get_force_signals_layer2_recognizer + _VideoAnalysisInputs.pole_axis_measurement + userAnalyses.ts normalize + 11 pipeline 통합 test + test_pipeline_gemini_integration.py fixture 업데이트
3. **In-line fix B + C: pole detection + Layer 2 monotonic** — `c71c75b` (fix) — HoughPoleDetector.detect_with_line + pipeline._ensure_adapters lazy init + _map_moments_to_5phase setup/hold/release 단독 boundary
4. **In-line fix B': pole_aligned 3D fallback** — `f627905` (fix) — compute_axis_deviation pole_aligned 자동 fallback (keypoints_2d 부재 시) + 2 warning enum 박제

Manual checkpoint Task 3 자동화 산출물 (no separate commit — sweep validation 만):

- SAM validate PASS (sam build --use-container 은 belle Docker 환경 한정)
- Lambda env 갱신 (FORCE_SIGNALS_LAYER2_ENABLED=1, GEMINI_MODEL=gemini-2.5-flash, PREFLIGHT_LABEL_GATE_PASSED=0) — file URI 방식 (secret CLI leak 방지)
- Pod env 26개 복원 + Phase 8 3개 추가 + uvicorn restart (auth_configured:true, pipeline_loaded:true)
- Pod phase08 pytest 103/103 PASS
- 3차 sweep 정은지 5영상 (sweep_temp/ prefix → SQS race 0): schema 정합 5/5, axis distance 실값 산출 (B' fallback), 0 server_error

## Files Created/Modified

### Created (6)

- `backend/tests/phase08/test_compute_phase_boundaries_layer2.py` — 8 test (Layer 2 활성/비활성 + agreement high/disagreement major + runtime error + no duplicate Gemini call + Cycle 2 NEW HIGH #2 ceiling 박제).
- `backend/tests/phase08/test_compute_force_signals_layer2.py` — 5 test (umbrella Layer 2 + Cycle 2 NEW HIGH #2 none/passed/failure preflight matrix).
- `backend/tests/phase08/test_firestore_lockstep.py` — 6 test (scoped validator + strict 박제 회귀 0 + camelCase 변환).
- `backend/tests/phase08/test_gemini_model_env_driven.py` — 4 test (default 'gemini-2.5-flash' + env override + literal grep 안전망).
- `backend/tests/pipeline/__init__.py` — pipeline test package marker (빈 파일).
- `backend/tests/pipeline/test_pipeline_phase8.py` — 11 test (Layer 2 env matrix 4 + mode 분기 2 + complete_analysis kwarg 1 + pole_axis_measurement 1 + preflight gate env 3-state 3).

### Modified (10)

- `backend/shared/python/sunity_shared/analysis/force_signals.py` — Layer 2 본체 활성 + _force_signals_layer2_env_enabled / _should_invoke_layer2 / _build_phase_boundaries / _map_moments_to_5phase / _layer2_boundaries_from_technique_profile / _confidence_from_agreement helper 박제 + Cycle 2 NEW HIGH #2 ceiling 적용. In-line fix B' (pole_aligned 3D fallback) + in-line fix C (setup/hold/release 단독 boundary).
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` — GEMINI_MODEL env wiring (R8 carryover) + _build_profile 의 key_moments populate (R6).
- `backend/shared/python/sunity_shared/analysis/technique.py` — TechniqueProfile.key_moments: list[KeyMoment] | None 필드 신설 (Phase 8 Layer 2 reuse source).
- `backend/shared/python/sunity_shared/analysis/pole/detector.py` — HoughPoleDetector.detect_with_line() 신설 (in-line fix B): vertical line midpoint x median → PoleLine2D 박제. cv2 graceful 분기.
- `backend/shared/python/sunity_shared/firestore_admin.py` — scoped validator `_validate_force_signals_report` 신설 (Cycle 2 NEW HIGH #3) + complete_analysis(force_signals_report=) kwarg 박제. `_validate_dict_only_scalars` 본체 변경 0 ([[firestore-nested-array-flat]] 보존).
- `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` — DEFAULT_GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash') 박제 (R8 carryover, line 48). 'gemini-3.1-pro-preview' hardcoded 박제 영구 제거.
- `backend/functions/pipeline/app.py` — Phase 8 wiring + _preflight_label_gate_passed (NEW HIGH #1) + _get_force_signals_layer2_recognizer singleton + _force_signals_layer2_enabled + _VideoAnalysisInputs.pole_axis_measurement (R10). _ensure_adapters() _POLE_DETECTOR lazy init (in-line fix B). _extract_video_analysis_inputs detected_pole + line 박제.
- `app/src/lib/userAnalyses.ts` — normalize() 의 forceSignalsReport null-guard (WR-02 B1 immutable spread + ?? null fallback 패턴). 7 필드 default.
- `backend/tests/test_pipeline_gemini_integration.py` — _stub_extract_inputs fixture 의 _VideoAnalysisInputs 5번째 필드 (pole_axis_measurement) 추가.
- `backend/tests/phase06/test_technique_profile_motion_id.py` — brittle "motion_id == fields[-1]" assertion → 구조적 안전 조건 (default 필드는 non-default 필드 뒤) 검증 (deviation Rule 1).

## Decisions Made

본 plan 의 박제는 PLAN.md 의 must_haves.truths + REVIEWS Cycle 1 R6/R7/R10 + Cycle 2 NEW HIGH #1/#2/#3 + R8 carryover 정합 — 신설 결정 없음. 박제 정신은 frontmatter `key-decisions` 박제.

핵심 박제 정신 정합:

- [[firestore-nested-array-flat]] — `_validate_dict_only_scalars` 본체 변경 영구 0. scoped validator `_validate_force_signals_report` 가 forceSignalsReport path 만 화이트리스트. 메모 영구 보존.
- [[gsd-pod-work-push-first]] — 각 commit (fc3b6b7 / ced1d87 / c71c75b / f627905) 후 즉시 push 박제 (belle Pod 가 sweep 시 정확한 HEAD pull 보장).
- [[analysis-objectivity-no-human-scores]] — preflight gate = 시각 라벨링 (수치 score 아님). 5영상 sweep severity 분포 = sanity check only (calibration ground truth X). Phase 8.5 의 threshold 재설계도 IPSF Code of Points + 5영상 sweep 분포 기반 (사람 점수 라벨링 영구 금지).
- [[scoring-dimensions-ipsf]] — severity 임계 = 도메인 룰 fixed. Phase 8.5 가 axis distance metric 의 도메인 정합 재설계 (IPSF "축 이탈" 채점 항목 research 기반).
- [[single-camera-first-multi-view-last]] — coordinateSpace='image_2d' 우선 박제 (in-line fix B). pole_aligned 3D fallback (B') 는 RTMW keypoints_2d 부재 시 단일 시점 단독 path.
- [[mvp-simple-pilot-quality]] — graceful degrade (line/scale 미가용 시 distance None + warning, 분석 죽지 않음). In-line fix B + B' 가 pole 미검출 / keypoints_2d 부재 시 graceful fallback path 박제.
- [[feedback-analysis-first]] — 4 metric 본체 정확성 우선. Phase 8.5 신설 결정 = "현 axis severity='high' 5/5 정은지 영상" 도메인 잘못된 결과 발견 시 즉시 후속 plan 박제 (분석 정확도 최우선).
- [[no-baekje-filler]] — 코드/test 안 박제 표현 0회 (warning enum + lockstep grep 키만 영문).

## Deviations from Plan

### Auto-fixed Issues (Plan 03 Task scope 안 박제)

**1. [Rule 1 - Bug] phase06/test_technique_profile_motion_id.py brittle assertion 구조적 강화**

- **Found during:** Task 1 (Plan 08-03 R6 의 TechniqueProfile.key_moments 신설 박제 시)
- **Issue:** Plan 06-02 박제 test 가 'motion_id == fields[-1]' assertion 박제 (dataclass 의 마지막 필드 정합 확인). Plan 08-03 R6 의 key_moments 신설 박제 시 motion_id 가 더 이상 마지막 필드 X → test fail.
- **Fix:** assertion 을 구조적 안전 조건 (default 필드는 non-default 필드 뒤) 검증으로 박제. dataclass.fields() walk + non-default 필드 인덱스 < default 필드 인덱스 검증. Plan 06-02 의 R1 fix 정신 (non-default 앞 금지) 정합 + Plan 08-03 의 key_moments 신설 forward-compatible.
- **Files modified:** `backend/tests/phase06/test_technique_profile_motion_id.py`
- **Verification:** phase06 156 PASS (회귀 0) + Plan 08-03 의 key_moments 신설 통과.
- **Committed in:** `fc3b6b7` (Task 1)

### In-scope Additions (Plan 03 manual checkpoint sweep 결과 박제)

본 4건은 PLAN.md 의 manual checkpoint Task 3 ('belle 운영 작업 sweep 박제') 실행 결과 발견된 정합성 fix. 다음 plan 으로 이연 시 sweep-to-prod gap 누적 → Plan 03 scope extension 으로 in-line commit 박제 ([[gsd-pod-work-push-first]] 정합 — 즉시 push 박제).

**A. [Rule 3 - Blocking] sweep ops 정합 (S3 sweep_temp/ prefix)**

- **Found during:** 1차 sweep (정은지 5영상)
- **Issue:** belle Pod sweep 시 production upload key path (uploads/{uid}/{analysisId}.{ext}) 사용 시 S3 ObjectCreated → SQS 가 sweep 명령 완료 전 trigger → race condition.
- **Fix:** sweep 전용 S3 prefix `sweep_temp/` 박제 — production path 와 분리. 3차 sweep 5/5 영상 schema 정합 + 0 server_error.
- **Files modified:** sweep script (belle ops, 코드 X). production upload key path 영향 0.
- **Verification:** 3차 sweep 5/5 PASS + 0 server_error.
- **Committed in:** N/A (sweep ops 박제, 코드 변경 0)

**B. [Rule 2 - Missing Critical] HoughPoleDetector.detect_with_line() 신설 (pole 미검출 false negative)**

- **Found during:** 1차 sweep (정은지 5영상 axisCoordSpace='unavailable' 5/5 — pole 미검출 false negative)
- **Issue:** Plan 08-03 Cycle 1 박제 시 `_extract_video_analysis_inputs` 가 default_pole (vertical fallback) 박제 → `build_pole_axis_measurement(line=None)` → coordinate_space='unavailable'. 5/5 영상 axis distance 산출 불가.
- **Fix:** HoughPoleDetector.detect_with_line() 신설 (image-space PoleLine2D 박제: vertical line midpoint x median → PoleLine2D(point_image, direction_image, confidence, source='detected')). pipeline._ensure_adapters() _POLE_DETECTOR lazy init + cv2 graceful 분기. _extract_video_analysis_inputs default_pole 박제 X → detected_pole + line 박제. 결과: low confidence 도 PoleLine2D 박제 → axis distance 산출 가능 + warning 박제.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/pole/detector.py` (HoughPoleDetector.detect_with_line() 신설), `backend/functions/pipeline/app.py` (_ensure_adapters _POLE_DETECTOR lazy init + _extract_video_analysis_inputs detected_pole 박제), `backend/shared/python/sunity_shared/analysis/force_signals.py` (image_2d 활성 path 안정화).
- **Verification:** 2차 sweep 5/5 axisCoordSpace='image_2d' 진입 + 3차 sweep 5/5 schema 정합.
- **Committed in:** `c71c75b` (fix B+C)

**B'. [Rule 2 - Missing Critical] compute_axis_deviation pole_aligned 3D fallback (keypoints_2d 부재)**

- **Found during:** 2차 sweep (axisCoordSpace='image_2d' 진입 성공했으나 distance 5/5 영상 모두 null)
- **Issue:** RTMW pose engine 이 PoseFrame.keypoints_2d 박제 X (3D pole_aligned 만 채움) → median_torso_length(image_2d) None → distance 정규화 불가. image_2d 진입 성공해도 산출 0.
- **Fix:** compute_axis_deviation 이 keypoints_2d 부재 감지 시 pole_aligned 3D 경로 자동 fallback. pole_aligned 공간은 폴 축을 Z+ 정렬했으므로: pelvis_distance = sqrt(pelvis_x²+pelvis_y²), chest_distance = sqrt(chest_x²+chest_y²), shoulder/hip tilt = arcsin(|Δz|/||Δ||) (line 미사용), deviation_direction = mean (x, y) 부호 기반 outward/inward/up/down. denominator = median_torso_length(pole_aligned) (shoulder-hip midpoint distance, RTMW 정상 산출). warning 'coordinate_space_pole_aligned_fallback' (use_pole_aligned True 시) + 'keypoints_2d_missing' (line 가용한데 keypoints_2d 부재로 image_2d 차단 시) 박제.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/force_signals.py` (compute_axis_deviation pole_aligned fallback path + 2 warning 박제).
- **Verification:** 3차 sweep 5/5 영상 axis distance 실값 산출 (B' fallback) + 0 server_error.
- **Committed in:** `f627905` (fix B')

**C. [Rule 1 - Bug] _map_moments_to_5phase Layer 1 mixing 제거 (monotonic 위반 by construction 차단)**

- **Found during:** 1차 sweep (5/5 영상 Layer 2 monotonic 위반 → Layer 1 fallback)
- **Issue:** _map_moments_to_5phase 가 Layer 1 by_phase 와 Layer 2 moments 를 mixing → boundary 순서 monotonic 위반 가능 (Layer 2 의 moment 시점이 Layer 1 의 phase boundary 안에 들어가지 않을 시).
- **Fix:** Layer 1 by_phase mixing 제거. setup/hold/release 3 moment 필수 (Gemini 가 박제) — lock_start ~ hold_start 3등분 = transition/final_shape start. monotonic 위반 by construction 차단 (구조적 안전성). setup/hold/release 누락 시 raise → Layer 1 fallback (기존 graceful fallback 정신 유지).
- **Files modified:** `backend/shared/python/sunity_shared/analysis/force_signals.py` (_map_moments_to_5phase 본체 재설계).
- **Verification:** Layer 2 활성 시 monotonic 위반 0 (구조적 보장) + setup/hold/release 누락 시 Layer 1 fallback 유지.
- **Committed in:** `c71c75b` (fix B+C)

---

**Total deviations:** 1 Rule 1 (phase06 brittle assertion) + 4 in-scope additions (A sweep ops / B pole detection / B' pole_aligned fallback / C Layer 2 monotonic).

**Impact on plan:** Rule 1 1건 은 forward-compatibility 강화 (Plan 06-02 R1 정신 정합). In-scope additions 4건 은 manual checkpoint sweep 결과 발견된 정합성 fix — 모두 Plan 03 의 `acceptance_criteria` (`pipeline 통합 test PASS + manual checkpoint sweep PASS`) 정합 강화. 신설 scope 없음 — Phase 8 박제 정신 (4 metric 산출 + graceful fallback) 유지.

## Issues Encountered

- 1차 sweep: 5/5 영상 axisCoordSpace='unavailable' (pole 미검출 false negative) + 5/5 영상 Layer 2 monotonic 위반. → fix B (HoughPoleDetector.detect_with_line) + fix C (setup/hold/release 단독 boundary) 박제.
- 2차 sweep: axisCoordSpace='image_2d' 진입 성공했으나 distance 5/5 null (RTMW keypoints_2d 부재). → fix B' (pole_aligned 3D fallback) 박제.
- 3차 sweep: schema 정합 5/5, axis distance 실값 산출 (B' fallback), 0 server_error. 단, **5/5 영상 모든 phase axis severity='high' 출력 — 도메인적으로 잘못된 결과** (정은지 = 폴스포츠 세계챔피언, severity='high' 기대 X).

## Domain Sanity Issue → Phase 8.5 (NEW) 신설 결정

**문제 박제 (2026-06-09 belle 결정 α)**: 정은지 5/5 영상 모든 phase axis severity='high' 출력.

**원인 박제 (2건 동시 발현)**:

1. **pole_aligned 좌표계 origin 미정의**: in-line fix B' 가 회전만 align (Z+ = 폴 축), translation (origin 박제) 안 함 — 같은 자세도 카메라/폴 위치에 따라 distance 값 상이.
2. **Thresholds 단위 mismatch**: AXIS_PELVIS_DISTANCE_THRESHOLDS = (0.15, 0.30) / AXIS_CHEST_DISTANCE_THRESHOLDS = (0.20, 0.40) 가 image_2d 단위 기준 (Plan 08-02 박제) — pole_aligned 3D 의 sqrt(x²+y²) 단위 (meters in pose space) 와 mismatch.

**Phase 8.5 (axis-metric-redesign, 신설 박제 예정) scope**:

- research: IPSF Code of Points 의 "축 이탈" 채점 항목 + 폴스포츠 도메인 "축 이탈" 정의
- discuss: pole_aligned 좌표계 origin 정의 (폴 축 중심 / pelvis 중심 / shoulder midpoint) + thresholds 단위 재설계
- plan: 도메인 정합 axis distance metric + 5영상 sweep 분포 + IPSF criteria 기반 thresholds 박제

**tilt 데이터 유효성**: shoulder/hip tilt (B' 박제) 는 rotation-only path (arcsin(|Δz|/||Δ||)) 라 의미 있음 (15~58° 산출). Phase 9 force_pattern 추론에서 1차 사용 가능 — axis distance 가 Phase 8.5 후 재설계 시 tilt 는 그대로 보존.

**belle 명시 결정 (2026-06-09)**: α (Phase 8.5 신설) 진행. Phase 8 종료 + Phase 8.5 별 plan 박제.

## Verification Evidence

- **Test count:** phase08 103 PASS (Plan 08-00 18 + Plan 08-01 11 + Plan 08-02 51 + Plan 08-03 신설 23). Pipeline 11 신설 + 35 기존 = 46 PASS. 회귀 0 (phase06 156 + phase07 88 + pipeline 11 + phase08 103 = 358 PASS + 1 skipped).
- **TS strict mode:** `cd app && npx tsc --noEmit` exit 0.
- **SAM validate:** exit 0 (sam build --use-container 은 belle Docker 환경 한정).
- **Lambda env:** FORCE_SIGNALS_LAYER2_ENABLED=1 / GEMINI_MODEL=gemini-2.5-flash / PREFLIGHT_LABEL_GATE_PASSED=0 박제 (file URI 방식, secret CLI leak 방지).
- **Pod env:** 26개 복원 + Phase 8 3개 추가 + uvicorn restart (auth_configured:true, pipeline_loaded:true).
- **Pod phase08 pytest:** 103/103 PASS.
- **3차 sweep:** 정은지 5영상 (sweep_temp/ prefix → SQS race 0), schema 정합 5/5, axis distance 실값 산출 (B' fallback), 0 server_error.
- **REVIEWS Cycle 2 NEW HIGH 차단 grep:** `grep -c "preflight_label_gate_passed=None" pipeline/app.py == 0` (NEW HIGH #1) + `grep -c "'medium'" force_signals.py` Layer 2 except 분기 안 hardcoded 0 (NEW HIGH #2) + `_validate_dict_only_scalars` 본체 변경 0 (NEW HIGH #3, git diff 0).
- **R8 carryover grep:** `grep -c "gemini-2.0-flash-exp" backend/shared/python/sunity_shared/` == 0 안전망 + `grep -c "GEMINI_MODEL" gemini_moment_extractor.py + gemini_technique_recognizer.py >= 2`.

## Pre-existing test failures (out of scope, SCOPE BOUNDARY)

Plan 08-03 와 무관한 pre-existing 실패 — Plan 08-02 박제 5개 유지 (분리 가능):

- `backend/tests/test_pole_detector.py` — collection error (fixtures import). Plan 08-03 와 무관.
- `test_estimated_height_scale_consumer_semantics.py::test_python_consumers_have_semantic_comment_in_sunity_shared` — Plan 08-03 와 무관.
- `test_estimated_height_scale_consumer_semantics.py::test_python_consumers_have_semantic_comment_in_functions_and_runpod` — Plan 08-03 와 무관.
- `test_compare_rtmw_vs_ipsf_recognizer_flag::test_build_recognizer_fallback` — fixture isolation 의심. Plan 08-03 와 무관.
- `test_spike_gemini_moment_smoke::test_runs_when_labeled` — pre-existing. Plan 08-03 와 무관.

## User Setup Required

**Phase 8 종료 후 Phase 8.5 (신설) 진입 전:**

- **belle 운영 작업 (preflight 25-timestamp 라벨링)** — Plan 08-00 박제 preflight_label_template.csv 25 row 채우기 (5영상 × 5 phase). 도메인 시각 라벨링 (belle 판단). ≥80% PASS 시 Lambda env `PREFLIGHT_LABEL_GATE_PASSED=1` 박제 → Layer 1 confidence='medium' 승급 (코드 변경 0).
- **belle/강사 운영 작업 (contact_points.yaml 도메인 검수)** — 5 motion entry 의 ContactPoint + ContactPrimitiveKind 정합 검증.

본 작업은 Phase 8 종료 차단 X (별도 plan 영역).

## Next Phase Readiness

**Phase 8.5 (NEW, axis-metric-redesign) 신설 진입 시그널:**

- research: IPSF Code of Points "축 이탈" 채점 항목 + 폴스포츠 도메인 "축 이탈" 정의 + NotebookLM IPSF CoP 2024-2025 lookup ([[notebook-lm-pole-sports]] 정합)
- discuss: pole_aligned 좌표계 origin 정의 (폴 축 중심 vs pelvis 중심 vs shoulder midpoint) + thresholds 단위 재설계 (meters vs torso_length normalized) + 5영상 sweep 분포 기반 calibration ([[analysis-objectivity-no-human-scores]] 정합 — IPSF + 분포 기반, 사람 점수 라벨링 영구 금지)
- plan: 도메인 정합 axis distance metric + Phase 8 의 compute_axis_deviation pole_aligned fallback path 의 산식 / threshold 재설계

**Phase 9 (ForceDirectionPattern + 실패 후보 3) 진입 시그널 — Phase 8.5 와 평행 가능:**

- Phase 8 박제 4 metric (axis / stability / contact) 입력 source 정합. axis severity 의 도메인 정합성 문제는 Phase 8.5 후 자동 해소되지만, Phase 9 의 force_pattern 추론은 tilt (B' rotation-only path, 유의미한 데이터) + stability (FPS-normalized jerk) + contact (evidence-with-confidence) 위에 1차 진입 가능.
- Phase 8.5 완료 후 Phase 9 가 axis distance 도 정상 입력 source 로 사용.

**Phase 12 (실측 각도 + 키포인트 오버레이) 진입 시그널 — Phase 8.5 와 평행 가능:**

- coordinate_space 별 overlay 분기 (image_2d / pole_aligned) — Phase 8 박제 정합 + Phase 8.5 후 axis overlay 추가.

**No blockers** — Phase 8 종료. Phase 8.5 신설 + Phase 9 평행 진입 가능.

## Known Stubs

본 plan 의 stub scan 결과:

- **preflight_label_template.csv 25 row 미작성** — belle 운영 작업 (도메인 시각 라벨링). Phase 8 종료 차단 X (PREFLIGHT_LABEL_GATE_PASSED env 박제 unset 시 graceful 'low' confidence 박제, Plan 08-02 _layer1_confidence_from_preflight 정합). belle 작업 후 env flip → 'medium' 승급.
- **contact_points.yaml 5 motion entry 도메인 검수** — Plan 08-01 박제 entry 가 IPSF Code of Points + 학원 정의 정합 검증 belle/강사 운영 작업. Phase 8 종료 차단 X (default empty fallback + warning 'motion_unrecognized' graceful path 박제).

**Phase 8 박제 정신 정합 — Phase 8 종료 차단 stub X.**

## Threat Flags

본 plan 의 threat surface scan 결과 신규 surface 0 — backend pipeline wiring + Firestore validator scope 확장 + frontend normalize + in-line sweep fix 박제만. 신규 network endpoint 0 / 신규 auth path 0 / 신규 file access 0 (Plan 08-03 박제 4 T-08-03-* mitigation 정합).

- Firestore scoped validator (`_validate_force_signals_report`): forceSignalsReport path 만 화이트리스트 — 다른 path strict 유지. [[firestore-nested-array-flat]] 영구 보존 → no new threat surface.
- HoughPoleDetector.detect_with_line() (in-line fix B): pure image processing (vertical line midpoint x median) — no new I/O, no PII.
- compute_axis_deviation pole_aligned fallback (in-line fix B'): pure numpy computation — no new I/O, no PII.
- Phase 8.5 신설 결정 = threat surface 변경 0 (별 plan 영역).

## Self-Check: PASSED

- `backend/shared/python/sunity_shared/analysis/force_signals.py` — MODIFIED (Layer 2 활성 + in-line fix B' + in-line fix C).
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` — MODIFIED (GEMINI_MODEL env + key_moments populate).
- `backend/shared/python/sunity_shared/analysis/technique.py` — MODIFIED (TechniqueProfile.key_moments 필드).
- `backend/shared/python/sunity_shared/analysis/pole/detector.py` — MODIFIED (HoughPoleDetector.detect_with_line, in-line fix B).
- `backend/shared/python/sunity_shared/firestore_admin.py` — MODIFIED (scoped validator + complete_analysis kwarg).
- `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` — MODIFIED (DEFAULT_GEMINI_MODEL env, R8 carryover).
- `backend/functions/pipeline/app.py` — MODIFIED (wiring + _preflight_label_gate_passed + singleton + _VideoAnalysisInputs.pole_axis_measurement + _ensure_adapters _POLE_DETECTOR lazy).
- `app/src/lib/userAnalyses.ts` — MODIFIED (forceSignalsReport null-guard).
- `backend/tests/test_pipeline_gemini_integration.py` — MODIFIED (_stub_extract_inputs 5번째 필드).
- `backend/tests/phase06/test_technique_profile_motion_id.py` — MODIFIED (구조적 assertion).
- `backend/tests/phase08/test_compute_phase_boundaries_layer2.py` — FOUND.
- `backend/tests/phase08/test_compute_force_signals_layer2.py` — FOUND.
- `backend/tests/phase08/test_firestore_lockstep.py` — FOUND.
- `backend/tests/phase08/test_gemini_model_env_driven.py` — FOUND.
- `backend/tests/pipeline/__init__.py` / `backend/tests/pipeline/test_pipeline_phase8.py` — FOUND.
- Commits: `fc3b6b7` (Task 1) / `ced1d87` (Task 2) / `c71c75b` (in-line fix B+C) / `f627905` (in-line fix B') — FOUND (`git log --oneline -10 HEAD` 확인).
- 358 PASS + 1 skipped (phase06 156 + phase07 88 + pipeline 11 + phase08 103) — VERIFIED.
- TS strict (`cd app && npx tsc --noEmit`) exit 0 — VERIFIED.

---

*Phase: 08-jerk-jitter*
*Plan: 03*
*Completed: 2026-06-09*
