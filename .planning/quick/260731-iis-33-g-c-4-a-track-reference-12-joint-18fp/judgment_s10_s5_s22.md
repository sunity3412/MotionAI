# S10 · S5 · S22 판정 — quick-260731-iis (33-G §C-4 A-트랙)

원칙: **본 것 / 못 본 것 / 그것을 성립시킨 행위**를 나눠 적는다.
"남의 문서를 읽은 것"은 검증이 아니다. 조용한 PASS 금지.

---

## S10 — 다리류 벌림각, **실 doc** 판정

### 판정: **PASS (조건부 — 계약대로 갈린다)**

f5h 가 못 본 것(합성 좌표라 인물과 정렬 안 됨)을 여기서 봤다.
재산출 doc 4건 중 `split_angle` 카드는 **2건**(kip-up, power-spin)에 있다.
elbow-twist-sister·pdshape 에는 `split_angle` 카드가 **없다** (있는 것처럼 쓰지 않는다).

| doc | 카드 | 선 2개 + 호 | 해부학적 정합 | 그것을 성립시킨 행위 |
|---|---|---|---|---|
| kipupFault1785373695 | `zoom_split_angle` | **보인다** | **정합한다** | PNG 를 Read 로 직접 열어봤다 |
| powerspinFault1785373695 | `zoom_split_angle` | 안 보인다(원 마커 폴백) | — | PNG 를 Read 로 직접 열어봤다 |

**kip-up 에서 본 것** — 골반을 꼭짓점으로 두 선이 뻗고 그 사이에 호가 있다.
두 패널(학생/기준) **모두** 그려졌다(both-or-neither 유지). 선이 실제 두 다리를 따라간다 —
뒤쪽 지지 다리와 앞으로 뻗은 다리 각각에 겹친다. **이것이 f5h 가 못 본 해부학적 정합이고,
실 doc 에서 성립한다.**

**power-spin 에서 본 것** — 두 패널 모두 브랜드색 원 마커. 선·호 없음. crop 이 골반 주변으로
매우 좁고 다리가 crop 밖에 있다.

### power-spin 이 폴백한 이유 — 어디까지 쟀고 어디부터 못 쟀나

**잰 것**: 두 doc 모두 **양측 6개 다리 관절(hip/knee/ankle L·R)이 학생·기준 양쪽에서
`fz._gated_kp` 를 통과**한다(1/1/1/1/1/1). 프로덕션 술어를 직접 호출해 확인했다.
→ conf 게이트 탈락은 **원인이 아니다**(제거됨).

**못 잰 것**: `_side_ok` 의 나머지 조건인 **crop 포함 여부**. `_pt_in_crop` 을 부르려면
crop box(left/top/side + 프레임 h·w)가 필요한데 **analysis doc 이 crop box 를 저장하지
않는다**. 로컬에 원본 프레임도 없다(imageio 미설치, 신규 설치 금지).
→ 따라서 "ankle·knee 둘 다 crop 밖(계약 4행)" 은 **이미지 관찰 + conf 원인 제거에 의한
추론**이지 직접 측정이 아니다. 그렇게 표기한다.

### 계약 4·5·6행 실 doc 발생 여부

| 계약행 | 실 doc 에서 발생했나 | 근거 |
|---|---|---|
| 4행 ankle·knee 둘 다 crop 밖 | **발생 추정**(power-spin) | 원 폴백 관찰 + conf 원인 제거. crop box 미측정 |
| 5행 골반 crop 밖 | **미관찰** | 2건 표본에 없었다. 없다고 단정하지 않는다 |
| 6행 좌우 비대칭 | **미관찰** | 2건 표본에 없었다 |

### 합성 스위프(T4) 쪽 S10

`sweep_out/real-ref` 에서 `split_angle` **10/10 leg_drawn=True** (f5h 10/10 유지, 회귀 0).
`--assert` 의 INV-D1(leg_drawn == user_ok AND ref_ok) **위반 0**.
동작축에서 끝점이 갈린다 — ankle 채택 3동작 / knee 폴백 7동작 = 계약 1행·2행 동시 실증.

---

## S22 — 멈춤 컷 = 결함 텍스트 서술 순간 (record 실측 창 안)

### 판정: **창 포함은 구조적으로 성립 / 멈춤 프레임은 창의 시작(결함 순간 −0.8초) / 화면 미확인**

**잰 것 1 (데이터)** — 재산출 doc 12개 카드 전건에서
`userFrameIdx / userVideoSec = 18.0000` 이고 `keypointReport.fps = 18.0`.
즉 카드가 표시하는 초 = `userFrameIdx / kpFps` 로 정확히 일치한다(파이썬으로 값을 찍었다).

