# Phase 31 계획 8차 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-19  
**리뷰 기준 커밋:** `477f411` (`iteration7 targeted replan`)  
**리뷰 범위:** 7차 개정된 `31-01-PLAN.md` ~ `31-13-PLAN.md`, `31-VALIDATION.md`, 1~7차 리뷰, Phase 31 CONTEXT/ROADMAP 및 계획이 직접 참조하는 현재 코드/IaC  
**리뷰 방법:** 7차 blocker/High/Medium closure 추적, correctedPose terminal invariant의 모든 boolean 조합, create lease의 정상·중복·만료 시간축, upload reservation/janitor의 concurrent interleaving, 실제 S3 IAM action, lifecycle/배포 artifact 계약, pair durability와 validation matrix 재대조  
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 리뷰 없이 직접 검토했다. AWS 공식 문서는 IAM action 의미를 확인하는 1차 명세로만 사용했다.  
**최종 판정:** **BLOCK / TARGETED REPLAN REQUIRED**

---

## 1. 결론

7차 수정은 이전 일곱 blocker의 표면적 요구를 대부분 계획에 편입했다.

- worker의 `s3:ListBucket`, Never-versioned 판정, bucket 선행 provision, bucket별 lifecycle 4파일이 추가됐다.
- cleanup proof를 finalizer 파라미터로 전달하도록 바뀌었고 failed correctedPose도 cleanup proof를 언급한다.
- create inbound CAS, PUT 전 reservation, durable orphan 문서와 janitor가 새로 생겼다.
- worker/pipeline metric 권한과 5개 alarm, D-06 제품 결정 checkpoint, canonical copy metadata 보존이 반영됐다.

하지만 새 계약은 정상 경로 또는 장애 경로를 실제로 닫지 못한다.

1. `begin_visual_job_create`가 reserved/retry_ready를 creating으로 바꿔 반환하면 바로 다음 “future lease는 no-op” 분기에 걸린다. 정상 vendor create가 실행되지 않는다. 이 함수는 31-02 구현 task에도 없다.
2. finalizer는 `inputSealed==True`일 때만 cleanup proof를 검사한다. `inputSealed=False`인 correctedPose는 done/failed 모두 privacy gate를 우회할 수 있다.
3. `cleanup_blocked` 복구 후 remaining 0이 되어도 finalizer는 기존 `job.privacyBlocker`를 거부하고, 호출은 이를 clear하지 않는다. blocker 상태에서 terminal로 회복할 수 없다.
4. dispatcher IAM에 넣은 `s3:HeadObject`는 존재하지 않는 IAM action이다. S3 `HeadObject` API에는 `s3:GetObject`가 필요하다.
5. `visualInputReservations/{jobId}` 단일 문서는 concurrent producer가 서로 덮어쓸 수 있어 먼저 PUT하고 죽은 invocation의 key가 추적에서 사라진다.
6. janitor의 “job 없음 확인 → S3 delete”와 producer의 “job reserve” 사이가 원자적이지 않아, 성공적으로 예약된 job의 입력을 janitor가 뒤늦게 삭제할 수 있다.

따라서 Wave 1 실행 전에 최소 31-01/02/09/10/12와 VALIDATION을 다시 targeted replan해야 한다. 특히 reservation은 문서 하나를 추가하는 수준이 아니라 producer와 janitor가 같은 transaction/CAS 계약을 공유하도록 다시 정의해야 한다.

### 발견 수

| 심각도 | 수 | 의미 |
|---|---:|---|
| BLOCKER | 6 | 정상 실행·privacy cleanup·실 IAM 중 하나를 깨므로 실행 전 수정 필수 |
| HIGH | 9 | 같은 targeted replan에서 계약·검증을 닫아야 함 |
| MEDIUM | 5 | 배포 전 문서·acceptance 정합 보강 필요 |

---

## 2. 7차 리뷰 지적 해소 추적

