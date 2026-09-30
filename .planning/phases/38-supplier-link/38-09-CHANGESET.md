# 38-09 CHANGESET — CFN 변경 요약 · 검증 · 롤백 (belle 검토용)

작성 2026-09-30 (Task 1). **changeset 은 만들기만 했고 실행하지 않았다.** 실행은 belle 승인 뒤 Task 3.

- 스택: `sunity-motion-pilot` (ap-northeast-2), 프로파일 `sunity-motion` (`arn:aws:iam::976369350031:user/sunity-motion`)
- changeset ARN: `arn:aws:cloudformation:ap-northeast-2:976369350031:changeSet/samcli-deploy1790723257/2f51b917-fd95-48bf-8c85-c2eb6f10a096`
- 상태 [확인 `describe-change-set`]: `Status CREATE_COMPLETE` · `ExecutionStatus AVAILABLE`
- 파라미터: `Stage`·`VideoBucketName`·`FirebaseSaParam` = samconfig 값, `RunpodAnalyzeUrl`·`RunpodAuthToken` = 이전 값 유지(samconfig 에 없음 → SAM 이 UsePreviousValue). 두 파라미터는 템플릿 어디서도 참조되지 않는다(pipeline env 는 SSM 동적 참조).

## 0. 배포 전 보존 (읽기 전용, 커밋 `61a255e2` — 이 플랜의 어떤 쓰기보다 앞)

| 보존물 | 위치 | 내용 |
|---|---|---|
| legacy baseline (R10) | `infra/legacy-reference-baseline.json` | `ref-*` 11 doc raw top-level(`anglesSha256`·len·`anglesJointKeys`·`anglesFrames`·`anglesUpdatedAt`·`clipRange`·`isActive`·`updatedAt`·`pointer:activeVersion`·`pointer:pipelineVersion`·docSha256) + `reference/_release`(`pointer:activeCandidate`) + S3 `reference/ref-*.mp4` 11 ETag + 저장 분석 표본 3건(전부 `done`/`mode1`, overallScore 85·100·80). Firestore 읽기 15 [확인] |
| 5함수 설정 (R12) | `infra/lambda-before.json` | CodeSha256·CodeSize·Layers·env **키 이름만**·Memory·Timeout·Runtime·Handler·LastModified·Role + zip sha256 |
| 5함수 코드 zip + layer zip | `/Users/Shared/sunity-motion-rollback/38-09/` | `sunity-motion-pilot-{upload-url,reference,reference-auto-register,pipeline,playback-url}.zip` + `layer-sunity-motion-pilot-shared-{16,20}.zip` (7개) |
| 규칙 원본 (R2·R13) | `infra/firestore-rules-before.rules` (= `git show debb86bf:firestore.rules`) · `infra/firestore-rules-live.rules` (`deploy_firestore_rules.py --current`) | 두 파일 `diff` 차이 0 [확인] — 라이브 release `rulesets/bc005961-…`, updateTime 2026-05-19 |

오프라인 self-diff: `snapshot_reference_baseline.py --diff <baseline> --out /dev/null --offline <baseline>` → `differences: 0`, exit 0 [확인].

## 1. 이번에 한 쓰기 (Task 1 안)

| 쓰기 | 결과 |
|---|---|
| SSM `/sunity/motion/supplier-uids` put (`--no-overwrite`, String) | Version 1, 2026-09-30 07:43:56 KST. 값 = `FDJr…:BELLE` (belle uid 28자 + 코드 `BELLE`; `models.parse_supplier_uids` 형식 통과) [확인] |
| SAM 산출물 업로드 | SAM 관리 버킷 `aws-sam-cli-managed-default-samclisourcebucket-rarbvlc0soco` 에 zip 7개 + 템플릿(changeset 생성에 필요) |
| changeset 생성 | 위 ARN. 실행 안 함 |

`sam validate --lint`: `template.yaml` exit 0 · `template-38-09-deploy.yaml` exit 0 [확인].
`sam build --use-container --skip-pull-image --no-cached -t template-38-09-deploy.yaml`: **exit 0** (`Build Succeeded`) [확인]. 이미지 = 로컬 `public.ecr.aws/sam/build-python3.12:latest-arm64` (2026-07-31 생성). `--skip-pull-image` 없이 돌린 첫 시도는 `Building layer` 직후 20분 멈춰(빌드 컨테이너 0개, sam CPU 0) 중단했고 — 원인은 이미지 pull 대기로 추정 [추정 — `--skip-pull-image` 로 즉시 풀렸다는 것만 확인], 로컬에 있던 같은 이름 이미지로 `--skip-pull-image` 빌드했다. 캐시로 3함수가 옛 산출물을 재사용해 `--no-cached` 로 한 번 더 전부 새로 빌드한 것이 최종본이다.

## 2. 브리지 템플릿으로 배포한다 (예상 밖 — 플랜 전제와 다름)

