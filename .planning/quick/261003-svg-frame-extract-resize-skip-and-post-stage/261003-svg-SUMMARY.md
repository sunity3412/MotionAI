---
phase: quick-261003-svg
plan: 01
status: complete
subsystem: backend/pipeline (analysis latency)
tags: [performance, frame-extract, post-stage, threading, no-scoring-change]
requires:
  - quick-261003-qmg (qmg 하네스 · 증거 로그 수치)
provides:
  - FfmpegFrameExtractor.extract 버리는 프레임 축소 생략 (출력 바이트 동일)
  - _post_stage_parallel_enabled (env POST_STAGE_PARALLEL, 기본 ON)
  - _run_post_stages (코칭 문장 ∥ 곁가지, compare_render 맨 뒤)
  - timingsMs 로그 키 post_parallel
affects:
  - backend/functions/pipeline/app.py _process 사후 블록
  - Pod 다음 기동부터 (배포 안 함)
tech-stack:
  added: []
  patterns: [분석-로컬 ThreadPoolExecutor(max_workers=1, "post_side"), 곁가지 전용 timings dict 후 join 병합, env 토글 매 호출 읽기]
key-files:
  created:
    - backend/tests/test_frame_extractor_resize_skip.py
    - backend/tests/test_post_stage_parallel.py
  modified:
    - backend/shared/python/sunity_shared/analysis/frame_extractor.py
    - backend/functions/pipeline/app.py
    - backend/tests/phase32/test_spot_check.py
    - docs/contract.md
decisions:
  - "사후 단계 병렬 = 코칭 문장(메인) ∥ 코칭 오디오 → 확대 사진 → 스팟체크(곁가지), compare_render 는 두 가지 뒤 메인 단독 — env POST_STAGE_PARALLEL 기본 ON, \"0\" 이면 직렬 그대로"
  - "프레임 추출은 버리는 프레임을 축소하지 않고 원본 참조만 들고 있다가 마지막 강제 포함 때만 한 장 축소 — ffmpeg select 필터 안은 픽셀이 달라 기각"
metrics:
  duration: "약 15분 (2026-10-03T12:07Z ~ 12:22Z)"
  completed: 2026-10-03
  tasks: 3
  commits: 6
  files: 6
---

# Quick 261003-svg: 프레임 추출 축소 생략 + 사후 단계 병렬 Summary

프레임 추출이 솎아 버리는 프레임까지 PIL 축소하던 것을 없앴고(출력 바이트 동일을 옛 루프 복제 대비 테스트로 잠금),
점수 뒤 사후 단계를 "코칭 문장 ∥ 오디오 → 확대 사진 → 스팟체크" 두 가지로 겹친 뒤 compare_render 를 맨 뒤에
혼자 돌리게 했다(env `POST_STAGE_PARALLEL`, 기본 ON, "0" 이면 지금 직렬). 채점 · veto · Gemini 설정 · 프롬프트 ·
단계 내부 알고리즘 diff 0. 배포 안 함 — Pod 실측은 다음 세션.

## 커밋

| Task | 커밋 | 내용 |
|------|------|------|
| 1 RED | 2e42d98b | test: 프레임 추출 축소 생략 — 바이트 동일 · 호출 수 테스트 |
| 1 GREEN | 95b644a8 | perf: 프레임 추출 — 버리는 프레임 축소 생략 (출력 바이트 동일) |
| 2 RED | cac6e2ca | test: 사후 단계 오케스트레이터 단위 테스트 |
| 2 GREEN | 1b69baf8 | feat: 사후 단계 오케스트레이터 + POST_STAGE_PARALLEL 토글 |
| 3 RED | 8395606c | test: _process 사후 병렬 통합 테스트 |
| 3 GREEN | cff6cfcc | feat: _process 사후 단계 병렬 배선 + 게이트 앵커 + contract |

Task 1(A) 은 95b644a8 까지로 혼자 완결된다 — Task 2 · 3 을 되돌려도 유효.

