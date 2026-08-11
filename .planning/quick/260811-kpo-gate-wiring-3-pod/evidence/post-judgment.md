# 실물 판정 박제 — 로컬 검증 후 (frames-before-numbers, pre-judgment.md 와 대조)

판정 시각: 2026-08-11 (verify_local --check 완료, 카드 PNG 직접 열람 후)

## 카드 실물 판정 (evidence/cards/)

### zoom_angle_vs_reference__left_knee.png — **인증 (다른 홀드 순간, 육안 같은 국면 계열)**

- 실제 순간: user 12.80s / ref 12.24s (재정박 — 사전 예측 3.667/2.4 계열과 다름).
- 양 패널 육안: 둘 다 역립 홀드에서 다리를 폴 방향으로 올린 국면. **유저 = 무릎
  접힘(링이 굽은 무릎 위), 정은지 = 다리 완전 신전(링이 편 무릎 위)** — "다리 안 폄"
  결함이 그림으로 읽힌다. 정은지 12.24s = CONTINUE 예고 "신전 홀드 rep 180~200 부근
  (12.0~13.3s)" 정확히 그 구간.
- 게이트 수치: hold 양측 PASS · pose d=0.308 (k=12) · 기계 눈 양측 일치
  (user bent/leg + ref extended/leg).
- 사전 예측 (3.667/2.4) 이 아닌 이유 실측: 포즈거리 최소 랭킹에서 (3.67, 2.33) 은
  d=0.732 로 하위 — 눈 확정 가능한 후보 중 포즈 최소가 (12.80, 12.24). 눈은
  7.6s(유저 무릎 마크가 팔에 전위 — eyecrop_knee_u7.6.png)와 10.27s(기준 마크 전위)
  후보를 기각하고 이 짝을 확정했다.

### zoom_angle_vs_reference__left_elbow.png — **인증 (freeze 상속, 기결론 축)**

- 순간: user 5.30s / ref 5.13s (영상 정지 그대로 상속). 양 패널 같은 역립 국면,
  사이각 베이크 양측 드로잉 (수치 미노출 유지 — 기결론).
- 게이트: hold PASS 59도/초(경계 — ii0 박제 그대로) · pose 0.314 · eye bent 일치.
- **귀속(attribution=pole_proximity) 미부착 — 정답표 3항 미달 (박제)**:
  freeze 짝 (u80, r77)의 pole_diff = 0.1498 < POLE_MARGIN 0.15 (0.0002 차).
  이웃 프레임 실측 diff = 0.007 / 0.140 / 0.150 / 0.029 / 0.244 — **순간 측정이
  프레임 지터에 불안정**. UNIFY 부록 D 창설 실측(left_elbow 0.32 vs 0.18, diff 0.14)
  은 "비대칭 성립"으로 세었으므로 0.15 임계와 상충. 임계 완화는 curve-fit 금지라
  하지 않음 — 창 기반(분위수) 귀속 측정(_pole_prox_pair 지속-분리 설계 선례)이
  다음 사이클 수리 후보. belle 결정 항목.

### 왼골반 카드 — **부재 확인 (정답표 1항 성립)**

- freeze 는 align-peak(16.7s 절정 표시 재배치)이었으나 각도-주장 record 라 측정 짝
  (4.70s)으로 게이트 → hold FAIL 111도/초(3창 전부 — ii0 그대로) → 재정박 탐색
  전 클러스터를 기계 눈이 기각 (마크가 팔/몸통에 전위 — eyecrop_hip_*.png,
  eye_ledger left_hip 14건 기각) → 예산 소진 미방출. **정직한 침묵 경로 성립.**

### r01 right_elbow / r02 right_shoulder — 미방출 (정답표 무구속)

- 홀드 FAIL(112/98도/초 — ii0 그대로) + 재정박 후보 전건 눈 기각 (off_body /
  bent→extended 불일치 / 마크 전위). eye_ledger 에 기각 근거 크롭 전건 보존.

## 사전 예측 대비 오판 박제 (정직)

