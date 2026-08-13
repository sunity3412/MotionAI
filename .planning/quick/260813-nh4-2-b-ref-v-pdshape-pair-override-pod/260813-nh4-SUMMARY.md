---
quick_id: 260813-nh4
slug: b-spec-port-ref-v-fix-pair-override-pod
completed: 2026-08-13
commits:
  - 1f5fe48 feat(quick-260813-nh4) B 스펙 운영 이식 — V 베이크 align 폴백 seam 1/2
  - 289c90c test(quick-260813-nh4) align_bake B 스펙 게이트 4종
  - 96b4e07 docs(quick-260813-nh4) m0k B 재현 게이트 PASS — verify_port + 소생 6장 육안
  - 11a9e48 docs(quick-260813-nh4) Pod 실증 완료 — B 스펙 코드 96b4e07b 무회귀 증명
  - 3ac5df9 docs(quick-260813-nh4) belle 08-13 미세조정 1차 판정 3건 장부 박제
  - cdc5f39 docs(quick-260813-nh4) 왼팔꿈치 ref V 진단 — (b) 좌표 정확, 보정 없음 명기
  - 6db2a06 docs(quick-260813-nh4) 왼무릎 content-match — 모호 경로 종료 (재렌더 미수행)
---

# 260813-nh4 Summary — B 스펙 운영 이식 + Pod 실증 + ref V 진단 + 왼무릎 판정 재료

**한 줄**: belle 채택 B 스펙(V 베이크 align 폴백)을 운영 코드로 이식해 m0k
인증값을 monkeypatch 없이 전건 재현(소생 6/6·카드 8→10·elbow r01 정직한
침묵·md5 동일)하고 Pod fresh 재분석으로 무회귀(점수 60·records 15자리
동일)를 증명했으며, 왼팔꿈치 ref V 는 "좌표 정확"이 실측되어 보정 없음으로,
왼무릎 확정 장면은 content-match 가 3갈래 모호(벌림/접힘 요소 불일치 +
override 구조 제약)를 드러내 재렌더 없이 판정 재료 3장으로 종료했다.

**실행 순서 override (belle 지시)**: B 스펙 이식+push → Pod 실증 → 로컬 작업.
**Pod 의존 작업 완료 시점 = 2026-08-13T11:14Z (KST 20:14)** — 이후 Pod 는
꺼도 되는 상태 (터미네이트는 belle 몫).

## Task 1 — B 스펙 운영 이식 + m0k 재현 게이트

- **이식 형태**: `fault_zoom.align_bake_spec` 헬퍼 + `build_fault_zoom_comparisons`
  keyword-only `align_bake` payload (기본 None = 전 경로 byte-동일) + seam 2곳
  (rep12 스펙 None 측만 align 유도 / `_member_pts` valid-0 align 폴백, relaxed
  미주입) + app.py `_run_gated_card_inherit` payload 산출 (u_ai/r_ai 공식
  display_anchor 공용, hand→wrist 역정규화, conf 미달 = 키 부재 + `align_bake
  miss` conf 실값 로그). 동작명/분석 ID 분기 0.
- **verify_port.py 기계 판정 PASS** (운영 경로 그대로, monkeypatch 0):
  zoom md5 == m0k B 인증값 **전건** + survivors/dropped == ivs 정본 전건 +
  소생 6/6 (elbow r00·r03, pdshape r00·r02·r03, powerspin r02) + elbow r01
  drop 유지 (**align conf 실값 0.229~0.429 로그** — m0k 실측과 일치) + 카드
  8→10 + 승인 무회귀 hold 9/9·pair 9/9.
- 소생 카드 6장 전수 Read 육안 PASS (환각 0) — `evidence/PORT-EYE-VERDICT.md`.
- pytest **59 failed 기준선 동일** (4162 passed — 신규 테스트 +5 전부 pass),
  채점 산식 5파일 diff 0, 배선 추가 라인 동작명 리터럴 grep 0.

## Task 3 — Pod 실증 (mddy6gsqmt24ud)

- pull `0f999619→96b4e07b` + 서버 재기동(setsid 표준) + `/health` **commitSha
  == 새 HEAD** 4항목 PASS.
- fresh `p34fresh1786613939` (591.2s): **점수 60 유지**, 감점 -45.0, records
  atVideoSec **15자리 전건 hlv 인증값 동일**, survivors/dropped/display_anchor
  좌표 전건 동일 — **예상 밖 변동 0**.
