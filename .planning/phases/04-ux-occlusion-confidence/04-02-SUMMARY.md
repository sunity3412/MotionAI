---
phase: 04-ux-occlusion-confidence
plan: "02"
subsystem: ui
tags: [react-native, react-three-fiber, expo-three, expo-gl, three.js, 3d-viewer, ipsf, occlusion]

requires:
  - phase: 04-01
    provides: "AnalysisResult.joints3d flat 필드 + AiSynthesisMeta(warnings/debugWarnings/audit/cost) — 04-02 reshaper 와 AccuracyLimitBadge 가 소비"
provides:
  - "Stage 3 사용자 3D 자세 뷰어 (PoseViewer3D) — VideoCompare 아래 삽입, 손가락 회전 가능"
  - "joints.ts reshapePose3dData — Firestore flat joints3d → (T, J, 3), angles 오용 차단"
  - "userAnalyses.ts normalize() — joints3d 5 필드 + aiSynthesisMeta(warnings + debugWarnings + audit/cost 9 필드) compat layer"
  - "AccuracyLimitBadge — ai_synthesis_failed warning 트리거, 블랙박스 카피"
  - "hasSynthesisWarning(result, code) helper — canonical surface = aiSynthesisMeta.warnings 단일화"
  - "Phase 4 alias 토큰 6개 (viewer3dBg/Bone/Joint/JointNormal + accuracyLimitBg/Text)"
affects: [04-03, 04-04, 04-05, phase-11, phase-12-deferred]

tech-stack:
  added: [three@0.184.0, "@react-three/fiber@9.6.1", "@react-three/drei@10.7.7", "expo-three@8.0.0", "expo-gl@16.0.7"]
  patterns:
    - "/native import 경로 분리 — @react-three/fiber/native + @react-three/drei/native (Pitfall 2)"
    - "Canvas/GL ErrorBoundary 격리 — class ErrorBoundary 가 result.tsx route 보호 (R8)"
    - "blackbox helper (hasSynthesisWarning) — canonical warning surface 단일화 (BLOCKER-3)"
    - "alias 토큰 — 기존 hex 복사 금지, 의미 alias 만 추가 (CLAUDE.md §4 정합)"

key-files:
  created:
    - app/src/components/PoseViewer3D.tsx
    - app/src/components/AccuracyLimitBadge.tsx
    - app/src/lib/joints.ts
  modified:
    - app/src/theme/colors.ts
    - app/src/types/analysis.ts
    - app/src/lib/userAnalyses.ts
    - app/src/app/analysis/result.tsx

key-decisions:
  - "drei OrbitControls /native 가용 확인 → 직접 사용 (PanResponder fallback 미채택, resume-signal 'approved OrbitControls:true' 박제)"
  - "EAS 실기기 smoke 검증 belle override 적용 — R8 ErrorBoundary + typecheck + grep gate 가 local safety net (다음 EAS preview 빌드에서 native 검증 재확인)"
  - "AiSynthesisMeta audit/cost 9 필드 optional 화 — backend payload 보다 좁지 않게 + 합성 미수행 분석의 partial emit 허용"
  - "PoseViewer3D referenceJoints 는 예약 prop only — Wave 2 = user-only viewer (HIGH-3). ReferenceMotion 타입 + normalizer 확장은 follow-up plan 으로 분리"
  - "result.tsx 3D 섹션 = joints3d != null 조건부 — Phase 4 이전 분석 doc 호환 (graceful 생략)"

patterns-established:
  - "Pattern A: Firestore flat → reshape 로더 (joints.ts) — angles 오용 length guard 로 차단, source 단계 차단 + 런타임 guard 이중 박제"
  - "Pattern B: blackbox 카피 — 사용자 노출 문자열은 컴포넌트 모듈 상단 상수 (LINE_OCCLUSION/LINE_SIDE) 로 격리, 내부 코드명 (ai_synthesis_failed 등) 은 helper 안에만 둠"
  - "Pattern C: warning surface 단일화 — top-level result.warnings 금지, aiSynthesisMeta.warnings 만 canonical. helper (hasSynthesisWarning) 가 caller 의 optional chain 부담 제거"

requirements-completed: [POSE-03]

duration: ~25min
completed: 2026-06-13
---

# Phase 04 Plan 02: Stage 3 사용자 3D 자세 뷰어 Summary