| 7차 ID | 8차 상태 | 판단 |
|---|---|---|
| B7-01 worker `ListBucket` | **해소** | worker bucket ARN + prefix condition, simulate/live canary가 반영됨 |
| B7-02 Never-versioned 판정 | **해소** | `Status` key 부재만 통과하고 Enabled/Suspended를 모두 차단 |
| B7-03 cleanup proof handoff | **대체로 해소** | explicit 파라미터와 candidate merge 반영. blocker clear 경로가 별도로 깨져 B8-03 발생 |
| B7-04 failed cleanup validator | **부분 해소** | done/failed 공통 문구는 들어갔으나 `inputSealed==True` 조건부라 false 우회가 남음(B8-02) |
| B7-05 hard-crash upload journal | **부분 해소** | PUT 전 reservation과 janitor 추가. 단일 `{jobId}` overwrite 및 janitor/producer TOCTOU로 보장이 깨짐(B8-05/B8-06) |
| B7-06 bucket provision | **해소 방향** | 31-01 Task 1b 추가. lifecycle 선후관계·rollback·대체명 전파는 High로 남음 |
| B7-07 bucket별 lifecycle | **대체로 해소** | 4파일과 교차 rollback 반영. 31-10/31-12의 stale artifact/acceptance가 남음 |
| H7-01 creating internal send | **해소** | `next_action is not None`일 때만 send/mark, action-null 테스트 반영 |
| H7-02 create inbound CAS | **미해소** | 함수 소유 task가 없고 반환 의미가 자기모순이라 정상 create가 no-op(B8-01) |
| H7-03 metric IAM/alarm | **대체로 해소** | producer 권한과 5 alarm 반영. 31-12 build acceptance 일부는 여전히 구 목록 |
| H7-04 durable orphan consumer | **부분 해소** | janitor가 추가됐으나 query/cursor/claim 및 producer와의 원자성 부재 |
| H7-05 smoke bucket | **해소** | 전용 bucket, delete, HEAD 404, Status 부재 검증 반영 |
| H7-06 D-06 완료 알림 | **해소 방향** | A/B blocking decision을 넣어 침묵 축소를 막음 |
| H7-07 pair off critical path | **부분 해소** | 사용자 terminal 지연은 제거했으나 durable retry 요구와 충돌(H8-02) |
| H7-08 copy metadata | **해소** | REPLACE + sha256 metadata와 response-loss replay 검증 반영 |
| H7-09 versioning drift | **해소 방향** | deploy/flag ON 재검사와 mutation 탐지 권고 반영 |
| M7-01 Object Lock 전용 API | **부분 해소** | must-have는 전용 API이나 Task 2 action/acceptance는 여전히 HEAD 3필드 |
| M7-02 full hash | **해소** | full 64 hex key/metadata 비교 반영 |
| M7-03 용어 정합 | **해소** | multi-object와 multi-version을 구분 |
| M7-04 worker-role E2E | **해소** | 관리자 helper canary와 분리해 request ID/role 증거 요구 |
| M7-05 IAM action/resource matrix | **부분 해소** | worker/pipeline은 좋아졌으나 dispatcher에 invalid action과 prefix condition 누락 |

---

## 3. BLOCKERS

### B8-01 · `begin_visual_job_create`의 정상 획득 결과가 즉시 no-op가 되며 구현 소유 task도 없다

**근거**

- `31-09-PLAN.md:105`는 `begin_visual_job_create`가 reserved/retry_ready를 **원자적으로 creating으로 전이하고 lease를 기록한 snapshot을 반환**한다고 한다.
- 같은 문장은 반환 snapshot의 state가 creating이고 lease가 미래면 **no-op**라고 한다.
- 신규 획득 직후 snapshot은 정확히 `state='creating'`, `leaseExpiresAt>now`이므로 vendor `create_task`에 도달하지 않는다.
- 뒤의 `state in ('reserved','retry_ready') → _advance(creating)` 분기는 begin 함수가 전이를 수행한다는 앞 계약과 양립할 수 없다.
- 전체 계획에서 함수명은 31-09와 VALIDATION에만 있고, `firestore_admin.py`를 수정하는 31-02 Task 3의 함수 목록·files/acceptance에는 없다. “wrapper 또는 별도 신설”은 구현 계약이 아니다.

**영향**

