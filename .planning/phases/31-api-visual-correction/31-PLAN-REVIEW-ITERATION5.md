# Phase 31 계획 5차 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-19  
**리뷰 범위:** 5차 개정된 `31-01-PLAN.md` ~ `31-13-PLAN.md`, `31-VALIDATION.md`, 1~4차 리뷰 및 계획이 직접 참조하는 현재 코드  
**리뷰 방법:** 4차 blocker/High 해소 추적, claim lease 시간축 분석, upload-first 동시성·terminal replay 분석, versioned S3 exact-delete 반례 검증, postprocessing crash/HMAC rotation/consent race 분석, dispatcher bounded scan 및 배포 checkpoint 재검증  
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 리뷰 없이 직접 검토했다. AWS 공식 문서는 Standard SQS 전달 보장 확인용 1차 자료로만 사용했다.  
**최종 판정:** **BLOCK / TARGETED REPLAN REQUIRED**

---

## 1. 결론

5차 개정은 4차 blocker 5개 중 4개를 해소했다.

- `outboxSeq + action + generation` CAS로 늦은 ACK가 다음 continuation을 덮는 문제를 막았다.
- production 경로를 async taskId 모델로 제한해 URL을 저장하지 않는 sync 경로의 복구 모순을 제거했다.
- moderation 재생성 전에 `taskId/attempt/lease`를 비우고 generation을 올린다.
- calibration manifest를 before/after pair와 각각의 hash로 바꿨다.
- display/training judge confidence와 pose tolerance를 4개 env로 분리하고 strict ordering build gate를 넣었다.
- correctedPose 성공 경로에 durable `postprocessing` state를 도입했다.
- `VersionId`를 payload에 보존하고 E2E에서 `list-object-versions` 0을 확인하도록 강화했다.

방향은 맞다. 그러나 새 계약이 주장하는 안전성보다 구현 계획이 약한 지점이 세 군데 남았다.

1. claim 함수는 같은 seq를 먼저 `already_claimed`로 반환하면서 동시에 “lease 만료 후 재claim”을 약속한다. 둘을 구분할 조건과 redelivery 정책이 없어 claim 직후 crash가 action을 영구 고착시킬 수 있다.
2. source/staging PUT은 check-then-put이며 재시도 때 새 version을 만들 수 있다. job에 기록된 한 VersionId만 삭제해서는 기록되지 않은 version을 지울 수 없다. terminal replay는 완료된 job 앞에 새 source version을 만들 수도 있다.
3. pair store는 commit marker가 이미 있는지 확인하지 않고 매번 3개 object를 PUT한다. postprocess crash와 HMAC active key rotation이 겹치면 동일 분석에서 서로 다른 pair가 생긴다.

따라서 현재 계획은 Wave 1 실행 전에 이 세 계약을 수정해야 한다.

### 발견 수

| 심각도 | 수 | 의미 |
|---|---:|---|
| BLOCKER | 3 | 실행 전 계획 수정 필수 |
| HIGH | 8 | 같은 targeted replan에서 해결 필요 |
| MEDIUM | 5 | 배포 전 계약·검증 보강 필요 |

---

## 2. 4차 리뷰 지적 해소 추적