**react-three-fiber/native Canvas + drei OrbitControls + ErrorBoundary 격리로 손가락 회전 가능한 3D 자세 뷰어를 결과 화면에 삽입, joints3d Firestore wiring + ai_synthesis_failed 블랙박스 배지까지 함께 통합**

## Performance

- **Duration:** 약 25분 (Task 3 + Task 4)
- **Started:** 2026-06-13T13:04:54Z (worktree base reset 시점)
- **Completed:** 2026-06-13 (Task 4 commit a1b055c)
- **Tasks:** 2 (Task 3 + Task 4 — Task 1 은 선행 wave 에서 완료, Task 2 는 belle override 로 skip)
- **Files created:** 3
- **Files modified:** 4

## Accomplishments

- joints3d 전용 reshaper (`reshapePose3dData`) — `result.angles` 오용을 source 단계 + 런타임 guard 양쪽에서 차단 (R3 박제 강화)
- `AccuracyLimitBadge` — `aiSynthesisMeta.warnings` 캐노니컬 surface 단일 source 박제, 블랙박스 카피만 노출 (D-05 R7)
- `userAnalyses.ts normalize()` — joints3d 5 필드 + aiSynthesisMeta 14 필드 (warnings + debugWarnings + audit 3 + cost 6) 전부 보존 (HIGH-2 / HIGH-5)
- `PoseViewer3D` — `/native` import 경로 + class `ErrorBoundary` + COCO-17 SkeletonMesh + drei `OrbitControls` + 4개 CameraPresetBar + PanResponder TimelineScrubber. 다크 배경 hex 0, 토큰만 사용
- `result.tsx` — `hasSynthesisWarning(result, code)` helper 신설로 caller 의 optional chain 부담 제거. AccuracyLimitBadge 를 헤더에, PoseViewer3D 를 VideoCompare 아래에 graceful 조건부 삽입

## Task Commits

각 task 는 별도로 atomic commit:

1. **Task 3: colors 토큰 + joints.ts + userAnalyses wiring + AccuracyLimitBadge** — `393929d` (feat)
2. **Task 4: PoseViewer3D + result.tsx 통합** — `a1b055c` (feat)

선행 Task 1 (`03dc3c9 chore(04-02): install R3F + expo-three stack + PoseViewer3DSmokeScreen`) 는 이 worktree 진입 전 main 에 이미 머지되어 있었음.

## Files Created/Modified

### Created
- `app/src/components/PoseViewer3D.tsx` — Stage 3 R3F 3D viewer. `/native` Canvas + class ErrorBoundary + COCO-17 SkeletonMesh + CameraPresetBar 4개 + TimelineScrubber. joints null = graceful 섹션 생략. referenceJoints 는 Wave 2 미사용 (예약 prop).
- `app/src/components/AccuracyLimitBadge.tsx` — D-08 정확도 제한 배지. `visible` prop 만 받음, caller 가 `hasSynthesisWarning(result, 'ai_synthesis_failed')` 로 파생. 블랙박스 카피 ("가림 구간 정확도가 제한적이에요" / "측면 관절 추정 오차가 포함될 수 있어요.") 만 렌더.
- `app/src/lib/joints.ts` — `reshapePose3dData(flat, jointKeys, frames)` — Firestore flat joints3d → (T, J, 3). 형식 불일치 / J=0 / length mismatch graceful null. `angles` 오입력 시 length guard 가 null 반환.

### Modified
- `app/src/theme/colors.ts` — Phase 4 alias 토큰 6개 추가 (viewer3dBg/Bone/Joint/JointNormal/accuracyLimitBg/Text). 기존 토큰 0 변경.
- `app/src/types/analysis.ts` — `AiSynthesisMeta` audit/cost 9 필드 (modelId/modelVersion/promptHash/framesConsidered/framesSynthesized/geminiCalls/framesSkipped/framesFailed/estCostUsd) 를 optional 로 전환 — backend payload 보다 좁지 않게 + 합성 미수행 분석의 partial emit 허용.
- `app/src/lib/userAnalyses.ts` — normalize() 에 joints3d block (BLOCKER-1 — optional, 형식 불일치 시 undefined) + aiSynthesisMeta block (BLOCKER-3 canonical warnings + HIGH-2 debugWarnings + HIGH-5 audit/cost 보존) 추가.
- `app/src/app/analysis/result.tsx` — `AccuracyLimitBadge`/`PoseViewer3D`/`reshapePose3dData`/`SynthesisWarningCode` import + `hasSynthesisWarning` helper + `joints3d` useMemo + `currentFrame` state. AccuracyLimitBadge 를 헤더 sub 텍스트 아래에, PoseViewer3D 를 VideoCompare 아래에 삽입.

