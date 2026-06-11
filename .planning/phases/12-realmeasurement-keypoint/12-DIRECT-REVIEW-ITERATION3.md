---
phase: 12-realmeasurement-keypoint
reviewer: Codex
date: 2026-06-10
scope: direct-plan-review-iteration-3
status: revise-before-execution
reviewed_plans:
  - 12-00-PLAN.md
  - 12-01-PLAN.md
  - 12-02-PLAN.md
  - 12-03-PLAN.md
  - 12-CONTEXT.md
  - 12-UI-SPEC.md
  - 12-VALIDATION.md
  - 12-DIRECT-REVIEW-ITERATION2.md
  - 12-PLAN-CHECK-ITER5.md
  - 12-PLAN-CHECK-ITER6.md
local_code_checked:
  - backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py
  - backend/shared/python/sunity_shared/analysis/pose_frame.py
  - backend/shared/python/sunity_shared/analysis/kismam.py
  - backend/shared/python/sunity_shared/analysis/skeleton.py
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - backend/functions/pipeline/app.py
  - app/src/types/analysis.ts
  - app/src/lib/referenceMotions.ts
---

# Phase 12 Direct Review: Iteration 3

## Executive Verdict

3차 수정본은 2차 대비 큰 폭으로 좋아졌다. 특히 `Keypoint2D.visibility` 정정, `axisData + axisMask` 10-field schema, `targetSource` end-to-end 확장, `referenceKeypointReport` task 추가, `onPlayersReady` 제거, delta 강조를 "영상 전체 대표 편차" MVP로 명시한 점은 올바른 방향이다. `12-PLAN-CHECK-ITER6.md`는 PASS라고 판정하지만, 그 체크는 주로 "9 필드" 잔재 제거에 한정되어 있다.

내 판정은 아직 **revise-before-execution**이다. 이유는 실행자가 plan 예시를 그대로 따라가면 깨질 가능성이 높은 계약 불일치가 남아 있기 때문이다. 특히 아래 3개는 실행 전에 반드시 정리해야 한다.

1. RTMW 2D helper 예시가 실제 adapter contract와 맞지 않는다. `scores_133`를 써야 하는데 `kp[2]`를 visibility로 쓰고, snippet 자체에도 문법 오류가 있다.
2. `referenceKeypointReport`를 새 계약으로 만들었지만 Wave 1/2 UI 예시는 계속 `refMotion?.keypointReport`를 참조한다.
3. `KeypointOverlay` props 계약이 12-02, 12-03, UI-SPEC 사이에서 서로 다르다.

큰 방향은 맞다. 지금은 구조 재설계가 아니라, 실행 전 contract를 한 번 더 잠그는 단계다.

## Iteration 2 Fix Status

| 2차 주요 지적 | 3차 상태 | 의견 |
|---|---|---|
| `Keypoint2D.raw_visibility` ghost field | **Closed** | 이제 `Keypoint2D.visibility`를 confidence source로 잡았다. |
| `kismam.assess(target_source=...)` contract 누락 | **Mostly closed** | `kismam.py`, `JointAssessment`, `assemble.py`, TS까지 task에 들어왔다. 다만 검증 게이트가 grep 기반이라 신뢰도가 낮다. |
| `axisData` NaN sentinel | **Closed** | `axisMask` 도입으로 finite-only 계약이 됐다. 이건 좋은 수정이다. |
| 9/10 field schema drift | **Closed in main artifacts** | 12-VALIDATION의 9필드 잔재도 iter-6에서 닫혔다. |
| mode1 reference overlay source 누락 | **Partially closed** | `referenceKeypointReport` task는 생겼지만 UI 사용 예시와 must_haves 일부가 여전히 다른 필드명을 쓴다. |
| `onPlayersReady` dual-state risk | **Closed** | 12-03이 render prop player 전달로 정리됐다. |
| delta frame-level 여부 불명확 | **Closed enough** | 12-03이 "영상 전체 대표 편차, frame-level X"로 MVP를 명시했다. |

