---
phase: 27-1-gemini-analysis-speed-1min
plan: 02
subsystem: infra
tags: [pod, eval, baseline, gemini, stage-timing, cold-run]

# Dependency graph
requires:
  - phase: 27-1-gemini-analysis-speed-1min
    provides: "27-01 stage-timing 계측 (_stage 11경계 + result.timingsMs) — 이 실측의 데이터 소스"
provides:
  - "27-TIMING-BEFORE.md — 최적화 착수 전 cold 단계별 타이밍 표 (EVAL18 6페어 양멤버 mode1, cacheHit=false 증빙, Pod/커밋 해시 박제)"
  - "레버 우선순위 실측 교정: Gemini vision 60% (veto 87s > coach 45s > recognizer 35s > scene 22s median) — 포즈 51s 추정은 과대(실측 20s)"
  - "27-RESEARCH Open Q1(미계상 45s = coach_dual) / Q2(업로드 4~5회 가정 = 실환경 확정) 답"
affects: [27-03, 27-04, 27-05, 27-06, 27-09, D-01]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "cold 격리 = fixture hash 한정 gemini_cache 문서 삭제 (PROMPT_VERSION bump 절대 금지 대안) — 삭제 내역 박제 + dry-run 재검증 0건"
    - "eval 하니스 read-only 관측 tee 확장 (vetoTelemetry.cacheHit / timingsMs / wallMs 리포트 수록)"

key-files:
  created:
    - .planning/phases/27-1-gemini-analysis-speed-1min/27-TIMING-BEFORE.md
  modified:
    - backend/evals/phase25/run_sweep.py

key-decisions:
  - "하니스 = evals/phase25/run_sweep.py (sweep_phase15.py 아님) — EVAL18 '페어' 관례(6동작 fault+correct 양멤버 mode1)와 일치하는 현행 하니스. sweep_phase15 keys 파일의 mode1 은 success 멤버만 있어 페어 형상 불일치"
  - "cold 증빙 수집을 위해 하니스에 관측 tee 3종 추가 (Rule 3) — 파이프라인 코드는 27-01 커밋과 byte-동일 유지"
  - "하니스 내장 pdshape 재실행의 cacheHit=true 는 결정론 체크 전용 — 타이밍 표본에서 명시 제외"

patterns-established:
  - "before/after 타이밍 대조 = 같은 조건의 cold run 끼리 (오래된 점수 baseline 과의 drift 는 pre-existing 으로 분리 기록)"

requirements-completed: [SPD-06]

# Metrics
duration: ~85min (sweep 벽시계 48.6min 포함)
completed: 2026-07-08
---

# Phase 27 Plan 02: Before Cold Baseline 실측 Summary

**27-01 계측 커밋을 Pod(s7gyvvlc6u7ktz)에 pin 하고 EVAL18 6페어 12멤버를 cold SERIAL 로 실측 — Gemini vision 이 wall 의 60%(veto_collect 단독 38%), 미계상 ~45s 의 정체는 coach_dual 로 확정, 포즈는 추정(51s)의 40%인 20s 에 불과함을 박제했다.**

## Performance

- **Duration:** ~85 min (sweep 48.6 min + 격리/검증)
- **Tasks:** 2 (Task 1 = checkpoint, belle "approved 6페어" 승인 후 재개)
- **Files created:** 1 / **modified:** 1

## Accomplishments

