---
phase: 07-difference-classification
plan: 01
subsystem: backend-analysis
tags: [classification, canned-copy, schema-lockstep, phase-07, test-scaffold, iteration-2]
requires:
  - phase-06 (BodyComparisonReport schema lock + 6 BodyComparisonFinding emit positions)
provides:
  - BodyComparisonFinding +4 fields (category / phase / body_type_interpretation / recommendation)
  - BodyComparisonReport +3 fields (do_not_over_correct / recommended_focus / recommended_focus_fallback)
  - copy_templates.py module (33 canned templates + 3 mode prefix + render_finding_copy)
  - CATEGORY_GATE + CATEGORY_CONF_GATE module constants
  - Wave 0 test infrastructure (phase07/ + 6 fixture JSON + factory loader)
  - 3-way contract lockstep drift defense (7 new fields in TS + Python + docs §8 + §8.3)
affects:
  - Plan 07-02 (classify_findings + integration tests — Wave 0 infrastructure ready)
  - Phase 11 (CoachCommentHook + Cerebras coach_writer — interpretation/recommendation 입력)
  - Phase 12 (실측 각도 + 키포인트 오버레이 — category 별 화면 분기)
tech-stack:
  added: []
  patterns:
    - 3-way contract lockstep (Phase 6 a444726 atomic commit pattern)
    - AST-based grep gate for forbidden phrases (D-07-D2)
    - frozen dataclass + __post_init__ Literal enum validator (D-07-A1)
    - fail-safe placeholder pattern (WR-01 — Plan 02 reassigns)
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/copy_templates.py
    - backend/tests/phase07/__init__.py
    - backend/tests/phase07/conftest.py
    - backend/tests/phase07/fixtures/__init__.py
    - backend/tests/phase07/fixtures/_factory.py
    - backend/tests/phase07/fixtures/fixture_classification_allowed.json
    - backend/tests/phase07/fixtures/fixture_classification_needs.json
    - backend/tests/phase07/fixtures/fixture_classification_uncertain_raw.json
    - backend/tests/phase07/fixtures/fixture_classification_uncertain_low_conf.json
    - backend/tests/phase07/fixtures/fixture_classification_uncertain_global_low.json
    - backend/tests/phase07/fixtures/fixture_classification_mode3_first_fallback.json
    - backend/tests/phase07/test_copy_templates_no_forbidden.py
    - backend/tests/phase07/test_copy_templates_render.py
    - backend/tests/phase07/test_copy_templates_resolver_coverage.py
    - backend/tests/phase07/test_body_comparison_report_phase7_lockstep.py
  modified:
    - backend/shared/python/sunity_shared/analysis/body_normalizer.py
    - backend/shared/python/sunity_shared/models.py
    - app/src/types/analysis.ts
    - docs/contract.md
key-decisions:
  - D-07-A1: category 분류 룰 — body_type_adjusted + |deduction_score| 게이트 (CATEGORY_GATE = 0.2)
  - D-07-A2: uncertain demotion 게이트 — body_normalization_confidence 또는 finding.confidence < 0.5 (CATEGORY_CONF_GATE = 0.5)
  - D-07-B3: 카피 분배 룰 — body_type_allowed → doNotOverCorrect, needs_adjustment + uncertain → recommendedFocus
  - D-07-C1: v1 phase = 'hold' 단일 (v2 Phase 8 / Plan 13 확장 호환)
  - D-07-D1: 권장 톤 3종 (가능성 언어 / AI 보조 / 부위별 원인)
  - D-07-D2: 금지 표현 9 grep gate (AST 기반 — _COPY_TEMPLATES + _MODE_PREFIX iterate)
  - D-07-D3: mode prefix 는 recommendation 에만 prepend, interpretation 은 mode 무관
  - iteration 2 CR-01: render_finding_copy(used_reference_fallback=True) → unprefixed 단일 fallback
  - iteration 2 CR-02: 12 global keys 추가 (joint_key=None emit 4 deficit × 3 category)
  - iteration 2 WR-01: 6 emit positions 모두 category="uncertain" placeholder (fail-safe)
  - iteration 2 WR-03: recommended_focus_fallback + _EMPTY_FOCUS_FALLBACK 박제
  - iteration 2 WR-04: test_copy_templates_resolver_coverage.py 신설 (18 + 15 = 33 coverage)
  - Deviation R1: BodyComparisonFinding.category 에 default = "uncertain" 박제 — Phase 6 회귀 0 + WR-01 fail-safe 정합
