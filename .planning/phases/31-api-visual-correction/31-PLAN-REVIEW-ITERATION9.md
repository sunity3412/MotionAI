# Phase 31 계획 9차 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-20
**리뷰 기준 커밋:** `00a5bdb` (`iteration8 targeted replan`)
**리뷰 범위:** 8차 개정된 `31-01-PLAN.md`, `31-02-PLAN.md`, `31-09-PLAN.md`, `31-10-PLAN.md`, `31-12-PLAN.md`, `31-VALIDATION.md`와 Phase 31의 나머지 계획·CONTEXT·1~8차 리뷰
**리뷰 방법:** 8차 6 blocker/9 High/5 Medium closure 추적, create acquisition 정상·중복·crash 시간축, per-invocation reservation의 동일-key·multi-object·janitor-crash interleaving, finalizer truth table, chosen bucket 전파, pair 제품 결정 및 배포 artifact lockstep 재대조
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 리뷰 없이 직접 검토했다.
**최종 판정:** **BLOCK / TARGETED REPLAN REQUIRED**

---

## 1. 결론

8차 개정은 이전 blocker 중 네 축을 실질적으로 개선했다.

- `begin_visual_job_create`가 31-02의 실제 함수로 편입되고 acquired/busy/resume/unconfirmed/stale 분기가 생겼다.
- correctedPose finalizer가 kind 기준 unconditional gate로 바뀌었고 cleanup_blocked clear+terminal도 한 transaction으로 정의됐다.
- dispatcher IAM은 잘못된 `s3:HeadObject` 대신 `s3:GetObject`를 사용하며 prefix-scoped ListBucket을 갖는다.
- reservation을 invocation별 문서로 나눠 서로 다른 expectedKeys overwrite 문제를 제거했다.
- lifecycle을 31-12 checkpoint로 이연하고 policy merge/rollback, Object Lock 전용 API, YAML 기반 build gate를 보강했다.

그러나 새 reservation/janitor 상태 머신은 아직 crash-safe하지 않다.

1. janitor가 reservation을 `claimed_by_janitor` 또는 orphan을 `claimed`로 바꾼 직후 죽으면 lease/owner/만료 복구 규칙이 없어 영구 정지한다.
2. invocation별 문서는 서로 다른 reservation끼리 같은 deterministic S3 key를 공유하는 경우를 조정하지 않는다. expired A를 청소하는 janitor가 현재 진행 중인 B의 입력을 삭제할 수 있다.
3. option-b 두 번째 PUT 직후 `record_reservation_keys` 전에 죽으면 `createdKeys`는 첫 key만 담고 `expectedKeys`는 두 key다. janitor의 “createdKeys 또는 expectedKeys” 선택은 두 번째 key를 남길 수 있다.
4. pair network 실패를 단일 시도로 낮추는 변경은 Phase 31 CONTEXT의 명시적 플라이휠 산출을 축소하지만, 실제 blocking decision task나 CONTEXT amend가 없다.
5. chosen bucket name을 단일 출처로 만들었다고 선언했지만 31-10/31-12의 lifecycle, IAM, Pod env, E2E 명령과 SAM deploy가 여전히 기본 이름을 하드코딩한다.

따라서 8차의 create/finalizer/IAM 방향은 유지하되, 31-01/02/09/10/11 또는 12와 VALIDATION을 한 번 더 targeted replan해야 한다.

### 발견 수

| 심각도 | 수 | 의미 |
|---|---:|---|
| BLOCKER | 5 | privacy cleanup·제품 결정·대체 bucket 실행 경로가 완결되지 않음 |
| HIGH | 9 | 같은 targeted replan에서 상태·IaC·검증 계약 보강 필요 |
| MEDIUM | 6 | 문서/acceptance/parser 정합 보강 필요 |

---

## 2. 8차 리뷰 지적 해소 추적

