---
phase: 09
verified: 2026-06-10
status: passed
score: 4/4 SC + 13/13 locked decisions verified
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 9: ForceDirectionPattern + 실패 원인 후보 3개 — Verification Report

**Phase Goal:** 기초 신호를 종합해 `ForceDirectionPattern`(pull/push/brace/rotate/release)을 추론하고, 동작 실패 원인 후보 3개를 카드 형태로 제시한다 (단정 금지, 모든 항목 "가능성"으로 표기).

**Verified:** 2026-06-10
**Status:** PASSED
**Re-verification:** No — initial verification.
**Mode:** mvp (vertical slice — Wave 0 schema + Wave 1 inference = E2E populated Firestore `forcePatternInference`).

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC#1 | `inferForceDirectionPattern` 함수가 5개 카테고리 중 하나 이상을 phase별로 반환한다 | VERIFIED | `force_pattern.py:642-740` — `infer_force_direction_pattern` returns `ForcePatternInference`; phase loop at `:680` iterates `_PHASE_ITERATION_ORDER = ('lock', 'hold', 'transition', 'final_shape', 'entry')`; per-phase candidates appended at `:704-718`; 6 patterns enumerated in `ForceDirectionPattern` Literal at `:44-46` (`pull/push/brace/rotate/release/unknown`). Per-phase emission verified by `tests/phase09/test_infer_force_direction_pattern.py::test_axis_tilt_signal_emits_release_finding` + 5 sibling tests (one per signal) PASS. `pytest tests/phase09/test_infer_force_direction_pattern.py -x -q` → **29 PASS**. |
| SC#2 | 실패 원인 후보가 정확히 상위 3개로 정렬되어 카드 형태 데이터로 출력된다 (KISMAM Top-3 진화) | VERIFIED | `force_pattern.py:604-639` — `_rank_top3` sorts by `(−score, _PHASE_PRIORITY[phase], _SIGNAL_PRIORITY[source_signal], −confidence)`; (pattern, phase) dedup at `:629-637`; length cap [0, 3] enforced both at `_rank_top3` and `ForcePatternInference.__post_init__` `:288-291`. `pytest tests/phase09/test_force_pattern_ranking.py -x -q` → **12 PASS** including `test_top3_ranking_by_score`, `test_tie_break_phase_priority`, `test_tie_break_signal_priority`, `test_tie_break_confidence_desc`, `test_pattern_dedup_same_phase`, `test_pattern_dedup_different_phase_ok`, `test_max_three_findings`. 0-finding fallback at `:728-730` (no fabrication — D-09-B4) verified by `test_no_signal_emits_fallback` PASS. |
| SC#3 | 모든 finding이 `confidence`와 `interpretation` 필드를 가지며 "단정"이 아닌 "가능성" 언어로 표현된다 | VERIFIED | `ForcePatternFinding` 8 필드 dataclass at `force_pattern.py:155-225` — `confidence: float` (`__post_init__` `:200-203` enforces [0, 1]) + `interpretation: str` (`:205-208` enforces non-empty). 18 canned bodies at `force_pattern_copy.py:71-150` — sampled bodies use possibility tone ("보여요" / "흐름이 나타나요" / "점검해 볼 수 있어요" / "살펴볼 만해요"); no imperatives/단정 forms. `pytest tests/phase09/test_force_pattern_copy_render.py -v` → **24 PASS** (parametrized over 18 canned + render gate). |
| SC#4 | "근육 힘 방향" 단정 표현이 출력에 없다 (코드 + 프롬프트 가드) | VERIFIED | `force_pattern_copy.py:184-204` — `FORBIDDEN_PHRASES_RESEARCH` 8 substring + `FORBIDDEN_PHRASES_PHASE9_REGEX` 2 regex (incl. `r"근육 힘 방향.*확정"` + `r"\d+%\s*감점"`). AST grep gate `tests/phase09/test_force_pattern_copy_no_forbidden.py` → **11 PASS** (8 substring + 2 regex + 1 AST sanity gate `test_ast_gate_extracts_strings`). |

