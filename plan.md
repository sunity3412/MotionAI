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
✅ 분석 결과 화면 #10 Mode1 (전문가 비교 — 시연 퀄리티 보완)
   - lib/simulatedResult.ts: mode1 전용 점수(전문가 기준 박하게 71/78/65/62),
     mode3 기존 유지(76/84/73/70). 두 모드 동시 시연 시 자연스러움
   - result.tsx 헤더 sub: mode1에서 "정은지 선수 · {동작명} 기준으로 분석했어요"
   - mode1 점수대별 요약 카피 분기(≥75/50~74/<50)
   - mode1 전용 메타 카드(브랜드 틴트 배경, 선수명+레벨 뱃지+동작명+설명)
   - useReferenceMotion(id) 헬퍼 추가(컬렉션 구독 재사용 — 시드 후 description 자동 채워짐)
   - tsc 클린 + iOS 번들 4.35MB 스모크 통과
✅ Mode3 정합성 + 레벨 벤치마크
   - simulationWriter: mode3 저장 전 사용자 이전 mode3 done 검색 →
     없으면 isFirst=true(델타 없음), 있으면 isFirst=false + previousAnalysisId
     + 실 partScores delta 계산. Firestore 컴포짓 인덱스 회피 위해 where(mode)
     만 쓰고 status·정렬은 클라이언트
   - lib/userAnalyses 에 useAnalysisDoc(analysisId) 추가 → 단일 doc onSnapshot
   - result.tsx 가 analysisId 있으면 Firestore 저장 result 사용(권위 있는 소스),
     없을 때만 시뮬 폴백. 저장값과 표시값이 정확히 일치
   - lib/levels.ts: LEVEL_EXPECTED_SCORE(입문 65/중급 78/고급 88 픽스처) +
     levelStanding(score) 헬퍼 → 결과 화면 점수 카드 하단에 3 칩 + 현재 위치
     강조 + "중급(78)까지 N점" 같은 한 줄 요약
