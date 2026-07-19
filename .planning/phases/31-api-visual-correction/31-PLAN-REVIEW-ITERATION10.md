# Phase 31 계획 10차 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-20  
**리뷰 기준 커밋:** `a3c3345` (`iteration9 targeted replan`)  
**리뷰 범위:** 9차에 수정된 `31-01-PLAN.md`, `31-02-PLAN.md`, `31-09-PLAN.md`, `31-10-PLAN.md`, `31-12-PLAN.md`, `31-CONTEXT.md`, `31-VALIDATION.md`와 Phase 31 전체 계획·1~9차 리뷰  
**리뷰 방법:** 9차 5 blocker/9 High/6 Medium closure 추적, reservation→ownership→PUT→reserve→worker cleanup→janitor delete의 전 시간축, 동일 key 다중 producer interleaving, janitor claim/delete crash, lifecycle Wave 0→dry-run→checkpoint 재적용, chosen bucket 배포 명령을 직접 대조  
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 리뷰 없이 직접 검토했다.  
**최종 판정:** **BLOCK / TARGETED REPLAN REQUIRED**

---

## 1. 결론

9차 수정은 이전 지적 중 다음 축을 실질적으로 닫았다.

- reservation/orphan janitor claim에 owner·lease·만료 후 재claim이 추가됐다.
- janitor 삭제 후보가 `expectedKeys ∪ createdKeys`로 통일됐다.
- reserve와 reservation claim은 내부 transaction helper를 공유하도록 구체화됐다.
- begin create full write set, orphan reopen, alarm 8종, create failure kind 분기가 정리됐다.
- chosen bucket 이름이 dry-run·lifecycle·IAM·Pod·E2E로 전파되기 시작했다.
- CONTEXT의 즉시삭제 SLA와 pair 단일 시도 결정은 명시적으로 고정됐다. 이 리뷰는 해당 제품 선택을 재개하지 않는다.

그러나 9차에 새로 도입한 `visualInputObjects` ownership 상태 머신은 아직 안전하지 않다.

1. expired reservation 자신의 ref가 `liveRefs`에 남아 있으므로 `live_ref_count==0` 조건을 스스로 영원히 만족하지 못한다.
2. count 확인 transaction이 끝난 뒤 S3 delete 전에 새 producer가 ref를 획득할 수 있다. object-level deleting fence가 없다.
3. 정상 worker cleanup과 여러 producer 보상 경로가 job/reservation ref를 release하지 않는다.
4. Wave 0 checkpoint는 설명·승인 절차에서는 lifecycle을 이연한다고 하면서 action에서는 live lifecycle을 변경한다. 이후 dry-run도 같은 rule을 idempotent하게 upsert한다고 명시하지 않는다.

즉, B9-02를 닫기 위해 추가한 ownership 문서가 현재 형태로는 cleanup을 영구 정지시키거나, 반대로 live input을 다시 삭제할 수 있다. Phase 31의 고정된 privacy SLA와 직접 충돌하므로 실행을 허용할 수 없다.

### 발견 수

| 심각도 | 수 | 의미 |
|---|---:|---|
| BLOCKER | 4 | raw input cleanup의 safety/liveness 또는 live mutation 승인 경계가 완결되지 않음 |
| HIGH | 7 | 같은 targeted replan에서 transaction·TTL·배포·검증 계약 보강 필요 |
| MEDIUM | 5 | stale 문구·artifact·검증 정합 보강 필요 |

---

## 2. 9차 리뷰 지적 해소 추적

