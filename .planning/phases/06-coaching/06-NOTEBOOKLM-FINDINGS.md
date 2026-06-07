# Phase 6 — NotebookLM Research Findings

**Gathered:** 2026-06-08
**Purpose:** gsd-phase-researcher 가 RESEARCH.md 박제 시 입력으로 소비. 4개 노트북 (88+31+70+90=279 sources) 의 핵심 발견 + CONTEXT.md 결정 (D-06-*) 과의 정합/충돌 명시.

> **읽는 법:** NotebookLM 답변은 외부 source 기반 산식·임계값을 제시한다. 본 phase 의 박제 결정 (D-06-A*, D-06-B*, D-06-U1) 과 충돌하는 항목은 §정합/충돌 표 박제. researcher 는 정합 항목은 그대로 reference, 충돌 항목은 CONTEXT.md 우선 + reconcile 박제.

---

## 1. 세그먼트별 정규화 알고리즘 (`normalizeByBodySegments`) — Notebook 1 폴스포츠 모션 기술

### 1.1 Kinematic Tree Bone-Length Reprojection (권장 산식)

골반(Pelvis)을 원점으로 하는 hierarchical kinematic tree 따라 root→leaf 순차 재투영:

```
1단계 (Root Centering):
    P_centered = P_raw - P_root_raw

2단계 (Bone Length Ratio Reprojection):
    parent P, child C 에 대해:
    C_norm = P_norm + (C_raw - P_raw) / ||C_raw - P_raw||₂ × L_ref(P, C)
```

- **방향 벡터는 보존, 뼈 길이만 reference 비율로 덮어씀**.
- root→leaf 누적 적용 → 신체 비율이 reference 와 완벽 일치.
- **CONTEXT.md D-06-A2 (방향 B: 프로 → 수강생 체형 좌표계) 정합**. `L_ref` = 수강생 BodyNormalizationProfile 의 세그먼트 길이.

### 1.2 대안 — Generalized Procrustes Analysis (GPA)

```
P_norm = s · P_raw · R + t
```

- 전체 scale + rotation + translation 동시 최적화.
- **한계:** 세그먼트별 길이 차이가 크면 부분 왜곡 발생 → kinematic tree 재투영이 정밀 비교에 더 적합.
- **사용처:** 평가 metric (PA-MPJPE) 정의에만 쓰고, 좌표 reproject 본체는 1.1 사용.

### 1.3 추천 reference 알고리즘 (비상업 OK, 단일 view 입력)

| 알고리즘 | 라이선스 | 특징 | 본 phase 적합도 |
|---|---|---|---|
| **SMPL 계열 (HMR/SPIN/CLIFF)** | 비상업 OK (commercial use 별도 협상) | shape β + pose θ 분리. β 강제 통일하면 뼈 길이 정규화 자동 | **부적합** — 메모리 [[license-blocklist-pose]] SMPL-X 상업 불가 + [[rtmw-free-stack-pivot]] SMPL/SMPL-X 의존 영구 제거. **사용 금지.** |
| **BioPose + NeurIK** | 비상업 R&D 가능 | OpenSim 기반 BSK (24 segment) — bone scale s + 회전 q^r 분리, anatomical constraint | **R&D reference 만** — 실 production 코드 통합 X (라이선스 미확정) |
| **MotionDTW (SportsGPT 방식)** | 비상업 | 각도 + 각속도 + 각가속도 feature vector (scale-invariant) | **현 stack 정합** — backend/.../motiondtw.py 박제 박제. 정규화 없이 각도만 비교해도 부분적 무효화 가능 — Phase 6 본체와는 다른 path. |

**박제 결정 (researcher 박제 권장):**
- 알고리즘 본체 = Kinematic Tree Bone-Length Reprojection (1.1) — pure numpy, 외부 모델 의존 0.
- BodyNormalizationProfile (Phase 2 박제) 의 5 필드 = `L_ref` 출처.
- SMPL 계열은 reference paper 인용에만 사용, 코드 통합 X.

### 1.4 정규화 효과 — Quantitative Evidence

- **MPJPE 237.43mm → PA-MPJPE 91.04mm** (MotionAGFormer/H3.6M, AthletePose3D val set 박제) — 약 60%+ 위양성 거리 오차 제거.
- 각도 deficit: 2-10도 범위로 수렴 (체형 무관, 동작 품질 본체).
- **정은지 41점 위양성 (CONTEXT.md 박제) → MPJPE 기반 거리 오차였을 가능성 → PA-MPJPE 또는 각도 deficit 로 전환하면 위양성 제거 박제.**

