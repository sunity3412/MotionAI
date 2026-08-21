---
phase: quick-260821-umc
plan: 01
subsystem: ml-training
tags: [sft, gates, vllm, runpod, 4090, driver580, promotion, flywheel, oom-stop]

requires:
  - phase: quick-260821-o3m
    provides: "v32 어댑터 checkpoint-68 (A100 학습 완주) + cu124 venv + gates venv gap 선택지"
provides:
  - "v32 bf16 병합본 /workspace/phase22_sft_out/v32-20260821-091049/checkpoint-68-merged (17G — 껍데기 아님, swift 병합 성공 로그 실물)"
  - "측정 확정: bf16 Qwen3-VL-8B + max_model_len 32768 은 24GB 4090 에서 서빙 물리 불가 (GATES_GPU_UTIL 무관, :8000 유무 무관)"
  - "GATES_GPU_UTIL env 노브 (run_sft_gates.sh, 기본 0.90 무회귀)"
  - "sunity_shared.gemini __init__ lazy 화 — pure config 소비자(게이트 하네스)가 google-genai 미설치 venv 에서 생존"
affects: [phase22-flywheel, sft-gates, promotion, next-pod-selection]

tech-stack:
  added: []
  patterns:
    - "venv 인터프리터 심링크는 버전 박힌 경로(/usr/bin/python3.11)로 — 무버전 /usr/bin/python3 는 Pod 교체 시 파손 (train_venv_cu124 실측 재발)"
    - "pgrep -f 원격 감시는 자기 argv 자기매칭 — 패턴에 [h] 브래킷을 써도 launch 라인 원문이 스크립트에 있으면 무력"

key-files:
  created: []
  modified:
    - backend/training/sft/run_sft_gates.sh
    - backend/shared/python/sunity_shared/gemini/__init__.py
    - backend/tests/gemini/test_config.py

key-decisions:
  - "OOM 계약 이행: 0.90 실패(KV 1.96<4.5GiB) → 오류 문구 방향대로 0.95 상향 1회 → 재실패(free 22.04<desired 22.34GiB) → STOP. 추가 조정 없음"
  - "merge_and_quant.sh 전체 대신 step1 커맨드만 직접 실행 — AWQ/gptq 는 qwen3_vl 미지원으로 실패 예정인데 각각 8B 재로드 = 24GB 공유 환경에서 불필요한 OOM 위험 2회"
  - "genai import 결손은 pip 설치가 아니라 리포 수리로 해소 — gemini_teacher 의 문서화된 lazy 계약을 08-18 중앙 config(359b9de5)가 깬 회귀였음 (pip 공급선 0건 유지)"

requirements-completed: []

duration: 50min
completed: 2026-08-21
---

# Quick 260821-umc: v32 게이트 (4090/580 Pod) Summary

> 게이트 선언 라인 `GATES ALLDONE (base=X require_pass=Y)` — **미생성** (두 발사 모두
> vLLM 기동 단계 사망, run1/run2·assert_gates 미도달). require_pass 판정 없음.

**v32 bf16 병합(17G)까지 완료했으나 게이트 vLLM 이 24GB 4090 에서 기동 불가 — 측정 2회로 물리 한계 확정(가중치 16.65 + 오버헤드 ~2.9 + KV 4.5 GiB > 카드 23.52 GiB), OOM 계약(1회 조정) 소진 후 STOP. 게이트 판정 없음, promote 미실행. 다음 수는 belle 결정.**

## 정직 명기 — 어디까지 갔나

