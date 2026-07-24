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

## 후속 (belle 결정) — 확대비교 입구 살리기
- 역립 저신뢰서 확대비교 입구가 억제로 사라진 gap 발견 → belle "예상 부위라도 보여줘야". 후속 커밋 d94ff96: "예상 부위 확대 비교 보기" 입구(안내줄 아래, advisoryOrange) + 시트 estimatedArea hedge(제목 "예상 부위 (참고)"·감점수치→"이 부위는 추정이라 관절별 감점 수치는 종합 점수로만 반영돼요"·크롭+배지 유지). 상세=SUMMARY-followup.md.

## 시뮬레이터 렌더 게이트 — PASS (2026-07-24, 합성 __DEV__ mock, expo run:ios iPhone16)
- 크래시 0. 집계 "= 종합 60점", "AI 공부 중" 안내 1줄, 점수 60 당당, per-joint 팁/카드/심사코너 억제 — 스크린샷 육안 확인(in01-05/07).
- 확대비교 입구 렌더 + 탭→"예상 부위 (참고)" hedge 시트(−N점 없음) — 육안 확인(in01b-01/02).
- ⚠ 실제 자산 필요분(라이브 Pod 없어 미확인, 코드경로는 존재): 오버레이 주황 "예상 부위" 1점(영상 프레임 필요), 실제 크롭 사진.
- **남은 것 = belle 최종 확인 → OTA.**

## 파일
- app/src/types/analysis.ts, app/src/lib/userAnalyses.ts, app/src/components/ScoreBreakdownSection.tsx, app/src/components/DeductionDetailSheet.tsx, app/src/app/analysis/result.tsx
