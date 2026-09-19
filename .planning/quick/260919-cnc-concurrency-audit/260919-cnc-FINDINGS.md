# 동시 분석 오염 감사 (260919-cnc)

조사일 2026-09-19 · 대상 HEAD `76c305ea` · 코드 정적 조사만. Pod 미기동, 실행 실측 0건.
구분 표기: **[코드]** = 파일을 열어 확인한 사실 · **[실측]** = 리포에 남은 로그/증거 파일 수치 · **[미확인]** = 안 쟀다.

---

## 1. 판정 한 줄

**오염 경로 있다.** 모듈 전역 recognizer 싱글턴 1개에 분석별 값을 쓰고 수십 초 뒤에 읽는
자리가 3군데 있고, 그 중 2군데는 **채점에 직접 닿는다**. 실패가 아니라 다른 동작 기준으로
채점된 숫자가 나온다.

---

## 2. 확정 오염 경로

세 경로 모두 같은 물건을 공유한다: `backend/functions/pipeline/app.py:249`
`_RECOGNIZER: technique.TechniqueRecognizer | None = None` — 프로세스에 1개인 모듈 전역.
`_process` 는 이것을 로컬 이름 `recognizer` 로 받아(app.py:7800) **속성에 분석별 값을 쓴다.**

기계 검사로 못을 박았다: `functions/pipeline/app.py` 전체를 AST 로 훑어 함수 안에서
로컬 이름의 속성에 대입하는 자리를 전수로 뽑으면 **정확히 2건**이고 둘 다 `_process` 안의
`recognizer` 다 (7847, 7986). 아래 A-2 는 그 recognizer 가 들고 있는 extractor 쪽이다.

### A-1. `recognizer.motion_query_hint` — 채점에 닿는다

| 항목 | 내용 |
|---|---|
| 쓰는 곳 | `backend/functions/pipeline/app.py:7846-7851` (`_process` 안) |
| 읽는 곳 | `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py:300` `motion_query = self.motion_query_hint or "auto"` |
| 읽기를 유발하는 호출 | `backend/functions/pipeline/app.py:8042` `recognizer.recognize(...)` → `recognize()` Step 4(recognizer.py:205) → `_call_extractor`(recognizer.py:292) |
| 섞이는 값 | 동작 식별자 (mode1 이면 `referenceMotionId` 문자열, mode3 이면 `None`) |

**[코드] 쓰기→읽기 창이 분석의 가장 긴 구간을 통째로 덮는다.**
쓰기(7847)는 S3 다운로드 직후이고, 읽기를 유발하는 `recognize()`(8042)는 프레임 추출과
RTMW 포즈 추출이 **끝난 뒤**다. 그 사이에 `frame_extract` 와 `rtmw` 스테이지가 전부 들어간다.

**[실측]** `.planning/quick/260914-rot180-gpu-validation/evidence/run12_log_lines.md` 의
Pod 실행 로그:

```
런2 (warm)  frame_extract 29090ms + rtmw  22253ms  = 51.3초
런1 (cold)  frame_extract 29042ms + rtmw 147562ms  = 176.6초
```

즉 **학생 A 가 51~177초짜리 창을 열어 두고 있는 동안, 학생 B 가 업로드하면 B 가 A 의 값을
덮어쓴다.** 학원은 정의상 이 창 안에서 다음 사람이 올린다.

**깨지는 소비처 (값이 흘러가는 경로 전체):**

```
recognizer.motion_query_hint
 → motion_query                              (recognizer.py:300)
 → extract_key_moments(motion=motion_query)  (recognizer.py:302)
 → _GEMINI_PROMPT_TEMPLATE.format(motion=…)  (gemini_moment_extractor.py:437)
      ← Gemini 가 "다른 동작"의 키모먼트를 뽑는다
 → moments → _build_profile(canonical, moments)          (recognizer.py:265)
 → TechniqueProfile.joint_expectations
 → dimensions.absolute_dimension_scores(angles, profile) (app.py:8047)   ← 점수
 → assemble.lookup_motion_branch(profile.motion_id)      (app.py:8053)   ← copy branch / mode3 게이트
```

