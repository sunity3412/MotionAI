# Phase 31 계획 4차 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-19  
**리뷰 범위:** 4차 개정된 `31-01-PLAN.md` ~ `31-13-PLAN.md`, `31-VALIDATION.md`, 1~3차 리뷰 및 계획이 참조하는 현재 코드  
**리뷰 방법:** 3차 blocker/High별 해소 추적, outbox send/ACK/중복 전달 경쟁 분석, sync/async vendor 경로 대조, moderation generation 재시도 추적, calibration 입출력 스키마와 env 소비 대조, versioned S3 개인정보 삭제 및 배포 checkpoint 재검증  
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 리뷰 없이 직접 검토했다. AWS 공식 문서는 SQS 중복 전달과 S3 Object Lock 동작 확인용 1차 자료로만 사용했다.  
**최종 판정:** **BLOCK / TARGETED REPLAN REQUIRED**

---

## 1. 결론

4차 개정은 3차 blocker의 본질을 대부분 정확히 이해하고 반영했다.

- 모든 nonterminal 전이에 `nextAction + dispatchState=pending`을 같은 Firestore transaction으로 기록한다.
- worker와 dispatcher를 분리하고 dispatcher에 전용 reserved concurrency를 준다.
- terminal job과 analysis visual status를 `finalize_visual_job` 다중 문서 transaction으로 묶는다.
- correctedPose는 S3 upload/head 성공 뒤에만 reserve하며, analysis pending도 reserve transaction 안에서 쓴다.
- signed vendor URL 저장을 제거하고 fetch에서 `taskId`를 재-poll한다.
- calibration을 31-05/06 뒤의 새 31-13 plan으로 이동하고 실행 가능한 harness를 추가한다.
- judge/pose payload 경계, pair partial cleanup, HMAC validator, versioned deletion, historical joint registry를 보강했다.

이 정도면 3차 설계보다 훨씬 실행 가능하다. 특히 **B3-02 atomic finalize와 B3-03 upload-first는 해소됐다고 판단**한다.

다만 새 범용 outbox에 `outboxSeq/dispatchToken`이 없다. `mark_visual_job_dispatched`가 generation만 확인하기 때문에 이전 action의 늦은 ACK가 다음 action의 pending outbox를 sent로 바꿀 수 있다. 또한 standard SQS 중복 메시지를 action 실행 전에 claim하지 않아 self-loop poll과 유료 judge가 중복 실행될 수 있다.

추가로 sync 이미지 성공 경로는 URL을 저장하지 않으면서 taskId도 없으므로 fetch에서 복구할 방법이 없고, moderation 재시도는 이전 taskId를 지운다는 계약이 없어 create crash 복구가 과거 blocked task로 되돌아간다. calibration은 before/after judge를 호출하려 하지만 manifest에 pair 경로가 하나뿐이며, 산출하는 training confidence는 배포 env에서 소비되지 않는다.

따라서 현재 실행 차단 사유는 5개다.

1. outbox ACK가 action instance를 식별하지 않아 다음 continuation을 소거할 수 있다.
2. sync image 성공은 taskId 없이 fetching으로 넘어가 fresh URL을 다시 얻을 수 없다.
3. moderation retry가 이전 taskId/attempt를 보존해 crash 시 과거 blocked task를 재개한다.
4. calibration manifest가 before/after pair를 표현하지 않아 실제 judge harness가 실행 불가능하다.
5. calibration의 `training_confidence`가 worker/template에서 소비되지 않아 training gate가 측정값과 다르다.

### 발견 수

| 심각도 | 수 | 의미 |
|---|---:|---|
| BLOCKER | 5 | Wave 1 실행 전 계획 수정 필수 |
| HIGH | 11 | 같은 재계획에서 해결 필요 |
| MEDIUM | 6 | 배포 전 계약·검증 보강 필요 |

---

## 2. 3차 리뷰 지적 해소 추적