### 1.5 shoulderHipRatio 보정 OFF 조건

- **위양성/위음성 발생 시나리오:** 폴 위에서 거꾸로 매달려 몸을 둥글게 마는 동작 → 2D 투영 평면에서 어깨-골반 픽셀 거리 ≈ 0 → 분모 폭발 → 모든 키포인트 오차 증폭/소거 위양성.
- **OFF 조건 (Notebook 1 권장):**
  1. 어깨-골반 벡터 vs 카메라 Z축 (depth) 각도 < 60° → OFF (몸통이 카메라 시선과 평행, 픽셀 길이 직립 대비 30-40% 이하)
  2. Hard threshold 150mm
  3. 직전 프레임 스케일 Low-pass filter 평활화

**CONTEXT.md D-06-A3 박제 정합** — shoulderHipRatio 점수 차원 미적용 + confidence 낮을 때 자동 OFF.

---

## 2. 각도 deficit + Confidence 산출 — Notebook 2 3D Pose Cycling

> ⚠️ Notebook 2 의 답변은 본 노트북이 직접 다루지 않은 영역 (라이더 체형 보정 산식 + scale ratio 임계값) 에 대해 "제공된 소스 내 미포함" 명시. 아래는 noteboo 안 의 인접 발견.

### 2.1 Scale-Invariant 각도 산출 (cosine law)

```
θ = arccos(BA · BC / ||BA|| · ||BC||)
```

- joint B 의 각도 = 인접 segment 벡터 BA, BC 의 내적 / 크기 곱.
- **본 산식은 scale-invariant** — 뼈 길이가 달라져도 각도 자체는 불변.
- **CONTEXT.md `Universal Principle D-06-U1` 정합:** 각도 차원은 정규화 없이도 비교 가능 — 단, 비교 의미가 정확하려면 root-centered + bone-aligned 가 선행 필요 (1.1 의 reproject 후 각도 산출).
- 산식 자체는 `backend/shared/python/sunity_shared/analysis/dimensions.py` 박제 패턴과 정합.

### 2.2 가중치 기반 dynamic edge weighting (per-joint confidence)

```
w_ij = exp(-d²_ij / σ²) · (c_i · c_j) / Σ_k exp(-d²_ik / σ²) · (c_i · c_k)
```

- c_i = keypoint confidence (RTMW heatmap score)
- d_ij = i-j keypoint Euclidean distance
- σ = decay coefficient (학습/실측)
- **사용:** 가려진/저신뢰 keypoint 의 영향력을 자동 감쇠 → 정규화 + 채점에 propagate.

### 2.3 Adaptive Feature Fusion (Fallback)

```
α = (g + ε) / (2 + ε),  β = 1 - α
f_fusion = α · f_gcn + β · f_trans
```

- g = image quality score (Laplacian gradient variance + occlusion confidence 종합)
- 이미지 화질 좋을 때 α↑ (raw feature 가중), 가려짐/블러 시 β↑ (skeletal topology 가중)
- **본 phase 적용:** confidence 낮음 시 정규화 OFF + raw 비교 (D-06-A4 박제) → adaptive fusion 의 단순화 버전.

### 2.4 DTW 가중치 (정합)

```
D(i,j) = w_i · w'_j · ||f_i - f'_j||² + min{D(i-1,j), D(i,j-1), D(i-1,j-1)}
```

- 이미 backend MotionDTW (`motiondtw.py`) 박제 박제 — 본 phase 는 DTW 호출 후 정규화된 좌표를 input 으로 박제.

---

## 3. IPSF Code of Points 정합성 — Notebook 3 IPSF Rules

> **중요:** IPSF Code of Points 는 **절대 각도 기준 + 체형 차이 보정 없음**. 본 phase 의 정규화 출력이 IPSF 박제와 충돌하지 않도록 reconcile 필수.

### 3.1 GeometricCriterion 평가 — 절대 각도

| 항목 | 박제 |
|---|---|
| 각도 정의 | "inner thighs of the legs in alignment with hips to knees" — 골반-무릎 절대 각도 (IPSF CoP Page 17, 20) |
| 허용 오차 | **maximum 20° tolerance** (모든 선수 동일, 체형 무관) |
| 체형 보정 | **존재하지 않음** — 절대 기준 |

