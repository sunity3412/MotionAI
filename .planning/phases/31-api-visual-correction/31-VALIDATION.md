---
phase: 31
slug: api-visual-correction
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-19
replanned: 2026-07-19
revision: iteration4
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 31-RESEARCH.md `## Validation Architecture` + 31-PLAN-REVIEW-ITERATION2/3/4.md 요구 게이트 (2차 §8 16종 + 3차 §8-3 11종 + 4차 §8 11종).
> Task IDs = 2026-07-19 iteration4 targeted replan (13 plans / **6 waves** — 31-13(w3) → 31-09(w4) → 31-10(w5) → 31-12(w6)).
> `nyquist_compliant: true` 는 4차 §6 fault matrix 확장(ACK clobber·duplicate claim·old poll seq·sync block·moderation stale taskId·pair manifest·chosen↔env·postprocess crash·versioned cleanup·Object Lock·JPEG mismatch·pending pagination 편입) 후 재선언한 값이다.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend) / tsc --noEmit + jest-expo (app — jest 는 31-11 T1 checkpoint 후) |
| **Config file** | backend/requirements-dev.txt / app/jest.config.js (31-11 신설) |
| **Quick run command** | `python -m pytest backend/tests/phase31/<file>.py -x -q` |
| **Full suite command** | `python -m pytest backend/tests -q` + `cd app && npm run typecheck` (+ `npx jest` 31-11 이후) |
| **Estimated runtime** | ~130 seconds (실 302 local server 통합 + RSS 스트림 + claim/postprocess crash 시나리오 포함) |

---

## Sampling Rate

- **After every task commit:** 해당 테스트 파일 `-x -q` 단건
- **After every plan wave:** `python -m pytest backend/tests -q` (+ 앱 wave 시 typecheck/jest)
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** 130 seconds

---

## Wave Structure (H2-08 + 3차 H3-02/H3-09 반영 — 4차 불변)

