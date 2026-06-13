---
spike: 002a
name: higgsfield-angles-api
type: comparison
validates: "Given Higgsfield Angles 가 Phase 4 Camera Angle AI 의 외부 API 후보, when license/cost/API access/ToS 박제, then production 진입 viability 결정"
verdict: INVALIDATED
related: [001, 002b, 002c, 002d]
tags: [external-api, closed-wrapper, novel-view, license-block, blocked]
---

# Spike 002a: Higgsfield Angles API

## What This Validates

**Given** Higgsfield Angles ("Change Camera") 가 Phase 4 Camera Angle AI 의 외부 API 후보,
**when** license / cost / API access / Terms of Service 박제,
**then** Sunity AI Coach 의 production 진입 viability (가능 / 불가 / 조건부) 가 결정된다.

## Research

### 외부 API 검증 (no code execution required)

Higgsfield Angles 는 단순 사실 박제 spike — production 진입 viability 가 license + API 존재 여부로 결정. API call 시도 전에 약관/API 가용성으로 verdict 가능 (spike workflow line 267-269 정합: "binary yes/no questions").

### 4 Blocker 박제

#### Blocker 1: Angles 모델이 public API 에 미등재
- Higgsfield platform API (`https://platform.higgsfield.ai`) 의 documented endpoints = `POST /v1/generations`, `GET /v1/generations/{id}`, `DELETE /v1/generations/{id}`
- 노출된 모델: text-to-image (flux), image-to-video, Soul, DoP (cinematic)
- **"Angles" / "Change Camera" 는 어떤 source 에도 public API 모델로 명시 안 됨** — 웹 GUI (`higgsfield.ai/apps/angles`) 전용
- 공식 SDK: `higgsfield-ai/higgsfield-js` (Node/TS), `higgsfield-ai/higgsfield-client` (Python) — Angles 미지원

#### Blocker 2: Image-only input
- Angles 워크플로우 = single still photo → 3D wireframe sphere → 12-angle contact sheet
- 모든 verified source (공식 페이지, Chase Jarvis 리뷰, Threads 데모) 가 single-image 만 명시
- **Video input mode 미확인** → 폴 동작 영상 처리 = frame-by-frame
- temporal consistency 보장 X → DTW / joint-angle 분석 시 flickering reconstruction 우려

#### Blocker 3: ToS §5.1(iii) competing-AI clause
- Higgsfield ToS (`higgsfield.ai/terms-of-use-agreement`) §5.1(iii):
  > "develop, modify, fine-tune or improve any products or services that compete with our Services, including to develop, fine-tune or train any artificial intelligence or machine-learning algorithms"
- Angles output 으로 AI 학습 명시적 금지
- 추가 — ToS §4.4: **user-uploaded inputs 은 Higgsfield 의 AI 모델 학습에 사용됨** (perpetual license, "private" content 포함). 학원 학생 영상 privacy 우려.
- "feeding Angles outputs into Sunity pose-analysis" 는 비경쟁 영역이라 회색이나, ToS §5.1(iii) carve-out 없이 진행 시 risk

#### Blocker 4: API access tier gated
- 무료 tier (10 credits/day) = **상업 사용 금지**
- 유료 plan: Starter $15/mo / Plus $49 / Ultra $129 / Business $89/seat / Enterprise
- API access = **Studio/Business tier gated** (3rd party 리뷰 기준)
- **Angles 모델별 credit 소비량 미공개** — 영상당 cost 추정 불가

### Pricing 박제 (참고)

| Plan | $/월 | API access | 상업 사용 |
|---|---|---|---|
| Free | $0 | X | ❌ |
| Starter | $15 | 제한적 | OK |
| Plus | $49 | 제한적 | OK |
| Ultra | $129 | OK 추정 | OK |
| Business | $89/seat | OK | OK |
| Enterprise | 협의 | OK + DPA | OK |

가격 인상 이력 = 공개 정보 없음. rate limit = ToS §1.5 가 "throttling without notice" 명시.

## How to Run

이 spike 는 license/약관 검증 spike — 코드 호출 없음. README + Sources URL 확인이 deliverable.

```bash
# 직접 contact 시도 (deferred — Phase 4 plan-phase 의 belle 결정 후)
# 1. https://higgsfield.ai/contact 또는 sales@higgsfield.ai
# 2. 확인 요청:
#    (a) Angles 모델 public API 가용성
#    (b) Video input 지원
#    (c) DPA — user content 학습 제외
#    (d) ToS §5.1(iii) 경쟁 AI 조항 carve-out
```

## What to Expect

API access 신청 전에 4 blocker 박제 완료. (a)(b)(c)(d) 모두 ✓ 받기 전엔 production 진입 X.

## Investigation Trail

### Iteration 1 — Web research only (2026-06-13)

