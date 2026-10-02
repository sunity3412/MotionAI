---
phase: quick-261002-pa2
plan: 01
subsystem: supplier-intake (공급자 등록 입구)
tags: [phase-38, supplier-link, registration, review-request, cancel]
requires: [261001-thx review 상태 · 승인/반려/내리기 CLI · 38-14 대역 완주]
provides:
  - registrationStatus 'cancelled' + 취소 오류 코드 not_cancellable · not_found (계약 3벌)
  - firestore_admin.cancel_reference_registration (소유자 검사 · 트랜잭션 · claim 과 경합 시 하나만)
  - validation.validate_reference_cancel_request (32 소문자 hex fullmatch)
  - POST /reference/upload-url {cancel: true, refId} 변형 (새 라우트 0)
  - 공급자 웹 '검토 중' 문구 · 검토 중 패널 · 화면 안 확인창 · 취소됨 패널
  - 261002-pa2-DEPLOY.md (배포 명령서 — 배포 안 함)
affects: [shared layer 다음 버전(:25 예상), reference-upload-url Lambda, 공급자 웹 번들]
tech-stack:
  added: []
  patterns: [상태 검사형 사람 결정 writer(소유자 = 토큰 uid) · 없는 doc = 남의 doc 같은 404 · 확인창 → 서버 → onSnapshot(낙관적 쓰기 없음)]
key-files:
  created:
    - .planning/quick/261002-pa2-supplier-review-request-copy-and-cancel/261002-pa2-DEPLOY.md
  modified:
    - backend/shared/python/sunity_shared/models.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/shared/python/sunity_shared/validation.py
    - backend/functions/reference-upload-url/app.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/constants/supplierCopy.ts
    - app/src/lib/supplierRules.ts
    - app/src/lib/supplierFixtures.ts
    - app/src/lib/api.ts
    - app/src/components/SupplierUi.tsx
    - app/src/app/supplier/index.tsx
    - 테스트 6개 (backend 4 · app 2)
decisions:
  - "취소 = queued · review 에서만, 공급자 본인만. 남의 doc 과 없는 doc 은 같은 404 not_found(playback-url _visible_to 선례), queued · review 밖은 409 not_cancellable"
  - "writer 는 공개 doc 하나만 읽고 쓴다 — 누가 = supplierUid, 언제 = registrationUpdatedAt. 비공개 doc 무접촉"
  - "명단 판정(403)은 취소에도 먼저 돈다 — 회수된 공급자는 자기 등록도 취소할 수 없다(단순함 우선)"
  - "승인 전 네 상태 행 = '검토 중'(진행 점 유지) + 이제 눌려서 검토 중 패널. hasDetail 은 모든 상태 true"
  - "파이프라인 · Pod · requeue · 검수 CLI 코드 무변경 — cancelled 는 기존 화이트리스트/상태 검사 밖이라 대기 아님으로 처리된다(테스트로 잠금)"
metrics:
  duration: "약 25분 (18:25~18:50 KST) [추정 — 시작 시각 미기록, 기준선 실행 종료 18:28:59 KST · 마지막 커밋 18:40:16 KST]"
  completed: 2026-10-02
  tasks: "3/3 (Task 3 = 배포 준비만, 배포 0)"
---

# Quick 261002-pa2: 공급자 '검토 요청' 문구 + 검토 요청 취소 Summary

공급자 등록의 승인 전 문구를 앱인토스식 '검토 요청' 말로 바꾸고(행 '검토 중', 패널 '검토는 보통 하루 안에 끝나요…', 토스트 '검토를 요청했어요…', 메일 약속 0), queued · review 인 자기 등록을 화면 안 확인창으로 거둘 수 있게 했다(새 상태 `cancelled`, 기존 `POST /reference/upload-url` 의 `{cancel: true, refId}` 변형, 서버 writer 가 소유자 · 상태를 트랜잭션으로 판정).

## 판정

