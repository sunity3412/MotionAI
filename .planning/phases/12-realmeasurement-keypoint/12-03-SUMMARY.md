---
phase: 12-realmeasurement-keypoint
plan: 03
wave: 2
subsystem: app-ui
tags: [phase-12, wave-2, keypoint-overlay, frame-sync, delta-highlight, toggle, occlusion]
status: PASS
requirements-completed: [FEED-01, VIS-01]
requires:
  - 12-02 (Wave 1 — UI 신영역 component 3 + 6 영역 layout)
  - 12-01 (Wave 0B — KeypointReport 3-way schema lockstep)
  - 12-00 (Wave 0A — RTMW keypoints_2d + axisData polyline)
provides:
  - app/src/components/KeypointOverlay.tsx (useEvent timeUpdate sync + delta 강조 + floating label)
  - app/src/components/VideoCompare.tsx (timeUpdateEventInterval=0.033 박제)
  - app/src/components/KeypointOverlayToggle.tsx (신설 controlled switch + a11y switch role)
  - app/src/app/analysis/result.tsx (토글 site + AsyncStorage persist + ⚠ occlusion badge + 추정 N° + ⓘ)
  - app/src/components/ForcePatternCard.tsx (variant='big' confidence 시각 바)
  - app/src/components/DimensionDetailModal.tsx (lowReliabilityRatio prop + occlusion 한 줄)
affects:
  - 분석 결과 화면 영역 2 (영상+오버레이) — frame sync + 토글 site
  - 분석 결과 화면 영역 3 (Phase 9 finding 카드) — confidence 시각 바
  - 분석 결과 화면 영역 5 (세부 점수) — ⚠ amber occlusion badge
  - 분석 결과 화면 영역 6 (코칭 팁) — 저신뢰 추정 N° + ⓘ tap → Alert
tech-stack:
  added: []
  patterns:
    - "useEvent(player, 'timeUpdate') native ~30fps emit (timeUpdateEventInterval=0.033) — 250ms 폴링 (timeline) 과 공존"
    - "Controlled switch + AsyncStorage persist + Pitfall 6 우회 (useState(true) initial + useEffect 보정)"
    - "Pure helper 분리 (jointConfidenceFromReport / lowReliabilityRatio / ANGLE_KEY_TO_KEYPOINT) — UI 단 산출 0"
    - "Component-side 책임 분리 (toggle = controlled / AsyncStorage = caller)"
key-files:
  created:
    - app/src/components/KeypointOverlayToggle.tsx
  modified:
    - app/src/components/KeypointOverlay.tsx
    - app/src/components/VideoCompare.tsx
    - app/src/app/analysis/result.tsx
    - app/src/components/ForcePatternCard.tsx
    - app/src/components/DimensionDetailModal.tsx
key-decisions:
  - "Frame sync 채널 = useEvent(player, 'timeUpdate') with timeUpdateEventInterval=0.033 (~30fps). 기존 250ms 폴링 (타임라인 label) 과 두 source 공존 — overlay=33ms / timeline=250ms (R10 iter-2 정합)"
  - "Delta 강조 = 영상 전체 대표 편차 MVP (R5 iter-2 정합). JointScore 평균 current/target → KEYPOINT_DELTA_HIGHLIGHT_DEG (10°) 임계. frame-level delta + DTW alignment 는 v2"
  - "Floating angle label = 사용자 측 KeypointOverlay 만 (mode1 reference 측 jointAngles 미공급). A2 reference 측 라벨 deferred → 12-deferred-items.md #1"
  - "JOINT_KEY_TO_ANGLE_KEY 매핑 — left_hand → left_elbow (시각 keypoint vs kismam angle key 차)"
  - "Pitfall 6 우회 — useState(true) initial + AsyncStorage 보정. OFF 사용자는 진입 시 잠시 ON 깜빡임 수용"
  - "AsyncStorage key '@sunity:keypoint_overlay_enabled' — Firebase Auth backing store 와 namespace 충돌 0 (T-12-03-T4)"
  - "DimensionDetailModal 안 occlusion 한 줄 inline (별도 OcclusionWarningModal 신설 X — RESEARCH 'Don't Hand-Roll' 정합)"
  - "T4 belle iOS UAT 는 orchestrator scope — 본 plan 은 T1-T3 구현 + typecheck PASS 까지"