## Decisions Made

- **belle override on blocking checkpoint (Task 2)**: belle 의 EAS 빌드 파이프라인 알려진 이슈로 실기기 smoke 검증을 이번 plan 에서 보류하고 R8 ErrorBoundary + typecheck + grep gate 를 local safety net 으로 사용. 다음 EAS preview 빌드에서 native 검증 재확인 예정. resume-signal "approved OrbitControls:true" 가 이 override 의 결정 박제.
- **drei OrbitControls /native 직접 사용**: `node -e "require('@react-three/drei/native')['OrbitControls']"` → YES 확인. PanResponder fallback 경로는 코드에서 제거 (불필요한 분기 0 박제).
- **HIGH-3 박제 적용**: `referenceJoints` 는 `PoseViewer3D` props 에 예약만 두고, result.tsx 에서 omit. mode1 reference 3D overlay 는 ReferenceMotion 타입 + `referenceMotions.ts` normalize 확장이 필요한 follow-up plan 으로 분리.
- **AnalysisResult.joints3d optional 정합**: `analysis.ts` 의 joints3d 계열 필드가 `nullable` 이 아니라 `optional` 이므로, normalize() 의 형식 불일치 폴백을 `null` 이 아니라 `undefined` 로 둠 (BLOCKER-1).
- **AiSynthesisMeta audit/cost 9 필드 optional 전환**: backend 가 합성 미수행 시 부분 emit 또는 omit 할 수 있음. TS 타입을 좁히면 normalize() 의 `undefined` 대입이 typecheck 실패 → HIGH-5 부합을 위해 9 필드 모두 optional 화.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] AiSynthesisMeta 9 audit/cost 필드 optional 화 (analysis.ts 동시 갱신)**
- **Found during:** Task 3 (userAnalyses normalize wiring)
- **Issue:** 플랜 HIGH-5 는 normalize() 가 audit/cost 필드 타입 검증 실패 시 `undefined` 를 대입하도록 명시하지만, 04-01 에서 `analysis.ts` 의 `AiSynthesisMeta` interface 는 9 필드가 모두 required (non-optional) 로 선언되어 있었음. normalize 의 `undefined` 대입 = typecheck 실패.
- **Fix:** `analysis.ts` 의 `modelId / modelVersion / promptHash / framesConsidered / framesSynthesized / geminiCalls / framesSkipped / framesFailed / estCostUsd` 9 필드를 모두 optional (`?:`) 로 전환. 주석에 HIGH-5 근거 + "backend payload 보다 좁지 않게" 박제.
- **Files modified:** `app/src/types/analysis.ts`
- **Verification:** `npm run typecheck` 0 errors. 04-01 contract.md / Firestore 3-way 계약은 유지 (백엔드는 합성 발생 시 full emit, 미수행 시 omit/partial 모두 허용).
- **Committed in:** `393929d` (Task 3 commit)

