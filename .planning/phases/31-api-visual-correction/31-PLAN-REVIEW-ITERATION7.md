# Phase 31 계획 7차 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-19  
**리뷰 범위:** 6차 개정된 `31-01-PLAN.md` ~ `31-13-PLAN.md`, `31-VALIDATION.md`, 1~6차 리뷰, Phase 31 CONTEXT/ROADMAP 및 계획이 직접 참조하는 현재 코드/IaC  
**리뷰 방법:** 6차 blocker/High/Medium별 closure 추적, 비-버저닝 VisualInputBucket 전환의 IAM·versioning·provisioning·lifecycle 적용 검증, upload-first 하드 크래시 시간축, finalize privacy validator 데이터 흐름, create 내부 전이/outbox 분석, metric/alarm 실권한과 제품 목표(D-06 완료 알림) 재대조  
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 리뷰 없이 직접 검토했다. AWS 공식 문서는 S3 versioning 상태와 삭제 의미를 확인하는 1차 자료로만 사용했다.  
**최종 판정:** **BLOCK / TARGETED REPLAN REQUIRED**

---

## 1. 결론

6차 개정은 이전 네 blocker를 정면으로 다뤘고 방향도 대체로 좋아졌다.

- claim 반환 snapshot handoff와 새 outboxSeq의 claim field clear가 계약·테스트에 들어갔다.
- sent recovery가 current-seq expired claim만 고르고 별도 cursor를 갖도록 좁혀졌다.
- 임시 생체 프레임을 전용 비-버저닝 버킷으로 분리해 version-aware cleanup 복잡도를 제거하려 했다.
- producer preflight/inputSealed, cleanup_blocked 비-terminal, pair partial payload 검증, marker-pair pagination, hash conflict 차단이 반영됐다.
- 6차 High/Medium 대부분이 테스트 matrix와 live IAM checkpoint로 연결됐다.

그러나 비-버저닝 버킷 전환 과정에서 실제 실행을 막거나 개인정보 완전 삭제 주장을 깨는 blocker가 새로 생겼다.

1. postprocess는 `list_objects_v2`를 필수 호출하지만 worker IAM에는 bucket-level `s3:ListBucket`이 없다. 실 배포에서 cleanup은 403이고 correctedPose는 terminal에 도달하지 못한다.
2. dry-run은 versioning 상태가 `Enabled`만 아니면 통과시켜 `Suspended` 버킷을 “비-버저닝”으로 오판한다. suspended bucket의 단순 delete는 과거 version 완전 삭제를 보장하지 않는다.
3. done finalizer는 기존 job의 `cleanupVerifiedAtMs > 0`을 요구하지만 postprocess는 이를 미리 persist하지 않고 `job_meta`로 같은 finalize 호출에 넘긴다. 계약을 글자 그대로 구현하면 모든 correctedPose done이 ValueError다.
4. failed correctedPose에는 cleanupVerified/inputSealed validator가 적용되지 않는다. “성공·실패 전부 cleanup 뒤 terminal”이라는 privacy invariant가 helper 레벨에서 강제되지 않는다.
5. upload-first는 PUT 직후 프로세스가 죽으면 reserve/보상 코드가 아예 실행되지 않는다. option-b의 두 번째 object 실패도 첫 object를 orphan으로 남길 수 있다.
6. `VisualInputBucketName`은 SAM 외부 bucket parameter일 뿐 신규 bucket 생성·보안 설정·존재 확인 절차가 어느 task에도 없다. Wave 1 smoke와 Wave 6 mutation 모두 전제 resource 없이 시작할 수 있다.
7. 두 bucket의 서로 다른 lifecycle을 하나의 `lifecycle_merged.json`/`lifecycle_before.json`에 담고 동일 파일을 두 번 `put-bucket-lifecycle-configuration`에 넘긴다. S3 API 입력 형상과 rollback 단위가 맞지 않아 적용 실패 또는 잘못된 규칙 교체가 발생한다.

따라서 6차의 핵심 방향은 유지하되, Wave 1 실행 전 31-01/02/09/10/12와 VALIDATION을 다시 targeted replan해야 한다.

### 발견 수

| 심각도 | 수 | 의미 |
|---|---:|---|
| BLOCKER | 7 | Wave 1 실행 전 계약/IaC/checkpoint 수정 필수 |
| HIGH | 9 | 같은 targeted replan에서 해결 필요 |
| MEDIUM | 5 | 배포 전 명시·검증 보강 필요 |

---

## 2. 6차 리뷰 지적 해소 추적

