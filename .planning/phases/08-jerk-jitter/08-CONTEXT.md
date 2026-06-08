# Phase 8: 중심축 이탈 + 접촉점 안정성 + jerk/jitter - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 9 의 `ForceDirectionPattern` 추론 + "실패 원인 후보 3개 카드" 의 **입력 신호**를 산출하는 **측정·신호 layer**. research 02 §7 의 3종 metric 박제:

- `AxisDeviationMetric` — 중심축 이탈 (골반/흉곽 ↔ 폴축 거리 + shoulder/hip tilt + deviationDirection)
- `StabilityMetric` — 흔들림 (jitterScore + jerkScore + holdStabilityScore + unstableBodyParts)
- `ContactStabilityMetric` — 접촉점 안정성 (12 ContactPoint 별 estimatedStable + lostContactAtMs + confidence)

본 phase 가 산출 (output 본체):

- 3종 metric 의 Python dataclass + TS interface + docs/contract.md §X 3-way lockstep 박제
- **5단계 motion-phase 분할** (entry/lock/transition/final_shape/hold) 산출 함수 — 모든 metric 의 `phase` 필드 단위
- **motion-agnostic 휴리스틱 (Layer 1)** + **Gemini key_moments 검증 (Layer 2)** 하이브리드 — Phase 5 motion_id 인식 시 정확도 향상, 미인식 시 Layer 1 baseline 단독 작동
- 신규 모듈 `force_signals.py` (진단 신호 전용) — `dimensions.py` (점수용) 와 호출 site 분리
- 도메인 룰 fixed severity 임계 (body-scale 정규화 + IPSF 각도 tolerance + research 02)
- 가림 프레임 스무딩 + confidence 가중 처리 (`temporal.temporal_fill` + frame-level reliability)
- pipeline/app.py::_process wiring (axis/stability/contact 산출 → AnalysisDoc)

본 phase 가 산출 X (downstream / 다른 phase 영역):

- `ForceDirectionPattern` 추론 (pull/push/brace/rotate/release) — Phase 9
- "실패 원인 후보 3개 카드" — Phase 9
- 부상 위험 신호 (좌우 비대칭/요추 과신전) — Phase 10
- CoachCommentHook 자연어 번역 — Phase 11
- 영상 위 오버레이 좌표 — Phase 12
- 보완 운동 매핑 — Phase 13

</domain>

<decisions>
## Implementation Decisions

### (A) 동작 구간 분할 — 5단계 + 하이브리드 산출

- **D-08-A1:** **5단계 분할** (`entry` / `lock` / `transition` / `final_shape` / `hold`) — research 02 §7 원본 표준. Phase 7 의 'hold' 단일은 Phase 6 입력이 hold-only 측정이라 구조적 결정이었음. Phase 8 은 Phase 9 force-pattern 추론용이라 단일 hold 가 "잡는 순간 골반 흘러내림" vs "버틸 때만 흘러내림" 같은 결정적 케이스를 구분 못함 → 분석 정확도 깨짐. 5단계 정합 필수.
- **D-08-A2:** **하이브리드 산출 (Layer 1 motion-agnostic 휴리스틱 baseline + Layer 2 Gemini key_moments 검증)**
  - **Layer 1 (모든 영상 작동, deterministic baseline)**: motion-agnostic 신호 — 발 keypoint vertical 위치 vs ground line / 폴축까지 손 거리 / keypoint 변화율. 모든 motion_id 무관 박제. 폴스포츠 공통 패턴 (땅→잡기→띄움→자세 형성→유지) 룰 박제.
  - **Layer 2 (Phase 5 motion_id 인식 시만)**: Gemini multimodal 이 5단계 timestamp 보강. Plan 01-13 의 `measurement_unreliable_blocked` 는 IPSF criteria 갭 chain 의 의심이지 key_moment 시각 자체의 의심은 아님 — Phase 8 use case 에 직접 적용 안 될 수도 있음. researcher 가 spike 검증.
  - **Confidence**: Layer 1 만 → `medium`, Layer 1+2 일치 → `high`, 두 layer 불일치 → `low` + warning 박제.
