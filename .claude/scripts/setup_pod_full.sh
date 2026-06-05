#!/bin/bash
# Phase 5 Wave 4 Task 2 — Pod 환경 자동 재설치 + Gemini wiring + sweep 박제
#
# 사용법 (belle 새 Pod SSH 들어와서 한 줄):
#   export AWS_ACCESS_KEY_ID="<sunity-motion 키>"
#   export AWS_SECRET_ACCESS_KEY="<sunity-motion 시크릿>"
#   cd /workspace && git clone https://github.com/sunity3412/MotionAI.git SunityMotion && \
#     bash SunityMotion/.claude/scripts/setup_pod_full.sh
#
# 자동 처리:
#   1. apt deps (ffmpeg + libgl1 + libglib2 + unzip)
#   2. Python deps (mmpose stack + boto3 + google-genai + firebase-admin + imageio)
#   3. RTMW weights 다운로드 + unzip
#   4. .bashrc 영구 박제 (PATHs, AWS region, RECOGNIZER_BACKEND)
#   5. Gemini API 호출 검증
#   6. 5영상 sweep 백그라운드 실행

set -e

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "ERROR: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 미설정"
  echo ""
  echo "사용법:"
  echo "  export AWS_ACCESS_KEY_ID=<키>"
  echo "  export AWS_SECRET_ACCESS_KEY=<시크릿>"
  echo "  bash $0"
  exit 1
fi

export AWS_DEFAULT_REGION=ap-northeast-2
export RECOGNIZER_BACKEND=gemini
export RTMW_ONNX_PATH=/workspace/rtmw_weights/20230928/rtmpose_onnx/rtmw-x_simcc-cocktail13_pt-ucoco_270e-384x288-0949e3a9_20230925/end2end.onnx

echo "=== [1/8] apt deps (ffmpeg / libgl / unzip) ==="
apt-get update -qq 2>&1 | tail -2
apt-get install -y -qq ffmpeg libgl1 libglib2.0-0 unzip 2>&1 | tail -3

echo "=== [2/8] numpy 다운그레이드 (mmpose 1.x ABI) ==="
pip install -q "numpy>=1.26,<2"

echo "=== [3/8] mmcv (no-build-isolation 함정) ==="
pip install -q --no-build-isolation "mmcv>=2.0,<2.2"

echo "=== [4/8] mmpose stack + chumpy ==="
pip install -q --no-build-isolation chumpy
pip install -q rtmlib==0.0.15 mmpose==1.3.2 mmengine==0.10.7 mmdet==3.3.0 xtcocotools==1.14.3

echo "=== [5/8] python deps (boto3 / imageio / google-genai / firebase-admin / onnxruntime-gpu) ==="
pip install -q boto3 'imageio[pyav]' imageio-ffmpeg firebase-admin google-genai
# 박제 함정 (2026-06-05): rtmlib 디폴트 의존성에 onnxruntime (CPU) 만 포함 → CUDA EP 미활성 → 영상당 30분+ CPU inference.
# onnxruntime 제거 + onnxruntime-gpu 명시 install 필수.
pip uninstall -y -q onnxruntime 2>/dev/null || true
pip install -q onnxruntime-gpu

echo "=== [6/8] RTMW weights 다운로드 ==="
mkdir -p /workspace/rtmw_weights
cd /workspace/rtmw_weights
if [ ! -f "20230928/rtmpose_onnx/rtmw-x_simcc-cocktail13_pt-ucoco_270e-384x288-0949e3a9_20230925/end2end.onnx" ]; then
  curl -L --fail -o rtmw_onnx.zip "https://download.openmmlab.com/mmpose/v1/projects/rtmw/onnx_sdk/rtmw-x_simcc-cocktail13_pt-ucoco_270e-384x288-0949e3a9_20230925.zip" 2>&1 | tail -2
  unzip -q -o rtmw_onnx.zip
  rm -f rtmw_onnx.zip
fi
find /workspace/rtmw_weights -name "end2end.onnx" | head -1

echo "=== [7/8] .bashrc 영구 박제 (다음 SSH 세션 자동 적용) ==="
cat >> /root/.bashrc << 'BRC'

