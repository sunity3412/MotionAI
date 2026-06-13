---
phase: 04-ux-occlusion-confidence
reviewer: Codex
date: 2026-06-13
scope: direct-plan-review-iteration-4
status: revise-before-execution
prior_review: 04-DIRECT-REVIEW-ITERATION3.md
response_reviewed: 04-DIRECT-REVIEW-ITERATION2-RESPONSE.md#iteration-3-response
external_search:
  repeated: false
  reason: "4차는 3차 response 반영분의 local plan/code-contract drift 검토. 신규 외부 API/가격/버전 판단 없음."
reviewed_plans:
  - 04-01-PLAN.md
  - 04-02-PLAN.md
  - 04-03-PLAN.md
  - 04-04-PLAN.md
  - 04-05-PLAN.md
  - 04-UI-SPEC.md
  - 04-PATTERNS.md
  - 04-RESEARCH.md
---

# 4차 직접 리뷰 — Phase 4

## 결론

**판정: revise-before-execution 유지.**

3차 response 에서 큰 축은 실제로 좋아졌다. 특히 `AnalysisDoc.joints3d` → `AnalysisResult.joints3d`, `space="pole_aligned"`, Wave 2 checkpoint reorder, UI-SPEC 의 canonical warning trigger 는 대부분 반영됐다. 다만 아직 실행 승인하면 안 된다. 남은 문제는 잔여 표현 수준이 아니라, executor 가 서로 다른 계약을 동시에 구현하게 만드는 active plan/read path 충돌이다.

4차 기준 차단 영역은 좁아졌다.

- 04-05 reference reprocess 가 **"Gemini + cylindrical mesh 신규 파이프라인"** 과 **"is_reference=True 이므로 합성 호출 0"** 을 동시에 요구한다.
- 04-05/UI-SPEC 은 reference `joints3d` 를 소비·mirror 하겠다고 하지만, 04-05 payload schema/reprocess 반환에는 `joints3d` 가 없다.
- 04-01/04-05 의 `read_first` 가 아직 구 tuple/None/`extra_warnings`/`referenceMotions` 패턴을 구현 기준으로 다시 읽게 만든다.

## 3차 대비 해결 확인

1. **R3 좌표계 escalated 이슈는 사용자 분석 결과 경로 기준 해결됨.**  
   `backend/shared/python/sunity_shared/analysis/pose_frame.py:325-328` 은 `to_coco17_array()` 가 `keypoints_3d_pole_aligned` 에서 산출된다고 명시한다. 04-01 은 이제 `inputs.keypoints_4ch[:, :, :3]` 를 source 로 쓰고 `space = "pole_aligned"` 로 저장하라고 지시한다 (`04-01-PLAN.md:280-285`).

2. **`AnalysisDoc.joints3d` stale 표현은 04-01 주요 경로에서 해결됨.**  
   read hint 가 `AnalysisResult 185-224` 를 보며 (`04-01-PLAN.md:131`), Firestore 저장도 `payload["result"]["joints3d"]` 를 명시한다 (`04-01-PLAN.md:264`).

3. **Wave 2 checkpoint 구조는 핵심 차단점이 해결됨.**  
   `04-02-PLAN.md:109-135` 가 먼저 deps install + smoke screen 생성 auto task 를 수행하고, 그 뒤 `04-02-PLAN.md:137-157` 에 blocking 실기기 checkpoint 가 온다.

4. **UI-SPEC 의 대표 warning trigger 는 canonical surface 로 수정됨.**  
   `04-UI-SPEC.md:258` 이 `result.aiSynthesisMeta.warnings` + `hasSynthesisWarning(...)` 를 지시한다.

## R1/R3 상태

- **R1 반박 유지:** Phase 4 합성 결과는 scoring promote 근거가 아니며, `coco_array`/DTW/KIS-MAM 입력을 건드리지 않는 non-scoring hardwall 이 맞다. 04-01 이 "합성 output 은 KeypointReport/aiSynthesisMeta/joints3d 에만 흐름 — coco_array 는 절대 변경 금지" 라고 명시한다 (`04-01-PLAN.md:278`). 이 방향은 승인한다.
- **R3 escalate 는 절반 해결:** 사용자 분석 결과 저장 경로와 좌표계는 해결됐지만, reference 5영상 재처리 쪽의 `joints3d` 생성/검증/mirror 가 아직 비어 있다. UI 는 `refMotion?.joints3d` 를 기대한다 (`04-UI-SPEC.md:156-158`).

