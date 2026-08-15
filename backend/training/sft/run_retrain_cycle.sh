#!/usr/bin/env bash
# Phase 22-12 주기 재학습 사이클 러너 — 데이터 플라이휠 "공부하기" 1커맨드 (belle 주 1회).
#
# 전부 기존 자산 orchestration: full_batch(라벨/조립) → run_sft(학습) →
# merge_and_quant(bf16 병합) → run_sft_gates(D-15 게이트) → promotion(단방향 래칫).
# 신규 코드는 이 러너 셸 + promotion.py(래칫) + 런북뿐이다.
#
# 실행 시점 제약: v7 등 진행 중 학습이 있으면 preflight serial lock 이 차단한다
#   (파이프라인 동시성 비안전 — 전 stage 순차 강제). Pod 전용(/workspace/*), nohup 무인.
#
# 사용 (Pod, cd /workspace/SunityMotion/backend):
#   PHASE22_BELLE_GREENLIGHT=1 nohup bash training/sft/run_retrain_cycle.sh all \
#     > /workspace/cycle_$(date -u +%y%m%d).log 2>&1 &
#   개별 stage: bash training/sft/run_retrain_cycle.sh [preflight|label|assemble|train|gates|promote]
#
# 시크릿: env 이름만 로그, 키 값 echo 금지 (T-22-12-04 / T-22-22 관례 승계).

set -euo pipefail

# ── 경로 앵커 (plan-checker WARNING 1 해소) ──────────────────────────────────
# cwd 를 단일 고정한다. 이후 모든 파일 인자(ledger/stats/report)는 $ROOT/backend/... 절대
# 경로로만 전달한다 — cwd=backend 에서 상대 "backend/..." 를 쓰면 backend/backend/... 로
# 깨져 SFT 완주 후 promote 가 실패한다.
ROOT="${SUNITY_ROOT:-/workspace/SunityMotion}"
cd "$ROOT/backend"

# distill/datagen/sft 의 bare import + `-m training.*` 동시 해석 (run_sft_gates 선례).
export PYTHONPATH="shared/python:training:.${PYTHONPATH:+:$PYTHONPATH}"

STAGE="${1:-all}"
BUCKET="${VIDEO_BUCKET:-sunity-motion-pilot-videos}"
OUT_DIR="${DISTILL_OUT_DIR:-/workspace/phase22_distill_out}"
CACHE_DIR="${COORDS_CACHE_DIR:-/workspace/phase22_coords_cache}"
SFT_OUT="${SFT_OUT_DIR:-/workspace/phase22_sft_out}"
REPORTS_DIR="${CYCLE_REPORTS_DIR:-/workspace/cycle_reports}"
LEDGER="$ROOT/backend/training/sft/promotion_ledger.json"   # 절대경로 앵커.
STATS_JSON="$OUT_DIR/cycle_label_stats.json"
WALL_FILE="$OUT_DIR/cycle_sft_wall.txt"
GATE_EXIT_FILE="$OUT_DIR/cycle_gate_exit.txt"
RUN_ID="cycle-$(date -u +%y%m%d-%H%M)"

mkdir -p "$OUT_DIR" "$REPORTS_DIR"

# ── stage 1: preflight ──────────────────────────────────────────────────────
preflight() {
  echo "[preflight] serial lock + greenlight + 디스크 + 코드 동기화"
  # (a) serial lock — 다른 학습/서빙 프로세스(v7 등) 비중첩 이중 방어.
  if pgrep -f "swift sft|vllm serve|full_batch" >/dev/null 2>&1; then
    echo "[중단] 다른 학습/서빙 프로세스 실행 중(v7 등) — 종료 후 재시도" >&2
    exit 1
  fi
  # (b) 과금 게이트 — 라벨 stage Gemini 과금은 belle 승인(greenlight) 후에만.
  if [ "${PHASE22_BELLE_GREENLIGHT:-}" != "1" ]; then
    echo "[중단] PHASE22_BELLE_GREENLIGHT=1 미설정 — 라벨 stage 과금은 belle 승인 후" >&2
    exit 2
  fi
  # (c) 볼륨 여유 디스크 — 쿼터 사건(유일본 어댑터 삭제 압박) 재발 방지.
  local avail_gb
  avail_gb=$(df -BG /workspace 2>/dev/null | awk 'NR==2 {gsub("G","",$4); print $4+0}')
  if [ -n "${avail_gb:-}" ] && [ "$avail_gb" -lt 30 ]; then
    echo "[중단] /workspace 여유 ${avail_gb}GB < 30GB — 정리 후 재시도" >&2
    exit 3
  fi
  # (c-2) 필수 CLI 존재 — assemble 의 canonical 백업이 `aws s3 sync` 를 쓴다.
  # 실측(2026-08-14 quick-260814-l5i): 새 Pod 에 awscli 가 없어 **라벨 453초(Gemini
  # 과금)를 태운 뒤** assemble 첫 줄에서 중단됐다. 과금 단계 앞에서 걸러야 한다.
  if ! command -v aws >/dev/null 2>&1; then
    echo "[중단] aws CLI 없음 — assemble 백업 불가. 설치: pip install awscli" >&2
    exit 6
  fi
  # (d) 최신 manifest/코드 동기화 (22-11 watch 배치가 자란 manifest 반영).
  git -C "$ROOT" pull --ff-only \
    || { echo "[중단] git pull --ff-only 실패 — 수동 동기화 필요" >&2; exit 4; }
  echo "[preflight] OK — greenlight=set, 여유 ${avail_gb:-unknown}GB"
}

