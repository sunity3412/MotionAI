#!/bin/bash
# SFT 학습 환경 셋업 — `/workspace/train_venv` 생성 (quick-260814-l5i).
#
# 왜 이 파일이 이제야 생기나: 22-07(QLoRA SFT)이 COMPLETE 로 표기돼 있었지만
# **학습 venv 가 만들어진 적이 없었다**. 2026-08-14 새 Pod 에서 run_sft.sh 가
# `/workspace/train_venv/bin/python3: No such file or directory` 로 즉사했고,
# /workspace 는 네트워크 볼륨이라 한 번이라도 만들었으면 남아 있었을 것이다
# → SFT 는 실제로 한 번도 돌지 않았다(promotion_ledger current=null 과 정합).
# 레시피가 어디에도 없어 재현이 불가능했던 것이 진짜 결함이다.
#
# 실행: bash backend/training/sft/setup_train_venv.sh
# 멱등: 이미 있으면 재설치하지 않는다(--force 로 재생성).

set -uo pipefail

VENV="${TRAIN_VENV:-/workspace/train_venv}"
HF_HOME="${HF_HOME:-/workspace/hf_cache}"
MODEL="${SFT_MODEL:-Qwen/Qwen3-VL-8B-Instruct}"
FORCE="${1:-}"

# ★`swift --version` 은 쓰지 않는다 — ms-swift 4.4 의 CLI 는 서브커맨드 라우터라
# `--version` 이 KeyError 트레이스백을 낸다(정상 설치인데 실패처럼 보임, 2026-08-14 실측).
# 버전 확인은 패키지 속성으로.
swift_ver() { "$VENV/bin/python" -c "import swift; print(swift.__version__)" 2>/dev/null; }

if [ -x "$VENV/bin/swift" ] && [ -n "$(swift_ver)" ] && [ "$FORCE" != "--force" ]; then
  echo "[setup] 이미 존재 — 스킵 ($VENV, ms-swift $(swift_ver)). 재생성은 --force"
  exit 0
fi

echo "[setup] 1/3 venv 생성 (--system-site-packages = 베이스 이미지의 CUDA torch 재사용)"
# torch 를 venv 안에 다시 받지 않는다 — 베이스 이미지 torch(cu124)가 이 Pod 의
# GPU 와 이미 맞춰져 있고, 재설치하면 CUDA 빌드가 어긋날 위험만 생긴다.
python3 -m venv --system-site-packages "$VENV" || exit 1

echo "[setup] 2/3 ms-swift + 학습 의존성"
# ms-swift 4.4.0 = run_sft.sh 의 인자명이 검증된 버전(A8, 2026-07-12). 상향 금지 —
# SftArguments 필드명이 버전마다 바뀌어 러너가 조용히 실패한다.
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q \
  "ms-swift==4.4.0" \
  "peft>=0.11" \
  "bitsandbytes>=0.43" \
  "accelerate>=0.30" \
  "transformers>=4.51" \
  "qwen-vl-utils" \
  "imageio-ffmpeg>=0.5.1" \
  "av" \
  || { echo "[setup] pip 실패" >&2; exit 2; }

echo "[setup] 3/3 백본 가중치 사전 다운로드 ($MODEL)"
# 학습 중 첫 스텝에서 받으면 실패 시 사이클 전체가 날아간다 — 셋업에서 미리 받는다.
HF_HOME="$HF_HOME" "$VENV/bin/python" - <<'PY' || echo "[setup] 가중치 사전받기 실패(학습 중 재시도됨)"
import os
from huggingface_hub import snapshot_download
mid = os.environ.get("SFT_MODEL", "Qwen/Qwen3-VL-8B-Instruct")
p = snapshot_download(mid, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])
print("[setup] 가중치:", p)
PY

echo "[setup] 완료 — ms-swift $(swift_ver) / venv $VENV"
