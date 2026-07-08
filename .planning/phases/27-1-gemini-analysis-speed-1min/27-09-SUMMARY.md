---
phase: 27-1-gemini-analysis-speed-1min
plan: 09
subsystem: infra
tags: [pod, deploy, eval, gate, no-regression, d-01]

# Dependency graph
requires:
  - phase: 27-1-gemini-analysis-speed-1min
    provides: "waves 3~7 최적화 + 27-08 Flash 판정 (전용 키 반영 경로) + 27-02 before cold run (대조 정본)"
provides:
  - "D-01 hard gate 판정 = PASS — EVAL18 6페어 cold 무회귀 + fan-out 4/4 완주 + 업로드/delete 24/24 균형 + prefetch submit-before-rtmw 13/13"
  - "before/after stage-timing 표 (두-지표 분리) — time-to-first-result median 229.6s→124.7s (−46%), Gemini vision 그룹 138.5s→29.9s (−78%)"
  - "Pod 프로덕션 = 3894bc8 + env 6종 박제 (GEMINI_UPLOAD_PREFETCH=1, GEMINI_FANOUT_WORKERS=4, STUDENT_FRAME_CACHE=1, GEMINI_MOMENT_MODEL=gemini-3.5-flash + 기존 VETO 2종)"
  - "pre-existing 발견: TechniqueCache hit 시 hold_window 미복원 → extension 측정 창 drift (gap-closure 회부, deferred-items.md)"
affects: [phase-27-verify, gap-closure, 27-VALIDATION]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "cold/warm 결정론 판정 = 점수뿐 아니라 record measuredValue 레벨 대조 — 관절당 감점 상한(−20)이 측정 drift 를 가릴 수 있음 (power-spin fault 78.27°↔140.9° 점수 동일 사례)"
    - "게이트 divergence 의 병렬화-귀속 여부 = 코드 고고학 (git log -L 함수 범위) + 결정론 불변량(alignment byte-동일)으로 분리"

key-files:
  created:
    - .planning/phases/27-1-gemini-analysis-speed-1min/deferred-items.md
    - .planning/phases/27-1-gemini-analysis-speed-1min/27-09-SUMMARY.md
  modified:
    - .planning/phases/27-1-gemini-analysis-speed-1min/27-TIMING-AFTER.md
    - backend/shared/python/sunity_shared/analysis/file_session.py (orphan fix, 3894bc8)
    - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py (전용 키, 87a9326)

key-decisions:
  - "D-01 gate = PASS — rollback 불발동, Pod 프로덕션 구성 유지. fault 멤버 drift 2건(kip-up 100→80, power-spin 57→52)은 vision 짚기 run 변동의 결함-검출 방향 — 회귀 아님 (success 5/5 record 동일)"
  - "cold/warm 결정론 = 병렬화 귀속 위반 0 으로 PASS. power-spin 2멤버 divergence 는 phase 8 코드(_profile_from_cache hold_window 미복원)의 pre-existing 버그 — env rollback 으로 해소 불가한 캐시 경계 문제라 gap-closure 회부 (채점 표면 변경이므로 자체 EVAL 게이트 동반 필수)"
  - "s3_download 이상치 4건(성공 멤버 64.6~135.8s)은 네트워크 변동으로 판정 (warm/before 동일 파일 정상 + 재시도 로그 0) — TTFR 표에 원인 병기, 레버는 범위 밖"

requirements-completed: [SPD-06]

# Metrics
duration: ~4.5h (배포 16min + cold/warm sweep 벽시계 ~57min + 판정/문서)
completed: 2026-07-08
---

# Phase 27 Plan 09: After 실측 + D-01 Hard Gate 판정 Summary

**waves 3~7 + Flash 전용 키를 프로덕션 Pod(3894bc8)에 배포하고 EVAL18 6페어 cold/warm sweep 으로 D-01 hard gate 를 판정 — 무회귀 PASS (success 5/5 record 동일, fault drift 는 검출 방향), time-to-first-result median 229.6s→124.7s (−46%, s3 정규화 시 104s), Gemini vision 그룹 −78%. cold/warm 결정론은 병렬화 귀속 위반 0 — 유일한 divergence(power-spin leg_extension)는 phase 8 TechniqueCache hold_window 미복원 pre-existing 버그로 확정해 gap-closure 회부.**

