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

## S3 업로드 방식 (중요)

```
Lambda를 통해 영상 직접 수신 금지 (100MB 제한, 타임아웃 위험)
→ Presigned URL 방식 사용

POST /upload-url  → S3 Presigned URL 발급
앱이 S3에 직접 PUT
S3 이벤트 → Lambda 트리거 → 분석 파이프라인 시작
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

## 플랜별 분기

```
Free   : Mode 3만 (자기 비교), 월 3회
Basic  : Mode 1 + Mode 3, 월 10회
Pro    : 무제한 + 상세 피드백
파일럿 : 제한 없음 (결제 로직 비활성화)
```