requirements-completed: [PERS-01]
metrics:
  duration: 14 min
  completed: 2026-06-08
  tasks: 3
  files: 19
---

# Phase 7 Plan 1: 차이 분류 schema + canned copy + test scaffold Summary

Phase 7 vertical slice (1/2) — 3-way contract lockstep 으로 BodyComparisonFinding 에 4 필드 + BodyComparisonReport 에 2+1 필드 (WR-03 fallback 포함) 박제 + 신규 모듈 `copy_templates.py` 33 canned (CR-02 12 global 추가) + 9 금지 표현 AST grep gate + Wave 0 test 인프라 (6 fixture JSON) 박제 단일 plan 완료. iteration 2 cross-AI review fix 7 finding (CR-01/CR-02/WR-01/WR-03/WR-04) 모두 mitigation.

## Execution Stats

- **Started:** 2026-06-08T10:41:05Z
- **Completed:** 2026-06-08T10:55:40Z
- **Duration:** 14 min
- **Tasks:** 3 / 3 complete
- **Files:** 19 (15 created + 4 modified)
- **Commits:** 3 (Task 1 / Task 2 / Task 3 atomic)
- **Tests:** 90 new (phase07) + 136 existing (phase06) PASS, 1 skipped

## Commits

| Task | Type | Commit | Files | Description |
|---|---|---|---|---|
| Task 1 | test | `3e1fbf7` | 10 created | phase07/ infrastructure + 6 fixture JSON |
| Task 2 | feat | `fcb4025` | 4 created | copy_templates.py + 3 test files (83 tests) |
| Task 3 | feat | `d4d8af4` | 5 (4 modified + 1 created) | **SINGLE ATOMIC** 3-way lockstep + WR-01 placeholder |

## 신설 필드 박제 위치

### BodyComparisonFinding +4 필드 (D-07-A1 + D-07-C1)

| 필드 | Python 위치 | TS 위치 | docs |
|---|---|---|---|
| `category` | `body_normalizer.py:843` | `analysis.ts:503` | `contract.md §8 표 +4 행` |
| `phase` | `body_normalizer.py:844` | `analysis.ts:506` | `contract.md §8 표` |
| `body_type_interpretation` | `body_normalizer.py:845` | `analysis.ts:509` | `contract.md §8 표` |
| `recommendation` | `body_normalizer.py:846` | `analysis.ts:512` | `contract.md §8 표` |

### BodyComparisonReport +3 필드 (D-07-B3 + WR-03 fix)

| 필드 | Python 위치 | TS 위치 | docs |
|---|---|---|---|
| `do_not_over_correct` | `body_normalizer.py:880` | `analysis.ts:563` | `contract.md §8 BodyComparisonReport 표` |
| `recommended_focus` | `body_normalizer.py:881` | `analysis.ts:566` | `contract.md §8 BodyComparisonReport 표` |
| `recommended_focus_fallback` (WR-03) | `body_normalizer.py:882` | `analysis.ts:570` | `contract.md §8 BodyComparisonReport 표` |

### Module-level constants (D-07-A1 + D-07-A2)

| 상수 | 위치 | 값 | 근거 |
|---|---|---|---|
| `CATEGORY_GATE` | `body_normalizer.py:178` | `0.2` | D-07-A1 |
| `CATEGORY_CONF_GATE` | `body_normalizer.py:179` | `0.5` | D-07-A2 + D-06-U1 재사용 |

### docs/contract.md §8.3 신설 서브섹션

- Module-level 임계 상수 표 (CATEGORY_GATE / CATEGORY_CONF_GATE)
- 분류 결정 룰 표 (6 조건 → category)
- 카피 분배 룰 표 (3 category → 박스)
- 33 canned coverage 표 (CR-02 fix 12 global keys 명시)
- CR-01 fix used_reference_fallback path 명세 (unprefixed 단일 카피)
- 9 금지 표현 grep gate 표 + 권장 톤 3종 (D-07-D1)

## 33 Canned Coverage (CR-02 fix)

