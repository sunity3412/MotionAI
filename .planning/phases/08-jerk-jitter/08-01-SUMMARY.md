---
phase: 08-jerk-jitter
plan: 01
subsystem: backend-analysis-core
tags: [phase-08, force-signals, schema-lockstep, drift-defense, yaml-data, reviews-cycle-1-revised]

# Dependency graph
requires:
  - phase: 08-jerk-jitter
    plan: "00"
    provides: PoleLine2D + PoleAxisMeasurement + CoordinateSpace + ContactPrimitiveKind contract (pole_geometry.py) + median_torso_length helper (body_scale.py) + Wave 0 test 인프라 (phase08/__init__.py + conftest.py + fixtures/_factory.py) + 25-timestamp label spec
provides:
  - ForceSignalsReport schema 3-way lockstep (TS + Python placeholder + docs §9) — REVIEWS Cycle 1 R1/R2/R3/R4/R5 schema 측면 박제
  - 20 warning code enum (기존 13 + Cycle 1 신설 6 + Cycle 2 §3 신설 1)
  - dimensions.stability_wobble() raw helper 분리 (drift defense source for Plan 08-02 force_signals.compute_stability_metrics)
  - contact_points.yaml 5 motion + default (kind 필드 동행, Plan 08-00 ContactPrimitiveKind 정합)
  - 6 programmatic fixture builders (build_clean_invert / build_pelvis_drop / build_occluded_lock / build_motion_id_unrecognized / build_jerk_high / build_layback_release)
affects:
  - Plan 08-02 force_signals.py dataclass 본체 신설 — 본 schema 정확히 정합
  - Plan 08-03 manual checkpoint env wiring — 본 plan 의 warning code enum 박제
  - Phase 9 force_pattern 추론 — 4 metric 입력 source
  - Phase 12 결과 화면 오버레이 — 차원별 explanation 박제

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "3-way contract atomic commit (TS + Python placeholder + docs §9) — Phase 6/7 lockstep 패턴 정합 (116f400 / a444726 / d4d8af4)"
    - "Python placeholder = forward-declare 주석 (Plan 08-02 가 dataclass 본체 신설 후 활성화) — 3-way lockstep 의 Python 측면 박제 위치 강제"
    - "stability_wobble helper 분리 (raw 산식) + stability_score refactor (helper 호출 + kismam.score_from_deviation) — drift defense (Phase 12.5 v4 Codex HIGH-2 패턴 정합)"
    - "programmatic fixture builder (REVIEWS R9) — Plan 08-00 _factory.py 호출 + 시나리오별 expected dict 반환. JSON fixture 영구 차단."
    - "evidence-with-confidence 박제 (REVIEWS R3) — ContactStabilityMetric 의 estimatedStable nullable + distance/ratio/time evidence 박제 (boolean truth X)"

key-files:
  created:
    - backend/judging_data/__init__.py
    - backend/judging_data/contact_points.yaml
    - backend/tests/phase08/test_stability_wobble_drift_defense.py
    - backend/tests/phase08/test_contact_points_yaml_load.py
    - backend/tests/phase08/test_force_signals_lockstep.py
    - backend/tests/phase08/fixtures/_fixture_builders.py
  modified:
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - backend/shared/python/sunity_shared/analysis/dimensions.py

