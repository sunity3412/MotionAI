# Phase 31 계획 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-19  
**범위:** `31-01-PLAN.md` ~ `31-09-PLAN.md`, `31-CONTEXT.md`, `31-RESEARCH.md`, `31-PATTERNS.md`, `31-VALIDATION.md`, ROADMAP/STATE 및 계획이 인용한 현재 backend/app 구현 경로  
**방법:** 목표 역산, 결정·불변식 대조, 실제 코드 계약 확인, 실패·재시도·개인정보·배포 경계 분석. 외부 AI, 외부 리뷰어, cross-AI 리뷰는 사용하지 않았다.  
**최종 판정:** **BLOCK / REPLAN REQUIRED (실행 전 재계획 필수)**

---

## 핵심 판정

계획의 분해 수준, 로컬 코드 인용, 계약 우선 순서, 명시적 위협 모델은 전반적으로 좋다. 4개 wave DAG가 읽기 쉽고, 대부분의 `read_first` 참조가 실제 코드와 일치하며, 상태 필드는 legacy 문서를 위해 optional로 설계되어 있다. 생성 시각물을 채점에서 분리한다는 원칙도 일관된다.

그럼에도 현재 상태로 실행하는 것은 안전하지 않다. 다음 3개 blocker는 잘못된 시각 지시 또는 영구 pending 작업을 직접 만들 수 있다.

1. R3F 계획은 저장된 RTMW 좌표의 depth 퇴화 때문에 실서비스 결과 화면에서 명시적으로 제거된 뷰어를 되살린다. 이를 “3D”, “360°”, “환각 0”으로 부르면 이미 코드에서 진단한 사용자 신뢰 결함을 그대로 재도입한다.
2. 목표각 화살표는 limb 벡터 하나로 관절 교정을 계산하고 모든 `unit='deg'` 감점 record를 절대각으로 취급한다. 둘 다 성립하지 않으며, 현재 코드도 `reference_relative.measuredValue`가 각도가 아니라 편차일 수 있음을 명시한다.
3. SQS worker는 Lambda가 정상 return하면 재전달된다고 가정한다. 실제로는 성공 처리된 메시지가 삭제되므로 polling 상한에 걸린 작업은 `rotationStatus='pending'`에 영구 고립된다.

그 밖에도 만료 URL, 외부 처리자 개인정보 경계, 원본 프레임 보관, 비동기 job 원자성, 약한 품질 게이트, 자동 교정 이미지 경로를 배포·E2E 검증하지 않은 채 phase를 완료 처리하는 문제가 고위험으로 확인됐다.

### 발견 항목 수

| 심각도 | 수 | 실행 영향 |
|---|---:|---|
| BLOCKER | 3 | 모든 구현 wave 착수 전에 해결 필수 |
| HIGH | 7 | 운영 배포 전 재계획에 반드시 반영 |
| MEDIUM | 8 | 같은 계획 개정에서 수정 권장 |
| LOW | 4 | 정밀도·표현 개선, 아키텍처 차단은 아님 |

---

## 차단·고위험 해결 요약

