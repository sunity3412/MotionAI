---
phase: quick-260731-plf
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: false
requirements: [S13, S24, S25, S26, D-2, D-43]
files_modified:
  - app/src/lib/illustrationScene.ts
  - app/src/components/DefectIllustration.tsx
  - app/src/lib/__tests__/illustrationScene.test.ts
  - app/assets/illustrations/
  - .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/

must_haves:
  truths:
    - "어깨 감점이 있는 mode1 결과에서 어깨 시트를 열면 **어깨를 가리키는** 일러스트가 보인다 (종전 = 아무것도 없음)"
    - "같은 doc 의 다리 시트에는 종전과 **완전히 같은** 다리 일러스트가 그대로 보인다 (승인 PASS 무회귀)"
    - "장면과 어긋나는 부위 시트에는 여전히 자리 자체가 생기지 않는다 (빈 카드·플레이스홀더 0)"
    - "등재된 신규 에셋은 전부 4게이트 판정 표에 행이 있고, 표에 없는 그림은 배선되지 않았다"
    - "생성 대상 (동작 × 부위) 선정 근거가 실 doc 방출 집계 + 33-A1 인용으로 기록돼 있다"
  artifacts:
    - path: "app/src/lib/illustrationScene.ts"
      provides: "(motionId, parts) 키 장면 표 + 부분집합·최구체 우선 판정"
      exports: ["ILLUSTRATION_SCENES", "illustrationAssetForPart", "hasIllustrationFor", "sceneCoversParts"]
    - path: "app/src/components/DefectIllustration.tsx"
      provides: "asset 키 require 맵 + silent hidden (props 무변경)"
      contains: "illustrationAssetForPart"
    - path: "app/src/lib/__tests__/illustrationScene.test.ts"
      provides: "판정 불변식 테스트 (기존 10축 + 최구체 우선 + 중복 금지 + 부위 어휘 게이트)"
    - path: ".planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/TARGETS.md"
      provides: "생성 대상표 — 실 doc 방출 집계 × 33-A1 인용 × 국면 t × 가이드 종류"
    - path: ".planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/REVIEW.md"
      provides: "4게이트 전수 판정 표 + 구도 실측 표 + 정직 미완 기록"
    - path: ".planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/golden_before.json"
      provides: "키 전환 전 판정 거동 스냅샷 (무손실 대조 기준)"
  key_links:
    - from: "app/src/components/DefectIllustration.tsx"
      to: "app/src/lib/illustrationScene.ts"
      via: "illustrationAssetForPart 결과를 require 맵 조회 키로 사용"
      pattern: "illustrationAssetForPart\\("
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/lib/illustrationScene.ts"
      via: "hasIllustrationFor(motionId, partKey) — 시그니처 무변경, 이 플랜에서 **무접촉**"
      pattern: "hasIllustrationFor\\(motionId, partKey\\)"
---

<objective>
33-G §C-4 3번 — **어깨·팔(팔꿈치) 결함 일러스트 신규 생성 + 부위별 키잉.**

현재 등재 에셋 6장은 전부 다리 장면이라 어깨·팔 항목은 전 동작 미부착이다(의도된
fail-closed, 최종 상태 아님). §C-4 A-트랙이 기준 보고서를 12관절로 올려 `omitted:ref_gate`
가 39→0 이 되면서 **어깨·팔꿈치 각도 카드가 실제로 방출되기 시작**했다 — 즉 그 시트들이
belle 확인 ③ 에서 열리는데 그림 자리가 비어 있다.

Purpose: "말하는 부위 = 가리키는 부위"의 일러스트 축을 **부착으로도** 성립시킨다. 3단위는
틀린 부착을 끊어(S13/S25 PASS) 절반을 닫았고, 이 플랜이 맞는 부착을 채워 나머지를 닫는다.

Output:
- `(motionId, part)` 키 장면 표 + 최구체 우선 판정 (기존 6장 거동 무손실)
- 4게이트 통과 어깨/팔 일러스트 + `provenance` 등재
- 생성 대상표(데이터 근거) · 검수 판정 표 · 구도 실측 표 · 정직 미완 기록
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/phases/33-result-trust-recovery/.continue-here.md
@.planning/phases/33-result-trust-recovery/33-14-SUMMARY.md
@.planning/phases/33-result-trust-recovery/33-A1-MOTION-STANDARDS.md
@app/src/lib/illustrationScene.ts
@app/src/components/DefectIllustration.tsx
@app/src/lib/__tests__/illustrationScene.test.ts
@.planning/quick/260731-2jt-33-g-c-2-3-s13-fail-closed-s23-illu-floa/260731-2jt-SUMMARY.md
@.planning/quick/260731-2jt-33-g-c-2-3-s13-fail-closed-s23-illu-floa/sweep_illustration_scene.test.ts
</context>

<locked_decisions>
설계 재논의 금지 (repair-cycle-no-rediscussion, D-39). 스펙 = 승인 목업 7R `DETAILS` +
33-14 확정 레시피. 아래는 오케스트레이터가 코드를 직접 열어 확정한 사실이므로 **재조사 금지**.

**L-1. `deferred D-2` 의 "코드 변경 없이 에셋+메타만"은 이 경우 틀렸다.**
두 표가 지금 **motionId 단독 키**다 — `VERIFIED_ILLUSTRATIONS: Record<string, number>` 가
동작당 파일 1장, `ILLUSTRATION_SCENES: Record<string, IllustrationScene>` 가 동작당 장면 1개,
`illustrationMotionForPart` 가 `ILLUSTRATION_SCENES[motionId]` 하나만 조회한다. 한 동작에
다리+어깨 두 장을 넣을 자리가 없다. **키를 `(motionId, parts)` 로 바꾸는 코드 변경이 필수**다.

**L-2. 그 변경이 승인 범위인 근거.** 승인 목업 `DETAILS` 는 일러스트를 **항목(부위)별
데이터**로 둔다 — legs `mockups/index.html:1047` "파워스핀 위·아래 일자 스플릿" / shoulder
`:1073` "그립 어깨 견갑 고정" / refonly `:1081` **null**. 세 시트가 서로 다른 값을 갖는다.
슬롯 조건은 `:1114` `if(d.illust)` — 불일치면 빈 박스가 아니라 **자리 자체가 없다**.

