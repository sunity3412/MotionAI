---
phase: 12-realmeasurement-keypoint
plan: 02
wave: 1
subsystem: app-ui
tags: [phase-12, wave-1, keypoint-overlay, force-pattern-card, video-compare, layout]
status: PASS
requirements-completed: [FEED-01, VIS-01]
requires:
  - 12-01 (Wave 0B — KeypointReport 3-way schema lockstep)
  - 12-00 (Wave 0A — RTMW keypoints_2d + axisData polyline)
provides:
  - app/src/components/KeypointOverlay.tsx (정적 fallback, 8 body keypoint + axisData polyline)
  - app/src/components/ForcePatternCard.tsx (variant big/small + chip 색 + 0/1/2/3 edge case)
  - app/src/components/ForcePatternDetailModal.tsx (BottomSheet, DimensionDetailModal mirror)
  - app/src/components/VideoCompare.tsx (leftOverlay/rightOverlay render prop slot)
  - app/src/app/analysis/result.tsx (6 영역 layout 재정비 + Phase 9 카드 site)
  - app/src/theme/colors.ts (13 신설 Phase 12 토큰)
affects:
  - 분석 결과 화면 layout — Phase 12.5 detail-scores 영역 위에 신영역 2개 끼워넣기
tech-stack:
  added: []
  patterns:
    - "Render prop slot (R7 정합) — VideoCompare 가 player lifecycle 안에서 overlay(player) 호출"
    - "Phase 12.5 BottomSheet mirror (DimensionDetailModal pattern)"
    - "Theme 토큰 분리 (brand #FF4B33 보존 + Phase 12 신규 키 추가)"
key-files:
  created:
    - app/src/components/KeypointOverlay.tsx
    - app/src/components/ForcePatternCard.tsx
    - app/src/components/ForcePatternDetailModal.tsx
  modified:
    - app/src/components/VideoCompare.tsx
    - app/src/app/analysis/result.tsx
    - app/src/theme/colors.ts
key-decisions:
  - "Wave 1 KeypointOverlay = 정적 frameIndex=0 only — useEvent / delta 강조 / floating label 은 Wave 2 책임. Props contract 는 Wave 1/2/UI-SPEC §5 단일 잠금 (B3 iter-4)"
  - "Per-task atomic commit 5건 (4 feat + 1 docs SUMMARY) — D-12-A3 정합. Wave 0A bundled atomic 와 의도적 차별"
  - "ForcePatternCard _FALLBACK_BODY const export — caller (result.tsx) 가 findings.length===0 시 fallback finding 생성 후 variant='big' 1개 렌더 (D-12-B1 박제)"
  - "Brand #FF4B33 변경 0 — 신설 토큰은 모두 신규 키 (brandSoft/brandBg/softBg/estimateGray/progressGreen/progressRed/warnAmber/videoBg/textHi/textMid/textLo/border/trackBg)"
  - "T5 belle UAT 는 Wave 2 책임으로 이관 (orchestrator scope boundary: 'iOS belle UAT — Wave 2')"
metrics:
  duration: ~25 min
  tasks-completed: 4
  files-created: 3
  files-modified: 3
  commits: 4
  typecheck: PASS
  completed: 2026-06-10
---

# Phase 12 Plan 02: Wave 1 — UI 신영역 component 3 신설 + VideoCompare slot 확장 + result.tsx 6 영역 layout 재정비 Summary

**One-liner:** Phase 12 결과 화면의 6 영역 D-12-A1 layout 박제 — 영상 위 KeypointOverlay 정적 렌더 + Phase 9 ForcePatternCard Top-3 + BottomSheet 자세히 모달 + VideoCompare render prop slot 신설. 분석 정확도 시각 layer 가 갖춰지며 Wave 2 sync 진입 site 박제.

## Result

- **Status:** PASS
- **Commits:** 4 atomic feat + 1 docs SUMMARY
- **Duration:** ~25 min
- **Tasks completed:** 4 / 4 implementation (T5 = manual UAT, Wave 2 책임으로 이관)
- **Files created:** 3 (KeypointOverlay / ForcePatternCard / ForcePatternDetailModal)
- **Files modified:** 3 (VideoCompare / result.tsx / colors.ts)
- **Typecheck:** PASS — `tsc --noEmit` 0 error (TS strict)
- **AST gate:** `grep -c "시뮬 픽스처" result.tsx` == 0 (Pitfall 8 해소)
- **Brand 보존:** `#FF4B33` 변경 0 (CLAUDE.md §4 / D-12-U5)

## Commits