문언대로 구현하면 모든 최초 correctedPose/rotation create가 creating에 멈춘다. 반대로 begin이 검증만 하고 reserved를 반환하도록 구현하면 CAS와 lease 획득이 분리돼 7차 H7-02의 중복 과금 방지가 다시 열린다.

**제가 처리한다면**

- 31-02에 `begin_visual_job_create`를 명시적인 9번째 함수로 추가하고 단일 Firestore transaction으로 소유한다.
- 반환을 `{"status":"acquired"|"busy"|"resume"|"stale"|"unconfirmed", "job": snapshot}`으로 정의한다.
  - reserved/retry_ready + inbound gen/seq/action/due 일치 → creating+lease+requestKey를 원자 기록, `acquired` 반환.
  - `acquired` 호출자는 future lease를 다시 busy 판정하지 않고 즉시 vendor create 1회를 수행한다.
  - 기존 creating + 다른 유효 owner → `busy`; lease 만료+taskId 없음 → `unconfirmed`; taskId 있음 → `resume`.
- `_advance(... creating ...)`를 두 번째로 호출하지 않는다. begin의 creating snapshot을 vendor create와 creating→polling CAS의 유일 입력으로 쓴다.
- 최초 reserved happy path가 vendor create 정확히 1회에 도달하는 테스트를 추가한다.

---

### B8-02 · correctedPose finalizer가 `inputSealed=False`일 때 cleanup proof를 완전히 우회한다

**근거**

- `31-02-PLAN.md:137`의 조건은 `kind=='correctedPose' & job.inputSealed==True → cleanup_verified_at_ms > 0`이다.
- 즉 `kind=='correctedPose'`, `inputSealed=False`, `privacyBlocker=None`이면 done/failed terminal 검증이 cleanup proof 없이 통과한다.
- `31-VALIDATION.md:176`은 failed + cleanupVerified=0을 검사하지만 inputSealed를 **True로 고정**해 false 우회를 검증하지 않는다.
- model 설명도 `cleanupVerifiedAtMs`를 correctedPose done validator용이라고 적어 failed 공통 invariant와 완전히 lockstep되지 않았다.

**영향**

새 호출 경로, 운영 복구 코드 또는 회귀가 initial reserved job을 직접 finalize하면 분석은 terminal이 되지만 source/staging PII가 남을 수 있다. worker에서 postprocessing을 경유한다는 grep은 shared finalizer의 안전 경계가 아니다.

**제가 처리한다면**

- 조건을 뒤집어 `if kind == 'correctedPose':` 아래에서 done/failed 공통으로 다음 세 가지를 모두 요구한다.
  - candidate `inputSealed is True`
  - candidate `cleanupVerifiedAtMs > 0`
  - candidate `privacyBlocker is None`
- 그 뒤 done의 key/failureReason, failed의 typed reason/key None 규칙을 추가한다.
- `done+inputSealed=False`, `failed+inputSealed=False`, `done/failed+cleanup=0` 네 케이스를 모두 ValueError로 고정한다.

---

### B8-03 · `cleanup_blocked`가 해소되어도 finalizer가 blocker를 clear할 수 없어 영구 비-terminal이 된다

**근거**

- `31-02-PLAN.md:137`은 현재 `job.privacyBlocker`가 None이 아니면 finalize를 거부한다.
- `31-09-PLAN.md:135`는 cleanup_blocked 재시도 후 remaining 0이면 같은 finalizer를 호출하며 “clear는 finalize candidate 병합에서 처리”한다고 서술한다.
- 그러나 예시 호출의 `job_meta`에는 pair/judge/pose metadata만 있고 `privacyBlocker=None`이 없다. finalizer signature에도 explicit `clear_privacy_blocker`가 없다.
- 31-02는 `cleanup_verified_at_ms`의 candidate merge만 명시했으며 기존 blocker를 어떤 조건에서 clear하는지 정의하지 않는다.

**영향**

처음 5회 cleanup 실패 후 장기 backoff 상태가 되면, 이후 S3 장애가 해소되어 remaining 0이어도 finalizer는 기존 blocker 때문에 ValueError다. 운영자 `--redispatch-cleanup`도 terminal 복구를 완성하지 못한다.