**L-3. 전신 1장에 `parts: ['leg','shoulder']` 를 주는 편법 금지.** `illustrationScene.ts`
헤더가 못박은 대로 전신 그림은 언제나 어깨·팔이 보이므로 **가시성으로 토큰을 주면 전부
매칭되어 지금의 결함이 그대로 남는다**. 그것이 belle M-5 반려의 재생산이다. 다토큰 장면은
**가이드 표시가 실제로 두 부위를 함께 짚을 때만**(예: 어깨→손 한 줄 = `arm_extension` 계열)
허용하고, 근거를 `provenance` 에 실물 열람으로 적는다.

**L-4. 33-14 승인 레시피 불변 (S24 는 이미 PASS).**
입력 1 = 그 동작 기준 영상의 **국면 완성 프레임**(33-A1 국면 데이터 키잉) / 입력 2 = **스타일
앵커** / 프롬프트 = 자세 충실 + 익명화 + 가이드 표시. **가이드 종류는 highlight 데이터로
키잉** — 신전·라인 계열 = **곧은 선**, hook·잠금 계열 = **부위 원**. **굽힘이 정답인 부위에
직선 금지.** 동작명 문자열 분기 0.

**L-5. 검수 게이트 4종 불변** — ① 익명(이목구비 제거) ② 자세 충실(입력 프레임 동일 자세)
③ 가이드 선(곧은 획·부위 관통) ④ 해부학(사지 수·관절). **생성 전량 Read 육안** + PASS 후보는
**2x 확대 크롭**(선·손발·얼굴) 추가 열람 + **입력 프레임 원본 대조**.

**L-6. 알려진 실패 계열 = 스타일 앵커 자세 복제** (33-14 에서 21회 중 10회). 대응 = 입력 인물
**크롭 확대** + **같은 방위의 통과본을 스타일 앵커로 교체**(33-14 Deviation 2, 2안 계열 스타일
유지). 이 플랜은 그 개선된 형태를 **기본값**으로 쓴다 — `illust_variant2_pro.jpg`(앉은 자세)로
되돌아가지 말 것.

**L-7. 틀린 그림은 없는 것보다 나쁘다 (D-15/D-43).** 게이트 미통과분은 배선하지 않는다.
상한 소진 후 미완은 정직한 결과이지 실패가 아니다. **부착 건수를 지키려고 억지 매칭 금지.**

**L-8. 토큰 부여 = 에셋 실물 열람으로만 (P-4).** `provenance` 없는 등재 금지. 확신이 안 서면
토큰을 **빼는** 쪽이 정답. 판정 축 = 그림이 **가리키는** 부위(가이드 표시가 얹힌 곳 + 그림의
주제)이지 "프레임에 보이는" 부위가 아니다.

**L-9. belle #11 "빈 프레임" — 구도도 같이 잡는다.** 현 6장은 비배경 픽셀이 11.1~17.6%
(= 82~89% 빈 배경). 신규분은 인물이 프레임을 채우도록 구도를 잡고, **같은 자**로 재서 대조한다.

**L-10. 승인 자산 무접촉.** 기존 6장의 파일 경로·바이트·require 키를 바꾸지 않는다.
`result.tsx` 는 이 플랜에서 **무접촉**(`hasIllustrationFor`·`DefectIllustration` props 시그니처
불변이라 변경이 필요 없다). 백엔드·contract·채점 무접촉.
</locked_decisions>

<verified_facts>
오케스트레이터가 직접 코드를 열고 명령을 돌려 확인. **재조사 불필요.**

**(A) 실 doc 방출 집계 — 생성 대상 선정의 1차 근거.** §C-4 A-트랙 재산출 doc 4건
(`.planning/quick/260731-iis-.../docs_after/*.json`)을 `regionPartKeyForRecord` 규칙으로
접은 결과:

| doc | referenceMotionId | 부위 키 → record |
|---|---|---|
| elbowtwistsisterFault | ref-elbow-twist-sister | **arm** ← left_elbow −3.8 · right_elbow −12.4 / **shoulder** ← left_shoulder −0.5 · right_shoulder −11.1 / leg ← hip·knee 4건 |
| kipupFault | ref-kip-up | leg ← split_angle −20.0 / **shoulder** ← left_shoulder −0.8 |
| powerspinFault | ref-power-spin | leg ← leg_extension −20.0 · split_angle −12.0 / **shoulder** ← left_shoulder −12.8 |
| pdshapeCorrect | ref-pdshape | leg ← right_knee −0.2 |

즉 **실제로 화면에 열리는데 그림이 없는 조합 = 4건**: `ref-power-spin×shoulder`,
`ref-elbow-twist-sister×shoulder`, `ref-elbow-twist-sister×arm`, `ref-kip-up×shoulder`.

**(B) 부위 토큰 어휘 = `shoulder` · `arm` · `leg` 3개뿐** (`deductionLabels.BODY_PART_OF_KEYPOINT`
치역). `left/right_elbow`·`left/right_hand` → `arm`, `left/right_shoulder` → `shoulder`.

**(C) `shoulder+arm` 복합 키는 합성이 아니라 실재한다.** `CRITERION_REGION_KEYPOINTS.arm_extension`
= `REGION_MEMBER_KEYPOINTS.arms` = `[left_shoulder, right_shoulder, left_hand, right_hand]`
→ 토큰 `{shoulder, arm}` → 부위 키 `'shoulder+arm'`. 스위프가 10동작 전건에 대해
`ref-*__arm_extension.png` 를 렌더한다. 단 4건 재산출 doc 에는 방출되지 않았다.

**(D) `result.tsx` 소비 지점 2곳, 둘 다 시그니처 무변경으로 흡수된다.**
`result.tsx:1853-1854` `hasIllustrationFor(motionId, partKey)` → `<DefectIllustration motionId partKey/>`
(illu-float) · `result.tsx:3304-3308` `illustrationSlot` (시트). **파일 무접촉.**

**(E) 도구·경로 실측.** `node v24.15.0` — `.ts` 진입점 type stripping 동작 확인(프로브 110셀
산출 성공). `node --test app/src/lib/__tests__/illustrationScene.test.ts` **11 pass / 0 fail**
(baseline). `ffmpeg`/`ffprobe` = `/opt/homebrew/bin`. **로컬 Mac 에 `imageio` 없음** — 프레임
추출은 ffmpeg CLI 로. PIL·numpy 는 있다.

