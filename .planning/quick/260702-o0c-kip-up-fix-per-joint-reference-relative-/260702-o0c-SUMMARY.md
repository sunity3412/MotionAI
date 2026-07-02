---
phase: quick-260702-o0c
plan: 01
subsystem: backend/scoring (deduction measured-deviation seed)
tags: [phase24, transparent-tally, reference-relative, kip-up, window-median, scoring-accuracy]
requires:
  - "quantification.windowMedianAngleDeltas (features.window_median_angle_deltas — 표시 레이어 source)"
  - "motiondtw.per_joint_deviation (DTW full-path median — fallback seed, 함수 불변)"
provides:
  - "angle_vs_reference__{jk} seed 2단 — (1순위) worst-window median (표시=감점 동일 source) + (fallback) DTW-median"
  - "seed source 관찰 로그 (window_median vs dtw_median_fallback)"
affects:
  - "kip-up fault 상체(어깨/고관절) 감점 — 표시 40° 편차가 이제 감점에 반영 (pod sweep PENDING)"
  - "mode1 전 동작 공통 — quant available 시 window median 이 감점의 authoritative source"
tech-stack:
  added: []
  patterns:
    - "표시되는 편차 = 감점되는 편차 (single source: features.window_median_angle_deltas)"
    - "양 경로 공통 방출 규칙 helper (_emit_reference_relative — JOINT_KEYS/NaN·0/cross-exclusion)"
key-files:
  created: []
  modified:
    - backend/functions/pipeline/app.py
    - backend/tests/test_pipeline_deduction_seam.py
decisions:
  - "window 경로를 탔으면(deltas 존재) fallback 미실행 — 전부 0 편차여도 DTW 재시도 없음 (honest 0, 표시=감점 일관성)"
  - "delta_deg 는 SIGNED(student−reference) → seed 는 abs() magnitude (criterion 은 비음수 deviation 기대)"
  - "seed source 는 log.info 만 — md 마커 키/contract/Firestore 스키마 변경 0 (엔진 md 계약은 criterion id 키만)"
metrics:
  duration: ~10m
  completed: 2026-07-02
---

# Quick Task 260702-o0c: kip-up fix — per-joint reference-relative seed 를 표시용 window median 과 정렬 Summary

kip-up fault 영상의 상체 결함(어깨 Δ40.4°/31.0°, 고관절 Δ22.7° — 전부 tol 20° 초과)이 감점 0 으로 새던 표시/감점 집계 불일치를 해소: `angle_vs_reference__{jk}` seed 가 (1순위) 표시용 `windowMedianAngleDeltas`(worst_pose_center ±2 median, single source = `features.window_median_angle_deltas`)를 소비하고, quant unavailable 시에만 기존 `per_joint_deviation` DTW-median fallback 을 유지하는 2단 구조.

## What Was Built

### Task 1 — RED: window-median seed 실패 테스트 (commit `b26d944`)

`backend/tests/test_pipeline_deduction_seam.py`:
- `_quant()` 헬퍼에 `window_median=None` 인자 추가 + `_window_median()` fixture 헬퍼 신설 (`features._delta_entry` 로 실제 산출과 동일 형상의 deltas dict 구성).
- 신규 6 테스트:
  1. `test_reference_relative_local_fault_from_window_median` — 어깨 delta_deg=-40 → md == 40.0 (abs, 국소-희석 회귀 문서화) + spurious joint(`not_a_joint`) skip.
  2. `test_reference_relative_window_median_takes_precedence_over_dtw` — window 40° vs DTW 희석값 10° 동시 제공 → 40.0 채택 (우선순위 증명).
  3. `test_reference_relative_fallback_when_quant_unavailable` — window=None + match/ref 보유 → DTW-median fallback 발동 (24-05/e5k 회귀 가드).
  4. `test_reference_relative_window_median_exclusion_registered_knee` — 등록 profile 무릎(EXTEND) 제외 / 어깨(BENT_OK) 유지 — window 경로에도 cross-exclusion.
  5. `test_reference_relative_window_median_self_compare_no_keys` — delta 전부 0 → 키 0개 (success/clean 감점 0 보장).
  6. `test_reference_relative_window_median_deterministic` — 동일 입력 2회 == .
- 기존 fallback 계열 테스트 5건은 삭제하지 않고 docstring 만 "quant unavailable → DTW-median fallback (24-05/e5k 회귀 가드, 260702-o0c 2단 구조)" 로 전환·보존.
- RED 확인: 4 failed (window 경로 미구현), 27 passed.

### Task 2 — GREEN: 2단 seed 구현 (commit `f513587`)