플랜은 정본 `backend/template.yaml` 로 changeset 을 만든다고 적었다. 그러면 **Phase 31 시각 교정물 스택 전체**(VisualQueue·DLQ·함수 3·알람 8·로그그룹 3 + pipeline `VISUAL_*` env/정책)가 같이 올라가고, 그 파라미터 5개(`VisualInputBucketName`·`Display/TrainingJudgeConfidence`·`Display/TrainingPoseTolDeg`)는 Default 가 없어 값을 지어내야 한다 — 31 H10-05 가 일부러 막아 둔 배포다.

관측 [확인]:
- 라이브 스택에는 Visual 리소스가 0개다(`list-stack-resources` 26개 — `Visual*` 없음).
- 라이브 스택 원본 템플릿(`get-template --template-stage Original`)과 `backend/template-32-16-deploy.yaml`(32-16 브리지, 커밋 `312ec21b`)을 CFN 태그 해석 후 구조 비교 → 차이 0.

그래서 32-16 선례를 그대로 따라 `backend/template-38-09-deploy.yaml` = 32-16 브리지 + Phase 38 델타 5개 로 만들었다. 정본 `template.yaml` 에도 같은 델타를 넣었다(수렴 지점). 두 파일 구조 비교 차이 = Phase 31 리소스·파라미터·pipeline `VISUAL_*` env·visual 정책뿐 [확인].

Phase 38 델타 5개 (두 파일 공통):
1. `ReferenceUploadUrlFunction` — `functions/reference-upload-url/`, Timeout 10, env `BELLE_UID`(SSM 동적 참조 `/sunity/motion/belle-uid`) · `SUPPLIER_UIDS_PARAM=/sunity/motion/supplier-uids`(런타임 읽기 — 정은지 추가 = SSM put 만, 배포 없음), 정책 `s3:PutObject` on `sunity-motion-pilot-videos/reference/*` + `ssm:GetParameter` on `…parameter/sunity/motion/firebase-sa`·`…parameter/sunity/motion/supplier-uids`, HttpApi `POST /reference/upload-url`
2. `ReferenceUploadUrlLogGroup` — `/aws/lambda/sunity-motion-pilot-reference-upload-url`, 30일 (같은 이름 로그그룹이 미리 있지 않음 [확인 `describe-log-groups` 빈 결과])
3. `PipelineFunction` env `POD_EXPECTED_PARAM=/sunity/motion/runpod-pod-expected`
4. `PipelineFunction` 정책 `ssm:GetParameter` on `…parameter/sunity/motion/runpod-pod-expected`
5. 버킷 주석 D-17: `(uploads/ 30일 만료)` → `(해제됨 2026-09-26, Phase 38 D-17 — uploads/ 영구 보관: 수명주기 규칙 없음)`

## 3. changeset 표 [확인 `describe-change-set --include-property-values`]

| # | Action | LogicalResourceId | Type | Replacement | 변경 속성 |
|---|---|---|---|---|---|
| 1 | Add | ReferenceUploadUrlFunction | AWS::Lambda::Function | — | 신규 |
| 2 | Add | ReferenceUploadUrlFunctionRole | AWS::IAM::Role | — | 신규(위 정책 2 Statement) |
| 3 | Add | ReferenceUploadUrlFunctionPostPermission | AWS::Lambda::Permission | — | 신규(HttpApi → 함수 호출 허용) |
| 4 | Add | ReferenceUploadUrlLogGroup | AWS::Logs::LogGroup | — | 신규 30일 |
| 5 | Add | SharedLayer1654f65912 | AWS::Lambda::LayerVersion | — | 새 layer 버전(리포 HEAD `sunity_shared`) |
| 6 | Modify | MotionHttpApi | AWS::ApiGatewayV2::Api | False | `Body` — 경로 4개 → 5개(`/reference/upload-url` 추가). 기존 4 경로 정의 변경 0 [확인 before/after Body 비교] |
| 7 | Modify | PipelineFunctionRole | AWS::IAM::Role | False | `Policies` — `PipelineFunctionRolePolicy3` 추가(`ssm:GetParameter` runpod-pod-expected) |
| 8 | Modify | PipelineFunction | AWS::Lambda::Function | False | `Code` · `Environment` · `Layers` |
| 9 | Modify | UploadUrlFunction | AWS::Lambda::Function | False | `Code` · `Layers` |
| 10 | Modify | ReferenceApiFunction | AWS::Lambda::Function | False | `Code` · `Layers` |
| 11 | Modify | ReferenceAutoRegisterFunction | AWS::Lambda::Function | False | `Code` · `Layers` |
| 12 | Modify | PlaybackUrlFunction | AWS::Lambda::Function | False | `Code` · `Layers` |
| 13 | **Remove** | **SharedLayer4941b5eae7** | AWS::Lambda::LayerVersion | — | **layer `:16` 삭제** (아래 예상 밖 1) |

Add 는 새 함수·역할·권한·로그그룹 + 새 layer 뿐이다. Replacement 가 True 인 항목 0. Memory·Timeout·Runtime·Handler 변경 0 (템플릿 값 = 라이브 값 5함수 모두 일치 [확인 `lambda-before.json` 대조]).

