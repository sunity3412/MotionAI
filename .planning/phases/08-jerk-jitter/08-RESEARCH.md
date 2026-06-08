# Phase 8: 중심축 이탈 + 접촉점 안정성 + jerk/jitter — Research

**Researched:** 2026-06-08
**Domain:** Backend signal extraction layer (pure-Python numpy + optional Gemini Layer 2 adapter) — 3 diagnostic metrics + 5-phase motion split + temporal smoothing
**Confidence:** HIGH (도메인 100% 내부 코드 + research §6/§7 source 정합 + Phase 6/7 박제 lockstep 패턴 그대로 적용 가능)

## Summary

Phase 8 은 Phase 9 의 `inferForceDirectionPattern` (pull/push/brace/rotate/release 추론 + 실패 원인 후보 3개 카드) 의 **입력 신호 layer** 다. research 02 §7 의 3종 dataclass (`AxisDeviationMetric` / `StabilityMetric` / `ContactStabilityMetric`) + 5단계 motion-phase 분할 (`entry` / `lock` / `transition` / `final_shape` / `hold`) 을 phase 별로 산출하고, 모든 신호에 `temporal.temporal_fill` 가림 스무딩을 적용하며, frame-level reliability + 측정 confidence 두 축을 분리 보존한다.

본 phase 는 **점수 출력이 아니라 진단 신호 raw 수치** 를 생성한다 — `dimensions.py` 의 `stability_score` (0~100 점수) 와는 호출 site 분리. 새 모듈 `backend/shared/python/sunity_shared/analysis/force_signals.py` 가 4개 public 함수를 제공: `compute_phase_boundaries` / `compute_axis_deviation` / `compute_stability_metrics` / `compute_contact_stability` + 통합 헬퍼 `compute_force_signals`. `dimensions._select_window` / `stability_wobble_by_joint` / `BodyNormalizationProfile.torso_scale` 은 helper import 로 재사용 (코드 중복 X, drift 방지 — Phase 12.5 v4 Codex HIGH-2 패턴).

5단계 split = **Layer 1 motion-agnostic 휴리스틱** (deterministic baseline — 모든 영상 작동) + **Layer 2 Gemini key_moments 검증** (Phase 5 motion_id 인식 시만). Layer 2 의 핵심 reuse 자산은 `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py::GeminiMomentExtractor.extract_key_moments()` — 이미 setup/hold/peak/release 4 key_moment timestamp 만 반환 (좌표/점수/판단 정규식 가드 3중) + Parameter Store API 키 + lazy import + 캐싱이 Plan 01-13 박제 완료. Phase 8 의 Layer 2 use case 는 **timestamp 추출만** 사용 — Plan 01-13 의 `measurement_unreliable_blocked` verdict (IPSF criteria 비교 chain 신뢰도 의심) 와 직접 무관하므로 v1 wiring 가능.

ContactStabilityMetric 의 expected_contact_points = motion_id 별 yaml 매핑 (`backend/judging_data/contact_points.yaml` 신설) + 폴축까지 거리 임계 (body-scale 정규화, torso_scale 8% 가설). proximity 측정 (Layer A) + 5단계 분할 시각 기반 abnormal release 검출 (Layer B) 의 하이브리드. motion_id 미인식 시 `expected_contact_points=[]` + estimatedStable=null + confidence='low' fallback.

severity 임계 = **도메인 룰 fixed** (정은지 분포 baseline 거부, [[scoring-dimensions-ipsf]] + [[analysis-objectivity-no-human-scores]] 박제 일관). 거리/jerk 는 motion-analysis 표준 + research 02 §7.1, tilt 각도는 IPSF Code of Points tolerance (NotebookLM lookup). reference 영상 sweep 은 sanity check 만 — 임계 자체 변동 X.

**Primary recommendation:** 새 모듈 `force_signals.py` 1개 + `contact_points.yaml` 1개 + `gemini_moment_extractor.py` adapter import (코드 변경 0, 기존 모듈 재사용) + `pipeline/app.py::_process` 에서 `compare_body_profiles` 호출 직후 1줄 wiring + `firestore_admin.complete_analysis()` 에 `force_signals_report` kwarg 추가. 3-way contract lockstep = TS `analysis.ts` 신규 7 타입 + Python `models.py` re-export + `docs/contract.md §9` 신설 단일 atomic commit.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**(A) 동작 구간 분할 — 5단계 + 하이브리드**

- **D-08-A1**: **5단계 분할** (`entry` / `lock` / `transition` / `final_shape` / `hold`) — research 02 §7 원본 표준. Phase 7 의 'hold' 단일은 구조적 결정이지 일반화 불가; Phase 9 force-pattern 추론용 5단계 정합 필수.
- **D-08-A2**: **하이브리드 산출 (Layer 1 motion-agnostic 휴리스틱 + Layer 2 Gemini key_moments 검증)**.
  - Layer 1 (모든 영상 작동, deterministic): 발 keypoint vertical / 폴축 거리 / keypoint 변화율 — motion_id 무관.
  - Layer 2 (Phase 5 motion_id 인식 시만): Gemini multimodal 이 5단계 timestamp 보강. Plan 01-13 의 measurement_unreliable_blocked 는 IPSF criteria 의심이지 key_moment 시각 자체의 의심은 아님 — Phase 8 use case 에 직접 적용 안 됨.
  - Confidence: Layer 1 만 → `medium`, Layer 1+2 일치 → `high`, 두 layer 불일치 → `low` + warning.
- **D-08-A3**: 새 동작군 추가 시 박제 부담 0 — Layer 1 motion-agnostic.
- **D-08-A4**: 3-5 동작군 밖 영상도 분석 죽지 않음 — Layer 1 단독 + confidence='medium' + warning.

**(B) ContactStability — Proximity + 시간 패턴**

- **D-08-B1**: Proximity 측정 — motion_id 별 `expected_contact_points` yaml + 폴축까지 거리 임계 (body-scale 정규화).
- **D-08-B2**: 시간 패턴 검증 — D-08-A1 의 5단계 분할 시각 활용. lostContactAtMs ∈ (lock_start_ms, release_estimated_ms) = 비정상 풀림 검출. motion_id 별 expected_timing yaml 박제 불필요.
- **D-08-B3**: Gemini 보강 채택 X — proximity 와 같은 정보의 다른 시각.
- **D-08-B4**: motion_id 미인식 시 fallback — `expected_contact_points=[]` + 모든 손/발 keypoint 의 폴축 거리만 산출. estimatedStable=null + confidence='low'.
- **D-08-B5**: 새 동작 추가 시 yaml 1줄 박제 (1 motion 당 1줄).

**(C) Stability/jerk — 기존 helpers 재사용 + jerk 신설 + 새 모듈**

- **D-08-C1**: 재사용 — `dimensions.stability_score` → `jitterScore` + `holdStabilityScore`. `dimensions.stability_wobble_by_joint` → `unstableBodyParts`.
- **D-08-C2**: 신설 — `jerkScore` = 3차 미분 (researcher 가 산식 박제).
- **D-08-C3**: 새 모듈 `force_signals.py` 박제 (dimensions.py 는 점수, force_signals.py 는 진단 신호 — 호출 site 분리).
- **D-08-C4**: AxisDeviation + ContactStability 도 같은 `force_signals.py` 모듈.

**(D) 거리/임계값 — 도메인 룰 fixed**

- **D-08-D1**: 거리 단위 = body-scale 정규화 (`BodyNormalizationProfile.torso_scale` 등).
- **D-08-D2**: severity 임계 출처:
  - 거리/jerk: research 02 + 폴스포츠-지식.md + motion analysis 표준값.
  - tilt 각도: IPSF Code of Points tolerance.
- **D-08-D3**: reference 영상 sweep = sanity check 만 (임계 변동 X).
- **D-08-D4**: 확장성 영구 (영상/선수/동작 추가 무관 임계 일관).

**(U) Universal Principle**

- **D-08-U1**: 가림 스무딩 + confidence 가중 — `temporal.temporal_fill` 적용 + frame-level reliability='low' 가중치 낮춤 + warning.
- **D-08-U2**: 모든 metric 에 confidence 필드 (severity ≠ confidence: severity=측정값 크기, confidence=측정 신뢰도).
- **D-08-U3**: 3-way contract lockstep (`analysis.ts` ↔ `models.py` ↔ `docs/contract.md` 동시 atomic commit, Phase 6/7 패턴).

### Claude's Discretion

- `force_signals.py` 모듈의 정확한 함수 시그너처 — 본 RESEARCH §Module Structure 가 박제.
- 5단계 분할 휴리스틱의 정확한 룰 — 본 RESEARCH §Layer 1 Heuristic 가 박제 + sweep 검증 권장.
- jerk 산식의 정확한 정의 — 본 RESEARCH §StabilityMetric Algorithm 가 박제.
- `expected_contact_points` yaml 의 정확한 motion_id 별 박제 내용 — 본 RESEARCH §Contact Points YAML 이 초안 박제, belle 검수.
- Layer 2 Gemini 호출 비용 + latency 박제 — planner 영역 (cache 정합 — `GeminiMomentExtractor._cache` 활용).
- 5단계 분할이 hold-only 측정과 다른 windowing — 본 RESEARCH §Phase Window 가 박제.
- AnalysisDoc Firestore 저장 키 — 본 RESEARCH §Firestore Schema 가 박제.

### Deferred Ideas (OUT OF SCOPE)

- v1.5+ Plan 01-13 Gemini key_moments 본격화 (별도 plan, measurement_unreliable_blocked verdict 해소 후).
- motion-id 별 미세 튜닝 (v2).
- EMG 기반 근육 힘 방향 단정 (v2).
- 카메라 앵글 합성 / 다각도 시점 (v2).
- forceSignalsByPhase aggregate (v2).
- per-motion expected_timing yaml (v2).
- release phase 박제 (v1.5).
- 임계 sweep dashboard (belle 운영 작업).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FORCE-01 | 중심축 이탈·접촉점 안정성·jerk/jitter 기초 신호로부터 ForceDirectionPattern 이 phase별로 추론되고, 동작 실패 원인 후보 상위 3개가 카드 형태로 제시된다. "근육 힘 방향" 단정 금지 — 모두 "가능성" 표기. | Phase 8 은 FORCE-01 의 **신호 layer** (전반부) — 본 RESEARCH §"AxisDeviationMetric Algorithm" + §"StabilityMetric Algorithm" + §"ContactStabilityMetric Algorithm" + §"5-Phase Motion Split" + §"Confidence + Smoothing" 가 4 success criteria 1:1 박제. Phase 9 가 본 phase 의 3 metric list + phaseBoundaries 를 consume 해 `inferForceDirectionPattern` 박제. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

| 출처 | Directive | 본 phase 적용 |
|---|---|---|
| §3 | 기술 스택 (변경 금지) — Python Lambda + RunPod GPU + Firestore | force_signals.py 는 numpy + 기존 helpers 만 사용 (boto3/네트워크 무관 pure 함수). Layer 2 Gemini 호출은 `gemini_moment_extractor` adapter 통과 (기존 박제). |
| §3 | 시크릿 — Parameter Store | Layer 2 Gemini API 키 = 기존 `/sunity/motion/gemini-api-key` SecureString 재사용 (Plan 01-13 박제). 본 phase 신규 시크릿 0. |
| §4 | 디자인 — 브랜드 컬러 / 라이트 전용 | 본 phase = 백엔드. UI 무관. Phase 12 가 본 phase 출력 소비 시 적용. |
| §7 | 작은 단위 작업, 의미있는 테스트, 이모지 금지, 슬롭 코드 금지 | dataclass + pure 함수 + 단위 test. canned warning 카피 안 이모지 금지. |
| Cross-cutting | `analysis.ts` ↔ `models.py` ↔ `contract.md` 3-way lockstep | 신설 7 TS 타입 + Python re-export + `docs/contract.md §9` 단일 atomic commit. |
| Cross-cutting | 한국어 user-facing, 영어 식별자 | warning 코드 (`occlusion_high_lock` 등) = 영어, 사용자 노출 카피 = Phase 11 책임 (본 phase 신호만). |
| Cross-cutting | Firestore nested-array 금지 ([[firestore-nested-array-flat]]) | `axisMetrics: list[dict-of-scalars-only]` + `phaseBoundaries: list[dict-of-scalars-only]` 박제. `_validate_dict_only_scalars` 통과 강제. |
| [[no-baekje-filler]] | "박제" 단어 — 전용어, 응답당 2~3회 한정 | 본 RESEARCH 본문 신중. 출력 카피 안 "박제" 사용 금지 (warning 코드만). |
| [[analysis-objectivity-no-human-scores]] | 사람 점수 라벨링 영구 X | severity 임계 = 도메인 룰 fixed (D-08-D2/D3/D4) — belle/강사/심사자 점수 라벨 0. |
| [[scoring-dimensions-ipsf]] | 점수 차원 = IPSF 기반, 좌우 대칭 제거 | tilt 임계 = IPSF Code of Points tolerance. 좌우 비대칭 자체는 metric 출력만 (감점 X — Phase 9/10 책임). |
| [[feedback-analysis-first]] | 분석 정확도 우선 | 5단계 분할 정확도 = Layer 1+2 하이브리드. Layer 1 단독 fallback 도 graceful degrade (분석 죽지 않음). |
| [[mvp-simple-pilot-quality]] | 구조만 열어두기 | motion-agnostic Layer 1 + motion_id 별 yaml 1줄 박제 → 새 동작 추가 비용 ~0. |
| [[firestore-nested-array-flat]] | nested-array 금지 | metric list 안 dict 는 모두 scalar-only. `_validate_dict_only_scalars` 통과. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 5-phase motion 분할 (entry/lock/transition/final_shape/hold) | Backend / pure-Python (`force_signals.compute_phase_boundaries`) | Backend adapter (`gemini_moment_extractor` for Layer 2) | Layer 1 = 순수 numpy 휴리스틱. Layer 2 호출은 어댑터 경계로 분리. 단위 test 가능. |
| 중심축 이탈 metric 산출 | Backend / pure-Python (`force_signals.compute_axis_deviation`) | — | pole-aligned 좌표 (Phase 1 PoseFrame) + body-scale (Phase 2 BodyNormalizationProfile) 입력만. 외부 의존 0. |
| 흔들림/jerk metric 산출 | Backend / pure-Python (`force_signals.compute_stability_metrics`) | Backend helper (`dimensions.stability_score` 재사용) | helper import 로 drift 방지. jerk 신설 산식만 본 모듈. |
| 접촉점 안정성 metric 산출 | Backend / pure-Python (`force_signals.compute_contact_stability`) | Backend data (`contact_points.yaml`) | proximity 계산 = pure numpy. expected_contact_points 매핑 = 정적 yaml load. |
| 가림 스무딩 + confidence 가중 | Backend / pure-Python (`temporal.temporal_fill` 재사용) | — | Phase 1 박제 모듈 그대로 사용. metric 산출 전 1회 적용. |
| Firestore 저장 | Backend (`firestore_admin.complete_analysis`) | — | 신설 kwarg `force_signals_report: dict` 추가. W5 validator + camelCase 변환 자동. |
| Frontend 렌더 | Frontend (Phase 12 책임) | — | 본 phase = 백엔드 신호만. UI 무관. |
| ForceDirectionPattern 추론 | Phase 9 책임 | — | 본 phase 의 3 metric + phaseBoundaries 를 input 으로 받음. |

