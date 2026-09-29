---
phase: 38-supplier-link
plan: 08
subsystem: pipeline
tags: [pipeline, runpod, fastapi, firestore, registration, self-check, requeue, tdd, pytest, supplier-link]

# Dependency graph
requires:
  - phase: 38-supplier-link (38-01)
    provides: models.ANALYSIS_FIELD_SELF_CHECK_* · SELF_CHECK_STATUS_* · REGISTRATION_STATUS_* · REG_ERR_SERVER_ERROR · REGISTRATION_ERROR_MESSAGE · s3keys.parse_reference_key(is_upload)
  - phase: 38-supplier-link (38-06)
    provides: firestore_admin self_check_authorized(순수) · set_reference_self_check(트랜잭션 가드) · get_reference_registration · claim_registration(now_ms) · set_registration_failed(job 가드) · set_registration_expired · list_reference_registrations_by_status · get_analysis
  - phase: 38-supplier-link (38-07)
    provides: pipeline._register_reference(bucket, key, uid, ref_id, job_id) · _trigger_self_check(표식 2개 + begin_self_check 선기록) · _delegate_to_runpod(url=/register-reference, extra={jobId})
provides:
  - "pipeline._self_check_target(meta, uid, analysis_id) -> (ref_id, job_id) | None — 표식 2개 + firestore_admin.self_check_authorized 하나로 가드"
  - "pipeline._record_self_score_if_needed(meta, result, uid, analysis_id) — result.overallScore(화면 점수)를 set_reference_self_check(done) 로, 모든 예외 삼킴"
  - "pipeline._mark_self_check_failed_if_needed(uid, analysis_id) — get_analysis 로 meta 재조회 → 같은 가드 → set_reference_self_check(failed), 모든 예외 삼킴"
  - "_process 의 분석 완료 로그 바로 다음 줄 훅 1줄 · lambda_handler except 3곳 · server._process_in_background except 3곳 실패 훅"
  - "Pod POST /register-reference {bucket, key(upload 키만), jobId?} → 202 {status, uid, refId, jobId} · jobId 없으면 claim_registration(False → 409) · 배경 예외 → set_registration_failed(server_error)"
  - "backend/scripts/requeue_reference_registrations.py — queued 재개 · --reclaim-stale · --sweep-expired · --dry-run, main(argv, *, now_ms) -> int"