1. **왼무릎 재정박 순간 예측 실패**: (3.667/2.4) 계열 예측 → 실제 (12.80/12.24).
   포즈거리 랭킹 감각이 틀렸다 (직립·전위 순간이 포즈 최소를 지배). 눈 지연 평가
   + 클러스터 재시도가 이를 흡수 — 최종 실물은 정답표 취지(홀드 + 같은 국면 +
   결함 가독) 충족으로 판정.
2. **eyecrop_knee_u12.8 내 초기 육안 판정("팔") 철회**: 타이트 크롭에서 팔로
   보였으나 카드 전폭 크롭에선 힙에서 폴로 올라가는 다리의 굽은 무릎이 명확
   (몽타주 축소본 검수 금지 교훈의 변형 — 좁은 크롭 단독 판독 위험). Gemini
   판정(leg)이 맞았다.
3. **eye 호출 상한 ≤2 로는 성립 불가 실측**: 광역 keypoint 전위(유저 트랙)에서
   첫 후보 1개 시험 규칙이면 왼무릎이 원리적으로 죽는다 → record 당 상한 16
   (클러스터 선두만 + 캐시)으로 완화. 실측 사용량: 분석 전체 46호출.

## 승인 무회귀 (approved_verdict.json)

joint-scope 9/9 hold+pair 생존 — **ii0 SWEEP 표와 수치 동일** (elbow r00 19 /
r01 2 / r03 13 · pdshapefault r00 26 / r01(override) 18 / r02 2 / r03 18 ·
peterpan 53 · powerspin 8 도/초). align-peak 3건 비구속. 이식 등가성 성립.

## pytest 기준선

59 failed / 4149 passed (기준선 59 동일 — 신규 실패 0, 실패 파일 중 변경 함수
참조 0건 grep 확인. passed 증가분 +8 = 신규 card_gates 테스트).

## Pod 실증 (p34fresh1786433865 — 카드 PNG 직접 열람 후 판정)

- `/health` commitSha 2112975a == 로컬 HEAD. 서버 재기동(정본 start_server.sh,
  md5 리포 일치) + aws_env 소싱 (미소싱 1차 기동은 키 len 0 실측 → 재기동).
- **분석 완료 666.1s — status=done score=60** (같은 영상 재현성 보존, records 5건이
  이전 fresh doc 과 recordId/criterion/atVideoSec/points 소수점까지 동일).
- **card_gates verdict (운영 실행 로그 = 배선 증거)**: total=5
  survivors=[r00:inherit, r01:reanchor, r04:reanchor]
  dropped=[r02:hold=moving pair=pose_far, r03:hold=moving pair=match]
  reanchored=[r01, r04] eye_calls=40 → evidence/pod_verdict_log.txt
- **왼골반 카드 부재** (doc faultZoomComparisons confirmed = right_elbow /
  left_elbow / left_knee — left_hip 없음) — must_have 1 성립.
- **왼무릎 카드**: pod_cards/zoom_angle_vs_reference__left_knee.png 직접 열람 —
  로컬 검증 카드와 동일 짝 (u 12.8s 접힌 무릎 vs r 12.3s 신전 무릎, 같은 역립
  홀드 국면) — 환경 넘어 결정적 재현. must_have 2 성립.
- **왼팔꿈치 카드**: attribution=**pole_proximity** doc 부착 (Pod 자체 align 의
  pair 폴거리 차가 마진 통과 — 로컬 리플레이의 0.1498 근소 미달과 달리 성립).
  정답표 3항 Pod 에서 성립. 각도 수치 미노출 유지.
- renderedCompare done + freezes 5 (영상 스테이지 무회귀).
- r01 right_elbow 는 Pod 재정박 생존 (로컬은 기각 — Pod 자체 align 미세 차이 +
  Gemini 경계 판정. 정답표 무구속 축, 카드 실물 pod_cards/ 보존).
- 기계 눈 원장 40건 S3 보존 (results/.../eye/) → evidence/pod_eye_ledger/ 회수.
