---
phase: 27-1-gemini-analysis-speed-1min
plan: 08
subsystem: infra
tags: [pod, gemini, flash, eval, d-05, conditional]

# Dependency graph
requires:
  - phase: 27-1-gemini-analysis-speed-1min
    provides: "27-02 wave 2 Pro cold run (같은 코드 6eb73b5, 같은 하니스) — Flash 변인 격리의 대조 기준"
provides:
  - "27-FLASH-DECISION.md — moment extractor Pro→Flash D-05 게이트 통과 (EVAL18 12멤버 record 레벨 diff 0) + recognizer 단계 median 8.5s 절감 실측"
  - "반영 제약 발견: GEMINI_MODEL env는 veto scorer와 공유 — env 한 줄 반영 불가, 전용 키 1줄(GEMINI_MOMENT_MODEL) 후속 권고"
  - "TechniqueCache model 라벨 = 상수 문자열 발견 (T-27-25 전제 교정) — fixture 캐시 재삭제로 완화 완료"
affects: [27-09, D-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "공유 env 키의 모듈별 스코핑 = import 순서 wrapper (env set → 대상 모듈 import → env del → 비대상 모듈 import) — eval 전용, 프로덕션 부적합"
    - "Flash A/B는 대조 리포트 덮어쓰기 방지 위해 EVAL_OUT_DIR 분리 (/workspace/eval_out_flash27)"

key-files:
  created:
    - .planning/phases/27-1-gemini-analysis-speed-1min/27-FLASH-DECISION.md
  modified: []

key-decisions:
  - "판정 = 채택 (D-05 게이트 통과) + 프로덕션 반영 보류 — GEMINI_MODEL 공유로 env 반영 시 veto까지 flip (belle 승인 범위·veto 기본 보류 위반). 반영은 전용 env 키 1줄과 함께 27-09/후속으로 이관"
  - "coach B(2순위) 미실행 — belle 승인 = 1순위만"
  - "사후 fixture 캐시 재삭제 — TechniqueCache model 라벨이 상수라 Flash 산출물이 Pro lookup에 hit되는 구조 → 22건 재삭제로 잔존 0"

requirements-completed: [SPD-07]

# Metrics
duration: ~75min (sweep 벽시계 ~46min 포함)
completed: 2026-07-08
---

# Phase 27 Plan 08: Pro→Flash 조건부 전환 실험 Summary

**moment extractor를 import 순서 스코핑 wrapper로 Flash 단독 전환해 EVAL18 12멤버 cold 대조를 돌린 결과 wave 2 Pro run과 record 레벨 완전 동일(diff 0) + recognizer 단계 median 8.5s 절감 — D-05 게이트 통과. 단 `GEMINI_MODEL` env가 veto와 공유되어 env 한 줄 반영이 불가능함을 발견, 프로덕션 반영은 전용 키 1줄 후속으로 이관하고 Pod env는 원상 유지.**

## Performance

- **Duration:** ~75 min (sweep 03:16~04:02 UTC 포함)
- **Tasks:** 2 (Task 1 = checkpoint, belle "approved 1순위만" 수신 후 재개)
- **Files created:** 1 (+ pod-side wrapper/아티팩트, git 밖)

## Accomplishments

- **스코프 격리 성공:** `GEMINI_MODEL`이 moment extractor(`gemini_moment_extractor.py:58`)와 veto scorer(`gemini_vision_scorer.py:102`) **공유 env**임을 발견 — 전역 export 금지. wrapper(`/workspace/phase27_flash_moment_sweep.py`)의 import 순서 스코핑으로 extractor=flash / veto=pro 단언 통과. httpx 집계로 기계 증빙 (pro 62콜 / flash 25콜).
- **D-05 게이트 통과:** 12멤버 status/overallScore/errorCode/activatedCriteria/faultRecords + 6페어 verdict 전부 wave 2 Pro run과 동일 (diff 0). run 간 drift(kip-up 100, power-spin success 80)까지 그대로 재현 — Flash의 채점 표면 영향 0의 가장 강한 증거. phase18 정본 `assert_baseline.py` PASS + verdict 클래스 전 페어 일치.
- **레이턴시:** recognizer 단계 절감 median 8.46s / mean 9.08s / range 4.7~15.1s (양쪽 다 최적화 전 코드 — 27-09 배포 후 재실측 필요 명기).
- **cold 격리 + 원복:** 실행 전 fixture 한정 gemini_cache 22건 삭제(잔존 0) → 10멤버 cacheHit=false + veto 4/4 → 실행 후 22건 재삭제(잔존 0). 프로덕션 사용자 캐시 무접촉, PROMPT_VERSION bump 0.
- **Pod 원상:** repo `6eb73b5` pin 유지(wave 3~6 미배포), start_server.sh 무변경(GEMINI_MODEL 0건), 서버 무재시작(PID 9108 유지), /health 200.

## Task Commits

1. **Task 2 (판정 박제):** `8e69505` (docs) — 27-FLASH-DECISION.md (100줄, 게이트 증빙 + 반영 제약 + 캐시 완화)

## Files Created/Modified

- `.planning/phases/27-1-gemini-analysis-speed-1min/27-FLASH-DECISION.md` — 후보별 판정 + 기계 근거 정본
- (pod, git 밖) `/workspace/phase27_flash_moment_sweep.py`, `/workspace/eval_out_flash27/phase25/*.json`, `/workspace/eval_out/phase27/flash_sweep.log`, `flash_cache_{isolate,restore}_{delete,verify}.json`

## Decisions Made

- **채택 + 반영 보류:** 게이트는 통과했으나 env 반영 수단이 veto 스코프를 침범 — 원상 유지가 D-01(무회귀)·belle 승인 범위 양쪽에 안전. 권고: `GEMINI_MOMENT_MODEL` 전용 키 1줄(기존 `GEMINI_MODEL` fallback) + start_server.sh export, 27-09 after-sweep 게이트와 같은 사이클로 검증.
- **EVAL_OUT_DIR 분리:** flash run 산출을 `/workspace/eval_out_flash27`로 — wave 2 리포트(대조 원본) 덮어쓰기 방지.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `GEMINI_MODEL` env가 moment extractor와 veto scorer에 공유 — 전역 override 불가**
- **Found during:** Task 2 step 1 (env 키 확정)
- **Issue:** plan 전제 "`gemini/config.py`의 `GEMINI_*_MODEL` 패턴"과 달리 extractor는 config.py를 쓰지 않고 `GEMINI_MODEL`을 직접 읽으며, `gemini_vision_scorer.py:102`도 같은 키를 읽는다. 전역 export = veto까지 Flash flip (명시 제외 대상 침범).
- **Fix:** import 순서 스코핑 wrapper (pod-side eval 전용, 파이프라인 코드 무접촉, 신규 env 발명 0) + 런타임 단언 + httpx 모델 집계로 스코프 증빙.
- **Files modified:** (pod, git 밖) `/workspace/phase27_flash_moment_sweep.py`
- **Verification:** `[flash-scope] extractor=gemini-3.5-flash veto=gemini-3.1-pro-preview (scoped OK)` + 로그 모델 집계
- **Commit:** 8e69505 (문서 박제)

**2. [Rule 2 - 완화] TechniqueCache "model명 네임스페이스" 전제 부정확 → 사후 캐시 재삭제**
- **Found during:** Task 2 read_first (technique_cache.py / gemini_technique_recognizer.py 정독)
- **Issue:** T-27-25 mitigation 전제("키에 model명 포함 → 자동 분리")와 달리 model 라벨은 상수 문자열(`gemini_technique_recognizer.py:220`) — Flash 산출 moments가 Pro lookup에 hit 가능한 구조 (fixture 한정, 프로덕션은 hash가 달라 무접촉).
- **Fix:** sweep 종료 후 fixture 한정 22건 재삭제 → 잔존 0 (운영적 완화). 전용 env 키 반영 시 상수 라벨의 실모델 문자열화 권고를 DECISION에 박제.
- **Verification:** `flash_cache_restore_verify.json` residual 0

---

**Total deviations:** 2 auto-fixed (blocking 1 + 완화 1)
**Impact on plan:** 실험 자체는 plan 의도대로 완수. 반영 절차(start_server.sh env 한 줄)만 구조적 제약으로 보류 — scope creep 0, 프로덕션 무접촉.

## Issues Encountered

- **Cerebras 코치 1차 응답 JSON 파손 (재발):** 기존 재시도/폴백 규율로 정상 복구 — 27-02와 동일한 양성 경로, 점수·verdict 무관. 조치 0.
- **모니터 오탐:** 위 Traceback이 로그 감시 조건에 걸려 조기 알림 — 프로세스 생존 확인 후 ALLDONE 전용 조건으로 재감시.

## Known Stubs

None — 문서/eval 산출물만. UI/데이터 배선 없음.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: cache-namespace | backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py:220 | TechniqueCache model 라벨이 상수 — 모델 A/B 실험 시 네임스페이스 미분리 (이번엔 운영적 완화, 코드 fix는 전용 env 키와 함께 권고) |

## User Setup Required

None — belle 승인(Task 1)으로 완료. Gemini 크레딧 소모: EVAL18 sweep 1회 (승인 범위 내, coach B 미실행으로 추가 소모 0).

## Next Phase Readiness

- 27-09 배포 게이트에 전달: (1) Flash 등가 증명은 6eb73b5 코드 기준 — wave 3~6 배포 후 반영하려면 전용 env 키 1줄 + after-sweep 게이트 같은 사이클 검증. (2) fixture 캐시는 cold 상태로 원복돼 있음 (27-09 cold 격리 그대로 재사용 가능).
- Pod 반환 상태: repo `6eb73b5` clean, 서버 Pro 구성 그대로 (무재시작), /health 200, 분석 in-flight 0.

---
*Phase: 27-1-gemini-analysis-speed-1min*
*Completed: 2026-07-08*

## Self-Check: PASSED

- 파일 2개 존재 (27-FLASH-DECISION.md 100줄 / 27-08-SUMMARY.md).
- 커밋 존재 (8e69505 docs-decision). 삭제 파일 0.
- acceptance: grep gemini-3.5-flash=5 (≥1) / gemini-2.5=0 / 채택·기각 라인=4 (≥1). 기각-경로 증빙(env 무변경 + /health 200) + 캐시 원복(잔존 0) 파일 내 포함.
- STATE.md / ROADMAP.md / app/ 무접촉 (orchestrator 소관 준수).
