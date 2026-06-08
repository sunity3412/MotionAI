---
phase: 7
slug: difference-classification
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-08
revised: 2026-06-08T16:00:00Z
revision_iteration: 2
revision_source: 07-REVIEW.md (cross-AI plan-risk review)
plans_emitted: ["07-01-PLAN.md", "07-02-PLAN.md"]
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `07-RESEARCH.md` §Validation Architecture + `07-REVIEW.md` (iteration 2 cross-AI plan-risk review).

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
- **After every plan wave:** Run `pytest backend/tests/ -x` (전체 phase06 136 + phase07 ~25 = ~161 pass / 1 skip)
- **Before `/gsd-verify-work`:** 전체 backend tests green + `tsc --noEmit` clean (3-way lockstep + WR-02 frontend mini-fix)
- **Max feedback latency:** ~10s (phase07 격리)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-T1 | 07-01 | 1 | PERS-01 | T-07-SC | N/A (CR-01 fixture #6 exact) | infra | `python -c "import json; from pathlib import Path; d=Path('backend/tests/phase07/fixtures'); files=['fixture_classification_allowed.json','fixture_classification_needs.json','fixture_classification_uncertain_raw.json','fixture_classification_uncertain_low_conf.json','fixture_classification_uncertain_global_low.json','fixture_classification_mode3_first_fallback.json']; assert all((d/f).exists() for f in files); d6=json.loads((d/'fixture_classification_mode3_first_fallback.json').read_text()); assert d6['expected']['recommendation']=='이 동작은 기준 영상이 없어, AI 가 IPSF 절대 기준만으로 분석했어요. 강사와 함께 확인 권유드려요.'"` | ❌ W0 (Plan 01 Task 1) | ⬜ pending |
| 07-01-T2-grep | 07-01 | 1 | PERS-01 | T-07-02 | grep gate 9 forbidden phrases (AST) | unit | `pytest backend/tests/phase07/test_copy_templates_no_forbidden.py -x` | ❌ W0 (Plan 01 Task 2) | ⬜ pending |
| 07-01-T2-render | 07-01 | 1 | PERS-01 | T-07-01 | render_finding_copy 33 lookup + fallback + CR-01 used_reference_fallback | unit | `pytest backend/tests/phase07/test_copy_templates_render.py -x` | ❌ W0 (Plan 01 Task 2) | ⬜ pending |
| 07-01-T2-resolver-coverage | 07-01 | 1 | PERS-01 | T-07-09 (CR-02 fix) | WR-04 — Phase 6 emit 패턴 6 × 3 category + 15 global keys coverage | unit | `pytest backend/tests/phase07/test_copy_templates_resolver_coverage.py -x` | ❌ W0 (Plan 01 Task 2 — WR-04 fix) | ⬜ pending |
| 07-01-T3-lockstep | 07-01 | 1 | PERS-01 | T-07-03 | 3-way drift defense (7 필드 — recommended_focus_fallback 포함 WR-03) | unit | `pytest backend/tests/phase07/test_body_comparison_report_phase7_lockstep.py -x` | ❌ W0 (Plan 01 Task 3) | ⬜ pending |
| 07-01-T3-tsc | 07-01 | 1 | PERS-01 | T-07-03 | TS interface 확장 type-check (recommendedFocusFallback 포함) | unit | `cd app && npx tsc --noEmit` | ❌ pending Plan 01 | ⬜ pending |
| 07-02-T1-classify | 07-02 | 2 | PERS-01 | T-07-05 | classify_findings 분류 룰 + CR-01 used_reference_fallback thread + WR-03 fallback + AST replace 우회 | unit | `pytest backend/tests/phase07/test_classify_findings.py -x` | ❌ W0 (Plan 02 Task 1) | ⬜ pending |
| 07-02-T1-preserves-fields | 07-02 | 2 | PERS-01 | T-07-05 | INF-01 fix — behavioral primary safety (6 원본 측정 필드 보존) | unit | `pytest backend/tests/phase07/test_classify_findings_preserves_measurement_fields.py -x` | ❌ W0 (Plan 02 Task 1 — INF-01 fix) | ⬜ pending |
| 07-02-T1-default-hold | 07-02 | 2 | PERS-01 | — | D-07-C1 v1 phase='hold' | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_phase_default_hold -x` | ❌ W0 (Plan 02 Task 1) | ⬜ pending |
| 07-02-T1-aggregate | 07-02 | 2 | PERS-01 | — | do_not_over_correct + recommended_focus 분배 (D-07-B3 + Decision 1) | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_aggregate_lists_populated -x` | ❌ W0 (Plan 02 Task 1) | ⬜ pending |
| 07-02-T1-low-conf | 07-02 | 2 | PERS-01 | — | confidence < 0.5 OR 합집합 demotion (D-07-A2 + D-07-U1) | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_uncertain_when_report_low_confidence backend/tests/phase07/test_classify_findings.py::test_uncertain_when_finding_low_confidence -x` | ❌ W0 (Plan 02 Task 1) | ⬜ pending |
| 07-02-T1-mode3-fallback | 07-02 | 2 | PERS-01 | T-07-08 (CR-01 fix) | CR-01 — recommendation = unprefixed 단일 카피 exact match + body_type_interpretation=None | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_uncertain_when_mode3_first_fallback -x` | ❌ W0 (Plan 02 Task 1) | ⬜ pending |
| 07-02-T1-empty-focus-fallback | 07-02 | 2 | PERS-01 | T-07-11 (WR-03 fix) | WR-03 — recommended_focus[] 빈 list 시 _EMPTY_FOCUS_FALLBACK 박제 | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_recommended_focus_fallback_populated_when_empty -x` | ❌ W0 (Plan 02 Task 1 — WR-03 fix) | ⬜ pending |
| 07-02-T2-integration | 07-02 | 2 | PERS-01 | — | compare_body_profiles wiring + Phase 6 fixture (3 base + 1 WR-03 fallback test) | integration | `pytest backend/tests/phase07/test_compare_body_profiles_phase7_integration.py -x` | ❌ W0 (Plan 02 Task 2) | ⬜ pending |
| 07-02-T2-camel | 07-02 | 2 | PERS-01 | T-07-06 | _dataclass_to_camel_case_dict 5-case 자동 변환 (7 신설 필드 incl recommendedFocusFallback) | unit | `pytest backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py -x` | ❌ W0 (Plan 02 Task 2) | ⬜ pending |
| 07-02-T3-normalize | 07-02 | 2 | PERS-01 | T-07-10 (WR-02 fix) | WR-02 — frontend userAnalyses.normalize() 안 bodyComparisonReport 4 필드 null-guard (iteration 1 B1 retract) | unit | `cd app && npx tsc --noEmit && grep -c "doNotOverCorrect" app/src/lib/userAnalyses.ts` | ❌ pending Plan 02 Task 3 (WR-02 fix) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Phase 7 SC → Test 매핑 (iteration 2 갱신):**
- SC #1 (category 별 산출): 07-02-T1-classify (10 unit tests incl. all enum branches) + 07-02-T1-preserves-fields (INF-01) + 07-02-T2-integration
- SC #2 (doNotOverCorrect / recommendedFocus 출력): 07-02-T1-aggregate + 07-02-T1-empty-focus-fallback (WR-03) + 07-02-T2-integration
- SC #3 (confidence < 0.5 → uncertain): 07-02-T1-low-conf + 07-02-T1-mode3-fallback (CR-01 Decision 1)
- SC #4 (금지 표현 grep gate): 07-01-T2-grep (9 parametrize — 6 research + 3 Sunity)

**Iteration 2 cross-AI review fix 매핑:**
- **CR-01** (mode3_first fallback unreachable): 07-01-T2-render (used_reference_fallback test) + 07-02-T1-mode3-fallback (recommendation exact match)
- **CR-02** (clean_lines resolver coverage gap): 07-01-T2-render (33 lookup) + 07-01-T2-resolver-coverage (WR-04 fix)
- **WR-01** (placeholder fail-open): Plan 01 Task 3 `category="uncertain"` placeholder (acceptance grep 검증)
- **WR-02** (frontend normalize): 07-02-T3-normalize
- **WR-03** (empty recommendedFocus UX): 07-02-T1-empty-focus-fallback + 07-02-T2-integration (1 추가 test)
- **WR-04** (resolver coverage): 07-01-T2-resolver-coverage
- **INF-01** (replace AST not core safety): 07-02-T1-preserves-fields (primary behavioral)

---

## Wave 0 Requirements (iteration 2 갱신)

- [ ] `backend/tests/phase07/__init__.py` (Plan 01 Task 1)
- [ ] `backend/tests/phase07/conftest.py` (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/_factory.py` (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_allowed.json` (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_needs.json` (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_uncertain_raw.json` (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_uncertain_low_conf.json` (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_uncertain_global_low.json` (Plan 01 Task 1)
- [ ] `backend/tests/phase07/fixtures/fixture_classification_mode3_first_fallback.json` — CR-01 fix exact match (Plan 01 Task 1)
- [ ] `backend/tests/phase07/test_classify_findings.py` — 10 단위 test (Plan 02 Task 1)
- [ ] **`backend/tests/phase07/test_classify_findings_preserves_measurement_fields.py` — INF-01 fix (Plan 02 Task 1)**
- [ ] `backend/tests/phase07/test_copy_templates_no_forbidden.py` — 9 parametrize (Plan 01 Task 2)
- [ ] `backend/tests/phase07/test_copy_templates_render.py` — 33 카피 매핑 + 3 mode prefix + fallback + CR-01 used_reference_fallback (Plan 01 Task 2)
- [ ] **`backend/tests/phase07/test_copy_templates_resolver_coverage.py` — WR-04 fix (Plan 01 Task 2)**
- [ ] `backend/tests/phase07/test_body_comparison_report_phase7_lockstep.py` — TS/Python 1:1 (4+3 필드 incl WR-03) (Plan 01 Task 3)
- [ ] `backend/tests/phase07/test_compare_body_profiles_phase7_integration.py` — 4 test (3 base + WR-03 fallback) (Plan 02 Task 2)
- [ ] `backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py` — 7 신설 필드 (Plan 02 Task 2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| canned string 36 line 한국어 자연스러움 + 강사 톤 (CR-02 fix 12 global keys 포함) | PERS-01 SC #4 | 자연어 품질은 native speaker 검수 영역. 금지 표현 grep gate 자동, 톤 검수 수동 | belle 가 plan 단계 + 실행 전 `copy_templates.py` 의 `_COPY_TEMPLATES` 33 항목 + 3 mode prefix + `_EMPTY_FOCUS_FALLBACK` 직접 검토. 어색한 표현 수정. |
| 임계 0.2 의 실 영상 sweep 검증 | PERS-01 SC #1 | sweep_rtmw_20260603_1409 5 영상 결과 0.2 / 0.3 / 0.4 동일 — belle final confirm 권장 | belle 가 `backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.md` 검토 후 0.2 confirm |
| mode3_first fallback 카피 형식 검수 (CR-01 fix) | PERS-01 SC #4 | unprefixed 단일 문장의 톤이 어색하지 않은지 (mode prefix 결합 X 결정) | belle 가 mode3_first + used_reference_fallback=True 케이스의 실제 렌더링 출력 검토. CR-01 fix path 정합. |
| recommended_focus_fallback 카피 (WR-03 fix) | PERS-01 SC #2 | "현재 영상에서 즉시 보정할 항목이 명확히 보이지 않아요" 단일 문장의 강사 톤 정합 검수 | belle 가 양질 영상 (pose_reliability_low 없음) 케이스의 결과 화면 검토 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (17 항목 위 — Plan 01 박제 9 + Plan 02 박제 4 + 6 fixture JSON)
- [x] No watch-mode flags
- [x] Feedback latency < 10s (phase07 격리)
- [x] `nyquist_compliant: true` set in frontmatter
- [x] **iteration 2 cross-AI review fix 7 finding 모두 test 박제** (CR-01 / CR-02 / WR-01 / WR-02 / WR-03 / WR-04 / INF-01)

**Approval:** approved (planner iteration 2 — cross-AI plan-risk review 7 finding mitigation 완료 2026-06-08)