**제가 처리한다면**

- finalizer가 correctedPose candidate를 만들 때 `cleanup_verified_at_ms>0`인 호출에 한해 `privacyBlocker=None`과 `cleanupVerifiedAtMs=...`를 같은 transaction에서 원자 반영하도록 명시한다.
- caller가 임의 `job_meta={'privacyBlocker': None}`로 지우는 방식은 금지하고 dedicated parameter/내부 규칙으로 제한한다.
- 기존 blocker가 cleanup 재확인 없이 clear되는 호출은 거부한다.
- fault test를 `5회 실패 → cleanup_blocked → 다음 invocation remaining 0 → blocker clear+terminal 한 transaction` 전체 시간축으로 만든다.

---

### B8-04 · dispatcher IAM의 `s3:HeadObject`는 존재하지 않는 action이다

**근거**

- `31-10-PLAN.md:138`은 VisualDispatchFunction object ARN에 `s3:DeleteObject/HeadObject`를 준다.
- S3 `HeadObject`는 API operation 이름이고 IAM action은 `s3:GetObject`다. 별도 `s3:HeadObject` action은 없다.
- AWS 공식 문서도 HEAD object 요청에 `s3:GetObject` 권한이 필요하다고 명시한다: [HeadObject API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html), [S3 API와 policy action 매핑](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html), [S3 IAM action 표](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security_iam_service-with-iam.html).

**영향**

정책 검증/배포가 invalid action으로 실패할 수 있고, 설령 계획 구현자가 임의로 생략하면 janitor의 delete 후 HEAD 404 검증이 403으로 실패해 orphan 문서를 닫지 못한다.

**제가 처리한다면**

- dispatcher object ARN action을 `s3:DeleteObject` + `s3:GetObject`로 바꾼다.
- template test에서 `s3:HeadObject` 문자열이 0임을 assert한다.
- simulate-principal-policy와 non-PII canary에서 dispatcher role의 GetObject/DeleteObject/ListBucket을 검증한다.

---

### B8-05 · `visualInputReservations/{jobId}` 단일 문서는 concurrent producer가 서로 덮어써 orphan key를 잃는다

**근거**

- `31-10-PLAN.md:137`은 preflight에서 job 부재를 본 각 invocation이 PUT 전 `visualInputReservations/{jobId}`를 “생성/갱신”한다.
- 같은 analysis에 서로 다른 `src_png`가 들어오면 sourceHash와 expectedKeys가 다르다. 계획은 이런 차이를 tampering/입력교체로 별도 처리할 만큼 가능성을 인정한다.
- interleaving: A가 expectedKeys=[A] 기록 → B가 같은 doc을 expectedKeys=[B]로 overwrite → A가 key A PUT → A SIGKILL. janitor는 B만 알고 A를 삭제하지 못한다.
- B가 job을 성공적으로 reserve하고 reservation 문서를 삭제하면 A key의 durable 추적은 완전히 사라진다.

**영향**

7차 B7-05가 막으려던 “PUT 직후 hard crash PII orphan”이 동시 invocation에서 그대로 재발한다. lifecycle 1일만 남는 것은 즉시 cleanup 계약을 충족하지 않는다.

**제가 처리한다면**

- reservation을 invocation별 immutable ID로 분리한다: `visualInputReservations/{jobId}_{reservationId}` 또는 job 하위 subcollection.
- 각 문서는 owner/sourceHash/expectedKeys/createdKeys/state/leaseExpiresAt을 가지며 다른 invocation이 replace할 수 없게 create-only precondition을 쓴다.
- job reserve 성공 시 **자기 reservation만** confirmed/closed하고 다른 reservation은 janitor가 job payload와 대조해 불일치 key를 삭제한다.
- A/B overwrite 시간축과 A hard crash를 fault test로 추가해 두 key 모두 소유 또는 삭제됨을 보인다.

---

### B8-06 · janitor의 read-then-delete가 producer reserve와 경쟁해 유효 job의 입력을 삭제할 수 있다

**근거**

