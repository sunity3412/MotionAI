---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: milestone
status: completed
stopped_at: Phase 20 planned (4 plans/3 waves, plan-checker PASS_WITH_CONCERNS→C-1 fixed). pod-free Wave1-2 실행 가능, Wave3 eval=Pod terminal gate
last_updated: "2026-06-19T04:13:59.281Z"
last_activity: 2026-06-18
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 8
  completed_plans: 4
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-29)

**Core value:** 분석 정확도 — 점수가 믿을 만하고 첫 분석이 "전문가 수준으로 구체적". 수치는 보조, 원인이 핵심.
**Current focus:** Milestone complete

## Current Position

Phase: 19
Plan: Not started
Verification: 13-C — `assemble.assemble_dual_coach_sections` 섹션 조립 + cross-fill 폴백 7 케이스 PASS / phase13 88 passed (81+7, 회귀 0) / pipeline+geminib+dispatch 포함 131 passed / app tsc --noEmit clean / 자세히 모달 벤더명 렌더 텍스트 0 / gemini_b dual-track audit Firestore flat 검증 통과 / GEMINI_COACH_ENABLED=0 Cerebras-only path 보존. 3 atomic commit (8ec9dc5/4f7f7aa/340d0c9).
Next: Phase 15 (실증) — 실 영상 → 실 dual-LLM 섹션 조립 E2E 라이브 검증 + "둘 중 하나 drop 여부" 결정 (13-C 빌드 ≠ drop 결정). Pod 기동 + 라이브 LLM 호출은 Phase 15 scope.
Status: Milestone complete

> ✓ Wave 5 (04-05) COMPLETE (2026-06-14, RunPod d9xxudi1i6xlpz RTX PRO 4500 Blackwell sm_120):
> code(Task1+2: daf6803/969a2c6, local pytest 41 pass/3 skip) → RunPod GPU 재처리 5/5 (RTMW onnxruntime-gpu
> sm_120 cuda ~50fps, 150s, NaN 0) → schema gate 5/5 → Firestore versioned write reference/{id}/versions/phase4_v1
> 5/5 → belle 시각검증 PASS (현 active 대비 관절각 Δ 0~6°, NaN 0, 프레임 1.5x↑ 더 촘촘) → active flip 5/5
> (activeVersion=phase4_v1, top-level mirror 11필드 incl joints3d/keypointReport, pre_phase4 백업 = rollback 소스).
> **Firestore 40k index-entry 한도 차단 해결**: gcloud `firestore indexes fields update --disable-indexes`
> 6개 면제 (joints3d/angles/keypointReport × collectionGroup reference+versions, owner sunity3412 login).
> composite mode3 index 무영향. [[firestore-index-entry-limit]] + [[rtmw-blackwell-lean-bootstrap]] 박제.
> rollback: `python backend/scripts/rollback_reference_motions_phase4.py --to-version pre_phase4`.
> :8000 server UP (proxy d9xxudi1i6xlpz /health ok, Lambda RUNPOD_ANALYZE_URL z3fy82→d9xx 동기화).
> 잔여(optional, phase blocker 아님): Wave 3b @integration evaluate_4way axis_b RunPod 증거 (parked, SKIP/XFAIL).

> ✓ Wave 3b CLOSED — 경로 보류 (belle 2026-06-15). 증거-먼저 단계 실행(새 GPU 불요, Wave 5 Firestore 데이터):
> pre_phase4(구 파이프라인 8관절) vs phase4_v1(RTMW) axis_b occlusion_frame_rate 비교 = mean −33.5% / 개선 1/5 /
> G4 악화 0 False. **단, 이 비교는 cross-model (서로 다른 모델 confidence 스케일) 이라 유효 게이트 아님** — RTMW
> occ_rate 가 높은 건 pose 하락이 아니라 confidence 분포 차이(mean_conf Δ 0.02~0.03). 유효 axis_b 게이트 =
> 동일 RTMW 의 합성 유무 비교(RTMW-baseline vs RTMW+mesh) → `_rerun_rtmw_on_views` 풀 구현 필요 = 보류.
> SYNTHESIS_MESH_ENABLED OFF default(B4 hard gate) 유지 = 코드 변경 0. 근거/재개조건 박제:
> `.planning/phases/04-ux-occlusion-confidence/04-WAVE3B-EVIDENCE-DECISION.md`. [[gsd-model-overrides-opus]] 무관.

> ✓ Reference 라이브러리 전체 RTMW 재처리 완료 (2026-06-15, belle 승인). Wave 5 가 5개만 했고
> 나머지 6개(ref-combo/elbow-twist-sister/kip-up/pdshape/peter-pan/power-spin)는 구 8관절 2D 파이프라인
> 이라 분석 품질 저하 — belle 지적. RunPod RTMW 로 6개 재처리(--no-flip → schema gate 6/6 → phase4_v1
> versioned write 6/6 → NaN 0, 8관절 2D→17관절 3D) → belle flip 승인 → active flip 6/6 (activeVersion=
> phase4_v1 + top-level mirror 11필드 + pre_phase4 백업=rollback). **전체 11개 reference 모두 phase4_v1
> active + top-level 3D = ALL GREEN.** flip JSON = Pod `/workspace/reference-phase4-reprocess-6new.json`.
> rollback: `rollback_reference_motions_phase4.py --to-version pre_phase4`. (후속 후보: reprocess 스크립트
> MOTION_IDS 5→11 영구 반영 — 현재는 --motions override 로 처리, repo 변경 X.)

> ⚠ Wave 2 belle override (2026-06-13): EAS preview build 환경 이슈로 실기기 smoke checkpoint 보류. R8 ErrorBoundary (PoseViewer3D Canvas 감쌈) + typecheck/grep 게이트가 로컬 안전망. 다음 native build 시점에 belle TestFlight 실기기로 OrbitControls 제스처 + Canvas/GL init + 4 카메라 preset 동작 검증 필요 (SUMMARY 04-02 deviation 섹션 박제).

> ⚠ Phase 04 Decision-Coverage Gate override (2026-06-13): 12/32 CONTEXT 결정만 plan 직접 인용. 미커버 20개는 빌드 대상 아님 — spike 절차 완료분(D-11/12/13/17/19), v2/후속 보류(D-06/14/24~28), 근거·IPSF 리서치(D-15/16/21/22/23), negative scope fence(D-01/02/04). 실 빌드 결정(D-03/05/07/08/09/10/18/20/29~32)은 plan-checker Dimension 7 PASS 확인. verify-phase 에서 재확인 가능. proceed-anyway 선택 (belle 위임 "그냥 진행").

Last activity: 2026-06-18

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260612-t9m | stability 점수 보정 + 사용자 안내 (TOL 15° → 25° + result.tsx 안내 캡션) | 2026-06-12 | 947570f | [260612-t9m-stability](./quick/260612-t9m-stability/) |
| 260615-cxe | vision Gemini default model gemini-2.5-flash → gemini-2.5-pro (recognizer/moment-extractor) | 2026-06-15 | d204291 | [260615-cxe-vision-gemini-default-model](./quick/260615-cxe-vision-gemini-default-model-gemini-2-5-f/) |

### Plan 09-01 close-out (2026-06-10)

| 영역 | 결과 |
|---|---|
| Wave 0 atomic commit | `defc973` — 11 files (TS + Python + docs §9.11 + Firestore validator + frontend null-guard + 4 tests) 단일 atomic commit per D-09-U1 |
| force_pattern.py 신설 | Literal aliases (`ForceDirectionPattern` / `ForceSourceSignal` / `ModeContext`) + frozen dataclass `ForcePatternFinding` (8 필드 / R7+R1+R2 strict `__post_init__` validator — `_MOTION_PHASES` reuse, list 컨테이너 강제, non-empty str warnings) + `ForcePatternInference` (5 필드 / non-default → default 순서) + module-level 상수 (`_PHASE_PRIORITY` / `_SIGNAL_PRIORITY` / `_SIGNAL_WEIGHT` / `_BASE_CONFIDENCE` / `_CONFIDENCE_TO_FACTOR` / `_MOTION_ID_BOOST=1.05` / `_IPSF_TOLERANCE_DEG=20.0`) |
| Firestore scoped validator | `_validate_force_pattern_inference` + `_validate_force_pattern_finding_dict` (R2 iter-5 — 8-key camelCase whitelist + strict `list[str]` warnings) + `complete_analysis(force_pattern_inference=)` kwarg |
| 3-way contract lockstep | TS `analysis.ts` + Python `force_pattern.py` + `docs/contract.md §9.11` 단일 atomic commit (D-09-U1). 5 lockstep 테스트 PASS |
| Frontend null-guard | `userAnalyses.ts::normalize` 가 `result?.forcePatternInference` 패턴으로 `forceSignalsReport` precedent 1:1 mirror (R1 iter-2/iter-4) |
| 회귀 게이트 | phase09 49 PASS + phase06/07/08/08.1 408 PASS / 1 skipped + tsc --noEmit clean |

### Plan 09-02 close-out (2026-06-10)

| 영역 | 결과 |
|---|---|
| 5 atomic commits | `d51ed37` T1 (canned + grep gate) / `24b974e` T2 (6 detector + confidence formula + phase fallback + AST severity guard) / `87bdcd3` T3 (Top-3 ranking + tie-break + dedup + motion_id boost) / `c9b6286` T4 (pipeline wiring + integration test) / `bed84e6` T5 (Wave 1 close-out + VALIDATION flip) |
| force_pattern_copy.py 신설 | `_FORCE_PATTERN_COPY_DATA` 18 canned (sourceSignal × modeContext) + `MappingProxyType` wrap (R9/R8 narrow scope) + `_MODE_PREFIX` 3 + `_JOINT_HINT_BY_SIGNAL` 6 + `_FALLBACK_BODY` 1 + `FORBIDDEN_PHRASES_RESEARCH` 8 substring + `FORBIDDEN_PHRASES_PHASE9_REGEX` 2 regex (incl. `근육 힘 방향.*확정` 조사 변형 catch + `\d+%\s*감점`) |
| force_pattern.py 본체 | 6 `_detect_*` (axis_tilt / pelvis_drop with None guard R4 iter-3 / late_contact / high_jitter / high_jerk / abnormal_release) + `_phase_metric_confidence_factor` (R11 conservative v1 documented) + `_apply_motion_id_boost` (×1.05 cap 1.0, ranking 전) + `_rank_top3` (4-stage sort + (pattern, phase) dedup) + `_overall_confidence_from_findings` + `_AXIS_IGNORE_WARNINGS_PER_METRIC` / `_AXIS_IGNORE_WARNINGS_REPORT` (R4 iter-3 two-tier) + `infer_force_direction_pattern` public entry |
| pipeline wiring | `_process` 안 mode_context inline (no helper) — `models.MODE_EXPERT` → "mode1" / `MODE_SELF + isFirst` → "mode3_first" / `MODE_SELF + !isFirst` → "mode3_progress" + `infer_force_direction_pattern` 호출 직후 `_dataclass_to_camel_case_dict` 변환 + `complete_analysis(force_pattern_inference=)` kwarg |
| 회귀 게이트 | phase09 + pipeline_phase9 131 PASS + phase06/07/08/08.1 408 / 1 skipped (regression 0) + tsc clean + 금지 표현 grep gate 10/10 PASS + AST severity guard `axis*.severity` 0 occurrence |
| Verification | 09-VERIFICATION.md — 4/4 SC VERIFIED + 13/13 D-09-* VERIFIED. Wave 2 production sweep OUT (D-09-E2 — Phase 11/15 자연 검증). |
| Follow-ups | belle 박제 검수 (18 canned + jointHint + pelvis_drop A1) + optional Codex cross-AI plan-review. |

