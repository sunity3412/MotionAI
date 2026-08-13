# Pod 실증 (카드 초 라벨 실효 fps) — mddy6gsqmt24ud, 2026-08-13

**Pod 의존 작업 완료 시점: 2026-08-13T14:05Z 경 — 이 시점 이후 이 사이클의 Pod
의존 작업 없음.** (터미네이트/스톱 제안은 하지 않음 — belle 몫.)

## 절차 실측

1. push `6ded49cf..ebfad42c` (수리 3커밋: test 1eccf9cd + feat 5e857582 + 게이트
   ebfad42c) → Pod `git fetch && merge --ff-only`: `96b4e07b → ebfad42c`.
2. 서버 재기동 (setsid nohup 표준, `source aws_env.sh` 선행): 구 uvicorn 종료
   확인(`pgrep` 빈 출력) 후 start_server.sh 재기동.
3. `/health` 4항목 PASS (poll 1 즉시): **commitSha ==
   ebfad42cec3163908c85351f69000da779f80a02 (push 된 새 HEAD 와 일치)** ·
   RTMW_DETERMINISTIC=true · PR_INVERSION_ENABLED=true · modelLoaded=true.
   → `health.json`.
4. fresh 재분석 1회 (프로덕션 env 그대로): **`p34fresh1786628533`** (347.4s,
   status=done) — 소스 = belle 계정 pdshape 업로드 (nh4 fresh 와 동일 영상,
   원 doc 무접촉, 신규 analysis id 하위 파이프라인 자체 쓰기만).

## 판정 (기계 — nh4 fresh `p34fresh1786613939` 대조)

| 항목 | nh4 fresh | 본 실증 | 판정 |
|------|-----------|---------|------|
| score | 60 | 60 | == |
| records atVideoSec 15자리 | r00 5.301767255751917 / r01 6.102034011337112 / r02 13.804601533844616 / r03 4.701567189063021 / r04 10.503501167055687 | 전건 동일 | == |
| records points | -11.6/-11.6/-6.7/-6.3/-8.8 (합 -45.0) | 동일 | == |
| card_gates survivors | r00:inherit@u5.302/r5.13 · r03:inherit@u16.667/r15.20 | 동일 | == |
| dropped | r01/r04/r02 (hold=moving 등) | 동일 | == |
| display_anchor 좌표 | r00 (0.4148,0.6402)/(0.4008,0.6604) · r03 (0.3997,0.5123)/(0.4139,0.4766) | 소수 4자리 전건 동일 | == |
| angle_bake | left_elbow=drawn · left_hip=drawn_hybrid | 동일 | == |
| eye_calls / ledger | 2 / 2 | 2 / 2 | == |

**의도 변경 = 카드 초 필드/라벨만** (doc `faultZoomComparisons[]` 실측):

| 카드 | 구 (nh4 fresh doc) | 신 (본 fresh doc) | freeze 실초 | Δ(신-freeze) | 판정 (≤0.15s) |
|------|--------------------|--------------------|-------------|--------------|----------------|
| left_elbow userVideoSec | 5.889 ("5.9s") | **5.301767255751917 ("5.3s")** | u 5.302 | ~0.000 | PASS ★플랜 앵커 5.9→5.3s 적중 |
| left_elbow refVideoSec | 5.667 | 5.122196183461667 | r 5.13 | 0.008 | PASS |
| left_hip userVideoSec | 18.556 ("18.6s") | 16.70556852284095 ("16.7s") | u 16.667 | 0.039 | PASS |
| left_hip refVideoSec | 16.889 | 15.266153331101439 | r 15.20 | 0.066 | PASS |
| (advisory) left_shoulder userVideoSec | 8.0 | 7.202400800266756 | — (advisory, freeze 짝 없음) | — | 환산 반영 확인 |

- 신 userVideoSec(5.301767…)이 record atVideoSec 와 **완전 동치** — atVideoSec
  (U2 교정)과 카드 라벨이 같은 실효 rate 분모를 타게 되어 F-3 정합이 필드
  수준에서 성립.

## 판정 (육안 — 회수 카드 Read, cards/)

- `zoom_angle_vs_reference__left_elbow.png`: 좌하단 라벨 픽셀 **"5.3s"**
  (nh4 fresh 동일 카드 = "5.9s") — 마크(양 패널 V 꼭짓점 = 왼팔꿈치)·장면 구조
  동일. PASS.
- `zoom_angle_vs_reference__left_hip.png`: 라벨 픽셀 **"16.7s"** (구 "18.6s") —
  user P3 하이브리드 + ref V 구조 동일. PASS.

## 운영 로그 실물 (wiring-claims-need-log-evidence)

- `card_gates verdict analysis_id=p34fresh1786628533 total=5 survivors=[...] eye_calls=2` (99행)
- `display_anchor rid=r00 ... rid=r03 ...` (100·103행) — drop 0
- `align_bake miss` 0건 (nh4 와 동일 — payload 전 점 conf 통과)
- 전체 로그 = `_fresh_u8i_full.log` (130행)

## 비고 (정직 기록)

- renderedCompare freezes outSec 중 r01 = 15.67 (nh4 15.83) — 합성 비교 **영상**
  렌더의 기지 비결정(mp3 길이 변동, 08-09 실측 잔여 비결정 ②)이고 이 수리의
  대상(카드 초 라벨)·게이트 밖. 카드/점수/records/survivors 는 전부 동일.
- Gemini 실호출 (운영 경로 허용분): generateContent 4건 = gemini-3.1-pro-preview
  x3 (기술 인식기) + gemini-3.5-flash x1 (눈 machine_eye 2회 포함 사슬). 추론만,
  학습 전송 0. 눈 원장 S3 additive 보존 (entries=2).
- AWS 인프라 무변경 — SSM/Lambda URL 은 이미 동기 (재갱신 안내 금지 메모리 준수).