- `31-09-PLAN.md:157`의 janitor는 expired reservation을 읽고 `read_visual_job` 결과에 matching nonterminal job이 없으면 S3 key를 삭제한다.
- producer의 `reserve_visual_job` transaction은 reservation을 읽거나 claim하지 않는다.
- 가능한 interleaving: janitor가 job 부재 확인 → producer가 job+analysis pending을 성공적으로 reserve → janitor가 input 삭제 → producer가 reservation confirm/delete 및 SQS send.
- job read와 S3 delete 사이에는 Firestore transaction으로 보호할 수 없는 외부 side effect가 있으므로 단순 재조회만으로도 선형화되지 않는다.
- TTL 숫자와 producer heartbeat/timeout 관계도 정의되지 않아 정상적으로 느린 producer를 expired로 오판할 수 있다.

**영향**

upload-first 보장이 역전된다. 유효한 reserved job이 존재하지만 source object가 사라져 vendor create 실패, 불필요한 과금/실패 및 개인정보 상태 불일치가 발생한다.

**제가 처리한다면**

- reservation state를 `open → claimed_by_job | claimed_by_janitor → closed`로 두고 transaction CAS를 공유한다.
- `reserve_visual_job`은 job 생성 transaction에서 자기 reservation이 open/owner 일치/미만료인지 읽고 `claimed_by_job`으로 바꾸어야만 job을 생성한다.
- janitor는 job 부재와 reservation expired를 같은 transaction에서 확인하고 `claimed_by_janitor`로 바꾼 뒤에만 S3 delete한다. 이 상태가 된 reservation으로 producer reserve는 실패하고 새 preflight부터 재시도한다.
- TTL은 pipeline 최대 실행시간+재시도 margin보다 크게 상수화하고, delete 실패는 같은 claimed reservation 또는 visualOrphans로 durable retry한다.
- 위 interleaving을 barrier 기반 concurrency test로 고정한다.

---

## 4. HIGH

### H8-01 · janitor에 bounded query, due filter, pagination/cursor, starvation 계약이 없다

dispatcher는 60초 Lambda인데 `visualInputReservations 중 expired`와 `visualOrphans 중 open`을 어떻게 조회하고 몇 건 처리하는지 없다. 전체 collection scan이면 backlog에서 timeout하고, 고정 first-N이면 실패 항목이 앞을 막아 후속 PII가 영구 starvation될 수 있다. outbox에는 별도 cursor를 정교하게 설계했지만 privacy janitor에는 같은 보장이 없다.

**제가 처리한다면:** 두 collection 각각 limit/max_scan/durable cursor를 두고 `nextRetryAtMs` due만 bounded 처리한다. 필요한 Firestore index를 계획에 명시하거나 단일-field query+client due filter+순환 cursor를 쓴다. oldest age/truncated/open count metric과 alarm을 추가하고 1,200건 drain 테스트를 둔다.

### H8-02 · pair network 실패 처리와 기존 durable retry/validation/success criteria가 서로 충돌한다

`31-09-PLAN.md:135`는 pair network/5xx 실패 시 즉시 `pairStoreStatus='failed'`로 terminal 진행하고 자동 retry를 제거한다. 그러나 같은 계획 `:136`은 M6-04 network failure에 “backoff self-loop”, success criteria `:211`은 H5-02 durable pair retry를 여전히 요구한다. `31-VALIDATION.md:141`도 pair/cleanup 일시 실패가 durable self-loop로 재개된다고 한다.

**제가 처리한다면:** user terminal과 pair retry를 분리한다. postprocess는 cleanup/finalize를 즉시 진행하되 별도 `visualPairOutbox/{pairId}`를 원자 기록하고 독립 consumer가 retry한다. 정말 manual-only로 낮출 경우 CONTEXT/requirement/VALIDATION/success criteria를 명시적으로 amend하고 데이터 플라이휠 손실을 제품 결정으로 승인받는다.

### H8-03 · reservation/orphan Firestore helper의 구현 위치·스키마·transaction test가 없다

31-10 pipeline과 31-09 dispatcher가 raw collection 이름을 직접 다루지만, 31-02 shared helper/files/acceptance에는 reservation create/claim/close 및 orphan upsert/claim/close 함수가 없다. FakeTransaction의 contention/commit-loss test도 계획되지 않았다. 이 상태에서는 양쪽이 서로 다른 필드·시간 단위·상태값을 구현할 가능성이 높다.