**기존 방어가 왜 못 막는가.** 이 자리에는 이미 누수 대책이 있고 회귀 테스트도 있다
(`backend/tests/phase06/test_motion_query_hint_leak.py`, WR-07). 그 대책은
"분기하지 말고 **항상** rebind" 다 — 즉 **직렬 누수**(앞 분석이 남긴 값을 뒤 분석이 상속)만
막는다. 쓰기와 읽기 사이에 **다른 스레드가 끼어드는 창**은 손대지 않았다. app.py:7838-7845
의 주석 자체가 `"module-global singleton (_RECOGNIZER) 가 SQS 메시지 / BackgroundTask 간
공유됨"` 이라고 적고 있다 — 공유는 인지됐고, 고쳐진 것은 순차 상속뿐이다.

**재현 방법 (Pod 필요).**
1. mode1 분석 A 를 올린다(기준 모션 지정, 예 `ref-foxtop`).
2. Pod 로그에 `stage_timing stage=frame_extract` 가 뜨고 `stage=recognizer` 가 뜨기 **전에**
   mode3 분석 B 를 올린다. (warm 기준 약 50초의 여유 — 실측치 위 표)
3. A 의 Firestore doc 에서 동작/`category` 를 본다. `unregistered` 이거나 B 의 동작이면 재현.
4. 통제군: 같은 A 를 단독으로 1회 더 분석해 값을 대조한다.

---

### A-2. `extractor._last_motion_name` / `_last_raw_response` — 채점에 닿는다

| 항목 | 내용 |
|---|---|
| 쓰는 곳 | `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py:325` (`self._last_motion_name = motion`), `:445` (`self._last_raw_response = text or ""`) |
| 읽는 곳 | `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py:307-309` — `getattr(self.extractor, "_last_raw_response", …)`, `getattr(self.extractor, "_last_motion_name", …)` |
| 섞이는 값 | 동작 이름 + Gemini 원문 응답 텍스트 |

**[코드] 왜 공유물인가.** `GeminiMomentExtractor` 는 `@dataclass` 이고
`_last_raw_response` / `_last_motion_name` 은 인스턴스 필드다
(gemini_moment_extractor.py:297-298). 그 인스턴스는 `GeminiTechniqueRecognizer.extractor`
(recognizer.py:153 필드, :201 lazy 생성)에 한 번 붙고, 그 recognizer 가 모듈 전역
`_RECOGNIZER` 이므로 **extractor 도 프로세스에 1개**다.

**[코드] 창이 열리는 구조.** `_call_extractor`(recognizer.py:292-310)는
`extract_key_moments()` 를 부르고 **반환된 뒤에** `getattr` 로 두 값을 읽는다.
`extract_key_moments` 는 진입 즉시 `self._last_motion_name = motion` 을 쓰고(:325),
그 다음 Gemini 왕복(`generate_content`)을 한다. 왕복 동안 다른 스레드가 같은 필드를 덮는다.

```
T_A: _last_motion_name = "ref-foxtop"   → Gemini 네트워크 대기 ────────┐
T_B:                                      _last_motion_name = "auto"  │
T_A: ←─ 응답 도착. getattr(_last_motion_name) == "auto"  ◀────────────┘
```

**[실측 주의]** run12 로그의 `stage=recognizer 103ms / 452ms` 는 이 창을 대표하지 **않는다**.
그 두 판은 `TechniqueCache` 히트라 Gemini 를 부르지 않은 경우다(recognizer.py:181-189 Step 1).
캐시 키는 영상 SHA256(technique_cache.py:42) 이라 **학생의 신규 영상은 항상 미스** — 실증에서는
반드시 Gemini 왕복이 일어난다. 왕복 길이는 **[미확인]**.

**깨지는 소비처 2개:**

