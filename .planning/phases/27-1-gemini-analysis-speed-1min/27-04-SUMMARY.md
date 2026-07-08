---
phase: 27-1-gemini-analysis-speed-1min
plan: 04
subsystem: backend
tags: [gemini, file-api, session, inline, performance, spd-02]

# Dependency graph
requires:
  - phase: 27-03
    provides: "GeminiFileSession 코어 (업로드 1회 + 핸들 공유 + get_or_upload) + GeminiVisionCall.call preuploaded_handle 주입 경로"
  - phase: 27-01
    provides: "fake genai fixture (tests/gemini/fake_genai.py — upload/get/delete 카운터)"
provides:
  - "학생 영상 File API 업로드 분석당 1회 — scene_finder/recognizer/veto/coach B 세션 핸들 공유 (중복 4~5회 → 1회, D-04 레버)"
  - "veto still PNG inline 전송 (Part.from_bytes) — 업로드 2회+폴링+delete → 0"
  - "moment extractor self-upload 폴백 File API 누수 표면 0 (try/finally 소유-핸들 delete, 외부 리뷰 HIGH-2)"
affects: [27-05, 27-09]

# Tech tracking
tech-stack:
  added: []  # 신규 패키지 0 — google-genai 기존 핀 재사용
  patterns:
    - "어댑터 결합 최소화: 세션 객체가 아닌 핸들만 keyword-only 주입 (default None → 미주입 시 byte-동일)"
    - "coach context-확장 패턴: B3 시그니처 hard gate 로 write(self, context) 고정 → 핸들은 context['preuploadedHandle'] 로 전달 (videoPath/sceneFlags 와 동일)"
    - "still 전송 방식 전환(inline)은 픽셀 불변 → 캐시 granularity bump 불필요 (입력 형태 변경과 구분)"

key-files:
  created:
    - backend/tests/gemini/test_session_wiring.py
  modified:
    - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
    - backend/shared/python/sunity_shared/gemini/scene_finder.py
    - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/analysis/technique.py
    - backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
    - backend/shared/python/sunity_shared/gemini/file_session.py

key-decisions:
  - "coach 핸들은 context['preuploadedHandle'] 로 전달 — write(self, context) B3 hard gate(inspect.signature 정확히 self/context) 유지. 계획의 write(*, preuploaded_handle) 는 이 게이트를 깨므로 context-확장 패턴으로 대체 (Rule 1)"
  - "recognizer 는 Protocol — technique.py + gemini_technique_recognizer.py 를 열어 recognize→_call_extractor→extract_key_moments 로 핸들 스레딩 (Task 3 point 3 요구, 계획 file 목록엔 미포함 — Rule 3)"
  - "file_session.get_or_upload: client 생성 실패(키 부재/SSM 실패)를 graceful None 으로 흡수 (Rule 2) — 없으면 keyless 환경/Lambda CPU 폴백에서 _process 가 세션 생성 시점에 crash. must_have '업로드 실패 시 자체 업로드 폴백 비차단' 충족"
  - "still inline 전환은 캐시 키 불변 — 픽셀 동일(전송 방식만 변경), A6 무회귀는 27-09 EVAL18 이 최종 방어 (90d038f stale-hit 사고와 구분)"

requirements-completed: [SPD-02]

# Metrics
duration: ~90min
completed: 2026-07-08
---

# Phase 27 Plan 04: 세션 핸들 소비처 배선 + still inline Summary

**학생 영상 File API 업로드를 분석당 4~5회에서 1회로 축약했다 — scene_finder/recognizer(moment extractor)/veto/coach B 가 `GeminiFileSession` 핸들을 공유하고, veto still PNG 2장은 업로드/폴링/delete 없이 inline(`Part.from_bytes`)으로 전송하며, `_process` outer finally 가 세션 핸들을 분석당 1회 일괄 delete 한다(NoHuman/NotPole 조기 raise 포함). moment extractor 의 self-upload 폴백에는 소유-핸들 try/finally delete 를 박아 세션 밖 File API 누수 표면을 닫았다(외부 리뷰 HIGH-2). 프레임/해상도/모델 불변 — D-04 준수, 픽셀 동일.**