| 6차 ID | 7차 상태 | 판단 |
|---|---|---|
| B6-01 claim snapshot handoff | **대체로 해소** | claimed action은 반환 snapshot을 쓰고 새 seq에서 claim을 clear한다. create 특례가 inbound seq/due CAS와 내부 전이 dispatch 규칙을 우회해 H7-01/H7-02가 남음 |
| B6-02 cleanup IAM | **미해소(아키텍처 변경 후 재발)** | version action은 불필요해졌지만 `ListObjectsV2`용 `s3:ListBucket`이 빠져 실제 cleanup이 403 |
| B6-03 producer-cleanup race | **부분 해소** | preflight/inputSealed/terminal compensation은 좋음. PUT 직후 hard crash와 option-b partial upload는 보상 코드에 도달하지 못함 |
| B6-04 cleanup_blocked terminal 금지 | **부분 해소** | cleanup_blocked 비-terminal은 반영. done의 cleanupVerified 전달 모순과 failed validator 누락으로 helper-level invariant가 아직 열림 |
| H6-01 sent recovery 정확 필터 | **해소** | same-seq claimed lease-expired + 별도 sent cursor + 1,200건 검증 반영 |
| H6-02 reserve 실패 orphan 보상 | **부분 해소** | catch 가능한 실패는 보상. hard crash, multi-object partial, delete 보상 실패의 durable consumer가 없음 |
| H6-03 deterministic hash conflict | **해소** | staging/canonical overwrite 금지 + typed invalid_output 반영 |
| H6-04 partial pair payload 검증 | **해소** | 412 재사용 전 size/hash 검증 반영 |
| H6-05 HMAC config display 비차단 | **해소** | failed_config + pair PUT 0 + display 진행 반영 |
| H6-06 version pagination | **해소** | boto3 paginator 또는 marker pair 고정 |
| H6-07 lease build gate | **해소** | 300s < 360s < 1800s template assert 반영 |
| H6-08 Object Lock 조회 권한 | **대체로 해소** | simulate와 canary 권한을 추가함. 전용 GetObjectRetention/GetObjectLegalHold 호출 형상은 Medium으로 보강 필요 |
| H6-09 deterministic cleanup E2E | **해소 방향** | 2+ object setup과 before/after count를 필수화. 신규 bucket 진위·IAM이 먼저 닫혀야 실행 가능 |
| M6-01~05 | **해소** | metric 명칭, 409, busy visibility, conflict 즉시 quarantine, DeleteObjects Errors 반영됨 |

---

## 3. BLOCKERS

### B7-01 · cleanup이 `ListObjectsV2`를 쓰는데 worker에 `s3:ListBucket` 권한이 없다

**근거**

- `31-09-PLAN.md:25,135`의 `_cleanup_visual_input`은 `list_objects_v2`로 exact prefix를 전 페이지 열거하고 삭제 후 다시 열거한다.
- `31-10-PLAN.md:33,134`의 worker policy는 VisualInputBucket **object ARN**에 `GetObject/PutObject/DeleteObject`만 준다.
- `31-12-PLAN.md:115,123`의 IAM simulate도 object action과 version action만 확인하며 bucket ARN의 `s3:ListBucket`을 확인하지 않는다.
- `ListObjectsV2`는 object ARN 권한이 아니라 bucket ARN의 `s3:ListBucket`을 요구한다.

**영향**

실 AWS에서 correctedPose success/failure postprocess가 list 단계에서 403이 된다. cleanupAttempt 5회 후 모든 job이 `cleanup_blocked`에 남고, 정상 이미지 표시도 실패 종결도 일어나지 않는다. 단위 mock과 `sam validate`는 이 오류를 잡지 못한다.

**제가 처리한다면**

- VisualWorkerFunction에 bucket ARN `arn:aws:s3:::${VisualInputBucketName}`의 `s3:ListBucket`을 추가하고 `s3:prefix`를 `visual-input/*`로 제한한다.
- object ARN에는 현재의 Get/Put/Delete만 유지하고 version action은 계속 부여하지 않는다.
- 31-12 IAM simulate에 bucket ARN + `s3:ListBucket` allowed를 추가한다.
- 실제 role로 `list-objects-v2 --prefix visual-input/_iam-probe/`를 호출하는 non-PII canary를 flag ON 전에 수행한다.

---

### B7-02 · “Status != Enabled” 검사는 `Suspended` bucket을 안전한 비-버저닝 bucket으로 오판한다

**근거**

- `31-10-PLAN.md:135`는 `get-bucket-versioning`이 Enabled가 아니면 VisualInputBucket을 통과시킨다.
- S3 bucket은 unversioned, Enabled, Suspended가 서로 다른 상태다. 한 번 Enabled가 된 bucket은 unversioned로 돌아갈 수 없고 Suspended만 가능하다.
- Suspended bucket의 단순 DELETE는 null version만 제거하며 기존 version이 있으면 남길 수 있다. Lifecycle Expiration도 versioned/suspended에서는 current version 영구 삭제와 동일하지 않다.