1. **동작 확정** — `raw_motion_name` → `_classify_motion`(recognizer.py:241) →
   `classify_motion_name`(`gemini_motion_classifier.py:130`). 남의 이름이 등록 동작이면
   `("ref-invert", "recognized")` 처럼 **조용히 그럴듯한 다른 동작**으로 확정된다.
   mode3 의 `"auto"` 를 읽으면 alias 매치 실패 → `("auto", "unregistered")` →
   `TechniqueProfile(category="unregistered", joint_expectations={}, motion_id=None)`
   (recognizer.py:254-262) → 빈 joint_expectations 로 채점.
2. **객관성 가드** — `response_text` → `_adapter_reject_guard(...)`(recognizer.py:215).
   남의 응답 텍스트로 좌표/점수 포함 여부를 판정한다. 내 응답이 오염돼도 통과하고,
   남의 응답이 더러우면 내 분석이 예외로 죽는다.

**특기할 점.** A 는 **자기 moments + 남의 동작 이름** 조합을 갖는다
(`_build_profile(canonical, moments)`, recognizer.py:265 — `canonical` 만 오염, `moments` 는
로컬 반환값이라 자기 것). 불일치가 예외를 내지 않고 **숫자로 나온다.** 정확히
"화면을 봐도 모르는" 형태다.

**재현 방법 (Pod 필요).** A-1 과 동일한 겹치기 시나리오. 구분법: A-1 은 `motion_query`
자체가 바뀌어 **Gemini 프롬프트**가 달라지고, A-2 는 프롬프트는 맞는데 **확정 이름**만
바뀐다. 로그에 `motion_query` 와 최종 `canonical` 을 함께 찍으면 둘이 갈린다.

---

### A-3. `recognizer.unregistered_hook` — 점수는 아니다

| 항목 | 내용 |
|---|---|
| 쓰는 곳 | `backend/functions/pipeline/app.py:7978-7989` (`_process` 안, caller uid 를 클로저 기본값으로 고정) |
| 읽는 곳 | `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py:247-251` (`recognize()` 안 unregistered 분기) |
| 섞이는 값 | uid |
| 깨지는 소비처 | `firestore_admin.record_unregistered_keyword(keyword, uid=…, video_hash=…)` (`firestore_admin.py:2707`) → `term_collection.unique_users` 집계 → Phase 16 TERM-DATA-01 promotion(pending→reviewing→approved) 임계 |

**[코드]** 창은 A-1 과 같다(쓰기 7986 → 읽기는 recognize() 안). 미등록 동작 수집 원장에
**다른 학생의 uid** 가 찍힌다. app.py:7973-7977 주석이 이 필드의 용도가 정확히
`unique_users` 임계 결정임을 명시하고 있으므로, 오염은 promotion 판정을 왜곡한다.
**점수 경로는 아니다.**

---

### B. 결정론 컨텍스트가 프로세스 전역 monkeypatch — 분석마다 재진입한다

| 항목 | 내용 |
|---|---|
| 자리 | `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/ort_determinism.py:129-176` |
| 무엇 | `ort_module.InferenceSession = _patched_inference_session` 후 `finally` 에서 `original_cls` 로 원복. `original_cls` 는 **진입 시점의 현재 값**이라 중첩 진입에 안전하지 않다 |
| 프로덕션 활성 | **켜져 있다.** `backend/runpod_inference/start_server.sh` 에 `export RTMW_DETERMINISTIC=1` |

**[코드] 분석마다 재진입하는 이유.** `compare_align.build_model()`(compare_align.py:82-105)이
이 컨텍스트 안에서 새 rtmlib `Wholebody`(YOLOX+RTMW 두 세션)를 만든다. 파이프라인은
`build_align(...)` 을 `model` 인자 없이 부르고(app.py:4982-4987), `build_align` 은
`model is None` 이면 `build_model()` 을 호출한다(compare_align.py:279-281).
`_run_deferred_compare_render` 는 `_process` 안에서 도는 분석별 스테이지다.
→ **분석 1건마다 컨텍스트에 1회 진입한다.**

**깨지는 소비처.** 두 스레드가 겹치면:

```
T1 진입 : original=원본,  ort.InferenceSession=P1
T2 진입 : original=P1,    ort.InferenceSession=P2
T1 종료 : ort.InferenceSession=원본   ← 여기서 patch 가 벗겨진다
T2 가 이 시점 이후 세션 생성 → 결정론 옵션 없이 생성됨
T2 종료 : ort.InferenceSession=P1     ← patch 영구 잔류
```

T2 의 세션이 만드는 것은 `compare_align` 의 렌더 정렬이다. compare_align.py:83-92 의
docstring 이 이 컨텍스트가 없을 때 실제로 무슨 일이 났는지 적어 두었다 —
"같은 영상의 재추출이 매번 다른 정렬을 만들었다 … 리그 판정이 갈림 = 통과가 운".
**동시 실행에서 그 상태가 되살아난다.** 잔류 patch 자체는 기능적으로 결정론 ON 유지라 무해.

**채점 경로인가: 아니다.** compare_render 는 complete 이후 스테이지이고 산출은 합성 비교
mp4 다. 채점용 세션(`RTMWPoseEngine.__init__`, rtmw_engine.py:155)은 startup 워밍업
(`server.py:_warmup` → `_ensure_adapters`)에서 1회 생성되므로 정상 운영에선 이 창에 안 걸린다.
단 워밍업이 실패하면 C 로 연결된다.

**[미확인]** 두 분석의 compare_render 구간이 실제로 겹치는 빈도는 안 쟀다.

---

### C. `_ensure_adapters()` 는 락이 없다 (조건부·낮음)

**[코드]** `backend/functions/pipeline/app.py:1337-1370`. `_ensure_recognizer`(1229)는
`_RECOGNIZER_LOCK` 으로 double-checked locking 을 하는데 `_ensure_adapters` 에는 보호가 없다.
정상 운영에선 `server.py` startup `_warmup()` 이 요청 전에 먼저 돌아 무해하다.
워밍업이 실패하면(그 경로는 예외를 삼키고 `"워밍업 실패 — 첫 요청 처리 시 재시도"` 만 남긴다,
server.py:261) 첫 동시 2건이 RTMW 엔진을 각각 만든다 → VRAM 2배 + B 의 monkeypatch 창에
**채점 세션**이 노출된다.

---

## 3. 안전 확인된 것 (무엇이 왜 안전한지)

1. **모듈 전역 변형 전수 — 1건뿐이고 그것은 정적 설정 캐시다.**
   AST 로 `functions/pipeline/app.py`, `runpod_inference/server.py`, `shared/python/sunity_shared/**`
   전체를 훑어 "함수 안에서 모듈 전역 이름을 변형(`X[...] =`, `X.attr =`, `X.append/update/…`)"
   하는 자리를 뽑으면 `analysis/reference_anchors.py:199 _CACHE[motion_id] = …` 단 1건.
   키가 motion_id 이고 값은 YAML 파일 내용 → 분석별 값이 아니다. **읽기 전용 성격.**

2. **작업 디렉터리·임시 파일 — 충돌 없다.**
   운영 코드에 `/tmp` 리터럴 하드코딩 **0건**(`start_server.sh` 의 서버 로그 리다이렉트 제외).
   전부 `tempfile.NamedTemporaryFile` / `tempfile.mkdtemp(prefix="fz_native_" | "compare_render_")`
   로 호출마다 유니크. 유일한 고정 경로인 `_preserve_compare_fail_workdir`(app.py:4862-4882)도
   `compare_fail_{analysis_id}` 로 id 를 포함한다. 하위 산출물
   (`compare_render.py:377 pole_{side}.json`, `compare_align.py:275-276 uf15/rf15`)은 모두
   분석별 workdir 밑이다.

3. **S3 키 — 전부 분석 스코프.**
   `shared/python/sunity_shared/s3keys.py` 의 빌더 전수(23, 47, 58, 73, 136행)가
   `{uid}/{analysis_id}` 를 포함한다.

