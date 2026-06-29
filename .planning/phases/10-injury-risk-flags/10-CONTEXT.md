# Phase 10: 부상 위험 신호 플래그 - Context

**Gathered:** 2026-06-29
**Status:** Ready for planning

<domain>
## Phase Boundary

연습 영상 분석 결과에 **결정론적(LLM 무관) 부상 위험 신호 레이어**를 추가한다. 좌우 비대칭·트렁크(요추) 과신전·관절 과신전·레벨 대비 무리한 동작을 수치 임계로 검출해 위험도 플래그로 산출하고, 결과 화면에 시각적으로 구분된 경고 + "전문가 확인 권유" 카피로 표시한다.

**핵심 재설계 (NotebookLM 도메인 리서치 반영):** 부상 위험 ≠ 극단 각도 그 자체. IPSF 규정에서 180° 스플릿·깊은 백아치·완전 신전(hyperextension)은 **필수/가점** 요소다(정은지가 의도적으로 수행). 극단 각도만으로 플래그하면 고수가 위양성으로 찍혀 프로젝트 핵심 가치(정은지 위양성 방지)와 충돌한다. 문헌상 위험의 변별자는 **통제 상실(loss of control)** — 반동 사용, 슬립, 리그립, 밸런스 상실(안 떨어지려 다른 팔다리를 황급히 뻗음), 정적 유지 불안정. 따라서 위험 신호 = **(극단/과신전/비대칭 자세) AND (통제 상실 지표)** 조합.

**스코프 제약 (ROADMAP):** "부상 확정" 단정 금지. "위험 가능성"으로만 표기 + 전문가 확인 권유. 객관성 원칙: 사람 점수 라벨 금지, 수치 임계값만 ([[analysis-objectivity-no-human-scores]]).

</domain>

<decisions>
## Implementation Decisions

### 신호 구조 (D-01)
- **D-01:** **별도 결정론 SafetyFlag 레이어**로 구현. 측정 기반 플래그를 독립 데이터 구조 + 전용 UI 배너로 산출. 결정론·객관성 보장(temp 무관, 캐시 안정). 기존 LLM `injuryRisk` 프로즈(`CoachingTipDetail.injuryRisk`, Cerebras 조립, 옵셔널)는 **코칭 보조로 별개 유지** — Phase 10이 대체하거나 입력 주입하지 않는다. 두 레이어는 독립.

### 위험 신호 = 자세 + 통제 상실 조합 (D-02)
- **D-02:** 각 위험 신호는 **(극단/과신전/비대칭 자세 조건) AND (통제 상실 지표)** 의 조합으로 발화한다. 자세 단독 플래그 금지(정은지 위양성 방지). 통제 상실 지표는 Phase 8 jerk/jitter temporal 신호 + `동작 안정성(stability)` 차원을 재사용(불안정 = 통제 상실 프록시). 문헌 매핑: 반동/momentum, 슬립, 리그립, 밸런스 상실, 정적 유지 <2초 불안정 = "근력 임계 초과" 신호이며 IPSF 감점 항목과 일치.

### 비대칭 위험 신호 (D-03)
- **D-03:** **Reference 대비 편차** 방식. Mode 1: 정은지 동작 자체의 좌우 편차를 baseline으로, 학생이 유의하게 더 비대칭이면 플래그. 의도적 비대칭은 reference에도 동일하게 존재하므로 자동 상쇄(scoring이 대칭 차원을 일부러 뺀 이유 = 폴 동작 다수가 의도적 비대칭, `dimensions.py:12`). Mode 3: 직전 영상 대비. **절대 좌우 비대칭은 v1에서 플래그하지 않음**(위양성 큼). 정량화는 KISMAM Z-score `D=(x−μ)/σ` 표준 지표 사용(`kismam.py` 재사용).

### 트렁크(요추) 과신전 검출 (D-04)
- **D-04:** **트렁크-대퇴 각도 프록시** — 어깨-고관절-무릎 3D 각도로 트렁크 후굴/과신전을 근사. **절대 신호 → 양 모드 동작.** 반드시 "추정/가능성"으로만 표기. **명시적 한계(CONTEXT 박제):** 몸통을 단일 강체로 보므로 요추 과전만(hyperlordosis) vs 고관절만 신전을 구분 불가(척추 중간 키포인트 부재). 따라서 단정 금지 + 통제 상실 지표(D-02)와 결합해야 발화.