공식 근거: [S3 Versioning의 세 상태](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html), [GetBucketVersioning 응답 형상](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketVersioning.html), [versioning-suspended bucket 삭제 동작](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjectsfromVersioningSuspendedBuckets.html)

**영향**

Status=`Suspended`인 기존 bucket이 dry-run과 checkpoint를 통과한다. `list-objects-v2 KeyCount==0`은 delete marker 아래 남은 noncurrent version을 보지 못하므로 E2E도 거짓 PASS할 수 있다.

**제가 처리한다면**

- 허용 조건을 `get_bucket_versioning()` 응답에 **`Status` key 자체가 없음**으로 고정한다. `Enabled`와 `Suspended`는 둘 다 blocker다.
- 사용 전 `list_object_versions`를 prefix 대상으로 1회 read-only 확인해 Versions/DeleteMarkers가 0임을 기록한다. 런타임 worker에는 version 권한을 주지 않고 checkpoint 주체만 검사한다.
- bucket을 새로 만들 때부터 versioning API를 한 번도 호출하지 않는 절차를 박제한다.
- flag ON 직전에 같은 검사를 반복하고 Suspended fixture가 반드시 blocked되는 unit test를 추가한다.

---

### B7-03 · `cleanupVerifiedAtMs`의 persist/validate 순서가 모순이라 correctedPose done이 불가능하다

**근거**

- `31-02-PLAN.md:136`의 finalizer는 `kind=='correctedPose' && terminal_state=='done'`이면 **현재 job 문서의** `cleanupVerifiedAtMs > 0`을 요구한다.
- `31-09-PLAN.md:135`의 postprocess는 remainingObject 0 확인 뒤 별도 transition으로 값을 기록하지 않고 `finalize_visual_job(... job_meta={cleanupVerifiedAtMs: ...})`에 넘긴다.
- 같은 두 계획의 호출 계약도 정확히 어긋난다. 31-02 함수 인자는 `job_meta`인데 31-09 호출 예시는 `meta={...}`라 문언 그대로 구현하면 Python `TypeError`다.
- transaction이 읽은 현재 job에는 여전히 초기값 0이다. validator가 write 후보를 만들기 전에 job을 검사하면 ValueError다.
- 반대로 먼저 postprocessing self-loop transition으로 값을 기록하면 새 outboxSeq와 claim clear가 생기므로 현재 owner로 즉시 finalize할 수 없다. 다음 postprocess 메시지에서 다시 claim하는 별도 단계가 필요하다.

**영향**

계획을 문언 그대로 구현하면 cleanup은 성공해도 모든 correctedPose done이 finalize되지 않는다. 구현자가 임의로 validator 순서를 바꾸면 테스트와 privacy 계약이 서로 다른 진실을 갖게 된다.

**제가 처리한다면**

두 방식 중 하나를 명시적으로 선택한다.

1. **권고:** `finalize_visual_job(cleanup_verified_at_ms=...)`가 transaction 안에서 기존 `inputSealed=True`, `privacyBlocker is None`, terminal intent를 검증한 뒤 candidate job에 cleanupVerifiedAtMs를 병합하고, 병합된 candidate를 validate+write한다. cleanup 시각과 terminal 전이가 한 transaction이다.
2. 별도 `postprocessing→postprocessing` 전이로 cleanupVerified를 persist하고 새 `postprocess` outbox를 만든 뒤, 다음 invocation이 재claim하여 finalize한다.

테스트는 remaining 0 + 기존 cleanupVerified 0에서 done finalize가 실제 성공하는 happy path와 forged timestamp/cleanup 미실행 거부를 둘 다 포함해야 한다.

---

### B7-04 · failed correctedPose는 cleanup 증명 없이도 finalizer를 통과할 수 있다

**근거**

- `31-02-PLAN.md:36,62,136`은 cleanupVerifiedAtMs/inputSealed 조건을 correctedPose **done**에만 적용한다.
- failed 조건은 typed failure reason + key None + privacyBlocker None뿐이다.
- `31-09`가 현재 모든 실패를 postprocessing으로 라우팅한다고 해도 helper 자체가 이를 강제하지 않으므로 새 호출 경로, 운영 스크립트, 회귀 코드가 failed를 직접 finalize할 수 있다.
- Phase 31의 privacy 주장은 성공과 실패 모두 임시 입력 0 뒤 terminal이다.

**영향**

에러 경로 하나가 direct finalize를 호출하면 분석은 failed로 닫히지만 raw source/staging이 남는다. 현재 finalizer test도 이 조합을 거부하지 않아 회귀를 허용한다.

