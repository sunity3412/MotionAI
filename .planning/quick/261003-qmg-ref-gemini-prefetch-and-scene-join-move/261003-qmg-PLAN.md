---
phase: quick-261003-qmg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/functions/pipeline/app.py
  - backend/tests/test_ref_prefetch_scene_join.py
  - docs/contract.md
autonomous: true
requirements: [QUICK-261003-qmg]

must_haves:
  truths:
    - "mode1 + veto ON + prefetch ON 이면 기준 영상의 S3 다운로드와 Gemini 업로드가 학생 영상 다운로드 직후(포즈 전) 백그라운드로 시작되고, 분석당 각각 정확히 1회만 일어난다 — :9358 자리는 다운로드를 건너뛰고 prefetch 파일을 쓰며, :9507 의 get_or_upload 는 세션 캐시 hit 또는 진행 중 업로드 대기로 끝난다"
    - "prefetch ON 이면 scene_finder 결과는 veto_collect 뒤 `_build_coach_context` 직전에서만 join 된다 — recognizer · DTW · veto 가 scene_finder 를 기다리지 않고, `_build_coach_context(scene_flags=)` 에 닿는 값은 scene_finder 가 돌려준 바로 그 객체다"
    - "GEMINI_UPLOAD_PREFETCH=0 이면 지금 동기 경로와 같다 — 기준 영상은 :9358 에서 동기 다운로드, :9507 에서 동기 업로드, scene_finder 는 recognizer 앞에서 동기 호출"
    - "mode3 이거나 veto OFF 이거나 referenceMotionId 가 없으면 기준 영상 prefetch 가 없다 — 추가 Firestore 읽기 0, 추가 S3 다운로드 0"
    - "prefetch 가 key 불일치 · 다운로드 실패 · 업로드 실패여도 분석은 기존 동기 폴백으로 계속되고, 쓰이지 않은 prefetch 임시 파일은 분석 끝에 지워진다"
    - "어디서 실패하든(포즈 블록 · 포즈 블록과 outer try 사이 · outer try 안) 순서는 executor join → session.close → 임시 파일 unlink 이다 — 늦게 끝난 기준 업로드 핸들도 close 에서 지워진다(Gemini 저장소 누수 0, /tmp 누수 0)"
    - "채점 입력 무변경 — 채점 경로의 `get_reference_motion`(:9054) · DTW · veto 입력 · 판정 순서는 그대로이고, veto 에 넘어가는 기준 영상은 채점 경로가 읽은 ref doc 의 videoS3Key 와 같은 키의 바이트다"
    - "timingsMs 에 `ref_upload`(mode1 에서만) 가 생겨, 지금 어느 stage 에도 안 잡히던 ≈42초 자리가 계측된다"
  artifacts:
    - path: "backend/functions/pipeline/app.py"
      provides: "기준 영상 prefetch 헬퍼 5개 + _process 배선(ref prefetch submit · scene join 이동 · executor 수명 연장 · 정리 순서) + ref_upload/ref_video_download/student_upload_wait stage"
      contains: "def _prefetch_reference_video"
    - path: "backend/tests/test_ref_prefetch_scene_join.py"
      provides: "헬퍼 단위 테스트 + _process 통합 테스트(prefetch on/off, mode1/mode3, key 불일치, prefetch 실패, 조기 실패/사이 구간 실패 정리 순서, scene join 위치)"
      min_lines: 250
    - path: "docs/contract.md"
      provides: "timingsMs 예시 키에 새 stage 3개 + scene_finder 의미 변화 한 줄"
      contains: "ref_upload"
  key_links:
    - from: "_process prefetch 블록 (:8843 if executor is not None)"
      to: "_prefetch_reference_video / _upload_prefetched_reference"
      via: "executor.submit — 학생 업로드 · scene 다음 순서로 제출(FIFO)"
      pattern: "executor\\.submit\\(\\s*_prefetch_reference_video"
    - from: "_process 기준 영상 확보 자리 (:9361 if _gemini_vision_veto_enabled())"
      to: "_take_prefetched_reference_path"
      via: "ref[\"videoS3Key\"] 와 prefetch key 대조"
      pattern: "_take_prefetched_reference_path\\(ref_prefetch_future"
    - from: "_process outer finally (:10428)"
      to: "executor.shutdown(wait=True)"
      via: "session.close() 보다 앞"
      pattern: "executor\\.shutdown\\(wait=True\\)"
    - from: "scene_future.result()"
      to: "_build_coach_context(scene_flags=scene_result)"
      via: "veto_collect stage 뒤 · coach_context 대입 직전"
      pattern: "scene_future\\.result\\(\\)"
---

<objective>
mode1 분석의 점수까지 시간을 줄인다(3분 40초 → 목표 2분대 [미확인 — Pod 실측 전]). 두 군데만 고친다:
(1) 기준 영상의 Gemini File API 업로드(+ACTIVE 폴링, ≈42초, 지금 어느 stage 에도 안 잡힘)를 학생 영상 다운로드 직후 백그라운드로 미리 시작한다.
(2) scene_finder join 을 recognizer 앞(37~45초 대기)에서 첫 소비처 `_build_coach_context` 직전으로 옮긴다.
채점 입력 · 판정 순서는 무변경. 배포 안 함 — 코드와 테스트까지.

