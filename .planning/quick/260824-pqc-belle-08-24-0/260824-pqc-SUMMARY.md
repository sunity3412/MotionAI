---
phase: quick-260824-pqc
plan: 01
subsystem: ui
tags: [react-native, expo, illustration-removal, result-screen, deduction-sheet]

requires:
  - phase: quick-260818-nc2
    provides: 시트 그림 카드 분기 (illustrationAvailable) — 이번에 제거된 대상
  - phase: quick-260822-oe1
    provides: 발전 캡션 배선 (findPreviousComparable/extractCriterionMeasure) — 이번에 제거된 대상
  - phase: quick-260824-bxf
    provides: PROGRESS_NOISE_THRESHOLDS criterion 배선 — 이번에 제거된 대상
  - phase: quick-260824-jw4
    provides: ghostPose 잔상 배선 — 이번에 제거된 대상
provides:
  - 일러스트 기능 전면 제거된 결과 화면 (belle 08-24 결정 — 확대비교·모션 분석 집중)
  - DeductionDetailSheet 항상-텍스트 goalLine 경로 (그림 카드 분기 소멸, 같은 문장 이중 표시 없음)
  - app/src 전체 일러스트 참조 grep 0 (주석 포함), 번들 에셋 21장 제거
affects: [result-screen, deduction-sheet, ota-publish]

tech-stack:
  added: []
  patterns: ["기능 제거 = git rm + 참조 grep 0 게이트 (주석 포함) — 죽은 코드 0, 복구는 git 이력"]

key-files:
  created: []
  modified:
    - app/src/app/analysis/result.tsx
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/components/VideoCompare.tsx (주석만)
    - app/src/lib/__tests__/screenVocabulary.test.ts
    - app/src/lib/deductionSheet.ts (주석만)
  deleted:
    - app/src/components/DefectIllustration.tsx (621줄)
    - app/src/lib/illustrationScene.ts (343줄)
    - app/src/lib/illustrationHow.ts (284줄)
    - app/src/lib/progressCaption.ts (189줄)
    - app/src/lib/ghostPose.ts (220줄)
    - app/src/lib/__tests__/illustrationScene.test.ts (404줄, 기지 실패 8 포함)
    - app/src/lib/__tests__/illustrationHow.test.ts (110줄)
    - app/src/lib/__tests__/progressCaption.test.ts (296줄)
    - app/src/lib/__tests__/ghostPose.test.ts (200줄)
    - app/assets/illustrations/ (jpg 21장)

key-decisions:
  - "VideoCompare renderCueIllustration prop 잔류 (코드 무접촉, 주석만 갱신) — 미전달 = 기존 fail-closed 렌더 0, 큐 행 레이아웃 회귀 0 우선 (오케스트레이터 결정)"
  - "deductionSheet.ts primaryMeasure 필드·splitGoalClause·buildCauseGroupKeys export 잔류 — 뷰모델·테스트 무접촉 원칙 (제거 시 58K 테스트 파일 연쇄)"
  - "PROGRESS_NOISE_THRESHOLDS(split_angle 문턱 상수)는 캡션 전용이라 함께 삭제 — 문턱 실측 원장은 .planning 잔존 (무접촉)"

patterns-established:
  - "제거 게이트: typecheck + 삭제 심볼 grep 0 (주석 포함) + node --test 전량 실패 0"

requirements-completed: [QUICK-260824-PQC]

duration: 5min
completed: 2026-08-24
---

# Quick 260824-pqc: 일러스트 기능 전면 제거 Summary

**belle 08-24 결정 실행 — 결함 일러스트·킵업 승인본·발전 캡션·파워스핀 rotate/ghostPose 전부 제거 (컴포넌트 1 + lib 4 + 테스트 4 + 에셋 21장, 총 −2,892줄), 시트는 실사진 비교·원인·수치·미션 텍스트 경로만 잔존**

## Performance

- **Duration:** 5 min
- **Started:** 2026-08-24T09:39:15Z
- **Completed:** 2026-08-24T09:44:44Z
- **Tasks:** 3
- **Files modified:** 5 (+ 삭제 30: 코드 9 + 에셋 21)

## Accomplishments