**제가 처리한다면**

- `kind=='correctedPose'`이면 terminal_state가 done이든 failed든 `inputSealed=True`, cleanupVerifiedAtMs>0, privacyBlocker None을 공통 요구한다.
- failed는 추가로 typed reason/key None을 요구하고 done은 key/failureReason 규칙을 추가한다.
- correctedPose direct-finalize grep만 믿지 않고 helper unit test에서 `failed + cleanupVerified=0`, `failed + inputSealed=False`를 ValueError로 고정한다.
- analysis_missing 분기도 cleanup 이후 finalizer 호출에서만 도달하도록 fault test를 추가한다.

---

### B7-05 · upload-first의 하드 크래시와 option-b partial upload는 보상 코드에 도달하지 못한다

**근거**

- `31-10-PLAN.md:133`의 순서는 preflight → srcKey PUT → 필요 시 trainingSrcKey PUT → reserve → catch compensation이다.
- srcKey PUT 성공 직후 프로세스/Lambda가 강제 종료되면 reserve도 catch도 실행되지 않는다. job이 없으므로 postprocess 주체도 없다.
- option-b에서 srcKey 성공 후 trainingSrcKey PUT이 일반 오류로 끝나면 계획은 “log + return”이라고만 하며 첫 object cleanup을 보장하지 않는다.
- `createdThisInvocation`이 단일 bool이라 srcKey는 재사용하고 trainingSrcKey만 새로 만든 경우처럼 object별 소유권을 표현하지 못한다.
- 1일 lifecycle은 방어층이지 즉시 cleanup invariant가 아니다.

**영향**

raw 생체 프레임이 job 없이 최대 1일 남을 수 있다. 더 나쁜 경우 늦은 producer가 terminal cleanup 뒤 PUT하고 바로 죽으면 이미 끝난 job에는 다시 cleanup action이 없다.

**제가 처리한다면**

- 가장 안전한 방식은 Firestore에 `uploading` 성격의 durable reservation/journal을 PUT **전** 원자 생성하는 것이다. state 수 증가를 원치 않으면 별도 `visualInputReservations/{jobId}` 문서로 `{expectedKeys, expiresAt, owner}`를 기록한다.
- PUT 후 source hash/keys를 reservation에 확정하고 그 다음에만 visual job의 dispatch를 연다. janitor가 expired reservation의 exact prefix를 삭제한다.
- 대안은 S3 ObjectCreated event → cleanup queue로 모든 input object를 추적하고, 유효한 unsealed job 소유가 없으면 삭제하는 방식이다.
- 최소한 `created_keys: set[str]`를 object별로 추적하고 pre-reserve 모든 오류에서 역순 compensation한다.
- fault matrix에 `src PUT 직후 SIGKILL`, `src 성공→training 실패`, `terminal cleanup 뒤 stale producer PUT→SIGKILL`을 넣고 lifecycle 대기 없이 object 0을 요구한다.

---

### B7-06 · 신규 VisualInputBucket을 실제로 만드는 task가 없다

**근거**

- `31-10-PLAN.md:22,134`는 `sunity-motion-pilot-visual-input`을 “신규, SAM 외부 생성”이라고 한다.
- template에는 Parameter만 있고 S3 Bucket resource가 없다.
- `31-12-PLAN.md:92`는 존재한다고 가정하고 lifecycle put부터 수행한다. `head-bucket`/create-bucket 분기가 없다.
- `31-01` smoke도 `visual-input/_smoke/` S3 공간을 먼저 필요로 하지만 새 bucket provision은 Wave 6보다도 뒤에 암묵적으로 놓여 있다.

**영향**

bucket이 없으면 smoke, dry-run, lifecycle mutation, Pod, Lambda E2E가 모두 실패한다. 누군가 콘솔에서 임의 생성하면 region/ownership/public access/encryption/tag 설정이 계획 밖으로 빠져 재현성과 보안이 깨진다.

**제가 처리한다면**

- 31-01 앞 Wave 0 또는 31-01 blocking human-action에 `head-bucket` → 없으면 승인 후 create 절차를 둔다.
- region을 stack/VideoBucket과 맞추고 ObjectOwnership=BucketOwnerEnforced, Block Public Access 4종, 기본 SSE, no Object Lock, no versioning, lifecycle 1일, project/environment tag를 명시한다.
- 생성 후 `get-bucket-versioning` Status 부재, `get-object-lock-configuration` 미설정, public access block, encryption, ownership, location을 모두 기록한다.
- 이미 존재하면 같은 속성이 하나라도 다를 때 STOP하고 다른 새 이름을 사용한다.

---

