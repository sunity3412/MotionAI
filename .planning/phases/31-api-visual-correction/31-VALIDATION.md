---
phase: 31
slug: api-visual-correction
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-19
replanned: 2026-07-19
revision: iteration2
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 31-RESEARCH.md `## Validation Architecture` + 31-PLAN-REVIEW-ITERATION2.md 요구 게이트 (§8 acceptance gate 16종).
> Task IDs = 2026-07-19 iteration2 replan (12 plans / **5 waves** — H2-08 직렬화: 31-09(wave 3) → 31-10(wave 4) → 31-12(wave 5)).
> `nyquist_compliant: true` 는 M2-04 반영(아래 Fault-Injection Matrix 를 task map 에 편입) 후 재선언한 값이다.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend) / tsc --noEmit + jest-expo (app — jest 는 31-11 T1 checkpoint 후) |
| **Config file** | backend/requirements-dev.txt / app/jest.config.js (31-11 신설) |
| **Quick run command** | `python -m pytest backend/tests/phase31/<file>.py -x -q` |
| **Full suite command** | `python -m pytest backend/tests -q` + `cd app && npm run typecheck` (+ `npx jest` 31-11 이후) |
| **Estimated runtime** | ~120 seconds (실 302 local server 통합 + RSS 스트림 테스트 포함) |

---

## Sampling Rate

- **After every task commit:** 해당 테스트 파일 `-x -q` 단건
- **After every plan wave:** `python -m pytest backend/tests -q` (+ 앱 wave 시 typecheck/jest)
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** 120 seconds

---

## Wave Structure (H2-08 반영)