Purpose: belle 10-02 "분석을 줄이기 위해 갖은 애를 썼는데 왜 또" — 점수 도착 시간 단축이 실증(2026-10 중순) 전 체감 문제.
Output: pipeline `app.py` 수정, 새 테스트 파일 1개, contract.md timingsMs 절 한 줄.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@backend/shared/python/sunity_shared/gemini/file_session.py
@backend/tests/test_stage_timing.py
@backend/tests/pipeline/test_pipeline_phase9.py

근거 문서 (읽기 전용):
- 메모리 /Users/kimtaesung/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/analysis-time-reference-gemini-reupload-42s.md
- Pod 로그 .planning/phases/38-supplier-link/evidence/runpod_server_38_14_1002.log

app.py 에서 읽을 범위(전체 10k+ 줄 — 이 범위만): :150~190(`_stage` · `_s3_download`), :500~541(`_gemini_upload_prefetch_enabled` · `_safe_unlink_local_video`), :602~638(`_call_wave1_scene_finder`), :8746~9060(`_process` 앞부분 — 포즈 블록 · 사이 구간 · outer try 시작), :9354~9383(기준 영상 다운로드), :9497~9558(ref 업로드 · veto_collect · coach context), :10428~10446(outer finally).

<planner_facts>
관측 — 플래너가 코드/명령으로 확인한 것. 실행기는 착수 즉시 줄 번호만 재대조(줄은 밀릴 수 있다):

- [확인] 포즈 블록 = `try:`(:8842) / `except Exception:`(:8920, shutdown → 학생 temp unlink → session.close → raise) / `finally:`(:8936, `executor.shutdown(wait=True)`). outer try = `try:`(:9020) / `finally:`(:10428) — outer try 에 `except` 절은 없다(:8746~10447 범위 4칸 들여쓰기 try/except/finally 는 이 5개뿐, grep).
- [확인] 포즈 블록과 outer try 사이(:8945~9019)에서 예외를 낼 수 있는 문장은 3개: `firestore_admin.update_analysis_status(uid, analysis_id, models.STATUS_COMPARISON)`(:8961), `my_video_url = _signed_get(bucket, key)`(:8964), `target_torso = _extract_target_torso_px(pose_frames)`(:9018). 나머지는 `_record_unregistered_with_uid` 정의와 순수 변수 초기화뿐. 지금 이 3개 중 하나가 raise 하면 session.close 도 학생 temp unlink 도 안 불린다(기존 결함).
- [확인] outer try 안에는 top-level `return` 이 없다(grep) — outer finally 는 성공 · 실패 모두 도달한다.
- [확인] `scene_result` 의 소비처는 전부 :9542(`_build_coach_context(scene_flags=)`) 이후(:10043 · :10109 · :10135 · :10277). :8919~:9542 사이 소비 0(오케스트레이터 grep 과 일치).
- [확인] `_build_coach_context(` 호출은 _process 안에 1곳(:9537), `_collect_vision_fault_context(` 호출도 1곳(:9512). 새 헬퍼 이름(`_prefetch_reference_video` 등)과 겹치는 기존 이름 0.
- [확인] `GeminiFileSession.get_or_upload` 는 예외를 밖으로 내지 않는다(실패 = None, CR-01) · None 은 캐시하지 않는다 · 같은 경로 동시 호출은 inflight Event 대기 · 다른 경로는 락 밖 병렬(file_session.py:96~135, 158~202). `close()` 는 그 시점 `_handles` 만 지운다(:273~293) → close 뒤에 끝난 업로드 핸들은 누수.
- [확인] `firestore_admin.get_reference_motion` 은 읽기 최대 3회(base doc :2578 · `_release` 포인터 :2525 · version doc :2585). `videoS3Key` 는 version overlay 대상(`_REFERENCE_CONSUMER_FIELDS` :2492)이 아니다 → videoS3Key 는 항상 base doc 값. prefetch 와 채점 경로가 다른 키를 보는 경우는 그 사이 base doc 이 바뀐 경우뿐.
- [확인] `_call_wave1_scene_finder` 는 모든 예외를 흡수해 None 을 돌려준다(:623~638). scene_finder.py 에 `global` 문 0.
- [확인] contract.md:747~763 timingsMs 절은 단계 키를 "예시(비고정 — 키 추가는 비파괴)" 로 적고 목록을 둔다. analysis.ts:1075~1079 는 `Record<string, number>`, 키 자유 — TS · models.py 변경 불필요.
- [확인] 기존 테스트 중 GEMINI_UPLOAD_PREFETCH · scene_future · executor 를 다루는 것은 test_stage_timing.py 1개(grep). `cd backend && .venv/bin/python -m pytest tests/test_stage_timing.py tests/pipeline/test_pipeline_phase9.py -q` = 9 passed(플래너 실행).
- [확인] Task 2 verify 의 awk 게이트(scene join 위치)를 지금 코드에 돌리면 veto_collect=9511 · scene_future.result()=8913 · coach=9537 → exit 1(이동 전이라 실패가 맞다, 플래너 실행).
- [확인] 테스트는 `backend/` 를 cwd 로 돌린다(conftest 가 shared/python · scripts · 리포 루트를 sys.path 에 넣는다). 가짜 genai 는 tests/gemini/fake_genai.py 에 있다(단 FakeFiles 카운터는 락이 없다 — 스레드 테스트에는 아래 기록용 세션을 쓴다).
- 오케스트레이터 제공(재측정 안 함): backend 전체 2026-10-02 기준 5910 passed / 20 skipped 근처.

