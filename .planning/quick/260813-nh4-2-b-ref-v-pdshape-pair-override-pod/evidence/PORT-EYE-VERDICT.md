# B 스펙 운영 이식 — 소생 카드 6장 육안 전수 (frames-before-numbers)

판정자: 실행 에이전트 (원본 카드 전수 Read — 몽타주/축소본 검수 금지 준수).
대상 = verify_port.py 운영 경로 스윕 산출 (monkeypatch 0), md5 == m0k B 인증값
전건이라 픽셀은 m0k AB-EYE-VERDICT 와 동일 실물이다 — 그래도 운영 산출본을
다시 열어 판정했다 (남의 판정 상속 아님).

| # | motion | rid | criterion | 육안 판정 |
|---|--------|-----|-----------|-----------|
| 1 | elbow | r00 | right_elbow (12.3s) | PASS — user V 꼭짓점 = 굽힌 오른팔꿈치 관절 위, 두 가닥 = 전완/상완 방향. ref V 도 팔꿈치 자리. 환각 0 |
| 2 | elbow | r03 | right_knee (11.2s) | PASS — 역립 자세, V 꼭짓점 = 무릎 위, 다리 축 따라 성립. 저사이각이라 선+호로 읽힘 (m0k 관측 그대로 — 튜닝 별건) |
| 3 | pdshapefault | r00 | left_elbow (9.6s) | PASS(성립) — user V = 왼팔꿈치 위. **ref 패널 V 위치가 머리카락 영역과 겹쳐 모호** — belle 판정 ② 의 진단 대상 그대로 재현 (Task 2A 에서 실측 진단) |
| 4 | pdshapefault | r02 | left_shoulder (3.6s) | PASS — 양 패널 V 꼭짓점 = 어깨 관절 위 (B 구조 = 관절 좌표, 겨드랑이 내분점 아님 — m0k 명기 구조 차이) |
| 5 | pdshapefault | r03 | left_knee (4.1s) | PASS — 양 패널 V = 무릎 위. 짝 장면 자체(r2.4)는 belle 반려 대상 — Task 2B content-match 별건 |
| 6 | powerspin | r02 | left_shoulder (3.6s) | PASS — 양 패널 V 꼭짓점 = 어깨, 들어올린 팔 축 성립. 무로그 침묵 소생 2호 |

환각 좌표로 살아난 카드 **0/6**. 회복 불가 유지 = elbow r01
(align conf 실값 로그: user right_elbow=0.292 right_hip=0.229
right_shoulder=0.429 — 전부 < 0.5, 정직한 침묵이 옳음).

기계 게이트: port_verdict.json `pass: true` — zoom md5 == m0k B 전건,
survivors/dropped == ivs 정본 전건, 카드 8→10, 승인 hold 9/9 + pair 9/9,
Gemini 실호출 0 (스텁 6회).