| 4차 ID | 5차 상태 | 판단 |
|---|---|---|
| B4-01 outbox ACK/action claim | **부분 해소** | outboxSeq CAS는 해소. claim lease 만료 분기와 메시지 redelivery 계약이 모순되어 crash 복구가 미완성 |
| B4-02 sync image 복구 | **해소** | production async-only, sync 결과 typed `vendor_error`, calibration/release gate 반영 |
| B4-03 moderation stale task | **해소** | `taskId=None`, attempt/lease clear, generation+1 계약 반영. 단 requestKey 생성 시 새 generation 사용 보장은 High로 남음 |
| B4-04 pair manifest | **해소** | before/after path·hash·provenance 및 after keypoint 대상 분리 |
| B4-05 training confidence 소비 | **해소** | 4개 calibration env와 strict ordering build gate 반영 |
| H4-01 durable pair/cleanup | **부분 해소** | postprocessing state는 맞지만 pair store 자체의 재실행 멱등성과 retry 상태가 없음 |
| H4-02 IAM canary | **해소** | send-only iam_probe, production receive/delete 금지로 수정 |
| H4-03 versioned PII cleanup | **미해소** | VersionId 기록은 단일 정상 경로만 다룬다. concurrent PUT/crash/replay의 untracked version이 남음 |
| H4-04 Object Lock | **부분 해소** | default retention fail-closed는 반영. default 없는 enabled bucket의 실제 PUT→version delete canary가 checkpoint에 명시되지 않음 |
| H4-05 JPEG→PNG | **해소** | decode 후 EXIF 제거·PNG 재인코딩·PNG hash/staging 계약 반영 |
| H4-06 decode 공통화 | **해소 방향** | `safe_decode_image` 공유. typed failure 매핑은 Medium으로 남음 |
| H4-07 finalize tampering | **해소** | uid/analysisId/kind를 job에서 파생하고 모순 terminal 조합 거부 |
| H4-08 dispatcher pagination | **부분 해소** | 첫 page 고정 starvation은 개선. max_scan 이후 cursor 지속성이 없어 1,000건 초과 시 새 starvation 발생 |
| H4-09 RSS 플랫폼 | **해소 방향** | Linux/container 재확인과 fresh subprocess 기준 유지 |
| H4-10 content-type mismatch | **대체로 해소** | 호출 경계 allowlist 반영. media type exact parsing은 Medium |
| H4-11 committed pair consumer | **부분 해소** | helper 도입은 맞음. marker가 가리키는 before/after 존재/hash 검증과 pagination이 없음 |

---

## 3. BLOCKERS

### B5-01 · claim lease 계약이 자기모순이며 claim 직후 crash가 action을 고착시킬 수 있다

**근거**

- `31-02-PLAN.md:124`는 `claimedOutboxSeq == outbox_seq`이면 조건 없이 `already_claimed`를 반환한다고 정의한다.
- 같은 문단은 “lease 만료 후 재claim 허용”도 약속한다. 그러나 만료 확인이 어느 분기보다 먼저인지, owner가 바뀌는지, 반환값이 무엇인지 정의하지 않는다.
- `31-09-PLAN.md:94`는 `already_claimed`를 외부 호출 0 + 정상 소비로 처리한다.
- Validation은 duplicate와 old seq만 다루고 “claim commit 직후 side-effect 전 crash → 만료 전 재전달 → 만료 후 재전달” 시간축을 검증하지 않는다.

**재현 순서**

1. worker A가 `{action:'judge', outboxSeq:7}`을 claim한다.
2. Firestore claim commit 직후 Gemini 호출 전에 A가 crash한다.
3. SQS가 같은 message를 다시 전달한다.
4. worker B는 같은 seq라 `already_claimed`를 받고 message를 정상 ACK한다.
5. 최초 receipt도 결국 사라지면 lease가 만료되어도 다시 실행할 message가 없다.
6. job은 `judging`, `dispatchState='sent'`에 남고 dispatcher도 재발행하지 않는다.

Standard SQS는 동일 message가 두 번 전달될 수 있으므로 consumer의 idempotency와 crash recovery를 함께 설계해야 한다. 단순히 duplicate를 정상 소비하는 것만으로는 부족하다. 공식 근거: [Amazon SQS at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html)

**영향**

poll/fetch/judge/pose_check/postprocess 어느 action이든 side-effect 전 고착될 수 있다. 특히 postprocess 고착은 canonical 결과가 있어도 analysis가 계속 pending이며 임시 개인정보도 삭제되지 않는다.

**제가 해결한다면**

claim 반환 상태와 queue 처리를 다음처럼 명시한다.

