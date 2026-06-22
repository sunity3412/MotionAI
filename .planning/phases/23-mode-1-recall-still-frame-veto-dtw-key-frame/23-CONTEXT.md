# Phase 23: Mode 1 결함 recall 복구 — still-frame veto + 기준선 정량화 - Context

**Gathered:** 2026-06-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Mode 1(정은지 기준 비교) veto/비교의 **입력 방식**을 "영상 통째 Gemini 업로드"에서 "DTW worst-pose **단일 key-frame(들)** + 부위별 프롬프트 + 프레임×부위 union + N-sample"으로 교체해, 전체영상 VLM이 구조적으로 놓치던 **상체 결함(팔-폴 갭/고개젖힘/팔꿈치) recall을 복구**한다. 위양성은 늘리지 않는다(깨끗 프레임/정타 = none 유지). 더불어 결함 출력에 **기준선 정량화 레이어**(각도=직접 측정 / 거리=몸-상대 칸·층 / 기준선=동작별)와 **증상→root cause(힘/폴밀착) 묶음 코칭**을 추가한다. Mode 3에도 동일 정렬·정량화를 적용한다.

**근거:** 2026-06-22 deep-research(소스 23개, 18 confirmed — whole-video VLM은 프레임 독립 인코딩으로 미세 결함을 놓치는 구조적 한계) + B 스파이크(kip-up: whole-video=다리만, 5프레임 배치=팔1, **단일 프레임=좌/우팔+고개 풀 recall, 위양성 0**). 레버는 프롬프트가 아니라 **입력 granularity**임이 실증됨.

**경계 (scope creep 아님):** 채점 수식(KISMAM tol/감점 공식) 변경 아님 — veto **입력**과 출력 정량화에 집중. 자체 모델 파인튜닝은 Phase 22. reference 등록은 Phase 21. 구현/eval = Pod GPU 필요.

</domain>

<decisions>
## Implementation Decisions

### D-01: Mode 1 veto 입력 형태 = 학생 + 정은지 still 나란히
학생 worst-pose frame + **DTW로 매칭된 정은지 same-pose frame**을 나란히(side-by-side) Gemini에 입력한다. Mode 1의 "정은지 기준 비교" 설계를 유지하고 상대 편차를 포착하며, 기존 v7.0 비교 프롬프트(`_COMPARISON_PROMPT`)와 정합. (대안: 학생 단일 frame만 IPSF 평가 — 스파이크 방식, recall은 되나 reference 기준점 의미 약화 → 채택 안 함.)

### D-02: 정량화 표현 + v1 범위 = 각도 수치 + 몸-상대 칸/층 텍스트 (시각 오버레이 바로 후속)
v1 출력 = ① **관절각 직접 수치**("무릎 145° vs 정은지 178°, 33° 더 굽음, ↑펴라") + ② **거리는 몸-상대 칸/층 텍스트**("정은지 3칸, 너 2칸 ⅔"). 절대 cm/m 금지(단일 카메라 스케일 모호, 140/150 깨짐). **화살표 + 칸 시각 오버레이**는 기존 fault-zoom 확대비교 이미지 위에 **후속(v1.1)** — v1은 텍스트+각도 먼저, 백엔드 계산·저장까지(앱 표시는 후속 UI phase, D-07). "칸" = keypoint/폴/바닥 baseline 에서 **결정적 계산**한 정수 칸("정은지 3칸, 너 2칸 ⅔") — **percent 표기 금지**(`_SCORE_PATTERN` 누수, D-08). VLM 이 칸 수치를 지어내지 않음.

### D-03: DTW 정렬 신뢰도 폴백 = 다중프레임 union → 보류+표시
정렬 신뢰도(`MotionMatch.distance`)가 낮으면(시작점/템포 상이) 단일 프레임 대신 **worst-pose ±윈도우 다중프레임 union**으로. 그래도 낮으면 **veto 보류 + "비교 신뢰도 낮음" 표시**(거짓결함 fabrication 금지 — 객관성·위양성 게이트). 전체영상 폴백은 채택 안 함(그게 상체를 놓치는 원인이라).

