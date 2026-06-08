---
phase: 7
slug: difference-classification
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-08
plans_emitted: ["07-01-PLAN.md", "07-02-PLAN.md"]
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `07-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 |
| **Config file** | `backend/requirements-dev.txt` + `backend/pytest.ini` (Phase 6 박제 정합) |
| **Quick run command** | `cd /Users/kimtaesung/Dev/SunityMotion && pytest backend/tests/phase07/ -x` |
| **Full suite command** | `cd /Users/kimtaesung/Dev/SunityMotion && pytest backend/tests/ -x` |
| **Estimated runtime** | ~10s phase07 격리 / ~30s 전체 backend |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/phase07/ -x` (Phase 7 격리)
- **After every plan wave:** Run `pytest backend/tests/ -x` (전체 phase06 136 + phase07 ~20 = ~156 pass / 1 skip)
- **Before `/gsd-verify-work`:** 전체 backend tests green + `tsc --noEmit` clean (3-way lockstep)
- **Max feedback latency:** ~10s (phase07 격리)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-T1 | 07-01 | 1 | PERS-01 | T-07-SC | N/A | infra | `python -c "import json; from pathlib import Path; d=Path('backend/tests/phase07/fixtures'); assert all((d/f).exists() for f in ['fixture_classification_allowed.json','fixture_classification_needs.json','fixture_classification_uncertain_raw.json','fixture_classification_uncertain_low_conf.json','fixture_classification_uncertain_global_low.json','fixture_classification_mode3_first_fallback.json'])"` | ❌ W0 (Plan 01 Task 1 creates) | ⬜ pending |
| 07-01-T2-grep | 07-01 | 1 | PERS-01 | T-07-02 | grep gate 9 forbidden phrases | unit | `pytest backend/tests/phase07/test_copy_templates_no_forbidden.py -x` | ❌ W0 (Plan 01 Task 2 creates) | ⬜ pending |
| 07-01-T2-render | 07-01 | 1 | PERS-01 | T-07-01 | render_finding_copy lookup + fallback | unit | `pytest backend/tests/phase07/test_copy_templates_render.py -x` | ❌ W0 (Plan 01 Task 2 creates) | ⬜ pending |
| 07-01-T3-lockstep | 07-01 | 1 | PERS-01 | T-07-03 | 3-way drift defense (TS/Python/contract) | unit | `pytest backend/tests/phase07/test_body_comparison_report_phase7_lockstep.py -x` | ❌ W0 (Plan 01 Task 3 creates) | ⬜ pending |
| 07-01-T3-tsc | 07-01 | 1 | PERS-01 | T-07-03 | TS interface 확장 type-check | unit | `cd app && npx tsc --noEmit` | ❌ pending Plan 01 | ⬜ pending |
| 07-02-T1-classify | 07-02 | 2 | PERS-01 | T-07-05 | classify_findings 분류 룰 + replace 우회 grep | unit | `pytest backend/tests/phase07/test_classify_findings.py -x` | ❌ W0 (Plan 02 Task 1 creates) | ⬜ pending |
| 07-02-T1-default-hold | 07-02 | 2 | PERS-01 | — | D-07-C1 v1 phase='hold' 단일 | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_phase_default_hold -x` | ❌ W0 (Plan 02 Task 1 creates) | ⬜ pending |
| 07-02-T1-aggregate | 07-02 | 2 | PERS-01 | — | do_not_over_correct + recommended_focus 분배 (D-07-B3 + Decision 1) | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_aggregate_lists_populated -x` | ❌ W0 (Plan 02 Task 1 creates) | ⬜ pending |
| 07-02-T1-low-conf | 07-02 | 2 | PERS-01 | — | confidence < 0.5 OR 합집합 demotion (D-07-A2 + D-07-U1) | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_uncertain_when_report_low_confidence backend/tests/phase07/test_classify_findings.py::test_uncertain_when_finding_low_confidence -x` | ❌ W0 (Plan 02 Task 1 creates) | ⬜ pending |
| 07-02-T1-mode3-fallback | 07-02 | 2 | PERS-01 | T-07-08 | Decision 1 — mode3_first + used_reference_fallback → 전체 uncertain | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_uncertain_when_mode3_first_fallback -x` | ❌ W0 (Plan 02 Task 1 creates) | ⬜ pending |
| 07-02-T2-integration | 07-02 | 2 | PERS-01 | — | compare_body_profiles wiring + Phase 6 fixture 재사용 | integration | `pytest backend/tests/phase07/test_compare_body_profiles_phase7_integration.py -x` | ❌ W0 (Plan 02 Task 2 creates) | ⬜ pending |
| 07-02-T2-camel | 07-02 | 2 | PERS-01 | T-07-06 | _dataclass_to_camel_case_dict 5-case 자동 변환 (Phase 6 C8 정합) | unit | `pytest backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py -x` | ❌ W0 (Plan 02 Task 2 creates) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Phase 7 SC → Test 매핑:**
- SC #1 (category 별 산출): 07-02-T1-classify (9 unit tests including all enum branches) + 07-02-T2-integration (Phase 6 fixture 재사용 검증)
- SC #2 (doNotOverCorrect / recommendedFocus 출력): 07-02-T1-aggregate + 07-02-T2-integration
- SC #3 (confidence < 0.5 → uncertain): 07-02-T1-low-conf + 07-02-T1-mode3-fallback (Decision 1 확장)
- SC #4 (금지 표현 grep gate): 07-01-T2-grep (9 parametrize — 6 research + 3 Sunity)