| 9차 ID | 10차 상태 | 판단 |
|---|---|---|
| B9-01 janitor claim crash 복구 | **해소** | reservation/orphan 모두 claimOwner·lease·expired reclaim 시간축 반영 |
| B9-02 동일 key ownership | **미해소** | 역색인은 생겼으나 self-ref deadlock, delete fence 부재, release 누락으로 B10-01~03 발생 |
| B9-03 multi-object 후보 누락 | **해소** | `expectedKeys ∪ createdKeys`로 통일되고 두 번째 PUT 직후 crash test 반영 |
| B9-04 pair 제품 결정 limbo | **해소** | CONTEXT amend와 SETTLED 축으로 단일 시도 손실 수용 고정. 재개하지 않음 |
| B9-05 chosen bucket 전파 | **대체로 해소** | 주요 action은 `$VIB`로 전환. checkpoint shell 변수의 정의·fail-closed는 H10-05로 남음 |
| H9-01 reservation TTL gate | **부분 해소** | build inequality는 추가. 실제 숫자·clock·Firestore metadata TTL policy는 불완전(H10-02/03) |
| H9-02 janitor job predicate | **해소** | terminal/inputSealed/mismatched와 matching nonterminal unsealed 표가 반영됨 |
| H9-03 begin full write set | **해소** | outboxSeq+1, nextAction/dispatchState clear, acquired snapshot 사용 고정 |
| H9-04 nested reservation transaction | **부분 해소** | `_claim_reservation_for_job_tx`는 추가. ownership promote에는 같은 내부 tx 계약이 없음(H10-01) |
| H9-05 alarm resource | **해소** | 두 orphan alarm을 포함한 8 logical ID가 action/test/build gate에 반영됨 |
| H9-06 metadata reconciliation/TTL | **부분 해소** | deleteAfterMs·reconcile 문구는 추가. TTL policy와 timestamp type이 없어 실제 삭제되지 않음(H10-02) |
| H9-07 orphan reopen | **해소** | closed→open generation+1/attempt reset CAS 반영 |
| H9-08 Wave 0 hard-crash defense | **부분 해소** | 1일 rule action은 추가. checkpoint 승인 문구와 lifecycle 재적용이 모순(B10-04) |
| H9-09 create failure kind 분기 | **해소** | correctedPose는 postprocess, rotation은 direct finalize로 테스트까지 분리 |
| M9-01 unconditional finalizer 설명 | **해소** | objective/action/validator가 kind 기준 unconditional로 정리됨 |
| M9-02 Wave 0 validation 정합 | **부분 해소** | VALIDATION은 lifecycle 적용으로 바뀌었으나 31-01 task 설명·done은 이전 이연 문구 유지 |
| M9-03 alarm 개수 | **대체로 해소** | action은 8종. 31-12 must-have에 `7종` 오기가 남음(M10-02) |
| M9-04 lifecycle filename | **해소** | visual_input/video × before/merged 4파일로 통일 |
| M9-05 build artifact lockstep | **해소** | YAML parser 기반 logical ID/action/resource/condition 검사 반영 |
| M9-06 Wave 0 artifact | **부분 해소** | chosen/policy/wave0 파일은 frontmatter에 추가. 기존 bucket lifecycle before 파일은 이름·artifact가 없음(M10-01) |

---

## 3. BLOCKERS

### B10-01 · expired reservation이 자기 ownership ref 때문에 영원히 cleanup되지 않는다

**근거**

- `31-10-PLAN.md:139`는 PUT 전에 reservation ref를 각 key의 `liveRefs`에 추가한다.
- `31-02-PLAN.md:153-157`은 janitor delete 조건을 `key_ownership_live_ref_count(bucket,key)==0`으로 고정한다.
- expired A를 claim한 순간에도 A의 reservation ref는 liveRefs에 남아 있다. claim 또는 close가 해당 ref를 제거한다는 규칙은 없다.
- 문구는 괄호로 “다른 live ref 0”이라고 설명하지만 helper signature에는 `exclude_ref`, `delete_claim`, ref 상태 구분이 없다.
- 9차 test는 A와 B가 있을 때 B 때문에 count가 양수임만 확인한다. A 단독 expired reservation이 자기 ref를 제외하고 삭제되는 happy path를 고정하지 않는다.

**영향**

PUT 전 또는 PUT 후 hard crash한 모든 reservation은 자신의 ref 때문에 delete 조건을 통과하지 못한다. 즉시삭제의 최종 복구 주체인 janitor가 구조적으로 정지하고 raw frame은 1일 lifecycle까지 남는다.

**제가 처리한다면**

- 단순 count helper를 없애고 `claim_key_for_delete(bucket,key, deleting_ref, owner, lease)`를 둔다.
- transaction에서 expired reservation 자신의 ref는 제거/소비하고, **다른** live ref가 0인지 확인한 뒤 object doc을 `state='deleting'`으로 CAS한다.
- A-only는 delete claim 성공, A-expired+B-live는 실패, A ref 제거 commit 직후 crash는 lease 만료 후 재claim되는 세 시간축을 테스트한다.

