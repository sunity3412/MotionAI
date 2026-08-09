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
export GEMINI_MOMENT_MODEL=gemini-3.5-flash  # 27-08 D-05 — moment extractor 만 Flash. veto 는 GEMINI_MODEL 체인(Pro) 유지 (rollback: 줄 삭제)
export GEMINI_SPOTCHECK_MODEL=gemini-3.1-pro-preview  # 32-13 스팟체크 판정 모델 (스모크 확정 — 스왑 시 이 줄만)
export PR_INVERSION_ENABLED=1  # 32-15 PR 인버전 2-pass 보정 — 제한 게이트 PASS(invert 46.8%↑, power-spin detect False) 후 on. rollback: 이 줄 삭제
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