| 8차 ID | 9차 상태 | 판단 |
|---|---|---|
| B8-01 create 획득 자기모순 | **대체로 해소** | typed status와 acquired happy path가 편입됨. creating 내부 outbox 필드와 rotation failure 분기는 High로 남음 |
| B8-02 inputSealed false 우회 | **해소** | kind 기준 unconditional gate와 네 거부 조합 반영 |
| B8-03 cleanup_blocked 회복 불능 | **해소** | dedicated cleanup parameter로 blocker clear+terminal을 원자 처리 |
| B8-04 invalid `s3:HeadObject` | **해소** | dispatcher GetObject/DeleteObject/ListBucket 및 HeadObject 문자열 0 검증 반영 |
| B8-05 reservation overwrite | **부분 해소** | per-invocation 문서로 서로 다른 key overwrite는 막음. 동일 S3 key를 공유하는 live reservation 간 조정이 없어 B9-02 발생 |
| B8-06 producer/janitor TOCTOU | **부분 해소** | 같은 reservation에서는 claim CAS를 공유함. 다른 reservation의 동일 key와 janitor claim crash는 닫히지 않음 |
| H8-01 janitor pagination | **대체로 해소** | bounded cursor/1,200 drain 반영. scan helper 소유와 claimed recovery는 남음 |
| H8-02 pair durability 충돌 | **미해소** | 문구는 단일 시도로 통일했으나 belle amend 대기만 적고 실제 checkpoint/CONTEXT 수정 없음(B9-04) |
| H8-03 shared helper | **부분 해소** | helper 목록 추가. nested transaction/list cursor/recovery 세부가 불완전 |
| H8-04 dispatcher least privilege | **해소** | prefix condition + Get/Delete가 plan/test에 반영 |
| H8-05 lifecycle 선후관계 | **해소 방향** | Wave 0 lifecycle 제거, 31-12 merge/rollback으로 이연. smoke hard-crash 방어층 부재는 High |
| H8-06 bucket policy replacement | **대체로 해소** | 신규/기존 분기와 Sid merge/rollback 반영. artifact frontmatter 누락은 Medium |
| H8-07 chosen name 전파 | **미해소** | JSON은 추가했지만 downstream 하드코딩과 deploy override 누락(B9-05) |
| H8-08 Object Lock API | **해소** | action/acceptance가 전용 API와 AccessDenied fail-closed로 통일 |
| H8-09 build lockstep | **대체로 해소** | YAML parser 검사 추가. alarm 생성 본문과 개수는 불일치 |
| M8-01 lifecycle/alarms stale | **부분 해소** | 4파일은 acceptance에 반영. alarm action/count 일부 stale |
| M8-02 31-12 frontmatter | **대체로 해소** | 두 before 파일 반영. 31-01 신규 bucket/policy artifact는 누락 |
| M8-03 model cleanup 설명 | **대체로 해소** | Task 2는 done|failed 공통. 31-02 objective에 예전 조건부 문구 잔존 |
| M8-04 create duplicate test | **해소** | acquired 정확히 1, 외부 create 총 1 반영 |
| M8-05 janitor metrics | **부분 해소** | metric/test 이름 추가. template action에 실제 두 alarm 정의가 없음 |

---

## 3. BLOCKERS

### B9-01 · janitor claim 자체가 crash-recoverable하지 않아 cleanup 문서가 영구 정지한다

**근거**

- `31-02-PLAN.md:143-148`의 reservation 상태는 `open → claimed_by_janitor → closed`다. `claimed_by_janitor`에 claimOwner/claimLeaseExpiresAt/재claim 규칙이 없다.
- janitor가 claim transaction을 commit한 직후 S3 delete 전에 죽으면 다음 sweep은 state가 open이 아니므로 다시 선택하지 않는다.
- `31-02-PLAN.md:149-152`의 orphan도 `open → claimed → closed`이고 claimed lease가 없다.
- orphan claim 직후 crash 또는 Lambda timeout이면 `claim_visual_orphan`은 open만 받으므로 해당 object는 다시 처리되지 않는다.
- 31-09의 1,200건 drain test는 정상 claim→delete→close만 다루고 claim 직후 crash를 다루지 않는다.

**영향**

durable cleanup의 최종 소유자인 janitor가 한 번 죽는 것만으로 raw input object가 lifecycle까지 남거나, lifecycle과 무관한 orphan registry가 영구 미처리 상태가 된다. alarm은 탐지할 수 있어도 복구 주체가 없다.

**제가 처리한다면**

