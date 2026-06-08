---
phase: 06-coaching
plan: 01
subsystem: backend-algorithm
tags: [body-normalization, kinematic-tree, ipsf-deficit, comparison-type, phase-06, contract-lockstep]
status: complete
requirements: [PERS-01]
dependency_graph:
  requires: [Phase 2 (BodyNormalizationProfile + measure_body_profile), Phase 5 (Gemini TechniqueProfile)]
  provides: [BodyComparisonReport schema, BodyComparisonSourcePose contract, normalize_pose_by_segments algorithm]
  affects: [Phase 6-02 (pipeline wiring), Phase 6-03 (reference backfill), Phase 7 (차이 분류), Phase 12 (오버레이), Phase 13 (보완 운동)]
tech_stack:
  added: []
  patterns: [pure-numpy adapter, frozen dataclass __post_init__ validator, 3-way contract lockstep, KINEMATIC_TREE_EDGES DAG, flat float array (Firestore nested-array 회피)]
key_files:
  created:
    - backend/shared/python/sunity_shared/analysis/body_normalizer.py
    - backend/tests/phase06/__init__.py
    - backend/tests/phase06/conftest.py
    - backend/tests/phase06/fixtures/__init__.py
    - backend/tests/phase06/fixtures/_factory.py
    - backend/tests/phase06/fixtures/_generate.py
    - backend/tests/phase06/fixtures/fixture_160cm_pro_vs_140cm_student.json
    - backend/tests/phase06/fixtures/fixture_lefty_vs_righty_twist.json
    - backend/tests/phase06/fixtures/fixture_foreshortening_lying_pose.json
    - backend/tests/phase06/fixtures/fixture_unstable_arm_swing.json
    - backend/tests/phase06/fixtures/fixture_split_angle_hipline.json
    - backend/tests/phase06/fixtures/fixture_high_dispersion_arms_sprawled.json
    - backend/tests/phase06/fixtures/test_fixtures_loadable.py
    - backend/tests/phase06/test_body_normalizer_kinematic_tree.py
    - backend/tests/phase06/test_body_normalizer_confidence.py
    - backend/tests/phase06/test_body_normalizer_ipsf_deficit.py
    - backend/tests/phase06/test_compare_body_profiles.py
    - backend/tests/phase06/test_body_comparison_report_lockstep.py
  modified:
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
decisions:
  - "D-06-A2 방향 B (프로 reference → 수강생 좌표계). 함수 이름 normalize_pose_by_segments 는 의미상 '평가 기준 위로 정렬'."
  - "C1 fix (review): normalize_pose_by_segments 시그너처 (source_keypoints, source_profile, target_profile, target_torso_px). L_ref 는 target (student) 의 segment ratio × target_torso_px. source_profile 은 R10 reserved 인자."
  - "C14 fix (review): deficit code bad_angle → pose_reliability_low rename. IPSF Page 21 의 judge-observation 'bad_angle' 과 의미 분리 — docs/contract.md §8.1 divergence note 신설."
  - "R2 fix (round-2): BodyComparisonSourcePose 신설 — Firestore reference 컬렉션의 reference 측 대표 hold frame keypoints 영속. flat values (4 × J = 68) + to_keypoints_array reshape. Plan 06-03 백필 contract source."
  - "R5 fix (round-2): spatial_dispersion_penalty 산식 자연화 = clip((C_s/sw - 1.5) / 1.5, 0, 1). high dispersion → high penalty (자연 방향). DISPERSION_BASELINE=1.5 / DISPERSION_RANGE=1.5."
  - "R6 fix (round-2): pose_frames → keypoints 변환은 to_coco17_array(pose_frames) (T,17,4) 4채널 보존. 자체 np.stack (T,17,3) 금지."
  - "R8 fix (round-2): compare_body_profiles(..., extra_warnings: list[str] | None) 파라미터 신설. caller-injected warnings 가 BODY_COMPARISON_WARNING_CODES frozenset 검증 통과. 우회 패턴 (dataclass replace) 금지."
  - "R9 fix (round-2): '7 deficits' 옛 표현 → '5 IPSF + 1 Sunity pose_reliability_low' 정정. poor_transitions v1.5 deferred (Phase 8 jerk/jitter 통합)."
  - "R10 fix (round-2): source_profile 인자는 reserved/debug. test_normalize_pose_by_segments_output_independent_of_source_profile 회귀 방지."