`backend/functions/pipeline/app.py::_build_deduction_measured_deviations` (24-07 ① 블록 재구성):
- `_emit_reference_relative(jk, v)` helper — 양 경로 공통 방출 규칙 1곳: `jk not in JOINT_KEYS` skip / NaN·0·음수 skip / `profile.expects_extension(jk)` skip (seed-stage cross-exclusion, double-count 0).
- **1순위 (window_median):** `quantification.windowMedianAngleDeltas` 가 dict 이고 `deltas` truthy → 각 entry 의 `abs(float(delta_deg))` 로 방출. 이 경로를 탔으면 fallback 미실행 (전부 0 편차여도 honest 0).
- **fallback (dtw_median_fallback):** window 부재/형상불량/빈 deltas 시에만 기존 `per_joint_deviation(path, angles[start:end], reference_angles)` 블록 그대로 (예외 = honest skip).
- 관찰 가능성: `log.info("angle_vs_reference seed source=%s joints=%d", ...)` — 1개 이상 방출 시 1줄, 스키마 변경 0.
- docstring 갱신 (angle_vs_reference 항목 — 표시=감점 정렬 + fallback 보존 사유).
- 시그니처(`reference_dtw_match`/`reference_angles`)·호출부(app.py ~3420) 불변, `motiondtw.per_joint_deviation` 함수 무변경, 신규 튜닝 상수 0, kip-up 특정 분기 0.

### Task 3 — Pod sweep: PENDING (checkpoint marker, executor 미실행)

Orchestrator 가 커밋 후 별도 실행. Gate 기대치 (플랜 박제):
1. kip-up fault (analysis af8fb8c8 류, mode1) → 88 에서 **추가 하락** (상체 어깨/고관절 감점 반영), belle 육안 정합.
2. 정은지 success 6영상 → 전부 **100 유지** (window median < tol 20°).
3. self-compare 0 재확인.
4. 로그에서 `seed source=window_median` 발동 확인 (low_alignment 케이스면 `dtw_median_fallback`).

## Verification

### 단위 테스트 GREEN
```
$ PYTHONPATH="shared/python:functions/pipeline" .venv/bin/python -m pytest tests/test_pipeline_deduction_seam.py -q
31 passed in 0.30s
```

### 전체 회귀 0 (baseline diff IDENTICAL)
Full backend suite (`--continue-on-collection-errors`, 11 collection error 는 pre-existing spike/smoke env 의존):
- Baseline (pre-change HEAD `18f72d2`): 101 failed, 1824 passed, 19 skipped, 29 errors.
- After (`f513587`): 101 failed, **1830 passed** (+6 = 신규 테스트), 19 skipped, 29 errors.
- FAILED/ERROR 목록 sort-diff → **IDENTICAL** (신규 실패 0).

### Task 1 verify gates
- `git diff --stat motiondtw.py` = 0줄 (무변경).
- `grep -c windowMedianAngleDeltas app.py` = 4, `grep -c per_joint_deviation app.py` = 11 (양 경로 존재).
- `import app` 무오류.

### 밴드 grep
플랜 grep 패턴 hit 2건은 모두 pre-existing "band-free" **anti-band** 주석(app.py:1813, 1933 — HEAD 이전부터 존재). 이번 diff 에 band/밴드/fixed_ceiling 용어 0건 — 밴드 재도입 없음.

## Deviations from Plan

None - plan executed exactly as written. (플랜의 Task 1=구현/Task 2=테스트 순서를 TDD RED→GREEN 커밋 순서로 실행 — 테스트 먼저 커밋 후 구현 커밋. 파일/내용은 플랜 그대로.)

## Orchestrator-Owned (NOT executed here)
- 새 pod bootstrap → Lambda `RUNPOD_ANALYZE_URL` 동기화 → 6 페어 SERIAL sweep ([[pipeline-not-concurrency-safe-eval-serial]]).
- PASS 기준: kip-up fault < 88 AND success 6/6 == 100. 실패 시 belle 에스컬레이션.

## Commits
- `b26d944` test(quick-260702-o0c): add failing tests for window-median angle_vs_reference seed
- `f513587` feat(quick-260702-o0c): angle_vs_reference seed 2단 — worst-window median 우선 + DTW-median fallback

## Self-Check: PASSED
- backend/functions/pipeline/app.py — FOUND (2단 seed + `_emit_reference_relative` + source log)
- backend/tests/test_pipeline_deduction_seam.py — FOUND (31 passed, 신규 6 테스트 포함)
- commit b26d944 — FOUND in git log
- commit f513587 — FOUND in git log (HEAD)
