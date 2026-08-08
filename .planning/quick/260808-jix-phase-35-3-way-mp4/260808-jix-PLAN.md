---
phase: quick-260808-jix
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/cue_text.py
  - backend/shared/python/sunity_shared/analysis/compare_align.py
  - backend/shared/python/sunity_shared/analysis/compare_render.py
  - backend/shared/python/sunity_shared/analysis/compare_verify.py
  - backend/shared/python/sunity_shared/s3keys.py
  - backend/shared/python/sunity_shared/models.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/functions/pipeline/app.py
  - backend/functions/playback-url/app.py
  - backend/scripts/render_compare_prototype.py
  - backend/scripts/p35_extract_align.py
  - backend/scripts/verify_render_prototype.py
  - backend/scripts/verify_compare_stage_local.py
  - backend/tests/phase35/__init__.py
  - backend/tests/phase35/test_rendered_compare_contract.py
  - backend/tests/phase35/test_compare_render_stage.py
  - backend/tests/phase35/test_compare_align_recompute.py
  - backend/tests/phase35/test_playback_url_rendered_compare.py
  - docs/contract.md
  - app/src/types/analysis.ts
  - app/src/lib/api.ts
  - app/src/app/analysis/result.tsx
  - app/src/components/RenderedComparePlayer.tsx
autonomous: true
requirements: [QUICK-260808-JIX]

must_haves:
  truths:
    - "Mode1 분석이 complete(status='done') 된 뒤, Pod 사후 스테이지가 15fps 재추출+자세거리 DTW 정렬(align)을 GPU 로 새로 만들고 그 align 으로 합성 비교 mp4 를 렌더한다 — doc 폴백(anchors/faultZoom 짝) 렌더는 운영 경로에 존재하지 않는다 (belle 반려 이력)."
    - "리그(compare_verify) 전 항목 PASS 인 mp4 만 S3 results/{uid}/{analysisId}/compare_v{N}.mp4 에 올라가고 doc result.renderedCompare={status:'done',key} 가 부착된다. 리그 FAIL·스테이지 예외 = status:'failed'(key '') 마킹, 분석 자체는 무훼손(재raise 0)."
    - "renderedCompare done doc 의 결과 화면 동작비교 = 단일 mp4 재생. 그 doc 에서 앱 큐 오디오·자막(cueWindows)·재생바 틱 발화 경로는 구조적으로 OFF (VideoCompare 자체 미렌더) — mp4 에 음성·자막이 구워져 있으므로 이중 발화 0."
    - "renderedCompare 부재(legacy)·failed doc = 기존 듀얼 플레이어+라이브 동기 경로가 현행 그대로 (폴백 강등 — 렌더 분기 밖 코드 diff 0)."
    - "프로토 CLI 3종(render_compare_prototype / p35_extract_align / verify_render_prototype)은 라이브러리화 후에도 같은 입력에 byte-동일 산출 (elbow·kipup·pdshapefault 3편 baseline cmp PASS)."
    - "채점 무접촉 — overallScore·deductionBreakdown 산출 모듈 diff 0 + pytest FAILED/ERROR node-ID baseline diff IDENTICAL."
    - "실기기·실분석 E2E 는 이번 범위 밖(Pod 없음) — SUMMARY 에 미검증 표 + 'Pod 재가동 시 검증 절차' 1절이 있다."
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/compare_render.py"
      provides: "렌더러 라이브러리 (build_timeline/render — 프로토 스크립트 본체 이동)"
      min_lines: 900
    - path: "backend/shared/python/sunity_shared/analysis/compare_align.py"
      provides: "15fps 재추출+DTW 정렬+짝 재선정 라이브러리 (build_align, GPU 부 lazy import)"
      contains: "def build_align"
    - path: "backend/shared/python/sunity_shared/analysis/compare_verify.py"
      provides: "기계 판정 리그 라이브러리 (verify — 스테이지 게이트 재사용)"
      contains: "def verify"
    - path: "backend/shared/python/sunity_shared/analysis/cue_text.py"
      provides: "자막=음성 단일 문장 소스 (coach_audio_speech_text — pipeline·렌더러 공용)"
      contains: "coach_audio_speech_text"
    - path: "backend/functions/pipeline/app.py"
      provides: "_run_deferred_compare_render 사후 스테이지 (spot_check 뒤, graceful)"
      contains: "_run_deferred_compare_render"
    - path: "backend/shared/python/sunity_shared/s3keys.py"
      provides: "build_rendered_compare_key 단일 출처 (compare_v{N}.mp4)"
      contains: "build_rendered_compare_key"
    - path: "backend/functions/playback-url/app.py"
      provides: "asset 'renderedCompare' 재서명 (서버 canonical 구성 + exact 비교)"
      contains: "renderedCompare"
    - path: "app/src/components/RenderedComparePlayer.tsx"
      provides: "단일 mp4 플레이어 (expo-video, playback-url asset URL)"
    - path: "app/src/app/analysis/result.tsx"
      provides: "동작비교 분기: renderedCompare done = 단일 플레이어 / 그 외 = 기존 VideoCompare"
      contains: "RenderedComparePlayer"
    - path: "docs/contract.md"
      provides: "§12.9 renderedCompare + playback-url asset 확장 + changelog"
      contains: "renderedCompare"
  key_links:
    - from: "backend/functions/pipeline/app.py::_run_deferred_compare_render"
      to: "sunity_shared/analysis/{compare_align,compare_render,compare_verify}"
      via: "사후 스테이지 lazy import (fault_zoom/coach_audio 뼈대 복제)"
      pattern: "compare_(align|render|verify)"
    - from: "backend/functions/playback-url/app.py"
      to: "s3keys.build_rendered_compare_key"
      via: "서버 canonical 구성 + doc 저장 key exact 비교 (M2-01/H-02, V-0 존재확인 규율)"
      pattern: "build_rendered_compare_key"
    - from: "app/src/app/analysis/result.tsx"
      to: "POST /playback-url { asset: 'renderedCompare' }"
      via: "requestAssetPlaybackUrl union 확장"
      pattern: "renderedCompare"
    - from: "sunity_shared/analysis/compare_render.py"
      to: "sunity_shared/analysis/cue_text.py"
      via: "freeze 자막 문장 = coach_audio 합성 문장 단일 소스 (path-exec import 제거)"
      pattern: "cue_text"
