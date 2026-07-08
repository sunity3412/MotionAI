---
phase: 27-1-gemini-analysis-speed-1min
plan: 06
subsystem: backend
tags: [fault-zoom, firestore, contract, postprocess, performance, deferred-update]

# Dependency graph
requires:
  - phase: 27-05
    provides: "prefetch seam(_download_analysis_video + _extract_video_analysis_inputs_from_local) + fault_zoom stage 계측 위치"
  - phase: 27-01
    provides: "timingsMs 3-way lockstep 선례 + _stage contextmanager (fault_zoom 키)"
provides:
  - "faultZoomStatus 계약 3-way lockstep (analysis.ts + models.py + contract.md) — status 머신 독립 scalar"
  - "firestore_admin.update_analysis_fault_zoom — field-path 부분 업데이트(result.faultZoom* 2필드) + scoped validator 재사용"
  - "_process 재배열 — 점수 먼저 complete(status='done') → zoom 사후 렌더 → done/failed 부분 업데이트 (pending 고아 방지)"
  - "_render_fault_zoom/_build_(mode3_)fault_zoom_comparisons: result 부착 → comparisons list[dict] 반환 리팩터"
  - "학생 프레임 배열 재사용 (_VideoAnalysisInputs.frames) — ffmpeg 학생 디코딩 3회→1회, STUDENT_FRAME_CACHE 게이트"
affects: [27-07, 27-09]

# Tech tracking
tech-stack:
  added: []  # 신규 패키지 0
  patterns:
    - "사후 부분 업데이트: complete(set merge) 이후 field-path .update() 로 zoom 2필드만 교체 (배열 통째 교체 의미 명확, set(merge) 병합 모호성 회피)"
    - "pending 마커: 대상 존재 시에만 result.faultZoomStatus='pending' (대상 없으면 필드 생략 — 하위호환 판정 규칙 정합)"
    - "deferred graceful 3단: render 성공=done / render 예외=failed / failed write 실패=log.exception (재raise 0, 분석 이미 complete)"
    - "분석-로컬 프레임 캐시: NamedTuple frames 필드(default None 하위호환) + env 게이트(RunPod ON / Lambda OFF)"

key-files:
  created:
    - backend/tests/test_fault_zoom_deferred.py
  modified:
    - backend/shared/python/sunity_shared/models.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/functions/pipeline/app.py
    - app/src/types/analysis.ts
    - docs/contract.md

key-decisions:
  - "faultZoomStatus 를 PIPELINE_SEQUENCE/status enum 에 넣지 않고 result 내부 독립 scalar 로 — status 머신 확장 3-way 비용 회피(27-RESEARCH Alternatives). 주석 박제."
  - "_render_fault_zoom 의 result 인자 유지(결함/편차 read 전용) — 사후 mutation 금지(D-03). 반환만 result 부착→comparisons list[dict]."
  - "프레임 캐시 게이트 = 메모리 env(STUDENT_FRAME_CACHE) — RunPod 자동 감지(RUNPOD_ANALYZE_URL 은 Lambda 측 위임 플래그라 Pod 에서 False)에 의존 불가. default ON, Lambda template/ Pod env 반영은 27-09."
  - "기준/지난 영상은 캐시 타협(A5 메모리) — 학생 프레임만 캐시, 기준은 zoom 시점 1회 추출 유지. Pattern 7 명시 타협."
  - "_VideoAnalysisInputs.frames default None — 실경로는 항상 채우고 기존 테스트 stub 4파일은 미지정 시 None(캐시 비활성). Rule 3 stub 동기화 회피(27-01 대비 저churn)."

requirements-completed: [SPD-04]

# Metrics
duration: ~70min
completed: 2026-07-08
---

# Phase 27 Plan 06: fault_zoom 사후 분리 + 프레임 재사용 Summary