| deficit_code | joint_group | × 3 category |
|---|---|---|
| `knee_toe_alignment` | `leg` | 3 |
| `clean_lines` | `arm` | 3 |
| `clean_lines` | `leg` | 3 |
| `clean_lines` | `global` (CR-02 신규) | 3 |
| `extension` | `torso` | 3 |
| `extension` | `global` (CR-02 신규) | 3 |
| `posture` | `arm` | 3 |
| `posture` | `global` (CR-02 신규) | 3 |
| `body_placement` | `pole_axis` | 3 |
| `body_placement` | `global` (CR-02 신규) | 3 |
| `pose_reliability_low` | `global` | 3 |
| **합계** | | **33 카피** |

`_MODE_PREFIX` 3 항 (mode1 / mode3_first / mode3_progress) — recommendation 에만 prepend.

## Test Results

### 90 신규 phase07 tests

| 파일 | tests | 결과 |
|---|---|---|
| `test_copy_templates_no_forbidden.py` | 10 (9 forbidden parametrize + 1 AST sanity) | PASS |
| `test_copy_templates_render.py` | 40 (33 keys + 7 explicit) | PASS |
| `test_copy_templates_resolver_coverage.py` | 33 (18 emit pattern + 15 global keys) | PASS |
| `test_body_comparison_report_phase7_lockstep.py` | 7 (3-way drift defense + WR-01 placeholder) | PASS |
| **합계** | **90 PASS** | ✓ |

### Phase 6 회귀 0 (WR-01 fail-safe 정합)

| 검증 | 결과 |
|---|---|
| `pytest backend/tests/phase06/ -x` | 136 PASS + 1 skipped (W3 placeholder `category="uncertain"` 박제로 회귀 0) |
| `cd app && npx tsc --noEmit` | exit 0 |
| `pytest backend/tests/phase06/ + tests/phase07/` 통합 | 226 PASS + 1 skipped |

## iteration 2 cross-AI review fix mitigation 위치

| Finding | Severity | Mitigation 위치 |
|---|---|---|
| **CR-01** — render_finding_copy(used_reference_fallback) | Critical | `copy_templates.py:200-205` (시그너처 + early return path) + `fixture_classification_mode3_first_fallback.json` (exact match 박제) + `test_copy_templates_render.py:test_render_with_used_reference_fallback_returns_unprefixed_single_copy` |
| **CR-02** — 12 global keys 추가 | Critical | `copy_templates.py:124-159` (12 신규 global entries) + `test_copy_templates_resolver_coverage.py:test_all_joint_key_none_deficits_have_global_keys` + `contract.md §8.3 33 canned coverage 표` |
| **WR-01** — 6 emit positions placeholder | Warning | `body_normalizer.py:989+ category="uncertain"` (6 위치) + `test_body_comparison_report_phase7_lockstep.py:test_wr01_placeholder_six_emit_positions` |
| **WR-02** — TS userAnalyses.normalize null-guard | Warning | Plan 02 Task 3 에서 박제 (본 plan scope X — iteration 1 B1 retract 박제) |
| **WR-03** — _EMPTY_FOCUS_FALLBACK 상수 + recommended_focus_fallback 필드 | Warning | `copy_templates.py:67-70` (상수) + `body_normalizer.py:882` (필드) + `analysis.ts:570` (TS) + `contract.md §8` 표 |
| **WR-04** — test_copy_templates_resolver_coverage.py | Warning | `backend/tests/phase07/test_copy_templates_resolver_coverage.py` 신설 (33 cases all green) |
| **INF-01** — Plan 02 scope clarification | Info | 본 plan scope X (Plan 02 의 책임 영역 박제) |

## Wave 0 fixture 박제

6 fixture JSON 박제 — fixture #6 의 expected.recommendation 에 CR-01 fix 의 **unprefixed exact match 박제 완료**:

```
이 동작은 기준 영상이 없어, AI 가 IPSF 절대 기준만으로 분석했어요. 강사와 함께 확인 권유드려요.
```

Plan 02 Task 1 의 `test_uncertain_when_mode3_first_fallback` 가 본 문자열 exact match 로 검증.

## Deviations from Plan

### [Rule 1 — Bug Prevention] BodyComparisonFinding.category 의 default 박제

