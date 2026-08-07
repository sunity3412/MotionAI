---
phase: quick-260807-iwp
plan: 01
subsystem: ui
tags: [react-native, expo-video, video-sync, voice-cue, keypoint-overlay, node-test]

# Dependency graph
requires:
  - phase: quick-260807-fpw
    provides: 재개 백오프 관찰창(resumeWatchTicksRef + RESUME_RETRY_AT_TICKS + 제자리 nudge), 큐 체이닝(nextChainedCue), 재생 중 색 반전(playingInversion)
  - phase: quick-260730-l7t (33-G §C-1)
    provides: FaultZoomComparison.refVideoSec — 백엔드 F-3 방출 기준 도메인 초 (스냅 시각의 유일한 정당 소스)
provides:
  - 음성 큐 발화 멈춤 동안 기준(우) 패널이 record 짝 시각(refVideoSec)으로 스냅, 재개 직전 원위치 복원 (BELLE-0807-5)
  - 드리프트 보정 히스테리시스 — 임계 0.3s + 보정 seek 최소 간격 0.8s (BELLE-0807-6)
  - 재생 중 학생 오버레이 관절 점 1.3배 + 외곽선 강화 opt-in (BELLE-0807-7)
affects: [VideoCompare 재생 제어 후속, 음성 큐 UX, KeypointOverlay 시인성 조정]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "voiceSnap.buildRefSnapSecs — recordId→refVideoSec 순수 빌더 (F-3 방출값만, 재계산 금지, fabricate 0)"
    - "driftHysteresis.shouldCorrectDrift — 보정 seek 발사 판정 순수 모듈 (상수 단일 출처, playbackInvariant 관례)"
    - "KeypointOverlay playbackEmphasis — opt-in 배율 prop (기본 false = 기존 렌더 byte 보존, FULLSCREEN_OVERLAY_SCALE 관례)"

key-files:
  created:
    - app/src/lib/voiceSnap.ts
    - app/src/lib/__tests__/voiceSnap.test.ts
    - app/src/lib/driftHysteresis.ts
    - app/src/lib/__tests__/driftHysteresis.test.ts
  modified:
    - app/src/components/VideoCompare.tsx
    - app/src/components/KeypointOverlay.tsx
    - app/src/app/analysis/result.tsx

key-decisions:
  - "스냅 시각 소스 = FaultZoomComparison.refVideoSec 만 (refFrameIdx/fps 재계산 금지 — F-3 근본원인 재도입 차단). 부재 record 는 스냅 생략 = 순간 날조 0"
  - "복원 목표는 최초 멈춤 시각 하나 (체인 발화 중 restoreRef null 일 때만 저장) — 체인 큐마다 짝 갱신해도 재개 정렬 보존"
  - "seek/오프셋 경로는 clearVoiceSnapOnly (복원 seek 생략) — 직후 setRightToStudentTime 재-seek 가 정렬 재확립, 이중 seek 스터터 차단"
  - "lastDriftSeekAtRef 는 follow/legacy 공유 1개 (한 tick 에 하나만 진입) — 간격 회계 단일"
  - "PLAYBACK_EMPHASIS_SCALE 은 keypoint circles 루프에서만 곱함 — RADIUS/STROKE_* 상수는 정지 번호 마커·그룹 배지와 공유라 전역 상향 금지"

patterns-established:
  - "음성 멈춤 스냅/복원 상태 정리는 voicePauseRef 리셋 5지점과 동일 지점에 건다 (tick 재개=복원, togglePlay 2분기=복원, seekBoth·오프셋 조작=클리어만)"

requirements-completed: [BELLE-0807-5, BELLE-0807-6, BELLE-0807-7]

# Metrics
duration: 14min
completed: 2026-08-07
---

# Quick 260807-iwp: belle 08-07 오후 실기기 3건 수리 Summary

**음성 멈춤 동안 기준 패널이 record 짝 프레임(refVideoSec)을 보여주고 재개 시 원위치 복원, 드리프트 보정에 0.3s 임계+0.8s 간격 히스테리시스, 재생 중 관절 점 1.3배 강화 — 전부 앱 전용, 채점·doc·백엔드 무접촉**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-07T04:49:00Z
- **Completed:** 2026-08-07T05:03:18Z
- **Tasks:** 3 (TDD 2 + auto 1)
- **Files modified:** 7 (신규 4 + 수정 3)

## Accomplishments

