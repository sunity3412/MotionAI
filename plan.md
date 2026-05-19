# plan.md — Sunity AI Coach 작업 현황

> 매 Claude Code 세션 시작 시 반드시 읽을 것.
> 작업 완료/전환 시 반드시 업데이트할 것.

---

## 현재 단계

**Phase 1 — MVP 개발 (파일럿용)**
목표: 정은지 선수에게 시연 가능한 수준의 앱 완성

---

## 완료된 것

```
✅ CLAUDE.md 작성 (루트 + 서브 디렉터리)
✅ design.md 작성 (피그마 기반)
✅ 기술 스택 결정
✅ 파일럿 목표 및 분석 모드 확정 (Mode 1 + Mode 3)
✅ 프로젝트 폴더 구조 설계
✅ GitHub 레포 연결 (github.com/sunity3412/MotionAI)
✅ Expo 프로젝트 초기화 (app/ — Expo SDK 54, TS, expo-router)
   - app.json: Sunity AI Coach / com.sunity.aicoach / 라이트
   - src/app 라우트(인트로 + 바텀탭 4) + src/theme 토큰(design.md)
✅ Firebase 연결 (#2) — 프로젝트 sunity-ai-coach
   - firebase@12 + async-storage / src/lib/firebase.ts (Firestore + 익명 Auth + RN 영속성)
   - .env / .env.example / scripts/verify-firebase.mjs (검증 통과: 익명로그인+Firestore RW)
   - Firestore 보안 규칙 배포 (firestore.rules — deny-by-default, users/{uid} 본인만)
     firebase.json/.firebaserc (firebase-tools CLI, 계정 sunity3412@gmail.com)
✅ 온보딩 #3 (파일럿 최소 게스트 진입)
   - src/app/index.tsx: 브랜드 그라디언트 인트로 + "게스트로 시작하기"
   - signInAnonymously → /(tabs), 영속 세션 시 자동 진입(인트로 스킵)
   - expo-linear-gradient 설치 / 번들 스모크 테스트 통과
   - (회원가입/로그인/레벨/플랜은 파일럿 범위 밖 — 미구현 의도적)
✅ 영상 소스 선택 #4 (UI + 검증)
   - src/app/(tabs)/analyze.tsx: 즉석 촬영 / 앨범에서 선택
   - expo-image-picker 설치 + app.json 권한 문구(심사 대비)
   - 권한 거부 처리(설정 열기), mp4/mov·100MB 검증, 선택 확인 상태
   - 실제 S3 업로드는 #6~7에서 연결 (지금은 영상 확보까지)
✅ 데이터 계약 확정 (#5 착수 전, A안)
   - docs/contract.md (앱↔백엔드 단일 소스: 흐름·엔드포인트·Firestore·결과 스키마)
   - app/src/types/analysis.ts (TS 타입 + 상태/오류 메시지 매핑)
   - 보안 규칙 격리에 맞춰 users/{uid}/analyses 경로 채택
✅ AI 분석 로딩 #5 (계약 기반, 백엔드 전 시뮬레이션)
   - src/app/analysis/loading.tsx: status 구동 단계 UI(스피너 금지),
     완료/오류(4종) 상태, 브랜드 펄스
   - analyze.tsx "분석 시작하기" → /analysis/loading 연결(mode3)
   - useSimulatedAnalysis 훅 = #6~7서 Firestore onSnapshot로 교체 예정(계약 동일)
✅ 백엔드 Lambda 기본 구조 #6 (AWS SAM — 코드/IaC 스캐폴딩, 배포는 보류)
   - IaC=AWS SAM 결정. backend/ template.yaml(API GW·Lambda·S3·SQS·DLQ·
     로그30일·수명주기30일) + samconfig.toml + README(배포 절차)
   - shared/ Lambda Layer(sunity_shared): models/s3keys/validation/responses/
     auth/firestore_admin/events — contract.md 미러
   - functions/upload-url 완전 구현(검증·analysisId·presigned PUT·Firebase auth)
   - functions/reference-api(GET /reference), functions/pipeline는 stub
     (queued까지 정직 전이 + NotImplementedError, ML은 #7)
   - tests/ 19개 유닛 통과(AWS 불필요), 전 파일 문법 OK
   - backend_CLAUDE.md를 contract.md/SAM 기준으로 정합화(미결 해소)
```

---

## 진행 중

```
(없음 — #6 코드/IaC 완료. 실제 배포는 AWS 계정·CLI 준비 후: backend/README.md)
※ 배포 전 1회: aws configure(ap-northeast-2) + Firebase 서비스계정 키를
   Parameter Store(/sunity/motion/firebase-sa, SecureString) 등록 → sam deploy
```

---

## 다음 할 것 (우선순위 순)

```
1. [x] GitHub 레포 생성 + Expo 프로젝트 초기화
2. [x] Firebase 프로젝트 생성 + 연결 (검증 통과)
3. [x] 온보딩 화면 구현 (파일럿 최소 게스트 진입 — 회원가입류 범위 밖)
4. [x] 영상 소스 선택 화면 (UI+검증, 실제 업로드는 #6~7)
5. [x] AI 분석 로딩 화면 (단계별, 계약 기반 — 백엔드서 실데이터 연결)
6. [x] 백엔드 Lambda 기본 구조 세팅 (SAM 스캐폴딩 — 배포는 계정 준비 후)
7. [ ] pose-extractor 함수 구현 (functions/pipeline stub → ML 채움)
8. [ ] 분석 결과 화면 (Mode 3 — 자기 비교)
9. [ ] 기준 모션 선택 화면
10.[ ] 분석 결과 화면 (Mode 1 — 정은지 비교)
```

---

## MVP 범위 밖 (건드리지 말 것)

```
❌ 결제/RevenueCat 연동
❌ 게이미피케이션 실제 지급 로직
❌ 실시간 카메라 분석
❌ 멀티 종목
❌ 회원가입 강제
```

---

## 플랫폼 전환 기록

| 날짜 | 전환 내용 | 사유 |
|------|----------|------|
| -    | -        | -    |

---

*마지막 업데이트: 2026-05-19 — #6 백엔드 SAM 스캐폴딩 완료(upload-url 완전구현,
 pipeline stub, 유닛 19통과). IaC=AWS SAM 확정. 실제 배포 보류(계정/CLI 필요).
 다음: #7 pose-extractor (pipeline stub → YOLO11·ViTPose·DTW·KISMAM·Cerebras)*
