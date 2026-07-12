#!/usr/bin/env bash
# Phase 22-07 병합→양자화 파이프라인 (학습 Pod 전용).
#
# 수순 (Pitfall 1 — 4-bit 직접 병합 금지, 16-bit 경유가 유일 경로):
#   1. swift export --adapters <ckpt> --merge_lora true
#      → QLoRA 어댑터를 **16-bit(BF16) 원본 베이스**에 병합. ms-swift 는 어댑터의
#        base_model 을 HF 캐시의 bf16 원본으로 로드한다 — 4-bit 베이스에 직접 병합하는
#        경로는 이 스크립트에 존재하지 않는다(봉인).
#   2. swift export --model <merged> --quant_method awq --quant_bits 4
#      실패 시 폴백 순서(A2): awq → gptq → (수동) llm-compressor 안내 후 exit.
#   3. vLLM 로드 스모크 — AWQ 모델 serve + guided JSON 1건 추론 파싱 성공까지 확인.
#   4. S3 업로드: training/phase22/checkpoints/{run_id}/awq/ (비-notified prefix,
#      T-22-21 — sha256 기록).
#
# 인자명은 ms-swift 4.4.0 ExportArguments 필드로 검증 완료 (2026-07-12):
#   adapters/merge_lora/quant_method/quant_bits/output_dir/quant_n_samples/dataset 존속.
#
# 사용 (Pod):
#   cd /workspace/SunityMotion/backend
#   bash training/export/merge_and_quant.sh <adapter_ckpt_dir> <run_id>
#   예: bash training/export/merge_and_quant.sh \
#         /workspace/phase22_sft_out/v0-.../checkpoint-28 sft-run1
# 시크릿: env 참조만, 키 값 echo 금지 (T-22-22).

set -euo pipefail

CKPT="${1:?adapter checkpoint dir 필수}"
RUN_ID="${2:?run_id 필수 (예: sft-run1)}"
VENV="${TRAIN_VENV:-/workspace/train_venv}"
EXPORT_ROOT=/workspace/phase22_export/"$RUN_ID"
MERGED="$EXPORT_ROOT/merged_bf16"
AWQ_OUT="$EXPORT_ROOT/awq"
CALIB_JSONL="${CALIB_JSONL:-/workspace/phase22_sft/train_local.jsonl}"
S3_DST="s3://sunity-motion-pilot-videos/training/phase22/checkpoints/$RUN_ID/awq/"
PORT=8001

export HF_HOME="${HF_HOME:-/workspace/hf_cache}"
export USE_HF=1  # 병합 시 베이스 모델을 HF 캐시에서 — ModelScope 재다운로드 금지 (run_sft 실증).
# shellcheck disable=SC1091
[ -f /workspace/aws_env.sh ] && source /workspace/aws_env.sh

mkdir -p "$EXPORT_ROOT"

echo "[1/4] 16-bit 병합 (merge_lora true — 4-bit 직접 병합 경로 없음)"
"$VENV/bin/swift" export \
  --adapters "$CKPT" \
  --merge_lora true \
  --output_dir "$MERGED"

echo "[2/4] AWQ 4-bit 재양자화 (폴백: awq→gptq→llm-compressor 수동)"
quant() {
  "$VENV/bin/swift" export \
    --model "$MERGED" \
    --quant_method "$1" --quant_bits 4 \
    --dataset "$CALIB_JSONL" --quant_n_samples 64 \
    --output_dir "$AWQ_OUT"
}
if ! quant awq; then
  echo "  [폴백] awq 실패 → gptq 시도" >&2
  rm -rf "$AWQ_OUT"
  if ! quant gptq; then
    echo "[중단] awq/gptq 모두 실패 — llm-compressor 수동 경로 필요 (A2). 로그 보존." >&2
    exit 20
  fi
fi

echo "[3/4] vLLM 로드 스모크 (guided JSON 1건 추론)"
nohup "$VENV/bin/python" -m vllm.entrypoints.openai.api_server \
  --model "$AWQ_OUT" --host 127.0.0.1 --port "$PORT" \
  --quantization awq --dtype float16 \
  --max-model-len 32768 --gpu-memory-utilization 0.90 \
  --limit-mm-per-prompt '{"image": 64}' > "$EXPORT_ROOT/vllm_smoke.log" 2>&1 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT
deadline=$((SECONDS + 1200))
until curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; do
  if [ $SECONDS -ge $deadline ]; then echo "[중단] vLLM 기동 실패 — vllm_smoke.log 확인" >&2; exit 21; fi
  if ! kill -0 "$VLLM_PID" 2>/dev/null; then echo "[중단] vLLM 프로세스 사망 — vllm_smoke.log 확인" >&2; exit 21; fi
  sleep 10
done
SMOKE_MODEL="$AWQ_OUT" SMOKE_URL="http://127.0.0.1:${PORT}/v1" \
  "$VENV/bin/python" - <<'PYEOF'
import json, os, sys

sys.path.insert(0, "evals/phase22")
sys.path.insert(0, "training")
sys.path.insert(0, "shared/python")
from run_bakeoff import build_guided_json_schema, build_system_prompt, score_json
from distill.gemini_teacher import DEFAULT_TASK_JOINTS
from openai import OpenAI

client = OpenAI(base_url=os.environ["SMOKE_URL"], api_key="EMPTY", timeout=600.0)
msgs = [
    {"role": "system", "content": build_system_prompt(DEFAULT_TASK_JOINTS)},
    {"role": "user", "content": [{"type": "text", "text":
        '분석 대상 동작: 스모크 테스트.\nRTMW_Data: [{"frame": 0, "left_knee": [500, 500, 0.9]}]\n'
        "위 좌표만으로 D-01 통합 리포트 JSON 을 출력하라."}]},
]
resp = client.chat.completions.create(
    model=os.environ["SMOKE_MODEL"], messages=msgs, temperature=0.0,
    response_format=build_guided_json_schema())
raw = resp.choices[0].message.content or ""
parsed = json.loads(raw)
metrics = score_json(parsed)
print("smoke raw head:", raw[:200].replace("\n", " "))
print("smoke json metrics:", metrics)
assert metrics["parse"] == 1.0, "AWQ 모델 guided JSON 파싱 실패"
print("SMOKE PASS")
PYEOF
kill "$VLLM_PID" 2>/dev/null || true
wait "$VLLM_PID" 2>/dev/null || true
trap - EXIT

echo "[4/4] S3 업로드 + sha256 기록 (T-22-21)"
( cd "$AWQ_OUT" && find . -type f -exec sha256sum {} \; > "$EXPORT_ROOT/awq_sha256.txt" )
python3 - "$AWQ_OUT" "$S3_DST" <<'PYEOF'
import sys
from pathlib import Path
import boto3

src, dst = Path(sys.argv[1]), sys.argv[2]
assert dst.startswith("s3://")
bucket, prefix = dst[5:].split("/", 1)
s3 = boto3.client("s3")
n = 0
for p in sorted(src.rglob("*")):
    if p.is_file():
        key = prefix + str(p.relative_to(src))
        s3.upload_file(str(p), bucket, key)
        n += 1
print(f"uploaded {n} files -> {dst}")
PYEOF
head -5 "$EXPORT_ROOT/awq_sha256.txt"
echo "MERGE_QUANT ALLDONE"
