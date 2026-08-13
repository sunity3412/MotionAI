# 왼무릎 신규 발굴 장부 — 사전 박제 (quick-260813-wif)

**이 페이지는 판정 재료다 — 판정은 belle 몫.** 아래 "실행자 추천"은 belle 판정
**전에** git 커밋으로 박제된다 (이력이 증인). freeze 상속 승격 경로 실적 장부의
**1번째 행**이 이 사이클이다 (memory freeze-inherit-is-fallback-not-goal —
freeze 상속은 실패로 강제된 바닥, 목표 = 시스템이 스스로 옳은 순간을 잡는 것).

## 기계 증명 요지

- 데이터 좌표: uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2` / doc `p34fresh1786628533`
  (u8i Pod 실증 doc, Firestore 실조회) / record `r04:angle_vs_reference__left_knee`
  (감점 -8.8) / 기준 `ref-pdshape`. 영상 = S3 read-only 회수 캐시, align =
  운영 build_align + P35 트랙 replay (프레임 수 272/237 정확 일치 = 영상 정체성
  게이트 PASS).
- 게이트 임계 = 260811-ii0 SWEEP-REPORT §2 확정값 그대로 (card_gates 모듈 상수
  임포트 — hold<60도/초 3창 Theil-Sen 최소 · pose<0.85 · poleDiff<0.375 몸통 ·
  conf>=0.35). **이 사이클에서 임계 재튜닝 0.**
- 초 환산: 스캔/게이트 = align 15fps 타임베이스 (재추출 정본 — xa1 R2 운영 실증,
  캐시 프레임수/길이 유도 교차검증 user 15.001/ref 15.031 = candidates.json meta).
  카드 라벨 = 측별 실효 fps (u8i label_fps). **9.0/18.0 라벨 분모 사용 0.**
- 스캔: 사용자 클립 전 구간(272프레임) 홀드 판정 — 통과 124프레임, 1초 버킷
  18후보. 짝 = align 매핑 이웃 창 +/-2s (시퀀스 순서 제약 — 전역 포즈 유사도
  최소 선택 금지, nh4 교훈 명문화) + kpo 의미론 짝(ref claim=extended 한정 포즈
  최소) 병기. 전표 = [evidence/candidates.json](evidence/candidates.json).
- frames-before-numbers: 후보 전신 스틸 64장 + 눈 크롭 8장 + 카드 2장 전건
  실행자 Read 육안 확인 — [evidence/VISUAL-REVIEW.md](evidence/VISUAL-REVIEW.md).
- 기계 눈: card_gates.machine_eye (gemini-3.5-flash, 관절 마킹 크롭, 좌우 이름
  금지, 2단 판정) — 실호출 10회 (상한 16/record 코드 강제, 로그 =
  [evidence/eye_calls.log](evidence/eye_calls.log), 원장 =
  [evidence/eye_ledger/](evidence/eye_ledger/)).
- 렌더 = 운영 헬퍼(`app._run_gated_card_inherit`) 그대로 — 확정 문법 (display_anchor
  align 단일 출처 + B 스펙 angle_bake + label_fps). **새 문법 발명 0, 스타일
  파라미터 신설 0.** 같은 입력 2회 재렌더 md5 동일 (결정론,
  [evidence/render_verdict.json](evidence/render_verdict.json)).

---

## 후보 1 — cand13b (u 12.87s / r 12.40s) : kpo 인증 장면의 자율 재발견

카드: [evidence/cards/cand13b_u12.8667s_r12.4s_zoom_angle_vs_reference__left_knee.png](evidence/cards/cand13b_u12.8667s_r12.4s_zoom_angle_vs_reference__left_knee.png)
전신 짝: [학생 12.87s](evidence/stills/cand13b_user_12.8667s.jpg) ·
[기준 12.40s](evidence/stills/cand13b_ref_12.4s.jpg)

- 게이트: hold 학생 21.7도/초 PASS + 기준측 hold PASS (양측 홀드) · pose 0.417 ·
  poleDiff 0.235 · conf 양측 성립.
- 기계 눈: user bent->bent/**leg** (conf 0.9) + ref extended->extended/**leg**
  (conf 0.95) — **양측 확정 PASS** (kpo 왼무릎 인증과 동일 의미론).
- 육안: 학생 = 역립에서 폴측 무릎 접힘 + 반대 다리 수평 신전 / 기준 = 같은 역립
  국면에서 폴측 다리 완전 신전. "다리 안 폄" 결함이 같은 요소 안에서 읽힌다.
- **kpo 실적 짝과의 관계 = 재발견.** kpo 인증 짝 (u 12.80 / r 12.24, belle 육안
  인증)에서 u +0.067s / r +0.16s — 같은 홀드 구간의 이웃 프레임. 이번 스캔은
  kpo 좌표를 입력받지 않고 전 구간 스캔 + 게이트만으로 이 순간에 도달했다
  (후보 버킷 12.07~12.93s 가 kpo 12.80 을 포함).
- 카드 문법 주석: user 측 left_ankle conf 0.489 < 0.5 게이트로 **V 베이크 양측
  생략** (omitted:user_gate — 정직한 침묵). 카드 = 링 + 장면 대조. 라벨 12.9s =
  실효 fps 환산 정합.

## 후보 2 — cand02b (u 1.53s / r 2.33s) : 신규 발굴 (초반 오픈 요소)

카드: [evidence/cards/cand02b_u1.5333s_r2.3333s_zoom_angle_vs_reference__left_knee.png](evidence/cards/cand02b_u1.5333s_r2.3333s_zoom_angle_vs_reference__left_knee.png)
전신 짝: [학생 1.53s](evidence/stills/cand02b_user_1.5333s.jpg) ·
[기준 2.33s](evidence/stills/cand02b_ref_2.3333s.jpg)

- 게이트: hold 학생 28.3도/초 PASS + 기준측 hold PASS · pose 0.760 (임계 0.85
  이내 — 거리의 상당분이 결함 그 자체) · poleDiff 0.009 · conf 양측 성립.
- 기계 눈: user bent->bent/**leg** (0.95) + ref extended->extended/**leg** (0.95)
  — **양측 확정 PASS**.
- 육안: 학생 = 초반 오픈 요소에서 폴측 무릎 접힘 + 자유 다리 신전 / 기준 = 같은
  오픈 요소에서 폴측 다리 위로 신전 (트랙 172.9도). 요소 서사 = belle 라운드 5
  판정의 "학생 2초대 요소 <-> 정은지 2.4초대" 시간대와 정합 (align 곡선이 u1.53
  을 r2.3 대역으로 매핑 — 시퀀스 순서 보존).
- **kpo 실적 짝과의 관계 = 신규 순간** (kpo 12.8s 와 별개 요소의 동일 결함 재현).
- 카드 문법 주석: **angle_bake 양측 drawn** — 학생 패널 예각 V vs 기준 패널
  일자 V. 이번 산출 중 마크만으로 대조가 가장 잘 읽히는 카드.

## 눈 기각 2건 (재료 — 통과 조작 없음)

- **cand06b (u 5.27 / r 5.60)**: 수치 게이트 전건 통과였으나 기계 눈이 ref 측
  기각 — extended->extended/**arm** (마크가 폴 잡은 팔 겹침 영역,
  [크롭 실물](evidence/eye_ledger/06_cand06b_ref_left_knee_extended.png)).
  ii0 §3-2 마크-전위 구멍을 2단 판정이 막은 실물. 재시도/크롭 재조정 0.
- **cand10 (u 9.20 / r 9.53)**: 동형 기각 — ref extended->extended/**arm**
  ([크롭](evidence/eye_ledger/08_cand10_ref_left_knee_extended.png)). kpo Pod
  실측(r 10.27 기각)과 같은 구간·같은 유형.

## 대조 행 (기계 재계산 — 해석 없이 수치 그대로)

- **kpo 실적 짝 (u 12.80 / r 12.24)**: 재계산 = 학생 hold PASS(47.6도/초) ·
  **기준측 hold=moving** · pose 0.259 · 기준 트랙 각도 142.3(중간각). kpo 박제
  ("hold 양측 PASS · ref extended")와 **불일치** — 이웃 인덱스 프로브 전건
  moving (candidates.json contrast.kpo.refHoldNeighbors). 육안으로는 기준 12.27s
  폴측 다리가 신전으로 읽힘 — 트랙 keypoint 정밀도 한계 후보 (환각 게이트
  의제와 같은 뿌리). 이번 스캔의 cand13b(r 12.40)는 같은 홀드의 **게이트가
  성립하는 이웃 프레임**을 잡은 것.
- **ufb freeze r04 (u 10.50 / r 9.40)**: 재계산 hold=moving 220도/초 — ufb 침묵
  판정 재확인. 육안도 전환 중. **freeze 는 스캔에서 살아나지 않았다** (ufb
  판정과 정합 — freeze-only 구조에서 이 record 침묵은 옳았고, 회복은 신규
  발굴로만 가능하다는 전제의 실측 재확인).
- **검증 행 — cand04b (u 3.67 / r 2.33)**: 스캔이 belle 라운드 5 "B" 채택 짝
  (u 3.667 <-> r 2.4)을 독립 재생산. 그 순간 카드는 승인 코퍼스 B 스펙 회복
  카드로 이미 존재 — 신규 발굴 카드로는 미채택 (중복 발명 금지).

---

## 실행자 추천 (사전 박제 — belle 판정 전 커밋)

**추천 1안: 후보 1 (cand13b, u 12.87s / r 12.40s).**

근거:

1. **승격 경로의 시험 그 자체** — 이 사이클의 목적은 "시스템이 스스로 옳은
   순간을 잡는가"이고, cand13b 는 belle 이 kpo 에서 육안 인증한 바로 그 결함
   장면을 좌표 입력 없이 전 구간 스캔 + 게이트만으로 재발견한 것이다. 인증
   이력이 있는 요소라 요소 정체성 위험이 최소다 (3.867s 반려 교훈 — 짝은 기술
   요소 정체성 우선).
2. 게이트 수치가 후보 중 가장 안정 (pose 0.417 vs cand02b 0.760) + 기계 눈
   양측 leg 확정 + kpo 재계산 불일치(기준측 hold)까지 해소된 이웃 프레임.
3. 한계 정직 박제: 카드의 V 베이크는 user conf 게이트로 생략(링 대조만) —
   마크 가독성은 cand02b 가 우위다. 그럼에도 "옳은 순간"의 확실성이 이 장부
   의 1행에서는 우선한다고 판단했다.

cand02b 는 **동반 재료** (신규 순간 + V 대조가 가장 잘 읽히는 카드) — 채택
여부는 belle 몫이며, 둘 다 채택/둘 다 반려도 판정 결과로 그대로 적는다.

## belle 판정 기입란 (판정 후 기입 — 실행자 선기입 금지)

| 후보 | 순간 (u/r) | belle 판정 (채택/반려/보류) | belle 원문 |
|---|---|---|---|
| 후보 1 (cand13b) | 12.87s / 12.40s | | |
| 후보 2 (cand02b) | 1.53s / 2.33s | | |
| (기각분 처분 — cand06b/cand10 눈 기각 유지 여부) | 5.27/5.60 · 9.20/9.53 | | |

## 일치/불일치 집계 — freeze 상속 승격 경로 실적 장부

> 승격 조건 (기결론): 사전 박제 추천과 belle 판정의 **일치 실적 누적**만이
> freeze 상속(바닥)에서 자율 순간 선정으로의 승격 근거가 된다.

| 행 | 사이클 | 사전 추천 (커밋 해시) | belle 판정 | 일치 여부 |
|---|---|---|---|---|
| 1 | 260813-wif (이 사이클) | cand13b (본 문서 커밋) | (판정 대기) | (판정 대기) |

참고 — 과거 추천 대조 누적 (다른 축, xa1 장부에서 전재): E3 적중 후 번복 기각 ·
P2 기각 · P3r1 일치 · EV5 불일치 · 왼무릎 3.867s 불일치. 이 표는 **발굴 사이클
전용 신설 장부**라 위 이력은 행으로 세지 않고 참고로만 둔다.
