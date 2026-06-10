---
phase: 09
plan: 01
subsystem: force-pattern-inference
tags: [schema, lockstep, firestore, dataclass, tdd]
requires:
  - Phase 8 ForceSignalsReport (umbrella)
  - Phase 8.1 AxisDeviationMetric (tilt-only, raw signal)
  - _dataclass_to_camel_case_dict (Phase 6 C8)
provides:
  - ForcePatternFinding frozen dataclass (Python)
  - ForcePatternInference frozen dataclass (Python)
  - ForcePatternFinding TS interface
  - ForcePatternInference TS interface
  - AnalysisResult.forcePatternInference field
  - docs/contract.md §9.11
  - _validate_force_pattern_inference scoped validator
  - complete_analysis(force_pattern_inference=) kwarg
  - userAnalyses.ts normalize() null-guard
  - phase09 pytest harness (conftest + 4 test files)
affects:
  - Wave 1 (Plan 09-02) — 본체 함수 (infer_force_direction_pattern) 가 본 schema 위에 박제
  - Phase 11 (CoachCommentHook) — findings[].interpretation 위 LLM 풍부화 consume
  - Phase 12 — raw 수치 (confidence) UI 노출 consume
tech-stack:
  added: []
  patterns:
    - 3-way contract lockstep (TS ↔ Python ↔ docs)
    - Frozen dataclass + __post_init__ validator (D-09-U3)
    - Firestore scoped validator (Phase 8 _validate_force_signals_report mirror)
    - Frontend null-guard immutable spread (Phase 7/8 패턴)
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/force_pattern.py
    - backend/tests/phase09/__init__.py
    - backend/tests/phase09/conftest.py
    - backend/tests/phase09/test_force_pattern_lockstep.py
    - backend/tests/phase09/test_dataclass_to_camel_case_dict_phase9.py
    - backend/tests/phase09/test_firestore_lockstep_phase9.py
    - backend/tests/phase09/test_force_pattern_dataclass.py
  modified:
    - backend/shared/python/sunity_shared/firestore_admin.py
    - app/src/types/analysis.ts
    - app/src/lib/userAnalyses.ts
    - docs/contract.md
decisions:
  - D-09-D1 8+5 필드 schema 박제
  - D-09-U1 11 files 단일 atomic commit
  - D-09-U3 frozen dataclass + __post_init__ strictness
  - D-09-U4 camelCase 자동 변환 (_dataclass_to_camel_case_dict 재사용)
  - D-09-U5 Firestore nested-array 차단 (scoped validator)
  - R1 iter-4 phase ∈ _MOTION_PHASES enforcement (downstream KeyError 차단)
  - R2 iter-3 warnings empty-string reject
  - R2 iter-4 tuple reject (contract = list[str] / list[ForcePatternFinding])
  - R2 iter-5 _FORCE_PATTERN_FINDING_KEYS 8-key whitelist
  - R6 iter-3 push-back: collect-only gate 제거, AST parse 만 (atomic commit 경계 보존)
metrics:
  duration_min: ~25
  completed_date: 2026-06-10
  commit_sha: defc973
  files_changed: 11
  insertions: 1438
  tests_added: 49
---

# Phase 09 Plan 01: Wave 0 — ForcePatternFinding/Inference 3-way schema lockstep — Summary

**One-liner:** Wave 0 = 3-way schema lockstep (TS interface + Python frozen dataclass + docs §9.11 + Firestore scoped validator + frontend null-guard) 단일 atomic commit. Wave 1 (Plan 09-02) 의 `infer_force_direction_pattern` 본체 함수가 schema drift 없이 흘러 들어갈 수 있도록 vertical 골격 확보.

## Objective

Phase 9 `ForceDirectionPattern + 실패 원인 후보 3개` 의 추론 layer 가 Firestore 까지 흘러갈 수 있게 `ForcePatternFinding` + `ForcePatternInference` Python frozen dataclass (신설 module `force_pattern.py`) + TS interface (`analysis.ts`) + `docs/contract.md §9.11` 동시 신설 + Firestore scoped validator + frontend null-guard 박제. `complete_analysis(..., force_pattern_inference=None)` 시그니처 미리 확장.

## Tasks Completed

