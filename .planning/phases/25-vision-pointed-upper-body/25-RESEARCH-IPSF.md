# Phase 25 도메인 리서치 — IPSF 상체 결함 규정 (NotebookLM, IPSF CoP 2024-2025/2025-2027)

**Source:** NotebookLM "IPSF Rules and Advanced Strength Pole Moves Guide" (96b061e8, 70 sources), 2026-07-04 질의 2건.
**용도:** Phase 25 상체 감점 criterion 설계의 IPSF 앵커 ([[judging-baseline-ipsf-code-of-points]] 준수).

## 1. 팔꿈치 굽힘 — Criteria 표기 3분류 (범주형)

- **"Fully Extended" 요구 + 굽힘(micro 포함)** → 기술 전체 무효(0점). 각도 오차 허용 없음 (categorical).
- **"Extended" 요구** → micro bent 허용 (정당 인정).
- **"Bent" 요구 / forearm grip 등** → 굽힘이 의도된 올바른 폼.
- 요건 외 일반 라인: "Clean lines" 위반 **−0.2/건**.
- 출처: IPSF CoP Mid-Cycle Update Appendix 2023 p.55/99/131 "Fully extended arm vs Micro bent arm vs Bent arm".
- ※ 기존 P1 해법(ipsf_absolute 180° 신전, 260627-afq)과 정합 — 이미 반영된 축.

## 2. 어깨 — 전용 감점 항목 없음, "Poor Posture" 로 처리

- "shrugging"/"passive shoulder" 명시 항목 **없음**.
- 어깨 말림/등 굽음(Rounded shoulders/back) = **Deficit Extension / Poor Posture −0.2/건** (Singular Deductions).
- **수치화된 각도 기준 없음** — 어깨 각도가 몇 도 틀어져야 감점인지 IPSF 는 정의하지 않음.
- **설계 함의:** 어깨는 ipsf_absolute(객관 각도) criterion 이 불가능한 관절 → **reference_relative(정은지 대비 편차) 측정이 유일하게 정직한 방식** — Phase 25 의 vision-pointed reference_relative 접근이 규정 구조와 정합.

## 3. 몸통/상체 라인

- Deficit Posture (twist 미요구인데 어깨-골반 방향 불일치/정렬 상실): **−0.2/건**.
- Loss of Balance (가시적 흔들림/덜컹): **−0.5/건**.
- 출처: IPSF Aerial Pole CoP 2024-2025 p.16/91 + Singular Deductions.

## 4. 허용오차(tolerance) — 어디에 있고 어디에 없는가

| 대상 | IPSF 허용오차 | 출처 |
|---|---|---|
| 스플릿 180° | **±20° 공식 명시** (≥160° 인정, 미달 = 0점). 모든 시점(all angles/perspectives)에서 동일해야 | CoP 2024-2025 p.15, Taxonomy "Geometry of Execution Tolerance" |
| 몸통 공간 정렬 (예: F115 Russian Split "body parallel to floor") | **20° tolerance 명시** (per-element) | CoP 2025-2027 p.49 |
| 팔/팔꿈치 신전 | **없음** (범주형 — Fully Extended 는 micro-bend 도 무효) | Appendix 2023 p.131 |
| 어깨/척추 관절각 | **없음** (수치 기준 자체가 없음) | — |

- **설계 함의:** 우리 kismam 20° tol 은 스플릿·몸통-공간-정렬 규정에는 직접 앵커되고, 어깨 per-joint 각도에는 IPSF 수치 근거가 없다 → 어깨 20° 는 "IPSF 가 각도 tolerance 를 쓰는 유일한 수치(20°)를 준용한 엔지니어링 선택"으로 문서화해야 정직 (IPSF 명시 규정인 척 금지).

## 5. 감점 방식 — IPSF 는 건당 고정, 우리는 편차 비례

- IPSF execution 감점은 **비례(graded) 방식 없음** — 결함 크기와 무관, 발생 건당 고정(−0.2 등), 루틴 전체 누적(최대 −25.0).
- 우리 엔진은 belle 결정(scoring-must-be-transparent-deduction-tally)에 따라 **측정편차 × 명시규칙(slope)** — IPSF 건당 고정보다 정보량이 많은 방식으로 이미 의도적으로 벗어나 있음 (Phase 24 에서 결정 완료, 재론 아님).
- **설계 함의:** 상체 감점도 동일 원칙 유지 (편차 비례). IPSF 앵커는 "무엇이 결함인가"(Poor Posture 범주, per-element Body/Arm position criteria)에 사용하고, "얼마나 깎나"는 기존 엔진 규칙(tol+slope)을 따른다. fault 종류별 상한만 IPSF 앵커 허용(Phase 24 게이트).

## 6. 스플릿 요소의 상체 — 공통 규정 없음, per-element Criteria 가 지정

- 모든 스플릿에 일괄 적용되는 상체 규정 없음. 개별 기술 코드의 Criteria 가 Body position(Inverted/Upright/parallel 등) + Arm position/grip 을 지정하고, 미충족 시 각도가 완벽해도 무효.
- **설계 함의:** registered-motion criteria yaml(현 kip-up = 무릎 EXTEND 만)에 **Body/Arm position 축을 추가하는 것이 IPSF per-element Criteria 구조와 동형** — Phase 25 의 "vision 이 상체를 짚을 기준"을 per-move yaml 로 주는 것이 규정 정합적.
