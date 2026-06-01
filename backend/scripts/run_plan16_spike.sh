#!/bin/bash
# Plan 01-16 T-6 belle Pod live mode 실행 스크립트.
# zsh paste line-wrap 함정 회피 — git repo 에 commit 후 Pod 에서 한 줄 실행.
#
# 사용법 (belle Pod):
#   cd /workspace/SunityMotion && git pull --ff-only origin main && bash backend/scripts/run_plan16_spike.sh
#
# 사전 조건 (Pod 환경, STATE.md 2026-06-01 박제):
#   - torch 2.4.1+cu124 / mmpose 1.3.2 / numpy 1.26.x / mediapipe 0.10.x
#   - /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin
#   - /workspace/rtmpose_weights/*.py + *.pth
#   - /workspace/models/pose_landmarker_heavy.task (Plan 16 신규 — wget 으로 다운로드 박제)
#   - AWS 자격증명 env (Plan 08 이래 박제)

set -e
cd /workspace/SunityMotion

STAMP=$(date +%Y%m%d_%H%M)
OUT="backend/research/spikes/reports/spike_measurement_trace_live_${STAMP}.json"

echo "[Plan 16 T-6] starting — ref-invert 단독, ~5분 (RTMPose+MB + MP+MB)"
echo "[Plan 16 T-6] out: ${OUT}"

python3 -m backend.research.spikes.spike_measurement_trace \
  --mode live \
  --motion ref-invert \
  --frame-index 88 \
  --hold-window 5 \
  --bucket sunity-motion-pilot-videos \
  --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \
  --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \
  --motionbert-root /workspace/MotionBERT \
  --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \
  --out "${OUT}"

echo "[Plan 16 T-6] complete — outputs:"
ls -lh "${OUT}" "${OUT%.json}.md" 2>/dev/null || true
