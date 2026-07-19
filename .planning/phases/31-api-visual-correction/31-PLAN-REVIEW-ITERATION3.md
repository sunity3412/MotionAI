# Phase 31 계획 3차 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-19  
**리뷰 범위:** 3차 개정된 `31-01-PLAN.md` ~ `31-12-PLAN.md`, `31-CONTEXT.md`, `31-RESEARCH.md`, `31-PATTERNS.md`, `31-VALIDATION.md`, 1·2차 리뷰와 계획이 참조하는 현재 코드  
**리뷰 방법:** 2차 지적별 해소 추적, action/state 전이별 crash window 분석, Firestore/SQS/S3 원자성 대조, 개인정보 보존·삭제 경로 검증, API payload 한계 및 테스트 실행 가능성 검증, 5-wave DAG 재검사  
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 리뷰 없이 직접 검토했다. AWS·Google 공식 문서는 변동 가능한 서비스 동작을 확인하는 1차 자료로만 사용했다.  
**최종 판정:** **BLOCK / REPLAN REQUIRED**

---

## 1. 결론

3차 개정은 2차 리뷰의 중요한 의미 오류를 상당수 바로잡았다.

- `CorrectedPoseTarget`이 joint, reference 기반 `targetDeg`, user/ref frame, provenance를 하나의 계약으로 묶는다.
- signed-negative 감점은 `abs(points)`로 정렬하고, 감점 record 수치는 목표각 산술에 쓰지 않는다.
- vendor create를 `creating` lease와 `polling(taskId 필수)`로 분리했다.
- 이미지 adapter 내부 폴링을 제거하고 image/video 모두 action 기반 create/poll로 통일했다.
- initial dispatch outbox, SQS visibility 1,800초, maxReceiveCount 5, DLQ, Pipeline/RunPod IAM 검증을 계획했다.
- 31-09와 31-10을 wave 3/4로 분리하고, 라이브 lifecycle/SSM mutation을 human checkpoint로 이동했다.
- versioned HMAC과 retired key 삭제 경로, machine-readable privacy 결정, calibration gate를 추가했다.

그러나 지금 계획은 **초기 enqueue만 outbox로 보호하고, worker 내부 continuation은 여전히 `Firestore CAS → SQS send`의 비원자적 이중 쓰기**다. CAS 직후 죽으면 재전달된 과거 action은 새 state에서 no-op하고, 새 action은 발행되지 않아 영구 고아가 된다. 또한 terminal job과 analysis 표시 결과를 두 번의 Firestore 쓰기로 끝내므로 둘 사이 crash가 영구 불일치를 만든다.

현재 실행 차단 사유는 3개다.

1. 모든 중간 state 전이 뒤 continuation 발행 유실 창이 남아 있으며, 현재 crash test의 “CAS no-op 멱등” 기대값은 복구를 증명하지 못한다.
2. terminal job과 analysis result가 원자적으로 종결되지 않아 job은 `done/failed`인데 앱은 `pending`인 상태가 영구화될 수 있다.
3. correctedPose 예약/outbox가 입력 S3 object 준비 전에 활성화되고, created 경로는 SQS 발행 뒤 `pending`을 기록해 worker 결과를 되감을 수 있다.

따라서 **31-02/09/10의 dispatch·finalize 계약을 한 번 더 재설계한 뒤에만 실행해야 한다.**

### 발견 수

| 심각도 | 수 | 의미 |
|---|---:|---|
| BLOCKER | 3 | Wave 1 실행 전 계획 수정 필수 |
| HIGH | 11 | blocker 수정과 같은 재계획에서 해결 필요 |
| MEDIUM | 7 | 배포 전 계약·검증 보강 필요 |

---

## 2. 2차 리뷰 지적 해소 추적

