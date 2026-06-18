---
phase: 19-vision-hybrid
plan: 04
subsystem: pipeline
tags: [pipeline, display-score-parity, scoring-basis, vision-hook, contract-3way, tdd-green]

# Dependency graph
requires:
  - phase: 19-vision-hybrid (19-01 Wave 0)
    provides: RED suite for display-score parity + Mode3 gate + vision identity hook
  - phase: 19-vision-hybrid (19-02 Wave 1)
    provides: deduction aggregation (overall_from_dimensions min-of-core, contributesToOverall)
  - phase: 19-vision-hybrid (19-03)
    provides: 3D normalization
provides:
  - "_angles_to_dtw_median_dicts: display angles = score-source DTW path-aligned median (TRUST-01)"
  - "is_reference_free_motion + Mode3 4-value scoringBasis source labels (TRUST-03)"
  - "build_mode1 always-emit reference_motion basis (Mode1 전용, OPTIONAL contract)"
  - "build_mode3 4-value enum frozenset + backward-compat + reference_motion ValueError guard"
  - "_apply_vision_veto SAME-object identity hook (v2 거부권 슬롯, TRUST-05)"
  - "scoringBasis 3-way contract (analysis.ts + models.py + contract.md) + result header + modal basis/aux copy"
affects: [Phase 15 실증 live E2E]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Display-score source unification: 표시 각도가 per_joint_deviation 과 동일 DTW path/median"
    - "scoringBasis = 실제 채점 SOURCE 라벨 (Mode3 4-value enum; reference_motion=Mode1 전용)"
    - "is_reference_free_motion: angleSource/fixtureKey/ipsfCode/officialName (copyBranch 단독 분기 금지)"
    - "v1 vision hook = SAME-object identity (out is score_result, mutation 0); v2 mutation 도입 시 계약 전환"
    - "branch_info early single-lookup after recognize (중복 lookup 0)"

key-files:
  created: []
  modified:
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/analysis/assemble.py
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/app/analysis/result.tsx
    - app/src/components/DimensionDetailModal.tsx
    - backend/tests/test_pipeline_mode3.py
    - backend/tests/test_assemble.py

key-decisions:
  - "_angles_to_dtw_median_dicts(user_seg, ref_angles, joint_keys) 내부 DTW 재정렬 — 테스트 시그니처 정합, per_joint_deviation 과 동일 source"
  - "mode3-first user 표시 = dimensions._select_window hold-window median (extension_deviation 정합, drift 방지)"
  - "Mode3 scoringBasis = 정확히 4 값 frozenset; reference_motion 전달 시 ValueError (Mode1 전용 분리)"
  - "build_mode1 always-emit scoringBasis=reference_motion (OPTIONAL contract, legacy 호환)"
  - "test_unknown_move_gate motion_id ref-climb→ref-foxtop 수정 (ref-climb=branch1, branch2 recognized 케이스엔 ref-foxtop 필요)"

requirements-completed: [TRUST-01, TRUST-03, TRUST-05]

# Metrics
duration: ~50min
completed: 2026-06-18
---

# Phase 19 Plan 04: Pipeline Display-Score Parity + ScoringBasis Gate + Vision Hook Summary

**표시 각도를 점수 산출 DTW path-정렬 median 과 동일 source 로 통일(TRUST-01)하고, Mode3 미보유 동작에 실제 채점 SOURCE 기반 scoringBasis(4-value enum, reference_motion=Mode1 전용)를 화면에 노출(TRUST-03)하며, v2 비전 거부권을 위한 SAME-object identity hook(TRUST-05)을 박았다 — Wave 0 의 잔여 RED 7케이스 전부 GREEN, 가드 케이스 GREEN, phase-wide 회귀 0.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-06-18
- **Tasks:** 3
- **Files modified:** 9 (0 created, 9 modified)

## Accomplishments

- **Task 1 (TRUST-01 표시-점수 정합):** `_angles_to_dtw_median_dicts(user_seg, ref_angles, joint_keys)` 신설 — per_joint_deviation 의 DTW path 순회를 모방하되 abs-diff 가 아닌 양측 각도값을 관절별로 모아 finite median 2 dict 반환. MODE_EXPERT 표시 각도가 whole-clip nanmean(user matched-window vs ref full-clip 시간 비대칭) → DTW path-정렬 median 으로 교체. mode3-progress 도 동일 helper. mode3-first user 표시는 `_hold_window_median_dict`(dimensions._select_window 공유) 로 extension_deviation 과 동일 hold-window source.
- **Task 2 (TRUST-03/05 게이트 + hook):**
  - `assemble.is_reference_free_motion(branch_info)` — angleSource/angleFixtureKey/ipsfCode/officialName 으로 판정 (copyBranch 단독 분기 금지: 안전 기본과 실 branch2 가 copyBranch 동일값).
  - `build_mode3` 에 `scoring_basis`/`scoring_basis_label` 추가 — None 시 기존 dict 정확 보존(backward-compat), 전달 시에만 키 emit, `_MODE3_SCORING_BASES` frozenset(4값) 검증, `reference_motion` 전달 시 ValueError.
  - `build_mode1` 이 신규 doc 에 `scoringBasis="reference_motion"` + label 항상 emit (Mode1 전용, OPTIONAL contract).
  - pipeline: branch_info lookup 을 recognize 직후로 이동(coach_context/build_result/MODE_SELF 게이트 공유, 중복 lookup 0). `_mode3_comparison` 가 branch_info+is_first 로 Mode3 4값 scoringBasis 산출 (source-based, composite 포함).
  - `_apply_vision_veto(score_result, ...)` — v1 SAME-object identity (`out is score_result`, mutation 0), graceful boundary, build_result 직후 wiring. v2 본체 DEFERRED.
  - reference-free 트랙 dimensionScores = line+stability 만 (absolute_dimension_scores 그대로; posture 점수 차원 아님, ABSOLUTE_DIMENSIONS 불변).
