# Phase 31 계획 6차 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-19  
**리뷰 범위:** 6차 개정된 `31-01-PLAN.md` ~ `31-13-PLAN.md`, `31-VALIDATION.md`, 1~5차 리뷰 및 계획이 직접 참조하는 현재 코드/IaC  
**리뷰 방법:** 5차 blocker/High별 closure 추적, claim owner 전달·outbox instance 교체 분석, dispatcher sent-recovery pagination 분석, upload/reserve/cleanup 3자 경쟁 분석, versioned S3 IAM 대조, cleanup retry terminal 규칙 및 pair partial-replay 검증  
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 리뷰 없이 직접 검토했다. AWS 공식 문서는 S3 conditional write·version 삭제·필수 IAM action 확인용 1차 자료로만 사용했다.  
**최종 판정:** **BLOCK / TARGETED REPLAN REQUIRED**

---

## 1. 결론

6차 개정은 5차 지적을 광범위하게 반영했다.

- claim을 `claimed/busy/stale/completed` 4상태로 분리했다.
- owner CAS와 갱신 snapshot 반환을 transition/finalize 계약에 추가했다.
- claim crash 복구용 sent+lease-expired dispatcher 경로를 추가했다.
- source conditional PUT, staging/canonical hash reuse, exact-prefix version cleanup을 도입했다.
- pairId/HMAC key version을 postprocessing 진입 시 고정하고 meta-read 멱등성을 추가했다.
- 저장 직전 consent 재확인, durable pair/cleanup self-loop, 성공·실패 전부 postprocessing 경유를 반영했다.
- dispatcher cursor, truncated alarm, Object Lock 실 delete canary를 추가했다.
- 5차의 High/Medium 대부분도 테스트 matrix에 연결했다.

하지만 새 계약 내부에 실제 실행을 막거나 개인정보 잔존을 허용하는 모순이 네 군데 남았다.

1. claim은 상태 문자열만 반환하는데 `_advance`는 claim 이전 `job.claimOwner`로 CAS한다. 정상 poll/fetch/judge/postprocess도 전이에 실패할 수 있다. 새 outbox instance 생성 시 claim 필드를 clear한다는 계약도 없다.
2. worker/pipeline IAM에 `ListObjectVersions`와 version 지정 삭제에 필요한 action이 없다. exact-prefix cleanup과 terminal replay delete가 실 AWS에서 403이 된다.
3. postprocess가 prefix 0을 확인한 직후 pipeline replay가 source를 다시 만들 수 있다. existing nonterminal job이면 새 VersionId를 삭제하지 않으므로 terminal 뒤 PII가 남는다.
4. cleanup max retry 뒤 `cleanup_blocked`여도 terminal finalize를 허용한다. 이는 “remainingVersionCount==0 뒤 finalize”라는 핵심 privacy invariant를 직접 위반한다.

따라서 5차의 세 핵심 불변식 중 pair-store 멱등성은 폐쇄됐지만, crash-resumable claim과 version 잔존 0은 아직 폐쇄되지 않았다.

### 발견 수

| 심각도 | 수 | 의미 |
|---|---:|---|
| BLOCKER | 4 | Wave 1 실행 전 계약 수정 필수 |
| HIGH | 9 | 같은 targeted replan에서 해결 필요 |
| MEDIUM | 5 | 배포 전 명시·검증 보강 필요 |

---

## 2. 5차 리뷰 지적 해소 추적