- BELLE-0807-5 ("정은지 선수 영상이 음성이랑 안 맞는다"): 발화 멈춤 순간 기준(우) 패널을 그 record 의 짝 시각(FaultZoomComparison.refVideoSec — 백엔드 F-3 방출 기준 도메인 초)으로 seek. 체인 발화마다 제 짝 갱신(짝 없으면 원위치 복귀 — 오귀속 차단), 재개·사용자 제스처 직전 최초 멈춤 시각으로 복원 후 기존 백오프 관찰창이 그대로 이어짐. refVideoSec 없는 record(refMatched=false·legacy doc)는 스냅 0.
- BELLE-0807-6 ("정은지 선수 영상이 끊겨 가지구"): Build 16 의 매 tick 즉시 보정(임계 0.2s)을 임계 0.3s + 보정 seek 최소 간격 0.8s 로 재균형. 간격 내엔 대기, 간격 후 잔존 drift 는 반드시 보정(수렴 보장 — Build 16 이 막으려던 drift 누적 재발 없음). follow/legacy 양 지점 치환, 상수·판정은 driftHysteresis.ts 단일 출처.
- BELLE-0807-7 ("마커는 좀 더 진하면 좋을 듯"): 재생 중 학생 오버레이 관절 점(흰 기본·빨강 활성 큐) 반지름·외곽선 1.3배 + 흰 점 어두운 외곽선 alpha 0.6→0.8. opt-in prop 이라 정지 상태 번호 마커·그룹 경계·기준(우) 패널·전체화면 정지 렌더는 byte 보존.
- 전 스위트 15파일 208 tests GREEN (기준선 13파일 196 + voiceSnap 5 + driftHysteresis 7), typecheck GREEN.

## Task Commits

Each task was committed atomically:

1. **Task 1: 음성 멈춤 짝 프레임 스냅 + 재개 복원 (TDD)** — `66344400` (test: RED) → `41e62f62` (fix: GREEN)
2. **Task 2: 드리프트 보정 히스테리시스 (TDD)** — `3395ef9d` (test: RED) → `258f266e` (fix: GREEN)
3. **Task 3: 재생 중 오버레이 점 시인성 강화** — `30c1bcb4` (fix)

**Plan metadata:** 없음 — 오케스트레이터 지시로 docs 아티팩트 미커밋.

## Files Created/Modified

- `app/src/lib/voiceSnap.ts` — buildRefSnapSecs 순수 빌더 (recordId→refVideoSec, 유한 >=0 만, 중복 first-wins, 크래시 0). 헤더에 F-3 재계산 금지 근거 박제.
- `app/src/lib/__tests__/voiceSnap.test.ts` — 5 tests (유효 등재/무효 드롭/키 무효 드롭/first-wins/null 입력).
- `app/src/lib/driftHysteresis.ts` — DRIFT_CORRECT_THRESHOLD_S(0.3)/DRIFT_SEEK_MIN_INTERVAL_MS(800) + shouldCorrectDrift. 헤더에 Build 16 절충 이력 + belle 08-07 재균형 근거.
- `app/src/lib/__tests__/driftHysteresis.test.ts` — 7 tests (임계 이하/간격 내 대기/간격 후 수렴/최초 즉시/경계 >=/NaN/상수 박제).
- `app/src/components/VideoCompare.tsx` — cueRefSnapSecs prop + ref 미러 + 헬퍼 3개(snapRightToCuePair/unsnapRight/clearVoiceSnapOnly), voicePauseRef 리셋 5지점 배선(발화 pause·체인=스냅, tick 재개·togglePlay 2분기=복원, seekBoth·오프셋 조작=클리어), 드리프트 보정 2곳 shouldCorrectDrift 치환 + lastDriftSeekAtRef, 로컬 임계 상수 제거, 정책 주석 갱신.
- `app/src/components/KeypointOverlay.tsx` — playbackEmphasis prop(기본 false) + PLAYBACK_EMPHASIS_SCALE(1.3), keypoint circles 루프에만 반지름·외곽선 배율 + 흰 점 외곽선 alpha 상향.
- `app/src/app/analysis/result.tsx` — cueRefSnapSecs useMemo(matchZoomForRecord 재사용, isRecordHidden 필터 cueWindows 동일) + VideoCompare 전달, leftOverlay playbackEmphasis={playingInversion}.

## Decisions Made

