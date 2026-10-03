---
phase: quick-261003-vsa
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/gemini/student_proxy.py
  - backend/tests/test_student_proxy.py
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/models.py
  - backend/shared/python/sunity_shared/provenance.py
  - app/src/types/analysis.ts
  - docs/contract.md
  - backend/tests/test_gemini_student_proxy.py
  - backend/tests/test_analysis_provenance.py
autonomous: true
requirements: [QUICK-261003-vsa]

must_haves:
  truths:
    - "GEMINI_STUDENT_PROXY 미설정 · \"0\" 이면 지금과 같다 — `_extract_video_analysis_inputs_from_local` 에 새 인자가 가지 않고, 학생 원본이 다운로드 직후(포즈 전) gemini 스레드에서 1회 업로드되며(prefetch OFF 면 포즈 뒤 메인에서 1회), scene_finder · recognizer · veto · coach B 가 원본 경로와 그 핸들을 받고, timingsMs 에 student_proxy_encode 가 없고, analysisVersion 에 geminiStudentInput 이 없다"
    - "GEMINI_STUDENT_PROXY=1 이면 학생 영상을 Gemini 에 올리는 소비처 전부(학생 업로드 · scene_finder · recognizer/moment extractor · veto 영상 비교 · coach B)가 같은 프록시 경로와 같은 핸들 객체를 받고, 학생 4K 원본은 Gemini File API 에 한 번도 올라가지 않는다"
    - "토글이 켜져도 Gemini File API 가 아닌 소비처(still-pair · `_pipeline_frame_fps` · fault_zoom · compare_render · wave2 augmenter · 레거시 veto · S3 서명 URL · 원본 unlink)는 원본 `local_video_path` 를 그대로 쓴다"
    - "프록시 프레임 i 는 추출 프레임 i(원본 시각 i/실효fps)이고 추출 출력의 마지막 프레임(§12-B 강제 포함일 수 있음)은 넣지 않는다 — 30fps 31/32/33프레임 · 24fps 26프레임 합성 영상에서 |프록시 길이 − 원본 길이| ≤ 프레임 간격 1개"
    - "프록시 인코딩 예외 · 실효 fps 미상이면 원본으로 폴백하고 `student_proxy fallback=original reason=...` 경고를 남기며 분석은 완주한다 — 이때 Gemini 소비처 전부가 원본을 받고 analysisVersion.geminiStudentInput = \"original\", 부분 프록시 파일은 남지 않는다"
    - "프록시 temp 파일은 성공 · 포즈 조기 실패 둘 다 executor join → session.close → unlink 순서로 지워지고, 프록시 File API 핸들은 session.close 가 지운다"
    - "토글 ON 이면 timingsMs 에 student_proxy_encode(frame_extract 직후 · rtmw 전, 메인 스레드)가 실리고, analysisVersion.geminiStudentInput 이 \"proxy640\" | \"original\" 로 실린다 — 3-way 계약(analysis.ts · models.py+provenance.py · contract.md) lockstep"
    - "채점 · Gemini 모델/프롬프트/thinking/media_resolution · 기준 영상 경로 · 기본값(OFF) · 배포 무변경"
  artifacts:
    - path: "backend/shared/python/sunity_shared/gemini/student_proxy.py"
      provides: "추출 프레임 → 작은 mp4 인코더 + 시간축 규칙(마지막 프레임 제외)"
      contains: "def encode_student_proxy"
    - path: "backend/tests/test_student_proxy.py"
      provides: "실제 imageio-ffmpeg 인코드로 시간축 길이 오차 · 프레임 대응 · 홀수 크기 · 입력 계약 잠금"
      min_lines: 100
    - path: "backend/functions/pipeline/app.py"
      provides: "_gemini_student_proxy_enabled · _student_effective_fps · _build_student_proxy · after_frame_extract 훅 · gemini_student_video_path 인자 · _process 배선"
      contains: "def _build_student_proxy"
    - path: "backend/tests/test_gemini_student_proxy.py"
      provides: "부품 단위(1부) + _process 통합(2부, qmg 하네스 재사용, 소켓 가드)"
      min_lines: 350
    - path: "backend/shared/python/sunity_shared/provenance.py"
      provides: "build_analysis_version(gemini_student_input=) + GEMINI_STUDENT_INPUTS + ANALYSIS_VERSION_KEYS 끝에 geminiStudentInput"
      contains: "geminiStudentInput"
    - path: "docs/contract.md"
      provides: "§4 timingsMs 에 student_proxy_encode · §11.13 에 geminiStudentInput"
      contains: "student_proxy_encode"
  key_links:
    - from: "_extract_video_analysis_inputs_from_local"
      to: "after_frame_extract 훅"
      via: "frame_extract stage 직후 · rtmw stage 전 호출, 예외는 경고로 삼킴"
      pattern: "after_frame_extract\\(frames\\)"
    - from: "_process 훅 클로저"
      to: "session.get_or_upload(프록시 경로)"
      via: "분석-로컬 executor submit (prefetch ON) — 학생 원본 다운로드 시점 업로드는 토글 ON 이면 제출하지 않음"
      pattern: "executor\\.submit\\(\\s*session\\.get_or_upload"
    - from: "_process"
      to: "recognizer.recognize / _call_wave1_scene_finder / _collect_vision_fault_context / _build_coach_context"
      via: "gemini_student_path (OFF = local_video_path 그 객체)"
      pattern: "gemini_student_path"
    - from: "_collect_vision_fault_context"
      to: "gemini_vision_scorer.assess_fault_context_video"
      via: "gemini_student_video_path or local_video_path — still-pair 는 local_video_path"
      pattern: "gemini_student_video_path"
    - from: "_attach_analysis_version"
      to: "provenance.build_analysis_version"
      via: "gemini_student_input kwarg (OFF = None → 키 생략)"
      pattern: "gemini_student_input="
---

<objective>
학생 영상을 Gemini 에 넘길 때 4K 원본(HEVC 2160×3840 30fps 101MB) 대신, frame_extractor 가 이미 만든 프레임(긴 변 640px, 실효 fps ≈ 9.99)을 다시 묶은 작은 mp4(프록시)를 넘기는 env 토글 `GEMINI_STUDENT_PROXY` 를 만든다. **기본 OFF — OFF 면 지금과 같은 경로.** 이 quick 은 코드 · 테스트까지다. 켜기는 Pod 동등성 검증 + belle 판정 뒤(SUMMARY 에 검증 계획).

Purpose: belle 10-03 밤 "속도 갑자기 심각해짐, 뭐라도 해봐". 점수까지 ≈109초 중 ≈80초가 Gemini 가 학생 4K 원본을 다루는 시간이다 — 업로드→ACTIVE 36초(그중 `student_upload_wait` 11~18초가 임계 경로) + 첫 generateContent(recognizer) 43초 [확인 — svg 증거 로그 `evidence/svg_after{1,2}_runpod_server.log`]. 오케스트레이터 로컬 실측(프로덕션 `GeminiFileSession.get_or_upload` + `find_scene_flags`, 1회씩): 4K = ACTIVE 37.0초 + scene 54.3초 · 프록시(199×640×360, fps 9.9867, libx264 crf23 veryfast, 0.43MB, 묶기 0.15초) = 5.7초 + 3.2초, scene 4 flag 세 변형 동일 [확인 — 오케스트레이터, scratchpad 휘발 · 수치만 승계].
Output: 새 모듈 student_proxy.py · app.py 부품과 `_process` 배선 · analysisVersion 한 키(3-way) · contract.md 두 곳 · 새 테스트 2파일 + provenance 테스트 1건 갱신. 배포 · 기본값 변경 · start_server.sh 변경 없음.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/quick/261003-qmg-ref-gemini-prefetch-and-scene-join-move/261003-qmg-SUMMARY.md
@.planning/quick/261003-svg-frame-extract-resize-skip-and-post-stage/261003-svg-SUMMARY.md
@backend/shared/python/sunity_shared/analysis/frame_extractor.py
@backend/shared/python/sunity_shared/gemini/file_session.py
@backend/tests/test_ref_prefetch_scene_join.py

app.py 는 11,339줄 — 통째로 읽지 말고 아래 범위만 읽는다:
:151~168 `_stage` · :462 `_VISION_FALSY` · :505~557 토글 2개 + `_safe_unlink_local_video` · :594~700 기준 prefetch 헬퍼 · :753~790 `_call_wave1_scene_finder` · :818~865 `_call_wave2_keypoint_augmenter` · :1481~1545 `_build_coach_context` · :1932~2112 `_VideoAnalysisInputs`(NamedTuple) · `_download_analysis_video` · `_extract_video_analysis_inputs_from_local` · :2608~2837 `_collect_vision_fault_context` · :3807~3890 `_apply_vision_veto` 머리 · :8087~8122 `_pipeline_frame_fps` · :8194~8240 `_attach_analysis_version` · :8974~9300 `_process` 앞부분 · :9784~9860 ref_upload · veto_collect · scene join · coach context · :10538~10556 analysisVersion 부착 · :10753~10781 outer finally.

