---
phase: quick-260821-umc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/training/sft/run_sft_gates.sh
  - backend/training/sft/promotion_ledger.json
  - .planning/quick/260821-umc-v32-gates-4090-580-pod-vllm-serve-v29-pr/260821-umc-SUMMARY.md
autonomous: true
requirements: [QUICK-260821-UMC]
tags: [sft, gates, vllm, runpod, 4090, driver580, promotion, flywheel]

must_haves:
  truths:
    - "v32(checkpoint-68) bf16 병합본이 존재하고 크기가 정상(약 16~17GB — 껍데기 아님)이다"
    - "게이트가 canonical 경로(run_retrain_cycle.sh gates)로 완주해 require_pass 판정이 cycle_gate_exit.txt 에 기록된다"
    - "4090(sm_89)에서 Blackwell 우회 가드 2종(compute_cap>=10 / >=12)이 미발동으로 관측·기록된다 (어긋나면 STOP 아니라 관측 기록)"
    - ":8000 추론 서버가 게이트 전 과정 후에도 /health 200 으로 살아 있다"
    - "PASS 면 promote 실행 + ledger commit/push, FAIL 이면 v29 대비 항목별 성적표가 SUMMARY 에 박제된다"
  artifacts:
    - path: "backend/training/sft/run_sft_gates.sh"
      provides: "GATES_GPU_UTIL env 노브 (기본 0.90 무회귀) + rp 헤더 주석의 08-18 A/B 결정 반영"
      contains: "GATES_GPU_UTIL"
    - path: ".planning/quick/260821-umc-v32-gates-4090-580-pod-vllm-serve-v29-pr/260821-umc-SUMMARY.md"
      provides: "게이트 판정 원문 + v29 대비 성적표(또는 promote 결과) + 가드/VRAM/Gemini 관측"
  key_links:
    - from: "backend/training/sft/run_retrain_cycle.sh (gates stage)"
      to: "backend/training/sft/run_sft_gates.sh"
      via: "env 상속 (TRAIN_VENV / GATES_PORT / REPETITION_PENALTY — `VAR=x bash cmd` 는 자식까지 전파)"
      pattern: "run_sft_gates.sh"
    - from: "backend/training/sft/run_retrain_cycle.sh (promote stage)"
      to: "/workspace/phase22_distill_out/cycle_gate_exit.txt"
      via: "gates stage 만 이 파일을 쓴다 — run_sft_gates.sh 직접 호출로는 promote 가 fail-closed(FAIL) 로 읽는다"
      pattern: "GATE_EXIT_FILE"
---

<objective>
오늘 A100 에서 완주한 v32 어댑터(checkpoint-68)를 새 4090/드라이버 580 Pod 에서
D-15 게이트로 판정하고, PASS 면 사이클 절차대로 promote 까지, FAIL 이면 v29 대비
항목별 성적표를 박제한다.

Purpose: v32 는 재료 확충(286 admit) + 파이프라인 수리 후 첫 판이다. v29 성적
(빈 골격 9/29 · faults 2건 · 4동작 중 1동작 · 게이트 FAIL)을 넘는지가 08-18 진단
("원인은 디코딩 아니라 학습 쪽")의 검증이다.
Output: 게이트 판정 원문 + promote 실행(조건부) 또는 성적표 SUMMARY. LLM 학습 영향 0
(게이트는 추론만 — SUMMARY 에 명시).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@backend/training/sft/run_sft_gates.sh
@backend/training/sft/run_retrain_cycle.sh
@backend/training/export/merge_and_quant.sh
@.planning/quick/260821-o3m-v30-train-a100-550-train-venv-transforme/260821-o3m-SUMMARY.md
@.planning/CONTINUE-2026-08-16.md
@.planning/CONTINUE-2026-08-19.md
</context>

<preflight_facts>
이 세션 실측 (재조사 금지, 대조만):