**(F) 기준 영상 S3 접근 정상.** `aws s3 ls s3://sunity-motion-pilot-videos/reference/ --profile
sunity-motion --region ap-northeast-2` → 11개 mp4. `ref-kip-up.mp4`(2.25MB) 다운로드 **1초**.
Pod 릴레이 불필요. 대상 3개 = ref-power-spin.mp4(3.1MB) · ref-kip-up.mp4(2.25MB) ·
ref-elbow-twist-sister.mp4(6.4MB).

**(G) 스타일 앵커 자산 위치.**
`.planning/phases/33-result-trust-recovery/mockups/assets/illust_variant2_pro.jpg` (원 2안 —
L-6 대로 기본값 아님) · 통과본 6장 = `app/assets/illustrations/*.jpg` (720x964, 3:4).

**(H) 생성 경로 — 오케스트레이터가 실제 호출해 200 + 이미지 바이트 수신.**
`POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent?key=$KEY`
· `generationConfig.responseModalities = ["TEXT","IMAGE"]`. 키 =
`aws ssm get-parameter --name /sunity/motion/gemini-api-key --with-decryption --profile sunity-motion --region ap-northeast-2`.
과거 크레딧 고갈 이력이 있으나 **지금은 산다**.

**(I) 구도 실측의 자(尺) — 2jt 와 동일해야 대조가 성립.** 배경 픽셀 = `min>225 ∧ (max−min)<22`.
비배경 비율 기존 실측 = ref-foxtop 11.1 · ref-invert 11.3 · ref-foxtop-split 12.6 ·
ref-kip-up 14.8 · ref-power-spin 17.4 · ref-climb 17.6 (%).

**(J) 승인 자산 6장 sha256 baseline (L-10 무접촉 게이트의 기준값).**

    780af0bad53b8c5854c897dbd3813fa75c268d62f5047a4a110f3ee8782e2df4  ref-climb.jpg
    1360c09fd4c44d28f764f6d370b196a9bf81c0a7549e8713959d692b067cb2ce  ref-foxtop-split.jpg
    dd441904c7d361e3dc6afd48e23018ef85a8621cda266bba350ac54238d34235  ref-foxtop.jpg
    241e924b6a55a2ac9da0a7fe043226a0a2c49eba7651b111c76abf1e29ce3594  ref-invert.jpg
    783a826f4e9af82d419b65973c3e9df6112fbf8d6f5a92bf393c22a264f43fd3  ref-kip-up.jpg
    a47e0dea389c3021ccda8c9acef66f6549f3ced5832b85b27884d5a03a126b0b  ref-power-spin.jpg

Task 1 에서 이 6줄을 그대로 `assets_baseline.sha256` (quick 디렉터리, 경로 접두
`app/assets/illustrations/` 를 붙여 리포 루트에서 `shasum -a 256 -c` 가 돌게)으로 저장하고,
이후 태스크 게이트가 그것으로 대조한다. 신규 파일 추가는 이 검사에 영향이 없다(목록 밖).
</verified_facts>

<tasks>

<task type="auto">
  <name>Task 1: 장면 표를 (motionId, parts) 키로 전환 — 신규 에셋 0으로 무손실 증명</name>
  <files>app/src/lib/illustrationScene.ts, app/src/components/DefectIllustration.tsx, app/src/lib/__tests__/illustrationScene.test.ts, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/golden_probe.ts, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/golden_before.json, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/golden_after.json, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/assets_baseline.sha256, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/sweep_illustration_scene.test.ts</files>
  <action>
**이 태스크에서는 신규 에셋을 등재하지 않는다.** 구조만 바꾸고 거동이 완전히 같음을
증명한다 — 그래야 나중에 거동이 변하면 그 원인이 "신규 에셋"으로 단일하게 귀속된다.

**(a0) 승인 자산 바이트 기준선.** verified_facts (J) 의 6줄에 경로 접두
`app/assets/illustrations/` 를 붙여 quick 디렉터리 `assets_baseline.sha256` 로 저장하고,
리포 루트에서 `shasum -a 256 -c` 가 통과하는지 즉시 확인한다(자 검증). 이후 모든 태스크의
L-10 무접촉 게이트가 이 파일을 쓴다.

**(a) 골든 스냅샷 먼저 (편집 전).** `golden_probe.ts` 를 quick 디렉터리에 만든다. 절대경로로
`app/src/lib/illustrationScene.ts` 를 import 하고, 모션 축 = `등재 6동작 + 미완 4동작
(ref-peter-pan · ref-elbow-twist-sister · ref-pdshape · ref-sideway-spin) + 'ref-unknown-move' +
'' + '__proto__' + 'constructor' + 'toString' + null + undefined`, 부위 축 = `'leg' ·
'shoulder' · 'arm' · 'shoulder+arm' · 'criterion:line' · 'criterion:split_angle' ·
'criterion:dimension_overall_fallback' · '' · '   ' · '+' · '++' · 'legs' · 'LEG' + null +
undefined` 의 **전 조합**에 대해 `{ has: hasIllustrationFor(m,k) }` 를 키 `` `${m}|${k}` `` 로
찍어 정렬된 JSON 으로 저장한다. 편집 **전에** 돌려 `golden_before.json` 에 남긴다.
(오케스트레이터 프로브 확인치 = 110셀 이상 산출됨. 이번엔 축이 더 넓다.)

**(b) 장면 표 자료구조 전환.** `ILLUSTRATION_SCENES` 를 `Record<string, IllustrationScene>` →
**`readonly IllustrationScene[]`** 로 바꾼다. `IllustrationScene` 필드 =
`motionId: string` · `parts: readonly string[]` · `asset: string` · `provenance: string`.
기존 6항목은 `motionId` = 기존 키, `parts`·`provenance` = **기존 문자열 그대로**(수정 금지),
`asset` = **기존 motionId 문자열 그대로**(= 현 require 맵 키와 문자 동일 → 파일·바이트·경로
무접촉, L-10). 신규 항목의 `asset` 은 `{motionId}--{parts를 '-' 로 이은 것}` 규칙으로 짓되,
**`asset` 은 파생 규칙이 아니라 명시 데이터**임을 헤더 주석에 박제한다 — 기존 6항목이 접미
없는 형태로 남는 이유(승인 자산 무접촉)를 같은 주석에 적을 것.