4. **설정 캐시들 — 값이 분석과 무관하다.**
   `phrasebook._PHRASEBOOK_CACHE/_TERMINOLOGY_CACHE`, `assemble._MOTION_IPSF_MAP_CACHE`,
   `exercise_map._CORRECTIVE_EXERCISES_CACHE`, `force_signals._TILT_THRESHOLDS_CACHE`/
   `_CONTACT_POINTS_CACHE` — 전부 파일 1회 로드. 락은 없으나 중복 로드해도 같은 값이라
   섞일 값이 없다.

5. **LLM 클라이언트 싱글턴 — 호출별 상태를 안 담는다.**
   `gemini_vision_scorer._CLIENT`, `spot_check._CLIENT`, `_GEMINI_COACH_WRITER`,
   `_SYNTHESIS_ADAPTER`, `_POLLY_CLIENT`, `_SQS_CLIENT`, `CerebrasCoachWriter._client`.
   기계 검사로 이들 클래스에서 `self.<attr> = ` 대입이 `__init__` 밖에 있는 자리를 뽑으면
   **A-2 의 2건 외에 0건**이다. 요청 인자는 전부 호출 로컬.

6. **과거 race fix 는 실재하고 지금도 유효하다.**
   커밋 `0d1e0cdf` "HIGH-1 v4 — sidecar dropped". `_RTMWNlfCompat.estimate_with_profile`
   (app.py:1307-1335)이 body profile 을 **인스턴스 사이드카 속성이 아니라 로컬 튜플로**
   반환한다. docstring 이 `"concurrent analyses 가 _POSE_ESTIMATOR 글로벌 공유해도
   profile leak 0"` 이라고 적고 있고, 코드가 실제로 그렇다. **이 자리는 깨끗하다.**
   즉 과거 수리는 "포즈/체형 사이드카"를 없앴고, **recognizer 쪽 두 속성(A-1/A-3)과
   extractor 쪽 두 속성(A-2)은 손대지 않았다** — 남은 것이 정확히 그것이다.

7. **`TechniqueCache._memory`** — 인스턴스 dict 이고 키가 `f"{video_hash}:{model}:{yaml_version}"`
   (technique_cache.py `_mem_key`). 다른 분석의 값을 집을 수 없다.

8. **`GeminiFileSession`** — `_process` 안에서 분석마다 새로 만들고(app.py:7831) 자체
   `threading.Lock` 을 갖는다(file_session.py:87). 모듈 전역 상태 0건. app.py:7823-7828
   주석이 "모듈 전역 캐시 금지(분석 간 상태 오염 0)"를 명시하고 코드가 그대로다.

9. **`os.environ` 런타임 변경 — 분석별 값 주입 없다.**
   전 리포에서 `os.environ[...] =` / `update` / `pop` / `putenv` **0건**. `setdefault` 3건뿐이고
   값이 전부 상수다: `PYOPENGL_PLATFORM=egl`(synthesis/virtual_renderer.py:29,
   synthesis/cylindrical_mesh.py:41), `CUBLAS_WORKSPACE_CONFIG=:4096:8`(ort_determinism.py:150).
   `os.chdir` **0건**.

10. **동시성이 실제로 열려 있다는 확인.**
    `backend/template.yaml` 의 `PipelineFunction`(326-401행)에 `ReservedConcurrentExecutions`
    가 **없다**. 그 설정을 가진 함수는 visual-worker(471행, 2)와 visual-dispatch(557행, 1)뿐이다.
    → SQS 메시지 N개 → pipeline Lambda N개 동시 → `POST /analyze` N회 → Pod 의
    `BackgroundTasks` N개가 한 프로세스 안 스레드로 동시 실행. `BatchSize: 1`(394행)은
    한 호출이 메시지 1개를 받는다는 뜻이고 동시성 제한이 아니다(과제 전제와 일치).

---

## 4. 미확인 — 무엇을 어떻게 재야 닫히는가

