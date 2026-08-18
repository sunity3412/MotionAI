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
#   · REPETITION_PENALTY (기본 1.0): rp A/B 관찰 전용 — 본판정은 1.0 고정.
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
nohup "$VENV/bin/python" -m vllm.entrypoints.openai.api_server \
  --model "$AWQ" --host 127.0.0.1 --port "$PORT" \
  "${QUANT_ARGS[@]}" \
  --max-model-len 32768 --gpu-memory-utilization 0.90 \
  "${MM_ARGS[@]}" > /workspace/sft_gates_vllm.log 2>&1 &
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