### D-04: 증상→root cause 묶음 = Gemini 추론, "~로 보임" 가설
Gemini가 결함군(예: 팔꿈치 굽음 + 고개젖힘 동시)을 보고 가능한 root cause(힘 부족/폴 밀착 풀림)를 **기존 dual-coach "원인" 섹션에서 추론**한다. 단정 금지 — "~로 보임" 가설 형태(객관성: 사람-라벨 원인을 ground truth로 박지 않음). 룰기반 매핑은 brittle → 채택 안 함. (belle 도메인: 폴 자세는 힘/밀착이 root, 고개젖힘·삐뚤어짐은 동반 증상 = 창발 시스템.)

### D-05: recall 완전성 = 프레임×부위 union + N-sample
단일 호출은 1~2개만 보고(과소열거) → 부위별(상체/하체/라인) 프롬프트 × 선별 key-frame을 union하고, Phase 20의 N-sample 집계(`VISION_VETO_SAMPLES`, rank-median)를 still 경로에도 적용해 흔들림을 줄인다.

### D-06: 객관성·일반화·위양성 게이트 (불변)
- 사람 점수 라벨 ground truth 금지 — VisionVerdict에 score 필드 영구 부재 유지([[analysis-objectivity-no-human-scores]]).
- known-answer에 맞춘 유도 프롬프트/curve-fit 금지 — 프롬프트는 generic, recall은 자체 라벨셋으로 측정([[scoring-redesign-must-generalize-no-overfit]]).
- 깨끗 프레임/정타 = none 유지(스파이크 확인 — 특이도 보존). 결정론(같은 입력=같은 verdict) 유지.

### D-07: 스코프 정정 (belle 2026-06-22, cross-AI 리뷰 후)
- **Mode 1 집중. Mode 3 정량화/정렬은 공식 defer** → Backlog B-15a("Mode 3 즉석 2영상 비교")로 합류. 본 phase 는 Mode 1 still-frame veto + 정량화/코칭 백엔드.
- **정량화·코칭 = 백엔드 계산·저장·생성까지.** 앱 표시(result.tsx 각도/칸 렌더, coach-report 원인섹션 렌더)는 **후속 UI phase** 로 분리. SC#4/#5 "표시"→"계산·저장/생성"으로 정정(ROADMAP 반영). (D-02 시각 오버레이 v1.1 방침과 일관.)

### D-08: cross-AI 리뷰 hardening (Codex HIGH 반영)
- **precision/support 게이트** — part×frame union 이 단발 환각 결함을 살리지 않도록, differences 는 최소 support(샘플/프레임 N 중 K 이상)일 때만 인정, 미만은 descriptive-only/폐기. 위양성 비증가(D-06) 강화.
- **칸/층 = 결정적 기하 계산.** keypoint + 폴축(pole_geometry)/바닥/엉덩이-라인 baseline 에서 reach 를 계산 — **Gemini 가 수치를 지어내지 않음**. body_normalization 비율은 보조. **percent("100%") 표기 절대 금지** — `_SCORE_PATTERN` 누수 가드에 걸려 정상 verdict 가 폐기됨. "정은지 = 3칸" 식 정수 칸만.
- **provenance 필드** — 측정값은 `source: "geometry" | "vision_hypothesis"` + confidence/가시성 표기(특히 root-cause 가설).
- **DTW 신뢰도 = 글로벌+로컬.** `MotionMatch.distance`(글로벌) 만으로 부족 → 선택 프레임 주변 path 밀도/ref-frame 존재/keypoint 가시성·blur 로컬 신뢰도 추가. worst_pose_timestamp 가 상체 결함 프레임이 아닐 수 있음 — 부위별 worst 후보 고려.
- **23-01 배선 명시** — `_apply_vision_veto` 시그니처/콜사이트가 `reference_dtw_match`/ref angles 를 받도록 변경 명시. still-pair API(이미지 경로·프레임 메타·part scope·selector version) 정의. 캐시 키에 selector version/frame indices/top-K/window 포함.
- **23-03 eval = 실제 production 경로** — 어댑터 직접호출 아니라 `_apply_vision_veto` 전체 경로 통과. whole-video baseline 을 **동일 모델/버전으로 재실행**(apples-to-apples). 케이스 매트릭스 확장(elite clean/imperfect clean/occluded/tempo-shifted/spinning/known-fault). cold vs warm 캐시 결정론 분리. cost/latency 게이트 + machine-checkable pass/fail 필드.
- **호출수 상한 강화** — `MAX_VETO_CALLS` 가 호출수뿐 아니라 upload count + wall-clock budget 도 bound. File API 핸들은 추적 list 에서 일괄 delete.

