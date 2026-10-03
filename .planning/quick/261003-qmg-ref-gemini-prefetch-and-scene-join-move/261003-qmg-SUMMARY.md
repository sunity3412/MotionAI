---
phase: quick-261003-qmg
plan: 01
status: complete
subsystem: pipeline (분석 시간 — mode1 점수 도착)
tags: [analysis-time, gemini-file-api, prefetch, scene-finder, stage-timing]
requires: [Phase 27 D-03/D-04 분석-로컬 executor · GeminiFileSession, 38-14 Pod 로그]
provides:
  - app.py 모듈 헬퍼 5개 — _reference_prefetch_wanted · _prefetch_reference_video · _upload_prefetched_reference · _take_prefetched_reference_path · _prefetched_reference_temp_path
  - _process 배선 — 기준 영상 다운로드+Gemini 업로드 prefetch 제출, prefetch 경로 scene_finder join 을 _build_coach_context 직전으로 이동, executor 수명 outer finally 까지, 정리 순서 join → close → unlink
  - 새 stage 3개 — student_upload_wait · ref_video_download · ref_upload
  - 포즈 블록과 outer try 사이의 raise 가능 문장 3개를 outer try 안으로(그 구간 실패도 session.close · temp unlink)
  - backend/tests/test_ref_prefetch_scene_join.py (헬퍼 단위 25 + _process 통합 [A]~[H] 8 = 33)
  - docs/contract.md timingsMs 절 — 새 키 3개 + scene_finder 의미 변화
affects: [RunPod Pod 의 _process (운영 경로), Lambda 폴백 _process, timingsMs 해석]
tech-stack:
  added: []
  patterns: [분석-로컬 executor 에 FIFO 의존 future 체인 · 채점 경로 키와 대조해 맞을 때만 prefetch 사용 · 첫 소비처 직전 join · join → close → unlink 정리 순서]
key-files:
  created:
    - backend/tests/test_ref_prefetch_scene_join.py
  modified:
    - backend/functions/pipeline/app.py
    - docs/contract.md
key-decisions:
  - "기준 영상 prefetch 는 mode1 + referenceMotionId + veto ON 일 때만 — mode3 · veto OFF · id 없음은 추가 Firestore 읽기 0, 추가 S3 다운로드 0"
  - "prefetch 파일은 채점 경로가 읽은 ref doc 의 videoS3Key 와 같을 때만 쓴다. 다르면 기존 동기 다운로드, 안 쓴 temp 는 executor join 뒤 outer finally 가 지운다"
  - "업로드 future 는 붙잡지 않는다 — 결과는 세션 캐시를 거쳐 ref_upload 자리의 get_or_upload(캐시 hit/inflight 대기)로 닿는다"
  - "포즈 블록 finally 의 executor.shutdown 삭제 — 남기면 성공 경로가 scene · 기준 업로드를 포즈 직후에 다 기다려 이동 효과 0"
requirements-completed: [QUICK-261003-qmg]
duration: 약 35분
completed: 2026-10-03
---

# quick-261003-qmg: 기준 영상 Gemini 업로드 prefetch + scene_finder join 이동 Summary

**mode1 · veto ON 분석의 기준 영상 S3 다운로드와 Gemini File API 업로드를 학생 영상 다운로드 직후 분석-로컬 executor 로 옮기고, prefetch 경로의 scene_finder join 을 recognizer 앞에서 `_build_coach_context` 직전으로 옮겼다. 채점 입력·판정 순서는 그대로다. 배포는 하지 않았다.**

## 커밋

| 커밋 | 내용 |
|------|------|
| 5c5cfef | test — 헬퍼 5개 단위 테스트 (RED) |
| 14a06b1 | feat — 헬퍼 5개 (GREEN) |
| ab794ab | test — _process 통합 [A]~[H] (RED) |
| 9214303 | feat — _process 배선 (GREEN) |
| 47c5505 | docs — contract.md timingsMs 절 |

`git diff --stat 367d676a..HEAD` 결과 바뀐 파일은 셋이다(`git diff --numstat`): app.py +266/-59, 새 테스트 +851, contract.md +11/-2. template.yaml · runpod_inference · shared/python · app/ 은 바뀌지 않았다 [확인].

---

## 관측 — 실행 출력과 코드 사실 (승계 가능)

### 1. 바꾼 자리 (app.py 최종 줄 번호) [확인 — grep]