## Blockers

### B1. RTMW `keypoints_2d` helper가 실제 adapter contract와 다르다

Severity: **BLOCKER**

`12-00-PLAN.md`의 RTMW 2D helper 예시는 현재 adapter의 입력 구조를 잘못 읽고 있다.

Evidence:

- `12-00-PLAN.md:99-120`: `_build_keypoints_2d_from_rtmw(raw_133, img_w, img_h)`가 `kp[2]`를 `score`로 읽는다.
- `12-00-PLAN.md:118-120`: `visibility=score, ,` 형태로 snippet 자체가 Python syntax error다.
- 실제 `backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py:138-157`: adapter는 `keypoints_133`와 `scores_133`를 분리해서 받는다.
- 실제 `rtmw_133_to_coco17.py:182-183`: COCO keypoint 좌표는 `keypoints_133[rtmw_idx]`, confidence는 `scores_133[rtmw_idx]`다.

Risk:

- 3D path에서 `kp[2]`는 score가 아니라 z일 수 있다. 그러면 visibility가 z좌표로 채워지고 confidence가 완전히 틀어진다.
- plan snippet을 복사하면 문법 오류로 바로 실패한다.
- `visibility=float(np.clip(score, 0.0, 1.0))`라고 behavior에는 적었지만 code block은 clamp도 누락한다. 실행자에게 상충 신호를 준다.

Recommendation:

`12-00-PLAN.md`의 helper를 실제 signature에 맞춰 고쳐라.

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

그리고 call site도 다음처럼 명시해야 한다.

```python
keypoints_2d=_build_keypoints_2d_from_rtmw(
    keypoints_133,
    scores_133,
    image_width,
    image_height,
)
```

내가 한다면 이 항목은 가장 먼저 고친다. 여기서 confidence source가 틀어지면 뒤의 `axisData`, `confidence`, low-reliability UI까지 모두 오염된다.

### B2. `referenceKeypointReport` 계약과 UI 사용 필드명이 어긋난다

Severity: **BLOCKER**

3차 수정본은 `referenceKeypointReport`를 신설했다. 그런데 Wave 1/2 사용 예시는 아직 `refMotion?.keypointReport`를 참조한다.

Evidence:

- `12-01-PLAN.md:340-348`: 새 계약은 `ReferenceMotion.referenceKeypointReport?: KeypointReport | null` 및 `AnalysisResult.referenceKeypointReport?: KeypointReport | null`.
- `12-01-PLAN.md:40`: must_haves에는 여전히 `ReferenceMotion` TS interface에 `keypointReport?: KeypointReport | null`을 추가한다고 적혀 있다. 같은 파일 내부에서도 필드명이 다르다.
- `12-02-PLAN.md:64`: key link가 `refMotion?.keypointReport`를 사용한다.
- `12-02-PLAN.md:390`: Wave 1 예시도 `<KeypointOverlay keypointReport={refMotion?.keypointReport ?? null} ... />`.
- `12-03-PLAN.md:126`: Wave 2 예시도 `keypointReport={refMotion?.keypointReport ?? null}`.
- 현재 `app/src/types/analysis.ts:255-293`의 `ReferenceMotion`에는 `keypointReport`가 없다.

Risk:

- strict TS에서는 `Property 'keypointReport' does not exist on type 'ReferenceMotion'`로 막힌다.
- 느슨하게 구현되면 reference overlay가 항상 null이 되어 mode1 좌측 오버레이가 비어 보인다.
- 더 위험한 경우, 실행자가 필드명을 맞추려고 `ReferenceMotion.keypointReport`를 추가하면서 `referenceKeypointReport`와 이중 계약이 생긴다.

Recommendation:

필드명을 하나로 고정하라. 나는 `referenceKeypointReport`를 유지하는 쪽을 추천한다. 이유는 사용자 분석 결과의 `keypointReport`와 reference motion의 keypoint report를 이름에서 분리할 수 있고, `AnalysisResult.referenceKeypointReport` mirror와도 맞기 때문이다.

