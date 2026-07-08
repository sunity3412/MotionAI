# Phase 30: 성장 추적 개선 — 평균 기반·동작별 막대 (growth-tracking) - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

파일럿 실증 피드백 E1/E2(시나리오 5단계)대로 홈 성장 그래프 재설계. 현행 `GrowthCard`는 최근 6건의 raw overallScore를 모드·동작 구분 없이 섞어 꺾은선으로 그림 — 이를 (E1) 주별 평균 기반 추이 + (E2) 동작별 상승/하락 포인트 막대(주식창식)로 교체한다. 화면은 홈 탭 성장 카드 하나로 완결(기록 탭 무수정). 백엔드는 mode3 인식 동작명 방출 필드 1건만 추가(데이터 적립 시작).

**스코프 밖 (ROADMAP 명시):** 지적 단위(fault_category) 세션간 개선 추적(매칭+신뢰구간) = 이후 단계 유지. 학원 명칭 카테고리 묶음 체계 = Phase 16.

**불변 경계:** 채점 로직 무접촉 — 이 phase는 표시·집계 계층만. mode3-progress-not-similarity(%일치 헤드라인 금지) 및 mode3-overall-exclude-angle-similarity invariant 준수(증감 '포인트 델타'는 유사도가 아니므로 정합 — 논의에서 확인).

</domain>

<decisions>
## Implementation Decisions

### E1 평균 집계 방식
- **D-01:** 집계 단위 = **주별 평균** — 한 주의 분석들을 평균내어 점 1개. 분석 없는 주는 점 없음(건너뜀). "이번주 성장 그래프" 라벨은 주별 평균 의미에 맞게 정정(카피는 재량).
- **D-02:** **mode1(프로 비교)/mode3(내 기록) 혼합 평균 금지** — 그래프 위 모드 토글 버튼으로 분리, 선택된 모드의 주별 평균만 표시. 근거: 기준이 다른 점수를 섞으면 모드 사용 비율 변화가 실력 변화로 오독됨.
- **D-03:** 기본 토글 = **마지막 분석 모드 따라감** (belle 제안, 논의로 확정) + **그 모드 주별 점 2개 미만이면 데이터 있는 다른 모드로 자동 폴백**. 토글 활성 상태는 브랜드색으로 명확히 표시(어느 탭인지 즉시 인지 — 일관성 우려 해소 장치).

### E2 동작별 막대
- **D-04:** 그룹핑 = **두 층 분리.** (i) 이번 phase 화면: mode1은 `comparison.referenceMotionName`으로 동작별 그룹핑, mode3는 '내 기록' 단일 항목. (ii) 백엔드: mode3 인식 동작 id/명을 분석 문서에 방출 시작(인식기는 이미 mode3에서 동작 인식 중 — 저장만 안 되던 것). 3-way lockstep(analysis.ts + models.py + docs/contract.md) 준수, optional 필드. legacy 문서는 여전히 그룹핑 불가 — 효과는 앞으로 쌓이는 분석부터. (iii) 학원 명칭 카테고리 체계(묶음 규칙)는 Phase 16이 이 필드를 소비.
- **D-05:** 증감 지표 = **점수 델타 포인트** ("+6점 / −4점"). 등락률% 기각 — 0~100 점수 위 %는 이중 상대값 왜곡(50→55=+10% vs 90→95=+5.6%) + %가 유사도로 오독될 여지. 기준선 = **최근 활동 주 평균 − 직전 활동 주 평균** (동작별, D-01 주별 평균과 정합). 비교 대상 없는 첫 기록 동작 = "첫 기록 N점 (비교 전)" 형태.
- **D-06:** 노이즈 임계 없음 — **모든 증감 그대로 ▲▼ 노출** (belle: 투명성 우선, 주식창식). ▲=브랜드레드, ▼=파란계열(한국 주식창 관례). '유지' 밴드/하락 숨김 기각.

