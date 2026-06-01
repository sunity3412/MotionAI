# RunPod 빠른 재셋업 체크리스트

> belle 가 Pod 끄고 다음에 다시 켤 때 사용하는 박제 — 새 Pod launch ~15-20분 안에 spike 실행 가능 상태로 복구.
> 본 docs 는 `backend/runpod_inference/setup.sh` 의 **보완** (mmpose/RTMPose/numpy 1.x 4함정 박제).
>
> 참조: memory `runpod-gpu-env.md` (2026-06-01 박제), `gsd-pod-work-push-first.md`, `license-blocklist-pose.md`.

---

## 0. 전제 — Pod 끄기 전에 (현재 세션 마무리 시)

| 항목 | 상태 |
|---|---|
| 로컬 Mac commit 후 GitHub push 완료 | 필수 — `git push origin main` 안 하면 Pod git pull 갱신 안 됨 (memory `gsd-pod-work-push-first.md` 박제) |
| 진행 중인 spike 결과 .json/.md 로컬 다운로드 | belle 가 수동 — Pod 종료 후 분실 위험 |
| Stop vs Terminate | **Terminate 권고** — Stop 은 GPU 회수 함정 (memory 박제). 어차피 Terminate 후 새 Pod = 깨끗하게 4함정 fix 박제부터 적용 |

---

## 1. 새 Pod launch (RunPod 웹 UI)

- **Template**: `RunPod PyTorch 2.4` (torch 2.4.1+cu124 박제, 다른 버전 금지)
- **GPU**: RTX 3090 / 4090 / RTX 5000 Ada — VRAM 16GB↑ CUDA 면 무엇이든 OK (현재 박제 = 3090)
- **Container Disk**: ≥ 30GB (시스템 패키지 + 모델 weights ~5GB + cache)
- **Volume**: 가능하면 **Network Volume `/workspace` 마운트** — 디스크 데이터 보존 (MotionBERT weights ~120MB / RTMPose weights ~150MB / SunityMotion git clone / firebase-sa.json 보존). 비용 ≈ $0.07/GB/month, 무시 가능.
- **SSH 키**: RunPod 계정 Settings>SSH Public Keys 에 `~/.ssh/id_ed25519` (sunity-runpod) 등록 — Pod 배포 *전*에 있어야 주입됨.
- **HTTP Ports**: 본 plan 18 spike 만 돌리면 SSH 만 필요 (8000 port 노출 불요 — uvicorn 서버 안 띄움).

---

## 2. Pod 진입 후 — 1 명령 박제

SSH "SSH over exposed TCP" (IP+포트, 진짜 sshd) 로 접속. ssh.runpod.io 프록시는 대화형 전용 — scp 안 됨.

```bash
ssh root@<pod-ip> -p <port>

# Pod 안에서 ↓
cd /workspace

# (Network Volume 마운트 시) /workspace/SunityMotion 이 보존돼 있으면 git pull 만
# 아니면 처음부터 clone
if [ -d SunityMotion/.git ]; then
  cd SunityMotion && git fetch --all && git reset --hard origin/main
else
  git clone https://github.com/<your-org>/SunityMotion.git
  cd SunityMotion
fi
```

---

## 3. 시스템 패키지 셋업 (~5분, 매 새 Pod 마다 필수)

setup.sh 가 NLF / MotionBERT / MediaPipe 처리 — 단 **mmpose/RTMPose 부분이 없음** (Plan 10 박제 4함정 fix 미반영). 아래 순서로:

```bash
cd /workspace/SunityMotion/backend

# 3-1. 기존 setup.sh — NLF (LICENSE 차단 박제, 단 모델 파일 자체는 호환 디스크 자원으로 보존)
#      + MotionBERT clone + MotionBERT weights 확인 + MediaPipe Heavy task 다운로드
#      ※ NLF lift path 는 Plan 12 (c) verdict 후 영구 폐기 — 호출 0건 박제.
#        setup.sh 의 NLF 모델 다운로드는 비활성 path 의 자원 박제만 (호출 X).
bash runpod_inference/setup.sh

# 3-2. Plan 10 박제 4함정 fix — mmpose / mmcv / numpy ABI / detector alias
#      (memory runpod-gpu-env.md 2026-06-01 § Plan 10 4함정 박제 그대로)
pip install --no-build-isolation "mmcv>=2.0,<2.2"   # 함정 1 fix (Python 3.11 wheel 미제공 + setuptools 81+ pkg_resources 제거)
pip install "numpy>=1.26,<2"                        # 함정 3 fix (xtcocotools binary wheel numpy 1.x 헤더)
pip install -U openmim
mim install "mmpose>=1.3,<1.4"                       # mmpose 1.3.2 — chumpy 함정 2 는 mmpose 가 자동 skip

# 3-3. xtcocotools / mmengine / mmdet 버전 박제 검증
python3 -c "import torch, mmcv, mmengine, mmdet, mmpose, xtcocotools, numpy; print(torch.__version__, mmcv.__version__, mmengine.__version__, mmdet.__version__, mmpose.__version__, xtcocotools.__version__, numpy.__version__)"
# 기대값:
#   torch 2.4.1+cu124
#   mmcv 2.1.0
#   mmengine 0.10.7
#   mmdet 3.3.0
#   mmpose 1.3.2
#   xtcocotools 1.14.3
#   numpy 1.26.4

# 3-4. CUDA 작동 확인 — 불량 Pod 박제 (nvidia-smi OK 라도 CUDA 할당 실패 가능)
CUDA_VISIBLE_DEVICES=0 python3 -c "import torch; t = torch.zeros(1, device='cuda'); print('CUDA OK', torch.cuda.get_device_name(0))"
# 실패 시 (cudaErrorDevicesUnavailable) → 불량 Pod, Terminate + 재배포
```