- **D-08-A3:** **새 동작군 추가 시 박제 부담 0** — Layer 1 휴리스틱이 motion-agnostic 이므로 새 동작 추가 시 Phase 8 박제 변경 X. Phase 5 가 motion_id 인식하면 Layer 2 자동 작동, 못 인식해도 Layer 1 항상 작동 → 새 스피닝/신규 동작도 cover. 메모리 `[[mvp-simple-pilot-quality]]` "구조만 열어두기" 정합.
- **D-08-A4:** **3-5 동작군 밖 영상도 분석 죽지 않음** — Phase 5 가 "미지원" 반환 시 Phase 8 = Layer 1 단독 산출 + confidence='medium' + warning. metric 은 계속 출력 (Phase 9 가 confidence 보고 추론 강도 조정). REQUIREMENTS "범위 밖 미지원" 정합.

### (B) ContactStability 추정 방식 — Proximity + 시간 패턴 (하이브리드)

- **D-08-B1:** **Proximity 측정 (Layer A)** — motion_id 별 `expected_contact_points` yaml 박제 + 폴축까지 거리 측정. 거리가 임계 (body-scale 정규화) 이내 + 일정 시간 유지 → `estimatedStable=true`. 거리가 갑자기 멀어진 시각 → `lostContactAtMs`. confidence = keypoint reliability + 거리 안정성 조합.
- **D-08-B2:** **시간 패턴 검증 (Layer B)** — D-08-A1 의 5단계 분할 시각 활용. 일반 룰: `lock` 시각 이후 ~ `release` 직전까지는 모든 expected_contact_points 가 stable 이어야 정상. `lostContactAtMs` 가 `(lock, release)` 구간 안에 들어가면 **비정상 풀림** 자동 검출. motion_id 별 expected_timing yaml 박제 불필요 — 5단계 분할 일반 룰만으로 cover.
- **D-08-B3:** **Gemini 보강 채택 X** — Gemini 가 영상 보고 "접촉 안정/풀림" 답해도 결국 화면상 거리 본 거. proximity 와 같은 정보의 다른 시각이라 cross-validation 가치 약함. + 비용/non-determinism 부담. 시간 패턴 (Layer B) 가 진짜 independent 신호 (공간 + 시간 결합) — 이게 belle 정신 "분석 정확도 우선" 정합.
- **D-08-B4:** **motion_id 미인식 시 fallback** — `expected_contact_points = []` 박제 + 모든 손/발 keypoint 의 폴축 거리만 산출. ContactStabilityMetric 은 출력하되 `estimatedStable=null` + confidence='low' 표기. 분석 죽지 않음.
- **D-08-B5:** **새 동작 추가 시 박제 = yaml 1줄** — motion_id 별 expected_contact_points 매핑은 각 동작의 본질적 속성 (인버트 = 양손+양 안쪽허벅지, 후굴 = 양손+발목+골반)이라 박제 불가피하지만 1 동작당 1줄 yaml. Phase 5 motion_id 등록과 같이 박제.

### (C) Stability/jerk 산식 — 기존 helpers 재사용 + jerk 신설 + 새 모듈

- **D-08-C1:** **재사용**: `dimensions.stability_score` (inter-frame median wobble) → `jitterScore` + `holdStabilityScore`. `dimensions.stability_wobble_by_joint` → `unstableBodyParts` 산출. 코드 중복 X, Phase 12.5 dimension 점수와 일관된 windowing (`_select_window`).
- **D-08-C2:** **신설**: `jerkScore` = 3차 미분 (가속도 변화율). 노이즈 민감 → 같은 windowing + 같은 스무딩 패턴 (`temporal.temporal_fill` 통과 후) 박제. researcher 가 산식 박제 (e.g., `np.abs(np.diff(angles, n=3, axis=0))` median).
- **D-08-C3:** **새 모듈 `force_signals.py` 박제** — `dimensions.py` 는 **점수 출력 (0~100)** 용, `force_signals.py` 는 **진단 신호 raw 수치 (jitter=0.08 등)** 용. 호출 site 분리, helper 함수는 `dimensions.py` 에서 import 재사용. 점수 vs 진단 성격 분리로 향후 유지보수 용이.
- **D-08-C4:** **AxisDeviation + ContactStability 도 같은 모듈** — `force_signals.py` 안에 3종 metric 산출 함수 박제. Phase 9 가 본 모듈만 import 하면 force-pattern 추론 입력 확보.

