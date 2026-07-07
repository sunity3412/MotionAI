---
phase: 27-1-gemini-analysis-speed-1min
plan: 01
subsystem: infra
tags: [performance, instrumentation, gemini, pipeline, stage-timing, testing]

# Dependency graph
requires:
  - phase: 17-gemini-4-areas
    provides: "pipeline _process 단계 골격 + Gemini coach/scene/keypoint 배선 (계측 대상 경계)"
  - phase: 26
    provides: "3-way lockstep 계약 갱신 선례 (learningOptIn — analysis.ts/models.py/contract.md 동시 갱신)"
provides:
  - "_stage contextmanager + _process 단계 경계 11곳 계측 (result.timingsMs flat dict)"
  - "timingsMs 3-way lockstep 계약 (analysis.ts AnalysisResult.timingsMs? + contract.md timingsMs 절, backend/audit 전용)"
  - "재사용 fake genai fixture (backend/tests/gemini/fake_genai.py — upload/get/delete 카운터 + fan-out 순서 결정론)"
affects: [27-02, 27-03, 27-04, 27-05, D-01, D-02]

# Tech tracking
tech-stack:
  added: []  # 신규 패키지 0 — stdlib contextlib/time 만
  patterns:
    - "stage-timing: contextmanager try/finally 로 elapsed(ms) 누적 + %-lazy 구조 로그, 기존 로직 이동 0 (감싸기만)"
    - "재사용 test fixture 모듈: test_client.py stub 패턴을 tests/gemini/fake_genai.py 로 추출 (본체 무수정)"

key-files:
  created:
    - backend/tests/test_stage_timing.py
    - backend/tests/gemini/fake_genai.py
  modified:
    - backend/functions/pipeline/app.py
    - app/src/types/analysis.ts
    - docs/contract.md
    - backend/tests/test_pipeline_gemini_integration.py
    - backend/tests/pipeline/test_pipeline_phase8.py
    - backend/tests/pipeline/test_pipeline_phase9.py

key-decisions:
  - "firestore_complete 단계는 complete_analysis 호출 자체를 감싸 저장 dict 에 미포함 — 로그 라인으로만 방출 (저장 재귀 방지)"
  - "s3_download/frame_extract/rtmw 는 _extract_video_analysis_inputs 안에서 계측 — timings_ms optional kwarg 로 helper 시그니처 확장 (단일 caller)"
  - "timingsMs 는 암묵 result 필드가 아니라 analysis.ts + contract.md lockstep 계약 (외부 리뷰 MEDIUM-1)"

patterns-established:
  - "stage 계측 = _stage(timings_ms, analysis_id, name) 로 감싸기만, 단계 키는 자유 dict (status enum 아님, 추가는 비파괴)"
  - "fake genai fixture = FakeFiles(delete_calls/deleted_names) + FakeModels(delay_by_index) 로 누수·순서 검증 재사용"

requirements-completed: [SPD-01]

# Metrics
duration: ~40min
completed: 2026-07-08
---

# Phase 27 Plan 01: Stage-Timing 계측 + fake genai fixture Summary

**mode1 분석 경로의 단계 경계 11곳을 `_stage` contextmanager 로 계측해 `result.timingsMs` flat dict 로 저장(analysis.ts/contract.md 계약 lockstep)하고, 후속 wave 가 import 만으로 재사용할 fake genai fixture(업로드/삭제 카운터 + fan-out 순서 결정론)를 신설했다.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2
- **Files created:** 2 / **modified:** 6

## Accomplishments
- `_stage` 순수 contextmanager 신설 — `time.monotonic` try/finally 로 elapsed(ms) 누적 + `stage_timing analysis_id=%s stage=%s elapsed_ms=%d` %-lazy 구조 로그 (시크릿/바이트 로그 0).
- `_process` 단계 경계 11곳 계측: `s3_download`/`frame_extract`/`rtmw`(helper 내부) + `scene_finder`/`recognizer`/`ref_fetch_download`/`dtw_scoring`/`veto_collect`/`coach_dual`/`assemble_misc`/`fault_zoom` + `firestore_complete`(저장 제외, 로그만). 기존 분석 로직 이동 0 — `with` 감싸기만.
- `result["timingsMs"] = timings_ms` (complete_analysis 직전) — flat `dict[str,int]`, [[firestore-nested-array-flat]] 정합.
- 계약 lockstep: `analysis.ts AnalysisResult.timingsMs?: Record<string, number>` + `docs/contract.md` timingsMs 절 (backend/audit 전용·사용자 비노출 명기, 단계 키는 예시·비고정). 암묵 result 필드 금지(외부 리뷰 MEDIUM-1).
- `backend/tests/gemini/fake_genai.py` — `FakeFile`/`FakeFiles`(upload/get/delete 카운터 + uploaded_names/deleted_names)/`FakeModels`(delay_by_index fan-out 순서)/`FakeClient`/`patch_genai`. test_client.py:38-100 패턴 확장, 본체 무수정.

## Task Commits

1. **Task 1 (RED): 실패 테스트** — `f063cea` (test)
2. **Task 1 (GREEN): 계측 + timingsMs + 계약 lockstep** — `b25a038` (feat)
3. **Task 2: fake genai fixture** — `58270c6` (test)