---

## Wave 0 Requirements

- [ ] `backend/tests/phase07/__init__.py` — phase07 디렉토리 표시 (Plan 01 Task 1)
- [ ] `backend/tests/phase07/conftest.py` — Phase 6 conftest 패턴 정합 (fixture loader) (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/_factory.py` — JSON → BodyComparisonFinding 로더 (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_allowed.json` — body_type_adjusted=True + deduction=-0.2 + conf=0.85 → category='body_type_allowed' (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_needs.json` — body_type_adjusted=True + deduction=-0.5 (pose_reliability_low) → category='needs_adjustment' (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_uncertain_raw.json` — body_type_adjusted=False → category='uncertain' (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_uncertain_low_conf.json` — finding.confidence=0.3 → category='uncertain' (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_uncertain_global_low.json` — body_normalization_confidence=0.3 → 전체 uncertain (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_mode3_first_fallback.json` — used_reference_fallback=True → 전체 uncertain (Decision 1) (Plan 01 Task 1)
- [ ] `backend/tests/phase07/test_classify_findings.py` — 9 단위 test (allowed/needs/uncertain × 3 + phase default + aggregate + replace grep) (Plan 02 Task 1)
- [ ] `backend/tests/phase07/test_copy_templates_no_forbidden.py` — 9 parametrize (6 research + 3 Sunity 금지) (Plan 01 Task 2)
- [ ] `backend/tests/phase07/test_copy_templates_render.py` — 21 카피 매핑 + 3 mode prefix + fallback (Plan 01 Task 2)
- [ ] `backend/tests/phase07/test_body_comparison_report_phase7_lockstep.py` — TS/Python 1:1 (4+2 필드) (Plan 01 Task 3)
- [ ] `backend/tests/phase07/test_compare_body_profiles_phase7_integration.py` — Phase 6 호출 + 분류 + 카피 통합 (Plan 02 Task 2)
- [ ] `backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py` — 신설 필드 자동 변환 (Plan 02 Task 2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| canned string 24 line 한국어 자연스러움 + 강사 톤 | PERS-01 SC #4 | 자연어 품질은 native speaker 검수 영역 (자동 검증 불가). 금지 표현 grep gate 는 자동, 톤 검수는 수동 | belle 가 plan 단계 + 실행 전 `copy_templates.py` 의 `_COPY_TEMPLATES` 21 항목 + 3 mode prefix 직접 검토. 어색한 표현/강사 톤 미정합 항목 수정. |
| 임계 0.2 의 실 영상 sweep 검증 | PERS-01 SC #1 | sweep_rtmw_20260603_1409 5 영상 + 정은지 mode1 분석 결과 0.2 / 0.3 / 0.4 동일 — but belle 가 final confirm 권장 (sweep 데이터 재산정 또는 새 영상 추가 시) | belle 가 `backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.md` 검토 후 임계 0.2 confirm (또는 0.3 / 0.4 조정 요청) |
| mode3_first fallback 카피 형식 검수 | PERS-01 SC #4 | "Page 9 절대 기준" mode prefix + uncertain demotion 결합 카피의 톤이 어색하지 않은지 | belle 가 mode3_first + used_reference_fallback=True 케이스의 실제 렌더링 출력 검토 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (15 항목 위 — Plan 01 박제 7 + Plan 02 박제 3 + 6 fixture JSON)
- [x] No watch-mode flags
- [x] Feedback latency < 10s (phase07 격리)
- [x] `nyquist_compliant: true` set in frontmatter (planner 가 plan 박제 + Wave 0 task 채움 완료 2026-06-08)

**Approval:** approved (planner 가 plan 박제 후 Task ID 채움 + Wave 0 / Wave N 매핑 완료 2026-06-08)