### (D) 거리/임계값 기준 — 도메인 룰 fixed 임계

- **D-08-D1:** **거리 단위 = body-scale 정규화** — `BodyNormalizationProfile` (Phase 2 산출) 의 `estimatedHeightScale` / `torsoScale` / `legScale` 재사용. 예: pelvis-pole 거리 = `torsoScale` 의 비율 (30% 등). 키 차이 무관 일관성. Phase 6 패턴 정합.
- **D-08-D2:** **severity 임계 출처 = 도메인 룰 fixed** (정은지 5영상 분포 박제 X):
  - **거리/jerk**: research 02 + 폴스포츠-지식.md + motion analysis 분야 표준값 (researcher 박제). 예: pelvis-pole 거리가 body-scale 의 30% 이상 = high. 임계 fixed → 영상/선수 추가 무관.
  - **tilt 각도**: IPSF Code of Points tolerance 차용 (각도 영역). researcher 가 IPSF Pole Sports CoP 2024-2025 + NotebookLM lookup 으로 박제.
- **D-08-D3:** **reference 영상 sweep = sanity check 만** — 정은지 reference 영상이 늘어도 임계 변동 X. sweep 으로 low/medium/high 분포가 합리적인지 (정은지가 90%+ low, 일반 학생이 medium/high 위주) 검증. 임계 자체는 도메인 룰로 박제.
- **D-08-D4:** **확장성 영구** — 정은지 영상 추가/교체, 다른 선수 등록, 새 동작군 추가 모두 임계 변동 X. 과거 분석과 비교 일관성 확보. 메모리 `[[scoring-dimensions-ipsf]]` "IPSF 절대 기준" + `[[analysis-objectivity-no-human-scores]]` "사람 점수 라벨링 X" 정합.

### Universal Principle (Phase 8 전반)

- **D-08-U1:** **가림 스무딩 + confidence 가중** — `temporal.temporal_fill` 을 모든 metric 산출 전 적용 (occlusion 보간). frame-level `reliability='low'` 프레임은 metric 산출 가중치 낮춤 + warning. success criteria #4 정합. Phase 4 (multi-view UX + occlusion gate) 미완료지만 Phase 1 의 per-frame reliability + temporal_fill 만으로 v1 박제 가능.
- **D-08-U2:** **모든 metric 에 confidence 필드** — research 02 의 "모든 finding 에 confidence + interpretation" 박제. severity (low/medium/high) 와 confidence (수치 0~1) 는 다른 차원: severity = 측정값 자체 크기, confidence = 측정값 신뢰도.
- **D-08-U3:** **3-way contract lockstep** — `app/src/types/analysis.ts` ↔ `backend/shared/python/sunity_shared/analysis/force_signals.py` (또는 models.py re-export) ↔ `docs/contract.md` §X 동시 atomic commit 박제. Phase 6/7 박제 패턴 정합.

### Plan-Checker Round-1 Promoted Decisions (2026-06-08)

> RESEARCH.md `## Open Questions` Q1/Q2/Q5 의 Recommendation 을 Dimension 11 정합으로 D-08-E* locked decisions 로 승급. plan-checker pass 후 plans 가 본 결정 박제.

- **D-08-E1:** **`_validate_dict_only_scalars` 명세 확장 = Option A (list[scalar] 허용)** — list[str], list[int], list[float], list[bool], list[None] 허용 + list[list] / list[dict] 거부 유지. Firestore nested-array 회피 핵심은 list[list] / list[dict] 차단이며 list[scalar] 는 SDK 직렬화 안전. Phase 6 BodyComparisonReport.warnings list[str] 와 일관성. Plan 08-03 Task 1 박제.

