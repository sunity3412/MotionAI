---
phase: 04-ux-occlusion-confidence
reviewer: Codex
date: 2026-06-13
scope: direct-plan-ui-technical-review
status: revise-before-execution
reviewed_plans:
  - 04-00-PLAN.md
  - 04-01-PLAN.md
  - 04-02-PLAN.md
  - 04-03-PLAN.md
  - 04-04-PLAN.md
  - 04-05-PLAN.md
  - 04-CONTEXT.md
  - 04-RESEARCH.md
  - 04-UI-SPEC.md
  - 04-VALIDATION.md
---

# Phase 4 Direct Review

## Executive Verdict

방향은 맞다. Phase 4 의 핵심 pivot, 즉 사용자는 1개 영상만 올리고 백엔드가 confidence/occlusion 구간만 보완하며 UI 는 "추정/정확도 제한"만 노출한다는 방향은 현재 제품 철학과 맞는다.

하지만 **현재 plan 그대로 실행하면 Phase 4 가 가장 위험한 방식으로 섞인다.** 모델 보완 결과, 점수 산출, 3D UI 표시, reference 재처리가 하나의 "정확도 향상" 이야기로 묶여 있는데, 실제 코드 계약은 이미 "합성 결과로 DTW/kismam scoring matrix 를 mutate 하지 않는다"는 안전 경계를 갖고 있다. 이 경계를 plan 에서 더 강하게 나누지 않으면 UI 는 자신감 있게 보이는데 실제 점수는 검증되지 않았거나, 반대로 실패한 합성이 성공처럼 저장되는 문제가 생길 수 있다.

내 판정은 **as-is 실행 보류, 짧은 plan patch 후 실행**이다. 특히 04-01, 04-02, 04-03, 04-05 는 실행 전에 수정해야 한다. 04-04 는 stub 로 유지하는 한 안전하다.

## Reviewed Inputs

- `.planning/phases/04-ux-occlusion-confidence/04-CONTEXT.md`
- `.planning/phases/04-ux-occlusion-confidence/04-RESEARCH.md`
- `.planning/phases/04-ux-occlusion-confidence/04-UI-SPEC.md`
- `.planning/phases/04-ux-occlusion-confidence/04-VALIDATION.md`
- `.planning/phases/04-ux-occlusion-confidence/04-00-PLAN.md` through `04-05-PLAN.md`
- `.planning/spikes/003-gemini-vision-view-reasoning/README.md`
- `.planning/spikes/002b-cylindrical-mesh-virtual-render/README.md`
- `.planning/spikes/005-frontend-3d-viewer/README.md`
- `backend/functions/pipeline/app.py`
- `backend/shared/python/sunity_shared/firestore_admin.py`
- `backend/shared/python/sunity_shared/analysis/temporal.py`
- `backend/shared/python/sunity_shared/gemini/scene_finder.py`
- `app/package.json`
- `app/src/lib/userAnalyses.ts`
- `app/src/types/analysis.ts`
- 2026-06-13 기준 공식 문서: Google Gemini API model docs, Google Cloud model docs, R3F install docs, Expo GLView docs.

## Global Strategy

Phase 4 는 반드시 두 채널로 나눠야 한다.

1. **Scoring-safe channel**
   - DTW/kismam/IPSF scoring matrix 는 기존 RTMW 원본 경로만 사용한다.
   - 합성/추론 좌표는 5-reference RunPod gate 를 통과하기 전까지 점수에 반영하지 않는다.
   - gate 조건: reference 5영상에서 occlusion 관련 감점 감소, G4 악화 0, self-comparison regression 0, failed/partial synthesis 가 명시적으로 기록.

2. **User-confidence/UI channel**
   - KeypointReport, `aiSynthesisMeta`, 3D viewer, warning badge 만 보강한다.
   - 사용자는 "AI 보완"을 보지 않는다. "가림 구간 정확도 제한"과 "추정값"만 본다.
   - 실패/부분성공/미적용은 내부 warning code 로 기록하고 UI 는 블랙박스 카피로 변환한다.

이 분리가 Phase 4 의 핵심 안전장치다. 이 분리가 없으면 모델 품질이 UI 신뢰도와 점수 신뢰도를 동시에 오염시킨다.

## Blockers

### R1. 합성 좌표와 scoring boundary 가 plan 안에서 충돌한다

Severity: **BLOCKER**

Evidence:

- `04-RESEARCH.md:383` and `04-RESEARCH.md:454-458` explicitly forbid mutating the RTMW 3D scoring matrix with synthesis output.
- `04-03-PLAN.md:19-22` claims 12-view render, RTMW re-inference, merge path, and evaluate_4way improvement.
- `04-03-PLAN.md:121-125` then says current implementation returns primary joints with boosted confidence, not real RTMW re-inference.
- `04-CONTEXT.md:63-66` says perspective correction is out of scope, so Phase 4 alone cannot claim to solve all camera-angle distortion.

Risk:

- "정확도 향상"이 UI confidence 보강인지, 실제 IPSF 점수 보강인지 모호해진다.
- 합성 품질이 낮아도 confidence boost 만으로 성공처럼 보일 수 있다.
- later executor 가 `coco_array` 또는 score input 을 mutate 하도록 잘못 이해할 가능성이 있다.

Recommendation:

- 04-01/04-03 에 "synthesis output is non-scoring until promoted" 를 acceptance criteria 로 추가한다.
- `SynthesisResult` 에 `scoringEligible: false` 를 기본값으로 둔다.
- scoring promotion 은 별도 gate 로 둔다: `evaluate_4way` real RunPod 결과, reference 5영상 G4 악화 0, score regression 0.
- UI/KeypointReport 에 들어가는 confidence boost 는 "visual confidence" 또는 "display confidence" 로 명명하고 scoring confidence 와 구분한다.

### R2. 실패 semantics 가 서로 맞지 않아 실패한 합성이 성공처럼 merge 될 수 있다

Severity: **BLOCKER**

Evidence:

- `04-00-PLAN.md:116-118` expects adapter degrade as `(None, None)`.
- `04-01-PLAN.md:138` and `04-01-PLAN.md:160-162` instruct GeminiViewReasoner to return zeros on API failure, JSON parse failure, or exception.
- `04-01-PLAN.md:228-236` says pipeline adds `ai_synthesis_failed` only when `synth_result is None`; if not None it merges.

Risk:

- `(zeros, zeros)` is not `None`, so pipeline can treat failed synthesis as a successful result.
- Shape-only tests will pass while all synthesized joints are bogus.
- UI can omit the "정확도 제한" badge because the failure was represented as an array, not as a status.

Recommendation:

Replace tuple/sentinel semantics with a typed result:

```python
@dataclass(frozen=True)
class SynthesisResult:
    status: Literal["applied", "partial", "skipped", "failed"]
    joints: np.ndarray | None = None
    confidence: np.ndarray | None = None
    warnings: tuple[str, ...] = ()
    meta: dict[str, object] = field(default_factory=dict)
```

Rules:

- `failed`: no merge, append `ai_synthesis_failed`.
- `skipped`: no warning unless reason is user-visible confidence limit.
- `partial`: merge only explicitly marked joints, append `ai_synthesis_partial`.
- `applied`: merge where synthesis confidence is higher.
- Never use all-zero arrays as a failure sentinel.

### R3. PoseViewer3D 의 data contract 가 현재 Firestore `angles` 계약과 맞지 않는다

Severity: **BLOCKER**

Evidence:

- `04-02-PLAN.md:169-172` defines `reshapeJoints3d(angles, jointKeys, frames)` as if `angles` were flat `(T,17,3)` coordinates.
- `04-02-PLAN.md:261-264` wires `reshapeJoints3d(doc?.result?.angles, doc?.result?.anglesJointKeys, doc?.result?.anglesFrames)`.
- Current pipeline stores `angles=np.asarray(angles).reshape(-1).tolist()` with `angles` computed by `compute_joint_angles`, shape `(T,J)` (`backend/functions/pipeline/app.py:1004-1007`, `backend/functions/pipeline/app.py:1841-1843`).
- `temporal.py:13-14` and `temporal.py:52-72` define angles/uncertainty as 2D `(T,J)`, not 3D coordinates.

Risk:

- 3D viewer draws angle values as XYZ coordinates.
- TypeScript typecheck can still pass because flat `number[]` matches both shapes.
- Users see a polished 3D viewer that is semantically wrong.

Recommendation:

- Do not feed `result.angles` into PoseViewer3D.
- Add an explicit field such as `pose3dReport` or `joints3dData`:
  - `joints3d: number[]`
  - `jointKeys: string[]`
  - `frames: number`
  - `coordDim: 3`
  - `space: "rtmw3d" | "pole_aligned"`
  - optional `source: "primary_rtmw" | "synthesis_display"`