## 4. 예상 밖

1. **layer `:16` 이 CFN 정리 단계에서 지워진다.** `SharedLayer` 는 `RetentionPolicy: Delete` 이고 CFN 이 관리하는 버전은 `:16`(`SharedLayer4941b5eae7`) [확인 `describe-stack-resource`]. 새 버전이 붙으면 `:16` 은 사라져, "옛 layer ARN 으로 되돌리기" 는 그대로는 안 된다. → `:16` zip 을 받아 두었고(`layer-sunity-motion-pilot-shared-16.zip`, sha256 `beab71a3…`), 롤백 절에 **재발행 후 새 번호를 붙이는** 명령을 적었다. `:20`(playback-url, 09-09 손 발행)은 CFN 밖이라 남는다 [추정 — CFN 은 자기가 만든 리소스만 지운다].
2. **`RUNPOD_ANALYZE_URL` 이 changeset 에는 바뀌는 것으로 나온다** — CFN 기억값 `https://6seluxc43awmqi-8000.proxy.runpod.net/analyze` → SSM 현재값 `https://pod-down.invalid/analyze`. 라이브 함수의 실제 값은 이미 `https://pod-down.invalid/analyze` 다(09-25 손 갱신) [확인 `get-function-configuration`]. → 라이브 기준 변화 0. 토큰은 라이브 = SSM (해시 대조, 값 미출력) [확인]. auto-register 의 `BELLE_UID`·`GEMINI_API_KEY`·`GEMINI_A_MODEL` 도 라이브 = SSM [확인].
3. **pipeline Lambda 코드가 07-22 → HEAD 로 크게 뛴다.** 라이브 pipeline `app.py` 는 커밋 `f07b3a5c`(32-16, 07-22) 와 바이트 동일, 5,951줄 [확인 — 히스토리 86 커밋 해시 대조]. HEAD 는 10,913줄, 그 사이 이 파일 커밋 85건(38-07 포함). 연구서의 "pipeline 09-25 손 갱신" 은 코드가 아니라 env 갱신이었다 [확인: 코드 = 07-22 판, env URL = 09-25 값]. Lambda 는 분석을 Pod 에 넘기는 얇은 경로라 채점 코드는 Pod 쪽이 돈다 — 그래도 `lambda_handler` 의 분기(reference 키 · pod 부재 queued · 위임)가 전부 새 코드다.
4. **5함수 모두 제3자 의존성이 다시 풀린다.** requirements 범위(`firebase-admin>=6,<7` 등) 안에서 pip 가 최신을 고른다. upload-url 예: `google-cloud-firestore 2.27.0→2.33.0` · `grpcio 1.81.1→1.84.0` · `cryptography 48.0.1→50.0.1` · `google-api-core 2.31.0→2.40.0` · `protobuf 7.35.1→7.36.2` · `urllib3 2.7.0→2.8.0` (`firebase-admin 6.9.0`·`requests 2.34.2` 는 그대로). layer: `numpy 2.5.1→2.5.3`. 32-16 배포 때도 같은 방식이었다 [추정 — 그때 기록 없음].
5. layer 에 `.DS_Store` 3개가 들어간다(`sunity_shared/`·`analysis/`·루트). 무해 — `:20` 에도 1개 있었다 [확인 zip 목록].

## 5. layer 범위 (리뷰 R12)

SAM 은 `SharedLayer` 를 5함수가 `!Ref` 로 공유하므로 새 버전이 전부에 붙는다. 4개 함수를 옛 layer ARN 리터럴로 고정하는 것은 템플릿 드리프트를 영구화하고, `:16` 은 어차피 이번 배포에서 지워지므로(예상 밖 1) **하지 않는다**. 대신 (i) 함수별로 실제 무엇이 바뀌는지를 zip 내용 비교로 적고 (ii) 배포 뒤 회귀(T3 A-2)와 함수 단위 롤백으로 반경을 닫는다.

zip sha256 은 빌드마다 달라 비교에 못 쓴다 — 라이브 zip 과 `sam build` 산출 디렉터리를 **파일 단위 sha256** 으로 비교했다(`__pycache__` 제외) [확인]:

| 함수 | 자기 코드(`app.py`) | 의존성 파일 변경/추가/삭제 | layer | 코드 변경 |
|---|---|---|---|---|
| upload-url | 동일 | 905 / 246 / 152 | :16 → 새 | 의존성만 |
| reference | 동일 | 905 / 246 / 152 | :16 → 새 | 의존성만 |
| reference-auto-register | 동일 | 926 / 269 / 175 | :16 → 새 | 의존성만 |
| pipeline | **변경**(07-22 → HEAD) | 914 / 218 / 161 | :16 → 새 | 자기 코드 + 의존성 |
| playback-url | 동일 | 680 / 193 / 117 | :20 → 새 | 의존성만 |
| (신규) reference-upload-url | — | — | 새 | 신규 |

