---
phase: quick-260802-tie
plan: 01
subsystem: analysis-output
tags: [fault-zoom, deduction-record, display-frame, keypoint-confidence, contract]
requires: [DeductionRecord.atFrameIdx, faultZoomComparisons, keypointReport]
provides: [moment.select_moment_index, FaultZoomComparison.refMarked]
affects:
  - backend/shared/python/sunity_shared/analysis/moment.py
  - backend/shared/python/sunity_shared/analysis/dimensions.py
  - backend/shared/python/sunity_shared/analysis/motiondtw.py
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/functions/pipeline/app.py
  - backend/evals/realfixture/replay.py
  - docs/contract.md
  - app/src/types/analysis.ts
  - app/src/components/DeductionDetailSheet.tsx
  - app/src/app/analysis/result.tsx
tech-stack:
  added: []
  patterns: [순수 규칙 모듈 + 주입 신뢰도, 그리는 코드가 인증, 어댑터 경계만 치환, 3-arm 실 데이터 대조]
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/moment.py
    - backend/tests/test_moment_tiebreak.py
    - backend/tests/test_fault_zoom_ref_marked.py
    - .planning/quick/260802-tie-frame-confidence-and-empty-ref-panel/measure_tie.py
    - .planning/quick/260802-tie-frame-confidence-and-empty-ref-panel/measure_out.json
  modified:
    - backend/shared/python/sunity_shared/analysis/dimensions.py
    - backend/shared/python/sunity_shared/analysis/motiondtw.py
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/functions/pipeline/app.py
    - backend/evals/realfixture/replay.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/app/analysis/result.tsx
decisions:
  - "동점 허용오차 = record 가 measuredValue 를 publish 하는 해상도 (엔진 출력에서 되읽어 게이트가 대조)"
  - "신뢰도 집계는 관절각 3점의 최솟값 — 표시 게이트가 3점 전부를 요구하기 때문"
  - "동점 아니면 argmin 그대로, 동률이면 최근접 유지 (엄격 부등호)"
  - "refMarked 는 criterion 카드에만 — legacy/advisory 는 정책상 무마킹이라 판정 대상 아님"
metrics:
  duration: 약 3시간
  completed: 2026-08-02
---

# quick-260802-tie: 프레임 신뢰도 동점 판정 + 빈 기준 패널 고지 Summary

두 건 다 **표시 계층**이다. 채점은 출력값으로 무접촉을 증명했다.

---

## ★ 먼저 알아야 할 것 — 오케스트레이터의 "7/12" 를 하네스가 독립 재현했다

브리프의 실측(“실 doc 12장 중 7장이 기준 패널 오버레이 0, 엘보 트위스트는 5장 전부”)을
**이 사이클이 새로 만든 `refMarked` 인증값으로 다시 세어 봤다.** 저장 doc 의 프레임을
그대로 재현하는 팔(A)에서:

| fixture | 카드 | criterion 카드 | 무표시 | advisory(정책상 무마킹) | 오버레이 0 합 |
|---|---|---|---|---|---|
| power-spin | 5 | 4 | 0 | 1 | 1 |
| kip-up | 1 | 1 | 0 | 0 | 0 |
| pd-shape | 1 | 0 | 0 | 1 | 1 |
| **elbow-twist** | **5** | **4** | **4** | **1** | **5** |
| **합계** | **12** | **9** | **4** | **3** | **7** |

**카드 12장 · 오버레이 0 이 7장 · 엘보 트위스트 5장 전부** — 브리프 수치와 정확히 같다.
서로 다른 두 경로(오케스트레이터의 doc 관찰 vs 렌더 코드가 낸 인증값)가 같은 수에
도달했으므로, `refMarked` 는 belle 이 실제로 보는 그 사실을 재고 있다.

---

## ① tie-break 이 실 데이터에서 프레임을 바꾼 건수 — **6/32 record** (그중 RECON 일치 4건)

`measure_out.json` 을 열어 센 값이다. 대조군/처리군의 처리 변수는 신뢰도 주입 하나뿐이다.