affects: [38-09 (배포 순서: Pod 코드 → Lambda → 버킷 알림 접두사), 38-10 (공급자 행 selfScore/selfCheckStatus 표시가 이 훅의 쓰기를 읽는다), 38-14 (실물 — /register-reference 401/503 probe · requeue dry-run · selfScore 실측)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "권위 가드 단일 출처 — 훅은 비교식을 다시 쓰지 않고 firestore_admin.self_check_authorized 를 부른다(AST 테스트가 훅 소스에 supplierUid/selfCheckAnalysisId 문자열 0 을 잠근다)"
    - "Pod 라우트의 claim 은 전달자 우선 — jobId 가 오면 그대로, 없을 때만 Pod 가 claim(입구가 셋이어도 실행 1회)"
    - "재개 스크립트 = 상태별 등가 쿼리 3개 + 클라이언트 측 시각 필터(복합 인덱스 불필요) + claim 경유 POST"
    - "CLI 전용 env 기본값(_default_sa_env)은 main 밖 __main__ 블록에서만 — 테스트 프로세스 env 오염 방지"

key-files:
  created:
    - backend/scripts/requeue_reference_registrations.py
    - backend/tests/test_self_score_hook.py
    - backend/tests/test_requeue_reference_registrations.py
  modified:
    - backend/functions/pipeline/app.py
    - backend/runpod_inference/server.py
    - backend/tests/test_runpod_server.py

key-decisions:
  - "38-08: Pod /register-reference 의 claim 은 server 모듈의 firestore_admin 로 부른다(플랜 원문 pipeline_app.firestore_admin) — Pod 에선 같은 모듈 객체이고, 요청 경로에서 pipeline 모듈 로드를 기다리지 않게"
  - "38-08: 409 는 HTTPException detail 'registration not claimable'(응답 {detail}) — 같은 라우트의 400/401 과 같은 형상"
  - "38-08: requeue 플래그는 누적 — queued 는 항상, --reclaim-stale · --sweep-expired 는 각 상태 쿼리를 더한다. --dry-run 은 S3 head 도 부르지 않는다"
  - "38-08: overallScore 가 bool · 문자열 · NaN · inf 면 selfScore 를 쓰지 않고 warning(writer 의 ValueError 에 기대지 않음)"

patterns-established:
  - "실패 훅은 fail_analysis 다음 줄 — 분석 실패 기록이 먼저, 자기 재현성 표시는 그 뒤 best-effort"

requirements-completed: [REQ-38-2, REQ-38-4]

# Metrics
duration: 12min
completed: 2026-09-30
---

# Phase 38 Plan 08: selfScore 훅 + Pod `/register-reference` + 재개 스크립트 Summary

**자기 재현성 분석이 끝나면 기준 doc 권위 가드(`self_check_authorized`)를 지난 경우에만 화면 점수(`overallScore`)가 `selfScore` 로 실리고, 실패하면 같은 가드 뒤 `selfCheckStatus:'failed'` 가 남는다. Pod 에 `POST /register-reference` 가 생겨 Lambda 위임·requeue·손 curl 이 모두 같은 claim 을 지나 등록 서비스를 부르고, Pod 기동 뒤 `requeue_reference_registrations.py` 한 번이 `queued`·lease 만료 `processing`·presign 만료 `registering` 을 닫는다. Pod 0 · Firestore 0 · AWS 0 으로 테스트했다.**

## Performance

- **Duration:** 12 min (00:20 → 00:32)
- **Started:** 2026-09-30T00:20+09:00
- **Completed:** 2026-09-30T00:32+09:00
- **Tasks:** 2 (각각 RED → GREEN 커밋)
- **Files modified:** 6 (생성 3 · 수정 3)

## Accomplishments

- selfScore 훅 2개 + 공통 `_self_check_target` — 위조 표식(u9 → r1) · 다른 공급자 refId · stale analysis id · pending 전 완료(R8) · 기준 doc 없음 · job 불일치 전부 writer 0회(테스트 6건)
- `_process` 의 `log.info("분석 완료 …")` 바로 다음 줄(10283, 로그 10282)에 훅 1줄. `lambda_handler` · `server._process_in_background` 의 except 각 3곳에서 `fail_analysis` 다음에 실패 훅
- Pod `POST /register-reference` — 토큰 없음 401 · legacy/uploads/v1 키 400 · `jobId` 전달 시 claim 0회 · `jobId` 없음 → Pod claim(False 409, 실행 0) · 배경 예외 → `set_registration_failed(server_error, 정본 문구)`
- `requeue_reference_registrations.py` — 테스트 20건(dry-run 무접촉 · 헤더 4개+jobId · 두 번 실행 POST 1회 · 비202/네트워크 오류 실패 카운트 · 키 5종 스킵 · 플래그 없으면 queued 쿼리 하나 · reclaim/sweep 경계)

## Task Commits

1. **Task 1 RED: selfScore 훅 · /register-reference 실패 테스트** — `912acf4c` (test)
2. **Task 1 GREEN: 훅 2개 + 배선 + Pod 라우트** — `f3ecc04e` (feat)
3. **Task 2 RED: requeue 실패 테스트** — `d0995958` (test)
4. **Task 2 GREEN: requeue 스크립트** — `7847ba5d` (feat)

## 관측 (다음 세션이 승계해도 되는 것)

- **[확인] 전체 backend suite:** `cd backend && .venv/bin/python -m pytest tests -q` → **5566 passed, 20 skipped, 98 warnings in 59.24s** (벽시계 61초). 38-07 뒤 5499 passed 에서 +67(이 플랜 신규 테스트 수와 일치: hook 33 + server 14 신규 + requeue 20). RESEARCH A15(전체 suite 소요) 해소 — 약 1분.
- **[확인] 플랜 검증 묶음 6파일:** 139 passed. 파일별: `test_self_score_hook.py` 33 · `test_runpod_server.py` 19(기존 5 + 신규 14) · `test_requeue_reference_registrations.py` 20.
- **[확인] app typecheck:** `npx tsc --noEmit` exit 0 (이 플랜은 app 무접촉).
- **[확인] acceptance grep:** 훅 호출 1줄(로그 +1줄) · `_mark_self_check_failed_if_needed(uid, analysis_id)` app.py 3 · server.py 이름 3 · `self_check_authorized(` app.py 1 · `@app.post("/register-reference"` 1 · `"selfCheckForReference"` 리터럴 app.py 0 / server.py 0 · requeue `head_object` 1 · `"completed"|"error"` 0 · `list_reference_registrations_by_status` 3 · `stream()` 0 · `claim_registration|set_registration_expired` 3.
- **[확인] `/analyze` 본문 무접촉:** `git diff` 의 server.py 삭제 줄은 import 1줄(`parse_upload_key` → `parse_reference_key, parse_upload_key`)뿐. `/health` 응답 형상 무변경(podwatch probe 계약).
- **[확인] 기록 값의 소비처 추적:** 훅이 쓰는 값은 `result["overallScore"]`. 이 필드는 `_apply_vision_veto` 의 applied/not_applicable 경로에서 `breakdown.final`(app.py :3766 · :3935 · :3953)이고, 앱 `result.tsx:812` 가 `종합 ${Math.round(result.overallScore)}점` 으로 그리는 같은 필드다. `dimensionScores` 가 아니다.
- **[확인] 예외:** veto 가 `skipped_error` passthrough 로 떨어지면 `overallScore` 는 `breakdown.final` 이 아니라 score_result 원값이다(app.py `_veto_passthrough`). 훅은 그 값을 그대로 기록한다 — 앱 화면에 뜨는 값과는 여전히 같다.
- **[확인] `scoreSuppressed`:** `_apply_score_suppression` 은 `overallScore` 를 지우지 않고 플래그만 단다 → 억제된 분석이어도 selfScore 는 기록된다. 자기 재현성 분석(새 UUID refId 의 mode1)이 억제 경로를 타는지는 **[미확인]** — 38-14 실물에서 볼 것.

## 진단 / 판단 (승계 전 재검증 대상)

- **[미확인] 배포 순서:** 이 플랜은 아무것도 배포하지 않았다. 38-07 Lambda 코드가 이 라우트 없는 Pod 에 `/register-reference` 를 보내면 404 → `_delegate_to_runpod` RuntimeError → 등록 doc `failed(server_error)` 가 될 것이라는 38-07 진단은 그대로 유효하다(코드 경로로 추론, 실물 미관측). 순서 = Pod 코드(이 플랜) → Lambda(38-07) → 버킷 알림 `reference/` 접두사(38-09).
- **[추론] requeue 뒤 POST 실패 건:** claim 성공 후 POST 가 실패하면 doc 은 `processing`(lease 900초)에 남는다. 스크립트는 그 건을 실패로 세고 "lease 만료 뒤 `--reclaim-stale`" 을 안내한다. 자동 재시도는 없다.
- **[추론] 훅의 이중 가드:** 훅의 사전 검사(`_self_check_target`)와 writer 트랜잭션 안 검사가 같은 함수다. 사전 검사는 읽기 1회를 더 쓰는 대신 불필요한 트랜잭션·warning 을 줄인다. 두 검사 사이에 기준 doc 이 바뀌면 writer 가 막는다.

## Pod 기동 절차 7단계 (메모리 demo-only-pod-bring-up-procedure 에 붙일 문장 — 갱신은 오케스트레이터/belle 몫)

> 7. **대기 등록 재개** — 1~6 을 마치고 health 가 `pipeline_loaded:true` 이면, 리포 루트에서
> `AWS_PROFILE=sunity-motion backend/.venv/bin/python backend/scripts/requeue_reference_registrations.py --dry-run`
> 으로 대기 건을 보고, 있으면 인자 없이 한 번 돌린다(Pod 부재 중 올린 공급자 등록은 `queued` 로 남아 있다 — 안 돌리면 영영 대기).
> Pod 이 중간에 죽었던 날은 `--reclaim-stale`, 오래 방치된 `registering` 이 보이면 `--sweep-expired` 를 더한다. 두 번 돌려도 claim 이 막아 등록은 한 번만 돈다.

**라우트 존재 확인법(38-09/38-14):** `/health` 는 라우트 목록을 싣지 않는다. 대신
`curl -s -o /dev/null -w '%{http_code}' -X POST https://{podId}-8000.proxy.runpod.net/register-reference -H 'Content-Type: application/json' -d '{"bucket":"x","key":"x"}'`
→ 토큰 설정된 Pod 은 **401**, 토큰 미설정 Pod 은 **503**, 라우트 없는 옛 코드면 **404**(토큰 검사 전에 라우팅이 먼저 404).

## Files Created/Modified

- `backend/functions/pipeline/app.py` — `_self_check_target` · `_record_self_score_if_needed` · `_mark_self_check_failed_if_needed`(+94줄, 삭제 0) + `_process` 훅 1줄 + `lambda_handler` except 3줄
- `backend/runpod_inference/server.py` — `RegisterReferenceRequest/Response` · `_register_in_background` · `POST /register-reference` · `_process_in_background` 실패 훅 3곳 · 머리말 1절
- `backend/scripts/requeue_reference_registrations.py` — 신규 CLI
- `backend/tests/test_self_score_hook.py` · `backend/tests/test_requeue_reference_registrations.py` — 신규
- `backend/tests/test_runpod_server.py` — `reg_mod` fixture(FakeMod · FakeAdmin) + 신규 14건, 기존 5건 무변경

## Decisions Made

frontmatter `key-decisions` 4건. 요약: claim 은 server 의 `firestore_admin`(Pod 에선 같은 모듈), 409 는 `{detail}` 형상, requeue 플래그 누적·dry-run 은 S3 도 안 부름, 비수치 overallScore 는 훅이 먼저 거른다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing validation] requeue 가 doc 의 refId 와 uploadKey 의 refId 불일치를 스킵**
- **Found during:** Task 2
- **Issue:** 플랜은 `parse_reference_key` 실패 · `kind != upload` 만 스킵. doc `motionId` 와 키 속 refId 가 어긋나면 다른 기준의 영상으로 이 doc 을 claim 하게 된다.
- **Fix:** `_upload_key(doc)` 가 `ref.ref_id != doc["motionId"]` 도 None. 테스트 파라미터 1건 추가.
- **Files modified:** `backend/scripts/requeue_reference_registrations.py`
- **Commit:** `7847ba5d`

