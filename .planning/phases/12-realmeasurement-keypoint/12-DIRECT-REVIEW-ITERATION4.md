---
phase: 12-realmeasurement-keypoint
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review-iteration-4
status: blocked-same-as-iteration-3
reviewed_plans:
  - 12-00-PLAN.md
  - 12-01-PLAN.md
  - 12-02-PLAN.md
  - 12-03-PLAN.md
  - 12-CONTEXT.md
  - 12-UI-SPEC.md
  - 12-VALIDATION.md
  - 12-DIRECT-REVIEW-ITERATION3.md
local_code_checked:
  - backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py
  - backend/shared/python/sunity_shared/analysis/pose_frame.py
  - app/src/types/analysis.ts
  - app/src/lib/referenceMotions.ts
---

# Phase 12 Direct Review: Iteration 4

## Executive Verdict

4차 기준으로는 **3차 리뷰 이후 plan 본문에 유의미한 수정이 반영되지 않았다.** 현재 작업트리에서 phase 12 계획서 본문은 tracked diff가 없고, 3차 리뷰의 핵심 blocker 검색 결과도 그대로 재현된다.

따라서 이번 판정은 **blocked-same-as-iteration-3**이다. 새로 발견한 설계 결함이라기보다, 3차에서 이미 차단한 항목들이 아직 닫히지 않은 상태다. 지금 `/gsd-execute-phase 12`로 들어가면 실행자가 같은 지점에서 깨질 가능성이 높다.

## Delta From Iteration 3

| 3차 항목 | 4차 상태 | 근거 |
|---|---|---|
| B1 RTMW helper가 `scores_133` 대신 `kp[2]`를 score로 사용 | **Open** | `12-00-PLAN.md:89-118` 그대로 |
| B2 `referenceKeypointReport` vs `refMotion?.keypointReport` mismatch | **Open** | `12-01-PLAN.md:40`, `12-02-PLAN.md:64/:390`, `12-03-PLAN.md:126` 그대로 |
| B3 `KeypointOverlay` props contract drift | **Open** | `12-02-PLAN.md:155-162`, `12-03-PLAN.md:144-151`, `12-UI-SPEC.md:248-258` 그대로 |
| H1 grep 기반 kismam 검증 | **Open** | `12-00-PLAN.md:477`, `12-01-PLAN.md:317/:438/:454` 그대로 |
| H2 size budget이 reference mirror를 반영하지 않음 | **Open** | `12-01-PLAN.md:341/:457`, `12-CONTEXT.md:157`, `12-UI-SPEC.md:570` 그대로 |
| H3 `data`/`confidence` finite/range validator 부족 | **Open** | `12-01-PLAN.md:222/:247` 그대로 |
| H4 첫 frame missing 시 전체 KeypointReport drop | **Open** | `12-01-PLAN.md:231` 그대로 |

## Blocking Findings

### B1. RTMW helper는 여전히 실제 adapter signature와 맞지 않는다

Severity: **BLOCKER**

Current plan:

- `12-00-PLAN.md:89`: `keypoints_2d=_build_keypoints_2d_from_rtmw(rtmw_kp_133, image_width, image_height)`
- `12-00-PLAN.md:92`: helper signature가 `raw_133, img_w, img_h`
- `12-00-PLAN.md:113-114`: `kp = raw_133[rtmw_idx]`, `x, y, score = float(kp[0]), float(kp[1]), float(kp[2])`
- `12-00-PLAN.md:118-120`: `visibility=score, ,`

Actual code:

- `backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py:138-157`는 `keypoints_133`와 `scores_133`를 별도 인자로 받는다.
- `rtmw_133_to_coco17.py:182-183`도 keypoint 좌표와 score를 분리해서 읽는다.
- `kp[2]`는 3D path에서는 z일 수 있다.

Risk:

- confidence가 z좌표로 저장될 수 있다.
- snippet 자체가 syntax error다.
- `KeypointReport.confidence`와 low-confidence UI가 처음부터 오염된다.

Required fix:

```python
def _build_keypoints_2d_from_rtmw(
    keypoints_133: np.ndarray,
    scores_133: np.ndarray,
    img_w: int,
    img_h: int,
) -> dict[str, Keypoint2D]:
    if img_w <= 0 or img_h <= 0:
        return {}

    out: dict[str, Keypoint2D] = {}
    for coco_name, rtmw_idx in RTMW_133_TO_COCO17.items():
        kp = keypoints_133[rtmw_idx]
        score = float(np.clip(scores_133[rtmw_idx], 0.0, 1.0))
        out[coco_name] = Keypoint2D(
            x=float(kp[0]) / float(img_w),
            y=float(kp[1]) / float(img_h),
            visibility=score,
        )
    return out
```

내 의견: 이건 문서 표현 수준이 아니다. Phase 12의 오버레이 데이터 신뢰도를 좌우하는 첫 source이다. 4차에서 다른 항목보다 먼저 닫아야 한다.

### B2. `referenceKeypointReport`를 정의해 놓고 UI 예시는 다른 필드를 읽는다

Severity: **BLOCKER**

