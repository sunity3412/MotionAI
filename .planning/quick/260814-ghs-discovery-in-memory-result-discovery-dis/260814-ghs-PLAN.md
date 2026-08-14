---
phase: quick-260814-ghs
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/tests/phase35/test_compare_render_stage.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/functions/pipeline/app.py
autonomous: true
requirements: [QUICK-260814-GHS]

must_haves:
  truths:
    - "운영 스테이지(_run_deferred_compare_render)가 doc result.discovery 를 조달해 렌더러에 싣는다 — 발굴 채택 정지가 재분석/재렌더에서 살아남는다"
    - "discover mp3(results/{uid}/{aid}/discover_audio_{rid}_{joint}.mp3)를 audio_dir/basename 으로 회수한다 — build_timeline 의 basename 조인 규약과 lockstep"
    - "discovery 부재 분석(절대다수)은 완전 무회귀 — freeze rid 집합·excluded·S3 다운로드 목록 불변, doc_like 에 discovery 키 없음"
    - "조용한 소실 불가: discovery 조달 실패/형상 위반/mp3 부재/렌더 미반영 — 네 경우 전부 log.warning 또는 excluded 행 중 하나로 관측 가능하며 테스트가 이를 못박는다"
    - "RED 우선: 수리 전 테스트가 실제로 실패(4 failed / 1 passed)하는 것을 실행 로그로 확인한 뒤 수리한다"
    - "채점 무접촉 + pytest 기준선 무회귀(59 failed IDENTICAL) + 프로덕션 쓰기 0 + Pod 무접촉"
  artifacts:
    - path: "backend/tests/phase35/test_compare_render_stage.py"
      provides: "운영 스테이지 레벨 discovery 회귀 5축 (조달·무회귀·읽기실패·mp3부재·미반영 회계)"
      contains: "discovery"
    - path: "backend/shared/python/sunity_shared/firestore_admin.py"
      provides: "get_analysis_discovery — update_analysis_discovery 의 read 짝 (검증 경유, 부재 = [])"
      contains: "def get_analysis_discovery"
    - path: "backend/functions/pipeline/app.py"
      provides: "_run_deferred_compare_render 발굴 조달 블록 + doc_like discovery 주입 + 미반영 회계 로그"
      contains: "discovery"
  key_links:
    - from: "backend/functions/pipeline/app.py::_run_deferred_compare_render"
      to: "firestore_admin.get_analysis_discovery"
      via: "align_quality 게이트 뒤 조달 블록 (fail-open + log.warning)"
      pattern: "get_analysis_discovery"
    - from: "_run_deferred_compare_render"
      to: "audio_dir/<basename(mp3Key)>"
      via: "_s3.download_file 항목별 비차단"
      pattern: "mp3Key"
    - from: "_run_deferred_compare_render"
      to: "compare_render.render / compare_verify.verify 의 doc_like"
      via: "_result_for_doc[\"discovery\"] 주입 (coachAudio 처방 미러)"
      pattern: "_result_for_doc"
    - from: "_run_deferred_compare_render"
      to: "report.freezes pairSrc=='discover'"
      via: "조달-반영 대조 회계 log.warning (조용한 소실 재발 차단)"
      pattern: "DISCOVERY_PAIR_SRC"
---

<objective>
di7 이 배선한 발굴 채택 freeze(`result.discovery`)가 **운영 재렌더 경로에서만 조용히 소실**되는 결함 2건을 수리한다.

- **갭 A (조용한 소실)**: `_run_deferred_compare_render` 는 `doc_like` 를 in-memory `result` 로 조립하는데(app.py:4256-4262), `result.discovery` 는 `update_analysis_discovery` 가 Firestore 단일 field-path 로만 부분 갱신하므로 in-memory 에 없다 (app.py 전체 discovery 참조 0건). → `build_timeline` 의 discovery 루프(compare_render.py:1335)가 빈 리스트를 돌아 **freeze 도 excluded 행도 안 남긴다**. 리그도 못 잡는다(H1 eligible 은 doc 의 discovery 를 보는데 그 doc 이 곧 discovery 없는 `doc_like` 라 대조가 성립조차 안 함).
- **갭 B (di7 이연 명기)**: audio_dir 적재 루프(app.py:4203-4208)가 `coach_audio_items` 전용이라 discover mp3 를 안 내려받는다 → `discover_no_mp3` excluded 행.

