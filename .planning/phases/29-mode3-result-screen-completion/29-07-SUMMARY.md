---
phase: 29-mode3-result-screen-completion
plan: 07
subsystem: ui
tags: [expo, react-native, expo-screen-orientation, expo-modules-core, video, orientation, ota]

# Dependency graph
requires:
  - phase: 29-04
    provides: 전체화면 비교 뷰어(VideoCompare) 회전 핵 기반 — 이 플랜이 진짜 가로로 확장
provides:
  - VideoCompare 전체화면 뷰어 진짜 가로(LANDSCAPE) 전환 (새 빌드) + 90° 회전 핵 폴백 (구빌드 27)
  - expo-screen-orientation ~9.0.9 네이티브 의존성 + app.json plugin 등록
  - requireOptionalNativeModule 런타임 감지 패턴 (정적 import = OTA 크래시 회피)
affects: [29-08-eas-build-submit, video-compare, mode3-result]

# Tech tracking
tech-stack:
  added: [expo-screen-orientation ~9.0.9]
  patterns:
    - "런타임 네이티브 모듈 감지: requireOptionalNativeModule + 함수 스코프 lazy require (정적 import 금지)"
    - "OTA 안전 네이티브 도입: version/runtimeVersion 불변으로 구빌드-신빌드 채널 공유 + 폴백 분기"

key-files:
  created: []
  modified:
    - app/package.json
    - app/package-lock.json
    - app/app.json
    - app/src/components/VideoCompare.tsx

key-decisions:
  - "진입 lock 은 Modal 마운트 후 effect, 이탈은 closeFullscreen 이 선제 PORTRAIT_UP lock — flicker 방지 + 언마운트 안전망은 effect cleanup"
  - "네이티브 가로 분기는 fsRotated 90° transform·축 스왑 오프셋을 생략하고 window 치수 그대로 사용 (D4 비율 이상 근본 해소)"
  - "구빌드 회전 핵 코드 byte-보존, FULLSCREEN_ZOOM=1.35 무변경 (핵 제거는 파일럿 이후 deferred)"
  - "version(1.0.0)/runtimeVersion(appVersion)/react-native-screens(~4.16.0) 전부 불변 — OTA 채널 공유 + lock 무력화 회귀 차단"

patterns-established:
  - "requireOptionalNativeModule('ExpoScreenOrientation') != null 로 module-level 감지, lockAsync 는 함수 스코프 require 뒤에서만"
  - "네이티브 기능 추가 시 구빌드 폴백 분기를 남기고 크래시 게이트(정적 import 0)를 acceptance 로 고정"

requirements-completed: [D-11, D-12]

# Metrics
duration: 14min
completed: 2026-07-17
---

# Phase 29 Plan 07: 전체화면 비교 뷰어 진짜 가로 전환 Summary

**expo-screen-orientation ~9.0.9 를 OTA-안전하게 도입해 VideoCompare 전체화면 뷰어가 새 빌드에서 진짜 가로(LANDSCAPE)로 전환되고, 구빌드(TestFlight 27)는 90° 회전 핵 폴백으로 크래시 없이 동작한다.**

## Performance

- **Duration:** ~14 min
- **Completed:** 2026-07-17
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- expo-screen-orientation ~9.0.9 를 `npx expo install` 로 SDK 54 번들 고정 설치 (npm latest 57.0.0 비호환 회피) + app.json plugin 등록
- version/runtimeVersion/react-native-screens 전부 불변 — 구빌드-신빌드 OTA 채널 공유 유지, lock 무력화 회귀 차단
- VideoCompare 에 requireOptionalNativeModule 런타임 감지 추가 → 새 빌드는 진짜 가로 lock, 구빌드는 회전 핵 폴백 (정적 import 0 = OTA 크래시 게이트 통과)
- 진짜 가로 분기에서 90° transform·축 스왑 치수 생략 → 회전 핵의 비율 왜곡(D4) 근본 해소

## Task Commits

각 태스크는 원자적으로 커밋되었다:

1. **Task 1: expo-screen-orientation 설치 + app.json plugin** - `9a106f7` (chore)
2. **Task 2: VideoCompare 가로 전환 분기 — 런타임 감지 + 회전 핵 폴백** - `92d40aa` (feat)

