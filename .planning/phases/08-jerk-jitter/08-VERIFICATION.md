---
phase: 08-jerk-jitter
verified: 2026-06-09T16:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
follow_up:
  phase: 08.1-axis-metric-redesign
  reason: "axis distance metric 의 도메인 정합성 위반 (정은지 5/5 영상 모든 phase severity='high'). schema/wiring 측면은 정상 — Phase 8 본 phase 의 success criteria 는 산출 측면에서 만족. 수치 의미 부여는 Phase 8.1 책임."
  evidence_source: ".planning/phases/08-jerk-jitter/PHASE8-INHERITED-ISSUES.md"
  belle_decision: "α (Phase 8.1 신설) — 2026-06-09"
---

# Phase 8: 중심축 이탈 + 접촉점 안정성 + jerk/jitter — Verification Report

**Phase Goal (ROADMAP.md L230):** 힘 방향 패턴 추론에 필요한 기초 신호(중심축 이탈, 접촉점 안정성, 흔들림, jerk)를 phase별로 산출한다 — 가림 스무딩 필수
**Verified:** 2026-06-09T16:00:00Z
**Status:** passed (complete-with-follow-up)
**Re-verification:** No — initial verification

---

## Verdict (TL;DR)

**Phase 8 본 phase 의 4 success criteria 모두 코드 박제 측면에서 VERIFIED.** ForceSignalsReport schema + wiring + 4 metric 산출 함수 + temporal smoothing + reliability/confidence 가중 모두 코드에서 확인. 정은지 5/5 영상 axis severity='high' 도메인 정합성 문제는 **수치 의미 부여 (threshold calibration + 좌표계 origin)** 영역 — 본 verifier 가 검증하는 Phase 8 success criteria 는 schema 산출과 phase-별 출력을 요구할 뿐 "정은지 baseline=low" 를 요구하지 않음. belle α 결정 (2026-06-09) 에 따라 Phase 8.1 (axis-metric-redesign) 가 분리 처리.

**핵심 caveat (정직한 박제):** SC #1 의 *artifact* 는 만족하지만, 산출된 *수치의 도메인 의미* 는 axis distance 측면에서 미신뢰. tilt 차원은 의미 보존 (정은지 5영상 10~58° 자연 분포). Phase 9 force_pattern 추론은 tilt + stability + contact 위에 평행 진입 가능, axis distance 는 Phase 8.1 후 정상화.

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth                                                                                                                                                          | Status     | Evidence                                                                                                                                                                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `AxisDeviationMetric`(골반/흉곽 폴축 거리, 어깨/골반 tilt, deviation 방향)이 phase별로 산출된다                                                              | ✓ VERIFIED (schema/output) — see caveat | `force_signals.py:272` 클래스 정의 + `force_signals.py:1037` `compute_axis_deviation` 함수 + pipeline wiring `pipeline/app.py:1118` + TS `analysis.ts:535-551`. 5 phase × 5 영상 = 25 metric 산출 확인 (PHASE8-INHERITED-ISSUES.md §1). distance 수치 의미는 Phase 8.1 책임 |
| 2   | `StabilityMetric`(jitterScore, jerkScore, holdStabilityScore, unstableBodyParts)이 phase별로 산출된다                                                          | ✓ VERIFIED | `force_signals.py:336` 클래스 + `force_signals.py:1291` `compute_stability_metrics` + 4 필드 모두 박제 (TS `analysis.ts:564-578`). FPS-normalized jerk (`jerkUnit='deg_per_sec_cubed'`). `dimensions.stability_wobble()` direct import (drift defense) |
| 3   | `ContactStabilityMetric`(접촉점별 estimatedStable, lostContactAtMs, confidence)이 phase별로 산출된다                                                          | ✓ VERIFIED | `force_signals.py:375` 클래스 + `force_signals.py:1513` `compute_contact_stability` + evidence-with-confidence (R3) schema (estimatedStable nullable, distanceToPoleNorm/nearPoleRatio/lostNearPoleAtMs 신설). `contact_points.yaml` 5 motion + default. 25 contact × 5 phase 정상 산출 |
| 4   | 모든 신호에 시간적 스무딩이 적용되고 가림 프레임은 confidence로 가중 처리된다                                                                                 | ✓ VERIFIED | `pipeline/app.py:418/446/525` `temporal_fill(angles, joint_uncertainty(keypoints))` 1회 적용 (double smoothing 차단). `force_signals.py:189` `LOW_RELIABILITY_PHASE_THRESHOLD=0.4` + L1199/L1336-1342 phase 내 frame `reliability` 비율 → `confidence` + `warnings.append("occlusion_high_in_phase")`. preflight gate 3-state (`_layer1_confidence_from_preflight`) |