## 플래너가 코드로 확인한 것 (관측 — 승계 가능)

### 학생 영상 Gemini File API 소비처 전수 (grep `files.upload` · `get_or_upload` · `preuploaded` · `GeminiVisionCall` · `.call(` — backend/shared · functions · runpod_inference)

| # | 자리 (app.py) | 하류 (업로드 · 캐시 키 · 폴백) | 토글 ON |
|---|---|---|---|
| 1 | :9080~9082 prefetch `executor.submit(session.get_or_upload, local_video_path_dl)` | file_session.py:96 (경로 키 inflight/handle 맵) | 다운로드 시점 제출 안 함 → 훅에서 프록시로 제출 |
| 2 | :9084~9097 `_scene_prefetch` → `_call_wave1_scene_finder(local_video_path=…, preuploaded_handle=…)` | scene_finder.py:179 → client.py:167 `GeminiVisionCall.call`; 핸들 None 이면 client.py:222~230 이 **넘겨받은 경로**를 자체 업로드. 캐시 없음 | 프록시 경로 + 프록시 핸들 |
| 3 | :9155~9161 `student_upload_wait` 동기 폴백 `session.get_or_upload(local_video_path)` | file_session.py | 프록시 |
| 4 | :9170~9176 동기 scene | 2 와 같음 | 프록시 |
| 5 | :9290~9298 `recognizer.recognize(angles, frames=local_video_path, preuploaded_handle=…)` | gemini_technique_recognizer.py:262 TechniqueCache.lookup(frames) → technique_cache.py:272 `compute_video_hash(경로)` = 파일 SHA256 · :338 미등록 hook video_hash · :359 store · moment extractor gemini_moment_extractor.py:330 프로세스 메모리 캐시 키 `(video_uri, motion, model)` · 핸들 None 이면 :418 `files.upload(file=video_uri)` | 프록시 경로 + 프록시 핸들 |
| 6 | :9796~9813 `_collect_vision_fault_context(local_video_path=…, preuploaded_student_handle=…)` → 안 :2777~2786 `assess_fault_context_video(local_video_path, …)` | gemini_vision_scorer.py:1294 `student_hash = compute_video_hash(student_video_path)` → VisionVetoCache 키 · :1341 lookup_rich · 학생/기준 핸들 **둘 다** 있을 때만 재사용, 아니면 :1370 학생 경로 자체 업로드 | **새 kwarg** `gemini_student_video_path` 로 assess 에만 프록시. still-pair(:2690 `_build_selected_frame_pair(user_video_path=local_video_path)`)는 원본 |
| 7 | :9828~9848 `_build_coach_context(local_video_path=…)` → `"videoPath"`(:1522, 이 함수에서 경로를 쓰는 곳은 이 키 하나) + `coach_context["preuploadedHandle"]` | coach_writer_v2.py:480 `videoPath` · :491 핸들 · :507 `call.call(video_path, preuploaded_handle=…)` — 핸들 None 이면 attempt 마다 경로 자체 업로드. `videoPath` 를 읽는 곳은 리포 전체에서 coach_writer_v2.py:480 하나 [확인 grep] | 프록시 경로 + 프록시 핸들 |
| 8 | :10330 `_call_wave2_keypoint_augmenter(local_video_path=…)` | keypoint_augmenter.py:379 `call.call(video_path)` — 청크마다 자체 업로드, 핸들 인자 없음, 프롬프트가 9fps 추출 프레임 번호를 문자로 묻는다 | **안 바꾼다** — `GEMINI_D_ENABLED` 기본 OFF 이고 Pod start_server.sh 에 없다 [확인], 핸들 인자가 없어 바꾸려면 모듈 시그니처 변경, 프레임 번호 의미 변화 미검증 |
| 9 | :10047~10055 레거시 `_apply_vision_veto(result, local_video_path, …)`(context 없는 분기) → :3878 `assess_fault_severity` → gemini_vision_scorer.py:1029 자체 업로드 | `_collect_vision_fault_context` 는 모든 return 이 `_ctx(...)` 이고 바깥 except 도 `_ctx("skipped_error")` 라 운영에서 None 을 돌려주지 않는다 → 이 분기는 운영 도달 0 [확인 :2608~2837 읽음]. :10004 의 context 분기는 Gemini 를 부르지 않는다 | **안 바꾼다**(도달 0. 도달해도 경로=원본·내용=원본이라 캐시 혼입 없음) |

File API 가 아닌 Gemini 호출(spot_check `Part.from_bytes` JPEG · card_gates 인라인 JPEG · coach_hook 텍스트)은 학생 영상 파일을 올리지 않는다 [확인 — svg SUMMARY 의존표 6 승계 + spot_check.py · card_gates.py · card_photo_audit.py grep `files.`/`upload` 0]. synthesis(gemini_view_reasoner)는 영상 경로를 받지 않는다 [확인]. reference_extractor 는 공급자 등록 경로 전용(functions/reference-auto-register) — `_process` 밖.

비-Gemini 소비처(원본 유지) [확인]: `_pipeline_frame_fps(local_video_path)` :9546 · :9996 · :10523 — `_FRAME_EXTRACTOR.effective_fps_for(경로)` 기록 조회라 **반드시 원본 경로**(프록시 경로를 주면 기록이 없어 target 9.0 으로 떨어진다, :8087~8122) · still-pair :2690 · fault_zoom :10662~10686 · compare_render :10736 · 서명 URL :9282(S3 key) · unlink :10774.

### 폴백 결정 — 핸들이 None 이 되어 소비처가 자체 업로드할 때 무엇을 올리나
- 소비처는 **자기가 받은 경로**를 올린다(위 표 2·5·6·7). 그래서 결정은 "경로를 무엇으로 주나" 하나다.
- **결정: 토글 ON 이고 프록시가 만들어졌으면 경로도 프록시다(폴백 업로드도 프록시).** 근거 [확인 — 코드]: (1) TechniqueCache(technique_cache.py:272) · VisionVetoCache(gemini_vision_scorer.py:1294) 키는 **넘겨받은 경로의 파일 SHA256** 이다. 핸들은 프록시인데 경로가 원본이면 프록시로 얻은 판정이 원본 hash 키에 저장돼 OFF 판정과 섞인다(요구 7 위반). 경로와 핸들이 같은 파일이어야 캐시가 입력과 맞는다. (2) 한 분석 안 Gemini 입력이 하나로 유지돼야 analysisVersion 기록과 Pod 동등성 비교가 해석된다. (3) 시간: 폴백 자체 업로드도 ≈6초(원본이면 ≈36초).
- 원본으로 가는 경우는 **프록시를 못 만들었을 때뿐**(인코더 예외 · 실효 fps 미상 · 프레임 부족) — 그때는 경로 · 핸들 · 기록 모두 원본("original"). 정확도 쪽 안전망은 "프록시가 원본과 같은 답을 내는가"를 Pod 동등성 검증이 판정하는 것이지, 분석마다 섞는 것이 아니다.
- 비용: 토글 ON 인데 인코딩이 실패하면 원본 업로드가 다운로드 시점이 아니라 frame_extract(≈13초) 뒤에 시작된다 → 그 분석은 OFF 보다 ≈13초 늦을 수 있다 [추정]. 실패 경로라 받아들인다(경고 로그로 보인다).

