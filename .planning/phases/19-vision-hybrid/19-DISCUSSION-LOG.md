# Phase 19 Discussion Log

**Date:** 2026-06-18
**Mode:** discuss (default)

> Human-reference only. Not consumed by downstream agents (they read 19-CONTEXT.md).

## Origin

Phase 19 신설 — Phase 15 실증 중 belle 실기기 검증에서 점수 신뢰도 붕괴 발견(정은지 '실패' 영상 Mode1 94점/89%). 3-갈래 심층조사로 근본원인 확정 후 belle 지시로 재설계 phase 착수.

## Areas discussed (belle selected all 4)

### 1. 채점 철학 (집계 방식)
- Options: IPSF 감점식(엄격) / 최악-앵커 / 중도
- **Selected: IPSF 감점식 (엄격)** — 결함이 점수 지배, 평균 희석 제거 → D-01

### 2. 비전 ↔ 기하학 역할 분담
- Options: 기하학 주도+비전 거부권 / 비전 판정 주도 / 융합
- **Selected: 기하학 주도 + 비전 거부권** — 객관성 유지 + 비전 위양성 안전망 → D-02

### 3. 미보유 동작 처리
- Options: 절대트랙+비전+근거명시 / 불확실 게이트 / 비전 단독
- **Selected: 절대트랙(Page 9) + 비전 + 근거 명시** — 거짓 프레이밍 없이 정직 채점 → D-03

### 4. 이 phase 범위 + 순서
- Options: v1/v2 분할 / 한 번에 통합 / 버그 핫픽스 먼저
- **Selected: v1/v2 단계 분할** — v1(감점식+버그+Mode3) / v2(비전 하이브리드), Phase 18 eval로 v1 검증 → D-04

## belle 추가 (2026-06-18, CONTEXT 작성 중)

보유 fault/correct 페어를 비전으로 먼저 비교 분석 → "어디 틀렸나" 정성 ground-truth + 예상 범위 확보 → known-answer 검증. 단 sanity 앵커이지 curve-fit 타깃 아님(overfit 금지). Phase 18 eval 라벨 + v2 de-risk 겸함 → D-05

## Deferred
- 운동 명칭 직관화 / 입문·중급·고급 레벨 UI / 촬영 가이드 UX
