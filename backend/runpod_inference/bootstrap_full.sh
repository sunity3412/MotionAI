#!/bin/bash
# Complete pod bootstrap — 리포 정본 (2026-08-14 회수, quick-260814-l5i).
#
# ★이 파일이 리포에 없던 것이 결함이었다: 원본은 Pod 네트워크 볼륨(/workspace)에만
# 있었고, 볼륨을 잃으면 부트스트랩 자체를 복구할 수 없었다. 이제 리포가 정본이고
# Pod 사본은 여기서 복사한다(md5 대조 — start_server.sh 와 같은 규율).
#
# 컨테이너 재생성 시 pip 패키지는 초기화되지만 /workspace(네트워크 볼륨)의
# 리포·가중치·스크립트는 남는다. 그래서 매번 이 스크립트를 다시 돌려야 한다.
#
# 실행: bash /workspace/SunityMotion/backend/runpod_inference/bootstrap_full.sh
# 다음: bash backend/scripts/pod_doctor.sh 로 전 항목 확인
set -e
export AWS_DEFAULT_REGION=ap-northeast-2
echo "[1/5] apt deps"
apt-get update -qq 2>&1 | tail -1 || true
apt-get install -y -qq ffmpeg libgl1 libglib2.0-0 unzip 2>&1 | tail -1 || true
echo "[2/5] git pull"
cd /workspace/SunityMotion && git fetch origin main --quiet && git checkout main --quiet && git pull --ff-only --quiet && echo "  HEAD: $(git rev-parse --short HEAD)"
echo "[3/5] pip deps (ALL — incl gemini/cerebras/fastapi)"
python3 -m pip install -q --break-system-packages --root-user-action=ignore "numpy>=1.26,<2" boto3 'imageio[pyav]' imageio-ffmpeg firebase-admin rtmlib==0.0.15 google-genai cerebras-cloud-sdk fastapi 'uvicorn[standard]' pydantic
python3 -m pip uninstall --break-system-packages -y -q onnxruntime 2>/dev/null || true
python3 -m pip install -q --break-system-packages --root-user-action=ignore onnxruntime-gpu==1.19.2
# awscli — 재학습 사이클 assemble 단계의 canonical 백업(`aws s3 sync`)이 쓴다.
# 실측(2026-08-14): 새 Pod 에 없어서 Gemini 라벨 453초를 태운 뒤 중단됐다.
python3 -m pip install -q --break-system-packages --root-user-action=ignore awscli
echo "[4/5] weights check (network storage should already have these)"
ls -lh /workspace/rtmw_weights/rtmw-x-384.onnx /workspace/yolox_weights/yolox_m.onnx 2>/dev/null || echo "  WARN: weights missing — 네트워크 볼륨 확인 필요"
echo "[5/5] 학습 venv 는 별도 (용량 크고 추론에는 불필요)"
echo "  학습까지 하려면: bash backend/training/sft/setup_train_venv.sh"
echo "[done] now run: source /workspace/aws_env.sh && bash /workspace/start_server.sh"
echo "[done] 전 항목 확인: bash backend/scripts/pod_doctor.sh"