- reservation과 orphan claim에 `claimOwner`, `claimLeaseExpiresAt`, `claimAttempt`를 추가한다.
- open/due뿐 아니라 claimed 상태의 lease가 만료된 문서도 재claim할 수 있게 한다.
- reservation의 `claimed_by_janitor`와 orphan의 `claimed`를 별도 cursor에서 복구하거나 동일 스캔에서 정확히 필터한다.
- claim commit 직후 SIGKILL → lease 전 재실행 0 → lease 후 새 owner 재claim → delete+HEAD404+close의 전체 시간축을 fault test로 고정한다.

---

### B9-02 · per-invocation reservation은 동일 deterministic S3 key의 cross-reservation 삭제 경쟁을 막지 못한다

**근거**

- source key는 `visual-input/{uid}/{analysisId}/{sourceHash}.png`로 deterministic하다. 같은 분석/source의 재실행은 서로 다른 reservationId를 쓰지만 같은 S3 key를 공유한다.
- `claim_reservation_for_janitor`는 **자기 reservation**과 visual job만 확인한다. 같은 key를 expectedKeys로 가진 다른 live open reservation은 확인하지 않는다.
- 가능한 시간축:
  1. A가 key K를 PUT하고 crash, reservation A가 expired.
  2. B가 새 reservation B를 만들고 K를 HEAD/reuse하거나 PUT하지만 아직 job reserve 전.
  3. janitor가 A를 claimed_by_janitor로 바꾸고 K를 삭제.
  4. B가 자기 reservation을 claimed_by_job로 바꾸고 job을 생성.
- A/B는 서로 다른 Firestore 문서이므로 B8-06의 같은-doc CAS는 이 경쟁을 감지하지 못한다.

**영향**

성공적으로 reserved된 job이 삭제된 input을 가리키게 된다. upload-first invariant가 다시 깨지고 vendor 실패·불필요 과금이 발생한다.

**제가 처리한다면**

- key별 단일 ownership 문서 `visualInputObjects/{hash(bucket,key)}`를 두고 live reservation ref/owner generation을 transaction으로 관리한다.
- producer는 PUT/reuse 전에 key ownership을 획득하고, job reserve 시 job ownership으로 승격한다.
- janitor는 자기 reservation claim뿐 아니라 object ownership에 다른 live reservation/job ref가 0인 경우에만 delete claim을 획득한다.
- 최소 대안으로 janitor transaction이 동일 key의 모든 live reservation을 안전하게 조회할 수 있는 역색인 문서를 사용한다. array query 후 외부 delete 같은 비원자 read는 금지한다.
- 위 A-expired/B-live interleaving을 barrier test로 추가한다.

---

### B9-03 · multi-object hard crash에서 `createdKeys 또는 expectedKeys`가 두 번째 object를 남길 수 있다

**근거**

- option-b reservation의 expectedKeys는 src와 trainingSrc 두 개다.
- producer는 PUT 성공 후 `record_reservation_keys`로 createdKeys를 갱신한다.
- 시간축: src PUT+record 성공(createdKeys=[src]) → trainingSrc PUT 성공 → record 전에 SIGKILL.
- `31-09-PLAN.md:158`은 janitor가 `createdKeys(또는 expectedKeys)`를 삭제한다고 한다. createdKeys가 비어 있지 않다는 이유로 이를 선택하면 trainingSrc는 삭제 대상에서 빠진다.
- validation에는 첫 PUT 직후 crash와 두 번째 PUT 실패는 있지만 **두 번째 PUT 성공 직후 record 전 crash**가 없다.

**영향**

학습용 원본/블러 frame 하나가 job 없이 남는다. 바로 이 구간은 catch compensation도 실행되지 않는다.

**제가 처리한다면**

- janitor 삭제 후보를 항상 `expectedKeys ∪ createdKeys`로 정의한다. 비-버저닝 `DeleteObject`는 존재하지 않는 expected key에도 멱등이므로 안전하다.
- 단, B9-02의 다른 live owner 검사를 key별로 먼저 통과해야 한다.
- 각 key delete 후 HEAD404/ListBucket 검증을 하고 하나라도 남으면 reservation을 close하지 않는다.
- 두 번째 PUT 2xx 직후 hard crash 테스트를 추가해 두 key 모두 0을 요구한다.