## 관측 [확인] — 다음 세션이 승계해도 되는 것

실행 출력 마지막 줄은 그대로 옮겼다.

1. **Task 1 RED** — `pytest tests/test_frame_extractor_resize_skip.py` → `7 failed, 9 passed in 0.35s`.
   바이트 동일 8건은 통과(같은 코드), 호출 수 8건 중 7건 실패(옛 코드는 범위 안 전 프레임 축소, 예: `assert 11 == 5`).
   g(step 1)는 버리는 프레임이 없어 옛 코드에서도 5/5 라 통과 — 계획 표와 일치.
2. **Task 1 GREEN** — 계획 verify 명령(새 파일 맨 앞 + last_frame · effective_fps · probe_duration ·
   fault_zoom_deferred · reference_real_fps) → `72 passed in 0.68s` (skip 0).
3. imageio 2.37.4(backend/.venv) `FfmpegFormat.Reader._read_frame` 안에
   `result = np.frombuffer(s, dtype=self._dtype).copy()` 가 있다 — 이번 세션에서 inspect 로 재확인.
4. **Task 2 RED** — `11 failed in 0.56s`, 원인 `AttributeError: module 'app' has no attribute '_post_stage_parallel_enabled'`.
5. **Task 2 GREEN** — `pytest tests/test_post_stage_parallel.py tests/test_analysis_local_state_concurrency.py tests/phase32/test_spot_check.py`
   → `55 passed, 1 warning in 1.50s` (warning = google genai `_UnionGenericAlias` DeprecationWarning, 기존).
6. **Task 3 RED** — 통합 3건 `3 failed, 11 deselected in 15.72s`. 실패 원인은 전부 스레드 단언
   (`'MainThread'.startswith('post_side')` False) — 직렬 쪽 단언(호출 1회 · 인자 · 순서)은 기존 코드에서 통과.
7. **Task 3 GREEN** — 앵커 갱신 전 계획 verify 묶음 → `1 failed, 210 passed, 1 warning in 6.04s`
   (`test_spot_check_stage_after_complete_and_fault_zoom` 의 들여쓰기 고정 `source.index` — 예상된 실패).
   앵커를 공백 무관 정규식으로 바꾼 뒤 → `211 passed, 1 warning in 5.88s`.
   `tests/quick_260901_wbo/test_coach_text_deferred.py` 는 무수정 통과(클로저가 `_process` 안이라 getsource 에 잡힌다).
8. 스레드 테스트 반복 — `test_post_stage_parallel.py + test_ref_prefetch_scene_join.py` 5회 연속 `47 passed`(2.0~2.2s).
9. `grep -c "post_parallel" docs/contract.md` → `2`.
10. **backend 전체** `pytest tests -q -p no:cacheprovider` → `5973 passed, 20 skipped, 98 warnings in 62.20s (0:01:02)`.
    기준선 5943 passed / 20 skipped + 새 테스트 30(resize_skip 16 + post_stage_parallel 14) = 5973. 실패 0, skip 증가 0.
11. `git diff --stat a21edc48..HEAD` 코드 파일 = frontmatter files_modified 6개뿐(app.py · frame_extractor.py ·
    test_spot_check.py · 새 테스트 2 · contract.md). 삭제 파일 0. template.yaml · runpod_inference · start_server.sh ·
    app/ · 채점 모듈 무변경. AWS · Pod · Lambda · sam · s3 무접촉. 통합 테스트 `net_attempts == []`.
12. qmg 하네스로 `_process` mode1 을 돌린 탐침(지운 임시 파일)에서: 감점 records 0건, 사후 다섯 단계 모두 호출,
    `_build_fault_zoom_comparisons` 호출 1회(빈 목록), Firestore 사후 갱신 = coach_audio done · fault_zoom done ·
    spot_check done, compare_render 는 가중치 파일 부재로 능력 프로브 스킵(doc 무접촉), 소켓 시도 0.
    → 통합 테스트의 "같은 결과" 대조는 **빈 records** 위에서의 대조다(아래 추정 2).

