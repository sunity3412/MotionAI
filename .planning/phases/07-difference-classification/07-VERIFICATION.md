---
phase: 07-difference-classification
verified: 2026-06-08T12:00:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 7: 차이 분류 — Verification Report

**Phase Goal:** "정규화 비교 결과를 '체형 허용 차이 / 개선 필요 차이 / uncertain'으로 자동 분류하고 각 항목에 bodyTypeInterpretation·recommendation 을 부착한다 (ROADMAP §Phase 7). Phase 6 의 `BodyComparisonReport.findings[]` 를 입력으로 받아 자동 분류 + `doNotOverCorrect` / `recommendedFocus` 두 카피 배열을 백엔드 canned 템플릿으로 박제."

**Verified:** 2026-06-08
**Status:** PASS
**Re-verification:** No — initial verification

---

## Goal Achievement

Phase 7 의 goal 은 codebase 에서 관찰 가능하게 달성되었다. `BodyComparisonReport` 가 8 커밋을 거쳐 ROADMAP SC #1~#4 + iteration 2 review 7 finding mitigation 까지 모두 박제. 백엔드 pipeline 의 `compare_body_profiles()` → `classify_findings()` → `render_finding_copy()` → `BodyComparisonReport` → camelCase 자동 변환 → Firestore → frontend `userAnalyses.normalize()` 가 lockstep 으로 연결되어 있고, 108 phase07 PASS + 136 phase06 회귀 0 + TSC clean 으로 wiring 검증 완료. forbidden phrase grep gate 는 AST 기반 (Assign + AnnAssign) 으로 직접 재현 시 173 strings 검사 / 0 violations.

---

## Observable Truths (ROADMAP §Phase 7 + Plan must-haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC #1: `BodyComparisonFinding[]` 이 category 별로 산출됨 (`body_type_allowed` / `needs_adjustment` / `uncertain`) | VERIFIED | `body_normalizer.py:837` Literal enum 3 values + `__post_init__` validator (line 851-855), `classify_findings()` line 1000-1111 분류 룰 본체. test_classify_findings.py 11 PASS + test_compare_body_profiles_phase7_integration.py 4 PASS |
| 2 | SC #2: `doNotOverCorrect` / `recommendedFocus` 두 배열이 출력에 포함됨 | VERIFIED | `body_normalizer.py:891-893` BodyComparisonReport 3 신설 필드 (do_not_over_correct / recommended_focus / recommended_focus_fallback WR-03), `compare_body_profiles()` line 1531-1539 wiring 주입. integration test 4 PASS + dataclass_to_camel_case test 2 PASS |
| 3 | SC #3: `bodyNormalizationConfidence` 가 낮으면 `uncertain` 으로 처리됨 | VERIFIED | `classify_findings()` line 1037-1056 OR 합집합 demotion (3 게이트: is_low_global + finding.confidence < 0.5 + not body_type_adjusted) + CATEGORY_CONF_GATE=0.5 (line 185). test_classify_findings.py test_uncertain_when_report_low_confidence + test_uncertain_when_finding_low_confidence PASS |
| 4 | SC #4: 결과 화면 카피가 "프로보다 못합니다" 같은 표현 없이 보정 중심 작성 | VERIFIED | 9 FORBIDDEN_PHRASES (6 research §10.3 + 3 Sunity memory) `copy_templates.py:247-265`. AST grep gate 직접 재현: 173 production strings 검사 → 0 violations. test_copy_templates_no_forbidden.py 10 PASS. 33 production canned strings 직접 inspection 결과 가능성 언어 + AI 보조 톤 + 부위별 원인 (고관절·후굴·코어·내전근·전완근·광배·흉곽·골반·견갑) 일관됨 |
| 5 | 3-way contract lockstep (TS ↔ Python ↔ docs §8/§8.3) | VERIFIED | TS `analysis.ts:502/505/508/511/568/571/575` (BodyComparisonFinding +4 + BodyComparisonReport +3 필드), Python `body_normalizer.py:837-840/891-893` 동일 schema. docs/contract.md line 417/419/462-464 §8 표 신설 + line 537-646 §8.3 신설 서브섹션 (분류 룰 + 분배 룰 + 33 coverage + CR-01 fallback + 9 forbidden grep gate). test_body_comparison_report_phase7_lockstep.py 7 PASS |
| 6 | Phase 6 회귀 0 | VERIFIED | `pytest backend/tests/phase06/ -x` → 136 PASS + 1 skipped. WR-01 fail-safe (BodyComparisonFinding.category default = "uncertain") 가 기존 Phase 6 호출자 (test_body_normalizer_ipsf_deficit.py / test_dataclass_to_camel_case_dict.py) TypeError breakage 방지. Deviation R1 박제 정합 |
| 7 | frontend `userAnalyses.normalize()` 신설 7 필드 null-guard (WR-02 retract B1) | VERIFIED | `app/src/lib/userAnalyses.ts:53-69` immutable spread + map 패턴. 4 ?? default + findings.map (category ?? 'uncertain' + phase ?? 'hold'). `npx tsc --noEmit` exit 0 |
| 8 | iteration 2 cross-AI review 7 finding 모두 mitigation | VERIFIED | CR-01: render_finding_copy used_reference_fallback path `copy_templates.py:301-302` + fixture #6 + classify_findings line 1043-1045/1073 thread. CR-02: 12 global keys (clean_lines/extension/posture/body_placement × 3 category) `copy_templates.py:135-225` 33 coverage. WR-01: 6 emit positions placeholder `body_normalizer.py:1169/1203/1255/1286/1308/1336`. WR-02: frontend normalize. WR-03: recommended_focus_fallback `body_normalizer.py:893` + _EMPTY_FOCUS_FALLBACK 박제. WR-04: test_copy_templates_resolver_coverage.py 33 PASS. INF-01: test_classify_findings_preserves_measurement_fields.py 1 PASS (behavioral primary) |