| 줄 | 무엇 |
|----|------|
| :49, :52 | import 에 `Future`, `Any` 추가 (표준 라이브러리만) |
| :543~674 | 헬퍼 5개 + 왜 주석 블록 (`_safe_unlink_local_video` 바로 뒤) |
| :8962~8966 | 27-05 주석의 "기준 영상 prefetch 는 27-05 범위 밖" 문장 정정 |
| :8978~8982 | `ref_prefetch_future = None`, `scene_result: dict \| None = None` |
| :9001~9019 | `_reference_prefetch_wanted` 이면 `executor.submit(_prefetch_reference_video, ...)` 다음 `executor.submit(_upload_prefetched_reference, ...)` (학생 업로드 · scene 다음 순서) |
| :9061 | `student_upload_wait` stage (학생 핸들 join/동기 업로드를 감쌈) |
| :9076 | `if scene_future is None:` 일 때만 옛 자리에서 동기 scene_finder |
| :9083~9104 | 포즈 블록 except 순서 = shutdown → session.close → 학생 temp unlink → 기준 prefetch temp unlink → raise |
| :9105~9108 | 포즈 블록 `finally:` (shutdown) 삭제, 그 자리 주석 |
| :9126~9131(주석), :9184~9191 | STATUS_COMPARISON write · `_signed_get(bucket, key)` · `_extract_target_torso_px` 를 같은 순서로 outer try 맨 앞으로 이동 |
| :9537 | `ref_video_download` stage — `_take_prefetched_reference_path(ref_prefetch_future, ref["videoS3Key"])` 먼저, None 이면 기존 동기 다운로드 블록(내용 그대로 들여씀) |
| :9696~9700 | `ref_upload` stage — 기준 영상이 있을 때만, 호출은 종전 `session.get_or_upload` 그대로 |
| :9729~9733 | prefetch 경로 scene join (`scene_finder` stage) — veto_collect 뒤 · `coach_context = _build_coach_context(` 바로 앞 |
| :10631~10632 | outer finally 맨 앞 `executor.shutdown(wait=True)` (session.close :10637 보다 앞) |
| :10653 | outer finally 끝에 `_safe_unlink_local_video(_prefetched_reference_temp_path(ref_prefetch_future))` |

플래너 줄 번호(:8746 _process, :8842 포즈 try, :8913 scene join, :9054 get_reference_motion, :9361 veto 게이트, :9507 ref 업로드, :9537 coach, :10428 outer finally)는 착수 시점 코드와 일치했다 [확인]. 헬퍼 추가로 이후 줄이 +134 밀렸다.

### 2. 바꾸지 않은 것 [확인 — diff]

- 채점 경로: `firestore_admin.get_reference_motion(meta.get("referenceMotionId"))`(지금 :9225), recognizer 호출, DTW, `_collect_vision_fault_context` 인자 목록, `_apply_vision_veto` 두 호출부 — diff 에 없다.
- veto 설정(GEMINI_VISION_VETO_ENABLED 기본 OFF) · 기준 영상 축소 · 분석 간 핸들 캐시(모듈 전역 0) · 사후 단계(`_run_deferred_*`) · executor max_workers(4) · 배포 · template.yaml · runpod_inference · shared/python · app/ — 전부 무변경.
- 학생 영상 업로드 · scene_finder prefetch 의 제출 방식(27-05)은 그대로이고, 그 뒤에 기준 2건만 덧붙였다.

### 3. 테스트 실행 출력 (마지막 줄 그대로)

- Task 1 RED: `25 failed in 1.12s` — 전부 `AttributeError: module 'app' has no attribute '_...'` (5종).
- Task 1 GREEN: `25 passed in 0.72s`.
- Task 2 RED: `7 failed, 1 passed, 25 deselected in 5.98s`. 실패 사유 — [A] 기준 다운로드가 MainThread · [B] `released_by_veto` False · [C] `stage=ref_upload` 로그 없음 · [E] gemini 스레드 다운로드 없음 · [F] "prefetch 다운로드 시도 자체가 없었다" · [G][H] "기준 prefetch 가 시작되지 않았다". [D] 는 통과 — 아래 편차 3.
- Task 2 GREEN: `tests/test_ref_prefetch_scene_join.py tests/test_stage_timing.py tests/pipeline/test_pipeline_phase9.py` → `42 passed, 1 warning in 4.49s`. 새 파일 단독 5회 반복 → 5회 모두 `33 passed` (1.60~1.65s, 스레드 테스트 흔들림 없음).
- awk 게이트(Task 2 verify): `v=9700 s=9732 n=1 c=9733` → exit 0 (`scene_future.result()` 코드 1곳, veto_collect 와 coach context 사이).
- pipeline 묶음(plan Task 3 목록): `6 failed, 701 passed, 1 skipped, 76 warnings in 31.41s`. 실패 6건은 이번 변경과 무관 — 아래 "기존 실패".
- backend 전체: `5943 passed, 20 skipped, 98 warnings in 61.86s (0:01:01)`, exit 0. 오케스트레이터 기준선 5910 passed / 20 skipped + 새 테스트 33 = 5943.