---

<objective>
Phase 35 앱 통합 — 합성 비교 영상을 프로토(수동 스크립트)에서 운영(파이프라인 자동)으로 승격.

belle 승인 설계 4점 (2026-08-08):
1. 렌더 위치 = Pod 분석 **사후 스테이지** (fault_zoom·coach_audio deferred 패턴 복제 — complete 후 백그라운드, 실패 graceful, doc 필드 부재 = 앱 폴백)
2. 계약 = doc `result.renderedCompare` 필드, **3-way lockstep** (docs/contract.md + models.py/firestore_admin + analysis.ts 동시 수정)
3. 앱 = 결과 화면 동작비교를 **단일 mp4 재생**으로, 기존 듀얼 플레이어+라이브 동기 로직은 "렌더 없는 doc" 전용 폴백 강등. **이중 발화 방지**: renderedCompare 있는 doc 에선 앱 큐 오디오·자막·틱 발화 경로 OFF
4. 리그 게이트 = verify 리그 **ALL PASS 아니면 doc 에 안 붙임** (돌파 ② 경험 계약서 첫 조항)

Purpose: 동기·스냅·재개·드리프트 계열 버그를 재생기 차원에서 원리적으로 소멸시키는 돌파 ①의 완성 단계 — 프로토 5편이 belle 판정을 통과한 표시 문법을 실분석 doc 에 자동 도착시킨다.
Output: 라이브러리 4모듈 + deferred 스테이지 + 계약 3-way + 앱 단일 플레이어 + 게이트 증거 + SUMMARY(미검증 표 + Pod 재가동 검증 절차).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/phases/35-server-rendered-comparison-video/data/README.md  (렌더 입력 데이터 정본 — S3 키 표·렌더 커맨드 템플릿·mp3 회수 규칙)
@backend/scripts/render_compare_prototype.py  (렌더러 본체 — build_timeline:765, render:948, main:1205, _load_speech_text:70)
@backend/scripts/p35_extract_align.py  (재추출+정렬 — process:183, 순수부 pose_feature/dtw_path/smooth_curve:108-152, JOBS:35)
@backend/scripts/verify_render_prototype.py  (리그 — verify:64)
@backend/functions/pipeline/app.py  (deferred 선례: _run_deferred_fault_zoom:3719 / _run_deferred_coach_audio:3889 / _run_deferred_spot_check:4049, 호출부:6754-6827, cue 문장:3806-3847, outer finally:6828)
@backend/shared/python/sunity_shared/s3keys.py  (build_coach_audio_key:46 — 단일 출처 선례)
@backend/shared/python/sunity_shared/models.py  (coachAudio 계약 블록:327-345, spotCheck:347-372 — 신규 블록 서식 미러)
@backend/shared/python/sunity_shared/firestore_admin.py  (update_analysis_coach_audio:1494 + _validate_coach_audio — 신규 update/validator 뼈대)
@backend/functions/playback-url/app.py  (_handle_asset:83, _handle_coach_audio:133, asset 디스패치:229-261)
@docs/contract.md  (§12.7 coachAudio:1973 / §12.8 spotCheck — §12.9 삽입 위치, changelog:문서 말미)
@app/src/types/analysis.ts  (CoachAudio:648-668, AnalysisResult coachAudio?:935 — 신규 필드 삽입 위치)
@app/src/lib/api.ts  (requestPlaybackUrl:99, requestAssetPlaybackUrl:154-167 — asset union 확장 지점)
@app/src/app/analysis/result.tsx  (동작비교 섹션:2500-2762, coachAudioAnalysisId 게이트:2049-2055, fresh URL 훅 3종:915-1023)
@backend/tests/phase32/test_coach_audio.py  (사후 스테이지·계약 테스트 선례 — 신규 테스트 미러)
</context>

