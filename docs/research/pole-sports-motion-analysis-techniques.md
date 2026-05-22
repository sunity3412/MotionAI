# 폴스포츠 모션 분석을 위한 핵심 개발 기술 통합 정리

> **출처**: NotebookLM 노트북 `Metric Scene Alignment for Precise Camera Video Diffusion Models` (94e6602c-76eb-430a-a3c8-31efa24e8909) · 소스 90건 + 생성 보고서 2종
> **정리일**: 2026-05-22
> **대상**: SunityMotion (RN+Expo · AWS Lambda · YOLO11 → ViTPose-S → MotionDTW)
> **목적**: 폴스포츠의 격렬한 회전·뒤틀림·폐색·블러 환경에서도 정확한 3D 비마커식 모션 분석을 구현하기 위한 모든 기술 옵션과 적용 방안을 한 문서에 집약

---

## 0. 폴스포츠 비전 분석의 4대 난제

| 난제 | 폴스포츠에서의 발생 양상 | 영향 |
|---|---|---|
| **비균일 모션 블러** | 폴 축 회전 시 사지 끝단의 각속도 폭증 → 픽셀 단위 잔상 | 2D 키포인트 검출 실패, 좌표 지터링 |
| **자기 가림 (Self-Occlusion)** | 사지가 몸통/폴에 밀착해 100% 폐색이 1–2초 지속 | 단일 프레임 피팅 붕괴, 좌우 반전 오류 |
| **극단 유연 자세** | 척추 과신전, 다리 360° 분리 | 해부학적으로 비현실적 포즈로 수렴 |
| **장비-인체 동역학** | 폴 굽힘·뒤틀림이 인체 관절 토크에 직접 전이 | 단순 포즈만으로는 정량 코칭 불가 |

→ **결론**: 단일 모듈(예: ViTPose) 하나만으로는 부족. **블러 복원 → 2D 검출 → 2D-3D 리프팅 → 메쉬 피팅 → 시공간 보간**을 밀결합한 하이브리드 파이프라인이 필수.

---

## 1. 권장 통합 파이프라인 아키텍처

```
[다시점 또는 단안 비디오 입력]
         │
         ▼
A. 영상 복원 (Restoration)
   • DeblurGAN-v2 (MobileNet-DSC 백본, 4MB, 모바일 추론용)
   • Real-ESRGAN / SA-SU-ESRGAN (저해상도 관절 에지 복원)
   • Human from Blur (서브프레임 궤적 역산)
         │
         ▼
B. 2D 키포인트 검출 (Pose Detection)
   • ViTPose-S (현 스택) / ExtPose (ViT 확장 robust)
   • OpenPose (베이스라인)
         │
         ▼
C. 2D → 3D 리프팅 (Lifting)
   • PoseFormerV2 (DCT 주파수 도메인, 파라미터 −85.3% / FLOPs −64.8%)
   • CGFusionFormer (저연산 강건 3D)
   • ST-Transformer + RoPE + Bone Priors (BMVC 2024)
   • Adaptive Spatial-Temporal Complexity-Aware (MDPI 2025)
         │
         ▼
D. 메쉬 피팅 + 폐색 보간
   • SMPL-X + SMPLify-X (체형·표정·손가락까지 통합)
   • TEMP3D (BERT 스타일 비지도 motion prior, 최대 수십 프레임 폐색 복구)
   • DexAvatar (손-바디 동시 prior)
         │
         ▼
E. 다시점 융합 + 생체역학 계층
   • MAMMA + BEDLAM (합성 데이터셋 기반 다인 마커리스)
   • Multi-View Fusion + Biomechanical Modeling (IEEE 2024)
   • Kirchhoff/Cosserat 탄성 봉 + 다관절 강체 결합
   • CusToM (생체역학 임상 라이브러리) 연계 관절 토크 추정
         │
         ▼
F. 코칭 룰 엔진
   • Pole-arina Bi-LSTM (기예 분류 93.82%) + 기하 룰 엔진
   • DTW 기반 기준 모션 정합 (현 SunityMotion 스택과 정렬)
         │
         ▼
[실시간 오버레이 코칭 피드백]
```