```text
stale
  generation/action/outboxSeq 불일치
  -> 정상 ACK, 외부 호출 0

claimed
  미claim 또는 같은 seq의 lease 만료
  -> owner/lease를 원자 갱신하고 action 실행

busy
  같은 seq + lease 아직 유효
  -> 정상 ACK 금지
  -> batchItemFailures 또는 ChangeMessageVisibility로 lease 뒤 재전달

completed/stale
  이미 다음 outboxSeq 또는 terminal
  -> 정상 ACK
```

- lease는 action별 worst-case runtime보다 길고 SQS visibility 1,800초보다 짧게 둔다. 300초 Lambda timeout이면 최소한 timeout·network margin을 포함한 수치와 근거를 template/코드 한 곳에서 공유한다.
- `claimedOutboxSeq`만 두지 말고 `claimState`, `claimLeaseExpiresAt`, `claimOwner`를 검사한다.
- action 성공 transition은 현재 claim owner와 seq도 CAS하여 lease를 잃은 worker가 늦게 결과를 쓰지 못하게 한다.
- dispatcher가 `dispatchState='sent' + lease expired + nonterminal`도 복구 대상으로 재발행하거나, SQS redelivery가 lease 이후 반드시 남도록 `busy` message를 실패 처리한다. 두 방식 중 하나를 계획에 고정한다.
- fault test: claim 직후 crash, 만료 전 retry, 만료 후 retry, 늦은 A 결과, 외부 호출 최대 1회, terminal 도달을 모두 검증한다.

---

### B5-02 · recorded VersionId 한 개 삭제로는 concurrent PUT·crash·terminal replay의 개인정보 version을 전부 제거할 수 없다

**근거**

- `31-10-PLAN.md:128`은 `head_object`에서 부재를 확인한 뒤 일반 `put_object`를 수행하는 check-then-put이다. `IfNoneMatch='*'` 또는 동등한 원자 조건이 없다.
- 같은 key에 두 invocation이 동시에 HEAD 404를 보면 각각 V1/V2를 생성할 수 있다. reserve 승자 한 명의 `sourceVersionId`만 job payload에 남는다.
- `31-09-PLAN.md:122`의 staging도 매 retry마다 `upload_file`한 후 최신 `VersionId` 하나만 기록한다.
- `31-09-PLAN.md:125`는 payload에 기록된 source/staging VersionId만 지정 삭제한다.
- `31-10-PLAN.md:128`은 completed job replay에서도 reserve 전에 source HEAD/PUT을 수행한다. worker가 이미 source를 삭제했다면 replay가 새 version을 만든 뒤 `existing done → no-op`하여 즉시 cleanup 주체가 없다.
- 반면 `31-12-PLAN.md:136`은 해당 prefix의 Versions와 DeleteMarkers가 모두 0이어야 PASS라고 선언한다.

**재현 경로 A — concurrent source upload**

1. pipeline A/B가 같은 분석을 동시에 처리한다.
2. 둘 다 source key HEAD 404.
3. A가 V1, B가 V2를 PUT한다.
4. 한 reserve만 job을 생성하고 그 호출이 관찰한 VersionId만 payload에 기록한다.
5. postprocess가 그 version만 삭제한다. 나머지 version은 lifecycle까지 남는다.

**재현 경로 B — staging crash**

1. fetch가 deterministic staging key에 V1을 upload한다.
2. `transition_visual_job` 전에 crash한다.
3. lease 만료 후 fetch 재실행이 같은 key에 V2를 upload한다.
4. V2만 job에 기록·삭제되고 V1이 남는다.

**재현 경로 C — terminal replay**

1. job done 후 postprocess가 source version을 삭제한다.
2. pipeline hook이 재실행되어 reserve 전에 같은 source를 새로 PUT한다.
3. reserve는 existing done을 반환한다.
4. producer가 no-op하므로 새 version이 즉시 삭제되지 않는다.

**영향**

계획의 핵심 개인정보 약속인 “versioned noncurrent PII 잔존 0”이 정상 동시성·재시도에서도 깨진다. E2E 단일 경로가 우연히 PASS해도 운영 중 orphan version이 누적될 수 있다.

**제가 해결한다면**

