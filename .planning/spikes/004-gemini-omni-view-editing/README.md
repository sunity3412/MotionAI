---
spike: 004
name: gemini-omni-view-editing
type: standard
validates: "Given Gemini Omni 의 영상 입력 → 카메라 앵글 변경 + 편집 능력, when Phase 17 통합 위에 Vertex AI GA 후 호출, then Higgsfield 카테고리 + Google ToS clean + Phase 17 정합 PRIMARY path 후보"
verdict: VALIDATED-DEFERRED-VERTEX-GA
related: [003, 002a, 002b]
tags: [gemini-omni, video-editing, vertex-ai, deferred, hybrid-primary]
---

# Spike 004: Gemini Omni View Editing

## What This Validates

**Given** Gemini Omni 가 영상 입력 → 카메라 앵글 변경 + 조명 변경 + Generative Inpainting/Outpainting 가능 (DeepMind 2026-05-19 발표),
**when** Vertex AI API GA (~2026-Q3 추정) + Phase 17 통합 위에 호출,
**then** Higgsfield 카테고리의 영상 편집 path 가 Google ToS clean + Phase 17 SDK 동일 호환으로 PRIMARY 후보가 된다 (단 폴스포츠 motion clean-data 검증 gate 통과 필수).

> **belle 박제 (2026-06-13):** "Gemini Omni 와 Vision 의 결합으로 가능. 1년 전 출시 (2026-06-02 Google 발표). Omni 와 함께 활용 박제가 spike 003 에 없어서 물어보는 것." → 정정 박제 + spike 004 신설.

## Research

### Gemini Omni 사양 박제

| 항목 | 박제 |
|---|---|
| 입력 | text + image + video + audio multimodal 동시 |
| 출력 (Omni Flash) | **video 최대 10초 / 720p (1280×720)** — 차기 ~30초 예고 |
| 카메라 앵글 변경 | 공식 prompt guide 명시 — "shift the camera angle", "punch in / dolly zoom / oner", "over the shoulder" |
| 대화형 multi-turn | 이전 turn 의 character / lighting / scene 유지 ✓ |
| 조명 변경 | 자연어로 광원/색온도/방향 지정 ✓ |
| Generative Inpainting | 객체 교체, 배경 변경, material 변환 (단어 미사용, "대화형 edit" 으로 brand) |
| **SynthID 워터마크** | **강제 삽입** — 사용자 화면 노출 시 혼란 가능 |

### Vertex AI / Google Cloud platform 상태 (2026-06-13 정정 박제)

**Vertex AI 플랫폼 자체 = 이미 완전 GA** (Sunity Phase 17 에서 이미 사용 중 — `gemini-3.1-pro-preview`). belle 박제 정합. 이전 박제 "Vertex AI 미출시" = 잘못된 표현 → 정정.

**정확한 상태 (2026-06-13 fact-check):**

| 항목 | 상태 |
|---|---|
| Vertex AI 플랫폼 | ✅ 이미 완전 GA — Sunity 운영 중 |
| 소비자 채널 (Gemini app / Flow / YouTube Shorts) Omni | ✅ 이미 GA (2026-05-19 live) — belle 가 본 YouTube 영상 출처 |
| **Vertex AI Model Garden 의 Gemini Omni endpoint** | ⏳ **미등록** (어떤 model id 도 공개 catalog 없음) |
| Vertex AI 개발자 API (Omni) | ⏳ "coming weeks" — **mid-to-late June 2026 윈도우 (수 주 내 가능)** |
| AI Studio Omni | ⏳ 미등록 (통상 consumer launch 후 ~1개월) |
| 현재 production-ready 영상 path | ✅ **Veo 3.1 (Vertex paid preview)** — 단 image-to-video 위주, "기존 영상 → 다른 앵글" 부분 대체 |

**갱신 박제:** 1주일 전 "~2026-Q3 GA" 박제는 **부분 정정** — 소비자 GA 완료, Vertex API 는 여전히 미출시지만 **Q3 까지 갈 가능성 낮음. June~July 윈도우가 현실적** (이번 주~다음 주 출시 가능성도 미확정으로 존재).

### belle 이미지 박제 정합 (2026-06-13, Google blog.google + Google Cloud Documentation 공식 출처)

belle 가 2026-06-13 외부 공식 출처 박제. 위 fact-check 결과와 정합 + 추가 박제:

| 박제 항목 | belle 이미지 출처 | Sunity 적용 |
|---|---|---|
| Omni Flash 소비자 출시 | ✅ Gemini app / Flow / YT Shorts | Sunity SaaS 통합 부적합 |
| 개발자 API "수주 내" | ✅ Vertex AI + AI Studio | Spike 004 본 검증 대기 |
| **Gemini 2.5 Flash / Pro = Vertex GA, 멀티모달 비디오 처리** | ✅ Google Cloud Documentation | ⚠ Sunity 메모리 [[gemini-latest-model-versions]] "2.5 영구 금지" 박제 — Sunity 는 **3.x 동등 모델** 사용 (gemini-3.1-pro-preview / gemini-3.5-flash, 이미 Phase 17 운영) |
| **Veo 3.1 = Vertex Public Preview, 엔터프라이즈 영상 생성** | ✅ Google Cloud Documentation | **현재 (2026-06-13) 즉시 사용 가능 대안 #2** (이전 "backup" 박제 정정) — Phase 17 동일 DPA cover, image-to-video 위주이나 spike 004 의 conversational re-edit 부분 대체 |
| Omni API 오픈 시 model id | `gemini-omni-flash` (예시) + Gemini Enterprise Agent Platform 문서 업데이트 | 출시 시 즉시 spike 004 본 검증 진입 |

**Sunity 내부 박제 충돌 확인:** belle 이미지가 "Gemini 2.5" 박제했으나 Sunity 메모리 = "2.5 영구 금지, 3.x 사용" 박제. **이 정책 유지 시 동등 path = `gemini-3.1-pro-preview` / `gemini-3.5-flash` 사용** (Phase 17 운영 stack). belle 가 명시적 정책 변경 박제 없는 한 메모리 정책 유지.

### License + ToS

- Consumer tier = Google Workspace ToS, **상업 SaaS 분석 부적합** (학생 영상 학습 사용 정책 미확정)
- **Vertex AI GA 후:**
  - Enterprise DPA 가능 (Google Cloud account team)
  - **Zero-data-retention amendment 가능** — prompt/file/output 학습 비사용 명시
  - Enterprise ToS = Sunity SaaS 적합
- **Indemnification 필요** (VentureBeat 경고): generative video 학습 데이터 법적 status unsettled, 고객 대면 채널 배포 전 indemnification 문구 필수

### 비용 박제

| Plan | Cost | Sunity 적합도 |
|---|---|---|
| Consumer (AI Plus / Pro / Ultra) | $20-100/mo | ❌ SaaS 통합 부적합 |
| Vertex API (추정) | $0.20-0.60/sec output + token cost | ⚠ 10초 영상당 **$2-6** |
| 폴스포츠 영상 30~60초 분석 | 분할 호출 (3~6 calls) | ⚠ $6-36/영상 |

**비교:**
- Higgsfield: $15-129/mo + tier gate (production BLOCKED)
- **Gemini Vision reasoning (Spike 003): $0.12/video** — Omni 대비 50-300배 저렴
- Cylindrical mesh (Spike 002b): GPU cost only

### 폴스포츠 motion 적용성 — 핵심 리스크

| 검증 | 결과 |
|---|---|
| Fast Motion 벤치 (500 sports prompt) | 통과 — 단 평가는 *generation* 측 |
| Sunity 케이스 (사용자 영상의 앵글 변환) | ⚠ **정확히 일치 안 함** |
| Motion Realism | **4/5** (Seedance 2.0 = 5/5) |
| **"매우 high-energy / physics-intensive scene"** | **"stylized 로 단순화"** — 폴스포츠 회전/역수직/spin 동작이 정확히 이 카테고리 |
| **pose consistency 보장** | prompt guide **부재** — Sunity 의 "분석 정확도 절대 원칙" (CLAUDE.md core value) 직접 충돌 가능성 |

→ **clean-data 검증 gate 필수**: 폴스포츠 영상 10건 (회전 / 역수직 / spin 균등) 으로 pose consistency 정량 측정. `sensitivity-gate-not-just-elite-low` 메모리 정합.

### Sunity Phase 17 통합 path

- **SDK 호환 ✓** — Phase 17 의 `gemini-3.1-pro-preview` 와 동일 client (`google-cloud-aiplatform`). Omni Flash Vertex GA 시 **model id 추가만** 으로 호출 가능 (별도 endpoint X)
- **Objectivity 정합 ✓** — Omni 출력 = 편집된 영상 (점수 X). 보완된 영상 → 기존 RTMW 133 wholebody 적용 → joint 좌표 추출 → 기존 분석 pipeline. `analysis-objectivity-no-human-scores` 충돌 없음
- **Lambda vs RunPod** — Omni 호출 = 순수 HTTP API (GPU 무관) → **Lambda 직접 호출 적합**. RunPod 는 RTMW pose extraction 유지

### Veo 3.1 비교 (Bonus — belle 박제 "Generative Inpainting/Outpainting 최대 4K")

