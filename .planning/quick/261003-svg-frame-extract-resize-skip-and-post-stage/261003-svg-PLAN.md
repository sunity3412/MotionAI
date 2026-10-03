---
phase: quick-261003-svg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/frame_extractor.py
  - backend/tests/test_frame_extractor_resize_skip.py
  - backend/functions/pipeline/app.py
  - backend/tests/test_post_stage_parallel.py
  - backend/tests/phase32/test_spot_check.py
  - docs/contract.md
autonomous: true
requirements: [QUICK-261003-svg]

must_haves:
  truths:
    - "FfmpegFrameExtractor.extract 의 출력은 옛 구현과 바이트 단위로 같다 — step 이 나눠떨어지는 길이 · 안 떨어지는 길이 · start_s/end_s 구간 · start 만 · end 가 영상 밖 · step 1 · RGBA 입력 전부"
    - "extract 는 솎아 버리는 프레임을 축소하지 않는다 — `_resize` 호출 수 = 남는 프레임 수 + (마지막 프레임 강제 포함이 일어나면 1)"
    - "POST_STAGE_PARALLEL 미설정(기본 ON)이면 코칭 문장(coach_text, 메인 스레드)과 곁가지(coach_audio → fault_zoom → spot_check, post_side 스레드)가 겹쳐 돌고, compare_render 는 두 가지가 다 끝난 뒤 메인 스레드에서 곁가지가 돌려준 coach_audio_items · fault_zoom_items 객체를 그대로 받는다"
    - "POST_STAGE_PARALLEL=0 이면 지금 직렬과 같다 — coach_text → coach_audio → fault_zoom → spot_check → compare_render, 전부 메인 스레드"
    - "두 모드에서 각 사후 단계는 같은 인자로 정확히 1회 불리고, Firestore 부분 갱신 호출(함수 · status)의 집합이 같고, in-memory result 의 키가 같다 — timingsMs 만 ON 에서 post_parallel 하나가 더 있다"
    - "한 가지의 실패가 다른 가지를 막지 않는다 — fault_zoom 렌더 예외면 faultZoomStatus failed 로 마킹되고 coach_text · spot_check · compare_render 는 계속 돈다. 곁가지에서 예기치 못한 예외가 새도 compare_render 는 빈 목록으로 계속 돈다"
    - "정리 순서가 그대로다 — 사후 단계가 전부 끝난 뒤에 executor.shutdown → session.close → 임시 파일 unlink. 메인 가지(coach_text)가 예외로 빠져도 곁가지가 끝난 뒤에 예외가 전파된다"
    - "채점 무변경 — 채점 · veto · Gemini 설정 · 프롬프트 · 각 단계 내부 알고리즘에 diff 0. RTMW(GPU)를 쓰는 compare_render 는 어떤 단계와도 겹치지 않는다"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/frame_extractor.py"
      provides: "버리는 프레임 축소 생략 — 원본 참조만 들고 있다가 마지막 강제 포함 때만 축소"
      contains: "last_raw"
    - path: "backend/tests/test_frame_extractor_resize_skip.py"
      provides: "옛 구현 참조 함수 대비 바이트 동일 + `_resize` 호출 수 spy"
      min_lines: 90
    - path: "backend/functions/pipeline/app.py"
      provides: "_post_stage_parallel_enabled · _run_post_stages + _process 사후 블록 클로저 배선"
      contains: "def _run_post_stages"
    - path: "backend/tests/test_post_stage_parallel.py"
      provides: "오케스트레이터 단위 테스트 + _process 통합(qmg 하네스 재사용)"
      min_lines: 220
    - path: "docs/contract.md"
      provides: "timingsMs 예시 키에 post_parallel"
      contains: "post_parallel"
  key_links:
    - from: "_process 사후 블록 (지금 :10502~:10624)"
      to: "_run_post_stages"
      via: "클로저 3개(_post_coach_text · _post_side · _post_compare_render) + parallel=_post_stage_parallel_enabled()"
      pattern: "_run_post_stages\\("
    - from: "_run_post_stages (parallel)"
      to: "분석-로컬 ThreadPoolExecutor"
      via: "max_workers=1, thread_name_prefix=\"post_side\" — with 블록 종료가 join"
      pattern: "thread_name_prefix=\"post_side\""
    - from: "_post_side"
      to: "_run_deferred_coach_audio → _run_deferred_fault_zoom → _run_deferred_spot_check"
      via: "같은 스레드 안 순차, stage_timings 는 곁가지 전용 dict"
      pattern: "_run_deferred_spot_check\\("
    - from: "_run_post_stages"
      to: "compare_render_stage(coach_audio_items, fault_zoom_items)"
      via: "곁가지 join 뒤 메인 스레드"
      pattern: "compare_render_stage\\("
---

<objective>
분석 대기 시간 두 군데를 줄인다. 채점 결과 · 출력물은 무변경.

Task A (점수 도착 시간): `FfmpegFrameExtractor.extract` 가 솎아 버리는 프레임까지 매번 `_resize` 하는 것을 없앤다. 로컬 실측 [확인 — 오케스트레이터 scratchpad fx_bench.py]: 같은 학생 영상(HEVC 2160×3840 30fps 593프레임) 25.7초 → 15.7초, 출력 (199,640,360,3) `np.array_equal` True. Pod `frame_extract` 22.5~26.1초 [확인 — qmg evidence 로그 4건].

Task B (화면이 다 채워지는 시간): 점수 뒤 사후 단계를 두 가지로 겹친다 — 메인 = coach_text, 곁가지 = coach_audio → fault_zoom → spot_check. compare_render 는 두 가지가 끝난 뒤. env `POST_STAGE_PARALLEL`(기본 ON, "0" 이면 지금 직렬 그대로).

Purpose: belle 10-02 이후 분석 시간 단축 트랙(quick-261003-qmg 다음). 실증(2026-10 중순) 전 체감 대기.
Output: frame_extractor.py · app.py 수정, 새 테스트 2개, test_spot_check.py 소스 순서 게이트 앵커 갱신, contract.md 한 줄. 배포 안 함.

Task A 와 B 는 서로 독립이다 — Task 1 은 혼자 커밋되고, Task 2 · 3 을 보류해도 Task 1 은 그대로 유효하다.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/quick/261003-qmg-ref-gemini-prefetch-and-scene-join-move/261003-qmg-SUMMARY.md
@backend/shared/python/sunity_shared/analysis/frame_extractor.py
@backend/tests/test_frame_extractor_last_frame.py
@backend/tests/test_ref_prefetch_scene_join.py
@backend/tests/phase32/test_spot_check.py

