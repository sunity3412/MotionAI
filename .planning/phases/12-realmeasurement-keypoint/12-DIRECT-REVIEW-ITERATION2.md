---
phase: 12-realmeasurement-keypoint
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review-iteration-2
status: revise-before-execution
reviewed_plans:
  - 12-00-PLAN.md
  - 12-01-PLAN.md
  - 12-02-PLAN.md
  - 12-03-PLAN.md
  - 12-CONTEXT.md
  - 12-UI-SPEC.md
  - 12-VALIDATION.md
  - 12-DIRECT-REVIEW.md
local_code_checked:
  - backend/shared/python/sunity_shared/analysis/pose_frame.py
  - backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py
  - backend/shared/python/sunity_shared/analysis/kismam.py
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - app/src/types/analysis.ts
  - app/src/lib/userAnalyses.ts
  - app/src/app/analysis/result.tsx
---

# Phase 12 Direct Review: Iteration 2

## Executive Verdict

2차 수정본은 1차 리뷰의 큰 방향을 상당히 반영했다. `12-00-PLAN.md`를 새로 추가해 RTMW 2D 좌표, axis polyline, fps required, target source를 Wave 0A로 분리한 점은 맞는 방향이다. `12-01-PLAN.md`도 `KeypointReport`를 9필드로 정리하고, `axisData`, size budget test, Wave 1 gate를 추가했다. `12-02-PLAN.md`는 R7 render prop을 받아들였고, `12-03-PLAN.md`는 R8 AsyncStorage key를 `@sunity:keypoint_overlay_enabled`로 정리했다.

그런데 현재 plan은 **1차 blocker를 고치려다 새로운 실행 blocker를 만들었다.** 가장 큰 문제는 두 가지다.

1. `Keypoint2D(raw_visibility=..., raw_presence=...)`를 전제로 쓰는데, 현재 `Keypoint2D`는 `x/y/visibility`만 가진다.
2. `kismam.assess(..., target_source=...)`를 호출하도록 계획했지만, `kismam.py`, `JointAssessment`, `assemble.build_joints`, `JointScore` contract 변경이 plan에 없다.

여기에 mode1 reference overlay 데이터 계약도 빠져 있다. 지금 구조대로면 정은지 영상 위에 사용자 `keypointReport`를 그릴 위험이 있다.

판정은 여전히 **revise-before-execution**이다. 다만 1차보다 훨씬 가까워졌다. 아래 blocker 4개만 먼저 정리하면 실행 가능한 계획으로 바뀐다.

## Iteration 1 Fix Status

| 1차 항목 | 2차 상태 | 의견 |
|---|---|---|
| R1 RTMW `keypoints_2d=None` | **Partially fixed** | 12-00으로 승격한 건 맞다. 하지만 `Keypoint2D` 필드명을 잘못 잡아 그대로는 실패한다. |
| R2 axis 단일 midpoint | **Mostly fixed** | `axisData` polyline 분리는 좋다. Python field naming과 NaN sentinel은 더 정리 필요. |
| R3 fps default 30 | **Mostly fixed** | `fps: float required`로 고쳤다. timestamp-aware lookup은 아직 없다. |
| R4 mode3 first target semantics | **Partially fixed** | `targetSource` enum을 추가했지만 kismam/JointScore contract가 빠졌다. |
| R5 Firestore size budget | **Fixed enough** | 9fps x 60s <= 700 KiB test가 들어갔다. |
| R6 confidence source | **Regressed** | `visibility` 대신 존재하지 않는 `raw_visibility`를 사용한다. |
| R7 VideoCompare player exposure | **Partially fixed, then regressed** | Wave 1은 render prop인데 Wave 2가 다시 `onPlayersReady`를 제안한다. |
| R8 AsyncStorage key | **Fixed** | `@sunity:keypoint_overlay_enabled`로 정리됐다. |
| R9 sequential gates | **Fixed enough** | Wave 1 gate에 summary/audit/production-like check가 들어갔다. |
| R10 field count | **Fixed** | 9 fields로 정리됐다. |
| R11 5/8/9 표현 혼재 | **Partially fixed** | 주요 plan은 8 body + axisData지만 UI-SPEC/12-03에 구 표현이 남았다. |
| R12 full regression | **Fixed** | full backend pytest gate가 들어갔다. |

