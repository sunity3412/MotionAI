# Phase 6: 체형 정규화 비교 엔진 (coaching 모드) — Research

**Researched:** 2026-06-08
**Domain:** Kinematic-tree bone-length reprojection + IPSF absolute scoring + multi-mode dispatch (mode1 / mode3_first / mode3_progress)
**Confidence:** HIGH (산식·임계값·코드 박제 위치 전부 검증). 일부 임계값 magnitude 는 sweep 데이터 부재로 MEDIUM (Open Question 으로 박제).
**Phase Mode:** mvp (vertical slice)

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### (A) 정규화 대상 — 좌표 재투영 vs 점수 보정

- **D-06-A1:** Phase 6 출력 본체 = **점수 보정 + scale ratio 메타 둘 다 출력**. Phase 6 본체는 점수 정확성 (체형 위양성 제거) 에 집중하고, scale ratio 메타 (5 필드) 를 별도 출력해서 Phase 12 오버레이가 메타를 소비해 좌표 reproject 별도 수행. 책임 분리.
- **D-06-A2:** 좌표 변환 방향 = **B (프로 reference → 수강생 체형 좌표계)**. 정은지의 키포인트를 "정은지가 수강생 키였다면 어디 있어야 할지" 로 reproject. Phase 12 오버레이 = 사용자 영상 위에 "내 키로 환산된 정은지 자세" 표시. 함수 이름 `normalizeStudentPoseToProReference` 는 "수강생 자세를 프로 reference 와 같은 평가 기준으로" 라는 의미지 변환 방향이 아님 (둘은 수학적 동치, 시각화만 다름).
- **D-06-A3:** 세그먼트별 정규화 적용 단위 = **5 필드 모두 + 하이브리드 게이트**. `estimatedHeightScale` + `armScale` + `legScale` + `torsoScale` + `shoulderHipRatio` 모두 활용. 단:
  - `shoulderHipRatio` (좌우 폭 비율) 는 **키포인트 reproject 에만 적용** (Phase 12 시각화 메타)
  - **점수 차원에는 미적용** — [[scoring-dimensions-ipsf]] 박제 (좌우 비대칭 = 폴 동작의 의도적 비대칭, 감점 차원 제거) 유지
  - `shoulderHipRatio` confidence 낮으면 폭 보정 자동 OFF (상하만 적용)
- **D-06-A4:** OFF 분기 = **mode + confidence 병행 게이트**. coaching 모드 + confidence ≥ 0.5 → 정규화 ON. confidence < 0.5 또는 judging 모드 (v1.5) → 정규화 OFF + warning 카피 "체형 측정 불충분, raw 비교". judging 모드 plumbing 은 v1 (mode flag 도입), 실제 활용은 v1.5.

#### (B) mode1 / mode3 first / mode3 second+ 3 케이스 분기

- **D-06-B1:** **mode3 first (수강생 첫 분석, 이전 영상 X)** = **Page 9 절대 트랙 단독 (기본)** + **confidence 높음 + Gemini motion 인식 성공 시 자동 매칭 reference fallback** (정규화 ON 으로 추가 비교 차원 제공). [[ipsf-5-track-scoring]] 정합. fallback 비교 UI 는 "참고용" 으로 명시.
- **D-06-B2:** **mode1 정은지 reference BodyProfile 박제 위치** = **`reference-motions` 컬렉션에 BodyProfile 필드 추가**. Phase 14 정은지 reference 등록 시 `measure_body_profile` 호출. Phase 6 시점 = 현재 등록된 reference 에 일회 측정 fixture 로 백필. contract (TS / Python / docs/contract.md) 의 reference-motion 타입에 `bodyNormalizationProfile` nullable 필드 추가.
- **D-06-B3:** **출력 schema** = **통합 `BodyComparisonReport` + `comparisonType` field**. `comparisonType: 'mode1' | 'mode3_first' | 'mode3_progress'` 구분 필드. 케이스별 없는 필드는 nullable. 3-way contract lockstep 단일 atomic commit.

#### Universal Principle

- **D-06-U1:** **confidence-tiered hybrid** (belle 2026-06-08).
  - **confidence 낮음** (< 0.5) → 안전 fallback (raw 비교, 단정 차단, 정규화 OFF + warning, mode3 first 도 Page 9 단독)
  - **confidence 높음** (≥ 0.5) → 분석 가능한 모든 path 활성화 (5 필드 정규화 + 매칭 reference fallback + 모든 차원 출력)
  - [[feedback-analysis-first]] + [[mvp-simple-pilot-quality]] 동시 정합. D-06-A3 / D-06-A4 / D-06-B1 모두 본 원칙의 구체화 — 단일 게이트로 박제.

### Claude's Discretion

- 점수 보정 산식 magnitude (deficit 점수에 미치는 영향 크기) — researcher 결정. [[scoring-dimensions-ipsf]] + [[analysis-objectivity-no-human-scores]] 박제 유지.
- 세그먼트별 정규화 알고리즘 (`normalizeByBodySegments`) 의 수학적 정의 — researcher 가 reference paper 조사 후 박제.
- `bodyNormalizationConfidence` UI 노출 방식 — Phase 12 / 12.5 협업. Phase 6 는 데이터 출력만.
- `shoulderHipRatio` confidence 임계값 — researcher 가 belle Pod sweep 데이터로 결정 (현재 데이터 부재 — Open Question).

### Deferred Ideas (OUT OF SCOPE)

- 점수 보정 산식 magnitude 의 최종 sweep 검증.
- 세그먼트 정규화 알고리즘 reference paper 정량 비교.
- `bodyNormalizationConfidence` UI 노출 방식.
- judging 모드 plumbing 구현 (v1.5).
- 다각도 입력 통합 (Phase 4 dep).
- `shoulderHipRatio` 측정 안정성 sweep 재실행 — 신규 fixture 또는 belle Pod 신규 sweep 후 결정.
- ROADMAP Progress 섹션 갱신 (별도 작업).

</user_constraints>

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERS-01 | 체형 정규화 비교 엔진(`normalizeStudentPoseToProReference`)이 프로의 동작 성공 원리를 수강생 신체 비율에 맞게 재계산하고, 차이를 "체형 허용 / 개선 필요 / uncertain"으로 분류한다 — coaching 모드 정규화 ON | §3 Kinematic Tree Reprojection 산식 + §5 BodyComparisonReport schema + §6 comparisonType 분기. ("체형 허용 / 개선 필요 / uncertain" 분류는 **Phase 7** 의 책임 — Phase 6 는 `findings[]` raw 산출만, category 라벨링은 downstream.) |

> **본 phase 의 출력이 PERS-01 의 절반 (정규화 + finding raw)을 책임지고, Phase 7 가 나머지 절반 (category 분류) 을 책임진다.** ROADMAP traceability `PERS-01 | Phase 6, Phase 7` 정합.

</phase_requirements>

---

## Project Constraints (from CLAUDE.md / 메모리)

| 제약 | 출처 | Phase 6 영향 |
|------|------|-------------|
| Tech stack 변경 금지 (RTMW + Lambda + RunPod + Firestore + Cerebras) | CLAUDE.md §3 | 신규 ML 모델 도입 X. RTMW PoseFrame + 기존 `_POSE_ESTIMATOR.estimate_with_profile()` 만 사용. |
| Motion AI = 별도 Lambda+S3 | CLAUDE.md §3 | 기존 sunity-motion-pilot stack 만 박제. |
| 3-way contract lockstep | CLAUDE.md Cross-cutting | `BodyComparisonReport` 신설 = TS + Python + `docs/contract.md` 단일 atomic commit. |
| Firestore nested-array 금지 | CLAUDE.md / [[firestore-nested-array-flat]] | `scaleRatios`, `findings`, normalized 좌표 등 nested array 금지. flat 저장 + reshape 또는 dict map 변환 박제. |
| 이모지 / 슬롭 코드 금지 | CLAUDE.md §7 | 본 RESEARCH.md, PLAN.md, 코드 일체 이모지 X. |
| 분석 정확도 최우선 | [[feedback-analysis-first]] | confidence 높을 때 모든 path 활성화 (D-06-U1 핵심). |
| 좌우 대칭 차원 감점 X | [[scoring-dimensions-ipsf]] | shoulderHipRatio 점수 차원 미적용 (D-06-A3). |
| mode3 = 발전 not 일치 | [[mode3-progress-not-similarity]] | mode3_progress 의 출력 = "지난 분석 대비 +N° 개선", "%일치" X. |
| 사람 점수 라벨링 영구 금지 | [[analysis-objectivity-no-human-scores]] | 임계값 = IPSF + 정은지 측정값 + 임계 수치만. belle/강사/심사자 점수 라벨링 X. |
| SMPL / SMPL-X 상업 불가 | [[license-blocklist-pose]] | β / shape_params 영구 도입 X. Anthropometric prior + RTMW measure_body_profile 만 사용. |
| RTMW 단일 백본 | [[rtmw-free-stack-pivot]] | NLF / MediaPipe 호출 경로 X. |
| 분석 핵심 = `_process` 단일 path | CLAUDE.md Cross-cutting | RunPod server.py 와 Lambda pipeline 둘 다 같은 `_process` 호출. 분기는 _process 내부만. |
| Pod xbdkj1g2ylnfwi git lineage 불일치 | STATE.md / [[runpod-gpu-env]] | Pod 동기화 task 별도 (planner 가 판단). |

---

## Summary

Phase 6 는 **체형 차이로 인한 위양성 감점을 제거하고, 수강생의 자세 품질만 측정하는 정규화 비교 엔진**이다. 입력 = (a) 수강생 영상에서 측정한 `BodyNormalizationProfile` (Phase 2 박제, 5 segment ratio 필드 + confidence + warnings), (b) 분석 모드 (mode1 / mode3), (c) reference BodyProfile (mode1 = 정은지 fetch, mode3 first = 매칭 reference fallback or None, mode3 progress = 이전 분석 doc fetch). 출력 = `BodyComparisonReport` (통합 schema + `comparisonType` 분기 + `scaleRatios` 메타 + `findings[]` raw + `bodyNormalizationConfidence`).

알고리즘 본체 = **Kinematic Tree Bone-Length Reprojection** (NotebookLM Notebook 1 §1.1) — 골반 root → kinematic tree 따라 root-to-leaf 순차 재투영. 방향 벡터 보존, 뼈 길이만 reference 비율로 덮어씀. pure numpy, 외부 모델 의존 0. 정규화된 키포인트에서 cosine-law 각도 (scale-invariant) 산출 후 IPSF GeometricCriterion 절대 deficit 7종 (Knee-Toe / Clean lines / Extension / Posture / Body placement / Poor transitions / Bad angle) 측정. 체형 ratio 를 deficit 에 직접 곱하지 않음 (IPSF 박제 위반 회피).

`bodyNormalizationConfidence` = temporal variance (Notebook 4 §4.2 — 5-10% bone-length 분산 임계) + spatial dispersion (Notebook 4 §4.2 B) per-segment aggregate. 게이트:
- confidence ≥ 0.5 → 5 필드 모두 정규화 ON
- confidence < 0.5 → 정규화 OFF, raw 비교 + `comparisonType=*_low_confidence` warning + IPSF 절대 deficit 만 (Page 9 단독)
- 추가 안전망: `shoulderHipRatio` 자체 confidence 낮거나 몸통-카메라 각도 < 60° (foreshortening) → 폭 보정 OFF (Notebook 1 §1.5)

