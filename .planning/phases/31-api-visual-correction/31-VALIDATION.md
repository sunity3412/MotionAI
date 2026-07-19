---
phase: 31
slug: api-visual-correction
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-19
replanned: 2026-07-19
revision: iteration5
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 31-RESEARCH.md `## Validation Architecture` + 31-PLAN-REVIEW-ITERATION2/3/4/5.md 요구 게이트 (2차 §8 16종 + 3차 §8-3 11종 + 4차 §8 11종 + 5차 §6 fault matrix 10종 + §7 실행 허용 12조건).
> Task IDs = 2026-07-19 iteration5 targeted replan (13 plans / **6 waves** — 31-02/07/09/10/12 + Validation 만 수정, 나머지 4차 불변).
> `nyquist_compliant: true` 는 5차 §6 fault matrix 확장(claim commit 직후 crash 시간축·old owner lease 만료 늦은 write·동시 source HEAD/PUT·staging crash reuse·terminal replay·pair commit 후 crash+HMAC rotation·opt-out race·pair/cleanup durable·pending 1,200 drain·Object Lock canary) 후 재선언한 값이다.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend) / tsc --noEmit + jest-expo (app — jest 는 31-11 T1 checkpoint 후) |
| **Config file** | backend/requirements-dev.txt / app/jest.config.js (31-11 신설) |
| **Quick run command** | `python -m pytest backend/tests/phase31/<file>.py -x -q` |
| **Full suite command** | `python -m pytest backend/tests -q` + `cd app && npm run typecheck` (+ `npx jest` 31-11 이후) |
| **Estimated runtime** | ~140 seconds (실 302 local server 통합 + RSS 스트림 + claim 4상태/시계 + postprocess crash/consent race/exact-prefix cleanup 시나리오 포함) |

---

## Sampling Rate

- **After every task commit:** 해당 테스트 파일 `-x -q` 단건
- **After every plan wave:** `python -m pytest backend/tests -q` (+ 앱 wave 시 typecheck/jest)
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** 140 seconds

---

## Wave Structure (H2-08 + 3차 H3-02/H3-09 반영 — 4차/5차 불변)