- **D-08-E2:** **`keep_local_video` = helper 함수 `_should_keep_local_video()` 박제** — `_extract_video_analysis_inputs.keep_local_video` default=False 유지 (Phase 6 path 회귀 0). Phase 8 wiring 시 module-level helper `_should_keep_local_video() -> bool` 신설 (`pipeline/app.py`) — 본체 = `os.environ.get("RECOGNIZER_BACKEND") == "gemini"`. `_get_gemini_moment_extractor()` 와 **동일 env probe 단일 박제** → drift 차단 (향후 backend 변경/추가 시 한 곳만 수정). mode1/mode3 양쪽 call site = `keep_local_video=_should_keep_local_video()` 명시 전달.

- **D-08-E3:** **Layer 2 wiring 박제 + pre-flight spike 별 plan 신설 X** — Plan 03 가 Layer 2 wiring 단일 plan 박제. 안전성 근거 3종:
  1. **graceful fallback 코드 박제** — `try/except (RuntimeError, ValueError, ConnectionError)` → Layer 1 단독 + `warnings: ["layer2_call_failed"]` + confidence='medium'. RECOGNIZER_BACKEND env unset 시 Layer 1 default path 단독 active (분석 죽지 않음, D-08-A4 정합).
  2. **env flag 명시 활성화 필요** — `RECOGNIZER_BACKEND=gemini` env 명시 설정 안 하면 Layer 2 wiring 호출 X. Plan 08-03 Task 1 acceptance 박제: "default state (env unset) = Layer 1 단독 path active = analysis pipeline 안전". 운영 default 안전 박제 후 RunPod Pod 에서 belle 가 명시 활성화.
  3. **Plan 08-03 Task 3 checkpoint = pre-flight spike 역할 대신** — manual checkpoint 가 (a) ref-invert 1영상 Layer 2 timestamp ±300ms sensible 검증, (b) 5영상 sweep severity 분포 sanity, (c) Layer 1 25-timestamp belle 라벨링 ≥ 80% 일치. **모든 sanity check 실패 시 unwind path = RECOGNIZER_BACKEND env unset** (코드 변경 0, 1 env 변경으로 Layer 1 단독 path active). 별 spike plan 박제 시 동일 검증 1회 추가 = redundancy.

- **D-08-E4:** **D-08-A2 sub-refinement (motion_id=None 시 Layer 1 confidence)** — D-08-A2 의 "Layer 1 만 → medium" 정신은 motion_id 인식 케이스 가정. motion_id=None 케이스에서는 Layer 1 단독 confidence 가 더 약함 (yaml expected_contact_points lookup 불가능 + Phase 5 인식 실패 의미). Plan 02 박제: motion_id 인식 시 Layer 1 단독 = `confidence='medium'`, motion_id=None 시 Layer 1 단독 = `confidence='low'` + `source='heuristic_fallback'` + warning `"motion_id_unrecognized_fallback"`. CONTEXT.md `<Claude's Discretion>` 항목 lift.

### Claude's Discretion

- **`force_signals.py` 모듈의 정확한 함수 시그니처** — `compute_axis_deviation(frames, phase_boundaries, body_profile, pole_axis) → list[AxisDeviationMetric]` 같은 시그니처. researcher / planner 영역.
- **5단계 분할 휴리스틱의 정확한 룰** — 발 vertical threshold, 폴 거리 threshold, keypoint 변화율 cutoff. researcher 가 폴스포츠 영상 분석 + research 02 §6 박제 + 5영상 sweep 으로 검증.
- **jerk 산식의 정확한 정의** — 3차 미분 vs 가속도 RMS 등. researcher 가 motion analysis 표준 박제 후 결정.
- **expected_contact_points yaml 의 정확한 motion_id 별 박제 내용** — 인버트/후굴/숄더마운트/기본 포징 등 3-5 동작군 박제. Phase 5 motion_id 와 정합. researcher / belle 검증.
- **Layer 2 Gemini 호출 비용 + latency 박제** — Phase 5 Gemini 호출 + Phase 8 Gemini 호출 = 2회 비용. cache 활용 + retry 정책 박제. planner 영역.
- **5단계 분할이 hold-only 측정과 다른 windowing** — Phase 12.5 의 `_select_window` 는 hold 구간만 산출. Phase 8 의 5단계 분할은 다중 window 박제 필요. researcher 가 windowing 박제 (각 phase 별 frame range).
- **AnalysisDoc Firestore 저장 키** — `forceSignals: { axisMetrics[], stabilityMetrics[], contactMetrics[], phaseBoundaries }` 형태 박제. Firestore nested-array 금지 정합 (각 metric list 안 dict-of-scalars-only). planner 영역.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 8 본 phase 산출 / contract

