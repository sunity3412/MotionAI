#!/usr/bin/env bash
# Phase 22-07 게이트 eval 러너 — SFT(AWQ) 모델로 D-15 게이트 artifact 생성 + 판정.
#
# 수순 (SERIAL — pipeline-not-concurrency-safe):
#   1. vLLM serve (AWQ, 127.0.0.1 — 외부 노출 금지)
#   2. run_bakeoff run1/run2 — 게이트 입력 artifact. --skip-judge (게이트는 coaching
#      축을 소비하지 않음 — Gemini 과금 0)
#   3. assert_gates 기본 모드 판정 → 이어서 --require-pass 판정 (둘 다 로그 기록)
#
# 스코프 정직성: 하네스 직접 추론(오프라인) — 파이프라인 swap 아님(Wave 3 전).
# 프롬프트 양식 (quick-260714-hv4 — 구 SUMMARY caveat "학습 입력 양식과는 다름" 해소):
#   · PROMPT_MODE=legacy (기본): 기존 하네스 양식(system+guided+프레임 image_url) —
#     기존 호출 동작 불변.
#   · PROMPT_MODE=aligned: 학습 JSONL user 양식과 문자 동일(지시문/시스템/디코딩 정렬)
#     + vLLM video_url 서빙(--allowed-local-media-path). v4 게이트 재계측은 aligned.
#   · REPETITION_PENALTY (기본 1.0 무회귀): 2026-08-18 A/B 실측 이후 **본판정도 1.05
#     사용** — 호출자가 env 로 지정한다. 근거: rp 1.0→1.05 에서 폭주 5/37→0,
#     파싱실패 11/29→0, 게이트 판정 불변 (원장
#     s3://sunity-motion-pilot-videos/training/phase22/ab_rp_260818/).
#     run1/run2 둘 다 동일 적용(determinism 비교는 동일 조건 cold 2회여야 유효).
#
# 사용 (Pod):
#   cd /workspace/SunityMotion/backend
#   PROMPT_MODE=aligned nohup bash training/sft/run_sft_gates.sh \
#     /workspace/phase22_export/sft-run1/awq > /workspace/sft_gates.log 2>&1 &

set -euo pipefail

AWQ="${1:?AWQ 모델 디렉토리 필수}"
VENV="${TRAIN_VENV:-/workspace/train_venv}"
export PATH="$VENV/bin:$PATH"   # vLLM EngineCore ninja 탐색 (bake-off 실증).
# ★포트는 덮어쓸 수 있어야 한다 (2026-08-18). 8000 은 운영 추론 서버
# (runpod_inference/server.py)가 쓰는 포트다. 같은 Pod 에서 앱 분석을 돌리면서
# 게이트를 돌리면 vLLM 이 bind 에 실패하거나 앱 경로를 밟는다.
# 앱과 같이 쓰는 Pod 에서는 GATES_PORT=8100 처럼 반드시 다른 포트를 줄 것.
PORT="${GATES_PORT:-8000}"

