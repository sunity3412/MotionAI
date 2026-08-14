#!/bin/bash
# Phase 22 데이터 플라이휠 — 주간 자동 사이클 (quick-260814-l5i).
#
# belle 지시 2026-08-14: "자동으로 좀 해놓으라니깐". 22-11(수집 러너)·22-12(재학습
# 루프)는 코드만 완성돼 있고 **한 번도 자동 실행된 적이 없었다** — 매번 사람이
# 트리거해야 했고 그래서 7/14 이후 한 달간 멈춰 있었다. 이 스크립트가 그 트리거를
# 대신한다.
#
# 범위 = **데이터 축적까지**. 학습(SFT)은 포함하지 않는다 — GPU Pod 이 상시 켜져
# 있지 않아 자동화하면 실패만 쌓인다. 학습은 Pod 이 있을 때
# `backend/training/sft/run_retrain_cycle.sh all` 로 별도 실행한다.
#
# 설치: launchctl load ~/Library/LaunchAgents/com.sunity.flywheel.plist
# 수동 실행: bash backend/scripts/flywheel_cycle.sh
# 로그: .planning/FLYWHEEL-LOG.md (1회 1행 append — 돌았는지/뭐가 늘었는지)

set -uo pipefail

ROOT="${SUNITY_ROOT:-/Users/kimtaesung/Dev/SunityMotion}"
PY="$ROOT/backend/.venv/bin/python"
MAPS="$ROOT/backend/training/data/eye_maps"
LOG="$ROOT/.planning/FLYWHEEL-LOG.md"
LOCK="/tmp/sunity-flywheel.lock"
STAMP="$(date '+%Y-%m-%d %H:%M')"

export AWS_PROFILE="${AWS_PROFILE:-sunity-motion}"
export GEMINI_KEY_PARAM="${GEMINI_KEY_PARAM:-/sunity/motion/gemini-api-key}"
export PHASE22_BELLE_GREENLIGHT=1   # belle 2026-08-14 상시 승인(수집 범위 = watchlist)

# ── 이중 실행 방지 (수집·원장 쓰기가 겹치면 JSON 이 깨진다) ───────────────────
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "[flywheel] 다른 사이클 실행 중 — 종료"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

cd "$ROOT" || exit 1
note() { printf '%s\n' "$1"; }

note "[flywheel] $STAMP 시작"

# ── 0. 코드 동기화 (실패해도 진행 — 로컬 작업 중일 수 있다) ──────────────────
git pull --ff-only --quiet 2>/dev/null || note "[flywheel] git pull 스킵(로컬 변경/충돌)"

rows_before=$(grep -c '"s3_key"' backend/training/data/manifest.json 2>/dev/null || echo 0)

# ── 1. 수집 — watchlist 신규분 (Gemini 선별 과금 발생) ───────────────────────
# --only 는 belle 이 범위를 넓히면 지우면 된다(현재 = 동의 확보된 정은지 계정만).
"$PY" backend/scripts/phase22_watch.py --run --only eunji > /tmp/_fw_watch.log 2>&1
watch_rc=$?
watch_new=$(grep -oE '신규 [0-9]+' /tmp/_fw_watch.log | tail -1 | grep -oE '[0-9]+' || echo 0)

# ── 2. 눈 원장 수확 + 재판정 (운영 분석이 돌 때마다 자란다) ──────────────────
"$PY" backend/training/datagen/harvest_eye.py --run --readjudicate --with-s3 \
  --motion-alias "$MAPS/motion_alias.json" \
  --analysis-motion-map "$MAPS/analysis_motion_map.json" \
  --motion-map "$MAPS/motion_map.json" \
  --consent-map "$MAPS/consent_map.json" > /tmp/_fw_harvest.log 2>&1
harvest_rc=$?
eye_rows=$(grep -oE 'rows_after [0-9]+' /tmp/_fw_harvest.log | tail -1 | grep -oE '[0-9]+' || echo 0)

# ── 3. admit 크롭 반출 (학습셋 조립의 fail-closed 를 여는 유일한 경로) ───────
"$PY" backend/training/datagen/harvest_eye.py --upload-media --run \
  > /tmp/_fw_upload.log 2>&1
upload_rc=$?
uploaded=$(grep -oE '업로드 [0-9]+' /tmp/_fw_upload.log | tail -1 | grep -oE '[0-9]+' || echo 0)

rows_after=$(grep -c '"s3_key"' backend/training/data/manifest.json 2>/dev/null || echo 0)

# ── 4. 원장 변경 커밋 (데이터가 리포에 남아야 다음 사이클이 이어진다) ────────
committed="no"
if ! git diff --quiet -- backend/training/data 2>/dev/null; then
  git add backend/training/data
  git commit -q -m "chore(flywheel): 주간 자동 사이클 $STAMP — 수집 +${watch_new} / 크롭 반출 ${uploaded}" \
    && git push -q 2>/dev/null && committed="yes"
fi

# ── 5. 1행 로그 append (돌았다는 증거 — 안 돌면 이 줄이 안 생긴다) ──────────
[ -f "$LOG" ] || cat > "$LOG" <<'HDR'
# 데이터 플라이휠 자동 사이클 로그

주 1회 자동 실행 기록. 줄이 안 늘면 자동화가 죽은 것이다(launchd 확인).
학습(SFT)은 이 사이클에 없다 — GPU Pod 필요, 별도 실행.

| 실행 시각 | 수집 신규 | 눈 원장 행 | 크롭 반출 | training 행 | 커밋 | rc(수집/수확/반출) |
|---|---|---|---|---|---|---|
HDR
printf '| %s | %s | %s | %s | %s → %s | %s | %s/%s/%s |\n' \
  "$STAMP" "$watch_new" "$eye_rows" "$uploaded" "$rows_before" "$rows_after" \
  "$committed" "$watch_rc" "$harvest_rc" "$upload_rc" >> "$LOG"

git add "$LOG" 2>/dev/null && git commit -q -m "chore(flywheel): 사이클 로그 $STAMP" 2>/dev/null \
  && git push -q 2>/dev/null

note "[flywheel] 완료 — 수집 +$watch_new / 눈 원장 $eye_rows / 크롭 반출 $uploaded"
