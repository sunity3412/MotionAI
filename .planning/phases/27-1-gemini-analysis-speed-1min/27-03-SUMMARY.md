---
phase: 27-1-gemini-analysis-speed-1min
plan: 03
subsystem: backend
tags: [gemini, file-api, session, performance, spd-02]

# Dependency graph
requires:
  - phase: 27-01
    provides: "fake genai fixture (tests/gemini/fake_genai.py — upload/get/delete 카운터 + delay_by_index)"
  - phase: 17-gemini-4-areas
    provides: "GeminiVisionCall 베이스 클라이언트 (upload/ACTIVE 폴링/delete 정본)"
provides:
  - "GeminiFileSession — 분석당 File API 업로드 1회 + 핸들 공유 + 종료 일괄 delete (D-04 레버)"
  - "get_or_upload(맵-스코프 락 + per-path in-flight dedupe, 업로드/폴링 락 밖)"
  - "GeminiVisionCall.call(video_path, *, preuploaded_handle=None) — 핸들 주입 시 업로드/폴링/delete skip"
affects: [27-04, 27-05]

# Tech tracking
tech-stack:
  added: []  # 신규 패키지 0 — google-genai 기존 핀 재사용
  patterns:
    - "좁은 락 + per-path in-flight Event: 락=맵/마커만, 업로드+폴링은 락 밖 (경로 간 병렬 보존, MEDIUM-2)"
    - "핸들 소유권 이동: call() preuploaded_handle 주입 시 finally delete skip — 세션 close()가 소유"

key-files:
  created:
    - backend/shared/python/sunity_shared/gemini/file_session.py
    - backend/tests/gemini/test_file_session.py
  modified:
    - backend/shared/python/sunity_shared/gemini/client.py

key-decisions:
  - "락 스코프 = 맵/마커만 (업로드/ACTIVE 폴링은 락 밖) — 정확성(경로당 1회)은 per-path Event 로, 경로 간 병렬은 락 협소화로 (27-05 prefetch 전제, MEDIUM-2)"
  - "None(업로드 실패)은 캐시 금지 — 재시도 여지 + in-flight 마커는 finally 로 반드시 해제(대기 스레드 기아 방지)"
  - "client.py 폴링 상수/_state_name/UploadFileConfig 폴백/ascii-safe 로직은 정본 재사용·포팅 — 신규 상수 발명 0"
  - "call() preuploaded_handle 주입 경로는 finally delete 도 skip — 이중 delete 시 후속 호출 404 (T-27-08)"

requirements-completed: [SPD-02]

# Metrics
duration: ~25min
completed: 2026-07-08
---

# Phase 27 Plan 03: GeminiFileSession 코어 (업로드 1회 + 핸들 공유) Summary

**학생/기준 영상을 분석당 File API 에 1회만 업로드하고 핸들을 전 모듈이 공유·종료 시 일괄 delete 하는 `GeminiFileSession` 을 신설하고(좁은 락 + per-path in-flight dedupe), `GeminiVisionCall.call()` 에 `preuploaded_handle` 주입 경로를 추가해 업로드/폴링/delete 를 skip 할 수 있게 했다(기본값 무변경). D-04 "파일 핸들 재사용" 레버의 코어 — 소비처 배선은 27-04.**

## Performance
- **Duration:** ~25 min
- **Tasks:** 2 (둘 다 TDD)
- **Files created:** 2 / **modified:** 1

## Accomplishments
- **GeminiFileSession (file_session.py)** — D-04 레버 구현:
  - `get_or_upload(video_path, *, mime_type)`: 캐시 hit → 즉시 반환. miss → 업로드+ACTIVE 폴링. **락=맵/마커만 보호**, 업로드/폴링(수십 초 I/O)은 **락 밖** — 서로 다른 경로(학생 ∥ 기준) 동시 업로드가 직렬화되지 않아 27-05 prefetch 수확 보존.
  - **per-path in-flight Event** (`_inflight`): 같은 경로 동시 호출 시 두 번째 스레드가 마커 wait → 첫 업로드 완료 후 재조회로 동일 핸들 수신 (이중 업로드 차단, MEDIUM-2). 마커 해제는 finally(실패 경로 포함, 대기 스레드 기아 방지).
  - `close()`/`__exit__`(예외 경로 포함): 세션 업로드분 일괄 `client.files.delete` — best-effort(delete 예외는 나머지 정리를 막지 않음). 20GB 적체(2026-07-06 실증) → RESOURCE_EXHAUSTED 방어. `gemini_vision_scorer.py:1283-1336` finally 정본 복제.
  - client.py 정본 재사용: 폴링 상수(`_FILES_PROCESSING_TIMEOUT_S`/`_FILES_POLL_INTERVAL_S`)·`_state_name`·UploadFileConfig TypeError 폴백. 한글 파일명 `_ascii_safe_path` 는 heavy 모듈(vision_scorer/numpy) import 회피 위해 로직 포팅. lazy genai import(Lambda 250MB).
