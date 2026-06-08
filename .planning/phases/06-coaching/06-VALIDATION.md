---
phase: 6
slug: 06-coaching
status: ready-for-execute
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-08
updated: 2026-06-08 (post-Codex revision — R1-R10 반영, 17 effective task slots)
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 06-RESEARCH.md `## Validation Architecture` 박제 5 fixture + Wave 0 박제.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (`backend/requirements-dev.txt`) |
| **Config file** | `backend/pyproject.toml` (if absent — Wave 0 installs `[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest backend/tests/phase06 -x --tb=short` |
| **Full suite command** | `pytest backend/tests/phase06 -v` |
| **Estimated runtime** | ~20 seconds (pure numpy fixtures, no GPU/ffmpeg) |

---

## Sampling Rate

- **After every task commit:** Run quick command (above)
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite green + 5 fixture all pass
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

17 effective task slots across 3 plans (5 + 5 + 7). Each row mirrors a PLAN.md task's `<verify>` block.

| Task ID     | Plan  | Wave | Requirement | Threat Ref       | Secure Behavior                              | Test Type   | Automated Command                                                                              | File Exists | Status     |
|-------------|-------|------|-------------|------------------|----------------------------------------------|-------------|------------------------------------------------------------------------------------------------|-------------|------------|
| 06-01-01    | 06-01 | 1    | PERS-01     | T-06-01          | 6 fixture loadable + JSON valid (R5 추가)   | unit        | `cd backend && pytest tests/phase06/fixtures/test_fixtures_loadable.py -x`                     | ❌ Wave 0   | ⬜ pending |
| 06-01-02    | 06-01 | 1    | PERS-01     | —                | Kinematic Tree DAG + target_profile L_ref (C1) + BodyComparisonSourcePose dataclass (R2) + R10 회귀 | unit | `cd backend && pytest tests/phase06/test_body_normalizer_kinematic_tree.py -x`           | ❌ Wave 0   | ⬜ pending |
| 06-01-03    | 06-01 | 1    | PERS-01     | —                | confidence + foreshortening + dispersion R5 + 4채널 R6 | unit        | `cd backend && pytest tests/phase06/test_confidence.py -x`                                     | ❌ Wave 0   | ⬜ pending |
| 06-01-04    | 06-01 | 1    | PERS-01     | T-06-02          | IPSF 5 deficit (pose_reliability_low rename C14) + compare_body_profiles (extra_warnings R8 + source_keypoints R2) + 160cm vs 140cm | unit | `cd backend && pytest tests/phase06/test_ipsf_deficit.py -x`                  | ❌ Wave 0   | ⬜ pending |
| 06-01-05    | 06-01 | 1    | PERS-01     | T-06-SC          | 3-way contract lockstep (3 ComparisonType + usedReferenceFallback + pose_reliability_low + BodyComparisonSourcePose R2 + IPSF divergence note) | unit | `cd backend && pytest tests/test_contract_lockstep.py::test_body_comparison_report_lockstep -x`  | ❌ Wave 0   | ⬜ pending |
| 06-02-00    | 06-02 | 2    | PERS-01     | T-06-02-00       | TechniqueProfile.motion_id 끝 위치 R1 + Gemini 4 path keyword arg | unit | `cd backend && pytest tests/phase05/test_technique_profile_motion_id.py -x`                                  | ❌ Wave 0   | ⬜ pending |
| 06-02-01    | 06-02 | 2    | PERS-01     | T-06-02-01..06   | `_extract_video_analysis_inputs` 단일 helper R3 + non-null student_profile R4 + source pose fetch R2 + extra_warnings R8 + canary R9 | integration | `cd backend && pytest tests/phase06/test_pipeline_body_comparison.py -x` | ❌ Wave 0   | ⬜ pending |
| 06-02-02    | 06-02 | 2    | PERS-01     | T-06-02-04       | Firestore flat validator (W5 + list[str]/list[dict-scalar] 허용) | unit        | `cd backend && pytest tests/test_firestore_admin.py::test_validate_flat_dict_no_nested_array -x` | ❌ Wave 0   | ⬜ pending |
| 06-02-03    | 06-02 | 2    | PERS-01     | T-06-02-05       | camelCase wrapper (C8 4-case) + frontend normalize | unit        | `cd backend && pytest tests/test_pipeline_dataclass_camel_case.py -x && cd ../app && npm run typecheck` | ❌ Wave 0   | ⬜ pending |
| 06-02-04    | 06-02 | 2    | PERS-01     | T-06-02-06       | SAM build + 5 artifact 존재 검증 C15 + 통합 smoke (R2/R3/R4) | smoke       | `cd backend && sam build --use-container && pytest tests/phase06/test_pipeline_smoke.py -x`    | ❌ Wave 0   | ⬜ pending |
| 06-03-01    | 06-03 | 3    | PERS-01     | T-06-03-01       | `update_reference_body_data` atomic merge (R2 두 필드) + nested-array 차단 | unit        | `cd backend && pytest tests/test_firestore_admin.py::test_update_reference_body_data -x`       | ❌ Wave 0   | ⬜ pending |
| 06-03-02    | 06-03 | 3    | PERS-01     | T-06-03-02       | Pod GPU extract script — BodyNormalizationProfile + BodyComparisonSourcePose R2 산출 | manual+smoke| `python backend/scripts/extract_reference_body_profiles.py --dry-run --reference-id smoke` (Pod SSH 환경) | ❌ Wave 0 | ⬜ pending |
| 06-03-03    | 06-03 | 3    | PERS-01     | T-06-03-03       | seed script atomic merge 두 필드 R2 + R7 ordering (dry-run no init) | integration | `cd app && node scripts/seed-reference-body-profile.mjs --dry-run`                             | ❌ Wave 0   | ⬜ pending |
| 06-03-04    | 06-03 | 3    | PERS-01     | T-06-03-04       | dry-run 통합 검증 + R7 ADC-free 검증 (양 스크립트) | integration | `cd backend && pytest tests/phase06/test_backfill_scripts_dry_run.py -x`                       | ❌ Wave 0   | ⬜ pending |
| 06-03-4.5   | 06-03 | 3    | PERS-01     | T-06-03-4.5      | revert-reference-body-profile.mjs — 두 필드 모두 FieldValue.delete | integration | `cd app && node scripts/revert-reference-body-profile.mjs --dry-run --motion-ids smoke-test`   | ❌ Wave 0   | ⬜ pending |
| 06-03-05    | 06-03 | 3    | PERS-01     | T-06-03-SC       | belle Firestore Console verify — 두 필드 모두 박제 검증 | checkpoint  | Manual — belle Firestore Console 에서 5 reference doc 의 `bodyNormalizationProfile` + `bodyComparisonSourcePose` 두 필드 존재 + 형식 검증 | ⬜          | ⬜ pending |
| 06-03-06    | 06-03 | 3    | PERS-01     | (deferred)       | Pod sweep 사양 doc 박제 (C6 deferred, 실 sweep 별도 운영) | doc         | `[ -f .planning/phases/06-coaching/06-03-DEFERRED-POD-SWEEP.md ]`                              | ❌ Wave 0   | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*All "❌ Wave 0" entries become ✅ after Plan 06-01 Task 1 (6 fixtures + conftest + test infrastructure) completes.*

*Note: 06-02-00 (Phase 5 retro patch C2 + R1) runs first in Plan 06-02 — must complete before 06-02-01..04. 06-03 Tasks renumbered post-Codex revision (3.5→4, 3.6→4.5, 4→5, 5→6).*

---

## Wave 0 Requirements

5 fixture 박제 (RESEARCH.md `Validation Architecture` 박제 박제):

- [ ] `backend/tests/phase06/test_body_normalizer.py` — Kinematic Tree reproject 단위 테스트 (numpy only)
- [ ] `backend/tests/phase06/test_body_comparison_report.py` — schema 검증 + 3-way contract 일치
- [ ] `backend/tests/phase06/test_confidence.py` — bodyNormalizationConfidence temporal variance / spatial dispersion 산식
- [ ] `backend/tests/phase06/conftest.py` — 5 fixture 공통 헬퍼
- [ ] `backend/tests/phase06/fixtures/` — 5 fixture 박제:
  - `fixture_160cm_pro_vs_140cm_student.json` — 북극성 use case (D-06 우선 박제)
  - `fixture_lefty_vs_righty_twist.json` — IPSF Twist 박제 (감점 X)
  - `fixture_foreshortening_lying_pose.json` — shoulderHipRatio OFF 트리거
  - `fixture_unstable_arm_swing.json` — armScale temporal variance > 10%
  - `fixture_split_angle_hipline.json` — hip→knee vs toe→toe 위양성 박제

*No new framework install — pytest 8.x already in `backend/requirements-dev.txt`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 정은지 실측 영상 mode1 분석 (분석 정확도 검증) | PERS-01 | 실제 RunPod GPU + RTMW + Gemini 의존 — 단위 테스트 외 영역 | RunPod xbdkj1g2ylnfwi 에서 reference + 수강생 영상 1쌍 분석 → BodyComparisonReport.comparisonType == 'mode1' + bodyNormalizationConfidence 보고 + 정은지 41점 위양성 미발생 확인 |
| Firestore AnalysisDoc 통합 박제 (flat array 박제) | PERS-01 | Firestore 의 nested-array 금지 박제 ([[firestore-nested-array-flat]]) 위반 여부는 실 컬렉션 write 후 read 로만 검증 가능 | mode1 분석 1회 → Firestore console 에서 `bodyComparisonReport` 필드 형식 검증 (scaleRatios flat, findings flat) |
| 백필 스크립트 idempotent 박제 | PERS-01 | 운영 작업 — 동일 reference 2회 실행 시 동일 결과 박제 박제 | `node app/scripts/seed-reference-body-profile.mjs` 2회 연속 실행 → diff 0 박제 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (5 fixture + conftest)
- [ ] No watch-mode flags (`pytest -x` not `pytest --watch`)
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner fills task map + executor confirms all pass)

**Approval:** pending (planner fills task map → checker verifies → execute-phase runs Wave 0 first)
