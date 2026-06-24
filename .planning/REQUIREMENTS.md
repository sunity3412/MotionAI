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
- [x] **POSE-03**: (2026-06-13 Camera Angle AI pivot — `.planning/phases/04-ux-occlusion-confidence/04-CONTEXT.md` D-01 정합) 사용자는 1 영상만 업로드하고, 백엔드가 confidence 미달 구간/가려진 관절만 AI 가상 시점으로 핀포인트 보완(재추론·병합)한다. 키포인트 confidence 임계값 미만 프레임은 "추정" 표기 + 결과 화면에 occlusion 경고 표시, 합성 실패 시 graceful degrade + 정확도 제한 표기. (구 "다중 시점 직접 업로드 UX" 는 영구 폐기 — D-01)
- [ ] **BODY-01**: RTMW 133 wholebody 키포인트로부터 신체 segment 길이·비율·좌우 비대칭이 자동 추출되어 `BodyNormalizationProfile`(키·팔/다리/몸통 스케일·어깨/골반 비율·confidence·warnings)이 두 엔진의 공유 입력으로 산출된다. SMPL-X β 비교군은 R&D 평가 스크립트에서만 갭 보고 (제품 코드 비호출)
- [x] **BODY-02**: 사용자가 키·몸무게·경력·통증부위·우세손을 1회 입력하고 분석에 BodyProfile이 함께 전달된다. weightKg는 보조 정보로만 사용, 유연성·근력 자가입력은 받지 않음(부정확)

### 점수 신뢰도 (Scoring)

- [ ] **SCORE-01**: 기술 인식기(Gemini 어댑터)가 영상에서 기술을 인식하고 관절별 EXTEND/BENT 프로파일을 반환하며, Gemini는 분류·자연어 번역만 (좌표·판단 출력 금지)
- [x] **SCORE-04**: 고수(정은지) 영상이 위양성 감점 없이 신뢰할 만한 점수로 산출되고, 다양한 영상에서 인체 추적·분석이 정확하다 (신뢰도 게이트 — 강사/운영자 신뢰의 핵심)
- [ ] **SCORE-05**: 5트랙 채점 시스템 v1 — IPSF 4공식 트랙 중 (a) Compulsory Criteria + (c) Technical Deduction 두 트랙 + Page 9 "all components" 절대 공통 트랙이 작동한다. 동작 인식 성공/실패/비등재/자유 루틴 모든 케이스에서 Page 9 절대 트랙 단독으로도 자세 품질 채점이 가능하다 (mode3 reference 없는 채점의 IPSF 공식 근거). (b) Tech Bonus 연계 가산 + (d) Artistic 정성 평가는 v2. (출처: IPSF Pole Sports CoP 2021-2024 Page 9 / NotebookLM lookup 2026-06-02)

