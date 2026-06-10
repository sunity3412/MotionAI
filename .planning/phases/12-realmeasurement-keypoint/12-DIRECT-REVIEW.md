---
phase: 12-realmeasurement-keypoint
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review
status: revise-before-execution
reviewed_plans:
  - 12-CONTEXT.md
  - 12-UI-SPEC.md
  - 12-RESEARCH.md
  - 12-VALIDATION.md
  - 12-01-PLAN.md
  - 12-02-PLAN.md
  - 12-03-PLAN.md
local_code_checked:
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/kismam.py
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - backend/shared/python/sunity_shared/analysis/pose_frame.py
  - backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py
  - app/src/app/analysis/result.tsx
  - app/src/components/VideoCompare.tsx
  - app/src/types/analysis.ts
  - app/package.json
---

# Phase 12 Direct Review

## Executive Verdict

Phase 12의 방향은 맞다. 특히 `currentAngle/targetAngle`이 production에서 비는 원인을 backend call-site wiring으로 잡은 것은 정확하다. 현재 `kismam.assess()`는 이미 `user_angles`/`reference_angles`를 받을 수 있고, `JointAssessment`와 `assemble.build_joints()`도 그 값을 result contract로 내릴 준비가 되어 있다. 그런데 pipeline의 3개 호출부는 모두 kwargs 없이 `kismam.assess(...)`를 호출한다. 이건 Phase 12 Wave 0이 반드시 해결해야 하는 실제 결함이다.

다만 현재 plan 그대로 실행하면 **오버레이 쪽은 높은 확률로 사용자에게 보이는 기능이 안 나온다.** 핵심 이유는 RTMW 운영 path가 `PoseFrame.keypoints_2d=None`을 반환하고 있기 때문이다. `12-01-PLAN.md`가 audit task를 넣어둔 점은 좋지만, 로컬 코드 기준으로는 이 audit 결과가 사실상 BLOCKED에 가깝다. Wave 1/2 UI를 만들기 전에 2D keypoint 산출 경로를 구현하거나, 명시적으로 fallback-only phase로 스코프를 낮춰야 한다.

내 판정은 **revise-before-execution**이다. 고쳐야 할 큰 축은 4개다.

1. RTMW `keypoints_2d` 부재를 audit 문서가 아니라 구현 선행 task로 승격.
2. `axis`를 단일 midpoint가 아니라 선/폴리라인 계약으로 재정의.
3. `fps`/frame index/storage budget을 실제 9fps extraction 기준으로 고정하고 default 30을 제거.
4. mode3 첫 분석의 `targetAngle` 의미를 reference mean angle과 분리.

저라면 12-01을 바로 실행하지 않고, **12-00 data-contract patch**를 먼저 만든 뒤 Wave 0으로 들어간다.

## What Looks Strong

- `kismam.assess()` wiring 결함을 정확히 짚었다. 현재 `pipeline/app.py:768`, `:772`, `:940`은 모두 kwargs 없이 호출되고, `result.tsx:94-119`는 이 결함을 reference fallback으로 가리고 있다.
- schema lockstep을 `analysis.ts` / Python dataclass / docs / Firestore validator로 묶으려는 방향은 Phase 9 패턴과 맞다.
- `expo`, `expo-video`, `react-native-svg`, `AsyncStorage`는 모두 현재 app dependency에 이미 있다. 신규 package 없이 구현 가능한 점은 좋다.
- `useEvent`는 현재 설치된 `expo` 타입에서 실제 export된다. `import { useEvent } from 'expo'` 자체는 로컬 SDK 기준으로 유효하다.
- `VideoCompare`에 overlay slot을 추가하는 접근은 현재 구조와 잘 맞는다. 기존 비교 재생 UX를 크게 흔들지 않고 오버레이를 끼울 수 있다.

## Blockers

### R1. RTMW 운영 path가 `keypoints_2d`를 채우지 않는다

Severity: **BLOCKER**

Phase 12의 visible feature는 비디오 위 keypoint overlay다. 그런데 현재 RTMW adapter는 `PoseFrame.keypoints_2d`를 명시적으로 `None`으로 반환한다.

Evidence:

- `backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py:226`:
  - `keypoints_2d=None`
  - comment: `RTMW 2D path: plan 22 (3D path) 에서 추가 예정`
- `12-01-PLAN.md:218-220`은 `pose_frames[0].keypoints_2d is None`이면 `build_keypoint_report()`가 `None`을 반환한다고 한다.
- `12-01-PLAN.md:342-372`에 audit gate가 있지만, 현재 코드 기준으로는 PASS보다 BLOCKED 가능성이 높다.