**Score:** 8/8 truths verified

---

## Required Artifacts (Level 1-4)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/shared/python/sunity_shared/analysis/body_normalizer.py` | BodyComparisonFinding +4 / Report +3 / classify_findings / _resolve_joint_group / wiring | VERIFIED | 11 grep hits 신설 필드 + 함수 정의 + line 1503 wiring 1줄. 직접 line 1000-1111 inspection 정합 |
| `backend/shared/python/sunity_shared/analysis/copy_templates.py` | 33 canned + render_finding_copy + FORBIDDEN_PHRASES (9) + _EMPTY_FOCUS_FALLBACK + _MODE_PREFIX (3) | VERIFIED | `_COPY_TEMPLATES` len = 33 (runtime inspection), 9 forbidden (6+3), 3 mode prefix, render_finding_copy 시그너처 includes used_reference_fallback kw-only. 334 lines |
| `app/src/types/analysis.ts` | TS contract +4 finding + +3 report 필드 | VERIFIED | line 502/505/508/511/568/571/575. category Literal 'body_type_allowed' \| 'needs_adjustment' \| 'uncertain' |
| `docs/contract.md` §8 + §8.3 | 신설 필드 표 + 분류 룰 서브섹션 | VERIFIED | line 417/419/462-464 §8 표, line 537-646 §8.3 신설 (Plan 07-01 footer) |
| `app/src/lib/userAnalyses.ts` | normalize() bodyComparisonReport 7 필드 null-guard | VERIFIED | line 53-69 immutable spread + map + ?? defaults |
| `backend/tests/phase07/` | 8 test files + 6 fixtures + factory loader | VERIFIED | 8 test files + 6 fixture JSON + conftest.py + _factory.py 모두 존재 |