app.py 는 11,211줄 — 통째로 읽지 말고 아래 줄 범위만 읽는다:
:49 (import) · :151~168 `_stage` · :462 `_VISION_FALSY` · :505~519 `_gemini_upload_prefetch_enabled` · :5097~5145 `_run_deferred_fault_zoom` · :5238~5299 `_run_deferred_coach_audio` · :5312~5551 `_run_deferred_coach_text` · :7077~7159 `_run_deferred_spot_check` · :9036~9048 (cached_user_frames) · :10260~10278 (fault_zoom_kind) · :10442~10653 (pending 마커 · complete · 사후 블록 · outer finally).

## 플래너가 코드로 확인한 것 (관측 — 승계 가능)

### Task A
- 지금 루프(frame_extractor.py:161~191)는 버리는 프레임(`(i - start_idx) % step != 0`)에서도 `last_resized = self._resize(rgb)` 를 한다(:174~177). 쓰임새는 루프 뒤 마지막 프레임 강제 포함(:187~191, 12-deferred §12-B) 하나뿐 [확인].
- imageio 2.37.4(backend/.venv) ffmpeg 플러그인 `_read_frame` 은 프레임마다 `np.frombuffer(s).copy()` 로 새 배열을 만든다 → 버리는 프레임의 원본 참조를 들고 있어도 다음 디코딩이 그 내용을 덮지 않는다 [확인 — inspect.getsource]. 옛 코드도 축소가 필요 없는 영상(긴 변 ≤ max_side)에서는 `_resize` 가 원본을 그대로 돌려줘 원본 참조를 frames 에 담고 있었다 — 같은 전제다. Pod 의 imageio 버전은 [미확인](requirements 하한 >=2.34).
- `FfmpegFrameExtractor` 는 운영에서 학생 추출(app.py:1830 싱글턴), fault_zoom 의 기준 영상 추출(app.py:4403), 공급자 등록 경로 등에서 쓰인다 → 바이트 동일이면 어디에도 동작 변화가 없다. fault_zoom 의 기준 영상(≈100MB) 추출도 같이 빨라질 수 있다 [미확인 — 기준 영상 코덱/해상도 미측정].
- 기존 테스트 관례 = `imageio.get_reader` 를 FakeReader 로 바꿔치기(test_frame_extractor_last_frame.py:47~62). 실제 mp4 를 tmp 에 쓰는 관례는 없다 [확인 grep].
- 주의 [확인]: test_frame_extractor_last_frame.py:30~44 는 `"PIL" not in sys.modules` 이면 가짜 PIL 을 sys.modules 에 넣는다. backend 전체 수집에서는 진짜 PIL 이 먼저 올라와 있다(플래너가 `pytest tests --collect-only` 뒤 `PIL.Image.fromarray` 타입 = function 확인). 두 파일만 그 순서로 돌리면 가짜가 들어갈 수 있다 → 새 테스트 파일을 명령줄 앞에 둔다.

### Task B — 의존 · 공유 자원 (오케스트레이터 질문 1~7)
1. **result dict 읽기/쓰기 키** [확인 — 코드]
   - coach_text 쓰기: in-memory `result["tips"]`, `result["coachStatus"]`(둘 다 이미 있는 키 — tips 는 assemble.build_result :804, coachStatus 는 app.py:10446) + `force_pattern_inference_dict["coachCommentHook"]` · `body_comparison_report_dict["coachCommentHook"]`(:5531~5534). `assemble.rebuild_tips_for_vision_fault` 안에서 `dict(result)` 로 최상위를 한 번 순회한다(assemble.py:876).
   - coach_audio 읽기: `result["deductionBreakdown"]["records"][].recordId/cueLine` 만(:5264~5275). **coach_text 결과를 쓰지 않는다** — cueLine 은 문구집 문장이고 coach_text 는 deductionBreakdown 을 건드리지 않는다. 기존 주석 :10503~10505 도 "coach_dual 무의존" 이라 적었다. → 오케스트레이터의 "coach_audio 는 coach_text 결과를 쓰는 것으로 보인다" 는 코드와 다르다.
   - fault_zoom 읽기: `visionVeto` · `joints` · `deductionBreakdown` · `motionAlignment`(:4828~4882, :4570~4620). result 에 쓰지 않는다(docstring "사후 mutation 금지" :4820, :5010).
   - spot_check 읽기: `deductionBreakdown.records` · `summaryPraise`(:7104~7111). result 에 쓰지 않는다.
   - → coach_text 의 쓰기 키 ∩ 곁가지의 읽기 키 = ∅. 곁가지는 result 최상위에 키를 더하지 않으므로 coach_text 의 `dict(result)` 순회 중 크기 변화가 생기지 않는다.
   - `timings_ms` 는 `result["timingsMs"]` 와 같은 객체(:10447)이고 `_stage` 가 새 키를 더한다(:162). 저장은 complete_analysis(:10458)에서 이미 끝났다 — 사후 키는 stage_timing 로그로만 나간다(update_* payload 에 timingsMs 없음). 그래도 두 스레드가 같은 dict 에 키를 더하지 않게 곁가지는 **자기 전용 dict** 에 재고, join 뒤 메인이 합친다.
