---
phase: 17-gemini-vision-integration-4
reviewer: codex
reviewed_at: 2026-06-12
status: issues_found
risk_level: high
scope:
  - 17-AI-SPEC.md
  - 17-01-PLAN.md
  - 17-02-PLAN.md
  - 17-03-PLAN.md
  - 17-04-PLAN.md
  - 17-05-PLAN.md
  - 17-06-PLAN.md
  - 17-07-PLAN.md
findings:
  blocker: 4
  warning: 6
---

# Phase 17 Codex Plan Review

## Verdict

Phase 17 방향 자체는 맞다. A/B/C/D를 독립 영역으로 나누고, 공통 Gemini client + Pydantic schema + guardrail을 먼저 박는 구조는 유지할 만하다. 다만 현재 계획 그대로 실행하면 핵심 가치인 D keypoint 보강과 B 코칭 교체가 잘못 동작할 가능성이 높다. 특히 모델 ID, RTMW 배열 계약, coach writer interface, pipeline video-path gate는 구현 전에 반드시 고쳐야 한다.

내 의견은 Phase 17을 바로 실행하지 말고, `17-AI-SPEC.md`와 Plan 03/04/06을 먼저 패치한 뒤 실행하는 것이다. 제일 위험한 D 영역은 "Gemini 좌표를 3D scoring 배열에 직접 주입"하는 설계를 줄이고, 처음에는 RTMW 실패 프레임 식별/좌우 힌트/2D overlay 보강까지만 production에 넣는 편이 더 안전하다.

## BLOCKER-1 — `gemini-3.1-pro` 모델 ID가 현재 공식 API 코드와 맞지 않는다

**근거**
- `17-AI-SPEC.md:344-347`, `17-03-PLAN.md:96`, `17-04-PLAN.md:95`, `17-05-PLAN.md:109`가 A/B/D와 C 승급 모델을 `gemini-3.1-pro`로 박고 있다.
- Google 공식 Gemini API 문서 기준, Gemini 3.1 Pro의 모델 코드는 `gemini-3.1-pro-preview`다. 같은 문서에서 `gemini-3.5-flash`는 stable model code로 확인된다.
  - https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview
  - https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash

**Risk**
Plan 03/04/05의 Pro 호출이 400/404로 실패하면 A reference 등록, B vision coach, D keypoint 보강이 전부 graceful fallback으로 조용히 빠질 수 있다. 테스트가 monkeypatch 기반이면 이 문제를 못 잡는다.

**내 의견 / 더 좋은 방안**
- `17-AI-SPEC.md`의 모델 표를 다음처럼 수정:
  - A: `gemini-3.1-pro-preview`
  - B vision: `gemini-3.1-pro-preview`
  - C default: `gemini-3.5-flash`
  - C override: `gemini-3.1-pro-preview`
  - D: `gemini-3.1-pro-preview`
- Plan 01에 `models.py` 또는 `gemini/config.py`를 두고 영역별 default model을 한 곳에서만 정의한다.
- 배포 전 smoke에 "configured model names"를 최소 1회 dry call 또는 explicit allowlist로 검증하는 gate를 추가한다.

## BLOCKER-2 — Plan 03이 RTMW 4채널을 `confidence`로 잘못 해석한다

**근거**
- Plan 03은 `coco_array[:, :, 3] = confidence`라고 전제하고, `min(axis=1) < 0.5`를 low-confidence frame으로 잡는다 (`17-03-PLAN.md:122`).
- 실제 `to_coco17_array` 계약은 `(x, y, z, uncertainty_proxy)`다. `result[:, :, 3] = 1.0`은 미감지/최대 불확실성이고, confidence가 아니다 (`backend/shared/python/sunity_shared/analysis/pose_frame.py:325-350`).
- Plan 03은 Gemini가 뽑은 normalized 2D 좌표를 `coco_array[..., 0:2]`에 `x * frame_w`, `y * frame_h`로 주입한다고 되어 있다 (`17-03-PLAN.md:124`). 하지만 이 배열의 x/y/z는 `keypoints_3d_pole_aligned` 좌표다.

