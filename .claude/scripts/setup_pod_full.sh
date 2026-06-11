#!/bin/bash
# Phase 5 Wave 4 Task 2 — Pod 환경 자동 재설치 + Gemini wiring + sweep 박제
#
# 사용법 (belle 새 Pod SSH 들어와서 한 줄):
#   export AWS_ACCESS_KEY_ID="<sunity-motion 키>"
#   export AWS_SECRET_ACCESS_KEY="<sunity-motion 시크릿>"
#   cd /workspace && git clone https://github.com/sunity3412/MotionAI.git SunityMotion && \
#     bash SunityMotion/.claude/scripts/setup_pod_full.sh
#
# 별도 (Gemini recognizer 사용 시 필수): firebase-sa.json 을 로컬에서 scp 또는 SSM fetch
#   로컬에서: scp -P <port> -i <key> firebase-sa.json root@<host>:/workspace/firebase-sa.json
#   또는 Pod 안: aws ssm get-parameter --name /sunity/motion/firebase-sa --with-decryption \
#                  --query Parameter.Value --output text > /workspace/firebase-sa.json
#
# 자동 처리 (예상 시간 ~15분 with MAX_JOBS=nproc, ~45분 single-core):
#   1. apt deps (ffmpeg + libgl1 + libglib2 + unzip)
#   2. mmcv CUDA build (MAX_JOBS=$(nproc), ~5-10분)
#   3. mmpose stack
#   4. Python deps (mmpose stack + boto3 + google-genai + firebase-admin + imageio + onnxruntime-gpu)
#   5. RTMW weights 다운로드 + unzip (~73초, 327MB)
#   6. .bashrc 영구 박제 (PATHs, RTMW_DEVICE, LD_LIBRARY_PATH, FIREBASE_SA_PATH)
#   7. Gemini API 호출 검증
#   8. 5영상 sweep wrapper 박제 (별도 명령으로 실행)
#
# 박제 함정 누적 12종 ([[runpod-gpu-env.md]] 참조):
#   - mmcv CUDA build single-core → MAX_JOBS=nproc + ninja 선행
#   - onnxruntime (CPU only) → onnxruntime-gpu 명시
#   - RTMW device='cpu' hardcode → RTMW_DEVICE env var (commit 50af90b)
#   - onnxruntime-gpu 버전/cuDNN 매트릭스 → 1.19.2 (CUDA 12 + cuDNN 9 native)
#   - cuDNN 9 system path 미설치 → torch 번들 LD_LIBRARY_PATH 추가
#   - cublasLt 11 vs 12 → 1.19.x CUDA 12 native (1.18.x 함정)
#   - _load_video_frames OOM (4K 21GB allocation) → FfmpegFrameExtractor 위임 (commit 391c933)
#   - 함정 20: OpenMMLab CDN 글로벌 만료 (2026-06-04) → RTMW HF/S3 mirror
#   - 함정 22: rtmlib det=None 도 OpenMMLab YOLOX 자동 다운 → YOLOX_ONNX_PATH 명시 (commit 081192b)
#   - 함정 23: runpod_inference/requirements.txt install 누락 → step 5/8 통합
#   - 함정 24: RUNPOD_AUTH_TOKEN .bashrc 박제 누락 → Lambda env 자동 fetch
#   - 함정 27: uvicorn restart 시 __pycache__ stale → restart 전 청소

set -e

# Path E2E (2026-06-05): production E2E 정합 — Pod ID 인자 받아 자동 Lambda env update
# 사용법: POD_ID=xxxxxxxxx bash setup_pod_full.sh
POD_ID="${POD_ID:-}"
if [ -z "$POD_ID" ]; then
  echo "WARN: POD_ID 미설정 — Lambda env 자동 update + production server 자동 시작 skip"
  echo "  (sweep 검증만 가능. production E2E test 박제 시 POD_ID 필수)"
  echo "  사용법: POD_ID=<runpod-pod-id> bash $0"
fi

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "ERROR: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 미설정"
  echo ""
  echo "사용법:"
  echo "  export AWS_ACCESS_KEY_ID=<키>"
  echo "  export AWS_SECRET_ACCESS_KEY=<시크릿>"
  echo "  POD_ID=<runpod-pod-id> bash $0"
  exit 1