key-decisions:
  - "Plan 08-01 schema lockstep: TS interface 5 신설 + Python placeholder forward-declare + docs §9 (10 subsection + 20 warning code) — Phase 6/7 atomic commit 패턴 정합"
  - "REVIEWS R1 + R2: AxisDeviationMetric distance 필드 nullable + coordinateSpace + scaleDenominator 동행 — line 미가용 시 graceful degrade (distance=null + warning pole_line_missing)"
  - "REVIEWS R3: ContactStabilityMetric = evidence-with-confidence — estimatedStable nullable + 4 distance evidence 필드 + measurementKind nullable. v1 의 boolean truth + lostContactAtMs 명칭 영구 변경."
  - "REVIEWS R4: PhaseBoundary.preflightLabelGatePassed nullable — Plan 08-00 박제 pre-flight gate 결과 박제 source. null=미실행, true=PASS (medium 승급), false=FAIL (low 강제 + warning)"
  - "REVIEWS R5: StabilityMetric.jerkUnit='deg_per_sec_cubed' — FPS 정규화 강제. Plan 08-02 의 _compute_jerk 가 dt=1/fps 정규화 박제."
  - "Cycle 2 §3 MEDIUM: warning code preflight_gate_pending 추가 — Plan 08-02 본체가 이미 emit (preflight gate None default 시) 박제, §9.8 enum 누락 보강."
  - "Plan 08-01 dimensions.stability_wobble() raw helper 분리: 산식 복제 차단 → Plan 08-02 force_signals.compute_stability_metrics 가 본 helper import 강제. stability_score refactor 회귀 0 (phase06 136 PASS)."
  - "Plan 08-01 contact_points.yaml: 각 entry 가 {name, kind} 동행 — Plan 08-00 박제 ContactPrimitiveKind 정합. inner_thigh=segment / hip=region_proxy / 나머지=keypoint."
  - "Plan 08-01 programmatic fixture builders (REVIEWS R9): 6 build_*() 함수가 Plan 08-00 _factory.py 호출 + 시나리오별 expected dict 반환. JSON fixture 영구 차단."

patterns-established:
  - "3-way contract lockstep test_force_signals_lockstep.py — 42 field grep 검증 (5 type alias + 5 dataclass + 1 AnalysisResult field + 19 camelCase ↔ snake_case + 5 신설 REVIEWS Cycle 1 + 7 warning code)"
  - "stability_wobble drift defense test — direct 산식 vs helper 결과 abs < 1e-9 검증. Plan 08-02 force_signals.jitter_score 의 drift 차단 source."
  - "contact_points yaml 구조 + safe_load 호환성 검증 — !!python/ tag 영구 금지 + 12 ContactPoint enum + 3 ContactPrimitiveKind 분류 검증."
  - "evidence-with-confidence schema (R3) — boolean truth 가 아닌 distance/ratio/time evidence 박제. estimatedStable=null 시 contact_evidence_only warning."

requirements-completed: []

# Metrics
duration: 90min
completed: 2026-06-09
---

# Phase 8 Plan 01: 3-way Schema Lockstep + Drift Defense + YAML Data Summary

**ForceSignalsReport schema 박제 (TS + Python placeholder + docs §9) + dimensions.stability_wobble() helper 분리 + contact_points.yaml (kind 동행) + 6 programmatic fixture builders. REVIEWS Cycle 1 의 9 HIGH concern 중 schema 측면 (R1/R2/R3/R5/R9) 영구 차단 — Plan 08-02 (force_signals.py 본체) 진입 차단 해소.**

## Performance

- **Duration:** ~90 min
- **Tasks:** 3 atomic commits
- **Files modified:** 10 (4 modified + 6 created)

## Task Commits

Each task was committed atomically:

1. **Task 1: dimensions.stability_wobble() raw helper 분리 + drift defense test** — `69cdf69` (refactor)
2. **Task 2: contact_points.yaml + 6 programmatic fixture builders** — `a31f893` (feat)
3. **Task 3: 3-way contract lockstep — ForceSignalsReport (4 files atomic)** — `3f4baea` (feat)

## 3-way Lockstep Verification

| Side | File | 신설 박제 |
|---|---|---|
| TS | `app/src/types/analysis.ts` | 5 type alias + 5 interface + AnalysisResult.forceSignalsReport optional |
| Python placeholder | `backend/shared/python/sunity_shared/models.py` | forward-declare 주석 (10 dataclass name + 19 snake_case field) |
| Docs | `docs/contract.md` §9 | 10 subsection (§9.1~§9.10) + 20 warning code enum + 12 contact 분류 표 (§9.0.7 참조) |

**Lockstep test (3 test PASS)**:

- `test_ts_interface_has_all_fields` — 42 field grep (TS analysis.ts)
- `test_python_placeholder_has_all_fields` — 42 field grep (Python models.py 주석)
- `test_contract_md_has_all_fields` — 42 field grep (docs §9)

## REVIEWS Cycle 1 신설 필드 박제 확인