**Risk**
현재 설계대로면 가장 불확실한 frame을 건너뛰고, 오히려 확실한 frame을 Gemini 보강 대상으로 고를 수 있다. 더 위험한 부분은 2D normalized pixel 좌표를 3D pole-aligned scoring 배열에 섞는 것이다. 그렇게 되면 `compute_joint_angles`, DTW, KISMAM score가 좌표계가 섞인 값을 기반으로 계산된다.

**내 의견 / 더 좋은 방안**
- D 영역 production scope를 줄인다. 1차 구현은 `PoseFrame.keypoints_2d` / `KeypointReport.confidence` 보강과 좌우/mirror hint까지만 쓰고, 3D scoring 배열은 직접 mutate하지 않는다.
- scoring에 반영하려면 먼저 좌표계 계약을 명시해야 한다.
  - RTMW 3D/pole-aligned 좌표를 유지할지
  - image normalized 2D 좌표를 별도 report로만 둘지
  - 2D 보강값을 어떤 lifter/alignment로 3D에 투영할지
- 그래도 low-confidence frame을 고른다면 `confidence = 1.0 - uncertainty_proxy` 또는 `uncertainty_proxy > 0.5`로 계산해야 한다.
- Success Criteria도 `KeypointReport.data confidence < 0.5`가 아니라 `KeypointReport.confidence` 기준으로 고쳐야 한다. `data`는 좌표 flat list이고 confidence는 별도 필드다.

## BLOCKER-3 — Plan 04의 `GeminiCoachWriter.write()` 인터페이스가 기존 writer와 호환되지 않는다

**근거**
- Plan 04는 `GeminiCoachWriter.write(joints, dim_scores, video_path=...)`가 `CerebrasCoachWriter`와 동일 시그니처라고 쓴다 (`17-04-PLAN.md:95-97`, `17-04-PLAN.md:127`).
- 실제 `CerebrasCoachWriter.write()`는 `write(context: dict) -> dict`이고, `_process`도 dict 하나만 넘긴다 (`backend/shared/python/sunity_shared/analysis/coach_writer.py:107-118`, `backend/functions/pipeline/app.py:1149-1162`).

**Risk**
Plan 04 구현자가 문서대로 `write(joints, dim_scores, video_path)`를 만들면 `_process` dual-track 교체가 바로 깨진다. 반대로 pipeline을 계획대로 바꾸면 Cerebras fallback 호출부가 깨진다.

**내 의견 / 더 좋은 방안**
- `GeminiCoachWriter.write(context: dict) -> dict`로 맞춘다.
- context에 optional field를 추가한다: `videoPath`, `dimensionScores`, `sceneFlags`, `geminiD`.
- `_process`에서는 `coach_context` dict를 한 번 만들고 Gemini/Cerebras 둘 다 같은 context를 받게 한다.
- Gemini 실패 시 return은 `None`보다 `{}`와 구분되는 명시 결과가 낫다. 예: `{"_fallbackReason": "gemini_none"}`는 Firestore audit에는 유용하지만, `assemble.build_result`에는 넘기지 않는다.

## BLOCKER-4 — Phase 17 영상 호출 gate가 현재 pipeline의 `keep_local_video` 조건과 맞지 않는다

**근거**
- 현재 `_process`는 `_extract_video_analysis_inputs(... keep_local_video=_gemini_enabled())`만 호출한다 (`backend/functions/pipeline/app.py:889-896`).
- `_gemini_enabled()`는 기존 Gemini technique recognizer 스위치다. Phase 17 C/D/B가 켜져도 recognizer가 꺼져 있으면 `local_video_path`가 없다.
- Plan 02/03/04는 `_process` 중간에 video_path 기반 Gemini Vision 호출을 추가한다고 되어 있다 (`17-03-PLAN.md:123`, `17-04-PLAN.md:127`).

