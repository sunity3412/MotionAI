---
phase: 33-result-trust-recovery
plan: 05
subsystem: ml
tags: [motiondtw, alignment, dtw, coverage-floor, fail-closed, safety-flags, data-gate, ipsf]

requires:
  - phase: 33-04
    provides: downstream backfill (밀도 정합된 reference — nu≈nr 지배 케이스 성립)
  - phase: 33-19
    provides: 33-M3-SPEC.md (LOCKED paired-range + coverage-floor + fail-closed 계약)
provides:
  - "find_action_segment/MotionMatch paired user+reference range (ref_start/ref_end)"
  - "nu<nr 기준 window 트리밍 — COVERAGE_FLOOR 0.80 + ambiguity + 구조 바닥 fail-closed"
  - "3 ripple 사이트(pipeline S1/S2, safety_flags S3) windowed-reference 소비"
  - "scoring-untouched JSON/exit-code DATA-GATE (|| echo 흡수 버그 제거)"
affects: [33-06, 33-07, mode1-scoring, safety-flags, segment-scores]

tech-stack:
  added: [scripts/dump_scoring_constants.py, tests/phase33/scoring_constants_pinned.json]
  patterns:
    - "paired-range DTW: 긴 쪽을 짧은 쪽 길이로 min-DTW 슬라이딩, 짧은 쪽 통째(양방향 대칭)"
    - "fail-closed = 항상 전체 기준(더 많은 편차 노출) 폴백 — 절대 잘린 window 로 폴백 금지"
    - "정렬 substrate 변경을 byte-identical-deviation + constants-hash + JSON data-gate 로 봉인"

key-files:
  created:
    - backend/tests/phase33/test_m3_alignment_only.py
    - backend/tests/phase33/test_safety_flags_m3_regression.py
    - backend/tests/phase33/scoring_constants_pinned.json
    - backend/scripts/dump_scoring_constants.py
  modified:
    - backend/shared/python/sunity_shared/analysis/motiondtw.py
    - backend/shared/python/sunity_shared/analysis/segments.py
    - backend/shared/python/sunity_shared/analysis/safety_flags.py
    - backend/functions/pipeline/app.py

key-decisions:
  - "find_action_segment 에 optional ref_boundary kwarg 추가 — §2.2 구조 바닥을 window 선정에 반영하는 유일한 방법(하위호환, 기본 None)"
  - "segment_scores 에 backward-compatible ref_start/nr_full kwarg — 기존 5-arg 호출 무변경, window-local 경계 시프트"
  - "scoring 상수는 kismam 코드에서 live 덤프 → pinned 매니페스트와 JSON 비교(tol/slope drift 를 데이터로 포착)"

patterns-established:
  - "MotionMatch.path 의 ref 인덱스는 window-local — 모든 소비자는 a_ref[ref_start:ref_end] 를 넘겨야 함"
  - "정렬 게이트 상수(COVERAGE_FLOOR/AMBIGUITY_*)와 채점 상수(tol/slope/cap/epsilon) 분리 — 전자만 이 플랜이 도입, 후자는 불변"

requirements-completed: [D-02, D-18, D-19, D-20, D-27, D-29]

duration: ~55min
completed: 2026-07-23
---

# Phase 33 Plan 05: M3 Alignment (paired-range find_action_segment) Summary

**`find_action_segment`/`MotionMatch` 가 paired user+reference range 를 운반하고, `nu<nr` 일 때 기준 준비/대기 구간을 COVERAGE_FLOOR 0.80·ambiguity·구조 바닥 게이트로 트리밍하되 모호하면 전체 기준으로 fail-closed — 채점 산식은 byte-identical 로 봉인하고 3 ripple 사이트를 windowed reference 로 통일.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-07-23
- **Tasks:** 2 (TDD RED → GREEN)
- **Files modified:** 8 (4 prod + 4 test/script) + pinned manifest

## Accomplishments

