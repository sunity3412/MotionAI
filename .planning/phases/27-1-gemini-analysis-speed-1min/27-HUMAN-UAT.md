---
status: partial
phase: 27-1-gemini-analysis-speed-1min
source: [27-VERIFICATION.md]
started: 2026-07-08T11:22:29Z
updated: 2026-07-08T11:22:29Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. zoom pending→done 전이 (D-06)

expected: mode1 분석 완료 시 점수가 먼저 도착하고, 결과 화면 확대비교 카드 자리에 로딩 placeholder가 표시된다. 몇 초 뒤 zoom 이미지가 도착하면 자동으로 이미지로 전환된다 (실측 +7.7s). zoom 생성 실패/레거시 문서는 기존처럼 카드가 조용히 숨겨진다. pending이 180초 넘게 지속되면 로딩 대신 숨김으로 폴백 — 무한 로딩이 없어야 한다.
result: [pending]

### 2. 폴스포츠 팁 로테이션 (D-07)

expected: 분석 대기 화면에서 폴스포츠 팁/동작 소개 텍스트 12종이 6초 간격으로 로테이션된다. 기존 안심 카피(4초 주기)와 겹치지 않고 자연스럽게 표시된다.
result: [pending]

### 3. 진행률 전진 체감 (D-02)

expected: 분석 중 진행률이 85%에서 얼어붙지 않고 실제 단계 진행에 맞춰 전진한다 (comparison 구간 base 40 → 상한 97 재배분). 오래 머무는 구간이 있어도 "멈췄다"는 오인이 없어야 한다.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