---

## 2. 카테고리별 핵심 기술 상세

### A. 영상 화질 복원 (Restoration)

#### A-1. DeblurGAN-v2 — 비균일 모션 블러 제거의 표준
- **아키텍처**: Relativistic Conditional GAN + **Feature Pyramid Network 생성기** + 이중 스케일 판별기
- **백본 선택지** (도메인 목적에 맞춰 교체 가능):
  | 백본 | PSNR | SSIM | 특성 |
  |---|---|---|---|
  | Inception-ResNet-v2 | 29.55 dB | 0.934 | 최상위 정밀, 서버 추론용 |
  | MobileNet | 28.17 dB | 0.925 | 저전력 균형형 |
  | **MobileNet-DSC** | 28.03 dB | 0.922 | **4MB · 11~100× 고속 · 온디바이스** |
- **손실**: `ragan-ls` (Relativistic average GAN + Least Squares)
- **SunityMotion 적용안**:
  - 백엔드 Lambda → Inception-ResNet-v2 백본
  - RN 앱 온디바이스 사전 처리 → **MobileNet-DSC (4MB)**: ViTPose-S 입력 전 블러 프레임을 선제 복원하여 키포인트 손실률 ↓
- **GitHub**: `VITA-Group/DeblurGANv2`

#### A-2. Human from Blur — 서브프레임 궤적 역산
- 카메라-피사체 순방향 노출 과정을 모델링, **저차 다항식 기반 T_i (평행이동), R_i (회전) 변환 역산**
- 한 프레임의 모션 블러 안에서 서브프레임 인체 궤적을 재구성 → 60fps 미만 환경의 회전 기동에 특히 유효
- 인용: ICCV 2023, Zhao et al.

#### A-3. UPGS (Unified Pose-aware Gaussian Splatting)
- 동적 장면의 디블러를 가우시안 스플랫팅으로 통합 처리 (arXiv 2509.00831)
- 폴 주변 다시점 합성 시 블러 + 새 시점 동시 생성 가능

#### A-4. 6DoF-pose-aided Motion Deblurring
- 카메라 6DoF 자세 정보를 디블러 손실에 결합 → 카메라 자체 흔들림과 피사체 모션 블러를 분리 처리

#### A-5. Real-ESRGAN / SA-SU-ESRGAN + WOA
- 저해상도 관절 에지 복원에 효과 (26 dB → 35 dB까지 향상)
- 공간 어텐션을 손실 함수에 통합한 **SU-ESRGAN** + 고래 최적화 알고리즘(WOA)으로 백그라운드 노이즈 차단
- **주의**: GAN 아티팩트가 키포인트 검출을 오히려 저해할 수 있어, **조인트 특징 피드백을 디블러/SR 생성기 입력단과 손실에 직접 연동**하는 하이브리드 (Joint SR + Head Pose Estimation Feedback) 권장
- 관련 논문: "Joint Estimation of Camera Pose, Depth, Deblurring, and Super-Resolution" (ICCV 2017)

---

### B. 2D 키포인트 검출 (Pose Detection)

| 모델 | 폴스포츠 적합도 | 특징 |
|---|---|---|
| **ViTPose / ViTPose-S** | ★★★★★ | 현 SunityMotion 스택. ViT 백본, 2D 검출 F1 85% |
| OpenPose | ★★★ | F1 79.5%, 베이스라인 |
| **ExtPose** | ★★★★ | ViT 확장형, 강건·일관성 강화 (ICML 2025 Poster) |

- **SunityMotion 권장**: ViTPose-S 유지하되, ExtPose를 자기 가림 강건 시나리오 A/B 테스트 대상으로 검토

---

### C. 2D → 3D 리프팅 (Lifting Transformers)