| fixture | 이동 | 상세 (프레임: 대조군 → 처리군) |
|---|---|---|
| power-spin | **0**/8 | — (DTW path 길이 161 = 홀수 → 동점 0) |
| kip-up | 3/8 | `left_elbow` 25→42 (RECON X) · `left_hip` 25→33 (RECON X) · `left_shoulder` 52→31 |
| pd-shape | 1/8 | `right_knee` 81→24 |
| elbow-twist | 2/8 | `right_hip` 54→179 · `right_shoulder` 27→162 |

**0 이 나온 fixture 가 있다는 사실이 이 수치의 의미를 만든다** — power-spin 은 DTW path
길이가 홀수라 median 을 정확히 갖는 스텝이 유일하고, 그래서 동점 자체가 없다. 규칙이
"동점일 때만" 작동한다는 것이 데이터로 드러난 것이다.

### 동점이 어디서 생기나 — 구조적이고, 관측된 것은 전부 DTW 경로다

**pointed window 경로의 동점은 이 4 fixture 에서 0건이다.** 네 doc 전부 `pointed=[]`
(Gemini 가 관절을 하나도 짚지 않음)이라 모든 관절이 DTW 경로로 흘렀다. window median
짝수 동점은 단위테스트가 잠그지만 **실 fixture 로는 확인되지 않았다.**

DTW 경로의 동점은 `np.median` 의 정의에서 온다 — path 길이가 짝수면 median 은 가운데 두
값의 평균이라 **어느 스텝도 그 값을 갖지 않고 두 스텝이 정확히 같은 거리**에 놓인다.

| fixture | DTW path | 짝수 | 관절별 동점 프레임 수 | 최대 |
|---|---|---|---|---|
| power-spin | 161 | 아니오 | `[1,1,1,1,1,1,1,1]` | **1** |
| kip-up | 118 | 예 | `[2,3,2,2,2,2,2,3]` | **3** |
| pd-shape | 237 | 아니오 | `[1,1,1,1,1,1,1,2]` | **2** |
| elbow-twist | 330 | 예 | `[1,2,2,2,2,2,2,2]` | **2** |

**동점 집합 최대 크기 = 3 프레임.** 창 전체를 훑는 argmax 였다면 수백(path 118~330)이
나왔을 자리다. 브리프의 "argmax 금지"는 이 수치로 지켜졌다.

### 이 이동이 실제로 무엇을 고쳤나 — 표시 게이트를 넘긴 사례 2건

동점 쌍의 학생 keypoint 신뢰도(관절각 3점의 최솟값, `_KP_CONF_MIN`=0.5):

```
elbow-twist right_shoulder   f27 conf=0.116 (게이트 미달)  ↔  f162 conf=0.508 (통과)
elbow-twist right_hip        f54 conf=0.255 (게이트 미달)  ↔  f179 conf=0.650 (통과)
```

둘 다 거리 차이 **정확히 0**이다. 종전 코드는 두 후보 중 **먼저 나온 스텝**을 골랐고,
그것이 하필 게이트 미달 프레임이었다. 브리프가 말한 "어느 프레임에 걸리느냐에 달린 우연"의
실물이다. 나머지 4건은 같은 게이트 쪽 안에서 움직였다(그림 가능성 변화 없음, 사진만 바뀜).

---

## ② 기준 패널 무표시가 실 fixture 에서 몇 장에 붙나 — **팔에 따라 4 / 2 / 1**

카드가 **어느 프레임에서 잘리느냐**에 따라 답이 달라진다. 그래서 세 팔로 쟀다.
**A 와 B/C 의 수를 증감으로 읽으면 안 된다 — 서로 다른 프레임의 카드다.**

| 팔 | 무엇인가 | 무표시 / 판정 대상 |
|---|---|---|
| **A** 앵커 없음 | belle 이 07-31 doc 에서 본 그 프레임 (czw 가 `REPRODUCED` 확인) | **4 / 9** |
| **B** 앵커 | quick-260801-gbk 반영분 (아직 belle 에게 안 나감) | **2 / 10** |
| **C** 앵커 + 동점 신뢰도 | 이 사이클 | **1 / 10** |