- **코드: 완료** — Task 1 · 2 커밋 2개, 게이트 전부 통과 [확인 — 아래 게이트 표, 직접 돌린 출력]. push 안 함.
- **배포: 안 함** — Task 3 은 명령서(DEPLOY.md)만. AWS 쓰기 명령 실행 0 [확인 — 이 세션 명령 기록]. 실측 · zip 조립 · Docker 스모크 · 웹 export 는 읽기/로컬.
- **아직 안 본 것**: 공급자 화면이 실제로 어떻게 보이는지(검토 중 패널 · 확인창 · 취소됨 패널) **[미확인]** — 로그인 뒤 화면을 fixture 로 그리는 장치가 없다. 배포 뒤 '선택 확인'(DEPLOY.md)이 belle 이 화면을 보는 자리다.
- **배포 뒤 확인 주의**: TESTB(`UmH3…`)가 지금 `active False`(38-14 회수) [확인 `supplier_invite.py list` 읽기] → TESTB 토큰 확인은 전부 403 이 정답이다. 취소 분기(404/400/409)를 라이브로 보려면 활성 공급자 토큰이 필요하다 — 선택지 3개를 DEPLOY.md 에 적었다(오케스트레이터 · belle 판단).

## 커밋

| Task | 커밋 | 내용 |
|---|---|---|
| 1 | `8c716824` | cancelled 상태 · cancel_reference_registration · validate_reference_cancel_request · upload-url 취소 분기 · 계약 3벌 · 앱 typecheck 유지(정규화 목록 · rowStatusWord case · row.status.cancelled) |
| 2 | `c7e732cc` | supplierCopy 검토 요청/취소 문구 · supplierRules(detailKind · canCancel · cancelFailureMessage · pendingCopy · cancelledCopy) · api.cancelReferenceRegistration · SupplierUi PendingPanel/ConfirmDialog · 공급자 홈 배선 · fixture |
| 3 | — | DEPLOY.md 작성(커밋 안 함 — 문서 커밋은 오케스트레이터) |

## 관측 (코드 사실 · 테스트 결과 — 다음 세션이 승계해도 된다)

### 게이트

| 게이트 | 결과 |
|---|---|
| backend 기준선 `backend/.venv/bin/python -m pytest backend/tests -q -x` (착수 직후, 코드 변경 전) | **5860 passed, 20 skipped** [확인] |
| Task 1 RED (4파일) | **47 failed, 250 passed** [확인] — 파이프라인 `[cancelled]` 파라미터는 코드 변경 없이 통과(확인 테스트) |
| Task 1 GREEN 뒤 backend 전체 | **5910 passed, 20 skipped** (+50) [확인] |
| `test_source_never_reads_body_uid_or_ref_id` (V4) | 무수정 통과 · app.py 에 `body.get("refId")` · `body["refId"]` · `body.get("uid")` 0 [확인 grep] |
| 파이프라인 · Pod · CLI · 규칙 무변경 | `git diff --stat 7e701c36..HEAD -- backend/functions/pipeline backend/runpod_inference backend/scripts firestore.rules` 0줄 [확인] |
| app `npm run typecheck` | Task 1 뒤 0 · Task 2 뒤 0 [확인] |
| app node `node --test src/lib/*.test.ts src/constants/*.test.ts` | 기준 **89/89** → Task 1 뒤 89/89 → Task 2 RED(supplierRules 모듈 export 없음으로 파일 실패 + copy 실패) → **97 tests, 97 pass, 0 fail** [확인] |
| 공급자 화면 3파일 + SupplierUi 주석 밖 한국어 · 색 리터럴 · 이모지 · 브라우저 confirm/alert | 0 — scratchpad `pa2_literal_gate.mjs` → `LITERAL_GATE_OK`. 게이트가 헛돌지 않음은 PickErrorDialog(한국어 리터럴 있음)를 넣어 `FAIL 3` 이 나는 것으로 확인 [확인]. 플랜 verify grep(`window.confirm\|window.alert\|Alert.alert`) 0 [확인] |
| Docker 스모크(새 layer + 새 함수) | `SMOKE_OK unauth=401 probe_unauth=401 cancelled=ok writer=ok validator=bad_request(ref-kip-up)` [확인] |
| 웹 export (scratchpad) | exit 0, `entry-c8639132…js`, `BUNDLE_COPY_OK` [확인] |

