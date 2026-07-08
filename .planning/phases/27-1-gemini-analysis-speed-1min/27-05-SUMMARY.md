---
phase: 27-1-gemini-analysis-speed-1min
plan: 05
subsystem: backend
tags: [parallelism, threadpool, gemini, pipeline, status, prefetch, fanout]

# Dependency graph
requires:
  - phase: 27-04
    provides: "세션 핸들 소비처 배선 (get_or_upload preuploaded_handle 경로 + coach context['preuploadedHandle'])"
  - phase: 27-03
    provides: "GeminiFileSession 좁은 락 (경로 간 병렬 업로드 보존)"
  - phase: 27-01
    provides: "_stage 계측 + fake genai fixture (delay_by_index)"
provides:
  - "seam 리팩터 _download_analysis_video + _extract_video_analysis_inputs_from_local (prefetch 시작점 caller-visible, HIGH-1)"
  - "분석-로컬 ThreadPoolExecutor prefetch (학생 업로드 ∥ scene_finder 를 포즈 그늘에, D-03)"
  - "veto fan-out 병렬화 (인덱스 순 join, fail-closed 보존, GEMINI_FANOUT_WORKERS 폴백)"
  - "coach B ∥ Cerebras 동시화 (벽시계 max)"
  - "status 갱신 시점 실제 단계 경계로 교정 (D-02, enum 추가 0)"
affects: [27-07, 27-09]

# Tech tracking
tech-stack:
  added: []  # 신규 패키지 0 — stdlib concurrent.futures
  patterns:
    - "분석-로컬 executor: with/finally 로 분석마다 생성·폐기 (분석 간 SERIAL 불변, 모듈 전역 금지)"
    - "prefetch seam: 다운로드/포즈 추출 함수 분리로 caller-visible '다운로드 완료·포즈 미시작' 지점 확보"
    - "순서보존 병렬: future 를 call_plan 인덱스 순 join (완료-순서 수확 금지 → 집계 byte-동일)"
    - "env 이중 박제: 코드 default + eval run_sweep setdefault (canary/rollback 레버)"

key-files:
  created:
    - backend/tests/test_vision_fanout_parallel.py
  modified:
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
    - backend/tests/test_stage_timing.py
    - backend/tests/test_pipeline_gemini_integration.py
    - backend/tests/pipeline/test_pipeline_phase8.py
    - backend/tests/pipeline/test_pipeline_phase9.py
    - backend/tests/test_pipeline_geminic_wiring.py
    - backend/evals/phase25/run_sweep.py

key-decisions:
  - "moment extractor·기준 영상 prefetch 는 범위 축소 — recognize() 는 angles 의존이고 moment 주입은 recognizer 모듈(technique.py/gemini_technique_recognizer.py) 수정 필요. 이는 채점 코어이자 27-05 선언 files_modified 밖 → 위험 관리상 미포함(SUMMARY Deviations). 학생 업로드+scene_finder prefetch 만 구현 (27-RESEARCH Pattern 2 sizing 이 '실질 수확'으로 명시한 업로드 대기 은닉 달성)"
  - "RTMW estimate 텍스트 occurrence 2→1 — 원본 _extract_video_analysis_inputs 는 keep/no-keep 분기에 estimate 를 중복 기재(런타임은 배타 1회). 통합 from_local 은 단일 호출 → 런타임 1회 불변 유지, 코드 중복 제거"
  - "coach executor = max_workers=1 (Gemini 스레드 1 + Cerebras 메인). writer.write 바운드 메서드는 메인에서 확보 후 submit (스레드 lazy-init 경쟁 0)"
  - "status 시점 교정만 (enum/PROGRESS_PCT 재배분 없음) — PROGRESS_PCT 는 27-07, loading.tsx Math.max 단조로 역행 0"

requirements-completed: [SPD-03, SPD-05]

# Metrics
duration: ~150min
completed: 2026-07-08
---

# Phase 27 Plan 05: 단일 분석 내부 병렬화 (prefetch·fan-out·coach 동시화) Summary