폴스포츠는 시퀀스가 길고(F ≥ 81 프레임) 회전이 격렬해 시간 일관성이 핵심.

#### C-1. 오리지널 PoseFormer
- 공간-시간 트랜스포머의 시초 (arXiv 2103.10455)
- 한계: O(F²) 어텐션 비용

#### C-2. **PoseFormerV2 — DCT 주파수 도메인 (★ 최우선 도입 권장)**
- **핵심 통찰**: 인간 모션의 운동 에너지는 저주파에 집중, 키포인트 검출 노이즈는 고주파 → DCT 분해로 분리
- **수식**:
  ```
  X_DCT(u) = C(u) Σ x(t) cos[π/F (t + 1/2) u]
  ```
- **하이브리드 적응형 융합 (HAF)**: 로컬 시간 피처 + 전체 시퀀스 저주파 DCT 피처 결합
- **성과**:
  - MPJPE 31.3 mm (GT 기준)
  - **파라미터 85.3% 절감 / FLOPs 64.8% 절감 / 수용장 k×배 확장**
- **SunityMotion 적용안**: ViTPose-S 출력을 PoseFormerV2로 리프팅 → Lambda 비용 절감 + 모바일 동시 가능

#### C-3. CGFusionFormer
- **Compact Spatial Representation** → 저연산 강건 3D (PMC12526803)
- 모바일 RN 앱의 미리보기용 라이트 추론 후보

#### C-4. ST-Transformer + RoPE + Bone Priors
- BMVC 2024: 로터리 위치 임베딩 + 골격 prior
- 폴스포츠 같은 극단 자세에서 해부학적 제약 부여에 유효

#### C-5. Adaptive Spatial-Temporal Complexity-Aware (MDPI 2025)
- 입력 복잡도에 따라 계산을 가변 할당
- 회전 구간만 고연산, 정적 구간은 저연산 → 배터리 친화적

---

### D. 자기 가림 & 시공간 보간

#### D-1. **TEMP3D — Temporally Continuous 3D Pose Under Occlusion (★)**
- **BERT 스타일 비지도 트랜스포머 motion prior** `M`
- 사전 학습된 정상 운동 분포 → **레이블 없이도** 단일 시점 비디오에서 **수십 프레임 100% 폐색** 복구
- 폴스포츠의 1–2초 폐색 구간(폴에 사지 밀착)에 가장 직접적 솔루션
- arXiv 2312.16221

#### D-2. Self-Occluded Human Pose Recovery in Monocular Video
- University of East Anglia (Research Portal)
- 자기 가림 전용 단안 비디오 복구 알고리즘

#### D-3. MAMMA — Markerless & Automatic Multi-Person Motion Action Capture
- 합성 데이터셋 **BEDLAM** 기반 학습
- 분할 마스크 조건 + 전신 표면 랜드마크 → **마커식 골드 스탠다드급 정확도 (수동 보정 無)**
- arXiv 2506.13040
- 다인 그룹 폴 퍼포먼스 분석 시나리오에 적합

---

### E. 신체 메쉬 피팅 (SMPL-X 패밀리)

폴스포츠의 극단 자세에서 **점 단위가 아닌 표면(메쉬) 일관성** 필수.

#### E-1. SMPL-X
- **체형 β + 관절 회전 θ + 표정 ψ + MANO 손가락**
- 폴 댄스의 손 그립 정확도 분석에 결정적

#### E-2. SMPLify-X — 최적화 손실
```
E(θ, β, ψ, t) = E_J + λ_θ·E_θ + λ_β·E_β + λ_expr·E_expr + λ_int·E_int
```
- **E_J**: Geman-McClure 강건 잔차 + 신뢰도 가중치 (노이즈 키포인트 필터)
- **E_θ, E_β**: GMM/VAE 기반 prior로 과신전·해부학적 불가 자세 패널티
- **E_int**: 파트별 다차원 안전 캡슐 교차 밀도 → 사지가 몸통 침범하는 기하학적 오류 방지

