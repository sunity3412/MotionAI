---
phase: 31
slug: api-visual-correction
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-19
replanned: 2026-07-19
revision: iteration9
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 31-RESEARCH.md + 31-PLAN-REVIEW-ITERATION2~9.md 요구 게이트 (…7차 fault 14종 + 8차 §7 15조건 + 9차 §7 실행 허용 15조건).
> Task IDs = 2026-07-20 iteration9 targeted replan (13 plans / **6 waves + Wave 0 bucket provision(+자기-완결 1일 lifecycle)** — 31-01/02/09/10/12 + CONTEXT + Validation 수정, 31-11 불변).
> **9차 핵심: reservation/janitor 를 '문서 CAS'에서 '실 S3 key ownership + crash-recoverable janitor lease'로 승격 — janitor claim lease 복구(B9-01), key-level ownership 문서 visualInputObjects/{hash}로 cross-reservation 동일-key 삭제 봉쇄(B9-02), 삭제 후보 expected∪created(B9-03), chosen bucket name 전파(B9-05), Wave 0 자기-완결 1일 lifecycle(H9-08).**
> **★belle SETTLED (CONTEXT): 즉시-삭제 privacy SLA 현행 유지 확정 + pair 단일 시도 손실 수용(B9-04 amended) — 이 두 축은 리뷰 재개 금지, closure 만 검증.**
> **8차 핵심: 7차 추가분(create CAS·reservation·janitor)의 선형화 결함 6 blocker 봉쇄 — begin_visual_job_create typed status(acquired→즉시 vendor create, no-op 0, B8-01), finalizer unconditional correctedPose gate(inputSealed=False 우회 0, B8-02) + cleanup_blocked 원자 clear(B8-03), dispatcher s3:GetObject(HeadObject 부재, B8-04), per-invocation immutable reservation(B8-05) + producer/janitor 공유 claim CAS 선형화(B8-06). pair 는 cleanup 만 durable·단일 시도(H8-02, 플라이휠 손실 belle 결정 위임).**
> **7차 핵심: 비-버저닝 버킷 아키텍처를 실 AWS 에 연결 — 신규 VisualInputBucket 을 31-01 Task1b(Wave 0)에서 provision(Never-versioned/PublicAccessBlock/SSE), worker s3:ListBucket 추가(cleanup 403 방지), Suspended 오판 차단(Status 부재만 통과), cleanupVerifiedAtMs 파라미터 handoff(done|failed 공통), upload-first 하드크래시 durable reservation+janitor, 버킷당 4 lifecycle 파일, D-06 완료알림 belle 결정(31-11 Task1c).**
> **6차 belle 아키텍처 조정: 임시 생체 프레임(correctedPose source/staging)은 신규 비-버저닝 전용 버킷(VisualInputBucket)으로 이동 — cleanup = 단일 delete + list-objects-v2 KeyCount 0(version 열거 소멸). 학습 페어(training/phase31/pairs/)만 versioned VideoBucket 유지 → version-aware 삭제·Object Lock canary 대상.**
> `nyquist_compliant: true` 는 5차 §6 확장 + 6차 §6 신규 축(claim owner→실행 snapshot handoff·새 outboxSeq claim clear·producer preflight/inputSealed·cleanup_blocked 비-terminal·same-seq expired claim 정확 필터·partial pair payload hash 검증·pair failed_config 비차단·version/lock IAM simulate·deterministic multi-object E2E) 후 재선언한 값이다.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend) / tsc --noEmit + jest-expo (app — jest 는 31-11 T1 checkpoint 후) |
| **Config file** | backend/requirements-dev.txt / app/jest.config.js (31-11 신설) |
| **Quick run command** | `python -m pytest backend/tests/phase31/<file>.py -x -q` |
| **Full suite command** | `python -m pytest backend/tests -q` + `cd app && npm run typecheck` (+ `npx jest` 31-11 이후) |
| **Estimated runtime** | ~145 seconds (실 302 local server 통합 + RSS 스트림 + claim dict 4상태/시계/snapshot handoff + postprocess crash/consent race/비-버저닝 단일 delete cleanup/cleanup_blocked 시나리오 포함) |

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
| 0 | 31-01 Task1b | **VisualInputBucket provision(Never-versioned/PublicAccessBlock/SSE/no-lock) — Wave 1 smoke·이후 전 단계 전제 (7차 B7-06)** |
| 1 | 31-01, 31-02, 31-03, 31-04 | 계약·target·상태·outbox·claim dict 4상태(snapshot handoff) + cleanup_verified_at_ms 파라미터/done|failed validator/read_visual_job(7차) 기반. 31-01 smoke 는 전용 버킷 사용 |
| 2 | 31-05, 31-06, 31-07, 31-08 | 어댑터(safe_decode·async-only)·게이트·페어(caller-fixed pairId·payload-verify consumer)·앱 컴포넌트 |
| 3 | 31-11, 31-13 | 앱 통합 + calibration harness (31-05/06 실 코드 뒤, pair 계약 — H3-02/B4-04) |
| 4 | 31-09 | 워커+dispatcher — claim dict 4상태(snapshot handoff) + owner/lease CAS + 성공/실패 postprocessing durable(inputSealed) + 비-버저닝 단일 delete cleanup + cleanup_blocked 비-terminal |
| 5 | 31-10 | HTTP 표면·enqueue(preflight+upload-first+inputSealed gate+terminal-replay/orphan 삭제)·IaC(신규 VisualInputBucket Parameter + 버전 액션 없는 IAM + lease build gate + ScannedOutboxMaxAge alarm) (H2-08) |
| 6 | 31-12 | 3중 blocked/ordering 게이트 + live mutation(페어 버킷 Object Lock 실 canary) checkpoint + 배포 + 버전/lock IAM simulate + E2E(H6-09 deterministic → VisualInputBucket KeyCount 0) |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 31-01/T1 | 31-01 | 1 | H-04+H2-06/H2-10 privacy gate | T-31-04 | 보존일수·blur 위치 확정 | manual (decision) | — | ⬜ pending |
| 31-01/T1b | 31-01 | 0 | VisualInputBucket provision (7차 B7-06/H7-05/H7-07/B7-02) | T-31-84 | Never-versioned(Status 부재)·PublicAccessBlock·SSE·no-lock·전용 버킷 | manual (human-action) | — | ⬜ pending |
| 31-01/T2 | 31-01 | 1 | D-03 스모크 + async여부 기록 (B4-02) | T-31-01/02/03/65 | 키 리터럴 0, MAX_CALLS=8, async(taskId) 기록 | script+assert | `python -c "import ast; ast.parse(...)"` | ⬜ pending |
| 31-01/T3 | 31-01 | 1 | async-only blocked(B4-02) + pair manifest(B4-04) + PASS4/FAIL8(H4-10) | T-31-65 | sync-only→blocked, before/after pair 10키, 표본 하한 | script+assert | RESULTS/manifest(pair)/privacy 스키마 assert + grep Training | ⬜ pending |
| 31-02/T1 | 31-02 | 1 | 테스트 스캐폴드 + mock(run_contended/commit_lost/clock) | — | N/A | unit | `python -m pytest backend/tests/phase31 -x -q` | ⬜ pending |
| 31-02/T2 | 31-02 | 1 | 상태 10종 + typed 10종 terminal + VISUAL_PRIVACY_BLOCKERS + outbox/claim/pending-terminal/privacy 필드 + VISUAL_CLAIM_LEASE_MS + sent cursor | — | postprocessing 포함, cleanup_blocked 비-terminal(privacy blocker), inputSealed/privacyBlocker/cleanupVerifiedAtMs, 신규 state 미추가 | unit | python -c import assert | ⬜ pending |
| 31-02/T3 | 31-02 | 1 | begin typed status(B8-01)+full write set(H9-03) + finalizer unconditional gate(B8-02)+cleanup_blocked clear(B8-03) + reservation/orphan state machine **+ janitor claim lease 복구(B9-01) + key-ownership 문서(B9-02) + nested tx 내부함수(H9-04) + orphan reopen(H9-07) + closed TTL(H9-06)** (8차 B8-01~06/H8-03 + 9차 B9-01/B9-02/H9-01/H9-03/H9-04/H9-06/H9-07) | T-31-…/85/86/87/88 | begin write set, done/failed×inputSealed False 거부, janitor claim crash 재claim, key ownership ref, nested tx 단일 commit, orphan reopen | unit | `python -m pytest backend/tests/phase31/test_visual_jobs.py -x -q` | ⬜ pending |
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
| 31-07/T1 | 31-07 | 2 | 페어 적재(strict+HMAC+caller-fixed pairId B5-03) + partial 재개 payload hash 검증(H6-04) + payload-verify consumer(H5-08/M5-05) | T-31-24/25/27/71/78 | is True strict, meta-read 멱등, 412 payload HEAD/GET hash 검증 후 resume·불일치 conflict, quarantine, pagination | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | ⬜ pending |
| 31-07/T2 | 31-07 | 2 | 삭제 경로 (전 키 + rotation + versioned + marker-pair pagination H6-06) | T-31-26 | key rotation 후 삭제, KeyMarker+VersionIdMarker paginator 완전 삭제 | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | ⬜ pending |
| 31-08/T1 | 31-08 | 2 | 목업 선제시 + 카드 위치 | — | N/A | manual (decision) | — | ⬜ pending |
| 31-08/T2 | 31-08 | 2 | amended D-10 2D 뷰어 | T-31-28/31 | R3F 0, "3D" 문구 0 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-08/T3 | 31-08 | 2 | D-09 참고코너 섹션 | T-31-29/30 | 에러 배너 0, 점수 미표시 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-13/T1 | 31-13 | 3 | calibrate harness — pair 계약(B4-04)/표본(H4-10)/version(M4-05) | T-31-56/60/64 | before/after hash, after keypoint, PASS4/FAIL8 blocked | script+assert | `python backend/scripts/calibrate_visual_gates.py --dry && test -f .../CALIBRATION.json` | ⬜ pending |
| 31-13/T2 | 31-13 | 3 | chosen 4값 + confusion + ACCEPTANCE (B4-05/M4-03) | — | training 더 엄격 없으면 blocked, RESULTS 동기화 | script+assert | CALIBRATION.json 4값+confusion assert | ⬜ pending |
| 31-11/T1 | 31-11 | 3 | jest-expo 정당성 | T-31-SC | npmjs 확인 후 설치 | manual + `npx jest --listTests` | — | ⬜ pending |
| 31-11/T1c | 31-11 | 3 | D-06 완료 알림 실체 결정 (7차 H7-06) | — | push 구현 vs amended decision | manual (decision) | — | ⬜ pending |
| 31-11/T2 | 31-11 | 3 | ApiError + 상태 순수 로직 | T-31-45 | typed code 분기 | unit (jest) | `cd app && npx jest src/lib/__tests__/visualCards.test.ts` | ⬜ pending |
| 31-11/T3 | 31-11 | 3 | 통합 (무조건 훅, H-02 재서명) | T-31-46/47 | URL 소비 0, 폴링 0 | unit (jest) + typecheck | `cd app && npx jest && npm run typecheck` | ⬜ pending |
| 31-09/T1 | 31-09 | 4 | claim 4상태 + busy visibility + snapshot handoff + owner/lease CAS + internal transition send 0 + **begin status 분기(acquired→vendor create 1회, concurrent acquired 1/busy 1, B8-01/M8-04)** (B5-01/B6-01/B4-02/B4-03/H5-04/M6-03/7차 H7-01/8차 B8-01/M8-04) | T-31-32/33/62/69/70/75 | busy→change_visibility+batchItemFailures, claimed snapshot only, crash 5지점, sync→vendor_error, **H7-01 internal transition send 0, H7-02 create CAS** | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | ⬜ pending |
| 31-09/T2 | 31-09 | 4 | fetch/judge/pose_check/postprocess (H4-01/H5-01/H5-05/B6-03/B6-04/B5-03/H6-03/H6-05, H4-05, B4-05, M5-01/M6-04/M6-05 + 7차 B7-03/B7-04/H7-07/H7-08) | T-31-34/35/36/63/71/72/73/77 | 성공+실패 postprocessing(inputSealed), 단일 delete cleanup, cleanup_verified_at_ms 파라미터(B7-03), pair off critical path(H7-07), copy REPLACE metadata(H7-08), consent 재read, hash conflict, failed_config 비차단 | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | ⬜ pending |
| 31-09/T3 | 31-09 | 4 | rotation streaming + dispatcher + **janitor crash-recoverable(claim lease B9-01 + key ownership ref B9-02 + expected∪created B9-03 + predicate 표 H9-02) + create failure kind 분기 H9-09 + reconciliation H9-06** (7차 H7-04/8차 B8-06/H8-01/M8-05/9차 B9-01/B9-02/B9-03/H9-02/H9-09) | T-31-37/58/88 | janitor claim crash 재claim, 동일 key live ref, multi-object expected∪created, predicate 표, create kind 분기 | unit | `python -m pytest backend/tests -q` | ⬜ pending |
| 31-10/T1 | 31-10 | 5 | 재서명 + exact guard + validator | T-31-41 | exact basename + status done + failed stale 404 | unit | `python -m pytest backend/tests/phase31/test_visual_url.py -x -q` | ⬜ pending |
| 31-10/T2 | 31-10 | 5 | 원자 요청 + outboxSeq dispatch + M-06 (B4-01) | T-31-38/39/40/42 | fail-closed env, send 실패→pending 잔존, mark(action+seq) | unit | `python -m pytest backend/tests/phase31/test_visual_request.py -x -q` | ⬜ pending |
| 31-10/T3 | 31-10 | 5 | per-invocation reservation + **key ownership acquire/promote/release(B9-02) + TTL build gate(H9-01) + alarm 8종 exact resource(H9-05/M9-03) + chosen name dry-run(B9-05)** (8차 B8-05/B8-06/B8-04/H8-04 + 9차 B9-02/B9-05/H9-01/H9-05/M9-03) | T-31-43/54/73/76/80/81 | key ownership ref, TTL gate, alarm 8종, chosen name 하드코딩 0 | lint+unit | `(cd backend && sam validate --lint) && python -m pytest backend/tests/phase31/test_visual_dispatch.py -x -q` | ⬜ pending |
| 31-12/T1 | 31-12 | 6 | 3중 게이트 + build(5 alarm + worker ListBucket/PutMetricData IAM + 버전 액션 부재) (H4-09/H5-06/M6-01/H6-02/B6-02/7차 B7-01/H7-03) | T-31-66 | template env 일치, 5 alarm(Orphan/CleanupBlocked/PairConflict 포함), worker ListBucket 존재, 버전 액션 부재 | full suite | `python -m pytest backend/tests -q && (cd backend && sam validate --lint)` | ⬜ pending |
| 31-12/T2 | 31-12 | 6 | 버킷당 4파일 lifecycle put+교차 rollback + Never-versioned 재확인 + **canary get_object_retention/legal_hold 직접 API + AccessDenied fail-closed(H8-08)** + chosen-name 전파(H8-07) (H4-04/H5-07/H6-08/7차 B7-06/B7-07/H7-09 + 8차 H8-07/H8-08) | T-31-55/68/82/84 | 1:1 put, 교차 rollback, 전용 API canary, AccessDenied STOP | manual (human-action) | — | ⬜ pending |
| 31-12/T3 | 31-12 | 6 | 배포(flag OFF) + 401/503/404 + iam_probe + worker s3:ListBucket allowed(B7-01) + Pod user VisualInputBucket(H7-02) + 버전/lock simulate (H4-02/B6-02/H6-08/7차 B7-01/H7-02) | T-31-48/49/67/79/81 | worker ListBucket allowed + 실 role canary, Pod IAM, 버전 액션 denied | manual (human-action) | — | ⬜ pending |
| 31-12/T4 | 31-12 | 6 | 실 E2E 2종 + Never-versioned 재확인(B7-02) + H6-09 deterministic → **worker-role cleanup 증명**(M7-04) → KeyCount 0(IsTruncated M7-01) + OTA + UAT | T-31-50/51 | Status 부재 재확인, worker-role/CloudWatch 증명, KeyCount 0, E2E PASS 전 완료 금지 | integration | `test -f 31-HUMAN-UAT.md && grep -q "D-10" ...` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Fault-Injection Matrix (M2-04 + 3차 §6 + 4차 §6 + 5차 §6 + 6차 §6 확장 — nyquist 재선언 근거)

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
| 3 | **동일 source 두 invocation 동시 HEAD/PUT** | 31-10 enqueue IfNoneMatch/409 | object content 1개, untracked object 0(412/409→full-hash reuse) | 31-10/T3 | 3 |
| 4 | **staging PUT 후 transition 전 crash** | 31-09 fetch staging | retry 가 deterministic key HEAD/full-hash reuse(비-버저닝), extra object 0 | 31-09/T2 | 3 |
| 5 | **terminal job producer replay** | 31-10 preflight+enqueue | preflight job 존재→PUT 0; race 시 inputSealed/terminal → createdThisInvocation object 즉시 delete_object(비-버저닝) | 31-10/T3 | 5 |
| 6 | **pair commit 후 finalize 전 crash + HMAC rotation** | 31-09 postprocess + 31-07 store | pairId job 고정 + meta-read 멱등 → pair prefix 1개, before/after/meta version 각 1, second PUT 0 | 31-09/T2 + 31-07/T1 | 6·7 |
| 7 | **pose_check 후 opt-out, postprocess 전** | 31-09 postprocess consent 재read | pair PUT 0, pairStoreStatus='skipped_consent', cleanup/finalize 정상 | 31-09/T2 | 8 |
| 8 | **pair/cleanup 일시 실패** | 31-09 postprocess self-loop | durable backoff(pairAttempt/cleanupAttempt) 후 재개, cleanup 성공(remainingObject 0) 또는 cleanup_blocked(비-terminal) 전까지 terminal 금지 | 31-09/T2 | 9 |
| 9 | **pending 1,200개** | 31-02 list_dispatch_pending durable cursor | 여러 dispatcher invocation 후 1,200개 모두 발행, starvation 0, truncated 플래그 | 31-02/T3 + 31-09/T3 | 10 |
| 10 | **Object Lock enabled/default 없음(페어 버킷)** | 31-10 dry-run + 31-12 canary | dry-run canary_required + 실 canary VersionId delete·versions 0(retention/hold HEAD 권한), 실패 시 flag OFF | 31-10/T3 + 31-12/T2 | 11 |
| — | **비-버저닝 exact-prefix cleanup** | 31-09 postprocess + 31-12 E2E | 단일 delete_object 완전 소거 — list-objects-v2 exact-prefix KeyCount 0(version 열거 불필요) | 31-09/T2 + 31-12/T4 | 4 |
| — | **correctedPose 실패도 durable cleanup** | 31-09 _finalize_correctedpose_intent | create/poll/fetch/judge/pose 실패 전부 postprocessing 경유(inputSealed) → cleanup 후 finalize, 직접 finalize 0 | 31-09/T1 + T2 | 4 |
| — | **decode 오류 분리** | 31-09 fetch/judge | size/pixel=judge_input_too_large, corrupt/mismatch=invalid_output (reason 별 metric) | 31-09/T2 | (M5-01) |

