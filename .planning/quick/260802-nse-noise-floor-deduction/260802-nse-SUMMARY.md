---
phase: quick-260802-nse
plan: 01
subsystem: scoring
tags: [deduction-engine, measurement-error, ipsf, transparency]
requires: [deduction_engine.tally, motiondtw.per_joint_deviation, replay.py]
provides: [analysis/measurement_error.py, DeductionBreakdown.suppressedRecords, contract §10.8]
affects: [backend/functions/pipeline/app.py, app/src/types/analysis.ts, docs/contract.md]
tech-stack:
  added: []
  patterns: [order-statistic distribution-free CI, additive-optional contract field, fail-closed]
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/measurement_error.py
    - backend/tests/test_measurement_error.py
    - backend/tests/test_noise_floor_suppression.py
    - .planning/quick/260802-nse-noise-floor-deduction/noise_floor_effect.json
  modified:
    - backend/shared/python/sunity_shared/analysis/deduction_engine.py
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/models.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - app/src/types/analysis.ts
    - docs/contract.md
    - backend/evals/realfixture/replay.py
decisions:
  - "문턱 = 그 값을 만든 표본의 순서통계 median 신뢰구간(양측 95%). 상수표·부트스트랩·해석적 근사 전부 기각"
  - "억제 자리 = records.append 직전 — activated/cross-exclusion 과 살아남는 points 를 byte-불변으로 두는 유일한 자리"
  - "구간 미확보 = 종전대로 감점(fail-closed). 억제된 감점은 wouldBePoints 로 doc 에 보관"
metrics:
  duration: ~2h
  completed: 2026-08-02
---

# quick-260802-nse: 측정 오차 미만 감점 억제 Summary

감점 record 가 하는 단정("이 관절의 편차가 허용치를 넘는다")을 그 값 자신의 median
신뢰구간으로 검정해, 불확실도 안에서 성립하지 않는 record 를 방출하지 않게 했다.
실 doc 4건에서 점수가 **+10 / +5 / +1 / 0** 움직였고 모든 이동이 억제 내역으로 설명된다.

**BASE** = `5911156265bbea8aae747e86aab40523670a0a39`
**커밋** = `d11cf24b`(Task 1) → `5c2b3196`(Task 2) → `6a516a73`(Task 3) → `7102b480`(정정)

---

## 1. 실 doc 4건 전건 표 (하네스로 잰 값 — `noise_floor_effect.json` 직접 열어 읽음)

| fixture | final 전→후 | Δ | record 전→후 | 카드 전→후 (confirmed / advisory) | 시트 입력 전→후 |
|---|---|---|---|---|---|
| elbow-twist | **63 → 73** | **+10** | 8 → 3 | 5 → 4 (4→3 / 1→1) | 8 → 3 (렌더 O→O) |
| power-spin | 62 → 67 | +5 | 4 → 2 | 5 → 3 (4→2 / 1→1) | 4 → 2 (렌더 O→O) |
| kip-up | 99 → 100 | +1 | 1 → 0 | **1 → 2** (1→2 / 0→0) | 1 → 0 (렌더 O→**X**) |
| pdshape | 100 → 100 | 0 | 1 → 0 | 2 → 2 (1→1 / 1→1) | 1 → 0 (렌더 O→**X**) |

**전건 상승 또는 불변. 내려간 케이스 0.** 불변식 위반 0 (`invariantsHold: true`).

**"시트 입력"은 행 수가 아니다.** 잰 것은 시트의 입력(records) 수와 렌더 여부다
(`buildRegionSheetView` 는 records 0 이면 `null`). 실제 행은 `buildCauseGroupKeys` 로
원인 묶음이라 행 수 ≤ record 수이고, 그것을 확인하려면 앱을 렌더해야 한다 — 안 했다.

### elbow-twist 63 이 어디로 갔나 — 73 (+10)

억제 5건, 살아남은 3건. **살아남은 셋이 그 동작의 실제 결함(양 팔꿈치 + 오른어깨)이고,
지워진 다섯이 "8관절 균일 소폭 초과" 서명 그대로다.**

| 억제된 criterion | measuredValue | tol | CI95 | n | wouldBePoints |
|---|---|---|---|---|---|
| `angle_vs_reference__left_shoulder` | 20.41 | 20.0 | [16.91, 22.43] | 330 | −0.5 |
| `angle_vs_reference__left_hip` | 21.86 | 20.0 | [19.66, 24.01] | 330 | −2.2 |
| `angle_vs_reference__right_hip` | 21.72 | 20.0 | [18.55, 24.30] | 330 | −2.1 |
| `angle_vs_reference__left_knee` | 21.81 | 20.0 | [18.93, 24.96] | 330 | −2.2 |
| `angle_vs_reference__right_knee` | 22.14 | 20.0 | [18.52, 25.43] | 330 | −2.6 |
| **Σ** | | | | | **−9.6** |