| ID | 문제 | 제가 적용할 해결 방향 |
|---|---|---|
| B-01 | depth가 없는 RTMW 평면 좌표를 360° 3D로 다시 노출 | D-10을 재결정해 카메라 평면 2D 비교 뷰어로 정직하게 강등하거나, 별도 depth-bearing pose source가 검증된 경우에만 orbit 허용 |
| B-02 | limb 1개와 direction 문자열로 목표 관절각 화살표 계산 | proximal-vertex-distal 3점과 DTW 대응 reference endpoint를 쓰는 명시적 `TargetArrowSpec`으로 교체; 의미가 불명확한 record는 화살표 생략 |
| B-03 | polling 상한에서 정상 return 후 SQS 재전달을 기대 | 장시간 Lambda polling을 없애고 delayed SQS/EventBridge/Step Functions 기반 1회성 poll state machine으로 전환 |
| H-01 | silhouette 생성이 RunPod 분석 task에 직결되고 실제 runtime secret/E2E가 없음 | silhouette·rotation을 하나의 durable visual job worker로 통합하고 분석 경로는 source artifact 저장+enqueue까지만 수행 |
| H-02 | Firestore에 저장한 7일 URL이 반드시 만료 | canonical S3 key만 저장하고 인증된 asset re-sign endpoint를 통해 mount/403 시 fresh URL 발급 |
| H-03 | 생성 이미지만 보는 Gemini judge가 원본 보존을 판정하고 smoke 실패도 live 진행 | before/after 비교 judge + 생성 이미지 pose 재측정 게이트 추가; `blocked=true`면 feature flag OFF 또는 downstream 차단 |
| H-04 | 외부 벤더 전송, 원본 frame·학습 pair 보존/삭제/동의 계약 부족 | 외부 처리 고지·보존 정책을 release gate로 두고 short-lived input prefix, lifecycle+finally 삭제, versioned consent, pseudonymous pair ID, 삭제 경로 구현 |
| H-05 | Firestore video key와 vendor download 경계가 느슨 | canonical upload key 일치 검증, HTTPS host boundary, redirect 재검증, private IP 차단, content-type/byte/time cap을 테스트로 고정 |
| H-06 | quota 증가·pending write·SQS send가 비원자적이고 공용 `updatedAt`을 사용 | transaction으로 quota+idempotent visual job을 예약하고 outbox/reconciler로 dispatch 복구; visual job 전용 timestamp 사용 |
| H-07 | worker 직접 invoke만으로 배포 성공 처리하고 silhouette 성공 E2E는 이월 | 인증 API→quota→실 SQS→worker→fresh asset의 rotation E2E와 신규 분석→silhouette done E2E 둘 다 통과해야 phase 완료 |

아래에는 각 항목의 코드 근거, 영향, 구체적인 수정안을 상세히 기록한다.

---

## What is already sound

- D-01~D-12 are carried into plan frontmatter and task truths with generally good traceability.
- Generated silhouette/rotation outputs are kept outside the score path; no plan intentionally mutates the deduction engine.
- The state contract uses optional fields and a three-state model, preserving legacy-document behavior.
- The plans correctly avoid storing vendor URLs as the canonical object location and intend to copy generated assets into the project S3 bucket.
- The rotation API requires Firebase auth, scopes Firestore reads by token UID, and specifies a single 404 response for missing/not-owned analyses.
- Learning storage uses a strict `learningOptIn is True` gate rather than truthiness.
- New Lambda log groups, DLQ, SSM secret sourcing, and a global spend guard are considered up front.
- The UI separates “참고하세요” from scoring and explicitly forbids multi-angle capture prompts and score-like numbers.

These strengths should be preserved during replanning.

---

## BLOCKERS

### B-01 · The plan reintroduces a known false-3D UI and labels it “hallucination 0”

**Evidence**

- `31-CONTEXT.md` D-04/D-10 and `31-05-PLAN.md:15-18, 41-45, 90-112` require an interactive R3F overlay of the user's measured pose and target pose, described as immediate, zero-hallucination 3D.
- The current result screen says the opposite at `app/src/app/analysis/result.tsx:1191-1195`: the viewer was removed because RTMW `joints3d` has effectively no depth and rotating the planar skeleton as “3D” was misleading.
- `app/src/components/PoseViewer3D.tsx:77-84, 409-420` confirms one axis is degenerate and explicitly disables/weakens rotation when depth is unavailable.
- `31-05` proposes reactivating the same component by adding a second skeleton; adding a reference skeleton does not restore missing user depth.
- The proposed frame alignment is also semantically mismatched: reference uses `execPeakS`, while the corrective silhouette/defect is top-1 fault-frame driven. Overlaying different pose moments can make a correct athlete look wrong.

**Impact**