**2. [Rule 2 - Missing error handling] `_register_in_background` 의 `set_registration_failed` 자체 실패를 삼킴**
- **Found during:** Task 1
- **Issue:** 실패 기록이 Firestore 장애로 예외를 내면 배경 작업이 예외로 끝나 로그가 흐려진다.
- **Fix:** 안쪽 try/except + `log.exception` — doc 은 `processing` 에 남고 lease 만료 뒤 `--reclaim-stale` 가 줍는다.
- **Commit:** `f3ecc04e`

**3. [Rule 3 - Blocking gate] requeue `head_object` grep 게이트 1**
- **Found during:** Task 2 acceptance — docstring · help · 출력 문구에 단어가 있어 4.
- **Fix:** 설명 문구를 "S3 객체 확인/유무" 로. 로직 무접촉. 20 passed 재확인.
- **Commit:** `7847ba5d`

**4. [계약 해석] claim 호출 대상 모듈 · 409 응답 형상** — key-decisions 첫째·둘째 줄. 동작은 플랜과 같다(`claim_registration` 1회, 409, 실행 0).

**Total deviations:** 3 auto-fixed (Rule 2 ×2, Rule 3 ×1) + 해석 1. **Impact:** 뒤 플랜이 쓰는 이름·시그니처·라우트 계약은 플랜 그대로.

