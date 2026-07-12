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
# 학습은 <video> 태그(비디오 토큰), 이 eval 은 프레임 image_url 64장 — bake-off 와
# 동일 계측기라 백본 비교와 정합하지만 학습 입력 양식과는 다름(SUMMARY caveat).
#
# 사용 (Pod):
#   cd /workspace/SunityMotion/backend
#   nohup bash training/sft/run_sft_gates.sh /workspace/phase22_export/sft-run1/awq \
#     > /workspace/sft_gates.log 2>&1 &

set -euo pipefail

AWQ="${1:?AWQ 모델 디렉토리 필수}"
VENV="${TRAIN_VENV:-/workspace/train_venv}"
export PATH="$VENV/bin:$PATH"   # vLLM EngineCore ninja 탐색 (bake-off 실증).
PORT=8000

export HF_HOME="${HF_HOME:-/workspace/hf_cache}" USE_HF=1
export EVAL_OUT_DIR="${EVAL_OUT_DIR:-/workspace/eval_out}"
export BAKEOFF_FIXTURES_DIR="${BAKEOFF_FIXTURES_DIR:-/workspace/bakeoff_fixtures}"
export BAKEOFF_COORDS_CACHE="${BAKEOFF_COORDS_CACHE:-/workspace/phase22_coords_cache}"
export BAKEOFF_VLLM_URL="http://127.0.0.1:${PORT}/v1"

# shellcheck disable=SC1091
[ -f /workspace/aws_env.sh ] && source /workspace/aws_env.sh

# 양자화 플래그 자동 판별 — config.json 에 quantization_config 가 있으면 AWQ 서빙,
# 없으면(병합 bf16) 무플래그. autoawq 가 qwen3_vl 미지원이라 게이트는 bf16 병합본으로도
# 돈다 (2026-07-12 — AWQ 는 llm-compressor 경로로 별도 재시도).
QUANT_ARGS=(--dtype bfloat16)
if grep -q '"quantization_config"' "$AWQ/config.json" 2>/dev/null; then
  QUANT_ARGS=(--quantization awq --dtype float16)
fi

echo "[1/3] vLLM serve (${QUANT_ARGS[*]})"
nohup "$VENV/bin/python" -m vllm.entrypoints.openai.api_server \
  --model "$AWQ" --host 127.0.0.1 --port "$PORT" \
  "${QUANT_ARGS[@]}" \
  --max-model-len 32768 --gpu-memory-utilization 0.90 \
  --limit-mm-per-prompt '{"image": 64}' > /workspace/sft_gates_vllm.log 2>&1 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT
deadline=$((SECONDS + 1200))
until curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; do
  if [ $SECONDS -ge $deadline ]; then echo "[중단] vLLM 기동 실패" >&2; exit 11; fi
  if ! kill -0 "$VLLM_PID" 2>/dev/null; then echo "[중단] vLLM 사망 — sft_gates_vllm.log" >&2; exit 11; fi
  sleep 10
done
echo "  serve UP"

echo "[2/3] 게이트 artifact — run_bakeoff run1/run2 (judge 생략, SERIAL)"
run_bakeoff() {
  (cd "$(dirname "$0")/../.." && \
    BAKEOFF_MODEL="$AWQ" \
    "$VENV/bin/python" evals/phase22/run_bakeoff.py \
      --model "$AWQ" --run-tag "$1" --skip-judge)
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