_TDD Task 1 = test(RED) → feat(GREEN). REFACTOR 불필요 (계측은 감싸기만이라 정리할 잔여 0)._

## Files Created/Modified
- `backend/functions/pipeline/app.py` — `_stage` helper + `_process` 11 단계 계측 + `_extract_video_analysis_inputs` timings_ms/analysis_id kwargs + result.timingsMs 부착
- `backend/tests/test_stage_timing.py` — `_stage` 계약 3건 (int ms 누적 + 로그 라인 / 예외 전파 / flat scalar 검증)
- `backend/tests/gemini/fake_genai.py` — 재사용 fake genai stub
- `app/src/types/analysis.ts` — `AnalysisResult.timingsMs?` optional 필드
- `docs/contract.md` — §4 timingsMs 절 (flat dict, backend/audit 전용, 단계 키 예시)
- `backend/tests/{test_pipeline_gemini_integration, pipeline/test_pipeline_phase8, pipeline/test_pipeline_phase9}.py` — helper stub `_impl` 시그니처에 timings_ms/analysis_id kwargs 추가 (Rule 3)

## Decisions Made
- **firestore_complete 저장 제외:** `firestore_complete` 단계는 `complete_analysis` 호출 자체를 감싸므로, timings_ms 에 그 키가 기록되는 시점(with finally)이 complete_analysis 직렬화보다 뒤 → 저장 dict 에는 미포함(로그로만). 저장 재귀/역참조 방지 위한 의도적 설계 (주석 박제).
- **helper 내부 3단계 계측:** s3_download/frame_extract/rtmw 는 `_extract_video_analysis_inputs` 안에 있어, `timings_ms`/`analysis_id` optional kwarg 로 helper 를 확장해 감쌌다 (단일 caller — 시그니처 확장 안전).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] helper 시그니처 변경에 따른 기존 테스트 stub kwargs 정합**
- **Found during:** Task 1 (계측 배선 검증)
- **Issue:** `_extract_video_analysis_inputs` 에 `timings_ms`/`analysis_id` kwargs 를 추가하니, `_process` 를 통해 이 helper 를 monkeypatch stub 으로 교체하는 기존 테스트 3파일(gemini_integration, pipeline/phase8, pipeline/phase9)의 `_impl(bucket, key, default_pole, *, keep_local_video=False)` stub 이 `unexpected keyword argument 'timings_ms'` TypeError 로 실패.
- **Fix:** 세 stub 의 `_impl` 시그니처에 `timings_ms=None, analysis_id=""` kwargs 추가 (stub 은 무시). 로직 무변경 — 시그니처 정합만.
- **Files modified:** backend/tests/test_pipeline_gemini_integration.py, backend/tests/pipeline/test_pipeline_phase8.py, backend/tests/pipeline/test_pipeline_phase9.py
- **Verification:** 세 파일 격리 실행 20 passed. base vs mine 실패 목록 IDENTICAL (신규 실패 0).
- **Committed in:** `b25a038` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** helper 시그니처 확장의 필연적 정합. scope creep 0.

## Issues Encountered
- **테스트 격리 flakiness(pre-existing):** phase06/geminic/geminid 파이프라인 통합 테스트를 넓은 세트로 함께 돌리면 module-global 싱글턴(_RECOGNIZER/adapters/env) 오염으로 순서 의존 실패가 발생([[pipeline-not-concurrency-safe-eval-serial]]). base app.py 와 내 app.py 를 동일 세트로 대조한 실패 목록이 IDENTICAL 임을 확인 — 본 plan 이 유발한 신규 실패 0. 격리 실행 시 전부 green.
- 본 worktree 에 node_modules 부재 → app typecheck 는 main checkout 의 node_modules 심볼릭 링크로 실행 (exit 0, 링크는 실행 후 제거). tracked 파일 무변경.

## User Setup Required
None - 외부 서비스 설정 불필요 (신규 패키지 0, OTA 무관 — 타입/문서만).

## Next Phase Readiness
- 27-02~05 최적화 wave 가 이 계측(timingsMs)으로 D-01 before/after 표 + D-02 진행률 재배분 실측을 확보.
- 27-03(세션 누수 0) / 27-05(fan-out 결정론) 테스트가 `tests/gemini/fake_genai.py` 를 import 로 재사용 가능.
- 계측 코드는 감싸기만이라 분석 결과/점수 무접촉 — 정확도 무회귀.

---
*Phase: 27-1-gemini-analysis-speed-1min*
*Completed: 2026-07-08*

## Self-Check: PASSED

- 생성 파일 6개 전부 존재 (test_stage_timing.py / fake_genai.py / app.py / analysis.ts / contract.md / SUMMARY.md).
- 커밋 4개 전부 존재 (f063cea test-RED / b25a038 feat / 58270c6 fake genai / 4ca2f7b docs).
- 검증: `tests/test_stage_timing.py tests/gemini/` 120 passed, `_stage(timings_ms` 15개 (≥10), timingsMs 계약 3곳(app.py 6 / analysis.ts 2 / contract.md 3), app typecheck exit 0.
