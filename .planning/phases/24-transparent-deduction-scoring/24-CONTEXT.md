# Phase 24: 투명 감점-합산 채점 엔진 - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

> ⚠️ **이 phase 는 Phase 20 을 "재설계"하지 않는다.** Phase 20 은 production 까지 배선 완료됨(`vision_veto.py` 971줄 + `gemini_vision_scorer.py` 1429줄 + `_apply_vision_veto`). Phase 24 는 그 중 **밴드 한 단(`SEVERITY_CAP` + `apply_downward_cap`)만 제거·교체**하고 나머지(Gemini 결함 짚기·Mode3 게이트·recall·Phase 23 정량화)는 보존·재사용한다. belle 명시(2026-06-24): "내가/너가 '이건 50 넘기지마' 밴드 박으면 그냥 사람이 판단하지 AI가 왜 있냐." → **자의적 밴드 절대 금지가 이 phase 의 존재 이유.**

<domain>
## Phase Boundary

Phase 20 이 위양성을 죽이려 도입한 채점 = `gemini_vision_scorer` 가 낸 severity enum 을 `vision_veto.SEVERITY_CAP{minor:90, moderate:75, major:50}` 로 lookup 해 `apply_downward_cap = min(overall, cap)` 로 **고정 천장**을 씌우는 방식. 2026-06-24 Phase 23 Pod eval 도중 belle 가 이 방식을 **철학적으로 거부**: severity→고정밴드는 영상마다 자의적 = 사람 판단 주입 = AI 존재이유 무효. 본 phase 는 채점을 **점수 = baseline(100) − Σ(criterion별 측정편차 × 명시규칙 감점)** 으로 교체하고, 보고서가 감점 내역("−X −Y −Z = 점수")을 명명백백하게 노출하게 한다.

**In scope:** (1) `SEVERITY_CAP`/`apply_downward_cap`(severity→고정천장) 제거, (2) 측정편차 → 명시규칙 감점 → 합산 엔진(criterion 묶음 + IPSF 상한), (3) Gemini 역할 강등(점수 X → 측정대상/결함종류만 짚기), (4) 보고서 감점 내역 노출(백엔드 계산·저장; 앱 표시는 후속 UI phase), (5) 케이스별 기대점수 manifest(moderate≤75·major=50, 23-03 흡수분 포함) curve-fit 제거 + 신규 eval 게이트(추적성·단조성·결정성·일반화).
**Out of scope:** Phase 20 working parts 재작성(보존), 앱 표시/렌더링(후속 UI phase), Phase 23 정량화 레이어 자체(완료된 입력으로 소비), 상단 변별(within-20° good vs perfect — 별도), climb ref-quality 트랙.

</domain>

<decisions>
## Implementation Decisions

### 채점 엔진 교체 (영역: 감점 규칙 도출)
- **ND-01 (엔진 교체):** 점수 = baseline(100) − Σ(criterion별 측정편차 × 명시규칙 감점). `SEVERITY_CAP` + `apply_downward_cap`(severity→고정천장) **제거**. 결과 숫자(50이든 70이든)는 tally 출력일 뿐 **범위가 아님** — 핵심은 보고서가 감점 내역을 노출하는 것. ([[scoring-must-be-transparent-deduction-tally]])
- **ND-03 (감점 규칙 anchor = 기하 tolerance 확장):** `dimensions.py` 의 tolerance + per-unit penalty(`_LINE_TOL_DEG` / `_PENALTY_PER_DEG=1.2` 기존, Phase 19)를 전 차원(각도·라인·거리 칸/층)으로 확장. **동일 형태 단일 규칙, 모든 영상 동일 slope** — "1도당 X점"이 영상마다 자의적이지 않게(curve-fit 금지). tolerance 안(편차 작음)은 0 감점.

