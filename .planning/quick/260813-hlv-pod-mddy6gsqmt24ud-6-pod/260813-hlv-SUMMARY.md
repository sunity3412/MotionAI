---
quick_id: 260813-hlv
slug: pod-mddy6gsqmt24ud-6-pod
completed: 2026-08-13
commits:
  - f84fff88 docs(quick-260813-hlv) Pod 재진입 6단계 증거 (health 4항목 + md5 + URL 재동기)
  - a5fb9a0c docs(quick-260813-hlv) 배선 실증 증거 (display_anchor/card_gates 로그 + 점수 60 대조)
  - a4bced58 docs(quick-260813-hlv) Pod 방출 카드 2장 회수 + fxx 픽셀 대조 + 육안 판정
---

# 260813-hlv Summary — Pod mddy6gsqmt24ud 재진입 6단계 + 선 문법 배선 Pod 실증

**한 줄**: 새 Pod mddy6gsqmt24ud 를 재진입 6단계 정본 절차로 기동·재동기(health 4항목
PASS + start_server.sh md5 일치 + SSM/Lambda URL 실측 재동기)하고, fxx 선 문법 운영
배선이 **운영 Pod 실분석에서 실제 호출됨**을 실행 로그 실물로 증명 — display_anchor
성립 2건 + card_gates verdict 가 fxx 로컬 인증값과 byte-동일, 점수 60 소수점까지
유지(채점 무접촉 Pod 실증), 방출 카드 2장 회수·픽셀 대조·육안 판정 완료.

## Task 1 — 재진입 6단계 실측표 (evidence/reentry/)

| 단계 | 실측 | 판정 |
|------|------|------|
| GPU | NVIDIA GeForce RTX 4090, 24564 MiB (nvidia-smi) | 기록 (gpu.txt) |
| 1. 코드 동기 | fetch + ff-only 5ddc1e3a → **0f999619** == origin/main, working tree clean | PASS |
| 2. 부트스트랩 | bootstrap_full.sh `[done]`, rtmw 352M + yolox 97M 가중치 확인 | PASS |
| 3. 서버 기동 | setsid 완전 분리, RUNPOD_AUTH_TOKEN len=64 / GEMINI_API_KEY len=53 (값 미출력), 단일 uvicorn PID 4713 | PASS |
| 4. health 4항목 | commitSha=0f999619... · RTMW_DETERMINISTIC true · PR_INVERSION_ENABLED true · modelLoaded true + `/analyze` 무토큰 **401** | PASS (health.json) |
| 5. md5 대조 | Pod /workspace/start_server.sh == 리포 정본 == `e7f224d648ef599270d14a6887bc7ae1` (덮어쓰기 불요) | PASS (md5.txt) |
| 6. URL 재동기 | SSM v31 + Lambda RUNPOD_ANALYZE_URL 둘 다 `https://mddy6gsqmt24ud-8000.proxy.runpod.net/analyze` **갱신 후 재조회 실측**, env 4키(FIREBASE_SA_PARAM/RUNPOD_ANALYZE_URL/RUNPOD_AUTH_TOKEN/VIDEO_BUCKET) 보존 | PASS (resync-after.txt) |

AWS 프로덕션 쓰기 = 계획대로 정확히 2건 (SSM put-parameter 1 + Lambda
update-function-configuration 1, --profile sunity-motion). 시크릿 값 로그/evidence 저장 0.

## Task 2 — 배선 실증 (evidence/wiring/)

**fresh 재분석**: `p34fresh1786593512` (uid fvcNXzEqKjgqVxRPVSj1iwFnIpn2, belle 원본
127a2a90 소스 — 이전 실증과 동일 영상, 원 doc 무접촉), 342.7s, exit 0, status=done.

**운영 로그 실물 (wiring-claims-need-log-evidence — display_anchor.log):**
- `display_anchor rid=r00 joint=left_elbow u_ai=80 r_ai=77 user=(0.4148,0.6402) ref=(0.4008,0.6604)`
- `display_anchor rid=r03 joint=left_hip u_ai=250 r_ai=228 user=(0.3997,0.5123) ref=(0.4139,0.4766)`
- `card_gates verdict analysis_id=p34fresh1786593512 total=5 survivors=['r00:inherit@u5.302/r5.13', 'r03:inherit@u16.667/r15.20'] dropped=[r01/r04:hold=moving pair=match, r02:hold=moving pair=pose_far] eye_calls=2`
- `display_anchor drop` = **0건**. angle_bake: left_elbow=`drawn`, left_hip=`drawn_hybrid`.

**fxx 로컬 인증값 대조 (fxx-cross-check.txt)**: survivors/dropped/display_anchor
좌표 전건 **byte-동일** (RTMW 결정론 ON 에서 freeze 순간 일치 기대 적중). 로그 나열
순서만 상이(Pod verdict r00 선행 vs fxx once1 r03 선행 — 값·구성 무차).

**점수 60 대조표 (score-compare.txt — 채점 무접촉 Pod 실증):**