**fault_zoom 확대비교 PNG 렌더(후처리 주요분)를 complete_analysis 이후로 분리해 점수/verdict/감점 내역을 먼저 앱에 도착시키고(time-to-first-result 단축), zoom 은 faultZoomStatus pending→done/failed 부분 업데이트로 뒤따르게 했다. faultZoomStatus 계약을 analysis.ts + models.py + contract.md 3-way lockstep(status 머신 독립 scalar)으로 정의하고, firestore_admin.update_analysis_fault_zoom 이 result.faultZoom* 두 필드만 field-path 로 갱신하도록(D-03 경계 + scoped validator) 배선했다. 동시에 학생 영상 9fps/640px 프레임 배열을 분석-로컬로 보존해 ffmpeg 학생 재디코딩을 3회→1회로 줄였다(RunPod ON, Lambda 폴백 재추출 유지). 신규 패키지 0.**

## 측정 구분 — time-to-first-result vs server task 총 시간 (외부 리뷰 MEDIUM-3)

이 plan 이 개선하는 지표와 개선하지 않는 지표를 **명확히 구분**한다:

- **(a) time-to-first-result (이 plan 이 단축):** 앱이 `status='done'` 을 onSnapshot 으로 보는 시점 = `complete_analysis` 도착까지. fault_zoom 렌더(과거 complete 前, 후처리 주요분)가 complete **이후**로 빠졌으므로, 사용자가 점수/verdict/감점 내역을 보는 체감 완료 시점이 zoom 렌더 소요만큼 앞당겨진다. (실 수치는 27-09 EVAL18 프로덕션 Pod 실측 — before/after.)
- **(b) server task 총 시간 (이 plan 이 개선하지 않을 수 있음):** zoom 렌더가 **같은 BackgroundTask 에 남으므로**(분석 간 SERIAL 불변 유지, 별도 태스크 미도입) worker 점유 총시간(BackgroundTask 종료까지)은 그대로다. **RunPod throughput 개선 주장 금지.** 총시간 단축에 기여하는 것은 오직 Task 3 의 **프레임 재사용(학생 디코딩 3회→1회)의 ffmpeg 절감분**뿐이다.

두-지표의 데이터 소스: complete 까지의 `timingsMs` 합 = (a) time-to-first-result / `timingsMs` + 사후 `fault_zoom` stage 로그 라인 = (b) server task 총 시간. (사후 fault_zoom 소요는 timingsMs dict 가 이미 저장된 뒤라 저장 dict 엔 미포함 — 로그로만.) 27-09 의 27-TIMING-AFTER 표도 이 두 지표를 분리 기재한다(27-09 Task 3 step 4).

## Performance
- **Duration:** ~70 min
- **Tasks:** 3 (Task 1 TDD)
- **Files created:** 1 / **modified:** 5

## Accomplishments
- **Task 1 (TDD) — 계약 3-way + persistence:** `models.py` 에 `FAULT_ZOOM_STATUS_PENDING/DONE/FAILED` + `FAULT_ZOOM_STATUSES` tuple(**PIPELINE_SEQUENCE 비추가**, 주석 박제). `firestore_admin.update_analysis_fault_zoom(uid, id, comparisons, status)` — status 를 `FAULT_ZOOM_STATUSES` 로 검증(ValueError), 각 item 을 `_validate_dict_only_scalars`(safetyFlags 선례, validator 본체 무수정)로 nested 거부, `.update({"result.faultZoomComparisons":…, "result.faultZoomStatus":…, "updatedAt":…})` field-path. `analysis.ts AnalysisResult.faultZoomStatus?` + `contract.md faultZoomStatus 절`(사후 변경 경계 + status 독립 명시). RED(5 fail)→GREEN(5 pass).
- **Task 2 — _process 재배열:** `_render_fault_zoom`/`_build_fault_zoom_comparisons`/`_build_mode3_fault_zoom_comparisons`(attach→build 개명) 를 result 부착 대신 comparisons `list[dict]` 반환으로 리팩터. `_process` fault_zoom stage: 사전 렌더 제거 → zoom 대상 존재 시 `result['faultZoomStatus']='pending'` 마커만(대상 없으면 필드 생략). `complete_analysis` 직후 같은 BackgroundTask 에서 `_run_deferred_fault_zoom(render=…)` → done/failed 부분 업데이트. graceful 3단(render 예외=failed / failed write 실패=log.exception, 재raise 0). unlink 는 outer finally(zoom 이후 도달) — temp 파일 생명주기 정합. D-03: 사후 `result[` 직접 mutation 0(grep), update_analysis_fault_zoom 단일 경로.
- **Task 3 — 프레임 재사용:** `_VideoAnalysisInputs.frames`(9fps/640px, default None 하위호환)로 학생 프레임 보존. `_student_frame_cache_enabled()`(STUDENT_FRAME_CACHE env, default ON=RunPod / '0'=Lambda 폴백). `_build_selected_frame_pair`/`_render_fault_zoom`/`_build_(mode3_)fault_zoom_comparisons` 에 `cached_user_frames` pass-through — 학생 재추출 2회 소멸(디코딩 3회→1회). 기준/지난 영상은 캐시 타협(zoom 시점 1회 추출 유지, A5 메모리). zoom 후 캐시 명시 해제.

