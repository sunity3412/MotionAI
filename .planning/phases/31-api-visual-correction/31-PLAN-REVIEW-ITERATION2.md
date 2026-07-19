# Phase 31 계획 2차 리뷰 — 직접 수행, 외부 리뷰어 미사용

**리뷰 일자:** 2026-07-19  
**리뷰 범위:** 개정된 `31-01-PLAN.md` ~ `31-12-PLAN.md`, `31-CONTEXT.md`, `31-RESEARCH.md`, `31-PATTERNS.md`, `31-VALIDATION.md`, 1차 리뷰(`31-PLAN-REVIEW.md`/`31-REVIEWS.md`) 및 계획이 참조하는 현재 backend/app 코드  
**리뷰 방법:** 1차 지적별 해소 추적, 상태 전이·재전달·크래시 지점 분석, 데이터 의미/프레임 provenance 대조, IAM·SQS·S3·Lambda 운영 제약 대조, privacy/삭제 경로 검증, 실행 DAG 및 검증 게이트 점검  
**외부 리뷰어:** 사용하지 않음. 외부 AI/cross-AI/서브에이전트 리뷰 없이 직접 검토했다. AWS/Python 공식 문서는 런타임 사실 확인용 1차 자료로만 사용했다.  
**최종 판정:** **BLOCK / REPLAN REQUIRED**

---

## 1. 총평

1차 리뷰 뒤의 구조 개정은 의미가 크다. 특히 다음은 올바른 방향으로 바뀌었다.

- 거짓 3D/R3F 뷰어를 제거하고 카메라 평면 2D 비교 뷰어로 재결정했다.
- 화살표 기하가 감점 record의 `measuredValue`/`baselineValue`를 읽지 않고 3점 관절과 DTW 대응 reference 좌표를 쓰도록 바뀌었다.
- Firestore에는 canonical S3 key만 저장하고, 표시 URL은 인증된 `playback-url` 경로에서 재서명한다.
- 자동 교정 생성을 분석 프로세스 내부의 장시간 외부 호출에서 분리해 enqueue-only 구조로 옮겼다.
- worker가 한 번의 긴 폴링 후 정상 return을 재전달로 오인하던 설계를 버리고 delayed SQS continuation과 partial batch failure를 도입했다.
- before/after judge와 생성 이미지 pose 재측정 게이트, strict 학습 동의, HMAC 가명화, 임시 입력 정리, feature flag OFF, 실 E2E 완료 게이트를 추가했다.

그러나 개정 계획은 아직 **“메시지를 다시 보낼 수 있음”을 “유료 작업이 멱등이고 고아가 될 수 없음”으로 과대평가**하고 있다. 또한 자동 교정 이미지의 핵심 입력인 `joint`와 `targetDeg`가 어떤 신뢰 가능한 기하에서 만들어지는지 정의되어 있지 않다. 이 둘은 단위 테스트를 많이 추가해도 구현 의미가 정해지지 않은 상태라 해결되지 않는다.

현재 발견한 실행 차단 사유는 3개다.

1. 자동 교정의 `joint`/`targetDeg`가 감점 record에서 나온다고만 되어 있으나 record에는 관절 식별자가 없고, `reference_relative` 값은 절대 목표각이 아닐 수 있다. 더구나 감점 `points`는 signed-negative인데 “최대 감점” 정렬도 모호하다.
2. worker가 `reserved → polling`으로 먼저 바꾼 뒤 vendor create를 호출한다. 전이 직후 또는 create 성공 직후 크래시하면 재전달 `run`은 stale로 no-op 되어 영구 고아가 되거나, 재시도를 허용하면 유료 task가 중복 생성된다. 이미지 adapter의 async 내부 폴링은 이 문제를 더 키운다.
3. pipeline enqueue가 S3 입력을 먼저 덮어쓰고 `reserve_visual_job` 결과와 무관하게 분석 상태를 `pending`으로 만들고 SQS를 발행한다. 동일 분석 재처리/중복 실행 시 이미 `done`인 job은 worker에서 no-op 되지만 UI 상태만 `pending`으로 되돌아갈 수 있다.

따라서 **Wave 1 구현 전, 최소한 31-02/03/05/09/10의 상태·target 계약을 다시 묶어 수정해야 한다.**

### 발견 수

| 심각도 | 수 | 의미 |
|---|---:|---|
| BLOCKER | 3 | 실행 전 계획 수정 필수 |
| HIGH | 10 | blocker 수정과 같은 재계획에서 해결 필요 |
| MEDIUM | 5 | 배포 전 계약·검증 보강 필요 |

---

## 2. 1차 리뷰 지적 해소 추적