| Wave | Plans | 비고 |
|------|-------|------|
| 1 | 31-01, 31-02, 31-03, 31-04 | 계약·target·상태 기반 (리뷰 §7 Step 1·2 선행) |
| 2 | 31-05, 31-06, 31-07, 31-08 | 어댑터·게이트·페어·앱 컴포넌트 |
| 3 | 31-09, 31-11 | 워커 코드 + 앱 통합 (파일 겹침 0) |
| 4 | 31-10 | HTTP 표면·enqueue·IaC — **31-09 산출(visual-worker CodeUri) 의존 (H2-08)** |
| 5 | 31-12 | live mutation checkpoint + 배포 + E2E |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 31-01/T1 | 31-01 | 1 | H-04+H2-06/H2-10 privacy gate + privacy_decision.json (M2-05) | T-31-04 | 보존일수 숫자·blur 실행 위치 확정 전 구현 금지 | manual (decision) | — | ⬜ pending |
| 31-01/T2 | 31-01 | 1 | D-03 스모크 (fixture 4종, scratch 전용) | T-31-01/02/03 | 키 리터럴 0, 이미지 미추적, MAX_CALLS=8 | script+assert | `python -c "import ast; ast.parse(...)"` | ⬜ pending |
| 31-01/T3 | 31-01 | 1 | H2-07 calibration 임계값 + RESULTS/CALIBRATION/ACCEPTANCE | — | blocked=true → flag OFF, calibration 미달도 blocked | script+assert | RESULTS/CALIBRATION/privacy_decision 스키마 assert + grep Training | ⬜ pending |
| 31-02/T1 | 31-02 | 1 | 테스트 스캐폴드 + mock | — | N/A | unit | `python -m pytest backend/tests/phase31 -x -q` | ⬜ pending |
| 31-02/T2 | 31-02 | 1 | B2-02 side-effect 상태 9종 + typed 실패 9종 (models.py) | — | create_unconfirmed 포함 | unit | python -c import assert | ⬜ pending |
| 31-02/T3 | 31-02 | 1 | 원자 예약+outbox·CAS validator·lease (H-06/B2-02/H2-02) | T-31-05/06/07/52 | 이중 예약 0, polling taskId 필수, dispatchState 원자 기록 | unit | `python -m pytest backend/tests/phase31/test_visual_jobs.py -x -q` | ⬜ pending |
| 31-03/T1 | 31-03 | 1 | B-02+H2-03 화살표 기하 + topology parity (D-11) | T-31-09/10 | record 비의존, parity 단일 결정, adversarial golden | unit | `python -m pytest backend/tests/test_fault_zoom_arrow.py -x -q` | ⬜ pending |
| 31-03/T2 | 31-03 | 1 | B2-01 CorrectedPoseTarget 단일 계약 | T-31-53 | reference_relative 미유입, abs(points) 정렬, unmapped 생략 | unit | `python -m pytest backend/tests/test_fault_zoom_arrow.py -x -q` | ⬜ pending |
| 31-03/T3 | 31-03 | 1 | 배선+프레임 쌍 방출+무회귀 (D-12, B-01) | T-31-11 | 채점 read-only | unit | `python -m pytest backend/tests -q` | ⬜ pending |
| 31-04/T1 | 31-04 | 1 | 계약 TS+normalize (H-02 URL 비저장) | T-31-12 | literal 화이트리스트, key prefix 강등 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-04/T2 | 31-04 | 1 | contract.md 엔드포인트 2절 (M-06 KST) | T-31-13/14 | 단일 404, server-selected key | grep | grep daily_limit/feature_disabled/correctedPose | ⬜ pending |
| 31-05/T1 | 31-05 | 2 | typed 어댑터 create_task/poll 통일 (D-02, M-08, B2-02) | T-31-15/19 | 이미지 어댑터 내부 폴링 0 (§8 gate 5) | unit | `python -m pytest backend/tests/phase31/test_visual_gen.py -x -q` | ⬜ pending |
| 31-05/T2 | 31-05 | 2 | H-05+H2-04+H2-05 다운로드 경계 | T-31-16/17 | _NoRedirectHandler subclass+ProxyHandler({}), 실 302 서버, 파일 스트리밍+RSS 실측 | unit+integration | `python -m pytest backend/tests/phase31/test_visual_gen.py -x -q` | ⬜ pending |
| 31-05/T3 | 31-05 | 2 | H-03 before/after judge (calibration 임계값 대조) | T-31-18 | 불확실=None, CALIBRATION.json chosen 일치, google-genai/pydantic 0 | unit | `python -m pytest backend/tests/phase31 -x -q` | ⬜ pending |
| 31-06/T1 | 31-06 | 2 | Pod /pose-image | T-31-20/22 | 토큰 인증, 8MB 상한 | script+assert | ast.parse + grep pose-image | ⬜ pending |
| 31-06/T2 | 31-06 | 2 | H-03 결정론 pose 게이트 (joint_inner_angle_deg 단일 소스) | T-31-21/23 | fail-closed unavailable | unit | `python -m pytest backend/tests/phase31/test_pose_gate.py -x -q` | ⬜ pending |
| 31-07/T1 | 31-07 | 2 | H-04+H2-06 페어 적재 (strict+versioned HMAC+M2-05 대조) | T-31-24/25/27 | is True strict, uid 미포함, hmacKeyVersion meta, blur 실행 0 | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | ⬜ pending |
| 31-07/T2 | 31-07 | 2 | H2-06 삭제 경로 (전 키 버전 + rotation 테스트) | T-31-26 | key rotation 후 삭제 가능 (§8 gate 12) | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | ⬜ pending |
| 31-08/T1 | 31-08 | 2 | 목업 선제시 + 카드 위치 | — | N/A | manual (decision) | — | ⬜ pending |
| 31-08/T2 | 31-08 | 2 | amended D-10 2D 뷰어 + M-02 단일 구독 | T-31-28/31 | R3F 0, "3D" 문구 0 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-08/T3 | 31-08 | 2 | D-09 참고코너 섹션 | T-31-29/30 | 에러 배너 0, 점수 미표시 | typecheck | `cd app && npm run typecheck` | ⬜ pending |
| 31-09/T1 | 31-09 | 3 | B2-02 action state machine + lease + M2-02 DLQ 증거 | T-31-32/33 | crash-injection 6지점, malformed→batchItemFailures, create_unconfirmed | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | ⬜ pending |
| 31-09/T2 | 31-09 | 3 | correctedPose fetch/judge/pose_check (invocation 분리) | T-31-34/35/36 | hash key equality, 종결 정리, env tolerance 분리, 판정 메타 flat 기록 | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | ⬜ pending |
| 31-09/T3 | 31-09 | 3 | rotation streaming fetch + H2-02 sweeper + 운영 스크립트 | T-31-37 | upload_file (bytes 적재 0), outbox 재발행, reconciliation 목록 | unit | `python -m pytest backend/tests -q` | ⬜ pending |
| 31-11/T1 | 31-11 | 3 | jest-expo 패키지 정당성 (M-03 전제) | T-31-SC | npmjs 확인 후 설치 (auto-approve 불가) | manual + `npx jest --listTests` | — | ⬜ pending |
| 31-11/T2 | 31-11 | 3 | M-05 ApiError + 상태 순수 로직 | T-31-45 | typed code 분기 | unit (jest) | `cd app && npx jest src/lib/__tests__/visualCards.test.ts` | ⬜ pending |
| 31-11/T3 | 31-11 | 3 | 통합 (M-04 무조건 훅, H-02 재서명 소비) | T-31-46/47 | URL 필드 소비 0, 폴링 0 | unit (jest) + typecheck | `cd app && npx jest && npm run typecheck` | ⬜ pending |
| 31-10/T1 | 31-10 | 4 | H-02 재서명 + M2-01 exact guard + L-03 validator | T-31-41 | exact basename + status done + failed stale 404 | unit | `python -m pytest backend/tests/phase31/test_visual_url.py -x -q` | ⬜ pending |
| 31-10/T2 | 31-10 | 4 | H-06 원자 요청 + H2-02 outbox dispatch + M-06 | T-31-38/39/40/42 | fail-closed env, 전용 timestamp dedupe, send 실패→dispatch_failed+sweeper | unit | `python -m pytest backend/tests/phase31/test_visual_request.py -x -q` | ⬜ pending |
| 31-10/T3 | 31-10 | 4 | B2-03 replay-safe enqueue + H2-01 IaC + H2-09 dry-run | T-31-43/44/54/55 | reserve 반환 유일 분기, immutable hash key, template 파싱 assert, live mutation 0 | lint+unit | `(cd backend && sam validate --lint) && python -m pytest backend/tests/phase31/test_visual_dispatch.py -x -q` | ⬜ pending |
| 31-12/T1 | 31-12 | 5 | 전체 게이트 + blocked 검사 (H-03) | — | blocked=true → 롤아웃 차단 | full suite | `python -m pytest backend/tests -q && (cd backend && sam validate --lint)` | ⬜ pending |
| 31-12/T2 | 31-12 | 5 | H2-09 라이브 mutation checkpoint (lifecycle merge + SSM versioned 키) | T-31-55 | belle 승인 + before rollback + put 후 get 검증 | manual (human-action) | — | ⬜ pending |
| 31-12/T3 | 31-12 | 5 | belle 배포 (flag OFF) + 401/503/404 + H2-02 IAM 실검증 | T-31-48/49 | simulate-principal-policy/canary — Pipeline+RunPod SendMessage (§8 gate 8) | manual (human-action) | — | ⬜ pending |
| 31-12/T4 | 31-12 | 5 | H-07 실 E2E 2종 + OTA + UAT (§8 gate 16) | T-31-50/51 | E2E PASS 전 완료 선언 금지 | integration | `test -f 31-HUMAN-UAT.md && grep -q "D-10" ...` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Fault-Injection Matrix (M2-04 — nyquist 재선언의 근거)