metrics:
  duration_minutes: ~75
  completed_date: "2026-06-08"
  tasks_total: 5
  tasks_completed: 5
  tests_total: 52
  tests_passed: 52
---

# Phase 6 Plan 01: 체형 정규화 비교 엔진 알고리즘 + Contract Lockstep — Summary

**One-liner:** Phase 6 의 algorithm 본체 + 3-way contract — Kinematic Tree Bone-Length Reprojection (C1 fix target-profile-based L_ref) + IPSF 절대 deficit (C14 rename pose_reliability_low) + confidence-tiered hybrid 산식 (R5 dispersion + R6 4채널) + BodyComparisonReport schema (W1 3 ComparisonType + usedReferenceFallback) + BodyComparisonSourcePose (R2 reference 영속) + TS/Python/docs §8/§8.2 atomic lockstep + 5 unit test 파일 (52 case PASS).

## Status

- Tasks executed: **5 / 5** (Wave 0 fixture → Wave 1 algorithm 본체)
- Tests: **52 / 52 PASS** (pytest backend/tests/phase06/)
- TypeScript: `tsc --noEmit` clean
- Commits: 5 atomic + 1 metadata
- Plan 06-02 진입 가능: pipeline wiring (mode1/mode3/Gemini fallback + Firestore complete_analysis 확장 + frontend normalize)

## Task 별 산출 + 검증

### Task 1 — Wave 0: 6 fixture + sanity test (commit `daa4e8b`)

신규 `backend/tests/phase06/fixtures/` 디렉토리:

- **fixture_160cm_pro_vs_140cm_student** — 30 frame each list (pro/student), scale_ratio 0.875. 북극성 use case 박제 (NotebookLM §1.4).
- **fixture_lefty_vs_righty_twist** — 10 frame Twist 자세 (어깨 +30° / 골반 -30°). IPSF 의도적 비대칭 요건 (Notebook §3.2).
- **fixture_foreshortening_lying_pose** — 15 frame, 어깨-골반 픽셀 거리 ~100px. OFF 조건 60°+150px 박제 (Notebook §1.5).
- **fixture_unstable_arm_swing** — 30 frame, 5 핵심 segment (upper_arm/forearm/thigh/shank/torso) 모두 swing — confidence 산출의 average path 트리거 (Notebook §4.2).
- **fixture_split_angle_hipline** — short/long_leg 각 15 frame. hip→knee 각도 동일, toe→toe Euclidean 다름. Split 위양성 회피 (Notebook §3.4).
- **fixture_high_dispersion_arms_sprawled (R5 fix 신규)** — 15 frame X자 자세. C_s / shoulder_width >= 3.0 보장. high dispersion → high penalty 자연 방향 검증용.

`_factory.py` = `pose_frame_from_dict` re-export + `load_paired_frames` helper. `_generate.py` = 합성 데이터 재현성 박제. `test_fixtures_loadable.py` 12 sanity smoke test PASS.

### Task 2 — body_normalizer.py 본체 (commit `12ed249`)

신규 모듈 `backend/shared/python/sunity_shared/analysis/body_normalizer.py` (pure numpy):