- SSH: `ssh -o ConnectTimeout=15 root@213.173.108.156 -p 10981 -i ~/.ssh/id_ed25519`
  — 4090 24GB, 드라이버 580.178(CUDA 13.0). 볼륨 리포는 오늘 HEAD 까지 pull 됨.
- v32 어댑터: `/workspace/phase22_sft_out/v32-20260821-091049/checkpoint-68`
  (LoRA, base = Qwen/Qwen3-VL-8B-Instruct — run_sft.sh 기본값, args.json 으로 확정).
- 추론 서버 :8000 가동 중 (앱 분석 경로) — **죽이지 말 것**. 게이트 vLLM 은 GATES_PORT=8100.
- venv 지형 (o3m 인계): `/workspace/train_venv_cu124` = swift/transformers 있음·vllm 없음
  (병합용). `/workspace/ab_venv_cu129` = vllm 있음 (08-18 A/B 서빙 실증). 게이트는
  이 두 venv 를 단계별로 나눠 쓴다 — o3m 인계의 gates venv gap 선택지 (b) "드라이버
  570+ Pod 에서 ab_venv_cu129 계열 재사용"이 이 Pod 에서 성립 (580 = CUDA 13.0 ≥ cu129).
- 디코딩: REPETITION_PENALTY=1.05 (08-18 A/B 검증 — 폭주 5/37→0 · 파싱실패 11/29→0 ·
  판정 불변. 원장 `s3://sunity-motion-pilot-videos/training/phase22/ab_rp_260818/`).
  스크립트 헤더의 "본판정은 1.0 고정"은 A/B 이전 문장 — 실측 > 이전 결정.
- 가드 기대값: run_sft_gates.sh 우회 3종은 compute_cap>=10 한정 (o3m 이 오늘 수리),
  run_retrain_cycle.sh gates() flashinfer env 는 cap>=12 한정. 4090 = cap 8.9 →
  **둘 다 미발동이 기대값**. 어긋나면 STOP 아니라 관측 기록.
- 게이트 파서는 08-16 수리됨 (잘린 조각 오인정 e26). 판정 = require-pass exit code +
  러너의 선언값 교차검증 (fail-closed).
- 넘어야 할 선 = v29: 빈 골격 9/29 · 내용 있는 산출 5 · faults 2건 · coaching 1,392자 ·
  산출 평균 18,733byte · 4동작 중 1동작 · FAIL (CONTINUE-2026-08-16 §v29 판정 표).
  FAIL 사유 4줄(eval18 power-spin 파싱 / 3동작 결함 0건 / svg_spec / determinism)과 1:1 대조.
</preflight_facts>

<tasks>

<task type="auto">
  <name>Task 1: GATES_GPU_UTIL 노브 + rp 주석 갱신 (리포) → Pod pull + preflight 실측</name>
  <files>backend/training/sft/run_sft_gates.sh</files>
  <action>
리포 수정 (2건, 커밋 1개, push 후 Pod pull — "Pod 작업 = push 한 단위"):

1. `run_sft_gates.sh` 의 vLLM serve 인자 `--gpu-memory-utilization 0.90` 을
   `--gpu-memory-utilization "${GATES_GPU_UTIL:-0.90}"` 로 교체. 바로 위에 짧은 주석:
   24GB Pod 에서 :8000 추론 서버와 VRAM 공유 시 OOM 1회 조정용 노브 (2026-08-21),
   기본 0.90 무회귀. `merge_and_quant.sh` 쪽 0.90 은 건드리지 않는다 (범위 밖).
