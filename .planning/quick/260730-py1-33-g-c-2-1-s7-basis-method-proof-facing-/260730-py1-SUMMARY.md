---
phase: quick-260730-py1
plan: 01
subsystem: app-result-sheet
tags: [33-G, S6, S7, F-3, deduction-sheet, approved-mockup-7R]
requires:
  - "FaultZoomComparison.userVideoSec / refVideoSec (quick-260730-l7t 백엔드 방출)"
  - "buildDeductionMarkers.recordNumbers (전역 마커 번호 단일 출처)"
  - "matchZoomForDeductionRecord (33-12 A-5 criterion 키 조인)"
provides:
  - "lib/deductionSheet.ts — 부위 단위 시트 뷰모델 + 승인 카피 조립 (순수 함수)"
  - "DeductionDetailSheet 승인 목업 7R ② 구조 렌더"
  - "참고코너 자세 비교 페어의 실영상 초 정합 (F-3 앱분)"
  - "theme colors infoTeal / infoTealBg / infoTealBorder"
affects:
  - "app/src/app/analysis/result.tsx (시트 배선 · 참고코너 poseFrames)"
  - "app/src/lib/deductionLabels.ts (부위 사전 추가, 기존 export 무수정)"
tech-stack:
  added: []
  patterns:
    - "조판 로직을 순수 뷰모델로 격리 (resultSections.ts 선례) — 컴포넌트는 렌더만"
    - "승인 확정 문구 상수 원문 박제 + 자리표시자 치환"
    - "HTML 대신 {text,bold} 세그먼트 → 중첩 Text (RN 마크업 미해석)"
    - "criteria yaml glob 파생 스위프로 등재 10동작 일반화 확인"
key-files:
  created:
    - app/src/lib/deductionSheet.ts
    - app/src/lib/__tests__/deductionSheet.test.ts
    - .planning/quick/260730-py1-33-g-c-2-1-s7-basis-method-proof-facing-/sweep_sheet_blocks.test.ts
  modified:
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/app/analysis/result.tsx
    - app/src/lib/deductionLabels.ts
    - app/src/lib/visualCards.ts
    - app/src/theme/colors.ts
decisions:
  - "초 표기 정본 = paircap 텍스트 (사진 속 초 지칭 안내 라벨 제거, M-1)"
  - "proof 증거 3컷 미구현 = 자리도 두지 않는 fail-closed (M-10, §C-4 이관)"
  - "basis 구간 축은 record별 측정창 방출 전까지 미구현 (M-7, §C-4 이관)"
  - "부위 그룹 키 = 부위 토큰 정렬 결합 (다중 부위 record 결정성, M-15)"
  - "basis/method = record 스코프 zoom, paircap/onecap/facing = 그룹 스코프 zoom (M-17)"
metrics:
  duration: "약 2시간"
  completed: 2026-07-30
  tasks: 3
  commits: 6
  files: 9
---

# quick-260730-py1: 33-G §C-2 앱 수리 1단위 (S6 부위 단위 시트 · S7 블록 요소 · F-3 앱분) Summary

승인 목업 7R ② 의 **부위 단위 시트**를 데이터로 재현했다 — record 단위 시트를 부위 그룹으로
접고, 승인본에만 있던 블록 요소(번호 헤더 · basis · method · numnote 위치 · facing · paircap
실영상 초 · onecap)를 신설하고, 참고코너 자세 비교 페어의 초 추정(rep 인덱스 ÷ fps)을
백엔드 방출값 소비로 교체했다. **백엔드 변경 0 · 신규 의존성 0 · OTA 미발행.**

## 커밋

| # | 해시 | 내용 |
|---|---|---|
| 1 | `5b8d61c` | test — 부위 단위 뷰모델 실패 테스트 (TDD RED, 25 검증) |
| 2 | `d670906` | feat — deductionSheet.ts 신설 + deductionLabels 부위 사전 (GREEN) |
| 3 | `a821933` | feat — 시트 승인 구조 렌더 + result.tsx 배선 + infoTeal 토큰 3종 |
| 4 | `cfb3694` | feat — F-3 앱분(참고코너 페어 초) + 등재 10동작 스위프 |
| 5 | `73f98ab` | fix — IN-01 추정 부위 시트에 확정 칩 미표시 (M-21) |
| 6 | `a9a9177` | fix — paircap 좌우 라벨 flexShrink (좁은 기기 밀림 방지) |