| 5차 ID | 6차 상태 | 판단 |
|---|---|---|
| B5-01 claim lease recovery | **부분 해소** | 4상태·busy ACK 금지·owner CAS·dispatcher 복구 방향은 맞음. claim 결과 snapshot 부재, claim field rollover 부재, sent scan 범위 문제로 정상 전이/복구가 아직 깨짐 |
| B5-02 untracked S3 versions | **부분 해소** | source conditional PUT·staging reuse·exact-prefix cleanup 추가. IAM action 누락, producer-vs-cleanup race, cleanup_blocked terminal 허용으로 잔존 0 미보장 |
| B5-03 pair-store 재실행 멱등 | **대체로 해소** | caller-fixed pairId/keyVersion + meta-read skip + hash meta 반영. partial object 재개 시 기존 payload 검증 계약이 High로 남음 |
| H5-01 consent race | **해소** | postprocess PUT 직전 current consent 재read + revoked 분기 테스트 |
| H5-02 durable postprocess retry | **부분 해소** | pairAttempt/cleanupAttempt self-loop 반영. cleanup max 뒤 terminal 허용이 새 blocker |
| H5-03 requestKey generation | **해소** | transition 내부 새 generation으로 생성·snapshot 반환·suffix test |
| H5-04 create 후속 snapshot | **부분 해소** | create 경로 snapshot 사용은 반영. claimed action은 claim 후 snapshot을 얻지 않아 owner CAS가 실패 |
| H5-05 failure cleanup | **해소 방향** | correctedPose 모든 terminal intent가 postprocessing 경유. cleanup 실패 terminal 규칙은 미해소 |
| H5-06 dispatcher max_scan | **부분 해소** | pending cursor·1,200건 test·alarm 반영. sent recovery scan에는 동등한 cursor/현재 claim 필터가 없음 |
| H5-07 Object Lock canary | **해소 방향** | PUT→VersionId→HEAD→delete→versions 0 checkpoint 반영. retention/legal-hold 조회 IAM 명시 필요 |
| H5-08 committed payload validation | **해소** | meta + before/after existence/hash/size 검증, quarantine, pagination 반영 |
| M5-01 decode reason | **해소** | oversize와 corrupt/format mismatch typed 분리 |
| M5-02 media type exact match | **해소** | 정규화 후 exact membership + adversarial test |
| M5-03 PIL 전역값 | **해소** | 모듈 import 시 한 번 고정 |
| M5-04 canonical replay versions | **부분 해소** | HEAD/hash reuse 추가. hash 불일치 overwrite 정책이 High로 남음 |
| M5-05 pair listing pagination | **해소** | 1,000+ fixture와 payload verify helper에 연결 |

---

## 3. BLOCKERS

### B6-01 · claim owner가 실행 snapshot에 전달되지 않아 claimed action의 정상 전이 자체가 실패한다

**근거**

- `31-02-PLAN.md:129`의 `claim_visual_job_action` 반환형은 `str`이다. transaction은 Firestore의 `claimOwner=aws_request_id`를 갱신하지만 호출자에게 갱신 job snapshot을 반환하지 않는다.
- `31-09-PLAN.md:98`의 `_advance`는 `expect_claim_owner=job.get('claimOwner')`를 넘긴다.
- `_action_poll/_fetch/_judge/_pose_check/_postprocess`가 받은 `job`은 claim transaction 이전 snapshot이라는 구조다. claim 뒤 re-read 또는 owner 인자 주입이 명시되지 않았다.
- `transition_visual_job`은 owner가 지정되면 `job.claimOwner`와 `claimedOutboxSeq==expect_outbox_seq`를 모두 요구한다.

**재현 순서 A — 정상 poll**

1. poll message를 받을 때 local job은 `claimOwner=None` 또는 이전 action owner를 가진다.
2. claim transaction이 Firestore에 `claimOwner='request-B'`를 기록하고 문자열 `'claimed'`만 반환한다.
3. `_action_poll(job)`이 외부 poll을 성공한다.
4. `_advance`는 claim 이전 `job.get('claimOwner')`를 `expect_claim_owner`로 전달한다.
5. Firestore의 현재 owner와 다르므로 transition은 `None`을 반환한다.
6. vendor poll은 성공했지만 job은 다음 state로 진행하지 못한다.

**재현 순서 B — moderation retry create**

