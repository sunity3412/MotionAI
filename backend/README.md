# Sunity Motion AI — 백엔드 (AWS SAM)

기존 `sunity.ai` EC2 와 **완전 분리된** 서버리스 인프라.
세부 규칙은 [`backend_CLAUDE.md`](./backend_CLAUDE.md), 데이터 계약은
[`../docs/contract.md`](../docs/contract.md) 가 단일 진실.

## 구성

```
template.yaml          SAM: API GW(HTTP) · Lambda · S3 · SQS · 로그/수명주기
samconfig.toml         배포 기본값 (리전 ap-northeast-2, 스택 sunity-motion-pilot)
functions/upload-url   POST /upload-url  — presigned PUT URL 발급 (완전 구현)
functions/reference-api GET /reference   — 기준 모션 목록
functions/pipeline     S3→SQS 트리거 분석 (stub — #7 에서 ML 채움)
shared/python/sunity_shared  공통 코드 Lambda Layer (계약 미러)
tests/                 AWS 없이 도는 유닛 테스트
```

앱이 직접 호출하는 HTTP 는 `POST /upload-url`, `GET /reference` **둘뿐**.
분석은 앱이 S3 에 영상을 직접 PUT → S3 이벤트 → SQS → `pipeline` 으로 비동기 진행,
앱은 Firestore `users/{uid}/analyses/{id}` 를 구독해 상태/결과를 받는다.

## 로컬 검증 (AWS 계정 불필요)

```bash
cd backend
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
```

## 배포 (belle 첫 sam deploy 절차)

사전 1회 준비:

1. **AWS CLI** (이미 셋업됨 — `sunity-api` 사용자 키), **SAM CLI** 설치:
   ```bash
   brew install aws-sam-cli
   sam --version    # 1.x.x 나오면 OK
   ```
2. **Firebase 서비스 계정 키를 SSM SecureString 으로 저장** (코드/.env 하드코딩 금지):
   ```bash
   aws ssm put-parameter \
     --name /sunity/motion/firebase-sa \
     --type SecureString \
     --value file://sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json \
     --region ap-northeast-2
   ```

배포:

```bash
cd backend
sam build
sam deploy --guided      # 첫 배포 1회. 이후엔 sam deploy (samconfig 기본값 사용)
```

`--guided` 가 묻는 값:
- Stack Name: `sunity-motion-pilot`
- AWS Region: `ap-northeast-2`
- Parameter Stage: `pilot`
- Parameter VideoBucketName: `sunity-motion-pilot-videos` (기존 버킷 그대로)
- Parameter FirebaseSaParam: `/sunity/motion/firebase-sa`
- **Parameter RunpodAnalyzeUrl**: `https://<pod-id>-8000.proxy.runpod.net/analyze`
- **Parameter RunpodAuthToken**: (RunPod 측 `$RUNPOD_AUTH_TOKEN` 64자)
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Disable rollback: `N`
- Save arguments to configuration file: `Y` (samconfig.toml 갱신)

배포 후 출력되는 `ApiBaseUrl` 을 앱 `.env` 에 연결한다.

## 외부 버킷 노티 설정 (배포 후 1회)

이 SAM 스택은 **`sunity-motion-pilot-videos` 버킷 자체를 만들지 않는다** — belle 가
awscli 로 직접 만들어 reference/ 5 영상을 이미 넣어둔 기존 버킷을 보존하기 위함.
그래서 버킷의 라이프사이클/CORS/Notification 은 별도로 1회 설정.

```bash
# 1) Lifecycle (uploads/ 30일 만료 — 비용 관리)
aws s3api put-bucket-lifecycle-configuration \
  --bucket sunity-motion-pilot-videos \
  --lifecycle-configuration '{"Rules":[{"ID":"expire-raw-uploads-30d","Status":"Enabled","Filter":{"Prefix":"uploads/"},"Expiration":{"Days":30}}]}'

# 2) CORS (앱이 직접 PUT)
aws s3api put-bucket-cors --bucket sunity-motion-pilot-videos --cors-configuration '{
  "CORSRules": [{
    "AllowedMethods": ["PUT"],
    "AllowedOrigins": ["*"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3000
  }]
}'

# 3) S3 → SQS Notification (uploads/* 가 올라오면 분석 큐로)
#    QUEUE_ARN = sam deploy outputs 의 AnalysisQueueUrl 에서 ARN 으로 변환
#    (보통 arn:aws:sqs:ap-northeast-2:<acct>:sunity-motion-pilot-analysis)
QUEUE_ARN="$(aws sqs get-queue-attributes \
  --queue-url <AnalysisQueueUrl> \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)"

aws s3api put-bucket-notification-configuration \
  --bucket sunity-motion-pilot-videos \
  --notification-configuration "{
    \"QueueConfigurations\": [{
      \"QueueArn\": \"$QUEUE_ARN\",
      \"Events\": [\"s3:ObjectCreated:*\"],
      \"Filter\": {\"Key\": {\"FilterRules\": [{\"Name\": \"prefix\", \"Value\": \"uploads/\"}]}}
    }]
  }"
```

설정 후 확인: 앱에서 영상 1개 업로드 → CloudWatch `/aws/lambda/sunity-motion-pilot-pipeline`
로그에 `RunPod 위임 모드 ON` + `/analyze accepted` 가 보여야 정상.

## 다음 단계

- `#7-follow 유닛 4`: 운영 GPU 인프라(RunPod) 가동 — `backend/runpod_inference/README.md`.
- 앱 연동: `ApiBaseUrl` 환경변수화, 로딩 화면을 시뮬레이션 훅에서
  Firestore `onSnapshot` 구독으로 교체.
