---
phase: 32-result-readability-3-omni
plan: 04
subsystem: result-ui-gates
status: PAUSED_AT_CHECKPOINT
tags: [mockup-gate, research-gate, D-02, D-03, D-05, D-10, checkpoint-decision]
requires: [32-02, 32-03]
provides:
  - "mockups/ 목업 세트 (강도별 + 최악 케이스 + 참고 지표 2형태 + 강조 체계) — belle 결정 대기"
  - "D-02 섹션 순서안 텍스트 원본 (section-order.md)"
  - "D-05 강조 토큰 스펙 (emphasis-tokens.md)"
affects:
  - "32-07 (타이포 토큰·요약 카드) / 32-10 (감점 카드) / 32-11 (재배치·참고 지표·세로/가로) — belle 결정 확정 후 입력"
key-files:
  created:
    - .planning/phases/32-result-readability-3-omni/mockups/index.html
    - .planning/phases/32-result-readability-3-omni/mockups/README.md
    - .planning/phases/32-result-readability-3-omni/mockups/section-order.md
    - .planning/phases/32-result-readability-3-omni/mockups/emphasis-tokens.md
  modified: []
decisions:
  - "목업은 self-contained HTML 1파일(index.html) + 텍스트 원본 2종 — belle Mac에서 더블클릭, 라이브 Figma MCP 불필요"
  - "공통 shell 1벌 + 동일 fixture(최악 케이스) 재사용, 안별 변형 플래그만 교체 (전면 재제작 금지)"
  - "Figma 결과 화면 = design.md §8 미설계 문서 확정 → 현행 result.tsx 출발점"
metrics:
  completed: 1
  total: 2
  checkpoint_task: 2
  completed_date: 2026-07-21
---

# Phase 32 Plan 04: 리서치 게이트(D-02) + 목업 게이트(D-03/D-05/D-10) Summary

**One-liner:** 4대 게이트 중 2개(리서치·목업)를 belle 결정으로 닫기 위한 산출물 — 공통 shell 기반 self-contained 비교 목업(강도별 A/B/C + 최악 케이스 4종 + 참고 지표 2형태 + 강조 체계 E1/E2 + D-09 검사표) + 섹션 순서/강조 토큰 텍스트 원본을 제작·커밋. **Task 2 checkpoint:decision 에서 belle 결정 대기 중 (plan 미완료).**

## Status: PAUSED AT CHECKPOINT (Task 2 / 2)

Task 1(목업 제작)은 완료·커밋. Task 2는 `checkpoint:decision` gate(`autonomous: false`) — belle의 UI 설계 결정이 필요하므로 자동 진행 불가. 구조화된 checkpoint 보고를 오케스트레이터에 반환(belle 릴레이). belle 결정 후 continuation agent가 32-GATE-DECISIONS.md에 확정 섹션 + 소비처 매핑 표를 적재하며 완료.

## Task 1 — 완료 (commit a871afe)

**제작물 (mockups/):**
- `index.html` — self-contained 비교 인덱스. 상단 탭 5개(섹션 순서 / 게임 프레임 / 최악·엣지 / 참고 지표 / 강조·타이포), 상단 라디오로 강조 스케일 E1/E2 전 보드 즉시 적용. iPhone 프레임 목업을 fixture 기반 JS 렌더.
- `README.md` — 안별 1줄 요약 + D-09 검사표 + shell/fixture 재사용 구조 + Figma 결과 + 소비처 표.
- `section-order.md` — D-02 리서치 게이트 제출안(10항 순서 + 정직한 근거 지형). 32-11 소비.
- `emphasis-tokens.md` — D-05 강조 토큰 스펙(옵션 b 신규 단계 + E1/E2 + 강조 규칙). 32-07 소비.

**자체 검증 통과:**
- 파일 4개(verify ≥3 OK) · `<div>` 균형 169/169 · JS 런타임 전 렌더 함수 무오류 실행
- 게임 프레임 확정 3요소(게이지+미션+기록배지)가 안 A/B/C 전부 포함 확인
- 최악 케이스 = 감점 7 + 장문 측정 문구(허용 초과 19°, wrap) + 안전 결함(게임 프레임 제외)
- % 환산 0건 · 측정 수치는 소형 배지만 · IPSF 규정 수치는 심사 코너 본문(구분 적용)
- D-17 확정(양옆 동시+탭 확대·자세 카드 존치·큐 구간당 1개)과 모순 없음

## Task 2 — CHECKPOINT (belle 결정 대기)

belle이 결정할 4항 (상세·권장안은 checkpoint 보고 참조):
1. **D-02 섹션 순서 승인/수정 + 세로 스크롤 vs 가로 카드 넘김** → 32-11 소비
2. **D-10 게임 프레임 범위** A(감점 카드 한정)/B(+성장 탭)/C(전면+추가 아이디어) → 32-10·32-07 소비
3. **D-05 강조 스케일** E1(중)/E2(강, 하한 17) + Pretendard 로드 여부 → 32-07 소비
4. **D-03 참고 지표 형태** 독립 심사 코너 vs 감점 카드 흡수 → 32-11 소비

**belle 결정 후 continuation 작업:** 32-GATE-DECISIONS.md에 "## 리서치 게이트 (D-02)" + "## 목업 게이트 (D-03/D-05/D-10)" 섹션 + "결정 → 소비 플랜/태스크" 매핑 표 적재 → plan 완료. (T-32-08 완화: belle 미결정 상태에서 GATE-DECISIONS.md에 확정 섹션 선기재하지 않음 — 후속 플랜이 이 파일만 신뢰하므로.)

## Deviations from Plan

없음 — Task 1은 플랜대로 실행. Task 2는 설계대로 checkpoint 정지.
(파일 카운트 ≥3 충족을 위해 section-order.md/emphasis-tokens.md를 추가했으나, 이는 must_haves가 요구하는 '섹션 순서안 텍스트' + '강조 체계 스펙'의 belle 확인용 원본이자 32-11/32-07 소비 계약이므로 slop 아님.)

## Self-Check: PASSED

- 산출물 4종 + SUMMARY 전부 FOUND
- Task 1 commit a871afe FOUND
- Task 2는 checkpoint(파일 산출 없음, 구조화 보고 반환)
