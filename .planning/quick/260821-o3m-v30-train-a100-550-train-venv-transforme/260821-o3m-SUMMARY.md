---
phase: quick-260821-o3m
plan: 01
subsystem: ml-training
tags: [sft, qlora, ms-swift, transformers, cu124, runpod, a100, flywheel]

requires:
  - phase: quick-260818 (v30 사이클 label/assemble)
    provides: "s3://sunity-motion-pilot-videos/training/phase22/jsonl/ canonical 학습셋 (08-18 조립 완료본)"
provides:
  - "v30 재학습 train 단계 재발사 — A100 80GB Pod(w340kaemere1po)에서 학습 진행 중 (run dir v32-20260821-091049)"
  - "cu124 핀 레시피 backend/training/sft/pins/cu124-driver550.txt — Pod 교체 시 재현 가능"
  - "setup_train_venv.sh TRAIN_VENV_SKIP_VLLM 노브 + torchvision 명시 설치 (스킵 분기)"
  - "run_sft_gates.sh 우회 가드 Blackwell(compute_cap>=10) 한정 — 비-Blackwell 보호"
affects: [phase22-flywheel, sft-gates, promotion, next-session-monitoring]

tech-stack:
  added: ["torch 2.6.0+cu124", "torchvision 0.21.0+cu124", "transformers 5.11.0 (핀)", "/workspace/train_venv_cu124 (격리 venv, python 3.11.10)"]
  patterns: ["PIP_CONSTRAINT + PIP_EXTRA_INDEX_URL 로 스크립트 무수정 핀 주입", "드라이버-CUDA 상한 맞춤 venv 를 핀 파일로 리포 박제"]

key-files:
  created:
    - backend/training/sft/pins/cu124-driver550.txt
  modified:
    - backend/training/sft/setup_train_venv.sh
    - backend/training/sft/run_sft_gates.sh

key-decisions:
  - "transformers 핀 = 5.11.0 (규칙 b): v29 실증 venv(/workspace/train_venv) 볼륨 부재 → PyPI 실측으로 5.12(사망 버전) 미만 최신 안정판, ms-swift 4.4.0 requires(<5.13,>=4.33) 범위 내, Qwen3-VL 지원(v5.11.0 태그 models/qwen3_vl 존재) 확인"
  - "torch 2.6.0+cu124 = cu124 인덱스 cp311 최종 빌드 실측 (드라이버 550.127.05 = CUDA 12.4 상한, cu129 회피는 locked)"
  - "SFT_RESUME=none 명시 — 볼륨에 v29 checkpoint-* 잔존, auto 는 스테일 재개"
  - "gates 는 이 venv 로 불가(vllm 스킵) — 별도 venv 축, 다음 세션 결정 사항"

patterns-established:
  - "격리 venv 진입점 게이트에 qwen_vl_utils 포함할 것 — swift sft --help 는 qwen_vl_utils 를 import 하지 않아 결손을 못 잡는다 (v31 실측)"

requirements-completed: [QUICK-260821-O3M]

duration: 55min
completed: 2026-08-21
---

# Quick 260821-o3m: v30 train 재개 (A100 + 드라이버 550, cu124 venv) Summary

**v30 을 죽인 transformers 5.12.1 을 실측 핀 5.11.0 으로 교체한 cu124 격리 venv 를 새로 구축, train 재발사 — 첫 optimizer step loss 1.58 실물 확인 (v32 run, 재과금 0).**

## Performance

- **Duration:** ~55 min (발사 후 step 4/68 까지 관측)
- **Started:** 2026-08-21T08:30:16Z
- **Completed:** 2026-08-21T09:25Z (SUMMARY 작성 시점 — 학습은 계속 진행 중)
- **Tasks:** 3/3
- **Files modified:** 3 (리포) + Pod 측 /workspace/train_venv_cu124, /workspace/train_pins_cu124.txt

## Accomplishments

- **v30 사인 해소 입증**: `purely quantized models` ValueError 재발 없이 swift sft 가 어댑터 부착 검증을 통과, step 1 loss 1.58112693 → step 4 까지 정상 진행 (loss 1.58→1.54→1.43→1.54, grad_norm 유한, VRAM 31/80GB)
- **cu124 venv 실측 구축**: torch 2.6.0+cu124 (CUDA 12.4, A100 확인) / transformers 5.11.0 / peft 0.19.1 / accelerate 1.14.0 / bnb 0.50.1 / ms-swift 4.4.0 / decord 0.6.0 / liger_kernel OK — 진입점 import 전건 통과
- **재현 레시피 리포 박제**: 핀 파일 + setup 노브 + 발사 커맨드 원문. Pod 가 또 바뀌어도 드라이버 550 계열이면 그대로 재현
- **재과금 0**: label/assemble 미실행 (S3 jsonl GET 만), `grep -ci gemini cycle_260821.log` = 0
- **기존 자산 무접촉**: train_venv312 / ab_venv_cu129 존속 확인, v30 빈 껍데기·v29 체크포인트 그대로

## Task Commits

