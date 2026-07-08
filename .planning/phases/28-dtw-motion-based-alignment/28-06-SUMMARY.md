---
phase: 28-dtw-motion-based-alignment
plan: 06
subsystem: motion-alignment (VideoCompare 워핑 소비 + tier 배지)
tags: [dtw, alignment, video-playback, warp, feedforward, tier-badge, wave-3, typecheck, ota]
requirements: [ALGN-04]
dependency_graph:
  requires:
    - "28-01 (alignmentWarp.ts warpTime/segmentRate/normalizeMotionAlignment 순수 함수)"
    - "28-03 (MotionAlignment 계약 analysis.ts 이관 — import 대상)"
  provides:
    - "VideoCompare alignment prop 소비 — 학생(left)=master 시계 불변, 정은지(right)만 warp"
    - "right 쓰기 helper 2개 격리 (setRightToStudentTime/setBothAbsoluteTime) — 정렬 활성 경로 절대시간 대입 구조적 차단 (MEDIUM-1)"
    - "rate feedforward + tick seek feedback 이중 제어 (D-01)"
    - "tier 사다리 3단 정직 배지 (warped/trim_only/disabled)"
  affects:
    - "28-07 (result.tsx 가 normalizeMotionAlignment 통과분을 alignment prop 으로 전달 — 소비 활성화)"
    - "22-* (source:'vlm' alignment 도 동일 prop 경유 소비 — 상위 호환)"
tech_stack:
  added: []
  patterns:
    - "prop 부재/null = legacy 100% 보존 (faultZoomStatus/tier optional 선례)"
    - "ref 미러(alignmentRef/lastRateRef)로 setInterval 클로저 stale 회피 (선행 tick/scrub ref 패턴)"
    - "helper 격리 + grep 기계 판정 (직접 대입 정확히 2곳) — legacy 예외 grep 폐기"
    - "feedforward(rate) + feedback(seek) 이중 제어 (A2 rate 지연 미문서화 방어)"
key_files:
  created: []
  modified:
    - app/src/lib/alignmentWarp.ts
    - app/src/components/VideoCompare.tsx
decisions:
  - "MotionAlignment 는 alignmentWarp.ts 에서 로컬 정의 제거 → analysis.ts import+재수출 (단일 출처, 28-01 이관 예고 소비)"
  - "prop 을 normalizeMotionAlignment 로 소비측 재검증 (T-28-02) — 이미 정규화됐더라도 malformed 가 재생 제어 오작동시키는 것 순수 함수로 격리 차단"
  - "종료 판정: 활성 시 either-own-end (cR=warp(ref-time)이라 min(cL,cR) 혼합 무의미), 비활성은 기존 로직 그대로"
  - "needsStartSync: 활성이면 setRightToStudentTime(leftCurrent)로 분기 (slowerTime min 절대대입은 워핑 하 무의미) — MEDIUM-1 실체 차단"
metrics:
  duration_min: 30
  tasks_completed: 2
  files_created: 0
  files_modified: 2
  completed_date: 2026-07-08
---

# Phase 28 Plan 06: VideoCompare 워핑 소비 (D-01) Summary

정은지(right) 재생을 학생(left) 마스터 타임라인에 동작 기준으로 워핑하되, 기존 100ms tick drift 보정 인프라(Build 16 UAT 산물)를 재학습 없이 재사용해 **목표값만** `cR ≈ cL`에서 `cR ≈ warpTime(alignment, cL)`로 교체했다. right 쓰기를 helper 2개로 격리해 정렬 활성 경로에 절대시간 seek 이 구조적으로 불가능하게 만들었고(MEDIUM-1), rate feedforward + tier 정직 배지 3단을 얹었다. alignment 부재 시 현행 절대시계 동작 100% 보존.

## What Was Built

### Task 1 — 계약 import 전환 + helper 격리 배선 (commit `eb84774`)

- **alignmentWarp.ts**: 로컬 `MotionAlignment` 타입 정의 제거 → `import type { MotionAlignment } from '../types/analysis'` + `export type { MotionAlignment }` 재수출. 함수 본체 무변경 (3-way lockstep 단일 출처는 analysis.ts).
- **VideoCompare.tsx — prop + helper 3종**:
  - `alignment?: MotionAlignment | null` prop 신설 (JSDoc 에 D-01/D-02 부재=100% 보존 박제).
  - 소비측 `normalizeMotionAlignment(alignmentInput ?? null)` 재검증 (T-28-02) — malformed/모순 alignment 가 rate/seek 를 오작동시키는 것 순수 함수로 격리.
  - `alignmentActive = !!alignment && alignment.tier !== 'disabled'`, `targetRefTime(t) = active ? warpTime : identity`, `setRightToStudentTime(t)` (**right 쓰기의 유일한 warp 경유 지점**), `setBothAbsoluteTime(t)` (legacy 절대 동기 전용, `!alignmentActive` 가드 분기 안에서만).
  - `alignmentRef` 미러로 tick(setInterval 클로저)의 stale alignment 회피.