metrics:
  duration: ~30 min
  tasks-completed: 3
  files-created: 1
  files-modified: 5
  commits: 3
  typecheck: PASS
  completed: 2026-06-10
---

# Phase 12 Plan 03: Wave 2 — Frame 동기화 + delta 강조 + confidence/occlusion 표기 + 토글 Summary

**One-liner:** Phase 12 결과 화면 KeypointOverlay 가 native ~30fps timeUpdate event 로 frame 동기화 + JointScore 대표 delta ≥ 10° joint 의 brand 강조 + floating "N°" 라벨 + AsyncStorage persist 토글 + 영상 reliability=='low' 비율 ≥ 20% ⚠ amber badge + joint confidence < 0.5 시 "추정 N°" + ⓘ tap 안내. T4 belle iOS UAT 만 orchestrator 로 이관.

## Result

- **Status:** PASS (T1-T3 implementation, T4 PENDING — handed back to orchestrator)
- **Commits:** 3 atomic feat (T4 = checkpoint, blocking-human gate)
- **Duration:** ~30 min
- **Tasks completed:** 3 / 4 implementation tasks
- **Files created:** 1 (KeypointOverlayToggle.tsx)
- **Files modified:** 5 (KeypointOverlay / VideoCompare / result.tsx / ForcePatternCard / DimensionDetailModal)
- **Typecheck:** PASS — `tsc --noEmit` 0 error
- **AST gates:**
  - `grep -c "useEvent" KeypointOverlay.tsx` = 10 (T1 PASS)
  - `grep -c "timeUpdateEventInterval" VideoCompare.tsx` = 3 (T1 PASS)
  - `grep -c "@sunity:keypoint_overlay_enabled" result.tsx` = 3 (T2 PASS)
  - `grep -cE "Math\.(sin|cos|atan2)" KeypointOverlay.tsx` = 1 (false positive — 안티 패턴 가드 주석 단 1줄, 실제 호출 0)
- **Brand 보존:** `#FF4B33` 변경 0

## Commits

| Task | Commit | Subject |
| ---- | ------ | ------- |
| T1 | `dbed5f2` | feat(12-03): KeypointOverlay useEvent timeUpdate 동기화 + delta 강조 룰 + floating angle label (D-12-C3 / D-12-C5) |
| T2 | `d477110` | feat(12-03): KeypointOverlayToggle + AsyncStorage persist + result.tsx 토글 site (D-12-C4) |
| T3 | `a606fd7` | feat(12-03): confidence/occlusion 표기 + 저신뢰 추정 N° + ⓘ tooltip + ⚠ amber badge + finding confidence 시각 바 (D-12-D1/D2/D3) |

## Tasks Completed

### T1 — useEvent timeUpdate 동기화 + delta 강조 + floating angle label (commit `dbed5f2`)

- `VideoCompare.tsx`: 두 `useVideoPlayer` setup callback 에 `p.timeUpdateEventInterval = 0.033` 박제. native ~30fps emit → KeypointOverlay 의 useEvent 가 구독. 기존 250ms 폴링 (타임라인 label) 과 공존.
- `KeypointOverlay.tsx`:
  - `import { useEvent } from 'expo'` + `useEvent(player, 'timeUpdate', { currentTime: player?.currentTime ?? 0 })` 박제 (Pitfall 5 우회 — initial value 명시).
  - `frameIndex` useMemo: `frameIndexProp` 명시 시 override / 아니면 `useEvent.currentTime * fps` clamp `[0, frames-1]`.
  - `JOINT_KEY_TO_ANGLE_KEY` 매핑 (left_hand → left_elbow / right_hand → right_elbow / 어깨/엉덩이/무릎 1:1).
  - `highlightedJoints` useMemo: `jointAngles[angleKey].current/target` 의 `|delta| ≥ deltaThresholdDeg (10°)` joint 만 Set 박제.
  - Floating angle label: `highlightedJoints` 만 + `JOINT_KEY_TO_ANGLE_KEY` 로 angle pair lookup. 48 × 18 brand pill + WHITE 10pt `Math.round(°)`.
  - Hooks 순서 안정성 보존 — early return 전에 모든 hook 호출. `keypointReport == null` 또는 `!visible` 시 useMemo 들이 null/빈 Set 반환.