- Add a Firestore validator for flat numeric arrays and `coordDim`.
- Rename frontend helper to `reshapePose3dData`, and make it reject `angles`.

### R4. Cylindrical mesh path acceptance can pass without real RTMW rerun

Severity: **BLOCKER**

Evidence:

- `04-03-PLAN.md:17-23` says the must-have path is 12-view render -> RTMW re-inference -> merge.
- `04-03-PLAN.md:121-125` says `_rerun_rtmw_on_views` is currently a placeholder that returns primary joints with boosted confidence.
- `04-03-PLAN.md:215-219` evaluates a simulated `confidence +0.15`.
- `04-03-PLAN.md:259-263` accepts `rate_reduction_pct >= 0.0`, which can pass with no real improvement.
- Spike 002b is `VALIDATED-SKELETON`, with RunPod real inference deferred (`002b.../README.md:85-95`, `:102`).

Risk:

- The plan claims backend accuracy improvement while only proving integration plumbing.
- A non-negative threshold is too weak; it accepts "no worse" synthetic output as success.
- Future scoring promotion would be based on a placeholder.

Recommendation:

Split Wave 3:

- **Wave 3a smoke**: mesh build, 12-view render artifact, licensing, no accuracy claim.
- **Wave 3b blocking accuracy gate**: real RunPod RTMW rerun on rendered views, persisted artifacts, evaluate_4way against baseline.

Acceptance should require:

- real rendered image files or arrays from 12 views,
- real RTMW inference output per view,
- comparison report with baseline and candidate metrics,
- no score promotion when only the synthetic boost path ran.

### R5. Gemini reasoning prototype is not yet enough to be a production accuracy path

Severity: **HIGH**

Evidence:

- Spike 003 is `VALIDATED-PROTOTYPE`, but says real API call is deferred (`003.../README.md:69`, `:82-90`, `:111-112`).
- `04-CONTEXT.md:79-80` treats Gemini reasoning as PRIMARY and cylindrical mesh as SECONDARY.
- `04-RESEARCH.md:570-585` admits confidence threshold 0.3 is assumed and should be swept.

Risk:

- The plan wires a reasoning prototype into the pipeline before validating coordinate accuracy, temporal consistency, and hallucination behavior.
- Frame-by-frame reasoning can produce temporally plausible-looking but physically inconsistent joints.

Recommendation:

Before pipeline-wide activation:

- Run a 10-frame clean-data gate: 5 clear frames, 5 occluded frames.
- Validate coordinate bounds, joint identity, temporal continuity, and `indeterminate` rate.
- Compare against RTMW baseline and reference visual review.
- Keep `SYNTHESIS_ENABLED=0` default until gate is green.
- Persist per-call model/version/prompt hash in `aiSynthesisMeta` for audit.

## High-Risk Findings

### R6. `identify_synthesis_targets` pseudocode calls `occluded_mask` with the wrong shape

Severity: **HIGH**

Evidence:

- `04-RESEARCH.md:291` calls `occluded_mask(joint_seq[..., :2], confidence_seq)`.
- Current `temporal.occluded_mask` requires 2D angles `(T,J)` and same-shape uncertainty, raising on non-2D input (`backend/shared/python/sunity_shared/analysis/temporal.py:52-72`).

Risk:

- A direct implementation will fail at runtime or silently duplicate logic incorrectly.
- The trigger mask becomes unreliable, causing excess model calls or missed occlusion.

Recommendation:

Create a separate target detector for Phase 4:

- Input: keypoint confidence matrix `(T,17)`, optional phase boundaries, scene flags, low-uncertainty frame indices.
- Output: bool mask `(T,17)`.
- Do not reuse `temporal.occluded_mask` for coordinate sequences.
- Sweep thresholds `0.2 / 0.3 / 0.4` on reference fixtures and record call volume/cost.

### R7. UI black-box copy is internally inconsistent

Severity: **HIGH**

Evidence:

- `04-UI-SPEC.md:16` says user-facing UI must not mention "AI".
- `04-UI-SPEC.md:283-286` explicitly bans "AI 보완 실패" and similar copy.
- `04-UI-SPEC.md:288-290` then adds DimensionDetailModal copy: "이 분석에서는 가림 구간 AI 보완이 적용되지 않았어요."

Risk:

- The result screen follows the black-box rule but the detail modal leaks implementation language.
- Users may trust or distrust scores based on "AI" wording rather than the actual reliability warning.

Recommendation:

Replace all user-facing failure copy with black-box wording:

- "가림 구간 정확도가 제한적이에요."
- "측면 관절 추정 오차가 포함될 수 있어요."
- "일부 구간은 가림 또는 측정 불확실로 추정값입니다."

Keep `ai_synthesis_failed` only as an internal warning code.

### R8. R3F/Expo integration is correctly identified as risky, but the plan still overstates readiness

Severity: **HIGH**

Evidence:

- `app/package.json` currently has Expo SDK 54 packages but no `three`, `@react-three/fiber`, `expo-three`, `@react-three/drei`, or `expo-gl`.
- `04-02-PLAN.md:96-125` requires a blocking real-device checkpoint.
- `04-UI-SPEC.md:4` is still `status: draft`.
- Official R3F docs require native imports for React Native and call out physical iOS device testing due to simulator OpenGL instability.
- Official Expo GL docs require installing `expo-gl` for GLView.

Risk:

- Typecheck can pass while GL rendering fails on device.
- Result screen can regress if a canvas crash takes down the analysis result route.

Recommendation:

- Keep Wave 2 `autonomous:false`.
- Build a separate `PoseViewer3DSmokeScreen` behind a feature flag before touching the result screen.
- Add a runtime fallback: if Canvas/GL fails, omit the 3D viewer and show normal results.
- Do not merge result-screen integration until physical iOS/Android smoke test passes.

### R9. Wave 4 Omni/Veo must remain stub-only

Severity: **HIGH**

Evidence:

- `04-04-PLAN.md:44-50` says Wave 4 is a disabled stub.
- `04-RESEARCH.md:447-449` says Gemini Omni endpoint is not publicly registered.
- Google Gemini API model docs list Gemini 3.x models and Veo 3.1 generative media models, but I did not find a public official "Gemini Omni" model endpoint in the checked Google model docs as of 2026-06-13.
- Google Cloud model docs describe Veo 3.1 as generating videos from text prompts and images, not as a verified drop-in existing-video camera-angle editor.

Risk:

- Hardcoding a rumored or non-public model id will create 404/runtime failures.
- Veo/Omni output can be visually plausible but analytically unusable for pose scoring.

Recommendation:

- Keep `SYNTHESIS_VIDEO_GEN_ENABLED=0`.
- Keep adapters raising `NotImplementedError`.
- Add a watch checklist: official model id, terms/pricing, region availability, input/output API shape, pose consistency gate.
- Require 10-video pose consistency before any Stage 4 output affects UI or scoring.

### R10. Reference reprocess tests are too grep-heavy for a critical migration

Severity: **HIGH**

Evidence:

- `04-05-PLAN.md:99-109` validates G4 guard and pipelineVersion mostly by string presence.
- `04-05-PLAN.md:137-139` allows partial failure and then hands output to seeding.
- `04-05-PLAN.md:347-355` recognizes a race/update risk but relies on pipelineVersion and seed script patterns.

Risk:

- `is_reference` can appear in a comment while the runtime path still calls synthesis.
- A partial reference update can make mode1 comparisons inconsistent.
- No rollback path is specified for bad reference reseed.

Recommendation:

- Replace grep tests with behavior tests using a fake adapter that raises if called when `is_reference=True`.
- Require dry-run JSON schema validation for all 5 reference motions before any write.
- Write reference docs atomically or versioned:
  - write `referenceMotions/{id}/versions/phase4_v1`,
  - flip active pointer only after all 5 pass,
  - include rollback script or previous-version pointer.
- Compare old/new self-test and mode1 smoke metrics before activation.

## Medium Findings

### R11. Validation frontmatter says approved/Nyquist compliant while files are still pending

Severity: **MEDIUM**

Evidence:

- `04-VALIDATION.md:4-5` says `status: approved` and `nyquist_compliant: true`.
- `04-VALIDATION.md:44-51` shows all Phase 04 test files as not existing yet.
- `04-VALIDATION.md:89` clarifies this is planning-stage approval.

Risk:

- Executor may read this as proof rather than a plan.

Recommendation:

- Add an explicit line: "This validates plan coverage only; no implementation proof until Wave 0 files exist and collect."
- Update after Wave 0 with actual collection counts.

### R12. Roadmap state has minor drift

Severity: **MEDIUM**

Evidence:

- `.planning/ROADMAP.md:142-159` has updated Phase 4 goal and success criteria.
- `.planning/ROADMAP.md:149` maps to POSE-03.
- `.planning/REQUIREMENTS.md:157` still marks POSE-03 as Pending, which is correct.
- The roadmap phase section does not list the six Phase 4 plan files yet.

Risk:

- GSD progress tools and humans may undercount Phase 4 planning state.

Recommendation:

- Add the six plan files to the Phase 4 Roadmap "Plans" section after this review is resolved.

### R13. Cost/caching controls are acknowledged but deferred

Severity: **MEDIUM**

Evidence:

- `04-CONTEXT.md:134-136` defers caching and cost dashboard.
- `04-CONTEXT.md:209` says cost efficiency depends on pinpoint synthesis.
- `04-RESEARCH.md:570-585` says trigger threshold is assumed.

Risk:

- A broad trigger threshold can turn a pinpoint feature into a high-cost per-frame model loop.

Recommendation:

- Add minimum cost telemetry in Wave 1, even if full dashboard is deferred:
  - frames considered,
  - frames synthesized,
  - model calls,
  - skipped by cache,
  - failed calls,
  - estimated cost.

## Plan-by-Plan Required Changes

### 04-00

- Align degradation test expectation with final contract. It currently expects `(None, None)`, while 04-01 says `(zeros, zeros)`.
- Prefer tests for `SynthesisResult.status`.
- Keep Wave 0 as TDD gate; this is the right sequencing.

### 04-01

- Introduce `SynthesisResult`.
- Remove zero-array failure sentinel.
- Add `scoringEligible=false`.
- Add audit metadata: model id, prompt hash, frame count, target mask count, status, warning codes.

### 04-02

- Replace `reshapeJoints3d(result.angles, ...)`.
- Add a real `pose3dReport` or `joints3dData` field.
- Keep result screen fallback path mandatory.
- Do not proceed while `04-UI-SPEC.md` remains draft unless the executor records an explicit UI-spec approval note.

### 04-03

- Split smoke vs real RunPod inference.
- Remove any acceptance criterion that passes from `confidence +0.15` alone.
- Require persisted 12-view render and actual RTMW rerun artifacts for accuracy claims.

### 04-04

- Keep as stub.
- Do not activate on env flag alone after future implementation; require model availability and pose consistency gate.

### 04-05

- Replace grep tests with behavioral tests.
- Add versioned reference update or rollback.
- Require all 5 reference motions pass schema and metric gates before active pointer flip.

## Web Search Notes, 2026-06-13

Sources checked:

- Google Gemini API Models: `https://ai.google.dev/gemini-api/docs/models` (last updated 2026-06-09). Confirms Gemini 3.x model family and Veo 3.1 generative media listings.
- Google Cloud model docs: `https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models` (redirects to Google model docs). I found Veo 3.1 listings, but no public "Gemini Omni" model endpoint in the checked official page.
- React Three Fiber install docs: `https://r3f.docs.pmnd.rs/getting-started/installation`. Confirms React Native uses `@react-three/fiber/native`, `expo-gl`, and physical device testing is important.
- Expo GLView docs: `https://docs.expo.dev/versions/latest/sdk/gl-view/`. Confirms `expo-gl` installation and GLView as the OpenGL ES render target.

Implication:

- Gemini reasoning path can be built against official Gemini API models.
- Omni should remain a watch/stub path until an official public endpoint is verified.
- Veo 3.1 is not enough by itself to replace the reasoning/mesh path for analytical pose correction.
- R3F/Expo UI is plausible but must be physical-device gated.

## Final Gate Before Execution

I would not start Wave 1 until these are patched:

1. `SynthesisResult` contract replaces tuple/zero sentinel semantics.
2. PoseViewer3D has an explicit 3D data source, not `result.angles`.
3. Cylindrical mesh acceptance separates smoke from real RTMW rerun.
4. User-facing AI copy is removed from `DimensionDetailModal`.
5. Reference reprocess has behavioral guard tests and rollback/versioning.
6. Roadmap Phase 4 lists the six plans and this direct review.

After those patches, Phase 4 is executable with the right risk profile: Wave 1 can safely add model reasoning as a non-scoring confidence/metadata layer, Wave 2 can ship UI behind real-device validation, Wave 3 can prove or reject backend accuracy improvement, Wave 4 stays dormant, and Wave 5 can migrate references without corrupting mode1 comparisons.