선례: 같은 계열 결함을 coachAudio 가 이미 당했고(app.py:4246-4255 주석 — 리그 H4 가 **운영 경로에서만** 전건 FAIL), 그 처방이 :4257-4261 이다. discovery 는 그 처방이 미적용. di7 live 검증이 못 본 이유 = 검증 드라이버가 Firestore 재fetch doc 을 넘겨서 경로가 달랐다 — "승인은 산출물이 아니라 생산 경로에 붙는다"의 재발 사례.

**핵심 차이 (설계 근거)**: coachAudio 는 "그 분석이 방금 합성한" in-memory 근거가 있지만, discovery 는 **분석 사후 belle 채택물**이라 in-memory 근거가 원리적으로 없다 → **Firestore 가 유일 진실**. 따라서 조달 소스 = (a) Firestore 읽기 (호출부 인자 전달은 무의미 — 호출부에도 없다).

Purpose: 발굴 채택 정지가 재분석/재렌더를 넘어 살아남게 하고, 실패했을 때 **반드시 보이게** 만든다 (이 사이클의 요지는 기능 복구가 아니라 침묵 제거).
Output: 스테이지 레벨 회귀 5축 + firestore_admin read 짝 + app.py 조달/주입/회계 3지점. 프로덕션 쓰기 0.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/quick/260814-di7-s3-doc-freeze-discover/260814-di7-SUMMARY.md

수리 지점 (읽기 전 이 좌표를 그대로 쓸 것 — 재탐색 금지):
- `backend/functions/pipeline/app.py`
  - `_run_deferred_compare_render` 정의 :4120, 본체 :4184-4355
  - audio_dir 적재 루프 :4198-4208 (coach mp3 전용, 파일명 계약 = `r{NN}.mp3`)
  - align_quality 게이트 종료 :4234-4240
  - doc_like 조립 + coachAudio 재조립 선례 :4242-4262
  - render 호출 :4264-4272 / report.json 기록 :4273-4277
  - freeze 전멸 스킵 :4279-4289 (**조기 return** — 회계 로그는 이 앞이어야 한다)
  - 리그 verify :4291-4295 (doc=doc_like)
  - 호출부 :7986-8001
- `backend/shared/python/sunity_shared/analysis/compare_render.py`
  - discovery 주입 레이어 :1322-1378 (`(r.get("discovery") or {}).get("items")`, mp3 = `audio_dir/basename(mp3Key)`, 부재 = `discover_no_mp3` excluded)
  - `build_timeline(doc, audio_dir, moments=None, align=None, poles=None, ...)` :1119, `r = doc["result"]` :1138
  - `mp3_duration_s` :115 — **ffmpeg 파싱 실패 시 RuntimeError** (가짜 mp3 바이트 금지)
  - report freeze 스키마 :1708 (`rid`/`userSec`/`refSec`/`pairSrc`/…)
- `backend/shared/python/sunity_shared/firestore_admin.py`
  - `_validate_discovery` :1649 / `update_analysis_discovery` :1724 (단일 field-path 통째 교체) / `get_analysis` :2205
- `backend/shared/python/sunity_shared/analysis/compare_verify.py`
  - H1 eligible = record rid ∪ discovery rid, accounted = freezes ∪ excluded :244-268 (**excluded 행이 있으면 H1 은 여전히 PASS** — mp3 부재가 리그를 깨지 않는다)
  - H2/H3/H4 discover 분기 :273-285 / :312-327 / :351-364 (`_discovery_item_for` 공유, fail-closed)