- **cold 격리 (T-27-03):** PROMPT_VERSION bump 0. Firestore `gemini_cache` 에서 fixture 12개 hash 한정 117건 삭제 (TechniqueCache 12 + VisionVetoCache 105) → dry-run 재검증 잔존 0. 프로덕션 사용자 영상 캐시 무접촉.
- **12멤버 SERIAL cold 실측:** 채점 10멤버 전원 `telemetry.cacheHit=false` + veto 4/4 콜 완료. climb 2멤버 = not_pole 게이트 (baseline known_gate_blocked 동일 — 누락 아님, 부분 stage 로그 박제).
- **27-TIMING-BEFORE.md (122줄):** 페어별 stage×elapsed_ms 표 12열, wall 합계 45.7분, env 스냅샷, cold 증빙, Pod/커밋 해시, 152s/197s 추정 대비 교정.
- **Open Q1 답:** 미계상 ~45s = coach_dual 36~67s (coach B 영상 업로드 #4 + generate + Cerebras 순차) + hook ~14s. **Open Q2 답:** 전 토글 ON — 학생 영상 업로드 4~5회 가정 실환경 확정 (모델: veto/coach/hook=3.1-pro-preview, scene=3.5-flash, recognizer=2.5-pro 박제 예외).
- **레버 우선순위 교정:** veto_collect(87s median, 38%) > coach_dual(45s, 20%) > recognizer(35s) > scene_finder(22s) > fault_zoom(16s) > pose 전체(20s, 9%). 27-03(핸들 세션)/27-04(겹치기)/27-05(coach 병렬) 기대치 상향, fault_zoom(27-06) 은 유효하되 후순위.

## Task Commits

1. **Task 2 (하니스 관측 tee):** `c398cf1` (chore) — vetoTelemetry.cacheHit/timingsMs/wallMs 리포트 수록 + basicConfig(INFO) stage_timing 로그 방출. **Pod pin 커밋이기도 함** (파이프라인 코드 = 27-01 `a67356e`/`bab4666` byte-동일).
2. **Task 2 (실측 박제):** `e8c3abc` (docs) — 27-TIMING-BEFORE.md

## Files Created/Modified

- `.planning/phases/27-1-gemini-analysis-speed-1min/27-TIMING-BEFORE.md` — before 타이밍 표 정본
- `backend/evals/phase25/run_sweep.py` — read-only 관측 tee 3종 (collect 인자/채점 경로 무접촉)

## Decisions Made

- **하니스 선택:** plan 의 `sweep_phase15.py --pair-sequential` 대신 `evals/phase25/run_sweep.py` — EVAL18 baseline 형상(6동작 fault+correct 양멤버 mode1)과 일치하는 현행 관례 (phase24/25 계보). sweep_phase15 의 mode1 항목은 success 멤버만 포함해 "페어" 실측 불가.
- **pin 해시 = c398cf1:** 27-01 커밋(bab4666) + eval 하니스 tee 만의 delta. 파이프라인/채점 코드 diff 0 — "실측 중 코드 변경 0" 의미론 충족 (verification 절의 pin 의도 = 이후 wave 최적화 코드 차단).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 하니스가 cold 증빙(cacheHit)·timingsMs·벽시계를 리포트에 미수록**
- **Found during:** Task 2 착수 전 read_first (run_sweep.py 정독)
- **Issue:** acceptance criteria 가 요구하는 `telemetry.cacheHit=false` per-run 증빙과 `result.timingsMs` 가 기존 리포트에 없음. 또한 27-01 의 stage_timing `log.info` 는 로깅 핸들러 미구성 시 lastResort(WARNING) 에 걸러져 로그 라인이 방출되지 않음.
- **Fix:** run_sweep.py 에 read-only 관측 tee 추가 — collectObservation.vetoTelemetry(cacheHit/cacheKey/calls/durationMs), 멤버 record 에 timingsMs/wallMs, main() 에 basicConfig(INFO). collect 인자·채점 경로 무접촉 (기존 tee 불변식 준수).
- **Files modified:** backend/evals/phase25/run_sweep.py
- **Verification:** sweep 리포트에 12멤버 cacheHit/timingsMs 수록 + stage_timing 로그 146라인 방출 확인
- **Commit:** c398cf1

**2. [컨텍스트 교정] plan 명기 Pod(svn31pzja7uay0) 소멸 — 현행 Pod 로 실행**
- **Found during:** Task 2 step 1
- **Issue:** plan/checkpoint 텍스트의 Pod 는 재생성 전 구세대. 오케스트레이터 live facts 로 현행 = `s7gyvvlc6u7ktz` (proxy/Lambda env 동기화 완료 상태).
- **Fix:** 현행 Pod 에서 실행, Pod ID 를 27-TIMING-BEFORE.md 에 박제. 코드 변경 0.

---

**Total deviations:** 1 auto-fixed (blocking) + 1 컨텍스트 교정
**Impact on plan:** 측정 신뢰도 확보 목적의 관측 도구 추가만 — 채점/파이프라인 무접촉, scope creep 0.

## Issues Encountered

- **coach writer Cerebras 1차 응답 JSON 파손 (power-spin success):** 기존 재시도 규율로 attempt 2 성공 — 크래시 아님, 로그에 Traceback 만 남는 정상 복구 경로. 조치 0.
- **점수 drift 관측 (27-09 대조 시 주의):** kip-up fault=100 (phase25 sweep 47), power-spin success=80 (과거 100) — Gemini 비전 짚기 run 간 변동으로 보임 (이번 run pointed=[]). 본 계측 코드는 점수 무접촉(27-01 무회귀 검증 완료)이므로 pre-existing 변동. **27-09 는 같은 조건의 이 run 을 before 로 대조할 것** (27-TIMING-BEFORE.md 에 명기).

## Known Stubs

None — 문서/eval 관측 산출물만. UI/데이터 배선 없음.

## User Setup Required

None — belle 승인(Task 1)으로 완료. Gemini 크레딧 소모: 12멤버 cold (veto 4콜×10 + recognizer/scene/coach/hook) — 승인 범위 내.

## Next Phase Readiness

- 27-09 D-01 게이트의 before 표 확보 — 동일 페어·동일 단계 키(timingsMs)로 after 와 기계 대조 가능 (하니스가 이제 timingsMs 를 리포트에 수록).
- wave 3~6 레버 기대치 실측 교정 완료: 최대 수확 = veto_collect(업로드+4콜 순차) → 27-03/27-04/27-05 가 순서대로 지배 구간을 공략.
- Pod 반환 상태: repo = origin/main `c398cf1` (파이프라인 = 27-01 코드), 서버 재기동·/health 200, working tree clean.

---
*Phase: 27-1-gemini-analysis-speed-1min*
*Completed: 2026-07-08*

## Self-Check: PASSED

- 파일 3개 전부 존재 (27-TIMING-BEFORE.md / 27-02-SUMMARY.md / run_sweep.py tee).
- 커밋 2개 전부 존재 (c398cf1 chore-tee / e8c3abc docs-baseline).
- acceptance: 27-TIMING-BEFORE.md 122줄 (≥30), grep cacheHit=3 / elapsed_ms·timingsMs=3 / commit=1 (전부 ≥1).
- 삭제 파일 0, STATE.md/ROADMAP.md 무접촉.
