---
phase: quick-261001-thx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/registration_checks.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/shared/python/sunity_shared/models.py
  - backend/functions/pipeline/app.py
  - backend/functions/playback-url/app.py
  - backend/scripts/review_reference_registrations.py
  - backend/tests/test_registration_checks.py
  - backend/tests/test_register_reference_pipeline.py
  - backend/tests/test_firestore_reference_writers.py
  - backend/tests/test_registration_contract.py
  - backend/tests/test_playback_url_reference.py
  - backend/tests/test_review_reference_registrations_script.py
  - docs/contract.md
  - app/src/types/analysis.ts
  - app/src/constants/supplierCopy.ts
  - app/src/constants/supplierCopy.test.ts
  - app/src/lib/supplierRules.ts
  - app/src/lib/supplierRules.test.ts
  - app/src/lib/supplierFixtures.ts
  - app/src/app/supplier/index.tsx
  - .planning/quick/261001-thx-supplier-intake-phase1a-block-only-unana/261001-thx-DEPLOY.md
autonomous: false
requirements: [QUICK-261001-thx]

must_haves:
  truths:
    - "공급자 등록은 분석 불가(사람 없음 no_human · 포즈 재료 없음 server_error · 파일 문제 too_large/too_short/too_long/복사·ETag·소리 제거 실패 server_error)일 때만 failed 가 된다 — 저신뢰·서 있는 시작·여러 명은 어떤 조합이어도 등록을 막지 않는다 (belle 10-01 결정 1)"
    - "세 진단(person_ratio · 저신뢰 관절 목록 · 서 있는 창 바닥 판정 결과)은 Pod 로그 key=value 와 비공개 reference/{refId}/private/registration 의 registrationDiagnostics 에 남는다"
    - "판정을 통과한 등록은 registrationStatus 'review' + isActive false 로 끝나 수강생 picker 에 안 보이고, 운영 스크립트 approve 뒤에만 active + isActive true 가 된다"
    - "review 상태에서도 자기 재현성 분석이 돌아 selfScore 가 기준 doc 에 기록된다"
    - "공급자 홈 행은 review 를 '검수 중' 쉬운 말로 보여 주고 썸네일이 보인다(본인 소유만), reject 된 등록은 실패 패널에 운영자가 적은 사유를 보여 준다"
    - "운영자는 review_reference_registrations.py list / show / approve / reject 로 검수한다 — legacy ref-* 거부, 반복 실행 무해, --dry-run 은 쓰기 0"
    - "썸네일 순간은 여전히 서 있는 창 가운데 프레임이고 어떤 판정과도 묶이지 않는다 (belle 결정 2)"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/registration_checks.py"
      provides: "diagnose_registration — 진단만 계산, 실패 사유 없음"
      contains: "def diagnose_registration"
    - path: "backend/shared/python/sunity_shared/firestore_admin.py"
      provides: "set_registration_review · approve_reference_registration · reject_reference_registration · begin_self_check(review 허용)"
      contains: "def set_registration_review"
    - path: "backend/shared/python/sunity_shared/models.py"
      provides: "REGISTRATION_STATUS_REVIEW · REG_ERR_REJECTED"
      contains: "REGISTRATION_STATUS_REVIEW"
    - path: "backend/scripts/review_reference_registrations.py"
      provides: "검수 운영 CLI list/show/approve/reject"
      min_lines: 150
    - path: "app/src/constants/supplierCopy.ts"
      provides: "row.status.review · row.fail.rejected 문구 단일 출처"
      contains: "review:"
    - path: ".planning/quick/261001-thx-supplier-intake-phase1a-block-only-unana/261001-thx-DEPLOY.md"
      provides: "롤백 먼저 · 배포 명령 목록 (belle 승인 대기)"
  key_links:
    - from: "backend/functions/pipeline/app.py::_register_reference"
      to: "firestore_admin.set_registration_review"
      via: "판정 통과 뒤 angles 다음 호출 (옛 set_registration_active 자리)"
      pattern: "set_registration_review\\("
    - from: "backend/functions/pipeline/app.py::_trigger_self_check"
      to: "firestore_admin.begin_self_check"
      via: "status ∈ {review, active} 허용"
      pattern: "REGISTRATION_STATUS_REVIEW"
    - from: "backend/scripts/review_reference_registrations.py"
      to: "firestore_admin.approve_reference_registration / reject_reference_registration"
      via: "approve / reject 서브커맨드"
      pattern: "approve_reference_registration|reject_reference_registration"
    - from: "app/src/lib/referenceMotions.ts:79"
      to: "isActive false 숨김"
      via: "변경 없음 — review doc 은 isActive false 라 picker 에서 빠진다"
      pattern: "isActive === false"
---

<objective>
공급자 등록 입구 1단계-가 (belle 2026-10-01 "1단계 오케이"): 등록 판정을 "분석 불가만 막는다" 구조로 바꾸고(저신뢰 · 서 있는 시작 · 여러 명을 한 번에 진단으로 내림 — 하나씩 고치는 수리 금지, belle 원문 "하나씩 고치면 절대 안돼"), 판정을 통과한 등록은 검수 대기(review, 수강생 비노출)로 두며, 운영 스크립트로 승인/반려한다.