| Wave | Plans | 비고 |
|------|-------|------|
| 1 | 31-01, 31-02, 31-03, 31-04 | 계약·target·상태(10종: postprocessing 포함)·outbox instance·claim 4상태 기반 |
| 2 | 31-05, 31-06, 31-07, 31-08 | 어댑터(safe_decode·async-only)·게이트·페어(caller-fixed pairId·payload-verify consumer)·앱 컴포넌트 |
| 3 | 31-11, 31-13 | 앱 통합 + calibration harness (31-05/06 실 코드 뒤, pair 계약 — H3-02/B4-04) |
| 4 | 31-09 | 워커+dispatcher — claim 4상태 + owner CAS + 성공/실패 postprocessing durable + exact-prefix cleanup |
| 5 | 31-10 | HTTP 표면·enqueue(upload-first+IfNoneMatch+terminal-replay)·IaC(4 게이트 env + truncated alarm) (H2-08) |
| 6 | 31-12 | 3중 blocked/ordering 게이트 + live mutation(Object Lock 실 canary) checkpoint + 배포 + E2E(multi-version 잔존 0) |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 31-01/T1 | 31-01 | 1 | H-04+H2-06/H2-10 privacy gate | T-31-04 | 보존일수·blur 위치 확정 | manual (decision) | — | ⬜ pending |
| 31-01/T2 | 31-01 | 1 | D-03 스모크 + async여부 기록 (B4-02) | T-31-01/02/03/65 | 키 리터럴 0, MAX_CALLS=8, async(taskId) 기록 | script+assert | `python -c "import ast; ast.parse(...)"` | ⬜ pending |
| 31-01/T3 | 31-01 | 1 | async-only blocked(B4-02) + pair manifest(B4-04) + PASS4/FAIL8(H4-10) | T-31-65 | sync-only→blocked, before/after pair 10키, 표본 하한 | script+assert | RESULTS/manifest(pair)/privacy 스키마 assert + grep Training | ⬜ pending |
| 31-02/T1 | 31-02 | 1 | 테스트 스캐폴드 + mock(run_contended/commit_lost/clock) | — | N/A | unit | `python -m pytest backend/tests/phase31 -x -q` | ⬜ pending |
| 31-02/T2 | 31-02 | 1 | 상태 10종 + typed 11종 + outbox/claim/pending-terminal 필드 + VISUAL_CLAIM_LEASE_MS | — | postprocessing 포함, dispatch_failed 부재, 신규 state 미추가 | unit | python -c import assert | ⬜ pending |
| 31-02/T3 | 31-02 | 1 | outbox CAS + claim 4상태 + owner CAS finalize + durable-cursor (B5-01/H5-03/H5-04/H5-06/H4-07) | T-31-05/06/07/52/56/57/62/63/69/70 | claim 4상태(busy/claimed/stale/completed), owner CAS, cursor 순환, finalize 파생 | unit | `python -m pytest backend/tests/phase31/test_visual_jobs.py -x -q` | ⬜ pending |
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
| 31-07/T1 | 31-07 | 2 | 페어 적재(strict+HMAC+caller-fixed pairId B5-03) + payload-verify consumer(H5-08/M5-05) | T-31-24/25/27/71 | is True strict, meta-read 멱등, payload hash 검증+quarantine, pagination | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | ⬜ pending |
| 31-07/T2 | 31-07 | 2 | 삭제 경로 (전 키 + rotation + versioned) | T-31-26 | key rotation 후 삭제, versionId 완전 삭제 | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | ⬜ pending |
| 31-08/T1 | 31-08 | 2 | 목업 선제시 + 카드 위치 | — | N/A | manual (decision) | — | ⬜ pending |
| 31-08/T2 | 31-08 | 2 | amended D-10 2D 뷰어 | T-31-28/31 | R3F 0, "3D" 문구 0 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-08/T3 | 31-08 | 2 | D-09 참고코너 섹션 | T-31-29/30 | 에러 배너 0, 점수 미표시 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-13/T1 | 31-13 | 3 | calibrate harness — pair 계약(B4-04)/표본(H4-10)/version(M4-05) | T-31-56/60/64 | before/after hash, after keypoint, PASS4/FAIL8 blocked | script+assert | `python backend/scripts/calibrate_visual_gates.py --dry && test -f .../CALIBRATION.json` | ⬜ pending |
| 31-13/T2 | 31-13 | 3 | chosen 4값 + confusion + ACCEPTANCE (B4-05/M4-03) | — | training 더 엄격 없으면 blocked, RESULTS 동기화 | script+assert | CALIBRATION.json 4값+confusion assert | ⬜ pending |
| 31-11/T1 | 31-11 | 3 | jest-expo 정당성 | T-31-SC | npmjs 확인 후 설치 | manual + `npx jest --listTests` | — | ⬜ pending |
| 31-11/T2 | 31-11 | 3 | ApiError + 상태 순수 로직 | T-31-45 | typed code 분기 | unit (jest) | `cd app && npx jest src/lib/__tests__/visualCards.test.ts` | ⬜ pending |
| 31-11/T3 | 31-11 | 3 | 통합 (무조건 훅, H-02 재서명) | T-31-46/47 | URL 소비 0, 폴링 0 | unit (jest) + typecheck | `cd app && npx jest && npm run typecheck` | ⬜ pending |
| 31-09/T1 | 31-09 | 4 | claim 4상태 state machine + busy batchItemFailures + owner CAS + async-only + moderation clear (B5-01/B4-02/B4-03/H5-04) | T-31-32/33/62/69/70 | busy→batchItemFailures, claimed 만 외부, crash-injection 5지점, sync→vendor_error | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | ⬜ pending |
| 31-09/T2 | 31-09 | 4 | fetch/judge/pose_check/postprocess (H4-01/H5-01/H5-02/H5-05/B5-02/B5-03, H4-05, B4-05, M5-01/M5-03) | T-31-34/35/36/63/71/72/73 | 성공+실패 postprocessing, exact-prefix cleanup, consent 재read, caller-fixed pairId, decode 분리 | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | ⬜ pending |
| 31-09/T3 | 31-09 | 4 | rotation streaming + dispatcher(cursor/lease-expired/age) + reconciler (H5-06/M5-02) | T-31-37/58 | upload_file, content-type exact, 실 backlog age, lease-expired 복구, reconcile | unit | `python -m pytest backend/tests -q` | ⬜ pending |
| 31-10/T1 | 31-10 | 5 | 재서명 + exact guard + validator | T-31-41 | exact basename + status done + failed stale 404 | unit | `python -m pytest backend/tests/phase31/test_visual_url.py -x -q` | ⬜ pending |
| 31-10/T2 | 31-10 | 5 | 원자 요청 + outboxSeq dispatch + M-06 (B4-01) | T-31-38/39/40/42 | fail-closed env, send 실패→pending 잔존, mark(action+seq) | unit | `python -m pytest backend/tests/phase31/test_visual_request.py -x -q` | ⬜ pending |
| 31-10/T3 | 31-10 | 5 | upload-first+IfNoneMatch+full-hash(B5-02)+terminal-replay 삭제 + IaC(4 게이트/H3-09/H5-06) + ObjectLock dry-run(H4-04/H5-07) | T-31-43/44/54/55 | IfNoneMatch 조건부, terminal-replay 즉시 삭제, template strict ordering + truncated alarm, ObjectLock canary_required | lint+unit | `(cd backend && sam validate --lint) && python -m pytest backend/tests/phase31/test_visual_dispatch.py -x -q` | ⬜ pending |
| 31-12/T1 | 31-12 | 6 | 3중 blocked/ordering 게이트 + dispatcher/2 alarm build (H4-09/H5-06) | T-31-66 | RESULTS/CALIBRATION/template env 일치, DispatchFunction build + OutboxScanTruncated alarm | full suite | `python -m pytest backend/tests -q && (cd backend && sam validate --lint)` | ⬜ pending |
| 31-12/T2 | 31-12 | 6 | live mutation checkpoint + M4-01 경로 + Object Lock 실 canary delete (H4-04/H5-07) | T-31-55/68 | 승인 + before rollback + get 검증 + canary PUT→VersionId→delete→versions 0 + 403 중단 | manual (human-action) | — | ⬜ pending |
| 31-12/T3 | 31-12 | 6 | 배포(flag OFF) + 401/503/404 + IAM send-only iam_probe (H4-02) | T-31-48/49/67 | receive/delete 금지, worker 로그 소비 | manual (human-action) | — | ⬜ pending |
| 31-12/T4 | 31-12 | 6 | 실 E2E 2종 + multi-version exact-prefix 잔존 0(B5-02) + OTA + UAT | T-31-50/51 | list-object-versions 0(multi-version), 실패 postprocessing 잔존 0, E2E PASS 전 완료 금지 | integration | `test -f 31-HUMAN-UAT.md && grep -q "D-10" ...` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Fault-Injection Matrix (M2-04 + 3차 §6 + 4차 §6 + 5차 §6 확장 — nyquist 재선언 근거)