**CONTEXT.md 와의 정합:**
- 본 phase 는 IPSF 절대 기준을 그대로 박제하되, **정규화는 IPSF 기준 적용 전 키포인트 좌표 정렬**에만 사용.
- 즉, "정은지 reference 의 키포인트를 수강생 체형 좌표계로 reproject → reproject 된 reference 와 수강생 키포인트 모두 IPSF 절대 각도 산식 적용" — **각도 산출 단계는 정규화 무관.**
- 정규화의 역할 = MPJPE 류 거리 metric 의 위양성 제거 (정은지 41점 박제 대응).

### 3.2 좌우 비대칭 (shoulderHipRatio) 채점 처리

| 케이스 | IPSF 처리 |
|---|---|
| Twist (의도적 좌우 비대칭) | **요건 (감점 X)** — 어깨와 골반이 다른 방향 = 요구 자세 (IPSF Aerial CoP Page 91) |
| Rounded shoulders/back | **-0.2 감점** (IPSF Pole Sports CoP Page 21) |
| 일반적 좌우 폭 비율 | **채점 차원 아님** — 의도 여부가 핵심 |

**CONTEXT.md D-06-A3 박제 정합** — shoulderHipRatio 점수 차원 미적용 = IPSF 박제 정합.
- 단, shoulderHipRatio 는 **키포인트 reproject** (Phase 12 시각화) 에는 사용 OK — 좌표 변환 정확도 향상.

### 3.3 "All Components" Page 21 절대 감점 트랙 — IPSF CoP Singular Deductions

| Deficit | 감점 | 산식 |
|---|---|---|
| Knee-Toe Alignment | -0.2 | kneecap → big toe 180° 직선 정렬 실패 |
| Clean lines | -0.2 | 팔/다리 180° 미달 (fully extended 미충족) |
| Extension | -0.2 | 척추/목/손목 라인 굽거나 어깨 rounded |
| Posture | -0.2 | 불제어 움직임 + 잘못된 body alignment |
| Body placement | -0.2 | 폴 대비 잘못된 위치 |
| Poor transitions | -0.5 | 진입/탈출 거침 |
| Bad angle | -0.5 | 심판이 실행 각도 미관측 |

**본 phase 박제 (researcher 박제 권장):**
- 정규화된 keypoint → 위 7개 GeometricCriterion 별 absolute 측정 (각도/거리/직선성).
- 각 criterion 미충족 → 절대 deficit 차감.
- **체형 ratio 곱하지 말 것** — IPSF 박제 위반.
- 메모리 [[ipsf-5-track-scoring]] Page 9 트랙과 정합.

### 3.4 정당화 vs 위양성 — IPSF 박제 박제

- **정당화되는 감점:** "Fully Extended" 요건 미충족 시 체형 한계 무관 0점 처리 (IPSF Mid-Cycle Update Appendix 2023 Page 60).
- **위양성 시나리오 (시스템 결함):** split 각도를 "toe-to-toe" 유클리드 거리로 계산 시 다리 긴 선수 유리 — **본 phase 는 hip→knee 라인 각도 산식 박제 필수.**

---

## 4. Per-Segment Scale Ratio 안정성 — Notebook 4 Metric Scene Alignment

### 4.1 mm 단위 추정 산식 (Camera intrinsic 없는 경우)

| 방법 | 산식 | 본 phase 적합도 |
|---|---|---|
| Anthropometric prior | `L_mm = L_pixel × H_avg_mm / H_pixel` | Fallback 으로 OK. Size Korea 평균 (여 1600mm, 남 1750mm) |
| Depth Anything v2 + Huber loss | `s = argmin Σ ρ(\|s·S(p) - M(p)\|)` | 추가 모델 의존 — v1 skip, R&D reference |
| SMPL β 최적화 | `E = Σ w_j ‖π(J(θ,β); c) - j²ᴰ‖²` | **SMPL 사용 금지 (메모리 [[license-blocklist-pose]]) — 차단** |

**박제 결정:** v1 은 Anthropometric prior + 카메라 영상 기반 단순 추정. Depth/SMPL 류는 R&D reference 만.

### 4.2 Uncertainty 산출 — 두 가지 분산 기반

**A. Temporal Variance of Limb Lengths**

```
Variance = (1/T) Σ_t (J_{t,j} - mean(J_·,j))²
```

- 정상 시 인체 뼈 길이는 시간 불변 → 변동 시 깊이 추정 ambiguity.
- **임계값:** 프레임 간 뼈 길이 분산 > 전체 길이의 **5-10%** → 해당 세그먼트 confidence Low/0.
- **CONTEXT.md `bodyNormalizationConfidence` 산출 박제 후보** — 5 필드 각각 temporal variance 계산 → confidence aggregate.

