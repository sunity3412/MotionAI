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
#
# Plan 01-08: MotionBERT + MediaPipe 추가 셋업 포함.
#   - MotionBERT 저장소 클론 + 가중치는 scp 로 수동 배치 (용량 크므로 git 미포함).
#   - MediaPipe pose_landmarker_heavy.task 모델 다운로드.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$(cd "$HERE/.." && pwd)"

# ── NLF ──────────────────────────────────────────────────────────────────────
MODEL_PATH="$BACKEND/scripts/nlf_l_multi.torchscript"
NLF_URL="https://github.com/isarandi/nlf/releases/download/v0.3.2/nlf_l_multi_0.3.2.torchscript"

# ── MotionBERT ────────────────────────────────────────────────────────────────
MOTIONBERT_ROOT="${MOTIONBERT_ROOT:-/workspace/MotionBERT}"
MOTIONBERT_REPO="https://github.com/Walter0807/MotionBERT.git"
MOTIONBERT_WEIGHTS_DIR="$MOTIONBERT_ROOT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite"
MOTIONBERT_WEIGHTS="$MOTIONBERT_WEIGHTS_DIR/best_epoch.bin"

# ── MediaPipe ─────────────────────────────────────────────────────────────────
MP_MODEL_DIR="$BACKEND/models"
MP_MODEL_PATH="$MP_MODEL_DIR/pose_landmarker_heavy.task"
MP_MODEL_URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"

echo "[1/6] 시스템 라이브러리 (mediapipe 의존)"
# mediapipe 는 libGL.so + libglib2.0-0 필요. 컨테이너에 없는 경우 설치.
if command -v apt-get &>/dev/null; then
  apt-get update -qq
  apt-get install -y -qq libgl1 libglib2.0-0
  echo "  libgl1, libglib2.0-0 설치 완료"
else
  echo "  apt-get 없음 — 건너뜀 (mediapipe 가 libGL 요구할 경우 수동 설치 필요)"
fi

echo "[2/6] Python 의존성 설치"
pip install -q --upgrade pip
pip install -q -r "$HERE/requirements.txt"

echo "[3/6] NLF 모델 다운로드 (없으면)"
mkdir -p "$BACKEND/scripts"
if [ -s "$MODEL_PATH" ]; then
  echo "  이미 존재: $MODEL_PATH ($(du -h "$MODEL_PATH" | cut -f1))"
else
  echo "  curl $NLF_URL"
  curl -L --fail -o "$MODEL_PATH" "$NLF_URL"
  echo "  완료: $MODEL_PATH ($(du -h "$MODEL_PATH" | cut -f1))"
fi

echo "[4/6] MotionBERT 저장소 (없으면 클론)"
if [ -d "$MOTIONBERT_ROOT/lib/model" ]; then
  echo "  이미 존재: $MOTIONBERT_ROOT"
else
  echo "  git clone $MOTIONBERT_REPO $MOTIONBERT_ROOT"
  git clone --depth 1 "$MOTIONBERT_REPO" "$MOTIONBERT_ROOT"
  echo "  완료: $MOTIONBERT_ROOT"
fi

echo "[4/6] MotionBERT 가중치 확인"
mkdir -p "$MOTIONBERT_WEIGHTS_DIR"
if [ -s "$MOTIONBERT_WEIGHTS" ]; then
  echo "  이미 존재: $MOTIONBERT_WEIGHTS ($(du -h "$MOTIONBERT_WEIGHTS" | cut -f1))"
else
  echo ""
  echo "  [주의] MotionBERT 가중치 파일 없음."
  echo "  아래 명령으로 로컬 → Pod 로 scp 전송 후 서버를 재기동하세요:"
  echo ""
  echo "    scp best_epoch.bin root@<pod-ip>:$MOTIONBERT_WEIGHTS"
  echo ""
  echo "  가중치 다운로드 위치 (MotionBERT 공식):"
  echo "    https://github.com/Walter0807/MotionBERT#model-zoo"
  echo "    파일: MB_ft_h36m_global_lite/best_epoch.bin"
  echo ""
  echo "  환경변수 MOTIONBERT_WEIGHTS 로 경로 오버라이드 가능."
  echo "  서버는 가중치 없이도 기동되나 MediaPipeWithLifterEngine 요청 시 오류 발생."
fi

echo "[5/6] MediaPipe pose_landmarker_heavy.task 다운로드 (없으면)"
mkdir -p "$MP_MODEL_DIR"
if [ -s "$MP_MODEL_PATH" ]; then
  echo "  이미 존재: $MP_MODEL_PATH ($(du -h "$MP_MODEL_PATH" | cut -f1))"
else
  echo "  wget $MP_MODEL_URL"
  wget -q -O "$MP_MODEL_PATH" "$MP_MODEL_URL"
  echo "  완료: $MP_MODEL_PATH ($(du -h "$MP_MODEL_PATH" | cut -f1))"
fi

echo "[6/6] CUDA 확인"
python3 - <<'PY'
import torch
print(f"  torch={torch.__version__}  CUDA={'available' if torch.cuda.is_available() else 'NOT AVAILABLE'}")
if torch.cuda.is_available():
    print(f"  device={torch.cuda.get_device_name(0)}")
PY

echo ""
echo "setup.sh 완료. 다음 명령으로 서버 기동:"
echo ""
echo "  cd $BACKEND"
echo "  export RUNPOD_AUTH_TOKEN=<생성>"
echo "  export AWS_ACCESS_KEY_ID=<...>"
echo "  export AWS_SECRET_ACCESS_KEY=<...>"
echo "  export AWS_DEFAULT_REGION=ap-northeast-2"
echo "  export FIREBASE_SA_PATH=/workspace/firebase-sa.json"
echo "  export CUDA_VISIBLE_DEVICES=0"
echo "  export MOTIONBERT_ROOT=$MOTIONBERT_ROOT"
echo "  # MOTIONBERT_WEIGHTS=$MOTIONBERT_WEIGHTS  (기본값 — 변경 시 오버라이드)"
echo "  uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1"

echo ""
echo "Phase 5 (Plan 5-04) — Gemini 기술 인식기 env 박제 (D-13 / D-15):"
echo ""
echo "  # 옵션 A — Parameter Store SSM fetch (D-15 박제 권장 path)"
echo "  export GEMINI_API_KEY=\$(aws ssm get-parameter \\"
echo "    --name /sunity/motion/gemini-api-key \\"
echo "    --with-decryption \\"
echo "    --query 'Parameter.Value' --output text \\"
echo "    --region ap-northeast-2)"
echo ""
echo "  # 옵션 B — env 직접 export (Plan 01-13 fallback path)"
echo "  # export GEMINI_API_KEY=<key>"
echo ""
echo "  # 어댑터 swap — gemini (Plan 5-03 박제), 미설정 = FallbackRecognizer default"
echo "  export RECOGNIZER_BACKEND=gemini  # 또는 GEMINI_RECOGNIZER_ENABLED=1 (alias)"
echo ""
echo "  # 경고: GEMINI_API_KEY 누락 + RECOGNIZER_BACKEND=gemini 상태에서 server 기동 시"
echo "  #       _warmup() 가 RuntimeError fail-loud (Plan 5-04 박제, Common Pitfall 4)"
