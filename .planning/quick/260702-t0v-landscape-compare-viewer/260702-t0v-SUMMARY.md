---
phase: quick-260702-t0v-landscape-compare-viewer
plan: 01
subsystem: app-result-screen
tags: [video-compare, keypoint-overlay, fullscreen, ota-safe]
requires: []
provides:
  - "VideoCompare 가로 전체화면 뷰어 (Modal + 90도 회전, player 인스턴스 재사용)"
  - "KeypointOverlay sizeScale prop (default 1, 전체화면 2.0)"
  - "colors.videoFullscreenBg 토큰 (몰입형 영상 전체화면 다크 예외)"
affects: [app/src/components/VideoCompare.tsx, app/src/components/KeypointOverlay.tsx, app/src/app/analysis/result.tsx, app/src/theme/colors.ts]
tech-stack:
  added: []
  patterns:
    - "portrait 고정 + Modal 내 뷰 90도 회전으로 가로 시뮬레이트 (native 모듈 0, OTA 안전)"
    - "expo-video 다중 VideoView attach — 같은 player 로 두 레이아웃 동기 제어"
key-files:
  created: []
  modified:
    - app/src/components/KeypointOverlay.tsx
    - app/src/components/VideoCompare.tsx
    - app/src/app/analysis/result.tsx
    - app/src/theme/colors.ts
decisions:
  - "회전 방식 = RN Modal + transform rotate 90deg (expo-screen-orientation 설치 금지 — native rebuild 유발)"
  - "전체화면 오버레이 배율 = FULLSCREEN_OVERLAY_SCALE 상수 2.0 (belle 실기기 확인 후 미세조정 가능하도록 상수화)"
  - "타임라인 track 폭 ref 분리 (trackWidthRef / fsTrackWidthRef) — 세로 카드가 Modal 뒤에 mount 유지라 onLayout 재발화 없음, scrubAtX 가 활성 레이아웃 폭을 읽음"
  - "dark 컨트롤 색 분기 = 기존 토큰만 (textWhite / videoBg) — 신규 반투명 토큰 미신설"
metrics:
  duration: "~12분"
  completed: "2026-07-04"
  tasks: 2
  files: 4
---

# Quick 260702-t0v: 가로 전체화면 동작 비교 뷰어 Summary

전체화면 Modal + 90도 회전으로 두 영상을 좌우 크게 나란히 보여주고, KeypointOverlay sizeScale 2.0 으로 각도 라벨(빨간 말풍선) 판독을 확보 — 기존 leftPlayer/rightPlayer 인스턴스 재사용이라 재생 위치/동기 로직 그대로, JS-only 로 OTA 배포 가능.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | KeypointOverlay sizeScale prop + render prop 시그니처 확장 + result.tsx 배선 | a0f0bb7 | KeypointOverlay.tsx, VideoCompare.tsx, result.tsx |
| 2 | VideoCompare 가로 전체화면 뷰어 (Modal + 90도 rotate) + 진입 버튼 + 토글 유지 | 6d16f97 | VideoCompare.tsx, colors.ts, result.tsx |

## What Was Built

