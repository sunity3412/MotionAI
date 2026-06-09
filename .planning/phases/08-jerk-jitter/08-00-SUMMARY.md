---
phase: 08-jerk-jitter
plan: 00
subsystem: backend-analysis-core
tags: [phase-08, coordinate-contract, scale-contract, preflight-gate, wave-0-infra, reviews-cycle-1, pole-geometry, body-scale]

# Dependency graph
requires:
  - phase: 01-poseengine-mediapipe-nlf-r-d
    provides: PoleAxis dataclass (direction-only) + HoughPoleDetector (image 2D 검출) — pole_geometry.py 가 axis_3d 메타 reuse + line 표현 contract 박제
  - phase: 02-body-normalization
    provides: BodyNormalizationProfile 7 필드 — body_scale.py 가 torso_scale 사용 영구 금지 정책 정합 (drift defense)
  - phase: 06-body-comparison
    provides: 3-way contract lockstep 패턴 (TS + Python + docs/contract.md atomic commit) — 본 plan 의 §9.0 박제 정합
provides:
  - PoleLine2D + PoleAxisMeasurement + CoordinateSpace + ContactPrimitiveKind contract (pole_geometry.py + analysis.ts + docs §9.0)
  - median_torso_length helper (body_scale.py) + BodyNormalizationProfile.torso_scale 사용 영구 금지 drift defense
  - Wave 0 test 인프라 (phase08/__init__.py + conftest.py + fixtures/_factory.py) — 7 programmatic factory + 3 pytest fixture
  - Pre-flight 25-timestamp label gate (PREFLIGHT-LABEL-SPEC.md + preflight_label_template.csv)
affects: [Plan 08-01 ForceSignalsReport schema, Plan 08-02 compute_axis_deviation/compute_contact_stability, Plan 08-03 manual checkpoint env wiring, Phase 9 force_pattern 추론, Phase 12 결과 화면 오버레이]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PoleAxis 본체 변경 0 + 신설 모듈 pole_geometry.py 에 보강 contract 박제 (Phase 1 lockstep 회귀 0)"
    - "coordinate_space enum 강제 동행 (모든 distance metric) + invariant 'line None ↔ unavailable' Python __post_init__ 강제"
    - "drift defense via AST gate test (docstring strip 후 실행 코드만 검증) — body_normalization import 영구 차단"
    - "programmatic dataclass factory (REVIEWS R9 권고) — JSON fixture 없이 정확한 시그너처 박제 (REVIEWS H1 영구 차단)"
    - "pre-flight 25-timestamp label = 시각 라벨링 (수치 score 아님) — analysis-objectivity-no-human-scores 정합"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/pole_geometry.py
    - backend/shared/python/sunity_shared/analysis/body_scale.py
    - backend/tests/phase08/__init__.py
    - backend/tests/phase08/conftest.py
    - backend/tests/phase08/fixtures/__init__.py
    - backend/tests/phase08/fixtures/_factory.py
    - backend/tests/phase08/test_pole_geometry_contract.py
    - backend/tests/phase08/test_body_scale_helper.py
    - backend/tests/phase08/test_preflight_label_schema.py
    - .planning/phases/08-jerk-jitter/preflight/PREFLIGHT-LABEL-SPEC.md
    - .planning/phases/08-jerk-jitter/preflight/preflight_label_template.csv
  modified:
    - app/src/types/analysis.ts
    - docs/contract.md