**검증:** Phase 8 = **분석 코어 layer** (Phase 6 sibling). pipeline wiring 변경 최소 (1줄 호출 + complete_analysis kwarg 1개). Layer 2 Gemini 호출은 어댑터 경계로 분리되어 mock 으로 단위 test 가능. UI/Firestore schema 자동 변환.

## Standard Stack

### Core (모두 기존 — 신규 라이브러리 0)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | 3.12 | frozen dataclass 4개 (AxisDeviationMetric / StabilityMetric / ContactStabilityMetric / ForceSignalsReport) + `PhaseBoundary` | Phase 6/7 박제 패턴 정합 |
| Python stdlib `typing.Literal` | 3.12 | `MotionPhase = Literal['entry','lock','transition','final_shape','hold']` + `DeviationDirection` + `ContactPoint` enum 박제 | Phase 6 `ComparisonType` 정합 |
| numpy | >=1.26,<2.0 | (T,J) 행렬 + 3차 미분 + median/MAD 산출 | 기존 stack |
| PyYAML | (stdlib `yaml` 또는 `PyYAML>=6.0`) | `contact_points.yaml` load — motion_id → expected_contact_points 매핑 | 정적 데이터 load. `judging/loader.py` 가 이미 사용 (Plan 01-15 박제) |
| `pytest >=8,<9` | 8.x | 단위 test (분할 휴리스틱 + 3 metric 산출 + drift defense) | Phase 6/7 정합 |

### Supporting (모두 기존)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sunity_shared.analysis.temporal::temporal_fill` | 내부 | 가림 보간 + 신뢰도 가중 스무딩 — D-08-U1 박제 source | metric 산출 직전 1회 적용 |
| `sunity_shared.analysis.dimensions::_select_window` | 내부 | `hold` phase windowing — 5단계 분할의 `hold` 단계 산출 helper 재사용 | StabilityMetric `holdStabilityScore` |
| `sunity_shared.analysis.dimensions::stability_score` | 내부 | inter-frame median wobble → jitterScore 산출 | D-08-C1 박제 source |
| `sunity_shared.analysis.dimensions::stability_wobble_by_joint` | 내부 | 관절별 wobble → unstableBodyParts 필터 | D-08-C1 박제 source |
| `sunity_shared.analysis.body_normalization::BodyNormalizationProfile` | 내부 | torso_scale + estimated_height_scale → 거리 정규화 input | D-08-D1 박제 source |
| `sunity_shared.analysis.pose_frame::PoseFrame.landmarks_pole_aligned` | 내부 | pole-aligned COCO-17 좌표 → 거리/tilt 산출 input | Phase 8 본체 input |
| `sunity_shared.analysis.pose_frame::PoseFrame.reliability` | 내부 | frame-level 'low'/'medium'/'high' → confidence 가중치 산출 | D-08-U1 박제 source |
| `sunity_shared.analysis.pose_frame::PoleAxis` | 내부 | axis_vector + base_point → 거리 측정 reference axis | 본 phase 본체 input |
| `sunity_shared.analysis.skeleton::JOINT_KEYS` + `KEYPOINT_NAMES` | 내부 | 17 COCO keypoint 매핑 + 8 joint angle | wobble_by_joint 결과 필터 |
| `sunity_shared.judging.gemini_moment_extractor::GeminiMomentExtractor` | 내부 | Layer 2 5단계 timestamp 추출 (재사용, 코드 변경 0) | D-08-A2 Layer 2 |
| `sunity_shared.analysis.gemini_technique_recognizer::TechniqueProfile.motion_id` | 내부 | motion_id → expected_contact_points yaml lookup key | D-08-B1 박제 source |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| reuse `dimensions.stability_score` | Re-implement in `force_signals.py` | Drift 위험 — Phase 12.5 v4 Codex HIGH-2 가 정확히 이 문제 박제. `dimensions._select_window` 공유 강제. |
| 5-phase 분할 by motion-agnostic 휴리스틱 | per-motion expected_timing yaml | belle 박제 거부 (D-08-B2) — 새 동작군 박제 부담 0 위해 motion-agnostic 채택. |
| Gemini 보강 (ContactStability) | proximity 단독 | belle 박제 거부 (D-08-B3) — 같은 정보 다른 시각, cross-validation 가치 약함. |
| jerk = `np.diff(angles, n=3, axis=0)` 직접 | Savitzky-Golay 3차 derivative | scipy 의존 추가 — 본 phase = numpy 만 (D-08-C3 pure 함수 정합). MAD 기반 outlier rejection 으로 노이즈 흡수. |
| severity 임계 = 정은지 sweep 분포 | 도메인 룰 fixed | belle 박제 (D-08-D2/D3/D4) — [[scoring-dimensions-ipsf]] + [[analysis-objectivity-no-human-scores]] 정합. |

### Installation

신규 외부 의존 0. 모든 import 는 기존 모듈.

```bash
# 신규 설치 없음. 기존 backend dev 환경에서 그대로 작동.
cd backend && pip install -e .  # dev shell — 변경 없음
```

**Version verification:**

```bash
# 기존 모듈 (변경 0 — 확인만):
python3 -c "from sunity_shared.analysis import temporal, dimensions, body_normalization, pose_frame, skeleton; print('OK')"
python3 -c "from sunity_shared.judging import gemini_moment_extractor; print('OK')"
```

## Package Legitimacy Audit

본 phase 는 외부 패키지 신규 설치 **없음**. 기존 박제 의존만 사용 (numpy / google-genai / boto3 / firebase-admin / pytest — 모두 Phase 1/6 박제 완료, slopcheck 무관).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| — | — | — | — | — | — | **No new packages — reuse only** |

## Architecture Patterns

### System Architecture Diagram

```
[pipeline/app.py::_process]
    │
    ├─ _extract_video_analysis_inputs() → PoseFrame list + pole_axis + body_normalization_profile + motion_id
    │
    ├─ compare_body_profiles() → BodyComparisonReport [Phase 6 박제]
    │
    ├─ compute_force_signals(                            ← Phase 8 신설 wiring (1줄)
    │     pose_frames, pole_axis, body_profile,
    │     motion_id=technique_profile.motion_id,
    │     gemini_extractor=_GEMINI_MOMENT_EXTRACTOR,    ← optional singleton
    │  )
    │     │
    │     ├─ Step 1: temporal_fill(angles, uncertainty) → smoothed (T,J)   [기존 박제]
    │     │
    │     ├─ Step 2: compute_phase_boundaries(pose_frames, pole_axis, body_profile, motion_id?, gemini_extractor?)
    │     │            │
    │     │            ├─ Layer 1 heuristic: foot_y / hand-pole_dist / keypoint-variance
    │     │            │   → list[PhaseBoundary] (entry/lock/transition/final_shape/hold)
    │     │            │
    │     │            └─ Layer 2 (motion_id 인식 + gemini_extractor 있을 때만):
    │     │                gemini_extractor.extract_key_moments(video_uri, motion_id)
    │     │                → assign_frame_indices()
    │     │                → 5-phase boundary 추론 (setup→entry, hold→hold, peak→final_shape, release→transition)
    │     │                → Layer 1 과 일치 검증 → confidence 갱신 (high/medium/low)
    │     │
    │     ├─ Step 3: compute_axis_deviation(pose_frames, phase_boundaries, body_profile, pole_axis)
    │     │            → list[AxisDeviationMetric]  (1 per phase × confidence)
    │     │
    │     ├─ Step 4: compute_stability_metrics(angles, phase_boundaries, pose_frames)
    │     │            → list[StabilityMetric]      (1 per phase)
    │     │              ├─ jitterScore = stability_score(angles[s:e])
    │     │              ├─ jerkScore = MAD-filtered np.diff(angles, n=3)
    │     │              ├─ holdStabilityScore = stability_score(angles[hold_s:hold_e])
    │     │              └─ unstableBodyParts = filter(stability_wobble_by_joint > threshold)
    │     │
    │     └─ Step 5: compute_contact_stability(pose_frames, phase_boundaries, pole_axis, body_profile, motion_id)
    │                  → list[ContactStabilityMetric]   (1 per expected_contact_point per phase)
    │                    ├─ proximity: distance(keypoint, pole_axis) < 8% * torso_scale
    │                    ├─ estimatedStable: holds ≥ debounce_frames within phase
    │                    └─ lostContactAtMs: first frame > threshold (debounced)
    │
    └─ firestore_admin.complete_analysis(
            ...,
            force_signals_report=_dataclass_to_camel_case_dict(report),   ← Phase 6 박제 path 그대로
        )
```

### Recommended Module Structure

```
backend/shared/python/sunity_shared/analysis/
  force_signals.py            # NEW — 본 phase 본체 (pure functions + 4 dataclass)
  ...

backend/judging_data/
  contact_points.yaml         # NEW — motion_id → expected_contact_points 매핑

backend/tests/
  phase08/
    __init__.py               # Phase 6/7 패턴 정합
    conftest.py               # 합성 PoseFrame fixture factory
    fixtures/
      _factory.py             # synthetic motion 영상 (T=60, J=17, hold/transition 명확)
      fixture_clean_invert.json
      fixture_pelvis_drop.json
      fixture_occluded_lock.json
      fixture_motion_id_unrecognized.json
      fixture_jerk_high.json
    test_compute_phase_boundaries.py   # Layer 1 휴리스틱 + Layer 2 mock + Layer 1+2 일치/불일치 confidence
    test_compute_axis_deviation.py     # tilt 부호 + deviationDirection enum + severity 임계
    test_compute_stability_metrics.py  # jitter/jerk/hold + dimension 함수 reuse drift 방지
    test_compute_contact_stability.py  # proximity + debounce + abnormal release 검출
    test_compute_force_signals.py      # umbrella + temporal_fill 통과 검증 + confidence 가중
    test_firestore_lockstep.py         # camelCase 변환 + nested-array 회피 + W5 통과
```

### Pattern 1: Pure-function + frozen dataclass + helper reuse

**What:** Phase 6/7 박제 패턴 그대로. force_signals.py 의 모든 산출 함수 = 순수 numpy + 기존 helper import. 외부 의존 X (Layer 2 만 어댑터 경계).

**When to use:** 분석 코어 layer 단위 test 가능성 + drift 방지.

**Example:**
```python
# Source: backend/shared/python/sunity_shared/analysis/force_signals.py
"""Force signals 추출 layer (Phase 8 본체).

dimensions.py 는 점수 출력 (0~100), force_signals.py 는 진단 신호 raw 수치.
호출 site 분리 (D-08-C3) — helper 함수 import 재사용.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import numpy as np
from . import temporal, dimensions, skeleton
from .body_normalization import BodyNormalizationProfile
from .pose_frame import PoseFrame, PoleAxis
from .technique import TechniqueProfile

MotionPhase = Literal["entry", "lock", "transition", "final_shape", "hold"]
DeviationDirection = Literal["up", "down", "left", "right", "outward", "inward", "unknown"]
SeverityLevel = Literal["low", "medium", "high"]
MetricConfidence = Literal["low", "medium", "high"]
ContactPoint = Literal[
    "left_hand", "right_hand",
    "left_inner_thigh", "right_inner_thigh",
    "left_knee", "right_knee",
    "left_foot", "right_foot",
    "left_ankle", "right_ankle",
    "hip", "unknown",
]

@dataclass(frozen=True)
class PhaseBoundary:
    phase: MotionPhase
    start_frame_idx: int
    end_frame_idx: int
    confidence: MetricConfidence
    source: Literal["heuristic", "gemini_assisted", "heuristic_fallback"]

@dataclass(frozen=True)
class AxisDeviationMetric:
    phase: MotionPhase
    pelvis_distance_from_pole_axis: float   # body-scale normalized (torso_scale 단위)
    chest_distance_from_pole_axis: float    # body-scale normalized
    shoulder_tilt: float                    # degrees (signed, perpendicular to pole_axis horizontal)
    hip_tilt: float                         # degrees (signed)
    deviation_direction: DeviationDirection
    severity: SeverityLevel
    confidence: MetricConfidence
    warnings: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class StabilityMetric:
    phase: MotionPhase
    jitter_score: float                     # raw inter-frame median wobble (degrees)
    jerk_score: float                       # MAD-filtered 3rd derivative median (deg/frame^3)
    hold_stability_score: float | None      # raw value on hold sub-window (None if phase != hold)
    unstable_body_parts: list[str]          # joint names exceeding threshold
    severity: SeverityLevel
    confidence: MetricConfidence
    warnings: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class ContactStabilityMetric:
    phase: MotionPhase
    contact_point: ContactPoint
    estimated_stable: bool | None           # null when motion_id unrecognized
    lost_contact_at_ms: int | None
    distance_at_lost_ms: float | None       # body-scale normalized
    confidence: MetricConfidence
    severity: SeverityLevel
    warnings: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class ForceSignalsReport:
    phase_boundaries: list[PhaseBoundary]
    axis_metrics: list[AxisDeviationMetric]
    stability_metrics: list[StabilityMetric]
    contact_metrics: list[ContactStabilityMetric]
    overall_confidence: MetricConfidence    # min of layer agreement + temporal_fill warnings
    warnings: list[str] = field(default_factory=list)
    version: str = "1.0"

# Public API
def compute_force_signals(
    pose_frames: list[PoseFrame],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
    *,
    motion_id: str | None = None,
    gemini_extractor: "GeminiMomentExtractor | None" = None,
    video_uri: str | None = None,
    fps: float = 9.0,
) -> ForceSignalsReport:
    """Phase 8 통합 헬퍼. pipeline/app.py::_process 가 1줄로 호출."""
    ...
```

### Pattern 2: motion-agnostic Layer 1 heuristic

**What:** 발 keypoint vertical 위치 / 폴축까지 손 거리 / keypoint 변화율 cutoff 의 3 신호 조합으로 5단계 boundary 추론. motion_id 무관 — 모든 영상 작동.

**When to use:** Layer 2 (Gemini) 가 없거나 motion_id 미인식 시 항상 작동하는 baseline.

**Example:**
```python
def _layer1_heuristic_boundaries(
    pose_frames: list[PoseFrame],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
) -> list[PhaseBoundary]:
    """Motion-agnostic 5-phase 휴리스틱.

    신호:
      foot_y_relative: 양 발 y 좌표 평균 (image-down 좌표 — 작을수록 위).
        - threshold = 비디오 안 lowest_foot_y * 0.85 (ground level proxy).
      hand_pole_distance: 양 손 - pole_axis 최소 거리.
      keypoint_velocity: ‖keypoints[t] - keypoints[t-1]‖ 의 17 keypoint 평균.

    룰:
      entry        = foot_y_relative >= ground_threshold AND keypoint_velocity > velocity_mid
                     (땅에 발이 있고 움직임 활발). 영상 안 person 이 이미 폴 위에서 시작
                     하면 entry phase 는 0-length (start=end=0, confidence='low'+warning).
      lock         = hand_pole_distance < body_scale * 0.15 (손이 폴을 잡음) AND
                     foot_y_relative < ground_threshold AND keypoint_velocity 감소 시작.
      transition   = keypoint_velocity 높음 (>velocity_mid) AND lock 직후.
      final_shape  = keypoint_velocity 감소 (<velocity_mid * 0.7) AND lock 이후 변동 마지막 1초.
      hold         = `dimensions._select_window(angles)` 의 분산 최소 구간 (기존 박제 재사용).

    빈 phase (e.g. 영상이 hold 직진입) 는 빈 PhaseBoundary (start=end) + warning.
    """
    ...
```

### Pattern 3: Layer 2 Gemini key_moments 통합

