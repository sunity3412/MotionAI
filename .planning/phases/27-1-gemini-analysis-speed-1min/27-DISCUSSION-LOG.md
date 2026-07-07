# Phase 27: 분석 속도 1분 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 27-analysis-speed-1min
**Areas discussed:** 1분 게이트 강도, veto 동기/비동기, 허용 레버 범위, 후처리 사후 분리

---

## 1분 게이트 강도

| Option | Description | Selected |
|--------|-------------|----------|
| 정확도 hard + 1분 목표 (Recommended) | 무회귀(EVAL18 순차)가 hard gate, 시간은 최대 절감 후 실측 보고 | ✓ |
| 1분 hard gate | 60s 미달 시 phase 미완 — 공격적 레버 강제 위험 | |
| 단계 목표 90s | 이번 phase 90s hard, 60s는 Phase 22 전환 후 | |

**User's choice:** 정확도 hard + 1분 목표
**Notes:** belle 원문 — "너무 1분에 집착 안 해도 됨. 4분 막 넘어가는데도 아무 조치가 없어서 나온 피드백이기 때문에.. 빠르면 빠를수록 좋은데 가능한 범위에서 현실적으로 진행." → 대기 중 무변화 체감이 본질이라는 인사이트가 D-02로 승격.

---

## veto 동기/비동기

| Option | Description | Selected |
|--------|-------------|----------|
| 파이프라인 내 겹치기 (Recommended) | 포즈 진행 중 비전 병렬 시작(단일 분석 내부), 점수는 결과 시점 동기 확정 | ✓ |
| veto 완전 비동기 | 결과 먼저, 점수 사후 보정 — 신뢰 리스크 | |
| 현행 순차 유지 | 라운드트립 축소만 | |

**User's choice:** 파이프라인 내 겹치기

---

## 허용 레버 범위

| Option | Description | Selected |
|--------|-------------|----------|
| 전송·캐시·병렬 + Flash 조건부 (Recommended) | 기본 모델·입력 불변, Flash 전환은 EVAL18 대조 통과 시만 | ✓ |
| 전송·캐시·병렬만 | 모델 절대 불변 | |
| 입력 축소까지 | 프레임/해상도 다이어트 포함 | |

**User's choice:** 전송·캐시·병렬 + Flash 조건부

---

## 후처리 사후 분리

| Option | Description | Selected |
|--------|-------------|----------|
| zoom 사후 업데이트 (Recommended) | 점수/verdict 먼저 complete, zoom PNG 사후 필드 업데이트 | ✓ |
| 동기 유지 + 내부 병렬화 | complete 시점 전부 준비 | |

**User's choice:** zoom 사후 업데이트
**Notes:** belle 추가 아이디어 — "로딩하는 동안 뭔가 재미적인 요소 (폴스포츠면 심플한 캐릭터가 폴스포츠 동작을 하고 있다던가.. 아님 텍스트로 표현한다던가)" → D-07로 캡처 (v1=텍스트 로테이션, 캐릭터는 에셋 확보 시).

---

## Claude's Discretion

- 병렬화 구현 방식, inline 전송 임계, 캐시 키 설계(버전 키 필수), 진행률 단계별 % 정밀화, 로딩 재미 요소 문구/구성

## Deferred Ideas

- 프레임/해상도 입력 축소 (D-04 금지)
- veto 완전 비동기 (기각)
- 캐릭터 애니메이션 에셋 제작 (디자인 트랙)
- Phase 22 자체 서빙으로 라운드트립 소멸 (근본 해법 — 이 phase는 브리지)