- `backend/tests/phase35/test_compare_render_stage.py` — 스테이지 하네스 정본: `papp` :96, `FakeS3` :104, `rc_updates` :122, `stage_env` :140
- `backend/tests/phase35/test_discovery_freeze.py` — build_timeline 레벨은 di7 이 이미 핀함(`_silence_mp3` :100 = ffmpeg anullsrc 1s, `_disc_item` :89). **같은 층 재작성 금지 — 이번은 스테이지 층만.**
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: RED — 운영 스테이지 discovery 회귀 5축 작성 + 실패 재현</name>
  <files>backend/tests/phase35/test_compare_render_stage.py</files>
  <behavior>
    파일 말미에 새 섹션 `# ═══ 6. 발굴 discovery 조달 + mp3 회수 (quick-260814-ghs) ═══` 추가. 전부 합성 값(실좌표/동작명/실 분석 ID 리터럴 0 — di7 규율 승계).

    공용 하네스 (새로 정의):
    - `_SILENCE_MP3` — 모듈 레벨 lazy 캐시. `compare_render.FF` 로 `-f lavfi -i anullsrc -t 1` 을 tmp 에 굽고 bytes 로 읽는다 (`mp3_duration_s` 가 ffmpeg 파싱이라 **진짜 mp3 바이트 필수** — `b"ID3fake"` 는 RuntimeError).
    - `_disc_item(**over)` — `{rid:"r07", joint:"left_elbow", userSec:3.2, refSec:2.9, pairSrc:"discover", text:<합성 문장>, mp3Key: build_discover_audio_key(UID, ANALYSIS_ID, "r07", "left_elbow"), adoptedAt:"2026-01-01"}`. **joint 은 left_elbow** — knee 의 `_body_line_viz` 경로는 di7 이 build_timeline 층에서 이미 핀했고, 여기서는 조달·조인만 대상이라 표면을 좁힌다. rid 는 records 에 없는 신규 rid(마커 경로 회피 + 신규 발굴 케이스 커버).
    - `disc_env(stage_env, monkeypatch)` fixture — stage_env 위에 4가지를 덮어쓴다:
      1. `papp._s3 = FakeS3(mp3_bytes=_SILENCE_MP3)` (다운로드 파일이 실 mp3 가 되도록)
      2. `result.deductionBreakdown.records[0]` 에 `cueLine`/`statusLine` 추가 (실 `build_timeline` 이 `coach_audio_speech_text` 를 부른다 — 없으면 예외). `stage_env["kwargs"]` 를 얕은 복사해 덮어쓰고 원본 fixture 는 무접촉.
      3. `compare_render.render` → `_timeline_render` 스텁: **실 `compare_render.build_timeline(doc, Path(audio_dir), None, align_json, None)`** 를 호출하고, 산출 freezes/excluded 로 report 를 조립해 반환 (`{"outDurationS":9.0, "userDurationS":9.0, "expectedFreezes":len(freezes), "freezes":[{"rid":f["rid"],"userSec":f["ut"],"refSec":f["rt"],"pairSrc":f["pair_src"],"freezeS":f["dur"],"voiceStartOutS":1.0,"text":f["text"]} …], "excludedFreezes":excluded}`), out 경로에 가짜 mp4 바이트 기록. `captured` dict 에 `doc`/`freezes`/`excluded`/`align` 보관 — 이 스텁이 "운영 스테이지가 렌더러에 무엇을 넘겼는가"를 재는 계측기다.
      4. `compare_verify.verify` 캡처 래퍼 — `doc` kwarg 를 `captured["verify_doc"]` 에 저장하고 `(True, ["  [PASS] all"])` 반환.
      반환: `{"captured":…, "s3":…, "kwargs":…}`
    - discovery 조달 소스는 **`firestore_admin.get_analysis` monkeypatch** 로 심는다 (수리 구현이 이 함수 위에 얹히는 계약 — Task 2 가 지킨다). 반환 형상 = `{"result": {"discovery": {"items": [item]}}}`.

    5축 테스트:
    - (a) `test_stage_procures_discovery_and_renders_discover_freeze` — get_analysis 가 discovery 1건 보유 doc 반환.
      · `captured["doc"]["result"]["discovery"]["items"]` == 조달 item 1건 (갭 A)
      · `captured["freezes"]` 에 `pair_src == models.DISCOVERY_PAIR_SRC` 1건, rid/ut/rt/text 가 item 과 일치
      · `s3.downloads` 에 `mp3Key` 가 있고 목적지 basename == `discover_audio_r07_left_elbow.mp3` (갭 B)
      · `captured["excluded"] == []`
      · `rc_updates[-1]["status"] == done` 이고 freezes payload 에 `r07` 포함
      · `compare_verify.authenticity_checks(report, captured["doc"], captured["align"])` 결과 중 **이름에 `[discover]` 가 든 항목 전부 PASS** (fail-closed 리그가 운영 조립 doc 를 받아들인다는 증명 — record 축은 align 형상 의존이라 대상에서 제외)
    - (b) `test_stage_without_discovery_no_regression` — get_analysis 가 `{"result": {}}` 반환.
      · freeze rid 집합 == `{"r00"}` 정확, `excluded == []`
      · `"discovery" not in captured["doc"]["result"]`
      · `s3.downloads` 키 집합 == coach mp3 1건 정확 (여분 GET 0)
      · `rc_updates[-1]["status"] == done`
      ※ 이 축은 RED 에서도 PASS 하는 것이 정상 — 수리 후에도 PASS 여야 무회귀 증명이다.
    - (c) `test_stage_discovery_read_failure_is_fail_open_with_warning` — get_analysis 가 예외 raise.
      · 렌더 진행 + `rc_updates[-1]["status"] == done` (fail-open — 발굴 없는 절대다수를 깨지 않는다)
      · `caplog` 에 WARNING 1건 이상이며 메시지에 `discovery` 포함 (침묵 금지)
    - (d) `test_stage_discover_mp3_missing_leaves_excluded_row_and_warning` — FakeS3.download_file 이 키에 `discover_audio` 포함 시 raise.
      · `captured["excluded"]` 에 `{"rid":"r07","reason":"discover_no_mp3"}` 존재
      · `captured["freezes"]` 에 discover 0건, 그러나 record freeze `r00` 은 생존 → `rc_updates[-1]["status"] == done` (전체 렌더 비차단)
      · `caplog` WARNING 에 `mp3Key` 또는 rid 흔적
    - (e) `test_stage_warns_when_procured_discovery_not_rendered` — 조달은 성공하지만 render 스텁이 discover freeze 를 빼고 반환(미래 회귀 시뮬).
      · `caplog` WARNING 에 미반영 rid `r07` 이 찍힌다 (조달-반영 대조 회계 = 이 사이클의 흔적 게이트)
      · 스테이지는 계속 진행해 `done` (회계는 관측이지 차단이 아니다)

    caplog 은 `caplog.set_level(logging.WARNING)` 로 루트 로거 대상 (app.py `log = logging.getLogger()`).
  </behavior>
  <action>