**What:** `gemini_moment_extractor.GeminiMomentExtractor.extract_key_moments()` 가 이미 박제된 setup/hold/peak/release 4 timestamp 를 5-phase boundary 로 매핑. Plan 01-13 의 measurement_unreliable_blocked 는 IPSF criteria 비교 chain 의심이지 key_moment 시각 자체의 의심은 아님 — Phase 8 use case (timestamp 만 사용) 에 직접 적용 안 됨.

**Mapping rule (Layer 2 → 5-phase):**

| Gemini key_moment | 5-phase boundary 영향 |
|---|---|
| `setup` | `entry` 끝 = `lock` 시작 (setup.timestamp ± epsilon) |
| `hold` | `final_shape` 끝 = `hold` 시작 (hold.timestamp = hold phase 진입) |
| `peak` | `final_shape` 의 대표 시점 (final_shape window 안 중앙) |
| `release` | `hold` 끝 (`release.timestamp` = hold 종료 시각) |

**일치 검증 (D-08-A2 confidence):**
- Layer 1 + Layer 2 timestamp 차이 ≤ 200ms (~ 9fps × 2 frames) → 일치 → confidence='high'
- 차이 > 200ms but ≤ 500ms → confidence='medium' + warning='layer_disagreement_minor'
- 차이 > 500ms 또는 Layer 2 timestamp 가 Layer 1 phase 순서를 뒤집음 → confidence='low' + warning='layer_disagreement_major' + Layer 1 boundary 사용 (Layer 2 무시)

**Example:**
```python
def _layer2_gemini_boundaries(
    layer1_boundaries: list[PhaseBoundary],
    video_uri: str,
    motion_id: str,
    fps: float,
    frames_total: int,
    gemini_extractor: "GeminiMomentExtractor",
) -> list[PhaseBoundary]:
    """Gemini key_moments 로 layer1 boundary 보강.

    extract_key_moments() 의 cache (video_uri, motion, model) 가 Phase 5 호출
    결과를 재사용 (비용 절감 — Plan 01-13 박제 _cache).
    """
    moments = gemini_extractor.extract_key_moments(video_uri, motion_id)
    from sunity_shared.judging.gemini_moment_extractor import assign_frame_indices
    moments = assign_frame_indices(moments, fps=fps, frames_total=frames_total)
    # Map moment.frame_index → 5-phase boundaries
    ...
```

### Pattern 4: Helper reuse + drift defense

**What:** Phase 12.5 v4 Codex HIGH-2 박제 — 모든 windowing/wobble 계산은 `dimensions._select_window` / `dimensions.stability_wobble_by_joint` 단일 호출 site. force_signals.py 는 import 만, 재구현 X. 단위 test 에 drift assert 추가.

**Example:**
```python
def _compute_stability_for_phase(
    angles: np.ndarray,
    phase_window: tuple[int, int],
) -> tuple[float, list[str]]:
    """phase window 안 stability metric — dimensions helper 재사용."""
    s, e = phase_window
    sliced = angles[s:e]
    if sliced.shape[0] < 2:
        return 0.0, []
    inter_frame_diff = np.abs(np.diff(sliced, axis=0))
    median_jerk = np.nanmedian(inter_frame_diff, axis=0)
    wobble = float(np.nanmean(median_jerk))
    # unstable_body_parts: dimensions.stability_wobble_by_joint 와 동일 산식
    wobble_by_joint = dimensions.stability_wobble_by_joint(sliced, profile=None)
    unstable = [
        k for k, v in wobble_by_joint.items()
        if v > UNSTABLE_BODY_PART_THRESHOLD_DEG
    ]
    return wobble, unstable
```

### Anti-Patterns to Avoid

- **`dimensions.stability_score` 산식 복제** — force_signals.py 가 wobble 산식을 다시 작성하면 dimensions.py 와 drift. helper import 강제, 단위 test 에서 동일 input 시 동일 output assert.
- **5-phase boundary 의 motion_id 별 분기** — D-08-A3 위반. motion-agnostic Layer 1 + (옵션) Layer 2 보강만.
- **severity 임계를 정은지 sweep 분포로 보정** — D-08-D3/D4 위반. fixed 임계만, sweep = sanity check.
- **Gemini 가 좌표/점수/판단 출력** — Plan 01-13 박제 정규식 가드 자동 차단. Phase 8 도 같은 어댑터 통과.
- **Firestore nested-array (list 안 list)** — `_validate_dict_only_scalars` 가 TypeError raise. metric list 안 dict 는 모두 scalar-only.
- **video URL 을 Layer 2 에 직접 전달 (S3 path)** — Plan 01-13 박제 `gemini_moment_extractor` 는 로컬 path 만 지원. pipeline 의 `_extract_video_analysis_inputs(..., keep_local_video=True)` 호출 결과 사용.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 가림 보간 + 신뢰도 가중 스무딩 | custom occlusion smoother | `temporal.temporal_fill` | 이미 NLF/RTMW uncertainty + MAD outlier + 신뢰도 가중 이동평균 박제 (D-08-U1 source). |
| hold-window 자동 검출 | custom hold detector | `dimensions._select_window` / `hold_window` | 분산 최소 구간 + profile.hold_window 우선 박제 (Phase 12.5 v4 박제 drift 방지). |
| inter-frame wobble 계산 | custom diff/median | `dimensions.stability_wobble_by_joint` | 동일 산식 강제로 dimensions 점수 vs force_signals 진단 일관성 보장. |
| Gemini API 호출 + Parameter Store key | custom Gemini client | `gemini_moment_extractor.GeminiMomentExtractor` | Plan 01-13 박제: lazy import + 좌표/점수/판단 정규식 가드 3 카테고리 + `_cache` (video, motion, model 키) + API 키 Parameter Store fallback + 신 `google-genai` SDK 마이그레이션. |
| Gemini timestamp → frame index 변환 | custom converter | `gemini_moment_extractor.assign_frame_indices` | clamp + validate + KeyMoment 정합 박제 (Plan 01-13). |
| Firestore camelCase 변환 + nested-array 검증 | custom serializer | `_dataclass_to_camel_case_dict` + `_validate_flat_dict_no_nested_array` + `_validate_dict_only_scalars` | Phase 6 W5 + C8 박제 (firestore_admin.py + pipeline/app.py). list[dict-of-scalars-only] 패턴 정합. |
| body-scale 거리 정규화 | custom torso length | `body_profile.torso_scale` (torso self-reference 1.0) | Phase 2 박제 (BodyNormalizationProfile v5 — measurer fallback 1.0 강제). |
| 5-phase split per-motion 휴리스틱 | per-motion 룰 yaml | motion-agnostic Layer 1 + (옵션) Gemini Layer 2 | D-08-A3 (새 동작군 박제 부담 0) + D-08-B2 (5-phase 일반 룰만). |
| contact 임계 frame 단위 debounce | custom state machine | `np.diff` + `np.where` + `_consecutive_runs` 헬퍼 | numpy 1차원 boolean 연산으로 5줄 박제 가능. |

**Key insight:** Phase 8 의 90% 는 기존 helper 호출 + 새 dataclass 4개 + 새 통합 함수 1개. 진짜 신설은 (1) 5-phase Layer 1 휴리스틱 (3 신호 cutoff 룰) + (2) jerk 산식 (np.diff n=3 + MAD outlier rejection) + (3) Layer 2 → 5-phase mapping + (4) contact_points.yaml 데이터. 나머지는 import.

## 5-Phase Motion Split — Layer 1 Heuristic 박제

### Signal sources

```python
def _phase_signals(
    pose_frames: list[PoseFrame],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
) -> dict[str, np.ndarray]:
    """3 motion-agnostic signals — Layer 1 heuristic input."""
    T = len(pose_frames)
    foot_y = np.full(T, np.nan)        # 양발 y 평균 (image-down: 작을수록 위)
    hand_pole_dist = np.full(T, np.nan)  # 양손 - pole_axis 최소 거리 (body-scale normalized)
    keypoint_velocity = np.zeros(T)    # ‖kp[t] - kp[t-1]‖ 의 17 keypoint 평균

    for t, frame in enumerate(pose_frames):
        kp = frame.keypoints_3d_pole_aligned
        # 발 vertical
        feet_y = [kp[n].y for n in ("left_ankle", "right_ankle") if n in kp]
        if feet_y:
            foot_y[t] = float(np.mean(feet_y))
        # 손-폴축 거리
        hand_distances = [
            _point_to_axis_distance(kp[n], pole_axis) / body_profile.torso_scale
            for n in ("left_wrist", "right_wrist") if n in kp
        ]
        if hand_distances:
            hand_pole_dist[t] = float(np.min(hand_distances))
        # velocity
        if t > 0:
            prev_kp = pose_frames[t - 1].keypoints_3d_pole_aligned
            vels = []
            for n in skeleton.KEYPOINT_NAMES:
                if n in kp and n in prev_kp:
                    vels.append(
                        np.linalg.norm(
                            np.array([kp[n].x, kp[n].y, kp[n].z])
                            - np.array([prev_kp[n].x, prev_kp[n].y, prev_kp[n].z])
                        )
                    )
            if vels:
                keypoint_velocity[t] = float(np.mean(vels)) / body_profile.torso_scale
    return {"foot_y": foot_y, "hand_pole_dist": hand_pole_dist, "velocity": keypoint_velocity}
```

### Ground-line proxy

person 이 폴 위에서 시작해 영상에 ground 가 안 보이는 경우 — `ground_y = nanmax(foot_y)` (image-down 좌표에서 가장 아래) 를 ground proxy 로 박제. entry phase = `foot_y >= ground_y * 0.85` AND `velocity > velocity_mid`. 영상 시작이 이미 폴 위라면 entry phase length=0 + warning='entry_not_detected'.

### Phase detection rules (researcher 초안 — belle Pod sweep sanity check before lock)

| Phase | 진입 조건 | 종료 조건 |
|---|---|---|
| `entry` | `foot_y[t] >= ground_y * 0.85` AND `velocity[t] > velocity_mid` | `hand_pole_dist[t] < 0.15` (손이 폴 가까이) — first occurrence |
| `lock` | `hand_pole_dist[t] < 0.15` AND `foot_y[t] < ground_y * 0.85` (발 떨어짐) | `velocity[t] > velocity_high` first occurrence after entry stops |
| `transition` | `velocity[t] > velocity_high` | `velocity[t] < velocity_mid * 0.7` for ≥ 3 consecutive frames |
| `final_shape` | velocity < velocity_mid * 0.7 sustained | hold phase 시작 (=arg-min variance window 진입) |
| `hold` | `dimensions._select_window(angles)` 결과 (분산 최소 구간) | `_select_window` 의 end |

**Thresholds (researcher 초안, body-scale normalized — belle Pod sweep sanity check before lock):**

| Constant | Initial value | Source / Note |
|---|---|---|
| `ground_y_relative` | `nanmax(foot_y) * 0.85` | 영상별 동적. entry detection |
| `hand_pole_dist_lock` | `0.15` (× torso_scale) | research §7.1 — pelvis-pole 거리 30% 의 절반 (손은 더 가까이) |
| `velocity_mid` | `0.03` (× torso_scale / frame) | 9fps × 0.03 ≈ torso 3% per frame. 자세 활발 변화 cutoff |
| `velocity_high` | `0.06` (× torso_scale / frame) | transition 진입 cutoff |
| `min_phase_frames` | `2` (≈ 220ms @ 9fps) | 단일 frame jitter 회피. phase length < 2 frames → 인접 phase 흡수 |

**[ASSUMED]** 위 4 threshold 는 researcher 초안. belle Pod `sweep_rtmw_20260603_1409` 5영상 sanity check (정은지 영상에서 phase 분할이 자연스러운지) 후 lock.

### Edge cases

- **영상이 hold 만:** entry/lock/transition/final_shape phase length=0 (warning='partial_motion_video'). hold 만 산출.
- **영상이 짧음 (T < 10):** 모든 phase 합쳐 단일 'hold' phase + warning='video_too_short'. confidence='low' 강제.
- **all-NaN angles (occlusion):** temporal_fill 통과 후도 NaN 잔존 시 phase boundary = (0, T) 단일 'hold' + warning='heavy_occlusion'. confidence='low'.

## 5-Phase Motion Split — Layer 2 Gemini Integration 박제

### Reuse 자산 (Plan 01-13 박제 — 코드 변경 0)

| Symbol | Path | 역할 |
|---|---|---|
| `GeminiMomentExtractor` | `sunity_shared/judging/gemini_moment_extractor.py` | Gemini client + cache + 좌표/점수/판단 정규식 가드 3 카테고리 + Parameter Store API 키 |
| `KeyMoment` | 같은 파일 | dataclass: motion + moment_key + timestamp_seconds + frame_index + confidence + source_response_excerpt |
| `VALID_MOMENT_KEYS` | `judging/geometric_criterion.py` | `setup` / `hold` / `peak` / `release` |
| `assign_frame_indices(moments, fps, frames_total)` | gemini_moment_extractor.py | timestamp → frame_index 변환 + validate() 자동 |
| `DEFAULT_GEMINI_MODEL` | gemini_moment_extractor.py | `gemini-3.1-pro-preview` (Phase 5 D-13 박제) |

### Layer 2 호출 조건 (D-08-A2)

```python
def _should_invoke_layer2(
    motion_id: str | None,
    gemini_extractor: "GeminiMomentExtractor | None",
    video_uri: str | None,
) -> bool:
    """Layer 2 wiring 조건:
      1. motion_id 가 None 이 아님 (FallbackRecognizer / unrecognized path 제외)
      2. gemini_extractor 가 주입됨 (singleton — pipeline/app.py 가 박제)
      3. video_uri 가 로컬 path (Gemini File API 제약 — Plan 01-13 박제)
    """
    return (
        motion_id is not None
        and gemini_extractor is not None
        and video_uri is not None
        and not video_uri.startswith(("http://", "https://", "s3://"))
    )
```

### Mapping rule (Gemini 4 moment → 5-phase)

```python
def _map_moments_to_5phase(
    layer1: list[PhaseBoundary],
    moments: list["KeyMoment"],  # already assign_frame_indices() applied
) -> list[PhaseBoundary]:
    """
    Gemini 4 key_moment → 5-phase boundary mapping:
      setup.frame   ≈ entry.end / lock.start
      hold.frame    ≈ final_shape.end / hold.start
      peak.frame    ≈ final_shape 의 대표 시점 (representative — boundary 변경 X)
      release.frame ≈ hold.end

    transition phase boundary 는 Gemini moment 가 직접 제공하지 않음 →
    Layer 1 의 transition 유지 (lock.end ~ final_shape.start 사이).
    """
    by_key = {m.moment_key: m for m in moments}
    layer1_by_phase = {b.phase: b for b in layer1}
    boundaries: list[PhaseBoundary] = []

    setup_frame = by_key.get("setup").frame_index if "setup" in by_key else layer1_by_phase["entry"].end_frame_idx
    hold_frame = by_key.get("hold").frame_index if "hold" in by_key else layer1_by_phase["final_shape"].end_frame_idx
    release_frame = by_key.get("release").frame_index if "release" in by_key else layer1_by_phase["hold"].end_frame_idx

    # 5-phase boundary 재구성 (Layer 1 transition 유지)
    boundaries = [
        PhaseBoundary("entry", 0, setup_frame, confidence="high", source="gemini_assisted"),
        PhaseBoundary("lock", setup_frame, layer1_by_phase["transition"].start_frame_idx,
                       confidence="high", source="gemini_assisted"),
        PhaseBoundary("transition", layer1_by_phase["transition"].start_frame_idx,
                       layer1_by_phase["transition"].end_frame_idx,
                       confidence="medium", source="heuristic"),  # Layer 2 모름
        PhaseBoundary("final_shape", layer1_by_phase["transition"].end_frame_idx,
                       hold_frame, confidence="high", source="gemini_assisted"),
        PhaseBoundary("hold", hold_frame, release_frame, confidence="high", source="gemini_assisted"),
    ]
    return boundaries
```