### 관절 과신전 검출 (D-05)
- **D-05:** **무릎·팔꿈치 과신전(역꺾임)** 을 3D로 방향까지 판별. **절대 신호 → 양 모드 동작** ("내 자세가 이러면 부상 위험 높다"의 Mode 3 핵심). 방법: 내적(dot product)은 0–180° 굽힘 각도만 줘 방향 미상 → **외적(cross product) 부호를 분절-국소 좌표계(시상면)에서 추적**해 정상 굴곡 vs 역방향 과신전(genu recurvatum / elbow hyperextension) 판별. 무릎·팔꿈치는 1자유도 힌지 관절이라 이 방법이 유효(NotebookLM 검증). 발화는 D-02 조합 규칙 적용.

### 레벨 대비 무리 (D-06)
- **D-06:** **Mode 1 전용** — `reference.level`(basic/intermediate/advanced) × 사용자 `experience`(beginner/intermediate/advanced) 매핑. 데이터 이미 존재(`analysis.ts`). Mode 3는 move 난이도 미상이라 이 규칙 미적용 — 대신 Mode 3의 "무리한 시도"는 D-02 통제 상실 지표(반동·슬립·밸런스 상실)로 절대 검출(레벨 무관 행동 신호).

### 임계값 출처 (D-07)
- **D-07:** 고정 단일 각도 금지. **정상 범위 `[T_min, T_max]`** (엘리트/reference 분포 기반, KISMAM tol = 허용 편차). 비대칭은 reference-anchored. 관절/트렁크 과신전의 절대 해부학적 임계(중립각 초과분)는 **외부 생체역학/물리치료 문헌으로 확인 필요**(폴 규정집엔 의학적 부상 임계 수치 없음 — NotebookLM 명시). **13영상 curve-fit 금지** ([[scoring-redesign-must-generalize-no-overfit]], [[calibration-source-hard-gate]]).

### UI 경고 표시 (D-08)
- **D-08:** 결과 화면에 시각적으로 구분된 위험 경고 배너 + "전문가 확인 권유" 카피. 구체 위치·색·톤은 `/gsd-ui-phase 10` UI-SPEC에서 확정(이 phase는 데이터 구조 + 발화 규칙까지). 브랜드 컬러 #FF4B33 / Pretendard / 라이트 전용 준수. "부상 확정" 단어 금지.