내구성 주장은 happy-path mock 이 아니라 아래 주입 테스트로 증명한다. 각 행은 위 task map 의 자동 테스트에 편입되어 있다.

| Fault | 주입 지점 | 기대 동작 | Task | §8 gate |
|-------|-----------|-----------|------|---------|
| crash: vendor create 직전 | 31-09 _action_create (creating 전이 후) | lease 만료 후 'create_unconfirmed' — 자동 재생성 0 | 31-09/T1 | 4 |
| crash: vendor 2xx 직후·taskId write 전 | 31-09 _action_create | 동일 — 중복 과금 0 (수동 reconciliation 목록) | 31-09/T1 | 4 |
| crash: taskId write 직후 | 31-09 | 재전달이 polling 재개, create 재호출 0 | 31-09/T1 | 4 |
| crash: continuation send 직전 | 31-09 공통 | batchItemFailures 재전달 → CAS 멱등 재실행 | 31-09/T1 | 4 |
| crash: S3 put 직후·CAS 전 (fetch) | 31-09 fetch | 재실행 멱등 (동일 dest, 벤더 호출 0) | 31-09/T1 | 4 |
| crash: terminal write 직전 | 31-09 | 종결 재시도, 외부 호출 0 | 31-09/T1 | 4 |
| replay: duplicate `_process` after done | 31-10 enqueue | 완전 no-op — S3/표시 상태/SQS 불변 | 31-10/T3 | 6 |
| replay: duplicate while polling | 31-10 enqueue | no-op | 31-10/T3 | 6 |
| concurrency: 2 enqueue 동시 | 31-10 enqueue (reserve 순차 2회 모사) | S3 put 1회·SQS 1회 | 31-10/T3 | 6 |
| crash: reserve 후 send 전 | 31-10 enqueue / 31-10 visual-request | dispatch_failed + nextDispatchAtMs → sweeper 재발행 | 31-10/T2·T3 + 31-09/T3 | 7 |
| redirect: 실 301/302/303/307/308 | 31-05 local HTTP server | 전부 VendorDownloadError('redirect') — 실 opener 경유 | 31-05/T2 | 10 |
| oversize/RSS: 200MB 급 스트림 | 31-05 다운로드 | 파일 스트리밍 peak RSS < 64MB 증가 + 실측 기록 | 31-05/T2 | 11 |
| key rotation: HMAC v1→v2 회전 후 삭제 | 31-07 삭제 스크립트 | retired v1 재계산으로 기존 pair 삭제 성공 | 31-07/T2 | 12 |
| malformed SQS 메시지 | 31-09 handler | batchItemFailures → DLQ 증거 (조용 삭제 0) | 31-09/T1 | — (M2-02) |
| template drift | 31-10 파싱 assert | visibility >= 6×timeout, maxReceiveCount >= 5 위반 시 테스트 실패 | 31-10/T3 | 9 |