| 1차 ID | 2차 상태 | 판단 |
|---|---|---|
| B-01 거짓 3D | **해소** | D-04/D-10 amended, `PoseCompareViewer` 2D 고정, R3F/orbit/3D 카피 금지 |
| B-02 화살표 의미 오류 | **부분 해소** | 3점+reference geometry는 맞지만 per-joint “가까운 반사 후보” 휴리스틱은 오방향 가능 |
| B-03 SQS 정상 return 오해 | **부분 해소** | continuation/partial failure는 맞지만 vendor create 전후 crash window가 남음 |
| H-01 분석 경로 결합 | **부분 해소** | enqueue-only로 분리했으나 target 생성·dispatch 내구성·IAM이 불완전 |
| H-02 만료 URL | **대체로 해소** | canonical key+재서명 도입. exact key/status guard는 추가 필요 |
| H-03 약한 품질 gate | **부분 해소** | before/after+pose gate 도입. target provenance와 임계값 calibration 미해결 |
| H-04 privacy/보존 | **부분 해소** | release checkpoint/HMAC/1일 input lifecycle/삭제 스크립트 추가. key rotation·보존기간·blur branch 미해결 |
| H-05 외부 다운로드 경계 | **부분 해소** | scheme/host/IP/type/size cap은 추가. urllib redirect 차단 방식과 메모리 경계가 불완전 |
| H-06 원자성/고아 | **부분 해소** | quota+job transaction은 개선. S3/SQS outbox와 replay-safe enqueue가 없음 |
| H-07 검증 없는 완료 | **해소** | flag OFF→ON, 실 인증 correctedPose/rotation E2E를 완료 필요조건으로 고정 |
| M-01 DAG | **미해소** | 31-09와 31-10이 같은 wave인데 31-10 IaC가 31-09 산출물을 가리킴 |
| M-02 대형 reference 구독 | **해소** | 단일 문서 구독 훅으로 변경 |
| M-03 typecheck-only | **해소** | jest-expo checkpoint와 유닛/컴포넌트 테스트 추가 |
| M-04 조건부 hook | **해소** | null ID를 넘기는 무조건 hook 호출로 고정 |
| M-05 문자열 오류 분기 | **해소** | typed `ApiError.code` 도입 |
| M-06 일일 한도 | **해소** | KST 날짜 키, 사용자/전역 한도, fail-closed env 명시 |
| M-07 빈 검증/경로 오류 | **대체로 해소** | 경로 수정 및 full suite/실 E2E 추가. crash/replay/security fixture는 추가 필요 |
| M-08 약한 adapter 반환형 | **부분 해소** | typed dataclass는 도입되나 async image task journal 계약이 없음 |
| L-01 무승인 유료 smoke | **해소** | privacy+비용 checkpoint 뒤 최대 4콜 |
| L-02 silhouette 명칭 | **해소** | 계약/카피를 `correctedPose`/“교정된 자세”로 변경 |
| L-03 validator 중복 | **해소** | 공유 `validate_analysis_id_format` 계획 |
| L-04 pending 숨김 의미 | **해소** | 표시 폴백이며 서버 job 취소가 아님을 주석/운영 스크립트에 명시 |

---

## 3. BLOCKERS

### B2-01 · 자동 교정 이미지의 목표 관절과 목표각 provenance가 정의되지 않았다

**근거**

- `31-10-PLAN.md:116`은 top-1 결함 관절을 “감점 records 최대 감점 기준”으로 고르고 `_enqueue_corrected_pose_job(... joint, target_deg ...)`에 전달한다고만 한다.
- 현재 `DeductionRecord`(`deduction_engine.py:47-68`)에는 `joint_key`가 없다. criterion/dimension 단위 record를 어떤 COCO 관절에 연결할지 계획에 없다.
- `points`는 signed-negative다(`models.py:150`, `deduction_engine.py:335`). 숫자상 `max(points)`는 가장 큰 감점이 아니라 0에 가장 가까운 작은 감점을 고를 수 있다. “최대 감점”이 `min(points)`인지 `max(abs(points))`인지 명시되지 않았다.
- 1차 B-02에서 확인했듯 `reference_relative.measuredValue`는 학생의 절대 관절각이 아니라 reference 대비 편차일 수 있다. 화살표 계획은 이 함정을 피했지만, correctedPose enqueue의 `targetDeg` 산출은 그 보호를 재사용하지 않는다.
- `31-09-PLAN.md:90`은 전달받은 `targetDeg`를 프롬프트와 pose gate 둘 다에 사용한다. 잘못된 target을 생성 지시와 검증 기준에 동시에 넣으면 “잘못된 목표에 정확히 맞춘” 이미지가 gate를 통과한다.
- 입력 `src_png`가 어느 `userFrameIdx`인지도 target과 하나의 provenance 객체로 묶이지 않는다. top-1 감점과 top-1 fault zoom이 다른 기준을 고르면 source frame, joint, target pose가 서로 다른 순간을 가리킬 수 있다.

**영향**

사용자에게 잘못된 관절을 교정하거나 편차값을 절대 목표각으로 사용한 이미지를 보여줄 수 있다. 품질 judge와 pose gate가 동일한 오염 target을 공유하므로 후단 검증이 이 오류를 발견하지 못한다.

**제가 해결한다면**

`joint`, `targetDeg`, `src_png`를 따로 계산하지 않고 하나의 immutable 계약으로 만든다.