### 6차 §6 신규 편입 (실행 허용 기준 직결)

| # | 시나리오 | 주입 지점 | 기대 결과 | Task | §7 조건 |
|---|----------|-----------|-----------|------|---------|
| 11 | **claim owner→실행 snapshot handoff** | 31-09 claim + 31-02 transition | claimed 시 worker 가 claim 반환 snapshot 만 사용(pre-claim job grep 0), owner+seq+미만료 lease CAS 통과로 정상 전이 성공 | 31-09/T1 + 31-02/T3 | 1·2 |
| 12 | **poll claimed → retry_ready → create** | 31-09 poll blocked + 31-02 transition | 새 outboxSeq 생성 시 claim 필드 원자 clear, create 전이가 owner CAS 로 막히지 않음 | 31-09/T1 + 31-02/T3 | 3 |
| 13 | **expired owner A 뒤 owner B 재claim, A late write** | 31-02 transition/finalize expect_claim_owner+now_ms | owner/seq/미만료 lease CAS 실패(None/stale), B 결과 보존 | 31-02/T3 + 31-09/T2 | (owner/lease CAS) |
| 14 | **sent-unclaimed 1,200 + 마지막 expired-claimed 1** | 31-02 list_dispatch_pending sent cursor | unclaimed(lease 0)·구 seq claim 재발행 0, same-seq expired claim 만 cursor 순환 복구 | 31-02/T3 + 31-09/T3 | 4 |
| 15 | **cleanup re-list 0 직후 producer replay PUT** | 31-10 preflight + inputSealed gate | 새 입력이 selected/sealed 와 불일치 시 즉시 delete_object, terminal 뒤 KeyCount 0 | 31-10/T3 | 5 |
| 16 | **reserve commit 전 실패 / commit response loss** | 31-10 enqueue orphan 보상 | job 재read 후 selected object 만 유지, orphan delete + VisualOrphanSourceObject metric | 31-10/T3 | (H6-02) |
| 17 | **cleanup 5회 실패** | 31-09 postprocess | job postprocessing/cleanup_blocked 유지, analysis pending, VisualCleanupBlocked alarm, terminal 0 | 31-09/T2 | 6 |
| 18 | **partial pair before-only/after-only 재개** | 31-07 store_training_pair 412 | 기존 payload hash 일치만 resume, 불일치 meta PUT 0(conflict) | 31-07/T1 | 7 |
| 19 | **단일 key 다중 version 페이지 경계 삭제** | 31-07 delete script paginator | KeyMarker+VersionIdMarker pagination 후 exact 0, 누락/반복 0 | 31-07/T2 | (H6-06) |
| 20 | **staging/canonical deterministic key hash 불일치** | 31-09 fetch/pose_check | overwrite 0 + 'invalid_output'(postprocessing 경유) | 31-09/T2 | (H6-03) |
| 21 | **HMAC env invalid + pairEligible True** | 31-09 pose_check/postprocess | pairStoreStatus='failed_config' + pair PUT 0 + display correctedPose done(비차단) | 31-09/T2 | (H6-05) |
| 22 | **worker/pipeline 버전 IAM simulate** | 31-12 T1 grep + T3 simulate | worker/pipeline 버전 액션 denied·페어삭제/canary 버전·retention 권한 allowed | 31-12/T1 + T3 | (B6-02/H6-08) |
| 23 | **deterministic multi-object E2E cleanup** | 31-12 E2E-A | 2+ object 의도 생성 후 helper cleanup → VisualInputBucket KeyCount 0(before/after 기록) | 31-12/T4 | (H6-09) |
| 24 | **busy duplicate visibility 조정** | 31-09 handler | busy → change_message_visibility(남은 lease+jitter) + batchItemFailures, DLQ 오염 최소 | 31-09/T1 | (M6-03) |
| 25 | **pair conflict 즉시 quarantine / delete Errors** | 31-09 postprocess | conflict → 재시도 0 + quarantine/alarm; delete_objects Errors → failed count 반영 | 31-09/T2 | (M6-04/M6-05) |