key-decisions:
  - "Plan 08-00 R1: PoleLine2D + PoleAxisMeasurement 신설 모듈 (pole_geometry.py) 에 박제 — Phase 1 의 PoleAxis 본체 변경 0 강제 (lockstep 회귀 0)"
  - "Plan 08-00 R1 invariant: PoleAxisMeasurement.line=None ↔ coordinate_space='unavailable' — Python __post_init__ 가 양방향 위반 시 ValueError raise"
  - "Plan 08-00 R2: BodyNormalizationProfile.torso_scale 사용 영구 금지 — body_scale.py 본체에서 body_normalization import 영구 차단. AST gate test 가 docstring strip 후 실행 코드만 검증해 정당한 docstring 안내 통과 + 코드 위반은 fail"
  - "Plan 08-00 R3: ContactPrimitiveKind 3 분류 (keypoint / segment / region_proxy) — 12 contact 분류 표가 docs §9.0.7 박제 (left_inner_thigh / right_inner_thigh = segment, hip = region_proxy, 나머지 9 = keypoint, unknown 포함)"
  - "Plan 08-00 R4: Pre-flight 25-timestamp label gate — 시각 라벨링 (수치 score 아님) ≥ 80% (delta_ms ≤ 200ms) PASS → Layer 1 confidence='medium' 승급. FAIL 시 unwind path = Plan 08-03 env unset (분석 죽지 않음)"
  - "Plan 08-00 R9 + H1: programmatic factory (JSON 없이) + 정확한 dataclass 시그너처 (PoseFrame.frame_index / Keypoint3DAligned 3 필드 / BodyNormalizationProfile 7 필드, asymmetry 없음) — REVIEWS H1 dataclass mismatch 영구 차단"
  - "Plan 08-00 (deviation): drift defense AST gate refinement — 초기 simple substring grep 이 docstring 의 정당한 'BodyNormalizationProfile 사용 금지' 안내까지 차단. AST 로 docstring 제거 후 실행 코드만 검증하는 helper 신설 + ast.ImportFrom/ast.Import gate 추가"

patterns-established:
  - "3-way contract atomic commit: TS interface (app/src/types/analysis.ts) + docs/contract.md §X + Python 본체 (analysis/*.py) 단일 commit 박제. Plan 06-01/07-01 패턴 정합. lockstep test (camelCase ↔ snake_case 5 field mirror) 가 검증."
  - "drift defense via AST gate: substring grep 대신 ast.parse → docstring 제거 → 실행 코드만 검증 + ast.ImportFrom 패턴별 차단. body_normalization import 영구 금지 같은 정책을 코드로 강제."
  - "programmatic dataclass factory: JSON fixture 박제 진입 차단 시 _factory.py 에 7 factory (make_keypoint3d / make_keypoint3d_aligned / make_keypoint2d / make_pose_frame / make_body_profile / make_pole_line_2d / make_pole_axis / make_pole_axis_measurement) 박제. 실제 dataclass 시그너처 정확히 mirror 강제."
  - "coordinate_space + warning 자동 박제 패턴: distance metric 의 'unavailable' 시 numeric 필드 null + warning ('pole_line_missing' / 'scale_unavailable') 강제. graceful degrade (분석 죽지 않음, mvp-simple-pilot-quality 정합)."

requirements-completed: [FORCE-01]

# Metrics
duration: 50min
completed: 2026-06-09
---

# Phase 8 Plan 00: Phase 8 Coordinate/Scale pre-contract + Pre-flight gate Summary

**PoleLine2D + PoleAxisMeasurement + median_torso_length helper + Wave 0 test 인프라 + 25-timestamp label gate — REVIEWS Cycle 1 의 4 HIGH blocker (R1/R2/R3/R4) + H1 dataclass mismatch + R9 programmatic factory 권고를 단일 thin plan 으로 박제. Plan 08-01/02/03 의 contract dependency 해소.**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-06-09T03:30Z (approx)
- **Completed:** 2026-06-09T04:20Z (approx)
- **Tasks:** 3
- **Files modified:** 13 (11 created + 2 modified)

## Accomplishments