- **KeypointOverlay `sizeScale` prop (default 1):** 화면상 크기를 갖는 모든 정규화 상수에만 곱함 — RADIUS/RADIUS_HI, STROKE 4종, 라벨 64x26/rx·ry 13/offset 14/fontSize 14/텍스트 stroke 0.6/Rect 테두리 1.4, 저신뢰 dashArray 4. 좌표(positions/axis)는 무변경. default 1 이면 기존 렌더와 수치 동일(세로 카드 무회귀). 임계값/강조 로직(KEYPOINT_DELTA_HIGHLIGHT_DEG 등) 무변경.
- **overlay render prop 확장:** `(player, opts?: { sizeScale?: number })` — `OverlayRenderProp` 단일 타입으로 VideoCompareProps.leftOverlay/rightOverlay + SlotProps.overlay 통일. 세로 VideoSlot 은 opts 생략 호출(하위호환).
- **가로 전체화면 뷰어:** `{fullscreen && <Modal>}` 조건부 렌더(닫힌 동안 native 리소스 0, T-t0v-01). 회전 컨테이너 `width:winH / height:winW / left:(winW-winH)/2 / top:(winH-winW)/2 + rotate 90deg`. 상단 bar(오버레이 토글 + 닫기), 중앙 두 영상 슬롯(flex 1 row), 하단 공유 컨트롤(dark).
- **player 재사용:** 전체화면 VideoView 가 기존 leftPlayer/rightPlayer 에 두 번째 attach — `useVideoPlayer(` 호출 수 2 유지(신규 생성 0). drift 보정 tick/togglePlay/seekBoth/restart 가 양 레이아웃을 그대로 제어. 열고 닫을 때 pause/seek 조작 0 → 위치·상태 자동 연속.
- **컨트롤 공유(로직 중복 0):** 기존 controls JSX 를 `renderControls(dark)` 로 추출. dark=false 경로는 기존과 동일 JSX(스타일 분기 미발동) — 세로 카드 무회귀. dark=true 는 시간 라벨 textWhite / step 버튼 videoBg / restart·step 아이콘 textWhite 만 토큰 분기.
- **scrub 폭 분리:** fsTrackWidthRef + fullscreenRef 로 scrubAtX 가 활성 레이아웃의 track 폭 사용 (전체화면 닫은 뒤 세로 scrub 비율 오염 방지).
- **진입 버튼:** "가로로 크게 보기" 전체 너비 pill (Ionicons expand + brandTint 배경 + brand 텍스트, accessibilityRole/Label + hitSlop). hasAny 일 때만.
- **토큰:** `videoFullscreenBg: '#000000'` 신설 — 다크 배경 금지 원칙의 의도적 예외(loading.tsx navy / videoBg 선례 정합) 주석 포함. 하드코딩 색 신규 0.
- **result.tsx:** left/right 오버레이 콜백 `(player, opts)` + `sizeScale={opts?.sizeScale ?? 1}` (사용자 측 + mode1 정은지 측), `fullscreenHeaderExtra`=KeypointOverlayToggle (state 단일 출처 = result.tsx, 토글 시 render prop 재실행으로 전체화면 즉시 반영). mode3 second+(left 오버레이만) 동일 경로.

## Verification

- `cd app && npm run typecheck` GREEN (유일한 정적 게이트).
- `grep -c "useVideoPlayer(" src/components/VideoCompare.tsx` == 2 (player 신규 생성 0). 참고: 플랜의 `grep -c "useVideoPlayer"` 리터럴은 import 문 + 주석까지 세어 4 — 호출 수 기준으로 검증 (원본 파일도 리터럴 카운트는 3 이었음).
- FULLSCREEN_OVERLAY_SCALE / videoFullscreenBg / rotate / sizeScale grep 전부 존재.
- app.json / package.json diff 0 — native rebuild 유발 변경 0, OTA 배포 가능.
- 세로 카드 무회귀: sizeScale 미전달 → S=1 → `(10*1)/H === 10/H` 수치 동일. renderControls(false) 는 기존 JSX 와 동일(다크 분기 미발동).

## Deviations from Plan

None — plan executed as written. (검증 grep 리터럴 카운트 불일치는 위 Verification 에 기록 — 플랜 의도(호출 수 2)는 충족.)

## belle 실기기 확인 체크리스트 (TestFlight)

1. mode1 결과 → "가로로 크게 보기" → 각도 라벨(빨간 말풍선) 판독 가능한가 (부족하면 `VideoCompare.tsx` 의 `FULLSCREEN_OVERLAY_SCALE` 상향)
2. 전체화면 재생/일시정지/0.1초 step/타임라인 드래그 동작 (드래그 방향이 회전 뷰에서 자연스러운가)
3. 오버레이 토글 ON/OFF 즉시 반영
4. 닫기 후 세로 복귀 + 재생 위치 유지
5. mode3(두 번째+ 분석) 동일 확인
6. Android 실기기: back 버튼 닫힘 + 레이아웃 정상 (edgeToEdge 환경)

## Known Stubs

None — 전체화면 뷰어는 기존 데이터 경로(player/overlay render prop)만 소비, 신규 데이터 소스 없음.

## Threat Flags

None — 신규 네트워크 경로/입력 파싱/패키지 설치 0. T-t0v-01(다중 VideoView 자원) mitigate 반영: 조건부 렌더 + 신규 player 0.

## Self-Check: PASSED

- app/src/components/KeypointOverlay.tsx: FOUND (sizeScale prop)
- app/src/components/VideoCompare.tsx: FOUND (rotate + FULLSCREEN_OVERLAY_SCALE)
- app/src/theme/colors.ts: FOUND (videoFullscreenBg)
- app/src/app/analysis/result.tsx: FOUND (opts.sizeScale + fullscreenHeaderExtra)
- Commit a0f0bb7: FOUND
- Commit 6d16f97: FOUND