- 운영 로그 실물: `card_gates verdict` + `display_anchor rid=r00/r03`(drop 0)
  + `fault_zoom_angle_bake drawn/drawn_hybrid` — `evidence/pod/`.
- 카드 2장 S3 read-only 회수 육안 PASS (팔꿈치 V 관절 위·골반 P3 하이브리드).
- **정직 기록**: 이 fresh doc 은 두 카드 모두 rep12 스펙 기성립이라 **B 폴백
  무발화가 옳다** (`align_bake miss` 0). 플랜의 "왼팔꿈치 카드 B 반영" 기대는
  이 doc 에 해당 자리가 없었음 — B 소생 실물 증거는 verify_port 승인 5동작
  스윕(같은 운영 코드)이 소유. Pod 의 역할 = 새 코드 운영 경로 무회귀 증명.

## Task 1(장부) — belle 판정 3건 박제

xa1 JUDGMENT.md append-only (+50/-0): ① B 채택("나머진 오케이다") ② 왼팔꿈치
ref V 위치 보정 지시 원문 ③ 왼무릎 3.867s 추천 반려 원문 전체 + **사전 박제
대조 불일치(기각) 기록** + 교훈(짝은 기술 요소 정체성/시퀀스 순서 우선, 포즈
유사도 보조 — 포즈 거리 랭킹이 닮은 다른 요소를 골랐다).

## Task 2A — 왼팔꿈치 ref V 진단: (b) 좌표 정확, 보정 없음

- 실측: V 3점 align conf 0.563~0.697 전부 게이트 통과, crosshair 육안 =
  팔꿈치 굽힘부 on-joint (`evidence/elbow_diag/`). **(a) 좌표 어긋남 아님.**
- 모호의 뿌리 = 접힌 팔 **저사이각 29.5도**(좁은 화살표로 읽힘) + V 가
  얼굴/머리카락 영역을 가로지름 + 팔꿈치가 턱 바로 옆.
- **보정 없음 명기**: V 이동 = 증상 덮기(금지) / 마크 크기·길이 = 튜닝
  금지(별건) / 팔꿈치 문법 변경 = belle fxx 라운드 3 기반려. 가독성 의제는
  마크 미세조정 라운드로 이월. verify_port 재실행 불요 (코드 무변경).

## Task 2B — 왼무릎 content-match: 모호 — 재렌더 미수행 (해석 금지)

- **픽셀 판정 명확**: 스크린샷 우측(ref) = **4.067s 접힘** (30fps 단봉 분리,
  2초대 최선 대비 22% 우위). 좌측 = user **2.87s 접힘**. 총길이 00:16 = ref
  원본 15.73s 정합.
- **갈림 실측 3가지** (`evidence/frame_match.json`):
  ① belle 실물 짝 = [접힘 2.87s | 접힘 4.067s], ② user **freeze(3.30s real)
  실물은 벌림(OPEN-V)** — ref 벌림 요소는 2.4s = **현행 반려 baseline 동일
  초**, ③ pair-override 는 ref 순간만 변경(user 변경 = 재정박, 경로 없음) —
  스크린샷 짝은 override 표현 밖이고, ref 4.067s 만 바꾸면 [벌림|접힘] =
  반려 사유 재생산.
- 처분: 판정 재료 3장 스테이징 (`staging/` A: freeze|4.067 접힘 / B:
  freeze|2.4 벌림 / C: 스크린샷 짝 그대로) + **belle 확인 1개** (A/B/C 중
  카드가 보여줄 짝 — C 는 freeze 상속 원칙 예외 승인 필요). override json·
  재렌더·리그는 확정 후 다음 단계.

## 보드 게시 재료 (게시는 오케스트레이터 몫 — 캡션 수치·이모지 0)

| 이미지 (절대경로) | 캡션 |
|---|---|
| /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-nh4-2-b-ref-v-pdshape-pair-override-pod/evidence/pod/cards/zoom_angle_vs_reference__left_elbow.png | Pod fresh 회수 — 왼팔꿈치 카드 (운영 경로, 새 코드) |
| /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-nh4-2-b-ref-v-pdshape-pair-override-pod/evidence/pod/cards/zoom_angle_vs_reference__left_hip.png | Pod fresh 회수 — 왼골반 P3 하이브리드 카드 |
| /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-nh4-2-b-ref-v-pdshape-pair-override-pod/evidence/elbow_diag/elbow_tight_crosshair.png | 왼팔꿈치 ref 좌표 진단 — 십자선 = align 좌표, 실제 팔꿈치 위 |
| /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-nh4-2-b-ref-v-pdshape-pair-override-pod/staging/knee_candidate_A_userfreeze_ref4.067s.png | 왼무릎 후보 A — user freeze 벌림, ref 접힘 |
| /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-nh4-2-b-ref-v-pdshape-pair-override-pod/staging/knee_candidate_B_userfreeze_ref2.4s.png | 왼무릎 후보 B — 벌림-벌림 (현행 반려 짝과 같은 초) |
| /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-nh4-2-b-ref-v-pdshape-pair-override-pod/staging/knee_candidate_C_screenshot_pair_user2.87_ref4.067.png | 왼무릎 후보 C — belle 스크린샷 실물 짝 (접힘-접힘) |