**Data-Flow Trace (Level 4):** `measure_ipsf_absolute_deficits()` (Phase 6) → `compare_body_profiles()` line 1503 1줄 wiring → `classify_findings()` returns 4-tuple → `BodyComparisonReport(findings=classified_findings, do_not_over_correct=…, recommended_focus=…, recommended_focus_fallback=…)` line 1527-1540 → `firestore_admin._dataclass_to_camel_case_dict` Phase 6 C8 박제로 camelCase 자동 변환 → Firestore → `userAnalyses.normalize()` null-guard layer. FLOWING.

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `compare_body_profiles()` | `classify_findings()` | line 1503 1줄 wiring | WIRED | 4-tuple destructure + 3 kwarg + findings 재할당 |
| `classify_findings()` | `render_finding_copy()` | line 1068-1074 with used_reference_fallback thread | WIRED | CR-01 fix path 정합 |
| `BodyComparisonReport` (Python) | `BodyComparisonReport` (TS) | docs/contract.md §8 표 6 행 mapping | WIRED | snake_case ↔ camelCase 1:1 lockstep 박제 |
| backend Firestore output | frontend `normalize()` | `bodyComparisonReport.{doNotOverCorrect, recommendedFocus, recommendedFocusFallback, findings[].category, findings[].phase}` 모두 ?? default | WIRED | WR-02 retract B1 null-guard. TS strict + React 19 정합 |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 7 test suite green | `pytest backend/tests/phase07/ -x` | 108 passed in 0.45s | PASS |
| Phase 6 회귀 0 | `pytest backend/tests/phase06/ -x` | 136 passed, 1 skipped in 1.03s | PASS |
| TypeScript type-check | `cd app && npx tsc --noEmit` | exit 0 (no errors) | PASS |
| 33 canned templates runtime count | `python3 -c "from sunity_shared.analysis.copy_templates import _COPY_TEMPLATES; print(len(_COPY_TEMPLATES))"` | 33 | PASS |
| 6 emit position uncertain placeholders (WR-01) | `grep -c 'category="uncertain"' body_normalizer.py` | 8 (6 emit + 2 comment/docstring) | PASS |
| Forbidden phrase AST grep gate (independent reproduction) | python3 ast walk over _COPY_TEMPLATES + _MODE_PREFIX + 2 fallback constants | 173 strings / 0 violations | PASS |
| All 8 commits exist | `git log --oneline 3e1fbf7 fcb4025 d4d8af4 7f6c546 2aedb84 4851a43 8559c6f 4ad0fc0 -8` | 8 commits all present | PASS |
| Full backend suite without phase 7 scope (deferred items) | `pytest backend/tests/` | 11 ERROR (pre-existing `from backend...` import path issue in R&D / spike / Plan 11 scripts — 07-deferred-items.md 박제 정합) | SKIP (out of scope, deferred-items 정합) |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PERS-01 | 07-01-PLAN.md + 07-02-PLAN.md | 체형 정규화 비교 엔진이 차이를 "체형 허용 / 개선 필요 / uncertain" 으로 분류 + coaching 모드 정규화 ON | SATISFIED | classify_findings 3 category 분류 + 분배 + canned 카피 박제. ROADMAP 의 PERS-01 → Phase 6 + Phase 7 Complete 매핑 정합 |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | 모든 modified files 에서 TBD / FIXME / XXX / TODO / HACK / PLACEHOLDER / return null stub / return [] stub / return {} stub 발견 X. `category="uncertain"` 의 6 emit position 은 WR-01 의 명시적 fail-safe 박제 (intentional behavior, classify_findings 가 재할당). |

---

## iteration 2 Cross-AI Review Fix Verification