### 7차 §6 신규 편입 (fault/IAM/live matrix — 실행 허용 기준 직결)

| # | 시나리오 | 주입 지점 | PASS 기준 | Task |
|---|----------|-----------|-----------|------|
| 26 | worker role 로 exact-prefix ListObjectsV2 | 31-10 IAM + 31-12 simulate/canary | s3:ListBucket(prefix) allowed, 타 prefix denied, cleanup/finalize terminal | 31-10/T3 + 31-12/T3 |
| 27 | bucket Status=Suspended | 31-10 dry-run + 31-12 checkpoint | dry-run/checkpoint/flag ON 모두 blocked | 31-10/T3 + 31-12/T2·T4 |
| 28 | bucket Status key 부재 | 31-10 dry-run + 31-12 | unversioned gate 통과 + Versions/DeleteMarkers 0 | 31-10/T3 + 31-12/T2 |
| 29 | remaining 0, job cleanupVerified=0 done finalize | 31-02 finalize + 31-09 postprocess | cleanup_verified_at_ms 파라미터 병합 후 done 성공 + job 문서 기록 | 31-02/T3 + 31-09/T2 |
| 30 | correctedPose done/failed × inputSealed=False × cleanupVerified=0 (네 조합) | 31-02 finalize validator | 전부 ValueError(unconditional gate — inputSealed=False 우회 0, 8차 B8-02) | 31-02/T3 + 31-09/T2 |
| 31 | src PUT 직후 hard crash | 31-10 reservation + 31-09 janitor | durable reservation/janitor 가 lifecycle 대기 없이 prefix 0 | 31-10/T3 + 31-09/T3 |
| 32 | src 성공→trainingSrc 실패(option-b) | 31-10 created_keys 보상 | created_keys 역순 delete 또는 durable visualOrphans 등록 | 31-10/T3 |
| 33 | terminal cleanup 뒤 stale producer PUT→hard crash | 31-09 janitor | janitor 가 object 0 복구 | 31-09/T3 |
| 34 | VisualInputBucket 미존재 | 31-01 Task1b | 승인 전 create 금지, 승인 후 보안 속성+Status 부재 검증 | 31-01/T1b |
| 35 | 두 bucket lifecycle 두번째 실패 | 31-12 T2 교차 rollback | 첫 bucket 포함 둘 다 before rollback | 31-12/T2 |
| 36 | creating internal transition | 31-09 _advance | SQS send 0, action null 메시지 0 | 31-09/T1 |
| 37 | old create seq 가 retry_ready 도착 | 31-09 begin_visual_job_create | due/seq/gen CAS 실패, vendor create 0 | 31-09/T1 |
| 38 | cleanup_blocked/orphan/pair conflict metric | 31-10 IAM + 31-12 build | 실 producer role PutMetricData allowed + 5 alarm 존재 | 31-10/T3 + 31-12/T1 |
| 39 | 회전 앱 닫은 뒤 완료(D-06) | 31-11 Task1c 결정 | push 알림+deep link 또는 amended decision 존재 | 31-11/T1c |