## Performance
- **Duration:** ~90 min
- **Tasks:** 3 (Task 1·2 TDD, Task 3 auto)
- **Files created:** 1 / **modified:** 8 (+ 테스트 stub 6 파일)

## Accomplishments
- **moment extractor (HIGH-2 fix)** — `extract_key_moments`/`_call_gemini` 에 keyword-only `preuploaded_handle` 추가. 주입 시 업로드/ACTIVE 폴링/delete 전부 skip(핸들 소유권=세션). 미주입 self-upload 폴백은 `uploaded = client.files.upload(...)` 를 try **밖**에서 바인딩하고 try(폴링~generate)/finally(`client.files.delete`)로 감싸 generate 예외·빈 응답 raise 포함 **정확히 1회** delete. upload 자체가 raise 하면 파일 미생성이라 delete 미실행·원 예외 보존(Warning 1). parse 예외는 `_call_gemini` 반환 후 발생하므로 그 시점에 파일 이미 삭제됨(누수 0).
- **scene_finder** — `find_scene_flags(..., preuploaded_handle=)` → `call.call` 전달. latency/graceful 무변경.
- **coach_writer_v2** — 핸들을 `context['preuploadedHandle']` 로 수용(B3 시그니처 hard gate 유지). retry 각 attempt 가 재업로드 없이 generate 만 반복(Pitfall 8 해소).
- **vision_scorer (veto)** — `assess_fault_context_video` 에 `preuploaded_student_handle`/`preuploaded_reference_handle` (둘 다일 때만 활성, still_* 계약 스타일). 활성 시 `_upload_video` skip + finally delete 는 자체 업로드분만(세션 소유 핸들 제외, T-27-08). still PNG 는 `_upload_image` → `_inline_image_part`(`Part.from_bytes`) inline 전송으로 업로드/폴링/delete 소멸. `uploadCount` 텔레메트리를 실제 업로드 수(세션 0 / 자체 2, still 0)로 교정.
- **pipeline `_process`** — 분석-로컬 `GeminiFileSession` 생성(lazy import, 모듈 전역 캐시 금지). 학생 영상 `get_or_upload` 1회 → scene/recognizer/veto/coach 공유. 기준 영상도 veto 직전 `get_or_upload`. outer finally 에 `session.close()`(unlink 앞, 조기 raise 경로 포함). Lambda CPU 폴백도 동일 코드 경로(분기 0). 핸들 None(업로드 실패) 시 각 모듈 자체 업로드 폴백 → 분석 비차단.
- **recognizer 스레딩** — `technique.py` Protocol + `FallbackRecognizer.recognize`(무시 수용) + `GeminiTechniqueRecognizer.recognize`→`_call_extractor`→`extract_key_moments` 로 keyword-only 핸들 전달(모두 default None → 기존 호출부 byte-동일).

## Task Commits
1. **Task 1 (RED): moment extractor 핸들 주입 + 누수 fix 실패 테스트** — `96feecf` (test, M1/M2 + upload-raise)
2. **Task 1 (GREEN): 어댑터 3종 핸들 주입 + self-upload try/finally delete** — `7f04fa2` (feat)
3. **Task 2 (RED): veto 핸들 + still inline 실패 테스트 3건** — `8931bc2` (test)
4. **Task 2 (GREEN): veto session-handle kwargs + still PNG inline** — `c2bd1e1` (feat)
5. **Task 3: `_process` 세션 배선 + outer finally close + 핸들 전달 + 통합 테스트** — `11d175f` (feat)

_TDD Task 1/2 = test(RED) → feat(GREEN). REFACTOR 불필요._

## TDD Gate Compliance
- Task 1: RED `96feecf`(3 fail — M1 TypeError·M2 delete 부재) → GREEN `7f04fa2`(4 passed).
- Task 2: RED `8931bc2`(3 fail — kwarg 미수용·inline 미적용) → GREEN `c2bd1e1`(7 passed 누계).
- Task 3: auto — 통합 테스트 2건(업로드 1회 dedupe + close delete 회계) `11d175f`.

