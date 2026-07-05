---
phase: quick-260705-k8y
plan: 01
subsystem: app-analysis-result
tags: [overlay, fullscreen, action-labels, keypoint, video-compare]
requires: [quick-260704-fz4, quick-260702-t0v, quick-260704-fwb]
provides:
  - "전체화면 뷰어 고정 1.35배 줌 (FULLSCREEN_ZOOM 클리핑 래퍼)"
  - "composeActionLabelKo/composeDeviationOnlyLabelKo 순수 매핑 (deductionLabels)"
  - "KeypointOverlay actionLabels prop — 문제 관절 한정 행동 지시 라벨 (절대각 제거)"
  - "result.tsx actionLabels 3-소스 우선순위 memo + 좌측 오버레이 배선"
affects: [app/src/components/VideoCompare.tsx, app/src/components/KeypointOverlay.tsx, app/src/lib/deductionLabels.ts, app/src/app/analysis/result.tsx]
tech-stack:
  added: []
  patterns:
    - "클리핑 래퍼(overflow hidden) + 내부 확대 박스 — 오버레이 absoluteFill 정합 자동 유지"
    - "라벨 문구 사전/조립 순수 함수 격리 (후속 리서치로 문구만 교체 가능)"
key-files:
  created: []
  modified:
    - app/src/components/VideoCompare.tsx
    - app/src/lib/deductionLabels.ts
    - app/src/components/KeypointOverlay.tsx
    - app/src/app/analysis/result.tsx
decisions:
  - "FULLSCREEN_ZOOM=1.35 모듈 상수 — 크롭 정도 조정은 상수 1개만 상향/하향"
  - "hip 라벨 부위어 = '다리' (좌우 구분은 마커 위치가 전달, ANGLE_MEANING_KO '벌림' 정합)"
  - "faultJointDeficits(부호 없음)는 방향 생략 폴백 '기준과 N° 차이' — 방향 fabricate 금지"
  - "coordinator 중계 문구 교체 요청(강사 큐잉 리서치)은 미적용 — plan must_haves 형태 위반 + hip 매핑 비결정적 (아래 Deferred 참조)"
metrics:
  duration: "~10m"
  completed: "2026-07-05T05:52:00Z"
  tasks: 3
  commits: [c34328f, d5deec9, 7d313ff]
---

# Quick 260705-k8y: 오버레이 행동 지시 라벨 + 전체화면 1.35배 줌 Summary

가로 전체화면 두 영상을 1.35배 확대·클리핑해 인물을 키우고, 절대각 숫자 라벨(158°)을 문제 관절 한정 행동 지시 라벨("왼쪽 무릎 23° 더 펴야")로 전면 교체 — 실측 signed delta 로만 조립, 방향 데이터 없으면 방향 생략 폴백.

## What Was Done

### Task 1 — VideoCompare 전체화면 고정 1.35배 줌 (c34328f)
- `FULLSCREEN_ZOOM = 1.35` 모듈 상수 (why 주석: belle 실기기 3차 2026-07-05 승인).
- `renderFullscreenSlot` 2겹 구조: 클리핑 래퍼(fsBoxW×fsBoxH, `overflow: 'hidden'`) + 내부 확대 박스(`fsZoomBox`, absolute, `Math.round(fsBox* × 1.35)` 치수 + 음수 left/top 중앙 정렬).
- VideoView + overlayContainer 를 내부 확대 박스로 이동 → 오버레이(absoluteFill)가 영상과 함께 확대·클리핑돼 마커 정합 자동 유지.
- slotEmpty/fsSlotLabel 은 래퍼 직속(잘리지 않음). 세로 카드 경로(slotFrame/VideoSlot) diff 0. 수치 전부 fsBox 파생 — 하드코딩 픽셀 0.

### Task 2 — 행동 지시 라벨 순수 매핑 + 오버레이 전환 (d5deec9)
- `composeActionLabelKo(angleKey, signedDeltaDeg)`: elbow/knee → "{부위} {N}° 더 펴야/굽혀야", hip → "다리 {N}° 더 벌려야/모아야", shoulder → "팔 {N}° 더 벌려야/모아야". delta<0=더 굽음 근거(features.py/kismam JOINT_DIRECTION_PAIRS)를 주석에 박제. n<1 또는 미등록 key 는 null(마커만).
- `composeDeviationOnlyLabelKo`: "{부위} 기준과 {N}° 차이" — 부호 없는 소스용, 방향 fabricate 금지.
- KeypointOverlay `actionLabels` prop 신설: highlighted∪attention 중 항목 있는 관절만 라벨 렌더. 절대각 `${Math.round(pair.current)}°` 코드 제거. `labelTextWidth`(한글 14/그 외 8 + 패딩 16) 동적 pill 폭 + 우측 overflow 시 keypoint 좌측 배치. 저신뢰(conf<0.5) 숨김 가드·S 배율·토큰 유지. `showAngleLabels` 이름 유지(의미 갱신 주석만).