### Agreement check (D-08-A2 confidence)

```python
LAYER_AGREEMENT_TOLERANCE_FRAMES = 2  # ≈ 220ms @ 9fps
LAYER_DISAGREEMENT_MAJOR_FRAMES = 5   # ≈ 555ms @ 9fps

def _confidence_from_agreement(
    layer1: list[PhaseBoundary],
    layer2: list[PhaseBoundary],
) -> tuple[MetricConfidence, list[str]]:
    """boundary timestamp 차이로 confidence 산출.

    각 phase 의 (start_frame_idx, end_frame_idx) 차이 abs 의 max:
      <= 2 frames → 'high' + no warning
      <= 5 frames → 'medium' + warning 'layer_disagreement_minor'
      >  5 frames OR ordering 뒤집힘 → 'low' + warning 'layer_disagreement_major'
                                                       → Layer 1 사용 (Layer 2 무시)
    """
    if layer2 is None:
        return ("medium", ["layer2_unavailable"])
    diffs = []
    by_phase1 = {b.phase: b for b in layer1}
    by_phase2 = {b.phase: b for b in layer2}
    for phase in ("entry", "lock", "transition", "final_shape", "hold"):
        if phase in by_phase1 and phase in by_phase2:
            diffs.append(abs(by_phase1[phase].start_frame_idx - by_phase2[phase].start_frame_idx))
            diffs.append(abs(by_phase1[phase].end_frame_idx - by_phase2[phase].end_frame_idx))
    if not diffs:
        return ("low", ["layer2_no_phases"])
    max_diff = max(diffs)
    if max_diff <= LAYER_AGREEMENT_TOLERANCE_FRAMES:
        return ("high", [])
    if max_diff <= LAYER_DISAGREEMENT_MAJOR_FRAMES:
        return ("medium", ["layer_disagreement_minor"])
    return ("low", ["layer_disagreement_major"])
```

### Plan 01-13 verdict 와 Phase 8 use case 분리

**Plan 01-13 verdict = `measurement_unreliable_blocked`** (5/5 minimum_requirement fail, IPSF criteria 비교 chain 의심). 정밀하게:

| Plan 01-13 chain | 신뢰도 | Phase 8 use case 영향 |
|---|---|---|
| Gemini → key_moment timestamp 자체 | **OK** (좌표/점수/판단 가드 0건 발동, 응답 정책 준수) | **Phase 8 직접 사용** — phase boundary 산출 |
| key_moment.frame → measure_moment_angles → IPSF criterion 비교 | **의심** (right_shoulder 18.2° 등 비정상 측정값, Plan 12 (e) verdict 직접 연결) | Phase 8 = 측정 X (IPSF 비교 X). Phase 9 force-pattern 추론도 phase boundary timestamp 만 사용 (자체 metric 산출은 Phase 8 분산/거리 metric). |

**결론:** Phase 8 의 Layer 2 wiring = Plan 01-13 의 measurement_unreliable_blocked verdict 와 직접 무관. v1 wiring 가능. Plan 01-13 의 후속 plan (criteria 비교 chain 측정 신뢰도 root cause spike) 와 별개로 진행.

## AxisDeviationMetric Algorithm

### Distance computation (D-08-D1 body-scale normalized)

```python
def _point_to_axis_distance(
    point: "Keypoint3DAligned",
    pole_axis: PoleAxis,
) -> float:
    """3D point 가 pole_axis 위로의 정사영까지의 거리 (magnitude).

    pole-aligned 좌표계에서 pole_axis = (0, 1, 0) (수직 fallback case) 또는
    detected vector. axis_vector unit norm 박제. base_point 는 (0, 0, 0) 가정.

    distance = ‖point - (point · axis_vector) · axis_vector‖
    """
    p = np.array([point.x, point.y, point.z])
    a = np.array(pole_axis.axis_vector)
    proj = np.dot(p, a) * a
    return float(np.linalg.norm(p - proj))

def _pelvis_distance(
    frame: PoseFrame,
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
) -> float | None:
    kp = frame.keypoints_3d_pole_aligned
    if "left_hip" not in kp or "right_hip" not in kp:
        return None
    pelvis_mid = Keypoint3DAligned(
        x=(kp["left_hip"].x + kp["right_hip"].x) / 2,
        y=(kp["left_hip"].y + kp["right_hip"].y) / 2,
        z=(kp["left_hip"].z + kp["right_hip"].z) / 2,
    )
    raw = _point_to_axis_distance(pelvis_mid, pole_axis)
    return raw / body_profile.torso_scale  # body-scale normalized

def _chest_distance(...) -> float | None:
    # mid of left_shoulder + right_shoulder, same formula
    ...
```

### Tilt computation

```python
def _shoulder_tilt(
    frame: PoseFrame,
    pole_axis: PoleAxis,
) -> float | None:
    """어깨 line 과 pole_axis 의 수직선 (horizontal plane) 사이 각도 (deg, signed).

    Convention:
      pole_axis 가 'up' (vertical_fallback 의 경우 (0, 1, 0)) 가정.
      shoulder_vector = right_shoulder - left_shoulder (오른쪽 양수 — 화면 기준).
      reference horizontal = axis_vector 와 수직인 평면 위의 방향.

    Signed angle:
      +값 = 오른쪽 어깨가 위 (image-up 의 반대 — image-down 좌표에서 y 더 작음)
      -값 = 왼쪽 어깨가 위

    Range: [-90°, +90°] (clamp).
    """
    kp = frame.keypoints_3d_pole_aligned
    if "left_shoulder" not in kp or "right_shoulder" not in kp:
        return None
    ls = np.array([kp["left_shoulder"].x, kp["left_shoulder"].y, kp["left_shoulder"].z])
    rs = np.array([kp["right_shoulder"].x, kp["right_shoulder"].y, kp["right_shoulder"].z])
    shoulder_vec = rs - ls
    axis = np.array(pole_axis.axis_vector)
    # Project onto plane perpendicular to axis
    shoulder_perp = shoulder_vec - np.dot(shoulder_vec, axis) * axis
    if np.linalg.norm(shoulder_perp) < 1e-6:
        return None  # shoulders aligned with pole — undefined tilt
    # angle between shoulder_perp and image-x reference
    # for signed: use cross product with axis to get sign
    sign = np.sign(np.dot(np.cross(shoulder_perp, np.array([1, 0, 0])), axis))
    cos_a = np.clip(shoulder_perp[0] / np.linalg.norm(shoulder_perp), -1.0, 1.0)
    angle = np.degrees(np.arccos(cos_a))
    # convert to signed tilt around horizontal (clamp to [-90, 90])
    if angle > 90:
        angle = 180 - angle
    return float(sign * angle)

def _hip_tilt(...) -> float | None:
    # same formula with left_hip / right_hip
    ...
```

### deviationDirection enum mapping rules

```python
def _deviation_direction(
    pelvis_distance: float | None,
    pelvis_kp: "Keypoint3DAligned | None",
    prev_pelvis_kp: "Keypoint3DAligned | None",
    pole_axis: PoleAxis,
) -> DeviationDirection:
    """
    Mapping rules:
      pelvis_y_delta = pelvis.y - prev_pelvis.y  (image-down 좌표: y 증가 = 아래)
      pelvis_x_delta = pelvis.x - prev_pelvis.x
      pelvis_distance_delta = current_distance - prev_distance

      pelvis_y_delta > body_scale * 0.05 over phase → 'down'
      pelvis_y_delta < -body_scale * 0.05 over phase → 'up'
      pelvis_distance_delta > 0.05 (outward) → 'outward'
      pelvis_distance_delta < -0.05 (inward) → 'inward'
      pelvis_x_delta > 0.05 → 'right'
      pelvis_x_delta < -0.05 → 'left'
      otherwise → 'unknown'

    Priority order: distance_delta (outward/inward) > y_delta (up/down) > x_delta (left/right).
    """
    ...
```

### severity thresholds (researcher 초안 — belle Pod sweep sanity check before lock)

| Metric | low | medium | high | Source / Note |
|---|---|---|---|---|
| `pelvis_distance_from_pole_axis` | < 0.15 (× torso_scale) | 0.15 ~ 0.30 | > 0.30 | research 02 §4.2 "골반-폴 거리 증가 = 힘이 바깥으로 새는 패턴". 30% = research 의 "중심축 이탈" significant threshold |
| `chest_distance_from_pole_axis` | < 0.20 | 0.20 ~ 0.40 | > 0.40 | 흉곽은 골반보다 자연 거리 큼 — 임계 +0.05 |
| `shoulder_tilt` | abs < 10° | 10°~25° | > 25° | **[ASSUMED]** IPSF Code of Points tolerance lookup 권장 — NotebookLM query "shoulder line tilt tolerance" (`notebook-lm-pole-sports` memory) |
| `hip_tilt` | abs < 10° | 10°~25° | > 25° | **[ASSUMED]** IPSF Code of Points tolerance lookup — "hip line tilt tolerance". 폴 동작은 비대칭 자연 — 25° 까지 가능성 표기만 |

**`[ASSUMED]` 처리:** IPSF Code of Points 가 명시적 tilt tolerance 정의를 가지는지 NotebookLM 으로 확인 — 없으면 researcher 가 한 motion-analysis literature 의 자세 ML 표준 (Lugaresi et al. 2019 BlazePose 등) 의 default 임계 차용 + belle 검수 박제. belle Pod sweep 으로 정은지 분포가 90%+ 'low' 떨어지는지 sanity check.

## StabilityMetric Algorithm

### jitterScore (D-08-C1 재사용)

`dimensions.stability_score(angles[s:e], profile)` 의 산식:
- `inter_frame_diff = np.abs(np.diff(sliced, axis=0))` (T-1, J)
- `median_jerk = np.nanmedian(inter_frame_diff, axis=0)` (J,)
- `wobble = float(np.nanmean(median_jerk))` (scalar)
- 점수 = `kismam.score_from_deviation(wobble, _STABILITY_TOL_DEG=15.0)` (0~100)

**Phase 8 use case:** **raw wobble 값** 필요 (0~100 점수 아님). 두 옵션:

**Option A (권장): helper 추출**
```python
# dimensions.py 안에 신설 (Phase 8 wave 1 단일 commit)
def stability_wobble(angles, profile=None) -> float:
    """raw inter-frame median wobble (degrees) — stability_score 의 score 변환 전 값.

    force_signals.py 가 본 helper import → drift 방지.
    """
    sliced, _ = _select_window(angles, profile)
    if sliced.shape[0] < 2:
        return 0.0
    inter_frame_diff = np.abs(np.diff(sliced, axis=0))
    median_jerk = np.nanmedian(inter_frame_diff, axis=0)
    return float(np.nanmean(median_jerk))

# 기존 stability_score 갱신 (drift 방지):
def stability_score(angles, profile=None) -> int:
    wobble = stability_wobble(angles, profile)
    # ... 기존 sliced.shape 가드 ...
    return kismam.score_from_deviation(wobble, _STABILITY_TOL_DEG)
```

**Option B (gateway 호출):** force_signals.py 에서 `dimensions.stability_score(...) → kismam` 의 역산 — 코드 가독성 떨어짐. **Option A 권장.**

### jerkScore (D-08-C2 신설 산식)

**산식 박제 (researcher 결정):**
```python
JERK_SMOOTH_WINDOW = 3  # frames
JERK_MAD_K = 3.0        # outlier rejection

def _compute_jerk(angles_window: np.ndarray) -> float:
    """3차 미분 절댓값의 MAD-filtered median (deg / frame^3).

    노이즈 흡수:
      1. np.diff(angles, n=3, axis=0) → (T-3, J)
      2. abs 절댓값
      3. 각 joint 별 MAD outlier rejection (median + 3*1.4826*MAD 초과 제거)
      4. 남은 값의 nanmedian over (T-3) frames → (J,)
      5. nanmean over J → scalar jerkScore

    rationale:
      - 3차 미분 = 가속도 변화율 = 부드러움의 inverse
      - MAD 가 sample-mean 보다 outlier robust (temporal.py 의 _column_outliers 와 동일 패턴)
      - n=3 만큼 길이 짧아짐 — phase window < 5 frames 면 jerkScore = 0.0 + warning
    """
    if angles_window.shape[0] < 5:
        return 0.0
    third_deriv = np.abs(np.diff(angles_window, n=3, axis=0))  # (T-3, J)
    out = []
    for j in range(third_deriv.shape[1]):
        col = third_deriv[:, j]
        finite = col[np.isfinite(col)]
        if finite.size < 3:
            continue
        med = float(np.median(finite))
        mad = float(np.median(np.abs(finite - med)))
        if mad > 0:
            mask = col <= med + JERK_MAD_K * 1.4826 * mad
        else:
            mask = np.isfinite(col)
        filtered = col[mask & np.isfinite(col)]
        if filtered.size > 0:
            out.append(float(np.median(filtered)))
    if not out:
        return 0.0
    return float(np.mean(out))
```

### holdStabilityScore (D-08-C1 reuse)

`hold` phase 의 window 에 한정해 `stability_wobble()` 호출 (또는 score 직접). 5-phase boundary 안 hold phase 의 (start, end) 가 곧 `dimensions._select_window` 의 결과 (Layer 1 의 hold phase 산출 = `_select_window` 직접 호출). hold 가 detect 안 됨 (e.g., heavy occlusion) → `hold_stability_score = None` + warning.

### unstableBodyParts (D-08-C1 재사용)

```python
UNSTABLE_BODY_PART_THRESHOLD_DEG = 12.0  # researcher 초안 — 정은지 reference wobble 6~16° 박제 (dimensions._STABILITY_TOL_DEG=15 정합)

def _compute_unstable_body_parts(
    angles_window: np.ndarray,
    profile: "TechniqueProfile | None" = None,
) -> list[str]:
    """dimensions.stability_wobble_by_joint 재사용 → joint key list (Korean 라벨 X — Phase 11 책임).

    프로젝트 컨벤션 정합: backend 는 JOINT_KEYS (영어 영어), Phase 11 가 JOINT_LABEL_KO 매핑.
    skeleton.JOINT_LABEL_KO 박제 자산 활용 가능 (한국어 표시 phase 8 backend 가 아님).
    """
    wobble_by_joint = dimensions.stability_wobble_by_joint(angles_window, profile=profile)
    return sorted([
        k for k, v in wobble_by_joint.items()
        if v > UNSTABLE_BODY_PART_THRESHOLD_DEG
    ])
```

### severity (researcher 초안 — belle Pod sweep sanity check before lock)

| Metric | low | medium | high | Source |
|---|---|---|---|---|
| `jitter_score` (raw wobble, deg) | < 8 | 8 ~ 20 | > 20 | `dimensions._STABILITY_TOL_DEG=15` 정합. 8 = 정은지 reference 6~16° 박제의 lower bound. **[ASSUMED]** belle sweep sanity check 권장. |
| `jerk_score` (deg/frame^3) | < 5 | 5 ~ 15 | > 15 | **[ASSUMED]** motion-analysis 표준값 없음 — researcher 가 정은지 영상 5개 jerk 분포 측정 후 default 박제. sweep 으로 분포 확인. |
| `unstable_body_parts.length` | 0 | 1 ~ 2 | ≥ 3 | 8 joints 중 3+ wobble — 전반 불안정. |

