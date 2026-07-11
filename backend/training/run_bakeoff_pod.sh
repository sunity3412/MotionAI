#!/usr/bin/env bash
# Phase 22-06 bake-off SERIAL 러너 (학습 Pod 전용, 밤샘 무인 실행).
#
# 후보 3종(belle 2026-07-10 3파전)을 한 번에 하나씩:
#   vLLM serve(127.0.0.1 — 외부 노출 금지, T-22-19) → run_bakeoff run1(judge 포함)
#   → cold re-run run2/run3(judge 생략 — 결정성 비교 전용, 과금 0) → serve 종료.
# 실패 시 다음 모델로 넘어가지 않고 원인 보존 후 정지 (belle 지시 2026-07-11).
#
# 선행: setup_training_pod.sh 완료 (모델 3종 + venv + fixtures prefetch).
# 사용:
#   cd /workspace/SunityMotion/backend
#   nohup bash training/run_bakeoff_pod.sh > /workspace/bakeoff_run.log 2>&1 &
#
# 산출물: $EVAL_OUT_DIR/phase22/bakeoff_{model}_{run1..3}.json (repo 밖)
#         + determinism_summary.json + 로그 /workspace/bakeoff_logs/.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$(cd "$HERE/.." && pwd)"

VENV="${TRAIN_VENV:-/workspace/train_venv}"
# vLLM EngineCore 는 ninja 등 빌드 도구를 subprocess PATH 로 찾는다 — venv 미활성
# 직접 호출이므로 PATH 선주입 필수 (2026-07-11 ninja FileNotFoundError 2회 실증).
export PATH="$VENV/bin:$PATH"
LOGDIR="${BAKEOFF_LOGDIR:-/workspace/bakeoff_logs}"
PORT=8000

export HF_HOME="${HF_HOME:-/workspace/hf_cache}"
export EVAL_OUT_DIR="${EVAL_OUT_DIR:-/workspace/eval_out}"
export BAKEOFF_FIXTURES_DIR="${BAKEOFF_FIXTURES_DIR:-/workspace/bakeoff_fixtures}"
export BAKEOFF_COORDS_CACHE="${BAKEOFF_COORDS_CACHE:-/workspace/phase22_coords_cache}"
export BAKEOFF_VLLM_URL="http://127.0.0.1:${PORT}/v1"

# 후보 모델 ID — setup_training_pod.sh 박제 상수와 동일해야 한다 (A6 확정 ID).
MODELS=(
  "Qwen/Qwen3-VL-8B-Instruct"
  "OpenGVLab/InternVL3_5-8B"
  "nvidia/Cosmos-Reason2-8B"
)

mkdir -p "$LOGDIR"

# AWS 자격 (SSM Gemini 키 fetch + boto3). 값 echo 금지 (T-22-18).
# shellcheck disable=SC1091
[ -f /workspace/aws_env.sh ] && source /workspace/aws_env.sh

echo "[0/3] Gemini judge 키 주입 (SSM /sunity/motion/gemini-api-key — 값 비출력)"
GEMINI_API_KEY="$(python3 - <<'PYEOF'
import boto3
print(boto3.client("ssm", region_name="ap-northeast-2").get_parameter(
    Name="/sunity/motion/gemini-api-key", WithDecryption=True)["Parameter"]["Value"].strip())
PYEOF
)"
export GEMINI_API_KEY
echo "  키 길이: ${#GEMINI_API_KEY}"

echo "[1/3] venv 실행부 의존 (idempotent — openai/google-genai/imageio/pillow)"
"$VENV/bin/pip" install -q "openai>=1.40,<3" "google-genai>=1.0,<2" \
  "imageio>=2.34" "imageio-ffmpeg>=0.5.1" "pillow>=10"

echo "[2/3] eval 미니셋 RTMW 좌표 사전 추출 (system python — 서빙 스택, Gemini 무접촉)"
(cd "$BACKEND" && \
  LD_LIBRARY_PATH=/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/dist-packages/nvidia/cublas/lib \
  RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx \
  YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx \
  RTMW_DEVICE=cuda \
  PYTHONPATH=shared/python:training:. \
  python3 evals/phase22/extract_eval_coords.py 2>&1 | tee "$LOGDIR/extract_coords.log") || {
    echo "[중단] 좌표 사전 추출 실패/누락 — $LOGDIR/extract_coords.log 확인" >&2
    exit 10
  }

wait_health() {
  # vLLM /v1/models 응답 대기 (모델 로드 수 분 — 최대 20분).
  local deadline=$((SECONDS + 1200))
  until curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; do
    if [ $SECONDS -ge $deadline ]; then return 1; fi
    if ! kill -0 "$1" 2>/dev/null; then return 2; fi  # serve 프로세스 사망.
    sleep 10
  done
  return 0
}

wait_gpu_free() {
  # serve 종료 후 VRAM 해제 대기 (다음 모델 OOM 방지).
  local deadline=$((SECONDS + 300))
  while [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)" -gt 2000 ]; do
    if [ $SECONDS -ge $deadline ]; then
      echo "  [경고] VRAM 미해제 (5분 초과) — 계속 진행" >&2
      break
    fi
    sleep 10
  done
}

