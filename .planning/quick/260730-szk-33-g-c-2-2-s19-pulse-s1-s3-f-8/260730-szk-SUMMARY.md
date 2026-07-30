---
phase: quick-260730-szk
plan: 01
subsystem: app-result-overlay
tags: [33-G, S19, S1, S2, S3, F-8, keypoint-overlay, part-chips, approved-mockup-7R]
requires:
  - "deductionSheet.regionPartKeyForRecord (quick-260730-py1 — 부위 키 단일 출처)"
  - "buildDeductionMarkers.recordNumbers (전역 마커 번호 단일 출처)"
  - "projectDeductionRecordKeypoints (record → keypoint 투영 규칙 1벌)"
  - "KeypointOverlay.KEYPOINT_LOW_CONFIDENCE_THRESHOLD (0.5 — 신규 임계 신설 금지)"
provides:
  - "lib/focusShape.ts — 음성 큐 강조 선/원 분기 순수 로직 + PULSE_PERIOD_MS 단일 선언"
  - "deductionSheet.buildPartGroups — 부위 단위 그룹 마커(번호 병합 배지)"
  - "deductionSheet.buildPartChips + partLabelKo — 승인 목업 ① 부위 칩"
  - "deductionSheet.ADVISORY_NOTE_KO / ADVISORY_CHIP_KO — 참고 문형 전 표면 단일 소스"
  - "components/PartChipsRow.tsx — 상시 진입점(F-8 대체 surface)"
  - "KeypointOverlay.markersVisible — 상시 마커 게이트 (D-42)"
affects:
  - "app/src/app/analysis/result.tsx (부위 그룹·칩 배선 + F-8 게이트)"
  - "app/src/components/KeypointOverlay.tsx (강조 형태·pulse·그룹 경계·마커 가시성)"
  - "app/src/components/DeductionDetailSheet.tsx (참고 문형 local 사본 제거)"
tech-stack:
  added: []
  patterns:
    - "기하 분기 규칙을 순수 모듈로 격리 — 오버레이는 좌표 환산·드로잉만 (규칙 사본 0)"
    - "체인 사전을 측별 사지로만 정의해 몸통 가로지르기를 자료구조로 금지 (조건문 아님)"
    - "pulse = 별 Animated.View opacity + useNativeDriver:true (SVG prop 애니메이션 회피)"
    - "부위 키 산출 함수 쪽으로 그룹 빌더를 옮겨 순환 import 회피 (사본 0벌 유지)"
    - "criteria yaml glob 파생 스위프로 등재 10동작 일반화 확인"
key-files:
  created:
    - app/src/lib/focusShape.ts
    - app/src/lib/__tests__/focusShape.test.ts
    - app/src/components/PartChipsRow.tsx
    - .planning/quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/sweep_markers_focus.test.ts
    - .planning/quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/sweep_markers_focus.json
  modified:
    - app/src/components/KeypointOverlay.tsx
    - app/src/lib/deductionSheet.ts
    - app/src/lib/__tests__/deductionSheet.test.ts
    - app/src/app/analysis/result.tsx
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/lib/deductionLabels.ts
decisions:
  - "buildPartGroups 는 deductionSheet 소유 — deductionLabels 에 두면 순환 import (N-16)"
  - "advisory 그룹 경계는 오버레이 능력만 — 승인본 ① 참고 표시는 개별 점선 마커 (N-18)"
  - "복합 부위(shoulder+arm) ↔ 토큰 부위(shoulder) 경계 중첩은 1단위 부위 모델의 귀결 — 시각 판정 위임 (N-19)"
  - "참고 칩 점선은 RN iOS borderRadius>0 한계로 실선 렌더 가능 — 구분은 라벨 접두+색 (N-20)"
  - "reduce-motion 분기는 범위 밖, deferred (N-9)"
metrics:
  duration: "약 2시간 30분"
  completed: 2026-07-30
  tasks: 3
  commits: 8
  files: 11
---

# quick-260730-szk: 33-G §C-2 앱 수리 2단위 (S19 강조 선/원+pulse · S1~S3 그룹 마커·부위 칩 · F-8) Summary