This violates the product's core trust value. A user can rotate a planar reconstruction into a fabricated side/back view and interpret it as measured anatomy. The “환각 0” claim is materially false even though no generative model is involved.

**제가 해결한다면**

I would reopen D-10 before implementation and choose one of two honest contracts:

1. **Recommended MVP:** rename this to a 2D “자세 비교 뷰어,” lock it to the reliable camera plane, allow pan/zoom/scrub but not side/back orbit, and overlay user/reference keypoints at a DTW-matched fault frame. The UI must say it is a camera-plane comparison, not 3D.
2. **True-3D path:** first introduce and validate a product-licensed depth-bearing pose source (for example, a separately validated MediaPipe world-landmark path if accuracy is sufficient). Add a depth-validity gate and only enable orbit when both user and reference pass it. Degenerate input must fall back to the 2D contract.

The plan must include an automated frame-pair alignment test and a real-device depth/gesture gate. Until then, D-10 cannot be claimed complete.

---

### B-02 · The target-angle arrow geometry and data semantics are invalid

**Evidence**

- `31-03-PLAN.md:61-62` defines `_draw_target_arrow(img, anchor_px, limb_px, direction, measured_deg, target_deg)` and rotates one vector by `target - measured`.
- A joint angle requires three points: proximal joint, vertex, and distal joint. One anchor-to-limb vector cannot reconstruct the current joint angle or determine which segment stays fixed.
- Direction words such as `extend`, `raise`, and `open` do not determine clockwise/counter-clockwise direction in image coordinates; side, camera mirroring, pose inversion, and left/right limb all matter.
- `31-03-PLAN.md:78-79` assumes every `unit=='deg'` record exposes an absolute `measuredValue` and an absolute target `baselineValue`.
- Current code explicitly disproves that assumption. `fault_zoom.py:708-715` documents that a `reference_relative` record's `measuredValue` can be the deviation from the reference, not the student's angle. `pipeline/app.py:2979-2990` preserves this distinction to avoid a previously reproduced false label.
- `DeductionRecord` has no joint key (`deduction_engine.py:47-64`); the plan does not define a reliable criterion-to-joint/region mapping for arrow generation.

**Impact**

The arrow can point in the wrong direction, use a deviation as if it were a body angle, or attach a collective criterion to the wrong joint. That turns a display-only feature into incorrect coaching guidance.

**제가 해결한다면**

I would not derive screen geometry from direction vocabulary. I would define an explicit `TargetArrowSpec` generated from matched pose geometry:

- `vertex`, `proximal`, `distal` keypoint names and crop-space coordinates;
- `sourceFrameIndex`, `referenceFrameIndex`, and alignment provenance;
- `targetEndpoint` taken from the DTW-matched reference pose after scale/translation alignment, or from a validated IPSF absolute construction for the small set of criteria that genuinely has one;
- `sourceKind: 'reference_pose' | 'ipsf_absolute'`;
- confidence and omission reason.

Only criteria with a declared renderer mapping should produce arrows. `reference_relative` records must use matched reference coordinates, not `measuredValue/baselineValue`. Collective or ambiguous criteria should render no arrow. Golden-image tests should cover left/right, inverted/upright, mirrored, edge-clamped, low-confidence, and reference-relative cases. A Pod/reference fixture visual gate should be required before rollout.

---

### B-03 · The SQS retry design deletes timed-out jobs instead of retrying them

**Evidence**

- `31-07-PLAN.md:92` says that when the ~780-second polling cap is reached, the worker returns with `pending + task_id`, and SQS redelivery will resume polling.
- Lambda's SQS integration treats a normal handler return as success and removes the message. Redelivery only occurs when the batch item fails, the invocation times out/errors, or the worker explicitly requeues/changes visibility under a defined protocol.
- The plan's worker loop and verification do not require partial batch failure reporting, requeue, or an exception at the polling cap.
- `VisibilityTimeout: 960` provides little operational margin over a 900-second Lambda and does not define heartbeat/visibility extension behavior.

