---
phase: 19-vision-hybrid
plan: 03
subsystem: ui
tags: [react-native, three-fiber, pose-3d, coordinate-normalization, typescript, smoke-test]

# Dependency graph
requires:
  - phase: 19-01
    provides: joints3d 저장/읽기 경로 + 3D 골격 뷰어 인프라
provides:
  - "normalizePose3d 단일 source 정규화 모듈 (COCO-17 hip-center recenter + torso/bbox 정규화, frame 수 보존, standalone TS)"
  - "reshapePose3dData 가 raw RTMW 픽셀좌표를 viewer frustum origin-centered normalized 좌표로 변환 (저장부/계약 불변, 과거 doc 즉시 호환)"
  - "LOCAL tsc 컴파일 + createRequire production-import smoke (알고리즘 복제 0, no-copy grep gate)"
affects: [19-04, phase-15-pilot-uat, testflight-native-build]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "단일 정규화 수학 source 모듈 (standalone TS, react/expo import 0) → joints.ts + smoke 둘 다 import"
    - "smoke 스크립트가 컴파일/import 경로 자가 소유 (LOCAL node_modules/typescript/bin/tsc + createRequire, 신규 설치 0)"
    - "thrown error + process.exitCode + finally cleanup (Node process.exit 가 finally unwind 안 함 → inline process.exit 금지)"
    - "frame 수 STABLE 보존 (per-frame null/drop 금지, last-resort = prev-valid 복제 또는 zero-skeleton, 시퀀스 전체 불가 시 whole null)"

key-files:
  created:
    - app/src/lib/normalizePose3d.ts
    - app/scripts/_smoke_joints_normalize.mjs
  modified:
    - app/src/lib/joints.ts
    - .gitignore

key-decisions:
  - "정규화는 읽는 쪽(joints.ts reshapePose3dData)에 둠 — backend joints3d 저장부 + 3중 계약(analysis.ts space enum) 불변, 과거 raw-픽셀 doc 도 즉시 정규화"
  - "hip/shoulder 인덱스는 jointKeys 인자(COCO-17 KEYPOINT_NAMES)에서 indexOf 도출 — 8 angle JOINT_KEYS 참조 금지 (HIGH-3)"
  - "Task 2 실기기 GL 렌더 육안 검증은 approved-with-deferred — 실제 디바이스 확인은 다음 native build 시점으로 연기, 미해소 human-UAT 항목으로 추적"

patterns-established:
  - "단일 source 정규화 모듈: 순수 수학을 standalone TS 로 추출 → production(joints.ts)과 smoke 가 동일 함수 import (false coverage 방지, BLOCKER-2)"
  - "smoke 자가-컴파일: LOCAL tsc 바이너리로 .ts 단독 컴파일 후 createRequire 로 production import (tsx/ts-node 부재 환경의 결정론적 import, HIGH-1)"
  - "process.exit-free smoke 종료: let exitCode + try/catch(exitCode=1)/finally(cleanup) + finally 이후 process.exitCode (MEDIUM-1)"

requirements-completed: [TRUST-04]

# Metrics
duration: ~10min (continuation/finalize session; Task 1 prior session)
completed: 2026-06-18
---

# Phase 19 Plan 03: 3D 골격 좌표 정규화 Summary

**reshapePose3dData 가 raw RTMW 픽셀좌표를 normalizePose3d 단일-source 정규화(COCO-17 hip-center recenter + torso/bbox, frame 수 보존)로 viewer frustum 안에 넣어 빈 회색 GL 렌더 버그(TRUST-04)를 고침 — backend·3중 계약 불변, LOCAL-tsc production-import smoke 로 검증**

## Performance

- **Duration:** Task 1 = 직전 세션 / 본 세션 = finalize (~10 min)
- **Completed:** 2026-06-18
- **Tasks:** 1 auto (완료) + 1 checkpoint:human-verify (approved-with-deferred-device-check)
- **Files modified:** 4 (normalizePose3d.ts 신설, joints.ts 수정, _smoke_joints_normalize.mjs 신설, .gitignore)

## Accomplishments