Wave 1/2 예시는 이렇게 바꿔야 한다.

```tsx
const referenceReport =
  result.referenceKeypointReport ??
  refMotion?.referenceKeypointReport ??
  null;

<VideoCompare
  leftOverlay={(player) => (
    <KeypointOverlay
      player={player}
      keypointReport={referenceReport}
      videoSize={referenceVideoSize}
      visible={overlayVisible}
      showAngleLabels={false}
    />
  )}
  rightOverlay={(player) => (
    <KeypointOverlay
      player={player}
      keypointReport={result.keypointReport ?? null}
      videoSize={userVideoSize}
      visible={overlayVisible}
      jointAngles={jointAngles}
      showAngleLabels
    />
  )}
/>
```

추가로 `12-01-PLAN.md:40`의 `keypointReport?:` 표현을 `referenceKeypointReport?:`로 바꿔야 한다. 이건 단순 문서 문제가 아니라 실행자가 타입을 잘못 추가하게 만드는 지시다.

### B3. `KeypointOverlay` props contract가 세 문서에서 서로 다르다

Severity: **BLOCKER**

`KeypointOverlay`가 player를 직접 받는지, `frameIndex`만 받는지, `jointAngles` shape가 무엇인지가 12-02, 12-03, UI-SPEC에서 다르게 정의되어 있다.

Evidence:

- `12-02-PLAN.md:155-162`: Wave 1 props는 `keypointReport`, `videoSize`, `frameIndex?`, `visible`, `jointAngles?: Record<string, ...>`.
- `12-03-PLAN.md:144-151`: Wave 2 props는 `player: VideoPlayer | null`, `keypointReport`, `videoSize`, `visible`, `jointAngles?: Record<string, ...>`이고 `frameIndex`가 사라진다.
- `12-03-PLAN.md:220`: "Wave 1의 frameIndex prop 보존"이라고 하지만, 같은 task의 props block에는 없다.
- `12-UI-SPEC.md:248-255`: props는 `frameIndex: number`, `jointAngles?: ReadonlyArray<JointAssessment>`, `deltaThresholdDeg?`.
- `12-UI-SPEC.md:258`: "KeypointOverlay 자체는 player 의존 X"라고 하지만 `12-03-PLAN.md:145`는 `player` prop을 필수로 둔다.
- `12-UI-SPEC.md:294`: Wave 1에서 VideoCompare render prop이 `useEvent`로 frameIndex를 산출한다고 되어 있는데, `12-02-PLAN.md:149`는 Wave 1에서 `useEvent` 미사용이라고 한다.

Risk:

- Wave 1에서 만든 component를 Wave 2가 대폭 갈아엎게 된다. 이건 phase plan의 "incremental wave" 의도와 반대다.
- TS strict mode에서 `jointAngles` 타입이 `Record`인지 `ReadonlyArray<JointAssessment>`인지 충돌한다.
- hooks 사용 위치가 애매해진다. `useEvent`는 React hook이므로 render prop callback 안에서 직접 쓰면 안 되고, component body 안에서 써야 한다.

Recommendation:

단일 props contract를 지금 확정하라. 내가 한다면 Wave 1부터 Wave 2까지 같은 component API를 유지한다.

```tsx
type KeypointOverlayProps = {
  player?: VideoPlayer | null;                 // Wave 1에서는 생략 가능
  keypointReport: KeypointReport | null;
  videoSize: { width: number; height: number };
  visible: boolean;
  frameIndex?: number;                         // static/test override
  jointAngles?: Record<string, { current: number | null; target: number | null }>;
  deltaThresholdDeg?: number;
  showAngleLabels?: boolean;                   // mode prop 대신 표현 의도만 전달
};
```

동작 규칙:

- `player`가 있으면 `useEvent(player, 'timeUpdate', ...)`로 frame index를 산출한다.
- `player`가 없으면 `frameIndex ?? 0`을 사용한다.
- `jointAngles`는 `Record`로 고정한다. backend `JointScore[]`는 result.tsx에서 한 번만 `Record`로 변환한다.
- UI-SPEC의 "player 의존 X" 문장은 제거한다. 대신 "player prop은 optional, frameIndex override 지원"으로 바꾼다.

