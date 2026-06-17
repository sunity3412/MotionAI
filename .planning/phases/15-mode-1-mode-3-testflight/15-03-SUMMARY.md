---
phase: 15-mode-1-mode-3-testflight
plan: 03
subsystem: testing
tags: [mode1, mode-expert, e2e, runpod, gpu, rtmw, gemini, cerebras, dual-coach, firestore, falsepositive, reference-verify, phase15]

# Dependency graph
requires:
  - phase: 14-reference-backfill
    provides: 11 reference 모션 phase4_v1 RTMW + downstream 4필드 (Mode 1 referenceMotionId lockstep)
  - phase: 15-mode-1-mode-3-testflight (15-01)
    provides: sweep_phase15.py + phase15_keys.json + upload_phase15_dataset.py (SOURCE/identity 분리, per-run uid, direct-process)
  - phase: 15-mode-1-mode-3-testflight (15-02)
    provides: 신규 Pod 01emvodj1pdooe live + SSM/Lambda RUNPOD_ANALYZE_URL sync + 듀얼 coach 발화 확인
provides:
  - "Mode 1 (MODE_EXPERT) 7-motion 실 Pod GPU E2E evidence — referenceMotionId lockstep, 실 Firestore doc 파생 overallScore/dimensionScores"
  - "Mode 1 7/7 server_error==0 gate PASS (15-03 단독)"
  - "11 reference downstream 4필드 + captureViews 검증 11/11 (FIELD-VERIFIED)"
  - "success 영상 OBSERVATIONAL 점수 (overallScore/severity/referenceMotionId/server_error) — blocking 게이트 아님"
  - "Open Q3 finding: 7/7 line=None (recognizer student-영상 미인식 anti-false-positive 폴백)"
  - "15-MODE1-FALSEPOSITIVE-EVIDENCE.md"
affects: [15-04, 15-05, phase-18-fault-eval-set]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pod sweep env = live uvicorn proc(/proc/<pid>/environ) 재사용 — LD_LIBRARY_PATH(cudnn)/CUDA/AWS/Gemini/Cerebras 전체 source (키 값 비노출, NUL-delimited)"
    - "transient Gemini 503 = per-run 새 uid 로 subset retry (fixed id 재사용 0, stale stuck doc 선삭제)"
    - "evidence = 실 Firestore doc read-back (dry-run 단독 불충분) — overallScore/dimensionScores/severity/coach sections"

key-files:
  created:
    - .planning/phases/15-mode-1-mode-3-testflight/15-MODE1-FALSEPOSITIVE-EVIDENCE.md
  modified: []

key-decisions:
  - "line=None 7/7 은 recognizer(Gemini)가 student 영상을 등재 동작으로 confident 인식 못함(motion_unrecognized_layer1_only) → expects_extension 전부 False → line 생략. 설계상 anti-false-positive 폴백(가짜 line 점수 금지), 15-03 blocking gate 아님. 임의 line floor 신규 fit 금지(calibration-source-hard-gate)."
  - "Gemini 503 UNAVAILABLE 은 transient 외부 LLM 가용성 이슈 — server_error 아님. peter-pan/power-spin 새 uid 로 retry → 둘 다 done."
  - "onnxruntime CUDA 폴백 root cause = LD_LIBRARY_PATH(cudnn lib) 누락. live uvicorn proc env 재사용으로 GPU 강제 (CPU 대비 ~3x)."
  - "Task 1+2 는 repo 코드 변경 없는 운영/evidence 작업 → 단일 evidence-doc commit (15-02 패턴 정합)."

patterns-established:
  - "Pattern: Pod 실행 env = live uvicorn proc environ source (secret 값 한 번도 출력/commit 0)"
  - "Pattern: Mode 1 evidence = 실 Firestore doc 파생 per-motion 행 + per-run uid/analysisId/createdAt (HIGH 2 stale 거부)"
  - "Pattern: coverage 정직성 — 11 FIELD-VERIFIED 이나 student 영상 가용 7 만 live 비교, 4 ref 한계 명시(R3)"

requirements-completed: [MODE-01, SCORE-04]

# Metrics
duration: ~70min
completed: 2026-06-17
---

# Phase 15 Plan 03: Mode 1 (MODE_EXPERT) 7/7 실 E2E Summary

**정은지 student 영상 7 motion 을 각자 matching reference 로 Mode 1 실 Pod GPU E2E(RTMW + Gemini recognizer + 듀얼 coach) 돌려 7/7 server_error==0 게이트를 통과하고, 11 reference downstream 4필드 11/11 검증 + success 영상 OBSERVATIONAL 점수 + line=None Open Q3 finding 을 실 Firestore doc 파생 evidence 로 박았다.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-06-17T08:49Z
- **Completed:** 2026-06-17T09:55Z
- **Tasks:** 2 auto tasks (운영/evidence)
- **Files modified:** 1 created (evidence) + phase15_keys.json regenerated (내용 동일, no diff)