### B7-07 · 두 bucket lifecycle을 한 JSON으로 적용·rollback하려는 형상이 S3 API와 맞지 않는다

**근거**

- `31-10-PLAN.md:135`는 `lifecycle_merged.json`과 `lifecycle_before.json` 한 쌍에 VisualInputBucket과 VideoBucket 규칙을 “두 buckets 분리 기록”한다고 한다.
- `31-12-PLAN.md:92`는 같은 `lifecycle_merged.json`을 두 bucket의 `put-bucket-lifecycle-configuration`에 각각 넘긴다.
- 이 API의 입력은 대상 bucket 하나의 `Rules` 배열이지 여러 bucket을 감싸는 custom wrapper가 아니다.
- before 파일도 하나면 두 bucket의 서로 다른 원상태를 독립 rollback할 수 없다.

**영향**

custom multi-bucket JSON이면 CLI schema validation에서 실패한다. 한 bucket 형상만 저장하면 다른 bucket에 잘못된 규칙을 적용하거나 기존 lifecycle을 소실할 수 있다. lifecycle put은 전체 교체라 위험이 크다.

**제가 처리한다면**

- 파일을 최소 네 개로 분리한다.
  - `visual_input_lifecycle_before.json`
  - `visual_input_lifecycle_merged.json`
  - `video_lifecycle_before.json`
  - `video_lifecycle_merged.json`
- 각 파일은 AWS API가 바로 받는 `{ "Rules": [...] }` 형상으로 만들고 bucket별 명령에 정확히 하나씩 전달한다.
- 첫 bucket 적용/검증 성공 후 두 번째를 적용한다. 두 번째 실패 시 첫 번째도 before로 되돌리는 compensating rollback 순서를 문서화한다.
- dry-run unit test가 각 merged JSON을 botocore shape validation하고 기존 규칙 보존을 bucket별로 assert하게 한다.

---

## 4. HIGH

### H7-01 · creating 내부 전이가 `_advance(..., next_action=None)`를 사용해 malformed SQS 메시지를 보낼 수 있다

`31-09-PLAN.md:103`의 `_advance`는 snapshot이 있으면 항상 `{action: next_action}`을 send+mark한다. `31-09-PLAN.md:105`는 reserved/retry_ready→creating에 `_advance(..., None)`을 호출한다. `31-02-PLAN.md:134`는 creating에서 dispatchState를 None으로 clear한다고 했지만 `_advance`의 send 조건은 별도로 없다. 글자 그대로면 각 vendor create마다 action null 메시지가 queue에 들어가 schema failure로 5회 재시도 후 DLQ를 오염시킨다.

**제가 처리한다면:** `_advance`를 `transition_and_dispatch`와 `transition_internal`로 분리한다. internal transition은 SQS send/mark를 절대 호출하지 않는 테스트를 둔다. 또는 `_advance`가 `next_action is not None`일 때만 send하며 creating snapshot의 dispatchState/nextAction이 둘 다 None인지 assert한다.

### H7-02 · create 특례가 inbound generation/action/outboxSeq와 nextDispatchAtMs를 CAS하지 않는다

claim을 생략한 create는 현재 job snapshot만 보고 reserved/retry_ready/creating을 처리한다. 오래된 create message가 moderation retry의 retry_ready 시점에 도착하면 현재 outbox를 소유하지 않아도 새 generation create를 조기 실행할 수 있다. backoff도 우회한다.

**제가 처리한다면:** create 전용 `begin_visual_job_create(job_id, expect_generation, expect_outbox_seq, now_ms, owner)` transaction을 두고 message의 generation/action/outboxSeq, nextAction=='create', due time, creating lease를 함께 CAS한다. stale old create, future-due create, same-seq duplicate를 각각 외부 0으로 테스트한다.

### H7-03 · 계획이 방출하는 privacy/orphan metric의 IAM과 alarm이 없다

`31-09`는 VisualCleanupBlocked와 pair conflict metric/alarm을 요구하고, `31-10` pipeline은 VisualOrphanSourceObject를 `PutMetricData`로 방출한다. 그러나 template에서 cloudwatch:PutMetricData는 dispatcher에만 있다. worker/pipeline 권한과 VisualCleanupBlocked/PairConflict alarm은 없다.

**제가 처리한다면:** worker와 pipeline에 namespace 제한이 가능한 범위의 PutMetricData 권한을 추가하고 `VisualCleanupBlockedAlarm`, `VisualPairConflictAlarm`을 IaC에 만든다. orphan alarm과 함께 metric call 실패를 business path에서 삼키되 로그로 남기고, IAM simulate/build test에 세 producer를 포함한다.

### H7-04 · orphan compensation의 “cleanup queue”가 로그 또는 optional 문서라 durable하지 않다