## Task Commits
1. **Task 1 (RED): update_analysis_fault_zoom + 3-way 상수 테스트** — `b67f54e` (test)
2. **Task 1 (GREEN): 계약 3-way + update_analysis_fault_zoom** — `970c9ad` (feat)
3. **Task 2: _process 재배열 (점수 먼저 complete → zoom 사후)** — `6c56d76` (feat)
4. **Task 3: 프레임 배열 재사용 (디코딩 3회→1회)** — `53256f3` (feat)

## TDD Gate Compliance
- Task 1: RED `b67f54e`(test, 상수/함수 부재로 5 fail) → GREEN `970c9ad`(feat, 5 pass). REFACTOR 불필요.
- Tasks 2/3 = `type="auto"`(비 TDD) — 각각 오케스트레이션/디코딩 카운트 behavior 테스트를 같은 파일에 추가.

## Deviations from Plan

### 설계 판단 (계획 범위 내)

**1. [설계 판단] 프레임 캐시 게이트 = STUDENT_FRAME_CACHE env (메모리 env)**
- 계획 Task 3 step 3 은 "RunPod 실행 여부(기존 env `RUNPOD_ANALYZE_URL` 소비 분기 **또는** 메모리 env)로 게이트"를 명시. `RUNPOD_ANALYZE_URL` 은 **Lambda 측 위임 플래그**라 실제 Pod 프로세스에서는 부재(False) — 그 분기로는 Pod 에서 캐시가 항상 OFF 되는 역전이 발생한다. 따라서 계획이 병기한 **메모리 env** 옵션을 채택: `STUDENT_FRAME_CACHE` default ON(=1), Lambda 폴백은 '0'. 27-05 의 env 이중 박제(코드 default + run_sweep/Pod env) 패턴과 정합. Pod start_server.sh / Lambda template 반영은 27-09.

**2. [설계 판단] _VideoAnalysisInputs.frames default None (Rule 3 stub 동기화 회피)**
- `frames` 필드에 default `None` 을 부여해, `_VideoAnalysisInputs(` 를 stub 하는 기존 테스트 4파일(test_stage_timing / gemini_integration / phase8 / phase9)을 무수정 통과시켰다(미지정=None=캐시 비활성). 실경로(`_extract_video_analysis_inputs_from_local`)는 항상 `frames=frames` 로 채운다. 27-01 은 helper 시그니처 확장 시 stub 4파일을 동기화(Rule 3)했으나, 여기선 default 로 저churn 처리.

**3. [개명] _attach_* → _build_* fault_zoom 함수**
- result 부착 시맨틱이 comparisons 반환으로 바뀌어 `_attach_fault_zoom_comparisons`→`_build_fault_zoom_comparisons`, `_attach_mode3_fault_zoom`→`_build_mode3_fault_zoom_comparisons` 로 개명(호출부/내부 참조 전량 갱신, 잔존 주석 참조도 갱신). 외부(테스트/타 모듈) 참조 0 확인 후 진행.

**Total deviations:** 3 설계 판단. Scope creep 0.