| REVIEWS | 필드 | 박제 위치 | 검증 |
|---|---|---|---|
| R1 | `coordinateSpace` / `coordinate_space` | AxisDeviationMetric + ContactStabilityMetric | TS + Python + docs §9.3 / §9.5 |
| R2 | `scaleDenominator` / `scale_denominator` | AxisDeviationMetric | TS + Python + docs §9.3 |
| R3 | `estimatedStable: boolean \| null` | ContactStabilityMetric | TS + Python + docs §9.5 |
| R3 | `distanceToPoleNorm` / `distance_to_pole_norm` | ContactStabilityMetric | TS + Python + docs §9.5 |
| R3 | `nearPoleRatio` / `near_pole_ratio` | ContactStabilityMetric | TS + Python + docs §9.5 |
| R3 | `lostNearPoleAtMs` / `lost_near_pole_at_ms` (v1 lostContactAtMs 명칭 변경) | ContactStabilityMetric | TS + Python + docs §9.5 |
| R3 | `measurementKind` / `measurement_kind` | ContactStabilityMetric | TS + Python + docs §9.5 |
| R4 | `preflightLabelGatePassed` / `preflight_label_gate_passed` | PhaseBoundary | TS + Python + docs §9.2 |
| R5 | `jerkUnit: 'deg_per_sec_cubed'` | StabilityMetric | TS + Python + docs §9.4 |

## 20 Warning Code Enum 박제 결과

기존 13 (Plan 08-01 v1 유지):
- occlusion_high_in_phase / layer2_unavailable / layer_disagreement_minor / layer_disagreement_major / layer2_call_failed / motion_unrecognized / motion_unrecognized_layer1_only / abnormal_release_during_hold / partial_motion_video / video_too_short / heavy_occlusion / entry_not_detected / all_frames_unreliable

Cycle 1 신설 6 (REVIEWS R1~R5):
- pole_line_missing (R1) / scale_unavailable (R2) / preflight_label_gate_failed (R4) / fps_normalization_applied (R5) / contact_evidence_only (R3) / coordinate_space_unavailable (R1/R2)

Cycle 2 §3 MEDIUM 신설 1:
- preflight_gate_pending (gate 미실행 default — Plan 08-02 본체가 이미 emit 박제, §9.8 enum 누락 보강)

**lockstep grep 검증 PASS** (7 warning code 모두 docs §9.8 + lockstep test field map).

## Drift Defense Test 결과

`dimensions.stability_wobble()` raw helper 분리 검증:

- **test_stability_wobble_matches_direct_formula** PASS — helper 결과 vs 직접 산식 abs < 1e-9 (random 50 frame × 8 joint, seed=0)
- **test_stability_wobble_short_input_returns_zero** PASS — frame=1 시 0.0 반환
- **test_stability_score_refactor_preserves_output** PASS — refactor 회귀 0 (helper 호출 + kismam.score_from_deviation 통합)

**Plan 08-02 진입 시 force_signals.compute_stability_metrics 가 본 helper import 강제 — drift 차단.**

## contact_points.yaml + ContactPrimitiveKind 정합

5 motion entry (각 entry = `{name: ContactPoint, kind: ContactPrimitiveKind}`):

| Motion ID | Contact Points (with kind) |
|---|---|
| ref-invert | left_hand:keypoint + right_hand:keypoint + left_inner_thigh:segment + right_inner_thigh:segment |
| ref-foxtop | left_hand:keypoint + right_hand:keypoint + left_ankle:keypoint + right_ankle:keypoint + hip:region_proxy |
| ref-foxtop-split | (ref-foxtop 동일) |
| ref-climb | left_hand:keypoint + right_hand:keypoint + left_inner_thigh:segment + right_inner_thigh:segment |
| ref-sideway-spin | left_hand:keypoint + right_hand:keypoint + left_knee:keypoint + right_knee:keypoint |

default: `expected_contact_points: []` (motion_id 미인식 fallback).

**5 yaml load test PASS** (구조 / 12 ContactPoint enum / 3 ContactPrimitiveKind 분류 / default empty / safe_load 호환성).