| Finding | Severity | Mitigation Status | Evidence |
|---------|----------|------------------|----------|
| **CR-01** — `mode3_first + used_reference_fallback` unreachable | Critical | VERIFIED | `copy_templates.py:301-302` early return path + `classify_findings()` line 1043-1045 (is_mode3_first_fallback) + line 1073 (used_reference_fallback=is_mode3_first_fallback). fixture #6 expected.recommendation "이 동작은 기준 영상이 없어, AI 가 IPSF 절대 기준만으로 분석했어요. 강사와 함께 확인 권유드려요." 박제 정합 |
| **CR-02** — `clean_lines` global resolver gap | Critical | VERIFIED | `copy_templates.py:135-225` 12 global keys (clean_lines/extension/posture/body_placement × 3 category) + pose_reliability_low global × 3 = 15 global keys. _resolve_joint_group `body_normalizer.py:985-998` clean_lines + joint_key=None → "global" path. test_copy_templates_resolver_coverage.py 33 PASS |
| **WR-01** — placeholder fail-open | Warning | VERIFIED | 6 emit positions `body_normalizer.py:1169/1203/1255/1286/1308/1336` 명시 `category="uncertain"`. dataclass default 도 "uncertain" (Deviation R1). test_body_comparison_report_phase7_lockstep.py PASS. fail-safe 정합 |
| **WR-02** — frontend normalize unguarded | Warning | VERIFIED | `userAnalyses.ts:53-69` immutable spread + 4 ?? default + map(category ?? 'uncertain', phase ?? 'hold'). iteration 1 B1 retract 박제 (commit `8559c6f` 메시지). tsc clean |
| **WR-03** — empty recommendedFocus UX | Warning | VERIFIED | `_EMPTY_FOCUS_FALLBACK` `copy_templates.py:68` + `recommended_focus_fallback` 필드 `body_normalizer.py:893` + classify_findings line 1102-1104 박제 룰 (빈 list → fallback, 채워지면 None) + integration test fallback PASS |
| **WR-04** — resolver coverage test | Warning | VERIFIED | `test_copy_templates_resolver_coverage.py` 33 PASS (18 emit pattern + 15 global keys) |
| **INF-01** — replace AST not core safety | Info | VERIFIED | `test_classify_findings_preserves_measurement_fields.py` 1 PASS (behavioral primary — 6 원본 측정 필드 input ↔ output 정확 일치 + 신규 4 필드 박제 + id 다름) |

---

## Open Issues / Human Verification

None blocking. Manual-only verification items (07-VALIDATION.md 105-112) 은 자연어 톤 품질 검수 영역으로, belle 이 plan 단계 + close-out 단계에서 검토하는 항목 (33 canned + 3 mode prefix + _EMPTY_FOCUS_FALLBACK + fixture #6 fallback). 코드/grep 으로 충족 못하는 자연어 품질 검수 — 직접 inspection 결과 가능성 언어 + AI 보조 톤 + 부위별 원인 (고관절·후굴·코어·내전근·전완근·광배·흉곽·골반·견갑) 일관됨. forbidden phrase 0 violation. belle 의 추가 final 검수가 권장되나 phase 종료 blocking 사유 아님.

Phase 7 deferred items (07-deferred-items.md): pre-existing `from backend.research...` import path 이슈가 11 test files (compare_engines_smoke, debug_gap_root_cause, gemini_motion_classify, mapping_audit, pole_detector, spike_gemini_moment, spike_measurement_trace, spike_mediapipe_to_h36m17, spike_rtmpose_to_h36m17, sweep_rtmpose_smoke) 에서 collection ERROR — Phase 7 scope 밖, Plan 11 sweep evaluation scope. 별도 plan 에서 fix.

---

## Test Counts (Summary)

| Suite | Result | Notes |
|-------|--------|-------|
| Phase 7 (`pytest backend/tests/phase07/ -x`) | **108 PASS** in 0.45s | 90 Plan 01 + 18 Plan 02 |
| Phase 6 회귀 (`pytest backend/tests/phase06/ -x`) | **136 PASS + 1 skipped** in 1.03s | 회귀 0 |
| TypeScript (`cd app && npx tsc --noEmit`) | **exit 0** | TSC clean |
| Full backend (`pytest backend/tests/`) | 11 pre-existing collection ERROR | 모두 R&D/spike `from backend...` import 이슈, 07-deferred-items.md 박제 |

---

## Verdict

**PASS** — Phase 7 의 phase goal + 4 success criteria + 7 iteration 2 review finding mitigation + 3-way contract lockstep + WR-02 frontend null-guard 모두 codebase 에서 직접 관찰 가능 + 직접 spot-check 재현 PASS. 분류 + 카피 layer 가 Phase 6 BodyComparisonReport 위에 lockstep 박제. classify_findings 가 measure_ipsf_absolute_deficits 의 6 fail-safe placeholder 를 모두 재할당하는 wiring 검증 완료. 다음 plan/phase (Phase 8 중심축 이탈) 진입 ready.

---

*Verified: 2026-06-08T12:00:00Z*
*Verifier: Claude (gsd-verifier)*