---

### 8차 §7 신규 편입 (선형화·privacy·IAM — 실행 허용 직결)

| # | 시나리오 | 주입 지점 | PASS 기준 | Task |
|---|----------|-----------|-----------|------|
| 40 | 최초 reserved create | 31-09 _action_create + 31-02 begin | begin acquired → vendor create 정확 1회(creating no-op 0) | 31-09/T1 + 31-02/T3 |
| 41 | concurrent same-seq create | 31-02 begin_visual_job_create | acquired 1·busy/stale 1·vendor create total 1 (M8-04) | 31-09/T1 + 31-02/T3 |
| 42 | correctedPose done/failed × inputSealed=False | 31-02 finalizer | 네 조합 전부 ValueError(unconditional gate B8-02) | 31-02/T3 + 31-09/T2 |
| 43 | cleanup 5회 실패→blocked→remaining 0 | 31-02 finalizer + 31-09 postprocess | cleanup_verified>0 시 privacyBlocker 원자 clear+terminal 한 transaction(B8-03) | 31-02/T3 + 31-09/T2 |
| 44 | template `s3:HeadObject` 존재 | 31-10 template + 31-12 build | 전 template HeadObject 0, dispatcher GetObject/DeleteObject/prefix ListBucket (B8-04/H8-04) | 31-10/T3 + 31-12/T1 |
| 45 | concurrent producer A/B reservation | 31-10 create_input_reservation | per-invocation immutable, A/B overwrite 0, 두 key 모두 소유/삭제(B8-05) | 31-10/T3 + 31-02/T3 |
| 46 | janitor read → producer reserve → janitor delete | 31-02 reservation CAS | claim_for_job↔claim_for_janitor 배타, 유효 job 입력 delete 0(B8-06) | 31-02/T3 + 31-09/T3 |
| 47 | reservation/orphan 1,200건 | 31-09 janitor bounded cursor | starvation 0 drain + oldest-age/failure alarm(H8-01/M8-05) | 31-09/T3 |
| 48 | pair network 실패 | 31-09 postprocess | user terminal 미차단 + cleanup 만 durable, pair 단일 시도(H8-02, 플라이휠 손실 amended) | 31-09/T2 |
| 49 | Wave 0 bucket policy/lifecycle | 31-01 Task1b + 31-12 | 보안속성만(lifecycle 이연 H8-05) + policy Sid merge/rollback(H8-06) + chosen name 전파(H8-07) | 31-01/T1b + 31-12/T2 |
| 50 | Object Lock canary AccessDenied | 31-12 Task2 | get_object_retention/legal_hold 직접 호출 + AccessDenied fail-closed(H8-08) | 31-12/T2 |