- **R1 blocker 해소 (PoleAxis position 부재)**: PoleLine2D (image 2D 직선) + PoleAxisMeasurement (axis_3d + line + coordinate_space) 신설. PoleAxis 본체 변경 0 → Phase 1 lockstep 회귀 0. line=None ↔ coordinate_space='unavailable' invariant Python __post_init__ 강제.
- **R2 blocker 해소 (torsoScale 오용)**: median_torso_length(pose_frames, *, space) helper 신설. observed shoulder-hip midpoint Euclidean median, valid frame < 5 시 None. body_scale.py 본체는 body_normalization import 영구 차단 — AST gate test 가 docstring strip 후 실행 코드만 검증.
- **R3 blocker 해소 (contact primitive 불명확)**: ContactPrimitiveKind enum (keypoint / segment / region_proxy) + 12 contact 분류 표 (docs §9.0.7) 박제. left_inner_thigh / right_inner_thigh = segment, hip = region_proxy, 나머지 9 keypoint + unknown.
- **R4 blocker 해소 (Layer-1 5-phase 미검증)**: Pre-flight 25-timestamp label spec (8 section) + CSV template (5영상 × 5 phase) + 3 schema test 박제. belle 운영 작업 진입 차단 해소. ≥80% PASS → Layer 1 confidence='medium' 승급, 미만 → 'low' 강제 + unwind path (Plan 08-03 env unset).
- **H1 + R9 blocker 해소 (dataclass mismatch + programmatic factory)**: phase08 test 인프라 신설. 7 programmatic factory 가 실제 dataclass 시그너처 정확 mirror (PoseFrame.frame_index NOT frame_idx, Keypoint3DAligned 3 필드 visibility 없음, BodyNormalizationProfile 7 필드 asymmetry 없음).
- **3-way contract atomic commit**: TS interface (analysis.ts) + docs §9.0 (7 subsection) + Python 본체 (pole_geometry.py + body_scale.py) 단일 commit. Plan 06-01/07-01 lockstep 패턴 정합. TS strict 모드 통과.

## Task Commits

Each task was committed atomically:

1. **Task 1: pole_geometry.py + body_scale.py + Wave 0 test 인프라** — `2261dc5` (feat)
2. **Task 2: 3-way contract lockstep (TS + docs §9.0 + lockstep test)** — `928c6d4` (feat)
3. **Task 3: Pre-flight 25-timestamp label spec + CSV template + schema test** — `80c353e` (feat)

## Files Created/Modified

### Created (11)

- `backend/shared/python/sunity_shared/analysis/pole_geometry.py` — PoleLine2D / PoleAxisMeasurement / CoordinateSpace / ContactPrimitiveKind enum + 2 helper (point_to_pole_line_distance_2d + build_pole_axis_measurement). PoleAxis 본체 변경 0.
- `backend/shared/python/sunity_shared/analysis/body_scale.py` — median_torso_length helper. body_normalization import 영구 차단.
- `backend/tests/phase08/__init__.py` — phase08 패키지 marker (빈 파일).
- `backend/tests/phase08/conftest.py` — 3 pytest fixture (synthetic_pose_frames 60 frame + synthetic_body_profile + synthetic_pole_axis_measurement) + PHASE08_FIXTURES_DIR 상수.
- `backend/tests/phase08/fixtures/__init__.py` — 빈 파일.
- `backend/tests/phase08/fixtures/_factory.py` — 7 programmatic factory (make_keypoint3d / make_keypoint3d_aligned / make_keypoint2d / make_pose_frame / make_body_profile / make_pole_line_2d / make_pole_axis / make_pole_axis_measurement). REVIEWS H1 dataclass mismatch 영구 차단.
- `backend/tests/phase08/test_pole_geometry_contract.py` — 8 test (4 Task 1 contract + 4 Task 2 lockstep).
- `backend/tests/phase08/test_body_scale_helper.py` — 7 test (3 space 분기 + missing keypoint + invalid space + 2 drift defense AST gate).
- `backend/tests/phase08/test_preflight_label_schema.py` — 3 test (spec md exists / csv header / csv 25 row + 5 video × 5 phase 분포).
- `.planning/phases/08-jerk-jitter/preflight/PREFLIGHT-LABEL-SPEC.md` — 8 section belle 운영 docs.
- `.planning/phases/08-jerk-jitter/preflight/preflight_label_template.csv` — header + 25 row template.

### Modified (2)

- `app/src/types/analysis.ts` — PoleAxis 직후 + BodyNormalizationProfile 직전 박제. CoordinateSpace / ContactPrimitiveKind type + PoleLine2D / PoleAxisMeasurement interface 4 신설. AnalysisDoc 영향 0.
- `docs/contract.md` — §8.3 직후 + 끝 footer 직전 §9.0 신설 (7 subsection: CoordinateSpace enum / ContactPrimitiveKind enum / PoleLine2D 표 / PoleAxisMeasurement 표 + invariant / median_torso_length 박제 + torso_scale 사용 영구 금지 정책 / Pre-flight 25-timestamp label gate / 12 contact 분류 표).