판정 대상에서 빠진 카드 3장은 advisory 다 — `criterion_units` 미전달로 구조적으로
criterion 이 없고, 기준측 무마킹이 게이트가 아니라 **정책**(게이트 B)이라 `refMarked`
키 자체를 싣지 않는다.

**A→B→C 로 줄어든 것은 이 사이클만의 공이 아니다.** 4→2 는 gbk 앵커의 효과이고, 2→1 이
이 사이클의 효과다(pd-shape `right_knee`). 그리고 그 1건조차 **직접 최적화한 결과가
아니다** — tie-break 이 고르는 것은 학생 패널 신뢰도이고, 기준 패널이 좋아진 것은
DTW 로 짝지어진 기준 프레임이 따라 움직인 **부수 효과**다. 이 구분을 흐리면 다음 사이클이
"신뢰도를 올리면 기준 패널이 좋아진다"는 잘못된 인과를 물려받는다.

남은 무표시 1장 = `elbow-twist / angle_vs_reference__right_elbow`. 기준 report 좌표가
게이트를 통과하지 못하는 카드로, **이 사이클의 목적은 그것을 고치는 것이 아니라 말하는
것**이다.

### 프레임 기하 민감도 — 답이 흔들리지 않는다

하네스의 프레임 배열은 합성이라 crop 포함 게이트(`_pt_in_crop`)가 프로덕션과 다르게
동작할 수 있다. 같은 측정을 8x8 과 640x360(프로덕션 추출기 형상) 두 기하로 돌렸다:
**무표시 1 → 1, 동일.** 이번 fixture 의 무표시 판정은 crop 기하가 아니라 confidence 게이트가
정한다는 뜻이다.

---

## "실질적으로 같은" 의 허용 오차를 **무엇에서 유도했는가**

`moment.TIE_EPS = 10^-2 (deg)`.

**출처 = 감점 record 가 자기 값을 publish 하는 해상도.** `deduction_engine` 은 record 를
방출할 때 `measuredValue` 와 `deviation` 을 소수 둘째 자리로 반올림한다. "이 값을 이
프레임에서 쟀다"는 주장은 **record 가 publish 한 값에 대한 주장**이므로, record 가
구분하지 못하는 차이는 그 주장도 구분하지 못한다. 그래서 그 해상도까지를 동점으로 본다.

**상수를 문서로 주장하지 않는다.** `test_tie_eps_is_the_record_published_resolution` 이
엔진에 소수 아래가 긴 값(41.23456789)을 먹여 방출된 자릿수를 반올림 동등으로 세고,
`TIE_EPS == 10^-그 자릿수` 를 단정한다. 엔진이 반올림 자릿수를 바꾸면 이 게이트가 먼저
깨진다 — 그때는 허용오차의 근거가 사라진 것이므로 폭도 함께 다시 정해야 한다.

**상한도 이 값이 스스로 준다.** 허용오차 안의 두 후보는 각도가 서로 2×TIE_EPS(0.02°)
이상 벌어질 수 없고, 그 크기는 RTMW jitter(도 단위)보다 두 자릿수 아래다. 그리고 실측에서
이 오차가 동점 집합을 넓힌 것은 **32개 관절-열 중 3건**뿐이었고, 넓혀도 최대 3프레임이었다.

**신뢰도 집계가 최솟값인 이유도 임의가 아니다.** 관절각은 keypoint 3점으로 이뤄지고
표시 게이트(`_high_conf_pts`)는 3점이 **전부** 임계 이상일 때만 각을 그린다. 게이트가 실제로
보는 양이 최솟값이므로 최솟값으로 잰다. 평균이면 신뢰도 높은 골반이 무너진 발목을 가려,
고른 프레임에서 정작 각이 안 그려진다 — 이 사이클이 없애려는 현상 그 자체다.

---

## 채점 무접촉의 근거 — "통과했다"가 아니라 출력값

**① 엔진·기준표 소스 diff 0 (구조적 증명, BASE 고정)**

