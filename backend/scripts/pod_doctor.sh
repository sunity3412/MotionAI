#!/bin/bash
# Pod 준비 상태 진단 — "새로 시작해도 문제없게" (quick-260814-l5i).
#
# belle 2026-08-14: "확실히 셋업 끝난거지? 앞으로 새로 시작해도 문제없게끔 하라구".
# 이번 사이클에서 **코드는 완성인데 환경이 없어서** 터진 것이 3건이었다:
#   (1) awscli 부재 → Gemini 라벨 453초 태운 뒤 assemble 중단
#   (2) train_venv 부재 → SFT 가 한 번도 돈 적 없음이 드러남
#   (3) RTMW_ONNX_PATH 미주입 → 신규 영상 라벨 전량 실패
# 셋 다 "돌려보기 전에는 안 보이는" 종류였다. 이 스크립트가 돌려보기 전에 보이게 한다.
#
# 실행(Pod 안): bash backend/scripts/pod_doctor.sh
# 종료코드: 0 = 추론까지 준비됨 / 1 = 필수 결손 / 2 = 추론은 되나 학습 불가
#
# 각 항목은 **무엇이 없으면 무엇이 깨지는지**와 복구 커맨드를 같이 낸다 —
# 진단이 처방 없이 끝나면 사람이 또 archaeology 를 해야 한다.

ROOT="${SUNITY_ROOT:-/workspace/SunityMotion}"
VENV="${TRAIN_VENV:-/workspace/train_venv}"
FAIL=0
WARN=0

# swift 버전은 패키지 속성으로만 읽는다 — `swift --version` 은 ms-swift 4.4 의
# 서브커맨드 라우터에서 KeyError 트레이스백을 내 정상 설치를 실패처럼 보이게 한다.
swift_ver_doctor() { "$VENV/bin/python" -c "import swift; print(swift.__version__)" 2>/dev/null; }

ok()   { printf '  [OK]   %s\n' "$1"; }
bad()  { printf '  [결손] %s\n         → %s\n' "$1" "$2"; FAIL=1; }
warn() { printf '  [주의] %s\n         → %s\n' "$1" "$2"; WARN=1; }

echo "== 1. 리포 =="
if [ -d "$ROOT/.git" ]; then
  cd "$ROOT" || exit 1
  git fetch -q origin 2>/dev/null
  local_sha=$(git rev-parse --short HEAD 2>/dev/null)
  behind=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "?")
  if [ "$behind" = "0" ]; then ok "리포 $local_sha (origin/main 동기)"
  else warn "리포 $local_sha — origin 대비 $behind 커밋 뒤처짐" "git -C $ROOT pull --ff-only"; fi
else
  bad "리포 없음 ($ROOT)" "네트워크 볼륨 확인 — 볼륨이 안 붙었을 수 있다"
fi

echo "== 2. 추론 런타임 =="
for mod in numpy boto3 rtmlib firebase_admin fastapi onnxruntime; do
  if python3 -c "import $mod" 2>/dev/null; then ok "python: $mod"
  else bad "python 모듈 없음: $mod" "bash $ROOT/backend/runpod_inference/bootstrap_full.sh"; fi
done
if python3 -c "import onnxruntime as o; assert 'CUDAExecutionProvider' in o.get_available_providers()" 2>/dev/null; then
  ok "onnxruntime CUDA EP"
else
  warn "onnxruntime CUDA EP 없음 — CPU 추론은 느리고 결과가 다를 수 있다" "onnxruntime-gpu==1.19.2 재설치"
fi

echo "== 3. 가중치 =="
for w in /workspace/rtmw_weights/rtmw-x-384.onnx /workspace/yolox_weights/yolox_m.onnx; do
  [ -f "$w" ] && ok "가중치 $(basename "$w")" || bad "가중치 없음: $w" "네트워크 볼륨 확인"
done

echo "== 4. CLI =="
command -v ffmpeg >/dev/null && ok "ffmpeg" || bad "ffmpeg 없음" "apt-get install -y ffmpeg"
command -v aws >/dev/null && ok "aws CLI" || bad "aws CLI 없음 — 재학습 assemble 의 canonical 백업이 실패한다" "pip install awscli"