---

### B10-02 · ownership count 확인과 S3 delete 사이에 새 producer를 막는 delete fence가 없다

**근거**

- `31-02-PLAN.md:157`은 ownership 문서 transaction에서 live ref 0을 확인한다고 하지만 실제 S3 delete는 transaction 밖에서 수행된다.
- `31-09-PLAN.md:158`은 reservation claim 성공 **후** key별 count를 다시 확인하고 delete한다고 적어, claim transaction과 ownership 판정의 원자성도 문서끼리 다르다.
- 가능한 시간축:
  1. janitor A가 ref 0을 확인하고 transaction commit.
  2. producer B가 `acquire_key_ownership(K)` 성공 후 K를 PUT/reuse.
  3. janitor A가 K를 delete.
  4. B가 reservation을 job으로 승격해 이미 삭제된 input을 참조.
- `visualInputObjects`에는 `active/deleting`, deleteOwner, deleteLeaseExpiresAt 같은 acquisition fence가 없다. `ownerGeneration`은 필드에만 있고 어느 CAS에도 사용되지 않는다.
- orphan sweep은 31-09 action에서 ownership check 자체가 빠진 채 claim→delete로 적혀 있다.

**영향**

B9-02가 막으려던 cross-reservation same-key 삭제 경쟁이 count-check 이후 구간에서 그대로 재현된다. 성공한 job이 없는 S3 input을 참조하고 vendor 실패·과금·privacy state 불일치가 발생한다.

**제가 처리한다면**

- object doc을 `active | deleting` 상태 머신으로 승격한다.
- janitor는 다른 live ref 0일 때 `deleting(owner, lease, generation)`을 원자 획득한 뒤에만 외부 delete한다.
- producer acquire는 deleting 동안 실패/재시도하고, lease 만료된 deleting만 새 owner가 회수한다.
- delete+HEAD404 뒤 object doc을 제거/closed 처리한다. delete 실패는 deleting lease/backoff를 유지한다.
- reservation과 orphan 모두 동일 helper를 사용하고, “janitor check commit → producer acquire → delete” barrier test에서 producer가 fence 해제 전 acquire하지 못함을 요구한다.

---

### B10-03 · 정상 worker cleanup과 producer 보상 경로가 ownership ref를 release하지 않는다

**근거**

- `31-09-PLAN.md:136`의 `_cleanup_visual_input`은 prefix list/delete/relist 후 finalize하지만 `release_key_ownership` 호출이 없다.
- reserve 성공 시 reservation ref는 job ref로 승격되므로 정상 correctedPose job마다 job liveRef가 남는다.
- `31-10-PLAN.md:139`은 terminal-replay 분기에서만 release를 명시한다. 다음 경로에는 release/close가 없다.
  - PUT/HEAD collision·일반 실패 후 return
  - option-b 두 번째 PUT 실패 보상 성공
  - analysis_missing 또는 reserve 예외 후 보상 delete 성공
  - orphan janitor delete 성공
  - reservation janitor delete 성공
- `close_reservation`과 `close_visual_orphan`도 ownership ref 제거를 원자적으로 수행한다고 정의하지 않는다.

**영향**

S3 object는 지워져도 ownership doc에는 live ref가 영구 잔존한다. 같은 deterministic key의 후속 orphan/reservation cleanup은 영원히 skip되고, bucket/key metadata도 남는다. self-ref 문제를 임시로 고쳐도 liveness가 다시 깨진다.

**제가 처리한다면**

- release를 호출자 선택사항이 아니라 상태 전이의 일부로 만든다.
- worker cleanup은 job payload의 모든 expected key에 대해 `release_key_ownership(ref=jobRef)`를 수행하고, S3 remaining 0과 ownership release 완료를 모두 terminal gate로 둔다.
- producer 보상 성공은 reservation close+ref release를 같은 Firestore transaction으로 완료한다.
- janitor delete 성공은 key delete claim close+reservation/orphan close+ref 소비를 일관된 finalize helper로 수행한다.
- 각 실패/성공 경로 종료 후 S3 count 0뿐 아니라 ownership liveRefs 0/object doc 제거도 테스트한다.

