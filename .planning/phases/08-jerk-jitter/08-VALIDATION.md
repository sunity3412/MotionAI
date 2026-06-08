---
phase: 8
slug: jerk-jitter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-08
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + numpy (Python stdlib) |
| **Config file** | none — Wave 0 installs `backend/tests/phase08/__init__.py` + `conftest.py` (Phase 6/7 패턴 정합) |
| **Quick run command** | `PYTHONPATH=backend/shared/python:. backend/.venv/bin/python3 -m pytest backend/tests/phase08/ -x` |
| **Full suite command** | `PYTHONPATH=backend/shared/python:. backend/.venv/bin/python3 -m pytest backend/tests/ -x` |
| **Estimated runtime** | ~10 seconds (phase08/) / ~60 seconds (full suite, regression) |

---

## Sampling Rate

- **After every task commit:** Run `PYTHONPATH=backend/shared/python:. backend/.venv/bin/python3 -m pytest backend/tests/phase08/ -x`
- **After every plan wave:** Run `PYTHONPATH=backend/shared/python:. backend/.venv/bin/python3 -m pytest backend/tests/ -x` (regression: phase06 / phase07 / pipeline 0 회귀)
- **Before `/gsd-verify-work`:** Full suite green + `tsc --noEmit clean` + `sam validate exit 0` + 5영상 sweep sanity check pass
- **Max feedback latency:** ~10s (phase08/) / ~60s (full suite)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-W0 | 01 | 0 | FORCE-01 | — | Wave 0 test infra + 6 fixture JSON | infra | `pytest backend/tests/phase08/ --collect-only` | ❌ W0 | ⬜ pending |
| 08-01-01 | 01 | 1 | FORCE-01 (success #1~4) | — | 7 TS type + Python mirror + docs/contract.md §9 3-way lockstep | unit | `pytest backend/tests/phase08/test_firestore_lockstep.py -x` + `cd app && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | FORCE-01 (drift defense) | — | `dimensions.stability_wobble` raw helper 추출 + `force_signals.jitter_score` 가 동일 input → 동일 output | unit | `pytest backend/tests/phase08/test_compute_stability_metrics.py::test_drift_defense -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | FORCE-01 (motion_id 매핑) | — | `backend/judging_data/contact_points.yaml` 박제 (researcher 초안, 인버트/후굴/숄더마운트/기본 포징) + loader 함수 | unit | `pytest backend/tests/phase08/test_compute_contact_stability.py::test_yaml_load -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | FORCE-01 (success #1) | — | `compute_axis_deviation` 본체 (pelvis/chest 폴축 거리 + tilt + deviationDirection + severity) | unit | `pytest backend/tests/phase08/test_compute_axis_deviation.py -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | FORCE-01 (success #2) | — | `compute_stability_metrics` 본체 (jitter/jerk/holdStability/unstableBodyParts) + jerk MAD outlier rejection | unit | `pytest backend/tests/phase08/test_compute_stability_metrics.py -x` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 2 | FORCE-01 (success #3) | — | `compute_contact_stability` 본체 (proximity + debounce + lostContactAtMs + 시간 패턴 검증) | unit | `pytest backend/tests/phase08/test_compute_contact_stability.py -x` | ❌ W0 | ⬜ pending |
| 08-02-04 | 02 | 2 | FORCE-01 (5-phase split) | — | `compute_phase_boundaries` Layer 1 (motion-agnostic 휴리스틱) — foot_y / hand_pole_dist / keypoint_velocity 3 신호 cutoff | unit | `pytest backend/tests/phase08/test_compute_phase_boundaries.py::test_layer1_only -x` | ❌ W0 | ⬜ pending |
| 08-02-05 | 02 | 2 | FORCE-01 (success #4) | — | `compute_force_signals` umbrella — `temporal_fill` → metric calc → confidence 가중 + warning | integration | `pytest backend/tests/phase08/test_compute_force_signals.py::test_temporal_fill_and_confidence_weighting -x` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 3 | FORCE-01 (Layer 2) | — | Layer 2 Gemini key_moments 통합 — Plan 01-13 `gemini_moment_extractor` import + 5-phase mapping + agreement 룰 | unit (mock) | `pytest backend/tests/phase08/test_compute_phase_boundaries.py::test_layer1_layer2_agreement -x` | ❌ W0 | ⬜ pending |
| 08-03-02 | 03 | 3 | FORCE-01 (pipeline wiring) | — | `_process` Phase 8 호출 site + 입력 fan-in (frames, body_profile, pole_axis, motion_id) | integration | `pytest backend/tests/pipeline/test_pipeline_phase8.py -x` | ❌ W0 | ⬜ pending |
| 08-03-03 | 03 | 3 | FORCE-01 (Firestore) | — | `firestore_admin.complete_analysis(force_signals_report=...)` + `_validate_dict_only_scalars` 명세 확장 (list[str] 허용) | unit | `pytest backend/tests/phase08/test_firestore_lockstep.py::test_validator_passes -x` | ❌ W0 | ⬜ pending |
| 08-03-04 | 03 | 3 | FORCE-01 (frontend normalize) | — | `userAnalyses.normalize()` forceSignals 7 신설 필드 null-guard (Phase 7 WR-02 B1 패턴) | unit | `cd app && npx tsc --noEmit` + `cd app && npx jest src/lib/__tests__/userAnalyses.test.ts -x` (만약 신설) | ❌ W0 | ⬜ pending |
| 08-03-05 | 03 | 3 | FORCE-01 (deploy smoke) | — | SAM build clean + Lambda import smoke + RunPod requirements update | smoke | `cd backend && sam validate` + `cd backend && sam build --use-container` | manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase08/__init__.py` — package marker (Phase 7 환경 패턴 정합 — `backend/tests/__init__.py` 도 Phase 7 Plan 02 Task 1 에서 신설됨)
- [ ] `backend/tests/phase08/conftest.py` — 합성 `PoseFrame` factory + `GeminiMomentExtractor` mock fixture + `BodyNormalizationProfile` synthetic factory
- [ ] `backend/tests/phase08/fixtures/_factory.py` — synthetic motion 영상 생성 (T=60, J=17 COCO-17 + RTMW 133 wholebody indices)
- [ ] `backend/tests/phase08/fixtures/fixture_clean_invert.json` — 정은지급 깔끔한 invert (severity 모두 low 예상)
- [ ] `backend/tests/phase08/fixtures/fixture_pelvis_drop.json` — pelvis 가 hold 중 outward 이동 (severity=high deviationDirection='outward')
- [ ] `backend/tests/phase08/fixtures/fixture_occluded_lock.json` — lock phase frame 의 reliability='low' 60% (occlusion warning emission)
- [ ] `backend/tests/phase08/fixtures/fixture_motion_id_unrecognized.json` — motion_id=None fallback (expected_contact_points=[] + estimatedStable=null)
- [ ] `backend/tests/phase08/fixtures/fixture_jerk_high.json` — transition phase jerk > 임계 (high severity)
- [ ] `backend/tests/phase08/fixtures/fixture_layback_release.json` — hold 안 lostContactAtMs (시간 패턴 검증 abnormal release)
- [ ] `backend/tests/phase08/test_compute_phase_boundaries.py` — Layer 1 단독 + Layer 2 mock + agreement 룰
- [ ] `backend/tests/phase08/test_compute_axis_deviation.py` — pelvis/chest 거리 + tilt + direction + severity
- [ ] `backend/tests/phase08/test_compute_stability_metrics.py` — jitter/jerk/holdStability/unstableBodyParts + **drift defense test** (force_signals.jitter == dimensions.stability_wobble)
- [ ] `backend/tests/phase08/test_compute_contact_stability.py` — yaml load + proximity + debounce + abnormal release + motion_id 미인식 fallback
- [ ] `backend/tests/phase08/test_compute_force_signals.py` — umbrella E2E + temporal_fill + confidence 가중 + warning
- [ ] `backend/tests/phase08/test_firestore_lockstep.py` — schema 3-way drift defense + camelCase + `_validate_flat_dict_no_nested_array` + tsc smoke
- [ ] `backend/judging_data/__init__.py` (만약 신설 필요) + `backend/judging_data/contact_points.yaml` — motion_id × 12 ContactPoint enum 매핑 (researcher 초안, belle 검수)

*Wave 0 신설 14개 (test 파일 6 + fixture 6 + infra 2). Phase 6/7 패턴 정합.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 5영상 sweep sanity check (severity 분포) | FORCE-01 (D-08-D3) | 정은지 영상 = 90%+ low severity 박제 / 학생 영상 = medium/high 위주 — fixed 임계의 sanity check, threshold derivation 아님 | belle Pod 에서 `sweep_rtmw_20260603_1409` + 정은지 mode1 5영상 재실행 + force_signals 출력 hist 박제. severity 분포가 합리적인지 belle 검수. |
| Layer 2 Gemini key_moments timestamp sensible check | FORCE-01 (D-08-A2 Layer 2) | Plan 01-13 measurement_unreliable_blocked verdict 의 timestamp 자체 의심 여부 직접 검증 — A11 [ASSUMED] | belle Pod 에서 ref-invert 1영상 + GeminiMomentExtractor.extract_key_moments() 호출 + 5 timestamp (entry/lock/transition/final_shape/hold) 가 영상의 실제 동작 경계와 ±300ms 안에 있는지 belle 육안 검수 |
| contact_points.yaml 도메인 검수 | FORCE-01 (D-08-B1) | researcher 초안 — 인버트/후굴/숄더마운트/기본 포징 motion_id 별 expected_contact_points (12 enum 중) 가 폴스포츠 도메인 정합한지 belle/강사 검수 필요 | belle 가 yaml 직접 검토 + 인버트 = (left_hand, right_hand, left_inner_thigh, right_inner_thigh) / 후굴 = (left_hand, right_hand, left_ankle, right_ankle, hip) / 숄더마운트 = (left_hand, right_hand, hip) 등 belle 박제 후 lock |
| TS tsc + Firestore output 양립 검증 (drift defense) | FORCE-01 (D-08-U3) | TS strict mode + Firestore raw dict 양쪽 호환성 — `tsc --noEmit` 가 자동 검증하지만 실 Firestore output (e.g., development 환경 1회) 도 belle 검수 권장 | development build 1회 + 분석 1회 실행 + Firestore console 에서 `forceSignals` 필드 7 필드 + 모든 type 일치 확인 |
| Layer 1 휴리스틱 25-timestamp belle labeling sanity (A10 [ASSUMED] 검증) | FORCE-01 (D-08-A1) | Layer 1 motion-agnostic 휴리스틱의 5영상 × 5 phase = 25 timestamp 가 belle 라벨링과 ±200ms 안인지 검증 — A10 가설 직접 검증 | belle 5영상 × 5 phase boundary 수동 라벨링 후 Layer 1 산출과 비교. 일치율 ≥ 80% = pass, < 80% = Layer 1 룰 cutoff 박제 재조정 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (14 신설 ❌ W0)
- [ ] No watch-mode flags
- [ ] Feedback latency < ~10s (phase08/) / ~60s (full suite)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
