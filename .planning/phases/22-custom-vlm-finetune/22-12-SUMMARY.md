---
phase: 22-custom-vlm-finetune
plan: 12
subsystem: training
tags: [data-flywheel, retrain-cycle, promotion-ratchet, sft-gate, flashinfer, runbook]

# Dependency graph
requires:
  - phase: 22-11
    provides: phase22_watch.py 쌓기 러너 + _meta.collection_batches[] 배치 증분 규약 + FLYWHEEL-RUNBOOK §1(쌓기)
  - phase: 22-04
    provides: full_batch.py 재개 가능 증류 러너(행별 영속화=증분 라벨링 공짜) + assemble_jsonl(--assemble --with-perturb --upload)
  - phase: 22-07
    provides: run_sft.sh / run_sft_gates.sh / merge_and_quant.sh + assert_gates.py D-15 6게이트
provides:
  - run_retrain_cycle.sh 1커맨드 주기 재학습 사이클 러너 (preflight/label/assemble/train/gates/promote 순차 stage)
  - promotion.py 승격 래칫 순수 로직 (parse_gate_verdict/make_ledger_entry/apply_ratchet/make_cycle_report) + CLI
  - promotion_ledger.json 승격 원장 (append-only entries + 단방향 current 포인터)
  - FLYWHEEL-RUNBOOK.md §2(공부하기) 주기 재학습 운영 절차서