2. **Firestore 쓰기** [확인 — firestore_admin.py] 전부 field-path `.update()`, 경로가 서로 겹치지 않는다: fault_zoom = `result.faultZoomComparisons` · `result.faultZoomStatus`(:1470 근처) / coach_audio = `result.coachAudio`(:1561 근처) / coach_text = `result.coachStatus` · `result.tips` · `result.forcePatternInference.coachCommentHook` · `result.bodyComparisonReport.coachCommentHook` · `geminiB`(:1712~1732) / spot_check = `result.spotCheck`(:2140 근처) / compare_render = `result.renderedCompare`(:1876). 공유 필드는 `updatedAt`(각 update 가 `int(time.time()*1000)`) 하나 — 마지막 쓰기가 남고 차이는 경쟁 간격(ms)뿐. 앱이 updatedAt 을 쓰는 곳은 zoom pending 180초 상한 재무장(result.tsx:1238~1251) — ms 차이는 영향 없음으로 본다 [미확인 — 앱 실측 안 함]. `_db()` 첫 초기화는 executor 생성 전 메인 스레드에서 끝나 있다(qmg SUMMARY 관측 7).
3. **GPU/RTMW** [확인 — grep] fault_zoom 경로(fault_zoom.py · card_gates.py · card_photo_audit.py · `_render_fault_zoom` · `_build_native_frame_provider`)에 rtmw/rtmlib/onnx/pose_engines import 또는 추정 호출 0 — 디코딩은 imageio-ffmpeg 와 ffmpeg subprocess(compare_render._native_frame :1089), 그림은 PIL. spot_check · coach_audio · coach_text 도 RTMW 0. RTMW 를 쓰는 것은 compare_render 의 `compare_align.build_align`(:5702, `_compare_render_capability` 가 rtmlib 확인) — **겹치지 않게 맨 뒤에 둔다.** 메모리 render-determinism-context-must-wrap-all-rtmw-paths 의 조건은 이 변경과 무관하다(compare_render 내부 무변경).
4. **프레임 · 임시 파일 수명** [확인 — 코드]
   - `cached_user_frames` 는 STUDENT_FRAME_CACHE=1(Pod, start_server.sh:11)일 때 `inputs.frames` 와 **같은 배열**(:9046~9048). fault_zoom 은 그것을, spot_check 는 `inputs.frames` 를 읽기만 한다 — fault_zoom.py · card_gates.py 에 프레임 제자리 쓰기 패턴 0 [확인 grep], spot_check 는 `Image.fromarray(arr[idx])`(:7057). 이 계획에서 둘은 **같은 곁가지 안에서 지금 순서대로** 돈다 → 동시 읽기도 생기지 않는다.
   - `_zoom_render` 람다는 `cached_user_frames` 등을 클로저로 늦게 읽는다(:4549~4574). 메인이 join 전에 그 이름을 다시 묶으면 곁가지가 다른 값을 본다 → `cached_user_frames = None` 은 곁가지 클로저 안(fault_zoom 직후, 지금 :10583 자리와 같은 순서)에서만 `nonlocal` 로 한다.
   - `local_video_path`(:9042) · `reference_local_video_path`(:9542/:9556/:9568 이후 재대입 0)는 outer finally(:10646, :10650)에서만 지운다. 새 pool 은 `_run_post_stages` 안 with 블록 종료에서 join 되므로 outer finally 보다 반드시 먼저 끝난다 → qmg 의 executor.shutdown(:10632) → session.close(:10637) → unlink 순서는 그대로다. coach B 는 `preuploadedHandle` 이 None 이면 `videoPath`(학생 로컬 파일)로 자체 업로드하므로(coach_writer_v2.py:481, :508) 학생 파일 수명이 coach_text 끝까지 필요하다 — 위 순서로 지켜진다.
5. **실패 격리** [확인 — 코드] 다섯 단계 모두 본체를 `try/except Exception` 으로 감싸 failed 마킹 후 재raise 0: fault_zoom :5122~5145 · coach_audio :5263~5299 · coach_text :5355~5551 · spot_check :7103~7159 · compare_render :5676~5955. 병렬 뒤에도 각 단계 함수는 그대로 쓰므로 같다. 추가로 곁가지 future 에서 예외가 새면(현재 계약상 나오지 않는 경로) 로그 한 줄 + 빈 목록으로 compare_render 를 계속한다.
6. **Gemini 동시 호출** [확인 — 코드] 사후 창에서 **학생 영상 File API 파일을 쓰는 호출은 coach B 하나뿐**이다(coach_writer_v2.py:491 `preuploadedHandle`). coach_hook 는 텍스트만(coach_hook_writer.py 에 upload/video/file 0). 곁가지의 Gemini 호출은 전부 인라인 JPEG — fault_zoom 앵커 확인 = urllib `inline_data image/jpeg`(card_gates.py:712~714, 키는 env GEMINI_API_KEY), spot_check = `Part.from_bytes(image/jpeg)`(spot_check.py:327, 자기 모듈 싱글턴 `_CLIENT`). coach B 는 호출마다 새 `genai.Client`(gemini/client.py:212) → 두 가지가 같은 클라이언트 객체를 나눠 쓰지 않는다. 사후 창 시점에 학생 파일에 대한 다른 호출(scene · recognizer · veto)은 이미 끝나 있다(qmg 배선 — scene join 은 coach context 직전, ref 업로드는 veto 직전). → qmg 후속 판독의 "같은 파일 동시 호출 = 둘 다 첫 호출 값" 경우에 해당하는 쌍이 없다. 같은 키로 2~3개 요청이 겹칠 때의 지연 · 429 는 [미확인] → 다음 Pod 실측에서 grep.
   - boto3: 곁가지가 새로 만드는 클라이언트는 `_get_polly_client()`(프로세스당 1회, :5181~5184)뿐. Pod 에서는 GEMINI_API_KEY 가 env 로 있어(start_server.sh:56) 메인 가지의 키 로더가 SSM 클라이언트를 만들지 않는다(gemini_moment_extractor.py:205, gemini_vision_scorer.py:779) [확인] → Pod 에서 두 스레드가 동시에 boto3 클라이언트를 만드는 경우 없음. env 키가 없는 환경(로컬 · Lambda 폴백)에서의 동시 생성 안전성은 [미확인] — 그 환경은 운영 경로가 아니고 `POST_STAGE_PARALLEL=0` 으로 끌 수 있다.
7. **stage_timing** 각 단계는 자기 stage 를 그대로 잰다(coach_dual · coach_hook = coach_text 안, coach_audio · fault_zoom · spot_check = 곁가지, compare_render = 메인). 병렬 구간 벽시계 `post_parallel` 을 새로 둔다(ON 일 때만). timingsMs 는 Record<string,number> 라 계약 형식 변경 없음.

