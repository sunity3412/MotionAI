---
phase: 32-result-readability-3-omni
plan: 04
subsystem: result-ui-gates
status: COMPLETE
tags: [mockup-gate, research-gate, D-02, D-03, D-05, D-10, checkpoint-decision]
requires: [32-02, 32-03]
provides:
  - "리서치 게이트(D-02) 확정 — 10항 순서 승인 + 세로 스크롤"
  - "목업 게이트(D-03/D-05/D-10) 확정 — 게임 프레임 안 B(수치 전면 금지) · E2 타이포(하한 17)+Pretendard · 참고 지표 개인화 심사 시뮬레이션(재설계)"
  - "⑤ 참조 원형 채택(Figma 결함 시트) + 확대쌍 사진 쌍 필수 — 32-10 시각 원형"
  - "mockups/ 목업 세트 + 32-GATE-DECISIONS.md 확정 섹션 + 소비처 매핑 표"
affects:
  - "32-07 (타이포 토큰 E2·요약 카드) / 32-10 (감점 카드·드릴다운 시트·게임 프레임·참조 원형) / 32-11 (재배치 세로 스크롤·개인화 심사 시뮬레이션)"
key-files:
  created:
    - .planning/phases/32-result-readability-3-omni/mockups/index.html
    - .planning/phases/32-result-readability-3-omni/mockups/README.md
    - .planning/phases/32-result-readability-3-omni/mockups/section-order.md
    - .planning/phases/32-result-readability-3-omni/mockups/emphasis-tokens.md
  modified:
    - .planning/phases/32-result-readability-3-omni/32-GATE-DECISIONS.md
decisions:
  - "D-02 = 10항 순서 승인 + 세로 스크롤 (폰트·세부는 후속 32-07/11/12 조정 — belle 조건)"
  - "D-10 = 안 B(감점 카드+성장 탭). ★수치 전면/헤드라인 금지, 게이지는 길이만 (belle 강한 교정)"
  - "D-05 = E2(하한 17) + Pretendard 실제 로드"
  - "D-03 = 개인화 심사 시뮬레이션 재설계 (기존 2형태 폐기 — 지식전달형 비판)"
  - "⑤ 참조 원형 = Figma 결함 시트 양식 + 확대쌍 사진 쌍 필수(32-10)"
  - "Figma 결과 화면 = design.md §8 미설계 문서 확정 → 현행 result.tsx 출발점"
metrics:
  completed: 2
  total: 2
  completed_date: 2026-07-21
---

# Phase 32 Plan 04: 리서치 게이트(D-02) + 목업 게이트(D-03/D-05/D-10) Summary

**One-liner:** 4대 게이트 중 2개(리서치·목업)를 공통 shell 기반 self-contained 목업으로 제시하고 belle 결정으로 닫음 — D-02(10항 순서+세로 스크롤), D-10(게임 프레임 안 B, ★수치 전면 금지), D-05(E2 하한 17+Pretendard), D-03(개인화 심사 시뮬레이션 재설계) + ⑤ 참조 원형(Figma 결함 시트+확대쌍) 확정 → 32-GATE-DECISIONS.md에 소비처 매핑과 함께 적재.

## Status: COMPLETE (2/2 tasks)

Task 1(목업 제작) 완료·커밋. Task 2(checkpoint:decision) — belle이 목업 열람 후 왕복 3회로 4건 결정 + ⑤ 참조 원형 채택. 확정본을 32-GATE-DECISIONS.md에 "리서치 게이트 (D-02)" + "목업 게이트 (D-03/D-05/D-10)" 섹션 + "결정 → 소비 플랜/태스크" 매핑 표로 적재. 목업 README에 정정 노트(②탭 각도 전면 배치 폐기·줌 쌍 사진 필수) 병기.

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

## Task 2 — 완료 (belle 결정 4건 + ⑤ 참조 원형 적재)

belle 확정 (32-GATE-DECISIONS.md canon):
1. **D-02** = 10항 순서 승인 + **세로 스크롤(안 V)**. belle 조건 병기: "폰트·세부는 후속 조정"(32-07/11/12). → 32-11
2. **D-10** = **안 B**(감점 카드 + 성장 탭). ★belle 강한 교정: **측정 수치 전면/헤드라인 금지, 게이지는 길이(bar)로만** — ②탭 각도 전면 배치 폐기. → 32-10 · 32-07
3. **D-05** = **E2(하한 17) + Pretendard 실제 로드**. → 32-07
4. **D-03** = **개인화 심사 시뮬레이션 재설계** (기존 2형태 모두 "지식전달형" 폐기) — 내 결함에 IPSF 규칙 적용, 독립 코너(채점 표면 뒤). → 32-11
5. **⑤ 참조 원형(신규)** = belle Figma 과거 결함 상세 시트 양식(단계 배지+부위 칩+신뢰도 / 수치 0 헤드라인 / 근거 박스에만 수치 / 하단 고지) + **결함 확대쌍 사진 쌍 필수**(감점 항목 탭 → 드릴다운 시트에 사진 쌍+문구 3단+근거 박스). → 32-10

**적재 완료:** 32-GATE-DECISIONS.md "## 리서치 게이트 (D-02)" + "## 목업 게이트 (D-03/D-05/D-10)" 섹션 + 매핑 표(①→32-11, ②→32-10·32-07, ③→32-07, ④→32-11, ⑤→32-10). 목업 README 정정 노트 병기. (T-32-08 준수 — 후속 플랜이 이 파일만 신뢰.)

## Deviations from Plan

- Task 1/2 모두 플랜대로. 파일 카운트 ≥3 충족을 위해 section-order.md/emphasis-tokens.md 추가 — must_haves가 요구하는 '섹션 순서안 텍스트' + '강조 체계 스펙'의 belle 확인용 원본이자 32-11/32-07 소비 계약이므로 slop 아님.
- **게이트 결정 결과 (belle 주도 — 내 deviation 아님):** (a) D-03 목업 2형태 모두 폐기 → 개인화 심사 시뮬레이션 재설계, (b) D-10 ②탭 각도 전면 배치 폐기(수치 전면 금지 강화), (c) ⑤ 참조 원형 신규 채택. 목업은 canon 아님을 GATE-DECISIONS·README에 명시.

## Self-Check: PASSED

- 산출물 4종 + SUMMARY + GATE-DECISIONS 확정 섹션 전부 FOUND
- Task 1 commit a871afe / SUMMARY commit f0a80a1 FOUND
- GATE-DECISIONS.md "목업 게이트" 문자열 존재(verify 통과) · 매핑 표 존재
- 커밋 후 git status clean 확인