## Decisions Made

본 plan 의 박제는 PLAN.md 의 D-08-E* / must_haves.truths 결정 정합 — 신설 결정 없음. 박제 정신은 frontmatter `key-decisions` 박제.

핵심 박제 정신 정합:

- [[single-camera-first-multi-view-last]] — coordinateSpace='image_2d' 우선 박제 (Phase 1 HoughPoleDetector image 평면 검출 정합). pole_aligned 3D 는 future plan.
- [[mvp-simple-pilot-quality]] — line/scale 미가용 시 distance/length null + warning 박제 (분석 죽지 않음 / graceful degrade).
- [[analysis-objectivity-no-human-scores]] — Pre-flight 25-timestamp label = phase boundary 시각 라벨링 (수치 score 아님). belle 의 시각 인식은 객관적 사실, 점수 라벨링과 분리.
- [[no-baekje-filler]] — 박제 표현 코드/test 안 0회 (CSV 의 `agreed` 컬럼 등 영문 식별자만).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] drift defense AST gate refinement — docstring 우회 차단**

- **Found during:** Task 1 (test_body_scale_helper.py 첫 실행)
- **Issue:** 초기 단순 substring grep 으로 'BodyNormalizationProfile' literal 차단 시, body_scale.py 의 docstring 안 정당한 "BodyNormalizationProfile.torso_scale 사용 금지" 안내 문구까지 차단해 test 가 fail. 정책 강제와 docs 정합 양립 불가.
- **Fix:** `_strip_comments_and_docstrings` AST helper 신설 — ast.parse 후 module / FunctionDef / AsyncFunctionDef / ClassDef 의 docstring 노드 제거 후 ast.unparse 로 실행 코드만 추출. 추가로 `test_body_scale_source_imports_clean` AST 기반 import gate 신설 — `ast.ImportFrom` + `ast.Import` 노드 walk 으로 body_normalization 모듈 또는 BodyNormalizationProfile 심볼 import 영구 차단.
- **Files modified:** `backend/tests/phase08/test_body_scale_helper.py`
- **Verification:** 7/7 test PASS. 정당한 docstring 안내는 통과, 실행 코드 내 위반은 fail (양방향 검증).
- **Committed in:** `2261dc5` (Task 1 commit)

**2. [Rule 2 - Missing Critical] test_median_torso_length_world_3d 추가 + test_median_torso_length_invalid_space_raises 추가**

- **Found during:** Task 1 (behavior 정의 검토)
- **Issue:** PLAN.md 의 test_body_scale_helper.py 는 4 test 만 명시 (image_2d / pole_aligned / missing keypoint / torso_scale gate). world_3d space 분기와 invalid space ValueError 분기는 helper 의 정상 동작 영역인데 검증 미박제.
- **Fix:** 2 추가 test 박제 — test_median_torso_length_world_3d (60 frame world 3D 좌표 검증) + test_median_torso_length_invalid_space_raises (space enum 검증 ValueError). PLAN 의 acceptance_criteria #pytest exit 0 정합.
- **Files modified:** `backend/tests/phase08/test_body_scale_helper.py`
- **Verification:** 7/7 PASS (4 PLAN 명시 + 2 추가 + 1 drift defense source imports clean).
- **Committed in:** `2261dc5` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 + 1 Rule 2)
**Impact on plan:** 2 fix 모두 correctness 강제 (drift defense 가 docstring 우회 차단 + space enum 검증). 신설 scope 없음 — PLAN 의 acceptance_criteria 정합 강화.

## Issues Encountered

- Initial 단순 substring 기반 drift defense test (test_torso_scale_is_not_used_as_denominator) 가 정당한 docstring 까지 차단 → AST 기반 docstring strip helper 로 재설계. 정책 강제와 docs 정합 양립 박제.

## Verification Evidence