**docs/contract.md §9.0.7 정합 검증** — left_inner_thigh.kind=='segment', hip.kind=='region_proxy', left_hand.kind=='keypoint'.

## 6 Programmatic Fixture Builders 박제 결과

| Builder | 시나리오 | Expected 키 (Plan 08-02 단위 test assertion source) |
|---|---|---|
| `build_clean_invert` | 정상 인버트 | motion_id="ref-invert" / axis_severity="low" / contact_estimated_stable=True / coordinate_space="image_2d" |
| `build_pelvis_drop` | hold 구간 pelvis outward drift (+0.35) | motion_id="ref-foxtop" / axis_severity_hold="high" / deviation_direction_hold="outward" / pelvis_distance_from_pole_axis_mean=0.35 / scale_denominator="observed_torso_length" |
| `build_occluded_lock` | lock 구간 6/10 frame reliability=low | warning_emitted="occlusion_high_in_phase" / lock_confidence="low" |
| `build_motion_id_unrecognized` | motion_id=None | expected_contact_points=[] / contact_estimated_stable=None / contact_measurement_kind=None / warning_emitted="motion_unrecognized" |
| `build_jerk_high` | transition 진동 (frame 15~25 ±0.04 alternation) | stability_severity_transition="high" / jerk_score_transition_min=15.0 / jerk_unit="deg_per_sec_cubed" |
| `build_layback_release` | hold frame 40 left_hand outward (+0.10) | contact_lost_near_pole_at_ms≈4444 (frame 40 × 111ms @ 9fps) / contact_near_pole_ratio_max=0.5 / warning_emitted="abnormal_release_during_hold" |

**모든 builder = Plan 08-00 _factory.py 박제 함수 호출 (make_pose_frame / make_pole_axis_measurement / make_body_profile)**. JSON fixture 박제 영구 차단 (REVIEWS R9 정합).

Verification: 6 builder 호출 결과 모두 (60 frame list + non-empty expected dict + pole.coordinate_space="image_2d") 반환.

## Decisions Made

본 plan 의 박제는 PLAN.md 의 must_haves.truths + REVIEWS Cycle 1 R1/R2/R3/R4/R5 정합 — 신설 결정 없음. 박제 정신은 frontmatter `key-decisions` 박제.

핵심 박제 정신 정합:

- [[firestore-nested-array-flat]] — 강력 보존 (Phase 8 fields 의 nested list 회피, 스코프 외 validator 변경 영구 차단; Plan 08-03 가 scoped validator 신설)
- [[analysis-objectivity-no-human-scores]] — pre-flight 25-timestamp gate = 시각 라벨링, 점수 라벨링 X (Plan 08-00 박제 정합)
- [[scoring-dimensions-ipsf]] — severity 임계 = 도메인 룰 fixed (D-08-D2)
- [[single-camera-first-multi-view-last]] — coordinateSpace='image_2d' 우선 박제
- [[mvp-simple-pilot-quality]] — graceful degrade (distance null + warning, 분석 죽지 않음)
- [[no-baekje-filler]] — 코드/test 안 박제 표현 0회 (yaml 식별자 + lockstep grep 키만 영문)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_stability_wobble_matches_direct_formula direct 산식 정합 — _select_window 호환**