---

### B10-04 · Wave 0 checkpoint의 승인 범위와 실제 lifecycle mutation이 서로 반대다

**근거**

- `31-01-PLAN.md:110-115`의 task 이름·what-built·human verification은 “보안 속성만”, “lifecycle은 31-12로 이연”이라고 사용자에게 제시한다.
- 같은 task의 action/acceptance(`:118-127`)는 승인 뒤 Wave 0에서 live `put-bucket-lifecycle-configuration`을 수행한다.
- `<done>`도 다시 `lifecycle 제외`라고 적는다.
- 기존 bucket의 lifecycle before를 저장한다고 하지만 파일명이 frontmatter/artifact에 없고, lifecycle 미설정 시 `NoSuchLifecycleConfiguration`을 빈 Rules로 정규화하는 규칙도 없다.
- 31-10 dry-run은 Wave 0에 이미 존재하는 `visual-input-1d` rule을 보존하면서 같은 rule을 merge한다. ID/prefix 기준 replace/upsert가 명시되지 않아 duplicate ID 또는 중복 rule을 만들 수 있다.

**영향**

사용자는 lifecycle mutation이 없는 계획에 승인했는데 실행자는 live lifecycle을 바꿀 수 있다. 또는 실행자가 설명을 따라 mutation을 생략해 smoke hard-crash 방어가 사라진다. mutation을 수행해도 31-12 재적용이 invalid lifecycle로 실패할 수 있다.

**제가 처리한다면**

- Task 이름·what-built·how-to-verify·action·acceptance·done을 모두 “Wave 0에 VisualInput 1일 lifecycle 적용”으로 통일해 승인 범위를 정확히 제시한다.
- 기존 bucket용 `visual_input_wave0_lifecycle_before.json`을 명명해 frontmatter에 추가하고 NoSuchLifecycleConfiguration은 `{"Rules":[]}`로 정규화한다.
- merge는 `ID='visual-input-1d'` 또는 exact prefix를 찾아 replace/upsert하고, 동일 ID 중복·겹치는 prefix rule을 fail-closed한다.
- Wave 0 적용 후 31-10 dry-run→31-12 재적용을 두 번 실행해도 결과 hash가 같은 idempotence test를 추가한다.

---

## 4. HIGH

### H10-01 · key promotion은 reservation claim과 달리 transaction 내부 helper 계약이 없다

`31-02-PLAN.md:136,153-156`은 reserve transaction 안에서 `promote_key_ownership_to_job`을 호출해 job+reservation+두 object doc을 한 commit으로 만든다고 한다. 그러나 helper signature에는 transaction 인자가 없고, H9-04에서 reservation claim에 추가한 `_..._tx(transaction, ...)` 동형이 없다. 독립 transactional wrapper로 구현하면 nested transaction 또는 부분 commit 위험이 다시 생긴다.

**제가 처리한다면:** `_promote_key_ownership_to_job_tx(transaction, ...)`를 만들고 reserve가 모든 reservation/object/job read를 먼저 한 뒤 write하도록 고정한다. 두 key 중 하나의 conflict, transaction retry, commit response loss에서 job·reservation·두 object doc이 전부 이전 상태이거나 전부 승격된 상태만 허용한다.

### H10-02 · `deleteAfterMs`만 기록해서는 Firestore metadata TTL이 작동하지 않는다

`31-02-PLAN.md:143-152`는 closed reservation/orphan에 숫자형 `deleteAfterMs`를 쓰고 “Firestore TTL”이라고 부른다. 그러나 TTL policy를 어느 collection group/field에 활성화하는 task, IaC/명령, live checkpoint, 검증이 없다. 또한 TTL 대상으로 쓸 필드는 timestamp 타입으로 정의돼야 하는데 계약은 millisecond number다. `visualInputObjects`의 bucket/key metadata는 retention 자체가 없다.

**제가 처리한다면:** `expireAt` timestamp로 바꾸고 `visualInputReservations`, `visualOrphans` collection group별 TTL policy 활성화를 승인 checkpoint와 검증에 추가한다. emulator/unit은 field type을, live gate는 TTL policy 상태를 확인한다. ownership doc은 liveRefs 0/delete close 뒤 즉시 delete하는 쪽을 권고한다.

