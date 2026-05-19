# /backend/CLAUDE.md — 백엔드 (AWS Lambda)

---

## 구조

```
/backend
  /functions
    /video-validator      → 영상 형식/용량 검증
    /pose-extractor       → YOLO11 + ViTPose-S
    /motion-comparator    → FastDTW + 점수 계산
    /reference-manager    → 기준 모션 등록/조회 (관리자)
    /feedback-generator   → 코칭 팁 생성 (Cerebras)
  /shared
    /models               → Firestore 데이터 모델
    /utils
```

## 핵심 엔드포인트

```
POST /analyze              → 수강생 영상 분석
POST /admin/reference      → 기준 모션 등록 (관리자 전용)
GET  /reference            → 기준 모션 목록 조회
GET  /history/{userId}     → 분석 기록 조회
```

## Firestore 컬렉션

```
users/{uid}                → 사용자 프로필, 플랜 정보
analyses/{analysisId}      → 분석 결과, 점수, 키포인트
reference_motions/{id}     → 기준 모션 데이터 (정은지 선수)
```

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