### 4. 기존 실패 (이번 변경과 무관, 고치지 않음)

pipeline 묶음을 그 순서로 돌릴 때만 실패하고, 단독(`tests/gemini/test_client.py tests/gemini/test_session_wiring.py` → `21 passed`, `tests/gemini` → `155 passed`)과 backend 전체(5943 passed)에서는 통과한다. 변경 전 커밋 367d676a 를 임시 worktree 로 띄워 같은 묶음(새 테스트 파일 제외)을 돌려 **같은 6건이 같은 이름으로** 실패하는 것을 확인했다 [확인] — 순서 의존 기존 결함:

- tests/gemini/test_client.py::TestAPIErrorRetry::test_5xx_retry_then_success
- tests/gemini/test_client.py::TestAPIErrorRetry::test_4xx_immediate_none
- tests/gemini/test_session_wiring.py::TestMomentExtractorHandleInjection::test_m1_injected_handle_skips_upload_poll_delete
- tests/gemini/test_session_wiring.py::TestMomentExtractorHandleInjection::test_m2_self_upload_generate_error_deletes_exactly_once
- tests/gemini/test_session_wiring.py::TestMomentExtractorHandleInjection::test_m2_self_upload_success_deletes_exactly_once
- tests/gemini/test_session_wiring.py::TestMomentExtractorHandleInjection::test_m2_upload_raise_no_delete_and_original_error

### 5. 새 stage 3개 — 무엇을 재나 [확인 — 코드]

| 키 | 언제 생기나 | prefetch ON | prefetch OFF |
|----|------------|-------------|--------------|
| `student_upload_wait` | keep_local_video 경로 전부(mode1 · mode3) | 포즈 뒤 학생 업로드 future 잔여 대기 | 학생 영상 동기 업로드 전체 |
| `ref_video_download` | mode1 · veto ON · ref doc 에 videoS3Key | prefetch 다운로드 잔여 대기(불일치 · 실패면 그 뒤 동기 다운로드까지 포함) | 기준 영상 동기 S3 다운로드 |
| `ref_upload` | 기준 로컬 파일이 있을 때만(mode3 · veto OFF 는 키 없음) | 세션 캐시 hit 또는 진행 중 업로드 대기 | 기준 영상 동기 업로드 + ACTIVE 폴링 — 지금까지 어느 stage 에도 안 잡히던 자리 |

기존 `ref_fetch_download`(:9224, get_reference_motion 감쌈)는 그대로다 — 이름과 달리 영상 다운로드가 아니라 Firestore 읽기를 잰다.

### 6. `scene_finder` stage 의미 변화 [확인 — 코드]

- prefetch ON: 이제 `_build_coach_context` 직전의 **잔여 대기**만 잰다(옛: recognizer 앞 join 대기).
- prefetch OFF: 종전처럼 옛 자리 동기 호출 전체.
- 이 변경 전후 doc 의 `scene_finder` 값은 같은 물건이 아니다 — contract.md timingsMs 절에 적었다. 전후 비교표를 만들 때 이 키를 같은 열에 놓으면 안 된다.

### 7. Firestore 읽기 [확인 — 코드]

- mode1 · veto ON 분석마다 prefetch 가 `get_reference_motion` 을 한 번 더 부른다 = 읽기 **최대 +3**: base doc(firestore_admin.py:2578) · `_release` 포인터(:2525) · version doc(:2585). 채점 경로의 기존 호출(:9225)은 그대로 1회.
- mode3 · veto OFF · referenceMotionId 없음: 추가 읽기 0 (테스트 [D] 와 `_reference_prefetch_wanted` 단위 테스트).
- `videoS3Key` 는 version overlay 대상(`_REFERENCE_CONSUMER_FIELDS` :2492)이 아니다 → prefetch 와 채점 경로가 다른 키를 보는 경우는 그 사이 base doc 이 바뀐 경우뿐이다. 그때는 채점 경로 키로 동기 폴백(테스트 [E]).
- Spark 5만/일 캡과의 관계는 메모리 [[firestore-spark-50k-read-cap-is-a-live-risk]] 참조. 분석 1건당 +3 이 캡 대비 작은지는 실증 분석 건수에 달렸다 [미확인 — 건수 미정].
- Firestore 클라이언트 `_db()`(firestore_admin.py:23)는 락 없는 지연 초기화다. `_process` 는 executor 를 만들기 전에 `update_analysis_status(STATUS_QUEUED)` 를 메인 스레드에서 부르므로 첫 초기화가 prefetch 스레드와 겹치지 않는다 [확인 — 코드 순서].