✅ 시뮬 종료 시 Firestore done 문서 쓰기 (스캐폴드)
   - lib/simulationWriter.ts saveSimulatedAnalysis(): users/{uid}/analyses 에
     auto-id 로 status='done' 1건. mode1 은 사용자가 고른 referenceMotion*
     덮어쓰기. loading.tsx 가 done 도달 시 1회만 호출(savingRef 가드)
   - 결과: 홈/기록 탭이 빈 상태 → 실데이터로 자동 전환. 시연 end-to-end 동작
   - 백엔드 실 파이프라인 켜지면 이 모듈은 폐기 대상(#7-follow)
✅ 홈/기록/마이 탭 (design.md §6 + IA AC-REC-001/AC-MY-*)
   - lib/userAnalyses.ts: 익명 UID 의 users/{uid}/analyses onSnapshot 구독
     (createdAt desc, doneOnly 옵션). 데이터 소스 격리 — 백엔드 붙어도 동일
   - 홈 (tabs/index): 상단 브랜드 그라디언트 + 흰→#FFF0EE 카드 영역.
     A(최근 분석 카드 → 결과로 라우팅) / B(첫 분석하기 그라디언트 pill)
     자동 분기. 오늘 도전해볼 동작(reference 화면) + 성장 그래프(2건↑ 활성,
     미만은 점선 잠금). 게스트·폴스포츠 고정이라 §6 C/D 상태는 MVP 밖
   - 기록 (tabs/history): 분석 기록 리스트(모드 뱃지·날짜·동작명·점수) +
     클릭 시 /analysis/result 로 분기. 빈 상태 = 분석 시작 CTA
   - 마이 (tabs/profile): 게스트 카드(UID 일부 표시) · 통계(횟수/평균) ·
     정보 리스트(종목/레벨/버전) · MVP 범위 안내
   - ScreenPlaceholder 미사용 → 파일 제거. tsc 클린 + iOS 번들 통과
✅ 계약 확장 — 점수 외 구조화 각도/방향 가이드 (#10-G, 자체 발의)
   - JointScore 옵셔널 필드: currentAngle/targetAngle/deltaDeg(signed)/direction
     ('extend'|'flex'|'raise'|'lower'|'open'|'close'). 회전력·반동 등 동적 큐는
     CoachingTip.detail(LLM 자연어) — 모드별 분기 없음([[coaching-tone-customization]])
   - 백엔드: JointAssessment 슬롯 + assess() 가 user_angles/reference_angles 받으면
     자동 채움. JOINT_DIRECTION_PAIRS 로 joint 종류 + signed delta → direction.
     assemble.build_joints 가 옵셔널 emit. 신규 테스트 2개 추가, backend 49 통과
   - 시뮬: 무릎·고관절·팔꿈치에 폴스포츠 그럴듯한 각도값. 코칭팁 detail 에
     회전 진입·반동 뉘앙스 한 줄(LLM 출력 모양 미리보기)
   - result.tsx: angleGuide() 헬퍼로 코칭팁 카드에 "현재 145° → 기준 168° · 더
     펴주세요" 보조 행, worstJoint 하이라이트도 같은 형태로 enrich
   - 계약(docs/contract.md §4) 단일 진실 동기화. tsc 클린 + iOS 번들 통과
✅ 기준 모션 선택 화면 #9 (앱, IA AC-ANAL-001 + design.md §6)
   - Firestore reference 컬렉션 직접 구독(파일럿 단순화, AWS 배포 불필요).
     lib/referenceMotions.ts 에 데이터 소스 격리 → 나중에 GET /reference 로
     교체 시 이 파일만 변경 (훅 시그니처 고정)
   - 백엔드 경로 정정: REFERENCE_MOTIONS_COLLECTION "reference/motions"
     (2-segment, Firestore invalid) → "reference"/단일 컬렉션. backend 47
     테스트 통과, contract.md / backend_CLAUDE.md 동기화
   - app/analysis/reference.tsx: "비교할 프로 동작을 골라주세요" 헤드라인 +
     탭(기본기/중급/고급) + 카드 리스트 + 빈 상태 + 미선택 시 CTA dim
   - analyze.tsx 영상 확인 단계에 모드 선택 2-카드 추가
     ("프로 동작과 비교" → reference.tsx / "내 기록과 비교" → 기존 mode3)
   - loading→result 까지 referenceMotionId/Name 파라미터 전달, 시뮬에 반영
   - tsc 클린 + iOS 번들 스모크 통과. 시드(정은지 동작 3개) = 별도 작업
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
9. [x] 기준 모션 선택 화면 (Firestore 직접 구독, 시드 별도)
10.[x] 분석 결과 화면 (Mode 1 — 정은지 비교) — 헤더·요약 카피·메타카드·
       시뮬 점수 차별화. 영상 나란히 보기·실데이터는 #7-follow
11.[x] 홈/기록/마이 탭 (게스트·폴스포츠 단일 종목 가정). users/{uid}/analyses
       구독으로 자동 분기. ScreenPlaceholder 제거
12.[ ] 시드: 정은지 동작 3개 메타(기초 1~2 + 중급 1). firebase-tools 인증
       방식 확정 후 (gcloud ADC 또는 토큰 위임). 시연 직전까지 보류 가능
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

*마지막 업데이트: 2026-05-20 — Mode3 자기 비교 흐름 정합성 보강. 첫 분석 시
 isFirst=true(델타 없음, 안내 카피), 두 번째부터 실 delta. 결과 화면이 Firestore
 저장값을 권위 소스로 사용(시뮬은 폴백). 레벨 벤치마크(입문 65/중급 78/고급
 88 픽스처)로 점수 의미 즉시 인지. 데이터 누적되면 실 평균치 교체.
 backend 49 / app tsc / iOS 번들 통과. 다음: 시드(시연 직전),
 #7-follow(AWS 환경 준비 후) 대기.*
