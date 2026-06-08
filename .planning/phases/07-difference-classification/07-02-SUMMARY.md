---
phase: 07-difference-classification
plan: 02
subsystem: backend-analysis
tags: [classify-findings, pipeline-wiring, integration, camel-case, phase-07, frontend-normalize]
requires:
  - phase-07-01 (BodyComparisonFinding +4 / BodyComparisonReport +3 / copy_templates.py / Wave 0 fixtures)
  - phase-06 (compare_body_profiles / BodyComparisonReport schema lock)
provides:
  - classify_findings() pure function (D-07-A1 + D-07-A2 + Decision 1 + CR-01 + WR-03)
  - _resolve_joint_group() helper (CR-02 path)
  - _DEFICIT_TO_GROUP (5 entries) + _JOINT_TO_GROUP (12 entries) module-level
  - compare_body_profiles() Phase 7 wiring (classify_findings 1줄 + 4 신설 kwarg)
  - frontend userAnalyses.normalize() bodyComparisonReport 7 필드 null-guard (WR-02)
affects:
  - Phase 11 (CoachCommentHook + Cerebras coach_writer — interpretation / recommendation 입력 ready)
  - Phase 12 (실측 각도 + 키포인트 오버레이 — category 별 화면 분기 ready)
tech-stack:
  added: []
  patterns:
    - Phase 7 vertical slice 2/2 — Wave 0 인프라 (Plan 01) 위 단순 wiring
    - 새 dataclass 인스턴스 생성 패턴 (dataclasses.replace 우회 — frozen __post_init__ 정합)
    - immutable normalize() compat layer (TS strict mode + React 19)
key-files:
  created:
    - backend/tests/__init__.py
    - backend/tests/phase07/test_classify_findings.py
    - backend/tests/phase07/test_classify_findings_preserves_measurement_fields.py
    - backend/tests/phase07/test_compare_body_profiles_phase7_integration.py
    - backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py
    - .planning/phases/07-difference-classification/07-deferred-items.md
  modified:
    - backend/shared/python/sunity_shared/analysis/body_normalizer.py
    - app/src/lib/userAnalyses.ts
key-decisions:
  - D-07-A1 적용: |deduction_score| <= 0.2 → body_type_allowed (CATEGORY_GATE = 0.2)
  - D-07-A2 적용: confidence < 0.5 → uncertain demotion (CATEGORY_CONF_GATE = 0.5)
  - Decision 1 적용: uncertain → recommended_focus 통합 (분리 박스 추가 X)
  - D-07-C1 적용: phase = 'hold' 단일 (v2 Phase 8 / Plan 13 확장)
  - iteration 2 CR-01 fix: render_finding_copy(used_reference_fallback=True) thread
  - iteration 2 WR-02 fix: frontend normalize() null-guard (iteration 1 B1 retract)
  - iteration 2 WR-03 fix: recommended_focus_fallback 박제 (_EMPTY_FOCUS_FALLBACK)
  - iteration 2 INF-01 fix: behavioral primary preserve test (AST grep = secondary)
  - Deviation Rule 3: backend/tests/__init__.py 신설 — pre-existing import gate fix
  - Deviation Rule 1: AST grep gate 가 docstring false positive — ast.get_docstring 패턴
requirements-completed: [PERS-01]
metrics:
  duration: 25 min
  completed: 2026-06-08
  tasks: 3
  files: 7
---

# Phase 7 Plan 2: 차이 분류 본체 (classify_findings + wiring + normalize fix) Summary

Phase 7 vertical slice (2/2) — `classify_findings()` pure function 박제 + `compare_body_profiles()` wiring + integration test + camelCase 자동 변환 test + frontend `userAnalyses.normalize()` WR-02 retract B1 mini-fix. Plan 01 의 schema + canned 카피 + Wave 0 인프라 위에서 분류 함수 본체 단일 plan 완료. iteration 2 cross-AI review fix 4 finding (CR-01 / WR-02 / WR-03 / INF-01) 모두 mitigation.

## Execution Stats