**Primary recommendation:** Phase 6 본체 = (1) `body_normalizer.py` 신규 모듈 (`normalize_pose_by_segments`, `compute_body_normalization_confidence`, `compare_body_profiles`), (2) `BodyComparisonReport` dataclass 3-way contract lockstep, (3) `pipeline/_process` 의 mode1 / mode3 분기 내부에 정규화 호출 wiring, (4) `firestore_admin.complete_analysis` 의 `bodyComparisonReport` 저장. 별도 plan = 정은지 reference 백필 스크립트 (운영 작업, 1회 실행).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Kinematic-tree bone-length reproject 산식 | Backend / 분석 코어 (pure numpy) | — | 모델/네트워크/AWS 무관 — 단위 테스트 가능. `backend/shared/python/sunity_shared/analysis/body_normalizer.py` 신설. |
| BodyComparisonReport schema | 데이터 contract (TS + Python + docs) | API / Firestore | 3-way lockstep — `app/src/types/analysis.ts` + `backend/shared/python/sunity_shared/models.py` + `docs/contract.md` §8 (신설). |
| confidence 산식 (temporal variance + spatial dispersion) | Backend / 분석 코어 | — | pure numpy. `body_normalizer.py` 내부. |
| mode 분기 (mode1 / mode3 first / mode3 progress) | Backend / 파이프라인 | — | `backend/functions/pipeline/app.py::_process` 의 기존 분기 안에 wiring. |
| reference BodyProfile 저장 | Database / Firestore | Backend (seed script) | `reference/{motionId}` 컬렉션 신규 nullable 필드 + 백필 스크립트. |
| Firestore AnalysisDoc 저장 | Database / Firestore | Backend | `firestore_admin.complete_analysis` 의 `bodyComparisonReport` arg 박제. flat 저장 정합. |
| BodyComparisonReport 노출 (UI) | Frontend / Phase 12.5 후속 | — | Phase 6 는 데이터 출력만. UI 노출은 Phase 12 / 12.5 책임 (D-06 deferred). |
| 차이 분류 (allowed / needs_adjustment / uncertain) | Backend / Phase 7 책임 | — | Phase 6 = `findings[]` raw 산출, Phase 7 = category 분류. ROADMAP `PERS-01 | Phase 6, Phase 7` 정합. |
| 키포인트 reproject 좌표 시각화 | Frontend / Phase 12 책임 | — | Phase 6 는 `scaleRatios` 메타만 emit. 실제 reproject 좌표는 Phase 12 가 메타 소비 후 산출. |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | >=1.26,<2.0 (Pod) / >=1.26,<3 (Lambda+dev) | Kinematic-tree reproject 산식, MAD, temporal variance, cosine-law 각도 | 기존 stack 박제 (`pose_estimator.py`, `body_normalization_measurer.py` 등 모두 numpy only). Pure 함수 → 단위 테스트 가능. **`backend/requirements-dev.txt` 박제 정합** `[VERIFIED: backend/requirements-dev.txt + runpod_inference/requirements.txt]` |
| 기존 RTMW PoseEngine (`_RTMWNlfCompat.estimate_with_profile`) | 운영 path | RTMW 키포인트 → BodyNormalizationProfile 측정 | Phase 2 박제, 본 phase 가 신규 호출 path 추가하지 않고 기존 helper `_angles_and_body_profile_from_video` 그대로 사용 `[VERIFIED: backend/functions/pipeline/app.py:306]` |
| `body_normalization_measurer.measure_body_profile` | 기존 박제 | reference 비디오 (정은지) 의 BodyProfile 백필 | Phase 2 박제 함수 — 백필 스크립트가 이 함수 호출 `[VERIFIED: backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py:212]` |
| `firestore_admin.get_reference_motion` / `complete_analysis` | 기존 박제 | reference BodyProfile fetch + AnalysisDoc 저장 | Phase 2 plan 02-01 박제 기반 — Phase 6 가 호출 site 추가 `[VERIFIED: backend/shared/python/sunity_shared/firestore_admin.py:45, 106]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses` (stdlib) | Python 3.12 | `BodyComparisonReport` + `BodyComparisonFinding` + `ScaleProfile` frozen dataclass | dimensions / models 박제 패턴 정합 `[VERIFIED: backend/shared/python/sunity_shared/analysis/body_normalization.py:48]` |
| `math` (stdlib) | Python 3.12 | finite / positive validator, cosine, sqrt | `__post_init__` validator 박제 (`isfinite`, ValueError) `[VERIFIED: backend/shared/python/sunity_shared/analysis/body_normalization.py:121]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Kinematic Tree Bone-Length Reprojection | Generalized Procrustes Analysis (GPA: `P_norm = s · P_raw · R + t`) | 전체 scale + rotation + translation 동시 최적화 — 평가 metric (PA-MPJPE) 정의에 OK. **세그먼트별 길이 차이가 크면 부분 왜곡 발생** → 정밀 비교에는 Kinematic Tree 가 우월 `[CITED: NotebookLM Notebook 1 §1.2]` |
| Kinematic Tree (pure numpy) | SMPL 계열 (HMR/SPIN/CLIFF) — shape β + pose θ 분리 | β 강제 통일 → 뼈 길이 정규화 자동. **사용 금지** — [[license-blocklist-pose]] SMPL/SMPL-X 상업 불가 + [[rtmw-free-stack-pivot]] β 의존 영구 제거 `[CITED: NotebookLM Notebook 1 §1.3 + memory]` |
| numpy 직접 산식 | BioPose + NeurIK (OpenSim 기반 BSK 24 segment) | bone scale s + 회전 q^r 분리, anatomical constraint. **R&D reference 만** — 라이선스 미확정, 운영 코드 통합 X `[CITED: NotebookLM Notebook 1 §1.3]` |
| 본 phase 의 정규화 본체 | 각도만 scale-invariant 비교 (정규화 없이) | 각도는 본질적으로 scale-invariant — 부분적 무효화 가능. **단, root-centered + bone-aligned reproject 가 선행되어야 정확** → Phase 6 의 본 path 와 보완적, 단독 사용 X `[CITED: NotebookLM Notebook 2 §2.1]` |
| 단순 Anthropometric prior | Depth Anything v2 + Huber loss (mm 단위 추정) | Camera intrinsic 없이도 metric scale 추정. **v1 skip** — 추가 모델 의존 + 라이선스 / 가중치 audit 별도 필요. R&D reference 만 `[CITED: NotebookLM Notebook 4 §4.1]` |

**Installation:**

- 신규 라이브러리 도입 **없음**. 기존 stack (numpy + stdlib) 만 사용.
- pip 설치 / weights 다운로드 / pyproject 갱신 박제 X.

**Version verification:**

```bash
grep -n "numpy" backend/requirements-dev.txt backend/runpod_inference/requirements.txt
# backend/requirements-dev.txt: "numpy>=1.26,<3"
# backend/runpod_inference/requirements.txt: "numpy>=1.26,<2.0"
```

(verified 2026-06-08. Phase 2 박제 body_normalization_measurer 가 numpy >=1.26 path 에서 정상 동작 확인.)

---

## Package Legitimacy Audit

> **본 phase 는 신규 외부 패키지를 도입하지 않으므로 본 섹션 스킵 가능.**

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| numpy (재인용) | PyPI | 18+ yrs | 200M+/mo | github.com/numpy/numpy | N/A (stdlib-tier 박제) | Approved (기존 박제) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

Phase 6 는 알고리즘 본체 + schema + wiring 만 박제하므로 신규 패키지 추가 검증 박제 불필요.

---

## Architecture Patterns

### System Architecture Diagram

```
                       [App: 영상 업로드 (mode1 or mode3)]
                                    │
                       S3 PUT (presigned URL)
                                    │
                       S3 ObjectCreated → SQS
                                    │
              ┌─────────────────────┴─────────────────────┐
              │                                             │
   [RunPod Lambda 위임]                          [Lambda 폴백 _process]
              │                                             │
              └─────────────────────┬─────────────────────┘
                                    │
                       backend/functions/pipeline/app.py::_process
                                    │
                       _angles_and_body_profile_from_video (Phase 2)
                          ├─→ angles (T, J=8)
                          └─→ student_profile: BodyNormalizationProfile (5 필드 + conf + warnings)
                                    │
                       _ensure_recognizer().recognize(angles, frames)
                          └─→ profile: TechniqueProfile (motion_id + EXTEND/BENT + hold_window)
                                    │
              ┌─────────────────────┴─────────────────────┐
              │            comparisonType 분기            │
              │            (NEW — Phase 6 본체)           │
              ├─ mode == "mode1":
              │     ref = firestore_admin.get_reference_motion(referenceMotionId)
              │     ref_profile = BodyNormalizationProfile(**ref["bodyNormalizationProfile"])
              │     comparisonType = "mode1"
              │
              ├─ mode == "mode3" and prev is None:
              │     # Page 9 절대 트랙 단독 (D-06-B1 기본)
              │     ref_profile = None  +  IPSF 절대 deficit
              │     comparisonType = "mode3_first"
              │     # confidence 높고 + Gemini motion 매칭 시 자동 fallback:
              │     if profile.name != "미상" and student_profile.confidence >= 0.5:
              │         ref = match_reference_by_motion_id(profile.motion_id)
              │         if ref and ref["bodyNormalizationProfile"]:
              │             ref_profile = BodyNormalizationProfile(**...)
              │             comparisonType = "mode3_first_with_fallback"
              │
              └─ mode == "mode3" and prev is not None:
                    prev_profile = BodyNormalizationProfile(**prev["bodyNormalizationProfile"])
                    comparisonType = "mode3_progress"
                                    │
                       body_normalizer.compare_body_profiles(
                           student_profile, ref_profile, comparisonType
                       )
                          └─→ scale_profile: ScaleProfile (5 필드 ratio 산출)
                                    │
                       body_normalizer.compute_body_normalization_confidence(
                           pose_frames, scale_profile
                       )
                          └─→ confidence: float [0,1]
                                    │
                       body_normalizer.measure_ipsf_deficits(
                           angles, profile, scale_profile, gate
                       )
                          └─→ findings: list[BodyComparisonFinding]
                                    │
                       BodyComparisonReport 조립 (comparisonType + scaleRatios +
                                                  findings + confidence + warnings)
                                    │
                       기존 build_result(...) + assemble.build_dimension_explanation
                                    │
                       firestore_admin.complete_analysis(
                           ..., body_comparison_report=...  # 신규 arg
                       )
                                    │
                       Firestore users/{uid}/analyses/{analysisId}
                          .result.bodyComparisonReport (신규 필드, flat 저장)
                                    │
                       App onSnapshot → Phase 7 / 12 / 13 가 소비
```

**핵심 흐름 변화 (Phase 6 본체):**
1. `_process` 내부 helper 교체: 기존 `_angles_from_video` → `_angles_and_body_profile_from_video` (Phase 2 박제 helper 가 이미 wiring 박제, Phase 6 가 호출 site 만 갱신).
2. `comparisonType` 분기 신설 — `_process` 내부 mode1 / mode3 분기 안에 wrap.
3. `body_normalizer` 모듈 (신규) 의 3 함수 호출: `compare_body_profiles`, `compute_body_normalization_confidence`, `measure_ipsf_deficits`.
4. `BodyComparisonReport` 조립 후 `complete_analysis` 의 신규 arg 로 Firestore 저장.

### Recommended Project Structure

```
backend/shared/python/sunity_shared/
├── analysis/
│   ├── body_normalization.py             # 기존 (Phase 2) — BodyNormalizationProfile dataclass
│   ├── body_normalization_measurer.py    # 기존 (Phase 2) — measure_body_profile
│   └── body_normalizer.py                # 신규 (Phase 6) — Kinematic Tree reproject + IPSF deficit + confidence
├── models.py                             # 갱신 (Phase 6) — BodyComparisonReport re-export
└── firestore_admin.py                    # 갱신 (Phase 6) — complete_analysis 신규 arg

backend/functions/pipeline/app.py         # 갱신 (Phase 6) — _process 분기 wiring
backend/scripts/
└── backfill_reference_body_profiles.py   # 신규 (Phase 6 별도 plan) — 정은지 reference 백필

backend/tests/
└── test_body_normalizer.py               # 신규 — pure 함수 단위 테스트 (5 fixture)

app/src/types/analysis.ts                 # 갱신 — BodyComparisonReport interface
docs/contract.md                          # 갱신 — §8 BodyComparisonReport 명세
```

### Pattern 1: Kinematic Tree Bone-Length Reprojection (정규화 본체 산식)

**What:** 골반 (Pelvis = `mid_hip`) 을 원점으로, hierarchical kinematic tree 따라 root → leaf 순서로 키포인트를 재투영. 방향 벡터는 raw 좌표에서 보존, 뼈 길이만 reference `L_ref` 로 덮어쓴다.

**When to use:** Phase 6 의 정규화 본체 알고리즘. `comparisonType in {mode1, mode3_first_with_fallback, mode3_progress}` 모든 케이스에서 reference BodyProfile 이 있을 때.

**산식 (NotebookLM Notebook 1 §1.1 박제):**

```
1단계 (Root Centering):
    P_centered[j] = P_raw[j] - P_root_raw       for j in JOINT_KEYS