## Performance

- **Duration:** ~4.5h (Task 2 배포 06:17~06:33 · cold sweep 06:38~07:08 · warm 07:14~07:35 · 판정/문서 이후)
- **Tasks:** 3 (Task 1 = checkpoint, belle "approved 끝까지" 수신)
- **Gemini 크레딧:** EVAL18 sweep 2세트 (cold+warm, 승인 범위 내)

## Accomplishments

- **배포 + env 박제 (Task 2):** Pod `s7gyvvlc6u7ktz` = `3894bc8`, start_server.sh 에 신규 env 4종 박제 + 라이브 프로세스 environ 검증, /health 200, 스모크에서 prefetch submit-before-rtmw 9.3s 실증. 스모크가 File API orphan 누수 1건을 발견해 즉시 fix(`3894bc8`) + 잔존 25건 전량 삭제 → 0.
- **D-01 무회귀 PASS:** 12멤버 record 레벨 기계 대조 — success 5/5 완전 동일, fault 2건 drift 는 모두 감점 증가(결함 검출) 방향 + margin 유지·확대 (kip-up known FP TIE→discriminate 20). 정본 `assert_baseline.py` PASS.
- **fan-out/업로드 규율 프로덕션 증빙:** veto completedCalls 4/4 전원 (429 실검출 0, workers=4 최종 채택), 학생 영상 업로드 분석당 1회 + 업로드/삭제 24/24 균형 (누수 0), prefetch 순서 13/13.
- **cold/warm 결정론:** 10/12 멤버 measuredValue 레벨 byte-동일. divergence 1계보(power-spin leg_extension)를 코드 고고학으로 **pre-existing**(phase 8 `_profile_from_cache` hold_window 미복원) 확정 — alignment byte-동일로 RTMW/DTW 결정론은 입증, 병렬화 무혐의.
- **before/after 두-지표 표 (MEDIUM-3):** TTFR median 124.7s (−46%) / server task 총 시간 133.7s (−42%) / zoom 추가 도착 median 7.7s 분리 기재. 단계별: scene_finder −90%, recognizer −84%, veto_collect −75%, coach_dual −32%, fault_zoom −52%+사후 이동. 역행(pp-S +4%)은 s3 네트워크 변동 전액 귀속 — 원인 병기.

## Task Commits

이전 세션 (Task 1~2 + sweep 착수):
1. `87a9326` — feat(27-09): GEMINI_MOMENT_MODEL 전용 키 (27-08 이관분 반영)
2. `af56fb2` — docs(27-09): canary/rollback 선기록
3. `3894bc8` — fix(27-09): File API orphan 정리 (스모크 발견, Rule 1)
4. `0c4aa92` — docs(27-09): 배포 기록 (§0~§1)

이번 세션 (Task 3 판정):
5. docs(27-09): D-01 gate 판정 PASS + before/after 두-지표 표 (§2~§3) + deferred-items

## Files Created/Modified

- `27-TIMING-AFTER.md` §2/§3 — 게이트 판정 정본 (235줄): 무회귀 표 + 결정론 root-cause + 로그 검증 + 두-지표 before/after 표 + 역행 원인
- `deferred-items.md` — hold_window 캐시 버그 (HIGH, gap-closure) + s3 변동 관측
- 원자료 (Pod, git 밖): `/workspace/eval_out/phase27/after_sweep{,_warm}.log`, `/workspace/eval_out_after27/phase25/phase25_sweep_report{,_warm}.json`, `after_cache_isolate_{delete,verify}.json`

## Decisions Made