## Findings

### BLOCKER-1 — 04-05 reference reprocess 계약이 아직 자기모순이다

**근거**

- `04-05-PLAN.md:24` 는 정은지 5영상이 "Wave 1 Gemini + Wave 3 cylindrical mesh" 신규 파이프라인으로 재처리된다고 쓴다.
- `04-05-PLAN.md:59-60` 도 "Gemini view reasoning + Wave 3 cylindrical mesh" 로 reference 5영상을 재처리한다고 반복한다.
- 반면 `04-05-PLAN.md:25` 는 `is_reference=True` 이므로 합성 트리거가 발동하지 않는다고 한다.
- 구현 지시도 `_reprocess_one` 에서 `synthesis_adapter` 를 호출하지 말라고 한다 (`04-05-PLAN.md:158-162`).

**위험**

executor 가 두 방향 중 하나를 임의 선택하게 된다. reference reprocess 에 Gemini/mesh 합성을 실제 적용하면 G4 guard 와 R1 non-scoring 정책을 깨고, 반대로 합성을 호출하지 않으면 `04-05` 의 목적/acceptance 문구가 거짓이 된다. 이 모순은 테스트로도 명확히 잡히지 않는다. fake adapter test 는 "호출 0" 만 증명하고, "Gemini+mesh 신규 파이프라인" 문구의 실행 여부는 검증하지 않는다.

**수정 방안**

04-05 의 reference reprocess 목적을 다음처럼 좁혀야 한다.

- "Phase 4-compatible reference reprocess: RTMW/pose extraction + keypointReport + angles + joints3d payload/schema/versioned write. `is_reference=True` 이므로 Gemini/mesh synthesis 는 호출하지 않는다."
- cylindrical mesh/evaluate_4way 는 reference Firestore migration 과 분리한다. `evaluate_4way` 실험은 POSE-03-g 평가 산출물이며, reference active document 에 synthetic coordinates 를 쓰는 단계가 아니다.

### BLOCKER-2 — 04-05 는 reference `joints3d` 를 mirror 하겠다고 하지만 payload 생성/schema 가 없다

**근거**

- dry-run schema 는 `angles`, `anglesJointKeys`, `anglesFrames`, `keypointReport`, `pipelineVersion`, `reprocessedAt` 6개만 검증한다 (`04-05-PLAN.md:123-129`).
- `_reprocess_one` 반환 dict 도 동일하게 6개만 포함한다 (`04-05-PLAN.md:167-168`).
- 그런데 active pointer flip 은 top-level mirror 에 `joints3d / joints3dKeys / joints3dFrames / coordDim / space` 를 포함하라고 한다 (`04-05-PLAN.md:178`).
- UI-SPEC 은 mode1 에서 `referenceJoints={refMotion?.joints3d}` 를 넘긴다 (`04-UI-SPEC.md:156-158`).

**위험**

reference 3D overlay 가 null 로 떨어지거나, flip 단계에서 존재하지 않는 필드를 mirror 하려다 실패한다. 더 나쁜 경우, 사용자 분석 결과에는 `result.joints3d` 가 있고 reference 에는 없어 mode1 3D 비교가 반쪽 UI 로 배포된다.

**수정 방안**

권장 수정은 `joints3d` 를 04-05 payload 에 포함하는 것이다.

- `_reprocess_one`: `to_coco17_array(pose_frames)[:, :, :3]` 를 flat list 로 저장.
- `_validate_payload_schema`: `joints3d`, `joints3dKeys`, `joints3dFrames`, `coordDim`, `space` 검증 추가.
- `space`: 04-01 과 동일하게 `pole_aligned`.
- version doc + top-level mirror + rollback snapshot 모두 같은 필드 세트 사용.
- `ReferenceMotion` TS 타입/normalizer 가 별도로 있다면 `joints3d` 필드를 추가한다.

대안은 reference overlay 를 Phase 4 scope 에서 명시적으로 제외하고 `04-UI-SPEC.md:158` 및 `04-05-PLAN.md:178` 의 reference `joints3d` mirror 요구를 제거하는 것이다. 다만 Phase 4 UI 중요도를 감안하면 포함이 더 일관적이다.

### BLOCKER-3 — active `read_first` 가 아직 superseded 패턴을 구현 기준으로 읽게 한다

