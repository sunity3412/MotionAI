#!/bin/bash
# Complete RunPod bootstrap (2026-06-19) — supersedes /workspace/bootstrap_wave5.sh which was
# STALE (missing google-genai / cerebras-cloud-sdk / fastapi / uvicorn / pydantic — the Gemini
# recognizer + FastAPI server deps added after that script was written).
#
# Network Storage persists /workspace (repo + RTMW/YOLOX weights + aws_env.sh + start_server.sh);
# the container's pip packages reset on every new pod, so re-run this after each pod (re)create.
#
# Usage on a fresh pod:
#   git -C /workspace/SunityMotion pull   # or clone if /workspace empty
#   bash /workspace/SunityMotion/scripts/pod_bootstrap_full.sh
#   source /workspace/aws_env.sh && bash /workspace/start_server.sh
set -e
export AWS_DEFAULT_REGION=ap-northeast-2
echo "[1/4] apt deps"
apt-get update -qq 2>&1 | tail -1 || true
apt-get install -y -qq ffmpeg libgl1 libglib2.0-0 unzip 2>&1 | tail -1 || true
echo "[2/4] git pull"
cd /workspace/SunityMotion && git fetch origin main --quiet && git checkout main --quiet && git pull --ff-only --quiet && echo "  HEAD: $(git rev-parse --short HEAD)"
echo "[3/4] pip deps (ALL — incl gemini/cerebras/fastapi)"
python3 -m pip install -q --root-user-action=ignore "numpy>=1.26,<2" boto3 'imageio[pyav]' imageio-ffmpeg firebase-admin rtmlib==0.0.15 google-genai cerebras-cloud-sdk fastapi 'uvicorn[standard]' pydantic
python3 -m pip uninstall -y -q onnxruntime 2>/dev/null || true
python3 -m pip install -q --root-user-action=ignore onnxruntime-gpu==1.19.2
echo "[4/4] weights check (network storage should already have these; else re-download)"
if [ ! -s /workspace/rtmw_weights/rtmw-x-384.onnx ]; then
  mkdir -p /workspace/rtmw_weights
  aws s3 cp s3://sunity-motion-pilot-videos/_artifacts/rtmw-x-384_bukuroo_hf.onnx /workspace/rtmw_weights/rtmw-x-384.onnx --quiet \
    || curl -L --fail -o /workspace/rtmw_weights/rtmw-x-384.onnx https://huggingface.co/bukuroo/RTMW-ONNX/resolve/main/rtmw-x-384.onnx
fi
if [ ! -s /workspace/yolox_weights/yolox_m.onnx ]; then
  mkdir -p /workspace/yolox_weights
  curl -L --fail -o /workspace/yolox_weights/yolox_m.onnx https://huggingface.co/hr16/yolox-onnx/resolve/main/yolox_m.onnx
fi
ls -lh /workspace/rtmw_weights/rtmw-x-384.onnx /workspace/yolox_weights/yolox_m.onnx 2>/dev/null
echo "[done] next: source /workspace/aws_env.sh && bash /workspace/start_server.sh"