승인 목업 7R 의 **영상 위 표시 계층**을 데이터로 재현했다 — 음성 큐 강조를 `bounds circle` 하나에서
kp 게이트 기반 **사지 모양 선 / 부위 원** 분기 + **1.4초 pulse** 로 갈랐고, 감점 마커를 **부위 단위
그룹 경계 1개**로 통일하면서 멤버 관절의 개별 빨강 원 나열을 없앴고, 승인본에만 있던 **부위 칩 행**을
신설해 F-8(상시 마커 제거)로 사라지는 상시 진입점을 대체했다.
**백엔드 변경 0 · 채점 무접촉(점수 산출 파일 diff 0) · 신규 패키지 0 · OTA 미발행.**

## 커밋

| # | 해시 | 내용 |
|---|---|---|
| 1 | `c070f8c` | test(szk-01) 강조 선/원 분기 실패 테스트 (승인본 7R 컷 2 재현 축) |
| 2 | `cdeeba9` | feat(szk-01) `focusShape.ts` — 체인 사전·최장 고신뢰 런·근위 inset·PULSE_PERIOD_MS |
| 3 | `d04b54f` | test(szk-01) 부위 그룹·부위 칩·참고 문형 실패 테스트 |
| 4 | `f2c5e20` | feat(szk-01) `buildPartGroups`/`buildPartChips`/`partLabelKo` + 참고 문형 단일 소스 |
| 5 | `361aefa` | feat(szk-02) 오버레이 — 선/원 렌더·pulse·점선 그룹·병합 배지·`markersVisible` |
| 6 | `41cb6bf` | test(szk-03) 등재 10동작 일반화 스위프 + 산출 JSON |
| 7 | `ea6bc6c` | feat(szk-03) `PartChipsRow` 신설 + result.tsx 배선 + F-8 게이트 |
| 8 | `df9d193` | docs(szk-03) 참고 칩 점선 iOS 플랫폼 한계 정직 기록 (N-20) |

## 변경 요지 (파일별)

| 파일 | 변경 |
|---|---|
| `app/src/lib/focusShape.ts` (신규 199줄) | `LIMB_CHAINS` 측별 사지 4개(좌우 혼합 체인 정의 자체가 없음) · `PROXIMAL_INSET_T` `{hip: 0.65, shoulder: 0}` · `PULSE_PERIOD_MS = 1400` · `buildFocusShapes` (focus 포함 최장 연속 고신뢰 런 ≥2 → 선 / <2 → 부위 원 강등 / 고신뢰 0 → 빈 결과). 좌표 미수신 — 환산은 오버레이 책임 |
| `app/src/lib/deductionSheet.ts` | `buildPartGroups`(부위 1경계 + 번호 오름차순 병합 배지 + 번호 0·투영 0 부위 제외) · `buildPartChips`(감점 칩 + 참고 칩, records 0/estimatedArea → `[]`) · `titleForPartKey` → `partLabelKo` export 승격 · `ADVISORY_ONE_CAP` → `ADVISORY_NOTE_KO` export(값 변경 0) · `ADVISORY_CHIP_KO` 신설 |
| `app/src/lib/deductionLabels.ts` | **주석 11줄만 추가**(N-16 근거). `buildDeductionMarkers` 3필드 산출 로직 diff 0 |
| `app/src/components/KeypointOverlay.tsx` | `buildFocusShapes` 소비 → halo+brand `Polyline`(근위 inset) / 타원 · dim `Rect` 정적 잔존 · 강조만 별 `Animated.View` opacity pulse(`useNativeDriver: true`, 의존성 boolean 1개, cleanup `loop.stop()`+`setValue(1)`) · `groupMarkers` 에 `badgeLabel`/`advisory` 확장 · 그룹 흡수 관절 개별 강조·번호·탭 억제 · `markersVisible`(default `true`) |
| `app/src/components/PartChipsRow.tsx` (신규 134줄) | 승인 `.jointchips` 렌더. 감점 칩 → `onPressPart`, 참고 칩 → 인라인 안내 토글. 테마 토큰만(hex 리터럴 0), 새 문장 0, 이모지 0 |
| `app/src/app/analysis/result.tsx` | `partGroups`/`partChips` memo(입력 전부 기존 판정 재사용) · breakdown 보유 doc 의 `overlayGroupMarkers` = 부위 그룹 / `overlayMarkerNumbers` = `{}` · `markersVisible={overlayVisible \|\| opts?.voiceCueRecordId != null}` · "상시 렌더" 주석 → D-42 근거로 교체 · 칩 행을 `VideoCompare` 직후에 배치 |
| `app/src/components/DeductionDetailSheet.tsx` | local `CHIP_ADVISORY` 제거 → `ADVISORY_CHIP_KO` import |