---

## 4. RTMPose weights 다운로드 (~3분, Network Volume 보존 시 skip)

```bash
mkdir -p /workspace/rtmpose_weights
cd /workspace/rtmpose_weights

# Config (.py)
wget -O rtmpose-l_8xb256-420e_coco-256x192.py \
  https://raw.githubusercontent.com/open-mmlab/mmpose/main/configs/body_2d_keypoint/rtmpose/coco/rtmpose-l_8xb256-420e_coco-256x192.py

# Checkpoint (.pth, ~150MB)
wget -O rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \
  https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth

ls -lh /workspace/rtmpose_weights/
# 기대: .py ~30KB + .pth ~150MB
```

---

## 5. MotionBERT weights (~120MB, Network Volume 보존 시 skip)

setup.sh 가 MotionBERT clone 은 자동, **weights 파일 (`best_epoch.bin`) 는 수동** (Plan 10 박제). 로컬 Mac 에서 scp:

```bash
# 로컬 Mac 에서 (Pod IP/port 갱신 후)
scp -P <port> ~/Dev/SunityMotion-Resources/best_epoch.bin \
  root@<pod-ip>:/workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin
```

또는 MotionBERT 공식 Model Zoo 에서 직접 다운로드:
- https://github.com/Walter0807/MotionBERT#model-zoo
- 파일: `MB_ft_h36m_global_lite/best_epoch.bin`

---

## 6. 환경 변수 + Firebase SA + AWS 자격증명

```bash
# Firebase SA (Network Volume 보존 시 skip)
# scp 또는 base64 박제 후 echo 로 복원 — belle 이 별도 박제 채널 사용

# AWS 자격증명 — memory `aws-keys-and-bucket.md` 박제 따름 (sunity-motion 키)
export AWS_ACCESS_KEY_ID=<...>
export AWS_SECRET_ACCESS_KEY=<...>
export AWS_DEFAULT_REGION=ap-northeast-2

# CUDA — 빈 문자열 함정 fix
export CUDA_VISIBLE_DEVICES=0

# Firebase
export FIREBASE_SA_PATH=/workspace/firebase-sa.json
```

---

## 7. spike 실행 확인 — Plan 18 fast-path

```bash
cd /workspace/SunityMotion
PYTHONPATH=backend/shared/python:. python3 -c "
import sys
from backend.research.spikes import spike_multi_engine_average
assert 'mmpose' not in sys.modules
print('Plan 18 spike import OK — module load 시점 mmpose/torch 미로드')
"

# Plan 18 T-6 live mode (실제 lift 호출, ~5분)
# - PLAN 의 T-6 how-to-verify 절차 그대로
```

---

## 8. 끝나면 — Terminate

```
RunPod 웹 UI → Pod → Terminate
```

Stop 금지 (GPU 회수 함정). Terminate 후 디스크 손실 — Network Volume 마운트 시에만 보존. 다음 세션 시 본 docs §1 부터 다시.

---

## 9. 빠른 path TL;DR

| 단계 | 시간 (Network Volume 보존 시) | 시간 (새 Pod) |
|---|---|---|
| Pod launch (§1) | ~2분 | ~2분 |
| git pull / clone (§2) | ~30초 | ~2분 (clone) |
| setup.sh + 4함정 fix (§3) | ~5분 | ~5분 |
| RTMPose weights (§4) | skip | ~3분 |
| MotionBERT weights (§5) | skip | ~2분 (scp) |
| 환경변수 (§6) | ~30초 | ~30초 |
| spike 실행 확인 (§7) | ~30초 | ~30초 |
| **합계** | **~9분** | **~15-20분** |

---

## 10. Anti-patterns (박제)

- **Stop 사용** — GPU 회수 함정 발현 (memory 박제). 매번 Terminate.
- **ssh.runpod.io 프록시 사용** — 대화형 전용. scp 불가. "SSH over exposed TCP" 사용.
- **`CUDA_VISIBLE_DEVICES=""` 그대로** — RunPod base image 가 빈 문자열로 줌. `=0` 명시 필수.
- **로컬 commit 후 push 누락** — Pod git pull 갱신 안 됨 (memory `gsd-pod-work-push-first.md` 박제).
- **torch 다른 버전 설치 시도** — torch 2.4.1+cu124 박제 (mmpose/mmcv 정합 박제). 다른 버전 = numpy / mmcv ABI 깨짐.
- **mmcv 2.2+** — Python 3.11 cp311 wheel 미제공. 2.0~2.1.x 만.
- **numpy 2.x** — xtcocotools 와 ABI 충돌. 1.26.x 박제.

---

*Last updated: 2026-06-01 (Plan 18 진입 박제, Plan 10 4함정 fix 동기화)*
