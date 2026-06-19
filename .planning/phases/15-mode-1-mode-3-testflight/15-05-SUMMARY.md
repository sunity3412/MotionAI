---
phase: 15-mode-1-mode-3-testflight
plan: 05
subsystem: delivery
tags: [deliv-01, sc4, testflight, eas, testflight-preview, store-signed, sigabrt, presigned, mode1, mode3, phase15, handoff]

# Dependency graph
requires:
  - phase: 15-mode-1-mode-3-testflight (15-03)
    provides: "Mode 1 (MODE_EXPERT) 7-영상 status 카운트 (done 7 / server_error 0) — 15-MODE1-FALSEPOSITIVE-EVIDENCE.md §Mode1 GATE"
  - phase: 15-mode-1-mode-3-testflight (15-04)
    provides: "Mode 3 (MODE_SELF) 6-페어 status 카운트 (total12/done12/server_error0) — 15-MODE3-DUALCOACH-EVIDENCE.md §Mode3status"
provides:
  - "13-영상 통합 SC4 집계 (15-03 Mode1 7 + 15-04 Mode3 6 read-only 합산, combined_total 13 / completed 13 / server_error 0) — verify 가 실 카운트 parse (MEDIUM 4)"
  - "store-signed testflight-preview EAS 빌드 프로필 (channel preview, autoIncrement true, production env mirror, distribution:internal 없음) — TestFlight/ASC submit 가능"
  - "EAS testflight-preview 빌드 #20/#21 FINISHED + 아티팩트 + #21 auto-submit (Claude-side 빌드+submit PASS)"
  - "DELIV-01 belle 실기기 핸드오프 준비 완료 (Claude-side PASS, belle device 검증만 blocking-checkpoint 대기)"
affects: [phase-18-fault-eval-set, phase-20-v2-vision-score]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "store-signed 빌드 프로필 + --auto-submit-with-profile production (동일-이름 submit 프로필 default 회피, R5)"
    - "EAS Install dependencies UNKNOWN_ERROR 는 transient infra — repo 수정 0 재시도로 해소 (#17/#18/#19 errored → #20/#21 FINISHED)"
    - "SC4 = read-only status 카운트 합산 (재sweep/재분석 0) + machine-parseable 카운트 행 verify parse"

key-files:
  created:
    - .planning/phases/15-mode-1-mode-3-testflight/15-SC4-AGGREGATE-EVIDENCE.md
  modified:
    - app/eas.json
    - .planning/phases/15-mode-1-mode-3-testflight/15-DELIV-EVIDENCE.md

key-decisions:
  - "13-영상 SC4 단위 = 분석 unit(motion/pair): Mode 1 7 motion + Mode 3 6 motion/pair = 13 (Mode3 doc 12 와 척도 다름, 둘 다 server_error 0)"
  - "빌드 PASS 판정 = #20/#21 FINISHED + 아티팩트 (동일 프로필 repo 수정 0 재시도) → #17~#19 errored 는 EAS remote worker 일시 장애로 확정"
  - "런타임 SIGABRT 부재는 build 로그로 단언 금지(LOW 7) — belle device 결과가 유일 증거. static 가드(track=()=>0)만 Claude-side"
  - "기존 preview 프로필(distribution:internal)은 내부 설치 전용 보존 — TestFlight submit 미사용"

patterns-established:
  - "Pattern: SC4 통합 집계 = depends_on 두 plan 의 확정 evidence 카운트 read-only 합산 (same-wave race 회피, HIGH 3 single-owner)"
  - "Pattern: 미검증 빌드 belle 핸드오프 금지 (D-09 verify-before-handoff) — Claude-side 빌드+submit+static PASS 이후에만"

requirements-completed: [DELIV-01, MODE-01, MODE-02, SCORE-04]

# Metrics
duration: ~50min (Claude-side) + belle device checkpoint 대기
completed: 2026-06-19 (Claude-side PASS; belle 실기기 checkpoint blocking-open)
---

# Phase 15 Plan 05: 13-영상 통합 SC4 집계 + store-signed testflight-preview 빌드 + DELIV-01 belle 핸드오프

**15-03 Mode 1(7 motion done/server_error 0) + 15-04 Mode 3(6 motion-pair done/server_error 0) status 카운트를 read-only 합산해 13-영상 통합 SC4(combined_total 13 / completed 13 / server_error 0)를 machine-parseable 카운트 행으로 박고(verify 가 실 카운트 parse — MEDIUM 4, 재sweep 0 HIGH 3), distribution:internal 없는 store-signed testflight-preview 빌드 프로필을 신설해(production env mirror, autoIncrement true) EAS 빌드 #20/#21 FINISHED + 아티팩트 + #21 auto-submit 로 Claude-side 빌드+submit PASS 를 확정했으며(#17~#19 errored 는 EAS infra transient 로 판정), static/회귀 체크 통과 후 belle 실기기 게스트 완주 + 영상 재생 + 런타임 SIGABRT 부재 검증만 blocking-checkpoint 로 핸드오프했다(D-09 verify-before-handoff).**