---

### 9차 §7 신규 편입 (reservation/janitor crash-safe — 실행 허용 직결)

| # | 시나리오 | 주입 지점 | PASS 기준 | Task |
|---|----------|-----------|-----------|------|
| 51 | janitor claim 직후 crash | 31-02 claim lease + 31-09 janitor | claimLease 만료 후 재claim → delete+HEAD404+close 완료(B9-01) | 31-02/T3 + 31-09/T3 |
| 52 | expired A + live B 동일 key | 31-02 key ownership + 31-09 janitor | janitor(A) live ref count>0 → K delete 0(B9-02) | 31-02/T3 + 31-09/T3 |
| 53 | src record→trainingSrc 2xx→record 전 crash | 31-09 janitor | expected∪created 로 두 key 모두 삭제(B9-03) | 31-09/T3 + 31-10/T3 |
| 54 | janitor predicate 표 | 31-09 janitor | terminal/inputSealed/mismatched 삭제, matching nonterminal unsealed 보존(H9-02) | 31-09/T3 |
| 55 | begin acquired write set | 31-02 begin | outboxSeq+1/nextAction None/dispatchState None/claim clear 고정, old create stale(H9-03) | 31-02/T3 |
| 56 | reserve+reservation claim nested tx | 31-02 _claim_..._tx | 단일 commit/commit-loss 단위(H9-04) | 31-02/T3 |
| 57 | closed orphan 동일 key 재발 | 31-02 upsert reopen | closed→open+generation+1+attempt 0(H9-07) | 31-02/T3 |
| 58 | reservation TTL build gate | 31-10 build | PipelineTimeout*1000+margin<=TTL(H9-01) | 31-10/T3 |
| 59 | alternative bucket name | 31-01/10/12 | dry-run→SAM override→lifecycle→IAM→Pod→E2E 전파, 하드코딩 0(B9-05) | 31-01/T1b + 31-10/T3 + 31-12 |
| 60 | pair network 실패 | 31-09 postprocess | 단일 시도+손실 수용(CONTEXT amended B9-04) — belle 결정 반영, limbo 0 | 31-09/T2 |
| 61 | create failure kind 분기 | 31-09 _finalize_create_failure | correctedPose→postprocessing, rotation→direct(H9-09) | 31-09/T1 |
| 62 | Wave 0 자기-완결 1일 lifecycle | 31-01 Task1b | 생성 직후 put+get(신규)/before+merge+rollback(기존)(H9-08) | 31-01/T1b |

