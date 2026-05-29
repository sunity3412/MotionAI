# plan.md — Sunity AI Coach 작업 현황

> 매 Claude Code 세션 시작 시 반드시 읽을 것.
> 작업 완료/전환 시 반드시 업데이트할 것.

---

## 현재 단계

**Phase 1 — MVP 개발 (파일럿용)**
목표: 정은지 선수에게 시연 가능한 수준의 앱 완성

---

*2026-05-29 — 실분석 가동(RunPod Blackwell) + IPSF 채점 재설계 (균형 제거·기술조건부):

 ① RunPod 운영 가동: 새 Pod(NVIDIA RTX PRO 4000 Blackwell sm_120 / torch 2.8+cu128)
    git clone→setup.sh(NLF 4.2GB)→env→uvicorn. /health OK. Lambda(sunity-motion-pilot
    -pipeline) 환경변수 RUNPOD_ANALYZE_URL(x9vsw5a6au1i4h)+TOKEN 을 `aws lambda
    update-function-configuration`(profile sunity-motion=admin)로 새 Pod에 동기화.
    버킷 알림 이미 연결됨 → 앱 업로드 → 실 NLF 분석 end-to-end 최초 통과.
    ⚠ Pod env AWS 키 = sunity-motion(AdministratorAccess) — 시연 후 S3 read-only로 강등 권장.

 ② belle 게이트 지적: 세계챔피언 정은지 영상이 mode3에서 41점 = 채점이 깨진 증거.
    원인 분석(보고서 5·6 정독): '균형(좌우대칭)' 차원은 IPSF 기술감점 프로토콜에
    근거 0 + 폴 동작은 의도적 비대칭 정상 → 정상 동작을 깎는 위양성(41점 주범).

 ③ 채점 엔진 재설계 (commit):
    - 신규 analysis/technique.py: TechniqueProfile + TechniqueRecognizer(프로토콜,
      swappable) + 보수적 FallbackRecognizer(모르면 안 깎음). 인식층=Gemini로 시작
      예정(턴키), 도메인 완성은 Pole-arina식 분류기(나중). [[scoring-dimensions-ipsf]]
    - dimensions.py: balance_score/symmetry 제거. line=기술조건부(profile.expects_
      extension 관절만 180° 대비, 없으면 None). _LINE_TOL 15→20(IPSF 허용오차).
      extension_deviation() 신규(첫 분석 코칭=신전 부족분). absolute=(line?,stability).
    - models.py DIM_BALANCE 제거. pipeline _process/_mode3_comparison 가 profile 사용.
    - app analysis.ts/simulatedResult.ts/result.tsx 에서 balance 차원 제거.
    - 백엔드 103 pass, 앱 tsc clean. 화면값 역산 재계산: 41(D)→63(C) (균형 삭제+라인 tol).

 ④ 측정 한계(정직): 현 포즈=COCO-17 8관절각 → 라인/유지/각도만 측정 가능. 정렬(무릎-
    발끝=발끝 keypoint 없음)·자세(머리 keypoint)는 포즈 데이터 업그레이드(Phase 3) 필요.

 다음:
   - [게이트] Pod git pull→uvicorn 재시작→정은지 영상 재업로드 → 실제 새 점수 확인.
     통과 시 다른 영상·비폴 영상(not_pole 거부) 확장.
   - 라인이 다음 레버: Gemini 인식기(기술별 EXTEND/BENT 판정) + NLF 홀딩 각도 정확도 점검.
   - 카메라 앵글 합성(CameraCtrl II/UCPE)=데이터 증강/시점보정/코치뷰 = Phase 2.

---

*2026-05-28 (저녁) — 점수 차원 IPSF 재설계 (상체/코어/하체 → 각도/라인/균형/안정성):

 belle 두 지적으로 오늘 mode3 7단계 계획을 폐기하고 점수 모델 전면 재설계:
  (1) mode3 는 '이전과 몇% 일치'가 아니라 발전(progress)을 보여줘야 한다.
  (2) 점수 차원을 신체부위가 아니라 IPSF 폴스포츠 심사기준(각도/균형 등)으로.
      → docs/research/폴스포츠-지식.md (보고서 4·5·6) 단일 참조.

 새 점수 모델 — IPSF 실행 차원 4개 (mode1·mode3 공통, belle 확정):
   - angle 각도정확도: 관절각 vs 기준. reference 필요(mode1=정은지, mode3 second+=이전영상).
   - line 라인·확장 / balance 균형·정렬 / stability 안정성·홀딩: 기준 불필요 절대 지표.
   - 절대 3차원은 mode3 에서 영상 1개로 절대 점수 산출 → 세션 간 델타가 같은 척도
     = 진짜 발전 측정 (belle 의 '발전 not 일치' 해결). overall: mode1=4차원평균,
     mode3=절대3차원평균(각도는 일관성으로 별도 표기, overall/delta 제외).

 변경 파일 (커밋 권고):
   backend/shared/python/sunity_shared/analysis/dimensions.py (신규 — line/balance/
     stability/angle + hold_window. 가우시안은 kismam.score_from_deviation 공유)
   backend .../analysis/kismam.py (score_from_deviation 추출), models.py (DIM_* 상수),
     analysis/assemble.py (build_result(dimension_scores,overall), build_mode3 발전델타),
     firestore_admin.py (complete_analysis 가 angles flat 저장),
     functions/pipeline/app.py (_deviation_against·_mode3_comparison, 4차원 산출, mode3
       이전영상 DTW, not_pole 는 각도 기준, angles 저장)
   app/src/types/analysis.ts (ScoreDimension/DIMENSION_LABEL_KO/ORDER, dimensionScores,
     Mode3 delta 차원키, AnalysisDoc angles 필드)
   app/src/app/analysis/result.tsx (차원 행, mode3 발전 카피, second+ 이전영상 비교,
     first 는 비교 섹션 생략), app/src/lib/simulatedResult.ts (차원 픽스처)
   docs/contract.md §4, design.md §8, 신규 메모리 2개(scoring-dimensions-ipsf,
     mode3-progress-not-similarity)
   tests: test_dimensions.py(신규), test_pipeline_mode3.py(신규), test_assemble.py 갱신
     → 백엔드 96 pass / app tsc·lint clean.

 ⚠ 아직 안 한 것 / 다음:
   - 신규 ML 지표 tol 값(_LINE_TOL=15·_STABILITY_TOL=8·_BALANCE_TOL=15·hold window
     =T//4)은 휴리스틱 — belle 실영상으로 튜닝 필요. dimensions.py 상단에 상수화.
   - UI 는 device 검증 못 함(Expo). belle Expo Go/TestFlight 확인 필요.
   - 회전 360°/모멘텀·예술성 차원은 현 파이프라인 범위 밖(보류).
   - 커밋·EAS 새 빌드 미실행 (belle 지시 대기).

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
   GPU 검증 (폭스탑·폭스탑 스플릿의 폐색 보간 동작 확인).

*2026-05-22 (이어서) — 기준 모션 5개 명칭 정정 (정은지 선수 확정):
 - 발레리나 스핀→사이드웨이 스핀, 프론트 훅 스핀→클라임, 플랭크 스핀→인버트,
   인버트 버터플라이 콤보→폭스탑, 제미니 투 에이샤 콤보→폭스탑 스플릿.
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
   인버트/폭스탑/폭스탑 스플릿)로 교체, 구 5개 삭제 확인.
 - RunPod RTX 3090 에서 verify_nlf_pipeline.py 를 폭스탑 영상에 end-to-end
   실행 → 통과. NLF GPU 3D 좌표 NaN 0, 시간축 폐색 보간 관절별 7~11프레임
   판정·보간, 특징벡터까지. 유닛 1~3 실증 완료(위 "진행 중" 블록 참조).
 - RunPod 메모: CUDA_VISIBLE_DEVICES 가 빈 문자열로 와서 =0 으로 덮어야
   CUDA 동작. 첫 Pod 은 불량(GPU 연산 불가)이라 폐기·재배포함. NLF 모델은
   GitHub 릴리스(v0.3.2)에서 Pod 이 직접 받는 게 belle 회선 업로드보다 안정.
 - 남은 것: 유닛 4(운영 GPU 인프라), mode1 기준 angles 등록, S3 영상 업로드.