`31-10-PLAN.md:133`은 delete 보상 실패 시 “로그 + 옵션 Firestore visualOrphans”라고 한다. optional 기록은 계약이 아니며, 그 문서를 소비하는 dispatcher/janitor/운영 스크립트도 없다. metric alarm은 탐지일 뿐 삭제 주체가 아니다.

**제가 처리한다면:** deterministic `visualOrphans/{hash(bucket,key)}` 문서를 필수 기록하고 EventBridge janitor가 재시도하도록 한다. 상태/attempt/nextRetryAt/lastError를 두고 삭제+HEAD 404 후 문서를 닫는다. list_stuck_visual_jobs.py에도 orphan 조회/재구동을 추가한다.

### H7-05 · 31-01 smoke의 S3 임시 입력이 새 버킷 전환과 동기화되지 않았다

`31-01-PLAN.md:110`은 `visual-input/_smoke/`에 PUT 후 단순 delete만 한다. bucket 이름, versioning 상태, list-after-delete 검증이 없다. 기존 VideoBucket을 쓰면 versioned object가 남고, 신규 VisualInputBucket을 쓰려면 B7-06 provisioning이 Wave 1보다 먼저 와야 한다.

**제가 처리한다면:** Wave 0 bucket checkpoint 뒤 31-01이 전용 VisualInputBucket만 사용하도록 의존성을 바꾸고, 각 smoke 호출의 exact key delete + HEAD 404 + bucket Status 부재를 기록한다. fixture가 실사용자 자료가 아니더라도 같은 privacy 경계를 적용한다.

### H7-06 · D-06의 “완료 알림”이 구현 계획에서 빠졌다

`31-CONTEXT.md:29`는 회전 영상이 온디맨드 + 완료 알림이라고 결정했다. `31-11-PLAN.md`는 Firestore onSnapshot으로 화면이 열린 동안 카드만 갱신하며 push/local notification 등록·전송·권한·deep link가 없다.

**제가 처리한다면:** 제품 의도를 다시 확인하지 않고 축소하지 않는다. 기존 push infrastructure가 있으면 terminal rotation finalize 뒤 outbox로 완료 알림을 보내고 analysis result deep link를 연결한다. 인프라가 없으면 D-06을 “결과 화면이 열려 있을 때 실시간 갱신”으로 변경할지 belle decision checkpoint를 추가한다. 현재 문구로는 phase goal 미충족이다.

### H7-07 · optional 학습 pair retry가 사용자 표시와 raw input cleanup을 지연시킨다

postprocess는 pair 저장을 먼저 최대 3회 재시도한 뒤 input cleanup/finalize를 수행한다. 학습 저장소 장애가 사용자 correctedPose 표시와 개인정보 삭제 시간을 함께 늘린다. pair는 부산물인데 core user path의 availability/privacy critical path가 됐다.

**제가 처리한다면:** display canonical 성공과 input cleanup을 먼저 끝내고 user job을 finalize한다. pair 적재는 별도 durable pair outbox로 분리하되 필요한 before bytes를 privacy 정책상 허용된 별도 short-lived staging 또는 한 번의 atomic pair attempt로 넘긴다. 분리를 원치 않으면 pair network 실패는 즉시 failed 저장 상태로 기록하고 cleanup/finalize를 진행하며 별도 운영 재처리만 허용한다.

### H7-08 · canonical copy의 sha256 metadata 보존 계약이 불완전하다

`31-09-PLAN.md:134`는 staging을 canonical로 copy하며 다음 replay에서 `Metadata sha256==afterHash`를 검사한다. 하지만 copy 시 MetadataDirective와 metadata map을 명시하지 않는다. 구현자가 ContentType을 새로 주면서 REPLACE를 쓰고 sha256을 누락하면 다음 재실행은 정상 객체를 integrity conflict로 처리한다.

**제가 처리한다면:** `copy_object(..., MetadataDirective='REPLACE', Metadata={'sha256': afterHash}, ContentType='image/png')`처럼 결과 metadata를 명시하고 HEAD로 hash/content-type/size를 검증한 뒤 postprocessing에 진입한다. copy response loss 재실행도 put/copy 0으로 테스트한다.

### H7-09 · bucket versioning drift를 flag ON 직전에만 수동 확인하고 지속 감시하지 않는다

전용 bucket은 한 번 versioning이 Enabled되면 다시 진짜 unversioned로 돌아갈 수 없다. 현재 계획은 dry-run/checkpoint 시점 검사뿐이고 이후 관리자 변경을 탐지하는 Config/CloudTrail alarm이나 deploy 전 반복 gate가 없다.