**Risk**
운영에서 `GEMINI_RECOGNIZER_ENABLED`가 off이고 Phase 17만 켜면 C/D/B는 호출할 파일 경로가 없다. 구현자가 이를 피하려고 S3 download/frame extract를 다시 하면 Phase 6에서 막아둔 "RTMW estimate 1회" 보장이 깨진다.

**내 의견 / 더 좋은 방안**
- 새 helper를 추가한다: `_gemini_vision_enabled()`.
- `keep_local_video = _gemini_enabled() or _gemini_vision_enabled()`로 바꾼다.
- server.py의 `_process(bucket, key, uid, analysis_id)` 시그니처는 바꾸지 않는다. `is_reference`는 `_process` 안에서 `key.startswith("reference/")`, analysis `mode`, 또는 reference-auto-register path로 분리한다.
- Plan 02/03/04에 "S3 download/RTMW 재실행 금지"를 explicit gate로 넣는다.

## WARNING-1 — Plan 06의 telemetry 의존성이 배포 파일 범위에 빠져 있다

**근거**
- Plan 06은 `arize-phoenix`, `openinference-instrumentation-google-genai`, `opentelemetry-*` 설치를 요구한다 (`17-06-PLAN.md:120-129`).
- 하지만 frontmatter `files_modified`에는 `backend/runpod_inference/requirements.txt`, `backend/functions/pipeline/requirements.txt`, `backend/shared/python/requirements.txt`가 없다.
- 현재 RunPod requirements에는 `google-genai`와 `cerebras-cloud-sdk`는 있지만 Phoenix/OpenTelemetry 패키지는 없다.

**Risk**
mock 테스트는 통과하고, Pod/Lambda에서 import failure가 난다. 특히 Plan 06은 뒤쪽 wave라 앞선 A/B/C/D가 배포된 뒤 telemetry만 깨지는 형태가 될 수 있다.

**내 의견 / 더 좋은 방안**
- Plan 06을 쪼갠다.
  - 06A: requirements + `phoenix_setup.py` + no-op bootstrap only
  - 06B: span event wiring
  - 06C: Promptfoo dataset/assertions
- 각 runtime별 requirements를 frontmatter에 명시한다.
- `bootstrap_tracing()` import 자체는 optional import로 감싸고, dependency missing이면 warning + noop으로 둔다. 단 CI에는 "telemetry extras installed" test를 별도로 둔다.

## WARNING-2 — Plan 05 Lambda timeout 120s는 자체 설명과 모순된다

**근거**
- Plan 05는 Files API polling 약 120s + Pro 호출 약 15s를 전제하면서 Lambda Timeout을 120s로 잡는다 (`17-05-PLAN.md:149`).

**Risk**
파일 ACTIVE 대기만으로 timeout 예산을 소진한다. reference 등록은 사람이 쓰는 admin path라 몇 초 더 기다리는 것이 실패보다 낫다.

**내 의견 / 더 좋은 방안**
- Timeout을 최소 180s, 보수적으로 240s로 잡는다.
- 또는 Files API polling upper bound를 90s로 줄이고, 90s 초과는 `202 accepted + pending job`으로 전환한다.

## WARNING-3 — `complete_analysis` geminiB/C/D 저장 위치가 contract에 명확하지 않다

**근거**
- Plan 02/03/04는 `complete_analysis(gemini_c=...)`, `gemini_d=...`, `gemini_b=...`를 추가한다고 되어 있다.
- 현재 `complete_analysis`는 일부 필드를 top-level에 두고, user-visible report는 `result` 내부에 둔다 (`backend/shared/python/sunity_shared/firestore_admin.py:637-673`).

**Risk**
geminiB/C/D가 top-level audit field인지, `result` 내부 user-visible field인지 모호하다. 앱 타입(`analysis.ts`)과 docs contract가 같이 안 바뀌면 프론트가 읽지 못하거나, audit-only 필드를 UI가 실수로 노출할 수 있다.

**내 의견 / 더 좋은 방안**
- 저장 위치를 둘로 분리한다.
  - audit: top-level `gemini.{a,b,c,d}` 또는 `aiTrace.phase17`
  - UI/result: `result.tips`, `result.coach`, `result.forcePatternInference`, `result.keypointReport`