| 단계 | 상태 |
|---|---|
| Task 1: GATES_GPU_UTIL 노브 + rp 주석 + preflight | 완료 (commit f4da1ff3 + 07201fc7, Pod HEAD 동기화) |
| Task 2-A: bf16 병합 | 완료 — 17G, "Successfully merged LoRA" 로그 실물, 껍데기 게이트 PASS |
| Task 2-B: canonical gates 발사 | **STOP** — vLLM 기동 2회 실패 (0.90 / 0.95), OOM 계약 소진 |
| Task 3: 판정 처리 | **도달 불가** — 게이트 판정 자체가 없음. promote 미실행(당연), v29 대비 성적표도 작성 불가 (v32 산출물이 0건 — run1/run2 가 시작조차 못 함) |

플랜 must_have 중 "게이트 완주 + cycle_gate_exit.txt 기록"과 "PASS/FAIL 분기"는 **미달성**이다. 병합본·가드 관측·서버 생존·노브는 달성.

## 게이트 판정 원문 — 없음. 대신 vLLM 실패 원문 2건

**시도 1 (GATES_GPU_UTIL 기본 0.90, 13:43 UTC):**
```
ValueError: To serve at least one request with the model's max seq len (32768),
(4.5 GiB KV cache is needed, which is larger than the available KV cache memory
(1.96 GiB). Based on the available memory, the estimated maximum model length is
14272. Try increasing `gpu_memory_utilization` ... or decreasing `max_model_len` ...
```

**시도 2 (GATES_GPU_UTIL=0.95, 오류 문구 지시 방향으로 1회 상향, 13:53 UTC):**
```
ValueError: Free memory on device cuda:0 (22.04/23.52 GiB) on startup is less than
desired GPU memory utilization (0.95, 22.34 GiB). Decrease GPU memory utilization
or reduce GPU memory used by other processes.
```

**측정으로 닫힌 브래킷:** vLLM 이 보는 카드 총량 23.52 GiB. 가중치 로드 실측 16.65 GiB
("Model loading took 16.65 GiB"), 0.90 예산에서 비-KV 오버헤드 역산 ~2.6-3.0 GiB.
KV 4.5 GiB(32k 컨텍스트 1요청 최소)를 더하면 **필요 예산 ≈ 24.1 GiB > 23.52 GiB** —
:8000(1.1 GiB)을 죽여도, util 을 어떻게 잡아도 불가. 두 실패는 동일 한계의 양면이다
(0.90 은 KV 부족으로, 0.95 는 free 부족으로 거절). 로그 실물: Pod
`/workspace/sft_gates_vllm.log`, `/workspace/gates_v32_260821.log`, `..._retry.log`.

## 가드 관측 (기대값 대조 — 전부 일치)

| 가드 | 기대 | 관측 |
|---|---|---|
| run_retrain_cycle.sh gates() flashinfer env (cap>=12) | 미발동 | `[gates] compute_cap=8.9 (<12) — flashinfer env 미설정(비-Blackwell 보호)` — 두 발사 모두 이 라인 |
| run_sft_gates.sh cu129 우회 3종 (cap>=10, o3m 수리) | 미발동 | `[env] Triton ptxas-blackwell` 라인 **부재** (두 발사 모두) |

canonical 경로 자체는 정상 동작 확인: `_latest_ckpt` → v32/checkpoint-68 정해석,
병합본 존재로 merge skip(멱등), env 3종(TRAIN_VENV/GATES_PORT/REPETITION_PENALTY) +
GATES_GPU_UTIL 상속이 vLLM argv 실물로 확인됨
(`--port 8100 --gpu-memory-utilization 0.95 --host 127.0.0.1`).

## VRAM 공유 관측

- :8000 서버 상주: 1112-1122 MiB (pid 1493, 게이트 전 과정 내내)
- vLLM 가중치 로딩 중 피크: 22005 MiB / 24564 MiB (시도 1)
- OOM 조정: 1회 (0.90 → 0.95, 계약 내) — 재실패로 소진, 추가 조정 없이 STOP
- 게이트 vLLM 바인딩: 127.0.0.1:8100 (T-umc-03 — 외부 노출 없음, argv 확인)
- 종료 후: GPU 에 서버만 잔존(1112 MiB), 8100 포트 비어 있음, 게이트 프로세스 0