- **Test count:** 18/18 phase08 test PASS (4 pole_geometry contract + 4 lockstep + 7 body_scale + 3 preflight).
- **Regression:** phase06 + phase07 244 PASS + 1 skipped (회귀 0).
- **TS strict mode:** `cd app && npx tsc --noEmit` exit 0.
- **3-way contract lockstep:** TS analysis.ts (PoleLine2D / PoleAxisMeasurement / CoordinateSpace / ContactPrimitiveKind) ↔ Python pole_geometry.py (5 field mirror) ↔ docs §9.0 (7 subsection + 12 contact 분류 표) 정합 — test_ts_python_field_camel_snake_mirror PASS.
- **PoleAxis 본체 변경 0:** pose_frame.py 변경 0 (Phase 1 lockstep 회귀 0).
- **drift defense:** body_scale.py 본체 실행 코드 안 BodyNormalizationProfile 영구 차단 — AST gate + import gate 양방향 검증.

## User Setup Required

None — 본 plan 은 contract + test infra + spec docs 박제만. belle 의 운영 작업 (preflight CSV 25 row 채우기) 은 Plan 08-02/08-03 의 Layer 1 산출 후 진입.

## Next Phase Readiness

**Plan 08-01 진입 시그널 — contract dependency 해소 완료:**

- ForceSignalsReport schema 박제 시 본 plan 의 §9.0 (CoordinateSpace + ContactPrimitiveKind + PoleAxisMeasurement) 위에 박제.
- AxisDeviationMetric 의 distance 필드 = coordinate_space='image_2d' (line 가용 시) / 'unavailable' (line 미가용 시) 박제.
- ContactStabilityMetric 의 12 contact entry 가 ContactPrimitiveKind 분류 yaml 박제 시 본 plan 의 §9.0.7 표 참조.
- expected_contact_points yaml 박제 시 kind 필드 동행 강제 (Plan 08-00 의 ContactPrimitiveKind enum 정합).

**Plan 08-02 진입 시그널:**

- compute_axis_deviation / compute_contact_stability 의 distance denominator = `median_torso_length(pose_frames, space='image_2d')` 직접 호출. BodyNormalizationProfile.torso_scale 사용 영구 금지 정책 정합.
- Layer-1 5-phase 산출 함수의 confidence 박제 source = Plan 08-03 의 pre-flight gate 결과 (PASS → 'medium' / FAIL → 'low').

**Plan 08-03 진입 시그널:**

- manual checkpoint 가 본 plan 의 PREFLIGHT-LABEL-SPEC.md §6 unwind path 정합 — RECOGNIZER_BACKEND + FORCE_SIGNALS_LAYER2_ENABLED env unset 박제.
- belle 가 preflight_label_template.csv 25 row 채워 PASS/FAIL 판정 후 Layer 1 confidence 박제 source 박제.

**No blockers** — Wave 1 (Plan 08-01) 진입 가능.

## Threat Flags

본 plan 의 threat surface scan 결과 신규 surface 0 — contract + test infra + spec docs 박제만. preflight_label_template.csv = video_id (reference 식별자) + motion_id + phase + timestamp_ms 만 박제, 사용자 영상 path / PII 박제 X (T-08-00-04 = accept 정합).

## Self-Check: PASSED

- `backend/shared/python/sunity_shared/analysis/pole_geometry.py` — FOUND
- `backend/shared/python/sunity_shared/analysis/body_scale.py` — FOUND
- `backend/tests/phase08/__init__.py` / `conftest.py` / `fixtures/__init__.py` / `fixtures/_factory.py` — FOUND (4)
- `backend/tests/phase08/test_pole_geometry_contract.py` / `test_body_scale_helper.py` / `test_preflight_label_schema.py` — FOUND (3)
- `.planning/phases/08-jerk-jitter/preflight/PREFLIGHT-LABEL-SPEC.md` / `preflight_label_template.csv` — FOUND (2)
- `app/src/types/analysis.ts` modified with PoleLine2D / PoleAxisMeasurement / CoordinateSpace / ContactPrimitiveKind — VERIFIED
- `docs/contract.md` §9.0 신설 with 7 subsection + 12 contact 표 — VERIFIED
- Commits: `2261dc5` / `928c6d4` / `80c353e` — FOUND (`git log --oneline -4 HEAD` 확인)
- 18 phase08 test PASS + 244 phase06/07 회귀 0 — VERIFIED
- TS strict (`cd app && npx tsc --noEmit`) exit 0 — VERIFIED

---

*Phase: 08-jerk-jitter*
*Plan: 00*
*Completed: 2026-06-09*
