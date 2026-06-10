---
phase: 09
slug: forcedirectionpattern-3
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 09-RESEARCH.md §Validation Architecture (2026-06-10). Wave 2 production sweep OUT of scope (D-09-E2).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend) + tsc --noEmit (app) |
| **Config file** | `backend/requirements-dev.txt` + `backend/tests/conftest.py` (Phase 8 박제 패턴) — Phase 9 신설 `backend/tests/phase09/conftest.py` (Wave 0) |
| **Quick run command** | `cd backend && pytest tests/phase09/ -x -q` |
| **Full suite command** | `cd backend && pytest tests/ -x && cd ../app && npm run typecheck` |
| **Estimated runtime** | ~15 seconds (phase09 only) / ~90 seconds (full backend suite + tsc) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/phase09/ -x -q`
- **After every plan wave:** Run `cd backend && pytest tests/ -x && cd ../app && npm run typecheck`
- **Before `/gsd-verify-work`:** Full suite + tsc --noEmit + 금지 표현 grep gate 10/10 PASS
- **Max feedback latency:** 15 seconds (per-task), 90 seconds (per-wave)

---

## Per-Task Verification Map

> Task IDs follow `{phase}-{plan}-{task}` shape per gsd-planner convention. Filled in by planner; rows below seed each Wave's verification surface from RESEARCH §Phase Requirements → Test Map.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-W0-S1 | Wave 0 | 0 | D-09-D1 / FORCE-01 | T-09-V5 (input validation) | 3-way schema lockstep (TS Literal union ↔ Python frozenset ↔ docs §9.11) | unit | `pytest tests/phase09/test_force_pattern_lockstep.py -x` | ❌ Wave 0 | ⬜ pending |
| 09-W0-S2 | Wave 0 | 0 | D-09-U4 | — | camelCase 변환 (source_signal/joint_hint/mode_context) | unit | `pytest tests/phase09/test_dataclass_to_camel_case_dict_phase9.py -x` | ❌ Wave 0 | ⬜ pending |
| 09-W0-S3 | Wave 0 | 0 | D-09-U5 | T-09-T2 (nested-array tampering) | `_validate_force_pattern_inference` rejects nested dict / list[list] / non-scalar warnings | unit | `pytest tests/phase09/test_firestore_lockstep_phase9.py -x` | ❌ Wave 0 | ⬜ pending |
| 09-W0-S4 | Wave 0 | 0 | D-09-U3 | T-09-V5 | Frozen dataclass `__post_init__` validators (enum + confidence [0,1] + interpretation non-empty) | unit | `pytest tests/phase09/test_force_pattern_dataclass.py -x` | ❌ Wave 0 | ⬜ pending |
| 09-W1-I1 | Wave 1 | 1 | FORCE-01 SC#1 / D-09-A1 | — | 6 signal detection rules + phase 별 finding emit | unit | `pytest tests/phase09/test_infer_force_direction_pattern.py -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-I2 | Wave 1 | 1 | D-09-A2 (CORE GUARD) | T-09-T1 (signal misuse) | `force_pattern.py` AST 안 `axisMetric.severity` 액세스 0회 + axis warnings 무시 룰 | unit + AST grep | `pytest tests/phase09/test_force_pattern_no_severity_use.py -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-I3 | Wave 1 | 1 | D-09-A4 | — | phaseBoundaries 미인식 fallback (phase_unavailable_for_inference warning) | unit | `pytest tests/phase09/test_infer_force_direction_pattern.py::test_phase_unavailable_fallback -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-I4 | Wave 1 | 1 | D-09-A5 | — | confidence = base × phase_metric_confidence_factor (min of axis.confidence, stability.confidence) | unit | `pytest tests/phase09/test_infer_force_direction_pattern.py::test_confidence_formula -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-R1 | Wave 1 | 1 | FORCE-01 SC#2 / D-09-B1/B2 | — | Top-3 ranking (score = confidence × signal_weight) | unit | `pytest tests/phase09/test_force_pattern_ranking.py::test_top3_ranking_with_signal_weight -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-R2 | Wave 1 | 1 | D-09-B3 | — | tie-break (phase priority → signal priority → confidence DESC) | unit | `pytest tests/phase09/test_force_pattern_ranking.py::test_tie_break_order -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-R3 | Wave 1 | 1 | D-09-B4 | T-09-S1 (fabrication) | 0 finding 시 `no_significant_force_pattern_signal` + fallback 본문, length [0,3] | unit | `pytest tests/phase09/test_infer_force_direction_pattern.py::test_no_signal_emits_fallback -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-R4 | Wave 1 | 1 | D-09-B5 | — | 동일 pattern 같은 phase 중복 차단, 다른 phase 는 OK | unit | `pytest tests/phase09/test_force_pattern_ranking.py::test_pattern_dedup_by_phase -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-R5 | Wave 1 | 1 | D-09-C2 | — | motion_id 인식 시 confidence × 1.05 cap 1.0 (ranking 전 적용) | unit | `pytest tests/phase09/test_force_pattern_ranking.py::test_motion_id_boost_before_ranking -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-C1 | Wave 1 | 1 | FEED-02 / D-09-D2 | T-09-T3 (canned escape) | 18 canned (sourceSignal × modeContext) lookup + mode 분기 prefix | unit | `pytest tests/phase09/test_force_pattern_copy_render.py -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-C2 | Wave 1 | 1 | FORCE-01 SC#3,#4 / D-09-D3 | T-09-R1 (단정 표현 회귀) | AST 금지 표현 grep gate 10/10 (research §10.2 6종 + 신규 4종) + `\d+%\s*감점` regex | unit (AST grep gate) | `pytest tests/phase09/test_force_pattern_copy_no_forbidden.py -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-C3 | Wave 1 | 1 | D-09-D1 (jointHint) | — | sourceSignal → jointHint 부위 어휘 매핑 (null 허용) | unit | `pytest tests/phase09/test_force_pattern_copy_render.py::test_joint_hint_mapping -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-P1 | Wave 1 | 1 | D-09-D6 | — | pipeline `_process` mode_context 산출 (mode1 / mode3_first / mode3_progress) + `infer_force_direction_pattern` 호출 | integration | `pytest tests/phase09/test_force_pattern_pipeline_wiring.py -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-P2 | Wave 1 | 1 | D-09-U1 (lockstep) | — | `complete_analysis(force_pattern_inference=...)` 시그니처 + `forcePatternInference` Firestore key | integration | `pytest tests/phase09/test_force_pattern_pipeline_wiring.py::test_complete_analysis_invocation -x` | ❌ Wave 1 | ⬜ pending |
| 09-W1-F1 | Wave 1 | 1 | D-09-U1 (frontend) | — | `userAnalyses.ts::normalize` 가 forcePatternInference null-guard + findings null-guard | typecheck | `cd app && npm run typecheck` | ❌ Wave 1 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase09/__init__.py` — empty package marker
- [ ] `backend/tests/phase09/conftest.py` — fixture factories (`_make_axis_metric`, `_make_stability_metric`, `_make_contact_metric`, `_make_phase_boundary`)
- [ ] `backend/tests/phase09/fixtures/` — dataclass factory helpers (frozen instances for inference test cases)
- [ ] `backend/tests/phase09/test_force_pattern_lockstep.py` — 3-way schema lockstep (mirrors Phase 8 `test_force_signals_lockstep.py`)
- [ ] `backend/tests/phase09/test_dataclass_to_camel_case_dict_phase9.py` — camelCase 변환 (mirrors Phase 7)
- [ ] `backend/tests/phase09/test_firestore_lockstep_phase9.py` — `_validate_force_pattern_inference` (mirrors Phase 8 `test_firestore_lockstep.py`)
- [ ] `backend/tests/phase09/test_force_pattern_dataclass.py` — `__post_init__` validators (enum, confidence range, interpretation non-empty)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 18 canned KO interpretation 본문 톤 + "가능성" 언어 + 부위 어휘 적절성 | FORCE-01 SC#3 / FEED-02 / D-09-D2 | 톤 / 의미적 적절성은 자동 grep 으로 잡히지 않음 (금지 표현은 자동 — D-09-D3) | belle 가 Wave 1 종료 시 18 canned 본문 + jointHint 부위 어휘 매핑 검수. [[no-baekje-filler]] 정합 — 박제 단어 남용 금지. 검수 PASS 시 D-09-E3 follow-up 해제. |
| pelvis_drop 임계 정량값 (RESEARCH Assumption A1 — `hip_tilt - shoulder_tilt > 10° AND hip_tilt > 20°`) | D-09-A1 | belle 의 정은지 25 sample 분포 도메인 판단 필요 | belle 가 Wave 1 코드 박제 직후 임계값 확인 + 필요시 plan 변경 (작은 추가 plan). 변경 시 RESEARCH §"Pitfall 1" 박제 갱신. |
| Wave 2 production sweep — Phase 9 finding 분포 (정은지 0~1 low + 학생 1~3 medium) | D-09-E2 | 실 영상 검증 = Phase 11 / Phase 15 책임 (본 phase OUT of scope) | Phase 11 (CoachCommentHook + Gemini 자연어 번역) 통합 시점 자연 검증. Phase 15 (Mode 1·Mode 3 실영상 + TestFlight) 가 종합 production validation. |

---

## Threat Reference

Threat refs cited above (per RESEARCH §Security Domain):

| ID | STRIDE | Source |
|----|--------|--------|
| T-09-T1 | Tampering | `axisMetrics.severity` 직접 사용 회귀 (D-09-A2 raw signal only guard 위반) |
| T-09-T2 | Tampering | Firestore nested-array 박제 (D-09-U5 / [[firestore-nested-array-flat]] 정합) |
| T-09-T3 | Tampering | canned 본문 외부 입력 inject — Phase 9 = 모듈 dict literal singleton 만 |
| T-09-V5 | Input Validation (ASVS V5) | Untrusted ForceSignalsReport 입력 — frozen dataclass validator + scoped Firestore validator 2 축 |
| T-09-S1 | Spoofing | confidence 조작 / fabrication 0 — D-09-B4 정합 |
| T-09-R1 | Repudiation | refactor 시 단정 표현 회귀 — AST grep gate 10/10 CI 차단 |

---

## Regression Gate (Existing Suites)

- `cd backend && pytest tests/phase06/ tests/phase07/ tests/phase08/ tests/phase08_1/ -x` — Phase 9 wave 1 종료 시 모두 PASS 검증 (Phase 8 8/8 / Phase 8.1 25/25 evidence 회귀 0).
- `cd app && npm run typecheck` — TS strict mode + ForcePatternInference / ForcePatternFinding 신설 type compile.
- `git diff app/src/types/analysis.ts backend/shared/python/sunity_shared/analysis/force_pattern.py docs/contract.md` — Wave 0 atomic commit lockstep manual check.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (Wave 0 task 7개 박제, Wave 1 task 14개 박제 — manual-only 3건 분리)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (Wave 0/1 all automated, manual-only 3 건은 별도 트랙 — belle 검수 / belle 임계값 검수 / Phase 11·15 통합 검증)
- [ ] Wave 0 covers all MISSING references (7개 신설 파일 박제)
- [ ] No watch-mode flags (모든 command 가 `-x -q` 단발성)
- [ ] Feedback latency < 90s (full suite + tsc)
- [ ] `nyquist_compliant: true` set in frontmatter (planner 박제 완료 후)

**Approval:** pending
