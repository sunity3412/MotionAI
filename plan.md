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
✅ 기준 모션 카탈로그 정합 — 정은지 실모션 5개 + 콤보 부분점수
   - docs/reference-motions.md v5(정은지 실영상 5개 분석)를 단일 진실로
     앱 타입·계약·시드·백엔드 전부 정합. 기존 시드 3개(가짜 픽스처)는 폐기
   - analysis.ts: ReferenceMotion 에 entryType/entryDescription/clipRange/
     checkpoints/videoUrl/sharedBaseMotionId/baseUntilS 추가. EntryType/
     ClipRange/Checkpoint 타입. Mode1Comparison.segmentScores 옵셔널
   - contract.md §3 ReferenceMotion 스키마 + §4 SegmentScores 동기화
   - seed-reference-motions.mjs: 발레리나/프론트훅/플랭크/인버트버터플라이/
     제미니에이샤 5개 실데이터 (clipRange·checkpoints weight합 1.0)
   - 콤보 부분점수: plank-spin → invert-butterfly-combo(baseUntil 6s)
     → gemini-ayesha-combo(baseUntil 18s) 트리. 콤보 분석 시 베이스/확장
     구간 점수를 분리 평가 → 학생이 어느 단계에서 막혔는지 가시화
   - 백엔드 segments.py: DTW 경로를 baseUntilS 비율로 베이스/확장 분리 →
     각 KISMAM 점수. pipeline mode1 통합. 신규 테스트 7개, backend 56 통과
   - 시뮬/결과화면: simulationWriter 가 콤보면 segmentScores 채움,
     result.tsx 에 "구간별 점수" 카드 + 학습 경로 힌트
   - tsc 클린 + iOS 번들 4.39MB 스모크 통과
   - ⚠ checkpoint 가중치·peak·자유 다리 좌우는 추정 — MVP 시연 후 정은지
     선수와 분석 결과 함께 보며 일괄 수정 (reference-motions.md §6·§7)
```

---

## 진행 중

```
#7-follow — ML 하이브리드 파이프라인 (2026-05-22)
  배경: ViTPose(2D)는 폴 폐색·접힌 인버트에 천장 확정 → NLF(3D HMR) 백본
    채택. docs/research/pole-sports-motion-analysis-techniques.md 가 정답
    아키텍처. ML 추론은 GPU 필요 — "Lambda CPU 컨테이너" 계획 폐기, Lambda
    는 오케스트레이션만.

  구축 완료 (유닛 1~3, CPU 유닛테스트 70개 통과):
    유닛 1 — NlfPoseEstimator (pose_estimator.py): YOLO11 박스 → NLF
      estimate_poses_batched 로 17 COCO joint 3D + 불확실도. SMPL J_template
      에서 COCO-17 canonical 점 재배열해 질의. YoloVitPoseEstimator(2D) 폐기.
    유닛 2 — 분석 코어 2D→3D: compute_joint_angles 가 3D 좌표에서 관절각
      계산(투영 왜곡 자유), joint_uncertainty 추가. motiondtw/kismam/
      selfmotion/segments/assemble 는 각도 스칼라 기반이라 무변경.
    유닛 3 — temporal.py: NLF 불확실도 상대 이상치로 폐색 프레임 판정 →
      인접 신뢰 프레임 보간 + 신뢰도 가중 스무딩. 보정 상수 없음.
    파이프라인(functions/pipeline/app.py)을 3D 흐름으로 배선.

  GPU 검증 완료 (2026-05-22, RunPod RTX 3090):
    verify_nlf_pipeline.py 를 폭스탑(ref-invert-butterfly-combo) 영상에
    end-to-end 실행 — 284프레임. NLF 가 GPU 에서 3D 좌표를 NaN/inf 0 개로
    산출(CPU 는 전부 NaN — 예측대로). 3D 관절각 (284,8) NaN 0. 시간축
    폐색 보간이 관절별 7~11 프레임을 폐색 판정해 보간(평균 5.71° 보정).
    특징벡터 (284,24)까지 통과. 유닛 1~3 실증 완료.

  남은 것:
    - 유닛 4 (이번 범위 밖, 후속): 운영 GPU 추론 환경 분리. 지금은
      interfaces 어댑터 seam 만 유지.
    - mode1 기준 모션 angles 등록: app.py 가 reference doc 의 angles 를
      읽음 — 정은지 영상을 같은 파이프라인에 1회 통과시켜 저장하는 별도 작업.

  검증 자산: verify_nlf_pipeline.py(신규 end-to-end)·verify_nlf_overlay.py·
    _nlf_smoke.py, overlay_*_nlf/, backend/.venv-ml(Python 3.13). NLF 모델
    = backend/scripts/nlf_l_multi.torchscript.
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
7. [~] pose-extractor — 코어/오케스트레이션/3D 어댑터(NLF) 완료.
       GPU 검증·운영 인프라(유닛 4)는 #7-follow 남음
