# Phase 19: 분석 점수 신뢰도 재설계 (vision-hybrid 채점) - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

점수가 실제 자세 품질을 반영하게 만든다 — **어떤 영상이든**(보유 정은지 셋에 국한하지 않고) 정확. Phase 15 실증에서 belle가 직접 실기기 검증 중 발견한 점수 신뢰도 붕괴(정은지 '실패' 영상이 Mode1 94점/89% "거의 다 왔어요")를 근본 수정한다.

**In scope:** 채점 집계(평균→감점식) 재설계 · 비전-추론을 채점 루프에 투입(거부권/교차검증) · 표시 각도값을 점수 산출값과 정합 + 어깨 '안정성' 라벨 수정 + 안정성을 종합점수 인플레에서 분리 · Mode3 미보유동작 유효성 게이트 + 점수근거 화면 표시 · 3D 골격 실기기 미표시 버그(좌표 정규화) · 보유 fault/correct 페어 비전 비교로 known-answer 검증 앵커 확보.

**Out of scope (deferred):** 운동 명칭 직관화 카피, 입문/중급/고급 레벨 UI 개선(폴리시), 촬영 가이드 UX(별도 검토).
</domain>

<decisions>
## Implementation Decisions

### 채점 철학 (집계 방식)
- **D-01:** **IPSF 감점식 (엄격)** 으로 전환. 현재 이중 단순평균(관절→각도 평균, 차원→종합 평균)이 결함을 다수 정상 관절/차원에 희석시켜 실패 영상이 94점이 나옴. 재설계 = 100에서 시작 → 결함마다 감점, **단일 major fault가 점수를 크게 지배**(대회 심사 정합, 위양성 제거). 차원 한 개(안정성)에 휘둘리지 않는 합성(PROJECT.md '점수 신뢰도' 요건). IPSF Code of Points = 감점식 baseline ([[judging-baseline-ipsf-code-of-points]]).

### 비전 ↔ 기하학 역할 분담
- **D-02:** **기하학 주도 + 비전 거부권(veto)/교차검증.** 기하학(IPSF 감점식, 측정가능 기준)이 점수를 산출하고, 비전(Gemini 영상+RTMW 수치 추론)이 "이 점수 타당한가 · 놓친 결함 없나"를 교차검증하며 **위양성에 거부권**을 행사한다. 비전이 헤드라인 점수를 직접 주는 게 아님 — 객관성·감사가능성 유지 + 비전이 안전망. (belle Gemini-Omni 통찰의 안전한 적용; 사람 점수 라벨 금지 [[analysis-objectivity-no-human-scores]])

### 미보유 동작 처리 (IPSF·정은지에 없는 동작)
- **D-03:** **IPSF Page 9 절대 공통 트랙 + 비전 품질 판정 + 근거 명시.** 기준 동작 데이터가 없어도 reference-free 절대 트랙(자세 품질)으로 점수를 주되, "**기준 동작 없음 — 절대 자세 기준 평가**"라고 근거를 화면에 명시한다. "정은지와 89% 일치" 같은 거짓 프레이밍 금지. Mode3(MODE_SELF)에 현재 없는 유효성/근거 게이트 신설 (not_pole 게이트는 Mode1 전용 — [[mode3-scoring-basis-unknown-move-gate]]). PROJECT.md IPSF 5트랙 v1 Page-9 절대 트랙 정합.

### 범위 · 순서 (v1/v2 분할)
- **D-04:** **v1 / v2 단계 분할.**
  - **v1** = 기하학 감점식 전환(D-01) + 확정 버그 수정(3D 골격 좌표 정규화 / 어깨 '안정성' 라벨 / 표시 각도값을 점수 산출값과 정합) + Mode3 게이트·근거표시(D-03). 측정가능·결정론적·빠른 신뢰 회복.
  - **v2** = 비전 거부권/교차검증 하이브리드(D-02).
  - Phase 18(deliberate-fault eval set)으로 **v1 일반화 검증** 후 v2 진입. 증거-먼저 + overfit 방지 정합.

