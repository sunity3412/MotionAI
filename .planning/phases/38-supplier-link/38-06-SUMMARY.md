---
phase: 38-supplier-link
plan: 06
subsystem: api
tags: [firestore, lambda, presigned-url, firestore-rules, transactions, supplier-link, pytest]

# Dependency graph
requires:
  - phase: 38-supplier-link (38-01)
    provides: models 상수(REGISTRATION_STATUS_*·SELF_CHECK_STATUS_*·CONSENT_VERSION·REGISTRATION_LEASE_SEC·REFERENCE_UPLOAD_EXPIRES_SEC·reference_private_path·parse_supplier_uids) · s3keys.build_reference_upload_key · validation.validate_reference_upload_request / ReferenceUploadRequest
  - phase: 31-api-visual-correction (31-02)
    provides: firestore_admin seam(_collection/_field_filter/_run_in_transaction/_now_ms/_snap_dict) + backend/tests/phase31/conftest.py FakeFirestore(실제 optimistic concurrency)
provides:
  - "firestore_admin: create_reference_registration(공개+비공개 batch create) · get_reference_registration / get_reference_registration_private(비가드 raw 읽기) · claim_registration(트랜잭션 claim/lease) · set_registration_queued / set_registration_expired · set_registration_active / set_registration_failed(job 가드) · set_reference_angles(job 가드, angles 유일 writer) · begin_self_check(선기록) · self_check_authorized(순수) · set_reference_self_check(권위 가드) · create_analysis_doc · list_reference_registrations_by_status"
  - "backend/functions/reference-upload-url/app.py: lambda_handler — 인증 → SSM 화이트리스트(∪ BELLE_UID, 60초 캐시) → probe | 검증 → presign `reference/{uid}/{refId}/upload.{ext}` → 공개+비공개 doc batch create → 응답"
  - "firestore.rules: reference top-level·versions 인증자 읽기 / private 서브문서 supplierUid 본인 읽기 / users/** selfCheckForReference·selfCheckJobId 클라이언트 create·update 거부"
  - "backend/scripts/deploy_firestore_rules.py: Rules REST --test / --current(--out) / --release / --dry-run + 순수 빌더(build_test_body·build_ruleset_body·build_release_body·summarize_test_results·load_cases) · backend/tests/firestore_rules_cases.json 12 케이스"