---

### B9-04 · pair 단일 시도는 명시적 제품 결정을 축소하지만 실제 belle checkpoint가 없다

**근거**

- `31-CONTEXT.md:12-13`은 `[틀린 폼→고쳐진 폼]` pair를 Phase 22 재도전 원료이며 Phase 31의 부산물로 명시한다.
- `31-09-PLAN.md:136-137,212`는 network/5xx 실패 시 durable retry 없이 `pairStoreStatus='failed'`로 terminal 진행하고 플라이휠 손실을 수용하도록 바꾼다.
- `31-VALIDATION.md:223,253,270,273`은 이를 “belle amend 대기/결정 위임”이라고 적지만, 31-01/31-11/31-12 어디에도 이 결정을 받는 blocking checkpoint가 없다.
- CONTEXT도 amend되지 않았고, validation은 대기 중인 결정을 `[x]`와 planner approval로 표시한다.

**영향**

실행자는 사용자 승인 없이 product requirement를 축소하거나, 반대로 승인 대기 상태라 phase를 끝낼 수 없다. 네트워크 일시 장애 때 자동 데이터 플라이휠 산출이 조용히 유실된다.

**제가 처리한다면**

- D-06 checkpoint와 동형의 blocking decision을 추가한다.
  - A: user terminal 밖 별도 durable pair outbox/consumer.
  - B: 단일 시도 수용 + CONTEXT D-01/부산물 문구 명시 amend.
- A를 권고한다. postprocess는 pair outbox만 원자 기록하고 cleanup/finalize를 진행해 사용자 지연 없이 durable retry를 유지할 수 있다.
- belle 결정 전 validation `[x]`, nyquist true, planner approval을 완료로 표시하지 않는다.

---

### B9-05 · chosen bucket 단일 출처 선언과 달리 alternative-name 경로가 여전히 기본 bucket을 사용한다

**근거**

- 31-01은 `infra/visual_input_bucket.json`을 단일 출처로 만들고 글로벌 이름 충돌 시 대체명을 승인받는다고 한다.
- 그러나 `31-10-PLAN.md:22,138`은 Parameter default와 설명을 기본 이름으로 고정하고 dry-run이 JSON을 읽는다는 명시가 없다.
- `31-12-PLAN.md:95` lifecycle put, `:118` IAM ARN, `:133` Pod env, `:143` E2E list 명령이 모두 `sunity-motion-pilot-visual-input`을 하드코딩한다.
- flag OFF/ON `sam deploy` 명령도 `VisualInputBucketName=<chosen>` parameter override를 전달하지 않는다.
- 31-01 acceptance의 “하드코딩 grep 0”과 31-12 objective의 “모두 JSON을 읽음”을 실제 action이 위반한다.

**영향**

기본 이름이 타 계정에 선점되어 대체명을 선택하면 lifecycle/IAM/Pod/E2E가 잘못된 bucket을 조회하거나 배포가 실패한다. Task 1b의 안전한 대체명 분기가 실행 불가능하다.

**제가 처리한다면**

- JSON을 읽어 shell-safe validated 변수로 전달하는 공통 로컬 helper/script를 둔다.
- 31-10 dry-run은 JSON의 bucketName을 필수 입력으로 사용한다.
- SAM deploy 두 번 모두 `VisualInputBucketName=<chosen>` override를 명시하고 deploy 후 stack parameter를 재검증한다.
- lifecycle/IAM/Pod/E2E 명령의 bucket/ARN을 전부 chosen 값에서 파생한다.
- 기본값 문자열은 template default/선택 제안 외 실행 action에 0임을 정적 검사하고 alternative fixture로 end-to-end dry-run한다.

---

## 4. HIGH

### H9-01 · reservation TTL이 숫자와 IaC build gate 없이 서술로만 존재한다

B8-06의 안전성은 reservation이 expire할 때 producer가 절대 실행 중일 수 없다는 전제에 의존한다. 그러나 `VISUAL_INPUT_RESERVATION_TTL_MS` 값, PipelineFunction timeout, clock source, build inequality가 없다. 31-02 import verify도 TTL 관계를 검사하지 않는다.