| 3차 ID | 4차 상태 | 판단 |
|---|---|---|
| B3-01 per-transition continuation | **부분 해소** | durable nextAction outbox와 별도 dispatcher 도입은 맞다. action instance/ACK ownership과 duplicate claim이 없어 새 경쟁 창이 생김 |
| B3-02 terminal dual-write | **해소** | `finalize_visual_job` 다중 문서 transaction, commit response loss test, reconciler 보조 반영 |
| B3-03 input-ready/pending 순서 | **해소** | immutable upload-first + reserve 안에서 analysis pending/outbox 원자 기록, 늦은 pending 제거 |
| H3-01 vendor URL 저장 | **대체로 해소** | taskId 재-poll + 3면 URL 부재 테스트. sync 결과는 taskId가 없어 새 blocker 발생 |
| H3-02 calibration 순서 | **부분 해소** | 31-13 실행 harness와 DAG는 맞음. manifest pair 스키마와 training threshold 소비가 빠짐 |
| H3-03 Gemini 20MB | **해소 방향** | 2048px JPEG 정규화 + serialized 16MB 상한 + typed failure 반영 |
| H3-04 pose 8MB | **해소 방향** | b64/decoded/pixel/dimension 상한과 worker 1024px 정규화 반영 |
| H3-05 redirect test | **해소** | TLS local server + injected SSL context로 실제 30x handler 도달 |
| H3-06 RSS test | **해소** | fresh subprocess + macOS/Linux 단위 정규화 + Linux/container 재확인 |
| H3-07 partial pair | **대체로 해소** | meta-last commit marker + 단계별 cleanup. consumer enforcement는 아직 문구뿐 |
| H3-08 versioned PII | **부분 해소** | lifecycle noncurrent 규칙과 training 삭제 script 반영. visual-input 즉시 삭제와 Object Lock 분기가 빠짐 |
| H3-09 sweeper starvation | **해소 방향** | 별도 `VisualDispatchFunction`, concurrency 1, 1분 schedule, age alarm |
| H3-10 unsafe IAM canary | **미해소** | worker에 `iam_probe`를 추가했지만 31-12는 여전히 receive/delete 절차를 지시 |
| H3-11 HMAC validation | **해소** | strict shared validator, inventory gate, retired keys, historical registry 반영 |
| M3-01 parity | **부분 해소** | adversarial/unknown fixture 강화. 전처리 mirror metadata는 여전히 없음 |
| M3-02 privacy runtime config | **해소** | 배포 상수 + JSON build 대조, runtime `.planning` 접근 금지 |
| M3-03 lifecycle path | **미해소** | 31-12가 여전히 `file://lifecycle_merged.json` 사용 |
| M3-04 URL test | **해소** | Firestore/SQS/log 전체 scheme+field 검사 |
| M3-05 historical joints | **해소** | append-only `HISTORICAL_PAIR_JOINTS` 도입 |
| M3-06 deterministic tie | **해소** | `abs(points)` 후 criterion key tie-break 반영 |
| M3-07 reconciliation wording | **해소** | 정확한 복구가 아닌 중복 과금 회피용 수동 판정으로 수정 |

---

## 3. BLOCKERS

### B4-01 · 이전 action의 늦은 ACK가 다음 action의 pending outbox를 sent로 덮을 수 있다

**재현 순서**

1. poll worker가 transaction으로 `polling → fetching`, `nextAction=fetch`, `dispatchState=pending`을 기록한다.
2. poll worker가 fetch SQS message를 성공적으로 보낸다.
3. reserved concurrency의 다른 worker가 fetch를 빠르게 받아 `fetching → judging`, `nextAction=judge`, `dispatchState=pending`을 기록한다.
4. 원 poll worker가 뒤늦게 `mark_visual_job_dispatched(jobId, expect_generation)`을 호출한다.
5. generation은 job 전체 재시도 세대이므로 여전히 같다. 함수는 현재 pending이 fetch용인지 judge용인지 구분하지 않고 `sent`로 바꾼다.
6. fetch worker가 judge send 전에 죽었다면 judge outbox는 이미 sent라 dispatcher가 복구하지 않는다.

같은 경쟁은 producer create send, dispatcher send, worker의 모든 best-effort send 뒤에 발생할 수 있다.

**근거**

- `31-02-PLAN.md:123`의 `mark_visual_job_dispatched` 조건은 `dispatchState=pending + expect_generation`뿐이다.
- `31-09-PLAN.md:92`의 `_advance`는 transition 뒤 send와 mark를 따로 한다.
- 메시지에는 `{jobId, action, generation}`만 있고 action instance 식별자가 없다.
- polling은 `polling → polling` self-loop이므로 state+generation만으로는 이전 poll message와 새 poll message도 구분하지 못한다.
- standard SQS는 동일 message를 두 번 전달할 수 있고 순서도 보장하지 않는다. AWS도 consumer를 idempotent하게 설계하라고 명시한다.

공식 근거: [Amazon SQS at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html), [Amazon SQS standard queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html)

**영향**

3차 blocker B3-01이 다른 형태로 재발한다. job은 `judging` 또는 `pose_checking`에서 영구 고아가 될 수 있다. 중복 message가 동시에 judge에 들어가면 Gemini 유료 호출도 중복될 수 있다.