backend +50 내역(파일별 collect 수, 기준 = 착수 시) [확인]:

| 파일 | 기준 → 지금 | 이유 |
|---|---|---|
| test_firestore_reference_writers.py | 139 → 162 (+23) | 가드 writer 12 → 13(parametrize +2) · claim 종결 표 +cancelled · begin_self_check 스킵 +cancelled · 취소 writer: queued/review 성공 2 · already 1 · bad_state 5 · 남의 uid 2 · 없음 1 · 빈 uid 3 · 경합 양방향 2 · 운영 writer 거부 3 |
| test_reference_upload_url_handler.py | 40 → 65 (+25) | 200 · already · 404 ×2 · 409 ×5 · 500 · 400 ×8(legacy · short · upper · 31hex · 끝 줄바꿈 · 숫자 · null · 없음) · 본문 uid 무시 · bool True 만 ×3 · 403 · 401 · fake_firestore 끝단 1 |
| test_registration_contract.py | 22 → 23 (+1) | 취소 상수 테스트 신설(기존 3벌 대조 테스트에 cancelled · 취소 코드 · 인터페이스 · contract.md 단언 추가) |
| test_register_reference_pipeline.py | 47 → 48 (+1) | 재PUT 스킵 parametrize 에 `cancelled` |

node +8 내역 [확인 `grep -c '^test('`]: supplierRules.test.ts 20 → 24 (pa2 상태어 · canCancel · cancelFailureMessage · pending/cancelled 문구, hasDetail 테스트는 detailKind 표로 교체) · supplierCopy.test.ts 23 → 27 (글자 단위 잠금 · models.py 문구 대조 · 메일/기한/출시하기 없음 · 옛 문구 없음).

### 동작 (테스트로 잠근 것)

- queued(소유자) → `('cancelled','queued')`, 공개 doc `registrationStatus 'cancelled'` · `isActive False` · `registrationUpdatedAt/updatedAt = now`, queuedReason · uploadKey 보존, 비공개 doc 생성 0, read-after-write 0 [확인 FakeFirestore].
- review(소유자, doc isActive True 로 심음) → `('cancelled','review')`, isActive False 명시, jobId · selfScore · thumbnailS3Key 보존 [확인].
- 두 번째 취소 → `('already_cancelled','cancelled')`, doc 동일 · 문서 version 불변(쓰기 0) [확인].
- registering · processing · active · failed · expired → `('bad_state', 그 상태)`, doc 무변경 [확인]. 남의 uid → `('not_found', 상태)`, 로그에 요청 uid · ref_id 만(doc 주인 uid 0) [확인 caplog]. doc 없음 → `('not_found', None)` [확인].
- 경합(FakeFirestore `run_contended`, 실제 version 충돌 → 재시도): 취소 먼저 → claim False · 최종 cancelled · jobId 없음 / claim 먼저 → 취소 `('bad_state','processing')` · 최종 processing jobId A. 두 경우 conflict_count 1 · read_after_write 0 [확인].
- claim_registration(cancelled) False · begin_self_check(cancelled) False · approve/reject/deactivate(cancelled) ValueError + doc 무변경 [확인]. 파이프라인 재PUT(cancelled) 'skipped', writer 0 [확인 — 코드 무변경].
- Lambda: 취소 분기는 명단 판정 뒤 · 이름 확인 앞(이름 없는 SSM 경로 공급자도 취소 200), writer 인자 `supplier_uid` = 토큰 uid, presign · create 호출 0. `cancel` 이 `"true"` · `1` · `"yes"` 면 폼 검증 400 [확인].

### 소비처 재대조 (착수 즉시, 지금 줄 번호)