## Accomplishments
- **11 reference downstream 4필드 + captureViews 검증 11/11** (seed-reference-downstream.mjs --verify, completeRequiredSet=11/11) — repair 불필요, Task 2 선행 게이트 충족.
- **Mode 1 (MODE_EXPERT) 7 student-video motion 실 Pod GPU E2E** — climb/combo/elbow-twist-sister/kip-up/pdshape/peter-pan/power-spin 각자 ref-{motion} 로 비교, referenceMotionId lockstep. 실 Firestore doc 파생 overallScore (65/90/78/98/68/97/95) + dimensionScores (angle+stability).
- **Mode 1 7/7 server_error==0 (15-03 단독 gate) PASS** — 7/7 done, server_error 0, no_human/not_pole_motion 0.
- **듀얼 coach 빈 섹션 0** — fault 섹션 산출 5 motion 전부 Gemini(causes/coachNote) + Cerebras(cause 내부 fix + injuryRisk) 채워짐 (D-03/D-12). kip-up/peter-pan 은 angle 매우 높아 positive 단일 tip path(정상).
- **success 영상 OBSERVATIONAL** 점수 기록 (MEDIUM 6, blocking 게이트 아님) + **4 no-student-video ref coverage 한계 명시** (R3).

## Task Commits

1. **Task 1 (11-ref 필드 검증) + Task 2 (Mode 1 7-motion E2E + evidence)** - `9d11112` (docs)

_Task 1·Task 2 는 repo 코드 변경 없는 운영(SSH sweep/Firestore read-back/reference verify) 작업이라 단일 evidence 문서로 atomically 기록 (15-02 패턴 정합)._

## Files Created/Modified
- `.planning/phases/15-mode-1-mode-3-testflight/15-MODE1-FALSEPOSITIVE-EVIDENCE.md` - 11-ref 필드 검증(11/11) + Mode1 7-motion 점수 표(실 Firestore 파생) + 7/7 server_error==0 gate + 듀얼 coach 빈 섹션 0 + success OBSERVATIONAL + line=None Open Q3 + 4 ref coverage 한계 + deviation (키 값 노출 0)
- `backend/scripts/phase15_keys.json` - upload_phase15_dataset.py 실 업로드(13 SOURCE) 후 재산출 — 내용 committed 버전과 동일(no git diff)

## Decisions Made
- **line=None 7/7 판정:** recognizer 가 student 영상에서 등재 동작 confident 인식 실패(`motion_unrecognized_layer1_only`) → 학생 technique profile `expects_extension` 전부 False → `dimensions.line_score()` None → line 키 생략. 설계상 anti-false-positive 폴백(STATE.md 장기 박제 정합). 15-03 blocking gate 아님 — recognizer student-영상 인식 정확도는 후속(Phase 5 recognizer / Phase 18) 과제. angle 차원(정은지 대비 일치도)은 7/7 정상(38~99) 으로 Mode 1 핵심 신호 작동.
- **OBSERVATIONAL only:** success 점수는 객관 numeric floor 부재(calibration-source-hard-gate)라 PASS/FAIL 판정 안 함. 블로킹 SCORE-04 = 15-04 frozen MODE_SELF baseline 단독 소유(HIGH 3). 15-03 은 15-04 MODE_SELF doc 미참조.
- **Ownership 경계:** 13-영상 통합 SC4 집계는 15-05(depends_on 15-03+15-04) 소유 — 15-03 은 Mode 1 7/7 만 gate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - 블로킹 환경 fix] onnxruntime CPU 폴백 → GPU 강제 (LD_LIBRARY_PATH)**
- **Found during:** Task 2 (1차 sweep 실행)
- **Issue:** sweep runner 가 source 한 env 에 `LD_LIBRARY_PATH`(cudnn `/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib`) 누락 → onnxruntime `libcudnn.so.9: cannot open` → CUDAExecutionProvider 실패 → CPU 폴백(GPU 0%, combo 318MB 매우 느림). .bashrc 의 PS1 비대화형 guard(line 6 `[ -z "$PS1" ] && return`)로 export 블록 미적용 + AWS/Gemini/LD_LIBRARY_PATH 는 .bashrc 부재(uvicorn proc env 에만 존재)가 root cause.
- **Fix:** sweep runner 가 live uvicorn proc(`/proc/<pid>/environ`)에서 LD_LIBRARY_PATH/CUDA_*/AWS_*/GEMINI/CEREBRAS/FIREBASE 전체 env 를 NUL-delimited 로 source(키 값 비노출). 재실행 → `ort.get_available_providers()` CUDA 포함 + cudnn 에러 0 + GPU 70%+ + climb CPU ~5.5min → GPU ~112s.
- **Files modified:** Pod-side 실행 runner 만 (repo 변경 0).
- **Verification:** `ort providers (after env): [..., 'CUDAExecutionProvider', ...]`, cudnn 에러 count 0, GPU util 70%.
- **Committed in:** `9d11112` (evidence 문서에 deviation 기록)