Purpose: 38-14 대역 등록이 화분(multiple_people) · 대각선 출발(no_standing_start)로 연달아 거절됐다. 분석에 지장 없는 것을 막는 구조 자체가 문제다. 대신 사람(belle/운영자)이 공개 전에 한 번 본다.
Output: 진단 전용 판정 · review 상태와 승인/반려 writer · 계약 3벌 동기 · 공급자 홈 '검수 중' 문구 · 검수 운영 CLI · 배포 명령서(belle 승인 체크포인트).

범위 밖 (locked 5): Gemini A 동작 정체 · 실행 구간 자동 도출 · 콤보 목록 · /admin 웹(1단계-나) · admin custom claims · 웹 배포 실행. 기존 실패 doc `dc7812c6…` · `fc4a393d…` 와 TESTB 정리는 38-14 Task 4 몫이다 — 이 플랜에서 건드리지 않는다.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
@/Users/kimtaesung/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/supplier-intake-redesign-20261001.md
@/Users/kimtaesung/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/studio-plant-detected-as-person.md
@.planning/phases/38-supplier-link/38-14-E2E.md

## 소비처 추적 (플래너가 코드로 확인, CLAUDE.md §7 ★ — 실행기는 착수 즉시 줄 번호 재대조)

registrationStatus 를 읽거나 쓰는 곳:
- `backend/shared/python/sunity_shared/models.py:815-828` REGISTRATION_* 상수와 REGISTRATION_STATUSES 튜플, `:808-814` 전이 표 주석.
- `firestore_admin.py:4481` `_REGISTRATION_TERMINAL`(정의만, 다른 소비처 0 [확인 grep]) · `:4617-4680` `claim_registration` — registering/queued 화이트리스트 + lease 만료 processing 만 claim [확인] → review 는 claim 불가(중복 S3 이벤트가 review doc 을 다시 돌리지 않는다) · `:4770-4824` `set_registration_active`(processing→active, isActive true) — 파이프라인이 유일한 운영 호출자 · `:4827` `set_registration_failed`(processing 만) · `:4962-4992` `begin_self_check`(**status == active 만** 허용 — review 를 더해야 자기 재현성이 돈다) · `:5111-5130` `list_reference_registrations_by_status`(REGISTRATION_STATUSES 밖이면 ValueError — review 를 더해야 list 가 된다).
- `backend/scripts/requeue_reference_registrations.py:119-127` queued/processing/registering 만 조회 → review 무접촉 [확인].
- `backend/functions/pipeline/app.py:333-362` `_handle_reference_upload` — Lambda 는 queued 또는 Pod 위임만, `_register_reference` 를 직접 돌리지 않는다 [확인] → 등록 동작 변경은 Pod 코드에서만 산다.
- 앱: `app/src/lib/supplierRules.ts:31-38` 상태 목록 · `:115-117` 미지 값 → registering 기본(옛 웹 번들은 review 를 '올린 영상 확인 중' 으로 보인다 — 무해) · `:173-193` `rowStatusWord` switch + `assertNever`(review 를 안 더하면 typecheck 실패) · `:244-250` `hasDetail` · `app/src/app/supplier/index.tsx:119-123` `rowTrailing` · `:272` anyQueued · `:473`/`:492` 실패·만료 패널.

isActive 를 읽거나 쓰는 곳:
- `app/src/lib/referenceMotions.ts:79` picker normalize 가 `isActive === false` 면 null — **변경 없음**, review doc 은 isActive false 라 수강생에게 안 보인다.
- `backend/functions/playback-url/app.py:351-380` `_handle_reference`(영상) · `:383-420` `_handle_reference_thumbnail` — 둘 다 `isActive is not False` 가드 → review 중이면 공급자 홈 썸네일과 공급자 본인 자기 재현성 결과 화면의 기준 영상이 404 가 된다. 호출자 uid 는 `:426` `verify_request(event)` 로 검증된 값.
- `firestore_admin.py:4559` create 때 false · `:4809` active 때 true · `:2365-2443` belle 전용 auto-register(손대지 않음) · `snapshot_reference_baseline.py:68` · `backup_reference_docs.py:166`(legacy 11개 전용, 무접촉).
- 파이프라인 채점 경로는 isActive 를 읽지 않는다 — `grep isActive backend/functions/pipeline/app.py backend/runpod_inference/*.py` 0건 [확인], `get_reference_motion`(`firestore_admin.py:2559`)도 가드 없음 → review 상태 기준으로 자기 재현성 mode1 분석이 그대로 돈다. 막는 것은 `begin_self_check` 의 상태 검사 하나뿐.

서 있는 창을 쓰는 곳:
- `pipeline/app.py:10521` `_stand_frames` → `:10678` `check_registration`(판정) 과 `:10537`/`:10735` `_thumbnail_time_sec`(썸네일). 판정만 진단으로 바꾸고 `_stand_frames` · `_thumbnail_time_sec` 는 그대로 둔다(locked 2).
- `hold_height.py:185` `hold_window_heights` 는 같은 바닥 규칙을 쓰지만 이 플랜과 무관 — 손대지 않는다.