fi

export AWS_DEFAULT_REGION=ap-northeast-2
export RECOGNIZER_BACKEND=gemini
# 박제 함정 20-22 (2026-06-06 OpenMMLab CDN 만료) — cocktail13 path 폐기, HF mirror 박제
export RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx
export YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx

echo "=== [1/8] apt deps (ffmpeg / libgl / unzip) ==="
apt-get update -qq 2>&1 | tail -2
apt-get install -y -qq ffmpeg libgl1 libglib2.0-0 unzip 2>&1 | tail -3

echo "=== [2/8] numpy 다운그레이드 (mmpose 1.x ABI) ==="
pip install -q "numpy>=1.26,<2"

echo "=== [3/8] mmcv (no-build-isolation 함정 + MAX_JOBS 가속) ==="
# 박제 함정 (2026-06-05): MAX_JOBS 미설정 시 single-core build → 30분+ (cudafe++/cicc).
# 박제 함정 (2026-06-06): inline `MAX_JOBS=$(nproc) pip install ...` 만으론 single-core 폴백.
#   원인 = torch.utils.cpp_extension.BuildExtension 이 ninja 미설치 시 distutils 폴백 →
#   MAX_JOBS 환경변수 자체를 무시. 64-core 머신에서 1 nvcc/cicc 만 도는 증상.
#   Fix = (1) ninja 선행 install, (2) export 로 자식 프로세스 전파.
pip install -q ninja
export MAX_JOBS=$(nproc)
pip install -q --no-build-isolation "mmcv>=2.0,<2.2"

echo "=== [4/8] mmpose stack + chumpy ==="
pip install -q --no-build-isolation chumpy
pip install -q rtmlib==0.0.15 mmpose==1.3.2 mmengine==0.10.7 mmdet==3.3.0 xtcocotools==1.14.3

echo "=== [5/8] python deps (boto3 / imageio / google-genai / firebase-admin / onnxruntime-gpu / runpod server deps) ==="
pip install -q boto3 'imageio[pyav]' imageio-ffmpeg firebase-admin google-genai
# 박제 함정 (2026-06-05): rtmlib 디폴트 의존성에 onnxruntime (CPU) 만 포함 → CUDA EP 미활성 → 영상당 30분+ CPU inference.
# onnxruntime 제거 + onnxruntime-gpu 1.19.2 (CUDA 12 + cuDNN 9 native) 명시 install 필수.
# - 1.18.x = CUDA 11 기본 (libcublasLt.so.11 요구) — 시스템 CUDA 12 환경 미스매치
# - 1.26.x = cuDNN 9 + 시스템 path 요구 (torch 번들로 못 찾음) — LD_LIBRARY_PATH 추가도 필요
# 1.19.2 가 가장 안전 (torch 2.4 cu124 매칭).
pip uninstall -y -q onnxruntime 2>/dev/null || true
pip install -q "onnxruntime-gpu==1.19.2"
# 박제 함정 23 (2026-06-06): runpod_inference/requirements.txt 박제 누락 → uvicorn 시작 실패.
# fastapi/uvicorn/pydantic/mediapipe/ultralytics/einops/timm 등 server 의존성 박제.
if [ -f /workspace/SunityMotion/backend/runpod_inference/requirements.txt ]; then
  pip install -q -r /workspace/SunityMotion/backend/runpod_inference/requirements.txt
fi

echo "=== [6/8] RTMW + YOLOX weights 다운로드 (OpenMMLab CDN 만료 대응) ==="
# 박제 함정 20 (2026-06-06): download.openmmlab.com 도메인 만료 (Alibaba HiChina expired).
# RTMW = S3 백업 (sunity-motion 계정 박제) 우선, HF mirror fallback.
# YOLOX = HF mirror (S3 백업 미박제 — follow-up).
mkdir -p /workspace/rtmw_weights /workspace/yolox_weights