---

## §7 실행 허용 조건 추적표 (9차 리뷰 — 15조건)

| # | 조건 | 플랜 위치 | 테스트 |
|---|------|-----------|--------|
| 1 | reservation/orphan janitor claim 직후 crash 가 lease 만료 후 재claim 되어 cleanup 완료 | 31-02 claim lease + 31-09 janitor | 31-02/T3 + 31-09/T3 |
| 2 | expired A 와 동일 key live B 있을 때 A janitor 는 key 삭제 안 함 | 31-02 key ownership + 31-09 | 31-02/T3 + 31-09/T3 |
| 3 | src record→training PUT 2xx→record 전 crash 뒤 두 expected key 모두 삭제 | 31-09 janitor | 31-09/T3 + 31-10/T3 |
| 4 | janitor 삭제 후보 = expected∪created + key별 live owner 0 선검증 | 31-02 helper + 31-09 | 31-02/T3 + 31-09/T3 |
| 5 | pair 정책 = durable outbox 또는 belle-approved CONTEXT amend 로 닫힘 | CONTEXT amended(단일 시도) | 31-09/T2 |
| 6 | chosen alternative bucket 이 dry-run→SAM param→lifecycle→IAM→Pod→E2E 전파 | 31-01/10/12 chosen name | 31-01/T1b+31-10/T3+31-12 |
| 7 | reservation TTL 값 + PipelineTimeout+margin<=TTL build gate | 31-02 상수 + 31-10 gate | 31-02/T2 + 31-10/T3 |
| 8 | terminal/inputSealed/mismatched/matching-nonterminal janitor predicate 표 test | 31-09 janitor | 31-09/T3 |
| 9 | begin acquired transaction 의 nextAction/dispatchState/outboxSeq full write set 고정 | 31-02 begin(4c) | 31-02/T3 |
| 10 | reserve 와 reservation claim 이 하나의 transaction/commit-loss 단위 | 31-02 _claim_..._tx | 31-02/T3 |
| 11 | same orphan key closed→new incident 가 다시 open→cleanup | 31-02 upsert reopen | 31-02/T3 |
| 12 | claimed_by_job/closed 문서 reconciliation + metadata TTL | 31-02 close deleteAfter + 31-09 reconcile | 31-02/T3 + 31-09/T3 |
| 13 | template action 에 OrphanOldestAge/SweepFailed alarm exact resource | 31-10 template | 31-10/T3 + 31-12/T1 |
| 14 | Wave 0 lifecycle/smoke hard-crash 방어 선택이 plan/VALIDATION 일치 | 31-01 Task1b + 본 문서 | 31-01/T1b |
| 15 | alarm 8종(DLQ 포함)/lifecycle 4파일/Object Lock API/plan tag balance lockstep | 31-10/31-12 | 31-10/T3 + 31-12/T1 |