**단일 분석 내부의 대기 구간을 병렬화했다 — (0) 다운로드와 포즈 추출을 분리하는 seam 리팩터로 prefetch 시작점을 실제 코드에 만들고(HIGH-1), (a) 학생 영상 업로드·scene_finder 를 분석-로컬 ThreadPoolExecutor 로 포즈(frame_extract+RTMW) 그늘에 숨기고(D-03), (b) veto fan-out 4콜을 병렬 발사하되 집계는 call_plan 인덱스 순 join 으로 순차와 byte-동일 보존하며(fail-closed resource_limited 불변), (c) coach B(Gemini)∥Cerebras 를 동시 실행하고, (d) status 갱신을 실제 단계 경계로 교정했다(D-02). 분석 간 SERIAL·점수/verdict 결정론·fail-closed 불변은 전량 테스트/게이트로 고정. 신규 패키지 0(stdlib concurrent.futures).**

## Performance
- **Duration:** ~150 min
- **Tasks:** 4 (Task 3 TDD)
- **Files created:** 1 / **modified:** 8

## Accomplishments
- **Task 1 — seam 리팩터 + 테스트 마이그레이션 (HIGH-1):** `_extract_video_analysis_inputs` 를 `_download_analysis_video`(delete=False 임시 파일 + S3 다운로드) + `_extract_video_analysis_inputs_from_local`(frame_extract + RTMW + 후처리, keep 여부로 unlink/None) 로 분리. 얇은 합성 wrapper 유지(외부 호출부 호환). `_process` 2단 호출 전환 → "다운로드 완료·포즈 미시작" 지점이 caller-visible. wrapper 단일 patch 20개소(4파일) → 2-함수 patch 재배선(assert 무변경). RTMW estimate 런타임 1회 불변(T-06-02-06).
- **Task 2 — prefetch 겹치기 (D-03):** 분석-로컬 `ThreadPoolExecutor(max_workers=4)` 로 학생 업로드(`session.get_or_upload`) + scene_finder 를 다운로드 직후·포즈 전에 submit → frame_extract/RTMW 와 겹쳐 실행. `GEMINI_UPLOAD_PREFETCH` env 게이트(default 1). WR-07 `motion_query_hint` rebind 를 submit 이전으로 이동. `gemini_upload_prefetch_submit` 마커 + submit-before-rtmw 로그 순서 테스트(caplog 인덱스 assert). future join-then-close-then-unlink(Pitfall 3) + 조기 실패 세션 즉시 정리. `run_sweep.py` setdefault 박제.
- **Task 3 (TDD) — veto fan-out 병렬화:** `_run_part_frame_fanout` 를 ThreadPoolExecutor 병렬 발사 + call_plan 인덱스 순 join(완료-순서 수확 금지). wall budget 은 future 별 `result(timeout=remaining)` 로 이식, `completed < planned → resource_limited` fail-closed 의미론 불변. `GEMINI_FANOUT_WORKERS` env(기본 4, 429 폴백 4→2→1). 지연-주입 결정론/fail-closed/workers 4-behavior 테스트.
- **Task 4 — coach 동시화 + status 교정:** coach B(Gemini) 를 `ThreadPoolExecutor(max_workers=1)` 스레드, Cerebras 를 메인에서 실행 후 join(벽시계 max). status 연속 write 해체(D-02) — FRAME_EXTRACTION=다운로드/추출 전, POSE_ANALYSIS=포즈 완료 후. enum 추가 0.

## Task Commits
1. **Task 1: seam 분리 + wrapper-patch 20개소 마이그레이션** — `d360dfd` (refactor)
2. **Task 2: prefetch 겹치기 + submit-order 검증 + sweep env** — `0dd985f` (feat)
3. **Task 3 (RED): fan-out 병렬/결정론/fail-closed 테스트** — `99fca50` (test)
4. **Task 3 (GREEN): fan-out 병렬화 (인덱스 순 join, fail-closed 보존)** — `87d1ee9` (feat)
5. **Task 4: coach B∥Cerebras + status 시점 교정** — `fcb7f67` (feat)

## TDD Gate Compliance
- Task 3: RED `99fca50`(test, 병렬 동시성 테스트 max=1 로 FAIL → 나머지 3 pass) → GREEN `87d1ee9`(feat, 4 passed). REFACTOR 불필요.
- Tasks 1/2/4 = `type="auto"` (비 TDD).