2단계 (Bone Length Ratio Reprojection):
    for each (parent, child) in KINEMATIC_TREE_EDGES (root → leaf 순):
        v = C_raw - P_raw                            # raw direction vector
        v_unit = v / max(||v||₂, eps)                # unit vector (eps=1e-8)
        L_ref = student_profile.segment_length(parent, child)   # NotebookLM: 수강생 BodyProfile 의 5 필드
        C_norm = P_norm + v_unit * L_ref             # reproject
```

**Example (numpy 의사코드):**

```python
# backend/shared/python/sunity_shared/analysis/body_normalizer.py
# Source: NotebookLM Notebook 1 §1.1 (Kinematic Tree Bone-Length Reprojection)
# Memory: rtmw-free-stack-pivot — RTMW PoseFrame.keypoints_3d input only.

import numpy as np
from .body_normalization import BodyNormalizationProfile
from .pose_frame import PoseFrame
from .skeleton import KEYPOINT_NAMES

# kinematic tree (parent, child) edges — RTMW COCO-17 joint topology.
# root = mid_hip (left_hip 과 right_hip 의 중점, 가상 keypoint).
# NotebookLM §1.1 박제 + 기존 skeleton.JOINT_ANGLES 정합 (8 관절각).
KINEMATIC_TREE_EDGES: tuple[tuple[str, str], ...] = (
    # 상체 (mid_hip → mid_shoulder)
    ("mid_hip", "mid_shoulder"),
    ("mid_shoulder", "left_shoulder"),
    ("mid_shoulder", "right_shoulder"),
    # 팔 (어깨 → 팔꿈치 → 손목)
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    # 골반 (mid_hip → 좌/우 hip)
    ("mid_hip", "left_hip"),
    ("mid_hip", "right_hip"),
    # 다리 (고관절 → 무릎 → 발목)
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
)

_EPS = 1e-8


def normalize_pose_by_segments(
    raw_keypoints: dict[str, tuple[float, float, float]],
    reference_profile: BodyNormalizationProfile,
    student_torso_length_px: float,
    *,
    apply_shoulder_hip_ratio: bool = True,  # foreshortening / confidence 게이트
) -> dict[str, tuple[float, float, float]]:
    """단일 frame keypoints → kinematic tree 정규화 (방향 B: 프로 → 수강생 좌표계).

    Note: 본 함수는 D-06-A2 방향 B 의 수학적 dual 인 "수강생 frame 의 길이를
    reference 비율로 reproject" 형식. caller (compare_body_profiles) 가
    student frame 에 ref segment 비율 적용 → "정은지가 수강생 키였다면" 효과.

    Args:
        raw_keypoints: name → (x, y, z) — RTMW image coord (y-down).
        reference_profile: 프로 (정은지) 의 BodyNormalizationProfile.
        student_torso_length_px: 수강생 영상의 측정 torso 길이 (px).
            모든 ref segment ratio 를 이 길이로 곱해 px 단위로 변환.
        apply_shoulder_hip_ratio: shoulderHipRatio 적용 여부.
            D-06-A3 박제 — confidence 낮거나 foreshortening 시 False.
    """
    # 1단계: 가상 root 계산 + Root Centering.
    if "left_hip" not in raw_keypoints or "right_hip" not in raw_keypoints:
        return raw_keypoints  # endpoint 미감지 — fallback
    lh = np.array(raw_keypoints["left_hip"])
    rh = np.array(raw_keypoints["right_hip"])
    mid_hip = (lh + rh) / 2

    centered: dict[str, np.ndarray] = {
        name: (np.array(p) - mid_hip)
        for name, p in raw_keypoints.items()
    }
    if "left_shoulder" in centered and "right_shoulder" in centered:
        centered["mid_shoulder"] = (
            centered["left_shoulder"] + centered["right_shoulder"]
        ) / 2
    centered["mid_hip"] = np.zeros(3)

    # 2단계: Bone Length Ratio Reprojection (root → leaf 순).
    normalized: dict[str, np.ndarray] = {"mid_hip": np.zeros(3)}
    for parent, child in KINEMATIC_TREE_EDGES:
        if parent not in centered or child not in centered:
            continue
        if parent not in normalized:
            normalized[parent] = centered[parent]  # 안전망 (사이클 없음)
        v_raw = centered[child] - centered[parent]
        norm = np.linalg.norm(v_raw)
        if norm < _EPS:
            normalized[child] = normalized[parent]
            continue
        v_unit = v_raw / norm
        # L_ref = ref segment ratio × student torso px.
        # D-06-A3 박제 — apply_shoulder_hip_ratio False 시 mid→shoulder, mid→hip 폭 보정 skip.
        L_ref_ratio = _ref_segment_ratio(
            parent, child, reference_profile,
            apply_shoulder_hip_ratio=apply_shoulder_hip_ratio,
        )
        L_ref_px = L_ref_ratio * student_torso_length_px
        normalized[child] = normalized[parent] + v_unit * L_ref_px

    return {k: tuple(v.tolist()) for k, v in normalized.items()}


def _ref_segment_ratio(
    parent: str, child: str, ref: BodyNormalizationProfile,
    *, apply_shoulder_hip_ratio: bool,
) -> float:
    """edge → reference profile 의 ratio mapping.

    5 필드 → 13 edges 매핑:
      mid_hip ↔ mid_shoulder        = torsoScale (=1.0 by self-reference)
      mid_shoulder ↔ {l,r}_shoulder = shoulderHipRatio / 2 * 0.5 (폭 절반)   ★ apply_shoulder_hip_ratio gate
      mid_hip ↔ {l,r}_hip           = 0.5 * (1.0 / shoulderHipRatio) * 0.5  ★ apply_shoulder_hip_ratio gate
      {l,r}_shoulder ↔ {l,r}_elbow  = armScale * 0.5    (상완 = 팔 전체의 약 1/2)
      {l,r}_elbow ↔ {l,r}_wrist     = armScale * 0.5    (전완 = 팔 전체의 약 1/2)
      {l,r}_hip ↔ {l,r}_knee        = legScale * 0.5    (대퇴 = 다리 전체의 약 1/2)
      {l,r}_knee ↔ {l,r}_ankle      = legScale * 0.5    (하퇴 = 다리 전체의 약 1/2)

    *armScale / legScale = torso 대비 사지 전체 길이 (Phase 2 v5 박제).
    *상완 vs 전완 50/50 분할 = 인체측정학 평균. Phase 6 v1 은 단순 분할 — v1.5 에서
    `upper_arm_ratio` / `forearm_ratio` 등 세분화 필드 추가 검토 (Open Question 박제).
    """
    if {parent, child} == {"mid_hip", "mid_shoulder"}:
        return ref.torso_scale  # 1.0
    if parent == "mid_shoulder" and child in {"left_shoulder", "right_shoulder"}:
        if not apply_shoulder_hip_ratio:
            return 0.25  # neutral fallback (수강생 본인 비율 유지)
        return ref.shoulder_hip_ratio * 0.25  # 폭 절반 × 0.5
    if parent == "mid_hip" and child in {"left_hip", "right_hip"}:
        if not apply_shoulder_hip_ratio:
            return 0.25
        return (1.0 / max(ref.shoulder_hip_ratio, _EPS)) * 0.25
    if child in {"left_elbow", "right_elbow"}:
        return ref.arm_scale * 0.5
    if child in {"left_wrist", "right_wrist"}:
        return ref.arm_scale * 0.5
    if child in {"left_knee", "right_knee"}:
        return ref.leg_scale * 0.5
    if child in {"left_ankle", "right_ankle"}:
        return ref.leg_scale * 0.5
    return 1.0  # unknown edge fallback
```

`[CITED: NotebookLM Notebook 1 §1.1 박제 — Kinematic Tree Bone-Length Reprojection]`

### Pattern 2: Scale-Invariant Angle (cosine law)

**What:** 정규화된 좌표에서 관절각을 cosine law 로 산출. 본질적으로 scale-invariant — 뼈 길이가 달라져도 각도 자체는 불변. `dimensions.py` 박제 패턴 정합.

**When to use:** 정규화 후 IPSF GeometricCriterion 절대 deficit 측정 전 단계.

**산식 (NotebookLM Notebook 2 §2.1 박제):**

```python
# joint B 의 각도 = 인접 segment 벡터 BA, BC 의 내적 / 크기 곱.
import numpy as np
import math

def joint_angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """∠ABC (도). NaN-safe (한쪽 벡터 = 0 시 NaN)."""
    ba = a - b
    bc = c - b
    n1 = np.linalg.norm(ba)
    n2 = np.linalg.norm(bc)
    if n1 < _EPS or n2 < _EPS:
        return float("nan")
    cos_theta = float(np.dot(ba, bc) / (n1 * n2))
    cos_theta = max(-1.0, min(1.0, cos_theta))  # 수치 안정성
    return math.degrees(math.acos(cos_theta))
```

`[CITED: NotebookLM Notebook 2 §2.1 — cosine law 각도 산출]`
`[VERIFIED: backend/shared/python/sunity_shared/analysis/skeleton.py:39 — JOINT_ANGLES 8 관절 박제]`

**중요:** 본 phase 의 IPSF deficit 산출은 정규화된 keypoint → 각도 → deficit 순서. **정규화는 IPSF 절대 deficit 산출 전 키포인트 좌표 정렬에만 사용** — 각도 산출 단계는 정규화 무관 (이미 scale-invariant). 정규화의 역할 = MPJPE 류 거리 metric 의 위양성 제거 + Phase 12 시각화 오버레이 좌표 일치 `[CITED: NotebookLM Notebook 3 §3.1 박제]`.

### Pattern 3: bodyNormalizationConfidence 산식 (temporal + spatial)

**What:** Phase 2 측정의 `BodyNormalizationProfile.confidence` (single video) 와 별개로, **본 phase 가 산출하는 confidence** = student profile 측정의 robustness + reference profile 매칭 신뢰도 + 세그먼트별 temporal variance + spatial dispersion 통합.

**When to use:** 모든 comparisonType 에서 `BodyComparisonReport.bodyNormalizationConfidence` 필드에 emit (D-06 success #4 박제 — "항상 포함").

**산식 (NotebookLM Notebook 4 §4.2 박제):**

```python
def compute_body_normalization_confidence(
    pose_frames: list[PoseFrame],
    student_profile: BodyNormalizationProfile,
    reference_profile: BodyNormalizationProfile | None,
) -> tuple[float, list[str]]:
    """bodyNormalizationConfidence 산출 — temporal variance + spatial dispersion 통합.

    Returns:
      (confidence: float [0,1], warnings: list[str])

    산식 단계:
      1) base = student_profile.confidence  (Phase 2 박제, 11 segment conf 평균)
      2) temporal_penalty = mean over segments of:
            normalized_variance = var(bone_length over frames) / mean(bone_length)^2
            penalty = clip( (normalized_variance - 0.05) / 0.05, 0, 1 )
         5% 임계 = excellent. 10% 임계 = 한계.  (Notebook 4 §4.2 박제)
      3) spatial_dispersion_penalty = 1 - clip( mean C_s(t) / shoulder_width, 0, 1 )
         C_s(t) = (1/J) Σ_j ||P_j(t) - centroid(t)||  (Notebook 4 §4.2 B)
         관절들이 중심에 뭉칠수록 (웅크림) → 깊이 모호 → penalty 박제.
      4) reference_match_bonus = 0.0 if ref is None else 0.1 * min(ref.confidence, 1.0)
         reference 가 있고 그 측정 신뢰도가 높으면 bonus.
      5) confidence = max(0, min(1, base - 0.5 * temporal_penalty - 0.3 * spatial_dispersion_penalty + reference_match_bonus))

    warnings 박제 (저신뢰 사유 누적):
      - "temporal_variance_above_threshold" if temporal_penalty > 0.5
      - "spatial_dispersion_low" if spatial_dispersion_penalty > 0.5
      - "reference_profile_missing" if reference_profile is None and comparisonType != "mode3_first"
    """
    # ... (구현은 plan 에서 구체화)