```text
CorrectedPoseTarget
  jointKey
  proximalKey / vertexKey / distalKey
  userFrameIdx / refFrameIdx
  sourceKind = reference_pose | ipsf_absolute
  sourceArtifactKey 또는 sourceFrameHash
  targetDeg
  referenceEndpoint 또는 reference 3점
  confidence
  provenanceVersion
```

- v1은 `TargetArrowSpec`과 동일한 **DTW matched reference 3점**에서 target angle을 계산한다.
- 감점 record는 후보 우선순위에만 쓰고 기하값에는 쓰지 않는다. 우선순위는 `points`의 부호를 반영해 명시적으로 `abs(points)` 또는 `min(points)`를 사용한다.
- criterion→joint 매핑이 선언된 항목만 후보가 된다. collective/unmapped/low-confidence/ref-match-failed이면 correctedPose 생성을 생략하고 legacy 숨김을 유지한다.
- source frame은 동일 target의 `userFrameIdx`에서 추출하고 hash를 job payload에 기록한다.
- `31-03`에서 arrow용과 correctedPose용 target builder를 공용화하거나, 최소한 동일 reference geometry helper를 단일 소스로 사용한다.
- 테스트는 `reference_relative`, signed-negative 정렬, unmapped criterion, 좌/우, inverted, low confidence, source-frame/target-frame 일치까지 포함한다.

---

### B2-02 · 유료 vendor task 생성 전후의 crash window가 여전히 고아 또는 중복 과금을 만든다

**근거**

- `31-09-PLAN.md:72`은 `action='run'`에서 job을 `reserved|dispatch_failed → polling`으로 먼저 CAS한 뒤 kind handler가 vendor create를 호출하도록 한다.
- create 전 크래시: job은 이미 `polling`, `taskId=None`이다. 원 SQS message가 재전달되어도 `run`은 `reserved|dispatch_failed`만 허용하므로 stale no-op으로 정상 return한다. continuation도 없고 terminal도 아니어서 계획이 주장하는 불변식이 깨진다.
- create 성공 후 `taskId` CAS 전 크래시: vendor에는 유료 task가 생겼지만 Firestore에는 ID가 없다. 재전달을 no-op하면 결과를 잃고, create 재호출을 허용하면 중복 과금한다.
- `taskId가 이미 있으면 create 생략` 테스트는 “ID가 저장된 뒤”의 재전달만 검증한다. 가장 위험한 “vendor 성공, journal 쓰기 전” 구간은 검증하지 않는다.
- `31-05-PLAN.md:68`의 `WanImageAdapter`는 선택 모델이 async이면 내부 폴링한다고 한다. 이미지 Protocol은 `VendorImageResult`만 반환하고 task creation/journal을 노출하지 않는다. Lambda timeout/크래시 시 이미지 task를 재개할 식별자가 없다.
- correctedPose 한 invocation은 생성, 다운로드, Gemini 최대 2회, pose endpoint, S3 저장까지 직렬로 수행한다. 각 단계 timeout 상한 합은 worker 300초를 쉽게 소진할 수 있다.

**영향**

유료 생성 작업이 영구 고아가 되거나 동일 분석에 중복 과금될 수 있다. 이것은 SQS continuation을 도입했는지와 별개의 exactly-once side-effect 문제다.

**제가 해결한다면**

job을 외부 side effect별 durable state로 분해한다.

```text
reserved
  -> creating (leaseOwner, leaseExpiresAt, requestKey)
  -> polling (taskId 필수)
  -> fetching
  -> judging
  -> pose_checking
  -> done | failed
```

- create 전에 stable `requestKey`를 만든다. vendor가 idempotency token을 지원하면 반드시 전달한다.
- vendor가 idempotency를 지원하지 않으면 `creating` lease가 만료된 후 무조건 재생성하지 않는다. vendor의 request 조회 API/request-id 조회 가능성을 먼저 확인하고, 불가능하면 중복 과금 가능성을 운영 계약에 명시하고 수동 reconciliation 대상으로 둔다.
- `polling` 상태는 `taskId` 없이는 성립할 수 없도록 CAS validator를 둔다.
- 이미지 async API도 video와 동일하게 `create_task/poll` 형태로 노출한다. adapter 내부 장시간 polling은 금지한다.
- sync-only 이미지 모델을 선택한다면 31-01 smoke가 p95 상한과 retry/idempotency 특성을 증명한 경우에만 별도 `generating` state로 허용한다.
- 각 외부 단계는 한 invocation에 하나만 수행하고 다음 SQS action을 발행한다. 이를 통해 300초 timeout 안에 여러 외부 timeout이 누적되지 않게 한다.
- 필수 crash-injection 테스트: create 직전, vendor 2xx 직후, taskId write 직후, continuation send 직전, output S3 put 직후, terminal Firestore write 직전.

---

### B2-03 · pipeline의 correctedPose enqueue가 replay-safe하지 않아 완료 상태를 pending으로 되돌릴 수 있다

**근거**