- **normalizePose3d.ts 단일 source** — react/expo/RN import 0 의 standalone 순수 수학. COCO-17 `jointKeys.indexOf('left_hip'/'right_hip'/'left_shoulder'/'right_shoulder')` 로 hip midpoint recenter + torso length 정규화(primary), centroid+bbox fallback, last-resort(prev-valid/zero-skeleton), 시퀀스 전체 불가 시 whole null. 모든 출력 좌표 finite, 입력=출력 frame 수.
- **reshapePose3dData → normalizeFrames 호출** — flat→(T,J,3) reshape 직후 단일 정규화 source 호출. joints.ts 안 좌표 수학 복제 0. 저장부/계약 불변이라 과거 raw-픽셀 분석 doc 도 즉시 정규화되어 렌더.
- **_smoke_joints_normalize.mjs production-import 검증** — LOCAL `node_modules/typescript/bin/tsc` 로 normalizePose3d.ts 단독 컴파일 후 `createRequire` 로 PRODUCTION `normalizeFrames` import. synthetic raw COCO-17 ~(320,240) → maxAbsCoord<=3 + frame 수 보존 + fallback + last-resort + whole-null 4 케이스 자동검증. 알고리즘 복제 0 (no-copy grep), inline process.exit 0, finally temp-dir cleanup.
- **검증 게이트 통과** — `npm run typecheck` (tsc --noEmit) clean / `node scripts/_smoke_joints_normalize.mjs` exit 0 (`SMOKE_PASS maxAbsCoord<=3 + frame_count_stable + production_import`).

## Task Commits

1. **Task 1: normalizePose3d single-source + reshapePose3dData 호출 + frame-수-보존 + LOCAL-tsc-compile production-import smoke (TRUST-04)** - `7f9d371` (feat) — 직전 세션 commit
2. **Task 2: 실기기 3D 골격 렌더 육안 검증 (checkpoint:human-verify, gate=blocking)** - 코드 commit 없음 (human-verify gate). **approved-with-deferred-device-check** — 아래 "Outstanding Human-UAT" 참조.

**Plan metadata:** (본 SUMMARY + STATE + ROADMAP 커밋)

## Files Created/Modified

- `app/src/lib/normalizePose3d.ts` (신설, 229줄) - 정규화 순수 수학 단일 source. standalone TS (외부 import 0). `normalizeFrames(frames, jointKeys): number[][][] | null`. COCO-17 indexOf hip-center recenter + torso/bbox normalize + last-resort + whole-null. finite sanity.
- `app/src/lib/joints.ts` (수정, +12/-1) - reshapePose3dData 가 reshape 직후 normalizeFrames import & 호출. graceful null 정책 유지.
- `app/scripts/_smoke_joints_normalize.mjs` (신설, 213줄) - LOCAL tsc 컴파일 + createRequire production import 검증 smoke. thrown error/process.exitCode/finally cleanup.
- `.gitignore` (수정, +3) - `app/scripts/_*.mjs` 광범위 ignore 규칙 유지 + `!app/scripts/_smoke_joints_normalize.mjs` negation 예외 (정식 검증 아티팩트, files_modified + acceptance grep 가 정확한 경로 박제 → 추적 필수).

## Decisions Made