### Claude's Discretion
- key-frame 선별 알고리즘 세부(worst-pose 선정 기준, ±윈도우 크기, top-K), 부위 분할 경계(skeleton.JOINT_TO_PART 확장: 머리/그립 추가), N-sample 수, 캐시 키에 input_granularity 반영 방식, 비용 상한(호출수 bound) — 구현 디테일은 planner/executor 재량(게이트 D-06 준수 하에).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Vision veto 어댑터 (교체 대상 핵심)
- `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` — veto 어댑터. `assess_fault_severity()`(COMPARISON/SINGLE), `_upload_video()`(영상 통째 — **이 입력을 still로 swap**), `_call_gemini_comparison()`/`_COMPARISON_PROMPT`(v7.0 ①→⑧), `_aggregate_comparison_verdict()`(N-sample rank-median), `build_schema()`(no-score), `VisionVetoCache`(키에 `input_granularity` 포함 — frame-input swap 대비 이미 설계됨), File API `client.files.delete` 정리.
- `backend/shared/python/sunity_shared/analysis/vision_veto.py` — `apply_downward_cap()`(하향 전용 cap), `fault_joints_from_differences()`(부위→키포인트), `worst_pose_timestamp()`(worst-pose 시점).
- `backend/functions/pipeline/app.py` — `_apply_vision_veto()` (≈1662-1767, swap 지점), `_process()`, B1 DTW wiring(≈2411 `_deviation_against`/`reference_dtw_match`), reference/prev profile fetch(≈2360 Mode1, ≈2494 Mode3).

### DTW 정렬 + 프레임 매칭 (still 선별 기반)
- `backend/shared/python/sunity_shared/analysis/motiondtw.py` — `find_action_segment()`(시작점), `dtw()`(워핑), `MotionMatch.distance`(**정렬 신뢰도 신호 — D-03 게이팅**), `per_joint_deviation()`(median).
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — `_matched_ref_frame()`(학생↔정은지 same-pose 프레임 쌍 — **D-01 나란히 still 재사용**), `build_fault_zoom_comparisons()`(확대비교 carousel — **D-02 시각 칸/층 오버레이 후속 위치**).

### 정량화 기반 (각도/거리/사이즈)
- `backend/shared/python/sunity_shared/analysis/features.py` — `compute_joint_angles()`(3D 관절각, 스케일 무관 → D-02 각도 직접).
- `backend/shared/python/sunity_shared/analysis/dimensions.py` — `JOINT_ANGLES`(8 관절), `line_score`.
- `backend/shared/python/sunity_shared/analysis/skeleton.py` — `JOINT_TO_PART`(상체/코어/하체 — D-05 부위 분할 시드), `JOINT_KEYS`.
- `backend/shared/python/sunity_shared/analysis/body_normalization.py` + `body_normalization_measurer.py` — 상대 스케일 프로파일(arm/leg/torso/height ratio — D-02 몸-상대 거리 기반).

### 진입점 / 로드맵
- `backend/runpod_inference/server.py` — `POST /analyze` (단일 분석 진입, X-RunPod-Token).
- `.planning/ROADMAP.md` — Phase 23 (Goal/Success Criteria/게이트).