- 스냅 배선 주석에 판독 근거 박제: 음성 멈춤 중 follow(leftPlaying)/legacy(bothPlaying) 드리프트 보정은 가드로 미진입 — 신규 게이트 코드 불요 (planner_findings 2 인용, 재조사 없이 주석만).
- 복원 직후 별도 지연 없음 — fpw 백오프 관찰창(RESUME_RETRY_AT_TICKS + 마지막 재시도 직전 제자리 nudge)이 seek 미적용 스톨을 감시 (planner_findings 4).
- Phase 12 scrub 우회 주석의 "drift > 0.2" 스테일 수치를 임계 일반 서술로 정정 (planner_findings 5 의 444~450 갱신 범위 내).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] buildRefSnapSecs 입력 타입에 `recordId: null` 허용 추가**
- **Found during:** Task 1 (GREEN 배선)
- **Issue:** 계획 스펙 시그니처는 `{ recordId?: string; refVideoSec?: number }` 인데 `DeductionRecord.recordId` 계약은 `string | null | undefined` (types/analysis.ts:589) — 그대로면 result.tsx 조립부가 typecheck 실패.
- **Fix:** 순수 함수 입력을 `{ recordId?: string | null; refVideoSec?: number }` 로 확장 (null 도 드롭 경로 — 방어 의미 동일), 테스트에 null recordId 드롭 케이스 포함.
- **Files modified:** app/src/lib/voiceSnap.ts, app/src/lib/__tests__/voiceSnap.test.ts
- **Verification:** voiceSnap 5 tests PASS + typecheck GREEN
- **Committed in:** 66344400/41e62f62 (Task 1 commits)

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking)
**Impact on plan:** 계약 타입 정합을 위한 최소 확장 — 동작·의미 변화 0, scope creep 없음.

## Verification Results

- 전 스위트 파일 단위 루프: 15파일 208 tests 전부 PASS (기준선 196 + 신규 12, 회귀 0)
- `cd app && npm run typecheck` GREEN
- 무접촉 증명 (base 01a83cd7..HEAD 전 구간): `backend/`·`app/src/types/`·`playbackInvariant.ts`·`cueTrack.ts` diff 0
- grep 게이트: VideoCompare `refFrameIdx` 0 / `const DRIFT_CORRECT_THRESHOLD_S` 0 / `shouldCorrectDrift(drift` 2, result.tsx `buildRefSnapSecs(` 1 / `playbackEmphasis={playingInversion}` 1, KeypointOverlay `playbackEmphasis` 6
- 신규 hex 색 리터럴 0 (rgba alpha 계수 조정만), 이모지 0

## TDD Gate Compliance

- Task 1: RED `66344400`(test) → GREEN `41e62f62`(fix) — RED 단계 실패 확인 후 진행.
- Task 2: RED `3395ef9d`(test) → GREEN `258f266e`(fix) — RED 단계 실패 확인 후 진행.
- REFACTOR 커밋 없음 (정리 불요 — GREEN 시점 코드가 최종형).

## Issues Encountered

None — 계획의 planner_findings 가 배선 지점(voicePauseRef 리셋 5곳·보정 2곳)을 정확히 지목해 재조사 없이 진행.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 시뮬 렌더 확인·OTA 발행은 계획 범위 밖 — 오케스트레이터가 사이클 후 수행.
- belle 실기기 확인 포인트: (1) 음성 중 우측 패널이 말하는 결함의 기준 자세를 보여주는지 + 재개 후 정렬 유지, (2) 정은지 패널 끊김 완화 체감, (3) 재생 중 점 진하기 (PLAYBACK_EMPHASIS_SCALE 1.3 — 부족하면 상수만 상향).
- refVideoSec 없는 실업로드 doc(refMatched=false)은 스냅이 안 걸리는 것이 정상 (순간 날조 0 설계) — 재분석이 짝을 만들면 자동 활성.

## Self-Check: PASSED

- app/src/lib/voiceSnap.ts — FOUND
- app/src/lib/__tests__/voiceSnap.test.ts — FOUND
- app/src/lib/driftHysteresis.ts — FOUND
- app/src/lib/__tests__/driftHysteresis.test.ts — FOUND
- commits 66344400/41e62f62/3395ef9d/258f266e/30c1bcb4 — FOUND (worktree-agent-a6c5de842425e6816)

---
*Phase: quick-260807-iwp*
*Completed: 2026-08-07*
