---
phase: 31
slug: api-visual-correction
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-19
replanned: 2026-07-19
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 31-RESEARCH.md `## Validation Architecture` + 31-REVIEWS.md 요구 게이트.
> Task IDs = 2026-07-19 structural replan (12 plans / 4 waves — 리뷰 BLOCK/REPLAN 반영).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend) / tsc --noEmit + jest-expo (app — jest 는 31-11 T1 checkpoint 후) |
| **Config file** | backend/requirements-dev.txt / app/jest.config.js (31-11 신설) |
| **Quick run command** | `python -m pytest backend/tests/phase31/<file>.py -x -q` |
| **Full suite command** | `python -m pytest backend/tests -q` + `cd app && npm run typecheck` (+ `npx jest` 31-11 이후) |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** 해당 테스트 파일 `-x -q` 단건
- **After every plan wave:** `python -m pytest backend/tests -q` (+ 앱 wave 시 typecheck/jest)
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 31-01/T1 | 31-01 | 1 | H-04 privacy release gate | T-31-04 | 고지·보존·삭제 결정 전 구현 금지 | manual (decision) | — | — | ⬜ pending |
| 31-01/T2 | 31-01 | 1 | D-03 스모크 (scratch 전용) | T-31-01/02/03 | 키 리터럴 0, 이미지 미추적, MAX_CALLS=4 | script+assert | `python -c "import ast; ast.parse(...)"` | 생성 대상 | ⬜ pending |
| 31-01/T3 | 31-01 | 1 | RESULTS.json + ACCEPTANCE 임계값 | — | blocked=true → flag OFF 유지 | script+assert | RESULTS.json 스키마 assert + grep Training | 생성 대상 | ⬜ pending |
| 31-02/T1 | 31-02 | 1 | 테스트 스캐폴드 + mock | — | N/A | unit | `python -m pytest backend/tests/phase31 -x -q` | 생성 대상 | ⬜ pending |
| 31-02/T2 | 31-02 | 1 | visual 상수/멱등키 (models.py) | — | typed failure 8종 | unit | python -c import assert | ✅ 수정 | ⬜ pending |
| 31-02/T3 | 31-02 | 1 | 원자 예약·CAS·전용 timestamp (H-06/B-03) + payload flat scalar | T-31-05/06/07 | 이중 예약 0, updatedAt 미기록, URL 파라미터 부재, payload nested 거부 | unit | `python -m pytest backend/tests/phase31/test_visual_jobs.py -x -q` | W0 | ⬜ pending |
| 31-03/T1 | 31-03 | 1 | B-02 TargetArrowSpec 기하 (D-11) | T-31-09/10 | record 비의존, omission 규칙 | unit | `python -m pytest backend/tests/test_fault_zoom_arrow.py -x -q` | 생성 대상 | ⬜ pending |
| 31-03/T2 | 31-03 | 1 | 배선+프레임 쌍 방출+무회귀 (D-12, B-01) | T-31-11 | 채점 read-only | unit | `python -m pytest backend/tests/test_fault_zoom_arrow.py -x -q && python -m pytest backend/tests -q` | ✅ 기존+신규 | ⬜ pending |
| 31-04/T1 | 31-04 | 1 | 계약 TS+normalize (H-02 URL 비저장) | T-31-12 | literal 화이트리스트, key prefix 강등 | typecheck | `cd app && npm run typecheck` | ✅ | ⬜ pending |
| 31-04/T2 | 31-04 | 1 | contract.md 엔드포인트 2절 (M-06 KST) | T-31-13/14 | 단일 404, server-selected key | grep | grep daily_limit/feature_disabled/correctedPose | ✅ | ⬜ pending |
| 31-05/T1 | 31-05 | 2 | typed 어댑터 (D-02, M-08) | T-31-15/19 | 키 비로깅, 재시도 1회 | unit | `python -m pytest backend/tests/phase31/test_visual_gen.py -x -q` | W0 | ⬜ pending |
| 31-05/T2 | 31-05 | 2 | H-05 다운로드 경계 | T-31-16/17 | evilaliyuncs/redirect/사설IP/CT/바이트캡 | unit | `python -m pytest backend/tests/phase31/test_visual_gen.py -x -q` | W0 | ⬜ pending |
| 31-05/T3 | 31-05 | 2 | H-03 before/after judge (stdlib urllib Gemini REST) | T-31-18 | 불확실=None, display/training 분리, google-genai/pydantic import 0, 키 헤더 전송(URL/로그 미노출) | unit | `python -m pytest backend/tests/phase31 -x -q` | W0 | ⬜ pending |
| 31-06/T1 | 31-06 | 2 | Pod /pose-image | T-31-20/22 | 토큰 인증, 8MB 상한 | script+assert | ast.parse + grep pose-image | ✅ 수정 | ⬜ pending |
| 31-06/T2 | 31-06 | 2 | H-03 결정론 pose 게이트 | T-31-21/23 | fail-closed unavailable | unit | `python -m pytest backend/tests/phase31/test_pose_gate.py -x -q` | W0 | ⬜ pending |
| 31-07/T1 | 31-07 | 2 | H-04 페어 적재 (strict+HMAC) | T-31-24/25/27 | is True strict, uid 미포함, 무키 거부 | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | W0 | ⬜ pending |
| 31-07/T2 | 31-07 | 2 | H-04 삭제 경로 | T-31-26 | HMAC 재계산 삭제 | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | W0 | ⬜ pending |
| 31-08/T1 | 31-08 | 2 | 목업 선제시 + 카드 위치 | — | N/A | manual (decision) | — | — | ⬜ pending |
| 31-08/T2 | 31-08 | 2 | amended D-10 2D 뷰어 + M-02 단일 구독 | T-31-28/31 | R3F 0, "3D" 문구 0 | typecheck | `cd app && npm run typecheck` | ✅ | ⬜ pending |
| 31-08/T3 | 31-08 | 2 | D-09 참고코너 섹션 | T-31-29/30 | 에러 배너 0, 점수 미표시 | typecheck | `cd app && npm run typecheck` | ✅ | ⬜ pending |
| 31-09/T1 | 31-09 | 3 | B-03 state machine + continuation | T-31-32/33 | 고아 불가 불변식, batchItemFailures, requirements.txt pyyaml 박제 | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | W0 | ⬜ pending |
| 31-09/T2 | 31-09 | 3 | correctedPose 잡 (이중 게이트+정리+페어+판정 메타) | T-31-34/35/36 | key equality, finally 삭제, training 별도 임계, judge/poseGate 메타 job 문서 flat 기록 (E2E-A 전제) | unit | `python -m pytest backend/tests/phase31/test_visual_worker.py -x -q` | W0 | ⬜ pending |
| 31-09/T3 | 31-09 | 3 | rotation 잡 + 운영자 스크립트 (L-04) | T-31-37 | canonical key, 벤더 URL 미저장 | unit | `python -m pytest backend/tests -q` | W0 | ⬜ pending |
| 31-10/T1 | 31-10 | 3 | H-02 재서명 + L-03 공유 validator | T-31-41 | server-selected key, 단일 404, 1h TTL | unit | `python -m pytest backend/tests/phase31/test_visual_url.py -x -q` | W0 | ⬜ pending |
| 31-10/T2 | 31-10 | 3 | H-06 원자 요청 + dispatch 복구 + M-06 | T-31-38/39/40/42 | fail-closed env, 전용 timestamp dedupe, requirements.txt pyyaml 박제 | unit | `python -m pytest backend/tests/phase31/test_visual_request.py -x -q` | W0 | ⬜ pending |
| 31-10/T3 | 31-10 | 3 | H-01 enqueue-only + IaC + flag OFF | T-31-43/44 | 인라인 생성 0, ReportBatchItemFailures, payload={srcKey,joint,targetDeg} 전달, GEMINI_API_KEY 워커 전용 주입 | lint+unit | `(cd backend && sam validate --lint) && python -m pytest backend/tests/phase31/test_visual_dispatch.py -x -q` | ✅ 수정 | ⬜ pending |
| 31-11/T1 | 31-11 | 3 | jest-expo 패키지 정당성 (M-03 전제) | T-31-SC | npmjs 확인 후 설치 (auto-approve 불가) | manual (human-verify) + `npx jest --listTests` | — | — | ⬜ pending |
| 31-11/T2 | 31-11 | 3 | M-05 ApiError + 상태 순수 로직 | T-31-45 | typed code 분기 | unit (jest) | `cd app && npx jest src/lib/__tests__/visualCards.test.ts` | 생성 대상 | ⬜ pending |
| 31-11/T3 | 31-11 | 3 | 통합 (M-04 무조건 훅, H-02 재서명 소비) | T-31-46/47 | URL 필드 소비 0, 폴링 0 | unit (jest) + typecheck | `cd app && npx jest && npm run typecheck` | ✅ 수정 | ⬜ pending |
| 31-12/T1 | 31-12 | 4 | 전체 게이트 + blocked 검사 (H-03) | — | blocked=true → 롤아웃 차단 | full suite | `python -m pytest backend/tests -q && (cd backend && sam validate --lint)` | ✅ | ⬜ pending |
| 31-12/T2 | 31-12 | 4 | belle 배포 (flag OFF) + 401/503/404 실검증 | T-31-48/49 | 수동 배포 게이트 + canary | manual (human-action) | — | — | ⬜ pending |
| 31-12/T3 | 31-12 | 4 | H-07 실 E2E 2종 + OTA + UAT | T-31-50/51 | E2E PASS 전 완료 선언 금지 | integration | `test -f 31-HUMAN-UAT.md && grep -q "D-10" ...` | 생성 대상 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase31/` conftest + 8 테스트 파일 (test_visual_jobs / test_visual_gen / test_pose_gate / test_pair_store / test_visual_worker / test_visual_request / test_visual_url / test_visual_dispatch) — **31-02/T1**
- [ ] DashScope urllib mock + _FakeTransaction fixture — **31-02/T1**
- [ ] app jest 러너 — **31-11/T1** (checkpoint 통과 후; 거부 시 M-03 deviation 기록)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실기기 UX — D-09/D-10 2D 뷰어·교정 이미지·회전 카드 렌더 | D-09/D-10 | 실기기 렌더는 자동화 불가 | 31-HUMAN-UAT.md 적립 — 즉시 belle 호출 금지 ([[batch-uat-after-phase-31]]) — 31-12/T3 |
| 화살표 시각 게이트 (B-02) | D-11 | 실 fixture PNG 시각 판정 | 31-12/T3 에서 E2E 분석의 zoom PNG 를 Claude Read 선검토 + UAT 적립 |
| sam deploy 2회 (OFF/ON) | 배포 | auto-mode classifier 차단 | belle `!` 프리픽스 — 31-12/T2·T3 |
| 실 E2E 2종 (correctedPose 자동·rotation 온디맨드) | D-05/D-06, 리뷰 H-07 | Pod 재생성 + flag ON 필요 | **phase 완료 필요조건 — 미통과 시 phase 미완료** (이월로 완료 처리 금지) — 31-12/T3 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or checkpoint 게이트 (checkpoint 5건 = belle)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (31-02/T1, 31-11/T1)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner 2026-07-19 (structural replan — 리뷰 BLOCK 반영, task map 재작성; same-day revision — checker fixups: judge urllib REST / pyyaml / payload / 판정 메타 / deps edges)