변경 규모: 9 파일 / +2,032 / −228 (base `85181a7`). 커밋 6건.

## 자체 도출 결정 적용 결과 (M-1~M-14)

D-39 재논의 없음 — belle 에게 아무것도 묻지 않았다. 플랜의 M-1~M-14 를 그대로 적용했고,
플랜이 답을 주지 않은 잔여 지점은 "승인본이 정답 / 수리에 새 범위 금지" 원칙으로 **M-15~M-21**
로 자체 도출했다.

| M | 결정 | 적용 결과 |
|---|---|---|
| M-1 | 초 정본 = paircap 텍스트, 사진 속 초 지칭 안내 제거 | `TIME_STAMP_NOTE_MAIN/PAREN` + 렌더 블록 제거 (grep 0). 백엔드 `_stamp_time` 무접촉 |
| M-2 | 초 포맷 `실 {toFixed(1)}초` | `formatVideoSecKo` — 비유한·음수 → null. `3.07` → `실 3.1초` |
| M-3 | 부위 그룹 키 = keypoint → 부위 토큰, 좌우 미분할 | `BODY_PART_OF_KEYPOINT` 12관절 전건 + `regionPartKeyForRecord`. 투영 공집합 → `criterion:{id}` |
| M-4 | 블록 번호 = 전역 `recordNumbers` | 그룹 2건+ 만 번호, 1건·null·estimatedArea 는 번호 절 생략. 스위프가 전 동작 대조 |
| M-5 | 그룹 크롭 = 저장순 첫 매치, 블록 순서 = 그 record 먼저 | `primaryRecordIndex` + `blockRecordIndexForCrop`(다른 카드일 때만, 중복 렌더 0) |
| M-6 | onecap = 마킹 기하 단정 금지 | `이 사진은 {무엇}을 기준 자세와 견줘요`. "빨간 두 줄/꼭짓점" 문구 0 (테스트 고정) |
| M-7 | basis = 성립하는 축만, 구간 축 이관 | 3분기 구현(초 보유 / 초 부재 / {무엇} 미상). 구간 축 미구현 = §C-4 |
| M-8 | method = source × deviationSource 키잉 | vision / geometry+reference_relative(+기준 초) / ipsf_absolute=null |
| M-9 | facing = reference_relative + 두 초 상이 | 승인본 분포(어깨 있음 / 다리 없음)를 데이터로 재현. "정은지는 무릎을 모아…" 절 제외 |
| M-10 | proof 3컷 = 미구현 fail-closed | 뷰모델에 필드 **자체 부재**(빈 배열조차 없음). 테스트가 `'proof' in block === false` 고정 |
| M-11 | F-3 앱분 = 같은 카드에서 초 함께 읽기 | `pickCompareFrames` 가 `userSec/refSec` 동반 반환. `frameIdx` 는 rep 공간 유지 |
| M-12 | S12 어휘는 범위 밖 | 헤더가 `criterionLabelKo` 단일 출처 소비 — 라벨 사전 무수정(다음 단위 자동 전파) |
| M-13 | 승인본 밖 기존 요소 처분 | `evidenceBox` → numnote 대체. `bullets`/`coachConnect`/`aiNoteBox`/`estimatedBadge`/`refMatchNote` 5개 존속(위치만 이동) |
| M-14 | 조판 = 앱 토큰 우선 | 본문급 E2 토큰 / 소형 주석급 caption. `infoTeal`·`infoTealBg`·`infoTealBorder` 신설, 하드코딩 hex 0 |

### 신규 도출 (M-15~M-21)

