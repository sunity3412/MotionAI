# Phase 09: ForceDirectionPattern + 실패 원인 후보 3개 - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 8 + Phase 8.1 의 산출 (`ForceSignalsReport` umbrella: phaseBoundaries + axisMetrics tilt-only + stabilityMetrics + contactMetrics) 위에 **추론 레이어**를 얹어 두 산물을 박제한다:

- `inferForceDirectionPattern` → 5종 ForceDirectionPattern (`pull` / `push` / `brace` / `rotate` / `release`) phase 별 반환
- `ForcePatternInference.findings: ForcePatternFinding[]` (실패 원인 후보 Top-3 카드 데이터)

본 phase 가 산출 (output 본체):

- 신설 모듈 `force_pattern.py` (추론 전용, `force_signals.py` 진단 신호 layer 와 분리 — Phase 8 D-08-C3 패턴 정합)
- `ForcePatternFinding` + `ForcePatternInference` Python dataclass + TS interface + docs/contract.md §9.5 3-way lockstep
- Layer 1 motion-agnostic 룰 (research §4.2 영상 신호 표 → 5종 pattern 매핑) — pure-function deterministic
- Top-3 ranking (signal_weight × confidence 정렬 + tie-break)
- Korean canned interpretation mapping (sourceSignal × modeContext, 24 카피)
- pipeline `_process` wiring — `compute_force_signals` 호출 직후 `infer_force_direction_pattern` 추가
- Firestore `forcePatternInference` 신설 필드 + `_validate_force_pattern_inference` scoped validator
- 단위 test + 금지 표현 grep gate (research §10.2 + 신규 6종)

본 phase 가 산출 X (downstream / 다른 phase 영역):

- 자연어 번역 / 풍부화 / Cerebras LLM → Phase 11 (CoachCommentHook)
- 부상 위험 신호 플래그 → Phase 10 (SAFE-01)
- 영상 위 오버레이 좌표 / 실측 각도 노출 → Phase 12
- 보완 운동 매핑 → Phase 13
- EMG / 근육 활성 / 챔피언 근력 측정 → v2 (research 02 §13)
- Gemini multimodal 호출 (추론 보강) → 영구 X (Phase 11 책임, Phase 9 = deterministic Layer 1 단독)

</domain>

<decisions>
## Implementation Decisions

### (A) Pattern Inference 룰 — Layer 1 motion-agnostic baseline

- **D-09-A1**: **research §4.2 force flux 실패 신호 8행 표 → 5 pattern 매핑** 을 Layer 1 baseline 룰로 박제. 단, Phase 9 v1 scope = **Phase 8 산출 신호만 cover** (axis_tilt / pelvis_drop / late_contact / high_jitter / high_jerk / abnormal_release 6종). "어깨 elevation" / "elbow lock" 절대 joint angle 패턴은 features.py 통합 필요 → **v2 or 후속 plan** 으로 deferred.
  - axis_tilt (shoulder_tilt 또는 hip_tilt > 20°) → `release` (코어/골반 고정 부족)
  - pelvis_drop (hip_tilt >> shoulder_tilt + axis warning 부재) → `release` (상체 보상)
  - late_contact (contactMetrics phase=`lock` 에서 estimatedStable=false OR nearPoleRatio < 0.5) → `brace` (레그락/내전근 타이밍)
  - high_jitter (jitterScore > Phase 8 JITTER_SEVERITY_THRESHOLDS medium=8.0) → `unknown` (유지 근력/호흡)
  - high_jerk (jerkScore > Phase 8 JERK_SEVERITY_THRESHOLDS medium=5000.0) → `unknown` (힘 전달 부드러움 부족)
  - abnormal_release (axisMetrics.warnings 에 `abnormal_release_during_hold` 포함) → `release` (hold 중 접촉 풀림)
- **D-09-A2 (CORE GUARD — Codex C-M4 / Phase 8.1 D-05 정합)**: **`axisMetrics[*].severity` 직접 trust 영구 차단**. raw `shoulder_tilt` + `hip_tilt` + `confidence` + `warnings` 만 사용. Phase 9 plan boundary 안에서 severity 사용 시 acceptance reject. 단, axis 가 아닌 **stabilityMetrics / contactMetrics severity 는 사용 가능** (guard scope 외, Phase 8 본체 신뢰).
  - **Tilt 임계값 source** = Phase 8.1 D-03 의 `ipsf_tolerance.tolerance_deg = 20.0°` (`backend/judging_data/tilt_thresholds.yaml::ipsf_tolerance`). IPSF Aerial Pole CoP Page 63 S55 Iron X (±20°) citation 박제. severity calibration 과 분리.
  - **axis warnings 무시 룰**: warnings 에 `axis_metric_transitional` 또는 `tilt_unavailable` 또는 `tilt_thresholds_fallback` 포함 시 → 해당 axisMetric raw tilt 도 무시 (Phase 8.1 sensitivity gate 미통과 신호). finding 생성 X + `axis_signal_unavailable` warning 박제.