### 점수 이질성 경계
- **D-07:** legacy 채점 체계 문서(mode1 Phase 24 이전 / mode3 Phase 29 tally 전환 이전) = **전부 포함, 특별 처리 없음.** 근거: 파일럿 수강생은 신규라 오염 미미(구 문서 보유자는 주로 내부 테스트 계정) + 주별 평균이 최근 몇 주만 보여서 시간이 지나면 자연 해소. 구현 비용 0.

### 표시 위치·화면 구성
- **D-08:** 배치 = **홈 성장 카드 하나에 [추이]/[동작별] 보기 전환 탭.** 기록 탭 무수정, 카드 높이 일정(홈 스크롤 부담 없음). 2층 토글: 모드(프로비교/내기록) × 보기(추이/동작별).
- **D-09:** **[동작별] 보기 시 모드 토글 숨김** — 프로비교 동작 행들 + '내 기록' 행을 한 리스트에 배지(·프로 등)로 구분해 통합 표시. 각 행의 델타는 행 내부에서만 계산되므로 모드 혼합 왜곡 없음. 모드 토글은 [추이] 보기에만 적용. ([내기록]×[동작별] = 1행뿐인 빈 화면 문제 회피)

### Claude's Discretion
- 라벨 카피 정정("이번주 성장 그래프" → 주별 평균 정합 표현) 및 홈 헤더 "(평균 N점)"(전체 누적 평균)의 유지/정리.
- 막대 정렬 순서, 표시 주 수(추이) 및 동작 수 상한(동작별), 색·타이포 세부 — **Figma 우선 확인**(fileKey jrdI7kp245HkPfLB0nclsz, ui-figma-first) 후 design.md 보조.
- mode3 인식 동작명 방출 필드의 계약 설계(필드명·위치·validator) — 단 3-way lockstep + Firestore flat 규칙 준수.
- 차트 구현 = 기존 react-native-svg 직접 패턴(GrowthChart 선례) 유지 권장 — 새 차트 라이브러리 도입 불필요.
- 데이터 없음/부족 상태 처리(GrowthLockedCard 카피 포함) — D-03 폴백 이후에도 양쪽 모드 다 부족한 경우.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 근거 (이 phase의 존재 이유)
- `.planning/PILOT-FEEDBACK-2026-07-06.md` §E — E1(raw→평균)/E2(동작별 막대) 원문 + 우선순위 맥락.
- `.planning/SCENARIO.md` 단계 5 — "지적 단위 세션간 개선 추적"은 이후(파일럿=점수 단위까지), 측정 노이즈>개선분 위험 언급. 불변 원칙(mode3=발전≠일치).
- `.planning/ROADMAP.md` Phase 30 섹션 — E1/E2 + mode3-progress-not-similarity 정합 확인 필수 + 지적 단위 추적 이후 유지.

### 현행 구현 (수정 대상)
- `app/src/components/GrowthChart.tsx` — 현행 raw 꺾은선(react-native-svg 직접). 교체/확장 대상.
- `app/src/app/(tabs)/index.tsx` — `GrowthCard`(최근 6건 mode 혼합 피드, :292), `averageScore`(:58, 헤더 "(평균 N점)"), `GrowthLockedCard`(:304). 수정 지점.
- `app/src/lib/userAnalyses.ts` — `useMyAnalyses` 구독(데이터 소스, doneOnly). 주별 집계는 이 위에 selector로.

### 데이터 계약 (D-04 방출 필드)
- `app/src/types/analysis.ts` — `Mode1Comparison.referenceMotionId/Name`(그룹핑 키, :243), `Mode3Comparison`(동작 식별 필드 부재 — 방출 필드 추가 지점, :258), `AnalysisDoc`(:637).
- `backend/shared/python/sunity_shared/models.py` + `docs/contract.md` — 3-way lockstep 대상.
- `backend/functions/pipeline/app.py` — mode3 scoringBasis 도출부(:3123 부근, recognizer 결과가 이미 존재하는 seam) — 인식 동작명 방출 배선 지점.
- `backend/shared/python/sunity_shared/firestore_admin.py` — complete_analysis validator (신규 필드 검증 추가 지점).

