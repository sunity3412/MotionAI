---
phase: 15-mode-1-mode-3-testflight
plan: 02
subsystem: infra
tags: [runpod, gpu, lambda, ssm, firestore, s3, gemini, cerebras, dual-coach, pod-bringup]

requires:
  - phase: 14-reference-backfill
    provides: 11 reference motions (phase4_v1 RTMW) for Mode 1 comparison library
provides:
  - 신규 RunPod Pod 01emvodj1pdooe live (/health 200, pipeline_loaded, auth_configured)
  - SSM /sunity/motion/runpod-analyze-url == live Lambda RUNPOD_ANALYZE_URL == new pod /analyze (synced, sam-deploy-safe)
  - Lambda pipeline env merge-updated with 4-key preservation (RUNPOD_ANALYZE_URL/RUNPOD_AUTH_TOKEN/VIDEO_BUCKET/FIREBASE_SA_PARAM)
  - 실 LLM dual-coach E2E 발화 확인 (gemini_ok=True, cerebras_ok=True, empty sections 0) — D-03/D-12 충족
  - 15-POD-BRINGUP-EVIDENCE.md (operational bring-up record)
affects: [15-mode-1-e2e, 15-mode-3-e2e, 15-false-positive-gate, mode1, mode3, score-04]

tech-stack:
  added: []
  patterns:
    - "Lambda env MERGE update (read full map -> change 1 key -> write whole map back) — never partial REPLACE"
    - "Self-contained notification-only smoke (temp Firestore doc + S3-to-S3 COPY) — no Plan-01 dependency, single S3 trigger, no double /analyze"
    - "Pod env repair via uvicorn restart preserving proc env + adding missing CEREBRAS_KEY_PARAM"

key-files:
  created:
    - .planning/phases/15-mode-1-mode-3-testflight/15-POD-BRINGUP-EVIDENCE.md
  modified: []

key-decisions:
  - "Verify-and-repair (not from-scratch bootstrap) — prior session already synced this pod; only repaired the missing Cerebras param"
  - "CEREBRAS_KEY_PARAM restored on pod (Rule 2) to enable best-case dual-coach (both LLMs fire), not just cross-fill"
  - "line=None on unrecognized 'auto' motion is correct fallback (no fake line score), not a gate failure; registered-motion line check deferred to Wave 2 Mode 1 E2E"

patterns-established:
  - "Pattern: Lambda env source-of-truth = SSM; update SSM first then merge live Lambda env, machine-assert SSM==Lambda equality + 4-key presence"
  - "Pattern: live-bucket smoke triggers analysis ONLY via S3 notification, never a second direct /analyze POST"

requirements-completed: [MODE-01, MODE-02, SCORE-04]

duration: ~13min
completed: 2026-06-17
---

# Phase 15 Plan 02: 신규 RunPod Pod Bring-up + SSM/Lambda 동기화 + 실 LLM Smoke Summary

**신규 Pod 01emvodj1pdooe 를 verify-and-repair 로 살리고(health 200 + Cerebras param 복구), SSM/Lambda RUNPOD_ANALYZE_URL 을 merge-동기화(4-key 보존)한 뒤, 자체-완결 notification-only smoke 로 실 듀얼 coach(gemini_ok=True cerebras_ok=True, 빈 섹션 0) 발화를 확인 — Wave 2~3 실 E2E 를 막던 단일 최상위 운영 블로커 해소.**

## Performance

- **Duration:** ~13 min (checkpoint 이후 자동 실행 구간)
- **Completed:** 2026-06-17T08:42:50Z
- **Tasks:** 2 auto tasks (체크포인트 human-action 은 사전 충족)
- **Files modified:** 1 created (evidence)

## Accomplishments
- 신규 Pod 01emvodj1pdooe `/health` 200 + `pipeline_loaded:true` + `auth_configured:true` (external proxy) 확인
- Pod env 전체 복원 검증 + 누락된 `CEREBRAS_KEY_PARAM` 복구(uvicorn 재시작, .bashrc 영구 박제) — 듀얼 coach 양쪽 발화 가능 상태로 복원
- SSM `/sunity/motion/runpod-analyze-url` 갱신(Version 4) + live Lambda env merge-update; machine verify `ALL_PRESENT_AND_SSM_EQ_LAMBDA` (exit 0)
- 자체-완결 notification-only 실 LLM smoke: S3 COPY → notification 단일 trigger → delegate 실행(`uploading→queued→pose_analysis→comparison→done`) → `gemini_ok=True cerebras_ok=True cross_filled=[]` (빈 섹션 0) → 임시 doc/객체 cleanup
- 두 LLM 키 모두 live 확인 → W-3 blocking escalation 불필요

## Task Commits

1. **Task 1 + Task 2 (evidence)** - `6086485` (docs) — pod bring-up evidence, SSM/Lambda sync, dual-coach smoke 결과