# RTMW-X-384 (369MB) — S3 백업 우선 (같은 AWS 계정, fast), HF fallback
if [ ! -f "$RTMW_ONNX_PATH" ]; then
  echo "  RTMW 다운로드 중..."
  if aws s3 cp s3://sunity-motion-pilot-videos/_artifacts/rtmw-x-384_bukuroo_hf.onnx "$RTMW_ONNX_PATH" --quiet; then
    echo "  ✓ RTMW S3 백업에서 다운로드 완료"
  else
    echo "  S3 fail → HF mirror fallback"
    curl -L --fail -o "$RTMW_ONNX_PATH" \
      "https://huggingface.co/bukuroo/RTMW-ONNX/resolve/main/rtmw-x-384.onnx" 2>&1 | tail -2
  fi
fi
ls -lh "$RTMW_ONNX_PATH"

# YOLOX-M (97MB, Apache-2.0) — HF mirror (hr16/yolox-onnx)
if [ ! -f "$YOLOX_ONNX_PATH" ]; then
  echo "  YOLOX 다운로드 중..."
  curl -L --fail -o "$YOLOX_ONNX_PATH" \
    "https://huggingface.co/hr16/yolox-onnx/resolve/main/yolox_m.onnx" 2>&1 | tail -2
fi
ls -lh "$YOLOX_ONNX_PATH"

echo "=== [7/8] .bashrc 영구 박제 (다음 SSH 세션 자동 적용) ==="
cat >> /root/.bashrc << 'BRC'

# Phase 5 Wave 4 — Pod 환경 박제 (setup_pod_full.sh 박제)
export AWS_DEFAULT_REGION=ap-northeast-2
export RECOGNIZER_BACKEND=gemini
# 박제 함정 20-22 (2026-06-06): OpenMMLab CDN 만료 → HF/S3 mirror path
export RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx
export YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx
export PYTHONPATH=/workspace/SunityMotion/backend/shared/python:.
export RTMW_DEVICE=cuda  # 박제 함정 (2026-06-05): cpu 디폴트 → GPU 0% → 영상당 30분+. cuda 강제.

# 박제 함정 (2026-06-05): onnxruntime-gpu 가 시스템 cuDNN 9 / cublasLt 12 못 찾음 → CUDAExecutionProvider load fail.
# torch 번들 nvidia/cudnn + nvidia/cublas path 를 LD_LIBRARY_PATH 에 추가.
export LD_LIBRARY_PATH=/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/dist-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH

# Firebase SA path (Gemini recognizer 의 학원 용어 매핑 + gemini_cache 필수).
# 파일 자체는 belle 가 scp 또는 SSM ssm get-parameter 로 박제. 박제 시 path 박제됨.
export FIREBASE_SA_PATH=/workspace/firebase-sa.json

# GEMINI_API_KEY = SSM fetch 매번 (보안상 .bashrc 박제 X)
# AWS_KEY = belle 가 매 세션 export 또는 RunPod 콘솔 Env 박제
# 매 세션:
#   export AWS_ACCESS_KEY_ID=...
#   export AWS_SECRET_ACCESS_KEY=...
#   export GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key --with-decryption --query Parameter.Value --output text)
BRC

# 박제 함정 24 (2026-06-06): RUNPOD_AUTH_TOKEN .bashrc 박제 누락 → /analyze 401.
# Lambda env 의 RUNPOD_AUTH_TOKEN 가 source of truth. AWS 권한 있을 때 자동 sync.
RUNPOD_TOKEN_FROM_LAMBDA=$(aws lambda get-function-configuration \
  --function-name sunity-motion-pilot-pipeline \
  --region ap-northeast-2 \
  --query 'Environment.Variables.RUNPOD_AUTH_TOKEN' --output text 2>/dev/null || echo "")
if [ -n "$RUNPOD_TOKEN_FROM_LAMBDA" ] && [ "$RUNPOD_TOKEN_FROM_LAMBDA" != "None" ]; then
  echo "export RUNPOD_AUTH_TOKEN=$RUNPOD_TOKEN_FROM_LAMBDA" >> /root/.bashrc
  export RUNPOD_AUTH_TOKEN="$RUNPOD_TOKEN_FROM_LAMBDA"
  echo "  ✓ RUNPOD_AUTH_TOKEN 박제 (Lambda env sync)"