**제가 처리한다면:** 최소한 모든 deploy/flag ON 전에 Status key 부재를 재검사한다. 가능하면 AWS Config custom rule 또는 EventBridge CloudTrail rule로 PutBucketVersioning/ObjectLockConfiguration을 탐지해 feature flag를 OFF하고 alarm한다. application roles에는 해당 mutation 권한을 주지 않는다.

---

## 5. MEDIUM

### M7-01 · Object Lock 확인은 HEAD 응답 필드 추정 대신 전용 API를 직접 호출하는 편이 명확하다

31-12 canary는 head_object에서 retention/legal-hold 세 필드를 본다고 적는다. 권한 검증 목적이라면 `get_object_retention`과 `get_object_legal_hold`를 직접 호출하고 “설정 없음” 정상 응답/예외 코드를 명시하는 편이 오판 가능성이 낮다.

**제가 처리한다면:** PUT VersionId → get_object_retention → get_object_legal_hold → version delete → list versions 0의 명시적 순서로 바꾼다.

### M7-02 · srcKey가 full hash가 아니라 64-bit prefix라 불필요한 collision block 경로가 남는다

full metadata 비교로 overwrite는 막지만 `sourceHash[:16]` collision이면 정당한 다른 입력도 job 0으로 차단된다. key 길이 비용이 작은 전용 prefix에서는 full 64 hex를 쓰는 편이 단순하다.

**제가 처리한다면:** srcKey에 full sha256을 사용하고 legacy가 없으므로 마이그레이션 없이 단일 계약으로 고정한다.

### M7-03 · E2E/완료 문구에 “multi-version exact-prefix”가 남아 새 아키텍처와 충돌한다

`31-12-PLAN.md:129,155`의 이름/done은 여전히 multi-version이라고 쓰지만 실제 acceptance는 non-versioned KeyCount 0이다. 실행자가 version-aware 검증을 다시 섞을 수 있다.

**제가 처리한다면:** 임시 입력은 “multi-object exact-prefix”로, 학습 pair만 “multi-version”으로 용어를 분리한다.

### M7-04 · cleanup canary가 helper 단독과 실제 worker role 경로를 구분하지 않는다

31-12의 non-sensitive 2+ object setup은 helper 논리를 증명하지만 helper를 관리자 credential로 직접 호출하면 B7-01 같은 worker IAM 오류를 놓친다.

**제가 처리한다면:** helper unit canary와 deployed worker-role E2E를 분리 기록하고, 실제 E2E-A job prefix cleanup은 worker CloudWatch request ID와 IAM role로 증명한다.

### M7-05 · 31-02 objective 번호와 일부 승인 문구가 6차 상태를 정확히 반영하지 않는다

objective에 3번이 중복되고 VALIDATION은 done privacy validator만 추적한다. 구조적 실행 오류는 아니지만 다음 replanner가 failed invariant를 놓치기 쉽다.

**제가 처리한다면:** 번호를 정리하고 §7 조건을 “correctedPose terminal(done|failed) 공통 cleanup 증명”으로 바꾼다.

---

## 6. 제가 적용할 targeted replan

범위를 넓히지 않고 다음 순서로 수정한다.

1. **31-12/31-01 — bucket 선행 provision gate:** 신규 bucket 생성/검증을 Wave 0으로 이동하고 smoke가 같은 bucket을 사용하게 한다.
2. **31-10/31-12 — versioning·lifecycle 형상:** Status 부재만 허용, Suspended 차단, bucket별 before/merged 4파일과 compensating rollback을 만든다.
3. **31-10 — IAM:** worker ListBucket, worker/pipeline metric 권한, 필요한 alarms와 실 role canary를 추가한다.
4. **31-02/31-09 — privacy finalizer:** cleanupVerified candidate 병합 방식을 고정하고 correctedPose done/failed 공통 validator를 적용한다.
5. **31-10 — upload hard-crash recovery:** PUT 전 durable reservation 또는 S3 event janitor를 추가하고 object별 created set을 둔다.
6. **31-09 — create 특례:** internal transition send 금지 + inbound seq/generation/due CAS를 함수로 고정한다.
7. **31-09/10 — operations:** orphan janitor, cleanup/pair conflict metric+alarm, bucket versioning drift gate를 실 운영 주체와 연결한다.
8. **31-11 또는 CONTEXT — D-06:** 완료 알림을 구현하거나 사용자 decision으로 요구를 수정한다.
9. **31-VALIDATION:** 아래 fault/IAM/live matrix를 task별 automated/manual gate에 연결한다.

### 수정 후 필수 fault/IAM matrix