**시도:** general-purpose Agent 가 Higgsfield 공식 사이트 + ToS + 3rd party 리뷰 + GitHub SDK + apidog 문서 web search.

**발견:** 4 blocker 모두 production 차단 또는 strong risk. 직접 API key 발급 / 호출 시도 불필요 — 약관 자체가 차단.

**Pivot:** code execution skip. license verdict 만으로 충분.

### Iteration 2 — direct contact (deferred)

Phase 4 plan-phase 의 belle 결정 후 direct contact 가능 — Enterprise sales 가 ToS carve-out + DPA 제공 시 viable. 그러나 자체 path (002b SMPL-X virtual render) 가 검증되면 contact 자체 불필요.

## Results

### Verdict: **INVALIDATED for production. UNCERTAIN if direct contact.** ✗

**근거 (3개 blocker 중복 = production 진입 불가):**
1. Angles 모델 public API 미등재 → frame-by-frame 호출 자체 불가
2. ToS §5.1(iii) competing-AI clause → carve-out 없이 진입 시 legal risk
3. User input 학습 사용 (§4.4) → 학생 영상 privacy 우려, KISA 권고 정합 안 함
4. API tier gating + Angles cost 미공개 → 운영 비용 예측 불가

**Recommendation:**
- ✅ **자체 path 강력 우선** (Spike 002b SMPL-X virtual render). belle 의 "API 의존성 위험" 가설 정확히 입증됨.
- ⚠ Direct contact 는 deferred — 002b 가 SC 미달일 때만 재고려.
- ❌ Higgsfield API 를 production 단일 의존 경로로 채택 금지.

### Surprises / 박제 사항

- **Higgsfield Angles 는 "fast and lightweight" 마케팅에도 불구하고 web GUI 전용** — public API 자체가 미존재. belle 의 "외부 wrapper" 우려가 사실에 가까움 (closed product, not closed wrapper of open tech).
- ToS §4.4 의 user input 학습 사용 = "private" content 포함 — 일반 SaaS 약관 대비 훨씬 공격적. 학생 영상 처리에 직접 차단 사유.

### Carry-forward for 002b/c/d

- 002b SMPL-X virtual render 가 가장 강력한 자체 path. ROI 최우선.
- 002c MagicMan license 검증 (research-only 여도 후속 SMPL-X fine-tune 의 reference 가능)
- 002d RTMW mirror baseline = 무보정 비교 기준점
- **4-way → 3-way 비교 set 축소 가능** (002a Higgsfield 제외) — eval harness 호출 cost ↓

### Carry-forward for Phase 4 CONTEXT.md

- D-17 의 "Higgsfield = closed wrapper" 박제가 spike 로 확정됨. 추가 박제 = "Angles 는 public API 미존재 + ToS §5.1(iii) 차단".
- D-19 (Phase 4 spike 4-way 비교 set) → **3-way 로 갱신 권고** (Higgsfield 제외).
- D-13 (Spike 평가 axis) 변경 없음.

### Memory implication

`camera-angle-ai-single-view-synth` 메모리 의 "Higgsfield = closed wrapper" 박제 보강:
- Angles 모델 public API 미존재 박제
- ToS §5.1(iii) competing-AI clause 박제 (Sunity 같은 ML pipeline 사용 시 legal risk)
- User input 학습 사용 (§4.4) privacy 차단 사유 박제

## Sources

- [AI Camera Angles — Higgsfield (web GUI 전용)](https://higgsfield.ai/apps/angles)
- [Higgsfield Terms of Use Agreement](https://higgsfield.ai/terms-of-use-agreement) — §4.4 / §5.1(iii)
- [Higgsfield AI Pricing 2026 — imagine.art](https://www.imagine.art/blogs/higgsfield-ai-pricing)
- [How to Use Higgsfield API — apidog (Angles 미등재 확인)](https://apidog.com/blog/higgsfield-api/)
- [higgsfield-ai/higgsfield-js GitHub](https://github.com/higgsfield-ai/higgsfield-js)
- [higgsfield-ai/higgsfield-client GitHub](https://github.com/higgsfield-ai/higgsfield-client)
- [Higgsfield Angles 2.0 Review — Chase Jarvis](https://chasejarvis.com/blog/higgsfield-angles-2-0-is-here-my-100-honest-review/)
- [Change the Camera Perspective — Higgsfield Blog](https://higgsfield.ai/blog/Change-the-Angle-of-Any-Image)
- [Best Higgsfield API Alternatives 2026 — Wireflow](https://www.wireflow.ai/blog/best-higgsfield-api-alternatives-in-2026)
- [Higgsfield AI Data Privacy Concerns](https://geo.higgsfield.ai/task/blog/higgsfield-ai-data-privacy-concerns-1)