**근거**

- 04-01 Wave 0 `read_first` 는 `04-PATTERNS.md §SynthesisAdapter 신규 선언` 과 `04-RESEARCH.md §Pattern 1` 을 시그니처 기준으로 읽게 한다 (`04-01-PLAN.md:127-130`).
- 04-01 Wave 1 `read_first` 는 `04-PATTERNS.md §pipeline/app.py` 를 "extra_warnings injection" 구현 패턴으로, `04-RESEARCH.md §Pattern 3` 을 `dataclasses.replace` 로 읽게 한다 (`04-01-PLAN.md:238-240`).
- 실제 `04-PATTERNS.md:306-338` 은 구 `_call_synthesis_adapter(...)-> tuple | None` 예시를 아직 담고 있고, `04-PATTERNS.md:895-905` 는 shared pattern 에서 `extra_warnings` + `dataclasses.replace` 를 그대로 보여준다.
- `04-PATTERNS.md:916-928` 의 shared protocol/G4 guard 도 여전히 `tuple[np.ndarray, np.ndarray]` 및 `return None` 계약이다.
- `04-RESEARCH.md:260-270`, `04-RESEARCH.md:304-322`, `04-RESEARCH.md:500-518`, `04-RESEARCH.md:531-532` 도 구 tuple/extra_warnings/top-level warnings 계약을 담고 있다.

**위험**

executor 가 04-01 의 canonical 본문과 `read_first` 대상 예시를 동시에 읽으면, 구 tuple/None 계약이나 `profile.extra_warnings` 경로를 다시 구현할 수 있다. "SUPERSEDED" 라벨이 일부 붙어 있어도 active plan 이 그 섹션을 읽으라고 지시하는 한 실행 리스크가 남는다.

**수정 방안**

둘 중 하나로 정리해야 한다.

- 04-PATTERNS/04-RESEARCH 의 관련 코드 예시를 전부 `SynthesisResult.status` + `ai_synthesis_meta["warnings"]` + `SynthesisAdapter.synthesize_occluded_joints(...) -> SynthesisResult` 로 갱신한다.
- 또는 04-01/04-05 `read_first` 에서 stale 섹션을 제거하고, "해당 섹션은 superseded 이므로 implementation source 로 사용 금지" 를 명시한다.

현 상태에서는 "라벨만 붙이고 active read path 유지" 가 가장 위험하다.

### HIGH-1 — 04-02 done gate 에 `warnings.includes` 잔재가 남아 있다

**근거**

- key link 는 `result.aiSynthesisMeta.warnings.includes('ai_synthesis_failed')` 로 고쳐졌다 (`04-02-PLAN.md:58-60`).
- UI-SPEC 도 helper 사용을 명시한다 (`04-UI-SPEC.md:258`).
- 하지만 done gate 는 아직 `result.tsx 에서 visible = warnings.includes('ai_synthesis_failed')` 로 파생하라고 한다 (`04-02-PLAN.md:285`).

**위험**

구현자가 `warnings` local 변수를 top-level `doc.warnings`/`result.warnings` 에서 만든 뒤 배지 visible 을 연결할 수 있다. 이 경우 3차에서 해결한 canonical warning surface 가 UI done criterion 에서 다시 깨진다.

**수정 방안**

`04-02-PLAN.md:285` 를 `hasSynthesisWarning(doc?.result, 'ai_synthesis_failed')` 또는 `result.aiSynthesisMeta?.warnings` 기반으로 바꾼다. top-level warning array 에서 배지를 파생하지 말라고 명시한다.

### HIGH-2 — 04-05 versioned write 테스트가 아직 실제 Firestore 경로를 증명하지 못한다

**근거**

- 테스트 설명은 `reference/{id}/versions/phase4_v1` 경로를 확인한다고 하지만 (`04-05-PLAN.md:132-134`),
- 실제 검증은 AST Constant 중 `"phase4_v1"` 포함 노드가 하나라도 있으면 GREEN 이다 (`04-05-PLAN.md:135-138`).
- acceptance 도 동일하게 `phase4_v1` Constant 존재만 본다 (`04-05-PLAN.md:264`, `04-05-PLAN.md:268`).

**위험**

`PIPELINE_VERSION = "phase4_v1"` 만 있어도 테스트가 통과한다. `referenceMotions`, top-level overwrite, 잘못된 subcollection, active pointer 없는 write 모두 놓친다.