- **쓰기 지점 교체** (직접 대입은 helper 2개 내부의 2곳만): seekBoth·restart·togglePlay(isAtEnd/needsStartSync) 전부 `setRightToStudentTime` 경유. needsStartSync 는 `alignmentActive` 분기 — 활성이면 `setRightToStudentTime(leftCurrent)`(slowerTime min 절대대입 차단, MEDIUM-1 실체), 비활성이면 `setBothAbsoluteTime(slowerTime)`.
- **tick 보정**: 활성 시 left back-seek 없이 `|cR - targetRefTime(cL)| > DRIFT_CORRECT_THRESHOLD_S(0.2)` 일 때만 `setRightToStudentTime(cL)`. 비활성 시 기존 상호 back-seek 그대로(right 는 helper 경유=identity).
- **종료 판정**: 활성 시 either-own-end(cR=warp(ref-time)이라 min 혼합 무의미), 비활성은 기존 `minReachedShortEnd || bothReachedOwnEnd` 보존.

### Task 2 — rate feedforward + tier 배지 (commit `1432ef5`)

- **rate feedforward**: tick 내 `segmentRate(alignment, cL)` 계산, **직전 설정값과 다를 때만** `rightPlayer.playbackRate` 대입(구간 경계 한정, 매 tick 재설정=재버퍼 위험 회피). 비활성/pause 시 1.0, unmount/재설치 cleanup 에서 1.0 복원. `preservesPitch` 는 muted=true 라 무접촉. 주석에 feedforward(rate)+feedback(tick seek) 이중 제어 근거(A2).
- **tier 배지 3종** (`alignBadgeCopy`): warped="동작 기준으로 자동 구간을 맞췄어요", trim_only="동작 차이가 있어 시작점만 맞췄어요 (배속 조정은 꺼짐)", disabled="기준 동작과 차이가 커 자동 정렬을 껐어요". alignment 부재(legacy)=기존 정적 카피 유지. 수치(DTW distance) 미표기(사용자 의미 없는 원값, Phase 20 A4). 기존 alignBadge* 토큰 재사용, 하드코딩 색/간격 0.
- Phase 20 `TODO(deferred-backend)` 주석 → "Phase 28 해소 — tier 실데이터 기반" 갱신.

## Verification

- **Task 1**: `npm run typecheck` exit 0 + `WARP_ROUTED` (직접 `rightPlayer.currentTime =` 대입 정확히 2곳 = helper 2개 내부, rightPlayer 쓰기 라인에 slowerTime 0). `setRightToStudentTime`=9(≥5) / `setBothAbsoluteTime`=3(≥2) / alignmentWarp import=1 / `alignment?`=1.
- **Task 2**: `npm run typecheck` exit 0. `playbackRate`=3(≥2, tick set + cleanup restore) / tier 카피 3종 각 1 / 하드코딩 hex=1 (baseline 동일, 증가 0 — 기존 `#F4F4F4` slotEmpty 뿐).
- **legacy 보존**: alignment 부재/null/disabled 경로는 조건 분기로 기존 코드 그대로(삭제 0) — 비활성 시 targetRefTime/setRightToStudentTime 이 identity 라 Build 16 drift 보정 동작 무변경.

## Deviations from Plan

None — 2 태스크 계획대로 실행. (환경 처리 1건, 계획 무변경: worktree app 에 node_modules 부재 → main repo node_modules 임시 심링크(gitignored, 커밋 무관)로 `npm run typecheck` 실행 후 제거.)

한 가지 커밋 순서 기록: Task 1·2 가 같은 파일(VideoCompare.tsx)을 편집하므로, 계획의 per-task 분리 커밋을 지키기 위해 Task 2 hunk 를 임시 revert → Task 1 커밋(eb84774) → Task 2 재적용 → 커밋(1432ef5) 순서로 진행. 계약/로직 무변경, 최종 상태는 두 태스크 합.

## Notes

- **채점 무접촉:** 앱 표시/재생만 — 점수/판정 재계산·재해석 0접촉 (deductionLabels 헤더 원칙 정합). 신규 native 모듈 0 (expo-video playbackRate/currentTime 기존 API), JS-only → OTA 가능.
- **의도된 seam (스텁 아님):** `alignment` prop 은 현재 소비처(result.tsx)가 전달하지 않으면 undefined→null→legacy 100% 보존. 실제 데이터 배선(result.motionAlignment → normalizeMotionAlignment → prop)은 28-07 소관. UI 로 흐르는 빈 데이터 스텁이 아니라, 부재 시 검증된 legacy 폴백(faultZoomStatus/tier optional 선례).
- **threat 정합:** T-28-02(malformed 소비)=normalizeMotionAlignment 재검증+순수 함수 격리 / T-28-15(오도 워핑)=tier 사다리 배지 정직 고지 / T-28-16(unwarped seek/stutter)=helper 2개 격리(직접 대입 2곳 grep)+setBothAbsoluteTime !alignmentActive 전용+threshold 0.2s 유지 — 전부 mitigate 반영.
- **실기기 체감(A2 rate 반응성)은 28-08 end-of-phase UAT 항목** (이 플랜은 typecheck+grep 게이트까지).

## Commits

- `eb84774` feat(28-06): setRightToStudentTime helper 격리 워핑 배선
- `1432ef5` feat(28-06): rate feedforward + tier 배지

## Self-Check: PASSED

- 수정 파일 2 + SUMMARY 존재 확인 (alignmentWarp.ts / VideoCompare.tsx / 28-06-SUMMARY.md).
- 커밋 2개 존재 확인 (eb84774 / 1432ef5).
- working tree clean (심링크 제거, 미커밋 산출물 0).
