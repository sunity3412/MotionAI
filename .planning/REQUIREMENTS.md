# Requirements: Sunity AI Coach

**Defined:** 2026-05-29
**Last restructured:** 2026-05-31 (research 3 docs 반영 + belle 결정 3건)
**Core Value:** 분석 정확도 — 점수가 믿을 만하고, 첫 분석이 "전문가 수준으로 구체적"이어야 한다. 수치는 보조, 원인이 핵심.

> 현장 니즈 출처: `docs/research/폴스포츠 수강생의 설문조사.md` (= 강사 설문조사.md, 동일 — 수강생 + 강사/운영자 통합). 시스템 아키텍처: `docs/research/00_시스템_아키텍처_FINAL.md`, `01_체형차이_보정엔진_FINAL.md`, `02_힘방향_힘조절_엔진_FINAL.md`.

## v1 Requirements

파일럿 MVP done 기준. 현장 리서치 P0 + research 3 docs + belle 확정 스코프. 각 요구사항은 로드맵 phase에 매핑된다.

> **분석 동작 제약**: 초기 분석은 3~5개 동작군(후굴 계열·인버트 계열·특정 기본 포징)으로 한정한다. 모든 동작을 한 번에 분석하는 범용 모델 금지.

> **belle 결정 (2026-05-31)**:
> - **상용/베타 제품 포즈 엔진 = MediaPipe + Gemini** (Apache 2.0, 라이선스 리스크 0).
> - **NLF/SMPL-X (입수처: https://is.mpg.de/ps/code, https://smpl-x.is.tue.mpg.de) = 라이선스 확인 전까지 실제 제품 코드에 넣지 않고, 내부 비상업 R&D 비교군으로만 사용.** 사용 환경 = 사내 R&D 노트북/RunPod, 공개 베타·유료 파일럿·고객 영상 처리 금지.
> - PoseEngine 인터페이스 추상화 — `MediaPipePoseEngine`(제품 코드) + `NlfPoseEngine`(R&D 비교군) 어댑터 둘 다 운영. 교체 = config 플래그.
> - NLF/SMPL-X 라이선스 = PS:License 1.0 (비상업) 사내 평가만. 출시 전 사용 시 Max Planck Innovation 상업 라이선스 (`info@max-planck-innovation.de`) 클리어 필수.
> - 데이터셋 AMASS/BEDLAM2.0/AGORA = R&D 평가 벤치마크 (비상업).
> - coaching 모드 기본 + judging 모드(IPSF 기하 점검) 옵션 → v1.5 분리, 데이터 수집은 v1 평행.
> - 다중 시점 촬영 UX는 v1 포함 (occlusion 완화).
> - 힘은 패턴 추론만, 측정 X. 모든 결과에 코치 훅 + confidence 항상 출력.

### 공통 레이어 (Common Layer)

- [ ] **POSE-01**: 상용 제품 코드의 포즈 엔진이 NLF → MediaPipe로 마이그레이션되고 `PoseEngine` 인터페이스 + 공통 계약(`PoseFrame`)이 도입된다. `NlfPoseEngine` 어댑터는 R&D 비교군으로 격리되어 제품 파이프라인 import 경로에서 제거되고 사내 평가 스크립트에서만 호출된다 (라이선스 리스크 0)
- [ ] **POSE-02**: 폴 축이 자동 검출되고 모든 키포인트가 폴 기준 좌표계로 정렬되며, 가림 프레임은 confidence 낮음으로 표기되어 후속 분석이 단정하지 않는다 (스피닝 폴은 v1.5)
- [ ] **POSE-03**: 사용자가 다중 시점(정면+측면) 영상을 업로드할 수 있고, 키포인트 confidence 임계값 미만 프레임은 "추정" 표기 + 결과 화면에 occlusion 경고 표시
- [ ] **BODY-01**: RTMW 133 wholebody 키포인트로부터 신체 segment 길이·비율·좌우 비대칭이 자동 추출되어 `BodyNormalizationProfile`(키·팔/다리/몸통 스케일·어깨/골반 비율·confidence·warnings)이 두 엔진의 공유 입력으로 산출된다. SMPL-X β 비교군은 R&D 평가 스크립트에서만 갭 보고 (제품 코드 비호출)
- [ ] **BODY-02**: 사용자가 키·몸무게·경력·통증부위·우세손을 1회 입력하고 분석에 BodyProfile이 함께 전달된다. weightKg는 보조 정보로만 사용, 유연성·근력 자가입력은 받지 않음(부정확)

### 점수 신뢰도 (Scoring)

- [ ] **SCORE-01**: 기술 인식기(Gemini 어댑터)가 영상에서 기술을 인식하고 관절별 EXTEND/BENT 프로파일을 반환하며, Gemini는 분류·자연어 번역만 (좌표·판단 출력 금지)
- [ ] **SCORE-04**: 고수(정은지) 영상이 위양성 감점 없이 신뢰할 만한 점수로 산출되고, 다양한 영상에서 인체 추적·분석이 정확하다 (신뢰도 게이트 — 강사/운영자 신뢰의 핵심)
- [ ] **SCORE-05**: 5트랙 채점 시스템 v1 — IPSF 4공식 트랙 중 (a) Compulsory Criteria + (c) Technical Deduction 두 트랙 + Page 9 "all components" 절대 공통 트랙이 작동한다. 동작 인식 성공/실패/비등재/자유 루틴 모든 케이스에서 Page 9 절대 트랙 단독으로도 자세 품질 채점이 가능하다 (mode3 reference 없는 채점의 IPSF 공식 근거). (b) Tech Bonus 연계 가산 + (d) Artistic 정성 평가는 v2. (출처: IPSF Pole Sports CoP 2021-2024 Page 9 / NotebookLM lookup 2026-06-02)

### 학원 용어 (Studio Terminology)

- [ ] **TERM-01**: 학원 용어 3분기 시스템이 작동한다. 분기 1 — AKA 매핑 (IPSF 등재 + 한국 학원 통용 매핑된 동작) → IPSF Code + Criteria 정밀 채점. 분기 2 — 한국 학원 통용 (정은지 reference 보유 비등재 동작, 예: 폭스탑) → 정은지 측정값 기준 + Page 9 절대 트랙. 분기 3 — 미등재 + 자동 수집 → Page 9 단독 + UX 카피 노출 + 키워드/영상 익명 박제. (현장 니즈: 강사 5-1 "기본기 표준화" + 운영자 5-2 "기술 데이터 표준화" + 운영자 5-2 "폭스탑 3회 분석 예시")
- [ ] **TERM-DATA-01**: 학원 용어 매핑 데이터 v1 박제 — (1) AKA 매핑 13개 (NotebookLM lookup 2026-06-02 출처: 나비/큐피드/펜실/데드리프트/스콜피오/제미니/숄더마운트/아이샤/제이드스플릿/아이언엑스/테디/플랫라인/요기니) + 각 IPSF Code + Criteria source_ref. (2) 분기 2 정은지 reference 보유 비등재 동작 1~2개 (폭스탑 우선). (3) 분기 3 자동 수집 데이터 스키마 — 입력 키워드 + 사용자 익명 ID + 누적 카운트. belle/강사 협업 없이 NotebookLM lookup + 정은지 영상으로 박제 가능 (사람 점수 라벨링 X — analysis-objectivity 정합)
- [ ] **TERM-COPY-01**: 분기 3 UX 카피가 belle 작성 그대로 박제되어 노출된다 — "공식 등재되어 있지 않은 기술명입니다. 서니티는 국제 대회 기준 명칭을 기준으로 평가하며 추가로 학원에서 등록된 명칭을 사용합니다. 귀하께서 입력한 기술 키워드는 지금 바로 '자동 수집' 되었으며 하나의 학원 이상에서 사용하는 기술임이 확인되면 업데이트 예정입니다." 변경/요약/재가공 금지

### 개인화 (Personalization) — research 01

- [x] **PERS-01**: 체형 정규화 비교 엔진(`normalizeStudentPoseToProReference`)이 프로의 동작 성공 원리를 수강생 신체 비율에 맞게 재계산하고, 차이를 "체형 허용 / 개선 필요 / uncertain"으로 분류한다 — coaching 모드 정규화 ON
- [ ] **PERS-03**: 실패 원인·체형 차이별로 매핑된 보완 운동·스트레칭 라이브러리가 결과 화면에 동작별 3~5개 표시되어 분석 → 행동으로 이어진다

### 힘 패턴 (Force Pattern) — research 02

- [x] **FORCE-01**: 중심축 이탈·접촉점 안정성·jerk/jitter 기초 신호로부터 ForceDirectionPattern(pull/push/brace/rotate/release)이 phase별로 추론되고, 동작 실패 원인 후보 상위 3개가 카드 형태로 제시된다. "근육 힘 방향" 단정 금지 — 모두 "가능성"으로 표기

### 안전 (Safety)

- [ ] **SAFE-01**: 좌우 비대칭·요추 과신전·레벨 대비 무리한 동작 신호가 위험도 플래그로 결과 화면에 표시되고 "전문가 확인 권유" 카피가 함께 표시된다. "부상 확정" 단정 금지

### 피드백·코치 훅 (Feedback & Coach Hook)

- [ ] **FEED-01**: 결과 화면에 관절 각도 수치가 "현재 87° → 기준 110°" 형태로 명확히 표시되고 영상 위에 어깨·골반·무릎·손 키포인트와 중심축이 오버레이로 표시된다
- [ ] **FEED-02**: 피드백이 "실패 원인 후보 3개 카드 → 내 몸 기준 힘 쓰는 방향·중심축 → 필요한 유연성/근력 → 보조 동작" 순서로 구성되고 부위별 언어(고관절·후굴·코어·내전근·전완근·광배 등)로 표현된다 (수치는 보조)
- [ ] **FEED-03**: 결과 화면 카피가 AI를 "강사 보조 도구"로 포지셔닝한다 (AI가 강사를 대체한다는 인상 제거)
- [ ] **COACH-01**: 모든 리포트(BodyComparisonReport, ForcePatternInference 등)에 `CoachCommentHook`(autoFindingsSummary, openQuestionsForCoach, suggestedCues, coachComment?, reviewedBy)이 부착되어 AI+코치 비즈니스 모델의 데이터 구조 기반이 마련된다. UI/입력은 v2 옵션

### 분석 모드 (Modes)

- [ ] **MODE-01**: 사용자가 정은지 기준 모션을 불러와 본인 영상과 비교하고 전문가 기준 점수를 실영상으로 end-to-end 확인할 수 있다 (Mode 1 — coaching 모드 + champion_reference)
- [ ] **MODE-02**: 사용자가 본인 영상 2개를 비교해 발전(progress)을 실영상으로 end-to-end 확인할 수 있다 (Mode 3 — coaching 모드 + self_progress)

### 기준 모션 (Reference)

- [ ] **REF-01**: 정은지 기준 모션을 다각도 캡처 프로토콜에 따라 등록할 수 있고, 등록 경로는 비교 분석 정확도가 최대화되는 방식(촬영 조건/앵글 통제 + BodyNormalizationProfile·EXTEND·ForceDirectionPattern 포함)으로 설계된다

### 전달 (Delivery)

- [ ] **DELIV-01**: 수강생이 TestFlight 게스트 모드에서 회원가입 없이 Mode 1 + Mode 3를 혼자 실기기로 완주할 수 있다

## v1.5 Requirements (별도 마일스톤, 데이터 수집은 v1 평행)

- **JUDGE-01**: IPSF Code of Points 절대 기준으로 기하 점검(무릎-발끝 정렬·발끝 포인트·라인·홀드)이 동작하고 `JudgingModeReport`가 "예술 점수 제외, 기술 점검" 디스클레이머와 함께 렌더된다 (judging 모드, 정규화 OFF). **SCORE-05 5트랙의 (a) Compulsory Criteria 정밀 채점이 judging 모드 코드 path 의 본체**
- **JUDGE-DATA-01** *(v1 평행 데이터 수집)*: 3~5개 동작 × phase별 `GeometricCriterion`(targetValue, toleranceFull, deductionPerStep, minimumRequirement) 라벨링 — belle/강사 협업. **TERM-DATA-01 의 AKA 매핑 13개 + 정은지 reference 1~2개와 평행 진행. 데이터 형식 동일 (GeometricCriterion)**

## v2 Requirements

향후 릴리스로 연기. 추적하되 현 로드맵에는 없음.

### 개인화 확장 (Personalization Expansion)

- **PERS-02**: 동작별 타깃 근육 시각화 (영상 위 muscle activation 추정 표시)

### 챔피언 레퍼런스 (Champion Reference Moat — research 0.8)

- **EMG-01**: 챔피언 EMG (Delsys/Noraxon/Athos) + 접촉력 (Tekscan) + 3D 모션캡처 (Theia3D/Vicon) 동작당 1회 캡처해 레퍼런스 라이브러리 구축 (해자 데이터셋)
- **EMG-02**: 챔피언 EMG 레퍼런스 기반 "근육 힘 방향" 단정 (v1은 추정만, v2는 측정 기반)
- **FORCE-V2-01**: push/pull/brace/rotate/release 패턴 자동 분류 학습 모델

### 측정 확장 (Measurement Expansion)

- **POSE-V2-01**: 측정 차원 확장 — 정렬(무릎-발끝)·자세(머리)·발끝 toe/head keypoint 위한 포즈 데이터 업그레이드
- **CAM-V2-01**: 카메라 앵글 합성(CameraCtrl II / UCPE)으로 시점 보정·코치뷰·데이터 증강
- **OCCLUSION-V2-01**: 사선/뒤 시점 다중 시점 + 시점 자동 매핑

### 학원/운영 (Studio Ops) — P2

- **OPS-01**: 학원 운영자 대시보드 — 수강생 성장 DB 일괄 조회 + 강사용 리포트
- **OPS-02**: 분석 자료 공유 제한 — 학원별 데이터 격리, 강사/수강생 권한 분리
- **EXPERT-01**: 전문가(강사) 코멘트 UI/입력 — 강사가 수강생 분석에 코멘트를 첨부 (CoachCommentHook의 UI 레이어, 프리미엄 티어)
- **CHAMP-COMMENT-01**: 세계 챔피언 코멘트 옵션 (럭셔리 티어 — research 0.5)
- **PRIV-01**: 프라이버시 설명 화면 — 영상 처리 흐름 + 삭제 시점 명시
- **GROW-01**: 같은 동작 반복 분석의 회차별 개선 그래프 ("폭스탑 62→71→78점")
- **DLVR-02**: 영상 인앱 다운로드 (CloudFront 서명 URL 기반 — 운영자 요청)

### 5트랙 채점 확장 (Scoring V2 — Out of Scope for v1)

- **SCORE-V2-02**: IPSF (b) Technical Bonus 연계 가산 자동 인식 — Dynamic Combinations (조합당 +0.5, max +3.0) + Combining Spins (결합당 +0.5~+1.0, max +2.0~+3.0). 동작 인식기 + 연계 인식기 둘 다 필요. (출처: IPSF Mid-Cycle Update Appendix 2024 Page 5, CoP 2025-2027 Page 16)
- **SCORE-V2-03**: IPSF (d) Artistic & Choreography 측정 가능 영역 — Flow (max +2.0, jerk + 멈춤 감지) + Stage Usage (위치 추적 → 무대 점유율). 정성 영역 (Musicality / Charisma / Theme / Originality 본질) 은 코치/심사위원 영역으로 영구 분리. (출처: IPSF Aerial Pole CoP 2024-2025 Page 12, Pole Sports CoP 2025-2027 Page 4)

### 학원 용어 확장 (Terminology V2 — Out of Scope for v1)

- **TERM-V2-01**: 다국 alias 풀 구현 — motionId 에 `aliases.ipsf_code` / `aliases.ipsf_name` / `aliases.kpsa_name` / `aliases.coach_variants` / `aliases.competition_variants` 신설. 사용자가 "학원 / 코치 / 대회" 모드 선택 시 해당 명칭 표시. (출처: [[terminology-multimap-future]] 2026-06-01 박제)
- **TERM-V2-02**: 분기 3 자동 수집 → 표준화 승격 알고리즘 — 누적 카운트 threshold + NotebookLM batch lookup 자동화 + 정은지 reference 우선순위 큐. KPSA 한국어 표준 작성 협업 path (강사 5-1 "기본기 표준화" 니즈 충족, 우리가 한국 최초 표준 후보 작성)

## Out of Scope

명시적 제외. 스코프 크리프 방지용.

| Feature | Reason |
|---------|--------|
| 결제/구독 (RevenueCat) | 파일럿은 과금 없음 |
| 회원가입 강제 | 게스트 모드로 충분 — 북극성은 "혼자 켜고 확인" |
| 회전 360° / 모멘텀 / 예술성 차원 | 현 NLF 파이프라인 범위 밖 |
| 다크 모드 | 라이트 전용 (design.md) |
| 영상 공개 기반 커뮤니티 랭킹 | 개인정보·신체 노출 우려 (현장 안티패턴) |
| 월 구독형 B2C 앱 단독 출시 | B2B 학원 우선 — 단독 출시 시 정확도 논란·전문가 반발 동시 위험 |
| 프로 자세 단순 유사도 비교 | 기술/원인 기반이어야 함 — 단순 유사도는 강사 철학과 충돌 |
| 모든 동작 한 번에 분석하는 범용 모델 | 초기 3~5개 동작군으로 한정 (범용은 실패 가능성 큼) |
| 영상만으로 근육량/근력/근육 힘 방향 단정 | research 0.4 — EMG 없이 불가. v1은 "추정" 표기만 |
| 온-폴 inverse dynamics 근력 측정 | research 02 §0.6 — 그립 외력 모델링 불가. 약속 금지 |
| AI 단독 코칭 (코치 마무리 없음) | research 0.5 — 고객·강사 모두 AI 단독 판단 불신. CoachCommentHook 필수 |
| Gemini가 좌표·판단·점수 출력 | research 00 §3 — Gemini는 자연어 번역 엔진. 판단은 운동학 휴리스틱 + 코치 |
| 자동 점수를 "대회 총점"으로 표기 | research 01 §2.1 — 예술 점수 미포함, "기술 점검"으로만 |
| NLF/SMPL-X를 상용/베타 제품 코드에 포함 | belle 결정 (2026-05-31) — 라이선스 확인 전까지 제품 사용 금지. R&D 비교군 전용 |
| NLF/SMPL-X로 공개 베타·유료 파일럿·고객 영상 처리 | PS:License 1.0(비상업) 범위 위반. 상업 라이선스 클리어 후만 가능 |

> 참고: CloudFront는 당초 제외였으나 운영자의 영상 다운로드 니즈로 v2(DLVR-02)에 편입.

## Traceability

어느 phase가 어느 요구사항을 커버하는지.

| Requirement | Phase | Status |
|-------------|-------|--------|
| POSE-01 | Phase 1 | Pending |
| POSE-02 | Phase 1 | Pending |
| BODY-01 | Phase 2 | Pending |
| BODY-02 | Phase 3 | Pending |
| POSE-03 | Phase 4 | Pending |
| SCORE-01 | Phase 5 | Pending |
| PERS-01 | Phase 6, Phase 7 | Complete |
| FORCE-01 | Phase 8, Phase 9 | Complete |
| FEED-02 | Phase 9, Phase 11 | Pending |
| SAFE-01 | Phase 10 | Pending |
| COACH-01 | Phase 11 | Pending |
| FEED-03 | Phase 11 | Pending |
| FEED-01 | Phase 12 | Pending |
| VIS-01 | Phase 12 | Pending |
| PERS-03 | Phase 13 | Pending |
| REF-01 | Phase 14 | Pending |
| MODE-01 | Phase 15 | Pending |
| MODE-02 | Phase 15 | Pending |
| SCORE-04 | Phase 15 | Pending |
| DELIV-01 | Phase 15 | Pending |
| SCORE-05 | Phase 16 | Pending |
| TERM-01 | Phase 16 | Pending |
| TERM-DATA-01 | Phase 16 | Pending |
| TERM-COPY-01 | Phase 16 | Pending |

**Coverage:**
- v1 requirements: 22 total (18 → 22, +4 신설 2026-06-02)
- Mapped to phases: 22 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-29*
*Last updated: 2026-05-31 — research 3 docs 통합, v2→v1 승격 (PERS-01·SAFE-01·PERS-03), 신규 v1 (POSE-02·03·BODY-01·02·COACH-01·FORCE-01), v1.5 분리 (judging 모드)*
*Updated 2026-05-31 — belle 결정: 상용/베타 = MediaPipe + Gemini, NLF/SMPL-X = R&D 비교군. POSE-01 신규 추가 (PoseEngine 추상화 + MediaPipe 마이그레이션 + NLF 격리), BODY-01 재정의 (MediaPipe segment 기반)*
*Updated 2026-06-02 — belle 결정: 학원 용어 3분기 시스템 + 5트랙 채점 (IPSF 4공식 + Page 9 절대 공통). NotebookLM IPSF CoP 2024-2025 / 2025-2027 lookup 결과 박제 — Element Code Matching IPSF 룰 (page 138-139), Page 9 "all components" 절대 트랙 (CoP 2021-2024), Dynamic Combinations / Flow 트랙, AKA 13개 매핑 (한국 학원 ↔ IPSF Code). v1 신설 SCORE-05/TERM-01/TERM-DATA-01/TERM-COPY-01. v2 신설 SCORE-V2-02/03 + TERM-V2-01/02. Phase 16 신설. 현장 설문 강사 5-1 "기본기 표준화" + 운영자 5-2 "기술 데이터 표준화" + "폭스탑 3회 분석 예시" 직접 충족*
*Updated 2026-06-07 — Phase 2 plan 01 RTMW pivot 정합 (BODY-01 MediaPipe → RTMW 갱신, v4/v5 박제).*
*Updated 2026-06-08 — Phase 2 plan 01 RTMW pivot 2차 정합: BODY-01 의 "SMPL-X β 비교군은 R&D 평가 스크립트에서만 갭 보고" 문구는 ROADMAP §4 (SMPL-X 비교) 폐기와 함께 R&D scope 에서도 last-resort 만 (paid commercial license — PS:License 1.0). 운영 path 는 RTMW-native 단일.*