**Impact**

Any generation exceeding the polling cap becomes a permanent `pending` job. The app hides it after 20 minutes, but the paid vendor task may have completed and the asset is never collected. Quota is consumed and no retry occurs.

**제가 해결한다면**

I would stop holding a Lambda open for 6-13 minutes. Use a state-machine poller:

1. Request worker creates the vendor task, stores `taskId`, `attempt`, `nextPollAt`, and returns.
2. It sends a delayed SQS poll message (maximum 15-minute delay) or uses EventBridge Scheduler/Step Functions.
3. Each poll invocation runs once, updates state, and schedules the next poll if still pending.
4. Terminal success downloads the asset; terminal blocked/failed records a typed failure reason.
5. Every message carries a stable `jobId`; Firestore transaction/lease logic makes each transition idempotent.

If the long-poll Lambda design is retained, the polling-cap path must deliberately fail/requeue the item, extend visibility safely, and test actual redelivery. A normal `return` is not acceptable.

---

## HIGH

### H-01 · Automatic silhouette generation is coupled to the analysis process, but its runtime/deployment contract is incomplete

**Evidence**

- `31-06-PLAN.md:110-113` inserts DashScope generation and Gemini judging directly after `complete_analysis` in `_process`.
- Production analysis is delegated: `pipeline/app.py:4819-4841` sends the job to RunPod, whose background task owns `_process` (`runpod_inference/server.py:195-217`). The Lambda exits after delegation.
- `31-07-PLAN.md:109` injects `DASHSCOPE_API_KEY` only into the new visual worker. It does not update `PipelineFunction`, and `31-09` explicitly admits the Pod also lacks the key.
- Long external image generation plus a Gemini judge runs serially inside the RunPod background task, delaying cleanup and the next analysis even though the score is already complete.
- `31-06` says to run immediately after fault zoom, but fault zoom is conditional (`pipeline/app.py:4760-4794`). The required placement outside that conditional is not pinned.
- `31-09-PLAN.md:19, 31-35, 89, 128-130` simultaneously claims D-01 full integration/live and defers the automatic silhouette E2E until a future Pod recreation.

**Impact**

The feature can silently fail in production due to missing secret/runtime configuration, reduce analysis throughput, or never run on paths where the insertion point is conditional. The phase can be marked complete without demonstrating its primary automatic feature.

**제가 해결한다면**

I would move silhouette generation to the same durable visual-job system as rotation, using `kind='silhouette'|'rotation'`. The analysis path should only persist the selected source-frame artifact and enqueue a job after `complete_analysis`; it should never wait for DashScope/Gemini. The visual worker owns secrets, retries, vendor download, judge, status, and cleanup. This requires `31-06` to depend on the worker/IaC plan or the worker plan to move earlier.

If an async split is rejected, the plan must at minimum add the key to every actual runtime, pin insertion outside the fault-zoom conditional, bound execution time, and require a real automatic silhouette E2E before phase completion. I would not accept “Pod 재생성 후” as a completed D-05.

---

### H-02 · Stored 7-day presigned URLs will deterministically break reopened results

**Evidence**

- `31-01` stores `silhouetteImageUrl` and `rotationVideoUrl`; `31-06/07` write 7-day presigned URLs to Firestore; `31-08` renders them directly.
- `31-07`'s completed-request branch returns the already stored `rotationVideoUrl`, so it does not refresh an expired URL.
- The repository already has this exact incident documented in `backend/functions/playback-url/app.py:1-14`: stored 7-day URLs expired and caused playback failures, requiring a re-sign endpoint.
- Although S3 keys are also stored, no plan consumes those keys through an authenticated re-sign path.

**Impact**

Every done silhouette/rotation card eventually becomes a broken image/video while its status remains `done`. The current app has no recovery path.

**제가 해결한다면**