Current plan:

- `12-01-PLAN.md:340-348`: `referenceKeypointReport?: KeypointReport | null`가 공식 task body에 있다.
- `12-01-PLAN.md:40`: must_haves에는 `ReferenceMotion`에 `keypointReport?: KeypointReport | null` 추가라고 남아 있다.
- `12-02-PLAN.md:64`, `12-02-PLAN.md:390`, `12-03-PLAN.md:126`: UI 예시는 `refMotion?.keypointReport`를 읽는다.

Actual code:

- `app/src/types/analysis.ts:255-293`의 현재 `ReferenceMotion`에는 `keypointReport`가 없다.
- `app/src/lib/referenceMotions.ts:99-120`의 normalize도 reference keypoint report를 아직 반환하지 않는다.

Risk:

- strict TS에서 바로 compile error.
- 실행자가 `keypointReport`와 `referenceKeypointReport`를 둘 다 추가하면 장기 schema drift.
- mode1 split의 reference overlay가 null로 비어 사용자 비교 경험이 깨진다.

Required fix:

필드명은 `referenceKeypointReport` 하나로 고정하라.

```tsx
const referenceReport =
  result.referenceKeypointReport ??
  refMotion?.referenceKeypointReport ??
  null;
```

`12-01-PLAN.md:40`, `12-02-PLAN.md:64/:390`, `12-03-PLAN.md:126`을 모두 이 기준으로 맞춰야 한다.

내 의견: `referenceKeypointReport`가 낫다. `keypointReport`는 사용자 분석 결과의 주 report 이름으로 이미 의미가 강하다. reference 문서에서 같은 이름을 쓰면 읽는 사람이 "현재 분석 결과인지 reference seed인지"를 매번 문맥으로 해석해야 한다.

### B3. `KeypointOverlayProps`가 아직 단일 계약으로 잠기지 않았다

Severity: **BLOCKER**

Current contradictions:

- `12-02-PLAN.md:155-162`: Wave 1 props는 `frameIndex?`, `jointAngles?: Record<string, ...>`.
- `12-03-PLAN.md:144-151`: Wave 2 props는 `player: VideoPlayer | null`, `jointAngles?: Record<string, ...>`, `frameIndex` 없음.
- `12-03-PLAN.md:220`: "Wave 1의 frameIndex prop 보존"이라고 하지만 props block에는 없다.
- `12-UI-SPEC.md:248-255`: `frameIndex: number`, `jointAngles?: ReadonlyArray<JointAssessment>`, `deltaThresholdDeg?`.
- `12-UI-SPEC.md:258`: `KeypointOverlay`는 player 의존이 없다고 하지만 `12-03-PLAN.md`는 player prop을 필수로 둔다.
- `12-UI-SPEC.md:294`: Wave 1에서 `useEvent`로 frameIndex를 산출한다고 하지만 `12-02-PLAN.md:149`는 Wave 1 `useEvent` 미사용이라고 한다.

Risk:

- Wave 1 구현물이 Wave 2에서 깨진다.
- TypeScript 타입이 문서마다 달라 실행자가 임의로 선택하게 된다.
- hook 위치가 애매해진다. `useEvent`는 component body에서 호출되어야 하므로 "VideoCompare render prop이 useEvent로 frameIndex 산출" 같은 표현은 위험하다.

Required fix:

Wave 1부터 최종 API를 하나로 고정하라.

```tsx
type KeypointOverlayProps = {
  player?: VideoPlayer | null;
  keypointReport: KeypointReport | null;
  videoSize: { width: number; height: number };
  visible: boolean;
  frameIndex?: number;
  jointAngles?: Record<string, { current: number | null; target: number | null }>;
  deltaThresholdDeg?: number;
  showAngleLabels?: boolean;
};
```

Rule:

- Wave 1: `player` 생략, `frameIndex={0}`.
- Wave 2: `player` 전달, `KeypointOverlay` 내부에서 `useEvent`로 frame index 산출.
- `frameIndex`는 테스트/static override로 유지.
- `jointAngles`는 `Record`로 고정. `JointScore[]`는 result.tsx에서 변환.

내 의견: 이 방식이 가장 적은 변경으로 Wave 1 정적 렌더와 Wave 2 sync를 같은 component 위에 얹는다. `player`를 Wave 2에서 새로 필수화하면 Wave 1 component API를 다시 바꾸게 된다.

## High Findings Still Open

### H1. kismam call-site 검증은 grep이 아니라 AST여야 한다

Severity: **HIGH**

Open evidence:

- `12-00-PLAN.md:477`
- `12-01-PLAN.md:317`
- `12-01-PLAN.md:438`
- `12-01-PLAN.md:454`

Risk:

- 멀티라인 Python call은 정상 코드도 grep에서 실패한다.
- 주석/문자열에 `user_angles=`가 있으면 잘못 통과할 수 있다.

Recommended technology:

Python standard library `ast`.

내 의견: Phase 12는 backend wiring phase다. 핵심 contract 검증을 grep으로 두는 건 품질 기준이 낮다. 이건 별도 패키지 없이 30줄 내외 테스트로 닫을 수 있다.