- **M3 를 33-M3-SPEC.md 그대로 구현** — `MotionMatch` 에 `ref_start/ref_end` 추가, `find_action_segment` 가 `((u_s,u_e),(r_s,r_e))` paired range 반환. `nu<nr` 신규 경로가 기준을 `nu` 길이로 min-DTW 슬라이딩(12/12 무력화 원인이던 `if nu<=nr: return 0,nu` 대체).
- **coverage floor + fail-closed** — `nu/nr < 0.80` 또는 근-동률 모호(eps 0.02 / Jaccard 0.80) 또는 공유 베이스 경계가 window 밖이면 전체 기준으로 폴백(팽창 불가, 현행 등가).
- **3 ripple 사이트 봉인** — pipeline `_angles_to_dtw_median_dicts`(S1)·`_deviation_against`(S2)·`safety_flags._dtw_aligned_joint_medians`(S3) 가 window-local path 를 `a_ref[ref_start:ref_end]` 로 소비. 표시·점수·안전 정렬 source 통일 유지.
- **scoring-untouched DATA-GATE** — `dump_scoring_constants.py`(kismam 코드 live 읽기) + `scoring_constants_pinned.json` 을 `gate_check.py --scoring-constants-match` 로 대조. 종료 코드가 게이트다 — trailing `|| echo ... OK` 흡수 버그(codex concern 8) 제거. `test_m3_scoring_untouched_data_gate` 가 drift 주입 시 non-zero 도 검증.

## Task Commits

1. **Task 1: RED — encode 33-M3-SPEC invariants** - `7e13b7b` (test)
2. **Task 2: implement M3 + ripple + data-gate** - `f406676` (feat)

_TDD: RED(9 신규 테스트 + 2 갱신, 전부 올바른 이유로 실패) → GREEN(구현 후 전부 통과)._

## D-19 증거 (무엇을 열어서 확인했는가)

**nu<nr window 실제 발동 (before/after 트림):**
```
nu=48 nr=56 coverage=48/56=0.857
  BEFORE(pre-M3): user (0,48), ref WHOLE (0,56)   -> 준비/대기 정렬 오염
  AFTER (M3)    : user (0,48), ref window (4,52)  -> 준비/대기 앞4 + 뒤4 프레임 트리밍
```

**coverage floor 폴백:**
```
nu=30 nr=50 coverage=0.60 < 0.80 -> fail-closed ref=(0,50)  (전체=팽창 불가)
```

**byte-identical (already-aligned nu==nr):**
```
np.array_equal(dev_m3, dev_full) = True   ref_win=(0,45)
```

**safety-flag baseline diff = 0:**
```
aligned S3 ref_median vs full-ref recompute: max abs diff = 0.0000000000  (신규 FP/FN 0)
```

## Files Created/Modified

- `motiondtw.py` — `MotionMatch(+ref_start,+ref_end)`; `find_action_segment` paired range + `_slide_windows`/`_window_ambiguous` 헬퍼 + `COVERAGE_FLOOR/AMBIGUITY_*` 상수 + optional `ref_boundary`; `motion_dtw` windowed 양쪽 DTW. `per_joint_deviation` **무변경**.
- `segments.py` — `segment_scores` 에 backward-compatible `ref_start/nr_full` 추가(window-local 경계 시프트, §5.1).
- `safety_flags.py` — S3 `_dtw_aligned_joint_medians` 가 `a_ref_win = a_ref[ref_start:ref_end]` 소비.
- `functions/pipeline/app.py` — S1/S2 windowed reference 소비; mode1 이 `ref_boundary`(공유 베이스 경계) 산출 후 `_deviation_against`·`_angles_to_dtw_median_dicts`·`segment_scores` 로 threading.
- `tests/phase33/test_m3_alignment_only.py` — I1~I5 + ambiguity + 구조 바닥 + scoring-untouched data-gate.
- `tests/phase33/test_safety_flags_m3_regression.py` — S3 신규 FP/FN 0.
- `scripts/dump_scoring_constants.py` + `tests/phase33/scoring_constants_pinned.json` — D-20/D-29 JSON data-gate.

## Decisions Made

