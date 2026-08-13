---
quick_id: 260813-m0k
slug: v-bake-align-ab-pair-recovery-coverage
completed: 2026-08-13
commits:
  - a28a0162 feat(quick-260813-m0k) V 베이크 align 단일 출처 A/B — 소생 6/6 육안 박제 + 미회복 conf 실측
  - 1655ab26 feat(quick-260813-m0k) 반려 2건 짝 국면 후보 스캔 + 스틸 + 추천 사전 박제
  - f0988a7a docs(quick-260813-m0k) 커버리지 실측 표 — 13 rid 전수, 침묵 3건 conf 실값 + B 결과
---

# 260813-m0k Summary — V 베이크 align A/B + 반려 짝 후보 + 커버리지 실측

**한 줄**: V 베이크 스펙을 rep12 대신 align 단일 출처에서 유도하는 B 하네스가
V 미베이크·침묵 회복 후보 6건을 전부 옳게 살렸고(꼭짓점 관절 위 6/6, 환각 0,
ref 무마크 2장 해소), 회복 불가 1건(elbow r01)은 align conf 실값(0.229~0.429)
으로 "정직한 침묵이 옳다"가 증명됐으며, 반려 2건의 짝 후보 스캔은 왼무릎 =
3.867s 교체 추천 / 왼팔꿈치 = 현행 유지(처방은 B 채택) 를 사전 박제했다 —
운영 코드·채점 무접촉 (survivors/dropped ivs==A==B 전건 동일이 기계 증거).

## Task 1 — V 베이크 A/B (핵심 실측)

- **A 런 무패치 동치 게이트 PASS**: zoom 카드 md5 + survivors/dropped 전건
  == ivs 정본 (기반 확인 후 B 진입 — BLOCKER 0).
- **B 소생 6/6, 옳게 소생 6/6** (AB-EYE-VERDICT.md 원본 카드 전수 Read):
  - V 미베이크 회복 4: elbow r00(user_gate), pdshape r02(ref_gate),
    pdshape r00·r03(ref_crop_relaxed — **ref 전신 무마크가 부위 크롭+V 로**).
  - 무로그 침묵 소생 2 (신규 카드): elbow r03, powerspin r02 (rep12 양측
    신뢰 0 이던 자리 — align conf 는 0.501~0.858 전부 통과).
  - 환각 좌표로 살아난 케이스 **0** — frames-before-numbers 충족.
- **회복 불가 3건 = 전부 사유 실측**: elbow r01 (user align conf
  0.429/0.292/0.229 — 좌표 실부재, B 도 drop 이 옳음), powerspin r00
  (unmapped — legs 계열, 설계상 비대상), kipup r00 (legs_owned — 동일).
- **채점·게이트 무접촉 기계 증거**: survivors/dropped **ivs==A==B 3원 전건
  동일** + 비대상 카드(pdshape r01, peterpan r00, kipup, powerspin r00)
  md5 무변동 (무누출). backend/·기존 하네스 원본 4파일 diff 0.
- 표현 관측(튜닝 0): 소생 V 중 3장이 저사이각 — 두 가닥이 선/화살표 하나로
  읽힘. 어깨 계열 B 꼭짓점 = 관절 좌표(승인 문법은 겨드랑이 내분점) — 채택 시
  결정 필요한 구조 차이로 명기.

## Task 2 — 반려 2건 짝 후보 (추천 사전 박제)

- **왼무릎 (u3.667/현행 r2.4)**: 전신 랭킹 1위 = **반려된 baseline 그 자체**
  (전신 거리 지표가 못 거르는 반려 — l0u 짝 게이트 의제와 정합). 추천 =
  **3.867s** — 부위 국소 거리 0.0837 (baseline 0.2081) 유일 대폭 개선 + 육안
  ref 왼무릎 접힘이 user 굽힘과 같은 장면 읽힘. 유보: ref 도 접힘이라 차이
  대비는 약해질 수 있음 (belle 화면감 판정 재료).
