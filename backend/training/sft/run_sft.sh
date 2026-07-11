#!/usr/bin/env bash
# Phase 22-07 SFT 러너 — bake-off 우승 백본 QLoRA 학습 (학습 Pod 전용, 밤샘 무인 실행).
#
# 백본 = Qwen/Qwen3-VL-8B-Instruct (22-BAKEOFF-RESULT PROVISIONAL, 2026-07-12).
# 학습셋 = s3://sunity-motion-pilot-videos/training/phase22/jsonl/ (train 101 / val 2,
#   manifest _meta.validation_owner=explicit_val_jsonl → val.jsonl 을 --val_dataset 으로
#   명시 소비하고 내부 재분할은 0 (--split_dataset_ratio 0). DR-04.)
# JSONL 의 video 참조는 정규 s3:// URI — 학습 전 로컬라이즈(다운로드+경로 재작성) 단계가
#   *_local.jsonl 을 만든다. 원본 JSONL 은 불변(T-22-20 학습셋 버전 고정).
#
# 인자명은 ms-swift 4.4.0 SftArguments 필드로 검증 완료 (A8, 2026-07-12):
#   --train_type(구 3.x) → --tuner_type 개명. vit_lr/aligner_lr/freeze_aligner/packing 존속.
#   QLoRA = --quant_method bnb --quant_bits 4 (기본 None — 명시 필수).
#
# 프레임 예산 (qwen_vl_utils env): FPS_MAX_FRAMES=32, VIDEO_MAX_PIXELS=448^2.
#   bake-off 실측: 64프레임x448 입력만 ~28~33K tok — assistant 타겟(리포트 JSON)까지
#   합치면 max_length 32768 초과. 32프레임이면 비주얼 ~8K tok 로 여유 확보.
#
# packing=false (RESEARCH 초기값에서 이탈, 2026-07-12 실측 근거): ms-swift 4.4 packing 은
#   flash-attn 필수인데 학습 Pod 에 미설치(T-22-SC 신규 pip 0 원칙). 샘플이 개당
#   ~20~30K tok 로 max_length 근접이라 32K 창에 1개만 들어가 packing 이득이 사실상 0 —
#   설치 비용/리스크 대비 실익 없음.
#
# Pod 실행 (nohup 무인):
#   cd /workspace/SunityMotion/backend
#   nohup bash training/sft/run_sft.sh > /workspace/sft_run1.log 2>&1 &
#
# 산출물: /workspace/phase22_sft_out/{run_id}/checkpoint-* (LoRA 어댑터) — 병합/양자화는
#   training/export/merge_and_quant.sh 가 담당 (4-bit 직접 병합 금지, Pitfall 1).
# 시크릿: env 참조만, 키 값 echo 금지 (T-22-22).

set -euo pipefail

MODEL="${SFT_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"
VENV="${TRAIN_VENV:-/workspace/train_venv}"
DATA=/workspace/phase22_sft
OUT=/workspace/phase22_sft_out
S3_JSONL=s3://sunity-motion-pilot-videos/training/phase22/jsonl

export HF_HOME="${HF_HOME:-/workspace/hf_cache}"
# ms-swift 기본 허브 = ModelScope — HF 캐시(bake-off 가 받아둔 가중치)를 재사용하려면
# USE_HF=1 필수 (미설정 시 같은 모델 17GB 를 ModelScope 에서 재다운로드, 2026-07-12 실증).
export USE_HF=1
export FPS_MAX_FRAMES="${FPS_MAX_FRAMES:-32}"
export VIDEO_MAX_PIXELS="${VIDEO_MAX_PIXELS:-200704}"

# AWS 자격 (S3 다운로드). 값 echo 금지.
# shellcheck disable=SC1091
[ -f /workspace/aws_env.sh ] && source /workspace/aws_env.sh

mkdir -p "$DATA" "$DATA/videos" "$OUT"

echo "[1/3] 학습셋 동기화 + 로컬라이즈 (원본 불변, *_local.jsonl 생성)"
python3 - "$DATA" <<'PYEOF'
import json, sys
from pathlib import Path
import boto3

data_dir = Path(sys.argv[1])
bucket = "sunity-motion-pilot-videos"
s3 = boto3.client("s3")
prefix = "training/phase22/jsonl/"
for name in ("train.jsonl", "val.jsonl", "_meta.json"):
    dst = data_dir / name
    s3.download_file(bucket, prefix + name, str(dst))
    print(f"  sync {name} {dst.stat().st_size}B")

meta = json.loads((data_dir / "_meta.json").read_text())
assert meta["validation_owner"] == "explicit_val_jsonl", meta["validation_owner"]

vid_root = data_dir / "videos"
uri_prefix = f"s3://{bucket}/"

def localize(name: str) -> None:
    rows, n_media = [], 0
    for line in (data_dir / name).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        for msg in row.get("messages") or []:
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                uri = part.get("video") if isinstance(part, dict) else None
                if not (isinstance(uri, str) and uri.startswith(uri_prefix)):
                    continue
                key = uri[len(uri_prefix):]
                local = vid_root / key
                if not local.exists():
                    local.parent.mkdir(parents=True, exist_ok=True)
                    s3.download_file(bucket, key, str(local))
                part["video"] = str(local)
                n_media += 1
        rows.append(row)
    out = data_dir / name.replace(".jsonl", "_local.jsonl")
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"  localize {name}: rows={len(rows)} media_refs={n_media} -> {out.name}")

localize("train.jsonl")
localize("val.jsonl")
PYEOF

echo "[2/3] swift sft (QLoRA rank64 4-bit, all-linear, packing, 32K)"
"$VENV/bin/swift" sft \
  --model "$MODEL" \
  --dataset "$DATA/train_local.jsonl" \
  --val_dataset "$DATA/val_local.jsonl" \
  --split_dataset_ratio 0 \
  --tuner_type lora --lora_rank 64 --lora_alpha 128 \
  --target_modules all-linear \
  --quant_method bnb --quant_bits 4 --torch_dtype bfloat16 \
  --gradient_checkpointing true --optim paged_adamw_8bit \
  --packing false --max_length 32768 \
  --per_device_train_batch_size 1 --gradient_accumulation_steps 16 \
  --learning_rate 1e-5 --vit_lr 2e-6 --aligner_lr 1e-5 \
  --freeze_aligner false \
  --num_train_epochs 4 \
  --save_strategy epoch --eval_strategy epoch --logging_steps 1 \
  --output_dir "$OUT"

echo "[3/3] 완료 — 최신 체크포인트:"
ls -dt "$OUT"/*/checkpoint-* 2>/dev/null | head -3
echo "SFT ALLDONE"