- [x] **SCORE-06**: 종합·차원 점수가 감점식(deduction)으로 집계되어 단일 major fault가 종합을 지배한다 — 이중 단순평균(`kismam.overall_score` 가중평균 + `dimensions.overall_from_dimensions` 단순평균) 폐기. 100에서 시작 → IPSF 트랙(요소 0점 + 누적 실행 감점) 비율 매핑으로 감점. D-05 6 앵커(모두 fault 영상)가 낮은 종합점수를, above-cutoff 케이스는 높은 점수를 받는다. 감점 임계는 IPSF 근거(19-IPSF-DEDUCTION-NOTES §A)에서만 — 보유 sweep 재calibrate 금지. (출처: Phase 15 실증 94점 위양성 + IPSF CoP 2021-2027 / [[calibration-source-hard-gate]] [[judging-baseline-ipsf-code-of-points]])
- [x] **SCORE-07**: "Fully Extended" 요소의 micro-bent 0점 트랙 — 신전 요구 관절(`profile.expects_extension` True)이 IPSF 임계(스플릿 160°=목표 180°−20° tol) 미달이면 해당 요소 무효(0점, 비례감점 아님). 의도적 굽힘(expects_extension False)은 미적용(위양성 차단). 임계는 IPSF 근거에서만. (출처: 19-IPSF-DEDUCTION-NOTES §A 트랙1)
- [x] **SCORE-08** (Phase 20 — v2 비전 거부권; still-frame regression subset = Phase 23-03): Gemini 시각 거부권이 채점 path(`_apply_vision_veto`)에 통합되어 v1 감점식 종합점수(`overallScore`)를 **하향만** 조정한다 (절대 못 올림 — `min()` cap, 가중블렌드/하한 거부 금지). 단위 = worst-pose(지배 결함 pose, key_moments 재사용, IPSF phase 평균 거부), 범위 = Mode1 + Mode3 둘 다, 트리거 = 채점 path 에 항상 호출. fault-free 정타 → v1 그대로(95~100 유지). **veto 입력이 whole-video → still-frame 으로 바뀌면서 cap(50/75/90 불변) regression 게이트의 still-frame 검증은 Phase 23-03 이 OWN (D-14): 정은지 95~100 / kip-up fault = moderate 점수 ≤75(20-04 evidence 75/moderate 와 일치) / EVAL18 변별 4쌍 퇴행0.** (출처: D-01/03/04/05, 20-CONTEXT.md / 23-CONTEXT.md D-14 / [[score-spec-95-100-elite-vision-fix]] / [[vision-score-must-analyze-not-stamp]])
- [ ] **SCORE-09** (Phase 20 → Phase 24 — 일반화 hard gate, PENDING; Phase 24 가 게이트 본체를 mint): SCORE-08 의 severity→cap 수치가 6페어 curve-fit 이 아니라 generalization-tested eval(미보유 + above-cutoff sensitivity 셋 포함)로 도출된다. 6페어 = known-answer 회귀(검증), fit 타깃 아님. 위양성(fault 하락)↔위음성(above-cutoff 유지) 양방 게이트. **소유권 (belle 2026-06-23, D-14 amended ITERATION6): SCORE-09 는 Phase 23-03 가 흡수하지 않는다 — 별도 pending 으로 Phase 20 / 후속에 잔류한다.** 23-03 가 흡수한 것은 still-frame SEVERITY_CAP *regression subset*(SCORE-08 cap + TRUST-06 결정론)뿐이며, SCORE-09 의 sensitivity/generalization(미보유+above-cutoff 양방검증, diversity floor)은 still 흡수되지 않았다. **SCORE-09 미처리로 Phase 23 을 닫거나 20-04 를 SCORE-09 채로 superseded 처리 금지.** **Phase 24 정합 (2026-06-24, ND-07): severity→cap 자체가 제거되므로 SCORE-09 는 "감점-합산 엔진의 일반화 게이트"로 재해석 — phase24 assert_gates.py 의 generalization 게이트(6페어 false-pos/false-neg pure-partial + 미보유·above-cutoff Pod-serial deferred)가 본체.** (출처: D-02, 20-CONTEXT.md / 23-CONTEXT.md D-14·D-15 / [[scoring-redesign-must-generalize-no-overfit]] [[sensitivity-gate-not-just-elite-low]])
- [ ] **SCORE-10** (Phase 24 — 감점 엔진 교체): `vision_veto.SEVERITY_CAP` + `apply_downward_cap` + `SEVERITY_CAP_PROVENANCE`(severity→고정천장 밴드) 가 제거되고, `점수 = baseline(100) − Σ(criterion별 측정편차×명시규칙 감점)` 투명 tally 엔진(`deduction_engine.tally`)으로 교체된다. 최종점수의 유일한 clamp 는 `max(0, …)` — `min(100, …)` 또는 severity→고정천장 금지. 엔진은 `_apply_vision_veto` seam 한 곳에서 통합(분기 0, 코드 1벌). (출처: 24-CONTEXT.md ND-01 / [[scoring-must-be-transparent-deduction-tally]])
- [ ] **SCORE-11** (Phase 24 — 감점 규칙 = 기하 tolerance 확장): criterion별 감점 = 측정편차 → dead-zone(tolerance 안=0감점) → 단일 slope 곡선, **모든 영상 동일 slope**(curve-fit 금지). `dimensions._LINE_TOL_DEG` / `kismam._PENALTY_PER_DEG=1.2` 정합 — slope/cap 수치는 `[ASSUMED]` 엔지니어링 파라미터(IPSF 는 fixed-flat 이라 per-degree 곡선은 단조성 게이트용 의도적 divergence), 160°-split 0-fail + 20° tolerance 는 `[CITED: 19-IPSF §A]`. (출처: 24-CONTEXT.md ND-03 / 24-RESEARCH IPSF §2 / [[scoring-redesign-must-generalize-no-overfit]])
- [ ] **SCORE-12** (Phase 24 — criterion 묶음 + per-fault IPSF 상한 + 합산): 상관 관절은 IPSF criterion 으로 묶어 1회 측정(양다리 = leg_extension 1 criterion → 30°+30° 가 −60 폭주 안 됨). criterion 감점은 그 fault 의 IPSF severity 가중치(fault 종류별 규칙, 영상 무관, **최종점수 밴드 아님**)로 상한, **합산**(평균 금지 — 희석 방지). 원 20-D05 worst-pose 지배를 합산 구조로 supersede. (출처: 24-CONTEXT.md ND-04 / 24-RESEARCH IPSF §1·§3)
- [ ] **SCORE-13** (Phase 24 — Gemini 강등): Gemini 는 점수를 절대 내지 않는다 — `gemini_vision_scorer` severity enum 이 "cap 입력"에서 "측정대상 지목 + criterion 식별"로 의미 재해석(어댑터 코드/schema 변경 0, 소비측 해석만 변경). severity 값이 점수 산술에 절대 진입하지 않는다. (출처: 24-CONTEXT.md ND-02 / [[vision-score-must-analyze-not-stamp]])
- [ ] **SCORE-14** (Phase 24 — baseline 분기 1급 입력): `baseline_kind`(floor / pole_vertical / hip_line, `vision_veto.BASELINE_KINDS` 재사용)가 측정 토대로 1급 입력된다. 사용자 선택 코치 동작 = 100, IPSF 공식 등재 동작 → IPSF 심사기준(20-D07 3분기 일반화). Mode3 = 절대지표 세션간 델타. (출처: 24-CONTEXT.md ND-05 / 24-RESEARCH IPSF §5 / [[output-needs-baselined-quantification-layer]] [[mode3-progress-not-similarity]])
- [ ] **SCORE-15** (Phase 24 — 측정불가 결함 매핑 강제 + coverage-gap 로그): Gemini 가 짚은 모든 결함은 기하 측정항으로 변환되어 감점된다. 규칙 미작성 시 임시로만 감점 0 + `coverageGap` audit 로그(자의적 밴드 주입 절대 금지). 출하 경로에 "보이는데 0감점" 0(coverage gap 로그로 검출·계수). (출처: 24-CONTEXT.md ND-06)
- [ ] **SCORE-16** (Phase 24 — 보고서 감점내역 계산·저장 + 신규 eval 게이트): 모든 −점이 명명된 측정편차 + 명명된 규칙으로 100% 역산되는 `deductionBreakdown`(criterion별 measured/baseline/deviation/ruleId/points/ipsfAnchor) 이 백엔드에서 계산·저장(Firestore flat list-of-dicts, 3-way 계약 lockstep; 앱 표시는 후속 UI phase). 케이스별 기대점수 manifest 제거 → 신규 게이트 = 추적성 + 단조성 + 결정성 + 일반화. (출처: 24-CONTEXT.md ND-07 / 23-03 흡수분 정정)
- [x] **TRUST-06** (Phase 20 — 결정론; still-frame regression subset = Phase 23-03): Gemini 시각 거부권 + 인식기 호출이 결정론적이다 — temperature 0 + reference/video-hash 별 profile 캐싱(TechniqueCache 재사용) 으로 같은 입력=같은 하향 cap. temp 0 단독은 bit-deterministic 아님 — 캐시가 실 보장. **still-frame veto 경로의 최종 점수 결정론(cold+warm 분리)은 Phase 23-03 이 OWN·검증 (D-14).** (출처: D-06, 20-CONTEXT.md / 23-CONTEXT.md D-14 / 20-RESEARCH Pitfall 2)
- [x] **TRUST-07** (Phase 20 — Mode3 미보유 게이트): Mode3 미보유동작이 Gemini 인식기 3분기(IPSF등재 ipsfCode / 정은지보유 reference / 둘다미보유→억제)로 판정되어, 미보유(분기3) 시 confident 점수가 억제되고 "기준 없음" 근거가 산출된다. not_pole 안전망을 reference-free 절대트랙으로 확장(MODE_EXPERT 전용 아님). fail-closed/raise 금지. (출처: D-07/08, 20-CONTEXT.md / [[mode3-scoring-basis-unknown-move-gate]])
- [x] **TRUST-08** (Phase 20 — 거부권/게이트 가시화 + 무음실패 방지): SCORE-08 의 거부권 결과(severity, capApplied → Phase 24 에서 `tallyFinal` 로 이관)가 `visionVeto` audit 필드로 직렬화되고(3-way 계약 lockstep), Mode3 미보유 시 결과 화면이 confident 점수를 억제 + scoringBasisLabel 을 표시한다. veto 가 adapter 실패로 silent no-op 되지 않게 WARNING 로그 + audit 필드로 관측 가능(Pitfall 5). 객관성: 비전 출력에 사람 점수 라벨/score 필드 0(임계값 수치 라벨링은 OK). (출처: D-08, 20-CONTEXT.md / 20-RESEARCH Pitfall 5 / [[analysis-objectivity-no-human-scores]])

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
- [x] **FEED-02**: 피드백이 "실패 원인 후보 3개 카드 → 내 몸 기준 힘 쓰는 방향·중심축 → 필요한 유연성/근력 → 보조 동작" 순서로 구성되고 부위별 언어(고관절·후굴·코어·내전근·전완근·광배 등)로 표현된다 (수치는 보조)
- [x] **FEED-03**: 결과 화면 카피가 AI를 "강사 보조 도구"로 포지셔닝한다 (AI가 강사를 대체한다는 인상 제거)
- [x] **COACH-01**: 모든 리포트(BodyComparisonReport, ForcePatternInference 등)에 `CoachCommentHook`(autoFindingsSummary, openQuestionsForCoach, suggestedCues, coachComment?, reviewedBy)이 부착되어 AI+코치 비즈니스 모델의 데이터 구조 기반이 마련된다. UI/입력은 v2 옵션