내구성 주장은 happy-path mock 이 아니라 아래 주입 테스트로 증명한다. **원칙: "재전달 → CAS no-op 멱등" 은 PASS 기준이 아니다. 모든 crash/replay 테스트 최종 기준 = `terminal 도달 + 외부 create/판정 중복 0 + job/analysis 일치 + PII 잔존 없음(성공·실패 경로 동일)`. 성공 경로만 cleanup 하는 기대값은 무효 — correctedPose 실패도 postprocessing 경유로 cleanup 후 finalize (H5-05).**

### 4차까지 편입분

| Fault | 주입 지점 | 기대 동작 | Task |
|-------|-----------|-----------|------|
| poll sender 늦은 mark | 31-02 mark_visual_job_dispatched | 이전 mark False(action/seq 불일치) — judge pending 유지 | 31-02/T3 |
| old poll seq 재전달 | 31-09 claim / 31-02 transition | claim 'stale' no-op, attempt/nextAction 불변 | 31-09/T1 + 31-02/T3 |
| crash: vendor create 직전 | 31-09 _action_create | lease 만료 후 'create_unconfirmed'(postprocessing 경유) — 자동 재생성 0 | 31-09/T1 |
| crash: vendor 2xx 직후·taskId write 전 | 31-09 _action_create | 동일 — 중복 과금 0 | 31-09/T1 |
| sync image create succeeded | 31-09 _action_create | 'vendor_error'(async-only, postprocessing 경유) — fetching 진입 0 | 31-09/T1 + 31-01/T3 |
| moderation T1 blocked → T2 create 후 crash | 31-09 poll blocked → retry_ready → create | retry_ready clear + generation+1 + requestKey 새 gen → T1 재-poll 0 | 31-09/T1 |
| calibration manifest dry-run | 31-13 --dry-run | before/after 각 hash + after keypoint provenance 일치 | 31-13/T1 |
| chosen 4값 template mapping | 31-10 파싱 + 31-12 게이트 | env 4값 == chosen exact + strict ordering | 31-10/T3 + 31-12/T1 |
| JPEG 벤더 출력 → .png key | 31-09 fetch | safe_decode→PNG 재인코딩: PNG magic + image/png + 정규화 sha256 | 31-09/T2 |
| redirect 실 301/302/303/307/308 | 31-05 TLS local server | 전부 VendorDownloadError('redirect') | 31-05/T2 |
| safe_decode bomb | 31-05/06 decode | 압축 20MB 이하 대해상도 → decode 전 typed 거부 | 31-05/T2 + 31-06/T2 |
| pair partial put 실패(1/2/3) | 31-07 store_training_pair | commit marker 없는 부분 pair 잔존 0 | 31-07/T2 |
| versioned bucket 삭제 | 31-07 삭제 스크립트 | list_object_versions 전부 삭제 → noncurrent 0 | 31-07/T2 |
| malformed SQS 메시지 | 31-09 handler | batchItemFailures → DLQ 증거 | 31-09/T1 |
| iam_probe send-only | 31-09 handler + 31-12 canary | worker 외부 0 + 로그 소비, production receive/delete 0 | 31-09/T1 + 31-12/T3 |
| composite index 회피 | 31-02 list_dispatch_pending | 단일 등가 쿼리 + __name__ pagination + due 필터 | 31-02/T3 |