## 자체 도출 결정 적용 결과 (N-1~N-15)

| # | 적용 | 근거/실측 |
|---|---|---|
| N-1 | 적용 — 마커 그룹 단위 = 부위(`regionPartKeyForRecord`) | 스위프: 그룹 수 == 감점 칩 수 == 부위 시트(투영 보유분) 수, 10/10 동작 |
| N-2 | 적용 — 병합 배지 `2·3`, 1건이면 단일 숫자 | 단위 Test 15/15b + 스위프 병합 배지 30건(동작당 3) |
| N-3 | 적용 — 병합 탭 대상 = 최소 번호 record | `buildPartChips.firstRecordIndex`, 오버레이 그룹 `number = numbers[0]` |
| N-4 | 적용 — 그룹 흡수 관절 개별 원·번호 미렌더 | `groupedKeypoints` 억제 + `overlayMarkerNumbers = {}` |
| N-5 | 적용 — 참고 마커 색 `advisoryOrange` 유지 (승인본 회색 미채택) | S2 판정축 = 형태(실선/점선). 색 변경 시 quick-260704-fz4 3표면 어긋남 |
| N-6 | 적용 — 참고 칩 = 인라인 안내 1줄(`ADVISORY_NOTE_KO`), advisory 상세 시트 이관 | advisory 는 record 부재 → 시트 뷰모델 입력 불성립 |
| N-7 | 적용 — 별 `Animated.View` + View opacity, native driver | grep 게이트: `useNativeDriver: false` 0건 |
| N-8 | 적용 — dim 은 정적(`Rect` 가 기존 `<Svg>` 에 잔존) | pulse 레이어에 dim 미포함 (S18 표현 보호) |
| N-9 | 미적용(기록) — reduce-motion 분기 | 범위 밖, 이관 |
| N-10 | 적용 — inset 관절 역할 키잉 `hip 0.65 / shoulder 0` | 0.65 = 승인본 실좌표 검산(161.3+0.65×(187.2−161.3)=178.1 / 334.7+0.65×(374.4−334.7)=360.5 = 승인 polyline 시작점). shoulder 값은 **만들지 않았다** |
| N-11 | 적용 — 선 = focus 포함 최장 연속 고신뢰 런(사지 가시 구간 전체) | 단위 테스트: 어깨 단독 focus + elbow/hand 고신뢰 → 3점 선 |
| N-12 | 적용 — 체인 사전에 좌우 혼합 없음 | 단위 테스트(사전 자체 검사) + 스위프 좌우 교차 **0** |
| N-13 | 적용 — 마커 숨김 시 번호 의미는 4진입점이 유지 | 칩·내역 행·재생바 틱·여백 범례 배선 무접촉(assert 4문자열) |
| N-14 | 적용 — cleanPass 칩 행 미렌더 | `buildPartChips(records: []) === []` + caller `length > 0` 게이트 |
| N-15 | 적용 — 마커 숨김 시 `tapTargets` 빈 배열 | `if (onMarkerPress && markersVisible)` + 그룹 흡수 관절 skip |

### 신규 도출 (N-16~N-20)