## Deviations from Plan

### Auto-fixed / adapted

**1. [Rule 1 - Bug] coach write() 시그니처 — B3 hard gate 충돌 회피 (context-확장 패턴)**
- **Found during:** Task 1 (coach 배선)
- **Issue:** 계획은 `write(coach_context, *, preuploaded_handle=None)` 지시. 그러나 `TestB3SignatureRegression::test_signature_matches_cerebras` 가 `inspect.signature(GeminiCoachWriter.write).parameters == ["self", "context"]` 를 hard gate 로 강제(Cerebras write 와 100% 동일 — `_process` 가 두 writer 를 동일 시그니처로 호출). write 에 param 추가 시 이 게이트가 깨진다.
- **Fix:** 핸들을 `context['preuploadedHandle']` 로 전달(videoPath/sceneFlags/visionFault 와 동일한 context-확장 패턴). Cerebras 는 무시(text-only). `preuploaded_handle` 지역 변수로 grep 계약 충족.
- **Files:** coach_writer_v2.py + 파이프라인 배선 (`coach_context["preuploadedHandle"]`)
- **Committed in:** `7f04fa2`, `11d175f`

**2. [Rule 3 - Blocking] recognizer 스레딩 — technique.py + gemini_technique_recognizer.py (계획 file 목록 밖)**
- **Found during:** Task 3 (recognizer 핸들 전달)
- **Issue:** Task 3 point 3 은 "recognizer(moment extractor — preuploaded_handle kwargs 경유)" 배선을 명시하나, moment extractor 는 `GeminiTechniqueRecognizer.recognize`(Protocol) 뒤에 있어 두 파일(technique.py Protocol + FallbackRecognizer, gemini_technique_recognizer.py recognize/_call_extractor)을 열지 않으면 핸들 전달 불가. 계획 frontmatter `files_modified` 에는 미포함.
- **Fix:** 세 recognize 시그니처에 keyword-only `preuploaded_handle=None` 추가(Fallback 은 무시, Gemini 는 extract_key_moments 로 전달). default None → 기존 positional 호출 byte-동일.
- **Files:** technique.py, gemini_technique_recognizer.py
- **Committed in:** `11d175f`

**3. [Rule 2 - Missing critical] file_session.get_or_upload — client 생성 실패 graceful None**
- **Found during:** Task 3 (pipeline 통합 테스트)
- **Issue:** `session.get_or_upload` 는 `_process` try(3254) **밖**(3182)에서 호출된다. client 생성 실패(API 키 부재/SSM AccessDenied)가 `_default_client_factory` 에서 RuntimeError 로 escape 하면 `_process` 가 세션 생성 시점에 crash — keyless 환경(Lambda CPU 폴백·22개 단위 테스트) 전면 실패. get_or_upload 계약("업로드 실패 → None graceful")·must_have("자체 업로드 폴백 비차단")과 모순.
- **Fix:** `_upload_and_wait_active` 의 `client = self._get_client()` 를 try/except → log.warning + None 으로 흡수. 소비처는 자체 업로드로 폴백.
- **Files:** file_session.py
- **Committed in:** `11d175f`

**4. [Rule 3 - Blocking] 테스트 stub 시그니처 정합 (7 stub, 6 파일 — 27-01 선례)**
- **Issue:** `_call_gemini`/`extract_key_moments`/`GeminiVisionCall.call`/`recognize` 를 override 하는 기존 stub 이 default-None keyword-only 추가로 TypeError.
- **Fix:** 실 함수가 이미 수용하는 kwarg 를 stub 시그니처에 정합(무시). 로직 무변경.
- **Files:** test_gemini_moment_extractor.py, test_scene_finder.py, test_coach_writer_v2.py, test_gemini_vision_scorer.py(2 hybrid still 테스트는 inline 계약으로 갱신 — Rule 1), test_gemini_technique_recognizer.py, test_pipeline_gemini_integration.py, phase06/test_gemini_recognizer_populates_motion_id.py
- **Committed in:** 각 Task 커밋