layer 내용: `:16` 대비 `sunity_shared` 42 파일 변경 · 22 추가 · 0 삭제 / `:20` 대비 44 변경 · 10 추가 · 0 삭제. 리포 커밋으로는 07-22 이후 `backend/shared/python/sunity_shared` 커밋 159건.

**배포 전 import 스모크 [확인]:** 빌드 산출물 6함수 각각을 Linux arm64 컨테이너(`build-python3.12` 이미지, `--network none`, layer 를 `/opt/python` 에 마운트)에서 `import app` → 6/6 `import ok`, `lambda_handler` 존재. 호출(Firestore·S3) 은 하지 않았다 — 런타임 회귀는 T3 A-2 몫.

## 6. 배포 뒤 상태 (예고 — Pod 은 이 플랜에서 안 켠다)

| 부분 | 이 플랜에서 | 누가 |
|---|---|---|
| Lambda·라우트·IAM (CFN) | 배포 (승인 시) | 38-09 T3 A |
| 버킷 알림 `reference/` · 수명주기 해제 | 적용 (승인 시) | 38-09 T3 B·C |
| Firestore 규칙 | 적용 (승인 + 권한 있을 때) | 38-09 T3 F |
| Pod 코드(38-08 `/register-reference`) | **배포 안 함** — Pod 꺼짐(`runpod-pod-expected = down` [확인]) | 38-14 |

배포 순서 메모(38-08 SUMMARY: Pod → Lambda → 알림)와 달리 Pod 이 빠진다. 그 사이 올라온 등록 영상은 pipeline 이 `pod-expected == down` 을 읽고 doc 을 `queued` 로 두고 메시지를 정상 소비한다(D-20 설계) [추정 — 38-07 코드 기준, 라이브 미관측]. Pod 기동 뒤 `requeue_reference_registrations.py` 로 재개(38-14).

## 7. 롤백

**미실행 상태에서 취소:**
```
aws cloudformation delete-change-set --change-set-name arn:aws:cloudformation:ap-northeast-2:976369350031:changeSet/samcli-deploy1790723257/2f51b917-fd95-48bf-8c85-c2eb6f10a096 --profile sunity-motion
```
SSM `supplier-uids` 도 되돌리려면: `aws ssm delete-parameter --name /sunity/motion/supplier-uids --profile sunity-motion`.

**실행 뒤 문제 시 — 함수 단위(메모리 lambda-code-update 절차):**
```
# 0) layer :16 재발행 (CFN 이 :16 을 지웠으므로 새 번호가 나온다)
L16=$(aws lambda publish-layer-version --layer-name sunity-motion-pilot-shared \
  --zip-file fileb:///Users/Shared/sunity-motion-rollback/38-09/layer-sunity-motion-pilot-shared-16.zip \
  --compatible-runtimes python3.12 --compatible-architectures arm64 \
  --query LayerVersionArn --output text --profile sunity-motion)
L20=arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared:20   # CFN 밖, 남아 있음

# 1) upload-url
aws lambda update-function-configuration --function-name sunity-motion-pilot-upload-url --layers "$L16" --profile sunity-motion
aws lambda update-function-code --function-name sunity-motion-pilot-upload-url --zip-file fileb:///Users/Shared/sunity-motion-rollback/38-09/sunity-motion-pilot-upload-url.zip --profile sunity-motion
# 2) reference
aws lambda update-function-configuration --function-name sunity-motion-pilot-reference --layers "$L16" --profile sunity-motion
aws lambda update-function-code --function-name sunity-motion-pilot-reference --zip-file fileb:///Users/Shared/sunity-motion-rollback/38-09/sunity-motion-pilot-reference.zip --profile sunity-motion
# 3) reference-auto-register
aws lambda update-function-configuration --function-name sunity-motion-pilot-reference-auto-register --layers "$L16" --profile sunity-motion
aws lambda update-function-code --function-name sunity-motion-pilot-reference-auto-register --zip-file fileb:///Users/Shared/sunity-motion-rollback/38-09/sunity-motion-pilot-reference-auto-register.zip --profile sunity-motion
# 4) pipeline (옛 코드는 POD_EXPECTED_PARAM 을 읽지 않아 env 가 남아도 무해)
aws lambda update-function-configuration --function-name sunity-motion-pilot-pipeline --layers "$L16" --profile sunity-motion
aws lambda update-function-code --function-name sunity-motion-pilot-pipeline --zip-file fileb:///Users/Shared/sunity-motion-rollback/38-09/sunity-motion-pilot-pipeline.zip --profile sunity-motion
#    env 까지 지우려면(토큰 값을 문서·셸에 남기지 않는 방식):
#    backend/.venv/bin/python -c "import boto3;l=boto3.client('lambda',region_name='ap-northeast-2');f='sunity-motion-pilot-pipeline';e=l.get_function_configuration(FunctionName=f)['Environment']['Variables'];e.pop('POD_EXPECTED_PARAM',None);l.update_function_configuration(FunctionName=f,Environment={'Variables':e});print('ok')"
# 5) playback-url
aws lambda update-function-configuration --function-name sunity-motion-pilot-playback-url --layers "$L20" --profile sunity-motion
aws lambda update-function-code --function-name sunity-motion-pilot-playback-url --zip-file fileb:///Users/Shared/sunity-motion-rollback/38-09/sunity-motion-pilot-playback-url.zip --profile sunity-motion
```
zip 은 전부 50 MB 미만(31.8~35.3 MB)이라 `--zip-file` 직접 업로드 한도 안이다. 함수 단위 롤백은 CFN 밖 변경이라 드리프트를 남긴다 — 새 함수·라우트는 그대로 두고(무토큰 401 뿐, 부작용 없음) 다음 CFN 배포 때 정리한다.