```

**임계값:**
- 5% normalized variance = excellent (penalty 0)
- 10% normalized variance = 한계 (penalty 1)
- `confidence ≥ 0.5` 게이트 = 정규화 ON (D-06-A4)
- `confidence < 0.5` 게이트 = OFF + warning

`[CITED: NotebookLM Notebook 4 §4.2 A (temporal variance 5-10% 임계) + B (spatial dispersion)]`
`[VERIFIED: backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py:330 — Phase 2 confidence 산출 패턴 정합]`

### Pattern 4: IPSF GeometricCriterion 절대 Deficit (Page 21)

**What:** 정규화된 키포인트에서 IPSF Code of Points "all components" 절대 트랙 7개 deficit 측정. 체형 ratio 를 deficit 에 직접 곱하지 X (IPSF 박제 위반 회피).

**When to use:** 모든 comparisonType — `mode3_first` 단독 진입 시에도 본 트랙 단독으로 자세 품질 채점 가능. ([[ipsf-5-track-scoring]] 정합)

**Deficit 7종 (NotebookLM Notebook 3 §3.3 박제):**

| Deficit | 감점 | 산식 (정규화 keypoint 기반) |
|---------|------|-----------------------------|
| Knee-Toe Alignment | -0.2 | `joint_angle_deg(big_toe, knee, ankle)` 가 180° 직선 정렬 실패 (tolerance ±20°) |
| Clean lines | -0.2 | 팔/다리 신전 관절 (`profile.expects_extension` True) 의 평균 각도 < 180° - 20° |
| Extension | -0.2 | 척추 / 목 / 손목 라인의 굽힘 (현재 v1 에서는 mid_shoulder ↔ mid_hip ↔ neck 라인의 평균 각도 < 160°) |
| Posture | -0.2 | 어깨 rounded (좌우 어깨 line z-axis 깊이 차이 > shoulder_width × 0.3) |
| Body placement | -0.2 | 폴 축 (PoleAxis) 대비 mid_hip 의 수평 거리 > 임계 (v1 = shoulder_width 의 50%) |
| Poor transitions | -0.5 | 진입 / 탈출 구간 (hold_window 이전 / 이후) 의 angular velocity 분산 > 임계 |
| Bad angle | -0.5 | reliability=low 인 frame ratio > 50% (심판이 실행 각도 미관측 = AI 가 측정 불가) |

**산출 시 박제 박제 박제:**
- **체형 ratio 곱하지 말 것** — IPSF 박제 위반 (NotebookLM §3.3 박제).
- **split 각도 toe-to-toe 절대 금지** — hip→knee 라인 각도만 사용 (NotebookLM §3.4 박제 — 다리 긴 선수 유리 위양성).
- 각 deficit 미충족 시 절대 deficit 차감, finding 으로 record.

`[CITED: NotebookLM Notebook 3 §3.3 박제 — IPSF Page 21 Singular Deductions 7종]`
`[CITED: NotebookLM Notebook 3 §3.4 박제 — split 각도 toe-to-toe 위양성 회피]`

### Pattern 5: foreshortening 자동 confidence 하향

**What:** shoulderHipRatio 의 픽셀 측정이 부정확한 시나리오 (몸통이 카메라 시선과 평행) 자동 detect → `apply_shoulder_hip_ratio=False` + confidence 하향.

**When to use:** 정규화 호출 전 게이트 판정.

**산식 (NotebookLM Notebook 1 §1.5 박제):**

```python
def is_foreshortening_detected(
    pose_frames: list[PoseFrame],
    threshold_deg: float = 60.0,
    threshold_px: float = 150.0,
) -> bool:
    """foreshortening (몸통 vs 카메라 Z축 < 60°) 검출.

    조건 (Notebook 1 §1.5):
      1) 어깨-골반 벡터 vs 카메라 Z축 각도 < 60° (몸통이 카메라 시선과 평행)
      2) hard threshold: shoulder-hip 픽셀 거리 < 150px
      (직립 대비 30-40% 이하)
    """
    # 산식 박제: 카메라 Z축 = (0, 0, 1) 가정 (image plane normal).
    # ...
```

`[CITED: NotebookLM Notebook 1 §1.5 박제]`

### Pattern 6: Pipeline `_process` 통합 분기 (mode 분기 wiring)

**What:** 기존 `backend/functions/pipeline/app.py::_process` 의 mode1 / mode3 분기 안에 Phase 6 정규화 호출을 wiring. **기존 흐름 무수정 + 추가만**.

**When to use:** Phase 6 본체 plan 의 핵심 wiring task.

**박제 위치 (기존 코드 박제):**

| Line | 기존 코드 | Phase 6 갱신 |
|------|-----------|--------------|
| `pipeline/app.py:450-452` | `angles = _angles_from_video(bucket, key)` (Gemini OFF path) | `angles, student_profile = _angles_and_body_profile_from_video(bucket, key)` — Phase 2 helper 사용 |
| `pipeline/app.py:476-516` | mode1 분기 — `ref = firestore_admin.get_reference_motion(...)` | ref fetch 후 `ref_profile = BodyNormalizationProfile(**ref.get("bodyNormalizationProfile"))` 추가 + `compare_body_profiles(student_profile, ref_profile, "mode1")` 호출 |
| `pipeline/app.py:517-525` | mode3 분기 — `prev = firestore_admin.get_previous_analysis(...)` | prev 있을 시 `prev_profile = BodyNormalizationProfile(**prev.get("bodyNormalizationProfile"))` + `comparisonType = "mode3_progress"`. prev 없으면 `comparisonType = "mode3_first"` + Gemini motion 매칭 fallback path |
| `pipeline/app.py:541-555` | `result = assemble.build_result(...)` | result 조립 시 `body_comparison_report=body_comparison_report` 신규 arg 추가 |
| `pipeline/app.py:556-564` | `firestore_admin.complete_analysis(...)` | `body_comparison_report=...` 신규 arg + flat 변환 책임 박제 |

**박제 박제 정신 (CLAUDE.md):**
- Lambda 폴백 path 와 RunPod path 둘 다 같은 `_process` 호출 → 본 변경이 양쪽에 자동 박제.
- B8 박제 (시그너처 무변경) — `_angles_from_video` 시그너처 유지 박제 (Gemini OFF path 호환). Phase 6 는 Gemini ON path 의 `_angles_and_video_path_from_video` 도 갱신 필요 — `student_profile` 도 함께 반환하는 신규 helper `_angles_video_path_and_body_profile_from_video` 추가 또는 `_angles_and_body_profile_from_video` 의 시그너처 확장 (planner 결정).

### Anti-Patterns to Avoid

- **체형 ratio 를 IPSF deficit 에 직접 곱하기** — IPSF 박제 위반. 정규화는 keypoint 좌표 정렬에만 사용, deficit 산출은 정규화된 keypoint 에서 IPSF 절대 기준으로. `[CITED: Notebook 3 §3.1]`
- **split 각도를 toe-to-toe Euclidean 거리로 측정** — 다리 긴 선수 유리 위양성. hip→knee 라인 각도만 사용. `[CITED: Notebook 3 §3.4]`
- **SMPL/SMPL-X β 도입** — 라이선스 차단 + RTMW pivot 위반. NLF_SMPLX path 의 R&D 산출도 본 contract 에 노출 X (`bodyNormalizationProfile` 만 박제). `[CITED: memory license-blocklist-pose + rtmw-free-stack-pivot]`
- **shoulderHipRatio 를 점수 차원에 적용** — 좌우 비대칭 = 폴 동작의 의도적 비대칭. 감점 차원 제거 박제 위반. `[CITED: D-06-A3 + memory scoring-dimensions-ipsf]`
- **mode3 first 에 강제 reference 비교 결과 노출** — [[mode3-progress-not-similarity]] 위반. fallback reference 사용 시 UI 카피 "참고용" 명시 박제, "%일치" 노출 X. `[CITED: D-06-B1]`
- **Firestore 에 nested array 저장** — `scaleRatios`, `findings`, normalized keypoints 등 nested array 형식 X. flat 저장 (dict map or flat list + meta) 박제. `[CITED: CLAUDE.md + memory firestore-nested-array-flat]`
- **`bodyNormalizationConfidence` 누락** — 모든 comparisonType 에서 항상 emit. confidence=0 일 때도 필드 자체는 박제 박제 (success #4). `[CITED: D-06 success #4]`
- **NLF 모듈 import** — `_RTMWNlfCompat` 가 NLF interface 호환 wrapper. NLF 모델 직접 호출 X. `[CITED: backend/functions/pipeline/app.py:203]`
- **새 Lambda 함수 / 신규 SAM 리소스 추가** — 본 phase 는 기존 pipeline Lambda 안에서만 작동. SAM template 갱신 박제 X.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BodyNormalizationProfile 측정 | 신규 segment 측정 함수 | `body_normalization_measurer.measure_body_profile` (Phase 2 박제) | Phase 2 가 MAD outlier rejection + 5 warning enum + fallback 박제 완료 `[VERIFIED: backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py:212]` |
| RTMW PoseFrame 추출 + body_shape 주입 | 신규 estimator wrapper | `_POSE_ESTIMATOR.estimate_with_profile()` (`_RTMWNlfCompat` Phase 2 박제) | 이미 race-safe local-tuple 반환 박제 `[VERIFIED: backend/functions/pipeline/app.py:234]` |
| Firestore reference 조회 | 새 helper | `firestore_admin.get_reference_motion(motionId)` | 박제 박제 `[VERIFIED: backend/shared/python/sunity_shared/firestore_admin.py:106]` |
| Firestore AnalysisDoc 저장 | 새 admin helper | `firestore_admin.complete_analysis(..., body_comparison_report=...)` 시그너처 확장 | 기존 `angles` flat 저장 패턴 정합 + nested-array 회피 `[VERIFIED: backend/shared/python/sunity_shared/firestore_admin.py:45]` |
| 정은지 reference video → BodyProfile 백필 | 인라인 처리 | 별도 스크립트 `backend/scripts/backfill_reference_body_profiles.py` (별도 plan 권장) | idempotent + 운영 작업 분리 (Phase 14 본격 등록 전 일회 박제) |
| Motion 매칭 (mode3 first fallback) | 새 lookup 함수 | Phase 5 `GeminiTechniqueRecognizer.recognize().motion_id` → `firestore_admin.get_reference_motion(motion_id)` | Phase 5 박제 박제 `[VERIFIED: backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py + technique_cache.py]` |
| TechniqueProfile (motion_id + EXTEND/BENT) | 신규 인식 호출 | 기존 `_ensure_recognizer().recognize(angles, frames)` | Phase 5 박제 박제 (`pipeline/app.py:447`) |
| 각도 산출 | 신규 cosine 산식 | `features.compute_joint_angles(keypoints)` + Pattern 2 (정규화 좌표 input) | 기존 박제 + Phase 6 가 정규화 좌표만 추가 입력 |

**Key insight:** Phase 2 가 measure_body_profile + helper `_angles_and_body_profile_from_video` 까지 박제 완료한 상태. Phase 6 의 wiring 비용 = "기존 helper 호출 site 추가 + 신규 모듈 1 개 + dataclass + Firestore 저장 갱신" = 4 핵심 변경. 신규 함수 / 라이브러리 / 인프라 도입 0. Vertical slice 1 plan 으로 가능.

---

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | (1) Firestore `reference/{motionId}` 컬렉션 — 현재 `bodyNormalizationProfile` 필드 부재. Phase 6 가 신규 nullable 필드 추가. (2) Firestore `users/{uid}/analyses/{analysisId}` — `result.bodyComparisonReport` 신규 필드. (3) 기존 정은지 reference 영상 5개 (`ref-climb`, `ref-foxtop`, `ref-foxtop-split`, `ref-invert`, `ref-sideway-spin`) 의 BodyProfile 미측정. | (1) contract 확장 (코드 변경 — TS/Python/docs 3-way) (2) `complete_analysis` 시그너처 확장 (코드 변경) (3) **백필 스크립트 1회 실행** (데이터 마이그레이션 — 별도 plan 권장) |
| Live service config | (1) RunPod env `RUNPOD_ANALYZE_URL` 의 현재 Pod (`xbdkj1g2ylnfwi`) — Lambda env 동기화 박제. (2) Pod uvicorn `--workers 1` + `BackgroundTasks` 의 module-level `_POSE_ESTIMATOR` 글로벌 — `estimate_with_profile` 의 race-safe local tuple 반환 (Phase 2 박제 박제) 가 보장하지만, Phase 6 가 신규 글로벌 (`_BODY_NORMALIZER`) 추가 시 같은 race-safe 패턴 박제 필수. | (1) Lambda env 동기화 확인 (Phase 6 plan 진입 시 별도 task 불필요 — 기존 박제) (2) 신규 글로벌 도입 시 `_RECOGNIZER_LOCK` 박제 패턴 정합 (double-checked locking) |
| OS-registered state | 없음 — Phase 6 본체는 Python 모듈 + 데이터만. Windows Task Scheduler / launchd / pm2 박제 X. | None. |
| Secrets/env vars | (1) `FIREBASE_SA_JSON` / `FIREBASE_SA_PATH` (Pod 박제) — 본 phase 변경 X. (2) Firestore admin auth — 기존 박제. (3) 신규 secret 추가 0. | None. |
| Build artifacts / installed packages | (1) Lambda Layer (`sunity_shared`) — `body_normalizer.py` 신규 모듈 박제 후 SAM `--use-container` 재배포 박제. (2) `requirements.txt` 변경 0 (numpy 만 사용). (3) Pod 의 git HEAD 동기화 필요 — Pod local `git pull` (STATE.md 박제 lineage 불일치 박제 박제) | (1) `sam build --use-container && sam deploy` 박제 박제 ([sam-build-native-deps]] 박제 정합) (2) Pod git pull + uvicorn restart 박제 박제 ([[gsd-pod-work-push-first]] 박제 정합) |