**제가 처리한다면:** models/firestore_admin에 typed path/state/TTL 상수와 transactional helper를 모으고 pipeline/dispatcher는 그 helper만 호출한다. unit test에서 owner mismatch, expiry boundary, concurrent reserve/janitor, commit response loss를 검증한다.

### H8-04 · dispatcher `s3:ListBucket`에 prefix condition이 없고 IAM acceptance가 GetObject를 확인하지 않는다

worker는 `visual-input/*` prefix condition을 갖지만 dispatcher는 bucket 전체 ListBucket으로 서술된다. 31-10 template test도 dispatcher의 List/Delete만 확인한다. janitor가 필요한 범위는 `visual-input/*`뿐이므로 bucket 전체 열거는 불필요한 개인정보 접근 확대다.

**제가 처리한다면:** dispatcher ListBucket에도 `StringLike s3:prefix: ["visual-input/*"]`를 고정하고 object ARN을 같은 prefix로 제한한다. test/simulate는 allowed prefix와 denied sibling prefix, Get/Delete allowed를 모두 확인한다.

### H8-05 · 31-01 Task 1b lifecycle 적용은 31-10 산출물보다 먼저인데 exact fallback/rollback artifact가 없다

Wave 0 Task 1b가 `visual_input_lifecycle_merged.json`을 적용하지만 이 파일은 Wave 5의 31-10 dry-run 산출물이다. “산출 전이면 최소 규칙”만 있고 파일 경로·JSON·before capture·put 후 get·실패 rollback이 없다. 이후 31-10 before artifact는 이미 mutation된 상태를 “before”로 기록한다.

**제가 처리한다면:** Wave 0 전용 exact lifecycle JSON을 31-01 산출물로 만들고 현재 lifecycle 404/기존 Rules를 별도 before 파일에 보존한다. 적용 후 get 검증과 rollback을 Task 1b에 넣고, 31-10은 그 실제 상태를 입력으로 merge한다. 또는 lifecycle mutation 자체를 31-12까지 미루고 Wave 0은 bucket 보안 속성만 만든다.

### H8-06 · 기존 bucket의 SecureTransport policy를 full replacement하며 before/merge/rollback이 없다

Task 1b의 `put-bucket-policy`는 bucket policy 전체 교체 API다. `exists-ok` 경로에서 기존 policy를 읽고 보존·merge한다는 계약이 없다. dedicated bucket이라도 이전 중단 실행이나 운영 policy가 있을 수 있다.

**제가 처리한다면:** 신규 생성 직후에만 known policy를 적용하거나, 기존 bucket이면 `get-bucket-policy` before artifact를 저장하고 Sid 기준 merge한다. 적용 후 BPA/SSE/ownership/policy/lifecycle을 검증하고 실패 시 생성 직후 bucket은 recoverable cleanup, 기존 bucket은 before policy로 rollback한다.

### H8-07 · bucket global-name 충돌 시 “다른 이름”이 downstream에 전파되지 않는다

31-01은 타 소유 선점 시 다른 이름을 쓰라고 하지만 smoke와 31-12 명령은 `sunity-motion-pilot-visual-input`을 하드코딩하고 template default도 고정이다. 대체명을 선택해도 계획의 이후 단계가 그 이름을 소비하는 단일 artifact/parameter가 없다.

**제가 처리한다면:** chosen bucket name을 승인 checkpoint 산출 JSON 또는 stack parameter 단일 출처로 기록하고 31-01 smoke, 31-10 dry-run, 31-12 CLI/SAM deploy가 모두 이를 읽게 한다. 하드코딩 grep과 alternative-name dry-run test를 추가한다.

### H8-08 · 31-12는 전용 Object Lock API를 요구하면서 실제 action/acceptance는 계속 `head_object`를 사용한다

31-12 must-have `:18`은 `get_object_retention` + `get_object_legal_hold`를 직접 호출한다고 수정됐지만 Task 2 action `:94`와 acceptance `:99`는 여전히 `head_object`의 세 필드를 확인한다. 실행자는 어느 계약을 따라야 할지 모른다.

