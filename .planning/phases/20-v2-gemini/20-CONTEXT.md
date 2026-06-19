# Phase 20: v2 비전 점수 (Gemini 시각 거부권) - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning (구현/eval 은 Pod 재개 후)

> ⚠️ **이 phase 는 신뢰를 깬 위양성(kip-up 100/100)을 고치려 생성됐다. belle 명시: "절대 실수하지 않도록 더 신중히."** 가장 큰 리스크 = **비전이 점수를 잘못 올려 위양성을 재발시키는 것**. 모든 결정이 "비전은 점수를 못 올린다(하향 전용)"로 수렴한 이유다.

<domain>
## Phase Boundary

Phase 19 v1(D-01 감점식)이 angle 채널 결함은 잡았으나(EVAL 변별 4/4) **비-각도형 실패는 여전히 위양성**(kip-up 100/100 — 타이밍/완성도 결함을 DTW band 가 흡수). 본 phase 는 belle 가 2026-06-12 이미 정한 해결책 = **Gemini 시각 점수를 채점 path 에 하향 거부권으로 투입**해 위양성을 죽인다. 동시에 Mode 3 미보유동작 무비판 confident 점수(97)를 유효성 게이트로 막는다.

**In scope:** (1) Gemini 시각 거부권을 Mode1/Mode3 채점 path 에 통합(하향 전용), (2) Gemini 인식기 결정성(temp 0 + reference profile 캐싱), (3) Mode3 미보유동작 유효성 게이트 + 점수근거 화면 표시.
**Out of scope:** 상단 변별(within-20°=100 → good vs perfect, 이연), climb not_pole(ref-climb reference 품질 문제 = 별도 ref-fix 트랙, 코드 아님), 비전이 점수를 올리는 모든 경로.

</domain>

<decisions>
## Implementation Decisions

### 비전↔v1 결합 (영역 1)
- **D-01:** **거부권/캡 — 하향 전용.** 비전은 fault 심각도에 따라 v1 감점식 점수를 **깎기만** 하고 **절대 못 올린다**. kip-up major fault → ≤50, fault 없는 정타 → v1 그대로(95~100 유지). belle 스펙(잘못된 동작 ≤50 AND 같은 정은지 95~100) 양 조건 동시 충족 + 위양성 재발 **구조적** 차단. (가중블렌드/하한 거부 — 비전이 올릴 수 있어 위양성 재발 위험.)
- **D-02:** **캡/감점 수치는 6페어에 curve-fit 금지.** 원칙(하향 전용·심각도 등급)만 잠그고, 실제 임계 수치는 **일반화 검증된 eval**로 정한다(보유셋 overfit 절대원칙 — [[scoring-redesign-must-generalize-no-overfit]]). 사람 점수 라벨 ground truth 금지(비전 출력=fault 위치/종류/기하 추정, 임계값 수치 라벨링은 OK — [[analysis-objectivity-no-human-scores]]).

### 비전 호출 범위·트리거·단위 (영역 2)
- **D-03:** **범위 = Mode1 + Mode3 둘 다.** fault 는 reference 유무와 무관하니 비전이 둘 다 본다 — Mode1 위양성(kip-up)과 Mode3 절대점수 모두에 하향 거부권 적용.
- **D-04:** **트리거 = Mode1/Mode3 채점 path 에 항상 비전 호출.** 위양성이 "고점이라 안 봐도 됨" 류 휴리스틱을 뚫고 들어왔으므로 영리한 게이팅으로 케이스를 놓치지 않는다. 비용 = 외부 Gemini API(Pod 무관, belle 허용 — 정확도 우선, 효율도 잡기 [[gemini-vision-active-use]]).
- **D-05:** **단위 = 지배 결함 pose(worst-pose) 중심.** 가장 심각한 결함 pose 가 종합점수를 지배한다(D-01 감점식 정합 — fault 1개가 종합을 끌어내려야). **모든 IPSF phase 평균 거부** — 평균은 Phase 19 에서 고친 "결함이 정상 관절에 희석되는" 바로 그 원래 버그. 기존 key_moments(Phase 8/11 technique profile)의 hold/peak 재사용 → 신규 Gemini moment 호출 0.

