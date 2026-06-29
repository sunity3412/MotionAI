# Phase 10: 부상 위험 신호 플래그 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-29
**Phase:** 10-injury-risk-flags
**Areas discussed:** 비대칭 위험 신호 정의, 요추 과신전 검출 방법, 측정 신호 ↔ 기존 LLM injuryRisk, 레벨 대비 무리(Mode 범위), Mode3 절대 자세-위험, 신호 재설계(NotebookLM)

---

## 비대칭 위험 신호 정의

| Option | Description | Selected |
|--------|-------------|----------|
| Reference 대비 편차 | 정은지 좌우 편차 baseline 대비 초과 시 플래그. 의도적 비대칭 자동 상쇄. 객관성 정합 | ✓ |
| 고위험 관절만 고정 임계 | 어깨·고관절 부하 차 등 고정 각도 임계 | |
| 양측대칭 동작에만 검사 | 인식기로 동작 분류 후 검사 (인식기 신뢰도 의존) | |

**User's choice:** Reference 대비 편차
**Notes:** scoring이 대칭 차원을 일부러 뺀 이유(폴 동작 의도적 비대칭)와 정합. Mode 3는 직전 영상 대비. 절대 비대칭은 위양성 커 v1 미포함.

---

## 요추 과신전 검출 방법

| Option | Description | Selected |
|--------|-------------|----------|
| 트렁크-대퇴 각도 프록시 | 어깨-고관절-무릎 3D 각도 근사, 보수 임계 + "추정" 라벨, 양 모드 | ✓ |
| Reference 대비 트렁크 후굴 편차 | Mode1 전용, 더 객관적이나 Mode3 미적용 | |
| v1에서 요추 제외 | 비대칭+레벨만, 요추는 후속 | |

**User's choice:** 트렁크-대퇴 각도 프록시
**Notes:** NotebookLM 검증 — 몸통 단일 강체 프록시는 요추 과전만 vs 고관절 신전 구분 불가. "추정/가능성"으로만 표기 필수.

---

## 측정 신호 ↔ 기존 LLM injuryRisk

| Option | Description | Selected |
|--------|-------------|----------|
| 별도 결정론 SafetyFlag 레이어 | 측정 기반 독립 구조+전용 UI. LLM injuryRisk는 코칭 보조 별개 유지 | ✓ |
| 측정값을 LLM 입력으로 주입 | LLM이 측정값 받아 서술 (드리프트 위험) | |
| 측정 플래그가 LLM injuryRisk 대체 | 가장 결정론적이나 기존 코드 구조 변경 | |

**User's choice:** 별도 결정론 SafetyFlag 레이어
**Notes:** 결정론·객관성 보장(temp 무관). 기존 `CoachingTipDetail.injuryRisk` 프로즈와 독립.

---

## 레벨 대비 무리 (Mode 범위)

| Option | Description | Selected |
|--------|-------------|----------|
| Mode1 전용 | reference.level × experience 매핑, 데이터 존재, 신뢰도 높음 | (부분) |
| 인식기로 양 모드 | 동작 분류해 둘 다 (인식기 신뢰도 의존) | |
| experience만 일반 경고 | 동작 무관 휴리스틱 | |

**User's choice (free-text):** "모드3은 부상 비교보다는... 뭔가 발견할만 한 방법 없나? 내 영상을 분석했을 때..? 자세가 이러면 부상의 위험이 높다.. 이런게 되야하는데 지금은 불가능인가?"
**Notes:** belle 푸시백 → Mode3 절대 자세-위험 신호로 확장. 레벨 매핑은 Mode1 전용 유지, Mode3는 절대 신호(트렁크/관절 과신전 + 통제 상실)로 충족.

---

## Mode3 절대 자세-위험 신호

| Option | Description | Selected |
|--------|-------------|----------|
| 트렁크+관절 과신전 | 절대 임계, 무릎·팔꿈치 역꺾임 3D 방향 판별, 양 모드 | ✓ |
| + 절대 비대칭도 포함 | Mode3 절대 좌우 비대칭도 플래그 (위양성 위험) | |
| 관절 과신전은 후속 | v1은 트렁크만 | |

**User's choice:** 트렁크+관절 과신전
**Notes:** Mode3에서 "내 자세가 이러면 부상 위험 높다" 실현. 관절 과신전 = 3D 외적 부호 판별.

---

## 신호 재설계 (NotebookLM 통찰)

| Option | Description | Selected |
|--------|-------------|----------|
| 통제 상실 결합 | 신호 = (극단/과신전/비대칭) AND (통제 상실). 정은지 위양성 방지 | ✓ |
| 극단 각도만(단순) | 통제 지표 없이 각도 임계만 (고수 위양성 위험) | |
| 통제 상실만 | 각도 무관 행동 불안정만 | |

**User's choice:** 통제 상실 결합
**Notes:** IPSF가 hyperextension·180° 스플릿·백아치를 가점으로 취급 → 극단 각도 단독 플래그 시 정은지 위양성. 문헌상 위험 변별자 = 통제 상실(반동·슬립·리그립·밸런스 상실). Phase 8 jerk/jitter + stability 재사용.

---

## Claude's Discretion

- 위험도 스코어 수치 스케일·등급 수, SafetyFlag 필드명·코드 식별자 (contract 3중 미러 준수 전제).

## Deferred Ideas

- 명시적 슬립/리그립/밸런스 상실 이벤트 검출 (v1은 jerk/jitter+stability 프록시).
- 요추 전용 척추 키포인트 추정 (트렁크 강체 한계 극복, 별도 ML 트랙).
- 동적 무릎 외반(knee valgus) ACL 지표 — 폴 정합성 검토 후 후속.
- 미해결 research: experience+reference.level 파이프라인 도달 검증, 과신전 절대 임계 외부 문헌 출처 확정.
