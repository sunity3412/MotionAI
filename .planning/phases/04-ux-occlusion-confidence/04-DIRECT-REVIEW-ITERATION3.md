---
phase: 04-ux-occlusion-confidence
reviewer: Codex
date: 2026-06-13
scope: direct-plan-review-iteration-3
status: revise-before-execution
prior_review: 04-DIRECT-REVIEW-ITERATION2.md
response_reviewed: 04-DIRECT-REVIEW-ITERATION2-RESPONSE.md
reviewed_plans:
  - 04-00-PLAN.md
  - 04-01-PLAN.md
  - 04-02-PLAN.md
  - 04-03-PLAN.md
  - 04-05-PLAN.md
  - 04-PATTERNS.md
  - 04-RESEARCH.md
  - 04-UI-SPEC.md
external_search:
  repeated: false
  reason: "3차는 2차 response 반영분의 local contract/code drift 검토. 신규 외부 API/가격/버전 주장 없음."
---

# Phase 4 Direct Review - Iteration 3

## Executive Verdict

2차 response의 핵심 결정은 맞다.

- `result.joints3d`를 canonical location으로 정한 것에 동의한다.
- `result.aiSynthesisMeta.warnings`를 canonical warning surface로 정한 것도 맞다.
- `reference/{id}/versions/phase4_v1` + top-level mirror + rollback 방향도 맞다.
- R1 반박은 계속 수용한다. Phase 4에서 scoring promotion 기계는 넣지 않는다.

다만 `04-DIRECT-REVIEW-ITERATION2-RESPONSE.md`의 "잔재 0" 주장은 실제 active plan과 맞지 않는다. 중요한 잔재가 아직 남아 있고, 일부는 executor가 어느 계약을 따라야 하는지 헷갈리게 만든다.

최종 판단: **revise-before-execution 유지**. 큰 설계는 승인 가능하지만, 아래 BLOCKER/HIGH는 실행 전 문서 패치가 필요하다.

## Findings

### BLOCKER-1: warning surface migration이 active UI 문서까지 끝나지 않았다

Evidence:

- `04-DIRECT-REVIEW-ITERATION2-RESPONSE.md:23-24`는 canonical warning surface를 `result.aiSynthesisMeta.warnings`로 확정한다.
- `04-DIRECT-REVIEW-ITERATION2-RESPONSE.md:34`는 `result.warnings.includes` 잔재 0이라고 주장한다.
- 하지만 `04-02-PLAN.md:60`은 아직 `warnings.includes('ai_synthesis_failed')`를 key link로 둔다.
- `04-02-PLAN.md:282`도 done gate에서 `visible = warnings.includes('ai_synthesis_failed')`를 요구한다.
- `04-UI-SPEC.md:258`은 Firestore 분석 doc의 `warnings` 배열을 trigger로 정의한다.
- `04-UI-SPEC.md:413`은 `AccuracyLimitBadge`가 `warnings.includes('ai_synthesis_failed')` 단일 trigger라고 한다.
- `04-PATTERNS.md:841-844`는 `result.warnings?.includes('ai_synthesis_failed')` 예시를 그대로 제공한다.

Impact:

executor가 `04-02` action의 `hasSynthesisWarning(doc?.result, ...)` 지시를 따라가면 맞지만, key_links/done/UI-SPEC/PATTERNS가 반대 방향을 말한다. 특히 UI-SPEC과 PATTERNS는 frontend 구현자가 그대로 복사할 가능성이 높다. 그러면 badge가 안 뜨거나 존재하지 않는 `result.warnings` 필드를 추가하게 된다.

Recommendation:

아래를 모두 같은 표현으로 바꾼다.

```ts
visible={hasSynthesisWarning(doc?.result, 'ai_synthesis_failed')}

function hasSynthesisWarning(
  result: AnalysisResult | null | undefined,
  code: SynthesisWarningCode,
): boolean {
  return (result?.aiSynthesisMeta?.warnings ?? []).includes(code);
}
```

수정 대상:

- `04-02-PLAN.md` key_links, done, verification 문구
- `04-UI-SPEC.md` Surface 2 trigger + A-8
- `04-PATTERNS.md` AccuracyLimitBadge/result.tsx snippets
- `04-RESEARCH.md` warning code 예시 중 top-level warnings 언급