| 항목 | 이전 실증 p34fresh1786458292 | 신규 p34fresh1786593512 | 판정 |
|------|------|------|------|
| overallScore / deductionBreakdown.final | 60 / 60 | 60 / 60 | 동일 |
| 감점 합 | -45.0 | -45.0 | 동일 |
| r00 left_elbow | -11.6 @ 5.301767255751917 | -11.6 @ 5.301767255751917 | 소수점 동일 |
| r01 right_elbow | -11.6 @ 6.102034011337112 | -11.6 @ 6.102034011337112 | 소수점 동일 |
| r02 right_shoulder | -6.7 @ 13.804601533844616 | -6.7 @ 13.804601533844616 | 소수점 동일 |
| r03 left_hip | -6.3 @ 4.701567189063021 | -6.3 @ 4.701567189063021 | 소수점 동일 |
| r04 left_knee | -8.8 @ 10.503501167055687 | -8.8 @ 10.503501167055687 | 소수점 동일 |

## Task 3 — 카드 회수 + 대조 + 육안 (evidence/cards/, EYE-VERDICT.md)

- **회수**: S3 `results/.../p34fresh1786593512/` 에서 방출 카드 2장(13:04 게이트 후
  재렌더 업로드분) `aws s3 cp` 회수.
- **md5 대조**: fxx 로컬 인증 카드와 **상이** — 원인 실측: 치수 동일(360x726),
  left_elbow 는 max Δ=3/255 전면 미세 노이즈(Δ>8 픽셀 0개), left_hip 은 Δ>8 이
  정확히 1픽셀(마크 선 가장자리 안티앨리어싱). 원인 = freeze 프레임 소스 디코드/
  리사이즈 반올림 차(로컬 하네스 vs Pod 프레임 캐시) — 기지 비결정 계열. 크롭
  기하가 1px 라도 어긋났으면 대면적 Δ>32 가 나와야 하는데 0 → **크롭 중심·마크
  좌표는 픽셀 정렬로 동일 증명**. 표시 좌표 배선 판정은 display_anchor 로그
  byte-동일로 md5 와 분리 성립.
- **육안 판정 (frames-before-numbers — 기대 사전 박제 후 개봉)**: 왼팔꿈치 = 양 패널
  기존 V + 꼭짓점 팔꿈치 관절 위 PASS(얼굴 관통 가닥 = belle 판정 스펙대로 유지),
  왼골반 = user 패널 P3 하이브리드 4요소(실선 V + 반투명 쐐기 + 화살촉 + 고스트
  점선) 전부 실물 확인 + ref 패널 기존 V PASS. 각도 수치는 양 패널 both-off
  (conf 게이트 기지 동작 — lockstep 불변식 유지, 배선 결함 아님).

## 한계 (이 사이클 완료 정의 아님)

- **belle 최종 육안 판정은 별건** — 이 카드 2장이 그 재료 (리포 evidence/cards/).
- 마크 위치 미세조정 라운드 미착수 (belle 라운드 3 판정 — 전체 완료 후).
- 카드 초 표기(5.9s/18.6s) = freeze 순간의 ÷9.0 계열 환산 잔존 — kpo 유보 기지 별건.
- 카드 png md5 는 로컬/Pod 간 비재현 (프레임 소스 디코드 노이즈 — 구조 차 0 실측).
  좌표·문법 판정은 로그와 픽셀 정렬로 분리 성립.
- Pod mddy6gsqmt24ud 는 계속 가동 중 (터미네이트/스톱 제안 안 함).

## LLM 학습 영향

- **Gemini 실호출 (운영 경로, 로그 실측)**: generateContent **4건** —
  gemini-3.1-pro-preview x3 + gemini-3.5-flash x1 (분석 1회분). 이 중 기계 눈
  freeze 방출 판정 = `eye_calls=2` (분석당 ~2회 수준 기대 적중), 나머지 = recognizer
  기술 인식. File API 업로드/삭제 잔여물 정리 로그 확인 (DELETE 200 x2).
- **학습 전송 0** — 추론 호출만. 사람/judge 점수 라벨 전송 0.
- **눈 원장**: `card_gates eye ledger 보존 entries=2` (S3 eye/ prefix) — Phase22
  씨앗 원장 누적 (기존 정책 그대로).

## Deviations

- Task 1 순서 최적화: md5 대조(5단계)를 서버 기동(3단계) 전에 수행 — 불일치 시
  재기동 1회를 아끼는 순서 변경일 뿐 검증 내용 동일 (일치라 덮어쓰기·재기동 불요).
- score-compare 필드 경로 수정: 플랜 명세에 없던 doc 스키마 확인
  (`result.overallScore` / `result.deductionBreakdown.records`) — 첫 조회가
  잘못된 최상위 키를 읽어 None 이 나왔고, 드라이버 스크립트 실물 대조로 교정
  (verify-the-target 위반 아님, 기록용).
- evidence/wiring/fxx-cross-check.txt 추가 (플랜 artifact 목록 밖) — survivors/
  dropped/anchor byte 대조를 기계 캡처로 남기기 위함.

## Self-Check: PASSED

- evidence/reentry/ 4파일 (gpu.txt, health.json, md5.txt, resync-after.txt) 존재
- evidence/wiring/ 3파일 (display_anchor.log, score-compare.txt, fxx-cross-check.txt) 존재
- evidence/cards/ 2장 + EYE-VERDICT.md 존재
- 커밋 f84fff88 / a5fb9a0c 존재 + Task 3 evidence 커밋
- `git status --porcelain backend app` 빈 출력 (리포 코드 무접촉)