| M | 지점 | 결정과 근거 |
|---|---|---|
| **M-15** | record 가 두 부위에 걸칠 때 그룹 키 | mode3 `arm_extension` → region `arms`(어깨+손) → 토큰 `{shoulder, arm}`. 결정적 키가 필요하므로 **머리→발 정렬 순서(`shoulder, arm, leg`)로 결합**(`shoulder+arm`), 제목은 라벨을 `·` 로 결합(`어깨·팔`). 대안(첫 토큰만 채택)은 팔 신전 항목을 '어깨' 시트로 보내 라벨이 거짓이 된다 |
| **M-16** | 플랜 Task 3 문면 "zoom 없는 record → basis == null" 과 M-7 의 충돌 | **M-7 우선**(자체 도출 결정이 authoritative). basis 첫 문장("이 항목은 겨드랑이 벌림을 재요")은 사진·초를 지칭하지 않아 zoom 없이도 참이다 — 이걸 지우면 정보를 잃고, 남기면 거짓이 없다. 스위프 불변식을 더 정확한 축으로 교체: zoom 없으면 **paircap/onecap/facing null + basis 에 '초'·'위 사진' 문자 0 + method 에 '기준 사진' 문자 0** |
| **M-17** | basis/method 가 어느 zoom 의 초를 쓰나 | **record 스코프**(`zooms[i]`) — 그 블록의 자기 카드만. 상단 크롭으로 폴백하면 다른 record 의 순간을 이 항목의 측정 순간이라고 말하게 된다(교차 귀속 = 날조). paircap/onecap/facing 은 상단 크롭을 지칭하므로 **그룹 스코프**(primary zoom) |
| **M-18** | 승인 문구의 '기준' 을 mode3 에서 어떻게 쓰나 | `rightPairLabel` 의 괄호 앞부분을 취해 비교 명사를 파생(`기준 (정은지)` → `기준`, `지난 영상` → `지난 영상`). mode1 은 승인 문형과 **바이트 동일**하고 mode3 는 자기 라벨로 흐른다 — mode 리터럴 분기 0 |
| **M-19** | `buildRegionSheetView` 입력에 `faultJoints` 추가 | 플랜의 input 목록에 없지만 부위 투영(`projectDeductionRecordKeypoints`)의 필수 인자다. 결과를 caller 가 대신 계산해 넘기면 투영 규칙 사본이 생긴다 |
| **M-20** | 용어줄(terminologyMap)의 기준 criterion | 뷰모델이 `primaryCriterion` 을 함께 나른다. 렌더가 헤더 라벨 문자열에서 criterion 을 역파싱하는 방식은 라벨 규칙의 역방향 사본이라 폐기했다 |
| **M-21** | IN-01 추정 부위 시트의 크롭 칩 | `estimatedArea=true` 면 "오늘 고칠 것" 확정 칩을 걸지 않는다. 바로 아래 "예상 부위" 배지와 모순되고, IN-01(belle 2026-07-24)은 확정 단정 표면을 강등하는 결정이다. 승인 목업 ② 에 추정 케이스가 없으므로 이 분기의 정답은 승인본이 아니라 IN-01 원칙에서 나온다 (S17 PASS 보존) |

## 검증

| 게이트 | 결과 |
|---|---|
| `node --test deductionSheet.test.ts` | **25 pass / 0 fail** (14 축: 그룹핑·criterion 그룹·번호·estimatedArea·블록순서·paircap·method·basis·facing·onecap·proof부재·방어·HTML금지·numnote) |
| `node --test sweep_sheet_blocks.test.ts` | **3 pass / 0 fail** — 등재 10동작 불변식 6종 |
| `npm run typecheck` | clean |
| grep — 신규 모듈 동작명 리터럴 | **0** (`ref-` 비주석 0건 + 스위프 INV-6b 가 10 모션 id 부재 assert) |
| grep — `TIME_STAMP_NOTE` 잔재 | **0** |
| grep — 컴포넌트 hex 리터럴 | **0** |
| grep — `compareFrames.(userIdx\|refIdx) /` | **2 → 0** |
| 범위 밖 fps 환산 2곳 | 불변 (`legacyStartOffsetSec` :1517-1518 · `buildCueWindows` :1861) |
| `git diff --stat app/package.json package-lock.json` | 빈 출력 (신규 의존성 0, T-33G2-SC) |
| `git diff --stat backend/` | 빈 출력 (**채점 무접촉 D-44**) |
| 기존 앱 테스트 회귀 | 8 파일 86 pass / 0 fail (cueTrack 7 · gaugeGeometry 4 · manualOffset 6 · resultSections 5 · summarySource 11 · visualCards 21 · pickerFailure 7 · 신규 25) |
| OTA | **미발행** (D-45) |

### 스위프 수치 표 (등재 10동작 일반화)

원문 = `sweep_out/sweep_sheet_blocks.log`. 동작 목록은 `backend/judging_data/criteria/*.yaml`
**glob 파생**(하드코딩 0). record 파생 = criteria yaml 관절 ∪ 전 kismam angle key
(l7t `_units_for` 와 같은 규칙 — reference_relative 는 전 관절에 criterion 을 만들고,
승인 목업의 어깨 카드가 바로 그 갈래라 yaml 만 보면 놓친다).

