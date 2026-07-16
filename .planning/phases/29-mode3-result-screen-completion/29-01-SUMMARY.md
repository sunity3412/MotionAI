---
phase: 29-mode3-result-screen-completion
plan: 01
subsystem: app/result-screen
tags: [injury-risk, safety-flags, copywriting, ota-safe, D-14]
requires: []
provides:
  - "InjuryRiskSection FLAG_COPY {title, why, recommendation} 4종 + 권고 렌더 행"
  - "10-UI-SPEC Copywriting Contract recommendation 동기화"
affects:
  - app/src/components/InjuryRiskSection.tsx
  - .planning/phases/10-injury-risk-flags/10-UI-SPEC.md
tech-stack:
  added: []
  patterns:
    - "클라이언트 카피맵 확장(계약·백엔드 0) — OTA-safe"
    - "테마 토큰 강제(amber 시맨틱, 브랜드 레드 0)"
    - "방어적 graceful skip(if !copy return null) 유지"
key-files:
  created: []
  modified:
    - app/src/components/InjuryRiskSection.tsx
    - .planning/phases/10-injury-risk-flags/10-UI-SPEC.md
decisions:
  - "SafetyFlag.recommendation 백엔드 필드 신설하지 않고 클라이언트 FLAG_COPY 확장으로 D-14 구현 (RESEARCH Pitfall 2) — legacy doc 자동 커버 + 3-way lockstep 비용 0"
  - "기존 EXPERT_REFERRAL 을 섹션 '강사와 점검' 캡션으로 유지 — 카드 recommendation 은 완화 안내에 그치고 진단 소유는 캡션에 위임"
requirements: [D-14]
metrics:
  tasks: 2
  files_changed: 2
  duration: ~20m
  completed: 2026-07-16
---

# Phase 29 Plan 01: 부상 대응법 노출 (D-14) Summary

SafetyFlag 부상 위험 카드에 flagType 4종 전부 "이렇게 해보세요" 권고 행을 추가하고 10-UI-SPEC Copywriting Contract 를 동기화 — 백엔드·계약 변경 0 의 클라이언트 카피맵 확장(OTA-safe)으로 시나리오 9단계 파일럿 gap #1 을 해소했다.

## What Was Built

- **Task 1** (`64b7fc3`) — `InjuryRiskSection.tsx`:
  - `FLAG_COPY` 타입을 `{title, why}` → `{title, why, recommendation}` 으로 확장, flagType 4종(asymmetry / trunk_hyperextension / joint_hyperextension / level_mismatch) 전부에 flagType 별 결이 다른 구체적 완화 행동 카피를 "~해요/~주세요" 체로 채움.
  - `InjuryRiskFlagCard` 에서 why 행 아래 `이렇게 해보세요` 도입구(`captionSmall`, warnAmber) + recommendation 행(`caption`, textPrimary)을 렌더. `accessibilityLabel` 에 intro + recommendation 포함.
  - 기존 `EXPERT_REFERRAL` 섹션 캡션("정확한 판단은 강사 또는 전문가와 함께 확인해 주세요.")을 "강사와 점검" 톤으로 유지 — 부상 확정 단정 0.
  - 신규 스타일(`recoIntro`, `reco`)은 StyleSheet 하단, theme 토큰만(amber 시맨틱, 브랜드 레드 0).
- **Task 2** (`6153c81`) — `10-UI-SPEC.md`:
  - Copywriting Contract 에 recommendation intro + 4종 카피를 컴포넌트 실카피와 문자열 일치로 반영, 카드 구조 서술을 `{title, why, recommendation}` + 강사 점검 캡션으로 갱신, 29-CONTEXT D-14 인용.

## Verification

- `npm run typecheck` (tsc --noEmit) exit 0.
- `grep -c 'recommendation:'` = 5 (type 정의 1 + flagType 4) ≥ 4.
- `grep -c 'copy.recommendation'` = 2 (accessibilityLabel + reco Text) ≥ 1.
- 금지어 게이트: `sed 's/심각도//g' | grep '각도'` 매치 0 (PASS).
- 브랜드 레드 게이트: `grep 'FF4B33\|colors.brand'` 신규 0 (PASS).
- 스코프 게이트: 변경 파일 = InjuryRiskSection.tsx + 10-UI-SPEC.md 2건. backend/ · analysis.ts · contract.md 변경 0 (SCOPE CLEAN).
- 4종 recommendation + intro 카피가 컴포넌트 ↔ 10-UI-SPEC 문자열 일치.

## Deviations from Plan

None — plan executed exactly as written. RESEARCH Pitfall 2(백엔드 필드 신설 금지)를 준수해 클라이언트 카피맵 확장으로만 구현.

Note (환경): 워크트리에 node_modules 부재 → 메인 리포 `app/node_modules` 를 심볼릭 링크(untracked, 커밋 제외)해 typecheck 실행. 소스 변경 아님.

## Known Stubs

None — 모든 flagType 4종에 실 카피가 채워졌고 렌더 경로가 `copy.recommendation` 을 소비한다.

## Follow-ups

- 실기기 시각 확인은 29-08 HUMAN-UAT.md 적립 항목 (batch UAT 원칙 — 즉시 belle 호출 금지).

## Self-Check: PASSED

- FOUND: app/src/components/InjuryRiskSection.tsx
- FOUND: .planning/phases/10-injury-risk-flags/10-UI-SPEC.md
- FOUND: .planning/phases/29-mode3-result-screen-completion/29-01-SUMMARY.md
- FOUND commit 64b7fc3 (Task 1) / 6153c81 (Task 2) / eef10fb (SUMMARY)