| 2차 ID | 3차 상태 | 판단 |
|---|---|---|
| B2-01 target provenance | **해소** | `CorrectedPoseTarget`, reference 3점, 명시 매핑, source/ref frame, `abs(points)`가 단일 계약으로 고정됨 |
| B2-02 vendor create crash | **부분 해소** | `creating` lease와 `taskId` validator는 유효. 그러나 이후 모든 continuation CAS→send crash가 새 blocker로 남음 |
| B2-03 replay-safe enqueue | **부분 해소** | immutable hash key와 reserve 반환 분기는 개선. input-ready 전 outbox 활성화와 send→pending 순서가 남음 |
| H2-01 SQS visibility/redrive | **해소** | 1,800초, maxReceiveCount 5, IaC assertion과 DLQ alarm 반영 |
| H2-02 outbox/IAM | **부분 해소** | initial outbox와 IAM 검증은 추가. per-transition outbox가 없고 sweeper가 worker와 concurrency를 공유 |
| H2-03 mirror 후보 | **대체로 해소** | 가까운 후보 휴리스틱 제거, topology parity와 unknown 생략 도입. 실제 parity 신뢰성 fixture는 더 필요 |
| H2-04 redirect 차단 | **구현안 해소 / 테스트 미해소** | `_NoRedirectHandler`는 맞지만 계획된 HTTP local test는 최초 scheme 검사에서 막힘 |
| H2-05 대용량 메모리 | **부분 해소** | file streaming과 multipart upload 반영. RSS 측정법, Gemini/pose payload 상한은 불일치 |
| H2-06 key rotation/보존 | **부분 해소** | versioned key·retired 삭제·retentionDays 반영. versioned S3의 noncurrent PII 삭제가 빠짐 |
| H2-07 calibration | **부분 해소** | fixture/grid/FA-FR 표가 추가됐으나 judge/pose 구현보다 먼저 실행되어 재현 가능한 harness가 없음 |
| H2-08 DAG | **해소** | 31-09 wave 3, 31-10 wave 4, 31-12 wave 5로 수정 |
| H2-09 live mutation | **해소** | dry-run과 human-action checkpoint 분리 |
| H2-10 blur runtime | **대체로 해소** | Pod 시점 training artifact 생성으로 이동. 결정 파일을 runtime에 어떻게 포함할지는 모호 |
| M2-01 exact playback guard | **해소** | canonical exact key + done status guard 반영 |
| M2-02 malformed SQS | **해소** | partial batch failure로 DLQ 증거 보존 |
| M2-03 stale research | **해소** | historical/do-not-implement 표지가 선두에 추가됨 |
| M2-04 fault matrix | **부분 해소** | matrix는 추가됐으나 가장 중요한 CAS→send 및 terminal dual-write crash 기대값이 잘못됨 |
| M2-05 privacy parameterization | **대체로 해소** | `privacy_decision.json`과 대조 테스트 도입. 배포 artifact 반영 방식은 명시 필요 |

---

## 3. BLOCKERS

### B3-01 · state CAS와 다음 action 발행 사이의 crash가 모든 중간 단계를 영구 고아로 만든다

**근거**

- `31-09-PLAN.md:50-56, 80-84`의 공통 패턴은 `현재 state → 다음 state CAS → sqs.send_message(next action)`이다.
- send 실패를 예외로 전파해도 원 메시지에는 **이전 action**이 들어 있다. 재전달된 이전 action이 새 state에서 CAS no-op하면, 유실된 다음 action을 다시 만들지 않는다.
- 구체적으로 다음 네 창이 모두 존재한다.
  - `create`: `creating → polling(taskId)` 성공 뒤 `poll` send 전 crash. 재전달 `create`는 state `polling`에서 continuation을 재발행한다는 규칙이 없다.
  - `poll`: `polling → fetching` 성공 뒤 `fetch` send 전 crash. 재전달 `poll`은 `fetching`에서 no-op한다.
  - `fetch`: `fetching → judging` 성공 뒤 `judge` send 전 crash.
  - `judge`: `judging → pose_checking` 성공 뒤 `pose_check` send 전 crash.
- `31-VALIDATION.md:106`과 `31-09-PLAN.md:84`는 이를 “재전달 → CAS no-op 멱등”으로 PASS 처리하지만, **중복 실행 방지와 다음 작업 복구는 다른 속성**이다. no-op은 고아를 고치지 않는다.
- moderation retry도 `polling` 상태에서 `retryCount`만 CAS한 뒤 `create` 메시지를 발행한다고 적었다. 새 `create`는 `reserved|dispatch_failed|creating`만 처리하므로 `polling`에서 no-op한다.
- sweeper는 `reserved|dispatch_failed`만 재발행한다(`31-09-PLAN.md:125`). `polling|fetching|judging|pose_checking` 고아는 운영 스크립트에 보이기만 하고 자동 복구되지 않는다.

**영향**

vendor task와 결과가 정상인데도 job이 `polling/fetching/judging/pose_checking`에 영구 정지한다. 사용자에게는 `pending`이 숨김으로 바뀌고, 입력 PII는 lifecycle 만료까지 남으며, 유료 결과가 폐기될 수 있다.

**제가 해결한다면**

initial dispatch와 동일한 durable outbox를 **모든 state 전이**에 적용한다.

```text
Firestore transaction
  validate current state/generation
  write next state + state metadata
  write nextAction + nextActionGeneration
  write dispatchState = pending
  write nextDispatchAtMs

best-effort dispatcher
  send {jobId, action: nextAction, generation}
  CAS dispatchState pending -> sent
```