## ContactStabilityMetric Algorithm

### expected_contact_points yaml (D-08-B1, D-08-B5)

**파일 위치:** `backend/judging_data/contact_points.yaml` (Plan 01-15 `judging_data/criteria/` 패턴 정합 — `judging/loader.py` PyYAML 박제).

**형식:**
```yaml
# backend/judging_data/contact_points.yaml
#
# motion_id 별 expected_contact_points 매핑 (D-08-B1).
# - Phase 8 가 motion_id 인식 시 (Phase 5 Gemini TechniqueProfile.motion_id) lookup.
# - 미인식 시 expected_contact_points = [] → 모든 손/발 keypoint 의 폴축 거리만 산출.
# - 새 motion 추가 = 1줄 박제 (D-08-B5).
# - belle/강사 도메인 검수 필요 (researcher 초안).

motions:
  # 인버트 계열 — 거꾸로 매달림 (research §13 폴스포츠-지식.md)
  ref-invert:
    expected_contact_points:
      - left_hand
      - right_hand
      - left_inner_thigh
      - right_inner_thigh

  # 후굴 계열 — 폭스탑 / 폭스탑 스플릿 (정은지 reference 박제)
  ref-foxtop:
    expected_contact_points:
      - left_hand
      - right_hand
      - left_ankle
      - right_ankle
      - hip

  ref-foxtop-split:
    expected_contact_points:
      - left_hand
      - right_hand
      - left_ankle
      - right_ankle
      - hip

  # 클라임/사이드웨이 스핀 — 기본 포징
  ref-climb:
    expected_contact_points:
      - left_hand
      - right_hand
      - left_inner_thigh
      - right_inner_thigh

  ref-sideway-spin:
    expected_contact_points:
      - left_hand
      - right_hand
      - left_knee
      - right_knee

# 미인식 fallback (D-08-B4)
default:
  expected_contact_points: []
```

**[ASSUMED]** 위 매핑은 **researcher 초안** — belle 폴스포츠 도메인 검수 필요. 인버트 / 후굴 / 클라임의 접촉점은 동작별 본질 속성이라 belle/강사 의견 필수.

**Loader:**
```python
import yaml
from pathlib import Path

_CONTACT_POINTS_PATH = Path(__file__).parent.parent.parent.parent.parent / "judging_data" / "contact_points.yaml"
_CONTACT_POINTS_CACHE: dict[str, list[ContactPoint]] | None = None

def _load_expected_contact_points(motion_id: str | None) -> list[ContactPoint]:
    global _CONTACT_POINTS_CACHE
    if _CONTACT_POINTS_CACHE is None:
        with _CONTACT_POINTS_PATH.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        _CONTACT_POINTS_CACHE = {
            mid: list(entry["expected_contact_points"])
            for mid, entry in raw.get("motions", {}).items()
        }
    if motion_id is None:
        return []
    return _CONTACT_POINTS_CACHE.get(motion_id, [])
```

### Proximity threshold + debounce (D-08-B1)

```python
CONTACT_PROXIMITY_THRESHOLD = 0.08      # × torso_scale — 손/발이 폴 8% 거리 이내 → 접촉
CONTACT_HOLD_MIN_FRAMES = 2             # ≥ 2 frames continuous → estimatedStable=True (9fps × 0.22s)
LOST_CONTACT_DEBOUNCE_FRAMES = 2        # ≥ 2 consecutive frames > threshold → 진짜 loss (단일 frame jitter 회피)

# Maps ContactPoint enum → COCO-17 keypoint name (or computed midpoint)
_CONTACT_POINT_TO_KEYPOINTS: dict[ContactPoint, tuple[str, ...]] = {
    "left_hand": ("left_wrist",),
    "right_hand": ("right_wrist",),
    "left_inner_thigh": ("left_hip", "left_knee"),  # midpoint of hip↔knee
    "right_inner_thigh": ("right_hip", "right_knee"),
    "left_knee": ("left_knee",),
    "right_knee": ("right_knee",),
    "left_foot": ("left_ankle",),  # foot ≈ ankle (no toe keypoint in COCO-17)
    "right_foot": ("right_ankle",),
    "left_ankle": ("left_ankle",),
    "right_ankle": ("right_ankle",),
    "hip": ("left_hip", "right_hip"),  # midpoint of hips
    "unknown": (),
}
```

### estimatedStable + lostContactAtMs detection

```python
def _detect_contact_stability(
    contact_point: ContactPoint,
    pose_frames: list[PoseFrame],
    phase_window: tuple[int, int],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
) -> tuple[bool | None, int | None, float | None, MetricConfidence]:
    """단일 contact_point × phase window 의 안정성.

    Returns:
      (estimated_stable, lost_contact_at_ms, distance_at_lost, confidence)
        - estimated_stable: contact_point keypoints 가 < threshold 로 ≥ HOLD_MIN_FRAMES 유지
        - lost_contact_at_ms: contact 시작 후 distance > threshold 가 ≥ DEBOUNCE_FRAMES 지속된 첫 시각
        - distance_at_lost: 그 시점 거리 (body-scale normalized)
        - confidence: keypoint reliability 평균 + 거리 안정성 합산 → high/medium/low
    """
    s, e = phase_window
    if e <= s:
        return (None, None, None, "low")
    keypoints = _CONTACT_POINT_TO_KEYPOINTS[contact_point]
    distances: list[float] = []
    timestamps: list[int] = []
    reliabilities: list[ReliabilityLevel] = []
    for t in range(s, e):
        frame = pose_frames[t]
        kp_dict = frame.keypoints_3d_pole_aligned
        if not all(k in kp_dict for k in keypoints):
            distances.append(float("nan"))
            timestamps.append(frame.timestamp_ms)
            reliabilities.append(frame.reliability)
            continue
        # midpoint of keypoints (single → just that point)
        pts = np.array([[kp_dict[k].x, kp_dict[k].y, kp_dict[k].z] for k in keypoints])
        midpoint = Keypoint3DAligned(x=float(np.mean(pts[:, 0])), y=float(np.mean(pts[:, 1])), z=float(np.mean(pts[:, 2])))
        d = _point_to_axis_distance(midpoint, pole_axis) / body_profile.torso_scale
        distances.append(d)
        timestamps.append(frame.timestamp_ms)
        reliabilities.append(frame.reliability)

    distances_arr = np.array(distances, dtype=float)
    contact_mask = distances_arr < CONTACT_PROXIMITY_THRESHOLD

    # estimatedStable: contact_mask 의 longest True run >= HOLD_MIN_FRAMES
    estimated_stable = _longest_consecutive_true(contact_mask) >= CONTACT_HOLD_MIN_FRAMES

    # lostContactAtMs: contact 시작 후 (first True) 다음 (False x DEBOUNCE_FRAMES) 시작 시각
    lost_at_idx = _find_first_loss(contact_mask, debounce=LOST_CONTACT_DEBOUNCE_FRAMES)
    lost_at_ms = timestamps[lost_at_idx] if lost_at_idx is not None else None
    lost_distance = float(distances_arr[lost_at_idx]) if lost_at_idx is not None else None

    # confidence: reliability 평균 가중 + NaN frame 비율
    nan_ratio = float(np.mean(np.isnan(distances_arr)))
    high_count = sum(1 for r in reliabilities if r == "high")
    low_count = sum(1 for r in reliabilities if r == "low")
    if nan_ratio > 0.3 or low_count > len(reliabilities) * 0.5:
        confidence: MetricConfidence = "low"
    elif high_count > len(reliabilities) * 0.6:
        confidence = "high"
    else:
        confidence = "medium"
    return (estimated_stable, lost_at_ms, lost_distance, confidence)
```

### Abnormal release detection (D-08-B2)

```python
def _detect_abnormal_release(
    metric: ContactStabilityMetric,
    phase_boundaries: list[PhaseBoundary],
) -> str | None:
    """lost_contact_at_ms 가 (lock_start_ms, release_estimated_ms) 안에 들면 abnormal release.

    release_estimated_ms (v1):
      explicit release phase 없으므로 hold.end 사용.
      → (lock.start, hold.end) 사이에 lostContactAtMs 있으면 abnormal.
    """
    if metric.lost_contact_at_ms is None:
        return None
    lock = next((b for b in phase_boundaries if b.phase == "lock"), None)
    hold = next((b for b in phase_boundaries if b.phase == "hold"), None)
    if lock is None or hold is None:
        return None
    # boundary.start_frame_idx → timestamp_ms via frame_idx → ms (need pose_frames[idx].timestamp_ms)
    # caller passes phase_boundaries with ms info already resolved
    lock_start_ms = lock.start_ms  # extended PhaseBoundary with ms fields
    hold_end_ms = hold.end_ms
    if lock_start_ms <= metric.lost_contact_at_ms <= hold_end_ms:
        return "abnormal_release_during_hold"
    return None
```

**(PhaseBoundary 에 `start_ms` / `end_ms` field 추가 필요 — pose_frames[idx].timestamp_ms 로 resolve. compute_phase_boundaries 가 채움.)**

### motion_id 미인식 fallback (D-08-B4)

`expected_contact_points = []` → contact_stability_metrics 가 모든 손/발 keypoint 대해 산출되나 estimated_stable=None + confidence='low' + warning='motion_unrecognized'. caller (Phase 9) 가 confidence='low' 보고 추론 강도 조정.

```python
def compute_contact_stability(
    pose_frames: list[PoseFrame],
    phase_boundaries: list[PhaseBoundary],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
    motion_id: str | None,
) -> list[ContactStabilityMetric]:
    expected = _load_expected_contact_points(motion_id)
    metrics: list[ContactStabilityMetric] = []
    if expected:
        # Normal path
        for phase in phase_boundaries:
            for cp in expected:
                stable, lost_ms, lost_dist, conf = _detect_contact_stability(
                    cp, pose_frames, (phase.start_frame_idx, phase.end_frame_idx),
                    pole_axis, body_profile,
                )
                warnings = []
                ab = _detect_abnormal_release(...)
                if ab:
                    warnings.append(ab)
                metrics.append(ContactStabilityMetric(
                    phase=phase.phase, contact_point=cp,
                    estimated_stable=stable, lost_contact_at_ms=lost_ms,
                    distance_at_lost_ms=lost_dist,
                    confidence=conf,
                    severity=_severity_from_distance(lost_dist),
                    warnings=warnings,
                ))
    else:
        # Fallback (D-08-B4)
        fallback_points: list[ContactPoint] = [
            "left_hand", "right_hand", "left_foot", "right_foot",
        ]
        for phase in phase_boundaries:
            for cp in fallback_points:
                _, lost_ms, lost_dist, conf = _detect_contact_stability(
                    cp, pose_frames, (phase.start_frame_idx, phase.end_frame_idx),
                    pole_axis, body_profile,
                )
                metrics.append(ContactStabilityMetric(
                    phase=phase.phase, contact_point=cp,
                    estimated_stable=None,  # null — motion 미인식
                    lost_contact_at_ms=lost_ms,
                    distance_at_lost_ms=lost_dist,
                    confidence="low",
                    severity="low",
                    warnings=["motion_unrecognized"],
                ))
    return metrics
```

### severity (researcher 초안)

| Metric | low | medium | high | Source |
|---|---|---|---|---|
| `distance_at_lost_ms` (body-scale) | < 0.10 | 0.10 ~ 0.20 | > 0.20 | proximity threshold 0.08 × 2~3 — 진짜 풀림 / 잠깐 떠 있음 / 멀리 떠남 |
| `estimated_stable=False` & `lost_at_ms in (lock, hold)` | — | — | high + warning='abnormal_release' | D-08-B2 비정상 풀림 |

## Confidence + Smoothing 박제 (D-08-U1, D-08-U2)

### Pipeline order

```
1. Extract angles (T, J=8) from pose_frames (features.compute_joint_angles)
2. Extract uncertainty (T, J=8) (features.joint_uncertainty)
3. angles_filled = temporal.temporal_fill(angles, uncertainty)   ← D-08-U1
4. Compute metrics from angles_filled + pose_frames (keypoints for distance/tilt)
5. confidence = weighted aggregation:
     frame_reliability_weight[t] = 1.0 if reliability='high'
                                   0.7 if reliability='medium'
                                   0.3 if reliability='low'
6. emit warning if > X% of frames in a phase are 'low' reliability
```

### Frame-level reliability weighting

```python
RELIABILITY_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.3}
LOW_RELIABILITY_PHASE_THRESHOLD = 0.4  # 40% — emit warning

def _weighted_aggregate(
    values: np.ndarray,         # (T,) raw metric per frame
    reliabilities: list[ReliabilityLevel],
    *,
    method: Literal["mean", "median"] = "median",
) -> tuple[float, list[str]]:
    """robust aggregation + warning emission."""
    weights = np.array([RELIABILITY_WEIGHT[r] for r in reliabilities])
    warnings: list[str] = []
    low_ratio = float(np.mean([r == "low" for r in reliabilities]))
    if low_ratio > LOW_RELIABILITY_PHASE_THRESHOLD:
        warnings.append("occlusion_high_in_phase")

    finite = np.isfinite(values)
    if not finite.any():
        return (0.0, warnings + ["all_frames_unreliable"])

    if method == "median":
        # weighted median: sort by value, find cumulative weight crossing 0.5*total
        v = values[finite]
        w = weights[finite]
        order = np.argsort(v)
        cum = np.cumsum(w[order])
        target = cum[-1] / 2.0
        median = float(v[order][np.searchsorted(cum, target)])
        return (median, warnings)
    else:
        return (float(np.average(values[finite], weights=weights[finite])), warnings)
```

**Per-metric aggregation choice (researcher 초안):**

| Metric field | Aggregation | rationale |
|---|---|---|
| `pelvis_distance_from_pole_axis` | weighted median (per-phase frames) | robust to single-frame jumps |
| `chest_distance_from_pole_axis` | weighted median | same |
| `shoulder_tilt` / `hip_tilt` | weighted median | tilt jumps from occlusion noise — median absorbs |
| `jitter_score` | inter-frame median (이미 dimensions.stability_wobble) | dimensions.py 박제 정합 |
| `jerk_score` | MAD-filtered median (위 산식) | self-robust |
| `hold_stability_score` | stability_wobble on hold window | dimensions.py 정합 |
| `contact.distance_at_lost_ms` | single value (이벤트 시점) | aggregation X |

### overall_confidence (per ForceSignalsReport)

```python
def _overall_confidence(
    phase_boundaries: list[PhaseBoundary],
    axis: list[AxisDeviationMetric],
    stability: list[StabilityMetric],
    contact: list[ContactStabilityMetric],
) -> MetricConfidence:
    """min of (phase boundary layer agreement) + (metric confidence aggregates).

    high: 모든 phase boundary 'high' + 모든 metric confidence 'high'
    medium: 위 두 조건 중 하나라도 'medium' (low 없음)
    low: 하나라도 'low'
    """
    confidences = [b.confidence for b in phase_boundaries]
    confidences.extend(m.confidence for m in axis)
    confidences.extend(m.confidence for m in stability)
    confidences.extend(m.confidence for m in contact)
    if "low" in confidences:
        return "low"
    if "medium" in confidences:
        return "medium"
    return "high"
```

## Module Structure + Pipeline Wiring + Firestore Schema