- **상수**: `KINEMATIC_TREE_EDGES` (13 edge DAG, mid_hip root), `CONFIDENCE_GATE=0.5`, `FORESHORTENING_ANGLE_DEG=60.0`, `SHOULDER_HIP_HARD_THRESHOLD_PX=150.0`, `TEMPORAL_VARIANCE_RATIO_THRESHOLD=0.10`, `DISPERSION_BASELINE=1.5`, `DISPERSION_RANGE=1.5` (R5 fix), `POSE_RELIABILITY_LOW_CONF_THRESHOLD=0.4`, `POSE_RELIABILITY_LOW_FRAME_RATIO=0.5` (C14 fix), `BODY_COMPARISON_WARNING_CODES` (8 enum frozen — R2 fix `reference_source_pose_missing` 포함).
- **ComparisonType**: `Literal["mode1", "mode3_first", "mode3_progress"]` (W1 — 3 cases 만).
- **ScaleProfile** (D-06-A3) — 5 numeric + `shoulder_hip_ratio_applied` bool. finite + strictly positive validator.
- **BodyComparisonSourcePose (R2 fix 신규)** — `joint_keys / values (flat 4 × J) / frame_index / torso_px / confidence / measured_at`. `__post_init__` length / finite / range validation. `to_keypoints_array() → (J, 4) ndarray`.
- **normalize_pose_by_segments (C1 fix)**: `(source_keypoints, source_profile, target_profile, target_torso_px, *, apply_shoulder_hip_ratio=True) → dict`. L_ref = `_ref_segment_ratio(parent, child, target_profile) × target_torso_px`. target = student. source_profile = R10 reserved (회귀 방지).
- **_ref_segment_ratio** helper — 13 edge ↔ 5 필드 매핑 + shoulder_hip_ratio OFF neutral 0.25 분기 (Phase 2 v5 회귀 안전망).

10 test PASS — kinematic tree 재투영 + DAG 검증 + split 위양성 회피 + segment-aware vs uniform scale (C1) + source_profile 독립성 (R10) + BCSP flat values + to_keypoints_array reshape (R2).

### Task 3 — confidence + foreshortening + temporal/spatial dispersion (commit `d9c50e1`)

- **is_foreshortening_detected**: 어깨-골반 vs 카메라 Z (60°) OR 픽셀 거리 (150px) 임계 (Notebook §1.5).
- **_compute_temporal_variance_per_segment**: 단일 segment normalized_variance + mean.
- **_compute_spatial_dispersion**: Notebook §4.2 B C_s / shoulder_width frame-wise. **R6 fix**: `to_coco17_array(pose_frames)` (T,17,4) 4채널 보존.
- **compute_body_normalization_confidence**: base = student_profile.confidence. 5 핵심 segment 평균 std/mean clip → temporal_penalty. **R5 fix**: `spatial_dispersion_penalty = clip((C_s/sw - 1.5) / 1.5, 0, 1)` — high dispersion → high penalty 자연 방향. reference_match_bonus = 0.1 × ref.confidence. clamp [0,1]. warnings: temporal_variance_high / spatial_dispersion_high / reference_profile_missing.

9 test PASS — foreshortening 검출 / 불안정 fixture conf < 0.5 / 안정 fixture conf >= 0.5 / clamp / pose_frames=None graceful / R5 high dispersion / R6 4채널 보존.

### Task 4 — IPSF deficit + compare_body_profiles 본체 (commit `116f400`)

- **BodyComparisonFinding** (frozen dataclass) — 6 필드. deficit_code 6 enum (5 IPSF + pose_reliability_low). confidence [0,1] validator. R9 fix '7 deficits' 표현 정정.
- **BodyComparisonReport** (frozen dataclass) — 9 필드. mode3_progress 시 previous_analysis_id 필수. used_reference_fallback 은 mode3_first 에서만 True 허용. **R8 fix**: 모든 warnings element 가 `BODY_COMPARISON_WARNING_CODES` 내 검증 (`__post_init__` 의 frozenset gate). 우회 (dataclass replace) 차단.
- **measure_ipsf_absolute_deficits**: 6 deduction (knee_toe_alignment / clean_lines / extension / posture / body_placement 각 -0.2 + pose_reliability_low -0.5). 체형 ratio 곱하지 않음 (Notebook §3.3 IPSF 절대). split = hip-knee-ankle 각도만 (Notebook §3.4 toe-to-toe 금지).
- **compare_body_profiles**:
  - confidence + foreshortening 산출 → apply_shoulder_hip_ratio 결정 (W6).
  - gate 조건: confidence ≥ 0.5 + reference_profile + source_keypoints 모두 있을 때만 정규화 ON. 하나라도 미충족 시 raw 비교 + low_confidence_normalization_off + (필요시 reference_source_pose_missing R2 fix).
  - 정규화 시 5 필드 ScaleProfile 산출 + normalize_pose_by_segments (C1 인자 순서) → measure_ipsf_absolute_deficits(normalized_keypoints, body_type_adjusted=True).
  - **R8 fix**: extra_warnings merge + frozenset validate. dedup preserve order.
  - **R2 fix**: source_keypoints 는 dict 또는 ndarray (J, ≥3) 자동 변환. caller (Plan 06-02) 가 `BodyComparisonSourcePose.to_keypoints_array()` 로 변환 후 전달.