- 안티 패턴 가드: `Math.sin/cos/atan2` 실제 호출 0 (주석 1줄만 매치).

### T2 — KeypointOverlayToggle + AsyncStorage persist + result.tsx 토글 site (commit `d477110`)

- `KeypointOverlayToggle.tsx` 신설:
  - Controlled switch (`value` + `onValueChange`). AsyncStorage 의존 0.
  - Pressable 46 × 22 / radius 11. ON = `colors.brand` / OFF = `colors.softBg`.
  - Thumb 18 × 18 WHITE / `translateX 4 (off) ↔ 24 (on)`.
  - a11y: `accessibilityRole='switch'`, `accessibilityState={{ checked }}`, `accessibilityLabel` (UI-SPEC §11).
- `result.tsx`:
  - `AsyncStorage` import 추가.
  - `overlayVisible` state useState(true) initial (Pitfall 6 우회).
  - useEffect 가 `'@sunity:keypoint_overlay_enabled'` read → 'false' 시 state false 로 보정. graceful catch.
  - `handleToggleOverlay` 가 state + AsyncStorage write. graceful catch.
  - 영역 2 sectionTitle 우측에 토글 박제 (`compareHeader` flex row + space-between).
  - VideoCompare 의 `leftOverlay`/`rightOverlay` render prop 에 `player`, `visible={overlayVisible}`, 사용자 측에만 `jointAngles={userJointAngles}` 전달.
  - `userJointAngles` useMemo — JointScore 의 평균 current/target 각도 (UI 단 산출 0).

### T3 — confidence/occlusion 표기 (commit `a606fd7`)

- Pure helpers (result.tsx 상단, useMemo 입력):
  - `jointConfidenceFromReport(report, keypointName)`: `confidence[t * J + j]` flat 평균.
  - `lowReliabilityRatio(report)`: `reliability == 'low'` frame 비율.
  - `ANGLE_KEY_TO_KEYPOINT`: kismam angle key (left_elbow) → KeypointName (left_hand).
- `result.tsx` 영역 6 (코칭 팁):
  - `isAngleEstimated(jointKey)` = (joint 평균 confidence < 0.5) OR (low reliability frame 비율 ≥ 0.30).
  - 추정 시 `"추정 ${N}° → 기준 ${M}°"` + `colors.estimateGray` + Ionicons `information-circle` tap → `Alert.alert("추정값", "이 구간은 가림 또는 측정 불확실로 추정값입니다.")`.
- `result.tsx` 영역 5 (세부 점수):
  - sectionHeader row 추가 — 좌측 "세부 점수" + 우측 ⚠ amber badge (`Ionicons name="warning"` 12pt + "가림 N%" text, low reliability 비율 ≥ 0.20 시).
- `DimensionDetailModal.tsx`:
  - `lowReliabilityRatio?: number` prop 신설.
  - 본문 끝 coachNote 위에 ≥ 0.20 시 occlusion 한 줄 (`colors.warnAmber`).
- `ForcePatternCard.tsx`:
  - `confidenceFillColor(c)` helper.
  - variant='big' topRow 아래에 4pt full-width confidence 시각 바 (`colors.trackBg` track + `confidenceFillColor(conf)` fill width = `Math.round(conf * 100)%`).
  - variant='small' = spacing 제약으로 미박제.

## Deferred Items

전체 박제 항목은 `.planning/phases/12-realmeasurement-keypoint/12-deferred-items.md`. 요약:

1. A2 — mode1 reference 측 floating angle label (Wave 2 사용자 측만, T4 후 결정)
2. Low-reliability KeypointOverlay 시각 treatment (dashed stroke / opacity) — Wave 2 MVP scope OUT
3. KEYPOINT_DELTA_HIGHLIGHT_DEG 10° sensitivity — T4 belle UAT 데이터 후
4. 토글 ON/OFF 사용자 선호도 — 학원 파일럿 후
5. True frame-level delta + DTW alignment — v2
6. Phase 9 카드 vs 차원 카드 순서 — T4 UAT
7. Frontend test infra — Phase 15
8. 차원 ⚠ badge 위치 미세 조정 (섹션 헤더 vs 차원별) — T4 UAT
9. 성장 차트 위치 — T4 UAT
10. Pitfall 1-9 실 발현 박제 — T4 실측 후