### BLOCKER-2: `AnalysisDoc.joints3d` stale wording이 04-01에 아직 남아 있다

Evidence:

- `04-01-PLAN.md:31`은 `AnalysisDoc.joints3d` 3-way lockstep이라고 한다.
- `04-01-PLAN.md:49`도 `app/src/types/analysis.ts`가 `AnalysisDoc joints3d` 필드를 제공한다고 한다.
- 반면 `04-01-PLAN.md:288-294`는 `AnalysisResult` 내부 필드로 올바르게 정정되어 있다.
- `04-01-PLAN.md:307`도 `AnalysisResult 내부, AnalysisDoc top-level 아님`이라고 말한다.
- 하지만 `04-01-PLAN.md:335`와 `04-01-PLAN.md:378`은 다시 `AnalysisDoc joints3d`라고 말한다.

Impact:

Wave 1 executor가 acceptance/done/success criteria를 기준으로 구현하면 top-level `AnalysisDoc.joints3d`를 추가할 수 있다. 그러면 2차에서 확정한 `result.joints3d` 계약이 다시 깨진다.

Recommendation:

`04-01-PLAN.md`의 모든 `AnalysisDoc joints3d` 표현을 `AnalysisResult.joints3d`로 바꾼다. `AnalysisDoc`에는 기존 `angles` quirk만 남긴다는 문구를 명시한다.

### BLOCKER-3: `inputs.keypoints_4ch`를 쓰면 좌표계는 `rtmw3d`가 아니라 `pole_aligned`에 가깝다

Evidence:

- `04-01-PLAN.md:280-286`은 `joints3d` source를 `inputs.keypoints_4ch[:, :, :3]`로 정하고 `space = "rtmw3d"`라고 한다.
- 현재 코드 `backend/shared/python/sunity_shared/analysis/pose_frame.py:325-351`의 `to_coco17_array()`는 `keypoints_3d_pole_aligned`에서 x/y/z를 읽어 `(T,17,4)`를 만든다.
- 현재 pipeline은 `backend/functions/pipeline/app.py:1005-1007`에서 `keypoints_4ch = to_coco17_array(pose_frames)`를 만든다.

Impact:

Firestore에 `space="rtmw3d"`라고 저장하지만 실제 값은 pole-aligned 좌표일 수 있다. 3D viewer, reference mirror, future metric/debug가 좌표계를 잘못 해석한다. 이건 단순 naming 문제가 아니라 mode1 reference/user alignment를 흔들 수 있다.

Recommendation:

둘 중 하나를 택한다.

- 권고 A: `inputs.keypoints_4ch[:, :, :3]`를 계속 쓰고 `space = "pole_aligned"`로 저장한다.
- 권고 B: `space = "rtmw3d"`를 유지하려면 `pose_frames[*].keypoints_3d`에서 `KEYPOINT_NAMES` 순서로 raw COCO-17 xyz를 직접 재구성한다.

내 판단은 A가 더 안전하다. 현재 pipeline의 angle/normalization 경로가 이미 pole-aligned array를 쓰고 있으므로, viewer도 같은 좌표계를 쓰는 편이 mode1 비교에서 덜 위험하다.

### BLOCKER-4: Wave 2 smoke checkpoint가 아직 구조적으로 auto task 앞에 있다

Evidence:

- `04-02-PLAN.md:109-154`는 첫 task가 `checkpoint:human-verify`다.
- 그 checkpoint 안에서 `04-02-PLAN.md:114-119`는 dependency install과 `PoseViewer3DSmokeScreen.tsx` 작성을 "Claude가 실행"한다고 한다.
- 실제 auto Task 1은 `04-02-PLAN.md:156-165`에서 뒤에 나온다.

Impact:

GSD executor가 `checkpoint:human-verify`를 blocking gate로 해석하면, 파일 생성과 dependency install이 일어나기 전에 사람 검증을 기다린다. 2차에서 지적한 "없는 smoke screen을 검증하라"는 문제가 문구상으로는 줄었지만, task 구조상 완전히 해결되지 않았다.

Recommendation:

checkpoint 앞에 실제 auto task를 만든다.

1. Task 0 auto: dependency install, postinstall 확인, `PoseViewer3DSmokeScreen.tsx` 생성, typecheck.
2. Task 0.5 checkpoint: EAS preview/실기기 smoke.
3. Task 1 auto: colors/joints/userAnalyses/AccuracyLimitBadge.
4. Task 2 auto: smoke pass 시 `result.tsx` integration.