### Task 3 — result.tsx actionLabels 조립·배선 (7d313ff)
- `actionLabels` memo 3-소스 우선순위: (1) windowMedianAngleDeltas signed delta (applied 시, direction 문자열 재파싱 금지) → (2) faultJointDeficits 방향 생략 폴백 (KEYPOINT_FROM_ANGLE_KEY entries 역탐색) → (3) JointScore.deltaDeg (Mode3 커버). deltaDeg 부재 시 current/target 재계산 금지 — 라벨 없음 = 마커만.
- leftOverlay 에 `actionLabels={actionLabels}` 배선 (세로 카드·전체화면 공용 render prop — 라벨 규칙 동시 전환). rightOverlay 무접촉.

## Verification

- `npm run typecheck` GREEN (3회 — 태스크별).
- grep 게이트 전부 통과: VideoCompare `FULLSCREEN_ZOOM` 5회, deductionLabels `composeActionLabelKo` 존재, KeypointOverlay `actionLabels` 5회 + 절대각 라벨 코드 부재, result.tsx `actionLabels` 3회.
- JS-only (native 모듈/의존성 추가 0) — OTA 가능 유지. 이모지 0, 테마 토큰만.

## 실기기 체크리스트 (belle 확인용)

- [ ] 가로 뷰어: 인물이 이전보다 크게(1.35배), 천장/바닥 잘림, 마커 정합 유지
- [ ] 줌 크롭 정도 적절 (부족하면 FULLSCREEN_ZOOM 상수만 상향)
- [ ] 문제 관절 라벨 문구 예시 확인 (예: "왼쪽 무릎 23° 더 펴야" / "다리 30° 더 벌려야" / 방향 없으면 "기준과 N° 차이")
- [ ] 정상 관절 = 마커만 (라벨 없음), 절대각 숫자(158° 등) 미노출
- [ ] Mode3 결과 화면에서 크래시/거짓 라벨 없음 (데이터 없으면 마커만)
- [ ] 세로 카드도 같은 라벨 규칙 (문제 관절만)

## Deviations from Plan

None — plan executed exactly as written.

## Deferred Items

**강사 큐잉 언어 기반 라벨 문구 교체 (coordinator 중계, 미적용):** 실행 중 coordinator 가 "리서치 완료" 매핑("무릎 {N}° 더 접기", "어깨 귀에서 멀리", "골반 {N}° 접기/열기" 등)으로 문구 교체를 요청했으나 미적용. 사유: (1) plan must_haves 가 라벨 형태를 '부위+편차 N°+방향' 으로 잠갔는데 요청 매핑 일부가 편차 수치를 생략("어깨 귀에서 멀리", "팔꿈치 살짝 굽히기"), (2) hip 매핑이 (angleKey, signedDelta) 순수 함수 서명으로 결정 불가(부족 → "다리 더 들기" vs "골반 열기" 가 컨텍스트 의존, split 그룹 정보 미주입) — 구현 시 컨텍스트 fabricate 필요(거짓 구체성 금지 위반), (3) coordinator 중계는 사용자 승인 권한 없음(plan 은 belle 승인분). 문구는 composeActionLabelKo 한 함수에 격리돼 있어, 매핑이 결정적·완전(관절별 2분기 + 수치/좌우 정책)으로 확정되면 1-커밋 교체 가능.

## Known Stubs

None — 모든 라벨은 실측 주입 데이터로만 조립되며, 데이터 부재 시 라벨 생략(마커만)이 의도된 동작.

## Threat Flags

None — 네트워크/인증/스키마 변경 없음 (UI 렌더 전용).

## Self-Check: PASSED

- FOUND: app/src/components/VideoCompare.tsx (FULLSCREEN_ZOOM)
- FOUND: app/src/lib/deductionLabels.ts (composeActionLabelKo)
- FOUND: app/src/components/KeypointOverlay.tsx (actionLabels)
- FOUND: app/src/app/analysis/result.tsx (actionLabels 배선)
- FOUND commits: c34328f, d5deec9, 7d313ff