- worker가 직접 best-effort send를 해 latency를 줄여도 되지만, 실패/크래시 복구는 outbox sweeper가 담당한다.
- sweeper는 `reserved`만 찾지 말고 `dispatchState=pending`인 **모든 nonterminal state**를 발행한다.
- action 메시지에 `generation`과 가능하면 `transitionVersion`을 넣어 이전 generation 메시지가 새 재시도 job을 건드리지 못하게 한다.
- moderation retry는 transaction에서 `polling → reserved` 또는 명시적인 `retry_ready`로 전이하면서 `nextAction=create, dispatchState=pending`을 함께 기록한다.
- fault injection을 `각 CAS 직후·send 직전` 4개 지점에 추가하고, 기대값을 “재전달 no-op”이 아니라 “sweeper가 정확한 다음 action 1회 이상 발행, 외부 create 중복 0, 최종 terminal 도달”로 바꾼다.

대안으로 각 과거 action이 현재 state를 보고 누락된 continuation을 재발행하게 할 수도 있지만, state/action 조합이 늘수록 빠뜨리기 쉽다. 제가 구현한다면 범용 `nextAction` outbox 하나로 통일한다.

---

### B3-02 · terminal job과 analysis result의 이중 쓰기가 비원자적이라 사용자 상태가 영구 분리된다

**근거**

- `31-09-PLAN.md:82`의 `_finalize`는 `transition_visual_job(...)` 뒤 `update_analysis_visual(...)`을 호출한다.
- correctedPose done/failed와 rotation done 모두 같은 패턴이다(`31-09-PLAN.md:106,125`).
- job terminal CAS가 성공한 직후 analysis update가 실패하거나 Lambda가 죽으면 원 action이 재전달된다.
- 재전달 시 job은 이미 `done|failed`이므로 action은 stale no-op한다. 따라서 analysis의 `pending`은 고쳐지지 않는다.
- 현재 fault matrix는 “terminal write 직전 crash”만 다룬다(`31-VALIDATION.md:108`). 위험한 지점은 **job terminal write 직후·analysis write 전**인데 테스트가 없다.
- 반대 순서로 analysis를 먼저 쓰면 worker crash 시 UI가 done인데 job은 nonterminal이 되어 역시 안전하지 않다.

**영향**

서버 job과 사용자 문서가 서로 다른 진실을 갖는다. canonical artifact가 존재해도 앱에는 나타나지 않거나, 실패 job이 계속 pending으로 남는다. terminal state 때문에 자동 재처리도 막힌다.

**제가 해결한다면**

`finalize_visual_job()`을 만들고 **job 문서와 analysis 문서를 하나의 Firestore transaction에서 함께 갱신**한다.

- transaction read: job current state/generation, analysis owner/existence.
- transaction write: job `done|failed` + meta + analysis `result.correctedPose*` 또는 `rotation*`.
- canonical S3 artifact는 transaction 전에 immutable key로 준비하되, transaction 실패 시 재실행 가능한 put/copy로 유지한다.
- analysis 문서가 사라졌으면 job을 무조건 done으로 만들지 말고 명시적 `orphaned_analysis` 실패/운영 경로를 둔다.
- 보조 방어로 terminal reconciler가 `job.state`와 analysis result를 대조해 repair할 수 있게 한다.
- 테스트를 다음 두 지점에 추가한다.
  1. canonical S3 put/copy 성공 후 Firestore transaction 전 crash → 재전달 후 원자 종결.
  2. transaction commit 응답 유실 → 재전달 no-op이더라도 두 문서가 이미 일치.

---

### B3-03 · correctedPose outbox가 input-ready 전에 활성화되고 send 뒤 pending 기록이 결과를 되감을 수 있다

**근거**

- `reserve_visual_job`은 job 생성과 동시에 `state=reserved, dispatchState=pending`을 기록한다(`31-02-PLAN.md:111`).
- pipeline created 경로는 그 뒤에 `S3 put(srcKey) → SQS send → mark dispatched → update_analysis_visual('pending')` 순으로 실행한다(`31-10-PLAN.md:122`).
- reserve 직후 S3 put 전 crash/예외가 나면 sweeper는 input이 없는 reserved job을 정상 create로 발행한다. worker는 뒤늦게 `srcKey` 부재로 `invalid_output`을 종결한다.
- `try 재raise 0`이므로 S3 put 실패가 pipeline 분석 재시도로 복구된다는 보장도 없다.
- sweeper가 15분 주기여도 reserve와 S3 put 사이 race가 사라지는 것은 아니다.
- 정상 created 경로도 SQS를 먼저 보낸 뒤 analysis를 pending으로 만든다. sync image 경로 또는 빠른 worker가 done을 기록한 뒤 producer의 늦은 `pending` write가 도착하면 완료 상태가 다시 pending으로 내려간다.
- `31-10` 테스트는 “S3 put 후 process crash”는 다루지만 “reserve 후 S3 put 전 crash/S3 실패”와 “worker done 후 producer pending”은 다루지 않는다.