**제가 처리한다면:** PipelineFunction timeout을 명시하고 `PipelineTimeout*1000 + margin <= TTL`을 YAML/model 단일 출처 test로 고정한다. Firestore server timestamp 기반 expiry를 권고하며 local clock skew 허용치를 포함한다.

### H9-02 · janitor의 job 조건이 “job 부재”와 “matching nonterminal 부재”로 갈린다

31-02 helper는 matching nonterminal job이 없으면 claim한다고 하지만 31-09 dispatcher는 job이 부재할 때만 claim한다고 쓴다. terminal job 뒤 stale reservation은 후자 구현에서 영원히 open으로 남는다. terminal 또는 inputSealed job은 오히려 새 input을 반드시 삭제해야 한다.

**제가 처리한다면:** exact predicate를 `유효하게 해당 key를 소유한 nonterminal unsealed job 없음`으로 정의한다. terminal/inputSealed/mismatched payload는 삭제 가능, matching nonterminal unsealed만 보존한다. 모든 분기를 표 기반 test로 고정한다.

### H9-03 · `begin_visual_job_create`의 creating 전이가 outbox 필드를 어떻게 바꾸는지 정의되지 않았다

begin은 state/lease/requestKey만 명시한다. creating은 내부 상태라 `nextAction=None`, `dispatchState=None`이어야 하는데 이를 원자 기록하는지, outboxSeq를 유지/증가시키는지 없다. `_advance`의 acquired snapshot CAS와 duplicate stale 판정은 이 선택에 의존한다.

**제가 처리한다면:** begin transaction의 full write set을 고정한다. 권고는 outboxSeq+1, nextAction=None, dispatchState=None, nextDispatchAtMs=0, claim fields clear이며 acquired snapshot의 새 seq를 creating→polling CAS에 사용한다. old create message는 즉시 stale가 된다.

### H9-04 · `reserve_visual_job` 안에서 transactional helper를 호출하는 방식이 nested transaction인지 불명확하다

`claim_reservation_for_job`은 독립 public helper 시그니처인데 동시에 reserve의 “같은 transaction 안에서 호출”된다고 한다. 두 `@firestore.transactional` wrapper를 중첩하면 동일 원자성이 보장되지 않거나 구현이 곤란하다.

**제가 처리한다면:** `_claim_reservation_for_job_tx(transaction, ...)` 내부 함수를 만들고 public wrapper와 reserve가 이를 공유한다. transaction object를 명시적으로 받아 read-all-before-write 순서를 지킨다. 테스트는 job과 reservation이 하나의 commit/commit-loss 단위임을 확인한다.

### H9-05 · M8-05 두 alarm을 test는 요구하지만 template action은 실제 resource를 정의하지 않는다

31-10 test와 31-12 build gate는 `VisualOrphanOldestAgeAlarm`과 `VisualOrphanSweepFailedAlarm`을 요구한다. 하지만 31-10 template action의 alarm 정의는 기존 5개에서 끝나고 새 두 alarm의 Namespace/MetricName/threshold/evaluation period가 없다.

**제가 처리한다면:** 두 CloudWatch Alarm resource를 template action에 exact하게 추가하고 no-data 처리와 threshold를 명시한다. `VisualDLQAlarm`까지 포함한 전체 logical ID 목록을 한 표로 단일화한다.

### H9-06 · claimed_by_job/closed reservation과 closed orphan 문서의 수명·reconciliation이 없다

job reserve 뒤 close 전에 crash하면 reservation은 claimed_by_job에 영구 잔존한다. 정상 close된 문서도 삭제/TTL이 없어 collection scan 비용과 metadata retention이 계속 늘어난다. orphan closed 문서도 bucket/key/uid 경로 metadata를 보존한다.

**제가 처리한다면:** terminal job/cleanup과 reservation close를 reconciliation하고, closed 문서는 Firestore TTL용 `deleteAfter`를 기록한다. 개인정보 식별자가 든 key는 close 후 hash만 남기거나 짧은 운영 보존기간 뒤 삭제한다.

### H9-07 · 동일 orphan key가 다시 생성됐을 때 closed 문서를 reopen하는 semantics가 없다