"포즈 추출 불가" 의 정의 (새 휴리스틱 없음, 기존 코드 그대로):
- `NoHumanError`(`pipeline/app.py:10656`, 전 프레임 미검출) → `no_human`.
- 프레임 0 또는 fps 무효(`:10637-10642`) · `build_keypoint_report` 가 None(`:10670-10675`, `assemble.py:929-931` pose_frames 비었거나 keypoints_2d 가 하나도 없음) → `server_error`(기존 코드 유지).
- 이 셋 말고는 막지 않는다. 저신뢰 관절이 전부여도 angles 는 `temporal_fill` 로 계산되므로 막지 않는다(진단에 남는다).
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 백엔드 — 진단 전용 판정 · review 상태 · 승인/반려 writer · 계약 3벌 · 소유자 썸네일 가드</name>
  <files>backend/shared/python/sunity_shared/analysis/registration_checks.py, backend/shared/python/sunity_shared/firestore_admin.py, backend/shared/python/sunity_shared/models.py, backend/functions/pipeline/app.py, backend/functions/playback-url/app.py, docs/contract.md, app/src/types/analysis.ts, backend/tests/test_registration_checks.py, backend/tests/test_register_reference_pipeline.py, backend/tests/test_firestore_reference_writers.py, backend/tests/test_registration_contract.py, backend/tests/test_playback_url_reference.py</files>
  <behavior>
    - diagnose_registration: 저신뢰 관절 + 바닥 위반 + 사람 둘이 동시에 있는 입력도 예외 없이 진단 객체를 돌려주고, 객체에 ok/reason 같은 실패 필드가 없다. person_ratio · low_confidence_joints · stand_material_unreadable · standing_start(ok | floor_violation | no_floor_reference | stand_window_too_short) 를 각각 정확히 싣는다(기존 low_confidence_joints · standing_start_measurable · _standing_start_detail · multiple_people_ratio 결과와 같은 값).
    - 비Mapping report 는 여전히 TypeError(배선 실수 fail-loud 유지).
    - 파이프라인: 저신뢰(발목 conf 0.2) · 바닥 위반 · 사람 둘 각각, 그리고 셋 동시 입력에서 failed 0 · set_registration_review 1회 · begin_self_check 호출 · 로그 `register-reference diagnostics` 에 person_ratio= low_conf= stand_unreadable= standing_start= n_stand= key=value.
    - 파이프라인: NoHumanError → no_human failed, 0 프레임 → server_error, too_large/too_short/too_long 는 기존 그대로 failed(회귀 잠금).
    - 구조 잠금: `_register_reference` 소스(inspect.getsource)와 registration_checks 모듈 소스를 `ast` 로 파싱해 코드 식별자(ast.Name · ast.Attribute · import 이름)에 REG_ERR_LOW_CONFIDENCE · REG_ERR_NO_STANDING_START · REG_ERR_MULTIPLE_PEOPLE 이 없다(docstring · 주석의 이력 언급은 세지 않는다). 동시에 세 상수는 models.REGISTRATION_ERROR_CODES 와 REGISTRATION_ERROR_MESSAGE 에 남아 있다(앱 문구 매핑이 읽는다).
    - set_registration_review: processing ∧ jobId 일치일 때만 공개 doc {registrationStatus 'review', isActive False, videoS3Key, videoETag, thumbnailS3Key?, leaseUntil None} + 비공개 registrationDiagnostics 를 한 트랜잭션에. stale job · processing 아님 → False, doc 무변경. ref-* 는 ValueError.
    - begin_self_check: review 와 active 에서 True, 그 밖(processing · failed)에서 False.
    - approve_reference_registration: review → active + isActive True + 비공개 review{decision 'approved', by, at} → 'approved'. 이미 active 이고 review.decision approved → 'already_approved' 쓰기 0. failed/processing 등 → ValueError. ref-* → ValueError.
    - reject_reference_registration: review → failed + 비공개 registrationError{code 'rejected', message, reason} + review{decision 'rejected', by, at, reason} → 'rejected'. 이미 rejected 로 failed → 'already_rejected' 쓰기 0. active 이면 ValueError(승인 뒤 내리기는 범위 밖). 빈 사유 ValueError.
    - list_reference_registrations_by_status('review') 가 ValueError 없이 돈다.
    - playback-url: review doc 은 호출자 uid == supplierUid 일 때만 썸네일·영상 서명, 다른 uid 는 404. isActive false 이고 review 가 아닌 doc 은 소유자여도 404(기존 가드 유지).
    - 계약 3벌: test_registration_contract 가 'review' 상태와 'rejected' 코드를 models.py · analysis.ts · contract.md 세 곳에서 대조한다.
  </behavior>
  <action>