## Blockers

### R1. `Keypoint2D.raw_visibility/raw_presence`는 현재 코드에 없다

Severity: **BLOCKER**

2차 plan은 RTMW score를 `Keypoint2D.raw_visibility`로 저장하도록 지시한다.

Evidence:

- `12-00-PLAN.md:76-77`: `Keypoint2D(x, y, raw_visibility=score, raw_presence=None)`
- `12-00-PLAN.md:118-119`: constructor example도 `raw_visibility`, `raw_presence`
- `12-01-PLAN.md:146`, `:231`: confidence source = `Keypoint2D.raw_visibility`
- `12-CONTEXT.md:343`: `Keypoint2D.raw_visibility confidence source`

하지만 실제 code contract는 다르다.

- `backend/shared/python/sunity_shared/analysis/pose_frame.py:135-146`: `Keypoint2D` fields are `x`, `y`, `visibility`
- `app/src/types/analysis.ts:347-355`: TS `Keypoint2D`도 `x`, `y`, `visibility`
- `raw_visibility/raw_presence`는 `Landmark3D` field다. `pose_frame.py:76-88`에 있고, Keypoint2D가 아니다.

Risk:

- RTMW adapter 구현 시 `TypeError: Keypoint2D.__init__() got an unexpected keyword argument 'raw_visibility'`.
- phase12 conftest의 `_make_keypoint_2d(... raw_visibility=...)`도 import 단계에서 실패한다.
- Wave 0B의 `build_keypoint_report()`가 `kp.raw_visibility`를 읽으면 `AttributeError`.

Recommendation:

가장 작은 수정은 `Keypoint2D.visibility`를 canonical confidence source로 쓰는 것이다.

```python
Keypoint2D(
    x=x / image_width,
    y=y / image_height,
    visibility=float(np.clip(score, 0.0, 1.0)),
)
```

그리고 12-00/12-01/CONTEXT의 모든 `raw_visibility/raw_presence` 표현을 `visibility`로 바꾸라. 만약 정말 `raw_visibility/raw_presence`를 Keypoint2D에 추가하고 싶다면, 그건 별도 schema migration이다. `pose_frame.py`, `analysis.ts`, docs, MediaPipe adapter, tests를 전부 같이 고쳐야 하므로 Phase 12에서는 추천하지 않는다.

### R2. `target_source`를 호출하지만 `kismam.assess()` contract 변경이 없다

Severity: **BLOCKER**

12-00은 `kismam.assess(..., target_source='reference_motion')` 같은 호출을 계획한다.

Evidence:

- `12-00-PLAN.md:140-142`: mode별 `target_source` kwarg
- `12-00-PLAN.md:162-187`: 3개 call-site 예시 전부 `target_source=...`
- `12-01-PLAN.md:204`: integration mock도 `target_source=...`

하지만 현재 `kismam.assess()`는 `target_source`를 받지 않는다.

- `backend/shared/python/sunity_shared/analysis/kismam.py:97-102`: signature is `assess(deviation_deg, tolerance=None, user_angles=None, reference_angles=None)`
- `JointAssessment`도 `target_source` 필드가 없다. `kismam.py:82-94`
- `assemble.build_joints()`도 `targetSource`를 내려주지 않는다. `assemble.py:161-172`
- `app/src/types/analysis.ts:91-101`의 `JointScore`에도 `targetSource`가 없다.

Risk:

- pipeline이 즉시 `TypeError: assess() got an unexpected keyword argument 'target_source'`로 실패한다.
- mode3_first는 `reference_angles=None`으로 호출되므로, 기존 assess 로직에서는 `targetAngle`이 전혀 채워지지 않는다.
- UI는 mode3_first에서 “기준 180°”인지 “기준 없음”인지 알 수 없다.

