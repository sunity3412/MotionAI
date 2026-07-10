#!/usr/bin/env bash
# 학습 Pod 셋업 (Phase 22 Wave 3, 22-06 Task 2) — bake-off/SFT 학습 스택 + 후보 모델 가중치.
# 멱등 — 재실행해도 안전 (venv/설치/다운로드 전부 존재 시 skip 또는 no-op resume).
#
# 사용 (A100 80GB Pod, /workspace = Network Volume):
#   cd /workspace/SunityMotion/backend
#   bash training/setup_training_pod.sh
#
# 무엇을 하나:
#   [1] 전용 venv 생성 (/workspace/train_venv) — 서빙 파이프라인(rtmlib/onnxruntime-gpu
#       1.19.2)과 의존성 충돌 방지를 위해 시스템 pip 오염 금지. 컨테이너 디스크 20GB
#       한계 때문에 venv 도 /workspace(Volume)에 둔다.
#   [2] 학습 스택 설치 — ms-swift 4.4.0 / vllm 0.24.0 / lmms-eval 0.7.2
#       (22-RESEARCH Standard Stack, PyPI 재실측 2026-07-10 동일 — Package Legitimacy
#       Audit 전부 Approved, T-22-SC). A100=sm_80 → 전부 프리빌트 CUDA 휠, 소스 빌드 없음.
#   [3] 후보 모델 3종 가중치 다운로드 (HF_HOME=/workspace/hf_cache Volume 캐시, 순차).
#   [4] bake-off 미니셋 real 트랙 pre-fetch (S3 read-only GET — 업로드 절대 없음).
#   [5] CUDA sanity + 다음 단계 env 안내 (변수명만 echo — 시크릿 값 하드코딩 금지, T-22-18).
#
# 이 스크립트가 하지 않는 것:
#   - run_bakeoff.py 실행 (22-06 Task 2 후반 — coaching judge=Gemini 가용 시점에 별도 실행).
#   - S3 업로드 / PHASE22_BELLE_GREENLIGHT / _meta.collection_complete 접촉.
#   - 서빙 Pod 의존성(rtmlib/onnxruntime) 변경 — 시스템 site-packages 무접촉.
#
# ── 후보 모델 3종 (belle 2026-07-10 확정 — D-04 원안 2파전에서 3파전으로 확대, deviation) ──
# A6 해소 (2026-07-10 실측): "Qwen 3.6-VL-8B"(NLM 노트북 통칭)의 실제 ID 는
# Qwen/Qwen3-VL-8B-Instruct 다 — Qwen3.6 라인은 텍스트 전용(27B/35B-A3B)만 존재하고
# VL 최신 dense 8B = Qwen3-VL-8B-Instruct (ms-swift Supported-Models 문서 등재 확인).
# InternVL 은 OpenGVLab/InternVL3_5-8B (최종 릴리스 — -Instruct/-MPO 는 중간 산출물,
# -HF 는 transformers 포맷 변형; ms-swift/vLLM 둘 다 본 ID 지원).
# Cosmos 는 nvidia/Cosmos-Reason2-8B (NVIDIA Open Model License = 상업/파생/출력 OK,
# base=Qwen/Qwen3-VL-8B-Instruct, arch=qwen3_vl → vLLM 서빙 동일 경로.
# 주의: HF gated:auto — HF 토큰 + 모델 페이지 약관 동의 필요. ms-swift SFT 시
# 미등재 모델이므로 --model_type qwen3_vl 오버라이드 필요 예상).
#
# 공급망 (T-22-17): 모델은 공식 org(Qwen/OpenGVLab/nvidia) HF 경로만, 아래 상수로 박제.
# 다운로드 실패 시 유사 이름 대체 금지 — 사람 확인 후 재시도.
#
# ── deviation (2026-07-10, Rule 3): ms-swift 는 [all] 아닌 base 설치 ──────────
# RESEARCH 설치 라인은 `pip install "ms-swift[all]"` 이었으나 Pod 실측에서
# [all] → evalscope>=1.0.0 → literal `dotenv` (2013년 sdist, 죽은 `distribute`
# 빌드 의존)로 pip metadata-generation-failed. ms-swift 4.4.0 base 가 이미
# 학습 스택 전체(accelerate/peft/trl/transformers/datasets)를 포함하고, [all]
# 추가분은 evalscope(+opencompass/vlmeval)/swanlab/ray 뿐 — 셋 다 불필요
# (평가=lmms-eval+자체 run_bakeoff 이 RESEARCH 확정, 단일 Pod=ray 불필요).
# evalscope 트리는 Package Legitimacy Audit 미감사 — base 설치가 감사 범위
# 준수(T-22-17)에도 정답. [all] 재도입 금지 — 필요 extra 만 개별 추가할 것.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$(cd "$HERE/.." && pwd)"