- `firestore_admin.py:4624` claim_registration 화이트리스트 = registering/queued + lease 만료 processing → cancelled False [확인 코드 + 테스트, 코드 무변경 · docstring 만]. `:4486` `_REGISTRATION_TERMINAL` 에 cancelled 추가(소비처 0 — thx 와 같은 문서용 목록) [확인 grep]. `:5288` cancel_reference_registration 신설.
- `:5169` · `:5229` · `:5274` approve/reject/deactivate 의 bad_state ValueError 가 cancelled 를 거부 [확인 코드 + 테스트].
- `:4984` begin_self_check 는 review ∨ active 만(`:5003` 스킵 로그) → 취소가 먼저면 자기 재현성 선기록이 건너뛰어진다 [확인 테스트].
- `pipeline/app.py:332` `_handle_reference_upload` — `:354` registering 검사 · `:357` '스킵: 등록 대기 doc 아님' [확인 코드 + 테스트].
- `requeue_reference_registrations.py:119/:122/:127` queued · processing · registering 만 조회 [확인 코드]. `review_reference_registrations.py:123` list 는 review 만 [확인 코드].
- `backend/runpod_inference` · `backend/functions/pipeline` · `backend/scripts` 에 `cancel_reference_registration` · `REGISTRATION_STATUS_CANCELLED` 0 [확인 grep].
- 옛 웹 번들(라이브 `entry-394e74ae…`, 커밋 e1a74f51)의 `normalizeRegistration` 은 모르는 상태를 registering 으로 → 취소된 행이 '확인 중 · 끝나면 수강생에게 보여요' 로 보인다 [확인 `git show e1a74f51:app/src/lib/supplierRules.ts:119`]. 그래서 웹은 서버와 같이 올려야 한다(DEPLOY 순서).

### 플래너 사실 — 범위 밖, 사실로만 [확인 코드 · 바꾸지 않음]

- **review 에서 취소했을 때 이미 시작된 자기 재현성**: `set_reference_self_check`(`firestore_admin.py:5041`)는 상태를 보지 않고 `self_check_authorized` 만 본다 → cancelled doc 에 selfScore 를 쓸 수 있다. isActive false 라 수강생 노출 0. 취소가 begin_self_check 보다 먼저면 begin 이 상태 검사로 스킵한다.
- **취소된 doc 의 썸네일**: playback-url `_visible_to` 는 review 가 아닌 isActive false 를 소유자에게도 404 → 취소 행은 아이콘 자리(failed/rejected 와 같은 기존 동작). review 때 보이던 썸네일이 취소 뒤 사라진다.
- **S3 객체**: 취소해도 `upload.*` · `v1.*` · `thumb.jpg` 는 남는다(failed 와 같다). 정리 경로 없음.
- **회수된 공급자**: 명단 판정이 먼저라 `active False` 공급자는 자기 등록도 취소할 수 없다(403). 운영자가 직접 처리하는 경로는 지금 없다(CLI 에 cancel 명령 없음).
- **승인 전 행**: 진행 점은 그대로이고 이제 눌린다(검토 중 패널). queued · review 만 취소 링크가 보이고 registering · processing 은 안내만.

## 진단 (승계 전에 재검증할 것)

- **"화면이 의도대로 보인다"** — PendingPanel · ConfirmDialog 는 기존 FailurePanel · PickErrorDialog 문법과 theme 토큰으로만 그렸고 typecheck · 리터럴 게이트를 지났다. 실제 렌더(간격 · 확인창이 웹에서 가운데 뜨는지 · ESC 동작)는 **[미확인]** — 배포 뒤 선택 확인에서 belle 눈으로.
- **"onSnapshot 이 취소 직후 패널을 cancelled 로 바꾼다"** — 낙관적 쓰기 없이 구독에 맡겼다. 구독 지연 동안(보통 1초 안 [추정]) 확인창은 닫히고 검토 중 패널이 잠깐 남는다. 그 사이 링크를 다시 누르면 두 번째 요청은 200 alreadyCancelled 라 해가 없다 [확인 테스트]. 체감은 [미확인].
- **"하루 안"** — belle 원문 "실제 3일이 걸리진 않음. 반나절 이내" 를 넉넉히 '보통 하루 안' 으로 적었다(결정 3 문구 그대로). 검수 운영(Claude CLI + belle 사진 OK)이 실제로 하루를 넘기면 문구가 거짓이 된다 — 운영 속도에 달렸다.
- **"pipeline LastModified 가 오늘인 이유"** — 코드 해시는 thx 기록 접두와 같아 설정 변경으로 보이나(38-14 Pod 정리의 Lambda 자리표시자) [미확인].