echo "== 5. 기동 env =="
if [ -f /workspace/aws_env.sh ]; then ok "aws_env.sh"; else bad "aws_env.sh 없음" "볼륨 확인 — AWS 자격증명 주입원"; fi
if [ -f /workspace/start_server.sh ]; then
  if [ -f "$ROOT/backend/runpod_inference/start_server.sh" ]; then
    a=$(md5sum /workspace/start_server.sh 2>/dev/null | cut -d' ' -f1)
    b=$(md5sum "$ROOT/backend/runpod_inference/start_server.sh" 2>/dev/null | cut -d' ' -f1)
    [ "$a" = "$b" ] && ok "start_server.sh == 리포 정본" \
      || warn "start_server.sh 가 리포 정본과 다름 (Pod 사본이 낡았을 수 있다)" \
              "cp $ROOT/backend/runpod_inference/start_server.sh /workspace/start_server.sh"
  fi
  # RTMW_ONNX_PATH 는 env 블록에서 온다 — 안 실으면 신규 영상 라벨이 전량 실패한다.
  grep -q "RTMW_ONNX_PATH" /workspace/start_server.sh && ok "env 블록에 RTMW_ONNX_PATH" \
    || bad "start_server.sh 에 RTMW_ONNX_PATH 없음" "라벨/재분석이 전부 실패한다 — 스크립트 확인"
else
  bad "start_server.sh 없음" "cp $ROOT/backend/runpod_inference/start_server.sh /workspace/"
fi

echo "== 6. 학습 환경 (SFT 를 돌릴 때만 필요) =="
# ★존재가 아니라 **import** 로 판정한다 (2026-08-14 실측 2건):
#   (a) 새 Pod 의 베이스 python 이 3.12 인데 venv 는 3.11 로 만들어져 있어, 실행
#       파일은 있는데 site-packages 를 못 찾아 `No module named swift` 로 학습이
#       즉사했다. 존재만 보던 이 검사는 그걸 "OK" 로 넘겼다.
#   (b) 같은 날 torch 도 설치 성공 직후 `libcudnn.so.9` 부재로 import 가 죽었다.
#   교훈: 설치 성공 != import 성공. 진단은 실제로 불러봐야 진단이다.
_venv_import_ok() { "$VENV/bin/python" -c "import $1" >/dev/null 2>&1; }
if [ -x "$VENV/bin/swift" ] && _venv_import_ok swift; then
  ok "train_venv + swift $(swift_ver_doctor)"
  for m in torch transformers peft vllm decord; do
    _venv_import_ok "$m" && ok "  학습 모듈: $m" \
      || warn "  학습 모듈 import 실패: $m" "$VENV/bin/pip install $m (venv python 버전 불일치면 pyvenv.cfg/bin 링크 확인)"
  done
  if find "${HF_HOME:-/workspace/hf_cache}" -maxdepth 4 -iname "*Qwen3-VL*" 2>/dev/null | grep -q .; then
    ok "백본 가중치 캐시"
  else
    warn "백본 가중치 미캐시 — 학습 첫 스텝에서 16GB 를 받는다(실패 시 사이클 유실)" \
         "bash $ROOT/backend/training/sft/setup_train_venv.sh"
  fi
elif [ -x "$VENV/bin/swift" ]; then
  # 실행 파일은 있는데 import 가 안 되는 상태 — 재설치 전에 원인부터 좁혀준다.
  vpy="$("$VENV/bin/python" --version 2>&1)"
  vlib="$(ls -d "$VENV"/lib/python* 2>/dev/null | head -1)"
  warn "train_venv 손상 — swift 실행파일은 있으나 import 불가 (venv $vpy / 패키지 $vlib)" \
       "버전 불일치면 재설치 전에: ln -sf /usr/bin/pythonX.Y $VENV/bin/python3 (패키지 재사용 가능)"
else
  warn "train_venv 없음 — 추론은 되지만 SFT 불가" \
       "bash $ROOT/backend/training/sft/setup_train_venv.sh (ms-swift + 백본 16GB, 수십 분)"
fi

echo "== 7. 서버 =="
if pgrep -f "uvicorn.*runpod_inference" >/dev/null 2>&1; then
  ok "추론 서버 프로세스"
else
  warn "추론 서버 미기동" "cd /workspace && source aws_env.sh && setsid nohup bash start_server.sh > /workspace/_server.log 2>&1 < /dev/null & disown"
fi

echo
if [ "$FAIL" = "1" ]; then
  echo "판정: 필수 결손 있음 — 위 복구 커맨드 실행 후 재진단"; exit 1
elif [ "$WARN" = "1" ]; then
  echo "판정: 추론 준비 완료 / 일부 항목 주의(학습·서버는 위 참조)"; exit 2
else
  echo "판정: 전 항목 준비 완료 — 추론·학습 둘 다 가능"; exit 0
fi