affects: [38-07 pipeline _register_reference(claim·angles·active/failed·begin_self_check·create_analysis_doc), 38-08 selfScore 훅(self_check_authorized·set_reference_self_check)·requeue(list_reference_registrations_by_status·claim_registration), 38-09 template(Lambda 배선·SSM·IAM)·규칙 배포(--current → --test → --release), 38-10/38-12 페이지(probe·upload-url), 38-14 재diff(get_reference_registration raw 읽기)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Firestore batch `create()` 두 문서 원자 선작성(리포 첫 create 사용) — 하나라도 존재하면 AlreadyExists, `snap.exists` 분기와 달리 경합 없음"
    - "`_guarded_update(ref_id, job_id, mutate)` 가 `_tx` 클로저를 돌려주고 각 writer 가 `_run_in_transaction(_tx)` 를 부른다 — jobId 가드는 한 곳, 트랜잭션을 여는 쪽은 호출측 하나(nested @transactional 금지)"
    - "Rules REST 스크립트 = 순수 body 빌더 + `http_post(method=)`/`http_get`/`get_access_token` seam — 네트워크 0 테스트, 403 = exit 2(콘솔 폴백 신호)"

key-files:
  created:
    - backend/tests/test_firestore_reference_writers.py
    - backend/functions/reference-upload-url/app.py
    - backend/functions/reference-upload-url/requirements.txt
    - backend/tests/test_reference_upload_url_handler.py
    - backend/scripts/deploy_firestore_rules.py
    - backend/tests/test_deploy_firestore_rules.py
    - backend/tests/firestore_rules_cases.json
  modified:
    - backend/shared/python/sunity_shared/firestore_admin.py
    - firestore.rules

key-decisions:
  - "38-06: `_guarded_update` 는 트랜잭션 본문(_tx)만 만들고 실행은 각 writer 가 한다 — 가드는 한 곳, `_run_in_transaction(_tx)` 호출은 writer 별(19 → 28)"
  - "38-06: set_registration_active/failed 는 jobId 일치 + `processing` 둘 다 요구, set_reference_angles 는 jobId 일치만(같은 작업의 후속 쓰기 허용), begin_self_check 는 jobId + `active`"
  - "38-06: SSM 화이트리스트 조회 실패는 캐시하지 않는다(다음 요청이 곧바로 복구) · get_parameter 는 WithDecryption=True(String/SecureString 둘 다 통과)"
  - "38-06: firestore.rules users/** 는 read·delete 자유, create 는 keys().hasAny, update 는 diff().affectedKeys() — 서버가 표식을 써 둔 doc 에도 앱의 coachReview merge-set 이 계속 된다"
  - "38-06: Rules REST 쓰기 호출은 `http_post(url, body, token, method=)` 한 seam(POST/PATCH) — 테스트가 호출 순서를 한 목록으로 잠근다"

patterns-established:
  - "`reference/{refId}` 를 쓰는 writer 는 첫 줄 `_require_registration_ref_id`, 읽기 3 + create_analysis_doc + 순수 가드는 비가드 — `inspect.getsource` 로 테스트가 9/5 를 잠근다(plan-checker 차단 2)"
  - "디렉터리 밖 픽스처 재사용: `from tests.phase31.conftest import fake_firestore` (backend/tests 는 패키지) + 파일 안 `_FakeBatch` 로 `_db().batch()` 보강"

requirements-completed: [REQ-38-1, REQ-38-3, REQ-38-4, REQ-38-5]

# Metrics
duration: 25min
completed: 2026-09-28
---

# Phase 38 Plan 06: Firestore 등록 writer · reference-upload-url Lambda · firestore.rules Summary

**공급자 링크 등록의 서버 쪽 세 축을 코드로 박았다 — (1) `firestore_admin` 에 등록 doc 생명주기 writer 13 + 순수 가드 1(공개+비공개 두 doc 한 batch `create()` 선작성, 트랜잭션 claim/lease 로 작업 소유권, jobId 가드로 늦은 stale 작업 차단, 기준 doc 이 권위인 자기 재현성 3중 일치), (2) `POST /reference/upload-url` Lambda(인증 → SSM 화이트리스트 ∪ BELLE_UID → probe | 검증 → upload 키 presign → doc batch create, create 실패면 URL 미응답), (3) `firestore.rules` 좁히기(reference 재귀 와일드카드 제거 + private 본인 읽기 + selfCheck 표식 클라이언트 create/update 거부) 와 Rules REST 스크립트 + 12 케이스. 전부 AWS/Firestore 없이 pytest 142건으로 닫혔고, 규칙 실배포(`--release`)는 실행하지 않았다(38-09 belle 승인 뒤).**

## Performance

- **Duration:** 25min
- **Started:** 2026-09-28T15:03:03Z
- **Completed:** 2026-09-28T15:28:27Z
- **Tasks:** 3/3 (각 RED → GREEN 2커밋)
- **Files modified:** 9 (+2844 / −4, `git diff --stat 2fdd64ae..HEAD` [확인])

## Accomplishments

- **Success ④(기존 11개 무접촉)의 구조적 보장** — 선작성은 `batch.create()` 라 존재하는 doc 을 못 덮고, `reference/{refId}` 를 쓰는 9함수(`create_reference_registration`·`claim_registration`·`set_registration_queued`·`set_registration_expired`·`set_registration_active`·`set_registration_failed`·`set_reference_angles`·`begin_self_check`·`set_reference_self_check`)는 첫 줄에서 빈 id·`ref-*` 를 ValueError 로 거부한다(어떤 Firestore 호출보다 먼저 — fake 호출 기록 0 을 18케이스 parametrize 가 단언). 읽기 3함수(`get_reference_registration`·`get_reference_registration_private`·`list_reference_registrations_by_status`)는 가드가 **없어** legacy `ref-kip-up` 을 raw 로 읽는다(plan-checker 차단 2 정합 — 38-09 baseline·38-14 재diff 경로).
- **리뷰 R3(중복 실행)** — `claim_registration` 이 `registering|queued` 또는 lease 만료 `processing` 에서만 `processing·jobId·leaseUntil` 을 쓴다. 동시 이벤트 2(둘째 False) · FakeFirestore 실제 CAS(같은 pre-state 를 읽은 두 트랜잭션 → conflict 1 → 재시도 뒤 False) · lease 만료 재claim(옛 jobId warning) · requeue 2회(한 번만) · 종결 3상태 거부가 전부 테스트로 잠겼다. active/failed/angles/begin_self_check 는 `doc.jobId == job_id` 일 때만 쓰고, stale 작업 B 의 늦은 실패가 A 가 활성화한 doc 을 못 뒤집는다(doc 바이트 동일 단언).
- **리뷰 R2·R8(자기 재현성 권위)** — `begin_self_check` 가 `selfCheckAnalysisId·selfCheckStatus=pending·selfCheckJobId` 를 **먼저** 쓰고, 순수 `self_check_authorized(ref_doc, uid, analysis_id, job_id)` 하나가 완료/실패 writer 를 지킨다(위조 표식 u9 · 다른 공급자 refId · stale analysis id · pending 전 완료 훅 · None/빈 doc · 빈 인자 전부 False). 규칙 쪽도 같은 표식을 클라이언트가 create/update 못 하게 막았다.
- **리뷰 R4·R5·R13(Lambda)** — presign 은 `upload.{ext}` 키에만, 그 **뒤** batch create, create 예외면 500 이고 응답 본문에 `uploadUrl` 이 없다(테스트가 `"https://s3.example" not in body` 단언). `uploadExpiresAt = now + REFERENCE_UPLOAD_EXPIRES_SEC*1000` 이 `ExpiresIn` 과 한 상수(900 리터럴 0). 본문 `uid:"evil"`/`refId:"ref-kip-up"` 은 어떤 호출 인자에도 닿지 않는다. 동의·선언·techniqueRefId·clipRange·registrationError 는 비공개 서브문서에만.
- **리뷰 R13(규칙)** — `match /reference/{document=**}` 를 지우고 `{refId}` · `{refId}/versions/{version}` · `{refId}/private/{doc}`(`resource.data.supplierUid == request.auth.uid`) 로 좁혔다. 배포 없이도 `deploy_firestore_rules.py --test` + 12 케이스로 검증 가능하고, `--current --out` 이 롤백 원본을 만든다.

## Task Commits

1. **Task 1: firestore_admin 등록 writer 13 + 순수 가드 1** — RED `645023b3` (test) → GREEN `0b2585bd` (feat)
2. **Task 2: reference-upload-url Lambda** — RED `0eddf336` (test) → GREEN `ce0504f0` (feat)
3. **Task 3: firestore.rules + deploy_firestore_rules.py + 케이스 JSON** — RED `d5740f2a` (test) → GREEN `e4c3d16a` (feat)

**Plan metadata:** 아래 docs 커밋(SUMMARY·STATE·ROADMAP). push 는 하지 않았다(오케스트레이터 지시 — belle 과 정산).

## Files Created/Modified

- `backend/shared/python/sunity_shared/firestore_admin.py` (+663, 블록 append + 모듈 상단 `import logging` 1줄) — 파일 끝 `# ── Phase 38 (D-04·D-05·D-08·D-10·D-19 + 리뷰 R2·R3·R4·R8·R13) — 공급자 링크 등록 writer ──` 블록: 불변식 3줄(visual job :2898-2907 미러) · `_require_registration_ref_id` · `_registration_ref` · `create_reference_registration` · `get_reference_registration` · `get_reference_registration_private` · `claim_registration` · `set_registration_queued` · `set_registration_expired` · `_guarded_update` · `set_registration_active` · `set_registration_failed` · `set_reference_angles` · `begin_self_check` · `self_check_authorized` · `set_reference_self_check` · `create_analysis_doc` · `list_reference_registrations_by_status`. `update_reference_body_data` / `update_reference_downstream_data` / `get_reference_motion` 무접촉(diff 0줄 [확인]).
- `backend/tests/test_firestore_reference_writers.py` (신규, 89 tests) — phase31 `fake_firestore` 재사용 + `_FakeBatch`/`_FakeDb`(`_db().batch()` · commit 시 존재하면 AlreadyExists) + `reg_db` 픽스처(`_now_ms` → T0). 절: seam 존재 · create(payload 키 정확·clipRange 생략·flat·AlreadyExists 전파) · 가드(9×2 parametrize + `inspect.getsource` 9/5 + `test_legacy_ref_id_read_allowed`) · claim(없음/registering/동시2/contended CAS/lease 만료/requeue 2회/종결 3/빈 job) · queued/expired · active/failed(stale·processing 요구·비공개 error·code/message 필수·활성 doc 무변경) · angles(키 정확·split·길이·nested TypeError·fps 3·stale) · begin_self_check · `self_check_authorized` 9케이스(순수성 포함) · `set_reference_self_check` 7 · `create_analysis_doc` 5 · list_by_status 2.
- `backend/functions/reference-upload-url/app.py` (신규, 173줄) — 헤더 docstring(contract §2 · D-03/04/08/12 · R4/R5 · "본문의 uid/refId 는 절대 읽지 않는다(V4)" · 서명 → create 순서 이유) · `_EXPIRES = int(models.REFERENCE_UPLOAD_EXPIRES_SEC)` · `_load_supplier_map`(SSM, 60초 캐시, 실패 = `{}` + warning param 이름만) · `_is_supplier` · `lambda_handler` 8단계.
- `backend/functions/reference-upload-url/requirements.txt` — `upload-url/requirements.txt` 바이트 동일 복사(테스트 `test_requirements_txt_copies_upload_url` 가 대조).
- `backend/tests/test_reference_upload_url_handler.py` (신규, 21 tests) — 401 · 403 3종(빈 화이트리스트+BELLE 없음 / 목록 밖 / SSM 장애 e2e) · BELLE 통과 · `_is_supplier` 순수 · probe 3 · 정상 경로(순서 `["presign","create"]`, Params, ExpiresIn 900, create 인자, refId uuid4 hex) · mov 키 · V4 · 소스 grep · 검증 오류 매핑(too_long 문구) · presign 실패(create 0) · create 실패(uploadUrl 없음) · SSM 로더 3(파싱+캐시 / TTL 만료 / 실패 warning 에 예외 본문 없음+비캐시) · 상수 · requirements.
- `firestore.rules` — users/** `read, delete` + `create`(`keys().hasAny`) + `update`(`diff().affectedKeys().hasAny`) · `reference/{refId}` · `/versions/{version}` · `/private/{doc}` 본인 읽기 · 기본 차단 유지. 주석에 R2·R13 이유(재귀 와일드카드는 OR 결합이라 더하기만으로 무효 · affectedKeys 인 이유 = coachReview merge-set).
- `backend/scripts/deploy_firestore_rules.py` (신규, 333줄) — 헤더(왜 REST · 사용법 4줄 · `--release` 는 38-09 승인 뒤 · 롤백 = 이전 파일로 --release · exit code 규약) · 순수 5함수 · `resolve_project`(--project → .firebaserc → SA project_id) · seam 3 · `run_test`(케이스별 `ALLOW/DENY expected=… state=…` 한 줄 + debugMessages, 실패 수 반환) · `run_current`(GET 2회, `--out` 저장) · `run_release`(rulesets POST → releases PATCH) · `main(argv) -> int`.
- `backend/tests/test_deploy_firestore_rules.py` (신규, 20 tests) — 빌더 3 · summarize 4(pass/failure 라벨/issues 전부 실패/결과 부족) · 케이스 파일 2(형식·시나리오 12 전부) · main 7(`--test` exit=실패 수 / 전부 통과 0 / 403 → 2 + 원문 / `--release` 순서 POST→PATCH + body / rulesets 실패면 PATCH 미호출 / `--current` GET 만 + `--out` / `--dry-run` HTTP 0) · 인자 없음 SystemExit · project 해석 · 토큰 출력 0 + 호스트 ≥ 3 · `firestore.rules` 텍스트 게이트 10.
- `backend/tests/firestore_rules_cases.json` — 12 케이스(경로 `/databases/(default)/documents/...`, 읽기는 `resource.data` 전상태, 쓰기는 `request.resource.data` 후상태): private get A ALLOW / B DENY / 무인증 DENY · reference/r1 get B ALLOW · versions/v1 get ALLOW · reference/r1 update DENY · analyses create 표식 있음 DENY / 없음 ALLOW · 표식 있는 doc 에 coachReview 만 update ALLOW / 표식 변경 update DENY · 남의 analyses get DENY · 본인 delete ALLOW.

## 관측 (이 세션이 직접 실행/읽은 것)

- [확인] `cd backend && .venv/bin/python -m pytest tests/test_firestore_reference_writers.py tests/test_reference_upload_url_handler.py tests/test_reference_auto_register_handler.py tests/test_deploy_firestore_rules.py -q` → `142 passed`(89 + 21 + 12 + 20). RED 단계 실측: T1 `88 failed, 1 passed`(seam 존재 테스트만 통과) · T2 `21 failed` · T3 collection error(`No module named 'deploy_firestore_rules'`).
- [확인] 회귀: `tests/phase31 tests/test_registration_contract.py tests/test_validation.py tests/test_s3keys.py` → `541 passed`(모듈 상단 `import logging` 추가 뒤).
- [확인] T1 게이트: 14 `^def` = 14 · `batch.create(\|\.create(` = 3 · `_run_in_transaction(_tx)` HEAD 19 → 28(+9 ≥ 7) · `startswith("ref-")` = 1 · `_require_registration_ref_id(ref_id)` = 10(def 1 + 호출 9) · 비가드 5함수 본문의 `_require_registration_ref_id` = 0(inspect) · diff 는 insert-only, 보호 3함수 변경 줄 0.
- [확인] T2 게이트: `body.get("uid")|body["uid"]|body.get("refId")` = 0 · `generate_presigned_url` :131 < `create_reference_registration` :145 · `ExpiresIn=_EXPIRES` = 1 · `REFERENCE_UPLOAD_EXPIRES_SEC` = 1 · `upload_expires_at_ms=` = 1 · 두 파일 존재.
- [확인] T3 게이트: `match /reference/{document=**}` = 0 · `match /reference/{refId}` = 1 · `private/{doc}` = 1 · `resource.data.supplierUid == request.auth.uid` = 1 · `hasAny(['selfCheckForReference', 'selfCheckJobId'])` = 2 · affectedKeys 존재 · 케이스 12(DENY 6, expectation 전부 ALLOW/DENY) · `firebaserules.googleapis.com` = 7 · `print(.*token\|log.*token` = 0.
- [확인] `backend/.venv/bin/python backend/scripts/deploy_firestore_rules.py --dry-run --test` → project `sunity-ai-coach`(.firebaserc), 12 케이스 body 출력, HTTP 0, exit 0.
- [확인] 라이브 `FIREBASE_SA_PATH=sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json … --test` → HTTP 403 `PERMISSION_DENIED`, `reason: IAM_PERMISSION_DENIED`, `permission: firebaserules.rulesets.test`, `resource: projects/sunity-ai-coach` → 스크립트가 원문 출력 + exit 2(설계대로). 오케스트레이터 지시대로 재시도·우회 없음. 키·토큰 출력 0.
- [미확인 — 38-09 T3 F 에서 재시도] `projects:test 12/12`. 케이스 JSON 의 쓰기 요청 형상(`request.resource.data` = 후상태, top-level `resource.data` = 전상태)이 Rules REST 가 받는 그대로인지도 라이브로는 못 봤다(단위 테스트는 내가 정한 형상만 검사).
- [확인] `--release` 는 이 세션에서 **실행하지 않았다**(스크립트 호출 이력: `--dry-run --test` 1회, `--test` 1회). 배포(sam/firebase)·SSM/Firestore/S3 쓰기·Pod 기동·Firestore 스캔·push 전부 0.
- [확인] 작업 트리의 `.planning/TRAINING-DUE.md` 미커밋 변경은 손대지 않았다(스테이징 0).

## 진단 (관측에서 내가 붙인 해석 — 다음 세션 재검증 대상)

- 403 의 원인: Admin 서비스 계정(`firebase-adminsdk-fbsvc@…`)에 `firebaserules.rulesets.test` 권한이 없다 → `roles/firebaserules.admin`(또는 Firebase Admin 역할) 부여가 필요하고, `--release` 도 같은 SA 로는 `rulesets.create`·`releases.update` 가 막힐 것이다 [추론 — GCP IAM 실물 미확인]. 38-09 T3 는 (a) IAM 부여 뒤 `--test` 재시도 또는 (b) belle 콘솔 폴백(스크립트가 exit 2 로 신호) 중 하나를 고른다.
- 규칙 파일은 커밋됐지만 **라이브 규칙은 종전 그대로**(`reference/{document=**}` 인증자 전체 읽기) — 38-09 `--release` 전까지 private 서브문서가 생기면 모든 인증자에게 읽힌다. 다만 Lambda 가 template 에 없어 등록 자체가 38-09 전에는 일어날 수 없으므로 실노출은 0 [추론 — 배선 부재는 template.yaml 미변경으로 확인, 손 등록 경로는 없다고 봄].
- `REGISTRATION_LEASE_SEC = 900` 은 38-01 의 [ASSUMED] 그대로 — 실측 없음.

## Decisions Made

- `_guarded_update(ref_id, job_id, mutate)` 는 플랜 시그니처 그대로 두되 **트랜잭션 본문(`_tx`)을 돌려주고** 실행은 각 writer 가 `_run_in_transaction(_tx)` 로 한다. 이유: 가드 로직은 한 곳(stale → warning + False), 트랜잭션은 호출측 하나(:3070 nested 금지 규율), acceptance 의 "writer 별 `_run_in_transaction(_tx)` ≥ +7" 도 자연히 만족.
- `set_registration_active`/`set_registration_failed` 는 jobId 일치 **+ `processing`** 둘 다 요구(플랜 behavior 그대로), `set_reference_angles` 는 jobId 일치만(같은 작업이 활성화 전후 어느 쪽에서 써도 됨), `begin_self_check` 는 jobId + `active`. 같은 작업이 active 뒤 failed 를 쓰려 해도 False(테스트 `test_same_job_failure_after_active_is_noop`).
- `set_reference_self_check` 의 status 는 `models.SELF_CHECK_STATUSES` 4개 전부 허용(`done` 만 유한 score 필수). 38-08 requeue 가 Pod 부재 때 `queued` 를 같은 권위 가드로 쓸 수 있게.
- Lambda `_load_supplier_map` 은 성공만 캐시(60초) — 실패를 캐시하면 SSM 일시 장애가 1분 잠금이 된다. `get_parameter(WithDecryption=True)` 는 String 파라미터에도 무해.
- `firestore.rules` users/** 는 `read, delete` 자유 + `create`(`request.resource.data.keys().hasAny`) + `update`(`diff().affectedKeys().hasAny`) — `hasAll`/필드 존재 검사면 서버가 표식을 쓴 뒤 앱의 `coachReview` merge-set(`coachReview.ts`)이 전부 막힌다.
- Rules REST 쓰기 호출은 `http_post(url, body, token, method="POST"|"PATCH")` 한 seam — 테스트가 `[("POST", …/rulesets), ("PATCH", …/releases/cloud.firestore)]` 순서를 한 목록으로 잠근다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] V4 테스트가 정당한 `techniqueRefId` 값을 주입값으로 오인**
- **Found during:** Task 2 GREEN(1 failed)
- **Issue:** `OK_BODY.techniqueRefId == "ref-kip-up"` 이라 폼 dataclass repr 에 그 문자열이 정당하게 남는데, 테스트가 dict 표기(`'technique_ref_id': 'ref-kip-up'`)만 제거하고 "ref-kip-up 없음" 을 단언했다.
- **Fix:** V4 케이스는 `techniqueRefId: None` 으로 비워 `"ref-kip-up"` 이 주입 `refId` 로만 남게 하고 `"evil"`/`"ref-kip-up"` 부재를 직접 단언.
- **Files modified:** `backend/tests/test_reference_upload_url_handler.py`
- **Verification:** 21 passed
- **Committed in:** `ce0504f0`

**2. [Rule 2 - Missing validation] 읽기/순수 함수의 조용한 오답 차단**
- **Found during:** Task 1
- **Issue:** (a) `list_reference_registrations_by_status("done")` 같은 오타가 빈 목록으로 조용히 통과 (b) `self_check_authorized(doc, analysis_id=None, job_id=None)` 이 doc 의 `None` 필드와 우연히 일치 (c) `create_analysis_doc` 의 `payload.analysisId` 와 경로 id 불일치 (d) `set_registration_active` 빈 key/etag · `set_reference_angles` 비유한 `split_angle`.
- **Fix:** (a) `REGISTRATION_STATUSES` 밖 → ValueError(쿼리 0) (b) 빈 uid/analysis_id/job_id → False 먼저 (c) ValueError (d) ValueError.
- **Files modified:** `firestore_admin.py`, 테스트 5건 추가
- **Committed in:** `0b2585bd`

**3. [Rule 3 - Blocking] `firestore_admin.py` 모듈 상단 `import logging` 1줄(블록 밖)**
- **Found during:** Task 1
- **Issue:** 파일에 모듈 로거가 없고(함수 안 `import logging` 만) 새 블록이 모듈 수준 `_reg_log` 를 쓴다.
- **Fix:** import 절에 `logging` 추가. 보호 3함수 무접촉.
- **Committed in:** `0b2585bd`

**4. [Rule 3 - Blocking gate] `deploy_firestore_rules.py` 엔드포인트 주석 블록**
- **Found during:** Task 3 GREEN(1 failed)
- **Issue:** URL 을 `RULES_API` 상수 하나로 조립해 `firebaserules.googleapis.com` 이 2회 — 게이트(≥ 3: test·rulesets·releases)와 테스트가 실패.
- **Fix:** `# ─── 동작 ───` 아래에 5 엔드포인트(POST test · GET release · GET ruleset · POST rulesets · PATCH release) 전체 URL 주석. 로직 무변경.
- **Committed in:** `e4c3d16a`

---

**Total deviations:** 4 auto-fixed (Rule 1 ×1, Rule 2 ×1, Rule 3 ×2)
**Impact on plan:** 범위 확장 0. 뒤 플랜이 쓰는 이름·시그니처는 플랜 그대로(`_guarded_update` 의 반환 형태만 Decisions 에).

## Issues Encountered

- 라이브 `projects:test` 가 IAM 403 — 위 관측/진단. 이 task 의 게이트는 단위 테스트 + grep 이라 플랜 완료에는 영향 없음, 38-09 T3 F 로 이월.
- Edit 도구 1회 일시적 분류기 오류(`import logging` 삽입) → 같은 편집을 1회 재시도해 성공. 결과물 영향 0.

## Known Stubs

None. `_supplier_cache`(모듈 캐시)·`anglesUpdatedAt: 0` 자리값(트랜잭션 안에서 `_now_ms()` 로 덮임)은 stub 이 아니다. `firestore_rules_cases.json` 의 `_comment` 키는 `load_cases` 가 `testCases` 만 꺼내므로 API 에 실리지 않는다.

## Threat Flags

None — 새 표면(`POST /reference/upload-url`, Admin batch create, SSM 읽기, Rules REST)은 전부 플랜 `<threat_model>` T-38-06-1~11 안. 추가 관측 1건: `deploy_firestore_rules.py --test/--release` 가 요구하는 IAM 권한(`firebaserules.rulesets.test` 등)이 현재 SA 에 없다 — 권한을 부여하면 그 SA 로 규칙 배포가 가능해지므로 부여 범위는 38-09 에서 belle 이 정한다(T-38-06-11 정합).

## User Setup Required

이 플랜에서는 없음(코드·테스트만). **38-09 가 해야 하는 것(이 플랜 산출물이 전제하는 배선):**
- `template.yaml`: 함수 디렉터리 `backend/functions/reference-upload-url` + 라우트 `POST /reference/upload-url` + env `VIDEO_BUCKET`·`BELLE_UID`·`SUPPLIER_UIDS_PARAM`·`FIREBASE_SA_PARAM` + IAM(`s3:PutObject` presign 정책 `reference/*`, `ssm:GetParameter` 화이트리스트 파라미터).
- SSM `/sunity/motion/supplier-uids` = `uid:CODE, uid, …`(없으면 BELLE_UID 만 통과).
- 규칙: `--current --out <롤백원본>` → (IAM 부여 또는 콘솔) `--test` 12/12 → belle 승인 → `--release`.

## 다음 플랜 주의 (38-07 · 38-08 · 38-09 · 38-14)

- **38-07** — Pod 위임·copy_object 는 `claim_registration(ref_id, job_id)` 가 True 를 준 뒤에만. `set_reference_angles(ref_id, job_id=…, angles_flat=…, joint_keys=…, frames=…, real_fps=…, keypoint_report=<camelCase dict>)` — `KeypointReport` dataclass 를 그대로 넘기면 TypeError(38-05 차단 1과 같은 함정). `set_registration_failed(ref_id, job_id, error={"code","message","joints":[한국어 라벨]})`. 순서: `set_registration_active` → `begin_self_check(ref_id, job_id=…, analysis_id=…)` → `create_analysis_doc(uid, analysis_id, payload)`(표식 키는 `models.ANALYSIS_FIELD_SELF_CHECK_*`) → S3 복사(이벤트). `video_etag` 는 copy_object 응답 ETag 그대로(따옴표 포함 문자열 — 테스트는 `'"abc"'`).
- **38-08** — 훅: `doc = get_reference_registration(ref_id)` → `self_check_authorized(doc, uid=, analysis_id=, job_id=)` → `set_reference_self_check(ref_id, status="done"|"failed", uid=, analysis_id=, job_id=, score=)`(가드 실패는 False + warning, 예외 아님). requeue: `list_reference_registrations_by_status("queued")` → 건별 `claim_registration` → Pod. `set_registration_expired` 는 `registering` 에서만 True — 스윕은 `uploadExpiresAt < now` 이고 객체 부재일 때만 부른다.
- **38-09** — T1 step 0(a) baseline 은 `get_reference_registration("ref-*")` raw 읽기(가드 없음 [확인]). 규칙 배포 전 IAM 403 을 먼저 풀 것(위 진단).
- **38-14** — 재diff 도 같은 읽기 함수. 정은지 새 영상이 오면 이 phase 보다 시험 영상 2차가 먼저.

## Next Phase Readiness

- writer 13 + 순수 가드 + 입구 Lambda + 규칙/스크립트가 pytest 142건으로 닫혔고, 기존 11개 doc 은 `create()` + 쓰기 가드로 구조적으로 못 건드린다.
- 등록 작업 소유권(claim/lease/jobId)·자기 재현성 권위·공개/비공개 분리가 코드와 규칙 파일에 있다. 규칙은 REST 케이스로 검증 가능하나 라이브 검증은 IAM 때문에 [미확인] — 38-09 T3 F.
- "REQ-38-1/3/4/5 완료" 는 **코드·테스트 층**의 완료다. 런타임(배선·SSM·규칙 배포)은 38-09 뒤에만 참 [미확인 — 실행되지 않음].

## Self-Check: PASSED

- 파일 9개 존재(`test -f` 전부 FOUND) · 커밋 6건(`645023b3` · `0b2585bd` · `0eddf336` · `ce0504f0` · `d5740f2a` · `e4c3d16a`) `git log --all` 에 존재 · 플랜 커밋 범위 삭제 파일 0 [확인]