**수정 방안**

fake Firestore client 를 주입해서 호출 path 를 기록해야 한다.

- `_write_versioned(fake, "ref-foxtop", payload)` 반환/기록 path == `reference/ref-foxtop/versions/phase4_v1`.
- `referenceMotions` 문자열/collection 호출은 테스트에서 금지.
- `_flip_active_pointer` 는 5개 completed 전에는 top-level merge/update 호출이 0임을 단언.

### HIGH-3 — 04-05 가 canonical `reference/{id}` 라고 말하지만 RESEARCH 는 아직 `referenceMotions/{id}` 를 가르친다

**근거**

- 04-05 `read_first` 는 `04-RESEARCH.md §Runtime State Inventory` 를 "canonical path = reference/{id}, referenceMotions 아님" 근거로 읽으라고 한다 (`04-05-PLAN.md:102-103`).
- 실제 `04-RESEARCH.md:543` 은 Stored data 를 `referenceMotions/{id}` 로 적고, 덮어쓰기/버전 필드 결정을 요구한다.
- `04-RESEARCH.md:590` 도 `referenceMotions/{id}` 에 기존 분석 결과가 저장됐다고 반복한다.

**위험**

executor 가 04-05 본문과 RESEARCH inventory 중 어느 쪽을 믿어야 하는지 알 수 없다. reference migration 은 데이터 쓰기 경로가 핵심이므로, 이 drift 는 단순 문서 부정확성이 아니라 잘못된 collection write 리스크다.

**수정 방안**

`04-RESEARCH.md` runtime inventory 를 실제 canonical path 로 고친다. 과거 명칭이 필요하면 "deprecated/old assumption" 으로 분리하고, implementation source 에서는 `reference/{id}` 만 남긴다.

### HIGH-4 — raw synthesis warning 과 public `AiSynthesisMeta.warnings` 의 매핑이 정의되지 않았다

**근거**

- `SynthesisResult.warnings` 는 arbitrary tuple 로 정의된다 (`04-01-PLAN.md:147`).
- Gemini adapter 실패는 `gemini_api_error`, `gemini_parse_error`, `g4_reference_guard` 같은 raw reason 을 넣는다 (`04-01-PLAN.md:156-161`).
- TypeScript public warning union 은 `ai_synthesis_failed | ai_synthesis_partial` 뿐이다 (`04-01-PLAN.md:171`).
- pipeline 은 status 기반으로 public warning 을 `ai_synthesis_meta["warnings"]` 에 추가한다 (`04-01-PLAN.md:274-275`).

**위험**

raw reason 이 public UI/contract warning 배열로 섞이면 TS 타입과 contract enum 을 깨고, 반대로 raw warning 이 완전히 버려지면 운영 디버깅 근거가 사라진다. 지금 계획은 둘 중 어느 쪽인지 명확하지 않다.

**수정 방안**

명시적으로 분리한다.

- `ai_synthesis_meta["warnings"]`: public enum only (`ai_synthesis_failed`, `ai_synthesis_partial`).
- `ai_synthesis_meta["errorCode"]` 또는 `debugWarnings`: raw reason (`gemini_api_error`, `gemini_parse_error`, `g4_reference_guard`).
- `g4_reference_guard` 는 reference skip 이므로 public warning 으로 승격하지 않는다.

### MEDIUM-1 — 04-03 의 active adapter chain 검증이 04-01 singleton 계약과 충돌한다

**근거**

- 04-03 은 `_get_synthesis_adapter()` 가 반환하는 "active adapter chain" 에 `CylindricalMeshAdapter` 가 포함되지 않는다고 검증하라고 한다 (`04-03-PLAN.md:253-254`).
- 04-01 은 `_get_synthesis_adapter()` 를 lazy singleton GeminiViewReasoner 로 정의한다 (`04-01-PLAN.md:269-274`, `04-01-PLAN.md:302` 근처의 adapter 호출 흐름).

**위험**

구현자가 존재하지 않는 chain abstraction 을 만들거나, 테스트가 실제 설계와 맞지 않아 불필요한 구조를 강제한다.

**수정 방안**

검증 문구를 "SYNTHESIS_MESH_ENABLED unset/0 일 때 `_get_synthesis_adapter()` 가 `CylindricalMeshAdapter` instance 를 반환하지 않는다" 로 바꾼다. chain 이 필요하면 04-01 에 먼저 chain 계약을 정의해야 한다.