### 8. 테스트가 잠그는 것 [확인 — 테스트 통과]

- [A] 기준 다운로드 1회 · "gemini" 접두 스레드 · veto 가 받은 `reference_video_path` = 그 dest · `preuploaded_reference_handle` 이 세션이 그 dest 에 만든 핸들과 같은 객체(`is`) · 기준 dest 실제 업로드 1회 · stage 로그 3종 · temp 없음 · close 뒤 업로드 핸들 전부 delete.
- [B] `_build_coach_context(scene_flags=)` 가 받은 값은 scene stub 이 돌려준 sentinel 객체 자체(`is`)이고 `released_by_veto is True`.
- [C] prefetch OFF = 기준 다운로드 MainThread 1회 · scene sentinel 도달 · ref_upload 로그 · temp 없음.
- [D] mode3 = `_prefetch_reference_video` 호출 0 · 기준 다운로드 0 · ref_upload 로그 없음.
- [E] 키 불일치 = 메인이 채점 키로 동기 다운로드 · veto 는 그 dest · 두 temp 모두 없음 · 두 업로드 핸들 모두 delete.
- [F] prefetch 다운로드 실패 = gemini 스레드 시도 1회 확인 후 메인 동기 다운로드로 완주 · temp 없음.
- [G] 포즈 실패 · [H] 사이 구간 실패(STATUS_COMPARISON write) = 사건 순서 `upload_done(기준) < close < unlink(기준)` · 기준 핸들 delete · 학생/기준 temp 없음 · 예외 전파.
- 모든 통합 테스트에서 소켓 connect/DNS 시도 0 (가드로 기록 · 단언).

---

## 추정 — 승계 전 재검증 대상 (전부 [미확인])

### 기대 효과 [미확인 — Pod 실측 전]

- 기준 업로드(38-14 Pod 로그 ≈42초)는 포즈 + recognizer 그늘에 대부분 숨고 잔여 ≈10~20초, scene_finder 잔여 대기는 veto 뒤라 ≈0 으로 본다. 점수 도착 3분 40초 → ≈2분 10초~2분 40초 [추정].
- **확인 방법**: Pod 에 반영 후 38-14 의 19.9초 mode1 영상으로 전후 stage_timing 비교 — (1) `ref_upload` · `ref_video_download` · `student_upload_wait` · `scene_finder` 값 (2) `overallScore` · `deductionBreakdown` 불변 (3) Pod 로그 `grep -E "RESOURCE_EXHAUSTED|429"` 0 (4) `student_upload_wait` 가 커지지 않았는지(기준 100MB 와 대역 경합).

### 실패 경로 지연 [추정]

- 포즈 블록 · outer try 실패 시 finally 가 기준 업로드(최대 ≈42초)까지 기다린다. 지금도 같은 실패가 scene join(37~45초)을 기다렸으므로 더 길어지지 않을 것으로 본다.
- prefetch 다운로드가 실패하면 메인이 다시 동기 다운로드한다(실패 시 다운로드 2회). prefetch 업로드가 None 이면 `ref_upload` 자리에서 같은 경로를 한 번 더 동기 업로드한다(None 은 세션이 캐시하지 않는다) — 실패 시 비용 = 비동기 1회 + 동기 1회. 기존 graceful 계약이라 바꾸지 않았다.
- Pod↔S3 링크가 조용히 멎는 경우(메모리 [[pod-link-can-collapse-silently]])에는 메인이 `ref_video_download` 에서 prefetch 다운로드를 기다린다. 옛 코드도 같은 자리에서 동기 다운로드로 멎었으므로 나빠지지 않을 것으로 본다.

### 동시 호출 · 대역 [미확인]

- scene_finder 의 Gemini generate 가 이제 recognizer · veto 와 시간상 겹칠 수 있다 → 429/RESOURCE_EXHAUSTED 위험은 낮다고 보지만 Pod 실측 로그 grep 대상.
- 기준 영상 ≈100MB 다운로드+업로드가 학생 업로드와 동시에 돈다 → 학생 업로드가 느려질 수 있다. 그래서 `student_upload_wait` 를 달았다.

### 배포 단위 [미확인]

- 이 quick 은 배포하지 않았다(AWS · Pod · Lambda · sam · s3 무접촉). 운영 경로는 RunPod Pod 의 `_process` 이므로 배포 단위는 pipeline Lambda 코드가 아니라 Pod 쪽 `_process` 재적재로 보인다 — 배포 단계에서 확인할 일.

