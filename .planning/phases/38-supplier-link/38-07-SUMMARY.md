---
phase: 38-supplier-link
plan: 07
subsystem: pipeline
tags: [pipeline, lambda, runpod, s3, registration, tdd, pytest, supplier-link]

# Dependency graph
requires:
  - phase: 38-supplier-link (38-01)
    provides: models.REG_ERR_* / REGISTRATION_ERROR_MESSAGE / REFERENCE_*_DURATION_SEC / MAX_VIDEO_BYTES / ANALYSIS_FIELD_SELF_CHECK_* · s3keys.parse_reference_key / build_reference_final_key / build_upload_key
  - phase: 38-supplier-link (38-05)
    provides: registration_checks.check_registration / joint_labels_ko / default_stand_frames / DETAIL_NO_FLOOR_REFERENCE · rtmw_engine.estimate_with_person_counts
  - phase: 38-supplier-link (38-06)
    provides: firestore_admin get_reference_registration(_private) · claim_registration · set_registration_queued/active/failed · set_reference_angles · begin_self_check · create_analysis_doc · set_reference_self_check
provides:
  - "pipeline.lambda_handler: for 루프 첫 줄 parse_reference_key → _handle_reference_upload(reference/ 접두사 분기), uploads/ 학생 경로 byte-무접촉"
  - "pipeline._handle_reference_upload(bucket, key, ref) -> 'skipped'|'queued'|'delegated'|'failed' — v1/비registering/uid 불일치 스킵 · Pod 부재 queued(쓰기 실패는 raise) · claim 뒤 /register-reference 위임 1회 · 위임 실패 failed(server_error)"
  - "pipeline._pod_available() -> (bool, reason) — runpod_env_unset · pod_expected_down(SSM /sunity/motion/runpod-pod-expected) · health_failed(/health 12s, status ok + pipeline_loaded) · healthy; _ssm_get_parameter · _health_url · _register_url · _runpod_route"
  - "pipeline._delegate_to_runpod(bucket, key, *, url=None, extra=None) — 기본 호출 byte-동일, 등록은 url=/register-reference + payload jobId"
  - "pipeline._register_reference(bucket, key, uid, ref_id, job_id) — jobId 대조 → head_object 크기 → copy_object(upload→v1, CopySourceIfMatch) → v1 다운로드 → probe 길이 → extract(end_s=상한+1) → T/fps 재검사 → estimate_with_person_counts → profile/coco17 → build_keypoint_report → _dataclass_to_camel_case_dict 한 번 → check_registration → angles(compute_joint_angles → joint_uncertainty → temporal_fill, round 2, NaN→0) → max_split 언패킹 → set_reference_angles → set_registration_active → _trigger_self_check"
  - "pipeline._fail_registration / _duration_verdict / _stand_frames / _trigger_self_check(begin_self_check → create_analysis_doc → copy_object v1→uploads/)"
  - "frame_extractor.FfmpegFrameExtractor.probe_duration_sec(path) -> float | None — meta duration, nframes/fps 폴백, 판정 불가 None"