Risk:

- Wave 0 schema와 Firestore field는 생겨도 `result.keypointReport`가 계속 `null`/missing이 된다.
- Wave 1/2의 KeypointOverlay는 placeholder만 보이거나 아무것도 그리지 않는다.
- Phase 12 success criteria의 “영상 위 어깨/골반/무릎/손 + 중심축 오버레이”가 충족되지 않는다.

Recommendation:

Audit task를 유지하되, 그 결과가 현재 코드처럼 BLOCKED면 바로 실행할 구현 task를 plan에 포함해야 한다.

내가 한다면 우선순위는 이렇다.

1. RTMW raw 133 keypoints에서 COCO-17 2D x/y/score를 보존해 `Keypoint2D(x, y, visibility)`로 채운다.
2. 좌표계를 normalized 0..1로 고정한다. `Keypoint2D` docstring도 이미 normalized 0..1이라고 되어 있다.
3. `build_keypoint_report()`는 `Keypoint2D.visibility`를 `confidence` flat array로 매핑한다.
4. 이 구현이 불가능하면 Phase 12 overlay scope를 “keypoint unavailable placeholder까지”로 낮추고, 실제 overlay는 별도 phase로 분리한다.

### R2. `axis`를 단일 point로 표현하면 Context와 UI-SPEC을 만족하지 못한다

Severity: **BLOCKER-HIGH**

Context는 중심축을 선으로 정의한다.

Evidence:

- `12-CONTEXT.md:82`: 중심축 = 어깨 중심 ↔ 골반 중심 ↔ 무릎 중심 선
- `12-UI-SPEC.md:260`: `axis` = 어깨중심 ↔ 골반중심
- `12-01-PLAN.md:155`, `:220`: `axis` = `midpoint(left_shoulder, right_shoulder)`

현재 plan의 `axis`는 어깨 midpoint 한 점이다. 이 값 하나로는 어깨 중심에서 골반 중심으로 내려가는 축선도, 무릎 중심까지 이어지는 body axis도 그릴 수 없다.

Risk:

- UI가 “중심축”을 그린다고 하지만 실제로는 어깨 중앙 점 하나만 가진다.
- Wave 2에서 delta 강조나 floating label을 붙일 때 `axis`의 의미가 모호해진다.
- 나중에 hip/knee 중심축을 추가하려면 schema migration이 다시 필요하다.

Recommendation:

`axis`를 keypoint list에 억지로 넣지 말고 별도 contract로 분리한다.

추천 schema:

```ts
export type KeypointName =
  | 'left_shoulder' | 'right_shoulder'
  | 'left_hip' | 'right_hip'
  | 'left_knee' | 'right_knee'
  | 'left_hand' | 'right_hand';

export interface AxisFrame {
  shoulderMid: [number, number];
  hipMid: [number, number];
  kneeMid?: [number, number];
}
```

Firestore flat 저장을 유지하려면 `axisData = T x 2 or 3 points x 2` flat array로 두면 된다. UI는 keypoints와 axis polyline을 별도로 그린다.

### R3. `fps=30` default는 overlay frame sync를 망가뜨릴 수 있다

Severity: **HIGH**

Plan은 `build_keypoint_report(pose_frames, fps: int = 30)`를 제안한다. 동시에 pipeline의 force signal path는 `fps=9.0`을 사용하고 있고, research도 frame extraction target fps가 9fps라고 말한다.

Evidence:

- `12-01-PLAN.md:143`: `fps: int (> 0, default 30)`
- `12-01-PLAN.md:218`: `build_keypoint_report(pose_frames: list, fps: int = 30)`
- `12-01-PLAN.md:279`: 현재 9fps 또는 default 30 + warning
- `backend/functions/pipeline/app.py:1119-1125`: `compute_force_signals(... fps=9.0)`
- `12-03-PLAN.md:158`: `frameIndex = Math.floor(currentTime * keypointReport.fps)`

Risk:

- call site에서 fps 전달을 한 번만 놓쳐도 overlay가 약 3.3배 빠르게 진행된다.
- `warnings.append("fps_inferred_default_30")`는 사용자에게 보이는 sync 오류를 막지 못한다.
- Firestore size budget도 30fps 기준과 9fps 기준이 섞여 판단된다.

Recommendation:

`fps` default 30을 제거하고, `fps`를 필수 인자로 만들라.

추천 구현:

```python
def build_keypoint_report(pose_frames: list[PoseFrame], *, fps: float) -> KeypointReport | None:
    if fps <= 0:
        raise ValueError("fps must be positive")
```