이렇게 하면 Wave 1 정적 렌더, Wave 2 동기화, 테스트 fixture가 모두 같은 API 위에서 동작한다.

## High Findings

### H1. kismam wiring 검증이 grep 기반이라 실제로는 신뢰하기 어렵다

Severity: **HIGH**

plan은 `grep "kismam.assess(" | grep -v "user_angles="`류의 gate를 여러 번 쓴다.

Evidence:

- `12-00-PLAN.md:477`: `test_kismam_assess_grep_no_kwargless_call`.
- `12-01-PLAN.md:317`: `<ast_check>grep -rn "kismam\.assess(" ... | grep -v "user_angles=" | wc -l</ast_check>`.
- `12-01-PLAN.md:438`, `:454`: threat/verification도 같은 grep gate를 신뢰한다.

Risk:

- 멀티라인 호출은 첫 줄이 `kismam.assess(`이고 `user_angles=`는 다음 줄에 오므로, 올바른 코드도 grep gate에서 실패할 수 있다.
- 반대로 한 줄에 `user_angles=` 문자열이 주석으로 있어도 통과할 수 있다.
- 12-00 T2의 핵심 회귀 차단이 약하다.

Recommendation:

Python `ast` 기반 검사로 바꿔라. 이건 별도 패키지 없이 가능하다.

```python
import ast
from pathlib import Path

tree = ast.parse(Path("backend/functions/pipeline/app.py").read_text())
bad = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    func = node.func
    is_kismam_assess = (
        isinstance(func, ast.Attribute)
        and func.attr == "assess"
        and isinstance(func.value, ast.Name)
        and func.value.id == "kismam"
    )
    if not is_kismam_assess:
        continue
    kwargs = {kw.arg for kw in node.keywords if kw.arg}
    required = {"user_angles", "reference_angles", "target_source"}
    if not required.issubset(kwargs):
        bad.append((node.lineno, sorted(required - kwargs)))

assert not bad, bad
```

나는 이 검사를 `backend/tests/phase12/test_kismam_assess_with_angles.py` 안에 넣겠다. shell grep은 보조 smoke check 정도로만 둔다.

### H2. Firestore size budget이 `referenceKeypointReport` mirror를 반영하지 않는다

Severity: **HIGH**

3차 수정본은 mode1 분석 결과에 사용자 `keypointReport`와 reference `referenceKeypointReport`를 둘 다 넣는 방향이다. 그런데 size budget 계산은 여전히 단일 keypoint report 기준에 가깝다.

Evidence:

- `12-01-PLAN.md:341`: mode1 분석 시 reference doc의 `referenceKeypointReport`를 `analysisDoc.result.referenceKeypointReport`로 mirror한다고 한다.
- `12-01-PLAN.md:457`: size budget test는 "9fps x 60s worst-case synthetic doc 전체 byte <= 700 KiB"만 명시한다.
- `12-CONTEXT.md:157`, `12-UI-SPEC.md:570`: 계산식도 단일 report 기준이다.

Risk:

- mode1 result doc은 `keypointReport`와 `referenceKeypointReport`를 모두 포함하므로 대략 2배가 된다.
- 여기에 `angles`, `bodyComparisonReport`, `bodyNormalizationProfile`, `forceSignalsReport`, `forcePatternInference`가 같이 들어가면 700 KiB margin이 생각보다 줄어든다.
- Firestore 1 MiB limit은 초과하면 분석 완료 저장 자체가 실패한다. 이건 UI fallback으로 복구되지 않는다.

Recommendation:

size budget test를 mode별로 나눠라.

- mode3 worst case: `result.keypointReport` 1개.
- mode1 worst case: `result.keypointReport` + `result.referenceKeypointReport` + 기존 result payload.