교착 판단 — 플래너 판단 [코드 근거]:
- executor 에 넣는 작업 4개, 제출 순서 = (1)학생 업로드 (2)scene((1)을 기다림) (3)기준 다운로드 (4)기준 업로드((3)을 기다림). 기다리는 작업은 언제나 자기보다 먼저 제출된 future 만 기다린다. ThreadPoolExecutor 작업 큐는 FIFO 라, 기다리는 쪽이 일을 시작했다면 기다림을 받는 쪽은 이미 다른 스레드에서 돌고 있거나 끝났다 → 워커 수가 1 이상이면 교착 없음. max_workers=4 = 작업 4개라 넷이 동시에 돈다 → 4 그대로 둔다.

추정 — 승계 전 재검증 대상, 전부 [미확인]:
- 기대 효과: 기준 업로드는 포즈+recognizer 그늘에 대부분 숨고(잔여 ≈10~20초 [추정]), scene_finder 잔여 대기는 veto 뒤라 ≈0 [추정]. 점수까지 ≈2분 10초~2분 40초 [미확인 — Pod 실측만이 답].
- 실패 경로 지연: 포즈 블록/outer try 실패 시 finally 가 기준 업로드(최대 ≈42초)까지 기다린다. 지금도 같은 실패가 scene join(37~45초)을 기다리므로 더 길어지지 않을 것 [추정].
- 대역 경합: 100MB 기준 영상 다운로드+업로드가 학생 업로드와 동시에 돈다 → 학생 업로드가 느려질 수 있다 [미확인]. 그래서 `student_upload_wait` stage 를 단다(Task 2 — 플래너 재량).
- Gemini 동시 호출: scene_finder generate 가 이제 recognizer · veto 와 시간상 겹칠 수 있다 → 429/RESOURCE_EXHAUSTED 위험은 낮다고 보지만 [미확인], Pod 실측 때 로그 grep 대상.
- 업로드 실패 재시도: prefetch 업로드가 None 이면 :9507 이 같은 경로를 한 번 더 동기 업로드한다(None 비캐시). 실패 시 비용 = 비동기 1회 + 동기 1회. 기존 graceful 계약 그대로라 바꾸지 않는다.
</planner_facts>

<interfaces>
새 모듈 수준 헬퍼 계약 (Task 1 이 만들고 Task 2 가 소비. 위치 = app.py `_safe_unlink_local_video`(:521) 바로 뒤):