- **Found during:** Task 3 (3-way lockstep)
- **Issue:** Plan 의 must-haves §3 + RESEARCH.md §Schema Extension 은 `category` 를 "default 없음 — required" 로 박제. 단, 본 시그너처는 Phase 6 의 기존 BodyComparisonFinding 호출 (test_body_normalizer_ipsf_deficit.py / test_dataclass_to_camel_case_dict.py 2 곳에서 직접 생성) 을 TypeError 로 즉시 breakage 시킴. acceptance criterion `pytest backend/tests/phase06/ -x` PASS 가 동시 충족 불가.
- **Fix:** `category: Literal[...] = "uncertain"` 으로 default 박제. WR-01 의 fail-safe 정신 정합 — 명시적 지정 없을 시에도 "AI 확신 부족" 으로 표시. measure_ipsf_absolute_deficits 의 6 emit 위치는 plan 대로 명시 `category="uncertain"` 박제 — verify command `grep -c 'category="uncertain"'` >= 6 정합.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py`
- **Verification:** Phase 6 회귀 0 (136 PASS + 1 skipped) + Phase 7 lockstep test 7 PASS + category enum validator 동작 (잘못된 값 입력 시 ValueError raise — Test 5).
- **Commit:** `d4d8af4`

### [Rule 1 — Bug] AST grep gate Assign + AnnAssign 양쪽 검사

- **Found during:** Task 2 (test_copy_templates_no_forbidden.py 작성 후 첫 실행)
- **Issue:** Plan 의 AST snippet 은 `ast.Assign` 만 iterate. 단, `copy_templates.py` 의 `_COPY_TEMPLATES: dict[...] = {...}` + `_MODE_PREFIX: dict[...] = {...}` 는 type annotation 박제 → `ast.AnnAssign` 노드로 파싱 (Assign 아님). plan snippet 실행 시 0 strings 반환 → 게이트 통과하지만 무의미 (false positive).
- **Fix:** Test helper `_extract_template_strings` 가 `ast.Assign` + `ast.AnnAssign` 둘 다 검사. sanity test (`test_ast_gate_extracts_strings`) 추가 — 추출 string 수 >= 66 (33 × 2 + 3 mode prefix) 보장.
- **Files modified:** `backend/tests/phase07/test_copy_templates_no_forbidden.py`
- **Verification:** 9 forbidden phrases × 171 strings 검사 = 0 violations + sanity test PASS.
- **Commit:** `fcb4025`

**Total deviations:** 2 auto-fixed (1 Rule 1 schema bug-prevention + 1 Rule 1 AST gate bug).
**Impact:** 양쪽 모두 plan 의 의도 정합 (fail-safe semantics / forbidden phrase gate 실효성). Plan 의 acceptance criterion 충족, 동작 verify command 정합.

## Authentication Gates

None — plan executed without auth interaction.

## Self-Check: PASSED

### Files exist verification

- ✓ `backend/shared/python/sunity_shared/analysis/copy_templates.py` (created)
- ✓ `backend/tests/phase07/__init__.py` (created, empty)
- ✓ `backend/tests/phase07/conftest.py` (created)
- ✓ `backend/tests/phase07/fixtures/__init__.py` (created, empty)
- ✓ `backend/tests/phase07/fixtures/_factory.py` (created)
- ✓ 6 fixture JSON (created)
- ✓ 4 test 파일 (created)
- ✓ 4 modified files (body_normalizer.py / models.py / analysis.ts / contract.md)

### Commits verification

- ✓ `3e1fbf7` Task 1 — 10 files created
- ✓ `fcb4025` Task 2 — 4 files created
- ✓ `d4d8af4` Task 3 — 5 files (4 modified + 1 created) atomic

### Verification commands

- ✓ `pytest backend/tests/phase07/ -x` → 90 PASS
- ✓ `pytest backend/tests/phase06/ -x` → 136 PASS + 1 skipped
- ✓ `cd app && npx tsc --noEmit` → exit 0
- ✓ AST grep gate → NO_FORBIDDEN_OK (171 strings checked, 0 violations)
- ✓ Resolver coverage → 33 cases all green
- ✓ CR-01 exact match → fixture #6 unprefixed 단일 문장 박제

## Known Stubs

None — Plan 02 의 `classify_findings()` 가 placeholder 를 재할당 path. 본 plan
은 schema + canned + test infrastructure 박제만 — 분류 로직 자체는 Plan 02 scope.

## Threat Flags

None — Phase 7 가 새로운 trust boundary 또는 attack surface 도입하지 않음. canned
string dict literal 은 정적 (compile-time) 박제, secret 무관. plan 의 threat_model
표 그대로 mitigate.

## Next Step

Ready for Plan 07-02 — `classify_findings()` 함수 박제 + integration test.
Wave 0 인프라 (phase07/ + 6 fixture JSON + copy_templates 모듈) 즉시 활용 가능.