## rp=1.05 본판정 사용

REPETITION_PENALTY=1.05 를 env 로 지정해 발사했다 (08-18 A/B 결정: 폭주 5/37→0,
파싱실패 11/29→0, 판정 불변 — 원장 s3://sunity-motion-pilot-videos/training/phase22/ab_rp_260818/).
스크립트 헤더의 스테일 "본판정은 1.0 고정" 주석은 f4da1ff3 에서 갱신. 단 vLLM 기동
실패로 **디코딩 단계에 도달하지 못했다** — rp 는 이번 판에서 소비되지 않았다.

## Gemini 회수 + LLM 학습 영향

- Gemini 호출: **0회** (`grep -ci gemini` — gates 로그 0 / retry 로그 0 / merge 로그 0.
  게이트는 --skip-judge 설계라 기대값도 0이었고, 이번엔 추론 자체가 시작 안 됨)
- **LLM 학습 영향: 0** — 이 작업은 병합(가중치 산술)과 서빙 시도뿐, 학습·라벨·canonical
  학습셋 접촉 없음. 원장 누적 변화 없음.

## 프로덕션 무접촉 확인

- :8000 /health — 게이트 전 200, 두 실패 후에도 200 (기준선 유지, E2E 무중단)
- SSM / Lambda env — 무접촉 (읽기도 안 함)
- S3 — 접촉 0 (병합은 로컬 HF 캐시 USE_HF=1, 업로드 단계 미실행)
- promotion_ledger.json — 무변경 (promote 미실행)
- `cycle_gate_exit.txt` 관측: 값 `1`, mtime **Aug 15 04:43** — v29 사이클의 스테일
  FAIL. 이번 러너는 set -e 로 기록 전에 죽어 파일을 안 썼다. 스테일 값이 FAIL 이라
  promote 가 잘못 열릴 위험은 없음(fail-closed). 수기 수정 금지 원칙대로 미수정.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] train_venv_cu124 인터프리터 심링크 파손 (Pod 교체 부작용)**
- **Found during:** Task 1 preflight (`swift --version` → `No module named 'swift'`)
- **Issue:** `bin/python3 -> /usr/bin/python3` (무버전). A100 Pod 에선 3.11.10, 이
  4090 Pod 에선 3.12.3 으로 해석돼 `lib/python3.11/site-packages` (swift 등 전부 존속)가
  비가시화. 메모리 `isolated-venv-must-declare-everything-borrowed` 의 "인터프리터도
  버전 박힌 경로로" 그 사례
- **Fix:** `ln -sfn /usr/bin/python3.11 /workspace/train_venv_cu124/bin/python3`
  (이 Pod 의 3.11.13). pip 0건. 검증: swift 4.4.0 / torch 2.6.0+cu124 / transformers
  5.11.0 / qwen_vl_utils import + CUDA available 전건 통과
- **Files modified:** Pod 측 심링크만 (리포 무변경)

**2. [Rule 1 - Bug] sunity_shared.gemini eager import 회귀 — 게이트 하네스 사망**
- **Found during:** Task 1 preflight venv 진입점 게이트 (`import run_bakeoff` →
  `ImportError: cannot import name 'genai' from 'google'`)
- **Issue:** gemini_teacher 는 "google-genai/boto3 는 lazy import" 를 문서화한 모듈인데,
  08-18 중앙 config 도입(359b9de5)이 `from sunity_shared.gemini.config import ...` 를
  추가했고 패키지 `__init__` 의 eager `.client` import 가 `from google import genai` 를
  무조건 끌고 옴. --skip-judge 라 Gemini 호출 0인 게이트 하네스가 genai 미설치
  venv(ab_venv_cu129)에서 import 사망. 라벨링 Pod 은 시스템 python 에 genai 가 있어
  여태 안 드러남