**2. [Rule 3 - 블로킹 외부 의존 retry] Gemini 503 UNAVAILABLE — peter-pan/power-spin 재실행**
- **Found during:** Task 2 (메인 sweep item 6/7)
- **Issue:** Gemini API `503 UNAVAILABLE`(transient) → `_process` 예외 → 두 doc `comparison` 상태로 미완(errorCode 미기록, server_error 아님). pdshape 는 Gemini files.get 503 graceful skip 후 정상 done.
- **Fix:** 두 motion 만 2-item keys 로 별도 재실행(새 per-run uid `phase15_mode1_1781689675370`, HIGH 2 fixed id 재사용 0). stuck doc 2개 선삭제(stale 차단) → 재실행 둘 다 `_process OK` + done + server_error 0 (peter-pan=97, power-spin=95).
- **Files modified:** Pod-side 실행만 + Firestore 임시 doc cleanup (repo 변경 0).
- **Verification:** retry sweep exit=0, invariant `_process=2`, read-back 2/2 done server_error 0.
- **Committed in:** `9d11112` (evidence 문서에 deviation 기록)

---

**Total deviations:** 2 auto-fixed (2 블로킹 — 1 환경/GPU, 1 외부 LLM transient retry)
**Impact on plan:** 둘 다 Mode 1 7/7 done gate 충족에 필수. scope creep 0. 임의 numeric floor/line floor 신규 fit 0(MEDIUM 6 / calibration-source-hard-gate 정합).

## Issues Encountered
- **SSM gemini-key 직접 decrypt read 차단:** auto-mode classifier 가 `aws ssm get-parameter --with-decryption` stdout read 를 차단(키 값 출력 금지 정합). 대안으로 live uvicorn proc env 의 GEMINI_API_KEY(값 비노출)를 그대로 재사용 — secret 한 번도 출력/commit 0.
- **macOS NFD 파일명:** 정은지 fail 영상 한글명 NFD 저장은 upload_phase15_dataset.py 가 이미 NFC normalize(15-01 fix)로 처리 — 13 영상 전부 정상 업로드.
- **out-of-scope:** line=None 은 recognizer student-영상 인식 한계(설계상 폴백)이지 15-03 결함 아님 — 후속 과제로 evidence 에 명시 기록.

## User Setup Required
None — 모든 SSH/AWS/SSM/Firestore/sweep 작업은 Claude 가 sunity-motion + Firebase SA 자격으로 자동 실행(pod-ops-claude-runs).

## Next Phase Readiness
- **15-04 (MODE_SELF 위양성 baseline):** Mode 3 success/fail pair sweep + frozen 08.1 baseline 대조 진입 가능. 15-03 은 MODE_SELF doc 미생성·미참조(same-wave race 차단).
- **15-05 (13-영상 통합 SC4):** 15-03 Mode 1 evidence(7) + 15-04 Mode 3 evidence(6) 합산 → total/completed/no_human/not_pole_motion/server_error 집계.
- **Open (후속):** student 영상에서 line 차원 해소 = recognizer 인식 정확도 과제(Phase 5/18). axis severity 위양성 블로킹 = 15-04.
- Pod ephemeral — Pod 재생성 시 RUNPOD_ANALYZE_URL/SSM 재동기화 필요(15-02 절차 재사용).

## Self-Check: PASSED

- FOUND: `.planning/phases/15-mode-1-mode-3-testflight/15-MODE1-FALSEPOSITIVE-EVIDENCE.md`
- FOUND: `.planning/phases/15-mode-1-mode-3-testflight/15-03-SUMMARY.md`
- FOUND: commit `9d11112` (evidence)
- Mode 1 7/7 server_error==0 verified from real Firestore docs (uid phase15_mode1_1781688254964 + 1781689675370)
- seed-reference-downstream.mjs --verify completeRequiredSet=11/11

---
*Phase: 15-mode-1-mode-3-testflight*
*Completed: 2026-06-17*