### Task B — 병렬화 결정
- **겹친다:** 메인 = coach_text ∥ 곁가지 = coach_audio → fault_zoom → spot_check. 곁가지 안 순서는 지금과 같다 → OFF(직렬)는 "메인 가지 다음 곁가지" 를 이어 붙인 것과 정확히 같은 순서다.
- **안 겹친다:** compare_render — `coach_audio_items`(:10612) · `fault_zoom_items`(:10623) 를 받고 RTMW(GPU)를 쓴다. `_maybe_enqueue_corrected_pose`(:10490~10500)는 사후 블록 앞 그대로.
- spot_check 를 메인(coach_text 뒤)에 붙이는 안도 따져 봤다 — qmg 증거 로그의 런별 값(전1 coach_dual 86.7/audio 0.35/zoom 66.0/spot 8.3 · 후1 84.4/0.38/111.6/9.5 · 후2 85.6/0.36/81.1/7.5초 [확인 grep])으로 두 안의 절감 평균이 81.5초 vs 80.6초로 같았다. 곁가지에 두는 안을 고른 이유: 곁가지 안 순서가 지금과 같아 소스 순서 게이트(test_spot_check.py "fault_zoom 뒤")의 뜻이 실행에서도 유지되고, spot_check 의 genai 싱글턴이 한 스레드에서만 쓰인다.
- 기대 [추정 — 위 런별 값 산술, Gemini 동시 호출 영향 미측정]: 사후 합계 234.5 / 281.1 / 251.6초 → 159.9 / 196.7 / 166.0초(−74.6 / −84.4 / −85.6초).
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 프레임 추출 — 버리는 프레임 축소 생략 (바이트 동일)</name>
  <files>backend/shared/python/sunity_shared/analysis/frame_extractor.py, backend/tests/test_frame_extractor_resize_skip.py</files>
  <behavior>
    - 케이스(src_fps, target_fps, 프레임 수, start_s, end_s) → 기대 `_resize` 호출 수(새) / 옛 구현 호출 수(참고):
      a) 30, 9, 10, -, - → 4 / 10 (마지막 idx 9 가 남는 프레임 — 강제 추가 없음)
      b) 30, 9, 11, -, - → 5 / 11 (idx 10 강제 추가)
      c) 10, 3, 20, 0.3, 1.1 → 4 / 8 (idx 3..10, 남는 3·6·9 + 강제 10)
      d) 10, 3, 20, 0.3, 1.0 → 3 / 7 (idx 3..9, 마지막 9 가 남는 프레임)
      e) 10, 3, 8, 0.2, - → 3 / 6 (start 만, 남는 2·5 + 강제 7)
      f) 10, 3, 8, -, 5.0 → 4 / 8 (end 가 영상 밖)
      g) 9, 9, 5, -, - → 5 / 5 (step 1 — 버리는 프레임 없음)
      h) b 와 같되 RGBA 4채널 입력 → 5 / 11
    - 출력 바이트 동일: 위 a~h 각각, 긴 변이 max_side 보다 큰 프레임(실제 PIL 축소가 일어나는 크기)으로 새 extract 결과와 테스트 안 참조 함수(옛 루프 복제) 결과가 shape · dtype · `tobytes()` 모두 같다.
    - `_effective_fps_by_path` 기록은 그대로(기존 test_frame_extractor_effective_fps.py 무회귀).
  </behavior>
  <action>
**RED.** 새 파일 `backend/tests/test_frame_extractor_resize_skip.py` 를 만든다. 경로 주입은 test_frame_extractor_last_frame.py:23~27 관례. 단, 그 파일의 가짜 PIL/imageio stub 블록은 복제하지 않는다 — 이 파일은 맨 위에서 진짜 `PIL.Image` 를 import 한다(축소 바이트 비교가 목적). FakeReader(get_meta_data · __iter__ · close)는 이 파일 안에 따로 정의한다(다른 테스트 모듈 import 금지 — 그 모듈의 stub 이 따라 들어온다).
- 프레임 생성: 프레임마다 내용이 달라야 한다 — `np.random.default_rng(idx)` 로 채운 uint8 배열. 축소 케이스는 H48×W80(max_side 32 → 실제 PIL 축소), 호출 수 케이스는 H24×W16(max_side 640 → `_resize` 가 원본 반환, PIL 무관). RGBA 케이스는 채널 4.
- 참조 함수 `_extract_old(extractor, path, start_s, end_s)`: 지금 frame_extractor.py:148~195 루프를 **그대로** 복제하되 `extractor._resize` 를 부른다(사본에 "quick-261003-svg 이전 구현 — 바이트 비교 기준" 주석). meta fps · decimation_step 은 모듈 함수를 그대로 쓴다.
- 테스트 1 (바이트 동일, parametrize a~h): `imageio.get_reader` 를 `patch("sunity_shared.analysis.frame_extractor.imageio.get_reader", side_effect=lambda p: FakeReader(...))` 로 두 번 공급(새 구현 1회 · 참조 1회 — 리더는 매번 새로). `np.array_equal` 과 `tobytes()` 동일, shape · dtype 동일을 단언. 진짜 PIL 이 아닌 경우(`isinstance(Image.fromarray, MagicMock)` — 다른 테스트 모듈의 stub)는 이유를 적고 skip 한다(가드는 이 테스트에만).
- 테스트 2 (호출 수, parametrize a~h): 인스턴스에 `monkeypatch.setattr(extractor, "_resize", spy)` — spy 는 원래 바운드 메서드를 부르고 횟수를 센다. 새 구현 횟수 = 위 표의 앞 숫자, 참조 함수 횟수 = 뒤 숫자. 출력 프레임 수 = 앞 숫자.
- RED 확인: 지금 코드로 돌리면 테스트 2 는 실패(옛 횟수가 나옴), 테스트 1 은 통과(같은 코드)한다. 커밋 `test(quick-261003-svg): 프레임 추출 축소 생략 — 바이트 동일·호출 수 테스트 (RED)`.