- `31-10-PLAN.md:116`의 순서는 S3 `src.png` put → `reserve_visual_job` → `update_analysis_visual('pending')` → SQS send다.
- `reserve_visual_job`은 이미 `done`/`polling` job이 있으면 `created=False`로 기존 job을 반환한다(`31-02-PLAN.md:107`). 그러나 enqueue action은 `created`나 기존 state에 따른 분기를 명시하지 않고 항상 pending write와 SQS send를 수행한다.
- 동일 `_process`가 SQS 재전달, Pod 재시작, 운영 재처리 등으로 두 번 실행되면:
  1. `src.png`가 덮어써지고,
  2. done job은 예약되지 않지만 분석 표시 상태는 pending으로 바뀌고,
  3. worker는 `state=done`을 stale message로 no-op 처리한다.
- 결과적으로 canonical output은 존재하지만 앱 카드가 pending 후 timeout 숨김으로 바뀐다.
- 동시 enqueue 테스트는 계획에 없다. 현재 `test_visual_dispatch.py`는 정상 1회와 SQS 실패만 고정한다.

**영향**

at-least-once 분석 경로에서 완료 기능이 사용자 화면에서 사라지고, 입력 artifact가 실행 중 job과 다른 프레임으로 교체될 수 있다.

**제가 해결한다면**

- `reserve_visual_job` 반환을 state machine의 유일한 분기 기준으로 삼는다.
  - `created=True`: immutable source artifact 확보 후 pending+dispatch.
  - existing `done`: S3/analysis 상태를 절대 변경하지 않고 no-op.
  - existing `reserved|dispatch_failed`: 동일 `srcKey/sourceHash`인지 확인하고 필요한 경우에만 재dispatch.
  - existing `polling`: no-op.
  - `failed`: 제품 정책에 따라 명시적 새 generation 번호로 재시도.
- source key를 고정 `src.png` 대신 `visual-input/{uid}/{analysisId}/{sourceHash}.png`처럼 immutable하게 만들고 hash를 job에 기록한다.
- S3 put 실패, reserve 실패, SQS 실패 각각을 복구 가능한 상태로 남긴다. Firestore transaction 안에서 SQS를 원자화할 수 없으므로 outbox 문서를 쓰고 dispatcher가 발행해야 한다.
- 테스트에 duplicate-after-done, duplicate-while-polling, concurrent two enqueue, S3 성공 후 process crash, reserve 성공 후 send crash를 추가한다.

---

## 4. HIGH

### H2-01 · SQS visibility/redrive 설정이 Lambda 공식 운영 권고보다 너무 짧다

**근거**

- `31-10-PLAN.md:116,126`은 worker timeout 300초, queue visibility 360초, `maxReceiveCount=3`을 요구한다.
- AWS Lambda 공식 문서는 SQS source queue visibility timeout을 **function timeout의 최소 6배**로 설정하고, redrive `maxReceiveCount`는 **최소 5**를 권고한다. 300초 worker라면 최소 1,800초가 기준이다.
- 360초는 throttling이나 cold start가 한 번만 겹쳐도 같은 message가 이전 invocation과 동시에 처리될 수 있다. vendor create crash window와 결합하면 중복 과금 위험이 커진다.

**제가 해결한다면**

- worker timeout을 단계별 실제 상한에 맞춰 낮추거나, 300초를 유지하면 `VisibilityTimeout >= 1800`, `maxReceiveCount >= 5`로 설정한다.
- deployment test에서 CloudFormation 값을 파싱해 `visibility >= 6 * timeout + batchingWindow`를 assert한다.
- Lambda reserved concurrency와 vendor rate limit을 함께 정하고, DLQ alarm을 추가한다.

공식 근거: AWS Lambda, “Creating and configuring an Amazon SQS event source mapping”  
https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html

---

### H2-02 · Firestore→SQS delivery는 durable outbox가 아니며 실제 producer 권한도 빠져 있다

**근거**

- rotation SQS send 실패는 사용자가 다시 버튼을 눌러야만 `dispatch_failed`를 복구한다(`31-10-PLAN.md:98`). 사용자가 앱을 닫으면 quota가 소비된 채 발행되지 않는다.
- 자동 correctedPose는 사용자 재요청 진입점이 없다. pipeline send 실패 시 analysis를 `failed`로 만들고 끝나므로 transient SQS 장애가 영구 기능 실패가 된다.
- `list_stuck_visual_jobs.py`는 조회만 하며 재발행하지 않는다.
- IaC 설명은 `VisualRequestFunction`과 `VisualWorkerFunction`의 `sqs:SendMessage`만 명시한다. `PipelineFunction`에는 queue URL env만 추가하고 send 권한을 명시하지 않는다.
- 실제 `_process`가 도는 RunPod의 AWS credential에도 VisualQueue `SendMessage` 권한이 필요하지만 31-12는 “기존 AWS 키”만 체크하고 최소 권한 정책/실권한 검증을 정의하지 않는다.

**제가 해결한다면**