| # | 지점 | 결정 | 근거 |
|---|---|---|---|
| **N-16** | `partGroups` 를 어느 파일에 두나 (플랜이 순환 시 대안 지시) | **`deductionSheet.ts`** 에 `buildPartGroups` 를 두고 `result.tsx` 가 `buildDeductionMarkers` 와 나란히 호출. `deductionLabels.ts` 는 근거 주석만 | 실제 import 방향 확인: `deductionSheet` → `deductionLabels` 단방향. 역방향 import 는 순환. 부위 키 산출 사본 0벌 유지가 상위 제약 |
| **N-17** | 근위 inset 을 어느 좌표에 적용하나 | 오버레이가 `lerp(p0, p1, insetT)` 로 **첫 점만** 대체. `insetT` 자체는 순수 모듈이 "런이 근위 관절에서 시작할 때만" 부여 | 승인본은 knee·ankle 실좌표를 유지하고 시작점만 밀었다(`:448` "knee·ankle 실좌표 유지"). 런이 knee 부터면 이미 몸통 밖 → 0 |
| **N-18** | advisory **그룹** 경계를 만들 것인가 | 오버레이에 `advisory` 지원만 넣고 **result.tsx 는 생성하지 않는다**. 승인본 ① 의 참고 표시는 `.mk.adv`(개별 점선 마커) 1개이고 앱은 이미 그것을 그린다 | 승인본이 정답 — 참고 부위를 그룹으로 승격하면 승인본에 없는 표시가 늘고, 기존 개별 점선(S2 형태 축)을 대체해버린다. `.mkg.adv` CSS 는 존재하나 승인 컷에서 미사용 |
| **N-19** | 복합 부위(`shoulder+arm`) ↔ 토큰 부위(`shoulder`) **경계 중첩** | 이 단위에서 고치지 않는다. 스위프가 **구조적으로 설명 가능한 중첩만 발생함**을 고정(INV-3b)하고 시각 판정을 시뮬에 위임 | 근본원인 = 1단위 M-3 부위 모델(한 record 가 두 부위 토큰에 걸치면 복합 부위). 그 모델은 **이미 PASS**(시트)이고, 플랜은 그룹 `keypoints` 를 record 투영 **전부의 합집합**으로 지정(Test 15c)했다. 배타 소유로 바꾸면 "어깨·팔" 경계가 어깨를 제외해 **항목 위치를 거짓 표기**하고, 부위 모델을 바꾸면 PASS 표면을 깬다 → over-generalize-breaks-approved |
| **N-20** | 참고 칩 점선이 iOS 에서 실선으로 렌더될 수 있음 | `borderStyle: 'dashed'` 를 유지(Android 정상)하고 한계를 코드·SUMMARY 에 명기. iOS 에서 구분은 **라벨 접두 "참고: " + advisoryOrange** 가 담당 | RN 은 `borderRadius > 0` 인 View 의 dashed 를 iOS 에서 실선으로 그린다(장기 미해결). 승인본 `.ref` 는 pill+dashed. **S2 의 판정축인 영상 위 마커 점선은 SVG `strokeDasharray` 라 이 한계와 무관** |

## 검증

| 게이트 | 결과 |
|---|---|
| `focusShape.test.ts` | **12 pass / 0 fail** (신규 — RED 확인 후 GREEN) |
| `deductionSheet.test.ts` | **35 pass / 0 fail** (기존 25 무회귀 + 신규 10) |
| `visualCards.test.mjs` (1단위 산출) | **21 pass / 0 fail** |
| `sweep_markers_focus.test.ts` (등재 10동작) | **2 pass / 0 fail** (INV-1~7) |
| 앱 lib 테스트 전건 | cueTrack 7 · deductionSheet 35 · focusShape 12 · gaugeGeometry 4 · manualOffset 6 · resultSections 5 · summarySource 11 · visualCards 21 = **101 pass / 0 fail** |
| `npm run typecheck` | clean |
| 동작명 리터럴 (focusShape·deductionSheet·deductionLabels, 주석 제외) | **0건** |
| `PULSE_PERIOD_MS = 1400` 선언 수 | **1** (오버레이는 import — 1.4s 사본 0) |
| `DeductionDetailSheet` 참고 문형 사본 | **0건** (lib 상수 import) |
| `useNativeDriver: false` | **0건** / `Animated.loop` + `loop.stop()` 존재 |
| `reanimated` in package.json | **0건** (신규 패키지 0) |
| `PartChipsRow.tsx` hex 색 리터럴 (주석 제외) | **0건** (테마 토큰만) |
| `result.tsx` "skeletonVisible 무관 상시 렌더" | **0건** (D-42 근거 주석으로 교체) |
| `result.tsx` 초 추정 `compareFrames.(userIdx\|refIdx) /` | **0건** (1단위 결과 무회귀) |
| S18/S20 배선 4문자열 존재 | `onLegendPress` · `onTickPress` · `cueWindows` · `audioAnalysisId` 전건 존재 |
| `KeypointOverlay` 신규 색 리터럴 | `#FFFFFF` 9 → 11 (halo 2건 증가, 승인본 흰 halo 규칙) · `#000000` 1 → 1 · 신규 색 값 **0** |
| 백엔드 diff | **0 파일** (채점 무접촉 D-44) |
| OTA/EAS | **미실행** (D-45) |