**Score: 4/4 truths VERIFIED.**

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/shared/python/sunity_shared/analysis/force_pattern.py` | Wave 1 본체 (`infer_force_direction_pattern` + 6 detectors + `_rank_top3` + frozen dataclasses) | VERIFIED | 764 lines. All decisions D-09-A1~U6 cited inline. `infer_force_direction_pattern` at `:642`, 6 `_detect_*` helpers at `:368-572`, `_rank_top3` at `:604`, `_apply_motion_id_boost` at `:575`, `_phase_metric_confidence_factor` at `:340`. |
| `backend/shared/python/sunity_shared/analysis/force_pattern_copy.py` | 18 canned + 3 mode prefix + 6 jointHint + 1 fallback + 10 forbidden | VERIFIED | 241 lines. `_FORCE_PATTERN_COPY_DATA` 18 entries at `:71-150`, `_MODE_PREFIX` at `:54-58`, `_JOINT_HINT_BY_SIGNAL` at `:161-168`, `_FALLBACK_BODY` at `:174-177`, `FORBIDDEN_PHRASES_RESEARCH` 8 + `FORBIDDEN_PHRASES_PHASE9_REGEX` 2 at `:184-204`. MappingProxyType wrap at `:152-154`. |
| `backend/shared/python/sunity_shared/firestore_admin.py` | `_validate_force_pattern_inference` scoped validator + `complete_analysis(force_pattern_inference=...)` kwarg | VERIFIED | Validator at `:343-403` (`force_pattern_inference` path), kwarg + write at `:418, 466-471`. |
| `backend/functions/pipeline/app.py` | `_process` wiring (mode_context inline + `infer_force_direction_pattern` call + Firestore write) | VERIFIED | Block at `:1131-1160`. mode_context inline at `:1141-1150` (`MODE_EXPERT` → `'mode1'`, MODE_SELF + `comparison.get('isFirst', True)` → `'mode3_first' or 'mode3_progress'`). camelCase convert + kwarg at `:1157, 1172`. Defensive `isinstance(comparison, dict)` guard at `:1147` (always-true on current code paths — `build_mode1` / `build_mode3` both return dict; benign future-refactor safety). |
| `app/src/types/analysis.ts` | TS interface + AnalysisDoc field | VERIFIED | `ForceDirectionPattern` / `ForceSourceSignal` / `ForcePatternModeContext` / `ForcePatternFinding` / `ForcePatternInference` at `:653-712`. `AnalysisDoc.forcePatternInference?: ForcePatternInference \| null` at `:199-204`. `npm run typecheck` → **0 errors**. |
| `app/src/lib/userAnalyses.ts` | Firestore normalize null-guard | VERIFIED | Null-guard at `:89-100` mirrors `forceSignalsReport` pattern; `?? null` fallback + immutable spread. |
| `docs/contract.md §9.11` | Phase 9 contract section | VERIFIED | §9.11 header at `:987`, §9.11.1 enum at `:991`, §9.11.2 ForcePatternFinding (8 fields) at `:999`, §9.11.3 ForcePatternInference (5 fields) at `:1012`, §9.11.4 Firestore path at `:1022`, §9.11.5 phase boundary at `:1027`, §9.11.6 warning codes at `:1034`. Note: CONTEXT.md `D-09-D1` originally referenced §9.5; Phase 8 had already used §9.0–§9.10 so Phase 9 was placed at §9.11. The lockstep test `tests/phase09/test_force_pattern_lockstep.py::test_contract_section_9_11_present` PASSes against the actual §9.11 location. |
| `backend/tests/phase09/` 8 test files | Unit test coverage | VERIFIED | 8 files present: `test_dataclass_to_camel_case_dict_phase9.py` / `test_firestore_lockstep_phase9.py` / `test_force_pattern_copy_no_forbidden.py` / `test_force_pattern_copy_render.py` / `test_force_pattern_dataclass.py` / `test_force_pattern_lockstep.py` / `test_force_pattern_no_severity_use.py` / `test_force_pattern_ranking.py` + `test_infer_force_direction_pattern.py`. |
| `backend/tests/pipeline/test_pipeline_phase9.py` | Integration test (5 cases) | VERIFIED | Present; 5 tests PASS. |

---

## Key Link Verification (Data Flow)

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `pipeline/app.py::_process` | `force_pattern.infer_force_direction_pattern` | `fp.infer_force_direction_pattern(force_signals_report, motion_id, mode_context)` | WIRED | Line `:1152-1156`. Real `force_signals_report` from `:1117-1128` `compute_force_signals` call. |
| `force_pattern.infer_force_direction_pattern` output | Firestore `result.forcePatternInference` | `complete_analysis(force_pattern_inference=force_pattern_inference_dict)` | WIRED | Camel-case convert at `:1157-1159`, kwarg at `:1172`. Validator `_validate_force_pattern_inference` runs at `firestore_admin.py:470`. |
| `_detect_*` (6 helpers) | `_rank_top3` | candidates list mutation `:704-718`, then `_rank_top3(candidates)` `:726` | WIRED | Pre-ranking motion_id boost at `:720-722` (D-09-C2 — BEFORE ranking). |
| `force_pattern_copy.force_pattern_canned_text` | `ForcePatternFinding.interpretation` | Called by 6 `_detect_*` helpers per `interpretation=force_pattern_canned_text(...)` | WIRED | 6 detector calls verified (lines `:393, 433, 473, 501, 531, 564`). |
| `app/src/lib/userAnalyses.ts::normalize` | App `AnalysisDoc.forcePatternInference` | `result?.forcePatternInference ?? null` | WIRED | Pattern matches `forceSignalsReport` precedent. `tsc --noEmit` → 0 errors. |

---

## D-09 Locked Decision Coverage

| Decision | Description | Status | Evidence |
|----------|-------------|--------|----------|
| D-09-A1 | 6-signal detection rules (axis_tilt / pelvis_drop / late_contact / high_jitter / high_jerk / abnormal_release) | VERIFIED | 6 `_detect_*` helpers `force_pattern.py:368-572`. All 6 signal detection tests PASS. |
| D-09-A2 | Raw signal only guard (axisMetric.severity 영구 차단) | VERIFIED | `grep -nE "axis.*\.severity" force_pattern.py` → 0 hits. `_AXIS_IGNORE_WARNINGS_PER_METRIC` (3 entries) at `:313-319` + `_AXIS_IGNORE_WARNINGS_REPORT` (1 entry) at `:323-325`. AST guard `tests/phase09/test_force_pattern_no_severity_use.py` → 2 PASS (AST + substring). |
| D-09-A4 | phaseBoundaries 미인식 fallback (`phase_unavailable_for_inference` warning) | VERIFIED | Emission at `:681-684`. `test_phase_unavailable_fallback` PASS. |
| D-09-A5 | Confidence formula `base × phase_metric_confidence_factor` | VERIFIED | `_phase_metric_confidence_factor` at `:340-365` (min of axis + stab). Applied at `:386, 426, 464, 494, 524, 554`. `test_confidence_formula_low_low` / `_high_high` / `_takes_min` → 3 PASS. |
| D-09-B2 | Top-3 ranking by `score = confidence × signal_weight` | VERIFIED | `_rank_top3` sort key at `:619-626`. `test_top3_ranking_by_score` / `test_signal_weight_overrides_confidence` / `test_abnormal_release_weight_priority` PASS. |
| D-09-B3 | 3-stage tie-break (phase priority → signal priority → confidence DESC) | VERIFIED | Sort key tuple at `:621-626`. `test_tie_break_phase_priority` / `_signal_priority` / `_confidence_desc` → 3 PASS. |
| D-09-B4 | 0-finding fallback (no fabrication) | VERIFIED | `:728-730` emits `no_significant_force_pattern_signal` warning + overall='low'. `test_no_signal_emits_fallback` PASS. `findings` length cap [0, 3] enforced at `ForcePatternInference.__post_init__` `:288-291` and `_rank_top3` early break `:638`. |
| D-09-B5 | (pattern, phase) dedup | VERIFIED | dedup loop at `:629-637` with `seen: set[tuple[str, str]]`. `test_pattern_dedup_same_phase` (dedups) + `test_pattern_dedup_different_phase_ok` (does NOT dedup) PASS. |
| D-09-C1 | Layer 2 (Gemini) 영구 차단 | VERIFIED | `grep -niE "(gemini\|cerebras\|openai\|anthropic)"` on force_pattern.py + force_pattern_copy.py → 0 functional imports/calls (2 docstring references only: `:165` "Phase 11 풍부화 source" comment, `:649` "Layer 2 (Gemini) 영구 차단 — D-09-C1" guard comment). Pure-function module — `numpy/dataclasses/types` imports only. |
| D-09-C2 | motion_id boost × 1.05 cap 1.0, BEFORE ranking | VERIFIED | `_apply_motion_id_boost` at `:575-587`, called at `:720-722` BEFORE `_rank_top3(:726)`. `test_motion_id_boost_changes_ranking` / `test_motion_id_boost_caps_at_one` / `test_motion_id_none_no_boost` → 3 PASS. |
| D-09-D1 | 3-way contract lockstep (TS + Python + docs) | VERIFIED | TS at `analysis.ts:653-712`, Python at `force_pattern.py:155-304`, docs at `contract.md §9.11`. `test_force_pattern_lockstep.py` 9 tests PASS. |
| D-09-D6 | mode_context inline (no helper) | VERIFIED | Pipeline inline at `app.py:1142-1150` — `MODE_EXPERT → 'mode1'`, MODE_SELF + `comparison.get('isFirst', True)` → `'mode3_first' or 'mode3_progress'`. No helper introduced. `test_pipeline_phase9.py` 5 cases PASS. |
| D-09-U1 | Wave 0 atomic commit | VERIFIED | `git show --stat defc973` → 11 files changed (1438 insertions): TS + force_pattern.py + firestore_admin.py + 5 tests + conftest + docs §9.11 + userAnalyses.ts. Exactly matches spec. |
| D-09-U5 | Firestore scoped validator | VERIFIED | `_validate_force_pattern_inference` at `firestore_admin.py:343-403`. `test_firestore_lockstep_phase9.py` 18 tests PASS (incl. nested-array reject + non-scalar reject + length>3 reject). |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 9 unit suite (full) | `cd backend && pytest tests/phase09/ tests/pipeline/test_pipeline_phase9.py -x -q` | **131 passed in 0.41s** | PASS |
| Forbidden phrase gate (SC#4) | `cd backend && pytest tests/phase09/test_force_pattern_copy_no_forbidden.py -v` | **11 passed** (8 substring + 2 regex + 1 AST) | PASS |
| AST severity guard (D-09-A2) | `cd backend && pytest tests/phase09/test_force_pattern_no_severity_use.py -v` | **2 passed** | PASS |
| 3-way contract lockstep (D-09-D1) | `cd backend && pytest tests/phase09/test_force_pattern_lockstep.py -v` | **9 passed** (TS literal + Python frozenset + docs §9.11 + warning codes) | PASS |
| Firestore validator (D-09-U5) | `cd backend && pytest tests/phase09/test_firestore_lockstep_phase9.py -v` | **18 passed** | PASS |
| Per-phase inference (SC#1) | `cd backend && pytest tests/phase09/test_infer_force_direction_pattern.py -v` | **29 passed** | PASS |
| Top-3 ranking + dedup (SC#2) | `cd backend && pytest tests/phase09/test_force_pattern_ranking.py -v` | **12 passed** | PASS |
| Pipeline integration | `cd backend && pytest tests/pipeline/test_pipeline_phase9.py -v` | **5 passed** | PASS |
| Direct grep — axis severity access | `grep -nE "axis.*\.severity" backend/shared/python/sunity_shared/analysis/force_pattern.py` | **0 hits** | PASS |
| Direct grep — LLM dependency (D-09-C1) | `grep -niE "(gemini\|cerebras\|openai\|anthropic)" force_pattern.py force_pattern_copy.py` | **0 functional hits** (2 docstring refs only) | PASS |
| Wave 0 atomic commit (D-09-U1) | `git show --stat defc973` | **11 files changed, 1438 insertions** | PASS |

---

## Regression Check

| Suite | Command | Result | Status |
|-------|---------|--------|--------|
| Phase 6/7/8/8.1 regression | `cd backend && pytest tests/phase06/ tests/phase07/ tests/phase08/ tests/phase08_1/ -x -q` | **408 passed, 1 skipped** | PASS |
| App typecheck | `cd app && npm run typecheck` (`tsc --noEmit`) | **0 errors** | PASS |
| Combined production suite | `cd backend && pytest tests/phase06/ tests/phase07/ tests/phase08/ tests/phase08_1/ tests/phase09/ tests/pipeline/ -q` | **550 passed, 1 skipped** | PASS — matches SUMMARY claim exactly |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FORCE-01 | 09-01, 09-02 | 중심축 이탈·접촉점 안정성·jerk/jitter 기초 신호로부터 ForceDirectionPattern 추론 + Top-3 카드. "근육 힘 방향" 단정 금지 | SATISFIED | SC#1–#4 all VERIFIED. 6 signal detection + Top-3 ranking + canned interpretation + forbidden phrase gate. REQUIREMENTS.md line 160 maps FORCE-01 → Phase 8, Phase 9 = Complete. |
| FEED-02 | 09-02 | 피드백 순서: 실패 원인 후보 3개 카드 → … 부위별 언어 (고관절·코어·내전근·광배 등) | SATISFIED | 18 canned KO bodies use 부위 어휘 (코어 / 고관절 / 내전근 / 광배 / 견갑 / 척추 / 호흡). `_JOINT_HINT_BY_SIGNAL` at `force_pattern_copy.py:161-168` maps 4 signals to 부위 키워드 + 2 to None (high_jerk/high_jitter where 부위 불명확). Phase 9 = "실패 원인 후보 3개 카드" — first item in FEED-02 sequence. REQUIREMENTS.md line 161 maps FEED-02 → Phase 9, Phase 11 = Complete (Phase 11 will add LLM enrichment). |

No orphaned requirements detected. REQUIREMENTS.md line 160-161 map FORCE-01 / FEED-02 to Phase 9 and both are claimed by 09-01-PLAN.md / 09-02-PLAN.md.

---

## Deviation Review (4 Items from SUMMARY.md)

### Deviation 1 — pelvis_drop test refactored to call `_detect_pelvis_drop` directly

**Classification:** Test-only refactor; correctness is by design.

**Analysis:** In production, pelvis_drop signal fires when `hip_tilt > 20° AND (hip_tilt - shoulder_tilt) > 10°`. When pelvis_drop fires, axis_tilt (`max(shoulder, hip) > 20°`) also necessarily fires (since hip > 20°). Both produce `(pattern='release', phase=same)` → D-09-B5 dedup keeps the first-sorted (axis_tilt by stable sort + identical confidence weight 1.0). Result: pelvis_drop never emits a distinct **finding** via the public path when axis_tilt also fires in the same phase.

This IS the intended behavior of D-09-B5 (pattern dedup eliminates same-pattern noise per phase). The user-visible joint_hint differs (axis_tilt='코어' vs pelvis_drop='고관절'), so the dedup loses a domain-relevant signal in the same phase — but this is acknowledged as v1 simplification (Wave 1 D-09-B5 + planner note + SUMMARY 'Deviations from Plan' section). The detection rule itself is correct and tested by direct `_detect_pelvis_drop` calls (3 tests covering emit, both-condition requirement, None-tilt safety). The Phase 11 LLM enrichment step + Phase 15 production sweep will surface whether this dedup compresses too aggressively.

**Verdict:** Acceptable. No correctness issue at Phase 9 v1 scope. Phase 11/15 follow-up flag.

### Deviation 2 — `isinstance(comparison, dict)` defensive guard added in pipeline wiring

**Classification:** Defensive, always-true on current code paths.

**Analysis:** `assemble.build_mode1` (line 214-229) and `assemble.build_mode3` (line 232-271) both return `dict` unconditionally. `_mode3_comparison` (line 749) returns the dict via `build_mode3(is_first=True/False, ...)`. The `isinstance(comparison, dict)` guard at `pipeline/app.py:1147` is always true today. It is benign future-refactor safety (e.g. if `_mode3_comparison` ever returns a dataclass). The 5 pipeline integration tests in `test_pipeline_phase9.py` pass with this guard in place.

**Verdict:** Acceptable. Defensive code, no runtime impact, no test masking.

### Deviation 3 — Pre-existing 11 collection errors in `backend/research/*` smoke/spike tests

**Classification:** Out-of-scope; pre-dates Phase 9.

**Analysis:** `pytest tests/ --collect-only -q` produces 11 collection errors:
```
ERROR tests/test_compare_engines_smoke.py
ERROR tests/test_debug_gap_root_cause_smoke.py
ERROR tests/test_gemini_motion_classify_spike.py
ERROR tests/test_mapping_audit.py
ERROR tests/test_pole_detector.py
ERROR tests/test_spike_gemini_moment_smoke.py
ERROR tests/test_spike_measurement_trace.py
ERROR tests/test_spike_measurement_trace_smoke.py
ERROR tests/test_spike_mediapipe_to_h36m17.py
ERROR tests/test_spike_rtmpose_to_h36m17.py
ERROR tests/test_sweep_rtmpose_smoke.py
```
All fail on `ModuleNotFoundError: No module named 'backend'` from `from backend.research.*` imports. These files were added in Phase 1 commits (6255380 / 84c249a / b87fe7c / 6e1d328 — pre-Phase 9 by months). The `deferred-items.md` documents this with explicit Phase-1 commit citation. Phase 9 did not introduce these errors and Phase 9 production suite (550 PASS) excludes them.

**Verdict:** Acceptable. Pre-existing; documented in `deferred-items.md`; production suite uncompromised.

### Deviation 4 — `git stash` misuse twice during verification

**Classification:** Procedural only; no artifact impact.

**Analysis:** Both stashes were immediately recovered via `git stash pop`; SUMMARY.md self-reports the violation. No data lost. No shipped artifact modified.

**Verdict:** Informational only. Process note recorded.

---

## Wave 2 OUT Verification (D-09-E2)

| Check | Expected | Observed | Status |
|-------|----------|----------|--------|
| No RunPod redeploy commit | 0 commits | 0 commits — git log since defc973 shows no RunPod reference | PASS |
| No 정은지 sweep | 0 sweep artifact | 0 SWEEP-EVIDENCE.md / no sweep test fixture | PASS |
| No production validation work | 0 validation commit | 0 validation commit; only schema + inference + wiring | PASS |

Wave 2 production sweep correctly OUT of scope per D-09-E2 (natural validation defers to Phase 11 LLM integration + Phase 15 TestFlight).

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No debt markers (TBD/FIXME/XXX) in shipped files | — | None |
| (none) | — | No PLACEHOLDER / "not implemented" / empty handlers in shipped files | — | None |
| (none) | — | No hardcoded data flowing to user output | — | None |

Anti-pattern scan on the 11 shipped files in Wave 0 + 4 shipped/modified in Wave 1 → 0 blockers.

---

## Probe Execution

Phase 9 is a pure-function backend phase. No `scripts/*/tests/probe-*.sh` exists for Phase 9 (verified by `find scripts -path '*/tests/probe-*.sh' -type f` — Phase 8.1 has probes; Phase 9 plans declare none). The pytest suites listed under Behavioral Spot-Checks ARE the probe equivalents.

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| (no formal probe) | — | — | N/A — covered by behavioral spot-checks above |

---

## Human Verification Required

Phase 9 = backend-only (D-09-D5: UI hint = 없음). Wave 2 production sweep deferred to Phase 11/15. The 18 canned KO interpretation bodies should be reviewed by belle for tone (research §10.1 — possibility language + 부위 어휘) and pelvis_drop pipeline-dedup acceptability, but this is the follow-up belle check named in SUMMARY.md's "Follow-ups" section, not a verifier-blocking gate. No mandatory human verification items remain.

---

## Gaps Summary

No gaps. All 4 Success Criteria are VERIFIED with concrete file:line citations and passing pytest evidence. All 13 locked decision items checked are VERIFIED. Pre-existing test collection errors (deviation 3) are pre-Phase 9 and documented in `deferred-items.md`. Regression suite (408 PASS phase 6-8.1) and combined production suite (550 PASS / 1 skipped) are green. TS `tsc --noEmit` is 0 errors.

Phase 9 goal — "기초 신호를 종합해 `ForceDirectionPattern`을 추론하고, 동작 실패 원인 후보 3개를 카드 형태로 제시한다 (단정 금지, '가능성' 언어)" — is achieved end-to-end: pipeline `_process` calls `infer_force_direction_pattern` after `compute_force_signals`, the inference produces Top-3 findings with canned possibility-language interpretation, the result is written to Firestore `result.forcePatternInference` via the scoped validator, and the TS contract exposes the field to the app with a null-safe normalize path.

---

_Verified: 2026-06-10_
_Verifier: Claude (gsd-verifier)_