# Phase 5 Wave 4 — Pod 환경 박제 (setup_pod_full.sh 박제)
export AWS_DEFAULT_REGION=ap-northeast-2
export RECOGNIZER_BACKEND=gemini
export RTMW_ONNX_PATH=/workspace/rtmw_weights/20230928/rtmpose_onnx/rtmw-x_simcc-cocktail13_pt-ucoco_270e-384x288-0949e3a9_20230925/end2end.onnx
export PYTHONPATH=/workspace/SunityMotion/backend/shared/python:.
export RTMW_DEVICE=cuda  # 박제 함정 (2026-06-05): cpu 디폴트 → GPU 0% → 영상당 30분+. cuda 강제.

# GEMINI_API_KEY = SSM fetch 매번 (보안상 .bashrc 박제 X)
# AWS_KEY = belle 가 매 세션 export 또는 RunPod 콘솔 Env 박제
# 매 세션:
#   export AWS_ACCESS_KEY_ID=...
#   export AWS_SECRET_ACCESS_KEY=...
#   export GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key --with-decryption --query Parameter.Value --output text)
BRC

echo "=== [8/8] Gemini API 호출 검증 + sweep wrapper 박제 ==="
export GEMINI_API_KEY=$(python3 -c "
import boto3
ssm = boto3.client('ssm', region_name='ap-northeast-2')
r = ssm.get_parameter(Name='/sunity/motion/gemini-api-key', WithDecryption=True)
print(r['Parameter']['Value'])
")
python3 -c "
import os
from google import genai
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
resp = client.models.generate_content(model='gemini-3.1-pro-preview', contents=['Hello, respond with just OK.'])
print('Gemini hello world:', resp.text[:30])
"

# sweep wrapper 박제
cp /workspace/SunityMotion/.claude/scripts/run_sweep_gemini.sh /workspace/run_sweep_gemini.sh 2>/dev/null || cat > /workspace/run_sweep_gemini.sh << 'SH'
#!/bin/bash
set -e
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then echo "AWS 키 미설정"; exit 1; fi
export AWS_DEFAULT_REGION=ap-northeast-2
export RECOGNIZER_BACKEND=gemini
export RTMW_ONNX_PATH=/workspace/rtmw_weights/20230928/rtmpose_onnx/rtmw-x_simcc-cocktail13_pt-ucoco_270e-384x288-0949e3a9_20230925/end2end.onnx
export GEMINI_API_KEY=$(python3 -c "
import boto3
ssm = boto3.client('ssm', region_name='ap-northeast-2')
r = ssm.get_parameter(Name='/sunity/motion/gemini-api-key', WithDecryption=True)
print(r['Parameter']['Value'])
")
echo "GEMINI_API_KEY length: ${#GEMINI_API_KEY}"
cd /workspace/SunityMotion/backend
export PYTHONPATH=shared/python:.
echo "=== 5영상 sweep --recognizer gemini 백그라운드 ==="
nohup python3 -m research.evaluations.compare_rtmw_vs_ipsf \
  --recognizer gemini \
  --videos s3://sunity-motion-pilot-videos/reference/ref-climb.mp4 \
           s3://sunity-motion-pilot-videos/reference/ref-foxtop.mp4 \
           s3://sunity-motion-pilot-videos/reference/ref-foxtop-split.mp4 \
           s3://sunity-motion-pilot-videos/reference/ref-invert.mp4 \
           s3://sunity-motion-pilot-videos/reference/ref-sideway-spin.mp4 \
  --output-dir research/evaluations/reports/sweep_rtmw_gemini/ \
  > /tmp/sweep_gemini.log 2>&1 &
echo "sweep PID: $!"
SH
chmod +x /workspace/run_sweep_gemini.sh

echo ""
echo "=========================================="
echo "✅ Pod 환경 박제 완료 + Gemini 검증 PASS"
echo "=========================================="
echo ""
echo "다음 명령으로 5영상 sweep 백그라운드 시작:"
echo "  bash /workspace/run_sweep_gemini.sh"
echo ""
echo "예상 시간 = 약 50분. PID 확인 후 polling 가능."
