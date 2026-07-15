---
phase: quick-260715-wq9
plan: 01
subsystem: phase22-vlm-training-dataset
tags: [phase22, vlm, distill, build_jsonl, gemini-teacher, dataset-rebalance]
requires:
  - backend/training/distill/gemini_teacher.py (교사 프롬프트)
  - backend/training/datagen/build_jsonl.py (학습셋 조립)
provides:
  - 결함 다중 열거 지시 강화된 교사 프롬프트 (A)
  - fault-ratio 재균형 캡 + _meta 관측치 (B)
  - corrected_coords descope 가역 플래그 include_perturb=False (C1)
affects:
  - 다음 교사 재라벨(Gemini 과금, scope 밖) + assemble_jsonl 산출물
tech-stack:
  added: []
  patterns: [ablation-축-상수, 가역-descope-플래그, fail-closed-guard]
key-files:
  created: []
  modified:
    - backend/training/distill/gemini_teacher.py
    - backend/tests/phase22/test_gemini_teacher.py
    - backend/training/datagen/build_jsonl.py
    - backend/tests/phase22/test_build_jsonl.py
    - backend/training/distill/full_batch.py
decisions:
  - "belle C1 (2026-07-15): perturb 트랙 기본 off (include_perturb=False), 코드 보존 = 가역 descope"
  - "FAULT_FREE_CAP_RATIO=1.5 = ablation 축 (수치 아닌 '정타 익사 차단' 방향이 근거)"
  - "fault-free 만 트림 (오버샘플/fault-bearing 부풀리기 금지 = overfit 방지)"
metrics:
  duration: ~35m
  completed: 2026-07-15
  tasks: 2 (Task 2 = belle C1 결정, 구현만)
  tests: 273 passed / 1 skipped (phase22 전체)
---

# Phase 22 v6 Plan wq9: 학습셋 조립 3축 교정 (교사 밀도 + 재균형 + descope) Summary

Gemini 교사 프롬프트 밀도 강화(A) + build_jsonl fault-ratio 재균형(B) + corrected_coords 방출 학습 가역 descope(C1)로 v5 SFT 게이트 FAIL의 데이터 근본원인(결함 신호 희박·불균형 + 학습 불가능한 좌표 타겟)을 코드+테스트로 제거했다. 재라벨/SFT는 scope 밖.

## What was done

### Task 1 (A) — 교사 프롬프트 결함 다중 열거 지시 강화
- `build_teacher_system_prompt` 에 "결함 영상에서는 관찰되는 모든 결함을 빠짐없이 각각 별도 faults[] 항목으로 산출 — 가장 뚜렷한 하나만 짚고 나머지를 생략하지 말 것" 지시 한 문장 추가.
- 진단: 교사 fault 중앙값 1개/영상(뚜렷한 하나만 짚는 관성) → 학생이 결함 미방출을 학습.
- 정타 빈 배열([]) / 억지 결함 금지 문장 바로 위에 인접 배치 → 다중 열거가 정타 위양성으로 번지지 않게 결함/정타 대비 유지(위양성 invariant 보존).
- fault 필드 계약·fault_category enum 주입·motion 조건부 판정 로직·점수 금지 문장 전부 불변. schema 무접촉. 함수 시그니처/반환 구조 불변(텍스트만 확장).
- 커밋: `1ba61d8`

### Task 2 — belle C1 결정 (checkpoint, 구현만)
- belle 확정: C1 (flag-remove, 가역). perturb 트랙을 기본 학습셋에서 제외하되 코드/상수/테스트는 보존 — `include_perturb=True` 로 언제든 부활. NotebookLM 좌표 CoT 비전은 삭제가 아니라 보류.

### Task 3 (B + C1) — build_jsonl 재균형 + descope
- **C1**: `build_dataset(..., include_perturb: bool = False)` 파라미터 추가. 기본 False → `_build_perturb_samples` 미호출. `_build_perturb_samples` / quick-260715-fjw 로직·상수(`_STAGE_CYCLE` 등)는 코드 보존(가역). perturb 전용 기존 테스트는 `include_perturb=True` 명시 호출로 도먼트 경로 커버 유지.
- **B**: `_cap_fault_free(media, cap_ratio)` — 각 미디어에 `_has_faults = bool(report["faults"])` 태깅(perturb/shadow=False, distill=가능) 후, fault-free 를 fault-bearing 대비 `FAULT_FREE_CAP_RATIO(=1.5)` 배 이하로 결정적(안정 입력 순서) 트림. 오버샘플/중복 0.
  - `fault_bearing==0` guard: 캡 skip(전량 트림 방지).
  - fault-bearing 은 절대 트림하지 않음 — fault-free 만 캡(overfit/curve-fit 방지).
  - `_meta` 에 `fault_bearing_count` / `fault_free_count` / `fault_free_cap_ratio` 관측치 방출(드롭률 은폐 불가).
- 커밋: `2988e8c`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] full_batch.assemble_jsonl 반전 경로 no-op 방지**
- **Found during:** Task 3
- **Issue:** `assemble_jsonl` 은 `perturb_loader` 는 넘기지만 `include_perturb` 는 넘기지 않았다. build_dataset 기본값이 False 로 바뀌면서 `--with-perturb` CLI 플래그가 loader 를 주입해도 perturb 가 조립되지 않는 silent no-op 발생(C1 가역성 반전 경로 파손).
- **Fix:** `assemble_jsonl` 에서 `include_perturb=perturb_loader is not None` 로 유도 — orchestrator 층 계약(loader 주입=의도)에 맞춰 기존 `--with-perturb` 동작을 정확히 보존. loader 미주입 시 distill 트랙만(기존 동작 불변).
- **Files modified:** backend/training/distill/full_batch.py
- **Commit:** `2988e8c`
- full_batch.py 는 게이트(assert_gates/run_bakeoff)가 아닌 조립 orchestrator라 무접촉 목록 밖 — Rule 3 일관성 수정.

## Invariants preserved
- 위양성 방지: 교사 정타 억지 결함 금지 문장 보존(test 회귀 0) + `fault_free_count > 0` 유지(정타 신호 완전 소거 = 역방향 위양성 실패 방지).
- overfit 없음: fault-bearing 트림·오버샘플 아닌 fault-free 캡만.
- 무접촉 확인(git diff 0): `schema.py`(REPORT_KEYS/DEDUCTION_CONSUMED_KEYS/fault enum), `analysis/`, `evals/phase22/assert_gates.py`, `evals/phase22/run_bakeoff.py`.
- 재라벨(Gemini 과금)·SFT(GPU) 미포함(scope 밖).

## Verification
- `cd backend && python3 -m pytest tests/phase22/ -q` → **273 passed, 1 skipped** (baseline 267 → +6: 신규 gemini 1 + 신규 build_jsonl 5).
- 무회귀: score-free / hard-negative 격리 / video_hash split leakage 0 / shadow 드롭 카운터 / validation_owner·collection_complete 게이트 전부 pass.
- 갱신 계약 테스트: perturb 전용 7건 → `include_perturb=True` 명시(도먼트 경로 커버).

## Known Stubs
없음.

## Next
- 교사 재라벨 배치(Gemini 과금, belle greenlight + Pod) — A 밀도 강화 프롬프트로 fault 다중 열거 라벨 재수집.
- assemble v6 + SFT v6 (GPU) — B 재균형 + C1 descope 반영된 학습셋으로.