## 용어 혼재 후보 — '운영팀 확인' 과 '검토' (안 바꿈, belle 판단)

belle 10-02 "제출과 취소정도만 그냥하든가" → 범위는 승인 전 상태어 · 검토 중 패널 · 업로드 토스트 · 취소 문구로 좁혔다. 아래는 같은 화면에 '확인' 말이 남은 자리다:

| 키 | 지금 글자 | 함께 보이는 새 말 |
|---|---|---|
| `home.motionsSub` | 올린 동작은 운영팀 확인 뒤 앱의 기준 동작 목록에 올라가요. | 행 '검토 중' |
| `home.emptyBody` | 올린 동작은 운영팀 확인 뒤 앱의 기준 동작 목록에 올라가요. 올리기 전에 촬영 전 체크 3가지를 확인해 주세요. | (빈 상태) |
| `guide.s4.items[0~1]` | …운영팀이 확인하고 기준 동작으로 올려요. 확인 전에는… / 확인이 끝나면… (docs/supplier-guide.md 와 글자 대조 잠금) | 검토 중 패널 |
| `row.fail.rejected.title` | 운영팀 확인에서 등록되지 않았어요 (결정 5 — 그대로, models · analysis.ts · contract.md 3벌) | — |

후보(안 바꿈): '운영팀 확인 뒤' → '검토 뒤', 가이드 s4 → '검토' 로 통일(md 동시 수정 필요), 반려 제목은 결정 5 로 고정.

## 벤치 메모 (결정 6 — proposals-must-be-benchmarked)

- **정면 = 토스 앱인토스 콘솔 출시 흐름**: '검토 요청하기 → 검토 중 → 검토 완료', 요청 단계에서 '요청 취소됨', 반려 시 사유 표시. 가져온 것 = 상태어 '검토 중' · '요청 취소됨', 검토 요청 시 예상 시간 안내, 요청자가 스스로 거두는 취소, 반려 사유(thx 에 이미 있음 — 그대로).
- **안 가져오는 것**: ① '검토 완료 → 출시하기' 의 별도 출시 단계 — 우리는 승인 = 즉시 공개(approve → active → picker, 결정 2). ② '3일 이내 메일로 알려 드려요' 약속 — 메일 인프라가 없고(grep 0, 결정 1), 실제 검토는 반나절 안이라 기한 숫자 대신 '보통 하루 안' 과 '결과는 이 화면에서'.

## Deviations from Plan

### Auto-fixed / 판단

