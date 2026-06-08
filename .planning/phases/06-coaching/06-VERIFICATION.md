---
phase: 06-coaching
verified: 2026-06-08T00:00:00Z
status: human_needed
score: 4/4 must-haves verified (algorithm + production wiring); 1 operational backfill pending belle
overrides_applied: 0
human_verification:
  - test: "Pod GPU 측정 → 로컬 seed real-run → Firestore Console verify (Plan 06-03 Task 5 단계 1-7)"
    expected: "5 reference docs (ref-climb / ref-foxtop / ref-foxtop-split / ref-invert / ref-sideway-spin) 모두 bodyNormalizationProfile + bodyComparisonSourcePose 두 필드 포함. jointKeys length=17, values length=68, torsoPx>0, confidence in [0,1]"
    why_human: "RunPod SSH (xbdkj1g2ylnfwi) + Firebase ADC (sunity3412@gmail.com) + S3 reference 영상 read + 실 Firestore write 필요. Autonomous executor scope 외. 06-03-SUMMARY.md의 \"Checkpoint: Task 5 — belle 운영\" 섹션이 단계별 명령 + 기대 출력 + rollback path 모두 박제."
  - test: "Plan 06-03 Task 6 — Pod sweep validation (5 reference × 5 student 25 조합 normalization ON vs OFF 평균 reduction % 측정)"
    expected: "평균 reduction >= 50% PASS — NotebookLM §1.4 60% 주장 검증 (10% 오차)"
    why_human: "belle 운영 수집 student 영상 5개 + Pod GPU 25 조합 분석 일정. 06-03-DEFERRED-POD-SWEEP.md에 사양 박제. Phase 7 진입 hard-block X (observational)."
---

# Phase 6: 체형 정규화 비교 엔진 (coaching 모드) Verification Report

**Phase Goal:** 프로의 동작 성공 원리를 수강생의 신체 비율에 맞게 재계산해 비교한다 (`normalizeStudentPoseToProReference` 알고리즘) — 체형 차이로 인한 위양성 감점 제거
**Verified:** 2026-06-08T00:00:00Z
**Status:** human_needed (algorithm + production wiring 검증 완료, 운영 백필 belle 위임)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 프로/수강생 BodyNormalizationProfile 차이로 scale 프로파일이 산출되고 세그먼트별 상대 좌표가 재계산된다 | VERIFIED | `body_normalizer.py:1198-1227` ScaleProfile 5 필드 산출 (ratio = student/reference). `body_normalizer.py:400-525` `normalize_pose_by_segments` 가 13-edge Kinematic Tree 순회로 source 방향 단위벡터 + target_profile 비율 × target_torso_px 로 reproject. Tests: `test_kinematic_tree_reproject_pro_to_student_140cm`, `test_normalize_direction_b_target_scale_is_student` PASS |
| 2 | 단순 확대/축소가 아닌 세그먼트별 정규화 (`normalizeByBodySegments`)가 구현된다 | VERIFIED | `body_normalizer.py:400` `normalize_pose_by_segments`. `_ref_segment_ratio` (line 301-376) 가 edge별 5 필드 분리 매핑 (torso/arm/leg/shoulder_hip). `test_segment_aware_not_uniform_scale` PASS — 동일 height + 다른 arm/leg 비율 두 student의 normalized arm/leg 길이 5%+ 차이 검증 |
| 3 | 동일 동작에서 체형이 다른 두 사용자가 각자 체형 비율 기준의 점수를 받는다 (절대 각도 차이만으로 감점 X) | VERIFIED | `body_normalizer.py:901-1112` `measure_ipsf_absolute_deficits` — 5 IPSF GeometricCriterion (knee_toe_alignment / clean_lines / extension / posture / body_placement) + Sunity pose_reliability_low. `body_type_adjusted=True` 시 normalized_keypoints에서 측정 (raw 체형 차이 자체에 ratio 미곱). `test_pose_reliability_low_deficit_code_in_findings` + `test_full_pipeline_mode1_smoke` PASS |
| 4 | coaching 모드 출력에 `bodyNormalizationConfidence`가 항상 포함된다 | VERIFIED | `BodyComparisonReport.body_normalization_confidence: float` (required, non-Optional, line 841). `__post_init__` 가 0~1 range validate (line 852). `compute_body_normalization_confidence` (line 683) always returns confidence regardless of comparisonType. Pipeline `_process` (app.py:807/903/940) 가 3 comparisonType 모두 `compare_body_profiles` 호출 → confidence emit. `test_full_pipeline_all_must_haves_emitted` PASS |