#### E-3. DexAvatar
- 손-바디 동시 prior, 수화·미세 손동작 → 폴 그립 정밀 분석 응용 가능
- WACV 2026

#### E-4. Egocentric Whole-Body Human Mesh Recovery
- 1인칭 시점 prior 학습 → 액션 캠 환경 옵션

---

### F. 다중 시점 융합 (Multi-View Fusion)

| 방식 | 마커 | 관절각 오차 | 비용/유연성 | 비고 |
|---|---|---|---|---|
| VICON / Qualisys | 필수 | ≤ 1° (≤ 10 mm) | 매우 높음 / 낮음 | 골드 스탠다드 |
| **MAMMA / EasyMocap** | 무 | 평균 3°~16° | 낮음 / 매우 높음 | 다시점 권장 |
| Move AI | 무 | 상용 SaaS | 상용 / 중 | 빠른 PoC |
| Multi-View Fusion + Bio Modeling | 무 | 향상됨 | 중 / 높음 | IEEE 2024 |

- **SunityMotion 적용안**: 학원 환경에 카메라 2~4대 설치 시 **EasyMocap + MAMMA 학습 가중치** 조합 검토. 단안만 가능한 사용자 케이스는 TEMP3D 보간으로 보완.

---

### G. 카메라 제어 비디오 생성 (데이터 증강·시각화·합성 학습 데이터 생성용)

폴스포츠 학습 데이터는 희소하므로 **합성 다각도 영상으로 증강** → 강건 학습.

#### G-1. CameraCtrl / CameraCtrl II
- **Plücker 좌표 기반 광선 임베딩**:
  ```
  O = -Rᵀ·T
  d_(x,y) = R·K⁻¹·[x,y,1]ᵀ
  L_(x,y) = (O × d_(x,y), d_(x,y))     ∈ ℝ⁶
  ```
- → H×W×6 spatial embedding으로 카메라 궤적을 픽셀 단위 기하 정보로 주입
- **CameraCtrl II**: 자기회귀 클립 확장 → 6컷 이상 연속 다각도 합성 가능

#### G-2. CamI2V — Epipolar Attention
- 에피폴라 라인을 따라 어텐션 제약 → **3D 기하 정합 강제**
- ```
  F_ij = K_j⁻ᵀ · R_j · [t]_× · R_iᵀ · K_i⁻¹
  l_j  = F_ij · p_i
  ```
- Register token으로 폐색 영역 수치 안정성 확보
- TransErr 0.236, RotErr 0.041 rad, 일관성 +25.64%

#### G-3. UCPE (Unified Camera Positional Encoding)
- **Relative Ray Encoding**: `T_rw = T_wc · T_cr` → 글로벌 좌표 의존 제거 → 일반화 향상
- **Absolute Orientation Encoding** (latitude-up map) → 정밀 pitch/roll 제어
- CVPR'26, intrinsics/distortion/orientation 통합 제어
- GitHub: `chengzhag/UCPE`

#### G-4. RealCam-I2V — 메트릭 스케일
- **Depth Anything v2 (metric) + COLMAP/GLOMAP + ICP** 정렬 → 절대 스케일 카메라 제어
- ```
  T_metric = s · T_colmap
  ```

#### G-5. VD3D / MotionCtrl / Collaborative Video Diffusion / Video4DGen
- VD3D: 대형 DiT의 3D 카메라 제어
- MotionCtrl: 카메라 + 객체 모션 분리 통합 컨트롤러
- CVD: 멀티 비디오 동기 + Epipolar Attention
- Video4DGen: Dynamic Gaussian Surfels (DGS) → 4D 재구성

#### G-6. 상용 도구
- **Higgsfield Cinema Studio 2.0** — Hero Frame First + 광학 리그 (8~50mm)
- **Freepik/Magnific Change Camera** — 360° 실시간 인터랙티브
- **Kling 3.0 Motion Control** — 얼굴 ID + 신체 제스처 앵커링
- **AI Relight** — 시점 변화 시 조명 재계산