**제가 처리한다면:** action/acceptance를 전용 API로 통일하고 `NoSuchObjectLockConfiguration`, retention/hold 미설정, AccessDenied를 각각 구분한다. 권한 부재를 “설정 없음”으로 처리하지 않는 실제 canary를 유지한다.

### H8-09 · 31-12 build gate가 상단의 5-alarm/IAM truth를 실제로 검증하지 않는다

31-12 `:16`은 CleanupBlocked/PairConflict 포함 5종과 worker ListBucket/PutMetricData를 요구하지만 Task 1 action `:71`과 acceptance `:78`은 기존 4 alarm 목록만 확인하고 새 두 alarm, worker ListBucket/PutMetricData, dispatcher janitor GetObject를 빠뜨린다.

**제가 처리한다면:** build artifact 검사 목록을 truth와 정확히 lockstep하고 YAML parser 기반 assert로 action/resource/condition까지 검사한다. 단순 grep은 잘못된 role/resource에 있는 action도 PASS시키므로 보조 수단으로만 쓴다.

---

## 5. MEDIUM

### M8-01 · 31-10 acceptance/done이 옛 lifecycle 파일명과 “3 alarm”을 유지한다

`31-10-PLAN.md:152`는 존재하지 않을 `infra/lifecycle_before.json + lifecycle_merged.json`을 요구하고 `:155`는 “3 alarm”이라 적는다. 본문 truth는 4 lifecycle 파일과 5 alarm이다.

**제가 처리한다면:** 네 파일명을 모두 열거하고 5 alarm 명칭을 acceptance/done에도 exact하게 맞춘다.

### M8-02 · 31-12 frontmatter artifact/files_modified가 옛 단일 lifecycle 파일을 가리킨다

`31-12-PLAN.md:7-10,28-33`은 `infra/lifecycle_before.json`만 기록한다. 실제 task는 visual_input/video before·merged 4파일을 소비하며 plan 자체와 UAT도 수정한다.

**제가 처리한다면:** frontmatter artifact를 네 파일 또는 정확한 두 before 파일로 갱신하고 summary manifest가 실제 파일 존재/hash를 검증하게 한다.

### M8-03 · 모델 계약의 cleanupVerified 설명이 done 전용으로 남아 있다

31-02 Task 2는 `cleanupVerifiedAtMs`를 “correctedPose done finalize validator 요구”라고 쓴다. Task 3은 done/failed 공통이라고 한다. shared model 주석이 구현자의 잘못된 조건 분기를 유도한다.

**제가 처리한다면:** “correctedPose terminal(done|failed) 공통”으로 고치고 model/finalizer/worker 세 면 lockstep grep test를 둔다.

### M8-04 · create duplicate 테스트의 기대 결과가 acquisition status별로 분리되지 않는다

31-09은 same-seq duplicate를 무조건 외부 0으로 적지만 최초 acquired invocation과 이후 busy duplicate를 구분하지 않는다. B8-01을 고친 뒤에는 동일 입력 중 정확히 하나가 acquired되어 외부 create 1회를 해야 한다.

**제가 처리한다면:** 두 concurrent messages 결과를 `acquired=1, busy/stale=1, vendor create total=1`로 명시하고 lease expiry/unconfirmed 케이스를 별도 테스트한다.

### M8-05 · `VisualOrphanSweepDeleted` metric은 단순 성공량뿐이고 미처리 최고령/실패량을 보여주지 않는다

삭제 성공 count는 janitor 정체를 탐지하지 못한다. dispatcher가 계속 timeout하거나 HEAD 권한이 깨져 성공 0이어도 alarm이 없다.

**제가 처리한다면:** `VisualOrphanOpenCount`, `VisualOrphanOldestAgeMs`, `VisualOrphanSweepFailed`, reservation equivalents를 방출하고 oldest age/failure alarm을 privacy 운영 gate에 포함한다.

---

## 6. 8차 수정 우선순위