- source 최초 생성은 `put_object(..., IfNoneMatch='*')` 같은 조건부 write를 사용한다. 412이면 HEAD 후 full SHA-256 metadata를 검증해 기존 object를 재사용한다.
- terminal job fast-path를 upload 전에 read-only로 확인한다. correctness는 여전히 reserve transaction이 결정하되, 이번 invocation이 새 version을 만들었다면 `createdThisInvocation + VersionId`를 보존하고 reserve가 done/failed를 반환할 때 즉시 삭제한다.
- staging은 deterministic key + HEAD/full-hash reuse를 적용한다. 재실행이 같은 normalized PNG면 새 version을 만들지 않는다.
- 가장 강한 안전망은 job에 단일 VersionId만 믿지 않고 `visual-input/{uid}/{analysisId}/` exact prefix의 **모든 Versions와 DeleteMarkers를 페이지 끝까지 열거·삭제**하는 cleanup helper다. key prefix는 job에서 파생하고 범위를 exact 분석 prefix로 제한한다.
- cleanup은 성공할 때까지 durable state로 유지하고 `remainingVersionCount==0`을 확인한 뒤 finalize한다.
- 테스트: concurrent source PUT, staging put 후 transition 전 crash, terminal replay, pagination된 multiple versions/delete markers를 만들고 cleanup 뒤 정확히 0을 검증한다.

---

### B5-03 · pair store가 실제로는 재실행 멱등하지 않아 postprocess crash와 HMAC rotation에서 중복 학습쌍이 생성된다

**근거**

- `31-09-PLAN.md:125`는 “pair commit-marker 존재 시 skip”으로 재실행 멱등성을 주장한다.
- 그러나 `31-07-PLAN.md:78`의 `store_training_pair` 계약은 active HMAC key로 pair_id를 계산한 뒤 항상 `before → after → meta`를 PUT한다. 기존 meta HEAD/GET·hash 대조·skip 절차가 없다.
- HMAC key set은 rotation을 지원하고 active version이 바뀔 수 있다. pair_id는 key에 의존하므로 같은 uid/analysis/joint도 v1과 v2에서 다른 prefix가 된다.
- postprocess는 pair 저장 뒤 finalize 전에 crash할 수 있으며 Validation이 이 crash를 의도적으로 허용한다.

**재현 순서**

1. postprocess A가 active key v1으로 pair P1의 before/after/meta를 저장한다.
2. finalize 전에 crash한다.
3. 운영자가 active key를 v2로 rotation한다.
4. postprocess retry가 v2로 pair P2를 새로 저장한다.
5. P1과 P2 모두 valid commit marker라 consumer가 동일 분석의 두 pair를 학습 데이터로 읽는다.

key가 바뀌지 않아도 같은 key에 재-PUT하면 versioned bucket에서 before/after/meta의 새 version이 생기므로 “한 번만 저장” 계약이 아니다.

**영향**

학습 데이터 중복, consent deletion inventory 불일치, version 증가, 비용 증가가 발생한다. 4차에 추가한 durable postprocessing의 핵심 불변식이 실제 store 함수에서 성립하지 않는다.

**제가 해결한다면**

- `pose_checking → postprocessing` transition에서 `pairId`와 `pairHmacKeyVersion`을 **한 번 계산해 job에 고정**한다. postprocess 재시도는 active key를 다시 선택하지 않는다.
- `store_training_pair`는 caller가 고정한 pair id/key version을 받고 먼저 meta를 읽는다.
  - meta가 있고 before/after hash, consentVersion, joint, model/provenance가 일치하면 PUT 0으로 idempotent success.
  - meta가 있으나 불일치하면 overwrite하지 않고 typed conflict로 실패한다.
  - meta가 없으면 조건부 PUT 또는 transaction에 준하는 marker-last 절차를 실행한다.
- meta에 `beforeSha256`, `afterSha256`, source generation/provenance를 넣고 consumer helper도 payload HEAD/hash를 검증한다.
- fault test: pair commit 후 finalize 전 crash + active key rotation → committed pair prefix 1개, before/after/meta version 각 1개, 재PUT 0을 검증한다.