**SunityMotion 활용 시나리오**:
1. 정은지 선수 단안 영상 1개 → CameraCtrl II로 다각도 합성 → 학습 데이터 증강
2. 학원 수강생에게 "코치 시점" 가상 카메라 뷰 제공
3. 합성 데이터로 ViTPose-S 도메인 적응 학습

---

### H. 4D / 동적 가우시안 재구성

#### H-1. Video4DGen + Dynamic Gaussian Surfels (DGS)
- 비강체 모션을 가우시안 표면으로 표현 → 임의 시점 신규 뷰 렌더링
- Confidence-filtered 4D guidance로 미관측 영역 복구

#### H-2. 3DEgo
- 모바일/엣지 환경 3D 편집 (ECCV 2024)

#### H-3. RealX3D
- 다시점 시각 복원·재구성 벤치마크 (arXiv 2512.23437)
- 폴스포츠 평가용 벤치마크 후보

---

### I. 메트릭 스케일 정렬 파이프라인 (Spatial Calibration)

```
[Input Video]
    → SfM (COLMAP / GLOMAP) : 상대 R, T 추출
    → Depth Anything v2 (metric)  : 기준 프레임 metric depth
    → 3D Point Cloud 재투영
    → ICP (Point-to-Point) : COLMAP↔metric depth 정합
    → 스케일 팩터 s 산출
    → T_metric = s · T_colmap
    → Scene-Constrained Noise Initialization (디퓨전 시 정적 프리뷰로 초기 노이즈 정형화)
```

**SunityMotion 적용안**: 학원 카메라 환경의 절대 거리(폴 직경 50mm/45mm 기준) 정합 → 관절각·중심 이동거리 정량화에 직접 활용.

---

### J. 폴스포츠/장비 특화 — 생체역학 정량화

#### J-1. **Pole-arina (★ 도메인 직접 적용 가능)**
- TU Wien Katharina Scheucher 2025
- **Bi-LSTM 기예 분류기 93.82%** + 기하 룰 엔진
- 파이프라인:
  ```
  비디오 → 2D keypoint+mask → Bi-LSTM 분류 → 기하 규칙·관절각 → 교정 피드백
  ```
- SunityMotion의 MotionDTW 단계와 직접 비교/통합 가능

#### J-2. Kirchhoff / Cosserat 탄성 봉 동역학
- 폴 = **유연체 연속체 (Deformable Thin Rod)**, 굽힘·뒤틀림 비선형 허용
- 인체 = 다관절 강체 시스템
- 양자 접촉 경계 조건 + 비마커 모션 데이터 → 다음을 산출:
  - **압축력 벡터 각도**: 폴 접촉점 반작용력 vs. 폴 축방향 힘의 각도
    - 엘리트: ≤ 2° (탄성에너지 E_pole 최대 충전)
    - 하위: 4°~8° (에너지 손실 + 부상 위험)
  - 질량중심(COG) 흐름, 관절 토크
- 라이브러리: **CusToM** (임상 다체 동역학)

#### J-3. Pole Vault Biomechanics (참고 데이터)
- "Effect of Stored Elastic Energy in the Bending Pole" (MDPI)
- "Energy and pole ground reaction force contributions"
- PAOLI PhD Proposal (Pole vAulting OptimaL Interaction, MimeTic)
- "Evaluating markerless biomechanical analysis in a real-world pole vault competition" (PMC13028377)

#### J-4. Markerless Sports Analysis — World-Class Performance
- Tandfonline 2025 (2576412): 비디오 기반 마커리스의 잠재력 종합
- Boccia Disability AI Kinematic Analysis (MDPI Bioengineering): 보조 기술 정량 평가 사례

---

## 3. 평가 지표 (Evaluation Metrics)