### Pod 산출물 (스파이크 근거 — eval 시드)
- `/workspace/spike_kipup_granularity_result.json` (pod) — 3-way(A/B1/B2) 결과.
- `/workspace/spike_perframe_upper_result.json` (pod) — 단일프레임 풀 recall 실증.
- `backend/research/spikes/reports/spike_vision_grounding_kip-up.json` — whole-video baseline(상체 0).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **gemini_vision_scorer 어댑터 경계**: 입력만 whole-video→still로 swap하면 됨. N-sample 집계·캐시·no-score 스키마·File 정리는 그대로 재사용. 캐시 키에 `input_granularity`가 이미 있어 frame-input verdict가 whole-video verdict와 충돌 안 함(20-02 설계).
- **fault_zoom._matched_ref_frame**: 학생↔정은지 same-pose 프레임 쌍이 이미 계산됨 → D-01 나란히 still 입력에 그대로 사용.
- **fault_zoom.build_fault_zoom_comparisons**: 확대비교 carousel 산출 → D-02 칸/층 시각 오버레이가 얹힐 자리.
- **MotionMatch.distance**: 정렬 신뢰도 신호가 이미 산출됨 → D-03 게이팅 임계만 추가.
- **compute_joint_angles + JOINT_ANGLES**: 스케일 무관 각도가 이미 계산·저장(keypointReport) → D-02 각도 직접 출력에 사용.
- **body_normalization 프로파일**: 학생·정은지 둘 다 측정·저장·wiring(force_signals 포함) → D-02 몸-상대 거리 정규화 기반.

### Established Patterns
- 어댑터 경계 + lazy-import(google.genai), VisionVerdict 객체(no-score 영구), temp 0 + 캐시 결정론, downward-only cap(비전이 점수 못 올림).
- Firestore nested-array 금지 → (T,J)는 flat 저장 + 읽는 쪽 reshape.
- 분석 코어는 numpy-only 순수 함수, 무거운 deps(genai/ffmpeg)는 어댑터 뒤.

### Integration Points
- `_apply_vision_veto` (pipeline/app.py) = 입력 swap의 단일 지점.
- `VisionVerdict` 스키마 = 정량화 필드 추가 시 객관성(score 부재) 유지.
- 앱 `result.tsx` + fault-zoom carousel = 정량화 표시/시각 오버레이 후속.

</code_context>

<specifics>
## Specific Ideas

- 칸/층 표현 예시(belle): "정은지 선수는 3칸 올라갔는데 너는 2칸, 2칸 ⅔ 올라갔다" + 화살표로 방향.
- 기준선은 동작별: kip-up=바닥, 공중 동작=폴(수직, 항상 프레임 내)/엉덩이 라인.
- 고개 젖힘 사례: belle 추정 "결함에 가까움" + Gemini 단일프레임 독립 판정("목 뒤로 젖혀져 정렬 무너짐") 수렴 → 결함으로 다루되 하드 라벨 금지.
- 검증: 시작점/템포가 정은지와 다른 일반 사용자 케이스(Mode 1 정상 상황)로 프레임선별이 거짓결함을 만들지 않는지 별도 검증 task.

</specifics>

<deferred>
## Deferred Ideas

- 화살표 + 칸/층 **시각 오버레이** 풀 구현 — v1.1(확대비교 이미지 위, v1은 텍스트+각도 먼저).
- **앱 표시(result.tsx 각도/칸 렌더 + coach-report 원인섹션 렌더)** — 후속 UI phase(D-07; 본 phase 는 백엔드 계산·저장·생성까지).
- **Mode 3 still-frame 정량화/정렬** — Backlog B-15a 합류(D-07; 본 phase Mode 1 집중).
- 자체 비전 모델 파인튜닝(오픈 모델) — Phase 22.
- reference 셀프 등록 자동화 — Phase 21.
- AQA-style part-aware contrastive 점수 모델 — 라벨 데이터셋 확보 후 중장기(리서치 중장기 트랙).

</deferred>

---

*Phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame*
*Context gathered: 2026-06-22*