| Task | Name | Status | Files |
|------|------|--------|-------|
| T1 | phase09 pytest harness 박제 (4 test) | green | `backend/tests/phase09/{__init__.py, conftest.py, test_force_pattern_lockstep.py, test_dataclass_to_camel_case_dict_phase9.py, test_firestore_lockstep_phase9.py, test_force_pattern_dataclass.py}` |
| T2 | 신설 force_pattern.py (Literal alias + frozen dataclass + 상수) | green | `backend/shared/python/sunity_shared/analysis/force_pattern.py` |
| T3 | TS interface 신설 + AnalysisResult.forcePatternInference | green | `app/src/types/analysis.ts` |
| T4 | docs/contract.md §9.11 신설 | green | `docs/contract.md` |
| T5 | Firestore scoped validator + complete_analysis 시그니처 확장 | green | `backend/shared/python/sunity_shared/firestore_admin.py` |
| T6 | Frontend null-guard (userAnalyses.ts::normalize) | green | `app/src/lib/userAnalyses.ts` |
| T7 | Wave 0 SINGLE atomic commit (11 files) | green | commit `defc973` |

## Commit

- `defc973` — `feat(09-01): Wave 0 — ForcePatternFinding/Inference 3-way schema lockstep`
  - 11 files changed, 1438 insertions(+)
  - Tasks T1-T6 staged via `git add` (no per-task commits per D-09-U1)
  - Single atomic commit invariant 박제 — Wave 0 rollback = `git revert defc973` 한 번

## Wave 0 Gates Passed

1. `cd backend && pytest tests/phase09/ -x -q` → **49 passed in 0.25s**
   - test_force_pattern_lockstep: 9 PASS (3-way TS ↔ Python ↔ docs §9.11 lockstep)
   - test_dataclass_to_camel_case_dict_phase9: 2 PASS (camelCase 변환)
   - test_firestore_lockstep_phase9: 18 PASS (1 PASS + 13 reject + 4 sanity)
   - test_force_pattern_dataclass: 20 PASS (__post_init__ validator)
2. `cd backend && pytest tests/phase06/ tests/phase07/ tests/phase08/ tests/phase08_1/ -x -q` → **408 passed, 1 skipped** (회귀 0)
3. `cd app && npm run typecheck` → **0 error** (TS strict mode)
4. `git log -1 --name-only` → **11 files** (single atomic commit invariant)

## Success Criteria

- [x] `backend/shared/python/sunity_shared/analysis/force_pattern.py` 신설 + import success + `ForcePatternFinding` / `ForcePatternInference` 박제 (본체 함수는 Wave 1)
- [x] `firestore_admin._validate_force_pattern_inference` + `complete_analysis(force_pattern_inference=)` 시그니처 확장
- [x] `app/src/types/analysis.ts`: `ForcePatternFinding` + `ForcePatternInference` + `AnalysisResult.forcePatternInference?`
- [x] `app/src/lib/userAnalyses.ts::normalize`: forcePatternInference null-guard + findings 내부 default
- [x] `docs/contract.md §9.11` 신설 (8 + 5 필드 + 3 warning code + 책임 경계)
- [x] `backend/tests/phase09/{__init__.py, conftest.py, 4 test files}` 신설 + `pytest tests/phase09/ -x -q` 49/49 PASS
- [x] Wave 0 = SINGLE atomic commit (11 files) — `git log -1 --stat` 확인
- [x] Phase 6/7/8/8.1 회귀 0 + `npm run typecheck` 0 error

## Decisions Made

- **D-09-D1 — 8+5 필드 schema 박제**: ForcePatternFinding (pattern / phase / sourceSignal / reason / interpretation / confidence / jointHint / warnings) + ForcePatternInference (version / findings / overallConfidence / modeContext / warnings).
- **D-09-U1 — 11 files 단일 atomic commit**: Tasks T1-T6 가 `git add` 로 staging 만 하고 T7 가 한 번에 commit. 부분 rollback 시 schema drift 발생 → 절대 금지.
- **D-09-U3 — Frozen dataclass + __post_init__ strict validator**: enum / confidence [0,1] / interpretation non-empty / warnings non-empty str / phase ∈ _MOTION_PHASES / findings list[ForcePatternFinding].
- **D-09-U4 — camelCase 자동 변환**: `_dataclass_to_camel_case_dict` 재사용 (Phase 6 C8). source_signal → sourceSignal / joint_hint → jointHint / mode_context → modeContext.
- **D-09-U5 — Firestore nested-array 차단**: `_validate_force_pattern_inference` scoped validator + 8-key whitelist (camelCase). list[str] warnings only, list[dict] findings 까지만 허용.
- **iter-4 R1 — phase ∈ _MOTION_PHASES enforcement**: downstream `_PHASE_PRIORITY[f.phase]` KeyError 차단. `from .force_signals import _MOTION_PHASES` 재사용 (drift 차단).
- **iter-5 R2 — _FORCE_PATTERN_FINDING_KEYS 8-key whitelist**: validator 가 `_dataclass_to_camel_case_dict` 출력 dict 만 받으므로 camelCase 기준 strict 화이트리스트.
- **iter-3 R2 — warnings empty-string reject**: dataclass + Firestore validator 양쪽에서 동일 strictness.
- **iter-3 R6 push-back — collect-only gate 제거**: T1 verify = AST parse 만. atomic commit 경계 보존 위해 inline import / stub 박제 거부, 자연 fail 후 T2 박제 시 자동 green.