| 동작 | yaml joint | record | 그룹 | 블록 | 번호부여 | method null(ipsf) | basis null(zoom無) |
|---|---|---|---|---|---|---|---|
| ref-climb | 0 | 13 | 6 | 13 | 8 | 3 | 1 |
| ref-elbow-twist-sister | 0 | 13 | 6 | 13 | 8 | 3 | 1 |
| ref-foxtop-split | 6 | 13 | 6 | 13 | 8 | 3 | 1 |
| ref-foxtop | 6 | 13 | 6 | 13 | 8 | 3 | 1 |
| ref-invert | 6 | 13 | 6 | 13 | 8 | 3 | 1 |
| ref-kip-up | 0 | 13 | 6 | 13 | 8 | 3 | 1 |
| ref-pdshape | 0 | 13 | 6 | 13 | 8 | 3 | 1 |
| ref-peter-pan | 0 | 13 | 6 | 13 | 8 | 3 | 1 |
| ref-power-spin | 2 | 13 | 6 | 13 | 8 | 3 | 1 |
| ref-sideway-spin | 6 | 13 | 6 | 13 | 8 | 3 | 1 |

**합계: 동작 10 / record 130 / 블록 130 / 소실 0 / 중복 0 / 예외 0 / null 반환 0.**

불변식 6종:
1. criteria 파일 **10개** 발견 (0건이면 FAIL). yaml joint 0건은 정상 — 그 동작은 IPSF
   absolute criterion 이 없고 reference_relative + vision 이 채점을 담당한다.
2. 모든 record 가 정확히 1개 그룹에 귀속 — Σ 블록 == record 수, 중복 귀속 0.
3. 블록 헤더 번호 == 전역 `recordNumbers` 값, 단일 블록에 번호 붙음 0. 헤더 라벨은
   `criterionLabelKo` 단일 출처와 일치.
4. `ipsf_absolute` geometry → `methodLine == null`(없는 문형 창작 0) · vision → 문형 방출 ·
   `reference_relative` → 정렬 문형 방출.
5. zoom 없는 record → paircap/onecap/facing null + basis 에 '초'/'위 사진' 0 +
   method 에 '기준 사진' 0 (M-16).
6. 전 동작·전 record 예외 0 · 유효 index 반환 null 0 · HTML 문자 0 · proof 자리 0.

**동작명 분기 0 의 성격 (정직한 해석).** 표의 그룹/블록 수가 10 동작 전건 동일한 것이
증거다 — 이 뷰모델은 모션 데이터를 **읽지 않는다**(criterion·source·deviationSource·
keypoint 투영만 읽는다). §C-1 처럼 "모션별 데이터로 거동이 갈린다"를 보인 게 아니라,
"모션이 거동에 개입할 경로가 없다"를 보인 것이다. 모션별로 갈리는 축(criteria yaml 관절
0/2/6)이 입력에 실제로 존재했고 구조 결과를 흔들지 않았다.

## 시뮬 확인 요청 (오케스트레이터)

**나는 시뮬레이터를 띄울 수 없다** (`mcp__ios-simulator__*` 미보유). 아래는 렌더 확인이
필요한 항목이고, 33-G 표 S6/S7/F-3 행은 **갱신하지 않고 그대로 두었다** — 렌더를 본 뒤
오케스트레이터가 재채점할 판단 자료를 아래 §33-G 재채점 제안에 적었다.

**공통 준비.** 검증 doc = `uat-33-16-verification` (파워스핀 80 · 킵업 79 · pdshape 100).
결과 화면 진입 후 스크린샷은 이 디렉터리에 남길 것 (증거 사슬 — §C-1 결손 1건 재발 방지).