- **optional `ref_boundary` kwarg (motiondtw + `_deviation_against`)**: 스펙 §2.2 구조 바닥/§4 fail-closed 는 window 선정 단계에서 경계를 알아야 성립한다. locked §1.2 시그니처를 유지하면서 하위호환 kwarg(기본 None)로 추가 — 스펙 이탈이 아니라 잠긴 §2.2/§4 를 실현하는 구현 세부. mode3(이전 영상)는 None.
- **표시·점수 window 통일**: S1(`_angles_to_dtw_median_dicts`)에도 동일 `ref_boundary` 를 threading 해 점수 경로와 같은 window 를 고르게 함(구조 바닥이 발동해 폴백해도 표시/점수 divergence 0).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] MotionMatch 시그니처 변경이 기존 테스트 빌더 5곳에 파급**
- **Found during:** Task 2 (전체 스위트 실행)
- **Issue:** `MotionMatch(start,end,distance,path)` 4-arg 로 합성 매치를 만드는 기존 테스트 5곳이 `ref_start/ref_end` 필수 인자 누락으로 `TypeError`.
- **Fix:** 5곳을 전체-기준 정렬(`ref_start=0, ref_end=max ref idx+1`)로 갱신(33-M3-SPEC.md §7 item 10 "기존 테스트 함께 갱신" 준수).
- **Files modified:** test_motion_alignment.py, test_pipeline_motion_alignment.py, phase32/test_motion_alignment_ladder.py, test_deduction_seed_pointed_merge.py, test_pipeline_deduction_seam.py
- **Verification:** base 커밋과 head 의 전체 필터 스위트 동일 45 pre-existing 실패 / head +16 신규 통과.
- **Committed in:** `f406676`

**2. [Rule 3 - Blocking] 잠긴 §5 ripple 은 files_modified 프론트매터(4파일)를 넘어선다**
- **Found during:** Task 2
- **Issue:** 프론트매터 `files_modified` 는 motiondtw.py + 3 테스트만 나열하나, 잠긴 스펙 §5 는 `pipeline/app.py`·`safety_flags.py`·`segments.py` 의 ripple 수정을 **명시적으로 요구**한다(must_haves 도 3 ripple 사이트 언급).
- **Fix:** 스펙 §5/§5.1 대로 세 파일을 windowed-reference 소비로 수정. 채점 산식 파일(dimensions.py/kismam.py)은 무접촉 유지(`git diff --quiet` 통과).
- **Verification:** gate_check `--scoring-constants-match` PASS + dimensions/kismam byte-unchanged + safety 회귀 green.
- **Committed in:** `f406676`

---

**Total deviations:** 2 auto-fixed (both Rule 3 blocking — 잠긴 스펙 실현에 필수). No scope creep — 채점 산식/임계 무변경.
**Impact on plan:** 정렬 substrate 만 변경. Core Value(채점 정확도) 불변 — byte-identical + constants-hash + JSON data-gate 3중 봉인.

## Issues Encountered

- **전체 스위트에 45 pre-existing 실패 존재**(gemini 모델 버전/`find_scene_flags` 미구현/knee YAML profile 등 — 전부 M3 무관). base 커밋(`7f234bb`)에서 동일 45 실패 재현 확인 → 내 변경의 신규 실패 0. SCOPE BOUNDARY 대로 미수정(범위 밖).
- **12개 spike/smoke 테스트는 수집 단계 ImportError**(torch/rtmlib/`fixtures` 등 optional dep) — base 에서도 동일, 무관.

## Next Phase Readiness

- M3 정렬 substrate 완료 — 33-06(재검증)·33-07(flip) 가 이 windowed-reference 위에서 동작.
- Pod 무접촉(code-only) — 실분석 검증은 후속 재추출/재검증 플랜(33-06+)에서 Pod 로.

## Self-Check: PASSED

- 산출물 파일 6/6 present (motiondtw.py, test_m3_alignment_only.py, test_safety_flags_m3_regression.py, scoring_constants_pinned.json, dump_scoring_constants.py, 33-05-SUMMARY.md).
- 커밋 2/2 present (RED `7e13b7b`, GREEN `f406676`).
- 게이트: M3 스위트 25 passed; gate_check `--scoring-constants-match` PASS; dimensions.py/kismam.py `git diff --quiet` clean.

---
*Phase: 33-result-trust-recovery*
*Completed: 2026-07-23*
