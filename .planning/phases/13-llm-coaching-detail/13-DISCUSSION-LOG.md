# Phase 13: 보완 운동 추천 + LLM 분기 카피 + coaching detail 완성 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-16
**Phase:** 13-llm-coaching-detail
**Areas discussed:** 규준 노출 범위, 연령·성별 입력 추가, 보완운동 라이브러리, LLM 분기 + 플랜 분할, NotebookLM 리서치

---

## 규준 맞춤 범위 (연령·성별 입력 + 국민체력100 규준)

| Option | Description | Selected |
|--------|-------------|----------|
| v2 연기 (지금 예약만) | REQUIREMENTS.md PERS-04 신설 + fixture 커밋 유지. v1 미소비. 손해 0. | ✓ |
| v1 포함 (입력 추가) | age band+gender 입력 + 규준 연동. 미성년 동의 + 폼 마찰 + 의학근거 부재 리스크. | |

**User's choice:** v2 연기 (지금 예약만)
**Notes:** belle 가 먼저 "v2 어디서 제작?"을 물어, GSD 동일 플로우(같은 repo, 나중 마일스톤) + REQUIREMENTS.md v2 버킷 + fixture 보존 메커니즘 설명. 그 뒤 연기 확정. 근거: NotebookLM 리서치상 연령·성별 의학적 차이 근거 부재 + PROJECT.md "체형 입력+맞춤 피드백" v2 연기와 정합.

---

## 보완운동 매핑 키

| Option | Description | Selected |
|--------|-------------|----------|
| 실패원인(Phase9) + 통증부위 | Phase 9 실패원인 + BodyProfile painAreas. 리서치가 결함별 운동 다 제공. | ✓ |
| + 체력약점 규준까지 | 위 + 국민체력100 규준. 단 체력은 영상 측정 불가 → 입력 추가 의존(Q1과 연동). | |

**User's choice:** 실패원인(Phase9) + 통증부위
**Notes:** Q1 v2 연기와 정합. 규준은 v1 매핑 입력에서 제외.

---

## 플랜 분할

| Option | Description | Selected |
|--------|-------------|----------|
| 2개 분리 | Plan A=보완운동(criteria 1-4), Plan B=실 LLM+ipsfCode 분기(criteria 5-8). | ✓ |
| 1개 통합 | 한 플랜에 전체. coach_writer 프롬프트에 보완운동 맥락 동시 주입 시 유리하나 큼. | |

**User's choice:** 2개 분리
**Notes:** 의존성·검증(Plan B 만 Pod 의존)이 달라 분리가 깔끔.

---

## Claude's Discretion

- 보완운동 라이브러리 저장 형태(JSON vs Firestore) — planner 재량(contract-first 정합 조건).
- IPSF Code 매핑 테이블을 studio-term-3branch 데이터로 흡수할지 — planner 재량.

## Deferred Ideas

- 연령·성별 입력 + 국민체력100 규준 맞춤 리포트 맥락 → v2 PERS-04(신설 완료). fixture 커밋(3c937d9) 보존, v2 wiring 만.
- 부상 위험 경고 본격 UI, 회차별 성장 그래프, 영상 인앱 다운로드 → PROJECT.md v2.

## belle 추가 지시

- NotebookLM 리서치 필수 + 리서치 비중 상향 → CONTEXT D-06 + canonical refs(노트북 2개) 박제. 디스커션 중 2개 쿼리 선실행, 결과를 CONTEXT Specifics 에 박제.