### Task B 의존 확인 표 (플래너 context 1~7 — 이번 세션 재확인 여부)

| # | 항목 | 판정 | 이번 세션에서 한 것 |
|---|------|------|---------------------|
| 1 | result 읽기/쓰기 키 — 코칭 문장 쓰기(tips · coachStatus · 리포트 hook) ∩ 곁가지 읽기 = ∅, 곁가지는 result 에 안 씀 | [확인] | `_run_deferred_coach_audio`(records.recordId/cueLine) · `_run_deferred_spot_check`(records · summaryPraise) · `_build_fault_zoom_comparisons`(visionVeto · joints · deductionBreakdown) · `_render_fault_zoom`(result 사용 = motionAlignment 한 곳, 하위 fault_zoom.py 로 result 를 넘기지 않음) 코드 읽음. `criterion_units_from_records` · `select_judged_records` 는 records 를 읽기만 함 |
| 1b | timings_ms 공유 | [확인] | 곁가지는 전용 dict(`side_timings`)에 재고 join 뒤 `timings_ms.update` — 단위 테스트가 `is not` 과 병합을 단언 |
| 2 | Firestore field-path 서로 다름, 공유는 updatedAt | [확인 — 플래너] / 앱 영향 [미확인] | 이번 세션은 update_* 시그니처만 확인, field-path 재독 안 함. 통합 테스트가 두 모드의 (함수, status) 다중집합 동일을 단언 |
| 2b | Firestore 클라이언트를 두 스레드가 동시에 쓰는 것 | 선례 [확인] / 안전성 문서 [미확인] | qmg prefetch 스레드("gemini")가 이미 `get_reference_motion` 을 메인과 동시에 부른다(하네스 `_fake_get_ref` 가 스레드 이름으로 가름). google-cloud-firestore 의 스레드 안전성 공식 문서 대조는 안 함 |
| 3 | RTMW 는 compare_render 만 | [확인] | app.py 4145~5300 · fault_zoom.py · card_gates.py · card_photo_audit.py · spot_check.py grep — rtmw/rtmlib/onnx 는 주석 3줄뿐, import · 호출 0 |
| 4 | 프레임 · 임시 파일 수명, `cached_user_frames = None` 은 곁가지 안 nonlocal | [확인] | 배선에서 그대로 구현. 통합 테스트가 각 런에서 다섯 단계 end < close < unlink 와 `_build_fault_zoom_comparisons` 실제 호출(람다 늦은 바인딩이 깨지면 여기서 잡힘)을 단언 |
| 5 | 실패 격리 — 각 `_run_deferred_*` 재raise 0 | [확인] | 다섯 함수 본문 except 블록 읽음. 통합 테스트가 fault_zoom 렌더 예외 → failed 마킹 + 나머지 3단계 1회씩 + compare_render 빈 목록을 단언 |
| 6 | Gemini 동시 호출 — 학생 File API 파일 쓰는 사후 호출은 coach B 하나 | [확인 — 플래너] + 부분 재확인 | spot_check `_CLIENT`(키 = gemini_vision_scorer._load_api_key, env 우선) · coach B 는 호출마다 `genai.Client` 새로 만듦(gemini/client.py) 재확인. card_gates 인라인 JPEG 는 플래너 확인을 승계(재독 안 함) |
| 6b | boto3 클라이언트 동시 생성 | Pod [확인] / env 키 없는 환경 [미확인] | 곁가지 새 클라이언트 = `_get_polly_client()` 하나. 메인 가지: Cerebras 키는 `CerebrasCoachWriter.__init__`(= `_ensure_adapters`, 분석 시작)에서 이미 로드, Gemini 키는 Pod env(`start_server.sh` GEMINI_API_KEY) → 사후 창에서 메인이 boto3 클라이언트를 만들지 않음 |
| 7 | stage_timing — 각 단계 자기 stage 그대로 + post_parallel | [확인] | 통합 테스트: ON 의 timingsMs 키 = OFF 키 ∪ {post_parallel}, coach_audio · fault_zoom · spot_check · compare_render 키 존재 |

