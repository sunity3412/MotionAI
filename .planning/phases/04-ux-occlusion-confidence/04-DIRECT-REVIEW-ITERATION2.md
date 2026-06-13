---
phase: 04-ux-occlusion-confidence
reviewer: Codex
date: 2026-06-13
scope: direct-plan-review-iteration-2
status: revise-before-execution
prior_review: 04-DIRECT-REVIEW.md
response_reviewed: 04-DIRECT-REVIEW-RESPONSE.md
reviewed_plans:
  - 04-00-PLAN.md
  - 04-01-PLAN.md
  - 04-02-PLAN.md
  - 04-03-PLAN.md
  - 04-04-PLAN.md
  - 04-05-PLAN.md
  - 04-PATTERNS.md
  - 04-RESEARCH.md
  - 04-UI-SPEC.md
---

# Phase 4 Direct Review - Iteration 2

## Executive Verdict

`04-DIRECT-REVIEW-RESPONSE.md`의 방향은 대체로 맞다.

- R1 반박은 수용한다. Phase 4 MVP에서는 `scoringEligible`, promotion gate, scoring promotion path를 넣지 않는 편이 더 안전하다. Phase 4 synthesis output은 영구적으로 non-scoring이며, 점수 반영은 별도 phase에서 새 평가/검증/롤백 계약으로 다루는 것이 맞다.
- R3 escalation도 맞다. 현재 Firestore/analysis payload에는 3D viewer가 바로 쓸 수 있는 `T x 17 x 3` 데이터 소스가 없으므로 `joints3d` 계약을 Phase 4에서 명시적으로 추가해야 한다.
- R2/R4/R5/R7/R8/R9에 대한 대응도 개념적으로는 좋아졌다. 특히 `SynthesisResult` 상태 계약, Wave 3a/3b 분리, activation 기본 OFF, AI badge 문구 수정은 1차 리뷰의 핵심 리스크를 줄인다.

다만 아직 실행 전 수정이 필요하다. 남은 문제는 큰 설계 반대가 아니라, executor가 서로 다른 계약을 보고 엇갈리게 구현할 가능성이 높은 문서 불일치다. 현재 상태로 실행하면 Phase 4는 backend에는 저장되지만 UI에서 못 읽거나, UI가 읽는 위치와 backend가 쓰는 위치가 달라지는 식으로 실패할 수 있다.

최종 판단: **revise-before-execution**. 범위는 1차보다 작지만, 아래 BLOCKER는 실행 전에 고정해야 한다.

## Findings

### BLOCKER-1: `joints3d` 저장 위치가 04-01과 04-02에서 서로 다르다

Evidence:

- `04-01-PLAN.md:257-265`는 `payload["joints3d"]`, `payload["joints3dKeys"]`, `payload["joints3dFrames"]`, `payload["coordDim"]`, `payload["space"]`를 top-level에 저장하라고 한다.
- `04-01-PLAN.md:287-291`도 `AnalysisDoc` top-level 필드로 `joints3d?`, `joints3dKeys?`, `joints3dFrames?`, `coordDim?`, `space?`를 추가하라고 한다.
- 반면 `04-02-PLAN.md:202-230`과 `04-02-PLAN.md:319-324`는 `doc.result.joints3d`, `doc.result.joints3dKeys`, `doc.result.joints3dFrames`를 읽는다.
- 현재 `app/src/types/analysis.ts`도 `angles`는 `AnalysisDoc` top-level이고, `AnalysisResult`에는 `joints3d`가 없다.

Impact:

backend와 UI가 각각 계획대로 구현되면 3D viewer는 빈 데이터로 떨어진다. 이건 기능 실패다.

Recommendation:

하나만 정해야 한다. 내 권고는 **UI 소비 데이터이므로 `result` 내부에 둔다**는 쪽이다.

- Backend: `payload["result"]["joints3d"]`, `payload["result"]["joints3dKeys"]`, `payload["result"]["joints3dFrames"]`, `payload["result"]["coordDim"]`, `payload["result"]["space"]`.
- Frontend: `AnalysisResult`에 위 필드를 추가하고 `doc.result`에서만 읽는다.
- 만약 `angles`와 같은 패턴을 유지하려면 반대로 04-02를 모두 `doc.joints3d`로 바꿔야 한다. 어느 쪽이든 04-01/04-02/04-UI-SPEC이 같은 위치를 말해야 한다.

### BLOCKER-2: 04-05가 잘못된 reference collection을 표준 경로처럼 사용한다

Evidence:

- `04-05-PLAN.md:24`, `04-05-PLAN.md:43-50`, `04-05-PLAN.md:170-179`는 `referenceMotions/{id}/versions/phase4_v1`를 사용한다.
- 현재 프로젝트의 canonical path는 `reference/{motionId}`다. 이 경로는 `.planning/ROADMAP.md`, `docs/contract.md`, `app/src/lib/referenceMotions.ts`, `backend/shared/python/sunity_shared/models.py`, `backend/shared/python/sunity_shared/firestore_admin.py`에서 일관되게 쓰인다.

Impact:

Wave 5가 `referenceMotions`에 쓰면 기존 앱/파이프라인은 그 데이터를 읽지 않는다. `activeVersion`을 업데이트해도 현재 consumer가 해당 collection을 보지 않으면 효과가 없다.

Recommendation:

04-05를 아래 계약으로 고정한다.

- Version doc: `reference/{motionId}/versions/phase4_v1`
- Active pointer: `reference/{motionId}.activeVersion = "phase4_v1"`
- MVP에서는 active version resolver를 앱/백엔드 전부에 추가하기보다, 5개 레퍼런스가 모두 통과한 뒤 selected fields를 top-level `reference/{motionId}`에 mirror한다.
- Rollback은 이전 top-level snapshot과 `activeVersion`을 함께 복원한다.

이렇게 해야 기존 consumer를 대규모로 바꾸지 않고도 Phase 4 reference baseline을 실제 서비스 경로에 반영할 수 있다.

### BLOCKER-3: `ai_synthesis_failed` warning의 저장 위치와 UI trigger가 불일치한다

Evidence:

- `04-02-PLAN.md:60`과 `04-02-PLAN.md:326`은 `doc?.result?.warnings?.includes("ai_synthesis_failed")`로 `AccuracyLimitBadge`를 켠다.
- 현재 `AnalysisResult` 타입에는 top-level `warnings`가 없다.
- `04-01-PLAN.md`의 설명은 `dataclasses.replace(profile, extra_warnings=...)` 계열로 warning을 추가하는 흐름에 가깝다. 이 경우 warning은 `bodyComparisonReport.warnings` 같은 report 내부로 들어갈 가능성이 높다.

Impact:

AI synthesis 실패가 발생해도 UI badge가 안 뜨거나, TypeScript에서 없는 필드를 참조하게 된다. Phase 4의 사용자 신뢰도 표시 목적이 깨진다.

Recommendation:

warning surface를 하나로 정한다.

내 권고:

- `result.aiSynthesisMeta.warnings?: SynthesisWarningCode[]`를 canonical warning 위치로 둔다.
- UI는 `hasSynthesisWarning(result)` helper로 `result.aiSynthesisMeta.warnings`, 필요 시 legacy report warnings를 함께 본다.
- global `result.warnings`를 새로 만들 거라면 04-01 backend payload, `AnalysisResult`, normalizer, UI trigger를 모두 같은 필드로 맞춘다.

### BLOCKER-4: 04-01의 `joints3d` source/validator 설명이 현재 코드와 맞지 않는다

Evidence:

- `04-01-PLAN.md:301-302`는 `_process`의 `keypoints_3d`를 사용한다고 설명한다.
- 현재 pipeline에는 `keypoints_3d` ndarray가 아니라 `_VideoAnalysisInputs.keypoints_4ch`가 있다. shape은 `(T, 17, 4)`이고, `to_coco17_array(pose_frames)`에서 만들어진다.
- `04-01-PLAN.md:295`는 `joints3d is not None: _validate_flat_dict_no_nested_array 우회(스칼라 list)`라고 한다. 반면 must-have는 Firestore flat payload validator를 통과해야 한다고 한다.

Impact:

executor가 존재하지 않는 변수명을 따라가거나 validator를 우회하면 저장 계약과 테스트가 흔들린다.

Recommendation:

04-01을 현재 코드 기준으로 고정한다.

- Source: `inputs.keypoints_4ch[:, :, :3]`에서 `T x 17 x 3`를 derive한다.
- Keys: COCO-17 keypoint order를 명시한다. angle용 `JOINT_KEYS`는 8개 관절용이므로 `joints3dKeys`에 쓰면 안 된다.
- Validator: `_validate_joints3d_payload(joints3d, joints3dKeys, joints3dFrames, coordDim, space)`를 별도로 둔다.
- Checks: flat length equals `frames * len(keys) * coordDim`, finite numbers only, `coordDim == 3`, `space in {"normalized_image", "camera", "world"}` 같은 enum 검증을 넣는다.

### HIGH-1: `identify_occlusion_targets`와 `identify_synthesis_targets` 이름이 섞여 있다

Evidence:

- `04-01-PLAN.md`는 `identify_occlusion_targets`를 새 canonical 함수로 쓴다.
- `04-00-PLAN.md`, `04-03-PLAN.md`, `04-05-PLAN.md`, `04-PATTERNS.md`, `04-RESEARCH.md`에는 아직 `identify_synthesis_targets`가 남아 있다.