- 예약 transaction에 `dispatchState='pending'` outbox를 함께 기록하고 별도 dispatcher/reconciler가 SQS 발행 후 `sent`로 CAS한다.
- 주기적 sweeper가 `reserved|dispatch_failed`와 `nextDispatchAt`을 재발행한다. 사용자 재시도는 보조 경로여야 한다.
- PipelineFunction role과 RunPod credential role에 정확한 VisualQueue ARN의 `sqs:SendMessage`를 명시한다.
- 배포 gate에서 `aws iam simulate-principal-policy` 또는 실제 canary send/delete로 Lambda fallback과 Pod producer 양쪽 권한을 검증한다.

---

### H2-03 · 화살표의 미러 후보를 “현재 자세에 더 가까운 쪽”으로 고르면 목표가 큰 교정에서 오방향이 가능하다

**근거**

- `31-03-PLAN.md:71`은 direct/reflected endpoint 중 현재 user distal에 더 가까운 후보를 선택한다.
- 이는 “올바른 교정은 작은 이동”이라는 가정이다. 실제 큰 결함, 축을 가로지르는 교정, 잘못 접힌 무릎/팔에서는 잘못된 반사 후보가 더 가까울 수 있다.
- 테스트의 mirrored case도 “가까운 후보가 선택됨”을 검증할 뿐, 실제 영상의 mirror parity가 맞는지를 검증하지 않는다.

**제가 해결한다면**

- per-joint 거리로 parity를 결정하지 않는다.
- 영상/pose 전처리 단계에서 좌우 mirror 여부를 full-body topology, pole axis, reference preprocessing metadata로 한 번 결정해 frame/job provenance에 기록한다.
- parity가 불명확하면 화살표를 생략한다. 두 후보 중 가까운 쪽을 고르는 fallback은 사용자 지시에 쓰지 않는다.
- golden fixture에 “큰 교정인데 반사 후보가 더 가까운” adversarial case를 추가한다.

---

### H2-04 · urllib redirect 차단 설명은 실제로 redirect를 끄지 못한다

**근거**

- `31-05-PLAN.md:85`는 “`HTTPRedirectHandler`를 제거한 opener”로 redirect를 거부한다고 한다.
- Python 공식 문서에 따르면 `urllib.request.build_opener()`는 handler 목록에 같은 클래스 또는 subclass가 없으면 기본 `HTTPRedirectHandler`를 자동 추가한다. 단순히 목록에서 빼는 것은 redirect 비활성화가 아니다.
- mock이 `302`를 직접 반환하는 방식이면 실제 opener가 redirect를 따라가는 동작을 재현하지 못하고 테스트가 거짓 green이 될 수 있다.

**제가 해결한다면**

- `HTTPRedirectHandler` subclass를 명시적으로 전달하고 `redirect_request` 또는 `http_error_301/302/303/307/308`에서 즉시 typed exception을 발생시킨다.
- local HTTP test server로 실제 302→private/other-host redirect를 발생시켜 네트워크 레벨 통합 테스트를 한다.
- proxy auto-detection도 우회 경계가 되므로 `ProxyHandler({})` 사용 여부를 명시한다.

공식 근거: Python `urllib.request.build_opener` 문서  
https://docs.python.org/3/library/urllib.request.html#urllib.request.build_opener

---

### H2-05 · 200MB 결과를 512MB Lambda 메모리에 bytes로 보관하는 계획은 OOM/timeout 여유가 부족하다

**근거**

- `download_vendor_asset`는 최종적으로 전체 `bytes`를 반환한다.
- rotation은 최대 200MB를 bytes로 받은 뒤 S3 `put_object`에 다시 전달한다(`31-09-PLAN.md:108`). Python buffer, HTTP chunk, SDK serialization, runtime/layer 메모리와 겹치면 512MB에서 여유가 작다.
- success poll invocation이 download+S3 upload까지 300초 안에 수행해야 하며 네트워크가 느리면 timeout 후 같은 작업을 반복한다.

**제가 해결한다면**

- `/tmp` 파일로 streaming download하고 누적 byte cap/hash를 계산한 뒤 `upload_file`/multipart upload를 사용한다.
- 가능하면 vendor output을 허용된 host에서 S3 multipart copy할 수 있는 전용 transfer path로 분리한다.
- `fetching` state를 별도 invocation으로 두고 200MB fixture 또는 throttled stream 테스트로 peak RSS와 실행 시간을 측정한다.
- 실측 전에는 MemorySize를 추측하지 말고 max object size에 맞춰 조정한다.

---

### H2-06 · HMAC key rotation/loss 시 기존 학습 pair 삭제가 불가능해지고 보존기간도 정해지지 않았다

**근거**

- pair key는 현재 `PAIR_ID_HMAC_KEY`로 `uid:analysisId:joint`를 재계산해야 찾을 수 있다(`31-07-PLAN.md:59,76`).
- meta에는 uid/analysisId를 남기지 않으며 key version도 없다.
- 키가 회전되거나 SSM parameter가 교체/유실되면 기존 pair prefix를 재계산할 수 없어 삭제 요청을 이행할 수 없다.
- 보존 정책은 “phase 22 재도전 트랙 활성 기간”이다. 종료일/TTL/검토 주기가 없어 실제 retention policy가 아니다.