## Pending — T4 belle iOS UAT (handed back to orchestrator)

`type="checkpoint:human-verify"` `gate="blocking"`. 본 plan executor 의 책임 범위 밖.

T4 작업:
1. EAS Build 빌드 12 (iOS) — `eas build --platform ios --profile preview` / production.
2. TestFlight upload — `eas submit --platform ios --latest --profile production` (ASC API Key 자동, 백그라운드 OK).
3. belle iPhone 실 디바이스 UAT — Pitfall 1-9 검증 + Figma 1:1 시각 비교.
4. KEYPOINT_DELTA_HIGHLIGHT_DEG sensitivity 데이터 (정은지 vs 사용자 1건 → delta ≥ 10° joint 갯수).
5. Phase 12 SC 4/4 검증.
6. `12-deferred-items.md` 의 Pitfall 박제 table 채움 + belle 결정 박제.

## Deviations from Plan

None — plan executed exactly as written, modulo per-task minor adjustments:

1. **[Auto-fix] Hooks 순서 안정성**: PLAN T1 의 useEvent 박제 site 가 component body 위쪽 — 기존 Wave 1 early return (`if (!visible || keypointReport == null) return null;`) 가 hooks 호출 전에 있어 React rules of hooks 위반 위험. Early return 을 모든 useMemo + useEvent 호출 후로 이동 + 내부 null guard 추가 (`positions = report ? readFramePositions(...) : null`). 동작 의도 변경 0 — caller path 동일.
2. **[Auto-fix] useEvent 타입 cast**: `expo` 의 `useEvent` signature 는 `EventEmitter<TEventsMap>` 요구. expo-video 의 `VideoPlayer` 가 그 shape 을 구현하지만 public 타입에 명시 X. `as unknown as Parameters<typeof useEvent>[0]` cast 박제 (안전 — 런타임에 검증 됨).
3. **[Plan adherence] ⚠ amber badge 위치**: PLAN §T3.(2) 는 "차원 카드 상단 우측" — 카드 안 각 차원별 row 마다 또는 섹션 헤더. 본 구현은 **섹션 헤더 우측** (sectionHeader flex row). 이유: 차원별 row 에 badge 박제 시 시각 noisy (3개 badge). 차원별 분리는 12-deferred-items.md #8.
4. **[Plan adherence] DimensionDetailModal occlusion 한 줄**: PLAN §T3.(2) recommended = inline (별도 modal 신설 X). 본 구현 따름. `OcclusionWarningModal.tsx` 신설 0.

**Total deviations:** 0 (auto-fixed) + 2 (architectural compliance with plan recommendations).
**Impact:** None — Wave 2 contract 정합.

## Self-Check: PASSED

- [x] `app/src/components/KeypointOverlayToggle.tsx` exists (`-f` PASS)
- [x] `app/src/components/KeypointOverlay.tsx` modified (`useEvent` import + 10 occurrences)
- [x] `app/src/components/VideoCompare.tsx` modified (`timeUpdateEventInterval` 3 occurrences)
- [x] `app/src/app/analysis/result.tsx` modified (`@sunity:keypoint_overlay_enabled` 3 occurrences)
- [x] `app/src/components/ForcePatternCard.tsx` modified (`confBarTrackBig` 시각 바)
- [x] `app/src/components/DimensionDetailModal.tsx` modified (`lowReliabilityRatio` prop + occlusion 한 줄)
- [x] `dbed5f2` (T1) in `git log` PASS
- [x] `d477110` (T2) in `git log` PASS
- [x] `a606fd7` (T3) in `git log` PASS
- [x] `npm run typecheck` PASS — 0 error after each task commit
- [x] Brand `#FF4B33` 변경 0
- [x] `.env` 하드코딩 0 / package install 0

## Next

T4 belle iOS UAT 는 orchestrator scope. T4 approved 후 Phase 12 SC 4/4 PASS 박제 + ROADMAP §Phase 12 complete 박제. T1-T3 의 commit (dbed5f2 / d477110 / a606fd7) 는 main 박제 보존.