새로 본 것(계획에 없던 관측, 위험 판정은 아님): 코칭 문장 단계는 안에서 이미 자기 풀(`thread_name_prefix="coach_gemini"`)로
Gemini coach B 를 돌리고 Cerebras 는 메인에서 돈다 [확인 — app.py `_run_deferred_coach_text`]. 그래서 병렬 ON 의 사후 창 스레드는
메인(Cerebras → coach_hook) · coach_gemini(coach B) · post_side(오디오 → 확대 사진 → 스팟체크) 셋이다. 같은 Gemini 키로 동시에
나가는 요청은 coach B 1 + 곁가지 1(card_gates 또는 spot_check, 곁가지 안은 순차) = 최대 2 — 계획의 "2~3개" 범위 안.
계획의 [확인] 사실과 다른 코드는 찾지 못했다 → B 를 멈출 사유 없음.

## 추정 [미확인] — 승계 전에 재검증할 것

1. **Pod 효과 크기.** frame_extract −≈10초는 오케스트레이터 로컬 실측(25.7 → 15.7초, 4K HEVC 593프레임) 비율을 옮긴 것이다.
   Pod CPU · 디코더 조건에서의 절감은 미측정. fault_zoom 안 기준 영상 추출도 같이 줄 수 있으나 기준 영상 코덱 · 해상도 미측정.
2. **사후 벽시계 −75~86초**는 qmg 증거 로그 런별 값의 산술이다. Gemini 동시 요청(같은 키 최대 2개) 지연 · 429 영향 미측정.
   통합 테스트의 "두 모드 결과 동일"은 감점 records 0건 하네스 위의 대조라, 실제 카드 · 오디오 · 스팟체크가 생기는 영상에서의
   OFF/ON 결과 동일은 Pod 실측(아래 5)으로 확인해야 한다.
3. Pod 의 imageio 버전(requirements 하한 >=2.34)이 `_read_frame` `.copy()` 를 갖는지 미확인 — 옛 코드도 축소 없는 영상에서
   같은 전제를 쓰고 있었다는 점이 유일한 근거.
4. 앱이 `updatedAt` 의 ms 단위 경쟁(사후 단계 두 스레드)에 영향받지 않는다는 판단은 코드 읽기(result.tsx zoom pending 180초 재무장)뿐, 앱 실측 없음.
5. env `GEMINI_API_KEY` 가 없는 환경(로컬 · Lambda 폴백)에서 두 스레드가 동시에 boto3 SSM/Polly 클라이언트를 만들 때의 안전성 미확인 —
   운영 경로 아님, `POST_STAGE_PARALLEL=0` 으로 끌 수 있다.

## Pod 측정 계획 (실행은 다음 세션)

메모리 analysis-time-reference-gemini-reupload-42s · pod-link-can-collapse-silently 규율 따름.

1. 같은 날 · 같은 RTX 4090 Pod · 38-14 쌍(학생 `uploads/zVJP…/2a7495bb….mp4` · 기준 `d8e849f7…` v1), `backend/scripts/e2e_app_path.py` 경로.
2. 코드는 이 quick 판(cff6cfcc 이후) 하나로 두고 env 만 바꿔 서버 재시작 — `POST_STAGE_PARALLEL` 0 → 1 → 1 → 0.
   앞 분석의 `stage=compare_render` 로그가 나온 뒤 다음을 보낸다(분석 간 겹침 0).
3. Task A 는 토글이 없다 — `frame_extract` 를 qmg 증거 로그(22.5 / 23.5 / 25.2 / 26.1초, 같은 쌍 · 같은 GPU 종류)와 비교하고,
   fault_zoom 안 기준 영상 추출 몫은 `fault_zoom` 값 변화로 본다. 필요하면 직전 커밋(a21edc48)으로 서버만 바꿔 1회 교차.