### H2. Firestore size budget은 mode1 double report를 포함해야 한다

Severity: **HIGH**

Open evidence:

- `12-01-PLAN.md:341`: mode1 result에 `referenceKeypointReport` mirror.
- `12-01-PLAN.md:457`: size budget은 9fps x 60s synthetic doc <= 700 KiB.
- `12-CONTEXT.md:157`, `12-UI-SPEC.md:570`: 계산식은 사실상 단일 report 기준.

Risk:

- mode1 result는 `keypointReport`와 `referenceKeypointReport`를 모두 품을 수 있다.
- 기존 `angles`, report들, force pattern까지 포함하면 Firestore 1 MiB margin이 줄어든다.

Required fix:

size test를 두 개로 나눠라.

- mode3: user `keypointReport` 1개.
- mode1: user `keypointReport` + `referenceKeypointReport` + 기존 result payload.

내 의견: 가능하면 analysis result에는 reference report를 mirror하지 말고 `referenceMotionId`로 reference doc을 읽는 쪽이 더 낫다. mirror를 유지한다면 size test는 반드시 두 report 포함이어야 한다.

### H3. `data`와 `confidence`도 finite/range 검증 대상이다

Severity: **HIGH**

Open evidence:

- `12-01-PLAN.md:222`: finite 검증은 `axis_data`에만 명시.
- `12-01-PLAN.md:247`: Firestore validator도 `axisData finite`만 명시.

Risk:

- `data`에 NaN/Inf가 들어가면 SVG가 깨질 수 있다.
- `confidence`가 NaN, Inf, -1, 2여도 통과할 수 있다.

Required fix:

- `data`: finite number. 좌표계가 normalized로 확정되면 `0 <= v <= 1`.
- `confidence`: finite number and `0 <= v <= 1`.
- `axisData`: finite 유지. normalized 확정 시 range도 같이 검증.
- `axisMask`: `type(item) is bool` 유지.

Recommended technology:

Python `math.isfinite` + explicit `type(item) is bool`. JavaScript/Firestore payload는 JSON 직전 Python validator에서 막는 편이 안전하다.

### H4. 첫 frame missing이면 전체 report를 버리는 조건은 과하다

Severity: **HIGH**

Open evidence:

- `12-01-PLAN.md:231`: `pose_frames[0].keypoints_2d is None -> return None`.

Risk:

- 첫 프레임에 사람 감지가 실패하면 뒤의 정상 frame들이 모두 버려진다.
- 실제 촬영 영상은 초반 진입/세팅 구간에서 첫 프레임 미감지가 충분히 발생할 수 있다.

Required fix:

```python
if not pose_frames:
    return None
if not any(frame.keypoints_2d for frame in pose_frames):
    return None
```

그 외 missing frame은 현재 계획처럼 `(0.0, 0.0)`, confidence 0, reliability low로 유지하면 된다.

## Recommended Patch Order

1. `12-00-PLAN.md`의 RTMW helper signature/code block을 실제 adapter 기준으로 수정한다.
2. `referenceKeypointReport` 필드명을 전 artifact에 일괄 적용한다.
3. `KeypointOverlayProps`를 Wave 1/2/UI-SPEC에서 하나로 잠근다.
4. kismam grep gate를 AST test로 바꾼다.
5. KeypointReport validator에 `data`/`confidence` finite/range를 추가한다.
6. size budget test에 mode1 double-report case를 추가하거나, reference report mirror를 제거한다.
7. `pose_frames[0]` 조건을 `any(frame.keypoints_2d)` 조건으로 바꾼다.

이 순서가 좋은 이유는 앞의 3개가 실행자가 어떤 타입/함수/props를 구현해야 하는지 결정하는 계약이고, 뒤의 4개는 그 계약을 안정적으로 검증하는 게이트이기 때문이다.

## Recommended Technologies

- **RTMW confidence source**: existing `scores_133`, `np.clip`, `Keypoint2D.visibility`.
- **Plan/code contract verification**: Python `ast` for call-site checks, not grep.
- **Payload validation**: Python `math.isfinite`; no dependency needed.
- **Frontend sync**: `expo-video` player via render prop, `useEvent` inside `KeypointOverlay` body.
- **Overlay rendering**: keep `react-native-svg`; optimize with single-frame reshape and `useMemo`.
- **Reference data**: prefer `referenceMotion.referenceKeypointReport` as source of truth; mirror into result only after size budget proves safe.

## Final Assessment

4차에서 새 수정이 반영되지 않았기 때문에 판정도 3차와 동일하다. 현재 plan은 방향은 맞지만, 실행 전 contract mismatch가 남아 있다.

승인 기준은 명확하다.

- B1, B2, B3는 반드시 닫아야 한다.
- H1-H4는 "나중에 실행 중 고치기"로 넘기기에는 비용이 낮고 리스크가 크다. 같이 닫는 편이 낫다.

이 7개를 수정하면 다음 리뷰에서는 execution-ready 판정까지 갈 수 있다. 지금은 실행 보류가 맞다.