**제가 해결한다면**

generation과 별개인 단조 증가 `outboxSeq` 또는 random `dispatchToken`을 각 transition에서 만든다.

```text
transition transaction
  state = next state
  nextAction = judge
  outboxSeq = previous + 1
  dispatchState = pending

message
  {jobId, generation, action, outboxSeq}

mark sent CAS
  generation == expected_generation
  nextAction == expected_action
  outboxSeq == expected_outbox_seq
  dispatchState == pending
```

- 이전 sender의 mark는 seq 불일치로 no-op한다.
- handler는 외부 호출 전에 `claim_visual_job_action(jobId, generation, action, outboxSeq, owner, lease)` transaction을 수행한다.
- 이미 같은 seq가 claimed이면 duplicate는 외부 호출 없이 no-op한다.
- poll/fetch/judge/pose는 lease 만료 후 안전하게 재실행 가능하되, create는 기존 `create_unconfirmed` 특례를 유지한다.
- transition은 `expect_outbox_seq`를 필수로 받고 성공 시 새 seq로 증가시킨다. 이 조치가 있어야 `polling → polling` self-loop의 오래된 message가 새 attempt를 실행하지 못한다.
- fault test에 “다음 state가 pending으로 바뀐 뒤 이전 sender가 mark”와 “동일 SQS message 2개 동시 처리”를 추가한다.

---

### B4-02 · sync image 성공은 taskId가 없어서 fetching 단계가 URL을 복구할 수 없다

**근거**

- image adapter는 sync 모델일 때 `create_task`가 `VendorPollResult(succeeded, output_url)`을 즉시 반환할 수 있다(`31-05-PLAN.md:78`).
- worker는 이 경우 URL을 기록하지 않고 `creating → fetching`으로 전이한다(`31-09-PLAN.md:93`).
- correctedPose fetch는 `job.taskId`를 다시 poll해 fresh URL을 얻는 것으로만 정의되어 있다(`31-09-PLAN.md:118`).
- sync result에는 taskId가 없으므로 fetch가 호출할 식별자가 없다.
- 31-01의 후보 중 sync 모델이 선택될 수 있으며, `RESULTS.json.sync=true`를 production 차단 조건으로 삼지 않는다.

**영향**

sync 후보가 선택되면 모든 correctedPose job이 fetching에서 `taskId` 없이 실패하거나 구현자가 임의로 URL persistence를 되살리게 된다.

**제가 해결한다면**

가장 안전한 v1 정책은 **production 모델을 async taskId 지원 모델로 제한**하는 것이다.

- 31-01/13 release gate에서 `RESULTS.sync is False`와 nonempty taskId를 요구한다.
- sync 후보만 성공하면 `blocked=true`로 flag OFF를 유지한다.

sync 모델을 반드시 지원해야 한다면 별도 계약이 필요하다.

- create invocation이 sync 결과 URL을 받자마자 같은 invocation에서 streaming download와 immutable staging S3 put까지 끝낸 후 `judging` outbox를 기록한다.
- create 성공 후 staging 전 crash는 `create_unconfirmed`로 수동 판정한다. URL을 Firestore/SQS에 저장하지 않는다.
- 이 경로는 “외부 side-effect 1개/invocation”의 명시적 예외이며 별도 crash test를 둔다.

둘을 섞어 구현자 판단에 맡기면 안 된다.

---

### B4-03 · moderation retry가 이전 taskId를 유지해 새 create crash를 과거 blocked task로 오판한다

**재현 순서**

1. taskId `T1`을 polling하다 moderation blocked가 발생한다.
2. 계획은 `polling → retry_ready`, `retryCount+1`, `nextAction=create`만 기록한다.
3. create는 `retry_ready → creating`으로 전이하지만 `taskId=None` 초기화를 명시하지 않는다.
4. vendor에 새 task `T2`를 create한 직후 taskId CAS 전에 crash한다.
5. redelivery는 state creating에서 과거 `taskId=T1`을 발견하고 “taskId 존재 = polling 재개”로 분기한다.
6. 새 T2는 고아가 되고 worker는 이미 blocked된 T1을 다시 poll한다.

**영향**

새 유료 task가 고아가 되고 moderation retry가 잘못된 이전 task를 재개한다. attempt가 reset되지 않으면 새 generation이 조기에 timeout될 수도 있다.

**제가 해결한다면**