Firestore should persist only canonical keys plus metadata/status. Add an authenticated `POST /visual/url` or extend `/playback-url` with a server-selected asset type (`silhouette`/`rotation`), never a client-supplied arbitrary key. The server reads the analysis document under the token UID, validates the exact allowed `results/{uid}/{analysisId}/...` prefix and expected field, then returns a fresh short-lived URL. The app refreshes on mount and on 403/expiry. Tests must use an expired URL fixture.

---

### H-03 · The quality gate cannot verify the stated preservation guarantees and the smoke path fails open

**Evidence**

- `31-04-PLAN.md:81-84` defines `judge_silhouette(image_bytes, context)` with only the generated image plus text context, yet asks it to validate identity, clothing, pole, and background preservation. Without the original image, it cannot compare “unchanged.”
- The judge is another generative model and has no deterministic pose-angle measurement backstop.
- `31-02-PLAN.md:70` allows both candidate image models to fail, sets `blocked: true`, and still instructs `31-04` to implement mock-only while later plans proceed toward live integration.
- `31-09` does not require a successful real silhouette generation before completion.

**Impact**

A visually plausible but identity-altered, pole-distorted, or geometrically incorrect image can pass. Conversely, an unavailable model path can still reach “phase complete.”

**제가 해결한다면**

The gate should receive before and after images together and output typed, independently asserted axes. I would use:

- before/after multimodal judge for identity/clothing/background/pole preservation;
- pose/keypoint extraction on the generated image, measuring the target joint error against a declared tolerance;
- hard rejection on missing person, extra limbs/persons, invalid pole geometry, or confidence below threshold;
- separate thresholds for user display and training-pair admission (training should be stricter);
- a real fixture set with PASS/FAIL examples and measured false-accept/false-reject results.

If `RESULTS.json.blocked == true`, downstream live plans must be blocked or the feature must ship behind an OFF flag. Mock-only is not a production quality gate.

---

### H-04 · External processing, raw-frame retention, and learning-pair privacy are under-specified

**Evidence**

- D-05 automatically sends a user's body/face frame to DashScope for every eligible analysis, independent of `learningOptIn`. Learning consent and third-party service processing are different legal/product purposes; the plan only addresses the former.
- `31-06` writes `_silhouette_src.png` under `results/{uid}/{analysisId}/` but defines no deletion in `finally` and no lifecycle for `results/`. The repository lifecycle currently documents only `uploads/` expiration.
- The plan recommends raw-face storage in training pairs. It records `analysisId` while claiming UID removal prevents tracing, but `analysisId` can still link the pair back to the analysis document and result prefix.
- Consent provenance is only a boolean; it lacks consent text/version, captured-at time, source, retention period, revocation/deletion path, and vendor-processing disclosure.
- `31-02` can save real athlete input/generated images under a tracked `.planning/.../smoke/` directory; no ignore or cleanup rule exists.

**Impact**

Raw biometric-like imagery can be retained indefinitely, sent to a third-party processor without a verified disclosure basis, or committed as a planning artifact. Pair “de-identification” is overstated and deletion/revocation cannot be honored reliably.

**제가 해결한다면**

Before implementation I would require a privacy/data-handling checkpoint that confirms vendor region, retention/training policy, DPA/terms, and user disclosure. Then:

- use a dedicated short-lived `visual-input/` prefix with lifecycle expiry and explicit best-effort deletion after terminal processing;
- never store smoke images in tracked planning directories; use a gitignored artifact directory or `/tmp`, retaining only redacted metrics in `RESULTS.json`;
- generate a random pair ID or keyed HMAC, not raw `analysisId`, and store any re-identification map separately with stricter access;
- record consent version, timestamp, source, and processing purpose;
- define retention and deletion/revocation workflows for `training/phase31/pairs/`;
- default to face anonymization unless a documented, versioned consent explicitly covers identifiable model-training data and the measured quality loss justifies it.

This is not a UI-only product choice; it is a release gate.