- **Task 3 (TRUST-03 3중 계약 + 가시화):**
  - analysis.ts: Mode1Comparison OPTIONAL `scoringBasis?: 'reference_motion'` + label; Mode3Comparison 4-value scoringBasis union (reference_motion 부재) + label.
  - models.py: `MODE1_SCORING_BASIS` + `MODE3_SCORING_BASES`(4값) spec block.
  - contract.md: Mode1/Mode3 scoringBasis 섹션 + Mode3 4-value 테이블 (reference_motion 은 Mode1 전용 명시).
  - result.tsx: scoringBasisLabel 헤더 1줄 렌더 (graceful, theme 토큰).
  - DimensionDetailModal: reference-free 시 하드코딩 "세계 심사 기준" → basis 카피 + contributesToOverall===false 보조지표 안내.

## Task Commits

1. **Task 1: display-score parity via _angles_to_dtw_median_dicts (TRUST-01)** - `6449456` (feat)
2. **Task 2: branch_info gate + scoringBasis source labels + vision identity hook (TRUST-03/05)** - `f5e790b` (feat)
3. **Task 3: scoringBasis 3-way contract + result header + modal basis/aux copy (TRUST-03)** - `840f468` (feat)

## RED → GREEN evidence

Wave 0 잔여 RED 케이스 (`19-01-SUMMARY` 기준, mean/proportional/helper-absent 로 standalone fail) 가 이제 PASS:

**test_pipeline_mode3.py (11 passed)**
- `test_display_matches_score_source` — `_angles_to_dtw_median_dicts` 가 DTW path-정렬 median 산출, whole-clip nanmean 과 구분.
- `test_mode1_scoring_basis_reference_motion` — 직렬화 build_mode1 comparison.scoringBasis == "reference_motion" + label.
- `test_unknown_move_gate[4 params]` — first reference-free/recognized + progress known/reference-free 4값 정확 emit, reference_motion 미등장, is_reference_free_motion 판정 정합.
- `test_build_mode3_backward_compat` — basis 미전달 시 `{"mode":"mode3","isFirst":True}` EXACT; reference_motion → ValueError.
- `test_vision_hook_passthrough` — `_apply_vision_veto` SAME-object identity + mutation 0.

가드 케이스 GREEN: `test_first_analysis_absolute_only_no_delta` (scoringBasis 추가에 맞춰 계약 단언으로 갱신), `test_second_analysis_has_progress_delta_and_angle`, `test_same_video_is_consistent`, test_assemble.py 13개, test_kismam/test_dimensions/test_assemble_dimension_explanation 전부 GREEN.

## Verification evidence