- 표시 배선 3면 제거: 부위 상세 시트 목표 자세 카드(illustrationSlot/illustrationAvailable), 재생 중 illu-float 큐 일러스트(cueIllustrationForRecordId), 발전 캡션 재료(doneAnalyses 구독 + findPreviousComparable/extractCriterionMeasure)
- DeductionDetailSheet goalLine 항상-텍스트 경로 성립 (quick-260818-nc2 그림 카드 분기 소멸 — 같은 문장 이중 표시 없음). React import·scrollH state·ILLUST 상수·illustCard/illustCap styles 전부 제거
- lib 4종(illustrationScene/illustrationHow/progressCaption/ghostPose)·테스트 4종·assets/illustrations 21장 git rm — app/src 전체 참조 grep 0 (주석 포함)
- screenVocabulary EXCLUSIONS 에서 illustrationScene provenance 항목 정리 (빈 맵, 스캔 로직 무접촉)

## Task Commits

1. **Task 1: 표시 배선 제거 — result.tsx / DeductionDetailSheet / DefectIllustration 삭제** - `eddbdf0e` (feat) — 4 files, −835줄
2. **Task 2: lib 4종·테스트 4종·에셋 21장 제거 + 잔존 참조 grep 0** - `fb2eef19` (feat) — 31 files, −2,057줄
3. **Task 3: 전량 게이트** - 커밋 없음 (게이트 실행만 — 파일 변경 0)

## Verification (전량 게이트)

- `npm run typecheck` GREEN (Task 1 직후·Task 3 재확인, exit 0)
- `node --test src/lib/__tests__/*.test.ts *.test.mjs`: **before 234 (233 pass / 기지 fail 1 = illustrationScene test 8) → after 201 (201 pass / fail 0)**, exit 0. 감소 33 = 삭제 테스트 4파일분 (예상 감소). 허용 실패 0 성립 — 기지 실패는 파일 삭제로 소멸
- grep 0 (Task 1): `DefectIllustration|illustrationSlot|illustrationAvailable|cueIllustrationForRecordId|findPreviousComparable|extractCriterionMeasure|buildCauseGroupKeys|doneAnalyses` — src/app + src/components 부재
- grep 0 (Task 2): `DefectIllustration|illustrationScene|illustrationHow|progressCaption|ghostPose|assets/illustrations|buildProgressCaption|hasIllustrationFor|illustrationAssetForPart|buildHowOverlay|HOW_ANCHORS|GHOST_ALIGN|buildGhostPoseForAsset|PROGRESS_NOISE` — app/src 전체 부재
- 부재 확인: DefectIllustration.tsx, lib 4종, __tests__ 4종, assets/illustrations/ 디렉터리
- 회귀 0 (구조적): VideoCompare diff = 주석 2줄 교체만 (git diff 실측), deductionSheet.ts diff = primaryMeasure 주석만, voiceCueRecordId·큐 자막·음성·부위 강조 경로 무접촉, 시트 크롭·블록·불릿·강사 연결·AI 고지 렌더 경로 무접촉

## Decisions Made

- result.tsx:1206 주석의 `buildCauseGroupKeys` 언급을 "deductionSheet 의 원인 키 단일 출처"로 재서술 — 함수는 lib 에 잔존하고 buildPartGroups/buildPartChips 가 내부 소비하므로 의미 보존, grep 게이트(주석 포함)만 충족
- 나머지는 플랜 그대로 (scope_fence 준수: VideoCompare·deductionSheet 코드 무접촉, OTA 미발행, 백엔드·Firestore·.planning 원장 무접촉)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## OTA / 후속 (범위 밖)

- **OTA 미발행** — 제거 반영에 새 OTA 필요하나 belle 한마디 대기. 코드베이스는 발행 준비 상태 (typecheck·테스트 전량 GREEN)
- 시뮬 실증(시트 텍스트 경로·큐 재생 육안) = 오케스트레이터 후속

## Next Phase Readiness

- 확대비교·모션 분석 집중 표면 성립 — 시트에 실사진 비교·원인 문구·수치(numNote)·미션(cueLine) 잔존으로 "어떻게" 역할 유지
- 복구 필요 시 git 이력: eddbdf0e^ (컴포넌트·배선), fb2eef19^ (lib·테스트·에셋)

## Self-Check: PASSED

- 삭제 9파일 + assets/illustrations/ 전부 부재 확인 (파일시스템 실측)
- 커밋 eddbdf0e / fb2eef19 git log 존재 확인
- SUMMARY.md 존재 확인
- 워킹트리 잔여 변경 = `.planning/quick/260824-gt1-.../compose_ghost_r6.py` (착수 전부터 있던 무관 변경 — 무접촉)

---
*Phase: quick-260824-pqc*
*Completed: 2026-08-24*