_Task 1(Pod verify+env repair)·Task 2(SSM/Lambda sync + smoke)는 repo 코드 변경 없는 운영 작업이라 단일 evidence 문서로 atomically 기록. Pod env 복구는 Pod-side(.bashrc + uvicorn restart)로 repo 파일 변경 없음._

## Files Created/Modified
- `.planning/phases/15-mode-1-mode-3-testflight/15-POD-BRINGUP-EVIDENCE.md` - Pod id/proxy, /health, env 복원 체크리스트, SSM==Lambda equality + 4-key presence(키 이름만), notification-only smoke 결과, LLM 키 liveness (secret 값 노출 0)

## Decisions Made
- **Verify-and-repair 접근:** 직전 세션이 이 pod 에 full-setup + URL sync 를 이미 적용 → healthy server 를 tear down 하지 않고 실제 누락분(Cerebras param)만 복구. orchestrator 가 /health 200 을 사전 확인했고 본 실행도 재확인.
- **CEREBRAS_KEY_PARAM 복구(Rule 2):** running uvicorn proc env 에 누락 → Cerebras coach 가 silent drop. Plan Task 1 env 체크리스트가 Cerebras 를 명시하므로 복구. SSM `/sunity/motion/cerebras-api-key` 존재 확인 후 env 주입 + 재시작.
- **line=None 판정:** pdshape 가 recognizer 에서 미등록='auto' 로 해소 → Page 9 단독(line 미산출)은 가짜 line 점수 방지를 위한 설계상 정상 폴백. recognizer 는 실 Gemini 호출로 발화했고 stability 는 정상. 등록 동작 line non-None 은 Wave 2 Mode 1 E2E 에서 검증.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Config] CEREBRAS_KEY_PARAM Pod env 복구**
- **Found during:** Task 1 (env 복원 검증)
- **Issue:** 직전 세션 부트스트랩의 running uvicorn proc env 에 `CEREBRAS_KEY_PARAM` 가 없어 `coach_writer._load_api_key()` 가 None 반환 → Cerebras 듀얼 coach silent drop. Plan Task 1 env 체크리스트("Cerebras key") 위반.
- **Fix:** SSM `/sunity/motion/cerebras-api-key` 존재 확인(len 52, 값 비노출) → uvicorn 을 전체 env 보존 + `CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-api-key` + `GEMINI_COACH_ENABLED=1` 로 재시작(pitfall 27 `__pycache__` 청소) → `.bashrc` 영구 박제.
- **Files modified:** Pod-side만 (`/root/.bashrc`); repo 파일 변경 없음.
- **Verification:** 재시작 후 /health 200 유지 + smoke 에서 `cerebras_ok=True` 실측.
- **Committed in:** `6086485` (evidence 문서에 deviation 기록)

---

**Total deviations:** 1 auto-fixed (1 missing critical config)
**Impact on plan:** Cerebras 복구는 D-12 best-case 듀얼 coach 검증에 필수. scope creep 없음.

## Issues Encountered
- macOS 로컬에 `timeout` 미존재 → ssh `ConnectTimeout`/`ServerAliveInterval` 로 대체.
- 로컬 zsh 가 remote heredoc 의 awk `$NF`/`sed` 패턴을 오파싱 → remote 스크립트를 파일로 작성해 `ssh 'bash -s' < file` 로 전달하여 해결.
- smoke 폴링이 백그라운드(>10s)로 전환 → harness background task 로 모니터링, 정상 완료(exit 0).

## User Setup Required
None — belle 의 Pod 생성(체크포인트 human-action)은 사전 충족됨. 이후 모든 SSH/AWS/SSM/Lambda 작업은 Claude 가 sunity-motion 자격으로 자동 실행.

## Next Phase Readiness
- 실 E2E delegate 경로 GREEN — Wave 2(Mode 1 11-ref) / Wave 3(Mode 3 success/fail pair) 진입 가능.
- 실 듀얼 coach(Gemini+Cerebras) 발화 확인 — D-03/D-12 충족.
- **Open(Wave 2):** 등록 동작에 대한 line dimension non-None 은 Mode 1 E2E(등록 reference 비교)에서 검증. 미등록 'auto' 동작 line=None 은 정상.
- **Volatility note:** Pod 는 ephemeral — RUNPOD_ANALYZE_URL/SSM 는 Pod 재생성 시 재동기화 필요(이 plan 의 절차 재사용).

## Self-Check: PASSED

- FOUND: `.planning/phases/15-mode-1-mode-3-testflight/15-POD-BRINGUP-EVIDENCE.md`
- FOUND: `.planning/phases/15-mode-1-mode-3-testflight/15-02-SUMMARY.md`
- FOUND commit `6086485` (evidence) + `c17dec3` (summary) in worktree log
- machine verify exit 0 (`ALL_PRESENT_AND_SSM_EQ_LAMBDA`)
- smoke exit 0 (`DELEGATE_RAN=True`, `gemini_ok=True`, `cerebras_ok=True`)

---
*Phase: 15-mode-1-mode-3-testflight*
*Completed: 2026-06-17*
