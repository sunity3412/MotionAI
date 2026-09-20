#!/bin/bash
# Bring up runpod_inference server on :8000 with RTMW GPU env + Lambda-synced auth token.
export AWS_DEFAULT_REGION=ap-northeast-2
export CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-api-key
export GEMINI_COACH_ENABLED=1   # pilot coach = Gemini (belle 2026-06-16); Cerebras stays as verified fallback
export GEMINI_VISION_VETO_ENABLED=1  # kip-up 등 결함 vision 거부권 — 미설정=OFF 함정(2026-07-02 FP 재발 원인). start_server 에 영구 박제
export GEMINI_MAX_VETO_WALL_S=300    # 검증된 sweep 설정과 동일(기본 120 은 미검증)
# ── Phase 27-09 신규 env 박제 (git 밖 — Pitfall 6. 미주입=무음 비활성/기본값) ──
export GEMINI_UPLOAD_PREFETCH=1     # 27-04 학생 업로드+scene_finder 를 포즈 그늘에 겹치기 (rollback: 0)
export GEMINI_FANOUT_WORKERS=4      # 27-05 veto fan-out 동시성 (429 시 2, rollback: 1)
export STUDENT_FRAME_CACHE=1        # 27-06 학생 프레임 재사용 — RunPod ON (Lambda 는 0)
# 27-08 D-05 — moment extractor 만 Flash. veto 는 GEMINI_MODEL 체인 유지.
# ★이 키를 지우면 안 된다 (quick-260818-lik 에서 한 번 지웠다가 되돌림):
#   gemini_moment_extractor.py:62 의 체인이 GEMINI_MOMENT_MODEL → GEMINI_MODEL →
#   "gemini-2.5-pro" 라서, 미설정이면 Flash 가 아니라 **2.5-pro 로 되돌아간다**.
#   즉 이 줄의 부재는 "기본값 사용"이 아니라 D-05 결정의 취소다.
# ★단 모델 문자열은 여기 박지 않는다 — 버전 owner 는 gemini/config.py 한 곳이고,
#   여기서 문자열을 박으면 config 를 올려도 이 줄이 덮어써서 갱신이 무효가 된다.
export GEMINI_MOMENT_MODEL=$(PYTHONPATH=/workspace/SunityMotion/backend/shared/python \
  python3 -c "from sunity_shared.gemini.config import DEFAULT_C_MODEL; print(DEFAULT_C_MODEL)")
echo "GEMINI_MOMENT_MODEL: $GEMINI_MOMENT_MODEL"
export GEMINI_SPOTCHECK_MODEL=gemini-3.1-pro-preview  # 32-13 스팟체크 판정 모델 (스모크 확정 — 스왑 시 이 줄만)
export PR_INVERSION_ENABLED=1  # 32-15 PR 인버전 2-pass 보정 — 제한 게이트 PASS(invert 46.8%↑, power-spin detect False) 후 on. rollback: 이 줄 삭제
export ROT180_INVERSION_ENABLED=1  # quick-260917-hjy: belle 승인(2026-09-17) 후 ON. ★기준 라이브러리 rot180_v1 승격과 **한 묶음**이다 — 한쪽만 되돌리면 학생·기준 중 한쪽만 교정된 비대칭 비교가 되어 지금보다 나빠진다(실측: 회전만 켜면 원감점 -55.3 -> -62.4, 정은지 자기비교 100 -> 60). 되돌릴 때도 둘 다: 이 값을 0 으로 + reference/_release.activeCandidate 를 None 으로. 실측 근거 = .planning/quick/260917-hjy-reference-drift-all11/. 켜지면 PR_INVERSION_ENABLED 보다 우선하고 PR 워프는 돌지 않는다(3패스 금지)
# quick-260920-m3r — mode3 채점에 기준 선수 각도 축을 건다. **기본 OFF, 일부러 안 켰다.**
# 켜려면 아래 줄의 주석을 벗기고 이 파일을 Pod 볼륨으로 복사한 뒤 재기동한다(배포 불필요).
# ★켜기 전 학생 영상으로 세 관문을 통과해야 한다 — 하나라도 안 되면 켜지 마라:
#   1. 같은 학생의 두 영상이 같은 기준에 일관되게 붙나
#   2. 강사 O/X 가 발전 방향과 일치하나
#   3. 카메라 각도가 바뀌어도 견디나
# 되돌리기 = 이 줄을 다시 주석 처리 + 재기동. 저장된 doc 은 안 바뀐다(재분석해야 반영).
# 근거·실측 = .planning/quick/260920-m3r-mode3-reference-axis/SUMMARY.md
# export MODE3_REFERENCE_RELATIVE_ENABLED=1
export RTMW_DETERMINISTIC=1  # 08-08 렌더 정렬 비결정성 뿌리 수리 — 채점(rtmw_engine)+렌더 정렬(compare_align.build_model) 세션 양쪽 결정론. 미주입=OFF 함정(같은 영상이 매 실행 다른 정렬 → 리그 판정이 운에 걸림). rollback: 이 줄 삭제
export RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx
export YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx
export RTMW_DEVICE=cuda
export FIREBASE_SA_PATH=/workspace/firebase-sa.json
export LD_LIBRARY_PATH=/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/dist-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH
cd /workspace/SunityMotion/backend
export PYTHONPATH=shared/python:.