**제가 해결한다면**

- `hmacKeyVersion`을 meta에 기록하고 SSM에 versioned key set을 보관한다. 삭제 도구는 활성+retired key version을 모두 시도한다.
- 더 나은 방식은 제한된 접근의 encrypted deletion index(`analysisId -> pairId`)를 별도 저장하고 학습 bucket과 권한을 분리하는 것이다.
- pair prefix에 lifecycle 또는 명시적 `deleteAfterMs`를 두고 보존일수, 연장 승인, 철회 SLA를 release gate에서 숫자로 확정한다.
- key rotation 전후 pair 삭제 테스트를 acceptance에 추가한다.

---

### H2-07 · 15°/8° 품질 임계값이 calibration 없이 선언되며 smoke 표본도 너무 작다

**근거**

- `31-01-PLAN.md:106`은 display 15°, training 8°를 “초기 선언값”으로 정한다.
- smoke는 후보 모델당 1회+재시도 1회이고 동일한 단일 정은지 fixture 프레임 중심이다.
- judge confidence 0.7/0.85와 pose score 0.3도 오탐/미탐 근거가 없다.
- 단일 합성 keypoint 단위 테스트는 수학 구현만 검증하며 생성 이미지 pose estimator의 편향, inverted pose, 좌우/occlusion, pole 겹침을 검증하지 않는다.

**제가 해결한다면**

- 최소한 관절/좌우/직립·도립/가림/모션블러를 포함한 작은 calibration set을 만든다.
- 사람이 라벨한 target angle 및 보존 PASS/FAIL과 비교해 false accept/false reject를 측정한다.
- user display는 false accept를 우선 낮추고, training은 더 엄격하게 정한다. 임계값은 결과표에서 고른다.
- 31-01 `blocked`는 모델 호출 성공뿐 아니라 최소 calibration gate 미달에도 true가 되어야 한다.

---

### H2-08 · 31-09와 31-10의 동일 Wave 실행은 실제 산출물 의존성을 표현하지 못한다

**근거**

- 두 plan 모두 wave 3이다.
- 31-10은 `VisualWorkerFunction CodeUri: functions/visual-worker/`를 template에 추가하고 `sam validate --lint`를 실행하지만 worker 디렉터리는 31-09가 만든다.
- 31-09는 worker가 사용할 env/IAM/SQS event source를 31-10에 의존한다.
- 31-10 `depends_on`에는 31-09가 없고, 31-09에도 31-10이 없다. 병렬 실행 중 validation timing에 따라 실패하거나, 각 plan이 상대 계약을 추정해 구현할 수 있다.

**제가 해결한다면**

- 31-09에서 worker code+unit test를 만든 뒤 31-10이 의존하도록 `31-10 depends_on: [31-09, ...]`로 바꾸고 다음 wave로 이동한다.
- 또는 31-09/10을 worker code plan과 IaC/wiring plan으로 명확히 직렬 분리한다.
- 수정된 DAG에 따라 31-11/12 wave 번호와 validation map을 갱신한다.

---

### H2-09 · `autonomous: true` plan이 라이브 bucket lifecycle과 SecureString을 직접 변경한다

**근거**

- `31-10`은 `autonomous: true`다.
- Task 3은 외부 관리 중인 실제 bucket에 `put-bucket-lifecycle-configuration`을 적용하고 SSM SecureString을 생성한다.
- 이 동작은 코드 작성/검증이 아니라 라이브 인프라 mutation이다. `put-bucket-lifecycle-configuration`은 기존 lifecycle을 교체하므로 merge 실수 시 기존 uploads retention rule이 사라질 수 있다.
- 실제 배포는 31-12 human checkpoint라고 쓰지만 lifecycle/SSM mutation은 31-10에 이미 수행된다.

**제가 해결한다면**

- 31-10은 code/IaC 파일 생성과 dry-run merge artifact까지만 수행한다.
- lifecycle 적용과 SSM 생성은 31-12의 별도 `checkpoint:human-action`으로 이동한다.
- before JSON을 SUMMARY 텍스트뿐 아니라 rollback 가능한 scratch artifact로 보관하고, put 후 get으로 rule ID/개수/prefix를 검증한다.
- 가능하면 외부 bucket 설정도 CloudFormation custom resource나 별도 versioned IaC로 소유권을 명확히 한다.

공식 근거: AWS CLI `put-bucket-lifecycle-configuration`은 기존 구성을 대체한다고 명시한다.  
https://docs.aws.amazon.com/cli/latest/reference/s3api/put-bucket-lifecycle-configuration.html

---

### H2-10 · privacy option B(얼굴 blur)는 계획에 적힌 helper와 실제 Lambda runtime이 맞지 않는다

**근거**