**(c) 판정 함수.** `illustrationMotionForPart` 를 **`illustrationAssetForPart(motionId, partKey):
string | null`** 로 대체한다(반환값 = require 맵 조회 키). 평가 순서는 기존 fail-closed 순서를
그대로 계승: ① motionId 문자열 유효성 ② partKey 문자열 유효성 ③ `partTokensOfKey`(`criterion:`
접두·공백·빈 토큰 → null, P-3) ④ `motionId` 일치 후보 필터 ⑤ `sceneCoversParts` 부분집합
통과분(P-2) ⑥ 0건이면 null / 복수면 **`parts.length` 오름차순, 동률이면 배열 등재 순서 먼저**
= **가장 구체적인 장면이 이긴다**(어깨 항목에는 어깨 전용 그림이, 어깨+팔 항목에는 두 부위를
짚는 그림이 간다). 배열 순회라 프로토타입 키 위험은 원천 소멸하지만 테스트는 유지한다.
`hasIllustrationFor(motionId, partKey): boolean` 은 **시그니처·의미 무변경**으로 이 함수에
위임한다(D — result.tsx 무접촉의 근거). `sceneCoversParts` 는 **무변경 + export 유지**(P-13
테스트 seam). 헤더 주석의 "미구현(의도된 공백) — 어깨·팔 부위용 일러스트 세트" 문단은 이
플랜의 실제 결과로 갱신한다(남으면 거짓 문서가 된다).

**(d) `DefectIllustration.tsx`.** `illustrationAssetForPart` 를 소비하도록 조회 1줄만 바꾼다.
`VERIFIED_ILLUSTRATIONS` 의 기존 6줄은 **문자 하나도 바꾸지 않는다**. props(`motionId`,
`partKey`)·`radius.card`·`aspectRatio: 3/4`·`resizeMode="cover"`·`accessibilityLabel`·null 폴백
전부 무변경(S26·P-10 무회귀). 헤더 주석에 부위별 키 전환 사유 1문단 추가.

**(e) 테스트 갱신.** `illustrationScene.test.ts` 의 **10축을 의미 그대로 보존**하고 열거
방식만 배열에 맞춘다(`REGISTERED` = 장면 배열, 동작 목록은 `[...new Set(scenes.map(s=>s.motionId))]`).
추가 축: **11)** 최구체 우선 — 합성 장면 2개(`parts:['shoulder']` vs `parts:['shoulder','arm']`)
를 `sceneCoversParts` 로 직접 고정하고, 실제 표에 복수 매칭이 존재하면 반환 `asset` 이 더
작은 `parts` 쪽임을 확인. **12)** 중복 금지 — `asset` 값 전건 유일 + 같은 `(motionId, parts집합)`
쌍 중복 0. **13) 부위 어휘 게이트(억지 매칭 차단)** — `parts` 의 각 토큰에 대해 `provenance`
가 그 부위의 한국어 어휘를 **최소 1개** 포함해야 한다(`shoulder`→어깨·견갑 / `arm`→팔·팔꿈치·
엘보·손 / `leg`→다리·무릎·발·골반). 어휘 표는 테스트 파일 1곳에만 둔다. 기존 6항목의
provenance 가 이 게이트를 통과함을 먼저 확인할 것(통과하도록 설계됨 — 통과 못 하면 게이트가
틀린 것이지 provenance 를 고칠 일이 아니다).

**(f) 스위프 포팅.** `2jt/sweep_illustration_scene.test.ts` 를 이 quick 디렉터리로 복사해
새 키 형태에 맞춘다(import 상대경로 `../../../app/src/...` 유지, `criteria/*.yaml` glob 파생
유지 = 동작 목록 하드코딩 0). INV-1~6 보존 + **INV-7 신설**: 임의 (동작 × 부위 키) 조합에서
반환 `asset` 이 결정적이고, 복수 후보가 있으면 `parts.length` 최소가 이긴다. INV-3(에셋 미보유
동작 집합)은 **하드코딩 목록이 아니라 장면 배열에서 파생**하도록 바꾼다 — Task 3 에서 집합이
바뀌므로 고정 목록이면 거짓 FAIL 이 난다. 산출 JSON 은 quick 디렉터리에.

**(g) 무손실 대조.** `golden_probe.ts` 를 다시 돌려 `golden_after.json` 생성 → `diff` **0**.
(신규 에셋 0이므로 `has` 값이 전부 같아야 한다.) 추가로 등재 6항목의 `asset` 이 각자
`motionId` 와 문자 동일함을 확인 = 같은 require 경로 = **같은 바이트가 렌더된다**.

주석은 한국어, 이모지 0, 하드코딩 색/간격 0, 신규 npm 의존성 0. `result.tsx` 무접촉.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && diff .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/golden_before.json .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/golden_after.json && node --test app/src/lib/__tests__/illustrationScene.test.ts && node --test .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/sweep_illustration_scene.test.ts && (cd app && npm run typecheck) && diff <(sed 's://.*::' app/src/lib/illustrationScene.ts | grep -oE "asset: '[^']+'" | sed -E "s/asset: '([^']+)'/\1/" | sort) <(sed 's://.*::' app/src/components/DefectIllustration.tsx | grep -oE "'[^']+': require\(" | sed -E "s/'([^']+)': require\(/\1/" | sort) && git diff --stat -- app/src/app/analysis/result.tsx | grep -c . | grep -qx 0 && shasum -a 256 -c .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/assets_baseline.sha256 && ls app/assets/illustrations | grep -c . | grep -qx 6 && echo GATE-T1-OK</automated>
  </verify>
  <done>golden diff 0 · 단위 테스트 전건 pass(기존 10축 + 신규 3축) · 스위프 INV-1~7 pass · typecheck clean · 두 표 키 목록 diff 0 · `result.tsx` 와 `app/assets/illustrations` diff **0줄**</done>
</task>

<task type="auto">
  <name>Task 2: 생성 대상표 — 데이터로 확정 + 입력 프레임 확보</name>
  <files>.planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/TARGETS.md, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/targets.json, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/emit_census.json</files>
  <action>
