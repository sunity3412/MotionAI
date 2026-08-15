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
# ★2026-08-15 범위 확대 (belle "좋아지는 기능이라면 언넝 진행해"): `--only eunji` 를
#   제거한다. 레지스트리에 유튜브 17채널이 활성인데 주간 수집은 정은지 IG 하나만
#   긁고 있었다 — 정은지 계정은 이미 다 긁어 매주 신규 0 이 나오는 중이었고, 재료
#   부족이 학습의 최대 병목이라는 것이 08-15 실측(학습셋 222행)으로 확인됐다.
#   미성년 채널(polesportkids)은 레지스트리에서 enabled=false 로 격리돼 있어 이
#   확대의 영향을 받지 않는다. 좁히려면 다시 `--only <alias>`.
"$PY" backend/scripts/phase22_watch.py --run > /tmp/_fw_watch.log 2>&1
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

# ── 3-2. 운영 분석 리포트 수확 + 영상 반출 (quick-260815-glc) ────────────────
# belle 2026-08-15 "분석할 때마다 학습할 여지가 있다면 하는거고" — 분석이 돌 때마다
# 결함 짚기 학습 재료가 자라는 유일한 트랙이다. 동의 축은 harvest_eye 와 같은 규율:
# 러너 계정·내부 계정은 admit, 앱 형태 uid 는 learningOptIn 실측 True 만 admit.
# ★베타 오픈 후 동의한 사용자의 분석이 여기로 자동 유입된다.
"$PY" backend/training/datagen/harvest_reports.py --run > /tmp/_fw_report.log 2>&1
report_rc=$?
report_rows=$(grep -oE 'rows_after [0-9]+' /tmp/_fw_report.log | tail -1 | grep -oE '[0-9]+' || echo 0)
"$PY" backend/training/datagen/harvest_reports.py --upload-media --run >> /tmp/_fw_report.log 2>&1
report_up_rc=$?
report_admit=$(grep -oE 'admit_after [0-9]+' /tmp/_fw_report.log | tail -1 | grep -oE '[0-9]+' || echo 0)

rows_after=$(grep -c '"s3_key"' backend/training/data/manifest.json 2>/dev/null || echo 0)

# ── 3-3. 재학습 시점 판정 (belle "때가 되면 너가 알려줘야 해", 2026-08-15) ────
# 왜 자동 판정인가: 재학습 시점을 문서에만 적으면 사람도 나도 까먹는다
# [[build-it-and-schedule-it-or-it-never-ran]]. 매주 스스로 재고, 넘으면 리포에
# 마커 파일을 남긴다 — 다음 세션에서 그 파일이 보이면 즉시 안내한다.
#
# 임계 근거 (2026-08-15 v29 실측): 재료 distill 79→171(2.2배)에 빈 골격 29→9,
# faults 0→2 였다. 게이트는 4동작 전부에서 결함을 짚어야 통과인데 v29 는 1동작뿐 —
# 관측 탄성상 최소 한 배수가 더 필요하다. 지금 재료로 또 돌리면 같은 자리에서 FAIL 이다.
#   · 영상 303 → 400편  (수집·재채굴 축)
#   · 또는 분석 원장 admit 25 → 60  (앱 사용이 늘면 이쪽이 먼저 참)
# 둘 중 하나만 넘어도 재학습 가치가 생긴다(OR).
TRAIN_DUE_VIDEOS=400
TRAIN_DUE_REPORT_ADMIT=60
DUE_FILE="$ROOT/.planning/TRAINING-DUE.md"
if [ "${rows_after:-0}" -ge "$TRAIN_DUE_VIDEOS" ] || [ "${report_admit:-0}" -ge "$TRAIN_DUE_REPORT_ADMIT" ]; then
  cat > "$DUE_FILE" <<DUEEOF
# 재학습 시점 도달 — $STAMP

플라이휠이 자동 판정했다. **다음 세션에서 belle 에게 알릴 것.**

| 축 | 현재 | 임계 |
|---|---|---|
| 수집 영상 | $rows_after | $TRAIN_DUE_VIDEOS |
| 분석 원장 admit | $report_admit | $TRAIN_DUE_REPORT_ADMIT |

## 돌리는 법
1. belle 이 5090 이상 Pod 추가 (EU-RO-1, 기존 볼륨)
2. \`bash backend/scripts/pod_doctor.sh\` — 결손 복구
3. train_venv312 없으면: \`TRAIN_VENV_ISOLATED=1 bash backend/training/sft/setup_train_venv.sh\`
4. 전 사이클: preflight → label → assemble → train → gates → promote
   (래퍼 예시 = .planning/CONTINUE-2026-08-16.md)

## 직전 판(v29) 성적 — 이번에 넘어야 할 선
빈 골격 9/29 · faults 2 · 4동작 중 1동작만 짚음 · 게이트 FAIL
DUEEOF
  note "[flywheel] ★재학습 시점 도달 — $DUE_FILE 생성 (영상 $rows_after / 분석 admit $report_admit)"
  osascript -e 'display notification "재학습 시점 도달 — 다음 세션에서 확인" with title "Sunity 플라이휠"' 2>/dev/null || true
else
  # 아직이면 마커를 지운다 — 낡은 마커가 남아 잘못 알리는 것을 막는다.
  rm -f "$DUE_FILE" 2>/dev/null || true
fi

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

| 실행 시각 | 수집 신규 | 눈 원장 행 | 크롭 반출 | 분석원장/admit | training 행 | 커밋 | rc(수집/수확/반출/분석) |
|---|---|---|---|---|---|---|---|
HDR
printf '| %s | %s | %s | %s | %s/%s | %s → %s | %s | %s/%s/%s/%s |\n' \
  "$STAMP" "$watch_new" "$eye_rows" "$uploaded" "$report_rows" "$report_admit" \
  "$rows_before" "$rows_after" \
  "$committed" "$watch_rc" "$harvest_rc" "$upload_rc" "$report_rc" >> "$LOG"

git add "$LOG" 2>/dev/null && git commit -q -m "chore(flywheel): 사이클 로그 $STAMP" 2>/dev/null \
  && git push -q 2>/dev/null

note "[flywheel] 완료 — 수집 +$watch_new / 눈 원장 $eye_rows / 크롭 반출 $uploaded / 분석 원장 $report_rows(admit $report_admit)"