- `31-07-PLAN.md:59`은 option B면 `anonymize_batch` 얼굴 blur helper를 적용한다고 한다.
- 실제 `backend/training/datagen/anonymize_batch.py`는 video file batch runner이며 `_anonymize_video`가 Pod용 `ultralytics`/ffmpeg 경로를 lazy import한다. PNG bytes용 얼굴 검출 helper가 아니다.
- worker requirements/IaC에는 ultralytics/torch/ffmpeg가 없고 512MB Lambda에 넣는 것도 현실적이지 않다.
- `anonymize.py`의 순수 blur 함수는 bbox가 필요하다. still image에서 얼굴 bbox를 얻는 경로가 계획에 없다.

**제가 해결한다면**

- privacy checkpoint에서 option A가 확정되면 option B 분기를 계획에서 제거하고 결정값을 downstream plan에 명시적으로 치환한다.
- option B를 지원해야 한다면 PNG 전용 anonymizer를 별도 설계한다. 가능한 선택은:
  - source frame을 만드는 Pod에서 이미 알고 있는 얼굴 keypoint/bbox로 blur한 별도 training-before artifact 생성,
  - `/anonymize-image` Pod endpoint,
  - 검출 실패 시 보수적 head-region blur를 적용하는 lightweight path.
- blur 여부와 anonymizer version을 meta에 기록하고, 원본 before bytes가 training prefix에 절대 올라가지 않는 테스트를 추가한다.

---

## 5. MEDIUM

### M2-01 · playback-url asset guard는 prefix뿐 아니라 exact artifact와 done 상태를 확인해야 한다

- `31-10-PLAN.md:82`는 분석 문서에서 key를 고른다는 점은 좋지만 `results/{uid}/{analysisId}/` prefix만 확인한다.
- `correctedPose`는 `corrected_pose_{joint}.png`, rotation은 `rotation.mp4`라는 exact 계약이 있다. status가 `done`인지도 action에 명확히 고정되지 않았다.
- 제가 수정한다면 asset별 status `done`, exact basename/pattern, extension/content type을 검사하고 stale key가 남은 failed 문서는 404로 강등한다.

### M2-02 · malformed SQS message를 log+skip하면 조용히 삭제된다

- `31-09-PLAN.md:72`는 파싱 실패 메시지를 재전달해도 무의미하다며 정상 처리한다.
- 내부 producer schema 버그나 배포 불일치도 같은 방식으로 영구 삭제된다. 관측 가능한 DLQ 증거가 남지 않는다.
- malformed payload는 typed metric을 남기고 batch failure로 DLQ까지 보내는 편이 안전하다. 정말 폐기할 메시지라면 별도 quarantine 기록과 schema version을 둔다.

### M2-03 · `31-RESEARCH.md`와 `31-PATTERNS.md`의 본문이 여전히 기각된 R3F/inline silhouette 구조를 설명한다

- 상단 SUPERSEDE 주석은 있으나 책임 맵, primary recommendation, phase requirements는 계속 R3F와 `_process` 내부 생성 구조를 권고한다.
- executor가 `read_first`로 두 문서를 읽으므로 계획과 충돌하는 인지 부하가 남는다.
- deprecated 절을 실제로 제거하거나 “Historical—do not implement” 영역으로 이동하고 12-plan 구조 기준으로 재작성하는 것이 좋다.

### M2-04 · validation이 위험한 failure point를 직접 검증하지 않는데 `nyquist_compliant: true`다

- validation map에는 vendor 2xx 직후 crash, duplicate `_process`, done job replay, actual urllib redirect, HMAC rotation, outbox sweeper가 없다.
- 현재 green suite는 happy path와 mock shape를 잘 검증하지만 내구성 주장을 증명하지 못한다.
- blocker/high 수정 후 fault-injection matrix를 validation map에 추가하고 그때 `ready/nyquist_compliant`를 다시 선언해야 한다.

### M2-05 · privacy checkpoint의 결정값이 downstream plan에 parameterized되지 않고 일부가 하드코딩돼 있다

- 31-01은 consent 체계/blur 여부를 결정받지만 31-07은 `CONSENT_VERSION='pilot-optout-v1'`를 미리 고정한다.
- 선택 결과를 ACCEPTANCE 문서에서 사람이 읽고 코드에 반영하라는 방식은 option drift가 생기기 쉽다.
- 31-01 산출물에 machine-readable `privacy_decision.json` 또는 명시적 상수를 만들고 downstream acceptance가 그 값과 일치하는지 assert하는 것이 좋다.

---

## 6. 보존해야 할 강점

재계획 시 아래는 되돌리지 않는 것이 좋다.

- amended D-04/D-10의 정직한 2D 계약과 mode3 숨김.
- `TargetArrowSpec`의 3점 geometry, record 수치 비의존, omission 우선 원칙.
- canonical key만 저장하고 server-selected asset으로 재서명하는 H-02 구조.
- 분석 완료를 시각 생성 실패로 되돌리지 않는 D-08 경계.
- strict `learningOptIn is True`, uid/analysisId 원문 미저장, training gate를 display보다 엄격히 두는 방향.
- feature flag default OFF와 `blocked=true` 시 phase 미완료 처리.
- 실 인증 API→SQS→worker→fresh asset E2E 두 개를 완료 필요조건으로 둔 점.
- typed failure reason, 전용 visual timestamp, 앱의 typed `ApiError`, reference 단일 doc 구독.

