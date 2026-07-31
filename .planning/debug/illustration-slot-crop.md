---
slug: illustration-slot-crop
status: awaiting_human_verify
trigger: "일러스트 슬롯이 에셋을 잘라낸다 (33-G V-3, 선행 결함)"
created: 2026-07-31
updated: 2026-07-31
---

# illustration-slot-crop — 일러스트 슬롯이 에셋을 잘라낸다 (33-G V-3)

## Symptoms

**1. Expected behavior**
`DefectIllustration` 카드가 3:4 에셋(720x964) 전체를 잘림 없이 보여준다. 시뮬 iPhone 16 Pro
(402x874pt)에서 카드 폭이 360pt 이므로 기대 박스 = **360 x 482pt**.
일러스트는 **전신 기하가 곧 메시지**다 — 가이드 선/원이 어느 부위에 얹혔는지가 판정 축이라
잘리면 축 자체가 전달되지 않는다 (33-G S13/S25, belle 확인 ② #11 "빈 프레임" 인접).

**2. Actual behavior**
카드가 약 **360 x 260pt** 로 잡혀 이미지의 약 **54%만** 보인다.
`overflow: 'hidden'` 이라 나머지는 잘린다.

**3. Error messages**
없음. 크래시·경고 0. 순수 레이아웃 문제라 typecheck·테스트로는 안 잡힌다.
(LogBox 배너는 뜨지만 정체 = `expo-video allowsFullscreen` deprecation 2건, 이 건과 무관.)

**4. Timeline**
**선행 결함 — 이번 사이클이 원인이 아니다.** 33-14 승인 자산(`ref-power-spin.jpg`,
바이트 무접촉)에서도 동일하게 발생한다. 33-14 는 시뮬 확인을 33-16 으로 이연했고
quick-260731-2jt 는 재생 중 캡처를 못 담아 미검증으로 남겼다 —
**이 슬롯이 실제로 렌더되는 것을 사람이 본 것은 2026-07-31 이 처음**이다.

**5. Reproduction**
기록 탭 → "프로 비교, 26.07.30, 파워스핀, 60" → 결과 화면 스크롤 →
"다리 부위 상세 보기" 칩 탭 → 시트 최하단 일러스트.
어깨 경로 = 같은 doc 에서 "어깨 부위 상세 보기" 칩 (신규 에셋 `ref-power-spin--shoulder.jpg`).

## Evidence

- timestamp: 2026-07-31 (오케스트레이터 직접 실측, 통제 비교)
  **같은 에셋 `app/assets/illustrations/ref-power-spin.jpg`(전신 + 발끝→골반→발끝 붉은 직선,
  720x964) 를 파일로 열어놓고 화면과 대조:**
  - 수정 전: 화면에 **위쪽 발/정강이만 약 3배 확대**. 스크롤하면 무릎·종아리가 이어서 나옴
    → 이미지가 카드보다 훨씬 크게 깔리고 카드 `overflow:hidden` 이 잘라내는 형상.
  - 수정 후(main `bff3a477` — Image 크기를 `onLayout` 실측 폭에서 직접 계산,
    `width=boxW, height=boxW*964/720`): **확대율 약 1/2 로 감소**, 폴 받침·바닥까지 보임.
    → Image 쪽 크기는 잡혔다.
  - 그러나 카드 박스는 **여전히 약 360x260pt**.

- timestamp: 2026-07-31 (측정 방법)
  시뮬 스크린샷 원본 1206x2622 → 2.289 px/pt. 카드 좌우 경계 x=47..872px = 360pt,
  상하 경계 y=600..1195px = 260pt.
  ⚠ **AX 트리에 Image 프레임이 안 나온다**(`accessible` 미지정) — 그래서 픽셀 측정을 썼다.
  더 정확한 계측 수단(예: 임시 `onLayout` 로그, `accessible` 부여)이 필요할 수 있다.

- timestamp: 2026-07-31 (무효 처리한 관측 — 재유도 금지)
  "Metro 가 옛 번들을 준다"고 한때 판단했으나, `curl localhost:8081/index.bundle` 응답이
  **4988 바이트**뿐이라 그 확인 자체가 무효였다. **철회함.** 결론은 통제 비교로만 냈다.

- timestamp: 2026-07-31 (debug 사이클 — 임시 계기 배선 후 실측)
  **계기 2종이 일치했고, 증상 전제가 뒤집혔다.** `DefectIllustration` 카드에 임시
  `accessible` + `accessibilityLabel`(RN `onLayout` 수치)을 달고 `idb ui describe-all` 로 읽음:
  - 네이티브 AXFrame = `{{20, 527}, {362, 484.67}}`
  - RN onLayout 라벨 = `DBGCARD w=362 h=485 boxW=362 want=485 imgW=362 imgH=485 asset=ref-power-spin`
  → **카드는 이미 362 x 484.7pt 이고 Image 도 같은 값이다.** 기대치(폭 362 → 362x964/720 =
  484.7)와 **정확히 일치**한다. 260 은 어디에도 없다.

- timestamp: 2026-07-31 (260 의 정체 — 재현으로 확정)
  260 은 **카드 높이가 아니라 뷰포트에 보이는 조각**이었다.
  시트 ScrollView 뷰포트 = 화면 y 264..776 (= 512pt).
    · 시트 top = 874 − round(874*0.78) = 192, +paddingTop 12 +handle 20 +titleRow 44 → 264
    · CTA `닫기` AXFrame y=792 (h=50), marginTop 16 → 뷰포트 하단 776
  카드(485)는 뷰포트(512)보다 **27pt 작을 뿐**이라, 스크롤 위치가 조금만 어긋나도 잘려 보인다.
  - **최하단 스크롤(스크롤 끝)**: 카드 AXFrame y=41.7..526.3 → 보이는 구간 264..526 = **262pt**.
    ← 오케스트레이터의 "360x260" 이 정확히 이 값이다. 그림의 **아래쪽**(정강이·발·폴 받침)만
    보인다 — 카드가 260 이고 위에서 잘렸다면 **위쪽**(골반·허벅지)이 보였어야 한다. 방향이
    반대라는 점이 "카드 260" 가설을 자체 반증한다.
  - 스크롤을 되돌려 카드 AXFrame y=262.3..747.0 (뷰포트 안)로 앉히면 **전신이 한 장에 다 보인다**
    (발끝→골반→발끝 붉은 직선 전체 + 폴 받침 + 바닥 — 스크린샷 육안 확인).

- timestamp: 2026-07-31 (px/pt 환산 불일치 해소 — 양쪽 다 맞았다)
  네이티브 스크린샷은 `sips` 실측 1206x2622 = **3.0 px/pt** 이 맞다. 그런데 Read 툴이 이미지를
  장변 2000px 로 다운샘플해서 모델에 보여준다("original 1206x2622, displayed at 920x2000").
  그 공간에서는 2000/874 = **2.289 px/pt** 라, 세션 파일의 2.289 도 **그 자체로는 옳았다**.
  즉 260 은 환산 오류가 아니라 **스크롤 위치 때문에 잘린 조각을 잰 것**이다.

- timestamp: 2026-07-31 (`aspectRatio` 축 — 직접 실험으로 종결)
  카드 스타일을 `{ aspectRatio: 3/4 }` 로 임시 교체하고 AXFrame 을 읽음:
  **w=362.00, h=482.67**. `362 / 0.75 = 482.67` — 소수점까지 일치.
  → RN 0.81.5 + New Architecture 의 `aspectRatio` 는 **문서대로 width/height** 다.
  Fabric 특이동작 **없음**. Eliminated 1번의 "방향 불일치"는 존재하지 않았다.
  (482.67 vs 484.67 은 2pt 차이라, 스크롤 조각을 재던 종전 방식으로는 둘 다 "약 260"으로
   보였다 — 그래서 `width*0.75 = 271` 로 오독됐다.)

- timestamp: 2026-07-31 (에셋 전수 — 일반화 확인)
  `sips` 로 `app/assets/illustrations/*.jpg` **9/9 전부 720x964** (h/w = 1.33889) 실측.
  코드 상수 `ASSET_H_OVER_W = 964/720 = 1.33889` 와 동일 → `resizeMode="cover"` 가
  **어느 에셋에서도 잘라낼 여백이 없다**. 파워스핀 전용 해결이 아니다.

- timestamp: 2026-07-31 (임시 계기 제거 후 재측정 — 계기 없이도 같은 값)
  임시 배선을 전부 걷어낸 최종 코드에서, **상시 존재하는 AXFrame 만으로** 카드 박스를 산출:
    · facing infoBox 텍스트 AXFrame y=1830.7 h=125 (+ padding 7 + border 1) → 박스 1822.7..1963.7
    · 다음 형제 bullets 첫 줄 AXFrame y=2476.3, x=20, **w=362**
    · `scrollContent` 의 `gap: 14` 를 사이에 두고 → 카드 = 1977.7 .. 2462.3
  → **362 x 484.60pt**, 기대 484.68 과 **오차 0.08pt**. 계기 유무와 무관하게 같은 값이다.

- timestamp: 2026-07-31 (화면 확인 — 최종 코드, 계기 0)
  파워스핀 **다리 시트**: 전신 1장 (발끝→골반→발끝 붉은 직선 **전체** + 폴 천장~받침 + 바닥).
  파워스핀 **어깨 시트**(`ref-power-spin--shoulder.jpg`): 전신 1장 (폴 잡은 손 ~ 어깨 붉은 원 ~
  다리). 두 시트 모두 **잘림 0**.

## Eliminated

- hypothesis: `aspectRatio: 3/4` 를 Image 에서 카드(View)로 옮기면 박스가 3:4 로 잡힌다
  result: ~~기각 (카드가 360x262 = width x 0.75)~~ → **2026-07-31 재심: 이 기각 자체가 오측이었다.**
  실제로는 h = 482.67 = `362/0.75` 로 **정상 동작했다**(직접 실험). 262 는 카드 높이가 아니라
  스크롤 조각이었다. RN `aspectRatio` 축 의혹은 **해소** — 문서대로 width/height.

- hypothesis: 자식 Image 높이를 키우면 카드가 따라 커진다
  result: **기각 유지 (사유는 정정).** RN 은 자식 높이를 부모로 밀어올리지 않으므로 이 가설은
  원래 성립하지 않는다. 다만 "카드 260 유지"라는 관측 근거는 오측이었다.

- hypothesis: 카드에 실측 높이를 직접 주면 된다
  result: ~~기각 (260 유지)~~ → **재심: 이것이 정답이었다.** `bff3a477` 이 바로 이 수정이고,
  적용 후 카드는 실제로 **362x484.67** 이 됐다. "260 유지"는 오측이라 기각이 잘못됐다.

- hypothesis: 카드 높이를 `DefectIllustration` **밖**(시트 ScrollView 제약 / 소비처 2개 혼선)에서
  누가 눌러 260 으로 고정한다
  result: **기각.** 카드 높이는 `DefectIllustration` 이 준 값 그대로(484.67) 잡힌다.
  소비처 2개는 실재하나 혼선의 원인이 아니다 — 시트 슬롯(`result.tsx:3305`)은 폭 362,
  `VideoCompare` illu-float(`:1854`)는 **패널폭 × 104/360 ≈ 51pt** 짜리 절대배치 카드이고
  `voiceCueRecordId != null` (음성 재생 중)에만 렌더된다. 시트는 Modal 이라 화면을 덮으므로
  두 인스턴스가 한 화면에서 섞여 보일 수 없다. 260 과도 무관한 크기다.

## Current Focus

reasoning_checkpoint:
  hypothesis: >
    보고된 "카드가 360x260 이라 에셋의 54% 가 잘린다"는 **증상 자체가 성립하지 않는다.**
    카드는 `bff3a477` 이후 이미 362x484.67pt 이고 에셋 전체를 보여준다. 260 은 시트
    ScrollView 뷰포트(512pt)에 **보이던 조각**이며, 최하단까지 스크롤한 상태에서 잰 값이다.
  confirming_evidence:
    - "네이티브 AXFrame = {362, 484.67} / RN onLayout = 362x485 — 계기 2종 일치 (직접 실측)"
    - "계기 제거 후 상시 AXFrame(facing 박스 + bullets + gap 14)만으로 362x484.60 재산출 — 오차 0.08pt"
    - "화면 확인: 다리·어깨 시트 모두 전신이 한 장에 다 보임 (붉은 직선 전체 + 폴 받침)"
    - "최하단 스크롤에서 카드 AXFrame y=41.7..526.3 → 뷰포트 264..776 과 겹치는 구간 = 262pt (260 재현)"
    - "보이던 것이 그림의 **아래쪽**이었다 — 카드가 260 이고 위에서 잘린 거라면 위쪽이 보였어야 한다 (자체 반증)"
    - "`aspectRatio: 3/4` 직접 실험 → h=482.67=362/0.75. RN 문서대로 width/height, Fabric 특이동작 없음"
    - "에셋 9/9 전부 720x964 (sips 전수) → cover 가 잘라낼 여백 0"
  falsification_test: >
    카드를 뷰포트 안에 온전히 앉힌 상태에서 그림 일부가 여전히 잘려 보이면 이 판정은 틀렸다.
    → 실행함. 다리 시트(카드 262.3..747.0)·어깨 시트 모두 **전체가 보였다.**
  fix_rationale: >
    레이아웃 결함이 없으므로 **레이아웃은 손대지 않는다.** 실제 수리 대상은 `bff3a477` 이
    코드에 남긴 오진 주석이다 — "카드가 여전히 360x260, 원인 미규명"이라고 단정해 두어
    다음 사람을 없는 버그로 보낸다. 그 주석을 실측 근거와 함께 정정하는 것이 수리다.
    (기능 diff 0 — `git diff` 상 변경은 주석 라인뿐임을 확인.)
  blind_spots:
    - "계산만 하고 **재보지 않은 것**: 작은 화면(iPhone SE 375x667)에서는 뷰포트≈350 < 카드 448.5 라
       전체가 한 화면에 안 들어온다는 산수. **시뮬로 확인 안 했다.** 아래 '남은 관찰' 참조."
    - "확인한 기기는 iPhone 16 Pro(402x874) 하나뿐. 다른 실기기 미확인."
    - "`VideoCompare` illu-float(약 51pt) 는 코드로만 읽었고 **음성 재생 중 화면으로는 못 봤다** — 미검증."
    - "다리·어깨 2개 시트만 화면 확인. 나머지 7개 에셋은 크기 산수(720x964 실측)로만 커버."

next_action: >
  belle 확인 대기 (human-verify). 확인 후 debug 세션 archive + 커밋.

## Constraints

- 판정 로직 `app/src/lib/illustrationScene.ts` **무접촉** (33-G S13/S25 PASS 유지).
- 에셋 바이트 **무접촉** (`app/assets/illustrations/*.jpg` 9장, sha256 게이트 있음).
- 백엔드 무접촉.
- 스택: RN 0.81.5 / React 19.1.0 / New Architecture `newArchEnabled: true` / Expo SDK 54.
- theme 토큰만, 하드코딩 색상·간격 0, 이모지 0 (app/CLAUDE.md).

## Verification requirement (코드 통과 ≠ 완료)

1. 시뮬에서 **같은 에셋 `ref-power-spin.jpg` 다리 시트를 직접 열어** 전신(발끝→골반→발끝
   붉은 직선 전체 + 폴 받침)이 한 장에 들어오는지 **화면으로** 확인.
2. 카드 박스를 **수치로** 재서 360x482 도달 여부를 보일 것 (픽셀 자가 아닌 실측 수단 권장).
3. 어깨 시트(신규 에셋 `ref-power-spin--shoulder.jpg`)도 함께 확인.
4. `npm run typecheck` PASS + `node --test app/src/lib/__tests__/illustrationScene.test.ts`.

## Resolution

root_cause: >
  **보고된 결함은 존재하지 않았다 (오측).** 카드는 `bff3a477` 이후 이미 362 x 484.67pt 이고
  `resizeMode="cover"` + 에셋 전수 720x964 라 잘림이 0 이다. "360x260" 은 카드 높이가 아니라
  **시트 ScrollView 뷰포트(화면 y 264..776 = 512pt)에 보이던 조각**이었다. 카드(485)가
  뷰포트(512)보다 27pt 작을 뿐이라, 시트 최하단까지 스크롤하면 카드 위쪽이 뷰포트 밖으로
  밀려 아래 262pt 만 남는다 — 그 상태의 스크린샷을 픽셀 자로 재서 카드 높이로 오인했다.
  세 차례의 "기각"(aspectRatio / 자식 높이 / 카드 직접 높이)도 전부 같은 스크롤 위치에서
  같은 조각을 잰 결과라 항상 "260" 이 나온 것이다. 실제 원 결함(Image 가 카드보다 크게
  깔리던 것)은 `bff3a477` 에서 이미 고쳐졌다.

fix: >
  **레이아웃 변경 0.** `app/src/components/DefectIllustration.tsx` 의 오진 주석 정정만 수행:
  "카드가 여전히 약 360x260 이라 54%만 보인다 · 원인 미규명" → 실측 근거(AXFrame 484.67,
  onLayout 362x485, aspectRatio 실험 482.67, 에셋 9/9 720x964)와 260 의 정체(스크롤 조각)를
  박제. 임시 계측(`accessible`/debug label/onLayout 로그)은 전부 제거했다.
  `git diff` 상 변경 라인은 **주석뿐** — 렌더 경로 diff 0.

verification: >
  1. 화면 — 파워스핀 **다리** 시트: 전신(발끝→골반→발끝 붉은 직선 전체 + 폴 천장~받침 + 바닥)
     한 장에 다 보임. **어깨** 시트(`ref-power-spin--shoulder.jpg`): 손·어깨 붉은 원·다리 전체 보임.
  2. 수치 — 계기 제거 후 상시 AXFrame 만으로 **362 x 484.60pt** (기대 484.68, 오차 0.08pt).
  3. 게이트 — `npm run typecheck` PASS(에러 0) / `node --test illustrationScene.test.ts` **14/14 PASS**.

files_changed:
  - app/src/components/DefectIllustration.tsx  (주석만 — 기능 diff 0)

## 남은 관찰 (이번 결함 아님 — belle 판단 사항)

**재보지 않고 산수만 한 것이라 "미검증"으로 표시한다.**
카드(485)와 시트 뷰포트(512)의 여유가 27pt 뿐이라, **일러스트 전체가 한눈에 들어오는 스크롤
구간이 좁다**. 특히 시트를 끝까지 내린 상태(읽기 흐름의 종착점)에서는 아래 절반만 보인다 —
직전 사이클이 그 화면을 보고 "잘렸다"고 판단한 것도 이 때문이다. 승인 목업은 일러스트를
**맨 끝**에 두는데(`mockups/index.html:1114`), 앱은 M-13 결정에 따라 bullets·coachConnect·
aiNoteBox 를 일러스트 **뒤**로 옮겨 두어 약 250pt 의 후행 콘텐츠가 뒤따른다. 이 배치는
기록된 결정이므로 임의로 되돌리지 않았다.
또한 **산수로만**: iPhone SE(375x667) 급에서는 뷰포트 ≈ 350 < 카드 448.5 라 전체가 한 화면에
안 들어온다. **시뮬로 확인하지 않았다.** 조치가 필요한지는 belle 판단.

## 시뮬 조작 요령 (시간 절약)

- LogBox 배너가 하단 탭을 가로챈다 — 우측 X 먼저 눌러 치울 것.
- **AX 프레임 y 가 화면(874) 밖이면 그 탭은 엉뚱한 데 간다.** 스크롤로 화면 안에 넣고 탭.
- 앱 재기동 = `launch_app` + `terminate_running: true` (Fast Refresh 후 홈으로 리셋됨).
- 재산출 doc 4건 = 파워스핀 60(카드 4) / 킵업 79(카드 2) / pdshape 100(카드 1) / 엘보 63(카드 5).
