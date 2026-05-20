# /backend/CLAUDE.md — 백엔드 (AWS Lambda)

---

## IaC / 배포 도구 — AWS SAM (결정 완료)

```
IaC        : AWS SAM (template.yaml 단일 소스 + samconfig.toml)
리전        : ap-northeast-2 (서울, 기존 플랫폼과 동일 리전·별도 스택)
런타임      : python3.12 (Lambda 지원 런타임. 로컬 3.14는 배포 대상 아님)
배포        : sam build && sam deploy  (AWS 계정/자격증명 준비 후 1커맨드)
로컬 테스트 : sam local invoke / pytest (AWS 없이 검증)
```

> ⚠️ sunity_aws_guide.md 는 기존 플랫폼(EC2) 운영 가이드. Motion AI 운영에
> 필요하면 본 문서·SAM 템플릿 기준으로 수정·확장 가능(사용자 승인됨).

## 구조 (SAM)

```
/backend
  template.yaml            → SAM: API GW, Lambda, S3, SQS, 권한, 수명주기
  samconfig.toml           → 배포 파라미터(리전/스택명/버킷)
  README.md                → 계정 준비 후 배포 절차(초보자용)
  /functions
    /upload-url            → POST /upload-url (앱 직접 호출, 완전 구현)
    /pipeline              → S3 트리거→SQS→분석 (stub, #7에서 ML 채움)
    /reference-api         → GET /reference (기준 모션 목록)
  /shared                  → Lambda Layer (공통 코드)
    /models                → Firestore 문서 모양 (contract.md 미러)
    /utils                 → s3 키, 응답 포맷, 입력검증, auth, firestore admin
  /tests                   → AWS 없이 도는 유닛 테스트
```

## 핵심 엔드포인트 (contract.md 기준 — 단일 진실)

앱이 직접 호출하는 HTTP 엔드포인트는 2개뿐. 분석 트리거는 S3 이벤트.

```
POST /upload-url   앱 → S3 presigned PUT URL 발급 (인증: Firebase Auth UID, 익명 포함)
GET  /reference    앱 → 기준 모션(정은지) 목록 (기준 모션 선택 화면 #9)
```

분석 실행/기록은 엔드포인트가 아님:
```
분석 트리거 : 앱이 호출하지 않음. S3 업로드 완료 이벤트 → SQS → pipeline Lambda
분석 진행/결과: 앱이 Firestore users/{uid}/analyses/{id} 를 onSnapshot 구독
분석 기록   : 앱이 users/{uid}/analyses 를 직접 쿼리 (GET /history 없음)
```

> backend 구버전의 `POST /analyze`·`GET /history/{userId}` 는 위로 대체됨(계약 §2).
> 기준 모션 등록 `POST /admin/reference` 는 관리자/ML 경로(ml_CLAUDE.md, 정은지
> 촬영 시) — 앱 범위 밖. MVP 파일럿에선 콘솔/스크립트 등록도 허용.

## Firestore 컬렉션 (배포된 보안 규칙·contract.md 와 일치)

```
users/{uid}                       사용자 프로필/플랜 (앱 본인만 RW)
users/{uid}/analyses/{analysisId} 분석 진행·결과 (앱: uploading 까지 생성,
                                  이후 status/result/error 는 백엔드 Admin SDK)
reference/{motionId}              기준 모션(정은지) — 앱 읽기 전용, 쓰기 백엔드/콘솔
```

> 경로 근거: firestore.rules(users/{uid} 격리, reference/** 읽기전용),
> docs/contract.md §3. 구버전 표기(`analyses/{id}`, `reference_motions/{id}`)는
> 폐기 — 이 문서가 갱신본.

## 보안

```
- /admin/* 엔드포인트: Firebase Admin SDK 토큰 필수
- 사용자 분석: Firebase Auth UID 검증
- S3 업로드: Presigned URL (직접 업로드, Lambda 경유 없음)
```

## 기존 플랫폼과 분리 운영 (필수)

```
서니티에는 이미 운영 중인 플랫폼이 있음:
  도메인     : sunity.ai
  EC2        : i-0de9190eb75eec460 (t3.medium, ap-northeast-2)
  스택       : Next.js (3000) + Spring Boot (12100) + nginx
  OS         : Ubuntu 22.04

Motion AI(이 앱)는 반드시 별도 인프라로 분리:
  → 영상 업로드/AI 분석은 용량·처리 시간이 크므로 기존 EC2에 얹지 말 것
  → 별도 Lambda + S3 + SQS 구조로 완전 분리
```

## AWS 아키텍처

```
[앱] → API Gateway → Lambda (upload-url 발급)
[앱] → S3 직접 PUT (Presigned URL)
S3 이벤트 → SQS 큐 → Lambda (분석 파이프라인)
Lambda → Firestore 저장 → 앱에 결과 전달
영상 배포 → CloudFront (S3 앞단)
```

## 핵심 AWS 서비스

```
S3              : 영상 원본 + 분석 결과 저장
SQS             : 분석 요청 비동기 큐 (Lambda 직접 트리거 대신)
CloudFront      : S3 영상/이미지 CDN 배포
CloudWatch      : Lambda 로그, 에러 알림
Parameter Store : API 키, DB 비밀값 관리 (.env 하드코딩 금지)
API Gateway     : REST 엔드포인트
Lambda          : 분석 파이프라인 실행 (타임아웃 15분)
```

## 파이프라인 오케스트레이션

```
AWS Step Functions (Phase 2 확장 시):
  Step 1: S3에서 영상 로드
  Step 2: YOLO11 인체 감지
  Step 3: ViTPose-S 관절 추출
  Step 4: MotionDTW 비교
  Step 5: KISMAM 점수 계산
  Step 6: Cerebras 피드백 생성
  Step 7: Firestore 저장

MVP: Lambda 단일 함수로 시작, 타임아웃 15분 설정
```

## 비용 관리 원칙

```
S3 lifecycle 정책: 영상 원본 30일 후 자동 삭제 (분석 결과만 장기 보관)
CloudWatch 로그: 보관 기간 30일로 제한
GPU/무거운 처리: 상시 구동 금지 → 작업 요청 시에만 실행
비용 알림: AWS Budgets 설정 필수 (월 예산 초과 시 알림)
```

## 보안 원칙

```
.env 파일 GitHub 업로드 절대 금지
API Key, DB Password → Parameter Store 또는 Secrets Manager 사용
코드에 하드코딩 금지
SSH 22번 포트 → 필요한 IP만 허용
```