- `polling → retry_ready` transaction에서 `taskId=None`, `attempt=0`, 이전 output/failure/lease metadata를 명시적으로 clear한다.
- `retry_ready → creating` validator는 `taskId is None`을 강제한다.
- 가능하면 새 vendor 재생성을 job `generation+1`로 승격해 과거 message를 완전히 격리한다. quota 정책은 correctedPose 자동 retry이므로 별도 카운터로 관리한다.
- 테스트는 T1 blocked → T2 create 2xx → CAS 전 crash를 주입하고, T1 재-poll 0·T2 중복 create 0·`create_unconfirmed` 종결을 검증한다.

---

### B4-04 · calibration manifest가 before/after pair를 표현하지 않아 judge harness가 실행 불가능하다

**근거**

- `judge_corrected_pose` 시그니처는 before와 after 이미지 둘 다 필수다.
- 31-13 harness도 `judge_corrected_pose(before, after, context)`를 호출한다고 명시한다.
- 그러나 31-01 `fixtures_manifest.json` 항목에는 단일 `path`와 단일 `sha256`만 있다(`31-01-PLAN.md:124-127`).
- 어떤 파일이 before이고 어떤 파일이 after인지, 두 파일이 같은 생성 pair인지, after keypoint가 어느 이미지에 속하는지 표현할 수 없다.
- 31-13의 hash 재검증도 단일 fixture 파일만 대상으로 한다.

**영향**

harness를 계획대로 구현할 수 없다. 구현자가 같은 이미지를 before/after로 넣거나 디렉터리 naming을 추측하면 judge confidence와 FA/FR 표가 무의미해진다.

**제가 해결한다면**

manifest item을 pair 계약으로 바꾼다.

```json
{
  "id": "...",
  "beforePath": "...",
  "beforeSha256": "...",
  "afterPath": "...",
  "afterSha256": "...",
  "label": "PASS|FAIL",
  "jointKey": "...",
  "targetDeg": 175.0,
  "afterKeypointSource": {"path": "...", "modelVersion": "..."},
  "failureAxes": ["pole", "extra_limbs"],
  "category": ["inverted", "left"]
}
```

- before/after 각각 hash를 검증한다.
- 생성 call ID/model/prompt version으로 pair provenance를 묶는다.
- pose error는 after keypoint로만 계산한다.
- dry-run test가 두 파일 존재, 두 hash, pair provenance, keypoint 대상 일치를 검증한다.

---

### B4-05 · calibration이 산출하는 training confidence가 worker/template에서 소비되지 않는다

**근거**

- CALIBRATION chosen은 `display_confidence`와 `training_confidence`를 모두 산출한다(`31-13-PLAN.md:72`).
- `judge_training_pass`는 별도의 `min_confidence` 인자를 요구한다(`31-05-PLAN.md:116`).
- 그러나 31-10 template env에는 `DISPLAY_JUDGE_CONFIDENCE`만 있고 `TRAINING_JUDGE_CONFIDENCE`가 없다.
- 31-09 judge action도 display env만 언급한 채 `judgeTrainingPass`를 기록한다. training gate는 이후 이 불명확한 bool을 신뢰한다.
- 31-13의 key link와 SUMMARY mapping에도 training confidence env가 없다.

**영향**

training gate가 display confidence를 재사용하거나 하드코딩될 가능성이 높다. “training은 display보다 엄격”이라는 privacy/quality 계약과 calibration 결과가 실제 적재 경로에서 분리된다.

**제가 해결한다면**

- env `TRAINING_JUDGE_CONFIDENCE`를 31-09/10/12 전체에 추가한다.
- judge action에서 같은 raw verdict에 대해:
  - `judge_display_pass(... DISPLAY_JUDGE_CONFIDENCE)`
  - `judge_training_pass(... TRAINING_JUDGE_CONFIDENCE)`
  를 각각 호출한다.
- template parsing test가 CALIBRATION chosen 4개 값과 env 4개 값의 exact mapping을 검사한다.
- `TRAINING_JUDGE_CONFIDENCE > DISPLAY_JUDGE_CONFIDENCE`와 `TRAINING_POSE_TOL_DEG < DISPLAY_POSE_TOL_DEG`를 build gate에서 강제한다.

---

## 4. HIGH

### H4-01 · pair 저장과 임시 입력 cleanup이 terminal finalize 뒤에 있어 crash 복구가 안 된다

**근거**