14 test PASS — false positive 제거 / twist 무 shoulder_hip_ratio / split 무 toe-to-toe / W6 foreshortening / C14 rename / mode1 full report / low confidence fallback / W1 used_reference_fallback / mode3_progress prev required / R8 extra_warnings merge & reject / R2 source from BCSP.

### Task 5 — 3-way contract lockstep (commit `a444726`)

(A) `app/src/types/analysis.ts`:
- `ComparisonType` union (W1 — 3 cases).
- `ScaleProfile / BodyComparisonFinding / BodyComparisonReport / BodyComparisonSourcePose` interface (R2 fix).
- `AnalysisResult.bodyComparisonReport?` 신규 필드.
- `ReferenceMotion.bodyNormalizationProfile?` + `.bodyComparisonSourcePose?` 신규 필드.

(B) `backend/shared/python/sunity_shared/models.py`:
- `from .analysis.body_normalizer import BodyComparisonFinding, BodyComparisonReport, BodyComparisonSourcePose, ComparisonType, ScaleProfile` (R2 포함).
- Phase 6 D-06-B3 + C14 + R2 + R8 + R9 lockstep 헤더 명시.

(C) `docs/contract.md`:
- §8 BodyComparisonReport 신설 (ComparisonType union + ScaleProfile 6 필드 표 + BodyComparisonFinding deficit 6 enum 표 + BodyComparisonReport 9 필드 표 + 8 warning enum + D-06-U1 Universal Principle).
- §8.1 IPSF divergence note (C14 — pose_reliability_low vs bad_angle 의미 차이).
- §8.2 BodyComparisonSourcePose 신설 (R2 — 6 필드 + flat values + Firestore path + 백필 + read 경로).

(D) `backend/tests/phase06/test_body_comparison_report_lockstep.py` 7 test PASS — TS interface / Python re-export / docs §8/§8.1/§8.2 / camelCase ↔ snake_case 양방향 / W1 4번째 케이스 금지 / C14 bad_angle absent / R2 BCSP 3-way.

## Deviations from Plan

### None (plan executed exactly as written)

Plan 06-01 의 모든 task 가 plan 사양대로 진행. 다음 항목은 plan 의 acceptance criteria 와의 사소한 표현 차이로 인한 grep gate 충돌 — 의미적으로 동등하게 처리:

1. **[Rule 3 - 변경] grep gate 충돌 — "mode3_first_with_fallback" 부정 멘션**
   - **Found during:** Task 5 (final verification)
   - **Issue:** Plan 의 `grep -c "mode3_first_with_fallback" == 0` gate 가 prohibition note (W1 박제 — 4번째 케이스 금지) 의 negation 언급도 catch.
   - **Fix:** TS + docs 의 negation note 표현을 "mode3_first_with_fallback 같은 4번째" → "4번째 fallback 변형 케이스 금지" 로 reword. literal 부재 + 의미 보존.
   - **Files modified:** `app/src/types/analysis.ts`, `docs/contract.md`

