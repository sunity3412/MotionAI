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

# ── 격리 모드 (TRAIN_VENV_ISOLATED=1) ────────────────────────────────────────
# ★2026-08-15 실측: `--system-site-packages` 는 **베이스 이미지와 결혼시키는 옵션**이고
#   그 결혼이 오늘 하루에 세 번 값을 치렀다.
#     · 베이스 cudnn 을 먼저 물어 `undefined symbol: cudnnGetLibConfig` — 래퍼에
#       nvidia lib 경로를 앞세우는 LD_LIBRARY_PATH 곡예를 넣어야 했다
#     · Pod 이 3.12 로 바뀌었는데 venv 는 3.11 이라 링크가 어긋났다
#     · 3.11 에 남은 flashinfer 가 `array.array[int]`(3.12+ 문법)로 게이트를 죽였다
#   격리 모드는 베이스를 아예 안 본다 — 설치는 느리지만 Pod 이 바뀌어도 안 깨진다.
#   기본값은 기존 동작 유지(무회귀), 새로 만드는 쪽이 명시적으로 켠다.
if [ "${TRAIN_VENV_ISOLATED:-0}" = "1" ]; then
  echo "[setup] 1/5 venv 생성 (격리 — 베이스 이미지 미참조, python $(python3 --version 2>&1 | awk '{print $2}'))"
  python3 -m venv "$VENV" || exit 1
else
  echo "[setup] 1/5 venv 생성 (--system-site-packages = 베이스 이미지 패키지 재사용)"
  python3 -m venv --system-site-packages "$VENV" || exit 1
fi

# ── 설치 순서가 결과를 정한다 (2026-08-14 실측으로 확정) ─────────────────────
# torch 를 먼저 깔고 **vllm 을 마지막에** 깔면, vllm 이 자기 요구에 맞춰 torch 를
# 올리면서 torchvision 까지 짝을 맞춰 정리한다 — 실측 수렴값 torch 2.13.0+cu130 /
# torchvision 0.28.0+cu130, 7개 패키지 import 전건 통과.
# 베이스 이미지의 torch·torchvision 2.4.1 을 그대로 쓰려 하면 ABI 가 어긋난다
# (torchvision 0.19.1 은 torch==2.4.1 고정). 즉 아래 핀은 **하한 보장**이고 최종
# 버전 결정권은 4단계 vllm 에 있다 — 상한으로 읽고 vllm 을 막으면 스택이 깨진다.
echo "[setup] 2/5 torch 하한 확보 (최종 버전은 4단계 vllm 이 정한다)"
# ★실측(2026-08-14): 베이스 이미지 torch 2.4.1 을 재사용했더니 학습이 4분 만에
#   `AttributeError: 'Qwen3VLForConditionalGeneration' object has no attribute
#   'set_submodule'` 로 죽었다. `nn.Module.set_submodule` 은 **torch 2.5 신규**이고,
#   Qwen3-VL 을 지원하는 transformers(5.x)의 bitsandbytes 4bit 경로가 그것을 부른다.
#   즉 "베이스 torch 재사용"과 "Qwen3-VL 학습"은 양립하지 않는다 — venv 안에 2.5+ 를
#   깔아 베이스를 가린다.
"$VENV/bin/pip" install -q --upgrade pip
# ★기본 PyPI 에서 받는다 — `--index-url https://download.pytorch.org/whl/cu124` 는
#   pip 가 **그 인덱스만** 보게 만들어 `nvidia-cudnn-cu12` 등 의존 패키지를 못 받는다.
#   실측(2026-08-14): 그렇게 깔았더니 `ImportError: libcudnn.so.9` 로 torch import
#   자체가 죽었다. PyPI 의 linux torch 휠은 cu12x 빌드 + nvidia-* 번들이라 그냥 맞다.
"$VENV/bin/pip" install -q "torch>=2.5" \
  || { echo "[setup] torch 설치 실패" >&2; exit 3; }
# 검증 = import 까지 실제로 해본다(설치 성공 != import 성공 — cudnn 사건의 교훈).
"$VENV/bin/python" - <<'PY' || { echo "[setup] torch 검증 실패" >&2; exit 3; }
import torch
assert hasattr(torch.nn.Module, "set_submodule"), f"torch {torch.__version__} < 2.5"
assert torch.cuda.is_available(), "CUDA 사용 불가"
print("  torch", torch.__version__, "cuda", torch.version.cuda, "GPU", torch.cuda.get_device_name(0))
PY

echo "[setup] 3/5 ms-swift + 학습 의존성"
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

# ★decord — `run_sft.sh` 가 `FORCE_QWENVL_VIDEO_READER=decord` 로 **강제**하는 백엔드다.
#   신형 torchvision 은 `io.read_video` 를 제거해서(0.28 실측) qwen_vl_utils 기본
#   백엔드가 전 영상 행에서 죽는다 — 2026-07-12 에 이미 겪고 러너 주석에 남아 있던
#   문제인데 셋업에 빠져 있어 2026-08-14 학습이 같은 자리에서 또 죽었다
#   (`AttributeError: torchvision.io has no attribute read_video` + `No module named decord`).
#   decord 본체가 없으면 유지보수 포크(eva-decord)로 폴백한다.
"$VENV/bin/pip" install -q decord 2>/dev/null \
  || "$VENV/bin/pip" install -q eva-decord 2>/dev/null \
  || echo "[setup] decord 설치 실패 — 영상 행 학습 불가(텍스트 행만 가능)"
"$VENV/bin/python" -c "import decord; print('  decord', decord.__version__)" \
  || echo "[setup] decord import 불가 — run_sft 영상 디코드가 실패한다"

