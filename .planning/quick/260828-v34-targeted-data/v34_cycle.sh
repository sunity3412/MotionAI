#!/bin/bash
# v34 사이클 — 표적 데이터 18편(정타11+fault7)이 처음 실리는 학습. LR 1e-4 (08-26 실증 설정).
# 관문 자동화: gates venv 병렬 구축(컨테이너 디스크) + 병합본 토크나이저 교정(08-26 실증).
set -u
# ── RTMW GPU env — 정본은 /workspace/start_server.sh 의 env 블록이다 ──────────────
# ★08-28 실측: 아래 RTMW_DEVICE 가 없어서 08-27·08-28 라벨이 전부 CPU 로 돌았다
#   (GPU 0%, 영상당 ~20분). rtmw_engine.py:131 의 코드 디폴트가 'cpu' 라 미주입은
#   에러가 아니라 "조용한 CPU 폴백"이다. 그동안 이 값은 Pod 의 .bashrc 에 박아 왔는데
#   컨테이너를 새로 만들면 .bashrc 가 초기화되므로 그 관행으로는 살아남지 않는다.
#   → 사이클 스크립트가 직접 박는다. 관측 = nvidia-smi 사용률이 0 이 아니어야 한다.
export RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx
export YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx   # OpenMMLab CDN 만료 우회
export RTMW_DEVICE=cuda
# ★RTMW_DETERMINISTIC 은 여기 켜지 않는다 (08-28 A/B 실측: 켜면 1.92fps, 끄면 27.48fps
#  = 14배). 옵션값이 ORT 1.19.2 기준이라 1.22 에서 conv 가 fallback 경로로 떨어진다
#  ("running in Fallback mode" 경고 다발). 게다가 rtmw_engine.py 주석이 "eval 전용"이라
#  못박고 있고, 08-08 결정론 규율의 목적은 채점·렌더 정렬 재현성이지 좌표 1회 추출·
#  캐시하는 라벨 경로가 아니다. 결정적으로 기존 363행이 전부 OFF 로 라벨돼 있어
#  여기만 켜면 데이터셋이 오히려 안 맞는다. 재도입하려면 먼저 1.22 용 옵션을 재측정할 것.
# ORT GPU (08-27 실측): onnxruntime-gpu==1.22(CUDA 12 빌드) + torch 동봉 cuDNN/cuBLAS 경로.
# 부트스트랩보다 먼저 깔아야 아래 CUDA EP 검증이 성립한다.
export LD_LIBRARY_PATH="/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/dist-packages/nvidia/cublas/lib:${LD_LIBRARY_PATH:-}"
for W in "$RTMW_ONNX_PATH" "$YOLOX_ONNX_PATH"; do
  [ -f "$W" ] || { echo "CYCLE_ENDED rc=4 (가중치 없음: $W)"; exit 4; }
done

# 컨테이너 부트스트랩 (새 pod 마다 필요 — 08-27 실측: awscli/genai/rtmlib 부재로 3연속 정지)
python3 -c "import boto3, rtmlib, cv2, imageio; from google import genai" 2>/dev/null || \
  pip install -q awscli google-genai boto3 rtmlib opencv-python-headless imageio imageio-ffmpeg

# ★ORT 는 따로 — rtmlib 의 의존성이 CPU 판 onnxruntime 을 끌고 오고, GPU 판과 공존하면
#  CUDA EP 가 아예 안 뜬다 (08-28 실측: 둘 다 1.29 설치 → providers=[Azure,CPU] → RTMW 가
#  CPU 로 떨어져 영상당 ~20분). 버전 무핀도 금물 — 1.29 는 CUDA 13 라이브러리를 요구한다.
#  판정은 "설치돼 있냐"가 아니라 "CUDAExecutionProvider 가 뜨냐"로 한다.
python3 -c "import onnxruntime as o,sys; sys.exit(0 if 'CUDAExecutionProvider' in o.get_available_providers() else 1)" 2>/dev/null || {
  pip uninstall -y -q onnxruntime onnxruntime-gpu >/dev/null 2>&1
  pip install -q "onnxruntime-gpu==1.22"
  python3 -c "import onnxruntime as o,sys; sys.exit(0 if 'CUDAExecutionProvider' in o.get_available_providers() else 1)" \
    || { echo "CYCLE_ENDED rc=5 (ORT CUDA EP 미탑재 — CPU 라벨링은 과금 낭비라 중단)"; exit 5; }
}
cd /workspace/SunityMotion/backend || exit 3
git fetch origin 2>/dev/null
git -c user.name=pod -c user.email=pod@local merge origin/main -m sync 2>/dev/null || true
source /workspace/aws_env.sh
export PHASE22_BELLE_GREENLIGHT=1 SFT_LR=1e-4 SFT_RESUME=none
CU=/workspace/train_venv_cu124

# gates venv 병렬 구축 — vllm 0.11.0 + transformers 4.57.1 (드라이버 CUDA 12.4 실증 조합)
setsid nohup bash -c 'python3 -m venv /root/gates_venv2 && \
  /root/gates_venv2/bin/pip install -q --no-input "vllm==0.11.0" "transformers==4.57.1" && \
  /root/gates_venv2/bin/python3 -c "import vllm, torch; torch.zeros(1, device=\"cuda\")" && \
  touch /root/GATES_VENV_READY' > /root/gates_venv_build.log 2>&1 &

TRAIN_VENV=$CU bash training/sft/run_retrain_cycle.sh preflight || { echo "CYCLE_ENDED rc=6 (preflight)"; exit 6; }
TRAIN_VENV=$CU bash training/sft/run_retrain_cycle.sh label     || { echo "CYCLE_ENDED rc=7 (label)"; exit 7; }
TRAIN_VENV=$CU bash training/sft/run_retrain_cycle.sh assemble  || { echo "CYCLE_ENDED rc=8 (assemble)"; exit 8; }
TRAIN_VENV=$CU bash training/sft/run_retrain_cycle.sh train     || { echo "CYCLE_ENDED rc=9 (train)"; exit 9; }

# gates 1차 = bf16 merge 생성 (cu124 에 vllm 없음 — vLLM 사망은 예상 동작, 관용)
TRAIN_VENV=$CU bash training/sft/run_retrain_cycle.sh gates || true

# 병합본 토크나이저 교정 — transformers 5.x 가 저장한 tokenizer_config(list형
# extra_special_tokens)를 4.57 이 못 읽는다. LoRA 는 토크나이저 불변이라 베이스 원본이 정본.
B=$(ls -d /workspace/hf_cache/hub/models--Qwen--Qwen3-VL-8B-Instruct/snapshots/*/ | head -1)
M=$(ls -dt /workspace/phase22_sft_out/*/checkpoint-*-merged 2>/dev/null | head -1)
[ -n "$M" ] && cp "$B/tokenizer_config.json" "$B/tokenizer.json" "$B/vocab.json" "$B/merges.txt" "$M/"

for i in $(seq 1 60); do [ -f /root/GATES_VENV_READY ] && break; sleep 30; done
[ -f /root/GATES_VENV_READY ] || { echo "CYCLE_ENDED rc=11 (gates venv 미구축 — /root/gates_venv_build.log)"; exit 11; }

TRAIN_VENV=/root/gates_venv2 bash training/sft/run_retrain_cycle.sh gates || { echo "CYCLE_ENDED rc=10 (gates 실행 실패)"; exit 10; }
TRAIN_VENV=$CU bash training/sft/run_retrain_cycle.sh promote
echo "CYCLE_ENDED rc=$?"