판정 구조(locked 결정 1, belle 10-01 "하나씩 고치면 절대 안돼"): registration_checks.py 의 `check_registration` 과 `RegistrationVerdict` 를 `diagnose_registration(person_counts, report, *, n_stand) -> RegistrationDiagnostics` 로 바꾼다. RegistrationDiagnostics 는 frozen dataclass 로 person_ratio(float) · low_confidence_joints(tuple, report 순서) · stand_material_unreadable(tuple) · standing_start(str 토큰: 새 상수 STANDING_START_OK = "ok" 또는 기존 DETAIL_* 토큰 셋) · n_stand(int) 를 갖고, `as_log_fields()`(key=value 문자열)와 `as_firestore_dict()`(camelCase 평면 dict: personRatio · lowConfidenceJoints · standMaterialUnreadable · standingStart · nStand — 리스트는 문자열 리스트라 중첩 배열 아님)를 제공한다. 실패 사유 필드는 두지 않는다 — 사유를 낼 수 있는 길 자체를 지운다(세 갈래를 각각 끄는 것이 아니다). 기존 원시 함수(low_confidence_joints · standing_start_measurable · _standing_start_detail · standing_start_ok · multiple_people_ratio · is_multiple_people · default_stand_frames · joint_labels_ko · 상수)는 그대로 재사용하고 문턱 숫자는 바꾸지 않는다. models 의 REG_ERR_LOW_CONFIDENCE · REG_ERR_NO_STANDING_START import 를 지운다. 모듈 docstring 을 "2026-10-01 belle 결정 — 진단만, 등록을 막지 않는다" 절로 고쳐 쓰고(판정 순서 절 · fail-closed 절은 이력 한 줄로 줄인다) 원문 인용을 남긴다. `_require_mapping` TypeError 는 유지.

파이프라인(pipeline/app.py `_register_reference` :10676-10701 블록): `check_registration` 호출과 `if not verdict.ok` 실패 분기를 통째로 `diagnose_registration` 호출로 바꾼다. 진단 로그 한 줄 `register-reference diagnostics ref_id=… <as_log_fields>` 를 info 로, standing_start 가 no_floor_reference 면 기존 경고 로그(파이프라인 버그 신호)를 유지한다. 소리 제거 · 썸네일(`_thumbnail_time_sec(n_stand, …)` 그대로, locked 2) · angles 순서는 그대로. `set_registration_active` 호출 자리를 `set_registration_review(ref_id, job_id, video_s3_key=…, video_etag=…, thumbnail_s3_key=…, diagnostics=diag.as_firestore_dict())` 로 바꾸고, ok 로그 끝의 person_ratio 를 진단 필드로 바꾼다(로그 문구 `register-reference ok` → `register-reference review` 로, 상태가 바뀌었음을 로그가 말하게). `_fmt_ratio` 는 소비처가 없어지면 지운다. 섹션 머리 주석(:10449-10470)과 `_register_reference` · `_trigger_self_check` docstring 의 실패 목록과 "active 뒤" 표현을 review 기준으로 고친다(no_human · too_short · too_long · too_large · server_error 만 남음).

상태와 writer(locked 결정 3, 계약 최소 변경 = registrationStatus 에 'review' 하나 + 실패 코드 'rejected' 하나 + 비공개 doc 필드 둘): models.py 에 REGISTRATION_STATUS_REVIEW = "review" 를 REGISTRATION_STATUSES 에 더하고 전이 표 주석을 `processing → review | failed`, `review → active | failed(반려)`, 종결 = active · failed · expired 로 고친다. REG_ERR_REJECTED = "rejected" 를 REGISTRATION_ERROR_CODES 에 더하고 REGISTRATION_ERROR_MESSAGE[rejected] = "검수에서 반려됐어요. 사유: {reason}. 고쳐서 다시 올려 주세요." (기존 조인 규칙 title + '. ' + body 를 지키게 Task 2 의 supplierCopy 와 같은 글자로; `{reason}` 치환은 str.replace — `{joints}` 와 같은 규율). 저신뢰 · 서 있는 시작 · 여러 명 상수와 문구는 지우지 않는다(앱 문구 매핑 · 옛 doc). firestore_admin.py: `_REGISTRATION_TERMINAL` 에 REVIEW 를 더한다(문서 일관성). `set_registration_active` 를 `set_registration_review` 로 대체한다 — 같은 job 가드(`_guarded_update`) · processing 검사 · 공개 update(registrationStatus review, isActive False 명시, videoS3Key, videoETag, leaseUntil None, registrationUpdatedAt, updatedAt, thumbnailS3Key 선택) + 같은 트랜잭션에서 비공개 doc 에 `{registrationDiagnostics: diagnostics, updatedAt}` merge set(`set_registration_failed` 의 private_ref 패턴 그대로, `_validate_flat_dict_no_nested_array` 통과). `set_registration_active` 는 운영 호출자가 파이프라인 하나뿐이므로 지우고 그 테스트를 새 함수 테스트로 옮긴다(실행기가 grep 으로 다른 호출자 0 을 먼저 확인; 있으면 지우지 말고 SUMMARY 에 적는다). `begin_self_check` 상태 검사를 `status in (REVIEW, ACTIVE)` 로(이것이 자기 재현성의 유일한 상태 의존 — 위 소비처 추적). 새 함수 둘: `approve_reference_registration(ref_id, *, by, now_ms=None) -> str` 과 `reject_reference_registration(ref_id, *, reason, by, now_ms=None) -> str` — 둘 다 첫 줄 `_require_registration_ref_id`(ref-* 거부), 트랜잭션 안에서 공개·비공개 doc 을 먼저 읽고 쓴다(read-before-write 규율), 상태 전이는 behavior 표 그대로, job 가드는 쓰지 않는다(사람 결정이라 jobId 와 무관 — 상태 검사만). approve 는 공개 {registrationStatus active, isActive True, registrationUpdatedAt, updatedAt} + 비공개 {review: {decision, by, at}}; reject 는 공개 {registrationStatus failed, registrationUpdatedAt, updatedAt} + 비공개 {registrationError: {code 'rejected', message(REGISTRATION_ERROR_MESSAGE 치환본), reason}, review: {decision, by, at, reason}}. 로그는 key=value(`approve_reference_registration ok ref_id=… by=…`). 누가/언제는 비공개 doc 에만 둔다(공개 doc 은 인증자 전체가 읽는다, 리뷰 R13 원칙).