- `_reference_prefetch_wanted(mode: str | None, ref_motion_id: object) -> bool` — `mode == models.MODE_EXPERT and bool(ref_motion_id) and _gemini_vision_veto_enabled()`.
- `_prefetch_reference_video(bucket: str, motion_id: object) -> tuple[str, str] | None` — executor 스레드에서 돈다. `firestore_admin.get_reference_motion(motion_id)` → doc 없음/`videoS3Key` 없음 = None(다운로드 0). 있으면 기존 :9364~9370 과 같은 방식(`os.path.splitext(key)[1] or ".mp4"` 접미사, `tempfile.NamedTemporaryFile(suffix=..., delete=False)` → close → `_s3_download(bucket, key, tmp.name)`)으로 받아 `(key, tmp.name)` 반환. 어떤 예외든 log.warning(구조 로그, 비밀 0) + 만든 temp 는 `_safe_unlink_local_video` + None. 절대 raise 하지 않는다.
- `_upload_prefetched_reference(session: Any, download_future: Future | None) -> Any | None` — executor 스레드에서 돈다. `download_future.result()`(예외 → None) 가 None 이면 None, 아니면 `session.get_or_upload(path)` 반환. 절대 raise 하지 않는다.
- `_take_prefetched_reference_path(download_future: Future | None, expected_key: str) -> str | None` — 메인 스레드. future None → None. `.result()` 로 기다린다(예외 → log.warning + None). 결과 None → None. 결과 key == expected_key → path. 불일치 → log.warning(두 키) + None. 불일치여도 파일을 지우지 않는다 — 업로드 future 가 아직 그 파일을 읽고 있을 수 있다(WR-02 선례: future 생존 중 unlink 0). 정리는 join 뒤 finally.
- `_prefetched_reference_temp_path(download_future: Future | None) -> str | None` — 정리 전용, executor join 뒤에만 부른다. future None 또는 `not future.done()` → None. 성공 결과면 path, 결과 None 이거나 예외면 None. 기다리지 않고 raise 하지 않는다.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 기준 영상 prefetch 헬퍼 5개 + 단위 테스트</name>
  <files>backend/functions/pipeline/app.py, backend/tests/test_ref_prefetch_scene_join.py</files>
  <behavior>
    - `_reference_prefetch_wanted`: mode1 + veto ON + id 있음 → True / veto OFF(GEMINI_VISION_VETO_ENABLED 미설정) → False / mode3 → False / id None 또는 "" → False
    - `_prefetch_reference_video` 정상: ref doc `videoS3Key="reference/ref-x/v1.mov"` → `_s3_download(bucket, key, dest)` 1회, 반환 `(key, dest)`, dest 는 `.mov` 로 끝나고 존재
    - `_prefetch_reference_video` doc None · `videoS3Key` 없음/None → None, `_s3_download` 호출 0
    - `_prefetch_reference_video` `get_reference_motion` raise → None (raise 안 함)
    - `_prefetch_reference_video` `_s3_download` raise → None, 그때 넘겨받은 dest 파일이 남아 있지 않다
    - `_upload_prefetched_reference`: 결과 `(key, path)` future → `session.get_or_upload(path)` 1회, 그 핸들 반환 / 결과 None future → None, session 호출 0 / 예외 future → None
    - `_take_prefetched_reference_path`: key 일치 → path / 불일치 → None 이고 파일은 그대로 존재 / future None → None / 결과 None → None / 예외 future → None
    - `_prefetched_reference_temp_path`: 성공 future → path / future None → None / 미완료 future → None(기다리지 않음) / 예외 future → None
  </behavior>
  <action>
RED 먼저: 새 파일 backend/tests/test_ref_prefetch_scene_join.py 를 만들고 위 behavior 를 테스트로 쓴다. import 관례는 test_stage_timing.py:27~35 와 같다(pipeline · shared 경로 주입 뒤 `import app`). future 는 스레드 없이 `concurrent.futures.Future()` 에 `set_result` / `set_exception` 으로 만든다. `firestore_admin.get_reference_motion` · `app._s3_download` 는 monkeypatch, veto 토글은 `GEMINI_VISION_VETO_ENABLED` setenv/delenv. 실제 S3 · Firestore · Gemini 호출 0. 파일 상단 docstring 에 목적과 근거(quick-261003-qmg, 메모리 analysis-time-reference-gemini-reupload-42s)를 한국어로. 이 시점에 실행하면 AttributeError 로 실패해야 한다.