| # | 케이스 | 도달 경로 | 대조할 승인 요소 | PASS 조건 |
|---|---|---|---|---|
| 1 | **부위에 감점 2건** (파워스핀 80 — 다리) | 결과 화면 → "오늘 고칠 것" 카드의 `확대 비교 자세히 보기 ›` 또는 영상 위 번호 점 탭. 다리 계열 항목(스플릿/무릎)을 열 것 | 목업 ② `renderDetail('legs')` — 크롭 **1쌍**, 그 아래 좌우 paircap, 그 아래 onecap 1줄, **결함 블록 2개**(각 블록 맨 위 `고칠 것 1 — …` / `고칠 것 2 — …` 브랜드 틴트 바) | 시트가 **1개**만 열리고 그 안에 블록이 **2개** 보인다. 블록 헤더 번호가 영상 위 마커 번호와 같다. 둘째 블록이 스크롤 없이도 존재를 알 수 있다(belle "무릎 피는 거 하나 어디 갔냐") |
| 2 | **감점 1건 부위** (킵업 79 — 어깨 계열 권장) | 같은 진입점, 어깨/팔 항목 | 목업 ② `renderDetail('shoulder')` — 블록 헤더가 `고칠 것 — 항목 (−N점)` **번호 없음**, basis 회색 박스, method 틸 박스, numnote 맨 뒤 작은 회색, 블록 전부 뒤 facing 틸 박스 | 번호 절이 **없다**. basis/method 가 보이고 numnote 가 블록 **맨 뒤**에 작게 있다. 어깨(reference_relative) 항목이면 facing 안내가 보인다 |
| 3 | **advisory / estimatedArea** | estimatedArea = 역립 저신뢰 doc 의 `예상 부위 확대 비교 ›` 링크 | 시트 제목 `예상 부위 (참고)`, "예상 부위" 주황 배지, numnote 자리에 IN-01 안내(관절별 수치 대신), **"오늘 고칠 것" 칩 미표시**(M-21) | 관절별 −N° 수치가 안 보이고 안내 문장이 보인다. 확정 칩·번호가 없다 |
| 4 | **paircap 기준측 초** (1·2 케이스에서 함께) | 위와 동일 | 목업 6R: 좌 `내 자세 · 실 1.7초` / 우 `기준 (정은지) · 실 3.07초` | 좌우 두 줄이 크롭 **바로 아래** 좌우 정렬로 보이고 **기준측에도 초가 있다**. 사진 속 베이크 초와 값이 같다(자릿수만 1자리). "사진 속 초는 …" 안내 문장은 **없어야** 한다(M-1) |
| 5 | **F-3 자세 비교 페어** | 결과 화면 맨 아래 "참고하세요" → 자세 비교 실프레임 페어 | 확대 크롭(위 1·2 케이스)과 **같은 순간** | 기준측 프레임이 확대 크롭의 기준 패널과 같은 자세다(대표 프레임이 아니다). 초가 안 내려온 legacy doc 이면 실프레임 대신 **스켈레톤 뷰어**로 폴백(빈 화면·틀린 프레임 금지) |
| 6 | **회귀 — 존속 요소 5개** | 아무 시트 1개 | `bullets`(용어줄·거울 확인) · `coachConnect` · `aiNoteBox` · `estimatedBadge` · `refMatchNote` | 5개가 여전히 보인다(위치는 일러스트 뒤로 이동). 하단 "이 원인은 어떻게 측정됐나" 박스는 **없어야** 한다(numnote 로 대체) |
| 7 | **크래시·레이아웃** | 1~3 전부 | — | 시트 열림/닫힘 크래시 0, 블록 카드 테두리 안에서 텍스트 잘림 0, 이모지 0 |

**렌더에서 깨질 수 있는 지점(중점 관찰).** ① 블록 카드가 `overflow:hidden` + 헤더 음수
마진 없이 구현됐다 — 헤더 바가 카드 좌우 끝까지 닿는지. ② basis 의 굵은 문두가 중첩
`Text` 로 그려진다 — `<b>` 문자열이 화면에 노출되면 즉시 결함(T-33G2-01, 테스트로는 소스
문자열만 고정했다). ③ `cueBox` 가 `alignSelf: 'flex-start'` 라 긴 큐 문장에서 줄바꿈이
자연스러운지.

## 33-G 재채점 제안 (표는 미갱신 — 렌더 확인 후 오케스트레이터 판단)

| # | 현 판정 | 제안 | 근거 (코드/테스트) |
|---|---|---|---|
| S6 | PARTIAL | **PASS** (렌더 1·2·4 PASS 조건 충족 시) | 부위 단위 그룹핑 구현 + 스위프 10동작 소실·중복 0 / paircap 좌우 + **기준측 초** 구현(테스트 6·6b) / onecap 구현(테스트 10·10b) / 크롭 1쌍 = 그룹 첫 매치(테스트 5) |
| S7 | FAIL | **PARTIAL** (proof 축만 미달) | 번호 헤더(테스트 3·3b, 스위프 INV-3) · basis(테스트 8) · method(테스트 7·7b, INV-4) · numnote 위치(테스트 14) · facing(테스트 9·9b) **5/6 구현**. **proof 증거 3컷은 M-10 로 미구현** — 백엔드가 카드당 합성 PNG 1장만 방출하고 "좋았던/감점/마무리" 분류는 doc 에 없는 측정 판단이다. 앱이 각도 시계열로 정하면 판정 재해석이므로 자리도 두지 않았다 → §C-4 (백엔드 3컷 방출)가 조건 |
| F-3 | 백엔드 PASS / 앱 잔여 | **PASS** (렌더 5 PASS 조건 충족 시) | rep 인덱스 ÷ fps 초 추정 2곳 제거(grep 2→0). 초는 `userVideoSec`/`refVideoSec` 방출값만. `refSec` 부재 → 기존 `framesReady=false` 스켈레톤 폴백(신규 분기 0) |