### 스위프 수치 표 (등재 10동작 일반화)

| 동작 | yaml joint | record | 부위 그룹 | 감점 칩 | 참고 칩 | 참고칩(최소) | 시트 | 병합배지 | 선(hi) | 원(hi) | 좌우교차 | 경계중첩 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ref-climb | 0 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| ref-elbow-twist-sister | 0 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| ref-foxtop-split | 6 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| ref-foxtop | 6 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| ref-invert | 6 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| ref-kip-up | 0 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| ref-pdshape | 0 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| ref-peter-pan | 0 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| ref-power-spin | 2 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| ref-sideway-spin | 6 | 13 | 4 | 4 | 0 | 1 | 6 | 3 | 14 | 0 | 0 | 2 |
| **합계** | — | **130** | **40** | **40** | **0** | **10** | **60** | **30** | **140** | **0** | **0** | **20** |

읽는 법:
- **부위 그룹 == 감점 칩 (40 == 40)** = 승인본 "화면의 표시 수 = 항목 수". 각 칩이 자기 `partKey`·`title`
  시트를 연다(전건 assert).
- **시트 60 vs 칩 40** 차이 20건 = `line` · `dimension_overall_fallback` (부위 투영 공집합).
  마커·칩을 만들 자리가 없어 제외하고 시트만 남긴다 — 의도된 차집합(assert 로 고정).
- **참고 칩 0** = 최대 시나리오에서 shoulder·arm·leg 토큰이 전부 감점에 덮여 정상 제외.
  참고 갈래는 "감점이 다리뿐" 최소 시나리오로 동작당 1건 별도 검증(`참고: 팔`).
- **좌우 교차 0** = 몸통 가로지르기 구조적 불가(N-12).
- **원(hi) 0** = 전 관절 고신뢰 시나리오라 전부 선으로 갈렸다는 뜻(정상). 원 갈래는 단위 테스트
  4축(승인본 7R 컷 2 재현: knee 0.43 · ankle 0.29)이 담당.
- **경계중첩 20** = N-19. 동작당 2건, 전건 `shoulder+arm` ↔ `shoulder` (좌·우 어깨 2관절).

### 스위프가 실제로 잡은 것 (코드 통과 ≠ 완료)

첫 실행에서 **FAIL** 이 나왔다: `ref-climb keypoint left_shoulder 가 두 그룹에 속한다
(shoulder / shoulder+arm)`. 그대로 넘기지 않고 데이터로 근본원인을 특정했다 —
`arm_extension` 의 투영이 `REGION_MEMBER_KEYPOINTS.arms`(어깨 2 + 손 2)라 부위 토큰 2개에
걸쳐 `shoulder+arm` 복합 부위가 되고, 그것이 `angle_vs_reference__left_shoulder` 의 `shoulder`
부위와 어깨 관절을 공유한다. 판정·처분은 N-19. **가정으로 넘기지 않고 실행 결과로 확인했다.**

## 시뮬 확인 요청 (오케스트레이터)

실행자에게 `mcp__ios-simulator__*` 가 없다 → **렌더/애니메이션은 확인하지 않았고 주장하지 않는다.**
33-G 표는 **미갱신**이다(아래 재채점은 제안).