1. poll action이 seq 5를 owner A로 claim한다.
2. `polling → retry_ready`가 seq 6 create outbox를 만든다.
3. transition이 claim fields를 clear한다는 계약은 없다. job에는 `claimedOutboxSeq=5`, `claimOwner=A`가 남는다.
4. create는 claim을 사용하지 않지만 `_advance`는 snapshot의 owner A를 넘기고 `expect_outbox_seq=6`을 사용한다.
5. owner CAS 내부의 `claimedOutboxSeq != expect_outbox_seq` 때문에 retry_ready→creating이 실패한다.

**영향**

create를 제외한 거의 모든 정상 action이 외부 side-effect 후 고착될 수 있고, moderation retry는 벤더 create 전에 막힐 수 있다. 5차 B5-01의 복구 설계를 구현하면 오히려 happy path가 깨지는 수준의 blocker다.

**제가 해결한다면**

- claim 반환형을 `{"status": ..., "job": updated_snapshot}`으로 바꾸거나 최소한 `{status, owner, outboxSeq, leaseExpiresAt}`를 반환한다.
- handler는 `claimed`일 때 반드시 claim이 반환한 snapshot만 action에 전달한다. 더 단순한 방법은 `_advance(..., claim_owner=aws_request_id)`로 현재 owner를 명시하되 job도 claim 후 re-read한다.
- transition/finalize는 `expect_claim_owner`, `expect_outbox_seq`, `now_ms < claimLeaseExpiresAt`을 함께 검증한다.
- **현재 action의 transition이 새 outboxSeq를 만들 때 다음 action용 claim fields를 원자 clear**한다: `claimState=None`, `claimOwner=None`, `claimLeaseExpiresAt=0`. `claimedOutboxSeq`는 audit용으로 유지해도 되지만 새 seq와 같아서는 안 된다.
- create action은 claim CAS를 사용하지 않고 state/outboxSeq + 기존 creating lease로만 보호한다. retry_ready snapshot에는 이전 claim owner가 남지 않아야 한다.
- 테스트: claimed poll happy path, poll→retry_ready→create, postprocess self-loop, claim 후 re-read 금지 정적 검사, 새 outbox snapshot claim fields clear를 추가한다.

---

### B6-02 · exact-version cleanup에 필요한 S3 IAM action이 IaC에서 빠져 있어 실 배포에서 403이 된다

**근거**

- `31-09-PLAN.md:130`은 `list_object_versions`로 모든 Versions/DeleteMarkers를 열거하고 VersionId 지정 삭제한다.
- `31-10-PLAN.md:130`의 worker policy는 `Get/Put/Delete(visual-input/*)`만 적고, pipeline policy도 `Put/Delete(visual-input/*)`만 추가한다.
- template acceptance는 Pipeline `s3 Delete(visual-input)`만 확인하며 version action을 검사하지 않는다.
- AWS는 `ListObjectVersions`에 `s3:ListBucketVersions`, versionId를 지정한 삭제에 `s3:DeleteObjectVersion`이 필요하다고 명시한다. 일반 `s3:DeleteObject`만으로는 version 지정 영구 삭제 권한이 충족되지 않는다.

공식 근거: [Required permissions for Amazon S3 API operations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html), [Listing objects in a versioning-enabled bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/list-obj-version-enabled-bucket.html), [Deleting object versions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjectVersions.html)

**영향**

- worker exact-prefix cleanup이 list 단계 또는 delete 단계에서 403이 된다.
- pipeline terminal replay의 `delete_object(VersionId=...)`도 403이 된다.
- cleanup retry가 5회 반복된 뒤 `cleanup_blocked` 경로로 빠지고 PII가 남는다.
- unit mock은 IAM을 검증하지 않으므로 전 테스트가 green이어도 live E2E에서만 실패한다.

**제가 해결한다면**

IaC에 최소 권한을 명시적으로 추가한다.

```text
VisualWorkerFunction
  bucket ARN:
    s3:ListBucketVersions
    Condition s3:prefix = visual-input/*
  object ARN visual-input/*:
    s3:GetObject
    s3:PutObject
    s3:DeleteObject
    s3:DeleteObjectVersion

PipelineFunction
  object ARN visual-input/*:
    s3:GetObject        # HEAD
    s3:PutObject
    s3:DeleteObject
    s3:DeleteObjectVersion
```

