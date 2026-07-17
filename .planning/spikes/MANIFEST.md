# Spike Manifest

## Idea

**Phase 4 Camera Angle AI 4-way 비교 spike.** Sunity AI Coach (폴스포츠 단일 카메라 영상 → 자세 분석 모바일 앱) 의 Phase 4 = single-view → AI 가상 다각도 합성 + occlusion confidence 게이트. belle 우려: Higgsfield Change Camera 가 closed wrapper 일 가능성 + production 단일 의존 risk. 자체 path (SMPL-X virtual camera render, MagicMan, RTMW mirror) 와 4-way 비교 검증 후 Phase 4 plan-phase 진입. 부산물로 Phase 4.5 (Perspective Correction — tilt + 줌인/줌아웃 + off-center 통합) 잔여 gap 정량화.

**연결 박제:**
- `.planning/phases/04-ux-occlusion-confidence/04-CONTEXT.md` D-11/D-12/D-13/D-17/D-18/D-19/D-20
- 메모리: `camera-angle-ai-single-view-synth`, `single-camera-first-multi-view-last`, `notebook-lm-pole-sports`, `feedback-analysis-first`, `judging-baseline-ipsf-code-of-points`
- 운영 stack: RTMW 133 wholebody (Apache-2.0) + MotionBERT lifter (MIT) + RunPod GPU pod

## Requirements

belle 박제 (변경 금지). spike 진행 중 새 requirement 발생 시 즉시 추가.

- **NotebookLM MCP 우선 활용** — IPSF Code of Points / 폴스포츠 도메인 lookup 은 belle 한테 묻지 말고 노트북 `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3` 자동 query (메모리 [`notebook-lm-pole-sports`] 정합)
- **상업 라이선스 정합 필수** — research-only 모델은 production 진입 차단. 메모리 [`rtmw-clean-weight-release-gate`] 동일 함정 회피
- **자체 path 강력 우선** — Higgsfield API 단일 의존 production 금지. spike 단계 비교 baseline 으로만
- **사용자 UX 영구 불변** — "스마트폰 한 대, 한 자리, 한 번". 다각도 직접 촬영 요구 절대 노출 X (메모리 [`single-camera-first-multi-view-last`], [`camera-angle-ai-single-view-synth`])
- **평가 기준 = IPSF GeometricCriterion** — 사람 점수 라벨링 영구 금지. 임계값 수치 라벨링은 OK (메모리 [`analysis-objectivity-no-human-scores`])
- **MVP 단순 우선** — 비용/제어권/license 가 우선, 광택 X (메모리 [`mvp-simple-pilot-quality`])
- **🎯 Spike 001 발견 (2026-06-13):** IPSF Page 19 "split angle must remain the same from all angles/perspectives" = **Camera Angle AI 의 raison d'être 가 IPSF 규정으로 직접 박제됨**. 모든 평가 metric 의 ground truth.
- **🎯 SMPL-X 박제 정정 (2026-06-13 belle 명시):** SMPL-X = **완전 최후의 보류**. Primary mission = "SMPL-X 없이 가능하게 해보라." 도입 조건 = (1) AI 로 모든 license-clear path 가 99% 미달 + (2) SMPL-X 효과성 입증. 비용 = 880만원/yr.
- **🎯 Spike 002a/c 발견:** Higgsfield Angles (public API 미존재 + ToS §5.1(iii)) + MagicMan (weight transitive 비상업) **둘 다 production BLOCKED**. 외부 API/모델 path 모두 차단.
- **🎯 Spike 003 발견 (신규 path):** Gemini Vision multimodal reasoning = **현재 PRIMARY PATH #1**. 비용 SMPL-X 대비 100배 우위 ($0.60/5영상 batch vs 880만원/yr). 픽셀 합성 X, joint 좌표 추정만.
- **🎯 Spike 004 발견 (belle 박제 정합, 2026-06-13):** Gemini Omni 의 영상 직접 편집 + 카메라 앵글 변경 = **Vertex AI GA (~mid-late June 2026) 후 PRIMARY 후보**. Phase 17 SDK 동일 호환, Google ToS clean (DPA + zero-data-retention). 단 폴스포츠 motion clean-data 검증 gate 필수 (Motion Realism 4/5, "stylized risk"). belle 의 multimodal AI 트렌드 감각 정확.
- **🎯 Spike 005 발견 (belle 결정적 깨달음, 2026-06-13):** **"AI 영상 생성 불필요 — 수학적 가상 카메라 연산으로 사용자 인터랙티브 360° 가능"** → react-three-fiber + expo-three frontend viewer 로 RN Expo 통합. v2 deferred 박제한 "구글맵 스트리트뷰 뷰어" 가 **MVP 가능 박제로 승격**. Decoupling 4-stage 아키텍처 박제: Stage 1 분석코어 (Gemini 3.x) → 2 3D pose (RTMW) → 3 시각화 (R3F frontend / cylindrical mesh backend) → 4 영상생성 plug-in (Omni 출시 후).

- **🎯 2026-07-17 재개 박제 (Iteration 3):** Omni API 실물 출시 (`gemini-omni-flash-preview`, Gemini API+AI Studio 6/30, **$0.10/sec** — 추정 대비 2-6배 저렴). **오픈 대체재 등장으로 구도 변경 = 4-way bake-off**: Omni(API) vs ReCamMaster(Wan2.1/Apache, 단일영상→새 궤적 재렌더 = 태스크 그대로) vs NVIDIA GEN3C-Cosmos-7B(Open Model License 상업 OK, 3D cache = 환각 구조적 억제) vs PersPose PR(수학, 환각 원천 불가). 오픈 경로 = 과금 0 + SynthID 없음 + 학생 영상 인프라 내 유지.
- **🎯 GT-free 검증 프로토콜 확정 (NLM 2026-07-17):** 10건 게이트 측정 = 교차시점 관절각 MAE(IPSF Page 19 "split angle 시점 불변") + 시간축 가속도 스파이크 + 뼈길이 불변. 사람 점수 라벨링 0 정합. phase 22 VLM(Qwen3-VL 계열) = 생성 불가·**judge 역할** (기하 무결성/시간 일관성 1-5점).