| Wave | Plans | 비고 |
|------|-------|------|
| 1 | 31-01, 31-02, 31-03, 31-04 | 계약·target·상태(10종: postprocessing 포함)·outbox instance 기반 |
| 2 | 31-05, 31-06, 31-07, 31-08 | 어댑터(safe_decode·async-only)·게이트·페어(consumer helper)·앱 컴포넌트 |
| 3 | 31-11, 31-13 | 앱 통합 + calibration harness (31-05/06 실 코드 뒤, pair 계약 — H3-02/B4-04) |
| 4 | 31-09 | 워커+dispatcher — claim + outboxSeq + postprocessing durable |
| 5 | 31-10 | HTTP 표면·enqueue(upload-first+full-hash)·IaC(4 게이트 env) (H2-08) |
| 6 | 31-12 | 3중 blocked/ordering 게이트 + live mutation(Object Lock) checkpoint + 배포 + E2E |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 31-01/T1 | 31-01 | 1 | H-04+H2-06/H2-10 privacy gate | T-31-04 | 보존일수·blur 위치 확정 | manual (decision) | — | ⬜ pending |
| 31-01/T2 | 31-01 | 1 | D-03 스모크 + async여부 기록 (B4-02) | T-31-01/02/03/65 | 키 리터럴 0, MAX_CALLS=8, async(taskId) 기록 | script+assert | `python -c "import ast; ast.parse(...)"` | ⬜ pending |
| 31-01/T3 | 31-01 | 1 | async-only blocked(B4-02) + pair manifest(B4-04) + PASS4/FAIL8(H4-10) | T-31-65 | sync-only→blocked, before/after pair 10키, 표본 하한 | script+assert | RESULTS/manifest(pair)/privacy 스키마 assert + grep Training | ⬜ pending |
| 31-02/T1 | 31-02 | 1 | 테스트 스캐폴드 + mock(run_contended/commit_lost) | — | N/A | unit | `python -m pytest backend/tests/phase31 -x -q` | ⬜ pending |
| 31-02/T2 | 31-02 | 1 | 상태 10종(retry_ready+postprocessing) + typed 10종 + outbox 필드(outboxSeq/claimedOutboxSeq) | — | postprocessing 포함, dispatch_failed 부재 | unit | python -c import assert | ⬜ pending |
| 31-02/T3 | 31-02 | 1 | outbox instance CAS + claim + 원자 finalize(job 파생) + pagination (B4-01/B4-03/H4-07/H4-08) | T-31-05/06/07/52/56/57/62/63 | expect_outbox_seq CAS, claim already_claimed no-op, finalize 파생/모순 거부, pagination | unit | `python -m pytest backend/tests/phase31/test_visual_jobs.py -x -q` | ⬜ pending |
| 31-03/T1 | 31-03 | 1 | 화살표 기하 + topology parity (D-11) | T-31-09/10 | record 비의존, parity 단일, adversarial golden | unit | `python -m pytest backend/tests/test_fault_zoom_arrow.py -x -q` | ⬜ pending |
| 31-03/T2 | 31-03 | 1 | CorrectedPoseTarget 단일 계약 | T-31-53 | reference_relative 미유입, abs 정렬 | unit | `python -m pytest backend/tests/test_fault_zoom_arrow.py -x -q` | ⬜ pending |
| 31-03/T3 | 31-03 | 1 | 배선+프레임 쌍+무회귀 (D-12) | T-31-11 | 채점 read-only | unit | `python -m pytest backend/tests -q` | ⬜ pending |
| 31-04/T1 | 31-04 | 1 | 계약 TS+normalize (H-02 URL 비저장) | T-31-12 | literal 화이트리스트, key prefix 강등 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-04/T2 | 31-04 | 1 | contract.md 엔드포인트 2절 (M-06 KST) | T-31-13/14 | 단일 404, server-selected key | grep | grep daily_limit/feature_disabled/correctedPose | ⬜ pending |
| 31-05/T1 | 31-05 | 2 | typed 어댑터 create_task/poll + async-only 방출 (B2-02/B4-02) | T-31-15/19 | 이미지 폴링 0, IMAGE_ENGINE_SYNC/BLOCKED | unit | `python -m pytest backend/tests/phase31/test_visual_gen.py -x -q` | ⬜ pending |
| 31-05/T2 | 31-05 | 2 | safe_decode_image 공용 bomb(H4-06) + 다운로드 경계(H2-04/05,H3-05/06) | T-31-16/17 | decode 전 cap, _NoRedirectHandler, 실 302, subprocess RSS | unit+integration | `python -m pytest backend/tests/phase31/test_visual_gen.py -x -q` | ⬜ pending |
| 31-05/T3 | 31-05 | 2 | before/after judge(H3-02 인자식/H3-03 16MB/M4-02 단일 호출) | T-31-18 | 불확실=None, JudgeInputTooLargeError 전파, display/training 분리 min_confidence | unit | `python -m pytest backend/tests/phase31 -x -q` | ⬜ pending |
| 31-06/T1 | 31-06 | 2 | Pod /pose-image (H3-04 상한) | T-31-20/22 | 토큰 인증, decoded/pixel/dimension 상한 | script+assert | ast.parse + grep pose-image | ⬜ pending |
| 31-06/T2 | 31-06 | 2 | pose 게이트 (H3-04+H4-06 safe_decode 동일 계약) | T-31-21/23 | fail-closed unavailable, bomb 서버 미호출 | unit | `python -m pytest backend/tests/phase31/test_pose_gate.py -x -q` | ⬜ pending |
| 31-07/T1 | 31-07 | 2 | 페어 적재(strict+HMAC+M2-05) + consumer helper(H4-11) | T-31-24/25/27 | is True strict, uid 미포함, list_committed_pairs marker 강제 | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | ⬜ pending |
| 31-07/T2 | 31-07 | 2 | 삭제 경로 (전 키 + rotation + versioned) | T-31-26 | key rotation 후 삭제, versionId 완전 삭제 | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | ⬜ pending |
| 31-08/T1 | 31-08 | 2 | 목업 선제시 + 카드 위치 | — | N/A | manual (decision) | — | ⬜ pending |
| 31-08/T2 | 31-08 | 2 | amended D-10 2D 뷰어 | T-31-28/31 | R3F 0, "3D" 문구 0 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-08/T3 | 31-08 | 2 | D-09 참고코너 섹션 | T-31-29/30 | 에러 배너 0, 점수 미표시 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-13/T1 | 31-13 | 3 | calibrate harness — pair 계약(B4-04)/표본(H4-10)/version(M4-05) | T-31-56/60/64 | before/after hash, after keypoint, PASS4/FAIL8 blocked | script+assert | `python backend/scripts/calibrate_visual_gates.py --dry && test -f .../CALIBRATION.json` | ⬜ pending |
| 31-13/T2 | 31-13 | 3 | chosen 4값 + confusion + ACCEPTANCE (B4-05/M4-03) | — | training 더 엄격 없으면 blocked, RESULTS 동기화 | script+assert | CALIBRATION.json 4값+confusion assert | ⬜ pending |
| 31-11/T1 | 31-11 | 3 | jest-expo 정당성 | T-31-SC | npmjs 확인 후 설치 | manual + `npx jest --listTests` | — | ⬜ pending |
| 31-11/T2 | 31-11 | 3 | ApiError + 상태 순수 로직 | T-31-45 | typed code 분기 | unit (jest) | `cd app && npx jest src/lib/__tests__/visualCards.test.ts` | ⬜ pending |
| 31-11/T3 | 31-11 | 3 | 통합 (무조건 훅, H-02 재서명) | T-31-46/47 | URL 소비 0, 폴링 0 | unit (jest) + typecheck | `cd app && npx jest && npm run typecheck` | ⬜ pending |
| 31-09/T1 | 31-09 | 4 | claim + outboxSeq state machine + DLQ + async-only + moderation clear (B4-01/02/03) | T-31-32/33/62 | claim already_claimed/stale no-op, crash-injection 5지점, sync→vendor_error | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | ⬜ pending |
| 31-09/T2 | 31-09 | 4 | fetch/judge/pose_check/postprocess (H4-01/03/05, B4-05) | T-31-34/35/36/63 | JPEG→PNG, postprocessing durable, versionId cleanup, 4 env 분리 | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | ⬜ pending |
| 31-09/T3 | 31-09 | 4 | rotation streaming + dispatcher(pagination age) + reconciler | T-31-37/58 | upload_file, 실 backlog age metric, reconcile | unit | `python -m pytest backend/tests -q` | ⬜ pending |
| 31-10/T1 | 31-10 | 5 | 재서명 + exact guard + validator | T-31-41 | exact basename + status done + failed stale 404 | unit | `python -m pytest backend/tests/phase31/test_visual_url.py -x -q` | ⬜ pending |
| 31-10/T2 | 31-10 | 5 | 원자 요청 + outboxSeq dispatch + M-06 (B4-01) | T-31-38/39/40/42 | fail-closed env, send 실패→pending 잔존, mark(action+seq) | unit | `python -m pytest backend/tests/phase31/test_visual_request.py -x -q` | ⬜ pending |
| 31-10/T3 | 31-10 | 5 | upload-first+full-hash(M4-04)+VersionId(H4-03) + IaC(4 게이트/H3-09) + ObjectLock dry-run(H4-04) | T-31-43/44/54/55 | head sha256 대조 block, template strict ordering, ObjectLock fail-closed | lint+unit | `(cd backend && sam validate --lint) && python -m pytest backend/tests/phase31/test_visual_dispatch.py -x -q` | ⬜ pending |
| 31-12/T1 | 31-12 | 6 | 3중 blocked/ordering 게이트 + dispatcher build (H4-09) | T-31-66 | RESULTS/CALIBRATION/template env 일치, DispatchFunction build 산출물 | full suite | `python -m pytest backend/tests -q && (cd backend && sam validate --lint)` | ⬜ pending |
| 31-12/T2 | 31-12 | 6 | live mutation checkpoint + M4-01 경로 + Object Lock fail gate (H4-04) | T-31-55/68 | 승인 + before rollback + get 검증 + 403 중단 | manual (human-action) | — | ⬜ pending |
| 31-12/T3 | 31-12 | 6 | 배포(flag OFF) + 401/503/404 + IAM send-only iam_probe (H4-02) | T-31-48/49/67 | receive/delete 금지, worker 로그 소비 | manual (human-action) | — | ⬜ pending |
| 31-12/T4 | 31-12 | 6 | 실 E2E 2종 + versioned 잔존 0(H4-03) + OTA + UAT | T-31-50/51 | list-object-versions 0, E2E PASS 전 완료 금지 | integration | `test -f 31-HUMAN-UAT.md && grep -q "D-10" ...` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Fault-Injection Matrix (M2-04 + 3차 §6 + 4차 §6 확장 — nyquist 재선언 근거)