### 분석 모드 (Modes)

- [x] **MODE-01**: 사용자가 정은지 기준 모션을 불러와 본인 영상과 비교하고 전문가 기준 점수를 실영상으로 end-to-end 확인할 수 있다 (Mode 1 — coaching 모드 + champion_reference)
- [x] **MODE-02**: 사용자가 본인 영상 2개를 비교해 발전(progress)을 실영상으로 end-to-end 확인할 수 있다 (Mode 3 — coaching 모드 + self_progress)

### 기준 모션 (Reference)

- [x] **REF-01**: 정은지 기준 모션을 다각도 캡처 프로토콜에 따라 등록할 수 있고, 등록 경로는 비교 분석 정확도가 최대화되는 방식(촬영 조건/앵글 통제 + BodyNormalizationProfile·EXTEND·ForceDirectionPattern 포함)으로 설계된다 (Phase 14 완료 2026-06-15 — 11/11 reference 백필 + active pose 불변 증명)

### 전달 (Delivery)

- [ ] **DELIV-01**: 수강생이 TestFlight 게스트 모드에서 회원가입 없이 Mode 1 + Mode 3를 혼자 실기기로 완주할 수 있다

## v1.5 Requirements (별도 마일스톤, 데이터 수집은 v1 평행)

- **JUDGE-01**: IPSF Code of Points 절대 기준으로 기하 점검(무릎-발끝 정렬·발끝 포인트·라인·홀드)이 동작하고 `JudgingModeReport`가 "예술 점수 제외, 기술 점검" 디스클레이머와 함께 렌더된다 (judging 모드, 정규화 OFF). **SCORE-05 5트랙의 (a) Compulsory Criteria 정밀 채점이 judging 모드 코드 path 의 본체**
- **JUDGE-DATA-01** *(v1 평행 데이터 수집)*: 3~5개 동작 × phase별 `GeometricCriterion`(targetValue, toleranceFull, deductionPerStep, minimumRequirement) 라벨링 — belle/강사 협업. **TERM-DATA-01 의 AKA 매핑 13개 + 정은지 reference 1~2개와 평행 진행. 데이터 형식 동일 (GeometricCriterion)**

