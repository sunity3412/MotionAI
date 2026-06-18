# Phase 19 — IPSF Code of Points 감점 방식 근거 (NotebookLM lookup, 2026-06-18)

**출처:** NotebookLM "IPSF Rules and Advanced Strength Pole Moves Guide" (70 sources,
IPSF Code of Points 2021–2024 / 2025–2027 인용). [[notebook-lm-pole-sports]]
**용도:** D-01(감점식 집계) + D-03(미보유동작 절대 트랙) 재설계의 도메인 baseline.
**경계:** 채점 baseline = IPSF ([[judging-baseline-ipsf-code-of-points]]). 사람 점수 라벨 금지;
임계값/감점 수치 라벨링은 OK ([[analysis-objectivity-no-human-scores]]).

---

## A. 감점(deduction) 기반 채점 — 2 트랙 (D-01 핵심)

IPSF는 평균을 내지 않는다. 결함마다 정해진 값을 **빼는** 단발성 누적 감점(Singular
Deductions) 구조 + 요소 무효(0점) 트랙을 병행한다.

### 트랙 1 — 요소 무효(0점, "not awarded")
- 동작 최소요건이 **"Fully Extended"** 인데 관절을 미세하게 굽히면(micro-bent) 그 요소는
  **감점이 아니라 득점 전체가 0점**. ("Extended" 요건이면 부분 인정.)
- 스플릿: 목표각 **±20° 허용오차**. 180° 목표 → **160° 미만이면 요소 fail(0점)**. (비례감점 아님.)
- 선언한 필수요소를 실패/식별불가 → **missing element, 회당 -3.0**.

### 트랙 2 — 누적 실행 감점(Singular Deductions, 회당)
| 결함 | 감점/회 |
|---|---|
| Knee/toe alignment (무릎-엄지 직선, 식클링) | -0.1 (구규정 -0.2) |
| Clean lines (완전신전·포인) | -0.1 (-0.2) |
| Extension (등/어깨 말림, 목·토르소 미신전) | -0.1 (-0.2) |
| Posture (정렬·통제) | -0.1 (-0.2) |
| Poor presentation / bad angle | -0.5 |
| Poor transition | -0.5 |
| Loss of balance | -0.5 |
| Slip | -1.0 |
| Fall | -3.0 |
| Missing element | -3.0/회 |

- **기술 감점 총 한도 -25.0.** 누적이며 평균 희석 없음.

### 단일 major fault 지배 (위양성 제거 핵심)
1.0점짜리 고난도 요소에서 micro-bend → 그 슬롯 **0점**(득점기회 박탈) + missing element 판정
시 **추가 -3.0** = 한 기하 오차가 ~4.0점 손실로 직결. **다른 정상 동작과 평균되지 않음.**
→ D-01 "단일 major fault가 종합점수를 지배" 설계의 도메인 직접 근거. 현재 이중 단순평균
(관절→각도 평균, 차원→종합 평균)이 이 지배성을 정면으로 위반 = 정은지 실패영상 94점 원인.

### 카테고리 합산 (가중 % 아님)
`최종 = 필수(Compulsory) + 기술보너스 + 예술·안무 − 기술감점`
엘리트 시니어 최대 스케일 ≈ 56점(필수 7.7~11 + 보너스 25 + 예술 20), 감점 −25 한도.
최소 점수 0. (우리 0~100 스케일로 매핑 시 비율 변환 필요 — 단 "감점식 + 단일결함 지배"
구조를 보존.)

---

## B. Reference-free 절대 기준 (D-03 미보유동작 트랙)

기술 감점(Technical Deduction) 트랙은 **특정 요소 성공 여부와 무관하게 무대 위 모든
움직임(floor work 포함)에 적용** → 기준 동작 데이터가 없어도 자세 품질을 절대 평가 가능.
이것이 D-03 "Page 9 절대 공통 트랙"의 근거.

- **완전신전 정의:** 팔 = 손목→어깨 일직선, 다리 = 발목뼈→골반뼈 일직선. (과신전은
  flexion 아니므로 fully extended 로 간주.)
- **포인:** 무릎뼈→엄지발가락 직선. 식클링(낫 모양) = 정렬 불일치 -0.2. (포인은 미감뿐
  아니라 knee-flexion lock 으로 폴 그립 강화하는 역학적 필수.)
- **스플릿:** 180° 목표, ±20° 허용 = 160° 최소. 미달 시 난이도 0점.

→ 미보유 동작은 이 절대 감점표로 점수를 주되, 화면에 "기준 동작 없음 — 절대 자세 기준
평가" 근거 명시 (D-03). "정은지와 89% 일치" 같은 거짓 프레이밍 금지.

---

## C. D-05 비전 앵커와의 정합 (known-answer)

D-05 6 페어가 짚은 지배 결함이 모두 위 트랙 2의 고감점 항목과 직결:
- 무릎 굽음(kip-up/pdshape/power-spin/peter-pan) = 신전 미달 → "Fully Extended" 요소면 0점,
  아니어도 Extension/Clean lines 회당 누적.
- 스플릿 좁음(elbow-twist-sister/power-spin) = 160° 임계 위반 → 요소 fail 후보.
- 등 말림(climb) = Extension/Posture 누적.
- 발끝 풀림(전 페어) = Knee/toe alignment + Clean lines 누적.
→ 6/6 모두 **major 또는 다중 누적 감점**이어야 정상. 94점/89%는 IPSF 기준 명백한 오류.

**미해결 질문 (연구/플랜에서 확정):** 0~100 매핑식, micro-bent 임계(각도 몇 도부터
"fully extended" 미달로 볼지), 누적 감점을 RTMW 측정 각도에서 어떻게 산출(회당 카운트 vs
프레임 비율), 단일 major 지배를 보장하는 합성식(min/감점합/가중). D-05 경계: 보유셋
overfit 금지 — 임계는 IPSF 근거에서, 보유 sweep 재calibrate 금지.