| # | 케이스 | 도달 경로 | 대조할 승인 요소 | PASS 조건 |
|---|---|---|---|---|
| 1 | **F-8 상시 마커 제거** | 결과 화면 진입 직후. 스켈레톤 토글 **OFF** 유지, 음성/자막 재생 전 | 승인본 ① `.dcap` = 캡처 위 표시가 항목 수(3)만, 그 아래 `.jointchips` | 영상 위 마커 **0개**(그룹 경계·번호 배지·빨강/주황 점 전부 없음) + 칩 행이 보인다. 영상 위 빈 곳을 눌러도 시트가 열리지 않는다(보이지 않는 탭 0, N-15) |
| 2 | **F-8 토글 ON 복귀** | 같은 화면에서 "관절 표시" 토글 ON | 승인본 ① `.mkg` 그룹 경계 | 부위 그룹 경계가 **등장**하고, 경계 안 멤버 관절에 **개별 빨강 원·번호가 나열되지 않는다**(흰 점만) |
| 3 | **4진입점 생존** | 칩 탭 / 점수 계산 내역 행 탭 / 재생바 cuedot 탭 / 가로 전체화면 여백 범례 탭 | — | 네 경로 모두 같은 부위 시트를 연다(번호↔행 대응 유지, D-18) |
| 4 | **S19 pulse (정지 스크린샷으로 판정 불가)** | 동작 비교 카드 재생 → 재생바 **cuedot** 위치 도달 시 자동 정지 + dim + 자막 + "음성 중 — 잠시 멈춤" | 승인본 `:227-228` `.legfx.pulse 1.4s` + `@keyframes legpulse{0%,100%{opacity:1} 50%{opacity:.5}}` | **절차**: ① `mcp__ios-simulator__record_video` 로 음성 큐 구간 **4초 이상** 녹화(1.4초 주기가 최소 2.8초이므로 3초는 경계) → 프레임 추출해 강조 도형 밝기 변화를 본다. ② 녹화 불가 시 `mcp__ios-simulator__screenshot` 을 **0.35초 간격 9장**(=1.4초 주기 2바퀴, 주기의 1/4 샘플링) 연속 캡처. **PASS = 강조 선/원의 밝기가 밝음→어두움→밝음으로 왕복하고, 같은 프레임들에서 dim 배경 밝기는 일정**(N-8). 강조가 계속 같은 밝기면 FAIL, dim 이 함께 진동하면 FAIL |
| 5 | **S19 선/원 분기** | 파워스핀 80 doc → **다리 부위** 음성 큐 구간에서 정지 | 승인본 `:452-455` polyline 3점(halo 아래 + brand 위) / circle r28 | 다리 강조가 **원 하나가 아니라 사지를 따르는 선**이다. ① 선이 **몸통을 가로지르지 않는다**(좌↔우 연결 0) ② 선 시작점이 **엉덩이 관절이 아니라 다리 쪽으로 들어와 있다**(승인본 65%) ③ 흰 halo 가 브랜드 선 **아래**로 깔려 영상 위에서 분리된다 |
| 6 | **S19 원 폴백** | 저신뢰/가려진 부위를 짚는 큐(어깨류 또는 접힌 다리) | 승인본 `:219-221` "확신 없는 모양선은 긋지 않는다" | 그 측이 **선 대신 부위 원**으로 나오거나(고신뢰 멤버 있음) **아무것도 안 나온다**(고신뢰 0). 저신뢰 좌표를 이은 선이 보이면 FAIL |
| 7 | **S1 병합 배지 + 나열 금지** | 엘보 60 doc(한 부위 2감점, 확대 카드 0장) → 토글 ON | 승인본 `:314-317` "항목은 3개인데 동그라미가 7개" → 항목 단위 3개 | 그 부위에 **경계 1개 + `2·3` 형태 병합 배지**(pill), 멤버 관절에 개별 빨강 원 **0개**. 배지 숫자가 잘리지 않는다 |
| 8 | **S1 어깨 그룹 생성** | 파워스핀 80 doc → 토글 ON | 승인본 ① 어깨 그룹 `.mkg` | **어깨 그룹 경계가 존재한다**(현재 FAIL 축 = 어깨는 관절별 점이었다) |
| 9 | **N-19 경계 중첩(판정 요청)** | `arm_extension` + 어깨 per-joint 감점이 함께 있는 doc → 토글 ON | 승인본 `:349` "화면의 표시 수 = 항목 수" | **판정 위임**: "어깨·팔" 경계가 "어깨" 경계를 감싸 **원이 겹쳐 보이는지**. 겹침이 2R#1("동그라미가 여러 개라 혼란") 재발로 보이면 별 플랜(부위 모델 재검토) 필요 — 이 단위에서 고치면 PASS 표면(시트)을 깬다 |
| 10 | **S2 점선/실선 · 문형 단일** | 참고(주황) 관절이 있는 doc → 토글 ON, 그 후 참고 칩 탭 | 승인본 `:182` `.mk.adv{border-style:dashed}` / `:348-350` legend / `:1091` 칩 문형 | ① 참고 마커가 **점선**, 감점 마커가 실선 ② 참고 칩을 누르면 펼쳐지는 안내 문장이 advisory 시트 onecap 문장과 **같은 문장**이다 ③ **N-20**: 참고 **칩 테두리**가 iOS 에서 점선으로 보이는지 확인 — 실선이면 플랫폼 한계(코드 주석 참조), 라벨 "참고: " + 주황색으로 구분되면 수용 |
| 11 | **S3 칩 수 == 시트 수** | 파워스핀 80 / 킵업 60 doc | 승인본 `:338-342` `다리` `어깨` `참고: 손` | 칩 개수가 **부위 시트 개수와 같다**. 각 감점 칩 탭 → 그 부위 시트가 열리고 **1단위 블록 N개 구조가 그대로** 보인다(회귀 0). 칩 라벨과 시트 제목이 **같은 단어**다 |
| 12 | **cleanPass 칩 행 미렌더** | pdshape 100 doc(감점 0) | 승인본 ① 은 감점 항목 화면 | 칩 행이 **아예 없다**(빈 행·빈 여백 0). 축하 카드만 |
| 13 | **IN-01 저신뢰 칩 억제** | `attributionReliability.unreliable` doc | S17 PASS 보존 | 칩 행이 **없고**, 기존 "예상 부위" 카드·"AI 공부 중" 안내 1줄은 그대로 |
| 14 | **회귀 4축** | — | — | ① **S18**: 음성 중 정지·dim·"잠시 멈춤" 라벨·자막 정상 ② **S20**: cuedot 탭 → 해당 항목 이동 ③ **1단위 시트 구조**(번호 헤더·basis·method·numnote) 무회귀 ④ **IN-01 예상 부위 카드** 무회귀 |
| 15 | **LogBox 경고** | 결과 화면 진입 + 음성 큐 구간 통과 | — | 1단위에서 관측된 정체 미상 경고 배너가 **늘지 않았다**. `Animated` 도입으로 새 경고(특히 `useNativeDriver` 계열)가 붙지 않았는지 배너를 열어 내용 확인 |

