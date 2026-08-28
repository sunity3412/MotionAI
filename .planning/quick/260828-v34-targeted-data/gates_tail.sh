#!/bin/bash
# v34 gates 재개 (train 완주분 v38-20260828-024523 에서 병합부터). 08-28.
# 이번 판에서 밟은 두 함정을 여기 박아둔다:
#  1) 볼륨 쿼터 150G 초과 → 병합이 샤드 4/4 와 index.json 을 못 써서 조용히 잘렸다.
#     증상은 vLLM 의 "Following weights were not initialized" (visual.* 전멸).
#  2) 병합본에 베이스의 비전 전처리기 설정이 안 따라온다 — Qwen3-VL 은 VLM 이라
#     preprocessor_config / video_preprocessor_config / chat_template 이 있어야 뜬다.
set -u
cd /workspace/SunityMotion/backend || exit 3
source /workspace/aws_env.sh
export PHASE22_BELLE_GREENLIGHT=1
CU=/workspace/train_venv_cu124

# 병합 전 디스크 여유 확인 — 병합본 1벌 = 약 17G. 미달이면 조용히 잘리느니 죽는다.
USED=$(du -sg /workspace 2>/dev/null | cut -f1)
echo "[gates-tail] 볼륨 사용 ${USED}G / 150G (병합 여유 17G 필요)"
[ "$USED" -gt 130 ] && { echo "CYCLE_ENDED rc=12 (볼륨 여유 부족 — 미승격 -merged 정리 필요)"; exit 12; }

# 1차 = bf16 merge 생성 (cu124 에 vllm 없음 — vLLM 사망은 예상 동작, 관용)
TRAIN_VENV=$CU bash training/sft/run_retrain_cycle.sh gates || true

B=$(ls -d /workspace/hf_cache/hub/models--Qwen--Qwen3-VL-8B-Instruct/snapshots/*/ | head -1)
M=$(ls -dt /workspace/phase22_sft_out/*/checkpoint-*-merged 2>/dev/null | head -1)
[ -n "$M" ] || { echo "CYCLE_ENDED rc=13 (병합본 없음)"; exit 13; }
echo "[gates-tail] 병합본 = $M"

# 토크나이저 = 베이스 원본이 정본(LoRA 불변). transformers 5.x 가 저장한 list 형
# extra_special_tokens 를 4.57 이 못 읽는 문제 회피. + 비전 전처리기 3종 동반.
cp "$B/tokenizer_config.json" "$B/tokenizer.json" "$B/vocab.json" "$B/merges.txt" \
   "$B/preprocessor_config.json" "$B/video_preprocessor_config.json" "$B/chat_template.json" "$M/"

# 병합 완결성 검사 — 샤드 결번/index 부재를 여기서 잡는다(잘린 채 vLLM 에 넘기지 않는다).
python3 - "$M" <<'PY' || { echo "CYCLE_ENDED rc=14 (병합본 불완전 — 볼륨 여유 확인 후 재병합)"; exit 14; }
import sys, glob, json, re, os
m = sys.argv[1]
sh = sorted(glob.glob(os.path.join(m, "model-*-of-*.safetensors")))
if not sh:
    print("[검사] 샤드 0개"); sys.exit(1)
tot = int(re.search(r"of-(\d+)", os.path.basename(sh[0])).group(1))
idx = glob.glob(os.path.join(m, "*.index.json"))
print(f"[검사] 샤드 {len(sh)}/{tot} · index {'있음' if idx else '없음'}")
sys.exit(0 if (len(sh) == tot and idx) else 1)
PY

TRAIN_VENV=/root/gates_venv2 bash training/sft/run_retrain_cycle.sh gates || { echo "CYCLE_ENDED rc=10 (gates 실행 실패)"; exit 10; }
TRAIN_VENV=$CU bash training/sft/run_retrain_cycle.sh promote
echo "CYCLE_ENDED rc=$?"
