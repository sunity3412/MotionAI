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

### Vertex AI / Google Cloud platform 상태

- **현재 (2026-06-13):** Consumer 출시 (Gemini app / Google Flow / YouTube Shorts) 만
- **Vertex AI API:** "coming weeks" — 2026-05-19 I/O 발표, ~2026-Q3 추정 GA
- **Sunity 직접 통합:** Vertex GA 전까지 production 불가

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

**HYBRID PRIMARY path 박제:**

| 우선순위 | Path | 시기 |
|---|---|---|
| #1 즉시 | Spike 003 Gemini Vision **reasoning** (joint 좌표 추정, 픽셀 합성 X) | 현재 PRIMARY |
| #2 즉시 | Spike 002b cylindrical mesh + virtual render (자체 path) | 현재 SECONDARY |
| baseline | Spike 002d RTMW mirror | 비교 기준 |
| **#3 deferred** | **Spike 004 Gemini Omni view editing** (영상 직접 편집, Phase 17 정합) | **Vertex GA 후 (~2026-Q3) PRIMARY 후보 — clean-data gate 통과 시** |
| backup | Veo 3.1 inpainting/outpainting | Omni 실패 시 |
| 완전 최후의 보류 | SMPL-X mesh ($7,300/yr) | 모든 path 99% 미달 + 효과성 입증 시 |

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