# ★Blackwell(sm_120) + 구 드라이버 조합 함정 — 2026-08-18 실측으로 잡음.
# Triton 3.7 은 arch>=100(=Blackwell)이면 번들된 `ptxas-blackwell` 을 쓰는데 그 바이너리가
# **CUDA 13.1** 이다. 드라이버가 CUDA 12.x 면 13.1 이 만든 cubin 을 로드하지 못해
#   RuntimeError: Triton Error [CUDA]: device kernel image is invalid
# 로 죽는다. **모델을 다 올린 뒤 프로파일 forward 에서** 터져서 OOM 처럼 보이는 게 함정이다.
# (실측: 5090 + 드라이버 570.195.03(CUDA 12.8) + vllm 0.27.1+cu129 → 사망 →
#  12.8 ptxas 로 바꾸니 통과. 12.8 은 sm_120 을 지원한다.)
# 드라이버가 감당하는 CUDA major 가 ptxas-blackwell 보다 낮을 때만 갈아끼운다.
# ★compute_cap 조건 추가 (2026-08-21 실측, A100 80GB + 드라이버 550.127.05):
#   기존 조건은 "번들 ptxas-blackwell CUDA > 드라이버 CUDA"만 봐서, A100(sm_80,
#   드라이버 CUDA 12.4, triton 번들 ptxas 13.x)에서도 발화해 3종 우회(ptxas 교체 +
#   FlashInfer off + attn 백엔드 강제)를 A100 에 강제했다. 3종 우회는 전부
#   Blackwell(sm_100+) 전용 증상이다 — ptxas-blackwell 은 triton 이 arch>=100 에서만
#   쓰고, FA2 PTX 거부와 FlashInfer 아키 파서 문제도 sm_120 실측이다. 비-Blackwell
#   에 백엔드 강제는 불필요·유해 (run_retrain_cycle.sh 의 T-22-12-06 과 같은 정신).
#   cap 미검출이면 발화 안 함(보수적).
if [ -z "${TRITON_PTXAS_BLACKWELL_PATH:-}" ] && [ -x /usr/local/cuda/bin/ptxas ]; then
  _drv_cuda=$(nvidia-smi 2>/dev/null | sed -n 's/.*CUDA Version: *\([0-9]*\)\..*/\1/p' | head -1)
  _bw=$("$VENV"/lib/python3.*/site-packages/triton/backends/nvidia/bin/ptxas-blackwell --version 2>/dev/null \
        | sed -n 's/.*release \([0-9]*\)\..*/\1/p' | head -1)
  _cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -1 | tr -d ' ')
  _is_blackwell=0
  if [ -n "${_cap:-}" ] && awk "BEGIN { exit !($_cap >= 10) }"; then _is_blackwell=1; fi
  if [ "$_is_blackwell" = "1" ] && [ -n "$_drv_cuda" ] && [ -n "$_bw" ] && [ "$_bw" -gt "$_drv_cuda" ]; then
    export TRITON_PTXAS_BLACKWELL_PATH=/usr/local/cuda/bin/ptxas
    echo "[env] Triton ptxas-blackwell(CUDA $_bw) > 드라이버(CUDA $_drv_cuda) — /usr/local/cuda/bin/ptxas 로 대체"
    # 같은 뿌리에서 나온 벽이 둘 더 있다(2026-08-18 실측, 하나씩 벗겨서 확인):
    #  ② vLLM 번들 FlashAttention-2 는 sm_120 SASS 가 없어 PTX 로 떨어지는데 그 PTX 가
    #     CUDA 12.9 제라 12.8 드라이버가 거부한다
    #     → "CUDA error: the provided PTX was compiled with an unsupported toolchain"
    #     회피 = 미리 컴파일된 커널을 안 쓰는 백엔드로 (Triton 은 위에서 고쳤으므로 쓸 수 있다).
    #  ③ FlashInfer 샘플러가 JIT 빌드 전 아키텍처 검사에서 sm_120 을 못 읽고 거부한다
    #     → "FlashInfer requires GPUs with sm75 or higher"(오해를 부르는 문구)
    #     회피 = FlashInfer 샘플러를 끄고 PyTorch 샘플러로. 반복 페널티는 그대로 적용된다.
    export VLLM_USE_FLASHINFER_SAMPLER=0
    VLLM_COMPAT_ARGS=(--attention-backend TRITON_ATTN --mm-encoder-attn-backend TORCH_SDPA)
    echo "[env] 드라이버-툴체인 불일치 회피: FlashInfer 샘플러 off + attn=TRITON_ATTN / vit=TORCH_SDPA"
  fi
fi
# 불일치가 없으면 빈 배열 = 기존 동작 그대로.
VLLM_COMPAT_ARGS=("${VLLM_COMPAT_ARGS[@]:-}")
[ -z "${VLLM_COMPAT_ARGS[0]:-}" ] && VLLM_COMPAT_ARGS=()

export HF_HOME="${HF_HOME:-/workspace/hf_cache}" USE_HF=1
export EVAL_OUT_DIR="${EVAL_OUT_DIR:-/workspace/eval_out}"
export BAKEOFF_FIXTURES_DIR="${BAKEOFF_FIXTURES_DIR:-/workspace/bakeoff_fixtures}"
export BAKEOFF_COORDS_CACHE="${BAKEOFF_COORDS_CACHE:-/workspace/phase22_coords_cache}"
export BAKEOFF_VLLM_URL="http://127.0.0.1:${PORT}/v1"

# 프롬프트 양식/디코딩 배선 (quick-260714-hv4) — 기본 legacy = 기존 호출 불변.
PROMPT_MODE="${PROMPT_MODE:-legacy}"
REPETITION_PENALTY="${REPETITION_PENALTY:-1.0}"

# shellcheck disable=SC1091
[ -f /workspace/aws_env.sh ] && source /workspace/aws_env.sh

# 양자화 플래그 자동 판별 — config.json 에 quantization_config 가 있으면 AWQ 서빙,
# 없으면(병합 bf16) 무플래그. autoawq 가 qwen3_vl 미지원이라 게이트는 bf16 병합본으로도
# 돈다 (2026-07-12 — AWQ 는 llm-compressor 경로로 별도 재시도).
QUANT_ARGS=(--dtype bfloat16)
if grep -q '"quantization_config"' "$AWQ/config.json" 2>/dev/null; then
  QUANT_ARGS=(--quantization awq --dtype float16)