### 3-1. 포즈 추정
| 지표 | 정의 | 폴스포츠 목표 |
|---|---|---|
| **MPJPE** | Mean Per-Joint Position Error (mm) | < 35 mm |
| **PA-MPJPE** | Procrustes 정렬 후 MPJPE | < 25 mm |
| **2D Keypoint F1** | 검출 정밀도 | > 85% (ViTPose 기준) |
| 관절각 오차 | 도(°) 단위 | < 5° (생체역학 목적) |

### 3-2. 영상 복원
| 지표 | 의미 |
|---|---|
| PSNR | 픽셀 SNR (dB) |
| SSIM | 구조 유사도 |

### 3-3. 카메라 제어 비디오 생성
| 지표 | 의미 |
|---|---|
| **TransErr** | 카메라 평행이동 오차 (낮을수록 ↑) |
| **RotErr** | 회전 오차 (rad) |
| **CamMC** | Camera Motion Consistency |
| **TSED** | Thresholded Symmetric Epipolar Distance |
| **FVD** | Fréchet Video Distance (비디오 품질·동역학) |

### 3-4. 동작 분류
- Bi-LSTM 정확도 (Pole-arina 기준 93.82%)
- DTW 거리 (현 MotionDTW 스택)

---

## 4. 모바일 엣지 배포 고려사항 (SunityMotion 매핑)

| 단계 | Lambda 서버 추론 | RN 온디바이스 |
|---|---|---|
| 블러 복원 | DeblurGAN-v2 Inception-ResNet-v2 | **DeblurGAN-v2 MobileNet-DSC (4MB)** |
| SR | Real-ESRGAN | (생략 또는 캐싱) |
| 2D Pose | ViTPose-S | MoveNet/BlazePose 미리보기 |
| 3D Lifting | PoseFormerV2 / CGFusionFormer | CGFusionFormer (저연산) |
| 폐색 보간 | TEMP3D | (생략, 결과만 푸시) |
| Mesh 피팅 | SMPLify-X | (생략) |
| DTW 비교 | FastDTW + 기준 모션 | FastDTW 가능 |

**핵심 트레이드오프**:
- iOS 16+ Core ML / Android NNAPI 환경에서 **MobileNet-DSC 4MB** 모델은 즉시 배포 가능
- PoseFormerV2의 **−85.3% 파라미터** → Lambda 콜드 스타트 단축에 결정적
- ExpoConfig + TensorFlow Lite / ONNX Runtime Mobile 권장

---

## 5. SunityMotion에 즉시 적용 가능한 개선안 Top 5

1. **ViTPose-S 입력 직전 DeblurGAN-v2(MobileNet-DSC) 사전 처리 삽입**
   - 폴 회전 구간 키포인트 손실률 ↓, 4MB 모델로 RN 앱 내장 가능
2. **MotionDTW 직전 PoseFormerV2 리프팅 단계 추가**
   - 2D 시퀀스 → 3D 좌표 변환 시 노이즈 지터링 제거
   - Lambda 추론 비용 64.8% 절감
3. **TEMP3D 통합으로 폐색 구간 자동 보간**
   - 정은지 선수 기준 모션에서도 폴 밀착 구간 안정화
4. **Pole-arina의 Bi-LSTM + 기하 룰 엔진 패턴 도입**
   - DTW 외에 기예 분류 + 자세 규칙 평가 레이어 추가
   - Cerebras LLM으로 자연어 피드백 변환 시 분류 결과를 prompt context로 사용
5. **다각도 합성 데이터로 데이터셋 증강**
   - CameraCtrl II / UCPE로 정은지 단안 영상 → 다각도 학습 데이터
   - 학원 환경 카메라 위치 편향 완화

---

## 6. 참고 자료 (90개 소스 핵심 인용)