## v2 Requirements

향후 릴리스로 연기. 추적하되 현 로드맵에는 없음.

### 개인화 확장 (Personalization Expansion)

- **PERS-02**: 동작별 타깃 근육 시각화 (영상 위 muscle activation 추정 표시)
- **PERS-04**: 연령·성별·체형 규준 맞춤 리포트 맥락 — BodyProfile 에 age band + gender 입력 신설(미성년 동의 처리 포함), 국민체력100 인증기준 규준(`backend/judging_data/fitness_norms_kspo.yaml`, Phase 13 커밋 3c937d9)을 join 하여 "또래 1등급 상대악력 ~45% 참고" 같은 교육적 맥락 + 연령·성별 맞춤 코칭 톤을 리포트에 부착한다. **점수/분석 차원 단정 금지(D-05), 영상 측정 불가라 자동 등급배치 금지 — 리포트 맥락 전용.** 데이터 fixture 는 Phase 13 에서 이미 확보(커밋만 됨, wiring 은 v2). belle 2026-06-16 결정: 연령·성별 의학적 차이 근거가 리서치에 부재(NotebookLM) + PROJECT.md "체형 입력+맞춤 피드백" v2 연기와 정합 → v1 미포함. (memory [[kspo-fitness-norms-report-context]])

### 챔피언 레퍼런스 (Champion Reference Moat — research 0.8)