위 behavior 대로 테스트만 작성한다. **운영 코드 수정 금지** (이 태스크에서 app.py / firestore_admin.py 무접촉 — RED 를 눈으로 확인하는 것이 목적).

파일 상단 docstring 에 이번 섹션의 대상(운영 스테이지 층 — build_timeline 층은 test_discovery_freeze 소유)과 조용한 소실 결함 요지를 2~3줄 추가한다. import 는 기존 블록에 `logging`, `models` 의 `DISCOVERY_PAIR_SRC` 사용, `build_discover_audio_key`, `compare_verify.authenticity_checks` 만 보강.

RED 실행 후 결과를 SUMMARY 에 인용할 수 있게 실패 라인을 그대로 남길 것. 기대 = (a)/(c)/(d)/(e) FAIL, (b) PASS. **(b) 가 FAIL 하면 하네스 자체가 틀린 것이니 수리 전에 하네스를 고친다** — 무회귀 축이 못 서면 나머지 판정이 무의미하다.

커밋: `test(quick-260814-ghs): 운영 스테이지 discovery 조달 회귀 5축 (RED)`
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/phase35/test_compare_render_stage.py -k "discovery or discover" 2>&1 | tail -30</automated>
  </verify>
  <done>5개 수집, 정확히 4 failed / 1 passed (passed = 무회귀 축 (b)). 실패 사유가 전부 "discover freeze/조달/경고 부재"이며 AttributeError·ImportError·ffmpeg 오류 같은 하네스 결함이 0건.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: GREEN — discovery 조달 + mp3 회수 + 미반영 회계</name>
  <files>backend/shared/python/sunity_shared/firestore_admin.py, backend/functions/pipeline/app.py</files>
  <behavior>
    Task 1 의 5축이 전부 PASS 한다. 그 외 phase35 기존 테스트 전건 무회귀.
  </behavior>
  <action>
**(A) `firestore_admin.py` — read 짝 신설.** `update_analysis_discovery` 바로 뒤(:1751 부근)에 `get_analysis_discovery(uid: str, analysis_id: str) -> list[dict]` 추가:

- 본문 = `data = get_analysis(uid, analysis_id) or {}` → `payload = (data.get("result") or {}).get("discovery")` → `payload is None` 이면 `[]` 반환 → 아니면 `_validate_discovery(payload)` 통과시킨 뒤 `list(payload.get("items") or [])` 반환.
- **형상 위반은 raise** (caller 가 graceful 처리 — validator 를 여기서 삼키면 침묵이 다시 생긴다).
- docstring: `update_analysis_discovery` 의 read 짝이며, 발굴은 **분석 사후 채택물이라 in-memory 근거가 없고 Firestore 가 유일 진실**임을 명기. 신규 SDK 표면(field projection)을 쓰지 않고 검증된 `get_analysis` 위에 얹는 이유 = analysis doc 은 Firestore 1 MiB 상한이라 전체 읽기 비용이 유계이고, 프로젝션 도입은 별건 최적화. `get_analysis` 가 파일 뒤(:2205)에 정의되지만 모듈 전역이 호출 시점에 해석되므로 배치는 무해 — 이 주석을 남길 것.

**(B) `app.py::_run_deferred_compare_render` — 3지점.**

1. **조달 블록** — align_quality 게이트 종료(:4240 `return` 뒤) ~ doc_like 조립(:4242) **사이**에 삽입. (게이트 스킵 경로에서 Firestore/S3 헛호출 0. audio_dir 적재가 두 곳으로 갈리므로 :4200 코치 mp3 루프 주석에 "발굴 discover mp3 는 align 게이트 뒤 조달 블록에서 같은 디렉터리로" 한 줄 포인터를 추가한다.)
   - `discovery_items: list[dict] = []` → `try: discovery_items = firestore_admin.get_analysis_discovery(uid, analysis_id)` / `except Exception:` 는 `log.warning("compare_render discovery 조달 실패 — 발굴 정지 없이 진행 uid=%s analysis_id=%s", uid, analysis_id, exc_info=True)` 후 `discovery_items = []` (**fail-open**: 부재/읽기실패/형상위반 전부 기존 동작 유지, 단 흔적은 남긴다).
   - 항목별 mp3 회수: `key = it.get("mp3Key")` 가 비-str/빈값이면 skip, 아니면 `dst = audio_dir / key.rsplit("/", 1)[-1]` 로 `_s3.download_file(bucket, key, str(dst))`. **항목별 try/except 로 비차단** — 실패는 `log.warning("compare_render discover mp3 회수 실패 rid=%s key=%s — discover_no_mp3 로 흘림", …)` 후 continue (그 항목만 build_timeline 의 `discover_no_mp3` excluded 행이 된다).
   - 성립 시 `log.info("compare_render discovery 조달 n=%d rids=%s analysis_id=%s", …)`.
   - 주석에 근거 3줄: coachAudio 처방(:4246-4255)과 같은 계열이되 **조달 소스가 다른 이유**(사후 채택물 = in-memory 근거 없음), basename 조인 규약이 `s3keys.build_discover_audio_key` 단일 출처라는 점, di7 이 이연했던 mp3 회수분이라는 점.

2. **doc_like 주입** — :4256 `_result_for_doc = {**result, "keypointReport": keypoint_report_dict}` 아래, coachAudio 블록과 나란히:
   `if discovery_items and "discovery" not in _result_for_doc: _result_for_doc["discovery"] = {"items": [dict(it) for it in discovery_items]}`
   (형상은 `models.DISCOVERY_KEYS` 계약 그대로. 이 한 줄이 갭 A 의 실수리이고, render 와 verify 가 **같은 doc_like** 를 받으므로 di7 의 H1~H4 discover fail-closed 의미론이 운영 경로에서 처음으로 실제 활성화된다 — 이 사실을 주석에 명기.)