**B. Spatial Dispersion (자기 가림 모호성)**

```
C_s(t) = (1/J) Σ_j ‖P_j(t) - P_centroid(t)‖₂
```

- 관절들이 중심에 뭉칠수록 (웅크림 자세) C_s ↓ → 깊이 모호성 ↑ → confidence weight w_j ↓.
- **본 phase 적용:** Phase 6 의 `bodyNormalizationConfidence` 산출에 통합 (per-frame → time-aggregate).

### 4.3 Fallback 전략 (Confidence 저하 시)

| 전략 | 적용 |
|---|---|
| Spatio-Temporal Interpolation | 일부 프레임 confidence 미달 → 선형 보간 (TEMP3D 박제) |
| SMPL mean shape prior | **사용 금지 (라이선스)** — 본 phase 는 anthropometric prior 회귀로 대체 |
| Biomechanical limits constraint | 세그먼트 각도/길이가 해부학 임계값 벗어나면 직전 프레임 값 고정 |

**CONTEXT.md D-06-A4 박제 정합** — confidence < 0.5 시 정규화 OFF + raw 비교 + warning. Spatio-temporal interpolation 은 BodyNormalizationProfile 측정 단계 (Phase 2 책임) 에서 처리됨 박제.

### 4.4 ⚠️ CONTEXT.md 와의 충돌 — 세그먼트 안정성 순위

Notebook 4 박제:
- **가장 robust:** Torso + Shoulder-Hip Ratio (rigid body, 변형 적음, 카메라 시점 변화에 강건)
- **불안정:** armScale + legScale (foreshortening — 깊이 정보 소실로 픽셀 길이 단축)
- **권장:** Torso + ShoulderHipRatio 를 anchor 로 global scale 산출

**CONTEXT.md D-06-A3 박제와의 정합:**
- D-06-A3 는 **shoulderHipRatio 를 점수 차원에서 미적용** (IPSF 박제 = 좌우 비대칭 채점 차원 아님) — Notebook 4 의 안정성 발견과 충돌하지 않음.
- **둘은 호환:** ShoulderHipRatio = 키포인트 reproject 의 anchor 로 사용 (Phase 12 시각화 메타) + 점수 차원 미적용 (IPSF 박제).
- **단, 본 발견은 D-06-A3 의 추가 박제 근거** — researcher 가 RESEARCH.md 에 "ShoulderHipRatio anchor 사용 + 점수 미적용" 박제 정밀화 권장.

**armScale/legScale foreshortening 대응:**
- D-06-A4 박제 정합 — confidence < 0.5 시 OFF.
- 추가 박제: 전면 view 에서 arm/leg foreshortening 시 confidence 자동 하향 — temporal variance > 10% 트리거.

---

## 5. CONTEXT.md 결정과의 정합/충돌 매트릭스

| CONTEXT.md 결정 | Notebook 박제 | 정합 여부 | reconcile |
|---|---|---|---|
| D-06-A1 (점수 보정 + scale ratio 메타) | Notebook 1 의 Kinematic Tree reproject 산식 | ✅ 정합 | scale ratio 메타 = 5 필드 그대로, 점수 보정 = PA-MPJPE 류 거리 metric 만 적용 (IPSF 절대 각도는 정규화 무관) |
| D-06-A2 (방향 B: 프로 → 수강생 좌표계) | Notebook 1 1.1 산식 | ✅ 정합 | L_ref = 수강생 BodyProfile, 변환 = 정은지 키포인트 |
| D-06-A3 (5 필드 + shoulderHipRatio 점수 미적용) | Notebook 4 의 ShoulderHipRatio anchor 안정성 + Notebook 3 의 IPSF Twist 박제 | ✅ 정합 | shoulderHipRatio = reproject anchor + 점수 미적용 — researcher 가 박제 강화 |
| D-06-A4 (mode + confidence 병행 게이트) | Notebook 4 의 temporal variance 임계값 5-10% + Notebook 2 의 adaptive fusion | ✅ 정합 | confidence 산식 = temporal variance + spatial dispersion 통합. 임계값 0.5 = 5-10% variance 매핑 |
| D-06-B1 (mode3 first Page 9 + 매칭 fallback) | Notebook 3 의 IPSF Page 21 Singular Deductions | ✅ 정합 | Page 9 absolute deficit 트랙 = Knee-Toe/Clean lines/Extension/Posture 7개 |
| D-06-B2 (reference-motions BodyProfile 박제) | Notebook 1 의 SMPL β 추출 | ⚠️ 라이선스 충돌 | SMPL 사용 금지 — 대신 RTMW PoseFrame → measure_body_profile (Phase 2 박제) 그대로 사용 |
| D-06-B3 (BodyComparisonReport schema) | Notebook 1 의 deviation structured output | ✅ 정합 | comparisonType + nullable 필드 = Notebook 1 의 "structured deviation information" 패턴 |
| D-06-U1 (confidence-tiered hybrid) | 4개 노트북 전부의 fallback 전략 | ✅ 정합 | 각도 산식 (scale-invariant) + temporal variance 임계값 + adaptive fusion + biomechanical constraint 모두 본 원칙 구체화 |