| # | 시나리오 | PASS 기준 |
|---|---|---|
| 1 | worker role로 exact-prefix ListObjectsV2 | s3:ListBucket allowed, 타 prefix denied, cleanup/finalize terminal |
| 2 | bucket Status=Suspended | dry-run/checkpoint/flag ON 모두 blocked |
| 3 | bucket Status key 부재 | unversioned gate 통과 + Versions/DeleteMarkers 0 |
| 4 | remainingObject 0, job cleanupVerified=0에서 done finalize | 같은 transaction candidate에 timestamp 기록 후 done 성공 |
| 5 | correctedPose failed + cleanupVerified=0/inputSealed=False | finalizer ValueError, analysis terminal 0 |
| 6 | src PUT 직후 hard crash | durable reservation/janitor가 lifecycle 대기 없이 prefix 0 |
| 7 | src 성공→trainingSrc 실패 | 이번 invocation 생성 key 전부 정리 또는 durable orphan 등록 |
| 8 | terminal cleanup 뒤 stale producer PUT→hard crash | janitor가 object 0으로 복구 |
| 9 | VisualInputBucket 미존재 | 승인 전 create 금지, 승인 후 보안 속성+Status 부재 검증 |
| 10 | 두 bucket lifecycle apply 중 두 번째 실패 | 첫 bucket 포함 둘 다 before 상태 rollback |
| 11 | creating internal transition | SQS send 0, action null 메시지 0 |
| 12 | old create seq가 retry_ready에 도착 | due/seq CAS 실패, vendor create 0 |
| 13 | cleanup_blocked/orphan/pair conflict metric | 실제 producer role PutMetricData allowed + alarm 존재 |
| 14 | 회전 앱을 닫은 뒤 완료 | D-06이 유지되면 notification 수신+result deep link, 아니면 amended decision 존재 |

---

## 7. 실행 허용 기준

다음이 모두 계획 문구·테스트·IaC에 반영되기 전에는 Wave 1 실행을 허용하지 않는다.

- [ ] Worker bucket ARN `s3:ListBucket` + prefix condition + live simulate/canary
- [ ] VisualInputBucket `Status` key 부재만 허용; Suspended fixture blocked
- [ ] correctedPose done cleanupVerified handoff가 한 가지 원자 계약으로 고정
- [ ] correctedPose failed도 inputSealed+cleanupVerified 공통 validator 통과 후만 terminal
- [ ] PUT 직후 hard crash용 durable cleanup 주체 존재
- [ ] srcKey/trainingSrcKey별 created ownership과 partial compensation 존재
- [ ] 신규 bucket create/보안 설정/존재 검증이 Wave 0 checkpoint에 존재
- [ ] bucket별 lifecycle before/merged 파일과 교차 rollback 존재
- [ ] creating internal transition action-null send 0
- [ ] create inbound generation/action/outboxSeq/nextDispatchAt CAS
- [ ] worker/pipeline PutMetricData IAM + cleanup/orphan/pair-conflict alarms
- [ ] orphan registry가 필수 durable record이고 실제 consumer가 존재
- [ ] 31-01 smoke가 전용 unversioned bucket에서 delete+HEAD 404 검증
- [ ] D-06 완료 알림 구현 또는 명시적 amended decision
- [ ] 위 14개 시나리오가 `31-VALIDATION.md` task map에 연결

---

## 8. 최종 판단

**BLOCK — 7차 targeted replan이 필요하다.**

6차 수정은 claim/outbox/pair 쪽의 복잡한 문제를 상당히 잘 닫았다. 이번 차수의 blocker는 대부분 그 수정이 도입한 “전용 비-버저닝 bucket”을 실제 AWS resource, IAM, lifecycle, privacy finalizer와 끝까지 연결하지 못한 데서 나온다.

제가 실제 수정까지 맡는다면 위 §6 순서대로 31-01/02/09/10/12와 VALIDATION만 targeted 변경하고, 다른 03~08/11/13의 이미 닫힌 기하·judge·UI·calibration 계약은 건드리지 않는다. 특히 새 설계를 또 늘리기보다 다음 네 불변식으로 수렴시킨다.

1. VisualInputBucket은 **never-versioned(Status 부재)** 이고 실제 worker가 list/delete할 수 있다.
2. correctedPose는 done/failed 구분 없이 **cleanup 증명과 terminal이 하나의 검증 가능한 계약**이다.
3. upload-first의 어떤 하드 크래시에도 **job 또는 durable orphan record 중 하나가 반드시 남는다**.
4. bucket 생성·lifecycle 변경·rollback·metric alarm이 모두 **실행 가능한 명령과 실제 IAM 주체**에 연결된다.

이 네 조건이 닫히면 8차 리뷰에서는 새 기능 범위를 넓히지 않고 blocker closure와 fault matrix만 재검증하면 된다.