# ── 버전 핀 (22-RESEARCH Standard Stack, PyPI 재확인 2026-07-10) ─────────────
MS_SWIFT_PIN="4.4.0"
VLLM_PIN="0.24.0"
LMMS_EVAL_PIN="0.7.2"
STACK_SENTINEL_TAG="ms-swift==${MS_SWIFT_PIN} vllm==${VLLM_PIN} lmms-eval==${LMMS_EVAL_PIN} v2-no-all-extra"

# ── 경로 상수 ────────────────────────────────────────────────────────────────
TRAIN_VENV="${TRAIN_VENV:-/workspace/train_venv}"
export HF_HOME="${HF_HOME:-/workspace/hf_cache}"
FIXTURES_DIR="${BAKEOFF_FIXTURES_DIR:-/workspace/bakeoff_fixtures}"
MANIFEST_PATH="$BACKEND/evals/phase22/fixtures/manifest.yaml"
VIDEO_BUCKET="${VIDEO_BUCKET:-sunity-motion-pilot-videos}"

# ── 후보 모델 ID 박제 (변경 금지 — 변경 시 22-BAKEOFF-RESULT.md 동시 수정) ──
BAKEOFF_MODEL_A="Qwen/Qwen3-VL-8B-Instruct"      # 후보 A (Apache 2.0, M-RoPE)
BAKEOFF_MODEL_B="OpenGVLab/InternVL3_5-8B"       # 후보 B (MIT+Apache, ViR)
BAKEOFF_MODEL_C="nvidia/Cosmos-Reason2-8B"       # 후보 C (NVIDIA OML, gated:auto)

echo "=== setup_training_pod.sh (Phase 22-06) ==="
echo "  venv=$TRAIN_VENV  HF_HOME=$HF_HOME  fixtures=$FIXTURES_DIR"

# ─────────────────────────────────────────────────────────────────────────────
echo "[1/5] 전용 venv (${TRAIN_VENV})"
if [ -x "$TRAIN_VENV/bin/python" ]; then
  echo "  이미 존재: $TRAIN_VENV ($("$TRAIN_VENV/bin/python" --version 2>&1))"
else
  python3 -m venv "$TRAIN_VENV"
  echo "  생성 완료: $TRAIN_VENV"
fi
PIP="$TRAIN_VENV/bin/pip"
PY="$TRAIN_VENV/bin/python"

# ─────────────────────────────────────────────────────────────────────────────
echo "[2/5] 학습 스택 설치 (ms-swift ${MS_SWIFT_PIN} / vllm ${VLLM_PIN} / lmms-eval ${LMMS_EVAL_PIN})"
STACK_SENTINEL="$TRAIN_VENV/.stack_installed"
if [ -f "$STACK_SENTINEL" ] && [ "$(cat "$STACK_SENTINEL")" = "$STACK_SENTINEL_TAG" ]; then
  echo "  이미 설치됨 (sentinel 일치) — skip"
else
  "$PIP" install -q --upgrade pip
  # A100(sm_80): vllm 이 CUDA 프리빌트 torch 를 의존성으로 끌어옴 — 소스 빌드 없음.
  # boto3/pyyaml = 미니셋 prefetch + run_bakeoff 실행용 (프로젝트 표준 의존).
  # huggingface_hub[cli] = hf/huggingface-cli 다운로드 커맨드 보장.
  # ms-swift 는 base (헤더 deviation 참조 — [all]=evalscope dotenv 함정+미감사 트리).
  "$PIP" install -q \
    "ms-swift==${MS_SWIFT_PIN}" \
    "vllm==${VLLM_PIN}" \
    "lmms-eval==${LMMS_EVAL_PIN}" \
    "boto3>=1.34,<2.0" \
    "pyyaml>=6" \
    "huggingface_hub[cli]"
  echo "$STACK_SENTINEL_TAG" > "$STACK_SENTINEL"
  echo "  설치 완료"