내구성 주장은 happy-path mock 이 아니라 아래 주입 테스트로 증명한다. **원칙: "재전달 → CAS no-op 멱등" 은 PASS 기준이 아니다. 모든 crash/replay 테스트 최종 기준 = `terminal 도달 + 외부 create/판정 중복 0 + job/analysis 일치 + PII 잔존 없음`.**

| Fault | 주입 지점 | 기대 동작 | Task | 4차 §8 gate |
|-------|-----------|-----------|------|---------|
| **poll sender send 후, fetch 가 judge pending 기록, poll sender 늦게 mark** | 31-02 mark_visual_job_dispatched | **이전 mark False(action/seq 불일치) — judge pending 유지, 다음 continuation 미소거** | 31-02/T3 | 2(B4-01) |
| **같은 {action,outboxSeq} 메시지 2개 동시** | 31-09 claim | **claim 1개만 'claimed'·나머지 already_claimed → 외부(Gemini/vendor) 호출 1회** | 31-09/T1 | 3(B4-01) |
| **old poll seq 재전달 (polling self-loop 후)** | 31-09 claim / 31-02 transition | **claim 'stale' no-op, attempt/nextAction 불변 (새 outboxSeq 가 old 무력화)** | 31-09/T1 + 31-02/T3 | 2(B4-01) |
| crash: vendor create 직전 | 31-09 _action_create | lease 만료 후 'create_unconfirmed' — 자동 재생성 0 | 31-09/T1 | (B2-02) |
| crash: vendor 2xx 직후·taskId write 전 | 31-09 _action_create | 동일 — 중복 과금 0 | 31-09/T1 | (B2-02) |
| **crash: polling/fetching/judging/pose_checking CAS 직후·send 전** | 31-09 각 전이 (outbox 기록됨) | **dispatcher 가 다음 action 1회+ 발행 → terminal, 외부 create 중복 0** | 31-09/T1 + T3(dispatcher) | 1·2(B4-01) |
| **sync image create succeeded (taskId 없음)** | 31-09 _action_create | **'vendor_error' 종결(async-only) — fetching 진입 0 (릴리스 게이트가 sync 후보 blocked)** | 31-09/T1 + 31-01/T3 | 4(B4-02) |
| **moderation T1 blocked → T2 create 2xx 후 crash** | 31-09 poll blocked → retry_ready → create | **retry_ready 가 taskId=None·attempt=0 clear + generation+1 → T1 재-poll 0, T2 중복 create 0, create_unconfirmed** | 31-09/T1 | (B4-03) |
| **crash: pose_checking→postprocessing 후·postprocess 전 / postprocess 중 crash** | 31-09 _action_postprocess | **재전달 postprocess 재개 (pair store + versionId cleanup + finalize 전부 idempotent) → 두 문서 일치, pair/cleanup 유실 0** | 31-09/T2 | 8(H4-01) |
| **finalize commit 응답 유실** | 31-09/31-02 finalize | **재전달 'stale' no-op 이어도 job·analysis 일치** | 31-09/T2 + 31-02/T3 | (B3-02) |
| **invariant: job terminal ↔ analysis result 일치** | 31-02 finalize property | 어떤 crash 조합에서도 (job done ⟺ analysis done) | 31-02/T3 | (B3-02) |
| **finalize caller 가 틀린 uid/analysisId/kind 주입** | 31-02 finalize | **job 문서 파생 값 사용 (cross-analysis tampering 차단); done+display failed 또는 failed+key → ValueError** | 31-02/T3 | (H4-07) |
| **calibration manifest dry-run** | 31-13 --dry-run | **before/after 각 hash 검증 + after keypoint provenance 대상 일치** | 31-13/T1 | 6(B4-04) |
| **chosen 4값 template mapping** | 31-10 template 파싱 + 31-12 게이트 | **env 4값 == chosen exact + TRAINING_JUDGE_CONFIDENCE > DISPLAY AND TRAINING_POSE_TOL < DISPLAY strict ordering** | 31-10/T3 + 31-12/T1 | 5·7(B4-05) |
| **JPEG 벤더 출력 → .png key** | 31-09 fetch | **safe_decode→PNG 재인코딩: PNG magic bytes + ContentType image/png + sha256 정규화 PNG** | 31-09/T2 | (H4-05) |
| **versioned visual-input cleanup** | 31-09 postprocess/finalize + 31-12 E2E | **VersionId 지정 삭제 + list-object-versions Versions/DeleteMarkers 0 (aws s3 ls 거짓 0 아님)** | 31-09/T2 + 31-12/T4 | (H4-03) |
| **Object Lock default retention** | 31-10 dry-run + 31-12 apply | **dry-run blocked 플래그 + apply 403 시 진행 금지·비정상 종료 (별도 bucket 요구)** | 31-10/T3 + 31-12/T2 | (H4-04) |
| **pending 100건 중 뒤쪽 overdue** | 31-02 list_dispatch_pending | **pagination bounded 전량 스캔 → overdue 전부 dispatch, backlog age 실제값, first-N slice starvation 0, truncated 플래그** | 31-02/T3 + 31-09/T3 | (H4-08) |
| replay: duplicate `_process` after done | 31-10 enqueue | 완전 no-op — S3/표시/SQS 불변 (done 되감기 0) | 31-10/T3 | (B3-03) |
| **replay: worker done 후 producer 늦은 pending** | 31-10 enqueue vs worker | done 이 pending 되감기 0 (pending 은 reserve transaction 안에서만) | 31-10/T3 | 5(B3-03) |
| **crash: reserve 후 S3 put 전 / S3 exception** | 31-10 enqueue (upload-first) | vendor create 0 — S3 put/head 성공 후에만 reserve | 31-10/T3 | 4(B3-03) |
| **16hex srcKey 충돌/변조** | 31-10 enqueue (M4-04) | **기존 head Metadata full sha256 != 신규 → block (reserve 0·SQS 0)** | 31-10/T3 | (M4-04) |
| **concurrency: 동시 2 enqueue** | 31-02 reserve run_contended | job 1·counter +1·외부 create 1회 | 31-02/T3 | (§6) |
| **직렬화 3면: URL 부재** | 31-09 종료 후 | job/analysis 직렬화 + SQS body + caplog 전부 'http(s)://'/'outputUrl'/'signedUrl' 부재 | 31-09/T1 | 6(H3-01·M3-04) |
| redirect: 실 301/302/303/307/308 | 31-05 TLS local server | 전부 VendorDownloadError('redirect') — scheme gate 우회 금지 | 31-05/T2 | (H3-05) |
| **safe_decode bomb** | 31-05/06 decode | **압축 20MB 이하 대해상도 PNG → decode 전 typed 거부 (Gemini/Pod 호출 0)** | 31-05/T2 + 31-06/T2 | (H4-06) |
| oversize/RSS: 대용량 스트림 | 31-05 isolated subprocess | 파일 스트리밍 peak RSS 제한 + 플랫폼 정규화 JSON | 31-05/T2 | (H3-06) |
| Gemini judge body 상한 | 31-09 judge (정규화 후) | serialized body < 16MB, 초과 = 'judge_input_too_large' (worker prepare 선호출 0 — M4-02) | 31-09/T2 | (H3-03) |
| /pose-image 상한 | 31-09 pose_check | pose 전용 resize/re-encode 후 상한 준수 | 31-09/T2 | (H3-04) |
| pair partial put 실패 (1/2/3번째) | 31-07 store_training_pair | commit marker 없는 부분 pair 잔존 0 | 31-07/T2 | (H3-07) |
| **pair consumer marker 강제** | 31-07 list_committed_pairs | **meta 없는 before/after prefix enumeration 제외** | 31-07/T1 | (H4-11) |
| versioned bucket 삭제 | 31-07 삭제 스크립트 | list_object_versions Versions+DeleteMarkers 전부 삭제 → noncurrent 0 | 31-07/T2 | (H3-08) |
| key rotation: HMAC v1→v2 후 삭제 | 31-07 삭제 스크립트 | retired v1 재계산으로 삭제 성공 | 31-07/T2 | (H3-11) |
| malformed SQS 메시지 | 31-09 handler | batchItemFailures → DLQ 증거 | 31-09/T1 | (M2-02) |
| **iam_probe send-only** | 31-09 handler + 31-12 canary | **worker 외부 side-effect 0 + 로그 소비 확인, production queue receive/delete 0** | 31-09/T1 + 31-12/T3 | (H4-02) |
| template drift | 31-10 파싱 assert | visibility >= 6×timeout + maxReceiveCount >= 5 + DispatchFunction concurrency 1 + worker schedule 부재 + OutboxAge alarm + 4 게이트 env | 31-10/T3 | (H3-09/H4-09) |
| **composite index 회피** | 31-02 list_dispatch_pending | 단일 등가 쿼리(dispatchState=='pending') + __name__ pagination + in-memory due 필터 — 복합 range 미발생 | 31-02/T3 | (H4-08) |