```
$ git diff 71ea5de4 --exit-code -- .../analysis/deduction_engine.py && echo "ENGINE-DIFF-0 (exit 0)"
ENGINE-DIFF-0 (exit 0)
$ git diff 71ea5de4 --exit-code -- .../analysis/ipsf_criteria.py && echo "CRITERIA-DIFF-0 (exit 0)"
CRITERIA-DIFF-0 (exit 0)
```

`--exit-code` 단독이 아니라 **BASE 고정 비교**다 — `git add` 한 번에 무력화되지 않는다.

**② 실 fixture 4건의 최종 점수 — 대조군/처리군 같은 값**

```
power-spin   final 62 → 62
kip-up       final 99 → 99
pd-shape     final 100 → 100
elbow-twist  final 63 → 63
mdIdenticalAll = True   finalIdenticalAll = True
```

`md`(점수 substrate)는 키·값 모두 동등했다. 즉 tie-break 은 `deduction_engine.tally` 의
입력을 만들지도 바꾸지도 않는다 — 순간은 out-param 에만 기록되고 점수 계산 코드는 그
존재를 모른다(gbk 가 세운 seam 그대로).

**③ 단위 게이트** — `test_tiebreak_does_not_touch_the_score_substrate` 가 신뢰도 주입
유무에 따른 `md` 키·값 동등을 단정한다(PASS).

**④ pytest 기준선 diff (착수 시점 캡처 대비)**

```
착수 (2026-08-02):  59 failed, 3812 passed, 27 skipped
종료:               59 failed, 3841 passed, 27 skipped   (+29 = 신규 테스트 16 + 13)
$ diff tie-before.txt tie-after3.txt ; echo "diff-exit=$?"
diff-exit=0
```

**FAILED/ERROR node ID diff 완전히 빔.** (브리프가 적은 착수 수치 `3813 passed` 와 1 다르다 —
게이트는 수치가 아니라 diff 이고 그 diff 는 비었다.)

**⑤ 게이트 무변경** — `test_kp_conf_min_unchanged` 가 `_KP_CONF_MIN == 0.5` 를 잠근다.
이 사이클은 게이트를 여는 것이 아니라 게이트가 닫혔음을 말하는 것이다.

**⑥ RECON 게이트 무영향** — `replay.py --recon-only` 는 신뢰도 인자가 기본 off 라
czw 와 같은 `record 11/16 MATCH · fixture 4건` 을 낸다.

---

## 새 문구의 정확한 문자열

앱이 `refMarked === false` 일 때 확대 크롭 아래에 덧붙이는 한 줄:

```
오른쪽 사진에는 관절 위치를 확인하지 못해 표시를 넣지 않았어요
```

- **단정 금지**: 오른쪽 영상이나 선수를 평가하지 않는다. 우리가 그 프레임에서 관절
  위치를 확인하지 못했다는 **사실**과, 그래서 표시를 넣지 않았다는 **처분**만 말한다.
- **사과 금지**: "죄송" · "아쉽게도" 없음.
- **문형**: 기존 `refMatchNote` 선례(`같은 동작 순간을 찾지 못해 전신 화면으로
  보여드려요`)와 같은 [이유]+[그래서 이렇게 했다]+`-요`.
- **"오른쪽"인 이유**: 크롭 위 `halfLabel` 이 좌='내 영상' / 우=`rightLabel`
  (mode1 '정은지 선수' / mode3 '지난 영상')을 이미 렌더한다. 라벨 이름을 문장에 넣으면
  mode 별로 문장이 갈리고 "정은지 사진에는…"이 선수 평가처럼 읽힌다.
- **카드는 숨기지 않는다.** 사진·수치·비교 전부 그대로 두고 한 줄만 덧붙인다(정보 보존).
- `refMatch==='failed'` 캡션과 **자리를 나눠 쓴다** — 그쪽은 "같은 순간을 못 찾음",
  이쪽은 "순간은 맞췄는데 표시를 못 그림". 구조적으로 동시 발화하지 않는다
  (criterion 카드는 ref 대응 실패 시 D-12 ① 로 아예 방출되지 않는다).

---

## 계약 변경 (3자 미러)

`FaultZoomComparison.refMarked?: boolean` — `refMatched`/`atMatched` 와 같은 형상의
스칼라 불리언.