`executionRawTotal` −36.9 → −27.3 = 이동 −9.6 = `Σ wouldBePoints`. 정확히 일치.

**계획 단계 추정과의 대조 — elbow-twist 는 완전 일치.** 계획 표의 5건·CI 하한
(16.91 / 19.66 / 18.55 / 18.93 / 18.52)·합계 −9.6 이 하네스 실측과 **소수점까지 같다.**
계획이 `motiondtw` 로 직접 잰 표본과 `app._deviation_against` 경로가 이 fixture 에서는
같은 열을 만들었다는 뜻이다.

### 나머지 3건 — 계획과 다른 곳

| fixture | 계획 표 | 실측 | 차이 |
|---|---|---|---|
| kip-up | `left_shoulder` 20.67 / CI 16.70 / −0.8 억제 | 20.67 / **16.70** / −0.8 억제 | 일치 |
| pdshape | `right_knee` 20.19 / CI **11.97** / −0.2 억제 | 20.19 / CI **12.28** / −0.2 억제 | CI 하한 0.31 차이 |
| power-spin | `left_shoulder` 30.67 / CI 24.83 **유지**만 기재 | `left_shoulder` 유지 + **`left_hip` −2.9 · `right_hip` −1.9 억제** | **계획 표가 불완전했다** |

- **pdshape CI 차이**는 계획이 미리 경고한 그것이다(`replay.py` 는 `_deviation_against`
  를 타므로 산출이 미세하게 다를 수 있다). 처분(억제)은 같다.
- **power-spin 은 계획 표에 없던 억제가 2건 나왔다.** 계획의 probe 가 그 fixture 의
  hip 관절을 표에 올리지 않았을 뿐, 규칙은 동일하게 적용됐다. 점수는 62 → 67.
  계획이 예측하지 못한 이동이므로 여기 적는다.

### fail-closed (구간 없이 종전대로 감점)

| fixture | criterion | points | 이유 코드 |
|---|---|---|---|
| power-spin | `leg_extension` | −20.0 | `different_estimator_select_window` |

나머지 3건은 fail-closed 항목 0 — 감점 record 가 전부 DTW-fallback
`angle_vs_reference__{jk}` 였기 때문이다. **fail-closed 가 비어 있는 것이 "fail-closed
가 안 걸린다"는 뜻이 아니다** — window/split/reach/fallback 경로 record 자체가 이
4건에 없었다(그 경로의 fail-closed 는 단위테스트로만 확인됨, §5 참조).

---

## 2. 점수가 움직인 만큼을 전건 설명

| fixture | executionRawTotal 전→후 | 이동 | Σ wouldBePoints | 일치 | final 항등식(INV-6) |
|---|---|---|---|---|---|
| elbow-twist | −36.9 → −27.3 | −9.6 | −9.6 | O | 성립 |
| power-spin | −37.6 → −32.8 | −4.8 | −4.8 | O | 성립 |
| kip-up | −0.8 → 0 | −0.8 | −0.8 | O | 성립 |
| pdshape | −0.2 → 0 | −0.2 | −0.2 | O | 성립 |

**설명 안 되는 이동 0건.** 살아남은 record 는 `to_dict()` 까지 byte-동일(밴드 아님),
`md` 도 억제 유무와 무관하게 byte-동일(빌더가 mutate 하지 않는다는 보증의 실측 확인).

억제 사유는 전부 하나 — **구간 하한이 허용치를 넘지 못했다**(`intervalLow <= 20.0`).
가장 여유가 없던 건은 elbow-twist `left_hip`(하한 19.66, 허용치까지 0.34), 가장 컸던
건은 pdshape `right_knee`(하한 12.28, 7.72 여유).

---

## 3. 헤드라인 — **2건에서 바뀌었다. 고치지 않고 보고한다.**

계획이 지목한 위험이 실제로 발생했다. 다만 발생 방식은 계획의 가설(최악 record 가
바뀜)이 아니라 **record 가 0이 되어 mission 자체가 사라지는** 쪽이었다.