---

## 7. 제가 다시 계획한다면 적용할 순서

### Step 1 — target 계약을 먼저 고정

31-03에 `CorrectedPoseTarget`/공용 reference geometry helper를 추가하고 31-10이 그것만 소비하게 한다. 이 작업 전에는 correctedPose worker/prompt/pose gate 구현을 시작하지 않는다.

### Step 2 — paid job state machine을 side-effect 단위로 다시 설계

31-02의 job states/CAS를 `creating/polling/fetching/judging/pose_checking`과 lease/requestKey를 포함하도록 확장한다. 31-05 image adapter도 async task를 노출한다. 31-09는 외부 단계 한 개당 invocation 한 개로 구현한다.

### Step 3 — replay-safe enqueue + outbox

31-10에서 `created/existing state` 분기를 강제하고 immutable source key를 사용한다. Firestore outbox와 reconciler를 추가한다. PipelineFunction/RunPod/VisualRequest/Worker IAM을 표로 고정한다.

### Step 4 — IaC와 실행 DAG 정리

worker code(31-09) → IaC/wiring(31-10)을 직렬화한다. SQS visibility 6배/maxReceive 5+, alarms, concurrency를 명시한다. lifecycle/SSM mutation은 31-12 human checkpoint로 이동한다.

### Step 5 — security/privacy의 조건부 경로를 실행 가능하게 만든다

custom no-redirect handler+실 redirect test, rotation file streaming, HMAC key version/retention, privacy option B의 실제 실행 위치를 확정한다.

### Step 6 — validation을 failure-injection 중심으로 갱신

happy path mock 외에 crash/replay/concurrency/timeout/redirect/key rotation을 넣은 뒤에만 `ready`로 되돌린다.

---

## 8. 재승인 전 최소 acceptance gate

아래가 계획 문서에 명시되고 자동/실검증으로 연결돼야 3차에서는 PASS를 검토할 수 있다.

1. `CorrectedPoseTarget`이 joint, source frame, ref frame, target angle, provenance를 한 객체로 제공한다.
2. `reference_relative` record 수치가 target angle 계산에 들어가지 않는 테스트가 있다.
3. signed-negative 감점 정렬과 unmapped criterion 생략이 테스트된다.
4. vendor create 직전/직후 crash에서 고아 또는 무제한 중복 과금이 생기지 않는다.
5. async image adapter가 taskId journal 없이 내부 polling하지 않는다.
6. duplicate `_process`가 done/polling 상태와 source artifact를 변경하지 않는다.
7. Firestore→SQS outbox/reconciler가 자동 correctedPose와 rotation 모두를 복구한다.
8. PipelineFunction과 RunPod producer의 실제 SQS send 권한이 검증된다.
9. queue visibility와 redrive가 Lambda 공식 권고를 만족한다.
10. actual urllib opener가 301/302/303/307/308을 전부 거부하는 integration test가 있다.
11. 200MB rotation은 메모리 전체 적재 없이 streaming transfer되고 peak RSS가 검증된다.
12. HMAC key rotation 후에도 기존 pair 삭제가 가능하며 retention 일수가 숫자로 고정된다.
13. privacy option B를 선택해도 실제 배포 runtime에서 실행 가능한 anonymizer가 있다.
14. display/training threshold가 복수 fixture calibration 결과로 결정된다.
15. 31-09→31-10 직렬 DAG와 31-12 live mutation checkpoint가 반영된다.
16. 마지막으로 31-12의 correctedPose/rotation 실 E2E 두 개가 기존 계획대로 모두 PASS해야 한다.

---

## 9. 최종 결론

2차 개정은 1차 계획보다 훨씬 안전하고 정직하다. 특히 거짓 3D 제거, canonical key 재서명, delayed SQS continuation, before/after+pose gate, 실 E2E 완료 조건은 유지할 가치가 높다.

하지만 현재 계획의 핵심 자동 교정 경로에는 아직 **무엇을 고칠지(target provenance)**와 **유료 작업을 어떻게 한 번만 만들고 반드시 회수할지(crash-safe journal)**가 빠져 있다. 여기에 replay 시 완료 상태를 pending으로 되돌리는 enqueue 순서까지 겹친다. 이 세 문제는 구현 중의 작은 보정으로 맡길 성격이 아니라 데이터/상태 계약을 먼저 바꿔야 하는 blocker다.

**판정: BLOCK / REPLAN REQUIRED.**  
권장 수정 범위는 전면 재작성은 아니다. `31-02/03/05/09/10`을 중심으로 target 계약, job state, outbox/IAM, DAG를 재조정하고, `31-01/07/12`에 calibration·key rotation·live mutation checkpoint를 보강하면 된다.