---

### H-05 · Vendor input/output boundaries lack object-key and download hardening

**Evidence**

- `31-07` reads `myVideoKey` from Firestore and presigns it without requiring an exact `uploads/{uid}/{analysisId}.<ext>` match or allowed extension.
- SQS messages are revalidated only for document existence/status, not for the stored input key's ownership prefix.
- `_is_allowed_output_url` is described only as an `aliyuncs.com` whitelist; the plan does not require HTTPS, exact hostname/subdomain boundary matching, redirect rejection/revalidation, DNS/IP class checks, response-size limits, content-type validation, or streamed download caps.
- Generated video is downloaded into a 512 MB Lambda; an unbounded or redirected response can exhaust memory/disk or reach an unintended host.

**Impact**

A corrupted/admin-written key could send another object to the vendor. A permissive suffix check or redirect can become SSRF. Oversized responses can repeatedly exhaust the worker.

**제가 해결한다면**

Use server-derived keys whenever possible. Otherwise require exact UID/analysis prefix, allowed extension, and equality to the canonical upload key. For vendor downloads: `https` only, parsed hostname equals an allowlisted host or ends with `.` + allowlisted suffix, no credentials/query logging, redirects disabled or revalidated at every hop, private/link-local IPs rejected after resolution, strict timeout, content-type allowlist, and streamed byte caps. Add malicious-host (`evilaliyuncs.com`), redirect, oversized, wrong-content-type, and cross-UID key tests.

---

### H-06 · Quota, job dispatch, and stale-state transitions are not atomic

**Evidence**

- `31-07-PLAN.md:75` increments quota, writes `rotationStatus='pending'`, then sends SQS. These are three independent systems/operations.
- If SQS send fails, quota remains consumed and the document remains pending with no job. A retry within 20 minutes is deduped and cannot repair it.
- The plan uses the analysis-wide `updatedAt` to determine whether pending is stale. Unrelated partial updates can refresh that timestamp and extend dedupe/timeouts.
- The app also bases pending timeout behavior on the shared analysis timestamp, not a visual-job timestamp.
- No compare-and-set transition prevents two near-simultaneous requests from both passing a stale status check before pending is written.

**Impact**

Users can lose quota without a job, duplicate paid jobs under races, or remain hidden in pending longer than intended.

**제가 해결한다면**

Create a dedicated `visualJobs/{jobId}` document or nested backend-only collection with `kind`, `state`, `leaseOwner`, `taskId`, `requestedAt`, `updatedAt`, `attempt`, and idempotency key (`uid+analysisId+kind+version`). A Firestore transaction should reserve quota and create/return the job atomically. Dispatch failure must be repairable by an outbox sweeper or explicit requeue state. The analysis result can mirror display state, but job timestamps—not analysis `updatedAt`—own dedupe and UI timeout semantics. Test concurrent requests and SQS-send failure recovery.

---

### H-07 · Deployment verification can report success without testing the user journey

**Evidence**

- `31-09` directly invokes the worker Lambda with a fabricated SQS-shaped event. This bypasses Firebase auth, request validation, quota, pending dedupe, real SQS permissions/redelivery, and the app request client.
- It accepts `rotationStatus='failed'` as successful wiring without requiring a typed moderation failure or excluding implementation/network/permission errors.
- The automatic silhouette E2E—the core D-05 experience—is explicitly deferred.
- UI verification is deferred to batch UAT, while the plan still publishes OTA and marks D-01 full integration live.

**Impact**

The stack can deploy and the plan can close while the real button-to-queue-to-worker-to-refresh path is broken and while automatic silhouettes have never succeeded.

**제가 해결한다면**

Phase completion should require two real authenticated E2Es on a fixture account:

1. New analysis → automatic silhouette reaches `done`, fresh URL loads, judge metadata exists, temporary input is gone, and non-opt-in training writes are zero.
2. App/API request → quota reservation → real SQS message → worker → `done` → fresh URL loads; then a second request returns idempotent `done` without a new vendor task.

