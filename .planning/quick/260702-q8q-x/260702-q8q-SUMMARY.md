---
phase: quick-260702-q8q
plan: 01
subsystem: app-result-ui, data-contract
tags: [score-transparency, deduction-tally, contract-lockstep, vision-provenance]
requires:
  - deduction_engine.tally source='vision' 방출 (belle 2026-06-29 결정 A, 이미 production)
  - result.deductionBreakdown Firestore 방출 경로 (Phase 24, 이미 배선·검증됨)
provides:
  - 결과 화면 "점수 계산 내역" 섹션 (100 − records − final tally 노출)
  - 실패 원인 상세 시트 실측 근거 (측정 문구 + 표본 일치 횟수 + 관절별 편차표)
  - DeductionRecord.source {'geometry','vision'} 3-way 계약 정합
  - deductionLabels.ts criterion KO 라벨 + generic angle_vs_reference__{jk} 파싱
affects: [app/src/app/analysis/result.tsx 렌더 트리, ForcePatternDetailModal 시트]
tech-stack:
  added: []
  patterns:
    - criterion 라벨/포맷터 단일 출처 모듈 (deductionLabels.ts)
    - 관절 KO 맵 단일화 (FaultZoomCompare 로컬 맵 → deductionLabels.JOINT_LABEL_KO)
key-files:
  created:
    - app/src/lib/deductionLabels.ts
    - app/src/components/ScoreBreakdownSection.tsx
  modified:
    - app/src/types/analysis.ts
    - docs/contract.md
    - backend/shared/python/sunity_shared/models.py
    - backend/tests/test_deduction_engine.py
    - app/src/lib/userAnalyses.ts
    - app/src/components/ForcePatternDetailModal.tsx
    - app/src/components/FaultZoomCompare.tsx
    - app/src/app/analysis/result.tsx
decisions:
  - "20° 허용오차 상수: 신규 선언 대신 KeypointOverlay.KEYPOINT_DELTA_HIGHLIGHT_DEG 재사용 (플랜 지침의 '기존 상수 있으면 재사용' 분기 — 중복 상수 0)"
  - "evidence 전달 가드 = mode1 + veto applied + Phase 9 실 finding 0건 (fallback finding 일 때만) — 일반 finding 시트 무회귀를 구조적으로 보장"
  - "veto fallback confidence: supportCount 3+ → 0.9 / 2 → 0.6 / 이하 0 (저장된 판정 일치 횟수의 표시 변환, fabricate 아님)"
metrics:
  duration: ~12m (2026-07-02T10:05:56Z → 10:18:13Z)
  completed: 2026-07-02
  tasks: 3/3
  commits: [35e97b8, c2b0911, 1b7d1e4]
---

# Quick 260702-q8q: 결과 화면 점수 근거 공개 (B 작업) Summary

투명 감점-합산 tally(100 − 12 = 88)를 앱이 스스로 설명 — 점수 계산 내역 섹션 + 상세 시트 실측 근거 + source='vision' 계약 drift 수정.

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | 계약 drift 수정(3-way lockstep) + normalize 방어 + lockstep 테스트 | 35e97b8 | analysis.ts, contract.md, models.py, test_deduction_engine.py, userAnalyses.ts |
| 2 | "점수 계산 내역" 섹션 | c2b0911 | deductionLabels.ts, ScoreBreakdownSection.tsx, result.tsx, FaultZoomCompare.tsx |
| 3 | 상세 시트 실측 근거 + 신뢰도 라벨 정합 | 1b7d1e4 | ForcePatternDetailModal.tsx, result.tsx, deductionLabels.ts |

## What Changed

**Task 1 — 계약 lockstep (단일 커밋):**
- `analysis.ts` DeductionRecord.source → `'geometry' | 'vision'` (belle 2026-06-29 결정 A 근거 주석 박제).
- `contract.md` §10.2: source 행 vision provenance 서술 + criterion 카탈로그에 `angle_vs_reference__{joint}` 추가 + deviationSource 설명에 split vision 경로 반영.
- `models.py` DEDUCTION 주석 블록에 source 값 집합 {'geometry','vision'} 서술 추가.
- `test_deduction_engine.py`: `test_vision_measured_split_emits_source_vision` (md 부재 + Gemini split diff 30° → source='vision', to_dict 키 == DEDUCTION_RECORD_KEYS) + `test_geometry_path_source_geometry` (회귀 0) + test_contract_lockstep 에 TS union 문자열 가드.
- `userAnalyses.ts` normalize: deductionBreakdown null-guard (객체 + records 배열만 통과, records 항목 객체 필터, malformed → undefined — 구 doc 크래시 0).

