# 08-31 코드리뷰 후속 측정 (belle "재라")

리뷰(c2976102..HEAD, high)가 크레딧 소진으로 중단 — 확보된 후보를 실측으로 처분한다.
Pod 불필요 (Gemini 호출 + 저장 데이터).

## ② vision-sourced tol 우회 → 소음 감점 위험 = **기각 (N=1 → N=6)**

정타(잘된예시) 6편 × 기준 영상, `assess_fault_context_video` 실행:

| 동작 | status | supported_differences |
|---|---|---|
| peter-pan | candidate_verdict | 0 |
| power-spin | candidate_verdict | 0 (1차 Gemini 503 → 재시도) |
| climb | candidate_verdict | 0 |
| kip-up | candidate_verdict | 0 (08-31 수동 실행과 동일 — 재현성) |
| elbow-twist-sister | candidate_verdict | 0 |
| pdshape | candidate_verdict | 0 |

**정타에서 vision 은 결함을 아예 보고하지 않는다** → 감점 record 자체가 생기지 않아
tol 우회와 무관. "support 게이트가 노이즈 게이트" 주장이 N=6 으로 지지됨. 대조:
같은 경로가 kip-up **fault** 에서는 split 20° 를 보고했다(변별 유지).
★한계(정직 고지): 검증 대상은 **엘리트 정타**다. 중간 수준 학생 영상에서 소량 편차가
보고되는지는 미검증 — 실사용 doc 축적 후 재측정 대상.

## ⑤ 기준 doc joints3d 부재 → 무발화 = **기각**

11/11 기준 모션이 joints3d + 17 keys 보유. 현 데이터에서 무발화 0건.

## ★신규 발견 (측정 중) — 기준 좌표 평면 불일치 = **확인됨, 수리 필요**

| 평면 | 기준 모션 | 상체각 중앙값 |
|---|---|---|
| xy (정상) | climb 24.9° · combo 63.9° · elbow 111.1° · kip-up 8.1° · pdshape 151.9° · peter-pan 6.4° · power-spin 84.1° | 실측값 |
| **xz (y축 소실)** | **foxtop · foxtop-split · invert · sideway-spin** | **항상 정확히 90.0°** |

4/11 기준의 joints3d 는 y 성분이 전 프레임 0 → 척추벡터가 up(0,-1,0)과 항상 직교 →
torso_uprightness 가 **자세와 무관한 상수 90°**. 그 4개 동작의 자세 코칭 수치는 지어낸 값.
점수 경로 무영향(coach context 전용)이라 점수 오염은 없다.
내 해석: 데이터 불일치는 오늘 것이 아니나, 오늘 기능이 이를 걸러내지 않고 소비한다 = 내 결함.

## ③ 자세 축 한 방향 발화 = **확인됨 (범위 실측)**

현행은 delta>0(학생이 더 기울어짐)만 발화. 위 표에서 **서 있는 계열은 3개뿐**
(peter-pan 6.4 · kip-up 8.1 · climb 24.9). 나머지(수평·뒤집힘)에서는 흔한 결함인
"덜 눕힘/덜 뒤집힘"이 delta<0 이라 "학생이 더 낫다"로 읽혀 영영 안 나온다.
피터팬 단일 동작으로 검증한 대가 — [[judgment-must-not-fixate-on-recent-fixture]].

## ① stability 창 (리뷰 검증 CONFIRMED) — 크기 실측

파워스핀 정타(힌트 창 실측 (54,90) → 수리 후 부창 (80,89)): stability **96 → 98 (+2)**.
이 건의 이동폭은 작다. 단 더 근본 문제: 창 선택자는 **위치 분산 최소**로 고르는데
stability 는 **프레임간 흔들림**으로 채점한다 — 자가 다르다. 스윕 12건에서 전구간 대비
최안정 1/4 구간 stability 는 **-15 ~ +5** 로 양방향 이동(pdshape 정타 77→62 등).
이 불일치는 오늘 이전부터 존재(자동 창 경로) — 오늘 수리가 힌트 창 안쪽으로 확장했다.