Recommendation:

12-00에 `kismam.py`, `assemble.py`, `app/src/types/analysis.ts`, `docs/contract.md` 변경을 명시적으로 추가하라.

추천 contract:

```python
TargetSource = Literal[
    "reference_motion",
    "previous_analysis",
    "extension_requirement",
    "unavailable",
]

@dataclass(frozen=True)
class JointAssessment:
    ...
    target_source: TargetSource | None = None
```

mode3_first는 `reference_angles=None`이 아니라 extension-required joint만 `{joint: 180.0}`인 dict를 넘기거나, `target_angles_by_joint`를 별도로 만들어 넘겨야 한다. non-extension joint는 `target_angle=None`, `target_source="unavailable"`로 둔다.

### R3. mode1 reference video overlay의 데이터 source가 없다

Severity: **BLOCKER**

Context는 mode1에서 정은지 영상과 사용자 영상 둘 다 오버레이를 요구한다.

Evidence:

- `12-CONTEXT.md:76-78`: mode1 = 정은지 영상 + 사용자 영상 둘 다 오버레이
- `12-UI-SPEC.md:414-418`: mode1 split + 각도 기준 정은지 measured
- `12-UI-SPEC.md:450`, `:456`: `referenceKeypoints`가 없으면 정은지 측 오버레이만 X, reference doc에도 동일 schema 필요

그런데 Wave 0B는 `users/{uid}/analyses/{analysisId}.result.keypointReport` 하나만 만든다.

- `12-01-PLAN.md:165`: 저장 경로는 `result.keypointReport`
- `12-01-PLAN.md:256-263`: `inputs.pose_frames`에서 `build_keypoint_report()`를 호출한다. 이건 사용자 분석 영상의 pose_frames다.
- `12-02-PLAN.md:389-393`: 예시가 reference/user 양쪽 모두 `result.keypointReport`를 넘긴다.

Risk:

- 정은지 영상에 사용자 keypoints가 그려질 수 있다.
- mode1 split UI에서 가장 눈에 띄는 비교 화면이 잘못된 정보를 보여준다.
- `referenceKeypoints` fallback policy는 UI-SPEC에만 있고, Wave 0/1 plan에 저장/조회 구현이 없다.

Recommendation:

둘 중 하나를 명확히 선택하라.

Option A, scope 유지:

- `reference/{motionId}`에 `keypointReport` 또는 `referenceKeypointReport`를 seed한다.
- app `ReferenceMotion` type과 `useReferenceMotion()` normalize에 해당 field를 추가한다.
- result.tsx는 left overlay에 `refMotion?.keypointReport`, right overlay에 `result.keypointReport`를 넘긴다.

Option B, scope 축소:

- mode1 reference overlay는 v2로 미룬다.
- Phase 12 SC 문구와 UI-SPEC을 “사용자 영상 overlay만, reference 영상은 영상만”으로 바꾼다.

나는 Option A를 추천한다. 비교 UI가 Phase 12의 핵심이라 reference overlay를 빼면 사용자 기대가 크게 줄어든다.

### R4. Wave 2가 R7 render prop 결정을 다시 깨뜨린다

Severity: **HIGH**

Wave 1은 R7을 반영해 `VideoCompare` overlay를 render prop으로 설계한다.

Evidence:

- `12-02-PLAN.md:28`: render prop 명시
- `12-02-PLAN.md:354-356`: `leftOverlay?: (player) => ReactNode`
- `12-02-PLAN.md:358-382`: `VideoSlot` 내부에서 `overlay(player)` 호출

그런데 Wave 2는 다시 `onPlayersReady`를 제안한다.

- `12-03-PLAN.md:120-128`: `onPlayersReady?: (left, right) => void`

Risk:

- Wave 1에서 없앤 dual-state player exposure가 Wave 2에서 부활한다.
- `result.tsx`가 player state를 들기 시작하면 render loop/race 가능성이 다시 생긴다.
- Wave 1 설계와 Wave 2 구현 지시가 충돌해 executor가 어느 쪽을 따라야 하는지 불명확하다.

Recommendation:

Wave 2에서 `onPlayersReady` 지시를 삭제하라. `KeypointOverlay`는 Wave 1 render prop으로 받은 player를 그대로 사용하면 된다.

```tsx
leftOverlay={(player) => (
  <KeypointOverlay player={player} keypointReport={referenceKeypointReport} ... />
)}
```

## High-Risk Findings

### R5. delta 강조가 frame-level이 아니라 static mean angle로 흐른다

Severity: **HIGH**

Context는 delta 강조를 현재 frame timestamp 기준으로 정의한다.

Evidence:

- `12-CONTEXT.md:90`: delta 산출 = 비디오 재생 위치 기준 angle
- `12-UI-SPEC.md:288-291`: `videoCurrentTime -> frame index -> keypoints[index]`

하지만 Wave 2 implementation은 `jointAngles?: Record<string, { current, target }>`만 받는다.

- `12-03-PLAN.md:133-140`: `jointAngles` prop
- `12-03-PLAN.md:165-188`: `jointAngles`에서 highlighted set 산출
- result의 `JointScore.currentAngle/targetAngle`은 평균/대표 각도다.

Risk:

- 영상이 재생되어도 강조 joint와 floating label은 전체 영상 내내 같은 값으로 보인다.
- 사용자는 특정 frame의 자세 문제로 이해하지만 실제로는 평균 편차를 보고 있는 셈이다.
- `analysisDoc.angles` flat frame-level data가 이미 있는데도 sync에 쓰지 못한다.

Recommendation:

둘 중 하나를 선택해 문서화하라.

Option A, 진짜 frame-level:

- `KeypointOverlay`에 `angles`, `anglesJointKeys`, `targetAnglesByFrame` 또는 aligned reference frame map을 넘긴다.
- `frameIndex` 기준으로 current angle을 lookup한다.
- mode1/reference는 DTW path alignment까지 필요하다.

Option B, MVP static highlight:

- delta 강조는 “영상 전체 대표 편차”라고 명시한다.
- floating label도 “대표 N°”로 바꾸거나 영상 위 label은 Wave 2에서 제외한다.

나는 Option B를 먼저 추천한다. DTW-aligned frame-level angle까지 한 번에 넣으면 Phase 12가 너무 커진다.

### R6. Python dataclass field를 `axisData`로 두면 local naming pattern과 어긋난다

Severity: **MEDIUM-HIGH**

`12-01-PLAN.md:218`은 Python `KeypointReport` field를 `axisData`로 둔다. 그런데 이 codebase는 Python dataclass는 snake_case, Firestore/TS는 camelCase로 변환하는 패턴이다.

Evidence:

- Phase 9도 Python `overall_confidence` → Firestore `overallConfidence` 패턴이다.
- `12-01-PLAN.md:200-201`은 `_dataclass_to_camel_case_dict()` lockstep test를 계획한다.

Risk:

- Python field만 camelCase가 되어 local style과 drift가 생긴다.
- `_dataclass_to_camel_case_dict()` test의 의미가 약해진다.
- future Python code에서 `report.axis_data`가 아니라 `report.axisData`를 써야 해서 실수 가능성이 커진다.

Recommendation:

Python dataclass field는 `axis_data`로 두고, TS/Firestore/docs는 `axisData`로 두라.

```python
axis_data: list[float]
```

validator whitelist와 app contract는 `axisData`를 유지하면 된다.

### R7. `NaN` sentinel은 Firestore/App 경계에서 불필요하게 위험하다

Severity: **MEDIUM-HIGH**

`axisData`에서 `knee_mid`가 없으면 `(NaN, NaN)`을 넣는 계획이다.

Evidence:

- `12-01-PLAN.md:148`, `:156`, `:233`, `:244`, `:296`