### 6-1. 영상 복원
- DeblurGAN-v2 (ICCV 2019, Kupyn) — `VITA-Group/DeblurGANv2`
- Human from Blur (ICCV 2023, Zhao et al.)
- UPGS (arXiv 2509.00831)
- 6DoF-pose-aided motion deblurring (SPIE)
- Motion Deblurring of Faces (Sumam David, NITK)
- Joint Estimation of Camera Pose, Depth, Deblurring, and SR (ICCV 2017)
- Real-ESRGAN + WOA / SA-SU-ESRGAN (MDPI Remote Sensing)

### 6-2. 2D-3D Pose
- 3D Human Pose Estimation with Spatial and Temporal Transformers (arXiv 2103.10455)
- PoseFormerV2 (CVPR 2023, arXiv 2303.17472)
- CGFusionFormer (PMC12526803)
- ST-Transformer + RoPE + Bone Priors (BMVC 2024)
- Adaptive 3D Pose Spatial-Temporal Complexity (MDPI Electronics 2025)
- ExtPose (ICML 2025 Poster)
- Overview of 3D Human Pose Estimation (Tech Science Press CMES)
- Comparative Study of 3D Pose Algorithms using Monocular Cameras (Preprints.org)

### 6-3. 자기 가림 / Mesh
- TEMP3D (arXiv 2312.16221)
- Self-Occluded Human Pose Recovery in Monocular Video (UEA)
- SMPLify / SMPLify-X (Emergent Mind topics)
- DexAvatar (WACV 2026)
- Egocentric Whole-Body Human Mesh Recovery (arXiv 2605.08606)
- Reconstructing 3D Humans From Visual Data (UCF STARS)

### 6-4. 다시점 / 마커리스
- MAMMA + BEDLAM (arXiv 2506.13040)
- A Review of Human Pose Estimation Methods in Markerless Motion Capture (CAD Journal Vol 21)
- Move AI (https://move.ai/)
- Multi-View Fusion + Biomechanical Modeling on Markerless (IEEE Xplore 11204549)
- Unlocking the potential of video-based markerless motion analysis (Tandfonline 2576412, 2025)
- Evaluating markerless biomechanical analysis in pole vault (PMC13028377)

### 6-5. 카메라 제어 비디오 디퓨전
- CameraCtrl (ICLR 2025)
- CameraCtrl II (ICCV 2025, arXiv 2503.10592)
- CamI2V (arXiv 2410.15957)
- UCPE — Unified Camera Positional Encoding (CVPR 2026, GitHub `chengzhag/UCPE`)
- RealCam-I2V (arXiv 2502.10059)
- VD3D (ICLR 2025)
- Boosting Camera Motion Control for Video Diffusion Transformers (BMVC 2025)
- MotionCtrl (arXiv 2312.03641)
- Collaborative Video Diffusion (NeurIPS 2024)
- Video4DGen (arXiv 2504.04153)
- Controlling Space and Time with Diffusion Models (arXiv 2407.07860)
- Higgsfield Cinema Studio 2.0 / Kling 3.0 / Freepik Magnific Change Camera / AI Relight
- 3DEgo (ECCV 2024)
- RealX3D (arXiv 2512.23437)

### 6-6. 폴스포츠 도메인
- **Pole-arina (TU Wien, Scheucher 2025)** — repositum.tuwien.at
- PAOLI PhD Proposal (MimeTic, biomecanique.org)
- Effect of Stored Elastic Energy in Bending Pole (MDPI Biomechanics)
- Energy and pole ground reaction force contributions to pole vault (SciSpace)
- Boccia AI Kinematic Analysis (MDPI Bioengineering)

### 6-7. 데이터 / 벤치마크
- EgoXtreme (arXiv 2603.25135) — Egocentric Robust Pose
- BEDLAM (MAMMA 연계 합성)
- RealX3D — 다시점 복원 벤치마크
- 2D-to-3D Image Reconstruction in Agriculture (PMC13030611, 방법론 리뷰)

---

## 7. 변경 이력

- 2026-05-22: 초안 작성. NotebookLM 노트북 90개 소스 + 통합 보고서 2종(영문 카메라 모션, 한국어 폴스포츠 통합 아키텍처) 분석 기반.