### 시간축
- extract(frame_extractor.py:141~204)는 start 0 부터 step=round(src/target) 간격으로 남기고(:183~188), 마지막으로 본 프레임이 버려지는 프레임이면 루프 뒤에 강제로 붙인다(:196~200, 12-deferred §12-B). 강제 프레임은 **언제나 출력의 마지막 원소**이고 균일 격자(i·step/src) 밖에 있다. extract 는 강제 여부를 밖에 알리지 않는다 [확인].
- **결정: 프록시 = 추출 출력에서 마지막 프레임을 무조건 뺀 T−1 장, fps = 그 영상의 실효 fps(`effective_fps_for`).** 그러면 프록시 프레임 i 는 원본 시각 i/e 에 정확히 놓이고(강제 프레임은 항상 마지막이라 빠진다), 길이 차는 강제 있음 = (k_last + step − N)/src ∈ [0, step−2]/src, 강제 없음 = −1/src → step ≥ 2(24 · 25 · 30 · 60fps 원본 전부, step 3~7)에서 |차| < 1 간격. 잃는 것은 영상 끝 ≤ (step−1)/src 초(30fps 면 0.067초).
- 플래너 로컬 탐침 [확인 — scratchpad axis_probe.py, 휘발]: 진짜 `FfmpegFrameExtractor(9.0, 640)` + 위 규칙으로 30fps n=31 → T=11 · 길이 차 −0.033초, n=32 → T=12(강제) · +0.033, n=33 → T=12(강제) · 0.000, 24fps n=26 → T=10 · e=8.0 · +0.042 — 전부 간격(0.1/0.125초) 안. 디코드 프레임 대 추출 프레임 평균 절대차 최대 2. 인코드 23~26ms(64×96). n=32 와 n=33 의 프록시 sha256 이 같았다(같은 프레임 11장 → 같은 바이트) → **로컬 x264 출력은 결정론적으로 보인다** [확인 로컬 1쌍 / Pod 미확인].
- imageio-ffmpeg 는 입력 rate 를 `"-r {:.02f}"` 로 넘긴다(backend/.venv imageio_ffmpeg/_io.py:528) → 9.9867 은 9.99 로 들어간다. 120초 영상 끝에서 ≈0.04초 — 간격(0.1초)보다 작다. 테스트로 그 몫을 잰다.
- Gemini 가 돌려주는 초를 프레임 번호로 바꾸는 소비처 [확인 grep]: (a) gemini_technique_recognizer.py:123 `_hold_window_from_moments` fps = **9.0 리터럴** → profile.hold_window → dimensions.py:366 흔들림 창 · (b) app.py:2685 `user_frame_idx = int(round(at * 9.0))`(at = vision_veto.worst_pose_timestamp, key_moments 의 초) → still-pair 선택 · (c) force_signals.py:580 `ts * fps`, fps = app.py:10102 `fps=9.0` 리터럴, `FORCE_SIGNALS_LAYER2_ENABLED` 미설정 = OFF · (d) veto 의 at_seconds 는 운영에서 None(app.py:2777 주석). judging `assign_frame_indices` 는 운영 호출 0. veto fan-out · scene · coach 응답에는 초 필드가 없다(gemini_vision_scorer.py · gemini/schemas.py grep — schemas.py:70/73 의 초는 공급자 등록 전용). → 전부 9.0 을 쓰고(실효 9.99 와 다른 것은 기존 사실, recognizer 주석 :107 이 이미 적음) 이 변경은 그 환산을 건드리지 않는다. 프록시는 초 축을 원본과 같게 유지하는 것만 책임진다.
- Gemini 쪽 영상 설정: `video_metadata` · `media_resolution` 지정 0 [확인 grep] → 기본 샘플링(초당 1장으로 알려짐 [미확인 — 문서 미대조])이면 10fps 프록시로 샘플이 줄지 않는다. 해상도: 640 긴 변이 Gemini 기본 처리 해상도보다 작을 수 있다 [미확인] — 정확도 위험은 Pod 동등성 검증이 판정한다. 프록시에는 오디오 트랙이 없다(writer 에 audio_path 미지정) — 원본 학생 영상은 소리가 있을 수 있다 → 입력 차이 [확인 — 코드] / 결과 영향 [미확인].

### 프록시 생성 시점
- `_extract_video_analysis_inputs_from_local`(:1997~2083)은 한 함수 안에서 frame_extract(:2027~2028) → rtmw(:2029~2030) 를 잇는다. 사이에 호출 지점이 없다 → **선택 인자 훅 `after_frame_extract` 를 추가**해 그 사이에서 부른다(인자 미전달 = 지금과 동일).
- 인코드는 **메인 스레드(훅 안)** 에서 한다 — RTMW 와 같은 프레임 배열을 두 스레드가 동시에 만지는 경우를 아예 없앤다(rot180 2차는 사본을 만든다 inversion_rot180.py:165 [확인], rtmlib 전처리의 제자리 쓰기 여부는 [미확인]). 비용은 임계 경로에 인코드 시간만큼(오케스트레이터 로컬 0.15초, Pod [미확인]) — `student_proxy_encode` stage 가 그 값을 보인다. 업로드(+ACTIVE ≈5.7초)는 executor 에서 RTMW(≈4.5초)와 겹친다.
- 시간 산술 [추정]: 훅 = 다운로드 + frame_extract(13.4초) 뒤 → 업로드 준비 ≈ +0.2 +5.7초, RTMW 끝 ≈ +4.5초 → `student_upload_wait` ≈1~2초(지금 11~18초). RTMW 뒤에 시작하면 ≈6초 — 훅이 ≈4.5초 앞선다.
- executor 교착 [확인 — 논리]: 제출 순서 = (기준 다운로드)(기준 업로드: 앞 것 대기) — 다운로드 시점, (프록시 업로드)(scene: 프록시 업로드 대기) — 훅 시점. 기다리는 작업은 자기보다 먼저 제출된 future 만 기다리고 FIFO · max_workers=4 → qmg 의 교착 0 논리 그대로.
- 정리 순서는 qmg 그대로: 조기 실패 except = executor.shutdown(wait) → session.close → 원본 unlink → 기준 prefetch temp unlink → **프록시 unlink(새)**. 성공 경로 outer finally 도 같은 순서 뒤에 프록시 unlink. 프록시 핸들은 세션이 올린 것이라 session.close 가 지운다(file_session.py:273~293).

### 캐시 (요구 7)
- TechniqueCache · VisionVetoCache 키는 넘겨받은 경로 파일의 SHA256 [확인 — 위 표]. ON 이면 경로가 프록시 → 원본 hash 와 자연히 다르다 → 원본 판정과 섞이지 않는다. moment extractor 메모리 캐시 키는 경로 문자열(temp 이름이라 분석마다 다름) [확인].
- 같은 영상 재분석 시 프록시 바이트가 같은가(캐시 적중 여부)는 로컬 1쌍에서 같았다 [확인 로컬] / Pod ffmpeg 바이너리 · 스레드에서 [미확인]. 반대로 같으면 Pod 검증에서 같은 fixture 를 ON 으로 두 번 돌리면 두 번째가 캐시 적중이다 — 검증 계획에 반영(Task 3 SUMMARY).
- 부수 효과 [확인 — 코드]: 미등록 동작 수집 hook 의 video_hash(gemini_technique_recognizer.py:338)가 ON 에서는 프록시 hash 다. uid 기반 unique_users 집계에는 영향 없다.

### 기록 (요구 6) — 플래너 판단
- analysisVersion 은 "이 결과를 낳은 판"의 기록이고 플래그(rot180 등)를 이미 싣는다(provenance.py:88~99, contract.md §11.13). 입력 종류도 같은 성격이라 여기에 **한 키** `geminiStudentInput: "proxy640" | "original"` 를 넣는다. 영향 = analysis.ts `AnalysisVersion` 한 줄 · models.py `ANALYSIS_VERSION_KEYS` 한 원소 + 값 튜플 · provenance.py 키 · 값 튜플 · builder kwarg · contract.md §11.13 몇 줄. 검증기(firestore_admin.py:630)는 models 키를 따라가 코드 변경 0. 앱은 이 필드를 읽지 않는다(§11.13).
- **토글 OFF 면 키를 싣지 않는다** — OFF 결과 doc 을 지금과 같게 두기 위해서다(토글 검증의 기준선). 부재의 뜻 = 토글 OFF 또는 이 키 도입 전 doc → 둘 다 원본 입력. 이 예외("부재 = 못 구했다" 관례와 다름)를 §11.13 에 적는다.
- test_analysis_provenance.py:418~426 `test_builder_emits_only_registered_keys` 는 "전부 채운 호출 = 등재 키 전부"를 단언한다 → 그 호출에 `gemini_student_input="proxy640"` 을 더해야 한다(테스트 뜻 유지). `test_typescript_contract_declares_every_key` · `test_markdown_contract_section_exists` 는 키 목록을 따라 자동으로 새 키를 검사한다.