- `pytest tests/test_pipeline_mode3.py tests/test_assemble.py tests/test_assemble_dimension_explanation.py tests/test_kismam.py tests/test_dimensions.py tests/test_anchor_known_answer.py` → **71 passed, 6 skipped** (real-video anchor pairs env-gated).
- `cd app && npm run typecheck` (`tsc --noEmit`) → **clean**.
- **Regression isolation (baseline diff):** 동일 ignore-set 으로 전체 backend suite 를 (a) 본 plan HEAD(840f468) 와 (b) 직전 커밋(7f2cb09) 에서 실행 비교 — baseline = **85 failed / 1474 passed**, 본 plan = **77 failed / 1482 passed**. 즉 **+8 GREEN, 신규 회귀 0**. 잔여 77 failures 는 전부 pre-existing(로컬 google/genai SDK 부재로 gemini/* + augment_low_confidence + spike 모듈 path) — 19-02-SUMMARY 의 격리 집합과 동일 범주.

## Grep gate evidence

- `is_reference_free_motion` body: copyBranch 참조 0 (angleSource/angleFixtureKey/ipsfCode/officialName 만).
- MODE_EXPERT 표시값 산출에 whole-clip `_angles_to_mean_dict`/`np.nanmean` 직접 호출 0 (DTW median helper 로 교체).
- `_MODE3_SCORING_BASES` frozenset = 정확히 4 값, reference_motion ∉ frozenset.
- 신규 추가 채점 경로에 `posture`/`DIM_POSTURE` dimensionScores 키 0; ABSOLUTE_DIMENSIONS 불변 = (DIM_LINE, DIM_STABILITY).
- analysis.ts Mode3Comparison.scoringBasis union = 4 리터럴, reference_motion ∉ union; Mode1Comparison.scoringBasis 유일 리터럴 = 'reference_motion'.
- models.py / contract.md: Mode3 허용값 = 4값, reference_motion row/value 없음, "5-enum" 표기 0 (negation 주석도 제거).
- `_apply_vision_veto` body: `return score_result` (copy/deepcopy 0).
- result.tsx / DimensionDetailModal: scoringBasisLabel + scoringBasis 분기 + contributesToOverall 분기 + "보조 지표" 카피 존재; 신규 라인에 hex 색/매직 px 0 (theme 토큰만).

## Calibration boundary (memory compliance)

본 plan 은 수치 calibration 없음 — display median/scoringBasis/vision-hook 은 구조 변경(표시 source 통일 + 라벨링 + 슬롯)이며 임계값 sweep/held-13-video fit 미사용 ([[scoring-redesign-must-generalize-no-overfit]], [[calibration-source-hard-gate]]).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test fixture] test_unknown_move_gate motion_id ref-climb → ref-foxtop**
- **Found during:** Task 2 (test 실행)
- **Issue:** 테스트가 "copyBranch 동일인데 is_reference_free 다름" 을 검증하려고 recognized motion_id 로 `ref-climb` 을 썼으나, motion_ipsf_map.json 에서 `ref-climb` = `branch1_ipsf_registered` (safe-default 의 `branch2_eunji_reference` 와 다름). 테스트의 `real_branch2.copyBranch == safe_default.copyBranch == "branch2_eunji_reference"` 단언이 데이터와 모순.
- **Fix:** recognized 케이스 motion_id 를 `ref-foxtop` 으로 교체 (copyBranch=branch2_eunji_reference + angleSource=eunji_measured_yaml + officialName 존재 → is_reference_free=False). 이로써 "copyBranch 동일인데 reference-free 판정 다름" 의도가 실제 데이터로 성립.
- **Files modified:** backend/tests/test_pipeline_mode3.py
- **Commit:** f5e790b

**2. [Rule 1 - Test contract] _mode3_comparison branch_info 인자 + scoringBasis always-emit 에 맞춘 테스트 갱신**
- **Found during:** Task 2
- **Issue:** (a) `_mode3_comparison` 가 동일 angles/profile 만으로는 first reference-free vs recognized 를 구분 불가 → branch_info 가 motion 인식 정보 single source. test_unknown_move_gate 호출에 `branch_info=branch` 전달. (b) `_mode3_comparison`/build_mode1 always-emit 으로 exact-dict 단언 깨짐 → `test_first_analysis_absolute_only_no_delta`(scoringBasis 계약 단언), `test_mode1_shape_and_clamp`(scoringBasis 추가), `test_mode1_segment_scores_included_only_when_given`(segment 유무 양쪽 basis 단언 ITER-5) 갱신. 새 계약에 직접 영향받는 케이스의 정당한 갱신.
- **Files modified:** backend/tests/test_pipeline_mode3.py, backend/tests/test_assemble.py
- **Commit:** f5e790b

## Known Stubs

None. `_apply_vision_veto` 의 v2 본체는 plan 이 명시한 DEFERRED 슬롯 (v1 = SAME-object identity, schema 변경 없음, _gemini_vision_enabled OFF 시 입력 그대로). 의도된 v2 거부권 슬롯이며 stub 아님 (계약/테스트로 identity 보장).

## Threat Flags

None. 내부 오케스트레이션/조립 순수함수 + 앱 표시 카피 + 3중 계약 변경만 — 신규 endpoint/auth/PII 표면 0. T-19-07/08/09/12/16/18/21 mitigate (scoringBasis source 라벨 + is_reference_free_motion + BRANCH2_FORBIDDEN_PHRASES + build_mode3 4-value ValueError 가드 + vision identity + line+stability 트랙 + Mode1 OPTIONAL 계약). T-19-SC accept (신규 패키지 설치 0).

## Deployment note

scoringBasis schema 키 추가 (Mode1Comparison + Mode3Comparison OPTIONAL) — **EAS 재빌드 + `sam build --use-container`** 필요 (새 옵셔널 키가 배포 pipeline + 앱에 흐르도록). Backward-compatible (OPTIONAL; legacy doc 미보유 시 UI graceful 미렌더).

## Self-Check: PASSED

- 9개 modified 파일 모두 disk 존재 확인.
- 3개 task 커밋 (6449456, f5e790b, 840f468) git history 존재 확인.
- Wave 0 잔여 RED 7케이스 GREEN; 가드 케이스 GREEN; tsc clean; baseline diff +8 GREEN / 회귀 0; grep gate 통과.

---
*Phase: 19-vision-hybrid*
*Completed: 2026-06-18*