## Performance

- **Duration:** ~50 min Claude-side (SC4 집계 + 프로필 + 빌드/submit + evidence) + belle device checkpoint 대기
- **Completed (Claude-side):** 2026-06-19
- **Tasks:** 3 auto + 1 blocking human-verify checkpoint (belle device — open)
- **Files modified:** 1 created (SC4 evidence) + 2 modified (eas.json, DELIV evidence)

## Accomplishments
- **Task 1 (SC4, HIGH 3/MEDIUM 4):** 13-영상 통합 집계를 `15-SC4-AGGREGATE-EVIDENCE.md` §SC4-집계 표 + machine-parseable 카운트 행(mode1_total 7 / mode3_total 6 / combined_total 13 / combined_completed 13 / combined_server_error 0)에 박음. 15-03/15-04 확정 evidence 카운트 read-only 합산만(재sweep/재분석 0). verify 가 4 키 실 카운트 parse PASS(파일 존재 silent 통과 차단). 안전게이트(no_human/not_pole_motion) 발동 0, unexpected pipeline 실패(server_error) 0. SC4 단위 정합(motion/pair 13 vs Mode3 doc 12) 명기.
- **Task 2 (HIGH 3):** `app/eas.json` 에 store-signed `testflight-preview` 빌드 프로필 신설(commit `3486bbd`) — distribution:internal 없음(TestFlight submit 차단 원인 해소) / channel preview / autoIncrement true / production env 7키(Firebase 6 + API base URL) mirror(node assert PASS). 기존 preview(internal)는 내부 설치 전용 보존. submit 섹션 미변경(production 재사용, R5). typography.ts:15 `track=()=>0` SIGABRT static 가드 유지 + negative letterSpacing 곱셈 패턴 grep 0. tsc --noEmit clean.
- **Task 3 (R5, LOW 7):** EAS testflight-preview 빌드 — #17/#18/#19 가 Install dependencies UNKNOWN_ERROR 로 errored 했으나 repo 수정 0 재시도로 **#20(`aebb083e`, commit 90f26d05) + #21(`1a387686`, commit e022afc, Phase 19 포함) FINISHED + 아티팩트 존재**. #21 은 `--auto-submit-with-profile production`(ASC App ID 6772934567) auto-submit 예약(submission `fd0662ca`). → #17~#19 errored = EAS remote worker transient infra 로 확정. static/build 체크 5/5 + 회귀 체크리스트 2/2 PASS(presigned `POST /playback-url` 7일 refresh path 존재 / S3 PUT Content-Type 명시). 런타임 SIGABRT 부재는 build 로그로 단언 안 함(belle device 결과로 이연).
- **Checkpoint (DELIV-01, blocking-open):** Claude-side 빌드+submit+static PASS 확정으로 belle 핸드오프 가능(D-09 충족). belle 가 TestFlight 빌드 #21 설치 → 익명 게스트 Mode 1+3 완주 + 결과 영상 재생 + 런타임 SIGABRT 부재 확인 후 "approved" 시 plan 종결.

## Task Commits

SC4 집계 + 빌드/submit 은 evidence-doc + eas.json 변경. (Task 2 eas.json `3486bbd` 선행 commit, 본 close-out 에서 SC4 evidence + DELIV evidence 갱신 commit.)

1. **Task 2 (testflight-preview 프로필)** - `3486bbd` (app/eas.json)
2. **Task 1 + Task 3 (SC4 집계 + 빌드 PASS evidence)** - 본 close-out commit (docs)