<tasks>

<task type="auto">
  <name>Task 1: 백엔드 — 라이브러리화(byte-보존) + deferred 렌더 스테이지 + 계약 py측 + 로컬 스테이지 검증</name>
  <files>backend/shared/python/sunity_shared/analysis/cue_text.py, backend/shared/python/sunity_shared/analysis/compare_align.py, backend/shared/python/sunity_shared/analysis/compare_render.py, backend/shared/python/sunity_shared/analysis/compare_verify.py, backend/shared/python/sunity_shared/s3keys.py, backend/shared/python/sunity_shared/models.py, backend/shared/python/sunity_shared/firestore_admin.py, backend/functions/pipeline/app.py, backend/functions/playback-url/app.py, backend/scripts/render_compare_prototype.py, backend/scripts/p35_extract_align.py, backend/scripts/verify_render_prototype.py, backend/scripts/verify_compare_stage_local.py, docs/contract.md, backend/tests/phase35/*</files>
  <action>
**0) baseline 렌더 캡처 (리팩터 전 — 이 단계 실패 시 코드 수정 진입 금지, epy 2패스 선례):**
data README(§렌더 커맨드 템플릿)대로 scratchpad 에 입력 준비 — user/ref mp4 = README S3 키 표에서 다운로드, mp3 = 각 doc.json `result.coachAudio.items[].key` 회수(파일명은 recordId 콜론 앞 `r{NN}.mp3`), AWS 자격증명은 로컬 기본(필요 시 AWS_PROFILE=sunity-motion). 대상 3편 = **elbow**(--text-override-json .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/elbow_text_overrides.json — 폴 문법 경로), **kipup**(--moments-json — moments 주입+피크 경로), **pdshapefault**(--pair-override-json .planning/quick/260808-epy-.../pdshape_pair_overrides.json — 명시 짝 경로). 각각 out_base.mp4 + report_base.json 저장. 리그 3편 ALL PASS 재확인(v7 과 동일해야 정상).

**1) cue_text 단일 소스 분리:** pipeline app.py 의 `_GOAL_CLAUSE_PREFIX`/`_GOAL_CLAUSE_SEPARATOR`/`_cue_action_line`/`_coach_audio_speech_text`(3806-3847)를 신규 `sunity_shared/analysis/cue_text.py` 로 **순수 이동**(공개명 `GOAL_CLAUSE_PREFIX`/`goal_clause_action_line`/`coach_audio_speech_text`, 로직 문자 단위 동일 — app deductionSheet.ts lockstep 주석 승계). pipeline app.py 는 import 후 기존 이름으로 alias(`_coach_audio_speech_text = cue_text.coach_audio_speech_text` 등 — 기존 테스트·참조 무파손). 렌더러의 path-exec `_load_speech_text()`(:70-76)는 cue_text import 로 대체 — 파이프라인 내부 호출 시 app.py 이중 exec 하던 구조 제거.

**2) 라이브러리화 (본체 이동 + 스크립트 = 얇은 CLI 래퍼, CLI 인자·stdout·산출 byte-보존):**
- `compare_render.py` ← render_compare_prototype.py 본체 전부(상수·pole 문법·build_timeline·render·시각화 헬퍼). imageio_ffmpeg/PIL 은 현행대로 모듈 레벨 유지(파이프라인 Lambda 에도 기존 존재 — frame_extractor/spot_check 선례), 호출측(pipeline)이 모듈 자체를 lazy import. FONT_PATH 는 모듈 위치 기준 리포 상대 재계산(shared/python/sunity_shared/analysis → repo root/app/assets/...) + env `RENDER_FONT_PATH` override — 폰트 부재 시 render 가 raise(스테이지 failed 로 수렴, 조용한 대체 금지). `render()` 는 doc 을 **dict 로도** 받게 오버로드(Path 면 json.load — CLI 경로 불변). moments/text_overrides/pair_overrides 파라미터는 **존치하되 운영 스테이지는 전부 None**(프로토 전용 입력 — background 승인).
- `compare_align.py` ← p35_extract_align.py 의 extract/build_model/infer_video/pose_feature/dtw_path/smooth_curve/짝 선정 블록(process:210-243)을 함수화. 최상위 `build_align(user_video, ref_video, records, workdir, *, model=None, infer_fn=None) -> dict`(align.json 스키마 그대로: fps/userSize/refSize/curveRefSec/pairs/userKp/refKp/userScore/refScore/joints17). rtmlib/cv2 는 **함수 내부 lazy import 유지**(Lambda 레이어 import 안전). `infer_fn` 주입 파라미터 = 로컬/테스트에서 GPU 없이 대체 가능 설계. atVideoSec 없는 record 는 스킵(fail-closed — p35 현행). verify jpg(draw_skeleton/hstack) 도 라이브러리로 이동(스테이지는 미출력, 스크립트 래퍼만 출력).
- `compare_verify.py` ← verify_render_prototype.py 의 verify()/frame_diff/mean_db/duration_s 이동.
- 스크립트 3종은 argparse main + 라이브러리 호출만 남긴다(기존 sys.path 주입 유지).

**3) 계약 py측 (coachAudio 블록 미러, 3-way 중 2면):**
- models.py: `RENDERED_COMPARE_KEYS = ("status", "key")` / `RENDERED_COMPARE_STATUS_DONE|FAILED` / `RENDERED_COMPARE_STATUSES` / `PLAYBACK_ASSET_RENDERED_COMPARE = "renderedCompare"` — coachAudio 블록(327-345) 형식·주석 관례(3-way lockstep 명기, 부재=legacy 폴백 서술)로 신규 블록 추가.
- s3keys.py: `RENDERED_COMPARE_RENDER_VERSION = 1` + `build_rendered_compare_key(uid, analysis_id) -> f"results/{uid}/{analysis_id}/compare_v{RENDERED_COMPARE_RENDER_VERSION}.mp4"` (단일 출처 — 저장측(pipeline)·서명측(playback-url) 공유, build_coach_audio_key 독스트링 관례).
- firestore_admin.py: `_validate_rendered_compare`(키 = RENDERED_COMPARE_KEYS 정확히, status enum, done→key 는 "results/" prefix + ".mp4" suffix 비어있지 않은 str, failed→key == "") + `update_analysis_rendered_compare(uid, analysis_id, key, status)` — `result.renderedCompare` **단일 field-path** `.update()` (update_analysis_coach_audio:1494 뼈대 복제, T-27-18/D-03 사후 단일 필드 규율 명기).
- playback-url app.py: 디스패치(:252-261)에 coachAudio 분기 **다음** `if asset == models.PLAYBACK_ASSET_RENDERED_COMPARE: return _handle_rendered_compare(uid, analysis_id)` 추가(기존 asset 응답 byte 불변 — 분기 순서만 추가). `_handle_rendered_compare` = _handle_asset(:83) 규율 복제: 서버가 build_rendered_compare_key 로 canonical **구성** + doc `result.renderedCompare.status == 'done'` + 저장 key **전체 문자열 exact 비교** 후에만 `_sign_get(expected, expires=_ASSET_EXPIRES, content_type=video/mp4)`. 가드 위반 전부 동일 404. **V-0 규율**: 존재 확인 없는 추측 서명 금지 — done+exact 이중 가드가 그 구현(260806-sjt 선례 주석 인용).
- docs/contract.md: §12.8 뒤 **§12.9 renderedCompare** 신설(§12.7 서식 미러 — 사후 스테이지·리그 ALL PASS 게이트·부재=듀얼 플레이어 폴백·이중 발화 방지 원칙·URL 비저장/재서명 H-02·3-way lockstep 각주) + POST /playback-url asset 표에 'renderedCompare' 행 + 문서 말미 changelog 1줄.

**4) deferred 렌더 스테이지 (pipeline app.py):**
- `_run_deferred_coach_audio` 반환형을 `list[dict]`(items)로 변경(현 None — 기존 호출측 무시라 additive). 호출부(:6760)에서 `coach_audio_items` 로 수령.
- `_run_deferred_compare_render(*, result, keypoint_report_dict, coach_audio_items, uid, analysis_id, bucket, local_video_path, reference_local_video_path)` 신설 — spot_check 스테이지(:6819-6827) **뒤**에 `with _stage(timings_ms, analysis_id, "compare_render"):` 로 호출(가장 무거운 표현물 = 마지막, outer finally unlink 전이라 두 로컬 영상 유효 — fault_zoom 주석 선례 명기). 게이트(전부 만족 시에만 시도, 아니면 **doc 필드 무접촉 스킵** + log.info):
  (a) env `RENDERED_COMPARE_ENABLED` != "0" (kill-switch, 기본 ON — POLLY_VOICE_ID env 스왑 선례),
  (b) mode == MODE_EXPERT 이고 reference_local_video_path 존재 (Mode3 는 이번 범위 밖 — 폴백 = 기존 듀얼 플레이어),
  (c) 추출 능력 프로브: rtmlib import 가능 + YOLOX_ONNX_PATH/RTMW_ONNX_PATH 실파일 존재 (Lambda 자동 스킵 — CPU NaN 경로에 GPU 스테이지 진입 0).
  스테이지 본체 (어떤 경로도 재raise 0 — _run_deferred_fault_zoom 규율 복제):
  1. workdir = tempfile 하위. coach_audio_items 의 key 를 S3 GET → audio_dir/`r{NN}.mp3`(recordId 콜론 앞 — build_timeline 파일명 계약). item 0건이어도 진행(freeze 0 = 순수 정렬 재생 편, 리그 C 가 freeze-0 분기 보유).
  2. `align = compare_align.build_align(local_video_path, reference_local_video_path, records, workdir)` — **align 실패 = failed 마킹**(doc 리포트 폴백 렌더 금지 — belle 반려 이력, must_have truth 1).
  3. `doc_like = {"result": {**result, "keypointReport": keypoint_report_dict}}` 로 `compare_render.render(...)` 호출(keypointReport 는 complete_analysis kwarg 라 in-memory result 에 없음 — build_timeline:826 이 무조건 읽는다, 주석 박제). moments/overrides = None.
  4. `ok, lines = compare_verify.verify(out_mp4, report, workdir)` — **ok 아니면 S3 업로드·doc 부착 없이 failed 마킹** + FAIL 라인 log.warning (돌파 ② "전 항목 PASS 아니면 없음").
  5. PASS 시 S3 put_object(key=build_rendered_compare_key, ContentType="video/mp4") → `update_analysis_rendered_compare(..., status=done)`.
  6. 예외/FAIL → `update_analysis_rendered_compare(uid, analysis_id, "", status=failed)` 시도, 그마저 실패 = log.exception 만(부재 유지 = 앱 폴백). workdir 는 finally 정리.
- **채점 무접촉**: complete_analysis 이후 표현물 스테이지 — deduction_engine/dimensions/kismam/motiondtw/temporal/features/assemble 등 채점 모듈 파일 수정 0.

**5) 로컬 스테이지 검증 (GPU 없이 — 픽스처 align 주입):**
`backend/scripts/verify_compare_stage_local.py` 신설 — 픽스처(.planning/phases/35-server-rendered-comparison-video/data/{motion}) doc.json + align.json + scratchpad 영상/mp3 로 스테이지 함수 경로를 로컬 실행: build_align 을 픽스처 align 반환 스텁으로 치환(infer_fn/monkeypatch — GPU 추출부만 skip), S3 업로드·firestore update 는 기록 스텁, 산출 mp4 를 compare_verify.verify 로 판정해 exit 0/1. elbow 1편으로 실행(운영 경로 = 오버라이드 None — 프로토 v7 과 문장이 달라도 무방, 리그 ALL PASS 가 판정 기준). Pod 재가동 시엔 스텁 없이 실 build_align 로 같은 스크립트를 돌리는 이중 용도(--build-align 플래그) — SUMMARY 의 Pod 검증 절차가 이 스크립트를 지목한다.

**6) 신규 유닛 (backend/tests/phase35/, phase32/test_coach_audio.py 서식 미러):**
- test_rendered_compare_contract.py: s3keys 빌더 형식, models 상수, _validate_rendered_compare(done/failed/키위반/prefix 위반), update_analysis_rendered_compare field-path(_doc monkeypatch).
- test_compare_render_stage.py: 게이트 스킵 3종(env off/모드/능력 프로브), align 실패→failed, 리그 FAIL→업로드·done 부착 0 + failed 마킹, 렌더 예외→failed, failed write 실패→무raise. 전부 render/verify/S3/firestore mock — 실렌더 0.
- test_compare_align_recompute.py: 픽스처 align.json 의 userKp/refKp/score 에서 pose_feature→D→dtw_path→smooth_curve 재계산 → 저장 curveRefSec 와 max|Δ|≤0.2s, 짝 재선정 재실행 → pairs refVideoSec |Δ|≤0.2s (반올림 유래 근사 허용 — GPU 없는 리팩터 회귀 게이트). elbow 1픽스처.
- test_playback_url_rendered_compare.py: done+exact=200 서명, status failed/부재/stale key=404, 기존 asset 경로 무회귀 1건.

**7) byte-보존 게이트 (리팩터 후):** 0) 과 동일 커맨드로 3편 재렌더 → `cmp out_base.mp4 out_ref.mp4` 3건 + report JSON diff 0 + 리그 3편 ALL PASS.

커밋 분리(한국어·이모지 금지): ① cue_text 분리+라이브러리화+byte 게이트 증거, ② 계약 py+s3keys+firestore_admin+playback-url+contract.md, ③ deferred 스테이지+로컬 검증 스크립트+유닛.
  </action>
  <verify>
    <automated>PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/phase35 && backend/.venv/bin/python backend/scripts/verify_compare_stage_local.py --motion elbow (exit 0 = 리그 ALL PASS) && cmp 3편 byte-동일 + 리그 3편 exit 0</automated>
  </verify>
  <done>라이브러리 4모듈 존재, 프로토 CLI 3종 byte-보존 cmp PASS, 스테이지가 리그 PASS 시에만 done+key 를 부착(FAIL/예외 = failed, 분석 무훼손), playback-url 'renderedCompare' done+exact 만 서명, contract.md §12.9 존재, phase35 유닛 전부 GREEN, 로컬 스테이지 검증 mp4 리그 ALL PASS.</done>
</task>

<task type="auto">
  <name>Task 2: 계약 ts + 앱 — 단일 mp4 플레이어 + 폴백 강등 + 이중 발화 방지</name>
  <files>app/src/types/analysis.ts, app/src/lib/api.ts, app/src/components/RenderedComparePlayer.tsx, app/src/app/analysis/result.tsx</files>
  <action>
**1) 계약 ts측 (3-way 마지막 면):** analysis.ts 에 `RenderedCompare { status: 'done' | 'failed'; key: string }` interface + `AnalysisResult.renderedCompare?: RenderedCompare` (coachAudio?:935 인접, CoachAudio 블록:648-668 주석 관례 미러 — 부재=legacy 듀얼 플레이어 폴백, URL 비저장/asset 재서명, models.py RENDERED_COMPARE_KEYS·contract.md §12.9 lockstep 각주). `app/src/lib/userAnalyses.ts` normalize 가 result 필드를 통과시키는 방식 확인 — 화이트리스트형이면 renderedCompare 통과 추가, passthrough 형이면 무수정.

**2) api.ts:** `requestAssetPlaybackUrl`(:154-167) asset union 을 `'correctedPose' | 'rotation' | 'renderedCompare'` 로 확장 (시그니처 외 로직 무변경 — 서버가 key 전권 소유 주석 유지).

**3) RenderedComparePlayer.tsx 신설:** props = `{ analysisId: string; onUnavailable: () => void }`. mount 시 `requestAssetPlaybackUrl(analysisId, 'renderedCompare')` → expo-video `useVideoPlayer` + `VideoView`(nativeControls, contentFit contain — mp4 자체가 두 패널 합성이라 오버레이·동기 로직 0). URL 은 1시간 TTL asset 서명이라 저장·재사용하지 않고 mount 마다 재발급(만료 재서명 = 기존 asset 패턴). fetch 실패/404 → `onUnavailable()` 호출(화면이 듀얼 플레이어로 강등) + `__DEV__` warn — catch 삼킴 금지([[icloud-offload-breaks-original-asset-picker]] 교훈). 로딩 중 자리 = 기존 카드 규격(theme 토큰만, 하드코딩 금지, 다크 배경 신설 금지 — 영상 콘텐츠 자체의 어두움은 무관). 신규 화면 디자인 아님 — 기존 '동작 비교' 섹션 내 재생원 교체.

**4) result.tsx 분기 (동작비교 섹션 :2500-2762):**
- `const renderedCompareReady = result.renderedCompare?.status === 'done' && !!result.renderedCompare.key;` + `const [renderedUnavailable, setRenderedUnavailable] = useState(false);` (analysisId 변경 시 리셋).
- `renderedCompareReady && !renderedUnavailable` 이면: 섹션 헤더("동작 비교") 아래 `<RenderedComparePlayer analysisId={analysisId} onUnavailable={() => setRenderedUnavailable(true)} />` 를 렌더하고 **VideoCompare + KeypointOverlayToggle 을 렌더하지 않는다** — cueWindows·cueRefSnapSecs·audioAnalysisId·timelineTicks·renderCueIllustration 이 전부 VideoCompare props 이므로 앱 큐 오디오 prefetch·자막·틱 발화가 **구조적으로 OFF** (이중 발화 방지의 구현 = 분기, 개별 prop 끄기 아님 — 주석으로 원칙 박제). PartChipsRow(감점 시트 진입점)·정렬 upsell 배너는 발화 없음 — 분기 밖 현행 유지.
- 그 외(부재 legacy·failed·fetch 실패 강등) = 기존 VideoCompare 경로 **무수정** (폴백 강등 — 이 가지의 코드 diff 0).
- Firestore onSnapshot 으로 renderedCompare 가 세션 중 도착하면 자동 전환됨(구독 기반 — 별도 폴링 금지) — 전환 시점 UX 는 시뮬 확인 항목으로 SUMMARY 에 기재.
- coachAudioAnalysisId(:2049-2055)·cueWindows 등 파생 계산은 무수정(분기로 미사용화) — 삭제 금지(폴백 가지가 소비).

주석은 한국어 + 근거 인용(contract.md §12.9, quick-260808-jix) 관례. 커밋 1개(한국어).
  </action>
  <verify>
    <automated>cd app && npm run typecheck && grep -c "RenderedComparePlayer" src/app/analysis/result.tsx | awk '$1>=2{exit 0}{exit 1}' && grep -n "renderedCompare" src/types/analysis.ts src/lib/api.ts</automated>
  </verify>
  <done>analysis.ts/RenderedCompare + api.ts union + RenderedComparePlayer 존재. renderedCompare done doc = 단일 mp4 재생이고 그 분기에서 VideoCompare(=큐 오디오·자막·틱 발화 경로) 미렌더. 부재/failed/URL 실패 = 기존 듀얼 플레이어 경로 byte-동등. typecheck GREEN.</done>
</task>

<task type="auto">
  <name>Task 3: 게이트·회귀 일괄 + SUMMARY (미검증 박제 + Pod 재가동 검증 절차)</name>
  <files>.planning/quick/260808-jix-phase-35-3-way-mp4/260808-jix-SUMMARY.md</files>
  <action>
**1) 채점 무접촉 diff 게이트:** `rtk git diff --stat main -- backend/shared/python/sunity_shared/analysis/{deduction_engine,dimensions,kismam,motiondtw,temporal,features,assemble,selfmotion}.py` 출력 0줄 확인 (렌더 스테이지는 complete 이후 표현물 — overallScore·deductionBreakdown byte 무접촉 구조 증명).

**2) pytest 전체 baseline diff:** 작업 전 캡처해 둔(없으면 main 체크아웃으로 캡처) `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests` 의 FAILED/ERROR **node-ID 목록**과 작업 후 목록 diff = IDENTICAL (260801 확립 게이트 — 총 카운트 아닌 node-ID 단위, pre-existing 실패는 그대로·신규 실패 0). 신규 phase35 테스트는 전부 PASS 로 추가.

**3) 프로토 CLI byte-보존 최종 재확인:** Task 1-7) 의 cmp 3건 결과를 SUMMARY 에 명령·결과 그대로 박제 (elbow/kipup/pdshapefault, "동사 = 재봤다" 규율 — cmp exit 0 원문).

**4) SUMMARY 작성 (260808-jix-SUMMARY.md):**
- 산출물·커밋 목록, 게이트 증거(byte cmp / 리그 ALL PASS / pytest diff / 채점 diff 0 / typecheck).
- **미검증 표** (이유와 함께 박제 — 33 선례): ① Pod 실분석 E2E(스테이지 실 GPU align+렌더+S3+doc 부착) — Pod 없음, ② 실기기/시뮬 단일 mp4 재생·폴백 전환·세션 중 도착 전환 UX — 시뮬 확인은 orchestrator 후속(verify-ui-on-simulator-before-ota — OTA 는 이번 범위 밖), ③ playback-url 실배포 재서명(sam deploy 전), ④ Mode3 rendered compare = 의도적 범위 밖(폴백 상시).
- **"Pod 재가동 시 검증 절차" 1절**: (1) git pull + Pod env 확인(YOLOX_ONNX_PATH/RTMW_ONNX_PATH/RENDERED_COMPARE_ENABLED), (2) `verify_compare_stage_local.py --build-align` 로 실 GPU align 경유 리그 PASS 확인, (3) 실분석 1건(Mode1 픽스처 업로드) → Firestore doc renderedCompare done+key 도착 → 앱 시뮬에서 단일 mp4 재생 + 큐 오디오 미발화 확인, (4) 리그 FAIL 강제(예: 임계 임시 조정 아닌 **결손 입력**)로 failed 마킹·앱 폴백 확인, (5) Lambda(비위임) 경로에서 스테이지 자동 스킵 로그 확인. 각 단계 판정 기준 명시.

plan.md 갱신(루트 관례) 불필요 — quick 트랙은 SUMMARY 가 정본. 커밋 1개(문서).
  </action>
  <verify>
    <automated>test -f .planning/quick/260808-jix-phase-35-3-way-mp4/260808-jix-SUMMARY.md && grep -c "Pod 재가동" .planning/quick/260808-jix-phase-35-3-way-mp4/260808-jix-SUMMARY.md | awk '$1>=1{exit 0}{exit 1}' && rtk git diff --stat main -- backend/shared/python/sunity_shared/analysis/deduction_engine.py backend/shared/python/sunity_shared/analysis/dimensions.py | wc -l | awk '$1==0{exit 0}{exit 1}'</automated>
  </verify>
  <done>채점 모듈 diff 0, pytest FAILED/ERROR node-ID baseline diff IDENTICAL, byte cmp 3건 증거 박제, SUMMARY 에 미검증 표 + Pod 재가동 검증 절차 존재.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 앱→playback-url API | 클라이언트가 asset 종류만 지정 — key 는 절대 클라이언트 입력 불가 |
| Pod 스테이지→S3/Firestore | 백엔드 자격증명으로 표현물 업로드·doc 부분 갱신 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35J-01 | Information Disclosure | playback-url asset 'renderedCompare' | mitigate | 서버 canonical 구성(build_rendered_compare_key) + doc status=='done' + 전체 문자열 exact 비교 후에만 서명, 가드 위반 전부 동일 404 (M2-01/H-02 복제). uid 는 토큰 유래 — 타 uid 객체 서명 불가 |
| T-35J-02 | Tampering | doc result.renderedCompare | mitigate | _validate_rendered_compare (키 정확 집합 + enum + results/ prefix + .mp4 suffix, failed→key '') — 임의 키 주입 차단 |
| T-35J-03 | DoS (디스크/시간) | compare_render 스테이지 workdir | mitigate | tempfile workdir + finally 정리, 스테이지 전체 graceful(분석 SERIAL 불변 — 다음 분석 차단 없음), RENDERED_COMPARE_ENABLED kill-switch |
| T-35J-04 | Elevation | Lambda CPU 경로에서 GPU 스테이지 오진입 | mitigate | 능력 프로브(rtmlib import + 가중치 실파일) fail-closed 스킵 |
| T-35J-SC | Tampering | 패키지 설치 | accept | 신규 패키지 설치 0 — rtmlib/cv2/PIL/imageio_ffmpeg 전부 기존 의존, requirements 무변경 |
</threat_model>

<verification>
- 프로토 CLI 3종 byte-보존: elbow/kipup/pdshapefault `cmp` 3건 PASS + 리그 3편 ALL PASS (리팩터 전 baseline → 후 재렌더).
- 로컬 스테이지 검증: verify_compare_stage_local.py (픽스처 align 주입, GPU skip) 산출 mp4 리그 ALL PASS exit 0.
- 신규 유닛 phase35 전부 GREEN + 전체 pytest FAILED/ERROR node-ID baseline diff IDENTICAL.
- 채점 무접촉: 채점 모듈 git diff 0 (deduction_engine/dimensions 등).
- 앱: `npm run typecheck` GREEN + renderedCompare 분기 grep 게이트.
- 계약 3-way: contract.md §12.9 ↔ models.py RENDERED_COMPARE_* ↔ analysis.ts RenderedCompare 동시 존재 (lockstep 각주 상호 인용).
</verification>

<success_criteria>
- Mode1 분석 사후 스테이지가 GPU align 재생성→렌더→리그 ALL PASS 시에만 S3 업로드+doc renderedCompare(done,key) 부착. FAIL/예외 = failed 마킹, 분석 무훼손, Lambda/기능 off/Mode3 = 필드 무접촉 스킵.
- renderedCompare done doc 의 앱 동작비교 = 단일 mp4 재생, 큐 오디오·자막·틱 발화 경로 구조적 OFF. 그 외 doc = 기존 듀얼 플레이어 byte-동등 폴백.
- 프로토 CLI byte-보존 + 채점 byte 무접촉 + 기존 테스트 무회귀 + 계약 3-way lockstep.
- 실기기·실분석 E2E 미검증은 SUMMARY 에 이유와 함께 박제 + Pod 재가동 검증 절차 1절 산출.
</success_criteria>

<output>
완료 시 `.planning/quick/260808-jix-phase-35-3-way-mp4/260808-jix-SUMMARY.md` 작성 (Task 3 이 본체).
</output>