## Files Created/Modified
- `app/package.json` - expo-screen-orientation ~9.0.9 의존성 추가 (rns/version 불변)
- `app/package-lock.json` - expo-screen-orientation 단일 패키지 추가 (공급망 diff 게이트 통과)
- `app/app.json` - plugins 배열에 "expo-screen-orientation" 문자열 등록 (version/runtimeVersion 무변경)
- `app/src/components/VideoCompare.tsx` - 런타임 네이티브 감지 + lockAsync(LANDSCAPE_RIGHT/PORTRAIT_UP) 진입/이탈 시퀀스 + Modal supportedOrientations landscape 허용 + fsLandscape 컨테이너 분기 (회전 핵 폴백 보존)

## Decisions Made
- **진입/이탈 lock 시퀀스:** 진입은 Modal 마운트(commit) 이후 useEffect 에서 lockLandscape (마운트 전 lock 무효, Pattern 4). 이탈은 closeFullscreen 이 setState 전에 선제 lockPortrait (역순이면 세로 복귀 전 Modal 닫혀 flicker). effect cleanup 의 lockPortrait 는 언마운트·화면 이탈 등 다른 경로 안전망.
- **네이티브 분기 치수:** fsShort/fsLong 은 min/max 파생이라 orientation-agnostic — 새 style `fsLandscape`(top/left 0, transform 없음)로 window 치수를 그대로 채우고, 폴백은 `fsRotated`(rotate 90deg) + 중앙 오프셋 유지. fsBoxW/fsBoxH·renderFullscreenSlot 는 양 분기 공용(수정 불필요).
- **lockAsync 실패 무해화:** iPad/기기 자동회전 설정 등에서 lock 실패 가능(Pitfall 5) → `.catch(() => {})` 로 세로 유지, HUMAN-UAT 관찰 항목으로 이관.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- 워크트리에 node_modules 부재 → `npm install`(lockfile 기준)로 로컬 설치 후 `npx expo install` 및 `npm run typecheck` 실행. node_modules 는 gitignore 되어 커밋에 포함되지 않음 (package.json/package-lock.json/app.json 만 스테이징).
- `node -e "require('expo-modules-core')"` 직접 실행은 Node 24 의 node_modules TS 스트리핑 제약으로 실패하나, Metro/tsc 경로와 무관 — build/*.d.ts 에 `requireOptionalNativeModule` 익스포트 확인 + `tsc --noEmit` exit 0 으로 검증.

## Known Stubs
None.

## Verification
- `cd app && npm run typecheck` exit 0 (Task 1·2 각각)
- grep 게이트: 정적 `from 'expo-screen-orientation'` 매치 0 (크래시 게이트) / requireOptionalNativeModule 존재 / 함수 스코프 lazy require 존재 / lockAsync LANDSCAPE_RIGHT·PORTRAIT_UP 양쪽 존재 / Modal supportedOrientations 'landscape' 포함 / 회전 핵 rotate transform 보존 / FULLSCREEN_ZOOM === 1.35 유지
- lockfile diff: expo-screen-orientation 단일 node_modules 엔트리 추가 (rns 등 무관 패키지 변동 0)

## HUMAN-UAT 후보 항목 (29-08 이 HUMAN-UAT.md 로 적립)
- 새 빌드: 전체화면 뷰어 진입 시 진짜 가로 전환, 닫으면 세로 복귀, 앱 전체 세로 고정 유지 (A1 — iOS orientation portrait 필드 vs lockAsync 우선순위)
- 진입/이탈 flicker 관찰 (A2 — Modal supportedOrientations + lockAsync 병용)
- iPad 가로 lock 동작 관찰 (Pitfall 5 — accept 처리, iPhone 중심)
- 구빌드(TestFlight 27): 같은 OTA 번들 로드 시 크래시 0 + 90° 회전 핵 폴백 정상

## Next Phase Readiness
- 29-08 EAS 빌드/제출에 네이티브 모듈(expo-screen-orientation) 동승 준비 완료 — `npx expo install` 고정 버전이라 prebuild/EAS Build 시 SDK 54 정합.
- HUMAN-UAT 항목(가로 전환·복귀·flicker·iPad·구빌드 무크래시)은 29-08 에서 적립.

## Self-Check: PASSED

- Files: app/package.json, app/package-lock.json, app/app.json, app/src/components/VideoCompare.tsx, 29-07-SUMMARY.md — all FOUND
- Commits: 9a106f7 (Task 1), 92d40aa (Task 2) — all FOUND

---
*Phase: 29-mode3-result-screen-completion*
*Completed: 2026-07-17*