### 검증 전략 (belle 2026-06-18 추가)
- **D-05:** **보유 fault/correct 페어를 비전(Gemini)으로 먼저 비교 분석해 known-answer 검증 앵커를 확보한다.** "이 동작에서 정은지가 어디를 틀렸나" 정성 ground-truth + 대략적 예상 점수/각도/뻗기-갭 범위를 *알고* 재설계 채점기를 테스트 → "94점이 틀렸다"를 자동 판정 가능. 동시에 (a) 비전-추론 접근을 우리 도메인에서 조기 de-risk(비전이 실제 fault를 잡나), (b) Phase 18 eval set의 fault 라벨(영상-파생, 사람 점수 라벨 아님 — 객관성 OK)을 생성한다.
  - **경계 (절대):** 이 정성 ground-truth + 예상 범위는 **sanity 앵커 / 일반화 검증용**이지, 거기에 **임계값을 curve-fit 하는 타깃이 아니다.** 정답을 *아는 것* ≠ 거기에 *맞추는 것*. 보유 셋 overfit/teaching-to-test 금지 ([[scoring-redesign-must-generalize-no-overfit]] [[calibration-source-hard-gate]]). 검증은 미보유/above-cutoff 케이스 포함 ([[sensitivity-gate-not-just-elite-low]]).

### Claude's Discretion
- 감점 임계값(major fault 정의 등) 구체 수치, 비전 거부권 발동 조건, 표시값 정합 구현 방식, 골격 좌표 정규화 위치(reshape vs viewer group) = research/plan 단계에서 확정 (단 D-05 경계 준수 — 보유 sweep 재calibrate 금지).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 15 실증 발견 + 근본원인 (필독)
- `.planning/phases/15-mode-1-mode-3-testflight/deferred-items.md` — Phase 15 실증에서 belle가 끌어낸 갭들 + 3-갈래 심층조사 결과(집계 결함 / 측정-표시 artifact / DTW 이미 구현 / 골격 좌표 버그 + 비전 하이브리드 방향). 이 phase의 1차 근거 문서.

### 점수 계산 코드 (수정 대상)
- `backend/shared/python/sunity_shared/analysis/kismam.py` — `overall_score`(관절 가중평균, DEFAULT_WEIGHT 전부 1.0), `score_from_deviation`(100·exp(-½·(dev/20)²), tol 20°), `COACHING_FOCUS`(어깨→'안정성' 라벨 오류), `top_issues`. **감점식 전환 핵심.**
- `backend/shared/python/sunity_shared/analysis/dimensions.py` — `overall_from_dimensions`(차원 단순평균 = 종합), `DIM_STABILITY` 별도 안정성 차원.
- `backend/functions/pipeline/app.py` — MODE_EXPERT 분기(~1740-1836, not_pole 게이트 1812 = Mode1 전용), MODE_SELF 분기(~1839 = 게이트 없음), `_angles_to_mean_dict`(1515-1538, 표시값 nanmean), `_deviation_against`(1557-1569, DTW-정렬 median = 점수값), 1800-1801(user matched-window vs ref full-clip 비대칭).
- `backend/shared/python/sunity_shared/analysis/motiondtw.py` — `find_action_segment`+`dtw`+`per_joint_deviation`(median). DTW 정렬은 이미 올바름 — 표시값만 비정렬.