3. **미반영 회계 로그** — report.json 기록(:4277) **뒤**, freeze 전멸 조기 return(:4279) **앞**:
   - `rendered = {str(fz.get("rid")) for fz in report.get("freezes") or [] if fz.get("pairSrc") == models.DISCOVERY_PAIR_SRC}`
   - `missing = [str(it.get("rid")) for it in discovery_items if str(it.get("rid")) not in rendered]`
   - `missing` 이 비지 않으면 `log.warning("compare_render discovery 미반영 rids=%s excluded=%s analysis_id=%s", missing, [e.get("rid") for e in report.get("excludedFreezes") or []], analysis_id)`
   - 주석: 갭 A 의 본질은 실패가 안 보인 것이었다 — 원인이 무엇이든(조인 실패·경계 핀·미래 회귀) 조달분이 렌더에 안 들어가면 **반드시 한 줄이 남는다**. 차단이 아니라 관측. 배치가 전멸 return 앞이어야 하는 이유(전멸 시에도 로그가 남아야 함)도 함께.

**금지**: 산식 5파일(deduction_engine/dimensions/kismam/motiondtw/temporal/features/assemble) 무접촉, `complete_analysis` 무접촉, 프로덕션 쓰기 0, 실 분석 ID·uid·동작명 리터럴 0(일반 경로 — belle "다른 영상들도 이런식으로"), 이모지 0, heredoc 파일 생성 0.

커밋: `fix(quick-260814-ghs): 운영 재렌더 discovery 조달 + discover mp3 회수 + 미반영 회계`
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/phase35 2>&1 | tail -15</automated>
  </verify>
  <done>phase35 전건 PASS (신규 5축 포함, 기존 실패 0). `rtk grep -n "get_analysis_discovery\|discovery" backend/functions/pipeline/app.py` 가 조달·주입·회계 3지점을 전부 보여준다.</done>
</task>

<task type="auto">
  <name>Task 3: 게이트 — pytest 기준선 · 산식 무접촉 · push</name>
  <files>없음 (검증 + push 전용)</files>
  <action>
1. **pytest 기준선**: `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests` — 기존 실패군이 늘지 않을 것. 기준선 = di7 시점 `59 failed / 4205 passed`. 기대 = **59 failed IDENTICAL**, passed = 4205 + 신규 5 = 4210 (신규 테스트 수가 다르면 실수만큼 조정해 보고). failed 수가 59 를 넘으면 즉시 중단하고 원인 보고 — 통과 조작 금지.
2. **산식 무접촉**: `rtk git diff af9cff96..HEAD --stat -- backend/shared/python/sunity_shared/analysis/dimensions.py backend/shared/python/sunity_shared/analysis/kismam.py backend/shared/python/sunity_shared/analysis/motiondtw.py backend/shared/python/sunity_shared/analysis/temporal.py backend/shared/python/sunity_shared/analysis/features.py backend/shared/python/sunity_shared/analysis/assemble.py backend/shared/python/sunity_shared/analysis/deduction_engine.py` → **빈 출력**.
3. **일반 경로 grep**: `rtk git diff af9cff96..HEAD -- backend/ | rtk grep -in "pdshape\|p34fresh\|peterpan\|powerspin\|kipup"` → 매치 0 (합성 fixture 만).
4. **compare_render/compare_verify 무접촉 확인**: 이번 사이클은 스테이지+read 짝만 고쳤다 — `rtk git diff af9cff96..HEAD --stat -- backend/shared/python/sunity_shared/analysis/compare_render.py backend/shared/python/sunity_shared/analysis/compare_verify.py` 가 빈 출력이면 di7 의 fail-closed 의미론 무손상이 구조로 증명된다. 만약 부득이 수정이 들어갔다면 SUMMARY 에 이유와 함께 정직 박제.
5. **프로덕션 쓰기 0 확인**: 이번 태스크들에서 S3 put / Firestore update 를 실행한 적이 없음을 명시 (테스트는 FakeS3 + monkeypatch).
6. `rtk git push` → `origin/main..HEAD` delta 0 확인.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -5 && git diff af9cff96..HEAD --stat -- backend/shared/python/sunity_shared/analysis/dimensions.py backend/shared/python/sunity_shared/analysis/kismam.py backend/shared/python/sunity_shared/analysis/motiondtw.py backend/shared/python/sunity_shared/analysis/temporal.py backend/shared/python/sunity_shared/analysis/features.py backend/shared/python/sunity_shared/analysis/assemble.py backend/shared/python/sunity_shared/analysis/deduction_engine.py && echo "SANSIK-DIFF-EMPTY-OK" && git log origin/main..HEAD --oneline | wc -l</automated>
  </verify>
  <done>pytest 59 failed IDENTICAL · 산식 diff 빈 출력 · 동작명 리터럴 0 · push 후 origin delta 0.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore doc → 렌더 스테이지 | 사후 채택물 `result.discovery` 가 렌더 입력으로 승격 — 형상/내용은 서버 validator 만이 보증 |
