#!/usr/bin/env bash
# RunPod Pod 초기 셋업. PyTorch + CUDA 가 깔린 RunPod 베이스 이미지 위에서 1회 실행.
# 멱등 — 재실행해도 안전.
#
# 사용:
#   cd /workspace/SunityMotion/backend
#   bash runpod_inference/setup.sh
#
# 끝나면 다음으로:
#   cd /workspace/SunityMotion/backend
#   export RUNPOD_AUTH_TOKEN=...          # 아래 환경변수 섹션 참조
#   export AWS_ACCESS_KEY_ID=...
#   export AWS_SECRET_ACCESS_KEY=...
#   export AWS_DEFAULT_REGION=ap-northeast-2
#   export FIREBASE_SA_PATH=/workspace/firebase-sa.json
#   export CUDA_VISIBLE_DEVICES=0
#   uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$(cd "$HERE/.." && pwd)"
MODEL_PATH="$BACKEND/scripts/nlf_l_multi.torchscript"
NLF_URL="https://github.com/isarandi/nlf/releases/download/v0.3.2/nlf_l_multi_0.3.2.torchscript"

echo "[1/3] Python 의존성 설치"
pip install -q --upgrade pip
pip install -q -r "$HERE/requirements.txt"

echo "[2/3] NLF 모델 다운로드 (없으면)"
mkdir -p "$BACKEND/scripts"
if [ -s "$MODEL_PATH" ]; then
  echo "  이미 존재: $MODEL_PATH ($(du -h "$MODEL_PATH" | cut -f1))"
else
  echo "  curl $NLF_URL"
  curl -L --fail -o "$MODEL_PATH" "$NLF_URL"
  echo "  완료: $MODEL_PATH ($(du -h "$MODEL_PATH" | cut -f1))"
fi

echo "[3/3] CUDA 확인"
python - <<'PY'
import torch
print(f"  torch={torch.__version__}  CUDA={'available' if torch.cuda.is_available() else 'NOT AVAILABLE'}")
if torch.cuda.is_available():
    print(f"  device={torch.cuda.get_device_name(0)}")
PY

echo ""
echo "✔ 셋업 완료. 다음 명령으로 서버 기동:"
echo ""
echo "  cd $BACKEND"
echo "  export RUNPOD_AUTH_TOKEN=<생성>"
echo "  export AWS_ACCESS_KEY_ID=<...>"
echo "  export AWS_SECRET_ACCESS_KEY=<...>"
echo "  export AWS_DEFAULT_REGION=ap-northeast-2"
echo "  export FIREBASE_SA_PATH=/workspace/firebase-sa.json"
echo "  export CUDA_VISIBLE_DEVICES=0"
echo "  uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1"