### Gemini 인식기 결정성 (영역 2 종속)
- **D-06:** **temperature 0 + reference 별 profile 캐싱.** line 차원을 결정하는 Gemini 인식기는 LLM 이라 run 변동 가능(실증 5회는 일관) → temp 0 + 같은 reference=같은 분류 캐싱으로 결정성 박제. 결정론(같은 입력=같은 점수) 유지.

### Mode3 미보유동작 게이트 (영역 3)
- **D-07:** **판정 주체 = Gemini 인식기 3분기.** reference-free 라 유사도 못 쓰니 비전이 "이게 내가 아는 폴 동작인가"를 판정 — (1) IPSF 공식 등재(ipsfCode 존재) → IPSF 심사기준 평가+근거+발전비교 / (2) IPSF없음·정은지 보유 → 정은지 비교+근거+발전비교 / (3) 둘 다 미보유 → 유효성 게이트. ([[mode3-scoring-basis-unknown-move-gate]] / [[studio-term-3branch-system]] 정합.)
- **D-08:** **미보유(분기 3) 표시 = confident 점수 억제 + "기준 없음".** "이 동작은 기준 데이터가 없어 정확한 점수를 드릴 수 없어요" 류 투명 표시. confident 97 금지(미보유에 확신 점수 = 신뢰 파괴). 점수근거(동작분류 IPSF/정은지/미보유)를 Mode3 첫분석 화면에 노출(현재 assemble 분기카피는 있으나 화면 미표시).

### Claude's Discretion
- D-08 의 정확한 UX 강도(점수 완전 숨김 vs 회색 처리 vs 배너)는 plan/Figma 에서 확정 — 원칙(confident 숫자 금지)만 잠금. belle 가 "점수 억제 + 기준없음" 방향 선택.
- D-02/D-05 의 정확한 캡/감점 수식·worst-pose 집계 룰은 research/plan + eval 로 도출(여기선 원칙만).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### belle 점수 스펙 (게이트 — 변경 금지)
- `.planning/HANDOFF-score-accuracy.md` — 같은 정은지 95~100 / 잘못된 동작 ≤50 / Gemini 시각 점수 직접(Stage C). tol 완화·UX 우회 금지.
- `.planning/phases/20-v2-gemini/20-CONTEXT.md` (본 파일) — discuss 결정 D-01~D-08.

### EVAL baseline (known-answer gate)
- `backend/evals/phase18/dataset/pairs.yaml` — 6 페어 + 비전-파생 fault 라벨(D-05 spike).
- `backend/evals/phase18/baseline/eval18_serial_baseline.json` — 확정 serial 스냅샷(kip-up 100→≤50 으로 내려가고 변별 4쌍 퇴행 0 이 목표).
- `backend/evals/phase18/assert_baseline.py` — self-check 하니스(게이트 의미론).
- `.planning/phases/18-expert-deliberate-fault-reference-eval-set/18-EVAL-SET.md` — 게이트 의미론·객관성·일반화 경계.

### v1 재설계 + 비전 앵커
- `.planning/phases/19-vision-hybrid/` — v1 감점식 + vision-hybrid hook(v2 가 붙는 자리).
- `.planning/phases/19-vision-hybrid/19-D05-VISION-GROUNDING-SPIKE.md` — 6/6 high confidence fault 앵커(비전 거부권 작동 신호).
- `backend/research/spikes/spike_vision_grounding_pair.py` — Gemini per-pair 비교(점수 라벨 0, 객관성 준수). Pod 불필요.
- `.planning/phases/15-mode-1-mode-3-testflight/deferred-items.md` — 위양성 근본원인.

### 채점 코드 (plan 단계에서 현재 코드 재확인 필수 — file:line 은 메모리 기준)
- `backend/functions/pipeline/app.py` — `_process` 채점 루프, not_pole 게이트(MODE_EXPERT 블록 내), Mode1/Mode3 분기.
- `backend/shared/python/sunity_shared/analysis/` — `assemble.py`(집계+분기카피), `dimensions.py`(angle/line 차원), `technique.py`(인식기 + key_moments), `coach_writer.py`.
- `backend/shared/.../analysis/` Gemini vision 어댑터(Phase 17) — 재사용 대상.