- app type + docs/contract.md + firestore validator를 같은 plan에 lockstep으로 넣는다.

## WARNING-4 — Plan 05/07이 기존 reference doc shape를 과신한다

**근거**
- Plan 07은 reference doc에서 `videoUrl + studioAlias`를 읽는 흐름을 전제한다.
- 현재 seed script는 `videoS3Key`, `name`, `entryDescription`, `isActive` 등을 저장하지만 `studioAlias` 필드는 명시적으로 없다 (`app/scripts/seed-reference-motions.mjs` reference doc 생성부).

**Risk**
reactivate script가 기존 5개/신규 6개 reference에서 alias를 못 읽고 branch2 routing을 누락할 수 있다.

**내 의견 / 더 좋은 방안**
- `reactivate_new6_motions.py` 상단에 `{motionId: studioAlias}` 명시 mapping을 둔다.
- Firestore에 `studioAlias`를 새로 추가할 거라면 Plan 05에서 reference doc contract를 갱신하고 seed script도 같이 수정한다.

## WARNING-5 — Plan 06의 "auto-escalation env set"은 운영 자동화로 성립하지 않는다

**근거**
- AI-SPEC은 E5 PASS rate가 95% 미만이면 `GEMINI_C_MODEL_OVERRIDE=gemini-3.1-pro`를 자동 set한다고 쓴다 (`17-AI-SPEC.md:346`).

**Risk**
프로세스 환경변수는 실행 중 앱 코드가 안정적으로 바꿀 수 있는 runtime config가 아니다. Pod/Lambda 재배포나 외부 config store가 필요하다.

**내 의견 / 더 좋은 방안**
- env가 아니라 Firestore/SSM/AppConfig 같은 runtime config를 읽는다.
- `GEMINI_C_MODEL_OVERRIDE`는 수동 emergency override로 유지하고, 자동 승급은 `visionConfig.regionC.model` 같은 동적 config로 설계한다.

## WARNING-6 — Promptfoo "CI/CD"가 실제 CI와 연결되어 있지 않다

**근거**
- Plan 06은 Promptfoo PR pre-merge gate를 말하지만, repo에는 `.github/workflows`가 없다.
- Plan 06 Task 3도 README와 config 생성까지만 명시한다.

**Risk**
문서상 PR block이라고 쓰이지만 실제로는 아무 것도 block하지 않는다.

**내 의견 / 더 좋은 방안**
- Phase 17 범위에서 "local eval config"와 "CI gate"를 분리해서 말한다.
- 실제 block이 필요하면 `.github/workflows/phase17-evals.yml` 또는 현재 배포 체계에 맞는 CI task를 별도 plan으로 추가한다.

## Recommended Patch Order

1. `17-AI-SPEC.md` 모델 표를 공식 model code로 수정한다.
2. Plan 03을 재설계한다. D 영역은 2D/3D 좌표계를 섞지 않는 방식으로 scope를 줄인다.
3. Plan 04 writer interface를 기존 `write(context: dict)` 계약에 맞춘다.
4. Plan 02/03/04 공통으로 `_gemini_vision_enabled()`와 `keep_local_video` 정책을 추가한다.
5. Plan 06을 telemetry / eval dataset / CI wiring으로 split한다.
6. Plan 05 timeout과 reference doc alias contract를 수정한다.

## Positive Notes

- 공통 Gemini client를 Plan 01에 먼저 두는 방향은 맞다.
- A/B/C/D를 Firestore audit field로 남기려는 방향은 이후 flywheel에 유리하다.
- G1/G3/G4/G5 guardrail을 plan에 명시한 점은 좋다. 다만 D 영역은 guardrail보다 좌표계 계약이 먼저다.
- Plan check가 잡은 latency SC 불일치와 Plan 06 split 필요성은 타당하다. 이 리뷰는 그 위에 실제 코드 계약 충돌을 추가로 지적한다.