### 하네스 재사용
- qmg 하네스(test_ref_prefetch_scene_join.py:304~606)의 `_install` 은 `_extract_video_analysis_inputs_from_local` 가짜를 **고정 시그니처**(:483~486, `after_frame_extract` 없음)로 깐다 → OFF 에서 새 인자를 넘기면 TypeError 로 기존 테스트가 깨진다. 그래서 `_process` 는 토글 ON 일 때만 훅 인자를 넘긴다. 같은 이유로 프록시 unlink 는 경로가 있을 때만 부른다(qmg `_rec_unlink` 사건 목록에 None unlink 를 더하지 않게).
- `_VideoAnalysisInputs` 는 NamedTuple(:1932) — 통합 테스트는 `inputs._replace(frames=...)` 로 프레임을 채운다.
- 새 테스트에서 픽스처 재등록 선례: `from tests.test_ref_prefetch_scene_join import pipeline, net_attempts  # noqa: F401` (svg test_post_stage_parallel.py · test_firestore_reference_writers.py:40). qmg `pipeline` 픽스처의 env 리셋 목록(:48~57)에 `GEMINI_STUDENT_PROXY` 는 없다 → 새 테스트마다 setenv/delenv 로 명시한다.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 프록시 인코더 + 시간축 규칙 (student_proxy.py, 실제 ffmpeg 로 잠금)</name>
  <files>backend/shared/python/sunity_shared/gemini/student_proxy.py, backend/tests/test_student_proxy.py</files>
  <behavior>
    - `proxy_frame_count(n)`: 0→0, 1→0, 2→0, 3→2, 12→11, 199→198 (마지막 1장 제외, 결과가 MIN_PROXY_FRAMES=2 미만이면 0).
    - 시간축(parametrize (src_fps, n) = (30,31) · (30,32) · (30,33) · (24,26)): tmp_path 에 프레임마다 회색값이 다른 H64×W96 소스 mp4 를 imageio(libx264, quality=None, macro_block_size=1, output_params crf 10)로 쓰고, 진짜 `FfmpegFrameExtractor(9.0, 640).extract` 로 뽑는다. 사전조건 단언: T = 11 · 12 · 12 · 10, e = effective_fps_for = 10.0 · 10.0 · 10.0 · 8.0. `encode_student_proxy(frames, e, dest)` 반환 == T−1. 프록시를 imageio 로 읽어 프레임 수 == T−1, meta fps 가 e 와 0.01 안, |(T−1)/meta_fps − n/src_fps| ≤ 1/e, 모든 i < T−1 에서 디코드 프레임 i 와 추출 프레임 i 의 평균 절대차 ≤ 4. 강제 포함 케이스(30,32)·(30,33)는 추가로 디코드 마지막 프레임과 추출 마지막(강제) 프레임의 평균 절대차 > 10 — 강제 프레임이 프록시에 없다.
    - 비정수 fps: (100, 32, 48, 3) 프레임 · fps 9.9867 → meta fps == 9.99(imageio-ffmpeg 소수 둘째 자리 반올림), 프레임 수 99, |99/9.99 − 99/9.9867| < 0.01.
    - 홀수 크기: (5, 63, 95, 3) → 반환 4, 디코드 shape (4, 62, 94, 3) — 짝수로 자른다(yuv420p 요구).
    - 입력 계약 위반은 ValueError 이고 dest 파일을 만들지 않는다: ndim 3 · 채널 4 · dtype float32 · T=2(남는 1장) · fps 0 · −1 · NaN · inf · True(bool).
    - 인코더 예외는 삼키지 않고 호출측으로 나온다: `imageio.get_writer` 를 RuntimeError 를 던지는 가짜로 바꾸면 같은 예외(폴백 · temp 정리는 호출측 몫).
  </behavior>
  <action>
**RED.** 새 파일 `backend/tests/test_student_proxy.py`. 경로 주입은 test_ref_prefetch_scene_join.py:39~43 관례(shared/python 을 sys.path 앞에). 맨 위에서 진짜 `imageio` · `numpy` 를 import 한다(가짜 PIL/imageio stub 을 넣는 다른 테스트 모듈을 import 하지 말 것 — test_frame_extractor_last_frame.py:30~44 가 그런다). 소스 프레임 회색값 = `(i * 23) % 220 + 10`(인접 차 ≥ 20). 위 behavior 를 테스트로 쓴다. 파일 머리 docstring: 목적(quick-261003-vsa — 학생 영상 Gemini 프록시, 시간축 결정과 그 산술), 실제 imageio-ffmpeg 바이너리를 쓰고 네트워크 0. RED = `ModuleNotFoundError: sunity_shared.gemini.student_proxy`. 커밋 `test(261003-vsa): 학생 프록시 인코더 — 시간축 · 프레임 대응 · 입력 계약 (RED)`.

**GREEN.** 새 모듈 `backend/shared/python/sunity_shared/gemini/student_proxy.py` (gemini/__init__.py 의 지연 export 목록은 건드리지 않는다 — 호출측이 서브모듈로 import).
- 상수: `PROXY_CODEC = "libx264"` · `PROXY_CRF = 23` · `PROXY_PRESET = "veryfast"` · `PROXY_PIXEL_FORMAT = "yuv420p"` · `MIN_PROXY_FRAMES = 2`. 값은 오케스트레이터 로컬 실측 조합(0.43MB, 묶기 0.15초)과 같게.
- `proxy_frame_count(n_frames: int) -> int`: n−1, 그 값이 MIN_PROXY_FRAMES 미만이면 0.
- `encode_student_proxy(frames, fps, dest_path) -> int`: 검증 먼저(writer 열기 전) — `np.ndarray` · ndim 4 · 마지막 축 3 · dtype uint8 · fps 는 bool 아닌 int/float 이고 유한 · > 0 · `proxy_frame_count(T) >= MIN_PROXY_FRAMES`, 위반은 ValueError(메시지에 무엇이 틀렸는지). H · W 가 홀수면 마지막 행/열 1개를 버린다(짝수화 후 2 미만이면 ValueError). imageio 는 함수 안에서 lazy import(Lambda 250MB 규율 — pipeline requirements 에 imageio 없음, functions/pipeline/requirements.txt:2). `imageio.get_writer(dest_path, fps=float(fps), codec=PROXY_CODEC, quality=None, pixelformat=PROXY_PIXEL_FORMAT, macro_block_size=1, output_params=["-crf", str(PROXY_CRF), "-preset", PROXY_PRESET], ffmpeg_log_level="error")` 로 열고 앞 keep 장을 `np.ascontiguousarray` 로 append, `finally` 에서 close. audio 는 넘기지 않는다. 반환 = 쓴 프레임 수. 예외는 그대로 raise.
- 모듈 docstring(한국어 why, 근거 `quick-261003-vsa`): 왜 프록시인가(위 objective 의 4K 대 프록시 실측), **시간축 결정과 산술**(마지막 프레임 무조건 제외 — §12-B 강제 프레임은 언제나 마지막이고 extract 가 강제 여부를 알리지 않는다, 길이 차 범위 식, step ≥ 2 에서 1 간격 미만), imageio-ffmpeg 의 `-r {:.02f}` 반올림 몫, 오디오 없음, 짝수화 이유, 폴백 · temp 정리는 호출측(pipeline `_build_student_proxy`) 책임.
- 커밋 `feat(261003-vsa): 학생 프록시 인코더 — 추출 프레임 → 작은 mp4, 마지막 프레임 제외 (GREEN)`.