orphan ID가 `hash(bucket,key)`라 같은 deterministic key가 나중에 다시 orphan될 수 있다. 기존 문서가 closed일 때 `upsert_visual_orphan`이 open으로 재설정하는지, attempt/createdAt/lastError를 어떻게 다루는지 없다.

**제가 처리한다면:** 새 incident generation을 두거나 `upsert`가 closed→open, generation+1, attempt=0, timestamps reset을 CAS하도록 명시한다. close된 동일 key 재발 테스트를 추가한다.

### H9-08 · Wave 0 lifecycle 이연으로 smoke hard crash 방어층이 Wave 6까지 없다

31-01 Task 1b는 lifecycle을 전혀 적용하지 않고 곧바로 smoke input을 bucket에 올린다. 스크립트가 hard-kill되면 janitor는 아직 구현/배포 전이고 lifecycle도 없으므로 object가 무기한 남는다. VALIDATION Wave 0은 여전히 1일 lifecycle을 요구한다.

**제가 처리한다면:** 신규 bucket이면 생성 직후 exact 1일 rule을 before/put-get/rollback과 함께 안전 적용한다. 기존 bucket이면 merge artifact를 먼저 만든다. 이게 어렵다면 smoke에 로컬 durable cleanup manifest와 다음 실행 preflight sweep을 넣고 Wave 0 validation 문구를 실제 선택과 맞춘다.

### H9-09 · create failure 분기가 correctedPose와 rotation을 명확히 구분하지 않는다

31-09 `_action_create`의 unconfirmed/sync/typed failure 예시는 `_finalize_correctedpose_intent`를 직접 호출하지만 같은 handler가 rotation도 처리한다. 아래 주석은 rotation 실패가 direct finalize라고만 한다. 구현자가 문언대로 공통 helper를 호출하면 rotation이 correctedPose postprocessing/input cleanup 계약으로 잘못 흐른다.

**제가 처리한다면:** `_finalize_create_failure(job, reason)`에서 kind를 분기해 correctedPose는 postprocessing, rotation은 direct finalize로 고정한다. 두 kind의 acquired→typed failure/unconfirmed/sync 결과를 별도 테스트한다.

---

## 5. MEDIUM

### M9-01 · 31-02 objective가 예전 `inputSealed==True면` 조건부 gate를 유지한다

`31-02-PLAN.md:63`은 아직 inputSealed가 true일 때만 cleanup proof를 요구한다고 쓴다. must-have/action/acceptance의 unconditional 계약과 충돌한다.

**제가 처리한다면:** objective도 `kind=='correctedPose'이면 unconditional`로 바꾸고 세 면 grep test를 둔다.

### M9-02 · VALIDATION Wave 0 요구가 lifecycle 이연 결정과 충돌한다

`31-VALIDATION.md:234`는 Wave 0 bucket에 1일 lifecycle을 요구하지만 31-01 Task 1b는 lifecycle put 0을 acceptance로 요구한다.

**제가 처리한다면:** H9-08에서 선택한 방식에 맞춰 한쪽으로 통일한다.

### M9-03 · alarm 수가 7종/8종으로 어긋나고 DLQ가 build 목록에서 빠진다

31-12 must-have는 “alarm 7종”이라고 하면서 괄호에는 기존 6개(DLQ 포함)+신규 2개, 즉 8개를 적는다. Task 1 action은 DLQ를 제외한 7개만 검사한다.

**제가 처리한다면:** logical ID 8개를 단일 표로 만들고 template/test/build acceptance가 그 목록을 import하도록 한다.

### M9-04 · 31-12에 중복 `</how-to-verify>` closing tag가 있다

`31-12-PLAN.md:114-115`에 closing tag가 두 번 있다. XML 유사 구조를 읽는 executor/checker의 task 경계를 흐릴 수 있다.

**제가 처리한다면:** 중복 한 줄을 제거하고 task tag balance 정적 검사를 돌린다.

### M9-05 · 31-12 lifecycle read_first/acceptance가 옛 단일 파일명을 유지한다

Task 2 read_first `:94`와 acceptance `:101-103`은 `lifecycle_before.json/lifecycle_merged.json` 단수 이름을 사용한다. 실제 artifact는 bucket별 4파일이다.

