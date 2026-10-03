#!/bin/bash
# 사용: vsa_round.sh <ip> <port> <podId> <commit> <proxy 0|1> <tag> <pair...>
# 서버를 (commit, GEMINI_STUDENT_PROXY=proxy, RENDERED_COMPARE_ENABLED=0) 로 재시작 → 각 쌍을 고유 remux 사본으로 E2E(직렬) → 사후 끝 대기.
set -u
IP=$1; PORT=$2; POD=$3; C=$4; PX=$5; TAG=$6; shift 6
SP=/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/c3002e9e-5db0-4719-958c-2a5c5cce1389/scratchpad
SSH="ssh -o ConnectTimeout=30 -i $HOME/.ssh/id_ed25519 -p $PORT root@$IP"
$SSH "[ -f /tmp/runpod_server.log ] && cp /tmp/runpod_server.log /workspace/vsa_prev_\$(date +%s).log; pkill -f '[u]vicorn runpod'; sleep 3; cd /workspace/SunityMotion && git checkout -q $C && export RUNPOD_POD_ID=$POD GEMINI_STUDENT_PROXY=$PX RENDERED_COMPARE_ENABLED=0 && source /workspace/aws_env.sh && nohup bash /workspace/start_server.sh > /workspace/server_vsa_$TAG.log 2>&1 < /dev/null & sleep 2; echo launched"
for i in $(seq 1 40); do H=$(curl -s --max-time 10 https://$POD-8000.proxy.runpod.net/health); echo "$H" | grep -q '"pipeline_loaded":true' && echo "$H" | grep -q "\"commitSha\":\"$C" && break; sleep 10; done
echo "[$TAG] health $(echo "$H" | grep -o '"commitSha":"[0-9a-f]\{8\}') proxy=$PX"
cd /Users/kimtaesung/Dev/SunityMotion
for P in "$@"; do
  M=${P%%__*}; R=ref-$M
  SRC=$SP/vsa_fix/$P.mp4; DST=$SP/vsa_fix/tmp_${TAG}_$P.mp4
  ffmpeg -v error -y -i $SRC -map 0 -c copy -metadata comment="vsa-$TAG-$P-$(date +%s%N)" $DST
  N0=$($SSH "grep -c 'INFO runpod_inference: 분석 완료' /tmp/runpod_server.log")
  backend/.venv/bin/python backend/scripts/e2e_app_path.py --video $DST --mode mode1 --reference $R --uid $(cat $SP/qmg_uid) 2>&1 | grep -v Warning | tail -1 > $SP/vsa_runs/${TAG}__$P.json
  echo "[$TAG] $P $(python3 -c "import json;d=json.load(open('$SP/vsa_runs/${TAG}__$P.json'));print(d['analysisId'],d['status'],d['overallScore'],d['elapsedSec'])" 2>&1 | tail -1)"
  for i in $(seq 1 60); do N=$($SSH "grep -c 'INFO runpod_inference: 분석 완료' /tmp/runpod_server.log"); [ "$N" -gt "$N0" ] && break; sleep 10; done
  rm -f $DST
done
$SSH "cp /tmp/runpod_server.log /workspace/vsa_${TAG}_runpod_server.log"
echo "[$TAG] round done"
