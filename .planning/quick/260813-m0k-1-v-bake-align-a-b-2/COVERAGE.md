# 확대 비교 커버리지 표 — 승인 5동작 감점 record 전수 13 rid (quick-260813-m0k)

belle 질문("영상별로 모든 확대 비교를 해주는 거지? 일부만 나타낸 것 같아서")의
실측 답. 출처 = ivs `sweep_verdict.json`/`measure.json` 정본(현행 상태) +
m0k `evidence/ab_verdict.json`/`measure_B.json`(B 실측) — 손 재유도 없음.
conf 값 = align 트랙 실측치(관절 순서: 꼭짓점/사지점/몸통점, 임계 0.5).

## 전수 표

| rid | criterion(관절) | 현행 상태 (ivs 정본) | B(align 유도) 결과 | conf 실값 / 사유 | 비고 |
|---|---|---|---|---|---|
| elbow r00 | angle_vs_reference__right_elbow | 방출 — V 미베이크(omitted:user_gate), 원 앵커 | **회복 — V 양패널 drawn** | seam1 user: 0.812/0.798/0.628 전부 통과 | 육안 PASS (AB-EYE-VERDICT #1) |
| elbow r01 | angle_vs_reference__right_shoulder | **침묵** — display_anchor drop side=user | **회복 불가 — B 도 동일 drop** | user 0.429/0.292/0.229 전부 임계 미달 (ref 0.680 통과/0.437/0.340) | 좌표가 진짜 없는 프레임 — 정직한 침묵 유지가 옳다는 실측 증거 |
| elbow r02 | (left_hip) | **dropped** hold=hold pair=pose_far | 동일 dropped (게이트 무접촉) | — (게이트 판정, 카드 단계 아님) | 정직한 침묵 |
| elbow r03 | angle_vs_reference__right_knee | **침묵** — rep12 양측 신뢰 0 (build 무로그 skip) | **회복 — 신규 카드 + V 양패널** | seam2+1: user 0.809/0.832/0.702 · ref 0.796/0.858/0.591 | 무로그 침묵 소생 1호, 육안 PASS |
| kipup r00 | split_angle | 방출 — legs 문법(omitted:legs_owned) | 동일 (md5 무변동) | angle 대상 아님 (다리 사이각 렌더 소유) | 회복 대상 아님 (설계) |
| pdshapefault r00 | angle_vs_reference__left_elbow | 방출 — ref 전신 폴백 무마크(omitted:ref_crop_relaxed) | **회복 — ref 부위 크롭 + V 양패널** | seam2+1 ref: 0.697/0.563/0.688 | belle 반려 카드 — 짝 후보 = PAIR-CANDIDATES.md 왼팔꿈치 (추천: 현행 9.4s 유지, B 회복이 처방) |
| pdshapefault r01 | angle_vs_reference__right_elbow | 방출 — V 양패널 (08-11 실눈 기각 이력, 스텁이라 방출) | 동일 (md5 무변동 — 무누출) | — | 눈 스텁 한계 그대로 |
| pdshapefault r02 | angle_vs_reference__left_shoulder | 방출 — V 미베이크(omitted:ref_gate), 원 앵커 | **회복 — V 양패널 drawn** | seam1 ref: 0.651/0.766/0.565 | 육안 PASS — 어깨 꼭짓점 자리(관절 vs 겨드랑이) 구조 차이 명기 |
| pdshapefault r03 | angle_vs_reference__left_knee | 방출 — ref 전신 폴백 무마크(omitted:ref_crop_relaxed) | **회복 — ref 부위 크롭 + V 양패널** | seam2+1 ref: 0.676/0.718/0.576 | belle 반려 카드 — 짝 후보 = PAIR-CANDIDATES.md 왼무릎 (추천: 3.867s) |
| peterpan r00 | angle_vs_reference__left_shoulder | 방출 — V 양패널 (08-11 실눈 기각 이력, 스텁이라 방출) | 동일 (md5 무변동) | — | 눈 스텁 한계 그대로 |
| powerspin r00 | leg_extension | 방출 — omitted:unmapped (angle 대상 아님) | 동일 (md5 무변동) | — | 회복 대상 아님 (설계 — legs 계열) |
| powerspin r01 | — | **dropped** no_freeze (승인 렌더에 이 record 의 정지 없음) | 동일 dropped | — | 정직한 침묵 |
| powerspin r02 | angle_vs_reference__left_shoulder | **침묵** — rep12 양측 신뢰 0 (build 무로그 skip) | **회복 — 신규 카드 + V 양패널** | seam2+1: user 0.645/0.796/0.501 · ref 0.724/0.787/0.631 | 무로그 침묵 소생 2호, 육안 PASS |

## 집계 (belle 질문의 답)

- 현행(A): 카드 8 / 침묵 5 (게이트 drop 2 + display_anchor drop 1 + 무로그
  신뢰 0 x 2). V 실물은 2장뿐.
- B(align 유도) 채택 시: **카드 10 / 침묵 3** — V 실물 8장 (기존 2 + 소생 6).
  남는 침묵 3 = 게이트 기각 2(hold/pair 불합·no_freeze) + 좌표 실부재
  1(elbow r01, conf 실값이 증거).
- 즉 "모든 확대 비교"는 아니고, **침묵은 전부 사유가 실측으로 채워진 정직한
  침묵**이다: 감점의 근거 프레임에 신뢰 좌표가 없거나(r01), 게이트가 짝/정지
  성립을 기각한 record(r02·r01) 만 카드가 없다. 나머지 10개 record 는 B 에서
  전부 확대 비교 카드가 나온다.

## 반영 경계 (이 사이클 무접촉)

- B 는 하네스 A/B 재료 — 운영 배선은 belle 채택 후 별도 사이클.
- 반려 2건의 장면 확정은 PAIR-CANDIDATES.md (pair-override 경로, 재정박 아님).
- 카드 초 표기 ÷9.0 잔존 (kpo 유보), 마크 길이·위치 튜닝 0 (별건).