**GREEN.** frame_extractor.py `extract` 루프(:161~191)만 고친다:
- `last_resized` 대신 `last_raw: np.ndarray | None = None` — 버리는 프레임이면 `rgb = np.asarray(frame)[:, :, :3]` 를 `last_raw` 에 담고 `continue`(축소 안 함). 남는 프레임이면 `frames.append(self._resize(rgb))`, `last_idx_appended = i`, `last_raw = None`(4K 원본 한 장을 일찍 놓는다).
- 루프 뒤: 조건 `last_raw is not None and last_idx_seen > last_idx_appended` 일 때만 `frames.append(self._resize(last_raw))`. 마지막으로 본 프레임이 버리는 프레임이면 `last_raw` 가 바로 그 프레임이므로 옛 `last_resized` 와 같은 입력 → 같은 바이트.
- `rgb = np.asarray(frame)[:, :, :3]` 는 두 분기 공통으로 한 번만 계산해도 된다(RGBA 대비 주석 유지).
- 한국어 why 주석: "quick-261003-svg — 버리는 프레임까지 축소하던 비용(로컬 25.7초 중 ≈10초, 4K HEVC 593프레임)을 없앤다. 마지막 강제 포함(12-deferred §12-B)은 원본 참조만 들고 있다가 필요할 때 한 장만 축소 — 출력 바이트 동일(test_frame_extractor_resize_skip.py). imageio ffmpeg 리더는 프레임마다 새 배열을 준다(`_read_frame` 의 `.copy()`) — 원본 참조를 들고 있어도 다음 디코딩이 덮지 않는다." ffmpeg `select` 필터 방식은 쓰지 않는다(로컬 15.3초로 이득 없고 픽셀이 달라 기각 — 오케스트레이터 실측). 주석에 그 기각 한 줄도 남긴다.
- `_effective_fps_by_path` 기록 · start_idx/end_idx 계산 · 빈 결과 ValueError · `np.stack(...).astype(np.uint8)` 은 손대지 않는다.
- 커밋 `perf(quick-261003-svg): 프레임 추출 — 버리는 프레임 축소 생략 (출력 바이트 동일)`.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_frame_extractor_resize_skip.py tests/test_frame_extractor_last_frame.py tests/test_frame_extractor_effective_fps.py tests/test_frame_extractor_probe_duration.py tests/test_fault_zoom_deferred.py tests/test_reference_real_fps.py -q -p no:cacheprovider</automated>
  </verify>
  <done>새 테스트 a~h 두 묶음 전부 통과(바이트 동일 묶음 skip 0 — 위 명령에서 새 파일이 맨 앞), 기존 frame_extractor · fault_zoom_deferred 테스트 무회귀. diff 는 frame_extractor.py 의 extract 루프와 새 테스트 파일뿐.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 사후 단계 오케스트레이터 — 토글 + _run_post_stages (단위)</name>
  <files>backend/functions/pipeline/app.py, backend/tests/test_post_stage_parallel.py</files>
  <behavior>
    - `_post_stage_parallel_enabled()`: env 미설정 → True, "1" → True, "0" · "false" · "FALSE" · "" → False (`_VISION_FALSY` 규칙, `_gemini_upload_prefetch_enabled` 와 같은 모양).
    - 직렬(parallel=False): 호출 순서 = coach_text_stage → side_stage → compare_render_stage, 전부 MainThread. coach_text_stage 와 side_stage 가 받은 dict 는 `timings_ms` 그 객체(`is`). compare_render_stage 는 side_stage 가 돌려준 두 리스트 객체를 그대로(`is`) 받는다. timings_ms 에 `post_parallel` 키 없음.
    - 병렬(parallel=True): side_stage 는 이름이 "post_side" 로 시작하는 스레드, coach_text_stage · compare_render_stage 는 MainThread. 겹침 증명 — coach 는 시작 때 Event A 를 set 하고 Event B 를 기다리며(timeout 5초), side 는 B 를 set 하고 A 를 기다린다 → 둘 다 True 로 기록돼야 한다(직렬이면 교착 대신 timeout 으로 False). compare 는 side 가 끝난 뒤(기록 순서) 1회, side 반환 객체 그대로(`is`). side 가 받은 dict 는 `timings_ms` 가 **아니고**(`is not`), side 가 그 dict 에 쓴 키는 끝나면 timings_ms 에 합쳐져 있다. timings_ms 에 `post_parallel` 정수 키.
    - 병렬 + side_stage 가 RuntimeError("boom-secret") → 호출측으로 예외가 새지 않는다. coach 1회, compare 1회 · 인자 ([], []). WARNING 로그에 "RuntimeError" 가 있고 "boom-secret" 은 없다(예외 본문 미기록).
    - 병렬 + coach_text_stage 가 RuntimeError → 예외는 전파된다(pytest.raises). 하지만 전파 시점에 side 는 이미 끝나 있다(side 가 coach 의 Event 를 기다린 뒤 0.05초 쉬고 "side_end" 기록 — raises 블록을 빠져나온 직후 "side_end" 존재 단언). compare 는 불리지 않는다. 이것이 outer finally 의 unlink 보다 곁가지가 먼저 끝난다는 보장이다.
  </behavior>
  <action>
**RED.** 새 파일 `backend/tests/test_post_stage_parallel.py` 1부(오케스트레이터 단위). 모듈 적재는 test_ref_prefetch_scene_join.py 의 `pipeline` fixture(:60~70)를 재등록해 쓴다 — `from tests.test_ref_prefetch_scene_join import pipeline, net_attempts  # noqa: F401 — 픽스처 재등록` (선례: tests/test_firestore_reference_writers.py:40). env `POST_STAGE_PARALLEL` 은 각 테스트에서 `monkeypatch.setenv/delenv` 로 명시한다. 스텁 stage 들은 스레드 이름 · 받은 인자 · 사건 순서를 락으로 보호된 리스트에 기록한다. 위 behavior 6묶음을 테스트로 쓴다. 파일 머리 docstring 에 목적(quick-261003-svg, 사후 단계 병렬 — 근거 수치는 qmg 증거 로그)과 1부/2부 구성을 적는다. RED = `AttributeError: module 'app' has no attribute '_run_post_stages'` 류. 커밋 `test(quick-261003-svg): 사후 단계 오케스트레이터 단위 테스트 (RED)`.