2. 헤더의 REPETITION_PENALTY 주석("rp A/B 관찰 전용 — 본판정은 1.0 고정")을 갱신:
   2026-08-18 A/B 실측 (폭주 5/37→0, 파싱실패 11/29→0, 게이트 판정 불변 —
   s3://…/training/phase22/ab_rp_260818/) 이후 본판정도 1.05 사용, 호출자가 env 로 지정.
   스테일 결정 주석을 남기면 다음 세션이 검증 없이 승계한다 (handoff 원칙).

`bash -n backend/training/sft/run_sft_gates.sh` 통과 확인 후 commit+push
(`fix(quick-260821-umc): gates gpu-util 노브 + rp=1.05 본판정 주석 갱신`).

Pod preflight (전부 읽기 전용, SSH 원라이너로 실측 기록):
- `git -C /workspace/SunityMotion pull --ff-only` → HEAD 에 위 커밋 포함 확인
- `nvidia-smi` — VRAM used/total 스냅샷 (서버 상주분 실측), 드라이버 580.178, cap 8.9
- `df -h /workspace` — 여유 25GB 이상 (병합본 약 17GB + 로그). 미달이면 STOP (정리는 belle 상의)
- `ls /workspace/phase22_sft_out/v32-20260821-091049/checkpoint-68/` + `args.json` 에서
  base model 라인 확인 (Qwen/Qwen3-VL-8B-Instruct 기대)
- `ls /workspace/bakeoff_fixtures /workspace/phase22_coords_cache` — 게이트 입력 존재
- `ls /workspace/hf_cache` 에 Qwen3-VL-8B 스냅샷 존재 (병합이 HF 캐시에서 로드, USE_HF=1)
- `curl -sf http://127.0.0.1:8000/health` — 추론 서버 생존 기준선
- 8100 포트 비어 있음 (`ss -tlnp | grep 8100` 무매치)
- venv 진입점 게이트 (o3m 교훈 — 패키지 목록이 아니라 호출되는 진입점 import):
  `/workspace/ab_venv_cu129/bin/python -c "import vllm, openai"` 그리고
  `cd /workspace/SunityMotion/backend && PYTHONPATH=shared/python:training:. /workspace/ab_venv_cu129/bin/python -c "import sys; sys.path.insert(0,'evals/phase22'); import run_bakeoff, assert_gates"` 그리고
  `/workspace/train_venv_cu124/bin/swift --version` (병합 도구)
- import 결손 시 계약: 볼륨 내 기존 venv(train_venv312/train_venv_cu124)에 이미 있는
  패키지를 **동일 버전으로만** ab_venv_cu129 에 pip 설치 (신규 패키지 도입 금지 —
  필요해지면 STOP). torch/vllm/triton 은 절대 재설치 금지. 설치 내역은 SUMMARY 에 기록.
  </action>
  <verify>
    <automated>bash -n backend/training/sft/run_sft_gates.sh && grep -c GATES_GPU_UTIL backend/training/sft/run_sft_gates.sh && ssh -o ConnectTimeout=15 root@213.173.108.156 -p 10981 -i ~/.ssh/id_ed25519 'grep -c GATES_GPU_UTIL /workspace/SunityMotion/backend/training/sft/run_sft_gates.sh && curl -sf http://127.0.0.1:8000/health >/dev/null && echo SERVER_UP'</automated>
  </verify>
  <done>노브 커밋이 origin/main + Pod HEAD 양쪽에 있고, preflight 체크리스트 전 항목이 실측값과 함께 기록됨 (차단 항목 0 또는 계약 내 해소). :8000 기준선 UP.</done>
</task>

<task type="auto">
  <name>Task 2: bf16 병합 → canonical gates 발사·완주 (nohup detached + 관측)</name>
  <files>(Pod 측 작업만 — 리포 파일 없음)</files>
  <action>
**단계 A — bf16 병합** (merge_and_quant.sh step 1 과 문자 동일한 커맨드를 직접 실행):

`cd /workspace/SunityMotion/backend && export HF_HOME=/workspace/hf_cache USE_HF=1 && nohup /workspace/train_venv_cu124/bin/swift export --adapters /workspace/phase22_sft_out/v32-20260821-091049/checkpoint-68 --merge_lora true > /workspace/merge_v32.log 2>&1 &`

merge_and_quant.sh 전체를 안 돌리는 이유 (판단 근거 박제): step 2 의 AWQ→gptq 는
qwen3_vl 미지원으로 실패가 예정돼 있는데 (22-07 실증, gates() 도 이미 관용) 그 두
시도가 각각 8B 모델을 다시 로드한다 — :8000 과 공유하는 24GB 에서 불필요한 OOM
위험 2회. gates() 는 `<ckpt>-merged` 존재만 보고 병합을 skip 하므로(멱등 재개)
단계 A 만으로 충분하다. swift 규약상 산출 경로는 `checkpoint-68-merged` 고정
(--output_dir 무시, 2026-07-12 실증).

완료 대기 후 **껍데기 게이트** (CONTINUE-2026-08-16 규율 — 쿼터 사건 재발 방지):
`du -sh .../checkpoint-68-merged` 가 약 16~17GB. 크게 미달이면 STOP (판정 금지).

병합 OOM 폴백 (1회): `free -g` 로 RAM 실측 후 40GB 이상이면
`CUDA_VISIBLE_DEVICES=""` 붙여 CPU 병합 재시도. RAM 미달이거나 재실패면 STOP.

**단계 B — 게이트 발사** (canonical 경로 — promote 가 읽는 cycle_gate_exit.txt 는
gates stage 만 쓴다. run_sft_gates.sh 직접 호출 금지):

`cd /workspace/SunityMotion/backend && TRAIN_VENV=/workspace/ab_venv_cu129 GATES_PORT=8100 REPETITION_PENALTY=1.05 nohup bash training/sft/run_retrain_cycle.sh gates > /workspace/gates_v32_260821.log 2>&1 &`

env 3종은 자식(run_sft_gates.sh)까지 상속된다. PROMPT_MODE=aligned 는 gates() 가
자체 지정. 장시간(vLLM 기동 최대 20분 + run1/run2 판정 생성 수시간) — detached 유지,
SSH 로 주기 관측:
- `/workspace/gates_v32_260821.log` — 기대 라인: "[gates] compute_cap=8.9 (<12) —
  flashinfer env 미설정" / "[env] Triton ptxas-blackwell" 라인 **부재** (가드 미발동).
  어긋나면 관측 기록하고 진행 (프로세스가 죽지 않는 한 STOP 아님)
- `/workspace/sft_gates_vllm.log` — "serve UP" 도달, vLLM 이 127.0.0.1 바인딩인지 확인
- `nvidia-smi` 주기 스냅샷 — VRAM 경합 관측 (앱 분석 유입 시 관측만, 개입 금지)

**OOM 계약 (1회 한정)**: vLLM 이 메모리 사유로 기동 실패/사망하면 로그 원문 박제 후
`GATES_GPU_UTIL` 값 1회 조정 재발사 (vLLM 오류 문구가 지시하는 방향으로 — 예:
"desired utilization" 부족 문구면 0.95 상향). 재실패면 STOP — 다음 수는 belle 과 결정.

**완주 판정**: 게이트 로그에 `GATES ALLDONE (base=X require_pass=Y)` +
`[gates] 게이트 exit=` 라인 + `/workspace/phase22_distill_out/cycle_gate_exit.txt`
실물. assert_gates 두 모드 출력 원문(항목별 PASS/FAIL/SKIP)을 로컬로 확보
(scp 또는 로그 발췌 — scratchpad 는 휘발이므로 SUMMARY 에 원문 인용).
Gemini 회수 집계: `grep -ci gemini /workspace/gates_v32_260821.log` (기대 0 —
--skip-judge). :8000 `/health` 재확인 (기준선 대비 생존).
  </action>
  <verify>
    <automated>ssh -o ConnectTimeout=15 root@213.173.108.156 -p 10981 -i ~/.ssh/id_ed25519 'du -s /workspace/phase22_sft_out/v32-20260821-091049/checkpoint-68-merged | awk "{exit !(\$1 > 10000000)}" && grep -c "GATES ALLDONE" /workspace/gates_v32_260821.log && cat /workspace/phase22_distill_out/cycle_gate_exit.txt && curl -sf http://127.0.0.1:8000/health >/dev/null && echo SERVER_STILL_UP'</automated>
  </verify>
  <done>병합본 크기 정상 확인 후 gates stage 완주 — ALLDONE 선언 + cycle_gate_exit.txt 기록, 선언값·exit 교차검증 결과 확보. 가드 미발동/VRAM/Gemini=0 관측 확보. :8000 생존.</done>
</task>

<task type="auto">
  <name>Task 3: 판정 처리 — PASS 면 promote, FAIL 이면 v29 대비 성적표 + SUMMARY 박제</name>
  <files>backend/training/sft/promotion_ledger.json, .planning/quick/260821-umc-v32-gates-4090-580-pod-vllm-serve-v29-pr/260821-umc-SUMMARY.md</files>
  <action>
cycle_gate_exit.txt 값으로 분기:

**exit=0 (PASS)**: 사이클 절차대로 promote 실행 —
`cd /workspace/SunityMotion/backend && bash training/sft/run_retrain_cycle.sh promote 2>&1 | tee /workspace/promote_v32.log`
- 리포트 JSON(`/workspace/cycle_reports/cycle_*.json`)을 **직접 열어** 전 필드 확인
  (사이클 비용 관측치 은폐 금지). PROMOTED / NOT PROMOTED 마지막 라인 기록.
- 관측 caveat: v32 train 은 run_sft.sh 직발사라 `cycle_sft_wall.txt` 가 스테일/부재
  (wall 폴백 0) 가능 — promotion 이 어떻게 기록하는지 관측만, 값 조작 금지.
  promote 가 입력 부재로 예외를 내면 원문 박제 후 STOP (ledger 수기 수정 금지).
- ledger 변경분을 Pod 에서 commit+push (Pod 작업 = push 한 단위), 로컬 pull 로 실물 확인.
- 22-08 서빙 swap(앱이 실제로 새 모델을 쓰게 하는 고리)은 **범위 밖** — SUMMARY 의
  "다음 수"로 기재만.

**exit!=0 (FAIL)**: promote 실행 금지 (NOT PROMOTED 는 실패 아님 — 데이터는 쌓임).
성적표를 작성해 SUMMARY 에 박제:
- v32 수치 추출: assert_gates 출력 + `/workspace/eval_out` 의 run1/run2 산출물에서
  빈 골격 n/29, 내용 있는 산출 수, faults 건수, faults 를 짚은 동작 수(4 중),
  coaching 자수, 산출 평균 byte, 게이트 항목별 판정(eval18 / svg_spec / determinism /
  synthetic_holdout SKIP 여부). 산출물 실물을 열어 근거 확보 — 집계 숫자만 옮기지 말 것.
- 대조 축 2열: v29 공식(rp1.0 — 빈 골격 9/29 · 산출 5 · faults 2 · 1동작 ·
  coaching 1,392자 · 평균 18,733byte · FAIL) + v29@rp1.05
  (`aws s3 ls s3://sunity-motion-pilot-videos/training/phase22/ab_rp_260818/` 로
  기록 원문 확보 — 폭주 0 · 파싱실패 0 · 결함 0건 FAIL). v32@rp1.05 와
  v29@rp1.05 가 apples-to-apples.
- v29 FAIL 사유 4줄과 1:1 대조 — 어느 줄이 풀렸고 어느 줄이 남았는지.
- 판정 문장: "재료 2.2배 → faults 0→2" 탄성 관측(08-16)에 이어 이번 재료
  (admit 286)가 무엇을 움직였는지 한 줄. 다음 수는 belle 과 결정 (단독 처방 금지).

**공통 (SUMMARY 필수 항목)**:
- 게이트 판정 원문 (base/require_pass, 항목별)
- rp=1.05 본판정 사용 사실 + 근거 (08-18 결정, 스크립트 주석 갱신 커밋)
- 가드 미발동 관측 (기대값 대조 — 어긋났으면 그 원문)
- VRAM 공유 관측 (서버 상주분, vLLM 기동 시 사용량, OOM 조정 여부)
- Gemini 회수 (기대 0) + **LLM 학습 영향: 0** (게이트는 추론만 — 원장 1행 보고 관례)
- 프로덕션 무접촉 확인 (:8000 생존, SSM/Lambda env 무변경, S3 는 training/ 경로만)
- SUMMARY commit+push (.planning 파일 + ledger 변경분 있으면 함께).
  </action>
  <verify>
    <automated>test -f /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260821-umc-v32-gates-4090-580-pod-vllm-serve-v29-pr/260821-umc-SUMMARY.md && grep -c "require_pass" /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260821-umc-v32-gates-4090-580-pod-vllm-serve-v29-pr/260821-umc-SUMMARY.md</automated>
  </verify>
  <done>PASS 경로: promote 리포트 실물 열람 + ledger push 확인. FAIL 경로: v29(rp1.0/rp1.05) 대비 항목별 성적표 + FAIL 사유 4줄 1:1 대조가 SUMMARY 에 있음. 공통 필수 항목 전부 기재, commit+push 완료.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 로컬 → Pod SSH | 키 인증(id_ed25519), 운영 커맨드만. 시크릿은 env 이름만 로그, 값 echo 금지 (T-22-22 관례) |
| 게이트 vLLM serve | 127.0.0.1:8100 바인딩 유지 — 외부 노출 금지 (스크립트 기본값, 로그로 확인) |
| Pod → S3 | training/ prefix 읽기 + 로그·ledger 쓰기만. 프로덕션(uploads/, SSM, Lambda env) 무접촉 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-umc-01 | Tampering | promotion 래칫 | mitigate | gates 는 canonical 러너 경유만 (cycle_gate_exit.txt + 선언값 교차검증 fail-closed). ledger 수기 수정 금지 |
| T-umc-02 | Denial of Service | :8000 추론 서버 (앱 분석) | mitigate | GATES_PORT=8100 강제 + 게이트 전후 /health 확인 + VRAM OOM 시 조정 1회 후 STOP |
| T-umc-03 | Information Disclosure | vLLM 게이트 서버 | mitigate | 127.0.0.1 바인딩 확인 (proxy 노출 경로 없음) |
| T-umc-SC | Tampering | ab_venv_cu129 pip 설치 (조건부) | mitigate | 볼륨 내 기존 venv 에 이미 있는 패키지·동일 버전 재사용만. 신규 패키지 필요 시 STOP (설치 강행 금지). torch/vllm/triton 재설치 금지 |
</threat_model>

<verification>
- `grep -c GATES_GPU_UTIL backend/training/sft/run_sft_gates.sh` ≥ 1, `bash -n` 통과, 기본값 0.90 무회귀
- Pod 게이트 로그에 `GATES ALLDONE (base=X require_pass=Y)` 존재 + `cycle_gate_exit.txt` 와 일치 (fail-closed 교차검증 통과)
- 병합본 `checkpoint-68-merged` du 실측 ≈ 16~17GB
- :8000 `/health` — 게이트 전/후 모두 200
- Gemini 매치 0 (`grep -ci gemini` 게이트 로그)
- SUMMARY 에 판정 원문 + (promote 결과 또는 v29 대비 성적표) + 가드/VRAM/LLM 학습 영향 0 기재
</verification>

<success_criteria>
- v32 가 D-15 게이트에서 완주 판정을 받았다 (PASS/FAIL 무관 — 완주 + 기록이 완료 조건)
- PASS 시: promote 실행됨, ledger 전진 commit+push, 리포트 JSON 실물 열람
- FAIL 시: promote 미실행, v29(rp1.0 공식 + rp1.05 A/B) 대비 항목별 성적표와 FAIL 사유 4줄 1:1 대조가 SUMMARY 에 박제됨
- 프로덕션 무접촉 (:8000 생존, SSM/Lambda 무변경), Gemini 0, LLM 학습 영향 0 보고
</success_criteria>

<output>
완료 시 `.planning/quick/260821-umc-v32-gates-4090-580-pod-vllm-serve-v29-pr/260821-umc-SUMMARY.md` 작성
</output>