### 감점 구조 (영역: per-degree 폭주 방지)
- **ND-04 (criterion 묶음 + IPSF 상한):** belle "오른발 30°·왼발 30° = −60 폭주" 걱정 해소. (a) 상관 관절은 **IPSF criterion 으로 묶어 1회 측정**(양다리 = "다리 신전/라인" 1 criterion → 30+30 중복계산 안 됨). (b) 각 criterion 감점 = 편차→tolerance→곡선, **상한 = 그 fault 의 IPSF severity 가중치**(예: 다리굽힘 fault 최대 −X). (c) criterion 감점 **합산**(평균 금지 — 결함이 정상 관절에 희석되는 Phase 19 이전 버그 재발 방지). **→ 원 20-D05 "worst-pose 지배"를 합산 구조로 supersede.**
  - **밴드 구분(핵심):** IPSF 상한은 **fault 종류별 규칙**(IPSF Code of Points 가 실제로 정하는 카테고리별 최대 감점, 영상 무관 동일, 추적가능) — belle 가 금지한 **최종점수 밴드**("50 넘지마")와 다르다. 최종점수엔 천장/하한 0.

### baseline = 100 (영역: 기준선 정의)
- **ND-05 (사용자 선택 코치 = 100 / IPSF 공식동작 = IPSF 기준):** 기준 = 사용자가 배우려는 코치(선수)의 동작 = 그 사용자에겐 100점(지금 정은지, 흐름상 임의 코치로 일반화). **IPSF 공식 등재 동작이면 IPSF 심사기준이 기준.** 기존 20-D07 3분기((1)IPSF공식→IPSF심사 / (2)미등재+코치보유→코치비교 / (3)둘다없음→유효성 게이트)와 정합 — "reference"를 "사용자 선택 코치"로 일반화. 동작별 기준선([[output-needs-baselined-quantification-layer]]: kip-up=바닥 / 공중동작=폴 수직·엉덩이 라인)은 측정 토대. Mode3(reference-free)는 절대지표 IPSF/criterion 기준의 세션간 델타로 성장 표시 ([[mode3-progress-not-similarity]]).

### Gemini 역할 강등 (영역: 측정대상 짚기)
- **ND-02 (점수 X, 측정대상만 짚기):** Gemini 는 점수를 절대 내지 않는다. **어디를 측정할지 / 무슨 결함인지**만 짚는다. 점수는 측정값 + 규칙. 기존 `gemini_vision_scorer.assess_fault_severity` 는 이미 score 0 / severity enum 만 냄(belle 강등 철학의 절반 기구현) → severity enum 을 "cap 입력"에서 "측정대상 지목 + criterion 식별"로 의미 재해석.

### 측정불가 결함 (영역: 위양성 재발 방지)
- **ND-06 (매핑 강제 — "보이는데 0감점" 출하 금지):** 설계 목표 = Gemini 가 짚은 모든 결함은 기하 측정항(각도/거리 칸·층/라인 편차)으로 변환되어 감점된다. 육안으로 뻔히 틀린 건 거의 항상 측정 가능(각도 부족/폴 거리/라인 꺾임) → 그 규칙을 쓴다. **출하 제품에서 "보이는데 0감점"이 나오면 그건 우리가 메울 coverage gap 이지 정상 동작이 아님.** 규칙 미작성 시 임시로만 감점 0 + coverage gap 로그(**자의적 밴드 주입 절대 금지** — belle 철학 준수). 임시상태(개발용)는 매핑 강제로 수렴.

### eval 게이트 재정의 (영역: Phase 경계 + eval)
- **ND-07 (4종 게이트, 케이스별 기대점수 제거):** 케이스별 기대점수 manifest(moderate≤75·major=50 등 = curve-fit) 제거. 신규 게이트 = (1) **추적성** — 모든 −점이 명명된 측정 편차 + 명명된 규칙으로 100% 역산(belle "명명백백하면 의외 점수도 OK"의 직접 게이트), (2) **단조성** — 측정 편차↑ → 점수↓ 역전 0, (3) **결정성** — 같은 입력 = 같은 감점 내역(temp 0 + 캐싱, Phase 18 exact-score drift 해소), (4) **일반화** — 미보유 + above-cutoff sensitivity 셋으로 위양성↔위음성 양방 검증. 정은지(또는 선택 코치) 95~100 은 타깃이 아닌 **결과**.

### Phase 경계
- **신규 phase(Phase 24), Phase 20 재오픈 아님.** Phase 23 완료 뒤 그 정량화 출력을 입력으로 소비 → 의존 역전 없음. Phase 20 은 verdict-level 로 두고(working parts 보존), 밴드 한 단만 Phase 24 가 supersede. Phase 22(파인튜닝)보다 먼저. **Phase 15 = belle 최종검증(끝으로). Pod 켜둠.**