4. 잴 것: 런별 `frame_extract` · `coach_dual` · `coach_hook` · `coach_audio` · `fault_zoom` · `spot_check` · `post_parallel` ·
   `compare_render`, 그리고 `분석 완료` 로그 → `stage=compare_render` 로그 사이 벽시계(화면이 다 채워지는 시간).
5. 불변 확인: 런마다 `overallScore` · `deductionBreakdown.final` · `dimensionScores` 동일, `coachStatus` · `faultZoomStatus` ·
   `coachAudio.status` · `spotCheck.status` · `renderedCompare.status` 가 OFF/ON 에서 같음, 카드 수 · 오디오 items 수 같음.
   Pod 로그 `grep -E "RESOURCE_EXHAUSTED|429|Traceback|사후 곁가지 실패"` 0.
6. 기대 [추정]: frame_extract −≈10초, 사후 벽시계 −75~86초. Gemini 동시 요청 지연이 커지면 절감이 줄 수 있다.
   문제가 보이면 재배포 없이 `POST_STAGE_PARALLEL=0` 으로 직렬 복귀.

## Deviations from Plan

1. **[커밋 형식] 스코프 `261003-svg`** — 계획은 `quick-261003-svg` 였으나 오케스트레이터 제약(`feat(261003-svg): ...`)을 따랐다.
   Task 1 GREEN 의 type 은 계획대로 `perf`.
2. **[통합 테스트 인자 대조] `reference_local_video_path`** — 계획은 두 모드에서 값이 같음을 단언하라 했으나, 기준 temp 파일 이름이
   런마다 무작위라 값이 다를 수밖에 없다. 대신 각 런에서 "그 런의 prefetch 다운로드 경로와 같음 + 런 뒤 파일 없음"을 단언했다.
   uid · analysis_id · bucket · mode · local_video_path 는 두 모드 값 동일 단언 그대로.
3. **[하네스 재사용 방식]** 두 모드를 **한 하네스**(`_install` 1회)에서 차례로 돌리고 기록 길이 · `complete.call_args_list[n]` 으로 런 구간을
   잘랐다. 런마다 `audio_started` Event 를 clear 해 앞 런의 set 이 겹침 증명을 오염시키지 않게 했다. 꼬임 없음(5회 반복 통과).
4. **[단언 추가 — 계획보다 강하게]** `_build_fault_zoom_comparisons` 기록 wrapper(실제 호출 1회 · 받은 result 객체 · 스레드),
   직렬 런의 사후 다섯 단계 start/end 정확한 순서, 상태 전이(update_analysis_status) 목록 동일, 토글 매 호출 env 읽기,
   곁가지 예외 로그에 exc_info 없음. 약화한 단언 없음.