**제가 처리한다면:** 네 exact 파일명을 전부 적고 각 hash/bucket mapping을 summary manifest에서 검증한다.

### M9-06 · 31-01 frontmatter에 새 bucket/policy artifact가 없다

Task 1b가 `infra/visual_input_bucket.json`과 조건부 `infra/visual_input_policy_before.json`을 만들지만 files_modified/artifacts에 없다. GSD commit/summary 범위에서 빠질 수 있다.

**제가 처리한다면:** 두 파일을 frontmatter에 추가하고 bucket JSON schema 및 policy before hash를 acceptance에 넣는다.

---

## 6. 9차 수정 우선순위

1. **31-02/09:** reservation·orphan janitor claim에 owner/lease/expired-reclaim을 추가한다.
2. **31-02/10:** key-level ownership/ref 계약으로 cross-reservation 동일-key 삭제 경쟁을 닫는다.
3. **31-09/10/VALIDATION:** multi-object 삭제는 expected∪created 전체로 고정하고 두 번째 PUT 직후 crash test를 추가한다.
4. **31-11 또는 별도 checkpoint/CONTEXT:** pair durable outbox vs 단일 시도 제품 결정을 belle에게 실제로 받는다.
5. **31-01/10/12:** chosen bucket JSON을 dry-run/SAM/lifecycle/IAM/Pod/E2E 전체에 실제 전달한다.
6. **31-02/09:** begin full write set, nested transaction 내부 helper, kind별 create failure를 명시한다.
7. **31-10/12/VALIDATION:** TTL build gate, 두 janitor alarm, lifecycle 선택, alarm 8종, 4 lifecycle 파일을 lockstep한다.

---

## 7. 다음 수정의 실행 허용 조건

1. reservation/orphan janitor claim 직후 crash가 lease 만료 후 재claim되어 cleanup을 완료한다.
2. expired reservation A와 동일 key를 쓰는 live reservation B가 있을 때 A janitor는 key를 삭제하지 않는다.
3. src record 완료→training PUT 2xx→record 전 crash 뒤 두 expected key가 모두 삭제된다.
4. janitor 삭제 후보는 `expectedKeys ∪ createdKeys`이며 key별 live owner 0을 먼저 검증한다.
5. pair 정책은 durable outbox 또는 belle-approved CONTEXT amend 중 하나로 닫힌다.
6. chosen alternative bucket fixture가 dry-run→SAM parameter→lifecycle→IAM→Pod→E2E 명령 전체에 전파된다.
7. reservation TTL 값과 `PipelineTimeout + margin <= TTL` build gate가 존재한다.
8. terminal/inputSealed/mismatched/matching-nonterminal별 janitor predicate 표 테스트가 있다.
9. begin acquired transaction의 nextAction/dispatchState/outboxSeq full write set이 고정된다.
10. reserve와 reservation claim이 하나의 transaction/commit-loss 단위임을 테스트한다.
11. same orphan key의 closed→new incident가 다시 open되어 cleanup된다.
12. claimed_by_job/closed 문서 reconciliation 및 metadata TTL이 있다.
13. template action에 OrphanOldestAge/SweepFailed alarm의 exact resource가 있다.
14. Wave 0 lifecycle/smoke hard-crash 방어 선택이 plan과 VALIDATION에서 일치한다.
15. alarm 8개(DLQ 포함), lifecycle 4파일, Object Lock API, plan tag balance가 lockstep 검증된다.

---

## 8. 최종 판단

**9차 리뷰도 승인 불가다.**

create acquisition, unconditional finalizer, invalid IAM action은 이번 개정으로 충분히 좋아졌다. 현재 남은 핵심은 reservation을 “문서 단위 CAS”에서 “실제 S3 key ownership + crash-recoverable janitor lease”로 한 단계 더 올리는 것이다. 지금 상태에서는 janitor 자체 crash와 서로 다른 reservation의 동일-key 경쟁이 privacy cleanup 보장을 깬다.

제가 실제 구현 책임자라면 Wave 1을 시작하기 전에 B9-01~05를 닫는다. 특히 pair 정책은 기술자가 임의로 amend하지 않고 belle의 명시 결정을 받은 뒤, 10차 리뷰에서 실행 가능 여부를 다시 판정한다.