---

## 4. HIGH

### H5-01 · pairEligible을 미리 고정해 두어 저장 직전 consent 철회를 반영하지 못한다

`31-09-PLAN.md:124`는 pose_check 시점의 `learningOptIn`으로 `pairEligible`을 계산하고 postprocess는 이 bool만 신뢰한다. 두 action 사이 또는 retry 대기 중 사용자가 opt-out하면 저장 시점에는 동의가 없는데도 pair가 생성된다.

**해결:** postprocess가 S3 PUT 직전에 analysis의 현재 `learningOptIn is True`, consentVersion, capturedAt/revokedAt을 다시 읽는다. 철회면 PUT 0 + `pairStoreStatus='skipped_consent'`. 이미 저장된 뒤의 철회는 31-07 삭제 workflow로 연결하고 UAT에 저장 전·후 철회 두 경로를 넣는다.

### H5-02 · “제한 retry”가 durable state로 정의되지 않았다

`31-09-PLAN.md:125`는 pair store 실패를 제한 retry한다고 하지만 `pairAttempt`, backoff, max, 새 outboxSeq, 재시도 후 terminal 규칙이 없다. 한 invocation 내부 반복이면 side-effect-per-action 원칙을 깨고, 바로 finalize하면 retry가 아니다.

**해결:** `postprocessing → postprocessing` self-loop에 `pairAttempt`, `nextDispatchAtMs`, 새 outboxSeq를 기록한다. max 초과 후에만 `pairStoreStatus='failed'`로 done을 허용한다. cleanup은 개인정보 삭제이므로 제품 상태 비차단으로 취급하지 말고 성공 또는 명시적 privacy blocker 전까지 terminal finalize하지 않는다.

### H5-03 · moderation retry의 requestKey가 이전 generation으로 만들어질 수 있다

`31-09-PLAN.md:97`은 `retry_ready → creating` transition 내부에서 generation+1이 되지만 `requestKey=f"{jobId}:gen{generation}"`은 transition 전 `job` 값으로 작성된 것처럼 기술되어 있다. 결과적으로 persisted generation=2인데 requestKey가 gen1일 수 있다.

**해결:** transition helper가 갱신된 job snapshot을 반환하게 하고 requestKey는 새 generation으로 같은 transaction에서 생성한다. `requestKey suffix == persisted generation`을 validator와 test로 강제한다.

### H5-04 · create의 두 번째 전이뿐 아니라 failure finalize도 갱신된 job snapshot이 필요하다

`31-09-PLAN.md:95`는 create 성공 후 `_advance`에 최신 job을 쓰라고 경고하지만 sync/typed failure의 `finalize_visual_job`도 첫 transition 이후 새 generation/outboxSeq를 사용해야 한다. inbound message 값을 쓰면 finalize가 stale no-op하여 job이 creating에 남는다.

**해결:** `_action_create`의 모든 후속 경로가 transition 반환 snapshot 하나만 사용하도록 API를 구조화한다. retry generation에서 vendor typed failure, sync result, taskId 성공 각각을 테스트하고 creating 잔존 0을 확인한다.

### H5-05 · correctedPose 실패 경로는 durable cleanup을 우회한다

계획은 pose success만 `postprocessing`으로 보내고 create/poll/fetch/judge/pose failure는 직접 finalize + best-effort delete한다. delete 실패나 finalize 경계 crash에서 source/staging PII가 즉시 삭제되지 않는다. 성공 경로에만 durable cleanup을 둔 것은 privacy invariant와 맞지 않는다.

**해결:** correctedPose의 모든 terminal intent를 `postprocessing`으로 보낸다. job에 `pendingTerminalState`, `pendingFailureReason`, 실패 메타를 저장하고 pair는 done+eligible일 때만 수행한다. exact-prefix cleanup 성공 뒤 한 번의 finalize로 done/failed를 기록한다.

### H5-06 · max_scan=1000 이후 문서는 반복 실행에서도 영구 starvation될 수 있다

