---
phase: 04-ux-occlusion-confidence
responder: Claude (Opus 4.8) — codebase + plan 직접 검증
date: 2026-06-13
source_review: 04-DIRECT-REVIEW.md (Codex, revise-before-execution)
verdict: ACCEPT-MOST (5/5 blocker 사실 확인) + R1 부분 반박 (MVP scope)
filters_applied:
  - 기술 스택 belle spike 잠금 (SMPL-X 완전 최후의 보류, Higgsfield/MagicMan 차단)
  - Gemini 2.5 = Vision 입력 영역만 한시 허용 (일반 reasoning 3.x)
  - calibration-source-hard-gate (자기 sweep 재calibrate 금지)
  - analysis-objectivity (사람 점수 라벨링 금지)
  - mvp-simple-pilot-quality (구조만 열고 과한 machinery 금지)
---

# Phase 4 Direct Review — 검증 + 수정 방향

## 한 줄 결론

리뷰의 5개 blocker는 **전부 코드/plan에서 사실로 확인됨.** as-is 실행 보류 판정에 동의한다.
핵심 안전축 = 리뷰의 Global Strategy "Scoring-safe channel ↔ User-confidence/UI channel 분리" — 이게 Phase 4의 진짜 안전장치고, 우리 프로젝트의 "분석 정확도 최우선" + analysis-objectivity 박제와 정확히 일치한다. **수용.**

단 R1은 분리 원칙은 수용하되 promotion-gate machinery는 MVP에서 안 짓는다(아래 반박).

## Blocker 검증 결과 (직접 확인한 증거)

### R1 — 합성 좌표 ↔ scoring boundary 충돌 → **수용(분리) + 부분 반박(promotion 기계 금지)**
- **확인:** RESEARCH가 scoring matrix mutate 금지를 명시(383, 454-458)하고, 04-01 merge는 KeypointReport/`aiSynthesisMeta`로만 흐른다. 경계는 사실상 이미 있으나 plan이 명시적으로 못 박지 않음 — 리뷰 지적 타당.
- **수용:** 04-01/04-03에 "synthesis output is **non-scoring**, DTW/kismam/IPSF coco_array를 절대 mutate 안 함"을 acceptance criterion으로 명문화. confidence를 **visual/display confidence**로 명명(scoring confidence와 구분).
- **반박(MVP scope):** 리뷰의 `scoringEligible` 필드 + "promotion gate(evaluate_4way 통과 시 점수 반영)" **machinery는 Phase 4에서 짓지 않는다.** Phase 4 = 합성은 **영구 non-scoring (UI/메타 전용)**. 점수 promotion은 CONTEXT scope 밖(D-05 블랙박스 + 정확도 검증은 Wave 3b/Wave 5 gate가 담당)이고, 안 쓸 gate 기계를 미리 만드는 건 mvp-simple-pilot-quality 위반. → "promotion = 별도 후속 phase" 한 줄 박제로 대체. **하드월 채택, 승급기계 기각.**

### R2 — 실패 semantics 불일치로 실패 합성이 성공처럼 merge → **수용 (정밀화)**
- **확인:** 04-00은 degrade를 `(None,None)` 기대(116-118), 04-01 adapter는 실패 시 `(np.zeros_like, np.zeros_like)` 반환(138), pipeline은 `synth_result is None`일 때만 `ai_synthesis_failed` 추가(228-236). → `(zeros,zeros)`는 None이 아니므로 **실패가 성공 경로로 빠지고 경고가 안 붙음 + Wave 0 테스트 계약(None vs zeros) 깨짐.** 둘 다 사실.
- **정밀화:** merge 로직이 `synth_conf > primary_conf`라 zero-conf는 비교에서 절대 못 이김 → 좌표 오염은 우연히 막힘. **그러나 진짜 버그는 (a) 경고 누락 → UI "정확도 제한" 배지 안 뜸, (b) None/zeros 계약 불일치로 Wave 0 RED.** 둘 다 실재.
- **수용:** 리뷰의 typed `SynthesisResult(status: applied|partial|skipped|failed, joints, confidence, warnings, meta)` 채택. all-zero sentinel 폐기. 04-00 테스트도 status 기반으로 정렬.