### H10-03 · reservation TTL 숫자와 clock 규칙이 아직 실행 가능한 계약이 아니다

`VISUAL_INPUT_RESERVATION_TTL_MS`는 “Pipeline timeout + margin”이라고만 정의되고 실제 숫자·margin·허용 clock skew가 없다. 동시에 “Firestore server timestamp 기준”과 caller `now_ms` 계산을 함께 요구한다. server timestamp는 commit 전 `leaseExpiresAt=server_now+TTL` 계산에 그대로 쓸 수 없으므로 구현자가 로컬 clock을 쓸 가능성이 크다.

**제가 처리한다면:** concrete TTL/claim lease/skew 값을 models에 고정하고 모든 비교에 UTC epoch milliseconds의 trusted service clock 하나를 사용한다. build gate는 단순 timeout뿐 아니라 최대 재시도/보상 구간까지 포함한다. expiry boundary `now==expiresAt`, ±skew test를 둔다.

### H10-04 · `liveRefs[]`는 ref identity와 상태가 부족하고 무제한 단일 문서 hotspot이 된다

reservationId/jobId 문자열만 한 배열에 넣으면 ref 종류·generation·expiry를 구분할 수 없다. crashed ref의 유효성 판정이 다른 collection 조회에 의존하고, 동일 key 재시도 누적으로 document size/transaction contention이 증가한다. 현재 `ownerGeneration`은 이 문제를 해결하는 데 사용되지 않는다.

**제가 처리한다면:** object doc에는 작은 상태와 현재 delete lease만 두고 ref는 deterministic child docs 또는 bounded map `{refId: {kind,generation,expiresAt}}`로 모델링한다. stale ref reconciliation과 max-ref invariant를 테스트하고, ownerGeneration은 acquire/delete CAS에 실제 사용하거나 제거한다.

### H10-05 · human deploy 명령의 `$VIB`가 같은 shell에서 정의되지 않고 template default가 fail-open이다

`31-12-PLAN.md:113`과 Task 4의 deploy 명령은 `$VIB`를 사용하지만 checkpoint의 동일 명령/스크립트에서 이를 설정하지 않는다. 이전 Task 2 주석의 shell 변수가 사람의 새 shell에 유지된다는 보장은 없다. 한편 template은 기본 bucket명을 Default로 가져 override 누락을 조용히 허용한다.

**제가 처리한다면:** repo-root helper가 JSON schema/region/name을 검증해 SAM override를 직접 구성하도록 하고 checkpoint는 그 단일 script를 호출한다. 또는 같은 명령에서 `VIB=$(jq -er ...)`를 설정·비어 있음 차단한다. `VisualInputBucketName`의 Default는 제거해 override 누락을 deploy 실패로 만든다. deploy 후 stack parameter exact match 검증을 유지한다.

### H10-06 · alarm threshold가 Python 상수 표현식으로만 적혀 CloudFormation 값이 정해지지 않았다

`31-10-PLAN.md:140`의 `VisualOrphanOldestAgeAlarm` threshold는 `VISUAL_INPUT_RESERVATION_TTL_MS×2`로 서술된다. CloudFormation template은 Python models 상수를 직접 평가하지 않는다. TTL 숫자도 미정이라 구현할 concrete Threshold가 없다.

**제가 처리한다면:** TTL과 alarm threshold를 한 생성 script/parameter source에서 파생하거나 template에 concrete numeric parameter를 두고 build test가 models 값과 exact 일치시키게 한다. Threshold/EvaluationPeriods/Period/DatapointsToAlarm/TreatMissingData를 모두 parser test로 고정한다.

### H10-07 · 새 ownership 위험을 검증하는 필수 barrier test가 VALIDATION에 없다

현재 §7은 A-expired+B-live에서 count>0만 요구한다. A-only self-ref, check commit 직후 B acquire, deleting claim 직후 janitor crash, worker cleanup 뒤 job ref 0, producer 보상 성공 뒤 reservation ref 0, orphan-vs-live-job을 다루지 않는다.