그리고 가능하면 frame index는 `fps`만 믿지 말고 `timestamp_ms` 기반 fallback도 저장한다. 최소한 `frameTimestampsMs: list[int]` 또는 flat `timestampsMs`를 넣으면 seek 이후 drift를 줄일 수 있다.

### R4. mode3 첫 분석의 `targetAngle`은 reference mean angle이 아니다

Severity: **HIGH**

mode1과 mode3 progress는 기준 시퀀스가 있다. `per_joint_deviation()` 이후 user/reference aligned segment 평균을 넣으면 `현재 N° → 기준 M°`가 자연스럽다.

하지만 mode3 첫 분석은 다르다. `_mode3_comparison()` 첫 분석 path는 `dimensions.extension_deviation(angles, profile)`을 사용한다. 이 값은 “이전 영상/정은지 대비 편차”가 아니라 `profile.expects_extension(k)`인 관절의 `180° - representative_angle`이다.

Evidence:

- `backend/functions/pipeline/app.py:768`: mode3 first uses `dimensions.extension_deviation(angles, profile)`
- `backend/shared/python/sunity_shared/analysis/dimensions.py:126-136`: extension deviation is 180° 부족분 for extension-required joints
- `kismam.assess()`는 `reference_angles`가 있어야 `target_angle`을 채운다.

Risk:

- mode3 첫 분석에서 targetAngle을 억지로 reference mean model에 맞추면 “기준 M°”의 의미가 불명확해진다.
- extension 대상이 아닌 관절은 deviation 0인데 targetAngle을 무엇으로 보여줄지 애매하다.
- 사용자는 `기준 180°`가 심판 기준인지, 정은지 기준인지, 이전 영상 기준인지 구분하지 못한다.

Recommendation:

Angle guide source를 명시적으로 분리하라.

추천 contract:

```ts
type AngleTargetSource =
  | 'reference_motion'
  | 'previous_analysis'
  | 'extension_requirement'
  | 'unavailable';
```

mode3 first에서는 extension-required joints만 `targetAngle=180`, `targetSource='extension_requirement'`로 채운다. extension 대상이 아닌 관절은 `targetAngle`을 비우거나 UI에서 “기준 없음”으로 숨긴다.

## High-Risk Findings

### R5. Firestore 1 MiB 계산이 raw float32 기준이라 안전 마진을 과대평가한다

Severity: **MEDIUM-HIGH**

Research는 `60s x 30fps x 9 x 2 x 4 byte = 0.124 MiB`로 flat Firestore 저장이 안전하다고 본다. 하지만 Firestore는 JSON/float32 raw buffer가 아니다. 숫자는 double로 저장되고, document field overhead와 기존 result/angles/force reports도 같은 1 MiB 문서 한도 안에 들어간다. `confidence` flat array와 `reliability` 문자열 array도 추가된다.

Risk:

- 9fps 짧은 영상은 괜찮을 가능성이 높다.
- 30fps 60s 또는 분석 metadata가 커진 문서는 1 MiB에 가까워질 수 있다.
- 한 번 한도에 닿으면 analysis completion write가 실패한다.

Recommendation:

Wave 0에 serialized size test를 넣어라.

내 기준:

- 9fps sampled report를 primary로 고정.
- 60s synthetic worst-case document를 만들어 Firestore Admin payload size를 추정.
- doc 전체가 700 KiB를 넘으면 Cloud Storage JSON 또는 gzip blob + Firestore pointer로 전환.
- `frames` cap을 둔다. 예: `maxFrames=900` 또는 extraction fps 기준 100s cap.

### R6. Keypoint confidence source가 `visibility`인지 명확하지 않다

Severity: **MEDIUM**

현재 `Keypoint2D`는 `confidence` 필드가 아니라 `visibility` 필드를 가진다.

Evidence:

- `backend/shared/python/sunity_shared/analysis/pose_frame.py:136-147`: `Keypoint2D(x, y, visibility)`
- `12-01-PLAN.md:223`: `confidence=flat (T x 9)`만 말하고 source mapping은 명확하지 않다.

Risk:

- 구현자가 confidence를 1.0으로 채우거나 0.0 fallback을 남발할 수 있다.
- Wave 2의 “추정 N°”, occlusion badge, confidence bar가 실제 pose confidence와 분리된다.

Recommendation:

`confidence[t, j] = clamp(keypoints_2d[name].visibility, 0, 1)`를 plan에 명시하라. RTMW raw score를 쓰는 경우에도 최종 `Keypoint2D.visibility`로 normalize해서 통일하는 게 낫다.

