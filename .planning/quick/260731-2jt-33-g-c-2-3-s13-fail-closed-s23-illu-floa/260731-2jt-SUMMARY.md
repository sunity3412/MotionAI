---
phase: quick-260731-2jt
plan: 01
subsystem: ui
tags: [33-g, c-2, illustration, scene-match, fail-closed, illu-float, s13, s23, s25, s26]

# Dependency graph
requires:
  - phase: 33-result-trust-recovery (33-14, A-7)
    provides: "검수 통과 일러스트 6동작 번들 + DefectIllustration silent-hidden 배선 + 입력 프레임/검수 게이트 기록(장면 토큰의 문서 근거)"
  - phase: quick-260730-py1 (§C-2 1단위)
    provides: "부위 단위 시트 뷰모델 buildRegionSheetView + regionPartKeyForRecord (부착 판정 입력)"
  - phase: quick-260730-szk (§C-2 2단위)
    provides: "부위 그룹 마커·부위 칩 (같은 부위 키 단일 출처) + 스위프 하네스 선례"
provides:
  - "illustrationScene.ts — 장면일치 판정 순수 모듈 (ILLUSTRATION_SCENES 장면 메타 + sceneCoversParts 부분집합 규칙 + illustrationMotionForPart / hasIllustrationFor)"
  - "시트 일러스트 fail-closed 배선 — 항목 부위와 그림 장면이 어긋나면 슬롯 자체가 없음 (S13/S25)"
  - "VideoCompare.renderCueIllustration — 음성 중 우상단 illu-float 자리 (S23), 매핑은 caller"
  - "등재 10동작 × 부위 키 130조합 스위프 산출 (sweep_illustration_scene.json)"
  - "S26 빈 배경 프레임 재현 판정 — 에셋 구도 귀결(②), 렌더 경로 결함 아님"
affects: [33-G-MOCKUP-DIFF, quick-260731-이후 §C-2 잔여(S12·F-4~F-7), §C-4]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "장면일치 = 항목 부위 토큰 ⊆ 에셋 장면 토큰 (부분 겹침 = 불일치)"
    - "규칙(순수 모듈) ↔ 에셋 require 맵(컴포넌트) 분리 + 두 표 키 목록 diff 게이트"
    - "옵셔널 render prop 슬롯 — 자리는 컴포넌트, 매핑은 caller (33-14 illustrationSlot 계승)"

key-files:
  created:
    - app/src/lib/illustrationScene.ts
    - app/src/lib/__tests__/illustrationScene.test.ts
    - .planning/quick/260731-2jt-33-g-c-2-3-s13-fail-closed-s23-illu-floa/sweep_illustration_scene.test.ts
    - .planning/quick/260731-2jt-33-g-c-2-3-s13-fail-closed-s23-illu-floa/sweep_illustration_scene.json
  modified:
    - app/src/components/DefectIllustration.tsx
    - app/src/components/VideoCompare.tsx
    - app/src/components/KeypointOverlay.tsx
    - app/src/app/analysis/result.tsx

key-decisions:
  - "장면 토큰은 33-14 기록 + 에셋 6장 실물 열람에서만 부여 — 관찰 결과 6/6 전부 다리 장면(leg). 어깨·팔 항목은 전 동작 미부착"
  - "부착 건수 감소(동작당 전 항목 → leg 항목만)는 결함이 아니라 이 수리의 목적 (D-43)"
  - "P-3 공집합 게이트를 규칙 안에 둠 — vacuous 부분집합이 fail-closed 를 정반대로 뒤집는다"
  - "S26 = 에셋 구도 귀결(②). 렌더 경로는 3:4 정합(크롭 0.417%), 에셋의 82~89%가 빈 스튜디오 배경"
  - "illu-float 은 시트와 같은 판정을 통과할 때만, 콘텐츠 null 이면 흰 카드 프레임 자체 미렌더 (P-9)"

# Metrics
duration: 약 75분 (2026-07-30 16:15~17:30 UTC)
completed: 2026-07-31
---

# quick-260731-2jt: 33-G §C-2 앱 3단위 (S13 fail-closed · S23 illu-float) Summary

**항목 부위와 그림 장면이 일치할 때만 일러스트를 부착하는 순수 판정 모듈을 세우고 시트·음성 중 두 표면에 같은 규칙으로 배선 — 등재 6에셋 실물 열람 결과 전부 다리 장면이라 어깨·팔 항목에는 전 동작에서 아무것도 붙지 않는다 (10동작 130조합 스위프: 부착 6 / 미부착 124).**