- `.planning/ROADMAP.md` §Phase 8 — goal + 4 success criteria + deps (Phase 1, Phase 4)
- `.planning/REQUIREMENTS.md` FORCE-01 — 힘 패턴 추론 (Phase 8 신호 + Phase 9 패턴)
- `app/src/types/analysis.ts` — TS contract 확장 (AxisDeviationMetric / StabilityMetric / ContactStabilityMetric / PhaseBoundary 추가 필요)
- `backend/shared/python/sunity_shared/models.py` — Python re-export contract
- `docs/contract.md` — schema 명세 (Phase 8 §X 추가 필요)

### research + 도메인 (입력 source)

- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §6 — 분석 흐름 (entry/lock/transition/final_shape/hold)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §7 — 3종 metric schema 원본 (AxisDeviation §7.1 / StabilityMetric §7.2 / ContactStabilityMetric §7.3)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §5.3 — 12 ContactPoint enum (left/right hand/inner_thigh/knee/foot/ankle/hip/unknown)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §8 — `inferForceDirectionPattern` 초안 (Phase 9 가 consume, Phase 8 입력 요구사항 확인 source)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §3.2 — 가림 스무딩 + confidence 게이트 박제 (success criteria #4 source)
- `docs/research/폴스포츠-지술.md` (있다면) / `docs/research/폴스포츠-지식.md` — 도메인 부위 어휘 + 중심축 정의 + 접촉점 도메인 박제
- `docs/research/00_시스템_아키텍처_FINAL.md` — 두 엔진 분리 (체형 보정 vs 힘 패턴) + PoseEngine 추상화 정합

### Phase 1 박제 (upstream — 폴 축 + reliability)

- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md` — PoseEngine + PoleAxis 박제
- `backend/shared/python/sunity_shared/analysis/pose_frame.py` — PoseFrame + PoleAxis + landmarks_pole_aligned + reliability (Phase 8 입력 본체)
- `backend/shared/python/sunity_shared/analysis/pose/` (PoleDetector 박제) — pole_axis 산출
- `backend/shared/python/sunity_shared/analysis/temporal.py` — `temporal_fill` + occluded_mask (가림 스무딩 본체, D-08-U1 박제 source)

### Phase 2 박제 (upstream — body normalization)

- `.planning/phases/02-body-normalization/02-CONTEXT.md` (있다면)
- `backend/shared/python/sunity_shared/analysis/body_normalization.py` — BodyNormalizationProfile 박제 (D-08-D1 거리 정규화 source)
- `backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py` — measure_body_profile 박제

### Phase 5 박제 (upstream — motion_id + Gemini)

- `.planning/phases/05-gemini/05-CONTEXT.md` — Gemini motion_id 인식 + EXTEND/BENT 박제
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` — TechniqueProfile (motion_id + expects_extension)
- `backend/shared/python/sunity_shared/analysis/technique.py` — TechniqueProfile dataclass (Phase 8 motion_id 매핑 입력)

### Plan 01-13 박제 (Gemini key_moments 선례)

- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-13-PLAN.md` — Gemini key moment timestamp + criteria extractor spike 본체
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-13-SUMMARY.md` — `measurement_unreliable_blocked` verdict + 5/5 minimum fail 박제. **중요**: Plan 13 의 blocker = IPSF criteria 갭 chain 의 의심이지 key_moment 시각 자체의 의심은 아님. Phase 8 use case (key_moment timestamp 만, IPSF 비교 X) 에는 직접 적용 안 될 수도 있음. Layer 2 spike 박제 source.
- `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` (있다면) — KeyMoment + GeminiMomentExtractor 박제 (Plan 13 산출)
- `backend/shared/python/sunity_shared/judging/moment_dimensions.py` (있다면) — measure_moment_angles + 8 joint 한정 박제

### Phase 12.5 박제 (downstream 패턴 참조)

- `.planning/phases/12_5-ui-transparency/12.5-CONTEXT.md` — dimensionExplanation 박제 패턴 (Phase 8 의 metric → 결과 화면 매핑 source)
- `backend/shared/python/sunity_shared/analysis/dimensions.py::stability_score` (line 60+) — 재사용 source (D-08-C1)
- `backend/shared/python/sunity_shared/analysis/dimensions.py::stability_wobble_by_joint` (line 170+) — 재사용 source (D-08-C1)
- `backend/shared/python/sunity_shared/analysis/dimensions.py::_select_window` — windowing 박제 source

### Pipeline + Firestore wiring

- `backend/functions/pipeline/app.py::_process` — Phase 6 박제 wiring. Phase 8 metric 산출 호출 site 박제 (compare_body_profiles 직후 / 병행 / 직전 — planner 결정)
- `backend/shared/python/sunity_shared/firestore_admin.py::complete_analysis` — Phase 6 박제. Phase 8 의 forceSignals 필드 자동 저장 박제 정합 (`_dataclass_to_camel_case_dict` + `_validate_flat_dict_no_nested_array`)
- `app/src/lib/userAnalyses.ts::normalize` — Firestore raw → AnalysisDoc 정규화. Phase 8 forceSignals normalize 확장

### IPSF + scoring 박제

- `.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md` — IPSF 5트랙 v1 박제 (Phase 8 tilt 각도 tolerance source)
- IPSF Code of Points 2024-2025 (NotebookLM lookup) — tilt 각도 tolerance source (researcher 가 NotebookLM query)

### Downstream (Phase 8 출력 소비)

- ROADMAP §Phase 9 — `inferForceDirectionPattern` + 실패 원인 후보 3개 카드 (Phase 8 의 axis/contact/stability metric → force pattern)
- ROADMAP §Phase 10 — 부상 위험 플래그 (Phase 8 의 unstableBodyParts + axis tilt 활용)
- ROADMAP §Phase 11 — CoachCommentHook + Gemini 자연어 번역 (Phase 8 metric → 코칭 카피)
- ROADMAP §Phase 12 — 영상 위 오버레이 (Phase 8 의 axis distance / contact point 시각화)

### 박제 메모리 (정합 필수)

- `[[mvp-simple-pilot-quality]]` — 구조만 열어두기. motion-agnostic 휴리스틱 + Gemini 옵션 layer 박제 근거.
- `[[scoring-dimensions-ipsf]]` — IPSF 절대 기준. severity 임계 도메인 룰 박제 정합.
- `[[analysis-objectivity-no-human-scores]]` — 사람 점수 라벨링 X. 정은지 분포 baseline 거부 근거.
- `[[feedback-analysis-first]]` — 분석 정확도 우선. 5단계 분할 채택 근거 (단일 hold 정확도 부족).
- `[[mode3-progress-not-similarity]]` — mode3 = 절대 지표 델타. DTW base/extension 거부 근거 (reference 없는 케이스 blocking).
- `[[single-camera-first-multi-view-last]]` — Phase 4 미완료여도 Phase 8 v1 박제 가능 (per-frame reliability + temporal_fill 만으로).
- `[[no-baekje-filler]]` — 본 CONTEXT 박제 표현 남용 X. (자동 작성 시 주의)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`backend/shared/python/sunity_shared/analysis/pose_frame.py::PoseFrame`** — `pole_axis: PoleAxis | None` 필드 (video-level) + `landmarks_pole_aligned` 박제. Phase 8 의 모든 거리 측정은 pole-aligned 좌표 입력. `reliability: ReliabilityLevel` (low/medium/high) 박제 — D-08-U1 confidence 가중 source.
- **`backend/shared/python/sunity_shared/analysis/pose_frame.py::PoleAxis`** — axis_vector + base_point + confidence_level + source (detected / vertical_fallback). Phase 8 의 axis 거리/tilt 산출 기준.
- **`backend/shared/python/sunity_shared/analysis/temporal.py::temporal_fill`** — NLF/RTMW 불확실도 기반 occlusion 보간 + smoothing. D-08-U1 박제. Phase 8 metric 산출 직전 호출.
- **`backend/shared/python/sunity_shared/analysis/dimensions.py::stability_score`** (line 60+) — inter-frame median wobble (1차 미분). `jitterScore` + `holdStabilityScore` 재사용 source.
- **`backend/shared/python/sunity_shared/analysis/dimensions.py::stability_wobble_by_joint`** (line 170+) — 관절별 wobble. `unstableBodyParts` 산출 source (임계 박제 후 list filter).
- **`backend/shared/python/sunity_shared/analysis/dimensions.py::_select_window`** — hold 구간 자동 검출 박제. Phase 8 `hold` phase 의 windowing 재사용 + 5단계 분할의 마지막 단계 = hold 의 source 정합.
- **`backend/shared/python/sunity_shared/analysis/body_normalization.py::BodyNormalizationProfile`** — Phase 2 산출. D-08-D1 거리 정규화 입력.
- **`backend/shared/python/sunity_shared/analysis/skeleton.py::JOINT_KEYS`** + `NUM_JOINTS` — 8 angle joints 박제. Phase 8 의 keypoint 차원 정합.
- **`backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py`** + **`technique.py::TechniqueProfile`** — motion_id 인식 + EXTEND/BENT. Phase 8 Layer 2 Gemini 호출 + motion_id 별 expected_contact_points lookup source.
- **`backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py`** (Plan 01-13 산출, 있을 경우) — Gemini key_moment 추출 박제. Phase 8 Layer 2 재시도 source. researcher 가 모듈 존재 확인 후 박제.

### Established Patterns

- **3-way contract lockstep** — `analysis.ts` ↔ `models.py` (re-export) ↔ `docs/contract.md` 동시 atomic commit (Phase 6/7 패턴). Phase 8 의 3종 metric schema 도 단일 commit 박제.
- **Frozen dataclass + `__post_init__` validator** — `BodyComparisonFinding` / `BodyComparisonReport` 박제 패턴. Phase 8 의 AxisDeviationMetric / StabilityMetric / ContactStabilityMetric 도 동일 박제 (severity enum 검증, confidence 범위 검증 등).
- **camelCase 변환** — `_dataclass_to_camel_case_dict` 박제 (Phase 6 C8). Phase 8 의 `axis_metrics` → `axisMetrics` / `lost_contact_at_ms` → `lostContactAtMs` 자동 변환.
- **Pure functions + numpy only** — `dimensions.py` / `body_normalizer.py` 박제 패턴. Phase 8 의 `force_signals.py` 도 순수 함수 (boto3 / 네트워크 / LLM 무관). Layer 2 Gemini 호출은 어댑터 boundary 분리.
- **Singleton adapters / lazy import** — Gemini 호출 어댑터는 Phase 5 박제 패턴 정합 (singleton + lazy import).
- **Firestore nested-array 금지** — `axisMetrics: list[dict-of-scalars-only]` 박제 (`_validate_dict_only_scalars` 정합). 깊은 중첩 X.
- **모듈 분리 (점수 vs 진단)** — `dimensions.py` (점수 출력) / `force_signals.py` 신설 (진단 신호) 박제. helper 함수는 import 재사용.

### Integration Points

- **`pipeline/app.py::_process`** — Phase 6 박제. Phase 8 wiring 위치 = `compare_body_profiles` 호출 직후 (또는 직전 — planner 결정). 입력: PoseFrame list + pole_axis + body_normalization_profile + motion_id (Phase 5 산출). 출력: AxisDeviationMetric[] + StabilityMetric[] + ContactStabilityMetric[] + phase_boundaries (5단계 분할 결과).
- **`firestore_admin.complete_analysis`** — Phase 8 신설 필드 (forceSignals) 자동 저장 박제. `_dataclass_to_camel_case_dict` + `_validate_flat_dict_no_nested_array` 정합.
- **`app/src/lib/userAnalyses.ts::normalize`** — Firestore raw → AnalysisDoc 정규화. Phase 8 forceSignals normalize 확장 (B1 null-guard 패턴 정합).
- **`app/src/types/analysis.ts::AnalysisDoc`** — `forceSignals: ForceSignalsReport` 필드 추가. 후속 phase (9/10/11/12) 가 본 필드 consume.

</code_context>

<specifics>
## Specific Ideas

- **belle 우려 박제 (2026-06-08)**: "정은지 영상은 더 늘어날 수도 있고, 다른 선수들도 올릴 수 있는데" — 임계 박제 시 확장성 우려. D-08-D2/D3/D4 가 직접 응답: 도메인 룰 fixed 임계 + reference sweep sanity check. 영상/선수/동작 추가 무관 일관성 영구 박제.
- **belle 우려 박제 (2026-06-08)**: "새 동작이든 뭐든 안 되는 게 있으면 안 됨" — D-08-A3/A4 + D-08-B4 가 직접 응답: motion-agnostic Layer 1 휴리스틱 + motion_id 미인식 fallback + 분석이 죽지 않는 graceful degrade.
- **belle 직관 박제 (2026-06-08)**: Phase 7 의 'hold' 단일이 Phase 8 에 그대로 적용되면 분석 정확도 깨짐 — 케이스 X(잡는 순간) vs Y(버틸 때만) 구분 불가. D-08-A1 채택 근거.
- **Plan 01-13 blocker 정확한 의미 박제**: `measurement_unreliable_blocked` = IPSF criteria 갭 chain 의심이지 key_moment 시각 자체 의심은 아님. Phase 8 use case (key_moment timestamp 만 사용, IPSF 비교 X) 에는 직접 적용 안 될 수도 있음 → Layer 2 spike 박제 가치.
- **5단계 분할 정확도 vs 비용 균형**: Layer 1 단독 80~90% 정확도 + Layer 2 보강 시 95%+ 추정. Layer 2 비용 = Phase 5 Gemini 호출 외 추가 1회. researcher / planner 가 cache + cost optimization 박제.
- **5단계 vs 2단계 schema 호환성**: `phase: Literal['entry', 'lock', 'transition', 'final_shape', 'hold']` 박제 시 v1.5/v2 호환. 2단계 (`setup_transition` / `hold`) 로 fallback 필요 시 enum 확장 + frontend 분기 박제.

</specifics>

<deferred>
## Deferred Ideas

- **v1.5+ Plan 01-13 Gemini key_moments 본격화** — Phase 8 Layer 2 spike 가 검증되면 Phase 8 close 후 별도 plan 으로 정확도 향상 박제. measurement_unreliable_blocked verdict 의 IPSF criteria 갭 chain 별도 해결 필요.
- **motion-id 별 미세 튜닝 (v2)** — Layer 1 baseline 정확도가 부족하면 (sweep 검증 후 80% 미달) motion-id 별 phase 분할 휴리스틱 룰 박제. v1 은 motion-agnostic 단일 박제로 충분.
- **EMG 기반 근육 힘 방향 단정 (v2)** — research 02 §0 박제. 챔피언 EMG 측정 + 근육 활성 timing. Phase 8 은 추정만, 단정 영구 금지.
- **카메라 앵글 합성 / 다각도 시점 (v2)** — Phase 4 v2 확장. Phase 8 single-view 박제 + 시점 추가 시 confidence 향상.
- **forceSignalsByPhase aggregate (v2)** — 5단계 × 3 metric cross-tabulation summary 출력 (Phase 9 force pattern 입력 + Phase 12 결과 화면 박제).
- **per-motion expected_timing yaml** — motion_id 별 expected lock_to_release 박제. v1 은 5단계 분할 일반 룰 (`lock`이후 `release`직전) 만 박제, v2 에서 motion 별 미세 차이 박제 가능.
- **release phase 박제 (v1.5)** — 5단계 박제 (entry/lock/transition/final_shape/hold) 외에 `release` phase 자연 확장. ContactStability 의 lostContactAtMs 검출 정확도 향상.
- **임계 sweep dashboard** — reference 영상이 늘어날 때 임계 sanity check 자동화 (admin script). belle 운영 작업.

</deferred>

---

*Phase: 8-jerk-jitter*
*Context gathered: 2026-06-08*