**렌더 가능 doc 4건은 §C-1 이전 산출이라 `userVideoSec`/`refVideoSec` 가 없다.** 이 단위는 그
필드에 새로 의존하지 않으므로 위 15건 전부 도달 가능하다. 도달 불가 케이스가 나오면 "§C-4 doc
재산출 후 판정"으로 남기고 PASS 를 주장하지 말 것.

## 33-G 재채점 제안 (표는 미갱신 — 렌더 확인 후 오케스트레이터 판단)

| 행 | 현 판정 | 제안 | 근거 (코드/스위프 축) | 렌더 확인 필요 |
|---|---|---|---|---|
| **S19** | FAIL | **PASS 후보** | 선/원 분기 순수 로직 12축 + 승인본 컷 2 실측 conf 재현 + `PULSE_PERIOD_MS 1400` 단일 선언 + `Animated.loop` native driver + halo/core 굵기 비 9:5·8:4 + 근위 inset 0.65 실좌표 검산 | **예** — pulse 는 다중 프레임(#4), 선 기하는 #5·#6 |
| **S1** | PARTIAL | **PASS 후보** | 마커 = 부위 그룹 1경계(스위프 40/40) + 멤버 개별 원 억제(`groupedKeypoints`) + 병합 배지 | **예** — #7·#8 (특히 어깨 그룹 존재) |
| **S2** | PARTIAL | **부분 PASS** | 문형 단일 소스화 완료(사본 grep 0) + 그룹 점선 지원 + 개별 참고 점 점선 기존 유지 | **예** — #10. 칩 테두리 점선은 iOS 한계(N-20)라 **완전 PASS 주장 안 함** |
| **S3** | PARTIAL | **PASS 후보** | 부위 칩 신설 + 칩 수 == 그룹 수 == 시트 수(스위프 전건) + 라벨 == 시트 제목 문자 동일 | **예** — #11 |
| **F-8** | FAIL | **PASS 후보** | `markersVisible` 게이트 + "상시 렌더" 문구 0 + 숨김 시 탭 타깃 0 + 칩 행 대체 진입점 | **예** — #1·#2·#3 |
| **S5** (보류) | 보류 | 판정 재료 추가됨 | 칩 행의 문장 신설 0(라벨·문형 전부 빌더/상수 산출), cleanPass 시 행 미렌더 | **예** — #12 와 함께 기본 화면 전체 문장 확인 |

## 이관 항목

| # | 항목 | 이관 | 근거 |
|---|---|---|---|
| ① | advisory(참고) **상세 시트** — 크롭 포함 | 별 플랜 | N-6. advisory 는 `record` 가 없어(`matchZoomForDeductionRecord` 가 advisory 제외) 시트 뷰모델 입력이 성립하지 않는다. 시트 신설은 수리에 새 범위(D-39) |
| ② | **reduce-motion** 대응(무한 pulse a11y) | 별 플랜 | N-9. 승인본이 pulse 를 지정했고 a11y 분기는 새 범위 |
| ③ | **N-19 경계 중첩** — 복합 부위 모델 재검토 | 시뮬 판정 후 결정 | 부위 모델(1단위 M-3)은 PASS 표면. 겹침이 belle 반려 계열로 판정되면 별 플랜에서 부위 모델 자체를 다룬다 |
| ④ | **N-20 칩 점선** — iOS dashed + borderRadius | 플랫폼 한계 | 우회는 borderRadius 0(승인본 pill 위반) 또는 커스텀 dashed 렌더(새 범위) |
| ⑤ | S13 일러스트 장면일치 · S23 illu-float · S12 어휘 잔재 · F-4~F-7 | §C-2 다음 단위 | 이 단위 범위 = 영상 위 표시 계층 |

## 알려진 한계 (정직 기록)

1. **렌더·애니메이션 미검증.** 실행자 도구에 시뮬레이터가 없다. typecheck·순수 로직·grep 게이트는
   전부 통과했으나 "화면에서 선이 사지 위에 앉는지 / 1.4초로 깜빡이는지 / 마커가 0개인지"는
   **확인하지 않았다.** 위 요청표가 그 위임이다.
2. **선의 해부학적 정합은 스위프 축이 아니다.** 스위프는 좌표를 넣지 않는다(어느 관절을 어떤
   형태로 그릴지만 판정). §C-1 스위프와 같은 한계 — 실 doc 좌표 판정은 시뮬/§C-4.
3. **`advisory` 그룹 경계 코드는 현재 미발화**(N-18 — result.tsx 가 advisory 그룹을 만들지 않는다).
   승인본 ① 의 참고 표시가 개별 점선 마커이기 때문이며, 오버레이 능력만 준비돼 있다.
4. **전 관절 고신뢰 스위프에서 원 갈래가 0**이다(전부 선으로 갈림 = 정상). 원 갈래의 커버리지는
   단위 테스트 4축(승인본 컷 2 실측 conf 재현)이 담당한다.
5. **LogBox 경고 내용은 여전히 미확인**(1단위 이월). `Animated` 도입이 새 경고를 유발했는지는
   시뮬 확인 #15 에서 판정한다.

## Self-Check: PASSED

생성 파일 존재 확인 (`[ -f ]`):
`app/src/lib/focusShape.ts` · `app/src/lib/__tests__/focusShape.test.ts` ·
`app/src/components/PartChipsRow.tsx` · `sweep_markers_focus.test.ts` ·
`sweep_markers_focus.json` · `260730-szk-SUMMARY.md` — **6/6 FOUND**

커밋 존재 확인 (`git log --oneline --all | grep`):
`c070f8c` `cdeeba9` `d04b54f` `f2c5e20` `361aefa` `41cb6bf` `ea6bc6c` `df9d193` — **8/8 FOUND**

수치 재실행 확인: cueTrack 7 · deductionSheet 35 · focusShape 12 · gaugeGeometry 4 ·
manualOffset 6 · resultSections 5 · summarySource 11 · visualCards 21 (= 101) + 스위프 2,
**fail 0** — SUMMARY 표와 일치. `focusShape.ts` 199줄 / `PartChipsRow.tsx` 134줄 (표기와 일치).

미주장 항목(정직): 시뮬 렌더·pulse 애니메이션·33-G 표 재채점은 **수행하지 않았다**.