1. **[Rule 2 - 입력 검증] refId 정규식을 `fullmatch` 로** — 플랜은 "정규식에 맞으면" 인데 Python `re.match(r"^…$")` 는 끝 줄바꿈 앞에서도 맞아 `'<32hex>\n'` 이 통과한다. `fullmatch` 로 바꾸고 handler 테스트에 `trailing-newline` 400 을 더했다(운영 CLI `_REF_ID_RE` 와 같은 정규식 문자열은 유지). 커밋 `8c716824`.
2. **[판단] 검토 중 패널에서는 비공개 doc 을 구독하지 않는다** — 패널이 비공개 필드를 쓰지 않아 읽기 1건을 아꼈다(Firestore Spark 읽기 상한 메모리). 취소되면 detailKind 가 cancelled 로 바뀌어 그때 구독해 다시 올리기 프리필(techniqueRefId)을 채운다. 커밋 `c7e732cc`.
3. **[판단] 확인창 [닫기] 도 busy 동안 비활성** — 플랜은 백드롭 · onRequestClose 만 적었다. 요청이 나가는 중에 창을 닫는 길을 모두 막아 일관되게 했다.
4. **[판단] 취소 실패 표를 fixture(`cancelFailures`)로** — 테스트 파일에 리터럴을 다시 쓰지 않는 fixture 한 벌 규율. 403 · 400 · 다른 409 코드 → 일반 문구도 표에 넣었다.
5. **[판단] 테스트 추가(플랜 밖, 같은 축)**: begin_self_check `cancelled` 스킵 · 취소 오류 문구 = models.py 글자 대조(node 테스트가 models.py 를 텍스트로 읽는다) · 공급자 문구 전역 '메일로 알려' · '출시하기' 0 · 옛 문구 0. `_Recorder` 에 kwcalls 를 더했다(기존 calls 무변경 — 키워드 인자 supplier_uid 확인용).
6. **[판단] Docker 스모크 3조합** — 플랜은 새 layer + 새 함수 하나. "옛 함수 + 새 layer = 안전", "새 함수 + `:24` = ImportError" 를 같이 돌려 배포 순서(layer 먼저)와 롤백 순서(코드 먼저)를 실측으로 뒷받침했다.
7. **[환경] 웹 번들 문구 검사 도구** — 번들이 한글을 `\uXXXX`, 가운뎃점을 `\xb7` 로 내보내 grep 이 전부 0 을 낸다. 둘 다 푸는 `pa2_bundle_check.mjs` 를 만들고 라이브 옛 번들에서 옛 문구가 1 로 잡히는 것으로 디코더를 검증했다(처음 판은 `\xb7` 를 못 풀어 '·' 문구를 0 으로 잘못 셌다 — 고친 뒤 재검사).
8. **[환경] Docker Desktop 을 켰다** — `open -a Docker`(로컬). 배포 아님.
9. **[판단] 배포 뒤 확인 대상** — TESTB 가 회수 상태라 기대값을 403 으로 적고, 취소 분기를 라이브로 볼 선택지 3개를 남겼다(결정하지 않음).

### TDD Gate Compliance

플랜 type 은 `execute`(태스크 단위 tdd="true"). Task 1 · 2 모두 RED 를 실행으로 확인한 뒤 구현했고(위 게이트 표), 테스트와 구현은 태스크당 커밋 하나(`feat`)로 묶었다 — 별도 `test(...)` 커밋은 없다(플랜 지시 커밋 메시지 그대로).

## Threat Flags

없음 — 새 표면(`{cancel, refId}` 입력 · Admin SDK 쓰기)은 플랜 threat register T-pa2-01~08 안이다. T-pa2-01(소유자) · 02(같은 404) · 03(형식) · 04(경합) · 05(운영 CLI 거부) · 06(registrationUpdatedAt + `reference-cancel` 로그) · 07(배포 순서 — Docker 스모크)은 테스트 또는 실측으로 잠갔다.

## Known Stubs

없음.

## 확인 필요 (belle / 오케스트레이터)

1. DEPLOY.md 승인 — 배포 순서 layer → reference-upload-url(layer → 코드) → 웹.
2. 배포 뒤 확인 대상 계정(TESTB 403 그대로 / TESTB 잠깐 되살림 / BELLE uid) 선택.
3. 용어 혼재 4자리('운영팀 확인' vs '검토') 통일 여부.
4. STATE.md 는 건드리지 않았다(stopped_at 포함) — 오케스트레이터 몫.

## Self-Check: PASSED

- FOUND: `261002-pa2-DEPLOY.md` · `261002-pa2-SUMMARY.md` [확인 ls]
- FOUND: 커밋 `8c716824` · `c7e732cc` (main, push 안 함) [확인 git log]
- FOUND: scratchpad 조립물 `pa2-build/layer-new.zip` · `pa2-build/fn-ruu-new.zip` · `pa2-build/smoke.py` · `pa2_bundle_check.mjs` · `pa2_livecheck.py` · `pa2_literal_gate.mjs` — **휘발**(세션 scratchpad) [확인 ls]
- 작업 트리: `git status --porcelain backend app docs` 0줄 [확인]
