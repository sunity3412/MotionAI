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
# 영상 디코드 백엔드 = decord 강제 (2026-07-12 실증: 신형 torchvision 은 read_video
# API 제거 → qwen_vl_utils 기본 백엔드가 전 영상 행 인코딩 실패). decord 도 일부
# 코덱에서 EAGAIN 으로 죽어 로컬라이즈가 전 영상을 h264 로 균일 재인코딩한다(아래).
export FORCE_QWENVL_VIDEO_READER=decord

# AWS 자격 (S3 다운로드). 값 echo 금지.
# shellcheck disable=SC1091
[ -f /workspace/aws_env.sh ] && source /workspace/aws_env.sh

mkdir -p "$DATA" "$DATA/videos" "$OUT"

echo "[1/3] 학습셋 동기화 + 로컬라이즈 (원본 불변, *_local.jsonl 생성)"
# train_venv python 사용 — imageio_ffmpeg(ffmpeg 바이너리 공급)가 이 venv 에 있음.
"$VENV/bin/python3" -u - "$DATA" <<'PYEOF'
import json, subprocess, sys
from pathlib import Path
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config as _BotoConfig
import imageio_ffmpeg

# MooseFS(Network Volume)에서 boto3 기본 멀티스레드 다운로드가 futex 데드락으로
# 무한 hang 한다(2026-07-15 실측: localize 가 한 영상에서 52분 정지, ffmpeg 자식
# 없이 python futex_wait). 단일 스레드 전송으로 회피 — 학습 전처리라 처리량보다
# 안정성 우선. -u(unbuffered)로 진행 로그도 실시간 flush.
_DL_CONFIG = TransferConfig(use_threads=False)

# 단일 스레드로도 S3 연결이 stall 하면 boto3 기본값(타임아웃 없음)이 do_poll 로
# 무한 대기한다(2026-07-15 실측: 한 영상에서 8.5분+ 정지). read/connect 타임아웃 +
# 재시도로 stall 을 끊고 자동 회복한다.
_S3_CFG = _BotoConfig(
    connect_timeout=15, read_timeout=60,
    retries={"max_attempts": 5, "mode": "standard"},
)

data_dir = Path(sys.argv[1])
bucket = "sunity-motion-pilot-videos"
s3 = boto3.client("s3", config=_S3_CFG)
prefix = "training/phase22/jsonl/"
for name in ("train.jsonl", "val.jsonl", "_meta.json"):
    dst = data_dir / name
    s3.download_file(bucket, prefix + name, str(dst), Config=_DL_CONFIG)
    print(f"  sync {name} {dst.stat().st_size}B")

meta = json.loads((data_dir / "_meta.json").read_text())
assert meta["validation_owner"] == "explicit_val_jsonl", meta["validation_owner"]

vid_root = data_dir / "videos"
norm_root = data_dir / "videos_norm"
uri_prefix = f"s3://{bucket}/"
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

def normalize(src: Path, key: str) -> Path:
    """전 영상 h264/yuv420p 균일 재인코딩 (멱등 — 결과물 존재 시 skip).

    decord 가 일부 수집 영상 코덱에서 EAGAIN 으로 죽는다(2026-07-12 진단: 85행 중
    21행). 백엔드별 예외를 쫓는 대신 입력을 균일화한다. 오디오 제거(-an) —
    학습 입력은 프레임뿐."""
    dst = (norm_root / key).with_suffix(".mp4")
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-an", str(dst)],
        check=True,
    )
    return dst

def localize(name: str) -> None:
    """s3 URI 로컬라이즈 + ms-swift 표준 형식 변환.

    원본 JSONL 은 content 타입이 행/롤마다 다르다(system=str, user=list[dict],
    assistant=dict) — HF datasets(Arrow) 라운드트립이 스키마를 뒤틀어 swift
    template.encode 가 TypeError 로 죽는다(2026-07-12 실증, step 0 사망 2회).
    변환 규칙 (homogeneous 스키마 = 전 content 문자열):
      · video part → "<video>" 태그 + top-level videos 리스트 (swift 표준)
      · assistant dict(리포트 객체) → json.dumps sort_keys (철칙 2 키 정렬 —
        모델이 배워야 할 출력 = 직렬화된 리포트 텍스트)
      · _track 등 사이드카 키 제거 (Arrow 스키마 최소화)
    """
    rows, n_media = [], 0
    for line in (data_dir / name).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        msgs, videos = [], []
        for msg in row.get("messages") or []:
            content = msg.get("content")
            if isinstance(content, list):
                texts = []
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    uri = part.get("video")
                    if isinstance(uri, str) and uri.startswith(uri_prefix):
                        key = uri[len(uri_prefix):]
                        local = vid_root / key
                        if not local.exists():
                            local.parent.mkdir(parents=True, exist_ok=True)
                            s3.download_file(bucket, key, str(local), Config=_DL_CONFIG)
                            print(f"  dl {key}", flush=True)
                        videos.append(str(normalize(local, key)))
                        texts.append("<video>")
                        n_media += 1
                    elif part.get("type") == "text":
                        texts.append(str(part.get("text") or ""))
                content = "\n".join(texts)
            elif isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False, sort_keys=True)
            msgs.append({"role": msg.get("role"), "content": content})
        out_row = {"messages": msgs}
        if videos:
            out_row["videos"] = videos
        rows.append(out_row)
    out = data_dir / name.replace(".jsonl", "_local.jsonl")
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"  localize {name}: rows={len(rows)} media_refs={n_media} -> {out.name}")