### Claude's Discretion
- ND-03/ND-04 의 정확한 곡선 형태·tolerance 폭·IPSF severity 가중치 매핑 수식은 research/plan + IPSF Code of Points lookup + eval 로 도출(여기선 원칙만 — anchor = 기하 tolerance·IPSF 가중치, curve-fit 금지).
- ND-02 의 보고서 감점 내역 UX 강도/형식은 후속 UI phase + Figma(백엔드는 계산·저장까지).
- criterion 묶음의 정확한 그룹 정의(어떤 관절이 한 IPSF criterion 인가)는 plan + technique profile + IPSF criterion 데이터로 도출.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### belle 채점 철학 (게이트 — 변경 금지)
- 메모리 [[scoring-must-be-transparent-deduction-tally]] — 점수=100−Σ(측정편차×명시규칙 감점), 보고서 내역 노출. severity→고정밴드 금지(=사람 판단 주입). Gemini=측정대상만 짚기. 본 phase 의 존재 이유.
- `.planning/HANDOFF-score-accuracy.md` — belle 스펙(같은 정은지 95~100 / 잘못된 동작 낮음). 단 "≤50" 은 밴드가 아니라 결과 분포로 재해석 ([[vision-score-must-analyze-not-stamp]]).

### 교체 대상 코드 (plan 단계 현재 코드 재확인 필수)
- `backend/shared/python/sunity_shared/analysis/vision_veto.py` — `SEVERITY_CAP`(L65) + `apply_downward_cap`(L104) + `SEVERITY_CAP_PROVENANCE`(L89) = **제거·교체 대상**. `worst_pose_timestamp` 등 일부는 재사용 후보.
- `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` — `assess_fault_severity` → `VisionVerdict`(score 0, severity enum). **보존**, 의미 재해석(측정대상 지목).
- `backend/functions/pipeline/app.py` — `_apply_vision_veto`(밴드 mutation 본체, 교체), `_gemini_vision_veto_enabled` 토글, `_apply_score_suppression`/Mode3 게이트(보존), `assess_fault_context`/still-pair fan-out(Phase 23, 보존).
- `backend/shared/python/sunity_shared/analysis/dimensions.py` — `_LINE_TOL_DEG` / `_PENALTY_PER_DEG` / `line_score` = ND-03 감점 규칙 확장 토대(전 차원).
- `backend/shared/python/sunity_shared/analysis/kismam.py` — `overall_score` 감점식 집계 코어(Phase 19) = 합산 구조 토대.
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — Phase 23 정량화 산출(각도편차·몸-상대 칸/층) = 감점 입력.

### EVAL baseline (게이트 재정의 대상)
- `backend/evals/phase18/` — `pairs.yaml`(6 페어 + 비전-파생 fault 라벨), `eval18_serial_baseline.json`, `assert_baseline.py`. **케이스별 기대점수 밴드 assert 는 추적성·단조성 게이트로 대체.**
- `.planning/phases/18-expert-deliberate-fault-reference-eval-set/18-EVAL-SET.md` — 게이트 의미론·객관성·일반화 경계.
- `.planning/phases/23-mode-1-recall-still-frame-veto-dtw-key-frame/23-03-PLAN.md` — 20-04 regression subset 흡수분(moderate≤75 밴드) = Phase 24 가 정정.

### 의존 phase
- `.planning/phases/20-v2-gemini/20-CONTEXT.md` — 원 D-01~D-08(밴드 거부권). ND-01~07 이 D-01/D-05 를 supersede, D-07(3분기)·D-06(결정성)은 계승.
- `.planning/phases/23-mode-1-recall-still-frame-veto-dtw-key-frame/` — 정량화 레이어 + recall(입력).
- `.planning/phases/19-vision-hybrid/` — 감점식 집계 코어.