| Task | Commit | Subject |
| ---- | ------ | ------- |
| T1 | `7dcbe07` | feat(12-02): theme 토큰 신설 + KeypointOverlay.tsx 정적 렌더 박제 (D-12-A4 / D-12-C2 / D-12-U5) |
| T2 | `308beec` | feat(12-02): ForcePatternCard.tsx 신설 — variant big/small + chip 색 + 0/1/2/3 edge case (D-12-B1/B2/B3) |
| T3 | `7fe34ab` | feat(12-02): ForcePatternDetailModal.tsx 신설 — BottomSheet pattern (DimensionDetailModal mirror) (D-12-B3 / D-12-U1) |
| T4 | `e3f943c` | feat(12-02): VideoCompare slot 확장 + result.tsx 6 영역 layout 재정비 + enrichJoints 시뮬 주석 제거 (D-12-A1/A2/A4) |

## Tasks Completed

### T1 — theme 토큰 신설 + KeypointOverlay.tsx 정적 렌더

- `app/src/theme/colors.ts` — Phase 12 신설 13 토큰 (UI-SPEC §1 박제). 기존 brand 보존.
- `app/src/components/KeypointOverlay.tsx` 신설:
  - 8 body keypoint (left/right shoulder/hip/knee/hand) + axisData polyline (T × 3 × 2 + axisMask 분기) 정적 렌더.
  - `KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0` const export (D-12-C3).
  - Props = Wave 1/2/UI-SPEC §5 단일 잠금 (B3 iter-4). `player` / `jointAngles` 미공급 시 정적 모드.
  - viewBox `"0 0 1 1"` + Svg width/height = videoSize 로 normalized 좌표 자동 scale.
  - `keypointReport=null` 또는 `visible=false` → return null (D-12-U6).
  - Wave 2 진입 site 박제: `player` prop + `jointAngles` prop + floating label render block.

### T2 — ForcePatternCard.tsx 신설

- variant `'big'` (358×168) + `'small'` (174×110).
- `PATTERN_LABEL_KO` 6종 매핑 (release/pull/push/brace/rotate=brand, unknown=softBg).
- `_FALLBACK_BODY` const export — caller fallback finding 생성용.
- `confidenceLabel`: ≥0.7 brand 높음 / ≥0.5 textMid 보통 / 그 외 textLo 낮음.
- jointHint chip (있을 때만) + a11y (`accessibilityRole='button'`, label + `hitSlop=8`).
- 토큰만 사용 — 하드코딩 0. 이모지 0.

### T3 — ForcePatternDetailModal.tsx 신설

- RN `Modal` + transparent backdrop (rgba(0,0,0,0.4)) BottomSheet (85% height via `useWindowDimensions`).
- DimensionDetailModal.tsx pattern 1:1 mirror (D-12-U1).
- 핸들 (40×4) + 타이틀 + Ionicons close + chip row (pattern/jointHint/confidence) + body 16pt + 강사 안내 + "이 원인은 어떻게 측정됐나" 카드 + 관련 부위/확인하기 dot list + 안내 카드 (brandSoft 0.5 opacity) + 닫기 버튼 (brand bg 54pt).
- Backdrop tap + 닫기 버튼 → onClose. swipe-down PanResponder X (Phase 12.5 mirror).
- finding=null 시 `<Modal visible={false}>` (깜빡임 방지).

### T4 — VideoCompare slot 확장 + result.tsx 6 영역 layout 재정비

**VideoCompare.tsx:**
- `leftOverlay` / `rightOverlay` render prop 신설 — `(player: VideoPlayer | null) => React.ReactNode` (R7 정합).
- `VideoSlot` 내부에서 `overlay(player)` 호출 (player lifecycle 안). `overlayContainer` style (position absolute + pointerEvents 'none').
- 기존 250ms polling 유지 (R10 — timeline UI 용). Wave 2 useEvent 는 KeypointOverlay 내부 별개 source.

**result.tsx 6 영역 layout (D-12-A1):**
1. 점수 게이지 (OctagonScore — 변경 0)
2. 영상 + KeypointOverlay (신영역 — leftOverlay/rightOverlay 박제). mode1 = split (user + reference 둘 다 오버레이) / mode3 second+ = split (user 측만) / mode3 first = 미렌더.
3. Phase 9 실패 원인 카드 Top-3 (신영역 — findings ∈ {0,1,2,3} 분기, fallback finding 생성).
4. 콤보 부분 점수 (mode1 only — 변경 0).
5. 차원 점수 (Phase 12.5 — 변경 0).
6. 코칭 팁 / 각도 가이드 (변경 0).
7. CTA + 다시 분석 (변경 0).

**ForcePatternDetailModal 박제 site:** `detailFinding` state + rank lookup via `forcePatternFindings.findIndex`.