localize("train.jsonl")
localize("val.jsonl")
PYEOF

# ── GPU 용량 적응 노브 (quick-260814-l5i) ────────────────────────────────────
# 기본값은 22-07 검증값(A100급 전제)이다. 24GB(4090)에서는 그대로 안 들어간다 —
# 실측 2026-08-14: 추론 서버 내리고 expandable_segments 걸고 프레임 32→16 으로
# 줄여도 학습 단독 22.8GiB 로 OOM(첫 스텝, lora_B forward 에서 736MiB 할당 실패).
# 값을 코드에 박아두면 GPU 가 바뀔 때마다 스크립트를 고쳐야 하므로 env 로 뺀다.
# ★기본값을 낮추지 않는다 — 큰 GPU 에서의 검증 설정이 기본이고, 작은 GPU 가
#   명시적으로 낮춰 쓰는 구조여야 "왜 이 값인가"가 추적된다.
SFT_LORA_RANK="${SFT_LORA_RANK:-64}"
SFT_LORA_ALPHA="${SFT_LORA_ALPHA:-128}"
SFT_MAX_LENGTH="${SFT_MAX_LENGTH:-32768}"
SFT_FREEZE_VIT="${SFT_FREEZE_VIT:-false}"
# liger-kernel = 손실을 조각내 계산해 **전체 로짓 텐서를 안 만든다**.
# ★실측(2026-08-14, 5090 32GB): `logits.float()` 가 8.57GiB 를 한 번에 잡으려다 OOM.
#   로짓 크기 = 시퀀스 x 어휘(15만) 라 GPU 를 키우거나 시퀀스를 줄이는 것 말고는
#   답이 없어 보였는데(프레임 절반으로 줄여도 오히려 늘었다 — 길이를 지배하는 건
#   영상이 아니라 3만~5만 자 텍스트 타깃이었다), 이 커널이 그 스파이크 자체를 없앤다.
#   미설치 환경에서 켜면 swift 가 죽으므로 **설치 확인 후에만** 켠다.
SFT_USE_LIGER="${SFT_USE_LIGER:-auto}"
if [ "$SFT_USE_LIGER" = "auto" ]; then
  if "$VENV/bin/python" -c "import liger_kernel" >/dev/null 2>&1; then SFT_USE_LIGER=true; else SFT_USE_LIGER=false; fi
fi

echo "[2/3] swift sft (QLoRA rank${SFT_LORA_RANK} 4-bit, all-linear, ${SFT_MAX_LENGTH} tok, freeze_vit=${SFT_FREEZE_VIT}, liger=${SFT_USE_LIGER})"
"$VENV/bin/swift" sft \
  --model "$MODEL" \
  --dataset "$DATA/train_local.jsonl" \
  --val_dataset "$DATA/val_local.jsonl" \
  --split_dataset_ratio 0 \
  --tuner_type lora --lora_rank "$SFT_LORA_RANK" --lora_alpha "$SFT_LORA_ALPHA" \
  --target_modules all-linear \
  --freeze_vit "$SFT_FREEZE_VIT" \
  --quant_method bnb --quant_bits 4 --torch_dtype bfloat16 \
  --use_liger_kernel "$SFT_USE_LIGER" \
  --gradient_checkpointing true --optim paged_adamw_8bit \
  --packing false --max_length "$SFT_MAX_LENGTH" \
  --per_device_train_batch_size 1 --gradient_accumulation_steps 16 \
  --learning_rate 1e-5 --vit_lr 2e-6 --aligner_lr 1e-5 \
  --freeze_aligner false \
  --num_train_epochs 4 \
  --save_strategy epoch --eval_strategy epoch --logging_steps 1 \
  --output_dir "$OUT"

echo "[3/3] 완료 — 최신 체크포인트:"
ls -dt "$OUT"/*/checkpoint-* 2>/dev/null | head -3
echo "SFT ALLDONE"