`31-02-PLAN.md:127`은 매 invocation마다 document name 처음부터 최대 1,000개만 스캔한다. pending backlog가 지속적으로 1,000개를 넘으면 그 뒤 문서는 다음 분에도 다시 스캔 범위 밖이다. `truncated` metric은 있으나 `31-10-PLAN.md:129`에는 이에 대한 alarm이 없다.

**해결:** last document cursor를 Firestore에 durable 저장해 다음 invocation이 이어서 스캔하고 끝에서 wrap한다. 더 나은 해법은 필요한 composite index를 IaC로 선언해 due query를 직접 하는 것이다. `OutboxScanTruncatedAlarm`과 1,200개 이상을 여러 invocation으로 전부 drain하는 테스트를 추가한다.

### H5-07 · Object Lock enabled/default 없음 분기의 실제 삭제 가능성을 검증하지 않는다

`31-10-PLAN.md:130`은 이 분기에 canary 검증이 필요하다고 기록하지만 `31-12` checkpoint는 default retention/403 처리만 강조하고 비민감 canary의 PUT→VersionId DELETE→versions 0 절차를 명시하지 않는다.

**해결:** live mutation 전에 전용 non-PII canary prefix에 PUT, 응답 VersionId 확인, retention/legal hold HEAD 확인, 그 VersionId 삭제, `list-object-versions` 0을 수행한다. 한 단계라도 실패하면 feature flag OFF와 별도 non-locked bucket을 요구한다.

### H5-08 · committed marker만 검사하고 실제 before/after payload 존재·hash를 검증하지 않는다

`31-07-PLAN.md:78`의 `list_committed_pairs/load_committed_pair`는 meta schema만 확인한다. 운영 삭제·부분 복구·version lifecycle로 before 또는 after가 없거나 변조되어도 valid pair로 반환될 수 있다.

**해결:** meta에 두 payload hash/size를 저장하고 helper가 HEAD/GET으로 둘의 존재·hash를 확인한 pair만 반환한다. 불일치는 metric과 quarantine 대상으로 분리한다.

---

## 5. MEDIUM

### M5-01 · 모든 decode 오류를 `judge_input_too_large`로 매핑하면 운영 진단이 왜곡된다

size/pixel 초과는 `judge_input_too_large`, corrupt/unsupported/mismatched format은 `invalid_output`으로 분리한다. 로그와 metric도 reason별로 나눈다.

### M5-02 · Content-Type은 prefix가 아니라 정규화한 media type exact match가 안전하다

`Content-Type.split(';', 1)[0].strip().lower()`를 allowlist exact membership으로 검사한다. `image/pngfoo` 같은 prefix 유사값을 거부하는 test를 추가한다.

### M5-03 · `Image.MAX_IMAGE_PIXELS` 전역 변경은 process 내 다른 decode에 영향을 준다

모듈 import 시 한 번 고정하거나 명시적 warning/error context로 감싼다. request마다 전역값을 바꾸지 않고 concurrent decode test를 둔다.

### M5-04 · canonical result의 재시도 version과 보존 정책이 불명확하다

pose_check 재실행이 같은 canonical key에 copy하면 versioned 결과가 늘 수 있다. canonical은 hash 대조 후 reuse하고, result version 보존/삭제 정책을 문서화한다.

### M5-05 · pair consumer listing pagination 계약이 없다

`list_objects_v2`/version listing은 continuation token을 끝까지 처리해야 한다. 1,000개 초과 committed pair fixture로 누락 0을 검증한다.

---

## 6. 제가 적용할 targeted replan

전체 13개 plan을 다시 쓸 필요는 없다. 아래 6개 plan과 Validation만 수정하면 된다.