### R3 — PoseViewer3D data contract가 Firestore `angles`와 불일치 → **수용 + 리뷰보다 더 심각(escalate)**
- **확인:** pipeline은 `angles=np.asarray(angles).reshape(-1).tolist()` = flat **(T,J) 관절각**(1841). temporal.py 명시 "입출력 모두 관절각 (T,J)". analysis.ts `angles: number[]` = T*J, J보통 8. **3D 좌표 필드(joints3d/pose3d/coordDim) 자체가 없음.**
- **04-02는 `reshapeJoints3d(result.angles, ...)`로 (T,17,3) 기대** → 8개 각도 스칼라를 XYZ로 그림. typecheck는 `number[]`라 통과 → **사용자는 의미상 완전히 틀린 3D 뷰어를 봄.**
- **리뷰가 과소평가한 부분:** 단순히 "잘못된 필드를 먹인다"가 아니라 **올바른 3D 소스가 Firestore에 아예 없다.** RTMW가 `keypoints_3d`를 계산하지만 **저장 안 됨**(현재 저장: angles(T,J) + keypointReport.data(T×8×2 이미지좌표) — 둘 다 2D/각도).
- **수용 + 확장:** 04-01(backend)에 **실 3D joint 좌표 저장 신설** — `joints3d`(flat T×17×3) + `joints3dKeys` + `joints3dFrames` + `coordDim:3` + `space:"rtmw3d"|"pole_aligned"` + flat validator(nested-array 금지) + analysis.ts/contract.md 3-way lockstep. 04-02는 그 필드만 읽고 `result.angles`는 **reject**. helper명 `reshapePose3dData`로.

### R4 — Cylindrical mesh acceptance가 실 RTMW 재추론 없이 통과 → **수용**
- **확인:** 04-03 `_rerun_rtmw_on_views`는 placeholder(118-125, "RTMW rerun not wired — returning primary joints with boosted conf"), acceptance는 `rate_reduction_pct >= 0.0`(257-263)로 **개선 0도 PASS**, Spike 002b는 VALIDATED-SKELETON(실추론 deferred). plan 본인도 "smoke gate" 주석 박음.
- **수용:** Wave 3 분리 — **3a smoke**(mesh build + 12-view render artifact + license, 정확도 주장 0) / **3b blocking accuracy gate**(실 RunPod RTMW 재추론 + 영상/배열 산출물 + evaluate_4way baseline 비교). `confidence +0.15` 단독으로 통과하는 acceptance 제거. calibration-source-hard-gate 정합 — 합성 boost를 근거로 점수 promote 금지.

### R5 — Gemini reasoning prototype이 production accuracy path엔 미흡 → **수용 (HIGH)**
- **확인:** Spike 003 = VALIDATED-PROTOTYPE(실 API deferred), threshold 0.3 = assumed(sweep 필요). 04-01은 `_synthesis_enabled()` default OFF "0" — **이미 박힘(좋음).**
- **수용(추가):** pipeline-wide 활성화 전 **10-frame clean-data gate**(clear 5 + occluded 5): 좌표 범위/joint identity/temporal 연속성/indeterminate rate + RTMW baseline 대비 + 시각 검수. green 전까지 `SYNTHESIS_ENABLED=0` 유지. `aiSynthesisMeta`에 model/version/prompt hash 감사 기록. → 이건 CONTEXT D-26(Omni clean-data gate)의 자연 확장 + sensitivity-gate 박제 정합. **Gemini 2.5-pro Vision 한시 허용은 유지**(env override 그대로 — 3.x Vision 미출시).

## High/Medium 검증 결과

