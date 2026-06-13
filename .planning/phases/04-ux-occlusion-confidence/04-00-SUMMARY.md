---
phase: 04-ux-occlusion-confidence
plan: "00"
subsystem: testing
tags: [pytest, tdd, synthesis, occlusion, phase04, wave0]

# Dependency graph
requires:
  - phase: 04-ux-occlusion-confidence
    provides: "Wave 0 — TDD 게이트 (Wave 1 합성 어댑터/confidence gate 구현 전 회귀 게이트)"
provides:
  - "backend/tests/phase04/ pytest 디렉토리 + __init__.py + conftest.py"
  - "POSE-03-a~f 6 단위 테스트 파일 (17 test items)"
  - "synthetic numpy fixture 7개 — joint_seq_30f, joint_seq_60f, conf_seq_30f, conf_seq_60f, low_conf_seq, scene_findings_occlusion, scene_findings_clean"
  - "Wave 1 게이트 — test_warning_lockstep (SYNTHESIS_WARNING_CODES frozenset 3-way lockstep 검증)"
affects: [04-01, 04-02, 04-03, 04-04, 04-05, POSE-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pytest fixture factory 박제 — Spike 002d 패턴 재사용 (Phase 8.1 conftest 와 형상 정합)"
    - "ImportError → pytest.skip (collect 가능, RED 회피) — Wave 미박제 어댑터 흡수"
    - "Wave 1 게이트 = 일반 assert 로 RED (skip/xfail 금지) — 구현 완료 증명"

key-files:
  created:
    - backend/tests/phase04/__init__.py
    - backend/tests/phase04/conftest.py
    - backend/tests/phase04/test_confidence_gate.py
    - backend/tests/phase04/test_synthesis_adapter.py
    - backend/tests/phase04/test_synthesis_merge.py
    - backend/tests/phase04/test_warning_lockstep.py
    - backend/tests/phase04/test_synthesis_firestore_flat.py
    - backend/tests/phase04/test_synthesis_g4_guard.py
  modified: []

key-decisions:
  - "Wave 0 = RED-first TDD 게이트 (Wave 1 04-01 박제 전까지 anchor 테스트 1개 RED 유지)"
  - "Wave 1 미박제 어댑터 import 는 try/except ImportError → pytest.skip — collect 0 errors 보장"
  - "test_warning_lockstep 만 예외적으로 skip/xfail 금지 — Wave 1 SYNTHESIS_WARNING_CODES frozenset 3-way lockstep 박제 완료를 증명하는 정상 assert RED"
  - "T=60 fixture (joint_seq_60f / conf_seq_60f) 사전 박제 — 04-03 evaluate_4way / 04-05 cylindrical mesh 가 T=60 기대"

patterns-established:
  - "Phase 4 단위 테스트 baseline — RTMW COCO17 (T, 17, 3) joint + (T, 17) confidence 형상"
  - "scene_findings dict — occlusion_severe / camera_angle_problematic 2 boolean 필드 박제"
  - "low_conf_seq factory — base conf_seq + [frame slice, joint slice] = 0.1 occlusion 시뮬"

requirements-completed: [POSE-03]

# Metrics
duration: 1 min
completed: 2026-06-13
---

# Phase 4 Plan 00: ux-occlusion-confidence Wave 0 Summary

**POSE-03-a~f 6 단위 테스트 파일 + 7 numpy fixture conftest — Wave 1 합성 어댑터/confidence gate TDD 게이트 박제 (test_warning_lockstep 이 SYNTHESIS_WARNING_CODES frozenset 박제 완료 시점의 RED→GREEN 전환 증명).**

## Performance

- **Duration:** 1 min
- **Started:** 2026-06-13
- **Completed:** 2026-06-13
- **Tasks:** 1
- **Files modified:** 8 (전부 신규)

## Accomplishments

- backend/tests/phase04/ 디렉토리 + __init__.py 신설 (pytest discovery)
- conftest.py — 7 fixture (joint_seq_30f / joint_seq_60f / conf_seq_30f / conf_seq_60f / low_conf_seq / scene_findings_occlusion / scene_findings_clean), Spike 002d 박제 패턴 재사용
- POSE-03-a~f 커버하는 6 test 파일, 총 17 test items collect 가능
- Wave 1 anchor 게이트 박제 — test_warning_lockstep::test_ai_synthesis_failed_in_frozenset 이 SYNTHESIS_WARNING_CODES frozenset 미박제 상태에서 정상 RED
- firestore flat 검증 GREEN — _validate_flat_dict_no_nested_array (W5 기존) 가 synthesizedJoints nested array reject

## Task Commits

1. **Task 1: phase04 test 인프라 신설 (conftest + 6 test 파일)** — `b6b7f78` (test)

## Files Created/Modified

- `backend/tests/phase04/__init__.py` — 빈 파일, pytest discovery 진입점 (phase08_1/__init__.py 패턴 정합)
- `backend/tests/phase04/conftest.py` — 7 synthetic numpy fixture (deterministic seed RNG, COCO17 17-joint 형상)
- `backend/tests/phase04/test_confidence_gate.py` — POSE-03-a (D-04 a/b/c/d 트리거 결합 검증), 3 test
- `backend/tests/phase04/test_synthesis_adapter.py` — POSE-03-b (Gemini/Cylindrical adapter Exception → SynthesisResult(status=failed) degrade 박제), 2 test
- `backend/tests/phase04/test_synthesis_merge.py` — POSE-03-c (merge_with_temporal 4-status 분기 검증 + temporal 모듈 import 확인), 5 test
- `backend/tests/phase04/test_warning_lockstep.py` — POSE-03-d (SYNTHESIS_WARNING_CODES frozenset 3-way lockstep), 3 test (RED gate)
- `backend/tests/phase04/test_synthesis_firestore_flat.py` — POSE-03-e (synthesizedJoints flat / nested-array reject), 2 test (GREEN)
- `backend/tests/phase04/test_synthesis_g4_guard.py` — POSE-03-f (is_reference=True 시 status=skipped + g4_reference_guard warning), 2 test

## Decisions Made

- **Wave 1 게이트 = 일반 assert RED (skip/xfail 금지)** — test_warning_lockstep 은 SYNTHESIS_WARNING_CODES frozenset 의 박제 완료를 증명하는 회귀 게이트라서 pytest.skip / xfail 처리 시 게이트가 사라진다. Wave 1 04-01 Task 1 박제 후 자동으로 GREEN 전환.
- **나머지 Wave 1 어댑터 import 는 try/except ImportError → pytest.skip** — SynthesisResult / SynthesisAdapter / merge_with_temporal / _call_synthesis_adapter 가 Wave 0 시점에서 미박제이므로 collect error 가 발생하면 회귀 게이트 자체가 멈춤. skip 으로 흡수해 collect 0 errors 유지.
- **T=60 fixture 사전 박제** — 04-03 evaluate_4way Task 2 / 04-05 cylindrical mesh Task 2 가 T=60 기대. Wave 0 에서 미리 박제해 Wave 3 단위 테스트가 fixture override 없이 재사용 가능하게 함.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **test_pole_detector.py 사전 존재 collection error** — Wave 0 시작 전부터 기존에 있던 1714-test baseline 의 1 error. phase04 와 무관 (out of scope, Rule 1-3 적용 대상 아님). 회귀 검증은 1714 → 1731 test 로 정확히 +17 추가됨을 확인.

## User Setup Required

None - no external service configuration required.

## Acceptance Criteria Verification

| Criterion | Command / Check | Result |
|---|---|---|
| pytest --collect-only 8 파일 0 errors | `pytest backend/tests/phase04/ --collect-only -q` | PASS — 17 tests collected, 0 errors |
| test_ai_synthesis_failed_in_frozenset RED (Wave 1 gate) | `pytest .../test_warning_lockstep.py::test_ai_synthesis_failed_in_frozenset` | PASS — FAILED (정상 RED, AssertionError: SYNTHESIS_WARNING_CODES None) |
| test_ai_synthesis_meta_nested_array_rejected GREEN | `pytest .../test_synthesis_firestore_flat.py::test_ai_synthesis_meta_nested_array_rejected` | PASS — PASSED (GREEN) |
| 모든 파일 import error 0 | `pytest --collect-only` | PASS — collect 단계 import error 0 (Wave 1 어댑터 fixture lazy import 가 skip 흡수) |
| 전체 backend suite 회귀 0 | `pytest backend/tests/ --collect-only` | PASS — 1714 → 1731 (+17 신규), 기존 collection error 1건 (test_pole_detector.py, 사전 존재) 불변 |
| joint_seq_60f fixture 존재 | `grep -c "joint_seq_60f" backend/tests/phase04/conftest.py` | PASS — 3건 (정의 + 2 assertion) |

전체 phase04 suite 실행 결과: **3 failed (Wave 1 gate, expected RED) / 3 passed (temporal import + 2 firestore flat GREEN) / 11 skipped (Wave 1 미박제 어댑터)**.

## Next Phase Readiness

- Wave 1 (04-01) 진입 준비 완료 — SynthesisResult dataclass + SynthesisAdapter Protocol + GeminiViewReasoner + SYNTHESIS_WARNING_CODES frozenset 박제 시 자동으로:
  - test_warning_lockstep 3건 RED → GREEN 전환 (Wave 1 완료 증명)
  - test_synthesis_adapter / test_synthesis_merge / test_confidence_gate / test_synthesis_g4_guard 11건 skipped → 실행 (RED/GREEN 분기)
- Wave 3 (04-03 / 04-05) T=60 fixture (joint_seq_60f / conf_seq_60f) 사전 박제 완료 — evaluate_4way / cylindrical mesh 단위 테스트 fixture override 불필요

## Self-Check: PASSED

- 8 신규 파일 모두 디스크 존재 확인 (git commit b6b7f78 = "8 files changed, 696 insertions(+)")
- commit hash b6b7f78 git log 확인 가능
- acceptance_criteria 6 항목 전부 PASS (위 표)
- 한국어 문구 + 영어 식별자 / 이모지 0 (CLAUDE.md §7 정합)

---
*Phase: 04-ux-occlusion-confidence*
*Completed: 2026-06-13*