| 축 | 위치 |
|---|---|
| TS | `app/src/types/analysis.ts` `FaultZoomComparison.refMarked?` |
| 계약 | `docs/contract.md` §11 표 + **§11.9** 신설 |
| Python | `fault_zoom.build_fault_zoom_comparisons` 방출부 + `pipeline._render_fault_zoom` 매퍼 |

`models.py` 는 건드리지 않았다 — `FaultZoomComparison` 은 Python 쪽 키 집합을 갖지 않는다
(§11.6 `refMatch` 선례: "models.py 는 status 만 소유"). 세 축이 실제로 맞는지는
`test_ref_marked_three_way_lockstep` 이 파일을 읽어 대조한다.

**하위호환**: 부재 = 앱 종전대로(문구 없음). 기존 doc 크래시 0 — 앱은 `=== false` 로만
발화하므로 `undefined` 는 자연히 무발화다. Firestore 중첩 배열 0(스칼라 bool).

---

## Deviations

### 1. [Rule 2 - Missing critical] `_render_fault_zoom` 매퍼는 화이트리스트다

- **발견:** Task 2 배선 중. gbk Deviation 3 이 정확히 이 자리에서 데였다(`atMatched`
  누락 → no-op 출하). 방출만 하고 매퍼를 안 고치면 앱이 인증을 영영 못 본다.
- **조치:** `refMatched` 선례와 같은 조건부 복사 추가. **False 도 통과**시켜야 한다는 점이
  `atMatched`(True 만 방출)와 다르다 — 앱이 알려야 하는 값이 바로 False 쪽이다.
- **게이트:** `test_mapper_preserves_ref_marked_false` + `test_mapper_rejects_non_bool_ref_marked`.

### 2. [Rule 1 - Bug] 첫 테스트가 원 마커 경로를 검증하지 못했다

- **발견:** 드로잉 함수를 감싸 어느 경로가 인증했는지 실제로 세어 봤더니, `left_hip`
  카드는 원이 아니라 **각도 베이크**로 인증되고 있었다(`mark_circle_args=[False]`).
  테스트 이름이 `test_circle_marker_...` 인데 원 경로는 한 번도 안 탄 것이다.
- **조치:** 입력을 `leg_extension`(무릎 2개 → 꼭짓점 미성립 → `unmapped`)으로 바꿔
  원 경로만 남게 했고, 각도/사이각 테스트에는 **호출 카운트 단정**을 추가해
  "같은 True 를 다른 이유로 얻는 것"을 막았다.

### 3. [Rule 2] 측정 ② 를 단일 값이 아니라 3개 팔로

- **발견:** 첫 측정에서 무표시 2/10 이 나왔는데 브리프 실측은 7/12 였다. 원인은 하네스가
  **gbk 앵커 프레임**으로 렌더하고 브리프는 **07-31 저장 doc 프레임**을 본 것 — 다른
  프레임의 카드라 비교 대상이 아니었다.
- **조치:** A(앵커없음)/B(앵커)/C(앵커+신뢰도) 3팔로 재설계. A 가 7/12 를 독립 재현하면서
  측정 자체의 타당성이 증명됐다. **두 수를 하나로 뭉쳐 "2로 줄었다"고 쓸 뻔했다.**

### 4. [계획 조정] `_unit_conf` 가 문자열을 받아들이고 있었다

- `float("0.9")` 가 성공해 문자열 신뢰도가 통과했다. 출처가 문자열을 주는 상황은 출처가
  깨진 것이고, 깨진 출처로 표시 프레임을 옮기면 조용한 악화다. `int`/`float` 만 수용,
  `bool` 명시 배제(True 가 1.0 = 최고 신뢰가 되는 것을 막는다).

### 5. [계획 조정] `analysis.ts` 신규 주석의 `⚠️` 제거

- 인접 블록(`atMatched?`)이 쓰고 있어 처음엔 따라 썼으나, CLAUDE.md §7 "이모지 금지"가
  하드 제약이다. 기존 3건은 건드리지 않았고(과잉 일반화 회피) 신규 줄만 `**주의**` 로
  바꿨다.

