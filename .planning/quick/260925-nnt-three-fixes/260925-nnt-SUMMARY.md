---
quick_id: 260925-nnt
slug: three-fixes
date: 2026-09-25
status: complete
commits: [a3c881ea, f9ca6d7f]
pod: ebo5coltal6p82 (RTX 4090, EU-RO-1 볼륨 a5z753defc)
---

# 세 칸 수리 — 결과 (belle "그럼 세 칸 고쳐봐")

> 봉인 시험지 1회(260925-mvh, 0/2) 뒤. 규율: 영상별 조절 0 · 정타 5편 침묵 · 문장은 belle ○× 전까지 초안 · 이 두 편은 이제 연습 문제.

## 0. 판정 한 줄씩

| 칸 | 한 것 | Pod 결과(앱 경로) |
|---|---|---|
| ① Gemini 가 결함을 적고도 버리는 경로 | severity none 이어도 K-of-N 지목을 no_fault ctx 에 승계. 감점은 기하만 | **climb**: "왼팔을 크게 굽혀 폴을 감싸 안음"이 grip coverage gap → 화면 강사 질문 "정확히 재기 어려웠던 부분 (왼팔 및 왼손)". 감점 문장은 못 만든다(팔 각도 자가 회전 중 −17°만 읽음) |
| ② 높이 카드 일반화 | 몸 전체 패턴 `body_low`(엉덩이 1/3 전부 낮음) → 어느 record 든 승인 문장이 있으면 호스트. 엉덩이 동그라미 | **power-spin 실수**: 카드 첫 줄 "정은지 선수보다 낮은 위치에서 돌고 있어요" + 엉덩이 원(6.91s\|9.80s). 점수 68 불변 |
| ③ 벌림 게이트 | **안 열었다** — 2D peak split 이 다리 접은 순간에도 180 으로 포화(기준 r43 180.0, kip-up 기준 180.0, pdshape 173.7). 실수 165.3 → 부족 14.7 < 20 이라 열어도 침묵 | belle 질문으로 대체: 카드의 "무릎이 덜 펴져 스플릿 라인이 꺾임" = belle 의 "다리 벌림이 다르다"인가 ○× |

정타 5편 = 100/100/100/100/100 (4090). 실수 = power-spin 68 · kip-up 83 · climb 60 · peter-pan 60 · pdshape 80 — 09-24(L4)와 같은 값. GPU 가 달라(4090) 점수 비교는 참고([[gpu-type-changes-pose-angles]]).

## 1. Pod 실측이 정정한 것 2건 (1차 커밋 a3c881ea → 2차 f9ca6d7f)

- `[확인]` **①의 부작용**: 지목 승계가 split 의 vision-측정값(Gemini 추정 50°)까지 실어 와 **kip-up 실수 83→63**(split −20, primaryFault 는 "머리가 덜 젖혀져"), power-spin 68→60. belle 이 09-24 에 닫은 카드가 열렸다. → `deduction_engine._vision_values_allowed`: severity none 이면 Gemini 숫자 주입 0, 라우팅만. 재실측 kip-up **83**, power-spin **68**, 로그 `split vision value skipped (severity none)` 2건.
- `[확인]` **②의 손 조건이 거짓이었다**: "grip −0.646" 은 손이 낮은 게 아니라 검출 탈락 비율이었다 — 회전 동작에서 "높은 손" 시계열이 1.3/0.6/0.1 세 봉우리(기준 영상도 같다, 공중에서 손이 바닥 높이일 수 없다). 대표 짝 사진에서 두 손 높이는 같았다. → 패턴을 엉덩이만으로(`body_low`), 문장·원에서 손 제거. [[grip-hand-height-series-is-trimodal-in-spins]]

## 2. 화면에 실리는 것 (초안, belle ○× 대기)

power-spin 실수 카드(leg_extension record, measuredPattern=body_low):
- statusLine: 정은지 선수보다 낮은 위치에서 돌고 있어요
- whyLine: 돌기 시작해서 끝날 때까지 엉덩이가 정은지 선수보다 눈에 띄게 아래에 있고, 무릎도 덜 펴져 있어요
- cueLine: 몸을 더 높이 끌어올린 채로, 무릎을 끝까지 편 채 돌아보세요
- 사진: 재실측(2e60f3e3)에서는 합성 영상이 리그 FAIL(09-24 관측과 같은 건, 1차 실행 d151d104 은 PASS — 경계 판정) → 확정 카드는 fault_zoom 단계 크롭 + 엉덩이 원(양 패널)이 앱에 붙는다(`e2e/card_power-spin-fault_2e60f3e3_leg_extension.png`). 영상 멈춤 장면은 없다(앱은 두 영상 나란히 재생). 잰 값: 엉덩이 1/3 차 −0.225/−0.157/−0.180 몸길이(정타 −0.037/−0.118/−0.038).
- 판정지 = `e2e/judge_power-spin_2e60f3e3.png` · kip-up 회귀 판정지 = `e2e/judge_kip-up_64c93c36.png`(09-24 ○ 카드와 같은 사진·문장, 83).

climb 실수: 감점 3건은 종전(오른고관절·무릎 둘) + 강사 질문 1줄(왼팔 및 왼손, 못 잼).

## 3. 관측 — 승계해도 되는 것
- `[확인]` 정타 5편은 `지목 승계` 로그 0 — supported differences 가 애초에 없다(Gemini 정타 방어 유지).
- `[확인]` peter-pan 실수도 지목 승계 2건이 있었으나 점수 60 불변(기하 tol 안).
- `[확인]` climb 실수 엉덩이 −0.203(1/3 전부) · 손 +0.31 → 팔을 접어 손 아래로 0.5 몸길이 처짐 — belle 판독과 방향이 맞는 **잰 값**이 이미 있다. 문장 배선은 안 했다(climb 승인 문장 없음, belle 판독은 봉인 정답이라 이 영상으로 규칙을 만들면 연습 문제화).
- `[관측]` power-spin 정타 엉덩이 앞·뒤 1/3 −0.037/−0.038 — 잡음 폭 0.05 바로 안쪽. 0.03 이면 정타가 뒤집힌다(테스트로 박제). 새 테이크에서 이 여유부터.
- `[관측]` 4090 이라 09-24(L4)와 GPU 가 다르다. 점수는 10편 모두 같은 값이 나왔다.

## 4. 미확인 — 진단 아님
- belle ○×: power-spin 문장 3줄 · 엉덩이 원 사진 · "무릎 덜 펴짐 = 벌림?" · climb 강사 질문 1줄.
- 앵커 부위 확인(Gemini part check)은 body_low 카드에도 안 돈다(좁은 크롭 문법 전용).
- 다른 동작(peter-pan·pdshape)은 서 있는 구간이 없어 높이 fail-closed — 몸 전체 패턴 대상 밖.

## 5. 인프라
Pod ebo5coltal6p82 4090 $0.74/h · 링크 3.3 MB/s(가속 ON) · 12편 재분석 · 17:22~18:12 ≈ 50분 · `pod_teardown.py` 로 종료 + Lambda 자리표시자 + pod-expected=down `[확인]`. 잔액 $21.98 → 21.41.
증거 = `e2e/`(카드 PNG · 멈춤 프레임 · pod_log_excerpt.txt · 1차(초안 오류) 카드도 보존: `*_d151d104_*`, `*_a205bccb_*`).