- `sam build` 산출 template과 `iam simulate-principal-policy` checkpoint에서 네 action을 실제 ARN으로 검증한다.
- worker의 `ListBucketVersions`가 bucket ARN에, DeleteObjectVersion이 object ARN에 붙는지 test한다.
- Object Lock canary 주체에는 별도로 `s3:GetObjectRetention`과 `s3:GetObjectLegalHold` 조회 권한도 확인한다.

---

### B6-03 · pipeline replay가 cleanup의 “remaining 0” 확인 뒤 source를 재생성할 수 있다

**근거**

- `31-09-PLAN.md:130`은 postprocess가 exact prefix를 삭제하고 재조회 0이면 finalize한다.
- `31-10-PLAN.md:129`은 pipeline이 job 존재 여부를 확인하기 전에 conditional source PUT을 수행한다.
- PUT 후 reserve가 existing nonterminal을 반환하면 `createdThisInvocation=True`여도 “진행 중 job의 입력”이라며 삭제하지 않는다.
- cleanup과 producer write 사이에 S3/Firestore를 묶는 transaction이나 `cleanupStarted/inputSealed` gate가 없다.

**재현 순서**

1. postprocess가 `visual-input/{uid}/{analysisId}/`의 모든 version을 삭제한다.
2. postprocess가 재조회하여 `remainingVersionCount=0`을 얻는다.
3. finalize 직전 pipeline replay가 실행된다. 현재 key가 없으므로 `IfNoneMatch='*'` PUT이 성공해 새 V3를 만든다.
4. reserve는 existing state=`postprocessing`을 반환한다.
5. 현재 계획은 progressing job이면 V3를 삭제하지 않는다.
6. postprocess는 이미 얻은 remaining=0을 근거로 job/analysis를 done 또는 failed로 finalize한다.
7. V3 개인정보가 terminal 뒤 남는다.