GREEN: app.py `_safe_unlink_local_video`(:521~540) 바로 뒤에 <interfaces> 의 헬퍼 5개를 그 계약 그대로 추가한다. 블록 위에 왜 주석(한국어): 기준 영상(v1 ≈100MB)을 매 분석 veto 직전에 새로 올리던 ≈42초(38-14 Pod 로그 관측)를 포즈 그늘로 옮기는 장치 · 분석-로컬 executor 에서만 부른다(모듈 전역 캐시 금지 원칙 — 분석 간 핸들 재사용은 하지 않는다) · 실패는 전부 None 이고 소비처는 기존 동기 경로로 폴백 · 불일치 temp 를 바로 지우지 않는 이유(WR-02). Future 타입 힌트는 `concurrent.futures.Future` 를 쓰고 이미 import 된 것이 있으면 재사용한다(새 패키지 0, 새 top-level import 는 표준 라이브러리만). 로그는 `%s` lazy 포맷 key=value(구조 로그 관례), 서명 URL · 비밀 기록 금지. 이모지 금지.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_ref_prefetch_scene_join.py -q</automated>
  </verify>
  <done>헬퍼 5개가 계약대로 있고 단위 테스트 전부 통과. 헬퍼는 어떤 입력에도 raise 하지 않는다(예외 future · 다운로드 실패 케이스가 테스트로 잠김). _process 는 아직 무변경.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: _process 배선 — 기준 prefetch 제출 · scene join 이동 · executor 수명 연장 · 정리 순서 + 통합 테스트</name>
  <files>backend/functions/pipeline/app.py, backend/tests/test_ref_prefetch_scene_join.py</files>
  <behavior>
    - [A] prefetch ON · mode1 · veto ON: `_s3_download` 는 기준 키로 정확히 1회, "gemini" 접두 스레드에서. `_collect_vision_fault_context` 가 받은 `reference_video_path` = 그 dest, `preuploaded_reference_handle` = 세션이 그 dest 에 대해 만든 핸들. 기준 dest 실제 업로드 1회(:9507 은 캐시 hit/inflight). 로그에 `stage=ref_upload` · `stage=ref_video_download` · `stage=student_upload_wait`. 분석 뒤 기준 temp 없음, close 에서 업로드 핸들 전부 delete
    - [B] scene join 위치: prefetch ON 에서 scene_finder stub 이 "veto 시작" Event 를 최대 5초 기다렸다가 `{"released_by_veto": event.is_set(), ...}` sentinel 을 돌려준다 → `_build_coach_context` 가 받은 `scene_flags` 는 그 sentinel 객체 자체(`is`)이고 `released_by_veto is True`(옛 코드면 recognizer 앞 join 이라 False — 이 테스트가 이동을 잠근다)
    - [C] prefetch OFF(GEMINI_UPLOAD_PREFETCH=0) · mode1 · veto ON: `_s3_download` 기준 키 1회, MainThread 에서. scene sentinel(대기 없는 stub)이 `_build_coach_context` 에 그대로 도달. `stage=ref_upload` 로그 있음. 기준 dest 업로드 1회. 분석 뒤 temp 없음
    - [D] mode3 · prefetch ON · veto ON: `_prefetch_reference_video` 호출 0(spy), 기준 키 `_s3_download` 0, `stage=ref_upload` 로그 없음, scene sentinel 은 `_build_coach_context` 에 도달
    - [E] key 불일치: gemini 스레드의 `get_reference_motion` 은 키 A, 메인 스레드는 키 B 를 돌려준다(스레드 이름으로 분기 — 순서 경쟁 없음) → 메인이 B 를 동기 다운로드, veto 는 B dest 를 받는다, 분석 뒤 A · B dest 둘 다 없음, A · B 업로드 핸들 둘 다 close 에서 delete
    - [F] prefetch 다운로드 실패: gemini 스레드의 `_s3_download` 만 raise → 메인 동기 다운로드로 계속, veto 는 메인 dest 를 받는다, 분석 완료(complete_analysis 1회), 남은 temp 없음
    - [G] 포즈 블록 조기 실패: 포즈 stub 이 RuntimeError, 기준 업로드는 0.3초 걸리게 → `_process` 가 RuntimeError 를 그대로 올리고, 사건 순서 = 기준 업로드 완료 < session.close < 기준 prefetch temp unlink, 기준 핸들이 delete 목록에 있다, 학생 temp · 기준 temp 둘 다 없음
    - [H] 사이 구간 실패: `update_analysis_status` 가 STATUS_COMPARISON 일 때만 raise(기준 업로드 0.3초) → 예외 전파, 순서 = 기준 업로드 완료 < close < 기준 temp unlink, 기준 핸들 delete, 학생 temp · 기준 temp 없음(옛 코드면 close 미호출로 실패)
  </behavior>
  <action>
RED 먼저 — 같은 테스트 파일에 [A]~[H] 통합 테스트를 추가한다. 하네스는 test_pipeline_phase9.py 의 `_import_pipeline` · env 리셋 fixture(:142~155) · `_stub_extract_inputs` 모양(:93~127)을 따른다(포즈 stub 은 tmp_path 에 실제 학생 파일을 쓰고 그 경로를 돌려준다 — unlink 검증용). 세션은 `sunity_shared.gemini.file_session.GeminiFileSession` 속성을 monkeypatch 해 기록용 하위 클래스로 바꾼다(_process 가 함수 안에서 import 하므로 속성 교체가 먹는다). 하위 클래스는 진짜 GeminiFileSession 의 락 · inflight · close 로직을 그대로 쓰고, `_upload_and_wait_active` 만 바꿔 (경로별 지연 → 공유 사건 목록에 ("upload_done", path) 기록 → `SimpleNamespace(name="files/" + basename)` 반환), `__init__` 에서 `self._client` 를 delete 를 기록하는 가짜로 채워 close 가 실제로 delete 경로를 타게 하고, `close` 는 ("close",) 를 기록한 뒤 부모 close 를 부른다. 기록 목록은 `threading.Lock` 으로 보호한다. `app._safe_unlink_local_video` 는 ("unlink", path) 를 기록한 뒤 원본을 부르는 래퍼로 바꾼다. 그 밖의 stub: firestore_admin(get_analysis · update_analysis_status · get_reference_motion — 60x8 각도 doc 에 `videoS3Key` · get_active_reference_release → None · get_previous_analysis → None · complete_analysis MagicMock), `app._s3_download`(dest 에 바이트를 쓰고 (key, dest, 스레드 이름) 기록), `app._signed_get`, `app._ensure_adapters`, `app._COACH_WRITER`, `app._call_wave1_scene_finder`(sentinel), `app._collect_vision_fault_context`(kwargs 기록 + Event set + None 반환), `app._apply_vision_veto`(result 그대로 반환), `app._build_coach_context`(원본을 감싼 spy). veto ON 으로 열리는 사후 단계(`_run_deferred_*`)나 다른 Firestore 쓰기가 네트워크를 건드리면 그만큼만 no-op stub 을 추가한다 — 테스트 중 네트워크 0, Event 대기는 반드시 timeout 을 둔다. 이 시점에 [A][B][D][E][F][G][H] 는 실패해야 한다.