fi
echo "  버전 실측:"
"$PY" - <<'PYEOF'
import importlib.metadata as md
for pkg in ("ms-swift", "vllm", "lmms-eval", "torch", "transformers", "huggingface-hub", "boto3"):
    try:
        print(f"    {pkg}=={md.version(pkg)}")
    except md.PackageNotFoundError:
        print(f"    {pkg}==NOT INSTALLED")
PYEOF

# ─────────────────────────────────────────────────────────────────────────────
echo "[3/5] 후보 모델 3종 다운로드 (HF_HOME=$HF_HOME, 순차)"
mkdir -p "$HF_HOME"

# hf CLI 탐지 (huggingface_hub 신버전=hf, 구버전=huggingface-cli)
if [ -x "$TRAIN_VENV/bin/hf" ]; then
  HF_CLI="$TRAIN_VENV/bin/hf"
elif [ -x "$TRAIN_VENV/bin/huggingface-cli" ]; then
  HF_CLI="$TRAIN_VENV/bin/huggingface-cli"
else
  echo "  [오류] venv 에 hf/huggingface-cli 없음 — [2/5] 설치 확인 필요"; exit 1
fi

# HF 토큰 존재 여부 (gated 모델 Cosmos 용). 값은 절대 echo 하지 않는다 (T-22-18).
HF_TOKEN_PRESENT=0
if [ -n "${HF_TOKEN:-}" ] || [ -s "$HF_HOME/token" ] || [ -s "$HOME/.cache/huggingface/token" ]; then
  HF_TOKEN_PRESENT=1
fi

STATUS_A="PENDING"; STATUS_B="PENDING"; STATUS_C="PENDING"

download_model() {
  # $1=model_id  — hf download 는 자체 resume/skip 이라 멱등.
  local model_id="$1"
  echo "  ── $model_id"
  if "$HF_CLI" download "$model_id" >/dev/null 2>"$HF_HOME/.dl_err_$$"; then
    local snap_dir="$HF_HOME/hub/models--${model_id//\//--}"
    echo "     OK ($(du -sh "$snap_dir" 2>/dev/null | cut -f1 || echo '?'))"
    return 0
  fi
  echo "     FAILED — 마지막 오류:"
  tail -3 "$HF_HOME/.dl_err_$$" | sed 's/^/       /'
  rm -f "$HF_HOME/.dl_err_$$"
  return 1
}

download_model "$BAKEOFF_MODEL_A" && STATUS_A="OK" || STATUS_A="FAILED"
download_model "$BAKEOFF_MODEL_B" && STATUS_B="OK" || STATUS_B="FAILED"

if [ "$HF_TOKEN_PRESENT" = "1" ]; then
  download_model "$BAKEOFF_MODEL_C" && STATUS_C="OK" || STATUS_C="FAILED"
else
  STATUS_C="PENDING(HF token)"
  echo "  ── $BAKEOFF_MODEL_C"
  echo "     [보류] gated 모델 — HF 토큰 없음. 절차:"
  echo "       1. https://huggingface.co/$BAKEOFF_MODEL_C 에서 로그인 후 라이선스 동의(gated:auto=즉시 승인)"
  echo "       2. https://huggingface.co/settings/tokens 에서 read 토큰 발급"
  echo "       3. export HF_TOKEN=<토큰> 후 본 스크립트 재실행 (멱등 — A/B 는 skip 됨)"
fi
rm -f "$HF_HOME/.dl_err_$$" 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
echo "[4/5] bake-off 미니셋 real 트랙 pre-fetch (S3 read-only GET — 업로드 없음)"
if [ ! -f "$MANIFEST_PATH" ]; then
  echo "  [경고] manifest 없음: $MANIFEST_PATH — skip (git pull 확인)"