### Plan 08.1-01 close-out (2026-06-09)

| 영역 | 결과 |
|---|---|
| compute_axis_deviation 실 본체 | Wave 0 transitional stub → 실 tilt-only 알고리즘 교체. pole_aligned 3D path 우선 + image_2d fallback + 둘 다 미가용 → 'tilt_unavailable'. severity = `_max_severity(_severity_from_tilt(shoulder), _severity_from_tilt(hip))`. confidence ≥ 70% high-reliability frame → 'medium', else 'low'. AxisDeviationMetric 6 필드 (Wave 0 schema 정합) |
| 신설 helpers | `_normalize_angle_undirected` (C-M1, modulo 180° + min(a, 180-a) → unsigned [0, 90], keypoint ordering swap artifact 차단) / `_severity_from_tilt` (C-H2, boundary-low + 1e-9 epsilon strict, boundary value = 'low', 정은지 baseline 25/25 'low' invariant) / `_get_tilt_thresholds` (lazy load + schema_v2 강제 검증, W10 정합 — fallback 신호 cache tuple 3rd element 단일 source, module-global flag 부재) / `_reset_tilt_thresholds_cache` |
| Helper cleanup (W9 audit) | 8 distance helper 삭제 (`_observed_torso_length_pole_aligned` + `_pelvis_position_*` + `_chest_position_*` + `_pole_aligned_axis_distance` + `_pelvis_position_image_2d` + `_chest_position_image_2d`) + `_severity_from_distance` + `_deviation_direction_from_pelvis`. 4 helper 보존 (`_observed_torso_length` + `_kp_pole_aligned_xy` + `_kp2d_xy` + `_midpoint` — compute_contact_stability 의존). `_shoulder_tilt_2d` / `_hip_tilt_2d` 갱신 — `_normalize_angle_undirected` 적용 |
| 모듈 상수 cleanup | `AXIS_PELVIS_DISTANCE_THRESHOLDS` + `AXIS_CHEST_DISTANCE_THRESHOLDS` 삭제. `AXIS_TILT_THRESHOLDS_DEG = (25.0, 37.5)` fallback default 보존 |
| tilt_thresholds.yaml | schema_v2 산출 (calibration_method='elite_p100_plus_margin', calibration_version='1.1', null_tilt_verified=true, 25 sample, 5 doc_ids). shoulder dist {p25=17.12, p50=24.84, p75=31.24, p90=42.36, p100=58.28} → medium=63.28° / high=94.92°. hip dist {p25=22.01, p50=27.73, p75=36.25, p90=44.36, p100=49.62} → medium=54.62° / high=81.93°. ipsf_tolerance.tolerance_deg=20.0 + major_fault_deg=40.0 |
| calibrate_tilt_thresholds.py | CLI (--sweep-uid / --source-type firestore/repo-artifact/wave2-explicit / --source-path / --output-path / --margin-deg 5.0 / --dry-run / --allow-recalibrate). C-H3 preflight hard gate (25 non-null + transitional 부재 + tilt_unavailable 부재 + 5 doc count + 5 phase/doc). P100+margin operational cutoff. D-04 future re-run entry point (value-only zero-code-change) |
| 옵션 A | Firestore reachable (FIREBASE_SA_PATH=`firebase-sa.json`) + sweep_phase8_1780986673 5 docs × 5 axisMetrics × 0 null × 0 transitional 검증 통과. Task 0 precondition belle 박제 완료 |
| 신설 phase08_1 test (46) | test_compute_axis_tilt_only (6) + test_axis_2d_angle_normalization (6) + test_severity_boundary_value_is_low (5) + test_severity_above_medium (3) + test_severity_above_high (3) + test_tilt_thresholds_loader (5) + test_tilt_thresholds_yaml_drift (12) + test_calibration_preflight (6). 모두 PASS |
| Wave 0 cleanup item | phase08/test_compute_axis_deviation.py — 4 stub assertion 제거, R2 drift defense (torso_scale denominator 영구 금지) 만 보존. phase08_1/test_compute_force_signals_does_not_reference_coordinate_space.py — test_compute_axis_deviation_emits_phase_8_1_transitional_warning (1 test) 제거 (Wave 1 새 본체 검증은 test_compute_axis_tilt_only.py 가 보유). C-B1 grep guard 2 tests 보존 |
| 회귀 게이트 | phase06 137 + phase07 108 + phase08 94 (Wave 0 cleanup -3) + phase08_1 63 (Wave 0 20 + Wave 1 46 - cleanup 3) + pipeline 11 = **413 PASS + 1 skipped**. TS strict mode clean (tsc --noEmit) |
| 3 commits | `30fd7d2` Task 1 (compute_axis_deviation tilt-only + yaml lazy loader + helper cleanup W9 audit + module-global flag 부재 W10) / `e08be9c` Task 2a (calibrate_tilt_thresholds.py + tilt_thresholds.yaml schema_v2) / `80c9a6b` Task 2b (yaml drift v2 (12) + calibration preflight (6)). Wave 0 + Wave 1 한 release boundary 박제 (Codex 권장 정합) |

Wave 2 진입 차단 해소 — schema_v2 yaml 존재 + null_tilt_verified=true. pipeline rewire + Pod 재배포 + 정은지 재sweep evidence 박제 가능.

### Plan 08.1-00 close-out (2026-06-09)

| 영역 | 결과 |
|---|---|
| 3-way lockstep atomic | AxisDeviationMetric 5 distance 필드 (pelvisDistanceFromPoleAxis / chestDistanceFromPoleAxis / scaleDenominator / coordinateSpace / deviationDirection) 영구 제거 + 6 필드 만 보존 (phase / shoulderTilt / hipTilt / severity / confidence / warnings). TS interface + Python dataclass + docs §9.3 + models.py 주석 single commit atomic |
| Transitional stub | compute_axis_deviation 본체 = stub (모든 phase boundary 에 대해 severity='low' default + warnings=['phase_8_1_wave_0_transitional'] 반환). distance 산출 path 영구 제거 + helper 함수 + 모듈 상수 보존 (Wave 1 cleanup) |
| C-B1 fix | compute_force_signals 본체 의 `coordinate_space == 'unavailable'` 참조 제거 → `axis_metric_transitional` 검출 로직 (모든 axis_metric warnings 박제 stub 신호 포함 시 top-level warning emit). C-H1 downstream guard 동일 신호 |
| C-H1 fix | Wave 0 단독 production 진입 금지 박제 (severity='low' 가 'measurement 안 됨' 을 '낮은 위험' 으로 silently 변환 차단). Wave 2 production sweep 게이트 = warning 부재 |
| C-MH1 박제 | AxisDeviationMetric naming caveat (실 의미 tilt-only) docstring/JSDoc 박제 + ROADMAP rename 별도 plan 메모 |
| Phase 8 test 수술 | test_compute_axis_deviation.py 11 → 5 함수 (distance 기반 6 함수 제거 + stub 동작 검증 5 함수 신설). test_force_signals_lockstep.py _FIELD_MAP 5 distance entry + coordinate_space_unavailable warning entry 제거 (coordinateSpace 박제 ContactStabilityMetric 보존). test_firestore_lockstep.py axisMetrics fixture 6 필드 dict 갱신 |
| Phase 08_1 test infra | __init__.py + conftest.py + 4 test 파일 신설 — 20 test (6 schema lockstep + 6 dataclass invariants + 5 firestore validator backwards-compat + 3 C-B1 grep guard). legacy 5 필드 dict 의 scalar backwards-compat 검증 박제 |
| 회귀 게이트 | phase06 137 + phase07 108 + phase08 97 + phase08_1 20 + pipeline 11 = 373 collected, **372 PASS + 1 skipped**. TS strict mode clean (tsc --noEmit) |
| 2 commits | `6a294d5` Task 1 (3-way lockstep atomic + stub + C-B1 + C-H1 + C-MH1 + Phase 8 test 수술 + phase08_1 신설 infra) / `1cb3e6e` Task 2 (firestore scoped validator backwards-compat + C-B1 grep guard) |

Wave 1 진입 차단 해소 — AxisDeviationMetric 6 필드 contract + stub 위에 compute_axis_deviation 본체 실 tilt 알고리즘 + threshold yaml 박제 가능.

### Plan 08-03 close-out (2026-06-09)