### 5차 §6 신규 편입 (10종 — 실행 허용 기준 직결)

| # | 시나리오 | 주입 지점 | 기대 결과 | Task | §7 조건 |
|---|----------|-----------|-----------|------|---------|
| 1 | **claim commit 직후 crash 시간축** | 31-09 claim + 31-02 dispatcher | 만료 전 외부 0(busy→batchItemFailures), 만료 후 정확히 한 worker 재claim, terminal 도달 | 31-09/T1 + 31-02/T3 | 1·2 |
| 2 | **old owner 가 lease 만료 후 늦게 결과 write** | 31-02 transition/finalize expect_claim_owner | owner/seq CAS 실패(None/stale), 새 worker 결과 보존 | 31-02/T3 + 31-09/T2 | (owner CAS) |
| 3 | **동일 source 두 invocation 동시 HEAD/PUT** | 31-10 enqueue IfNoneMatch | object content 1개, untracked version 0(412→full-hash reuse) | 31-10/T3 | 3 |
| 4 | **staging PUT 후 transition 전 crash** | 31-09 fetch staging | retry 가 deterministic key HEAD/full-hash reuse, extra version 0 | 31-09/T2 | 3 |
| 5 | **terminal job producer replay** | 31-10 enqueue | 신규 source version 0 또는 createdThisInvocation VersionId 즉시 삭제 | 31-10/T3 | (terminal replay) |
| 6 | **pair commit 후 finalize 전 crash + HMAC rotation** | 31-09 postprocess + 31-07 store | pairId job 고정 + meta-read 멱등 → pair prefix 1개, before/after/meta version 각 1, second PUT 0 | 31-09/T2 + 31-07/T1 | 6·7 |
| 7 | **pose_check 후 opt-out, postprocess 전** | 31-09 postprocess consent 재read | pair PUT 0, pairStoreStatus='skipped_consent', cleanup/finalize 정상 | 31-09/T2 | 8 |
| 8 | **pair/cleanup 일시 실패** | 31-09 postprocess self-loop | durable backoff(pairAttempt/cleanupAttempt) 후 재개, cleanup 성공(remaining 0) 또는 cleanup_blocked 전까지 terminal 금지 | 31-09/T2 | 9 |
| 9 | **pending 1,200개** | 31-02 list_dispatch_pending durable cursor | 여러 dispatcher invocation 후 1,200개 모두 발행, starvation 0, truncated 플래그 | 31-02/T3 + 31-09/T3 | 10 |
| 10 | **Object Lock enabled/default 없음** | 31-10 dry-run + 31-12 canary | dry-run canary_required + 실 canary VersionId delete·versions 0, 실패 시 flag OFF | 31-10/T3 + 31-12/T2 | 11 |
| — | **exact-prefix multi-version cleanup** | 31-09 postprocess + 31-12 E2E | job 단일 VersionId 미신뢰 — 전 Versions/DeleteMarkers 열거·삭제 후 list-object-versions 0 | 31-09/T2 + 31-12/T4 | 4 |
| — | **correctedPose 실패도 durable cleanup** | 31-09 _finalize_correctedpose_intent | create/poll/fetch/judge/pose 실패 전부 postprocessing 경유 → cleanup 후 finalize, 직접 finalize 0 | 31-09/T1 + T2 | 4 |
| — | **decode 오류 분리** | 31-09 fetch/judge | size/pixel=judge_input_too_large, corrupt/mismatch=invalid_output (reason 별 metric) | 31-09/T2 | (M5-01) |