# RUNPOD_AUTH_TOKEN from Lambda env so app->Lambda->Pod token matches (함정 24/25)
RTOK=$(python3 -c "import boto3; print(boto3.client('lambda', region_name='ap-northeast-2').get_function_configuration(FunctionName='sunity-motion-pilot-pipeline')['Environment']['Variables'].get('RUNPOD_AUTH_TOKEN',''))")
export RUNPOD_AUTH_TOKEN="$RTOK"
echo "RUNPOD_AUTH_TOKEN len: ${#RUNPOD_AUTH_TOKEN}"

# Gemini 기술 인식기 활성 (belle: Gemini 상시 사용). 키는 SSM 에서 주입.
# 모델 rotation(2.5 vision / 3.5 flash / 3.1 pro)은 코드/SSM resolve_model 가 담당.
export RECOGNIZER_BACKEND=gemini
GKEY=$(python3 -c "import boto3; print(boto3.client('ssm', region_name='ap-northeast-2').get_parameter(Name='/sunity/motion/gemini-api-key', WithDecryption=True)['Parameter']['Value'])")
export GEMINI_API_KEY="$GKEY"
echo "GEMINI_API_KEY len: ${#GEMINI_API_KEY}"

pkill -f "uvicorn.*server:app" 2>/dev/null || true
sleep 1
find shared/python/sunity_shared -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
find runpod_inference -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

nohup uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1 > /tmp/runpod_server.log 2>&1 &
echo "SERVER_PID $!"

# ── Lambda/SSM 주소 자동 동기 (quick-260919-t2v, belle 2026-09-19) ────────────
# belle: "pod 주소는 매일매일 새롭게 하는데" — Pod ID 는 재생성마다 바뀌는데
# Lambda RUNPOD_ANALYZE_URL 은 Pod 생성의 부수효과로 안 바뀐다. 손으로 맞추는
# 절차는 빠뜨리면 **분석이 통째로 실패**하고(폴백 없음), 실제로 빠뜨려서 라이브
# Lambda 가 3세대 전 Pod(elevev58iv4mox)을 가리키고 있었다(2026-09-19 실측).
# → 주소를 **아는 쪽**(=이 Pod)이 직접 쓴다. 사람 절차에서 제거.
#
# health 통과 뒤에 쓴다 — 모델 로딩에 실패한 Pod 으로 Lambda 를 돌려놓으면
# "주소는 맞는데 분석은 실패"라는 더 나쁜 상태가 된다(fail-closed).
sync_endpoint() {
  local url="https://${RUNPOD_POD_ID}-8000.proxy.runpod.net/analyze"
  for _ in $(seq 1 60); do
    if curl -sf -m 5 http://127.0.0.1:8000/health 2>/dev/null | grep -q '"pipeline_loaded": *true'; then
      python3 - "$url" <<'PY'
import sys, boto3
url = sys.argv[1]
fn = "sunity-motion-pilot-pipeline"
lam = boto3.client("lambda", region_name="ap-northeast-2")
cfg = lam.get_function_configuration(FunctionName=fn)
env = dict(cfg.get("Environment", {}).get("Variables", {}))
if env.get("RUNPOD_ANALYZE_URL") == url:
    print(f"endpoint_sync 이미 일치 {url}")
else:
    env["RUNPOD_ANALYZE_URL"] = url          # 나머지 키 보존 — 통째 치환 금지
    lam.update_function_configuration(FunctionName=fn, Environment={"Variables": env})
    print(f"endpoint_sync Lambda 갱신 {url}")
ssm = boto3.client("ssm", region_name="ap-northeast-2")
for name, val in (("/sunity/motion/runpod-analyze-url", url),
                  ("/sunity/motion/runpod-pod-expected", "up")):
    ssm.put_parameter(Name=name, Value=val, Type="String", Overwrite=True)
print("endpoint_sync SSM 갱신 (pod-expected=up)")
PY
      return 0
    fi
    sleep 5
  done
  echo "endpoint_sync SKIP — health 미통과(5분). Lambda 는 종전 값 유지(fail-closed)." >&2
  return 1
}
if [ -n "${RUNPOD_POD_ID:-}" ]; then
  ( sync_endpoint ) &
else
  echo "endpoint_sync SKIP — RUNPOD_POD_ID 없음(로컬 실행?)" >&2
fi