- pose pass 경로는 canonical copy → atomic finalize done → pair store → src/staging cleanup 순서다(`31-09-PLAN.md:120`).
- finalize 직후 crash하면 redelivery는 terminal job을 stale no-op한다.
- opt-in quality-pass pair는 영구 누락되고, src/staging은 lifecycle까지 남는다.
- `store_training_pair`가 False를 반환해도 retry journal이 없다.

**제가 해결한다면**

- `pose_checking → postprocessing` state를 추가하고 canonical key, pair eligibility를 기록한다.
- `postprocess` action이 idempotent commit-marker pair store와 exact-version temp cleanup을 수행한 뒤 atomic finalize한다.
- pair store가 제품 상태를 막지 않는 정책이면 제한된 retry 후 `pairStoreStatus=failed` 메타를 기록하고 done으로 finalize하되, 관측 가능한 metric/DLQ를 남긴다.
- 실패 종결도 cleanup action을 거치거나 terminal transaction에 별도 durable cleanup outbox를 남긴다.

---

### H4-02 · 31-12 배포 plan이 이전 sweeper 구조와 unsafe receive/delete canary를 그대로 유지한다

**근거**

- 31-09는 `iam_probe` action을 추가하고 31-10은 별도 `VisualDispatchFunction`을 만든다.
- 그러나 31-12 must-have와 Task 3은 여전히 “canary send + 즉시 receive/delete”를 지시한다.
- `<what-built>`도 `VisualWorkerFunction(+SweepSchedule)`이라고 쓰며 dispatcher/outbox alarm을 언급하지 않는다.
- SQS receive는 방금 보낸 canary를 반환한다는 보장이 없어 실제 message를 삭제할 수 있다.

**제가 해결한다면**

- 31-12를 현재 architecture에 맞춰 다시 쓴다: VisualWorker에는 schedule 없음, VisualDispatchFunction+OutboxAgeAlarm 포함.
- IAM simulation fallback은 `{jobId:"iam-probe", action:"iam_probe", generation:0, outboxSeq:0}` 같은 명시 schema로 **send만** 하고 worker log에서 해당 probe ID 소비를 확인한다.
- client가 production queue를 receive/delete하지 않는다.
- build acceptance에 VisualDispatchFunction과 dispatcher LogGroup을 추가한다.

---

### H4-03 · versioned bucket에서 visual-input의 “즉시 삭제”는 실제 데이터 version을 남긴다

**근거**

- worker cleanup은 일반 `delete_object` 시도만 명시한다.
- versioned bucket의 simple delete는 delete marker를 만들고 원본 version을 noncurrent로 남긴다.
- 31-12 E2E의 `aws s3 ls ... 0건`은 current view만 보므로 noncurrent PII 잔존을 놓친다.
- lifecycle이 1일 뒤 정리하더라도 계획이 주장하는 처리 후 즉시 삭제와는 다르다.

**제가 해결한다면**

- source put과 staging upload의 VersionId를 job payload/meta에 저장하고 cleanup에서 versionId 지정 삭제한다.
- `upload_file` 후 `head_object`로 정확한 VersionId를 확보하거나 response를 받을 수 있는 upload API를 사용한다.
- 대안은 visual-input 전용 non-versioned transient bucket을 분리하는 것이다.
- E2E는 `list-object-versions`로 해당 prefix의 Versions/DeleteMarkers가 모두 0인지 검사한다.

---

### H4-04 · Object Lock을 조회만 하고 enabled/default-retention일 때의 차단 정책이 없다

**근거**

- 31-10 dry-run은 `get-object-lock-configuration` 결과를 기록하지만 그 결과에 따른 fail-closed 분기가 없다.
- Object Lock retention 또는 legal hold가 적용된 version은 lifecycle로 삭제되지 않으며 versionId delete도 거부될 수 있다.
- 개인정보 보존일수와 삭제 요청 이행 약속이 깨질 수 있다.

AWS 공식 근거: [S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html), [Object Lock과 lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-managing.html)

**제가 해결한다면**

- Object Lock enabled + default retention 존재 시 phase 31 민감 prefix를 이 bucket에 쓰지 않고 별도 bucket을 요구하며 blocked 처리한다.
- enabled지만 default retention이 없다면 실제 test object version의 retention/legal-hold 상태와 delete 가능성을 dry-run canary bucket/prefix에서 검증한다.
- deletion script가 403을 만나면 성공처럼 진행하지 않고 retention/hold 정보를 출력하고 비정상 종료한다.

---

### H4-05 · JPEG vendor 결과를 `.png` key와 `image/png` metadata로 저장할 수 있다

**근거**