GREEN — app.py `_process` 를 아래 순서로 고친다. 모든 변경 블록 위에 왜 주석(한국어, `quick-261003-qmg` 인용, 관측 수치는 38-14 Pod 로그 출처와 함께). 채점 경로(`get_reference_motion` :9054 · recognizer · DTW · `_collect_vision_fault_context` 인자 · `_apply_vision_veto`)는 손대지 않는다.
(a) `student_handle_future = None` 옆(:8840~8841)에 `ref_prefetch_future = None`, `ref_upload_future = None`, `scene_result: dict | None = None` 을 둔다. :8827~8833 주석의 "기준 영상 prefetch 는 27-05 범위 밖" 문장을 이번 변경으로 고친다.
(b) `if executor is not None:` 블록에서 `scene_future = executor.submit(_scene_prefetch)` 뒤 · 제출 마커 log.info 앞에, `_reference_prefetch_wanted(mode, ref_motion_id)` 이면 `ref_prefetch_future = executor.submit(_prefetch_reference_video, bucket, ref_motion_id)` 다음 `ref_upload_future = executor.submit(_upload_prefetched_reference, session, ref_prefetch_future)` 를 제출한다. 제출 순서와 max_workers=4 근거(<planner_facts> 교착 판단)를 주석에 남긴다. 워커 수는 바꾸지 않는다.
(c) 학생 핸들 join if/else(:8901~8906)를 `with _stage(timings_ms, analysis_id, "student_upload_wait"):` 로 감싼다(플래너 재량 — 동작 무변경 계측. 기준 100MB 가 학생 업로드와 대역을 나눠 쓰게 되므로, 학생 업로드가 느려지면 그것이 또 어느 stage 에도 안 잡히는 시간이 되는 것을 막는다).
(d) 포즈 블록의 scene join(:8911~8919): prefetch 경로(scene_future 있음)는 여기서 join 하지 않는다. `if scene_future is None:` 일 때만 지금처럼 `with _stage(..., "scene_finder"):` 안에서 `_call_wave1_scene_finder(...)` 동기 호출(동기라 겹칠 것이 없어 위치 유지).
(e) 포즈 블록 `except Exception:`(:8920~8935) 순서를 executor.shutdown(wait=True) → session.close()(기존 try/except 그대로) → 학생 temp unlink(기존 줄) → `_safe_unlink_local_video(_prefetched_reference_temp_path(ref_prefetch_future))` → raise 로 맞춘다(close 를 학생 unlink 앞으로 — outer finally 와 같은 순서). 포즈 블록 `finally:`(:8936~8943)의 shutdown 은 지운다 — 남겨 두면 성공 경로가 scene · 기준 업로드를 여기서 다 기다려 이동 효과가 0 이 된다. 그 자리 주석에 executor 수명이 outer finally 까지 늘어났다고 적는다.
(f) 사이 구간: `update_analysis_status(..., STATUS_COMPARISON)`(:8961) · `my_video_url = _signed_get(bucket, key)`(:8964) · `target_torso = _extract_target_torso_px(pose_frames)`(:9018) 세 문장을 같은 상대 순서로 outer `try:`(:9020) 본문 맨 앞으로 옮긴다. 넘어가는 것은 순수 정의/대입뿐이라 관측 가능한 순서 변화 0. 이로써 포즈 블록과 outer try 사이에는 raise 할 문장이 남지 않고, 그 구간 실패도 outer finally 정리를 탄다(지금은 session.close 미호출 — 기존 결함을 같이 막는다). `reference_local_video_path` 등 outer finally 가 읽는 변수 초기화는 try 밖에 그대로 둔다.
(g) 기준 영상 확보(:9361 `if _gemini_vision_veto_enabled():` 안): 전체를 `with _stage(timings_ms, analysis_id, "ref_video_download"):` 로 감싸고, 먼저 `_take_prefetched_reference_path(ref_prefetch_future, ref["videoS3Key"])` 를 부른다. path 면 `reference_local_video_path` 에 대입하고 log.info(prefetch 사용), None 이면 기존 동기 다운로드 블록(:9362~9382)을 내용 그대로 else 아래로 들여 실행한다.
(h) 기준 업로드(:9506~9510): `reference_local_video_path` 가 있을 때만 `with _stage(timings_ms, analysis_id, "ref_upload"):` 안에서 `session.get_or_upload(reference_local_video_path)`, 없으면 None(mode3 에 ref_upload 키가 안 생기게). 호출 자체는 그대로 — prefetch 면 캐시 hit/inflight 대기, 아니면 지금과 같은 동기 업로드라 이 stage 가 그 ≈42초를 처음으로 보이게 한다.
(i) `coach_context = _build_coach_context(`(:9537) 바로 앞에 `if scene_future is not None:` → `with _stage(timings_ms, analysis_id, "scene_finder"):` 안에서 `scene_result = scene_future.result()`. 주석: 첫 소비처 직전 join, 이 경로의 scene_finder stage 는 잔여 대기만 잰다. 주석 문장에 `scene_future.result()` 문자열을 그대로 쓰지 않는다(아래 awk 게이트는 주석 줄을 건너뛰지만 줄 중간 주석은 못 거른다).
(j) outer finally(:10428) 맨 앞에 `if executor is not None: executor.shutdown(wait=True)` — 반드시 `session.close()` 보다 앞(close 는 그 시점 핸들만 지운다, file_session.py:273). 그 뒤 기존 session.close · 학생 unlink · `reference_local_video_path` unlink, 마지막에 `_safe_unlink_local_video(_prefetched_reference_temp_path(ref_prefetch_future))`(일치 시 같은 경로 — missing_ok 라 무해, 불일치 시 쓰이지 않은 temp 정리).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_ref_prefetch_scene_join.py tests/test_stage_timing.py tests/pipeline/test_pipeline_phase9.py -q && awk '!/^[[:space:]]*#/ && /_stage\(timings_ms, analysis_id, "veto_collect"\)/{v=NR} !/^[[:space:]]*#/ && /scene_future\.result\(\)/{s=NR;n++} !/^[[:space:]]*#/ && /coach_context = _build_coach_context\(/{c=NR} END{exit !(n==1 && v<s && s<c)}' functions/pipeline/app.py</automated>
  </verify>
  <done>[A]~[H] 통합 테스트 통과 + test_stage_timing(prefetch submit 이 rtmw 로그보다 먼저) · phase9 무회귀. 코드상 scene join 은 1곳이고 veto_collect 와 coach context 사이에 있다(awk 게이트). 포즈 블록 finally 의 shutdown 은 없고, outer finally 에서 shutdown 이 session.close 앞에 있다.</done>