human checkpoint 안에 "Claude가 실행"해야 하는 file write를 넣지 않는다.

### HIGH-1: 04-05가 "reference 재처리 = Gemini + mesh path"처럼 말하지만 G4 guard는 synthesis 0을 요구한다

Evidence:

- `04-05-PLAN.md:24`는 정은지 5영상이 "Wave 1 Gemini + Wave 3 cylindrical mesh" 신규 파이프라인으로 재처리된다고 한다.
- `04-05-PLAN.md:25`는 동시에 `is_reference=True`라 합성 trigger가 발동하지 않는다고 한다.
- `04-05-PLAN.md:158-162`도 `_reprocess_one(... synthesis_adapter=None)` 및 `is_reference=True`로 adapter 호출이 없어야 한다고 한다.

Impact:

문장만 보면 reference reprocess가 Gemini/mesh synthesis를 적용한다고 오해할 수 있다. 하지만 R1/G4 정책상 reference에는 synthesis 좌표를 주입하면 안 된다. 이 혼선은 reprocess script에서 fake adapter를 "호출하면 fail"로 만들지, 실제 Wave 1/3 adapter를 연결할지 결정할 때 중요하다.

Recommendation:

04-05 목적/ must-have를 이렇게 바꾼다.

- "Phase 4-compatible pipeline으로 재처리하되, `is_reference=True`에서는 synthesis adapters가 전부 guarded off다."
- "reference reprocess의 목적은 동일한 RTMW/normalization/schema path와 versioned write 검증이지, reference에 Gemini/mesh synthetic coordinates를 적용하는 것이 아니다."
- evaluate_4way의 cylindrical mesh 실험은 reference Firestore reprocess와 별도 integration gate로 분리한다.

### HIGH-2: reference `joints3d`를 mirror하겠다고 하지만 reprocess payload schema는 만들지 않는다

Evidence:

- `04-05-PLAN.md:178`은 top-level mirror 필드에 `joints3d / joints3dKeys / joints3dFrames / coordDim / space`를 포함한다.
- `04-05-PLAN.md:127-129`의 dry-run schema 검증 필드는 `angles`, `anglesJointKeys`, `anglesFrames`, `keypointReport`, `pipelineVersion`, `reprocessedAt`뿐이다.
- `04-05-PLAN.md:167-168`의 `_reprocess_one` 반환 dict도 같은 6개 중심이고 `joints3d` 계열이 없다.
- `04-UI-SPEC.md:156-159`는 mode1에서 `referenceJoints={refMotion?.joints3d}`를 기대한다.

Impact:

Wave 5가 계획대로 실행되어도 reference doc에 3D skeleton 데이터가 없을 수 있다. 그러면 mode1 3D viewer는 사용자 skeleton만 보여주거나 reference skeleton을 항상 null로 처리한다. 이게 의도라면 UI-SPEC에서 빼야 하고, 의도가 아니라면 Wave 5 schema가 부족하다.

Recommendation:

둘 중 하나를 명시한다.

- mode1 reference 3D 비교를 Phase 4에 포함한다면: `_reprocess_one` payload에 `joints3d`, `joints3dKeys`, `joints3dFrames`, `coordDim`, `space`를 추가하고 schema gate에도 넣는다. source/space는 04-01과 동일하게 맞춘다.
- Phase 4 MVP에서는 사용자 skeleton만 보여준다면: `04-UI-SPEC.md`와 PATTERNS의 `referenceJoints={refMotion?.joints3d}`를 제거하고 Wave 5 mirror 목록에서도 `joints3d` 계열을 빼거나 deferred로 표시한다.

내 의견은 reference 3D도 넣는 쪽이다. 이미 Wave 5가 top-level mirror를 하기로 했고, mode1 비교 UX에서 reference skeleton이 없으면 3D viewer의 가치가 절반으로 줄어든다.

### HIGH-3: PATTERNS/RESEARCH의 superseded banner만으로는 충분하지 않다

Evidence:

- `04-PATTERNS.md:7`과 `04-RESEARCH.md:7`에는 superseded banner가 추가됐다.
- 하지만 `04-01-PLAN.md:127-130`과 `04-01-PLAN.md:238-240`은 여전히 PATTERNS/RESEARCH의 구체 섹션을 read_first로 요구한다.
- `04-PATTERNS.md:86-93`은 `SynthesisAdapter` 반환을 tuple로 보여준다.
- `04-PATTERNS.md:304-336`은 `_call_synthesis_adapter`가 tuple 또는 `None`을 반환하는 예시를 보여준다.
- `04-PATTERNS.md:338-350`은 `extra_warnings`와 `dataclasses.replace` 주입 예시를 제공한다.
- `04-RESEARCH.md:260-270`, `04-RESEARCH.md:494-518`, `04-RESEARCH.md:531-532`도 old tuple/top-level warning 흐름을 보여준다.

Impact:

executor가 "read_first"로 특정 old snippets를 읽고 그대로 복사하면, 최신 plan과 반대되는 구현이 나온다. 상단 banner는 방어막이지만, active plan이 그 stale section을 직접 읽으라고 하면 여전히 위험하다.

Recommendation:

최소 수정이 아니라 실제 snippets를 고친다.

- `SynthesisAdapter` 예시는 `-> SynthesisResult`.
- `_call_synthesis_adapter` 예시는 `SynthesisResult(status="skipped"|"failed")`.
- warning injection은 `ai_synthesis_meta["warnings"]`로.
- result.tsx badge 예시는 `hasSynthesisWarning`.
- `reshapeJoints3d(angles...)`는 `reshapePose3dData(joints3d...)`로.

### HIGH-4: 04-05의 versioned write test가 path/collection 검증으로는 약하다

Evidence:

- `04-05-PLAN.md:132-138`은 AST에서 `"phase4_v1"` 상수만 찾는다.
- `04-05-PLAN.md:260-269` acceptance도 `"phase4_v1"` constant 존재 중심이다.
- `reference/{motion_id}/versions/phase4_v1`를 실제로 쓰는지, `referenceMotions`로 회귀하지 않았는지, top-level mirror가 같은 collection에 merge되는지는 테스트가 직접 검증하지 않는다.

Impact:

2차 BLOCKER-2의 핵심은 collection path drift였다. 그런데 테스트가 `"phase4_v1"`만 보면 잘못된 collection에도 통과한다.

Recommendation:

fake Firestore client를 둬서 실제 call path를 검증한다.

- `_write_versioned(fake, "ref-sideway-spin", payload)` 후 recorded path가 `("reference", "ref-sideway-spin", "versions", "phase4_v1")`인지 assert.
- `_flip_active_pointer()`가 `reference/{id}` top-level merge를 수행하는지 assert.
- 소스 검사도 유지한다면 `"referenceMotions"` 문자열이 reprocess/rollback scripts에 없음을 assert한다.

### MEDIUM-1: `SynthesisResult.warnings`와 `AiSynthesisMeta.warnings`의 타입 의미가 섞일 수 있다

Evidence:

- `04-01-PLAN.md:147`은 `SynthesisResult.warnings: tuple[str, ...]`.
- `04-01-PLAN.md:156-161`은 raw reason으로 `gemini_api_error`, `gemini_parse_error`, `g4_reference_guard` 등을 넣는다.
- `04-01-PLAN.md:171-172`의 TS `SynthesisWarningCode`는 `ai_synthesis_failed | ai_synthesis_partial`만 정의한다.
- `04-01-PLAN.md:274-275`는 canonical UI warning으로 failed/partial만 meta에 추가한다.

Impact:

executor가 `SynthesisResult.warnings`를 그대로 `aiSynthesisMeta.warnings`에 복사하면 TS union과 contract가 깨진다. 반대로 raw reason을 버리면 debug가 어려워진다.

Recommendation:

필드 의미를 분리한다.

- `aiSynthesisMeta.warnings`: UI/contract code only (`ai_synthesis_failed`, `ai_synthesis_partial`)
- `aiSynthesisMeta.errorCode?: string`
- `aiSynthesisMeta.internalWarnings?: string[]` 또는 `debugWarnings?: string[]`

MVP에서는 `errorCode` 하나만 둬도 충분하다.

### MEDIUM-2: mesh exclusion test가 04-01의 singleton adapter 설계와 어긋난다

Evidence:

- `04-01-PLAN.md:303`은 `_get_synthesis_adapter()`를 GeminiViewReasoner lazy singleton으로 정의한다.
- `04-03-PLAN.md:253-254`는 `_get_synthesis_adapter()`가 "active adapter chain"을 반환하고 `CylindricalMeshAdapter`가 포함되지 않음을 단언하라고 한다.