내 추천은 mirror를 꼭 해야 하는지 재검토하는 것이다. UI가 `refMotion?.referenceKeypointReport`를 읽을 수 있다면 analysis result에는 `referenceMotionId`만 유지하고 reference report는 reference doc에서 읽는 편이 더 낫다. offline/debug 편의를 위해 mirror를 유지하려면, size gate는 반드시 "두 report 포함"으로 잠가야 한다.

### H3. `KeypointReport` validator가 `data`/`confidence`의 finite/range를 충분히 막지 않는다

Severity: **HIGH**

3차 수정본은 `axisData`의 NaN/Inf를 잘 막았다. 하지만 본체 좌표인 `data`와 `confidence`는 상대적으로 느슨하다.

Evidence:

- `12-01-PLAN.md:222`: `axis_data` finite 검증은 명시되어 있지만 `data` finite, `confidence` finite/range 검증은 없다.
- `12-01-PLAN.md:247`: Firestore validator도 `data` / `confidence` / `axisData`를 list[number]로 묶고, finite 강제는 `axisData`에만 명시한다.

Risk:

- `data`에 NaN/Inf가 들어가면 SVG 좌표가 깨진다.
- `confidence`가 NaN, Inf, 2.0, -1.0이어도 통과할 수 있다.
- UI의 low-confidence/occlusion 표기가 신뢰할 수 없어진다.

Recommendation:

`KeypointReport.__post_init__`와 `_validate_keypoint_report`에 다음을 추가하라.

- `data`: 모든 값 `int | float`, finite, 가능하면 normalized path에서는 `0.0 <= v <= 1.0`.
- `confidence`: 모든 값 finite, `0.0 <= v <= 1.0`.
- `axisData`: 모든 값 finite, 좌표계가 normalized로 확정되면 `0.0 <= v <= 1.0`.

좌표계가 pixel일 가능성을 열어둔다면 range check는 `12-WAVE0-AUDIT.md` 결과에 따라 분기해도 된다. 하지만 finite check는 반드시 공통으로 필요하다.

### H4. 첫 frame의 `keypoints_2d`가 없으면 전체 `KeypointReport`를 버리는 설계다

Severity: **HIGH**

`build_keypoint_report`가 `pose_frames[0].keypoints_2d is None`이면 `return None` 하도록 계획되어 있다.

Evidence:

- `12-01-PLAN.md:230-231`: "pose_frames 비었거나 `pose_frames[0].keypoints_2d` 가 None -> return None".
- 같은 task의 나머지 설명은 frame별 missing keypoint를 `(0.0, 0.0) + confidence=0.0 + reliability='low'`로 처리한다.

Risk:

- 영상 첫 프레임에 사람 감지가 없거나 낮은 confidence면, 뒤 프레임 데이터가 정상이어도 report 전체가 사라진다.
- 사용자는 "키포인트 데이터 미가용"만 보게 되고, 실제 분석 가능한 대부분의 frame을 버린다.

Recommendation:

전체 report를 버리는 조건은 "모든 frame에 keypoints_2d가 없음"으로 바꿔라.

```python
if not pose_frames:
    return None
if not any(frame.keypoints_2d for frame in pose_frames):
    return None
```

그 외에는 frame별로 zero placeholder + low reliability를 채우는 현재 계획이 맞다.

## Medium Findings

### M1. `TargetSource` 정의 위치가 중복될 가능성이 높다

Severity: **MEDIUM**

`12-00-PLAN.md`는 `TargetSource`를 `kismam.py`에도 두고, `dimensions.py`에도 둔다.

Evidence:

- `12-00-PLAN.md:146-149`: `kismam.py`에 `TargetSource = Literal[...]`.
- `12-00-PLAN.md:330-340`: `dimensions.py`에도 `TargetSource`와 `_TARGET_SOURCES`.

Risk:

- enum value가 한쪽만 수정되는 drift가 생긴다.
- `_target_source_for_extension`이 dimensions에 있고, 실제 `JointAssessment.target_source`는 kismam에 있으면 소유권이 애매하다.