## Files Created/Modified
- `.planning/phases/15-mode-1-mode-3-testflight/15-SC4-AGGREGATE-EVIDENCE.md` - 13-영상 통합 SC4 집계 표 + machine-parseable 카운트 행 + 단위 정합(motion/pair vs doc) + read-only 합산 근거
- `app/eas.json` - store-signed testflight-preview 빌드 프로필 (channel preview / autoIncrement true / production env mirror / distribution:internal 없음)
- `.planning/phases/15-mode-1-mode-3-testflight/15-DELIV-EVIDENCE.md` - 프로필 diff + static/build 체크 표 + 빌드 성공(#20/#21 FINISHED) + transient 판정 + 회귀 체크리스트 + belle 핸드오프 절차(빌드 PASS 확정, device 검증만 대기)

## Decisions Made
- **SC4 단위 = motion/pair 13(Mode1 7 + Mode3 6):** Mode 3 의 doc 수(12 = 6 페어 × {fault,success})와 다른 척도. server_error 는 doc-level/unit-level 모두 0 으로 동일. combo 는 Mode-1-only 7 에 포함(Mode-3 페어 없음 — 정상).
- **빌드 PASS 판정(transient 확정):** 동일 testflight-preview 프로필 + repo 수정 0 으로 #20/#21 FINISHED → #17~#19 의 UNKNOWN_ERROR 는 EAS infra 일시 장애. DELIV evidence 의 "EAS-infra 면 재시도" 진단 경로가 정답이었음. 로컬 `npm ci` PASS(lockfile/peer-dep 원인 아님)와 정합.
- **런타임 SIGABRT 부재는 device-only 증거(LOW 7):** release 런타임 크래시 경로라 build 로그로 단언 금지. Claude-side 는 static 가드(track=()=>0 present + negative letterSpacing 0)만. 최종 부재 판정은 belle device.
- **objectivity(D-06):** SC4 집계는 status 카운트(객관 pipeline 상태)만 합산 — 사람 점수 라벨 ground truth 미사용. 점수 품질 판정은 15-03/15-04 evidence 소관.

## Deviations from Plan

### Auto-fixed Issues

**1. [빌드 실패 → 재시도로 해소] EAS Install dependencies UNKNOWN_ERROR (#17/#18/#19) → repo 수정 없는 재빌드(#20/#21) FINISHED**
- **Found during:** Task 3 (1차 빌드, 2026-06-17)
- **Issue:** testflight-preview 빌드 #17/#18/#19 가 EAS remote worker 의 Install dependencies 단계에서 ~1분 내 즉시 errored(errorCode UNKNOWN_ERROR). 로컬 `npm ci` 는 동일 lockfile 로 PASS → repo-side 원인 아님.
- **Fix:** repo 수정 0. EAS 워커 일시 장애 가설에 따라 재빌드 → #20(2026-06-17 21:11 KST)·#21(2026-06-18) FINISHED + 아티팩트.
- **Files modified:** 없음 (repo 변경 0).
- **Verification:** `eas build:list` — #20 `aebb083e` / #21 `1a387686` status FINISHED, artifacts True, profile testflight-preview, dist STORE, channel preview.
- **Committed in:** 본 close-out (DELIV evidence 에 기록).

---

**Total deviations:** 1 (빌드 인프라 transient, repo 수정 0 해소)
**Impact on plan:** scope creep 0. 빌드 config/프로필/자격/submit 경로는 처음부터 정상이었고 실패는 EAS infra 일시 장애였음.

## Issues Encountered
- **EAS Install dependencies transient(#17~#19):** 위 deviation 참조 — 재시도로 해소, repo 수정 0. 메모리 [[eas-build-gotchas]] 정합(transient 큐/워커 항목).
- **belle device checkpoint open:** 런타임 SIGABRT 부재 + 게스트 완주 + 영상 재생은 사람-전용 — Claude-side 로 단언 불가. plan 은 이 blocking-checkpoint 가 "approved" 될 때 완전 종결.

## User Setup Required
- **belle (blocking):** TestFlight 에서 빌드 #21(`1a387686`, 1.0.0/21) 설치 → 익명 게스트 진입 → Mode 1 완주(정은지 기준 점수) + Mode 3 완주(N점 발전 델타) + 결과 영상 재생 + 런타임 SIGABRT 부재 확인. 결과를 15-DELIV-EVIDENCE.md §belle 핸드오프 표에 기록. resume-signal "approved".

## Next Phase Readiness
- **Phase 18 (Expert deliberate-fault eval set):** 15-04 가 defer 한 success-severity 자동 gating + fail per-fault gating 의 labeled eval set. 오늘(2026-06-19) belle 6 페어 수동 eval baseline(power-spin 72/100, peter-pan 79/100, elbow-twist 59/100, pdshape 58/100, kip-up 100/100 위양성, climb not_pole 게이트)을 정식 fixture 로 박제 예정.
- **Phase 20 (v2 비전 점수):** kip-up 위양성(100 vs 100) + climb 차단 + 상단 변별을 belle 스펙(같은 정은지 95~100 / 잘못된 동작 ≤50 / Gemini 시각 점수) + EVAL baseline 표 게이트로 해소.
- Pod ephemeral — 재생성 시 RUNPOD_ANALYZE_URL/SSM 재동기화(HANDOFF 절차 + pod_bootstrap_full.sh).

## Self-Check: PASSED (Claude-side)

- FOUND: `.planning/phases/15-mode-1-mode-3-testflight/15-SC4-AGGREGATE-EVIDENCE.md` — verify SC4 OK (mode1_total 7 / mode3_total 6 / combined_total 13 / combined_server_error 0)
- FOUND: `app/eas.json` testflight-preview 프로필 (node assert OK) + commit `3486bbd`
- EAS 빌드 #20/#21 FINISHED + 아티팩트 (eas build:list 확인) + #21 auto-submit 예약
- static/build 5/5 + 회귀 2/2 PASS
- OPEN: belle device checkpoint (런타임 SIGABRT 부재 + 게스트 완주 + 영상 재생) — blocking, 사람-전용

---
*Phase: 15-mode-1-mode-3-testflight*
*Completed (Claude-side): 2026-06-19 — belle device checkpoint blocking-open*