### 메모리 (박제)
- [[score-spec-95-100-elite-vision-fix]] [[mode3-scoring-basis-unknown-move-gate]] [[scoring-redesign-must-generalize-no-overfit]] [[sensitivity-gate-not-just-elite-low]] [[pipeline-not-concurrency-safe-eval-serial]] [[analysis-objectivity-no-human-scores]] [[gemini-latest-model-versions]] [[gemini-vision-active-use]] [[studio-term-3branch-system]]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Gemini Vision 어댑터 (Phase 17):** reference 자동등록/코칭/finding 인식에 이미 Gemini multimodal 통합 — 시각 점수 호출에 재사용. 모델 = `gemini-3.1-pro-preview`(-preview 필수), 키 = SSM `/sunity/motion/gemini-api-key`(로컬 조회 `--profile sunity-motion` — [[gemini-key-local-ssm-profile]]).
- **D-05 spike 하니스:** `spike_vision_grounding_pair.py` 가 per-pose fault 판정 프롬프트 패턴 보유(객관성 가드 포함). 시각 점수 프롬프트 출발점.
- **key_moments (technique profile, Phase 8/11):** hold/peak 시점 이미 추출 — worst-pose 단위에 재사용(신규 moment 호출 0, D-05).
- **EVAL 하니스:** `backend/scripts/sweep_phase15.py --pair-sequential`(15-01) + `backend/evals/phase18/`(순차 eval + self-check).

### Established Patterns
- **단일 채점 path, 두 런타임:** `pipeline/app.py::_process` 를 Lambda/RunPod 가 공유 — 비전 거부권은 `_process` 한 곳에 통합(분기 0, 코드 1벌).
- **D-01 감점식:** 결함이 정상 관절에 희석되지 않게 감점 집계. 비전 거부권은 이 위에 **하향만** 얹음(평균/블렌드 금지).
- **동시성 비안전:** `_process` 전역 공유 → eval/sweep **순차만**([[pipeline-not-concurrency-safe-eval-serial]]).
- **객관성:** 사람 점수 라벨 ground truth 금지. 비전=결함 위치/종류/기하 추정(자연어/판단), 좌표 단정 금지.

### Integration Points
- 비전 거부권 = `_process` 의 dimension 집계(`assemble.py`) **직후** overall 산출에 하향 캡으로 삽입(Mode1/Mode3 둘 다).
- Mode3 미보유 게이트 = 현재 `not_pole_motion`(MODE_EXPERT 블록 한정)을 reference-free Mode3 용 Gemini 인식기 3분기로 확장. 점수근거 = `assemble` 분기카피를 Mode3 첫분석 화면(app)에 노출.

</code_context>

<specifics>
## Specific Ideas

- belle "절대 실수하지 않도록 더 신중히" — 이 phase 의 모든 결정은 **위양성 재발 방지(하향 전용)** 우선. 풍부함(상단 변별)보다 안전이 먼저(영역 4 이연).
- 일반화 hard gate: 6페어는 정은지 단일 선수 + fault(elite-low) → curve-fit 타깃 아님. **미보유 + above-cutoff(고득점이어야 정상) sensitivity 셋**으로 위양성↔위음성 양방 검증 필수([[sensitivity-gate-not-just-elite-low]]).

</specifics>

<deferred>
## Deferred Ideas

- **상단 변별 (within-20°=100 → good vs perfect):** 영역 4 — 비전이 점수를 올려야 해 D-01 하향전용과 충돌 → 위양성 재발 위험. v2 는 하향 안전 우선, 상단 변별은 후속 phase 또는 비전 보조의 하향-안전 변형으로 재검토.
- **climb not_pole 게이트:** correct-climb 조차 ref-climb 유사도 <25 → ref-climb **reference 품질/촬영각** 문제. 별도 reference-fix 트랙(재등록/재촬영, Phase 14 seeder/rollback 재사용). 본 phase 코드 scope 아님.
- **sensitivity 셋 구축(미보유+above-cutoff):** Phase 18 Deferred 와 동일 — 일반화 검증 자산. 본 phase eval 의 일반화 게이트로 필요하나, 자산 수집은 별도.

</deferred>

---

*Phase: 20-v2-gemini*
*Context gathered: 2026-06-19*