### R7. `VideoCompare` player 노출 방식은 render prop이 더 안전하다

Severity: **MEDIUM**

Wave 1은 overlay slot을 추가하고, Wave 2는 `onPlayersReady?: (left, right) => void` 또는 ref prop으로 player를 caller에 노출하려 한다.

Risk:

- `onPlayersReady`가 render마다 새 함수면 `result.tsx` state update loop를 만들 수 있다.
- `VideoCompare` 내부 player lifecycle과 overlay lifecycle이 분리되어 null state race가 생긴다.
- overlay는 `VideoSlot` 위에 absolute layer로 있어야 하므로 player도 같은 slot scope에서 넘기는 게 자연스럽다.

Recommendation:

slot을 `ReactNode`가 아니라 render prop으로 설계하라.

```ts
leftOverlay?: (player: VideoPlayer | null) => React.ReactNode;
rightOverlay?: (player: VideoPlayer | null) => React.ReactNode;
```

그러면 `KeypointOverlay`가 같은 `VideoSlot` 안에서 player를 받아 `useEvent`를 구독하고, `result.tsx`는 player 상태를 따로 들고 있을 필요가 없다.

### R8. AsyncStorage key가 문서마다 다르다

Severity: **MEDIUM**

Evidence:

- `12-UI-SPEC.md:379`: `force_pattern_overlay_enabled`
- `12-03-PLAN.md:28`, `:236`, `:254`, `:260`: `@sunity:overlay_enabled`
- `12-03-PLAN.md:41` frontmatter target contains `force_pattern_overlay_enabled`

Risk:

- 구현과 QA가 서로 다른 key를 확인한다.
- 기존 사용자가 toggle preference를 잃거나, migration 없이 key가 바뀐다.

Recommendation:

하나로 고정하라. 나는 `@sunity:keypoint_overlay_enabled`를 추천한다. Phase 9 force pattern card가 아니라 keypoint overlay 토글이므로 이름도 그렇게 좁히는 게 맞다.

### R9. summary artifact references는 sequential gate로 명시해야 한다

Severity: **MEDIUM**

`12-02-PLAN.md`와 `12-03-PLAN.md`는 아직 생성되지 않은 summary/audit files를 context로 참조한다.

Evidence:

- `12-02-PLAN.md:107-108`: `12-01-SUMMARY.md`, `12-WAVE0-AUDIT.md`
- `12-03-PLAN.md:88-89`: `12-01-SUMMARY.md`, `12-02-SUMMARY.md`

이 자체가 문제는 아니다. sequential execution이면 정상이다. 다만 현재 plan에는 “이 파일들이 없으면 다음 wave를 시작하지 않는다”는 실행 gate가 더 선명해야 한다.

Recommendation:

Wave 1 시작 gate:

- `12-01-SUMMARY.md` exists
- `12-WAVE0-AUDIT.md` has `STATUS: PASS`
- 실제 production-like analysis 1건에서 `result.keypointReport.frames > 0`

Wave 2 시작 gate:

- `12-02-SUMMARY.md` exists
- Wave 1 UAT approved
- `KeypointOverlay` static frameIndex path가 실제 coordinates를 렌더

## Medium / Low Findings

### R10. KeypointReport field count가 7과 8로 섞여 있다

Severity: **LOW-MEDIUM**

Evidence:

- `12-01-PLAN.md:139`: “필드 7개”
- `12-01-PLAN.md:209`: `version, joints, frames, fps, data, confidence, reliability, warnings` = 8 fields
- `12-01-PLAN.md:286`: “7 필드 + warnings”

Risk:

- docs lockstep test가 잘못 작성된다.
- Firestore validator whitelist와 TS interface가 어긋난다.

Recommendation:

8 fields로 정리하라. `warnings`도 contract field다.

### R11. UI-SPEC의 “5 joints” 표현과 실제 9 keypoint 설계가 섞여 있다

Severity: **LOW**

`12-UI-SPEC.md:454`는 “5 joint x N frame x 2 axis”라고 쓰지만, plan은 8 body keypoints + axis를 다룬다. 용어가 섞이면 normalize/reshape 테스트가 헷갈린다.

Recommendation:

문서 표현을 `8 body keypoints + axis polyline` 또는 `J keypoints`로 통일하라.

### R12. Validation은 root 기준 pytest가 가능하지만 full backend test gate도 유지해야 한다

Severity: **LOW**