| # | 미확인 항목 | 닫는 방법 | Pod |
|---|---|---|---|
| 1 | **rtmlib / onnxruntime 세션의 스레드 동시 호출 안전성.** `_POSE_ESTIMATOR` 는 전역 1개이고 두 분석이 같은 `Wholebody` 를 동시에 호출한다. ORT 의 `Run()` 동시 호출은 일반적으로 지원되나, rtmlib 의 `YOLOX`/`RTMPose` 래퍼가 전처리 중간값을 `self` 에 담는지는 **못 봤다** — 로컬에 rtmlib 미설치(`import rtmlib` 실패 확인). | Pod 에서 `python -c "import inspect, rtmlib.tools; print(inspect.getsource(...))"` 로 래퍼의 `self.` 대입 유무 확인. 또는 **같은 영상 2벌**을 동시에 `/analyze` 에 넣고 단독 실행본과 keypoint 배열을 바이트 대조(같아야 정상). | 필요 |
| 2 | **A-1/A-2 가 점수를 얼마나 바꾸는가.** 기전은 코드로 확정했으나 점수 차이는 실측 0. | 학생 영상 1편을 (a) 단독, (b) mode3 분석과 겹쳐서 각 3회 분석 → `result.score`, `profile.motion_id`, `category` 대조. 겹치는 타이밍은 로그 `stage=frame_extract` 직후(warm 약 50초 창, 위 실측표). | 필요 |
| 3 | **B(결정론 patch) 중첩의 실제 발생률.** compare_render 는 분석 후반 스테이지라 두 분석의 이 구간이 겹칠 확률을 안 쟀다. | `deterministic_inference_session` 진입/이탈에 `threading.get_ident()` 로그를 붙이고 동시 2건 실행 → 중첩 로그 유무 확인. | 필요 |
| 4 | **C 의 실현 조건.** startup 워밍업이 실제로 실패한 적이 있는지. | Pod 로그에서 `"워밍업 실패 — 첫 요청 처리 시 재시도"` 검색. 단 `start_server.sh:51` 의 `>` 가 재기동마다 truncate 하므로 **과거분은 못 본다** — 앞으로는 재기동 전에 내려받아야 한다. | 필요 |
| 5 | **Firestore 공유 doc 의 동시 쓰기.** 이번 조사는 분석별 doc 스코프까지만 봤다. `gemini_cache/{video_hash}`, `term_collection/*`, `reference/_release` 같은 **여러 분석이 같이 쓰는 doc** 의 동시 쓰기 semantics(트랜잭션/증분 여부)는 안 봤다. | `firestore_admin.py` 의 해당 helper 들이 `Increment`/transaction 을 쓰는지 읽기. Pod 불필요. | 불필요 |
| 6 | **동시 실행 시 GPU VRAM.** compare_render 가 분석마다 새 Wholebody(YOLOX+RTMW)를 VRAM 에 올린다(B 항 참조). N 명 동시면 N 벌이다. 상한을 안 쟀다. | 동시 2~3건 돌리며 `nvidia-smi` 관찰. OOM 은 실패로 드러나므로 "조용한 고장"은 아니다. | 필요 |

---

## 5. 우선순위 (실증 기준)

1. **A-1 + A-2** — 채점에 닿고, 창이 51~177초(실측)이며, 학원은 정의상 그 창 안에서 다음
   사람이 올린다. 조용한 오염의 정의에 정확히 들어맞는다.
2. **C** — 조건부지만 실현되면 A 와 같은 등급(채점 세션이 비결정론이 된다).
3. **B** — 사용자에게 보이는 합성 비교 영상의 정렬이 운에 걸린다. 점수는 아니다.
4. **A-3** — 수집 원장 왜곡. 실증 판정을 막지는 않는다.

수리 방향은 이 보고서의 범위 밖이다(조사만 지시받음). 다만 세 A 경로가 전부
**"전역 싱글턴의 속성에 분석별 값을 얹고 나중에 읽는다"** 는 한 가지 모양이라는 점,
그리고 이미 같은 리포 안에 그 모양을 없앤 선례(`estimate_with_profile` 의 로컬 튜플 반환,
`GeminiFileSession` 의 분석-로컬 생성)가 있다는 점은 기록해 둔다.