---

## 안 본 것 — "안 재봤다"

| 항목 | 상태 | 이유 |
|---|---|---|
| 시뮬레이터 렌더 | **안 봤다** | 시뮬레이터를 띄우지 않았다. `npm run typecheck` 는 렌더 크래시를 못 잡는다 |
| 실기기 | **안 봤다** | belle 확인 대상 |
| 새 문구가 실제로 화면에 나오는 것 | **안 봤다** | prop 배선은 typecheck 로만 확인. 시트 렌더는 미확인 |
| Pod 재분석 후 실제 doc | **안 돌렸다** | Pod 미기동. 이 사이클은 **저장된 07-31 doc 을 재생**한 것이지 새 분석이 아니다 |
| PNG 픽셀 | **안 봤다** | 하네스 프레임 배열이 합성이다. ② 는 렌더 코드가 낸 인증값을 센 것이지 사진을 본 것이 아니다 |
| pointed window 경로의 동점 | **실 데이터로 확인 안 됨** | 4 fixture 전부 `pointed=[]` — 단위테스트로만 잠갔다 |
| mode3 경로 | **안 돌렸다** | fixture 4건 전부 mode1. mode3 도 `criterion_units` 를 넘기므로 `refMarked` 가 실리지만 실행으로 확인하지 않았다 |
| `split_angle`·창 의존 criterion 의 순간 | **관측 범위 밖** | czw RECON 이 재현하지 못하는 record 라 이 측정의 분모에도 없다 |
| 프로덕션 신뢰도 출처와 하네스 출처의 등가 | **실측 아님** | production=`pose_frames`(9fps), 하네스=저장 report(18fps). 짝수 rep 에서 선형보간 가중치 0 이라 같은 표본이 복원된다는 것은 `upsample_to_fps` **산식에서 온 추론**이지 두 값을 나란히 찍어 본 것이 아니다 |

**코드 게이트 통과 ≠ belle 확인.** 위 항목은 Pod 재분석 → OTA 발행 후 belle 이 실기기에서
봐야 한다.

---

## Known Stubs

없음. 하드코딩 빈값·placeholder·미배선 데이터 소스 0.

---

## Threat Flags

없음. 신규 네트워크 엔드포인트·인증 경로·파일 접근·신뢰경계 스키마 변경 0.
방출한 1필드는 렌더 결과의 boolean 이고 PII 0. 신규 의존성 0 (npm/pip install 0).

---

## 실행 환경 메모

워크트리에 `backend/.venv` 와 `app/node_modules` 가 없어 메인 체크아웃
(`/Users/kimtaesung/Dev/SunityMotion`)의 것을 **심볼릭 링크**해 게이트를 돌렸다.
패키지 설치 0, 네트워크 0, 메인 체크아웃 수정 0. 작업 종료 시 두 링크 모두 제거했다.
pytest 가 재생성한 추적 `.pyc` 2개도 원복했다.

---

## Commits

| hash | 내용 |
|---|---|
| `4edcd1a3` | Task 1 — `moment.py` 신설 + 4개 선택 지점 배선 + 게이트 16건 |
| `7f7f41d9` | Task 2 — `refMarked` 인증/방출/매퍼 + 계약 3자 미러 + 앱 한 줄 + 게이트 13건 |
| `9757059c` | 하네스 — 신뢰도 어댑터 + 3팔 측정 스크립트/산출물 |
| `fcc920f3` | 신규 주석 이모지 제거 (CLAUDE.md §7) |

문서(SUMMARY)는 커밋하지 않았다 — 브리프 지시.

---

## Self-Check: PASSED

- 신규 파일 5종 전부 존재 확인 (`moment.py` · 테스트 2 · `measure_tie.py` · `measure_out.json`).
- 커밋 4개 전부 `git log 71ea5de4..HEAD` 에 존재 확인.
- `measure_out.json` 재실행 byte-동일(`DETERMINISTIC-OK`), `X-Amz-Signature`/`AKIA` 0건.
- pytest FAILED/ERROR node ID diff 빔 · `npm run typecheck` 무출력 통과.