**버킷 설정(T3 B·C 에서 원본 저장 — 커밋됨):**
```
# 알림 되돌리기 (uploads/ 1항목으로)
aws s3api put-bucket-notification-configuration --bucket sunity-motion-pilot-videos --notification-configuration file://.planning/phases/38-supplier-link/infra/notification-before.json --profile sunity-motion
# 수명주기 되돌리기 (uploads/ 30일 만료 규칙 복원)
aws s3api put-bucket-lifecycle-configuration --bucket sunity-motion-pilot-videos --lifecycle-configuration file://.planning/phases/38-supplier-link/infra/lifecycle-before.json --profile sunity-motion
```
`lifecycle-before.json` 에는 get 응답의 `TransitionDefaultMinimumObjectSize` 키가 같이 들어 있다 — put 이 그 키를 거부하면 `Rules` 만 남긴 사본으로 put 한다 [미확인 — 실행 안 해 봄].

**Firestore 규칙:**
```
FIREBASE_SA_PATH=<리포 루트 SA json> backend/.venv/bin/python backend/scripts/deploy_firestore_rules.py --release --rules .planning/phases/38-supplier-link/infra/firestore-rules-before.rules
```
(스크립트 배포가 막히면 콘솔 규칙 탭에 `infra/firestore-rules-before.rules` 내용을 붙여 넣고 게시.)

## 8. 규칙 — 배포 경로 결정 필요

관측:
- 38-06 에서 `deploy_firestore_rules.py --test` 가 HTTP 403 `firebaserules.rulesets.test`(Admin SA) [확인 38-06].
- 오늘 `--current`(GET release + ruleset) 는 같은 SA 로 성공 [확인].
- `--release`(rulesets create + releases update) 권한 [미확인 — 실행 금지 구간이라 안 불렀다]. `--test` 가 막힌 SA 라 막힐 가능성이 높다 [추정].

선택지 (belle 결정 — 실행기는 IAM 을 스스로 부여하지 않는다):
- (A) belle 이 Google Cloud 콘솔 IAM 에서 Admin SA(`firebase-adminsdk-fbsvc@sunity-ai-coach.iam.gserviceaccount.com` [확인 — SA json `client_email`]) 에 **Firebase Rules Admin**(`roles/firebaserules.admin`) 역할 추가 → T3 F 가 `--test`(12/12) → `--release` → 라이브 probe 를 전부 스크립트로. 장점: 시험(12 케이스)이 배포 전에 돈다, 롤백도 한 줄. 단점: Admin SA 권한이 넓어진다.
- (B) belle 이 Firebase 콘솔 → Firestore → 규칙 탭에 `firestore.rules` 내용을 붙여 넣고 게시 → 실행기가 `--current` 로 게시 내용 = 리포 파일인지 확인 + 라이브 probe. 장점: 권한 변경 0. 단점: `projects:test` 12 케이스 사전 시험을 못 돌린다(콘솔 규칙 플레이그라운드로 대체 가능) — 라이브 probe 5줄이 유일한 검증.
- (C) 규칙만 보류 — CFN 만 배포하고 규칙은 나중에. 이 경우 `reference/**/private/` 가 지금 규칙(`reference/{document=**}` 인증 사용자 전원 읽기)에선 **다른 로그인 사용자에게 읽힌다** [확인 — 라이브 규칙 원문]. 공급자 비공개 doc 이 생기기 전(첫 공급자 업로드 전)에 규칙이 나가야 한다.

## 9. 승인

(Task 2 — belle 응답을 원문 그대로 여기에 적는다.)

belle 응답 (2026-09-30, 오케스트레이터 질문에 대한 답):
- 배포: "승인 — 배포 진행" → **approved** (changeset 실행)
- 규칙: "콘솔에 직접 붙여넣기" → 선택지 **(B)** — belle 이 Firebase 콘솔 규칙 탭에 `firestore.rules` 를 붙여 넣고 게시. 실행기는 IAM 을 부여하지 않고 `--test`·`--release` 를 부르지 않는다.

## 10. 실행 결과 (Task 3, 2026-09-30)

