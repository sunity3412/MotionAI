# SEED — 관절 귀속 정밀도 (belle 지정 다음 작업, 2026-07-24)

> 출처: Wave R(33-22 채점 재설계 + 33-23 재검증) 후 belle 요청 영상 전수 검증에서 도출. 근거 = 33-SCORING-REVERIFY.md "영상 전수 검증".

## 문제 한 줄

채점 **점수 크기는 정당**(5 fixture 영상 검증 완료)하나, **"어느 관절이/왜 문제인지"(귀속)는 신뢰 불가** — 특히 역립 동작. 사용자에게 "여기가 문제"를 보여주려면 이 귀속 정밀도부터 고쳐야 한다. = belle 최초 A-0("분석이 엉뚱한 데를 짚는다")의 잔존 형태.

## 증거 (33-23 sweep, shadow candidate phase33-cm3-run1, 2트랙 엔진)

- **역립 2개가 핵심 신호:** elbow-twist-sister(60) = 8관절 전부 26~36° 균일 감점(Σ−111.4→캡60), pdshape(60) = 7관절 25~30° 균일(Σ−57.1→캡60). **균일 다관절 편차 = 개별 진짜 결함 아니라 "거꾸로 자세에서 포즈추정/DTW정렬이 통째 틀어진" 아티팩트 냄새.**
- **vision severity=none (5/5):** Gemini 가 특정 결함을 하나도 짚지 못함 → 점수가 순수 기하 per-joint 편차에만 의존. 의미(무슨 결함) 레이어가 비어있음.
- **seedObservation.pointed=[] (전부):** vision 침묵 → `angle_vs_reference__{joint}` fallback 경로가 전 관절 편차를 감점. window_joints 도 비어있음.
- **power-spin worst-window 70° = 정렬 아티팩트** (클립 위상 어긋남). 점수엔 DTW-median 이 옳게 쓰임 — 귀속 문제와 별개지만, 측정 시스템 간 불일치가 큼을 보여줌.

## 가설 (조사 대상 — curve-fit 금지, 일반화)

1. **역립 포즈 추정 신뢰도 저하** — RTMW 가 거꾸로/폐색 자세에서 관절을 통째 오프셋. → 관절별 confidence 게이트로 저신뢰 관절을 귀속에서 제외?
2. **DTW/좌표프레임 전역 오프셋** — 정은지 대비 학생의 몸 전체가 회전/정렬 어긋나 모든 관절이 균일하게 X° 밀림. → 전역 오프셋 제거 후 잔차로 귀속?
3. **vision 의미 레이어 미발화** — Gemini severity=none 이라 "무슨 결함"이 없음. → vision 이 짚은 관절에만 window 측정 적용하는 원칙([[window-median-silent-seed-fp-reverted]] 교훈)을 역으로: vision 이 침묵하면 귀속을 "전체 자세가 덜 깨끗" 수준으로만 표현하고 특정 관절 단정 회피?
4. **fixture 성격** — 이 fault 들은 그로스 폴트가 아니라 "덜 깨끗한" 데모. 귀속이 애매한 건 결함 자체가 미세·분산돼서일 수도. → belle 와 fixture 의도 확인 필요.

## 스코프 경계

- **채점 크기(엔진/임계) 재변경 아님** — Wave R 로 검증됨. 이 작업은 "귀속/표현"이지 "점수값"이 아님(D-20/D-29 정신).
- 표현 트랙(33-08~16)과 연결되나, 그 트랙은 flip(33-07) depends. 이 SEED 는 flip 전에도 가능한 **seed/측정 정밀도 조사**(역립 균일편차 근본원인)를 우선 분리 가능.
- curve-fit 금지: 특정 fixture 를 맞추려 관절 규칙 조작 금지([[judgment-must-not-fixate-on-recent-fixture]]).

## 착수 제안

`/gsd-debug` 또는 `/gsd-quick` 로 **역립 균일-다관절-편차 근본원인**(가설 1/2)부터 조사 — 이게 crux. 원인 규명 후 표현/귀속 설계(가설 3)로. Pod 필요 시 belle greenlight(전부 terminated).