| S3 discover mp3 → audio_dir | basename 조인이라 파일명이 렌더 대상 결정에 관여 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ghs-01 | Tampering | `get_analysis_discovery` 반환 payload | mitigate | `_validate_discovery` 강제 통과 (키 화이트리스트·pairSrc enum·mp3Key prefix/suffix·중복 거부) — 위반 = raise → 스테이지 fail-open + WARNING |
| T-ghs-02 | Spoofing | 렌더 리포트의 discover freeze | mitigate | di7 H2/H3/H4 fail-closed 유지 (`_discovery_item_for` 매칭 필수). 이번 변경은 doc 공급만 — verify 코드 무접촉이 구조 보증 (Task 3 게이트 4) |
| T-ghs-03 | Denial of Service | 조달 실패가 전체 렌더 차단 | mitigate | 조달 예외·항목별 mp3 실패 전부 비차단 fail-open — 발굴 없는 절대다수 분석 무영향 (테스트 (b)/(c)/(d) 가 핀) |
| T-ghs-04 | Repudiation | 조용한 소실 재발 | mitigate | 조달-반영 대조 회계 log.warning + `discover_no_mp3` excluded 행 — 네 실패 경로 전부 관측 가능, 테스트 (c)/(d)/(e) 가 못박음 |
| T-ghs-05 | Information Disclosure | 로그에 uid/analysis_id 노출 | accept | 기존 스테이지 로그 규약과 동일 (PII 아님, CloudWatch 30일 보존) |
| T-ghs-SC | Tampering | 패키지 설치 | n/a | 신규 의존성 0 — 설치 태스크 없음 |
</threat_model>

<verification>
1. RED 실행 로그가 실제로 존재하는가 (4 failed / 1 passed) — 수리 전 커밋이 남아 있는가.
2. `captured["doc"]["result"]["discovery"]` 로 **운영 조립 doc** 에 discovery 가 실렸음을 직접 확인 (코드 통과가 아니라 산출물 확인).
3. discovery 부재 경로가 S3 GET 여분 0 · freeze rid 집합 불변으로 무회귀인가.
4. 네 실패 경로(읽기 실패 / 형상 위반 / mp3 부재 / 렌더 미반영) 각각이 WARNING 또는 excluded 행 중 하나를 남기는가 — 테스트가 이를 강제하는가.
5. compare_render.py / compare_verify.py diff 0 (di7 fail-closed 의미론 무손상).
6. 산식 diff 0 · pytest 59 failed IDENTICAL · 프로덕션 쓰기 0 · Pod 무접촉.
</verification>

<success_criteria>
- RED → GREEN 순서가 커밋 이력으로 증명된다 (test 커밋이 fix 커밋보다 앞).
- 5축 전건 PASS + phase35 전건 PASS + pytest 기준선 59 failed IDENTICAL.
- 산식 5파일 + compare_render/compare_verify diff 빈 출력.
- push 완료 (origin delta 0).
- SUMMARY 에 **다음 1단계** 명기: 새 Pod 실증 사이클(운영 `_run_deferred_compare_render` 가 실제 discovery 보유 doc 을 재렌더 → `[discover]` 실행 로그 + 카드/영상 실물) — 스코프 밖이므로 사양과 함께 belle 에게 Pod 요청(GPU 모델 명시).
</success_criteria>

<output>
Create `.planning/quick/260814-ghs-discovery-in-memory-result-discovery-dis/260814-ghs-SUMMARY.md` when done.

SUMMARY 에 반드시 포함:
- RED 실패 라인 원문 인용 (조용한 소실이 재현됐다는 증거)
- 조달 소스 설계 결정과 근거 (Firestore 유일 진실 / `get_analysis` 위 구현 / 프로젝션 미도입 이유)
- 네 실패 경로의 흔적 수단 표 (경로 → WARNING or excluded)
- pytest 기준선 대조 수치 + 산식/compare_* diff 게이트 결과
- LLM 학습 영향 (이번 사이클 추론 호출 0 예상 — 실제와 다르면 실측 기재)
</output>