**GREEN.** app.py 에 모듈 함수 2개만 더한다(_process 는 Task 3).
- `_post_stage_parallel_enabled()` — `_gemini_upload_prefetch_enabled`(:505~519) 바로 뒤. `os.environ.get("POST_STAGE_PARALLEL", "1")` 을 strip · lower 해 `_VISION_FALSY` 에 없으면 True. 매 호출 env 를 읽는다(모듈 적재 시 고정 금지 — Pod env 재기동만으로 전후 교차 측정). docstring: 기본 ON, "0" 이면 직렬 그대로(롤백 · 같은 Pod 전후 대조 레버), quick-261003-svg.
- `_run_post_stages(*, coach_text_stage, side_stage, compare_render_stage, timings_ms, analysis_id, parallel)` — `_run_deferred_fault_zoom`(:5097) 바로 앞에 "사후 단계 오케스트레이터" 블록으로. 인자 이름에 `run_spot_check` 같은 문자열을 만들지 말 것 — test_spot_check.py:733 이 소스 안 `"run_spot_check("` 개수 = 1 을 센다.
  - parallel=False: `coach_text_stage(timings_ms)` → `audio, zoom = side_stage(timings_ms)` → `compare_render_stage(audio, zoom)`.
  - parallel=True: `side_timings = {}` · 기본값 `audio, zoom = [], []`. `with _stage(timings_ms, analysis_id, "post_parallel"):` 안에서 `with ThreadPoolExecutor(max_workers=1, thread_name_prefix="post_side") as pool:` → `future = pool.submit(side_stage, side_timings)` → 메인에서 `coach_text_stage(timings_ms)` → `try: audio, zoom = future.result()` / `except Exception as exc:` 이면 `log.warning("사후 곁가지 실패 — compare_render 는 빈 목록으로 계속 analysis_id=%s err=%s", analysis_id, type(exc).__name__)` 후 빈 목록. with 를 빠져나온 뒤 `timings_ms.update(side_timings)` → `compare_render_stage(audio, zoom)`.
  - pool 은 함수 지역(분석-로컬) — 모듈 전역 금지(Phase 27 D-03 규율). 스레드 접두는 "gemini" 로 시작하면 안 된다(qmg 하네스가 "gemini" 접두로 prefetch 스레드를 가른다).
  - BaseException 은 잡지 않는다. 메인 가지 예외는 with 종료(shutdown wait=True)가 곁가지를 기다린 뒤 전파된다 — 이 성질을 docstring 에 적는다(outer finally 의 unlink 보다 곁가지가 먼저 끝나는 근거).
  - docstring/주석(한국어 why): 기대 근거(qmg 증거 로그 coach_dual 58~87초 · fault_zoom 66~112초 · spot_check 7.5~9.5초 · compare_render 73~77초 [확인]), 왜 이렇게 나눴나(coach_audio 는 문구집 cueLine 만 읽어 coach_text 무의존, 곁가지는 result 에 쓰지 않음, Firestore 경로 서로 다름, 곁가지 Gemini 호출은 인라인 JPEG 뿐), 왜 compare_render 는 뒤인가(두 결과를 받고 RTMW GPU 사용), 곁가지 타이밍을 전용 dict 에 재는 이유. 근거 표기 `quick-261003-svg`.
- 커밋 `feat(quick-261003-svg): 사후 단계 오케스트레이터 + POST_STAGE_PARALLEL 토글 (GREEN)`.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_post_stage_parallel.py tests/test_analysis_local_state_concurrency.py tests/phase32/test_spot_check.py -q -p no:cacheprovider</automated>
  </verify>
  <done>1부 테스트 전부 통과(겹침 증명 Event 두 개 True, 곁가지 예외 비전파, 메인 예외는 곁가지 종료 뒤 전파). test_spot_check.py 의 `run_spot_check(` 개수 게이트 그대로 통과. _process 는 아직 무변경.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: _process 사후 블록 배선 + 통합 테스트 + 게이트 앵커 + 계약</name>
  <files>backend/functions/pipeline/app.py, backend/tests/test_post_stage_parallel.py, backend/tests/phase32/test_spot_check.py, docs/contract.md</files>
  <behavior>
    - qmg 하네스(mode1, prefetch ON)로 `_process` 를 POST_STAGE_PARALLEL "0" 과 "1" 로 각각 돌린다. 다섯 `_run_deferred_*` 는 각 모드에서 정확히 1회. kwargs 키 집합이 두 모드에서 같고, 문자열 인자(uid · analysis_id · bucket · mode · local_video_path · reference_local_video_path)의 값도 같다. 각 단계가 받은 `result` 는 그 런의 complete_analysis 세 번째 인자와 같은 객체(`is`).
    - compare_render 가 받은 `coach_audio_items` · `fault_zoom_items` 는 coach_audio · fault_zoom 이 돌려준 객체 그대로(`is`) — 두 모드 모두.
    - 스레드: "0" = 다섯 단계 전부 MainThread. "1" = coach_audio · fault_zoom · spot_check 은 "post_side" 접두, coach_text · compare_render 은 MainThread. "1" 에서 겹침 증명 — coach_text 기록 stub 이 "coach_audio 시작" Event 를 기다려(timeout 5초) True.
    - 정리 순서(각 런 구간 안에서): 모든 단계의 "end" 사건이 ("close",) 보다 앞, ("unlink", 학생 경로) 보다 앞. 런이 끝나면 학생 파일 · 기준 temp 없음. 소켓 시도 0(`net_attempts == []`).
    - 결과 동일: 두 런의 `set(result)` 같음. `set(result["timingsMs"])` 은 "1" 쪽이 "0" 쪽 ∪ {"post_parallel"}. Firestore 부분 갱신 기록(함수 이름, status)의 다중집합이 두 런에서 같다.
    - 실패 격리("1"): `_build_fault_zoom_comparisons` 가 RuntimeError → update_analysis_fault_zoom 기록이 status failed, coach_text · spot_check · compare_render 각 1회, compare_render 의 fault_zoom_items == [], `_process` 정상 종료, complete 1회.
    - mode3 첫 분석("1"): fault_zoom 은 안 불리고(fault_zoom_kind None), coach_audio · spot_check 는 post_side 스레드, compare_render 1회.
  </behavior>
  <action>
**RED.** test_post_stage_parallel.py 에 2부(_process 통합)를 더한다. `from tests.test_ref_prefetch_scene_join import _install, _STUDENT_KEY` 로 qmg 하네스를 그대로 쓴다(선례 tests/test_analysis_provenance.py:454). `_install(...)` 뒤에:
- `_run_deferred_coach_text` 는 기록 stub 으로 덮는다(하네스가 이미 no-op 로 둔 이유 = Gemini coach B 의 SSM 키 조회, qmg SUMMARY 편차 2). stub 은 스레드 이름 · kwargs 를 기록하고, 병렬 런에서만 "coach_audio 시작" Event 를 기다려 결과를 기록한다(직렬 런에서 기다리면 5초 낭비).
- coach_audio · fault_zoom · spot_check · compare_render 는 원본을 감싼 기록 wrapper(시작 · 끝 사건을 `h.rec.add` 로, 스레드 이름 · kwargs · 반환값 보관 후 원본 호출).
- `firestore_admin.update_analysis_coach_audio` · `update_analysis_fault_zoom` · `update_analysis_spot_check` · `update_analysis_rendered_compare` 를 (이름, status) 기록 stub 으로.
- 두 모드를 한 테스트에서 순서대로 돌릴 때는 런마다 `h.rec.snapshot()` 길이로 구간을 자르고 complete 의 `call_args_list[n]` 으로 그 런의 result 를 잡는다. 하네스 재사용이 깨지면(두 번째 런에서 학생 파일 · 세션 기록이 꼬이면) 런마다 `tmp_path / "run0"`, `"run1"` 으로 `_install` 을 따로 깔아도 된다 — 어느 쪽을 썼는지 SUMMARY 에 적는다.
- RED = 지금 `_process` 는 전부 MainThread 라 "1" 의 스레드 · 겹침 · post_parallel 단언이 실패. 커밋 `test(quick-261003-svg): _process 사후 병렬 통합 테스트 (RED)`.