### Public API signatures (D-08-C3, D-08-C4)

```python
# backend/shared/python/sunity_shared/analysis/force_signals.py

def compute_force_signals(
    pose_frames: list[PoseFrame],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
    *,
    angles: np.ndarray | None = None,         # 이미 추출된 (T, J=8) — 없으면 내부 추출
    motion_id: str | None = None,
    gemini_extractor: "GeminiMomentExtractor | None" = None,
    video_uri: str | None = None,             # 로컬 path (Layer 2 enable 시 필수)
    fps: float = 9.0,
) -> ForceSignalsReport:
    """Phase 8 통합 헬퍼. pipeline/app.py::_process 가 1줄로 호출."""

def compute_phase_boundaries(
    pose_frames: list[PoseFrame],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
    angles: np.ndarray,
    *,
    motion_id: str | None = None,
    gemini_extractor: "GeminiMomentExtractor | None" = None,
    video_uri: str | None = None,
    fps: float = 9.0,
) -> list[PhaseBoundary]:
    """Layer 1 + (옵션) Layer 2 결합 5-phase boundary 산출."""

def compute_axis_deviation(
    pose_frames: list[PoseFrame],
    phase_boundaries: list[PhaseBoundary],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
) -> list[AxisDeviationMetric]:
    """Per-phase pelvis/chest distance + shoulder/hip tilt + direction + severity."""

def compute_stability_metrics(
    angles: np.ndarray,
    phase_boundaries: list[PhaseBoundary],
    pose_frames: list[PoseFrame],
) -> list[StabilityMetric]:
    """Per-phase jitter (dimensions reuse) + jerk (신설) + hold (dimensions reuse) + unstable parts."""

def compute_contact_stability(
    pose_frames: list[PoseFrame],
    phase_boundaries: list[PhaseBoundary],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
    motion_id: str | None,
) -> list[ContactStabilityMetric]:
    """Per-phase × per-contact-point proximity + debounce + abnormal release."""
```

### Pipeline wiring (backend/functions/pipeline/app.py)

```python
# pipeline/app.py — _process 안에서 compare_body_profiles 호출 직후 (line ~807 또는 1000 부근)

from sunity_shared.analysis import force_signals as fs
from sunity_shared.judging.gemini_moment_extractor import GeminiMomentExtractor

# Singleton (module-level, lazy)
_GEMINI_MOMENT_EXTRACTOR: GeminiMomentExtractor | None = None

def _get_gemini_moment_extractor() -> GeminiMomentExtractor | None:
    """RECOGNIZER_BACKEND='gemini' 시만 활성."""
    global _GEMINI_MOMENT_EXTRACTOR
    if os.environ.get("RECOGNIZER_BACKEND", "fallback") != "gemini":
        return None
    if _GEMINI_MOMENT_EXTRACTOR is None:
        _GEMINI_MOMENT_EXTRACTOR = GeminiMomentExtractor()
    return _GEMINI_MOMENT_EXTRACTOR

# _process 안:
# ... compare_body_profiles 호출 끝난 직후 ...
force_signals_report = fs.compute_force_signals(
    pose_frames=inputs.pose_frames,
    pole_axis=inputs.pole_axis,
    body_profile=student_profile,
    angles=angles,
    motion_id=getattr(profile, "motion_id", None),
    gemini_extractor=_get_gemini_moment_extractor(),
    video_uri=inputs.local_video_path,   # _extract_video_analysis_inputs 가 박제 (keep_local_video=True 필요)
    fps=9.0,
)

# Firestore 저장 — Phase 6 박제 path 그대로
force_signals_dict = _dataclass_to_camel_case_dict(force_signals_report)

firestore_admin.complete_analysis(
    uid, analysis_id, result,
    angles=...,
    body_comparison_report=body_comparison_report_dict,
    body_normalization_profile=body_normalization_profile_dict,
    force_signals_report=force_signals_dict,    # ← NEW
)
```

**`_extract_video_analysis_inputs` 변경 필요:** `keep_local_video=False` default → Phase 8 Layer 2 wiring 시 `True` 박제 (Gemini File API local path 제약). 기존 caller (Phase 6) 무영향.

### firestore_admin.complete_analysis 확장

```python
def complete_analysis(
    uid: str,
    analysis_id: str,
    result: dict,
    *,
    angles: list | None = None,
    angles_joint_keys: list | None = None,
    angles_frames: int | None = None,
    body_comparison_report: dict | None = None,
    body_normalization_profile: dict | None = None,
    force_signals_report: dict | None = None,   # ← NEW (Phase 8)
) -> None:
    """... 기존 doc ..."""
    payload: dict = { ... }  # 기존
    if force_signals_report is not None:
        _validate_flat_dict_no_nested_array(
            force_signals_report, path="forceSignalsReport"
        )
        payload["result"]["forceSignalsReport"] = force_signals_report
    _doc(...).set(payload, merge=True)
```

### Firestore document shape (D-08-U3, [[firestore-nested-array-flat]])

```
users/{uid}/analyses/{id}.result.forceSignalsReport: {
  version: "1.0",
  overallConfidence: "high" | "medium" | "low",
  warnings: [string],                                     # list[str] OK
  phaseBoundaries: [                                      # list[dict-of-scalars-only] OK
    {
      phase: "entry",
      startFrameIdx: 0, endFrameIdx: 5,
      startMs: 0, endMs: 555,
      confidence: "high",
      source: "gemini_assisted"
    },
    ...
  ],
  axisMetrics: [
    {
      phase: "lock",
      pelvisDistanceFromPoleAxis: 0.12,
      chestDistanceFromPoleAxis: 0.18,
      shoulderTilt: 8.3, hipTilt: -2.1,
      deviationDirection: "outward",
      severity: "low", confidence: "high",
      warnings: []                                       # list[str] OK at this level
    },
    ...
  ],
  stabilityMetrics: [
    {
      phase: "hold",
      jitterScore: 7.2, jerkScore: 3.5,
      holdStabilityScore: 6.8,
      unstableBodyParts: ["right_shoulder"],             # list[str] OK
      severity: "low", confidence: "high",
      warnings: []
    },
    ...
  ],
  contactMetrics: [
    {
      phase: "hold",
      contactPoint: "left_hand",
      estimatedStable: true,
      lostContactAtMs: null,
      distanceAtLostMs: null,
      confidence: "high",
      severity: "low",
      warnings: []
    },
    ...
  ]
}
```

**Validation:** `_validate_flat_dict_no_nested_array(force_signals_report, path='forceSignalsReport')` 통과. list[dict-of-scalars-only] 패턴은 `_validate_dict_only_scalars` 통과 — 단 `warnings: list[str]` 가 list-of-dict 안에 있으면 `_validate_dict_only_scalars` 가 TypeError. **해결:** dict 안 `warnings` field 는 sibling 으로 옮기지 말고, `_validate_dict_only_scalars` 의 명세 갱신 — `list[str]` 도 허용 추가. **또는** warnings 를 dict 안에서 빼고 metric 별 단일 string code 로 단순화.

**연결:** `_validate_dict_only_scalars` 의 현재 명세 (`backend/shared/python/sunity_shared/firestore_admin.py:104-123`): "list[dict] 의 dict 원소 안에서는 nested list / nested dict 금지". Phase 8 metric 안 warnings 가 list[str] 라 위반. **Plan 8 단계에서 결정 필요 (planner 영역):**

- Option A: `_validate_dict_only_scalars` 명세 확장 — `list[str]` 도 허용 (recursive validator)
- Option B: metric 안 warnings 제거, 단일 `warning_code: str | None` 박제 (단순)
- Option C: metric 안 warnings 를 string concat ("|" 구분) 으로 단일 string

**[ASSUMED]** Option A 권장 (UX 정합 — 여러 warning 동시 가능). planner 가 firestore_admin 명세 확장 단일 commit 박제.

## 3-Way Contract Additions (D-08-U3)

### TS additions (`app/src/types/analysis.ts`)

```typescript
// ── Phase 8 Force Signals (FORCE-01 신호 layer) ──────────────────────────

export type MotionPhase = 'entry' | 'lock' | 'transition' | 'final_shape' | 'hold';

export type DeviationDirection =
  | 'up' | 'down' | 'left' | 'right'
  | 'outward' | 'inward' | 'unknown';

export type SeverityLevel = 'low' | 'medium' | 'high';
export type MetricConfidence = 'low' | 'medium' | 'high';

export type ContactPoint =
  | 'left_hand' | 'right_hand'
  | 'left_inner_thigh' | 'right_inner_thigh'
  | 'left_knee' | 'right_knee'
  | 'left_foot' | 'right_foot'
  | 'left_ankle' | 'right_ankle'
  | 'hip' | 'unknown';

export interface PhaseBoundary {
  phase: MotionPhase;
  startFrameIdx: number;
  endFrameIdx: number;
  startMs: number;
  endMs: number;
  confidence: MetricConfidence;
  source: 'heuristic' | 'gemini_assisted' | 'heuristic_fallback';
}

export interface AxisDeviationMetric {
  phase: MotionPhase;
  pelvisDistanceFromPoleAxis: number;   // body-scale normalized
  chestDistanceFromPoleAxis: number;
  shoulderTilt: number;                 // degrees signed
  hipTilt: number;
  deviationDirection: DeviationDirection;
  severity: SeverityLevel;
  confidence: MetricConfidence;
  warnings: string[];
}

export interface StabilityMetric {
  phase: MotionPhase;
  jitterScore: number;                  // raw wobble (deg)
  jerkScore: number;                    // 3rd derivative MAD-filtered median (deg/frame^3)
  holdStabilityScore: number | null;    // null when phase != hold
  unstableBodyParts: string[];          // joint keys (English) — Phase 11 maps to Korean
  severity: SeverityLevel;
  confidence: MetricConfidence;
  warnings: string[];
}

export interface ContactStabilityMetric {
  phase: MotionPhase;
  contactPoint: ContactPoint;
  estimatedStable: boolean | null;      // null when motion_id unrecognized
  lostContactAtMs: number | null;
  distanceAtLostMs: number | null;
  severity: SeverityLevel;
  confidence: MetricConfidence;
  warnings: string[];
}

export interface ForceSignalsReport {
  version: string;                      // '1.0'
  overallConfidence: MetricConfidence;
  warnings: string[];
  phaseBoundaries: PhaseBoundary[];
  axisMetrics: AxisDeviationMetric[];
  stabilityMetrics: StabilityMetric[];
  contactMetrics: ContactStabilityMetric[];
}

// Extend AnalysisResult:
export interface AnalysisResult {
  // ... 기존 ...
  forceSignalsReport?: ForceSignalsReport | null;   // Phase 8 (Plan 08-01) — nullable for backward-compat
}
```

### Python re-export (`backend/shared/python/sunity_shared/models.py`)

```python
# Append (Phase 6/7 패턴):
from .analysis.force_signals import (
    MotionPhase,
    DeviationDirection,
    SeverityLevel,
    MetricConfidence,
    ContactPoint,
    PhaseBoundary,
    AxisDeviationMetric,
    StabilityMetric,
    ContactStabilityMetric,
    ForceSignalsReport,
)
```

### docs/contract.md addition

신설 `## §9. ForceSignalsReport (Plan 08-01 신설 — FORCE-01 신호 layer)` — Phase 6/7 의 §8 / §8.3 패턴 정합. 본 RESEARCH 의 schema + warning enum + ContactPoint enum + MotionPhase enum 박제.

### Frontend normalize (`app/src/lib/userAnalyses.ts`)

```typescript
// normalize() 안에 신설:
const result: AnalysisResult | undefined = raw.result
  ? {
      ...,
      forceSignalsReport: raw.result.forceSignalsReport ?? null,
    }
  : undefined;
```

Phase 7 의 WR-02 retract B1 패턴 (immutable spread + null-guard) 정합. TS interface non-optional `forceSignalsReport: ForceSignalsReport | null` — normalize() 가 compat layer.

## Test + Sweep Strategy

### Unit tests (Phase 6/7 패턴 정합)

**Drift defense:**
```python
def test_jitter_score_uses_dimensions_helper():
    """force_signals.compute_stability_metrics 의 jitter_score 가
    dimensions.stability_wobble (또는 stability_score 의 raw 산식) 과 동일.

    Phase 12.5 v4 Codex HIGH-2 패턴: 동일 input → 동일 output assert.
    drift 차단."""
    angles = np.random.default_rng(0).normal(120, 5, size=(50, 8))
    from sunity_shared.analysis import dimensions, force_signals
    direct = dimensions.stability_wobble(angles, profile=None)
    metrics = force_signals.compute_stability_metrics(
        angles, [PhaseBoundary("hold", 0, 50, ...)], pose_frames=[]
    )
    assert abs(metrics[0].jitter_score - direct) < 1e-6
```

**Layer 1 / Layer 2 agreement:**
```python
def test_layer1_layer2_agreement_high_confidence():
    """Layer 1 + Layer 2 timestamp 차이 <= 2 frames → confidence='high'."""
    ...

def test_layer1_layer2_disagreement_low_confidence():
    """timestamp 차이 > 5 frames → confidence='low' + warning='layer_disagreement_major'."""
    ...

def test_layer2_unavailable_falls_back_to_layer1():
    """gemini_extractor=None → Layer 1 단독, confidence='medium'."""
    ...
```

**Edge cases:**
```python
def test_motion_id_unrecognized_returns_estimated_stable_null():
def test_video_too_short_falls_back_to_single_hold_phase():
def test_heavy_occlusion_emits_warning_and_low_confidence():
def test_temporal_fill_applied_before_metrics():
def test_layer2_invoked_only_when_local_path():
def test_layer2_invoked_only_when_motion_id_not_none():
```

**Schema lockstep (Phase 6 W5):**
```python
def test_force_signals_dict_passes_validate_flat_dict_no_nested_array():
def test_force_signals_dict_camel_case_round_trip():
def test_unstable_body_parts_is_list_of_str_not_dict():
```

**Grep gates (canned warning 코드):**
```python
def test_warning_codes_use_snake_case_no_korean():
def test_no_emoji_in_warning_strings():
```

### Integration tests (1 fixture E2E)

```python
def test_compute_force_signals_e2e_clean_invert():
    """합성 PoseFrame list (T=60, J=17, hold phase 분명) → ForceSignalsReport.

    Assertions:
      - len(phase_boundaries) == 5 (모든 phase 존재)
      - axis_metrics[hold].severity == 'low' (정은지급 fixture)
      - stability_metrics[hold].jitterScore < 8
      - contact_metrics[hold].estimated_stable == True
      - overall_confidence == 'medium' (Layer 2 없으므로)
    """
```

### Sweep validation (D-08-D3, sanity check only)

```bash
# belle Pod 실행 (researcher 박제 직후, threshold lock 전):
python3 -m backend.research.spikes.sweep_force_signals \
  --inputs sweep_rtmw_20260603_1409 \
  --reference-motion ref-invert ref-foxtop ref-foxtop-split ref-climb ref-sideway-spin \
  --out backend/research/spikes/reports/force_signals_sweep_<UTC>.json

# 기대 결과 (sanity check):
# - 정은지 reference 5영상 모두: axis severity 90%+ 'low', stability severity 90%+ 'low'
# - phase boundaries: 5개 모두 detect (entry 가 length=0 경우 OK + warning)
# - jerk_score: 정은지 영상 평균 < 5 (high 임계 15 의 1/3)
```

