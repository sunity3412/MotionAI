---
phase: quick-260715-fjw
plan: 01
type: execute
status: complete
completed: 2026-07-15
commits:
  - fddada5  # test: failing drift + stage displacement tests (Task 1 RED)
  - 5b3a569  # feat: displacement-first perturb stages via _apply_drift (Task 1 GREEN)
  - 8c71497  # feat: coords-only + subsample-first + stage weighting (Task 2)
tests: "backend/tests/phase22 267 passed / 1 skipped"
---

# Quick Task 260715-fjw — perturb 트랙 재설계 (SUMMARY)

## 목표

Phase 22 SFT v4 aligned 게이트 재계측(2026-07-14)의 잔여 gap — synthetic_holdout 에서
모델이 `corrected_coords=[]` 전량 방출(학습=전부 video+coords vs 게이트=좌표전용 분포
불일치) + v2 진단 "perturb 가 변위 보정을 못 가르침"(holdout ≈ 무보정 기준선) — 을
학습 데이터 측 3처방으로 해소한다. 로컬 코드+테스트만(Pod/GPU/네트워크 0).

## 구현 (2 태스크, TDD)

### Task 1 — perturb.py drift primitive + stage 변위 강화 (D1, D2)
- `_apply_drift(out, ji, start, end, jump_hist, rng)` 신설: [start,end) run 동안 관절에
  **일정한**(프레임 간 동일) 오프셋 벡터를 더하는 지속 변위 primitive. 프레임별 독립
  노이즈인 `_apply_jitter` 와 구분. 크기 = `per_joint_jump_deg` 집계 히스토그램 샘플/90.0
  (기존 jitter 와 동일 환산, 신규 매직 상수 0), 방향 = rng 단위벡터 run 내 고정,
  confidence 채널 불변(가시 오류). run 길이 = `_drift_run_length`(confidence_drop_run_length
  분포 재사용, proxy 명시, 최소 2 프레임).
- stage 1/2/3 전부에 drift run 배선. **핵심: stage2 는 지금까지 순수 가려짐(NaN)이라
  게이트 가시 마스크에서 전량 제외 → 게이트 대상 변위 신호 0 이었음.** stage2/3 는
  가려진 관절을 회피해 drift 를 미가려짐 관절에 주입(가시성 보장).
- 기존 test_perturb.py 7개 계약(비핵심/핵심/스왑/재현성/profile=None TypeError) 불변.

### Task 2 — build_jsonl.py subsample-first + 좌표전용 + stage cycle + cc 근거 (D3~D6)
- **D3 stage cycle**: `_STAGE_CYCLE = (1, 1, 2, 3)` 상수 + `stage = _STAGE_CYCLE[k % 4]`
  (균등 `(i%3)+1` 교체). 변위-순수 stage1 2배 가중.
- **D4 subsample-first**: `coords[idxs]` 로 먼저 서브샘플한 (N,J,C) 배열에 perturb_sequence
  적용 → 모든 교란이 표시 프레임에 반드시 반영(순수 항등 echo 샘플 0). 과거엔 전체 T
  교란 후 ≤64 서브샘플이라 교란 프레임 대다수가 표시 밖으로 빠졌음(v2 "무보정 동률"의
  기계적 원인). `_coords_to_frames` 에 `frame_labels` 파라미터 추가 — 배열 인덱스(0..N-1)와
  frame 라벨(원본 영상 프레임 번호 idxs)을 분리, user 행/corrected_coords 행 라벨 일치.
- **D5 좌표전용 혼합**: eligible perturb 행 순번 `k % 3 == 2`(1/3)는 video 파트 없이
  좌표전용 방출. user 텍스트 = `_rtmw_text(user_frames) + _TASK_INSTRUCTION`(모듈 상수
  재사용 — 게이트 `build_aligned_report_messages(rows, [])` 좌표전용 경로와 문자 단위
  동일, 단일 진실). `_coords_only: True` 마킹 + `_meta.perturb_coords_only_count` 카운터.
  `_track="perturb"` 유지 → video_hash split 이 두 양식을 같은 쪽에 두어 leakage 0.
- **D6 corrected_coords 전체 프레임 echo 유지**(변경 프레임만 방출 채택 안 함): 근거를
  코드 주석으로 박제 — 부분 방출은 모델이 쉬운 프레임만 골라 상대 게이트를 cherry-picking
  으로 뒷문 무력화(=게이트 완화) 가능. 항등 echo 밀도는 D3/D4/drift 의 변위 밀도 확대로
  실질 신호 비율을 올려 해소(v3 distill echo 익사와 다름 — distill cc=None 은 v4 에서 이미 제거).

## 순번 인덱스 정정
`stage`·`coords_only` 결정 기준을 원본 row 인덱스에서 **eligible+loaded 통과 순번 k**로
교체 — 중간에 미가명 고객/holdout 행이 걸러져도 cycle 이 어긋나지 않는다.

## 검증
- `backend/tests/phase22` **267 passed / 1 skipped** (기준 258 + Task1 3 + Task2 6). FAILED/ERROR 0.
- `_TASK_INSTRUCTION` 정의 build_jsonl.py 단일(grep 게이트). test_bakeoff_harness 의
  `rb._TASK_INSTRUCTION is build_jsonl._TASK_INSTRUCTION` import 동일성 무회귀.
- 변경 파일 = frontmatter files_modified 4개뿐. `backend/evals/phase22/`(run_bakeoff,
  assert_gates) 및 `backend/shared/python/sunity_shared/analysis/` diff 0(게이트 완화 0, 채점 무접촉).

## 게이트 영향 (하네스 무수정, 문서화만)
run_bakeoff synth 항목은 `perturb.perturb_sequence` 를 직접 호출하므로 D1/D2 로 v5 게이트의
교란 자체가 달라진다 — `grounding_uncorrected` 기준선도 매 run 재계산되어 **상대 게이트
semantics 는 불변(완화 아님)**이나 **v4 절대 수치와 직접 비교는 불가**하다. 좌표전용 1/3 ·
stage cycle (1,1,2,3) 은 ablation 축(방향이 근거, 수치 자체가 근거 아님).

## 다음 단계 (스코프 밖)
Pod 에서 `--assemble --with-perturb --upload` v5 조립 → SFT v5 → aligned 게이트 재판정.
게이트 판정 시 synthetic_holdout(좌표전용 보정)과 eval18(fault 짚기, 실결함 라벨 118개로 확대)
두 축을 관건으로 본다.
