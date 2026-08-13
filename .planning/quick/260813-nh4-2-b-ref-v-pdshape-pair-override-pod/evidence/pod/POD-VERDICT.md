# Pod 실증 (B 스펙) — mddy6gsqmt24ud, 2026-08-13

**Pod 의존 작업 완료 시점: 2026-08-13T11:14Z (KST 20:14) — 이 시점 이후 Pod 는
꺼도 되는 상태** (belle 지시: Pod 필요 작업 최우선 완료 후 명기).

## 절차 실측

1. git pull: `0f999619 → 96b4e07b` (ff-only) — B 스펙 커밋 3개 반영.
2. 서버 재기동 (setsid nohup 표준, `source aws_env.sh` 선행): 구 uvicorn 종료
   확인 후 start_server.sh 재기동. ★첫 SSH 시도가 pkill 후 끊겨(exit 255)
   서버가 죽은 채 남았었음 — 재접속·재기동으로 해소 (log = _server_nh4.log).
3. `/health` 4항목 PASS: **commitSha == 96b4e07bfef0c9d037554c959f521ba927656a9f
   (로컬 새 HEAD 와 일치)** · RTMW_DETERMINISTIC=true · PR_INVERSION_ENABLED=true
   · modelLoaded=true.
4. fresh 재분석 1회: `p34fresh1786613939` (591.2s, exit 0) — 소스 = belle 계정
   pdshape 업로드 (hlv 와 동일 영상, 원 doc 무접촉).

## 판정 (hlv 인증값 p34fresh1786593512 대조)

| 항목 | hlv 인증 | 본 실증 | 판정 |
|------|----------|---------|------|
| score | 60 | 60 | == |
| 감점 합 | -45.0 | -45.0 (-11.6-11.6-6.7-6.3-8.8) | == |
| records atVideoSec | 15자리 | 전건 동일 (r00 5.301767255751917 등 5건) | == |
| card_gates survivors | r00@u5.302/r5.13, r03@u16.667/r15.20 | 동일 | == |
| dropped | r01/r04/r02 (hold=moving 등) | 동일 | == |
| display_anchor 좌표 | r00 (0.4148,0.6402)/(0.4008,0.6604) · r03 (0.3997,0.5123)/(0.4139,0.4766) | 소수 4자리 전건 동일 | == |
| angle_bake | left_elbow=drawn · left_hip=drawn_hybrid | 동일 | == |
| confirmed/advisory | 2/1 | 2/1 | == |
| eye_calls | 2 | 2 | == |

**예상 밖 변동 0** — 점수·survivors·records·앵커 좌표 전부 불변 (채점 무접촉
+ 게이트 무접촉의 Pod 증명).

## 운영 로그 실물 (wiring-claims-need-log-evidence)

- `card_gates verdict analysis_id=p34fresh1786613939 total=5 survivors=[...] eye_calls=2` (101행)
- `display_anchor rid=r00 joint=left_elbow u_ai=80 r_ai=77 ...` (102행) / `rid=r03` (105행) — drop 0
- `fault_zoom_angle_bake ... angle_bake=drawn` (left_elbow) / `drawn_hybrid` (left_hip)
- `align_bake miss` 로그 **0건** — 이 doc 은 payload 전 점이 conf 통과.
- 전체 로그 = `_fresh_nh4_full.log` (132행).

## 카드 육안 (S3 read-only 회수 → cards/)

- `zoom_angle_vs_reference__left_elbow.png` (5.9s): 양 패널 V 꼭짓점 = 왼팔꿈치
  관절 위 — PASS. hlv 인증 카드와 구조 동일.
- `zoom_angle_vs_reference__left_hip.png` (18.6s): user 패널 P3 하이브리드
  (쐐기+화살촉+V), ref 패널 V — PASS. hlv 인증 카드와 구조 동일.

## 정직 기록 — 플랜 기대와의 차이

플랜은 "왼팔꿈치 카드에 B 스펙 V 반영 (V 미베이크였던 자리에 align 유도 V
성립)"을 기대했으나, **이 fresh doc 의 두 카드는 hlv 시점에 이미 rep12 스펙으로
V 성립 상태였다** (hlv display_anchor.log 의 angle_bake=drawn 동일) — 즉 이
doc 에는 B 폴백이 발화할 자리가 없다 (align_bake miss 0, 폴백 무발화 = B 는
이 doc 에서 no-op 이 옳음). **B 소생의 실물 증거는 verify_port 승인 5동작
스윕**(같은 운영 코드, 소생 6/6 — pdshape r00 왼팔꿈치 9.4s ref V 회복 포함)이며,
Pod 실증의 역할은 "새 코드(96b4e07b)가 운영 경로에서 무회귀로 돈다"의 증명이다.
신규 카드 증가 0 (survivors 불변 — 예상 밖 변동 아님, 위 표).

## Gemini 실호출 (운영 경로만 — 허용분)

- generateContent 4건: gemini-3.1-pro-preview x3 (기술 인식기) +
  gemini-3.5-flash x1. 눈(machine_eye) 2회 포함, 학습 전송 0.
- 눈 원장: S3 `results/.../eye/` additive 보존 (entries=2, 서버 로그 108행+).

Pod 는 터미네이트하지 않음 (belle 몫 — 종료 제안 금지 메모리 준수).