### 메모리 (박제)
- [[scoring-must-be-transparent-deduction-tally]] [[output-needs-baselined-quantification-layer]] [[judging-baseline-ipsf-code-of-points]] [[ipsf-5-track-scoring]] [[scoring-dimensions-ipsf]] [[mode3-progress-not-similarity]] [[scoring-redesign-must-generalize-no-overfit]] [[sensitivity-gate-not-just-elite-low]] [[analysis-objectivity-no-human-scores]] [[pipeline-not-concurrency-safe-eval-serial]] [[vision-score-must-analyze-not-stamp]] [[phase23-pod-eval-gate-fail-2026-06-24]] [[gemini-latest-model-versions]]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (Phase 20·23 보존)
- **`gemini_vision_scorer.assess_fault_severity`** — score 0 / severity enum / differences. Gemini 강등 철학의 절반 기구현. severity enum → "측정대상 지목 + criterion 식별"로 의미 재해석(코드 재작성 최소).
- **Phase 23 정량화(`fault_zoom` + still-pair fan-out)** — 각도 직접 측정 + 몸-상대 칸/층(keypoint·폴·바닥 baseline 결정적 계산). 감점 엔진의 **측정 입력**. percent 표기 금지(`_SCORE_PATTERN` 누수 회피).
- **`dimensions.line_score` + `_PENALTY_PER_DEG`** — per-degree 감점이 이미 일부 존재. ND-03 확장의 출발점.
- **`kismam.overall_score`** — Phase 19 감점식 누적 집계(가중평균→누적감점). ND-04 합산 구조 토대.
- **Mode3 게이트 + score suppression(`_apply_score_suppression`)** — Phase 20-03 보존, 미보유 동작 분기.
- **EVAL 하니스** — `backend/evals/phase18/`(순차 self-check) + `backend/scripts/sweep_phase15.py --pair-sequential`.

### Established Patterns
- **단일 채점 path, 두 런타임:** `pipeline/app.py::_process` 를 Lambda/RunPod 공유 — 감점 엔진은 한 곳 통합(분기 0, 코드 1벌).
- **동시성 비안전:** `_process` 전역 공유 → eval/sweep 순차만 ([[pipeline-not-concurrency-safe-eval-serial]]).
- **객관성:** 사람 점수 라벨 ground truth 금지. 감점은 실측 편차 + 명시 규칙에서만.

### Integration Points
- 감점 엔진 = `_apply_vision_veto`(현 밴드 mutation) 자리를 **측정편차→criterion 감점→합산**으로 교체. `assemble.py` dimension 집계 + `fault_zoom` 정량화 직후 overall 산출.
- 감점 내역 = 보고서/Firestore 에 criterion별 (측정값, 기준값, 편차, 적용 규칙, −점) 구조로 계산·저장(앱 표시 후속). 계약 lockstep(`analysis.ts` ↔ `models.py`).

</code_context>

<specifics>
## Specific Ideas

- belle 원문(2026-06-24): "50점이든 70이든 범위가 아니라, 우리 심사기준 이렇게 잡았으니 감점 어디어디 −몇점 = 50점, 이게 중요." 점수가 의외여도 **보고서가 명명백백하면 OK**(육안보다 정확해진 것). 보고서가 빈약 + 숫자가 자의적이면 "이정도 틀린게 이렇게 낮나?" 공감 실패.
- belle 우려(2026-06-24): per-degree 선형 합산은 상관 결함(양발 동시 굽음)에서 −60 폭주. → ND-04 criterion 묶음 + IPSF 상한으로 해소(밴드 아님).
- "우리가 규칙을 정해도 객관적인 이유": 모든 영상 동일 규칙 + 실측값에 묶임 + 보고서가 계산 노출 → "왜 이 점수?" 항상 추적가능. vs "major=50 밴드"는 영상마다 자의적.

</specifics>

<deferred>
## Deferred Ideas

- **앱 표시/렌더링:** 감점 내역의 사용자 화면 노출(`result.tsx` / coach-report) = 후속 UI phase. 본 phase 는 백엔드 계산·저장까지.
- **상단 변별 (within-20° good vs perfect):** 정타 안에서 더 잘함을 변별 — 별도 phase(감점 엔진은 결함 하향이 1차).
- **자체 비전 모델 파인튜닝(Phase 22):** Gemini 강등으로 모은 "측정대상/결함 종류" 라벨이 학습셋. 본 phase 의 측정 항목 정의가 그 라벨 스키마와 정합되게.
- **sensitivity 셋 구축(미보유+above-cutoff):** ND-07 일반화 게이트의 입력 자산. 수집은 별도(Phase 18 Deferred 와 동일).

### Reviewed Todos (not folded)
None — 신규 phase, todo 매칭 없음.

</deferred>

---

*Phase: 24-transparent-deduction-scoring*
*Context gathered: 2026-06-24*