`backend/tests/conftest.py`가 shared python path를 주입하므로 `pytest backend/tests/phase12/`는 루트 기준으로도 동작할 가능성이 높다. 이건 문제로 보지 않는다.

다만 Phase 12는 pipeline, Firestore validator, TS contract, app normalize를 모두 건드린다. phase12-only test만으로는 부족하다.

Recommendation:

Wave 0 close-out에는 plan에 있는 것처럼 `phase06/07/08/08.1/09` regression을 포함하고, 마지막에는 `pytest backend/tests/ -x -q` full suite를 한 번 돌리는 게 맞다.

## My Recommended Execution Strategy

저라면 이렇게 진행한다.

### 0. Data Contract Patch First

12-01 전에 짧은 plan patch를 만든다.

- RTMW 2D coordinate source를 확정한다.
- axis를 단일 keypoint에서 `axisData` polyline으로 분리한다.
- `fps`를 required float로 바꾸고 default 30을 제거한다.
- `timestampMs` 저장 여부를 결정한다.
- `targetSource`를 angle guide contract에 추가한다.

이 patch 없이 UI부터 만들면 “예쁜 placeholder”는 만들 수 있지만 Phase 12의 핵심 value는 검증되지 않는다.

### 1. Wave 0A: RTMW keypoints_2d 구현과 실측 angle wiring

먼저 backend 데이터가 실제로 내려오는지 끝낸다.

- RTMW adapter에서 `Keypoint2D`를 채운다.
- `kismam.assess()` 3 call site에 user/reference/extension target angles를 넣는다.
- mode3 first target semantics를 분리한다.
- `build_keypoint_report()`는 `fps` required, `visibility -> confidence`, `axisData` 포함으로 구현한다.
- production-like mock pipeline test에서 `keypointReport.frames > 0`을 확인한다.

### 2. Wave 0B: Firestore / TS / normalize lockstep

데이터가 생긴 뒤 schema lockstep을 한다.

- Python dataclass
- Firestore scoped validator
- `docs/contract.md`
- `app/src/types/analysis.ts`
- `userAnalyses.ts::normalize`
- size budget test

여기까지가 끝나야 UI wave가 의미가 있다.

### 3. Wave 1: Static UI

정적 `frameIndex=0`만 렌더한다.

- `VideoCompare` render-prop overlay slot
- `KeypointOverlay` static render
- `ForcePatternCard`
- `ForcePatternDetailModal`
- result screen 6 영역 재배치

이 wave의 목표는 sync가 아니라 “실제 좌표가 영상 위에 맞게 놓이는지”다.

### 4. Wave 2: Sync, Delta, Confidence

그 다음에만 `useEvent` sync를 붙인다.

- `player.timeUpdateEventInterval = 0.033`
- `useEvent(player, 'timeUpdate', ...)`
- `frameIndex = timestamp-aware lookup`
- delta >= 10° highlight
- confidence/occlusion UI
- AsyncStorage toggle
- iOS device UAT

## Recommended Technologies

### Backend

- Python frozen dataclasses for `KeypointReport`.
- `Keypoint2D.visibility` as the canonical confidence source.
- Firestore flat arrays for 9fps sampled data only.
- Cloud Storage JSON/gzip pointer if worst-case document size exceeds safe budget.
- Explicit `targetSource` enum for angle guide semantics.
- pytest contract tests plus pipeline integration tests.

### Frontend

- `expo-video` `useVideoPlayer` remains the player primitive.
- `useEvent` from `expo` for video time updates, verified in local SDK 54.
- `react-native-svg` for 8 keypoints + axis polyline. No Skia unless iOS UAT shows jank.
- `VideoCompare` render-prop overlay slot instead of global player callback.
- `AsyncStorage` with a single namespaced key: `@sunity:keypoint_overlay_enabled`.
- `useMemo` for frame lookup and shape conversion. Avoid recomputing flat array slices on every render without memoization.

### Verification

- Backend: `pytest backend/tests/phase12/ -x -q`, then affected regression suites, then full backend suite once.
- App: `npm run typecheck`.
- Native UAT: iOS real device or TestFlight. Browser/Playwright is not enough for `expo-video` native timing.
- Manual checks: seek, pause, resume, short video end, missing keypointReport, low confidence frames, mode1 split, mode3 single.

## Final Recommendation

Do not execute Phase 12 as-is. The plan is close in shape, but it assumes a 2D keypoint stream that the current RTMW path does not provide. Fix the data contract first, especially RTMW `keypoints_2d`, axis polyline, required fps, and mode3 first target semantics. After that, the frontend plan becomes much lower risk and can be executed in the proposed wave structure.