---

## §8 Acceptance Gate 추적표 (4차 리뷰 실행 승인 조건 11종)

| # | 조건 | 플랜 위치 |
|---|------|-----------|
| 1 | 모든 outbox 에 generation 과 별개의 action instance ID(outboxSeq) | 31-02/T2·T3 (outboxSeq 필드 + transition) |
| 2 | sent ACK 가 expected action+instance CAS, 다음 outbox 미소거 | 31-02/T3 (mark_visual_job_dispatched action+seq CAS) + §6 clobber 테스트 |
| 3 | worker 가 외부 side-effect 전 action instance lease/claim — duplicate 실행 차단 | 31-02/T3 (claim_visual_job_action) + 31-09/T1 (claim 선행) |
| 4 | sync image 모델 지원 여부 명시 결정, taskId 없는 fetching 부재 | 31-01/T3 (async-only blocked) + 31-05/T1 (IMAGE_ENGINE_SYNC) + 31-09/T1 (sync→vendor_error) |
| 5 | moderation retry 가 이전 taskId/attempt/lease atomic clear | 31-02/T3 (polling→retry_ready clear + generation+1) + 31-09/T1 |
| 6 | calibration manifest 가 before/after pair + 각 hash 표현 | 31-01/T3 (pair 계약 manifest) + 31-13/T1 (hash 재검증) |
| 7 | display/training confidence + pose tolerance 4값 전부 template/worker 소비 | 31-13 (chosen 4값) + 31-10/T3 (4 env + strict ordering build gate) + 31-09/T2 (4 env) |
| 8 | pair store + temp cleanup 이 crash 후 재개 가능 durable action | 31-02/T2 (postprocessing state) + 31-09/T2 (_action_postprocess idempotent) |
| 9 | versioned visual-input cleanup + E2E 실제 version 잔존 0 | 31-09/T2 (VersionId 삭제) + 31-10/T3 (dry-run) + 31-12/T4 (list-object-versions) |
| 10 | Object Lock 이 개인정보 retention/delete 와 충돌 시 배포 차단 | 31-10/T3 (dry-run fail-closed) + 31-12/T2 (403 중단) |
| 11 | 31-12 가 VisualDispatchFunction/iam_probe/current lifecycle 경로 기준 갱신 | 31-12/T1 (dispatcher build) + T2 (M4-01 경로) + T3 (iam_probe send-only) |