- **왼팔꿈치 (u8.556/현행 r9.4)**: 전 구간 스캔에서 유의 개선 없음 (전신 Δ
  0.013 수준, 육안 3후보 동일 국면). 추천 = **현행 9.4s 유지, pair-override
  불요** — rank1(8.133s)은 ref V 미성립(left_hand conf 0.479)이라 무마크
  재생산. 이 반려의 처방은 짝 교체가 아니라 **B 문법의 ref 크롭+V 회복**
  (Task 1 실물이 같은 9.4s 에서 이미 성립).

## Task 3 — 커버리지 (belle 질문의 실측 답)

- 13 rid 전수 표 = COVERAGE.md. 현행 카드 8/침묵 5 → **B 채택 시 카드 10/
  침묵 3** (V 실물 2장 → 8장). 남는 침묵 3 = 게이트 기각 2(pose_far·
  no_freeze) + 좌표 실부재 1(conf 실값 증거) — **전부 사유가 채워진 정직한
  침묵**.

## 구조 구분 (필수)

- **Task 2 는 재정박 부활이 아니다** — 운영 코드 무접촉, belle 장면 확정용
  판정 재료. 확정 시 다음 사이클에서 pdshapefault r01 선례(pairSrc=override,
  명시 짝 지정)와 같은 **pair-override 경로**로 반영.
- **Task 1 B 는 하네스 A/B 재료** — monkeypatch 2 seam 은 드라이버 프로세스
  안에만 존재. 운영 배선은 belle 채택 후 별도 사이클.

## 보드 게시 재료 (게시는 오케스트레이터 몫 — 캡션 각도 수치·이모지 0)

| 이미지 (절대경로) | 캡션 |
|---|---|
| /Users/Shared/sunity-finetune-260813/엘보트위스트_오른팔꿈치_전후시트.png | 전(원 앵커)/후(V 소생) — align 유도 스펙 B 실물, 꼭짓점 팔꿈치 위 |
| /Users/Shared/sunity-finetune-260813/엘보트위스트_오른무릎_전후시트.png | 전(카드 없음 — 무로그 침묵)/후(신규 카드 + V) — 침묵 소생 1호 |
| /Users/Shared/sunity-finetune-260813/피디쉐입_왼팔꿈치_전후시트.png | 전(ref 전신 무마크)/후(ref 부위 크롭 + V) — 반려 카드의 화면 격차 해소 실물 |
| /Users/Shared/sunity-finetune-260813/피디쉐입_왼무릎_전후시트.png | 전(ref 전신 무마크)/후(ref 부위 크롭 + V) — 짝 순간은 반려된 그대로, 장면 교체는 별도 판정 재료 |
| /Users/Shared/sunity-finetune-260813/피디쉐입_왼어깨_전후시트.png | 전(원 앵커)/후(V 소생) — 어깨 꼭짓점 자리(관절/겨드랑이) 구조 차이 판정 필요 |
| /Users/Shared/sunity-finetune-260813/파워스핀_왼어깨_전후시트.png | 전(카드 없음 — 무로그 침묵)/후(신규 카드 + V) — 침묵 소생 2호 |
| /Users/Shared/sunity-finetune-260813/피디쉐입_왼무릎_현행짝_반려기준선_2.4초.png | 현행 짝(반려) — ref 다리 뻗은 장면, user 굽힘과 다른 읽힘 |
| /Users/Shared/sunity-finetune-260813/피디쉐입_왼무릎_짝후보3_추천_3.9초.png | 추천 후보 — ref 왼무릎 접힘, user 와 같은 장면 읽힘 (부위 거리 최저) |
| /Users/Shared/sunity-finetune-260813/피디쉐입_왼무릎_짝후보2_0.7초.png | 참고 후보 — 진입 국면, 다른 읽힘 |
| /Users/Shared/sunity-finetune-260813/피디쉐입_왼팔꿈치_현행짝_반려기준선_9.4초.png | 현행 짝 — 전 구간에 유의하게 나은 순간 없음 (추천 = 유지) |
| /Users/Shared/sunity-finetune-260813/피디쉐입_왼팔꿈치_짝후보1_8.1초.png | 수치 1위 후보 — 단 ref 마크 미성립이라 무마크 재생산 (비추천 근거) |
| /Users/Shared/sunity-finetune-260813/피디쉐입_왼팔꿈치_짝후보2_10.6초.png | 참고 후보 — 현행과 사실상 동일 국면 |