---

## §7 실행 허용 12조건 추적표 (5차 리뷰)

| # | 조건 | 플랜 위치 | 테스트 |
|---|------|-----------|--------|
| 1 | same seq + active lease 와 same seq + expired lease 가 서로 다른 반환/queue 처리 | 31-02 claim(busy vs claimed) + 31-09(busy→batchItemFailures) | 31-02/T3 + 31-09/T1 |
| 2 | claim 후 crash message 가 lease 만료 뒤 반드시 재실행될 복구 주체 | 31-02 list_dispatch_pending(sent+lease-expired) + 31-09 dispatcher | 31-02/T3 + 31-09/T3 |
| 3 | source/staging concurrent·retry PUT 이 untracked version 미생성 | 31-10 IfNoneMatch + 31-09 staging deterministic reuse | 31-10/T3 + 31-09/T2 |
| 4 | correctedPose success/failure 모두 exact-prefix Versions/DeleteMarkers 0 뒤 finalize | 31-09 all-terminal postprocessing + exact-prefix cleanup | 31-09/T2 + 31-12/T4 |
| 5 | terminal producer replay 가 새 source PII 미잔존 | 31-10 terminal-replay 즉시 삭제 | 31-10/T3 |
| 6 | pairId/HMAC key version 이 postprocessing 진입 시 고정 | 31-09 pose_checking→postprocessing 고정 | 31-09/T2 |
| 7 | existing commit marker hash 일치 시 PUT 0, 불일치 시 overwrite 0 | 31-07 store_training_pair meta-read | 31-07/T1 |
| 8 | pair 저장 직전 current consent 재검증 | 31-09 postprocess consent 재read | 31-09/T2 |
| 9 | postprocess pair/cleanup retry 가 durable self-loop | 31-09 postprocessing→postprocessing pairAttempt/cleanupAttempt | 31-09/T2 |
| 10 | dispatcher 가 max_scan 보다 큰 backlog 를 순환하며 전부 처리 | 31-02 durable cursor + 31-10 truncated alarm | 31-02/T3 + 31-10/T3 |
| 11 | Object Lock canary delete 가 live checkpoint 에 명시 | 31-12 T2 canary delete | 31-12/T2 |
| 12 | 위 조건이 31-VALIDATION fault matrix + task별 automated test 에 연결 | 본 문서 §6 5차 표 + §7 추적표 | 전 task |