- **D-09-A3**: **phase 별 multiple finding 가능**. 1 phase 에서 release + brace 동시 emit 가능 (signal 별 독립 검출). `inferForceDirectionPattern` 출력 = phase 별 list[ForcePatternFinding], aggregate findings (전체) = Top-3 ranked.
- **D-09-A4**: **phase 미인식 fallback** — Phase 8 의 phaseBoundaries 가 entry/lock 미검출 (`entry_not_detected` warning) 시 → 해당 phase 에 대해 signal 검사 skip + `phase_unavailable_for_inference` warning. 분석 죽지 않음 (Phase 8 D-08-A4 정합).
- **D-09-A5**: **Confidence base 산식** — `finding.confidence = base_confidence × phase_metric_confidence_factor`. base_confidence = signal 별 fixed (axis_tilt=0.72 / pelvis_drop=0.72 / late_contact=0.70 / high_jitter=0.63 / high_jerk=0.63 / abnormal_release=0.75, research §8 정합). phase_metric_confidence_factor = 해당 phase 의 axisMetric.confidence 와 stabilityMetric.confidence 의 중 작은 값 (0~1). 산식 = `base × confidence_factor` → [0, 1] 범위.

### (B) Top-3 Ranking + 후보 Pool — KISMAM Top-3 진화

- **D-09-B1**: **후보 pool** = D-09-A1 의 6 signal × 5 phase = 최대 30 candidate. signal 별 detection threshold 미통과 시 candidate 생성 X (fabrication 금지).
- **D-09-B2**: **정렬 기준** = `score = confidence × signal_weight`.
  - signal_weight: `axis_tilt=1.0` / `pelvis_drop=1.0` / `late_contact=0.95` / `abnormal_release=1.1` (release 직접 신호 priority) / `high_jerk=0.85` / `high_jitter=0.80` (gross signal — domain priority 낮음).
- **D-09-B3**: **tie-break** = (1) phase priority `lock > hold > transition > final_shape > entry` (lock = 자세 형성 결정 구간) → (2) signal priority `axis > contact > stability` (도메인 객관성 순서) → (3) confidence 큰 순.
- **D-09-B4**: **후보 부족 시 처리** — emit 된 candidate 가 0~2 개일 때 빈 슬롯 pad X. `ForcePatternInference.findings` 길이 [0, 3]. **0개 시** → `overallConfidence='low'` + `warnings=['no_significant_force_pattern_signal']` + interpretation 본체 = "이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다. 강사와 함께 확인하는 것을 권장해요." (강제 finding fabrication 금지 — [[analysis-objectivity-no-human-scores]] / [[mode3-progress-not-similarity]] 정합).
- **D-09-B5**: **pattern 분포 cap** — 동일 pattern 중복 finding 시 confidence 가장 높은 것 1개만 emit (Top-3 안 동일 pattern 중복 차단 — UX 다양성 박제). 단 phase 다른 동일 pattern (예: `release@lock` + `release@hold`) 은 다른 finding 으로 인정.

### (C) Layer 2 (Gemini) — 영구 차단, Layer 1 단독