**영향**

일시적 S3 실패가 복구 불가능한 기능 실패로 바뀌고, 없는 입력으로 vendor 작업이 시작될 수 있다. 빠른 성공 결과가 producer의 늦은 pending write로 사용자 화면에서 사라질 수도 있다.

**제가 해결한다면**

immutable content hash key가 이미 도입됐으므로 다음 둘 중 하나로 고친다.

**권장안 A — upload first**

1. hash 기반 immutable `srcKey`를 put/head 검증한다.
2. 그 다음 Firestore transaction에서 job reserve + analysis pending + initial `nextAction=create, dispatchState=pending`을 함께 쓴다.
3. duplicate done에서 같은 hash object를 한 번 확인/put하는 비용은 허용하고 1일 lifecycle로 정리한다. 완료 상태를 되감지 않는 것이 더 중요하다.

**대안 B — explicit input state**

1. `awaiting_input`으로 예약하되 dispatch pending을 만들지 않는다.
2. S3 put 성공 뒤 transaction으로 `awaiting_input → reserved`, analysis pending, `nextAction=create/pending`을 한 번에 기록한다.
3. `awaiting_input` 만료는 vendor 발행 없이 typed 실패/정리한다.

어느 안이든 analysis pending은 **dispatch 가능 상태를 여는 같은 transaction**에 들어가야 한다. fault test에는 reserve/input 경계, S3 exception, transaction commit 응답 유실, worker done과 producer 지연 경쟁을 추가한다.

---

## 4. HIGH

### H3-01 · signed vendor `outputUrl`을 Firestore job에 저장해 “URL 미저장” 불변식을 위반한다

**근거**

- `31-09-PLAN.md:51,80,104,125`는 polling 성공 시 `fetching(outputUrl 기록)` 후 fetch가 그 값을 읽는다.
- `update_analysis_visual`에 URL 인자가 없다는 보호는 analysis 문서만 보호한다. `visualJobs`도 Firestore이며 signed URL은 bearer credential이다.
- 현재 테스트는 Firestore 문자열에 `dashscope`/`aliyuncs`가 없는지만 찾는다. 다른 CDN host 또는 필드명 `outputUrl` 자체는 놓친다.
- signed URL은 fetch 지연/재시도 중 만료될 수도 있다.

**제가 해결한다면**

- job에는 `taskId`만 보존한다.
- fetch 시작 시 `taskId`를 한 번 더 poll/resolve해 fresh URL을 얻고, 같은 invocation에서 즉시 streaming download한다.
- 필요하면 state를 `resolving → fetching`으로 분리하되 raw URL은 메시지·Firestore·로그에 남기지 않는다.
- 테스트는 Firestore 전체 직렬화에 `http://`, `https://`, `outputUrl`, `signedUrl`이 없음을 assert한다.

---

### H3-02 · calibration이 judge/pose 구현보다 먼저 실행되어 재현 가능한 측정 경로가 없다

**근거**

- 31-01 Task 3은 “31-05와 동일한 judge 프롬프트”와 pose 측정을 실행해 threshold를 선택한다.
- 실제 `judge_corrected_pose`는 31-05, `measure_generated_pose`와 `/pose-image`는 31-06에서 만들어진다. 두 plan은 31-01 산출값을 다시 전제로 한다.
- 31-01 Task 3의 `<files>`는 결과 JSON/MD뿐이고, fixture enumeration·Gemini 호출·pose 측정·grid 계산을 재실행할 harness 파일이 없다.
- 스모크 신규 출력에는 keypoint 산출 경로가 명시되지 않았고 “Pod 불요 시 기존 kpts 재사용”은 신규 4개 출력의 pose error를 보장하지 않는다.

**제가 해결한다면**

- 31-01은 privacy 결정, 모델 smoke, **라벨 fixture manifest**까지만 만든다.
- 31-05/06은 threshold를 인자로 받는 raw judge/pose 측정기를 구현한다.
- 새 calibration plan을 31-05와 31-06 뒤에 두고, 실행 가능한 `calibrate_visual_gates.py`가 fixture별 raw verdict/error와 grid FA/FR 표를 생성하게 한다.
- 31-09/10은 이 calibration plan에 의존하도록 wave를 한 단계 이동한다.
- JSON에는 fixture hash, judge model/prompt version, pose model version, 실행 시각을 넣어 재현성과 drift를 추적한다.

---

### H3-03 · before/after inline Gemini 요청이 공식 20MB 총 요청 상한을 넘을 수 있다

**근거**

- worker는 generated image를 최대 20MB까지 허용하고, judge는 before/after를 둘 다 base64 inline으로 보낸다(`31-05-PLAN.md:107`, `31-09-PLAN.md:104-105`).
- base64는 원본보다 약 4/3 커진다. 8MB 이미지 두 장만으로도 prompt를 제외한 inline data가 약 21.3MB다.
- Google 공식 문서는 inline image data를 포함한 **전체 요청 크기**를 20MB 미만으로 제한한다.

