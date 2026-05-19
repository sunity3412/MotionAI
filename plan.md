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
🟡 #7 분석 알고리즘 코어 (모델 무관·검증 완료, 모델 어댑터는 #7-follow)
   - analysis/: skeleton(17kp·관절각·상체코어하체) features(F=[Θ,αΘ̇,βΘ̈])
     motiondtw(2단계 밴디드 DTW) kismam(Z-score 가우시안 0~100·Top-3)
     selfmotion(Mode3 좌우대칭) assemble(contract AnalysisResult 조립)
     interfaces(FrameExtractor/PoseEstimator/CoachWriter 프로토콜+stub)
   - functions/pipeline: 진짜 오케스트레이션(상태머신·mode1/3 분기·
     no_human/server_error 매핑). 모델 미구현은 NotImplemented로 가시화
   - tests/ 총 47개 통과(AWS·모델 불필요)
✅ 분석 결과 화면 #8 Mode3 (design.md §8 + ia AC-RES-001, 자체설계)
   - react-native-svg 설치(15.12.1). components/ScoreGauge(원호 게이지+등급A~D)
   - app/analysis/result.tsx: 점수개요·세부점수(상체/코어/하체+델타)·
     동작비교(영상 플레이스홀더+최저관절 하이라이트)·코칭팁 3카드
   - lib/simulatedResult.ts(계약 AnalysisResult 픽스처, #7-follow서 교체)
   - loading.tsx done → result로 router.replace(mode/name/analysisId) 연결
   - 흰 배경·토큰만·이모지/스피너 없음. tsc 클린 + iOS 번들 스모크 통과
```

---

## 진행 중

```
#7-follow (AWS 컨테이너·모델 가중치·Cerebras 키 준비 후 — 여기서 검증 불가):
  - PoseEstimator: YOLO11(인체)→ViTPose-S(17점). 미감지 시 NoHumanError
  - FrameExtractor: ffmpeg 프레임 추출
  - CoachWriter: Cerebras LLM (현재 폴백 = 실제 편차값 기반 문장, 위조 아님)
  - template.yaml: zip→Lambda 컨테이너(ECR) 패키징 전환 + 모델 캐싱
  → 교체 지점은 functions/pipeline/app.py 상단 3개 상수만 (코어 불변)

배포 전 1회(공통): aws configure(ap-northeast-2) + Firebase 서비스계정 키를
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
7. [~] pose-extractor — 알고리즘 코어/오케스트레이션 완료,
       모델 어댑터(YOLO/ViTPose/Cerebras)+컨테이너는 #7-follow(계정/가중치)
8. [x] 분석 결과 화면 (Mode 3 — 자기 비교) — 시뮬 데이터, 백엔드 연결은 #7-follow
9. [ ] 기준 모션 선택 화면 (GET /reference — reference-api 이미 구현)
10.[ ] 분석 결과 화면 (Mode 1 — 정은지 비교) — result.tsx 모드분기 재사용
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

*마지막 업데이트: 2026-05-19 — #8 분석 결과 화면(Mode3) 완료. ScoreGauge
 (react-native-svg)+세부점수+코칭팁, 시뮬 데이터(계약 동일), loading→result
 연결. tsc 클린+iOS 번들 스모크 통과. 다음: #9 기준 모션 선택 화면(앱,
 reference-api 계약 확정) 또는 #7-follow(배포 환경 준비 시)*