- **PASS + Pod 유지:** rollback 레버 불발동. fault drift = vision run 변동(27-02 관측 계보)이며 위양성 방향 회귀 0.
- **결정론 divergence = gap-closure 회부 (즉시 fix 아님):** hold_window 복원은 warm-path 채점 표면을 바꾸므로 자체 EVAL18 게이트 사이클 필수 — 27-09 범위 밖 + pre-existing (scope boundary). 회귀 방치가 아니라 신규 관측 버그의 정식 회부.
- **s3 이상치 = 관측 기록만:** 코드 무혐의 3중 근거 (warm/before 정상, fault 멤버 정상, 재시도 로그 0).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] File API orphan 업로드 누수 (이전 세션, 스모크 발견)**
- **Found during:** Task 2 스모크
- **Issue:** ref 세션 업로드 후 `files.get` 폴링 503 → graceful None 반환 시 이미 업로드된 파일을 아무도 delete 안 함 (20GB 사고 계보)
- **Fix:** `file_session.py` None 반환 전 best-effort delete + 테스트 2종
- **Commit:** `3894bc8`

### Discovered, Not Fixed (scope boundary)

**2. TechniqueCache hold_window 미복원 (pre-existing, phase 8)** — cold/warm 결정론 대조가 최초 관측. deferred-items.md #1 로 gap-closure 회부 (상세 root-cause + fix 방향 포함).

**3. Pod S3 다운로드 일시 변동** — deferred-items.md #2 관측 기록.

**Total deviations:** 1 auto-fixed + 2 deferred (pre-existing/환경)
**Impact on plan:** 게이트 판정 자체는 plan 의도대로 완수. scope creep 0.

## Issues Encountered

- **Cerebras 코치 1차 JSON 파손 재발 (cold 3건/warm 5건):** 기존 재시도/수치 폴백 규율로 진행 — 27-02/27-08 과 동일 양성 경로, 점수·verdict 무관. 조치 0.

## belle 실기기 수동 확인 항목 (27-VALIDATION Manual-Only — 배치 UAT 정책상 즉시 호출 아님, phase UAT 적립)

| 항목 | 확인 방법 |
|------|----------|
| zoom pending→done 전이 (D-06) | 결과 화면 진입 직후 확대카드 로딩 표시 → 수십 초 내(실측 median 7.7s) PNG 도착 |
| 팁 로테이션 (D-07) | 분석 대기 중 폴스포츠 팁 텍스트 로테이션 표시 |
| 진행률 전진 (D-02) | 로딩 진행률이 멈춤 없이 전진 (재배분 반영) |

## Known Stubs

None — 문서/판정 산출물만.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: cache-determinism | backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py:383-392 | TechniqueCache hit 시 hold_window 미복원 → 같은 영상 재분석에서 extension 측정 창 drift (pre-existing, gap-closure 회부 — deferred-items.md #1) |

## Next Phase Readiness

- **Phase gate 충족** → `/gsd-verify-work` 진행 가능 (belle 실기기 manual 항목은 상단 표 — 배치 UAT 적립).
- Pod 반환 상태: repo `3894bc8` clean, env 6종 박제 유지, /health 200, fixture 캐시 = warm sweep 재적재 상태 (다음 cold 실측 시 27-02 격리 절차 재사용).
- gap-closure 후보 1건 (hold_window) — 채점 정확도 직결, 우선 처리 권고.

---
*Phase: 27-1-gemini-analysis-speed-1min*
*Completed: 2026-07-08*

## Self-Check: PASSED

- 파일 3개 존재 (27-TIMING-AFTER.md 235줄 / 27-09-SUMMARY.md / deferred-items.md).
- 커밋 6개 존재 (87a9326 · af56fb2 · 3894bc8 · 0c4aa92 · 4711b61 · c9d8bed). 삭제 파일 0.
- acceptance grep (27-TIMING-AFTER.md): cacheHit=1 (≥1) / completedCalls=1 (≥1) / gemini_upload_prefetch_submit=2 (≥1) / PASS|FAIL=9 (≥1) / GEMINI_UPLOAD_PREFETCH|GEMINI_FANOUT_WORKERS=9 (≥2) / timingsMs|elapsed_ms=2 (key_link 패턴).
- PASS 판정 → rollback 불발동, Pod /health 200 유지 확인.
- STATE.md / ROADMAP.md 무접촉 (orchestrator 소관 준수).