**제가 처리한다면:** 위 여섯 시나리오를 10차 실행 허용 조건으로 승격한다. 각 테스트는 S3 object 존재 여부와 Firestore reservation/orphan/object doc을 함께 assert하며, 단순 mock call count가 아니라 transaction barrier로 interleaving을 고정한다.

---

## 5. MEDIUM

### M10-01 · Wave 0 기존 lifecycle rollback artifact가 frontmatter에 없다

`31-01`은 기존 bucket lifecycle before 저장을 요구하지만 `visual_input_wave0_lifecycle_before.json` 같은 경로가 없다. 실행자는 임의 경로를 쓰거나 artifact를 남기지 않을 수 있다.

**제가 처리한다면:** 명시 파일을 `files_modified`와 acceptance에 추가하고 적용 전/후 hash, rollback 명령, 신규 bucket의 “before 없음” manifest를 남긴다.

### M10-02 · 31-12 must-have의 alarm 개수가 다시 틀렸다

`31-12-PLAN.md:16`은 “alarm 7종”이라고 쓰지만 괄호의 logical set은 8종이고 Task 1 action도 8종을 검사한다.

**제가 처리한다면:** 숫자 나열 대신 exact logical ID 표 하나를 참조하게 하고 문구를 8종으로 정정한다.

### M10-03 · 31-02 artifact/output 설명이 ownership helper를 반영하지 않는다

frontmatter의 firestore_admin `provides`, objective Output, success criteria는 여전히 reservation/orphan helper까지만 요약하거나 “핵심 함수 9종”으로 끝난다. 실행 범위가 긴 action 본문에만 ownership 구현이 존재한다.

**제가 처리한다면:** models/firestore artifact에 object path/state를, firestore_admin artifact에 acquire/promote/release/delete-claim helper를 명시하고 Output/acceptance를 같은 목록으로 맞춘다.

### M10-04 · threat model이 새 object ownership 상태 머신의 핵심 위협을 등록하지 않는다

31-02/09/10 threat register는 9차에 추가된 cross-reservation delete, self-ref liveness, delete-fence race, metadata retention을 다루지 않는다.

**제가 처리한다면:** privacy/availability 위협 ID를 추가하고 mitigation을 object delete lease+ref release+TTL policy+barrier test에 연결한다.

### M10-05 · VALIDATION은 아직 닫히지 않은 15조건을 승인 완료로 표시한다

`31-VALIDATION.md:284-295`는 9차 §7을 완비·nyquist compliant·planner approved로 표시하지만 핵심 조건 2/4/12는 실제로 self-ref/fence/release/TTL policy가 없어 만족하지 않는다.

**제가 처리한다면:** 10차 targeted replan 전 approval을 pending으로 되돌리고 10차 조건을 추가한 뒤에만 `nyquist_compliant: true`와 sign-off를 다시 선언한다.

---

## 6. 리스크별 제가 실제로 취할 처리 순서

1. **즉시 실행 차단:** 31-01 live lifecycle checkpoint와 31-02/09/10 privacy ownership 구현을 시작하지 않는다.
2. **object 상태 머신 단순화:** `active/deleting(lease)` + typed ref + atomic consume/release 모델을 먼저 확정한다.
3. **transaction 경계 고정:** reservation claim, 두 key promote, job create는 한 transaction; janitor는 ref consume+deleting claim을 한 transaction으로 만든다.
4. **외부 side-effect 복구:** delete 전/후 crash 모두 lease reclaim과 idempotent delete로 수렴하게 한다.
5. **모든 종료 경로 release:** worker 정상 cleanup, producer compensation, reservation janitor, orphan janitor 각각 liveRefs 0/object doc 제거를 증명한다.
6. **live mutation 승인 정합:** Wave 0 lifecycle 적용을 checkpoint 설명에 명시하고 before/merge/upsert/rollback을 idempotent하게 만든다.
7. **TTL·배포 fail-closed:** timestamp TTL policy를 live gate로 검증하고 chosen bucket override가 없으면 SAM deploy가 실패하게 한다.
8. **barrier test 후만 승인:** A-only/A+B/check→acquire/delete-crash/release/TTL/deploy alternative-name을 통과한 뒤 전체 test·SAM build를 실행한다.

---

## 7. 10차 targeted replan 필수 변경 파일