- correctedPose download는 `image/png`와 `image/jpeg`를 모두 허용한다.
- staging/canonical key는 항상 `.png`이고 최종 copy metadata도 `image/png`다.
- 계획에는 JPEG bytes를 PNG로 decode/re-encode한다는 단계가 없다.

**영향**

S3 metadata와 실제 bytes가 달라 CDN/클라이언트 decoder에서 표시 실패가 날 수 있다. canonical key exact guard는 통과하므로 늦게 발견된다.

**제가 해결한다면**

- download 후 PIL로 format/dimension을 검증하고 EXIF를 제거해 실제 PNG로 재인코딩한다.
- staging부터 canonical까지 PNG bytes만 허용하고 sha256은 정규화된 PNG 기준으로 기록한다.
- JPEG fixture를 넣어 PNG magic bytes와 S3 ContentType 일치를 검증한다.

---

### H4-06 · judge 정규화 경로에 decompression-bomb/pixel cap이 명시되지 않았다

**근거**

- pose normalizer와 `/pose-image`에는 `MAX_IMAGE_PIXELS`, format, dimension cap이 있다.
- `prepare_judge_payload`는 PIL open 후 2048px resize만 명시하고, open/decode 전 bomb 방어가 없다.
- 압축 크기 20MB 이하인 대해상도 JPEG/PNG도 decode 과정에서 worker 메모리를 소진할 수 있다.

**제가 해결한다면**

- judge/pose가 공용 `safe_decode_image`를 사용하게 한다.
- format allowlist, `MAX_IMAGE_PIXELS`, width/height/pixel cap을 decode 전에/직후 검사한다.
- bomb fixture에서 Gemini 호출 0, typed `invalid_output` 또는 `judge_input_too_large` 종결을 검증한다.

---

### H4-07 · atomic finalize가 caller의 uid/analysisId/kind와 terminal/display 조합을 신뢰한다

**근거**

- `finalize_visual_job`은 jobId 외에 uid, analysisId, kind, terminalState, displayStatus를 별도 인자로 받는다.
- 계획은 인자가 job 문서의 uid/analysisId/kind와 exact 일치하는지 검증하지 않는다.
- `terminal_state='done', display_status='failed'` 같은 모순 조합도 금지하지 않는다.

**제가 해결한다면**

- uid/analysisId/kind는 caller 인자에서 제거하고 transaction이 job 문서에서 파생한다.
- 제거가 어렵다면 세 값 exact equality를 validator로 강제한다.
- done↔display done, failed↔display failed를 고정하고, done은 canonical key 필수, failed는 새 canonical key 금지 규칙을 둔다.
- cross-analysis tampering과 모순 조합 테스트를 추가한다.

---

### H4-08 · `limit*3` pending 조회는 due job 복구와 age metric의 완전성을 보장하지 않는다

**근거**

- `dispatchState==pending` query를 60건에서 자른 뒤 메모리에서 due time을 필터한다.
- Firestore 반환 순서가 due time 순이라는 보장이 없다.
- 미래 due 문서나 낮은 ID 문서가 앞부분을 차지하면 뒤의 오래된 due job을 보지 못한다.
- metric도 조회된 slice의 max만 계산하므로 숨은 오래된 backlog를 0/낮게 보고할 수 있다.

**제가 해결한다면**

- durability 경로에는 필요한 composite index를 명시적으로 배포하는 편이 낫다: `dispatchState ASC, nextDispatchAtMs ASC`.
- index 배포를 원치 않으면 due-minute bucket/shard field를 transaction에 기록하고 현재·이전 bucket을 equality query한다.
- pilot scan 방식을 유지한다면 pagination으로 pending 전체를 bounded maximum까지 스캔하고 초과 자체를 alarm/error로 만든다. 첫 60건 고정은 제거한다.

---

### H4-09 · 31-12 blocked/build gate가 CALIBRATION과 dispatcher 산출물을 직접 검증하지 않는다

**근거**

- Task 1은 `RESULTS.json.blocked`만 검사한다.
- CALIBRATION missing/blocked/chosen 불완전인데 RESULTS 동기화가 실패하거나 stale이면 배포가 진행될 수 있다.
- build 산출물 acceptance도 VisualRequest/Worker만 보고 VisualDispatchFunction을 확인하지 않는다.

**제가 해결한다면**

- RESULTS와 CALIBRATION을 각각 읽어 둘 다 blocked false, chosen 4값 존재, strict ordering 충족을 검사한다.
- template env 4값이 chosen과 일치하는지 검사한다.
- `.aws-sam/build/VisualDispatchFunction`과 세 함수 LogGroup/alarms까지 확인한다.