**관측만(테스트 아님, SUMMARY 에 기록):** (1) 같은 프레임을 두 번 인코드해 sha256 이 같은지 — 로컬 결정론. (2) 합성 (199, 640, 360, 3) 배열(부드러운 그라디언트 + 프레임마다 이동하는 사각형) 인코드 시간 · 파일 크기 — 실제 영상과 내용이 다르다는 단서와 함께. 스크립트는 scratchpad 에(리포 밖).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_student_proxy.py tests/test_frame_extractor_effective_fps.py tests/test_frame_extractor_last_frame.py -q -p no:cacheprovider</automated>
  </verify>
  <done>새 테스트 전부 통과(skip 0 — 새 파일을 명령줄 맨 앞), 기존 frame_extractor 테스트 무회귀. diff = 새 모듈 1 + 새 테스트 1.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: app.py 부품 5개 + analysisVersion.geminiStudentInput 3-way 계약 (단위)</name>
  <files>backend/functions/pipeline/app.py, backend/shared/python/sunity_shared/models.py, backend/shared/python/sunity_shared/provenance.py, app/src/types/analysis.ts, docs/contract.md, backend/tests/test_gemini_student_proxy.py, backend/tests/test_analysis_provenance.py</files>
  <behavior>
    - `_gemini_student_proxy_enabled()`: 미설정 · "0" · "false" · "FALSE" · "" → False, "1" · "true" · " 1 " → True. 호출마다 env 를 읽는다(같은 테스트 안에서 setenv 뒤 바로 반영).
    - `_student_effective_fps(path)`: `_FRAME_EXTRACTOR` 가 None → None. `effective_fps_for` 가 None · 0 · −1 · NaN 을 주거나 raise → None. 9.9867 → 9.9867. target_fps(9.0)로 떨어지지 않는다(`_pipeline_frame_fps` 와 다른 점 — 단언으로 대조).
    - `_build_student_proxy(frames, *, fps, analysis_id)`: 성공 → 존재하는 경로, 이름 `student_proxy_` 로 시작 · `.mp4` 로 끝, INFO 로그에 `student_proxy ok` · `analysis_id=` · `frames=` · `fps=` · `bytes=` · `sha12=`. fps None → None, WARNING 에 `student_proxy fallback=original` 과 `reason=fps_unknown`, 인코더 미호출. frames None → `reason=frames_missing`. 인코더(`sunity_shared.gemini.student_proxy.encode_student_proxy` 를 monkeypatch)가 dest 에 부분 바이트를 쓰고 RuntimeError → None, `reason=RuntimeError`, 그 dest 파일이 남지 않는다.
    - `_extract_video_analysis_inputs_from_local` 훅(`_ensure_adapters` no-op · 가짜 `_FRAME_EXTRACTOR.extract`(T=60 작은 배열) · 가짜 `_RTMW_ENGINE.estimate`(qmg `_make_pose_frames(60)` 반환) · `_POLE_DETECTOR` None · keep_local_video=True): 순서 = extract → 훅(받은 배열이 extract 반환 객체 그 자체, `is`) → rtmw. 로그 `stage=frame_extract` 가 훅 기록보다 앞. 훅이 RuntimeError 를 던지면 WARNING 한 줄 뒤 rtmw 가 돌고 정상 반환(inputs.frames 가 그 배열), 영상 파일은 남아 있다. 훅을 안 넘기면 결과 angles 가 훅을 넘긴 런과 같다.
    - `_collect_vision_fault_context`(env `GEMINI_VISION_VETO_ENABLED=1`, mode1, reference_video_path 있음, `_build_selected_frame_pair` 기록 stub → None, `gemini_vision_scorer.assess_fault_context_video` 기록 stub → status skipped_error): `gemini_student_video_path="proxy.mp4"` 를 주면 assess 첫 인자 = proxy.mp4 · `preuploaded_student_handle` 그대로 전달 · still-pair `user_video_path` = 원본. 안 주면 assess 첫 인자 = 원본(지금과 같음).
    - `_attach_analysis_version(..., gemini_student_input=)`: "proxy640" · "original" → `analysisVersion.geminiStudentInput` 그 값. None 또는 인자 생략 → 키 없음이고 나머지 dict 가 생략 호출과 같다. "proxy" 같은 미등재 값 → 키 생략(fail-closed).
    - lockstep: `provenance.GEMINI_STUDENT_INPUTS == models.GEMINI_STUDENT_INPUTS == ("proxy640", "original")`. 두 `ANALYSIS_VERSION_KEYS` 가 같고 마지막 원소가 "geminiStudentInput". 저장 검증기가 `{"geminiStudentInput": "proxy640"}` 를 통과시킨다. analysis.ts 에 두 값 문자열이 따옴표째 있다.
  </behavior>
  <action>
**RED.** 새 파일 `backend/tests/test_gemini_student_proxy.py` 1부(부품 단위). 모듈 적재 = `from tests.test_ref_prefetch_scene_join import pipeline, net_attempts  # noqa: F401 — 픽스처 재등록` + 헬퍼 `_make_pose_frames` import. 각 테스트에서 `GEMINI_STUDENT_PROXY` 를 setenv/delenv 로 명시. 파일 머리 docstring: 목적(quick-261003-vsa), 1부 = 부품, 2부 = `_process` 통합(Task 3 에서 추가), 네트워크 0. 위 behavior 중 app.py · provenance 관련 묶음을 쓴다. test_analysis_provenance.py 는 :418~426 `test_builder_emits_only_registered_keys` 의 builder 호출에 `gemini_student_input="proxy640"` 을 더하고(주석: 전부 채운 호출의 뜻 유지 — quick-261003-vsa), 값 lockstep 테스트 2개(provenance↔models 값 튜플 · analysis.ts 에 두 값)를 추가한다. RED = AttributeError(`_gemini_student_proxy_enabled` 등) · TypeError(unexpected kwarg) 류. 커밋 `test(261003-vsa): 프록시 부품 · geminiStudentInput 계약 단위 테스트 (RED)`.

**GREEN — app.py (모듈 함수 · 시그니처만, `_process` 는 Task 3).**
- `_gemini_student_proxy_enabled()` — `_post_stage_parallel_enabled`(:521) 바로 뒤. `os.environ.get("GEMINI_STUDENT_PROXY", "0")` 을 strip · lower 해 `_VISION_FALSY` 에 없으면 True(같은 모양, **기본값만 "0"**). docstring: 기본 OFF, Pod 동등성 검증 + belle 판정 뒤에 켠다, 매 호출 env(서버 재시작만으로 전후 대조), quick-261003-vsa.
- `_student_effective_fps(video_path) -> float | None` — `_pipeline_frame_fps`(:8087) 바로 앞. `_FRAME_EXTRACTOR.effective_fps_for` 만 보고, 없거나 비정상(None · ≤0 · NaN · inf · 예외)이면 None. docstring: 프록시 fps 는 추측 금지 — 9.0 으로 떨어지면 시간축이 ≈10% 어긋난다(frame_extractor.effective_fps 주석의 quick-260810-cbt 피해와 같은 종류), 그래서 `_pipeline_frame_fps` 의 fail-open 을 쓰지 않는다.
- `_build_student_proxy(frames, *, fps, analysis_id) -> str | None` — `_safe_unlink_local_video`(:538) 뒤. 순서: fps 판정(None/비정상 → reason=fps_unknown) → frames None → reason=frames_missing → `tempfile.NamedTemporaryFile(prefix="student_proxy_", suffix=".mp4", delete=False)` 로 경로를 만들고 닫음 → 함수 안 lazy `from sunity_shared.gemini import student_proxy as _student_proxy` 후 `_student_proxy.encode_student_proxy(frames, fps, path)`(모듈 속성 호출 — 테스트가 바꿔 끼울 수 있게) → 성공이면 sha256 앞 12자 · 바이트 수를 INFO `student_proxy ok analysis_id=%s frames=%d fps=%.4f bytes=%d sha12=%s` 로 남기고 경로 반환. 어떤 예외든 `_safe_unlink_local_video(path)` 후 WARNING `student_proxy fallback=original analysis_id=%s reason=%s detail=%s`(reason = 예외 클래스명, detail = str(exc)[:200]) 하고 None. raise 하지 않는다. sha12 는 Pod 검증에서 캐시 문서를 찾는 손잡이다(SUMMARY 검증 계획).
- `_extract_video_analysis_inputs_from_local` 에 kw-only `after_frame_extract: Callable[[np.ndarray], None] | None = None` 추가. frame_extract `with` 블록 바로 뒤 · rtmw `with` 블록 앞에서, None 이 아니면 try 로 감싸 `after_frame_extract(frames)` 를 부르고 예외는 `log.warning("after_frame_extract 실패 — 분석 계속 analysis_id=%s", analysis_id, exc_info=True)` 로 삼킨다(훅 실패가 추출 실패로 바뀌어 unlink_on_error · 분석 실패로 번지지 않게). docstring 에 인자 뜻(quick-261003-vsa 프록시 생성 접점, 미전달 = 종전과 동일)을 한 단락. 다른 줄은 손대지 않는다.
- `_collect_vision_fault_context` 에 kw-only `gemini_student_video_path: str | None = None` 추가. assess 호출(:2777~2786)의 첫 인자만 `gemini_student_video_path or local_video_path` 로. `missing_current_video` 게이트(:2672) · `_build_selected_frame_pair(user_video_path=local_video_path)`(:2690)는 그대로 — still 이미지는 원본 9fps 프레임 · 원본 실효 fps 공간이다. 주석: VisionVetoCache 키가 이 경로의 파일 hash 라서 핸들과 같은 파일을 줘야 한다(gemini_vision_scorer.py:1294), quick-261003-vsa.
- `_attach_analysis_version` 에 kw-only `gemini_student_input: str | None = None` 추가해 `provenance.build_analysis_version(..., gemini_student_input=gemini_student_input)` 로 넘긴다. docstring 한 줄.