fi

# aligned 는 video_url(file://) 수용 서빙 — 허용 경로는 BAKEOFF_FIXTURES_DIR 단일
# 디렉토리 한정(T-hv4-02) + 127.0.0.1 바인딩 유지. vLLM 버전이 video_url 미지원이면
# 하네스 auto 폴백이 frames 로 처리하므로 안전. legacy 서빙 인자는 불변.
MM_ARGS=(--limit-mm-per-prompt '{"image": 64}')
if [ "$PROMPT_MODE" = "aligned" ]; then
  MM_ARGS=(--limit-mm-per-prompt '{"image": 64, "video": 1}'
           --allowed-local-media-path "$BAKEOFF_FIXTURES_DIR")
fi

echo "[1/3] vLLM serve (${QUANT_ARGS[*]}, prompt_mode=${PROMPT_MODE})"
# GATES_GPU_UTIL: 24GB Pod 에서 :8000 추론 서버와 VRAM 공유 시 OOM 1회 조정용 노브
# (2026-08-21). 기본 0.90 무회귀 — merge_and_quant.sh 쪽 0.90 은 별개(범위 밖).
nohup "$VENV/bin/python" -m vllm.entrypoints.openai.api_server \
  --model "$AWQ" --host 127.0.0.1 --port "$PORT" \
  "${QUANT_ARGS[@]}" \
  --max-model-len 32768 --gpu-memory-utilization "${GATES_GPU_UTIL:-0.90}" \
  "${MM_ARGS[@]}" "${VLLM_COMPAT_ARGS[@]}" > /workspace/sft_gates_vllm.log 2>&1 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT
deadline=$((SECONDS + 1200))
until curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; do
  if [ $SECONDS -ge $deadline ]; then echo "[중단] vLLM 기동 실패" >&2; exit 11; fi
  if ! kill -0 "$VLLM_PID" 2>/dev/null; then echo "[중단] vLLM 사망 — sft_gates_vllm.log" >&2; exit 11; fi
  sleep 10
done
echo "  serve UP"

echo "[2/3] 게이트 artifact — run_bakeoff run1/run2 (judge 생략, SERIAL, prompt_mode=${PROMPT_MODE})"
run_bakeoff() {
  (cd "$(dirname "$0")/../.." && \
    BAKEOFF_MODEL="$AWQ" \
    "$VENV/bin/python" evals/phase22/run_bakeoff.py \
      --model "$AWQ" --run-tag "$1" --skip-judge \
      --prompt-mode "$PROMPT_MODE" --repetition-penalty "$REPETITION_PENALTY")
}
run_bakeoff run1
run_bakeoff run2

kill "$VLLM_PID" 2>/dev/null || true
wait "$VLLM_PID" 2>/dev/null || true
trap - EXIT

echo "[3/3] assert_gates 판정"
cd "$(dirname "$0")/../.."
PYTHONPATH=shared/python:training:. "$VENV/bin/python" evals/phase22/assert_gates.py --model "$AWQ" || GATE_RC=$?
echo "기본 모드 exit=${GATE_RC:-0}"
PYTHONPATH=shared/python:training:. "$VENV/bin/python" evals/phase22/assert_gates.py --model "$AWQ" --require-pass || REQ_RC=$?
echo "require-pass 모드 exit=${REQ_RC:-0}"
echo "GATES ALLDONE (base=${GATE_RC:-0} require_pass=${REQ_RC:-0})"

# ★스크립트의 종료 코드 = require-pass 판정 (2026-08-15 실측 수리).
# 이 줄이 없으면 스크립트는 마지막 `echo` 의 성공(0)으로 끝난다. 호출자
# (run_retrain_cycle.sh gates)는 `$?` 를 게이트 판정으로 기록하고, promotion 은
# "require-pass exit 0 만 pass=True" 계약으로 그 값을 읽는다 — 즉 **게이트가
# FAIL 해도 PASS 로 승격**될 수 있었다. 단방향 래칫의 전제가 무너지는 자리다.
# 실측: 2026-08-15 v28 사이클에서 게이트가 base=1/require_pass=1 로 FAIL 했는데
# `게이트 exit=0` 이 기록됐다(승격을 막은 것은 무관한 promote 예외였을 뿐이다).
# 게이트가 완주해서 FAIL 한 것이 이번이 처음이라 여태 드러나지 않았다.
exit "${REQ_RC:-0}"