| # | 판정 | 근거 (직접 확인) |
|---|------|------|
| R6 occluded_mask 형상 오용 | **수용** | `temporal.occluded_mask`는 `a.ndim != 2 → raise`. RESEARCH:291은 (T,J,2) 전달 → 런타임 raise. Phase 4 전용 target detector 신설: 입력 confidence (T,17) + scene flags → bool mask (T,17). `occluded_mask` 재사용 금지. |
| R7 UI 블랙박스 카피 모순 | **수용** | UI-SPEC 290줄에 "가림 구간 **AI 보완**이 적용되지 않았어요" — 283-286 "AI 보완 금지"와 직접 모순. 블랙박스 카피로 교체("가림 구간 정확도가 제한적이에요"). `ai_synthesis_failed`는 내부 코드로만. |
| R8 R3F readiness 과장 | **수용** | package.json에 three/R3F/expo-gl 부재(Wave 2 설치 예정). autonomous:false + checkpoint Task 0는 이미 있음. **추가:** 별도 `PoseViewer3DSmokeScreen`(feature flag) + 런타임 fallback(Canvas/GL crash → 뷰어 생략, 일반 결과 표시) + 실기기 smoke 전 result.tsx 병합 금지. |
| R9 Omni/Veo stub 유지 | **수용 (내 필터와 일치)** | Omni 공개 endpoint 없음(내 박제와 동일). stub 유지 + ENABLED=0 + NotImplementedError + watch checklist + 10-video pose consistency gate(D-26). Codex가 SMPL-X 재제안 안 하고 stub 유지 권고 — 레인 지킴. |
| R10 reference reprocess grep 과다 | **수용** | 04-05가 문자열 존재로 검증(99-109). **behavioral 테스트로 교체**: is_reference=True 시 호출되면 raise하는 fake adapter + 5영상 dry-run schema 검증 + **versioned/atomic write**(`referenceMotions/{id}/versions/phase4_v1` → 5개 다 통과 후 active pointer flip) + rollback. mode1 양쪽 오염 방지(분석 최우선). |
| R11 VALIDATION approved 표기 | **수용(경미)** | "계획 단계 검증만, Wave 0 파일 collect 전 구현 증명 아님" 1줄 명시. |
| R12 ROADMAP plan 미등재 | **수용(경미)** | ROADMAP Phase 4 Plans 섹션에 6 plan + 본 리뷰 등재. |
| R13 cost telemetry 부재 | **수용** | Wave 1에 최소 카운터(frames considered/synthesized/calls/skipped/failed/est cost). 대시보드는 deferred 유지. belle 비용효율 직관 정합. |

## 반박/유보 (rubber-stamp 방지)

1. **R1 promotion-gate machinery — 기각.** 분리(하드월)는 수용하되 `scoringEligible` 필드 + 점수 승급 게이트는 Phase 4에서 만들지 않는다. Phase 4 합성 = 영구 non-scoring. 승급은 별도 후속 phase. (mvp-simple-pilot-quality: 안 쓸 기계 금지.)
2. **R4 Wave 3b를 phase 전체 blocker로 두지 말 것.** 3b(실 RunPod 재추론)는 RunPod 운영 의존이라, Wave 5(reference 재처리)는 **Wave 1 Gemini path 기준으로 진행 가능**해야 한다(04-05 depends_on을 04-03 3a smoke까지만). 3b는 정확도 검증 gate로 분리하되 Wave 2(UI)·Wave 5 진행을 막지 않음.
3. **Codex SMPL-X 편향 — 이번엔 없음.** 메모리상 경계 대상이었으나 이 리뷰는 스택 재제안 0. 그대로 신뢰.

## 수정 방향 (plan별 patch 요약 — 실행 시)

- **04-00:** degrade 기대를 `SynthesisResult.status`로 정렬(`(None,None)`/`(zeros,zeros)` 혼선 제거).
- **04-01:** ① `SynthesisResult` 타입 도입(zero sentinel 폐기) ② `joints3d`(T×17×3)+coordDim+space Firestore 저장 신설 + analysis.ts/contract.md 3-way lockstep ③ non-scoring 하드월 acceptance ④ Phase4 전용 target detector(occluded_mask 재사용 금지) ⑤ visual/display confidence 명명 ⑥ aiSynthesisMeta 감사필드(model/version/prompt hash) + cost 카운터.
- **04-02:** ① `result.angles` 제거 → `joints3d` 소스 사용(`reshapePose3dData`, angles reject) ② Canvas/GL 런타임 fallback 필수 ③ 별도 smoke screen + 실기기 통과 전 result.tsx 병합 금지 ④ UI-SPEC draft→approved 노트.
- **04-03:** Wave 3a(smoke, 정확도 주장 0) ↔ 3b(실 RunPod 재추론 blocking gate) 분리. `+0.15` 단독 통과 acceptance 제거.
- **04-04:** stub 유지(변경 없음). env flag 단독 활성화 금지 — model 가용성 + pose consistency gate 필수.
- **04-05:** behavioral guard 테스트(fake adapter raise) + 5영상 dry-run schema + versioned/atomic write + rollback. depends_on은 04-03 3a까지(3b 비차단).
- **UI-SPEC:** DimensionDetailModal "AI 보완" 카피 → 블랙박스 카피 교체.
- **VALIDATION/ROADMAP:** R11/R12 경미 수정.

## Gemini 모델 박제 (revision 시 사수)

- Vision 입력 영역(scene_finder / GeminiViewReasoner) = `gemini-2.5-pro` 한시 허용 유지. env override(`GEMINI_C_MODEL_OVERRIDE`)로 제어. 일반 reasoning은 3.x. **revision이 실수로 Vision을 3.x로 강제하지 않도록 주의**(Google Vision 3.x 미출시).
