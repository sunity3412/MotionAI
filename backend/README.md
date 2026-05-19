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

## 배포 (AWS 계정/자격증명 준비된 뒤 — 현재 보류)

> 이 환경엔 AWS CLI/자격증명이 없어 `#6` 단계에서는 **배포하지 않는다**.
> 아래는 계정이 준비된 후 1회 셋업 + 배포 절차.

사전 1회 준비:

1. AWS CLI · SAM CLI 설치, `aws configure` 로 자격증명 등록 (리전 `ap-northeast-2`).
2. Firebase 서비스 계정 키(JSON)를 Parameter Store 에 SecureString 으로 저장
   (코드/.env 하드코딩 금지 — `backend_CLAUDE.md` 보안 원칙):

   ```bash
   aws ssm put-parameter \
     --name /sunity/motion/firebase-sa \
     --type SecureString \
     --value file://service-account.json \
     --region ap-northeast-2
   ```

배포:

```bash
cd backend
sam build
sam deploy            # samconfig.toml 기본값 사용. 첫 배포는 변경셋 확인 후 y
```

배포 후 출력되는 `ApiBaseUrl` 을 앱 `.env` 에 연결한다(다음 단계 작업).

## 다음 단계

- `#7` pose-extractor: `functions/pipeline` 의 stub 를 YOLO11 → ViTPose-S →
  MotionDTW → KISMAM → Cerebras 로 교체 (상태 머신/계약은 유지).
- 앱 연동: `ApiBaseUrl` 환경변수화, 로딩 화면을 시뮬레이션 훅에서
  Firestore `onSnapshot` 구독으로 교체.