**"어느 동작에 어깨·팔 그림이 필요한가"를 동작명 감으로 정하지 말 것.** 아래 두 데이터로만
정한다.

**(a) 방출 집계 재산출(스스로 확인).** verified_facts (A) 표를 그대로 믿지 말고 직접 재계산해
`emit_census.json` 에 남긴다. 입력 = `.planning/quick/260731-iis-.../docs_after/*.json` 4건.
규칙 = `deductionLabels.projectDeductionRecordKeypoints` + `deductionSheet.regionPartKeyForRecord`
와 **같은 규칙**(`angle_vs_reference__{jk}` → 단일 keypoint / `source==='vision'` →
faultJoints ∩ 부위 / 그 외 `CRITERION_REGION_KEYPOINTS` / `dimension_overall_fallback`·
`unit==='score_delta'` → 공집합). Node `.ts` 프로브로 **실제 앱 함수를 import 해서** 돌리면
규칙 사본이 0벌이 된다 — 그렇게 할 것. 산출이 (A) 표와 다르면 **그것이 보고 대상**이다
(evidence-outranks-prior-decisions): 표를 조용히 따르지 말고 차이를 TARGETS.md 에 적는다.

**(b) 33-A1 인용으로 국면·가이드 확정.** `33-A1-MOTION-STANDARDS.md` 표 1·2 에서 대상 동작
행을 읽고 각 (동작 × 부위)마다 다음을 채운다 — `t`(33-14 선정 프레임 시각) · `window`(A-1 국면
창) · `guideType`(`line` | `circle`) · `guideTarget`(무엇 위에 얹는가) · `a1_cite`(①②③④ 중
어느 칸의 어느 문구인가) · `orientation`(도립/직립 — A-1 실측 inv%) · `anchor`(스타일 앵커).

`guideType` 키잉 규칙(L-4): A-1 이 그 부위를 **신전·라인**으로 말하면 `line`, **hook·잠금·
고정·으쓱 금지**로 말하면 `circle`. **굽힘이 정답인 부위에 직선 금지.**
`anchor` 규칙(L-6): 같은 동작의 통과본이 있으면 그것, 없으면 **같은 방위**(도립/직립) 통과본
중 등재 순서 첫 번째. 두 규칙 모두 **데이터 조회**이지 동작명 분기가 아니다.

**a1_cite 를 채울 수 없는 조합은 생성하지 않는다** (없는 코칭을 그림으로 날조하는 것). 제외한
조합은 TARGETS.md 의 별도 절에 사유와 함께 남긴다. 예상 경계선 = `ref-pdshape × shoulder`
(④에 어깨 없음, ②③에만 "어깨 부하 쏠림"/"어깨로 버텨") · `ref-foxtop-split × shoulder|arm`
(④에 상체 없음).

**(c) 우선순위.** Tier 1 = (a) 에서 실제로 방출된 조합(= belle 확인 ③ 화면에서 열린다).
Tier 2 = A-1 ④가 그 부위를 짚지만 4건 doc 에는 안 나온 조합. **Tier 1 4건이 이 플랜의
약속**이고 Tier 2 는 남는 예산으로만 간다(§budget). 순위 1번은 **ref-power-spin × shoulder** —
그 doc 하나로 "어깨 시트에 새 그림이 붙는다"와 "다리 시트는 그대로다"를 **동시에** 화면
확인할 수 있다.

**(d) 입력 프레임 확보 (PII 주의).** 대상 동작의 기준 영상을 `aws s3 cp
s3://sunity-motion-pilot-videos/reference/{motionId}.mp4 --profile sunity-motion --region
ap-northeast-2` 로 **스크래치패드**에 받는다. **리포에 절대 두지 말 것** — `~` 가 git 저장소라
인물 실사는 PII 위험이다(memory: home-dir-is-git-repo-pii-hazard). ffmpeg 로 `-ss {t}` 단일
프레임 추출(`-frames:v 1`). 대상 부위가 그 t 에 가려졌으면(33-14 climb 5.00s 머리카락 가림
선례) A-1 창 안에서 ±0.25s 씩 4컷을 더 뽑아 콘택트 스트립으로 열람 후 교체하고, 교체 사유를
TARGETS.md 에 적는다. 그다음 PIL 로 **대상 부위 중심 상반신 크롭 → 3:4** 를 만든다(L-6 자세
후퇴 대응이자 L-9 구도 대응). 크롭본도 스크래치패드에만 둔다.

**추출·크롭 결과를 Read 로 직접 열어** 대상 부위가 실제로 보이는지 확인한 뒤 다음으로 간다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && python3 -c "
import json,sys,os
t=json.load(open('.planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/targets.json'))
rows=t['targets'] if isinstance(t,dict) else t
assert len(rows)>=4, 'Tier1 4건 미만'
req={'motionId','part','tier','t','guideType','guideTarget','a1_cite','anchor','inputFrame'}
for r in rows:
    miss=req-set(r); assert not miss, (r.get('motionId'),r.get('part'),miss)
    assert r['guideType'] in ('line','circle'), r
    assert isinstance(r['a1_cite'],str) and len(r['a1_cite'].strip())>=10, r
    assert os.path.exists(r['inputFrame']), r['inputFrame']
t1=[r for r in rows if r['tier']==1]
assert len(t1)==4, ('Tier1 = 4건이어야 한다', len(t1))
print('GATE-T2-OK rows=',len(rows),'tier1=',len(t1))
" && git status --porcelain .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect | grep -E '\.(mp4|mov)$' | grep -c . | grep -qx 0 && echo NO-PII-IN-REPO</automated>
  </verify>
  <done>`targets.json` 전 행이 a1_cite·guideType·anchor·inputFrame 을 갖고 Tier 1 이 정확히 4건 · 제외 조합이 사유와 함께 TARGETS.md 에 기록 · 입력 프레임/크롭이 스크래치패드에만 존재(리포에 영상·실사 0) · 프레임을 직접 열람함</done>
</task>

<task type="auto">
  <name>Task 3: 생성 + 4게이트 전수 검수 (Tier 1 4건, 조합당 상한 3회)</name>
  <files>.planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/gen/, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/REVIEW.md, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/generate.py</files>
  <action>