1. **Task 1: gates 가드 Blackwell 한정 + setup vllm 스킵 노브** - `a747043f` (fix)
2. **Task 2: Pod cu124 venv 구축 + 진입점 게이트** - (Pod 측 작업만 — 리포 파일 없음)
3. **Task 3-수리: vllm 스킵 시 torchvision 명시 설치** - `cb9e51ba` (fix, deviation)
4. **Task 3: cu124 핀 레시피 박제** - `80d22a82` (docs)

## Files Created/Modified

- `backend/training/sft/pins/cu124-driver550.txt` - cu124 핀 3종 + 실측 근거·발사 커맨드 원문 (Pod `/workspace/train_pins_cu124.txt` 로 미러됨)
- `backend/training/sft/setup_train_venv.sh` - TRAIN_VENV_SKIP_VLLM 노브 (기본 0 무회귀) + 스킵 분기에서 torchvision 명시 설치
- `backend/training/sft/run_sft_gates.sh` - cu129 우회 3종 가드에 compute_cap>=10 조건 (cap 미검출 시 발화 안 함)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] torchvision 미설치로 1차 발사 즉사 → 명시 설치 + 레시피 수리**
- **Found during:** Task 3 1차 발사 (v31-20260821-090524 run)
- **Issue:** `qwen_vl_utils` 가 모듈 최상단에서 `import torchvision` — decord 강제여도 import 는 무조건. 기존엔 vllm 이 torchvision 을 끌어와 돌았는데 TRAIN_VENV_SKIP_VLLM=1 로 공급선이 끊김. 플랜의 "torchvision 핀은 설치 강제 아님" 가정이 실측으로 반증됨
- **Fix:** Pod 에 `torchvision==0.21.0+cu124` constraint 설치 (torch 2.6.0+cu124 유지 확인) + setup 스킵 분기에 명시 설치 추가
- **Files modified:** backend/training/sft/setup_train_venv.sh
- **Commit:** `cb9e51ba`
- **교훈:** 진입점 게이트에 `import qwen_vl_utils` 가 빠져 있었다 (`swift sft --help` 는 이걸 import 안 함). 핀 파일 헤더와 patterns-established 에 박제

## 다음 세션 인계 — 모니터링·재개·다음 수

**★loss 는 stdout 이 아니라 run dir 의 logging.jsonl 에 찍힌다** (swift 4.4 실측). cycle 로그의 Train 진행바 + logging.jsonl 둘로 본다.

```bash
# 진행 (loss 원장 — 관측 시점 step 4/68, ETA ~3h)
ssh -o ConnectTimeout=15 root@213.173.105.5 -p 30279 -i ~/.ssh/id_ed25519 \
  'tail -3 /workspace/phase22_sft_out/v32-20260821-091049/logging.jsonl'

# 프로세스·진행바·에러
ssh ... 'tail -2 /workspace/cycle_260821.log; pgrep -f "swift sft" && echo ALIVE'

# 체크포인트 (save_strategy=epoch — 17 step 마다)
ssh ... 'ls -dt /workspace/phase22_sft_out/*/checkpoint-* | head -3'
```

- **중단 시 재개**: 같은 발사 커맨드(핀 파일 헤더에 원문)에서 `SFT_RESUME=auto` — 이제 v32 의 checkpoint-* 가 최신이므로 auto 가 올바르게 잡는다
- **완주 후 다음 수**: `run_retrain_cycle.sh gates` → `promote`. ★train 은 run_sft.sh 만 돌고 gates/promote 로 이어지지 않는다 — 완주 감시와 게이트 발사는 다음 세션 몫
- **★★gates venv gap (결정 필요)**: `/workspace/train_venv_cu124` 는 TRAIN_VENV_SKIP_VLLM=1 로 만들어 **vllm 이 없다 = 이 venv 로 gates 불가**. Qwen3-VL 을 서빙할 만큼 새로운 vllm 과 cu124 torch(드라이버 550 상한)의 양립 가능성이 낮다. 선택지: (a) 별도 gates venv 를 cu124 로 시도 (vllm 구버전이 Qwen3-VL 지원하는지 실측 필요), (b) 드라이버 570+ Pod 로 옮겨 ab_venv_cu129 계열 재사용, (c) belle 과 Pod 교체 상의. **추측으로 정하지 말고 실측 후 결정**
- **관측 사실**: 추론 서버(:8000)는 계속 떠 있음 — 학습과 공존 중 (VRAM 31/80GB). Pod `pod-expected` SSM 스위치 상태는 이번 작업에서 안 건드림

## Self-Check: PASSED

- backend/training/sft/pins/cu124-driver550.txt — FOUND
- backend/training/sft/setup_train_venv.sh (TRAIN_VENV_SKIP_VLLM) — FOUND
- backend/training/sft/run_sft_gates.sh (compute_cap) — FOUND
- 커밋 a747043f / cb9e51ba / 80d22a82 — origin/main push 확인
- 첫 loss 라인 — /workspace/phase22_sft_out/v32-20260821-091049/logging.jsonl step 1/68 실물 확인
- gemini 게이트 — cycle_260821.log 매치 0
- train_venv312 / ab_venv_cu129 — 존속 확인