**GREEN — 계약 3-way.**
- models.py :244~289 블록: `GEMINI_STUDENT_INPUT_PROXY = "proxy640"` · `GEMINI_STUDENT_INPUT_ORIGINAL = "original"` · `GEMINI_STUDENT_INPUTS = (PROXY, ORIGINAL)` 를 정의하고 `ANALYSIS_VERSION_KEYS` **맨 끝**에 `"geminiStudentInput"`. 블록 주석에 키 설명(토글 ON 에서만 실림, 값 뜻, 부재 = 토글 OFF 또는 도입 전 = 원본 입력).
- provenance.py: models 를 import 하지 않는다(models.py 하단이 분석 모듈을 re-export 해 무겁다 — provenance 는 stdlib 전용 유지). 같은 값 튜플 `GEMINI_STUDENT_INPUTS` 를 자체 정의(테스트가 drift 를 막는다), `ANALYSIS_VERSION_KEYS` 를 `(...) + tuple(flags) + ("geminiStudentInput",)` 로 — models 와 같은 순서. `build_analysis_version` 에 kw-only `gemini_student_input: str | None = None` — `GEMINI_STUDENT_INPUTS` 안의 값일 때만 `out["geminiStudentInput"]` 에 싣고 그 밖은 키 생략(fail-closed, 추측 금지). docstring Args 에 한 줄.
- analysis.ts `AnalysisVersion`(:1052~1059)에 `geminiStudentInput?: 'proxy640' | 'original'; // quick-261003-vsa — GEMINI_STUDENT_PROXY ON 일 때만. 부재 = OFF 또는 도입 전(원본 입력).` 위 주석 블록의 lockstep 목록은 그대로.
- contract.md §11.13(:2516~2580): 코드 블록 필드 목록에 `geminiStudentInput  string  optional ← 학생 영상 Gemini 입력 ("proxy640" | "original")` 한 줄, 그리고 출처 · 값 · 부재 뜻 단락 — "proxy640" = 추출 프레임(긴 변 640 · 실효 fps · 마지막 프레임 제외)을 묶은 mp4 로 Gemini 소비처 전부를 불렀다, "original" = 토글 ON 이었지만 프록시를 못 만들어(인코더 예외 · fps 미상) 원본으로 폴백, **부재 = 토글 OFF 또는 이 키 도입 전 doc → 원본 입력**. 이 키가 "부재 = 못 구했다" 관례의 예외인 이유(OFF doc 을 지금과 같게 두는 기준선)를 한 문장. 출처 = pipeline `_process` 의 gemini_student_input → `_attach_analysis_version` → `provenance.build_analysis_version`. 채점 무접촉 · 앱 미소비 문구는 절 공통 규칙이 그대로 적용.
- 커밋 `feat(261003-vsa): 프록시 부품(토글 · fps · 생성 · 추출 훅 · veto 경로 인자) + analysisVersion.geminiStudentInput 계약 (GREEN)`.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_gemini_student_proxy.py tests/test_analysis_provenance.py tests/test_student_proxy.py tests/test_ref_prefetch_scene_join.py tests/test_stage_timing.py tests/test_post_stage_parallel.py -q -p no:cacheprovider && cd /Users/kimtaesung/Dev/SunityMotion/app && npx tsc --noEmit</automated>
  </verify>
  <done>1부 단위 테스트 · provenance 테스트(갱신 1 + 새 2) 통과, qmg · stage_timing · post_stage_parallel 하네스 무회귀(훅 인자는 아직 아무도 안 넘긴다), app 타입체크 통과. `_process` 무변경.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: _process 배선 + 통합 테스트(OFF 잠금 · ON 소비처 · 폴백 · 정리) + timingsMs 계약 + 전체 무회귀</name>
  <files>backend/functions/pipeline/app.py, backend/tests/test_gemini_student_proxy.py, docs/contract.md</files>
  <behavior>
    하네스 = qmg `_install`(test_ref_prefetch_scene_join.py:418) 을 부른 뒤 아래를 덧까는 `_install_proxy`. 모든 테스트 `net_attempts == []`.
    - [OFF 잠금] env 미설정 · "0" × prefetch ON · OFF, mode1. `_extract_video_analysis_inputs_from_local` 가 받은 kwargs 키 = {keep_local_video, timings_ms, analysis_id, unlink_on_error} 정확히(훅 없음). prefetch ON: 학생 원본 업로드가 포즈 가짜 **안에서 기다리는 동안** gemini 스레드에서 시작된다(Event 5초 wait True) — 다운로드 시점 제출. prefetch OFF: 학생 원본 업로드가 MainThread. 학생 원본 업로드 1회, 그 밖의 학생 경로 업로드 0, `_build_student_proxy` 호출 0. scene · recognizer(`frames`) · collect(`local_video_path` 와 `gemini_student_video_path` 둘 다 원본) · coach(`videoPath`) 가 원본 경로이고 핸들은 전부 같은 객체(`is`). complete 의 result `timingsMs` 에 student_proxy_encode 없음, `analysisVersion` 에 geminiStudentInput 없음.
    - [ON mode1 prefetch] 훅이 받은 프레임으로 프록시가 1개 만들어지고, 그 경로가 업로드 시점에 존재(크기 > 0)하며 업로드 스레드 이름이 "gemini" 로 시작. 학생 원본 업로드 0. scene · recognizer · collect(`gemini_student_video_path` · `preuploaded_student_handle`) · coach(`videoPath` · `preuploadedHandle`) 전부 프록시 경로 + 같은 핸들 객체(`is`, 세션이 프록시 경로에 만든 그 핸들). collect 의 `local_video_path` 는 원본. `_pipeline_frame_fps` 인자 ⊆ {원본, None}, `_build_fault_zoom_comparisons` 2번째 인자 = 원본(호출 ≥1), `_run_deferred_compare_render` kwargs `local_video_path` = 원본(호출 ≥1), `_call_wave2_keypoint_augmenter` 가 불렸다면 원본. timingsMs 에 student_proxy_encode(int), analysisVersion.geminiStudentInput == "proxy640". 런 뒤 프록시 · 원본 파일 없음, 사건 순서 close < unlink(프록시), 프록시 핸들 delete 기록.
    - [ON mode3 prefetch] 기준 다운로드 0, recognizer · scene · coach 프록시, geminiStudentInput "proxy640".
    - [ON prefetch OFF] 프록시 업로드가 MainThread(student_upload_wait 자리), scene 동기 호출이 프록시 경로 + 그 핸들, 원본 업로드 0.
    - [폴백 — 인코더 예외] `sunity_shared.gemini.student_proxy.encode_student_proxy` 를 dest 에 부분 바이트를 쓰고 RuntimeError 를 던지는 가짜로: WARNING 에 `student_proxy fallback=original` · `reason=RuntimeError`, 학생 원본 업로드 정확히 1회(훅 시점 gemini 스레드), Gemini 소비처 전부 원본 + 원본 핸들, geminiStudentInput == "original", timingsMs 에 student_proxy_encode 있음, 부분 파일 없음, complete 1회.
    - [폴백 — fps 미상] `_student_effective_fps` stub 이 None → `reason=fps_unknown`, 인코더 미호출, 원본 경로로 완주. (다른 ON 묶음은 stub 이 학생 원본 다운로드 경로로 불렸음을 단언 — 프록시 fps 는 원본의 실효 fps.)
    - [조기 실패 — 훅 뒤] 포즈 가짜가 훅을 부른 뒤 raise(프록시 업로드에 0.3초 지연): `_process` 가 그 예외로 끝나고, 사건 순서 upload_done(프록시) < close < unlink(프록시), 프록시 핸들 delete 기록, 프록시 · 원본 파일 없음, complete 미호출.
    - [조기 실패 — 훅 전] 포즈 가짜가 훅 전에 raise: `_build_student_proxy` 0회, 학생 경로 업로드 0, 원본 파일 없음.
  </behavior>
  <action>
**RED.** test_gemini_student_proxy.py 2부. `_install_proxy(pipeline, monkeypatch, tmp_path, *, mode, prefetch, proxy_env, encoder_error=False, fps_known=True, pose_error_before_hook=None, pose_error_after_hook=None, proxy_upload_delay=0.0)`:
- `h = _install(...)` 뒤 env `GEMINI_STUDENT_PROXY` 설정/삭제.
- 세션: `fs_mod.GeminiFileSession`(이제 qmg 기록 클래스)을 한 번 더 상속해 `_upload_and_wait_active` 에서 (경로, 스레드 이름, 존재 여부, 크기)를 락 안 리스트에 기록하고, 학생 원본 경로면 Event set, 프록시 경로(이름이 `student_proxy_` 로 시작)면 proxy_upload_delay 만큼 쉰 뒤 super 호출.
- 포즈: `orig = pipeline._extract_video_analysis_inputs_from_local`(qmg 가짜)를 잡고, 새 가짜 `(local, pole, *, after_frame_extract=None, **kw)` 가 kwargs 키 집합을 기록 → (OFF + prefetch 면 학생 원본 업로드 Event 를 5초 기다려 결과 기록) → pose_error_before_hook → 훅이 있으면 `after_frame_extract(frames)`(frames = (12, 64, 96, 3) uint8, 프레임마다 다른 회색) → pose_error_after_hook → `orig(local, pole, **kw)` 를 그대로 반환. inputs.frames 는 qmg 처럼 None 으로 둔다 — 프레임을 채우면 사후 spot_check 가 그 프레임으로 Gemini 키를 찾으러 나가 소켓 가드에 걸린다(svg SUMMARY 관측 12 의 탐침은 frames None 에서 소켓 0). 프록시는 훅이 받은 배열로만 만든다.
- `monkeypatch.setattr(pipeline, "_student_effective_fps", stub)` — 받은 경로를 기록하고 fps_known 이고 realpath 가 학생 원본 경로면 10.0, 아니면 None. `_FRAME_EXTRACTOR` 는 건드리지 않는다(`_pipeline_frame_fps` 가 qmg 하네스와 같은 값을 내게 — 진짜 `_student_effective_fps` 는 Task 2 단위 테스트가 잠갔다).
- recognizer: `monkeypatch.setattr(pipeline, "_RECOGNIZER", 기록 가짜)` — `recognize(angles, frames=None, *, preuploaded_handle=None, motion_hint=None, unregistered_hook=None)` 이 (frames, 핸들, 경로 존재)를 기록하고 `technique.FallbackRecognizer().recognize(angles)` 를 돌려준다.
- scene: `_call_wave1_scene_finder` 를 (경로, 핸들, 스레드) 기록 + `{}` 반환으로. coach: `_run_deferred_coach_text` 를 kwargs["coach_context"] 의 `videoPath` · `preuploadedHandle` 기록으로. 원본을 감싼 기록 spy: `_pipeline_frame_fps` · `_build_fault_zoom_comparisons` · `_run_deferred_compare_render` · `_call_wave2_keypoint_augmenter` · `_build_student_proxy`(반환 경로 수집).
- 인코더 예외 케이스: `monkeypatch.setattr(student_proxy_module, "encode_student_proxy", 가짜)` — dest 에 b"partial" 을 쓰고 RuntimeError, dest 를 수집.
위 behavior 8묶음을 쓴다. RED 확인: OFF 잠금은 지금 코드로 통과해야 하고(현 동작의 박제), ON 묶음은 실패(원본 업로드 · 훅 없음). 커밋 `test(261003-vsa): _process 프록시 통합 — OFF 잠금 · ON 소비처 · 폴백 · 정리 (RED)`.