계약 3벌 동기(CLAUDE.md Cross-cutting): app/src/types/analysis.ts 의 ReferenceRegistrationStatus 에 'review', ReferenceRegistrationErrorCode 에 'rejected', REGISTRATION_ERROR_MESSAGE 에 같은 글자, ReferenceRegistrationError 에 `reason?: string`(rejected 때 운영자 사유). docs/contract.md §3 의 registrationStatus 줄(:435-440)·전이, registrationError 줄(:477), 비공개 doc 줄(:502)에 registrationDiagnostics · review 필드, §5 REGISTRATION_ERROR_MESSAGE 표(:1079~)에 rejected 행. test_registration_contract.py 가 새 값을 세 벌에서 대조하게 갱신한다.

playback-url(소유자 예외, 플래너 판단 — 아래 output 의 확인 필요 항목): `_handle_reference` 와 `_handle_reference_thumbnail` 의 `isActive is not False` 조건을 "isActive is not False, 또는 (registrationStatus == REVIEW 이고 supplierUid == 호출자 uid)" 로 넓힌다. 다른 가드(키 접두사 · exact 구성 키 비교 · 동일 404 응답)는 그대로. 이유: review 중 공급자 홈 썸네일과 공급자 본인 자기 재현성 결과의 기준 영상이 404 가 되는 회귀를 막되 수강생에게는 계속 안 보이게.

테스트(의미 있는 것만, 숫자 채우기 금지): behavior 목록을 test_registration_checks.py(옛 check_registration 테스트 239-322 를 진단 테스트로 교체, 원시 함수 테스트는 유지) · test_register_reference_pipeline.py(fake harness 의 set_registration_active 를 set_registration_review 로, 실패 기대였던 low_confidence/no_standing_start 테스트를 "review + 진단 로그 + 비공개 진단" 으로 교체, 오디오·썸네일 순서 테스트의 이름 갱신, 소리·썸네일 테스트가 실패 유도에 바닥 위반을 쓰던 곳은 실패 유도를 too_long 이나 no_human 처럼 여전히 막히는 사유로 바꾼다) · test_firestore_reference_writers.py · test_playback_url_reference.py 에 반영한다. 먼저 테스트를 고쳐 실패를 보고(RED) 구현한다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_registration_checks.py tests/test_register_reference_pipeline.py tests/test_firestore_reference_writers.py tests/test_registration_contract.py tests/test_playback_url_reference.py tests/test_requeue_reference_registrations.py -q</automated>
  </verify>
  <done>위 6개 테스트 파일 통과(ast 구조 잠금 포함). app typecheck 는 이 태스크에서 게이트로 쓰지 않는다 — analysis.ts 에 'review' 가 들어가면 supplierRules.rowStatusWord 의 assertNever 가 Task 2 전까지 깨지는 것이 예상 동작이고 Task 2 verify 가 닫는다. 커밋: `feat(261001-thx): registration diagnoses only, review state, approve/reject writers`.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 공급자 홈 '검수 중' · 반려 사유 문구 + 검수 운영 CLI</name>
  <files>app/src/constants/supplierCopy.ts, app/src/constants/supplierCopy.test.ts, app/src/lib/supplierRules.ts, app/src/lib/supplierRules.test.ts, app/src/lib/supplierFixtures.ts, app/src/app/supplier/index.tsx, backend/scripts/review_reference_registrations.py, backend/tests/test_review_reference_registrations_script.py</files>
  <behavior>
    - normalizeRegistration 이 registrationStatus 'review' 를 그대로 보존(registering 으로 떨어지지 않음).
    - rowStatusWord(review) = supplierCopy.row.status.review, hasDetail(review) = false, rowTrailing(review) = 'progress'.
    - 비공개 정규화가 registrationError.reason(문자열)을 보존, 문자열 아니면 버린다.
    - failCopy('rejected', undefined, '화면이 어두워요') 의 본문에 사유가 들어가고 `{reason}` 리터럴이 남지 않는다. 사유가 없으면 '사유: ' 줄 없이 자연스러운 문장(아래 문구 규칙).
    - supplierCopy.test 조인 규칙: rejected 의 title + '. ' + body == REGISTRATION_ERROR_MESSAGE.rejected(analysis.ts) 글자 단위.
    - CLI list: review 상태만, 열 = refId 앞 8자 · supplierCode · name · athleteName · level · selfScore(없으면 selfCheckStatus) · 진단 요약(personRatio · 저신뢰 관절 수와 이름 · standingStart). 0건이면 "검수 대기 0건".
    - CLI show <refId>: thumbnailS3Key 와 videoS3Key(v1)를 --out 폴더(기본 /Users/Shared/sunity-motion-review/<refId>/, 권한 700)에 내려받고, anglesFrames/anglesRealFps 로 구한 길이의 10% · 50% · 90% 순간 프레임 3장을 jpg 로 뽑아 경로 5줄(thumb · video · frame 3)을 출력. 썸네일 키가 없으면 그 줄은 '없음' 이고 나머지는 계속.
    - CLI approve <refId> [--by] [--dry-run] · reject <refId> --reason "<한국어>" [--by] [--dry-run]: firestore_admin 함수 결과를 출력('approved' / 'already_approved' / 'rejected' / 'already_rejected'), ValueError 는 stderr + 종료 1, ref-* · 빈 사유 · 200자 초과 사유는 Firestore 호출 전에 종료 2. --dry-run 은 현재 상태와 바뀔 상태만 출력하고 writer 호출 0.
    - --help 는 자격 없이 돈다.
  </behavior>
  <action>