- **Started:** 2026-06-08T11:00:00Z (approximate)
- **Completed:** 2026-06-08T11:25:00Z (approximate)
- **Duration:** 25 min
- **Tasks:** 3 / 3 complete
- **Files:** 7 (6 created + 2 modified)
- **Commits:** 3 (Task 1 / Task 2 / Task 3 atomic)
- **Tests:** 18 new (phase07 Plan 02 신설) + 90 existing (phase07 Plan 01) + 136 existing (phase06) PASS, 1 skipped

## Commits

| Task | Type | Commit | Files | Description |
|---|---|---|---|---|
| Task 1 | feat | `2aedb84` | 4 (1 mod + 3 created) | classify_findings + mapping dicts + 12 unit tests + tests/__init__.py fix |
| Task 2 | feat | `4851a43` | 3 (1 mod + 2 created) | compare_body_profiles wiring + 6 integration/camelCase tests |
| Task 3 | fix | `8559c6f` | 1 modified | WR-02 retract B1 — userAnalyses.normalize() 7 필드 null-guard |

## 신설 박제 위치

### body_normalizer.py — Module-level 박제 순서 (ORDER_OK)

| 박제 | 위치 (line) | 근거 |
|---|---|---|
| `_DEFICIT_TO_GROUP` (5 entries) | line 958 | CR-02 — clean_lines 제외 |
| `_JOINT_TO_GROUP` (12 entries — arm/leg) | line 967 | CR-02 정합 |
| `def _resolve_joint_group(finding)` | line 985 | CR-02 path — clean_lines + joint_key=None → "global" |
| `def classify_findings(...)` | line 1000 | D-07-A1 + D-07-A2 + Decision 1 + CR-01 + WR-03 |

import 추가: `from .copy_templates import _EMPTY_FOCUS_FALLBACK, render_finding_copy` (body_normalizer.py:91)

### body_normalizer.py — compare_body_profiles() wiring

| 박제 | 위치 (line) | 내용 |
|---|---|---|
| classify_findings 1줄 wiring | line 1503 | measure_ipsf_absolute_deficits() 호출 직후 — `classified_findings, do_not_over_correct, recommended_focus, recommended_focus_fallback = classify_findings(...)` |
| BodyComparisonReport 조립 4 신설 kwarg | line 1531-1539 | findings=classified_findings + do_not_over_correct + recommended_focus + recommended_focus_fallback |

### app/src/lib/userAnalyses.ts — WR-02 fix

- normalize() 안 immutable pattern 박제 (line 47~ 부근). bodyComparisonReport 존재 시 spread + map 으로 신설 7 필드 default. TS strict 정합.

## Test Results

### 18 신규 phase07 tests (Plan 02 신설)

| 파일 | tests | 결과 |
|---|---|---|
| `test_classify_findings.py` | 11 (10 분류 + AST grep convention + import gate) | PASS |
| `test_classify_findings_preserves_measurement_fields.py` | 1 (INF-01 primary behavioral) | PASS |
| `test_compare_body_profiles_phase7_integration.py` | 4 (classified findings + dnoc + rec + WR-03 fallback) | PASS |
| `test_dataclass_to_camel_case_dict_phase7.py` | 2 (7 신설 필드 + fallback None) | PASS |
| **합계** | **18 PASS** | OK |

### phase07 통합 (Plan 01 + Plan 02)

| 검증 | 결과 |
|---|---|
| `pytest tests/phase07/ -x` | **108 PASS** (Plan 01 90 + Plan 02 18) |
| `pytest tests/phase06/ -x` | **136 PASS + 1 skipped** (회귀 0) |
| `cd app && npx tsc --noEmit` | exit 0 (TSC_CLEAN) |
| ORDER_OK module-level 박제 순서 | `_DEFICIT_TO_GROUP < _JOINT_TO_GROUP < _resolve_joint_group < classify_findings` |
| AST grep `dataclasses.replace` 0회 | PASS (docstring 제외, body_nodes 만 검사) |

## iteration 2 cross-AI review fix mitigation 위치