**GREEN — `_process` (:8974~ ) 배선.** 기존 줄의 상대 순서는 바꾸지 않는다.
- 세션 생성 뒤 prefetch 블록 앞(:9064 근처)에서 한 번 읽는다: `proxy_active = keep_local_video and _gemini_student_proxy_enabled()` — 분석 도중 env 를 다시 읽지 않는다(한 분석 안 입력 일관성). 이어 `student_proxy_path: str | None = None` · `gemini_student_input: str | None = None` · `hook_gemini_path: str | None = None` 를 둔다(`student_handle_future` · `scene_future` 와 같은 자리, try 밖).
- prefetch 블록(:9078~9097): `executor is not None and not proxy_active` 일 때만 지금의 학생 업로드 + `_scene_prefetch` 제출을 한다(그 블록 텍스트는 그대로 두고 조건만 감싼다). 기준 다운로드/업로드 제출(:9105~9113)과 `gemini_upload_prefetch_submit` 마커는 지금 그대로 executor 가 있으면 항상.
- 훅 클로저 `_on_student_frames(frames)` 를 try 앞에 정의(`nonlocal student_proxy_path, gemini_student_input, hook_gemini_path, student_handle_future, scene_future`): `with _stage(timings_ms, analysis_id, "student_proxy_encode"):` 안에서 `student_proxy_path = _build_student_proxy(frames, fps=_student_effective_fps(local_video_path_dl), analysis_id=analysis_id)` → `hook_gemini_path = student_proxy_path or local_video_path_dl` · `gemini_student_input = models.GEMINI_STUDENT_INPUT_PROXY if student_proxy_path else models.GEMINI_STUDENT_INPUT_ORIGINAL`(이 둘을 submit 보다 먼저) → executor 가 있으면 `student_handle_future = executor.submit(session.get_or_upload, hook_gemini_path)` 와 같은 본문(핸들 대기 → `_call_wave1_scene_finder(local_video_path=경로, is_reference=is_reference_local, preuploaded_handle=핸들)`)의 scene 클로저를 기본인자 바인딩으로 제출. 주석(한국어 why): 프록시는 프레임이 있어야 만들 수 있어 이 접점(frame_extract 뒤 · RTMW 전)에서 만든다, 인코드는 메인 스레드(프레임 배열 동시 접근 0), 업로드는 RTMW 와 겹친다, 제출 순서와 교착 0 논리, 근거 quick-261003-vsa(4K 업로드→ACTIVE 36초 · 첫 호출 43초 vs 프록시 5.7초 · 3.2초).
- 추출 호출(:9123~9131)에 `**({"after_frame_extract": _on_student_frames} if proxy_active else {})` — OFF 는 지금과 같은 인자.
- 추출 뒤 `local_video_path` 대입(:9136) 직후: proxy_active 면 `gemini_student_path = hook_gemini_path or local_video_path`, `gemini_student_input` 이 None 이면(훅 미실행 · 훅 안 예외) ORIGINAL 로, 그리고 INFO `gemini_student_input analysis_id=%s input=%s`. 아니면 `gemini_student_path = local_video_path`(그 객체).
- `student_upload_wait` 동기 폴백(:9159~9161)의 `local_video_path` → `gemini_student_path`(조건식 포함). 동기 scene(:9172~9176)의 `local_video_path=` → `gemini_student_path`. recognizer(:9293) `frames=gemini_student_path`. veto collect(:9796~9813)에 `gemini_student_video_path=gemini_student_path`(local_video_path 인자는 그대로). `_build_coach_context(local_video_path=gemini_student_path, ...)`(:9832) — 주석: 이 인자는 `videoPath`(coach B Gemini 입력) 하나에만 쓰인다. `_attach_analysis_version(..., gemini_student_input=gemini_student_input)`(:10545).
- 바꾸지 않는 자리(주석 한 줄씩 — 왜 원본인가): `_pipeline_frame_fps(local_video_path)` 세 곳 · `_call_wave2_keypoint_augmenter` · 레거시 `_apply_vision_veto` 두 곳 · fault_zoom · compare_render · outer finally 의 원본 unlink. (augmenter · 레거시 veto 는 위 context 표 8·9 의 근거를 짧게.)
- 정리: 조기 실패 except(:9177~9198)의 기준 temp unlink 뒤, outer finally(:10753~10781)의 기준 prefetch temp unlink 뒤에 각각 `if student_proxy_path is not None: _safe_unlink_local_video(student_proxy_path)`. 주석: join → close 뒤라 업로드 스레드가 읽는 중 unlink 0, 프록시 핸들은 close 가 지웠다.
- 커밋 `feat(261003-vsa): _process 학생 Gemini 입력 프록시 배선 — GEMINI_STUDENT_PROXY 기본 OFF (GREEN)`.

**계약 — docs/contract.md §4 timingsMs(:747~777).** svg 의 `post_parallel` 항목 뒤에 항목 하나: `student_proxy_encode` (quick-261003-vsa) = `GEMINI_STUDENT_PROXY` ON 일 때만, frame_extract 직후 · rtmw 전 메인 스레드에서 추출 프레임을 Gemini 입력용 작은 mp4 로 묶는 시간(실패해 원본으로 폴백한 경우 포함). OFF 면 키 없음. ON 이면 `student_upload_wait` 은 프록시 업로드 잔여 대기다(이 변경 전후 doc 의 값은 같은 물건이 아니다). 같은 커밋에 넣거나 `docs(261003-vsa): ...` 로 따로.

**전체 무회귀.** backend 전체 pytest(기준선 5973 passed / 20 skipped + 이번 새 테스트 수 = 기대 passed, skip 증가 0, 실패 0) · app 타입체크. 통합 테스트 반복 3회(스레드 꼬임 확인).