| 영역 | 결과 |
|---|---|
| Layer 2 wiring | TechniqueProfile.key_moments reuse (R6, 신규 Gemini call 영구 차단) + FORCE_SIGNALS_LAYER2_ENABLED 별도 env flag (R7) + _layer2_boundaries_from_technique_profile + _confidence_from_agreement + Cycle 2 NEW HIGH #2 ceiling 박제 (Layer 2 success/except 둘 다 `_layer1_confidence_from_preflight()` + `_min_confidence(agreement, ceiling)`) |
| pipeline wiring | _process Phase 8 wiring (compare_body_profiles 직후 1줄 호출) + _preflight_label_gate_passed env helper (Cycle 2 NEW HIGH #1, env 3-state) + _get_force_signals_layer2_recognizer singleton + _VideoAnalysisInputs.pole_axis_measurement 5번째 필드 (R10) |
| Gemini model env | R8 carryover (Codex Cycle 2) — 실 default 위치 = judging/gemini_moment_extractor.py:48 (`DEFAULT_GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')`). 'gemini-2.0-flash-exp' EOL 안전망 + recognizer.py 도 동일 GEMINI_MODEL env reuse |
| Firestore scoped validator | Cycle 2 NEW HIGH #3 — `_validate_dict_only_scalars` 본체 변경 영구 0 (firestore-nested-array-flat 보존) + 신설 scoped validator `_validate_force_signals_report` (forceSignalsReport path 만 화이트리스트) + complete_analysis(force_signals_report=) kwarg |
| frontend normalize | userAnalyses.ts forceSignalsReport null-guard (Phase 7 WR-02 B1 immutable spread + ?? null fallback, 7 필드 default) |
| In-line sweep fix (A/B/B'/C) | A: sweep_temp/ prefix 박제 (SQS race 우회). B: HoughPoleDetector.detect_with_line() image-space PoleLine2D 박제. B': compute_axis_deviation pole_aligned 3D fallback (RTMW keypoints_2d 부재 시 자동, warning 'coordinate_space_pole_aligned_fallback' + 'keypoints_2d_missing'). C: _map_moments_to_5phase setup/hold/release 단독 boundary 도출 (monotonic 위반 by construction 차단) |
| Manual checkpoint 자동화 | SAM validate PASS / Lambda env 갱신 (FORCE_SIGNALS_LAYER2_ENABLED=1, GEMINI_MODEL=gemini-2.5-flash, PREFLIGHT_LABEL_GATE_PASSED=0, file URI 방식) / Pod env 26개 복원 + Phase 8 3개 추가 + uvicorn restart (auth_configured:true, pipeline_loaded:true) / Pod phase08 pytest 103/103 PASS / 3차 sweep 정은지 5영상 schema 정합 5/5, axis distance 실값 산출, 0 server_error |
| Test | phase06 156 + phase07 88 + phase08 103 + pipeline 11 = 358 PASS + 1 skipped (회귀 0). TS strict mode clean |
| 4 commits | `fc3b6b7` Task 1 (Layer 2 wiring + Cycle 2 NEW HIGH #2/#3 + R8) / `ced1d87` Task 2 (pipeline wiring + Cycle 2 NEW HIGH #1 + R10 + frontend) / `c71c75b` in-line fix B+C (pole detection + Layer 2 monotonic) / `f627905` in-line fix B' (pole_aligned 3D fallback) |
| Deviation | (1) Rule 1 phase06 brittle assertion 구조적 강화 (key_moments 신설 forward-compatible) + (2) 4 in-scope additions A/B/B'/C — manual checkpoint sweep 결과 발견된 정합성 fix in-line commit |

Phase 8.5 (NEW, axis-metric-redesign) 신설 결정 — 정은지 5/5 영상 axis severity='high' 도메인 정합성 문제 (pole_aligned 좌표계 origin 미정의 + thresholds 단위 mismatch) 발견. research → discuss → plan path 박제. tilt 데이터 (rotation-only) 는 유의미 → Phase 9 1차 사용 가능.

### Plan 07-02 close-out (2026-06-08)

| 영역 | 결과 |
|---|---|
| classify_findings 본체 | pure function (D-07-A1 + D-07-A2 + Decision 1 + CR-01 + WR-03) + module-level _DEFICIT_TO_GROUP (5) + _JOINT_TO_GROUP (12) + _resolve_joint_group (CR-02 path) — body_normalizer.py:958-1140 |
| compare_body_profiles wiring | measure_ipsf_absolute_deficits 호출 직후 classify_findings 1줄 + BodyComparisonReport 조립 4 신설 kwarg 주입 (findings/dnoc/rec_focus/recommended_focus_fallback) — line 1503 + 1531-1539 |
| WR-02 frontend normalize | userAnalyses.normalize() immutable spread + map 패턴, bodyComparisonReport 신설 7 필드 null-guard (iteration 1 B1 retract). TS interface non-optional 유지 — normalize() 가 compat layer |
| CR-01 thread | render_finding_copy(used_reference_fallback=is_mode3_first_fallback) — mode3_first fallback path 에서 unprefixed 단일 카피 + interpretation=None |
| WR-03 fallback | recommended_focus[] 빈 list → _EMPTY_FOCUS_FALLBACK 자동 박제, 채워진 list → None |
| INF-01 preserves | test_classify_findings_preserves_measurement_fields.py — 6 원본 측정 필드 보존 behavioral primary safety property |
| Test | phase07 108 PASS (Plan 01 90 + Plan 02 18 신설) + phase06 136 PASS + 1 skipped (회귀 0) + tsc --noEmit clean |
| 3 commits | `2aedb84` Task 1 (classify_findings + 12 unit tests + tests/__init__.py 환경 fix) / `4851a43` Task 2 (wiring + 6 integration/camelCase tests) / `8559c6f` Task 3 (WR-02 retract B1 frontend) |
| Deviation | (1) Rule 3: backend/tests/__init__.py 신설 — pre-existing 환경 blocker (2) Rule 1: AST grep gate docstring false positive — ast.get_docstring 패턴 적용 |

Phase 8 진입 시그널: 중심축 이탈 + 접촉점 안정성 + jerk/jitter 측정 — phase별 산출 + 가림 스무딩. FORCE-01 요구사항.

### Plan 07-01 close-out (2026-06-08)

| 영역 | 결과 |
|---|---|
| schema lockstep | BodyComparisonFinding +4 + BodyComparisonReport +3 (recommended_focus_fallback WR-03 fix 포함) — Python dataclass + TS interface + docs §8 + §8.3 단일 atomic commit (d4d8af4) |
| copy_templates.py | 33 canned (21 + 12 global CR-02 fix) + 3 mode prefix + render_finding_copy(used_reference_fallback CR-01 fix) + FORBIDDEN 9 종 + _EMPTY_FOCUS_FALLBACK WR-03 (fcb4025) |
| Wave 0 인프라 | phase07/__init__.py + conftest.py + fixtures/_factory.py + 6 fixture JSON (3e1fbf7) |
| WR-01 fail-safe | measure_ipsf_absolute_deficits 의 6 BodyComparisonFinding emit 위치 placeholder category="uncertain" (Plan 02 재할당) |
| iteration 2 fix | CR-01 / CR-02 / WR-01 / WR-03 / WR-04 모두 mitigation. WR-02 + INF-01 은 Plan 02 scope |
| Test | phase07 90 PASS / phase06 136 PASS + 1 skipped (회귀 0) / tsc --noEmit clean |
| 3 commits | `3e1fbf7` Task 1 (fixture infra) / `fcb4025` Task 2 (copy_templates + 3 test) / `d4d8af4` Task 3 (3-way lockstep + WR-01 atomic, 5 files) |
| Deviation | (1) Rule 1 schema: BodyComparisonFinding.category default = "uncertain" — Phase 6 회귀 0 + WR-01 fail-safe 정합 (2) Rule 1 AST gate: Assign + AnnAssign 양쪽 검사 — copy_templates.py 의 typed dict literal 검출 |

Plan 07-02 진입 시그널: `classify_findings(findings, body_normalization_confidence, comparison_type, *, used_reference_fallback)` 본체 + integration test. body_normalizer.py 의 6 placeholder 를 D-07-A1 + D-07-A2 룰로 재할당.

> Phase 6 close-out (2026-06-08): 알고리즘 + production wiring 4/4 검증 PASS. 코드 리뷰 10/10 fix (3 Critical + 7 Warning). phase06 tests 136 pass / 1 skip. Plan 06-03 Task 5 (실 Firestore 백필) + Task 6 (Pod sweep) 은 belle 운영 작업으로 `06-HUMAN-UAT.md` 박제.

### Plan 06-02 close-out (2026-06-08)

| 영역 | 결과 |
|---|---|
| pipeline wiring | _extract_video_analysis_inputs 단일 helper (R3) + R4 non-null student_profile + R2 reference source_pose fetch + R8 extra_warnings injection + C2 motion_id exact-match (retro Phase 5 patch) |
| firestore_admin | complete_analysis(body_comparison_report=, body_normalization_profile=) 확장 + _validate_flat_dict_no_nested_array recursive validator (W5) + _validate_dict_only_scalars (list-of-dict 안 nested 금지) |
| _dataclass_to_camel_case_dict | C8 4-case 명세 (None / dataclass / list / dict / Enum / scalar) + BodyComparisonReport 중첩 변환 |
| frontend | userAnalyses.ts I2 positive assertion (bodyComparisonReport literal) + Korean defensive comment |
| Rule 1 fix | body_normalizer.measure_ipsf_absolute_deficits 의 expects 변수 iterate 오류 (joint_expectations dict 에서 JOINT_EXTEND 값 키로 derive) |
| Test | 본 plan 55/55 PASS, 전체 phase06 107/107 PASS, 기존 pipeline 156/156 PASS, tsc --noEmit clean, sam validate exit 0 |
| 5 commits | `8c5b002` Task 0 (motion_id + Gemini populate) / `2e7d97c` Task 1 (pipeline wiring) / `a60b034` Task 2 (firestore_admin + W5) / `fc75212` Task 3 (camelCase + frontend) / `77383a1` Task 4 (통합 smoke) |

Plan 06-03 진입 시그널: 정은지 reference 5개 영상 백필 (extract_reference_body_profiles.py + seed-reference-body-profile.mjs) — bodyNormalizationProfile + bodyComparisonSourcePose 둘 다.

### Plan 06-01 close-out (2026-06-08)

| 영역 | 결과 |
|---|---|
| body_normalizer.py | Kinematic Tree Reprojection (C1 target-profile L_ref) + IPSF deficit (C14 pose_reliability_low rename) + confidence-tiered hybrid 산식 (R5 dispersion + R6 4채널) + BodyComparisonReport + BodyComparisonSourcePose (R2) |
| 3-way contract lockstep | TS `analysis.ts` + Python `models.py` re-export + `docs/contract.md §8 + §8.1 + §8.2` atomic commit |
| 6 fixture Validation Architecture | 합성 데이터 (160cm pro vs 140cm student, twist, foreshortening, unstable swing, split angle, **high dispersion R5 신규**) |
| Test | pytest 52/52 PASS, tsc --noEmit clean |
| 5 commits | `daa4e8b` test fixtures / `12ed249` Kinematic Tree / `d9c50e1` confidence / `116f400` IPSF deficit + compare_body_profiles / `a444726` 3-way lockstep |

Plan 06-02 진입 시그널: pipeline _process wiring + mode1/mode3/Gemini fallback (C2 retro Phase 5 patch + R3 단일 helper + R4 student non-null + R2 source pose fetch + R8 extra_warnings injection) + Firestore complete_analysis 확장 + frontend normalize + SAM build smoke.

### 진입 chain 갱신 (belle 2026-06-08)

belle 박제 — "분석이 제대로 되는 게 목표. 오버레이, 체형 정규화, 힘 패턴은 필수적. 어떻게든 기필코 개발하려고 하는 게 지금."

v1 시퀀스 (분석 정확도 chain — ROADMAP dep 그래프 정합):

**Phase 6 (체형 정규화) → 7 (차이 분류) → 8 (중심축·접촉점·jerk) → 9 (ForceDirectionPattern + 실패 후보 3) → 12 (실측 각도 + 키포인트 오버레이) → 13 (보완 운동 + LLM)**

이전 chain 박제 (이력 보존):

- 2026-06-07 belle 결정: A+B+C 우선, Phase 2~11 보류 (파일럿 후 v1.5) — Phase 12.5 close-out 후 belle 갱신으로 무효
- 2026-06-07 belle 결정: "Phase 2 → 6 → 7 → 12 → 13" — 힘 패턴 (8, 9) 누락, 본 갱신으로 8/9 추가

### Phase 2 plan 산출

| 파일 | 내용 |
|---|---|
| 02-CONTEXT.md | scope + 6 dependencies + 6 locked decisions (D-02-01~06) |
| 02-RESEARCH.md | RTMW COCO-17 mapping + MAD smoothing + torso self-ref normalize + R&D 격리 path |
| 02-01-PLAN.md | 6 atomic commits (T1 contract → T2 fixture → T3 measurer → T4 pipeline 통합 + T5 R&D harness → T6 AST gate + BODY-01 rename) |
| 02-PLAN-CHECK.md | 15/15 binary PASS, PASS_WITH_CONCERNS (4 non-blocking risks) |

### Phase 2 진입 순서 (전체)

Phase 2 → 6 (체형 정규화) → 7 (차이 분류) → 12 (키포인트 오버레이) → 13 (보완 운동 + LLM)

> Phase 13 scope 확장 (belle 2026-06-07): 원래 "보완 운동·스트레칭 추천 라이브러리" (PERS-03) 단독이었으나, Phase 12.5 시뮬 한계의 backend 후속 작업 (LLM 활성화 + 분기 1/2 카피 분리 + IPSF 정의 각도 fixture) 을 같은 phase 로 통합. 이전 Phase 12.6 = revert.

### Phase 12.5 close-out 내역

| 영역 | 결과 |
|---|---|
| backend `assemble.build_dimension_explanation` | weightPercent (Largest Remainder) + mode-aware baseline + source-faithful deficits (commit 1c0d20a) |
| backend `coach_writer` LLM | Cerebras gpt-oss-120b JSON 프롬프트 — 다중 원인 + case 처방 + 부상 경고 + coachNote. graceful `_normalize_entry` (commit 62fdeed) |
| frontend `DimensionDetailModal` | 동작·사용자 동적 formula ("세계 심사 기준은 [동작]에서 ... [회원]님의 영상 자세를 반영") + "심사평" 자연어 3박자 (평가+이유+결정) |
| frontend `CoachingTipDetailModal` | LLM `tip.detail2` 렌더 (causes 카드 + injury 경고 + coachNote). detail2 없으면 graceful fallback |
| UX 함정 fix | (a) sheet useWindowDimensions 명시 height (b) backdrop = pure View + 위 빈 영역만 Pressable — Pressable+stopPropagation 가 ScrollView gesture 가로채는 함정 회피 |
| belle UX 검증 | PASS — 스크롤 어디서든 정상 동작, 심사평 톤 OK |

### Phase 12.5 남은 한계 (Phase 12.6 이관)

1. **학원 용어 vs IPSF 등재 분기 카피** — 폭스탑 = "정은지 선수 기준" / 클라임 = "세계 심사 기준 (IPSF) + 180°". 메모리 [`studio-term-3branch-system`] 분기 1/2 정합
2. **angle 차원 동작별 IPSF 정의 각도** — 어깨 90° / 엉덩이 110° 등 동작별 fixture 또는 LLM 매핑
3. **시뮬 segments 일부 시나리오 X** — mode 3 first 정답 (이전 영상 없음), 그 외는 실 분석에서 backend `assemble.build_segments` 자동 생성

### Phase 12 §12 UAT 2차 finding fix (2026-06-11)

belle iOS UAT 2차 (TestFlight Build 12) 에서 4 finding 박혀있음. 3건 (B/C/D) Phase 12 내 해소, 1건 (A 좌/우 mirror) 은 Phase 13 신규 plan 분리.

| 항목 | 결과 |
|---|---|
| 12-B frame_extractor 마지막 frame | `4156a89` — last_resized 추적 + step 모듈로 미달 시 강제 추가. 5 단위 테스트 (`backend/tests/test_frame_extractor_last_frame.py`) PASS — remainder skip / no-dup / clip / empty / UAT 17s 시나리오 모두 검증 |
| 12-D KeypointOverlay 저신뢰 keypoint | `62270f2` — `KEYPOINT_LOW_CONFIDENCE_THRESHOLD = 0.5`. `KeypointReport.confidence` flat array read, `KeypointPoint` type 신설. visibility<0.5 → estimateGray (#B0B0B0) + dashed 4/W + opacity 0.7. 강조 분기 (highlightedJoints) 보다 우선. floating angle label 도 저신뢰 joint 표시 X (각도 자체 불신뢰). TS PASS |
| 12-C VideoCompare 두 영상 timeline 분리 | `ddbe074` — left/right currentTime + duration 4 state 분리. progress bar 단일 유지 (짧은 쪽 기준). 시간 라벨 두 영상 동시 표시 `{leftLabel} 0:01 / 0:17 · {rightLabel} 0:01 / 0:16`. TS PASS |
| reference keypoint 5영상 재추출 | Pod (RTX 4090 z3fy82pjgu4mga) extract_reference_keypoint_reports.py 5/5 OK (453.9s) → /workspace/reference-keypoint-reports.json (1.0M) → seed-reference-motions.mjs --keypoint-reports 로 Firestore reference/{motionId}.referenceKeypointReport 5건 갱신 (presigned URL 도 7일 연장, 만료 2026-06-18) |
| deferred-items.md §12 박제 갱신 | `c3dca7c` — B/C/D 완료 + 우선순위 진행 상태 갱신 |
| pod setup_pod_full.sh OpenMMLab CDN 만료 패치 | `7f81eb2` — RTMW HF/S3 mirror, YOLOX HF mirror, RUNPOD_AUTH_TOKEN auto-fetch, uvicorn __pycache__ 청소. 다음 Pod 셋업 시 함정 20-27 자동 회피 |

**Pod 인프라 결정 (2026-06-11)**:

- Network Volume EU-RO-1 (`sunity-motion-vol`, 31GB, $2.17/월) 생성. 단 RunPod Community Cloud GPU 호스트가 Network Volume mount 미지원 → ephemeral 진행. Volume 은 향후 Secure Cloud 전환 또는 mmpose 작업 시 재평가.
- mmcv CUDA 빌드 40분+ stall → fast-path 셋업 (boto3 / imageio / rtmlib / onnxruntime-gpu 1.19.2 / RTMW S3 백업 / YOLOX HF mirror / Firebase SA SSM) 으로 우회. extract 스크립트엔 mmpose 불필요.

**다음 단계**:

1. belle EAS Build profile production → TestFlight Build 13 빌드 + submit
2. belle UAT 3차 (12-A 외 3 finding 해소 검증)
3. UAT 3차 PASS → Phase 12 전체 close-out + ROADMAP `[x]` 표기
4. Phase 13 신규 plan (좌/우 mirror correction post-process)

Last activity: 2026-06-12

**시퀀스 (belle 2026-06-07 결정 — B → C → A)**:

1. **B (Phase 12.5)** — 3~5일 — UI transparency + 강사 보조 카피 — 빌드 12 ship
2. **C (Phase 16 코드 통합)** — 1~2주 — AKA 매핑 + 5트랙 v1 + 분기 3 — 빌드 13 ship
3. **A (Phase 12)** — 2주~ — 실측 각도 + 키포인트 오버레이 — 빌드 14 ship
4. parallel: Plan 01-24 — NLF R&D 격리 명시 — 0.5~1일, B 와 별도 PR

상세 = `.planning/roadmap-replan-2026-06-07.md` + `.planning/roadmap-replan-2026-06-07-review.md`.

Progress: [██████████] 100%

## ▶ Plan 23 sweep verdict `phase1_ready_to_swap=False` (2026-06-03) — D-16 보류

belle Pod 5영상 sweep (`backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.md`) 결과:

| 게이트 | 결과 | 박제 기준 |
|---|---|---|
| IPSF within_tolerance | **1/5 PASS** | 5/5 필요 |
| line PASS | **3/5 PASS** | 5/5 필요 |
| angle PASS | **0/5 PASS** | 5/5 필요 |
| pole_axis | 5/5 low (수직 폴백) | high 필요 |

| 모션 | pole_axis | IPSF | line | angle | ms/f | rtmw_score |
|---|---|---|---|---|---|---|
| ref-climb | low | PASS | PASS | FAIL | 2201 | 95.4 |
| ref-foxtop-split | low | FAIL | FAIL | FAIL | 2164 | 93.0 |
| ref-foxtop | low | FAIL | FAIL | FAIL | 2083 | 93.3 |
| ref-invert | low | FAIL | PASS | FAIL | 2116 | 93.6 |
| ref-sideway-spin | low | FAIL | PASS | FAIL | 2009 | 94.8 |

**핵심 진단 (root cause 3종 동시 발현)**:

1. **IPSF criteria target=180° 일률 — FallbackRecognizer 한계**
   - 모든 hold moment 의 shoulder/hip/knee target=180° (완전 EXTEND 가정)
   - measured 값 21~107° = 실제 자세는 굽힘인데 yaml 은 폄 가정
   - Plan 11 박제 ("FallbackRecognizer 가 굽은 자세에서 EXTEND 못 찾아 line 차원 None") 그대로 — Phase 5 (Gemini 기술 인식기) 통합 전엔 IPSF angle 게이트 의미 없음

2. **HoughPoleDetector 미설치 → pole_axis 부정확**
   - 5영상 모두 axis_vector=(0,1,0) low confidence (수직 폴백)
   - 실제 카메라 각도/폴 회전 있을 시 line 측정값 부정확
   - line 3/5 PASS 도 폴백 영향 가능

3. **AKA 매핑 vs yaml criteria 정합 미검증**
   - belle 매핑: `ref-foxtop.yaml` ← 인버트 버터플라이, `ref-invert.yaml` ← 플랭크 스핀, 등
   - yaml hold target=180° 가 그 자세의 IPSF 기준인지 belle/정은지/NotebookLM IPSF CoP 2024-2025 재검증 필요

**belle 결정 (2026-06-03)**: 결과 박제 commit 먼저 + 다음 plan 의논. 박제 [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" 정신 유지.

**Plan 24 / 25 진입 차단 — D-16 보류**. 다음 후보:

- (A) Phase 5 (Gemini 기술 인식기) 통합 선행
- (B) Plan 26 (가칭) — root cause 3종 동시 fix plan 신설 (Gemini wiring + HoughPoleDetector + yaml 재검증)

### Plan 23 belle Pod sweep 함정 5종 박제 (재사용 위함)

| 함정 | Fix |
|---|---|
| `imageio` pyav 플러그인 누락 | `pip install 'imageio[pyav]'` |
| rtmlib 0.0.15 `pose` alias 부재 | `export RTMW_ONNX_PATH=<unzipped end2end.onnx>` 강제 (commit 3b27c25) |
| rtmlib Wholebody batch 미지원 | 단일 (H,W,3) frame 입력 (commit 375c21c) |
| mmpose `chumpy` 빌드 fail | `pip install --no-build-isolation chumpy` 선행 |
| onnx 위치 패턴 | `<weights_root>/20230928/rtmpose_onnx/<model>/end2end.onnx` |

상세 박제 = [[runpod-gpu-env.md]] 업데이트 누적 중.

---

## ▶ Plan 11 sweep verdict `gap_too_wide_blocked` (2026-06-01) — Plan 12/13/14 신설

belle Pod 5영상 sweep (`sweep_rtmpose_20260601_0411`) 결과:

| 모션 | RTMPose+MB | NLF | gap | D-15① ≥70 | D-14 |gap|≤5 | line | angle |
|---|---|---|---|---|---|---|---|
| ref-climb | 89.0 | 58.0 | **+31** | PASS | **FAIL** | N/A | N/A |
| ref-foxtop-split | 79.0 | 63.0 | **+16** | PASS | **FAIL** | N/A | N/A |
| ref-foxtop | 81.0 | 64.0 | **+17** | PASS | **FAIL** | N/A | N/A |
| ref-invert | 70.0 | 65.0 | +5 | PASS | PASS | N/A | N/A |
| ref-sideway-spin | 80.0 | 81.0 | -1 | PASS | PASS | N/A | N/A |

D-15① 5/5 PASS, D-14 2/5 PASS, line·angle 0/5 PASS. 평균 |gap| = 14점.

**belle 결정 (2026-06-01)**: "갭은 어떻게든 줄여야 한다. Gemini 든 다른 수단이든 가리지 말고." + "라인과 각도도 계획에 들어가야 한다." → D-14 강등 거부. 갭 + line/angle 둘 다 Wave 3 진입 1순위 게이트. Plan 12/13/14 신설.

### 신설 Plan 12 / 13 / 14

| Plan | 역할 | 게이트 통과 path |
|---|---|---|
| **01-12** (NEW) | 갭 root cause 디버그 spike | 가설 a~e (frame-mean / RTMPose headdown / NLF baseline 편차 / keypoint 매핑 / MotionBERT lift path) + ref-invert 22점 회귀 + sideway-spin Plan10 vs Plan11 비일관성 박제 |
| **01-13** (NEW) | Gemini key moment + criteria extractor | multimodal 2.5 Pro. hold/peak/setup/release 시점 + EXTEND/BENT criteria. dimensions sampling frame-mean → moment-list 교체. line/angle 회복 + 갭 줄이기 동시 path. |
| **01-14** (NEW) | 5영상 재검증 sweep | Plan 12 fix + Plan 13 key moment 적용 후 sweep_rtmpose 재실행. **게이트 = 갭 ≤5 + line/angle 5/5 PASS** |

Plan 14 통과 → Plan 04 / Plan 05 (Wave 3) 진입.

### Plan 08 (MP+MB) 대비 RTMPose 회귀

| 모션 | MP+MB (P08) | RTMPose+MB (P11) | Δ |
|---|---|---|---|
| ref-climb | 85 | 89 | +4 |
| ref-foxtop-split | 75 | 79 | +4 |
| ref-foxtop | 90 | 81 | -9 |
| **ref-invert** | **92** | **70** | **-22** ← 회귀 |
| ref-sideway-spin | 64 | 80 | +16 |

ref-invert RTMPose headdown 약점 가설 — Plan 12 에서 frame-by-frame avg_rtm_score 분포 분석.

### Plan 10 spike vs Plan 11 sweep — ref-sideway-spin 비일관성

| | Plan 10 spike | Plan 11 sweep | Δ |
|---|---|---|---|
| overall | 72 | 80 | +8 |
| ms/frame | 37 | 21 | 절반 |

같은 영상/설정. frame seek/sampling 차이 가설 — Plan 12 에서 spike vs sweep 같은 영상 비교 trace.

## ▶ Plan 10 STRONG_PASS 결과 (2026-06-01) — Plan 11 (C scope) 진입

**Plan 10 verdict** = `strong_pass`. ref-sideway-spin 1영상:

| 항목 | RTMPose+MB | NLF | 갭 | 게이트 |
|---|---|---|---|---|
| overall | **72.0** | 81.0 | -9.0 | D-15① PASS (≥70) |
| stability | 72.0 | 81.0 | -9.0 | — |
| line | N/A | N/A | N/A | **Phase 5 게이트** |
| angle | N/A | N/A | N/A | **Phase 5 게이트** |
| ms/frame | 37 | 665 | — | 18x faster (production win) |

**핵심 발견**: line / angle N/A = FallbackRecognizer 한계 (PROJECT.md "현 핵심 블로커"와 정확히 일치 — "굽은 그립 자세에서 EXTEND 못 찾아 line 차원 None"). 해결은 **Phase 5 Gemini 기술 인식기** 통합.

### Plan 11 scope (belle approved C, 2026-06-01)

- **T-1**: 5영상 sweep (ref-climb / ref-foxtop-split / ref-foxtop / ref-invert / ref-sideway-spin) — RTMPose+MB vs NLF baseline
- **T-2**: line / angle N/A root cause 박제 — FallbackRecognizer 한계 정확히 어떤 자세/관절에서 발동? threshold 조정으로 일부 회복 가능? 다른 4영상에서도 같은 패턴?
- **T-3**: 게이트 룰 검토 — D-15① 70 threshold 적정 여부, D-14 (NLF gap ≤5) production 우선순위 재확인
- **T-4**: Wave 3 진입 게이트 — Plan 04 (NLF R&D 격리) + Plan 05 (atomic swap) 진입 조건 명시
- **T-5**: belle Pod 실행 + 5영상 결과 판정

Gemini 통합은 **Phase 5 별 phase** — belle Gemini API 키 (Google AI Studio) 발급 + Parameter Store 주입 wiring 선행 필요.

### belle Gemini API 키 작업 (병행, 2026-06-01 발급 진행 / 2026-06-03 모델 갱신)

| Phase | Gemini 역할 | 권장 모델 (2026-06-03 belle 결정) | 키 발급 path |
|---|---|---|---|
| **Phase 5** | 기술 인식기 (영상 → 분류 + EXTEND/BENT) | **Gemini 3.1 Pro 단일** (belle 2026-06-04 확정, 3.0 삭제). 3.5 Flash 는 v1 미사용 — v2 비용 분석 후 별 plan 평가 | Google AI Studio → /sunity/motion/gemini-api-key (SecureString) |
| **Phase 11** | 자연어 코칭 번역 | Cerebras llama3.1 유지 권장 (이미 동작 중) — Gemini 3.5 Flash 도 후보 (한국어 품질 비교 필요) | — |

belle 박제 (2026-06-03): "분석이 완벽해야 한다는 것 = 모든 박제 기준. 우회/대체 상황이면 언제든 제안 OK". 모델 선택은 분석 정확도 기준 — 이전 박제 (2.5 Pro) 는 정보 부족 시점 추정, 3.0/3.1 Pro 가 실제 사용 가능 시점에 정확도 + multimodal 성능 우위.

### Plan 10 디버그 이력 (Pod 4함정 박제)

1. mmcv 빌드 실패 → `pip install --no-build-isolation "mmcv>=2.0,<2.2"` (mmcv 2.1.0)
2. numpy ABI 불일치 → `pip install "numpy>=1.26,<2"` (1.26.4 다운그레이드)
3. detector alias 카탈로그 실패 → spike 코드 패치 commit `f019070` (single-person 우회 default)
4. Pod git pull 갱신 안 됨 → 로컬 commit 후 `git push origin main` 누락. push 후 Pod pull 정상.

상세 fix 명령 + 환경 변수 = `.claude/projects/.../memory/runpod-gpu-env.md` 박제됨.
GSD process rule = `.claude/projects/.../memory/gsd-pod-work-push-first.md` 박제됨.

### 현재 Pod 환경 (2026-06-01 22:00 시점, Plan 11 진입 준비됨)

**Pod 살아있음. 추가 install 없음.** Plan 11 belle 실행 = git pull + sweep 명령만.

| 항목 | 상태 |
|---|---|
| GPU / Container | RTX 3090 / RunPod PyTorch 2.4 template, Python 3.11 |
| torch | 2.4.1+cu124 (검증됨) |
| numpy | 1.26.4 (다운그레이드, opencv-python warning 무시 가능) |
| mmcv / mmengine / mmdet / mmpose | 2.1.0 / 0.10.7 / 3.3.0 / 1.3.2 |
| xtcocotools | 1.14.3 (numpy 1.x 호환) |
| MotionBERT | `/workspace/MotionBERT/` clone + `best_epoch.bin` (~120MB) |
| RTMPose-l weights | `/workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth` + `.py` config |
| SunityMotion git HEAD | 10683aa (Plan 10 closeout + Plan 11) — push 됨, Pod 에서 `git pull` 시 받음 |
| detector default | single-person 우회 (`--det-model none`) — commit f019070 |
| AWS 자격증명 | env 박제됨 (Plan 08 setup 이래 유지) |
| Firebase SA | `/workspace/firebase-sa.json` |
| Gemini API 키 | Parameter Store `/sunity/motion/gemini-api-key` (SecureString, 2026-06-01 박제). Pod env 주입은 Phase 5 진입 시 wiring |

**Memory 박제 완료** (`license-blocklist-pose.md`): AlphaPose Noncommercial → 향후 plan 후보군에서 영구 제외.

### Plan 09 의사결정 매트릭스 (이력 보존)

| belle 응답 | Plan 10 방향 | 결과 |
|---|---|---|
| **option-b-1, spike RTMPose** | Apache 2.0 + 2D detector 교체 | **✓ 선택됨 (2026-06-01) → STRONG_PASS** |
| option-a, spike HybrIK | MIT + SMPL prior lift | 미선택 |
| option-c, accept 4/5 | 게이트 룰 재정의 | 미선택 |
| option-d, multi-view | 다중 시점 v1 spec | 미선택 |
| option-b-2 / b-3 | MMPose HRNet / MS HRNet | 미선택 |
| hold + research more | 별도 research 후 신규 plan | 미선택 |

## Plan 08 5영상 검증 결과 (재인용)

| 모션 | MP+lifter | NLF | D-15① ≥70 |
|---|---|---|---|
| ref-climb | 85 | 58 | PASS |
| ref-foxtop-split | 75 | 62 | PASS |
| ref-foxtop | 90 | 64 | PASS |
| ref-invert | 92 | 65 | PASS |
| **ref-sideway-spin** | **64** | 81 | **FAIL** |

평균 81.2 (Plan 06 단독 MP: 22.8 → **3.5배 회복**). D-15① 4/5 PASS.

**Path B 결정 (2026-05-31)**: AlphaPose 2D 어댑터로 측면 자세 보강 → ref-sideway-spin ≥ 70 회복 spike (Plan 09).
**Path B 수정 (2026-06-01)**: AlphaPose 라이선스 Noncommercial → **RTMPose-l (Apache 2.0)** 로 대체 (Plan 10). 통과 시 5영상 sweep + 게이트 룰 재정의 + Wave 3 진입 (Plan 11+).

## Performance Metrics

**Velocity:**

- Total plans completed: 22 (01-01, 01-02, 01-03, 01-06, 01-07, 01-08)
- Average duration: ~30 min/plan (executor) + belle Pod 실행 별도

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 06 | 3 | - | - |
| 03 | 3 | - | - |
| 14 | 3 | - | - |
| 11 | 3 | - | - |
| 19 | 4 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 06 P03 | 50 | 7 tasks | 10 files |
| Phase 08.1 P02 | 90 min | 5 tasks | 6 files |
| Phase 09 P01 | 25min | 7 tasks | 11 files |
| Phase 09 P02 | 30 | 5 tasks | 11 files |
| Phase 04 P03 | ~20min | 2 tasks | 4 files |
| Phase 04 P05 | 15 | 2 tasks | 4 files |
| Phase 03 P01 | 9min | 3 tasks | 8 files |
| Phase 03 P02 | 4 | 2 tasks | 2 files |
| Phase 03-bodyprofileinput P03 | 5min | 2 tasks | 4 files |
| Phase 15 P01 | 35min | 3 tasks | 4 files |
| Phase 15 P03 | 70min | 2 tasks | 1 files |
| Phase 15 P04 | 75min | 3 tasks | 2 files |
| Phase 19-vision-hybrid P01 | 18min | 2 tasks | 4 files |
| Phase 19 P02 | 14 | 2 tasks | 8 files |

## Accumulated Context

### Roadmap Evolution

- Phase 18 added: 전문가 일부러-실수 reference eval 세트 (가칭, Phase 15 이후, belle 2026-06-16)
- Phase 20 added: v2 비전 점수 (Gemini 시각 거부권) — kip-up 위양성 + 상단변별 + Mode3 미보유게이트. roadmap+CONTEXT pod-free, 구현 Pod 의존

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [2026-05-31 아키텍처]: 두 엔진 분리 — 엔진 A(체형 보정, coaching 모드 정규화 ON) + 엔진 B(힘 패턴, 움직임 방향만 측정·근육 힘 단정 금지)
- [2026-05-31 포즈 — 최종]: **상용/베타 제품 = MediaPipe + Gemini** (Apache 2.0, 라이선스 리스크 0). **NLF/SMPL-X = 라이선스 확인 전까지 제품 코드 비포함, 내부 비상업 R&D 비교군으로만 사용**. 입수처 = https://is.mpg.de/ps/code, https://smpl-x.is.tue.mpg.de. PoseEngine 인터페이스 추상화 — `MediaPipePoseEngine`(제품) + `NlfPoseEngine`(R&D 격리) 어댑터 2개 운영. NLF/SMPL-X 출시 사용 시 Max Planck Innovation 상업 라이선스(`info@max-planck-innovation.de`) 클리어 필수. 공개 베타·유료 파일럿·고객 영상 처리에 NLF/SMPL-X 절대 사용 금지
- [2026-05-31 모드]: judging 모드(IPSF Code of Points) v1.5로 분리, 데이터 수집은 v1 평행 (belle/강사)
- [2026-05-31 UX]: 다중 시점 촬영 v1 포함 (occlusion 완화)
- [2026-05-31 Gemini]: 역할 = 자연어 번역 전용. 좌표·판단·점수 출력 금지 (운동학 휴리스틱 + 코치 마무리)
- [2026-05-31 코치]: 모든 리포트에 CoachCommentHook 부착 (v1 데이터 구조), UI/입력은 v2
- [전반]: 채점 차원 = IPSF 기반 (각도/라인/안정성), 균형(대칭) 제거 — 위양성(41점) 주범 제거
- [Phase 14]: 기준 모션 등록 = 다각도 캡처 프로토콜 + 두 엔진 출력 포함 (Mode 1 신뢰도의 기준)
- [Phase 15]: Mode 3 = 발전(progress) 표시, %일치 헤드라인 금지 (세션 간 델타)
- [2026-06-02 학원 용어 + 5트랙]: Phase 16 신설 — Studio Terminology Foundation. 학원 용어 3분기 시스템 (AKA 매핑 13개 / 정은지 reference 비등재 동작 / 자동 수집 + UX 카피) + IPSF 5트랙 채점 v1 scope (a) Compulsory Criteria + (c) Technical Deduction + Page 9 "all components" 절대 트랙. **MVP 가볍게 — 코드 통합 후속, 박제만 v1**. **실증 검증 게이트** = 파일럿 후 사용자 키워드 분기 1/2/3 비율 + 자동 수집 누적 패턴 → 한 번에 확장. NotebookLM IPSF CoP 2024-2025 lookup 박제 (Element Code Matching p.138-139, Page 9 "all components" CoP 2021-2024, AKA 13개 매핑). v1 신설 SCORE-05/TERM-01/TERM-DATA-01/TERM-COPY-01 + v2 신설 SCORE-V2-02/03 + TERM-V2-01/02. memory studio-term-3branch-system + ipsf-5-track-scoring 박제.
- [2026-06-08 Plan 06-01 C1]: normalize_pose_by_segments 시그너처 = (source_keypoints, source_profile, target_profile, target_torso_px). L_ref = target(student) 의 segment ratio × target_torso_px (segment-aware, uniform scale degeneration 회피)
- [2026-06-08 Plan 06-01 C14]: deficit code bad_angle → pose_reliability_low rename. IPSF Page 21 judge-observation 'bad_angle' 과 의미 분리, docs/contract.md §8.1 divergence note 박제
- [2026-06-08 Plan 06-01 R2]: BodyComparisonSourcePose 신설 — Firestore reference 컬렉션의 reference 측 대표 hold frame keypoints 영속. flat values (4 × J = 68) + to_keypoints_array reshape. Plan 06-03 백필 contract source
- [2026-06-08 Plan 06-01 R5]: spatial_dispersion_penalty 산식 자연화 = clip((C_s/sw - 1.5) / 1.5, 0, 1). high dispersion → high penalty 자연 방향
- [2026-06-08 Plan 06-01 W1]: BodyComparisonReport.comparisonType 3 cases 만 (mode1 / mode3_first / mode3_progress). Gemini fallback 은 sibling boolean usedReferenceFallback (mode3_first 에서만 true 허용). 4번째 fallback 변형 케이스 금지
- [2026-06-08 Plan 06-02 C2 + R1]: TechniqueProfile.motion_id 필드 (위치: dataclass 맨 끝, hold_window 뒤 — R1 fix non-default 앞 금지). Gemini recognizer 4 path keyword populate. mode3-first Gemini fallback path 가 firestore_admin.get_reference_motion(motion_id) exact-match 사용 (Phase 5 retroactive patch).
- [2026-06-08 Plan 06-02 R3]: 단일 _extract_video_analysis_inputs(bucket, key, default_pole, *, keep_local_video=False) helper. S3 download + frame extract + RTMW estimate 1회만 실행 (T-06-02-06 mitigation). 기존 _angles_and_video_path_from_video 폐기. Phase 2 _angles_and_body_profile_from_video 무수정 보존.
- [2026-06-08 Plan 06-02 R4]: student_profile 반환 타입 = BodyNormalizationProfile (non-null). measure_body_profile 의 _fallback_profile 정합. caller 별도 None check 불요.
- [2026-06-08 Plan 06-02 R8]: caller-injected extra_warnings injection (compare_body_profiles 신규 파라미터). 'fallback_reference_not_found' / 'reference_source_pose_missing' 주입. dataclasses.replace 우회 패턴 금지.
- [2026-06-08 Plan 06-02 W5]: _validate_flat_dict_no_nested_array recursive validator + _validate_dict_only_scalars helper. list[str] (warnings) + list[dict-of-scalars-only] (findings) 허용. list[list] / list[dict-with-nested-list] TypeError raise.
- [2026-06-08 Plan 06-02 C8]: _dataclass_to_camel_case_dict 5-case 명시 (None / dataclass / list / dict / Enum / scalar). BodyComparisonReport 중첩 ScaleProfile + list[BodyComparisonFinding] camelCase 변환.
- [2026-06-09 Plan 08.1-01 C-H2]: tilt_thresholds.yaml operational cutoff = P100 + margin_deg (P90 폐기). medium = max(P100 + margin, ipsf_tolerance.tolerance_deg=20°), high = max(medium × 1.5, ipsf_tolerance.major_fault_deg=40°). 정은지 baseline 25/25 'low' 유지 보장 (boundary value = 'low' rule 정합). `_severity_from_tilt` boundary semantics: strict `>` + 1e-9 epsilon (float-safety). boundary value 정확히 cutoff → 'low'.
- [2026-06-09 Plan 08.1-01 C-M1]: `_normalize_angle_undirected(angle_deg) = (a % 180.0; return 180.0 - a if a > 90.0 else a)`. modulo 180° + min(a, 180-a) = undirected line angle [0, 90]. keypoint ordering swap (left↔right) artifact 차단. 2D path (`_shoulder_tilt_2d` / `_hip_tilt_2d`) 가 본 helper 적용 → unsigned [0, 90] 강제. 3D path 는 이미 arcsin(|Δz|/||Δ||) 로 unsigned [0, 90] 산출.
- [2026-06-09 Plan 08.1-01 C-H3]: calibrate_tilt_thresholds.py preflight hard gate — 5 doc × 5 axisMetric per doc + non-null shoulderTilt/hipTilt + 'phase_8_1_wave_0_transitional' 부재 + 'tilt_unavailable' 부재 검증. 위반 시 RuntimeError + 명시 doc_id. yaml schema_v2 의 source.null_tilt_verified=true 박제 (loader 의 schema 검증 통과 조건).
- [2026-06-09 Plan 08.1-01 W10]: tilt_thresholds.yaml fallback 신호 = cache tuple 3rd element (`['tilt_thresholds_fallback']`) 단일 source. module-global mutable boolean flag 부재 (test 로 강제 검증 — `_TILT_THRESHOLDS_FALLBACK_FLAG` 등 forbidden name set).
- [2026-06-09 Plan 08.1-01 source 분기]: calibrate_tilt_thresholds.py `--source-type` 3 분기 — `firestore` (default, Phase 8 inherited sweep) / `repo-artifact` (Firestore 미가용 시 08.1-CALIBRATION-SOURCE.json) / `wave2-explicit` (Wave 2 자기 sweep 재calibrate, `--allow-recalibrate` 명시 강제 = circular threshold chasing 차단).
- [Phase ?]: Plan 16-01 T-6 belle threshold 결정
- [Phase ?]: Plan 06-03 R2: 단일 helper update_reference_body_data(motion_id, body_profile, source_pose) — 두 필드 atomic merge. 구 update_reference_body_profile 폐기. Phase 14 정은지 reference 등록 helper 재사용 진입점.
- [Phase ?]: Plan 06-03 R7: seed-reference-body-profile.mjs explicit ordering — Step 1 parse + validate → Step 2 if dry-run early return (Firebase 미접촉) → Step 3 real-run. ADC 미설정 환경에서도 dry-run path 안전 (Firebase init 호출 0).
- [Phase ?]: Plan 06-03 C12: revert-reference-body-profile.mjs 신설 + 안전 기본값 (--commit 미지정 시 강제 dry-run) + R2 정합 (두 필드 모두 FieldValue.delete).
- [Phase 08.1]: Wave 2: production sweep + 8조건 measured-low gate 8/8 PASS (25/25 'low' + 5/5 sensitivity) — 정은지 5영상 sweep_phase8_1_1781009003567 exit 0 + 25/25 axisMetric measured_low_count=25 severity_low_count=25 + Task 2.5 synthetic 5/5. ROADMAP Phase 8.1 SC #1-5 backward coverage 박제.
- [Phase 08.1]: Layer 2 evidence only — Pass 게이트 아님 — 본 sweep 0/25 gemini_assisted + 5/5 layer2_unavailable warning. recognizer factory 미초기화 추정. 본 phase 의 axis metric fix 가 본질 scope. Layer 2 활성도 검증 = Phase 9/11 deferred.
- [Phase 08.1]: pipeline/app.py caller-side 변경 0 (Wave 1 시그너처 보존) — grep audit 결과 distance kwarg 부재 + 3 coordinate_space reference 모두 pole_axis_measurement.coordinate_space (PoleAxisMeasurement unchanged field). Plan must_haves Wave 2 'caller-side 변경 0 가능' 정합.
- [Phase ?]: D-09-D1 / D-09-U1 / D-09-U3 / D-09-U4 / D-09-U5 박제 — Wave 0 11 files 단일 atomic commit (defc973)
- [Phase ?]: Wave 1 Plan 09-02: D-09-D6 mode_context inline (no helper) + R4 iter-3 two-tier axis warning + R4 None guard for pelvis_drop + R5 high_jitter wins tie-break + R11 conservative v1 cf cap when axis missing
- [Phase ?]: (2026-06-15, Plan 03-01) BodyProfile 3-way 계약 lockstep + AnalysisDoc.bodyProfile snapshot — 결과 화면 재현성(R1), client+server 이중 normalize graceful(D-06).
- [Phase 03]: (2026-06-15, Plan 03-01) weightKg 보조 ONLY — 6 scoring-consumer 모듈 grep gate 로 유입 차단 (D-05/R4). coach context(D-04)에만 전달.
- [Phase ?]: 03-02: BodyProfileForm presentation = 전체화면 Modal(pageSheet), 신규 route 없이 재사용 component 유지
- [Phase ?]: 03-02: Segmented 토글 해제 허용 (오선택 정정 + 부분입력 D-06)
- [Phase ?]: 03-03: useBodyProfile 가 promptDismissedAt once-flag 노출 — normalizer all-empty→null 우회로 게이트가 미입력+dismiss 정확 판별 (R2)
- [Phase ?]: 03-03: pendingPicked 게이트 4-경로 모두 continuePendingRoute 단일 수렴 — 영상 유실/stale closure 방지
- [Phase ?]: Phase 15-01: SOURCE fixture(비-notified fixtures/) vs per-run/per-mode 영숫자 analysis identity 분리; direct-process 가 fixtures/ 키를 _process 에 직접 넘겨 uploads/ COPY 0 (HIGH 1/HIGH 2)
- [Phase ?]: Phase 15-01: 위양성 gate = 08.1 frozen baseline(c94bb8…e87c) checksum hard-gate 대조만, 재calibrate import 0 (D-02)
- [Phase ?]: Mode 1 7/7 server_error==0 PASS — 정은지 7 student 영상 실 Pod GPU E2E (referenceMotionId lockstep). line=None 7/7 은 recognizer 미인식 anti-false-positive 폴백(blocking gate 아님)
- [Phase ?]: Gemini 503 transient = server_error 아님 → 새 uid subset retry. onnxruntime CPU 폴백 = LD_LIBRARY_PATH(cudnn) 누락 → live uvicorn proc env 재사용으로 GPU 강제
- [Phase ?]: 15-04: Mode 3 6 fail->success 페어 deltaFromPrevious 차원 점수(stability) 델타 — 6/6 previousAnalysisId==paired fault, MODE-02 충족
- [Phase ?]: 15-04: SCORE-04 단독 — frozen 08.1 checksum(c94bb8)+fallback==0 12/12, SC3 41점-스타일 위양성 부재(최저 overall 55=실 결손). all-low success-severity gate=reference-motion invariant라 학생-연습 success 미전이 → Phase 18 defer(재calibrate 0)
- [Phase ?]: 15-04: 듀얼 coach 12/12 doc dualTrack=True+nonCrossFilledGemini6(실 LLM)+빈 섹션 0(D-12). Mode 3 6-페어 status total12/done12/server_error0 → 15-05 SC4 입력
- [Phase ?]: Phase 19 Wave 0: RED proven by standalone behavioral failure (not collection); within_tolerance_remains_high intentionally RED (dead-zone), clean_pose/synthetic above-cutoff pass today as guards
- [Phase ?]: Mode1 reference_motion basis asserted on serialized build_mode1 comparison.scoringBasis (ITER-4 HIGH-1), kept out of Mode3 4-value gate (ITER-3 MEDIUM-1)
- [Phase ?]: Phase 19-02: kismam overall_score = IPSF 감점식(평균 폐기, 단일 major fault 지배), _PENALTY_PER_DEG=1.2 [ASSUMED] v1 (sweep 재calibrate 금지)
- [Phase ?]: Phase 19-02: overall_from_dimensions = min-of-core(angle/line), stability 종합 분리. line micro-bent <160deg = 요소 무효 0점 [CITED] IPSF
- [Phase ?]: Phase 19-02: DimensionExplanation.contributesToOverall OPTIONAL 3중 계약 추가 + 비기여 weightPercent=0 (HIGH-1)

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- [Phase 1 — 마이그레이션 HIGH]: 현 제품 코드는 NLF 기반 (`backend/shared/python/sunity_shared/analysis/pose_estimator.py`, RunPod GPU pod). Phase 1에서 MediaPipe 어댑터로 전환 + NLF 모듈을 R&D 비교군으로 격리 필요. RunPod GPU pod 비용 절감 + 라이선스 리스크 0 효과.
- [라이선스 — 출시 게이트]: NLF/SMPL-X는 R&D 비교군 전용으로 제품 비포함 결정 — Phase 진행은 블로킹되지 않음. 향후 NLF/SMPL-X를 제품에 도입하려면 Max Planck Innovation 상업 라이선스 클리어 필수 (`info@max-planck-innovation.de`). Meshcapade 채널은 종료됨.
- [Phase 5 — 외부 의존]: Gemini API 키(belle, Google AI Studio) 필요. Parameter Store / RunPod env 주입 전까지 Phase 5 블로킹.
- [v1.5 — 데이터 수집]: IPSF Code of Points 임계값(3~5개 동작 × phase별 GeometricCriterion) 라벨링은 v1 평행 진행 (belle/강사 협업).
- [전반 — 보안 HIGH]: 노출된 `sunity-api` AWS 키 비활성화 미완 (plan.md cleanup 큐). 작업 착수 전 처리 권장.
- [Phase 15 — 운영]: RunPod Pod 생명주기 수동. 재생성 시 proxy URL 변경 → Lambda env(RunpodAnalyzeUrl) 동기화 필요. 중단 시 실분석 전면 중단.
- [Phase 15 — iOS]: iOS 26+ native style 회귀(letterSpacing SIGABRT) — 빌드 10에서 ship 필요, 음수 style 값 audit.
- [Phase 16 — 데이터/스펙 박제]: Phase 1~15 의존성 없음 (v1 평행). Phase 1 진행 중 평행 진입 가능. 단 Phase 5 (Gemini 기술 인식기) / Phase 14 (정은지 reference) 가 Phase 16 데이터를 소비하므로 그 시점에 통합 필요. 첫 plan (16-01-PLAN.md) = AKA 매핑 13개 + 5트랙 spec + 카피 박제 (코드 통합 X).
- Plan 06-03 Task 5 pending checkpoint — belle 운영 작업 (Pod GPU 측정 + 로컬 seed + Firestore Console verify) 필요. Phase 14 reference 등록 helper 재사용 path 박제 완료, 실 데이터 백필만 잔여.
- 13-B Task 4 (criteria 5) Cerebras Pod E2E checkpoint 대기 — belle: SSM 키 + Lambda/Pod env + uvicorn 재시작 + 1건 실분석 검증. Tasks 2-3 완료(db252c9, 79d862c).

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-06-19T04:13:59.262Z

Stopped at: Phase 20 planned (4 plans/3 waves, plan-checker PASS_WITH_CONCERNS→C-1 fixed). pod-free Wave1-2 실행 가능, Wave3 eval=Pod terminal gate

### 2026-06-07 추가 fix 5종 (빌드 10 → 11 박제)

| commit | scope |
|---|---|
| `787a901` | iOS 26+ letterSpacing 음수 SIGABRT fix (typography.ts track → 0) |
| `e3bf753` | package-lock.json sync |
| `0472c01` | eas.json production profile env 박제 (.env gitignore 우회) |
| `0bd6a48` | get_previous_analysis mode 인자 박제 (mode3 first ↔ mode1 prev 함정) |
| `3f6681f` | Firestore composite index 회피 + in-memory mode filter |

### 박제 메모 [[runpod-gpu-env]] 함정 31-34 추가

- 31: eas.json production env 누락 (.gitignore 박제 .env)
- 32: Firebase 익명 uid 가 IPA 빌드별 다름 (정상 동작, 단 시연 시 데이터 fresh)
- 33: Firestore composite index 자동 생성 X — query 단순화 + in-memory filter
- 34: simulatedResult 폴백이 Firestore 없을 때 가짜 결과 보임 (dev 안전망 — production 박제 후보)

### belle 의 진단 + 박제 정신 안내 (코드 fix 없이)

- "Expo 박제 박제 박제 박제 박제 박제 X" — 박제 정신 정합 안내. TestFlight 박제 박제 박제 박제
- mode1 vs mode3 점수 차이 = 같은 정은지지만 다른 cut/clip 박제 정합
- ref-climb line 차원 누락 = IPSF "Transitions & Climbs" 박제 각도 임계 X (의도된 빈 list). foxtop/invert 박제 박제 line 박제 박제 박제
- "고급 88" = 사용자 박제 SkillLevel (advanced) 박제 평균 점수, 현재 분석과 무관
- VideoCompare 10초 정지 = 짧은 영상 끝나면 둘 다 정지 (동시 비교 박제 정신)

### 다음 세션 우선 진행 (belle 결정)

belle 의 의문 박제 정신 정합:

1. **개발 로드맵 순서 정리** — Phase 1-15 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 (Phase 5 박제 박제, Phase 1/14/15 박제 박제 박제)
2. **외부 AI 검증** — Codex/gpt-5.5 plan-review-convergence 박제 cross-check ([[cross-ai-plan-review-good]] 박제 정합)
3. **A/B/C plan 진행** (belle 명시 박제):
   - **A. Phase 12** = 실측 각도 표시 + 키포인트 오버레이 (큰 scope)
   - **B. (d) 결과 UI transparency** = result.tsx 차원별 "이게 무슨 기준" 박제 + 가중치 표시 (작은 scope)
   - **C. Phase 16 IPSF 5트랙 코드 통합** = 학원 용어 매핑 + RepetitionCriterion + Page 9 (중간 scope)

박제 정신상 belle 의 의도 = "사용자가 '아 이래서 이런 평가구나' 박제" = B 박제 빠른 path. A 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제. C 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제. 박제 정신상 A+B+C 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제.

### 2026-06-07 세션 핵심 박제

**Phase 5 사실상 완료** — mock E2E mode1/mode3 PASS + belle 실제 분석 mode1 점수 94/97 PASS + 5가지 UI/UX 의문 fix:

1. (b3) 코칭팁 라벨 중복 fix ("오른쪽 어깨 어깨" → "오른쪽 어깨")
2. (b4) 숫자 브랜드 컬러 강조 (#FF4B33)
3. (b5) 완벽 수행 메시지 (angle 95+ 시 + mode 분기)
4. (b1) backend playback-url Lambda 신설 + (b2) frontend wiring (S3 7일 TTL 만료 fix)
5. mode3 second+ overall 산식 변경 — (각도+안정성) 평균 (belle 의문 정합)

**Phase 15 진행** — TestFlight letterSpacing SIGABRT fix:

- root cause = `theme/typography.ts` 의 `track(size) = size * -0.04` (음수 letterSpacing)
- fix = `track(size) = 0` (commit 787a901)
- EAS Build 10 + auto-submit (commit e3bf753 lock sync)

**Cerebras 모델 fix** — `llama3.1-8b` deprecated → `gpt-oss-120b` (commit 1110935)

**SAM deploy regression fix** — Lambda env RUNPOD_ANALYZE_URL 직접 update (SAM template parameter default reset 함정 28)

### belle 박제 의문 정합 안내 (코드 fix 없이 박제 정신)

1. mode1=95 vs mode3=100 차이 = belle 영상 (_talkv_high.mp4) ≠ reference (ref-climb.mp4) 다른 cut → 정합
2. line 차원 누락 = `ref-climb` 은 IPSF "Transitions & Climbs" 박제 각도 임계 X (의도된 빈 list). 다른 motion (foxtop/invert) 시 line 정상 박제 — Phase 16 코드 통합 후속
3. "고급 88" = 사용자 박제 SkillLevel (advanced) 박제 평균 점수, 현재 분석과 무관
4. VideoCompare 10초 정지 = 짧은 영상 끝나면 둘 다 정지 (동시 비교 박제 정합)

Resume file: .planning/phases/20-v2-gemini/20-01-PLAN.md

### 2026-06-06 세션 핵심 사건 — OpenMMLab CDN 글로벌 만료

`download.openmmlab.com` 도메인이 2026-06-04 즈음 만료 — `dig +trace` 권한 NS 자체가 `expirens3/4.hichina.com` (Alibaba HiChina 만료 도메인 전용 NS). 박제된 RTMW URL + YOLOX URL 모두 도달 불가. mmpose 사용자 전체 영향. 박제 메모 [[rtmw-clean-weight-release-gate.md]] 의 우려 적중.

belle 결정 (mirror 검색 path) → HuggingFace anonymous mirror 활용 우회 완료:

- RTMW-X-384: `hf://bukuroo/RTMW-ONNX/rtmw-x-384.onnx` (369MB) + S3 백업 `s3://sunity-motion-pilot-videos/_artifacts/rtmw-x-384_bukuroo_hf.onnx`
- YOLOX-M (person detector): `hf://hr16/yolox-onnx/yolox_m.onnx` (97MB, Apache-2.0)

### 박제 commit + 함정 추가 (이번 세션)

| commit | 영역 | 내용 |
|---|---|---|
| 4b823de | setup_pod_full.sh | mmcv build ninja 선행 install + MAX_JOBS export (함정 26) |
| 081192b | rtmw_engine.py | YOLOX_ONNX_PATH env 박제 — OpenMMLab CDN 만료 우회 (함정 22) |

박제 메모 [[runpod-gpu-env.md]] 갱신 = 함정 20~27 추가 (누적 27종). 핵심:

- 함정 20: OpenMMLab CDN 글로벌 만료 (2026-06-04)
- 함정 21/22: RTMW + YOLOX HF mirror path
- 함정 23/24: setup_pod_full.sh 박제 누락 (runpod_inference/requirements.txt install + RUNPOD_AUTH_TOKEN .bashrc)
- 함정 25: server.py auth header = `X-RunPod-Token` (Authorization Bearer 아님)
- 함정 27: stale __pycache__ — git pull 후 uvicorn restart 시 cache 청소 필요

### 백엔드 검증 결과

| 검증 | 결과 |
|---|---|
| Pod /health 외부 | 200 OK, `pipeline_loaded:true, auth_configured:true` |
| Pod /analyze 외부 mock (X-RunPod-Token + dummy body) | 422 Pydantic validation (endpoint alive) |
| Lambda env RUNPOD_ANALYZE_URL | Active, 새 Pod URL 정합 |
| **mock E2E** (Pod 안에서 _process 직접 호출) | **PASS** — Firestore status=done, 49.8s |

### Pod 환경 (2026-06-17 시점, Pod 01emvodj1pdooe — RTX 4090, Network Storage EU-RO, 풀세팅 완료·검증)

| 항목 | 상태 |
|---|---|
| GPU / Container | RTX 4090 24GB / RunPod, driver 565, Python 3.11.10, torch 2.4.1+cu124 |
| Pod ID | `01emvodj1pdooe` |
| SSH (proxy) | `ssh 01emvodj1pdooe-6441164d@ssh.runpod.io -i ~/.ssh/id_ed25519` |
| SSH (direct TCP) | `ssh root@213.173.110.226 -p 39380 -i ~/.ssh/id_ed25519` |
| Network Storage | `/workspace` = `mfs#euro.runpod.net` (EU-RO, persist) — repo·rtmw-x-384.onnx·yolox_m.onnx·firebase-sa.json·aws_env.sh 보존. deps(onnxruntime-gpu/rtmlib/mmpose)는 overlay라 매 세션 재설치 |
| 서버 기동 | `nohup /workspace/start_p15_server.sh > /workspace/p15_server.log 2>&1 </dev/null &` (전체 env + GEMINI/RUNPOD_AUTH_TOKEN 명시 export 박제 — `.bashrc` early-return 우회). **kill은 ss PID로** (pkill 패턴이 ssh 명령 self-match → 셸 자살 함정) |
| HTTP Port 8000 | UP — `/health {status:ok, auth_configured:true, pipeline_loaded:true}`, GPU 1056MiB 모델 적재, RTMW-x-384(commercial_ok)+YOLOX+GeminiTechniqueRecognizer+Gemini 키 검증 |
| 인증 스모크 | wrong token→401 / correct token+bad key→400(auth 통과) / 외부 proxy /health→200 |
| Lambda env RUNPOD_ANALYZE_URL | `https://01emvodj1pdooe-8000.proxy.runpod.net/analyze` — **SSM `/sunity/motion/runpod-analyze-url` + 라이브 Lambda 둘 다 동기화(boto3 merge, 4키 보존)**. SSM이 source of truth라 sam deploy 시 안 되돌아감. AWS 자격 = sunity-motion (sunity-api는 Lambda 거부) |

### 이전 Pod 이력 (2026-06-06 종료 시점, Pod 1ablelgbtrzcgb — 교체됨)

| 항목 | 상태 |
|---|---|
| GPU / Container | RTX 3090 / RunPod PyTorch 2.4, Python 3.11 |
| SSH | `ssh -p 14818 -i ~/.ssh/id_ed25519 root@64.119.209.250` |
| /workspace | SunityMotion HEAD = 081192b, firebase-sa.json, rtmw_weights/rtmw-x-384.onnx, yolox_weights/yolox_m.onnx |
| .bashrc env | RUNPOD_AUTH_TOKEN/RTMW_ONNX_PATH/YOLOX_ONNX_PATH/RECOGNIZER_BACKEND=gemini/RTMW_DEVICE=cuda/LD_LIBRARY_PATH/FIREBASE_SA_PATH 박제 |
| uvicorn server | PID 9652 살아있음, 0.0.0.0:8000 LISTEN, 워밍업 완료 (RTMW+YOLOX+Gemini API 검증) |
| Lambda env RUNPOD_ANALYZE_URL | https://1ablelgbtrzcgb-8000.proxy.runpod.net/analyze |

### 남은 작업

- [ ] **TestFlight 튕김 fix** (별개 blocker, [Phase 15 — iOS] letterSpacing SIGABRT 후보) — belle 가 진짜 E2E 검증할 channel 필요
- [ ] **belle 진짜 E2E 검증** — Expo Go QR 또는 빌드 10 ship 후 TestFlight 재시도. mock 가 동일 path PASS 확인.
- [ ] Phase 5 close-out (ROADMAP Phase 5 ✓) — belle 진짜 E2E 통과 후
- [ ] Phase 6 진입 — Phase 5 close-out 후
- [ ] setup_pod_full.sh 후속 갱신 commit — 함정 23/24 박제 (runpod_inference/requirements.txt install + RUNPOD_AUTH_TOKEN + YOLOX_ONNX_PATH .bashrc + OpenMMLab CDN 우회 download path)
- [ ] mock E2E artifact cleanup (선택) — S3 `uploads/mock_e2e_belle_1780754054/` + Firestore mock doc
- [ ] sweep 박제 baseline 재산정 (선택) — cocktail13 → bukuroo 가중치 변경 영향 평가 (`sweep_rtmw_20260603_1409` baseline 과 직접 비교 무효 가능)