**제가 해결한다면**

- judge 전용으로 EXIF 제거, 최대 변 1600~2048px, bounded JPEG quality로 정규화한 파생 이미지를 메모리/`/tmp`에서 만든다.
- 최종 JSON body byte length를 POST 전에 측정해 20MB보다 충분히 낮은 내부 상한(예: 16MB)을 강제한다.
- 초과는 `judge_failed`로 조용히 보내지 말고 `judge_input_too_large` typed reason으로 관측한다.
- 원본 canonical 결과와 pose gate 입력은 별개로 유지해 판정용 압축이 사용자 결과를 바꾸지 않게 한다.

공식 근거: [Google Gemini image understanding — inline request 20MB limit](https://ai.google.dev/gemini-api/docs/image-understanding)

---

### H3-04 · worker의 20MB image 허용과 `/pose-image` 8MB 상한이 서로 맞지 않는다

**근거**

- correctedPose download는 20MB까지 허용한다(`31-09-PLAN.md:104`).
- `/pose-image`는 `imageB64` 8MB 상한이다(`31-06-PLAN.md:60`).
- 상한이 decoded bytes인지 base64 문자열인지도 명시되지 않았다. 문자열 기준이면 약 6MB raw image부터 거부될 수 있다.

**제가 해결한다면**

- `/pose-image` 계약을 “decoded image bytes 최대 N, pixel count 최대 P, width/height 최대 D”로 명확히 한다.
- worker가 decode 후 deterministic resize/re-encode한 pose 전용 PNG/JPEG를 보내고 전송 전 base64/body 상한을 assert한다.
- decompression bomb 방지를 위해 PIL `MAX_IMAGE_PIXELS`, format allowlist, decode 후 dimension/pixel cap을 함께 둔다.
- 8MB 경계값의 바로 아래/위와 큰 해상도·작은 압축 파일 테스트를 추가한다.

---

### H3-05 · 실제 redirect 통합 테스트는 첫 `http` scheme 검사에서 끝나 30x handler를 검증하지 못한다

**근거**

- production 규칙은 최초 URL scheme이 `https`가 아니면 `bad_scheme`이다.
- 계획된 통합 테스트는 `http.server.ThreadingHTTPServer`의 `http://127.0.0.1` URL을 쓴다.
- `_test_allowed_hosts`와 `_test_allow_private`는 host/IP만 우회하고 scheme을 우회하지 않는다.
- 따라서 기대한 `VendorDownloadError('redirect')`까지 도달하지 않고 `bad_scheme`이 발생한다.

**제가 해결한다면**

- local server socket을 임시 self-signed certificate로 TLS wrap하고, 테스트 전용 SSL context를 dependency injection한다.
- 또는 opener/HTTPS handler를 주입해 최초 요청은 HTTPS 계약을 유지하면서 실제 301/302/303/307/308 응답을 처리하게 한다.
- production 함수에 `allow_http` 우회 인자를 추가하지 않는다.

---

### H3-06 · `ru_maxrss` delta를 같은 pytest process에서 재면 메모리 검증이 불안정하고 플랫폼 단위도 다르다

**근거**

- `ru_maxrss`는 현재 사용량이 아니라 프로세스 lifetime high-water mark다.
- 이전 테스트가 이미 더 높은 RSS를 기록하면 200MB download test의 delta가 0에 가까워져 거짓 green이 된다.
- macOS는 bytes, Linux는 KiB 단위여서 `<64MB` 비교를 그대로 쓰면 환경별 의미가 달라진다.

**제가 해결한다면**

- 대용량 다운로드를 fresh subprocess에서 실행한다.
- 플랫폼별 단위를 정규화하고 baseline/peak를 구조화된 JSON으로 반환한다.
- CI에서는 절대 peak와 payload 대비 증가량을 모두 검사하고, IaC 메모리 결정은 Lambda와 동일한 Linux/container 측정값을 사용한다.

---

### H3-07 · 학습 pair 3-object 저장이 부분 실패하면 PII object가 orphan으로 남는다

**근거**

- `store_training_pair`는 `before.png`, `after.png`, `meta.json`을 순차 put하고 예외 시 False만 반환한다(`31-07-PLAN.md:65`).
- 두 번째/세 번째 put 실패 시 먼저 성공한 before/after를 삭제한다는 규칙이 없다.
- consumer가 prefix listing을 하면 meta 없는 부분 pair를 읽을 가능성도 명시적으로 차단되지 않는다.

**제가 해결한다면**

- 같은 pair prefix에 staging object를 쓰고 `meta.json` 또는 `_COMMITTED`를 마지막 commit marker로 쓴다.
- 예외 시 이번 호출에서 만든 모든 version ID/object를 best-effort 삭제한다.
- consumer는 commit marker가 있는 pair만 열거한다.
- lifecycle은 staging/partial prefix를 더 짧게 만료한다.
- 1/2/3번째 put 각각의 실패 주입에서 object 0개 또는 committed pair만 남는지 검증한다.

---

### H3-08 · bucket versioning 상태를 확인하지 않아 lifecycle과 삭제 요청이 PII의 noncurrent version을 남길 수 있다

**근거**

- dry-run은 current object `Expiration` 규칙만 merge한다(`31-10-PLAN.md:124`).
- 삭제 스크립트도 일반 list/delete만 계획한다(`31-07-PLAN.md:83`).
- versioning-enabled/suspended bucket에서 일반 delete와 current expiration은 delete marker를 만들고 기존 데이터는 noncurrent version으로 남을 수 있다.
- 계획에는 `get-bucket-versioning`, `NoncurrentVersionExpiration`, `list_object_versions`, versionId 삭제가 없다.

**제가 해결한다면**

- dry-run 첫 단계에서 bucket versioning과 Object Lock을 조회한다.
- versioning이 enabled/suspended이면 민감 prefix 규칙에 `NoncurrentVersionExpiration`과 expired delete marker 정리를 포함한다.
- 사용자 삭제 스크립트는 `list_object_versions`로 Versions/DeleteMarkers를 모두 열거해 version ID별 삭제한다.
- 적용 후 current/noncurrent version 개수까지 검증하고 SUMMARY에 기록한다.

AWS 공식 문서상 versioned bucket의 current `Expiration`은 noncurrent version을 지우지 않으며, 영구 제거에는 `NoncurrentVersionExpiration` 또는 versionId 지정 삭제가 필요하다: [S3 deleting object versions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjectVersions.html), [NoncurrentVersionExpiration API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_NoncurrentVersionExpiration.html).

---

### H3-09 · sweeper가 worker와 reserved concurrency 2를 공유해 복구 경로가 본 작업에 굶을 수 있다

**근거**

- `VisualWorkerFunction` 하나가 SQS event source와 EventBridge schedule을 모두 처리하고 reserved concurrency가 2다(`31-10-PLAN.md:123`).
- queue가 계속 차 있거나 vendor 호출이 길면 두 slot을 SQS invocation이 점유할 수 있다.
- 이때 initial/per-transition outbox를 복구해야 할 schedule invocation이 throttle되어 복구 latency가 예측 불가능해진다.

**제가 해결한다면**

- `VisualDispatchFunction`을 작은 별도 Lambda로 분리하고 전용 reserved concurrency 1을 준다.
- worker는 job 처리만, dispatcher는 `dispatchState=pending` query/send/mark만 담당한다.
- pending outbox age metric과 alarm을 추가하고, 정상 queue backlog와 별개로 SLO를 둔다.

---

### H3-10 · IAM fallback canary의 “receive/delete”가 다른 실제 메시지를 삭제할 수 있다

**근거**

- 31-12는 IAM simulation 불가 시 RunPod credential로 canary send 후 즉시 receive/delete하도록 한다(`31-12-PLAN.md:106`).
- SQS receive는 방금 보낸 message를 선택한다는 보장이 없다. queue에 기존 message가 있으면 다른 작업을 받아 삭제할 수 있다.
- worker event source가 동시에 canary를 가져가면 검증도 비결정적이다.

**제가 해결한다면**

- 우선 `simulate-principal-policy` 또는 `sts get-caller-identity` + policy inspection으로 끝낸다.
- 실 canary가 꼭 필요하면 별도 temporary verification queue를 같은 최소 policy 범위로 만들거나, production handler가 외부 side effect 없이 소비하는 명시적 `action=iam_probe`를 정의한다.
- receive한 message가 고유 canary ID와 일치하지 않으면 절대 delete하지 않고 visibility를 즉시 복원한다.

---

### H3-11 · HMAC key set 검증이 불충분해 회전 시 적재·삭제가 런타임에서 깨질 수 있다

**근거**

- `_load_hmac_keys`는 JSON 파싱, active 존재, keys 비어 있지 않음까지만 검사한다(`31-07-PLAN.md:65`).
- `active in keys`, 각 key의 유효 hex, 정확한 32-byte 길이, version 이름 uniqueness/형식은 고정하지 않는다.
- 잘못된 SecureString이 배포되면 적재는 fail-closed하더라도 삭제 스크립트가 기존 pair ID를 재계산하지 못할 수 있다.

**제가 해결한다면**

- strict schema validator를 하나만 두고 store/delete/dry-run이 공용 사용한다.
- `active in keys`, nonempty stable version ID, `bytes.fromhex`, 32 bytes, unknown top-level key 정책을 검사한다.
- rotation은 기존 key를 삭제하지 않고 새 active를 추가하는 방식만 허용하고, 삭제 전 inventory에 등장한 `hmacKeyVersion` 전부가 key set에 존재하는지 gate로 검사한다.

---

## 5. MEDIUM

### M3-01 · topology parity가 해부학적 좌우 label과 실제 mirror 여부를 혼동할 수 있다

shoulder/hip 좌우 x-sign만으로 mirror parity를 추정하면 측면 자세, 도립, 큰 가림에서 잘못된 확정값이 나올 수 있다. unknown 생략은 좋지만 “틀린 known” fixture가 없다. 제가 고친다면 전처리 mirror metadata를 provenance에 넣거나, front/side/inverted/mirrored golden fixture에서 parity를 검증하고 애매한 경우 unknown 범위를 넓힌다.

### M3-02 · `privacy_decision.json`을 runtime에서 읽는지 build-time 상수로 컴파일하는지 모호하다

31-07은 상수와 repo JSON을 테스트로 대조하지만, 31-10 option branch는 “privacy_decision.json 값으로 분기”라고 표현한다. `.planning`은 Lambda/Pod package에 포함된다는 보장이 없다. 결정값은 template env 또는 배포된 config/상수로 명시하고, build test가 JSON과 일치하는지 검사해야 한다.

### M3-03 · lifecycle apply 명령의 relative file path가 산출 위치와 맞지 않을 수 있다

artifact는 phase 하위 `infra/lifecycle_merged.json`인데 31-12 명령은 `file://lifecycle_merged.json`이다. checkpoint action에 repo-root 기준 absolute/정확한 relative path를 써야 한다.

### M3-04 · vendor URL 미저장 테스트가 특정 hostname 문자열만 검사한다

`dashscope`/`aliyuncs` 부재는 URL 부재를 증명하지 않는다. job/analysis fixture를 전체 직렬화해 URL scheme과 URL 계열 field name이 모두 없는지 검사해야 한다.

### M3-05 · 삭제 대상 joint 집합이 현재 `ARROW_JOINT_MAP`에만 의존한다

향후 map에서 joint가 제거/rename되면 과거 pair ID를 재계산하지 못한다. stable historical joint registry를 유지하거나, 개인정보 원문 없이 삭제 가능한 별도 keyed delete index를 설계해야 한다.

### M3-06 · `abs(points)` 동률의 deterministic tie-break가 없다

같은 감점의 여러 record 순서가 입력/serialization에 따라 바뀌면 correctedPose target도 달라진다. criterion priority, confidence, frame index, criterion key 순의 고정 tie-break를 계약과 테스트에 넣어야 한다.

### M3-07 · `create_unconfirmed` 수동 reconciliation의 상관 키가 vendor에 전달되지 않는다

`requestKey`는 Firestore에만 있고 vendor idempotency/request metadata로 전달되지 않는다. DashScope console에서 시간대와 입력만으로 찾는 것은 확정적 reconciliation이 아니다. vendor가 client tag/header를 지원하는지 확인하고, 불가능하면 “정확한 복구”가 아니라 “중복 과금 회피를 위한 수동 판정”임을 운영 문구에 명확히 써야 한다.

---

## 6. 검증 계획에서 바꿔야 할 항목

현재 `31-VALIDATION.md`의 fault matrix는 항목 수는 늘었지만 다음 기대값을 교체해야 한다.

| 현재 행 | 문제 | 교체할 검증 |
|---|---|---|
| continuation send 직전 crash → CAS no-op 멱등 | 다음 action이 유실됨 | 각 state transaction이 `nextAction/pending`을 남기고 dispatcher가 복구해 terminal 도달 |
| terminal write 직전 crash | dual-write 사이 crash를 안 다룸 | canonical S3 후 crash, Firestore atomic finalize commit 응답 유실 두 케이스 |
| reserve 후 send 전 | input S3 준비 여부를 안 봄 | reserve 후 S3 전 crash/S3 exception에서 vendor create 0 |
| concurrent enqueue “순차 2회 모사” | 실제 transaction 경쟁 아님 | barrier를 둔 동시 transaction 또는 Firestore emulator concurrency test |
| Firestore vendor hostname 문자열 부재 | URL 부재를 증명하지 못함 | 모든 persisted doc에 scheme/URL field 부재 |
| local HTTP redirect 5종 | scheme gate에서 종료 | TLS local server로 redirect handler 실제 도달 |
| same-process ru_maxrss delta | high-water/단위 문제 | isolated Linux subprocess peak 측정 |
| pair put exception → False | partial object 잔존 미검증 | 각 put 단계 실패 후 committed/PII object 정합 검사 |
| lifecycle prefix/개수 일치 | noncurrent version 미검증 | bucket versioning별 current/noncurrent/delete-marker 검증 |

추가 필수 gate:

- `polling/fetching/judging/pose_checking` 각각에서 CAS commit 직후 crash 후 자동 복구.
- job terminal 상태와 analysis result 상태가 항상 일치한다는 invariant/property test.
- before+after Gemini serialized body가 내부 상한 이하임을 검사.
- 20MB vendor image가 pose 전송용 정규화 뒤 endpoint 상한 이하가 되는 테스트.
- dispatcher 전용 concurrency와 pending outbox age alarm template assertion.
- versioned bucket fixture에서 retention/delete가 모든 version을 제거하는 테스트.

---

## 7. 권장 재계획 순서

제가 수정한다면 아래 순서로 계획을 고친다.

1. **31-02 상태 저장 계약 재작성**
   - 모든 transition에 `nextAction`, `dispatchState`, `generation/transitionVersion` 추가.
   - job+analysis atomic `finalize_visual_job` 추가.
   - correctedPose input readiness를 `upload-first` 또는 `awaiting_input`으로 명시.

2. **31-09 worker/dispatcher 분리**
   - worker는 state action 1개만 수행하고 durable next action을 transaction에 남김.
   - 별도 dispatcher가 모든 pending continuation을 발행.
   - moderation retry도 같은 state/outbox 규칙 사용.
   - `outputUrl` persistence 제거.

3. **31-10 enqueue 순서 수정**
   - input ready 뒤 reserve/pending/outbox를 원자화.
   - SQS send 뒤 analysis pending write 제거.
   - dispatcher 별도 Lambda/IAM/concurrency/alarm 반영.

4. **calibration plan을 31-05/06 뒤로 이동**
   - reproducible harness를 실제 산출물로 추가.
   - 31-09/10 dependency와 wave 재배치.

5. **payload·privacy 경계 보강**
   - Gemini 20MB total body, pose decoded/pixel cap, judge/pose 정규화.
   - pair commit marker/partial cleanup.
   - S3 versioning-aware lifecycle와 versionId deletion.

6. **VALIDATION fault matrix 재작성**
   - “no-op이므로 멱등”을 PASS 기준에서 제거.
   - 모든 테스트의 최종 기준을 `terminal 도달 + 외부 create 중복 0 + job/analysis 일치 + PII 잔존 없음`으로 통일.

---

## 8. 실행 승인 조건

다음 조건을 계획 문서와 테스트 acceptance에 반영하기 전에는 Phase 31 실행을 승인하지 않는다.

- [ ] 모든 nonterminal transition이 state와 next-action outbox를 같은 transaction에 기록한다.
- [ ] dispatcher가 `dispatchState=pending`인 모든 state를 독립 concurrency로 복구한다.
- [ ] job terminal과 analysis visual status가 하나의 Firestore transaction으로 갱신된다.
- [ ] correctedPose input object가 준비되기 전에는 create action이 발행될 수 없다.
- [ ] producer의 늦은 pending write가 worker의 done/failed를 되감을 수 없다.
- [ ] signed vendor URL이 Firestore/SQS/log에 저장되지 않는다.
- [ ] calibration이 31-05/06 실제 측정 코드를 사용하는 재현 가능한 harness로 실행된다.
- [ ] Gemini before/after 요청과 `/pose-image` 요청이 명시적 byte/pixel 상한 안에 정규화된다.
- [ ] pair partial put 실패 시 PII orphan이 남지 않는다.
- [ ] versioned bucket에서도 lifecycle와 삭제 요청이 noncurrent version까지 제거한다.
- [ ] fault injection이 각 CAS commit 직후 crash와 terminal atomic commit 응답 유실을 검증한다.

---

## 9. 최종 의견

3차 개정은 **무엇을 교정할지**에 대한 의미 계약과 vendor create의 중복 과금 방어를 실질적으로 개선했다. 특히 `CorrectedPoseTarget`, `creating` lease, explicit task polling, immutable source hash, versioned HMAC, 5-wave DAG는 유지할 가치가 있다.

하지만 현재 가장 큰 위험은 상태 종류가 부족한 것이 아니라 **상태와 메시지, terminal job과 사용자 결과가 각각 따로 commit되는 것**이다. 이 부분을 고치지 않으면 테스트가 많아도 production crash 한 번으로 고아 job이나 영구 pending이 생긴다.

따라서 판정은 **BLOCK**이다. 수정 범위는 Phase 31 전체 재작성까지는 필요 없고, 31-02/09/10의 transaction/outbox/finalize 계약과 그에 연결된 validation matrix를 집중 재계획하면 된다. 그 수정 뒤에는 4차 리뷰에서 blocker 해소 여부만 좁게 재검증할 수 있다.