> 참고: 2차 §8 16종 + 3차 §8-3 11종 + 4차 §8 11종은 위 fault matrix 에 흡수됨. 5차 리뷰 6차 검증 축 = 3 불변식(crash-resumable claim / version 잔존 0 / idempotent pair) closure 확인만.

---

## Wave 0 Requirements

- [ ] `backend/tests/phase31/` conftest + 9 테스트 파일 (run_contended/commit_lost/clock) — **31-02/T1**
- [ ] DashScope urllib mock + _FakeTransaction fixture — **31-02/T1**
- [ ] app jest 러너 — **31-11/T1** (checkpoint 통과 후)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실기기 UX — D-09/D-10 2D 뷰어·교정 이미지·회전 카드 | D-09/D-10 | 실기기 렌더 자동화 불가 | 31-HUMAN-UAT.md 적립 — 31-12/T4 |
| 화살표 시각 게이트 | D-11 | 실 fixture PNG 시각 판정 | 31-12/T4 zoom PNG Claude Read + UAT |
| 라이브 lifecycle/SSM mutation + Object Lock 실 canary | H2-09/H4-04/H5-07 | put=전체 교체, belle 승인 | 31-12/T2 — before rollback + get 검증 + canary VersionId delete + 403 중단 |
| sam deploy 2회 (OFF/ON) | 배포 | auto-mode classifier | belle `!` — 31-12/T3·T4 |
| IAM 실권한 (send-only iam_probe) | H2-02/H4-02 | 실 계정 권한 — receive/delete 금지 | 31-12/T3 |
| 실 E2E 2종 + multi-version exact-prefix 잔존 | D-05/D-06, H-07, B5-02 | Pod 재생성 + flag ON | **완료 필요조건** — 31-12/T4 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or checkpoint 게이트 (checkpoint 6건 = belle)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (31-02/T1, 31-11/T1)
- [x] Fault-Injection Matrix 가 task map 자동 테스트에 편입 (5차 §6 10종 확장 — claim crash 시간축/old owner 늦은 write/동시 source PUT/staging crash reuse/terminal replay/pair crash+rotation/opt-out race/pair·cleanup durable/1,200 drain/Object Lock canary + exact-prefix multi-version + 실패 postprocessing + decode 분리)
- [x] §7 실행 허용 12조건 추적표 완비
- [x] "성공 경로만 cleanup" 기대값 제거 — 성공·실패 전부 postprocessing 경유 cleanup (H5-05)
- [x] No watch-mode flags
- [x] Feedback latency < 140s
- [x] `nyquist_compliant: true` re-declared (5차 §6 확장 반영 후)

**Approval:** planner 2026-07-19 (iteration5 targeted replan — 5차 리뷰 BLOCK 반영: B5-01~03 + H5-01~08 + M5-01~05, 31-02/07/09/10/12 + Validation targeted)