---

## 6. researcher 박제 권장 — RESEARCH.md 박제 시 필수 항목

> 본 findings 를 입력으로 받는 gsd-phase-researcher 는 RESEARCH.md 에 아래 항목을 박제 박제.

1. **Kinematic Tree Bone-Length Reprojection (§1.1)** — 본 phase 의 정규화 본체 산식. pure numpy 구현 박제. BodyNormalizationProfile (Phase 2 박제) 의 5 필드 = L_ref 입력.
2. **scale-invariant 각도 산식 (§2.1)** — `dimensions.py` 박제 패턴 정합. 정규화된 키포인트 → 각도 산출 → IPSF deficit 차감 순서.
3. **IPSF 절대 deficit 트랙 7개 (§3.3)** — 본 phase 의 점수 보정 출력 schema. Knee-Toe / Clean lines / Extension / Posture / Body placement / Poor transitions / Bad angle.
4. **shoulderHipRatio 처리 박제 (§3.2, §4.4)** — anchor 로 사용 + 점수 차원 미적용 + foreshortening 시 OFF (몸통 vs 카메라 Z축 각도 < 60°).
5. **bodyNormalizationConfidence 산출 산식 (§4.2)** — temporal variance (5-10%) + spatial dispersion 통합. 시간 aggregate.
6. **Fallback 전략 매트릭스 (§1.5, §2.3, §4.3)** — confidence 단계별 OFF 조건 + warning 카피.
7. **위양성 회피 박제 (§3.4)** — split 각도 산출 시 toe-to-toe 절대 금지, hip→knee 라인 박제.
8. **라이선스 차단 박제 (§1.3, §4.1)** — SMPL/SMPL-X 사용 금지. anthropometric prior + RTMW measure_body_profile 만 사용.

### Validation Architecture 박제 (Nyquist Dimension 8 박제)

researcher 는 RESEARCH.md 에 `## Validation Architecture` 섹션 박제 시 아래 fixture 박제 박제:

| Fixture | 내용 | Notebook 박제 |
|---|---|---|
| `fixture_160cm_pro_vs_140cm_student` | 정은지 (160cm reference) + 합성/실측 140cm 수강생 동일 동작 | §1.4 정규화 효과 (PA-MPJPE 60% 감소) 박제 |
| `fixture_lefty_vs_righty_twist` | Twist 동작 좌우 비대칭 (IPSF 요건) — 감점 X 박제 | §3.2 IPSF Twist 박제 |
| `fixture_foreshortening_lying_pose` | 카메라 시선 평행 + 몸통 단축 — shoulderHipRatio OFF 트리거 박제 | §1.5 OFF 조건 60° |
| `fixture_unstable_arm_swing` | 빠른 팔 swing — armScale temporal variance > 10% → confidence Low 박제 | §4.2 temporal variance 임계값 |
| `fixture_split_angle_hipline` | split 각도 산출 시 hip→knee vs toe→toe 비교 — 후자 위양성 박제 | §3.4 IPSF 박제 |

---

*Source notebooks (NotebookLM):*
- `6e7880e7-d781-40e6-bfc3-6bdcf56de5ee` — 폴스포츠 모션 관련 기술 (88 sources)
- `415b6b35-86cd-424a-bda9-9c9fa38586ac` — 3D Pose Estimation for Cycling Motion Analysis (31 sources)
- `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3` — IPSF Rules and Advanced Strength Pole Moves Guide (70 sources)
- `94e6602c-76eb-430a-a3c8-31efa24e8909` — Metric Scene Alignment for Precise Camera Video Diffusion Models (90 sources)

*박제 query 일자: 2026-06-08*