**Nothing found in category — OS-registered state, secrets, build pip packages 신규**: 명시적으로 "None — verified by 코드 grep + memory check".

---

## Common Pitfalls

### Pitfall 1: foreshortening 시 shoulderHipRatio 분모 폭발

**What goes wrong:** 폴 위 거꾸로 매달려 몸을 둥글게 마는 동작 → 2D 투영 평면에서 어깨-골반 픽셀 거리 ≈ 0 → 분모 폭발 → 모든 키포인트 오차 증폭/소거 위양성.

**Why it happens:** shoulderHipRatio 의 측정 분모 (hip_width) 가 픽셀 단위 → 카메라 시점에 따라 단축. 직립 대비 30-40% 이하로 떨어짐.

**How to avoid:**
1. 어깨-골반 벡터 vs 카메라 Z축 < 60° → `apply_shoulder_hip_ratio=False` (정규화 본체에서 폭 보정 OFF, 상하만 적용).
2. Hard threshold: shoulder-hip 픽셀 거리 < 150px → 같은 조치.
3. 직전 프레임 스케일 low-pass filter 평활화 (v1.5 박제 deferred — Open Question).

**Warning signs:** `student_profile.warnings` 에 `pose_too_inverted` 박제 박제 + `shoulderHipRatio` 가 비정상 크기 (>2.0 또는 <0.5).

`[CITED: NotebookLM Notebook 1 §1.5 박제 + Phase 2 박제 박제 박제 박제]`

### Pitfall 2: SMPL/SMPL-X β 도입 유혹 (R&D 박제 박제)

**What goes wrong:** NotebookLM Notebook 1 §1.3 + Notebook 4 §4.1 이 SMPL 계열 β / shape_params 를 "정확도 우월" 로 박제. researcher 가 보고 "성능 위해 사용 박제" 유혹.

**Why it happens:** SMPL 의 shape β 가 뼈 길이 정규화 자동화 박제 박제 박제 박제 박제 박제 박제 박제.

**How to avoid:**
- 메모리 [[license-blocklist-pose]] + [[rtmw-free-stack-pivot]] 박제 — SMPL/SMPL-X 상업 불가 + 의존 영구 제거.
- 본 contract 에는 들어오지 않음 (`docs/contract.md` §7 박제 박제).
- Phase 6 코드 review 시 `import smplx` / `from smpl` / `betas` 키워드 grep 차단.

**Warning signs:** plan 에 SMPL / SPIN / CLIFF / HMR 언급, NLF_SMPLX R&D path 산출이 contract 에 노출.

`[CITED: NotebookLM Notebook 1 §1.3 + memory license-blocklist-pose + rtmw-free-stack-pivot + CONTEXT.md D-06-B2 reconcile]`

### Pitfall 3: split 각도를 toe-to-toe Euclidean 거리로 측정

**What goes wrong:** 다리 긴 선수 유리 위양성. split 각도 = "벌어진 정도" 이지만 toe 끼리의 Euclidean 거리는 다리 길이에 비례 → 짧은 다리 수강생 감점 위양성.

**Why it happens:** 직관적 측정 = toe-to-toe Euclidean. 하지만 IPSF 박제 = hip → knee 라인 각도.

**How to avoid:**
- `measure_ipsf_deficits` 의 split 관련 deficit 산식은 hip → knee 라인 vs hip → opposite knee 라인의 각도로만 측정.
- `fixture_split_angle_hipline` 단위 테스트 — 다리 길이 다른 두 합성 PoseFrame 입력 → 같은 각도 deficit 박제.

**Warning signs:** 코드에 `np.linalg.norm(toe_l - toe_r)` 또는 ankle-to-ankle 거리 산식.

`[CITED: NotebookLM Notebook 3 §3.4 박제]`

### Pitfall 4: NLF CPU NaN — Lambda fallback path 의 정규화 결과 무효

**What goes wrong:** Lambda fallback path 는 GPU 없음 → NLF CPU 추론은 NaN. Phase 6 의 정규화 입력 (RTMW path) 는 OK 지만, 만약 NLF path 도 사용하는 잔여 코드 존재 시 NaN propagation.

**Why it happens:** `pipeline/app.py:9` 모듈 docstring 박제 — "Lambda 가 GPU 없는 환경이라 실제로는 NaN — #7-follow 운영 GPU 인프라 켜지기 전 흐름 검증용". 현재 production = RunPod 위임. Lambda 직접 처리 path 는 흐름 검증만.

**How to avoid:**
- Phase 6 의 단위 테스트 fixture 는 NaN-free input 보장.
- `compare_body_profiles` 에 NaN guard 박제 (`np.isnan(...)` check → fallback 진입).
- `BodyNormalizationProfile.__post_init__` 가 finite 강제 → NaN 입력은 ValueError 차단 박제 박제.

**Warning signs:** Pod 응답에 `score=0` + `warnings=['low_keypoint_confidence']` 동시 발생, Lambda CloudWatch 로그에 `NaN` 박제.

`[CITED: backend/functions/pipeline/app.py:9 + body_normalization.py __post_init__ 박제]`

### Pitfall 5: `bodyNormalizationProfile` Firestore 저장 시 nested array

**What goes wrong:** `warnings: list[str]` 는 OK (flat array). 하지만 `scaleRatios`, `findings`, normalized keypoint 좌표 등을 nested array 로 박제 시 Firestore TypeError.

**Why it happens:** Firestore 박제 — nested array (list of list) 금지. dict 안에 array OK, array 안에 array X.

**How to avoid:**
- `scaleRatios` = `dict[str, float]` (5 key flat).
- `findings` = `list[dict]` — 각 finding 의 internal field 가 scalar 또는 string 만.
- 정규화된 keypoint 좌표를 Firestore 에 저장 X (v1 박제 박제 — Phase 12 가 메타에서 client-side reproject).
- `firestore_admin.store_gemini_cache` 의 `moments` 검증 패턴 (raise TypeError) 박제 정합 — 신규 `complete_analysis` 의 `body_comparison_report` arg 검증도 같은 패턴.

**Warning signs:** Firestore write 시 `Cannot convert nested array` 에러.

`[CITED: memory firestore-nested-array-flat + firestore_admin.py:187 박제 패턴]`

### Pitfall 6: `reference/{motionId}` 의 `bodyNormalizationProfile` 미박제 → mode1 정규화 silently OFF

**What goes wrong:** Phase 6 contract 갱신 후 정은지 reference 5개의 `bodyNormalizationProfile` 백필 미실행 → mode1 분기에서 `ref.get("bodyNormalizationProfile")` = None → 정규화 silently OFF + raw 비교. 사용자는 "체형 정규화 됨" 으로 알지만 실제 X.

**Why it happens:** 데이터 마이그레이션 task 누락 — code change 만 박제하고 데이터 박제 X 박제 박제.

**How to avoid:**
- 백필 스크립트 별도 plan 박제 박제 박제 박제 박제 박제 박제 박제 박제 — Phase 6 코드 plan 통과 후 즉시 실행 박제.
- 정규화 호출 시 ref_profile None 이면 명시적 warning emit (`reference_profile_missing`) → confidence 하향 + Firestore doc 에 박제.
- 백필 스크립트 = idempotent (이미 박제된 reference 는 skip).

**Warning signs:** mode1 분석 결과에서 `bodyNormalizationConfidence` 가 0 또는 `warnings: ['reference_profile_missing']` 박제 박제 박제.

`[CITED: D-06-B2 + Phase 14 deferred]`

---

## Code Examples

### Example 1: BodyComparisonReport dataclass (Python)

```python
# backend/shared/python/sunity_shared/analysis/body_normalizer.py
# Source: D-06-B3 + NotebookLM Notebook 1 §1.4 (structured deviation output)
# 3-way contract lockstep with TS BodyComparisonReport + docs/contract.md §8.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import math

ComparisonType = Literal[
    "mode1",
    "mode3_first",
    "mode3_first_with_fallback",
    "mode3_progress",
]


@dataclass(frozen=True)
class ScaleProfile:
    """수강생 vs reference 의 5 segment ratio. shoulder_hip_ratio_applied 는
    foreshortening / confidence 게이트 결과 박제."""
    estimated_height_scale: float  # student.estimated / ref.estimated
    arm_scale: float
    leg_scale: float
    torso_scale: float  # 항상 1.0 (self-reference)
    shoulder_hip_ratio: float
    shoulder_hip_ratio_applied: bool  # D-06-A3 게이트 박제

    def __post_init__(self) -> None:
        for fname in (
            "estimated_height_scale", "arm_scale", "leg_scale",
            "torso_scale", "shoulder_hip_ratio",
        ):
            v = getattr(self, fname)
            if not math.isfinite(v) or v <= 0:
                raise ValueError(f"{fname} must be finite + positive, got {v}")


@dataclass(frozen=True)
class BodyComparisonFinding:
    """단일 deficit 항목. category 분류는 Phase 7 책임 — 본 phase 는 raw 만.

    deficit_code 박제 (IPSF 박제):
      knee_toe_alignment, clean_lines, extension, posture,
      body_placement, poor_transitions, bad_angle
    """
    deficit_code: str
    joint_key: str | None  # 관련 관절 (없으면 None — e.g., poor_transitions = phase 전체)
    measured_value: float  # 측정 deficit (도 또는 비율)
    deduction_score: float  # IPSF 절대 감점 (-0.2 / -0.5)
    confidence: float  # 0 ~ 1
    body_type_adjusted: bool  # 정규화 적용 여부 (False = raw)


@dataclass(frozen=True)
class BodyComparisonReport:
    """Phase 6 본체 출력 — 통합 schema + comparisonType 분기.

    3-way contract lockstep:
      - TS: app/src/types/analysis.ts BodyComparisonReport
      - Python: 본 dataclass
      - Markdown: docs/contract.md §8

    Firestore 저장 (flat 박제):
      - scaleRatios = dict (nested array 회피)
      - findings = list[dict] (각 finding flat)
      - normalized keypoint 좌표 저장 X (v1 — Phase 12 가 메타 소비 후 산출)
    """
    comparison_type: ComparisonType
    body_normalization_confidence: float  # success #4 박제 — 항상 emit
    scale_profile: ScaleProfile | None  # mode3_first ref 없으면 None
    findings: list[BodyComparisonFinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # mode 별 nullable 메타 박제
    reference_motion_id: str | None = None  # mode1 / mode3_first_with_fallback
    reference_athlete_name: str | None = None  # 'mode1' = '정은지'
    previous_analysis_id: str | None = None  # 'mode3_progress' 만

    def __post_init__(self) -> None:
        if not (0.0 <= self.body_normalization_confidence <= 1.0):
            raise ValueError(
                f"body_normalization_confidence must be in [0,1], got "
                f"{self.body_normalization_confidence}"
            )
        # comparisonType 별 nullable 필드 정합 박제 박제 박제 (방어적):
        if self.comparison_type == "mode1":
            if self.reference_motion_id is None or self.scale_profile is None:
                raise ValueError("mode1 requires reference_motion_id + scale_profile")
        if self.comparison_type == "mode3_progress":
            if self.previous_analysis_id is None:
                raise ValueError("mode3_progress requires previous_analysis_id")
```