S6·F-3 를 내가 PASS 로 못 박지 않은 이유: 두 항목의 완료 판정은 "화면에 그렇게 보이는가"고
코드 통과는 그 증거가 아니다(D-40 / [[verify-against-approved-mockup-not-just-code]]).

## §C-4 이관 항목

| # | 항목 | 이관 이유 |
|---|---|---|
| ① | 백엔드 `_stamp_time` 제거 (crop PNG 베이크 초) | 초 정본이 paircap 텍스트로 확정(M-1)됐으나 코드만 바꾸면 **기존 crop PNG 와 불일치**한다 — crop 전수 재생성과 같은 단위에서 해야 한다. 그 사이에도 두 표기는 **같은 값**이라 모순이 아니다 |
| ② | `markingKind` 방출 (어떤 마킹이 베이크됐는지) | onecap 이 "빨간 두 줄 / 꼭짓점 = 겨드랑이"를 말하려면 카드별 마킹 종류가 필요하다. 현재 doc 에 없고(렌더 지역변수), 각도 베이크는 21/110 카드만 성립하므로 상시 문구는 대부분 거짓 지칭이 된다 (M-6) |
| ③ | record별 `measureWindowStartSec` / `measureWindowEndSec` 방출 | basis 의 **구간 축**("실제 재생 6.3~8.2초 구간에서 재요", "7.3~7.7초에 도로 접힘")의 조건. 현 계약의 측정창은 record별이 아니라 공유 단일 창이고 창 인덱스→초 변환 fps 가 앱에 없다 (M-7) |
| ④ | proof 증거 3컷 방출 (초 + 캡션 분류) | S7 의 유일한 미달 축. 카드당 PNG 1장 → 3컷 + "좋았던/감점/마무리" 분류를 백엔드가 방출해야 한다 (M-10) |
| ⑤ | S12 어휘 잔재 3곳 (`다리 신전(펴짐)` 등) | 블록 헤더가 `criterionLabelKo` 단일 출처를 소비하므로 라벨 수정이 자동 전파된다 — 다음 단위에서 사전만 고치면 된다 (M-12, 이 단위에서 사전 무수정) |

## 알려진 한계

- **`isAdvisoryOnly` 는 현 진입점에서 도달 불가.** 시트 진입은 전부 감점 record 이고
  `matchZoomForDeductionRecord` 가 advisory 카드를 배제하므로 `primaryZoom.tier==='advisory'`
  가 실제로 참이 되는 경로가 지금은 없다. 플랜 behavior 가 명시한 축이라 구현·테스트했고
  (테스트 10c), advisory 카드 진입점이 생기면 즉시 유효해진다.
- **부위 그룹 제목 접미가 criterion 그룹에서 어색하다.** `바디 라인 부위 상세` /
  `측정 기하 종합(정량화 불가 폴백) 부위 상세`. 규칙을 하나로 유지하는 대가이고(분기 추가 =
  새 범위), criterion 그룹은 투영이 공집합인 드문 경로다. S12 어휘 수정에서 라벨 자체가
  개선되면 함께 나아진다.
- **facing 문구의 부위 지칭이 criterion 그룹에서 부정확할 수 있다** (`… 바디 라인 각도만
  견줘 보세요`). 게이트가 `reference_relative` 라 실제 발화 조합은 관절 각도 항목이다.

## Self-Check: PASSED

생성 파일 4/4 존재 (`deductionSheet.ts` · `deductionSheet.test.ts` ·
`sweep_sheet_blocks.test.ts` · `sweep_out/sweep_sheet_blocks.log`), 커밋 6/6 존재
(`5b8d61c` `d670906` `a821933` `cfb3694` `73f98ab` `a9a9177`).