| Finding | Severity | Mitigation 위치 |
|---|---|---|
| **CR-01** — render_finding_copy(used_reference_fallback) thread | Critical | `body_normalizer.py:classify_findings::is_mode3_first_fallback` (line 1057 부근) + `render_finding_copy(..., used_reference_fallback=is_mode3_first_fallback)` (line 1085 부근) + fixture #6 exact match (test_classify_findings.py::test_uncertain_when_mode3_first_fallback) |
| **WR-02** — frontend userAnalyses.normalize null-guard | Warning | `app/src/lib/userAnalyses.ts::normalize()` line 47-60 부근 — immutable spread + map 패턴. iteration 1 의 B1 retract 명시 (commit 메시지 `WR-02 retract B1`). |
| **WR-03** — recommended_focus_fallback 박제 | Warning | `body_normalizer.py:classify_findings` line 1119 부근 (`recommended_focus_fallback = _EMPTY_FOCUS_FALLBACK if not recommended_focus else None`) + test_recommended_focus_fallback_populated_when_empty + test_compare_body_profiles_emits_recommended_focus_fallback_when_empty |
| **INF-01** — behavioral preserves test (primary safety) | Info | `backend/tests/phase07/test_classify_findings_preserves_measurement_fields.py` (1 test) — 6 원본 측정 필드 input → output 정확 일치 + 신규 4 필드 박제 + id 다름 |

## Phase 7 ROADMAP 4 success criteria 달성 매핑

| SC | 내용 | 달성 위치 (Plan 01 + Plan 02) |
|---|---|---|
| SC #1 | category 별 산출 | classify_findings 10 분류 test (Plan 02) + integration 4 test (Plan 02) + Plan 01 23 lockstep test |
| SC #2 | doNotOverCorrect / recommendedFocus 출력 | test_compare_body_profiles_emits_do_not_over_correct + test_compare_body_profiles_emits_recommended_focus + WR-03 fallback (Plan 02) |
| SC #3 | confidence < 0.5 → uncertain demotion | test_uncertain_when_finding_low_confidence + test_uncertain_when_report_low_confidence (Plan 02) |
| SC #4 | 금지 표현 grep gate | Plan 01 test_copy_templates_no_forbidden.py 10 parametrize (이미 PASS) |

## Phase 7 cumulative 단위 test 커버리지

| 카테고리 | Plan | 파일 | tests |
|---|---|---|---|
| classify_findings 분류 룰 | 02 | test_classify_findings.py | 11 |
| INF-01 preserves | 02 | test_classify_findings_preserves_measurement_fields.py | 1 |
| compare_body_profiles 통합 | 02 | test_compare_body_profiles_phase7_integration.py | 4 |
| _dataclass_to_camel_case_dict 자동 | 02 | test_dataclass_to_camel_case_dict_phase7.py | 2 |
| AST grep gate (forbidden) | 01 | test_copy_templates_no_forbidden.py | 10 |
| render_finding_copy 렌더 | 01 | test_copy_templates_render.py | 40 |
| resolver coverage | 01 | test_copy_templates_resolver_coverage.py | 33 |
| 3-way lockstep + WR-01 placeholder | 01 | test_body_comparison_report_phase7_lockstep.py | 7 |
| **합계 (Phase 7 total)** | | | **108** |

## Deviations from Plan

### [Rule 3 — Blocker] backend/tests/__init__.py 신설

- **Found during:** Task 1 의 첫 pytest 실행
- **Issue:** `from tests.phase06.fixtures._factory import ...` 와 같은 import 가 `ModuleNotFoundError: No module named 'tests'` 로 실패. backend/tests/__init__.py 부재로 `tests` 패키지 marker 없음.
- **Fix:** `backend/tests/__init__.py` 빈 파일로 생성. 패키지로 인식 + import 정상 동작.
- **Files modified:** `backend/tests/__init__.py` (created)
- **Verification:** Phase 6 회귀 PASS 복구 (136 PASS + 1 skipped) — Plan 01 SUMMARY 의 "136 PASS" claim 환경 정합.
- **Commit:** `2aedb84` (Task 1 atomic 포함)

### [Rule 1 — Bug] AST grep gate docstring false positive