Impact:

executor가 테스트를 만족시키려고 불필요한 adapter chain abstraction을 만들 수 있다.

Recommendation:

04-03 test 문구를 04-01과 맞춘다.

- default: `_get_synthesis_adapter()` returns Gemini adapter only.
- `SYNTHESIS_MESH_ENABLED` unset/0이면 returned adapter is not `CylindricalMeshAdapter`.
- composite chain은 도입하지 않는다. 나중에 필요해지면 별도 phase에서 추가한다.

### MEDIUM-3: UI-SPEC status가 아직 draft다

Evidence:

- `04-UI-SPEC.md:4`는 `status: draft`.
- `04-02-PLAN.md:81`은 실행 전 UI-SPEC을 approved로 기록하라고 한다.

Impact:

문서 흐름상 큰 기능 버그는 아니지만, UI executor가 design contract 승인 전 작업인지 후 작업인지 헷갈릴 수 있다.

Recommendation:

3차 patch 후 `status: approved`로 올리거나, 아직 미승인이면 04-02의 "approved로 기록할 것" 문구를 checkpoint로 남긴다. 현재 상태는 둘 중 하나가 아니다.

## Resolved Since Iteration 2

좋아진 부분도 명확하다.

- R1 non-scoring hard wall은 이제 plan 전반의 주요 문구에 반영됐다.
- 04-01의 core behavior는 `SynthesisResult` status 기반으로 정리됐다.
- `joints3d` source를 존재하지 않는 `keypoints_3d` 변수에서 `inputs.keypoints_4ch`로 바꾼 방향은 맞다. 다만 좌표계 label을 고쳐야 한다.
- 04-05의 collection 방향은 `reference`로 수정됐다.
- Wave 3b를 Wave 2/5 blocker로 두지 않는 결정은 여전히 맞다.
- 04-03에 mesh accidental activation test를 추가한 방향도 맞다. 다만 chain/singleton 표현만 정리하면 된다.

## Required Patch List Before Execution

1. `result.warnings` / doc `warnings` / `warnings.includes` 잔재를 active plan/UI-SPEC/PATTERNS에서 제거하고 `hasSynthesisWarning(result, code)`로 통일.
2. `04-01-PLAN.md`의 `AnalysisDoc.joints3d` stale wording을 전부 `AnalysisResult.joints3d`로 수정.
3. `joints3d` source가 `inputs.keypoints_4ch`이면 `space="pole_aligned"`로 바꾸거나, `space="rtmw3d"`를 유지하려면 raw `PoseFrame.keypoints_3d`에서 재구성.
4. `04-02-PLAN.md`의 첫 human checkpoint 앞에 실제 auto Task 0을 만들고, checkpoint 안의 file write/install 지시를 제거.
5. `04-05-PLAN.md`에서 reference reprocess는 synthesis guarded-off path라고 명확히 쓰고, Gemini/mesh synthesis 적용처럼 읽히는 문구를 제거.
6. reference 3D viewer를 포함할지 결정. 포함한다면 04-05 schema/build/mirror에 `joints3d` 계열을 필수로 추가.
7. PATTERNS/RESEARCH old snippets를 실제 최신 contract로 고친다. 상단 superseded banner만으로는 부족하다.
8. 04-05 versioned write test를 fake Firestore path assertion으로 강화.
9. `SynthesisResult.warnings` raw reason과 `AiSynthesisMeta.warnings` UI code를 분리.
10. 04-03 mesh exclusion test를 singleton adapter 설계에 맞게 단순화.

## Execution Readiness

아직 실행하면 안 된다. 이유는 큰 아키텍처 반대가 아니라 "closure 문서가 말하는 완료 상태"와 "executor가 읽을 active plan"이 다르기 때문이다.

3차 기준 내 의견은 다음과 같다.

**Phase 4 설계 방향은 승인 가능. 단, active plan/read_first/UI-SPEC/PATTERNS의 계약 drift를 제거한 뒤 실행해야 한다.**

특히 좌표계(`pole_aligned` vs `rtmw3d`)와 warning surface(`aiSynthesisMeta.warnings`)는 구현 후 바꾸기 번거롭다. 지금 고정하는 편이 훨씬 싸다.