### Claude's Discretion
- 위험도 스코어의 구체 수치 스케일·등급 단계 수, SafetyFlag 데이터 구조 필드명, 플래그별 코드 식별자 — 플래너/실행 재량(단 contract 3중 미러 규칙 준수: `analysis.ts` ↔ `models.py` ↔ `contract.md`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 요구사항 / 로드맵
- `.planning/ROADMAP.md` §"Phase 10: 부상 위험 신호 플래그" — Goal, Success Criteria 1–4, 스코프 제약
- `.planning/REQUIREMENTS.md` — SAFE-01 (유일 요구 ID)

### 분석 코어 (재사용 substrate)
- `backend/shared/python/sunity_shared/analysis/skeleton.py` — JOINT_KEYS / JOINT_ANGLES (어깨·팔꿈치·손목·고관절·무릎·발목; **척추 중간 키포인트 없음** — D-04 한계 근거)
- `backend/shared/python/sunity_shared/analysis/kismam.py` — Z-score 정상범위 `D=dev/tol` 채점(D-03/D-07 임계 substrate)
- `backend/shared/python/sunity_shared/analysis/dimensions.py` §12 — 대칭 차원 의도적 제외 사유(D-03 근거); `stability` 동작 안정성 차원(D-02 통제 상실 substrate)
- `backend/shared/python/sunity_shared/analysis/temporal.py` — temporal 신호(Phase 8 jerk/jitter 통제 상실 substrate)
- `backend/shared/python/sunity_shared/analysis/assemble.py` — 차원/finding 조립 지점(SafetyFlag 주입 위치 후보)
- `backend/functions/pipeline/app.py` `_process` — 분석 단일 경로(Lambda+RunPod 공유)

### 코칭 레이어 경계 (충돌 회피)
- `app/src/types/analysis.ts` — `CoachingTipDetail.injuryRisk`(기존 LLM 프로즈, D-01 별개 유지), `ExperienceLevel`, `SkillLevel`/`reference.level`(D-06), `AnalysisDoc`(contract)
- `backend/shared/python/sunity_shared/models.py` — Python contract 미러(3중 동시 수정 규칙)
- `docs/contract.md` — API contract 단일 진실

### UI
- `app/src/app/analysis/result.tsx` — 결과 화면(경고 배너 표시 위치, D-08)
- `design.md` §5 — 라이트 테마·브랜드 컬러 규칙

### 도메인 원칙 (메모리)
- [[analysis-objectivity-no-human-scores]] — 사람 점수 라벨 금지, 수치 임계 OK
- [[scoring-redesign-must-generalize-no-overfit]] / [[calibration-source-hard-gate]] — 13영상 curve-fit 금지, 임계 출처 게이트
- [[mode3-progress-not-similarity]] — Mode 3 = 발전(절대 지표 델타)

### 도메인 리서치 (NotebookLM, 2026-06-29 질의)
- NotebookLM "폴스포츠에 대한 지식" (e688fb4e) — 위험 패턴: 수직 당기기 편중, 비대칭 부하, 반동 백아치, 어깨 충돌 증후군, 초보자 red flags(슬립/리그립/밸런스 상실). IPSF가 hyperextension을 가점으로 취급(위양성 근거)
- NotebookLM "폴스포츠 모션 관련 기술" (6e7880e7) — 과신전 외적 부호 판별법(D-05), 트렁크 강체 프록시 한계(D-04), KISMAM Z-score 정상범위(D-07), 동적 무릎 외반(knee valgus) ACL 위험 지표

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kismam.py` Z-score `score_from_deviation(dev, tol)` — 정상범위 임계 로직 재사용(D-07). tol = IPSF [CITED] 허용 편차.
- Phase 8 temporal jerk/jitter + `dimensions.py` stability 차원 — 통제 상실 지표 substrate(D-02). 단 명시적 슬립/리그립/밸런스 상실 검출은 미구현(아래 research 항목).
- `analysis.ts` `experience` + `reference.level` — D-06 레벨 매핑 데이터 이미 존재.

### Established Patterns
- 결정론 우선(temp 0 + 캐시) — SafetyFlag는 LLM 무관 순수 측정(D-01).
- Contract 3중 미러(`analysis.ts` ↔ `models.py` ↔ `contract.md`) — SafetyFlag 타입 추가 시 동시 수정 필수.
- 순수 함수 분석 코어(numpy only) — SafetyFlag 산출 로직은 boto3/네트워크 무관 순수 함수로.

### Integration Points
- `assemble.py` / `_process` 결과 조립 단계에 SafetyFlag 산출 주입.
- `result.tsx` 경고 배너 렌더(D-08), `AnalysisDoc`에 SafetyFlag 필드 추가.

</code_context>

<specifics>
## Specific Ideas

- belle 명시 요구: Mode 3에서도 "내 영상 자세가 이러면 부상 위험 높다"가 실현돼야 함 → D-04(트렁크)·D-05(관절 과신전)·D-02(통제 상실)가 절대 신호라 Mode 3 충족. 레벨 매핑(D-06)만 Mode 1 전용.
- 위험 신호는 "위험 가능성"으로만, 전문가 확인 권유 동반(과잉 경고로 사용자 불안 유발 금지).

</specifics>

<deferred>
## Deferred Ideas

- **명시적 슬립/리그립/밸런스 상실 이벤트 검출** — v1은 jerk/jitter+stability 불안정 프록시로 통제 상실 근사. 정밀 이벤트 검출(폴 접촉점 추적, 급강하 검출)은 후속 phase 후보. (research/plan 단계에서 v1 프록시로 충분한지 판단)
- **요추 전용 척추 키포인트** — 척추 중간 관절 추정(133-keypoint wholebody 또는 자체 학습)으로 트렁크 강체 한계 극복은 별도 트랙([[ml-pose-3d-pivot]] 계열).
- **동적 무릎 외반(knee valgus) ACL 지표** — NotebookLM이 핵심 부상 지표로 언급. v1 스코프엔 미포함(착지/방향전환 동작 중심이라 폴 정합성 검토 필요). 후속 검토.

### 미해결 research 항목 (플래너/researcher가 다룰 것)
- `experience`(body profile) + `reference.level`이 분석 시점에 파이프라인까지 도달하는지 검증(D-06 실현 전제).
- 관절/트렁크 과신전 절대 임계의 외부 생체역학 문헌 출처 확정(D-07).

</deferred>

---

*Phase: 10-injury-risk-flags*
*Context gathered: 2026-06-29*