# ── stage 2: label (신규 배치만 과금 — 행별 영속화가 기존 행 skip) ───────────
label() {
  echo "[label] full_batch 증류 — 신규 collection_batch 행만 과금(기존 행 skip=과금 0)"
  local start end
  start=$(date -u +%s)
  # ★stdout 을 그대로 $STATS_JSON 에 붓지 않는다 (2026-08-15 실측): rtmlib 이
  # 모델 로드 때 "load ... with onnxruntime backend" 를 **stdout** 에 찍어 파일 첫
  # 줄이 JSON 이 아니게 되고, promote 의 json.loads 가 char 0 에서 죽는다(리포트 소실).
  # 원문은 로그로 남기고 JSON 본문만 골라 담는다.
  local raw="$OUT_DIR/cycle_label_raw.log"
  python3 -m training.distill.full_batch \
    --out-dir "$OUT_DIR" --cache-dir "$CACHE_DIR" | tee "$raw"
  end=$(date -u +%s)
  python3 - "$raw" "$STATS_JSON" <<'PY' || echo "[label] 경고 — stdout 에서 JSON 을 못 찾았다. 원문: $raw"
import json, sys
raw, out = sys.argv[1], sys.argv[2]
text = open(raw, encoding="utf-8").read()
start = text.find("{")
if start < 0:
    raise SystemExit(1)
obj = json.JSONDecoder().raw_decode(text[start:])[0]
open(out, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
print(f"[label] stats JSON 추출 완료 -> {out}")
PY
  echo "[label] 경과 $((end - start))s — 결과 원장 $STATS_JSON (원문 $raw)"
}

# ── stage 3: assemble (백업 선행 강제 → 병합 재조립 → canonical 교체) ────────
assemble() {
  local ts
  ts=$(date -u +%y%m%d-%H%M)
  echo "[assemble] canonical 백업 선행 (교체 전 스냅샷 — T-22-12-01)"
  # 백업 s3 sync 가 exit 0 이어야만 다음 줄(교체) 진행. 백업 실패 = 사이클 중단.
  aws s3 sync "s3://$BUCKET/training/phase22/jsonl/" \
    "s3://$BUCKET/training/phase22/jsonl_backup_${ts}/" \
    || { echo "[중단] canonical 백업 실패 — 교체 차단(단일 진실 보호)" >&2; exit 5; }
  echo "[assemble] 기존+신규 accepted 병합 재조립 + canonical 교체 (--assemble --with-perturb --with-eye --upload)"
  # --with-eye (j24): 기계 눈 수확 원장(eye_manifest.json)의 admit 행을 4번째 트랙으로
  # 태운다. 크롭 PNG 가 아직 S3 에 없으면 assemble 이 fail-closed 로 멈춘다 —
  # 존재하지 않는 training/phase22/eye/*.png 를 가리키는 학습셋을 canonical 로 올리지
  # 않기 위한 의도된 차단이다. 해제 조건 = 크롭 업로드 사이클 선행(EYE-HARVEST-REPORT §6).
  python3 -m training.distill.full_batch \
    --out-dir "$OUT_DIR" --cache-dir "$CACHE_DIR" \
    --assemble --with-perturb --with-eye --upload
}

# ── stage 4: train (foreground — 사이클 자체가 nohup) ────────────────────────
train() {
  echo "[train] run_sft.sh QLoRA (foreground — wall time 계측)"
  local start end wall
  start=$(date -u +%s)
  bash training/sft/run_sft.sh
  end=$(date -u +%s)
  wall=$((end - start))
  echo "$wall" > "$WALL_FILE"
  echo "[train] SFT wall ${wall}s — 최신 ckpt:"
  ls -dt "$SFT_OUT"/*/checkpoint-* 2>/dev/null | head -1 || true
}

# 최신 SFT run 의 best ckpt 해석 (train/gates/promote 공용).
# ★`-merged` 를 반드시 제외한다 (2026-08-15 실측): gates 가 만든 병합본
# `<ckpt>-merged` 는 원본 ckpt 보다 **나중에 생기므로** `ls -dt` 의 첫 줄을 차지한다.
# 그러면 재실행 시 merged="<ckpt>-merged-merged" 가 되어 이미 있는 병합본을 못 찾고
# 병합을 다시 돌린다. 첫 실행에서는 병합본이 아직 없어 안 걸리는 **재실행 전용 함정**이고,
# 게이트가 인프라 문제로 죽은 뒤 이어받는 경로가 정확히 그 재실행이다.
_latest_ckpt() {
  ls -dt "$SFT_OUT"/*/checkpoint-* 2>/dev/null | grep -v -- '-merged$' | head -1
}

# ── stage 5: gates (bf16 병합 → 조건부 flashinfer env → D-15 게이트) ─────────
gates() {
  local ckpt merged cap
  ckpt="$(_latest_ckpt)"
  [ -n "$ckpt" ] || { echo "[중단] SFT 체크포인트 없음 — train stage 선행 필요" >&2; exit 6; }
  merged="${ckpt%/}-merged"
  if [ ! -d "$merged" ]; then
    echo "[gates] bf16 병합 (merge_and_quant.sh — AWQ/업로드 단계 실패는 예상, bf16 병합본만 필요)"
    # merge_and_quant 는 bf16 병합(step1) 후 AWQ 재양자화를 시도한다. autoawq 가 qwen3_vl
    # 미지원(22-07)이라 AWQ 단계에서 비0 종료할 수 있으나, 게이트가 소비하는 bf16 병합본
    # (<ckpt>-merged)은 step1 에서 이미 생성된다. 따라서 실패를 관용하고 병합본만 요구한다.
    bash training/export/merge_and_quant.sh "$ckpt" "$RUN_ID" \
      || echo "[gates] merge_and_quant 후반 단계 실패(예상) — bf16 병합본으로 진행"
  fi
  [ -d "$merged" ] || { echo "[중단] bf16 병합본 없음: $merged" >&2; exit 7; }

  # flashinfer 오탐 우회 env 는 Blackwell(compute_cap >= 12, sm_120)에서만 적용한다.
  # A100(sm_80) 등에 TORCH_CUDA_ARCH_LIST=12.0 을 강제하면 학습/서빙이 깨진다(T-22-12-06).
  cap="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -1 | tr -d ' ')"
  if [ -n "${cap:-}" ] && awk "BEGIN { exit !($cap >= 12) }"; then
    export VLLM_USE_FLASHINFER_SAMPLER=0
    export TORCH_CUDA_ARCH_LIST=12.0
    echo "[gates] Blackwell 감지(compute_cap=$cap) — flashinfer 오탐 우회 env 적용(2026-07-16 실증)"
  else
    echo "[gates] compute_cap=${cap:-미검출} (<12) — flashinfer env 미설정(비-Blackwell 보호)"
  fi

  echo "[gates] run_sft_gates.sh (PROMPT_MODE=aligned, SERIAL)"
  local gate_exit=0
  PROMPT_MODE=aligned bash training/sft/run_sft_gates.sh "$merged" || gate_exit=$?
  echo "$gate_exit" > "$GATE_EXIT_FILE"
  echo "[gates] 게이트 exit=$gate_exit (0=PASS 만 승격)"
}

# ── stage 6: promote (단방향 래칫 — PASS 만 current 전진) ────────────────────
promote() {
  local ckpt merged gate_exit wall report promo_rc
  ckpt="$(_latest_ckpt)"
  [ -n "$ckpt" ] || { echo "[중단] SFT 체크포인트 없음 — promote 불가" >&2; exit 8; }
  merged="${ckpt%/}-merged"
  gate_exit="$(cat "$GATE_EXIT_FILE" 2>/dev/null || echo 1)"
  wall="$(cat "$WALL_FILE" 2>/dev/null || echo 0)"
  report="$REPORTS_DIR/cycle_$(date -u +%y%m%d-%H%M).json"

  promo_rc=0
  python3 -m training.sft.promotion \
    --gate-exit "$gate_exit" \
    --ckpt "$merged" \
    --stats-json "$STATS_JSON" \
    --ledger "$LEDGER" \
    --meta-json "$OUT_DIR/jsonl/_meta.json" \
    --sft-wall-seconds "$wall" \
    --report-out "$report" || promo_rc=$?

  echo "=================== 사이클 비용 관측치 (은폐 금지) ==================="
  # 리포트 JSON 을 그대로 출력 — new_labeled/accepted/reject 분해/est_gemini_calls/
  # sft_wall_seconds/gates/promoted 전 필드 포함.
  cat "$report" 2>/dev/null || echo "(리포트 없음: $report)"
  echo "===================================================================="
  echo "ledger 변경은 git commit+push 대상 (Pod 작업 = push 한 단위): $LEDGER"

  # 러너는 FAIL 에서도 exit 0 로 정상 종료 — promoted 여부만 마지막 줄에 명시.
  if [ "$promo_rc" -eq 0 ]; then
    echo "PROMOTED — current 전진. Wave 3(22-08 서빙 swap) 진입 조건 충족."
  else
    echo "NOT PROMOTED — 기존 모델 유지. 게이트 FAIL 은 실패 아님(데이터는 쌓임, 다음 처방 근거)."
  fi
}

# ── dispatch (전 stage 순차 — 병렬 없음) ─────────────────────────────────────
case "$STAGE" in
  all)       preflight; label; assemble; train; gates; promote ;;
  preflight) preflight ;;
  label)     label ;;
  assemble)  assemble ;;
  train)     train ;;
  gates)     gates ;;
  promote)   promote ;;
  *) echo "usage: run_retrain_cycle.sh [all|preflight|label|assemble|train|gates|promote]" >&2; exit 64 ;;
esac