33-14 레시피(L-4)를 **그대로** 실행한다. 규칙을 개선하려 들지 말 것 — S24 는 이미 PASS 다.

**(a) 호출.** `generate.py`(표준 라이브러리 `urllib` 만, 신규 패키지 0) 로
`gemini-3-pro-image:generateContent` 를 호출한다. 키는 SSM 에서 읽어 **환경변수로만** 쓰고
스크립트·로그·커밋 어디에도 문자열로 남기지 않는다. `generationConfig.responseModalities =
["TEXT","IMAGE"]`. inlineData 파트 2개 = ① `targets.json` 의 `inputFrame`(상반신 크롭)
② `anchor` 이미지. 프롬프트 3요소 = **자세 충실**(입력 프레임과 동일 자세·동일 방위·폴 위치
유지) + **익명화**(이목구비 제거) + **가이드 표시**(`guideType`·`guideTarget` 을 그대로 문장에
넣는다 — 파이썬에 동작명 조건 분기 0, 전부 `targets.json` 소비). 출력은 3:4.

**(b) 검수 — 생성 전량 Read 육안.** 매 산출물을 예외 없이 Read 로 연다. 게이트 4종을
`REVIEW.md` 에 **33-14 형식 표**로 판정한다: `동작 | 부위 | try | 판정 | 세부(실패 사유)`.
PASS 후보는 추가로 ① **2x 확대 크롭**(가이드 표시부 · 손발 · 얼굴)을 PIL 로 만들어 열람
② **입력 프레임 원본과 나란히 대조**(자세 복제 여부). 이 두 단계를 거치지 않은 것은 PASS 로
적지 않는다.

**(c) 실패 대응(L-6).** 자세 복제(앵커 자세로 후퇴)가 나오면 ① 입력 인물 크롭을 더 좁혀
확대 ② 같은 방위의 다른 통과본으로 앵커 교체. **조합당 상한 3회.** 소진하면 그 조합은
**미완**으로 정직 기록하고 넘어간다 — 억지로 통과시키지 않는다(L-7).

**(d) 예산 규칙.** Tier 1 4건이 약속이다. 4건을 끝낸 시점에 컨텍스트 여유가 **40% 이상** 남아
있을 때만 Tier 2 를 `targets.json` 순서대로 이어간다. 예산으로 시도하지 못한 조합은
"시도 안 함(예산)"으로 REVIEW.md 에 명시한다 — **조용한 누락 금지.**

**(e) 산출물 보관.** 생성분은 탈락본 포함 `gen/` 에 둔다(익명화된 일러스트라 PII 아님).
확대 크롭·대조 컷 등 파생 이미지가 커지면 `gen/.gitignore` 로 파생분만 제외하고 **원 생성분과
대표 확대컷은 커밋**한다(검수 증거). **입력 실사 프레임은 여기 두지 말 것.**

**REVIEW.md 에 표가 없는 그림은 Task 4 에서 등재 금지.**
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect && test -s REVIEW.md && python3 -c "
import re,glob,os,sys
md=open('REVIEW.md',encoding='utf-8').read()
gen=[os.path.basename(p) for p in glob.glob('gen/*.jpg')+glob.glob('gen/*.png') if '_2x' not in os.path.basename(p) and 'compare' not in os.path.basename(p)]
assert gen, 'gen/ 산출물 0건'
missing=[g for g in gen if g not in md]
assert not missing, ('검수 표에 없는 생성물: ', missing)
body=[l for l in md.splitlines() if not l.strip().startswith('#')]
rows=[l for l in body if l.count('|')>=5 and ('PASS' in l or 'FAIL' in l)]
assert len(rows)>=len(gen), ('판정 행 부족', len(rows), len(gen))
assert re.search(r'(미완|시도 안 함|상한 소진|해당 없음)', md), '정직 기록 절 없음'
print('GATE-T3-OK gen=',len(gen),'rows=',len(rows))
" && ! grep -rlE 'AIza[0-9A-Za-z_-]{20,}' . && echo NO-KEY-LEAK</automated>
  </verify>
  <done>`gen/` 전 산출물이 REVIEW.md 4게이트 표에 행을 갖는다 · PASS 후보는 2x 확대 + 입력 대조 열람 기록이 있다 · 미완/미시도 조합이 사유와 함께 명시돼 있다 · API 키 문자열 리포 유출 0</done>
</task>

<task type="auto">
  <name>Task 4: 등재 + 구도 실측 + 게이트/회귀 + 시뮬 렌더 확인</name>
  <files>app/assets/illustrations/, app/src/lib/illustrationScene.ts, app/src/components/DefectIllustration.tsx, app/src/lib/__tests__/illustrationScene.test.ts, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/REVIEW.md, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/composition.json, .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/sweep_illustration_scene.json</files>
  <action>
**(a) 구도 실측 — 자부터 검증.** 2jt 와 **같은 자**로 잰다: 배경 픽셀 = `min>225 ∧
(max−min)<22`, 비배경 비율 = 1 − 배경/전체. 먼저 **기존 6장을 재서** verified_facts (I) 의
수치(11.1 / 11.3 / 12.6 / 14.8 / 17.4 / 17.6)를 재현하는지 확인한다 — 재현 못 하면 자가
틀린 것이니 자를 고치고, 그 사실을 적는다. 그다음 PASS 신규분을 같은 자로 재서
`composition.json` + REVIEW.md 표에 남긴다. 신규분이 기존 최댓값 **17.6% 를 넘지 못하면**
남은 시도 횟수가 있는 한 입력 크롭을 더 좁혀 **1회** 재생성한다. 두 번째도 못 넘으면
**"구도 개선 못 함"으로 정직 기록**한다(억지 후처리 금지).

**(b) 등재.** PASS 분만 `app/assets/illustrations/{asset}.jpg` 로 저장한다 — **720x964(3:4)
리사이즈**(기존 6장과 동일 규격, S26 렌더 경로 정합 유지). `ILLUSTRATION_SCENES` 에 항목 추가:
`motionId` · `parts`(L-3·L-8 — 가이드 표시가 실제로 얹힌 부위만) · `asset` · `provenance`.
`provenance` 는 **문서 근거 + 실물 열람 결과**를 함께 담고 문자열 `'실물 열람'` 을 포함해야
하며(테스트 8) 각 토큰의 부위 어휘를 포함해야 한다(테스트 13). `VERIFIED_ILLUSTRATIONS` 에
같은 `asset` 키로 `require` 를 추가한다. **기존 6줄 무접촉.**