Impact:

테스트 파일명/함수명/implementation prompt가 갈라질 수 있다.

Recommendation:

하나로 통일한다. 내 권고는 `identify_occlusion_targets`다. 함수가 하는 일이 “합성 대상” 일반이 아니라 occlusion-driven target selection이므로 이름이 더 정확하다.

### HIGH-2: 04-00의 Wave 0 테스트 기대값이 `SynthesisResult` 계약과 충돌한다

Evidence:

- `04-01-PLAN.md:249`는 reference input에서 `SynthesisResult(status="skipped")`를 기대한다.
- `04-00-PLAN.md:138-140`, `04-00-PLAN.md:158`은 아직 guard가 `None`을 반환한다고 적는다.

Impact:

Wave 0 테스트를 먼저 구현하면 Wave 1 implementation과 즉시 충돌한다.

Recommendation:

04-00 테스트 spec을 `None` 기반에서 `SynthesisResult(status="skipped" | "failed" | "disabled")` 기반으로 업데이트한다.

### HIGH-3: 04-PATTERNS와 04-RESEARCH가 여전히 tuple/None old contract를 안내한다

Evidence:

- `04-PATTERNS.md:69-90`, `04-PATTERNS.md:304-333`은 adapter가 tuple 또는 `None`을 반환하는 패턴을 보여준다.
- `04-RESEARCH.md:258-268`, `04-RESEARCH.md:495-516`도 같은 old contract를 사용한다.
- `04-PATTERNS.md:512-535`는 `reshapeJoints3d(angles...)`처럼 현재 결정과 맞지 않는 이름/데이터 소스를 쓴다.

Impact:

04-01이 `read_first`로 PATTERNS/RESEARCH를 참조하면 executor가 최신 plan보다 오래된 pattern을 따라갈 가능성이 있다.

Recommendation:

둘 중 하나를 반드시 한다.

- 더 좋음: PATTERNS/RESEARCH의 adapter examples를 `SynthesisResult` 기반으로 고친다.
- 최소: 해당 섹션 상단에 “superseded by 04-DIRECT-REVIEW-RESPONSE and 04-01 SynthesisResult contract”라고 명시하고 executor가 오래된 tuple contract를 쓰지 못하게 한다.

### HIGH-4: 04-02의 Wave 2 smoke checkpoint 순서가 실행 불가능하다

Evidence:

- `04-02-PLAN.md:109-152`는 blocking checkpoint를 Task 1보다 앞에 둔다.
- 그 checkpoint는 `PoseViewer3DSmokeScreen.tsx`가 “Task 0에서 생성됨”이라고 말하지만, 실제 Task 0이 없다.

Impact:

사람이 smoke test를 하라는 지점에서 아직 테스트 화면이 없다.

Recommendation:

순서를 바꾼다.

- Task 1a: dependency install
- Task 1b: `PoseViewer3DSmokeScreen.tsx` 생성
- Blocking checkpoint: simulator/device에서 GL render 확인
- Task 2+: result integration

### HIGH-5: `AiSynthesisMeta` normalizer가 04-01의 감사/비용 필드를 보존하지 않는다

Evidence:

- `04-01-PLAN.md:170-178`은 `modelId`, `modelVersion`, `promptHash`, cost counters 등 감사/비용 필드를 추가한다.
- `04-02-PLAN.md:216-227`의 frontend normalizer는 `status`, `model`, `updatedAt`, `errorCode` 정도만 보존한다.

Impact:

UI/API 타입이 backend payload보다 좁아지고, 나중에 audit/cost 표시나 debug가 필요할 때 데이터가 client boundary에서 사라진다.

Recommendation:

`AiSynthesisMeta` TS type을 backend contract와 맞춘다. UI에서 당장 쓰지 않는 필드도 optional로 보존한다.

### MEDIUM-1: Wave 3b mesh placeholder가 `applied` 상태를 낼 수 있으므로 default OFF 테스트가 필요하다

Evidence:

- `04-03-PLAN.md:121-130`의 `CylindricalMeshAdapter` placeholder는 `SynthesisResult(status="applied", ...)`를 반환한다.
- `04-03-PLAN.md:216-218`은 3b가 skipped면 `SYNTHESIS_MESH_ENABLED=0` default를 유지한다고 한다.

Impact:

placeholder가 실수로 adapter chain에 등록되면 non-authoritative mesh 결과가 applied로 저장될 수 있다.

Recommendation:

`_get_synthesis_adapter`가 `SYNTHESIS_MESH_ENABLED` 없이는 mesh adapter를 절대 포함하지 않는다는 unit test를 추가한다. 3b가 skipped인 동안 mesh path는 imported 되어도 active adapter chain에 들어가면 안 된다.

### MEDIUM-2: 04-UI-SPEC code block에 prop typo가 남아 있다