- **정규화 위치 = 읽는 쪽(joints.ts)** — backend joints3d 저장부 + analysis.ts space enum 3중 계약을 건드리지 않고 과거 doc 까지 즉시 호환. (19-RESEARCH Pattern 4 선택지 B 권장, Pitfall 3 저장 vs 읽기.)
- **hip/shoulder 인덱스 = jointKeys 인자(COCO-17)에서 indexOf** — 8 angle JOINT_KEYS 가 아님. 엉뚱한 점 중심 정규화(T-19-11 Tampering) 차단.
- **frame 수 STABLE 보존** — per-frame null/drop 시 PoseViewer3D 의 timeline currentFrame/ipsfViolationFrames 인덱싱 desync (T-19-14). last-resort = prev-valid 복제 또는 zero-skeleton, 시퀀스 전체 불가 시에만 whole null.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] .gitignore negation 예외 추가 (app/scripts/_smoke_joints_normalize.mjs)**
- **Found during:** Task 1 (직전 세션)
- **Issue:** root `.gitignore` 에 `app/scripts/_*.mjs` 광범위 ignore 규칙(Phase 17 ad-hoc 진단 스크립트용) 이 존재 → plan 의 files_modified + acceptance grep gate 가 박제한 정식 검증 아티팩트(`_smoke_joints_normalize.mjs`) 가 추적 불가. 커밋해도 무시되어 검증 게이트가 무력화.
- **Fix:** 광범위 ignore 규칙은 유지하고 `!app/scripts/_smoke_joints_normalize.mjs` negation 1줄 예외 추가 (주석 = "정식 검증 아티팩트, acceptance grep gate 가 경로 박제하므로 추적 필수").
- **Files modified:** .gitignore
- **Verification:** `git check-ignore app/scripts/_smoke_joints_normalize.mjs` → not ignored. 파일이 commit 7f9d371 에 정상 추적됨.
- **Committed in:** `7f9d371` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** 정식 검증 아티팩트 추적 가능화 — 검증 게이트 보존에 필수. scope creep 없음.

## Issues Encountered

None — Task 1 은 직전 세션에서 acceptance criteria 전부 통과한 채 commit 됨. 본 세션은 finalize(검증 재확인 + SUMMARY + state) 만 수행.

## Outstanding Human-UAT (DEFERRED)

**Task 2: 실기기 3D 골격 렌더 육안 검증 — approved-with-deferred-device-check**

- **상태:** belle "approved" — 단, 실제 on-device 시각 검증은 **다음 native build 시점으로 연기**. plan 자체 note 박제: "belle TestFlight 실기기 검증은 다음 native build 시점(STATE.md Wave 2 override)에 함께 가능".
- **자동 검증으로 커버된 부분:** smoke 가 PRODUCTION `normalizeFrames` 로 maxAbsCoord<=3 + frame 수 보존 + fallback/last-resort/whole-null 을 검증. PoseViewer3D ErrorBoundary(R8) + typecheck/grep 가 로컬 안전망.
- **미해소(디바이스 육안이 유일한 동작 게이트):**
  1. 신규 분석 + 과거 raw-픽셀 doc 둘 다 3D 골격이 회색 영역이 아니라 카메라 frustum 안에 실제 렌더되는지.
  2. OrbitControls 제스처 회전/줌 시 골격이 frustum 안에 유지되는지.
  3. occlusion 있던 과거 분석(hip/shoulder 일부 누락) fallback 정규화 렌더 + timeline scrub frame 누락/점프 0.
- **추적:** 본 항목은 outstanding human-UAT 으로 /gsd-progress + /gsd-audit-uat 에 surface 되어야 함. Phase 04-02 Wave 2 belle override(STATE.md) 와 동일하게 다음 native build TestFlight 검증 묶음에 합류.

## User Setup Required

None — 외부 서비스 구성 불필요. (앱 클라이언트 좌표 변환 순수함수 + standalone smoke 만 변경, 신규 endpoint/auth/네트워크 표면 0.)

## Next Phase Readiness

- **19-04 진입 가능** — joints3d 정규화가 viewer frustum 정합 보장 (수치 자동검증 PASS). backend·3중 계약 불변이라 후속 plan 의 분석 경로 영향 0.
- **Blocker/Concern:** Task 2 실기기 GL 렌더 육안 검증이 DEFERRED — 다음 native build TestFlight 시점에 belle 가 신규+과거 doc 골격 렌더 + OrbitControls + timeline scrub 을 검증해야 최종 동작 게이트 완료. (코드 수준은 모두 통과, GL frustum 내 실 렌더만 미확인.)

## Self-Check: PASSED

- FOUND: app/src/lib/normalizePose3d.ts
- FOUND: app/scripts/_smoke_joints_normalize.mjs
- FOUND: .planning/phases/19-vision-hybrid/19-03-SUMMARY.md
- FOUND commit: 7f9d371 (Task 1)

---
*Phase: 19-vision-hybrid*
*Completed: 2026-06-18*