### 비전-추론 통합 지점 (v2)
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` — Gemini 영상 인식기(gemini-3.1-pro).
- `backend/shared/python/sunity_shared/analysis/force_signals.py`, `coach_writer.py`, `synthesis/gemini_view_reasoner.py`, `gemini/scene_finder.py` — 기존 Gemini 활용처(거부권/교차검증 재사용).

### 골격 렌더 버그 (v1)
- `app/src/components/PoseViewer3D.tsx` (reshape/camera/scale), `app/src/lib/joints.ts`(reshapePose3dData), `app/src/app/analysis/result.tsx`(628-640 joints3d 빌드). joints3d = RTMW 픽셀좌표(중심/정규화 안됨) → 카메라 밖. `backend/functions/pipeline/app.py:2328-2337` 등 joints3d 저장부.

### 채점 baseline / 원칙
- `.planning/PROJECT.md` §Core Value + '점수 신뢰도' 미완 요건(overall 취약성 / 신뢰도 게이트 / IPSF 5트랙 v1 Page-9 절대 트랙).
- IPSF Code of Points 2024-2025 (NotebookLM 자동 lookup — [[notebook-lm-pole-sports]]).

### 검증 자산
- 정은지 fault/correct 페어 (`~/Downloads/정은지 선수 추가 영상/` + S3 `fixtures/phase15/{motion}/correct|fault.mp4`, `backend/scripts/phase15_keys.json`). [[jeongeunji-success-fail-pair-dataset]]
- ROADMAP Phase 18 (deliberate-fault eval set) — 이 검증과 병합.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kismam.score_from_deviation` / `assess` / `top_issues` — 관절별 편차→점수 인프라 존재. 감점식은 집계(overall_score)와 종합(overall_from_dimensions) 교체가 핵심, 관절 편차 산출은 재사용.
- `motiondtw` 2단계 정렬(find_action_segment + banded DTW + global fallback) — 이미 올바름. 표시값을 이 정렬 median으로 바꾸면 표시-점수 정합 해결.
- 기존 Gemini 어댑터(recognizer/force/coach/scene/view) — 비전 거부권 v2의 호출 패턴 재사용.

### Established Patterns
- contract 3중 동기화(app/src/types/analysis.ts ↔ models.py ↔ contract.md) — 점수/차원 schema 변경 시 함께 수정.
- adapter 경계(heavy deps lazy-import) — 비전 거부권도 adapter Protocol로.
- Firestore flat 저장(nested-array 금지) — joints3d 정규화는 읽는 쪽(reshape) 또는 저장 schema 결정.

### Integration Points
- `pipeline/app.py::_process` MODE_EXPERT/MODE_SELF 분기 = 감점식 집계 + Mode3 게이트 + 비전 거부권 투입 지점.
- `assemble.build_mode1/build_mode3/build_dimension_explanation` = 점수근거·표시 카피.
- `result.tsx` = 표시값/근거/골격 렌더.
</code_context>

<specifics>
## Specific Ideas

- belle: "정은지라 아무리 못하게 하려고 해도 89%는 그러려니 하지만, 영상 자체에 문제가 많이 보이는데 이 점수는 기준이 심각하게 이상함" — 점수가 실제 품질을 반영해야 (fault→낮은 점수).
- belle (D-05): "두 영상을 비교해보니 정은지 선수가 어디를 틀렸군요 — 그렇게 정보를 알고 있는 상태에서 테스트하면 더 좋지 않겠냐" = known-answer 검증.
- belle: 점수화 *아니어도* 비전이 fault 위치를 짚는 것 자체가 가치(Phase 18 라벨 + v2 de-risk).
</specifics>

<deferred>
## Deferred Ideas

- **운동 명칭 직관화** — 엘보 트위스트 시스터 / 폭스탑 / 콤보 음차·전문용어 + 보완운동 영문명(Farmer's Walk)이 비직관적. 용어 직관화 후속 (별도 phase, [[studio-term-3branch-system]] [[terminology-multimap-future]]).
- **입문/중급/고급 레벨 UI** — belle: "허접한 느낌, 세 개 중 하나만 선택되니 애매". 레벨 표시 UX 개선 (v1 폴리시 또는 별도).
- **촬영 가이드 UX** — 전문가 영상 먼저 보고 비슷한 시작점에서 촬영하라는 촬영 팁(belle #6). DTW 정렬은 이미 됨 — 이건 순수 UX 안내. 별도 검토.
</deferred>

---

*Phase: 19-vision-hybrid*
*Context gathered: 2026-06-18*