> 참고: 2차~8차 게이트는 위 fault matrix 에 흡수됨. 9차 검증 축 = reservation/janitor 를 crash-recoverable key-ownership 상태 머신으로 승격 + chosen-name 전파 + pair/SLA belle 결정 박제. belle SETTLED 축(즉시-삭제 SLA / pair 단일시도)은 재개 금지 — closure 만.

---

## Wave 0 Requirements

- [ ] **VisualInputBucket provision (Never-versioned Status 부재 + PublicAccessBlock 4종 + SSE + BucketOwnerEnforced + no Object Lock + visual-input/ 1일 lifecycle) — 31-01/T1b (belle 승인, Wave 1 smoke 전제)**
- [ ] `backend/tests/phase31/` conftest + 9 테스트 파일 (run_contended/commit_lost/clock) — **31-02/T1**
- [ ] DashScope urllib mock + _FakeTransaction fixture — **31-02/T1**
- [ ] app jest 러너 — **31-11/T1** (checkpoint 통과 후)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실기기 UX — D-09/D-10 2D 뷰어·교정 이미지·회전 카드 | D-09/D-10 | 실기기 렌더 자동화 불가 | 31-HUMAN-UAT.md 적립 — 31-12/T4 |
| 화살표 시각 게이트 | D-11 | 실 fixture PNG 시각 판정 | 31-12/T4 zoom PNG Claude Read + UAT |
| 두 버킷 lifecycle/SSM mutation + 페어 버킷 Object Lock 실 canary | H2-09/H4-04/H5-07/H6-08 | put=전체 교체, belle 승인 | 31-12/T2 — 두 버킷 before rollback + get + canary VersionId delete(retention/hold HEAD) + 403/권한부재 중단 |
| sam deploy 2회 (OFF/ON) | 배포 | auto-mode classifier | belle `!` — 31-12/T3·T4 |
| IAM 실권한 (send-only iam_probe + 버전/lock simulate) | H2-02/H4-02/B6-02/H6-08 | 실 계정 권한 — receive/delete 금지, 버전 액션 분리 | 31-12/T3 |
| 실 E2E 2종 + Never-versioned 재확인 + worker-role cleanup 증명 → KeyCount 0 | D-05/D-06, H-07, 7차 B7-02/M7-04 | Pod 재생성 + flag ON | **완료 필요조건** — 31-12/T4 |
| VisualInputBucket provision (Never-versioned/보안 속성) | 7차 B7-06/H7-07 | 신규 버킷 생성·belle 승인 | **Wave 0 전제** — 31-01/T1b |
| D-06 완료 알림 실체 (push vs amended) | 7차 H7-06 | 제품 목표 결정 | belle 결정 — 31-11/T1c |
| pair network 실패 = 단일 시도 + 손실 수용 | 9차 B9-04 (belle 위임→planner) | CONTEXT D-01 amended(2026-07-20), limbo 종료 | 31-09/T2 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or checkpoint 게이트 (checkpoint 6건 = belle)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (31-02/T1, 31-11/T1)
- [x] Fault-Injection Matrix 가 task map 자동 테스트에 편입 (5차 10종 + 6차 15종 + 7차 §6 14종 신규 — worker ListBucket/Suspended 오판 차단/cleanupVerified 파라미터 handoff/failed cleanup validator/하드크래시 reservation+janitor/option-b 보상/신규 버킷 provision/두 버킷 lifecycle 교차 rollback/internal transition send 0/create CAS/metric IAM+alarm/D-06 완료알림 결정)
- [x] §7 실행 허용 15조건 추적표 완비 (9차 리뷰 — reservation/janitor crash-safe 승격)
- [x] "성공 경로만 cleanup" 기대값 제거 — 성공·실패 공통 cleanup 증명 후 terminal (H5-05/B6-03/7차 B7-04)
- [x] 신규 VisualInputBucket 생성 절차(Wave 0 provision) + worker s3:ListBucket + Never-versioned 오판 차단 반영
- [x] upload-first 하드크래시 durable reservation+janitor — "즉시 잔존 0" 정상 경로 한정 정정
- [x] D-06 완료 알림 belle 결정 checkpoint(31-11 Task1c) — phase goal 축소 방지
- [x] No watch-mode flags
- [x] Feedback latency < 140s
- [x] pair network 실패 = 단일 시도 + 손실 수용 — CONTEXT D-01 amended(9차 B9-04, belle 위임 후 planner 결정, limbo 종료)
- [x] belle SETTLED 축(즉시-삭제 SLA / pair 단일시도) CONTEXT 박제 — 리뷰 재개 금지
- [x] `nyquist_compliant: true` re-declared (9차 §7 15조건 반영 후)

**Approval:** planner 2026-07-20 (iteration9 targeted replan — 9차 리뷰 BLOCK 반영: B9-01~05 + H9-01~09 + M9-01~06, 31-01/02/09/10/12 + CONTEXT + Validation targeted. Q1 SLA=현행유지(belle)·Q2 pair=단일시도(planner) 확정. D-06 완료알림만 belle 결정 대기)