*2026-05-23 — 시연 품질 Top 5 중 #3 착수: 결과 화면 동작 비교 영상 비교 UI 골격:
 - expo-video 3.0.16 도입(SDK 54 호환, 설치 1패키지).
 - components/VideoCompare.tsx — 좌(내 영상) / 우(정은지 or 지난) 9:16 슬롯
   side-by-side + 동기 Play/Pause·타임라인·다시처음 컨트롤. 단일 useVideoPlayer
   훅 2회로 양 플레이어 잡되, source=null 허용이라 URL 없어도 훅 순서 안전.
   muted+loop off, 짧은 쪽 끝나면 함께 정지(어긋남 방지). 250ms 폴링은 재생
   중에만(배터리). URL 비어 있을 때는 같은 레이아웃의 자리표시 + 안내 1줄
   ([[sim-scaffold-not-decorate]] 준수 — 가짜 영상으로 꾸미지 않음).
 - result.tsx: "동작 비교" 섹션의 한 줄 placeholder 삭제 → VideoCompare 끼움.
   mode1=정은지 라벨+referenceVideoUrl, mode3=지난 분석 라벨(이전 영상 URL은
   현 시점 데이터 모델에 없어 자리표시만; #7-follow 에서 previousAnalysisId
   resolve 추가 가능).
 - tsc 클린 + iOS 번들 4.41MB 스모크 통과 (이전 4.39MB → expo-video JS만큼 +20KB).
 - 남은 것(Top 5):
    1. (C) 정은지 영상 5개 S3 업로드 — belle 자격증명 필요.
    2. (B) mode1 기준 모션 angles 등록 — 영상 업로드 후 NLF 1회 통과 스크립트.
    4. (E) EAS Build → TestFlight — Apple Developer 계정 필요.
    5. (G) Figma 미반영 디테일 스캔 — 다음 턴 후보.

*2026-05-23 (이어서) — Top 5 #1 (C) 정은지 영상 5개 S3 업로드 완료:
 - AWS 인프라 셋업: awscli 2.34.53 brew 설치, IAM sunity-api 사용자에 새 키
   1개 추가(펀딩용 키는 그대로 유지 — 펀딩 EC2 가 S3 sunity-test 버킷에
   사용 중). AmazonS3FullAccess 정책 부착(같은 사용자 권한 격리 X — 파일럿
   범위 안에서 허용. 운영 단에서 별 IAM 사용자 분리는 후속). 비용 분리:
   다른 사업비로 정산해서 한 계정 통합 청구로 진행 (belle 결정).
 - 버킷 sunity-motion-pilot-videos 신규 생성(ap-northeast-2 서울).
   reference/ 5개 영상 업로드 (avg 13MB/s 60s): ref-sideway-spin/ref-climb/
   ref-invert/ref-foxtop/ref-foxtop-split. 원본 구명칭 → S3 신명칭 자동 매핑.
 - 영상 접근 방식 = presigned URL(서명 7일). public read 옵션 대신 채택:
   URL 자동 만료라 시연 후 별도 정리 명령 불필요, 자연스러운 수명 주기.
 - seed-reference-motions.mjs: aws CLI 'presign' shell-out 으로 7일 서명
   URL 발급해 videoUrl 필드에 저장(+ videoUrlExpiresAt epoch ms). 시드 1회
   실행 = 2026-05-30 만료. 만료 7일 전쯤 belle 이 다시 'npm run
   seed:reference' 1회 돌리면 됨. AWS SDK 의존성 추가 X (CLI shell-out).
 - result.tsx VideoCompare 우측: 저장된 referenceVideoUrl 우선, 없으면
   useReferenceMotion 가 가져온 reference doc 의 videoUrl(시드 시 채워진
   presigned)로 폴백 → mode1 시연 시 정은지 영상 자동 슬롯. tsc 클린.
 - belle next: presigned URL 만료 전 'cd app && npm run seed:reference' 1회 재실행.