---

## §8 Acceptance Gate 추적표 (2차 리뷰 — 16종 전부 플랜 텍스트에서 추적 가능)

| Gate | 내용 | 플랜 위치 |
|------|------|-----------|
| 1 | CorrectedPoseTarget 단일 객체 | 31-03/T2 |
| 2 | reference_relative 미유입 테스트 | 31-03/T2 (record 오염 불변 테스트) |
| 3 | signed-negative 정렬 + unmapped 생략 | 31-03/T2 |
| 4 | create 전후 crash 무고아·무중복과금 | 31-02/T3 (lease validator) + 31-09/T1 (crash 6지점) |
| 5 | 이미지 adapter 내부 폴링 금지 | 31-05/T1 |
| 6 | duplicate _process no-op | 31-10/T3 |
| 7 | outbox/sweeper 양 kind 복구 | 31-02/T3 + 31-09/T3 + 31-10/T2·T3 |
| 8 | Pipeline+RunPod SendMessage 실권한 | 31-10/T3 (정책 명시) + 31-12/T3 (simulate/canary) |
| 9 | visibility/redrive 공식 권고 | 31-10/T3 (1800/5 + 파싱 assert) |
| 10 | 실 urllib 30x 거부 통합 테스트 | 31-05/T2 |
| 11 | 200MB streaming + peak RSS | 31-05/T2 + 31-09/T3 (upload_file) |
| 12 | HMAC rotation 후 삭제 + 보존 숫자 | 31-01/T1 (retentionDays) + 31-07/T2 |
| 13 | option B 실행 가능 anonymizer | 31-01/T1 (Pod blur 설계) + 31-07/T1 (Lambda blur 0) + 31-10/T3 (trainingSrcKey) |
| 14 | calibration 기반 임계값 | 31-01/T3 + 31-05/T3 (대조 테스트) |
| 15 | 31-09→31-10 직렬 DAG + live mutation checkpoint | frontmatter (wave 3→4→5) + 31-12/T2 |
| 16 | 실 E2E 2종 PASS | 31-12/T4 |

---

## Wave 0 Requirements

- [ ] `backend/tests/phase31/` conftest + 8 테스트 파일 — **31-02/T1**
- [ ] DashScope urllib mock + _FakeTransaction fixture — **31-02/T1**
- [ ] app jest 러너 — **31-11/T1** (checkpoint 통과 후; 거부 시 M-03 deviation 기록)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실기기 UX — D-09/D-10 2D 뷰어·교정 이미지·회전 카드 렌더 | D-09/D-10 | 실기기 렌더는 자동화 불가 | 31-HUMAN-UAT.md 적립 ([[batch-uat-after-phase-31]]) — 31-12/T4 |
| 화살표 시각 게이트 (B-02) | D-11 | 실 fixture PNG 시각 판정 | 31-12/T4 에서 E2E 분석의 zoom PNG Claude Read 선검토 + UAT 적립 |
| 라이브 lifecycle/SSM mutation | H2-09 | put = 전체 교체, belle 승인 필요 | 31-12/T2 checkpoint — before rollback + put 후 get 검증 |
| sam deploy 2회 (OFF/ON) | 배포 | auto-mode classifier 차단 | belle `!` 프리픽스 — 31-12/T3·T4 |
| IAM 실권한 (RunPod credential) | H2-02 | 실 계정 권한 — simulate/canary | 31-12/T3 |
| 실 E2E 2종 | D-05/D-06, H-07 | Pod 재생성 + flag ON 필요 | **phase 완료 필요조건 — 미통과 시 phase 미완료** — 31-12/T4 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or checkpoint 게이트 (checkpoint 6건 = belle)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (31-02/T1, 31-11/T1)
- [x] Fault-Injection Matrix 가 task map 자동 테스트에 편입됨 (M2-04)
- [x] §8 gate 16종 추적표 완비
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` re-declared (M2-04 반영 후)

**Approval:** planner 2026-07-19 (iteration2 replan — 2차 리뷰 BLOCK 반영: B2-01/02/03 + H2-01~10 + M2-01~05, wave 5단 재배치)