- **Found during:** Task 1 의 test_classify_findings_uses_replace_pattern_zero 첫 실행
- **Issue:** Plan 의 AST snippet (`ast.unparse(fn)` 전체) 가 classify_findings docstring 안의 한국어 주석 `"dataclasses.replace 우회 X"` 를 false positive 로 검출. AST grep gate 실패.
- **Fix:** ast.get_docstring 패턴 — 첫 body node 가 `ast.Expr(ast.Constant(str))` 이면 제거 + 실제 body_nodes 만 unparse 해서 검사. Plan 01 fcb4025 의 AST gate Assign+AnnAssign fix 패턴 정합.
- **Files modified:** `backend/tests/phase07/test_classify_findings.py`
- **Verification:** test PASS (12 PASS).
- **Commit:** `2aedb84` (Task 1 atomic 포함)

**Total deviations:** 2 auto-fixed (1 Rule 3 환경 blocker + 1 Rule 1 docstring false positive).
**Impact:** 둘 다 Plan 의 의도 정합. Plan 의 acceptance criterion 충족 + verify command 정합.

## Authentication Gates

None — plan executed without auth interaction.

## Self-Check: PASSED

### Files exist verification

- ✓ `backend/tests/__init__.py` (created, empty)
- ✓ `backend/tests/phase07/test_classify_findings.py` (created)
- ✓ `backend/tests/phase07/test_classify_findings_preserves_measurement_fields.py` (created)
- ✓ `backend/tests/phase07/test_compare_body_profiles_phase7_integration.py` (created)
- ✓ `backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py` (created)
- ✓ `.planning/phases/07-difference-classification/07-deferred-items.md` (created)
- ✓ `backend/shared/python/sunity_shared/analysis/body_normalizer.py` (modified)
- ✓ `app/src/lib/userAnalyses.ts` (modified)

### Commits verification (via git log)

- ✓ `2aedb84` Task 1 — classify_findings + 12 unit tests
- ✓ `4851a43` Task 2 — wiring + 6 integration / camelCase tests
- ✓ `8559c6f` Task 3 — WR-02 retract B1 frontend normalize

### Verification commands

- ✓ `pytest tests/phase07/ -x` → 108 PASS
- ✓ `pytest tests/phase06/ -x` → 136 PASS + 1 skipped (회귀 0)
- ✓ `cd app && npx tsc --noEmit` → exit 0
- ✓ CR-01 exact match → fixture #6 unprefixed 단일 문장 박제 + body_type_interpretation = None
- ✓ WR-02 retract B1 → commit `8559c6f` 메시지 포함
- ✓ WR-03 fallback → 빈 list 케이스 _EMPTY_FOCUS_FALLBACK + 채워진 케이스 None
- ✓ INF-01 → 6 원본 측정 필드 input → output 정확 일치 PASS
- ✓ AST grep dataclasses.replace 0회 (docstring 제외 body_nodes 만 검사) → PASS
- ✓ Module-level 박제 순서 ORDER_OK

### Deferred items

- See `.planning/phases/07-difference-classification/07-deferred-items.md` — pre-existing
  `tests/test_compare_engines_smoke.py::ModuleNotFoundError` (Phase 7 scope 밖, Plan 11
  research evaluation 영향).

## Known Stubs

None — Plan 02 의 classify_findings 가 Plan 01 의 6 placeholder uncertain 을
모두 재할당. measure_ipsf_absolute_deficits 의 emit 위치 placeholder 는 그대로
유지 (fail-safe — classify_findings 미통과 시에도 "AI 확신 부족" 으로 표시).

## Threat Flags

None — Phase 7 vertical slice (2/2) 가 새로운 trust boundary 또는 attack surface
도입하지 않음. classify_findings 는 pure function (numpy / boto3 / network / LLM
무관). frontend normalize() 의 null-guard 는 raw doc 정상화 layer — backend
W5 validator 와 별개.

## Next Step

**Phase 7 plans complete (2/2).** Ready for verify-work — 다음 진행:

1. `/gsd-verify-work 7` 실행 (Phase 7 close-out 검증).
2. Phase 7 close-out 후 Phase 8 (중심축·접촉점·jerk) 진입 — belle chain 2026-06-08:
   Phase 6 → 7 → **8** → 9 → 12 → 13.

Plan 07-02 산출 = Phase 11 (LLM 풍부화) + Phase 12 (실측 각도 + 키포인트 오버레이)
downstream 활용 ready — interpretation / recommendation / doNotOverCorrect /
recommendedFocus / recommendedFocusFallback 모두 backend → Firestore →
frontend 까지 lockstep 박제.
