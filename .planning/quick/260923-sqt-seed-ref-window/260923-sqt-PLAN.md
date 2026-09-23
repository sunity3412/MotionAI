---
quick_id: 260923-sqt
slug: seed-ref-window
date: 2026-09-23
mode: quick (inline — 260923-smt 와 같은 사유)
---

# Quick 260923-sqt — 감점 재료가 기준의 엉뚱한 구간과 비교되는 결함 수리

## 문제 (코드 사실)

- `MotionMatch.path` 의 기준 인덱스는 **window-local** 이다 (`motiondtw.py:130-136` 계약).
- 점수 경로 `_deviation_against` 는 `a_ref[ref_start:ref_end]` 로 잘라 쓰고, 반환은 **전체** `a_ref` 다
  (`app.py:7044-7049`, 독스트링이 "전체 a_ref 로 넘기면 인덱스 어긋남 → 조용한 오채점"이라 경고).
- mode1 은 그 전체 `a_ref` 를 `reference_angles_for_veto` 로 받아(`app.py:8453`) 감점 builder 에
  넘긴다(`app.py:8827`). mode3 기준 축(`_mode3_reference_relative`)도 전체 `a_ref` 를 넘긴다.
- `_build_deduction_measured_deviations` 의 DTW fallback 은 그 전체 배열을 자르지 않고
  `per_joint_deviation` · `per_joint_median_ci` · `per_joint_representative_frames` 에 넣는다.
- 33-M3-SPEC 이 window-local 인덱스를 도입할 때 `_deviation_against`(S2) ·
  `_angles_to_dtw_median_dicts`(S1) · segment 채점은 고쳤고 이 builder 만 빠졌다.
  기존 테스트는 전부 `ref_start=0` 이라 못 잡았다.

## 언제 터지나

`find_action_segment` 가 기준 안에서 창을 미끄러뜨리는 경우 = 학생 프레임 수가 기준의
80~100%. 학생 분석은 ~10fps, 기준은 ~15fps 라 **학생 영상 길이가 기준의 1.2~1.5배**일 때다.
정은지 fixture 는 전부 이 밖(0.52~0.77)이라 지금까지 측정에 한 번도 안 걸렸다.

## Task 1 — 실패하는 회귀 테스트

`backend/tests/test_deduction_seed_ref_window.py` — 기준의 뒷부분을 학생으로(한 관절만 +25도)
넣어 **감점 seed = 점수 경로 편차**를 관절마다 단언. 전제(`ref_start > 0`)를 명시 단언해
공허 통과를 막는다. 수정 전 실패 확인.

## Task 2 — 수리

builder 안에서 `reference_angles[ref_start:ref_end]` 로 한 번 잘라 세 호출에 쓴다.
창이 기준 전체([0, nr))면 byte-동일. 채점 산식·허용오차·기울기 무접촉.

## Task 3 — 검증

- 새 테스트 통과 + 전체 게이트(backend/.venv 직접)
- 운영 함수 + 실제 기준 doc 재현 스크립트로 수리 전후 대조
- 2026-09-22 운영 11건이 전부 `ref_start=0` 인지 확인(= 과거 점수 불변)