# HF 토큰 주입 — Cosmos-Reason2 는 gated repo 라 vLLM 의 허브 파일 조회가 무인증이면
# 401 GatedRepoError 로 즉사한다 (2026-07-11 실증). 값 echo 금지 (T-22-18).
HF_TOKEN="$(python3 - <<'PYEOF'
import boto3
print(boto3.client("ssm", region_name="ap-northeast-2").get_parameter(
    Name="/sunity/motion/hf-token", WithDecryption=True)["Parameter"]["Value"])
PYEOF
)"
export HF_TOKEN HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
echo "HF_TOKEN len: ${#HF_TOKEN}"

echo "[3/3] bake-off SERIAL (모델당 run1+judge → run2/run3 cold re-run)"
for MODEL in "${MODELS[@]}"; do
  SLUG="${MODEL//\//_}"
  # 재개(resume): run3 리포트가 이미 있으면 완주한 모델 — 재계측·재과금 금지.
  if [ -f "$EVAL_OUT_DIR/phase22/bakeoff_${MODEL//\//_}_run3.json" ]; then
    echo "── $MODEL skip(완주 리포트 존재)"
    continue
  fi
  echo "── $MODEL"
  EXTRA_ARGS=()
  case "$MODEL" in
    OpenGVLab/*) EXTRA_ARGS+=(--trust-remote-code) ;;  # InternVLChatModel 커스텀 코드.
  esac

  nohup "$VENV/bin/python" -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" --host 127.0.0.1 --port "$PORT" \
    --dtype bfloat16 --limit-mm-per-prompt '{"image": 64}' \
    --max-model-len 32768 --gpu-memory-utilization 0.90 \
    "${EXTRA_ARGS[@]}" > "$LOGDIR/vllm_${SLUG}.log" 2>&1 &
  VLLM_PID=$!
  echo "  vllm serve pid=$VLLM_PID (log: $LOGDIR/vllm_${SLUG}.log)"

  if ! wait_health "$VLLM_PID"; then
    echo "[중단] vLLM 기동 실패: $MODEL — $LOGDIR/vllm_${SLUG}.log 보존" >&2
    kill "$VLLM_PID" 2>/dev/null || true
    exit 11
  fi
  echo "  serve UP — run1 (zero+few, judge 포함)"

  run_bakeoff() {
    # $1=run-tag  $2=extra flag("--skip-judge" 또는 "")
    (cd "$BACKEND" && \
      BAKEOFF_MODEL="$MODEL" \
      "$VENV/bin/python" evals/phase22/run_bakeoff.py \
        --model "$MODEL" --run-tag "$1" ${2:-} \
        2>&1 | tee "$LOGDIR/bakeoff_${SLUG}_$1.log")
  }

  if ! run_bakeoff run1 ""; then
    echo "[중단] run1 실패: $MODEL (quota/오류) — 로그 보존, serve 종료" >&2
    kill "$VLLM_PID" 2>/dev/null || true
    exit 12
  fi
  echo "  cold re-run run2/run3 (judge 생략 — 결정성 비교)"
  run_bakeoff run2 "--skip-judge" || { kill "$VLLM_PID" 2>/dev/null || true; exit 13; }
  run_bakeoff run3 "--skip-judge" || { kill "$VLLM_PID" 2>/dev/null || true; exit 13; }

  kill "$VLLM_PID" 2>/dev/null || true
  wait "$VLLM_PID" 2>/dev/null || true
  wait_gpu_free
  echo "  $MODEL 완료 — serve 종료/VRAM 해제"
done

echo "[후처리] cold re-run 결정성 비교 (raw_sha 항목별 일치)"
"$VENV/bin/python" - <<'PYEOF'
import json, os
from pathlib import Path

out = Path(os.environ["EVAL_OUT_DIR"]).expanduser() / "phase22"
models = ["Qwen/Qwen3-VL-8B-Instruct", "OpenGVLab/InternVL3_5-8B", "nvidia/Cosmos-Reason2-8B"]
summary = {}
for m in models:
    slug = m.replace("/", "_")
    runs = {}
    for tag in ("run1", "run2", "run3"):
        p = out / f"bakeoff_{slug}_{tag}.json"
        if not p.exists():
            continue
        rep = json.loads(p.read_text(encoding="utf-8"))
        runs[tag] = {
            f"{r.get('id')}|{r.get('mode')}": r.get("raw_sha")
            for r in rep.get("records", []) if r.get("raw_sha")
        }
    tags = sorted(runs)
    det = {"runs_found": tags}
    if len(tags) >= 2:
        keys = set().union(*(runs[t].keys() for t in tags))
        matched = sum(1 for k in keys if len({runs[t].get(k) for t in tags}) == 1)
        det.update(items=len(keys), identical=matched,
                   deterministic=(matched == len(keys)))
    summary[m] = det
p = out / "determinism_summary.json"
p.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
print(f"wrote {p}")
PYEOF

echo "BAKEOFF ALLDONE"