---

### H4-10 · calibration 최소 표본이 PASS/FAIL 각 1개라 FA 우선 threshold 근거가 너무 약하다

**근거**

- manifest는 12개 이상이지만 PASS/FAIL은 각 1개만 요구한다.
- 측정 불가 25%를 허용하므로 유효 9개 중 FAIL 1개만 남을 수 있다.
- FA 최소화 우선 정책은 negative sample 수와 failure axis 다양성이 핵심이다.

**제가 해결한다면**

- 최소 PASS 4, FAIL 8처럼 negative를 더 많이 요구한다.
- FAIL에는 pole, identity/clothing/background, extra limbs/person, correction invisible, pose tolerance failure를 각각 포함한다.
- category별 confusion table과 Wilson interval 또는 최소한 표본 수를 함께 기록한다.
- 조건 미달은 chosen을 만들지 않고 blocked한다.

---

### H4-11 · pair consumer의 commit-marker 규칙이 실행 코드가 아니라 docstring에만 있다

**근거**

- store는 meta-last로 개선됐지만 “consumer는 meta.json 있는 pair만 연다”는 문서 계약뿐이다.
- 31-07 files에는 committed pair enumerator나 실제 phase 22 consumer 변경이 없다.
- future consumer가 before/after prefix를 직접 list하면 partial pair를 읽을 수 있다.

**제가 해결한다면**

- `list_committed_pairs`/`load_committed_pair` helper를 pair_store에 제공하고 meta 존재+schema 검증을 단일 경로로 만든다.
- phase 22 소비 plan에서 이 helper만 사용하도록 acceptance를 연결한다.
- meta 없는 before/after fixture가 enumeration에서 제외되는 테스트를 추가한다.

---

## 5. MEDIUM

### M4-01 · lifecycle apply 경로가 여전히 산출 위치와 다르다

artifact는 `.planning/phases/31-api-visual-correction/infra/lifecycle_merged.json`인데 명령은 `file://lifecycle_merged.json`이다. repo-root 기준 정확한 경로로 고정해야 한다.

### M4-02 · worker가 `prepare_judge_payload`를 선호출한 뒤 judge가 다시 호출하는 것으로 읽힌다

31-05는 `judge_corrected_pose` 내부에서 prepare를 호출한다. 31-09는 prepare 후 judge 호출로 서술한다. 호출은 judge 하나로 통일하고 worker는 `JudgeInputTooLargeError`만 catch해야 이중 decode/encode를 피할 수 있다.

### M4-03 · stricter training grid 후보가 없을 때의 동작이 정의되지 않았다

display chosen이 이미 pose 8°/confidence 0.85면 더 엄격한 grid 조합이 없다. 이 경우 arbitrary fallback이 아니라 calibration blocked가 되어야 한다.

### M4-04 · upload-first의 existing object head가 full hash 일치를 어떻게 증명하는지 없다

S3 key는 full hash의 16 hex(64 bit)만 쓴다. existing head를 재사용하려면 object metadata에 full sha256을 넣고 신규 sourceHash와 exact 비교해야 한다. 불일치면 collision/tampering으로 block해야 한다.

### M4-05 · calibration `pose_model_version`이 실제 model version이 아니라 source 표기일 수 있다

manual keypoint와 여러 spike kpts가 섞이면 단일 `pose_model_version` 문자열은 부정확하다. fixture별 estimator/model/version과 전체 calibration의 version set을 기록해야 한다.

### M4-06 · topology parity는 여전히 추정값이며 provenance에 전처리 mirror metadata가 없다

adversarial/unknown 테스트는 개선이지만 측면·가림에서 틀린 known이 가능하다. 실제 preprocessing이 mirror를 수행했다면 그 metadata를 우선 사용하고 topology는 fallback으로 두는 것이 안전하다.

---

## 6. 반드시 추가할 fault/concurrency tests