</task>

<task type="auto">
  <name>Task 3: contract.md timingsMs 절 갱신 + backend 전체 무회귀</name>
  <files>docs/contract.md</files>
  <action>
docs/contract.md timingsMs 절(:747~763)의 "단계 키는 예시" 목록에 `student_upload_wait`, `ref_video_download`, `ref_upload` 를 넣고, 바로 아래 한 줄을 더한다: quick-261003-qmg 부터 `scene_finder` 는 prefetch ON 이면 첫 소비처(코칭 컨텍스트) 직전의 잔여 대기, OFF 면 동기 호출 전체를 잰다 — 이 변경 전후 doc 의 scene_finder 값은 같은 물건이 아니다. 형식(`Record<string, number>`)은 그대로라 app/src/types/analysis.ts 와 models.py 는 고치지 않는다(키 자유 — analysis.ts:1075~1079 주석 확인, SUMMARY 에 그렇게 적는다).

그다음 회귀: pipeline 관련 묶음(tests/test_ref_prefetch_scene_join.py · tests/test_stage_timing.py · tests/pipeline · tests/phase06 · tests/test_pipeline_*.py · tests/gemini · tests/test_runpod_server.py · tests/test_analysis_provenance.py · tests/test_self_score_hook.py)을 먼저 돌리고, 이어 backend 전체를 돌린다(오래 걸리면 백그라운드). 기준선(5910 passed / 20 skipped 근처, 오케스트레이터 제공) 대비 실패가 생기면 이번 변경 때문인지 먼저 가른다 — 이번 변경과 무관한 기존 실패면 고치지 말고 SUMMARY 에 이름만 적는다. 수치는 실제 실행 출력의 마지막 줄을 그대로 옮긴다(추정 수치 금지).

SUMMARY 에 반드시 넣을 것(관측 절과 추정 절을 나눠서 — CLAUDE.md 보고 규칙): (1) 바꾼 자리 줄 번호와 무엇을 안 바꿨는지(채점 경로 · veto 설정 · 기준 영상 축소 · 분석 간 핸들 캐시 · 사후 단계 · 배포 · template.yaml 전부 0) (2) Firestore 읽기: veto ON mode1 분석마다 prefetch 가 `get_reference_motion` 을 한 번 더 부른다 = 읽기 최대 +3(base · `_release` 포인터 · version doc, firestore_admin.py:2578/2525/2585) — 메모리 firestore-spark-50k-read-cap-is-a-live-risk 언급 (3) `scene_finder` stage 의미 변화 (4) 새 stage 3개와 각각 무엇을 재는지 (5) 기대 효과는 [미확인] 으로만 — 확인 방법 = Pod 에 배포 후 같은 영상(38-14 의 19.9초 mode1 영상)으로 전후 stage_timing 비교 + 점수(overallScore · deductionBreakdown) 불변 + Pod 로그 grep `RESOURCE_EXHAUSTED|429` 0 + `student_upload_wait` 가 커지지 않았는지 (6) 실패 경로 지연 추정과 업로드 실패 시 재시도 비용(<planner_facts> 추정 절) (7) 이 quick 은 배포하지 않았다 — 배포 단위는 pipeline Lambda 코드가 아니라 Pod 쪽 `_process` 재적재(운영 경로 = RunPod)라는 점은 배포 단계에서 확인할 일로 [미확인] 표시.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && grep -c "ref_upload" docs/contract.md && cd backend && .venv/bin/python -m pytest tests -q -p no:cacheprovider 2>&1 | tail -3</automated>
  </verify>
  <done>contract.md timingsMs 절에 새 키 3개와 scene_finder 의미 한 줄. backend 전체 pytest 가 기준선 + 새 테스트 수만큼 통과(실패 0, 또는 이번 변경과 무관한 기존 실패만 이름과 함께 SUMMARY 기록). SUMMARY 가 위 7항목을 관측/추정 분리해 담는다.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Pod/Lambda → Gemini File API | 분석 영상(학생 · 기준)을 외부 저장소에 올린다 — 지우지 않으면 프로젝트 저장 한도(≈20GB) 적체 |