**잰 것 2 (코드 경로)** — `app/src/lib/cueTrack.ts::buildCueWindows` 가 만드는 창은
`center = userFrameIdx / userFps`, `[center − windowSec/2, center + windowSec/2)`.
호출측 `result.tsx:1938` 이 `userFps = result.keypointReport?.fps || 9`, `CUE_WINDOW_SEC = 1.6`
을 넘긴다. → **창 중심 = 카드의 `userVideoSec` = record 실측 시점**. 반폭 0.8초.

**잰 것 3 (멈춤 배선)** — `VideoCompare.tsx:676` 의 100ms tick 이 `activeCue(cueWindows, cL)` 로
큐를 판정하고, **큐 텍스트가 바뀌는 그 tick 에서** `speakCue` 가 실제 발화를 시작한 경우에만
`leftPlayer.pause() / rightPlayer.pause()` 를 호출한다(`VideoCompare.tsx:697~703`).
→ 멈춤은 **재생 헤드가 창에 진입하는 순간** = `startSec = center − 0.8s` 에 일어난다.

**따라서**: 멈춤 시각은 record 실측 창 `[start, end)` **안에 있다**(창의 하단 경계 그 자체).
불변식 ①("실측 창 안")은 **구조적으로 성립**한다.
다만 얼어붙는 프레임은 **결함 순간 그 프레임이 아니라 그보다 0.8초 이른 프레임**이다.
승인 스펙 문구가 "창 안"이면 충족, "결함 그 순간의 컷"이면 0.8초 이르다 — 이 구분은
데이터가 아니라 스펙 해석이라 belle 확인 몫으로 남긴다.

**못 본 것**: 실제 화면에서 어떤 컷이 얼어붙는지. 실행자 도구로 시뮬레이터/실기기 재생
화면을 캡처할 수 없고, **멈춤은 `audioEnabled` + 발화 성공(started=true)이 조건**인데
F-6(실기기 음성 무음)이 미해결이라 실기기에서 큐 자체가 안 울릴 수 있다.
**어디서 볼 것**: 결과 화면 → 음성 큐 설정 ON → 재생 → 첫 큐에서 멈추는 프레임이
확대 카드의 표시 초(power-spin 2.11초 / kip-up 0.89초)보다 0.8초 이른지 확인.

---

## S5 — 기본 화면 새 문장 0 (D-05)

### 판정: **미판정** (조용한 PASS 하지 않는다)

**잰 것** — 재산출 doc 이 실어 보내는 문장 필드 인벤토리를 뽑았다(고유 개수):
`statusLine` 14 · `cueLine` 12 · `whyLine` 11 · `coachQuestion` 11 · `exerciseReason` 11 ·
`mission.headline` 1. 전부 백엔드 phrasebook 산출이며 doc 에 실재한다.

**못 본 것 / 왜** — 이 문장들 중 **어느 것이 "기본 화면"에 렌더되는지**를 가르지 못했다.
`result.tsx` 는 이 필드들을 컴포넌트 props 로 넘길 뿐(1807~1809, 2019~2022), 기본 화면과
부위 상세 시트 중 어디에 표시되는지는 렌더 트리를 따라가야 하고, 최종 판정은
**승인 목업 `mockups/index.html` 기본 화면 문장 집합과 화면 대조**여야 한다
(memory: verify-against-approved-mockup-not-just-code — 코드 grep 판정 불가는 33-G 26행이
이미 명시한 보류 사유이며 이번 실측으로도 그 사유가 해소되지 않았다).

**어디서 볼 것** — 시뮬레이터에서 재산출 doc 4건을 열고 **기본 화면(시트 미확장)** 상태의
문장을 전수 채집해 `mockups/index.html` 기본 화면 문장 집합과 diff.
점수가 움직인 doc(power-spin 80→60, elbow-twist 60→63)과 카드 수가 바뀐 doc 을 우선 볼 것 —
문장 인벤토리가 바뀌었을 가능성이 가장 크다.

---

## 부수 판정 — §C-4 항목 4 (9모션 앵커 주석)

### 판정: **잔여 없음** (등재 10동작 기준)

`sweep_out/real-ref/summary.json` 실측: `omitted:ref_gate` **39 → 0**.
기준이 12관절이 된 뒤 앵커 주석(부재 관절 대입 선언)이 필요한 criterion 이 **0개**다.
남은 omit 는 성격이 다르다:
- `omitted:unmapped` 30 = `arm_extension`·`leg_extension`·`split_angle` (애초에 각도 베이크
  대상이 아닌 region criterion). 주석과 무관.
- `omitted:degenerate` 1 = `ref-invert / angle_vs_reference__left_shoulder`
  (세 점이 겹쳐 각이 정의되지 않음). 주석으로 해결되는 종류가 아니다.

**값 채우기는 하지 않았다**(L-6 준수). `ref-combo` 는 criteria yaml 미보유라 스위프 대상이
아니다 — 기준 라이브러리 11 과 등재 10 을 섞어 쓰지 않았다.
