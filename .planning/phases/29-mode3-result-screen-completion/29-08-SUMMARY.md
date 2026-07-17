---
phase: 29-mode3-result-screen-completion
plan: 08
subsystem: release
tags: [eas, ota, testflight, android-apk, human-uat, phase-gate]

# Dependency graph
requires:
  - phase: 29-05
    provides: production 전환(점수 seam) + D-02 sweep PASS — phase gate 전제
  - phase: 29-06
    provides: D1 비교영상 재서명 fix 배포 — OTA 동승분
  - phase: 29-07
    provides: 진짜 가로 전환 + 정적 import 0 크래시 게이트 — OTA/새 빌드 전제
provides:
  - OTA 발행 production 4d079a4b-0986-453b-a22c-9605b1120082 / preview df164e4d-5359-4168-8783-19a5525de073 (commit f3eb332)
  - iOS production build 28 (aaa54678-72db-478e-b626-59dc8bedc36f) FINISHED + TestFlight 무인 제출 실행 (ASC 6772934567)
  - Android preview-android APK (04dc0e96-65c6-4c94-9885-4caab95aceef) FINISHED — 직원 설치용
  - 29-HUMAN-UAT.md 10항목 적립 (batch UAT — 즉시 belle 호출 금지)
affects: [phase-30, batch-uat, pilot-distribution]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "OTA 발행 전 blocking 게이트: 정적 `from 'expo-screen-orientation'` import grep = 0"
    - "EAS 무인 체인: build production iOS → submit --latest → build preview-android"

key-files:
  created:
    - .planning/phases/29-mode3-result-screen-completion/29-HUMAN-UAT.md
  modified: []

key-decisions:
  - "Android 빌드 IN_QUEUE 상태로 밤사이 마감 보류(belle 결정) → 2026-07-17 아침 FINISHED 확인 후 수동 close-out"
  - "TestFlight(Apple 처리) 최종 확인은 ASC 콘솔 — CLI 로 submission 조회 불가(eas build:view 에 submissions 필드 부재), belle 콘솔 확인 항목으로 이월"

patterns-established:
  - "executor 가 SUMMARY 전에 죽은 plan 은 safe-resume 게이트로 수동 close-out (worktree 커밋 수동 머지 + 스팟체크 재실행 + SUMMARY 후기 작성)"

status: complete
duration: 밤샘 (2026-07-16 야간 실행 + 2026-07-17 아침 close-out)
---

# 29-08 Summary — Phase 29 마감: phase gate + OTA + 빌드 2종 + HUMAN-UAT

## What was built

D-13 마감 체인 전부 완료. 실행은 2026-07-16 야간 executor(worktree)가 수행했고, Android 빌드 IN_QUEUE 대기 중 SUMMARY 작성 전에 세션이 종료되어 2026-07-17 아침 수동 close-out 으로 마감.

### Task 1 — phase gate + OTA 발행

- 크래시 게이트: `grep "from 'expo-screen-orientation'"` VideoCompare.tsx 매치 0 (2026-07-17 아침 재확인 PASS)
- `npm run typecheck` exit 0 (아침 재확인 PASS)
- backend full suite: 29-08 자체는 소스 변경 0 (docs/release only) — wave 3 머지 시점 baseline 대비 신규 실패 0 게이트로 커버 (로컬 44 fail + 12 collection error 는 pre-existing 환경 실패)
- OTA 발행 (commit f3eb332, 미커밋 변경 0):
  - production: `4d079a4b-0986-453b-a22c-9605b1120082`
  - preview: `df164e4d-5359-4168-8783-19a5525de073`
  - runtime 1.0.0 공유 — 구빌드 27 사용자에게 mode3 내역·부상 대응법·D1 fix·라벨 즉시 도달. 가로 코드는 lazy require 라 무해.

### Task 2 — EAS 빌드 2종 + iOS 무인 제출

- iOS production build 28: `aaa54678-72db-478e-b626-59dc8bedc36f` — **FINISHED**, ipa: https://expo.dev/artifacts/eas/rx0ztu0eocqlKAKR0yYQRzVE3DU3zGat-Tjv6xbLZ4I.ipa
- TestFlight 무인 제출 실행 완료 (`eas submit -p ios --latest --non-interactive`, ASC 6772934567, 2026-07-17 01:36 KST 기록). Apple 측 처리 완료 여부는 ASC 콘솔 확인 필요 (CLI 조회 불가) — belle 확인 항목.
- Android preview-android APK: `04dc0e96-65c6-4c94-9885-4caab95aceef` — **FINISHED** (2026-07-17 아침 확인), APK: https://expo.dev/artifacts/eas/wNMqBIqTg4pNaOali3pqJFGmLf1A9kHlEka9Tdp8fLI.apk
- F1(문의하기): expo-mail-composer 네이티브가 새 빌드 2종에 자동 포함 (plugins 기등록, 코드 변경 0) — 실기기 확인은 UAT 항목 9.

### Task 3 — 29-HUMAN-UAT.md 적립

- 10항목 적립 (D-14 / D-01~05 / D-06·07 / D-08+power-spin 드릴다운 / D-10 / D-09 / D-11 / D-12 / F1 / iPad). per-token grep 게이트 전 토큰 통과 (MEDIUM-2).
- batch UAT 원칙 명시 — /gsd-audit-uat 일괄, 즉시 belle 호출 금지.
- commit `00637e1` → main 머지 `91fbc60`.

## Deviations

- executor 가 Android IN_QUEUE 대기 중 SUMMARY 작성 전에 종료 → safe-resume 게이트 발동, 아침 수동 close-out (worktree 수동 머지 + 스팟체크 재실행). 산출물 자체 결손 없음.
- TestFlight Apple 처리 최종 확인은 ASC 콘솔 몫으로 이월 (belle).

## Self-Check: PASSED

- 29-HUMAN-UAT.md 존재 + per-token grep 통과 (D-14/D-01/D-06/D-08/D-09/D-10/D-11/D-12/F1/iPad/power-spin/"belle 호출 금지")
- OTA update ID 2건 기록, iOS FINISHED + 제출 실행, Android FINISHED + APK URL
- typecheck exit 0, 정적 import 게이트 0 매치 (2026-07-17 재검증)