## Deviations from Plan

### Auto-fixed Issues

None — plan 박제 정확하고, Phase 8 dataclass signatures (PhaseBoundary.source / ContactStabilityMetric 11 fields / _MOTION_PHASES export) 모두 plan 의 verified upstream contracts 와 일치. T1 conftest.py factory signature 가 Phase 8 actual constructor 와 1:1 매칭.

### Plan vs Reality

- Plan 의 T3 verify gate `pytest tests/phase09/test_force_pattern_lockstep.py -x -q -k "ts or analysis_ts"` 의 `-k` filter 는 "test_contract_section..." 도 매칭 (test name 안 'ts' substring) — T3 시점에 1 test 가 RED 였으나 이는 T4 에서 docs §9.11 박제 시 자동 green (T3 → T4 의존 순서 정합). plan 의 의도된 behavior — 본 시점 deviation X.

## Threat Surface

본 Wave 가 새로 도입한 security-relevant surface = 없음 (schema only — Wave 1 의 inference 본체가 실제 force_signals report consume).

Threat model 의 mitigations 4 종 모두 박제:
- T-09-V5 (frozen dataclass validator): `test_force_pattern_dataclass.py` 20 PASS
- T-09-T2 (Firestore nested-array): `test_firestore_lockstep_phase9.py` 18 PASS
- T-09-V5b (frontend null/undefined): `userAnalyses.ts` normalize null-guard + `tsc --noEmit` 0 error
- T-09-T-drift (3-way schema drift): `test_force_pattern_lockstep.py` 9 PASS + atomic commit (T7) 가 drift 발생 자체 차단

## Known Stubs

본 Wave 의 산출은 schema only — 본체 함수 (`infer_force_direction_pattern`) + 18 canned 본문 + pipeline wiring 은 Wave 1 (Plan 09-02) 책임. 의도된 boundary (D-09-E1).

- `force_pattern.py`: `infer_force_direction_pattern` / `_detect_*` / `_rank_top3` 미박제 (Wave 1).
- `_FORCE_PATTERN_COPY` (18 canned): `force_pattern_copy.py` 신설 Wave 1.
- `pipeline/app.py::_process`: `infer_force_direction_pattern` 호출 + `complete_analysis(force_pattern_inference=...)` 박제 Wave 1.

본 stub 들은 `AnalysisResult.forcePatternInference?: ForcePatternInference | null` 의 optional/nullable 박제로 처리 — Wave 1 wiring 전 도 Firestore doc crash X (Phase 8 패턴 정합).

## Follow-ups

- **Wave 1 진입 OK** (즉시): 3-way schema field alignment 회귀 0 확인, atomic commit `defc973` 안 11 files 모두 박제. Wave 1 (Plan 09-02) 의 `infer_force_direction_pattern` 본체 함수 + 18 canned + pipeline wiring 박제 가능.
- **belle 박제 검수 = N/A**: Wave 0 = schema only (18 canned 본문은 Wave 1 책임).
- **Codex cross-AI plan-review = N/A**: Wave 1 종료 시점 진행 (Phase 8.1 패턴 정합).

## Self-Check: PASSED

- [x] FOUND: `backend/shared/python/sunity_shared/analysis/force_pattern.py`
- [x] FOUND: `backend/shared/python/sunity_shared/firestore_admin.py` (modified)
- [x] FOUND: `app/src/types/analysis.ts` (modified)
- [x] FOUND: `app/src/lib/userAnalyses.ts` (modified)
- [x] FOUND: `docs/contract.md` (modified)
- [x] FOUND: `backend/tests/phase09/__init__.py`
- [x] FOUND: `backend/tests/phase09/conftest.py`
- [x] FOUND: `backend/tests/phase09/test_force_pattern_lockstep.py`
- [x] FOUND: `backend/tests/phase09/test_dataclass_to_camel_case_dict_phase9.py`
- [x] FOUND: `backend/tests/phase09/test_firestore_lockstep_phase9.py`
- [x] FOUND: `backend/tests/phase09/test_force_pattern_dataclass.py`
- [x] FOUND: commit `defc973`
