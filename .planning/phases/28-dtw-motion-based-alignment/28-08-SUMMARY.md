---
phase: 28-dtw-motion-based-alignment
plan: 08
subsystem: infra
tags: [eas-update, ota, pytest, typecheck, runpod, firestore, dtw, motion-alignment]

# Dependency graph
requires:
  - phase: 28-04
    provides: motionAlignment 방출 (anchors 초 단위·tier 사다리) + 채점 무접촉 단위 증명
  - phase: 28-05
    provides: ratio 근사 제거 + fault_zoom refMatch 표시 경로
  - phase: 28-06
    provides: warp 경유 재생 (rightPlayer.currentTime WARP_ROUTED)
  - phase: 28-07
    provides: result 화면 소비 배선 (tier 배지 + D-05 legacy 재분석 배너 + refMatch 캡션)
provides:
  - "phase 28 전체 로컬 게이트 green 박제 (affected pytest / typecheck / grep 4종 / 채점 무접촉 phase-범위 diff)"
  - "Pod 실분석 1건으로 motionAlignment end-to-end 실재 기계 판정 (DOC_CHECK_OK)"
  - "preview → production OTA 순차 발행 (runtime 1.0.0), production group aa3b0ec9-..."
affects: [29-mode3-result-screen-completion, 31-api-visual-correction, batch-uat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "phase-범위 diff 게이트 (PHASE_START..HEAD) — 단일 커밋이 아닌 phase 전체로 채점 무접촉/JS-only 판정"
    - "gate plan: 코드 변경 0, 게이트 실행 + 배포 확인만 (files_modified: [])"

key-files:
  created:
    - .planning/phases/28-dtw-motion-based-alignment/28-08-SUMMARY.md
    - .planning/phases/28-dtw-motion-based-alignment/28-HUMAN-UAT.md
  modified: []

key-decisions:
  - "belle 결정 (Task 5): '지금 발행 — 배치 UAT'. 실기기 확인을 blocking 하지 않고 production OTA 를 지금 발행, 실기기 5항목은 phase 31 후 합동 UAT 로 적립 (phase 27 선례)."
  - "belle 승인 (Task 2): Pod SSH 재분석 1건 착수 승인."
  - "PHASE_START = 8a6b106 (28-01 첫 커밋) — 채점 무접촉/JS-only diff 게이트 단일 기점."

patterns-established:
  - "gate plan 종결 절차: 로컬 게이트 → belle 승인 → Pod 실분석 1건 → preview OTA → belle 확인(배치 UAT) → production OTA → SUMMARY"

requirements-completed: [ALGN-01, ALGN-02, ALGN-03, ALGN-04, ALGN-05, ALGN-06]

# Metrics
duration: ~40min (Task 1-4 earlier session, Task 6 이번 continuation)
completed: 2026-07-08
---

# Phase 28 Plan 08: DTW 동작 정렬 phase gate 종결 Summary

**phase 28 전체가 로컬 게이트 green + Pod 실분석 1건에서 motionAlignment(tier=disabled, 초 단위 anchors) 기계 판정 + preview→production OTA 순차 발행으로 종결. 채점 무접촉을 phase-범위 diff + 실데이터 점수 무이동(52=결정론 baseline) 양쪽으로 증빙.**

## Performance

- **Duration:** ~40min (Task 1-4 이전 세션 + Task 6 continuation)
- **Started:** 2026-07-08T13:15:31Z (Task 5 checkpoint 적립)
- **Completed:** 2026-07-08T13:34:28Z
- **Tasks:** 6 (Task 2/5 = belle checkpoint)
- **Files modified:** 0 코드 (gate plan) — 문서 2개(28-HUMAN-UAT.md, 이 SUMMARY)

## Accomplishments

- phase 28 전체 로컬 게이트 일괄 green (affected pytest 신규 FAILED 0 / typecheck 0 / grep 4종 / 채점 무접촉 phase-범위 diff)
- Pod 실분석 1건(power-spin fault)에서 motionAlignment end-to-end 실재를 read-only Firestore 검사로 기계 판정 (DOC_CHECK_OK)
- 채점 무접촉 이중 증빙: phase-범위 diff 에 채점 코어 부재(SCORING_CORE_ABSENT) + 실데이터 overallScore 52 = 문서화 결정론 baseline 무이동
- preview(577ac5e9-...) → production(aa3b0ec9-...) OTA 순차 발행, runtime 1.0.0, 동일 app 콘텐츠(b6a14a8)

## Task Commits

이 플랜은 **gate plan** (files_modified: [], 코드 변경 0) — 게이트 실행/배포 확인/문서화만 수행. per-task 코드 커밋 없음.

1. **Task 1: 로컬 게이트 일괄** — 코드 변경 0 (게이트 실행만, 결과 아래 표)
2. **Task 2: belle 승인 (Pod 재분석 착수)** — checkpoint, 승인 회신
3. **Task 3: Pod 동기화 + 재분석 1건** — 운영 확인만 (Pod git pull 1c64288→b6a14a8)
4. **Task 4: JS-only 게이트 + preview OTA 선발행** — 배포 (preview group 577ac5e9-...)
5. **Task 5: belle 실기기 확인** — checkpoint, 결정 "지금 발행 — 배치 UAT" (28-HUMAN-UAT.md 5항목 적립, `741a54b`)
6. **Task 6: production OTA 발행 + SUMMARY** — 배포 (production group aa3b0ec9-...) + 이 문서

**문서 커밋:** `741a54b` (docs(28-08): HUMAN-UAT 적립) + 이 SUMMARY 커밋 (docs(28-08): complete plan)

## Task 1 — 로컬 게이트 표 (박제)

**PHASE_START = `8a6b106`** (28-01 첫 커밋, base `53860a1`). 이하 diff 게이트는 `8a6b106..HEAD` 범위.

| 게이트 | 명령 스코프 | 결과 |
|--------|-------------|------|
| affected pytest | `pytest tests/ -k "alignment or fault_zoom or pipeline"` | 신규 FAILED/ERROR **0** (pre-existing ~49건 = full-suite 스코프, STATE.md baseline 과 IDENTICAL) |
| typecheck | `cd app && npm run typecheck` | exit **0** |
| grep (a) ratio 근사 부재 | 28-05 게이트 명령 재실행 | **0** (근사 부재) |
| grep (b) warp 경유 재생 | `rightPlayer.currentTime =` WARP_ROUTED | **2** (helper-internal — warp 경유만) |
| grep (c) 3-way lockstep | `grep -c motionAlignment analysis.ts / models.py / contract.md` | 각 **>= 1** (계약 동기화) |
| grep (d) 임계 출처 | `grep -c "_ALIGN_GLOBAL" motion_alignment.py` | **4** (>= 1) |
| 채점 무접촉 diff (W1) | `git diff --name-only 8a6b106..HEAD` | **SCORING_CORE_ABSENT** — vision_veto/kismam/dimensions/deduction_engine/motiondtw 부재 (fault_zoom 은 표시 경로만) |

## Task 3 — Pod 실분석 증거 + DOC_CHECK

- **Pod:** `s7gyvvlc6u7ktz` (플랜 기재 `svn31pzja7uay0` 는 dead — 메모리 [[current-pod-hbpvhedq2bu01i]] 최신 Pod 로 대체)
- **동기화:** `git pull` 1c64288 → **b6a14a8**, 서버 재시작 → `/health` `pipeline_loaded: true`
- **재분석 1건 (순차, pipeline-not-concurrency-safe-eval-serial 준수):**
  - uid `phase28eval` / analysisId `powerspinFaultAlign1783516096`
  - fixture `fixtures/phase15/power-spin/fault.mp4` (mode1 vs ref-power-spin)
  - status **done** / **overallScore 52** (= 문서화된 결정론 baseline, ±0 무이동 — 채점 무접촉 실데이터 관측) / wallMs 155013
- **motionAlignment:** tier **`disabled`** (reason=low_global_confidence, DTW distance **60.13 > T2=25.0**), anchorCount 20 / anchors len 40 (짝수 flat), u 단조증가·r 단조비감소, 초 단위 범위 OK
- **faultZoomComparisons:** 3건, refMatch present
- **verify 스니펫 출력: `DOC_CHECK_OK`** (assert 전부 통과 — motionAlignment 존재 / tier 3종 / anchors 초 단위·짝수·단조 / anchorCount*2==len / refMatch)

### tier=disabled caveat (중요)

이 재분석 doc 의 tier 가 `disabled` 인 것은 **버그가 아니라 설계된 안전 동작**이다. fault 영상(학생이 틀리게 수행)은 reference(정은지 정타)와 전역 DTW 유사도가 낮아 워핑을 끄고 legacy 동기 재생으로 폴백한다 (tier 사다리: distance ≤8.0→warped / ≤25.0→trim_only / else→disabled). 따라서 이 doc 에서는 워핑이 아니라 "disabled" tier 배지 + 기존 동기 재생이 보인다. **워핑(tier=warped) 체감은 학생이 reference 를 근접히 따라간 doc(실제 학생 시연 or correct fixture)에서 확인 필요** — "1건만" 제약(순차) 준수로 이 게이트에서는 warped doc 미생성. 워핑 경로 자체는 28-04/05/06 단위검증으로 커버됨.

## Task 4 / Task 6 — OTA 발행 로그 (양 채널)

| 채널 | Group ID | Runtime | 커밋(app 콘텐츠) | 발행 |
|------|----------|---------|------------------|------|
| preview (Task 4) | `577ac5e9-2816-4d9b-bd9f-559aa74b8213` | 1.0.0 | b6a14a8 | 선발행 (belle 확인용) |
| production (Task 6) | `aa3b0ec9-5344-4dda-9b8f-f2145ecf0b94` | 1.0.0 | 741a54b* (app 콘텐츠 = b6a14a8 동일) | belle "지금 발행" 결정 후 |

- **JS-only 게이트 (W1):** `git diff --name-only 8a6b106..HEAD | grep -E '^app/(package\.json|package-lock\.json|app\.json|ios/|android/)'` = **0줄** (JS_ONLY — 신규 native 모듈 0)
- **production ≡ preview 콘텐츠:** `git diff --name-only b6a14a8..HEAD -- app/` = **empty** (741a54b 은 .planning/ 만 변경). production 번들 app JS = preview 와 byte-identical.
- **production update IDs:** Android `019f41ef-74a4-7829-b6ac-504c88a549a5` / iOS `019f41ef-74a4-77ae-b59c-de961eabbc8b`
- **메시지 (양 채널 동일):** "phase 28: DTW 동작 기반 비교 정렬 (워핑 재생 + tier 배지 + D-05 재분석 배너 + refMatch 캡션)"

## Task 5 — belle 확인 (배치 UAT 결정)

**Task 5 (checkpoint:human-verify) 는 belle 결정 "지금 발행 — 배치 UAT" 로 resolve.** 실기기 확인을 production 발행의 blocking 조건으로 두지 않고, phase 27 선례에 따라 production OTA 를 지금 발행하고 실기기 5항목은 **phase 31 후 합동 UAT** 로 적립한다 (메모리 [[batch-uat-after-phase-31]]).

적립 위치: `28-HUMAN-UAT.md` (commit `741a54b`, status: partial, pending 5). 재분석 doc 의 tier=disabled 이므로 워핑 체감은 별도 doc 필요 — UAT Gaps 에 명기됨.

실기기 확인 5항목 체크리스트 (전부 [pending] — 배치 UAT 로 이월):
1. 비교 재생 정렬 체감 (D-01 / A2) — [pending]
2. 스크럽/재시작 동기 유지 (Pitfall 7) — [pending]
3. tier 배지 카피 (D-02 사다리) — [pending] (재분석 doc = disabled 배지가 정상)
4. legacy 재분석 유도 배너 (D-05) — [pending]
5. 확대비교 카드 정합 (D2 종결 / D-04) — [pending]

## Decisions Made

- **belle Task 2 승인:** Pod SSH 재분석 1건 착수 승인.
- **belle Task 5 결정:** "지금 발행 — 배치 UAT" (실기기 확인 non-blocking, phase 31 후 합동).
- **Pod 대체:** 플랜 기재 Pod svn31pzja7uay0 dead → s7gyvvlc6u7ktz (최신 Pod) 사용.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 플랜 기재 Pod dead → 최신 Pod 로 대체**
- **Found during:** Task 3 (Pod 동기화)
- **Issue:** 플랜의 Pod `svn31pzja7uay0` (SSH root@213.173.102.233:12729) 가 dead 상태.
- **Fix:** 메모리 [[current-pod-hbpvhedq2bu01i]] 의 활성 Pod `s7gyvvlc6u7ktz` 로 동기화·재분석 수행. Pod 코드 pull 1c64288→b6a14a8, /health pipeline_loaded:true 확인.
- **Files modified:** 없음 (운영 작업)
- **Verification:** DOC_CHECK_OK
- **Committed in:** N/A (코드 변경 0)

---

**Total deviations:** 1 auto-fixed (1 blocking — Pod 교체, 운영 인프라 변경, 코드 무접촉)
**Impact on plan:** 스코프 변화 없음. Pod 교체는 운영 인프라 실체와 플랜 기재 불일치 해소일 뿐 산출물 동일.

## Issues Encountered

- **재분석 doc tier=disabled:** power-spin fault fixture 는 reference 와 DTW distance 60.13 (>T2 25.0) 로 워핑이 꺼진다. 이는 설계된 안전 동작(위 caveat)이며 warped 체감은 배치 UAT 에서 별도 correct doc 으로 확인. 워핑 경로는 28-04/05/06 단위검증으로 커버.

## User Setup Required

None - no external service configuration required. (실기기 확인은 배치 UAT 로 이월 — 28-HUMAN-UAT.md)

## Next Phase Readiness

- phase 28 gate 종결: 로컬 게이트 green + Pod 실분석 기계 판정 + production OTA 라이브.
- 채점 무접촉이 단위(28-04) + 실데이터(52 무이동) 양쪽 증빙.
- 잔여: 실기기 5항목 배치 UAT (phase 31 후 합동), warped tier 체감 doc.
- 다음: phase 29(mode3 result 완성) / 30(growth tracking) / 31(api visual correction) — 플랜 산출 완료 상태.

## Self-Check: PASSED

- FOUND: `.planning/phases/28-dtw-motion-based-alignment/28-08-SUMMARY.md`
- FOUND commit: `741a54b` (28-HUMAN-UAT 적립)
- FOUND production OTA group `aa3b0ec9-5344-4dda-9b8f-f2145ecf0b94` (eas update:list --branch production)

## Addendum — 코드 리뷰 fix 재발행 (2026-07-08, phase 마감 직전)

phase 28 코드 리뷰(28-REVIEW.md)에서 Critical 2건(CR-01 mode3 fps 도메인, CR-02 stepBy 시간축 혼합) + Warning 4건 fix 후 belle 승인으로 재배포:

- fix HEAD: `349aceb` (fix 커밋 f814b23/9178b7f/f3048b2/f8814b0/da8848e/7b0eec7), origin push 완료
- Pod `s7gyvvlc6u7ktz` pull 349aceb + start_server.sh 재시작, /health ok·pipeline_loaded true
- preview OTA 재발행: group `6a1df648-b697-4b7d-a83c-b6cc5211dbaa`
- production OTA 재발행: group `1581bdf3-245c-4d57-954a-dc9c8f85b094` (위 aa3b0ec9를 대체)
- JS-only 재확인: b6a14a8..349aceb app diff = VideoCompare.tsx 1개, native touch 0
- WR-04(veto still fps 오독)는 채점 무접촉 게이트로 deferred — 28-REVIEW.md에 기록

---
*Phase: 28-dtw-motion-based-alignment*
*Completed: 2026-07-08*