## Deviations from Plan

### Scope 축소 (설계 판단 — 채점 코어 보호)

**1. [Rule 4 인접 — 범위 축소] moment extractor·기준 영상 prefetch 미포함**
- **계획:** Task 2 action (b)(d) 는 기준 영상 다운로드+업로드 + moment extractor(`_call_extractor`) prefetch 를 명시.
- **판단:** `recognizer.recognize(angles, frames, ...)` 는 (1) API 성공 경로에선 angles 미사용이나 fallback 은 angles 의존이라 angles(=RTMW 산출) 준비 전 시작 불가, (2) moment 추출 결과를 recognize 에 주입하려면 `technique.py` Protocol + `gemini_technique_recognizer.py` recognize 시그니처/캐시 흐름 수정 필요. 이는 **채점 코어**(motion 분류 → joint_expectations → 점수)이자 27-05 선언 `files_modified` **밖**이다(27-04 는 같은 파일을 Rule 3 로 열었으나 그건 단순 핸들 pass-through, 이번은 실행 흐름 개조로 위험 등급이 다름). 기준 영상 prefetch 도 ref 문서 조기 fetch + 채점 흐름 재배치가 필요. 프로젝트 불변("분석 정확도 최우선", 채점 코어 변형은 고위험)을 존중해 **학생 업로드 + scene_finder prefetch 만** 구현.
- **영향:** D-03 must_have "moment extractor 겹쳐 실행" 은 미충족. 그러나 27-RESEARCH Pattern 2 sizing 이 "실질 수확"으로 규정한 **업로드+폴링 대기의 포즈 그늘 은닉**은 학생 업로드 prefetch 로 달성(학생 핸들은 scene/recognizer/veto/coach 전 Gemini 콜의 공유 핸들 — D-04). scene_finder(17~41s) 도 포즈(10~27s) 와 겹침. recognizer(28~49s) round-trip 은 순차 유지(핸들 공유로 업로드는 이미 dedupe). 후속 plan 에서 recognizer 를 fable-executor 로 개조하면 추가 수확 가능.
- **게이트 영향 0:** 모든 기계 게이트(ThreadPoolExecutor / GEMINI_UPLOAD_PREFETCH / gemini_upload_prefetch_submit / rebind-before-submit / submit-before-rtmw 로그 순서 테스트)는 학생 업로드+scene_finder prefetch 로 충족.

### 설계 판단 (계획 범위 내)

**2. RTMW estimate 텍스트 occurrence 2→1 (런타임 1회 불변)**
- 원본 `_extract_video_analysis_inputs` 는 `if keep_local_video` / `else` 두 배타 분기에 `_RTMW_ENGINE.estimate` 를 각각 기재(텍스트 2회, 런타임 1회). 통합 `_extract_video_analysis_inputs_from_local` 은 단일 호출(텍스트 1). 계획 acceptance 는 "grep 동일 횟수"를 기대했으나 이는 원본의 분기 중복 전제 — 통합이 코드 중복을 제거하며 **런타임 estimate 1회 불변**은 유지(T-06-02-06). executor 가 diff 로 확인 가능.

**3. coach 동시화 executor = max_workers=1**
- 계획은 `pool.submit(gemini)` + Cerebras 메인. Gemini 1개만 스레드로 띄우면 되므로 max_workers=1 로 충분(추가 워커 낭비 0). `_ensure_gemini_coach_writer().write` 바운드 메서드를 메인에서 확보 후 submit — 스레드 내 lazy-init 경쟁 회피.

**Total deviations:** 1 범위 축소 + 2 설계 판단. Scope creep 0.