**GREEN — app.py `_process` 사후 블록(:10502~:10624)만 바꾼다.**
- `_maybe_enqueue_corrected_pose`(:10490~10500) 뒤에 클로저 3개를 정의하고 `_run_post_stages(coach_text_stage=_post_coach_text, side_stage=_post_side, compare_render_stage=_post_compare_render, timings_ms=timings_ms, analysis_id=analysis_id, parallel=_post_stage_parallel_enabled())` 를 한 번 부른다. 클로저 정의 순서 = 코치 → 곁가지 → compare(소스 순서 = 직렬 실행 순서).
- `_post_coach_text(stage_timings)`: 지금 `_run_deferred_coach_text(...)` 호출(:10508~10519)을 그대로 옮기고 `timings_ms=stage_timings` 만 바꾼다.
- `_post_side(stage_timings)`: 첫 줄 `nonlocal cached_user_frames`. 지금 coach_audio 블록(:10527~10532) → fault_zoom 블록(:10545~10583, `if fault_zoom_kind is not None:` · 두 `_zoom_render` 람다 · `cached_user_frames = None` 위치 그대로) → spot_check 블록(:10592~10600)을 같은 순서로 옮기고 각 `_stage(timings_ms, ...)` 를 `_stage(stage_timings, ...)` 로 바꾼다. 반환 `(coach_audio_items, fault_zoom_items)`. 지역 이름은 지금 이름(`coach_audio_items`, `fault_zoom_items`)을 쓴다.
- `_post_compare_render(coach_audio_items, fault_zoom_items)`: 지금 compare_render 블록(:10608~10624)을 그대로 — `_stage(timings_ms, analysis_id, "compare_render")`.
- 기존 주석은 코드와 함께 옮기고 지우지 않는다(승인 사후 순서 · 오디오 먼저 도착 · spot_check 사후 · compare_render 마지막 · fault_zoom temp 유효 근거). 블록 머리 주석을 고친다: "승인 사후 순서" 는 POST_STAGE_PARALLEL=0 의 순서이고, 기본 ON 에서는 coach_text(메인) ∥ coach_audio → fault_zoom → spot_check(곁가지), compare_render 는 둘 뒤 — 근거 `quick-261003-svg`, 의존 확인 요약(위 context 1~6을 3~4줄로).
- 메인은 join 전에 `cached_user_frames` · `local_video_path` · `reference_local_video_path` · `result` 를 다시 묶지 않는다(람다가 늦게 읽는다 — 주석 한 줄).
- outer finally(:10625~10653)는 손대지 않는다.

**게이트 앵커 갱신 — tests/phase32/test_spot_check.py:713~733.** 들여쓰기에 묶인 `source.index(...)` 세 개를 공백 무관 정규식 `re.search(...).start()` 로 바꾼다: `r"_run_deferred_fault_zoom\(\s*render="`, `r'_stage\(\w+, analysis_id, "spot_check"\)'`, `r"_run_deferred_spot_check\(\s*result="`. `complete_pos` · 세 단언 · `source.count("run_spot_check(") == 1` 은 그대로. docstring 에 "소스 순서 = POST_STAGE_PARALLEL=0 의 실행 순서. 병렬 실행 순서는 test_post_stage_parallel.py 가 잠근다(quick-261003-svg)" 한 줄 추가. 단언을 약하게 만들지 않는다. tests/quick_260901_wbo/test_coach_text_deferred.py:187~207 은 `inspect.getsource(_process)` 안에 `_run_deferred_coach_text(` 가 complete 뒤에 있는지 보므로 클로저가 `_process` 안에 있으면 무수정으로 통과해야 한다 — 실패하면 고치지 말고 원인을 SUMMARY 에 적고 멈춘다.

**contract.md timingsMs 절(:756~768).** qmg 문단 뒤에 한 문단: `post_parallel`(quick-261003-svg) = 사후 병렬 구간(코칭 문장 ∥ 코칭 오디오 → 확대 사진 → 스팟체크) 벽시계, `POST_STAGE_PARALLEL` 이 켜졌을 때만(기본 ON, "0" 이면 직렬 · 키 없음). complete 뒤 단계라 저장 doc 의 timingsMs 에는 없고 stage_timing 로그로만 나온다(coach_dual · fault_zoom 등 다른 사후 키와 같다). 병렬 ON 이면 사후 키들의 합은 사후 대기 시간이 아니다 — 겹친 구간은 post_parallel 이 잰다.

**전체 회귀.** backend 전체 pytest. 기준선 = `pytest tests --collect-only` 5963(5943 passed + 20 skipped, qmg 마감 수치) + 이번 새 테스트 수. 실패가 나면 이번 변경과 무관한지 변경 전 커밋(a21edc48)에서 같은 이름으로 재현해 판정한다 — qmg SUMMARY §4 의 "pipeline 묶음 순서 의존 6건" 은 이미 알려진 것.

커밋 `feat(quick-261003-svg): _process 사후 단계 병렬 배선 + 게이트 앵커 + contract (GREEN)`.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_post_stage_parallel.py tests/test_ref_prefetch_scene_join.py tests/test_stage_timing.py tests/phase32/test_spot_check.py tests/phase32/test_coach_audio.py tests/quick_260901_wbo/test_coach_text_deferred.py tests/phase35/test_compare_render_stage.py tests/test_fault_zoom_deferred.py tests/test_analysis_local_state_concurrency.py tests/test_pair_time_deviation.py tests/pipeline/test_pipeline_phase9.py -q -p no:cacheprovider && cd /Users/kimtaesung/Dev/SunityMotion && grep -c "post_parallel" docs/contract.md && cd backend && .venv/bin/python -m pytest tests -q -p no:cacheprovider 2>&1 | tail -3</automated>
  </verify>
  <done>2부 통합 테스트 전부 통과(두 모드 각 단계 1회 · 인자 동일 · 스레드 · 겹침 · 정리 순서 · 결과 키 · Firestore 기록 다중집합 · 실패 격리 · mode3). qmg 통합 [A]~[H] 무회귀(이제 기본 ON 으로 돈다). test_spot_check 앵커만 바뀌고 단언 수 동일. contract.md 에 post_parallel. backend 전체가 기준선 + 새 테스트 수만큼 통과(또는 무관 판정된 기존 실패만, 이름과 함께 SUMMARY).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Pod `_process` 사후 단계 → Firestore analyses doc | 같은 doc 에 두 스레드가 부분 갱신 |