B 소생 카드 원본 6장도 같은 폴더 (`*_B회복카드.png`, `*_B신규카드.png`).

## LLM 학습 영향 (필수)

**없음.** Gemini 실호출 0 — grammar_round machine_eye 스텁 + env 더미 키
상속 (eyeStubCalls A=6 / B=6, 전부 스텁 — 기계 확인값 ab_verdict.json).
학습 전송 0, 눈 원장 신규 적재 0 (스텁 산출물은 눈 원장이 아님).

## 한계 박제

- **눈 스텁**: 08-11 실눈 기각 이력 record 2건(pdshape r01, peterpan r00)이
  이번에도 방출됨 — 카드 문법 재료로만 볼 것 (눈 판정은 범위 밖).
- **마크 길이·위치 튜닝 0** (별건 — belle 미세조정 라운드). 소생 V 3장의
  저사이각 가독성 문제가 그 라운드 의제로 이월.
- **÷9.0 표기 잔존** (카드 좌하 초 — kpo 유보 3, 무접촉).
- **Pod 실증 범위 밖** — B 는 로컬 하네스 실물, 운영 배선·Pod 검증은 채택 후.
- **채점 무접촉** — survivors/dropped 3원 동일 + 산식 파일 diff 0 이 증거.
- 짝 후보 거리 지표는 2D 정규화 L2 (좌우 방향 미구분) — 스틸 육안이 보완,
  추천은 수치+육안 병기로만.

## Deviations

- **[Rule 3 - 블로킹] `_conf_probe_all` 순회 범위 수정**: probes.log 전 동작
  순회가 벤치 슬롯(pdshape correct/realupload — 구포맷 align refKp 부재)에서
  KeyError — 스윕 5동작 한정으로 교정 (run1 실측, 산출 무영향).
- **플랜 가정 1건 실측 교정 (문서화)**: `cg.NAME_ALT` 는 wrist→hand(rep12)
  단방향 — align17 에서 `{side}_hand` 조회는 미해석(None)임을 `_resolve`
  실물로 확인, 같은 NAME_ALT 데이터의 역방향(hand→wrist) 정규화로 처리
  (신규 매핑 발명 0, ab_render.py docstring 명기).
- **캐시 재fetch 불발생**: 플랜은 구세션 캐시 사망을 예상했으나 ivs 가 같은
  세션 scratchpad 를 썼음이 확인돼 영상/refmotion 캐시 재사용 — S3/Firestore
  신규 fetch 0 (동치 게이트가 md5 로 입력 동일성을 증명).

## Self-Check: PASSED

- 산출물 존재: ab_render.py / evidence/{ab_verdict.json, measure_A/B.json,
  sweep_verdict_A/B.json, ab_cards/{A,B,sheets}, pair_candidates.json,
  pair_stills/ 8장} / AB-EYE-VERDICT.md / PAIR-CANDIDATES.md / COVERAGE.md /
  /Users/Shared/sunity-finetune-260813/ 20장
- 커밋 존재: a28a0162 / 1655ab26 / f0988a7a — 파일 삭제 0
- 게이트: A==ivs 전건 + 3원 동일 + diff-0 (backend/ + 하네스 4파일) +
  Task1/2/3 기계 verify PASS + Gemini 실호출 0
