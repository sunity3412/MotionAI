---
status: partial
phase: 03-bodyprofileinput
source: [03-VERIFICATION.md]
started: 2026-06-15T03:40:00Z
updated: 2026-06-15T03:40:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. 작은 화면 keyboard-safe 폼 레이아웃 (R6)
expected: iPhone SE급 작은 화면에서 마이 → 내 몸 정보 입력 → 5필드 모두 탭하여 키보드 open 상태에서도 저장 CTA 가 스크롤로 도달·탭 가능하고, 통증부위 칩이 하단 safe area 와 겹치지 않음. 부분 입력 저장 성공 후 카드가 요약 갱신.
result: [pending]

### 2. 첫 분석 권유 모달 전체 플로우 (R1/R2/D-06)
expected: 첫 분석 게스트로 영상 pick → 권유 모달 1회 출현(분석을 막지 않음). [건너뛰기]/백드롭/native back 4-경로 모두 보류된 영상으로 분석 자동 재개. dismiss 후 재pick 시 모달 미출현(once-flag 영속). [입력하기]→폼 저장 후 동일 영상으로 분석 재개. 결과 화면에 분석-당시 BodyProfile snapshot row 표기.
result: [pending]

### 3. CR-01 회귀 — 콜드스타트/느린 네트워크 prompt 오출현
expected: 이상적으로는 프로필을 이미 입력했거나 이미 건너뛴 사용자에게는 콜드스타트(앱 첫 진입 직후) 또는 느린 네트워크에서 영상 pick 시 권유 모달이 뜨지 않아야 함.
result: resolved (code fix) — `maybePromptBeforeRoute` 에 `if (profileLoading) { routeAfterPick(picked); return; }` 가드 추가. 구독 로딩 중에는 권유를 보류하고 즉시 라우팅(게스트 우선). 잔여 확인: 실기기에서 콜드스타트 pick 시 모달 미출현 스모크 확인 권장.

## Summary

total: 3
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0
resolved: 1

## Gaps