| 특성 | Gemini Omni Flash | Veo 3.1 |
|---|---|---|
| 모드 | conversational iterative edit | one-shot generation |
| 해상도 | 720p (10s cap) | 1080p native (Topaz 등 외부 upscale 로 4K) |
| Inpainting/Outpainting | 대화형 edit 으로 brand | 정식 지원 ✓ |
| **사용자 업로드 영상 편집** | ✅ 적합 | ⚠ 비공식 use case (prompt-based generation 위주) |
| Scene extension | — | ✓ |

**Sunity 카메라 앵글 변경:** **Omni 가 더 적합**. Veo 3.1 = backup (객체·프레임 확장에 강하나 "기존 인물 동작의 다른 시점 합성" 비공식).

## How to Run

Vertex AI GA 전까지 spike 자체 실행 불가. 박제 + roadmap 만.

```bash
# Vertex AI GA 후 (~2026-Q3):
# 1. Google Cloud project + Vertex AI API enable
# 2. DPA + zero-data-retention amendment 신청 (Google Cloud account team)
# 3. python3 run_spike.py (예정 — Omni model id 호출 + pose consistency 정량)
```

## Investigation Trail

### Iteration 1 — belle 박제 정합 + Vertex 미출시 발견 (2026-06-13)

**시도:** belle 의 "Gemini Omni 와 Vision 결합" 박제를 받아 Spike 003 보강.

**발견:**
- ✅ Omni 는 카메라 앵글 변경 능력 공식 박제 (prompt guide 명시)
- ✅ Phase 17 SDK 동일 호환 — 통합 cost 0
- ✅ Google ToS clean (Vertex enterprise DPA)
- ⚠ Vertex AI API 미출시 → 즉시 production 불가
- ⚠ 폴스포츠 motion "stylized risk" 카테고리 — pose consistency 미보장
- ⚠ 비용 $2-6/10초 vs Spike 003 reasoning $0.12/video → 50-300배 차이

**Pivot:** Spike 003 ("reasoning only, 픽셀 합성 X") 박제 유지 + Spike 004 신설 (Vertex GA deferred). HYBRID path.

### Iteration 2 — Vertex GA 후 (deferred ~2026-Q3)

- Vertex API enable + DPA 신청
- 폴스포츠 10건 (회전 5 / 역수직 3 / spin 2) Omni 호출 + 결과 영상의 RTMW 재추론
- pose consistency 정량 측정 — 원본 vs 편집된 영상의 joint 좌표 비교
- 비용 실측 vs 추정
- Spike 001 evaluate_4way 에 PathOutput 으로 wrap → 003 + 002b + 002d + 004 4-way 비교

## Results

### Verdict: **VALIDATED-DEFERRED-VERTEX-GA** ⏳

**근거:**
1. ✅ Omni 카메라 앵글 변경 능력 박제 (belle 박제 정확)
2. ✅ Phase 17 SDK 호환 + ToS clean (Vertex GA 후) + Sunity 분석 pipeline 정합
3. ⏳ Vertex AI API 미출시 → 즉시 production 불가, ~2026-Q3 GA 후 진입
4. ⚠ 폴스포츠 motion clean-data 검증 gate 필수 (회전/역수직 pose consistency)
5. ⚠ 비용 Spike 003 reasoning path 대비 50-300배 → 조건부 트리거 + Vertex GA 시기 정합

### Surprises / 박제 사항

- **belle 박제의 정확성:** "Omni 와 Vision 결합" 박제 = 맞음. 제가 Spike 003 에서 reasoning only path 만 박제한 게 누락. **belle 의 multimodal AI 트렌드 감각 정확.**
- **Vertex AI 미출시 = 즉시 production 차단:** consumer tier (Gemini app) 만 출시 — Sunity SaaS 통합 path 차단. ~2026-Q3 까지 대기.
- **폴스포츠 motion = "stylized risk":** Motion Realism 4/5, "high-energy / physics-intensive 단순화" 정의 = 폴스포츠 회전/역수직/spin 직접 적용. Sunity 의 "분석 정확도 절대 원칙" 과 직접 충돌 가능성. 실측 검증 전 정량 분석 ground truth 로 사용 불가.

### Carry-forward for Phase 4 plan-phase

**HYBRID PRIMARY path 박제 (2026-06-13 belle 이미지 박제 보강):**

