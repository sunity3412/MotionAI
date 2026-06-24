# Phase 24: 투명 감점-합산 채점 엔진 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-24
**Phase:** 24-transparent-deduction-scoring
**Areas discussed:** 감점 규칙 도출, 기준선=100 정의, 측정불가 결함 처리, Phase 경계+eval 게이트, (파생) 감점 구조, 파일 처리 위치

> **컨텍스트:** discuss 는 "Phase 20" 으로 열렸으나, 논의 중 Phase 20 이 이미 production 배선 완료됐고 밴드 한 단만 교체하면 됨이 확정 → 신규 Phase 24 로 분리. 아래 결정은 Phase 24 CONTEXT 로 박힘.

---

## 감점 규칙 도출 (anchor/형태)

| Option | Description | Selected |
|--------|-------------|----------|
| 기하 tolerance 확장 | dimensions.py tolerance+per-unit penalty 를 전 차원으로 확장, 동일 형태 단일 규칙, 전 영상 동일 slope | ✓ |
| IPSF 등급→편차 임계 매핑 | IPSF minor/moderate/major 의미를 편차 임계로 변환, 사이는 연속 감점 | |
| 동작별 IPSF criterion | 등재 동작마다 필요 신전관절/기하조건당 감점 | |

**User's choice:** 기하 tolerance 확장 (ND-03)
**Notes:** `_LINE_TOL_DEG`/`_PENALTY_PER_DEG=1.2` 가 이미 코드에 존재 → per-degree 감점이 완전 신규는 아님. curve-fit 금지 위해 전 영상 동일 slope.

---

## 기준선 = 100 정의

| Option | Description | Selected |
|--------|-------------|----------|
| IPSF 이상기하 통일 + 동작별 | 기준=IPSF 이상기하, 정은지는 ~100 나와야 하는 검증자 | |
| 모드별 혼합 | Mode1=정은지 matched / Mode3=IPSF 이상기하 | |
| 동작별 baseline 분기 우선 | 기준선 선택(바닥/폴/엉덩이라인)을 동작 분기의 1급 출력 | |

**User's choice (free-text):** "지금은 정은지지만 흐름이 이렇게 되어야지. 사용자가 배우고 싶은 선수(코치)의 동작을 선택 → 이게 그 사용자 입장에선 100점이 됨. IPSF 의 동작이 있는 공식 동작이라면 해당 심사 기준이 기준이 됨." (ND-05)
**Notes:** 기존 20-D07 3분기와 정합, "reference"를 "사용자 선택 코치"로 일반화. 동작별 기준선([[output-needs-baselined-quantification-layer]])은 측정 토대로 합류.

---

## 감점 구조 (per-degree 폭주 방지 — belle 파생 질문)

| Option | Description | Selected |
|--------|-------------|----------|
| criterion 묶음 + IPSF 상한 | 상관 관절 1회 측정, criterion별 IPSF severity 가 상한(최종점수 밴드 아님), 합산 | ✓ |
| 지배 결함 가중(worst-fault) | top-1/top-K 결함만 점수 지배 | |
| 묶음+상한+지배가중 결합 | 셋 다 결합(가장 안전, 규칙 복잡도↑) | |

**User's choice:** criterion 묶음 + IPSF 상한 (ND-04)
**Notes:** belle 우려 — "오른발 30°·왼발 30°(거의 같을 확률) 벌써 −60... 무시무시." 해소책 = 상관 관절 묶음(중복계산 제거) + criterion별 IPSF 상한. **최종점수 밴드(금지)와 fault 종류별 IPSF 상한(허용)의 구분**이 핵심. 원 20-D05 worst-pose 지배를 합산 구조로 supersede.

---

## 측정불가 결함 처리

| Option | Description | Selected |
|--------|-------------|----------|
| 감점 0 + coverage gap 로그 | 규칙 없으면 0(밴드 주입 안 함), 정성 관찰 표시 + 갭 로그 | ✓ (임시상태) |
| 매핑 강제 | 모든 결함이 측정가능 criterion 으로 매핑되게 설계 | ✓ (설계 목표) |
| 정성 경고만 | 감점은 정량만, 측정불가는 경고 텍스트 | |

**User's choice (clarifying):** "규칙이 없으면 육안으로 틀린게 뻔히 보이는데 감점을 안 하는 거?" → 해소: **매핑 강제가 설계 목표(2번), 감점0+로그(1번)는 갭 메우는 동안의 정직한 임시상태.** "보이는데 0감점"은 출하 금지(coverage gap). 자의적 밴드 주입은 절대 금지. (ND-06)
**Notes:** 육안으로 뻔히 틀린 건 거의 항상 측정 가능(각도/거리/라인) → 그 규칙을 쓴다.

---

## Phase 경계 + eval 게이트

| Option | Description | Selected |
|--------|-------------|----------|
| 신규 phase (23 뒤) | 23 정량화 완료분 소비, 의존 깔끔, SEVERITY_CAP 제거 | ✓ |
| Phase 20 재오픈 | 20 제자리 피봇 — 단 23 의존 역전 위험 | |
| 23 에 흡수 | 23 스코프 확대 — 단 still-frame recall 과 섞여 커짐 | |

**User's choice:** 신규 phase (Phase 24). belle 확인 — "phase 23 이후의 phase로 만들면 20도 재설계 필요없는 거네? 근데 20을 우리가 개발을 했나" → 20 은 production 배선 완료(확인), 신규 phase 가 밴드 한 단만 supersede·나머지 보존.
**Notes (eval 게이트, ND-07):** 케이스별 기대점수 manifest(moderate≤75·major=50, 23-03 흡수분 포함) curve-fit 제거. 신규 게이트 = 추적성 + 단조성 + 결정성 + 일반화. belle "1번(네 개 모두)" 방향, 단 예시 보고 확정 — 워크드 예시(pdshape 100−33−9=58) 제시 후 수긍. 정은지 95~100 은 타깃 아닌 결과.

## 파일 처리 위치

**User's choice:** 신규 phase 생성 (ROADMAP Phase 24 추가 + 24-CONTEXT.md 작성, 20-CONTEXT 는 그대로).

## Claude's Discretion

- 곡선 형태·tolerance 폭·IPSF severity 가중치 매핑 수식 (research/plan + IPSF CoP lookup + eval, curve-fit 금지)
- 보고서 감점 내역 UX 강도/형식 (후속 UI phase + Figma)
- criterion 묶음의 정확한 그룹 정의 (plan + technique profile + IPSF criterion 데이터)

## Deferred Ideas

- 앱 표시/렌더링 (후속 UI phase)
- 상단 변별 (within-20° good vs perfect)
- 자체 비전 모델 파인튜닝(Phase 22) 라벨 스키마 정합
- sensitivity 셋 구축(미보유+above-cutoff) — ND-07 일반화 게이트 입력 자산