### MEDIUM-2 — 04-04 는 아직 G4 guard 를 `return None` 계약으로 읽게 한다

**근거**

- 04-04 `read_first` 는 `test_synthesis_g4_guard.py` 를 "return None 검증" 패턴으로 읽으라고 한다 (`04-04-PLAN.md:150`).
- 04-01 의 최신 계약은 `is_reference=True` 에서 `SynthesisResult(status="skipped")` 이다 (`04-01-PLAN.md:160-161`, `04-01-PLAN.md:248-250`).

**위험**

Wave 4 executor 가 구 None 계약을 다시 테스트에 복원할 수 있다.

**수정 방안**

`04-04-PLAN.md:150` 을 `SynthesisResult(status="skipped")` 검증 패턴으로 바꾼다.

### MEDIUM-3 — UI-SPEC 은 아직 `draft` 이고 04-02 는 executor 가 승인 상태를 기록한다고만 한다

**근거**

- `04-UI-SPEC.md:4` 는 `status: draft`.
- 04-02 는 실행 전 executor 가 approved 로 기록할 것이라고 한다 (`04-02-PLAN.md:81`).

**위험**

UI 계약 승인 여부가 실행자의 부수 작업이 된다. Phase 4 는 UI surface 가 큰 phase 이므로, 승인 상태는 실행 전 명시적으로 결정돼야 한다.

**수정 방안**

위 BLOCKER/HIGH 수정 후 `04-UI-SPEC.md` 를 `approved` 로 바꾸거나, 04-02 시작 전 blocking precondition 으로 "UI-SPEC approve commit 존재" 를 둔다.

### MEDIUM-4 — 04-02 Task 3 이 Task 1 smoke screen 생성을 다시 지시한다

**근거**

- Task 1 은 `PoseViewer3DSmokeScreen.tsx` 를 생성한다 (`04-02-PLAN.md:109-135`).
- Task 3 files/action 에도 같은 파일이 포함되고 신규 생성 지시가 있다 (`04-02-PLAN.md:159-169`, `04-02-PLAN.md:262-267`).

**위험**

Task 1 smoke 에서 검증한 파일을 Task 3 이 다시 덮어써 실기기 검증 결과와 실제 병합 전 코드가 달라질 수 있다.

**수정 방안**

Task 3 은 smoke screen 파일을 "verify/reuse only" 로 바꾸고, 수정이 필요하면 checkpoint 재검증을 요구한다.

## 실행 승인 전 필수 패치 목록

1. `04-05-PLAN.md` 의 reference reprocess 목적을 "synthesis off, Phase 4-compatible payload/versioned write" 로 재작성한다.
2. 04-05 payload/schema/versioned write/top-level mirror 에 `joints3d` 필드 세트를 추가하거나, reference 3D overlay 를 scope out 한다. 권장은 추가.
3. `04-01-PLAN.md`, `04-05-PLAN.md` 의 `read_first` 에서 stale PATTERNS/RESEARCH 섹션을 제거하거나, 해당 섹션의 코드 예시를 최신 계약으로 갱신한다.
4. `04-02-PLAN.md:285` 를 `hasSynthesisWarning(doc?.result, 'ai_synthesis_failed')` 기준으로 수정한다.
5. 04-05 versioned write test 를 AST constant 검색에서 fake Firestore path assertion 으로 강화한다.
6. `04-RESEARCH.md` runtime inventory 의 `referenceMotions/{id}` 를 canonical `reference/{id}` 로 정정한다.
7. raw synthesis reason 과 public warning enum 의 매핑을 `AiSynthesisMeta` 에 명시한다.
8. 04-03 chain wording, 04-04 `return None`, 04-02 duplicate smoke screen 생성 지시를 정리한다.
9. 위 수정 후 `04-UI-SPEC.md` status 를 `approved` 로 올리거나, 실행 전 승인 checkpoint 를 명시한다.

## 최종 의견

3차 response 의 "잔여 0" 주장은 아직 성립하지 않는다. 하지만 남은 문제는 이제 Phase 4 전체 방향성이 아니라 **04-05 reference migration 계약 + stale implementation source 정리** 로 압축됐다. 이 두 축을 고치면 Phase 4 는 실행 가능한 수준에 가까워진다.