else
  echo "  ⚠ RUNPOD_AUTH_TOKEN Lambda fetch 실패 — /analyze 401 가능. 수동 export 필요."
fi

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
# 박제 함정 20-22 (2026-06-06): OpenMMLab CDN 만료 → HF/S3 mirror path
export RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx
export YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx
export RTMW_DEVICE=cuda  # GPU 강제 (박제 함정 2026-06-05)
# torch 번들 cuDNN 9 / cublas 12 — onnxruntime-gpu 가 시스템 path 못 찾음
export LD_LIBRARY_PATH=/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/dist-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH
# Firebase SA — gemini_cache + unregistered_hook 필수 (없으면 학원 용어 매핑 graceful degrade)
export FIREBASE_SA_PATH=${FIREBASE_SA_PATH:-/workspace/firebase-sa.json}
if [ ! -f "$FIREBASE_SA_PATH" ]; then
  echo "WARN: Firebase SA 파일 없음 — Gemini recognizer 가 학원 용어 매핑 못함 (motion='auto' 폴백)."
  echo "      scp 또는 SSM 으로 박제 필요: scp firebase-sa.json root@<pod>:$FIREBASE_SA_PATH"
fi
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

# Path E2E (2026-06-05): POD_ID 인자 박제 시 production E2E 자동 박제
if [ -n "$POD_ID" ]; then
  PROXY_URL="https://${POD_ID}-8000.proxy.runpod.net/analyze"
  echo ""
  echo "=== [9/10] production server 자동 시작 (uvicorn) ==="
  cd /workspace/SunityMotion/backend
  export PYTHONPATH=shared/python:.
  # 기존 server 종료 (idempotent)
  pkill -f "uvicorn.*server:app" 2>/dev/null || true
  sleep 1
  # 박제 함정 27 (2026-06-06): __pycache__ stale → 새 commit 의 env var read 누락 가능.
  # uvicorn restart 전에 lazy import path 의 .pyc 청소.
  find shared/python/sunity_shared -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
  find runpod_inference -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
  # 자동 server 시작 (background, log /tmp/runpod_server.log)
  nohup uvicorn runpod_inference.server:app \
    --host 0.0.0.0 --port 8000 --workers 1 \
    > /tmp/runpod_server.log 2>&1 &
  SERVER_PID=$!
  echo "server PID: $SERVER_PID"
  sleep 3
  if curl -fsS http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ server /health OK"
  else
    echo "⚠ server /health 미응답 — /tmp/runpod_server.log 확인"
  fi

  echo ""
  echo "=== [10/10] Lambda env RUNPOD_ANALYZE_URL 자동 update ==="
  echo "proxy URL: $PROXY_URL"
  python3 << PYEOF
import boto3
lambda_client = boto3.client('lambda', region_name='ap-northeast-2')
fn = 'sunity-motion-pilot-pipeline'
try:
    cfg = lambda_client.get_function_configuration(FunctionName=fn)
    env = cfg['Environment']['Variables']
    env['RUNPOD_ANALYZE_URL'] = '$PROXY_URL'
    lambda_client.update_function_configuration(
        FunctionName=fn,
        Environment={'Variables': env},
    )
    print('✓ Lambda env RUNPOD_ANALYZE_URL = $PROXY_URL')
except Exception as e:
    print(f'⚠ Lambda env update 실패: {e}')
PYEOF

  echo ""
  echo "=========================================="
  echo "✅ Production E2E 박제 완료"
  echo "=========================================="
  echo "  server: localhost:8000 (PID $SERVER_PID)"
  echo "  proxy:  $PROXY_URL"
  echo "  Lambda env 자동 update"
  echo ""
  echo "이제 앱에서 영상 분석 trigger 가능."
else
  echo ""
  echo "다음 단계 (sweep 검증 시):"
  echo "  bash /workspace/run_sweep_gemini.sh"
  echo ""
  echo "production E2E 박제 시 = POD_ID 인자 박제 후 재실행:"
  echo "  POD_ID=<runpod-pod-id> bash $0"
fi