affects: [38-08 (Pod /register-reference 라우트가 _register_reference 를 부른다 · selfScore 훅), 38-09 (template: ssm:GetParameter runpod-pod-expected ARN · 버킷 알림 reference/ 접두사 · Pod 자격증명 PutObject 범위 simulate), 38-14 (Pod 실물 실패 관측 · uploads/reference PutObject probe)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "등록 분기의 예외 정책은 학생 경로와 다르다 — 상태 쓰기(queued/claim) 실패만 raise(SQS BatchSize 1 · maxReceiveCount 3 → DLQ 가 재전달·격리), 위임 실패는 doc failed 로 소비"
    - "확정 객체 = 서버 copy_object(CopySourceIfMatch=ETag) — presign 은 upload 키에만, 소비(angles·videoS3Key·자기 재현성)는 v1 에만"
    - "dataclass → camelCase dict 변환은 한 번, 같은 객체를 판정과 writer 에 — 판정 입력 계약(Mapping)과 저장 형상(legacy referenceKeypointReport)이 한 물건"
    - "합성 강제: 실제 엔진(create_with_inferencer) + 프레임별 mock 추론 + 가짜 S3 객체 저장소(조건부 복사) — 판정·각도·max_split 은 실제 함수, spy 는 인자만 기록"

key-files:
  created:
    - backend/tests/test_pipeline_reference_dispatch.py
    - backend/tests/test_register_reference_pipeline.py
    - backend/tests/test_frame_extractor_probe_duration.py
  modified:
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/analysis/frame_extractor.py

key-decisions:
  - "38-07: copy_object 의 ClientError 는 PreconditionFailed(처리 중 원본 교체) 뿐 아니라 AccessDenied 등 전부 failed(server_error) 로 doc 에 남긴다 — Pod 자격증명 reference/* PutObject 거부(T-38-07-7)가 processing 에 멈춰 있지 않게"
  - "38-07: n_stand 는 폼 clipRange.execStartS × fps 가 유한·양수일 때만, 아니면 registration_checks.default_stand_frames(real_fps)(38-05 소비처) — 같은 식을 다시 쓰지 않는다"
  - "38-07: 자기 재현성 분석 doc 의 uid = 공급자 uid, fileName = self-check-{refId}.{ext}, learningOptIn = 비공개 consent.training — 표식 2개는 models.ANALYSIS_FIELD_SELF_CHECK_* 상수만(리터럴 0)"
  - "38-07: v1 ETag 가 upload ETag 와 다르면 등록하지 않는다(server_error) — 단일 PUT 객체는 ETag=MD5 라 같아야 하고, 다르면 예상 밖 상태(멀티파트 등)를 fail-closed"

patterns-established:
  - "Pod 부재 판정 = env → SSM(쓰기 측 이름) → /health(podwatch probe 원문) 순서, 조회 실패는 '모름' 으로 다음 단계"
  - "등록 서비스 안 함수 순서를 grep 게이트로 잠근다(head_object < copy_object < download < probe < extract, camel 변환 < check_registration, begin < create_doc < copy)"

requirements-completed: [REQ-38-1, REQ-38-2, REQ-38-4]

# Metrics
duration: 19min
completed: 2026-09-28
---

# Phase 38 Plan 07: 파이프라인 reference/ 분기 + 등록 서비스 `_register_reference` Summary

**`reference/{uid}/{refId}/upload.{ext}` 이벤트가 파이프라인 입구에서 더 이상 스킵되지 않는다 — Pod 유무로 `queued`/`delegated` 로 갈리고(상태 쓰기 실패만 SQS 재전달, 위임은 `claim_registration` 뒤 정확히 1회), 등록 서비스 `_register_reference` 가 크기·길이를 디코딩 **전**에 거른 뒤 불변 v1 객체(`copy_object(CopySourceIfMatch=ETag)`)에서 기준 11개와 **같은 함수 순서**로 angles·`anglesRealFps`·`referenceKeypointReport`(camelCase dict — `check_registration` 이 본 것과 같은 객체)·`referenceSplitAngle`(실제 `max_split` 튜플 언패킹)을 쓰고 `active` 로 만든 다음 자기 재현성을 선기록 → 분석 doc → v1 복사 순서로 기존 경로에 태운다. 실패 8코드(no_human · low_confidence(한국어 부위 라벨) · multiple_people · no_standing_start · too_short · too_long · too_large · server_error)가 합성 입력 pytest 로 각각 doc 에 남는 것이 강제됐다. Pod · S3 · Firestore · GPU 호출 0, 채점 경로 호출 0.**

## Performance

- **Duration:** 19min (실행 시작 2026-09-28T15:49:15Z → Task 2 GREEN 커밋 뒤 관측 2026-09-28T16:08:05Z)
- **Tasks:** 2/2 (TDD — test → feat 커밋 각 2)
- **Files modified:** 5 (+1702 / −4, `git diff --stat b10415ef..HEAD` [확인] — 삭제 4줄은 `_delegate_to_runpod` 시그니처·payload·URL 줄의 교체)

## Accomplishments

- **Task 1 — 입구 분기(REQ-38-1 · D-20 · R3/R4/R5).** `lambda_handler` for 루프 첫 줄에서 `parse_reference_key(key)` → `_handle_reference_upload` → `continue`; 그 아래 `uploads/` 코드는 무접촉(`test_pipeline_dispatch.py` 6건 그대로 통과, 같은 이벤트에 두 종류가 섞여도 각자 처리). `_pod_available` 은 env → SSM `/sunity/motion/runpod-pod-expected`(**쓰기 측** `start_server.sh:95`·`pod_teardown.py:125` 가 갱신하는 이름 — podwatch 기본값 `pod-expected` 가 아니다) → `/health`(12초, UA 헤더, `status=="ok" and pipeline_loaded`). Pod 부재면 `set_registration_queued(pod_down)` 가 **성공했을 때만** 정상 반환하고 그 쓰기·`claim_registration` 의 예외는 전파한다(SQS `AnalysisQueue` BatchSize 1 · maxReceiveCount 3 → `AnalysisDLQ`). 위임은 claim True 뒤 `_delegate_to_runpod(url=…/register-reference, extra={"jobId"})` 1회 — 같은 이벤트 2건이면 둘째는 `중복 이벤트 스킵`. 위임 예외는 `set_registration_failed(server_error)` 로 소비.
- **Task 2 — 등록 서비스(REQ-38-2·REQ-38-4 · D-05·D-09·D-10 · R1/R5/R6/R8/R9 · 차단 1).** `_register_reference` 는 입구에서 `doc.jobId == job_id` 를 대조(stale 이면 S3·writer 호출 0) → `head_object` 크기(101MB → `too_large`, 다운로드 0) → `copy_object(upload → v1, CopySourceIfMatch=ETag, MetadataDirective=COPY)`(PreconditionFailed/AccessDenied → `server_error`) → v1 ETag 재확인 → **v1** 다운로드 → `probe_duration_sec`(35초 → `too_long`, 3초 → `too_short`, 콤보 60초, 전부 `extract` 0회) → `extract(end_s=상한+1.0)` 캡 → `len(frames)/real_fps` 재검사(probe None 경로) → `estimate_with_person_counts`(NoHumanError → `no_human`, 기존 `ERROR_MESSAGE` 문구) → `measure_body_profile` → `to_coco17_array` → `build_keypoint_report`(None → `server_error`, 판정 미호출) → `_dataclass_to_camel_case_dict` **한 번** → `check_registration(counts, report, n_stand)` → 실패면 `REGISTRATION_ERROR_MESSAGE[reason]` 의 `{joints}` 를 `joint_labels_ko` 로 치환 → angles(`compute_joint_angles` → `joint_uncertainty` → `temporal_fill`, round 2, NaN→0.0) → `peak, peak_idx = max_split(split_angle_series(kp))` → `set_reference_angles(keypoint_report=report)`(같은 dict 객체) → `set_registration_active(video_s3_key=v1, video_etag)` → `_trigger_self_check`(`begin_self_check` → `create_analysis_doc` → `copy_object(v1 → uploads/{uid}/{newId}.{ext})`, ②·③ 실패는 `set_reference_self_check(failed)`). 임시 파일은 성공·실패 모두 finally 에서 삭제.
- **`frame_extractor.probe_duration_sec`** — `probe_effective_fps` 와 같은 reader/meta 어법. `duration` 유한·양수 → 그 값, 아니면 `nframes/fps`(둘 다 유한·양수), 아니면 None. fps 이력 무접촉.

## Task Commits

1. **Task 1: lambda_handler 접두사 분기 + _pod_available + _handle_reference_upload + _delegate_to_runpod(url=, extra=)** — `b65746da` (test, RED: `17 failed, 18 errors` — AttributeError `_pod_available`/`_handle_reference_upload` 등) → `4219aeb5` (feat, GREEN: `41 passed` = 신규 35 + 기존 6)
2. **Task 2: frame_extractor.probe_duration_sec + _register_reference(+ _fail_registration · _duration_verdict · _stand_frames · _trigger_self_check)** — `1f12236e` (test, RED: `15 failed, 1 passed, 25 errors` — 통과 1 = 순수 `max_split` 계약) → `2b038ace` (feat, GREEN: `41 passed` = 등록 26 + probe 15)

**Plan metadata:** 아래 docs 커밋(SUMMARY · STATE · ROADMAP). push 는 하지 않았다(오케스트레이터 지시 — belle 과 정산).

## Files Created/Modified

- `backend/functions/pipeline/app.py` (+479 / −4) — import 3(`build_reference_final_key` · `build_upload_key` · `parse_reference_key`) + `from sunity_shared.analysis import registration_checks` + `from botocore.exceptions import ClientError`; `_delegate_to_runpod(bucket, key, *, url=None, extra=None)`(:211, 본문 byte-동일 + `url or _RUNPOD_URL` · payload `**(extra or {})`); 블록 "Phase 38 (38-07 T1)" :249-379 — `_POD_EXPECTED_PARAM` :263 · `_HEALTH_TIMEOUT_S = 12` :264 · `_ssm_get_parameter` :267 · `_runpod_route` :277 · `_health_url` :285 · `_register_url` :290 · `_pod_available` :295 · `_handle_reference_upload` :328; 블록 "Phase 38 (38-07 T2)" :10443-10758 — `_fail_registration` :10461 · `_duration_verdict` :10492 · `_stand_frames` :10504 · `_register_reference` :10517 · `_trigger_self_check` :10707; `lambda_handler` :10761 의 for 루프 첫 줄 `ref = parse_reference_key(key)` :10773(< `parsed = parse_upload_key(key)` :10780). `_process` · recognizer · dimensions · assemble 호출부 무접촉.
- `backend/shared/python/sunity_shared/analysis/frame_extractor.py` (+30) — `FfmpegFrameExtractor.probe_duration_sec` :102(`probe_effective_fps` 바로 뒤, `extract` 무접촉).
- `backend/tests/test_pipeline_reference_dispatch.py` (신규, 35 tests) — `_Harness`(writer·claim·pod·delegate 기록 + 예외 주입): queued/queued 쓰기 실패 raise · claim→delegate(jobId 32-hex, url) · 중복 2건 = 위임 1 · claim 예외 raise · delegate 실패 → failed(server_error) · failed writer 마저 예외 = 로그만 · v1 스킵 · doc 없음/비registering(5 상태)/uid 불일치 스킵 · 반환값 계약 · uploads+reference 혼합 이벤트 · legacy 평면 키 무인식 · `_pod_available` 7케이스(env/SSM down/SSM 실패→health/미준비 3/URLError·Timeout/HTTPError) · `_ssm_get_parameter` 2(값 로그 0) · URL 파생 4 · 실제 `_delegate_to_runpod` 2(url/extra payload · 500 → RuntimeError).
- `backend/tests/test_register_reference_pipeline.py` (신규, 26 tests) — `_FakeS3`(객체 저장소 · `CopySourceIfMatch` 불일치 → `ClientError(PreconditionFailed)` · `deny_copy_prefix` → AccessDenied · `on_head` 로 head 응답 **뒤** 원본 교체) · `_FakeExtractor` · `_FakePose`(실제 `RTMWPoseEngine.create_with_inferencer` + 프레임별 `side_effect`) · `_frames_133(T, n_people, stand, ankle_stand_y, ankle_window_y, ankle_conf)` · `check_registration` spy(실제 함수 위임). 케이스: too_large(다운로드 0) · R5 순서(head→copy→head→download v1) · 원본 교체 → server_error · AccessDenied → server_error · too_long/too_short(extract 0) · 콤보 35 통과/65 거부 · probe None 캡 31.0/61.0 + 재검사 · T=0 → server_error · no_human · low_confidence(발목 0.2 + 바닥 위반 형상, joints `['왼쪽 발목','오른쪽 발목']`, 문구 치환) · multiple_people · no_standing_start · `max_split` 계약 · happy path(판정 입력·report dict 12관절·`axisData`·**같은 객체**·angles 소수 2자리·NaN 0·active v1+ETag·begin→doc→copy 순서·payload 리터럴 단언) · consent.training → learningOptIn · report None → server_error(판정 0) · begin False → doc/복사 0 · uploads 복사 실패/doc create 실패 → self_check failed · stale job 쓰기 0 · doc 없음 RuntimeError · 재PUT 불변 · 임시 파일 삭제(성공·실패) · 채점 경로 미호출.
- `backend/tests/test_frame_extractor_probe_duration.py` (신규, 15 tests) — meta duration · nframes/fps 폴백 · None 9형(빈/fps만/nframes만/fps 0/nframes inf/duration 0·음수·inf·문자열) · NaN duration → 폴백 · reader 예외 · meta 예외(+close) · fps 이력 무접촉.

## 관측 (이 세션이 직접 실행/읽은 것)

- [확인] `cd backend && .venv/bin/python -m pytest tests/test_pipeline_reference_dispatch.py tests/test_register_reference_pipeline.py tests/test_frame_extractor_probe_duration.py tests/test_pipeline_dispatch.py -q -p no:cacheprovider` → `82 passed in 2.76s`(35 + 26 + 15 + 6). 인터프리터 = `backend/.venv`.
- [확인] **전체 suite**(최종 docs 커밋 전 1회, 오케스트레이터 지시): `cd backend && .venv/bin/python -m pytest tests -q -p no:cacheprovider` → **`5499 passed, 20 skipped, 42 warnings in 64.89s`**. 실패 0 — 플랜 범위 실행과 다른 결과 없음.
- [확인] RED 실측: T1 `17 failed, 18 errors`(fixture 의 `monkeypatch.setattr(app, "_pod_available", …)` AttributeError) · T2 `15 failed, 1 passed, 25 errors`(`app.registration_checks`/`_register_reference`/`probe_duration_sec` 부재; 통과 1 = `max_split` 순수 계약).
- [확인] **R1 — `assert max_split(np.array([20.0, 90.0, 70.0])) == (90.0, 1)` 이 실제 함수로 통과**했고(`test_max_split_unpacking_contract`), happy path 로그가 실제 `max_split` 산출 `split=61.93 peak_idx=10`(합성 창 자세, 두 허벅지 벌림)을 남겼다. `grep -c "peak, peak_idx = max_split(" app.py` = 1 · `float(max_split(` = 0 · 테스트 파일 `max_split` 4회 · `monkeypatch.setattr(.*max_split` 0.
- [확인] T1 게이트: `ref = parse_reference_key(key)` :10773 < `parsed = parse_upload_key(key)` :10780 · `"/sunity/motion/runpod-pod-expected"` 1 · `_HEALTH_TIMEOUT_S = 12` 1 · 5 def = 5 · `claim_registration(` 호출 :358 < `_delegate_to_runpod(` :363 · `git diff` 삭제 줄 = `_delegate_to_runpod` 4줄뿐(uploads/ 분기 본문 무변경).
- [확인] T2 게이트: 3 def = 3 · `def probe_duration_sec` = 1 · `CopySourceIfMatch=` = 1 · `build_reference_final_key(` = 1 · `_register_reference` 안 순서(함수 내 상대 줄) head_object 32 < copy_object 44 < `_download_analysis_video` 67 < probe_duration_sec 71 < `extract(` 78 · `_dataclass_to_camel_case_dict(report_obj)` 119 < `check_registration(` 121 · `_process(\|build_mode1\|recognize(` 안 = 0 · `estimate_with_person_counts` 1 · `keypoint_report=report,` 1 · `asdict(report` 0 · `_trigger_self_check` 안 begin_self_check 12 < create_analysis_doc 13 < copy_object 14 · 리터럴 `"selfCheckForReference"|"selfCheckJobId"` 0 · 상수 2.
- [확인] 차단 1: happy path 에서 `check_registration` spy 의 둘째 인자가 `dict`, `len(report["joints"]) == 12`, `report["frames"] == 60`, `"axisData"`·`"axisMask"` 있음, `"axis_data"` 없음, `set_reference_angles(keypoint_report=…)` 가 **같은 객체(`is`)**. `build_keypoint_report` → None 이면 `set_registration_failed(server_error)` 1회 · `check_registration` 0회 · angles/active 0회.
- [확인] 커밋 4건 `b65746da` · `4219aeb5` · `1f12236e` · `2b038ace`, 플랜 커밋 범위 삭제 파일 0(`git diff --diff-filter=D b10415ef HEAD` 빈 출력), 미추적 파일 0. `.planning/TRAINING-DUE.md` 의 기존 미커밋 변경은 손대지 않았다(스테이징 0).
- [확인] 배포(sam/Lambda/rules) · RunPod 기동 · 라이브 URL 호출 · Firestore/S3/SSM 쓰기 · Firestore 스캔 · push 전부 0. `boto3.client("ssm")` 은 `_ssm_get_parameter` 호출 시점에만 만들어지고 테스트는 `app.boto3.client` 를 가짜로 바꿨다.
- [확인] 합성 판정 재료: `_frames_133` 은 앞 10프레임 서 있음(어깨 y 0.5 · 발목 0.8 → 몸길이 0.3, 바닥 0.8), 이후 창 자세(발목 0.7 → lowFoot +0.33 통과); 바닥 위반형은 서 있는 발목 0.6 · 창 발목 0.85(lowFoot −2.5 < −0.10). RTMW 133 레이아웃의 COCO 인덱스 5~16 은 `wholebody_keypoints.RTMW_KEYPOINT_INDICES` 실측과 같다.

## 진단 (관측에서 내가 붙인 해석 — 다음 세션 재검증 대상)

- **Pod 자격증명의 `reference/*`·`uploads/*` PutObject 범위 [미확인 — 38-09 T3 (E) `iam simulate-principal-policy` / 38-14 T2 3-b Pod 세션 probe 가 잰다].** `reference/*` 가 거부되면 등록은 R5 복사 단계에서 `failed(server_error)`(`test_v1_copy_access_denied_is_server_error` 가 그 경로를 잠근다), `uploads/*` 가 거부되면 `selfCheckStatus:'failed'` 로 강등되고 등록은 active 그대로 — Success ③ 을 못 잰다.
- **배선 순서 주의(38-08 → 38-09):** 이 코드가 Lambda 에 배포된 상태에서 Pod 에 `/register-reference`(38-08) 가 없으면 위임이 404 → `failed(server_error)` 로 소비된다(queued 가 아니다). Pod 코드가 먼저 올라가야 한다 [추론 — `_delegate_to_runpod` 의 HTTPError 경로에서 도출, 실물 미확인].
- Lambda 의 `ssm:GetParameter` 정책은 아직 `FirebaseSaParam` ARN 하나(template 무변경) — 38-09 전에는 `_ssm_get_parameter` 가 AccessDenied 로 None 을 내고 health 만으로 판정한다(fail-loud 설계라 동작은 한다) [추론].
- `MetadataDirective="COPY"` 가 upload 객체의 Content-Type(video/mp4 · video/quicktime)을 v1 에 그대로 옮긴다는 것은 boto3/S3 문서 기준 [추론 — 라이브 미확인]. 재생(P0 #6 Content-Type 함정)이 v1 을 보므로 38-14 실물에서 `head_object` 로 ContentType 을 한 번 볼 것.
- 브라우저 presigned PUT 은 단일 파트라 ETag = MD5 이고 복사본 ETag 와 같다 [추론]. 멀티파트로 올린 객체는 ETag 가 달라 `server_error` 로 fail-closed 된다 — 페이지(38-10/12) 가 멀티파트를 쓰지 않는 한 무관.
- iPhone mov/mp4 의 imageio 메타에 `duration` 이 항상 있는지 [미확인] — 없으면 None 경로(extract 캡 + T/fps 재검사)가 받는다.
- "REQ-38-1/2/4 완료" 는 **코드·테스트 층**의 완료다. 런타임(버킷 알림 `reference/` 접두사 · template IAM · Pod 라우트)은 38-08/38-09 뒤에만 참 [미확인 — 실행되지 않음].

## Decisions Made

- **copy 단계의 `ClientError` 전부 `server_error`** — 플랜은 `PreconditionFailed` 만 적었지만 AccessDenied(T-38-07-7)가 나면 raise 해도 결국 38-08 라우트가 `server_error` 로 적는다; 여기서 적으면 로그에 `code=AccessDenied` 가 남고 Lambda 폴백에서도 같은 결과다. PreconditionFailed 는 warning("처리 중 원본 교체"), 그 밖은 `log.exception`.
- **`_duration_verdict` · `_stand_frames` · `_runpod_route` 헬퍼 3개** — 플랜이 인라인으로 적은 식을 함수로 뺐다(같은 검사를 probe 값과 프레임 수에 두 번, URL 파생을 두 라우트에). 이름 있는 5 def / 3 def 게이트는 그대로(grep 은 이름을 센다). `_stand_frames` 는 38-05 인계대로 `default_stand_frames(real_fps)` 를 쓴다(플랜의 `round(STANDING_START_DEFAULT_SEC × fps)` 와 같은 값).
- **키·인자 대조** — `parse_reference_key(key)` 의 uid/ref_id 가 인자와 다르면 RuntimeError(플랜 밖, 4줄). 라우트가 잘못된 짝을 넘기면 다른 doc 을 활성화할 수 있어 막았다.
- **v1 ETag 불일치 = 등록 거부** — 플랜 그대로. 단일 PUT 객체는 같아야 하고, 다르면 모르는 상태라 fail-closed.
- **self-check 분석 doc** — `fileName = self-check-{refId}.{ext}`(플랜은 키 존재만), `createdAt/updatedAt = int(time.time()*1000)`(앱 loading.tsx 의 `Date.now()` 와 같은 단위), `bodyProfile` 은 넣지 않는다(공급자 자기 재현성은 자세 프로필 스냅샷 대상이 아니다 — [ASSUMED 선택]).
- **`verdict.detail == no_floor_reference` warning** — 38-05 권장대로 로그 한 줄(계약 변경 아님). 38-14 실물에서 버그와 진짜 실패를 가른다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] copy_object 의 비-PreconditionFailed `ClientError` 도 `server_error` 로 기록**
- **Found during:** Task 2 (R5 복사 단계 설계)
- **Issue:** 플랜은 `PreconditionFailed` 만 매핑 — Pod 자격증명이 `reference/*` PutObject 를 거부하면(T-38-07-7, 위협표는 "server_error" 라 적음) 예외가 함수 밖으로 나가 doc 이 `processing` 에 남는다(Lambda 폴백 경로엔 아직 감싸는 라우트가 없다).
- **Fix:** `except ClientError` 에서 코드별 로그 뒤 `_fail_registration(server_error)` + return.
- **Files modified:** `app.py`
- **Verification:** `test_v1_copy_access_denied_is_server_error`(download 0 · angles 0).
- **Committed in:** `2b038ace`

**2. [Rule 2 - Missing validation] 키와 인자(uid · ref_id) 대조**
- **Found during:** Task 2
- **Issue:** `_register_reference(bucket, key, uid, ref_id, job_id)` 는 키에서 uid/refId 를 또 파싱한다 — 둘이 어긋나면 남의 doc 을 활성화할 수 있다.
- **Fix:** 불일치면 RuntimeError(쓰기 0).
- **Files modified:** `app.py`
- **Verification:** 로직 검토(전용 테스트 없음 — 정상 경로 26건이 일치 인자로 돈다).
- **Committed in:** `2b038ace`

**3. [Rule 3 - Blocking gate] 블록 머리말 주석이 `peak, peak_idx = max_split(` 게이트를 2 로 만듦**
- **Found during:** Task 2 acceptance
- **Issue:** 설명 주석에 원문을 그대로 적어 `grep -c == 1` 게이트가 2 (38-05 의 사이드카 docstring 과 같은 종류).
- **Fix:** 주석을 "max_split 튜플 언패킹(R1)" 으로. 로직 무접촉.
- **Verification:** grep 1, 82 passed.
- **Committed in:** `2b038ace`

---

**Total deviations:** 3 auto-fixed (Rule 2 ×2, Rule 3 ×1)
**Impact on plan:** 뒤 플랜이 쓰는 이름·시그니처는 플랜 그대로(`_register_reference(bucket, key, uid, ref_id, job_id)` · `_handle_reference_upload` 반환 4값 · `_delegate_to_runpod(url=, extra=)` · `probe_duration_sec(path)`). 범위 확장은 헬퍼 3개 + 대조 4줄.

## Issues Encountered

- GREEN 첫 실행 1 failed — 테스트 가짜의 버그였다: `_FakeS3.on_head` 훅이 head 응답을 **만들기 전**에 ETag 를 바꿔 copy 가 정당하게 일치했다. 훅을 응답 생성 뒤로 옮겨 "head 뒤 재PUT" 을 재현(코드 무변경, `2b038ace` 에 포함).
- `test_combo_limit_is_60` 는 한 하네스로 두 번 돌린다(35초 통과 → 65초 거부) — `h.calls["failed"].clear()` 로 두 판정을 가른다.

## Known Stubs

None. `_POD_EXPECTED_PARAM` 은 env 로 덮을 수 있는 기본값이고, `fileName` 문자열은 표시용 값이다(조인 키 아님 — 메모리 display-string-is-not-a-join-key).

## Threat Flags

None — 새 표면(SSM 읽기 · `/health` GET · `/register-reference` POST · `copy_object` 2곳 · Admin writer)은 전부 플랜 `<threat_model>` T-38-07-1~10 안. T-38-07-7 은 위 "진단" 첫 줄대로 **[미확인 — 38-09 T3 (E)/38-14 T2 3-b 가 잰다]**.

## User Setup Required

이 플랜에서는 없음(코드·테스트만). **38-09 가 해야 하는 것(이 플랜 산출물이 전제하는 배선):**
- `template.yaml` PipelineFunction 정책에 `ssm:GetParameter` for `arn:…:parameter/sunity/motion/runpod-pod-expected` 추가(없으면 health 만으로 판정 — 동작은 함).
- 버킷 알림에 `reference/` 접두사 QueueConfiguration(같은 `AnalysisQueue`) 추가 — 없으면 이벤트가 오지 않는다(RESEARCH Pitfall 1).
- Pod 자격증명 `reference/*`·`uploads/*` PutObject 확인(simulate-principal-policy) — 38-14 Pod 세션 probe 와 짝.
- 배포 순서: Pod 코드(38-08 `/register-reference`) → Lambda(이 플랜) → 알림 접두사. 역순이면 등록이 404 로 `failed(server_error)` 된다(위 진단).

## 다음 플랜 주의 (38-08 · 38-09 · 38-14)

- **38-08** — 라우트는 `pipeline_app._register_reference(bucket, key, uid, ref_id, job_id)` 를 BackgroundTasks 로 부르고 `Exception` 하나만 잡아 `set_registration_failed(server_error)`. `no_human` 은 안에서 코드로 매핑됨, stale 은 쓰기 없이 return(예외 아님), 등록 doc 없음/키 형 불일치는 RuntimeError. `_delegate_to_runpod` 의 payload 는 `{"bucket","key","jobId"}` — 라우트 모델 `jobId: str | None` 과 맞다. selfScore 훅의 표식 키는 이 플랜과 같은 `models.ANALYSIS_FIELD_SELF_CHECK_*`.
- **38-09** — 위 "User Setup Required". `_pod_available` 의 SSM 이름은 `runpod-pod-expected`(쓰기 측) — podwatch 스택의 `PodExpectedParam` override 여부와 무관.
- **38-14** — 실물 실패 관측 때 `register-reference verdict … detail=` 로그(no_floor_reference 는 warning) 와 `register-reference ok … split= peak_idx=` 를 볼 것. 문턱 3개(38-05)는 [ASSUMED] — 영상에 맞춰 숫자를 옮기지 말 것.

## Next Phase Readiness

- 입구 분기 + 등록 서비스 + probe 가 pytest 82건(+ 전체 5499)으로 닫혔고, 기존 학생 경로·기준 11개는 diff 상 무접촉(`_process` 호출부 0, `uploads/` 분기 본문 삭제 줄 0).
- 남은 것: 38-08(Pod 라우트·selfScore 훅·requeue) → 38-09(배선·배포 결정 체크포인트). 정은지 새 영상이 오면 이 phase 보다 시험 영상 2차가 먼저(플랜 머리말).

## Self-Check: PASSED

- 파일 5개 존재(`test -f` 전부 FOUND) · 커밋 4건(`b65746da` · `4219aeb5` · `1f12236e` · `2b038ace`) `git log --all` 에 존재 · 플랜 커밋 범위 삭제 파일 0 [확인]