- **D-09-C1**: **Phase 9 = Layer 1 단독, Gemini 추론 호출 영구 차단**.
  - **Why**: Phase 11 책임 = "Gemini 자연어 번역만, 좌표·판단·점수 출력 금지" (ROADMAP Phase 11 SC #3). Phase 9 가 Gemini 호출해 패턴 분류 시 "판단 출력" 금지 위반.
  - **Why**: Phase 9 추론은 deterministic + 객관 임계 (IPSF tolerance + Phase 8 fixed threshold) 박제. 비결정적 LLM 으로 객관성 훼손 X.
  - **Why**: Phase 8 Layer 2 (Gemini key_moment timestamp 보강, `FORCE_SIGNALS_LAYER2_ENABLED` env) 은 phase 분할 정확도 향상 (위치 측정) — 패턴 추론 자체 X. Phase 9 는 phaseBoundaries 입력으로 받아 신호 처리만 → Layer 2 영향 X (자동 정합).
- **D-09-C2**: **motion_id 인식 시 confidence 보강** — `compute_force_signals` 입력의 motion_id 인식 (Phase 5 산출) 시 → finding confidence × 1.05 (max 1.0 cap). 미인식 시 보강 X (motion-agnostic Layer 1 단독 = Phase 8 D-08-A4 정합). 새 motion 추가 시 박제 부담 0.
- **D-09-C3**: **자연어 번역은 Phase 11 책임** — Phase 9 = canned Korean interpretation mapping 박제. Phase 11 CoachCommentHook 이 `autoFindingsSummary` 에서 Phase 9 finding 을 LLM 풍부화 (강사 보조 layer). Phase 9 → Phase 11 책임 경계 명시.

### (D) ForcePatternFinding Schema + 카피 mapping + 노출 깊이

- **D-09-D1**: **ForcePatternFinding Python dataclass + TS interface** 박제 (8 필드):
  ```ts
  type ForcePatternFinding = {
    pattern: 'pull' | 'push' | 'brace' | 'rotate' | 'release' | 'unknown';
    phase: MotionPhase;
    sourceSignal: 'axis_tilt' | 'pelvis_drop' | 'late_contact'
                | 'high_jitter' | 'high_jerk' | 'abnormal_release';
    reason: string;              // EN — research §8 패턴 영문 1 sentence (debug + LLM input)
    interpretation: string;       // KO canned — 가능성 언어 (research §10.1 톤)
    confidence: number;           // [0, 1]
    jointHint: string | null;     // 부위 키워드 — '고관절' / '코어' / '광배' / '내전근' / null (research §10.1 부위별 원인 언어)
    warnings: string[];           // signal-specific (e.g. 'axis_signal_unavailable')
  };

  type ForcePatternInference = {
    version: string;
    findings: ForcePatternFinding[];   // Top-3, length 0~3
    overallConfidence: MetricConfidence;
    warnings: string[];                 // umbrella (e.g. 'no_significant_force_pattern_signal')
    modeContext: 'mode1' | 'mode3_first' | 'mode3_progress';
  };
  ```
- **D-09-D2**: **interpretation canned mapping table** = `(sourceSignal × modeContext)` → KO 1 sentence. 6 signal × 3 modeContext = **18 카피** (phase 분기 X — Phase 9 v1 단순화. Phase 11 LLM 통합 시 phase-aware 변환 자연 확장).
  - 톤: research §10.1 권장 (가능성 언어 + 부위별 원인 + 강사 보조).
  - mode 분기 카피 (Phase 7 D-07-D3 + Phase 12.5 패턴 정합):
    - `mode1` → "정은지 선수 기준 패턴과 비교했을 때, …"
    - `mode3_first` → "이번 첫 분석에서, …"
    - `mode3_progress` → "지난 영상 대비, …"
  - 위치: 신설 `backend/shared/python/sunity_shared/analysis/force_pattern_copy.py` (Phase 7 `copy_templates.py` 패턴 정합) — stateless dict literal singleton.
- **D-09-D3**: **금지 표현 grep gate** — research §10.2 6종 + Phase 9 신규 4종:
  - research §10.2: `광배 N% 부족` / `근력이 부족` / `전완 힘이 약` / `이 자세는 틀렸` / `AI가 정확히 측정` / `부상 위험 확정`
  - 신규 4종: `근육 힘 방향.*확정` / `힘이 정확히` / `프로보다 못합` / `\d+%.*감점` (수치 단독 노출 차단)
  - 단위 test: `force_pattern_copy.py` 의 모든 canned + `_force_pattern_canned_text` helper 출력 → 10종 grep 검증. 회귀 차단.
- **D-09-D4**: **evidence 수치 raw 값 노출 X** — interpretation 본문 = canned KO sentence 만. raw shoulder_tilt 값 (예: "87°"), jerkScore 값 등 수치 단독 노출 = research §10.2 피해야 할 표현. **Phase 12 (실측 각도 표시) 책임 — Phase 9 = canned 만**.
- **D-09-D5**: **UI hint = 없음** (ROADMAP Phase 9 entry 명시 X). 결과 화면 노출 = Phase 12 / 12.5 (downstream consume). Phase 9 = backend canned data 박제만.
- **D-09-D6**: **mode 분기 카피** — pipeline 의 `_process` 가 `analysis.mode` (mode1/mode3) + Firestore 의 mode3 first/progress 판단 → `modeContext` 산출 → `infer_force_direction_pattern(..., mode_context=...)` 전달. mode3 first vs progress 분기 룰 = Phase 12.5 `_select_mode3_subcontext` 패턴 재사용 (이전 분석 doc 존재 여부).

### (E) Plan 구조 — 2 Wave (RunPod 불필요, pure-function)

- **D-09-E1**: **2 wave 구조** (Phase 8.1 D-06 패턴 정합 — wave 단위 위험 차원 분리):
  - **Wave 0** — Schema lockstep: `ForcePatternFinding` + `ForcePatternInference` TS interface (`app/src/types/analysis.ts`) + Python dataclass (`force_pattern.py` 신설) + docs `§9.5` 신설 + `AnalysisDoc.forcePatternInference?: ForcePatternInference | null` 필드 (단일 atomic commit). Firestore validator `_validate_force_pattern_inference` 신설. Frontend `userAnalyses.ts` normalize null-guard.
  - **Wave 1** — Inference 본체: `infer_force_direction_pattern(force_signals_report, motion_id, mode_context) → ForcePatternInference` pure function 박제 (6 signal detection rules + Top-3 ranking + canned interpretation mapping import). `force_pattern_copy.py` 18 canned 박제. pipeline `_process` wiring (`compute_force_signals` 직후 1줄 호출 + `complete_analysis(force_pattern_inference=...)` 저장). 단위 test (signal detection + ranking + tie-break + 후보 0/1/2/3 케이스 + mode 분기) + 금지 표현 grep gate.
- **D-09-E2**: **Wave 2 (production sweep) 불필요** — RunPod 재배포 / 정은지 5영상 재sweep evidence 박제 **본 phase scope OUT**. 근거:
  - (a) Phase 9 = pure-function pipeline downstream (RunPod GPU 무관 — RunPod 는 NLF/RTMW pose estimation 만, Phase 9 는 force_signals 산출 위 pure inference).
  - (b) Phase 8.1 SWEEP-EVIDENCE 가 raw shoulder_tilt/hip_tilt 의 정은지 25/25 분포 + sensitivity 5/5 PASS 검증 완료 → Phase 9 inference 의 입력 신호 정합성 이미 박제.
  - (c) Phase 9 의 sweep 검증 = mode1/mode3 실 영상 검증 = Phase 15 (Mode 1·Mode 3 실영상 + 신뢰도 게이트 + TestFlight) scope.
  - **Phase 11 통합 시점에 자연 검증** — Phase 11 LLM 풍부화 + 실 영상 mode1/mode3 → Phase 9 finding 노출 정합성 동시 확인.
- **D-09-E3**: **Plan checkpoint** — Wave 1 완료 후 belle 박제 검수 (canned 18 카피 + 금지 표현 grep gate). plan-review (cross-AI Codex) 권장 (Phase 8.1 패턴 정합).

### Universal Principle (Phase 9 전반)

- **D-09-U1**: **3-way contract lockstep** — `app/src/types/analysis.ts` ↔ `backend/shared/python/sunity_shared/analysis/force_pattern.py` ↔ `docs/contract.md §9.5` 단일 atomic commit (Phase 6/7/8/8.1 패턴 정합).
- **D-09-U2**: **Pure function + numpy only** — `force_pattern.py` 도 순수 함수 (boto3 / 네트워크 / LLM 무관). Layer 2 영구 차단 (D-09-C1) → singleton adapter 불요. 단위 test 가능.
- **D-09-U3**: **Frozen dataclass + `__post_init__` validator** — `ForcePatternFinding` (pattern enum 6종 + sourceSignal enum 6종 + confidence [0,1] + interpretation non-empty) + `ForcePatternInference` (findings length 0~3 + modeContext enum 3종) validator.
- **D-09-U4**: **camelCase 변환** — `_dataclass_to_camel_case_dict` 박제 자동 적용 (`source_signal` → `sourceSignal` / `joint_hint` → `jointHint` / `mode_context` → `modeContext`).
- **D-09-U5**: **Firestore nested-array 금지** — `forcePatternInference.findings: list[dict-of-scalars-only]` 박제 (`_validate_force_pattern_inference` scoped validator — Phase 7/8/8.1 패턴 정합). [[firestore-nested-array-flat]] 정합.
- **D-09-U6**: **단정 금지 grep gate** — D-09-D3 정합. 단위 test 회귀 차단.

### Claude's Discretion (planner / researcher 영역)

- `force_pattern.py` 신설 모듈 vs `force_signals.py` 확장 — 신설 권장 (Phase 8 D-08-C3 분리 패턴 정합, 진단 신호 vs 추론 분리), planner 최종 결정.
- 18 canned KO interpretation 정확한 본문 — Claude 가 research §10.1 톤 + 부위별 원인 어휘 박제. plan 단계 belle 검수.
- `joint_hint` 부위 어휘 매핑 (sourceSignal → 부위 키워드) — researcher / planner 박제 후 belle 검수.
- `phase_metric_confidence_factor` 산식 디테일 (min vs avg vs weighted) — planner 결정.
- Firestore scoped validator 의 정확한 화이트리스트 schema — planner 박제.
- pipeline `_process` 안 `infer_force_direction_pattern` 호출 위치 — `compute_force_signals` 직후 권장.
- `modeContext` 산출 룰 (mode3 first vs progress 판단) — Phase 12.5 `_select_mode3_subcontext` 재사용 가능 여부 planner 확인.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### ROADMAP / REQUIREMENTS

- `.planning/ROADMAP.md` §Phase 9 (line 277-291) — goal + 4 SC + Axis raw signal only guard + deps (Phase 8 평행 진입 OK)
- `.planning/REQUIREMENTS.md` FORCE-01 — Phase 8 신호 + Phase 9 패턴 추론 + Top-3 카드
- `.planning/REQUIREMENTS.md` FEED-02 — 피드백이 "실패 원인 후보 3개 카드 → 내 몸 기준 힘 쓰는 방향·중심축 → 필요한 유연성/근력 → 보조 동작" 순서 (Phase 9 는 1번째 항목)

### Phase 8 / 8.1 산출 (upstream — Phase 9 입력 본체)

- `backend/shared/python/sunity_shared/analysis/force_signals.py` — `ForceSignalsReport` (umbrella) + `AxisDeviationMetric` (tilt-only Phase 8.1 D-01) + `StabilityMetric` (jerk/jitter Plan 08-02) + `ContactStabilityMetric` (evidence-with-confidence Plan 08-00 R3) + `PhaseBoundary` (5단계 분할)
- `backend/shared/python/sunity_shared/analysis/force_signals.py:1067-1161` — `compute_axis_deviation` tilt-only 본체 (Phase 8.1 Wave 1)
- `backend/shared/python/sunity_shared/analysis/force_signals.py:1220-1300` — `compute_stability_metrics` (FPS-normalized jerk + jitter)
- `backend/shared/python/sunity_shared/analysis/force_signals.py:1442-1553` — `compute_contact_stability` (evidence-with-confidence)
- `backend/shared/python/sunity_shared/analysis/force_signals.py:1578-1693` — `compute_force_signals` umbrella + overall_confidence + abnormal_release 감지
- `backend/shared/python/sunity_shared/analysis/force_signals.py:170-180` — Phase 8 모듈 상수: `AXIS_TILT_THRESHOLDS_DEG=(25.0, 37.5)` / `JITTER_SEVERITY_THRESHOLDS=(8.0, 20.0)` / `JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED=(5000.0, 15000.0)` (Phase 9 는 axis severity 우회, jitter/jerk 임계는 재사용)
- `backend/judging_data/tilt_thresholds.yaml` — `ipsf_tolerance.tolerance_deg=20.0` / `major_fault_deg=40.0` (D-09-A2 axis tilt 임계 source, NotebookLM citation Aerial Pole CoP Page 63 S55 Iron X)
- `app/src/types/analysis.ts:467` — `MotionPhase` 5단계 enum
- `app/src/types/analysis.ts:489-512` — `ContactPoint` enum
- `app/src/types/analysis.ts:541-635` — Phase 8 산출 TS contract (`AxisDeviationMetric` / `StabilityMetric` / `ContactStabilityMetric` / `ForceSignalsReport`)
- `docs/contract.md §9.0/9.3/9.4/9.7/9.8` — Phase 8 contract 명세 (warning enum 20종 박제)

### Phase 8 CONTEXT (의존 패턴 source)

- `.planning/phases/08-jerk-jitter/08-CONTEXT.md` — D-08-A2 Layer 1/Layer 2 패턴 (Phase 9 D-09-C1/C2 분리 source) + D-08-C3 module 분리 패턴 (force_signals.py 진단 vs force_pattern.py 추론, Phase 9 신설 module 근거)
- `.planning/phases/08.1-axis-metric-redesign/08.1-CONTEXT.md` — **D-05 (raw signal only guard) 단일 source** + D-01 (distance 필드 제거) + D-03 (IPSF tolerance 20° floor)
- `.planning/phases/08.1-axis-metric-redesign/08.1-SWEEP-EVIDENCE.md` §11 — sensitivity 5/5 PASS (Phase 9 가 raw tilt 사용 정합)
- `.planning/phases/08-jerk-jitter/08-VERIFICATION.md` — Phase 8 4/4 SC verified

### research (도메인 + 알고리즘 초안 source)

- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §4.1 — `ForceDirectionPattern` 5종 enum 정의 (pull/push/brace/rotate/release/unknown) — Phase 9 SC #1 source
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §4.2 — 영상 신호 8행 표 → 패턴 가능성 매핑 (D-09-A1 룰 source)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §8 — `inferForceDirectionPattern` 알고리즘 초안 (D-09-A1/A5 base_confidence source)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §9.2 — `ForceComparisonFinding` schema (Phase 9 ForcePatternFinding 변형 source)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §10.1 — 좋은 표현 5예문 (D-09-D2 canned 톤 source — 가능성 언어 + 부위별 원인)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §10.2 — 피해야 할 표현 6종 (D-09-D3 grep gate source)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §11 — 코치 개입 포인트 (Phase 9 vs Phase 11 책임 경계 source: 패턴 추출 = AI, 진짜 원인 = 코치)
- `docs/research/00_시스템_아키텍처_FINAL.md` — 두 엔진 분리 (체형 보정 vs 힘 패턴) + AI vs 코치 경계 + confidence 항상 출력
- `docs/research/폴스포츠-지식.md` — 부위별 원인 언어 어휘 (고관절 / 광배 / 코어 / 내전근 / 전완근 / 후굴 / 견갑 / 흉곽 — D-09-D1 jointHint + canned 어휘 source)

### Phase 7 / 12.5 (downstream 카피 패턴 + module 분기 source)

- `.planning/phases/07-difference-classification/07-CONTEXT.md` — D-07-B1 (백엔드 캔드 우선) + D-07-D1 (가능성 언어 / 부위별 원인) + D-07-D2 (금지 표현 grep gate) + D-07-D3 (mode 분기 카피)
- `backend/shared/python/sunity_shared/analysis/copy_templates.py` — Phase 7 canned mapping 패턴 (`force_pattern_copy.py` 박제 source)
- `.planning/phases/12_5-ui-transparency/12.5-CONTEXT.md` — mode 분기 (mode1 / mode3_first / mode3_progress) 패턴 (D-09-D6 source)
- `backend/shared/python/sunity_shared/analysis/assemble.py::build_dimension_explanation` — mode-aware baseline 카피 패턴 (D-09-D2 mapping 박제 source)

### Phase 11 (downstream — Phase 9 출력 소비)

- `.planning/ROADMAP.md` §Phase 11 — CoachCommentHook 데이터 구조 + Gemini 자연어 번역만 (D-09-C3 책임 경계 source)
- Phase 11 SC #3 — "Gemini 프롬프트가 '자연어 번역만, 좌표·판단·점수 출력 금지'" — Phase 9 = Layer 1 단독 영구 차단 근거
- `backend/shared/python/sunity_shared/analysis/coach_writer.py` — Cerebras LLM 어댑터 (Phase 11 wiring point — Phase 9 산출 입력)

### Pipeline + Firestore wiring (Phase 8 패턴 재사용)

- `backend/functions/pipeline/app.py:1117-1140` — Phase 8 wiring (`compute_force_signals` 호출 + `complete_analysis(force_signals_report=...)`) → Phase 9 가 동일 패턴 (`infer_force_direction_pattern` 호출 + `complete_analysis(force_pattern_inference=...)`)
- `backend/shared/python/sunity_shared/firestore_admin.py::complete_analysis` — `_dataclass_to_camel_case_dict` + `_validate_flat_dict_no_nested_array` (Phase 9 신설 필드 자동 저장 + scoped validator 추가)
- `backend/shared/python/sunity_shared/firestore_admin.py::_validate_force_signals_report` — scoped validator 박제 패턴 (Phase 8 Plan 03 Cycle 2 NEW HIGH #3) — Phase 9 `_validate_force_pattern_inference` 신설 source
- `app/src/lib/userAnalyses.ts::normalize` — Firestore raw → AnalysisDoc null-guard (Phase 8 forceSignalsReport null-guard 패턴 — Phase 9 forcePatternInference 동일 적용)

### 박제 메모리 (정합 필수)

- `[[scoring-dimensions-ipsf]]` — IPSF 절대 기준, severity 임계 도메인 룰 (D-09-A2 IPSF tolerance 20° source)
- `[[analysis-objectivity-no-human-scores]]` — 사람 점수 라벨링 영구 X, 객관 임계 박제 (D-09-A2 / D-09-B4 fabrication 금지 source)
- `[[mode3-progress-not-similarity]]` — mode3 = 절대 지표 델타, % 일치 X (D-09-B4 강제 finding 금지 + D-09-D6 mode3 progress 분기 source)
- `[[feedback-analysis-first]]` — 분석 정확도 우선, 가능성 언어 (D-09-A2 / D-09-D2 source)
- `[[feedback-no-echo-confirm]]` — AI = 강사 보조 도구 톤 (D-09-D2 카피 톤 + D-09-C3 Phase 11 책임 경계 source)
- `[[mvp-simple-pilot-quality]]` — 단순 fallback + 점진 정밀화 (D-09-A1 v1 6 signal scope 축소 + D-09-E2 Wave 2 sweep deferred 근거)
- `[[plan-vs-pivot-cross-check]]` — execute-phase 진입 전 scope vs pivot 정합 (D-09-A2 raw signal only guard locked)
- `[[firestore-nested-array-flat]]` — scoped validator 박제 (D-09-U5 정합)
- `[[no-baekje-filler]]` — 카피 작성 시 박제 단어 남용 X
- `[[notebook-lm-pole-sports]]` — IPSF lookup 노트북 (D-09-A2 tolerance 20° citation source)
- `[[codex-reviewer-smplx-bias]]` — Codex plan-review 활용 (D-09-E3 cross-AI checkpoint 권장)
- `[[gsd-pod-work-push-first]]` — Phase 9 = pure-function, RunPod 무관 (D-09-E2 정합)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (Phase 8 / 8.1 산출)

- **`backend/shared/python/sunity_shared/analysis/force_signals.py::ForceSignalsReport`** — Phase 9 의 단일 입력 (umbrella). axisMetrics + stabilityMetrics + contactMetrics + phaseBoundaries 박제. Phase 9 = 본 모듈 import 후 추론.
- **`backend/shared/python/sunity_shared/analysis/force_signals.py::AxisDeviationMetric`** (Phase 8.1 Wave 1) — `shoulder_tilt: float | None` + `hip_tilt: float | None` + `confidence` + `warnings`. D-09-A2 raw 사용. `severity` 영구 차단.
- **`backend/shared/python/sunity_shared/analysis/force_signals.py::StabilityMetric`** — `jitter_score` + `jerk_score` + `jerk_unit='deg_per_sec_cubed'` (FPS-normalized) + `unstable_body_parts` + `holdStabilityScore`. D-09-A1 high_jitter / high_jerk 신호 source.
- **`backend/shared/python/sunity_shared/analysis/force_signals.py::ContactStabilityMetric`** — `estimated_stable` + `lost_near_pole_at_ms` + `near_pole_ratio` + `distance_to_pole_norm` + `measurement_kind`. D-09-A1 late_contact 신호 source.
- **`backend/shared/python/sunity_shared/analysis/force_signals.py::PhaseBoundary`** — 5단계 분할 결과 (start_ms / end_ms / confidence / source). D-09-A4 phase 미인식 fallback 시 본 입력 확인.
- **`backend/judging_data/tilt_thresholds.yaml::ipsf_tolerance.tolerance_deg`** = 20.0 — D-09-A2 axis_tilt 임계 source. Phase 9 force_pattern.py 가 yaml load (calibrate_tilt_thresholds.py 의 loader 재사용 가능).
- **`backend/shared/python/sunity_shared/analysis/force_signals.py:170-180` 모듈 상수** — JITTER_SEVERITY_THRESHOLDS / JERK_SEVERITY_THRESHOLDS — Phase 9 high_jitter / high_jerk detection 임계 재사용 (severity 산출 X, 임계 값 자체만 import).
- **`backend/shared/python/sunity_shared/analysis/copy_templates.py`** (Phase 7) — canned mapping 박제 패턴 (Phase 9 `force_pattern_copy.py` 신설 source).
- **`backend/shared/python/sunity_shared/analysis/assemble.py::build_dimension_explanation`** (Phase 12.5) — mode 분기 카피 박제 패턴 (D-09-D2 mode-aware 매핑 source).
- **`backend/shared/python/sunity_shared/firestore_admin.py::_validate_force_signals_report`** — scoped validator 박제 패턴 (Phase 8 Plan 03 Cycle 2 NEW HIGH #3) — `_validate_force_pattern_inference` 신설 source.

### Established Patterns

- **3-way contract lockstep** — `analysis.ts` ↔ `models.py` (re-export) ↔ `docs/contract.md` 동시 atomic commit (Phase 6/7/8/8.1 패턴). Phase 9 `ForcePatternFinding` + `ForcePatternInference` schema 도 단일 atomic commit (Wave 0).
- **Frozen dataclass + `__post_init__` validator** — `AxisDeviationMetric` / `BodyComparisonFinding` 박제. Phase 9 `ForcePatternFinding` 도 pattern enum 6종 + sourceSignal enum 6종 + confidence [0,1] validator 박제.
- **camelCase 변환** — `_dataclass_to_camel_case_dict` 박제 (Phase 6 C8). Phase 9 의 `source_signal` → `sourceSignal` / `joint_hint` → `jointHint` / `mode_context` → `modeContext` 자동 변환.
- **Pure functions + numpy only** — `dimensions.py` / `force_signals.py` 패턴. Phase 9 `force_pattern.py` 도 순수 함수 (boto3 / 네트워크 / LLM 무관, Layer 2 영구 차단 정합).
- **모듈 분리 (진단 신호 vs 추론)** — Phase 8 D-08-C3 의 `dimensions.py` (점수 출력) ↔ `force_signals.py` (진단 신호) 분리 패턴 정합 → Phase 9 `force_pattern.py` 신설 (진단 신호 위 추론 layer).
- **Firestore scoped validator** — `_validate_force_signals_report` 박제 (Phase 8 Plan 03 Cycle 2 NEW HIGH #3) — Phase 9 `_validate_force_pattern_inference` 신설.
- **Singleton + lazy load (config)** — `_get_tilt_thresholds()` 박제 (Phase 8.1) — Phase 9 의 ipsf_tolerance.tolerance_deg load 시 재사용 (별도 loader 신설 X).

### Integration Points

- **`pipeline/app.py::_process`** (line 1117-1140) — Phase 8 wiring. Phase 9 = `compute_force_signals` 호출 직후 `infer_force_direction_pattern(force_signals_report, motion_id, mode_context)` 추가 + `complete_analysis(force_pattern_inference=force_pattern_dict)` 추가. mode_context 산출 = `_select_mode_context(mode, analysis_id, uid)` helper 신설 (Phase 12.5 패턴 재사용 가능 확인 필요).
- **`firestore_admin.complete_analysis`** — Phase 9 신설 필드 (`forcePatternInference`) 자동 저장. `_dataclass_to_camel_case_dict` + 신설 `_validate_force_pattern_inference` scoped validator. complete_analysis 시그니처 = `complete_analysis(..., force_signals_report=, force_pattern_inference=...)` 확장.
- **`app/src/lib/userAnalyses.ts::normalize`** — Firestore raw → AnalysisDoc normalize. Phase 9 `forcePatternInference` null-guard 확장 (Phase 8 forceSignalsReport null-guard 패턴 정합 — `?? null` fallback + immutable spread).
- **`app/src/types/analysis.ts::AnalysisDoc`** — `forcePatternInference?: ForcePatternInference | null` 필드 추가. 후속 phase (11/12/12.5) consume.

</code_context>

<specifics>
## Specific Ideas

- **belle 박제 (2026-06-10)**: "Phase 8.1 종료 (verifier 5/5 SC PASS, 정은지 25/25 'low'). Phase 9 평행 진입 — raw shoulder_tilt + hip_tilt + stability + contact + jerk 사용. axisMetrics severity 직접 trust 금지 (Codex C-M4 / Phase 8.1 D-05 raw signal only guard). RunPod 불필요 (Wave 0/1 = pure-function)." — D-09-A2 (axis severity guard) + D-09-E1/E2 (2 wave 구조 + Wave 2 production sweep deferred) 직접 정합.
- **Codex C-M4 (Phase 8.1 D-05) raw signal only guard 영구 박제 의미**: Phase 8.1 sensitivity gate (8/8 PASS) 통과해도 Phase 9 plan boundary 안에서 severity 사용 영구 차단. 근거: Phase 8.1 calibration 은 elite false-positive 차단 검증, 실 mode1/mode3 production validity 는 Phase 15 검증. Phase 9 가 calibrated 'low' 를 line quality correctness 로 trust 시 Phase 8 fail pattern 재발 위험.
- **research §4.2 vs §8 박제 정합**: research §4.2 영상 신호 8행 표 = 사용자 친화 도메인 분류, §8 inferForceDirectionPattern 코드 초안 = 4 detection function (`isPelvisDroppingOrMovingOutward` / `isShoulderElevatedAndElbowLocked` / `isLowerBodyContactDelayed` / `hasHighJerkOrJitter`). Phase 9 v1 = §8 의 4 detection + axis_tilt + abnormal_release = 6 signal (`isShoulderElevatedAndElbowLocked` 의 joint angle 패턴 = 절대 angle 통합 v2 deferred). research 의 base_confidence (0.72/0.68/0.70/0.63) 박제 (D-09-A5 source).
- **module 분리 (force_signals.py vs force_pattern.py 신설) 박제 의미**: Phase 8 D-08-C3 의 dimensions.py (점수 0~100) vs force_signals.py (진단 신호 raw) 분리 패턴 정합 — Phase 9 force_pattern.py 신설 (추론 layer). 호출 site 분리, helper import 재사용 (예: `_get_tilt_thresholds` + signal threshold constants). Phase 8 1762줄 force_signals.py 확장 회피.
- **Phase 9 UI hint 없음 정합**: ROADMAP Phase 9 entry 에 `UI hint: yes` 부재. 결과 화면 노출은 Phase 12 / 12.5 책임. Phase 9 = backend canned data 박제만, frontend 변경 = `userAnalyses.ts::normalize` 박제만 (rendering X).
- **모드 분기 (modeContext) source**: Phase 12.5 `assemble.build_dimension_explanation` 의 mode 분기 패턴 (`mode1` / `mode3_first` / `mode3_progress`) 재사용. mode3 first vs progress 판단 룰 = 이전 analysis doc 존재 여부 (Firestore query). Phase 9 pipeline wiring 시 동일 helper 재사용 가능 — planner 확인.
- **Wave 2 sweep 자연 검증 path**: Phase 11 통합 시점 (CoachCommentHook + Gemini 자연어 번역) → 실 영상 mode1/mode3 → Phase 9 finding 노출 정합성 동시 검증. Phase 15 (Mode 1·Mode 3 실영상 + TestFlight) 가 종합 검증.

</specifics>

<deferred>
## Deferred Ideas

### "어깨 elevation" / "elbow lock" 절대 joint angle 패턴 (research §4.2 의 2 signal)
- **Why deferred**: Phase 8 산출 (`ForceSignalsReport`) 에 절대 joint angle 직접 노출 X. features.py 의 angles_tj 매트릭스 통합 + joint angle 임계 박제 필요 → Phase 9 v1 scope 폭발. research §8 의 `isShoulderElevatedAndElbowLocked` 함수 본체 신설 = v2 또는 후속 plan.
- **Target phase**: v2 or 후속 plan (Phase 9 close-out 후 작은 plan).

### Phase-aware canned interpretation mapping (`sourceSignal × phase × modeContext`)
- **Why deferred**: Phase 9 v1 = 18 canned (signal × mode, phase 분기 X). Phase 11 LLM 통합 시 phase-aware 자연 확장. 예: "entry 단계에서 골반 흔들림 = …" vs "hold 단계에서 골반 흔들림 = …" 차별 카피.
- **Target phase**: Phase 11 (CoachCommentHook + Cerebras LLM 풍부화) — phase 별 풍부화는 LLM 동적 생성으로 처리.

### Confidence factor 정밀화 (joint-level + phase-level + technique-level weighted)
- **Why deferred**: Phase 9 v1 = phase_metric_confidence_factor (단순 min). 정밀화 = joint reliability + phase boundary confidence + Phase 5 motion_id confidence + Phase 2 body normalization confidence 가중. v2 박제.
- **Target phase**: v2 or 후속 plan.

### `rotate` pattern detection 정밀화
- **Why deferred**: research §4.1 의 `rotate` (몸통/골반/시선 방향 전환) = Phase 8 산출 신호로 직접 검출 어려움 (회전 angular velocity = 별도 산출 필요). Phase 9 v1 = `rotate` enum 박제만, 자동 검출 X (warning + fallback `unknown`). v2 박제.
- **Target phase**: v2 or 후속 plan.

### EMG / 근육 활성 / 챔피언 근력 측정 통합
- **Why deferred**: research 02 §13 챔피언 EMG = v2 R&D 해자. Phase 9 = 영상 추정만, 단정 영구 금지.
- **Target phase**: v2 R&D milestone.

### v2 카메라 다각도 시점 통합
- **Why deferred**: Phase 4 (다중 시점 촬영 UX) 미완 + Phase 9 single-view 추론 박제. occlusion 완화 = Phase 4 산출 후 confidence 자연 향상.
- **Target phase**: Phase 4 완료 후 v2.

### Cross-phase aggregate summary (`patternSummaryByPhase`)
- **Why deferred**: 5 phase × 5 pattern cross-tabulation = v2 결과 화면 시각화. Phase 9 v1 = findings list (Top-3) 만.
- **Target phase**: v2 or Phase 12 결과 화면 분기.

</deferred>

<follow_ups>
## Follow-ups (Wave-specific signal)

### Wave 0 종료 후 — TS / Python / docs §9.5 lockstep 검증
- **Trigger**: Wave 0 commit + `npm run typecheck` (`tsc --noEmit`) + Python lockstep test PASS
- **Action**: 3-way schema field alignment 회귀 0. Wave 1 진입 OK.

### Wave 1 종료 후 — belle 박제 검수 + cross-AI plan-review
- **Trigger**: Wave 1 commit + 단위 test 회귀 PASS + 금지 표현 grep gate PASS
- **Action**: belle 가 18 canned KO interpretation 검수 + Codex plan-review (cross-AI convergence) 권장. Phase 8.1 패턴 정합 ([[cross-ai-plan-review-good]]).
- **Boundary**: 본 검수 후 Phase 9 verifier 진입.

### Phase 11 통합 시점 — 자연 검증
- **Trigger**: Phase 11 (CoachCommentHook + Gemini 자연어 번역) 실 영상 검증
- **Action**: mode1/mode3 실 영상에서 Phase 9 finding → Phase 11 LLM 풍부화 → 결과 화면 노출 정합성 동시 확인. Phase 9 의 fabrication 0 / overall_confidence 분포 / mode 분기 카피 정합 검증.

### Phase 15 통합 시점 — production sweep
- **Trigger**: Phase 15 (Mode 1·Mode 3 실영상 + 신뢰도 게이트 + TestFlight)
- **Action**: 정은지 + 학생 영상 sweep → Phase 9 finding 분포 검증 (정은지 = 대부분 0~1 finding low confidence + 학생 = 1~3 finding medium confidence). 위양성 검증.

</follow_ups>

## Next Steps

1. `/gsd-plan-phase 9` — Wave 0 / Wave 1 plan breakdown (RunPod 불필요)
2. plan-review (cross-AI Codex 등 권장) — D-09-A2 raw signal guard + D-09-C1 Layer 1 단독 + D-09-D3 금지 표현 grep gate 정합 확인
3. Wave 0 → Wave 1 순차 실행 + 각 wave 종료 시 회귀 PASS gate
4. Wave 1 종료 → Phase 9 verifier → ROADMAP Phase 9 entry "completed" 표시
5. Phase 11 / Phase 15 통합 시점 자연 검증 (Wave 2 production sweep 본 phase scope OUT)
