#!/bin/bash
# 사용: svg_arm.sh <commit> <tag> — 서버를 그 커밋으로 재시작 → E2E mode1 1건 → 사후 단계 끝까지 대기 → 로그 보존
set -u
C=$1; T=$2
SP=/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/c3002e9e-5db0-4719-958c-2a5c5cce1389/scratchpad
SSH="ssh -o ConnectTimeout=30 -i $HOME/.ssh/id_ed25519 -p 38035 root@213.173.110.204"
POD=70k9sodi33enon
$SSH "pkill -f '[u]vicorn runpod'; sleep 3; cd /workspace/SunityMotion && git checkout -q $C && export RUNPOD_POD_ID=$POD && source /workspace/aws_env.sh && nohup bash /workspace/start_server.sh > /workspace/server_svg_$T.log 2>&1 < /dev/null & sleep 2; echo launched"
for i in $(seq 1 40); do H=$(curl -s --max-time 10 https://$POD-8000.proxy.runpod.net/health); echo "$H" | grep -q '"pipeline_loaded":true' && echo "$H" | grep -q "\"commitSha\":\"$C" && break; sleep 10; done
echo "[$T] health $(echo "$H" | grep -o '"commitSha":"[0-9a-f]\{8\}')"
cd /Users/kimtaesung/Dev/SunityMotion
backend/.venv/bin/python backend/scripts/e2e_app_path.py --video $SP/qmg_student.mp4 --mode mode1 --reference d8e849f70ee4430ab8a4aeb75cf673e4 --uid $(cat $SP/qmg_uid) 2>&1 | grep -v Warning | tail -1 > $SP/svg_$T.json
echo "[$T] e2e $(python3 -c "import json;d=json.load(open('$SP/svg_$T.json'));print(d['analysisId'],d['status'],d['overallScore'],d['elapsedSec'])")"
for i in $(seq 1 60); do N=$($SSH "grep -c 'INFO runpod_inference: 분석 완료' /tmp/runpod_server.log"); [ "$N" -ge 1 ] && break; sleep 15; done
$SSH "cp /tmp/runpod_server.log /workspace/svg_${T}_runpod_server.log"
echo "[$T] post done, log saved"
