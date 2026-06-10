# Phase 9 — Deferred Items

Discovered during Wave 1 execution but out of scope (not introduced by this plan).

## Pre-existing test collection errors — `from backend.research.*` import path

`pytest tests/ -q` from inside `backend/` fails to collect 11 smoke/spike test
files because they import via the absolute `from backend.research.*` path,
which doesn't resolve when pytest is launched from inside the `backend/`
directory (the parent — `backend/` itself — is the package, so `backend.*` is
not on `sys.path`). The same import also fails from the repo root because
there's no top-level `backend/__init__.py`.

Affected files (all added in Phase 1, commits 6255380 / 84c249a / b87fe7c / 6e1d328):

- `tests/test_compare_engines_smoke.py`
- `tests/test_debug_gap_root_cause_smoke.py`
- `tests/test_gemini_motion_classify_spike.py`
- `tests/test_mapping_audit.py`
- `tests/test_pole_detector.py`
- `tests/test_spike_gemini_moment_smoke.py`
- `tests/test_spike_measurement_trace.py`
- `tests/test_spike_measurement_trace_smoke.py`
- `tests/test_spike_mediapipe_to_h36m17.py`
- `tests/test_spike_rtmpose_to_h36m17.py`
- `tests/test_sweep_rtmpose_smoke.py`

Why deferred: pre-existing (Phase 1) — not introduced by Phase 9. Fix requires
either (a) adding `backend/__init__.py` and running pytest from repo root, or
(b) rewriting the imports to use the installed-package path
(`sunity_shared.research.*`). Both are scope-out from a Phase 9 Wave 1 fix.

T5 full-regression gate verified via subset path:

```
cd backend && pytest tests/phase06/ tests/phase07/ tests/phase08/ tests/phase08_1/ tests/phase09/ tests/pipeline/ -q
# → 550 passed, 1 skipped
```

This subset covers all production-pertinent test suites. The deferred smoke/spike
suites are research-only and do not gate production behavior.

---

## 실증 테스트 시점 점검 리스트 (2026-06-10 belle 결정)

Phase 9 코드 자체는 verified PASS (4/4 SC + 13/13 D-09-*). 아래 3 항목은
"자동화로 못 잡는 도메인 적절성 판단" — 학원 파일럿 실증 시점 (belle + 강사 +
수강생 함께) 톤/어휘/임계값을 점검한다.

| # | 항목 | 위치 | 점검 방법 | 변경 시 작업 |
|---|---|---|---|---|
| 1 | 18 canned 본문 톤 | `backend/shared/python/sunity_shared/analysis/force_pattern_copy.py::_FORCE_PATTERN_COPY_DATA` | 수강생 3-5명에게 카드 표시 → "무슨 뜻인지 바로 이해돼?" 인터뷰. 강사 시점에서 "도메인 적절성" 점검. | dict literal 18개 본문 직접 수정 → `pytest tests/phase09/test_force_pattern_copy_render.py tests/phase09/test_force_pattern_copy_no_forbidden.py -x -q` 재실행. 단, 각 본문이 `_MODE_PREFIX[mc]` 로 시작 + 길이 ≥ 25 + 금지 표현 0 invariant 보존. |
| 2 | jointHint 부위 어휘 | 같은 파일 `_JOINT_HINT_BY_SIGNAL` (4 매핑 + 2 None) | 강사한테 "이 동작 실패 원인을 학생에게 알릴 때 어떤 부위 단어 쓰는지?" 인터뷰 + 카드 안 어휘가 본문과 자연스럽게 어울리는지. | `_JOINT_HINT_BY_SIGNAL` dict + `test_force_pattern_copy_render.py::test_joint_hint_mapping` + `test_infer_force_direction_pattern.py` 안 4 assertion + `test_force_pattern_dataclass.py` / `test_force_pattern_ranking.py` 안 fixture 동시 갱신. 재실행 = `pytest tests/phase09/ -x -q`. |
| 3 | pelvis_drop 임계값 (Assumption A1) | `backend/shared/python/sunity_shared/analysis/force_pattern.py::_detect_pelvis_drop` — `hip_tilt > 20.0 AND (hip_tilt - shoulder_tilt) > 10.0` | 정은지 25 sample 분포 통계 — `(hip_tilt > 20°) AND ((hip_tilt - shoulder_tilt) > 10°)` 만족하는 정은지 frame 0개 확인 (현 분포는 hip < 50°). 학생 영상에서 실제 finding emit 분포 추세 검토. | 임계값 상수 수정 → `pytest tests/phase09/test_infer_force_direction_pattern.py -x -q` 재실행. boundary case test (hip=21/shoulder=10 emit / hip=18/shoulder=5 no-emit) 도 동시 갱신. |

**Trigger**: 학원 파일럿 1차 (정은지 시연 직후) — 첫 5-10 수강생 영상 분석 결과를 belle + 강사가 직접 확인하는 시점. 또는 Phase 11 (Gemini 자연어 풍부화) 통합 자연 검증 시 톤이 LLM 출력과 일관성 깨질 때.

**Skip-OK 조건**: Phase 11 LLM 자연어 풍부화가 본문 톤을 자연스럽게 다시 쓰므로 (Phase 9 canned 는 LLM input 으로 들어감), Phase 11 시점에 톤 불일치가 발견되지 않으면 본 리스트는 invariant 박제 그대로 두어도 무방.