앱 문구(locked 결정 3 — 문구는 supplierCopy.ts 단일 출처, 하드코딩 금지): supplierCopy.row.status 에 `review: '검수 중 · 확인 뒤 수강생에게 보여요'` 를, supplierCopy.row.fail 에 `rejected: { title: '검수에서 반려됐어요', body: '사유: {reason}. 고쳐서 다시 올려 주세요.' }` 를 더한다(Task 1 의 REGISTRATION_ERROR_MESSAGE[rejected] 와 조인 규칙으로 글자 단위 일치). 사유 없는 rejected(데이터 이상)는 failCopy 가 '사유: {reason}. ' 조각을 빼서 '고쳐서 다시 올려 주세요.' 만 남긴다 — 규칙은 supplierRules.failCopy 안에서 문자열 치환으로만(JSX 해석 금지, 파일 머리 주석 규율). supplierRules.ts: REGISTRATION_STATUSES 에 'review', rowStatusWord switch 에 review 분기, 비공개 정규화(:134-146)에 reason 보존, failCopy 에 세 번째 인자 reason. supplier/index.tsx: rowTrailing 에 review → 'progress', 실패 패널 호출(:478)에 `err?.reason` 전달. supplierFixtures 에 review 행 하나(isActive false, selfScore 있음). 화면 구조·스타일은 바꾸지 않는다(design.md 토큰 그대로). node 테스트를 먼저 고쳐 RED 확인 후 구현.