## LLM 학습 영향 (필수)

- **로컬**: Gemini 실호출 **0** — verify_port 는 grammar_round machine_eye
  스텁(6회, 더미 키), Task 2 는 PIL/ffmpeg 만.
- **Pod**: 운영 경로 실호출 **4건** (gemini-3.1-pro-preview x3 기술 인식 +
  gemini-3.5-flash x1, 눈 2회 포함). 추론만 — **학습 전송 0**. 눈 원장
  entries=2 S3 additive 보존 (Phase 22 씨앗).

## 한계 박제

- **왼무릎 미확정** — 모호 3갈래가 판정 재료로 남음 (belle 확인 1개). override
  재렌더·리그 게이트·pair_overrides.json 은 확정 후 (플랜 모호 경로 명기 준수).
- **왼팔꿈치 보정 없음** — belle 지시 ②의 처분 = "좌표 정확 실측 + 가독성
  의제 미세조정 라운드 이월". belle 이 가독성 자체의 즉시 수리를 원하면 그
  라운드에서 마크 문법 요소로 다뤄야 함 (튜닝 상수 금지 제약 때문).
- **S3 업로드 보류** — staging/ 실물은 로컬만 (belle 복귀 후 별도 1단계).
  세션 중 S3 쓰기 0 (GET 2건 + ls 1건만 — 운영 파이프라인의 자체 업로드는
  운영 경로 소유분).
- **÷9.0 표기 잔존** (카드 좌하 초 — kpo 유보, 무접촉).
- **Pod fresh doc 에서 B 폴백 무발화** — 이 doc 은 폴백 자리가 없었음 (정직
  기록). B 발화 실증은 승인 코퍼스 스윕이 소유.
- 어깨 계열 B 꼭짓점 = 관절 좌표 (승인 문법 겨드랑이 내분점과 구조 차이 —
  m0k 명기 유지, 미세조정 라운드 판정 대상).

## Deviations

- **[Rule 3 - 블로킹] Pod 서버 재기동 1회차 실패 수습**: 첫 SSH 가 pkill 후
  세션 단절(exit 255)로 끊겨 서버가 죽은 채 남음 — 재접속·표준 재기동으로
  해소 (POD-VERDICT.md 박제). 같은 명령 3회 재시도 규칙 내 (2회차 성공).
- **플랜 기대 1건 실측 교정 (문서화)**: Task 3 "왼팔꿈치 카드 B 스펙 V 반영"
  — fresh doc 실물은 rep12 기성립이라 폴백 자리 없음 (숨기지 않고 역할
  재명기: Pod = 무회귀 증명 / B 발화 = verify_port 스윕).
- **Task 2B 모호 경로 선택**: 플랜이 명기한 해석 금지 트리거(2초대 서사 vs
  4초대 실물 갈림 + override 구조 제약 발견) 발동 — 재렌더 대신 판정 재료.
- 실행 순서는 belle override (Pod 우선) 그대로 — 플랜 task 정의·게이트 무변형.

## Self-Check: PASSED

- 산출물 존재: verify_port.py / evidence/{port_verdict.json,
  sweep_verdict_port.json, PORT-EYE-VERDICT.md, sweep_cards 10장,
  elbow_ref_v_diagnosis.json, elbow_diag 5, frame_match.json, knee_match 4,
  pod/{POD-VERDICT.md, _fresh_nh4_full.log, cards 2}} / staging/{README + 스틸
  3} / JUDGMENT.md append(+50/-0)
- 커밋 존재: 1f5fe48 / 289c90c / 96b4e07 / 11a9e48 / 3ac5df9 / cdc5f39 /
  6db2a06 — 파일 삭제 0
- 게이트: verify_port PASS(전건) + pytest 59 failed 동일 + 산식 5파일 diff 0
  + 분기 grep 0 + Pod 점수 60/records 동일 + S3 쓰기 0
