---
status: complete
quick_id: 260724-q6b
date: 2026-07-24
---

# Quick Task 260724-q6b — IN-01 역립 저신뢰 결과화면 표현 강등

## What shipped

앱측이 이미 배포된 백엔드 `result.attributionReliability.unreliable` 마커(main d5490a8)를 소비하도록 배선. `attributionUnreliable = result.attributionReliability?.unreliable === true` 단일 게이트로, 역립 저신뢰 시 결과화면의 **8개 per-joint 단정 표면**을 "확정" → "예상/집계"로 강등.

**LOCKED 4 (belle 확정 설계):**
1. 영상 오버레이 — 붉은/노란 8점 → 주황 "예상 부위" ≤1점 (`colors.advisoryOrange` 재사용)
2. 점수 계산 내역 — 관절별 행 → 집계 1행 (`= 종합 {final}점` 불변, ScoreBreakdownSection aggregateMode prop)
3. 코칭 팁 — per-joint 팁 억제, correction 헤드라인 관절명 제거
4. 확대비교 크롭 — 유지하되 "예상 부위" 라벨 (DeductionDetailSheet)

**ADDITIONAL 4 (플래너 grep 감사로 발견):**
5. topFix "오늘 고칠 것" 카드 — 억제 (clean-card 오폴백 방지 확인)
6. "다른 감점 항목" 접힌 카드 — 억제
7. SummaryCard todayFix → aggregate 라우팅 / nextAction 숨김 (TODAY_NONE 오해 방지)
8. 심사 정보 코너 per-joint records.map — 억제

**동작비교 안내 1줄 (유일한 "AI 공부 중"):**
- Mode1: "거꾸로 자세는 관절 하나하나까진 AI가 아직 공부 중이에요. 정은지 선수 영상을 자세히 비교해보세요."
- Mode3 2번째+: "점수 기준으로 이전보다 발전하고 있어요. 거꾸로 자세 세부 관절은 AI가 아직 공부 중이에요."
- Mode3 첫: "첫 분석이에요 — 다음부터 발전을 비교해드려요. 거꾸로 자세 세부는 AI가 공부 중이에요."

## 유지(강등 안 함, belle 원칙 정렬)
- 강사 질문(ask-coach), 보완 운동 이유 — 코치 라우팅/처방이지 per-joint 단정 아님. [[product-role-interpret-act-or-ask-coach]] ③ 정렬.

## Hard invariants 준수
- overallScore / deductionBreakdown.final / deductionBreakdown.records **byte 불변** (표현만).
- 신규 카피 전부 module-level SCREAMING_SNAKE 상수. 테마 토큰만(하드코딩 0), 라이트 전용, 이모지 0.
- unreliable=false/부재 → 전 삼항 else → 정상 분석 렌더 diff 0.
- `npm run typecheck` (tsc --noEmit) clean.

## Commits (main, cherry-pick from worktree)
- 65ed94b feat: AttributionReliability contract type + defensive normalize
- c53627d feat: ScoreBreakdownSection aggregate mode prop
- a7c2587 feat: attributionUnreliable gate — LOCKED-4 + guidance line
- 604b2bf feat: remaining 4 per-joint surfaces (same gate)

## 남은 게이트 (미완)
- **시뮬레이터 렌더 확인** (verify-ui-on-simulator-before-ota) — unreliable 케이스에서 크래시 0 + 8표면 강등 육안 확인. typecheck는 렌더 크래시 미포착. 합성 unreliable doc 시딩 필요.
- OTA는 belle 확인 후.

## 파일
- app/src/types/analysis.ts, app/src/lib/userAnalyses.ts, app/src/components/ScoreBreakdownSection.tsx, app/src/components/DeductionDetailSheet.tsx, app/src/app/analysis/result.tsx