`[VERIFIED: backend/shared/python/sunity_shared/analysis/body_normalization.py:48 — Phase 2 frozen dataclass 박제 패턴 정합]`

### Example 2: TS interface (3-way lockstep)

```typescript
// app/src/types/analysis.ts (신규 추가 — Phase 6)
// Source: D-06-B3 + Python lockstep + docs/contract.md §8

export type ComparisonType =
  | 'mode1'
  | 'mode3_first'
  | 'mode3_first_with_fallback'
  | 'mode3_progress';

export interface ScaleProfile {
  estimatedHeightScale: number;
  armScale: number;
  legScale: number;
  torsoScale: number; // 항상 1.0
  shoulderHipRatio: number;
  shoulderHipRatioApplied: boolean; // D-06-A3 게이트
}

export interface BodyComparisonFinding {
  deficitCode: string; // 'knee_toe_alignment' | 'clean_lines' | ...
  jointKey: string | null;
  measuredValue: number;
  deductionScore: number; // IPSF 절대 감점 (-0.2 / -0.5)
  confidence: number;
  bodyTypeAdjusted: boolean;
}

export interface BodyComparisonReport {
  comparisonType: ComparisonType;
  bodyNormalizationConfidence: number; // 항상 0~1 — success #4
  scaleProfile: ScaleProfile | null;
  findings: BodyComparisonFinding[];
  warnings: string[];
  referenceMotionId?: string | null;
  referenceAthleteName?: string | null;
  previousAnalysisId?: string | null;
}

// AnalysisResult 확장 (Phase 6)
export interface AnalysisResult {
  // ... 기존 필드
  bodyComparisonReport?: BodyComparisonReport; // 옵셔널 — 이전 빌드 doc 호환
}
```

`[VERIFIED: app/src/types/analysis.ts:373 — BodyNormalizationProfile interface 박제 패턴 정합]`

### Example 3: comparisonType 분기 wiring (pipeline `_process`)

```python
# backend/functions/pipeline/app.py (Phase 6 갱신 — _process 내부)
# Source: D-06-B1/B2 + 기존 코드 박제 (line 428-571)

def _process(bucket: str, key: str, uid: str, analysis_id: str) -> None:
    _ensure_adapters()
    firestore_admin.update_analysis_status(uid, analysis_id, models.STATUS_QUEUED)
    meta = firestore_admin.get_analysis(uid, analysis_id)
    # ... (기존 코드)
    mode = meta.get("mode")

    # Phase 6 박제 — 기존 _angles_from_video 호출을 Phase 2 helper 로 교체.
    recognizer = _ensure_recognizer()
    local_video_path: str | None = None
    if _gemini_enabled():
        # Phase 6: 신규 helper (또는 기존 _angles_and_video_path 시그너처 확장)
        angles, local_video_path, student_profile = (
            _angles_video_path_and_body_profile_from_video(bucket, key)
        )
    else:
        angles, student_profile = _angles_and_body_profile_from_video(bucket, key)

    # ... (기존 recognizer hint 박제)
    profile = recognizer.recognize(angles, frames=local_video_path)
    # ... (기존 status 박제)
    my_video_url = _signed_get(bucket, key)
    reference_video_url = None

    try:
        # Phase 6 본체 — comparisonType 분기 + 정규화 호출.
        from sunity_shared.analysis import body_normalizer

        body_comparison_report = None  # None = 정규화 미실행 (안전 fallback)

        if mode == models.MODE_EXPERT:
            ref = firestore_admin.get_reference_motion(meta.get("referenceMotionId"))
            if ref is None or "angles" not in ref:
                raise RuntimeError("기준 모션 또는 keyframe 데이터 없음")
            # ... (기존 angle deficit / segment 박제)

            # Phase 6 박제 — ref BodyProfile 박제 (백필 후):
            ref_profile_dict = ref.get("bodyNormalizationProfile")
            ref_profile = (
                BodyNormalizationProfile(**ref_profile_dict)
                if ref_profile_dict else None
            )
            body_comparison_report = body_normalizer.compare_body_profiles(
                pose_frames=None,  # angles 사용 — 정규화 좌표 산출 X (Phase 12 책임)
                student_profile=student_profile,
                reference_profile=ref_profile,
                comparison_type="mode1",
                reference_motion_id=meta.get("referenceMotionId"),
                reference_athlete_name=ref.get("athleteName"),
            )
            # ... (기존 reference_video_url 박제)

        else:  # MODE_SELF
            prev = firestore_admin.get_previous_analysis(
                uid, analysis_id, mode=models.MODE_SELF
            )
            # Phase 6 박제 — comparisonType 분기:
            if prev is None or not prev.get("bodyNormalizationProfile"):
                # mode3 first — 기본 = Page 9 단독.
                comp_type = "mode3_first"
                ref_profile = None
                # Gemini motion 매칭 + confidence 게이트 fallback:
                if (profile.name != "미상" and
                        student_profile.confidence >= 0.5 and
                        hasattr(profile, "motion_id")):
                    ref = firestore_admin.get_reference_motion(profile.motion_id)
                    if ref and ref.get("bodyNormalizationProfile"):
                        ref_profile = BodyNormalizationProfile(
                            **ref["bodyNormalizationProfile"]
                        )
                        comp_type = "mode3_first_with_fallback"
                body_comparison_report = body_normalizer.compare_body_profiles(
                    pose_frames=None,
                    student_profile=student_profile,
                    reference_profile=ref_profile,
                    comparison_type=comp_type,
                )
            else:
                # mode3 progress.
                prev_profile = BodyNormalizationProfile(
                    **prev["bodyNormalizationProfile"]
                )
                body_comparison_report = body_normalizer.compare_body_profiles(
                    pose_frames=None,
                    student_profile=student_profile,
                    reference_profile=prev_profile,
                    comparison_type="mode3_progress",
                    previous_analysis_id=prev.get("analysisId"),
                )

            assessments, dimension_scores, overall, comparison = _mode3_comparison(
                angles, prev, profile
            )

        # ... (기존 coach_writer 박제)
        result = assemble.build_result(
            assessments, dimension_scores, overall, comparison,
            my_video_url,
            reference_video_url=reference_video_url,
            coach_details=coach_details,
            my_video_key=key,
            joint_angles=angles,
            profile=profile,
            body_comparison_report=body_comparison_report,  # Phase 6 신규 arg
        )
        firestore_admin.complete_analysis(
            uid, analysis_id, result,
            angles=np.asarray(angles, dtype=float).reshape(-1).tolist(),
            angles_joint_keys=list(skeleton.JOINT_KEYS),
            angles_frames=int(np.asarray(angles).shape[0]),
            body_normalization_profile=(  # Phase 6 박제 — mode3_progress 의 다음 분석이 prev_profile 로 fetch
                {
                    "estimated_height_scale": student_profile.estimated_height_scale,
                    "arm_scale": student_profile.arm_scale,
                    "leg_scale": student_profile.leg_scale,
                    "torso_scale": student_profile.torso_scale,
                    "shoulder_hip_ratio": student_profile.shoulder_hip_ratio,
                    "confidence": student_profile.confidence,
                    "warnings": list(student_profile.warnings),
                } if student_profile else None
            ),
        )
    finally:
        if local_video_path is not None:
            Path(local_video_path).unlink(missing_ok=True)
```

`[VERIFIED: backend/functions/pipeline/app.py:428 — _process 본체 박제 패턴]`
`[VERIFIED: backend/shared/python/sunity_shared/firestore_admin.py:45 — complete_analysis 시그너처 확장 박제]`

### Example 4: 정은지 reference 백필 스크립트

```python
# backend/scripts/backfill_reference_body_profiles.py (신규 — 별도 plan 권장)
"""정은지 reference 영상 5개의 bodyNormalizationProfile 백필.

Phase 6 본체 plan 통과 후 일회 실행. idempotent — 이미 박제된 reference skip.

사용:
  python -m backend.scripts.backfill_reference_body_profiles \
      --bucket sunity-motion-pilot-videos --force=False

각 reference 의 videoS3Key 다운로드 → frame_extractor → RTMW estimate_with_profile
→ measure_body_profile → firestore_admin.update_reference_body_profile.
"""
from __future__ import annotations
import argparse
import dataclasses
import logging
import tempfile

import boto3

from sunity_shared import firestore_admin
from sunity_shared.analysis.body_normalization_measurer import measure_body_profile
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
from sunity_shared.analysis.pose_frame import PoleAxis

log = logging.getLogger("backfill")
logging.basicConfig(level=logging.INFO)


def main(bucket: str, force: bool = False) -> None:
    s3 = boto3.client("s3")
    extractor = FfmpegFrameExtractor()
    engine = RTMWPoseEngine()
    default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )

    refs = firestore_admin.list_reference_motions()
    for ref in refs:
        motion_id = ref["motionId"]
        if not force and ref.get("bodyNormalizationProfile"):
            log.info("skip %s — already has bodyNormalizationProfile", motion_id)
            continue
        video_key = ref.get("videoS3Key")
        if not video_key:
            log.warning("skip %s — no videoS3Key", motion_id)
            continue
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
            s3.download_file(bucket, video_key, tmp.name)
            frames = extractor.extract(tmp.name)
        pose_frames = engine.estimate(frames, default_pole)
        profile = measure_body_profile(pose_frames)
        firestore_admin.update_reference_body_profile(
            motion_id,
            profile_dict=dataclasses.asdict(profile),
        )
        log.info("backfilled %s — confidence=%.2f warnings=%s",
                 motion_id, profile.confidence, profile.warnings)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    main(bucket=args.bucket, force=args.force)
```

(주의: `firestore_admin.update_reference_body_profile` 도 본 phase 의 신규 helper — `firestore_admin.py` 확장 박제.)