8. [x] 분석 결과 화면 (Mode 3 — 자기 비교) — 시뮬 데이터, 백엔드 연결은 #7-follow
9. [x] 기준 모션 선택 화면 (Firestore 직접 구독, 시드 별도)
10.[x] 분석 결과 화면 (Mode 1 — 정은지 비교) — 헤더·요약 카피·메타카드·
       시뮬 점수 차별화. 영상 나란히 보기·실데이터는 #7-follow
11.[x] 홈/기록/마이 탭 (게스트·폴스포츠 단일 종목 가정). users/{uid}/analyses
       구독으로 자동 분기. ScreenPlaceholder 제거
12.[x] 시드: 정은지 실모션 5개로 교체 (발레리나/프론트훅/플랭크/인버트버터
       플라이/제미니에이샤) + 콤보 부분점수까지 — 아래 완료 블록 참조.
       기존 가짜 3개(인사이드레그행/기본그립/파이어맨스핀)는 폐기
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

*마지막 업데이트: 2026-05-21 (이어서) — 시연 품질 보강:
 - Firestore 시드 실행 완료 (정은지 실모션 5개 reference 컬렉션 반영,
   가짜 3개 삭제). 앱 홈/기준모션 화면에서 5개 정상 노출 확인
 - 옥타곤 점수 위젯: 외곽선 → 게이지 (회색 트랙 + 브랜드 그라디언트 진행)
 - 분석 기록 버그 수정: userAnalyses.normalize 가 fileName 빈 문자열
   문서를 !fileName 으로 전부 걸러내 홈/기록이 비던 문제 (fileName===null)
 - firebase.ts: initializeAuth globalThis 캐시 (already-initialized 경고 방지)
 - 모션 선택 화면 뒤로가기 버튼 추가
 - 결과 화면 동작 비교: 골격/각도 목업 제거 → 자리표시만. #7-follow 실영상
   없이는 공허 — 구조만 열어둠 (영상+골격 오버레이는 #7-follow)
 - 홈 성장 그래프: 막대 → react-native-svg 라인차트 (점수 추이)
 - 분석 로딩 화면: Figma(1:429/436/445)대로 재구성 — 글로우 그라디언트 링
   (안에 텍스트) + 단계 한 줄 + 오류/완료 웨이브 그라디언트

 남은 외부 작업(belle, 자격증명 필요):
  - 영상 5개 S3 업로드 (로컬 작업본은 구명칭, S3 키는 신명칭으로 매핑):
     aws s3 cp "정은지님 영상/ref-ballerina-spin.mp4"         s3://sunity-motion-pilot-videos/reference/ref-sideway-spin.mp4
     aws s3 cp "정은지님 영상/ref-front-hook-spin.mp4"        s3://sunity-motion-pilot-videos/reference/ref-climb.mp4
     aws s3 cp "정은지님 영상/ref-plank-spin.mp4"             s3://sunity-motion-pilot-videos/reference/ref-invert.mp4
     aws s3 cp "정은지님 영상/ref-invert-butterfly-combo.mp4" s3://sunity-motion-pilot-videos/reference/ref-foxtop.mp4
     aws s3 cp "정은지님 영상/ref-gemini-to-ayesha-combo.mp4" s3://sunity-motion-pilot-videos/reference/ref-foxtop-split.mp4
  - #7-follow (AWS+ML): aws 계정·ViTPose/YOLO 가중치·Cerebras 키

 다음 후보: 1. #7-follow (§8 실증 본체)  2. TestFlight 빌드 (EAS)

*2026-05-21 — 기준 모션 카탈로그 정합:
 정은지 실모션 5개(발레리나/프론트훅/플랭크/인버트버터플라이/제미니에이샤) +
 콤보 부분점수(베이스/확장 구간 분리). 타입·계약·시드·백엔드·UI 전부 동기화.

*2026-05-20 — 시드 시각 검증 + 홈 외관 보강.

 [홈] Figma 1:719 기준 6개 디테일 중 5개 반영:
  ✅ 프로필 아이콘 (상단 흰 반투명 동그라미)
  ✅ NEW 공지 배너 (rounded pill + NEW 배지 + 최근 모션명)
  ✅ 옥타곤 점수 위젯 (components/OctagonScore — react-native-svg Polygon)
  ✅ "전체보기 ›" 링크 (reference 화면으로 이동)
  ✅ 동작 컨텍스트 카피 ("중급 도전 추천" / "입문 기본기" / "고급 새로 추가됨")
     + 회색 썸네일 박스 + Figma 정렬(고급→중급→기본기)
  🟡 성장 그래프 라인차트(victory-native 도입) — 별도 턴

 [버그 픽스] 홈 챌린지 카드 누를 때 reference 화면 항상 기본기 탭으로 들어가던 문제
   → motionId params 전달 + reference 화면에서 해당 level 탭으로 자동 점프 + 미리 선택

 [design.md 정정]
  - §5-5: 점수 위젯을 원형 → 옥타곤(정팔각형 외곽선)으로 정정
  - §10: 분석 로딩 화면(Figma 1:429/436/445)은 다크 + 그라디언트 링이 최신 결정 (라이트 테마 단독 예외)

 [발견] Figma의 "AI분석-결과1/2/3" 노드는 실제로는 분석 로딩 화면의 단계별
   변형(✓ 추출 완료 체크 등). 진짜 결과 화면은 여전히 Figma에 없음(자체 설계).

 다음 후보 (우선순위):
  1. 결과 화면 영상 비교 UI 보강 (사용자 통찰 — 시연 임팩트 핵심)
  2. 분석 로딩 화면 다크 + 그라디언트 링 + 이름 인터폴 카피
  3. 성장 그래프 라인차트 (victory-native)
  4. EAS Build/TestFlight (외부 준비 — Apple Developer 계정)
  5. #7-follow (AWS+ML 모델 어댑터) — 외부 준비*

*2026-05-22 — #7-follow ML 검증·재설계 (위 "진행 중" #7-follow 블록 참조):
 - Phase 1(ML 어댑터 3개) 커밋 e1dca17 후 Phase 2(keypoint 검증) 진행.
 - ViTPose(2D) 폴 폐색·접힌 인버트 천장 확정. NLF(3D HMR)는 CPU 에서 동작은
   하나 GPU 전제 모델이라 불안정 — 3D 검증은 GPU 환경에서 마무리 필요.
 - belle research 문서(docs/research/)가 정답 아키텍처. ML 추론 GPU 필수.
 - 결정: 정식 파이프라인 먼저. 개발 GPU = RunPod(RTX 4090).
 - belle action item: RunPod 계정 생성 + 크레딧 등록.

*2026-05-22 (이어서) — #7-follow 하이브리드 파이프라인 유닛 1~3 구축:
 - NLF torchscript API 직접 확인 → NlfPoseEstimator 작성. SMPL J_template
   에서 COCO-17 canonical 점 재배열 → get_weights_for_canonical_points →
   estimate_poses_batched. 구조는 CPU 로 검증(출력 형상·키), 수치는 GPU 필요.
 - 분석 코어 2D→3D 전환(compute_joint_angles/joint_uncertainty). 코어 나머지
   (motiondtw/kismam/selfmotion/segments/assemble)는 각도 스칼라 기반 무변경.
 - temporal.py — 불확실도 상대 이상치 기반 시간축 폐색 보간(보정 상수 없음).
 - pipeline/app.py 3D 배선. 백엔드 유닛테스트 70개 통과(2D→3D 테스트 갱신).
 - 폐기: YoloVitPoseEstimator(2D)·verify_pose_overlay.py·interfaces 의
   NotImplemented* stub. transformers(ViTPose) 의존성 제거.
 - belle action item: RunPod Pod 띄워 verify_nlf_pipeline.py 로 정은지 5영상
   GPU 검증 (폭스탑·폭스탑스플릿의 폐색 보간 동작 확인).

*2026-05-22 (이어서) — 기준 모션 5개 명칭 정정 (정은지 선수 확정):
 - 발레리나 스핀→사이드웨이 스핀, 프론트 훅 스핀→클라임, 플랭크 스핀→인버트,
   인버트 버터플라이 콤보→폭스탑, 제미니 투 에이샤 콤보→폭스탑스플릿.
   브라우저 검증 완료 (Foxtop Split 등 스피닝 폴 동작 용어로 실재).
 - '연속 동작=하나의 기술' — 콤보 용어 제거. 베이스/확장 구간 점수 구조는
   유지(한 기술 안 단계별 점수). 난이도 불변. motionId·S3 키도 신명칭.
 - 갱신: reference-motions.md(단일 출처)·seed 스크립트·contract·app 타입·
   simulatedResult·backend segments 문서·테스트. 백엔드 70개 통과.
 - belle action item:
   1) 정은지 영상 5개 S3 업로드 — 위 "남은 외부 작업"의 신 S3 키 명령 사용.
   2) cd app && npm run seed:reference — 구 motionId 5개 삭제 + 신 5개 등록.

*2026-05-22 (이어서) — #7-follow 유닛 1~3 GPU 검증 완료 + 시드 반영:
 - Firestore 재시드 실행 완료 — reference 컬렉션이 신 5개(사이드웨이/클라임/
   인버트/폭스탑/폭스탑스플릿)로 교체, 구 5개 삭제 확인.
 - RunPod RTX 3090 에서 verify_nlf_pipeline.py 를 폭스탑 영상에 end-to-end
   실행 → 통과. NLF GPU 3D 좌표 NaN 0, 시간축 폐색 보간 관절별 7~11프레임
   판정·보간, 특징벡터까지. 유닛 1~3 실증 완료(위 "진행 중" 블록 참조).
 - RunPod 메모: CUDA_VISIBLE_DEVICES 가 빈 문자열로 와서 =0 으로 덮어야
   CUDA 동작. 첫 Pod 은 불량(GPU 연산 불가)이라 폐기·재배포함. NLF 모델은
   GitHub 릴리스(v0.3.2)에서 Pod 이 직접 받는 게 belle 회선 업로드보다 안정.
 - 남은 것: 유닛 4(운영 GPU 인프라), mode1 기준 angles 등록, S3 영상 업로드.