---

## 1. 무엇을 했나

| 단위 | 산출 | 커밋 |
|---|---|---|
| Task 1 | `illustrationScene.ts` 장면 메타 + 부분집합 매칭 규칙 · 단위 테스트 11 · 10동작 스위프 | `98a52a3` |
| Task 2 | 시트 배선(fail-closed) + S26 재현 판정 | `bb82f07` |
| Task 3 | S23 illu-float 자리·배선 + P-12 토큰 정리 | `f83480f` |

---

## 2. 장면 토큰을 어떻게 정했나 (P-4 — 이 단위의 핵심)

### 2-1. 절차 (건너뛴 단계 없음)

1. `33-14-SUMMARY.md`「입력 프레임 선정 기록」10행 + 「검수 게이트 4종 전수 판정 표」의 PASS 행 세부·정직 노트를 읽었다.
2. **`app/assets/illustrations/*.jpg` 6장을 Read 로 직접 열었다** (D-40/D-19 — 문서만 보고 정하지 않는다). 확인 축 = 가이드 표시(곧은 선 / 부위 원)가 **어느 부위 위에** 얹혀 있는가.
3. 육안 판독을 **기계적으로 교차 검증**했다 — 코럴/브랜드 붉은 픽셀 마스크(`r>170 ∧ r−g>55 ∧ r−b>55`)의 bounding box 를 뽑아, 내가 못 본 작은 표시가 팔·어깨에 있는지 확인했다.

### 2-2. 실물 열람 결과 (전건)

| 에셋 | 붉은 가이드 표시 | 붉은 픽셀 bbox | 부여 토큰 |
|---|---|---|---|
| ref-power-spin | 직선 1줄이 위 다리 발끝→골반→아래 다리 발끝 관통 | x240-430 y80-791 | `leg` |
| ref-kip-up | 좌·우 다리에 각각 직선(골반→무릎→발목) | x84-629 **y566-848** (팔은 y60-300 → 표시 0) | `leg` |
| ref-climb | 원 1개가 앞무릎 중심(뒷무릎 일부) | x370-523 **y421-587** (그립 팔 y130-400 → 표시 0) | `leg` |
| ref-invert | 좌·우 다리에 각각 직선 | x56-659 y270-402 | `leg` |
| ref-foxtop | 직선 1줄이 위(수직) 다리 골반→발끝 | x236-328 y102-421 | `leg` |
| ref-foxtop-split | 굵은 직선 1줄이 수평 신전 다리 골반→발끝 | x49-409 y323-404 | `leg` |

**6/6 전부 `leg` 단독.** 이것은 목표가 아니라 관측이다. 팔·어깨 쪽 33-14 정직 노트는 전부 UNVERIFIED 축이라 토큰 근거가 되지 않는다:
- kip-up — "그립 팔 **좌우 반전**(회전 좌우 라벨 UNVERIFIED)"
- climb — "아래 그립 팔이 실측 신전 대신 **굽은 스태거 그립**"

즉 문서 근거도 실물도 팔·어깨 토큰을 지지하지 않는다. **확신이 안 서면 빼는 쪽이 정답**(P-4)이라 뺐다.

### 2-3. 귀결 — 부착 건수가 준다