Risk:

- Firestore Admin은 NaN을 받을 수 있더라도, JSON serialization, logs, tests, app memoization에서 edge case가 생긴다.
- RN/SVG가 NaN coordinate를 받으면 render warning 또는 blank line이 날 수 있다.
- validator가 `list[number]`만 본다고 NaN safety가 보장되지는 않는다.

Recommendation:

finite sentinel + validity mask를 추천한다.

```ts
axisData: number[];      // finite only
axisMask: boolean[];     // T x 3, point exists
```

MVP로 field를 줄이고 싶다면 `knee_mid`가 없을 때 shoulder/hip 2-point만 렌더하도록 `axisPointCount: number[]`를 둬도 된다.

### R8. UI-SPEC이 아직 구형 `KeypointFrame[]` props를 유지한다

Severity: **MEDIUM**

Plans는 `KeypointReport` 중심으로 정리됐는데 UI-SPEC §5는 아직 구형 props를 쓴다.

Evidence:

- `12-UI-SPEC.md:246-253`: `keypoints: KeypointFrame[]`, `referenceKeypoints?: KeypointFrame[]`
- `12-01-PLAN.md:140-149`: 실제 contract는 `KeypointReport` 9필드
- `12-02-PLAN.md:155-162`: `KeypointOverlayProps.keypointReport`

Risk:

- 구현자가 UI-SPEC을 따르면 `KeypointFrame[]` component를 만들고, Wave plan을 따르면 `KeypointReport` component를 만든다.
- docs/contract와 UI-SPEC이 다른 model을 설명한다.

Recommendation:

UI-SPEC §5 props를 `KeypointReport` 기반으로 갱신하라. `referenceKeypointReport?: KeypointReport | null`까지 포함해야 mode1 reference overlay가 해결된다.

### R9. 12-02의 `KeypointOverlay` usage sample이 T1 props와 맞지 않는다

Severity: **MEDIUM**

Wave 1 T1 props에는 `player`, `mode`, `side`가 없다. 그런데 T4 usage sample은 넘긴다.

Evidence:

- `12-02-PLAN.md:153-162`: props = `keypointReport`, `videoSize`, `frameIndex`, `visible`, `jointAngles`
- `12-02-PLAN.md:389-393`: `<KeypointOverlay player={player} ... mode={analysisDoc.mode} side="reference" />`
- `12-02-PLAN.md:448`: Wave 1에서 player prop 금지

Risk:

- Wave 1 typecheck가 실패한다.
- executor가 Wave 2 props를 Wave 1에 앞당겨 섞을 수 있다.

Recommendation:

Wave 1 sample에서 `player`, `mode`, `side`를 제거하라. Wave 2에서 props를 확장할 때 한 번에 추가하면 된다.

### R10. `VideoCompare` polling policy가 Wave 1/2에서 충돌한다

Severity: **MEDIUM**

Evidence:

- `12-02-PLAN.md:383`: 기존 250ms polling 제거, Wave 2가 `useEvent`로 통합
- `12-03-PLAN.md:119`: 기존 250ms polling 유지

Risk:

- Wave 1에서 제거했는데 Wave 2가 유지 전제로 구현하거나, 반대로 Wave 2에서 중복 state source가 생긴다.

Recommendation:

MVP에서는 polling을 유지하라. Timeline은 기존 250ms polling, overlay만 `useEvent`로 간다. `12-02-PLAN.md:383`의 “제거” 문장을 삭제하는 게 맞다.

## Medium / Low Findings

### R11. 12-00 test/function names do not match current adapter

Severity: **MEDIUM**

Evidence:

- Plan uses `_build_pose_frame()` and `_RTMW_TO_COCO17_INDEX`.
- Actual adapter has `convert_rtmw_keypoints_to_coco17_and_pole_ext()` and `RTMW_133_TO_COCO17`.

Recommendation:

Tests should call the actual public conversion function unless you intentionally introduce a new private helper. Helper name은 `_build_keypoints_2d_from_rtmw()` 정도만 추가하면 충분하다.

### R12. Validation map has not fully split Wave 0A / 0B

Severity: **LOW-MEDIUM**

`12-VALIDATION.md` now mentions 0A/0B in SC and decision coverage, but Source Requirements table still says Wave `0` for all backend items and does not directly list RTMW 2D population / targetSource enum / axisData tests.

Recommendation:

Add explicit rows for:

- RTMW `keypoints_2d` populated
- `TargetSource` enum and invalid reject
- `axisData` polyline
- reference keypoint report availability if mode1 overlay remains in scope

### R13. Old wording remains: 9 keypoint / 5 joint / KeypointFrame

Severity: **LOW**

Examples:

- `12-03-PLAN.md:9`, `:23`, `:403`, `:438`: 9 keypoint
- `12-CONTEXT.md:16-17`, `:313`: 5 joint wording
- `12-CONTEXT.md:136`, `:242`, `:248`: KeypointFrame
- `12-UI-SPEC.md:565`: 60s x 30fps x 9 keypoint old size formula

Recommendation:

Use one glossary:

- storage: `8 body keypoints + axisData`
- display: `5 groups = shoulder/hip/knee/hand/axis`
- schema: `KeypointReport`, not `KeypointFrame`

### R14. UI-SPEC still contains an emoji in modal mock

Severity: **LOW**

`12-UI-SPEC.md:337` contains `💬`, while `12-02-PLAN.md` correctly says no emoji. The plan is safer than the spec, but the spec should not contradict execution rules.

Recommendation:

Remove the emoji from UI-SPEC or mark it explicitly as visual mock not implementation.

## My Recommended Patch Order

1. Patch 12-00 first:
   - Replace all `raw_visibility/raw_presence` Keypoint2D usage with `visibility`.
   - Add actual `kismam.py` / `JointAssessment` / `assemble.py` / `JointScore` targetSource contract, or remove `target_source` from calls and use a separate `reference_angles` dict for extension targets.
   - Fix adapter/test function names to match `convert_rtmw_keypoints_to_coco17_and_pole_ext`.

2. Patch 12-01:
   - Rename Python `axisData` field to `axis_data`.
   - Replace NaN sentinel with `axisMask` or another finite representation.
   - Add `referenceKeypointReport` contract if mode1 reference overlay remains in scope.

3. Patch 12-02:
   - Keep render prop.
   - Fix KeypointOverlay sample props.
   - Do not remove VideoCompare polling in Wave 1.

4. Patch 12-03:
   - Delete `onPlayersReady`.
   - Remove `axis: null` from `Record<KeypointName, ...>` since `axis` is no longer a `KeypointName`.
   - Decide whether delta highlight is representative-angle MVP or true frame-level.

5. Patch UI-SPEC / VALIDATION:
   - Convert all props to `KeypointReport`.
   - Add reference keypoint report row.
   - Split validation rows into Wave 0A and 0B.

## Recommended Technologies

- Backend confidence: use existing `Keypoint2D.visibility`.
- Backend report: Python `@dataclass(frozen=True)` with snake_case fields, camelCase only at Firestore/TS boundary.
- Axis missing data: finite mask (`axisMask`) rather than NaN coordinates.
- Mode1 reference overlay: `reference/{motionId}.keypointReport` plus `ReferenceMotion.keypointReport?` in app.
- Video sync: keep existing timeline polling; use `useEvent` only inside overlay for frame updates.
- Delta MVP: start with representative-angle highlight, label it honestly. Move DTW frame-level delta to follow-up if needed.

## Final Recommendation

Do not execute yet. The 4-wave structure is now the right shape, but 12-00/12-01 need a focused contract patch before implementation. If the next revision fixes `Keypoint2D.visibility`, `targetSource` end-to-end, mode1 reference keypoints, and keeps render prop through Wave 2, I would expect the next review to move from `revise-before-execution` to `ready-with-minor-notes`.