- **EMG-01**: 챔피언 EMG (Delsys/Noraxon/Athos) + 접촉력 (Tekscan) + 3D 모션캡처 (Theia3D/Vicon) 동작당 1회 캡처해 레퍼런스 라이브러리 구축 (해자 데이터셋)
- **EMG-02**: 챔피언 EMG 레퍼런스 기반 "근육 힘 방향" 단정 (v1은 추정만, v2는 측정 기반)
- **FORCE-V2-01**: push/pull/brace/rotate/release 패턴 자동 분류 학습 모델

### 측정 확장 (Measurement Expansion)

- **POSE-V2-01**: 측정 차원 확장 — 정렬(무릎-발끝)·자세(머리)·발끝 toe/head keypoint 위한 포즈 데이터 업그레이드
- **CAM-V2-01**: 카메라 앵글 합성(CameraCtrl II / UCPE)으로 시점 보정·코치뷰·데이터 증강
- **OCCLUSION-V2-01**: 사선/뒤 시점 다중 시점 + 시점 자동 매핑

### 상단 변별 (Upper-Band Discrimination — v2, Phase 20 Deferred)

- **SCORE-V2-04**: within-20°=일률 100 인 정타 구간의 상단 변별(good vs perfect) — 비전이 점수를 **올려야** 하므로 Phase 20 의 하향-전용(D-01)과 충돌. v2 또는 하향-안전 변형(상한은 100 유지 + 미세 결함만 하향)으로 재검토. (출처: 20-CONTEXT.md Deferred, D-01 충돌)

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
| 비전이 점수를 **올리는** 경로 (가중블렌드/하한) | Phase 20 D-01 — 위양성 재발 위험. 하향-전용(min cap)만 |
| 상단 변별(within-20°=100 good vs perfect) | Phase 20 Deferred (SCORE-V2-04) — 비전 상향 필요, D-01 충돌 |
| climb not_pole 게이트 (ref-climb 품질) | Phase 20 scope 아님 — 별도 reference-fix 트랙(재등록/재촬영) |
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
| BODY-02 | Phase 3 | Complete |
| POSE-03 | Phase 4 | Complete |
| SCORE-01 | Phase 5 | Pending |
| PERS-01 | Phase 6, Phase 7 | Complete |
| FORCE-01 | Phase 8, Phase 9 | Complete |
| FEED-02 | Phase 9, Phase 11 | Complete |
| SAFE-01 | Phase 10 | Pending |
| COACH-01 | Phase 11 | Complete |
| FEED-03 | Phase 11 | Complete |
| FEED-01 | Phase 12 | Pending |
| VIS-01 | Phase 12 | Pending |
| PERS-03 | Phase 13 | Pending |
| REF-01 | Phase 14 | Complete |
| MODE-01 | Phase 15 | Complete |
| MODE-02 | Phase 15 | Complete |
| SCORE-04 | Phase 15 | Complete |
| SCORE-06 | Phase 19 | Complete |
| SCORE-07 | Phase 19 | Complete |
| TRUST-01 | Phase 19 | Complete |
| TRUST-02 | Phase 19 | Complete |
| TRUST-03 | Phase 19 | Complete |
| TRUST-04 | Phase 19 | Complete |
| TRUST-05 | Phase 19 | Complete |
| SCORE-08 | Phase 20 (still-frame regression subset: Phase 23) | Complete (Phase 20); 23-03 OWN still-frame |
| SCORE-09 | Phase 20 → Phase 24 (generalization gate body) | Pending |
| SCORE-10 | Phase 24 | Pending |
| SCORE-11 | Phase 24 | Pending |
| SCORE-12 | Phase 24 | Pending |
| SCORE-13 | Phase 24 | Pending |
| SCORE-14 | Phase 24 | Pending |
| SCORE-15 | Phase 24 | Pending |
| SCORE-16 | Phase 24 | Pending |
| TRUST-06 | Phase 20 (still-frame determinism: Phase 23) | Complete (Phase 20); 23-03 OWN still-frame |
| TRUST-07 | Phase 20 | Complete |
| TRUST-08 | Phase 20 | Complete |
| DELIV-01 | Phase 15 | Pending |
| SCORE-05 | Phase 16 | Pending |
| TERM-01 | Phase 16 | Pending |
| TERM-DATA-01 | Phase 16 | Pending |
| TERM-COPY-01 | Phase 16 | Pending |

