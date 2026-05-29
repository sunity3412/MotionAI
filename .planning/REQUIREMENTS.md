# Requirements: Sunity AI Coach

**Defined:** 2026-05-29
**Core Value:** 분석 정확도 — 점수가 믿을 만하고, 첫 분석이 "전문가 수준으로 구체적"이어야 한다. 수치는 보조, 원인이 핵심.

> 현장 니즈 출처: `docs/research/폴스포츠 수강생의 설문조사.md` (= 강사 설문조사.md, 동일 — 수강생 + 강사/운영자 통합). P0/P1/P2 우선순위는 이 문서 기준.

## v1 Requirements

파일럿 MVP done 기준. 현장 리서치 P0(파일럿 전 필수) + belle 확정 스코프. 각 요구사항은 로드맵 phase에 매핑된다.

### 점수 신뢰도 (Scoring)

- [ ] **SCORE-01**: 기술 인식기(Gemini 어댑터)가 영상에서 기술을 인식하고 관절별 EXTEND/BENT를 판정해 line 차원이 None으로 빠지지 않고 의미있게 산출된다
- [ ] **SCORE-02**: 같은/유사 영상 비교 시 "각도 정확도 100" 아티팩트 없이 정확한 라벨과 점수가 표시된다
- [ ] **SCORE-03**: overall 점수가 단일 차원(예: 안정성)에 휘둘리지 않고 안정적으로 합성된다
- [ ] **SCORE-04**: 고수(정은지) 영상이 위양성 감점 없이 신뢰할 만한 점수로 산출되고, 스피닝 폴 포함 다양한 영상에서 인체 추적·분석이 정확하다 (신뢰도 게이트 — 강사/운영자 신뢰의 핵심)

### 피드백 품질 (Feedback)

- [ ] **FEED-01**: 결과 화면에 관절 각도 수치가 "현재 87° → 기준 110°" 형태로 명확히 표시된다
- [ ] **FEED-02**: 피드백이 "실패 원인 → 필요한 힘/유연성 → 보조 동작" 순서로 구성된다 (수치는 보조, "왜 안 되는지 + 무엇이 필요한지"가 한 세트 — Cerebras 프롬프트 개선)
- [ ] **FEED-03**: 결과 화면 카피가 AI를 "강사 보조 도구"로 포지셔닝한다 (AI가 강사를 대체한다는 인상 제거)

### 분석 모드 (Modes)

- [ ] **MODE-01**: 사용자가 정은지 기준 모션을 불러와 본인 영상과 비교하고 전문가 기준 점수를 실영상으로 end-to-end 확인할 수 있다 (Mode 1)
- [ ] **MODE-02**: 사용자가 본인 영상 2개를 비교해 발전(progress)을 실영상으로 end-to-end 확인할 수 있다 (Mode 3)

### 기준 모션 (Reference)

- [ ] **REF-01**: 정은지 기준 모션을 등록할 수 있고, 등록 경로는 비교 분석 정확도가 최대화되는 방식(촬영 조건/앵글 통제 포함)으로 설계된다

### 전달 (Delivery)

- [ ] **DELIV-01**: 수강생이 TestFlight 게스트 모드에서 회원가입 없이 Mode 1 + Mode 3를 혼자 실기기로 완주할 수 있다

## v2 Requirements

향후 릴리스로 연기. 추적하되 현 로드맵에는 없음. (현장 리서치 P1·P2 + 측정 확장)

### 개인화 (Personalization) — P1

- **PERS-01**: 체형 정보 입력(키/몸무게/유연성 수준) → 코칭 텍스트 개인화 (Cerebras 프롬프트에 체형 파라미터 주입)
- **PERS-02**: 동작별 타깃 근육 시각화

### 안전 (Safety) — P1

- **SAFE-01**: 부상 위험 경고 — 레벨 대비 무리한 동작, 좌우 불균형 패턴, 요추 과신전 감지 → 경고 (kismam 외 "위험도 스코어" 별도 산출)

### 성장/전달 (Growth & Delivery) — P1

- **GROW-01**: 같은 동작 반복 분석의 회차별 개선 그래프 ("폭스탑 62→71→78점")
- **DLVR-02**: 영상 인앱 다운로드 (CloudFront 서명 URL 기반 — 운영자 요청)

### 학원/운영 (Studio Ops) — P2

- **OPS-01**: 학원 운영자 대시보드 — 수강생 성장 DB 일괄 조회 + 강사용 리포트
- **OPS-02**: 분석 자료 공유 제한 — 학원별 데이터 격리, 강사/수강생 권한 분리
- **PRIV-01**: 프라이버시 설명 화면 — 영상 처리 흐름 + 삭제 시점 명시
- **PERS-03**: 체형별 보조 운동(스트레칭/근력) 추천

### 분석 확장 (Analysis Expansion)

- **CAM-01**: 카메라 앵글 합성(CameraCtrl II / UCPE)으로 시점 보정·코치뷰·데이터 증강
- **POSE-01**: 측정 차원 확장 — 정렬(무릎-발끝)·자세(머리). toe/head keypoint 위한 포즈 데이터 업그레이드

## Out of Scope

명시적 제외. 스코프 크리프 방지용.

| Feature | Reason |
|---------|--------|
| 결제/구독 (RevenueCat) | 파일럿은 과금 없음 |
| 회원가입 강제 | 게스트 모드로 충분 — 북극성은 "혼자 켜고 확인" |
| 회전 360° / 모멘텀 / 예술성 차원 | 현 NLF 파이프라인 범위 밖 |
| 다크 모드 | 라이트 전용 (design.md) |

> 참고: CloudFront는 당초 제외였으나 운영자의 영상 다운로드 니즈로 v2(DLVR-02)에 편입.

## Traceability

어느 phase가 어느 요구사항을 커버하는지. 로드맵 생성 시 채워짐.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCORE-01 | Phase 1 | Pending |
| SCORE-03 | Phase 2 | Pending |
| SCORE-02 | Phase 3 | Pending |
| FEED-01 | Phase 4 | Pending |
| FEED-02 | Phase 5 | Pending |
| FEED-03 | Phase 6 | Pending |
| REF-01 | Phase 7 | Pending |
| MODE-01 | Phase 8 | Pending |
| MODE-02 | Phase 9 | Pending |
| SCORE-04 | Phase 10 | Pending |
| DELIV-01 | Phase 11 | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-29*
*Last updated: 2026-05-29 after roadmap creation (11 phases, 11/11 매핑)*