1. **31-02 + 31-09:** `begin_visual_job_create`를 실제 shared transactional helper로 정의하고 acquired/busy/resume/stale/unconfirmed 상태와 최초 happy path를 고정한다.
2. **31-02 + 31-09:** correctedPose terminal validator를 unconditional kind gate로 바꾸고 cleanup_blocked clear+finalize를 한 transaction으로 만든다.
3. **31-02 + 31-09 + 31-10:** per-invocation reservation state machine과 producer/janitor 공유 CAS를 설계한다.
4. **31-09 + 31-10:** janitor bounded cursor/claim/retry/metrics와 정확한 S3 IAM(`GetObject`, prefix-scoped `ListBucket`)을 넣는다.
5. **31-09 + VALIDATION:** pair를 user terminal 밖 durable outbox로 분리하거나 durable requirement를 명시적으로 amend한다.
6. **31-01 + 31-10 + 31-12:** lifecycle/policy before·merge·rollback, chosen bucket name 전파, 4파일/5alarm artifact를 lockstep한다.
7. **31-12:** Object Lock 전용 API와 build IAM/alarm acceptance를 실제 action까지 일치시킨다.

---

## 7. 다음 수정의 실행 허용 조건

다음 개정에서 아래 조건이 모두 문서·테스트에 들어오기 전에는 Phase 31 실행을 권하지 않는다.

1. 최초 reserved create 한 건이 `begin_visual_job_create`에서 acquired되어 vendor create 정확히 1회에 도달한다.
2. concurrent same-seq create 둘 중 acquired는 정확히 하나이고 나머지는 busy/stale이며 외부 create 총 1회다.
3. `begin_visual_job_create`가 31-02 files/action/acceptance에 실제 구현 함수로 존재한다.
4. correctedPose done/failed 모두 inputSealed=True, cleanupVerified>0, privacyBlocker=None을 unconditional 요구한다.
5. inputSealed=False done/failed와 cleanupVerified=0 done/failed 네 조합이 helper에서 거부된다.
6. cleanup 5회 실패→cleanup_blocked→후속 remaining 0이 blocker clear+terminal 한 transaction으로 끝난다.
7. template 전체에 `s3:HeadObject`가 0이고 dispatcher에 prefix-scoped ListBucket + GetObject + DeleteObject가 있다.
8. per-invocation reservation은 서로 다른 expectedKeys를 overwrite하지 않는다.
9. janitor claim과 producer reserve가 같은 reservation CAS를 공유해 “job reserve 후 input delete” interleaving이 불가능하다.
10. reservation TTL이 producer timeout/margin과 단일 상수 관계로 검증된다.
11. reservation/orphan 1,200건이 bounded cursor로 starvation 없이 drain되고 oldest-age alarm이 존재한다.
12. pair network 실패가 user terminal을 막지 않으면서 durable 재처리되거나, 요구 축소가 belle 결정으로 명시된다.
13. Wave 0 bucket policy/lifecycle은 before artifact, merge, put 후 get, rollback 및 chosen-name 전파를 가진다.
14. 31-10/31-12의 frontmatter/read_first/action/acceptance/done이 lifecycle 4파일과 5 alarm으로 일치한다.
15. Object Lock canary action이 `get_object_retention`/`get_object_legal_hold`를 실제로 호출하고 AccessDenied를 fail-closed한다.

---

## 8. 최종 판단

**이번 8차 리뷰 결과는 승인 불가다.**

7차 수정으로 인프라 전제와 privacy cleanup의 큰 방향은 훨씬 명확해졌다. 다만 이번에 추가된 create CAS와 reservation/janitor가 아직 선형화된 상태 머신이 아니어서, 정상 create가 멈추거나 유효 입력이 삭제되거나 hard-crash object가 추적에서 빠지는 interleaving이 존재한다. finalizer 역시 `inputSealed=False` 우회와 cleanup_blocked 회복 불능을 동시에 가진다.

제가 실제 구현 책임자라면 이 상태에서 Wave 1을 시작하지 않는다. 위 6 blocker를 먼저 계약과 fault test로 닫고, High 9건을 같은 targeted replan에서 정리한 뒤 9차 리뷰로 실행 가능 여부를 다시 판정한다.
