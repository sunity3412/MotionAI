---
phase: 12-realmeasurement-keypoint
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review-iteration-5
status: revise-small-before-execution
reviewed_plans:
  - 12-00-PLAN.md
  - 12-01-PLAN.md
  - 12-02-PLAN.md
  - 12-03-PLAN.md
  - 12-CONTEXT.md
  - 12-UI-SPEC.md
  - 12-VALIDATION.md
  - 12-PLAN-CHECK-ITER7.md
  - 12-PLAN-CHECK-ITER8.md
  - 12-DIRECT-REVIEW-ITERATION4.md
local_code_checked:
  - backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py
  - backend/shared/python/sunity_shared/models.py
  - app/scripts/seed-reference-motions.mjs
  - app/src/lib/referenceMotions.ts
  - app/src/types/analysis.ts
external_primary_docs_checked:
  - https://docs.expo.dev/versions/v54.0.0/sdk/video/
---

# Phase 12 Direct Review: Iteration 5

## Executive Verdict

5차 수정본은 4차 blocker 대부분을 제대로 닫았다. `12-PLAN-CHECK-ITER8.md`의 PASS 판정은 큰 방향에서는 맞다.

Closed:

- B1: RTMW helper가 `keypoints_133 + scores_133` 분리 signature로 고쳐졌다.
- B2: `referenceKeypointReport` 필드명으로 통일됐다.
- B3: `KeypointOverlayProps`가 Wave 1/2/UI-SPEC에서 단일 contract로 잠겼다.
- H1: kismam grep gate가 AST pytest gate로 바뀌었다.
- H2: `referenceKeypointReport` analysis result mirror를 폐기했고, reference doc 직접 read로 정리됐다.
- H3: `data`/`confidence` finite/range validator가 추가됐다.
- H4: first-frame missing이면 전체 report drop하던 조건이 `any(frame.keypoints_2d)` 기준으로 고쳐졌다.

다만 나는 아직 **완전 PASS는 주지 않는다.** 이유는 `12-01-PLAN.md`의 reference seed task 한 줄이 실제 Firestore collection과 다른 `reference_motions/{motionId}`를 지시하기 때문이다. 기존 앱과 backend contract는 `reference/{motionId}` 단일 컬렉션이다. 이건 1-line fix지만, 실행자가 그대로 따르면 mode1 reference overlay가 데이터를 못 읽는다.

판정: **revise-small-before-execution**. 아래 H1만 고치면 execution-ready로 봐도 된다.

## Closure Verification

| Prior finding | 5차 상태 | 확인 |
|---|---|---|
| B1 RTMW helper signature | **Closed** | `12-00-PLAN.md:104-128`가 `keypoints_133`, `scores_133`를 분리하고 `kp[2]`를 z로 명시 |
| B2 reference field name | **Closed** | `refMotion?.keypointReport` active plan hit 0, `referenceKeypointReport`로 통일 |
| B3 KeypointOverlay props | **Closed** | `12-02`, `12-03`, `12-UI-SPEC` props block이 같은 형태 |
| H1 grep gate | **Mostly closed** | verify gate는 AST pytest로 변경. 단 threat table 표현 하나는 warning |
| H2 double-report size | **Closed** | analysis result mirror 폐기, reference doc 직접 read |
| H3 finite/range | **Closed** | dataclass + Firestore validator에 data finite, confidence range 추가 |
| H4 first frame drop | **Closed** | `any(frame.keypoints_2d for frame in pose_frames)` 조건으로 변경 |

## High Finding

### H1. reference seed write path가 실제 collection과 다르다

Severity: **HIGH**

`referenceKeypointReport` 자체는 잘 정리됐다. 그런데 seed task의 write path 한 줄이 실제 앱/백엔드 contract와 다르다.

Evidence:

- `12-01-PLAN.md:40`: `reference/{motionId}` 문서 안 `referenceKeypointReport` field 신설이라고 맞게 적혀 있다.
- `12-01-PLAN.md:354`: 같은 task에서 Firestore에 `reference_motions/{motionId}` doc에 set한다고 적혀 있다.
- 실제 app read path: `app/src/lib/referenceMotions.ts:140`은 `collection(db, 'reference')`를 구독한다.
- 실제 seed script: `app/scripts/seed-reference-motions.mjs:252`는 `db.collection('reference').doc(m.motionId)`에 쓴다.
- 실제 backend contract: `backend/shared/python/sunity_shared/models.py:98-105`는 `reference/{motionId}`와 `REFERENCE_MOTIONS_COLLECTION = "reference"`를 명시한다.
- `docs/contract.md:137-139`도 `reference_motions/{id}`는 구버전 표기이고 실제는 `reference/{motionId}`라고 정리해 둔다.