**Sweep 실패 시 (분포가 정은지 = high) — researcher 가 threshold 1차 조정 후 재실행. 임계 자체는 도메인 fixed (D-08-D2/D4) — sweep 으로는 fixed 임계의 sanity 만 확인, 정은지 분포로 threshold 자동 derive X.**

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + numpy (Python stdlib) |
| Config file | `backend/pyproject.toml` (만약 신설 — 현재는 backend/tests/ 직접 박제 + `PYTHONPATH=backend/shared/python:.`) |
| Quick run command | `PYTHONPATH=backend/shared/python:. backend/.venv/bin/python3 -m pytest backend/tests/phase08/ -x` |
| Full suite command | `PYTHONPATH=backend/shared/python:. backend/.venv/bin/python3 -m pytest backend/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| FORCE-01 (success #1) | `AxisDeviationMetric`(골반/흉곽 폴축 거리, 어깨/골반 tilt, deviation 방향, severity) 가 phase 별로 산출 | unit | `pytest backend/tests/phase08/test_compute_axis_deviation.py -x` | ❌ Wave 0 |
| FORCE-01 (success #2) | `StabilityMetric`(jitterScore, jerkScore, holdStabilityScore, unstableBodyParts) 가 phase 별로 산출 | unit | `pytest backend/tests/phase08/test_compute_stability_metrics.py -x` | ❌ Wave 0 |
| FORCE-01 (success #3) | `ContactStabilityMetric`(접촉점별 estimatedStable, lostContactAtMs, confidence) 가 phase 별로 산출 | unit | `pytest backend/tests/phase08/test_compute_contact_stability.py -x` | ❌ Wave 0 |
| FORCE-01 (success #4) | 모든 신호에 시간적 스무딩 적용 + 가림 프레임 confidence 가중 | integration | `pytest backend/tests/phase08/test_compute_force_signals.py::test_temporal_fill_and_confidence_weighting -x` | ❌ Wave 0 |
| FORCE-01 (5-phase split) | 5단계 phase boundary 산출 (entry/lock/transition/final_shape/hold) | unit | `pytest backend/tests/phase08/test_compute_phase_boundaries.py -x` | ❌ Wave 0 |
| FORCE-01 (Layer 1/2 hybrid) | Layer 1 단독 = confidence='medium', Layer 1+2 일치 = 'high', 불일치 = 'low' + warning | unit (with mock Gemini) | `pytest backend/tests/phase08/test_compute_phase_boundaries.py::test_layer1_layer2_agreement -x` | ❌ Wave 0 |
| FORCE-01 (motion 미인식 fallback) | `expected_contact_points=[]` + estimatedStable=null + warning | unit | `pytest backend/tests/phase08/test_compute_contact_stability.py::test_motion_unrecognized_fallback -x` | ❌ Wave 0 |
| FORCE-01 (3-way lockstep) | TS / Python / contract.md schema 일치 | integration | `pytest backend/tests/phase08/test_firestore_lockstep.py -x` + `cd app && npx tsc --noEmit` | ❌ Wave 0 |
| FORCE-01 (nested-array 회피) | force_signals_report dict 가 `_validate_flat_dict_no_nested_array` 통과 | unit | `pytest backend/tests/phase08/test_firestore_lockstep.py::test_validator_passes -x` | ❌ Wave 0 |
| FORCE-01 (drift defense) | force_signals.jitter == dimensions.stability_wobble (동일 input → 동일 output) | unit | `pytest backend/tests/phase08/test_compute_stability_metrics.py::test_drift_defense -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `PYTHONPATH=backend/shared/python:. backend/.venv/bin/python3 -m pytest backend/tests/phase08/ -x`
- **Per wave merge:** `PYTHONPATH=backend/shared/python:. backend/.venv/bin/python3 -m pytest backend/tests/ -x` (regression: phase06 / phase07 / pipeline 0 회귀)
- **Phase gate:** Full suite green + `tsc --noEmit clean` + `sam validate exit 0` + 5영상 sweep sanity check pass

### Wave 0 Gaps

- [ ] `backend/tests/phase08/__init__.py` — 신설 (Phase 6/7 패턴)
- [ ] `backend/tests/phase08/conftest.py` — 합성 PoseFrame factory + GeminiMomentExtractor mock fixture
- [ ] `backend/tests/phase08/fixtures/_factory.py` — synthetic motion 영상 생성 (T=60, J=17)
- [ ] `backend/tests/phase08/fixtures/fixture_clean_invert.json` — 정은지급 깔끔한 invert
- [ ] `backend/tests/phase08/fixtures/fixture_pelvis_drop.json` — pelvis 가 hold 중 outward 이동
- [ ] `backend/tests/phase08/fixtures/fixture_occluded_lock.json` — lock phase frame 의 reliability='low' 60%
- [ ] `backend/tests/phase08/fixtures/fixture_motion_id_unrecognized.json` — motion_id=None fallback
- [ ] `backend/tests/phase08/fixtures/fixture_jerk_high.json` — transition phase jerk > 15
- [ ] `backend/tests/phase08/test_compute_phase_boundaries.py` — Layer 1 + Layer 2 mock + agreement
- [ ] `backend/tests/phase08/test_compute_axis_deviation.py`
- [ ] `backend/tests/phase08/test_compute_stability_metrics.py` — drift defense 포함
- [ ] `backend/tests/phase08/test_compute_contact_stability.py` — yaml load + debounce + abnormal release
- [ ] `backend/tests/phase08/test_compute_force_signals.py` — umbrella E2E
- [ ] `backend/tests/phase08/test_firestore_lockstep.py` — schema + camelCase + validator + tsc

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 본 phase = 분석 코어 layer, 기존 Lambda auth (Firebase ID token) 통과 후 호출됨 |
| V3 Session Management | no | Firestore client + Lambda session (기존 박제) |
| V4 Access Control | no | Firestore Admin SDK (기존 박제) — body_normalization_profile 패턴 정합 |
| V5 Input Validation | **yes** | `_validate_flat_dict_no_nested_array` + `_validate_dict_only_scalars` (W5) — force_signals_report dict 검증 |
| V6 Cryptography | **yes** | Gemini API 키 = Parameter Store SecureString (Plan 01-13 박제, 변경 0). `.env` 하드코딩 금지 |
| V8 Data Protection | yes | Firestore `forceSignalsReport` 는 user analyses 격리 (기존 보안 규칙). 신규 PII 없음 (관절 좌표만, 얼굴 좌표 보존되나 Phase 1 박제 시 keypoint_3d 만 저장) |
| V11 Business Logic | yes | severity 임계 = 도메인 룰 fixed (D-08-D2/D3/D4) — 사용자 영향 받지 않음 |
| V12 Files / Resources | yes | `contact_points.yaml` = 정적 파일 (gitignore X, repo 박제). yaml.safe_load 사용 — `yaml.load` 금지 |
| V14 Configuration | yes | RECOGNIZER_BACKEND=gemini env flag (기존 박제). 본 phase 박제 영향 없음 |

### Known Threat Patterns for backend-Python-Lambda + Gemini adapter

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Gemini 응답이 좌표/점수/심사 판단 포함 | Spoofing (사람 점수 ground truth 위변조) | 정규식 가드 3 카테고리 (Plan 01-13 박제) — `_enforce_no_coordinate_or_score` 자동 발동 |
| Gemini API 키 leak (env / log / Firestore) | Information disclosure | Parameter Store SecureString + `log.debug` 만 (key 본문 0) + `.env` 하드코딩 금지 (CLAUDE.md §3) |
| YAML deserialization RCE | Tampering | `yaml.safe_load` 강제, `yaml.load` 금지 |
| Firestore nested-array DoS (직렬화 오류) | Denial of service | `_validate_flat_dict_no_nested_array` + `_validate_dict_only_scalars` (W5) |
| Layer 2 무응답 / 타임아웃 | Denial of service | Plan 01-13 박제: 120s max wait (FILE_API processing) + `RuntimeError` 박제 + caller (pipeline) 가 catch 시 Layer 1 단독 fallback |
| 사용자 영상 PII leak via warnings field | Information disclosure | warnings = canned snake_case code 만 (영어, 한국어 카피 X, 사용자 정보 X) |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 단일 hold-window measurement (Phase 6/7) | 5-phase split (entry/lock/transition/final_shape/hold) | Phase 8 (본 phase) | force-pattern 추론용 시간 정보 박제, "잡는 순간 흘러내림 vs 버틸 때만" 구분 가능 |
| per-motion phase 분할 yaml | motion-agnostic Layer 1 heuristic + (옵션) Gemini Layer 2 | belle 2026-06-08 결정 (D-08-A3) | 새 동작군 박제 부담 0, 미인식 영상도 분석 가능 |
| 정은지 영상 분포 기반 severity threshold | 도메인 룰 fixed threshold (research 02 + IPSF + 폴스포츠-지식.md) | belle 2026-06-08 결정 (D-08-D2/D3/D4) | reference 영상 추가/교체 무관 임계 영구 박제 |
| Gemini 가 좌표/점수 출력 시도 (Plan 01-13 IPSF 비교 chain) | Gemini = key_moment timestamp 만 (좌표/점수/판단 정규식 차단) | Plan 01-13 박제 | Phase 8 의 Layer 2 = timestamp 만 사용 — measurement_unreliable_blocked verdict 와 분리 |
| custom occlusion smoother | `temporal.temporal_fill` (Phase 1 박제) | Phase 1 박제 | NLF/RTMW uncertainty + MAD outlier + 신뢰도 가중 이동평균 통합. Phase 8 재사용 |
| `kismam.score_from_deviation` 변환만 (raw 산식 없음) | `stability_wobble()` raw helper 신설 (Option A) | Phase 8 (본 phase, dimensions.py 확장) | force_signals.py 가 0~100 점수 변환 없이 raw wobble 직접 사용 가능 |

**Deprecated/outdated:**

- Plan 01-13 의 NLF baseline 갭 (D-14 ≤5) — Plan 15 (commit 861fb3a) 에서 영구 폐기. Phase 8 도 NLF 호출 0.
- `dimensions.balance_score` (좌우 대칭) — 2026-05-29 박제 제거. Phase 8 도 좌우 대칭 자체는 metric 출력만 (감점 X).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Layer 1 heuristic thresholds (ground_y_relative * 0.85, hand_pole_dist_lock 0.15, velocity_mid 0.03, velocity_high 0.06) | 5-Phase Layer 1 Heuristic | 5단계 분할 정확도 떨어짐 → confidence='medium' (D-08-A4 정합). belle Pod sweep sanity check 권장 |
| A2 | Tilt severity thresholds (shoulder/hip 10°/25°) | AxisDeviation severity | IPSF Code of Points 가 명시적 tolerance 정의하는지 NotebookLM lookup 권장. 없으면 motion-analysis literature default 차용 |
| A3 | Pelvis distance severity (0.15 / 0.30 body-scale) | AxisDeviation severity | research 02 §4.2 의 "30% 이상" 박제와 일관 — 검증 권장 |
| A4 | Jerk severity (5 / 15 deg/frame^3) | StabilityMetric severity | motion-analysis 표준값 없음 — 정은지 5영상 jerk 분포 측정 권장 |
| A5 | Unstable body part threshold (12.0 degrees wobble) | StabilityMetric unstable_body_parts | `_STABILITY_TOL_DEG=15` 정합 (12 = 15 의 80% — high 임계 진입 전 cutoff) |
| A6 | Contact proximity threshold (0.08 × torso_scale) | ContactStability proximity | 손이 폴 직접 잡는 자세에서 안정값 — 정은지 영상 측정 권장 |
| A7 | Hold min frames (2 frames @ 9fps = ~220ms) | ContactStability debounce | fps 변경 시 재계산 필요 (9fps 박제 정합) |
| A8 | expected_contact_points yaml 매핑 (인버트/후굴/숄더마운트/기본 포징) | ContactStability yaml | belle/강사 도메인 검수 필수 — researcher 초안 |
| A9 | Layer 2 confidence threshold (2 / 5 frames) | Layer 2 Gemini agreement | Plan 01-13 박제 belle Pod 영상에서 검증 필요 |
| A10 | `_validate_dict_only_scalars` 명세 확장 (list[str] 허용) | Firestore schema validator | Option A 권장 — planner 가 firestore_admin 단일 commit 박제 결정. Option B/C 도 viable |
| A11 | Plan 01-13 의 measurement_unreliable_blocked verdict 가 Phase 8 timestamp use case 와 분리됨 | Layer 2 Gemini 박제 | Plan 01-13 SUMMARY §"belle Pod live mode 결과" §"Measurement unreliability 박제 (3 증거)" 의 정확한 의미 — 좌표 chain 의심이지 timestamp 자체 의심 아님. spike 진입 시 검증 |

**모든 [ASSUMED] 박제는 belle 검수 권장.** belle Pod 5영상 sweep 으로 threshold sanity check 후 lock.

## Open Questions

1. **`_validate_dict_only_scalars` 명세 확장 (Option A vs B vs C)**
   - What we know: 현재 명세는 list[dict] 의 dict 안에서 nested 모두 금지 (firestore_admin.py:104-123). Phase 8 metric 안 `warnings: list[str]` 가 위반.
   - What's unclear: 명세 확장 (list[str] 허용) 이 firestore-nested-array 정합인지 — Firestore SDK 가 list-of-string 은 직렬화 가능.
   - Recommendation: **Option A** (명세 확장, list[str] 허용). planner 가 firestore_admin 단일 commit 박제. Phase 6 의 BodyComparisonReport.warnings list[str] 와 일관성.

2. **`_extract_video_analysis_inputs` 의 `keep_local_video` default 변경**
   - What we know: 현재 default=False (Phase 6 박제). Phase 8 Layer 2 wiring 시 True 필요.
   - What's unclear: default 변경 시 기존 Phase 6 path 메모리/디스크 누수 위험.
   - Recommendation: default=False 유지 + Phase 8 호출 site 에서 명시적 `keep_local_video=True` + try/finally 정리. pipeline/app.py 의 기존 `Path(local_video_path).unlink(missing_ok=True)` 패턴 정합.

3. **Layer 2 호출 비용 vs Phase 5 cache 활용**
   - What we know: `GeminiMomentExtractor._cache` 가 `(video_uri, motion, model)` 키로 응답 보관. Phase 5 (TechniqueRecognizer) 가 같은 영상 호출했으면 cache hit.
   - What's unclear: Phase 5 와 Phase 8 의 motion 인자가 같은지 — Phase 5 가 `recognize()` 시 그 영상의 motion_id 를 인자로 호출하면 Phase 8 도 same motion_id 사용 → cache hit. 그러나 GeminiTechniqueRecognizer 의 호출 시그너처는 다른 path 일 수 있음.
   - Recommendation: Phase 8 의 Layer 2 = `extract_key_moments(video_uri=local_path, motion=motion_id)` 호출. Phase 5 가 다른 method (`recognize_technique`) 호출이라면 cache miss → 별 Gemini 호출 1회. cost = $0.02~0.05/영상 (belle 예상 박제). planner 가 비용/latency 영향 박제 시 검토.

4. **`PoseFrame.timestamp_ms` 의 정확한 의미 (frame_index × (1000/fps) vs 실제 video timestamp)**
   - What we know: Phase 1 박제 — `timestamp_ms: int` field 가 PoseFrame 에 있음.
   - What's unclear: frame extractor 가 timestamp_ms 를 정확한 영상 시각으로 박제하는지 (vs index × 111ms @ 9fps 근사).
   - Recommendation: planner 가 `frame_extractor.py` 박제 정신 확인 — Phase 8 의 ContactStability.lostContactAtMs 는 frame index × (1000/fps) 로 충분 (정밀도 < 100ms).