- **🎯 belle 제품 방향 박제 (2026-07-17):** 카메라 앵글의 **점수 반영은 stretch goal** — "회전을 돌려보면 말했던 자세가 여기서 어긋난다" 수준의 올바른 분석이 되면 채점 보강 채택, 게이트 미달이면 강행 금지. **미달분은 phase 22 자체 VLM 학습 트랙과 동행** (도메인 파인튜닝으로 재도전). **폴백 확정 = "참고하세요 코너"**: 비채점 시각 기능으로 사용자가 각도를 직접 돌려보는 UX (Spike 005 R3F 수학 뷰어 + 합성 영상 후보) — 점수와 분리된 참고 콘텐츠로 노출.

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | dataset-eval-harness | foundation | 정은지 5영상 + IPSF rubric (NLM lookup) 위에 4-way 비교용 평가 harness 셋업 | ✓ VALIDATED | foundation, ipsf, nlm, eval |
| 002a | higgsfield-angles-api | comparison | Higgsfield Angles API 의 license/cost/약관 박제 + 실제 호출 검증 | ✗ INVALIDATED | external-api, closed-wrapper, novel-view, license-block |
| 002c | magicman-zero-shot | comparison | MagicMan license 검증 + 인체 NVS zero-shot 추론 품질 | ✗ INVALIDATED | human-nvs, license-gate, smplx, blocked |
| 002b | cylindrical-mesh-virtual-render | comparison | RTMW 3D → cylindrical humanoid mesh → 12 virtual camera render (SMPL-X 제거, license clear) | ✓ VALIDATED-SKELETON | self-path, cylindrical-mesh, license-clear, virtual-render |
| 002d | rtmw-mirror-baseline | comparison | 보정 없는 현 운영 stack 상한 정확도 박제 | ✓ VALIDATED-BASELINE | baseline, rtmw, mirror, operational-stack |
| 003 | gemini-vision-view-reasoning | standard | Gemini multimodal reasoning 으로 occluded joint 좌표 추정 (픽셀 합성 X). SMPL-X 없이 occlusion 보완 | ✓ VALIDATED-PROTOTYPE | gemini-vision, multimodal-reasoning, license-clear, low-cost |
| 004 | gemini-omni-view-editing | standard | Gemini Omni 의 영상 입력 → 카메라 앵글 변경 + 편집. Phase 17 SDK 호환, Vertex GA 후 PRIMARY 후보. clean-data gate 필수 | ⏳ VALIDATED-DEFERRED-VERTEX-GA | gemini-omni, video-editing, vertex-ai, deferred, hybrid-primary |
| 005 | frontend-3d-viewer | standard | RTMW 3D joints + react-three-fiber + expo-three frontend viewer. AI 영상 생성 없이 사용자 360° 인터랙션 가능. v2 deferred → MVP 가능 승격 | ✓ VALIDATED-ARCHITECTURE | frontend, 3d-viewer, react-three-fiber, expo, decoupling, user-interactive, mvp-viable |
| 004-iii | omni-gate-resume | resume(004) | Omni API 실물 스모크 + 10건 pose-consistency 게이트 (GT-free 3축) | ⚠ PARTIAL — 앵글/비용/동기 검증, 굴곡각 MAE 중앙 22.8°+뼈길이 CV 악화=채점 투입 부적격, 모더레이션 30%/10% 차단. 007/006 상대비교로 재판정 | gemini-omni, gate, partial, moderation-risk |
| 006 | perspose-pr-math-baseline | comparison | PR 수학 회전(픽셀 생성 0)만으로 재추론 개선 — 생성 대비 실익 판정 기준선 | ○ PLANNED | perspose, math, license-free |
| 007a | recammaster-wan | comparison | ReCamMaster(Wan2.1) 하한 측정 | ✗ ABANDONED — belle 지시(구모델→최신모델 대체) + Pod 쿼터 충돌, GEN3C 로 일원화 | recammaster, abandoned |
| 008 | wan27-videoedit-gate | comparison | Wan2.7-VideoEdit(DashScope, belle 키)가 동일 10건에서 자세 충실도 유지하는가 | ★ WINNER(닫힌 API 트랙) — MAE 중앙 9.9°(Omni 22.8°의 2.3배 우수), <10° 5/9, 워터마크 off 지원, 차단 10%, 참고코너 엔진 1순위 | wan2.7, dashscope, camera-angle, reference-corner |
| 007b | gen3c-cosmos-7b | comparison | GEN3C 3D-cache 카메라컨트롤이 동일 10건에서 자세 충실도 유지하는가 (GPU Pod 필요) | ○ PLANNED-POD | nvidia, gen3c, open-model, 3d-cache |

## Risk Order Rationale

1. **001 foundation** — 다른 spike 가 호출할 공통 평가 harness. 0순위.
2. **002a Higgsfield API** — 외부 의존성 가장 큰 가설. license/약관 차단 시 즉시 kill switch → 자체 path 비교 set 축소.
3. **002c MagicMan license** — research-only 추정. 일찍 검증해서 production 가능성 판정.
4. **002b SMPL-X virtual render** — belle 자체 path 강력 후보. 가장 검증 가치 큼.
5. **002d RTMW mirror baseline** — 현 운영 stack 상한. 비교 기준점.