**Coverage:**
- v1 requirements: 27 total (22 + 5 신설 2026-06-19 Phase 20)
- Mapped to phases: 27 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-29*
*Last updated: 2026-05-31 — research 3 docs 통합, v2→v1 승격 (PERS-01·SAFE-01·PERS-03), 신규 v1 (POSE-02·03·BODY-01·02·COACH-01·FORCE-01), v1.5 분리 (judging 모드)*
*Updated 2026-05-31 — belle 결정: 상용/베타 = MediaPipe + Gemini, NLF/SMPL-X = R&D 비교군. POSE-01 신규 추가 (PoseEngine 추상화 + MediaPipe 마이그레이션 + NLF 격리), BODY-01 재정의 (MediaPipe segment 기반)*
*Updated 2026-06-02 — belle 결정: 학원 용어 3분기 시스템 + 5트랙 채점 (IPSF 4공식 + Page 9 절대 공통). NotebookLM IPSF CoP 2024-2025 / 2025-2027 lookup 결과 박제 — Element Code Matching IPSF 룰 (page 138-139), Page 9 "all components" 절대 트랙 (CoP 2021-2024), Dynamic Combinations / Flow 트랙, AKA 13개 매핑 (한국 학원 ↔ IPSF Code). v1 신설 SCORE-05/TERM-01/TERM-DATA-01/TERM-COPY-01. v2 신설 SCORE-V2-02/03 + TERM-V2-01/02. Phase 16 신설. 현장 설문 강사 5-1 "기본기 표준화" + 운영자 5-2 "기술 데이터 표준화" + "폭스탑 3회 분석 예시" 직접 충족*
*Updated 2026-06-07 — Phase 2 plan 01 RTMW pivot 정합 (BODY-01 MediaPipe → RTMW 갱신, v4/v5 박제).*
*Updated 2026-06-18 — Phase 19 신설 (분석 점수 신뢰도 재설계). v1 신설 SCORE-06/07 (감점식 집계 + micro-bent 0점) + TRUST-01~05 (표시-점수 정합 / 어깨 라벨·stability 분리 / Mode3 미보유 게이트 / 3D 골격 정규화 / v2 vision hook 자리). 출처: Phase 15 실증 94점 위양성 근본원인 + IPSF CoP 감점식 baseline. v2 비전 거부권 본체는 deferred.*
*Updated 2026-06-08 — Phase 2 plan 01 RTMW pivot 2차 정합: BODY-01 의 "SMPL-X β 비교군은 R&D 평가 스크립트에서만 갭 보고" 문구는 ROADMAP §4 (SMPL-X 비교) 폐기와 함께 R&D scope 에서도 last-resort 만 (paid commercial license — PS:License 1.0). 운영 path 는 RTMW-native 단일.*
*Updated 2026-06-19 — Phase 20 신설 (v2 비전 점수 — Gemini 시각 거부권). v1 신설 SCORE-08 (비전 하향-전용 거부권 통합) + SCORE-09 (curve-fit 금지 일반화 게이트) + TRUST-06 (결정론 temp 0 + 캐시) + TRUST-07 (Mode3 미보유 3분기 게이트) + TRUST-08 (visionVeto audit + 억제 UX + 객관성 무음실패 방지). 출처: Phase 19 v1 이 남긴 비-각도형 위양성(kip-up 100/100) + belle 2026-06-12 스펙. v2 신설 SCORE-V2-04 (상단 변별 — D-01 충돌로 deferred).*
*Updated 2026-06-24 — Phase 24 신설 (투명 감점-합산 채점 엔진). v1 신설 SCORE-10~16 (감점 엔진 교체 / 기하 tolerance 확장 / criterion 묶음·IPSF 상한·합산 / Gemini 강등 / baseline 분기 / 측정불가 매핑·coverage-gap / 보고서 감점내역 계산·저장 + 추적성·단조성·결정성·일반화 게이트). SCORE-09 재해석 (severity→cap 제거로 "감점-합산 엔진 일반화 게이트" = phase24 generalization gate). 출처: 24-CONTEXT.md ND-01~07 / [[scoring-must-be-transparent-deduction-tally]].*
