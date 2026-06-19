# Phase 20: v2 비전 점수 (Gemini 시각 거부권) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** 20-v2-gemini
**Areas discussed:** 비전↔v1 결합, 비전 호출 범위·트리거·단위, Mode3 미보유동작 게이트, 상단 변별
**belle 명시:** "오류 나서 생성된 phase인 만큼 절대 실수하지 않도록 더 신중히" → 모든 결정이 위양성 재발 방지(하향 전용)로 수렴.

---

## 영역 1 — 비전↔v1 결합 방식

| Option | Description | Selected |
|--------|-------------|----------|
| 거부권/캡 (하향 전용) | 비전은 fault 심각도로 v1 점수를 깎기만, 못 올림. 위양성 재발 구조적 차단 + belle 스펙 동시 충족 | ✓ |
| 가중 블렌드 (양방향) | α·v1 + β·비전. 비전이 올릴 수도 → 깨끗한 자세 끌어내리거나 위양성 재발 위험 | |
| min(v1, 비전) | 둘 중 낮은 값. 보수적이나 비전이 절대점수 쓰는 게 되어 거칠 수 있음 | |

**User's choice:** 거부권/캡 (하향 전용)
**Notes:** 캡/감점 수치는 6페어 curve-fit 금지 — 원칙만 잠그고 수치는 일반화 검증 eval 로(D-02).

## 영역 4 — 상단 변별 (within-20°=100)

| Option | Description | Selected |
|--------|-------------|----------|
| 이연(Defer) — 하향안전 우선 | v2 는 위양성 제거(하향)에만 집중. 비전 상단 인상은 위양성 문 재개방 | ✓ |
| 포함(양방향 비전) | 비전이 상단 해상도도 담당(올림 허용). 풍부하나 위양성 재발 리스크, 영역1 모순 | |

**User's choice:** 이연(Defer)
**Notes:** 영역1 '하향 전용'과 정합 — 신뢰=위양성 제거가 우선.

## 영역 2 — 비전 호출 범위

| Option | Description | Selected |
|--------|-------------|----------|
| Mode1+Mode3 둘 다 | fault 는 reference 유무 무관 → 비전이 둘 다 봄 | ✓ |
| Mode1만 | 위양성이 난 Mode1 한정. 범위 작게 | |

**User's choice:** Mode1+Mode3 둘 다

## 영역 2 — 비전 점수 단위

| Option | Description | Selected |
|--------|-------------|----------|
| 지배 결함 pose(worst) 중심 | worst-pose 가 점수 지배(D-01 정합). key_moments 재사용 | ✓ |
| 모든 IPSF phase 평균 | setup/hold/release 평균. Phase 19 가 고친 희석 버그 재발 위험 | |

**User's choice:** 지배 결함 pose(worst) 중심

## 영역 3 — Mode3 미보유동작 불확실 표시 강도

| Option | Description | Selected |
|--------|-------------|----------|
| 점수 억제 + '기준 없음' | confident 숫자 안 줌, 투명 표시. 신뢰 우선 | ✓ |
| 점수 + 강한 경고 배너 | 점수는 주되 미신뢰 명시 | |
| 이 세부는 plan으로 | UX 세부는 plan/Figma. 원칙만 잠금 | |

**User's choice:** 점수 억제 + '기준 없음'
**Notes:** 판정 주체 = Gemini 인식기 3분기(IPSF공식/정은지보유/둘다미보유). 트리거 = 채점 path 항상 호출. 인식기 결정성 = temp 0 + reference profile 캐싱(권장 그대로 수용).

## Claude's Discretion
- D-08 UX 강도(완전 숨김 vs 회색 vs 배너) 세부는 plan/Figma 확정 — 원칙(confident 숫자 금지)만 잠금.
- D-02/D-05 캡·감점 수식 + worst-pose 집계 룰은 research/plan + eval 도출.

## Deferred Ideas
- 상단 변별(영역 4) — 후속 phase 또는 하향-안전 변형으로 재검토.
- climb not_pole — ref-climb reference 품질 별도 ref-fix 트랙(코드 아님).
- sensitivity 셋(미보유+above-cutoff) — 일반화 게이트 자산, 별도 수집.