### A. 배포 [확인]
- `execute-change-set` 2026-09-29T23:56:58Z(UTC) → `wait stack-update-complete` exit 0 → 스택 `UPDATE_COMPLETE` (LastUpdatedTime 23:56:59Z). 이벤트: 새 함수·역할·권한·로그그룹·layer `SharedLayer1654f65912` CREATE_COMPLETE, 5함수·`PipelineFunctionRole`·`MotionHttpApi` UPDATE_COMPLETE, 정리 단계에서 `SharedLayer4941b5eae7`(:16) DELETE_COMPLETE. 실패 이벤트 0.
- ① 라우트 (`get-routes --api-id 2rbpecm4d8`): `GET /reference` · `POST /playback-url` · `POST /reference/auto-register` · **`POST /reference/upload-url`** · `POST /upload-url`
- ② pipeline env: `POD_EXPECTED_PARAM=/sunity/motion/runpod-pod-expected` · `RUNPOD_ANALYZE_URL=https://pod-down.invalid/analyze` (배포 전 라이브 값과 같음. 토큰 미출력)
- ③ layer: 6함수(기존 5 + 새 1) 모두 `sunity-motion-pilot-shared:21`, `State Active` · `LastUpdateStatus Successful`. 남은 layer 버전 = 21·20·19·18·17 (:16 삭제됨 — 예상 밖 1 대로)
- ④ 스모크: `POST /reference/upload-url` 본문 `{}` 무토큰 → `HTTP 401` `{"error": {"code": "unauthorized", "message": "인증이 필요합니다."}}`
- 38-10 이월 CORS 줄: `Origin: http://localhost:8082` 로 POST → `HTTP/2 401` + `access-control-allow-origin: *`. preflight `OPTIONS` → `204` + `access-control-allow-origin: *` · `access-control-allow-methods: GET,OPTIONS,POST` · `access-control-allow-headers: authorization,content-type`. (38-10 때의 404 무헤더 → 해소. 브라우저 실측은 38-13)

### A-2. 설정 diff (R12) [확인 `infra/lambda-after.json`]

| 함수 | 필드 | before | after | 예고됐나 |
|---|---|---|---|---|
| upload-url | Layers / CodeSha256 | :16 / `USY2eaYeJg…` | :21 / `5ceFWtQRtQ…` | 예 (의존성만) |
| reference | Layers / CodeSha256 | :16 / `YcoJ3Im2Nc…` | :21 / `rb9kpifr/j…` | 예 (의존성만) |
| reference-auto-register | Layers / CodeSha256 | :16 / `LgCTx++M39…` | :21 / `8Y9X5XCKN8…` | 예 (의존성만) |
| pipeline | Layers / CodeSha256 / EnvKeys | :16 / `8Ew9qbrRYt…` / 4키 | :21 / `RFXSEcgMOr…` / +`POD_EXPECTED_PARAM` | 예 |
| playback-url | Layers / CodeSha256 | :20 / `whIHZBkjC2…` | :21 / `9Y2ahu2W56…` | 예 (의존성만) |
| reference-upload-url (신규) | — | — | :21 · Mem 256 · Timeout 10 · env `BELLE_UID`·`FIREBASE_SA_PARAM`·`SUPPLIER_UIDS_PARAM`·`VIDEO_BUCKET` | 예 |

Memory·Timeout·Runtime·Handler·Role·그 밖의 env 키 변화 0 → 예고 밖 차이 없음.

### A-2. 기존 API 회귀 (R12)
무토큰 [확인]:
- `POST /upload-url` → `401` `error.code=unauthorized`
- `GET /reference` → `401` `error.code=unauthorized`
- `POST /playback-url` → `401` `error.code=unauthorized`

토큰 (Admin SA custom token → `signInWithCustomToken`, uid `regress38`, 토큰 미출력; 스크립트 = scratchpad `regress38.py`, `e2e_app_path.signin_custom` 재사용) [확인, 2회 같은 결과]:
- `POST /upload-url {mode:'mode3', format:'mp4', fileSizeBytes:1000}` → `200` 키 `analysisId · expiresInSec · s3Key · uploadUrl` (PUT 안 함 — 객체 0. 이 함수는 Firestore 에 쓰지 않는다 [확인 코드])
- `POST /playback-url {referenceMotionId:'ref-kip-up'}` → `200` 키 `expiresInSec · playbackUrl`
- **`GET /reference` → `500` `{"message": ...}`(API Gateway 기본 본문) — 함수가 10초 타임아웃**(`Duration: 10000.00 ms · Status: timeout · Max Memory 171 MB`)

**`GET /reference` 500 은 배포 전부터 있던 것이다 — 이번 배포로 깨진 게 아니다.**
관측 [확인 CloudWatch `/aws/lambda/sunity-motion-pilot-reference`, 31일 REPORT 전부]:
| 시각(KST) | Duration | 상태 | 코드 |
|---|---|---|---|
| 08-31 09:30:24 | 10000 ms | timeout | 배포 전(:16 + 옛 zip) |
| 08-31 09:32:02 | 10000 ms | timeout | 배포 전 |
| 08-31 09:32:15 | 10000 ms | timeout | 배포 전 |
| 09-30 08:59:55 | 2 ms | ok (무토큰 401) | 배포 후 |
| 09-30 09:00:28 | 10000 ms | timeout | 배포 후 |
| 09-30 09:01:14 | 10000 ms | timeout | 배포 후 |