2. **[Rule 3 - 변경] R8 grep gate 충돌 — "dataclasses.replace" 부정 docstring**
   - **Found during:** Task 4 final verification
   - **Issue:** Plan 의 `grep -v '^#' ... | grep -c "dataclasses.replace" == 0` gate 가 docstring 의 prohibition 언급 ("dataclasses.replace 우회 금지") 도 catch (docstring 은 `^#` 로 시작하지 않음).
   - **Fix:** docstring 표현을 "dataclasses.replace 우회 금지" → "우회 패턴 (dataclass replace helper) 금지" 로 reword. literal 부재 + 의미 보존.
   - **Files modified:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py`

3. **[Rule 3 - 변경] "pro_raw_keypoints" docstring 표현 변경**
   - **Found during:** Task 2 final verification
   - **Issue:** Plan 의 `grep -v '^#' ... | grep -c "pro_raw_keypoints" == 0` gate 가 historical 설명 docstring 도 catch.
   - **Fix:** docstring 의 historical legacy signature 설명을 "pro_raw_keypoints, pro_profile, student_target_torso_px" → "pro raw kpts + pro profile + student torso" 로 변경. 의미 보존.
   - **Files modified:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py`

위 3건은 모두 acceptance gate 정합을 위한 **문구 정리** — 알고리즘 / contract / 동작은 변경 없음.

### 4. fixture_unstable_arm_swing 의 swing 범위 확장

- **Found during:** Task 3 confidence test 작성 중.
- **Issue:** 초기 fixture 의 swing 이 upper_arm 만 적용 → 5 핵심 segment 평균이 임계 미달 (avg std/mean ≈ 2.4%).
- **Fix:** _generate.py 의 unstable swing 을 5 핵심 segment 모두 (upper_arm/forearm/thigh/shank/torso) 에 적용 → 평균 std/mean ≈ 8.8% → temporal_penalty ≈ 0.76 → confidence < 0.5.
- **Files modified:** `backend/tests/phase06/fixtures/_generate.py`, `fixture_unstable_arm_swing.json`.

## Plan 06-02 진입 시그널

Plan 06-01 산출이 **algorithm 본체 + dataclass + 3-way contract** 까지. Plan 06-02 책임:

1. **C2 + R1 fix retro Phase 5 patch**: TechniqueProfile.motion_id 필드 추가 (dataclass 맨 끝, default-after-non-default 회피) + Gemini recognizer populate + exact-match fallback.
2. **pipeline _process wiring** (R3 fix — `_extract_video_analysis_inputs` 단일 helper, RTMW 1회 실행 보장, R4 student_profile non-null).
3. **R2 wiring**: mode1 + mode3 fallback path 가 reference 의 `bodyComparisonSourcePose` 도 fetch → `_extract_target_torso_px` → `source_keypoints` 인자 전달. source_pose 미존재 시 warnings ⊃ 'reference_source_pose_missing' + confidence 하향 검증.
4. **R8 wiring**: extra_warnings injection (caller-side 'fallback_reference_not_found' 신호 주입). `dataclasses.replace` 우회 패턴 영구 금지 보장.
5. `firestore_admin.complete_analysis` 확장 + `_validate_flat_dict_no_nested_array` (W5).
6. frontend `userAnalyses.normalize` defensive validation (bodyComparisonReport 필드).
7. SAM Lambda Layer 빌드 smoke test.

Plan 06-02 진입 = Plan 06-03 (reference 백필) 와 **wave 분리 가능** — Plan 06-02 wiring + Plan 06-03 백필이 병행 wave 2/3.

## Known Stubs

(없음 — Plan 06-01 산출은 algorithm 본체. UI 노출은 Phase 12/12.5 책임.)

## Self-Check: PASSED

모든 created 파일 (17개) 존재 + commits (5개) git log 확인.

- 5 task commits: `daa4e8b` / `12ed249` / `d9c50e1` / `116f400` / `a444726`
- 6 fixture JSON + 6 algorithm/lockstep test 파일 + 1 SUMMARY.md
- pytest 52/52 PASS, tsc --noEmit clean