**2. [Rule 2 - Missing Critical] `hasSynthesisWarning` helper 신설 (result.tsx)**
- **Found during:** Task 4 (result.tsx 통합)
- **Issue:** BLOCKER-3 박제는 canonical warning surface 가 `aiSynthesisMeta.warnings` 임을 명시하지만, plan 은 helper 의 정의 위치를 명시하지 않음 (`hasSynthesisWarning(result, code)` 만 언급). caller site (result.tsx) 에서 optional chain (`result?.aiSynthesisMeta?.warnings?.includes(...)`) 을 반복 작성하면 MEDIUM-4 (null/undefined guard 단일화) 위반.
- **Fix:** result.tsx 상단 helper 영역 (`lowReliabilityRatio` 뒤) 에 `hasSynthesisWarning(result, code)` 신설. 내부 = `(result?.aiSynthesisMeta?.warnings ?? []).includes(code)`. AccuracyLimitBadge 는 `visible={hasSynthesisWarning(result, 'ai_synthesis_failed')}` 로만 호출.
- **Files modified:** `app/src/app/analysis/result.tsx`
- **Verification:** grep `result.warnings` / `top-level warnings` 사용 0. helper 가 단일 derivation 경로.
- **Committed in:** `a1b055c` (Task 4 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** 두 fix 모두 plan 의 BLOCKER/HIGH/MEDIUM 박제를 강제 위해 필요한 보강 — scope creep 0. analysis.ts optional 전환은 04-01 contract 의 broadcast invariant ("backend 가 보낸 모든 필드 보존") 와 정합.

## Issues Encountered

- **rogue commit on main during Task 3 (수정 완료)**: Task 3 stage + commit 시 `cd /Users/kimtaesung/Dev/SunityMotion` (main 체크아웃 path) 로 잘못 진입해 worktree 가 아닌 main 에 직접 commit 했음. 즉시 발견하고 cherry-pick 으로 worktree 브랜치 (`393929d`) 에 옮긴 뒤 `git reset --hard 03dc3c9` 로 main 을 원상 복귀. 최종 상태: worktree 만 Task 3+4 보유, main 은 `03dc3c9` (Task 1 commit). 이후 모든 명령은 absolute `cd app && ...` 패턴 (worktree-relative) 으로 통일해 재발 방지.
- **node_modules 부재 (worktree fresh state)**: 워크트리에 node_modules 가 없어 첫 typecheck 실패 (`tsc: command not found`). `cd app && npm install` 로 package-lock.json 기반 idempotent 설치. 이후 typecheck 0 errors.
- **블랙박스 grep gate (AccuracyLimitBadge.tsx)**: 첫 작성 시 주석에 금지 단어 (`AI 보완` / `ai_synthesis_failed`) 가 4회 등장 (모두 negation 설명용). plan 의 grep gate 는 file-level 0 을 요구 → 주석 재작성으로 0 으로 줄임. 사용자 노출 카피는 처음부터 LINE_OCCLUSION/LINE_SIDE 두 상수로 격리되어 있었으므로 사용자 surface 영향 0.

## User Setup Required

없음 — 외부 서비스 설정 불필요. 단 다음 EAS preview/development 빌드에서 실기기 smoke (R8 blocking checkpoint 의 원래 의도) 를 재확인 권장: `PoseViewer3DSmokeScreen` 은 main 에 머지되어 있으므로 별도 재배포 없이 next build 에서 확인 가능.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| (none) | — | 본 plan 은 신규 trust boundary 0. `app/src/lib/joints.ts` 의 reshape 는 plan threat_model T-04-W2-01 mitigate 그대로. Three.js GL 컨텍스트는 ErrorBoundary 격리 (T-04-W2-03 mitigate). |

## Next Phase Readiness

- **Wave 3 진입 가능**: PoseViewer3D 마운트 + AccuracyLimitBadge 표시 + joints3d wiring 모두 결과 화면에 박혔음. `reshapePose3dData` 는 향후 reference 3D 비교 (follow-up plan) 가 재사용할 수 있음.
- **EAS native 검증 후속**: 다음 preview 빌드에서 (1) PoseViewer3DSmokeScreen 실기기 회전 (2) result.tsx 통합된 PoseViewer3D 실기기 graceful (3) joints3d 누락 doc 의 graceful skip — 세 가지 sanity check 권장. 본 plan 의 ErrorBoundary 는 마지막 안전망.
- **follow-up plan 후보**: `ReferenceMotion` 타입 + `referenceMotions.ts` normalize 가 `joints3d` 를 흘리기 시작하면 mode1 reference 3D overlay 활성화 가능 (HIGH-3 박제 정합).

## Self-Check: PASSED

다음 산출물 모두 존재 확인 (worktree HEAD = `a1b055c`):

- File `app/src/components/PoseViewer3D.tsx` — FOUND
- File `app/src/components/AccuracyLimitBadge.tsx` — FOUND
- File `app/src/lib/joints.ts` — FOUND
- Commit `393929d` (Task 3) — FOUND
- Commit `a1b055c` (Task 4) — FOUND
- `npm run typecheck` — 0 errors
- `grep "@react-three/fiber/native"` in PoseViewer3D — found
- `grep "reshapePose3dData"` in result.tsx — 4 hits
- `grep "result.angles"` in result.tsx — 0 hits (R3 박제)
- `grep -E "AI 보완|AI가 처리|다각도 분석"` in result.tsx + PoseViewer3D.tsx + AccuracyLimitBadge.tsx — 0 hits (R7 블랙박스)
- `grep "joints3dKeys"` in userAnalyses.ts — 4 hits
- `grep "aiSynthesisMeta"` in userAnalyses.ts — 5 hits
- `grep "ErrorBoundary"` in PoseViewer3D.tsx — found (R8)

---
*Phase: 04-ux-occlusion-confidence*
*Plan: 02*
*Completed: 2026-06-13*