| 순서 | 대상 | 필수 수정 |
|---:|---|---|
| 1 | 31-02 | claim의 `claimed/busy/stale` 시간 조건, owner CAS, lease-expired redispatch, transition 반환 snapshot, durable scan cursor |
| 2 | 31-07 | fixed pairId/keyVersion, existing marker hash 검증·skip, payload hash meta, paginated/validated consumer helper |
| 3 | 31-09 | busy 메시지 ACK 금지, 모든 correctedPose terminal intent의 postprocessing 경유, durable pair/cleanup retry, consent 재확인, fresh generation requestKey |
| 4 | 31-10 | conditional source PUT, terminal replay cleanup, staging reuse 계약, truncated alarm, Object Lock canary 전제 |
| 5 | 31-12 | 실제 non-PII Object Lock delete canary, multi-version exact-prefix cleanup E2E |
| 6 | 31-VALIDATION | claim-crash 시간축, concurrent PUT, staging crash, terminal replay, HMAC rotation postprocess, consent race, 1,200 pending drain 추가 |

### 수정 후 필수 fault matrix

| 시나리오 | 기대 결과 |
|---|---|
| claim commit 직후 crash | 만료 전 외부 0, 만료 후 정확히 한 worker가 재claim, terminal 도달 |
| old owner가 lease 만료 후 늦게 결과 write | owner/seq CAS 실패, 새 worker 결과 보존 |
| 동일 source 두 invocation 동시 HEAD/PUT | object content 1개, untracked version 0 |
| staging PUT 후 transition 전 crash | retry가 기존 hash를 reuse, extra version 0 |
| terminal job producer replay | 신규 source version 0 또는 created version 즉시 삭제 |
| pair commit 후 finalize 전 crash + HMAC rotation | pair prefix 1개, second PUT 0 |
| pose_check 후 opt-out, postprocess 전 | pair PUT 0, skipped_consent 기록 |
| pair/cleanup 일시 실패 | durable backoff 후 재개, max/terminal 규칙 일관 |
| pending 1,200개 | 여러 dispatcher invocation 뒤 1,200개 모두 발행, starvation 0 |
| Object Lock enabled/default 없음 | canary VersionId delete 및 versions 0, 실패 시 flag OFF |

---

## 7. 실행 허용 기준

다음 조건을 문서와 테스트에 모두 고정한 뒤에만 Wave 1 실행을 권고한다.

- [ ] same seq + active lease와 same seq + expired lease가 서로 다른 반환/queue 처리로 정의됨
- [ ] claim 후 crash message가 lease 만료 뒤 반드시 재실행될 복구 주체가 있음
- [ ] source/staging concurrent·retry PUT이 untracked version을 만들지 않음
- [ ] correctedPose success/failure 모두 exact-prefix Versions/DeleteMarkers 0 뒤 finalize됨
- [ ] terminal producer replay가 새 source PII를 남기지 않음
- [ ] pairId/HMAC key version이 postprocessing 진입 시 고정됨
- [ ] existing commit marker의 before/after hash 일치 시 PUT 0, 불일치 시 overwrite 0
- [ ] pair 저장 직전 current consent를 재검증함
- [ ] postprocess pair/cleanup retry가 durable self-loop로 정의됨
- [ ] dispatcher가 max_scan보다 큰 backlog를 순환하며 전부 처리함
- [ ] Object Lock canary delete가 live checkpoint에 명시됨
- [ ] 위 조건이 `31-VALIDATION.md` fault matrix와 task별 automated test에 연결됨

---

## 8. 최종 판단

5차 계획은 4차보다 분명히 좋아졌고, 기존 blocker 다수는 실제로 해소됐다. 그러나 현재 남은 세 blocker는 단순 설명 보강이 아니다.

- claim crash는 job을 영구 pending으로 만들 수 있다.
- S3 version 추적 누락은 개인정보를 lifecycle까지 남길 수 있다.
- pair store 비멱등은 동일 분석을 중복 학습 데이터로 만들 수 있다.

세 문제 모두 계획이 명시적으로 약속한 “crash-resumable”, “version 잔존 0”, “idempotent commit-marker”를 깨므로 실행 단계에서 구현자가 임의로 메우게 두면 안 된다. 위 targeted replan과 fault matrix를 반영한 뒤 6차 리뷰에서는 새 범위 확장 없이 이 세 불변식의 완전한 closure만 확인하면 된다.