Recommendation:

가장 단순한 방식은 `TargetSource`를 `kismam.py`에만 두고, `dimensions.py`에는 extension target dict/helper만 두는 것이다. 더 깔끔하게 하려면 `analysis/target_source.py` 같은 tiny module을 만들 수 있지만, Phase 12에서는 새 abstraction보다 중복 제거가 우선이다.

### M2. reference seed 방식이 운영 재현성 측면에서 약하다

Severity: **MEDIUM**

`referenceKeypointReport` seed 방식은 "belle가 production analysis 1건 돌린 결과를 복사"에 가깝다.

Evidence:

- `12-01-PLAN.md:354-356`: production analysis 결과의 `analysisDoc.result.keypointReport`를 reference doc으로 복사한다고 한다.

Risk:

- 어떤 analysisId에서 복사했는지 추적이 약하면 reference report 재생성이 어렵다.
- reference 영상이 바뀌거나 fps/adapter가 바뀌었을 때 stale data를 감지하기 어렵다.

Recommendation:

seed helper에 source metadata를 넣어라.

- `sourceAnalysisId`
- `sourceVideoUrl` 또는 `referenceMotionId`
- `generatedAt`
- `keypointReport.version`
- `frameExtractorFps`

내가 한다면 `copy-reference-keypoint-report --motion-id ref-... --analysis-id ...` 형태의 deterministic script를 만들고, script가 `_validate_keypoint_report`를 통과한 payload만 쓰게 한다.

### M3. `complete_analysis(... reference_keypoint_report=...) 또는 result dict 직접 박제`는 선택지가 아니라 결정을 내려야 한다

Severity: **MEDIUM**

Evidence:

- `12-01-PLAN.md:359`: `complete_analysis(..., reference_keypoint_report=...)` 또는 result dict 직접 박제 후 complete_analysis 한 번에.

Risk:

- 실행자가 둘 중 하나를 임의로 고르면 테스트/validator 위치가 흔들린다.
- `keypoint_report`는 scoped validator를 타는데 `referenceKeypointReport`는 직접 result dict에 넣으면 validator 우회가 생길 수 있다.

Recommendation:

`firestore_admin.complete_analysis(reference_keypoint_report=...)`로 고정하라. validator는 `_validate_keypoint_report`를 재사용한다. 직접 result dict 삽입은 금지한다.

### M4. UI-SPEC의 frame sync 설명은 Wave 1/2 책임과 맞지 않는다

Severity: **MEDIUM**

Evidence:

- `12-02-PLAN.md:149`: Wave 1은 `useEvent` 미사용, `frameIndex` prop 사용.
- `12-UI-SPEC.md:294`: Wave 1에서 VideoCompare render prop이 `useEvent`로 frameIndex를 산출한다고 한다.

Risk:

- Wave 1에서 sync를 구현하려다 scope creep이 생긴다.
- Wave 2에서 다시 같은 코드를 옮겨야 한다.

Recommendation:

UI-SPEC을 다음처럼 고쳐라.

- Wave 1: `frameIndex={0}` static render only.
- Wave 2: `player` prop이 있는 경우 KeypointOverlay 내부에서 `useEvent`로 frameIndex 산출.

## Low Findings

### L1. `12-03-PLAN.md`의 size 계산식에 30fps/9개 잔재가 있다

Severity: **LOW**

Evidence:

- `12-03-PLAN.md:382`: `60s x 30fps x 9 x 2 x 4 byte ~= 0.12 MiB`.

이제 Phase 12 계약은 9fps, 8 body keypoint, axisData/axisMask다. 수치 자체는 UAT 설명이라 실행 blocker는 아니지만, Firestore size 판단 근거로 읽힐 수 있으니 최신 식으로 바꿔라.

### L2. `12-VALIDATION.md` 일부 decision row가 `axisMask`를 빠뜨린다

Severity: **LOW**

Evidence:

- `12-VALIDATION.md:57`: D-12-C2 row는 `KeypointReport 8 + axisData`까지만 말한다.
- `12-VALIDATION.md:66`: D-12-E3 row도 `Firestore flat scoped validator + axisData`까지만 말한다.

주요 SC와 schema row는 이미 10필드로 고쳐졌으므로 blocker는 아니다. 다만 close-out verifier가 읽는 seed 문서라 `axisMask`까지 넣는 편이 안전하다.

## My Recommended Execution Approach

내가 이 phase를 실행한다면 plan을 이렇게 한 번 더 잠그고 시작하겠다.

1. **Plan patch only commit**
   - B1/B2/B3/H1/H2/H3/H4만 먼저 문서에서 고친다.
   - `12-PLAN-CHECK-ITER6.md`의 PASS는 유지하되, 이번 direct review의 blocker closure를 별도 `ITER7` 또는 `DIRECT-REVIEW-ITERATION3-FIX.md`로 남긴다.

2. **Wave 0A**
   - RTMW adapter는 `scores_133`를 visibility source로 쓴다.
   - `targetSource`는 kismam contract에만 canonical로 둔다.
   - grep gate 대신 AST test를 추가한다.

3. **Wave 0B**
   - `KeypointReport` validator는 `data`, `confidence`, `axisData`, `axisMask` 모두 검증한다.
   - `build_keypoint_report`는 첫 frame이 아니라 전체 frame availability를 본다.
   - mode1 size budget은 `keypointReport + referenceKeypointReport` 포함으로 측정한다.
   - `referenceKeypointReport` 저장은 `complete_analysis` kwarg로만 통과시킨다.

4. **Wave 1/2**
   - `KeypointOverlayProps`를 Wave 1부터 최종 shape로 만든다.
   - Wave 1은 `player` 없이 `frameIndex={0}`만 쓴다.
   - Wave 2는 같은 component에 `player`를 넘겨 `useEvent`를 켠다.
   - `jointAngles`는 result.tsx에서 `JointScore[] -> Record`로 한 번 변환한다.

## Recommended Technologies

- **Backend validation**: Python `dataclass(frozen=True)`, `typing.Literal`, `math.isfinite`, scoped Firestore validator. 새 dependency는 필요 없다.
- **Call-site verification**: Python `ast` module. grep은 멀티라인 Python 호출 검증에 맞지 않는다.
- **Numerical handling**: `numpy.clip`은 RTMW score clamp에만 사용하고, persisted JSON payload 직전에는 plain `math.isfinite`로 검증한다.
- **Frontend overlay**: `react-native-svg` 유지. Phase 12 규모에서는 Skia로 가기 전 `useMemo`, single-frame reshape, `React.memo`로 충분하다.
- **Video sync**: `expo-video` player를 render prop으로 KeypointOverlay에 넘기고, `useEvent`는 KeypointOverlay component body 안에서만 호출한다.
- **Persistence**: AsyncStorage key `@sunity:keypoint_overlay_enabled` 유지. default ON + lazy load 후 state update가 현재 계획대로 맞다.
- **Reference report**: Firestore reference doc에 `referenceKeypointReport`를 두고, analysis result mirror는 size gate 통과 시에만 유지한다. 장기적으로는 result doc에는 pointer만 두는 쪽이 더 안전하다.

## Final Assessment

3차 수정본은 실행 가능한 형태에 가까워졌다. 특히 2차에서 가장 위험했던 ghost field와 schema field count 문제는 상당히 정리됐다.

하지만 지금 바로 `/gsd-execute-phase 12`로 가는 것은 이르다. B1, B2, B3는 실행자가 plan대로 구현하면 실제 코드에서 바로 깨질 수 있는 문제다. H1-H4까지 같이 고치면 Phase 12는 꽤 안정적인 plan이 된다. 내가 승인 기준을 잡는다면 **B1-B3 + H1-H4 수정 후 재검토 없이 실행 가능**, 단 size budget test 결과가 700 KiB를 넘으면 `referenceKeypointReport` mirror 전략은 다시 결정해야 한다.