| Pod/Lambda → S3 / Firestore | 기준 doc 읽기 · 기준 영상 다운로드 — 내부 자원, 새 쓰기 0 |
| executor 스레드 ↔ 메인 스레드 | 임시 파일 · 세션 핸들 수명을 두 스레드가 공유 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-qmg-01 | Denial of Service | Gemini 업로드 핸들 누수(close 뒤 끝난 기준 업로드) | mitigate | 포즈 블록 except 와 outer finally 모두 `executor.shutdown(wait=True)` 를 `session.close()` 앞에 둔다. 테스트 [G][H] 가 "업로드 완료 < close" 순서와 기준 핸들 delete 를 잠근다 |
| T-qmg-02 | Denial of Service | /tmp 기준 영상 임시 파일(≈100MB) 누수 | mitigate | prefetch 실패 temp 는 헬퍼가 즉시, 불일치/미사용 temp 는 join 뒤 `_prefetched_reference_temp_path` 로 정리. 사이 구간 문장을 outer try 로 옮겨 그 구간 실패도 정리. 테스트 [E][F][G][H] 가 분석 뒤 파일 부재를 확인 |
| T-qmg-03 | Tampering (무결성) | 다른 기준 영상으로 veto | mitigate | 메인이 채점 경로의 `ref["videoS3Key"]` 와 prefetch key 를 대조해 같을 때만 사용, 다르면 기존 동기 다운로드. 테스트 [E] |
| T-qmg-04 | Denial of Service | Firestore Spark 읽기 캡(5만/일) | accept | mode1 · veto ON 분석당 읽기 최대 +3. 실증 규모에서 캡 대비 작다 [추정] — SUMMARY 에 수치와 메모리 링크 |
| T-qmg-05 | Information Disclosure | 로그 | mitigate | 새 로그는 analysis_id · S3 키 · 단계명만(기존 로그와 같은 수준), 서명 URL · 토큰 기록 0 |
| T-qmg-06 | Denial of Service | executor 교착 | mitigate | 기다리는 작업은 먼저 제출된 future 만 기다린다(FIFO) — 워커 수 무관 교착 없음. 테스트 [B] Event 대기는 timeout 5초 |
</threat_model>

<verification>
- `cd backend && .venv/bin/python -m pytest tests/test_ref_prefetch_scene_join.py tests/test_stage_timing.py tests/pipeline/test_pipeline_phase9.py -q` 전부 통과.
- scene join 위치 awk 게이트(Task 2 verify) exit 0 — `scene_future.result()` 코드 1곳, veto_collect stage 와 `coach_context = _build_coach_context(` 사이.
- backend 전체 pytest 무회귀(기준선 5910 passed / 20 skipped 근처 + 새 테스트).
- `git diff --stat` 대상 파일이 app.py · 새 테스트 · contract.md 3개뿐 — template.yaml · runpod_inference · shared/python · app/ 무변경.
- Pod/Lambda 배포 0, AWS 쓰기 0.
</verification>

<success_criteria>
- mode1 · veto ON · prefetch ON 에서 기준 영상 다운로드와 Gemini 업로드가 포즈 전에 시작되고 분석당 1회씩만 일어난다(테스트 [A]).
- scene_finder 결과는 veto 뒤 첫 소비처 직전에서 join 되고 같은 값이 코칭 컨텍스트에 닿는다(테스트 [B] · awk 게이트).
- prefetch OFF · mode3 · veto OFF 는 지금 동작 그대로(테스트 [C][D] · `_reference_prefetch_wanted` 단위 테스트).
- 어떤 실패에서도 join → close → unlink 순서, 누수 0(테스트 [E]~[H]).
- timingsMs 에 `ref_upload` 등 새 stage 가 생기고 contract.md 에 적혀 있다.
- 채점 경로 코드 무변경, 배포 0.
</success_criteria>

<output>
Create `.planning/quick/261003-qmg-ref-gemini-prefetch-and-scene-join-move/261003-qmg-SUMMARY.md` when done. 코드 커밋은 태스크별로 하고, SUMMARY · STATE · 메모리 갱신과 그 커밋은 오케스트레이터가 한다.
</output>