종전: 동작 1장 → 그 동작의 **모든 항목**에 부착 (어깨 항목에 다리 그림 = belle #8·#9·#11).
현재: `leg` 부위 항목에만 부착. **어깨·팔·복합(`shoulder+arm`)·투영 공집합 항목은 전 동작에서 미부착.**

이 감소는 결함이 아니라 목적이다(D-43). 어깨·팔용 일러스트 **신규 생성**은 생성·검수 라운드가 필요해 수리 사이클 밖이며, 억지 매칭으로 건수를 지키는 것이 곧 belle 반려의 재생산이다.

---

## 3. 일반화 스위프 (blocking 축)

`sweep_illustration_scene.json` — `backend/judging_data/criteria/*.yaml` **glob 파생** 10동작 × 부위 키.

| 지표 | 수치 |
|---|---|
| 동작 | 10 (하드코딩 목록 0건) |
| 부위 키 조합 | 파생(합성 record 가 실제로 낸 키) + 프로브(부위 사전 치역의 전 비공집합 조합 7) |
| 판정 셀 | **130** |
| 부착 / 미부착 | **6 / 124** |
| 에셋 보유 / 미보유 동작 | 6 / 4 |
| `criterion:*` 부착 | **0** (P-3) |
| `motionId` 부재(mode3) 부착 | **0** |
| 동작명 조건 분기 | **0** (판정 모듈 + 스위프 소스 grep, 주석 제외) |

불변식 6종 전건 통과. 특히:
- **INV-4** — 부착 여부가 "항목 토큰 ⊆ 장면 토큰"과 **양방향으로** 일치(반례 0). 덮이는데 안 붙는 false-negative 도 0.
- **INV-3** — 에셋 미보유 집합이 33-14 미완 4동작(peter-pan · elbow-twist-sister · pdshape · sideway-spin)과 **정확히 일치**. 검수 게이트를 건너뛴 유입·이탈이 생기면 즉시 FAIL.
- **INV-6** — 부착 하한 6 ≥ 1. 배선이 죽은 코드가 아니다.

---

## 4. S26 — "빈 배경 프레임" 재현 판정 (P-11)

### 판정: **② 에셋 구도 귀결 → §C-4/deferred 이관.** 렌더 경로 결함 아님. 억지 수정 0.

근거 3축:

**(a) 렌더 경로는 승인본 M-6 정합.** 에셋 6장 전부 720×964(ar 0.746888). 컨테이너 `aspectRatio: 3/4`(0.750000) 대비 `cover` 세로 잘림 = **0.417%**(상하 각 0.208%). 무시할 수준임을 수치로 확정.

**(b) 에셋 구도 — 프레임의 82~89%가 빈 배경이다.**

| 에셋 | 비배경(인물+가이드) 픽셀 | 인물 bbox 폭 / 높이 |
|---|---|---|
| ref-climb | 17.6% | 45.6% / 88.4% |
| ref-foxtop-split | 12.6% | 78.6% / 87.9% |
| ref-foxtop | **11.1%** | 50.1% / 89.6% |
| ref-invert | 11.3% | 96.0% / 89.7% |
| ref-kip-up | 14.8% | 82.4% / 88.1% |
| ref-power-spin | 17.4% | 100.0% / 92.0% |

(배경 = 밝고 저채도 스튜디오 오프화이트, `min>225 ∧ max−min<22`)

가는 연필선 인물이 넓은 오프화이트 스튜디오 안에 놓인 구도다. 이 그림이 **어긋난 항목**(어깨 시트) 아래 앉으면 "빈 배경 프레임 — 이 일러스트는 뭘까"(belle #11)로 읽히는 것이 자연스럽다. **즉 #11 의 1차 원인은 S13 불일치이고, 2차 요인이 에셋 구도다.** S13 수리로 1차 원인은 이번에 닫혔다.

**(c) 다른 소비 표면 없음.** `grep -rn "DefectIllustration\|assets/illustrations" app/src` 전수 = `DefectIllustration.tsx` · `result.tsx` · `DeductionDetailSheet.illustrationSlot`(슬롯만). 시트가 유일 소비처였고, 이번에 illu-float 이 **같은 컴포넌트**로 두 번째 표면이 되어 3:4 규칙을 그대로 승계한다.

**빈 프레임 구조 점검(추가 확인).** `DeductionDetailSheet:327` 은 `{illustrationSlot ?? null}` 로 **래퍼 View 없이** 렌더한다 → 컴포넌트가 null 을 돌려주면 빈 박스가 남지 않는다. 시트 쪽 "빈 카드·점선 박스 0" 은 구조적으로 성립.

**하지 않은 것 (P-11 준수).** `resizeMode` 를 `contain` 으로 바꾸지 않았다 — 레터박스 빈 띠를 만들어 #11 을 오히려 재생산한다. 에셋 재생성은 새 범위(D-43).

**못 본 것.** belle 화면의 실제 픽셀은 재현하지 못했다(시뮬 렌더 = 오케스트레이터 몫). 위 (a)(b)(c)는 전부 에셋·코드 실측이다.

---

## 5. S23 illu-float — 구현과 **정직 고지**

### 5-1. 구현

- 자리 = `VideoCompare` `styles.row` 안, 자막 wrap(`cueSubtitleWrap`)과 **같은 레벨**(P-6). 발동 = `voiceCueRecordId != null`.
- 기하 = 승인본 비율(P-7): width `row×104/360`, top/right inset `row×10/360`, 배경 `rgba(255,255,255,0.94)`, radius 12, padding 6, shadow `0 4px 14px rgba(0,0,0,.25)` → RN `shadowRadius 7 / elevation 4`. `pointerEvents="none"`(S20 보호).
- fail-closed(P-9): 콜백 결과를 **먼저 변수(`cueIllustration`)에 받고** null 이면 흰 카드 프레임 자체를 렌더하지 않는다.
- 캡션 없음(P-8). 목업 `.illu-float .t`("현 채택본 — 후보 선택 시 교체…")는 belle 후보-선택 안내이지 제품 카피가 아니다.
- 매핑은 caller: `recordId → records 조회 → regionPartKeyForRecord → hasIllustrationFor` 통과 시에만 노드 반환. motionId 규칙은 시트와 동일 → mode3 자동 null.

### 5-2. ⚠ 렌더 확인 없이는 PASS 주장 불가 — 선결 조건

`voiceCueRecordId` 는 `speakCue` 가 `started=true` 를 돌려줄 때만 세워진다(33-13 D-18 고아 가드). 즉 illu-float 이 화면에 나타나려면 **① 재생 구동 + ② coachAudio 준비 doc(`audioAnalysisId`) + ③ 음성 안내 토글 ON** 이 전부 성립해야 한다.

**재생 없이 이 상태를 만드는 진입점은 코드에 없다.** 디버그 진입점 신설은 새 범위라 만들지 않았다. 2단위에서 시뮬 재생이 구동되지 않아 S19·S2 가 미검증으로 남았으므로, **S23 도 재생 구동이 선결**이다. 구동 실패 시 미검증으로 남겨야 하며 PASS 주장은 금지다.

### 5-3. ⚠ 승인본 대비 크기 — 오케스트레이터가 목업과 대조해야 할 축 (P-14)

승인본 `.player` 는 **패널 1장(360pt)**, 앱의 `row` 는 **패널 2장 + gap** 이다. P-6/P-7 이 정한 대로 `row` 를 `.player` 대응으로 두면 비율이 이렇게 나온다:

| | 승인본 | 앱 (iPhone 16 Pro 402pt 기준) |
|---|---|---|
| 기준 면 | `.player` 360pt (패널 1장) | `row` 328.3pt (패널 2장 + gap 8) |
| float 폭 | 104pt = **패널의 28.9%** | 94.8pt = **패널 1장(160.1pt)의 59.2%** |
| inset | 10pt | 9.1pt |

- 왜 이렇게 뒀나: 앱은 이미 자막 wrap·"잠시 멈춤" pill 을 `row` 레벨에 두어 **`.player` ↔ `row`** 대응을 확립했다. 같은 상태에서 함께 뜨는 요소를 다른 레벨에 두면 기준이 갈린다(P-6). 플랜이 명시한 결정이라 임의 이탈하지 않았다.
- 기능적 해는 확인되지 않는다: float 은 row 우상단 = **기준(오른쪽) 패널** 위에 앉고, 강조·pulse 는 학생(왼쪽) 패널에 있어 가리지 않는다.
- **그래도 화면에서 "너무 크다"로 읽히면** 한 줄 대안이 준비돼 있다 — 부착 레벨(row)은 그대로 두고 기준 폭만 슬롯으로 바꾼다: `width = (rowWidth − 8)/2 × 104/360` (= 46.3pt, 패널의 28.9% = 승인본과 동일 비율). 이 판단은 승인 목업 실물 대조가 필요하므로 **실행자가 단독으로 바꾸지 않았다.**
- 부수 항목: `DefectIllustration` 카드 반경은 `radius.card`(15)이고 승인본 `.illu-float img` 는 8이다. 시트와 공유하는 컴포넌트라 바꾸면 이미 렌더 확인된 시트 표면이 함께 변한다 → 무접촉(P-10). 목업 대조 시 참고.

---

## 6. 검증 결과

### 자동 게이트 (전건 통과)

| 게이트 | 결과 |
|---|---|
| `illustrationScene.test.ts` | 11 pass / 0 fail (behavior 9축 + 프로토타입 키 우회 + 부위 키 단일 출처) |
| `sweep_illustration_scene.test.ts` | 2 pass / 0 fail (INV-1~6) |
| `npm run typecheck` | clean |
| 두 표 키 목록 `diff` | **0** (`ILLUSTRATION_SCENES` ↔ `VERIFIED_ILLUSTRATIONS`) |
| `DefectIllustration` `<Text` | 0 (캡션 0 — D-05) |
| `aspectRatio: 3 / 4` 생존 | 예 (M-6) |
| `KeypointOverlay` `#FFFFFF` | 11 → **0** |
| `result.tsx` 동작명 조건 분기 | 0 |
| 1·2단위 회귀 | `deductionSheet` 35 · `focusShape` 12 · `cueTrack` 7 — 전부 pass |
| 앱 lib 테스트 전건 | 112 pass / 0 fail (9 파일) |
| 1·2단위 스위프 | `sweep_sheet_blocks` 3 pass · `sweep_markers_focus` 2 pass |
| 신규 npm 의존성 | 0 (`package.json`·lock 무변경) |

### 무접촉 증명 (over-generalize-breaks-approved 방지)

- **S18(음성 상태전이)** — `git diff -U0 VideoCompare.tsx` 에서 `speakCue` / `stopCue` / `setVoiceCueRecordId` / `voiceCueRecordIdRef` / `activeCue(` 매치 **0줄**. 상태전이 로직 diff 0.
- **S20(cuedot·틱)** — 같은 diff 에서 `cuedot` / `timelineTicks` / `onTickPress` 매치 **0줄**. float 은 `pointerEvents="none"`.
- **S19/S1/S3/F-8(KeypointOverlay)** — diff 가 색 리터럴 11줄 + 주석 5줄뿐. 형태·pulse·게이트 로직 매치 0줄.
- **기존 `VideoCompare` 소비처** — `renderCueIllustration` 미전달 시 렌더 diff 0(옵셔널). 유일한 기존 줄 변경 = `<View style={styles.row}>` 에 `onLayout` 추가(레이아웃 무영향).
- **채점 무접촉(D-44)** — 백엔드·`backend/` 파일 변경 0. 점수 산출 경로 무접촉.
- **배포 없음(D-45)** — OTA/EAS 실행 0.

### 내가 직접 열어본 것 (D-19/D-40)

- 일러스트 에셋 **6장 전부** Read 열람 + 붉은 픽셀 bbox·배경 비중 실측.
- 승인 목업 `mockups/index.html` 표적 정독: `:204-218`(illust-slot·illu-float CSS) · `:512-545`(illu-float 실물 배치 + `.t` 문구) · `:1040-1120`(`DETAILS` 3시트 illust 값 + `renderDetail` 슬롯 조건).
- `criteria/*.yaml`(ref-climb·ref-power-spin) 실물 — 스위프의 `yamlJoints 0` 이 파싱 실패가 아니라 **의도된 빈 criteria**(IPSF Climbs 카테고리)임을 확인.
- 스위프 산출 JSON 값 직접 확인(130 셀 / 부착 6 / 미부착 124).

### 내가 못 본 것 (정직 고지)

- **시뮬레이터 렌더 전건.** 실행자 도구에 시뮬레이터가 없다. 아래 §7 이 오케스트레이터 몫.
- **belle 화면의 실제 "빈 배경 프레임" 픽셀.** §4 는 에셋·코드 실측이지 그 화면의 재현이 아니다.
- **illu-float 실렌더.** §5-2 선결 조건(재생 구동)이 실행자 환경에서 성립하지 않는다.

---

## 7. 시뮬 확인 요청 (오케스트레이터)

> 실행자는 33-G 표를 **갱신하지 않았다**. 아래는 재채점 제안이며, 판정은 렌더 대조 후 오케스트레이터가 확정한다.

| # | 항목 | 도달 경로 | 무엇을 보면 PASS | 선결 조건 |
|---|---|---|---|---|
| V-1 | **S13/S25 — 어깨 항목에 다리 그림 0** | 결과 화면 → 부위 칩 `어깨`(또는 어깨 감점 행) 탭 → 시트 최하단까지 스크롤 | 일러스트 **자리 자체가 없음**. 빈 카드·점선 박스·"준비 중" 문구 **0**. facing 다음에 바로 다음 섹션(용어줄) | mode1 doc + 어깨 감점 record |
| V-2 | **S13 — 다리 항목에는 종전대로 보임** | 같은 doc → 부위 칩 `다리` 탭 → 시트 최하단 | 일러스트가 **보인다**(일괄 제거가 아님). 위치·순서 = facing 다음 최하단(P-10 무회귀) | 등재 6동작(power-spin·kip-up·climb·invert·foxtop·foxtop-split) 중 하나 |
| V-3 | **S26 — 3:4 원본 비율** | V-2 시트 | 그림이 세로로 늘어나거나 좌우 잘리지 않음. 위아래 빈 띠(레터박스) 0 | V-2 와 동일 |
| V-4 | **회귀 — mode3 / 에셋 미보유 4동작** | mode3 doc 또는 pdshape·peter-pan·elbow-twist-sister·sideway-spin doc → 아무 부위 시트 | 일러스트 없음(종전과 동일), 에러 표면 0 | — |
| V-5 | **S23 — illu-float 등장/소멸** | 동작 비교 카드 → **음성 안내 토글 ON** → 재생 | 음성이 읽는 동안 row **우상단**에 흰 카드 + 그림, 자막·"음성 중 — 잠시 멈춤"·dim 과 **동시**. 음성이 끝나면 사라짐 | ⚠ **재생 구동 + coachAudio 준비 doc + 토글 ON 3개 전부** (§5-2). 하나라도 불성립 시 **미검증으로 남길 것 — PASS 주장 금지** |
| V-6 | **S23 fail-closed — 흰 카드조차 없음** | V-5 상태에서 **어깨 항목** 음성 큐 순간 | 어깨 큐 동안에는 우상단에 **아무것도 없다**(빈 흰 카드도 없음) | V-5 와 동일 |
| V-7 | **P-14 크기 대조 (판단 요청)** | V-5 화면 캡처 ↔ 승인 목업 `.illu-float` 컷 | float 이 기준 패널 우상단을 과도하게 덮지 않는가 (앱 59.2% vs 승인본 28.9% — §5-3) | V-5 와 동일. "크다" 판정 시 대안 1줄 = §5-3 |
| V-8 | **S18/S20 무회귀** | V-5 재생 중 | 정지·dim·"잠시 멈춤" 그대로, 재생바 ①②③ 틱 탭 정상(float 이 탭을 가리지 않음) | V-5 와 동일 |
| V-9 | **F-8/S1/S3 무회귀** (P-12 토큰 교체분) | 결과 화면 → 스켈레톤 토글 ON/OFF | 흰 스켈레톤 점·선, 번호 배지 흰 글자, 흰 halo 가 **종전과 동일**(값 동일 교체라 불변이어야) | — |
| V-10 | **새 RN 경고 0** | Metro stdout | `expo-video allowsFullscreen` deprecation **2건 외 신규 경고 0**(특히 shadow/elevation 계열) | Metro stdout 캡처 |

### 재채점 제안 (33-G 표 — 오케스트레이터가 확정)

| 행 | 현재 | 제안 | 조건 |
|---|---|---|---|
| **S13** | FAIL | **PASS** | V-1 + V-2 + V-4 전건 |
| **S25** | FAIL (S13 흡수) | **PASS** | S13 과 동일 |
| **S23** | FAIL | **미검증** 또는 PASS | V-5·V-6 성립 시 PASS. 재생 미구동이면 **미검증 유지**(코드는 들어갔으나 화면으로 못 봤으므로) |
| **S26** | PARTIAL (재현 확인) | **PARTIAL → 판정 기록 완료 / 잔여 = §C-4 이관** | 렌더 경로 정합은 실측 확정(§4). 에셋 구도 개선(재생성)은 D-43 로 범위 밖 |

---

## 8. 자체 도출 결정 적용 결과 (P-1~P-12) + 신규 (P-13~P-14)

| # | 적용 | 근거·비고 |
|---|---|---|
| **P-1** | 적용 | 판정 입력 = `regionPartKeyForRecord` 키. 시트·illu-float 양쪽 같은 함수 소비. 단위 테스트 10 이 "실제로 그 함수가 내는 키"를 그대로 먹는지 고정 |
| **P-2** | 적용 | `sceneCoversParts` = 전부 포함. 부분 겹침 불일치를 합성 토큰 테스트로 고정(등재 6장이 전부 같은 계열이라 실맵으로는 그 분기를 못 밟음 → P-13) |
| **P-3** | 적용 | 공집합·`criterion:` 게이트를 **규칙 안**에 뒀다(밖에 두면 새 소비처가 건너뛴다). 단위 테스트 4 + 스위프 INV-5 로 이중 고정 |
| **P-4** | 적용 | §2. 6장 실물 열람 + 붉은 픽셀 bbox 교차 검증. `provenance` 필수 + "실물 열람" 문자열을 테스트가 강제 |
| **P-5** | 적용 | 규칙 = `lib/illustrationScene.ts` / 에셋 맵 = `DefectIllustration.tsx`. 두 표 키 목록 `diff` 게이트 0 |
| **P-6** | 적용 | illu-float = `styles.row` 안 자막 wrap 과 같은 레벨. ⚠ 크기 귀결은 P-14 |
| **P-7** | 적용 | row 폭 비율. `onLayout` 으로 row 폭 실측 — 퍼센트 스타일은 `top` 이 부모 **높이** 기준이라 축이 어긋난다(이 사유를 코드 주석에 박제) |
| **P-8** | 적용 | `.illu-float .t` 미이식. 캡션 `<Text>` 0 |
| **P-9** | 적용 | 콜백 결과를 먼저 변수에 받고 null 이면 프레임 미렌더. 시트·float 같은 판정 |
| **P-10** | 적용 | 시트 슬롯 위치·순서 diff 0. `DefectIllustration` 반경·3:4·`resizeMode` 무변경 |
| **P-11** | 적용 | §4. `contain` 전환 등 억지 수정 0. 판정 = ② |
| **P-12** | 적용 | `#FFFFFF` 11 → 0. `rgba(0,0,0,0.6)`(저신뢰 원 외곽)은 대응 토큰 없어 유지 — **잔여**. `rgba(255,255,255,…)` 는 이 파일에 애초에 0건이었다(흰 halo 는 `#FFFFFF` + `strokeOpacity` 형태였고 전부 토큰화됨) |
| **P-13** (신규) | — | **`sceneCoversParts` 를 export 한다.** 등재 6장이 전부 다리 계열이라 실맵만으로는 P-2 의 "부분 겹침 → 불일치" 분기를 밟을 수 없다. 규칙을 합성 토큰으로 고정할 테스트 seam 이 필요하다. 공집합 게이트를 이 함수 **안**에 둬서 외부 호출자도 fail-closed 를 우회하지 못한다 |
| **P-14** (신규) | — | **illu-float 크기 = 승인본 비율의 2배(패널 대비)라는 사실을 기록하고 판단은 목업 대조로 넘긴다.** 원인 = 승인본 `.player`(패널 1장) ↔ 앱 `row`(패널 2장) 대응(P-6). 실행자 단독 변경 금지 — 승인 자산 실물 대조가 필요한 시각 판단이고, 대안 1줄은 §5-3 에 준비. 기능적 해(강조 가림)는 확인되지 않음 |

---

## 9. Deviations from Plan

**1. [Rule 2 — fail-closed 보강] 프로토타입 키 우회 차단**
- **Found during:** Task 1
- **Issue:** `ILLUSTRATION_SCENES[motionId]` 를 그대로 인덱싱하면 `motionId='__proto__'`·`'constructor'` 가 truthy 객체를 돌려줘 조회 게이트를 통과한다.
- **Fix:** `Object.prototype.hasOwnProperty.call(...)` 선행 게이트 + 단위 테스트 5 가 3개 키를 고정.
- **Commit:** `98a52a3`

**2. [Rule 2 — fail-closed 보강] 유효 범위 밖 부위 토큰도 미부착**
- **Found during:** Task 1
- **Issue:** 오타 토큰(`legs`·`LEG`)이 항목/장면 양쪽에 같은 문자로 들어가면 부분집합 판정이 참이 되어 사전에 없는 부위에도 그림이 붙는다.
- **Fix:** `sceneCoversParts` 가 `BODY_PART_OF_KEYPOINT` 치역 소속을 함께 검사. 단위 테스트 3b·9.
- **Commit:** `98a52a3`

**3. [판단 — 플랜 명세 준수] illu-float 크기 이슈를 코드로 고치지 않음**
- **Issue:** P-7 대로 구현하면 패널 대비 승인본의 2배가 된다(§5-3).
- **판단:** P-6/P-7 은 플랜의 명시 결정이고, 크기 적정성은 **승인 자산 실물 대조가 필요한 시각 판단**이다. 실행자가 임의로 바꾸면 그 자체가 "코드 기준 검증"이 된다. → 수치·대안과 함께 P-14 로 기록하고 V-7 로 넘겼다. 좁게 덮지 않고 사실을 드러내는 쪽을 택했다.

**4. [스코프 밖 관찰 — 미수정]**
- `KeypointOverlay.tsx` `rgba(0,0,0,0.6)` (저신뢰 원 외곽) — 대응 알파 토큰 없음. 신설은 새 범위(P-12 명시)라 유지.
- `VideoCompare.tsx:1889` `backgroundColor: '#F4F4F4'` (빈 슬롯 배경) — 기존 항목, 이 단위 범위 밖.
- `DefectIllustration` 카드 반경 `radius.card`(15) vs 승인본 `.illu-float img` 8 — 시트와 공유 컴포넌트라 무접촉(P-10).

---

## 10. Known Stubs

없음. 어깨·팔 항목의 일러스트 부재는 stub 이 아니라 **의도된 fail-closed**다 — 그 부위를 가리키는 검수 통과 에셋이 존재하지 않으며(§2-2 실측), 없는 그림을 붙이는 것이 belle 반려의 원인이었다. 어깨·팔 세트 생성은 D-43 로 이 사이클 밖(§C-4 이후 별 플랜 후보).

## 11. Threat Flags

없음 — 신규 네트워크 표면·인증 경로·스키마 변경 0. 신규 npm 의존성 0.

플랜 threat register 대응:
- **T-33G4-01**(거짓 근거 표시) — `provenance` 필수 + "실물 열람" 문자열 강제 + 스위프 INV-3 이 33-14 검수 집합과의 정확 일치를 고정.
- **T-33G4-02**(fail-closed 우회) — 공집합 게이트를 규칙 안에 + 단위 테스트 4 + 스위프 INV-5(부착 0).
- **T-33G4-03**(두 표 drift) — `diff` 키 목록 게이트 0.
- **T-33G4-04**(승인 표면 파괴) — S18/S20/KeypointOverlay 로직 diff 0 실증 + 1·2단위 테스트 회귀 0.
- **T-33G4-05**(빈 카드 노출) — 콜백 결과 선-수신 배선(P-9) + 시트 쪽 래퍼 없는 `{illustrationSlot ?? null}` 구조 확인.

## 12. Task Commits

1. **Task 1: 장면일치 판정 순수 모듈 + 10동작 스위프** — `98a52a3` (feat)
2. **Task 2: S13/S25 시트 배선 + S26 재현 판정** — `bb82f07` (feat)
3. **Task 3: S23 illu-float + P-12 토큰 정리** — `f83480f` (feat)

## 13. 다음 단위로 넘기는 것

- **§C-2 잔여**: S12 어휘 잔재 3곳 — 이번 단위에서 **현재 줄번호를 재확인**했다(33-G 표의 `:424` 는 그 사이 파일 이동으로 stale):
  - `deductionLabels.ts:479` `leg_extension: '다리 신전(펴짐)'`
  - `DimensionDetailModal.tsx:94` "완성도 기준으로" (같은 파일 `:141` `:147` 에도 "완성도" 2건 추가 발견 — 33-G 표 미기재분)
  - `loading.tsx:68,72` 팁 "라인의 완성도" / "완성도의 차이"
  그 외 F-4(100점 헤드라인) · F-5(슬라이더 기호) · F-6(실기기 음성 무음, 원인 미상) · F-7(자세히 보기 스크롤).
- **S23 렌더 판정** — 재생 구동이 선결. 시뮬 재생이 계속 불가하면 §C-4 재산출 doc + 실기기 확인으로 이월(2단위 S19·S2 와 같은 처지).
- **어깨·팔 일러스트 세트** — D-43 deferred. 생성 시 33-14 검수 게이트 4종 재수행 + `ILLUSTRATION_SCENES` 등재(실물 열람 provenance 필수) + 스위프 INV-3 갱신이 한 묶음.
- **P-14 크기 판단** — V-7 결과에 따라 한 줄 수정(§5-3).

## Self-Check: PASSED

- 생성 파일 4건 존재 확인 (`illustrationScene.ts`, `illustrationScene.test.ts`, `sweep_illustration_scene.test.ts`, `sweep_illustration_scene.json`)
- 커밋 3건 존재 확인 (`98a52a3`, `bb82f07`, `f83480f`)
- 자동 게이트 전건 재실행 통과 (typecheck · 단위 11 · 스위프 2 · 회귀 112 · diff/grep 게이트)

---
*Quick task: 260731-2jt*
*Completed: 2026-07-31*