| fixture | 헤드라인 record 전→후 | 문장 전 | 문장 후 |
|---|---|---|---|
| kip-up | `angle_vs_reference__left_shoulder` → **없음** | `왼쪽 어깨(겨드랑이) 각도가 킵업 기준 자세와 차이가 있어요` | `오늘은 이 부분에 집중해봐요` |
| pdshape | `angle_vs_reference__right_knee` → **없음** | `오른쪽 무릎 각도가 기준 셰이프와 차이가 있어요` | `오늘은 이 부분에 집중해봐요` |
| elbow-twist | `angle_vs_reference__right_elbow` (불변) | (동일) | (동일) |
| power-spin | `leg_extension` (불변) | (동일) | (동일) |

음성은 요약 문장을 읽는 경로이므로 위 2건은 **발화 내용도 바뀐다.**
표시 정책 변경은 이 사이클 범위 밖 — belle 판단 대상으로 올린다.

**이 답을 내기 위해 하네스를 한 번 고쳤다(자기 정정).** 최초 구현은 헤드라인을 **저장
doc 의 mission** 에서 읽었는데, mission 은 각인 시점(`_attach_translation_emission` →
`mission_mod.select_mission(records, ...)`)에 **그때의 record 로 다시 선정**된다.
저장 mission 을 쓰면 억제 전후가 언제나 같게 나와 질문 자체가 무의미해진다.
각인 후 result 에서 읽도록 바꾼 뒤에야 위 2건이 드러났다.

---

## 4. 계획에 없던 발견 — 카드는 사라지지 않고 **앵커를 잃는다**

kip-up 에서 record 가 1 → 0 인데 confirmed 카드가 **1 → 2 로 늘었다.**