Risk:

- 실행자가 `reference_motions/{motionId}`에 `referenceKeypointReport`를 쓰면 앱은 `reference/{motionId}`만 읽기 때문에 mode1 좌측 reference overlay가 계속 null이 된다.
- 5차에서 mirror를 폐기했기 때문에 reference doc이 유일한 source-of-truth다. write path가 틀리면 fallback이 없다.
- seed script와 plan 사이가 갈라져서 운영 seed 재현성이 낮아진다.

Required fix:

`12-01-PLAN.md:354`의 path를 `reference/{motionId}`로 바꿔라.

```text
산출 박제 후 Firestore `reference/{motionId}` doc 에 merge/set.
```

Recommended implementation detail:

- JS seed script는 기존처럼 `db.collection('reference').doc(motionId)`를 유지한다.
- Python helper를 만들면 hardcoded string 대신 `models.REFERENCE_MOTIONS_COLLECTION` 또는 `models.reference_motion_path(motion_id)`를 사용한다.
- test 이름은 `test_reference_motion_schema_lockstep` 그대로 괜찮지만, assertion은 반드시 `reference/{motionId}` path를 검증해야 한다.

내 의견: 이건 구조 문제가 아니라 경로 drift다. 하지만 reference mirror를 폐기한 현재 설계에서는 write path가 사실상 critical path이므로 HIGH로 본다. 수정량은 작다.

## Medium Findings

### M1. `player?` + `useEvent(player as any, ...)` static path 안전성이 명확하지 않다

Severity: **MEDIUM**

`KeypointOverlayProps`는 좋아졌다. 다만 최종 Wave 2 snippet은 optional `player`를 두고도 `useEvent(player as any, ...)`를 무조건 호출한다.

Evidence:

- `12-02-PLAN.md:155-164`: `player?: VideoPlayer | null`, `frameIndex?: number`.
- `12-03-PLAN.md:156`: `frameIndex` 명시 시 override라고 한다.
- `12-03-PLAN.md:161-165`: `useEvent(player as any, 'timeUpdate', ...)`.
- Expo 공식 v54 docs의 `useEvent` 예시는 실제 `player` 인스턴스를 대상으로 구독한다. event system은 `EventEmitter` 기반으로 설명된다.

Risk:

- Wave 2 이후에도 test/static render가 `frameIndex` override만 주고 `player`를 생략하면, `useEvent`가 null/undefined emitter를 받는 path가 생긴다.
- 타입을 `as any`로 눌러 통과시키면 compile-time 보호가 사라진다.

Recommendation:

내가 구현한다면 component를 둘로 나눈다.

```tsx
function KeypointOverlayBase(props: BaseProps & { resolvedFrameIndex: number }) {
  // SVG reshape/render only
}

export function KeypointOverlay(props: KeypointOverlayProps) {
  if (!props.player) {
    return <KeypointOverlayBase {...props} resolvedFrameIndex={props.frameIndex ?? 0} />;
  }
  return <SyncedKeypointOverlay {...props} player={props.player} />;
}

function SyncedKeypointOverlay(props: KeypointOverlayProps & { player: VideoPlayer }) {
  const { currentTime } = useEvent(props.player, 'timeUpdate', {
    currentTime: props.player.currentTime,
  });
  const frameIndex = props.frameIndex ?? clampFrame(currentTime, props.keypointReport);
  return <KeypointOverlayBase {...props} resolvedFrameIndex={frameIndex} />;
}
```

이렇게 하면 hook은 항상 concrete player를 받는 component에서만 호출되고, static/test path는 hook 없이 동작한다. Rules of Hooks도 지킨다.

### M2. reference seed reproducibility metadata가 아직 약하다

Severity: **MEDIUM**

`referenceKeypointReport` seed는 production analysis 1건 결과를 복사하는 방식이다. 가능은 하지만 출처 추적을 남겨야 한다.

Evidence:

- `12-01-PLAN.md:354`: 정은지 영상 분석 1건의 `analysisDoc.result.keypointReport`를 reference doc으로 복사한다고 한다.

Risk:

- 어떤 analysis에서 복사했는지 모르면 adapter/fps/schema version 변경 후 재생성이 어렵다.
- stale reference report를 감지하기 어렵다.

Recommendation:

`reference/{motionId}`에 report와 함께 metadata를 남겨라.

```typescript
referenceKeypointReportMeta?: {
  sourceAnalysisId: string;
  generatedAt: number;
  keypointReportVersion: string;
  fps: number;
  sourceVideoUrl?: string;
}
```

이건 execution blocker는 아니다. 다만 seed가 운영 기준 데이터가 되므로 추적성은 갖춰야 한다.

## Low Findings

### L1. `analysisDoc.keypoints` 구표현이 CONTEXT/UI-SPEC에 남아 있다

Severity: **LOW**

Active implementation contract는 `result.keypointReport`다. 그런데 일부 UI/context 문구는 예전 `analysisDoc.keypoints`를 말한다.

Evidence:

- `12-CONTEXT.md:141`: `analysisDoc.keypoints` 예시.
- `12-CONTEXT.md:150`: `analysisDoc.keypoints` 없을 시 fallback.
- `12-UI-SPEC.md:459-460`: `analysisDoc.angles` + `analysisDoc.keypoints` 필요 / keypoints 없으면 placeholder.

Risk:

- 실행자가 UI fallback을 `result.keypointReport`가 아니라 `analysisDoc.keypoints`로 찾을 수 있다.

Recommendation:

모두 `analysisDoc.result.keypointReport` 또는 `result.keypointReport`로 바꿔라. historical context라면 "legacy 표현"이라고 명시해야 한다.

### L2. `AST grep gate` 표현이 하나 남아 있다

Severity: **LOW**

Evidence:

- `12-00-PLAN.md:560`: "AST grep gate".

실제 verify line은 AST pytest로 바뀌었으므로 실행 blocker는 아니다. 표현만 `AST pytest gate` 또는 `Python ast gate`로 바꾸면 된다.

### L3. Wave 2 Firestore size 산식이 오래된 30fps/9개 표현이다

Severity: **LOW**

Evidence:

- `12-03-PLAN.md:386`, `12-03-PLAN.md:428`: `60s x 30fps x 9 x 2 x 4 byte`.

현재 계약은 9fps, 8 body keypoint + axisData/axisMask다. UAT 설명이긴 하지만 size 판단 문구라 최신 식으로 맞추는 편이 낫다.

## Recommended Patch Order

1. `12-01-PLAN.md:354`의 `reference_motions/{motionId}`를 `reference/{motionId}`로 수정한다.
2. `12-CONTEXT.md`와 `12-UI-SPEC.md`의 `analysisDoc.keypoints`를 `result.keypointReport`로 치환한다.
3. `12-00-PLAN.md:560`의 `AST grep gate`를 `Python ast pytest gate`로 바꾼다.
4. `12-03-PLAN.md`의 size 산식을 9fps/8 keypoint/axisData 기준으로 정정한다.
5. Wave 2 implementation note에 `KeypointOverlayBase` / `SyncedKeypointOverlay` split을 추가한다.
6. reference seed metadata를 follow-up 또는 Task 3 sub-step에 추가한다.

## Recommended Technologies

- Firestore path: existing `reference` collection. JS는 `db.collection('reference')`, Python은 `models.REFERENCE_MOTIONS_COLLECTION`.
- Call-site verification: Python stdlib `ast`, 현재 수정 방향 유지.
- Keypoint validation: Python `math.isfinite`, confidence `[0,1]` range, `type(item) is bool` for `axisMask`.
- Video sync: Expo v54 `useEvent` with concrete `VideoPlayer`; optional/static path는 base component로 분리.
- Overlay render: `react-native-svg`, single-frame reshape, `useMemo`.
- Seed traceability: `referenceKeypointReportMeta` with `sourceAnalysisId`, `generatedAt`, `fps`, report version.

## Final Assessment

5차 수정본은 4차 대비 실질적으로 수렴했다. 이전 blocker들은 대부분 닫혔고, plan-check iter-8의 PASS도 큰 흐름에서는 타당하다.

내 최종 판정은 **작은 수정 후 실행 가능**이다. `reference_motions/{motionId}` 경로만은 실제 collection과 달라서 HIGH로 남긴다. 이 한 줄을 `reference/{motionId}`로 고치면 Phase 12 plan은 실행 가능한 수준이다. 나머지는 execution blocker라기보다 실행 품질을 올리는 warning이다.

Official doc note: Expo v54 video docs show `useEvent` used against a concrete `VideoPlayer` instance and describe the event system as EventEmitter-based: https://docs.expo.dev/versions/v54.0.0/sdk/video/