A moderation fixture may validate the `failed` path separately, but generic failure is not success. The production rollout should be feature-flagged/canary first, and the phase must remain incomplete if the Pod/worker needed for D-05 is unavailable.

---

## MEDIUM

### M-01 · The wave DAG no longer works if silhouette is made durable

`31-06` currently precedes/does not depend on `31-07`, even though the recommended architecture needs the visual queue/worker. Replan so job contract/IaC exists before both silhouette and rotation integrations. Avoid two unrelated implementations of the same vendor lifecycle.

### M-02 · Reference pose loading expands an all-doc Firestore subscription with large arrays

`useReferenceMotions()` subscribes to the whole `reference` collection and currently returns a compact subset. Adding every document's full `joints3d` sequence makes every result screen download all reference sequences. Prefer a compact `peakJoints3d`/named-pose field (51 floats per pose) or a direct single-document subscription for the selected reference. Index exemptions and document-size/read-cost checks should be explicit.

### M-03 · Typecheck is not sufficient verification for R3F/expo-image/expo-video behavior

`31-05` and `31-08` rely almost entirely on `npm run typecheck`. This cannot detect GL context crashes, transparent mesh z-fighting, incorrect frame alignment, video playback failure, gesture conflicts, or conditional-hook errors. Add component tests for state branches, a runtime Expo smoke, and iOS/Android device checks before OTA—not only after phase closure.

### M-04 · The plan risks conditional React hook usage for mode-specific references

`31-08` says mode1 uses one `useReferenceMotion` and mode3 conditionally uses `recognizedMotionId`. Implementation instructions must require an unconditional hook call with a derived `targetReferenceId`; calling hooks inside mode branches would violate React hook ordering.

### M-05 · `daily_limit` detection by `Error.message.includes()` is brittle

`31-08` parses a server code out of an error message string. Introduce a typed `ApiError {status, code, message}` in `api.ts` and branch on `code === 'daily_limit'`. Add response-schema validation for 200/202 bodies instead of trusting JSON shape.

### M-06 · The daily quota definition is operationally underspecified

KST day boundaries are hardcoded because current pilot users are Korean, but the behavior should be explicit in the contract/UI. Environment limits need integer/range validation and fail-closed defaults. Global counter contention is acceptable at 30/day, but transaction retry/exhaustion behavior needs a test and an operator reset/runbook.

### M-07 · Validation commands contain a working-directory error and several hollow gates

`31-09-PLAN.md:56` runs `cd backend && sam validate --lint && python -m pytest backend/tests -q`; after `cd backend`, `backend/tests` resolves to `backend/backend/tests`. Use `(cd backend && sam validate --lint) && python -m pytest backend/tests -q` from repo root. Also replace file-existence/grep-only gates with behavior assertions where possible, especially HUMAN-UAT creation and `RESULTS.json` validation.

### M-08 · Protocol return types are too weak for a multi-step paid job system

`dict | None` and string status values in `31-04` invite key drift across image/video adapters and workers. Use frozen dataclasses/TypedDicts or Pydantic models for create/poll results, with typed error categories (`moderation`, `timeout`, `vendor_error`, `invalid_output`) and request IDs. This will also make H-07's typed-failure verification possible.

---

## LOW

### L-01 · `autonomous: true` conflicts with paid live smoke calls

`31-02` performs paid API calls and writes temporary S3 objects. Make the real-call task a cost/data checkpoint; script authoring can remain autonomous.

### L-02 · “silhouette” is an inaccurate artifact name

The planned output is a full edited photograph preserving face, clothing, pole, and background, not a silhouette. Rename the contract to `correctedPoseImage*` or explicitly define the visual as a silhouette/mask. Ambiguous naming will leak into APIs and user copy.

### L-03 · `analysisId` format validation should have one shared owner