### 남은 작은 구멍 [확인 — 코드 / 영향 미확인]

- 포즈 블록 `finally:` 를 지웠으므로 포즈 블록에서 `Exception` 이 아닌 `BaseException`(KeyboardInterrupt · SystemExit)이 나면 그 자리에서 executor.shutdown 이 불리지 않는다. 기존 except 도 `Exception` 만 잡아 session.close 를 안 불렀으므로 그 경로의 정리 공백은 원래 있었고, 이번에 executor shutdown 이 그 공백에 더해졌다. Pod BackgroundTasks 에서 실제로 나는 경로인지는 미확인.

---

## Deviations from Plan

1. **[Rule 1 성격 — 슬롭 제거] `ref_upload_future` 변수를 두지 않았다.** plan (a)(b) 는 `ref_upload_future = None` 초기화와 대입을 적었지만, 소비처는 그 future 를 읽지 않고 세션 캐시(`get_or_upload` 캐시 hit/inflight)로 결과를 받는다 → 쓰기만 하는 변수가 된다. 업로드 작업은 `executor.submit(...)` 으로 제출만 하고 join 은 outer finally 의 shutdown 이 한다(주석 :9015~9016). 동작 차이 0. 커밋 9214303.
2. **[계획 허용 범위] 통합 테스트에서 `_run_deferred_coach_text` 를 no-op 으로 둠.** 소켓 가드를 달아 처음 돌렸을 때 네트워크 시도가 전부 이 사후 단계 하나(Gemini coach B → API 키 SSM 조회, `app.py _call_coach_writer_with_retry → coach_writer_v2.write → client._default_api_key_loader`)에서 나왔다(그 상태 8건 176초). 이것만 stub 했고 나머지 사후 단계는 실제 코드로 돈다(Firestore 부분 갱신은 네트워크 전에 실패 — 가드 기록 0).
3. **[계획 사실 차이] plan 은 RED 시점에 [D] 가 실패해야 한다고 적었지만 [D] 는 통과했다.** [D] 는 mode3 무변경 보호 테스트라 옛 코드에서도 기준 prefetch 가 없다 — Task 1 이 헬퍼를 먼저 만들었으므로 spy 설치도 실패하지 않는다. 대신 plan 목록에 없던 [C] 가 RED 에서 실패했다(새 `ref_upload` stage 로그 단언). RED 를 의미 있게 하려고 [E][F] 에 "prefetch 가 실제로 돌았다"(gemini 스레드 다운로드 존재) 전제 단언을 넣었다 — 이것이 없으면 [F] 는 옛 코드에서도 통과한다.
4. **[Rule 2 — 테스트 강화] 소켓 가드 fixture 추가.** plan 의 "테스트 중 네트워크 0" 을 말이 아니라 단언으로 확인하려고 `socket.socket.connect` · `connect_ex` · `socket.getaddrinfo` 를 막고 시도를 기록해 통합 테스트마다 0 을 단언한다.
5. **plan Task 3 의 pipeline 묶음은 6건 실패** — 위 "기존 실패" 절. 변경 전 커밋에서 같은 6건 재현으로 무관 판정, 고치지 않았다.

## Threat model 대응

- T-qmg-01(핸들 누수): 포즈 블록 except · outer finally 모두 shutdown 이 close 앞 — [G][H] 가 `upload_done < close` 와 기준 핸들 delete 를 잠금.
- T-qmg-02(/tmp 누수): 헬퍼가 실패 temp 즉시 정리, 불일치/미사용 temp 는 join 뒤 정리, 사이 구간 문장 이동 — [E][F][G][H] 가 파일 부재 확인.
- T-qmg-03(다른 기준 영상으로 veto): 키 대조 — [E].
- T-qmg-04(읽기 캡): accept — 관측 7.
- T-qmg-05(로그): 새 로그는 motion_id · S3 키 · analysis_id · 예외 타입 이름만. 서명 URL · 토큰 0. 예외 메시지 본문도 남기지 않는다(`type(exc).__name__`).
- T-qmg-06(교착): 제출 순서 FIFO 근거 주석 · [B] Event 대기 timeout 5초 · 5회 반복 무흔들림.

## Self-Check: PASSED

- 파일: backend/functions/pipeline/app.py · backend/tests/test_ref_prefetch_scene_join.py · docs/contract.md 존재 확인.
- 커밋: 5c5cfef · 14a06b1 · ab794ab · 9214303 · 47c5505 — `git log` 에 존재.
- `grep -c "ref_upload" docs/contract.md` = 2.