- **GeminiVisionCall.call() 핸들 주입** — `call(self, video_path, *, preuploaded_handle=None)` keyword-only 확장:
  - `preuploaded_handle is not None` → Step 2(업로드)~3(폴링) + **finally delete skip**, generate 직행. 소유권=세션(주석 박제: 여기서 지우면 후속 호출 404, T-27-08).
  - 미주입 경로 diff 0 — 기존 업로드/폴링/delete 블록 무이동, byte-동일(RunPod server.py 무수정).

## Task Commits
1. **Task 1 (RED): GeminiFileSession 실패 테스트 6종** — `cb3c0f1` (test)
2. **Task 1 (GREEN): file_session.py 구현** — `61bd135` (feat)
3. **Task 2 (RED): preuploaded_handle 실패 테스트 2종** — `9fd7976` (test)
4. **Task 2 (GREEN): client.py 핸들 주입 경로** — `fde6aac` (feat)

_TDD Task 1/2 = test(RED) → feat(GREEN). REFACTOR 불필요 (포팅·감싸기라 정리할 잔여 0)._

## TDD Gate Compliance
- Task 1: RED `cb3c0f1`(test, 6종 import 실패) → GREEN `61bd135`(feat, 7 passed).
- Task 2: RED `9fd7976`(test 7 TypeError) → GREEN `fde6aac`(feat, 126 passed). Test 8(회귀 가드)은 RED 시점에 이미 green(기본 경로 무변경 확인) — 정상.

## Files Created/Modified
- `backend/shared/python/sunity_shared/gemini/file_session.py` (신규, 248줄) — GeminiFileSession + `_default_client_factory`/`_ascii_safe_path`
- `backend/tests/gemini/test_file_session.py` (신규) — 8 behavior (upload-once/일괄 delete/예외 경로/실패 graceful/delete best-effort/동시 dedupe/핸들 주입 skip/미주입 회귀)
- `backend/shared/python/sunity_shared/gemini/client.py` — `call()` 시그니처에 `preuploaded_handle` keyword-only 추가 + 주입 분기(업로드/폴링/delete skip)

## Deviations from Plan
None - 계획대로 실행. 신규 패키지 0, scope creep 0.

**세부 설계 판단(계획 범위 내):**
- `_ascii_safe_path` 를 vision_scorer 에서 import 하지 않고 로직 포팅 — vision_scorer 는 numpy 등 heavy 의존을 top-level import 하므로, 세션 모듈이 그걸 끌어오면 Lambda 250MB/import 비용 증가. 계획의 "로직 포팅" 지시와 정합.
- `_get_client()` 를 `_lock` 으로 가드 — 서로 다른 경로가 동시에 첫 업로드에 진입할 때 client_factory 이중 호출(Client 2개 생성) 방지. get_or_upload 는 업로드 전 락을 해제하므로 중첩 데드락 없음.

## Threat Surface Scan
계획 `<threat_model>` 범위 내 — 신규 surface 없음. T-27-06(누수/20GB)·T-27-08(이중 delete)·T-27-21(동시 업로드 경쟁)은 각각 Test 2/3/5, Test 7, Test 6 으로 기계 고정.

## Issues Encountered
- **넓은 파이프라인 스위트의 pre-existing 순서 의존 실패**(module-global 싱글턴 오염, [[pipeline-not-concurrency-safe-eval-serial]])는 본 plan 범위 밖 — 본 변경은 신규 모듈 + keyword-only default None(기존 호출부 무영향)이라 파이프라인 무접촉. 판단 기준 = scoped run(`tests/gemini/` 126 passed).

## User Setup Required
None — 외부 서비스 설정 불필요(신규 패키지 0, OTA 무관 — 백엔드 코어). 소비처 배선(27-04) 전까지 프로덕션 동작 무변경.

## Next Phase Readiness
- 27-04 가 `GeminiFileSession` 을 `_process` 비전 구간에 배선(scene_finder/recognizer/veto/coach B 가 세션 핸들 공유) → 중복 업로드 4~5회 → 1회.
- 27-05 prefetch 는 좁은 락 덕에 학생 ∥ 기준 업로드 병렬 수확 가능.
- 핸들 주입 경로가 회귀 가드로 고정돼, 미배선 호출부는 기존 동작 byte-동일 유지.

---
*Phase: 27-1-gemini-analysis-speed-1min*
*Completed: 2026-07-08*

## Self-Check: PASSED
- 생성/수정 파일 3개 전부 존재 (file_session.py / test_file_session.py / client.py).
- 커밋 4개 전부 존재 (cb3c0f1 test-RED / 61bd135 feat / 9fd7976 test-RED / fde6aac feat).
- 검증: `tests/gemini/ -q` 126 passed (기준선 117 + 신규 9), test_client.py 신규 실패 0.
- grep 가드: file_session.py `files.delete`=1(≥1) / `20GB|RESOURCE_EXHAUSTED`=3(≥1) / `threading`=5(≥1) / `_inflight`=6(≥2); client.py `preuploaded_handle`=4(≥2).