**5. [설계 판단] 세션 생성 위치 — scene_finder 앞 (계획 "try 초입" 라인 추정 보정)**
- 계획은 "try 초입" + "outer finally 4155-4166" 로 기술하나, 실제 scene_finder 호출은 outer try(3254) **앞**(3184), outer finally 는 4227. scene_finder 를 소비처로 포함하려면 세션을 try 앞(3182)에 생성해야 함. close 는 outer finally(4227) — NoHuman/NotPole 조기 raise(try 내부) 포함 도달. 세션 생성~try 진입 사이 좁은 창(update_status/_signed_get)의 예외 시 close 미도달은 48h TTL 최후 안전망(T-27-09 mitigation 명시)이 커버.

**Total deviations:** 4 auto-fixed/adapted + 1 설계 판단. Scope creep 0 — 전부 계획 의도(핸들 공유·누수 0·비차단) 충족을 위한 필연.

## Threat Surface Scan
계획 `<threat_model>` 범위 내 — 신규 surface 없음.
- **T-27-22** (moment extractor self-upload 누수, HIGH-2): try/finally 소유-핸들 delete + Test M1/M2(정상·generate 예외·upload-raise) 기계 고정.
- **T-27-09** (세션 close 조기 raise 미도달 → 20GB 적체): outer finally 배치 + 통합 테스트(업로드 1회 + close delete 회계) + 48h TTL 최후 안전망.
- **T-27-10** (inline 전환 응답 분포 변경, A6): 픽셀 동일(전송 방식만) + 캐시 키 불변 + 27-09 EVAL18 무회귀 최종 판정(D-01).
- **T-27-11** (still PNG 바이트 로그 유출): inline 바이트 never-log 규율 유지.

## Issues Encountered
- **넓은 파이프라인 스위트 pre-existing 순서 의존 실패**([[pipeline-not-concurrency-safe-eval-serial]]): 전체 `tests/` 실패 집합은 base 와 mine 이 **IDENTICAL**(65/65, comm 양방향 empty). 격리 실행으로 진짜 regression 2 파일(test_pipeline_gemini_integration 4건·phase06/test_gemini_recognizer_populates_motion_id 2건)만 식별→stub/lambda 시그니처 정합으로 해소. body_comparison/geminic_wiring/model-constant 등은 base 격리에서도 동일 실패(pre-existing).
- `test_default_model_constant`(gemini-2.5-pro vs 기대 3.1-pro-preview) 는 pre-existing — 본 plan 무접촉.

## User Setup Required
None — 신규 패키지 0, OTA 무관(백엔드). 실 효과(업로드 4~5회 → 1회 절감)는 프로덕션 Pod 실측(27-09 EVAL18 before/after)에서 확인.

## Next Phase Readiness
- 27-05 prefetch: 좁은 락(27-03) + 세션 배선 완료로 학생 ∥ 기준 업로드 병렬 + coach∥Cerebras 동시화 수확 가능.
- 27-09 EVAL18: 인라인/핸들 공유 픽셀 동일 검증 + before/after 타이밍(veto_collect 87s 지배 레버) 최종 판정.

---
*Phase: 27-1-gemini-analysis-speed-1min*
*Completed: 2026-07-08*

## Self-Check: PASSED
- 생성 파일 존재: test_session_wiring.py, 27-04-SUMMARY.md.
- 커밋 6개 전부 존재: 96feecf(test) / 7f04fa2(feat) / 8931bc2(test) / c2bd1e1(feat) / 11d175f(feat) / f0129e2(docs).
- 스코프 게이트: `tests/gemini/ tests/test_stage_timing.py` 138 passed. 전체 `tests/` 실패 집합 = base 와 IDENTICAL (신규 실패 0).
- grep 가드 전량 통과: scene_finder preuploaded_handle=3 / coach=4 / moment=7·files.delete=1 / vision Part.from_bytes=2·preuploaded_student_handle=4 / app.py session.close()=2·get_or_upload=3.
- working tree clean (tracked 무변경).