**Task 2 — 점수 계산 내역:**
- `deductionLabels.ts` 신설: criterion → KO 라벨 (split_angle → '다리 스플릿 각도' 등 6종 고정 + `angle_vs_reference__{jk}` generic 파싱 → '{관절}(정은지 대비 각도)', 미등록 id 그대로 노출), deviationSource/unit 별 행 포맷터 (tol 역산: reference_relative = measured − deviation; 음수/비유한이면 허용오차 구문 생략), source='vision' → "(영상 비교 측정)" 꼬리.
- `ScoreBreakdownSection.tsx` 신설: 기준 100 헤더 → record 행 (라벨+detailText / −points brand 강조, 저장 순서) → "= 종합 {final}점" (breakdown.final 사용) + 빈 records/coverageGaps/fallback 캡션 + 행 단위 accessibilityLabel. 토큰만.
- `result.tsx`: 세부 점수 + auxCaption 직후 배치, 가드 `cmp.mode === 'mode1' && result.deductionBreakdown != null`. reframe 캡션에 "아래 '점수 계산 내역'에서 감점 근거를 확인할 수 있어요." 연결 문장 (섹션 존재 시).
- `FaultZoomCompare.tsx`: 로컬 KEYPOINT_KO 제거 → JOINT_LABEL_KO import (중복 2벌 금지).

**Task 3 — 실측 근거 + 신뢰도:**
- `ForcePatternDetailModal` optional `measuredEvidence` prop (inline type): 측정 방법 실문구 교체 + "분석 표본 N회에서 같은 결함이 확인됐어요" (절대 횟수만 — 분모 데이터 없음) + 관절별 편차표 (내/기준/차이, |delta| > 20° brand 강조) + "확인하기" 문구 교체. evidence 없으면 현행 템플릿 (Phase 9 finding/legacy 무회귀).
- `result.tsx` evidence useMemo: mode1 + applied + fallback finding 전용, windowMedianAngleDeltas → 관절 KO + 소수 1자리, 첫 non-fallback record → deductionLabels 포맷터 재사용 실측 한 줄.
- 신뢰도 라벨 모순 해소: veto fallback finding confidence 0 하드코딩 → supportCount 기반 (3+ → 0.9 '높음', 2 → 0.6 '보통', 이하 0). confidenceLabel 함수 무변경.

## Deviations from Plan

**1. [Rule 1 - 사실 정정] models.py 에 "source='geometry' 하드 리터럴" 문구 부재**
- **Found during:** Task 1
- **Issue:** 플랜은 models.py DEDUCTION 주석의 기존 서술을 "갱신"하라 했으나 해당 문구는 analysis.ts 에만 존재.
- **Fix:** models.py 에 값 집합 서술을 신규 추가 (플랜 의도 동일 달성).
- **Commit:** 35e97b8

**2. [플랜 내 분기 선택] IPSF_TOLERANCE_DEG 신규 선언 → 기존 상수 재사용으로 전환**
- **Found during:** Task 3
- **Issue:** Task 2 에서 deductionLabels 에 IPSF_TOLERANCE_DEG=20 을 선언했으나, Task 3 조사에서 `KeypointOverlay.KEYPOINT_DELTA_HIGHLIGHT_DEG = 20.0` (dimensions.py _LINE_TOL_DEG 정합) 기존 export 발견 — 플랜의 "기존 20 상수 있으면 재사용" 분기 해당.
- **Fix:** deductionLabels 중복 상수 제거, result.tsx 가 KEYPOINT_DELTA_HIGHLIGHT_DEG import.
- **Commit:** 1b7d1e4

## Verification

- `cd backend && python3 -m pytest tests/test_deduction_engine.py -q` — **45 passed** (기존 43 + 신규 2)
- `cd app && npm run typecheck` — clean (Task 1/2/3 각각 재확인)
- grep 게이트: `git diff --stat 72af90f..HEAD` 에 `backend/functions/pipeline/app.py` **부재** (동시 진행 A 작업 충돌 0)
- 점수 계산 로직/엔진 수치 무변경 — deduction_engine.py diff 0

## Known Stubs

없음 — 신규 섹션/시트는 실데이터(deductionBreakdown/visionVeto) 배선 완료. 데이터 미보유 doc(legacy/mode3)은 의도적 숨김 (stub 아님 — 하위호환 가드).

## Threat Flags

없음 — 표시 전용 변경, 신규 데이터 방출/네트워크 표면 0.

## 수동 검증 (belle 실기기 — 선택)

kip-up fault 88점 문서(18796f8b…) 열기 → "점수 계산 내역" 100 − 12(다리 스플릿 각도, 영상 비교 측정) = 88 확인 → 실패 원인 상세보기 → 실측 문구/편차표/표본 일치 횟수 + 신뢰도 '높음' 확인.

## Self-Check: PASSED

- app/src/lib/deductionLabels.ts — FOUND (contains `angle_vs_reference__`)
- app/src/components/ScoreBreakdownSection.tsx — FOUND (130 lines ≥ 60)
- analysis.ts contains `'geometry' | 'vision'` — FOUND
- userAnalyses.ts contains `deductionBreakdown` — FOUND
- commits 35e97b8 / c2b0911 / 1b7d1e4 — FOUND in git log