원인(추측 아님, 소스 확인): `_build_fault_zoom_comparisons` 는 `criterion_units` 를
`deductionBreakdown.records` 에서 파생하는데(`app.py:3507-3512`), records 가 비면
`criterion_units = None` 이 되어 **legacy `fault_joints` fan-out 으로 폴백한다**
(그 자리 주석이 명시한 설계: "record 부재/빈 리스트는 None → 종전 fault_joints fan-out
보존"). `fault_joints` 는 `visionVeto.faultJoints` 에서 오는 **다른 출처**라 억제가
건드리지 않는다.

관측된 카드:

| fixture | 억제 전 | 억제 후 |
|---|---|---|
| kip-up | `angle_vs_reference__left_shoulder` (confirmed, criterion 있음) 1장 | criterion **없는** confirmed 2장 (`left_knee/legs`, `left_shoulder/arms`) |
| pdshape | `angle_vs_reference__right_knee` confirmed + advisory 1 | criterion **없는** confirmed 1(`left_hip/legs`) + advisory 1 |

즉 **감점 0점(100점)인데 확대 비교 카드는 남고, 그 카드가 가리키는 근거가 없다.**
표시 정합성 문제이고 표시 정책 변경은 범위 밖이라 고치지 않았다 — belle 판단 대상.

---

## 5. 게이트 결과 (수치)

### pytest — FAILED node ID diff

| | failed | passed | skipped |
|---|---|---|---|
| 착수 (`pytest_before.txt`) | 59 | **3841** | 27 |
| 종료 (`pytest_after.txt`) | 59 | 3952 | 27 |

**신규 실패 0건. 사라진 실패 0건.** (`comm` 으로 node ID 집합 대조 — 양방향 공집합.)
증가한 3841 → 3952 = 신규 테스트 111건(measurement_error 33 + noise_floor 78).

**계획이 적은 착수 관측치는 `59 failed / 3842 passed` 였는데 실측은 3841 passed 다.**
failed 수와 node ID 집합은 같고 passed 만 1 적다. 원인은 확인하지 않았다 — 이 사이클의
diff 기준선은 실측한 3841 을 썼다.

### 채점이 바뀌는데 깨진 기존 테스트 — **0건**

기본 off 가 byte-동일이라 깨질 이유가 구조적으로 없다. 그것을 두 층에서 확인했다:

1. 단위: `tally(...)` 를 인자 없이 부른 결과와 `measurement_error=None` 결과가
   dict 동등 + `suppressedRecords` 키 자체 부재.
2. **실물**: 변경 **전** `replay.py`(BASE 에서 `git show` 로 꺼냄)를 지금 코드로 돌린
   `--recon-only` 출력이 현재 `replay.py` 출력과 **byte-동일**, exit code 둘 다 1.
   실 doc 4건·record 16건 경로가 실제로 안 움직였다는 실행 증거다.

### legacy_baseline.py --verify

`PASS — 9 case / 9 card 해시 동일`. `fault_zoom.py` 무접촉이므로 기대대로다.

### git diff 범위

`git diff $BASE --stat` = 15 파일. `files_modified` 를 넘은 것은 **1개**:
`backend/shared/python/sunity_shared/firestore_admin.py` (아래 이탈 참조).

### app typecheck

`tsc --noEmit` 통과(출력 없음).

---

## 6. 계획에서 이탈한 것

### [Rule 2 - 누락된 필수 기능] firestore_admin 검증 대상에 `suppressedRecords` 추가

- **발견 시점:** Task 2, 계약 미러 작성 중
- **문제:** `_validate_deduction_breakdown` 은 `("records", "coverageGaps")` 만
  `_validate_dict_only_scalars` 로 라우팅한다. `suppressedRecords` 를 넣지 않으면
  이 키를 통해 nested array 가 검증 없이 통과해 Firestore 쓰기가 런타임에 깨진다
  (`[[firestore-nested-array-flat]]` — 아키텍처 제약).
- **처치:** 튜플에 `"suppressedRecords"` 추가 + 회귀 테스트 1건.
- **커밋:** `5c2b3196`

### `measurement_error[cid]` 를 `(L, U)` 뿐 아니라 `(L, U, n)` 도 받게 함

- **이유:** 계획의 `behavior` 는 항목을 `(L, U)` 로, 억제 내역 키는 `sampleSize` 를
  요구한다. 표본수를 어디서도 못 받으면 그 필드를 채울 수 없다.
- **처치:** 2원소/3원소 둘 다 수용. 3번째가 없으면 `sampleSize=0`(미제공).
  프로덕션 배선은 항상 3원소를 넘긴다. `per_joint_median_ci` 의 반환 형상은 계획대로
  `(L, U)` 그대로 두었다.
- **n 의 근거:** 방출된 관절은 `per_joint_deviation` 이 유한값을 냈다는 뜻이고
  `np.median` 은 NaN 을 전파하므로, 그 관절 열은 전부 유한 → 유한 표본수 == `len(path)`.
  실측 확인: elbow-twist n=330, pdshape n=237, power-spin n=161, kip-up n=118.

### 계획 `<done>` 의 grep 조건과 `<action>` 요구가 충돌 — action 을 따랐다

- `<done>` 은 `grep "1.253\|bootstrap\|random\|seed" measurement_error.py` 0건을
  요구하는데, 같은 계획의 `<action>` 은 "해석적 근사가 `motiondtw.py:201-212` 와
  자기모순인 이유"를 모듈 독스트링에 적으라고 요구한다. 그 이유를 적으면 `1.253` 이
  독스트링에 들어간다.
- **처치:** action 을 따랐다(설명은 남긴다). 대신 실질을 테스트로 잠갔다 —
  `tokenize` 로 COMMENT/STRING 을 걷어낸 **실행 코드**에 `1.253`/`random`/`bootstrap`/
  `seed`/`shuffle`/`choice` 가 0건임을 단언. `grep` 은 1건(독스트링), 실행 코드는 0건.
- 최초 작성한 라인 필터 버전은 `### 해석적 근사(...)` 가 `#` 로 시작한다는 이유로
  **우연히 통과**하고 있었다 — 그것을 알아채고 tokenize 로 바꿨다.

### 하네스 자기 정정 2건 (커밋 `6a516a73` → `7102b480`)

1. 헤드라인을 저장 mission 에서 읽던 것을 각인 후 result 로(§3).
2. `sheetRows*` 라는 이름이 재지 않은 것을 잰 것처럼 말하고 있었다 →
   `sheetRecordInput*`/`sheetRenders*` 로 정정(§1).

---

## 7. 문턱은 조정하지 않았다

`CI_ALPHA = 0.05` 는 착수 전 고정값 그대로다. fixture 결과를 보고 손대지 않았다.
그 수준이 임의 상수가 아님을 지키는 것은 **커버리지 테스트**다 — 정규·라플라스·
outlier 혼합 세 분포 × n∈{8,31,120} 에서 구간이 참 median 을 덮는 비율이 명목
95% 이상임을 단언한다(분포무관임의 실증). 최소표본 6도 리터럴이 아니라
`ceil(log2(2/alpha))` 닫힌 식과 탐색 구현의 **대조**로 잠갔다.

window 경로 fail-closed 도 임의 배제가 아니다: `inspect` 로 읽은
`window_median_angle_deltas` 기본 window(2) → 최대 표본 5 < 최소표본 6.
**방법 자신이 "이 median 은 못 묶는다"고 선언한다.**

---

## 8. 안 본 것 (재보지 않았다 — 확인했다고 말하지 않는다)

- **belle 실기기** — kip-up 어깨 카드가 실제로 사라지는지, elbow-twist 화면의 감점
  항목이 팔꿈치·어깨로 좁혀지는지. 하네스는 화면을 렌더하지 않는다.
- **시뮬레이터** — 앱 UI 변경이 없어(타입만 미러) 렌더 확인을 하지 않았다.
  `suppressedRecords` 는 **표시되지 않는다** — 렌더 추가는 belle 승인 사안.
- **Pod 재분석** — GPU/Pod/Gemini 호출 0. 실제 재분석 doc 으로는 확인하지 않았다.
- **mode3** — `measurement_error` 를 mode3 경로에 넘기지 않는다(기준 DTW 표본 부재).
  mode3 산출이 안 바뀐다는 것은 단위테스트가 아니라 **미배선**이 보장한다.
- **ipsf_absolute 구간 유도** — `leg_extension`/`arm_extension`/`line` 은
  `_select_window` 창 집계라 추정량이 다르다. 별도 유도가 필요하고 하지 않았다.
  power-spin 의 −20 이 그대로 남은 이유가 이것이다.
- **window/split/reach/fallback 경로의 fail-closed** — 실 doc 4건에 그 경로 record 가
  없어 **합성 단위테스트로만** 확인됐다. 실물에서는 관측되지 않았다.
- **`attributionReliability` 재계산** — 마커는 md 기준 `over_tol_count` 로 발화하고
  md 는 안 바뀌므로 **그대로 발화한다**. 억제 후 남은 3 record 에도 "AI 공부중" 강등이
  계속 붙는다. 이 마커를 억제 후 record 로 재계산할지는 별도 표시 결정 — 후속 판단 대상.
- **감점 시트 실제 행 수** — 앱을 렌더하지 않았다(§1).

---

## 9. Phase 34 로 넘기는 긴장

구간은 `(path, user_seg, reference_angles)` 의 **순수 함수**다 — 같은 입력이면 같은
구간, 같은 점수(결정성 유지, 테스트로 잠금). 다만 **같은 자세를 더 흔들리게 촬영하면**
구간이 넓어져 억제가 더 걸릴 수 있다.

이것이 새 분산원은 아니다 — 그 촬영은 오늘도 이미 다른 편차값을 낸다. 이 사이클은 그
분산이 **감점으로 새는 것**을 막는 쪽이다. 그래도 Phase 34("같은 자세면 같은 점수")가
이 seam 을 재검토 대상으로 삼을 수 있도록 명시한다:

- **재검토 대상:** record 단위 적응적 구간 vs. 관절별 고정표. 고정표는 코퍼스에 맞춘
  상수 묶음이라 이번엔 기각했지만(임의 상수 금지 + 포즈 모델/fps/기준 영상 변경 시
  re-fit 필요), "촬영 흔들림이 억제량을 바꾼다"를 Phase 34 가 문제로 규정하면 그 저울이
  달라질 수 있다.
- **미해소로 남긴 편향:** DTW 경로 스텝은 독립이 아니라 유효 표본수 < n → 구간이 참
  구간보다 **좁다** → 억제가 **덜** 걸린다. fail-closed 방향이라 이번 사이클에서
  보정하지 않았다(자기상관 보정 = 새 튜닝 상수).

---

## 10. belle 확인 요청 (2건, 둘 다 표시 정책 — 고치지 않았다)

1. **헤드라인/음성이 kip-up·pdshape 에서 일반 문구로 바뀐다** (§3). 감점이 0이 됐으니
   "오늘의 교정"이 없어지는 것이 옳은가, 아니면 감점 0에도 다음 과제를 제시해야 하는가.
2. **감점 0인데 확대 비교 카드가 남고 근거를 잃는다** (§4). records 가 비면 카드
   생성기가 legacy fan-out 으로 폴백해 criterion 없는 카드를 만든다. 카드를 함께
   없앨지, 앵커 없는 카드를 다른 어조로 보여줄지가 결정 사항이다.

---

## Self-Check: PASSED

생성 파일 존재 확인:
- `backend/shared/python/sunity_shared/analysis/measurement_error.py` FOUND
- `backend/tests/test_measurement_error.py` FOUND
- `backend/tests/test_noise_floor_suppression.py` FOUND
- `.planning/quick/260802-nse-noise-floor-deduction/noise_floor_effect.json` FOUND
- `.planning/quick/260802-nse-noise-floor-deduction/pytest_before.txt` / `pytest_after.txt` FOUND
- `.planning/quick/260802-nse-noise-floor-deduction/legacy_baseline_before.json` / `legacy_baseline.json` FOUND

커밋 존재 확인: `d11cf24b` / `5c2b3196` / `6a516a73` / `7102b480` 전부 FOUND.