**(c) 게이트·회귀 전수.** ① 두 표 키 목록 diff 0 ② 단위 테스트 전건(신규 항목이 13축 전부
통과) ③ 스위프 재실행 — INV-3 이 파생이므로 에셋 보유 집합이 바뀐 채로 통과해야 하고,
INV-4(부착 ⇔ 부분집합, 양방향) 반례 0, INV-6 부착 하한 상승 확인 ④ `npm run typecheck`
⑤ `PYTHONPATH=backend/tests python3 -m pytest backend/tests -q` FAILED/ERROR **node ID 집합**을
baseline(58건)과 대조해 **diff 0**(수치가 아니라 집합) ⑥ `git diff --stat -- app/src/app/analysis/result.tsx`
**0줄** ⑦ 기존 6장 파일 **sha256 불변** ⑧ `golden_before.json` 대비 신규 `has` 가 **true 로만**
바뀌었는지 확인(false 로 뒤집힌 셀이 있으면 기존 부착을 깬 것 = 즉시 FAIL).

**(d) 시뮬 렌더 확인.** 신규 `require` 는 Metro **재시작**이 필요하다(fast refresh 로는
번들에 안 들어온다). 앱 uid = `fvcNXzEqKjgqVxRPVSj1iwFnIpn2`. `.continue-here.md` "시뮬 검증
요령" 준수: **LogBox 배너 우측 X 를 먼저 눌러 치울 것**(하단 탭을 가로챈다), **AX 프레임 y 가
화면(874) 밖이면 스크롤로 넣고 탭할 것**. 확인 항목은 아래 `<verify>` 의 `<human-check>` 표
그대로. 실행자에게 시뮬 도구가 없으면 **PASS 를 주장하지 말고** 그 표를 그대로
"오케스트레이터 확인 요청"으로 SUMMARY 에 옮긴다(2jt 선례).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && node --test app/src/lib/__tests__/illustrationScene.test.ts && node --test .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/sweep_illustration_scene.test.ts && (cd app && npm run typecheck) && diff <(sed 's://.*::' app/src/lib/illustrationScene.ts | grep -oE "asset: '[^']+'" | sed -E "s/asset: '([^']+)'/\1/" | sort) <(sed 's://.*::' app/src/components/DefectIllustration.tsx | grep -oE "'[^']+': require\(" | sed -E "s/'([^']+)': require\(/\1/" | sort) && git diff --stat -- app/src/app/analysis/result.tsx | grep -c . | grep -qx 0 && shasum -a 256 -c .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/assets_baseline.sha256 && node .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/golden_probe.ts > /tmp/golden_final.json && python3 -c "
import json
b=json.load(open('.planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/golden_before.json'))
a=json.load(open('/tmp/golden_final.json'))
flip=[k for k in b if b[k]['has'] and not a.get(k,{}).get('has')]
assert not flip, ('기존 부착이 사라졌다: ', flip[:10])
gain=[k for k in a if a[k]['has'] and not b.get(k,{}).get('has')]
print('GATE-T4-OK 신규부착=',len(gain),'소실=0')
" && PYTHONPATH=backend/tests python3 -m pytest backend/tests -q 2>&1 | grep -E '^(FAILED|ERROR)' | sort > /tmp/pytest_after_ids.txt; diff /tmp/pytest_after_ids.txt <(grep -E '^(FAILED|ERROR)' .planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/pytest_after.txt | sort) && echo PYTEST-NODEID-DIFF-0</automated>
    <human-check>
시뮬레이터 렌더 확인 (Metro **재시작** 후):