5. **Plan 01-13 verdict 직접 검증 — Layer 2 spike**
   - What we know: Plan 01-13 의 5/5 minimum_fail 는 IPSF criteria 비교 (measure_moment_angles → score_moment) 의 의심.
   - What's unclear: Phase 8 의 Layer 2 = timestamp 만 사용 — 측정 chain 무관. 그러나 belle Pod 실 테스트 없이 단정 X.
   - Recommendation: Phase 8 plan 단계에서 **별 Layer 2 spike** 신설 (선택) — ref-invert 영상 1개로 Gemini key_moment timestamp 가 정은지 영상에서 sensible 한지 belle Pod 검증. spike 통과 시 v1 wiring, 실패 시 Layer 1 단독 (D-08-A2 confidence='medium' fallback 그대로). v1.5 후속 plan 으로 본격화.

6. **5단계 분할 의 belle 검증 set (timestamp 라벨링)**
   - What we know: motion boundary timestamp 는 **객관적 video event** ([[analysis-objectivity-no-human-scores]] 와 별개 — "어디서 손이 폴에 닿는지" 는 점수 라벨 아님).
   - What's unclear: belle 가 5영상 × 5단계 = 25 timestamp 라벨 박제 가능한지.
   - Recommendation: planner 가 belle Pod sweep 단계에서 25 timestamp belle 검증 박제 — Layer 1 휴리스틱 정확도 sanity check (>= 80% 정합 보면 통과).

7. **`hip` ContactPoint (research §5.3 enum) 의 COCO-17 매핑**
   - What we know: research 02 §5.3 의 12 ContactPoint enum 안 `hip` 단독.
   - What's unclear: COCO-17 에는 `hip` 단일 keypoint 없음 (left_hip + right_hip).
   - Recommendation: 본 RESEARCH `_CONTACT_POINT_TO_KEYPOINTS` 박제 — `hip` → `("left_hip", "right_hip")` midpoint 사용. planner 가 yaml 매핑 시 belle 검수.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| numpy | force_signals.py 산술 | ✓ | >=1.26,<2.0 (기존) | — |
| PyYAML (yaml) | contact_points.yaml load | ✓ | judging/loader.py 박제 — 6.x | — |
| pytest | 단위 test | ✓ | 8.x | — |
| `temporal.temporal_fill` | D-08-U1 가림 보간 | ✓ | 내부 박제 (Phase 1) | — |
| `dimensions.stability_score` / `_select_window` | D-08-C1 재사용 | ✓ | 내부 박제 (Phase 12.5 v4) | — |
| `body_normalization.BodyNormalizationProfile` | D-08-D1 거리 정규화 | ✓ | 내부 박제 (Phase 2) | — |
| `gemini_moment_extractor.GeminiMomentExtractor` | D-08-A2 Layer 2 | ✓ | 내부 박제 (Plan 01-13) | Layer 1 단독 (D-08-A4) |
| Gemini API 키 (Parameter Store `/sunity/motion/gemini-api-key`) | Layer 2 호출 | ✓ | 박제 (Plan 01-13) | RECOGNIZER_BACKEND != 'gemini' 시 fallback |
| google-genai SDK | Layer 2 호출 | RunPod Pod ✓ | 박제 (Plan 01-13 함정 3) | local dev — Layer 2 mock |
| RECOGNIZER_BACKEND=gemini env | Layer 2 wiring 조건 | RunPod Pod ✓ | 박제 (Phase 5 D-13 commit) | Layer 1 단독 |

**Missing dependencies with fallback:** Layer 2 의 모든 의존성은 fallback 가능 (Layer 1 단독 → confidence='medium' + warning). 분석 죽지 않음 (D-08-A4 정합).
**Missing dependencies with no fallback:** 없음.

## Code Examples

### Example 1: compute_force_signals umbrella (pipeline wiring 1줄)

```python
# Source: backend/shared/python/sunity_shared/analysis/force_signals.py (신설)
from . import features, temporal

def compute_force_signals(
    pose_frames: list[PoseFrame],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
    *,
    angles: np.ndarray | None = None,
    motion_id: str | None = None,
    gemini_extractor: "GeminiMomentExtractor | None" = None,
    video_uri: str | None = None,
    fps: float = 9.0,
) -> ForceSignalsReport:
    """Phase 8 통합 헬퍼.

    Phase 6 패턴 정합 — pipeline/app.py::_process 가 1줄로 호출.
    내부 단계:
      1. angles 가 None 이면 features.compute_joint_angles + joint_uncertainty 호출
      2. temporal.temporal_fill 통과 (D-08-U1)
      3. compute_phase_boundaries (Layer 1 + 옵션 Layer 2)
      4. 3 metric 산출 함수 호출
      5. overall_confidence 산출
      6. ForceSignalsReport 조립
    """
    # Step 1
    if angles is None:
        # keypoints (T, 17, 4) 재구성 — pose_frame.to_coco17_array 박제 재사용
        from .pose_frame import to_coco17_array
        kp_array = to_coco17_array(pose_frames)
        angles = features.compute_joint_angles(kp_array)
        uncertainty = features.joint_uncertainty(kp_array)
    else:
        uncertainty = None  # 이미 보간된 input 가정

    # Step 2 — temporal_fill (가림 보간)
    angles_filled = temporal.temporal_fill(angles, uncertainty)

    # Step 3 — phase boundaries
    phase_boundaries = compute_phase_boundaries(
        pose_frames=pose_frames, pole_axis=pole_axis, body_profile=body_profile,
        angles=angles_filled, motion_id=motion_id, gemini_extractor=gemini_extractor,
        video_uri=video_uri, fps=fps,
    )

    # Step 4 — 3 metric
    axis_metrics = compute_axis_deviation(pose_frames, phase_boundaries, pole_axis, body_profile)
    stability_metrics = compute_stability_metrics(angles_filled, phase_boundaries, pose_frames)
    contact_metrics = compute_contact_stability(pose_frames, phase_boundaries, pole_axis, body_profile, motion_id)

    # Step 5 — overall confidence
    overall_confidence = _overall_confidence(phase_boundaries, axis_metrics, stability_metrics, contact_metrics)

    warnings: list[str] = []
    if motion_id is None:
        warnings.append("motion_unrecognized_layer1_only")
    if gemini_extractor is None:
        warnings.append("layer2_unavailable")

    return ForceSignalsReport(
        version="1.0",
        overall_confidence=overall_confidence,
        warnings=warnings,
        phase_boundaries=phase_boundaries,
        axis_metrics=axis_metrics,
        stability_metrics=stability_metrics,
        contact_metrics=contact_metrics,
    )
```

### Example 2: dimensions.stability_wobble helper (Option A 박제 — D-08-C1 drift defense)

```python
# Source: backend/shared/python/sunity_shared/analysis/dimensions.py (Phase 8 wave 1 단일 commit)

def stability_wobble(angles, profile: "TechniqueProfile | None" = None) -> float:
    """Raw inter-frame median wobble (degrees) — stability_score 의 변환 전 값.

    force_signals.py 가 본 helper import 해 jitter_score 산출 — drift 방지
    (Phase 12.5 v4 Codex HIGH-2 패턴 정합).
    """
    sliced, _ = _select_window(angles, profile)
    if sliced.shape[0] < 2:
        return 0.0
    inter_frame_diff = np.abs(np.diff(sliced, axis=0))
    median_jerk = np.nanmedian(inter_frame_diff, axis=0)
    return float(np.nanmean(median_jerk))

def stability_score(angles, profile: "TechniqueProfile | None" = None) -> int:
    """기존 — stability_wobble + kismam.score_from_deviation 분리."""
    wobble = stability_wobble(angles, profile)
    sliced, _ = _select_window(angles, profile)
    if sliced.shape[0] < 2:
        return 100  # 기존 박제 정합
    return kismam.score_from_deviation(wobble, _STABILITY_TOL_DEG)
```

### Example 3: Layer 2 Gemini integration with fallback

```python
def compute_phase_boundaries(
    pose_frames: list[PoseFrame],
    pole_axis: PoleAxis,
    body_profile: BodyNormalizationProfile,
    angles: np.ndarray,
    *,
    motion_id: str | None = None,
    gemini_extractor: "GeminiMomentExtractor | None" = None,
    video_uri: str | None = None,
    fps: float = 9.0,
) -> list[PhaseBoundary]:
    # Layer 1 — always
    layer1 = _layer1_heuristic_boundaries(pose_frames, pole_axis, body_profile, angles)

    # Layer 2 — optional
    if not _should_invoke_layer2(motion_id, gemini_extractor, video_uri):
        # confidence='medium' (Layer 1 만)
        return [
            PhaseBoundary(
                phase=b.phase,
                start_frame_idx=b.start_frame_idx, end_frame_idx=b.end_frame_idx,
                start_ms=pose_frames[b.start_frame_idx].timestamp_ms,
                end_ms=pose_frames[b.end_frame_idx - 1].timestamp_ms if b.end_frame_idx > 0 else 0,
                confidence="medium" if motion_id else "low",
                source="heuristic" if motion_id else "heuristic_fallback",
            )
            for b in layer1
        ]

    # Layer 2 호출 — Plan 01-13 박제 모듈
    try:
        layer2_raw = _layer2_gemini_boundaries(
            layer1, video_uri, motion_id, fps, len(pose_frames), gemini_extractor,
        )
        confidence, warnings = _confidence_from_agreement(layer1, layer2_raw)
        if confidence == "low":
            # 불일치 major — Layer 1 사용
            return [_promote_layer1(b, confidence, "heuristic", warnings) for b in layer1]
        else:
            return [_promote_layer1(b, confidence, "gemini_assisted", warnings) for b in layer2_raw]
    except (RuntimeError, ValueError) as exc:
        log.warning("Layer 2 Gemini 호출 실패 — Layer 1 단독: %s", exc)
        return [_promote_layer1(b, "medium", "heuristic", ["layer2_call_failed"]) for b in layer1]
```

## Sources

### Primary (HIGH confidence)

- **`docs/research/02_힘방향_힘조절_엔진_FINAL.md` §5 / §6 / §7** — 3 metric schema 원본 + 5단계 분할 + 12 ContactPoint enum (research 본체)
- **`backend/shared/python/sunity_shared/analysis/pose_frame.py`** — PoseFrame + PoleAxis + ReliabilityLevel + Keypoint3DAligned (Phase 8 입력 본체, Phase 1 박제)
- **`backend/shared/python/sunity_shared/analysis/temporal.py::temporal_fill`** — D-08-U1 박제 source (Phase 1)
- **`backend/shared/python/sunity_shared/analysis/dimensions.py::stability_score / stability_wobble_by_joint / _select_window`** — D-08-C1 재사용 source (Phase 12.5 v4)
- **`backend/shared/python/sunity_shared/analysis/body_normalization.py::BodyNormalizationProfile`** — D-08-D1 거리 정규화 source (Phase 2 v5)
- **`backend/shared/python/sunity_shared/analysis/skeleton.py::JOINT_KEYS / KEYPOINT_NAMES / JOINT_LABEL_KO`** — keypoint 매핑 박제
- **`backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py`** — D-08-A2 Layer 2 reuse 자산 (Plan 01-13 박제)
- **`backend/shared/python/sunity_shared/firestore_admin.py::complete_analysis / _validate_flat_dict_no_nested_array / _validate_dict_only_scalars`** — Firestore 저장 패턴 (Phase 6 W5 박제)
- **`backend/functions/pipeline/app.py::_process / _extract_video_analysis_inputs / _dataclass_to_camel_case_dict`** — pipeline wiring 패턴 (Phase 6 박제)
- **`app/src/types/analysis.ts`** — TS contract (Phase 6/7 박제 정합)
- **`docs/contract.md` §8 / §8.1 / §8.2 / §8.3** — schema 명세 패턴 (Phase 6/7 박제)
- **`.planning/phases/06-coaching/06-RESEARCH.md` / `06-CONTEXT.md`** — Phase 6 wiring 패턴 reference
- **`.planning/phases/07-difference-classification/07-RESEARCH.md` / `07-CONTEXT.md`** — Phase 7 contrast (hold-only 단일 = 구조적 결정, Phase 8 5-phase 의 근거)
- **`.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-13-SUMMARY.md`** — Plan 01-13 verdict + Layer 2 reuse 정확한 분리 박제

### Secondary (MEDIUM confidence)

- **`docs/research/폴스포츠-지식.md`** — 도메인 부위 어휘 (고관절·후굴·코어·내전근·전완근·광배·흉곽·골반·견갑) + 중심축 정의 + 접촉점 도메인
- **`docs/research/00_시스템_아키텍처_FINAL.md`** — 두 엔진 분리 (체형 보정 vs 힘 패턴) — Phase 8 = 엔진 B (힘 패턴) 신호 layer
- **`.planning/REQUIREMENTS.md` FORCE-01** — 본 phase 요구사항 명세
- **`.planning/ROADMAP.md` §Phase 8 / §Phase 9 / §Phase 10**  — downstream consumer 박제
- **`.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md`** — IPSF 5트랙 v1 박제 (Phase 8 tilt 각도 tolerance source — IPSF Code of Points 2024-2025)
- **`backend/shared/python/sunity_shared/analysis/features.py::compute_joint_angles / joint_uncertainty`** — keypoints (T, 17, 4) → angles (T, J=8) 박제
- **`backend/shared/python/sunity_shared/analysis/technique.py::TechniqueProfile.motion_id`** — Phase 5 motion_id field 박제 (Plan 06-02 C2 retro patch)

### Tertiary (LOW confidence — needs validation)

- **IPSF Code of Points 2024-2025 tilt tolerance** — NotebookLM lookup 권장 (memory `notebook-lm-pole-sports`). 명시적 shoulder/hip tilt tolerance 정의 여부 확인 후 A2 lock.
- **Motion-analysis literature default jerk thresholds** — researcher 가 정은지 5영상 jerk 분포 측정 후 A4 lock (sweep sanity check 패턴).
- **expected_contact_points yaml 매핑** — A8 belle/강사 도메인 검수 필수.

## Metadata

**Confidence breakdown:**

- **Standard stack:** HIGH — 신규 라이브러리 0, 모든 import 기존 모듈, Phase 6/7 박제 패턴 직접 정합.
- **Architecture:** HIGH — Phase 6 wiring 패턴 + Phase 12.5 v4 drift defense 패턴 + Plan 01-13 Layer 2 reuse 자산이 모두 박제 완료. 신설은 force_signals.py 1 모듈 + contact_points.yaml 1 파일.
- **Pitfalls:** HIGH — Plan 01-13 verdict 의 정확한 의미 (timestamp vs criteria chain 분리) 박제. Phase 6 W5 + Firestore nested-array 검증 패턴 박제. drift defense 패턴 박제.
- **Threshold values (severity / heuristic cutoff):** MEDIUM — researcher 초안 + belle Pod sweep sanity check 권장. lock 전 belle 검수 박제 (A1~A9 모두).
- **Layer 2 Gemini wiring:** MEDIUM — Plan 01-13 SUMMARY 의 measurement_unreliable_blocked 가 timestamp 자체 의심이 아닌지 belle Pod 실 검증 권장 (A11).
- **expected_contact_points yaml:** MEDIUM — researcher 초안, belle/강사 검수 필수 (A8).

**Research date:** 2026-06-08
**Valid until:** 2026-07-08 (30일 — stable 코드 base, threshold sanity check 만 belle Pod sweep 의존)