| 시나리오 | 현재 계획의 문제 | 필요한 기대값 |
|---|---|---|
| poll sender send 후, fetch가 judge pending 기록, poll sender가 늦게 mark | generation만 비교해 judge를 sent 처리 | 이전 mark False, judge pending 유지 |
| 같은 `{action,outboxSeq}` message 2개 동시 처리 | 외부 호출 전 claim 없음 | claim 1개만 성공, Gemini/vendor 외부 호출 1회 |
| old poll seq 재전달 after polling self-loop | state/generation 동일 | old seq no-op, attempt/nextAction 불변 |
| sync image create succeeded/taskId 없음 | fetch 재-poll 불가 | async-only block 또는 same-invocation staging 완료 |
| moderation T1 blocked → T2 create 2xx 후 crash | stale T1 taskId 잔존 | T1 poll 0, T2 duplicate create 0, create_unconfirmed |
| calibration manifest dry-run | before/after 구분 없음 | pair 파일·두 hash·after kpts provenance 검증 |
| chosen 4값 template mapping | training confidence 누락 | env 4개 exact equality + strict ordering |
| finalize 직후 postprocess 전 crash | pair/cleanup 유실 | durable postprocess 재개 후 pair/cleanup/finalize 정합 |
| versioned visual-input cleanup | `aws s3 ls` 거짓 0 | Versions/DeleteMarkers 모두 0 |
| Object Lock default retention | delete/lifecycle 불가 | phase blocked 또는 별도 bucket 요구 |
| JPEG vendor output | `.png` key MIME mismatch | PNG magic bytes + ContentType image/png |
| pending 100건 중 뒤쪽 overdue | first 60 slice starvation | overdue 모두 bounded 시간 내 dispatch, age metric 정확 |

---

## 7. 권장 재계획 순서

1. **31-02 outbox identity 추가**
   - `outboxSeq/dispatchToken`, expected action+seq CAS, action claim lease.
   - self-loop poll도 seq가 바뀌도록 강제.

2. **31-05/09 vendor mode 계약 확정**
   - v1 async-only gate 또는 sync same-invocation staging 중 하나를 명시.
   - moderation retry에서 이전 task metadata atomic clear.

3. **31-01/13 calibration pair schema 수정**
   - before/after path+hash, after keypoint provenance.
   - `TRAINING_JUDGE_CONFIDENCE`를 포함해 chosen 4값 전부 runtime 소비.

4. **31-09 postprocessing 내구성 추가**
   - pair store와 temp cleanup을 terminal 이전 durable action으로 이동.

5. **31-10/12 infra·privacy 마감**
   - due index/bucket query, exact-version visual-input cleanup, Object Lock fail gate.
   - dispatcher/iam_probe 기준으로 31-12 stale 문구 전면 교체.

6. **VALIDATION matrix 확장**
   - ACK clobber, duplicate claim, sync path, moderation stale taskId, pair manifest/env mapping을 blocker gate로 추가.

---

## 8. 실행 승인 조건

- [ ] 모든 outbox에 generation과 별도의 action instance ID가 있다.
- [ ] sent ACK가 expected action+instance를 CAS하며 다음 outbox를 덮을 수 없다.
- [ ] worker가 외부 side effect 전에 action instance를 lease/claim해 duplicate 실행을 막는다.
- [ ] sync image 모델 지원 여부가 명시적으로 결정되고 taskId 없는 fetching이 존재하지 않는다.
- [ ] moderation retry가 이전 taskId/attempt/lease metadata를 atomic clear한다.
- [ ] calibration manifest가 before/after pair와 각각의 hash를 표현한다.
- [ ] display/training confidence와 pose tolerance 4값이 template/worker에서 전부 소비된다.
- [ ] pair store와 temp cleanup이 crash 후 재개 가능한 durable action이다.
- [ ] versioned visual-input cleanup과 E2E가 실제 version 잔존 0을 검증한다.
- [ ] Object Lock이 개인정보 retention/delete 약속과 충돌하면 배포를 차단한다.
- [ ] 31-12가 VisualDispatchFunction/iam_probe/current lifecycle artifact 경로를 기준으로 갱신된다.

---

## 9. 최종 의견

4차 개정은 지금까지 중 가장 구조가 좋다. 3차에서 요구한 atomic finalize, upload-first, independent dispatcher, reproducible calibration, payload/privacy 경계 대부분이 설계에 들어왔다. 기존 계획을 다시 뒤엎을 필요는 없다.

현재 blocker는 **범용 outbox를 완성하는 마지막 동시성 계약**과 몇 개의 명확한 데이터 연결 누락이다. 특히 `outboxSeq + action claim`을 넣지 않으면 standard SQS의 중복·역순 전달과 빠른 다음 worker 실행에서 continuation 유실이 다시 발생한다. 이것이 4차 리뷰의 최우선 수정점이다.

판정은 **BLOCK**이다. 31-02/05/09/10/13과 31-12의 해당 절만 targeted replan하면 된다. 수정 후 5차 리뷰는 outbox instance ownership, sync/async 경로, moderation reset, calibration pair/env 소비 네 축만 좁게 검증하면 충분하다.
