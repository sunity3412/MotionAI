---
phase: quick-260705-fx4-landscape-viewer-fix
plan: 01
subsystem: app-ui
tags: [video-compare, fullscreen-viewer, landscape, keypoint-overlay, ota]
requires: [quick-260702-t0v (가로 전체화면 뷰어 신설)]
provides:
  - 가로 전체화면 뷰어 명시 숫자 치수 레이아웃 (fsBoxW/fsBoxH = window 파생)
affects: []
tech-stack:
  added: []
  patterns:
    - "회전(transform) absolute 컨테이너 안 박스 치수는 퍼센트+aspectRatio 대신 JS 숫자 주입"
key-files:
  created: []
  modified:
    - app/src/components/VideoCompare.tsx
key-decisions:
  - "퍼센트/aspectRatio 기반 fsVideoBox 폐기 → fsBoxH=fsShort, fsBoxW=round(fsShort*9/16) 숫자 주입 (실기기 ~68% 축소 렌더 근본 fix)"
  - "fsSlot flex 반쪽 래퍼 삭제 → fsVideoRow justifyContent center + gap 8 중앙 인접 배치"
  - "url 있는 슬롯만 조건부 렌더 — 단일 영상 시 1박스 자동 중앙"
metrics:
  duration: ~4min
  completed: 2026-07-05
  tasks: 1/1
  commits: 1
---

# Quick 260705-fx4: 가로 전체화면 뷰어 명시 치수 fix Summary

가로 전체화면 뷰어의 실기기 레이아웃 붕괴 3종(68% 축소 렌더 / 박스 사이 ~200pt 간격 / 오버레이 유령 마커)을 퍼센트+aspectRatio → window 파생 JS 숫자 치수 전환으로 수정.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | 가로 전체화면 뷰어를 명시 숫자 치수 레이아웃으로 전환 | f532245 | app/src/components/VideoCompare.tsx |

## What Changed

1. **명시 치수 계산**: `fsBoxH = fsShort`, `fsBoxW = Math.round(fsShort * VIDEO_ASPECT)` — fsShort/fsLong 파생 직후 추가. 한국어 why 주석 + "belle 실기기 2차 2026-07-05" 근거 인용.
2. **renderFullscreenSlot 재구성**: fsSlot flex 래퍼 폐기, 슬롯 = 박스 자체. `style={[styles.fsVideoBox, { width: fsBoxW, height: fsBoxH }]}` 인라인 주입. VideoView(contentFit contain)/overlayContainer(sizeScale=FULLSCREEN_OVERLAY_SCALE)/slotEmpty 무변경. fsSlotLabel 을 박스 내부 마지막 child 로 이동.
3. **인접 배치**: fsVideoRow 에 justifyContent center + alignItems center + gap 8. Modal 안 슬롯 호출을 `{hasLeft && ...}` / `{hasRight && ...}` 조건부로 전환 — 단일 영상 시 1박스 중앙.
4. **styles 정리**: fsVideoBox 에서 height '100%'/maxWidth '100%'/aspectRatio 전부 제거 (배경 videoFullscreenBg 만 유지). fsSlot 삭제. fsSlotLabel 은 left 0/right 0/top 12 + textAlign center 로 박스 기준 absolute. fsTopBar 주석을 새 레이아웃(중앙 인접 배치, 393 기기 박스 우측 끝 x≈639) 기준으로 갱신.

## Verification

- `npm run typecheck` GREEN (tsc --noEmit, 에러 0)
- grep 게이트 PASS: `fsShort * VIDEO_ASPECT` 존재 + `maxWidth: '100%'` 부재 + fsVideoBox aspectRatio 부재 + fsSlot 스타일 소멸
- 기하 검증 (iPhone 393×852): 박스 221×393 두 개 + gap 8 = 450pt ≤ fsLong 852 — 중앙 인접 배치, 세로 꽉 참
- 세로 카드 경로(VideoSlot/slotFrame/row) diff 0 — 무회귀 (diff 는 전체화면 경로 + 들여쓰기만)
- KeypointOverlay.tsx 무접촉, app.json/package.json 무변경 (JS-only, OTA 가능)

## 실기기 검증 체크리스트 (belle — OTA 배포 후)

1. [ ] 영상이 세로(짧은 변)를 꽉 채움 — 68% 축소 렌더 소멸
2. [ ] 두 영상 인접 배치 — 박스 사이 큰 검은 간격 없음
3. [ ] 오버레이 마커가 영상 속 몸 위에 정확히 겹침 — 박스 밖 유령 마커 소멸
4. [ ] 슬롯 라벨이 각 영상 박스 내부 상단 중앙에 표시
5. [ ] 재생/일시정지/스텝/스크럽/타임라인 동작 정상
6. [ ] 닫기 후 세로 카드 정상 복귀

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] worktree 에 node_modules 부재로 typecheck 불가**
- **Found during:** Task 1 검증 단계
- **Issue:** worktree 는 gitignored node_modules 를 포함하지 않아 `tsc: command not found`
- **Fix:** 메인 repo `app/node_modules` 를 임시 symlink 후 typecheck 실행, 검증 완료 후 symlink 제거 (커밋 무포함)
- **Files modified:** 없음 (repo 파일 무변경)
- **Commit:** 해당 없음

## Known Stubs

없음 — 스텁/placeholder 미도입.

## Self-Check: PASSED

- FOUND: app/src/components/VideoCompare.tsx
- FOUND: commit f532245