### 인접 phase 경계 (중복 방지)
- `.planning/phases/29-mode3-result-screen-completion/29-CONTEXT.md` — D-02(mode3 overallScore tally 전환 예정, sweep 게이트 조건부) — 본 phase D-07의 전제. Phase 29와 파일 충돌 가능 지점(result 계약)은 없음 — 본 phase는 홈 카드·계약 optional 필드만.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GrowthChart.tsx` — react-native-svg 꺾은선 선례(브랜드 그라디언트 area + 점 라벨). 주별 평균 선으로 데이터만 바꿔 재사용 가능. 막대 뷰도 동일 svg 패턴으로.
- `useMyAnalyses({ doneOnly: true })` — 이미 홈에서 구독 중. 추가 쿼리 없이 클라이언트 집계로 충분(파일럿 데이터 규모).
- `history.tsx`의 `motionLabel()` — mode1 동작명/mode3 '내 동작 분석' 구분 선례(D-04 화면 층과 동일 로직).
- 기록 탭 `modeBadge()`('프로 비교'/'내 기록') — 토글·배지 라벨 카피 재사용.

### Established Patterns
- 계약 optional 필드 + legacy 폴백 (faultZoomStatus/tier 선례) — mode3 동작명 필드도 optional, 부재 시 '내 기록' 그룹.
- 3-way lockstep 단일 atomic commit + Firestore flat(nested array 금지).
- 테마 토큰만 사용(하드코딩 금지) — ▼ 파란계열도 토큰 신설 또는 기존 토큰에서.
- OTA(JS-only) — 앱 변경분은 전부 OTA 가능. 백엔드 방출 필드는 SAM 배포(`sam build --use-container`).
- 실기기 확인 = HUMAN-UAT.md 적립(batch UAT 원칙, 즉시 belle 호출 금지).

### Integration Points
- 홈 `GrowthCard` ↔ `useMyAnalyses` — 집계 selector(주별 평균, 동작별 델타)는 순수 함수로 분리해 테스트 가능하게.
- 파이프라인 `_process` mode3 분기 → `complete_analysis` (인식 동작명 방출).
- 앱 `normalize()`(userAnalyses.ts) — 신규 필드 defensive 파싱.

</code_context>

<specifics>
## Specific Ideas

- belle: "버튼으로 선택해서 보게 하는 건 어때?" — 모드 분리를 토글 버튼 UI로 푸는 방향 직접 제안(D-02 채택 경로).
- belle: 기본 탭 = "다음 접속 때 최근 분석한 게 마지막이니깐" — 마지막 분석 연속성 논리(D-03).
- belle: mode3 학원 명칭 수집·카테고리 묶음은 "더 기획이 필요하다" — Phase 16 defer + 이번엔 데이터 적립만(D-04 두 층 분리의 배경).
- 주식창식 컨벤션 명시 선호: 상승=빨강(브랜드레드와 자연 정합), 하락=파랑, 전부 노출(D-06).

</specifics>

<deferred>
## Deferred Ideas

- **학원 명칭 카테고리 묶음 체계** (mode3 동작별 그룹핑 규칙·용어 정규화) — Phase 16 학원 용어 3분기 시스템에서 D-04 방출 필드를 소비해 활성화.
- **지적 단위(fault_category) 세션간 개선 추적** — ROADMAP 명시대로 이후 단계(신뢰구간 필요).
- **노이즈 신뢰구간/유지 밴드** — 이번엔 전부 노출(D-06)로 확정했으나, 파일럿에서 "노이즈 하락 오독" 신고가 실제 발생하면 재검토 후보.

</deferred>

---

*Phase: 30-growth-tracking*
*Context gathered: 2026-07-09*