The plan copies `isalnum() and len>=16` from playback-url. Extract/reuse a shared validator or exact UUID/analysis-ID contract so new endpoints do not drift.

### L-04 · “pending timeout = hide” should be described as presentation fallback only

The app timeout does not cancel or fail the server job. Document this explicitly and provide operator-visible stuck-job metrics; otherwise hidden pending jobs become invisible operational debt.

---

## Required revised plan structure

I would replace the current four-wave plan with the following gate order while preserving most existing task content.

### Wave 0 — reopen invalid assumptions and freeze release gates

1. Resolve D-10: honest 2D camera-plane viewer vs validated true-3D source.
2. Approve third-party visual-processing disclosure, retention, deletion, and training-data consent contract.
3. Run image-model smoke with redacted/fixture input; `blocked=true` must stop live rollout or keep the feature flag OFF.
4. Define measurable visual acceptance thresholds and a small labeled fixture set.

### Wave 1 — contracts and durable job state

1. Define typed visual asset/job contracts, dedicated timestamps, canonical S3 keys, typed failure reasons, and idempotency key.
2. Add authenticated asset URL re-signing.
3. Build test scaffolding for transactions, dispatch failure, redelivery, expired URLs, malicious URLs, and concurrent requests.

### Wave 2 — geometry and generation engines

1. Implement reference-coordinate/three-point target overlay with omission rules and golden fixtures.
2. Implement image/video adapters with strict URL/download boundaries.
3. Implement before/after judge plus deterministic pose measurement.

### Wave 3 — async workers and privacy lifecycle

1. Implement the visual job queue/poller/state machine.
2. Enqueue automatic silhouette jobs after analysis completion without blocking `_process`.
3. Implement consent-versioned pair storage, pseudonymous IDs, retention/deletion, and temporary-source cleanup.
4. Implement rotation request/quota/idempotency on the same job substrate.

### Wave 4 — app integration

1. Implement the approved 2D/true-3D viewer contract.
2. Add typed API errors and fresh-URL acquisition.
3. Integrate state cards using visual-job timestamps and onSnapshot.
4. Add component/runtime tests for legacy, pending, failed, expired, mode3-no-recognition, and malformed data.

### Wave 5 — fail-closed deployment gate

1. Full tests + SAM build/validate.
2. Human-approved canary deploy with feature flags default OFF.
3. Real authenticated silhouette-success and rotation-success E2Es.
4. Moderation/failed-path E2E, quota/idempotency check, temporary-object cleanup check, and fresh-URL reopen check.
5. Only then enable OTA/canary and create HUMAN-UAT. D-01/D-05 remain incomplete if either real success path is unavailable.

---

## Minimum acceptance gates after replan

- A degenerate-depth user pose can never be presented as rotatable measured 3D.
- Every rendered arrow is backed by an explicit three-keypoint/reference geometry spec; ambiguous records produce no arrow.
- Pending visual jobs either reach a terminal state or remain recoverably scheduled; successful message return can never orphan them.
- No Firestore field relies on an expired vendor/project presigned URL as canonical state.
- Visual input/output downloads enforce key ownership, HTTPS host boundaries, redirect policy, content type, byte caps, and timeouts.
- Temporary raw frames are deleted and lifecycle-protected; training pairs have versioned consent and a deletion path.
- `RESULTS.json.blocked=true` prevents live feature enablement.
- Automatic silhouette success and authenticated rotation success are both demonstrated end-to-end before Phase 31 is marked complete.
- Generated visuals remain read-only with respect to every scoring input and score result.

---

## Final recommendation

Do not start `31-01` execution under the current plan set. The safest path is a focused replan, not incremental wording patches. The first decisions should be D-10's false-3D conflict and the external-processing/privacy contract; the first architectural change should be a single durable visual-job system shared by silhouette and rotation. Once those are fixed, most of the plan's existing contract, adapter, UI-section, and test scaffolding work can be retained with limited rewrite.