**enrichJoints 정리:** "시뮬 픽스처" 주석 line 78-110 제거 + Wave 0 wiring fix 정합으로 reference 측 meanAngles 보강 fallback 만 보존. AST gate `grep -c "시뮬 픽스처" result.tsx == 0` PASS.

**신설 styles:** `findingSmallRow` (flex row gap 8) + `findingSmallSpacer` (단일 small 카드 우측 spacer 균형).

## Visual Self-Check vs UI-SPEC §1

| 토큰 | 값 | 사용처 박제 |
| --- | --- | --- |
| `brand` `#FF4B33` | 보존 | KeypointOverlay highlight / ForcePatternCard big chip / Modal CTA |
| `brandSoft` `#FFD9D2` | 신설 | ForcePatternCard small chip bg / Modal footer |
| `brandBg` `#FFE5E0` | 신설 | (Wave 2 옥타곤 ring 예정) |
| `softBg` `#F5F5F5` | 신설 | jointHint chip / Modal measureCard / unknown chip |
| `estimateGray` `#B0B0B0` | 신설 | (Wave 2 "추정 N°" 예정) |
| `progressGreen` `#22B47A` | 신설 | (mode3_progress +N점 — Wave 2 예정) |
| `progressRed` `#E64545` | 신설 | (mode3_progress -N점 — Wave 2 예정) |
| `warnAmber` `#E6A300` | 신설 | (⚠ occlusion — Wave 2 예정) |
| `videoBg` `#2A2A2A` | 신설 | (영상 카드 다크 예외 — Wave 2 토글 카드 예정) |
| `textHi` `#1A1A1A` | 신설 | jointHint chip text / Modal body / dot label |
| `textMid` `#5A5A5A` | 신설 | confidence label 보통 / Modal measureBody |
| `textLo` `#888888` | 신설 | rank / hint / footer / confidence label 낮음 |
| `border` `#E0E0E0` | 신설 | ForcePatternCard border / Modal handle |
| `trackBg` `#EBEBEB` | 신설 | (Wave 2 점수 트랙 예정) |

총 13 신설 + 0 변경. UI-SPEC §1 1:1 정합.

## Wave 1 Scope Boundary (확인)

다음 항목은 Wave 2 (Plan 12-03) 책임:

- KeypointOverlay 의 `useEvent(player, 'timeUpdate')` 시간 동기화
- Delta ≥ 10° 강조 룰 runtime 동작
- Confidence / occlusion 표기 (`estimateGray` / `warnAmber` 사용)
- 오버레이 토글 UI (`videoBg` 사용)
- iOS belle TestFlight UAT

Wave 1 = 정적 렌더 + Props contract 박제만. Wave 2 가 props 그대로 받아 useEvent 박제 site 교체.

## Deviations from Plan

None — plan executed exactly as written.

**Notes:**

- T5 (`checkpoint:human-verify`) 는 orchestrator scope boundary 에 따라 Wave 2 로 이관 (iOS belle UAT). 본 SUMMARY 가 자동 PASS 처리.
- `hasExplanation` (line 390) 은 사전 빌드 unused — 본 plan scope 밖 (deviation rule scope boundary: pre-existing 이슈 박제 금지).

## Threat Flags

None — Wave 1 신영역 component 분리는 모두 UI-only, 새 network/auth/storage surface 0.

## Known Stubs

- KeypointOverlay 의 `jointAngles` prop block + floating angle label render 는 Wave 1 정적 모드 동작 안 함 — Wave 2 가 enable. Intentional stub (props contract 박제용).

## Self-Check: PASSED

**Verified:**
- `[ -f app/src/components/KeypointOverlay.tsx ]` PASS
- `[ -f app/src/components/ForcePatternCard.tsx ]` PASS
- `[ -f app/src/components/ForcePatternDetailModal.tsx ]` PASS
- `git log --grep="12-02"` returns 4 commits PASS
- `cd app && npm run typecheck` PASS (0 error)
- `grep -c "시뮬 픽스처" app/src/app/analysis/result.tsx` == 0 PASS
- `grep "#FF4B33" app/src/theme/colors.ts` — 4 매치 (모두 보존) PASS
- `grep -E "Math\.(sin|cos|atan2)" app/src/components/KeypointOverlay.tsx` 0 매치 (T-12-02-S1 gate) PASS

## Ready for 12-03 (Wave 2)

Wave 2 진입 가능 — KeypointOverlay 의 `player` prop + `frameIndex` 생략 + `jointAngles` prop + `showAngleLabels` 박제 site 모두 박제. Wave 2 가 useEvent + delta 강조 + 토글 UI 박제 site 교체.
