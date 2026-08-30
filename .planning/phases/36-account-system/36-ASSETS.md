# Phase 36 에셋 출처 (provenance)

> 브랜드 에셋은 어디서 왔는지 적어 둔다. 다음 사람이 재현하거나 교체할 수 있어야 한다.

---

## `app/assets/auth/intro-bg.jpg` — 인트로 배경

**belle 승인 2026-08-30** — 후보 6장을 실제 앱 화면에 올려 찍어 비교한 뒤 **C** 선택.
판정 보드: https://claude.ai/code/artifact/eac63758-8a48-4891-a3af-0f3a16a4fa06

| | |
|---|---|
| 출처 | Magnific(Freepik) 생성 — 모델 `recraft-v4-1`, 1:2, 768×1536 |
| 후처리 | Magnific `images_upscale` (mode `ultra-photo`, 2x) → 기기 비율(402:874) 중앙 크롭 |
| 비용 | 생성 4장 240 크레딧 + 업스케일 90 크레딧 |

**프롬프트 (원문)**

```
Dramatic low-key studio photograph of a female pole sports athlete holding an elegant,
powerful strength pose on a vertical chrome pole. Deep crimson-red backlight glowing
through thick atmospheric haze and rolling smoke; dark maroon-to-black background.
She wears a plain black athletic leotard; her body is a rim-lit silhouette, muscle lines
defined only by red edge light. Full-body figure, tall vertical composition, the figure
set slightly off-centre so smoke and darkness fill the upper middle of the frame.
Very dark overall exposure, deep crushed shadows, cinematic high-contrast sports
photography, shot on 85mm, shallow depth of field. No text, no logos, no watermark.
```

**왜 스톡이 아니라 생성인가 (belle 이 스톡을 먼저 제안했음 — 실측 결과)**

- 폴 스톡 사진은 대다수가 **힐·란제리 연출**이다. 우리 사용자는 폴스포츠 학원 수강생이고
  도입 결정권자는 강사다([[field-research-stakeholders]]) — 그 톤은 정면으로 어긋난다.
- 스포츠 톤인 스톡(Freepik `376761866` 스포츠웨어 / `259410037` / `126909421`)은
  **붉은 연기 분위기가 없다.** 브랜드 진홍 그레이드를 따로 입혀야 했고(코드는
  `.planning/phases/36-account-system/` 밖 scratchpad, 재현 필요 시 아래 스톱 참조),
  그래도 승인본 튜토리얼 3장의 결과 어긋났다.
- 생성본은 이미 승인된 튜토리얼 이미지(`app/assets/tutorial/slide-*.jpg`, Phase 26-01)와
  **같은 시각 언어**다.

**진홍 그레이드 레시피** (스톡을 다시 쓸 일이 생기면):
휘도 → 3점 그라디언트 매핑 `0.00 #180507 · 0.45 #7A1810 · 1.00 #E8827A`,
노출 0.92, 감마 1.15, 원본 18% 블렌드.

---

## `app/assets/auth/icon-google.png` — Google 아이콘

Figma node `1:980` 의 원본 래스터(`rawImages`, 알파 있음)에서 G 부분만 crop.
Figma 에 벡터가 없어 이것만 PNG 다. 나머지 3종은 벡터 인라인
(`app/src/components/SocialIcon.tsx`).

## 로고 · 소셜 아이콘 (벡터 인라인)

`app/src/components/SunityWordmark.tsx` (`1:147` white / `1:573` brand),
`app/src/components/SocialIcon.tsx` (`1:974` 카카오 / `1:979` 네이버 / `1:981` Apple).

★PNG 로 export 하면 프레임 배경 `#CCCCCC` 가 같이 구워진다 —
메모리 `figma-frame-export-bakes-background` 참조.