| 파일 | 필수 변경 |
|---|---|
| `31-01-PLAN.md` | Wave 0 lifecycle 승인 문구 통일, before artifact, NoSuchLifecycle 정규화, ID/prefix idempotent upsert |
| `31-02-PLAN.md` | object `active/deleting` lease, own-ref consume, tx 내부 promote, typed/bounded refs, release/finalize helper, timestamp TTL 계약 |
| `31-09-PLAN.md` | reservation/orphan 공통 delete-claim helper, janitor crash recovery, worker cleanup job-ref release |
| `31-10-PLAN.md` | producer 모든 return/보상 경로 release, deleting acquire fence, barrier tests, concrete TTL/alarm threshold, chosen-name deploy helper 전제 |
| `31-12-PLAN.md` | `$VIB` fail-closed resolution, template parameter default 제거 검증, TTL policy checkpoint, alarm count 정정 |
| `31-VALIDATION.md` | 10차 ownership/lifecycle/TTL/deploy fault matrix와 approval pending/재승인 |

CONTEXT의 SETTLED 두 축(즉시삭제 SLA, pair 단일 시도)은 수정 대상이 아니다. 구현을 그 결정에 맞게 닫는 것이 이번 replan의 범위다.

---

## 8. 다음 실행 허용 조건

아래가 계획과 테스트에 모두 박제되기 전 Phase 31 실행을 허용하지 않는다.

1. expired reservation A만 있는 key가 자기 ref를 소비하고 delete+close까지 수렴한다.
2. expired A와 live B가 같은 key를 공유하면 A는 deleting claim을 얻지 못한다.
3. janitor가 deleting claim한 뒤에는 새 producer acquire가 실패하고, delete close 뒤에만 재시도 성공한다.
4. deleting claim 직후 crash와 delete 성공 직후 crash가 lease 만료 후 재claim되어 최종 S3 0/object doc 정리로 수렴한다.
5. reservation claim+두 key ownership promote+job create가 하나의 transaction/commit-loss 단위다.
6. worker 성공·실패 cleanup 뒤 job ref 0이고 object doc이 제거된다.
7. producer의 PUT 실패·collision·option-b 보상·analysis_missing·reserve exception 각 경로 뒤 reservation ref가 정리되거나 janitor가 처리 가능한 상태다.
8. orphan janitor도 live reservation/job ref와 동일 deleting fence를 사용한다.
9. closed reservation/orphan의 `expireAt` timestamp와 실제 Firestore TTL policy가 collection group별로 검증된다.
10. Wave 0 checkpoint 설명과 action이 모두 lifecycle mutation을 명시하고 before/rollback artifact가 존재한다.
11. Wave 0 rule이 이미 있는 상태에서 31-10 dry-run/31-12 put을 반복해도 duplicate ID 없이 결과가 동일하다.
12. `$VIB` 미정·JSON 부재·schema 오류면 deploy/lifecycle/IAM/E2E가 모두 시작 전에 실패한다.
13. alternative bucket fixture가 dry-run→SAM parameter→IAM ARN→Pod env→E2E prefix로 exact 전파된다.
14. ownership 여섯 barrier test + 전체 backend test + SAM validate/build가 green이다.

---

## 9. 최종 판정

**BLOCK / TARGETED REPLAN REQUIRED**

9차 수정은 이전 5 blocker 중 janitor lease, multi-object, pair 결정, bucket 전파를 대부분 개선했다. 하지만 동일-key ownership의 핵심 선형화 지점이 아직 S3 delete를 보호하지 못하고, ref lifecycle도 닫히지 않았다. 이는 작은 문구 문제가 아니라 Phase 31의 확정된 즉시삭제 SLA를 구현하는 핵심 상태 머신 결함이다.

따라서 31-01/02/09/10/12와 VALIDATION을 위 범위로 수정한 뒤 11차 리뷰에서 다음을 다시 검증해야 한다.

- object delete claim의 safety와 liveness
- 모든 producer/worker/janitor 종료 경로의 ref 정리
- Wave 0 lifecycle 승인·idempotence·rollback
- Firestore TTL policy와 chosen bucket fail-closed 배포

외부 리뷰어를 호출하지 않았으며, 이 판정과 처리안은 직접 검토 결과다.