affects: [22-08 서빙 swap(current 포인터 진입 조건), 데이터 플라이휠 지속 운영(공부 동사 상설화)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "단방향 승격 래칫: 게이트 PASS(assert_gates --require-pass exit 0)만 current 전진, FAIL 은 attempt 기록만 — 미승격 모델이 current 가 되는 경로 부재(단조성)"
    - "순수 로직 + I/O 껍데기 분리: parse/make/apply 는 boto3/torch import 0 로 테스트, load/save 는 얇은 파일 껍데기"
    - "경로 앵커: cwd=\$ROOT/backend 고정 + ledger 절대경로($ROOT/backend/...) — cwd=backend 상대표기 backend/backend 깨짐 차단"
    - "조건부 flashinfer env: compute_cap >= 12(sm_120 Blackwell)에서만 VLLM_USE_FLASHINFER_SAMPLER=0 + TORCH_CUDA_ARCH_LIST=12.0 자동 적용, A100(sm_80) 강제 금지"
    - "백업 선행 강제: assemble stage 는 jsonl_backup_<ts>/ s3 sync 성공(exit 0) 후에만 canonical 교체 — 백업 실패=사이클 중단"

key-files:
  created:
    - backend/training/sft/promotion.py
    - backend/training/sft/promotion_ledger.json
    - backend/tests/phase22/test_promotion.py
    - backend/training/sft/run_retrain_cycle.sh
  modified:
    - backend/training/FLYWHEEL-RUNBOOK.md

key-decisions:
  - "승격 원장은 게이트 verdict 문자열(PASS/FAIL)과 비용 관측치만 저장 — 사람/judge 점수 수치 저장 금지(객관성 hard gate)"
  - "v7 이전 이력(v4/v5 FAIL)은 원장에 소급 미기재 — 22-07 SUMMARY 가 이력 소유, ledger 는 current=null/entries=[] 초기화"
  - "merge_and_quant 후반 AWQ 실패는 관용(autoawq qwen3_vl 미지원 22-07) — 게이트는 bf16 병합본(<ckpt>-merged, step1 산출)으로 실행"
  - "러너는 게이트 FAIL 에서도 exit 0 정상 종료 + 마지막 줄 NOT PROMOTED 명시 — FAIL 은 실패 아님(데이터는 쌓임)"

patterns-established:
  - "promote stage CLI: python3 -m training.sft.promotion --gate-exit N 이 promoted 를 exit 0/1 로 반환 → 셸이 분기"
  - "stage 재시작 안전: label 은 행별 영속화로 재과금 0, assemble 이후 개별 stage 지정 가능"

requirements-completed: [FT-03, FT-04]

# Metrics
duration: 18min
completed: 2026-07-16
---

# Phase 22 Plan 12: 데이터 플라이휠 공부하기 배치 루프 Summary

**belle 주 1회 1커맨드(run_retrain_cycle.sh all)로 22-11 신규 배치를 라벨(신규분만 과금)→병합 조립(백업 선행)→SFT→D-15 게이트→통과 시만 승격(단방향 래칫)으로 전환하는 주기 재학습 사이클을 기존 자산 orchestration 으로 상설화하고, 게이트 PASS 만 current 를 전진시키는 승격 래칫을 순수 로직+테스트로 박제.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-07-16
- **Tasks:** 3/3
- **Files created:** 4 / modified: 1

## Accomplishments

- **Task 1 (TDD):** 승격 래칫 순수 로직 `promotion.py` — `parse_gate_verdict`(require-pass exit 0 만 pass=True + assert_gates run_all_checks 출력 → per-gate PASS/FAIL) / `make_ledger_entry`(promoted=verdict.pass, judge·사람 점수 저장 0) / `apply_ratchet`(append-only + promoted=True 만 current 전진, 입력 ledger 불변) / `make_cycle_report`(new_labeled/accepted/reject 분해/est_gemini_calls=new_labeled×2/sft_wall/gates/promoted). ledger 초기화(current=null/entries=[]). CLI `python3 -m training.sft.promotion` = promoted 를 exit 0/1 반환. RED(75cfa77)→GREEN(2561992) 2커밋, 9 테스트 pass.
- **Task 2:** `run_retrain_cycle.sh` 6 stage 순차 러너 — preflight(pgrep serial lock + PHASE22_BELLE_GREENLIGHT 과금 게이트 + 디스크 30GB + git pull --ff-only) / label(full_batch 신규분만 과금) / assemble(jsonl_backup_<ts>/ s3 백업 성공 후에만 canonical 교체) / train(run_sft wall 계측) / gates(bf16 병합 + compute_cap>=12 조건부 flashinfer env + run_sft_gates aligned) / promote(promotion 래칫 연동, FAIL 도 exit 0 + 비용 관측치 방출). 경로 앵커(cwd=$ROOT/backend, ledger 절대경로) + PYTHONPATH(shared/python:training:.). 9d84b29.
- **Task 3:** FLYWHEEL-RUNBOOK.md §2(공부하기) — belle 1커맨드 트리거 + 전제 조건 체크리스트(v7 없음/Pod 기동/신규 배치/Gemini 크레딧) + stage 재시작(label 재과금 0) + flashinfer env 박제(sm_120 자동/A100 미설정) + 래칫 해석(FAIL=실패 아님, promotion_ledger 가 current 진실) + 종료 절차(commit/push/Pod stop) + 비용 관측치 필드 표 + 최종 리허설 커맨드. §1 무변형(placeholder 3줄만 교체). c305d65.

## Verification

- `python3 -m pytest backend/tests/phase22 -q` → **302 passed, 1 skipped** (22-11 293 pass 대비 +9 신규 test_promotion, 무회귀).
- `python3 -m pytest backend/tests/phase22/test_promotion.py -q` → 9 passed.
- ledger 초기: `current is None and entries == []` → OK.
- `bash -n backend/training/sft/run_retrain_cycle.sh` → exit 0.
- grep 계약: VLLM_USE_FLASHINFER_SAMPLER=0(1) / compute_cap(4) / jsonl_backup_ line 88 < --assemble line 90 / pgrep serial lock(1) / PHASE22_BELLE_GREENLIGHT(3) 전부 충족. 백그라운드 병렬 실행 0.
- CLI 스모크: `--gate-exit 1` → exit 1 + current 유지(None), `--gate-exit 0` → exit 0 + current 전진 — 래칫 단조성 실증.
- `git diff --quiet` — run_sft.sh / run_sft_gates.sh / assert_gates.py / build_jsonl.py / merge_and_quant.sh **무접촉**.
- promotion.py: judge_score 저장 0 / boto3·torch 최상위 import 0.
- FLYWHEEL §2 grep: TORCH_CUDA_ARCH_LIST(2) / VLLM_USE_FLASHINFER_SAMPLER(1) / run_retrain_cycle.sh(4) / promotion_ledger(3). §1 삭제/변경 0(placeholder 3줄만 교체).

## Deviations from Plan

None - 플랜 3개 태스크를 작성된 대로 실행. Rules 1-4 발동 없음. 실 Pod 사이클 실행(라벨 과금/SFT/게이트)은 플랜 스코프대로 실행하지 않음 — v7 SFT 진행 중이며 운영은 런북 §2 절차(belle 트리거).

## Known Stubs

- promotion_ledger.json 은 current=null/entries=[] 초기 상태 — 첫 실 사이클 promote stage 가 첫 entry 를 append(의도된 초기값, 22-07 이력은 원장 소유 아님).
- cycle_reports/ 디렉토리는 promote stage 실행 시에만 생성(런타임 산출) — 현재 미생성이 정상.
- run_retrain_cycle.sh 의 실 실행 경로(/workspace/*)는 Pod 전용 — 로컬은 bash -n 문법 + grep 계약 + CLI 스모크로만 검증(실 사이클은 v7 종료 후 belle 트리거).

## Threat Surface Notes

플랜 threat_model(T-22-12-01~SC) 범위 내 — 신규 보안 표면 없음.
- T-22-12-01(canonical 파괴): assemble 이 jsonl_backup_<ts>/ s3 sync 성공 후에만 --upload — grep 으로 백업(line 88) < --assemble(line 90) 확인.
- T-22-12-02(FAIL 승격): apply_ratchet 이 promoted=True 만 current 전진, 테스트가 FAIL 후 current 불변·None 유지 강제.
- T-22-12-03(동시 실행 오염): preflight pgrep serial lock + 전 stage 순차(병렬 0) + 런북 전제 조건.
- T-22-12-04(키 유출): 러너는 env 이름만 로그, 키 값 echo 0(코드 리뷰 확인).
- T-22-12-05(이력 부재): cycle_reports JSON + promotion_ledger entries append-only 이중 원장.
- T-22-12-06(비-Blackwell env 파괴): compute_cap 조건부 — sm_120 미만 미설정.
- T-22-12-SC(공급망): 신규 pip 설치 0(기존 러너·게이트 재사용).

## Self-Check: PASSED

- FOUND: backend/training/sft/promotion.py
- FOUND: backend/training/sft/promotion_ledger.json
- FOUND: backend/tests/phase22/test_promotion.py
- FOUND: backend/training/sft/run_retrain_cycle.sh
- FOUND: backend/training/FLYWHEEL-RUNBOOK.md §2
- FOUND: commits 75cfa77 / 2561992 / 9d84b29 / c305d65
