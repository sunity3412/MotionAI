---
phase: 08.1-axis-metric-redesign
status: not-started
created: 2026-06-09
depends_on: [08-jerk-jitter]
inherits_from: ../08-jerk-jitter/PHASE8-INHERITED-ISSUES.md
---

# Phase 8.1 — Axis Metric Redesign

## 본 phase 가 존재하는 이유

Phase 8 종료 시 3차 sweep 에서 발견된 **axis metric 도메인 정합성 위반** 을 해결하기 위해 belle 명시 결정 (2026-06-09 α) 으로 신설된 phase.

**증상**: 정은지 (폴 세계챔피언) 5/5 reference 영상 모든 phase 에서 axis severity = `high` 출력. 도메인적으로 명백히 잘못된 결과.

**Root cause**: pose_aligned 좌표계 origin 미정의 + threshold 가 image_2d 단위 가정 으로 박제. RTMW 가 `keypoints_2d` 미박제 (B' fix path 가 pole_aligned 3D fallback) — 좌표계 단위 mismatch.

## 단일 evidence source

→ **`../08-jerk-jitter/PHASE8-INHERITED-ISSUES.md`**

본 phase 의 research/discuss/plan/cross-AI review 모든 단계가 위 evidence 를 단일 참조. 외부 AI reviewer (Codex/Gemini/Claude) 가 plan-review-convergence 시 위 evidence 만 읽어도 Phase 8 의 어디서 무엇이 깨졌는지 판단 가능.

## 다음 단계

1. `/gsd-research-phase 08.1` — IPSF Code of Points axis 채점 항목 + 폴스포츠 도메인 "축 이탈" 정의 research
   - **NotebookLM 활용**: [[notebook-lm-pole-sports]] memory — IPSF Code of Points 2024-2025 자동 lookup 노트북
   - PHASE8-INHERITED-ISSUES.md §4 (의사결정 공간 α-1~4 / β-1~3) 에 답 박제
   - PHASE8-INHERITED-ISSUES.md §6 (외부 AI reviewer 5 질문) 이 research scope

2. `/gsd-discuss-phase 08.1` — α/β 옵션 중 선택 + 외부 자료 vs 자체 추론 비율 결정

3. `/gsd-plan-phase 08.1` — 좌표계 fix + threshold calibration + 정은지 sweep 재실행 evidence

4. `/gsd-review 08.1` — 외부 AI plan-review (Codex 등) — PHASE8-INHERITED-ISSUES.md 참조 강제

## Memory invariants 정합

- [[analysis-objectivity-no-human-scores]] — 정은지/belle 점수 ground truth 금지. threshold 수치 calibration 만 OK
- [[scoring-dimensions-ipsf]] — 점수 차원 = IPSF 기반. 폴스포츠-지식 필독
- [[mode3-progress-not-similarity]] — 절대지표 세션간 델타로 성장. % 일치 헤드라인 금지
- [[notebook-lm-pole-sports]] — IPSF 자동 lookup 노트북 활용
- [[codex-reviewer-smplx-bias]] — Codex 신규 architecture 제안 신뢰도 낮음. 기술 스택 결정은 Claude side
- [[plan-vs-pivot-cross-check]] — execute-phase 진입 전 plan scope vs evidence 정합 확인