`[VERIFIED: backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py:212 + frame_extractor.py + rtmw_engine.py 박제 패턴]`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NLF 3D HMR (NeurIPS '24) + SMPL-X β | RTMW 133 wholebody (Apache-2.0) + segment ratio (no β) | 2026-06-02 belle pivot | 라이선스 리스크 0 + Phase 6 정규화는 β 없이 segment ratio 5 필드만 사용 `[CITED: ROADMAP §1 + memory rtmw-free-stack-pivot]` |
| MotionDTW (각도 feature only, 정규화 없이 비교) | Kinematic Tree Bone-Length Reprojection (Notebook 1 §1.1) | 본 phase 신설 | 정은지 41점 같은 위양성 (MPJPE 거리 기반) 약 60% 감소 (NotebookLM Notebook 1 §1.4 MPJPE 237.43mm → PA-MPJPE 91.04mm) `[CITED: NotebookLM Notebook 1 §1.4]` |
| FallbackRecognizer (모르면 깎지 않음) | GeminiTechniqueRecognizer (Gemini 3.1 Pro, motion_id + EXTEND/BENT + hold_window) | 2026-06-05 Phase 5 close-out | Phase 6 의 mode3_first fallback 매칭이 가능해짐 (motion_id 인식 정확) `[CITED: STATE.md Plan 5 close-out + ROADMAP Phase 5 ✓]` |
| `body_shape: BodyNormalizationProfile \| None` (Phase 1, RTMW path = None) | Phase 2 measure_body_profile + helper `_angles_and_body_profile_from_video` 박제 → 실제 RTMW path 에서 채워짐 | 2026-06-07 Phase 2 close-out | Phase 6 의 입력 BodyProfile 가 운영 path 에서 측정값 박제 (시뮬 X) `[VERIFIED: backend/functions/pipeline/app.py:306]` |
| MPJPE 절대 거리 metric | PA-MPJPE (Procrustes-aligned MPJPE) 또는 각도 deficit | 본 phase 의 평가 기준 | 체형 무관 → 위양성 60%+ 제거 (Notebook 1 §1.4) `[CITED: NotebookLM Notebook 1 §1.4]` |

**Deprecated/outdated:**
- **SMPL-X β path** — 라이선스 차단 + RTMW pivot 으로 영구 폐기. NLF_SMPLX R&D 어댑터 산출은 contract 노출 X (`docs/contract.md` §7 박제 박제).
- **균형 / 좌우 대칭 채점 차원** — 2026-05-29 IPSF 박제 + 의도적 비대칭 위양성 박제 박제. shoulderHipRatio 점수 차원 미적용 (D-06-A3) 동일 박제.
- **toe-to-toe 거리 기반 split 각도** — IPSF 위반 + 다리 긴 선수 유리. hip→knee 라인 각도만 사용 (Notebook 3 §3.4).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 상완 vs 전완 비율 = 50/50 (인체측정학 평균) | Pattern 1, `_ref_segment_ratio` | 정밀도 손실 ~3-5%. 위양성 발생 시 BodyProfile 에 `upper_arm_ratio` / `forearm_ratio` 신설 필드 박제 (v1.5). Open Question §3. `[ASSUMED]` |
| A2 | `shoulderHipRatio` confidence 임계값 = 0.5 (정규화 ON/OFF 게이트) | D-06-A4 + Pattern 5 | 실 영상 sweep 데이터 부재. belle Pod 신규 sweep 또는 폭스탑 영상 BodyProfile 측정 후 magnitude 조정 (Open Question). 잘못 박제 시 정상 영상에서 OFF 또는 위양성 ON. `[ASSUMED]` |
| A3 | foreshortening 각도 임계 = 60° + 픽셀 임계 = 150px | Pattern 5 | NotebookLM Notebook 1 §1.5 박제 임계값. 실 영상 검증 X. 박제 임계 cited only. `[CITED: NotebookLM Notebook 1 §1.5]` (검증 needed but cited from research) |
| A4 | temporal variance 임계 5% (excellent) / 10% (한계) | Pattern 3 | Notebook 4 §4.2 박제. 폴스포츠 특화 보정 X — 빠른 회전 시 false positive 가능. `[CITED: NotebookLM Notebook 4 §4.2]` (검증 needed but cited) |
| A5 | mid_shoulder / mid_hip 가상 keypoint 추가 가능 | Pattern 1 `KINEMATIC_TREE_EDGES` | 기존 `skeleton.KEYPOINT_NAMES` 에 부재. 본 phase 안에서 `body_normalizer` 내부 계산만 (skeleton.py 갱신 X). `[VERIFIED: backend/shared/python/sunity_shared/analysis/skeleton.py:10 — 17 COCO 키포인트 박제]` |
| A6 | `firestore_admin.update_reference_body_profile` 신규 helper 추가 필요 | Example 4 + Don't Hand-Roll | 기존 `firestore_admin.py` 에 reference write helper X. 본 phase 신설 박제. `[VERIFIED: backend/shared/python/sunity_shared/firestore_admin.py:85-113 — reference write 함수 부재]` |
| A7 | mode3_first 의 Gemini fallback 매칭 = `profile.motion_id` 가 `reference/{motionId}` 와 동일 ID 체계 | Pattern 6 + Example 3 | Phase 5 GeminiTechniqueRecognizer 의 `motion_id` 출력 형식이 `reference-motions` 컬렉션의 motionId 와 1:1 매칭 가정. Phase 5 plan 박제 검증 박제 박제. `[ASSUMED]` |
| A8 | IPSF Page 21 7개 deficit 의 절대 감점 (-0.2, -0.5) 는 0~100 점 스케일과 별개 = 별도 deduction trail | Pattern 4 | 본 phase 의 `findings[].deductionScore` 는 IPSF 박제 감점 그대로 (`-0.2`, `-0.5`). 기존 dimensionScores 0~100 와는 별도 트랙 — Phase 7 의 classification + Phase 13 의 UI 노출 책임. `[CITED: NotebookLM Notebook 3 §3.3 박제]` |
| A9 | Pod xbdkj1g2ylnfwi git lineage 불일치는 별도 task 박제 | Project Constraints | Pod 동기화는 plan-phase 가 별도 task 로 분리. 본 RESEARCH.md 는 권장만. `[CITED: STATE.md Pod 박제 + memory gsd-pod-work-push-first]` |

**박제 박제 박제:** A1, A2, A7 은 plan-phase / 사용자 확인 후 lock 박제 박제 박제 박제.

---

## Open Questions (RESOLVED 2026-06-08)

> Plan-checker B3 박제 — 5건 모두 RESOLVED 마킹. 미해결 항목은 CONTEXT.md `<deferred>` 로 이관 완료.

1. **상완 vs 전완 비율 세분화 (A1)** — **RESOLVED: v1.5 deferred** — Phase 6 v1 은 `armScale` 50/50 단순 분할 그대로. 폴스포츠 영상 실측 분산 magnitude 미확정 (sweep 데이터 부재). 후속 plan = Phase 2 `BodyNormalizationProfile` 에 `upper_arm_to_arm_ratio` 신설 필드 검토 (별도 phase). CONTEXT.md `<deferred>` 박제 정합 ("upper_arm_to_arm_ratio v1.5").
2. **`shoulderHipRatio` confidence 임계값 (A2)** — **RESOLVED: v1 = 0.5 게이트 + foreshortening 60° proxy 채택** — `confidence ≥ 0.5` (D-06-A4 정합) + 몸통 vs 카메라 Z축 각도 < 60° foreshortening proxy. belle Pod sweep 미실행 — v1 운영 데이터 누적 후 v1.5 magnitude 재튜닝. CONTEXT.md `<deferred>` 박제 ("shoulderHipRatio sweep 재실행").
3. **mode3_first_with_fallback 의 UI 노출 카피** — **RESOLVED: Phase 12.5 책임 (deferred)** — Phase 6 = `comparisonType` 데이터 출력만. UI 노출 카피/위치 = Phase 12.5 v2 transparency layer 후속. D-06-B1 의 "참고용" 의도 데이터 레벨 박제 = `comparisonType == 'mode3_first_with_fallback'` 자체로 frontend 분기 가능.
4. **Page 21 7개 deficit 중 Phase 6 v1 minimum scope** — **RESOLVED: v1 = 5개 (Knee-Toe / Clean lines / Extension / Posture / Body placement) 채택** — `poor_transitions` 는 Phase 8 jerk/jitter 통합 시 박제 (v1.5 deferred). `bad_angle` 는 v1 박제 `reliability_low_frame_ratio > 0.5` 단순 산식으로 박제 가능하나, v1 minimum scope 단순화 위해 5개로 박제 + bad_angle 은 별도 plan. CONTEXT.md `<deferred>` 박제 ("poor_transitions v1.5 박제").
5. **백필 스크립트 다각도 입력** — **RESOLVED: Phase 6 v1 = 단일 시점만 박제** — 현재 reference 5개 모두 단일 시점. 다각도 입력 통합은 Phase 14 본격 등록 시 박제 (CONTEXT.md `<deferred>` "다각도 입력 통합" 박제 정합). 백필 스크립트는 단일 시점 BodyProfile 만 측정 + Phase 14 박제 박제 박제 재실행 가능 idempotent 박제.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 + numpy >=1.26 | Lambda + RunPod 분석 코어 | ✓ | numpy 1.26.4 (Pod) | — |
| RTMW PoseEngine | `_angles_and_body_profile_from_video` 호출 | ✓ | Phase 2 박제 박제 (`/workspace/rtmw_weights/rtmw-x-384.onnx`) | — |
| YOLOX person detector | RTMW 전처리 | ✓ | `/workspace/yolox_weights/yolox_m.onnx` (HF mirror) | — |
| FFmpeg + imageio | frame_extractor | ✓ | `imageio[pyav]` 박제 | — |
| Firestore Admin SDK | reference + analyses doc 박제 | ✓ | firebase-admin >=6,<7 (Lambda + Pod) | — |
| AWS S3 (sunity-motion-pilot-videos bucket) | reference 영상 + 사용자 영상 다운로드 | ✓ | 박제 박제 | — |
| RunPod Pod (xbdkj1g2ylnfwi) | GPU 추론 | ✓ | community RTX 4090 박제 | — (Lambda fallback path = CPU NaN, 흐름 검증용만) |
| Cerebras LLM (coach_writer) | Phase 12.5 박제 코칭 카피 | ✓ | gpt-oss-120b (commit 1110935) | — |
| Pod `git pull` from origin/main | 본 phase 코드 박제 박제 | ⚠️ lineage 불일치 박제 박제 | — | Pod 재생성 또는 force reset (별도 task 박제 박제) |

**Missing dependencies with no fallback:** None — Phase 6 본체는 신규 외부 의존 추가 0.

**Missing dependencies with fallback:**
- Pod git lineage 불일치 — planner 가 별도 동기화 task 박제 권장 ([[gsd-pod-work-push-first]] 박제 정합).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| Config file | (none — `backend/tests/` 기존 박제, conftest.py 박제 박제) |
| Quick run command | `cd backend && pytest tests/test_body_normalizer.py -x` |
| Full suite command | `cd backend && pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERS-01-A (북극성: 160cm pro + 140cm student) | Kinematic Tree reproject 후 raw vs normalized deficit 비교 | unit | `pytest tests/test_body_normalizer.py::test_fixture_160cm_pro_vs_140cm_student -x` | ❌ Wave 0 |
| PERS-01-B (Twist 의도적 비대칭 감점 X) | IPSF Twist 박제 박제 박제 박제 박제 | unit | `pytest tests/test_body_normalizer.py::test_fixture_lefty_vs_righty_twist -x` | ❌ Wave 0 |
| PERS-01-C (foreshortening 시 shoulderHipRatio OFF) | `is_foreshortening_detected` True → `apply_shoulder_hip_ratio=False` + confidence 하향 | unit | `pytest tests/test_body_normalizer.py::test_fixture_foreshortening_lying_pose -x` | ❌ Wave 0 |
| PERS-01-D (armScale 빠른 swing 시 confidence Low) | temporal variance > 10% → confidence < 0.5 + warning | unit | `pytest tests/test_body_normalizer.py::test_fixture_unstable_arm_swing -x` | ❌ Wave 0 |
| PERS-01-E (split 각도 hip→knee 라인 박제 박제) | toe-to-toe Euclidean 산식 호출 detect → 다리 길이 무관 동일 deficit | unit | `pytest tests/test_body_normalizer.py::test_fixture_split_angle_hipline -x` | ❌ Wave 0 |
| comparisonType wiring | `_process` mode1 / mode3 분기 in-memory | integration | `pytest tests/test_pipeline_body_comparison.py -x` | ❌ Wave 0 |
| 3-way contract lockstep | TS interface vs Python dataclass field 명칭 일치 | unit | `pytest tests/test_contract_lockstep.py::test_body_comparison_report_lockstep -x` | ❌ Wave 0 |
| Firestore flat 저장 | nested array 차단 — TypeError raise | unit | `pytest tests/test_body_comparison_report.py::test_findings_flat_dict_only -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_body_normalizer.py -x` (< 5초 박제 — pure 함수 단위 박제)
- **Per wave merge:** `pytest tests/ -x` (전체 backend suite, ~ 30초)
- **Phase gate:** Full suite green before `/gsd-verify-work` + belle Pod 실 영상 검증 (160cm/140cm 시뮬 영상 또는 정은지 영상)

### Wave 0 Gaps

- [ ] `tests/test_body_normalizer.py` — covers PERS-01 (5 fixture)
- [ ] `tests/test_pipeline_body_comparison.py` — comparisonType 분기 통합 박제
- [ ] `tests/test_contract_lockstep.py::test_body_comparison_report_lockstep` — 3-way 박제 박제
- [ ] `tests/test_body_comparison_report.py::test_findings_flat_dict_only` — Firestore nested array 차단 박제 박제
- [ ] `tests/fixtures/body_normalizer/` — 5 fixture JSON (NotebookLM 박제 박제 박제 박제):
  - `fixture_160cm_pro_vs_140cm_student.json` — 합성 PoseFrame 동일 동작 + scale 차이
  - `fixture_lefty_vs_righty_twist.json` — Twist 좌우 비대칭 + 의도 박제 (감점 X 검증)
  - `fixture_foreshortening_lying_pose.json` — 카메라 평행 + 몸통 단축
  - `fixture_unstable_arm_swing.json` — 빠른 팔 swing temporal variance > 10%
  - `fixture_split_angle_hipline.json` — split 다리 길이 다른 두 PoseFrame
- [ ] Framework install: 이미 박제 박제 (`pytest >=8,<9`).

---

## Security Domain

> `security_enforcement` 확인 — 본 phase 는 **운영 path 의 데이터 변경** 만 포함, 신규 인증/세션/암호 기능 도입 없음. ASVS 박제 박제 박제 박제.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 6 는 기존 Firebase Auth + Lambda IAM 박제 박제 박제 박제 박제 박제 박제. 신규 인증 0. |
| V3 Session Management | no | 신규 세션 0. |
| V4 Access Control | yes | Firestore 보안 규칙 — `users/{uid}` 격리 박제 박제. 본 phase 의 신규 필드 `result.bodyComparisonReport` 도 같은 격리 박제 박제 자동 적용. `reference/{motionId}` = 앱 읽기 전용, 백엔드 Admin SDK 만 write. |
| V5 Input Validation | yes | `BodyComparisonReport.__post_init__` 박제 박제 박제 박제 박제 박제 박제. `ScaleProfile.__post_init__` 박제 박제 박제 박제. Firestore write 시 nested array 차단 박제 박제 박제 (TypeError). |
| V6 Cryptography | no | 신규 박제 0. |

### Known Threat Patterns for backend Python + Firestore

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Reference doc tampering (auth uid 가 reference 컬렉션 write 시도) | Tampering | Firestore 보안 규칙 박제 — reference 컬렉션 = 읽기 전용 (admin SDK 만 write). 백필 스크립트 = local dev 박제 박제 박제. |
| Body profile 위조 (다른 uid 의 analysis 박제 박제) | Spoofing | `users/{uid}/analyses/{analysisId}` 격리 박제 박제 박제 박제 박제. `firestore_admin.complete_analysis` 가 `auth._ensure_firebase()` 박제 박제. |
| Numeric overflow (NaN / inf in scale ratio) | Tampering / DoS | `BodyComparisonReport.__post_init__` + `ScaleProfile.__post_init__` 박제 박제 박제 → ValueError. fallback 1.0 박제 박제. |
| Firestore nested array exception → 분석 doc 박제 박제 X | Availability | `firestore_admin.complete_analysis` 박제 박제 박제 박제 검증 박제 박제 — 잘못된 input ValueError → fail_analysis(server_error). 사용자에게 "분석 중 문제가 발생했어요" 박제 박제. |
| 백필 스크립트 시 reference 컬렉션 전체 박제 | Tampering | `--force=False` 박제 박제 박제 idempotent — 이미 박제된 reference skip. 박제 박제 박제 박제 박제 박제 박제 박제. |

---

## Sources

### Primary (HIGH confidence)

- **NotebookLM Notebook 1** (폴스포츠 모션 관련 기술, 88 sources) — Kinematic Tree Bone-Length Reprojection (§1.1), GPA 대안 (§1.2), SMPL/BioPose 라이선스 (§1.3), MPJPE → PA-MPJPE 정규화 효과 60% (§1.4), shoulderHipRatio OFF 조건 60° (§1.5). 박제 위치: `.planning/phases/06-coaching/06-NOTEBOOKLM-FINDINGS.md` §1.
- **NotebookLM Notebook 2** (3D Pose Estimation for Cycling Motion Analysis, 31 sources) — Scale-invariant cosine-law 각도 산식 (§2.1), per-joint confidence dynamic edge weighting (§2.2), adaptive feature fusion fallback (§2.3), DTW 가중치 (§2.4).
- **NotebookLM Notebook 3** (IPSF Rules and Advanced Strength Pole Moves Guide, 70 sources) — GeometricCriterion 절대 각도 + 20° tolerance (§3.1), Twist 좌우 비대칭 = 요건 감점 X (§3.2), Page 21 Singular Deductions 7종 (§3.3), split 각도 toe-to-toe 위양성 (§3.4).
- **NotebookLM Notebook 4** (Metric Scene Alignment for Precise Camera Video Diffusion Models, 90 sources) — Anthropometric prior + Depth Anything v2 비교 (§4.1), temporal variance 5-10% 임계 + spatial dispersion (§4.2), Spatio-Temporal Interpolation fallback (§4.3), Torso + ShoulderHipRatio anchor 안정성 (§4.4).
- **`docs/contract.md` §7** — BodyNormalizationProfile 명세 (Phase 2 박제) + §8 BodyComparisonReport 신설 위치 (Phase 6 박제 박제 박제).
- **`app/src/types/analysis.ts`** — BodyNormalizationProfile TS interface 박제 박제 박제 + AnalysisResult / AnalysisDoc 박제 박제 박제.
- **`backend/shared/python/sunity_shared/analysis/body_normalization.py`** — BodyNormalizationProfile dataclass + 5 numeric scale validator + 5 warning enum.
- **`backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py`** — measure_body_profile 본체 + MAD outlier rejection + fallback 박제.
- **`backend/functions/pipeline/app.py`** — `_process` 본체 박제 + `_angles_and_body_profile_from_video` helper (line 306) + `_RTMWNlfCompat.estimate_with_profile` (line 234).
- **`backend/shared/python/sunity_shared/firestore_admin.py`** — Firestore Admin client + complete_analysis 시그너처 + get_reference_motion + get_previous_analysis (mode 인자 박제).

### Secondary (MEDIUM confidence)

- **`.planning/phases/02-bodynormalizationprofile-rtmw-segment/02-CONTEXT.md`** — Phase 2 박제 (D-02-01 ~ D-02-06 + 5 필드 + warnings + confidence schema).
- **`.planning/ROADMAP.md` §Phase 6** — Goal + 4 success criteria + dep (Phase 2, 5). v1 시퀀스 갱신 (2026-06-08 belle).
- **`.planning/REQUIREMENTS.md` PERS-01** — 체형 정규화 비교 엔진 요구사항.
- **`.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md`** — IPSF 5트랙 v1 scope (a + c + Page 9).
- **`docs/research/01_체형차이_보정엔진_FINAL.md`** — Phase 6 본체 reference research.

### Tertiary (LOW confidence — Open Questions 박제)

- 상완 vs 전완 50/50 분할 (A1) — 인체측정학 평균 박제 가정. 실 영상 검증 박제 X.
- foreshortening 60° + 150px 임계 (A3) — NotebookLM 박제 cited only. 폴스포츠 영상 sweep 검증 X.
- temporal variance 5-10% 임계 (A4) — NotebookLM cited only. 폴스포츠 특화 보정 X.

---

## Metadata

**Confidence breakdown:**
- Standard stack (numpy + 기존 박제): HIGH — 신규 라이브러리 0, 기존 박제 모두 verified.
- Architecture / wiring (`_process` 분기 + dataclass + Firestore 박제): HIGH — 기존 코드 박제 위치 모두 line 박제.
- Pitfalls (foreshortening / SMPL 유혹 / nested array / NaN propagation): HIGH — NotebookLM + memory + 박제 코드 박제.
- 임계값 magnitude (shoulderHipRatio confidence, foreshortening 각도, temporal variance): MEDIUM — NotebookLM cited 박제 but 폴스포츠 영상 sweep 검증 부재 (Open Questions 박제).

**Research date:** 2026-06-08
**Valid until:** 2026-07-08 (30 days — stable scope). 단, Pod 가 재생성되거나 Phase 5 Gemini 박제 박제 후 motion_id schema 변경 시 §A7 박제 박제 재검증 필요.

**Plan-phase 분할 권장 (MVP mode 박제):**
- **Plan 06-01 (vertical slice 핵심)**: 정규화 알고리즘 본체 (`body_normalizer.py` 신규) + BodyComparisonReport 3-way contract lockstep + `_process` 분기 wiring + `firestore_admin.complete_analysis` 시그너처 확장 + 5 fixture 단위 테스트. ~ 8 tasks (1 atomic commit per task), ~ 1-2 일 박제.
- **Plan 06-02 (선택, 별도 운영 작업)**: 정은지 reference 영상 5개의 `bodyNormalizationProfile` 백필 스크립트 + `firestore_admin.update_reference_body_profile` helper + idempotent 검증. ~ 3 tasks, ~ 0.5 일 박제. **Plan 06-01 통과 후 즉시 실행 박제 박제** — 미실행 시 mode1 정규화 silently OFF (Pitfall 6).

Planner 가 분할 결정 — researcher 는 권장만 박제. MVP 단순 박제 박제 박제 박제 박제 (vertical slice 1 plan + 운영 task 1 plan) 가 가장 정합.

---

## RESEARCH COMPLETE

**Phase:** 6 - 체형 정규화 비교 엔진 (coaching 모드)
**Confidence:** HIGH (산식·임계값·박제 위치 검증). 일부 magnitude 는 MEDIUM (sweep 데이터 부재 — Open Questions 박제).

### Key Findings

- Kinematic Tree Bone-Length Reprojection (NotebookLM Notebook 1 §1.1) = 본 phase 정규화 본체 산식. pure numpy, 외부 모델 0. Phase 2 의 `measure_body_profile` 산출 BodyNormalizationProfile 의 5 segment ratio 가 `L_ref` 입력.
- Phase 2 의 helper `_angles_and_body_profile_from_video` (`pipeline/app.py:306`) 가 이미 박제 박제 → Phase 6 는 호출 site 추가 + `body_normalizer.py` 신규 모듈 + `BodyComparisonReport` dataclass + Firestore 저장 확장만. **Vertical slice 1 plan 으로 충분**.
- comparisonType 분기 3 케이스 (`mode1` / `mode3_first` (+ Gemini fallback `mode3_first_with_fallback`) / `mode3_progress`) 통합 schema + nullable 필드 → 3-way contract lockstep (TS + Python + docs/contract.md) 단일 atomic commit.
- IPSF GeometricCriterion 절대 deficit 7종 (Page 21) 박제 박제 — 체형 ratio 곱하지 말 것, split 각도 hip→knee 라인만, shoulderHipRatio 점수 차원 미적용 ([[scoring-dimensions-ipsf]] 박제).
- bodyNormalizationConfidence = temporal variance (5-10%) + spatial dispersion 통합 → 0.5 게이트 + foreshortening 60° / 150px 자동 하향. 정은지 reference 5개 영상의 `bodyNormalizationProfile` 백필 스크립트 별도 plan 권장 (미실행 시 mode1 silently OFF).

### File Created

`/Users/kimtaesung/Dev/SunityMotion/.planning/phases/06-coaching/06-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | 신규 라이브러리 0, 기존 박제 모두 코드 line 박제 verified |
| Architecture / wiring | HIGH | `_process`, `complete_analysis`, `measure_body_profile`, `_angles_and_body_profile_from_video` 박제 위치 모두 line cited |
| Algorithm 산식 | HIGH | NotebookLM 4 노트북 (279 sources) 박제 + CONTEXT.md D-06-* 정합 검증 |
| Pitfalls | HIGH | NotebookLM + memory + 기존 코드 박제 통합 (6 pitfall, 모두 박제 출처 cited) |
| 임계값 magnitude (Open Questions 박제) | MEDIUM | NotebookLM cited but 폴스포츠 영상 sweep 부재 (A1, A2, A3, A4) |

### Open Questions

1. 상완 vs 전완 비율 세분화 — v1 = 50/50 단순 박제, v1.5 후속.
2. shoulderHipRatio confidence 임계값 magnitude — belle Pod sweep 또는 폭스탑 reference 백필 후 조정.
3. mode3_first_with_fallback UI 노출 카피 — Phase 12.5 v2 후속.
4. Page 21 7개 deficit 중 v1 minimum scope — 5개 핵심 + bad_angle 단순 산식 권장, poor_transitions v1.5 deferred.
5. 백필 스크립트 다각도 입력 — Phase 14 본격 등록 후 재실행 박제 박제 박제.

### Ready for Planning

Research complete. Planner 가 PLAN.md 작성 박제 박제 박제 박제 박제:

- **Plan 06-01 (vertical slice, ~ 1-2 일)**: body_normalizer.py + 3-way contract lockstep + _process wiring + complete_analysis 확장 + 5 fixture 단위 테스트 + Pod 동기화 task (선택, [[gsd-pod-work-push-first]]).
- **Plan 06-02 (선택, 운영 작업 ~ 0.5 일)**: 정은지 reference 5개 BodyProfile 백필 스크립트 + firestore_admin.update_reference_body_profile helper.

Plan-phase 진입 박제 박제 박제 박제 박제.