**Score:** 4/4 truths verified (algorithm + production wiring level)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/shared/python/sunity_shared/analysis/body_normalizer.py` | Kinematic Tree reproject + ScaleProfile + BodyComparisonReport + BodyComparisonSourcePose + IPSF deficit + confidence | VERIFIED | 1297 LOC, all required dataclasses (ScaleProfile, BodyComparisonSourcePose, BodyComparisonFinding, BodyComparisonReport) + 4 functions (normalize_pose_by_segments, compute_body_normalization_confidence, measure_ipsf_absolute_deficits, compare_body_profiles) + 9-warning frozenset + KINEMATIC_TREE_EDGES (13) + module-load assert (WR-05) |
| `app/src/types/analysis.ts` | TS contract — BodyComparisonReport interface + ComparisonType + BodyComparisonSourcePose | VERIFIED | Lines 452-550 contain ComparisonType union (3 cases), ScaleProfile, BodyComparisonFinding, BodyComparisonSourcePose, BodyComparisonReport interfaces. `AnalysisResult.bodyComparisonReport` (line 193) + `ReferenceMotion.bodyNormalizationProfile` (line 276) + `ReferenceMotion.bodyComparisonSourcePose` (line 281) all wired. `npm run typecheck` exit 0 |
| `backend/shared/python/sunity_shared/models.py` | Python re-export of body_normalizer family | VERIFIED | Lines 141-146 re-export BodyComparisonFinding, BodyComparisonReport, BodyComparisonSourcePose, ComparisonType, ScaleProfile from `.analysis.body_normalizer` |
| `docs/contract.md` | §8 BodyComparisonReport + §8.1 IPSF divergence + §8.2 BodyComparisonSourcePose | VERIFIED | §8 (line 376-478): ComparisonType union, ScaleProfile table (6 fields), BodyComparisonFinding (6 fields), 6 deficit enum, BodyComparisonReport (9 fields), 9 warning enum (incl. WR-02 target_torso_px_missing). §8.1 IPSF divergence note. §8.2 BodyComparisonSourcePose (line 482-526) |
| `backend/functions/pipeline/app.py` | Production wiring — mode1/mode3_first/mode3_progress 3 분기 + compare_body_profiles 호출 + complete_analysis kwargs | VERIFIED | Lines 807 (mode1), 903 (mode3_first + Gemini fallback), 940 (mode3_progress) call `body_normalizer.compare_body_profiles(...)`. Lines 992-1001 pass body_comparison_report + body_normalization_profile to firestore_admin.complete_analysis. Helpers `_extract_target_torso_px` (3D, WR-04 fix), `_coerce_body_profile_dict` (CR-01/02 fix), `_coerce_source_pose_dict` (CR-03 fix), `_match_reference_by_motion_id` (C2) all present |
| `backend/shared/python/sunity_shared/firestore_admin.py` | complete_analysis(body_comparison_report=, body_normalization_profile=) + update_reference_body_data helper | VERIFIED | Line 126-170 `complete_analysis` 확장 (W5 validator 통과). Line 199-275 `update_reference_body_data(motion_id, body_profile, source_pose)` 단일 helper (R2) — 두 필드 atomic merge, 6 + 7 required field check, values length == 4 × jointKeys 강제 |
| `backend/tests/phase06/` | 5 fixture + 7+ algorithm test files | VERIFIED | 6 fixtures (incl. high_dispersion_arms_sprawled R5) + 19 test files: kinematic_tree, confidence, ipsf_deficit, compare_body_profiles, lockstep, integration_smoke, pipeline_body_comparison, firestore_admin_body_comparison, dataclass_to_camel_case_dict, backfill_scripts_dry_run, update_reference_body_data, edge_coverage, source pose, etc. |
| `backend/scripts/extract_reference_body_profiles.py` | Pod GPU 측정 스크립트 (R2 + C5 dry-run + W3) | VERIFIED | --help exit 0, --dry-run + --output + --motion-ids argparse, lazy import (imageio/rtmlib/boto3) for Mac local --help compat, BodyComparisonSourcePose payload 산출 |
| `app/scripts/seed-reference-body-profile.mjs` | Firebase Admin seed (R7 ordering — validate → dry-run early return → real-run) | VERIFIED | parseArgs + validate at line ≤152 (dryRun branch), initializeApp at line 176 (real-run). R7 PASS (dryRun line < initializeApp line). `node --check` exit 0. npm script `seed:body-profile` 등록 |
| `app/scripts/revert-reference-body-profile.mjs` | C12 safety-default revert (--commit 없으면 강제 dry-run) | VERIFIED | FieldValue.delete on 4 fields per motion. 안전 기본값 ("forcing --dry-run for safety"). npm script `revert:body-profile` 등록 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `app/src/types/analysis.ts BodyComparisonReport` | `backend/.../body_normalizer.py BodyComparisonReport` | 3-way contract — camelCase TS ↔ snake_case Python ↔ docs §8 atomic commit | WIRED | `test_body_comparison_report_lockstep.py` 7/7 PASS — TS interface ↔ Python dataclass ↔ docs/contract.md §8 양방향 검증 + BodyComparisonSourcePose lockstep + warnings 9-enum gate |
| `backend/.../models.py` | `backend/.../body_normalizer.py` | `from .analysis.body_normalizer import BodyComparisonReport, ...` | WIRED | Direct re-export line 141 |
| `backend/functions/pipeline/app.py _process` | `body_normalizer.compare_body_profiles` | 3 분기 (mode1/mode3_first/mode3_progress) 모두 호출 | WIRED | Lines 807, 903, 940 — 모두 compare_body_profiles 호출. test_pipeline_body_comparison.py 13 PASS |
| `pipeline _process` | `firestore_admin.complete_analysis(body_comparison_report=, body_normalization_profile=)` | _dataclass_to_camel_case_dict 변환 후 kwargs | WIRED | Lines 986-1001. `test_pipeline_firestore_integration.py` 5 PASS |
| `firestore_admin.complete_analysis` | Firestore AnalysisDoc | result.bodyComparisonReport + top-level bodyNormalizationProfile, _validate_flat_dict_no_nested_array 통과 | WIRED | firestore_admin.py:160-169. `test_firestore_admin_body_comparison.py` 10 PASS |
| Reference motion fetch | `BodyComparisonSourcePose.to_keypoints_array()` | mode1 + mode3 fallback 모두 fetch + source_keypoints 인자 전달 | WIRED | app.py:780-788 (mode1), 884-896 (mode3_first matched), 924-934 (mode3_progress prev) |
| `app/src/lib/userAnalyses.ts` | AnalysisDoc.result.bodyComparisonReport | TS type-only — Firestore raw → AnalysisDoc | WIRED | I2 positive assertion comment 박제 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `body_normalizer.compare_body_profiles` | scale_profile, findings, confidence | student_profile (`measure_body_profile` fallback non-null guaranteed) + reference_profile (Firestore reference doc) + pose_frames (RTMW estimate) | Yes — algorithm runs on real numpy + numpy inputs; pipeline computes real torso_px from pose_frames | FLOWING (algorithm) |
| `pipeline _process` body_comparison_report write | body_comparison_report_dict | _dataclass_to_camel_case_dict(compare_body_profiles 결과) | Yes — non-None when reference + source_pose both present; gracefully degraded warnings otherwise | FLOWING |
| Firestore reference docs (`reference/{motionId}`) — bodyNormalizationProfile + bodyComparisonSourcePose | reference body data | `update_reference_body_data` helper or seed script | **STATIC at backend code level** — production data not yet written. Plan 06-03 Task 5 backfill belle-pending. mode1 production path will emit `reference_profile_missing` / `reference_source_pose_missing` warnings + confidence-tiered fallback (정직한 graceful degradation, not silent failure) until backfill complete | DISCONNECTED-until-backfill (operational, not algorithmic) |

**Note on Level 4 — production data flow vs algorithmic data flow:** Algorithm + wiring code is FLOWING. The `reference/{motionId}` collection's two new fields will be populated by Plan 06-03 Task 5 backfill (belle operational checkpoint). Until then, the production wiring emits explicit `reference_source_pose_missing` warnings and confidence-tiered fallback per design (D-06-U1) — not silent failure. The algorithm tests verify behavior with real backfill data shapes via fixtures.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 6 full test suite | `python3 -m pytest tests/phase06/ -q` | 136 passed, 1 skipped | PASS |
| Phase 6 integration smoke (end-to-end pipeline mock) | `python3 -m pytest tests/phase06/test_phase06_integration_smoke.py -v` | 11 passed | PASS |
| Phase 6 lockstep (3-way contract drift defense) | `python3 -m pytest tests/phase06/test_body_comparison_report_lockstep.py -v` | 7 passed | PASS |
| Phase 6 algorithm core tests | `python3 -m pytest tests/phase06/test_body_normalizer_kinematic_tree.py tests/phase06/test_compare_body_profiles.py tests/phase06/test_body_normalizer_confidence.py -v` | 26 passed | PASS |
| App TypeScript typecheck | `cd app && npm run typecheck` | exit 0 (clean) | PASS |
| extract_reference_body_profiles.py --help (W3 lazy import gate) | `python3 backend/scripts/extract_reference_body_profiles.py --help` | exit 0 (per Plan 06-03 SUMMARY) | PASS |
| seed-reference-body-profile.mjs syntax | `node --check app/scripts/seed-reference-body-profile.mjs` | exit 0 (per Plan 06-03 SUMMARY) | PASS |
| revert-reference-body-profile.mjs syntax | `node --check app/scripts/revert-reference-body-profile.mjs` | exit 0 (per Plan 06-03 SUMMARY) | PASS |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| (no project probes — pytest is the canonical verification) | — | — | N/A |

Phase 6 declared no `scripts/*/tests/probe-*.sh` probes. The pytest suite (136 tests) + lockstep tests + integration smoke + TypeScript typecheck collectively serve as the verification gates. No probe execution needed.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|-------------|-------------|--------|----------|
| PERS-01 | 06-01, 06-02, 06-03 | 체형 정규화 비교 엔진(`normalizeStudentPoseToProReference`)이 프로의 동작 성공 원리를 수강생 신체 비율에 맞게 재계산하고 차이를 "체형 허용 / 개선 필요 / uncertain"으로 분류한다 — coaching 모드 정규화 ON | SATISFIED (Phase 6 portion) | Phase 6 가 PERS-01의 "체형 비율에 맞게 재계산" 부분을 완료 — body_normalizer 본체 + production wiring + Firestore 저장 path. "체형 허용 / 개선 필요 / uncertain" 분류는 Phase 7 책임 (ROADMAP 박제). REQUIREMENTS.md line 159은 `PERS-01: Phase 6, Phase 7 | Complete` — Phase 6 단독으로는 SATISFIED, 전체 close-out은 Phase 7 통합 후 |

No orphaned requirements detected.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none material to Phase 6 goal) | — | — | — | — |

**Scan summary:** Reviewed body_normalizer.py, pipeline/app.py (Phase 6 paths), firestore_admin.py, seed scripts, extract scripts, app/src/types/analysis.ts. No TBD/FIXME/XXX without issue references. The `del source_profile  # noqa: F841` (line 441) is intentional R10 fix (reserved/debug arg) with regression test `test_normalize_pose_by_segments_output_independent_of_source_profile`. The `assert target_torso_px is not None  # gate invariant` (line 1254) is intentional gate-invariant assertion (WR-02 fix). Hardcoded empty `[]` defaults in dataclass `field(default_factory=list)` are valid Python idioms for required-list fields (not stubs).

### Human Verification Required

1. **Plan 06-03 Task 5 — Live Firestore Backfill (belle operational)**
   - **Test:** Execute Pod GPU 측정 (`extract_reference_body_profiles.py`) → 로컬 다운로드 → seed dry-run (validate) → seed real-run → Firestore Console verify. 06-03-SUMMARY.md "Checkpoint: Task 5 — belle 운영" 섹션의 Step 1-7.
   - **Expected:** 5 reference motion docs (`ref-climb` / `ref-foxtop` / `ref-foxtop-split` / `ref-invert` / `ref-sideway-spin`) 모두 `bodyNormalizationProfile` + `bodyComparisonSourcePose` 두 필드 포함. `bodyComparisonSourcePose.jointKeys` length=17, `values` length=68 (= 4 × 17), `torsoPx > 0` + finite, `confidence ∈ [0,1]`. 5 doc 모두 동일 schema. Idempotent (재실행 회귀 0).
   - **Why human:** RunPod SSH (xbdkj1g2ylnfwi) + Firebase ADC (sunity3412@gmail.com) + 실 S3 reference 영상 read + 실 Firestore write 필요. Autonomous executor scope 외 (06-03-SUMMARY.md 박제). Rollback path는 `revert:body-profile --commit` (C12 안전 기본값 정합).

2. **Plan 06-03 Task 6 — Pod sweep validation (NotebookLM §1.4 60% reduction 검증)**
   - **Test:** belle 운영 sweep — 5 reference × 5 student 25 조합 normalization ON vs OFF, 평균 reduction % 측정. 06-03-DEFERRED-POD-SWEEP.md 사양 박제.
   - **Expected:** 평균 reduction >= 50% PASS (NotebookLM §1.4 60% 주장 검증, 10% 오차).
   - **Why human:** belle 운영 student 영상 5개 수집 + Pod GPU 25 조합 분석 일정 + 결과 분석. Phase 7 진입 hard-block X — observational (06-03-DEFERRED 박제). `feedback-analysis-first` + `mvp-simple-pilot-quality` 메모리 박제 정합.

### Gaps Summary

**No gaps blocking Phase 6 goal achievement at the code level.**

체형 정규화 비교 엔진의 알고리즘 본체 (`normalize_pose_by_segments`, `compute_body_normalization_confidence`, `measure_ipsf_absolute_deficits`, `compare_body_profiles`) + production wiring (`pipeline/app.py _process` 3 분기 + `firestore_admin.complete_analysis` 확장) + 3-way contract lockstep (TS / Python / docs §8 + §8.2) + 6 test fixtures + 19 test files (136 pass, 1 skip — documented) 모두 박제. Code review (10 findings) 의 3 Critical + 7 Warning 모두 commit 6449eca-ca6ed25 + 4003e11 에서 FIXED (REVIEW-FIX.md 박제).

**Only operational backfill of production reference data remains** — Plan 06-03 Task 5 belle 운영 작업으로 정직하게 위임됨 (autonomous scope 외, 06-03-SUMMARY.md "Checkpoint: Task 5" 섹션이 단계별 명령 + rollback path 박제). 백필 미완 상태에서는 production mode1 path가 `reference_source_pose_missing` warning + confidence-tiered fallback로 정직하게 graceful degrade (silent failure X, R2 canary 박제).

Phase 6 의 4개 success criteria 모두 codebase 에서 검증 가능 (4/4 VERIFIED). Algorithm 정확성 + 3-way contract drift defense + IPSF GeometricCriterion 절대 deficit + segment-aware reprojection + bodyNormalizationConfidence 무조건 emit 모두 single-source-of-truth tests 가 박제. ROADMAP §Phase 6 status는 `Complete | 2026-06-08` 박제 (line 444).

**Status decision rationale (Step 9 decision tree):**
- 4/4 truths VERIFIED, no FAILED artifacts, all key links WIRED, no blocker anti-patterns
- BUT 2 human verification items identified (Plan 06-03 Task 5 + Task 6, deferred per belle/autonomous scope 박제)
- Per decision tree rule: "passed is ONLY valid when the human verification section is empty"
- → **human_needed**

Plan 06-03 Task 5 의 backfill은 Phase 6 algorithm 박제와 별개의 운영 단계 — Phase 6 코드 산출은 운영 백필 부재 시에도 graceful (canary warnings + confidence-tiered fallback) — 박제 완료. belle approval (Firestore Console verify Step 6 통과) → Phase 6 전체 closure → Phase 7 진입 가능.

---

_Verified: 2026-06-08T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