| Pod `_process` → Gemini API(같은 키) | 사후 창에서 요청 2~3개 동시 |
| 영상 → FfmpegFrameExtractor → 채점 입력 | 프레임 배열이 점수의 원료 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-svg-01 | Tampering(무결성) | frame_extractor.extract 출력 | mitigate | 옛 루프 복제 참조 함수 대비 `tobytes()` 동일 테스트 a~h(Task 1). 채점 · veto 코드 diff 0 |
| T-svg-02 | Tampering(무결성) | Firestore 부분 갱신 동시 쓰기 | mitigate | field-path 가 단계별로 서로 다름(context 2 [확인]). 통합 테스트가 두 모드의 (함수, status) 다중집합 동일을 단언 |
| T-svg-03 | Tampering(경쟁) | in-memory result / timings_ms 공유 | mitigate | 곁가지는 result 에 쓰지 않음 [확인], 곁가지 타이밍은 전용 dict → join 뒤 메인이 합침. `cached_user_frames = None` 은 곁가지 안에서만(nonlocal) |
| T-svg-04 | Denial of Service | 임시 파일 · Gemini 핸들 수명 | mitigate | 새 pool 은 `_run_post_stages` 의 with 종료에서 join → outer finally(executor.shutdown → session.close → unlink) 보다 먼저. 단위(메인 예외 시 곁가지 종료 뒤 전파) + 통합(end < close < unlink) 테스트 |
| T-svg-05 | Denial of Service | GPU(RTMW) 동시 사용 | mitigate | RTMW 쓰는 compare_render 를 join 뒤 단독 실행. 곁가지에 RTMW 0 [확인 grep] |
| T-svg-06 | Denial of Service | Gemini 동시 요청(429 · 지연) | accept | 같은 학생 파일 동시 호출 쌍 없음 [확인]. 지연 · 429 는 [미확인] → 다음 Pod 실측에서 grep, 문제면 `POST_STAGE_PARALLEL=0` 으로 즉시 직렬 복귀(재배포 없이 env) |
| T-svg-07 | Information Disclosure | 새 경고 로그 | mitigate | analysis_id 와 예외 타입 이름만 — 예외 본문 · URL · 키 미기록(단위 테스트가 본문 부재 단언) |
| T-svg-08 | Denial of Service | 곁가지 예기치 못한 예외 | mitigate | join 에서 Exception 을 잡아 빈 목록으로 compare_render 계속(각 `_run_deferred_*` 는 원래 재raise 0) |

패키지 설치 없음 — 공급망 항목 해당 없음.
</threat_model>

<verification>
- Task 1~3 의 automated 명령 전부 통과.
- `git diff --stat a21edc48..HEAD` 의 코드 파일이 frontmatter files_modified 6개뿐(+ SUMMARY). template.yaml · runpod_inference · start_server.sh · app/ · 채점 모듈(dimensions · deduction_engine · vision_veto · assemble) 무변경.
- AWS · Pod · Lambda · sam · s3 무접촉(배포 안 함).
</verification>

<success_criteria>
- 프레임 추출 출력 바이트 동일 + 버리는 프레임 축소 0 이 테스트로 잠김.
- 사후 단계가 기본 ON 에서 두 가지로 겹치고, "0" 이면 지금 직렬과 같음이 테스트로 잠김(인자 · 횟수 · 결과 키 · Firestore 기록 · 정리 순서 · 실패 격리).
- backend 전체 pytest 기준선 + 새 테스트 수 통과.
- SUMMARY 가 관측 / 추정을 다른 절로 나누고, Task B 의존 확인 표(위 context 1~7, [확인]/[미확인] 그대로)와 아래 Pod 측정 계획을 담는다.

Pod 측정 계획(SUMMARY 에 계획만 적는다 — 실행은 다음 세션, 메모리 analysis-time-reference-gemini-reupload-42s · pod-link-can-collapse-silently):
1. 같은 날 · 같은 RTX 4090 Pod · 38-14 쌍(학생 `uploads/zVJP…/2a7495bb….mp4` · 기준 `d8e849f7…` v1), `backend/scripts/e2e_app_path.py` 경로.
2. 코드는 이 quick 판 하나로 두고 env 만 바꿔 서버 재시작 — `POST_STAGE_PARALLEL` 0 → 1 → 1 → 0. 앞 분석의 compare_render stage 로그가 나온 뒤 다음을 보낸다(겹침 0).
3. Task A 는 토글이 없으므로 `frame_extract` 를 qmg 증거 로그(22.5 / 23.5 / 25.2 / 26.1초, 같은 쌍 · 같은 GPU 종류)와 비교하고, fault_zoom 안 기준 영상 추출 몫은 `fault_zoom` 값 변화로 본다 — 필요하면 직전 커밋으로 서버만 바꿔 1회 교차.
4. 잴 것: 런별 `frame_extract` · `coach_dual` · `coach_audio` · `fault_zoom` · `spot_check` · `post_parallel` · `compare_render`, 그리고 `분석 완료` 로그 → `stage=compare_render` 로그 사이 벽시계(화면이 다 채워지는 시간).
5. 불변 확인: 런마다 `overallScore` · `deductionBreakdown.final` · `dimensionScores` 동일, `coachStatus` · `faultZoomStatus` · `coachAudio.status` · `spotCheck.status` · `renderedCompare.status` 가 OFF/ON 에서 같음. Pod 로그 `grep -E "RESOURCE_EXHAUSTED|429|Traceback|사후 곁가지 실패"` 0.
6. 기대 [추정]: frame_extract −≈10초(로컬 비율), 사후 벽시계 −75~86초(context 의 런별 산술). Gemini 동시 요청 지연이 커지면 절감이 줄 수 있다 [미확인].
</success_criteria>

<output>
Create `.planning/quick/261003-svg-frame-extract-resize-skip-and-post-stage/261003-svg-SUMMARY.md` when done
</output>