5. **[STATE.md 미갱신]** 실행기 기본 절차(state.advance-plan 등)는 돌리지 않았다 — 오케스트레이터 제약("SUMMARY.md / STATE.md 는
   오케스트레이터가 커밋", quick 은 Phase 38 plan 카운터와 무관). ROADMAP · REQUIREMENTS 무접촉.

Rule 1~3 자동 수정 없음. Rule 4 사유 없음.

## Known Stubs

없음. (새 테스트의 stub 은 테스트 전용 — 운영 코드에 빈 값 · 자리표시자 없음.)

## TDD Gate Compliance

세 Task 모두 `test(...)` 커밋(RED, 실제 실패 확인) 뒤 `perf/feat(...)` 커밋(GREEN). REFACTOR 커밋 없음.

## Self-Check: PASSED

- 파일: frame_extractor.py · app.py · test_spot_check.py · contract.md 수정, test_frame_extractor_resize_skip.py · test_post_stage_parallel.py 존재 — `git diff --stat a21edc48..HEAD` 6 files.
- 커밋: 2e42d98b · 95b644a8 · cac6e2ca · 1b69baf8 · 8395606c · cff6cfcc — `git log --oneline a21edc48..HEAD` 6줄.

## Pod 실측 (2026-10-03 밤, belle "끝나면 Pod 켜서 실측까지" — 오케스트레이터 실행)

### 관측 [확인]

- Pod `70k9sodi33enon` RTX 4090(qmg 와 같은 종류) · 생성 12:22Z → `pod_teardown.py` 로 종료 · 잔액 $14.54 → $14.18 · Lambda `RUNPOD_ANALYZE_URL` = `pod-down.invalid` · 계정 Pod 0대 [확인 조회]. 볼륨 리포는 종료 전 `main`(15b90db1)으로 되돌림.
- 한 Pod 에서 서버만 재시작해 판을 바꿈: 전 = `a21edc48`(qmg 포함, svg 직전) · 후 = `15b90db1`(svg, `POST_STAGE_PARALLEL` 기본 ON). 순서 전1 → 후1 → 후2 → 전2, 각 런은 사후 단계 끝(`INFO runpod_inference: 분석 완료`) 뒤 다음. 입력 = qmg 와 같은 38-14 쌍, 같은 익명 계정.
- 로그 = `evidence/svg_{before1,after1,after2,before2}_runpod_server.log`. Traceback · RESOURCE_EXHAUSTED · 429 · `사후 곁가지 실패` = 0 [확인 grep].

| 런 | 점수까지 | 점수 → 사후 끝 | 전체 | frame_extract | coach_dual | fault_zoom | post_parallel | coach B 504 재시도 |
|---|---|---|---|---|---|---|---|---|
| 전1 | 120.5초 | 222.8초 | 343.3초 | 22.7 | 56.0 | 80.0 | — | 0 |
| 후1 | 101.7초 | 195.8초 | 297.5초 | **13.4** | 86.4 | 109.4 | 119.7 | 1 |
| 후2 | 108.8초 | 167.1초 | 275.9초 | **13.5** | 91.4 | 61.1 | 91.7 | 1 |
| 전2 | 116.5초 | 260.7초 | 377.2초 | 22.7 | 85.9 | 89.5 | — | 1 |

- 평균: 점수까지 118.5 → 105.3초(**−13초**) · 점수 뒤 241.8 → 181.5초(**−60초**) · 전체 360.3 → 286.7초(**−74초**).
- frame_extract 22.7초 → 13.4~13.5초(−9.2초) — 양쪽 2회씩 값이 거의 같다 [확인].
- spot_check 9.6~10.3초 · compare_render 71.7~73.7초 — 양쪽 같다(판과 무관).
- 점수 불변: 4건 모두 `overallScore 100` · `deductionBreakdown.final 100` · `faultZoomStatus done` · coachAudio done [확인]. result 잎 필드 155개 중 다른 16개 = timingsMs · 영상/결과 키·URL · commitSha · faultZoomComparisons[0] 의 imageKey/imageKeyPlain/imageUrl/imageUrlPlain(분석 ID·서명이 든 경로) — 그 밖의 확대 사진 데이터는 4건 동일 [확인 비교 스크립트].
- coach B(`gemini-3.1-pro-preview`) 504 → 1회 재시도가 4건 중 3건(전2 · 후1 · 후2)에 있다. 오전 qmg 런에도 있었다 — 판과 무관한 Gemini 쪽 현상 [확인 로그].

### 진단 — 재검증 대상 [미확인]

- 병렬 구간(`post_parallel`)은 max(코칭 문장, 곁가지) 이다. 코칭 문장이 504 재시도로 86~91초가 되면 그쪽이 사후 구간의 바닥이 된다(후2: 코칭 91 vs 곁가지 ≈71 → 92초).
- veto_collect 가 후 쪽에서 23 → 14초로 줄었지만 이번 변경은 veto 를 건드리지 않는다 — Gemini 편차 또는 VisionVetoCache 로 보이고 효과로 세지 않는다.
- 다음 레버 후보: coach B 504(≈60초 타임아웃 후 재시도) · compare_render 72초(혼자 남은 가장 긴 단계).