## Issues Encountered

None — RED 두 번 모두 기대대로 실패(44 failed / collection error), GREEN 첫 실행 통과.

## TDD Gate Compliance

두 태스크 모두 `test(38-08)` → `feat(38-08)` 순서 커밋 존재(`912acf4c` → `f3ecc04e`, `d0995958` → `7847ba5d`). REFACTOR 커밋 없음(불필요).

## Known Stubs

None.

## Threat Flags

None — 새 표면(`POST /register-reference` · requeue 의 SSM 읽기 · S3 head · Pod POST · Admin claim/expired 쓰기)은 전부 플랜 `<threat_model>` T-38-08-1~7 안. T-38-08-4(토큰 출력 금지)는 테스트 2건(`t-secret` 미출력)으로 잠갔다.

## User Setup Required

없음(코드·테스트만, push 안 함 — 방식 belle 결정 대기).

## Next Phase Readiness

- 등록 경로 코드가 Lambda(38-07) · Pod 라우트 · 재개 스크립트까지 닫혔다. 전체 suite green.
- 웨이브 4 남은 것: 38-10(앱 공급자 화면 — 행의 selfScore/selfCheckStatus 는 이 플랜의 훅이 쓴다).
- 38-09: 배포 순서(Pod → Lambda → 알림 접두사)와 위 curl 401/503/404 확인법을 체크리스트에.

## Self-Check: PASSED

- 파일 6개 존재 · 커밋 4건(`912acf4c` · `f3ecc04e` · `d0995958` · `7847ba5d`) `git log` 에 존재 · 플랜 커밋 범위 삭제 파일 0 [확인]