- 10초를 채운 호출은 인증을 통과한 호출이다(무토큰 401 경로는 2 ms) [확인].
- 앱은 `GET /reference` 를 부르지 않는다 — 기준 목록은 Firestore `reference` 컬렉션을 `onSnapshot` 으로 직접 읽는다(`app/src/lib/referenceMotions.ts:214`); `app/src/lib/api.ts` 에 이 경로를 부르는 함수가 없다 [확인 grep].
- 그래서 **함수 롤백은 하지 않았다** — 롤백 대상 코드도 같은 타임아웃을 냈고(위 08-31), 롤백은 CFN 밖 드리프트만 남긴다. 플랜 A-2 의 "3 × 200" 중 이 한 줄은 **미충족**으로 남긴다.

진단(승계 전 재검증 대상) [추정]: `list_reference_motions()` 가 `reference` 컬렉션 전체 doc 을 `angles`·`joints3d`·`keypointReport` 등 큰 필드째 읽어 돌려주는데, 256 MB·10초 안에 못 끝나는 것으로 보인다. 컬렉션 크기·응답 크기는 재지 않았다.

### A-3. baseline 재diff (R10) [확인]
```
$ FIREBASE_SA_PATH=… backend/.venv/bin/python backend/scripts/snapshot_reference_baseline.py \
    --diff .planning/phases/38-supplier-link/infra/legacy-reference-baseline.json \
    --out <scratchpad>/baseline-after-deploy.json
differences: 0
exit=0
```
legacy 11 doc raw 필드 · `reference/_release` 포인터 · S3 `reference/ref-*.mp4` ETag 11 · 저장 분석 표본 3건 — 배포 전과 차이 0.

### B. 버킷 알림 (교체-전체, 한 번에 2항목) [확인]
- 원본: `infra/notification-before.json` — 1항목 `Id M2Y1OTFk…` · `uploads/` · 큐 `sunity-motion-pilot-analysis`
- 넣은 설정: `infra/notification-after.json` (원본 항목 그대로 + `reference-supplier-link` · `reference/`)
- `put-bucket-notification-configuration` exit 0 → `get` 결과:
```
M2Y1OTFkZDctN2RiYi00MTFhLTliMDctZWI0OTM1M2JjM2Nl	arn:aws:sqs:ap-northeast-2:976369350031:sunity-motion-pilot-analysis	s3:ObjectCreated:*	uploads/
reference-supplier-link	arn:aws:sqs:ap-northeast-2:976369350031:sunity-motion-pilot-analysis	s3:ObjectCreated:*	reference/
```
- `reference/` 아래 다른 모양 키(평면 `ref-*.mp4`, `_archive/…`, 확정 `v1.*`)는 pipeline 이 경고 로그만 남기고 넘긴다 [확인 코드 — `parse_reference_key` 영숫자 세그먼트 · `parse_upload_key` None → `스킵: 인식 불가 S3 키`; 확정 키 → `확정 키 이벤트 무시`]. 라이브 관측은 아직 없다 [미확인].
- 롤백: §7 명령.

### C. 수명주기 해제 (REQ-38-7 · D-17) [확인]
- 원본: `infra/lifecycle-before.json` — 규칙 1개 `expire-raw-uploads-30d` (`uploads/`, 30일)
- `delete-bucket-lifecycle` exit 0 → `get-bucket-lifecycle-configuration`:
```
aws: [ERROR]: An error occurred (NoSuchLifecycleConfiguration) when calling the GetBucketLifecycleConfiguration operation: The lifecycle configuration does not exist
```
- 롤백: §7 명령.

### D. 문서 [확인]
- `backend/README.md`: 수명주기 put 명령 → "해제됨(D-17)" 주석 + 되돌리기 원본 경로. 알림 명령 → 2항목 판 + "교체-전체 — 항목 하나만 넣으면 다른 접두사 알림이 사라진다" 경고.
- `backend/scripts/intake_clips.py:27`: "30일 뒤 지워진다" → "`uploads/` 도 영구 보관(D-17)".
- `grep -c '30일'` README·intake_clips = 0 · template `uploads/ 30일|30일 만료` = 0.

### E. IAM (읽기 전용 simulate) [확인]
caller `arn:aws:iam::976369350031:user/sunity-motion` (매칭 정책 `AdministratorAccess`):

| Action | Resource | 결과 |
|---|---|---|
| s3:PutObject | `…/uploads/u1/0123…cdef.mp4` | allowed |
| s3:PutObject | `…/reference/u1/0123…cdef/v1.mp4` | allowed |
| s3:PutObject | `…/reference/u1/0123…cdef/upload.mp4` | allowed |
| s3:GetObject | `…/uploads/u1/0123…cdef.mp4` | allowed |
| s3:GetObject | `…/reference/u1/0123…cdef/v1.mp4` | allowed |
| s3:GetObject | `…/reference/u1/0123…cdef/upload.mp4` | allowed |

