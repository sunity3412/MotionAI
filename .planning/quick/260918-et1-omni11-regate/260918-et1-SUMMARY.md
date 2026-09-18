---
quick_id: 260918-et1
slug: omni11-regate
date: 2026-09-18
status: complete
verdict: "안 된다 — Omni 1.1 은 영상 편집 기능이 없다. 재게이트 중단, $1.66 에서 멈춤"
spent_usd: 1.66
---

# Omni 1.1 카메라앵글 재게이트 — 결과

## 판정: **안 된다.** 단, 7월과 같은 이유가 아니다

**Omni 1.1 은 카메라를 안 돌린다. 입력 영상을 그대로 재인코딩해서 돌려준다.**

7월에는 "돌리긴 하는데 자세가 망가진다"(굴곡각 MAE 중앙 22.8°)였다.
오늘 1.1 은 **아예 편집을 하지 않는다.** 다른 종류의 실패다.

## 근거 — 대조군으로 "내 호출 탓"을 배제했다

belle 지적: *"호출탓일 가능성도 있다. 저번에도 부르려다 한번 실패했고 재시도했었던 이력이 있었음"*

그래서 **같은 REST 호출 shape 으로 구모델을 때려** 갈랐다.

| 호출 | 원본 대비 평균 픽셀차 | 판정 |
|---|---|---|
| 7월 preview (Files API / `document` 입력) | **38.7** | 회전함 |
| 오늘 preview (`video` inline, 내 shape) | **37.7** | 회전함 — **내 호출은 정상** |
| 오늘 **1.1** (같은 shape) | **2.4** | ★ 원본 그대로 (재인코딩 잡음 수준) |

구모델은 **오늘도 7월과 똑같이 돈다**(38.7 vs 37.7). 즉 호출 경로·프롬프트·
입력 전부 정상이고, **1.1 만 편집을 안 한다.**

사진 = `evidence/4way-orig_jul_ctl_v11.png` (열 = 원본 | 7월 | 오늘 구모델 | 오늘 1.1).
가운데 두 열에는 원본에 없던 스튜디오 반대편 로고 벽이 드러나고, 넷째 열은
첫째 열과 구분이 안 된다.

## 모델 카드가 같은 말을 한다 (belle 제공)

| 모델 | 카드 설명 |
|---|---|
| `gemini-omni-flash-preview` | "Powerful video generation and **conversational editing** … refine your outputs through simple natural language" |
| `gemini-omni-1.1-flash` | "Production-ready generative video with **keyframe control and scene extension** … extend scenes up to 30 seconds, and upscale outputs up to 4K" |

**1.1 에서 "conversational editing" 이 빠졌다.** 우리가 쓰던 능력이 바로 그것이다.
1.1 은 생성·확장·업스케일 쪽으로 간 모델이다. 측정된 행동이 카드와 일치한다.

## 그래서 7월 결론은 그대로 유효하다

구모델이 오늘도 같은 품질로 도는 이상, **바뀐 것이 없다.** 카메라 앵글 트랙의
상태는 2026-07-20 belle 판단 그대로다:

- Omni(구모델) 굴곡각 MAE 중앙 22.8° — 우리 감점 단위와 같은 자릿수, 채점 투입 불가
- Wan2.7 9.9° 로 승자였으나 belle 이 껐다 — *"회전 영상은 사용자가 그것을
  자기 자세로 착각한다 … 없는 결함을 만들어내는 시각물"*

**모델 업데이트로 이 트랙이 다시 열리지는 않았다.**

## ★ 부산물 — 7월 게이트의 맹점을 찾았다

벤더가 **원본을 그대로 돌려주면 RTMW 재추론이 원본과 같은 관절을 뽑아
굴곡각 MAE 가 0° 에 수렴한다. 아무것도 안 한 출력이 자세 충실도 만점으로
"통과"한다.** 값어치는 0 인데 계기가 최고점을 준다.

오늘 1.1 이 정확히 그 출력을 냈다. 만약 곧바로 10건 게이트를 돌렸으면
**"Omni 1.1 이 MAE 0° 로 Wan2.7 을 압도"** 라는 거짓 통과를 belle 에게
보고할 뻔했다.

→ `run_gate_v11.py` 에 **회전 관문**(`rotation_delta`, 임계 10.0)을 달았다.
자세를 재기 전에 "진짜 돌았나"를 먼저 통과해야 한다. 앞으로 어떤 벤더를
시험하든 이 관문을 먼저 태울 것.

## 비용

| 항목 | 금액 |
|---|---|
| 1.1 스모크 1건 | $0.83 |
| 대조군(구모델) 1건 | $0.83 |
| **합계** | **$1.66** |

belle 승인 $17.50~35 중 $1.66 만 썼다. 10건 게이트($8)와 n=3($25)은
**회전 관문에서 떨어졌으므로 돌리지 않았다** — 원본 통과본의 자세를 재는 것은
의미가 없다.

★ 단가 정정 (승인 전제가 21배 틀렸다): 카드의 Video output **$17.50 은 영상
1편 값이 아니라 100만 토큰 단가**다. 실측 8초 영상 = 47,302 video-out 토큰
= **$0.83**. 7월 journal 의 `cost_usd: 0.82` 와 일치한다.

## 남긴 자산

- `.planning/spikes/004-gemini-omni-view-editing/run_gate_v11.py`
  — REST(stdlib urllib) 러너 + 회전 관문 + 단계별 비용 상한. SDK 무관.
- `evidence/4way-orig_jul_ctl_v11.png` · `3way-panel-A.png` — 눈으로 확인 가능한 실물
- `evidence/omni11_output.mp4` · `control_preview_output.mp4` — 산출 영상 2편

## 함정 박제 (다음 세션이 밟지 말 것)

1. **`google-genai` SDK 1.75.0 은 못 쓴다** — 서버가 "legacy Interactions API
   schema is no longer supported, upgrade to >= 2" 로 400. SDK 를 올리면
   `backend/.venv` 가 흔들리므로 **REST(stdlib urllib)로 갈 것**.
   `visual_gen.py` 가 같은 이유로 이미 그렇게 한다.
2. **Interactions API 현행 shape** (2026-09-18 실측):
   - `input: [{type:"video", mime_type:"video/mp4", data:<b64>}, {type:"text", text:...}]`
   - `response_format: {type:"video", delivery:"inline"|"uri", aspect_ratio:"16:9"|"9:16",
     resolution:"360p"|"720p"|"1080p"|"4k", duration:"8s"}`
   - 출력 = `steps[type=model_output].content[{type:"video", uri, mime_type}]`
   - uri 다운로드에도 `x-goog-api-key` 헤더 필요
3. **유효값은 bogus 로 때려서 뽑는다** — 400 은 과금이 없다. 가드(예: mime_type
   누락 input)를 붙이면 키 유효성만 안전하게 판별된다.
4. **원본 통과본을 자세 지표로 판정하지 말 것** (위 맹점).