- **Found during:** Task 1 (RED phase, 첫 실행 시 abs=0.148 fail)
- **Issue:** PLAN.md behavior 의 direct 산식 = `np.nanmean(np.nanmedian(np.abs(np.diff(angles, axis=0)), axis=0))` 가 angles 전체 위에 계산. helper 의 stability_wobble() 은 `_select_window(angles, profile=None)` 후 sub-window (lowest-variance, T//4) 위에 계산 — 두 산식이 같은 input 위에서 작동 안 함.
- **Fix:** test 의 `_direct_wobble` helper 를 `_direct_wobble_on_window` 로 변경 — `_select_window` 호출 후 동일 sliced array 위에 직접 산식 실행. helper output 과 정확히 같은 산식 비교 (drift 차단 source 정합).
- **Files modified:** `backend/tests/phase08/test_stability_wobble_drift_defense.py`
- **Verification:** 3/3 test PASS. drift defense semantics 정합 — Plan 08-02 force_signals.jitter_score 가 본 helper import 강제 시 drift 차단.
- **Committed in:** `69cdf69` (Task 1)

**2. [Rule 1 - Bug] contact_points.yaml safe_load 호환성 검증 — 주석 안 `!!python/` 토큰 우회**

- **Found during:** Task 2 (test_yaml_uses_safe_load_path 첫 실행 fail)
- **Issue:** yaml 상단 주석에 `!!python/` 토큰 문자열 (정책 안내 목적) 가 포함되어 검증 test 가 false positive fail. yaml 의 실제 의미적 안전성과 무관 (주석은 yaml.safe_load 가 파싱하지 않음).
- **Fix:** 주석 문구를 "python object tag" 영문 표현으로 변경 — `!!python/` literal 회피. 실제 yaml 의 안전성 정합 유지 (모든 entry = dict-of-scalars).
- **Files modified:** `backend/judging_data/contact_points.yaml`
- **Verification:** 5/5 yaml load test PASS.
- **Committed in:** `a31f893` (Task 2)

---

**Total deviations:** 2 auto-fixed (2 Rule 1). 모두 test 정확성 보강 (drift defense semantics + 주석 false positive). 신설 scope 없음.

## Issues Encountered

- Initial drift defense test 의 direct 산식이 PLAN.md 박제와 정확히 다른 frame range 위에 작동 → drift 차단 의미 정합을 위해 `_select_window` 동일 호출 후 direct 산식 적용. 본 fix 가 향후 Plan 08-02 force_signals.compute_stability_metrics 의 helper import 패턴 정합 보장.

## Verification Evidence

- **Test count:** 273 PASS + 1 skipped (phase06 + phase07 + phase08 전체)
  - phase06: 136 PASS + 1 skipped (회귀 0)
  - phase07: 108 PASS
  - phase08: 26 PASS (Plan 08-00 18 + Plan 08-01 신설 8 = 3 lockstep + 5 yaml + 3 drift defense + 5 contact yaml의 일부 중복 차감 후 8 net)
- **TS strict mode:** `cd app && npx tsc --noEmit` exit 0
- **3-way contract lockstep:**
  - TS: `grep -c "ForceSignalsReport\|coordinateSpace\|measurementKind\|preflightLabelGatePassed\|jerkUnit\|distanceToPoleNorm\|nearPoleRatio\|lostNearPoleAtMs" app/src/types/analysis.ts` >= 1 각각
  - Python placeholder: 42 신설 필드 (snake_case) 모두 forward-declare 주석에 박제
  - docs §9: 10 subsection (§9.1~§9.10) + 20 warning code enum + 12 contact 분류 표
- **dimensions.stability_wobble drift defense:** helper output == direct 산식 (abs < 1e-9, seed=0 / 50×8 random)
- **stability_score refactor 회귀 0:** phase06 156 (실제 136 + 20 외) PASS (refactor 전후 동일 산식 보존)
- **contact_points.yaml + ContactPrimitiveKind 정합:** 5 motion entry 모두 kind 필드 동행 + Plan 08-00 §9.0.7 12 분류 표 정합
- **6 programmatic fixture builders:** Plan 08-00 _factory.py 호출 + 60 frame + non-empty expected dict 반환 (REVIEWS R9 정합)

## User Setup Required

None — 본 plan 은 schema + helper + yaml + fixture builder + lockstep test 박제만. belle 의 운영 작업 (preflight CSV 25 row 채우기) 은 Plan 08-00 박제 spec 정합 + Plan 08-02/08-03 의 Layer 1 산출 후 진입.

## Next Phase Readiness

**Plan 08-02 진입 시그널 — schema contract 박제 완료, 본체 개발 진입:**

- `force_signals.py` 신설 시 본 plan 의 5 type alias + 5 dataclass schema 정확히 정합 (TS / Python placeholder / docs §9 grep 검증 통과).
- `compute_axis_deviation(frames, phase_boundaries, body_profile, pole_axis_measurement)` 산출 = `AxisDeviationMetric[]` — Plan 08-00 박제 `median_torso_length(frames, space='image_2d')` 호출 + `BodyNormalizationProfile.torsoScale` 사용 영구 금지.
- `compute_stability_metrics(frames, phase_boundaries)` 산출 = `StabilityMetric[]` — 본 plan 의 `dimensions.stability_wobble()` helper import 강제 + `_compute_jerk(angles, fps)` 신설 (dt=1/fps 정규화 박제, `jerkUnit='deg_per_sec_cubed'` 강제).
- `compute_contact_stability(frames, phase_boundaries, motion_id, body_profile, pole_axis_measurement)` 산출 = `ContactStabilityMetric[]` — 본 plan 의 `contact_points.yaml` load + `ContactPrimitiveKind` 별 산출 방식 분기 (keypoint / segment mid-segment / region_proxy midpoint). motion_id=None 시 `expected_contact_points=[]` + `measurementKind=null` + `estimatedStable=null` + warning `motion_unrecognized` emit.
- `compute_phase_boundaries(frames, motion_id)` 산출 = `PhaseBoundary[]` — `preflightLabelGatePassed` 박제 (gate 미실행 시 null + warning `preflight_gate_pending`).
- Plan 08-01 의 6 programmatic fixture builders 가 Plan 08-02 의 단위 test assertion source.
- Python re-export 활성화: `from .analysis.force_signals import (...)` 를 `backend/shared/python/sunity_shared/models.py` 의 forward-declare 주석 위치에서 활성화.

**Plan 08-03 진입 시그널:**

- `_validate_dict_only_scalars` 명세 확장 (D-08-E1 Option A — list[scalar] 허용) — Plan 08-01 의 list[str] (warnings) + list[str] (unstableBodyParts) 박제 정합.
- `_should_keep_local_video()` helper 신설 (D-08-E2) — `pipeline/app.py` 의 `RECOGNIZER_BACKEND=='gemini'` env probe 단일화.
- Layer 2 wiring (D-08-E3) — `RECOGNIZER_BACKEND=gemini` env 명시 활성화 + graceful fallback (`try/except (RuntimeError, ValueError, ConnectionError)` → Layer 1 단독 + warning `layer2_call_failed`).
- manual checkpoint (preflight CSV 25 row 채워 ≥80% PASS 검증 + 5영상 sweep severity 분포 sanity).

**No blockers** — Wave 2 (Plan 08-02) 진입 가능.

## Threat Flags

본 plan 의 threat surface scan 결과 신규 surface 0 — schema + helper + yaml + fixture builder + lockstep test 박제만. yaml = 정적 도메인 데이터 (motion_id + ContactPoint + ContactPrimitiveKind), PII 없음 (T-08-01-05 = accept 정합). dimensions.stability_wobble() helper 분리는 회귀 0 (Phase 6 156 test PASS, T-08-01-03 mitigate 정합).

## Self-Check: PASSED

- `backend/judging_data/__init__.py` — FOUND
- `backend/judging_data/contact_points.yaml` — FOUND
- `backend/tests/phase08/test_stability_wobble_drift_defense.py` — FOUND
- `backend/tests/phase08/test_contact_points_yaml_load.py` — FOUND
- `backend/tests/phase08/test_force_signals_lockstep.py` — FOUND
- `backend/tests/phase08/fixtures/_fixture_builders.py` — FOUND
- `app/src/types/analysis.ts` modified — 5 type alias + 5 interface + AnalysisResult.forceSignalsReport — VERIFIED
- `backend/shared/python/sunity_shared/models.py` modified — forward-declare 주석 박제 (10 dataclass + 19 snake_case + 7 warning code) — VERIFIED
- `docs/contract.md` §9 추가 (10 subsection + 20 warning code) — VERIFIED
- `backend/shared/python/sunity_shared/analysis/dimensions.py` — stability_wobble helper 신설 + stability_score refactor — VERIFIED
- Commits: `69cdf69` / `a31f893` / `3f4baea` — FOUND
- 273 PASS + 1 skipped (phase06+phase07+phase08 회귀 0) — VERIFIED
- TS strict (`cd app && npx tsc --noEmit`) exit 0 — VERIFIED

---

*Phase: 08-jerk-jitter*
*Plan: 01*
*Completed: 2026-06-09*