**Score:** 4/4 truths verified.

---

### Required Artifacts (Level 1+2+3+4)

| Artifact                                                                                  | Expected                                       | Status     | Details                                                                                                                                                                                                                            |
| ----------------------------------------------------------------------------------------- | ---------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/shared/python/sunity_shared/analysis/force_signals.py`                          | 5 dataclass + 5 public function + Layer 1/2    | ✓ VERIFIED | 1829 lines, 5 dataclass (PhaseBoundary L237 / AxisDeviationMetric L272 / StabilityMetric L336 / ContactStabilityMetric L375 / ForceSignalsReport L429), 5 public compute_* + umbrella, wired via `pipeline/app.py:61` + L1118 |
| `backend/shared/python/sunity_shared/analysis/pole_geometry.py`                          | PoleLine2D + PoleAxisMeasurement + invariant   | ✓ VERIFIED | Plan 08-00 산출 — invariant `line=None ↔ coordinate_space='unavailable'` 강제. `pipeline/app.py:_extract_video_analysis_inputs` 사용. SUMMARY commits 2261dc5 / 928c6d4 / 80c353e |
| `backend/shared/python/sunity_shared/analysis/body_scale.py`                              | median_torso_length + drift defense            | ✓ VERIFIED | space 3분기 (image_2d / world_3d / pole_aligned), BodyNormalizationProfile import 영구 차단 (AST gate). `force_signals.py` 의 distance denominator 단일 source |
| `backend/shared/python/sunity_shared/models.py`                                          | Python re-export (3-way lockstep)             | ✓ VERIFIED | L183-193 `from .analysis.force_signals import (...)` active import (Plan 08-02 활성화) |
| `app/src/types/analysis.ts`                                                              | TS interfaces lockstep                         | ✓ VERIFIED | L512 PhaseBoundary / L535 AxisDeviationMetric / L564 StabilityMetric / L592 ContactStabilityMetric / L628 ForceSignalsReport. AnalysisResult.forceSignalsReport (L198 optional nullable) |
| `docs/contract.md` §9                                                                     | docs lockstep — 10 subsection + 20 warning code | ✓ VERIFIED | L642 §9.0 (Coordinate/Scale pre-contract) + L793 §9 (ForceSignalsReport) + L926 §9.8 warning code enum (20 codes) |
| `backend/functions/pipeline/app.py` (wiring)                                              | compute_force_signals 1줄 호출 + complete_analysis kwarg | ✓ VERIFIED | L1117-1140 — `_get_force_signals_layer2_recognizer()` singleton + `fs.compute_force_signals(...)` + `_dataclass_to_camel_case_dict` + `complete_analysis(force_signals_report=...)` |
| `backend/shared/python/sunity_shared/firestore_admin.py` (scoped validator)              | `_validate_force_signals_report` (Cycle 2 NEW HIGH #3) | ✓ VERIFIED | L148 `_validate_force_signals_report` 신설 + L273-320 `complete_analysis(force_signals_report=)` kwarg. `_validate_dict_only_scalars` 본체 변경 영구 0 ([[firestore-nested-array-flat]] 보존) |
| `app/src/lib/userAnalyses.ts` (normalize null-guard)                                     | forceSignalsReport null-guard (WR-02 B1 패턴)  | ✓ VERIFIED | L74-88 — `result?.forceSignalsReport` 분기 + 7 필드 default (version / overallConfidence / warnings / phaseBoundaries / axisMetrics / stabilityMetrics / contactMetrics) |
| `backend/judging_data/contact_points.yaml`                                                | 5 motion entry + default + kind 동행            | ✓ VERIFIED | Plan 08-01 산출 (commit a31f893). 5 motion (ref-invert / ref-foxtop / ref-foxtop-split / ref-climb / ref-sideway-spin) + default empty. ContactPrimitiveKind 분기 (keypoint/segment/region_proxy) 정합 |

**Score:** 10/10 artifacts VERIFIED at all 4 levels (exists, substantive, wired, data flowing).

---

### Key Link Verification

| From                              | To                                       | Via                                                              | Status   | Details                                                                                                                          |
| --------------------------------- | ---------------------------------------- | ---------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `pipeline/app.py::_process`       | `force_signals.compute_force_signals`    | direct call L1117-1127, pose_frames + pole_axis_measurement 전달 | ✓ WIRED   | `from sunity_shared.analysis import force_signals as fs` L61 + `fs.compute_force_signals(...)` L1118                            |
| `force_signals.py`                | `dimensions.stability_wobble()`          | direct import (drift defense)                                    | ✓ WIRED   | Plan 08-01 helper 분리 + Plan 08-02 import 강제. test_drift_defense (abs<1e-9)                                                  |
| `force_signals.py`                | `body_scale.median_torso_length`          | denominator helper                                                | ✓ WIRED   | image_2d / pole_aligned 분기 시 직접 호출. BodyNormalizationProfile 영구 차단 (static check `grep -c == 0`)                       |
| `pipeline/app.py`                 | `temporal.temporal_fill`                  | `_extract_video_analysis_inputs` 1회 적용 후 angles 전달          | ✓ WIRED   | L76 import + L418/446/525 단일 호출. `force_signals.py` 안 0회 (double smoothing 차단)                                          |
| `force_signals.py`                | `technique.TechniqueProfile.key_moments`  | Layer 2 reuse (REVIEWS R6)                                       | ✓ WIRED   | Plan 08-03 R6 — `compute_phase_boundaries(technique_profile=...)` kwarg + `_layer2_boundaries_from_technique_profile` 분기      |
| `force_signals.py`                | env probe (FORCE_SIGNALS_LAYER2_ENABLED) | `_force_signals_layer2_env_enabled()`                            | ✓ WIRED   | Plan 08-03 R7 separation. default off 시 Layer 1 단독 path                                                                       |
| `pipeline/app.py`                 | env probe (PREFLIGHT_LABEL_GATE_PASSED)   | `_preflight_label_gate_passed()` 3-state helper                  | ✓ WIRED   | Cycle 2 NEW HIGH #1. L1125 `preflight_label_gate_passed=_preflight_label_gate_passed()` 직접 전달                                |
| `firestore_admin.complete_analysis` | `_validate_force_signals_report`         | scoped validator (NEW HIGH #3)                                   | ✓ WIRED   | L319 `_validate_force_signals_report(force_signals_report)` 후 `payload["result"]["forceSignalsReport"]` 박제                  |
| `app/src/lib/userAnalyses.ts`     | `AnalysisDoc.forceSignalsReport`         | normalize null-guard                                              | ✓ WIRED   | L74-88. 7 필드 default + immutable spread                                                                                       |

**Score:** 9/9 key links VERIFIED.

---

### Data-Flow Trace (Level 4)

| Artifact                                  | Data Variable                                    | Source                                                                          | Produces Real Data | Status      |
| ----------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------- | ------------------ | ----------- |
| `force_signals.compute_force_signals`     | `ForceSignalsReport.phase_boundaries`            | `compute_phase_boundaries` (Layer 1 휴리스틱 + Layer 2 technique_profile reuse) | Yes (5 phase 분할 산출)         | ✓ FLOWING (sweep 3차 정은지 5/5 영상 5 phase 정상 분할) |
| `force_signals.compute_force_signals`     | `ForceSignalsReport.axis_metrics`                 | `compute_axis_deviation` (pole_aligned 3D fallback path B' 활성)               | Partial — schema 산출 ✓, distance 수치 의미 ✗ | ⚠️ HOLLOW (caveat) — 5/5 영상 severity='high' 출력. Phase 8.1 redesign 책임 |
| `force_signals.compute_force_signals`     | `ForceSignalsReport.stability_metrics`            | `compute_stability_metrics` + `dimensions.stability_wobble`                       | Yes (jerkScore deg/sec^3 + jitterScore + holdStabilityScore + unstableBodyParts) | ✓ FLOWING (sweep low/medium 혼합 분포 자연스러움) |
| `force_signals.compute_force_signals`     | `ForceSignalsReport.contact_metrics`              | `compute_contact_stability` + `contact_points.yaml` + 3 ContactPrimitiveKind 분기 | Yes (25 contact × 5 phase 정상 산출, 3 분기 lookup) | ✓ FLOWING |
| `pipeline/app.py::_process`               | `force_signals_dict` → Firestore                  | `_dataclass_to_camel_case_dict(force_signals_report)`                            | Yes                | ✓ FLOWING (sweep_phase8_1780986673 Firestore docs 5/5 schema 정합) |
| `app/src/lib/userAnalyses.ts::normalize`  | `AnalysisDoc.result.forceSignalsReport`           | Firestore raw → normalize null-guard                                              | Yes                | ✓ FLOWING (7 필드 default + 실 sweep 결과 read 가능)               |

**Score:** 5/6 data flows VERIFIED ✓, 1/6 ⚠️ HOLLOW (axis distance, Phase 8.1 책임). 본 HOLLOW 는 ROADMAP success criteria #1 의 *artifact 산출 측면* 은 만족 (schema 출력 + phase별 metric list 산출) — 단지 수치 의미가 도메인적으로 미신뢰. 본 verifier 의 책임 영역 (codebase 의 산출 존재) 에서는 ✓.

---

### Behavioral Spot-Checks

| Behavior                                                                          | Command                                                                                  | Result                                                                                  | Status     |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ---------- |
| `force_signals.py` 모듈 import 가능                                              | `python -c "from sunity_shared.analysis import force_signals"`                          | Plan 08-02 commit 6b4dd16 후 active import, models.py L183 active                       | ✓ PASS     |
| `compute_force_signals` 5 public function 노출                                   | `grep -E "^def compute_" force_signals.py`                                              | 4 public (compute_phase_boundaries / compute_axis_deviation / compute_stability_metrics / compute_contact_stability) + 1 umbrella (compute_force_signals) = 5 | ✓ PASS     |
| Firestore scoped validator `_validate_force_signals_report` 존재                  | `grep -c "_validate_force_signals_report" firestore_admin.py`                            | L148 정의 + L319 호출 = 2+ matches                                                       | ✓ PASS     |
| TS strict mode 통과 (`tsc --noEmit`)                                              | Plan 08-03 SUMMARY L264 verified                                                          | exit 0                                                                                  | ✓ PASS     |
| 358 PASS + 1 skipped (phase06 156 + phase07 88 + pipeline 11 + phase08 103)       | Plan 08-03 SUMMARY L262 verified                                                          | 358 PASS                                                                                | ✓ PASS     |
| 3차 sweep 정은지 5영상 Firestore docs 직접 조회 가능                              | PHASE8-INHERITED-ISSUES.md §1 + §9 박제 (`sweep_phase8_1780986673` 5 doc ids)             | 5/5 영상 schema 정합 + axis distance 산출 + 0 server_error                              | ✓ PASS     |

**Score:** 6/6 spot-checks PASS.

---

### Probe Execution

본 phase 는 migration/tooling phase 아님. 별도 `scripts/*/tests/probe-*.sh` 미박제. SUMMARY 의 PASS marker (358 PASS) 는 본 verifier 의 코드 박제 직접 확인 위에 보조 evidence — 이미 위 spot-check 6 에 박제됨. 별도 probe 실행 없음.

**Status:** N/A (probe-based verification 대상 phase 아님)

---

### Requirements Coverage

| Requirement | Source Plan       | Description                                            | Status     | Evidence                                                                                       |
| ----------- | ----------------- | ------------------------------------------------------ | ---------- | ---------------------------------------------------------------------------------------------- |
| FORCE-01    | 08-00 / 08-02 / 08-03 frontmatter `requirements-completed` | 힘 패턴 추론을 위한 기초 신호 (Phase 8) + 패턴 추론 (Phase 9) | ✓ SATISFIED (Phase 8 측면) | 4 metric 산출 함수 + ForceSignalsReport 3-way lockstep + pipeline wiring + Firestore 저장 + frontend normalize 전체 박제. Phase 9 의 force pattern 추론 분기는 Phase 9 책임 (Phase 8 입력 source 제공 측면 ✓) |

**Score:** 1/1 requirement SATISFIED (Phase 8 측면 scope 한정).

---

### Anti-Patterns Found

| File                                             | Line  | Pattern                                                | Severity | Impact                                                                                                                          |
| ------------------------------------------------ | ----- | ------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `force_signals.py` (compute_axis_deviation pole_aligned fallback) | 1037+ | 정은지 5/5 영상 severity='high' — 도메인 정합성 위반   | ⚠️ WARNING — Phase 8.1 분리 처리 (belle α 결정 2026-06-09) | schema/wiring 측면 정상, 수치 의미 (좌표계 origin + threshold 단위) 미정합. tilt 차원은 보존 — Phase 9 평행 진입 가능. PHASE8-INHERITED-ISSUES.md §2 root cause 박제 |

스캔 한 다른 패턴 (전체 PHASE 8 modified files):
- TBD/FIXME/XXX 마커 0 (force_signals.py / firestore_admin.py / pipeline/app.py / analysis.ts / userAnalyses.ts grep)
- 빈 `return null / return {}` stub 패턴 0 (모든 compute_* 함수 본체 구현됨)
- console.log only 패턴 0 (frontend normalize null-guard 만, 실제 spread 적용)
- Hardcoded empty data 0 (compute 함수의 실제 numpy 계산 결과 반환)

**Score:** 0 BLOCKER + 1 WARNING (Phase 8.1 inherited issue, 분리 처리 박제).

---

### Human Verification Required

Phase 8 의 본체 success criteria 는 코드 박제로 검증 완료 — 별도 human verification 필요 항목 없음.

**단, belle 운영 작업 (Phase 8 종료 차단 X):**

1. **preflight_label_template.csv 25 row 채우기** (Plan 08-00 박제 spec) — belle 도메인 시각 라벨링. ≥80% PASS 시 Lambda env `PREFLIGHT_LABEL_GATE_PASSED=1` 박제 → Layer 1 confidence='medium' 승급 (코드 변경 0, [[analysis-objectivity-no-human-scores]] 정합 — 시각 라벨링 X 점수 라벨링).
2. **contact_points.yaml 5 motion entry 도메인 검수** — belle/강사 IPSF Code of Points + 학원 정의 정합 검증. graceful fallback (default empty + warning 'motion_unrecognized') 박제 — Phase 8 종료 차단 X.

두 항목 모두 graceful path 박제 — 본 verification 의 status 영향 0.

---

### Phase 8.1 Follow-up Scope (Inherited Issue)

본 verifier 가 명시 박제: Phase 8 의 본 success criteria 는 만족 (4/4 ✓), 단 axis distance 차원의 도메인 정합성은 Phase 8.1 의 책임.

**Phase 8.1 (axis-metric-redesign, ROADMAP L248-265):**

- **Goal:** axis distance metric 의 좌표계 origin 정의 + threshold 단위 재설계 + 정은지 baseline=low 출력
- **Single evidence source:** `.planning/phases/08-jerk-jitter/PHASE8-INHERITED-ISSUES.md` (정은지 5영상 sweep raw distance/severity/tilt 분포 + root cause + 의사결정 공간 α-1~4 / β-1~3 + 외부 AI reviewer 5 핵심 질문)
- **Scope 보존:** tilt 데이터 (shoulder/hip rotation-only, origin-invariant) + schema (ForceSignalsReport + coordinate_space enum) 보존, Phase 9 가 tilt + stability + contact 위에 평행 진입 가능
- **belle 결정 (2026-06-09):** α (Phase 8.1 신설) 진행. NotebookLM IPSF Code of Points 활용

**본 verifier 의 정직한 박제:** Phase 8 의 ROADMAP success criteria #1 은 *"AxisDeviationMetric (...) 이 phase별 산출된다"* — "산출" 측면 (artifact + schema + phase 분기) 만족. "값 자체의 도메인 정합성" 은 요구 사항에 명시 X — 단, [[feedback-analysis-first]] 메모 정신상 분석 정확도가 최우선이므로 belle 가 즉시 후속 phase 박제 결정 (정상 박제 정신).

---

### Gaps Summary

**No blocking gaps.** Phase 8 본체 success criteria 4/4 만족. axis distance 수치 의미 부여는 Phase 8.1 분리 scope — belle 명시 결정 (α, 2026-06-09) 정합.

**Caveat (정직):** SC #1 의 *artifact* 산출 측면은 ✓ VERIFIED, *수치 의미* 측면은 Phase 8.1 책임. 본 verifier 가 두 측면을 분리 박제. Phase 9 (force_pattern 추론) 진입 시 axis distance 차원은 Phase 8.1 후 사용, tilt + stability + contact 는 평행 진입 가능 (PHASE8-INHERITED-ISSUES.md §3 박제).

---

## Verification Summary

| Category | VERIFIED | TOTAL |
|----------|----------|-------|
| Observable Truths (ROADMAP SC) | 4 | 4 |
| Required Artifacts (Level 1+2+3) | 10 | 10 |
| Data-Flow Trace (Level 4) | 5 (+1 HOLLOW caveat) | 6 |
| Key Links | 9 | 9 |
| Behavioral Spot-Checks | 6 | 6 |
| Requirements (FORCE-01) | 1 | 1 |
| Anti-Patterns | 0 BLOCKER (1 WARNING → Phase 8.1) | — |
| Human Verification Items | 0 BLOCKING (2 belle 운영 작업, graceful path 박제) | — |

**Overall:** Phase 8 본 phase 의 책임 영역 (4 metric 산출 + temporal smoothing + confidence 가중 + 3-way lockstep + pipeline wiring + Firestore + frontend) 100% 박제. axis distance 수치 의미 부여 = Phase 8.1 (axis-metric-redesign) 책임 — belle 명시 결정 정합.

**Verdict:** `passed` (complete-with-follow-up). Phase 8 종료 가능. Phase 8.1 진입 권장 (Phase 9 와 평행 가능 — tilt + stability + contact 가 Phase 9 입력으로 즉시 사용 가능, axis distance 는 Phase 8.1 후 정상화).

---

*Verified: 2026-06-09T16:00:00Z*
*Verifier: Claude (gsd-verifier, opus-4-7)*
*Evidence sources: 4 SUMMARY.md (08-00/01/02/03) + 5 source files (force_signals.py / pipeline/app.py / firestore_admin.py / analysis.ts / userAnalyses.ts) + PHASE8-INHERITED-ISSUES.md + ROADMAP.md + 9 commit hashes (2261dc5 / 928c6d4 / 80c353e / 69cdf69 / a31f893 / 3f4baea / 6b4dd16 / 8ee5376 / fb659e6 / fc3b6b7 / ced1d87 / c71c75b / f627905)*