Evidence:

- `04-UI-SPEC.md:156-159`의 snippet에 `ipsf ViolationFrames={iпsfViolationFrames}`가 있다. 공백과 Cyrillic-looking 문자가 섞여 있다.

Impact:

문서 snippet이 그대로 복사되면 컴파일 실패 또는 prop 누락이 발생한다.

Recommendation:

`ipsfViolationFrames={ipsfViolationFrames}`로 수정한다.

### MEDIUM-3: 04-01 objective에 아직 “분석 정확도 향상” 표현이 남아 있다

Evidence:

- `04-01-PLAN.md:83`은 “분석 정확도가 향상되는 수직 슬라이스”라고 한다.
- 같은 문서의 핵심 결정은 “Phase 4 synthesis output is permanently non-scoring”이다.

Impact:

정확도 향상이라는 표현은 scoring/metric improvement처럼 읽힐 수 있다. Phase 4의 실제 목표는 score improvement가 아니라 confidence explanation, occlusion transparency, 3D inspection이다.

Recommendation:

표현을 “사용자 표시 신뢰도와 가림 구간 설명이 향상되는 수직 슬라이스” 또는 “점수 계산은 변경하지 않고 표시 신뢰도를 높이는 수직 슬라이스”로 바꾼다.

## Response Judgment

### R1

Response의 partial rebuttal을 수용한다.

내 2차 의견은 다음과 같다.

- Phase 4에서 `scoringEligible`을 넣지 않는다.
- promotion machinery도 넣지 않는다.
- scoring path와 synthesis path를 영구 분리한다.
- 나중에 scoring 반영을 검토하려면 새 phase에서 metric eval, bias audit, rollback, reference migration, UAT를 다시 정의한다.

즉, R1은 “반박 수용”이 맞다. 다만 그 결정을 모든 plan 문서의 wording과 tests에 끝까지 반영해야 한다.

### R3

Response의 escalation을 수용한다.

단, `joints3d` 추가 방향만으로는 부족하다. 저장 위치, source variable, key order, validator, frontend type 위치가 아직 서로 맞지 않는다. R3는 “escalate 완료”가 아니라 “계약 정합성 패치 후 완료”로 보는 게 맞다.

### R4/R5

Wave 3a smoke와 Wave 3b mesh 분리는 적절하다. Video generation adapter default OFF도 맞다.

남은 요구는 accidental activation 방지다. placeholder, mesh, video generation path가 import되는 것과 active scoring/analysis path에 붙는 것은 다르다. env flag 없이는 active adapter chain에 들어가지 않는 테스트가 있어야 한다.

### R7

AI badge copy 수정은 충분히 좋아졌다. “AI가 진실”처럼 보이던 표현은 빠졌다.

남은 것은 copy 문제가 아니라 warning trigger 위치 문제다.

### R8

manual GL smoke checkpoint를 강화한 방향은 맞다. 다만 checkpoint를 테스트 화면 생성 뒤로 옮겨야 한다.

## Required Patch List Before Execution

1. `joints3d` canonical location 결정: 권고는 `result` 내부.
2. `ai_synthesis_failed` canonical warning location 결정: 권고는 `result.aiSynthesisMeta.warnings`.
3. `joints3d` source를 `inputs.keypoints_4ch[:, :, :3]` 기반으로 수정하고 별도 validator를 추가.
4. `referenceMotions`를 `reference`로 전부 수정하고, active version mirror/rollback 전략을 04-05에 명시.
5. `identify_synthesis_targets` 잔여 참조를 `identify_occlusion_targets`로 통일.
6. 04-00 테스트 기대값을 `None`에서 `SynthesisResult(status=...)`로 수정.
7. 04-PATTERNS/04-RESEARCH의 old tuple contract를 최신 계약으로 수정하거나 superseded 처리.
8. 04-02 smoke checkpoint를 smoke screen 생성 뒤로 이동.
9. `AiSynthesisMeta` TS normalizer가 backend audit/cost fields를 보존하도록 확장.
10. 04-UI-SPEC prop typo와 04-01 objective wording을 정리.

## Execution Readiness

이 패치들이 반영되면 Phase 4는 실행 가능한 계획으로 보인다.

현재 가장 중요한 판단은 R1이다. 여기서는 1차 리뷰의 promotion 제안을 철회하고 response의 판단을 따른다. Phase 4의 기술적 가치는 score improvement가 아니라, occlusion/low-confidence 상황을 사용자가 이해하고 검토할 수 있게 만드는 데 있다. 그 목표라면 non-scoring hard wall이 가장 안전하고 구현 리스크도 낮다.

따라서 남은 리뷰 결론은 다음과 같다.

**설계 방향은 승인 가능. 실행 전 계약 정합성 패치가 필요.**