| 우선순위 | Path | 시기 |
|---|---|---|
| #1 즉시 | Spike 003 Gemini Vision **reasoning** (joint 좌표 추정, gemini-3.1-pro-preview, 픽셀 합성 X) | 현재 PRIMARY |
| #2 즉시 | Spike 002b cylindrical mesh + virtual render (자체 path) | 현재 SECONDARY |
| **#3 즉시 (정정 박제)** | **Veo 3.1 (Vertex Public Preview)** — image-to-video / reference-image consistency. Phase 17 동일 DPA cover. "기존 영상 다른 앵글 재합성" 부분 대체 (Omni 의 conversational editing 보다 약하지만 즉시 가능) | **현재 secondary 즉시 가능** |
| baseline | Spike 002d RTMW mirror | 비교 기준 |
| **#4 deferred** | **Spike 004 Gemini Omni view editing** (영상 직접 편집, Phase 17 정합) | **Vertex API 출시 후 (June~July 2026 윈도우, 이번 주~수 주 내) PRIMARY 후보 — clean-data gate 통과 시** |
| 완전 최후의 보류 | SMPL-X mesh ($7,300/yr) | 모든 path 99% 미달 + 효과성 입증 시 |

**Spike 004 2-track 분리 (Agent #15 권고):**
- (i) **즉시:** Veo 3.1 으로 image-to-video 카메라 prompt PoC — 부분 대체로 spike 004 기능 검증 시작
- (ii) **Watch:** Vertex AI early access program 신청 + 매주 release notes 폴. Omni 출시 시 즉시 본 검증 진입
- (iii) **본 검증:** Omni Vertex 출시 후 폴스포츠 motion clean-data gate 측정 (회전 5 / 역수직 3 / spin 2 = 10건 pose consistency)

### Memory implication

`camera-angle-ai-single-view-synth` 메모리 보강 박제:
- "Gemini Omni 영상 편집 path = Vertex GA 후 PRIMARY 후보" 박제
- "belle 의 multimodal AI 트렌드 감각 정확 — 누락 시 즉시 보강" 자체 박제 (claude 학습)
- Spike 003 reasoning path 와 Spike 004 editing path 의 **HYBRID 구조 박제**

### Phase 4 CONTEXT.md 보강 박제 권고

- D-18 Path #1 (PRIMARY) = Spike 003 (현재) + Spike 004 (Vertex GA 후) 박제
- D-24 신설 = Veo 3.1 backup 박제
- D-25 신설 = clean-data 검증 gate (sensitivity-gate-not-just-elite-low 정합)

## Sources

- [DeepMind Gemini Omni](https://deepmind.google/models/gemini-omni/)
- [DeepMind Prompt Guide](https://deepmind.google/models/gemini-omni/prompt-guide/)
- [VentureBeat — enterprise considerations](https://venturebeat.com/technology/google-unveils-gemini-omni-any-to-any-ai-model-what-enterprises-should-know)
- [WaveSpeed — 10s/720p cap](https://wavespeed.ai/blog/posts/gemini-omni-flash-shipped-what-actually-launched/)
- [Atlas Cloud — conversational editing](https://www.atlascloud.ai/blog/ai-updates/google-gemini-omni-conversational-video-editing)
- [Techsy — API pricing projection](https://techsy.io/en/blog/gemini-omni-api-pricing)
- [i10x — enterprise data policy](https://i10x.ai/news/google-gemini-training-data-consumer-vs-enterprise)
- [Meetily — DPA + zero retention](https://meetily.ai/llm-privacy/gemini)
- [Invideo — Flash review](https://invideo.io/blog/gemini-omni-flash-review/)
- [Opus — sports benchmark](https://www.opus.pro/agent/models/gemini-omni)
- [Skywork — Veo 3.1 capabilities](https://skywork.ai/blog/veo-3-1-capabilities-resolution-duration-use-cases-2025/)
- [PetaPixel — Veo 3.1 inpainting/outpainting](https://petapixel.com/2026/01/19/google-veo-3-1-updates-promise-even-more-realistic-ai-generated-video/)
- [MindStudio — Omni vs Veo 3.1](https://www.veo3ai.io/blog/gemini-omni-vs-veo-3-1-what-changed)
- [YouTube — belle 박제 소스 (NEW Google Gemini AI Editor)](https://www.youtube.com/watch?v=HmBGro96z-k)

---

## Iteration 3 — 2026-07-17 재개: API 실물 확인 + 리서치 갱신 (belle 지시 "한 달이면 AI가 크게 변한다")

### API 실물 (6월 박제 대비 정정)

| 항목 | 6/13 박제 | 2026-07-17 실물 |
|---|---|---|
| 출시 경로 | Vertex AI 대기 | **Gemini API + AI Studio 선출시 (2026-06-30)** — model id `gemini-omni-flash-preview` (public preview) |
| 가격 | $0.20-0.60/sec 추정 ($2-6/10초) | **$0.10/sec output** (Veo 3.1 Fast 동일) — 추정 대비 2-6배 저렴, 10건 게이트 ~$10-30 |
| Vertex Model Garden | 미등록 | Google Cloud 블로그 "Omni Flash available" 발표 — enterprise DPA path 확인 필요 (production 전제) |
| 능력 데모 | prompt guide 문구 | 공식 데모: 바이올린 클립 카메라 정면→후면 회전 + 멀티턴 편집 지속성 실연 |
| 캡 | 10초/720p | 동일 (긴 영상 = 구간 분할 호출) + SynthID 강제 유지 |

### NLM 재조사 (2026-07-17, 모션기술 88소스 + 파인튜닝 가이드 97소스)

1. **합성→재추론→융합 파이프라인은 문헌 부재** — 우리가 조합을 개척. 재료: JPMA(재투영 신뢰도 가중, 단 가림에서 불안정), P-Agg(가설 평균), confidence-aware majority voting.
2. **GT-free 자세 충실도 검증 프로토콜 확보** (10건 게이트 측정법): (a) 교차 시점 일관성 — 원본 vs 합성 시점 RTMW 3D 포즈 정렬 후 관절각 MAE (IPSF Page 19 "split angle 시점 불변" = 근거), (b) 시간축 일관성(가속도 스파이크), (c) 뼈길이 프레임간 불변, (+2D 재투영 오차).
3. **폴스포츠 특화 권고 스택**: ① PR 위상회전(수학, PersPose — 자세 충실도 수학적 보장/환각 원천 불가) → ② CLIFF 전역방향 → ③ Lie algebra/쿼터니언 평활화. **문헌은 "생성 이전에 수학 정규화 먼저" 권고** → 스파이크 비교군에 PR 필수.
4. **phase 22 파인튜닝 후보군(Qwen3-VL/InternVL3.5)은 생성 능력 0 — 대체 불가, 대신 judge 역할 확정**: 합성 영상의 기하 무결성(뼈대 비율/왜곡 1-5점) + 시간 일관성(VBench 유사 축) 판정. 당장은 Gemini 3.x judge, 장기적으로 phase 22 자체 VLM이 도메인 judge 승계 후보.
5. NLM 갭: NVIDIA NVS 계열·카메라컨트롤 오픈 모델 커버리지 없음 → 웹 리서치로 보강 (아래).

### 오픈 모델 대체재 발견 (2026-07-17 웹 리서치) — Omni 단독 후보 구도 깨짐

| 모델 | 정체 | 라이선스 | 우리 태스크 적합 |
|---|---|---|---|
| **ReCamMaster** (Kuaishou/Kling, ICCV'25 Best Paper Finalist) | **단일 영상 → 새 카메라 궤적 재렌더** — 우리 태스크 정의 그대로 | 코드/데이터 공개, 오픈 체크포인트 = Wan2.1 기반 (Wan = Apache-2.0) | ★★★ 태스크 일치 최고 |
| **NVIDIA GEN3C-Cosmos-7B** (CVPR'25 Highlight) | depth 점군 3D cache 조건부 카메라컨트롤 영상 생성 — monocular dynamic video NVS 명시 지원 | **NVIDIA Open Model License = 상업 OK** | ★★★ 3D cache 구조가 환각을 구조적으로 억제 (Omni 대비 잠재 강점) |
| Wan2.2 (Alibaba) | MoE 오픈 영상 생성 백본 (카메라컨트롤 파생 생태계) | Apache-2.0 상업 OK | 백본/생태계 |
| VACE (Wan 계열) | 오픈 video-to-video 편집 프레임워크 | Apache 계열 | 보조 (앵글 특화 아님) |

**전략 함의:**
- 오픈 경로 = 과금 $0 (GPU만) + **SynthID 없음** + **학생 영상이 우리 인프라 밖으로 안 나감** (Omni는 Google 전송 = DPA 전제) + phase 22 플라이휠로 향후 도메인 파인튜닝 가능성.
- 단 GPU Pod 필요 (현재 Pod 부재 — 재생성 후 실행) + 셋업 비용 + 품질 미검증.
- **구도 변경: "Omni 단독 본검증" → "Omni(API) vs ReCamMaster(오픈) vs GEN3C(오픈) vs PR(수학) 4-way bake-off"** — Spike 001 evaluate_4way 하네스 설계 그대로 재사용.

### Sources (Iteration 3)

- [Google Cloud Blog — Omni Flash available](https://cloud.google.com/blog/products/ai-machine-learning/nano-banana-2-lite-and-gemini-omni-flash-available)
- [Gemini API changelog](https://ai.google.dev/gemini-api/docs/changelog)
- [nvidia/GEN3C-Cosmos-7B (HF)](https://huggingface.co/nvidia/GEN3C-Cosmos-7B) / [GEN3C GitHub](https://github.com/nv-tlabs/GEN3C)
- [ReCamMaster GitHub](https://github.com/KlingAIResearch/ReCamMaster) / [arXiv 2503.11647](https://arxiv.org/abs/2503.11647)
- [Wan2.2 GitHub (Apache-2.0)](https://github.com/Wan-Video/Wan2.2)

### Iteration 3 실행 — 004-iii-a Omni API 스모크 (2026-07-17)

**셋업:** `power-spin-correct.mp4` (S3 fixtures) 8초 트림 → Files API 업로드 → `interactions.create(model="gemini-omni-flash-preview", input=[document, "rotate the camera 90 degrees to view from her left side, keep pose/motion/timing identical"])`.

**결과: SMOKE PASS**

| 실측 | 값 |
|---|---|
| 파이프라인 | 업로드 10.4s + 생성 ~65s → status=completed |
| 출력 | 8.17s / 720×1280 (9:16 유지) / 2.06MB mp4 |
| 비용 | 출력 8.17s × $0.10 ≈ **$0.82** (usage: video out 47,302 tokens) |
| 앵글 변경 | **실제로 회전됨** — 원본에 안 보이던 스튜디오 반대편 벽(로고 벽)이 드러나는 시점으로 전환, 방/폴/인물 정체성 보존 |
| 시간 동기 | 타임스탬프별 스핀 위상 대체로 일치 (0.5/2/4/6/7.5s 프레임 대조) |
| 자세 충실도 | **의심 지점 존재** — 7.5s 프레임에서 다리 벌림 각(레그 스플릿 폭)이 원본과 눈에 띄게 다름. 정확히 10건 정량 게이트(관절각 MAE)가 재야 할 결함 유형 |

**SDK 함정 박제 (게이트 러너 재사용):**
- Interactions API는 experimental warning. `interaction.output_video.uri` = **직접 다운로드 URI** (`files/<id>:download?alt=media`) — `client.files.get` 폴링 불필요/불가(빈 body로 JSONDecodeError), `client.files.download(file=uri)` 바로 호출이 정답.
- `client.interactions.get(id)` 로 재조회 가능 — 생성 크래시 시 재과금 없이 출력 회수 가능 (이번에 실증).
- 산출물 로컬: `smoke_out/power_spin_side_view.mp4` + `smoke_out/frames/pair_*.png` (원본↔출력 나란히).

### Iteration 3 실행 — 004-iii-b 10건 pose-consistency 게이트 (2026-07-17)

**셋업:** 10건(회전5/역수직3/spin2 — 정은지 ref 6 + phase22 수집 4) 8초 트림 → Omni 앵글 90° 회전 → 새 Pod(vktsrcks6dc1h4, 4090) RTMW(production 동일 onnx) 9fps 재추론 → GT-free 3축. 스크립트: `run_gate_batch.py`(멱등 journal) + `extract_kpts_pod.py` + `compute_metrics.py`, 수치: `gate_out/metrics.json`.

**생성 결과: 9/10.** 모더레이션 차단 첫 시도 3/10 (peter-pan·sideway-spin·straddle-invert, "prohibited content" — 폴스포츠 복장 오탐 추정), 재시도로 2건 통과(확률적), **straddle-invert 는 2회 연속 차단(영구)**. 비용 실측 9건 ≈ $7.4, 건당 80~170s.

**측정 결과 (9쌍):**

| 지표 | 값 |
|---|---|
| 굴곡각 MAE | **5.5°~40.9° (중앙 22.8°)** — Chair-spin 5.5 / kip-up 9.9 / peter-pan 12.1 / sliding 13.4 / sideway 22.8 / invert 24.8 / power-spin 27.7 / Diamond 31.2 / elbow-twist 40.9 |
| 뼈길이 CV 비율(omni/orig) | 5/9 악화 (최대 x1.82 sliding-spin, x1.52 power-spin) = 사지 길이 프레임간 요동 — 시점 무관 환각 증거 |
| jerk | kip-up x1.87 / peter-pan x1.76 악화, 나머지 비슷 |
| L/R 매핑 | 전 건 direct (회전 후 라벨 스왑 없음) |

**해석 (과대해석 방지 주석):**
- 2D 굴곡각은 시점 준불변일 뿐이라 MAE 에는 정당한 투영 변화분이 섞여 있음 — **절대 판정이 아니라 4-way bake-off 상대 비교의 공통 자(동일 프로토콜)로 쓰는 것이 정당**. 단 뼈길이 CV 악화는 투영과 무관한 순수 환각 신호.
- 원본 자체 추적이 나쁜 3건(elbow-twist conf 0.54 / invert CV 1.16 / power-spin CV 1.03)은 측정 기질 노이즈 포함. 추적 깨끗한 5건만 봐도 5.5°~31.2° 산포.
- 흥미: invert/elbow-twist 는 omni 출력에서 CV 가 오히려 개선(x0.33/x0.82) — 생성 과정이 모션블러를 제거해 RTMW 추적이 쉬워지는 부수효과.

### Verdict 갱신: **PARTIAL** (VALIDATED-DEFERRED-VERTEX-GA → 본 검증 완료)

1. ✓ 검증됨: API 실물·앵글 실회전·시간 동기·비용($0.82/8초)·멀티턴 편집 — 기능 자체는 진짜.
2. ✗ **채점(측정) 입력 기준 미달**: 관절각 편차 중앙 22.8° = 우리 감점 단위와 같은 자릿수. 지금 품질로 재추론→융합에 넣으면 점수 오염. "분석 정확도 절대 원칙" 위배.
3. ✗ **모더레이션 리스크**: 첫 시도 30% 차단 + 10% 영구 차단 — 실사용자 영상에서 재현되면 기능 신뢰 붕괴. production 채택 전 해소 필수 (Vertex enterprise 설정으로 완화 가능한지 확인 과제).
4. → **측정 보강 용도는 007(GEN3C 3D-cache/ReCamMaster) + 006(PR 수학) 상대 비교로 재판정.** 사용자 대면 "다른 각도 보기"(비채점 시각 기능) 후보로는 조건부 유지 — 모더레이션 해소 전제.

### Spike 006 — PersPose PR 수학 기준선 결과 (2026-07-17)

**구현:** `pr_warp_pod.py` — 인체 중심 광선을 Rodrigues 회전으로 z축 정렬, H=K·R·K⁻¹ 호모그래피 워프 (focal=CLIFF 근사, 중심=RTMW kpts 9fps 보간+평활). 10건 워프 → RTMW 재추론 → 기질 비교 (`gate_out/pr_metrics.json`).

**결과: 조건부 유효 — 전면 적용은 악화.**

| 케이스 | boneCV 변화 | 해석 |
|---|---|---|
| invert (역수직) | **1.16 → 0.489 (−58%)** | PR 설계 의도 그대로 — 인버전 원근왜곡 정규화가 추적 대폭 개선 |
| power-spin | 1.03 → **7.0** | 고속 스핀 = 중심이 빠르게 움직여 프레임별 워프가 요동 → 추적 파괴 |
| sideway-spin / peter-pan | 0.27→1.82 / 0.14→0.53 | 동일 악화 패턴 |
| 나머지 6건 | ±0.03 이내 | 중앙 근접 클립은 무영향 |

**판정:** naive 영상 전처리 PR = 부적격. 올바른 통합 = (a) PersPose 원안대로 **모델 입력 crop 단계 통합** 또는 (b) **역수직 구간 조건부 적용** (인버전 검출 시만). 역수직 개선 −58% 는 실증됐으므로 Phase 4 플랜에 "인버전 조건부 PR" 을 측정 보강 후보로 반영.

---

## Spike 008 — Wan2.7-VideoEdit (DashScope) 게이트 결과 (2026-07-17, belle 키)

**셋업:** Omni와 동일 10건·동일 프롬프트·동일 측정(RTMW 재추론 GT-free 3축). 입력 = S3 presigned URL, `wan2.7-videoedit` + watermark:false + seed 42. 스크립트 `wan_gate_batch.py`, 수치 `wan_out/metrics.json`.

**생성: 9/10** — 차단은 power-spin 1건(2/2 결정적, Alibaba Green net "output"). **Omni와 차단 교차**: Omni 영구차단(straddle-invert)을 Wan 통과, Wan 차단(power-spin)을 Omni 통과 — 두 벤더 필터 기준 상이. 건당 처리 6~7분(Omni 80~170s보다 느림), usage duration 16/클립.

**측정 (9쌍):**

| 지표 | Wan2.7 | Omni (동일 프로토콜) |
|---|---|---|
| 굴곡각 MAE 중앙 | **9.9°** | 22.8° |
| MAE <10° 클립 | **5/9** (kip-up 6.3 / straddle 7.7 / sideway 8.6 / peter-pan 9.4 / Diamond 9.9) | 2/9 |
| 뼈길이 CV | 대체로 안정 (x1.0~1.2), invert 개선 x0.52 | 5/9 악화 |
| 최악 outlier | sliding-spin 38.7° + CV x2.84 | elbow-twist 40.9° |
| 워터마크 | **없음 (watermark:false 지원)** | SynthID 강제 |
| 모더레이션 | 10% 영구 차단 | 첫시도 30% / 영구 10% |

**판정: Wan2.7 = 닫힌 API 트랙 승자.** 자세 충실도 Omni 대비 ~2.3배 우수, 절반 이상 클립이 10° 미만. 단 (a) outlier 존재(sliding-spin) — 점수 투입은 여전히 게이트 미달, (b) 모더레이션 차단 잔존(power-spin류 복장), (c) 건당 6~7분 지연. **"참고하세요 코너"(비채점) 엔진 1순위 후보로 승격**, 점수 보강은 GEN3C(오픈)와의 비교 + judge 게이트(Qwen3-VL-Plus 후보) 후 재판정.

**007a(ReCamMaster/Wan2.1) 폐기 박제:** belle 지시("구모델 검증을 최신 모델로 대체") + Pod 디스크 쿼터 충돌 → 셋업 중단·모델 삭제(29GB 회수). 접근법의 오픈 트랙 검증은 GEN3C(007b)로 일원화.

---

## Spike 007b — NVIDIA GEN3C-Cosmos-7B (오픈 모델) 게이트 결과 (2026-07-18)

**셋업:** Omni/Wan 과 동일 10건·동일 측정(RTMW 재추론 GT-free 3축). 파이프라인 = mp4 → 24fps/1280×704 121프레임 → **MoGe(monocular) per-frame depth** → GEN3C distributed 포맷(rgb+depth+mask+camera) → `gen3c_dynamic.py` trajectory=left, movement_distance=0.3, num_frames=121, guardrail/prompt-upsampler 비활성. 스크립트 `build_gen3c_inputs.py`+`run_gen3c_batch9.sh`, 수치 `gate_out/gen3c_metrics.json`.

**구동 성과 (별도 박제):** GEN3C 는 A100 80GB 에서 완주(구동 성공). Blackwell(PRO 6000, sm_120)에서도 TE 완전 우회(te_compat shim + megatron/apex 스텁 + torch 2.7.1+cu128, 아래 "Blackwell 구동" 참조)로 8/9 생성했으나 spot 회수로 A100 재개. **"오픈 모델 구동 불가" 시나리오는 기각** — 셋업 재현 가능(볼륨 박제).

**측정 (10/10 생성·추출):**

| 지표 | GEN3C | Wan2.7 | Omni |
|---|---|---|---|
| 굴곡각 MAE **중앙** | **41.1°** | 9.9° | 22.8° |
| MAE <10° 클립 | 4/10 | 5/9 | 2/9 |
| 분포 | **이봉(bimodal)** — 4클립 2.0~5.6° / 6클립 40~56°+inf | 단봉 대체로 <15° | 넓게 분산 |
| conf 저하 | 고-MAE 6클립 전부 급락(0.7→0.3대) = **인체 붕괴 신호** | 안정 | 부분 악화 |
| 최악 | power-spin = inf (인물 소실) | sliding 38.7° | elbow 40.9° |

- **잘 맞는 4클립은 최상**: sliding-spin 2.0° / Diamond 4.8° / Chair 5.4° / straddle-invert 5.6° — Wan2.7 중앙(9.9°)보다도 우수. depth-cache 접근이 정면·단순 회전에서 강력.
- **나머지 6클립은 완전 붕괴**: kip-up 40.4 / peter-pan 41.9 / invert 42.1 / sideway 49.1 / elbow-twist 56.1 / power-spin inf. 역위·급격 모션에서 **MoGe monocular depth 부정확 → 3D cache 왜곡 → 인체 환각**(conf 급락 + boneCV x2.3~4.0 + L/R swap 발생).

**판정: GEN3C = 측정 투입 부적격, 현 파이프라인에서 Wan2.7 대비 열등.** 중앙 MAE 41.1° = Wan2.7(9.9°)의 4배. 이봉분포 = 어느 클립이 무너질지 예측 불가 → 참고코너·측정 어느 용도로도 신뢰 불가. **근본 원인은 GEN3C 모델이 아니라 monocular depth 소스(MoGe)** — 역위/급격 모션에서 depth 붕괴. 개선 여지(멀티프레임 depth·실제 카메라궤적·foreground masking) 존재하나 별도 트랙.

**D-02 결론 (phase 31): Wan2.7-VideoEdit 확정 유지** (spike 008 승자). GEN3C 오픈 트랙은 depth 파이프라인 개선 후 재평가 후보로 보류. 강점(잘 맞을 때 <6°·워터마크 없음·자체호스팅)은 기록.

**Blackwell 구동 스텁/패치 (재현용, 볼륨 박제):** cosmos env torch=2.7.1+cu128(sm_120) + TE 완전 우회 — `te_compat.py`(RMSNorm/rope/DPA), attention backend="torch"(SDPA), peft·prompt-upsampler 지연/try-except(ImportError+**OSError** 둘 다), `gen3c_stubs/`(megatron core·parallel_state·tensor_parallel·apex/amp_C), hf_hub<1.0, HF_HUB_DISABLE_XET=1, t5-11b pytorch_model.bin 만.