- **Fix:** `__init__` 을 PEP 562 `__getattr__` lazy 로 전환 (공개 API 불변) + fresh
  인터프리터 회귀 테스트. pip 설치 0건 (플랜의 "신규 패키지 필요 시 STOP" 분기 자체를
  리포 수리로 회피 — 결손이 venv 가 아니라 코드 회귀였음)
- **Tests:** tests/gemini 141 passed + 패키지-레벨 소비자(tests/phase11) 20 passed
- **Files modified:** backend/shared/python/sunity_shared/gemini/__init__.py,
  backend/tests/gemini/test_config.py
- **Commit:** 07201fc7

### 계약 내 처리 (deviation 아님)

- **OOM 계약 1회 조정**: 0.90 실패 원문 박제 → 오류 문구가 지시한 방향(gpu_memory_utilization
  상향)으로 0.95 재발사 → 재실패 → STOP. 계약 문언 그대로 이행

## 다음 수 — belle 과 결정 (단독 처방 금지, 측정 근거 첨부)

게이트를 돌리려면 아래 중 하나. **측정이 지지하는 것은 (a)** — 판정 조건(32k 컨텍스트,
bf16, aligned)을 하나도 안 바꾸는 유일한 길이고, v29 게이트도 32GB(5090)에서 돌았다:

- **(a) 32GB+ VRAM Pod 에서 게이트만 재발사** — 볼륨은 network storage 라 병합본 17G
  그대로 소비. 필요 커맨드는 이번과 동일 (`TRAIN_VENV=/workspace/ab_venv_cu129
  GATES_PORT=8100 REPETITION_PENALTY=1.05 bash training/sft/run_retrain_cycle.sh gates`).
  단 새 Pod 드라이버가 cu129 미만이면 ab_venv 재검증 필요
- (b) max_model_len 축소 (24GB 에서 ~14k 까지) — 게이트 서빙 조건 변경이라 v29 와의
  비교성이 깨진다. aligned 프롬프트(프레임 64장/비디오)가 14k 를 넘으면 판정 자체가
  왜곡됨 — 권장하지 않음
- (c) 4bit 양자화 서빙 — autoawq qwen3_vl 미지원(22-07 실증), llm-compressor 수동
  경로는 미검증 신규 작업

부수 관측: 22-08 서빙 swap 은 여전히 범위 밖 미착수 (게이트 PASS 모델이 생겨도 앱은
안 바뀜 — CONTINUE-08-16 §3).

## Task Commits

1. **Task 1: GATES_GPU_UTIL 노브 + rp=1.05 주석 갱신** - `f4da1ff3` (fix)
2. **Task 1-deviation: gemini __init__ lazy 화 + 회귀 테스트** - `07201fc7` (fix)
3. **Task 2: Pod 측 작업만** (병합 17G + 게이트 2회 발사 + STOP — 리포 파일 없음)

## Known Stubs

없음 — 이번 작업에 UI/데이터 배선 없음.

## Threat Flags

없음 — 신규 표면 없음. 게이트 vLLM 은 127.0.0.1 유지, 프로덕션 무접촉 (위 절 실측).

## Self-Check: PASSED

- backend/training/sft/run_sft_gates.sh (GATES_GPU_UTIL 2매치, bash -n 통과, 기본 0.90) — FOUND
- backend/shared/python/sunity_shared/gemini/__init__.py (lazy) — FOUND
- 커밋 f4da1ff3 / 07201fc7 — origin/main push + Pod HEAD 07201fc7 확인
- 병합본 17G — Pod du 실측 + "Successfully merged LoRA" 로그 원문
- vLLM 실패 원문 2건 — sft_gates_vllm.log 에서 발췌, 본 문서 인용
- :8000 health 200 (전/후) — 실측
- gemini 매치 0/0/0 — 실측
- 게이트 판정/성적표 — **없음 (완주 실패)** — 본 문서가 그 사실 자체를 박제