## Threat Surface Scan
계획 `<threat_model>` 범위 내 — 신규 surface 없음.
- **T-27-17** (zoom 부분 쓰기 실패 → 앱 무한 로딩): 렌더 실패=failed write(테스트) + failed write 실패=log.exception + pending 은 대상 존재 시에만 마킹. 앱 시간 상한 폴백은 27-07.
- **T-27-18** (complete 후 점수 필드 사후 변경 D-03 위반): 사후 write = update_analysis_fault_zoom 단일 경로(result.faultZoom* field-path만) — complete 이후 `result[` 직접 mutation grep 0.
- **T-27-19** (nested-array 부분 update 우회 유입): `_validate_dict_only_scalars` 루프(본체 무수정) — Test 2 로 고정.
- **T-27-20** (프레임 캐시 메모리 OOM): 학생만 캐시(기준 타협) + STUDENT_FRAME_CACHE Lambda OFF 분기 + zoom 후 명시 해제.
- **T-27-SC** (패키지 설치): 신규 패키지 0.

## Verification Evidence
- `tests/test_fault_zoom_deferred.py` = 12 passed (Task1 5 + Task2 3 + Task3 4).
- 3-way grep: faultZoomStatus analysis.ts=2 / firestore_admin=3 / contract.md=5 / FAULT_ZOOM_STATUS_PENDING models.py=2. PIPELINE_SEQUENCE 정의 무변경.
- app.py grep: update_analysis_fault_zoom=5(done/failed 경로 포함) / FAULT_ZOOM_STATUS_PENDING=1 / cached_user_frames=16 / _student_frame_cache_enabled=2. complete 이후 `result[` 직접 mutation 0.
- 스코프 게이트: `tests/gemini/ + test_stage_timing + test_vision_fanout_parallel + test_fault_zoom_deferred` = 155 passed.
- 전체 backend pytest 실패/에러 집합 = base(f9e0dd3) 와 **IDENTICAL (65/65, comm 양방향 empty)** — 신규 FAILED/ERROR 0. 넓은 스위트 실패는 pre-existing module-global 순서 의존 + 미설치 dep(imageio/fixtures) 수집 오류(격리 시 green).
- app typecheck(`tsc --noEmit`) exit 0 (worktree node_modules 심볼릭 링크, 실행 후 제거 — tracked 무변경).

## Issues Encountered
- **dev 머신 imageio 미설치:** `frame_extractor` 모듈이 imageio 를 top-level import 하므로 디코딩 카운트 테스트가 실 import 대신 fake 모듈을 `sys.modules` 에 주입(monkeypatch string path 는 실 import 유발)로 해결.
- **넓은 파이프라인 스위트 pre-existing 순서 의존 + 수집 오류**([[pipeline-not-concurrency-safe-eval-serial]]): base vs mine 격리 대조 = IDENTICAL(신규 0)로 확정.

## User Setup Required
None — 신규 패키지 0, OTA 무관(백엔드; 앱 소비는 27-07). 신규 env `STUDENT_FRAME_CACHE`(default ON) 는 코드 default 로 Pod 에서 즉시 유효 — Pod start_server.sh / Lambda template 반영은 27-09(27-05 env 패턴 정합). 실 수확(사후 분리 time-to-first-result + 프레임 재사용 디코딩 절감)은 프로덕션 Pod 실측(27-09 EVAL18)에서 확인.

## Next Phase Readiness
- 27-07: `faultZoomStatus` 계약 도착 → 앱 result 화면이 pending=placeholder / done=카드 / failed=숨김 소비 + pending 고아 시간 상한 폴백 배선.
- 27-09 EVAL18: time-to-first-result vs server task 총 시간 before/after(27-TIMING-AFTER 두-지표 분리) + STUDENT_FRAME_CACHE A/B + Pod start_server.sh env 반영.

---
*Phase: 27-1-gemini-analysis-speed-1min*
*Completed: 2026-07-08*

## Self-Check: PASSED
- 생성 파일 존재: test_fault_zoom_deferred.py, 27-06-SUMMARY.md.
- 커밋 4개 전부 존재: b67f54e(test-RED) / 970c9ad(feat Task1) / 6c56d76(feat Task2) / 53256f3(feat Task3).
- test_fault_zoom_deferred.py 12 passed / 스코프 게이트 155 passed / 전체 backend 실패집합 = base IDENTICAL(65/65).
- 3-way grep + PIPELINE_SEQUENCE 비추가 + 사후 result[ mutation 0 + app typecheck exit 0.