## Threat Surface Scan
계획 `<threat_model>` 범위 내 — 신규 surface 없음.
- **T-27-12** (fan-out 집계 순서 비결정): 인덱스 순 join(완료-순서 수확 금지) + `as_completed` 소스 0(grep) + 지연-주입 결정론 테스트로 고정.
- **T-27-13** (부분 완료 verdict): `completed < planned → resource_limited` fail-closed 테스트(clock 예산 소진)로 고정.
- **T-27-14** (공유 상태 오염): WR-07 rebind→submit 순서 박제, 캐시 키 불변, Client 폴백 방침 주석.
- **T-27-15** (429 표면화): GEMINI_FANOUT_WORKERS 폴백 상수(4→2→1) + workers=1 순차 등가 테스트.
- **T-27-16** (future 생존 중 unlink): prefetch executor shutdown(wait=True) → outer finally session.close → unlink 순서(Pitfall 3).
- **T-27-23** (RTMW/추출 이중 실행 또는 prefetch RTMW 후 시작): estimate 런타임 1회 + submit-before-rtmw 로그 순서 테스트로 고정.
- **T-27-24** (테스트 마이그레이션 회귀 은폐): assert 무변경 + setattr 문자열 잔존 0(grep) + 4파일 명시 pytest.

## Verification Evidence
- 마이그레이션 4파일 setattr 문자열 잔존 0 (각 파일 `grep -c '"_extract_video_analysis_inputs"'` = 0).
- app.py: `_download_analysis_video`(6) / `_extract_video_analysis_inputs_from_local`(5) / ThreadPoolExecutor(2) / GEMINI_UPLOAD_PREFETCH(2) / gemini_upload_prefetch_submit(1) / gemini_future(2). rebind(3269) < submit(3296).
- gemini_vision_scorer.py: `as_completed`=0 / GEMINI_FANOUT_WORKERS=2.
- 스코프 게이트 `tests/gemini/ tests/test_stage_timing.py tests/test_vision_fanout_parallel.py` = 143 passed.
- 전체 backend pytest 실패/에러 집합 = base(c430b3e) 와 **IDENTICAL (65/65, comm 양방향 empty)** — 27-05 신규 FAILED/ERROR 0. 넓은 파이프라인 실패는 pre-existing module-global 순서 의존(격리 실행 시 전부 green).

## Issues Encountered
- **넓은 파이프라인 스위트 pre-existing 순서 의존 실패**([[pipeline-not-concurrency-safe-eval-serial]]): phase8/phase9 는 격리 실행 시 20 passed 이나 wide -k 실행 시 module-global 싱글턴 오염으로 실패. base vs mine 격리 대조 = IDENTICAL(신규 0)로 확정.
- geminic_wiring 의 `find_scene_flags` 노출 테스트 6건은 lazy import 구조(모듈 attr 아님)로 pre-existing 실패 — 본 plan 무접촉(unmodified 체크아웃 동일 6건 확인).

## User Setup Required
None — 신규 패키지 0, OTA 무관(백엔드). 신규 env 2종(GEMINI_UPLOAD_PREFETCH / GEMINI_FANOUT_WORKERS)은 코드 default(ON/4) + run_sweep setdefault 로 이중 박제. Pod `start_server.sh` 반영은 27-09. 실 벽시계 수확(prefetch 겹치기 + fan-out/coach 병렬)은 프로덕션 Pod 실측(27-09 EVAL18 before/after)에서 확인.

## Next Phase Readiness
- 27-07: status 시점 교정 완료 → PROGRESS_PCT 재배분(loading.tsx) 실측 기반 가능.
- 27-09 EVAL18: prefetch/fan-out/coach 병렬화 before/after 타이밍 + cold/warm 결정론 게이트 + completedCalls==plannedCalls(429 폴백 검증) + GEMINI_UPLOAD_PREFETCH=0 A/B 대조.

---
*Phase: 27-1-gemini-analysis-speed-1min*
*Completed: 2026-07-08*

## Self-Check: PASSED
- 생성/수정 파일 존재: test_vision_fanout_parallel.py, app.py, gemini_vision_scorer.py, 27-05-SUMMARY.md.
- 커밋 5개 전부 존재: d360dfd(refactor) / 0dd985f(feat) / 99fca50(test-RED) / 87d1ee9(feat-GREEN) / fcb7f67(feat).
- 스코프 게이트: tests/gemini/ + test_stage_timing + test_vision_fanout_parallel = 143 passed.
- 전체 backend pytest 실패/에러 집합 = base(c430b3e) 와 IDENTICAL (65/65) — 신규 0.
- grep 게이트 전량 통과: setattr 잔존 0 / as_completed 0 / seam·env·marker 존재 / rebind<submit.