elif [ -f /workspace/aws_env.sh ] || [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
  # shellcheck disable=SC1091
  [ -f /workspace/aws_env.sh ] && source /workspace/aws_env.sh
  mkdir -p "$FIXTURES_DIR"
  MANIFEST_PATH="$MANIFEST_PATH" FIXTURES_DIR="$FIXTURES_DIR" VIDEO_BUCKET="$VIDEO_BUCKET" \
  "$PY" - <<'PYEOF'
# read-only: get_object 만 사용. put/delete 절대 없음 (하드 제약).
import os, pathlib, sys
import yaml, boto3
manifest = yaml.safe_load(pathlib.Path(os.environ["MANIFEST_PATH"]).read_text(encoding="utf-8"))
dest_root = pathlib.Path(os.environ["FIXTURES_DIR"])
bucket = os.environ["VIDEO_BUCKET"]
s3 = boto3.client("s3")
done = skipped = failed = 0
for item in manifest.get("items") or []:
    key = item.get("s3_key")
    if not key:  # synthetic/trap/hard_negative(relocate pending) 트랙 — 파일 없음.
        continue
    dest = dest_root / key
    if dest.exists() and dest.stat().st_size > 0:
        skipped += 1
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        s3.download_file(bucket, key, str(dest))
        done += 1
        print(f"    GET s3://{bucket}/{key}")
    except Exception as e:  # noqa: BLE001 - prefetch 는 best-effort, run_bakeoff 가 런타임 재시도
        failed += 1
        print(f"    FAIL {key}: {e}", file=sys.stderr)
print(f"  prefetch: downloaded={done} cached={skipped} failed={failed} -> {dest_root}")
PYEOF
else
  echo "  [보류] AWS 자격 없음 (/workspace/aws_env.sh 또는 env) — skip."
  echo "         run_bakeoff.py 가 런타임에 항목별 다운로드하므로 필수 아님."
fi

# ─────────────────────────────────────────────────────────────────────────────
echo "[5/5] CUDA sanity"
"$PY" - <<'PYEOF'
import torch
print(f"  torch={torch.__version__}  CUDA={'available' if torch.cuda.is_available() else 'NOT AVAILABLE'}")
if torch.cuda.is_available():
    print(f"  device={torch.cuda.get_device_name(0)} (cc={'.'.join(map(str, torch.cuda.get_device_capability(0)))})")
PYEOF

echo ""
echo "=== 모델 다운로드 상태 ==="
echo "  A  $BAKEOFF_MODEL_A : $STATUS_A"
echo "  B  $BAKEOFF_MODEL_B : $STATUS_B"
echo "  C  $BAKEOFF_MODEL_C : $STATUS_C"

echo ""
echo "setup_training_pod.sh 완료. bake-off 실행(22-06 Task 2 후반, SERIAL — 한 번에 한 모델):"
echo ""
echo "  source $TRAIN_VENV/bin/activate"
echo "  export HF_HOME=$HF_HOME"
echo "  # vLLM serve 는 localhost 바인드 — 외부 노출 금지 (T-22-19):"
echo "  python3 -m vllm.entrypoints.openai.api_server \\"
echo "      --model \$CANDIDATE_MODEL --host 127.0.0.1 --port 8000 \\"
echo "      --dtype bfloat16 --limit-mm-per-prompt image=64"
echo ""
echo "  # run_bakeoff env (값은 SSM/aws_env.sh 주입 — 하드코딩 금지, T-22-18):"
echo "  #   source /workspace/aws_env.sh"
echo "  #   export EVAL_OUT_DIR=/workspace/eval_out           # repo 밖 강제"
echo "  #   export BAKEOFF_VLLM_URL=http://127.0.0.1:8000/v1"
echo "  #   export BAKEOFF_MODEL=\$CANDIDATE_MODEL"
echo "  #   export FIREBASE_SA_PATH=/workspace/firebase-sa.json"
echo "  #   export VIDEO_BUCKET=$VIDEO_BUCKET"
echo "  #   export GEMINI_API_KEY=<SSM /sunity/motion/gemini-api-key>  # judge — 상한 복구 후"

# 최종 exit code: 후보 3종 전부 OK 면 0, 아니면 3 (재실행 필요 신호 — 멱등이므로 무해).
if [ "$STATUS_A" = "OK" ] && [ "$STATUS_B" = "OK" ] && [ "$STATUS_C" = "OK" ]; then
  exit 0
fi
echo ""
echo "[미완료] 위 상태표에서 OK 아닌 항목 해소 후 재실행 (exit 3)"
exit 3