echo "[setup] 4/5 vLLM (게이트 단계가 쓴다 — 학습만 하고 끝나지 않게)"
# ★`run_sft_gates.sh` 는 `$VENV/bin/python -m vllm.entrypoints.openai.api_server` 로
#   병합본을 띄워 판정한다. 셋업에 vllm 이 빠져 있으면 **학습을 몇 시간 돌린 뒤**
#   게이트에서 ModuleNotFoundError 로 죽는다(2026-08-14 사전 발견 — 학습 전에 잡음).
# ★vllm 은 torch 를 자기 핀으로 되돌릴 수 있다 → 설치 후 torch 를 **재검증**하고,
#   set_submodule 이 사라졌으면 즉시 실패시킨다(조용한 회귀 금지).
# ★uvloop 을 함께 박는다 (2026-08-15 실측): vllm 본체는 uvloop 없이도 import 되지만
#   게이트가 실제로 부르는 `vllm.entrypoints.openai.api_server` 는 최상단에서
#   `import uvloop` 한다. 그래서 `import vllm` 검증은 **통과하는데 게이트만 죽었다**
#   (학습 39분 태운 뒤 서버 기동에서 ModuleNotFoundError, exit 11).
# ★TRAIN_VENV_SKIP_VLLM=1 (2026-08-21): 드라이버 550(cu124 상한) Pod 에서 vllm
#   최신판이 torch 를 cu13x 로 끌어올려 이 스크립트가 4단계에서 hard-fail 하는 것을
#   막는다. Qwen3-VL 을 서빙할 만큼 새로운 vllm 과 cu124 torch 는 양립 가능성이
#   낮아, 게이트는 별도 venv 축으로 분리한다. 기본 0 = 기존 설치 유지(무회귀).
if [ "${TRAIN_VENV_SKIP_VLLM:-0}" = "1" ]; then
  echo "[setup] TRAIN_VENV_SKIP_VLLM=1 — vllm/uvloop 설치 생략. 이 venv 로는 게이트 단계 불가 — gates 는 vllm 가용 venv(TRAIN_VENV 교체)로 별도 실행"
else
  "$VENV/bin/pip" install -q vllm uvloop || echo "[setup] vllm 설치 실패 — 게이트 단계 불가(학습은 가능)"
fi

# ★liger-kernel — 레시피에 없으면 재현이 안 된다 (2026-08-15 실증).
#   run_sft.sh 는 `import liger_kernel` 성공 시에만 --use_liger_kernel true 를 켠다.
#   없으면 조용히 false 로 떨어지고, 로짓(시퀀스 x 어휘 15만)이 8.57GiB 를 한 번에
#   잡아 32GB GPU 에서 첫 스텝 OOM 이다. 08-14 에 손으로 깔아 학습을 살렸는데 그게
#   레시피에 안 들어가 있어서, 3.12 로 새로 만든 venv 에서 그대로 재발했다.
"$VENV/bin/pip" install -q liger-kernel \
  || echo "[setup] liger-kernel 설치 실패 — 32GB 이하 GPU 에서 로짓 OOM 위험"

# ★run_sft.sh [1/3] 이 **venv python 으로** 학습셋을 S3 에서 당기고 영상을 만진다:
#   boto3 / botocore / imageio_ffmpeg 를 그 인라인 스크립트가 직접 import 한다.
#   --system-site-packages 시절엔 베이스 이미지에서 빌려 썼기 때문에 레시피에
#   없어도 돌았다. 격리 모드(2026-08-15)로 바꾸자 `No module named 'boto3'` 로
#   학습이 [1/3] 에서 즉사했다 — 격리의 대가는 "빌려 쓰던 것을 전부 명시"다.
"$VENV/bin/pip" install -q boto3 "imageio[pyav]" imageio-ffmpeg \
  || echo "[setup] S3/영상 의존성 설치 실패 — run_sft [1/3] 학습셋 동기화 불가"
"$VENV/bin/python" - <<'PY' || { echo "[setup] vllm 설치 후 torch 회귀 — 게이트/학습 불가" >&2; exit 4; }
import torch
assert hasattr(torch.nn.Module, "set_submodule"), f"torch 회귀: {torch.__version__} (<2.5)"
assert torch.cuda.is_available(), "CUDA 사용 불가"
try:
    import vllm
    # ★패키지가 아니라 **게이트가 실제로 실행하는 진입점**을 불러본다.
    #   `import vllm` 만으로는 uvloop 같은 진입점 전용 의존성 결손을 못 잡는다.
    import vllm.entrypoints.openai.api_server  # noqa: F401
    print("  vllm", vllm.__version__, "(api_server 진입점 OK) | torch", torch.__version__)
except ImportError as e:
    print(f"  vllm 게이트 진입점 불가({e}) — 게이트 단계는 불가, 학습은 가능 | torch", torch.__version__)
PY

echo "[setup] 5/5 백본 가중치 사전 다운로드 ($MODEL)"
# 학습 중 첫 스텝에서 받으면 실패 시 사이클 전체가 날아간다 — 셋업에서 미리 받는다.
HF_HOME="$HF_HOME" "$VENV/bin/python" - <<'PY' || echo "[setup] 가중치 사전받기 실패(학습 중 재시도됨)"
import os
from huggingface_hub import snapshot_download
mid = os.environ.get("SFT_MODEL", "Qwen/Qwen3-VL-8B-Instruct")
p = snapshot_download(mid, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])
print("[setup] 가중치:", p)
PY

echo "[setup] 완료 — ms-swift $(swift_ver) / venv $VENV"