| # | 항목 | 도달 경로 | 무엇을 보면 PASS |
|---|---|---|---|
| V-1 | **신규 부착** | 파워스핀 doc(60점, 카드 4) → 부위 칩 `어깨` → 시트 최하단 | 어깨를 가리키는 일러스트가 **보인다**(가이드 표시가 어깨/견갑 위) |
| V-2 | **무회귀 — 다리** | 같은 doc → 부위 칩 `다리` → 시트 최하단 | 종전과 **같은** 다리 일러스트가 같은 자리(facing 다음 최하단)에 보인다 |
| V-3 | **3:4 유지** | V-1 시트 | 세로 늘어남·좌우 잘림·레터박스 빈 띠 0 |
| V-4 | **팔 시트** | 엘보 doc(63점, 카드 **5**) → 부위 칩 `팔` → 시트 최하단 | 팔(팔꿈치)을 가리키는 일러스트. 같은 doc `어깨` 칩도 확인 |
| V-5 | **fail-closed 유지** | 미등재 조합 시트(예: pdshape doc `다리` 이외) / mode3 doc | 자리 **자체가 없음** — 빈 카드·점선 박스·"준비 중" 0 |
| V-6 | **구도** | V-1·V-4 시트 | 인물이 프레임을 채워 "빈 배경 프레임"(belle #11)으로 읽히지 않는다 |
| V-7 | **신규 경고 0** | Metro stdout | `expo-video allowsFullscreen` deprecation 2건 외 신규 경고 0 |

도구 없어 못 봤으면 **미검증으로 남길 것 — PASS 주장 금지.**
    </human-check>
  </verify>
  <done>PASS 분만 등재 · 기존 6장 `assets_baseline.sha256` 대조 통과(바이트 불변) · 두 표 diff 0 · 단위/스위프/typecheck 전건 pass · pytest node ID 집합 diff 0 · golden 소실 셀 0 · 구도 실측 표 기록 · 시뮬 V-1~V-7 결과(또는 미검증 사유) 기록</done>
</task>

</tasks>

<budget>
- Tier 1 **4건**(`ref-power-spin×shoulder` · `ref-elbow-twist-sister×shoulder` ·
  `ref-elbow-twist-sister×arm` · `ref-kip-up×shoulder`) = 이 플랜의 약속. 조합당 생성 상한 3회.
- Tier 2 는 Tier 1 완료 후 컨텍스트 여유 40% 이상일 때만. 미시도분은 REVIEW.md 에 명시.
- **전 등재 조합(10동작 × {shoulder, arm, shoulder+arm})을 이 플랜이 덮지 않는다.** 남는 조합은
  화면에서 조용히 미부착으로 남고(fail-closed), 그 목록을 SUMMARY 에 그대로 넘긴다 — 이것이
  33-14 가 세운 정직 미완 처리이며 숨김이 아니다.
</budget>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Gemini API ↔ 로컬 | 외부 생성 이미지가 앱 번들 자산으로 유입 |
| SSM ↔ 프로세스 env | Gemini API 키가 평문으로 프로세스에 들어옴 |
| 스크래치패드 ↔ git 리포 | 인물 실사 프레임(PII)이 커밋 경로로 넘어갈 수 있음 |
| 장면 표 ↔ 렌더 | 근거 없는 토큰이 화면의 "틀린 그림"이 됨 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-33C4-01 | Spoofing | `ILLUSTRATION_SCENES.provenance` | mitigate | 실물 열람 없는 등재 차단 — 테스트 8(`'실물 열람'` 문자열 강제) + 신규 테스트 13(부위 어휘 게이트) + REVIEW.md 표에 행 없는 그림 등재 금지 |
| T-33C4-02 | Tampering | 승인 자산 6장 / `result.tsx` | mitigate | 기존 6장 sha256 불변 + `git diff --numstat app/assets/illustrations` 삭제·수정 0 + `result.tsx` diff 0줄 게이트 |
| T-33C4-03 | Tampering | 판정 규칙 전환 | mitigate | golden 스냅샷 전/후 diff 0(신규 에셋 0 상태) + 최종 golden 에서 `has: true → false` 뒤집힘 0 |
| T-33C4-04 | Information Disclosure | Gemini API 키 | mitigate | SSM → env 만, 스크립트/로그/커밋에 문자열 0 (`grep -rlE 'AIza[0-9A-Za-z_-]{20,}'` 게이트) |
| T-33C4-05 | Information Disclosure | 정은지 실사 프레임(PII) | mitigate | 스크래치패드/`/Users/Shared` 전용, 리포 커밋 0 (`git status --porcelain` mp4/실사 0 게이트). memory: home-dir-is-git-repo-pii-hazard |
| T-33C4-06 | Denial of Service | Gemini 크레딧 | accept | 조합당 상한 3회로 소진 한계. 고갈 시 미완 정직 기록(선례 = gemini-credits-depleted) |
| T-33C4-SC | Tampering | 패키지 설치 | mitigate | **신규 npm/pip 설치 0** — `package.json`·lock·`requirements*.txt` 무변경. 설치 태스크가 없으므로 Package Legitimacy Gate 비해당 |
</threat_model>

<verification>
1. **생성 전량 Read 육안 + 4게이트 판정 표** (33-14 형식). PASS 후보는 2x 확대 크롭 + 입력
   프레임 대조. **표에 없는 등재 금지.**
2. **구도 실측** — 2jt 와 같은 자(`min>225 ∧ max−min<22`)로 기존 6장 재현 확인 후 신규분 측정.
   개선 못 하면 정직 기록.
3. **부위별 키 전환 무손실** — golden 스냅샷 diff 0(신규 에셋 0 상태) + 기존 6항목 `asset` ==
   `motionId`(같은 require 경로 = 같은 바이트) + 최종 golden 에서 부착 소실 셀 0.
4. **두 표 키 목록 일치 게이트**가 새 키 형식에서 작동(주석 제거 후 diff 0).
5. **시뮬 렌더** — V-1~V-7 (Task 4 `<human-check>`). 못 봤으면 미검증으로 남긴다.
6. **회귀** — `npm run typecheck` · `node --test illustrationScene.test.ts` · 스위프 INV-1~7 ·
   `pytest backend/tests` FAILED/ERROR **node ID 집합** diff 0(baseline 58) · `result.tsx` diff 0줄.
</verification>

<success_criteria>
- 어깨/팔 항목 시트에 **그 부위를 가리키는** 일러스트가 붙고, 다리 시트 거동은 종전과 동일하다.
- 등재된 신규 에셋 전건이 4게이트 판정 표 + `provenance`(실물 열람 + 부위 어휘)를 갖는다.
- 생성 대상 (동작 × 부위)가 **실 doc 방출 집계 + 33-A1 인용**으로 정해졌고 근거가 파일로 남았다.
- 기존 6장의 파일·바이트·require 키·부착 거동이 하나도 변하지 않았다.
- 시도했으나 못 만든 조합, 예산으로 못 간 조합이 **전부 이름과 사유로** 기록됐다.
</success_criteria>

<anti_patterns severity="blocking">
| Anti-pattern | 설명 |
|---|---|
| code-only-verification | 코드 통과 ≠ 완료. 생성 이미지를 **전량 직접 열어** 게이트 판정하고, 화면 렌더까지 본다 |
| single-motion-fixation | 가이드 종류·앵커·국면은 **데이터 조회**(targets.json ← 33-A1). 동작명 문자열 분기 0 |
| over-generalize-breaks-approved | 키 전환이 기존 6장 거동(S13/S25/S26 PASS)을 깨면 실패. golden·sha256·result.tsx diff 게이트로 봉인 |
| repair-rediscussion | 33-14 레시피·4게이트를 바꾸지 말 것. 단 **데이터가 결정과 안 맞으면 보고**(재논의 아님) |
| 억지 매칭 | 부착 건수를 위해 토큰을 넓게 주지 말 것. 확신 없으면 **빼는** 쪽이 정답(D-43) |
| 조용한 누락 | 미완·미시도 조합을 표에서 빼지 말 것. 이름과 사유로 남긴다 |
</anti_patterns>

<output>
Create `.planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/260731-plf-SUMMARY.md` when done.

SUMMARY 에 반드시 포함:
- 4게이트 전수 판정 표 + 구도 실측 표
- 등재 조합 / 미완 조합 / 미시도 조합 **세 목록**
- 키 전환 무손실 증거(golden diff · sha256 · result.tsx diff 0줄)
- 시뮬 V-1~V-7 결과 또는 "미검증 + 사유" (도구 없으면 오케스트레이터 확인 요청 표로)
- 33-G 표 재채점 **제안**(S13/S24/S25/S26) — 판정 확정은 오케스트레이터 몫
</output>