conditional write는 동시 overwrite를 막을 뿐 cleanup 이후의 새 write를 봉쇄하지 않는다. versioned bucket에서 overwrite/write는 새 version을 생성한다. 공식 근거: [How S3 Versioning works](https://docs.aws.amazon.com/AmazonS3/latest/userguide/versioning-workflows.html), [S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)

**영향**

E2E 단일 실행은 PASS할 수 있지만 pipeline 재전달과 postprocess가 겹치면 terminal 상태에서 PII가 남는다. “exact-prefix Versions/DeleteMarkers 0 뒤 finalize”를 시간적으로 보장하지 못한다.

**제가 해결한다면**

- producer에 read-only preflight를 추가한다. job이 어떤 state로든 이미 존재하면 source PUT을 하지 않고 기존 outbox 처리만 한다. 최종 권위는 reserve transaction이 유지한다.
- preflight와 PUT 사이의 race를 위해 reserve 결과 후 **이번에 만든 VersionId와 existing job payload의 selected VersionId를 비교**한다.
  - exact match면 job이 선택한 입력이므로 유지한다.
  - 불일치면 existing state가 reserved/진행중/terminal인지와 무관하게 이번 invocation VersionId를 즉시 삭제한다.
- reserve 예외/commit response loss는 job을 재read해 selected VersionId 일치 여부를 판정한다. job이 없거나 다른 version을 선택했으면 이번 version을 삭제한다.
- postprocessing 진입 시 Firestore에 `inputSealed=True`를 기록하고 producer가 이를 hard gate로 사용할 수 있다. 다만 preflight race 때문에 VersionId 비교 cleanup도 함께 필요하다.
- fault test는 정확히 “cleanup 재조회 0 후 finalize 전 producer PUT”에 barrier를 걸고 terminal 뒤 versions 0을 검증한다.

---

### B6-04 · cleanup max retry 후 잔존 PII가 있어도 terminal finalize를 허용한다

**근거**

- `31-09-PLAN.md:130`은 remaining이 0이 아니면 최대 5회 self-loop 후 `pendingFailureReason='cleanup_blocked'`로 승격한다.
- 같은 문장은 “remaining==0 **또는 cleanup_blocked** 후에만 finalize”라고 적어 잔존이 있는 terminal을 허용한다.
- `pendingTerminalState`를 failed로 바꾼다는 계약도 없다. 원래 성공 경로라면 `done + cleanup_blocked + canonicalKey` 조합이 가능하다.
- `finalize_visual_job`은 done일 때 `failure_reason is None` 또는 `remainingVersionCount==0`을 검증하지 않는다.
- `cleanup_blocked` 이후 자동 재시도, alarm, 운영자 cleanup command도 없다.

**영향**

privacy cleanup 실패가 사용자-visible done으로 끝날 수 있고, terminal이 된 뒤 dispatcher가 재시도하지 않는다. lifecycle 1일은 방어층일 뿐 “즉시 version 잔존 0” 약속을 대체하지 못한다.

**제가 해결한다면**

- `remainingVersionCount > 0`이면 절대 terminal finalize하지 않는다.
- 상태 폭발을 피하려면 state는 `postprocessing`으로 유지하고 `privacyBlocker='cleanup_blocked'`, `nextAction='postprocess'`, 장기 backoff를 기록한다. 즉시 자동 retry max 이후에는 저빈도 retry + alarm + 운영자 remediation으로 전환한다.
- `VisualCleanupBlocked` metric/alarm과 exact job prefix만 정리하는 운영 스크립트를 추가한다.
- `finalize_visual_job` validator가 correctedPose에 대해 `cleanupVerifiedAtMs`, `remainingVersionCount==0`, `inputSealed=True`를 요구하도록 한다.
- done이면 `failure_reason is None`, failed이면 typed failure reason 필수로 모순 조합을 더 엄격히 거부한다.
- cleanup_blocked 해결 후 같은 postprocessing action이 re-list 0을 확인하고 그때만 원래 `pendingTerminalState`로 finalize한다.

---

## 4. HIGH

### H6-01 · sent recovery scan이 “현재 seq를 실제 claim했다가 만료된 job”만 고르지 않는다

`31-02-PLAN.md:132`는 `dispatchState='sent' + claimLeaseExpiresAt<now`만으로 복구 대상을 설명한다. 새 outbox는 claim fields clear 계약이 없고 최초 job의 lease는 0이므로 아직 worker가 claim하지 않은 정상 sent message도 즉시 매분 재발행될 수 있다. 반대로 sent 문서가 1,000개를 넘을 때 이 별도 scan에는 durable cursor가 없어 뒤쪽 expired claim이 계속 누락될 수 있다.

**해결:** 복구 조건을 `claimedOutboxSeq==outboxSeq AND claimState=='claimed' AND 0<claimLeaseExpiresAt<=now`로 고정한다. pending cursor와 별도의 sent cursor를 두거나 필요한 composite index를 IaC로 배포한다. 1,200개 sent 중 마지막 expired claim, unclaimed sent 0 재발행, current seq 불일치 0 재발행을 테스트한다.

### H6-02 · source PUT 성공 후 reserve 실패/분석 부재 경로의 orphan compensation이 없다

upload-first는 reserve 전에 object를 만든다. reserve가 transaction commit 전 실패하거나 analysis_missing을 반환하면 job/postprocess 주체가 없는데 `createdThisInvocation` version을 지우는 계약이 없다. commit response loss에서는 무조건 삭제도 위험하다.

**해결:** 예외 후 job 재read → selected VersionId가 이번 version과 같으면 유지, job 부재/다른 version이면 삭제한다. compensation delete 실패는 별도 orphan metric과 cleanup queue에 넣는다.

### H6-03 · staging/canonical 기존 hash 불일치를 overwrite하도록 허용한다

`31-09-PLAN.md:127/129`는 기존 object hash가 같으면 reuse하고 “아니면 put/copy”한다. deterministic key에서 hash가 다르다는 것은 vendor 비결정성, key collision, tampering 또는 이전 bug 신호다. overwrite는 새 version을 만들고 현재 job의 입력을 조용히 바꾼다.

**해결:** deterministic staging/canonical key가 존재하면서 hash가 다르면 overwrite하지 말고 typed `invalid_output`/integrity conflict로 차단한다. 새 generation을 명시적으로 선택할 때만 generation이 포함된 새 key를 쓴다.

### H6-04 · meta 없는 partial pair 재개 시 기존 before/after object의 hash 검증이 명시되지 않았다

`store_training_pair`는 meta 부재 시 conditional before/after PUT을 수행하고 “존재 시 재PUT 0”이라고 한다. hard crash로 before만 남았거나 같은 prefix가 변조된 경우, 412를 skip하려면 기존 payload가 이번 expected hash/size와 같은지 먼저 확인해야 한다.

**해결:** 각 conditional PUT 412마다 HEAD size + GET sha256을 검증한다. 일치하면 resume, 불일치면 `conflict`로 중단하고 meta는 쓰지 않는다. before commit 후 hard crash, after commit 후 hard crash, mismatched preexisting payload를 각각 테스트한다.

### H6-05 · pairId/HMAC key 선택 실패가 display 성공 경로까지 막을 수 있다

pose_check 성공 transition은 `pairEligible`과 별개로 `pairId + pairHmacKeyVersion`을 계산해 job에 넣는 것으로 기술되어 있다. 사용자가 opt-out했거나 training gate가 false여도 HMAC env가 잘못되면 display correctedPose의 postprocessing 진입이 실패할 수 있다.

**해결:** `pairEligible=False`면 pairId/keyVersion은 None으로 두고 display 경로를 계속한다. eligible=True인데 key config가 invalid하면 pairStoreStatus=`failed_config`, pair PUT 0, 제품 결과는 cleanup 후 done으로 허용한다. 이 정책을 테스트한다.

### H6-06 · ListObjectVersions pagination은 일반 continuation token이 아니라 key/version marker 쌍을 요구한다

계획 여러 곳이 `list_object_versions continuation token 끝까지`라고만 적는다. raw S3 API는 `NextKeyMarker`와 `NextVersionIdMarker`를 함께 이어야 하며, 둘 중 하나만 쓰면 동일 key의 다중 version 페이지에서 누락/반복이 생길 수 있다.

**해결:** boto3 paginator 사용을 고정하거나 `{KeyMarker, VersionIdMarker}` 쌍을 명시한다. 단일 key에 1,001 versions + delete markers가 있는 fixture로 전부 삭제되는지 검증한다.

### H6-07 · claim lease와 Lambda timeout 관계가 설명에만 있고 build gate가 없다

`VISUAL_CLAIM_LEASE_MS=360000`, worker timeout=300, visibility=1800의 현재 값은 타당하지만 template 변경 시 자동 검증이 없다. owner CAS도 lease가 아직 유효한지 확인하지 않는다.

**해결:** build test가 `WorkerTimeout*1000 < CLAIM_LEASE_MS < VisibilityTimeout*1000`을 강제한다. transition/finalize에 now를 주입해 owner+seq+unexpired lease를 함께 검증한다.

### H6-08 · Object Lock HEAD 검증에 필요한 retention/legal-hold 조회 권한이 checkpoint에 없다

AWS는 HeadObject의 retention mode/date와 legal hold status 반환에 각각 `s3:GetObjectRetention`, `s3:GetObjectLegalHold` 권한을 요구한다. 권한이 없으면 안전한 bucket도 canary가 불완전하거나 false block될 수 있다.

**해결:** canary 실행 주체의 두 조회 action과 `DeleteObjectVersion`을 simulate하고, HEAD 응답에 세 필드가 명시적으로 존재함을 요구한다. 권한 부재와 “lock 없음”을 같은 상태로 취급하지 않는다. 공식 근거: [HeadObject permissions](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html), [Object Lock permissions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-managing.html)

### H6-09 · E2E action은 multi-version 유발을 선택사항으로 쓰면서 acceptance는 필수라고 선언한다

`31-12-PLAN.md:137`은 “가능하면 재시도로 multi-version 유발”이라고 적지만 acceptance는 multi-version case 포함을 요구한다. 이대로면 실제로 version 1개만 만든 E2E도 수행자가 PASS로 해석할 수 있다.

**해결:** 비민감 fixture prefix에 의도적으로 2개 version + delete marker를 만든 뒤 job cleanup 또는 전용 동일 helper로 0을 확인하는 deterministic setup을 필수화한다. “가능하면”을 제거하고 version count before/after를 SUMMARY에 기록한다.

---

## 5. MEDIUM

### M6-01 · backlog_max_age_ms는 현재 scan window의 최고령이지 전체 backlog 최고령이 아니다

durable cursor가 max_scan 이후로 이동하면 현재 window 밖의 더 오래된 item을 볼 수 없다. metric 이름/문구를 `ScannedOutboxMaxAgeMs`로 낮추거나 별도 oldest query/index를 둔다.

### M6-02 · conditional PUT은 concurrent delete와 겹치면 409 Conflict도 반환할 수 있다

계획은 412만 재사용 경로로 처리한다. AWS 공식 문서는 concurrent request 상황에서 409가 가능하다고 설명한다. bounded retry 후 HEAD/hash 판정 계약을 추가한다. 공식 근거: [S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)

### M6-03 · busy duplicate를 기본 visibility 전체로 실패 처리하면 불필요한 DLQ/지연이 생긴다

가능하면 message visibility를 남은 lease + jitter로 조정하고 batch failure한다. duplicate busy가 maxReceiveCount를 소비해 DLQ alarm을 오염시키지 않는지 test한다.

### M6-04 · deterministic pair conflict를 3회 재시도하는 것은 의미가 없다

`conflict`는 transient failure가 아니라 기존 meta/payload 불일치다. 즉시 pairStoreStatus=`conflict` + alarm/quarantine으로 보내고, network/5xx만 backoff retry한다.

### M6-05 · DeleteObjects의 HTTP 성공만 믿지 말고 per-object Errors를 기록해야 한다

S3 multi-delete는 일부 key 실패를 response의 `Errors`에 담을 수 있다. re-list가 최종 안전망이지만, error code/key/version을 즉시 metric/log에 남기고 failed count를 cleanupAttempt 판단에 포함한다.

---

## 6. 제가 적용할 targeted replan

이번에도 전체 phase 재작성은 필요 없다. `31-02`, `31-07`, `31-09`, `31-10`, `31-12`, Validation만 수정하면 된다.

| 순서 | 대상 | 필수 수정 |
|---:|---|---|
| 1 | 31-02 | claim updated snapshot 반환, owner+seq+lease CAS, 새 outbox에서 claim fields clear, pending/sent 이중 cursor와 정확한 expired-claim filter |
| 2 | 31-10 | worker/pipeline version IAM action, selected VersionId 비교 compensation, existing-job preflight, reserve 예외 orphan 처리, lease/IAM build assertions |
| 3 | 31-09 | cleanup_blocked nonterminal 유지, cleanup alarm/운영 복구, mismatched staging/canonical overwrite 금지, pair config 비차단 분기 |
| 4 | 31-07 | partial existing payload hash 검증 후 resume, raw version pagination marker 쌍, conflict 즉시 quarantine |
| 5 | 31-12 | IAM simulate에 ListBucketVersions/DeleteObjectVersion/lock 조회 포함, deterministic multi-version E2E setup |
| 6 | 31-VALIDATION | claim happy path snapshot, poll→retry create, producer-after-cleanup race, IAM assertions, cleanup_blocked nonterminal, 1,200 sent scan 추가 |

### 수정 후 필수 fault/concurrency matrix

| 시나리오 | 기대 결과 |
|---|---|
| claim 직후 local pre-claim snapshot 보유 | action은 claim 반환 snapshot/explicit owner만 사용, 정상 transition 성공 |
| poll claimed → retry_ready → create | 새 seq claim fields clear, create transition 성공 |
| expired owner A 뒤 owner B 재claim, A late write | owner+seq+lease CAS 실패, B 결과 보존 |
| sent-unclaimed 1,200개 + 마지막 expired-claimed 1개 | unclaimed 재발행 0, expired claim은 cursor 순환 내 복구 |
| worker live IAM simulation | ListBucketVersions/Get/Put/Delete/DeleteObjectVersion expected ARN 전부 allowed |
| cleanup re-list 0 직후 pipeline replay PUT | 새 version이 selected VersionId와 불일치해 즉시 삭제, terminal 뒤 0 |
| reserve commit 전 실패 / commit response loss | job 재read 후 selected version만 유지, orphan 0 |
| cleanup 5회 실패 | job은 postprocessing/cleanup_blocked 유지, analysis pending, alarm 발생, terminal 0 |
| partial pair before-only/after-only 재개 | existing hash 일치만 resume, 불일치 meta PUT 0 |
| 단일 key 1,001 versions/delete markers | marker-pair pagination 후 exact 0 |
| Object Lock canary 권한 부재 | lock 없음으로 오판하지 않고 배포 STOP |

---

## 7. 실행 허용 기준

- [ ] claim 성공 호출자가 갱신된 owner/lease snapshot을 받음
- [ ] claimed action happy path transition/finalize가 owner CAS를 통과함
- [ ] 새 outboxSeq 생성 시 이전 claim fields가 원자 clear됨
- [ ] sent recovery는 current seq의 expired claimed job만 대상으로 하고 별도 cursor가 있음
- [ ] worker에 `s3:ListBucketVersions`·`s3:DeleteObjectVersion`, pipeline에 `s3:DeleteObjectVersion`이 실제 ARN으로 허용됨
- [ ] producer가 만든 version과 job selected VersionId를 비교해 불필요 version을 state 무관하게 정리함
- [ ] cleanup 0 확인 뒤 producer write 경쟁 테스트가 terminal versions 0으로 끝남
- [ ] cleanup_blocked 상태에서 terminal finalize가 불가능함
- [ ] correctedPose finalize validator가 cleanup verified/count 0을 요구함
- [ ] partial pair object 재사용 전에 content hash를 확인함
- [ ] raw ListObjectVersions pagination이 KeyMarker+VersionIdMarker 또는 paginator로 고정됨
- [ ] live Object Lock canary 권한과 deterministic multi-version E2E가 필수 gate임

---

## 8. 최종 판단

6차 개정은 5차 리뷰를 피상적으로 반영한 문서가 아니다. claim 4상태, caller-fixed pairId, exact-prefix cleanup, consent 재확인, dual cursor 아이디어 등 핵심 방향은 상당히 좋아졌다. 특히 **B5-03 pair-store 멱등성은 실행 가능한 수준에 가까워졌다.**

그러나 현재 남은 네 blocker는 구현 세부가 아니라 핵심 불변식의 연결부 문제다.

- claim transaction의 owner가 worker 실행 snapshot으로 이어지지 않는다.
- exact version API와 IAM 권한이 연결되지 않는다.
- producer write와 cleanup의 시간 경쟁이 봉쇄되지 않는다.
- cleanup 실패를 terminal로 닫아 재시도 주체를 없앤다.

이 네 연결을 고치면 다음 리뷰는 범위를 더 넓힐 필요가 없다. 7차에서는 `claim owner handoff`, `version IAM`, `producer-cleanup race`, `cleanup_blocked nonterminal` 네 축의 closure와 그 fault test만 확인하면 실행 승인 여부를 판정할 수 있다.