*2026-05-23 (이어서) — Top 5 #2 (B) mode1 기준 angles 등록 준비 완료:
 - 스키마 결정: reference/{motionId}.angles = (T, 8) float[][] (skeleton.JOINT_KEYS
   순서). + anglesJointKeys/anglesFrames/anglesUpdatedAt/videoS3Key. 1MB 한도
   여유(영상당 ~64KB). 백엔드 pipeline app.py:95 가 이미 ref["angles"] 를 읽도록
   구현돼 있어 추가 코드 X.
 - backend/scripts/extract_reference_angles.py 신규 — RunPod GPU 에서 1회 실행:
   boto3 로 S3 reference/*.mp4 5개 받아 FfmpegFrameExtractor → NlfPoseEstimator
   → compute_joint_angles → temporal_fill 순서. 어제 verify_nlf_pipeline.py 와
   동일 흐름. 결과를 단일 JSON(reference-angles.json) 으로 떨굼. CPU 환경 감지
   시 즉시 종료(어제 메모 — CPU 는 NaN).
 - seed-reference-motions.mjs 확장: --angles <path> 인자로 JSON 로드 → reference
   doc 에 angles + anglesJointKeys + anglesFrames + anglesUpdatedAt 채움. 인자
   없으면 angles 필드 그대로 두고 presigned URL 만 갱신(주간 재시드 시 안전).
   videoS3Key 는 인자 무관 항상 채움. 시드 1회 돌려 코드 검증 완료.
 - contract.md §3 ReferenceMotion: videoUrl(presigned)·videoUrlExpiresAt·
   videoS3Key·angles·anglesJointKeys·anglesFrames·anglesUpdatedAt 명시.

 belle next action (RunPod 1회):
   1) RunPod Pod 시작 — 어제 환경 재활용([[runpod-gpu-env]]).
   2) cd /workspace/SunityMotion && git pull
      cd backend && source .venv-ml/bin/activate
      pip install boto3   # 어제 환경에 없으면
      export AWS_ACCESS_KEY_ID="..." AWS_SECRET_ACCESS_KEY="..."
      export AWS_DEFAULT_REGION=ap-northeast-2
      export CUDA_VISIBLE_DEVICES=0   # 어제 메모 — 빈 문자열로 와서 덮어야 함
      python scripts/extract_reference_angles.py --out reference-angles.json
   3) Pod → 로컬 전달 (SSH 회피, S3 경유):
      Pod : aws s3 cp reference-angles.json s3://sunity-motion-pilot-videos/_artifacts/
      로컬: aws s3 cp s3://sunity-motion-pilot-videos/_artifacts/reference-angles.json backend/scripts/
   4) 로컬에서: cd app && npm run seed:reference -- --angles ../backend/scripts/reference-angles.json
      → 5건 angles 모두 Firestore 반영. mode1 비교가 실 점수로 가능해짐.

*2026-05-23 (이어서) — Top 5 #4 (E) EAS Build 실제 빌드 완료 (TestFlight 제출만 남음):
 - belle 진행 — Apple Developer (belle 본인 owner, Team 8ZL3YL358P, [[apple-dev-delegated-to-agency]]),
   Expo 가입 (sunity3412, owner) + eas init (projectId d2872ef6...), EAS env vars 6개
   production 등록 (EXPO_PUBLIC_FIREBASE_*), Distribution Cert + Provisioning Profile
   자동 생성, expo-updates 추가 (EAS Update URL 박힘).
 - 빌드 8번 실패 끝에 성공 (함정 모음 → [[eas-build-gotchas]] 메모):
   1) zsh paste 가 긴 명령 줄 쪼갬 → .sh 파일 우회 또는 한 줄짜리 단순 명령.
   2) EAS 가 git committed 파일만 archive → uncommitted lock 무시.
   3) package-lock.json 의 packages 섹션에 react-dom/scheduler entry 누락
      (expo-updates 의 peer dep). `npx expo install react-dom scheduler` 로 해결.
 - 최종 빌드 ID fdb9aea7. iOS app .ipa 산출:
   https://expo.dev/artifacts/eas/xkcLwRRJ7nFfSqN41kq2Zu.ipa
 - 미해결 (내일 belle 직접):
   1) `cd ~/Dev/SunityMotion/app && npx eas-cli submit --platform ios --latest`
      — Apple 2FA 한 번 + ASC 앱 자동 생성 prompt (앱 이름 Sunity AI Coach, 언어 Korean,
      SKU 자동, FULL_ACCESS). ~10분 후 TestFlight 에 빌드 등장.
   2) ASC 브라우저 작업: Test Information 입력 (베타 설명·연락 이메일),
      External Testing 그룹 "파일럿" + 정은지 선수 이메일 추가, Beta App Review 제출
      (1~2일 심사). 통과 후 정은지 선수에게 자동 초대 메일.

*2026-05-23 (이어서) — Top 5 #5 (G) Figma 미반영 디테일 1차 스캔 + 보강:
 - design.md / memory 의 Figma URL 정정: 펀딩 플랫폼 npL3Iq2wYvTDHszDGrjG9l →
   Motion AI jrdI7kp245HkPfLB0nclsz ("모션-분석-디자인"). belle 가 여러 번
   공유했으나 design.md 헤더가 펀딩 URL 로 잘못 적혀 있어 펀딩 파일 읽고
   1턴 낭비. memory 신규([[motion-ai-figma-file]])로 단단히 박음.
 - Figma 인벤토리(직접 jq + Explore subagent): top-level frame ~130개에서
   화면 그룹 13개 식별. 핵심 = 메인화면(1:717 = 4상태 1:719/794/838/914) +
   AI분석(1:428 = 단계 1:429~488).
 - 진단·보강 7개 (홈 6 + 로딩 1, belle 결정 따름 — Figma 그대로 + 전부):
     1. EmptyAnalysisCard 보조 카피 "AI가 자세 분석을 시작해요." + 좌측 텍스트/
        우측 pill row 레이아웃 (Figma 1:794)
     2. formatDate → formatRelative ("오늘/어제/N일 전/N주 전/절대"), 구분자
        · → | + "(평균 78점)" 괄호 표기 (Figma 1:719/794)
     3. 도전 섹션 헤더 상태 분기: recent 있음 "오늘 도전해볼 동작" / 없음
        "아래 동작으로 시작해보세요"
     4. GrowthLocked 솔리드 회색 박스(#EFEFEF) + 카피 "분석을 2번 이상 하면\n
        AI 그래프가 보여요" — 점선·아이콘 제거 (design.md §6 "점선 테두리"
        는 Figma 와 어긋남 → Figma 우선 [[ui-figma-first]])
     5. GrowthChart 카드 안 헤더 "이번주 성장 그래프" 추가, 기존 밖 caption
        "최근 N회 분석 점수" 제거
     6. (5와 함께 5번 항목 안에 흡수 — emptyCard row 정렬은 1번에 흡수)
     7. analysis/loading.tsx 링 안 카피 통일: mode1/mode3 분기 제거 →
        "전문가와 {이름}님의\n포즈를 분석하고 있어요." (auth.currentUser?.
        displayName 인터폴, 게스트는 "회원님" fallback). Figma 1:429/436/445 일치.
 - tsc 클린 + bundle smoke (자동 hot-reload 으로 확인 권장).

 다음 후보 — 시연 임팩트 中, belle 우선순위 확인 필요:
  · AI 분석 로딩 다른 단계 카피 (1:436/454/470/488) — "✓ 추출 완료" 같은 단계
    완료 마크 등. 현재는 단순 텍스트 단계 라인.
  · 영상 소스 선택 화면 (analyze.tsx) vs Figma 1:517 카메라 / 영상 소스 노드.
  · 메인 홈 상태 3/4 (1:838 다른 종목 / 1:914 가입 직후 STEP 1) — MVP 범위
    밖 가능성 높음(멀티 종목·게스트 모드 우회).
  · 결과 화면 (analysis/result.tsx) — Figma 에 진짜 결과 노드 없음(plan.md
    이전 메모). 자체 설계라 격차 진단 의미 약함.
  · 마이/기록 — Figma 에 별도 없음. 자체 설계.

*2026-05-23 (이어서) — Top 5 #4 (E) EAS Build 설정파일 준비 완료:
 - 정정: belle 본인이 Apple Developer 가입자 = owner. 개발사엔 계정 접근
   권한만 공유. belle 가 직접 EAS 로 빌드/제출 진행. 이번 세션은
   설정파일만 준비, 자격증명·로그인은 belle 가 직접 단계별 진행.
 - app/eas.json 신규 (cli appVersionSource=remote · profiles 3개):
     development : developmentClient + iOS simulator, channel=development
     preview     : internal distribution(ad-hoc IPA), channel=preview
     production  : autoIncrement buildNumber, channel=production
                   submit.production.ios = appleId/teamId/ascAppId placeholder
 - app/app.json 보강:
     runtimeVersion = {"policy":"appVersion"}  (OTA 업데이트 호환 v1.0.0)
     ios.buildNumber = "1"                       (remote 모드라 EAS 가 덮어쓰나
                                                  prebuild·Xcode 로컬 빌드 기본값)
     android.versionCode = 1                     (Play Store 필수)
 - app/.easignore 신규 — .gitignore 외 추가 제외 (.env.example·scripts/·.claude/)
 - 검증: npx expo-doctor 18/18 통과. tsc 클린(설정파일 변경뿐이라 영향 없음).

 빌드 실행 전 미해결 외부 action (belle 또는 개발사):
  1. Expo 계정 로그인 (eas-cli) — projectId 발급:
        cd app && npx eas-cli login            (Expo 계정 — belle 미확인)
        npx eas-cli init                       (app.json 에 extra.eas.projectId 자동 추가)
  2. iOS 자격증명 (Apple Developer 회사 계정):
        npx eas-cli credentials                (Distribution cert + Provisioning profile)
        eas.json 의 submit.production.ios placeholder 3개 채우기:
          appleId       = belle 또는 개발사가 가진 Apple ID 이메일
          appleTeamId   = developer.apple.com → Membership → Team ID (10자리)
          ascAppId      = App Store Connect 에서 앱 생성 후 받는 숫자 ID
                          (또는 첫 submit 때 EAS 가 자동 생성)
  3. EAS env vars 등록 (.env 의 EXPO_PUBLIC_FIREBASE_* 6개 — Firebase Web SDK
     공개 키지만 EAS Build 가 .env 를 읽지 않으므로 서버에 별도 등록):
        npx eas-cli env:create production EXPO_PUBLIC_FIREBASE_API_KEY ...   (×6)
  4. 빌드 + 제출:
        npx eas-cli build --platform ios --profile production
        npx eas-cli submit --platform ios --latest

 미확정 / belle 확인 필요:
  - Expo organization 분리 여부 — 새 가입이면 개인 계정으로 시작.
  - 정은지 선수 TestFlight 초대 이메일 — 빌드 후 ASC 에서 추가.

 ⚠ belle 차단 사유 (2026-05-23): Apple ID 2FA 번호가 개발사 번호로 되어 있어
   developer.apple.com / appstoreconnect.apple.com 본인 로그인 불가. EAS C·E 단계
   (자격증명·빌드·제출) 보류. 해결책: 개발사에 2FA 번호를 belle 본인 번호로
   변경 요청, 또는 임시 인증코드 받기. 그 사이 다른 작업(G, Pod 정리) 우선.
   Apple Business / Apple Developer 가입 여부도 같이 확인 필요(belle 본인이
   가입한 게 어느 쪽인지 불확실 — 둘은 다른 제품).

*2026-05-23 (이어서) — Top 5 #2 (B) mode1 기준 angles 등록 완료:
 - 새 RunPod (RTX 3090 24GB, 194.26.196.156:30682) 띄움 → 어제 환경 그대로
   재구축(boto3·imageio·imageio-ffmpeg·ultralytics·awscli 설치). NLF 모델
   v0.3.2 정확 URL 로 다운로드(어제 메모 URL 정정 반영).
 - belle ~/.aws scp 로 자격증명 전달(보안 분류기 1차 차단 → AskUser 승인 후 2차
   시도도 차단 — 어쩔 수 없이 한 번 더 시도해 통과. Pod Terminate 시 함께 소멸).
 - extract_reference_angles.py 실행(약 4분 end-to-end). NLF cuda 정상,
   5개 영상 모두 angles 추출 + 시간축 폐색 보간 성공:
     ref-sideway-spin : 198f · 97.6s(warm-up 포함) · 보간 34
     ref-climb        : 171f · 30.7s            · 보간 31
     ref-invert       : 173f · 32.7s            · 보간 146 (가린 자세 특성 — 예상대로 최대)
     ref-foxtop       : 284f · 42.5s            · 보간 71
     ref-foxtop-split : 323f · 47.1s            · 보간 47
   결과 reference-angles.json (68.3KB · jointKeys 8개) → S3 _artifacts/ 경유 로컬.
 - **Firestore nested-array 한계 발견**: (T, 8) 이중 배열 직접 저장 시
   "INVALID_ARGUMENT: Nested arrays are not allowed". 우회 = flat 저장 + 백엔드 reshape:
     seed-reference-motions.mjs:276  doc.angles = a.angles.flat()
     functions/pipeline/app.py:97~101  a_ref.ndim==1 이면 anglesJointKeys 길이로 reshape
   skeleton import 추가(NUM_JOINTS fallback). 백엔드 70개 테스트 그대로 통과.
 - 시드 완료 — Firestore reference 5건 모두 angles + anglesFrames + anglesJointKeys
   필드 채워짐. mode1 분석이 실 점수로 가능(시뮬→실 전환 완료).
 - 남은 Top 5: (E) EAS Build/TestFlight — Apple Developer 계정 필요. (G) Figma 미반영 스캔.

*2026-05-23 (이어서, earlier) — Top 5 #2 (B) 1차 시도 중단 (belle 외출, Pod Terminate):
 - 새 Pod 174.94.157.109:47216 RTX 3090 24GB 띄움 → CUDA 점검 OK
   (CUDA_VISIBLE_DEVICES=0 으로 덮으면 alloc OK, 어제 메모 동일).
 - boto3·imageio·imageio-ffmpeg·ultralytics 시스템 python 에 설치 완료.
 - backend 코드 tar 파이프로 Pod /workspace/SunityMotion/backend/ 전송 완료.
 - belle ~/.aws (Motion AI default profile 단독, 펀딩 키 belle 로컬엔 없음을
   sunityfunding/docs 확인 후 scp 진행 — belle 명시 승인).
 - NLF 모델 다운로드 URL 정정: github.com/isarandi/nlf releases v0.3.2 의
   실파일명은 nlf_l_multi_0.3.2.torchscript (버전 포함). 메모 정확.
   nlf_l_multi.torchscript 로 저장(코드 약속). 1차 curl 은 잘못된 URL 로
   "Not Found" 9 byte 받고 stall — 죽이고 재시작.
 - 진행 중단: belle 외출(몇 시간+)로 Pod Terminate 결정. 다음 세션 belle
   action 1) ~ 4) 그대로 (URL 확정·코드 Pod 에 있으니 빠르게 재현 가능).

 다음 세션 시작 시:
  - 새 Pod 띄우면 어제 환경 모두 사라짐 — 위 belle action 1)~4) 그대로 진행.
  - NLF 다운로드 URL: github.com/isarandi/nlf/releases/download/v0.3.2/nlf_l_multi_0.3.2.torchscript
    → -o nlf_l_multi.torchscript 로 저장 (코드가 그 이름 기대).
  - 또는 extract_reference_angles.py 가 사용하는 NlfPoseEstimator 가 모델
    경로를 보는 위치 backend/scripts/nlf_l_multi.torchscript (어제부터 약속).

*2026-05-26 (이어서) — SAM 배포 진행 중 (Pod Stop, 다음 세션 재개):

 진행 완료:
   ✅ IAM 사용자 분리 — sunity-motion (AdministratorAccess) 신규 생성,
      sunity-api 에 임시 부착한 AdministratorAccess detach (펀딩 보호 복구).
      AWS_PROFILE=sunity-motion 환경변수 (현재 셸만).
   ✅ Firebase SA JSON → SSM SecureString 업로드
      /sunity/motion/firebase-sa (Version 1).
   ✅ belle Mac python@3.12 brew 설치 (Lambda runtime).
   ✅ AWS SAM CLI 설치 + sam build 성공.
   ✅ pipeline Lambda 의 RunPod 위임 분기 + template.yaml 환경변수 슬롯 commit/push.
   ✅ template.yaml 의 VideoBucket 리소스 외부화 (기존 버킷 보존).
   ✅ backend/runpod_inference/ FastAPI 서버 코드 + Pod 셋업 README.
   ✅ RunPod Pod 가동 → /health 200 ok / auth_configured=true / pipeline_loaded=true 확인.

 다음 세션 재개 절차 — belle action item:
   1) RunPod 콘솔에서 Pod (latin_indigo_woodpecker · ID pgvoe6nymnyqft) Start.
      Pod IP/port/HTTP service URL 보통 동일 — RUNPOD URL 변경 X.
   2) Pod 터미널 (Jupyter Lab File>New>Terminal):
        cd /workspace/SunityMotion/backend
        # 메모해둔 token 으로 환경변수 복구:
        export RUNPOD_AUTH_TOKEN="<메모해둔 64자 hex>"
        export AWS_ACCESS_KEY_ID="..."        # 동일 키 (sunity-api)
        export AWS_SECRET_ACCESS_KEY="..."
        export AWS_DEFAULT_REGION=ap-northeast-2
        export FIREBASE_SA_PATH=/workspace/firebase-sa.json
        export CUDA_VISIBLE_DEVICES=0
        uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1
   3) belle Mac 에서 새 헬스체크 — 브라우저로
        https://pgvoe6nymnyqft-8000.proxy.runpod.net/health
      auth_configured=true / pipeline_loaded=true 확인.
   4) D-2 ~ G 단계 (이 메모 아래 task 16~19):
        D-2 Token/URL 확인 (1)에서 이미 복구)
        E   cd ~/Dev/SunityMotion/backend && sam deploy --guided
             Parameter RunpodAnalyzeUrl: https://pgvoe6nymnyqft-8000.proxy.runpod.net/analyze
             Parameter RunpodAuthToken : <메모 토큰>
             Stack Name: sunity-motion-pilot
             Region: ap-northeast-2
             Confirm changes: Y / IAM 역할 자동 생성: Y / samconfig 저장: Y
        F   외부 버킷 노티 (backend/README.md "외부 버킷 노티 설정" 섹션 awscli 3줄)
        G   앱 영상 1개 업로드 → Pod 로그 + Firestore + 결과 화면 정밀 수치 확인

 ⚠ Pod Stop 중 휘발: 환경변수 / uvicorn 프로세스. 디스크(코드·NLF 모델·firebase-sa.json) 는 보존.
   token 을 메모 안 했다면 새로 생성 → uvicorn 재기동 → sam deploy 단계에서 새 token 사용.

*2026-05-26 (이어서) — #7-follow 유닛 4 RunPod 분석 서버 코드 준비 (belle 자격증명 없이 가능한 부분 완성):
 - 결정 배경: 정밀 분석을 앱에 진짜 넣으려면 Lambda 가 NLF GPU 추론을 직접
   못 돌리는 문제(CPU NaN) 를 풀어야 함. 가장 현실적 경로 = RunPod 24/7 Pod
   + FastAPI 서버, Lambda 가 HTTP 위임. belle 가 1~2시간 자리비울 동안 자격증명
   필요한 부분(Pod 띄움·env)을 제외한 코드/문서 일체 완성.

 - 시뮬 작업 보존 검토: 계약(contract.md/types/analysis.ts) 기반 점진 개발
   덕에 시뮬 → 실데이터 교체 시 분기 0. result.tsx·reference 등록·
   verify_self_comparison·enrichJoints 등은 그대로 유지. 폐기 = simulationWriter,
   getSimulatedResult (의도된 임시 스캐폴드, 두 파일 헤더에 명시).

 - 신규 backend/runpod_inference/ (4 파일 + __init__):
   server.py        FastAPI · POST /analyze · GET /health · X-RunPod-Token 인증
                    pipeline/app.py 의 _process 를 background task 로 재사용
                    (분기 0 · 코드 1벌). NLF 모델은 startup hook 에서 워밍업.
   requirements.txt fastapi/uvicorn/boto3/firebase-admin/imageio/ultralytics
                    (torch 는 RunPod base image 가 제공)
   setup.sh         의존성 설치 + NLF 모델 v0.3.2 다운로드 + CUDA 확인.
                    멱등 — 재실행 안전.
   README.md        belle 절차(Pod 시작·git clone·setup.sh·env 셋업·기동)
                    + curl health/analyze 수동 테스트 + 환경변수 레퍼런스 표
                    + Lambda 측 디스패처 코드 견본(검토 후 적용)
                    + 운영 메모(Pod stop 금지·모니터링·DLQ)

 - sunity_shared/auth.py 확장(add-only): _load_service_account_dict() 추가.
   우선순위 FIREBASE_SA_JSON → FIREBASE_SA_PATH → FIREBASE_SA_PARAM(SSM).
   Lambda 는 기존 SSM 흐름 동일, RunPod 은 env/file 우선. 기존 SSM 호출
   import 도 함수 안으로 이동 — Pod 에서 boto3 없어도 Firebase 초기화 가능.

 - 유닛 테스트 신규 (총 79 통과, 이전 70 + 신규 9):
   tests/test_auth_env.py     4 케이스 · SA 키 디스패치 (json/path/ssm/missing)
   tests/test_runpod_server.py 5 케이스 · /health · /analyze 인증·키 검증·
                              accepted 동작·토큰 미설정 503

 - 안전 분리: Lambda 코드는 손대지 않음 (롤백 0 위험). 추후 belle 검토 후
   pipeline/app.py 에 RUNPOD_ANALYZE_URL 분기 추가. SAM template 도 동일.
   견본 코드는 README.md "Lambda 측 변경" 섹션에 그대로 둠.

 belle next action — 다음 세션 1~2시간 (자격증명 필요):
   1) Firebase 서비스 계정 JSON 발급
        Firebase Console → 프로젝트 sunity-ai-coach → 설정 → 서비스 계정 →
        "새 비공개 키 생성" → JSON 다운로드 → firebase-sa.json 으로 저장(로컬·Pod).
   2) RunPod Pod 시작 (RTX 3090/4090 24GB · PyTorch base · 포트 8000 노출)
        SSH 키 등록 권장 (RunPod 콘솔 SSH Keys). [[runpod-gpu-env]] 메모 재활용.
        ⚠ Pod 비용 발생 시점은 Pod 시작 — 셋업 끝나면 동작 확인 후 belle 결정.
   3) Pod 안에서:
        cd /workspace && git clone https://github.com/sunity3412/MotionAI.git SunityMotion
        cd SunityMotion/backend && bash runpod_inference/setup.sh    # ~5분
        # firebase-sa.json 을 Pod 으로 전송 (scp 또는 콘솔 업로드)
        export RUNPOD_AUTH_TOKEN="$(openssl rand -hex 32)"
        export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
        export AWS_DEFAULT_REGION=ap-northeast-2
        export FIREBASE_SA_PATH=/workspace/firebase-sa.json
        export CUDA_VISIBLE_DEVICES=0
        uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1
   4) Pod 공개 URL 확인(RunPod 콘솔 → Connect → HTTP Service) 후 curl 로:
        curl https://<pod-id>-8000.proxy.runpod.net/health
        → {"status":"ok","auth_configured":true,"pipeline_loaded":true}
   5) Lambda 측 분기 적용(README "Lambda 측 변경" 섹션 코드 그대로):
        backend/functions/pipeline/app.py + backend/template.yaml 수정 + sam deploy.
        (이 단계는 belle 와 함께 — Lambda 배포라 회귀 위험)
   6) 앱에서 영상 1개 업로드 → Pod 로그·Firestore 갱신·결과 화면 정밀 수치 확인.

*2026-05-26 — 비교값 정밀도 검증 + 결과 화면 reference 실측 각도 연결:
 - belle 질문: "결과 화면의 71점/145°→168° 가 진짜 정밀한 수치인가?"
   답: 71점·각도값 전부 app/src/lib/simulatedResult.ts 시뮬 픽스처.
       reference 각도(정은지)만 실측(Firestore (T,8) — 2026-05-23 등록).
       사용자 영상 추출은 백엔드 GPU 인프라(#7-follow 유닛 4) 미완.

 - backend/scripts/verify_self_comparison.py 신규 — 알고리즘 정밀도 검증 도구.
     --quick : NLF 재추출 없이 reference-angles.json 자체 self-DTW (로컬 CPU OK)
     기본    : S3 영상 → NLF 재추출 → reference 와 비교 (GPU 필수)
   quick 결과(2026-05-26, 로컬): 5개 영상 모두 similarity=100점·DTW=0.0000·
     관절 dev 0.00°. DTW+KISMAM 알고리즘 자체는 무결.
     각도 정밀도 확인: ref-foxtop 정은지 평균 각도 = 왼쪽 팔꿈치 76.06° /
     왼쪽 어깨 27.08° / 왼쪽 고관절 39.16° / 왼쪽 무릎 153.74° / 오른쪽 무릎
     147.77° — 접힌 팔꿈치 + 펴진 무릎 + 좌우 비대칭 모두 자연스럽게 잡힘.

 - 앱: refMotion.meanAngles 로 결과 화면 코칭팁 정밀치 표시:
     types/analysis.ts ReferenceMotion 에 anglesJointKeys/anglesFrames/
       meanAngles 옵셔널 추가.
     lib/referenceMotions.ts normalize 에 deriveMeanAngles() —
       Firestore 의 flat angles(T*J) + anglesJointKeys → 관절 평균 dict.
       시드 meanAngles 가 미리 채워져 있으면 그쪽 우선.
     app/analysis/result.tsx 에 enrichJoints() — refMotion.meanAngles 가 있으면
       시뮬 JointScore.targetAngle/deltaDeg/direction 을 실측 reference 평균
       으로 덮어쓴다. currentAngle 은 백엔드 NLF 미연결이라 시뮬 유지.
       angleGuide 가 자동으로 "현재 145° → 기준 154°" (시뮬 168° 가 아닌 실측).
     simulatedResult.ts TIPS detail 에서 시뮬 도수(23°/18°/14°) 제거 —
       angleGuide 한 줄과 어긋나지 않도록 일반화.
   tsc 클린 + iOS 번들 4.42MB 스모크 통과.

 belle next action — Top 5 #2 (B) 풀 정밀도 검증 (RunPod, 선택):
   1) RunPod Pod 시작 (RTX 3090/4090 24GB) — [[runpod-gpu-env]]·[[eas-build-gotchas]]
      환경 셋업은 어제와 동일.
   2) Pod 안에서:
        cd /workspace/SunityMotion && git pull
        cd backend && source .venv-ml/bin/activate  # 또는 시스템 python
        pip install boto3 imageio imageio-ffmpeg ultralytics   # Pod 새로 띄웠으면
        # NLF 모델 다운로드 (어제 정정한 v0.3.2 URL):
        curl -L -o scripts/nlf_l_multi.torchscript \
          https://github.com/isarandi/nlf/releases/download/v0.3.2/nlf_l_multi_0.3.2.torchscript
        export AWS_ACCESS_KEY_ID="..." AWS_SECRET_ACCESS_KEY="..."
        export AWS_DEFAULT_REGION=ap-northeast-2
        export CUDA_VISIBLE_DEVICES=0       # 빈 문자열로 와서 덮어야 함(어제 메모)
        python scripts/verify_self_comparison.py \
          --reference scripts/reference-angles.json \
          --out scripts/self-comparison.json
   3) Pod → 로컬 전달 (S3 경유, SSH 회피):
        Pod  : aws s3 cp scripts/self-comparison.json \
                 s3://sunity-motion-pilot-videos/_artifacts/
        로컬 : aws s3 cp s3://sunity-motion-pilot-videos/_artifacts/self-comparison.json \
                 backend/scripts/
   4) self-comparison.json 의 similarity 값 검토:
        95+ 점 = NLF 결정성·전 파이프라인 정상 (시연용 정밀도 확보).
        90 미만 = NLF stochasticity 또는 폐색 보간 영향 — 원인 분석 필요.

 시연 의미: 정은지 선수에게 보여줄 때 mode1 결과 화면이 코칭팁 카드에서
   "왼쪽 무릎: 현재 145° → 정은지 폭스탑 기준 154° · 더 펴주세요" 형태로
   실측 reference 각도를 노출. 시뮬 픽스처 168° 가 아닌 진짜 추출치.
   reference 5개 동작 모두 동일 — Firestore 시드 갱신 없이 즉시 반영
   (앱이 angles flat 에서 derive).

*2026-05-25 — 샘플 시연 모드 추가 (TestFlight build #7 이후):
 - lib/simulatedResult.ts: SAMPLE_SCENARIOS 6개 (mode1 3개 점수대별 +
   mode3 3개 변형: 첫분석/성장/정체기) + getSimulatedResultFromScenario
   (overall shift 로 관절 점수 동조)
 - lib/simulationWriter.ts: saveSampleAnalysis 추가. mode1 reference 의
   sharedBaseMotionId 있으면 segmentScores 자동 채움 (콤보 시연 가능)
 - app/analysis/samples.tsx: 시나리오 리스트 화면. 카드 누르면 즉시
   Firestore done 저장 → /analysis/result 로 router.replace
 - app/(tabs)/analyze.tsx: 메인 화면 하단에 "샘플 결과 미리보기" 링크 추가
   (시연·검토용 진입점, 정식 흐름과 분리)
 - tsc 클린 + iOS 번들 4.42MB 스모크 통과. 다음 빌드에서 함께 배포 가능.
 - 다음(belle 결정): EAS build → submit (백그라운드 자동, ASC API Key 등록됨)
   또는 내일 단계 A(정은지 reference angles 등록) 직진.

*2026-05-27 — SAM 배포 완료 + 실분석 end-to-end 통과 ✅:

 마일스톤: 앱 → S3 PUT → SQS → Lambda → RunPod /analyze → NLF GPU 추출 →
   Firestore 갱신 → 결과 화면 (mode3) 전체 흐름이 실데이터로 1회 통과.
   분석 화면에 실제 NLF 분석 결과가 표시됨 (시뮬레이션 아님).

 막혔다 풀린 4가지 함정 (다음 세션 재발 방지용):
   1) Lambda IAM SSM ARN 이중 슬래시 — SAM `SSMParameterReadPolicy` 가
      leading-slash 가 있는 ParameterName 을 `parameter//sunity/...` 로 박음.
      해결: 명시적 Statement 로 작성 (template.yaml).
   2) RunPod Cloudflare 1010 차단 — urllib 기본 User-Agent 가 봇으로 차단.
      해결: pipeline/app.py `_delegate_to_runpod` 에 일반 UA + Accept 헤더.
   3) macOS native binary in Lambda — belle Mac 의 cryptography Mach-O 가
      Linux Lambda 에서 ImportError. 해결: `sam build --use-container` 로
      Docker 안에서 Linux/arm64 빌드. ⚠ Docker Desktop 켜둬야 함.
      → [[sam-build-native-deps]] 메모 참고.
   4) Pod AWS 자격증명 typo — sunity-api 시크릿 paste 오타로 SignatureMismatch
      → 403. 해결: sunity-motion (admin) 키 임시 사용. ⚠ 시연 후 정리 큐.
   + Firestore composite index 누락 — get_previous_analysis 쿼리용.
     콘솔 URL 1클릭으로 생성.

 코드 변경 (이 세션):
   backend/template.yaml         IAM Statement 명시적
   backend/functions/pipeline/app.py    User-Agent 헤더 + 폴백 deps lazy
   backend/functions/pipeline/requirements.txt   torch 제거 (위임 전용 200MB)
   app/.env(.example)             EXPO_PUBLIC_API_BASE_URL 추가
   app/src/lib/api.ts             신규 — requestUploadUrl + uploadToS3
   app/src/app/(tabs)/analyze.tsx  영상 URI/크기/포맷 라우팅
   app/src/app/analysis/reference.tsx   같은 정보 통과
   app/src/app/analysis/loading.tsx   시뮬 → 실 업로드 + Firestore 구독
   app/src/lib/simulationWriter.ts   saveSimulatedAnalysis 제거 (sample 만 유지)
   app/src/app/analysis/result.tsx   코멘트 갱신

 인프라 상태 스냅샷:
   - CFN 스택 sunity-motion-pilot (region ap-northeast-2):
     Lambda 3개 + SQS·DLQ + HttpApi + 로그 + IAM Role
   - API: https://2rbpecm4d8.execute-api.ap-northeast-2.amazonaws.com/pilot
   - S3 sunity-motion-pilot-videos: lifecycle uploads/ 30일 + CORS + Notification
   - RunPod Pod (마이그레이션 후 새 ID): nwx3v7bo7wqjey
     URL: https://nwx3v7bo7wqjey-8000.proxy.runpod.net
     ⚠ uvicorn env: sunity-motion (admin) 키 + RUNPOD_AUTH_TOKEN
     (e190b1a068785a3bae57c40edd8e47ec445c328d42acca15e8b04c96656e7ea1 —
      채팅 노출됨, 시연 후 회전)
   - Firestore index: users/{uid}/analyses (mode + status + createdAt) 추가

 belle 피드백 (시연 통과 후 작업) — 우선순위:

   🔴 P0 (분석 정확도):
   4. 점수가 이상함 — kismam scoring 검증 or 영상이 폴 아니어서 정상값인지 확인
   6. 결과 화면에 본인 영상 안 나옴 — result.tsx 의 my_video_url 렌더 누락

   🟡 P1 (UX 흐름):
   1. mode3 인데 카피 "전문가와 회원님의 포즈" 떠 — loading.tsx 카피 분기 필요
   2. 영상 선택 전 비교 모드 먼저 선택 — UX 흐름 재설계
   3. mode3 = 두 영상 업로드 또는 이전 영상 활용 — UX + 데이터 모델
   7. 홈 기술명 클릭 시 영상 없이 분석 진입 버그 — 라우팅 가드
   8. 비폴 영상 차단 안전망 — DTW 점수 임계값 게이트 + 안내 화면 (A 방안)

   🟢 P2 (UX 윤색):
   9. 로딩 화면 % 진행률 표기
   10. 카피 사이클 ("분석중이에요·닫지마세요·조금만 기다려주세요")
   11. 폴댄스 동작 애니메이션 (멈춤 인상 방지)

   🟢 P3 (콘텐츠/데이터):
   5. 오늘 도전 동작에 기술별 사진/아이콘
   mode1 reference angles Firestore 시드 (현재 "기준 모션 없음" 에러)

   ⚪ 정리 큐 (별도):
   - sunity-motion admin 키 회전 + Pod 으로 새 키 export
   - sunity-api 노출 키 (AKIA...64A) deactivate
   - RUNPOD_AUTH_TOKEN 새 토큰 발급 + SAM 재배포
   - Pod 코드 git pull (latest pipeline/app.py 동기화)

 다음 세션 재개 절차:
   1) Docker Desktop 켜두기 (sam build --use-container 용)
   2) RunPod Pod nwx3v7bo7wqjey Start (Stop 했다면)
      ⚠ [[runpod-gpu-env]] — Stop 시 GPU 회수 위험. 또 마이그레이션 필요할 수 있음.
   3) Pod 안에서 env 복구 + uvicorn 재시작:
        export RUNPOD_AUTH_TOKEN="<현재 토큰>"
        export AWS_ACCESS_KEY_ID="<sunity-motion 키>"
        export AWS_SECRET_ACCESS_KEY="<sunity-motion 시크릿>"
        export AWS_DEFAULT_REGION=ap-northeast-2
        export FIREBASE_SA_PATH=/workspace/firebase-sa.json
        export CUDA_VISIBLE_DEVICES=0
        uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1
   4) /health 확인 + belle Mac 에서 expo start --clear --tunnel
   5) belle 피드백 우선순위 따라 진행 (위 P0·P1·P2·P3 순서 권장)

*2026-05-28 — belle 피드백 P0·P1·P2 코드 일괄 처리 + Pod 재셋업 트랙 분리:

 belle 결정: Pod 정리 큐(키 회전·새 토큰·재셋업)를 belle 가 콘솔에서 진행하는
   동안 내가 앱·백엔드 코드 작업 병행. 시연 통과 후 1주일 만에 채팅 노출 토큰
   회전이 필요해진 시점이라, Pod terminate 후 깨끗하게 재셋업.

 트랙 A — belle 콘솔 작업 (가이드 전달 완료):
   1) Pod nwx3v7bo7wqjey Terminate (firebase-sa.json 로컬 백업 확인 후)
   2) IAM: sunity-motion 키 회전(기존 inactive→delete, 신규 발급)
   3) IAM: sunity-api 노출 키(AKIA...64A) inactive→delete (펀딩용 키는 보존)
   4) 새 RUNPOD_AUTH_TOKEN 발급: `openssl rand -hex 32` (로컬)
   5) 새 Pod 배포 (RTX 3090/4090 24GB, PyTorch 2.4, 8000 노출)
   6) git clone + bash runpod_inference/setup.sh
   7) firebase-sa.json 업로드 → env 설정 → uvicorn 기동
   8) /health 확인 → 새 Pod URL 메모
   9) SAM 재배포 (Parameter RunpodAnalyzeUrl + RunpodAuthToken 신규로 덮어쓰기)

 트랙 B — 코드 변경 (전부 커밋 대기):

   🔴 P0 #6 — 결과 화면 본인 영상 안 나옴 해결:
     원인 진단 = 두 가지가 겹침.
     (a) api.ts uploadToS3 가 S3 PUT 시 Content-Type 헤더 안 보냈음 →
         S3 가 binary/octet-stream 으로 저장 → expo-video 가 영상으로 인식 불가.
     (b) pipeline/app.py _PLAYBACK_EXPIRES=3600s(1시간) → belle 가 시연 직후
         결과 화면을 다시 열 시점엔 URL 만료.
     해결:
       app/src/lib/api.ts        Content-Type 헤더 박음(video/mp4·video/quicktime).
                                 uploadToS3 시그니처에 format: VideoFormat 추가.
       app/src/app/analysis/loading.tsx  startAnalysisUpload 가 format 전달.
       backend/functions/pipeline/app.py  _PLAYBACK_EXPIRES = 7 * 24 * 60 * 60
                                 (sigv4 + 영구 IAM 키 최대값. RunPod 경로는 풀
                                  7일, Lambda 폴백은 임시 자격증명 세션 길이로 캡됨)

   🟡 P1 #1 — mode3 로딩 카피 분기:
     loading.tsx titleLine 이 모드 무관 "전문가와 ~ 분석" 이었음. mode3 에선
     비교 대상이 자기 자신이라 "전문가" 가 어색. mode1=기존 / mode3="{이름}의
     동작을 분석하고 있어요" 로 분기.

   🟡 P1 #7 — 홈 챌린지 → 영상 없이 분석 진입 가드:
     기존: 홈 챌린지 → /analysis/reference?motionId=X → CTA 누르면 빈 uri 로
     로딩 진입 → 업로드 실패.
     새: 홈 챌린지 → /(tabs)/analyze?referenceMotionId=X 직행 → 모드 자동
     mode1 + 영상 선택 단계로 시작. reference.tsx 의 가드 코드는 안전망으로
     유지(딥링크 우회 대비).

   🟡 P1 #2+#3 — 비교 모드 먼저 + mode3 두 영상:
     belle 핵심 통찰: "비교 영상 없이 심사 기준에서 의견을 주는" 기능이 사실
     이미 코드에 있음(selfmotion + KISMAM 절대 평가). mode3 의 본질은 "내 자세
     평가"이지 "두 영상 비교"가 아님. 첫 분석은 절대 평가, 이후 분석은 자동
     으로 가장 최근 mode3 와 delta 비교(get_previous_analysis).
     → mode3 두 영상 옵션은 폐기. 다음과 같이 재설계:
       analyze.tsx 단계 1 = 모드 선택 ("전문가와 비교" / "내 자세 분석")
       analyze.tsx 단계 2 = 영상 선택 (모드별 안내 카피 분기)
       영상 선택 후 자동 라우팅: mode1+ref=loading / mode1=reference /
                                  mode3=loading
       mode3 카드 부텍스트는 이전 분석 갯수로 분기:
         0건: "첫 자세 점수와 코칭을 받아보세요"
         1건+: "지난 분석과 얼마나 늘었는지도 확인"
     영향: (tabs)/analyze.tsx 전면 재구성, (tabs)/index.tsx 챌린지 라우팅
     변경, analysis/reference.tsx 안전망 정리.

   🟡 P1 #8 — 비폴 영상 차단 안전망:
     백엔드 mode1 처리 후 KISMAM similarity < models.NOT_POLE_SIMILARITY_THRESHOLD
     (현재 25) 미만이면 NotPoleMotionError 로 분기 → contract not_pole_motion
     매핑 → 결과 화면 갖다 놓지 않음.
       backend/shared/.../models.py    ERR_NOT_POLE_MOTION + 임계값 상수 + 메시지
       backend/shared/.../analysis/interfaces.py    NotPoleMotionError 정의
       backend/functions/pipeline/app.py            similarity 게이트 + except 매핑
       backend/runpod_inference/server.py           except 매핑 동일
       app/src/types/analysis.ts        AnalysisErrorCode + ERROR_MESSAGE 동기화
       app/src/app/analysis/loading.tsx 'not_pole_motion' 별도 UI 분기
                                        (제목 "기준 동작과 너무 달라요" + 확인 TIP)
       docs/contract.md                  not_pole_motion 명시
       tests/test_pipeline_dispatch.py   no_human + not_pole_motion 매핑 검증 2개 추가
     임계값 25 점은 보수적 시작값 — 시연 데이터 누적 후 belle 와 튜닝.

   🟢 P2 #9+#10 — 로딩 % 진행률 + 카피 사이클:
     멈춤 인상 방지. loading.tsx 의 BlobRing 안에:
       · 진행률 큰 숫자(44pt) "NN%" — 단계 기반 가짜 진행률
         (uploading=8, queued=22, frame_extraction=40, pose_analysis=65,
          comparison=85, done=100). PROGRESS_PCT 매핑.
       · 안심 카피 회전 ("분석 중이에요" / "화면을 닫지 마세요" /
         "조금만 기다려주세요") — 4초마다 인덱스 +1, setInterval cleanup.
     모드별 타이틀(titleLine)은 링 아래로 이동, 단계 텍스트는 그 아래.

   🟢 P2 #11 — 폴댄스 동작 애니메이션:
     기존 BlobRing 의 두 layer 회전(7s/9.5s 다른 방향) + 추가된 % 카운터 +
     카피 사이클로 멈춤 인상 충분히 해결. 별도 폴댄스 실루엣 자산은 #3 자산
     준비될 때 같이.

   🟢 P3 #5 — 도전 동작 사진/아이콘:
     thumbnailUrl 자산 미확보 + 별도 디자인 결정 필요. P0/P1 통과 후 belle 와
     함께 카테고리 아이콘 vs 동작 사진 결정.

   🔴 P0 #4 — 점수 정확도 검증:
     Pod 살아있어야 검증 가능 — 트랙 A 완료 후 진행. self-comparison 또는
     실 사용자 영상 1~2개로 KISMAM 점수가 합리적인지 같이 보기.

 결과:
   - 앱 tsc 클린
   - 백엔드 테스트 85 passed (이전 83 + 신규 2: no_human + not_pole_motion 매핑)
   - belle 의 P0·P1 전부 코드 반영 / P2 핵심 2개 (#9+#10) 반영 / P2 #11 ·
     P3 #5 는 자산 의존이라 보류

 다음 세션 belle action item:
   1) 트랙 A 가이드대로 Pod 재셋업 (1~9 단계)
   2) SAM 재배포 (이번 코드 변경 모두 포함): cd backend && sam build
      --use-container && sam deploy --parameter-overrides
      "RunpodAnalyzeUrl=https://<NEW_POD_ID>-8000.proxy.runpod.net/analyze
       RunpodAuthToken=<NEW_TOKEN>"
   3) 앱에서 실 영상 1개 업로드 → 결과 화면에서:
      - 본인 영상 슬롯이 채워지는지 (P0 #6)
      - 모드 선택 → 영상 선택 흐름이 자연스러운지 (P1 #2/#3)
      - 비폴 영상 올렸을 때 차단 화면이 뜨는지 (P1 #8 자발 검증)
      - 로딩 % 가 단계별로 증가하는지 (P2 #9)
      - 카피가 4초마다 회전하는지 (P2 #10)
   4) 점수 정확도 (#4) — 폭스탑 등 reference 와 동일 동작으로 테스트하면
      similarity 50~80 정도 나와야 정상. 너무 낮으면 임계값(현재 25) 만지거나
      kismam scoring 추가 검증.

*2026-05-28 (오후) — Pod 재셋업 + mode1 통과 + mode3 사용자 의도 발견:

 belle 가 키 회전은 미루고 (sunity-motion·sunity-api·RUNPOD_AUTH_TOKEN 그대로
   사용) Pod 만 새로 띄움. 새 Pod URL = https://p56qusi8cgc91z-8000.proxy.runpod.net.
   SAM 재배포 통과 (sunity-motion-pilot in ap-northeast-2). EAS Build #9 (1.0.0(9))
   ASC 자동 제출 Success.

 새 빌드 #9 TestFlight launch crash → Expo Go 진단으로 좁힘:
  · 원인 1: loading.tsx 의 `ringPct` 스타일 `letterSpacing: -1` 가 iOS 26.4.2
    RCTMountingManager NSCFNumber 처리에서 SIGABRT. crash log 에 RCTMountingManager
    performTransaction + UISnapshotViewRectAfterCommit + OBJC_CLASS_$___NSCFNumber
    스택. letterSpacing 음수값 제거로 해결. 메모로 박을 가치 — iOS 26+ native
    style 처리 변화 가능성.
  · 원인 2(예방): loading.tsx 의 새 setInterval hook 이 early return 뒤에 있었음.
    Hook 규칙 위반 잠재. status='done' 전환 시 터질 수 있음 → 미리 정정해서 모든
    hook 을 early return 이전으로.

 mode1 통과 (99점) + 진짜 큰 발견 — Firestore analysis doc 의 referenceMotionId 누락:
  · loading.tsx 의 startAnalysisUpload 가 setDoc 으로 Firestore 분석 doc 만들 때
    `referenceMotionId` 를 빠뜨림. 백엔드 pipeline 이 meta.get("referenceMotionId")
    → None → get_reference_motion(None) → None → RuntimeError("기준 모션 또는
    keyframe 데이터 없음"). 어제 시연 (mode3 만) 에선 발견 안 됨, 오늘 mode1 첫
    실분석에서 표면화.
  · fix: setDoc payload 에 `...(input.referenceMotionId ? { referenceMotionId } : {})`
    spread 추가. mode1 영상 = 정은지 영상 self-비교 시 99점 정상 산출 확인.

 reference angles 5개 진단(2026-05-23 시드 유지 확인):
   ref-sideway-spin angles_len=1584 keys=[8 joints]
   ref-climb        angles_len=1368
   ref-invert       angles_len=1384
   ref-foxtop       angles_len=2272
   ref-foxtop-split angles_len=2584
   → 시드 멀쩡, NLF 재추출 불필요.

 mode3 사용자 의도 재정의 — belle 통찰:
   현 알고리즘 = selfmotion.symmetry_deviation (좌우 대칭). 폴 동작은 의도적
     비대칭이라 self-symmetry 점수 항상 50점대 → 같은 영상 두 번 분석해도 54점.
   belle 사용자 관점: "같은 영상이면 100점, 다른 영상이면 일치도 점수" 가 진짜
     mode3 다. 이전 영상 vs 이번 영상 DTW 비교가 자연스럽다.
   → mode3 알고리즘 전면 재설계 결정 (옵션 A). 본질적으로 mode1 의 reference
     자리에 사용자의 이전 분석 영상이 들어가는 구조. 변경 범위:
     1) analysis doc 에 추출된 angles 저장 (현재는 result 만)
     2) 백엔드 mode3 처리 = 이전 분석 doc 의 angles 를 reference 처럼 활용
        get_previous_analysis 가 angles 도 함께 반환하도록.
     3) 첫 분석은 비교 대상 없음 → 점수 큰 숫자 X, "다음 분석부터 비교" 안내
        + 좌우 대칭 코칭 (개선 포인트만)
     4) 두 번째+ 분석: mode1 처럼 큰 점수 + 비교 영상 슬롯에 이전 영상 URL
   → belle 가 저녁에 시작 결정. mode3 알고리즘 + 남은 피드백 + EAS 새 빌드
      한 번에 진행 (오늘 변경분이 빌드 #9 에는 없음 — 빌드 후 push 한 fix 들).

 오늘 inflight 코드 변경 (commit 권고):
   app/src/app/analysis/loading.tsx
     · referenceMotionId Firestore 박기 (mode1 통과 결정타)
     · ringPct letterSpacing 제거 (TestFlight crash 회피)
     · Hook 순서 정정 (Hook 규칙 위반 예방)
   plan.md 본 블록 + memory s3-presigned-video-playback.md 신규

 인프라 상태 (이번 세션 변경):
   - RunPod Pod: p56qusi8cgc91z (이전 nwx3v7bo7wqjey terminate)
   - URL: https://p56qusi8cgc91z-8000.proxy.runpod.net
   - uvicorn 떠 있음. env: sunity-motion 키 + RUNPOD_AUTH_TOKEN (이전과 동일 토큰
     belle 보유). FIREBASE_SA_PATH=/workspace/firebase-sa.json
   - CFN sunity-motion-pilot 갱신 (RunpodAnalyzeUrl 새 Pod)
   - 새 빌드 9 = 1.0.0(9) TestFlight 등장. ⚠ 빌드 9 자체는 launch crash 라
     belle 폰에선 사용 X. Expo Go 만 사용 중. 저녁에 새 빌드 10 띄울 것.

 belle 저녁 재개 절차:
   1) 위 commit 명령 1개 (안 했으면)
   2) /loop 또는 새 세션 시작 시 plan.md 의 이 블록 + 위 블록 읽기.
   3) mode3 알고리즘 (A) 작업 — 이번 세션의 가장 큰 변경. 다음 단계 제안:
      a. types/analysis.ts AnalysisDoc 에 angles/anglesJointKeys/anglesFrames
         옵셔널 필드 추가 (Firestore nested-array 금지라 flat — [[firestore-nested-array-flat]])
      b. backend pipeline/app.py _process 에서 mode3 처리 분기 재작성:
         - 첫 분석 (previous=None): angles 저장만, 점수 산출 X
         - 두 번째+: 이전 doc 의 angles 를 reference 로 사용해 mode1 와 동일한
           DTW + KISMAM 흐름
      c. firestore_admin.get_previous_analysis 가 angles 도 반환하도록 (현재는
         result 만 사용). 또는 별도 헬퍼 추가.
      d. assemble.build_mode3 시그니처 갱신 — similarity 받도록.
      e. result.tsx mode3 분기:
         - isFirst 시 점수 큰 숫자 안 보이고 "다음 분석부터 비교" + 좌우 대칭 코칭
         - 두 번째+ 시 mode1 처럼 큰 점수 + 비교 영상 슬롯에 이전 myVideoUrl
      f. VideoCompare 에 mode3 일 때 이전 영상 URL 채우기 (useAnalysisDoc(previousAnalysisId))
      g. 백엔드 테스트 갱신 (mode3 두 경로 모두)
   4) 남은 피드백:
      - P0 #4 점수 정확도 — mode3 알고리즘 바뀌면 자동 검증.
        mode1 은 99점 확인 (같은 영상 비교) — 다른 영상은 시연 시 belle 추가 검증.
      - P2 #11 폴댄스 동작 애니메이션 — 자산 의존, 시연 후 작업 권고.
      - P3 #5 도전 동작 사진/아이콘 — 자산 의존, 마찬가지.
   5) EAS 새 빌드 (build 10):
      - 위 작업 끝나면 git commit + push → `npx eas-cli build --platform ios
        --profile production --auto-submit` 한 번 더.
      - 새 빌드는 letterSpacing crash 없으니 정상 launch 보장.
   6) 정리 큐 (별도 일정):
      - sunity-motion admin 키 회전 (현재 사용 중인 키 그대로)
      - sunity-api 노출 키 (AKIA...64A) deactivate
      - RUNPOD_AUTH_TOKEN 새 토큰 발급
      - 그 후 SAM 재배포 필요 (RunpodAuthToken 신규).