운영 CLI(locked 결정 4): backend/scripts/review_reference_registrations.py 를 supplier_invite.py 형식 그대로 만든다 — 모듈 docstring 에 서브커맨드 표 · 자격(FIREBASE_SA_PATH 는 리포 루트 SA 파일 자동, S3 는 셸 AWS_PROFILE=sunity-motion) · 종료 코드(0 성공 · 1 Firestore 거부 · 2 입력 규칙 위반), `_REPO`/`_LAYER` sys.path 삽입, `_ensure_credentials()` 를 서브커맨드 실행 안에서만, argparse 서브파서 list/show/approve/reject, `main(argv) -> int`. list 는 `firestore_admin.list_reference_registrations_by_status(models.REGISTRATION_STATUS_REVIEW)` 후 건마다 `get_reference_registration_private` 로 registrationDiagnostics 를 읽는다(읽기 = 2N, Spark 캡 메모리). show 는 boto3 s3 download_file 로 두 객체를 받고 `sunity_shared.analysis.reference_media.extract_thumbnail(src, t_sec, dst)` 를 세 순간에 부른다(로컬 ffmpeg = imageio_ffmpeg, backend/.venv 에 있음 [확인]). 내려받기 폴더는 홈 디렉터리 밖 기본값(메모리 home-dir-is-git-repo-pii-hazard — 정은지 영상 = 초상) 이고 --out 으로 바꿀 수 있다. approve/reject 의 --by 기본값 = "ops:" + getpass.getuser(). reject 사유는 앞뒤 공백과 끝 마침표를 떼고 검사(빈 값 · 200자 초과 → 2). legacy `ref-` 접두사는 입력 단계에서 종료 2(writer 의 ValueError 이전에). 반복 실행 무해는 writer 의 already_* 반환으로. 테스트는 test_supplier_invite_script.py 패턴(firestore_admin · boto3 · reference_media 를 monkeypatch, 실제 Firestore/S3 0)으로 behavior 를 덮는다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && node --test src/lib/*.test.ts src/constants/*.test.ts && npm run typecheck && cd ../backend && .venv/bin/python -m pytest tests/test_review_reference_registrations_script.py tests/test_supplier_invite_script.py -q && .venv/bin/python scripts/review_reference_registrations.py --help >/dev/null && .venv/bin/python -m pytest tests -q -p no:cacheprovider 2>&1 | tail -3</automated>
  </verify>
  <done>node 테스트 전부 통과(기준 82 + 새 테스트, 0 fail) · typecheck 0 · CLI 테스트 통과 · --help 자격 없이 0 · backend 전체 pytest 실패 0 (기준 5758 passed / 20 skipped 에서 늘거나 준 수와 이유를 SUMMARY 에 적는다). 웹 번들 빌드 `CI=1 npx expo export --platform web --output-dir <scratchpad>/thx-web` 성공만 확인(배포는 Task 3). 커밋: `feat(261001-thx): supplier review row copy, rejected reason, review ops CLI`. 두 커밋 뒤 `git push origin main`(rtk 접두 없이) — push 는 배포가 아니다(Pod 는 꺼져 있고 git reset 은 Task 3 승인 뒤).</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: 배포 명령서 — belle 승인 전 실행 금지</name>
  <files>.planning/quick/261001-thx-supplier-intake-phase1a-block-only-unana/261001-thx-DEPLOY.md</files>
  <action>
배포는 하지 않는다(locked 5). 260930-w9l-DEPLOY.md 형식으로 DEPLOY.md 를 만들고 멈춘다. 먼저 '## 롤백' 절: 보존 폴더 /Users/Shared/sunity-motion-rollback/thx/(700)에 playback-url 의 get-function(CodeSha256 · Layers ARN)과 현재 코드 zip, 현재 layer 번호(:23 예상 — 실측값), 웹 버킷 전체 web-before/ sync 를 **준비 명령으로 적고**, 롤백 명령(update-function-configuration --layers 옛 ARN · update-function-code 옛 zip · 웹 sync --delete + 무효화)을 적는다. 그다음 '## 배포 (belle 승인 대기)' 절에 순서대로 정확한 명령: (1) layer — :23 zip 복사본 + 바뀐 파일(models.py · firestore_admin.py · analysis/registration_checks.py)만 덮어쓴 새 zip, `aws lambda publish-layer-version --layer-name sunity-motion-pilot-shared …` (AWS_PROFILE=sunity-motion), 풀어서 리포 HEAD 와 cmp 결과를 표로(이 비교는 로컬이라 지금 실행해도 된다 — 업로드만 하지 않는다); (2) playback-url — 새 layer 붙이기 + 코드 zip(app.py 만 교체) + Docker 스모크(`public.ecr.aws/sam/build-python3.12:latest-arm64`, 무토큰 401) 결과; (3) reference-upload-url — 새 layer 를 붙일지(코드 변경 없음, models 일치 목적) belle 선택으로 표시; (4) pipeline Lambda — 등록을 직접 돌리지 않으므로(`pipeline/app.py:333-362` queued 또는 위임) 배포 불필요라고 근거와 함께 적는다; (5) Pod — 지금 꺼져 있음, 38-14 재개 때 `git fetch origin -q && git reset --hard origin/main -q` 후 start_server.sh 재기동, `/health` commitSha == push 한 HEAD 확인(38-14-E2E 재배포 절 절차 그대로); (6) 웹 — `cd app && rm -rf dist && CI=1 npx expo export --platform web --output-dir dist` · `aws s3 sync app/dist s3://sunity-motion-pilot-supplier-web --delete --only-show-errors` · `aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"`; (7) OTA — 수강생 앱 동작 변화 없음(picker 는 isActive false 를 이미 숨김) 이므로 불필요, 단 iOS 앱 안에서 /supplier 라우트가 도달 가능한지 실행기가 확인해 적는다. 끝에 '## 배포 뒤 확인' : review 상태 doc 이 없으므로 라이브 확인은 38-14 Task 3 재시도에서 한다 — 대역 재업로드 → 공급자 홈 '검수 중' → `review_reference_registrations.py list` → `show` 로 사진 → belle OK → `approve` → picker 노출 → mode1. 기존 실패 doc dc7812c6… · fc4a393d… 와 TESTB 정리는 38-14 Task 4.
  </action>
  <what-built>Task 1·2 코드(진단 전용 판정 · review 상태 · 승인/반려 · 공급자 문구 · 검수 CLI)가 커밋·push 됐고, 배포 명령서와 롤백 명령이 준비됐다. 라이브는 아무것도 바뀌지 않았다.</what-built>
  <how-to-verify>
    1. DEPLOY.md '## 롤백' 이 '## 배포' 보다 위에 있고 보존 폴더 경로가 홈 디렉터리 밖인지 본다.
    2. layer zip cmp 표에서 바뀐 파일이 정확히 3개(models · firestore_admin · registration_checks)인지 본다.
    3. 배포 단계 (1)(2)(6) 를 승인하는지, (3) reference-upload-url layer 를 붙일지 고른다.
    4. Pod 코드는 38-14 재개 때 올라간다는 점을 확인한다.
  </how-to-verify>
  <verify>
    <automated>test -f /Users/kimtaesung/Dev/SunityMotion/.planning/quick/261001-thx-supplier-intake-phase1a-block-only-unana/261001-thx-DEPLOY.md && grep -n "## 롤백" /Users/kimtaesung/Dev/SunityMotion/.planning/quick/261001-thx-supplier-intake-phase1a-block-only-unana/261001-thx-DEPLOY.md</automated>
  </verify>
  <done>DEPLOY.md 존재 · 롤백 절이 배포 절보다 앞 · 실행된 배포 0 · belle 응답 대기.</done>
  <resume-signal>"배포 승인" (선택한 단계 번호와 함께) 또는 고칠 점</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 공급자 웹 → S3/Pod 등록 | 공급자가 올린 영상이 기계 판정만 거쳐 기준 doc 이 된다 — 이제 막는 범위가 좁아졌다 |
| 기준 doc → 수강생 picker | 공개 doc 은 인증자 전체 읽기, picker 는 isActive 로만 거른다 |
| 운영자 로컬 → Firestore Admin | 승인/반려는 Admin SA 를 가진 로컬 CLI 만 할 수 있다 |
| 앱 → playback-url | 서명 URL 발급 경계, 호출자 uid 는 ID 토큰 검증값 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-thx-01 | Elevation | 미승인 기준이 수강생에게 노출 | mitigate | set_registration_review 가 isActive False 를 명시 기록, approve 만 True 로; 클라이언트 쓰기는 firestore.rules `allow write: if false`; picker `referenceMotions.ts:79` 무변경; 테스트가 review 쓰기의 isActive False 를 잠근다 |
| T-thx-02 | Information disclosure | playback-url 소유자 예외 | mitigate | review 예외는 registrationStatus == review ∧ supplierUid == verify_request uid 둘 다일 때만, 다른 uid 는 같은 404; 기존 키 접두사 · exact 구성 키 가드 유지; 테스트로 타 uid 404 잠금 |
| T-thx-03 | Spoofing | 승인/반려 주체 | accept | 서버 API 없음 — Admin SA 파일을 가진 로컬 CLI 만. /admin 웹 · custom claims 는 1단계-나 |
| T-thx-04 | Repudiation | 승인/반려 기록 | mitigate | 비공개 doc review{decision, by, at, reason} + key=value 로그 |
| T-thx-05 | Tampering | 학생이 자기 분석 doc 에 review refId 를 넣어 mode1 | accept | 기존 inactive doc 과 같은 노출(각도 비교만, 영상 서명은 T-thx-02 가드로 404); 파일럿 범위 |
| T-thx-06 | Denial of service | 진짜 두 사람 · 저품질 영상도 review 까지 간다 | accept | belle 결정(막기 = 분석 불가만) — 사람 검수가 공개 전 관문, 진단 3종이 list/show 에 보인다 |
| T-thx-07 | Tampering | legacy ref-* 11개 덮어쓰기 | mitigate | approve/reject writer 첫 줄 `_require_registration_ref_id` + CLI 입력 단계 종료 2 |
| T-thx-08 | Information disclosure | show 가 내려받는 정은지 영상(초상) | mitigate | 기본 폴더 /Users/Shared/sunity-motion-review/<refId>/ 권한 700, 홈 디렉터리(git) 밖 |
</threat_model>

<verification>
- backend 전체 `cd backend && .venv/bin/python -m pytest tests -q` 실패 0 (기준 5758 passed / 20 skipped, 증감 이유 기록).
- app `npm run typecheck` 0 · `node --test src/lib/*.test.ts src/constants/*.test.ts` 0 fail (기준 82).
- ast 구조 잠금 테스트 통과(`_register_reference` · registration_checks 코드 식별자에 세 실패 상수 0), `models.py` 에는 세 상수와 문구가 남아 있다.
- 계약 3벌: 'review' · 'rejected' 가 models.py · app/src/types/analysis.ts · docs/contract.md 에 모두 있다(test_registration_contract).
- 보고 규칙(CLAUDE.md §7): SUMMARY 의 관측(코드 사실 · 테스트 결과)과 진단(예: "실영상에서 review 까지 간다")을 다른 절에, 라이브 미검증은 [미확인 — 38-14 Task 3 재시도].
</verification>

<success_criteria>
- 저신뢰 · 서 있는 시작 · 여러 명 어느 조합도 등록을 failed 로 만들지 않고, 세 진단이 로그와 비공개 doc 에 남는다.
- 판정 통과 등록은 review(isActive false)로 끝나 수강생에게 안 보이고, 자기 재현성 selfScore 는 review 중에도 기록된다.
- 공급자 홈에 '검수 중' 행, 반려 시 운영자 사유가 실패 패널에 보인다.
- review_reference_registrations.py list/show/approve/reject 가 테스트로 덮였고 ref-* · 빈 사유 · dry-run 규칙을 지킨다.
- 배포 0, DEPLOY.md 가 belle 승인을 기다린다.
</success_criteria>

<output>
Create `.planning/quick/261001-thx-supplier-intake-phase1a-block-only-unana/261001-thx-SUMMARY.md` when done (관측 / 진단 분리, 소비처 file:line 재대조 결과, 테스트 수 증감, 38-14 재개 순서 변화: 대역 재업로드 → review → show 사진 → belle OK → approve → picker).
</output>