**SUMMARY (관측 · 진단 분리, `[확인]`/`[미확인]` 문장마다).** 반드시 담을 것:
1. 학생 Gemini File API 소비처 전수 표 — 바꾼 뒤의 파일:줄과 프록시/원본 여부(context 표를 실제 줄 번호로 갱신).
2. 시간축 결정 · 테스트 실측(길이 차) · Gemini 초→프레임 환산 소비처와 쓰는 fps.
3. 폴백 결정과 근거. 캐시 분리 근거.
4. Task 1 관측(로컬 결정론 · 합성 인코드 시간).
5. **Pod 동등성 검증 계획(오케스트레이터 실행).** 아래를 그대로 옮기고 실제 확인한 경로로 갱신:
   - 입력: `s3://sunity-motion-pilot-videos/fixtures/phase15/{power-spin,climb,peter-pan,pdshape,kip-up}/{correct,fault}.mp4` 10편(원장 `backend/training/data/pairs.jsonl` 의 `pr_*_je_001`, sha256 = clips.jsonl), mode1 · 기준 `ref-{motion}`(09-24 ig3 10편 표 `.planning/quick/260924-ig3-window-constant/260924-ig3-SUMMARY.md` §3 과 같은 묶음).
   - 캐시 우회: 런마다 메타데이터만 바꾼 remux 사본 — `imageio_ffmpeg.get_ffmpeg_exe()` 로 `-i in.mp4 -map 0 -c copy -metadata comment=vsa-<arm>-<n>` → sha256 이 원본 · 다른 사본과 다른지 확인. 사본은 scratchpad 에만(리포 · manifest 밖 — 메모리 human-videos-stay-out-of-manifest), **intake 원장(clips.jsonl)에 등록하지 않는다**(원장은 주 1회 학습 입력).
   - **ON 캐시 함정:** remux 는 디코드 프레임을 안 바꾸므로 같은 fixture 의 ON 프록시는 런마다 같은 바이트일 수 있다(로컬 결정론 관측). 그러면 두 번째 ON 런은 TechniqueCache(Firestore + 프로세스 메모리) · VisionVetoCache(Firestore) 적중이다. → ON 은 fixture 당 1회만 돌리거나, 반복하려면 `student_proxy ok ... sha12=` 로그로 그 hash 의 캐시 문서를 지우고 서버를 재시작한다. 비교에 쓰는 모든 런은 로그 `TechniqueCache .*hit|VisionVetoCache rich hit` 0 을 확인.
   - 순서: 같은 Pod · 같은 GPU 종류에서 서버 재시작으로 env 만 바꿔 OFF1(10) → ON(10, `GEMINI_STUDENT_PROXY=1`) → OFF2(10). 경로 = `backend/scripts/e2e_app_path.py --video <사본> --mode mode1 --reference ref-<motion> --uid <고정 익명 uid>`, 직렬, 앞 런의 `분석 완료` 로그(사후 단계 끝) 뒤 다음 런(메모리 pipeline-not-concurrency-safe-eval-serial).
   - 비교 항목: overallScore · deductionBreakdown(final + records 의 criterion/points) · visionVeto(status · severity · primaryFault · faultJoints) · recognizedMotionId/Name · dimensionScores(흔들림 창이 key moment hold 를 쓴다) · analysisVersion.geminiStudentInput · stage(s3_download · frame_extract · student_proxy_encode · rtmw · student_upload_wait · recognizer · veto_collect · scene_finder · 점수까지 벽시계).
   - 판정 규칙: OFF1↔OFF2 차이 = fixture 별 Gemini 흔들림 기준선. ON 이 그 범위를 벗어나는 fixture 는 belle 판정 대상(사진 + ○×, 메모리 belle-report-format-verdict-first). 켜기(start_server.sh 에 export)는 belle 판정 뒤 별도 단위.
   - Pod 로그 grep 0 기대: `student_proxy fallback` · `Traceback` · `RESOURCE_EXHAUSTED` · `429`.
   - 기대 [추정, 미확인]: student_upload_wait 11~18 → 1~2초, recognizer 첫 호출 43초 → 수 초, 점수까지 ≈105 → ≈55~60초. 정확도 위험 [미확인]: 640 해상도 · 오디오 없음 · crf23 압축.
6. STATE.md · ROADMAP 은 건드리지 않는다(오케스트레이터 몫).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && for i in 1 2 3; do .venv/bin/python -m pytest tests/test_gemini_student_proxy.py tests/test_ref_prefetch_scene_join.py tests/test_post_stage_parallel.py -q -p no:cacheprovider || exit 1; done && .venv/bin/python -m pytest tests/test_student_proxy.py tests/test_stage_timing.py tests/test_analysis_provenance.py -q -p no:cacheprovider && .venv/bin/python -m pytest tests -q -p no:cacheprovider && cd /Users/kimtaesung/Dev/SunityMotion/app && npx tsc --noEmit</automated>
  </verify>
  <done>통합 8묶음 3회 연속 통과, qmg · svg · stage_timing · provenance 무회귀, backend 전체 실패 0 · skip 20 그대로, 타입체크 통과. `grep -v '^\s*#' backend/functions/pipeline/app.py | grep -c "gemini_student_path"` ≥ 7. `git diff --stat` 코드 파일 = frontmatter files_modified 9개뿐(template.yaml · runpod_inference · start_server.sh · 채점 모듈 · Gemini 모듈 프롬프트/설정 무변경). SUMMARY 에 소비처 표 · 시간축 · 폴백 · Pod 검증 계획.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Pod 로컬 디스크 → Gemini File API | 학생 영상(파생본 포함)이 외부 저장소로 나간다 — 프록시도 같은 학생 영상의 파생본 |
| Pod temp 디렉터리 | 학생 영상 원본 · 프록시 temp 파일이 분석 수명 동안 놓인다 |
| Pod env → 분석 경로 | `GEMINI_STUDENT_PROXY` 로 Gemini 입력이 바뀐다 |
| Gemini 판정 캐시(Firestore) | 입력 파일 hash 로 판정을 재사용한다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-vsa-01 | Information disclosure | 프록시 temp 파일(학생 영상 파생) | mitigate | 성공 · 조기 실패 모두 join → close 뒤 `_safe_unlink_local_video(student_proxy_path)`, 인코딩 실패 시 `_build_student_proxy` 가 부분 파일을 즉시 지움 — 통합 테스트가 세 경로 모두 파일 부재를 단언 |
| T-vsa-02 | Denial of service | Gemini File API 저장소 적체(20GB 사고 계보) | mitigate | 프록시는 세션 `get_or_upload` 로만 올리고 `session.close()` 가 일괄 delete — 테스트가 프록시 핸들 delete 사건을 단언. 자체 업로드 폴백은 각 소비처의 기존 finally delete 규율 그대로 |
| T-vsa-03 | Tampering | 판정 캐시 혼입(원본 판정 ↔ 프록시 판정) | mitigate | Gemini 소비처에 경로와 핸들을 같은 파일로 준다 → TechniqueCache · VisionVetoCache 키(파일 SHA256)가 입력과 일치. 테스트가 각 소비처의 경로 = 핸들 파일을 단언 |
| T-vsa-04 | Repudiation | 어느 입력으로 판정했는지 기록 부재 | mitigate | analysisVersion.geminiStudentInput("proxy640"/"original") + 구조 로그 `gemini_student_input` · `student_proxy ok/fallback` |
| T-vsa-05 | Tampering | 시간축 어긋남으로 다른 순간을 판정(still · hold 창) | mitigate | 마지막 프레임 제외 규칙 + 실효 fps(추측 금지, fps 미상이면 원본 폴백) — test_student_proxy.py 가 길이 오차 · 프레임 대응을 실제 인코드로 잠금 |
| T-vsa-06 | Denial of service | 인코더 hang · 예외가 분석을 멈춤 | accept / mitigate | 예외는 원본 폴백(분석 완주, 테스트 잠금). hang 은 timeout 장치 없음 — 640px · 분석당 ≤ 1200장 · 로컬 수십~수백 ms 라 수용, Pod 에서 `student_proxy_encode` stage 로 관측 |
| T-vsa-SC | Tampering | 패키지 설치 | accept | 새 설치 0 — imageio · imageio-ffmpeg 는 runpod_inference/requirements.txt:16~17 기존 의존 |
</threat_model>

<verification>
- 세 Task 의 automated verify 통과(Task 3 = backend 전체 + 타입체크 포함).
- 기본 OFF 확인: `grep -n 'GEMINI_STUDENT_PROXY' backend/runpod_inference/start_server.sh backend/template.yaml` 결과 0.
- 채점 무변경: `git diff --stat` 에 dimensions.py · deduction_engine.py · vision_veto.py · gemini_vision_scorer.py · gemini_technique_recognizer.py · scene_finder.py · coach_writer_v2.py · client.py · file_session.py · frame_extractor.py 없음.
- 소켓 가드: 통합 테스트 전부 `net_attempts == []`.
</verification>

<success_criteria>
- `GEMINI_STUDENT_PROXY` 미설정이면 `_process` 의 호출 인자 · 순서 · 저장 result 가 지금과 같다(OFF 잠금 테스트).
- 켜면 학생 4K 원본은 Gemini 에 올라가지 않고 Gemini 소비처 5종이 같은 프록시를 받으며, 비-Gemini 소비처는 원본 그대로(통합 테스트).
- 프록시 길이 오차 ≤ 프레임 간격 1개 · 프레임 i 대응(실제 인코드 테스트).
- 실패 폴백 · 정리 · stage 기록 · analysisVersion 기록이 테스트로 잠김.
- backend 전체 실패 0(기준선 5973 passed / 20 skipped + 새 테스트), 타입체크 통과, 배포 0.
- SUMMARY 에 Pod 동등성 검증 계획(입력 경로 · remux 우회 · ON 캐시 함정 · 순서 · 비교 항목 · 판정 규칙).
</success_criteria>

<output>
Create `.planning/quick/261003-vsa-gemini-student-proxy-video-toggle/261003-vsa-SUMMARY.md` when done.
</output>
</content>
</invoke>