> 참고: 2차 §8 16종 + 3차 §8-3 11종은 위 fault matrix + 이 표에 흡수됨. 4차 리뷰 narrow 5차 검증 축 = outbox instance ownership(gate 1·2·3) / sync·async(gate 4) / moderation reset(gate 5) / calibration pair·env 소비(gate 6·7).

---

## Wave 0 Requirements

- [ ] `backend/tests/phase31/` conftest + 9 테스트 파일 (run_contended/commit_lost) — **31-02/T1**
- [ ] DashScope urllib mock + _FakeTransaction fixture — **31-02/T1**
- [ ] app jest 러너 — **31-11/T1** (checkpoint 통과 후)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실기기 UX — D-09/D-10 2D 뷰어·교정 이미지·회전 카드 | D-09/D-10 | 실기기 렌더 자동화 불가 | 31-HUMAN-UAT.md 적립 — 31-12/T4 |
| 화살표 시각 게이트 | D-11 | 실 fixture PNG 시각 판정 | 31-12/T4 zoom PNG Claude Read + UAT |
| 라이브 lifecycle/SSM mutation + Object Lock | H2-09/H4-04 | put=전체 교체, belle 승인 | 31-12/T2 — before rollback + get 검증 + 403 중단 |
| sam deploy 2회 (OFF/ON) | 배포 | auto-mode classifier | belle `!` — 31-12/T3·T4 |
| IAM 실권한 (send-only iam_probe) | H2-02/H4-02 | 실 계정 권한 — receive/delete 금지 | 31-12/T3 |
| 실 E2E 2종 + versioned 잔존 | D-05/D-06, H-07, H4-03 | Pod 재생성 + flag ON | **완료 필요조건** — 31-12/T4 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or checkpoint 게이트 (checkpoint 6건 = belle)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (31-02/T1, 31-11/T1)
- [x] Fault-Injection Matrix 가 task map 자동 테스트에 편입 (4차 §6 12종 확장 — ACK clobber/duplicate claim/old seq/sync block/moderation stale/pair manifest/chosen↔env/postprocess crash/versioned cleanup/ObjectLock/JPEG/pagination)
- [x] §8 4차 실행 승인 조건 11종 추적표 완비
- [x] No watch-mode flags
- [x] Feedback latency < 130s
- [x] `nyquist_compliant: true` re-declared (4차 §6 확장 반영 후)

**Approval:** planner 2026-07-19 (iteration4 targeted replan — 4차 리뷰 BLOCK 반영: B4-01~05 + H4-01~11 + M4-01~06, 31-01/02/05/06/07/09/10/12/13 targeted)
</content>
</invoke>