이 결과는 **로컬 `sunity-motion` 사용자** 기준이다. Pod 이 같은 키를 쓰는지는 [미확인 — 38-14 T2 3-b 가 Pod 에서 `get-caller-identity` 로 대조].

### F. Firestore 규칙 — 선택지 (B) 콘솔 게시 대기
- 리포 `firestore.rules`: 마지막 변경 커밋 `e4c3d16a` (38-06), 작업트리 변경 없음, 51줄, sha256 `b5b63131…48b8` [확인].
- 라이브 `--current`(09-30 Task 3 시점): release `rulesets/bc005961-b1db-4099-85a7-91c4756ecf62`, updateTime 2026-05-19T09:27:24Z — 내용 = `infra/firestore-rules-before.rules` (diff 0) [확인]. 리포 파일과는 다름(아직 안 올림 — 예상대로).
- 실행기는 `--test`·`--release` 를 부르지 않았고 IAM 도 바꾸지 않았다 (belle 선택 B).
- 다음: belle 이 콘솔에서 게시 → 이어받는 실행기가 `--current` 로 라이브 = 리포 확인 + 라이브 probe 5줄.

#### F-2. belle 콘솔 게시 뒤 확인 (2026-09-30)

belle: "게시했어" — Firebase 콘솔 규칙 탭에 리포 `firestore.rules`(38-06 `e4c3d16a`, 51줄)를 붙여 넣고 게시.

**`--current` 대조 [확인]:**
```
$ FIREBASE_SA_PATH=<리포 루트 firebase-sa.json> backend/.venv/bin/python backend/scripts/deploy_firestore_rules.py --current --out <scratchpad>/rules-live-after-publish.rules
current release name=projects/sunity-ai-coach/releases/cloud.firestore rulesetName=projects/sunity-ai-coach/rulesets/18587bf6-155f-43ae-aded-fdafdd7eabda updateTime=2026-09-30T00:58:37.642026Z files=1
saved …/rules-live-after-publish.rules (2263 chars)
$ diff firestore.rules <scratchpad>/rules-live-after-publish.rules   → 출력 없음, exit 0
sha256 둘 다 b5b631319bcc811f0f7891b364cd12bfece56866bdbf32f3aaf2ce11d76448b8
```
- 새 release = `rulesets/18587bf6-155f-43ae-aded-fdafdd7eabda` (이전 `bc005961-…`, 05-19). 라이브 = 리포 **바이트 단위 동일** — 공백 차이도 없음.
- `--test`(projects:test 12 케이스)는 선택지 (B) 라 돌리지 않았다(SA 403, 38-06). 아래 라이브 probe 가 유일한 검증이다.

**라이브 probe [확인]** — scratchpad `rulesprobe38.py`. 클라이언트 요청은 Firestore REST v1 + Firebase ID 토큰(Admin SA custom token → `signInWithCustomToken` 교환, uid `regress38A`·`regress38B`, 토큰 미출력). 규칙은 웹 SDK 와 REST 에 똑같이 적용된다. 임시 doc 은 Admin 으로 만들고 지웠다.

| # | 요청 (클라이언트) | 기대 | 결과 |
|---|---|---|---|
| 1 | A → `reference/_rulesprobe38/private/registration` get (`supplierUid = regress38A`) | ALLOW | HTTP 200 |
| 2 | B → 같은 private doc get | DENY | HTTP 403 `PERMISSION_DENIED` (permission-denied) |
| 3 | B → `reference/_rulesprobe38` (공개 top-level) get | ALLOW | HTTP 200 |
| 4 | B → `users/regress38B/analyses/probe38` create, `selfCheckForReference:'x'` 포함 | DENY | HTTP 403 `PERMISSION_DENIED` (permission-denied) |
| 5 | B → 같은 경로 create, 표식 없음 | ALLOW | HTTP 200 |
| 6 | B → 5 의 doc delete (본인) | ALLOW | HTTP 200 |

`ALL PASS` (6/6).

**정리 [확인]:**
- 시작 전 임시 doc 3개 존재 여부 `[False, False, False]` → 끝난 뒤 `[False, False, False]` (`reference/_rulesprobe38`, 그 `private/registration`, `users/regress38B/analyses/probe38`).
- Firebase Auth 임시 유저 삭제: `regress38A` · `regress38B` · `regress38`(A-2 회귀 때 만든 것) — 3개 모두 `delete_user` 성공.
- Firestore 읽기·쓰기: Admin 읽기 6 · 쓰기 2 · 삭제 3, 클라이언트 요청 6 — Spark 캡 무관.

**규칙 롤백** (필요 시): §7 "Firestore 규칙" 명령 — 또는 콘솔 규칙 탭에 `infra/firestore-rules-before.rules` 내용을 붙여 넣고 게시.
